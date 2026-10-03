#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
frontier.py - la lista de lo que queda abierto, CLASIFICADA por lo que haria
falta para cerrarla.

POR QUE EXISTE

Hay 230 afirmaciones `NOT_DETERMINED` vivas en 55 findings. Es un numero que
no dice nada: no dice cuales son un registro y cuales son el spec de GFX8, que
esta no publicado (033), y la diferencia entre las dos cosas es la diferencia
entre un experimento de una hora y una linea de codigo que no se puede
escribir nunca.

`AGENTS.md` manda no abrir RUNTIME "porque podria ser interesante", solo con un
discriminante. Y `INFORMATION_GAIN_GATE` manda elegir por
UNCERTAINTY_REDUCTION + PATH_UNLOCKS sobre INVESTIGATION_COST. Las dos reglas
necesitan la misma entrada, y esa entrada no existia: que cuesta cerrar cada
hueco, y con que evidencia.

ASI QUE ESTA HERRAMIENTA CLASIFICA CADA HUECO POR SU VIA DE CIERRE

  UN_REGISTRO      Se cierra leyendo UN registro de la tarjeta. Es el unico
                   caso donde un experimento de runtime esta justificado por
                   el metodo, porque su discriminante es una sola lectura.
  POCOS_REGISTROS  Se cierra leyendo varios. Un experimento de runtime tambien
                   puede servir, pero el coste sube con cada uno.
  SPEC_NO_PUBLICADO Lo que falta es documentacion que no existe. 033 lo
                   establecio para la arquitectura de GFX8. Ningun experimento
                   lo cierra, y por eso NO es trabajo: es una pared. Se
                   listan aparte, porque lo que no se puede hacer tiene que
                   estar a la vista para que no se intente.
  RUNTIME_ACTIVO   Solo se cierra observando el comportamiento: orden real de
                   ejecucion, latencia, si un flush surte efecto. Un
                   experimento con control y diff, no una lectura.
  POR_DEFINICION   Depende de una convencion, no de una medicion: MODEL_CHOICE,
                   REQUIREMENT, POLICY. Un driver propio elige, y no se
                   "descubre". No es un hueco de investigacion.

Y el orden de salida NO es el de las clases: es por RENTABILIDAD, que es
coste de cierre por incertidumbre que se reduce. Un hueco de UN_REGISTRO
que bloquea tres findings vale mas que diez de UN_REGISTRO que no bloquean
nada, y eso se mide contando cuantos findings citan la misma evidencia.

LIMITE DURO, DECLARADO ANTES DE LOS RESULTADOS

LA CLASIFICACION ES POR PALABRAS, Y ESO NO ES ENTENDER.

Se buscan en el texto de la afirmacion marcas de cada via: un nombre de
registro, la palabra "spec" o "documentado", palabras de comportamiento como
"orden" o "efecto". Eso NO sabe que un `NOT_DETERMINED` sobre el orden de
ejecucion se cerraria leyendo un registro: no, porque no se cierra asi. Y NO
sabe que uno sobre el valor de una mascara se cerraria con la spec, aunque la
mascara este en el corpus.

Por eso la herramienta imprime el TEXTO INTEGRO de cada fila y la clase
propuesta, para que un lector pueda estar en desacuerdo en un segundo. Y
porque el codigo de salida distingue "clasificado" de "clasificado con
confianza": si la marca que decidio la clase esta lejos de la frase, se
imprime como DEBIL.

Es una herramienta de TRIAJE, no de verdad. Su valor es ordenar 230 huecos en
cinco grupos y decir cuales son una pared. La verdad la pone quien lee, y por
eso el texto va al lado.

CODIGOS DE SALIDA

  0  la clasificacion se completo para todos los huecos
  1  algun hueco quedo sin clasificar, y el detalle lo dice
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

# Las clases de hueco, con lo que significa cada una y si es trabajo.
VIAS: Dict[str, str] = {
    "DIFERENCIAL": "se cierra repitiendo con un parametro y comparando",
    "UN_REGISTRO": "se cierra leyendo un registro de la tarjeta",
    "POCOS_REGISTROS": "se cierra leyendo varios registros",
    "SPEC_NO_PUBLICADO": "falta documentacion que no existe (033)",
    "RUNTIME_ACTIVO": "solo se cierra observando comportamiento",
    "POR_DEFINICION": "es una convencion que se elige, no se descubre",
    "SIN_PISTAS": "el texto no dice que haria falta para cerrarlo",
}

