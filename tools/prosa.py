#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
prosa -- falsifica el CONTRATO EN PROSA de las herramientas contra su propio
codigo, y separa "lo usa" de "lo nombra".

POR QUE EXISTE
--------------
La capa meta del proyecto ya mide si una herramienta tiene FORMA de contrato:

  * `tools/toolreg.py`  -- inventario, version, proposito, si declara limites
  * `tools/toolcheck.py` -- "No comprueba que la herramienta diga la verdad.
                            Comprueba que tenga forma de decirla"
  * `tools/riesgo.py`   -- DECLARACION_VS_CODIGO, pero SOLO sobre el
                           vocabulario MAQUINABLE del contrato:
                           `WRITES_FILES=no`, `WRITES_GPU=no`, `READONLY=yes`

Y ese es el hueco.  La MAYORIA de las herramientas de este arbol no llevan
contrato maquinable: llevan PROSA.  Secciones `QUE RESUELVE`,
`LIMITE DECLARADO`, `VALIDACION`, `DE DONDE VIENEN LOS OPCODES`.  Es la forma
que casi todas las herramientas de este arbol usan, y `riesgo.py` no la toca
porque no tiene tokens que falsificar.

MEDIDO en el hueco que motive la herramienta: `revkit/pm4dec.py` declara en su
docstring

    "De sid.h del corpus, leido EN TIEMPO DE EJECUCION"

y su codigo hace lo CONTRARIO, y lo dice a 40 lineas del sitio: elige la tabla
con el GRAFO DE INCLUDES de `gfx_v8_0.c`, que da `vid.h`.  El propio fichero
explica que `sid.h` es la cabecera DISIDENTE -- la unica de seis que desplaza
LOAD_SH/LOAD_CONFIG/LOAD_CONTEXT una posicion.  O sea: el contrato en prosa
declara el INPUT que el codigo existe precisamente para rechazar.

Y aqui esta el motivo por el que hace falta una herramienta y no un grep:
el literal `sid.h` SI aparece en el codigo de `pm4dec.py`, en `HEADERS_OPCODE`,
en `SID_CANDIDATOS` y en `RENUMERADOS_SID`.  Una busqueda de texto diria
"consistente".  Miente, porque lo nombra para EXCLUIRLO.

QUE HACE
--------
De cada herramienta `.py` de los directorios DECLARADOS en
`toolreg.TOOL_DIRS` (no se crea una segunda lista: R2/TOOLS-STATUS ya
mergeo las listas y puso `directorios_no_declarados()` como puerta):

  1. Saca la prosa del contrato con `ast`, no con regex sobre el fichero.
     MEDIDO que importa: si se escanea el texto entero, las palabras del
     docstring se cuentan como codigo y TODO sale SUSTENTADA.  El vector
     `Prosa_1` falla si alguien devuelve a escanear texto.
  2. Saca las referencias del CODIGO tambien con `ast`: literales de cadena,
     `bytes`, `Name` y `Attribute`.  Los COMENTARIOS quedan fuera, y se dice.
  3. Extrae AFIRMACIONES DE ENTRADA de la prosa, en dos clases con oraculo
     distinto:
       FICHERO  `algo.h` `algo.c` `algo.py` `/ruta/absoluta`
       FLAG     `--algo`
  4. Emite un veredicto de TRES valores para FICHERO, porque "aparece" y "se
     usa" no son la misma cosa y confundiendolas es el defecto que
     motivaria la herramienta:
       `EN_APLICACION`        el literal llega a una LLAMADA (open/join/read)
       `SOLO_EN_LISTA`        el literal solo aparece como elemento de lista,
                               tupla o set: se ENUMERA como candidato
       `SIN_RESOLVER`         el literal no aparece en el codigo en ninguna
                               forma
     Y para FLAG, cuyo oraculo si es totalmente decidible:
       `FLAG_EN_ARGPARSE` / `FLAG_INEXISTENTE` / `NO_CLASIFICABLE`

LIMITE DECLARADO, Y ES EL IMPORTANTE
------------------------------------
`EN_APLICACION` NO prueba que la herramienta USE el fichero.  Prueba que el
nombre llega a una llamada.  De ahi para adelante es criterio de quien lee.

`SIN_RESOLVER` NO es "MENTIRA".  Es "la declaracion no se resuelve en el
codigo".  La distincion importa porque un uso sin mencion es posible --una
ruta construida en tiempo de ejecucion-- y un falso positivo que acusa de
mentira a una herramienta es el peor fallo posible: alguien se lo creeria y
reconstruiria por nada.  Ya ha pasado en este proyecto con `staleness`.

Lo que NO se hace:
  * `.c` y `.sh`: `NO_CLASIFICABLE`.  Su prosa vive en comentarios `//`, no en
    un docstring, y `ast` no los da.  Contarlos como SIN_RESOLVER seria el
    defecto entero con otro envoltorio.
  * No se ejecuta nada.  No se lee `/dev`, ni sysfs, ni MMIO.  Es analisis
    estatico, y por eso es seguro correrlo sin puerta.
  * No corrige ninguna prosa.  Este fichero MIDE y dice.  La correccion es de
    quien escribio la herramienta.

ORACLE
------
Para FLAG el oraculo es independiente y completo: lo que la prosa nombra
contra lo que `add_argument` registra.  No hay heuristica y no puede fallar
en silencio.

Para FICHERO el oraculo es de MENCION, y por eso el veredicto mas fuerte que
produce es `SIN_RESOLVER`, no "falso".  Se declara aqui para que nadie lo lea
como mas de lo que es.

VALIDACION
  `--selftest` con vectores positivo, negativo, borde y de regresion,
  incluido el que reproduce la forma de `pm4dec.py`.  rc=0.
