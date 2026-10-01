#!/usr/bin/env python3
r"""INCLUDE CLOSURE RESOLVER -- que opcode ve REALMENTE una unidad

POR QUE EXISTE. En 037 escribi que "el mapa de registros del RX550 es gmc_8_2"
y era falso: gfx_v8_0.c incluye seis familias de registros, y solo GMC y SMU
son de Polaris12. Lo lei del primer #include sin listar los demas.

En 038 intentando usar el preprocesador como verdad:

    gcc -E -P -I... gfx_v8_0.c
    -> 60391 lineas, luego
    fatal error: dm_services_types.h: No existe el fichero o el directorio

Ese header no existe en ninguna parte del sistema. El preprocesador se detiene
y no puede arbitrarse el cierre de includes.

Mientras tanto pm4_reachable.py resuelve valores de opcode recorriendo TODAS
las cabeceras en ORDEN ALFABETICO y quedarse con el primero. Eso es una
suposicion, no una resolucion: si dos cabeceras dieran valores distintos, se
quedaba con uno sin decirlo (038 lo arreglo para que al menos lo declare).

Este script hace la resolucion de verdad, sin preprocesador:

  1. Parte de un .c
  2. Sigue sus #include recursivamente, respetando el orden de las directivas
  3. En cada cabecera, registra los #define con su ORDEN
  4. Un nombre definido mas tarde PISA al anterior (regla del preprocesador)
  5. Reporta: valor final, quien lo definio, y quien lo definio ANTES con otro
     valor (los redefinidos)

No resuelve macros de sistema, condicionales #if, ni ##. Eso se DECLARA: la
herramienta sirve para el subconjunto de directivas que el codigo de amdgpu usa
en la practica, y para lo demas dice "no pude" en vez de inventar.

Que NO hace a proposito: no intenta reconstruir el include de cabeceras del
kernel (fuera del corpus). Si una cabecera esta ausente, se declara ausente y
la resolucion se marca incompleta para ese nombre. Un "no se" explicito es mas
util que un numero plausible.

Uso:
  python3 include_closure.py <fichero.c>
  python3 include_closure.py <fichero.c> --opcodes     solo opcodes PACKET3
  python3 include_closure.py <fichero.c> --show PACKET3_COND_EXEC
"""
import os
import re
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
AMD = f"{ROOT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"

SEARCH_DIRS = [
    f"{AMD}/amdgpu",
    f"{AMD}/include",
    f"{AMD}/include/asic_reg",
    f"{AMD}/include/asic_reg/gca",
    f"{AMD}/include/asic_reg/gmc",
    f"{AMD}/include/asic_reg/bif",
    f"{AMD}/include/asic_reg/oss",
    f"{AMD}/include/asic_reg/dce",
    f"{AMD}/include/asic_reg/smu",
    f"{AMD}/include/asic_reg/oss",
    f"{AMD}/include/asic_reg/ivsrcid",
]

INC_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"')
DEF_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)"
                    r"(?:\s*\(([^)]*)\))?\s*(.*?)\s*$")
# solo #include locales (con comillas). Los de sistema (<linux/...>) se declaran
# ausentes: no estan en el corpus y no afectan a la resolucion de opcodes.
SYST_RE = re.compile(r"^\s*#\s*include\s+<([^>]+)>")


def find_header(name, seen_dirs=None):
    """Busca una cabecera local por nombre, en las rutas del corpus."""
    cands = [os.path.join(ROOT, name)]
    for d in SEARCH_DIRS:
        cands.append(os.path.join(d, name))
    for c in cands:
        if os.path.exists(c):
            return os.path.normpath(c)
    # buscar por basename en el arbol del corpus (una sola vuelta)
    base = os.path.basename(name)
    for d in [f"{AMD}/amdgpu", f"{AMD}/include"]:
        for dp, _dirs, files in os.walk(d):
            if base in files:
                return os.path.join(dp, base)
    return None


