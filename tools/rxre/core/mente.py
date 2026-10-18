"""MENTE: razonamiento causal."""
import sqlite3, json, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

PASOS = ["EVIDENCE", "SEMANTICS", "SCHEMA",
         "DISCRIMINATING_TEST", "IMPLEMENTATION", "VALIDATION"]
INDICE = {p: i for i, p in enumerate(PASOS)}


@dataclass
class Hipotesis:
    id: str
    statement: str
    predicciones: list[str] = field(default_factory=list)
    falsificador: str = ""
    evidencia_refs: list[str] = field(default_factory=list)
    estado: str = "PROPUESTA"
    creada_en: str = ""


@dataclass
class Prueba:
    id: str
    hip_a: str
    hip_b: str
    procedimiento: str
    prediccion_a: str
    prediccion_b: str


class Mente:
    def __init__(self, db_path: str = ".rxre/mente.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS mente_hipotesis (
                    id TEXT PRIMARY KEY,
                    observacion TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    predicciones TEXT NOT NULL,
                    falsificador TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'PROPUESTA',
                    creada_en TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS mente_pruebas (
                    id TEXT PRIMARY KEY,
                    hip_a TEXT NOT NULL,
                    hip_b TEXT NOT NULL,
                    procedimiento TEXT NOT NULL,
                    prediccion_a TEXT NOT NULL,
                    prediccion_b TEXT NOT NULL,
                    resultado TEXT,
                    creada_en TEXT NOT NULL
                )
            """)

    def proponer_hipotesis(self, observacion: dict) -> list[Hipotesis]:
        fenomeno = observacion.get("fenomeno", "")
        plantilla_a = {
            "statement": f"El fenómeno '{fenomeno}' ocurre siempre.",
            "predicciones": [
                "Bajo cualquier condición controlable, el fenómeno se reproduce.",
                "No hay condición de borde que lo inhiba.",
            ],
            "falsificador": "Un caso reproducible donde el fenómeno NO ocurre.",
        }
        plantilla_b = {
            "statement": f"El fenómeno '{fenomeno}' ocurre solo bajo condiciones específicas.",
            "predicciones": [
                "Existe al menos una condición donde el fenómeno NO ocurre.",
                "Si se identifica esa condición, el fenómeno se puede inhibir.",
            ],
            "falsificador": "Un caso donde el fenómeno ocurre incluso fuera de la condición específica.",
        }
        return [
            self._guardar_hipotesis(observacion, plantilla_a),
            self._guardar_hipotesis(observacion, plantilla_b),
        ]

    def _guardar_hipotesis(self, obs: dict, plantilla: dict) -> Hipotesis:
        hid = f"hip-{uuid.uuid4().hex[:12]}"
        ahora = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO mente_hipotesis (id, observacion, statement, predicciones, falsificador, estado, creada_en) VALUES (?, ?, ?, ?, ?, 'PROPUESTA', ?)",
                (hid, json.dumps(obs), plantilla["statement"],
                 json.dumps(plantilla["predicciones"]), plantilla["falsificador"], ahora)
            )
        return Hipotesis(
            id=hid, statement=plantilla["statement"],
            predicciones=plantilla["predicciones"],
            falsificador=plantilla["falsificador"], creada_en=ahora)

    def disenar_prueba(self, hip_a_id: str, hip_b_id: str) -> Prueba:
        with sqlite3.connect(self.db_path) as c:
            a = c.execute("SELECT predicciones FROM mente_hipotesis WHERE id=?", (hip_a_id,)).fetchone()
            b = c.execute("SELECT predicciones FROM mente_hipotesis WHERE id=?", (hip_b_id,)).fetchone()
        if not a or not b:
            raise ValueError("hipótesis no encontrada")
        pred_a = json.loads(a[0])
        pred_b = json.loads(b[0])
        if pred_a == pred_b or (isinstance(pred_a, list) and isinstance(pred_b, list) and pred_a == pred_b):
            raise ValueError("Hipótesis no distinguibles: predicciones idénticas")
        proc = f"Verificar si: '{pred_a[0]}' vs '{pred_b[0]}'"
        pid = f"pr-{uuid.uuid4().hex[:12]}"
        ahora = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO mente_pruebas (id, hip_a, hip_b, procedimiento, prediccion_a, prediccion_b, creada_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, hip_a_id, hip_b_id, proc, pred_a[0], pred_b[0], ahora)
            )
        return Prueba(id=pid, hip_a=hip_a_id, hip_b=hip_b_id,
                      procedimiento=proc, prediccion_a=pred_a[0], prediccion_b=pred_b[0])

    def invocar_fuego(self, op: str, args: dict) -> dict:
        """M6: interfaz síncrona MENTE → FUEGO."""
        from rxre.api import machine
        return machine.procesar_linea(json.dumps({"op": f"fuego.{op}", **args}))

    def evaluar_prueba(self, prueba_id: str, resultado: dict) -> dict:
        observado = resultado.get("observado", "")
        with sqlite3.connect(self.db_path) as c:
            prueba = c.execute(
                "SELECT hip_a, hip_b, prediccion_a, prediccion_b FROM mente_pruebas WHERE id=?", (prueba_id,)
            ).fetchone()
            if not prueba:
                raise ValueError("prueba no encontrada")
            hip_a, hip_b, pred_a, pred_b = prueba
            if observado == pred_a:
                sobrevive, refutada = hip_a, hip_b
            elif observado == pred_b:
                sobrevive, refutada = hip_b, hip_a
            else:
                return {"ok": False, "razon": "resultado no discrimina"}
            c.execute("UPDATE mente_hipotesis SET estado='SOBREVIVE' WHERE id=?", (sobrevive,))
            c.execute("UPDATE mente_hipotesis SET estado='REFUTADA' WHERE id=?", (refutada,))
            c.execute("UPDATE mente_pruebas SET resultado=? WHERE id=?",
                      (json.dumps(resultado), prueba_id))
        return {"ok": True, "sobrevive": sobrevive, "refutada": refutada}
