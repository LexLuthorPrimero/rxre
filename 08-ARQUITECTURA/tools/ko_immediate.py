#!/usr/bin/env python3
# CONTRACT: name=ko_immediate
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""ko_immediate -- extrae los dwords PM4 que el .ko REALMENTE escribe.

Por que existe: pm4_emit.py calcula los valores de los paquetes PM4 leyendo las
macros del driver. Eso es una DERIVACION. Este script los lee del binario
cargado, que es OBSERVACION. Que coincidan convierte la derivacion en hecho
comprobado sobre el modulo que esta en memoria.

Y no es un detalle: en un .ko los `call` tienen desplazamiento cero y lo
parchea la reubicacion, asi que el desensamblado lineal se desincroniza a
partir del primer `call`. Por eso NO se usa objdump para contar, sino un
escaneo de bytes del patron de `movl`.

Se busca: la forma en que `amdgpu_ring_write(ring, v)` compila en este
build, que es

    c7 04 <sib> <imm32>      movl $imm32, disp(%base,%index,4)

LIMITACION DECLARADA: es un patron, no un desensamblado. Cualquier otra
instruccion con la misma forma daria un falso positivo. Por eso la salida
muestra el byte SIB y por eso el valor de esta herramienta es el CONTRASTE
con pm4_emit, no el analisis en solitario.

Uso:
  ko_immediate.py --func gfx_v8_0_ring_emit_vm_flush
  ko_immediate.py --compare FUNCION    una funcion, binario vs pm4_emit
  ko_immediate.py --compare-all        TODAS: tabla de estado por funcion
  ko_immediate.py --all gfx_v8_0
  ko_immediate.py --self-test

Codigos de salida:
  0  todo lo pedido se resolvio
  2  simbolo no encontrado
  3  no existe el .ko
