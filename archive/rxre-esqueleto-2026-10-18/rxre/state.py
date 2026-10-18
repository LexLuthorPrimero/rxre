"""Maquina de estados epistemicos. Funcional.

Del diagrama:

    ESTADOS EPISTEMICOS (6, [v3] incluye INVALIDATED)
      PROVEN | PARTIAL | NOT_DETERMINED | PROVEN_ABSENT | DEFERRED | INVALIDATED

    [v3] INVALIDATED != automatico:
      contradiccion -> reevaluacion documentada -> puede resultar INVALIDATED
      o volver a PROVEN si se refuta la contradiccion

QUE HACE ESTA TABLA Y POR QUE ES UNA TABLA Y NO UNA FUNCION

Las transiciones validas son una RELACION, no un procedimiento. Escribirlas
como una funcion con `if` repetidos produce dos fallos que la tabla hace
imposibles:

  ·olvidar un caso en una rama (un estado al que no se puede llegar nunca)
  ·aceptar un caso que no se documento (un `else` generico)

Con la tabla, lo que NO esta en la tabla es invalido por construccion. Anadir
un estado obliga a decidir, para ese estado, a que se puede llegar: no hay
default.

EL RECORRIDO DE `PROVEN_ABSENT` ES DELIBERADO
    PROVEN_ABSENT -> NOT_DETERMINED, y solo eso.

Es el unico estado del que no se sale hacia adelante. `PROVEN_ABSENT` afirma
"hemos probado que no esta", y esa afirmacion solo puede refutarse volviendo a
"no lo se": nadie ha vuelto a "si, esta". Un sistema que permitiera
PROVEN_ABSENT -> PROVEN tendria que permitirlo SIN nueva evidencia, que es
justo el salto que la v3-2 y la v3-5 prohiben.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import db as _db

PROVEN = "PROVEN"
PARTIAL = "PARTIAL"
NOT_DETERMINED = "NOT_DETERMINED"
PROVEN_ABSENT = "PROVEN_ABSENT"
DEFERRED = "DEFERRED"
INVALIDATED = "INVALIDATED"

VALID_TRANSITIONS: dict[str, set[str]] = {
    PROVEN: {PARTIAL, INVALIDATED, NOT_DETERMINED},
    PARTIAL: {PROVEN, NOT_DETERMINED, INVALIDATED},
    NOT_DETERMINED: {PROVEN, PARTIAL, PROVEN_ABSENT, DEFERRED},
    PROVEN_ABSENT: {NOT_DETERMINED},
    DEFERRED: {NOT_DETERMINED},
    INVALIDATED: {NOT_DETERMINED},
}

# El tipo de evidencia que autoriza una invalidacion. `REVERTED` no es un
# estado: es la decision de volver a PROVEN cuando la contradiccion que causo
# INVALIDATED se refuta. Sin esa via de vuelta, INVALIDATED seria terminal y
# la primera contradiccion que llegara ganaria para siempre.
TRANSITION_TYPE_CONTRADICTION = "contradiction"


class InvalidTransitionError(ValueError):
    """La transicion no esta en `VALID_TRANSITIONS`.

    `ValueError` y no `KeyError`: un `KeyError` sugeriria que falta una clave,
    cuando lo que falta es la RELACION entre dos estados que si existen.
    """


class MissingContradictionError(ValueError):
    """Se pidio INVALIDATED sin evidencia de contradiccion.

    Es la v3-2 hecha exception. Sin este chequeo, INVALIDATED seria un valor
    mas de una columna y bastaria con teclearlo para tumbar un claim que
    nadie ha revisado.
    """


def is_valid(current: str, new: str) -> bool:
    return new in VALID_TRANSITIONS.get(current, set())


def contradiction_exists(conn: sqlite3.Connection, claim_id: str) -> bool:
    """Hay evidencia de tipo 'contradiction' para este claim."""
    row = conn.execute(
        "SELECT 1 FROM evidence WHERE claim_ref = ? AND type = ? LIMIT 1",
        (claim_id, TRANSITION_TYPE_CONTRADICTION)).fetchone()
    return row is not None


def transition(claim_id: str, new_state: str, reason: str,
               conn: Optional[sqlite3.Connection] = None) -> dict:
    """Cambia el estado de un claim. Optimistic locking, sin lock global.

    El orden de las comprobaciones NO es arbitrario:

      1. el claim existe
      2. la transicion es valida desde el estado ACTUAL (leido aqui, no antes)
      3. si el destino es INVALIDATED, hay `reason` y hay contradiccion
      4. el UPDATE optimista aplica (si no, `StaleVersionError`)

    El paso 2 se valida contra el estado leido EN EL MOMENTO, y el paso 4
    vuelve a comprobar la version. Esa doble comprobacion no es redundante:
    entre la lectura y el UPDATE otro escritor pudo mover el estado. Sin el
    paso 4, un escritor podria aplicar una transicion que se valido contra un
    estado que ya no era el suyo.

    Raises:
        ValueError            si el claim no existe o falta `reason`
        InvalidTransitionError si la transicion no es valida
        MissingContradictionError si es INVALIDATED sin contradiccion
        StaleVersionError     si otro escritor gano la carrera
    """
    propia = conn is None
    conn = conn or _db.connect()
    try:
        claim = _db.get_claim(conn, claim_id)
        if claim is None:
            raise ValueError("claim inexistente: %s" % claim_id)

        actual = claim["epistemic_state"]
        if actual == new_state:
            raise InvalidTransitionError(
                "%s ya esta en %s. Una transicion a si mismo no es una "
                "transicion: significa que la version o la reevaluacion se "
                "han saltado." % (claim_id, new_state))
        if not is_valid(actual, new_state):
            raise InvalidTransitionError(
                "transicion invalida %s -> %s. Validas desde %s: %s"
                % (actual, new_state, actual,
                   ", ".join(sorted(VALID_TRANSITIONS.get(actual, set())))
                   or "ninguna"))

        if new_state == INVALIDATED:
            if not (reason or "").strip():
                raise ValueError(
                    "INVALIDATED exige `reason`: la v3-2 prohibe que la "
                    "invalidacion sea automatica, y un motivo vacio es "
                    "automatico con otra forma")
            if not contradiction_exists(conn, claim_id):
                raise MissingContradictionError(
                    "INVALIDATED exige evidencia type='contradiction' para "
                    "%s. Sin ella no hay nada que reevaluar." % claim_id)

        applied = _db.update_claim_state(conn, claim_id, claim["version"],
                                         new_state)
        if applied != 1:
            raise _db.StaleVersionError(
                "version de %s cambio antes del UPDATE (se esperaba %d). "
                "Reintenta con la version leida."
                % (claim_id, claim["version"]))

        updated = _db.get_claim(conn, claim_id)
        updated["reason"] = reason
        return updated
    finally:
        if propia:
            conn.close()