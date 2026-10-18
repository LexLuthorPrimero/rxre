"""CUERPO: observación y medición de artefactos."""
import hashlib, sqlite3, uuid
from datetime import datetime
from pathlib import Path


class Cuerpo:
    def __init__(self, db_path: str = ".rxre/cuerpo.sqlite3"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS cuerpo_observaciones (
                    obs_id TEXT PRIMARY KEY,
                    artifact_path TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    size_bytes INTEGER,
                    mtime TEXT,
                    media_type TEXT,
                    observado_en TEXT NOT NULL
                )
            """)

    def observar(self, artifact_path: str) -> dict:
        p = Path(artifact_path)
        if not p.exists():
            raise FileNotFoundError(f"artefacto no existe: {artifact_path}")
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        stat = p.stat()
        media = self._media_type(p)
        obs_id = f"obs-{uuid.uuid4().hex[:12]}"
        ahora = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO cuerpo_observaciones (obs_id, artifact_path, artifact_hash, size_bytes, mtime, media_type, observado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (obs_id, str(p.absolute()), sha, stat.st_size,
                 datetime.fromtimestamp(stat.st_mtime).isoformat(), media, ahora)
            )
        return {"obs_id": obs_id, "artifact_path": str(p.absolute()),
                "artifact_hash": sha, "size_bytes": stat.st_size,
                "media_type": media}

    def recuperar(self, obs_id: str) -> dict:
        with sqlite3.connect(self.db_path) as c:
            cursor = c.execute("SELECT * FROM cuerpo_observaciones WHERE obs_id=?", (obs_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def verificar_no_alterado(self, obs_id: str) -> bool:
        obs = self.recuperar(obs_id)
        if not obs:
            raise ValueError("observación no encontrada")
        actual = hashlib.sha256(Path(obs["artifact_path"]).read_bytes()).hexdigest()
        return actual == obs["artifact_hash"]

    def _media_type(self, p: Path) -> str:
        ext = p.suffix.lower()
        mapa = {".bin": "application/octet-stream",
                ".elf": "application/x-elf",
                ".ko": "application/x-object",
                ".c": "text/x-c", ".h": "text/x-c",
                ".py": "text/x-python", ".md": "text/markdown"}
        return mapa.get(ext, "application/octet-stream")
