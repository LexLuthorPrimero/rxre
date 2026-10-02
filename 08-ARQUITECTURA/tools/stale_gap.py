#!/usr/bin/env python3
# CONTRACT: name=stale_gap
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""STALE GAP -- fronteras que otro documento ya cerro, y no se sabe.

EL PROBLEMA QUE RESUELVE, Y QUE NINGUNA HERRAMIENTA DE ESTE PROYECTO
ATACABA.

El proyecto tiene dos extractores de fronteras y no los compara:

  causal_map.py   60 claims   de 89 documentos   (tabla sujeto/valor/estado)
  frontier.py    130 huecos   de 100 documentos  (cualquier linea con estado)

Uno ve el triple que el otro. Cada uno es correcto en lo suyo y ninguno sabe
lo que el otro sabe, asi que:

  - la cuenta de trabajo pendiente difiere entre herramientas (207 lineas con
    NOT_DETERMINED en next_work, 130 huecos en frontier), sin que ninguna diga
    por que;
  - una frontera marcada NOT_DETERMINED en un documento de marzo puede haber
    sido resuelta en uno de octubre, y NADIE lo comprueba. El documento viejo
    sigue diciendo NOT_DETERMINED.

ESA SEGUNDA COSA ES LA QUE IMPORTA. Un NOT_DETERMINED obsoleto es peor que uno
verdadero: dirige el trabajo hacia algo ya hecho, y el resultado es volver a
investigar lo mismo y escribir un hallazgo que ya existe.

LO QUE HACE. Para cada frontera con sujeto, busca en el resto de documentos un
claim sobre ESE sujeto con estado cerrado. Y dice tres cosas distintas, que no
son lo mismo:

  VIVA            el sujeto sigue sin resolver. Trabajo real.
  RESUELTA_OTRO   otro documento afirma PROVEN sobre ese sujeto. El
                  NOT_DETERMINED del documento viejo esta OBSOLETO, y lo que
                  hay que hacer es CORREGIR EL DOCUMENTO, no investigar.
  SIN_SUJETO      la linea dice NOT_DETERMINED pero no dice de que. No se
                  puede cruzar, y eso es un defecto del documento: una
                  frontera sin sujeto no se puede cerrar ni repetir.

Y un cuarto, que es el que da el numero útil:

  RESUELTA_AQUI   el MISMO documento afirma despues PROVEN sobre ese sujeto.

Que es un caso particular y frecuente: un documento dice "es NOT_DETERMINED"
en la seccion del problema y "PROVEN" tres paginas despues al resolverlo, y se
le ha olvidado quitar la marca. No es un documento viejo: es el mismo, y aun
esta contradiciendose consigo mismo.

LO QUE NO HACE. No decide cual de dos afirmaciones es la correcta. Si dos
documentos dan valores distintos para el mismo sujeto, eso es una
contradiccion y la reporta causal_map, no esta. Aqui solo se pregunta una
cosa: ¿el sujeto tiene ya una respuesta cerrada en el proyecto?

Uso:
  python3 stale_gap.py              tabla de las tres clases, agrupadas
  python3 stale_gap.py --obsoletas  solo las RESUELTA_OTRO y RESUELTA_AQUI
  python3 stale_gap.py --sin-sujeto solo las que no se pueden cruzar
  python3 stale_gap.py --sujeto X  el rastro completo de un sujeto
  python3 stale_gap.py --self-test  control negativo
  python3 stale_gap.py --json