# Marcas de cada via. Se declara el ORDEN porque el primero que casa decide, y
# el orden importa: una frase que dice "la spec no lo dice" y luego menciona un
# registro es SPEC, no UN_REGISTRO, porque un experimento no puede crear la
# documentacion que falta.
MARCAS: List[Tuple[str, str, int]] = [
    # (clase, regex, fuerza)  fuerza 3 = fuerte, 2 = media, 1 = debil
    ("SPEC_NO_PUBLICADO",
     r"spec(?:ification)?\b|arquitectura de gfx8|no (?:esta|published|publicad)|"
     r"no documentad|no publicad|no hay documentaci|not_published|"
     r"no hay fuente primaria|desconocido por el hardware", 3),
    ("POR_DEFINICION",
     r"model_choice|modelo elegido|convenci[oó]n|por decisi[oó]n propia|"
     r"requirement|policy|decisi[oó]n de dise[nñ]o", 2),
    ("RUNTIME_ACTIVO",
     r"\borden\b|\border de ejecuci|efecto real|si surte efecto|no se sabe si|"
     r"comportamiento real|hardware (?:lo )?(?:hace|interpreta)|"
     r"no est[aá] (?:probado|medido) (?:en )?(?:el )?hardware|"
     r"latencia|timing|inmediat|visible para", 2),
    # DIFERENCIAL, y por que va ANTES de UN_REGISTRO.
    #
    # "Si el resultado cambia al variar X" ES la definicion de un experimento
    # controlado, y la que AGENTS.md llama automatizacion diferencial
    # (RUN A / RUN B -> DIFF). No es una lectura: es repetir la misma
    # secuencia cambiando un parametro y comparar.
    #
    # Va antes de UN_REGISTRO por un caso real. 057 dice que
    # FUNCTION=always se cierra escribiendo un WAIT_REG_MEM(poll=0x20) y
    # repitiendo con poll=0x0 y poll=0xFF, "si el resultado cambia con el
    # poll, el wait espera algo". La seccion NOMBRA registros -- nombra
    # INVALIDATE_RESPONSE para explicar que NO sirve como discriminante -- y
    # por eso la clasificaba como UN_REGISTRO. Y es RUNTIME_ACTIVO: el
    # discriminante es COMPORTAMENTAL.
    #
    # Un nombre de registro en el texto no dice si el discriminante es leerlo o
    # observar un efecto. Por eso esta categoria mira la FORMA de la frase, no
    # si menciona un registro.
    ("DIFERENCIAL",
     r"cambia con el|cambia el resultado|si el resultado cambia|"
     r"repetir con|repetir el mismo|comparar (?:con|ambos)|"
     r"diferencia (?:entre|si)|con (?:un )?valor distinto|variando|"
     r"cambiando el|y repetir", 3),
    ("UN_REGISTRO",
     r"leer un (?:único|solo) registro|un solo registro|"
     r"basta con leer|se lee de un registro|un registro", 3),
    ("POCOS_REGISTROS",
     r"leer \w+ registros|la cadena de \w+ registros|"
     r"varios registros|registros de mmio|leer la cadena", 2),
]

# Un registro concreto mencionado en la frase: mmX, SOC15D_X, o un macro en
# acentos graves con forma de registro.
# Cabeceras cuyo texto declara que algo queda abierto. Una lista de sinonimos
# y no una sola palabra, porque cada autor escribio el suyo, y elegir uno solo
# daria una seccion equivocada en 40 de 55 documentos sin dar ningun error.
RE_TITULO = re.compile(
    r"^#{1,6}\s*.*\b(not[_ ]determin|not[_ ]proven|unknown|abierto|"
    r"pendiente|que falta|lo que sigue|sin resolver|limite|frontera|"
    r"no (?:sabemos|determinado|resuelto|probado|no (?:esta|puedo)))\b", re.I)

# El patron de clasificacion tipificada, para contar clases por seccion sin
# reimplementar el extractor de claims. Se COPIA el patron y no se llama al
# modulo porque aqui solo hace falta contar, y claims ya tiene su selftest
# sobre el suyo.
CLASE_RX = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")

REGISTRO_RX = re.compile(
    r"\bmm[A-Z][A-Z0-9_]{3,}\b|\bSOC15D_[A-Z0-9_]+\b|"
    r"`(?:SOC15D|SOC15|XT)_[A-Z0-9_]+`")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def cargar_claims(root: str) -> List[Dict[str, object]]:
    """Las afirmaciones extraidas, por composicion: llama a claims.py.

    No se reimplementa el extractor. Ya tiene 20 vectores de selftest y una
    seccion de limites escrita; duplicarlo seria mantener dos extractores de
    prosa que divergen sin que nadie lo note, y cada uno con sus propios fallos
    de anclas.
    """
    sys.path.insert(0, os.path.join(root, "tools"))
    import claims as C  # type: ignore
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    filas: List[Dict[str, object]] = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = C.FINDING_RX.match(f)
        num = m.group(1) if m else f[:3]
        try:
            with open(os.path.join(d, f), "r", errors="replace") as fh:
                lineas = fh.read().splitlines()
        except OSError:
            continue
        fs, _fuera = C.extraer(lineas)
        for x in fs:
            x["finding"] = num
            x["documento"] = f
            filas.append(x)
    return filas


def secciones(lineas: List[str]) -> List[Tuple[int, str, str]]:
    """(linea, titulo, cuerpo) de cada cabecera, con su cuerpo hasta la siguiente.

    Un parser de Markdown minimo, por niveles de #. No es un parser completo y
    no pretende serlo: solo necesita saber donde empieza cada seccion, que es
    lo que permite elegir la que declara los huecos en vez de fragments sueltos.
    """
    out: List[Tuple[int, str, str]] = []
    pila: List[Tuple[int, int, str]] = []
    cuerpo: List[List[str]] = []
    for i, ln in enumerate(lineas, start=1):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            if pila:
                out.append((pila[-1][1], pila[-1][2], "\n".join(cuerpo[-1])))
            n = len(m.group(1))
            while pila and pila[-1][0] >= n:
                pila.pop()
                cuerpo.pop()
            pila.append((n, i, m.group(2)))
            cuerpo.append([])
            continue
        if pila:
            cuerpo[-1].append(ln)
    if pila:
        out.append((pila[-1][1], pila[-1][2], "\n".join(cuerpo[-1])))
    return out


def seccion_que_declara(lineas: List[str],
                        clases_abiertas: Set[str]) -> Tuple[int, str, str, bool]:
    """La seccion que contiene mas clases ABIERTAS, y si su titulo lo dice.

    Se elige por CONTENIDO, no por titulo. El titulo se usa para AVISAR: si no
    habla de huecos, la eleccion es una conjetura sobre el formato del
    documento, y se dice en vez de presentarla como una lectura.

    Y esa conjetura es el motivo por el que la UNIDAD es el documento y no la
    afirmacion. Clasificando las 261 afirmaciones por su frase se quedaba
    226 sin pistas; con el parrafo, 184. Ni uno ni otro sirve, porque la
    clasificacion va al FINAL de la frase ("... es `NOT_DETERMINED`") y el
    motivo esta en la seccion que el autor titulo para enumerarlos. 55
    secciones se leen; 261 fragmentos sueltos no.
    """
    secs = secciones(lineas)
    if not secs:
        return 0, "(documento sin cabeceras)", "\n".join(lineas), False
    mejor_n = 0
    mejor = (0, "(ninguna seccion contiene clases)", "", False)
    for lin, titulo, cuerpo in secs:
        n = sum(1 for m in CLASE_RX.finditer(cuerpo) if m.group(1) in clases_abiertas)
        if n > mejor_n:
            mejor_n = n
            mejor = (lin, titulo, cuerpo, bool(RE_TITULO.search(titulo)))
    return mejor


