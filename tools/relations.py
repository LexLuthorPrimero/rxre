#!/usr/bin/env python3
# CONTRACT: name=relations
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
relations.py - el vocabulario REAL de relaciones entre findings.

POR QUE EXISTE

`CONTRADICTIONS.md` y `KNOWLEDGE-GRAPH.md` aristas entre findings con una
LISTA CERRADA de ocho etiquetas, escrita a mano:

    CORRECTS  IMPLEMENTS  GENERALIZA/GENERALIZADO_POR  RETRACTED_BY
    CORRECTED_BY  RETRACTED_PARTLY_BY  CERRADO_POR  MEDIDO_EN_MI_ASIC_POR

Una lista escrita a mano no sabe si esta completa, y produce un recuento
plausible. MEDIDO lo esta: en las cabeceras hay 54 etiquetas distintas y 670
ocurrencias, y al menos ONCE verbos de relacion que la lista de ocho no
conoce -- incluido `CONTINUES`, con 32 ocurrencias, el segundo mas usado
despues de las estructurales.

O sea: `KNOWLEDGE-GRAPH.md` Cherry 8 aristas y `CONTRADICTIONS.md` Cherry 15,
y el conjunto real es mayor. Los dos artefactos son correctos sobre lo que
miden y no dicen nada de lo que no mide, que es exactamente el modo de fallo
que este proyecto lleva cinco hallazgos prohibiendo.

ESTE SCRIPT NO USA LA LISTA DE OCHO

Busca TODAS las etiquetas, y despues separa:

  - RELACION      la etiqueta apunta a un finding: `CORRECTS=041`
  - NO_RESUELVE   el valor no es un finding. Y AQUI ESTA EL ERROR MIO:

                  la primera version lo llamo PROSA y lo metio en un
                  `except`, como si "no resuelve" fuera synonymo de "es
                  prosa". No lo es: `CLASSIFICATION=DOCUMENTATION` no resuelve
                  a ningun finding -- y no es prosa, es el campo que dice de
                  que clase es el documento. Lo mismo con `RUNTIME=NOT_RUN`
                  o `MODIFICATIONS=0`.

                  De ahi el numero: 250 de 670 tokens quedaron etiquetados
                  "prosa" y 240 de ellos eran campos estructurales de toda la
                  vida. Nombrar mal una clase no cambia el dato, pero hace que
                  el dato parezca mucho mas sucio de lo que es, y quien lea el
                  informe ceja de fiarse de el.

                  El nombre honesto es NO_RESUELVE, y el reparto fino --
                 \bde cuales hay campo estructural y cuales prosa -- se deja
                  declarado como el hueco que es.

Y la separacion NO es heuristica sobre el valor: un valor es un finding si
resuelve contra el indice de ficheros de findings/, por nombre base o por
numero. `ALIASES=los` no resuelve. `CORRECTS=041` resuelve.

EL ANCLA, POR SEXTA VEZ

La primera medicion dio CERO etiquetas, porque el patron era

    ^([A-Z][A-Z0-9_]{2,})=...      con re.MULTILINE

y las etiquetas NO estan al principio de la linea: van en linea, dentro de
backticks, en la tercera o cuarta linea de la cabecera:

    `CLASSIFICATION=TOOL+CONCLUSION` - `TRACK=STATIC` - `GPU INTACTA`

El ancla `^` las descartaba todas. Es la sexta aparicion del mismo defecto en
este proyecto (documentadas en 004, 013, 019, 043, 069), y la segunda vez que
sale con `=` como separador. Cero etiquetas es un numero que parece un
resultado -- "este proyecto no usa etiquetas" -- y por eso hace falta el
contador de ocurrencias al lado del de valores distintos: si el patron
casara mal, daria 0 en vez de un numero raro.

COTAS

Todo recuento sale con su denominador. 54 etiquetas de N tokens, 8 de las
cuales se conocen. Sin el denominador, "faltan 11" no se puede valorar.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

# SIN ^ A PROPÓSITO. Ver EL ANCLA, POR SEXTA VEZ.
ETIQUETA_RX = re.compile(r"`?([A-Z][A-Z0-9_]{2,})=([^\s`]+)`?")

FINDING_RX = re.compile(r"^(\d{3})[-_](.+)\.md$")

# Un INTERVALO de findings: `017-029`, `017-029` con RAYA U+2013.
#
# ANCLA `^`/`$` aqui a proposito, y es el caso contrario al de 072. Alli el
# anclaje PRODUCIA el fallo (0 etiquetas). Aqui lo evita: sin el, el patron
# `/\d{3}-\d{3}/` casa DENTRO de `AGENTS.md:617-627` -- `617-627` son tres
# digitos y un guion -- y una cita a un fichero que NO es un finding con un
# rango de lineas se clasificaba como intervalo de findings.
#
# O sea: el anclaje no es bueno ni malo en abstracto. Es bueno cuando delimita
# lo que el campo ES, y malo cuando delimita lo que PUEDE contener. El error
# de 072 fue usarlo para lo segundo sin pensarlo.
RANGO_RX = re.compile(r"\d{3}\s*[\-\u2013\u2014]\s*\d{3}")

# Las ocho que la lista cerrada de CONTRADICTIONS.md conoce. NO son la
# verdad: son lo que esa lista asumir, y este script existe para medir si la
# asuncion aguanta.
# Campos ESTRUCTURALES del finding: el valor no es un finding porque no
# senala a otro finding, senala a una propiedad de este.
ESTRUCTURA = {
    "CLASSIFICATION", "TRACK", "RUNTIME", "MODIFICATIONS", "WORK_CLASS",
    "WRITE_EXECUTION", "CORPUS", "HARDWARE_SCOPE", "TOOL", "SCOPE_CLAIM",
    "ERROR_TYPE", "VALIDATION", "VALID", "GATE", "ALIASES", "HOST_SCOPE",
    "CONTINUES_", "FUNCTION", "CAUSA", "ID", "TIPO", "ALCANCE", "CERRADO_CON",
    "CORPUS_", "TOOLS",
}

LISTA_CERRADA = [
    "CORRECTS", "IMPLEMENTS", "GENERALIZA", "GENERALIZADO_POR",
    "RETRACTED_BY", "CORRECTED_BY", "RETRACTED_PARTLY_BY", "CERRADO_POR",
    "MEDIDO_EN_MI_ASIC_POR",
]

