"""PUERTA: estados del audit (CONTESTED / CHALLENGED / ACCEPTED)."""
import sqlite3, uuid, json
from datetime import datetime
from pathlib import Path

ESTADOS = ["DELIVERED", "CONTESTED", "CHALLENGED", "ACCEPTED"]
TRANSICIONES = {
    "DELIVERED": ["CONTESTED", "CHALLENGED"],
    "CHALLENGED": ["ACCEPTED", "CONTESTED"],
    "CONTESTED": ["CHALLENGED"],
    "ACCEPTED": [],
}


class Puerta:
    def __init__(self, db_path: str = ".rxre/puerta.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS puerta_estado (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    estado TEXT NOT NULL DEFAULT 'DELIVERED',
                    artefactos_integros INTEGER DEFAULT 0,
                    refutaciones_pendientes INTEGER DEFAULT 0,
                    revisor_independiente INTEGER DEFAULT 0,
                    autoridad_nombrada INTEGER DEFAULT 0,
                    actualizado_en TEXT
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS puerta_transiciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    desde TEXT NOT NULL,
                    hacia TEXT NOT NULL,
                    motivo TEXT,
                    evidencia_nueva TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            c.execute("INSERT OR IGNORE INTO puerta_estado (id, estado) VALUES (1, 'DELIVERED')")

    def estado(self) -> dict:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("SELECT * FROM puerta_estado WHERE id=1").fetchone()
            if not row: return {"estado":"DELIVERED","artefactos_integros":0,"refutaciones_pendientes":0,"revisor_independiente":0,"autoridad_nombrada":0}
            return {"estado": row[1], "artefactos_integros": bool(row[2]),
                    "refutaciones_pendientes": bool(row[3]),
                    "revisor_independiente": bool(row[4]),
                    "autoridad_nombrada": bool(row[5]),
                    "actualizado_en": row[6]}

    def marcar(self, campo: str, valor: bool):
        if campo not in ("artefactos_integros", "refutaciones_pendientes",
                        "revisor_independiente", "autoridad_nombrada"):
            raise ValueError(f"campo inválido: {campo}")
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                f"UPDATE puerta_estado SET {campo}=?, actualizado_en=? WHERE id=1",
                (1 if valor else 0, datetime.utcnow().isoformat()))

    def puede_aceptar(self) -> dict:
        e = self.estado()
        cond = {
            "artefactos_integros": bool(e["artefactos_integros"]),
            "refutaciones_pendientes_cero": not bool(e["refutaciones_pendientes"]),
            "revisor_independiente": bool(e["revisor_independiente"]),
            "autoridad_nombrada": bool(e["autoridad_nombrada"]),
        }
        return {"puede_aceptar": all(cond.values()), "condiciones": cond}

    def transicionar(self, hacia: str, motivo: str, evidencia_nueva: str = None) -> dict:
        actual = self.estado()["estado"]
        if hacia not in TRANSICIONES.get(actual, []):
            raise ValueError(f"transición inválida: {actual} → {hacia}")
        if actual == "CONTESTED" and hacia == "CHALLENGED" and (not evidencia_nueva):
            raise ValueError("CONTESTED→CHALLENGED requiere evidencia_nueva")
        if hacia == "ACCEPTED":
            if not self.puede_aceptar()["puede_aceptar"]:
                raise ValueError("ACCEPTED requiere 4 condiciones: " + str(self.puede_aceptar()["condiciones"]))
        with sqlite3.connect(self.db_path) as c:
            c.execute("UPDATE puerta_estado SET estado=?, actualizado_en=? WHERE id=1",
                      (hacia, datetime.utcnow().isoformat()))
            c.execute(
                "INSERT INTO puerta_transiciones (desde, hacia, motivo, evidencia_nueva, timestamp) VALUES (?, ?, ?, ?, ?)",
                (actual, hacia, motivo, evidencia_nueva, datetime.utcnow().isoformat()))
        return {"ok": True, "desde": actual, "hacia": hacia}

    def etapa1_bloqueada(self) -> bool:
        return self.estado()["estado"] != "ACCEPTED"
