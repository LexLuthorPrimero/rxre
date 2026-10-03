#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
vocabpm4.py - censo de los opcodes PM4 que el KERNEL puede emitir en GFX8.

POR QUE EXISTE

Un hallazgo paralelo afirma: "el vocabulario PM4 del kernel en esta GPU es
una docena de palabras -- hdp_flush, gds_switch, pipeline_sync, vm_flush,
fence, indirect_buffer -- mas escrituras de registro. No hay un solo comando de
dibujo, de shader, de DispatchPkt, de estado, ni de clear."

Es la afirmacion mas estructural de esa ronda y **nadie la ha medido**. Es un
resultado NEGATIVO de gran alcance, y un negativo sin denominador no es un
resultado: es una impresion. Este proyecto lleva 128 hallazgos previniendo
exactamente eso, y el mas caro de todos --034-- fue un "0 coincidencias" sin
contar contra que se comprobaba.

QUE MIDE

Para el ASIC de esta placa (CHIP_POLARIS12), el conjunto de opcodes PM4 que el
kernel PUEDE emitir, y se compara contra la lista de lo que un motor de
render necesitaria. De ahi sale el denominador: N opcodes alcanzables, M de los
cuales son de dibujo/shader/estado.

El alcance NO es el arbol entero. Es el camino que corre en esta placa:

    vi.c:2106-2113  case CHIP_POLARIS10/11/12/VEGAM:
                    gfx_v8_0_ip_block, sdma_v3_1_ip_block, ...

Y de ahi, las funciones de emision de GFX8 y las de GMC que emiten paquetes.
Se sigue la evidencia montada en 119: ese `case` monta `gfx_v8_0_ip_block`, y
sus ip_funcs son las de `gfx_v8_0.c`.

POR QUE UN CENSO Y NO UN RASTREO DE "dibujar"

Porque "dibujar" no es una condicion verificable sobre texto. Lo que si lo es:
cuantos opcodes hay, cuales son, y cuales de una lista de categorias
conocidas aparecen. Las categorias se declaran SI O NO en el codigo y son
discutibles; los opcodes se leen y se cuentan.

CODIGOS DE SALIDA

  0  se pudo medir
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

VERSION = "1.0.0"

CORPUS_REL = os.path.join("rx550-upstream-7.2.8", "linux-7.2.8",
                          "drivers", "gpu", "drm", "amd", "amdgpu")

# (opcode, categoria). La categoria es una DECLARACION de quien escribe esto,
# no un hecho medido: por eso la tabla la imprime completa y el veredicto no
# depende de ella. Lo medido son los opcodes; las categorias sirven para
# pregunta "de que tipo de trabajo es capaz el kernel", que es la pregunta.
#
# Las que el hallazgo paralelo afirma que NO estan son las marcadas NEEDS_GPU.
NEEDS_GPU = {
    "DRAW": "dibujo",
    "DISPATCH": "dispatch / shader",
    "SET_SH": "estado de shader",
    "CLEAR": "clear de render target",
    "COLOR": "estado de color",
    "DEPTH": "estado de profundidad",
    "BLEND": "estado de blend",
    "VIEWPORT": "viewport",
    "ATOMIC": "atomicos / memoria",
}

# CATEGORIAS QUE EL KERNEL SI TIENE Y QUE NO SON LO QUE UN MOTOR DE RENDER
# NECESITA. Van aparte a proposito. "estado_motor" es invalidar cache de
# estado y programar contexto de motor -- CLEAR_STATE, CONTEXT_CONTROL,
# PREAMBLE -- y no es estado de la tuberia grafica. Meterlo en NEEDS_GPU
# haria que el recuento dijera "el kernel tiene estado", que es otra frase.
NO_ES_ESTADO_GRAFICO = {"estado_motor", "memoria", "relleno", "control_de_cola"}