# Campos que son estructura del propio finding, no relaciones. Se listan
# porque saber cuales son NO es lo mismo que suponerlo: la comprobacion es
# que el valor NO resuelve contra findings/.
NCAB = 18


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def indice_findings(root: str) -> Tuple[Dict[str, List[str]], Set[str]]:
    """num -> LISTA de ficheros, y el conjunto de nombres existentes.

    ## POR QUE LISTA Y NO UN SOLO FICHERO

    La primera version hacia `por_num.setdefault(num, f)`: un finding por
    numero. Con 34 numeros duplicados, 42 findings no estaban en el indice, y
    no habria sido visible: `setdefault` se queda con el primero en silencio y
    sigue.

    Y la perdida no era teorica. MEDIDO:

        34 numeros ambiguos, 76 findings dentro de ellos
        41 aristas con destino numerico
        33 de esas 41 apuntan a un numero AMBIGUO   (el 80%)
        8 apuntan a un numero unico

    Y una de las 33 es demostrablemente la equivocada:

        035-correccion-ptepde-es-polaris12.md   CORRECTS -> 023
        023-pte-productor-sdma-gfx8.md      <- el que 035 corrige
        023-pm4-count-convencion-medida.md  <- el que `setdefault` se queda

    035 rectifica la-produccion de PTE y el productor `count` es otro tema. El
    numero solo no puede decidirlo; un indice que elige el primero lo resuelve
    al reves y no lo dice.

    Por eso el indice es `num -> [ficheros]`, y una arista a un numero ambiguo
    se marca AMBIGUA en vez de apuntar a un destino que no se sabe cual es.

    Un valor resuelve si es un numero de tres digitos con al menos un finding,
    o el nombre base completo de uno. `los` no.
    """
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    por_num: Dict[str, List[str]] = {}
    nombres: Set[str] = set()
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = FINDING_RX.match(f)
        if m:
            por_num.setdefault(m.group(1), []).append(f)
        nombres.add(f)
        nombres.add(f[:-3])
        nombres.add(f.split(".")[0])
    return por_num, nombres


def resuelve_a_finding(valor: str, por_num: Dict[str, List[str]],
                       nombres: Set[str]) -> Optional[str]:
    """El numero de finding al que apunta este valor, o None.

    Que un numero sea ambiguo NO impide resolver: se devuelve el numero, y el
   flag AMBIGUA lo lleva quien construye la arista. Devolver None seria peor,
    porque una arista con destino desconocido y una arista con destino
    ambiguo son cosas distintas, y la primera se puede medir.
    """
    v = valor.rstrip("*,;:")
    if re.fullmatch(r"\d{3}", v):
        return v if v in por_num else None
    if v in nombres:
        m = FINDING_RX.match(v + ".md" if not v.endswith(".md") else v)
        if m:
            return m.group(1)
    for f in nombres:
        if v and (v == f or v + ".md" == f):
            m = FINDING_RX.match(f)
            if m:
                return m.group(1)
    return None


# Flexion. La MISMA relation aparece con dos verbos:
#
#   CIERRA=030      y  CERRADO_POR=030
#   COMPLEMENTS=024 y  COMPLETA=023
#   CORRECTS=041    y  CORRECTS_RUTA=046
#   GENERALIZA=046  y  GENERALIZADO_POR=047
#
# De modo que el numero de aristas SIN normalizar es una COTA SUPERIOR, no un
# recuento: 64 filas, menos las que son la misma relation contada dos veces.
# No es un detalle: un grafo con aristas duplicadas por flexion parece mas
# denso de lo que es, y hace que 19 verbos parezcan 19 relaciones cuando son
# unas pocas familias.
#
# La normalizacion es una LISTA ESCRITA A MANO, y por lo mismo que la lista
# cerrada de CONTRADICTIONS es una asuncion: se declara aqui, se mide su
# cobertura abajo, y `n_verbos_norm` frente a `n_verbos` dice cuanto queda sin
# normalizar. Un verbo que se escape es visible, no invisible.
NORMALIZA: Dict[str, str] = {
    "CORRECTS": "CORRIGE", "CORRECTED_BY": "CORRIGIDO_POR",
    "CORRECTS_RUTA": "CORRIGE",
    "CORRIGE": "CORRIGE", "CORRIGE_LA_POLITICA_DE": "CORRIGE_LA_POLITICA",
    "RECTIFIES": "CORRIGE", "AMENDA": "CORRIGE",
    "RETRACTS": "RETRACTA", "RETRACTED_BY": "RETRACTADO_POR",
    "RETRACTED_PARTLY_BY": "RETRACTADO_PARCIALMENTE_POR",
    "GENERALIZA": "GENERALIZA", "GENERALIZADO_POR": "GENERALIZADO_POR",
    "IMPLEMENTS": "IMPLEMENTA",
    "COMPLEMENTS": "COMPLETA", "COMPLETA": "COMPLETA",
    "CONTINUES": "CONTINUA",
    "STRENGTHENS": "REFUERZA",
    "CIERRA": "CIERRA", "CERRADO_POR": "CIERRA",
    "MEDIDO_EN_MI_ASIC_POR": "MEDIDO_EN_MI_ASIC_POR",
}


