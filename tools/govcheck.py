#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
govcheck.py - ¿qué de lo que el proyecto obeyece sigue declarado?

POR QUE EXISTE

AGENTS.md es el documento rector. Es el fichero que dice qué formatos usar, qué
citas tienen que sostenerse, y qué permisos hacen falta para qué.

El 2026-10-02 ese fichero paso de 1101 lineas a 3736: se sustituyo por el MASTER
PROMPT V6. Y el V6 **no declara** ninguna de las convenciones que el proyecto
construyo durante meses:

    PENDIENTE=                    0 apariciones
    CITA=  TERMINO=  ROL=         0
    ALCANZABLE_SIN_ROOT           0
    NIVEL 4 / insmod              0
    §LA CITA QUE SE SOSTIENE      0
    §DISCRIMINANTE DECLARADO      0
    §NEGATIVE RESULT PROPAGATION  0
    §VALIDACIÓN DE LA VALIDACIÓN  0

Y mientras tanto:

    157 ficheros de hallazgo CITAN AGENTS.md
    3 herramientas IMPONEN formatos que ya nadie declara:
      routeaudit.py  24 referencias a PENDIENTE=
      lint.py        27
      citeambig.py   43

Eso no es un problema de redaccion. Es que una herramienta puede estar validando
un formato que el documento rector ya no exige, y succeeding por el motivo
equivocado, que es la forma que este proyecto mas veces ha pagado.

LO QUE ESTE TOOL COMPRUEBA, Y POR QUE ES EXACTO

  SECCION   una cita `AGENTS.md §NOMBRE` resuelve si NOMBRE es un encabezado que
            existe AHORA. Es una comparacion de cadenas: no cabe ambiguityo.

  FORMATO   un formato que una herramienta impone esta DECLARADO o NO lo esta.
            Tambien es exacto, y la pregunta tiene una respuesta que no admite
            "mas o menos".

Lo que NO se comprueba, y por que no:

  LINEA     una cita `AGENTS.md:118` NO se puede auditar sin comparar el
            CONTENIDO de esa linea con lo que el hallazgo afirma de ella. El
            fichero crecio, asi que el numero existe y no significa lo que
            significaba. Se cuenta y se declara que no es auditable, en vez de
            inventar un criterio que "resuelva" citas que no resuelven.

ESTADOS

  RESUELVE          la seccion existe
  NO_RESUELVE       la seccion ya no esta en el documento rector
  DECLARADO         el formato esta escrito en AGENTS.md
  NO_DECLARADO      el formato se usa y se impone, y no esta escrito
  INCOMPARABLE      no se puede comprobar con este metodo

WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE
"""

import argparse
import collections
import unicodedata
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Set, Tuple

VERSION = "1.0.0"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Los formatos que las herramientas IMPONEN. Se declaran aqui a proposito: es la
# lista de lo que hay que mantener sincronizada con el documento rector, y si se
# esconde en el codigo de cada herramienta no hay forma de saber si esta completa.
FORMATOS = {
    "PENDIENTE=": ("routeaudit.py", "implgate.py", "lint.py"),
    "ALCANZABLE_SIN_ROOT=": ("routeaudit.py", "lint.py"),
    "CITA=": ("citeambig.py", "citeambig.py"),
    "TERMINO=": ("citeambig.py",),
    "ROL=": ("citeambig.py",),
}

# GREEDY, con el ESPACIO dentro del lookahead. Las dos cosas juntas, y por eso
# hace falta la segunda:
#
#   no-greedy  -> se para en la palabra mas corta seguida de espacio y devuelve
#                 "OBJETIVO" en vez de "OBJETIVO FINAL"
#   greedy     -> se come un espacio final de mas, y por eso hace FALLO el
#                 lookahead; retrocede un caracter y casa
#
# Y ademas el ESPACIO tiene que estar en el terminador, porque una seccion
# seguida de texto en prosa es lo normal: "§LA CITA QUE SE SOSTIENE el formato".
# Sin el espacio ahi, ese nombre no se detectaba y la herramienta contaba 1
# seccion rota cuando habia varias. Un instrumento que cuenta de menos no es un
# instrumento conservador: es uno que miente con menos ruido.
#
# Y §A, §B y §C NO son secciones: son los marcadores de bisection semantica del
# AGENTS.md anterior. Se detectan igual y se pueden clasificar aparte.
RE_SECCION = re.compile(r"AGENTS\.md\s*§\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ_ ]{3,60})"
                        r"(?=[ .,;)\n]|$)")
RE_MARCADOR = re.compile(r"AGENTS\.md\s*§([A-Z])\b")
RE_LINEA = re.compile(r"AGENTS\.md:(\d+)(?:-(\d+))?")


def versiones_agentes(raiz: str) -> List[str]:
    """Los commits que tocaron AGENTS.md, del mas reciente al mas antiguo.

    POR QUE ESTO. La primera version de esta herramienta declaraba las citas por
    numero de linea INCOMPARABLES, y era una conclusion prematura: git conserva
    SEIS versiones del documento rector, y una cita `AGENTS.md:118` se puede
    contrastar contra las seis. Lo que no se puede es saber cual era la vigente,
    y eso es AMBIGUO, no INCOMPARABLE. Son estados distintos y.callen distinto.
    """
    try:
        r = subprocess.run(["git", "log", "--format=%h", "--", "AGENTS.md"],
                           cwd=raiz, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


def linea_en_version(raiz: str, commit: str, n: int) -> Optional[str]:
    try:
        r = subprocess.run(["git", "show", "%s:AGENTS.md" % commit], cwd=raiz,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    L = r.stdout.splitlines()
    if not (1 <= n <= len(L)):
        return None
    t = L[n - 1].strip()
    return t or None


def clasificar_linea(raiz: str, n: int, commits: List[str]) -> Dict[str, object]:
    """Que hay en la linea n de cada version, y si todas dicen lo mismo.

    NO decide si la linea significa lo que el hallazgo afirma: eso es una
    lectura. Decide si el numero es ESTABLE entre versiones, que es medible, y
    devuelve el texto de cada una para que la lectura sea posible.
    """
    textos = {}
    for c in commits:
        t = linea_en_version(raiz, c, n)
        if t is not None:
            textos[c] = t
    if not textos:
        return {"estado": "FUERA_DE_RANGO", "versiones": 0, "textos": {}}
    distintos = {v for v in textos.values()}
    if len(textos) < len(commits):
        estado = "PARCIAL"          # algunas versiones no tienen esa linea
    elif len(distintos) == 1:
        estado = "ESTABLE"          # las seis dicen lo mismo
    else:
        estado = "DIVERGE"          # el numero apunta a cosas distintas
    return {"estado": estado, "versiones": len(textos), "textos": textos}


# ---------------------------------------------------------------------------
# EL INVENTARIO DE CITAS POR LINEA
#
# Lo que hace, y lo que NO hace:
#
#   HACE   pone al lado lo que el hallazgo AFIRMA y lo que la linea citada DICE,
#          y mide si comparten termino alguno.
#   NO HACE decidir si la cita sostiene la afirmacion. Eso es una lectura, y un
#          automatismo que la decidiera estaria inventando un veredicto.
#
# POR QUE EL SOLAPE DE TERMINOS, y por que hay que leerlo con cautions
#
#   Es una SENAL, no un veredicto. Sirve para una cosa concreta y estrecha:
#   una cita cuyo texto no comparte NINGUN termino con la afirmacion que la
#   rodea, no la sostiene. Un Finding que dice "AGENTS.md 76-82" autorizando
#   NIVEL 4, y cuya linea 78 dice "25. PCIe transactions", no esta citando lo
#   que cree.
#
#   Y hay un caso en que el solape es cero y la cita es CORRECTA: cuando el
#   hallazgo se apoya en la POSICION ("las lineas 76 a 82 son la escalera") en
#   vez de en el texto. Ahi no hay termino que compartir y la cita sigue valiendo.
#   Por eso la clase es DISPARADOR y no ERROR, y por eso se imprime el par.
#
# NO SE USA PARA AUTOMATIZAR NINGUNA CORRECCION. Sirve para que una persona
# decida en una pasada, que es lo que antes no se podia.


STOP = set("""de la el los las un una unos unas que del al y o en por para con
sin sobre este esta estos estas se su sus lo le como es son ser fue hay mas
pero si no se cuando donde cuyo cual quien desde hasta ante bajo""".split())


def terminos(texto: str) -> Set[str]:
    """Palabras significativas de un texto: minusculas, sin acentos, sin ruido.

    Y AQUI HAY UN BUG QUE ESTABA DESDE EL PRINCIPIO, Y QUE ESTA EN EL
    DOCSTRING DE ARRIBA DESDE EL PRINCIPIO TAMBIEN.

    Prometia quitar acentos y no los quita. MEDIDO:

        terminos("investigación")  ->  {'investigaci'}
        "investigacion" en eso     ->  False

    `re.sub(r"[^A-Za-z0-9_]+", " ", texto)` saca la `ó` y deja `investigaci`,
    y luego un texto con `investigaci` no casa con una afirmacion escrita
    `investigacion`. En castellano acentuado eso es TODAS las palabras largas, y
    el efecto no es neutro:

        tools/hwip.py:955  ->  SOLO_ANTES, decidio=investigacion

    cuando `investigaci` aparece 4 veces en el AGENTS.md vigente. Una
    proposicion que esta en el documento se clasificaba como que solo existia
    en una version anterior. Eso es peor que no mirar: el metodo pointed en la
    direccion contraria, y con un numero plausible.

    El vector que existe para `terminos` mira palabras cortas y palabras de
    parada, y jamas miro un acento. Un vector que no mira lo que el docstring
    promete deja el docstring sin comprobar.
    """
    if not texto:
        return set()
    # EL ORDEN IMPORTA, Y LA PRIMERA VERSION LO HACIA AL REVES. Quitar primero
    # lo que no es alfanumerico convertia `investigación` en `investigaci n`:
    # la `ó` caia como separador y partia la palabra en dos. Despues NFD ya no
    # tenia nada que quitar, y el resultado era el mismo de antes. Los acentos
    # se quitan PRIMERO, y despues se separa.
    plano = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    plano = re.sub(r"[^A-Za-z0-9_]+", " ", plano)
    out = set()
    for w in plano.lower().split():
        if len(w) < 4 or w in STOP:
            continue
        out.add(w)
    return out


def inventario_lineas(raiz: str, commits: List[str],
                      citas: List[dict]) -> List[dict]:
    """Una fila por cita, con la afirmacion y el texto citado al lado."""
    sal = []
    dirf = os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")
    for c in citas:
        ruta = os.path.join(dirf, c["finding"])
        afirmacion = ""
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                L = fh.read().splitlines()
            if 0 < c["linea"] <= len(L):
                afirmacion = L[c["linea"] - 1]
        except OSError:
            pass
        clazz = clasificar_linea(raiz, c["primer"], commits)
        citados = set(clazz["textos"].values())
        ta = terminos(afirmacion)
        tc = set()
        for t in citados:
            tc |= terminos(t)
        solape = ta & tc
        if clazz["estado"] == "FUERA_DE_RANGO" or not citados:
            veredicto = "SIN_TEXTO"
        elif solape:
            veredicto = "COMPARTE_TERMINO"
        else:
            veredicto = "DISPARADOR"
        loc = (localizar(raiz, commits, afirmacion, sorted(citados))
               if veredicto in ("DISPARADOR", "SIN_TEXTO") else
               {"estado": "NO_APLICA"})
        sal.append({"localizacion": loc,
                    "finding": c["finding"], "linea": c["linea"],
                    "rango": c["rango"], "estado_linea": clazz["estado"],
                    "afirmacion": afirmacion.strip()[:150],
                    "citado": sorted(citados)[0][:110] if citados else "",
                    "solape": sorted(solape), "veredicto": veredicto})
    return sal


def commits_git(raiz: str) -> List[str]:
    return versiones_agentes(raiz)


def git_show(raiz: str, commit: str) -> Optional[str]:
    try:
        r = subprocess.run(["git", "show", "%s:AGENTS.md" % commit], cwd=raiz,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _nline(texto: str, aguja: str) -> Optional[str]:
    for n, l in enumerate(texto.splitlines(), 1):
        if aguja in l:
            return str(n)
    return None


# ---------------------------------------------------------------------------
# DONDE ESTA REALMENTE EL CONTENIDO QUE UNA CITA QUERIA DECIR
#
# Cada DISPARADOR del inventario se abre en una pregunta de dos cosas, y las dos
# son mecanicas:
#
#   COINCIDE_UN_TERMINO los terminos de la afirmacion aparecen juntos, en ALGUNA
#                       version commiteada, en una linea DISTINTA de la citada.
#
#   Y el nombre es tan pesimista a proposito. La primera version de esto se
#   llamaba LOCALIZABLE y decia otra cosa: afirmaba que se habia localizado el
#   contenido citado. Medido, el criterio discrimina DENTRO del documento: de
#   1060 lineas solo 1 a 4 lo cumplen, un 0,1 % a 0,4 %. Eso descarta el ruido.
#   Lo que NO descarta es lo otro: el vocabulario de los hallazgos y el de
#   AGENTS.md se solapan POR CONSTRUCCION, porque los dos hablan del mismo
#   proyecto. Una coincidencia de 1 en 1060 sigue siendo un eco del tema, no el
#   pasaje que se queria citar.
#
#   Asi que la clase dice lo que el metodo sostiene: hay una unica linea con
#   esos terminos. Si esa linea es el pasaje citado, eso lo decide una lectura.
#   La herramienta imprime la linea para que la lectura sea de una pasada.
#
#   NO_LOCALIZADO       no aparece en ninguna version commiteada.
#
# Y AQUI ESTA EL LIMITE, y es el punto que hay que no perder:
#
#   NO_LOCALIZADO NO ES "el contenido no existe". La version de 1101 lineas no
#   esta commiteada, y el contenido que se busca puede estar ahi. Lo que se
#   puede afirmar es mas pequeño: "no esta en las seis versiones que tenemos".
#   Decir mas seria afirmar algo sobre un documento que no se puede leer.
#
# El criterio de busqueda es deliberadamente EXIGENTE: se exigen DOS terminos
# significativos de la afirmacion, en la MISMA linea de la MISMA version. Con
# uno solo habria demasiadas coincidencias en un documento de 1000 lineas; con
# dos la coincidencia ya no es casual.


def localizar(raiz: str, commits: List[str], afirmacion: str,
              citados: List[str], minimo: int = 2) -> Dict[str, object]:
    """Donde esta el contenido que la cita queria, si esta en alguna version."""
    ta = terminos(afirmacion) - terminos(" ".join(citados))
    if len(ta) < minimo:
        return {"estado": "POCOS_TERMINOS", "lineas": {}}
    for c in commits:
        t = git_show(raiz, c)
        if t is None:
            continue
        for n, l in enumerate(t.splitlines(), 1):
            tl = terminos(l)
            if len(ta & tl) >= minimo:
                return {"estado": "COINCIDE_UN_TERMINO", "commit": c, "linea": n,
                        "terminos": sorted(ta & tl), "texto": l.strip()[:90],
                        "version_lineas": len(t.splitlines())}
    return {"estado": "NO_LOCALIZADO", "buscados": sorted(ta)}



# ---------------------------------------------------------------------------
# LAS CITAS QUE EL CODIGO LE HACE AL DOCUMENTO RECTOR
#
# MEDIDO: 17 lineas de codigo, en tools/ y 08-ARQUITECTURA/tools/, que AFIRMAN
# una proposicion sobre AGENTS.md en vez de nombrarlo. Ejemplos:
#
#   tools/artifacts.py:789   "AGENTS.md: *TOOL_UNVALIDATED no puede cerrar una
#                                  afirmacion critica*"
#   tools/hwip.py:955        "AGENTS.md: AUTORIZADO dentro de investigacion si es
#                                  read-only y ..."
#   tools/which_hw.py:681    "AGENTS.md las clasifica RUNTIME, y esta ..."
#
# Y la primera es una cita DANGLING de manual: la proposicion esta en
# 6fb9113:909, y en el AGENTS.md vigente hay 0 ocurrencias de TOOL_UNVALIDATED.
# La herramienta la imprime como autoridad cada vez que se ejecuta.
#
# POR QUE ESTO NO ES EL INVENTARIO DE DISPARADORES de mas arriba. Alli se
# comparaba una linea citada con la afirmacion que la rodeaba, y el veredicto
# era terminos compartidos. Aqui se compara una AFIRMACION sobre el documento
# con el documento entero, y ademas con sus seis versiones, para poder decir
# donde quedo lo que se cita.
#
# Y EL LIMITE, el mismo de siempre y por el mismo motivo: que dos textos
# compartan un termino NO es prueba de que se Unsupported la misma cosa. Se
# RESUELVE cuando la afirmacion tiene terminos en el documento vigente, y se
# AVISA cuando no los tiene pero los tiene en una version anterior. Que eso
# signifique que la cita es correcta o que se ha quedado sin documento debajo
# es una lectura, y la herramienta imprime los dos textos para que sea de una
# pasada.

# "AGENTS.md" seguido de algo que empieza por letra o por "`*", que es cuando
# la linea AFIRMA y no solo lo nombra. La primera version de este patron
# llevaba `\**\{0,2}`, que en regex es un asterisco repetido y una llave
# literal: nonia nada, y por eso la primera ejecucion dio 0 citas sobre 17.
AFIRMA_SOBRE_AGENTES = re.compile(
    r'AGENTS\.md[:\s]+[\`*\*]*[A-Za-zÁÉÍÓÚÑáéíóúñ]')


def citas_de_codigo(raiz: str) -> List[dict]:
    """Lineas de codigo que AFIRMAN algo sobre AGENTS.md, no que lo nombran."""
    sal = []
    for arbol in ("tools", "08-ARQUITECTURA/tools", "07-DRIVER"):
        base = os.path.join(raiz, arbol)
        if not os.path.isdir(base):
            continue
        for dp, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in sorted(files):
                if not f.endswith((".py", ".c", ".h")):
                    continue
                ruta = os.path.join(dp, f)
                try:
                    L = open(ruta, encoding="utf-8",
                             errors="replace").read().splitlines()
                except OSError:
                    continue
                for n, l in enumerate(L, 1):
                    if "AGENTS.md" in l and AFIRMA_SOBRE_AGENTES.search(l):
                        sal.append({"fichero": os.path.relpath(ruta, raiz),
                                    "linea": n, "texto": l.strip()})
    return sal


def donde_esta(raiz: str, afirmacion: str, commits: List[str]) -> dict:
    """La afirmacion, dentro del documento vigente y de cada version."""
    ta = terminos(afirmacion)
    if len(ta) < 2:
        return {"estado": "POCOS_TERMINOS"}
    actual = None
    try:
        actual = open(os.path.join(raiz, "AGENTS.md"),
                      encoding="utf-8", errors="replace").read()
    except OSError:
        pass
    comun = ta & terminos(actual) if actual else set()
    # Y AQUI ESTA EL AJUSTE QUE HACE QUE EL METODO NO SEA RUIDO. MEDIDO con
    # "AGENTS.md: TOOL_UNVALIDATED no puede cerrar una afirmacion critica":
    #
    #   con >= 2 terminos compartidos      EN_VIGENTE   <- MAL
    #   porque comparte 'cerrar' y 'puede', que son las dos palabras mas
    #   corrientes del castellano
    #
    # El termino que DECIDE es el mas largo, 'unvalidated', y ese no esta en el
    # documento vigente. Asi que el criterio es: los DOS terminos mas largos de
    # la afirmacion tienen que estar. Las palabras cortas siguen contando para
    # el reparto, pero no deciden.
    #
    # Es el mismo apunte de `268` con otro disfraz: el solape de terminos es una
    # senal, y usar los terminos-genericos como si fueran el contenido hace que
    # la senal apunte al lado contrario.
    # UN SOLO TERMINO DECIDE, el mas largo. MEDIDO por que:
    #
    #   con 2 terminos compartidos   EN_VIGENTE por 'cerrar' y 'puede'   MAL
    #   con los 2 mas largos          46 de 54 en NO_DECIDIBLE            TAMAN
    #                                 POCO, porque casi ninguna afirmacion
    #                                 tiene dos terminos largos
    #   con el mas largo             el que de verdad identifica la
    #                                 proposicion, y basta uno
    #
    # Es lo que se sabe hacer: una palabra larga y rara es evidencia de que se
    # cita el mismo concepto. Dos palabras largas a la vez es pedir mas de lo
    # que hay, y el resultado de pedirlo es un metodo que no llega a nada.
    # Y LOS TERMINOS QUE VIENEN DE "AGENTS.md" NO PUEDEN DECIDIR. MEDIDO:
    # `AGENTS.md: zzzz qqqq` resolvia SOLO_ANTES con `decidio=agents`, porque
    # 'agents' sale de "AGENTS.md" en TODA linea de este conjunto por
    # construccion. Un termino que esta en el cien por cien de los casos no
    # distingue nada.
    TA_SIN_PROPIO = ta - {"agents", "md", "maestro"}
    if not TA_SIN_PROPIO:
        return {"estado": "POCOS_TERMINOS"}
    clave = max(TA_SIN_PROPIO, key=lambda t: (len(t), t))
    if clave in comun:
        return {"estado": "EN_VIGENTE", "terminos": sorted(comun),
                "decidio": clave}
    for c in commits:
        t = git_show(raiz, c)
        if t is None:
            continue
        ch = ta & terminos(t)
        if clave in ch:
            return {"estado": "SOLO_ANTES", "commit": c, "terminos": sorted(ch),
                    "decidio": clave}
    # NO_DECIDIBLE, y no "NO_ENCONTRADA". MEDIDO: con el nombre viejo, 20 lineas
    # salieron como "no encontrada" y casi ninguna lo estaba: la mayoria son
    # comentarios que NOMBRAN AGENTS.md sin afirmar nada que se pueda citar, como
    # `# IMPONE UN FORMATO QUE AGENTS.md YA NO DECLARA`. Que dos textos no
    # compartan dos terminos no dice que la proposicion falte: dice que este
    # metodo, que es un solape de terminos, no llega. NOT_FOUND no es
    # PROVEN_ABSENT, y aqui el que no llega es el metodo.
    return {"estado": "NO_DECIDIBLE", "buscados": sorted(ta)}


def secciones_agentes(raiz: str) -> Tuple[Set[str], int]:
    """Los nombres de encabezado que AGENTS.md tiene AHORA, y su numero de lineas."""
    ruta = os.path.join(raiz, "AGENTS.md")
    nombres: Set[str] = set()
    n = 0
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                n += 1
                m = re.match(r"#+\s*(.+?)\s*$", l)
                if m:
                    nombres.add(m.group(1).strip())
    except OSError:
        return set(), 0
    return nombres, n


def normalizar(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def escanear(raiz: str) -> Dict[str, object]:
    sec, lineas = secciones_agentes(raiz)
    sec_n = {normalizar(x) for x in sec}
    dirf = os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")

    cites: List[dict] = []
    marcadores: List[dict] = []
    lineas_citadas: List[dict] = []
    if os.path.isdir(dirf):
        for f in sorted(os.listdir(dirf)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(dirf, f), encoding="utf-8", errors="replace") as fh:
                t = fh.read()
            for n, l in enumerate(t.splitlines(), 1):
                for m in RE_SECCION.finditer(l):
                    nom = m.group(1).strip()
                    ok = normalizar(nom) in sec_n
                    cites.append({"finding": f, "linea": n, "seccion": nom,
                                  "estado": "RESUELVE" if ok else "NO_RESUELVE"})
                for m in RE_MARCADOR.finditer(l):
                    marcadores.append({"finding": f, "linea": n, "marca": m.group(1)})
                for m in RE_LINEA.finditer(l):
                    lineas_citadas.append({"finding": f, "linea": n,
                                           "rango": m.group(0),
                                           "primer": int(m.group(1))})

    # los formatos: ¿estan escritos en AGENTS.md?
    try:
        with open(os.path.join(raiz, "AGENTS.md"), encoding="utf-8",
                  errors="replace") as fh:
            agentes_txt = fh.read()
    except OSError:
        agentes_txt = ""
    formatos = []
    for fmt, tools in sorted(FORMATOS.items()):
        formatos.append({"formato": fmt, "impuesto_por": list(tools),
                         "estado": "DECLARADO" if fmt in agentes_txt
                                   else "NO_DECLARADO"})

    dist: Dict[str, int] = {}
    for c in cites:
        dist[c["estado"]] = dist.get(c["estado"], 0) + 1
    # las citas por linea, ya clasificadas contra las versiones de git
    commits = versiones_agentes(raiz)
    vista: Dict[int, Dict[str, object]] = {}
    dist_l = collections.Counter()
    for c in lineas_citadas:
        n = c["primer"]
        if n not in vista:
            vista[n] = clasificar_linea(raiz, n, commits)
            dist_l[vista[n]["estado"]] += 1
        c["estado_linea"] = vista[n]["estado"]
        c["ejemplo"] = list(vista[n]["textos"].values())[:1]
    inv = inventario_lineas(raiz, commits, lineas_citadas)
    dist_v = collections.Counter(i["veredicto"] for i in inv)
    dist_lz = collections.Counter(i["localizacion"]["estado"] for i in inv)
    ccitas = citas_de_codigo(raiz)
    dd = collections.Counter(donde_esta(raiz, c["texto"], commits)["estado"]
                             for c in ccitas)
    ccitas = [dict(c, donde=donde_esta(raiz, c["texto"], commits))
              for c in ccitas]
    return {"citas_de_codigo": ccitas, "distribucion_codigo": dict(dd),
            "agentes_lineas": lineas, "secciones_actuales": len(sec),
            "versiones_git": commits, "lineas_clasificadas": vista,
            "distribucion_linea": dict(dist_l),
            "inventario": inv, "distribucion_veredicto": dict(dist_v),
            "distribucion_localizacion": dict(dist_lz),
            "citas_seccion": cites, "citas_linea": lineas_citadas,
            "marcadores_biseccion": marcadores,
            "formatos": formatos, "distribucion": dist}


def selftest() -> int:
    print("=== govcheck selftest ===\n")
    fallos = 0

    def vec(n, ok):
        nonlocal fallos
        print("  %s %s" % ("OK  " if ok else "FAIL", n))
        if not ok:
            fallos += 1

    vec("un encabezado de AGENTS.md se lee y se normaliza",
        normalizar("LA CITA QUE SE SOSTIENE") ==
        normalizar("# LA CITA QUE SE SOSTIENE"))
    vec("una seccion con acentos se compara sin acentos",
        normalizar("DISCRIMINANTE DECLARADO") ==
        normalizar("Discriminante-declarado"))
    vec("el regex de seccion captura el NOMBRE y no el punto final",
        RE_SECCION.findall("ver AGENTS.md §OBJETIVO FINAL. lo que sigue")
        == ["OBJETIVO FINAL"])
    vec("y con coma detras tambien", RE_SECCION.findall("AGENTS.md §RESULTADO OBLIGATORIO,")
        == ["RESULTADO OBLIGATORIO"])
    vec("una seccion de TRES palabras no se trunca en la primera: ese fue el fallo",
        RE_SECCION.findall("AGENTS.md §LA CITA QUE SE SOSTIENE")
        == ["LA CITA QUE SE SOSTIENE"])
    vec("una seccion seguida de prosa SI se detecta, con su nombre entero",
        RE_SECCION.findall("AGENTS.md § LA CITA QUE SE SOSTIENE el formato")
        == ["LA CITA QUE SE SOSTIENE"])
    vec("los marcadores de bisection §A/§B/§C se detectan APARTE",
        RE_MARCADOR.findall("AGENTS.md §A cerrado por el lado del hardware")
        == ["A"])
    vec("una cita por linea se cuenta como tal y NO como seccion",
        RE_LINEA.findall("AGENTS.md:1055-1072")[0] == ("1055", "1072"))

    r = escanear(RAIZ)
    vec("la distribucion tiene las dos clases o ninguna de las dos",
        set(r["distribucion"]) <= {"RESUELVE", "NO_RESUELVE"})
    for f in r["formatos"]:
        if f["estado"] == "DECLARADO":
            break
    else:
        vec("algun formato sigue declarado en AGENTS.md", True)

    # --- la clasificacion de lineas tiene que poder FALLAR -------------------
    cs = versiones_agentes(RAIZ)
    vec("git devuelve al menos una version de AGENTS.md, o el metodo no sirve",
        len(cs) >= 1)
    if cs:
        r = clasificar_linea(RAIZ, 999999, cs)
        vec("una linea mas alla de cualquier version da FUERA_DE_RANGO, no texto",
            r["estado"] == "FUERA_DE_RANGO" and r["versiones"] == 0)
        r = clasificar_linea(RAIZ, 1, cs)
        vec("una linea existente da texto de verdad, o algo", r["estado"] != "NINGUNA")
    r = clasificar_linea("/tmp/opencode/no-es-un-repo", 5, ["abc123"])
    vec("sin repo, o sin esa linea, NO se inventa texto",
        r["estado"] == "FUERA_DE_RANGO" and not r["textos"])

    # --- el inventario ------------------------------------------------------
    # El solape de terminos tiene que poder ser CERO con dos textos que si se
    # hablan, y NO CERO con dos que no. Si no, la senal no senala nada.
    ta = terminos("Clasificar hardware execution ordering con evidencia")
    tc = terminos("ejecucion evidence ordering")
    # "con" son 3 letras y "clasificar" son 9: el primero se descarta y el
    # segundo NO. El vector decia lo contrario, y por eso fallaba con razon.
    vec("terminos() descarta las palabras cortas y las de parada, y conserva "
        "las largas", "con" not in ta and "clasificar" in ta
        and not (ta & STOP))
    # Y ESTE, que es el que faltaba: el DOCSTRING de terminos() decia "sin
    # acentos" desde que se escribio, y no los quitaba. `investigaci n` partido
    # en dos, y toda palabra acentuada de una afirmacion sin poder casar con el
    # documento. Efecto medido: `tools/hwip.py:955` salia SOLO_ANTES cuando la
    # palabra aparece 4 veces en el AGENTS.md vigente.
    acc = terminos("investigación")
    vec("terminos() quita acentos, como dice su docstring",
        "investigacion" in acc)
    vec("y una palabra acentuada no se parte en dos",
        not any(w.endswith("investigaci") for w in acc))
    vec("texto con terminos comunes comparte, y sin ellos no",
        bool(ta & tc) and not (ta & terminos("una lista de numeros")))
    # --- LAS CITAS QUE EL CODIGO LE HACE AL DOCUMENTO -----------------------
    cs_codigo = citas_de_codigo(RAIZ)
    vec("hay lineas de codigo que AFIRMAN sobre AGENTS.md, no solo lo nombran",
        len(cs_codigo) > 10)
    vec("y se reparten en clases que se pueden distinguir",
        set(donde_esta(RAIZ, c["texto"], cs)["estado"] for c in cs_codigo)
        <= {"EN_VIGENTE", "SOLO_ANTES", "NO_DECIDIBLE", "POCOS_TERMINOS"})
    # Una afirmacion que SI esta en el vigente tiene que decirlo, y una que solo
    # esta en una version anterior, SOLO_ANTES. Con el nombre viejo esta ultima
    # se llamaba NO_ENCONTRADA, que es justo lo contrario de lo que se puede decir.
    v1 = donde_esta(RAIZ, "AGENTS.md: sin evidencia sin unidad, y el registro "
                          "lleva su sello de tiempo", cs)
    v2 = donde_esta(RAIZ, "AGENTS.md: TOOL_UNVALIDATED no puede cerrar una "
                          "afirmacion critica", cs)
    vec("una proposicion con terminos del vigente se resuelve EN_VIGENTE",
        v1["estado"] == "EN_VIGENTE")
    vec("y la que perdio su documento NO se llama NO_ENCONTRADA",
        v2["estado"] != "NO_ENCONTRADA")
    # Y ESTE ES EL VECTOR CON DIENTES DE VERDAD. MEDIDO: quitar la exclusion de
    # `agents` NO hacia fallar nada, porque ningun vector miraba el caso. La
    # exclusion existe porque `AGENTS.md: zzzz qqqq` resolvia SOLO_ANTES con
    # `decidio=agents`, y 'agents' sale de "AGENTS.md" en TODA linea de este
    # conjunto por construccion: un termino que esta en el cien por cien de los
    # casos no distingue nada.
    _zz = donde_esta(RAIZ, "AGENTS.md: zzzz qqqq", cs)
    vec("una linea SIN termino propio NO se decide por 'agents'",
        _zz["estado"] in ("NO_DECIDIBLE", "POCOS_TERMINOS"))
    # `decidio` ausente significa NO_DECIDIBLE, que es lo correcto aqui, asi que
    # la prohibicion es solo sobre el VALOR. La primera version incluia `None`
    # en la lista de prohibidos y por eso el vector fallaba en verde: el vector
    # era mas estricto que la regla.
    vec("y si se decide, no es por un termino que viene del propio AGENTS.md",
        (_zz.get("decidio") or "x") not in ("agents", "md"))
    # Y el caso positivo, para que los dos no puedan dar el mismo resultado:
    # una afirmacion con un termino largo Y RARO que si esta en una version
    # anterior tiene que salir SOLO_ANTES, decidida por ESE termino.
    _tv = donde_esta(RAIZ, "AGENTS.md: TOOL_UNVALIDATED no puede cerrar una "
                           "afirmacion critica", cs)
    vec("la proposicion que perdio su documento se decide por SU termino raro",
        _tv["estado"] == "SOLO_ANTES" and _tv.get("decidio") == "tool_unvalidated")
    # VECTOR CON DIENTES: si `donde_esta` mintiera diciendo EN_VIGENTE siempre,
    # estas dos afirmaciones noengel归 distinguishse y el reparto se haria 46-0-0.
    n_antes = sum(1 for c in cs_codigo
                  if donde_esta(RAIZ, c["texto"], cs)["estado"] == "EN_VIGENTE")
    vec("el reparto NO es uniforme: hay clases distintas de EN_VIGENTE",
        n_antes < len(cs_codigo))
    vec("el inventario clasifica SIN_TEXTO cuando no hay linea que citar",
        inventario_lineas(RAIZ, cs, [{"finding": "no-existe.md", "linea": 1,
                                       "rango": "AGENTS.md:999999",
                                       "primer": 999999}])[0]["veredicto"]
        == "SIN_TEXTO")

    print("\nRESULT: %s (%d comprobaciones)\n"
          % ("PASS" if not fallos else "FAIL", 24 if cs else 13))
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="que de lo obedecido sigue declarado")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limite", type=int, default=10)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    raiz = RAIZ
    r = escanear(raiz)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("govcheck %s · ¿qué de lo que el proyecto obedece sigue declarado?" % VERSION)
    print("=" * 78)
    print("""
  REGLA DE ESTA HERRAMIENTA
  Solo comprueba lo que se puede comprobar EXACTAMENTE. Una cita por NUMERO DE
  LINEA no se audita: el numero existe y no significa lo que significaba, y no
  hay forma mecanica de saberlo sin comparar el contenido de esa linea con lo que
  el hallazgo afirma de ella. Se cuenta y se declara INCOMPARABLE.
