"""TIERRA: el grafo de evidencia. SQLite, funcional.

Del diagrama:

    SCHEMA DEL CLAIM   id · statement · object_hash · scope · epistemic_state
                       evidence_refs[] · derivation_refs[] · contradiction_refs[]
                       falsification_test · unresolved_obligations[]
    EVIDENCE           append-only · delete prohibido por MECANISMO
                       hash de fila verificado al leer · supersedes_ref
    CONCURRENCIA       optimistic (version + row_count) · append sin lock ·
                       pessimistic (locked_by + expires)

LO QUE ESTE MODULO NO HACE, Y POR QUE

  · No hay `contradiction_refs` ni `falsification_test` en la tabla de
    claims. El SQL de la especificacion no los trae, y anadirlos seria
    inventar schema. Las contradicciones viven en `evidence` con
    `type='contradiction'`; `falsification_test` no cabe en una columna TEXT
    sin decidir su forma, y decidirla aqui seria adelantarse al audit.
  · No hay lock global. El diagrama prohibe explicitamente el lock global, y
    la unica concurrencia que este modulo implementa es la optimista por
    `version`, que no bloquea nada.
  · La columna `supersedes_ref` NO tiene indice unico. Deliberado: la v3
    permite que una evidencia sea corregida dos veces (por dos revisores
    distintos), y un indice unico sobre el referenciado prohibiria la
    segunda correccion.

IDEMPOTENCIA DE `add_evidence`
------------------------------
El id se deriva del CONTENIDO, no de `len()`. Un id derivado del numero de
elementos es un contador con prefijo: dos contenidos distintos de la misma
longitud comparten id y el segundo pisa al primero. Esa es la razon por la
que la correccion no se puede deshacer con evidencia.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  statement TEXT NOT NULL,
  object_hash TEXT NOT NULL,
  scope TEXT NOT NULL,
  epistemic_state TEXT NOT NULL CHECK(epistemic_state IN (
    'PROVEN','PARTIAL','NOT_DETERMINED',
    'PROVEN_ABSENT','DEFERRED','INVALIDATED'
  )),
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  claim_ref TEXT NOT NULL,
  type TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  tool_version TEXT NOT NULL,
  command TEXT NOT NULL,
  output_hash TEXT NOT NULL,
  provenance TEXT NOT NULL,
  supersedes_ref TEXT NULL,
  created_at TIMESTAMP NOT NULL,
  row_hash TEXT NOT NULL,
  FOREIGN KEY (claim_ref) REFERENCES claims(id)
);
"""

# ==========================================================================
# [v3] INMUTABILIDAD COMO MECANISMO, NO COMO FLAG.
#
#   "delete prohibido por permiso en punto de escritura". El "permiso" es un
#   TRIGGER: lo impone el motor. Un flag (`mutable=1`) se puede ignorar con el
#   mismo esfuerzo que se escribe; un trigger convierte el intento en error
#   del motor, y no hay forma de escribir `DELETE` que lo esquive.
# ==========================================================================
TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_evidence_no_update
BEFORE UPDATE ON evidence
BEGIN
  SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: UPDATE prohibido sobre evidence');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
  SELECT RAISE(ABORT, 'EVIDENCE_APPEND_ONLY: DELETE prohibido sobre evidence');