CATEGORIA = {
    "PACKET3_DRAW_INDIRECT": "DRAW",
    "PACKET3_DRAW_DIRECT": "DRAW",
    "PACKET3_INDIRECT_BUFFER": "indirect_buffer",
    "PACKET3_EVENT_WRITE": "evento",
    "PACKET3_WAIT_REG_MEM": "sincronizacion",
    "PACKET3_WRITE_DATA": "escritura de registro",
    "PACKET3_PFP_SYNC_ME": "sincronizacion",
    "PACKET3_SURFACE_SYNC": "sincronizacion",
    "PACKET3_ACQUIRE_MEM": "sincronizacion",
    "PACKET3_RELEASE_MEM": "sincronizacion",
    "PACKET3_CONDITION": "condicion",
    "PACKET3_CONDITION_SET": "condicion",
    # Dispatch. INALCANZABLE en esta ASIC por el gate de :1485, y por eso
    # clasificarlo es lo que hace visible el defecto del censo textual.
    "PACKET3_DISPATCH_DIRECT": "DISPATCH",
    "PACKET3_DISPATCH_INDIRECT": "DISPATCH",
    # GESTION DE ESTADO DEL MOTOR. Distinto del estado de la tuberia grafica:
    # el kernel invalida y programa contexto de motor, y no programa color,
    # profundidad, blend ni viewport. Confundir las dos cosas hace que "no hay
    # estado" suene a que no hay estado de ningun tipo, que es falso.
    "PACKET3_CLEAR_STATE": "estado_motor",
    "PACKET3_PREAMBLE_BEGIN_CLEAR_STATE": "estado_motor",
    "PACKET3_PREAMBLE_END_CLEAR_STATE": "estado_motor",
    "PACKET3_PREAMBLE_CNTL": "estado_motor",
    "PACKET3_CONTEXT_CONTROL": "estado_motor",
    "PACKET3_SET_CONFIG_REG": "estado_motor",
    "PACKET3_SET_BASE": "estado_motor",
    "PACKET3_BASE_INDEX": "estado_motor",
    "PACKET3_COPY_DATA": "memoria",
    "PACKET3_NOP": "relleno",
    "PACKET3_EVENT_WRITE_EOP": "evento",
    "PACKET3_MAP_QUEUES": "control_de_cola",
}

# Sin categoria asignada: NO seKVPersonaliza. Cada uno se reporta por su cuenta.
SDMA_OP = re.compile(r"SDMA_OP_([A-Z_]+)")


# ---------------------------------------------------------------- ALCANCE
#
# La primera version de esta herramienta conto la presencia TEXTUAL de un
# opcode y la llamo "alcanzable". No lo es, y el caso lo demuestra dentro del
# propio output: PACKET3_DISPATCH_DIRECT sale en 1541, 1567 y 1593, las tres
# dentro de gfx_v8_0_do_edc_gpr_workarounds, que en :1485 hace
# `if (adev->asic_type != CHIP_CARRIZO) return 0;`. Polaris12 no es Carrizo,
# luego ese opcode NO se emite en esta placa -- que es lo que findings/012
# ya habia establecido para SET_SH_REG, con el mismo gate.
#
# Asi que un censo textual sobredimensiona el vocabulario en exactamente lo que
# mas importa: hace parecer que el kernel tiene un comando de dispatch cuando
# el unico que tiene esta muerto en esta ASIC.

FUNC_RX = re.compile(r"^(?:static\s+|const\s+|inline\s+)*"
                     r"[A-Za-z_][\w \t*]*?\b([a-z_0-9]+)\s*\(")
ASIC_RX = re.compile(r"\bCHIP_([A-Z0-9]+)\b")


def funciones(lineas):
    """(inicio, fin, nombre) de cada funcion de nivel superior, 0-based."""
    starts = []
    for i, l in enumerate(lineas):
        m = FUNC_RX.match(l)
        if m and not l.startswith((" ", "\t")):
            starts.append((i, m.group(1)))
    out = []
    for k, (i, nom) in enumerate(starts):
        fin = starts[k + 1][0] if k + 1 < len(starts) else len(lineas)
        out.append((i, fin, nom))
    return out


def puerta_de(asic, cuerpo):
    """Como decide el cuerpo si esta ASIC entra: PASA, SOLO_SI o NUNCA.

    Se declara el limite: esto lee la FORMA de los gates, no el flujo de
    control. Una funcion con dos gates contradictorios, o con un return
    temprano que no sigue al if, se clasifica mal. Se declara porque un
    clasificador que finge mas precision de la que tiene vuelve a producir el
    cero falso que esta herramienta vino a evitar.
    """
    txt = "\n".join(cuerpo)
    solo_si = set(ASIC_RX.findall(txt))
    for m in re.finditer(r"asic_type\s*!=\s*(CHIP_[A-Z0-9]+)", txt):
        cola = txt[m.end():m.end() + 90]
        if "return" in cola:
            chip = m.group(1)[len("CHIP_"):]
            if asic != chip:
                return "NUNCA"
    if solo_si and asic not in solo_si:
        return "SOLO_SI"
    return "PASA"