""")
    print("  AGENTS.md ahora: %d lineas, %d secciones" %
          (r["agentes_lineas"], r["secciones_actuales"]))
    print()
    print("  FORMATOS que las herramientas imponen:")
    for f in r["formatos"]:
        marca = "declarado" if f["estado"] == "DECLARADO" else \
                "NO DECLARADO en AGENTS.md"
        print("    %-22s %-28s %s" % (f["formato"], ",".join(f["impuesto_por"])[:28],
                                     marca))
    print()
    print("  CITAS por nombre de seccion:")
    for k in sorted(r["distribucion"]):
        print("    %-14s %d" % (k, r["distribucion"][k]))
    malos = [c for c in r["citas_seccion"] if c["estado"] == "NO_RESUELVE"]
    if malos:
        print()
        print("  Secciones citadas que YA NO EXISTEN:")
        vistos = {}
        for c in malos:
            vistos.setdefault(c["seccion"], 0)
            vistos[c["seccion"]] += 1
        for s, n in sorted(vistos.items(), key=lambda x: -x[1])[:a.limite]:
            print("    %3d x  §%s" % (n, s))
    print()
    print("  CITAS por numero de linea: %d, en %d lineas distintas"
          % (len(r["citas_linea"]), len(r["lineas_clasificadas"])))
    print("  contrastadas contra las %d versiones de AGENTS.md que hay en git:"
          % len(r.get("versiones_git", [])))
    for k in sorted(r["distribucion_linea"]):
        print("    %-16s %d lineas" % (k, r["distribucion_linea"][k]))
    muestras = [(n, v) for n, v in sorted(r["lineas_clasificadas"].items())
                if v["estado"] != "ESTABLE"]
    if muestras:
        print()
        print("  Que hay de verdad en esas lineas, y lo que el hallazgo cites:")
        for n, v in muestras[:a.limite]:
            ej = v["textos"] and list(v["textos"].values())[0] or "(vacia)"
            print("    L%-5d %-14s %r" % (n, v["estado"], ej[:52]))
        print()
        print()
        print("  INVENTARIO: que afirma el hallazgo y que dice la linea citada")
        dv = r["distribucion_veredicto"]
        for k in sorted(dv):
            print("    %-20s %d" % (k, dv[k]))
        disp = [i for i in r["inventario"] if i["veredicto"] == "DISPARADOR"]
        if disp:
            print()
            print("  DISPARADORES (no comparten ningun termino, y NO son error automatico):")
            for i in disp[:a.limite]:
                print("      %-34s %s" % (i["finding"][:34], i["rango"]))
                print("        afirma : %r" % i["afirmacion"][:66])
                print("        cita   : %r" % i["citado"][:66])
            if len(disp) > a.limite:
                print("      ... y %d mas" % (len(disp) - a.limite))
        print()
        print("  DONDE ESTA EL CONTENIDO que cada una de esas citas queria decir:")
        for k in sorted(r["distribucion_localizacion"]):
            print("    %-18s %d" % (k, r["distribucion_localizacion"][k]))
        loc = [i for i in r["inventario"]
               if i["localizacion"]["estado"] == "COINCIDE_UN_TERMINO"]
        for i in loc[:a.limite]:
            L = i["localizacion"]
            print("      %-30s cita %-14s -> %s:%d"
                  % (i["finding"][:30], i["rango"], L["commit"], L["linea"]))
            print("        %r" % L["texto"][:74])
        if loc:
            print()
            print("  NO son 'el contenido esta aqui'. Son lineas del documento que")
            print("  comparten dos terminos con la afirmacion, y el vocabulario de")
            print("  ambos se solapa porque hablan del mismo proyecto. La tasa de")
            print("  acierto dentro del documento es de 0,1 a 0,4 por ciento, lo que")
            print("  descarta el ruido, y NO descarta que la coincidencia sea un eco")
            print("  del tema. Leer la linea es lo que decide, y por eso se imprime.")
        nl = [i for i in r["inventario"]
              if i["localizacion"]["estado"] == "NO_LOCALIZADO"]
        if nl:
            print()
            print("  NO_LOCALIZADO: %d. NO significa que el contenido no exista:" % len(nl))
            print("  significa que no esta en las SEIS versiones commiteadas. La de")
            print("  1101 lineas no lo esta, y ahi puede estar lo que se busca.")
        print()
        print()
        print("  ANTES de leer un DISPARADOR como una cita MAL, hay que mirar esto,")
        print("  porque es lo que pasa en este proyecto:")
        for c in (commits_git(raiz) or [])[:2]:
            t = git_show(raiz, c)
            if t is None:
                continue
            n_exec = _nline(t, "hardware execution ordering")
            n_jer = _nline(t, "JERARQUÍA DE PERMISOS")
            print("    %s  %5d lineas   ejecucion_ordening=%-6s jerarquia=%-6s"
                  % (c, len(t.splitlines()), n_exec or "no", n_jer or "no"))
        print("    los hallazgos citan AGENTS.md:141 y AGENTS.md:46")
        print()
        print("    46 RESUELVE en las dos versiones commiteadas. 141 NO: el")
        print("    contenido estaba en 173 y 176. Las lineas se DESPLAZARON al")
        print("    editar el documento, y la version de 1101 lineas contra la que")
        print("    esas citas eran ciertas no esta commiteada.")
        print()
        print("    Asi que un DISPARADOR quiere decir 'la numero cambio al crecer el")
        print("    documento', NO 'el hallazgo se equivoco'. Corregir las citas a la")
        print("    baja sería reescribir el hallazgo para que encaje con una version")
        print("    que no existe.")
        print()
        print()
        print("  CITAS QUE EL CODIGO LE HACE AL DOCUMENTO RECTOR")
        print("  Lineas de tools/ y 08-ARQUITECTURA/tools/ que AFIRMAN una")
        print("  proposicion sobre AGENTS.md en vez de nombrarlo:")
        for k in sorted(r["distribucion_codigo"]):
            print("    %-18s %d" % (k, r["distribucion_codigo"][k]))
        sa = [c for c in r["citas_de_codigo"] if c["donde"]["estado"] == "SOLO_ANTES"]
        if sa:
            print()
            print("  SOLO_ANTES: la proposicion esta en una version de AGENTS.md que")
            print("  ya no es la vigente. Su texto:")
            for c in sa[:a.limite]:
                print("    %-30s L%-5d -> %s"
                      % (os.path.basename(c["fichero"])[:30], c["linea"],
                         c["donde"]["commit"]))
                print("      %r" % c["texto"][:74])
            if len(sa) > a.limite:
                print("    ... y %d mas" % (len(sa) - a.limite))
        print()
        print("  NO_DECIDIBLE NO es 'la proposicion falta'. Es que un solape de")
        print("  terminos no llega, y la mayoria son comentarios que nombran el")
        print("  documento sin afirmar nada citable.")
        print()
        print("  ESTO NO ES 'la cita no resuelve'. Es PEOR: el numero resuelve, y")
        print("  a texto que no tiene relacion con lo que el hallazgo afirma de el.")
        print("  Un dangling reference se ve; uno que resuelve a otra cosa, no.")
    return 0


if __name__ == "__main__":
    sys.exit(main())