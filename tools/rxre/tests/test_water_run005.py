#!/usr/bin/env python3
"""RXRE-CORE-CAUSAL-002 / WATER-through-run.

Prueba que la leccion ahora viaja hasta la ruta de ejecucion (op:run), con
control. No altera argv: la IA decide si sigue la estrategia.
"""
import json, os, sys, tempfile
REPO = "/home/lucas/Escritorio/rxre"
PKG = os.path.join(REPO, "tools"); RXRE = os.path.join(PKG, "rxre")
for p in (PKG, RXRE):
    if p not in sys.path: sys.path.insert(0, p)
import subprocess
from core import store as S

DB = tempfile.mktemp(suffix=".sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []

def v(d, cond, det=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + d + ((" -> " + str(det)[:150]) if det else ""))

c = S.conectar(DB)
S.crear_mision(c, "t", "x")
S.registrar_reflexion(c, hypothesis_id="h", attempt_id=None,
    feedback="binary.inspect devolvio un archivo con 0 secciones",
    reflection="el artefacto no era ELF; se paso sin chequear",
    outcome="failure",
    strategy="antes de inspeccionar, leer el magico y abortar si no es ELF",
    check_ejecutable="test_fase5_trace.py", target="binary.inspect",
    capability="binary.inspect")
c.commit(); c.close()

def run(cap):
    r = subprocess.run([sys.executable, "-B", os.path.join(RXRE, "api", "machine.py")],
        input=json.dumps({"op": "run", "capability": cap, "artefacto": "/bin/ls",
                          "db_path": DB}) + "\n",
        capture_output=True, text=True, timeout=180, env=env)
    return json.loads(r.stdout.strip().splitlines()[0])

print("=== op:run sobre binary.inspect (tiene la leccion) ===")
d1 = run("binary.inspect")
lec = d1.get("lecciones_previas") or []
v("expone lecciones_previas", "lecciones_previas" in d1, "%d" % len(lec))
v("hay una estrategia concreta", len(lec) == 1 and bool(lec[0]["strategy"]),
  (lec[0]["strategy"][:40] if lec else ""))
v("la estrategia nombra el remedio concreto",
  ("abortar" in (lec[0]["strategy"] if lec else "") or "ELF" in (lec[0]["strategy"] if lec else "")))

print("\n=== op:run sobre binary.strings (SIN leccion: control) ===")
d2 = run("binary.strings")
lec2 = d2.get("lecciones_previas") or []
v("control: lista vacia", lec2 == [], "capability sin historial de fallo")

print("\n=== el argv NO cambio (la leccion no altera el comando) ===")
v("no hay argv injectado en la respuesta",
  "argv" not in d1 and "command_override" not in d1)

print("\n=== LIMITACIONES MEDIDAS ===")
for l in ["No prueba que el agente SIGA la estrategia; solo que la recibe.",
          "No prueba que seguirla evite el fallo; falta el experimento comparativo.",
          "La leccion se registra a mano aqui; en produccion viene de un fallo real."]:
    print("  - " + l)

print()
print("  %d/%d" % (sum(1 for x in ok if x), len(ok)))
if os.path.exists(DB): os.unlink(DB)
sys.exit(0 if all(ok) else 1)
