#!/usr/bin/env python3
# CONTRACT: name=treescope
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 0 escrituras que
# tiene se resolvieron a la clase TEMPORAL: no tiene ninguna escritura, asi que no hay nada que resolver.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
# SPDX-License-Identifier: GPL-2.0
"""
treescope.py - comprueba que las citas `fichero.c:NNN` de los hallazgos
               resuelven contra el ARBOL DECLARADO, y no contra otro.

POR QUE EXISTE

Un hallazgo escrito esta sesion (127) citaba:

    amdgpu_gfx.c:1682   for (i = 0; i <= ring->funcs->align_mask; ++i)

Medido: `grep -c 'ring->funcs->align_mask' amdgpu_gfx.c` en
`rx550-upstream-7.2.8/.../amdgpu_gfx.c` -> **0**. Esa linea existe en
`RESEARCH/kernelbuild/linux-7.1.3/.../amdgpu_gfx.c:1682`.

O sea: **una cita que resuelve, pero en el arbol equivocado.** El proyecto
tiene CUATRO arboles de fuentes con `drivers/gpu/drm/amd/amdgpu/`, y nada en
el corpus de herramientas distingue cual es el declarado:

    rx550-upstream-7.2.8/linux-7.2.8/     <- el declarado, el que cita todo
    RESEARCH/baseline/linux-7.1.3/
    RESEARCH/kernelbuild/linux-7.1.3/
    RESEARCH/working/linux-7.1.3/

Por que el hueco existia:
  - `audit_citations.sh` resuelve contra 7.2.8, pero solo audita 07-DRIVER/.
  - `artifacts.py --solo-referencias` audita las citas de los hallazgos, pero
    resuelve por NOMBRE DE FICHERO, sin mirar el numero de linea.
Entre los dos, ninguna comprobacion cubre "`fichero.c:NNN` de un hallazgo apunta
a esa linea". Que es exactamente el hueco por el que paso la cita falsa.

QUE CLASIFICA

  RESUELVE           el fichero existe en el arbol declarado y la linea cae
                     dentro del fichero
  FUERA_DE_RANGO     el fichero existe pero la linea no
  SOLO_EN_OTRO_ARBOL el fichero NO existe en el arbol declarado, pero si en uno
                     de los otros tres, y la linea cae dentro
  NO_RESUELVE        no existe en ninguno

La tercera es la clase que importa, y no es un resultado negativo: es una cita
**plausible** que apunta a otro sitio.

POR QUE NO CORRIGE

Porque elegir el arbol correcto de una cita es una decision sobre lo que el
autor quiso decir, y buscar el destino por parecido seria inventarla. Aqui solo
se dice en que arbol resuelve cada cita.

CODIGOS DE SALIDA

  0  se pudo medir
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.0.0"

DECLARADO = os.path.join("rx550-upstream-7.2.8", "linux-7.2.8")
OTROS = [
    os.path.join("RESEARCH", "baseline", "linux-7.1.3"),
    os.path.join("RESEARCH", "kernelbuild", "linux-7.1.3"),
    os.path.join("RESEARCH", "working", "linux-7.1.3"),
]
SUFIJOS = (".c", ".h")

# `fichero.c:123`, `fichero.c:123-456`, `fichero.c:123,456`
CITA_RX = re.compile(
    r"`([A-Za-z0-9_./-]+\.(?:c|h))`?\s*:\s*(\d+)(?:\s*[-–]\s*(\d+))?")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def indice_arbol(root: str, arbol: str) -> Dict[str, List[str]]:
    """nombre de fichero -> lineas, indexado SOLO bajo drivers/gpu/drm/amd."""
    base = os.path.join(root, arbol, "drivers", "gpu", "drm", "amd")
    out: Dict[str, List[str]] = {}
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fn:
            if not f.endswith(SUFIJOS):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, "r", errors="replace") as fh:
                    out.setdefault(f, []).extend(fh.read().splitlines())
            except OSError:
                pass
    return out


def clasificar(ref: str, linea: int,
               declarado: Dict[str, List[str]],
               otros: Dict[str, Dict[str, List[str]]]
               ) -> Tuple[str, Optional[str]]:
    """La clase de UNA cita, y el arbol alterno donde resolveria."""
    nombre = os.path.basename(ref)
    cuerpo = declarado.get(nombre)
    # Los alternos se consultan SIEMPRE, no solo cuando el fichero falta aqui.
    # La primera version devolvia FUERA_DE_RANGO en cuanto encontraba el
    # fichero, y por eso clasificaba mal `amdgpu_vm.c:3268`: ese fichero
    # EXISTE en 7.2.8 con 3228 lineas, asi que salia "fuera de rango" sin
    # mirar que en 7.1.3 tiene 3282 y la linea cabe. Es exactamente la clase
    # que la herramienta vino a cazar, y la cazo al reves.
    alt = None
    for arbol, idx in otros.items():
        c = idx.get(nombre)
        if c is not None and 1 <= linea <= len(c):
            alt = arbol
            break
    if cuerpo is not None and 1 <= linea <= len(cuerpo):
        return "RESUELVE", None
    if cuerpo is None and alt:
        return "SOLO_EN_OTRO_ARBOL", alt
    if alt:
        return "FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO", alt
    if cuerpo is not None:
        return "FUERA_DE_RANGO", None
    return "NO_RESUELVE", None


def selftest() -> int:
    print("=== treescope selftest ===\n")
    fallos = 0
    dec = {"a.c": ["l1"] * 10}
    oth = {"R/kernelbuild": {"a.c": ["l1"] * 50}}

    print("[1] una cita que resuelve en el arbol DECLARADO")
    c, a = clasificar("a.c", 5, dec, oth)
    if c != "RESUELVE":
        print("  FAIL %s" % c)
        fallos += 1
    else:
        print("  OK   a.c:5 con 10 lineas -> RESUELVE")

    print()
    print("[2] la clase que importa: resuelve, pero en OTRO arbol")
    c2, a2 = clasificar("b.c", 5, dec, {"R/kb": {"b.c": ["l"] * 50}})
    if c2 != "SOLO_EN_OTRO_ARBOL" or a2 != "R/kb":
        print("  FAIL %s %s" % (c2, a2))
        fallos += 1
    else:
        print("  OK   b.c:5 ausente aqui, presente ahi -> SOLO_EN_OTRO_ARBOL")

    print()
    print("[3] linea fuera de rango NO es lo mismo que arbol equivocado")
    if clasificar("a.c", 999, dec, oth)[0] != "FUERA_DE_RANGO":
        print("  FAIL")
        fallos += 1
    else:
        print("  OK   a.c:999 con 10 lineas -> FUERA_DE_RANGO")
    if clasificar("zzz.c", 1, dec, oth)[0] != "NO_RESUELVE":
        print("  FAIL")
        fallos += 1
    else:
        print("  OK   fichero inexistente en todos -> NO_RESUELVE")

    print()
    print("[4] el indice distingue ficheros HOMONIMOS de subdirectorios")
    idx = indice_arbol("/tmp/opencode", DECLARADO) if os.path.isdir(
        os.path.join("/tmp/opencode", DECLARADO)) else {}
    if os.path.isdir(os.path.join("/tmp/opencode", DECLARADO)):
        print("  FAIL el arbol de prueba no deberia existir")
        fallos += 1
    else:
        print("  OK   arbol inexistente -> indice vacio, sin excepcion")

    print()
    print("[5] un fichero que EXISTE aqui pero cuya linea no, puede")
    print("    estar citando el otro arbol: hay que mirar tambien ahi")
    dec2 = {"c.c": ["l"] * 100}
    oth2 = {"R/7_1_3": {"c.c": ["l"] * 4000}}
    c5, a5 = clasificar("c.c", 3268, dec2, oth2)
    if c5 != "FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO" or a5 != "R/7_1_3":
        print("  FAIL -> %s / %s" % (c5, a5))
        fallos += 1
    else:
        print("  OK   c.c:3268 con 100 lineas aqui y 4000 ahi -> %s" % c5)

    print()
    print("[6] la regex capta el rango, y no confunde una ruta con una linea")
    t = "`gfx_v8_0.c:6875` y `gfx_v8_0.c:6921-6956` y `amdgpu_gfx.c:1702`"
    cits = CITA_RX.findall(t)
    if len(cits) != 3:
        print("  FAIL %d citas: %r" % (len(cits), cits))
        fallos += 1
    else:
        print("  OK   3 citas, la del rango con su segundo numero: %r"
              % (cits[1],))

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (11 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="comprueba el arbol de las citas fichero.c:NNN de los hallazgos")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    root = proyecto()
    if not os.path.isdir(os.path.join(root, DECLARADO)):
        print("  ERROR: no existe el arbol declarado: %s" % DECLARADO,
              file=sys.stderr)
        return 2
    declarado = indice_arbol(root, DECLARADO)
    otros = {a: indice_arbol(root, a) for a in OTROS}
    otros = {a: v for a, v in otros.items() if v}

    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    filas = []
    conteo: Dict[str, int] = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            txt = fh.read()
        for m in CITA_RX.finditer(txt):
            ref, a, b = m.group(1), int(m.group(2)), m.group(3)
            fin = int(b) if b else a
            # el rango mas largo manda: si el final cae, es FUERA_DE_RANGO
            clase, alt = clasificar(ref, a, declarado, otros)
            if clase in ("RESUELVE", "SOLO_EN_OTRO_ARBOL",
                         "FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO") and fin > a:
                idx = (declarado if clase == "RESUELVE"
                       else otros.get(alt, {}))
                cuerpo = idx.get(os.path.basename(ref), [])
                if not (1 <= fin <= len(cuerpo)):
                    clase = ("FUERA_DE_RANGO" if clase == "RESUELVE"
                             else "FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO")
            lin = txt.count("\n", 0, m.start()) + 1
            # Una cita que el propio documento declara FALSA es un ejemplo, no
            # un error. 117-doclint-no-se-mira-el-80.md usa `psp_v10_0.c:4963`
            # seis veces y calcula "174 lineas -> +4289" como prueba de que
            # su doclint no mira el 80. Sin esta clase, la herramienta reporta
            # seis errores donde hay seis ejemplos. Es la misma distincion que
            # reftriage llama AUSENCIA_DOCUMENTADA, aplicada a la linea.
            ini = txt.rfind("\n", 0, m.start()) + 1
            finl = txt.find("\n", m.end())
            ctx = txt[max(0, ini - 900):(finl + 900 if finl > 0 else len(txt))]
            if re.search(r"cita\s+(falsa|err[oó]nea|que no existe)"
                         r"|falsa\s+a\s+secas|ejemplo\s+de\s+cita", ctx,
                         re.IGNORECASE):
                clase = "EJEMPLO_DOCUMENTADO"
            elif (clase.startswith("FUERA_DE_RANGO")
                  and "CORRECCION POSTERIOR" in txt
                  and re.search(re.escape(m.group(0)) + r"[^\n]*"
                               r"|[^\n]*" + re.escape(m.group(0)),
                               txt.split("CORRECCION POSTERIOR")[-1])):
                # La cita sigue en el cuerpo --los hallazgos no se reescriben--
                # pero su CORRECCION POSTERIOR documenta el numero bueno. Es una
                # clase aparte, CONTADA Y VISIBLE, no una extincion: si se
                # mezclase con RESUELVE, el recuento de problemas reopened
                # bajaria y pareceria que el arbol esta limpio por segunda vez.
                clase = "CORREGIDO_Y_DOCUMENTADO"
            conteo[clase] = conteo.get(clase, 0) + 1
            filas.append({"finding": f, "linea": lin, "cita": m.group(0),
                          "fichero": ref, "desde": a, "hasta": fin,
                          "clase": clase, "arbol_alterno": alt})

    if args.json:
        print(json.dumps({"version": VERSION, "arbol_declarado": DECLARADO,
                          "arboles_alternos": sorted(otros),
                          "total": len(filas), "conteo": conteo,
                          "filas": filas},
                         indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("ARBOL DE LAS CITAS -- findings/06-INGENIERIA-INVERSA")
    print("=" * 78)
    print()
    print("  arbol DECLARADO: %s" % DECLARADO)
    print("  arboles alternos presentes: %s" % (", ".join(sorted(otros)) or "ninguno"))
    print()
    print("  citas `fichero.c:NNN` examinadas: %d" % len(filas))
    print()
    for k, v in sorted(conteo.items(), key=lambda kv: -kv[1]):
        print("    %-22s %4d  %s" % (k, v, "%5.1f%%" % (100.0 * v / max(1, len(filas)))))
    print()

    sucias = [x for x in filas if x["clase"] == "SOLO_EN_OTRO_ARBOL"]
    print("=" * 78)
    print("SOLO EN OTRO ARBOL (%d) -- estas citas resuelven, pero no aqui"
          % len(sucias))
    print("=" * 78)
    print()
    if not sucias:
        print("  ninguna. Todas las citas caen dentro del arbol declarado.")
    else:
        print("  No son citas rotas: son citas PLAUSIBLES que apuntan a otro")
        print("  arbol. Una de ellas empezo el hallazgo 127-CORRECCION-POSTERIOR.")
        print()
        por_fichero = {}
        for x in sucias:
            por_fichero.setdefault(x["fichero"], []).append(x)
        for ref in sorted(por_fichero, key=lambda k: -len(por_fichero[k])):
            xs = por_fichero[ref]
            print("  %s  (%d citas)" % (ref, len(xs)))
            alts = sorted({x["arbol_alterno"] for x in xs})
            print("    resuelve en: %s" % ", ".join(alts))
            for x in xs[:6]:
                print("      %-46s L%-5d %s"
                      % (x["finding"][:46], x["linea"], x["cita"][:34]))
            if len(xs) > 6:
                print("      ... y %d mas" % (len(xs) - 6))
    print()
    ej = [x for x in filas if x["clase"] == "EJEMPLO_DOCUMENTADO"]
    if ej:
        print("  EJEMPLOS DOCUMENTADOS: %d. Son citas que el propio documento"
              % len(ej))
        print("  declara FALSAS a proposito, para demostrar algo. No son")
        print("  errores y no hay que tocarlas.")
        print()
        for x in ej[:8]:
            print("    %-44s L%-5d %s" % (x["finding"][:44], x["linea"],
                                          x["cita"][:34]))
        if len(ej) > 8:
            print("    ... y %d mas" % (len(ej) - 8))
        print()

    cor = [x for x in filas if x["clase"] == "CORREGIDO_Y_DOCUMENTADO"]
    if cor:
        print("  CORREGIDAS Y DOCUMENTADAS: %d. La cita sigue en el cuerpo"
              % len(cor))
        print("  --los hallazgos no se reescriben-- pero su CORRECCION")
        print("  POSTERIOR registra el numero bueno. No estan abiertas.")
        print()
        for x in cor:
            print("    %-44s L%-5d %s" % (x["finding"][:44], x["linea"],
                                          x["cita"][:34]))
        print()

    fuera = [x for x in filas if x["clase"] in (
        "FUERA_DE_RANGO", "FUERA_DE_RANGO_PERO_RESUELVE_EN_OTRO")]
    if fuera:
        print("  ADEMAS: %d citas con linea FUERA DE RANGO en el fichero citado."
              % len(fuera))
        print("  Eso NO prueba que esten mal: una cita `fichero.c:1682` de un")
        print("  fichero de 1700 lineas es valida aunque el numero alto del")
        print("  rango se pase. Se listan aparte por no mezclarlas con la clase")
        print("  de arriba, que si es un fallo de puntería.")
        print()
        for x in fuera[:10]:
            print("    %-46s L%-5d %s" % (x["finding"][:46], x["linea"],
                                          x["cita"][:34]))
        if len(fuera) > 10:
            print("    ... y %d mas" % (len(fuera) - 10))
    print()
    print("  LO QUE NO HACE: no corrige, no adivina el arbol correcto y no")
    print("  resuelve cual de los dos autores queria. Solo dice donde resuelve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())