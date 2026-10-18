#!/usr/bin/env python3
"""ÉTER integrado en el pipeline de machine.py.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
Que `_handle_eter` existe, esta registrado en HANDLERS, y que sus
suboperaciones (emit/recover/drain/stats) se comportan como el contrato
del diagrama: hub async con write-ahead, 3 modos de fallo, idempotencia.

El punto que importa no es que el modulo exista (ya existe desde FASE 2):
es que el PIPELINE lo invoque. Sin handler, `core/eter.py` es codigo
huerfano con tests propios, igual que `core/fuego.py`.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


import api.machine as machine  # noqa: E402

# Aislar la BD de eventos: un temporal, no la de desarrollo.
_tmp = tempfile.mkdtemp(prefix="eter-int-")
os.environ["RXRE_DB"] = os.path.join(_tmp, "rxre.db")
machine._ETER = None

print("\n=== ETER handler registrado ===")

v("ETER.1 HANDLERS tiene la op 'eter'",
  "eter" in machine.HANDLERS)
v("ETER.2 la op apunta a _handle_eter",
  machine.HANDLERS.get("eter") is machine._handle_eter)

print("\n=== ETER emit ===")

r_emit = machine._handle_eter({"subop": "emit", "tipo": "test",
                               "carga": {"id": "evt-1"}})
v("ETER.3 emit devuelve status ok",
  r_emit.get("status") == "ok", str(r_emit)[:70])
eid = r_emit.get("event_id")
v("ETER.4 emit devuelve event_id", isinstance(eid, str) and eid.startswith("evt_"),
  str(eid))
v("ETER.5 el event_id es deterministico (mismo contenido -> mismo id)",
  machine._handle_eter({"subop": "emit", "tipo": "test",
                        "carga": {"id": "evt-1"}})["event_id"] == eid)

print("\n=== ETER idempotencia (v3) ===")

r_dup = machine._handle_eter({"subop": "emit", "tipo": "test",
                              "carga": {"id": "evt-1"}})
stats = machine._handle_eter({"subop": "stats"})["estadisticas"]
v("ETER.6 emit duplicado NO duplica (duplicados_idempotentes >= 1)",
  stats.get("duplicados_idempotentes", 0) >= 1,
  str(stats.get("duplicados_idempotentes")))
v("ETER.7 el descarte por saturacion se CUENTA (contador existe)",
  "descartados_saturacion" in stats, str(sorted(stats)))

print("\n=== ETER recover (modo de fallo REINICIO) ===")

r_rec = machine._handle_eter({"subop": "recover"})
v("ETER.8 recover devuelve los eventos pendientes",
  r_rec.get("status") == "ok" and r_rec.get("n") >= 1, str(r_rec)[:70])
v("ETER.9 recover no los marca como entregados (siguen pendientes)",
  machine._handle_eter({"subop": "recover"}).get("n") >= 1)

print("\n=== ETER drain ===")

r_drain = machine._handle_eter({"subop": "drain"})
v("ETER.10 drain entrega lo encolado",
  r_drain.get("status") == "ok" and r_drain.get("entregados") >= 0,
  str(r_drain)[:70])
v("ETER.11 tras drain, recover no encuentra pendientes",
  machine._handle_eter({"subop": "recover"}).get("n") == 0,
  str(machine._handle_eter({"subop": "recover"}))[:70])

print("\n=== ETER invalida entrada sin carga ===")

r_bad = machine._handle_eter({"subop": "emit", "tipo": "test"})
v("ETER.12 emit sin carga es invalid_input, no excepcion",
  r_bad.get("status") == "invalid_input", str(r_bad)[:70])

print("\n=== ETER subop desconocida ===")

r_unk = machine._handle_eter({"subop": "inventada"})
v("ETER.13 subop desconocida es invalid_input",
  r_unk.get("status") == "invalid_input", str(r_unk)[:70])

print("\n=== ETER no rompe los otros handlers ===")

r_back = machine._handle_backends({})
v("ETER.14 _handle_backends sigue funcionando",
  r_back.get("status") == "ok", str(r_back)[:70])
r_ops = machine._handle_ops({})
v("ETER.15 _handle_ops sigue funcionando",
  r_ops.get("status") == "ok" or "operaciones" in r_ops, str(r_ops)[:70])

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("ETER INTEGRADO EN EL PIPELINE")
sys.exit(0)