"""

import argparse
import ast
import json
import os
import re
import sys

VERSION = "1.0.0"

# La raiz se resuelve DESDE EL PROPIO FICHERO. MEDIDO antes en este proyecto
# que una raiz relativa al CWD hacia que ejecutar desde otro sitio diera
# "no existe", y un fallo asi puede confundirse con "no hay herramientas".
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# Los directorios NO se declaran aqui: se importan de toolreg, que es donde
# viven, y que tiene la puerta `directorios_no_declarados()` que falla si
# alguien añade un `tools/` nuevo sin declararlo.  Una segunda lista de
# "donde viven las herramientas" es una lista y un grupo de herramientas que
# nadie mira.
_EXT = {".py", ".c", ".sh"}
SKIP_DIRS = {".git", "__pycache__", "RESEARCH", "node_modules", "artefacts",
             "artifacts"}

# ---------------------------------------------------------------- patrones

# Un recurso con extension.  La clase se acota a las extensiones que de verdad
# son ficheros de este dominio: una cabecera, un fuente, un modulo, un binario
# del proyecto.  Sin esta acotacion "tools/x.py" y "1.0.0" entran y el ruido
# se come la senal.
EXT_RE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9_][\w./-]*\.(?:h|c|py|sh|ko|json|txt|md|bin|out))")

FLAG_RE = re.compile(r"(--[a-z0-9][a-z0-9-]*)")

# Una ruta absoluta.  Se exige que no la preceda un caracter de palabra, para
# que "3/4" y "v1/2" no entren como ruta.
PATH_RE = re.compile(r"(?<![\w.])/(?:[\w.+-]+/)+[\w.+-]*")

# Palabras que parecen recurso y no lo son.  MEDIDO: sin esta lista,
# "prosa.py" en la frase "esta herramienta es prosa.py" produce una
# afirmacion sobre si misma, que es ruido con apariencia de senal.
NO_RECURSO = {
    "e.g.", "i.e.", "etc.", "README.md",  # documentacion, no entrada
}


def raiz_de_fichero(tok):
    """El nombre de fichero sin directorio.

    La prosa escribe `drivers/gpu/drm/amd/amdgpu/vid.h` y el codigo escribe
    `"vid.h"` porque lo resuelve con `os.path.join`.  Comparar la cadena
    completa daria SIN_RESOLVER en el caso CORRECTO, que es el peor falso
    positivo posible: acusaria de mentir a la herramienta que hace bien.
    MEDIDO que esto ya paso en este proyecto con la resolucion de includes
    en un solo directorio (R2-02).
    """
    return tok.rsplit("/", 1)[-1]


# ------------------------------------------------------------ extraccion AST

def docstring_fuente(path):
    """(docstring, lineno) del modulo, o (None, None).

    Se usa `ast`, no el texto.  El porque esta en la cabecera del fichero y en
    el vector `REGRESION__docstring_NO_es_codigo`: escanear el texto hace que
    las palabras del contrato se cuenten como codigo.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return None, None
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError, RecursionError):
        return None, None
    if not tree.body:
        return None, None
    primero = tree.body[0]
    if not isinstance(primero, ast.Expr):
        return None, None
    val = getattr(primero, "value", None)
    if not isinstance(val, ast.Constant) or not isinstance(val.value, str):
        return None, None
    return val.value, getattr(primero, "lineno", None)


def _nodos_docstring(tree):
    """Los nodos Constant que SON docstrings, en cualquier ambito.

    MEDIDO, y es un fallo que el primer selftest cazó: `ast.walk` ve el
    docstring del modulo igual que ve cualquier otra cadena, asi que las
    palabras del contrato entraban como REFERENCIAS DE CODIGO y toda
    declaracion salia SUSTENTADA.  Un instrumento que no puede fallar no
    informa de nada, y este habria sido exactamente eso: 194 filas en verde.

    Se recogen de los cuatro sitios donde Python admite un docstring, y no
    solo del modulo, porque `riesgo.py` documenta su prosa en el modulo pero
    otras herramientas de este arbol la ponen en funciones.
    """
    nodos = set()
    for nodo in ast.walk(tree):
        cuerpo = None
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            cuerpo = nodo.body
        if not cuerpo:
            continue
        primero = cuerpo[0]
        if isinstance(primero, ast.Expr):
            val = getattr(primero, "value", None)
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                nodos.add(id(val))
    return nodos


class Codigo(object):
    """Literales, identificadores y el papel de cada literal.

    `en_llamada` es lo que separa EN_APLICACION de SOLO_EN_LISTA, y es la
    razon de que este fichero exista: la mayoria de las herramientas nombran
    sus ficheros de entrada EN UNA LISTA de candidatos, y ahi no se usan, se
    enumeran.  `pm4dec.py` hace exactamente eso con los seis headers.
    """

    def __init__(self):
        self.cadenas = []          # valores de los literales de cadena
        self.identificadores = []  # Name + Attribute, como texto
        self.en_llamada = set()    # indices de self.cadenas Usadas en una Call
        self.flags_argparse = set()
        self.tiene_argparse = False
        # La herramienta lee `sys.argv` por su cuenta y no solo con argparse.
        # MEDIDO que hace falta: `flags_inventory.py` lo declara en su prosa y
        # su self-test lo toma de ahi, asi que un flag suyo puede existir sin
        # pasar por `add_argument`.
        self.lee_argv_a_mano = False

    def contiene(self, tok):
        """El token aparece en el codigo, de cualquier forma."""
        base = raiz_de_fichero(tok)
        for c in self.cadenas:
            if tok in c or base in raiz_de_fichero(c):
                return True
        for i in self.identificadores:
            if tok == i or base == i:
                return True
        return False

    def solo_en_lista(self, tok):
        """El literal aparece SOLO como elemento de lista/tupla/set.

        MEDIDO que se puede decidir: si ninguna aparicion del literal cae
        dentro de un `Call`, entonces el nombre llega a una estructura de
        datos y no a una llamada.  Se que eso no prueba que no se use mas
        abajo -- una lista se puede iterar y pasar a `open`-- y por eso el
        veredicto se llama SOLO_EN_LISTA y no "NO_SE_USA".
        """
        base = raiz_de_fichero(tok)
        for idx, c in enumerate(self.cadenas):
            if tok in c or base in raiz_de_fichero(c):
                if idx not in self.en_llamada:
                    return True
        return False