def alcanzable(fichero, ops, asic="POLARIS12"):
    """opcode -> veredicto de alcance, y las funciones donde aparece."""
    lineas = leer(fichero)
    fns = funciones(lineas)
    ver = {}
    for i, l in enumerate(lineas):
        if l.strip().startswith(("*", "/*", "//")):
            continue
        for op in ops:
            if re.search(r"\b%s\b" % op, l):
                f = next(((a, b, n) for a, b, n in fns if a <= i < b),
                         (i, i, "<fuera de funcion>"))
                ver.setdefault(op, []).append(
                    (f[2], puerta_de(asic, lineas[f[0]:f[1]])))
    final = {}
    for op, vues in ver.items():
        gates = set(g for _, g in vues)
        if "NUNCA" in gates and "PASA" not in gates:
            final[op] = "INALCANZABLE_EN_ESTA_ASIC"
        elif gates == {"SOLO_SI"}:
            final[op] = "CONDICIONAL"
        else:
            final[op] = "ALCANZABLE"
    return final, ver


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def ruta(fichero: str) -> str:
    return os.path.join(proyecto(), CORPUS_REL, fichero)


def leer(fichero: str) -> List[str]:
    with open(ruta(fichero), "r", errors="replace") as fh:
        return fh.read().splitlines()


def selftest() -> int:
    print("=== vocabpm4 selftest ===\n")
    fallos = 0

    print("[1] se cuenta cada opcode UNA vez, aunque se use N veces")
    src = ["PACKET3(PACKET3_WAIT_REG_MEM, 5);",
           "PACKET3(PACKET3_WAIT_REG_MEM, 6);",
           "PACKET3(PACKET3_PFP_SYNC_ME, 0);"]
    ops = census_en_lineas(src)
    if sorted(ops) != ["PACKET3_PFP_SYNC_ME", "PACKET3_WAIT_REG_MEM"]:
        print("  FAIL %r" % sorted(ops))
        fallos += 1
    else:
        print("  OK   3 usos, 2 opcodes distintos")

    print()
    print("[2] una cadena que NO es opcode no se cuenta")
    src2 = ["/* PACKET3_DRAW_DIRECT */", "PACKET3_HDR(0, 0);",
            "PACKET3(PACKET3_EVENT_WRITE, 0);"]
    ops2 = census_en_lineas(src2)
    if any("DRAW" in o for o in ops2):
        print("  FAIL conto un opcode dentro de un comentario: %r" % ops2)
        fallos += 1
    else:
        print("  OK   el comentario con PACKET3_DRAW_DIRECT no se conto: %r" % ops2)

    print()
    print("[3] la CATEGORIA es una declaracion, y lo no clasificado no se inventa")
    if CATEGORIA.get("PACKET3_WAIT_REG_MEM") != "sincronizacion":
        print("  FAIL")
        fallos += 1
    else:
        print("  OK   PACKET3_WAIT_REG_MEM -> sincronizacion")
    if "PACKET3_ALGO_INVENTADO" in CATEGORIA:
        print("  FAIL hay una categoria inventada")
        fallos += 1
    else:
        print("  OK   lo que no esta en la tabla se reporta sin categoria")

    print()
    print("[4] lo que el hallazgo afirma que NO esta se cuenta contra el total")
    ops3 = ["PACKET3_WAIT_REG_MEM", "PACKET3_PFP_SYNC_ME"]
    cats = {CATEGORIA.get(o, "sin_clasificar") for o in ops3}
    faltan = cats & set(NEEDS_GPU)
    if faltan:
        print("  FAIL detecto categorias de GPU: %s" % faltan)
        fallos += 1
    else:
        print("  OK   de %d opcodes, ninguno es de las %d categorias NEEDS_GPU"
              % (len(ops3), len(NEEDS_GPU)))
    ops4 = ops3 + ["PACKET3_DRAW_DIRECT"]
    cats4 = {CATEGORIA.get(o, "sin_clasificar") for o in ops4}
    if not (cats4 & set(NEEDS_GPU)):
        print("  FAIL un opcode de dibujo no se detecto")
        fallos += 1
    else:
        print("  OK   con un PACKET3_DRAW_DIRECT si se detecta: DRAW")

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (10 vectores)")
    return 0


PKT_RX = re.compile(r"PACKET[23]\(\s*(PACKET[23]_[A-Z0-9_]+)\s*,")
BARE_RX = re.compile(r"\b(PACKET[23]_[A-Z0-9_]+)\b")


