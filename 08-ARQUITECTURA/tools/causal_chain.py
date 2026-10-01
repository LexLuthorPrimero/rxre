#!/usr/bin/env python3"
# CONTRACT: name=causal_chain
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""CAUSAL CHAIN -- el mapa causal de Polaris12, generado y actualizado solo.

POR QUE EXISTE. El proyecto tiene cinco herramientas que produces cada una una
pieza del mapa causal, y ninguna las une:

  gmmio_inventory  -> que REGISTROS toca el camino GFX8, con offset
  pm4_reachable    -> que PAQUETES ejecuta de verdad, con su sitio
  pm4_codec        -> el framing, y los nombres de campo
  include_closure  -> que opcode ve realmente el codigo
  causal_map       -> que AFIRMAN los documentos

El mapa causal que el proyecto quiere es la cadena:

  SOURCE -> SYMBOL -> PRODUCER -> REPRESENTATION -> TRANSFORMATION
         -> CONSUMER -> REGISTER/MEMORY -> HARDWARE EFFECT

Y los hallazgos van pokeandolo a mano, uno por ronda: "el wptr va a la pagina
del writeback", "el doorbell es una apertura de dispositivo", "CP_RB0_WPTR es
la rama muerta". Todas esas relaciones existen ya en el codigo, escritas por el
driver. Esta herramienta las EXTRAE.

QUE HACE Y QUE NO HACE:

  HACE: recorrer el codigo del camino alcanzable de GFX8 y, para cada cadena
  de llamadas, determinar que se escribe y donde. Emite aristas tipadas con su
  fichero y su linea, para que cada arista sea verificable.

  NO HACE: no dice que EFECTO tiene un registro. Eso no esta en el codigo, esta
  en el hardware, y 033 demostro que no hay documento que lo diga. Las aristas
  de efecto se marcan como INFERIDAS o se dejan fuera. Un mapa causal que se
  inventa los efectos es peor que no tener mapa.

FORMATO DE SALIDA: JSON con nodos y aristas, cada arista con su procedencia
(fichero:linea) y su tipo. Legible por maquina para composing con pm4_codec y
causal_map.

Uso:
  python3 causal_chain.py                 resumen de la cadena
  python3 causal_chain.py --register mmXX  quien escribe/lee ese registro
  python3 causal_chain.py --edges REG      aristas que tocan un registro
  python3 causal_chain.py --depth N        cuanto bajar por las llamadas
  python3 causal_chain.py --json           el grafo entero
  python3 causal_chain.py --graph          salida en formato dot (graphviz)
