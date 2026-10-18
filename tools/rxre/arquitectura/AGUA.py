"""AGUA: aprendizaje con procedencia, y REVALIDACION al recuperar.

    DEL DIAGRAMA:
      AGUA  aprendizaje con procedencia
      [v3] revalidar al recuperar, no confiar solo en lo persistido

LA REGLA QUE NO SE PUEDE OMITIR
--------------------------------
"no confiar solo en lo persistido" significa que recuperar un aprendizaje
NO es devolver lo que se guardo. Significa que hay que volver a COMPROBAR
que sigue siendo cierto contra el mundo. Si el resultado fuera solo un
`return cache`, la revalidacion seria decorativa y la v3 estaria ausente.

Por eso `recuperar()` devuelve DOS cosas y por eso `revalidar()` puede
devolver NOT_DETERMINED: no es que el aprendizaje haya caducado, es que
ahora no se puede comprobar. Esa tercera respuesta es la que hace que el
sistema pueda decir "no lo sé" despues de haber dicho "lo sé", que es el
unico estado en el que un sistema que aprende sigue siendo honesto.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional

from . import DEFERRED, NOT_DETERMINED, PROVEN, PROVEN_ABSENT
from .schemas import canonico, hash_contenido


class Aprendizaje:
    __slots__ = ("id", "proposito", "procedencia", "regla", "reverificar",
                 "confianza")

    def __init__(self, proposito: str, procedencia: str, regla: str,
                 reverificar: Callable[[], bool], confianza: float = 0.5):
        self.id = "apr_" + hash_contenido([proposito, regla])[:16]
        self.proposito = proposito
        # PROCEDENCIA obligatoria: un aprendizaje sin de donde viene es
        # una opinion con almacenamiento.
        self.procedencia = procedencia
        self.regla = regla
        self.reverificar = reverificar
        self.confianza = confianza

    def __repr__(self) -> str:
        return "Aprendizaje(%s,%s)" % (self.id, self.proposito)


SCHEMA_APRENDIZAJE = """
CREATE TABLE IF NOT EXISTS aprendizajes (
    aprendizaje_id TEXT PRIMARY KEY,
    proposito      TEXT NOT NULL,
    procedencia    TEXT NOT NULL,
    regla          TEXT NOT NULL,
    confianza      REAL NOT NULL,
    verificado_en  REAL,
    verificado_ok  INTEGER,
    created_at     TEXT NOT NULL
);
"""


class Agua:
    def __init__(self, ruta: str):
        self.ruta = ruta
        directorio = os.path.dirname(os.path.abspath(ruta))
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        self.db = sqlite3.connect(ruta, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA_APRENDIZAJE)
        self.vivos: Dict[str, Aprendizaje] = {}
        self.revalidaciones = 0
        self.caidas = 0

    # -- aprender --------------------------------------------------------
    def aprender(self, a: Aprendizaje) -> str:
        """Guardar NO es afirmar que es cierto: es declarar que se va a
        comprobar. Por eso la fila nace con `verificado_ok` a NULL."""
        if not a.procedencia:
            raise ValueError(
                "aprendizaje sin procedencia: no se sabe de donde sale")
        self.vivos[a.id] = a
        self.db.execute(
            "INSERT OR REPLACE INTO aprendizajes (aprendizaje_id, proposito,"
            " procedencia, regla, confianza, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (a.id, a.proposito, a.procedencia, a.regla, a.confianza,
             time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        return a.id

    # -- [v3] revalidar al recuperar --------------------------------------
    def revalidar(self, aprendizaje_id: str) -> Dict[str, Any]:
        """VUELVE A COMPROBAR. No devuelve lo guardado: lo reevalua."""
        a = self.vivos.get(aprendizaje_id)
        if a is None:
            fila = self.db.execute(
                "SELECT * FROM aprendizajes WHERE aprendizaje_id = ?",
                (aprendizaje_id,)).fetchone()
            if fila is None:
                raise KeyError(aprendizaje_id)
            return {"id": aprendizaje_id, "estado": NOT_DETERMINED,
                    "motivo": "procedencia ausente en memoria: no se puede "
                              "revalidar, y eso NO es lo mismo que falso"}

        try:
            ok = bool(a.reverificar())
        except Exception as exc:                       # noqa: BLE001
            # Si la comprobacion falla, el estado honesto es "no lo se", no
            # "falso". Colapsar ambas cosas convierte un fallo de
            # infraestructura en una conclusion sobre el mundo.
            self.db.execute(
                "UPDATE aprendizajes SET verificado_en = ?, verificado_ok ="
                " NULL WHERE aprendizaje_id = ?", (time.time(), a.id))
            return {"id": a.id, "estado": NOT_DETERMINED,
                    "motivo": "la revalidacion lanzo: %s" % exc}

        self.revalidaciones += 1
        estado = PROVEN if ok else PROVEN_ABSENT
        self.db.execute(
            "UPDATE aprendizajes SET verificado_en = ?, verificado_ok = ?"
            " WHERE aprendizaje_id = ?",
            (time.time(), 1 if ok else 0, a.id))
        return {"id": a.id, "estado": estado,
                "revalidado": True,
                "confianza": a.confianza}

    def recuperar(self, aprendizaje_id: str) -> Dict[str, Any]:
        """Recuperar ES revalidar. Si `revalidar` devolviera lo persistido,
        este metodo no tendria sentido propio y seria el sitio donde la v3
        se pierde."""
        return self.revalidar(aprendizaje_id)

    # -- modo de fallo: reinicio ------------------------------------------
    def reiniciar(self) -> Dict[str, int]:
        """El proceso cae. La RAM de reglas se pierde.

        Lo que sobrevive en disco son las REGLAS y su PROCEDENCIA, no su
        verdad. Por eso lo recuperado vuelve como NOT_DETERMINED: un
        aprendizaje que no se puede revalidar no vuelve como PROVEN.
        """
        self.caidas += 1
        self.vivos.clear()
        return self.estadisticas()

    def estadisticas(self) -> Dict[str, int]:
        total = self.db.execute(
            "SELECT COUNT(*) FROM aprendizajes").fetchone()[0]
        verificados = self.db.execute(
            "SELECT COUNT(*) FROM aprendizajes WHERE verificado_ok = 1"
        ).fetchone()[0]
        refutados = self.db.execute(
            "SELECT COUNT(*) FROM aprendizajes WHERE verificado_ok = 0"
        ).fetchone()[0]
        return {"aprendizajes": total, "verificados": verificados,
                "refutados": refutados, "revalidaciones": self.revalidaciones,
                "caidas": self.caidas}

    def cerrar(self) -> None:
        self.db.close()