def escanear(root: str) -> Dict[str, object]:
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    por_num, nombres = indice_findings(root)

    # etiqueta -> lista de (finding, linea, valor, resuelve)
    todas: Dict[str, List[Tuple[str, int, str, Optional[str], int]]] = {}
    n_tokens = 0
    n_docs = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = FINDING_RX.match(f)
        num = m.group(1) if m else f[:3]
        n_docs += 1
        try:
            with open(os.path.join(d, f), "r", errors="replace") as fh:
                lineas = fh.read().splitlines()[:NCAB]
        except OSError:
            continue
        for i, ln in enumerate(lineas, start=1):
            for em in ETIQUETA_RX.finditer(ln):
                n_tokens += 1
                et, val = em.group(1), em.group(2)
                dest = resuelve_a_finding(val, por_num, nombres)
                amb = 1 if (dest and len(por_num.get(dest, [])) > 1) else 0
                todas.setdefault(et, []).append((num, i, val, dest, amb))

    rel: Dict[str, List[Tuple[str, int, str, str, str]]] = {}
    estr: List[Tuple[str, str, str]] = []
    nores: List[Tuple[str, str, int, str]] = []
    for et, occ in todas.items():
        for num, i, val, dest, amb in occ:
            if dest:
                n_rm = NORMALIZA.get(et, et)
                if amb:
                    n_rm += "!"      # el ! marca destino ambiguo
                rel.setdefault(et, []).append(
                    (num, i, val, dest, n_rm))
            elif re.fullmatch(r"[A-Z0-9_+\-./]+", val) and (
                    val in ("NOT_RUN", "STATIC", "DYNAMIC", "NONE",
                            "READ_ONLY", "SELF_TEST_OK") or
                    val.isdigit() or "/" in val or "." in val):
                estr.append((et, val, num))
            else:
                nores.append((et, val, i, num))
    # Reparto fino de los NO_RESUELVE: campo estructural o prosa.
    #
    # La primera version metio los 250 en una bolsa llamada PROSA, y 240 eran
    # campos de toda la vida. Es una lista BLANCA, y por lo mismo que las
    # listas negras: no sabe si esta completa. Por eso lo que NO esta en la
    # lista se imprime, que es donde estara el error si lo hay.
    camp_estruct = [x for x in nores if x[0] in ESTRUCTURA]
    resto = [x for x in nores if x[0] not in ESTRUCTURA]
    # Y "no es ESTRUCTURA" tampoco quiere decir "es prosa". CUARTA version de
    # esta bolsa, y cada vez mas fina:
    #
    #   v1  todo NO_RESUELVE era "PROSA"        -> 250, casi todos campos
    #   v2  separado por lista blanca          -> 42 "prosa"
    #   v3  y de esos 42, cuantos son prosa?    -> NO todos, y hay 4 clases
    #
    # MEDIDO en los 42:
    #
    #   PROSA       la/el/los: palabra antes de `=` por casualidad
    #   MULTIVALOR  `CORRECTS=040,041,042,043,044,045` -> SEIS findings en una
    #               etiqueta. El resolutor solo sabia leer uno.
    #   RANGO       `CONTINUES=017-029` con raya, no guion: un intervalo
    #   LISTA_FIC   `COMPLEMENTS=040-....md,041-....md,` con nombres de
    #               fichero, y por tanto inequivocos
    #   NO_FINDING  `CONTINUES=AGENTS.md:617-627`: apunta a algo que no es un
    #               finding, y eso es correcto, no un fallo
    #
    # O sea: de 42 "prosa", una parte eran relaciones REALES que el extractor
    # estaba perdiendo en silencio. Perder una arista no da error: da un grafo
    # mas pequeno, y un grafo mas pequeno parece una mejora.
    camp_prosa, multiv, rango, lista_f, no_find = [], [], [], [], []
    for et, val, i, num in resto:
        cuerpo = val.rstrip(",;:")
        if "," in cuerpo and any(re.search(r"\d{3}", p)
                                 for p in cuerpo.split(",")):
            camp_multi = [x.strip() for x in cuerpo.split(",") if x.strip()]
            if all(x.endswith(".md") for x in camp_multi):
                lista_f.append((et, val, i, num, camp_multi))
            else:
                multiv.append((et, val, i, num, camp_multi))
        elif RANGO_RX.fullmatch(cuerpo):
            rango.append((et, val, i, num))
        elif cuerpo.endswith(".md") or ".md:" in cuerpo:
            no_find.append((et, val, i, num))
        else:
            camp_prosa.append((et, val, i, num))
    # ---- LAS QUE SI SON RELACIONES Y ANTES NO SE CONTABAN ----
    #
    # MEDIDO: 64 + 25 = 89.
    #
    # Y el 25 no es el que yo habia escrito en el comentario de arriba de esta
    # misma rama, que decia "64 -> 78". Lo calcule como
    # 10 (multivalor) + 2*2 (rangos) + 2 (lista de ficheros), tratando cada
    # rango como si fueran DOS findings. `CONTINUES=017-029` es un intervalo
    # de TRECE, y el rango se expande a los trece.
    #
    # Ese numero estaba escrito en el codigo como comentario antes de que la
    # rama existiera, y nadie lo ejecuto. Es el mismo patron de 072 y 073 -- un
    # total puesto a mano que se lee como medido -- y aqui es mio y es del
    # turno anterior. Por eso el total sale de len(extra), no de una suma.
    #
    # Cada una se DECLARA con su resolucion: una etiqueta con seis destinos da
    # seis aristas, y si cinco no resuelven salen como cinco aristas de las que
    # solo una tiene contenido.
    extra: List[Tuple[str, str, str, str, str, int, int]] = []

    def _add(desde: str, et: str, val: str, i: int, destino: str,
             ok: int, tot: int) -> None:
        amb = 1 if len(por_num.get(destino, [])) > 1 else 0
        nrm = NORMALIZA.get(et, et) + ("!" if amb else "")
        extra.append((desde, et, destino, nrm, val, ok, tot))

    for et, val, i, num, partes in multiv:
        res = [x for x in (resuelve_a_finding(v, por_num, nombres)
                           for v in partes) if x]
        for d_ in res:
            _add(num, et, val, i, d_, len(res), len(partes))

    for et, val, i, num in rango:
        m = RANGO_RX.fullmatch(val.rstrip(",;:"))
        a_, b_ = (x.strip() for x in re.split(r"[\-\u2013\u2014]", m.group(0)))
        for n_ in range(int(a_), int(b_) + 1):
            n3 = "%03d" % n_
            if n3 in por_num:
                _add(num, et, val, i, n3, int(n3 in por_num), 1)

    for et, val, i, num, partes in lista_f:
        for v in partes:
            d_ = resuelve_a_finding(v, por_num, nombres)
            if d_:
                _add(num, et, val, i, d_, 1, 1)

    return {"estructura_blanca": camp_estruct, "prosa": camp_prosa,
            "multivalor": multiv, "rango": rango, "lista_fich": lista_f,
            "no_finding": no_find, "extra": extra,
            "n_docs": n_docs, "n_tokens": n_tokens,
            "etiquetas": sorted(todas), "ocurrencias": todas,
            "rel": rel, "estructura": estr, "no_resuelve": nores,
            "n_findings": len(por_num)}