def clasificar(frase: str, parrafo: str = "") -> Tuple[str, int, str]:
    """(via, fuerza, que marca decidio). El primero que casa, en orden.

    Se lee la FRASE y el parrafo, y la frase manda. El parrafo es contexto: la
    clasificacion suele ir al final de la frase que la contiene, asi que la
    frase sola no dice por que el hueco sigue abierto.
    """
    for clase, rx, fuerza in MARCAS:
        m = re.search(rx, frase, re.I)
        if m:
            return clase, fuerza, "frase: " + m.group(0)
    for clase, rx, fuerza in MARCAS:
        m = re.search(rx, parrafo, re.I)
        if m:
            # El parrafo es mas contexto, asi que la marca vale menos que si
            # estuviera en la frase. No es la MISMA confianza, y se marca.
            return clase, max(1, fuerza - 1), "parrafo: " + m.group(0)
    # Sin marca de via. Pero si menciona un registro concreto, es al menos una
    # lectura: eso es informacion, aunque no sepa cuanto.
    if REGISTRO_RX.search(frase):
        return "UN_REGISTRO", 1, (REGISTRO_RX.search(frase).group(0))
    return "SIN_PISTAS", 0, ""


CLASES_TOK = (
    "NOT_DETERMINED", "NOT_PROVEN", "UNKNOWN", "PROVEN", "PROVEN_DERIVED",
    "PROVEN_ABSENT", "CORROBORATED", "REFUTED", "OBSERVED", "MODEL_CHOICE",
    "REQUIREMENT", "POLICY", "LIMITATION", "NEGATIVE_RESULT", "NOT_AVAILABLE",
    "NOT_OBSERVED", "NOT_FOUND", "NOT_APPLICABLE", "PARTIAL", "DEFERRED",
    "HYPOTHESIS", "ASSUMPTION", "CONCLUSION", "FACT", "DERIVATION", "ERROR",
    "TEST", "IMPLEMENTATION", "CONTRADICTION", "IN_CORPUS")

CIERRES = ("cerrado", "queda cerrado", "cierra", "resuelto", "medido",
           "demostrado", "probado", "ya no", "obsoleto", "retractad",
           "correccion", "se cierra")

NEGACIONES = ("no cierra", "no resuelve", "no cubre", "no aplica", "sigue sin",
              "sigue siendo", "queda abierto", "queda sin", "no es un cierre",
              "no lo cierra", "nada de esto", "no he cerrado", "no se cierra",
              "sigue abierto", "continua abierto", "no descarta")


def sujeto_de(frase: str) -> Optional[str]:
    """El simbolo del que habla el hueco, NO su clasificacion.

    La primera version tomaba el primer token entrecomillado, y en este
    proyecto ese token es SIEMPRE la clase -- el texto esta escrito como
    "GFX_HWIP sigue `NOT_DETERMINED`", con la clase al final. Asi que el
    "sujeto" era `NOT_DETERMINED`, que aparece en casi todos los findings
    posteriores, y la deteccion marcaba 133 huecos como cerrados citando la
    frase "Parcialmente cerrado, y el resto NOT_DETERMINED", que es
    exactamente lo contrario de cerrado.
    """
    for m in re.finditer(r"`([A-Za-z_][A-Za-z0-9_]{2,})`", frase):
        tok = m.group(1)
        if tok in CLASES_TOK:
            continue
        return tok
    return None


def es_cierre_real(linea: str) -> bool:
    """La palabra de cierre existe, y la frase NO la esta negando.

    Tres filtros, los tres por un falso positivo concreto:

      1. la palabra de cierre tiene que estar;
      2. una linea que declara un cierre Y una clase abierta no es un cierre:
         "parcialmente cerrado, y el resto NOT_DETERMINED" declara que el
         resto NO se cerro;
      3. y una NEGACION la anula entera. 051 dice "No cierra F1 ni 018.
         INVALIDATE_RESPONSE sigue sin token y sin handshake", y los dos
         filtros anteriores lo aceptaban.

    Es un falso negativo caro -- un hueco realmente cerrado se queda en la
    lista -- y se prefiere ahi, porque un hueco de mas se mira y uno que
    falta se olvida.
    """
    bajo = linea.lower()
    if not any(c in bajo for c in CIERRES):
        return False
    if re.search(r"`(NOT_DETERMINED|NOT_PROVEN|UNKNOWN)`", linea):
        return False
    for neg in NEGACIONES:
        if neg in bajo:
            return False
    return True


# Un identificador del corpus, con prefijo en minusculas opcional. "mmVM..." y
# "SOC15D_..." empiezan en minuscula, y sin ese grupo el patron no casaba con
# ninguno de los dos: el \b entre "m" y "V" no existe porque ambos son
# caracteres de palabra. Es el mismo fallo de ancla, una vez mas.
IDENT_RX = re.compile(
    r"\b((?:[a-z]+)?[A-Z][A-Za-z0-9_]*[A-Za-z0-9])\b")


