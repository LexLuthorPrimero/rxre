"""Maquina de estados: transiciones validas, invalidas, e INVALIDATED.

Lo que mas importa aqui no es que una transicion valida funcione: es que una
INVALID que no funciona. Si `INVALIDATED` se pudiera alcanzar sin contradiccion
y sin motivo, la v3-2 estaria ausente y el estado nuevo no valdria nada.
"""
from __future__ import annotations

import pytest

from rxre import db, state


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "s.sqlite3")
    yield c
    c.close()


@pytest.fixture()
def claim(conn):
    return db.create_claim(conn, "el binario expone 3 funciones",
                          "sha:abc", "binary.functions")


def test_transition_valid(conn, claim):
    """NOT_DETERMINED -> PROVEN esta permitida y mueve la version."""
    res = state.transition(claim, "PROVEN", "dos producers coinciden", conn)
    assert res["epistemic_state"] == "PROVEN"
    assert res["version"] == 1


def test_transition_invalid(conn, claim):
    """Lo que NO esta en la tabla es invalido por construccion."""
    # El claim esta en NOT_DETERMINED; PROVEN_ABSENT si es valido desde ahi,
    # pero NOT_DETERMINED -> INVALIDATED no lo es: no se puede invalidar algo
    # que nunca se afirmo.
    with pytest.raises(state.InvalidTransitionError, match="invalida"):
        state.transition(claim, "INVALIDATED", "porque si", conn)

    # Y una transicion a si mismo tampoco.
    with pytest.raises(state.InvalidTransitionError, match="ya esta"):
        state.transition(claim, "NOT_DETERMINED", "", conn)


def test_proven_absent_is_a_one_way_door(conn, claim):
    """PROVEN_ABSENT solo sale a NOT_DETERMINED. Nunca a PROVEN.

    'Hemos probado que no esta' no puede convertirse en 'si, esta' sin nueva
    evidencia, y la tabla no tiene esa arista porque no deberia existir.
    """
    state.transition(claim, "PROVEN_ABSENT", "vacio + discriminante", conn)
    with pytest.raises(state.InvalidTransitionError):
        state.transition(claim, "PROVEN", "ahora si", conn)
    res = state.transition(claim, "NOT_DETERMINED", "hay que medir otra vez",
                           conn)
    assert res["epistemic_state"] == "NOT_DETERMINED"


def test_invalidated_requires_contradiction(conn, claim):
    """[v3-2] INVALIDATED exige motivo Y evidencia de contradiccion.

    Se llega a PROVEN primero, porque INVALIDATED no es alcanzable desde
    NOT_DETERMINED. Desde PROVEN si lo es, pero sin contradiccion registrada.
    """
    state.transition(claim, "PROVEN", "medido", conn)

    # Sin evidencia de contradiccion -> RECHAZADO. El mensaje usa el literal
    # ingles 'contradiction' porque es el valor del campo `type`; el regex
    # busca ese literal, no la palabra castellana.
    with pytest.raises(state.MissingContradictionError, match="contradiction"):
        state.transition(claim, "INVALIDATED", "el otro producer discrepa", conn)

    # Sin motivo -> RECHAZADO, aunque haya contradiccion.
    db.add_evidence(conn, claim, "contradiction", "sha:s", "ghidra", "cmd",
                    "sha:o", "{}")
    with pytest.raises(ValueError, match="reason"):
        state.transition(claim, "INVALIDATED", "   ", conn)

    # Con ambas cosas -> ACEPTADO.
    res = state.transition(claim, "INVALIDATED",
                           "el segundo producer cuenta 5", conn)
    assert res["epistemic_state"] == "INVALIDATED"


def test_invalidated_is_reversible_to_not_determined(conn, claim):
    """INVALIDATED no es terminal: se vuelve a NOT_DETERMINED para reevaluar.

    Un estado del que no se sale obliga a reabrir el claim entero. Este
    recorrido permite refutar la contradiccion sin perder el resto.
    """
    state.transition(claim, "PROVEN", "medido", conn)
    db.add_evidence(conn, claim, "contradiction", "sha:s", "ghidra", "cmd",
                    "sha:o", "{}")
    state.transition(claim, "INVALIDATED", "discrepancia", conn)
    res = state.transition(claim, "NOT_DETERMINED", "hay que reevaluar", conn)
    assert res["epistemic_state"] == "NOT_DETERMINED"


def test_stale_version_is_detected(conn, claim, monkeypatch):
    """Doble comprobacion: transicion valida contra el estado REAL.

    `transition` valida la transicion contra el estado que LEE, y luego
    actualiza con `WHERE version = <la que leyo>`. Entre una cosa y otra cabe
    otro escritor.

    En un solo hilo esa ventana no se abre nunca: `transition` relee al entrar
    y el `UPDATE` va con esa misma version, asi que aplicaria siempre. Para
    simular la carrera hay que hacer que otro escritor actue EN MEDIO, y eso
    es lo que hace este monkeypatch: intercepta la lectura y, justo despues de
    devolverla, mueve la version por debajo.

    Sin ese patch, el test pasaria por el motivo equivocado — porque la
    carrera no ocurrió — y no probaria nada.
    """
    leida = {}
    original = db.get_claim          # el patch re-resuelve el atributo, asi
                                    # que sin esta referencia se llama a si
                                    # mismo hasta reventar la pila

    def get_claim_trap(_conn, claim_id):
        fila = original(_conn, claim_id)
        if "primera" not in leida:
            leida["primera"] = fila["version"]
            # El otro escritor, entre la lectura y el UPDATE.
            db.update_claim_state(_conn, claim_id, fila["version"], "PARTIAL")
        return fila

    monkeypatch.setattr(state._db, "get_claim", get_claim_trap)

    with pytest.raises(db.StaleVersionError, match="cambio antes del UPDATE"):
        state.transition(claim, "PROVEN", "con una version ya caduca", conn)


def test_transition_on_missing_claim(conn):
    with pytest.raises(ValueError, match="inexistente"):
        state.transition("clm_no_existe", "PROVEN", "", conn)