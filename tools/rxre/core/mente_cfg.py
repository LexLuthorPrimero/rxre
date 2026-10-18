"""MENTE-3: CFG (control flow graph) con dispatcher."""
import sqlite3, json, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class MenteCFG:
    def __init__(self, db_path: str, dispatcher=None):
        self.db_path = db_path
        self.dispatcher = dispatcher
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS mente_cfg (
                    cfg_id TEXT PRIMARY KEY,
                    artifact_hash TEXT NOT NULL,
                    funcion TEXT NOT NULL,
                    bloques TEXT NOT NULL,
                    aristas TEXT NOT NULL,
                    entry_block TEXT,
                    exit_blocks TEXT,
                    creado_en TEXT NOT NULL
                )
            """)

    def construir(self, artifact_path: str, funcion: str, backend: str = None) -> dict:
        if not self.dispatcher:
            raise ValueError(
                "MENTE-3: requiere dispatcher (ROUTER) con backend de binarios. "
                "Sin él, construir() no es ejecutable.")
        res = self.dispatcher.resolve("binary.functions", backend)
        backend_usado = res.get("backend")
        # ADAPT: usar el backend resuelto para invocar análisis real
        # MÍNIMO: simular análisis con datos mínimos
        # Si hay backend real, reemplazar esta parte con llamada real
        resultado = {
            "artifact_path": artifact_path,
            "funcion": funcion,
            "backend": backend_usado,
            "bloques": ["B0", "B1", "B2", "B3"],
            "aristas": [["B0", "B1"], ["B1", "B2"], ["B2", "B3"], ["B0", "B3"]],
            "entry_block": "B0",
            "exit_blocks": ["B3"],
            "artifact_hash": f"hash-{uuid.uuid4().hex[:8]}"
        }
        cfg_id = f"cfg-{uuid.uuid4().hex[:12]}"
        ahora = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO mente_cfg (cfg_id, artifact_hash, funcion, bloques, aristas, entry_block, exit_blocks, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cfg_id, resultado["artifact_hash"], funcion,
                 json.dumps(resultado["bloques"]),
                 json.dumps(resultado["aristas"]),
                 resultado["entry_block"],
                 json.dumps(resultado["exit_blocks"]), ahora)
            )
        return self._leer(cfg_id)

    def _leer(self, cfg_id: str) -> dict:
        with sqlite3.connect(self.db_path) as c:
            cursor = c.execute("SELECT * FROM mente_cfg WHERE cfg_id=?", (cfg_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            d = dict(zip(cols, row))
            for k in ("bloques", "aristas", "exit_blocks"):
                d[k] = json.loads(d[k])
            return d

    def alcanzable(self, cfg_id: str, desde: str, hasta: str) -> bool:
        cfg = self._leer(cfg_id)
        if not cfg: raise ValueError("CFG no encontrado")
        visitados = set()
        cola = [desde]
        while cola:
            actual = cola.pop(0)
            if actual == hasta: return True
            if actual in visitados: continue
            visitados.add(actual)
            for (o, d) in cfg["aristas"]:
                if o == actual and d not in visitados:
                    cola.append(d)
        return False

    def caminos(self, cfg_id: str, desde: str, hasta: str, max_caminos: int = 10) -> list:
        cfg = self._leer(cfg_id)
        if not cfg: raise ValueError("CFG no encontrado")
        caminos = []
        def dfs(nodo, camino, visitados):
            if len(caminos) >= max_caminos: return
            if nodo == hasta:
                caminos.append(camino + [nodo])
                return
            for (o, d) in cfg["aristas"]:
                if o == nodo and d not in visitados:
                    dfs(d, camino + [nodo], visitados | {d})
        dfs(desde, [], {desde})
        return caminos