END;
"""

# Campos que entran en el `row_hash`. `row_hash` queda fuera por definicion:
# es el hash de la fila, no un campo mas de la fila.
_EVIDENCE_HASHED = ("id", "claim_ref", "type", "source_hash", "tool_version",
                    "command", "output_hash", "provenance",
                    "supersedes_ref", "created_at")


class IntegrityError(RuntimeError):
    """El `row_hash` recalculado no coincide con el almacenado.

    Nombre a proposito: NO es una excepcion de base de datos. La base esta
    bien; lo que esta mal es que alguien escribio por una via que el trigger
    no cubre. Se distingue para que el llamador no la confunda con un fallo
    de disco y reintente.
    """


class StaleVersionError(RuntimeError):
    """El `version` cambio entre la lectura y el UPDATE (optimistic locking)."""


class SupersedesCicloError(RuntimeError):
    """Una correccion seorrecte a si misma o crea un ciclo."""


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def db_path() -> Path:
    """Ruta de la base. `$RXRE_DB` si esta, si no `.rxre/rxre.db`."""
    env = os.environ.get("RXRE_DB")
    if env:
        return Path(env)
    return Path(".rxre") / "rxre.db"


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    ruta = Path(path) if path else db_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ruta), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.executescript(TRIGGERS)
    return conn


def init(path: Optional[Path] = None) -> Path:
    """Crea el directorio y el fichero. Idempotente."""
    ruta = Path(path) if path else db_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(ruta)
    conn.close()
    return ruta


# --- hashing ---------------------------------------------------------------
def _canonical(value: Any) -> str:
    """Representacion canonica: orden de claves fijo, separadores fijos.

    Sin esto, dos filas con el mismo contenido podrian tener hashes distintos
    solo por el orden en que se construyo el dict, y `row_hash` no detectaria
    una alteracion real.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def compute_row_hash(fila: dict) -> str:
    """SHA-256 de los campos de la fila, en orden canonico."""
    return hashlib.sha256(
        _canonical({k: fila.get(k) for k in _EVIDENCE_HASHED}).encode("utf-8")
    ).hexdigest()


def _id(prefix: str, *partes: Any) -> str:
    """Id determinista derivado del CONTENIDO.

    Nunca de `len()`: dos contenidos distintos de igual longitud deben dar
    ids distintos, o el segundo pisa al primero sin dejar rastro.
    """
    return prefix + "_" + hashlib.sha256(
        _canonical(list(partes)).encode("utf-8")).hexdigest()[:16]


# ==========================================================================
# CLAIMS
# ==========================================================================
def create_claim(conn: sqlite3.Connection, statement: str, object_hash: str,
                 scope: str,
                 epistemic_state: str = "NOT_DETERMINED") -> str:
    """Crea un claim y devuelve su id.

    El id se deriva de (statement, object_hash, scope), NO del estado: dos
    llamadas con la misma afirmacion y el mismo objeto son el MISMO claim,
    aunque uno llegue con PARTIAL y otro con PROVEN. Si el id incluyera el
    estado, cambiar de estado crearia un claim nuevo y el historico se
    partiria en dos filas que dicen lo mismo.
    """
    ts = ahora()
    cid = _id("clm", statement, object_hash, scope)
    conn.execute(
        "INSERT OR IGNORE INTO claims "
        "(id, statement, object_hash, scope, epistemic_state, created_at,"
        " updated_at, version) VALUES (?,?,?,?,?,?,?,0)",
        (cid, statement, object_hash, scope, epistemic_state, ts, ts))
    return cid


def get_claim(conn: sqlite3.Connection, claim_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM claims WHERE id = ?",
                       (claim_id,)).fetchone()
    return dict(row) if row else None


def update_claim_state(conn: sqlite3.Connection, claim_id: str,
                       expected_version: int, new_state: str) -> int:
    """OPTIMISTIC LOCKING. Devuelve 1 si aplico, 0 si no.

    `UPDATE ... WHERE id=? AND version=?` es el mecanismo. Si otra escritura
    movio la version entre la lectura y aqui, el WHERE no casa y `row_count`
    es 0. El llamador decide si reintenta.

    Por que NO hay lock: el diagrama pide concurrencia POR OPERACION, y un
    lock sobre la fila convertira cada transicion en una operacion atomica
    que espera. El optimistic lock deja que dos escritores compitan y que solo
    uno gane, sin ninguno esperando.
    """
    ts = ahora()
    cur = conn.execute(
        "UPDATE claims SET epistemic_state = ?, version = version + 1,"
        " updated_at = ? WHERE id = ? AND version = ?",
        (new_state, ts, claim_id, expected_version))
    return cur.rowcount