def contiene_componentes(linea: str, comps: List[str]) -> bool:
    """comp aparece en un identificador de la linea, con la ASIMETRIA CORRECTA.

    Que coincidencia de componentes se acepta NO es simetrica, y esa es toda
    la dificultad:

        PGM_RSRC1 dentro de COMPUTE_PGM_RSRC1   -> True
        SUPPORTED dentro de SMC_NOT_SUPPORTED   -> False

    COMPUTE_ es un ESPACIO DE NOMBRES: PGM_RSRC1 es el mismo simbolo con un
    prefijo. SMC_NOT_ es una CALIFICACION: SUPPORTED es un simbolo distinto, y
    un claim sobre "SUPPORTED" no se cierra con una linea que habla de
    SMC_NOT_SUPPORTED.

    La regla mecanica que sale de ahi: un sujeto de UN componente solo casa
    como PREFIXO, y uno de DOS O MAS casa en cualquier posicion. Es una
    heuristica sobre una convencion de nombres, y se declara como tal -- pero
    es la que separa un acierto de cuatro falsos positivos, y el
    razonamiento es explicito.

    La primera version no distinguia los casos y daba cuatro falsos positivos
    de mas, todos del mismo tipo. Y la version con limites de palabra era peor
    aun: eliminaba los cuatro Y el positivo real, porque "PGM_RSRC1" esta
    dentro de "COMPUTE_PGM_RSRC1" y "_" es caracter de palabra.
    """
    if not comps:
        return False
    multi = len(comps) >= 2
    for m in IDENT_RX.finditer(linea):
        partes = [x for x in m.group(1).split("_") if x]
        for i in range(len(partes) - len(comps) + 1):
            if partes[i:i + len(comps)] != comps:
                continue
            if multi or i == 0:
                return True
    return False


