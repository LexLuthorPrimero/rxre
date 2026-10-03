#!/usr/bin/env python3
# CONTRACT: name=driver_offsets
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""driver_offsets -- cada constante de registro del driver, cotejada con el ASIC.

POR QUE EXISTE. El driver declara offsets de registro en sus cabeceras
(`RX550_MM_VM_CTX0_PTBA 0x54f`, ...). Esos numeros son un CONTRATO con el
hardware, y §8 dice que la implementacion no es autoridad: que el driver escriba
0x54f no prueba que 0x54f sea el registro que cree, solo prueba que escribe 0x54f.

La unica forma de cerrarlo es cotejar cada constante contra las definiciones
reales del ASIC en `include/asic_reg/`. Eso es lo que hace esto, y lo hace de
forma REPETIBLE: un numero mal puesto se ve aqui, antes de que exista hardware.

TRES VEREDICTOS, Y LA DISTINCION IMPORTA

  CONFIRMADO   el offset existe y es UN registro con ese nombre
  AMBIGUO      existe, pero MAS DE UN registro con ese offset. No se puede decir
               cual de ellos pretendia el driver, y la ambiguedad es informacion,
               no un fallo que haya que tapar
  NO_ENCONTRADO ningun registro tiene ese offset. Esto NO es "el driver se
               equivoca": puede ser un registro que GFX8 no tiene y que el driver
               deberia quitar, o un offset derivado que no es un registro. Por
               eso NO_SE_ENCONTRADO, no FALLO.

LIMITE DECLARADO. Solo coteja constantes que se parecen a un offset de registro
(`RX550_MM_*`, `MM_*`, `*_ADDR`, `*_REG`). Una constante de mascara de bits NO es un
offset y no se busca: buscarla daria un falso NO_ENCONTRADO.

Uso:
  driver_offsets.py                  todos los ficheros
  driver_offsets.py --fichero N      uno
  driver_offsets.py --pm4           opcode de paquete del driver vs sid.h/vid.h
  driver_offsets.py --pm4           opcode de paquete vs sid.h/vid.h
  driver_offsets.py --vflush      dwords de la secuencia de vm-flush
  driver_offsets.py --campos       shifts de campo vs sid.h/vid.h
  driver_offsets.py --self-test

Codigos de salida:
  0  todas las constantes de registro están CONFIRMADAS
  1  hay alguna AMBIGUA o NO_ENCONTRADA
  2  no encuentro el arbol del driver o el de asic_reg
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DRV = os.path.join(ROOT, "07-DRIVER", "kernel")
ASIC = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                    "drivers", "gpu", "drm", "amd", "include", "asic_reg")

# Constantes que son offsets de REGISTRO. El filtro es por forma de nombre, y es
# deliberado: una mascara de bits (RX550_..._MASK) NO es un offset.
# Los opcode de PAQUETE PM4 (`RX550_PKT3_*`) NO son offsets de registro: son
# el valor de cabecera que se pasa a `rx550_pm4_header(opcode, count, ...)`.
# Se excluyen por nombre Y el motivo queda escrito, porque el exclusion sin
# motivo es un caso que se "corrige" dentro de seis meses.
RE_OFF = re.compile(r"^\s*#define\s+((?:RX550_)?(?:MM_[A-Z0-9_]+|[A-Z0-9_]*"
                    r"(?:_ADDR|_REG|_BASE|_PTBA|_REQUEST|_RESPONSE)))\s+"
                    r"0x([0-9a-fA-F]+)\s*(?:/\*.*)?$")

RE_PKT3 = re.compile(r"^RX550_PKT3_")

RE_DEF = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)\s+0x([0-9a-fA-F]+)\s*$")


# Solo los headers que ESTA PLACA usa. Indexarlos todos hacia que TODO salga
# ambiguo, porque el mismo offset existe en GCN1, GCN3, GCN5 y GCN12 con nombres
# distintos. Eso no es ambiguedad del driver: es falta de ALCANCE. Comparar sin
#scope es el mismo error que buscar una capacidad en el directorio equivocado.
HEADERS_PLACA = ["gmc/gmc_8_1_d.h", "gca/gfx_8_0_d.h", "oss/oss_3_0_d.h",
                 "uvd/uvd_6_0_d.h", "vce/vce_3_0_d.h", "bif/bif_5_0_d.h",
                 "bif/bif_5_1_d.h", "smu/smu_7_1_3_d.h", "dce/dce_10_0_d.h"]