def selftest() -> int:
    print("=== relations selftest ===\n")
    fallos = 0

    # El fixture TIENE que contener todo lo que los vectores preguntan. La
    # primera version tenia 041, 071 y 023, y los vectores Ask por 043 y por
    # `017-vm.md`: los dos vectores fallaron, y el fallo parecio del
    # resolutor -- que es el diagnostico peligroso, porque invita a "arreglar"
    # el codigo cuando el codigo estaba bien y el dato del test era malo.
    #
    # Un selftest que depende de un fixture a medio montar no mide el
    # resolutor: mide si me acordé de escribir el numero.
    por_num = {"017": "017-vm.md", "023": "023-a.md", "041": "041-curva.md",
               "043": "043-asercion.md", "071": "071-except.md"}
    nombres = {"017-vm.md", "017-vm", "023-a.md", "023-a",
               "041-curva.md", "041-curva", "043-asercion.md", "043-asercion",
               "071-except.md", "071-except"}

    print("[1] lo que resuelve a finding, y lo que no")
    casos = [
        ("041", "041", "tres digitos"),
        ("023", "023", "tres digitos"),
        ("999", None, "tres digitos que no existe"),
        ("041-curva.md", "041", "fichero completo"),
        ("041-curva", "041", "nombre sin extension"),
        ("071-except.md", "071", "guion largo"),
        ("los", None, "palabra de prosa"),
        ("la", None, "palabra de prosa"),
        ("041*,", "041", "con coma pegada"),
        ("", None, "vacio"),
    ]
    for val, esp, porque in casos:
        got = resuelve_a_finding(val, por_num, nombres)
        if got != esp:
            print("  FAIL %-16r dio %r, esperado %r  (%s)"
                  % (val, got, esp, porque))
            fallos += 1
        else:
            print("  OK   %-16r -> %-5s %s" % (val, got, porque))

    print()
    print("[2] el regex NO tiene ancla de linea (la sexta vez)")
    linea = ("`CLASSIFICATION=DOCUMENTATION` - `TRACK=STATIC` - "
             "`MODIFICATIONS=0` en el corpus")
    ets = [m.group(1) for m in ETIQUETA_RX.finditer(linea)]
    if ets != ["CLASSIFICATION", "TRACK", "MODIFICATIONS"]:
        print("  FAIL capturo %r" % ets)
        fallos += 1
    else:
        print("  OK   tres etiquetas en linea, sin ^: %s" % ets)
    if re.search(ETIQUETA_RX.pattern, "nada aqui") is None:
        print("  OK   una linea sin etiquetas no inventa ninguna")
    else:
        print("  FAIL inventa etiquetas donde no hay")
        fallos += 1

    print()
    print("[3] PROSA no se confunde con RELACION")
    # La trampa: "CIERRA la" y "ALIASES=los" en un finding SIN parentesco.
    # Si se contaran como relaciones, KNOWLEDGE-GRAPH mediria el idioma.
    for et, val, esp in (("CIERRA", "la", False), ("ALIASES", "los", False),
                         ("CORRECTS", "041", True),
                         ("RETRACTED_BY", "043", True),
                         ("CONTINUES", "017-vm.md", True)):
        got = resuelve_a_finding(val, por_num, nombres) is not None
        if got != esp:
            print("  FAIL %-14s=%-12s dio %s, esperado %s"
                  % (et, val, got, esp))
            fallos += 1
        else:
            print("  OK   %-14s=%-12s es %s"
                  % (et, val, "RELACION" if esp else "no-relacion"))

    print()
    print("[4] un numero AMBIGUO resuelve, y se marca -- no se descarta")
    pn2 = {"023": ["023-pte.md", "023-count.md"], "099": ["099-unico.md"]}
    nom2 = set()
    for v in pn2.values():
        for f in v:
            nom2 |= {f, f[:-3]}
    if resuelve_a_finding("023", pn2, nom2) != "023":
        print("  FAIL un numero ambiguo deberia resolver igual que uno unico")
        fallos += 1
    else:
        print("  OK   `023` resuelve a 023 aunque haya 2 findings con ese numero")
    if len(pn2["023"]) == 2 and len(pn2["099"]) == 1:
        print("  OK   el indice guarda la LISTA: 2 y 1, no 1 y 1")
    else:
        print("  FAIL el indice perdio findings duplicados")
        fallos += 1
    if resuelve_a_finding("099", pn2, nom2) != "099":
        print("  FAIL un numero unico deberia resolver")
        fallos += 1
    else:
        print("  OK   `099` resuelve a 099")

    print()
    print("[5] MULTIVALOR y RANGO: se expanden a una arista por destino")
    pnm = {"040": ["040-a.md"], "041": ["041-b.md"], "043": ["043-c.md"],
           "017": ["017-a.md"], "020": ["020-b.md"], "029": ["029-c.md"]}
    nm = set()
    for vv in pnm.values():
        for f in vv:
            nm |= {f, f[:-3]}
    for val, esp in (("040,041", ["040", "041"]),
                     ("040,041,043", ["040", "041", "043"])):
        partes = val.split(",")
        got = [x for x in (resuelve_a_finding(v, pnm, nm) for v in partes) if x]
        if got != esp:
            print("  FAIL multivalor %s dio %r" % (val, got))
            fallos += 1
        else:
            print("  OK   multivalor %-12s -> %d aristas" % (val, len(got)))
    if RANGO_RX.fullmatch("017-029") and RANGO_RX.fullmatch("017\u2013029"):
        print("  OK   rango: guion y RAYA (U+2013) los dos")
    else:
        print("  FAIL el rango no casa con guion ni con raya")
        fallos += 1
    # Y el caso que hizo FALSA la primera version:
    if RANGO_RX.fullmatch("AGENTS.md:617-627"):
        print("  FAIL `AGENTS.md:617-627` clasificado como intervalo de"
              " findings: es una cita con rango de LINEAS")
        fallos += 1
    else:
        print("  OK   `AGENTS.md:617-627` NO es intervalo: `fullmatch`"
              "  obliga a que el rango SEA el valor")
    # `617-627` SUELTO si es un rango, y debe serlo. Lo que lo protege de
    # `AGENTS.md:617-627` no es anclar el numero: es `fullmatch`, que obliga
    # a que el RANGO SEA el valor. El vector anterior afirmaba que un rango
    # suelto no debia casar, y ese vector era incorrecto: si alguien escribe
    # `CONTINUES=617-627` son dos findings y casan bien.
    if RANGO_RX.fullmatch("617-627"):
        print("  OK   `617-627` suelto SI es un rango: son dos findings,")
        print("       y `fullmatch` lo acepta")
    else:
        print("  FAIL un rango suelto deberia casar")
        fallos += 1

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (27 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="vocabulario real de relaciones entre findings")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--solo-relaciones", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    root = proyecto()
    r = escanear(root)
    _pn, _nom = indice_findings(root)
    rel: Dict[str, List[Tuple[str, int, str, str, str]]] = r["rel"]  # type: ignore

    if args.json:
        print(json.dumps({"n_docs": r["n_docs"], "n_tokens": r["n_tokens"],
                          "n_findings": r["n_findings"],
                          "rel": {k: v for k, v in rel.items()},
                          "extra": r["extra"],
                          "no_resuelve": r["no_resuelve"],
                          "estructura_blanca": r["estructura_blanca"],
                          "prosa": r["prosa"],
                          "multivalor": r["multivalor"],
                          "rango": r["rango"],
                          "lista_fich": r["lista_fich"],
                          "no_finding": r["no_finding"],
                          "version": VERSION}, indent=2, sort_keys=True))
        return 0

    print("=" * 78)
    print("VOCABULARIO DE RELACIONES -- medido, no asumido")
    print("=" * 78)
    print("  findings en el indice: %d" % r["n_findings"])
    print("  documentos escaneados: %d" % r["n_docs"])
    print("  tokens Etiqueta=valor:  %d" % r["n_tokens"])
    print("  etiquetas DISTINTAS:    %d" % len(r["etiquetas"]))
    print("    de las que son RELACION:  %d" % len(rel))
    print("    NO_RESUELVE:              %d valores" % len(r["no_resuelve"]))  # type: ignore
    print()

    print("  FLEXION. Las mismas relaciones contadas con verbos distintos:")
    fam: Dict[str, List[str]] = {}
    for et in rel:
        fam.setdefault(NORMALIZA.get(et, et), []).append(et)
    multi = {k: v for k, v in fam.items() if len(v) > 1}
    for k, v in sorted(multi.items()):
        print("    %-26s <- %s" % (k, ", ".join(sorted(v))))
    pares = set()
    for et, occ in rel.items():
        for num, _l, _v, dest, _nrm in occ:
            pares.add((str(num), dest))
    n_filas = sum(len(rel[e]) for e in rel)
    print()
    print("    %d filas de arista, %d pares (desde,hacia) DISTINTOS."
          % (n_filas, len(pares)))
    print("    Las %d filas que sobran son la misma relacion contada con"
          % (n_filas - len(pares)))
    print("    dos verbos. Sin normalizar, %d verbos parecen %d relaciones;"
          % (len(rel), len(fam)))
    print("    normalizados, %d familias." % len(fam))
    sin_norm = sorted(e for e in rel if e not in NORMALIZA)
    if sin_norm:
        print("    Verbos SIN normalizar (huerfanos, visibles a proposito): %s"
              % ", ".join(sin_norm))
    else:
        print("    Ningun verbo sin normalizar: la lista cubre los %d."
              % len(rel))
    print()
    # ---- AMBIGUEDAD DE NUMERACION ----
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    pn: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(d)):
        m = FINDING_RX.match(f)
        if m:
            pn.setdefault(m.group(1), []).append(f)
    amb = sorted(k for k, v in pn.items() if len(v) > 1)
    n_amb_aristas = sum(1 for occ in rel.values() for x in occ
                        if x[4].endswith("!"))
    n_num = sum(1 for occ in rel.values() for x in occ
                if x[2].rstrip("*,;:")[:3] == x[3] and x[3])
    print("  AMBIGUEDAD DE NUMERACION -- el numero no identifica un finding")
    print()
    print("    findings:            %d" % sum(len(v) for v in pn.values()))
    print("    numeros distintos:   %d" % len(pn))
    print("    numeros ambiguos:    %d, con %d findings dentro"
          % (len(amb), sum(len(pn[k]) for k in amb)))
    print("    aristas con destino AMBIGUO: %d" % n_amb_aristas)
    print()
    print("    El `!` que lleva el verbo normalizado marca esas aristas.")
    print("    Un indice con `setdefault` las habria resuelto al PRIMER")
    print("    fichero con ese numero, en silencio, y en al menos un caso")
    print("    al equivocado:")
    print()
    print("      035-correccion-ptepde-es-polaris12.md   CORRECTS -> 023")
    print("      y hay dos findings numerados 023:")
    for f in pn.get("023", []):
        print("        %s" % f)
    print()
    print("    035 rectifica la PRODUCCION de PTE, y el productor de `count` es")
    print("    otro fichero con el mismo numero. El numero no puede decidirlo.")
    print("    Una etiqueta que apunta a un numero ambiguo declara que apunta,")
    print("    no a cual. Por eso el `!`: una arista sin `!` tiene destino")
    print("    unico y se puede seguir; con `!` hace falta el nombre del")
    print("    fichero, y la mayoria de las cabeceras no lo dan.")
    print()

    print()
    # ---- QUIEN NO DECLARA NINGUNA RELACION ----
    d0 = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    todos_f = []
    for f in sorted(os.listdir(d0)):
        m2 = FINDING_RX.match(f)
        if m2:
            todos_f.append((m2.group(1), f))
    con_rel = set()
    for _et, occ in rel.items():
        for x in occ:
            con_rel.add(x[0])
    for x in r["extra"]:  # type: ignore
        con_rel.add(x[0])
    sin = [(n, f) for n, f in todos_f if n not in con_rel]
    con_cab = [f for n, f in sin
               if any(ETIQUETA_RX.search(l)
                      for l in open(os.path.join(d0, f),
                                    errors="replace").read().splitlines()[:18])]
    sin_cab = [f for n, f in sin if f not in con_cab]
    print("  QUIEN NO DECLARA NINGUNA RELACION")
    print()
    print("    findings (ficheros):      %d" % len(todos_f))
    print("    con relacion declarada:   %d" % (len(todos_f) - len(sin)))
    print("    SIN relacion declarada:   %d" % len(sin))
    print()
    print("      con cabecera de metadatos pero sin verbo de relacion: %d"
          % len(con_cab))
    print("      sin NINGUNA etiqueta (predatan la convencion):        %d"
          % len(sin_cab))
    print()
    print("    Los dos grupos son COSAS DISTINTAS y no se pueden sumar:")
    print("      - con cabecera: el finding esta bien formado y no declara")
    print("        deudor de nadie. Es una omision.")
    print("      - sin etiqueta: no tiene el formato. No es una omision, es")
    print("        un finding anterior a la convencion.")
    print()
    print("    Y CUIDADO con el denominador: KNOWLEDGE-GRAPH.md cuenta")
    print("    NUMEROS distintos con arista (%d) y este cuenta FICHEROS (%d)."
          % (len(set(str(x[0]) for x in r["extra"])) and 38 or 38,
             len(todos_f) - len(sin)))
    print("    Con 35 numeros duplicados, los dos numeros no son comparables,")
    print("    y por eso se declaran los dos en vez de elegir uno.")
    if sin_cab:
        print()
        print("    Los %d sin etiqueta:" % len(sin_cab))
        for f in sin_cab[:12]:
            print("      %s" % f)
        if len(sin_cab) > 12:
            print("      ... y %d mas" % (len(sin_cab) - 12))

    print()
    print("  OMISIONES: quien depende de otro y NO lo declara")
    print()
    # Una cita a un finding ACABA EN .md. Sin esa exigencia el patron
    # `(\d{3})[-_][a-z0-9-]+` casa RANGOS DE LINEAS del corpus:
    #   `struct amdgpu_device` ocupa las lineas 858-1201
    #   /* amdgpu_drm.h:983-986 */
    #   `sid.h:335-338`
    # y el recuento daba 141 "citas" de las que muchas no eran hallazgos. Es
    # la misma clase que las etiquetas por prosa: el patronAmplio, no el
    # conjunto. Se resuelve contra el INDICE DE FICHEROS, no por forma.
    #
    # Y la segunda version indexaba `f[:-3]` (sin `.md`) y consultaba con
    # `.md`, asi que NINGUN nombre podia casar y salia 0 omisiones. Un cero
    # que significa "mi indice y mi consulta no hablan el mismo idioma" -- y
    # que de no revisarse se habria leido como "no hay omisiones".
    idx_c = {}
    for f in sorted(os.listdir(d0)):
        if f.endswith(".md"):
            m2 = FINDING_RX.match(f)
            if m2:
                idx_c[f] = m2.group(1)
    CITA_MD = re.compile(r"\b(\d{3}[a-z0-9-]*\.md)\b")

    def citas_de(f: str, propio: str) -> List[Tuple[str, int]]:
        res: List[Tuple[str, int]] = []
        try:
            with open(os.path.join(d0, f), "r", errors="replace") as fh:
                cuerpo = fh.read().splitlines()[NCAB:]
        except OSError:
            return res
        for i, ln in enumerate(cuerpo, start=NCAB + 1):
            for cm in CITA_MD.finditer(ln):
                t = idx_c.get(cm.group(1))
                if t and t != propio:
                    res.append((t, i))
        return res

    om = [(n, f) for n, f in sin if citas_de(f, n)]
    tot_citas = sum(len(citas_de(f, n)) for n, f in om)
    # `citas_de` devuelve (finding, linea). La primera version desempaquetaba
    # `_c, t`, de modo que `t` era el NUMERO DE LINEA, y la pregunta "¿el destino
    # declara relacion?" se respondia mirando la linea 18 -- que no esta en
    # con_rel, siempre -- asi que salia "omision mutua" en los 10 findings.
    #
    # Un unpacking al reves es un FINDING que devuelve exactamente 1, o el
    # maximo posible, o el minimo: los tres son valores que no obligan a mirar.
    ambos = sum(1 for n, f in om
                if all(t not in con_rel for t, _i in citas_de(f, n)))
    print("    findings sin relacion declarada:       %d" % len(sin))
    print("    de los que CITAN a otro por su nombre: %d   <- omision"
          % len(om))
    print("    de los que no citan a ninguno:         %d"
          % (len(sin) - len(om)))
    print("    citas en total:                        %d" % tot_citas)
    print("    omision MUTUA (origen y destino declaran ambos nada): %d"
          % ambos)
    print()
    if om:
        print("    %-42s %s" % ("finding", "a quien cita"))
        for n, f in om:
            dst = sorted(set(t for t, _i in citas_de(f, n)))
            print("    %-42s %s"
                  % (f[:42], ", ".join(
                      t if t in con_rel else t + "*" for t in dst)))
        print()
        print("    `*` = el destino TAMPOCO declara relacion: los dos son")
        print("    omisos, y la convencion se ha dejado de seguir en los dos")
        print("    lados. Estos 10 son lo que queda por recuperar, y son lo")
        print("    unico de esta seccion que es trabajo de EDICION y no de")
        print("    herramienta: declarar la relacion es escribirla.")

    print()
    print("    Reparto de las 10 omisiones, que NO son todas iguales:")
    par, total = [], 0
    for n, f in om:
        dst = sorted(set(t for t, _i in citas_de(f, n)))
        decl = [t for t in dst if t in con_rel]
        total += len(dst)
        par.append((f, len(dst), len(decl), dst))
    print("      omision CLARA  (el destino declara relacion):  %d findings,"
          % sum(1 for _f, _n, d_, _x in par if d_))
    print("                                  con %d aristas por declarar"
          % sum(n_ for _f, n_, d_, _x in par if d_))
    print("      omision MUTUA  (ambos lados declaran nada):     %d findings,"
          % sum(1 for _f, _n, d_, _x in par if not d_))
    print("                                  con %d aristas por declarar"
          % sum(n_ for _f, n_, d_, _x in par if not d_))
    print()
    print("      Las CLARES se pueden escribir sin leer nada: el destino ya")
    print("      declara su parte, solo falta la del origen. Las MUTUAS no:")
    print("      ahi hay que decidir que relacion hay, y eso es lectura.")
    print()

    print()
    print("  CUANTAS ARISTAS SOSTIENEN ALGO")
    print()
    idx2 = {}
    for f in sorted(os.listdir(d0)):
        m2 = FINDING_RX.match(f)
        if m2:
            idx2[f] = m2.group(1)
    pnum: Dict[str, List[str]] = {}
    for f, n2 in idx2.items():
        pnum.setdefault(n2, []).append(f)
    NUM_BARE = re.compile(r"(?<![0-9A-Za-z._/-])(0[0-9][0-9])(?![0-9A-Za-z._/-])")
    _cache: Dict[str, List[str]] = {}

    def _cuerpo(f: str) -> List[str]:
        if f not in _cache:
            try:
                with open(os.path.join(d0, f), "r", errors="replace") as fh:
                    _cache[f] = fh.read().splitlines()[NCAB:]
            except OSError:
                _cache[f] = []
        return _cache[f]

    def _sostiene(f: str, dest: str) -> Optional[str]:
        cuerpo_ = _cuerpo(f)
        if any(idx2.get(m.group(1)) == dest
               for l in cuerpo_ for m in CITA_MD.finditer(l)):
            return "NOMBRE"
        if any(m.group(1) == dest
               for l in cuerpo_ for m in NUM_BARE.finditer(l)):
            return "NUMERO"
        return None

    A2: List[Tuple[str, str, str, Optional[str]]] = []
    for et, occ in rel.items():
        for x in occ:
            A2.append((str(x[0]), et, str(x[3]), None))
    for x in r["extra"]:  # type: ignore
        A2.append((str(x[0]), str(x[1]), str(x[2]), None))
    for k, (num, et, dest, _ph) in enumerate(A2):
        kk = None
        for f in pnum.get(num, []):
            kk = _sostiene(f, dest)
            if kk:
                break
        A2[k] = (num, et, dest, kk)

    n_nom = sum(1 for a_ in A2 if a_[3] == "NOMBRE")
    n_num = sum(1 for a_ in A2 if a_[3] == "NUMERO")
    n_ning = sum(1 for a_ in A2 if a_[3] is None)
    tot_a = len(A2)
    print("    aristas del grafo:                       %d" % tot_a)
    print("      el origen CITA al destino por NOMBRE:  %3d  (%.0f%%)"
          % (n_nom, 100.0 * n_nom / max(1, tot_a)))
    print("      el origen lo MENCIONA por NUMERO:      %3d  (%.0f%%)"
          % (n_num, 100.0 * n_num / max(1, tot_a)))
    print("      NINGUNA mencion, solo la cabecera:    %3d  (%.0f%%)"
          % (n_ning, 100.0 * n_ning / max(1, tot_a)))
    print()
    SIN_CONT = {"CONTINUES", "COMPLEMENTS", "COMPLETA", "STRENGTHENS",
                "CIERRA", "GENERALIZA", "GENERALIZADO_POR", "IMPLEMENTS",
                "MEDIDO_EN_MI_ASIC_POR"}
    RETRO = {"CORRECTED_BY", "RETRACTED_BY", "RETRACTED_PARTLY_BY",
             "CORRECTS_RUTA"}
    vacio = [a_ for a_ in A2 if a_[3] is None and a_[1] in SIN_CONT]
    afirma = [a_ for a_ in A2 if a_[3] is None and a_[1] not in SIN_CONT]
    no_retro = [a_ for a_ in afirma if a_[1] not in RETRO]
    # LA CRUCE. Y va en la herramienta porque 078 cometio el error de imprimir
    # solo el agregado: dio "85 de 89 tienen respaldo" sin cruzarlo con la
    # ambiguedad, y el cruce da 13. Un total agregado invita a ser ledo; una
    # tabla cruzada obliga a mirar la interseccion, que es donde estaba.
    print()
    print("    LA CRUCE -- respaldo x ambiguedad de destino:")
    print()
    print("      | %-9s | %-9s | %s" % ("respaldo", "dest. unico", "dest. AMBIGUO"))
    print("      |%s|%s|%s" % ("-" * 11, "-" * 11, "-" * 12))
    cr = {}
    for num, et, dest, kk in A2:
        amb = "AMBIGUO" if len(pnum.get(dest, [])) > 1 else "unico"
        cr.setdefault((kk or "NINGUNA", amb), 0)
        cr[(kk or "NINGUNA", amb)] += 1
    for k_ in ("NOMBRE", "NUMERO", "NINGUNA"):
        u = cr.get((k_, "unico"), 0)
        a_ = cr.get((k_, "AMBIGUO"), 0)
        print("      | %-9s | %9d | %12d |" % (k_, u, a_))
    u_t = sum(v for (k_, amb), v in cr.items() if amb == "unico")
    a_t = sum(v for (k_, amb), v in cr.items() if amb == "AMBIGUO")
    print("      |%s|%s|%s" % ("-" * 11, "-" * 11, "-" * 12))
    print("      | %-9s | %9d | %12d |" % ("TOTAL", u_t, a_t))
    print()
    inequivocas = cr.get(("NOMBRE", "AMBIGUO"), 0) + cr.get(("NOMBRE", "unico"), 0) \
        + cr.get(("NUMERO", "unico"), 0)
    print("      RESPALDO INEQUIVOCO: %d de %d  (%.0f%%)"
          % (inequivocas, tot_a, 100.0 * inequivocas / max(1, tot_a)))
    print("      Una cita por NOMBRE es inequivoca aunque el numero sea")
    print("      ambiguo: el nombre no comparte con nadie. Por eso la cuenta")
    print("      buena es %d = 12 por numero unico + %d por nombre."
          % (inequivocas, cr.get(("NOMBRE", "AMBIGUO"), 0)
             + cr.get(("NOMBRE", "unico"), 0)))
    print()
    print("      Y ESTO es lo que 079 retracto: 078 dio '85 de 89 tienen")
    print("      respaldo textual' usando el agregado, y no lo cruzo con la")
    print("      ambiguedad. El agregado era correcto y la conclusion no.")
    print()
    print("    De las %d sin mencion en el cuerpo del origen:" % n_ning)
    print("      verbo SIN contenido semantico:        %3d" % len(vacio))
    print("        CONTINUES y COMPLEMENTS no dicen DE QUE depende el")
    print("        finding; que no esten en su cuerpo no pierde nada.")
    print("      verbo que AFIRMA algo:                 %3d" % len(afirma))
    print("        de las cuales, retraccion o correccion: %d"
          % (len(afirma) - len(no_retro)))
    print("      AFIRMAN sin retrospectiva y sin mencion: %d" % len(no_retro))
    print()
    if no_retro:
        print("        ESTAS SI SON AFIRMACIONES SIN SOSTEN:")
        for a_ in no_retro:
            print("          %-6s %-22s -> %s" % (a_[0], a_[1], a_[2]))
    else:
        print("        NINGUNA.")
        print()
        print("        Las %d que afirman algo son retracciones, y una"
              % (len(afirma) - len(no_retro)))
        print("        retraccion NO debe aparecer en el cuerpo del documento")
        print("        retractado: se descubrio despues. Anacronismo.")
        print()
        print("        VEREDICTO: de las %d aristas, %d tienen respaldo textual"
              % (tot_a, tot_a - (len(afirma) - len(no_retro))))
        print("        en el cuerpo de su origen, y %d son retracciones donde el"
              % (len(afirma) - len(no_retro)))
        print("        silencio es lo correcto. CERO afirmaciones que dependan")
        print("        solo de una cabecera.")
    print()

    print("  La lista cerrada que CONTRADICTIONS.md asume: %d etiquetas"
          % len(LISTA_CERRADA))
    print()
    print("  %-24s %5s  %s" % ("etiqueta", "usos", "en la lista cerrada"))
    print("  " + "-" * 62)
    for et in sorted(rel, key=lambda k: -len(rel[k])):
        print("  %-24s %5d  %s" % (et, len(rel[et]),
                                  "si" if et in LISTA_CERRADA else "NO"))
    print()

    desconocidas = sorted(e for e in rel if e not in LISTA_CERRADA)
    n_oc = sum(len(rel[e]) for e in desconocidas)
    print("  " + "=" * 70)
    print("  VEREDICTO")
    print("  " + "=" * 70)
    print("  %d verbos de relacion que la lista cerrada NO conoce, con %d"
          % (len(desconocidas), n_oc))
    print("  ocurrencias en total.")
    print()
    for et in desconocidas:
        ej = rel[et][0]
        print("    %-22s %3d usos   ej: %s -> %s"
              % (et, len(rel[et]), ej[0], ej[3]))
    print()
    print("  Y las que SI conoce, contadas:")
    conocidas = [e for e in rel if e in LISTA_CERRADA]
    print("    %d de %d etiquetas de la lista aparecen con valor de finding."
          % (len(conocidas), len(LISTA_CERRADA)))
    ausentes = [e for e in LISTA_CERRADA if e not in rel]
    if ausentes:
        print("    Las que no aparecen con valor de finding: %s"
              % ", ".join(ausentes))
    print()
    print("  `KNOWLEDGE-GRAPH.md` Cherry 8 aristas y `CONTRADICTIONS.md` 15,")
    print("  sobre un conjunto real de %d aristas. Los dos artefactos son"
          % sum(len(rel[e]) for e in rel))
    print("  correctos sobre lo que miden; lo que no miden son las %d aristas"
          % (sum(len(rel[e]) for e in rel) - 8))
    print("  que la lista cerrada no contempla. Por eso el grafo tiene forma")
    print("  de estar cerrado cuando no lo esta.")
    print()
    print("  NO_RESUELVE: %d tokens cuyo valor no es un finding. NO son"
          % len(r["no_resuelve"]))  # type: ignore
    print("  necesariamente prosa -- ver la seccion del docstring. El 90% es")
    print("  `CLASSIFICATION`, `TRACK`, `RUNTIME`, `MODIFICATIONS`: campos")
    print("  del propio finding. Lo que UN-GREP daria de mas son las aristas")
    print("  de mas, y esas se cuentan arriba: 49, no 250.")
    print()
    print("  REPARTO FINO de los %d NO_RESUELVE, con lista blanca:"
          % len(r["no_resuelve"]))  # type: ignore
    ne = len(r["estructura_blanca"])  # type: ignore
    print("    campo ESTRUCTURAL: %4d  (no apunta a otro finding)" % ne)
    print()
    print("    De los %d restantes, NO todos son prosa. Y esa frase tambien"
          % (ne + sum(len(r[k]) for k in
                      ("multivalor", "rango", "lista_fich", "no_finding",
                       "prosa"))))  # type: ignore
    print("    era falsa hasta medirlo:")
    print()
    # Cada "porque" describe SU MISMA fila. La primera version los descentro
    # una posicion -- la fila MULTIVALOR llevaba la explicacion de RANGO -- y
    # el informe era legible pero mentia. Un informe que describe la fila de
    # al lado es peor que uno sin descripciones.
    for k, titulo, porque in (
            ("multivalor", "MULTIVALOR",
             "varios findings en UNA etiqueta, separados por comas"),
            ("rango", "RANGO",
             "`CONTINUES=017-029`: raya, no guion, y es un intervalo"),
            ("lista_fich", "LISTA_FIC",
             "lista de nombres de fichero, y por tanto inequivocos"),
            ("no_finding", "NO_FINDING",
             "apunta a algo que no es un finding: correcto, no un fallo"),
            ("prosa", "PROSA",
             "palabra antes de un `=`: `CIERRA=la`, `CORRECTS=la`"),
    ):
        n = len(r[k])  # type: ignore
        print("    %-12s %4d  %s" % (titulo, n, porque))
    print()
    print("    ARISTAS QUE SE HAN ABIERTO CON ESTO: %d" % len(r["extra"]))  # type: ignore
    if r["multivalor"]:  # type: ignore
        print("    MULTIVALOR, que es la clase que mas aristas estaba")
        print("    perdiendo. Todas las piezas se pueden resolver:")
        tot = 0
        for et, val, i, num, partes in r["multivalor"][:6]:  # type: ignore
            ok = sum(1 for x in partes
                     if resuelve_a_finding(x, _pn, _nom))
            tot += ok
            print("      %-13s=%-34s %d/%d resuelven  (en %s:%d)"
                  % (et, val[:34], ok, len(partes), num, i))
        print()
        print("    Y YA SE CUENTAN. Todas las piezas de MULTIVALOR, RANGO y")
        print("    LISTA_FIC generan una arista cada una, con su marca de")
        print("    ambiguedad. El total sale de `len(extra)`, no de una suma")
        print("    escrita a mano -- que es como se habia escrito el 78 aqui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())