"""
import os
import re
import sys
import json
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

AMD = ("/home/lucas/Escritorio/RX550-INVESTIGACION/"
       "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
AMDDIR = f"{AMD}/amdgpu"

# ------------------------------------------------------------------ aristas
# Tipos de arista. El nombre ES la afirmacion: una arista MMIO_WR significa
# "esta funcion escribe este registro MMIO". Nada mas. No significa que el
# hardware lo interprete de una forma concreta.
ARISTAS = {
    "CALL":        "llama a",
    "REG_WRITE":   "escribe el registro MMIO",
    "REG_READ":    "lee el registro MMIO",
    "PM4_EMIT":    "emite el paquete PM4",
    "WR_MEM":      "escribe memoria del writeback",
    "DOORBELL":    "toca el doorbell",
    "IB_WRITE":    "escribe dwords en el indirect buffer",
}

# Efectos: NO se inventan. Un nodo sin efecto conocido se marca explicitamente
# como tal, y el recuento de "efectos conocidos" es la medida de lo poco que se
# sabe del hardware.
EFECTOS_CONOCIDOS = {}


# ------------------------------------------------------- indice del codigo
def load_functions():
    """{nombre: (fichero, ini, fin, lineas)}"""
    idx = {}
    for f in sorted(os.listdir(AMDDIR)):
        if not f.endswith(".c"):
            continue
        path = os.path.join(AMDDIR, f)
        try:
            src = open(path, errors="replace").read().split("\n")
        except OSError:
            continue
        i = 0
        while i < len(src):
            l = src[i]
            m = re.match(r"^(?:static\s+)?[\w \*]*?\**(\w+)\s*\(", l)
            if m and not l.rstrip().endswith(";"):
                name = m.group(1)
                j = i
                while "{" not in src[j] and j < len(src) - 1:
                    j += 1
                if "{" not in src[j]:
                    i += 1
                    continue
                d = 0
                for k in range(j, len(src)):
                    d += src[k].count("{") - src[k].count("}")
                    if d == 0:
                        idx.setdefault(name, (f, i, k, src))
                        i = k
                        break
                else:
                    break
            i += 1
    return idx


def reachable(idx):
    """BFS desde las semillas reales: ring_funcs + ip_funcs + genericas."""
    import pm4_reachable as R
    seeds = []
    src8 = open(f"{AMDDIR}/gfx_v8_0.c", errors="replace").read()
    for tab in ("gfx_v8_0_ring_funcs_gfx", "gfx_v8_0_ring_funcs_compute",
                "gfx_v8_0_ring_funcs_kiq"):
        m = re.search(r"struct amdgpu_ring_funcs\s+" + tab + r"\s*=\s*\{(.*?)\n\};",
                      src8, re.S)
        if m:
            for _f, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,",
                                    m.group(1), re.M):
                if fn in idx:
                    seeds.append(fn)
    m = re.search(r"struct amd_ip_funcs\s+gfx_v8_0_ip_funcs\s*=\s*\{(.*?)\n\};",
                  src8, re.S)
    if m:
        for _f, fn in re.findall(r"^\s*\.(\w+)\s*=\s*(\w+)\s*,", m.group(1), re.M):
            if fn in idx:
                seeds.append(fn)
    for g in R.GENERIC_ROOTS:
        if g in idx:
            seeds.append(g)
    seen, q = set(), deque(seeds)
    while q:
        fn = q.popleft()
        if fn in seen:
            continue
        seen.add(fn)
        rec = idx.get(fn)
        if not rec:
            continue
        body = "\n".join(rec[3][rec[1]:rec[2] + 1])
        for c in R.calls_in(body):
            if c in idx and c not in seen:
                q.append(c)
    return seen


# ---------------------------------------------------------- extraccion
REG_W = re.compile(r"\bWREG32(?:_SMC)?\s*\(\s*(mm\w+|ix\w+)")
REG_R = re.compile(r"\bRREG32(?:_SMC)?\s*\(\s*(mm\w+|ix\w+)")
PM4 = re.compile(r"PACKET3\(\s*(PACKET3_[A-Z0-9_]+)\s*,")
WDOOR = re.compile(r"\bWDOORBELL(?:32|64)\s*\(")
SMC = re.compile(r"\bamdgpu_reg_smc_(?:rd32|wr32)\s*\(")


def extract(fn, rec):
    """Aristas que salen de UNA funcion."""
    f, lo, hi, src = rec
    out = []
    body = src[lo:hi + 1]
    bodytxt = "\n".join(body)
    for k, line in enumerate(body, lo + 1):
        for m in REG_W.finditer(line):
            out.append(("REG_WRITE", m.group(1), k, f))
        for m in REG_R.finditer(line):
            out.append(("REG_READ", m.group(1), k, f))
        for m in PM4.finditer(line):
            out.append(("PM4_EMIT", m.group(1), k, f))
        if WDOOR.search(line):
            out.append(("DOORBELL", "doorbell", k, f))
        if SMC.search(line):
            out.append(("REG_WRITE", "SMC_despacio_propio", k, f))
        # escritura al IB: ring->ring[...] o *puntero
        if re.search(r"amdgpu_ring_write\s*\(", line):
            out.append(("IB_WRITE", "ring->ring", k, f))
        if re.search(r"\*ring->\w+_cpu_addr\s*=", line):
            out.append(("WR_MEM", line.split("=")[0].strip()[:40], k, f))
    return out


def calls(fn, rec):
    """Funciones que llama, con su linea."""
    f, lo, hi, src = rec
    out = []
    for k in range(lo, hi + 1):
        for m in re.finditer(r"(?<![\w.])([a-z_][a-z0-9_]*)\s*\(", src[k]):
            n = m.group(1)
            if n in ("if", "for", "while", "switch", "return", "sizeof"):
                continue
            out.append((n, k + 1, f))
    return out


# --------------------------------------------------------------- construccion
def build(depth=2):
    idx = load_functions()
    live = reachable(idx)
    nodes = {}
    edges = []
    for fn in sorted(live):
        rec = idx[fn]
        nodes[fn] = {"tipo": "funcion", "fichero": rec[0],
                     "linea": rec[1] + 1}
        for tipo, obj, ln, f in extract(fn, rec):
            edges.append(dict(src=fn, tipo=tipo, dst=obj, linea=ln,
                              fichero=f))
        if depth > 0:
            for callee, ln, f in calls(fn, rec):
                if callee in idx:
                    edges.append(dict(src=fn, tipo="CALL", dst=callee,
                                      linea=ln, fichero=f))
    return idx, live, nodes, edges


def main():
    args = sys.argv[1:]
    depth = 2
    if "--depth" in sys.argv:
        i = sys.argv.index("--depth")
        if i + 1 < len(sys.argv):
            try:
                depth = int(sys.argv[i + 1])
            except ValueError:
                pass
    idx, live, nodes, edges = build(depth)

    if "--json" in args:
        print(json.dumps(dict(
            n_funciones=len(live), n_aristas=len(edges),
            por_tipo={t: sum(1 for e in edges if e["tipo"] == t)
                      for t in ARISTAS},
            nodos=nodes, aristas=edges), indent=1))
        return 0

    if "--graph" in args:
        print("digraph causal {")
        for n, v in nodes.items():
            print(f'  "{n}" [shape=box];')
        for e in edges:
            if e["tipo"] == "CALL":
                continue
            print(f'  "{e["src"]}" -> "{e["dst"]}" '
                  f'[label="{e["tipo"]}", color=red];')
        print("}")
        return 0

    # BUG QUE ESTO ARREGLA: los filtros se buscaban sobre `args`, que ya
    # excluye los flags que empiezan por --, asi que `args[i+1]` era la
    # posicion siguiente de una lista SIN el flag. Con
    #     python3 causal_chain.py --edges WR_MEM
    # el filtro se leia como ausente y la seccion salia vacia, mientras que el
    # resumen de arriba decia "WR_MEM 2". Datos correctos, filtro roto.
    #
    # La forma correcta: buscar en sys.argv, que es donde estan los flags.
    def opt(nombre):
        if nombre in sys.argv:
            i = sys.argv.index(nombre)
            if i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        return None

    reg = opt("--register")
    edge_f = opt("--edges")

    print("=" * 76)
    print("CAUSAL CHAIN -- mapa causal generado del codigo de GFX8")
    print("=" * 76)
    print(f"funciones alcanzables : {len(live)}")
    print(f"aristas extraidas     : {len(edges)}  (profundidad {depth})")
    print()

    por = defaultdict(int)
    for e in edges:
        por[e["tipo"]] += 1
    print(f"{'tipo de arista':16} {'que significa':36} {'n':>5}")
    print("-" * 60)
    for t, n in sorted(por.items(), key=lambda kv: -kv[1]):
        print(f"{t:16} {ARISTAS.get(t, '?'):36} {n:5}")
    print()

    if reg:
        print("-" * 76)
        print(f"QUIEN TOCA {reg}")
        print("-" * 76)
        for e in edges:
            if e["dst"] == reg:
                print(f"  {e['tipo']:10} {e['src']:34} {e['fichero']}:{e['linea']}")
        print()

    if edge_f:
        print(f"aristas de tipo {edge_f}:")
        for e in edges:
            if e["tipo"] == edge_f:
                print(f"  {e['src']:34} -> {e['dst']:30} "
                      f"{e['fichero']}:{e['linea']}")
        print()

    # Lo que la herramienta NO sabe, dicho con numeros.
    regs = set(e["dst"] for e in edges if e["tipo"].startswith("REG"))
    with_efecto = sum(1 for r in regs if r in EFECTOS_CONOCIDOS)
    print("-" * 76)
    print("LIMITE, con numeros:")
    print(f"  registros tocados por el camino   : {len(regs)}")
    print(f"  de ellos, con efecto CONOCIDO    : {with_efecto}")
    print(f"  sin efecto conocido (NOT_DETERMINED): {len(regs) - with_efecto}")
    print()
    print("  Las aristas de arriba son REALES y VERIFICABLES: cada una dice")
    print("  'esta funcion escribe este registro' con fichero y linea. El")
    print("  EFECTO de un registro no esta en el codigo, esta en el hardware,")
    print("  y 033 demostro que no hay documento que lo de. Por eso el")
    print("  recuento de efectos conocidos es 0 y eso se dice con un numero.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())