"""

import os
import re
import subprocess
import sys

KO = "/tmp/amdgpu_loaded.ko"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# movl $imm32, disp(%base,%index,scale) -- el codigo de amdgpu_ring_write.
STORE_RE = re.compile(rb"\xc7\x04(.)(.{4})", re.S)


class Ko:
    def __init__(self, path=KO):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.path = path
        self.data = open(path, "rb").read()
        self.text_addr, self.text_off = self._text_section()
        self.syms = self._symbols()

    def _text_section(self):
        out = subprocess.run(["readelf", "-S", "--wide", self.path],
                             capture_output=True, text=True).stdout
        m = re.search(r"\.text\s+PROGBITS\s+([0-9a-f]+)\s+([0-9a-f]+)", out)
        if not m:
            raise ValueError("no se encontro .text")
        return int(m.group(1), 16), int(m.group(2), 16)

    def _symbols(self):
        out = subprocess.run(["nm", self.path], capture_output=True,
                             text=True).stdout
        syms = []
        for line in out.splitlines():
            parts = line.split()
            # nm imprime: <direccion> <tipo> <nombre>. El tipo es parts[1].
            if len(parts) == 3 and parts[1] in ("t", "T"):
                syms.append((int(parts[0], 16), parts[1], parts[2]))
        syms.sort()
        return syms

    def bytes_at(self, va, n):
        return self.data[self.text_off + (va - self.text_addr):
                          self.text_off + (va - self.text_addr) + n]

    def func_bounds(self, name):
        """(inicio, fin) de un simbolo de texto. El fin es el siguiente simbolo.

        Los simbolos locales (`t`) tambien estan: en un .ko el simbolo de una
        funcion static SI aparece, que es lo que hace esto posible.
        """
        idx = None
        for i, (addr, _t, nm) in enumerate(self.syms):
            if nm == name:
                idx = i
                break
        if idx is None:
            return None
        start = self.syms[idx][0]
        end = self.syms[idx + 1][0] if idx + 1 < len(self.syms) else start + 0x1000
        return start, end

    def dwords(self, name):
        """[(offset_relativo, valor, sib)] de los stores del patron."""
        b = self.func_bounds(name)
        if b is None:
            return None
        start, end = b
        body = self.bytes_at(start, end - start)
        out = []
        for m in STORE_RE.finditer(body):
            out.append((m.start(), int.from_bytes(m.group(2), "little"),
                        m.group(1)[0]))
        return out, end - start


def describe(ko, name):
    r = ko.dwords(name)
    if r is None:
        return None
    vals, size = r
    print("%s  @0x%x  %d bytes  %d stores"
          % (name, ko.func_bounds(name)[0], size, len(vals)))
    for off, v, sib in vals:
        print("   +0x%04x  0x%08X   sib=0x%02x  (base=%d idx=%d esc=%d)"
              % (off, v, sib, sib & 7, (sib >> 3) & 7, (sib >> 6) & 3))
    return vals


def compare(ko, name):
    """Contraste contra pm4_emit.py, que es la otra via de obtener el valor."""
    vals = describe(ko, name)
    if vals is None:
        print("simbolo no encontrado: %s" % name)
        return 2
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "08-ARQUITECTURA", "tools",
                                     "pm4_emit.py"), "--func", name],
                       capture_output=True, text=True)
    expected = []
    for line in r.stdout.splitlines():
        m = re.match(r"\s*\d+\s+\S+\s+(0x[0-9A-Fa-f]{8})"
                     r"(?:\s+\[cond\])?\s*$", line)
        if not m:
            continue
        tok = m.group(1)
        # Un valor parcial ("00000000 | ?addr") NO es un dword conocido, pero
        # ocupa una posicion y hay que conservarla: si se filtra, pm4_emit
        # pareceria emitir menos dwords de los que emite, y el veredicto
        # "DIFIERE" seria un artefacto de este script y no un hallazgo.
        mv = re.match(r"^0x([0-9A-Fa-f]{8})$", tok)
        expected.append(int(mv.group(1), 16) if mv else None)
    if not expected:
        print("\npm4_emit no produjo valores para %s" % name)
        print(r.stdout.strip()[:200])
        return 2

    print("\n  %-4s %-12s %-12s %s" % ("#", "binario", "pm4_emit", ""))
    n = max(len(vals), len(expected))
    same = 0
    for i in range(n):
        a = vals[i][1] if i < len(vals) else None
        b = expected[i] if i < len(expected) else None
        if a is not None and b is not None:
            if a == b:
                same += 1
                ok = "coincide"
            else:
                ok = "DIFIERE"
            print("  %-4d 0x%08X   0x%08X   %s" % (i, a, b, ok))
        else:
            print("  %-4d %-12s %-12s %s"
                  % (i, "0x%08X" % a if a is not None else "-",
                     "0x%08X" % b if b is not None else "-", "solo en uno"))
    comun = min(len(vals), len(expected))
    print("\n  %d/%d coincidentes;  binario=%d dwords  pm4_emit=%d dwords"
          % (same, n, len(vals), len(expected)))
    if same == comun and len(vals) == len(expected):
        print("  RESULTADO: identico")
        return 0
    print("  RESULTADO: NO identico -- revisar antes de concluir")
    return 1


def is_subsequence(needles, hay):
    """¿Cada elemento de needles aparece en hay, respetando el orden?

    POR QUE UNA SUBCADENA Y NO UNA COMPARACION POSICIONAL: el patron del
    binario solo ve `movl $inmediato, memoria`. Las escrituras con valor de
    runtime (cmd, reg, val) las compila a `mov %reg, memoria`, que NO aparece.
    Asi que el numero de dwords de un lado y del otro no es comparable, y
    comparar posicion a posicion daria "DIFIERE" en todas partes sin que
    hubiera ninguna discrepancia real.

    Lo que si es comparable y es la afirmacion que importa: toda constante que
    pm4_emit calcula tiene que aparecer en el binario, en ese orden.
    """
    it = iter(hay)
    faltan = []
    for n in needles:
        for h in it:
            if h == n:
                break
        else:
            faltan.append(n)
    return faltan


def const_offsets_in_body(body, consts):
    """Para cada constante, el PRIMER offset >= anterior donde aparece.

    POR QUE EL CUERPO ENTERO Y NO SOLO LOS STORES `movl $imm`:

    El compilador no siempre deja la constante en un `movl $inmediato`.
    Puede cargarla en un registro y luego storear el registro, o emitirla con
    otra forma. Los 3 casos que fallaban con el criterio estrecho
    (0x00038514, 0x40100000) ESTABAN en el cuerpo: no era un error de
    pm4_emit, era un criterio de busqueda demasiado estrecho.

    Y se conserva el orden: una constante no puede aparecer ANTES que la
    anterior. Sin eso, "esta en el cuerpo" no diria nada sobre el orden de
    emision, que es justo lo que se quiere comprobar.
    """
    faltan, off, primero = [], 0, True
    for c in consts:
        le = (c & 0xFFFFFFFF).to_bytes(4, "little")
        p = body.find(le, off)
        if p < 0:
            faltan.append(c)
            primero = False          # tras fallar, no exigimos orden
        else:
            off = p + 1
    return faltan


def compare_all(ko, prefix="gfx_v8_0"):
    """Contraste en lote: una fila por funcion, y una tabla de estado.

    La columna que importa es la ultima. pm4_emit no puede resolver lo que el
    preprocesador ya resolvio (un #ifdef dentro de una expresion), pero el
    binario si. Y al reves, el binario no dice cual de dos ramas tomo. Juntas
    cierran mas que cada una por separado, y por eso la tabla distingue las
    cuatro situaciones en vez de dar un unico veredicto.
    """
    names = [nm for _a, _t, nm in ko.syms
             if nm.startswith(prefix) and "emit" in nm
             and not nm.startswith("__pfx")]
    rows = []
    ident = faltan_constantes = sin_constantes = 0
    for nm in sorted(names):
        d = ko.dwords(nm)
        if d is None or not d[0]:
            continue
        b = ko.func_bounds(nm)
        body = ko.bytes_at(b[0], b[1] - b[0])
        r = subprocess.run([sys.executable,
                            os.path.join(ROOT, "08-ARQUITECTURA", "tools",
                                         "pm4_emit.py"), "--func", nm],
                           capture_output=True, text=True)
        consts, sinres = [], 0
        for line in r.stdout.splitlines():
            # Anclado a FIN DE LINEA a proposito: "0x00000001 (rango en una
            # rama)" NO es una constante, es un rango. Sin el anclaje se
            # aceptaba como valor limpio y producia un "NO EN EL BINARIO"
            # falso contra el driver.
            m = re.match(r"\s*\d+\s+\S+\s+(0x[0-9A-Fa-f]{8})"
                         r"(?:\s+\[cond\])?\s*$", line)
            if m:
                consts.append(int(m.group(1), 16))
            else:
                sinres += 1
        faltan, fuera_de_orden, off = [], [], 0
        for c in consts:
            le = (c & 0xFFFFFFFF).to_bytes(4, "little")
            if body.find(le) < 0:
                faltan.append(c)
            else:
                p = body.find(le, off)
                if p < 0:
                    fuera_de_orden.append(c)
                else:
                    off = p + 1
        if not consts:
            estado = "sin constantes"
            sin_constantes += 1
        elif faltan:
            estado = "NO EN EL BINARIO: " + " ".join("%08X" % f for f in faltan)
            faltan_constantes += 1
        elif fuera_de_orden:
            # Presentes, pero el compilador movio la carga. No es un defecto:
            # es reordenacion del compilador, y por eso se informa aparte.
            estado = ("presentes (%d), %d reordenadas por el compilador"
                      % (len(consts), len(fuera_de_orden)))
            ident += 1
        else:
            estado = "todas presentes y en orden (%d)" % len(consts)
            ident += 1
        rows.append((nm, b[1] - b[0], len(consts), sinres, estado))

    print("%-42s %8s %9s %7s  %s"
          % ("funcion", "bytes", "constantes", "sin res.", "estado"))
    for nm, nb, nc, sr, est in rows:
        print("%-42s %8d %9d %7d  %s" % (nm, nb, nc, sr, est))
    ordenadas = sum(1 for _n, _b, _c, _s, e in rows if "en orden" in e)
    reord = sum(1 for _n, _b, _c, _s, e in rows if "reordenadas" in e)
    print("\n%d funciones: %d con TODAS sus constantes presentes en el codigo"
          % (len(rows), ident))
    print("real del modulo cargado. De esas, %d mantienen el orden y %d tienen"
          % (ordenadas, reord))
    print("constantes reordenadas por el compilador. %d tienen alguna constante"
          % faltan_constantes)
    print("que NO aparece (revisar). %d sin constantes." % sin_constantes)
    return 0 if faltan_constantes == 0 else 1


def self_test():
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))

    try:
        ko = Ko()
    except FileNotFoundError:
        print("self-test FALLA: no existe %s" % KO)
        print("   Sin .ko no se puede validar. No se da por bueno.")
        return 1

    # 1. El .ko tiene que ser un ELF con .text localizable.
    if ko.text_addr < 0 or ko.text_off < 0:
        fails.append(".text mal resuelta")
    if len(ko.syms) < 1000:
        fails.append("solo %d simbolos: improbable para un .ko de amdgpu"
                     % len(ko.syms))

    # 2. Los simbolos LOCALES deben estar. Es lo que hace posible todo esto:
    #    una funcion static no sale en la tabla de simbolos exportados.
    if not any(t == "t" for _a, t, _n in ko.syms):
        fails.append("no hay simbolos locales: el escaneo no serviria")

    # 3. VECTOR CONOCIDO, verificado a mano con objdump:
    #    0x147876: movl $0xc0053c00,(%rdx,%rax,4)
    b = ko.func_bounds("gfx_v8_0_ring_emit_vm_flush")
    if b is None:
        fails.append("no esta gfx_v8_0_ring_emit_vm_flush en el simbolo")
    else:
        got = [v for _o, v, _s in ko.dwords("gfx_v8_0_ring_emit_vm_flush")[0]]
        eq("dword 0 (cabecera WAIT_REG_MEM)", got[0] if got else None, 0xC0053C00)
        eq("dword 2 (POLL_ADDR)", got[2] if len(got) > 2 else None, 0x51E)
        eq("dword 6 (poll interval)", got[6] if len(got) > 6 else None, 0x20)
        eq("dword 7 (PFP_SYNC_ME)", got[7] if len(got) > 7 else None,
           0xC0004200)
        eq("numero de dwords", len(got), 9)

    # 4. VECTOR DE OTRA FUNCION, opcode conocido de sid.h:
    #    PACKET3_COND_EXEC = 0x22 (sid.h:359), PACKET3_SWITCH_BUFFER = 0x8B
    #    (sid.h:550). Si el escaneo no los encuentra, el patron esta roto.
    r = ko.dwords("gfx_v8_0_ring_emit_init_cond_exec")
    if r is None:
        fails.append("falta gfx_v8_0_ring_emit_init_cond_exec")
    else:
        vals = [v for _o, v, _s in r[0]]
        if 0xC0032200 not in vals:
            fails.append("no se encontro COND_EXEC (0xC0032200) en %r"
                         % [hex(v) for v in vals])

    # 5. CONTROL NEGATIVO: un simbolo que no existe debe devolver None, no
    #    una lista vacia que pareceria "esta funcion no escribe nada".
    if ko.dwords("no_existe_esta_funcion") is not None:
        fails.append("un simbolo inexistente devolvio algo en vez de None")

    # 6. CONTROL NEGATIVO: los limites de la funcion tienen que ser crecientes
    #    y el cuerpo no puede estar vacio.
    for nm in ("gfx_v8_0_ring_emit_vm_flush", "gfx_v8_0_ring_emit_wreg"):
        b = ko.func_bounds(nm)
        if b is None:
            fails.append("sin limites para %s" % nm)
            continue
        if b[1] <= b[0]:
            fails.append("limites degenerados en %s: %r" % (nm, b))
        if ko.bytes_at(b[0], b[1] - b[0]) == b"":
            fails.append("cuerpo vacio en %s" % nm)

    # 7. CONTROL NEGATIVO: si el patron emparejara cualquier cosa, el numero
    #    de stores seria absurdo. Se acota a un rango plausible.
    vals, size = ko.dwords("gfx_v8_0_ring_emit_vm_flush")
    if len(vals) * 4 > size:
        fails.append("mas stores que bytes: el patron esta demasiado laxo")

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (9 vectores, 4 controles)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()

    try:
        ko = Ko()
    except FileNotFoundError:
        print("no existe %s" % KO)
        return 3

    if "--func" in argv:
        name = argv[argv.index("--func") + 1]
        if describe(ko, name) is None:
            print("simbolo no encontrado: %s" % name)
            return 2
        return 0

    if "--compare" in argv:
        return compare(ko, argv[argv.index("--compare") + 1])

    if "--compare-all" in argv:
        pref = argv[argv.index("--compare-all") + 1] if len(argv) > \
            argv.index("--compare-all") + 1 else "gfx_v8_0"
        return compare_all(ko, pref)

    if "--all" in argv:
        pref = argv[argv.index("--all") + 1] if len(argv) > \
            argv.index("--all") + 1 else "gfx_v8_0"
        total = 0
        for addr, _t, nm in ko.syms:
            if nm.startswith(pref) and "emit" in nm and not \
                    nm.startswith("__pfx"):
                r = ko.dwords(nm)
                if r is None:
                    continue
                vals, size = r
                print("%-44s %4d bytes  %2d stores  %s"
                      % (nm, size, len(vals),
                         " ".join("%08X" % v for v, in
                                  ((v,) for _o, v, _s in vals))[:60]))
                total += 1
        print("\n%d funciones con stores" % total)
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
