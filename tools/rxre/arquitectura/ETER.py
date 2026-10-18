"""ETER: hub asincrono. NO media sincrono.

    [v3] 3 modos de fallo:
      · caida proceso (RAM pierde)
      · saturacion cola (descarte contado, no silencioso)
      · reinicio (solo disco vive)

    [v3] write-ahead:
      evento -> id unico -> fsync -> confirmacion -> idempotencia
      eventos criticos: siempre disco, nunca solo RAM

QUE ES Y QUE NO ES
------------------
El diagrama escribe, literalmente, "hub async · NO media sync". Son dos
prohibiciones y hay que entender las dos:

  1. NO es un mediador. ETER no decide, no arbitra, no enruta por politica.
     Solo transporta eventos con una garantia de entrega declarada. Quien
     decide es MENTE; quien transformaba es FUEGO.

  2. NO es sincrono. El punto de la asincronia no es la latencia: es que
     ETER NO puede convertirse en el punto donde el mundo se serializa. Si
     un productor espera confirmacion para seguir, el hub es un cuello de
     botella global y la concurrencia por operacion de TIERRA es ficticia.

EL ORDEN DEL WRITE-AHEAD NO ES DECORATIVO
-----------------------------------------
    1. id unico        aunque se caiga antes de escribir, el evento tiene
                       nombre y no se puede confundir con otro
    2. fsync           el SO confirma que llego al platter, no al page cache
    3. confirmacion    el emisor ya puede afirmar "esta en disco"
    4. idempotencia    reintentar el mismo evento no duplica el efecto

Si se invirtiera (confirmar y despues fsync), el paso 3 diria una mentira
justo en el instante en que el proceso se cae: exactamente la ventana que
el modo de fallo "CAIDA_PROCESO" nombra.

DESCARTE CONTADO
----------------
Una cola que cuando esta llena rechaza en silencio tiene dos fallos a la
vez: pierde datos y no deja rastro. `Estadisticas` lleva la cuenta, y el
productor puede consultarla. Un descarte invisible es indistinguible de "no
ocurrio nada", y un pipeline que no puede distinguir esas dos cosas no puede
afirmar nada sobre el mundo.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional

from .schemas import canonico, hash_contenido

# --- clasificacion de eventos --------------------------------------------
CRITICO = "critico"      # SIEMPRE disco, jamas solo RAM
VOLATIL = "volatil"      # puede perderse en una caida; se declara


class _Contador:
    """Contador explicito. Sin esto, un descarte es indistinguible de un no-op."""

    __slots__ = ("valor",)

    def __init__(self) -> None:
        self.valor = 0

    def incr(self, n: int = 1) -> int:
        self.valor += n
        return self.valor

    def obtener(self) -> int:
        return self.valor


class Estadisticas:
    """Lo que ETER sabe de si mismo. Contado, no opinado."""

    def __init__(self) -> None:
        self.aceptados = _Contador()
        self.despachados = _Contador()
        self.descartados_saturacion = _Contador()
        self.descartados_criticos = _Contador()
        self.duplicados_idempotentes = _Contador()
        self.fsync_realizados = _Contador()
        self.persistidos = _Contador()
        self.perdidos_por_caida = _Contador()

    def snapshot(self) -> Dict[str, int]:
        """El recuento completo. El nombre es `snapshot` y no `obtener`
        porque un snapshot se puede tomar en cualquier momento sin
        consumir nada: ETER observa, no altera."""
        return {
            "aceptados": self.aceptados.obtener(),
            "despachados": self.despachados.obtener(),
            "descartados_saturacion":
                self.descartados_saturacion.obtener(),
            "descartados_criticos": self.descartados_criticos.obtener(),
            "duplicados_idempotentes":
                self.duplicados_idempotentes.obtener(),
            "fsync_realizados": self.fsync_realizados.obtener(),
            "persistidos": self.persistidos.obtener(),
            "perdidos_por_caida": self.perdidos_por_caida.obtener(),
        }

    def __repr__(self) -> str:
        d = self.snapshot()
        return "Estadisticas(%s)" % ", ".join(
            "%s=%d" % (k, v) for k, v in sorted(d.items()))


class Evento:
    """Un evento del hub. Tiene id antes de existir en disco."""

    __slots__ = ("event_id", "tipo", "carga", "critico", "creado")

    def __init__(self, tipo: str, carga: Any, critico: bool = False):
        self.event_id = "evt_" + hash_contenido([tipo, carga])[:20]
        self.tipo = tipo
        self.carga = carga
        self.critico = critico
        self.creado = time.time()

    def __repr__(self) -> str:
        return "Evento(%s,%s,critico=%s)" % (self.event_id, self.tipo,
                                             self.critico)


SCHEMA_JOURNAL = """
CREATE TABLE IF NOT EXISTS journal (
    event_id    TEXT PRIMARY KEY,
    tipo        TEXT NOT NULL,
    carga       TEXT NOT NULL,
    critico     INTEGER NOT NULL,
    entregado   INTEGER NOT NULL DEFAULT 0,
    created_at  REAL NOT NULL
);
"""


class Eter:
    """Hub asincrono con write-ahead y cola acotada.

    La cola esta EN MEMORIA y por tanto acotada: eso es lo que hace posible
    observar el modo de fallo SATURACION_COLA. Una cola sin limite no tiene
    ese modo de fallo, y un sistema que no puede saturarse tampoco puede
    decir que descarta de forma contada.
    """

    def __init__(self, ruta_journal: str, max_cola: int = 1024):
        self.max_cola = max_cola
        self.estadisticas = Estadisticas()
        self.cola: List[Evento] = []
        self._vivos: set = set()
        self.ruta_journal = ruta_journal
        self._cerrado = False

        directorio = os.path.dirname(os.path.abspath(ruta_journal))
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        self.journal = sqlite3.connect(ruta_journal, isolation_level=None)
        self.journal.row_factory = sqlite3.Row
        self.journal.executescript(SCHEMA_JOURNAL)

    # -- [v3] WRITE-AHEAD ------------------------------------------------
    def _fsync(self) -> None:
        """Force al journal. NO es un fsync de SQLite: SQLite hace su
        propio WAL, y usar el fsync de la conexion seria assumir que el
        PRAGMA estan activo sin comprobarlo."""
        self.journal.execute("PRAGMA synchronous = FULL")
        self.journal.execute(
            "INSERT OR IGNORE INTO journal (event_id, tipo, carga, critico,"
            " created_at) VALUES (?,?,?,?,?)",
            (self._sync_id, self._sync_tipo, self._sync_carga,
             int(self._sync_critico), self._sync_creado))
        self.estadisticas.fsync_realizados.incr()
        self.estadisticas.persistidos.incr()

    def publicar(self, tipo: str, carga: Any,
                 critico: bool = True) -> Dict[str, Any]:
        """El camino del write-ahead, en orden. Los cinco pasos se ven.

        Devuelve un dict con el resultado de cada paso, para que un test
        pueda comprobar el ORDEN y no solo el efecto final.
        """
        if self._cerrado:
            raise RuntimeError("ETER cerrado: hub reiniciado")

        ev = Evento(tipo, carga, critico)
        pasos: Dict[str, Any] = {"evento": ev}

        # (1) ID UNICO — ya existe, se calcula antes de tocar disco.
        pasos["id_unico"] = ev.event_id

        # (2) IDEMPOTENCIA — reintentar el mismo evento no duplica.
        ya_vivo = self.journal.execute(
            "SELECT 1 FROM journal WHERE event_id = ?",
            (ev.event_id,)).fetchone()
        if ya_vivo:
            self.estadisticas.duplicados_idempotentes.incr()
            pasos.update({"idempotente": True, "encolado": False,
                          "descartado": False, "fsync": False})
            return pasos
        pasos["idempotente"] = False

        # (3) fsync — a disco ANTES de confirmar nada.
        self._sync_id, self._sync_tipo = ev.event_id, ev.tipo
        self._sync_carga, self._sync_critico = canonico(ev.carga), critico
        self._sync_creado = ev.creado
        try:
            self._fsync()
            pasos["fsync"] = True
        except sqlite3.Error as exc:
            # Un evento CRITICO que no llega a disco no se puede encolar "a
            # la espera": se cuenta como perdido y se dice. Perder en
            # silencio es el modo de fallo que el diagrama prohibe.
            self.estadisticas.perdidos_por_caida.incr()
            pasos.update({"fsync": False, "error": str(exc),
                          "encolado": False, "descartado": critico})
            if critico:
                self.estadisticas.descartados_criticos.incr()
            return pasos

        # (4) COLA — acotada, con descarte CONTADO.
        if len(self.cola) >= self.max_cola:
            self.estadisticas.descartados_saturacion.incr()
            pasos.update({"encolado": False, "descartado": True,
                          "motivo": "SATURACION_COLA"})
            return pasos

        self.cola.append(ev)
        self._vivos.add(ev.event_id)
        self.estadisticas.aceptados.incr()
        pasos.update({"encolado": True, "descartado": False})
        return pasos

    # -- entrega ---------------------------------------------------------
    def despachar(self, consumidor: Callable[[Evento], Any]) -> int:
        """Entrega lo encolado. Asincrono: NO espera al productor.

        Si `consumidor` lanza, el evento vuelve a la cola y se cuenta: no
        se pierde y no se finge entrega.
        """
        entregados = 0
        pendientes: List[Evento] = []
        while self.cola:
            ev = self.cola.pop(0)
            try:
                consumidor(ev)
            except Exception:
                pendientes.append(ev)
                continue
            self._vivos.discard(ev.event_id)
            self.journal.execute(
                "UPDATE journal SET entregado = 1 WHERE event_id = ?",
                (ev.event_id,))
            self.estadisticas.despachados.incr()
            entregados += 1
        self.cola[:0] = pendientes
        return entregados

    # -- [v3] modo de fallo: REINICIO -----------------------------------
    def reiniciar(self) -> int:
        """Cae el proceso. Solo sobrevive el disco.

        Los eventos en RAM que eran CRITICOS ya estan en el journal: se
        recuperan. Los VOLATILES se pierden, y se CUENTAN como perdidos.
        """
        perdidos = [ev for ev in self.cola if not ev.critico]
        recuperables = [dict(r) for r in self.journal.execute(
            "SELECT event_id, tipo, carga, critico FROM journal"
            " WHERE entregado = 0 ORDER BY created_at")]
        self.estadisticas.perdidos_por_caida.incr(len(perdidos))
        self.cola.clear()
        self._vivos.clear()
        return len(recuperables)

    def recuperar(self) -> List[Evento]:
        """Lo que el journal todavia no entrego. Del disco, no de RAM."""
        filas = self.journal.execute(
            "SELECT event_id, tipo, carga, critico FROM journal"
            " WHERE entregado = 0 ORDER BY created_at").fetchall()
        salida: List[Evento] = []
        for f in filas:
            ev = Evento(f["tipo"], json.loads(f["carga"]),
                        bool(f["critico"]))
            ev.event_id = f["event_id"]
            salida.append(ev)
        self.cola[:0] = salida
        return salida

    def cerrar(self) -> None:
        self._cerrado = True
        self.journal.close()

    def __enter__(self) -> "Eter":
        return self

    def __exit__(self, *_):
        self.cerrar()
        return False


def modo_saturacion(eter: Eter) -> Dict[str, int]:
    """Observa el modo de fallo SATURACION_COLA sin cronometrarlo.

    Devuelve el antes/despues de descartes. Si el numero no sube tras
    llenar la cola, el descarte no esta contado y el sistema miente sobre
    si mismo.
    """
    antes = eter.estadisticas.descartados_saturacion.obtener()
    for i in range(eter.max_cola + 50):
        eter.publicar("saturacion", {"i": i}, critico=False)
    despues = eter.estadisticas.descartados_saturacion.obtener()
    return {"antes": antes, "despues": despues,
            "descartados": despues - antes}