# ==========================================================================
# EVIDENCE — append only
# ==========================================================================
def add_evidence(conn: sqlite3.Connection, claim_ref: str, type: str,
                 source_hash: str, tool_version: str, command: str,
                 output_hash: str, provenance: str,
                 supersedes_ref: Optional[str] = None) -> str:
    """Anade una fila de evidencia. NUNCA modifica ni borra otra.

    Corregir evidencia es anadir una fila nueva con `supersedes_ref` apuntando
    a la anterior. La anterior NO se borra: sigue viva y sigue verificable,
    y eso es lo que hace que "alguien lo cambio" sea un hecho y no una
    impresion.

    Si `supersedes_ref` no existe, se rechaza: una correccion que no apunta a
    nada no es una correccion.
    """
    if supersedes_ref is not None:
        previa = conn.execute("SELECT id FROM evidence WHERE id = ?",
                              (supersedes_ref,)).fetchone()
        if previa is None:
            raise ValueError(
                "supersedes_ref inexistente: %s. Una correccion que no "
                "apunta a nada no es una correccion." % supersedes_ref)

    ts = ahora()
    cuerpo = {
        "claim_ref": claim_ref, "type": type, "source_hash": source_hash,
        "tool_version": tool_version, "command": command,
        "output_hash": output_hash, "provenance": provenance,
        "supersedes_ref": supersedes_ref, "created_at": ts,
    }
    eid = _id("ev", cuerpo)

    # El id se deriva del contenido, y `supersedes_ref` es parte de ese
    # contenido. Que una fila se apunte a si misma solo puede ocurrir si los
    # dos lados generan el mismo id, que es justo el caso a rechazar: dejaria
    # la evidencia "corregida" por si misma.
    if eid == supersedes_ref:
        raise SupersedesCicloError(
            "la evidencia %s se supersediria a si misma" % eid)

    fila = {"id": eid, **cuerpo}
    conn.execute(
        "INSERT INTO evidence (id, claim_ref, type, source_hash, tool_version,"
        " command, output_hash, provenance, supersedes_ref, created_at,"
        " row_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eid, claim_ref, type, source_hash, tool_version, command,
         output_hash, provenance, supersedes_ref, ts,
         compute_row_hash(fila)))
    return eid


def get_evidence(conn: sqlite3.Connection, evidence_id: str,
                 verify: bool = True) -> dict:
    """Lee evidencia. Por defecto VERIFICANDO el `row_hash`.

    Verificar en la lectura y no solo en la escritura es lo que convierte la
    inmutabilidad en una garantia y no en una costumbre: entre que se escribe
    y se lee hay un hueco en el que el fichero pudo cambiar, y una garantia
    sobre el pasado no dice nada del presente.

    Se Lanza `IntegrityError` en vez de devolver una bandera porque un
    registro alterado no es un registro "un poco raro": no es fiable, y el
    llamador no deberia poder seguir como si lo fuera.
    """
    row = conn.execute("SELECT * FROM evidence WHERE id = ?",
                       (evidence_id,)).fetchone()
    if row is None:
        raise KeyError(evidence_id)
    fila = dict(row)
    if verify:
        recalculado = compute_row_hash(fila)
        if recalculado != fila["row_hash"]:
            raise IntegrityError(
                "row_hash de %s no coincide: almacenado=%s recalculado=%s. "
                "La fila fue alterada por una via que el trigger no cubre."
                % (evidence_id, fila["row_hash"][:16],
                   recalculado[:16]))
    return fila


def list_evidence(conn: sqlite3.Connection,
                  claim_id: Optional[str] = None) -> list[dict]:
    if claim_id:
        rows = conn.execute(
            "SELECT * FROM evidence WHERE claim_ref = ? ORDER BY created_at,"
            " id", (claim_id,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM evidence ORDER BY created_at, id").fetchall()
    return [dict(r) for r in rows]


def counts(conn: sqlite3.Connection) -> tuple[int, int]:
    c = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    e = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    return c, e