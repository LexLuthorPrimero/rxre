"""Las tres capas del hash, SEPARADAS.

El diagrama:

    integridad    -> hash actual == hash declarado?      PASS / FAIL
    autenticidad  -> coincide con referencia confiable?   PASS / NOT_DETERMINED
    validez sem.  -> el artefacto dice lo que el claim
                     afirma?                             requiere PRUEBA

    Un hash detecta cambios. NO autentica. NO valida semantica.

QUE HACE ESTE MODULO Y POR QUE ESTA PARTIDO EN TRES

Lo tempting es una sola funcion que devuelva un booleano: "el hash
coincide, todo bien". Ese unico booleano mezcla tres preguntas distintas y
produce tres mentira distintas segun que falle:

  · Si solo compara artefacto contra artefacto y devuelve OK, ESTA AFIRMANDO
    que nadie altero el archivo. No lo sabe. Solo sabe que dos archivos son
    iguales.
  · Si ademas lo contrasta contra un ancla de confianza y devuelve OK, esta
    autenticando: sostiene que el archivo es el que el ancla declara. Un hash
    no puede demostrar ESO; como maximo puede notar que no encaja.
  · Si ademas lo da por bueno semanticamente, esta validando: sostiene que el
    contenido dice lo que el claim afirma. Eso es una PRUEBA sobre el mundo,
    no una operacion sobre bytes.

Las tres funciones de aqui NO se pueden fusionar sin perder una de esas
diferencias. Por eso la API devuelve la capa, no un veredicto.

    una capa que no puede decir "no lo se" miente por omision
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

INTEGRITY_PASS = "PASS"
INTEGRITY_FAIL = "FAIL"

AUTH_PASS = "PASS"
AUTH_NOT_DETERMINED = "NOT_DETERMINED"
AUTH_FAIL = "FAIL"

# La validez semantica NUNCA se resuelve aqui. Este valor no es una salida
# pragmatica: es la negacion de que exista un atajo.
SEMANTICS_REQUIRES_TEST = "REQUIRES_TEST"

PASS = "PASS"
FAIL = "FAIL"
REQUIRES_TEST = "REQUIRES_TEST"


def hash_file(path: Path) -> str:
    """SHA-256 de un fichero, por bloques.

    Por bloques y no de una vez porque los artefactos de RXRE son binarios
    de cientos de MB y `read()` entero los mete en RAM; un hash que agota la
    memoria no puede usarse en el punto de uso.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- CAPA 1 ---------------------------------------------------------------
def verify_integrity(path: Path, declared_hash: str) -> bool:
    """Capa 1: hash actual == hash declarado?

    Lo UNICO que responde: "este archivo sigue siendo el que medi". No dice
    quien lo escribio, ni si dice lo que dice el claim.

    Devuelve `bool` y no 'PASS'/'FAIL' porque no hay tercer estado: el
    archivo esta o no esta. Un estado "NO_SE" para esta capa seria ruido.
    """
    return hash_file(Path(path)) == declared_hash


# --- CAPA 2 ---------------------------------------------------------------
def verify_authenticity(declared_hash: str, trust_anchor: Path | None) -> str:
    """Capa 2: coincide con una referencia confiable?

    Returns:
        'PASS'           si el anchor contiene algo cuyo hash es el declarado
        'NOT_DETERMINED' si no hay anchor
        'FAIL'           si hay anchor y NO coincide

    EL `None` ES LA PARTE IMPORTANTE. Sin anchor, la respuesta correcta es
    NOT_DETERMINED, no FAIL y no PASS:

      · FAIL seria afirmar "el archivo no es autentico". No lo sabemos: no
        tenemos con que compararlo.
      · PASS seria afirmar "el archivo es autentico". Tampoco: la ausencia de
        referencia no es una referencia que coincida.

    Devolver FAIL ante un None convertiria "no se" en "no", que es el error
    clasico de estos tres estados: convertir la falta de informacion en un
    veredicto. Un hash que no tiene contra quien validarse no es un hash
    falso; es un hash sin referencia.

    Y aun asi, `PASS` aqui NO significa "autentico". Significa "este
    contenido es el que declara el anchor". Quien es el anchor y si el anchor
    es de fiar, son preguntas por encima de esta funcion.
    """
    if trust_anchor is None:
        return AUTH_NOT_DETERMINED
    return AUTH_PASS if hash_file(Path(trust_anchor)) == declared_hash else AUTH_FAIL


# --- CAPA 3 ---------------------------------------------------------------
def verify_semantics(claim: Any, artifact: Path) -> str:
    """Capa 3: el artefacto dice lo que el claim afirma?

    Returns:
        'REQUIRES_TEST', SIEMPRE.

    Siempre, sin excepcion, y esa es la funcion de la funcion. La validez
    semantica no se deduce de un hash: requiere ejecutar la afirmacion contra
    el artefacto y observar si se sostiene. Un hash que coincidiera no
    distinguiria un artefacto que dice la verdad de otro identico que miente
    con las mismas palabras.

    Que la funcion tenga `claim` y `artifact` como parametros y aun asi
    responda siempre lo mismo NO es un stub: es una afirmacion sobre lo que es
    comprobable con esta pieza. Si alguna vez devolviera otra cosa, ese
    alguien habria convertido un hash en un oraculo, que es exactamente lo
    que el diagrama prohibe.
    """
    return SEMANTICS_REQUIRES_TEST


def verify_all(path: Path, declared_hash: str,
               trust_anchor: Path | None = None,
               claim: Any = None) -> dict[str, str]:
    """Las tres capas, JUNTAS pero SEPARADAS en el resultado.

    Existe para que quien use el hash tenga las tres respuestas delante y no
    solo la primera. Un consumidor que solo lee `integridad` y se lo pasa a
    otro como si fuera "validado" ha recreado el error que este modulo
    evita; devolverlas juntas no lo impide, pero lo hace visible.
    """
    integridad = INTEGRITY_PASS if verify_integrity(path, declared_hash) \
        else INTEGRITY_FAIL
    return {
        "integridad": integridad,
        "autenticidad": verify_authenticity(declared_hash, trust_anchor),
        "validez_semantica": (verify_semantics(claim, path) if claim is not None
                               else SEMANTICS_REQUIRES_TEST),
    }