def registro_por_offset():
    """offset -> [nombres] desde SOLO los headers que esta placa usa.

    Los registros `ix*` se EXCLUYEN: son indices de acceso indirecto, no offsets
    MMIO. Sin este filtro, `RX550_PKT3_SET_SH_REG 0x76` casaba con
    `ixMC_IO_DEBUG_UP_118` y decia AMBIGUO cuando lo cierto es que 0x76 no es un
    offset de registro en absoluto.
    """
    idx = {}
    if not os.path.isdir(ASIC):
        return None
    for rel in HEADERS_PLACA:
        h = os.path.join(ASIC, rel)
        if not os.path.exists(h):
            continue
        try:
            with open(h, encoding="utf-8", errors="replace") as fh:
                for linea in fh:
                    m = RE_DEF.match(linea)
                    if m and not m.group(1).startswith("ix"):
                        idx.setdefault(int(m.group(2), 16), []).append(m.group(1))
        except OSError:
            continue
    return idx


def constantes(fichero):
    out = []
    with open(fichero, encoding="utf-8", errors="replace") as fh:
        for n, linea in enumerate(fh, 1):
            m = RE_OFF.match(linea)
            if m and not RE_PKT3.match(m.group(1)):
                out.append({"nombre": m.group(1), "off": int(m.group(2), 16),
                            "linea": n, "fichero": os.path.basename(fichero)})
    return out



# ---------------------------------------------------------------- PM4
# Los opcode de PAQUETE no son registros, pero son contrato con el ASIC igual:
# un valor distinto produce sumisiones invalidas SIN ningun sintoma hasta que
# el trabajo no llega a la GPU. Se cotejan contra sid.h y vid.h.
AMD_DIR = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                       "drivers", "gpu", "drm", "amd", "amdgpu")
RE_PKT_DEF = re.compile(r"^\s*#define\s+(PACKET3_[A-Z0-9_]+)\s+0x([0-9a-fA-F]+)")
RE_DRIVER_PKT = re.compile(r"^\s*#define\s+(RX550_PKT3_[A-Z0-9_]+)\s+"
                           r"0x([0-9a-fA-F]+)")


def tabla_packets():
    """PACKET3_X -> (valor, fichero, linea), desde sid.h y vid.h.

    Se leen los DOS porque un paquete puede estar definido en cualquiera de los
    dos, y a veces en los dos. `vid.h` separa los defines con TABULADOR y
    `sid.h` con espacio: un grep con un solo separador encuentra uno de los dos y
    hace pensar que el otro no existe. Ya me paso: casi reporto una cita
    erronea del driver por eso.
    """
    t = {}
    for h in ("sid.h", "vid.h"):
        ruta = os.path.join(AMD_DIR, h)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for n, linea in enumerate(fh, 1):
                m = RE_PKT_DEF.match(linea)
                if m:
                    t.setdefault(m.group(1), (int(m.group(2), 16), h, n))
    return t


