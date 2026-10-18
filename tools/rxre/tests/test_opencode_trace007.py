#!/usr/bin/env python3
"""RXRE-OPENCODE-TERMINAL-001 — prueba de traza causal integrada.

Demuestra, sobre datos en vivo y reproducibles, que el ciclo completo
OpenCode (decision) -> terminal -> RXRE (persistencia) -> consumo -> nueva
decision esta OBSERVABLE y CORRELACIONABLE. No requiere modificar OpenCode:
lee el registro durable de OpenCode (opencode.db.session_message) y lo
contrasta con rxre.sqlite3 mediante el result_id, que es la clave de union
estable entre ambos sistemas (el operation_id NO lo es; ver hallazgo).

Partes:
  A. terminal->RXRE (REPRODUCIBLE, DB temporal): invoke machine.py via
     subprocess, assert operation_id/result_id/exit persisenten en rxre.
  B. OpenCode decision observable (LIVE opencode.db): un turno assistant
     reciente contiene reasoning + tool(shell) con input.command, state.content
     y state.metadata.exit.
  C. correlacion cruzada (LIVE): un result_id aparece EN session_message.content
     (registro de OpenCode) Y en rxre.sqlite3.results (registro de RXRE).
"""
import json, os, sys, sqlite3, subprocess, tempfile, time
REPO="/home/lucas/Escritorio/rxre"
PKG=os.path.join(REPO,"tools"); RXRE=os.path.join(PKG,"rxre")
for p in (PKG,RXRE):
    if p not in sys.path: sys.path.insert(0,p)
