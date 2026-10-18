"""AIRE: traza de decisiones → herramientas → resultados."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


class Aire:
    def __init__(self, db_path: str = ".rxre/aire.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS aire_traces (
                    trace_id TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    herramienta TEXT NOT NULL,
                    resultado TEXT,
                    error TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

    def trazar(self, decision: str, herramienta: str) -> str:
        trace_id = f"tr-{uuid.uuid4().hex[:12]}"
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO aire_traces (trace_id, decision, herramienta, timestamp) VALUES (?, ?, ?, ?)",
                (trace_id, decision, herramienta, datetime.utcnow().isoformat())
            )
        return trace_id

    def resultado(self, trace_id: str, resultado: str = None, error: str = None):
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "UPDATE aire_traces SET resultado=?, error=? WHERE trace_id=?",
                (resultado, error, trace_id)
            )

    def reconstruir(self, trace_id: str = None) -> dict | None:
        with sqlite3.connect(self.db_path) as c:
            if trace_id:
                cursor = c.execute(
                    "SELECT * FROM aire_traces WHERE trace_id=?", (trace_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cursor.description]
                return dict(zip(cols, row))
            cursor = c.execute(
                "SELECT * FROM aire_traces ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
