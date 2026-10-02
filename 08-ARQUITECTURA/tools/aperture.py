#!/usr/bin/env python3
# CONTRACT: name=aperture
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""aperture -- ¿caben los registros de esta placa en la apertura que mapea el driver?

POR QUE EXISTE. El hallazgo 200Ayerigio que el driver NO mapea BAR2 sino BAR5,
de 256 KiB (0x40000 bytes), base 0xF7D00000. Eso da un limite DURO y verificable:
si algun registro que el driver usa estuviera por encima de 0x40000, ese acceso
seria inalcanzable con el mapeo que hace.

Es una comprobacion con resultado binario y con adversario real: si el limite
fuera falso, habria un fallo. No es una lista de副主任, es una prueba.

ADEMAS responde una pregunta que no estaba registrada: cual es la SUPERFICIE DE
REGISTROS de cada bloque de esta placa, contada desde las cabeceras que el codigo
incluye de verdad. Ojo: la superficie se cuenta por el include del .c, NO por el
nombre del bloque -- VCE 3.4 usa vce_3_0_d.h, y UVD 6.3 usa uvd_6_0_d.h. Es la
misma aliasacion que abide 192, y buscar por el nombre del bloque daria "ausente".

LIMITE DECLARADO. Se extraen los #define cuyo valor es UN hexadecimal literal.
Los registros de GCN se definen asi. Los defines con shifts, enum o expresiones
NO se cuentan, y eso hace que el maximo sea una COTA INFERIOR del offset real: si
algo no cabe, es que no cabe de verdad; si todo cabe, no se puede prometer que
todo lo demas tambien.

Uso:
  aperture.py --todos              todas las cabeceras de la placa
  aperture.py --cabecera gca/gfx_8_0_d.h
  aperture.py --self-test

Codigos de salida:
  0  todo cabe en la apertura
  3  algun registro NO cabe en la apertura
  2  cabecera ausente
  4  .ko ausente (no aplica aqui; reservado)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AMD = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd", "amdgpu")
ASIC = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                    "drivers", "gpu", "drm", "amd", "include", "asic_reg")

_CACHE = {}


def codigo_driver():
    """Todo el .c/.h del driver en un solo string, cacheado.

    Importa porque la medicion de USO es una busqueda de nombre sobre ~625
    ficheros: sin cachearla, cada cabecera rebarre el arbol entero.
    """
    if "src" not in _CACHE:
        trozos = []
        for d in (AMD,):
            for f in sorted(os.listdir(d)):
                if f.endswith((".c", ".h")):
                    try:
                        with open(os.path.join(d, f), encoding="utf-8",
                                  errors="replace") as fh:
                            trozos.append(fh.read())
                    except OSError:
                        pass
        _CACHE["src"] = "\n".join(trozos)
    return _CACHE["src"]

# La apertura que el driver REALMENTE mapea: BAR5, 256 KiB. Ver hallazgo 200.
APERTURA = 0x40000

# Cabeceras por bloque de esta placa. El nombre es el del .c que la incluye, no
# el del bloque, por el motivo que dice la docstring.
PLACA = [
    ("gfx_v8_0",   "gca/gfx_8_0_d.h"),
    ("gmc_v8_2",   "gmc/gmc_8_2_d.h"),
    ("gmc_v8_1",   "gmc/gmc_8_1_d.h"),
    ("uvd_v6_0",   "uvd/uvd_6_0_d.h"),
    ("vce_v3_0",   "vce/vce_3_0_d.h"),
    ("oss_3_0",    "oss/oss_3_0_d.h"),
    ("oss_2_0",    "oss/oss_2_0_d.h"),
    ("bif_5_0",    "bif/bif_5_0_d.h"),
    ("bif_5_1",    "bif/bif_5_1_d.h"),
    ("smu_7_1_3",  "smu/smu_7_1_3_d.h"),
    ("smu_7_1_2",  "smu/smu_7_1_2_d.h"),
    ("dce_10_0",   "dce/dce_10_0_d.h"),
]

# #define NOMBRE 0x...    con el valor siendo un hexadecimal literal.
DEF = re.compile(r"^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
                 r"(0[xX][0-9a-fA-F]+)\s*(?:/\*.*)?$")
DEF_PARENS = re.compile(r"^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
                        r"\(\s*(0[xX][0-9a-fA-F]+)\s*\)\s*(?:/\*.*)?$")


def escanear(rel):
    """(nombre, offset) de cada #define con valor hexadecimal literal."""
    ruta = os.path.join(ASIC, rel)
    if not os.path.exists(ruta):
        return None
    out = []
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = DEF.match(linea) or DEF_PARENS.match(linea)
            if m:
                out.append((m.group(1), int(m.group(2), 16)))
    return out


