#!/usr/bin/env python3
"""E5: crash test para ÉTER — durabilidad bajo SIGKILL.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
Que un evento confirmado por `emit()` sobrevive a un SIGKILL del proceso
emisor. Si sobrevive, el fsync (via PRAGMA synchronous=FULL) es real y E5
pasa a VERIFIED. Si no sobrevive, el fsync es cosmético y hay que agregar
os.fsync() explícito.

CONTRASTE
---------
Antes: nadie probó durabilidad bajo crash.
Después: test mata el proceso con SIGKILL y verifica que el evento sigue en
disco.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
DB = None
SCRIPT = None


def setup(tmp_path):
    global DB, SCRIPT
    DB = tmp_path / "eter.db"
    SCRIPT = tmp_path / "emit.py"
    SCRIPT.write_text(f"""
import os, signal, sys
sys.path.insert(0, '{PKG}')
from core.eter import Eter
e = Eter('{DB}')
eid = e.emit("test", {{"id": "evt-001"}})
# Confirmar que se encoló (no solo que se intentó)
assert eid.startswith("evt_"), eid
# Morir SIN cleanup: el OS debe garantizar que lo fsync-eado sobrevive
os.kill(os.getpid(), signal.SIGKILL)
""")
    return DB, SCRIPT


def test_evento_confirmado_sobrevive_sigkill(tmp_path):
    """E5: si emit() confirmó, el evento está en disco tras SIGKILL."""
    db, script = setup(tmp_path)

    # Ejecutar subproceso; debe morir por SIGKILL (returncode -9)
    r = subprocess.run([__import__("sys").executable, str(script)])
    assert r.returncode == -9, (
        "el proceso no murió por SIGKILL (rc=%d). Si rc=0, el script "
        "terminó antes de matarse." % r.returncode)

    # Al reabrir, el evento confirmado debe estar en el journal
    import sys; sys.path.insert(0, '/home/lucas/Escritorio/rxre/tools/rxre'); from core.eter import Eter
    e = Eter(db)
    eventos = e.recover()
    ids = [ev.event_id for ev in eventos]
    # El event_id se deriva del contenido; verificar que hay al menos 1
    assert len(eventos) >= 1, (
        "evento confirmado se perdió tras SIGKILL. fsync no garantiza "
        "durabilidad. Se necesita os.fsync() explícito.")
    # Verificar que el evento tiene el contenido correcto
    assert any(ev.carga.get("id") == "evt-001" for ev in eventos), (
        "el evento sobrevivió pero con contenido distinto: %s" % ids)


def test_evento_sin_confirmar_no_esta_marcado_confirmed(tmp_path):
    """Un evento que no se encoló no debe aparecer como confirmado."""
    db = tmp_path / "eter2.db"
    # Crear BD vacía (sin emitir nada)
    import sys; sys.path.insert(0, '/home/lucas/Escritorio/rxre/tools/rxre'); from core.eter import Eter
    e = Eter(db)
    e.cerrar()
    # Reabrir: no debe haber eventos confirmados
    e2 = Eter(db)
    eventos = e2.recover()
    assert len(eventos) == 0, (
        "hay %d eventos en una BD que nunca emitió nada" % len(eventos))
    e2.cerrar()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])