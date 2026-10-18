"""ALMA: propósito y criterios de cierre."""
import sqlite3, uuid, json
from datetime import datetime
from pathlib import Path


class Alma:
    def __init__(self, db_path: str = ".rxre/alma.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS alma_propositos (
                    proposito_id TEXT PRIMARY KEY,
                    descripcion TEXT NOT NULL,
                    objetivo TEXT NOT NULL,
                    criterios TEXT NOT NULL DEFAULT '[]',
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL
                )
            """)

    def definir(self, descripcion: str, objetivo: str,
                criterios: list) -> str:
        aid = f"prop-{uuid.uuid4().hex[:12]}"
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO alma_propositos (proposito_id, descripcion, objetivo, criterios, creado_en) VALUES (?, ?, ?, ?, ?)",
                (aid, descripcion, objetivo,
                 json.dumps(criterios or []), datetime.utcnow().isoformat())
            )
        return aid

    def evaluar_criterio(self, proposito_id: str, criterio_id: str,
                         estado: dict) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute(
                "SELECT criterios FROM alma_propositos WHERE proposito_id=?",
                (proposito_id,) ).fetchone()
        if not row: raise ValueError(f"propósito no existe: {proposito_id}")
        criterios = json.loads(row[0] if row[0] else "[]")
        for crit in criterios:
            if crit.get("id") == criterio_id:
                campo = crit.get("campo") or crit.get("evaluable")
                if campo and campo in estado:
                    return {"ok": True, "evaluable": True,
                            "valor": estado[campo]}
                return {"ok": False, "evaluable": False,
                        "razon": f"campo '{campo}' no presente"}
        raise ValueError(f"criterio no existe: {criterio_id}")

    def puede_cerrar(self, proposito_id: str, estado: dict) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute(
                "SELECT criterios FROM alma_propositos WHERE proposito_id=?",
                (proposito_id,) ).fetchone()
        if not row: raise ValueError(f"propósito no existe: {proposito_id}")
        criterios = json.loads(row[0] if row[0] else "[]")
        resultados = []
        todos_ok = True
        for crit in criterios:
            try:
                r = self.evaluar_criterio(proposito_id, crit.get("id"), estado)
                resultados.append({"criterio": crit.get("id"), **r})
                if not r.get("ok"):
                    todos_ok = False
            except Exception as exc:
                resultados.append({"criterio": crit.get("id"), "ok": False,
                                   "razon": str(exc)})
                todos_ok = False
        return {"puede_cerrar": todos_ok, "resultados": resultados}

    def proposito(self) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute(
                "SELECT * FROM alma_propositos WHERE activo=1 ORDER BY creado_en DESC LIMIT 1"
            ).fetchone()
            if not row: return None
            cursor = c.execute("SELECT * FROM alma_propositos WHERE activo=1 ORDER BY creado_en DESC LIMIT 1")
            # Note: we already fetched; retrieve column info from PRAGMA as fallback or rerun
            # For simplicity, hardcode columns used in this module
            d = {
                "proposito_id": row[0],
                "descripcion": row[1],
                "objetivo": row[2],
                "criterios": json.loads(row[3] if row[3] else "[]"),
                "activo": row[4],
                "creado_en": row[5],
            }
            return d
