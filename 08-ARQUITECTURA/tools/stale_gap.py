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
def _es_referencia(s):
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
    return None


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
            out.append(dict(doc=doc, linea=i + 1, sujeto=s,
                            estado=est[0], todos=est,
                            texto=l.strip()[:150]))
    return out


def claims_cerrados():
    """{clave: [(doc, linea, estado, texto)]} de lo que ya esta resuelto."""
    out = defaultdict(list)
    for path in documentos():
        ls = lineas_de(path)
        doc = os.path.basename(path)
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
            # Y ahora: que la linea AFIRME, no que mencione.
            if not _afirma(l):
                continue
            prev = ls[i - 1] if i >= 1 else ""
            prev2 = ls[i - 2] if i >= 2 else ""
            s = sujeto_de(l, prev, prev2)
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
    print("=" * 74)
    print("SELF-TEST de stale_gap: control negativo")
    print("=" * 74)
    fallos = 0
    # ESTA ES LA UNICA ESCRITURA DE LA HERRAMIENTA, y vive aqui.
    #
    # El contrato dice WRITES_FILES=no porque el modo normal -- el que la
    # usa run_all y el que consume la evidencia -- solo lee. El self-test
    # necesita ficheros, y la forma correcta de decirlo es en el sitio donde
    # ocurre, no en una linea del docstring que nadie comprueba.
    #
    # Los ficheros van a un directorio propio de /tmp, se BORRAN antes de
    # empezar, y se nombran t1..t10 para que no puedan confundirse con nada
    # del proyecto. Nada del corpus se toca, y el contrato sigue siendo
    # cierto para toda la ejecucion que produce evidencia.
    tmp = "/tmp/opencode/stale_gap_selftest"
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))

    def doc(nombre, texto):
        p = os.path.join(tmp, nombre)
        with open(p, "w") as fh:
            fh.write(texto)
        return p

    # CADA CASO EN UN FICHERO DISTINTO.
    #
    # La primera version de este self-test escribia cinco casos todos en
    # "a.md". Cada llamada a doc() sobreescribia la anterior, asi que solo
    # sobrevivia el ultimo caso, y cuatro controles de siete daban FALLA.
    #
    # Un control que dice "FALLA" porque el test esta mal escrito entrena a
    # ignorar el self-test entero. Por eso los ficheros son distintos y no un
    # bucle: la repeticion es lo que Rompio esto, no el caso.
    # 1. frontera viva: nadie responde. Debe salir VIVA.
    doc("t1-viva.md", "El registro `mmX_VIVO`:\n`NOT_DETERMINED` todavia.\n")
    # 2. frontera obsoleta: otro doc responde PROVEN. Debe salir RESUELTA_OTRO.
    doc("t2-obsoleta.md", "El registro `mmX_OTRO`:\n`NOT_DETERMINED` por medir.\n")
    doc("t2-respuesta.md", "Se midio `mmX_OTRO`: `PROVEN` vale 42.\n")
    # 3. contradiccion consigo mismo: el mismo doc dice las dos.
    doc("t3-propia.md", "Sobre `mmX_AQUI`:\n`NOT_DETERMINED` al principio.\n"
                        "Tres lineas mas tarde queda `PROVEN` resuelto.\n")
    # 4. sin sujeto: la linea dice el estado y nada mas.
    doc("t4-sinsujeto.md", "No se sabe todavia.\n`NOT_DETERMINED`.\n")
    # 5. respuesta ANTIGUA a una frontera posterior: es actualizacion
    #    legitima, no contradiccion consigo mismo. Debe salir VIVA.
    doc("t5-antes.md", "`mmX_ANTES` ya era `PROVEN` medido.\n"
                       "Despues: `mmX_ANTES` `NOT_DETERMINED` de nuevo.\n")

    fr, _cc = _clasificar_en(tmp)
    por = defaultdict(list)
    for f in fr:
        por[f["sujeto"]].append(f["clase"])

    casos = [
        ("mmX_VIVO", "VIVA"),
        ("mmX_OTRO", "RESUELTA_OTRO"),
        ("mmX_AQUI", "RESUELTA_AQUI"),
        ("mmX_ANTES", "VIVA"),
        (None, "SIN_SUJETO"),
    ]
    for sujeto, esperado in casos:
        obt = por.get(sujeto, [])
        ok = esperado in obt
        print(f"  {str(sujeto):12} esperado {esperado:14} obtenido "
              f"{obt if obt else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
        fallos += 0 if ok else 1

    # 6. el cruce debe aceptar las dos formas del nombre del registro.
    #    Este es el fallo que mas importa: si no acepta `mmX` y `X` como el
    #    mismo sujeto, todos los registros dejan de cruzarse.
    doc("t6-forma.md", "`CP_FORMA`:\n`NOT_DETERMINED`\n")
    doc("t6-respuesta.md", "`mmCP_FORMA`: `PROVEN` confirmado.\n")
    fr2, _ = _clasificar_en(tmp)
    r = [f["clase"] for f in fr2 if f["sujeto"] == "CP_FORMA"]
    ok = "RESUELTA_OTRO" in r
    print(f"  {'prefijo mm/':12} mmCP_FORMA == CP_FORMA"
          f"          {r if r else '(nada)'}  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 7. determinismo
    #
    # LAS DOS EXTRACCIONES TIENEN QUE HACERSE DESPUES DE CREAR TODOS LOS
    # FICHEROS. La primera version comparaba `fr` (calculada antes de crear
    # los ficheros del caso 6) contra una nueva, y salia distinta: no era
    # falta de determinismo sino que entre medias se habian anadido dos
    # ficheros mas. Un control de determinismo tiene que medir lo que dice,
    # que es que dos EJECUCIONES sobre el MISMO estado dan lo mismo.
    f1, _ = _clasificar_en(tmp)
    f2, _ = _clasificar_en(tmp)
    a = json.dumps(f1, sort_keys=True, default=str)
    b2 = json.dumps(f2, sort_keys=True, default=str)
    ok = a == b2
    print(f"  {'determinismo':12} dos extracciones identicas    "
          f"{'IDEMPOTENTE' if ok else 'NO DETERMINISTA <<<'}")
    fallos += 0 if ok else 1

    # 8. directorio inexistente: no debe reventar
    try:
        _clasificar_en("/tmp/opencode/no_existe_stale_gap_xyz")
        ok = True
        detalle = "vacio"
    except Exception as e:
        ok = False
        detalle = f"revento: {e}"
    print(f"  {'dir ausente':12} debe devolver lista vacia    {detalle}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 9. NO_CRUZABLE: un numero de documento NO es un sujeto.
    #
    #    Es el control que mas trabajo evita. Los documentos se citan entre si
    #    por numero, y cada numero esta en el titulo de su fichero. Sin
    #    filtrarlo, `017` cruzaba con TODOS los documentos que citaran un
    #    numero, y salian 52 fronteras obsoletas de las que muchas no lo eran.
    #    Un cruce por referencia produce relaciones falsas.
    doc("t9-ref.md", "Tal como dice `017`:\n`NOT_DETERMINED` aun.\n")
    doc("t9-resp.md", "`017` es un documento.\n`NOT_DETERMINED` aqui tambien.\n")
    doc("t9-resp2.md", "Otra vez `017`.\n`NOT_DETERMINED` por aqui.\n")
    fr9, _ = _clasificar_en(tmp)
    r9 = [f["clase"] for f in fr9 if f["sujeto"] == "017"]
    ok = r9 and all(c == "NO_CRUZABLE" for c in r9)
    print(f"  {'numero de doc':12} `017` debe ser NO_CRUZABLE   {r9 if r9 else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 9b. y un sujeto real NO debe caer en la trampa del filtro
    doc("t9b-real.md", "`mmREAL_SUBJ`:\n`NOT_DETERMINED`\n")
    fr9b, _ = _clasificar_en(tmp)
    r9b = [f["clase"] for f in fr9b if f["sujeto"] == "mmREAL_SUBJ"]
    ok = r9b == ["VIVA"]
    print(f"  {'sujeto real':12} no debe filtrarse             {r9b if r9b else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10. LA NEGACION. El control mas importante de los diez.
    #
    #     Reproduce el caso REAL del corpus, 056:153:
    #
    #       "Para pasar de `NOT_DETERMINED` a `PROVEN` harían falta tres
    #        cosas, y ninguna existe"
    #
    #     La linea contiene PROVEN. Sin filtro de negacion, la herramienta da
    #     por CERRADA una frontera que esta ABIERTA, y ademas lo hace
    #     financiando la mentira: el texto dice que no se puede llegar.
    doc("t10-neg.md", "`mmX_NEGADO`:\n`NOT_DETERMINED` sin resolver.\n")
    doc("t10-resp.md", "Para pasar de `NOT_DETERMINED` a `PROVEN` "
                       "harían falta tres cosas, y ninguna existe.\n")
    fr10, _ = _clasificar_en(tmp)
    r10 = [f["clase"] for f in fr10 if f["sujeto"] == "mmX_NEGADO"]
    ok = r10 == ["VIVA"]
    print(f"  {'negacion':12} PROVEN en frase negativa    {r10 if r10 else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10b. y un PROVEN de verdad NO debe descartarse por prudencia
    doc("t10b-ok.md", "`mmX_DE_VERDAD`:\n`NOT_DETERMINED` al inicio.\n")
    doc("t10b-resp.md", "Ya esta resuelto: `mmX_DE_VERDAD` es `PROVEN`.\n")
    fr10b, _ = _clasificar_en(tmp)
    r10b = [f["clase"] for f in fr10b if f["sujeto"] == "mmX_DE_VERDAD"]
    ok = r10b == ["RESUELTA_OTRO"]
    print(f"  {'PROVEN real':12} no debe descartarse        {r10b if r10b else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10c. la AFIRMACION frente a la MENCION.
    #
    #     Cuarto fallo real, encontrado al verificar a mano las 30 obsoletas
    #     que quedaron tras los filtros de negacion y de numero de documento.
    #     Caso del corpus, 017:194:
    #
    #       "...haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION`
    #        tuviera otro valor que 0 en..."
    #
    #     La linea tiene REFUTED y NO afirma nada: dice que sería incorrecto.
    #     Con ella de "respuesta", dos fronteras de 018 salian RESUELTA_OTRO.
    doc("t10c-mencion.md", "`mmX_MENCION`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10c-resp.md", "Haria `REFUTED` incorrecto; (c) `mmX_MENCION` "
                        "tuviera otro valor que 0 en la mascara.\n")
    fr10c, _ = _clasificar_en(tmp)
    r10c = [f["clase"] for f in fr10c if f["sujeto"] == "mmX_MENCION"]
    ok = r10c == ["VIVA"]
    print(f"  {'mencion':12} REFUTED condicional no afirma  {r10c if r10c else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    # 10d. y un REFUTED de verdad, en tabla, SI debe contar
    doc("t10d-ref.md", "`mmX_REFUTADO`:\n`NOT_DETERMINED` abierto.\n")
    doc("t10d-resp.md", "| Que el fence necesite `mmX_REFUTADO` | `REFUTED` "
                        "— es un buzon |")
    fr10d, _ = _clasificar_en(tmp)
    r10d = [f["clase"] for f in fr10d if f["sujeto"] == "mmX_REFUTADO"]
    ok = r10d == ["RESUELTA_OTRO"]
    print(f"  {'REFUTED real':12} en tabla si afirma         {r10d if r10d else '(nada)'}"
          f"  {'OK' if ok else 'FALLA <<<'}")
    fallos += 0 if ok else 1

    print()
    if fallos:
        print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan")
        return 1
    print(f"  RESULTADO: TOOL_VALIDATED -- {len(casos) + 7} controles pasan.")
    print("  Los cuatro que mas evitan relaciones falsas:")
    print("    - PROVEN dentro de una frase NEGATIVA no cuenta como respuesta.")
    print("      El caso real (056:153) daba por cerradas dos fronteras")
    print("      ABIERTAS de FUNCTION=always, y el texto decia lo contrario.")
    print("    - un estado CONDCIONAL ('haría REFUTED incorrecto') no afirma.")
    print("      El caso real (017:194) cerraba dos fronteras de 018.")
    print("    - un numero de documento no es un sujeto consultable.")
    print("    - una actualizacion posterior no es una contradiccion consigo")
    print("      mismo.")
    print("  Y en las tres primeras se exige lo simetrico: un PROVEN o un")
    print("  REFUTED de verdad NO se descartan por prudencia.")
    return 0


def _clasificar_en(directorio):
    """La misma clasificacion, sobre otro directorio. Para el self-test."""
    global FIND
    old = FIND
    FIND = directorio
    try:
        fr = extraer()
        cc = claims_cerrados()
        _resolver(fr, cc)
        return fr, cc
    finally:
        FIND = old


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
             "SIN_SUJETO", "VIVA"]
    print(f"{'clase':16} {'n':>5} {'que significa':44}")
    print("-" * 74)
    sig = {
        "RESUELTA_AQUI": "el mismo doc se contradice consigo mismo",
        "RESUELTA_OTRO": "otro doc ya lo cerrO; el NOT_DET esta obsoleto",
        "NO_CRUZABLE": "lo que hay entre backticks no es un sujeto",
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