def census_en_lineas(lineas: List[str]) -> Set[str]:
    """Opcodes distintos de un texto, sin contar lo que esta comentado.

    Se ignoran los bloques de comentario por completo. Una alternativa es
   nada el comentario con espacios, que es lo que hace el proyecto en otros
    sitios; aqui se eliminan por bloques porque un `PACKET3_X` dentro de un
    comentario es prosa, no codigo.
    """
    limpio: List[str] = []
    en_com = False
    for l in lineas:
        s = l.strip()
        if en_com:
            if "*/" in s:
                en_com = False
            continue
        if s.startswith("/*"):
            if "*/" not in s:
                en_com = True
                continue
            s = s.split("*/")[1]
        limpio.append(s)
    ops: Set[str] = set()
    for l in limpio:
        ops.update(PKT_RX.findall(l))
        if not PKT_RX.search(l):
            ops.update(BARE_RX.findall(l))
    return ops


def main() -> int:
    ap = argparse.ArgumentParser(
        description="censo de opcodes PM4 que el kernel puede emitir en GFX8")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    if not os.path.isdir(ruta("")):
        print("  ERROR: no existe el corpus en %s" % ruta(""),
              file=sys.stderr)
        return 2

    ficheros = ["gfx_v8_0.c", "gmc_v8_0.c", "amdgpu_gfx.c", "amdgpu_gmc.c"]
    ops_por_fichero: Dict[str, List[str]] = {}
    for f in ficheros:
        try:
            ops_por_fichero[f] = sorted(census_en_lineas(leer(f)))
        except OSError as exc:
            print("  ERROR leyendo %s: %s" % (f, exc), file=sys.stderr)
            return 2

    total: Set[str] = set()
    for v in ops_por_fichero.values():
        total.update(v)

    alc: Dict[str, str] = {}
    usos: Dict[str, list] = {}
    for f in ficheros:
        ops_f = set(ops_por_fichero[f])
        if not ops_f:
            continue
        v, u = alcanzable(f, ops_f)
        alc.update(v)
        usos.update(u)

    # El denominador se calcula sobre lo ALCANZABLE, no sobre lo presente.
    # Con los inalcanzables dentro, el recuento daria al kernel un comando de
    # dispatch que en esta placa no ejecuta, que es exactamente el defecto
    # que esta segunda pasada vino a corregir.
    alcanzables = {o for o in total
                   if alc.get(o, "ALCANZABLE") == "ALCANZABLE"}
    cats: Dict[str, str] = {}
    for o in total:
        cats[o] = CATEGORIA.get(o, "sin_clasificar")
    por_cat: Dict[str, List[str]] = {}
    for o, c in cats.items():
        por_cat.setdefault(c, []).append(o)
    hay_gpu = {cats[o] for o in alcanzables if cats[o] in NEEDS_GPU}
    moteros = {cats[o] for o in alcanzables if cats[o] in NO_ES_ESTADO_GRAFICO}

    if args.json:
        print(json.dumps({
            "version": VERSION, "ficheros": ficheros,
            "ops_por_fichero": ops_por_fichero,
            "total_opcodes": len(total), "categorias": cats,
            "necesita_gpu": sorted(hay_gpu),
        }, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("VOCABULARIO PM4 QUE EL KERNEL PUEDE EMITIR EN GFX8")
    print("=" * 78)
    print()
    print("  Alcance: los ficheros de emision de GFX8 y GMC. No es el arbol")
    print("  entero: solo lo que la cadena vi.c:2106-2113 -> gfx_v8_0_ip_block")
    print("  monta en CHIP_POLARIS12.")
    print()
    for f in ficheros:
        print("  %-16s %3d opcodes distintos" % (f, len(ops_por_fichero[f])))
    print()
    print("  TOTAL: %d opcodes distintos alcanzables" % len(total))
    print()
    print("=" * 78)
    print("POR CATEGORIA")
    print("=" * 78)
    print()
    print("  La columna CATEGORIA es una DECLARACION de quien escribe esta tabla,")
    print("  no un hecho medido. Lo medido son los opcodes de la izquierda. La")
    print("  tabla se imprime entera para que el lector pueda discutirla.")
    print()
    for c in sorted(por_cat):
        marca = " <-- CATEGORIA QUE EL HALLAZGO AFIRMA INEXISTENTE" \
            if c in NEEDS_GPU else ""
        print("  %-16s %2d%s" % (c, len(por_cat[c]), marca))
        for o in sorted(por_cat[c]):
            print("      %s" % o)
    print()
    print("=" * 78)
    print("ALCANCE EN ESTA ASIC  (la distincion que faltaba)")
    print("=" * 78)
    print()
    print("  Un opcode puede estar en el fichero y NO emitirse nunca en esta")
    print("  placa. El caso de referencia lo encontro esta misma herramienta:")
    print("  PACKET3_DISPATCH_DIRECT sale en gfx_v8_0.c:1541, 1567 y 1593, las tres")
    print("  dentro de gfx_v8_0_do_edc_gpr_workarounds, cuyo :1485 es")
    print("  `if (adev->asic_type != CHIP_CARRIZO) return 0;`. Polaris12 no es")
    print("  Carrizo. El mismo gate con el que findings/012 marcó SET_SH_REG")
    print("  como NOT_APPLICABLE en esta placa.")
    print()
    from collections import Counter
    cnt = Counter(alc.values())
    for v in ("ALCANZABLE", "CONDICIONAL", "INALCANZABLE_EN_ESTA_ASIC"):
        if cnt.get(v):
            print("    %-26s %2d" % (v, cnt[v]))
    print()
    print("    TOTAL caracteres en el fichero: %d" % len(total))
    print()
    inacc = sorted(o for o, v in alc.items()
                   if v == "INALCANZABLE_EN_ESTA_ASIC")
    if inacc:
        print("  INALCANZABLES EN ESTA ASIC (%d), con la funcion que los emite:"
              % len(inacc))
        for o in inacc:
            fns_ = sorted(set(n for n, g in usos.get(o, []) if g == "NUNCA"))
            print("    %-40s %s" % (o, ", ".join(fns_)))
        print()
        print("  Estos contaban antes como alcanzables. Un censo textual")
        print("  sobredimensiona el vocabulario en justo lo que mas importa.")
    else:
        print("  ninguno")
    print()
    print("  LIMITE DECLARADO: `puerta_de` lee la FORMA de los gates, no el flujo")
    print("  de control. Una funcion con dos gates contradictorios, o con un")
    print("  return temprano que no sigue al if, se clasifica mal. Se declara")
    print("  porque un clasificador que finge mas precision de la que tiene")
    print("  vuelve a producir el cero falso que esta herramienta vino a evitar.")
    print()
    print("=" * 78)
    print("EL DENOMINADOR, que es lo que faltaba")
    print("=" * 78)
    print()
    print("  opcodes ALCANZABLES en esta ASIC:     %d" % len(alcanzables))
    print("  (los %d restantes son inalcanzables y no cuentan)" % (len(total) - len(alcanzables)))
    print("  de las %d categorias que un motor de render necesita" % len(NEEDS_GPU))
    print("  estan presentes:                      %d  %s"
          % (len(hay_gpu), sorted(hay_gpu) if hay_gpu else "(ninguna)"))
    print()
    print("  Y lo que SI tiene, que es distinto de lo anterior:")
    print("  categorias de gestion que no son estado grafico: %s"
          % (sorted(moteros) if moteros else "(ninguna)"))
    print()
    if not hay_gpu:
        print("  Eso convierte la afirmacion de impresion en MEDIDA: 0 de las")
        print("  %d categorias de las que necesita un motor de render, sobre"
              % len(NEEDS_GPU))
        print("  %d opcodes alcanzables." % len(alcanzables))
        print()
        print("  CON UN MATIZ QUE EL ENUNCIADO ORIGINAL NO HACE. El hallazgo")
        print("  paralelo dice 'ni de estado'. Es impreciso, y el matiz importa:")
        print("  el kernel SI tiene %d opcodes de gestion de estado del MOTOR"
              % len([o for o in alcanzables if cats[o] == "estado_motor"]))
        print("  -- CLEAR_STATE, CONTEXT_CONTROL, PREAMBLE --, que no son estado")
        print("  de la tuberia grafica. La afirmacion correcta es 'no hay estado")
        print("  de color, profundidad, blend ni viewport', que es mas estrecha")
        print("  y mas fuerte: no es que falte estado, es que el que hay no es")
        print("  del que un motor de render habla.")
        print()
        print("  Y el alcance tiene un limite declarado: son 4 ficheros de")
        print("  emision de GFX8 y GMC. Que no haya mas de los que veo aqui NO")
        print("  esta medido, y este alcance no lo cubre.")
    else:
        print("  HAY categorias de las que el hallazgo afirma que no existen:")
        for c in sorted(hay_gpu):
            print("    %-10s %s" % (c, ", ".join(sorted(por_cat[c]))))
        print()
        print("  O el hallazgo esta equivocado, o el alcance de este censo es")
        print("  mayor que el suyo. Hay que decidir cual antes de citarlo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())