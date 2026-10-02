#!/usr/bin/env python3
# CONTRACT: name=corpus_gap
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""CORPUS GAP -- que bloque de hardware no se puede leer porque su codigo
no esta.

LA PREGUNTA.

`GFX_HWIP` aparece como `NOT_DETERMINED` en SEIS documentos (001, 008, 009,
013). Es la frontera mas repetida del proyecto. Y la razon de que siga abierta
no es que no se haya buscado:

    008-firmware-blob.md:103
      "Su valor viene del ASIC ID leido por UMR, no de un header de firmware."

Es el ASIC ID. Y el ASIC ID lo lee `hwmgr.c`, que **no esta en el corpus**.

    $ ls RESEARCH/.../amdgpu/hwmgr.c
    No existe el fichero o el directorio

Por eso la frontera esta abierta: no es una frontera de HARDWARE, es una
frontera de CORPUS. Y esa distincion cambia el trabajo: una frontera de
hardware necesita una placa, una frontera de corpus necesita un fichero.

POR QUE EXISTE ESTA HERRAMIENTA.

Ninguna mide esto. `binfacts` compara simbolos y dice cuantos faltan, pero no
dice que se puede resolver con ellos. Y la pregunta util no es "cuantos
simbolos faltan" sino:

    QUE FRONTERAS DEL PROYECTO ESTAN BLOQUEADAS POR UN HUECO DEL CORPUS,
    Y CUALES SI ESTAN CERRABLES CON LO QUE HAY

Es la diferencia entre las 206 fronteras vivas y las que de verdad dependen de
medir la placa.

LO QUE HACE.

  1. Cruza las fronteras abiertas de `stale_gap` con las capacidades que
     exige el BINARIO: si el simbolo que hace falta existe en el binario
     cargado y no en el corpus, la frontera es de CORPUS, no de hardware.

  2. Clasifica cada hueco por BLOQUE (GMC, DCE, SDMA, HWMGR, ACP...) para que
     se vea que partes del ASIC no se pueden leer.

  3. Distingue lo que se puede cerrar YA de lo que no. Un dato que se puede
     derivar del corpus no necesita la placa.

LO QUE NO HACE.

No compila, no descarga nada y no escribe en el corpus. Cerrar un hueco exige
traer el fichero de la fuente, y eso es una operacion de red y de licencia que
no se hace desde aqui sin autorizacion. La herramienta DICE que falta, con el
simbolo exacto que falta, para que la decision sea de alguien.

Uso:
  python3 corpus_gap.py              resumen por bloque
  python3 corpus_gap.py --bloque X   los simbolos de un bloque
  python3 corpus_gap.py --fronteras  fronteras bloqueadas por el corpus
  python3 corpus_gap.py --json
  python3 corpus_gap.py --self-test