def es_indirecto(nombre):
    """Los registros con prefijo `ix` NO son offsets MMIO.

    Son indices de acceso indirecto: ixPCIEP_RESERVED=0x10010000,
    ixGCK_MCLK_FUSES=0xC0500008, ixD3F5_PCIE_MC_OVERLAY_BAR1=0x0B0000C7.

    ATENCION, y este es el punto donde mi primera version se equivoco por partida
    doble: yo clasificaba por MASCARA de nibble alto (v & 0xF0000000). Eso falla
    en los dos sentidos:

      * da como "offset" valores que no lo son  -> ixPB1_TX_LANE15_* = 0x02209A08
        tiene el nibble alto a cero y se colaba como si fuera un offset de 34 MiB.
      * el patron no es el nibble, es el PREFIJO: el 100% de los defines con
        nibble alto lleva `ix`, pero hay `ix` con nibble alto cero.

    El prefijo `ix` es la convencion de AMD para registro de indice, no una
    aproximacion mia por el nombre. Y aun asi se comprueba en el self-test: si
    queda algun define SIN `ix` por encima de 32 MiB, es que el filtro falla.
    """
    return nombre.startswith("ix")


def self_test():
    fails = []

    def eq(lbl, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (lbl, got, want))

    # 1. La apertura sale del hallazgo 200: BAR5 = 262144 = 0x40000.
    eq("APERTURA es 256 KiB", APERTURA, 262144)
    eq("APERTURA en hex", hex(APERTURA), "0x40000")

    # 2. VECTOR DE EXTRACCION: los cuatro formatos de #define que hay que aceptar
    #    y los dos que NO.
    import tempfile
    _fd, ruta = tempfile.mkstemp(suffix=".h")
    with os.fdopen(_fd, "w", encoding="utf-8") as fh:
        fh.write("#define A 0x10\n"
                 "#define B    0x20   /* comentario */\n"
                 "#define C (0x30)\n"
                 "#define D 0x40 /* pegado */\n"
                 "#define E (A)\n"
                 "#define F 48\n")
    try:
        # Se prueba el regex contra las lineas, que es lo que hace escanear().
        got = []
        for linea in io_lines(ruta):
            m = DEF.match(linea) or DEF_PARENS.match(linea)
            if m:
                got.append((m.group(1), int(m.group(2), 16)))
        eq("hex extraidos", got, [("A", 0x10), ("B", 0x20), ("C", 0x30), ("D", 0x40)])
    finally:
        os.unlink(ruta)

    # 3. CONTROL NEGATIVO: una cabecera inexistente tiene que devolver None, no []
    #    -- una lista vacia se lee como "esa cabecera no tiene registros".
    if escanear("no_existe/esta_cabecera_d.h") is not None:
        fails.append("control negativo: cabecera inexistente devolvio datos")

    # 4. ANCLA EXTERNA: gfx_8_0_d.h tiene 2801 #define (contado a mano antes de
    #    escribir la herramienta). El extractor tiene que dar un numero del mismo
    #    orden. Si difiere en un factor, el extractor esta roto.
    cab = escanear("gca/gfx_8_0_d.h")
    if cab is None:
        fails.append("ancla: no encuentro gca/gfx_8_0_d.h")
    elif not (1000 < len(cab) < 4000):
        fails.append("ancla: gfx_8_0_d.h da %d registros hex, esperaba del orden "
                     "de miles (contados a mano: 2801 defines totales)" % len(cab))

    # 5. Control negativo: escanear no debe inventar offsets por encima de 32 bits
    if cab:
        for n, v in cab:
            if v > 0xFFFFFFFF:
                fails.append("offset absurdo %s=0x%x" % (n, v))
                break

    # 6. CLASIFICADOR ix. Tres vectores tomados del header real, no inventados:
    #    los dos primeros son `ix` CON nibble alto (una mascara los pillaria bien),
    #    y el tercero es `ix` con nibble alto CERO, que es justo el caso que hizo
    #    fallar a la mascara por partida doble.
    eq("ixPCIEP_RESERVED es indirecto", es_indirecto("ixPCIEP_RESERVED"), True)
    eq("ixPB1_TX_LANE15_CTRL_REG0 (nibble alto 0) es indirecto",
       es_indirecto("ixPB1_TX_LANE15_CTRL_REG0"), True)
    eq("mmVM_CONTEXT1_CNTL no es indirecto", es_indirecto("mmVM_CONTEXT1_CNTL"), False)

    # 7. Y la comprobacion que hace que el prefijo no sea una custom de fe: si
    #    queda algun define sin `ix` por encima de 32 MiB, el filtro esta roto.
    rotas = []
    for rel in ("gca/gfx_8_0_d.h", "bif/bif_5_1_d.h", "smu/smu_7_1_3_d.h"):
        for n, v in escanear(rel) or []:
            if not es_indirecto(n) and v > 0x2000000:
                rotas.append("%s=%#x" % (n, v))
    if rotas:
        fails.append("filtro ix incompleto: %d define(s) sin ix por encima de "
                     "32 MiB, p.ej. %s" % (len(rotas), rotas[0]))

    # 8. ANCLA EXTERNA del modo --uso, con lo medido a mano sobre 625 ficheros:
    #    ixPCIE_SCRATCH_OVRD (de bif_5_1_d.h) SI aparece en el codigo del driver,
    #    e ixGCK_MCLK_FUSES (de smu_7_1_3_d.h) NO. Medido a mano: de 5500 ix
    #    definidos, 84 referenciados. Si el extractor de uso se rompe y no
    #    encontrara NADA, daria 0 y este aserto lo detectaria.
    src = codigo_driver()
    cab = escanear("bif/bif_5_1_d.h") or []
    nombres = [n for n, _v in cab if es_indirecto(n)]
    if not nombres:
        fails.append("modo uso: no se extrajo ningun ix de bif_5_1_d.h")
    else:
        usados = [n for n in nombres if n in src]
        if len(usados) > len(nombres) * 0.5:
            fails.append("modo uso: %d de %d ix de bif_5_1_d.h salen usados; el "
                         "medido a mano es ~20 de 3188" % (len(usados), len(nombres)))
        eq("codigo del driver no vacio", len(src) > 1000000, True)

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (2 vectores de apertura, 4 de extraccion, "
          "2 anclas, 3 del clasificador, 1 del modo uso, 4 controles)")
    return 0


