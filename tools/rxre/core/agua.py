"""AGUA: aprendizaje con procedencia + revalidación."""
import sqlite3, json, uuid
from datetime import datetime
from pathlib import Path


class Agua:
    def __init__(self, db_path: str = ".rxre/agua.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS agua_lecciones (
                    leccion_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    procedencia TEXT NOT NULL,
                    condiciones TEXT,
                    revalidada_en TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def guardar(self, topic, contenido, procedencia, condiciones=None):
        lid = f"lec-{uuid.uuid4().hex[:12]}"
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO agua_lecciones (leccion_id, topic, contenido, procedencia, condiciones, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (lid, topic, contenido, procedencia, json.dumps(condiciones or {}), datetime.utcnow().isoformat())
            )
        return lid

    def recuperar(self, topic, revalidar=True):
        with sqlite3.connect(self.db_path) as c:
            rows = c.execute(
                "SELECT * FROM agua_lecciones WHERE topic=? ORDER BY created_at DESC", (topic,)
            ).fetchall()
        cols = ["leccion_id", "topic", "contenido", "procedencia", "condiciones", "revalidada_en", "created_at"]
        lecciones = [dict(zip(cols, r)) for r in rows]
        if revalidar:
            for l in lecciones:
                l["revalidada"] = self._fue_revalidada_recientemente(l)
        return lecciones

    def revalidar(self, leccion_id):
        with sqlite3.connect(self.db_path) as c:
            cur = c.execute(
                "UPDATE agua_lecciones SET revalidada_en=? WHERE leccion_id=?",
                (datetime.utcnow().isoformat(), leccion_id)
            )
            return cur.rowcount == 1

    def _fue_revalidada_recientemente(self, leccion, dias=30):
        if not leccion.get("revalidada_en"):
            return False
        from datetime import datetime
        delta = datetime.utcnow() - datetime.fromisoformat(leccion["revalidada_en"])
        return delta.days <= dias