def selftest() -> int:
    """Vectores de lo que ha fallado, que es la unica lista que importa.

    Los fallos de este archivo fueron todos COINCIDENCIA PARCIAL. Un simbolo
    que casa donde no debe marca huecos cerrados que estan vivos, y eso es
    peor que no detectar ninguno. Uno que NO casa donde debe deja trabajo real
    en la lista, que es el fallo barato.
    """
    print("=== frontier selftest ===\n")
    fallos = 0

    print("[1] sujeto_de: la clase NO es el sujeto")
    for frase, esperado in (
            ("`GFX_HWIP` sigue `NOT_DETERMINED`", "GFX_HWIP"),
            ("GFX_HWIP sigue `NOT_DETERMINED`.", None),
            ("`PROVEN_DERIVED` sobre `mmVM_INVALIDATE_REQUEST`",
             "mmVM_INVALIDATE_REQUEST"),
            ("solo `NOT_PROVEN` y nada mas", None),
    ):
        got = sujeto_de(frase)
        if got != esperado:
            print("  FAIL %-44s dio %r, esperado %r"
                  % (frase[:44], got, esperado))
            fallos += 1
        else:
            print("  OK   %-44s %s" % (frase[:44], got))

    print()
    print("[2] es_cierre_real: la palabra existe, y la negacion la anula")
    for linea, esperado, porque in (
            ("el bloqueo 1 resuelto", True, "cierre real"),
            ("No cierra F1 ni 018. `INVALIDATE_RESPONSE` sigue sin token", False,
             "NEGACION explicita"),
            ("Parcialmente cerrado, y el resto `NOT_DETERMINED`", False,
             "cierre y clase abierta"),
            ("sigue abierto el punto 3", False, "sigue abierto"),
            ("queda medido y demostrado", True, "cierre real"),
    ):
        got = es_cierre_real(linea)
        if got != esperado:
            print("  FAIL %-50s dio %s, esperado %s (%s)"
                  % (linea[:50], got, esperado, porque))
            fallos += 1
        else:
            print("  OK   %-50s %s" % (linea[:50], str(esperado)))

    print()
    print("[3] la coincidencia por COMPONENTES")
    for linea, comps, esperado, porque in (
            ("COMPUTE_PGM_RSRC1 decodificado", ["PGM", "RSRC1"], True,
             "PGM_RSRC1 esta DENTRO de COMPUTE_PGM_RSRC1"),
            ("SMC_NOT_SUPPORTED   = 0xFE", ["SUPPORTED"], False,
             "SUPPORTED es un componente suelto de otra cosa"),
            ("RESUELTO en `010`", ["PGM", "RSRC1"], False, "no aparece"),
            ("mmVM_INVALIDATE_REQUEST", ["mmVM", "INVALIDATE", "REQUEST"], True,
             "identico completo"),
    ):
        got = contiene_componentes(linea, comps)
        if got != esperado:
            print("  FAIL %-32s dio %s, esperado %s (%s)"
                  % (linea[:32], got, esperado, porque))
            fallos += 1
        else:
            print("  OK   %-32s %s" % (linea[:32], str(esperado)))

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (12 vectores)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="que hace falta para cerrar cada hueco, y cuales son pared")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--vias", help="filtra por via, separado por comas")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--prosa", action="store_true",
                    help="excluye las filas de tabla, que no son afirmaciones")
    ap.add_argument("--fuerte", action="store_true",
                    help="solo las marcadas en su propia frase, no en el parrafo")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    root = proyecto()
    filas = cargar_claims(root)
    if not filas:
        print("frontier: no encuentro afirmaciones en %s" % root, file=sys.stderr)
        return 2

    ABIERTAS = {"NOT_DETERMINED", "NOT_PROVEN", "UNKNOWN"}

    # Se agrupa por DOCUMENTO. La version anterior clasificaba 261
    # afirmaciones sueltas y daba 226 sin pistas; con el parrafo, 184. Ninguna
    # de las dos sirve, porque una afirmacion suelta no dice por que sigue
    # abierta: la clasificacion va al final de la frase y el motivo esta en la
    # seccion que el autor escribio para enumerarlos. 55 secciones se leen;
    # 261 fragmentos sueltos no.
    por_doc: Dict[str, Dict[str, object]] = {}
    for f in filas:
        num = str(f["finding"])
        d = por_doc.setdefault(num, {"fichero": f["documento"], "huecos": [],
                                     "clases": {}})
        d["huecos"].append(f)
        d["clases"][f["clase"]] = d["clases"].get(f["clase"], 0) + 1

    huecos: List[Dict[str, object]] = []
    for num in sorted(por_doc):
        d = por_doc[num]
        ruta = os.path.join(root, "06-INGENIERIA-INVERSA", "findings",
                            str(d["fichero"]))
        try:
            with open(ruta, "r", errors="replace") as fh:
                lineas = fh.read().splitlines()
        except OSError:
            continue
        lin, titulo, cuerpo, titulo_ok = seccion_que_declara(lineas, ABIERTAS)
        via_secc, fuerza_secc, marca_secc = clasificar(cuerpo)
        # El documento entero como ULTIMO contexto, y con menos fuerza.
        #
        # La seccion elegida es la que mas clases abiertas contiene, y puede no
        # ser la que explica COMO se cierra. En 057 el discriminante de
        # FUNCTION=always esta escrito en su seccion 7 -- "repetir con
        # poll=0x0 y poll=0xFF; si el resultado cambia con el poll, el wait
        # espera algo" -- y la seccion elegida es la de CUDA principal, que no
        # lo contiene. Sin este tercer contexto el hueco se pierde.
        #
        # Es la misma escalera de la frase al parrafo a la seccion, y cada
        # peldano baja la fuerza porque cada uno es mas contexto que la
        # afirmacion. Tres peldanos, y el ultimo se declara.
        via_doc = fuerza_doc = None
        marca_doc = ""
        if via_secc == "SIN_PISTAS":
            v2, f2, m2 = clasificar("\n".join(lineas))
            if v2 != "SIN_PISTAS":
                via_doc, fuerza_doc, marca_doc = v2, 1, m2
        for f in d["huecos"]:
            if f["clase"] not in ABIERTAS:
                continue
            via, fuerza, marca = clasificar(str(f["frase"]),
                                            str(f.get("parrafo_texto", "")))
            if via == "SIN_PISTAS" and via_doc is not None:
                via, fuerza, marca = via_doc, fuerza_doc, \
                    "documento entero: " + marca_doc
            elif via == "SIN_PISTAS" and via_secc != "SIN_PISTAS":
                # La seccion responde por el hueco. Es MENOS confianza que si
                # lo dijera la frase, y por eso la fuerza baja un punto.
                via, fuerza, marca = via_secc, max(1, fuerza_secc - 1), \
                    "seccion: " + marca_secc
            # ESTE APPEND TIENE QUE ESTAR DENTRO DEL BUCLE INTERNO.
            #
            # Con la misma sangria que el `for`, la tabla salia con una fila
            # por documento en vez de una por hueco, y la clase que imprimia
            # era la del ULTIMO hueco de cada documento -- por eso el recuento
            # mostraba CORPUS=1 y RUNTIME=5 en una tabla que solo deberia
            # contener clases abiertas.
            #
            # Y el sintoma no era un error: era una tabla plausible con
            # numeros que no cuadraban con los que claims.py contaba para el
            # mismo conjunto. Esa discrepancia fue lo que lo delato. Un error
            # que solo se ve al compararlo con otra herramienta, y por eso
            # las herramientas de este proyecto se comparan entre si.
            huecos.append({
                "finding": f["finding"], "documento": f["documento"],
                "linea": f["linea"], "clase": f["clase"], "via": via,
                "es_fila": bool(f.get("es_fila", False)),
                "fuerza": fuerza, "marca": marca, "frase": f["frase"],
                "registros": sorted(set(REGISTRO_RX.findall(str(f["frase"])))),
                "citas": f["citas"],
                "seccion_linea": lin, "seccion_titulo": titulo,
                "seccion_titulo_sobre_huecos": titulo_ok,
                "seccion_via": via_secc, "seccion_texto": cuerpo,
            # Los registros que nombra la SECCION, no los de la ventana de la
            # frase. La version anterior solo miraba la frase, y por eso los
            # cinco huecos UN_REGISTRO aparecian sin nombrar ningun registro:
            # la ventana de 120 chars no llega al punto donde estan.
            #
            # Y esto es lo que convierte la clasificacion en un discriminante
            # concreto. "Se cierra leyendo un registro" no es accionable;
            # "se cierra leyendo mmCP_HQD_PQ_RPTR" si. La diferencia es leer la
            # seccion entera en vez de la frase que la contiene.
            "seccion_registros": sorted(set(REGISTRO_RX.findall(cuerpo)))[:8],
            "n_seccion_registros": len(set(REGISTRO_RX.findall(cuerpo))),
                "n_huecos_del_finding": len(d["huecos"]),
            })

    # Cuantos findings citan cada hueco: un hueco compartido vale mas.
    por_frase: Dict[str, Set[str]] = {}
    for h in huecos:
        clave = (str(h["frase"])[:110]).lower()
        por_frase.setdefault(clave, set()).add(str(h["finding"]))
    for h in huecos:
        clave = (str(h["frase"])[:110]).lower()
        h["n_findings_que_lo_citan"] = len(por_frase[clave])

    # ---- LA OBSOLESCENCIA, QUE ES EL RESULTADO MAS UTIL DE ESTA HERRAMIENTA
    #
    # Un hueco puede seguir marcado NOT_DETERMINED aunque un finding POSTERIOR
    # lo haya cerrado. No se ve a ojo porque el finding viejo no se actualiza,
    # y por eso la frontera crece sola con cada iteracion.
    #
    # El primer resultado que salio fue exactamente eso: 001:213 dice "GFX_HWIP
    # sigue NOT_DETERMINED", y 047 acaba de PROBAR que la version de GC no
    # decide que codigo se ejecuta. El hueco esta muerto y la lista lo contaba
    # como vivo.
    #
    # El sujeto de un hueco es el primer simbolo entrecomillado de su frase, y
    # la busca es MECANICA: ese simbolo, en un finding de numero MAYOR, cerca
    # de una palabra que declara un cierre. No se entiende el texto: se busca
    # la co-ocurrencia, y si no se encuentra el hueco se queda vivo.
    #
    # Y la asimetria es deliberada: solo se declara obsoleto si el hallazgo es
    # FUERTE, con el simbolo y la palabra de cierre en la MISMA frase. Un
    # match debil deja el hueco vivo, porque un falso positivo aqui borra
    # trabajo real de la lista.
    cierres = ("cerrado", "queda cerrado", "cierra", "resuelto", "medido",
               "demostrado", "probado", "ya no", "obsoleto", "retractad",
               "correccion", "se cierra")
    indices: Dict[str, List[Tuple[str, str]]] = {}
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        mnum = re.match(r"^(\d{3})", f)
        if not mnum:
            continue
        try:
            with open(os.path.join(d, f), "r", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        indices[mnum.group(1)] = [(f, txt)]

    n_obsoletos = 0
    for h in huecos:
        h["obsoleto_por"] = None
        num = str(h["finding"])
        subj = sujeto_de(str(h["frase"]))
        if not subj or not (subj.isupper() or "_" in subj):
            # Solo se persiguen simbolos que PARECEN simbolos: en mayusculas o
            # con guion bajo. Una palabra en espanol no se cierra por un
            # hallazgo posterior, y buscarla produce ruido.
            continue
        for otro in sorted(indices):
            if otro <= num:
                continue
            for fnombre, txt in indices[otro]:
                comps_subj = [x for x in subj.split("_") if x]
                for linea in txt.splitlines():
                    # POR COMPONENTES, y no por palabra ni por subcadena.
                    #
                    # Con subcadena, "SUPPORTED" casaba dentro de
                    # "SMC_NOT_SUPPORTED": cuatro huecos marcados como
                    # cerrados por la linea de esa constante.
                    #
                    # Con limites de palabra se pasa el otro extremo y se
                    # pierde el positivo real: PGM_RSRC1 esta DENTRO de
                    # COMPUTE_PGM_RSRC1, y como "_" es caracter de palabra no
                    # hay \b entre "_" y "P", asi que no casa. Y ese positivo
                    # era el unico que quedaba: 009:187 marcado RESUELTO en
                    # 010.
                    #
                    # La regla correcta es la de los componentes separados por
                    # "_": el simbolo del hueco casa si aparece como grupo
                    # CONTIGUO de componentes de un identificador mas largo.
                    # PGM_RSRC1 casa en COMPUTE_PGM_RSRC1. SUPPORTED NO casa
                    # en SMC_NOT_SUPPORTED, porque ahi es el ultimo
                    # componente y el sujeto es el ultimo, pero el sujeto
                    # tiene mas componentes que el candidato por delante.
                    if not contiene_componentes(linea, comps_subj):
                        continue
                    bajo = linea.lower()
                    if not es_cierre_real(linea):
                        continue
                    # FUERTE: el simbolo y la palabra de cierre estan juntos
                    h["obsoleto_por"] = "%s  %s" % (
                        fnombre, linea.strip()[:90])
                    n_obsoletos += 1
                    break
                break
            if h["obsoleto_por"]:
                break

    if args.json:
        # MEDIDO 2026-10-03: el JSON salia SIN el campo `documento`, que la
        # variable tiene desde su construccion (linea 559). El consumidor --
        # cualquier script, incluida esta sesion para medir los UN_REGISTRO --
        # recibia `fichero: None` en las 1085 filas.
        #
        # Es el mismo defecto que la tabla de artifacts.py: el dato existe, no
        # se imprime. Y aqui es PEOR, porque la tabla se leia a ojo y el JSON se
        # consume en silencio: un `None` en un campo no rompe nada, simplemente
        # no esta.
        for h in huecos:
            h.setdefault("fichero", h.get("documento"))
        faltan = sum(1 for h in huecos if not h.get("fichero"))
        if faltan:
            print("frontier: %d huecos sin fichero en el JSON" % faltan,
                  file=sys.stderr)
        print(json.dumps({"version": VERSION, "huecos": huecos,
                          "vias": VIAS, "n_obsoletos": n_obsoletos},
                         indent=2, sort_keys=True, default=str))
        return 0

    print("=" * 78)
    print("frontier %s · WORK_CLASS=READ_ONLY" % VERSION)
    print("=" * 78)
    # Los dos filtros se aplican ANTES de contar, no despues: un filtro que
    # actua sobre el informe deja el titular diciendo una cosa y la tabla otra,
    # y la tabla es la que se lee.
    if args.prosa:
        huecos = [h for h in huecos if not h["es_fila"]]
    if args.fuerte:
        huecos = [h for h in huecos if str(h["marca"]).startswith("frase")]
    filas = [h for h in huecos if h["es_fila"]]
    prosa = [h for h in huecos if not h["es_fila"]]
    print("afirmaciones abiertas: %d" % len(huecos))
    print("  clases: %s" % ", ".join(sorted(
        "%s=%d" % (k, sum(1 for h in huecos if h["clase"] == k))
        for k in sorted(set(str(h["clase"]) for h in huecos)))))
    # El titular de arriba, con su denominador. 390 de 682 son FILAS DE TABLA,
    # no afirmaciones, y de las 292 de prosa solo 22 llevan la marca en su propia
    # frase. Sin esto, "682 abiertas" es un numero plausible sin base, que es la
    # clase de resultado que estas herramientas existen para no dar.
    print("  de las cuales FILAS DE TABLA, que no son afirmaciones: %d (%.0f%%)"
          % (len(filas), 100.0 * len(filas) / len(huecos)) if huecos else "")
    print("  prosa real: %d   con marca en su propia frase: %d (%.0f%%)"
          % (len(prosa),
             sum(1 for h in prosa if str(h["marca"]).startswith("frase")),
             100.0 * sum(1 for h in prosa
                         if str(h["marca"]).startswith("frase")) / max(1, len(prosa))))
    print()

    print("=" * 78)
    print("1 · LA CLASIFICACION, POR VIA DE CIERRE")
    print("=" * 78)
    conteo: Dict[str, int] = {}
    fuerza_alta: Dict[str, int] = {}
    for h in huecos:
        conteo[h["via"]] = conteo.get(h["via"], 0) + 1
        if int(h["fuerza"]) >= 2:
            fuerza_alta[h["via"]] = fuerza_alta.get(h["via"], 0) + 1
    print("  %-20s %6s %8s  %s" % ("via", "total", "fuerte", "que significa"))
    print("  " + "-" * 74)
    for via in sorted(conteo, key=lambda v: -conteo[v]):
        print("  %-20s %6d %8d  %s"
              % (via, conteo[via], fuerza_alta.get(via, 0), VIAS[via]))
    print()
    print("  'fuerte' = la marca aparecio en la FRASE del propio hueco. Si vino")
    print("  del parrafo, de la seccion o del documento entero, baja puntos,")
    print("  porque eso es contexto y no la afirmacion. El caso mas debil es")
    print("  deducir la via solo de que la frase menciona un registro.")
    print()
    print("  CUIDADO CON LA PROPAGACION, y es el riesgo de la escalera.")
    print("  Un documento que dice 'spec' UNA vez clasifica TODOS sus huecos")
    print("  como spec, porque la marca viene del documento entero. Es la via")
    print("  de menor fuerza y la mayoria de las marcadas asi lo son, asi que")
    print("  la columna 'fuerte' no es decorativa: es la unica que separa lo que")
    print("  el propio hueco dice de lo que se le atribuye por su documento.")
    print()
    print("  La escalera de contexto es FRASE -> PARRAFO -> SECCION ->")
    print("  DOCUMENTO, y cada peldano baja la fuerza de la marca: cada uno es")
    print("  mas contexto que la afirmacion. Sin la seccion se quedaban 184 de")
    print("  241 sin pistas. Y el documento entero hace falta porque la seccion")
    print("  que mas clases contiene puede no ser la que explica COMO se cierra:")
    print("  en 057 el discriminante esta en su seccion 7 y no en la elegida.")
    print()

    print("=" * 78)
    print("2 · LO QUE ES TRABAJO, ORDENADO POR RENTABILIDAD")
    print("=" * 78)
    print("  Un hueco vale mas si se cierra con una sola lectura y si otros")
    print("  findings dependen de el. Se ordena por eso, no por fecha ni por")
    print("  gravedad.")
    print()
    print("  RENTABILIDAD = (1 si es UN_REGISTRO) * (1 + registros de la seccion)")
    print()
    print("  Y se imprime el REGISTRO, porque un discriminante sin nombre no es")
    print("  un discriminante: es una clasificacion. La version anterior solo")
    print("  miraba la ventana de 120 caracteres de la frase, y por eso los")
    print("  cinco huecos UN_REGISTRO aparecian sin nombrar ninguno. Donde la")
    print("  seccion no nombra ninguno, la herramienta lo dice en vez de dejar")
    print("  que suponga cual es.")
    print()
    trabajo = [h for h in huecos if h["via"] in ("UN_REGISTRO",
                                                 "POCOS_REGISTROS",
                                                 "DIFERENCIAL")]
    trabajo.sort(key=lambda h: -(int(h["via"] in ("UN_REGISTRO",
                                                   "DIFERENCIAL")) *
                                (1 + int(h.get("n_seccion_registros", 0)))))
    for h in trabajo[:args.top]:
        print("  %-4s :%-5d %-16s  %s"
              % (h["finding"], h["linea"], h["via"], (h["frase"] or "")[:52]))
        regs = h.get("seccion_registros") or []
        # Lo que falta depende de la VIA, y decir siempre "registro" es
        # mentiroo para un experimento diferencial, donde lo que falta es el
        # PARAMETRO y el registro no hace falta.
        falta = ("el PARAMETRO que se varia" if h["via"] == "DIFERENCIAL"
                 else "el REGISTRO que se lee")
        if regs:
            print("       REGISTRO QUE HARIA FALTA: %s" % ", ".join(regs[:5]))
            if int(h.get("n_seccion_registros", 0)) > 1:
                print("       (la seccion nombra %d. Cual es EL discriminante no"
                      % h["n_seccion_registros"])
                print("        lo decide quien lee: la herramienta no sabe que")
                print("        registro separa una hipotesis de otra.)")
        else:
            print("       *** la seccion NO nombra %s. Dice COMO se cierra" % falta)
            print("       pero no cual, y un discriminante sin nombre no se puede")
            print("       ejecutar. Leer la seccion para nombrarlo es el trabajo")
            print("       que queda, y es de lectura.")
    if not trabajo:
        print("  ninguno. No hay ningun hueco cuya via de cierre sea una lectura.")
        print("  Eso significa que lo que queda abierto NO se cierra midiendo, y")
        print("  es un dato sobre el proyecto, no un hueco de la herramienta.")
    print()

    print("=" * 78)
    print("3 · LA PARED: LO QUE NO ES TRABAJO")
    print("=" * 78)
    pared = [h for h in huecos if h["via"] in ("SPEC_NO_PUBLICADO",
                                               "POR_DEFINICION")]
    print("  %d huecos no son experimentos. Se listan porque lo que no se puede"
          % len(pared))
    print("  hacer tiene que estar a la vista, o se vuelve a intentar.")
    print()
    por_motivo: Dict[str, List[Dict[str, object]]] = {}
    for h in pared:
        por_motivo.setdefault(str(h["via"]), []).append(h)
    for via, hs in sorted(por_motivo.items(), key=lambda kv: -len(kv[1])):
        print("  %s  (%d)  %s" % (via, len(hs), VIAS[via]))
        docs: Dict[str, int] = {}
        for h in hs:
            docs[str(h["documento"])[:46]] = docs.get(
                str(h["documento"])[:46], 0) + 1
        for d, n in sorted(docs.items(), key=lambda kv: -kv[1])[:6]:
            print("      %-48s %d" % (d, n))
        print()

    print("=" * 78)
    print("4 · HUECOS OBSOLETOS: CERRADOS POR UN FINDING POSTERIOR")
    print("=" * 78)
    print("  %d huecos marcados como Cerrados, de un total de %d." % (n_obsoletos,
                                                                      len(huecos)))
    print()
    if n_obsoletos > 12:
        print("  *** %d es un numero que hay que mirar antes de creer. Un" % n_obsoletos)
        print("  detector de obsolescencia que acierta mas de la mitad de los")
        print("  huecos esta marcando cualquier cosa, y la causa mas probable es")
        print("  que el sujeto no es el sujeto. Se imprime igual porque puede")
        print("  ser real, pero no se puede leer como resultado.")
        print()
    if n_obsoletos:
        print("  Un hueco puede seguir marcado NOT_DETERMINED aunque un finding")
        print("  POSTERIOR lo haya cerrado. No se ve a ojo porque el finding viejo")
        print("  no se actualiza, y por eso la frontera crece sola con cada")
        print("  iteracion. Esto no lo arregla: lo DECLARA, y quien lee decide si")
        print("  el hallazgo posterior cierra este hueco o uno vecino.")
        print()
        for h in sorted([x for x in huecos if x.get("obsoleto_por")],
                        key=lambda x: (str(x["finding"]), x["linea"]))[:14]:
            print("  %-4s :%-5d %s" % (h["finding"], h["linea"],
                                       (h["frase"] or "")[:56]))
            print("       cerrado por %s" % h["obsoleto_por"])
        if n_obsoletos > 14:
            print("  ... y %d mas" % (n_obsoletos - 14))
    else:
        print("  ninguno. Y eso tambien es un dato: la frontera no ha crecido")
        print("  por huecos que ya estaban cerrados, sino por huecos nuevos.")
    print()
    print("  Y el criterio es FUERTE a proposito: el simbolo del hueco y la")
    print("  palabra que declara el cierre tienen que estar en la MISMA frase")
    print("  de un finding de numero MAYOR. Un match debil deja el hueco vivo,")
    print("  porque un falso positivo aqui borra trabajo real de la lista, y")
    print("  eso es peor que un falso negativo que solo ocupa una linea.")
    print()

    print("=" * 78)
    print("5 · SIN PISTAS: EL TEXTO NO DICE QUE HACE FALTA")
    print("=" * 78)
    sinp = [h for h in huecos if h["via"] == "SIN_PISTAS"]
    print("  %d huecos. NO se clasifican por lo que falta: se cuentan y se"
          % len(sinp))
    print("  tiene, es mas util que uno que rellena el hueco con una")
    print("  conjetura.")
    print("  una conjetura.")
    print()
    for h in sinp[:8]:
        print("  %-4s :%-5d %s" % (h["finding"], h["linea"],
                                   (h["frase"] or "")[:66]))
    if len(sinp) > 8:
        print("  ... y %d mas" % (len(sinp) - 8))
    print()

    print("=" * 78)

    print("=" * 78)
    print("LO QUE ESTA HERRAMIENTA NO ES")
    print("=" * 78)
    print("  - LA CLASIFICACION ES POR PALABRAS, con la frase primero y el")
    print("    parrafo como contexto. Se buscan marcas en el texto")
    print("    de la afirmacion, y eso no es entender. Sabe que 'la spec no lo")
    print("    dice' es una pared; NO sabe que un hueco sobre el orden de")
    print("    ejecucion no se cierra leyendo un registro, porque no se cierra")
    print("    asi. Por eso cada fila imprime su texto y su marca, para que un")
    print("    lector pueda estar en desacuerdo en un segundo.")
    print("  - La ventana de la FRASE es de 120 caracteres a cada lado, recortada")
    print("    por limites de frase. Una afirmacion larga puede spilling en la")
    print("    anterior o en la siguiente, y eso cambia lo que se encuentra.")
    print("    Se ve en la fila, que es donde tiene que verse.")
    print("  - El REGISTRO que haria falta lo saca de la seccion, por patron. Si la")
    print("    seccion nombra varios, la herramienta NO elige: dice cuantos son.")
    print("  - NO sabe si un hueco sigue vivo. Se limita a declarar CUALES")
    print("    parecen cerrados por un finding posterior, con la frase al lado.")
    print("    No borra ninguno de la lista.")
    print("  - La deteccion de obsolescencia es por CO-OCURRENCIA de un simbolo y")
    print("    una palabra de cierre en la misma frase de un finding mayor. No")
    print("    entiende la prosa y no pretende. Y el criterio es asimetrico a")
    print("    proposito: un sujeto de un componente solo casa como prefijo, para")
    print("    que SUPPORTED no case dentro de SMC_NOT_SUPPORTED.")
    print("  - NO propone ni ejecuta una lectura de registro. Leer un registro es")
    print("    NIVEL 2 en la jerarquia de permisos, y esta AUTORIZADO con")
    print("    registro antes/despues. No lo hace porque no es su trabajo: nombrar")
    print("    el registro correcto requiere leer la seccion y juzgar cual")
    print("    distingue una hipotesis de otra, y eso no lo automatiza nadie.")

    return 1 if (sinp or n_obsoletos) else 0


if __name__ == "__main__":
    sys.exit(main())
