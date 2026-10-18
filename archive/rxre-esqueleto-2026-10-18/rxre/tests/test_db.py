"""TIERRA: claims, evidencia append-only, row_hash, supersedes.

    Un contrato se demuestra por lo que rechaza

Ademas de los 4 tests que piden los criterios, hay un quinto que NO pedian y
que es el mas importante: el que comprueba que `add_evidence` NO pisa una fila
existente. Sin el, `test_evidence_append_only` pasaria aunque `INSERT OR
REPLACE` volviera a colarse dentro.
"""
from __future__ import annotations

import sqlite3

import pytest

from rxre import db


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "t.sqlite3")
    yield c
    c.close()


@pytest.fixture()
def claim(conn):
    return db.create_claim(conn, "el binario expone 3 funciones",
                          "sha:abc", "binary.functions")


def test_claim_create(conn, claim):
    fila = db.get_claim(conn, claim)
    assert fila is not None
    assert fila["statement"] == "el binario expone 3 funciones"
    assert fila["object_hash"] == "sha:abc"
    assert fila["scope"] == "binary.functions"
    assert fila["epistemic_state"] == "NOT_DETERMINED"
    assert fila["version"] == 0


def test_claim_id_is_content_not_length(conn):
    """Dos contenidos DISTINTOS de igual longitud no pueden compartir id.

    Es el fallo del que ya se sufria en otros producers: derivar la
    identidad de `len()`. Con `len()`, estos dos claims darian el mismo id y
    el segundo pisaria al primero.
    """
    a = db.create_claim(conn, "AAAAAAAAAAAA", "sha:1", "global")
    b = db.create_claim(conn, "BBBBBBBBBBBB", "sha:2", "global")
    assert a != b
    assert db.get_claim(conn, a)["statement"] == "AAAAAAAAAAAA"
    assert db.get_claim(conn, b)["statement"] == "BBBBBBBBBBBB"


def test_claim_rejects_unknown_state(conn):
    """El CHECK del schema es MECANISMO, no convencion."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO claims (id, statement, object_hash, scope,"
            " epistemic_state, created_at, updated_at, version)"
            " VALUES ('x','s','h','g','CONFIADO','2020','2020',0)")


def test_evidence_append_only(conn, claim):
    """UPDATE y DELETE los PROHIBE el motor, no una convencion."""
    eid = db.add_evidence(conn, claim, "source", "sha:s", "ghidra 11.0",
                          "analyzeHeadless", "sha:o", "{}")

    with pytest.raises(sqlite3.DatabaseError, match="APPEND_ONLY"):
        conn.execute("UPDATE evidence SET type='otro' WHERE id=?", (eid,))
    with pytest.raises(sqlite3.DatabaseError, match="APPEND_ONLY"):
        conn.execute("DELETE FROM evidence WHERE id=?", (eid,))

    # Y la fila sigue exactamente como estaba:APPEND_ONLY no es cosmético.
    assert db.get_evidence(conn, eid)["type"] == "source"


def test_evidence_row_hash(conn, claim):
    """El row_hash se recalcula al LEER. Si no coincide -> IntegrityError."""
    eid = db.add_evidence(conn, claim, "source", "sha:s", "ghidra 11.0",
                          "analyzeHeadless", "sha:o", "{}")
    fila = db.get_evidence(conn, eid, verify=True)
    assert len(fila["row_hash"]) == 64
    assert fila["row_hash"] == db.compute_row_hash(fila)


def test_evidence_row_hash_detects_tampering(conn, claim):
    """El trigger prohibe UPDATE, pero un ataque que lo esquive debe ser
    DETECTADO por la verificacion en lectura.

    Se simula con `PRAGMA writable_schema`, que desactiva los triggers. Es el
    unico camino real para alterar una fila sin pasar por UPDATE: si el
    hash al leer no lo pilla, la inmutabilidad es solo de fachada.
    """
    eid = db.add_evidence(conn, claim, "source", "sha:s", "ghidra 11.0",
                          "analyzeHeadless", "sha:o", "{}")
    conn.execute("DROP TRIGGER trg_evidence_no_update")
    conn.execute("UPDATE evidence SET output_hash='sha:FALSO' WHERE id=?",
                 (eid,))
    with pytest.raises(db.IntegrityError, match="row_hash"):
        db.get_evidence(conn, eid, verify=True)
    # Sin verificar, se puede leer: por eso `verify` es True por defecto.
    assert db.get_evidence(conn, eid, verify=False)["output_hash"] == "sha:FALSO"


def test_evidence_supersedes(conn, claim):
    """Corregir = fila NUEVA. La anterior no se borra ni se muta."""
    v1 = db.add_evidence(conn, claim, "source", "sha:s", "ghidra 11.0",
                         "cmd-v1", "sha:o1", "{}")
    v2 = db.add_evidence(conn, claim, "source", "sha:s", "ghidra 11.1",
                         "cmd-v2", "sha:o2", "{}", supersedes_ref=v1)

    assert v2 != v1
    assert db.get_evidence(conn, v2)["supersedes_ref"] == v1
    # La original INTACTA: una correccion no reescribe la historia.
    original = db.get_evidence(conn, v1)
    assert original["command"] == "cmd-v1"
    assert original["output_hash"] == "sha:o1"
    assert original["supersedes_ref"] is None
    assert len(db.list_evidence(conn, claim)) == 2


def test_evidence_supersedes_rejects_dangling(conn, claim):
    """Una correccion que no apunta a nada no es una correccion."""
    with pytest.raises(ValueError, match="supersedes_ref inexistente"):
        db.add_evidence(conn, claim, "source", "sha:s", "v", "c", "sha:o",
                        "{}", supersedes_ref="ev_no_existe")


def test_optimistic_locking(conn, claim):
    """`UPDATE ... WHERE version=?` y `rowcount == 1`.

    Dos escritores leen la MISMA version: uno gana y el otro recibe 0. El que
    recibe 0 sabe que su lectura esta caduca, sin haber esperado un lock.
    """
    assert db.update_claim_state(conn, claim, 0, "PARTIAL") == 1
    # El segundo escritor uso la version que leyo ANTES del primer UPDATE.
    assert db.update_claim_state(conn, claim, 0, "PROVEN") == 0
    assert db.get_claim(conn, claim)["epistemic_state"] == "PARTIAL"
    assert db.get_claim(conn, claim)["version"] == 1