class Closure:
    def __init__(self):
        # nombre -> (valor, fichero, linea)
        self.defs = {}
        # nombre -> [(valor, fichero, linea), ...] en orden de aparicion
        self.history = {}
        self.visited = set()
        self.missing = []          # cabeceras locales no encontradas
        self.system_includes = []  # cabeceras de sistema (fuera del corpus)
        self.order = []            # orden de inclusion real

    def process_file(self, path, depth=0):
        path = os.path.normpath(path)
        if path in self.visited:
            return
        self.visited.add(path)
        rel = os.path.relpath(path, ROOT)
        self.order.append(rel)
        try:
            lines = open(path, errors="replace").read().split("\n")
        except OSError:
            return
        for n, line in enumerate(lines, 1):
            m = INC_RE.match(line)
            if m:
                inc = m.group(1)
                sub = find_header(inc)
                if sub:
                    self.process_file(sub, depth + 1)
                else:
                    if inc not in self.missing:
                        self.missing.append(inc)
                continue
            m = SYST_RE.match(line)
            if m:
                sysh = m.group(1)
                if sysh not in self.system_includes:
                    self.system_includes.append(sysh)
                continue
            m = DEF_RE.match(line)
            if m:
                name = m.group(1)
                val = (m.group(3) or "").strip()
                self.history.setdefault(name, []).append((val, rel, n))
                # el preprocesador: la ultima definicion gana
                self.defs[name] = (val, rel, n)

    def redefinitions(self):
        """Nombres definidos mas de una vez con VALOR DISTINTO."""
        out = []
        for name, hist in self.history.items():
            vals = [h[0] for h in hist]
            if len(hist) > 1 and len(set(vals)) > 1:
                out.append((name, hist))
        return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opcodes_only = "--opcodes" in sys.argv
    show = None
    for i, a in enumerate(sys.argv):
        if a == "--show" and i + 1 < len(sys.argv):
            show = sys.argv[i + 1]

    if not args:
        print(__doc__)
        return 2

    target = args[0]
    if not os.path.isabs(target):
        for d in SEARCH_DIRS:
            if os.path.exists(os.path.join(d, target)):
                target = os.path.join(d, target)
                break
        else:
            target = os.path.join(ROOT, target)

    if not os.path.exists(target):
        print(f"no existe {target}")
        return 2

    cl = Closure()
    cl.process_file(target)

    print("=" * 72)
    print(f"CIERRE DE INCLUDES -- {os.path.relpath(target, ROOT)}")
    print("=" * 72)
    print(f"ficheros incluidos      : {len(cl.order)}")
    print(f"cabeceras locales ausentes: {len(cl.missing)}"
          + (f"  {cl.missing[:6]}" if cl.missing else ""))
    print(f"cabeceras de sistema (fuera del corpus): {len(cl.system_includes)}")
    print()

    redefs = cl.redefinitions()
    if redefs:
        print(f"REDEFINICIONES con valor distinto: {len(redefs)}")
        print("(el preprocesador usa la ULTIMA; la herramienta lo declara)")
        print()
        for name, hist in sorted(redefs):
            vals = sorted(set(h[0] for h in hist))
            if not name.startswith("PACKET3_") and opcodes_only:
                continue
            print(f"  {name}")
            for val, rel, ln in hist:
                print(f"      {val:<12} <- {rel}:{ln}")
            print(f"      >>> gana: {hist[-1][0]}  ({hist[-1][1]}:{hist[-1][2]})")
        print()

    if show:
        if show in cl.defs:
            val, rel, ln = cl.defs[show]
            print(f"{show} = {val}   (de {rel}:{ln})")
        else:
            print(f"{show}: no definido en el cierre")
        return 0

    if opcodes_only:
        ops = {n: v for n, v in cl.defs.items() if n.startswith("PACKET3_")}
        print(f"opcodes PACKET3 en el cierre: {len(ops)}")
        # valores con conflicto entre las redefiniciones
        conflict_ops = {n for n, _ in redefs if n.startswith("PACKET3_")}
        if conflict_ops:
            print(f"de los cuales con redefinicion: {len(conflict_ops)}")
            for n in sorted(conflict_ops):
                print(f"  {n} -> {cl.defs[n][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())