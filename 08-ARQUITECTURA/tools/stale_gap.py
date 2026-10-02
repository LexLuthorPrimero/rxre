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