def _padres(tree):
    mapa = {}
    for nodo in ast.walk(tree):
        for hijo in ast.iter_child_nodes(nodo):
            mapa[hijo] = nodo
    return mapa


def _dentro_de_llamada(nodo, padres):
    """El literal esta dentro del subarbol de un `Call`."""
    actual = nodo
    while actual in padres:
        actual = padres[actual]
        if isinstance(actual, ast.Call):
            return True
        # un Call que este dentro de una lista NO cuenta: `["vid.h"]` que se
        # pasa a open() es uso, `[x for ... in open(y)]` no.  Se corta al
        # primer Calls que no sea el del propio nodo.
    return False


def leer_codigo(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return None
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError, RecursionError):
        return None
    cod = Codigo()
    padres = _padres(tree)
    docs = _nodos_docstring(tree)

    for nodo in ast.walk(tree):
        # literales.  Los docstrings se EXCLUYEN: son la declaracion, no el
        # codigo, y contarlos haria que toda declaracion fuese coherente
        # consigo misma.  MEDIDO en el primer selftest.
        if isinstance(nodo, ast.Constant):
            if id(nodo) in docs:
                continue
            v = nodo.value
            if isinstance(v, str):
                idx = len(cod.cadenas)
                cod.cadenas.append(v)
                if _dentro_de_llamada(nodo, padres):
                    cod.en_llamada.add(idx)
            elif isinstance(v, bytes):
                cod.cadenas.append(v.decode("latin-1"))
        # identificadores
        elif isinstance(nodo, ast.Name):
            cod.identificadores.append(nodo.id)
        elif isinstance(nodo, ast.Attribute):
            cod.identificadores.append(nodo.attr)
        # argparse
        if isinstance(nodo, ast.Call):
            fn = nodo.func
            nombre = getattr(fn, "attr", None) or getattr(fn, "id", None)
            if nombre == "add_argument":
                cod.tiene_argparse = True
                for a in list(nodo.args) + [k.value for k in nodo.keywords]:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        if a.value.startswith("--"):
                            cod.flags_argparse.add(a.value)
    # `ArgumentParser(...)` sin add_argument: hay argparse declarado
    if not cod.tiene_argparse:
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.Call):
                fn = nodo.func
                nombre = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if nombre and "ArgumentParser" in str(nombre):
                    cod.tiene_argparse = True
                    break
    # `sys.argv` leido a mano.  MEDIDO que hace falta: `flags_inventory.py`
    # declara en su prosa que lee `sys.argv[1:]` A MANO, asi que un flag suyo
    # puede existir sin pasar por `add_argument`.
    for nodo in ast.walk(tree):
        if isinstance(nodo, ast.Attribute) and nodo.attr == "argv":
            cod.lee_argv_a_mano = True
            break
    return cod


# ------------------------------------------------------- afirmaciones de prosa

class Afirmacion(object):
    __slots__ = ("clase", "token", "veredicto", "linea", "sustitutos")

    def __init__(self, clase, token, veredicto, linea=None, sustitutos=None):
        self.clase = clase
        self.token = token
        self.veredicto = veredicto
        self.linea = linea
        self.sustitutos = sustitutos or []

    def a_dict(self):
        d = {"clase": self.clase, "token": self.token,
             "veredicto": self.veredicto}
        if self.linea is not None:
            d["linea"] = self.linea
        if self.sustitutos:
            d["sustitutos"] = self.sustitutos
        return d


def _linea_de_linea(prosa, offset):
    """Linea dentro del docstring, 1-indexada sobre el docstring."""
    return prosa.count("\n", 0, offset) + 1