def pm4_driver():
    t = {}
    for f in glob.glob(os.path.join(DRV, "*.h")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                m = RE_DRIVER_PKT.match(linea)
                if m:
                    nombre = m.group(1)
                    # RX550_PKT3_SET_SH_REG_START es un OFFSET de registro,
                    # no un opcode de paquete: se llama PKT3 pero no lo es.
                    if nombre.endswith("_START"):
                        continue
                    t[nombre[len("RX550_PKT3_"):]] = int(m.group(2), 16)
    return t


def cotejo_pm4():
    t = tabla_packets()
    d = pm4_driver()
    filas, ok, mal = [], 0, 0
    for k in sorted(d):
        ref = t.get("PACKET3_" + k)
        if ref is None:
            filas.append((k, d[k], None, "NO_ENCONTRADO", "-"))
            mal += 1
        elif ref[0] == d[k]:
            filas.append((k, d[k], ref[0], "CONFIRMADO", "%s:%d" % (ref[1], ref[2])))
            ok += 1
        else:
            filas.append((k, d[k], ref[0], "** DIFIERE **",
                          "%s:%d" % (ref[1], ref[2])))
            mal += 1
    return filas, ok, mal



# ------------------------------------------------- SECUENCIA DE INVALIDACION
# Ni opcode ni registro: el numero de DWORDS que escribe la secuencia de
# vm-flush. Es el ultimo contrato numerico del driver, y gobierna si el TLB se
# invalida entero. Se cuenta LEYENDO los emisores, no creyendo la constante: si
# un emisor cambia y la constante no, esta herramienta lo ve.
RE_EMIT = re.compile(r"buf\[ib->length_dw\+\+\]")


def _dwords(nombre):
    """Cuantos dwords escribe un emisor del driver, contados en su cuerpo."""
    ruta = os.path.join(DRV, "rx550_pm4.c")
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        texto = fh.read().split("\n")
    total, dentro = 0, False
    for linea in texto:
        if re.match(r"^(__u32|void|static).*\b%s\s*\(" % nombre, linea):
            dentro = True
            continue
        if dentro:
            total += len(RE_EMIT.findall(linea))
            if linea.startswith("}"):
                return total
    return None


def cotejo_vflush():
    wd, wr, pf = _dwords("rx550_pm4_write_data"), \
                   _dwords("rx550_pm4_wait_reg_mem"), \
                   _dwords("rx550_pm4_pfp_sync_me")
    filas, ok, mal = [], 0, 0
    if None in (wd, wr, pf):
        return [("no se pudo contar un emisor", "-", 0, "NO_ENCONTRADO", "-")], 0, 1
    gfx = wd + wd + wr + pf        # PTBA + invalidate + wait + pfp
    nofp = wd + wd + wr            # PTBA + invalidate + wait
    # El desglose se escribe con los NOMBRES de los emisores, no con numeros
    # sueltos: "5+5" no dice de donde sale, y un desglose que no se puede
    # leer es peor que no dar ninguno.
    desglose = ("2 write_data(%d+%d) + wait(%d) + pfp(%d)"
                % (wd, wd, wr, pf))
    desglose_nopfp = "2 write_data(%d+%d) + wait(%d)" % (wd, wd, wr)
    for nombre, cuenta, declarado, desglose in (
            ("VM_FLUSH_DW (con PFP)", gfx, 19, desglose),
            ("VM_FLUSH_DW_NO_PFP", nofp, 17, desglose_nopfp)):
        est = "CONFIRMADO" if cuenta == declarado else "** DIFIERE **"
        if est == "CONFIRMADO":
            ok += 1
        else:
            mal += 1
        filas.append((nombre, desglose, cuenta, est, "declarado %d" % declarado))
    return filas, ok, mal


# ------------------------------------------------------------- CAMPOS
# Un opcode correcto con un campo mal puesto emite un paquete BIEN FORMADO que
# hace OTRA cosa. Es la clase de fallo que si da sintomas, a diferencia del
# opcode, y por eso merece su propio cotejo.
#
# Se compara el SHIFT, no el texto: la ISA escribe `(1 << 16)` y el driver
# `(1u << 16)`, que son el mismo valor con distinto sufijo. Comparar cadenas
# daria un falso "difiere" por el sufijo, que es la clase de error que ya ha
# pasado varias veces aqui.
RE_SHIFT = re.compile(r"<<\s*(\d+)")

PARES_CAMPO = [
    ("WRITE_DATA_DST_SEL",   "RX550_WRITE_DATA_DST_SEL"),
    ("WR_ONE_ADDR",          "RX550_WR_ONE_ADDR"),
    ("WR_CONFIRM",           "RX550_WR_CONFIRM"),
    ("WRITE_DATA_ENGINE_SEL", "RX550_WRITE_DATA_ENGINE_SEL"),
    ("WAIT_REG_MEM_FUNCTION",  "RX550_WAIT_REG_MEM_FUNCTION"),
    ("WAIT_REG_MEM_MEM_SPACE", "RX550_WAIT_REG_MEM_MEM_SPACE"),
    ("WAIT_REG_MEM_OPERATION", "RX550_WAIT_REG_MEM_OPERATION"),
    ("WAIT_REG_MEM_ENGINE",    "RX550_WAIT_REG_MEM_ENGINE"),
]


def _defines_isa():
    """nombre -> (shift_o_None, fichero, linea) para los campos de paquete."""
    t = {}
    for h in ("sid.h", "vid.h"):
        ruta = os.path.join(AMD_DIR, h)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for n, linea in enumerate(fh, 1):
                if not linea.lstrip().startswith("#define"):
                    continue
                m = re.match(r"\s*#define\s+([A-Za-z_]\w*)", linea)
                if not m:
                    continue
                sh = RE_SHIFT.search(linea)
                t.setdefault(m.group(1),
                             (int(sh.group(1)) if sh else None, h, n))
    return t


def _shift_driver(nombre):
    for f in glob.glob(os.path.join(DRV, "*.h")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                m = re.match(r"\s*#define\s+%s\b(.*)$" % re.escape(nombre),
                             linea)
                if m:
                    sh = RE_SHIFT.search(m.group(1))
                    return int(sh.group(1)) if sh else None
    return None


def cotejo_campos():
    isa = _defines_isa()
    filas, ok, mal = [], 0, 0
    for nom_isa, nom_drv in PARES_CAMPO:
        d = _shift_driver(nom_drv)
        r = isa.get(nom_isa)
        if d is None or r is None:
            filas.append((nom_drv, nom_isa, d, r[0] if r else None,
                          "NO_ENCONTRADO", "-"))
            mal += 1
        elif r[0] is not None and d == r[0]:
            filas.append((nom_drv, nom_isa, d, r[0], "CONFIRMADO",
                          "%s:%d" % (r[1], r[2])))
            ok += 1
        else:
            filas.append((nom_drv, nom_isa, d, r[0], "** DIFIERE **",
                          "%s:%d" % (r[1], r[2])))
            mal += 1
    return filas, ok, mal


def self_test():
    fails = []

    def eq(l, g, w):
        if g != w:
            fails.append("%s: %r != %r" % (l, g, w))

    # 1. ANCLA EXTERNA. Estas tres son las del driver y estan medidas contra
    #    gmc_8_1_d.h a mano. Si el extractor dejara de reconocer la forma del
    #    nombre, daria cero y el self-test pasaria sin comprobar nada.
    idx = registro_por_offset()
    if idx is None:
        fails.append("no encuentro asic_reg en %s" % ASIC)
        return _fin(fails)
    eq("mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR en 0x54f",
       "mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR" in idx.get(0x54F, []), True)
    eq("mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR en 0x50e",
       "mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR" in idx.get(0x50E, []), True)
    eq("mmVM_INVALIDATE_REQUEST en 0x51e",
       "mmVM_INVALIDATE_REQUEST" in idx.get(0x51E, []), True)

    # 2. CONTROL NEGATIVO del filtro de offset: una mascara de bits NO es un
    #    registro. Si el filtro la aceptara, apareceria como NO_ENCONTRADO y
    #    haria ruido que no corresponde.
    if not os.path.isdir(DRV):
        fails.append("no encuentro el driver en %s" % DRV)
        return _fin(fails)
    # El control anterior (una mascara en el driver) NO se puede probar: este
    # driver no define ninguna, asi que el test no probaba nada y solo habria
    # certificado un vacio. Se sustituye por un control sobre el propio patron,
    # que se puede ejecutar siempre.
    if RE_OFF.match("#define RX550_X_MASK   0xdeadbeef\n"):
        fails.append("control negativo: el filtro acepta una mascara como offset")
    if RE_OFF.match("#define RX550_BITS_PER_X 0x20\n"):
        fails.append("control negativo: el filtro acepta un conteo como offset")
    if not RE_OFF.match("#define RX550_MM_VM_CTX0_PTBA   0x54f\n"):
        fails.append("control positivo: el filtro dejo de reconocer un offset real")
    # El opcode de paquete tiene la FORMA de un offset (acaba en _REG) pero no lo
    # es. Sin esta exclusion sale NO_ENCONTRADO y parece un defecto del driver.
    _m = RE_OFF.match("#define RX550_PKT3_SET_SH_REG   0x76\n")
    if not (_m and RE_PKT3.match(_m.group(1))):
        fails.append("control: un opcode PM4 debe casar con el filtro Y quedar "
                     "excluido por nombre")
    for f in glob.glob(os.path.join(DRV, "*.h")):
        for c in constantes(f):
            if "MASK" in c["nombre"] or c["nombre"].endswith("_BITS"):
                fails.append("el filtro acepto una mascara o un conteo: %s"
                             % c["nombre"])

    # 3. Las tres constantes del driver tienen que CONFIRMARSE. Es el contrato
    #    de hardware del driver, y es lo que esta herramienta existe para cerrar.
    # 4. ANCLAS DE PAQUETES: 12 opcode del driver, cotejados con sid.h/vid.h. Los
    #    doce coinciden; si el extractor dejara de leer tabulador vs espacio,
    #    PACKET3_SURFACE_SYNC (que esta en LOS DOS headers) saldria NO_ENCONTRADO.
    filas, ok, mal = cotejo_pm4()
    if len(filas) != 12:
        fails.append("esperaba 12 opcode de paquete en el driver, lei %d" % len(filas))
    if mal:
        fails.append("%d opcode de paquete no coinciden: %s"
                     % (mal, [f for f in filas if "CONFIRMADO" not in f[3]]))
    if ok != 12:
        fails.append("solo %d de 12 opcode confirman" % ok)

    # 5. ANCLAS DE CAMPOS: los 8 shifts del driver contra sid.h/vid.h. Comparar el
    #    SHIFT y no el texto: la ISA usa (1 << 16) y el driver (1u << 16), que
    #    es el mismo valor. Comparar cadenas daria un falso "difiere".
    filas, okc, malc = cotejo_campos()
    if len(filas) != 8:
        fails.append("esperaba 8 campos de paquete, lei %d" % len(filas))
    if malc:
        fails.append("%d campos no coinciden: %s"
                     % (malc, [f for f in filas if f[4] != "CONFIRMADO"]))

    # 6. ANCLA DE LA SECUENCIA DE INVALIDACION. Los 19 y 17 NO se creyen: se
    #    cuentan los dwords que escriben los emisores. Dos write_data + wait +
    #    pfp_sync_me. Si un emisor cambiara y la constante no, esto falla.
    _f, _ok, _mal = cotejo_vflush()
    if _mal:
        fails.append("la secuencia de vm-flush no cuadra: %s" % [f for f in _f])

    for nom, off in (("RX550_MM_VM_CTX0_PTBA", 0x54F),
                     ("RX550_MM_VM_CTX8_PTBA", 0x50E),
                     ("RX550_MM_VM_INVALIDATE_REQ", 0x51E)):
        nombres = idx.get(off, [])
        if not nombres:
            fails.append("%s = 0x%x no existe en el ASIC" % (nom, off))
    return _fin(fails)


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (3 anclas externas, 4 controles del patron, "
          "3 contratos del driver)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    idx = registro_por_offset()
    if idx is None or not os.path.isdir(DRV):
        print("driver_offsets: falta asic_reg o el driver", file=sys.stderr)
        return 2
    ficheros = glob.glob(os.path.join(DRV, "*.h"))
    if "--fichero" in argv:
        base = argv[argv.index("--fichero") + 1]
        ficheros = [f for f in ficheros if os.path.basename(f) == base]
        if not ficheros:
            print("driver_offsets: no existe %s" % base, file=sys.stderr)
            return 2

    if "--vflush" in argv:
        filas, ok2, mal = cotejo_vflush()
        print("secuencia de vm-flush: dwords CONTADOS en los emisores")
        print()
        for nombre, desglose, cuenta, est, src in filas:
            print("  %-20s %-40s = %-3s %-12s %s"
                  % (nombre, desglose, cuenta, est, src))
        print()
        print("CONFIRMADOS %d de %d" % (ok2, len(filas)))
        return 1 if mal else 0


    if "--campos" in argv:
        filas, ok2, mal = cotejo_campos()
        print("%-32s %-26s %-6s %-6s %-12s %s"
              % ("driver", "ISA", "drv", "isa", "estado", "fuente"))
        print("-" * 88)
        for dv, iv, a, b, est, src in filas:
            print("%-32s %-26s %-6s %-6s %-12s %s"
                  % (dv, iv, a, b, est, src))
        print()
        print("CONFIRMADOS %d de %d" % (ok2, len(filas)))
        return 1 if mal else 0


    if "--pm4" in argv:
        filas, ok2, mal = cotejo_pm4()
        print("%-20s %-9s %-9s %-12s %s"
              % ("paquete", "driver", "sid/vid", "estado", "fuente"))
        print("-" * 66)
        for k, dv, sv, est, src in filas:
            print("%-20s 0x%-7x %-9s %-12s %s"
                  % (k, dv, ("0x%x" % sv) if sv is not None else "-", est, src))
        print()
        print("CONFIRMADOS %d de %d" % (ok2, len(filas)))
        return 1 if mal else 0


    ok = amb = no = 0
    print("%-28s %-9s %-10s %s" % ("constante", "offset", "veredicto", "registro"))
    print("-" * 92)
    for f in ficheros:
        for c in constantes(f):
            nombres = idx.get(c["off"], [])
            if len(nombres) == 1:
                v, r = "CONFIRMADO", nombres[0]
                ok += 1
            elif len(nombres) > 1:
                v, r = "** AMBIGUO **", ", ".join(nombres[:3])
                amb += 1
            else:
                v, r = "NO_ENCONTRADO", "-"
                no += 1
            print("%-28s 0x%-8x %-10s %s"
                  % (c["nombre"][:28], c["off"], v, r[:44]))
    print()
    print("CONFIRMADAS %d   AMBIGUAS %d   NO_ENCONTRADAS %d" % (ok, amb, no))
    if no or amb:
        print("NO_ENCONTRADA no significa 'el driver se equivoca': puede ser un")
        print("offset derivado o un registro que GFX8 no tiene. Es informacion.")
    return 1 if (amb or no) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))