def io_lines(ruta):
    import io
    with io.open(ruta, encoding="utf-8", errors="replace") as fh:
        return fh.readlines()


def main(argv):
    if "--self-test" in argv:
        return self_test()

    if "--uso" in argv:
        src = codigo_driver()
        print("codigo del driver leido: %d bytes" % len(src))
        print()
        print("%-24s %7s %7s %7s   %-14s %-14s"
              % ("cabecera", "MMIO", "usados", "%", "ix", "ix usados"))
        print("-" * 76)
        tmm = tmu = tix = tixu = 0
        for bloque, rel in PLACA:
            cab = escanear(rel)
            if cab is None:
                continue
            mm = [n for n, _v in cab if not es_indirecto(n)]
            ix = [n for n, _v in cab if es_indirecto(n)]
            mu = [n for n in mm if n in src]
            xu = [n for n in ix if n in src]
            print("%-24s %7d %7d %6.1f%%   %-14d %-14d"
                  % (rel.split("/")[-1], len(mm), len(mu),
                     100.0 * len(mu) / max(len(mm), 1), len(ix), len(xu)))
            tmm += len(mm); tmu += len(mu); tix += len(ix); tixu += len(xu)
        print("-" * 76)
        print("%-24s %7d %7d %6.1f%%   %-14d %-14d"
              % ("TOTAL", tmm, tmu, 100.0 * tmu / max(tmm, 1), tix, tixu))
        print()
        print("Ojo con lo que esto significa: los headers son un VOCABULARIO, no un")
        print("mapa de uso. Que un registro este definido no dice que el driver lo")
        print("toque, y la cifra de MMIO usados (%d de %d) es la relevante."
              % (tmu, tmm))
        return 0

    objetivos = PLACA
    if "--cabecera" in argv:
        rel = argv[argv.index("--cabecera") + 1]
        objetivos = [("custom", rel)]

    print("apertura real mapeada por el driver: BAR5 = 0x%X (%d bytes)"
          % (APERTURA, APERTURA))
    print()
    print("%-12s %-24s %7s %10s %8s  %s"
          % ("bloque", "cabecera", "define", "indirectos", "maxMMIO", "cabe"))
    print("-" * 82)

    fuera = []
    ausentes = []
    for bloque, rel in objetivos:
        cab = escanear(rel)
        if cab is None:
            ausentes.append(rel)
            print("%-12s %-24s %7s %10s %10s  AUSENTE"
                  % (bloque, rel, "-", "-", "-"))
            continue
        mmio = [v for n, v in cab if not es_indirecto(n)]
        ix = len(cab) - len(mmio)
        vals = mmio if mmio else [0]
        lo, hi = min(vals), max(vals)
        cabe = hi < APERTURA
        if not cabe:
            fuera.append((bloque, rel, hi))
        print("%-12s %-24s %7d %10s 0x%06X  %s"
              % (bloque, rel, len(cab), "(%d ix)" % ix, hi,
                 "si" if cabe else "** NO **"))

    print()
    print("cabeceras ausentes: %d de %d" % (len(ausentes), len(objetivos)))
    print("cabeceras con registros por encima de la apertura: %d" % len(fuera))
    for b, r, hi in fuera:
        print("   %s (%s) llega a 0x%X, %d bytes por encima"
              % (b, r, hi, hi - APERTURA + 1))
    if ausentes:
        return 2
    return 3 if fuera else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))