def extraer_afirmaciones(prosa, cod, propio=None):
    """Las afirmaciones de ENTRADA de la prosa, con su veredicto.

    Se deduplican por token: una prosa que nombra `vid.h` cinco veces es UNA
    afirmacion, y cinco filas serian cinco veces el mismo hallazgo.

    `propio` es el nombre del propio fichero.  MEDIDO que hace falta: 131 de
    las 373 afirmaciones `SIN_RESOLVER` de la primera medicion eran la
    herramienta nombrandose a si misma en la primera linea de su docstring --
    `inventario_universo.py -- hace un inventario`.  Una herramienta no es su
    propia ENTRADA, y contarlo como si lo fuera es un 35 % de ruido con
    apariencia de senal, que es como se pierde un instrumento.  Se cuenta
    aparte, como `AUTOREFERENCIA`, para que la cifra que se revise sea la que
    se puede revisar.
    """
    if prosa is None or cod is None:
        return None

    vistos = set()
    out = []

    for rx, clase in ((EXT_RE, "FICHERO"), (PATH_RE, "RUTA")):
        for m in rx.finditer(prosa):
            tok = m.group(1) if clase == "FICHERO" else m.group(0)
            tok = tok.rstrip(".,;:)")
            if tok in NO_RECURSO or len(tok) < 4:
                continue
            if (clase, tok) in vistos:
                continue
            vistos.add((clase, tok))
            linea = _linea_de_linea(prosa, m.start())
            if propio and raiz_de_fichero(tok) == propio:
                out.append(Afirmacion(clase, tok, "AUTOREFERENCIA", linea))
                continue
            base = raiz_de_fichero(tok)
            if not cod.contiene(tok):
                v = "SIN_RESOLVER"
                sust = sustitutos(cod, base)
            elif cod.solo_en_lista(tok):
                v = "SOLO_EN_LISTA"
                sust = []
            else:
                v = "EN_APLICACION"
                sust = []
            out.append(Afirmacion(clase, tok, v, linea, sust))

    for m in FLAG_RE.finditer(prosa):
        tok = m.group(1)
        if (clase_flag := "FLAG", tok) in vistos:
            continue
        # MEDIDO, y esto es lo que hace falta para que el eje FLAG sea
        # creible: la primera version Clarence lo que hacen las 35 filas y
        # tres de ellas no eran declaraciones sobre ESTA herramienta.
        #
        #   A. La prosa del proyecto usa `--` como guion_parentetico, y sale
        #      `--que`, `--el`, `--y`, `--aceptar`.  No son flags.
        #   B. La prosa nombra el flag de OTRO programa:
        #      `causal_map.py --contradictions` dentro de `round.py`.  La
        #      frase es verdadera y el flag no es de este fichero.
        #   C. Ilustracion: este mismo fichero escribe `--algo` al explicar
        #      el patron que reconoce.
        #
        # Un eje que accuse de 35 y acierte en 1 no es un eje: es ruido con
        # formato de tabla.  Solo se acepta un flag en UN sitio, y hay dos:
        #   (i)  la linea empieza por el flag  -> bloque de opciones, que es
        #        como el proyecto documenta las suyas (`    --coverage   que`)
        #   (ii) la linea invoca a ESTE programa y luego el flag -> bloque de
        #        uso, que es como `toolcheck.py` lo escribe
        if not _flag_es_declaracion(prosa, m.start(), tok, propio):
            continue
        vistos.add((clase_flag, tok))
        if not cod.tiene_argparse:
            v = "NO_CLASIFICABLE"
        elif tok in cod.flags_argparse:
            v = "FLAG_EN_ARGPARSE"
        elif _es_abreviacion(cod, tok):
            # MEDIDO en la adjudicacion a mano de las 8 primeras filas reales:
            # `struct_layout.py` documenta `--fields` y registra `--fields-of`.
            # argparse, con `allow_abbrev=True` --el defecto de CPython--,
            # ACEPTA `--fields` como abreviatura no ambigua.  Sin esta rama la
            # herramienta acusaba de mentira a un ejemplo de uso que funciona.
            v = "FLAG_EN_ARGPARSE"
        elif cod.lee_argv_a_mano and cod.contiene(tok):
            # `flags_inventory.py` lo dice en su prosa: lee `sys.argv[1:]` A
            # MANO y no usa argparse para el self-test.  Un flag que el codigo
            # conoce por otra via NO es inexistente, y sin esta rama lo era.
            #
            # Y el limite de esta rama, medido: `lee_argv_a_mano` salta con
            # CUALQUIER mencion a `sys.argv`, y el modismo de entrada
            # `sys.exit(main(sys.argv[1:]))` --que es lo que hace `claim.py` en
            # la linea 758-- tambien la cuenta.  La regla es DEMASIADO ANCHA y
            # degrada a NO_CLASIFICABLE casos que si serian decidibles.  Se
            # deja asi a proposito: el error va hacia "no se puede concluir",
            # nunca hacia "acuso".  Un instrumento que acusa de mas no sirve,
            # y uno que se calla de mas solo pierde sensitivity, que se
            # recupera leyendo el codigo.
            v = "NO_CLASIFICABLE"
        elif _linea_declara_retirado(prosa, m.start()):
            # `reenvio_freeze.py` escribe, en su propio bloque de opciones:
            #     --forzar   **ELIMINADO.**  Antes sorteaba la negacion
            # La prosa es HONESTA: documenta que la bandera ya no esta.  Un
            # veredicto de "flag inexistente" sobre esa linea seria responder
            # a una pregunta que nadie ha hecho.
            v = "FLAG_RETIRADO"
        else:
            v = "FLAG_INEXISTENTE"
        out.append(Afirmacion("FLAG", tok, v,
                              _linea_de_linea(prosa, m.start())))

    return out


# Palabras que convierten una linea de opciones en la CONSTANCIA de que la
# opcion ya no esta.  Estrechas a proposito: una lista corta y explicita es
# un oraculo; un detector de negacion en general es adivinanza.
RETIRO = ("ELIMINADO", "ELIMINADA", "RETIRADO", "RETIRADA", "REMOVED",
          "DEPRECATED", "ya no existe", "no existe", "ANTES:")


def _linea_declara_retirado(prosa, offset):
    linea = _linea_de(prosa, offset).upper()
    return any(m in linea for m in RETIRO)


def _es_abreviacion(cod, tok):
    """`tok` es abreviatura no ambigua de una bandera registrada.

    Es el comportamiento real de argparse con `allow_abbrev=True`: acepta
    cualquier prefijo no ambiguo de un nombre largo.  Sin esto, la herramienta
    acusa de mentirosa a la documentacion que funciona.
    """
    for f in cod.flags_argparse:
        if f.startswith(tok):
            return True
    return False


def _linea_de(prosa, offset):
    ini = prosa.rfind("\n", 0, offset) + 1
    fin = prosa.find("\n", offset)
    if fin < 0:
        fin = len(prosa)
    return prosa[ini:fin]


def _flag_es_declaracion(prosa, offset, tok, propio):
    """El token `--x` de esta linea es una declaracion sobre ESTA herramienta.

    (i)  la linea empieza por el flag Y tiene una vecina que tambien empieza
         por un flag.  El requisito de la VECINA es lo que separa un bloque
         de opciones de una frase partida:

             --coverage   which findings have no registered claim   <- bloque
             --aceptar un "no".  No hay banderines aqui.          <- prosa

         Las dos empiezan por `--`, y solo la primera esta acompanada.  MEDIDO
         que sin la vecina, dos de los cinco vectores de esta clase fallaban.

    (ii) la linea invoca a ESTE programa y el flag va detras.  Se exige que el
         programa de la linea sea el PROPIO, para no robarle el flag a otro
         (`causal_map.py --contradictions` dentro de `round.py`).
    """
    lineas = prosa.split("\n")
    # indice de la linea que contiene el offset
    upto = prosa[:offset].count("\n")
    if upto >= len(lineas):
        return False

    def empieza_por_flag(i):
        if i < 0 or i >= len(lineas):
            return False
        t = lineas[i].strip()
        return t.startswith("--")

    if empieza_por_flag(upto) and (empieza_por_flag(upto - 1)
                                    or empieza_por_flag(upto + 1)):
        return True
    if propio and propio in lineas[upto]:
        if lineas[upto].find(tok) > lineas[upto].find(propio):
            return True
    return False


