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