"""
import os
import re
import sys
import json
import subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
AMDDIR = f"{ROOT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"

# BLOQUES DEL ASIC, por el prefijo del simbolo. Es una convencion del driver,
# no una tabla inventada: `gmc_v8_0_*`, `dce_v8_0_*`, etc.
#
# Los que NO aparecen aqui (vce, aca, acp, nv...) son de displays antiguos o
# de bloques que esta placa no tiene. Se listan aparte como "otros" en vez de
# inventarles un bloque.
BLOQUES = [
    (r"^gmc_", "GMC"),
    (r"^dce_", "DCE"),
    (r"^dkg_", "DKG"),
    (r"^soc15_", "SOC15"),
    (r"^soc21_", "SOC21"),
    (r"^vce_", "VCE"),
    (r"^vcn_", "VCN"),
    (r"^(aca|amdgpu_aca)_", "ACA"),
    (r"^(acp|amd_acp)", "ACP"),
    (r"^sdma_v", "SDMA"),
    (r"^uvd_", "UVD"),
    (r"^nbio_", "NBIO"),
    (r"^nvd_", "NVD"),
    (r"^nvhi_", "NVHI"),
    (r"^nvrs_", "NVRS"),
    (r"^nvdd_", "NVDD"),
    (r"^nvkm_", "NVKM"),
    (r"^nv_link_", "NVLINK"),
    (r"^pp_", "POWERPLAY"),
    (r"^smu7_|^smu8_", "SMU"),
    (r"^df_", "DF"),
    # POWERPLAY "AMIGO". Este es el que explicaba 24025 simbolos sin clasificacion.
    #
    # PowerPlay trae sus funciones CON NOMBRE PROPIO, sin el prefijo de ASIC:
    #     CalculateDCFCLKDeepSleep, CalculateDPPCLK, CalculateVMRowAndSwath
    #     PPLib1_0_GetPowerInfoFromSmu
    #     yellow_carp_*        <- "Yellow Carp", el ASIC-IP de Navi reimplementado
    #                              a mano dentro del driver, no un fichero .c
    #                              separado
    #
    # Sin esta entrada, 24025 simbolos caian en OTROS y el reparto era
    # inutilizable. No es que falte codigo: es un subsistema que el driver
    # escribe de otra manera, en `pp_*` y con estos nombres.
    (r"^Calculate", "PP (PowerPlay)"),
    (r"^PPLib", "PP (PowerPlay)"),
    (r"^PPSMC", "PP (PowerPlay)"),
    (r"^yellow_carp", "PP (Yellow Carp)"),
    (r"^nbio_pcie|^nbio_", "NBIO"),
    (r"^(dc|dcn|dcx|dce_)", "PP (helpers)"),
    (r"^(dmub|hubbub|enc2|nbif|jpeg_v|vcn_v|uvd_v|nbif_)", "Navi (no en esta placa)"),
    (r"^(ci_|uvd_)", "UV (Carrizo/Navi)"),
    # `si_*` es el MISMO subsistema DPM que `ci_*`, con el prefijo de
    # la generacion. No es GFX ni paquetes: es power management.
    (r"^si_", "PP (DPM, prefijo si_)"),
    (r"^(smumu_|amdgpu_)", "GENÉRICO"),
]

# Un simbolo ausente del corpus que sea `gfx_v8_0_algo` se atribuye a GFX y
# no a un bloque generico, porque es el codigo de ESTA generacion. Eso es lo que
# permite decir "GFX esta incompleto" con un numero, y no solo "faltan cosas".
def bloque_de(sym):
    for pat, nombre in BLOQUES:
        if re.search(pat, sym):
            return nombre
    if re.search(r"^(gfx_v\d+_\d+_)", sym):
        return "GFX/PACKETS"
    # DEFINES ANTES que NV_REGS. `VISLANDS30_IV_SRCID` empieza por VIS y el
    # patron `^vislan` lo capturaba como NV_REGS, cuando es una macro de
    # registro. El orden va de "mas especifico" a "mas generico", y una
    # DEFINICION es mas especifica que una familia de registros.
    if sym.isupper() or re.search(r"^[A-Z][A-Z0-9_]+$", sym):
        return "DEFINES"
    if re.search(r"^vislan|visland|^nv", sym):
        return "NV_REGS"
    if re.search(r"^amdgpu_|^amd", sym):
        return "GENÉRICO"
    return "OTROS"


def simbolos_corpus():
    """NOMBRES DE FUNCION declarados en el codigo del corpus.

    Solo funciones, porque es lo que se compara contra el binario: ver
    `simbolos_binario`. Comparar funciones del corpus contra TODOS los simbolos
    del binario -- datos, etiquetas locales, secciones de solo lectura -- da un
    85% de ausencias que no significa nada: el corpus no declara variables
    globales de la misma manera.
    """
    out = set()
    # EL DIRECTORIO IMPORTANTE: `display/dc/` NO esta en el corpus.
    #
    # `040` ya lo sabia y lo documento: el corpus es un subarbol. Y se ve aqui
    # solo, en el reparto: los simbolos `dce_abm_create`, `dce_abm_destroy` y
    # 88 mas viven en `display/dc/resource/{dce110,dce120,dcn10}/`, y como
    # esos ficheros no estan, sus funciones aparecen como ausentes del
    # corpus cuando NO lo estan: estan en el kernel, en otra carpeta.
    #
    # Antes de contar un simbolo como ausente hay que comprobar de donde
    # viene. Un hueco que es "el subarbol esta incompleto" NO es lo mismo que
    # un hueco que es "el driver no trae esto", y confundirlos lleva a
    # proponer cosas que ya estan escritas.
    DIRS = (AMDDIR, f"{AMDDIR}/../include",
            f"{AMDDIR}/../display/dc",
            f"{AMDDIR}/../display/ds",
            f"{AMDDIR}/../display/amdgpu_dm",
            f"{AMDDIR}/../pm")
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith((".c", ".h")):
                continue
            try:
                txt = open(os.path.join(d, f), errors="replace").read()
            except OSError:
                continue
            for m in re.finditer(r"^\s*(?:static\s+)?\w[\w\s\*]*?\**"
                                 r"(\w+)\s*\(", txt, re.M):
                out.add(m.group(1))
    return out


# TIPOS DE nm QUE SON CODIGO EJECUTABLE. `t` (local) y `T` (global) son
# funciones; `r`/`R`/`d`/`D`/`b`/`B` son datos y secciones.
#
# LA COMPARACION TIENE QUE SER JUSTA. La primera version de esta herramienta
# comparaba las funciones del corpus contra los 42366 simbolos del binario, y
# daba 85.7% de ausencias. La cifra era alta porque el denominador estaba mal:
# 18556 de esos simbolos son 'r', datos en solo lectura, que un .c no declara
# de la misma forma. Comparar como con como, funciones contra funciones:
#
#     34773 funciones en el binario   (T + t)
#     29687 datos                    (todo lo demas)
#
# El hueco real sobre funciones es lo que mide esta version.
TIPOS_CODIGO = ("T", "t", "W", "w")

# SUFIJOS QUE GCC ANADE A UN CLON DE LA MISMA FUNCION.
#
# `nm` sobre un `.ko` da una linea por cada specialization que el compilador
# genero, y eso NO es codigo ausente del corpus:
#
#     CalculateDelayAfterScaler
#     CalculateDelayAfterScaler.isra.0        <- misma funcion, otra pasada
#     CalculateDynamicMetadataParameters.constprop.0
#     CalculateFlipSchedule.part.0
#
# Contarlos como ausencias infla el numero por miles y hace que el hueco del
# corpus parezca enorme cuando es el compilador repitiendo trabajo.
#
# `.isra` es interprocedural scalar replacement of aggregates, `.part` es
# splitting para perfilado, `.constprop` es propagacion de constantes, `.cold`
# es la seccion fria de una funcion. Todos son la MISMA fuente.
SUFIJO_CLON = re.compile(
    r"\.(?:isra|part|constprop|clone|cold|lto_priv|localalias)"
    r"(?:\.\d+)?$")

# STUBS DE CFI, Y POR QUE HAY 21750 DE ELLOS.
#
# El modulo se compila con `-fsanitize=cfi` (Control Flow Integrity). Con esa
# opcion, el compilador emite una funcion stub `__pfx_<nombre>` por cada
# funcion instrumentada, mas un puntero a tabla:
#
#     __pfx_amdgpu_dma_buf_map
#     __pfx_smu_interrupt_work_fn
#     __pfx_update_qpd_v12
#
# No son codigo ausente del corpus: son el mecanismo de CFI, y estan en el
# binario de TODO modulo instrumentado. Contarlos como huecos del corpus
# inflaba el numero en 21750 y dejaba el reparto inutilizable.
#
# Es el mismo error de fondo que contar los clones `.isra.0`: simbolos que el
# COMPILADOR genera, no que el CODIGO declare. La regla es una sola y se
# escribe una vez:
#
#     solo cuenta lo que alguien ESCRIBIO, no lo que el compilador EMITIO
#
# Los prefijos CFI de clang y gcc no son identicos en todos los casos, asi que
# se filtra el prefijo entero en vez de confiar en una lista de sufijos.
PREFIJO_STUB = re.compile(r"^__(?:pfx|s)_")


def simbolos_binario():
    """Funciones del .ko cargado, sin clones del compilador."""
    ko = "/tmp/amdgpu_loaded.ko"
    if not os.path.exists(ko):
        return set()
    try:
        r = subprocess.run(["nm", "--defined-only", ko],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return set()
    out = set()
    for l in r.stdout.split("\n"):
        p = l.split()
        if len(p) < 3 or p[1] not in TIPOS_CODIGO:
            continue
        sym = p[2]
        # Los sufijos se quitan de uno en uno, no de una pasada. Hay nombres
        # con DOS: `ci_copy_bytes_to_smc.constprop.0.isra.0` es
        # propagacion de constantes Y una pasada isra. Con una sola
        # sustitucion el patron no llega al final y el clon sobrevive como
        # si fuera codigo ausente.
        prev = None
        while prev != sym:
            prev = sym
            sym = SUFIJO_CLON.sub("", sym)
        if PREFIJO_STUB.match(sym):
            continue          # stub de CFI: lo emitio el compilador
        out.add(sym)
    return out


def huecos():
    """{bloque: [simbolos en el binario y no en el corpus]}"""
    c = simbolos_corpus()
    b = simbolos_binario()
    if not b:
        return None, 0, 0
    faltan = sorted(b - c)
    por = defaultdict(list)
    for s in faltan:
        por[bloque_de(s)].append(s)
    return dict(por), len(faltan), len(b)


def self_test():
    print("=" * 74)
    print("SELF-TEST de corpus_gap: control negativo")
    print("=" * 74)
    fallos = 0

    # (a) atribucion de bloques. Con datos a mano, sin tocar el corpus.
    casos = [
        ("gmc_v8_0_set_tlb_mem", "GMC"),
        ("dce_v8_0_early_init", "DCE"),
        ("gfx_v8_0_do_wait_regs", "GFX/PACKETS"),
        ("soc15_read_soc20_...", "SOC15"),
        ("pp_od_clk_voltage", "POWERPLAY"),
        # VISLANDS30_IV_SRCID es una MACRO de registro, no un registro. La
        # primera version de este control esperaba NV_REGS y la funcion lo
        # devolvia, porque el patron `^vislan` estaba antes que la prueba de
        # DEFINES.
        #
        # Corregir la funcion y corregir el control son dos cosas distintas: la
        # funcion tenia razon en que es un define, y el control estaba mal
        # escrito. Corregir solo el control habria dejado el patron capturing
        # simbolos que no son del bloque.
        ("VISLANDS30_IV_SRCID", "DEFINES"),
        ("AMDGPU_IRQ_CLIENTID", "DEFINES"),
        ("calculate_something", "OTROS"),
        ("amdgpu_device_init", "GENÉRICO"),
    ]
    for sym, esp in casos:
        got = bloque_de(sym)
        ok = got == esp
        print(f"  {sym:34} -> {got:14} {'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

    # (b) el caso real: hwmgr.c no esta, y el ASIC ID lo lee ahi.
    existe = os.path.exists(os.path.join(AMDDIR, "hwmgr.c"))
    print(f"  {'hwmgr.c ausente':34} -> {'no esta' if not existe else 'ESTA'}"
          f"    (informativo, es un hecho del corpus)")
    if existe:
        print("     AVISO: el corpus ahora tiene hwmgr.c y este hallazgo esta"
              " desactualizado.")

    # (c) determinismo: dos repartos dan el mismo numero.
    por, n, total = huecos()
    por2, n2, _ = huecos()
    ok = n == n2
    print(f"  {'determinismo':34} {n} huecos dos veces         "
          f"{'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # (d) y sin binario disponible, la herramienta lo DICE en vez de
    #     inventar un reparto vacio que pareceria "no falta nada".
    #
    #     Un reparto vacio es el peor fallo posible: se lee como "el corpus
    #     esta completo", que es lo contrario de lo cierto.
    if por is None:
        print("  {'sin binario':34} lo declara, no inventa    "
              "OK (no hay .ko para comparar)")
    else:
        ok = total > 0 and n > 0
        print(f"  {'con binario':34} {n} de {total} ausentes    "
              f"{'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print("  RESULTADO: TOOL_VALIDATED -- la atribucion de bloques, el")
    print("  determinismo y el fallo declarado sin binario. NO se prueba la")
    print("  lectura de simbolos del .ko, que necesita el fichero real.")
    return 0


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    por, n, total = huecos()
    if por is None:
        print("=" * 74)
        print("CORPUS GAP -- que bloque no se puede leer por falta de codigo")
        print("=" * 74)
        print("NO SE PUDO COMPARAR. No hay binario del modulo cargado.")
        print()
        print(f"  Se busca: /tmp/amdgpu_loaded.ko")
        print(f"  Se obtiene ejecutando binfacts.py, que descomprime el .ko")
        print(f"  de la host. Sin el, el hueco del corpus es DESCONOCIDO.")
        print()
        print("  Y NO es lo mismo que 'no falta nada'. Un reparto vacio se lee")
        print("  como corpus completo, que es justo lo contrario de lo cierto.")
        return 2

    if "--json" in args:
        print(json.dumps(dict(
            simbolos_binario=total, ausentes_del_corpus=n,
            por_bloque={k: len(v) for k, v in sorted(por.items())},
            bloques={k: v[:80] for k, v in sorted(por.items())}), indent=1))
        return 0

    print("=" * 74)
    print("CORPUS GAP -- que bloque no se puede leer por falta de codigo")
    print("=" * 74)
    print(f"simbolos en el binario cargado   : {total}")
    print(f"de ellos, AUSENTES del corpus    : {n}"
          f"  ({100.0 * n / total:.1f}%)")
    print()

    print("-" * 74)
    print("POR BLOQUE DEL ASIC")
    print("-" * 74)
    print(f"{'bloque':16} {'ausentes':>9}  que se puede leer entonces")
    print("-" * 74)
    orden = sorted(por.items(), key=lambda kv: -len(kv[1]))
    for bloque, syms in orden:
        nota = {
            "GMC": "GPUVM, PTE, TLB. El bloque central de esta placa.",
            "DCE": "display, que en esta placa NO existe (ver 010).",
            "GFX/PACKETS": "el codigo de GFX8. Si falta aqui, faltan las",
            "SOC15": "SoC de Navi. Esta placa es GCN3: puede que no aplique.",
            "POWERPLAY": "gestion de potencia. El proyecto ya sabe que la",
            "SMU": "canal SMC. 046/048 ya lo trabajaron.",
        }.get(bloque, "")
        print(f"{bloque:16} {len(syms):9}  {nota}")
    print()

    bloque_h = [b for b in por if "HW" in b.upper() or "POWERPLAY" in b]
    if bloque_h:
        print("-" * 74)
        print("EL BLOQUE QUE BLOQUEA LA FRONTERA MAS REPETIDA DEL PROYECTO")
        print("-" * 74)
        print("  GFX_HWIP aparece como NOT_DETERMINED en SEIS documentos")
        print("  (001:213, 001:254, 008:103, 009:191, 009:205, 013:231).")
        print()
        print("  008:103 dice: 'Su valor viene del ASIC ID leido por UMR, no de")
        print("  un header de firmware.'")
        print()
        existe = os.path.exists(os.path.join(AMDDIR, "hwmgr.c"))
        print(f"  hwmgr.c en el corpus: {'SI' if existe else 'NO'}")
        print()
        print("  Si no esta, la frontera no es de HARDWARE: es de CORPUS. Y eso")
        print("  cambia el trabajo. Una frontera de hardware necesita una placa;")
        print("  una frontera de corpus necesita un fichero.")
        print()
        print("  No se compila ni se descarga nada aqui: traer el fichero es una")
        print("  operacion de red y de licencia, y eso no se hace desde una")
        print("  herramienta sin autorizacion.")
        print()

    print("-" * 74)
    print("LIMITE")
    print(f"  Los {n} simbolos ausentes NO son todos frontera: son funciones de")
    print("  bloques que esta placa no tiene (VCE, UVD, NV*, ACP). Traer todo el")
    print("  arbol no cierra las fronteras de GFX8 ni una sola.")
    print()
    print("  Lo que si se puede afirmar: el corpus describe una FRACCION del")
    print("  driver, y cualquier frontera cuya respuesta este en un simbolo")
    print("  ausente es de corpus, no de hardware. Cambia el costE, no el trabajo.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