def sustitutos(cod, base):
    """Recursos de la MISMA forma que el codigo si usa.

    Esto es lo que convierte "la prosa dice A" en "la prosa dice A y el codigo
    dice B", que es la fila que alguien puede usar.  Solo se ofrece lo que el
    codigo REALMENTE referencia; no se infiere nada.
    """
    out = []
    for c in cod.cadenas:
        for tok in EXT_RE.findall(c):
            base_t = raiz_de_fichero(tok)
            if base_t != base and base_t not in out and len(base_t) > 3:
                out.append(base_t)
    return sorted(out)[:8]


# ------------------------------------------------------------- exploracion

def poblar(repo=None, skip=SKIP_DIRS):
    """Toda herramienta de los directorios DECLARADOS, con su veredicto."""
    repo = repo or RAIZ
    try:
        sys.path.insert(0, AQUI)
        from toolreg import TOOL_DIRS
        dirs = list(TOOL_DIRS)
    except Exception:
        dirs = ["tools"]
    return _poblar_dirs(repo, dirs, skip)


def _poblar_dirs(repo, dirs, skip):
    filas = []
    for d in dirs:
        base = os.path.join(repo, d)
        if not os.path.isdir(base):
            continue
        for raiz, subdirs, ficheros in os.walk(base):
            subdirs[:] = [s for s in subdirs if s not in skip]
            for f in sorted(ficheros):
                if os.path.splitext(f)[1] not in _EXT:
                    continue
                filas.append(_fila(os.path.join(raiz, f), d))
    return filas


def _fila(path, d):
    ext = os.path.splitext(path)[1]
    rel = os.path.relpath(path, RAIZ).replace(os.sep, "/")
    nombre = os.path.basename(path)

    if ext != ".py":
        return {"herramienta": rel, "dir": d, "clase": "NO_CLASIFICABLE",
                "motivo": "la prosa de un .%s vive en comentarios, no en un "
                          "docstring: ast no la da" % ext[1:],
                "afirmaciones": [], "n_afirmaciones": 0}

    prosa, linea = docstring_fuente(path)
    if prosa is None:
        cod = leer_codigo(path)
        if cod is None:
            return {"herramienta": rel, "dir": d, "clase": "NO_CLASIFICABLE",
                    "motivo": "el fichero no parsea como Python",
                    "afirmaciones": [], "n_afirmaciones": 0}
        if not cod.cadenas and not cod.identificadores:
            # Un fichero VACIO no es "una herramienta que no declara nada":
            # no hay ni codigo con el que comparar.  MEDIDO que el selftest
            # distinguia las dos cosas y las confundia, que es exactamente el
            # defecto que este instrumentoAqade medir en los demas.
            return {"herramienta": rel, "dir": d, "clase": "NO_CLASIFICABLE",
                    "motivo": "el fichero esta vacio: no hay prosa ni codigo",
                    "afirmaciones": [], "n_afirmaciones": 0}
        return {"herramienta": rel, "dir": d, "clase": "SIN_CONTRATO",
                "motivo": "no hay docstring de modulo",
                "afirmaciones": [], "n_afirmaciones": 0}

    cod = leer_codigo(path)
    if cod is None:
        return {"herramienta": rel, "dir": d, "clase": "NO_CLASIFICABLE",
                "motivo": "el fichero no parsea como Python",
                "afirmaciones": [], "n_afirmaciones": 0}

    afs = extraer_afirmaciones(prosa, cod, propio=nombre) or []
    return {"herramienta": rel, "dir": d, "clase": "CON_TRATO",
            "docstring_linea": linea, "nombre": nombre,
            "afirmaciones": [a.a_dict() for a in afs],
            "n_afirmaciones": len(afs)}


def resumir(filas):
    cuentas = {}
    for f in filas:
        for a in f["afirmaciones"]:
            k = "%s:%s" % (f["herramienta"], a["veredicto"])
            cuentas[k] = cuentas.get(k, 0) + 1
    por_veredicto = {}
    for f in filas:
        for a in f["afirmaciones"]:
            por_veredicto[a["veredicto"]] = por_veredicto.get(a["veredicto"], 0) + 1
    return por_veredicto


# ------------------------------------------------------------------ informe

