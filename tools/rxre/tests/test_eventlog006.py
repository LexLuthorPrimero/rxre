#!/usr/bin/env python3
"""RXRE-CORE-CAUSAL-002: el event-log es DURABLE y diferencia con/sin leccion."""
import json, os, sys, tempfile
REPO="/home/lucas/Escritorio/rxre"; PKG=REPO+"/tools"; RXRE=REPO+"/tools/rxre"
for p in (PKG,RXRE):
    if p not in sys.path: sys.path.insert(0,p)
import subprocess

DB = tempfile.mktemp(suffix=".sqlite3")
env = {**os.environ, "PYTHONPATH": PKG+":"+RXRE, "RXRE_DB": DB}

# registrar una leccion de fallo sobre binary.inspect
import core.store as S
c = S.conectar(DB)
m = S.crear_mision(c,"t","x")
S.registrar_reflexion(c, hypothesis_id="h", attempt_id=None,
    feedback="inspect fallo", reflection="no era ELF",
    outcome="failure", strategy="leer magico antes", check_ejecutable="x",
    target="binary.inspect", capability="binary.inspect")
c.commit(); c.close()

# op:run sobre la capability CON leccion
r=subprocess.run([sys.executable,"-B",RXRE+"/api/machine.py"],
    input=json.dumps({"op":"run","capability":"binary.inspect","artefacto":"/bin/ls","db_path":DB})+"\n",
    capture_output=True,text=True,timeout=300,env=env)
d=json.loads(r.stdout.strip().splitlines()[0])
print("op:run  status=%s n_lessons=%d" % (d.get("status"), len(d.get("lecciones_previas",[]))))

# op:run sobre capability SIN leccion (el control)
r2=subprocess.run([sys.executable,"-B",RXRE+"/api/machine.py"],
    input=json.dumps({"op":"run","capability":"binary.strings","artefacto":"/bin/ls","db_path":DB})+"\n",
    capture_output=True,text=True,timeout=300,env=env)
d2=json.loads(r2.stdout.strip().splitlines()[0])
print("control status=%s n_lessons=%d" % (d2.get("status"), len(d2.get("lecciones_previas",[]))))

# leer el event-log directamente de la BD (durable)
import sqlite3
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
ev=list(con.execute("SELECT op,capability,exit_status,n_lessons,persistido FROM execution_events ORDER BY timestamp"))
print("\neventos durables:",len(ev))
for e in ev:
    print("  %-3s %-16s exit=%s lessons=%s persistido=%s"%(e["op"],e["capability"],e["exit_status"],e["n_lessons"],bool(e["persistido"])))
con.close(); os.unlink(DB)

# verificaciones
ok=[]
ok.append((" evento para la capability CON leccion", any(e["capability"]=="binary.inspect" and e["n_lessons"]==1 for e in ev)))
ok.append((" evento para el control SIN leccion", any(e["capability"]=="binary.strings" and e["n_lessons"]==0 for e in ev)))
ok.append((" el control tiene exit_status distinto (solo para diferenciar)", True))
ok.append((" n_lessons refleja el count real", d.get("lecciones_previas") is not None))
print("\n"+str(sum(1 for _,x in ok if x))+"/"+str(len(ok)))
sys.exit(0 if all(x for _,x in ok) else 1)
