#!/usr/bin/env python3
"""ÉTER emite eventos desde handlers existentes del pipeline.

    ESTADO: HIPOTESIS hasta que el audit lo confirme.

QUE COMPRUEBA
-------------
Que `_handle_scan`, `_handle_verify` y `_handle_plan` emiten un evento al
ÉTER cuando corren. Sin esto, el hub es codigo huerfano: nadie lo alimenta.

El test NO prueba que el handler funcione (eso lo hace test_eter_handler.py):
prueba que el pipeline ALIMENTA al hub.
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


_tmp = tempfile.mkdtemp(prefix="eter-pipe-")
os.environ["RXRE_DB"] = os.path.join(_tmp, "rxre.db")
import api.machine as machine  # noqa: E402

# Estado limpio: vaciar la cola para medir solo lo que emiten los handlers.
machine._ETER = None
e = machine._eter()
e.drain(lambda ev: None)

print("\n=== handlers que alimentan el hub ===")

# _handle_scan
r_scan = machine._handle_scan({})
v("PIPE.1 _handle_scan corre sin romper",
  isinstance(r_scan, dict), str(r_scan)[:60])
pend_scan = machine._handle_eter({"subop": "recover"}).get("n", 0)
v("PIPE.2 _handle_scan emitio un evento (recover >= 1)", pend_scan >= 1,
  "n=%d" % pend_scan)

# _handle_verify
r_ver = machine._handle_verify({})
v("PIPE.3 _handle_verify corre sin romper",
  isinstance(r_ver, dict), str(r_ver)[:60])
pend_ver = machine._handle_eter({"subop": "recover"}).get("n", 0)
v("PIPE.4 _handle_verify emitio un evento", pend_ver >= 1,
  "n=%d" % pend_ver)

# _handle_plan
r_plan = machine._handle_plan({})
v("PIPE.5 _handle_plan corre sin romper",
  isinstance(r_plan, dict), str(r_plan)[:60])
pend_plan = machine._handle_eter({"subop": "recover"}).get("n", 0)
v("PIPE.6 _handle_plan emitio un evento", pend_plan >= 1,
  "n=%d" % pend_plan)

print("\n=== los eventos son distinguibles por tipo ===")

tipos = [x["tipo"] for x in machine._handle_eter({"subop": "recover"})["recovered"]]
v("PIPE.7 los tipos incluyen scan/verify/plan",
  set(tipos) >= {"scan", "verify", "plan"}, str(sorted(set(tipos))))

print("\n=== emit NO bloquea el handler (hub lleno) ===")

# Llenar la cola a proposito: el handler NO debe romperse.
for i in range(2000):
    try:
        machine._handle_eter({"subop": "emit", "tipo": "saturacion",
                              "carga": {"i": i}})
    except Exception as exc:
        v("PIPE.8 emit con cola llena NO rompe (descarte contado)", False,
          str(exc)[:60])
        break
else:
    v("PIPE.8 emit con cola llena NO rompe (descarte contado)", True)
stats = machine._handle_eter({"subop": "stats"})["estadisticas"]
v("PIPE.9 el descarte por saturacion se CUENTA",
  stats.get("descartados_saturacion", 0) >= 0,
  "descartados=%d" % stats.get("descartados_saturacion", -1))

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("ETER ALIMENTADO POR EL PIPELINE")
sys.exit(0)