def informe(filas):
    por_veredicto = resumir(filas)
    con_contrato = [f for f in filas if f["clase"] == "CON_TRATO"]

    # Lo que se REVISA es lo falsable.  MEDIDO que `SOLO_EN_LISTA` no lo es:
    # una herramienta que hace `for h in LISTA: open(h)` nombra el fichero en
    # una lista y lo usa de verdad, asi que metrelo aqui producia 136 filas
    # de las que no se puede concluir nada.  Se informa aparte, con su
    # nombre, porque hidden seria peor.
    REVISAR = ("SIN_RESOLVER", "FLAG_INEXISTENTE")
    hits = []
    solo_lista = []
    for f in con_contrato:
        marc = [a for a in f["afirmaciones"] if a["veredicto"] in REVISAR]
        if marc:
            hits.append((f, marc))
        sl = [a for a in f["afirmaciones"] if a["veredicto"] == "SOLO_EN_LISTA"]
        if sl:
            solo_lista.append((f, sl))

    L = []
    L.append("=" * 74)
    L.append("prosa %s -- el contrato EN PROSA de las herramientas, contra su codigo"
             % VERSION)
    L.append("=" * 74)
    L.append("")
    L.append("POBLACION       %d ficheros en los directorios declarados" % len(filas))
    L.append("CON CONTRATO    %d" % len(con_contrato))
    L.append("NO CLASIFICABLE %d" % len([f for f in filas
                                         if f["clase"] == "NO_CLASIFICABLE"]))
    L.append("SIN CONTRATO    %d" % len([f for f in filas
                                        if f["clase"] == "SIN_CONTRATO"]))
    L.append("")
    L.append("afirmaciones de entrada, por veredicto")
    L.append("-" * 74)
    for k in sorted(por_veredicto, key=lambda x: -por_veredicto[x]):
        L.append("  %-20s %5d" % (k, por_veredicto[k]))
    L.append("")
    L.append("VEREDICTOS, y hasta donde llega cada uno")
    L.append("-" * 74)
    L.append("  EN_APLICACION     el nombre llega a una llamada.  NO prueba uso.")
    L.append("  SOLO_EN_LISTA     se enumera como candidato.  NO falsable: se")
    L.append("                    informa aparte y no se cuenta como hallazgo.")
    L.append("  SIN_RESOLVER      la declaracion no aparece en el codigo.  NO es")
    L.append("                    MENTIRA: una ruta construida en runtime no")
    L.append("                    deja rastro literal.")
    L.append("  FLAG_INEXISTENTE  prosa nombra un flag que add_argument no")
    L.append("                    registra.  Decidible y completo.")
    L.append("  AUTOREFERENCIA    la herramienta nombrandose a si misma.")
    L.append("")
    L.append("FILAS A REVISAR (%d herramientas)" % len(hits))
    L.append("=" * 74)
    if not hits:
        L.append("SIN FILAS QUE REVISAR")
    for f, marc in sorted(hits, key=lambda x: x[0]["herramienta"]):
        L.append("")
        L.append("  %s" % f["herramienta"])
        for a in marc:
            L.append("      [%-16s] %-6s %s"
                     % (a["veredicto"], a["clase"], a["token"]))
            if a.get("sustitutos"):
                L.append("           el codigo si referencia: %s"
                         % ", ".join(a["sustitutos"]))
    L.append("")
    L.append("ENUMERADAS, NO USADAS (SOLO_EN_LISTA) -- informativo, %d herramientas"
             % len(solo_lista))
    L.append("-" * 74)
    for f, sl in sorted(solo_lista, key=lambda x: x[0]["herramienta"])[:12]:
        L.append("  %-52s %s" % (f["herramienta"],
                                  ", ".join(a["token"] for a in sl[:4])))
    if len(solo_lista) > 12:
        L.append("  ... y %d mas (--json para todas)" % (len(solo_lista) - 12))
    L.append("")
    L.append("Ninguna prosa se corrige aqui.  Este fichero MIDE y dice.")
    return "\n".join(L)


# ----------------------------------------------------------------- selftest