OCDB="/home/lucas/.local/share/opencode/opencode.db"
LIVE_RXRE=os.path.join(RXRE,"storage","rxre.sqlite3")
SID="ses_edaa301eeffenFHFHeLvSlWupx"  # sesion actual
ok=[]
def v(d,cond,det=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ")+d+(" -> "+str(det)[:120] if det else ""))
def ctt(c):
    if isinstance(c,str): return c
    if isinstance(c,dict): return c.get("text","") if isinstance(c.get("text"),str) else json.dumps(c)
    if isinstance(c,list): return "\n".join(ctt(x) for x in c)
    return str(c)

# ---- PARTE A: terminal->RXRE reproducible con DB temporal ----
print("=== PARTE A: terminal -> RXRE (subprocess, DB temporal) ===")
DB=tempfile.mktemp(suffix=".sqlite3")
env={**os.environ,"PYTHONPATH":PKG+":"+RXRE,"RXRE_DB":DB}
resp_bytes=(b'{"op":"run","capability":"binary.inspect","artefacto":"/bin/ls","db_path":"'+DB.encode()+b'"}\n')
r=subprocess.run([sys.executable,"-B",os.path.join(RXRE,"api","machine.py")],
                 input=resp_bytes,capture_output=True,timeout=90,env=env)
try: resp=json.loads(r.stdout.strip().splitlines()[0])
except Exception:
    v("machine.py responde JSON", False, r.stdout[:120]+r.stderr[:80]); sys.exit(1)
v("machine.py ejecuta (terminal invocation)", resp.get("status")=="ok", resp.get("status"))
v("persistido en RXRE", resp.get("persistido") is True, resp.get("persistido"))
rid=resp.get("results",[{}])[0].get("result_id") if resp.get("results") else None
v("result_id devuelto", bool(rid), rid)
v("backend_rc=0 (exit capture)", resp.get("backend_rc")==0, resp.get("backend_rc"))
# ahora leer la DB temporal desde un PROCESO DISTINTO (open cursor nuevo)
rx=sqlite3.connect(DB); rx.row_factory=sqlite3.Row
ro=rx.execute("SELECT result_id,operation_id,type,tool,status,source FROM results WHERE result_id=?",(rid,)).fetchone()
v("result persistido en DB temporal (cross-process read)", bool(ro), ro and ro["tool"])
if ro:
    op=rx.execute("SELECT operation_id,capability,status FROM operations WHERE operation_id=?",(ro["operation_id"],)).fetchone()
    v("operation vinculada", bool(op) and op["capability"]=="binary.inspect", op and op["capability"])
    ev=rx.execute("SELECT evento_id,exit_status,persistido FROM execution_events WHERE result_id=?",(rid,)).fetchone()
    v("execution_events durable", bool(ev) and ev["persistido"]==1 and ev["exit_status"]==0, ev and (ev["persistido"],ev["exit_status"]))
rx.close()
if os.path.exists(DB): os.unlink(DB)

# ---- PARTE B: decision de OpenCode observable en session_message ----
print("\n=== PARTE B: decision de OpenCode observable (session_message) ===")
if not os.path.exists(OCDB):
    v("opencode.db accesible", False, "no existe "+OCDB); sys.exit(1)
oc=sqlite3.connect(OCDB); oc.row_factory=sqlite3.Row
rows=oc.execute("SELECT seq,type,data,time_created FROM session_message WHERE session_id=? AND type='assistant' ORDER BY seq DESC",(SID,)).fetchall()
v("session_message tiene assistant msgs", len(rows)>0, len(rows))
seen_reasoning=False; seen_tool_with_io=False; seen_exit=False
for m in rows:
    d=json.loads(m["data"]); content=d.get("content") or []
    order=[p.get("type") for p in content if isinstance(p,dict)]
    if "reasoning" in order: seen_reasoning=True
    for p in content:
        if not isinstance(p,dict) or p.get("type")!="tool": continue
        st=p.get("state") or {}
        if st.get("input"): seen_tool_with_io=True
        meta=st.get("metadata") or {}
        if "exit" in meta: seen_exit=True
    if seen_reasoning and seen_tool_with_io and seen_exit: break
v("CUERPO: reasoning (cadena de decision) registrado", seen_reasoning)
v("CUERPO: tool call con input.command registrado", seen_tool_with_io)
v("CUERPO: exit_status del shell registrado en metadata", seen_exit)
# orden causal: reasoning antes que tool en al menos un turno
order_ok=False
for m in rows:
    d=json.loads(m["data"]); content=d.get("content") or []
    order=[p.get("type") for p in content if isinstance(p,dict)]
    if "reasoning" in order and "tool" in order and order.index("reasoning")<order.index("tool"):
        order_ok=True; break
v("MENTE: razonamiento precede a la accion (decision->accion)", order_ok)
oc.close()

# ---- PARTE C: correlacion cruzada result_id (OpenCode content <-> RXRE results) ----
print("\n=== PARTE C: correlacion cruzada OpenCode <-> RXRE ===")
oc=sqlite3.connect(OCDB); oc.row_factory=sqlite3.Row
rx=sqlite3.connect(LIVE_RXRE); rx.row_factory=sqlite3.Row
# recoger result_ids que aparecen en contenidos de herramientas de la sesion actual
oc_rows=oc.execute("SELECT data FROM session_message WHERE session_id=? AND type='assistant'",(SID,)).fetchall()
oc_rids=set()
import re
pat=re.compile(r'res_[A-Za-z0-9_]+')
for m in oc_rows:
    d=json.loads(m["data"])
    for p in d.get("content",[]):
        if isinstance(p,dict) and p.get("type")=="tool":
            txt=ctt(p.get("state",{}).get("content"))
            oc_rids.update(x for x in pat.findall(txt) if x.startswith("res_"))
# result_ids en rxre.results (tablas operations/results/execution_events)
rx_rids=set(r[0] for r in rx.execute("SELECT result_id FROM results WHERE result_id IS NOT NULL"))
bridge=oc_rids & rx_rids
v("AIRE: result_id aparece en session_message.content (OpenCode)", len(oc_rids)>0, len(oc_rids))
v("AIRE: result_id aparece en rxre.results (RXRE)", len(rx_rids)>0, len(rx_rids))
v("AIRE: AL MENOS un result_id comun puente los dos sistemas", len(bridge)>0, len(bridge))
if bridge:
    b=sorted(bridge)[0]
    r=rx.execute("SELECT result_id,operation_id,type,tool FROM results WHERE result_id=?",(b,)).fetchone()
    v("AIRE: el result_id comun existe en results", bool(r), r and r["tool"])
    # contar cuantos result_ids comunes tambien tienen execution_event (event-log durable)
    ev_rids=set(x[0] for x in rx.execute("SELECT result_id FROM execution_events WHERE result_id IS NOT NULL"))
    bridge_ev=bridge & ev_rids
    v("AIRE: result_id comun tambien en execution_events (evento durable)", len(bridge_ev)>0, len(bridge_ev))
oc.close(); rx.close()
# HALLAZGO: operation_id NO es la clave estable
print("\n=== HALLAZGO: namespace de operation_id ===")
oc=sqlite3.connect(OCDB); oc.row_factory=sqlite3.Row
rx=sqlite3.connect(LIVE_RXRE); rx.row_factory=sqlite3.Row
# tomar un result_id comun donde AMBOS lados tengan operation_id y comparar
if bridge:
    rx_opid=None; oc_opid=None; found_b=None
    for b in bridge:
        r=rx.execute("SELECT operation_id FROM results WHERE result_id=?",(b,)).fetchone()
        if not r: continue
        rx_opid=r["operation_id"]
        for m in oc_rows:
            d=json.loads(m["data"])
            for p in d.get("content",[]):
                if isinstance(p,dict) and p.get("type")=="tool":
                    txt=ctt(p.get("state",{}).get("content"))
                    if b in txt:
                        mm=re.search(r'"operation_id"\s*:\s*"([^"]+)"', txt)
                        if mm:
                            oc_opid=mm.group(1); found_b=b; break
            if found_b: break
        if found_b: break
    print("  result_id de comparacion:", found_b)
    print("  rxre.operations.operation_id =", rx_opid)
    print("  opencodecontent response operation_id =", oc_opid)
    if found_b:
        e=rx.execute("SELECT operation_id FROM execution_events WHERE result_id=?",(found_b,)).fetchone()
        ev_oid=e["operation_id"] if e else None
    else:
        ev_oid=None
    print("  execution_events.operation_id =", ev_oid)
    print("  operations/results.operation_id =", rx_opid)
    v("HALLAZGO: operation_id en execution_events != operations (namespace no unificado; result_id es la clave estable)",
      bool(ev_oid) and bool(rx_opid) and ev_oid!=rx_opid,
      "ev=%s ops=%s"%(ev_oid,rx_opid))
oc.close(); rx.close()

print("\n  %d/%d"%(sum(1 for x in ok if x),len(ok)))
sys.exit(0 if all(ok) else 1)
