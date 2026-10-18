"""DISCIPLINA: máquina de estados de los 6 pasos metodológicos."""
import sqlite3, json, uuid
from datetime import datetime
from pathlib import Path

PASOS = ["EVIDENCE", "SEMANTICS", "SCHEMA",
         "DISCRIMINATING_TEST", "IMPLEMENTATION", "VALIDATION"]
INDICE = {p: i for i, p in enumerate(PASOS)}


class Disciplina:
    def __init__(self, db_path: str = ".rxre/disciplina.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS disciplina_investigaciones (
                    invest_id TEXT PRIMARY KEY,
                    objetivo TEXT NOT NULL,
                    paso_actual TEXT NOT NULL DEFAULT 'EVIDENCE',
                    evidencia_id TEXT,
                    aborted_at TEXT,
                    abort_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS disciplina_transiciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invest_id TEXT NOT NULL,
                    desde TEXT NOT NULL,
                    hacia TEXT NOT NULL,
                    payload TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (invest_id) REFERENCES disciplina_investigaciones(invest_id)
                )
            """)

    def iniciar(self, objetivo: str) -> str:
        iid = f"inv-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO disciplina_investigaciones (invest_id, objetivo, paso_actual, created_at, updated_at) VALUES (?, ?, 'EVIDENCE', ?, ?)",
                (iid, objetivo, now, now)
            )
        return iid

    def avanzar(self, invest_id: str, hacia: str, payload: dict = None) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute(
                "SELECT paso_actual, aborted_at FROM disciplina_investigaciones WHERE invest_id=?",
                (invest_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"invest no existe: {invest_id}")
            actual, aborted_at = row
            if aborted_at:
                raise ValueError(f"invest abortada: {invest_id}")

            if hacia not in INDICE:
                raise ValueError(f"paso inválido: {hacia}")

            if INDICE[hacia] != INDICE[actual] + 1:
                self._abortar(c, invest_id, f"saltó de {actual} a {hacia}")
                c.execute("COMMIT")
                raise ValueError(
                    f"SALTO DE PASO: {actual} → {hacia} (esperado: {PASOS[INDICE[actual] + 1]})"
                )

            now = datetime.utcnow().isoformat()
            c.execute(
                "UPDATE disciplina_investigaciones SET paso_actual=?, updated_at=? WHERE invest_id=?",
                (hacia, now, invest_id)
            )
            c.execute(
                "INSERT INTO disciplina_transiciones (invest_id, desde, hacia, payload, timestamp) VALUES (?, ?, ?, ?, ?)",
                (invest_id, actual, hacia, json.dumps(payload or {}), now)
            )
        return {"ok": True, "invest_id": invest_id, "paso_actual": hacia}

    def _abortar(self, c, invest_id: str, razon: str):
        now = datetime.utcnow().isoformat()
        c.execute(
            "UPDATE disciplina_investigaciones SET aborted_at=?, abort_reason=? WHERE invest_id=?",
            (now, razon, invest_id)
        )

    def estado(self, invest_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as c:
            cursor = c.execute(
                "SELECT * FROM disciplina_investigaciones WHERE invest_id=?", (invest_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def historial(self, invest_id: str) -> list:
        with sqlite3.connect(self.db_path) as c:
            cursor = c.execute(
                "SELECT * FROM disciplina_transiciones WHERE invest_id=? ORDER BY timestamp", (invest_id,)
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]
