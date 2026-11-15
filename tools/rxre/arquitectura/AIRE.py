"""AIRE — capa transversal que observa."""
import hashlib, json
from datetime import datetime

_TRAZAS: dict[str, dict] = {}

def emitir_traza(decision: str, herramienta: dict, resultado: dict) -> str:
    if not (decision and herramienta and resultado):
        raise ValueError("tramos incompletos: decisión/herramienta/resultado requeridos")
    h = hashlib.sha256(
        f"{decision}{herramienta.get('name')}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]
    _TRAZAS[h] = {
        "decision": decision,
        "herramienta": herramienta,
        "resultado": resultado,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return h

def reconstruir_traza(traza_id: str) -> dict:
    if traza_id not in _TRAZAS:
        raise KeyError(f"traza {traza_id} no existe")
    t = _TRAZAS[traza_id]
    if not all(k in t for k in ("decision", "herramienta", "resultado")):
        raise ValueError("traza incompleta: falta algún tramo")
    return t

def tool_hash(herramienta: dict) -> str:
    payload = json.dumps(
        {"name": herramienta["name"], "version": herramienta.get("version", "")},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class Traza:
    def __init__(self):
        self.decisions = {}
        self.invocations = {}
        self.results = {}
        self._counts = {"decisiones": 0, "invocaciones": 0, "resultados": 0, "rotos": 0}

    def decidir(self, decision: str, detalle: str = "") -> dict:
        did = "d_" + hashlib.sha256(f"{decision}{detalle}".encode()).hexdigest()[:8]
        self.decisions[did] = {"decision": decision, "detalle": detalle}
        self._counts["decisiones"] += 1
        return {"id": did, "decision": decision}

    def invocar(self, d: dict, tool_name: str, version: str, tool_hash_str: str = "") -> dict:
        if not tool_hash_str:
            raise ValueError("tool_hash vacío: hueco de atribución")
        iid = "i_" + hashlib.sha256(f"{d['id']}{tool_name}{version}".encode()).hexdigest()[:8]
        self.invocations[iid] = {
            "decision_id": d["id"], "tool": tool_name, "version": version,
            "tool_hash": tool_hash_str
        }
        self._counts["invocaciones"] += 1
        return {"id": iid}

    def producir(self, i: dict, resultados: list) -> None:
        rid = "r_" + hashlib.sha256(str(i["id"]).encode()).hexdigest()[:8]
        self.results[rid] = {"invocacion_id": i["id"], "resultados": resultados}
        self._counts["resultados"] += 1

    def alcance(self) -> dict:
        return {
            "decisiones": self._counts["decisiones"],
            "invocaciones": self._counts["invocaciones"],
            "resultados": self._counts["resultados"],
            "rotos": self._counts["rotos"],
        }