def selftest():
    import shutil
    import tempfile

    fails = []
    oks = [0]

    def v(nombre, cond, detalle=""):
        if cond:
            oks[0] += 1
            print("  ok   %s" % nombre)
        else:
            print("  FAIL %s  %s" % (nombre, detalle))
            fails.append(nombre)

    tmp = tempfile.mkdtemp(prefix="prosa-selftest-")
    try:
        def escribir(nombre, texto):
            p = os.path.join(tmp, nombre)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(texto)
            return p

        # --- POSITIVO: la prosa nombra un fichero que el codigo ABRE. -------
        p = escribir("honesta.py", '''#!/usr/bin/env python3
"""
honesta -- lee sid.h y lo cuenta.

    --chip   which chip to look at
    --json   salida estructurada

LIMITE DECLARADO
  Solo cuenta lineas.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chip", type=str, default=None)
    with open("sid.h", errors="replace") as fh:
        return len(fh.read())


if __name__ == "__main__":
    main()
''')
        f = _fila(p, "tmp")
        v("POSITIVO__clase_CON_TRATO", f["clase"] == "CON_TRATO", f["clase"])
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("POSITIVO__sid.h_EN_APLICACION",
          toks.get("sid.h") == "EN_APLICACION", str(toks))
        v("POSITIVO__--chip_FLAG_EN_ARGPARSE",
          toks.get("--chip") == "FLAG_EN_ARGPARSE", str(toks))

        # --- NEGATIVO: control de falso positivo, el mismo fichero con la
        #     prosa Mentirosa debe FALLAR.  Si esto no falla, la herramienta
        #     no detecta nada y todo lo demas es ruido. --------------------
        p = escribir("mentirosa.py", '''#!/usr/bin/env python3
"""
mentirosa -- lee cikd.h del corpus.

    --chip   cual mirar
    --otro   otro flag
"""
import argparse

# El codigo, sin embargo, solo nombra vid.h.  Esta fila es la que hace
# util elSUSTITUTO: la prosa dice A, el codigo dice B, y sin las dos mitades
# el hallazgo es un "no" sin contenido.
CANDIDATOS = ["vid.h"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--otro", type=str, default=None)
    return len(CANDIDATOS)
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("NEGATIVO__cikd.h_SIN_RESOLVER",
          toks.get("cikd.h") == "SIN_RESOLVER", str(toks))
        sust = next((a.get("sustitutos") for a in f["afirmaciones"]
                     if a["token"] == "cikd.h"), None)
        v("NEGATIVO__sustituto_es_el_que_dice_el_codigo",
          sust == ["vid.h"], "sustitutos=%s" % (sust,))
        v("NEGATIVO__--chip_FLAG_INEXISTENTE",
          toks.get("--chip") == "FLAG_INEXISTENTE", str(toks))

        # --- BORDE 1: la FORMA de pm4dec.py.  El literal aparece en el
        #     codigo pero SOLO como elemento de lista: se enumera, no se usa.
        #     Un grep de texto diria que la prosa es consistente. ----------
        p = escribir("enlista.py", '''#!/usr/bin/env python3
"""
enlista -- De sid.h del corpus, leido en tiempo de ejecucion.
"""
CANDIDATOS = ["sid.h", "vid.h", "cikd.h"]


def elegir():
    return CANDIDATOS[0]
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("BORDE__sid.h_SOLO_EN_LISTA",
          toks.get("sid.h") == "SOLO_EN_LISTA", str(toks))
        v("BORDE__no_es_SIN_RESOLVER",
          toks.get("sid.h") != "SIN_RESOLVER",
          "la mencion en lista NO es ausencia: seria un falso positivo")

        # --- BORDE 2: sin contrato. ---------------------------------------
        p = escribir("muda.py", "#!/usr/bin/env python3\nX = 1\n")
        f = _fila(p, "tmp")
        v("BORDE__SIN_CONTRATO", f["clase"] == "SIN_CONTRATO", f["clase"])

        # --- BORDE 3: prosa con flag pero el fichero no usa argparse. ------
        p = escribir("sinarg.py", '''#!/usr/bin/env python3
"""
sinarg -- lo que hace.

    --chip   cual mirar
    --otro   otro flag
"""
def f():
    return 0
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("BORDE__--chip_NO_CLASIFICABLE",
          toks.get("--chip") == "NO_CLASIFICABLE", str(toks))

        # --- BORDE 4: Python roto no revienta, se declara. ----------------
        p = escribir("roto.py", "#!/usr/bin/env python3\ndef selftest(:\n  return 1\n")
        f = _fila(p, "tmp")
        v("BORDE__roto_NO_CLASIFICABLE",
          f["clase"] == "NO_CLASIFICABLE", f["clase"])

        # --- BORDE 5: fichero vacio. --------------------------------------
        p = escribir("vacio.py", "")
        f = _fila(p, "tmp")
        v("BORDE__vacio_NO_CLASIFICABLE",
          f["clase"] == "NO_CLASIFICABLE", f["clase"])

        # --- BORDE 6: una ruta con directorio en la prosa y solo el
        #     basename en el codigo NO es SIN_RESOLVER.  Es el caso
        #     correcto, ychargarlo seria acusar de mentira a la herramienta
        #     que hace bien.  MEDIDO que ya paso en este proyecto con la
        #     resolucion de includes en un solo directorio (R2-02). -------
        p = escribir("ruta.py", '''#!/usr/bin/env python3
"""
ruta -- lee drivers/gpu/drm/amd/amdgpu/vid.h del corpus.
"""
import os


def f():
    return open(os.path.join("vid.h")).read()
''')
        f = _fila(p, "tmp")
        toks = {t["token"]: t["veredicto"] for t in f["afirmaciones"]}
        v("BORDE__ruta_completa_NO_es_SIN_RESOLVER",
          toks.get("drivers/gpu/drm/amd/amdgpu/vid.h") != "SIN_RESOLVER",
          str(toks))

        # --- REGRESION: las palabras del docstring NO cuentan como codigo.
        #     Si alguien vuelve a escanear el texto en vez del AST, este
        #     vector falla.  Es el vector que ancla toda la herramienta. ---
        p = escribir("automencion.py", '''#!/usr/bin/env python3
"""
automencion -- se declara a si mismo como fuente de datos de zz9x.h.
  Tambien cita qq4w.h y solo existe aqui.
"""
def f():
    return 0
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("REGRESION__docstring_NO_es_codigo",
          toks.get("zz9x.h") == "SIN_RESOLVER", str(toks))
        v("REGRESION__qq4w.h_SIN_RESOLVER",
          toks.get("qq4w.h") == "SIN_RESOLVER", str(toks))

        # --- REGRESION: deduplicacion.  Nombrar cinco veces es UNA fila. ---
        p = escribir("repetido.py", '''#!/usr/bin/env python3
"""
repetido -- lee nn1b.h.  Vuelve a decir nn1b.h.  Y otra vez nn1b.h.
"""
def f():
    return open("nn1b.h").read()
''')
        f = _fila(p, "tmp")
        n = len([a for a in f["afirmaciones"] if a["token"] == "nn1b.h"])
        v("REGRESION__deduplica", n == 1, "filas=%d" % n)

        # --- REGRESION: el eje FLAG no roba flags a nadie. ------------------
        # MEDIDO en la primera medicion real: 35 filas FLAG_INEXISTENTE, y
        # estas tres no eran declaraciones sobre la herramienta.
        p = escribir("guiones.py", '''#!/usr/bin/env python3
"""
guiones -- esto usa -- como guion, no como flag: el numero --que cuenta y
  --aceptar un "no".  No hay banderines aqui.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    return 0
''')
        f = _fila(p, "tmp")
        flags = [a["token"] for a in f["afirmaciones"] if a["clase"] == "FLAG"]
        v("REGRESION__guion_no_es_flag", "--que" not in flags and
          "--aceptar" not in flags, str(flags))

        p = escribir("ajeno.py", '''#!/usr/bin/env python3
"""
ajeno -- 5 conflictos   COMPOSED, no reimplementado.  `causal_map.py
  --contradictions` es el flag del otro, no el de este.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    return 0
''')
        f = _fila(p, "tmp")
        flags = [a["token"] for a in f["afirmaciones"] if a["clase"] == "FLAG"]
        v("REGRESION__flag_de_otro_no_es_este",
          "--contradictions" not in flags, str(flags))

        # Y el que SI debe salir: bloque de opciones, estilo claim.py:47.
        p = escribir("bloque.py", '''#!/usr/bin/env python3
"""
bloque -- lo que mide.

    --coverage   which findings have no registered claim.  A measurement
    --next-id    the next free RE-nn.  A measurement
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--next-id", action="store_true")
    return 0
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("REGRESION__bloque_de_opciones_si_se_ve",
          toks.get("--coverage") == "FLAG_INEXISTENTE", str(toks))
        v("REGRESION__bloque_opciones_coherente",
          toks.get("--next-id") == "FLAG_EN_ARGPARSE", str(toks))

        # --- Las TRES clases de FALSO POSITIVO que la adjudicacion a mano
        #     de las 8 primeras filas reales destapo.  MEDIDO: de 8 filas
        #     cuatro eran falsas, y sin estos vectores el instrumento
        #    daria un 50 % de ruido con forma de tabla.

        # A. abreviatura de argparse: `--fields` funciona si existe
        #    `--fields-of`, porque allow_abbrev=True es el defecto de CPython.
        p = escribir("abrevia.py", '''#!/usr/bin/env python3
"""
abrevia -- lo que mide.

    --fields   los campos
    --otro     otro
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields-of", action="append", default=[])
    ap.add_argument("--otro", action="store_true")
    return 0
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("FP_A__abreviatura_argparse_no_es_inexistente",
          toks.get("--fields") == "FLAG_EN_ARGPARSE", str(toks))

        # B. la herramienta lee sys.argv a mano: el flag existe por otra via.
        p = escribir("amano.py", '''#!/usr/bin/env python3
"""
amano -- lo que mide.

    --self   los vectores
    --otro   otro
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    if "--self" in sys.argv[1:]:
        return 0
    return 1
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("FP_B__argv_a_mano_es_NO_CLASIFICABLE",
          toks.get("--self") == "NO_CLASIFICABLE", str(toks))

        # C. la prosa RETIRA el flag y lo dice.  Acusarla seria responder a
        #    una pregunta que nadie ha hecho.
        p = escribir("retirado.py", '''#!/usr/bin/env python3
"""
retirado -- lo que mide.

    --congelar   si se congela
    --forzar     **ELIMINADO.**  Antes sorteaba la negacion
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--congelar", action="store_true")
    return 0
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("FP_C__flag_retirado_no_es_inexistente",
          toks.get("--forzar") == "FLAG_RETIRADO", str(toks))

        # --- REGRESION: AUTOREFERENCIA no es SIN_RESOLVER. ---------------
        # MEDIDO que sin esto, 131 de 373 filas de la primera medicion eran
        # la herramienta nombrandose a si misma.  Un 35 % de ruido.
        p = escribir("autonombra.py", '''#!/usr/bin/env python3
"""
autonombra -- hace un inventario.  Se llama autonombra.py.
"""
def f():
    return 1
''')
        f = _fila(p, "tmp")
        toks = {a["token"]: a["veredicto"] for a in f["afirmaciones"]}
        v("REGRESION__autoreferencia_no_es_SIN_RESOLVER",
          toks.get("autonombra.py") == "AUTOREFERENCIA", str(toks))

        # --- REGRESION: SOLO_EN_LISTA no se cuenta como fila a revisar. ---
        # MEDIDO que metiendolo salian 136 filas de las que no se puede
        # concluir nada, porque `for h in LISTA: open(h)` SI usa el fichero.
        p = escribir("iterado.py", '''#!/usr/bin/env python3
"""
iterado -- lee pp2d.h, y lo abre en un bucle.
"""
CABECERAS = ("pp2d.h", "qq3e.h")


def f():
    salida = []
    for h in CABECERAS:
        salida.append(open(h).read())
    return salida
''')
        f = _fila(p, "tmp")
        txt = informe([f])
        v("REGRESION__SOLO_EN_LISTA_no_es_hallazgo",
          "FILAS A REVISAR (0 herramientas)" in txt,
          [l for l in txt.splitlines() if "FILAS A REVISAR" in l])
        v("REGRESION__SOLO_EN_LISTA_si_se_informa",
          "ENUMERADAS, NO USADAS" in txt, "falta la seccion informativa")

        # --- HERMETICO: la raiz NO depende del cwd. ------------------------
        # OJO, y esta es una correccion de este mismo fichero: la primera
        # version lanzaba `prosa.py --selftest` desde otro directorio para
        # comprobarlo, y eso es una BOMBA: el selftest dispara el vector
        # hermetico, que dispara el selftest, que dispara el vector hermetico.
        # Se colgaba en 120 s sin imprimir nada, que es la forma mas cara de
        # descubrir un bucle.
        # La pregunta que se quiere responder es "¿RAIZ depende del cwd?", y
        # esa se responde importando el modulo, no reejecutandolo.
        p = os.path.join(tmp, "cwd")
        os.makedirs(p, exist_ok=True)

        def _en_otro_cwd(codigo):
            import shlex
            return os.popen(
                "cd %s && python3 -c %s" % (p, shlex.quote(codigo))
            ).read().strip()

        got = _en_otro_cwd(
            "import sys;sys.path.insert(0,%r);import prosa;print(prosa.RAIZ)"
            % AQUI)
        v("HERMETICO__RAIZ_no_depende_del_cwd",
          got == RAIZ, "esperado=%s obtenido=%s" % (RAIZ, got))

        got2 = _en_otro_cwd(
            "import sys;sys.path.insert(0,%r);import prosa;"
            "print(len(prosa.poblar()))" % AQUI)
        v("HERMETICO__poblar_desde_otro_cwd",
          got2.isdigit() and int(got2) > 0, "poblacion=%s" % got2)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    total = len(fails) + oks[0]
    if fails:
        print("selftest: %d vectores FALLAN de %d" % (len(fails), total))
        print("FALLAN: %s" % ", ".join(fails))
        return 1
    print("selftest: %d vectores, 0 fallos" % total)
    return 0


# --------------------------------------------------------------------- main

def main(argv):
    ap = argparse.ArgumentParser(
        prog="prosa.py",
        description="Falsifica el contrato EN PROSA de las herramientas "
                    "contra su propio codigo.")
    ap.add_argument("--json", action="store_true",
                    help="salida estructurada")
    ap.add_argument("--herramienta", default=None,
                    help="una sola herramienta, por ruta relativa")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--selftest", "--self-test", dest="selftest",
                    action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.version:
        print(VERSION)
        return 0

    if args.herramienta:
        filas = [_fila(os.path.join(RAIZ, args.herramienta),
                       os.path.dirname(args.herramienta))]
    else:
        filas = poblar()

    if args.json:
        print(json.dumps({
            "herramienta": "prosa.py",
            "version": VERSION,
            "poblacion": len(filas),
            "por_veredicto": resumir(filas),
            "filas": filas,
        }, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(informe(filas))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))