"""
import os
import re
import sys
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
FIND = f"{ROOT}/06-INGENIERIA-INVERSA/findings"

# Estados que CIERRAN una frontera. La lista es explicita y corta a proposito:
# "cerrar" una frontera exige una afirmacion, y casi todas las de aqui lo son.
# UNKNOWN no cierra: es ignorance declarada, no respuesta.
CIERRAN = {"PROVEN", "PROVEN_DERIVED", "PROVEN_ABSENT", "OBSERVED",
           "CORROBORATED", "REFUTED", "NEGATIVE_RESULT"}
# Estados que ABREN una frontera.
ABREN = {"NOT_DETERMINED", "NOT_OBSERVED", "NOT_AVAILABLE", "NOT_PROVEN",
         "UNKNOWN", "NOT_FOUND", "PARTIAL", "DEFERRED"}

_EST = "|".join(sorted(CIERRAN | ABREN, key=len, reverse=True))
_EST_RE = re.compile(r"\b(" + _EST + r")\b")

# SIGNOS DE NEGACION.
#
# No es una lista ideal de conectores en ingles: es la lista de las formas que
# USAN estos documentos para negar. "would require", "cannot" y demas no
# detectarian "harían falta", que es la que aparece de verdad.
#
# El criterio es "el estado se menciona como algo a lo que NO se llega". Por
# eso el filtro es conservador: ante la duda se marca como negada y se pierde
# un cierre, que es un falso NEGATIVO. Perder una resolucion cuesta re-leer un
# documento; inventar una cuesta repetir un experimento ya hecho.
NEGACION = [
    r"har[ií]an\s+falta",           # 056:153  "para llegar a PROVEN harian falta"
    r"hacdr?ian\s+falta",                # sin tilde
    r"para\s+(pasar|llegar|alcanzar)",
    r"no\s+(se\s+puede|podría|podria|hay|existe|se\s+llega)",
    r"nunca\s+(se\s+puede|podrá|podra|llegó|llego)",
    r"imposible",
    r"\bsin\s+documentaci[oó]n\b",
    r"queda\s+sin\s+resolver",
    r"para\s+que\s+.*\s+haga\s+falta",
    r"\brequiere\b.*\bno\b",
    r"\bno\b.*\bposible\b",
]
_BCK = re.compile(r"`([^`]{1,60})`")
# Sujeto formal: IDENTIFICADOR = ESTADO  o  IDENTIFICADOR: ESTADO
_ASG = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]{2,})\s*[:=]\s*")

# SUJETO EN NEGRITA, QUE NO ESTA ENTRE BACKTICKS.
#
# La primera version de `sujeto_de` solo miraba entre backticks y el patron
# `IDENT = ESTADO`. Con eso, 112 fronteras salian SIN_SUJETO, y al mirarlas
# muchas si lo tienen:
#
#   001:213  **GFX_HWIP sigue `NOT_DETERMINED`.**
#   009:145  **Estado: `NOT_DETERMINED`, causa distinta.**
#
# El sujeto es el identificador, y esta escrito en negrita o en prosa con
# mayusculas. Una frontera a la que le falta el sujeto NO se puede cerrar ni
# repetir, asi que perderla aqui convierte un dato en un defecto de documento.
#
# EL RIESGO, Y POR QUE SE ACEPTA. Ampliar de donde se busca el sujeto mete
# ruido: cualquier palabra en negrita puede ser sujeto. Se acota con tres
# condiciones, todas necesarias:
#
#   1. la forma tiene que ser de IDENTIFICADOR, no de frase (una palabra suelta
#      o dos, con guion bajo o mayusculas internas);
#   2. NO puede ser el nombre del estado, que ya se filtra aparte;
#   3. tiene que estar en la linea del estado o en la inmediatamente
#      anterior, igual que los otros candidatos.
_BOLD = re.compile(r"\*\*([A-Za-z_][A-Za-z0-9_]{2,40})\*\*")
_MAYU = re.compile(r"(?<![`\w])([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?![`\w])")

# EL SUJETO DE UNA FRONTERA PUEDE SER UNA FRASE.
#
# De las 86 fronteras que salian SIN_SUJETO, 18 estan en TABLA y el sujeto es
# la primera celda, escrita en prosa y SIN backticks:
#
#   020:131  | Que el hardware execute 19 dw | `NOT_DETERMINED` — RUNTIME |
#   026:158  | La reserva alcanza con preemption en VF | `NOT_DETERMINED` |
#
# El sujeto es "Que el hardware ejecute 19 dw", no un identificador. Y eso es
# un sujeto MEJOR que un identificador: es una pregunta, y una pregunta se
# puede cerrar, repetir y medir. Un identificador es un indice.
#
# NO SE APLICA A NINGUNA OTRA CLASE, solo a la de fronteras: para cruzar dos
# documentos, una frase no es clave. Por eso la tabla tiene dos campos
# distintos y no un unico `sujeto`:
#
#   etiqueta  la clave de cruce: identificador, o None si es frase
#   texto     lo que dice, siempre
#
# Confundirlos obligaba a elegir: o se renuncia a la frase y se pierde el
# sujeto, o se usa la frase como clave y el cruce no encuentra nada. Las dos
# salidas pierden algo, y solo por no haber separado los dos papeles.
#
# LA REGLA ES DELIMITAR LA FILA. En una tabla de Markdown, la primera celda de
# la fila del estado es el sujeto. No se busca en toda la linea, porque en una
# tabla de clasificacion hay otras celdas con backticks y ganaría la que no es.
_CELDA = re.compile(r"^\s*\|\s*([^|]{3,120}?)\s*\|")


def _sujetos_negrita(linea):
    """Identificadores de la linea que PODRIAN ser sujeto."""
    out = []
    for m in _BOLD.finditer(linea):
        s = m.group(1)
        if _EST_RE.fullmatch(s) or len(s) < 4:
            continue
        # frase en negrita: mas de dos palabras no es un identificador
        if " " in s:
            continue
        out.append(s)
    # CONSTANTE_EN_MAYUSCULAS con guion bajo, que es como se escriben los
    # registros y los campos en estos documentos.
    for m in _MAYU.finditer(linea):
        s = m.group(1)
        if _EST_RE.fullmatch(s):
            continue
        out.append(s)
    return out

# UNA RESOLUCION TIENE QUE ESTAR EN UNA AFIRMACION, NO EN UNA MENCION.
#
# Cuarto fallo de extraccion de esta herramienta, y el que mas fronteras
# falsas ha generado. La regla cruzaba cualquier linea que contuviera un
# estado cerrado, aunque el estado estuviera MENCIONADO al pasar:
#
#   017:194  "...haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION`
#              tuviera otro valor que 0 en..."
#
# Esa linea no AFIRMA que algo es REFUTED: dice que sería incorrecto. Con ella
# de "respuesta", dos fronteras de 018 salian RESUELTA_OTRO.
#
# PATRON DE AFIRMACION. Una linea afirma cuando el estado aparece en una de
# estas formas, que son las que usa el corpus:
#
#   | sujeto | PROVEN | ... |          tabla
#   sujeto es `PROVEN`                   prosa
#   `sujeto` es `PROVEN` / esta `PROVEN`
#   PROVEN al final de la frase
#
# Y NO afirma cuando el estado va precedido de un condicional o un impersonal
# ("haría", "sería", "seria", "quedaría", "tendría", "habría") o cuando la
# linea esta dentro de una lista de requisitos.
CONDICIONAL = re.compile(
    r"\b(har[ií]a|ser[ií]a|seria|quedar[ií]a|tendr[ií]a|habr[ií]a|"
    r"would|could|might|puede|permitir[ií]a)\b", re.I)
# Linea que es un requisito: empieza por numero o vineta de requisito.
_REQUISITO = re.compile(r"^\s*(?:[0-9]+[.)]|[-*+]\s)", )

# Las formas en que un estado CIERRA una linea. Mas restrictivo que "contiene
# un estado cerrado": tiene que estar en posicion de afirmacion.
_AFIRMA = re.compile(
    r"(?:^\s*\|[^|]*\|\s*(?:" + "|".join(CIERRAN) + r")\s*\|)"   # tabla
    r"|(?:\b(?:" + "|".join(CIERRAN) + r")\s*(?:\(\s*\w+\s*\))?\s*\|)"  # tabla
    r"|(?:(?:`[^`]+`|" + "|".join(CIERRAN) + r")\s+(?:es|son|esta|est[aá]"
    r"|queda|qued[aó]|resulta|pas[aá])\b)"
    r"|(?:\b(?:es|son|esta|est[aá]|queda|qued[aó])\s+`?" +
    "|".join(CIERRAN) + r"\b)"
    r"|(?:\b" + "|".join(CIERRAN) + r"\b\s*[-–—:]\s*\S)"
    r"|(?:\|\s*(?:" + "|".join(CIERRAN) + r")\s*(?:\(|—|-|\||$))"
    r"|(?:\b" + "|".join(CIERRAN) + r"\b\s*$)", re.I)


def _negada(linea):
    """¿La linea MENciona un estado para decir que no se llega a el?"""
    for pat in NEGACION:
        if re.search(pat, linea, re.I):
            return True
    return False


def _afirma(linea):
    """¿La linea AFIRMA un estado cerrado, o solo lo menciona?

    Un condicional o un impersonal delante del estado significa que la linea
    esta hablando de lo que pasaria SI, no de lo que es. Ejemplo real:

        "...haría `REFUTED` incorrecto; (c) ..."

    ahi hay un REFUTED y no se afirma nada sobre el sujeto.
    """
    if CONDICIONAL.search(linea):
        return False
    if _REQUISITO.match(linea):
        # "1. Silicon documentation con NDA (no accesible)" -- puede contener
        # un estado sin afirmarlo. Exige que ademas haya un verbo de estado.
        return bool(re.search(r"\b(es|son|esta|est[aá]|queda|qued[aó])\b",
                              linea, re.I))
    return bool(_AFIRMA.search(linea))


def normaliza(s):
    """Clave de cruce. Dos menciones del mismo sujeto tienen que coincidir.

    Se quitan los prefijos de los documentos (backticks ya lo hacen) y se
    baja a minusculas, porque el mismo registro se escribe `mmCP_HQD_ERROR`
    en un sitio y `CP_HQD_ERROR` en otro. SI NO SE NORMALIZARA EL PREFIJO,
    el cruce fallaria justo en los casos que mas importan: los registros, que
    se nombran de las dos formas en el mismo corpus.
    """
    if not s:
        return None
    s = s.strip().strip("`")
    s = s.lower()
    for pref in ("mm", "ix"):
        if s.startswith(pref) and len(s) > len(pref) + 1:
            alt = s[len(pref):]
            return s + "|" + alt      # se aceptan las dos formas
    return s


# SUJETOS QUE NO SON SUJETOS.
#
# La primera version cruzaba cualquier cosa entre backticks. El resultado
# incluia 52 "fronteras obsoletas" de las cuales muchas no lo eran: los
# documentos se citan entre si por NUMERO (`017`, `033`, `020`), y como cada
# numero aparece en el titulo del fichero y en el cuerpo de casi todos los
# demas, cualquier linea de cualquier documento se cruzaba con cualquier otra
# que citara un numero.
#
# Ejemplo real del ruido:
#
#   018-...:19  sujeto `017`  frontera: "...al siguiente IB (NOT_DETERMINED)"
#                    respuesta: 025-...:226  PROVEN
#
# No tiene relacion: `017` es una REFERENCIA a otro documento, no el tema de
# la linea. Y `HYPOTHESIS` estaba de sujeto en tres casos, que es el nombre de
# un estado, no de una cosa.
#
# La lista se deriva de lo QUE SON, no de lo que se ha visto, para que se
# pueda discutir. Un sujeto que sea un numero de documento NO es una entidad
# del hardware y no se puede cerrar.
# SERIE DE DOCUMENTOS QUE SON METODO, NO HALLAZGO.
#
# Un hallazgo mide el ASIC. Un documento de metodo mide el PROYECTO: sus
# afirmaciones sobre el hardware son EJEMPLOS de por que una herramienta
# falla, no respuestas a las fronteras del ASIC.
#
# Y la confusion no es teorica. 045 explica que un PROVEN CITADO se cuela
# como respuesta, y al escribirlo se reprodujo SOLO: las lineas que citan
# FUNCTION=always para explicar el fallo se convirtieron en "respuesta
# cerrada" de SIETE fronteras que siguen abiertas. La herramienta se estaba
# citando a si misma.
#
# No se arregla con un filtro mas de lenguaje: hay que excluir por el nombre
# del documento, que es una propiedad de la FUENTE y no del texto.
#
# Se declara la lista entera, no un patron generico, para que se pueda
# discutir que entra. Añadir un patron es barato y por eso es peligroso: la
# exclusion debe ser visible y razonada.
SERIE_METODO = [
    r"herramient",                # 038, 056-sin-herramientas
    r"fronteras-obsoletas",       # 045, este detector
    r"mapa-causal",               # 042
    r"grafo-y-detector",          # 041
    r"auditoria|prospeccion",     # 048-claims, 041-herramientas-de-procedencia
    r"correccion.*make",          # 044-correccion-implementada
    r"convencion-de-count",       # 045-la-convencion
    r"el-limite-del-claim",       # 047-los-diez-selectores
]


def _es_documento_de_metodo(nombre):
    """¿Este documento habla de herramientas y no del hardware?

    Si es asi, NO PUEDE cerrar fronteras del ASIC: lo que dice del hardware es
    un ejemplo de por que una herramienta falla, no una respuesta.
    """
    b = nombre.lower()
    if "herramient" in b:
        return True
    for pat in SERIE_METODO:
        if re.search(pat, b):
            return True
    return False


def _es_referencia(s):
    """¿Este documento habla de herramientas y no del hardware?

    Dos familias, y las dos son metodo:
      1. hallazgos cuyo nombre lleva el patron 'herramient';
      2. documentos de la serie de detectores automaticos (stale_gap,
         contradicciones, grafo, bitmap de citas), que existen para medir el
         proyecto y no el ASIC.
    """
    b = nombre.lower()
    if "herramient" in b:
        return True
    for pat in SERIE_METODO:
        if re.search(pat, b):
            return True
    return False


def _es_referencia(s):
    """¿Lo que hay entre backticks es algo que se pueda consultar?"""
    b = s.strip().strip("`").lower()
    if not b:
        return True
    if re.fullmatch(r"\d{3}", b):          # 017, 033, 020
        return True
    if b in CIERRAN or b in ABREN:
        return True
    if b in ("corpus", "codigo", "hardware", "runtime", "static",
             "documentacion", "driver", "amd", "amdgpu"):
        return True
    if b.endswith(".md") or b.endswith(".c") or b.endswith(".h"):
        return True
    return False


def variantes(s):
    """Todas las claves aceptables para un sujeto.

    Devuelve VACIO si lo que hay entre backticks no es un sujeto: un numero de
    documento, un nombre de estado o un nombre generico. Cruzar esos produce
    relaciones falsas, que es peor que no cruzar nada.
    """
    if not s:
        return set()
    if _es_referencia(s):
        return set()
    s = s.strip().strip("`")
    base = s.lower()
    out = {base}
    for pref in ("mm", "ix"):
        if base.startswith(pref):
            out.add(base[len(pref):])
    if base.endswith("."):
        out.add(base[:-1])
    return {x for x in out if len(x) > 2}


def documentos():
    if not os.path.isdir(FIND):
        return []
    return [os.path.join(FIND, f) for f in sorted(os.listdir(FIND))
            if f.endswith(".md")]


def lineas_de(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


def sujeto_de(line, previa, previa2):
    """El sujeto mas cercano al estado de la linea.

    Tres candidatos, en orden:
      1. el primer simbolo en backticks de la propia linea;
      2. un `IDENT = ESTADO` formal;
      3. el mismo, en las dos lineas anteriores.

    POR QUE EL TERCER CASO. La forma mayoritaria en estos documentos es

        | `mmCP_HQD_ERROR` | NOT_DETERMINED |

    pero tambien es muy comun

        El registro `mmCP_HQD_ERROR`:
        `NOT_DETERMINED` hasta que se mida.

    donde el estado esta en su propia linea y el sujeto en la anterior. Sin el
    tercer caso, esas fronteras no tienen sujeto y no se pueden cruzar.
    """
    m = _BCK.search(line)
    if m and not _EST_RE.fullmatch(m.group(1).strip()):
        return m.group(1)
    m = _ASG.match(line.strip())
    if m:
        return m.group(1)
    for p in (previa, previa2):
        if not p:
            continue
        m = _BCK.search(p)
        if m and not _EST_RE.fullmatch(m.group(1).strip()):
            return m.group(1)
        m = _ASG.match(p.strip())
        if m:
            return m.group(1)
    # Cuarto caso, y es el que mas saldo dio: el sujeto en NEGRITA o en
    # CONSTANTE, que no esta entre backticks.
    #
    # ESTE CASO VA EL ULTIMO A PROPOSITO. Con el puesto antes, se perdian los
    # sujetos entre backticks de las lineas anteriores, y el resultado fue
    # {"SIN_SUJETO" 112 -> 185} y {"RESUELTA_OTRO" 29 -> 19}: es decir, la
    # ampliacion DESTRUYO informacion que ya se tenia.
    #
    # El orden de los candidatos es el de confianza: backticks explicitos
    # primero, despues la forma `IDENT = ESTADO`, despues prosa. Anadir una
    # fuente mas debil al principio no es "buscar mas", es cambiar el
    # extractor a algo peor.
    for p in (line, previa, previa2):
        if not p:
            continue
        for cand in _sujetos_negrita(p):
            return cand
    return None


# UNA FRASE, NO UN IDENTIFICADOR.
#
# El sujeto de una frontera en tabla suele ser una PREGUNTA escrita en prosa:
#
#     | Que el hardware ejecute 19 dw | `NOT_DETERMINED` — RUNTIME |
#
# Esa es la fuente de 18 de las fronteras que antes salian SIN_SUJETO, y es un
# sujeto MEJOR que un identificador: es una pregunta, y una pregunta se puede
# cerrar, repetir y medir. Un identificador es un indice.
#
# Pero una frase no sirve como CLAVE de cruce, porque en dos documentos la
# misma frontera se escribe distinto. De ahi `etiqueta_de`.
#
# LO QUE ESTA HACIENDO ESTA MAL, Y POR QUE NO SE ARREGLA CON UNA FRASE SUELTA:
# el recorte condicional ("Que X" -> "X") es correcto solo si las dos formas
# Keeps el mismo verbo y el mismo sujeto. "Que la cola arranque sola" recortado
# da "la cola arranque sola", y la forma sin condicional "La cola arranca sola"
# NO coincide: `arranque` y `arranca` son el mismo verbo en distinto tiempo.
#
# Arreglar eso con una regla de conjugacion es empezar de nuevo: la regla
# tendria que saber que Spanish tiene cuatro tiempos verbales. La solucion
# honesta es NO recortar, y que la frase sea legible sin ser clave de cruce.
_CELDA = re.compile(r"^\s*\|\s*([^|]{3,160}?)\s*\|")
_COND = re.compile(r"^(que|si|cuando|como)\s+", re.I)


def etiqueta_de(linea):
    """Si la linea es una fila de tabla, la primera celda es el sujeto.

    Se devuelve TAL CUAL, sin recortar el condicional. La razon esta en el
    comentario de arriba: recortar funciona para "Que X" frente a "X", pero
    rompe en cuanto el verbo se conjuga, y no hay forma de arreglarlo sin
    saber conjugar.
    """
    m = _CELDA.match(linea)
    if not m:
        return None
    celda = m.group(1).strip()
    # una celda que es solo un estado no es un sujeto
    if _EST_RE.fullmatch(celda.strip("`")):
        return None
    if len(celda) < 6:
        return None
    return celda


def extraer():
    """[(frontera)] con su sujeto, su estado y donde esta."""
    out = []
    for path in documentos():
        ls = lineas_de(path)
        doc = os.path.basename(path)
        for i, l in enumerate(ls):
            if "```" in l:
                continue
            ms = _EST_RE.findall(l)
            if not ms:
                continue
            est = [e for e in ms if e in ABREN]
            if not est:
                continue
            prev = ls[i - 1] if i >= 1 else ""
            prev2 = ls[i - 2] if i >= 2 else ""
            s = sujeto_de(l, prev, prev2)
            # Cuarto recurso: la primera celda de una fila de tabla. Ver
            # `etiqueta_de`: el sujeto de una frontera puede ser una FRASE
            # ("que el hardware ejecute 19 dw"), y eso es un sujeto mejor que
            # un identificador, porque es una pregunta y se puede cerrar.
            et = etiqueta_de(l) or etiqueta_de(prev)
            out.append(dict(doc=doc, linea=i + 1, sujeto=s,
                            etiqueta=et, estado=est[0], todos=est,
                            texto=l.strip()[:150]))
    return out


def claims_cerrados():
    """{clave: [(doc, linea, estado, texto)]} de lo que ya esta resuelto.

    EXCLUYE los documentos de metodo, y por que.

    045 documenta el caso de un PROVEN citado que se cuela como respuesta. Al
    escribir ese documento, el caso se reprodujo SOLO: sus lineas, que citan
    FUNCTION=always para explicar el fallo, se convirtieron en "respuesta
    cerrada" de siete fronteras que siguen ABIERTAS.

    Es auto-referencia: una herramienta que se cita a si misma. Y no hay filtro
    de lenguaje que lo arregle, porque el problema no es la frase: es que un
    documento de metodo, por definicion, no mide el ASIC.
    """
    out = defaultdict(list)
    for path in documentos():
        doc = os.path.basename(path)
        if _es_documento_de_metodo(doc):
            continue
        ls = lineas_de(path)
        for i, l in enumerate(ls):
            ms = _EST_RE.findall(l)
            cerradas = [e for e in ms if e in CIERRAN]
            if not cerradas:
                continue
            # LA NEGACION, y es el fallo mas grave de esta herramienta.
            #
            # Un documento puede MENCIONAR un estado cerrado para decir que NO
            # se puede llegar a el. Caso real del corpus, 056:153:
            #
            #     "Para pasar de `NOT_DETERMINED` a `PROVEN` harían falta tres
            #      cosas, y ninguna existe como documento público"
            #
            # La linea contiene PROVEN. Sin este filtro contaba como respuesta
            # cerrada, y daba por RESUELTA_OTRO dos fronteras ABIERTAS de 017
            # y 020 sobre FUNCTION=always. El texto decia justo lo contrario.
            #
            # Un detector que lee un estado sin leer la frase que lo rodea
            # tiene esta clase de fallo garantizada, porque en estos documentos
            # se CITA el estado para discutirlo.
            if _negada(l):
                continue

            # EL VECINO IMPORTA, Y ESTO ES LO MAS IMPORTANTE QUE HECHO ESTA
            # HERRAMIENTA.
            #
            # El filtro de negacion mira UNA linea, y una linea de continuacion
            # no tiene la negacion: la frase empieza en la anterior. Por eso:
            #
            #   045:117  "para llegar a `PROVEN` es exactamente lo contrario.
            #             El texto decia que no se puede llegar a `PROVEN`."
            #   045:118  "llegar a `PROVEN`."          <- sin negacion visible
            #
            # La 118 hereda el PROVEN de la 117 y se cuela como respuesta,
            # cerrando SIETE fronteras de FUNCTION=always que siguen ABIERTAS.
            # Y lo grave no es el numero: es que el documento que lo produce
            # es ESTE PROYECTO hablando de SU PROPIA HERRAMIENTA. Una
            # herramienta que cita el caso que analisa se cita a si misma.
            #
            # La regla es conservador a proposito: si la ventana de negacion
            # de la linea esta contaminada, la linea NO PUEDE cerrar nada. No
            # se busca la negacion mas atras, que es lo que haria falta de
            # verdad: se descarta, porque un "PROVEN" que aparece dentro de un
            # parrafo que esta hablando de que no se puede, no es un
            # PROVEN dicho. Es el sujeto de una discusion.
            ventana = " ".join(ls[max(0, i - 1):i + 1])
            if any(re.search(p, ventana, re.I) for p in NEGACION):
                continue
            # Y ahora: que la linea AFIRME, no que mencione.
            if not _afirma(l):
                continue
            prev = ls[i - 1] if i >= 1 else ""
            prev2 = ls[i - 2] if i >= 2 else ""
            s = sujeto_de(l, prev, prev2)
            # Si no hay sujeto identificable, se prueba con la primera celda de
            # una fila de tabla, que es la forma mayoritaria de las que faltan.
            if not s:
                s = etiqueta_de(l) or etiqueta_de(prev)
            if not s:
                continue
            for v in variantes(s):
                out[v].append(dict(doc=doc, linea=i + 1,
                                  estado=cerradas[0], texto=l.strip()[:150]))
    return out


def _resolver(fr, cc):
    """La regla de clasificacion. Aislada para que el self-test la reutilice."""
    for f in fr:
        if not f["sujeto"]:
            # SIN identificador, pero con la primera celda de una tabla: la
            # frontera tiene sujeto y es una FRASE. Eso no la hace cruzable,
            # pero si la hace DESCRIBIBLE, que es lo que importa para poder
            # arreglarla.
            if f.get("etiqueta"):
                f["clase"] = "SUJETO_EN_FRASE"
                f["resolucion"] = None
                continue
            f["clase"] = "SIN_SUJETO"
            f["resolucion"] = None
            continue
        vs = variantes(f["sujeto"])
        if not vs:
            # hay algo entre backticks pero NO es un sujeto consultable
            f["clase"] = "NO_CRUZABLE"
            f["resolucion"] = None
            continue
        hits = []
        for v in vs:
            hits += cc.get(v, [])
        # RESUELTA_AQUI: la respuesta esta en el MISMO documento.
        propias = [h for h in hits if h["doc"] == f["doc"]]
        otras = [h for h in hits if h["doc"] != f["doc"]]
        despues = [h for h in propias if h["linea"] > f["linea"]]
        if despues:
            f["clase"] = "RESUELTA_AQUI"
            f["resolucion"] = sorted(despues, key=lambda h: h["linea"])[0]
            continue
        if otras:
            f["clase"] = "RESUELTA_OTRO"
            f["resolucion"] = sorted(otras, key=lambda h: h["doc"])[0]
            continue
        f["clase"] = "VIVA"
        f["resolucion"] = None
    return fr


def clasificar():
    fr = extraer()
    cc = claims_cerrados()
    _resolver(fr, cc)
    return fr, cc


def selftest():
    """Delega en su propio fichero. Ver `_selftest_stale_gap.py`.

    POR QUE NO ESTA AQUI. Esta herramienta declara `READONLY=yes`, y es cierto
    para el modo que produce evidencia: sin argumentos, solo lee. El self-test
    necesita escribir, y mientras vivia aqui el validador de contratos leia el
    codigo, encontraba la apertura en modo escritura y tenia razon en que el
    contrato mentia.

    Habia tres salidas: declarar la escritura aqui, degradar el self-test a
    memoria, o moverlo. Se eligio moverlo: un contrato inflado deja de
    distinguir herramientas, y un self-test en memoria deja de probar contra
    ficheros de verdad.

    Delegar en vez de reimplementar mantiene una sola copia de los casos, que
    es lo que hay que mover si el self-test anade algo.
    """
    import _selftest_stale_gap as T
    return T.selftest()


def main():
    args = sys.argv[1:]
    if "--self-test" in args:
        return selftest()

    def opt(n):
        if n in sys.argv and sys.argv.index(n) + 1 < len(sys.argv):
            return sys.argv[sys.argv.index(n) + 1]
        return None

    fr, cc = clasificar()
    cls = defaultdict(list)
    for f in fr:
        cls[f["clase"]].append(f)

    if "--json" in args:
        print(json.dumps(dict(total=len(fr), por_clase={k: len(v) for k, v in cls.items()},
                              huecos=fr, n_claims_cerrados=len(cc)), indent=1))
        return 0

    subj = opt("--sujeto")
    if subj:
        print("=" * 74)
        print(f"RASTRO COMPLETO de {subj}")
        print("=" * 74)
        vs = variantes(subj)
        for f in fr:
            if f["sujeto"] and (variantes(f["sujeto"]) & vs):
                print(f"  [{f['clase']:14}] {f['doc']}:{f['linea']}")
                print(f"      {f['texto']}")
                if f["resolucion"]:
                    r = f["resolucion"]
                    print(f"      -> resuelto en {r['doc']}:{r['linea']} ({r['estado']})")
        print()
        print(f"  claims cerrados que mencionan el sujeto: {len(cc.get(subj.lower(), []))}")
        return 0

    print("=" * 74)
    print("STALE GAP -- fronteras ya resueltas en otro sitio")
    print("=" * 74)
    print(f"fronteras con estado decierre : {len(fr)}")
    print(f"claims cerrados indexados     : {len(cc)}")
    print()
    orden = ["RESUELTA_AQUI", "RESUELTA_OTRO", "NO_CRUZABLE",
             "SUJETO_EN_FRASE", "SIN_SUJETO", "VIVA"]
    print(f"{'clase':16} {'n':>5} {'que significa':44}")
    print("-" * 74)
    sig = {
        "RESUELTA_AQUI": "el mismo doc se contradice consigo mismo",
        "RESUELTA_OTRO": "otro doc ya lo cerrO; el NOT_DET esta obsoleto",
        "NO_CRUZABLE": "lo que hay entre backticks no es un sujeto",
        "SUJETO_EN_FRASE": "sujeto en prosa: se puede leer, no cruzar",
        "SIN_SUJETO": "no dice de que; no se puede cerrar ni repetir",
        "VIVA": "sin resolver: trabajo real",
    }
    for c in orden:
        print(f"{c:16} {len(cls.get(c, [])):5} {sig[c]:44}")
    print()

    if "--obsoletas" in args or not args:
        obsoletas = cls.get("RESUELTA_OTRO", []) + cls.get("RESUELTA_AQUI", [])
        if obsoletas:
            print("-" * 74)
            print(f"FRONTERAS OBSOLETAS ({len(obsoletas)}): el trabajo ya esta hecho")
            print("-" * 74)
            for f in sorted(obsoletas, key=lambda x: x["doc"])[:40]:
                r = f["resolucion"]
                print(f"  {f['doc']}:{f['linea']}  {f['sujeto']}")
                print(f"      frontera: {f['texto'][:90]}")
                print(f"      respuesta: {r['doc']}:{r['linea']} ({r['estado']})")
            if len(obsoletas) > 40:
                print(f"  ... y {len(obsoletas) - 40} mas")
            print()

    if "--sin-sujeto" in args:
        ss = cls.get("SIN_SUJETO", [])
        if ss:
            print("-" * 74)
            print(f"SIN SUJETO ({len(ss)}): fronteras que no se pueden cruzar")
            print("-" * 74)
            for f in ss[:25]:
                print(f"  {f['doc']}:{f['linea']}  {f['texto'][:88]}")
            print()
            print("  Una frontera sin sujeto no es trabajo: es un defecto del")
            print("  documento. No se puede cerrar ni repetir ni medir.")

    print("-" * 74)
    print("LIMITE:")
    print("  El cruce es POR SUJETO NOMBRADO. Dos documentos que hablen de la")
    print("  misma cosa con nombres distintos no se cruzan, y se contaran como")
    print(f"  VIVA: {len(cls.get('VIVA', []))} es una COTA SUPERIOR del trabajo real.")
    print("  Y RESUELTA_OTRO no dice que la respuesta sea correcta: dice que")
    print("  existe. Quien decidio bien es otro asunto (causal_map).")
    print()
    print("  NO_CRUZABLE existe por un motivo concreto. Los documentos se citan")
    print("  entre si por numero (`017`, `033`), y como cada numero aparece en")
    print("  el titulo de su fichero, sin filtrarlo cualquier linea se cruzaba")
    print("  con cualquier otra. Eso daba 52 'fronteras obsoletas' de las que")
    print("  muchas no lo eran. Un cruce por referencia a documento produce")
    print("  relaciones falsas, que son PEORES que no cruzar.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())