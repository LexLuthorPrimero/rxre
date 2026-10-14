#!/usr/bin/env python3
"""RXRE-CAUSAL-EVOL-001: AETHER. Una frontera parada produce trabajo.

LO QUE NO SE COMPRUEBA
---------------------
No se comprueba que la funcion exista. Se comprueba que DISTINGA motivos de
estancamiento que necesitan salidas distintas, y que la salida tenga un
DISCRIMINANTE. Un modulo que devuelve "investiga mas" para todo es
indistinguible de uno que no hace nada, y es peor: parece trabajo.

LA DISTINCION IMPORTANTE
-----------------------
"parada" y "saturada" no son lo mismo. Saturada = el trabajo de ESA frontera
esta hecho. Parada = no se puede seguir por la via actual. Confundirlas
hace que un sistema autonomo marque por terminado lo que solo esta
esperando, y ahi se acaba el avance.
"""
import json, os, sys, tempfile, shutil

REPO = "/home/lucas/Escritorio/rxre"
for p in (os.path.join(REPO, "tools"), os.path.join(REPO, "tools", "rxre")):
    if p not in sys.path:
        sys.path.insert(0, p)
from core import store as S  # noqa: E402

d = tempfile.mkdtemp(prefix="aether_")
c = S.conectar(os.path.join(d, "a.sqlite3"))
ok = []


def v(et, cond, det=""):
    ok.append(cond)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", et,
                         (" -> " + str(det)[:150]) if det else ""))


print("=" * 74)
print("1) DISTINGUE los motivos de estancamiento")
print("=" * 74)

# (a) capability no ejecutable
S.registrar_investigacion(c, kind="frontier", status="OPEN",
                          text="x", target="gpu.no.existe.nada")
# (b) sin next_action
S.registrar_investigacion(c, kind="frontier", status="OPEN",
                          text="y", target="otro.sin.accion")
# (c) con plan escrito y ejecutado
S.registrar_investigacion(c, kind="frontier", status="OPEN",
                          text="z", target="binary.inspect")
S.registrar_investigacion(c, kind="next_action", status="OPEN",
                          text="medir X", target="binary.inspect")
# (d) completada con evidencia -> NO esta parada, esta HECHA
S.registrar_investigacion(c, kind="frontier", status="PROVEN",
                          text="w", target="binary.cfg")
r = S.evaluar_saturacion_frontier(c)
motivos = {e["target"]: e["motivo"] for e in r["frontier_evaluaciones"]}
for t, m in sorted(motivos.items()):
    print("   %-26s %s" % (t, m))
v("capability inexistente -> BLOQUEADA_POR_CAPACIDAD",
  motivos.get("gpu.no.existe.nada") == "BLOQUEADA_POR_CAPACIDAD")
v("sin next_action -> SIN_DISCRIMINANTE",
  motivos.get("otro.sin.accion") == "SIN_DISCRIMINANTE")
v("con plan escrito -> PLAN_SIN_EJECUCION",
  motivos.get("binary.inspect") == "PLAN_SIN_EJECUCION")
# MEDIDO 2026-10-14: al escribir este test se dio por hecho que un frontier
# PROVEN sin refs se registraba. NO se registra: `registrar_investigacion`
# lo rechaza con
#   "una claim PROVEN exige `refs`: al menos un result_id u operation_id
#    del que se deriva. §9: una conclusion que no se puede rastrear no es
#    PROVEN"
# Es decir: la garantia de EARTH ya impedia el caso, y la rama
# COMPLETADA_SIN_EVIDENCIA de `_motivo_saturacion` es DEFENSIVA, para filas
# que han podido entrar por otra via. Se comprueban las dos cosas por separado.
v("el store RECHAZA PROVEN sin evidencia (garantia previa de EARTH)",
  S.registrar_investigacion(c, kind="frontier", text="x", status="PROVEN",
                            target="binary.sin.refs").get("estado") == "blocked",
  "PROVEN exige refs")
v("el store RECHAZA refs que no existen",
  S.registrar_investigacion(c, kind="frontier", text="x", status="PROVEN",
                            target="binary.ref.fantasma",
                            refs=["res_no_existe"]).get("estado") == "blocked")

# Ahora una frontera PROVEN de verdad: necesita un result_id real. Se
# produce ejecutando algo, porque un id inventado seria el mismo error que
# el store acaba de impedir.
# MEDIDO: `dispatch.ejecutar()` NO persiste; la persistencia la hace
# `persistir()`, que el dispatch invoca desde la superficie publica. Con la
# llamada directa el result_id no existe en la base y el store lo rechaza
# como ref — correctamente. Se pasa por la superficie, que es ademas el
# camino real.
_rid = None
try:
    import subprocess as _sp
    import json as _js
    _env2 = {**os.environ,
             "PYTHONPATH": "%s:%s" % (os.path.join(REPO, "tools"),
                                      os.path.join(REPO, "tools", "rxre")),
             "RXRE_DB": os.path.join(d, "a.sqlite3")}
    _q = _sp.run([sys.executable,
                  os.path.join(REPO, "tools", "rxre", "api", "machine.py")],
                 input=_js.dumps({"op": "run", "capability": "binary.inspect",
                                  "artefacto": "/bin/ls"}) + chr(10),
                 capture_output=True, text=True, timeout=300, env=_env2)
    _rs = [_js.loads(x) for x in _q.stdout.strip().splitlines() if x.strip()]
    if _rs and (_rs[0].get("results") or []):
        _rid = _rs[0]["results"][0].get("result_id")
        print("   result_id persistido: %s (persistido=%s)"
              % (_rid, _rs[0].get("persistido")))
except Exception as _e:
    print("   (no se pudo ejecutar por la superficie: %s)" % _e)

if _rid:
    S.registrar_investigacion(c, kind="frontier", status="PROVEN",
                              text="completada con evidencia",
                              target="binary.imports", refs=[_rid])
    _r = S.evaluar_saturacion_frontier(c, target="binary.imports")
    _e = _r["frontier_evaluaciones"][0]
    print("   binary.imports -> %s  saturada=%s" % (_e["motivo"], _e["saturada"]))
    v("PROVEN con evidencia real -> COMPLETADA_CON_EVIDENCIA y saturada",
      _e["motivo"] == "COMPLETADA_CON_EVIDENCIA" and _e["saturada"] is True,
      _e["motivo"])
else:
    v("PROVEN con evidencia real -> COMPLETADA_CON_EVIDENCIA", False,
      "no se pudo obtener un result_id real; el test no lo simula")

# La rama defensiva: se comprueba insertando la fila por SQL, que es como
# podria existir en una base escrita por otra herramienta. Se dice que se
# hace asi, para que el test no parezca mas fuerte de lo que es.
c.execute("INSERT INTO research(id, kind, status, text, refs_json, target, "
          "timestamp) VALUES(9999,'frontier','PROVEN','fila defensiva','[]',"
          "'binary.symbols','2026-10-14')")
c.commit()
_rd = S.evaluar_saturacion_frontier(c, target="binary.symbols")
_ed = _rd["frontier_evaluaciones"][0]
print("   binary.symbols -> %s" % _ed["motivo"])
v("PROVEN con refs vacias (fila defensiva) NO cuenta como completada",
  _ed["motivo"] == "COMPLETADA_SIN_EVIDENCIA", _ed["motivo"])
v("y ofrece SOSTENER o REFUTAR, no 'ya esta hecho'",
  any(a["tipo"] in ("sostener", "refutar") for a in _ed["alternativas"]),
  [a["tipo"] for a in _ed["alternativas"]])

# Lo que esto tiene que SIGNIFICAR: una frontera cerrada no aparece en
# `siguiente` como trabajo por hacer. MEDIDO al escribirlo: la primera
# version de la asercion era una comprehension anidada que comprobaba una
# lista contra si misma, asi que podia dar verde con la frontera cerrada
# Follow-up still first. Se comprueba contra `siguiente`, que es donde se
# propone trabajo de verdad.
_rr = S.evaluar_saturacion_frontier(c)
_sat = {e["frontier_id"] for e in _rr["frontier_evaluaciones"] if e.get("saturada")}
_sig = (_rr.get("siguiente") or {}).get("frontier_id")
print("   saturadas: %s   siguiente: %s" % (sorted(_sat), _sig))
v("una frontera HECTA no se propone como trabajo pendiente",
  _sig not in _sat, "siguiente=%s saturadas=%s" % (_sig, sorted(_sat)))

print()
print("=" * 74)
print("2) COMPLETADA_SIN_EVIDENCIA no cuenta como trabajo hecho")
print("=" * 74)
S.registrar_investigacion(c, kind="frontier", status="PROVEN",
                          text="afirmacion sin respaldo", target="binary.symbols")
r2 = S.evaluar_saturacion_frontier(c, target="binary.symbols")
e = r2["frontier_evaluaciones"][0]
print("   motivo  : %s" % e["motivo"])
print("   porque  : %s" % e["porque"][:140])
print("   saturada: %s" % e["saturada"])
v("PROVEN sin refs NO es COMPLETADA_CON_EVIDENCIA",
  e["motivo"] == "COMPLETADA_SIN_EVIDENCIA", e["motivo"])
v("PROVEN sin refs tiene alternativa de SOSTENER o REFUTAR",
  any(a["tipo"] in ("sostener", "refutar") for a in e["alternativas"]),
  [a["tipo"] for a in e["alternativas"]])

print()
print("=" * 74)
print("3) TODA alternativa tiene DISCRIMINANTE")
print("=" * 74)
r3 = S.evaluar_saturacion_frontier(c)
todas = [a for e in r3["frontier_evaluaciones"] for a in e["alternativas"]]
v("se generaron alternativas", len(todas) > 0, "%d alternativas" % len(todas))
v("toda alternativa dice que estableceria",
  all(a["establece"] for a in todas))
v("toda alternativa dice COMO se distingue",
  all(a["discriminante"] for a in todas))
v("toda alternativa declara coste y reversibilidad",
  all(a["coste"] and a["reversible"] is not None for a in todas))
v("ninguna alternativa es 'investiga mas'",
  not any("investiga mas" in a["accion"].lower() for a in todas))
for a in todas[:3]:
    print("   [%s] %s" % (a["tipo"], a["accion"][:88]))
    print("      -> %s" % a["discriminante"][:88])

print()
print("=" * 74)
print("4) UNA FRONTERA PARADA NO TERMINA EL TRABAJO")
print("=" * 74)
v("se propone una alternativa siguiente", r3.get("siguiente") is not None)
if r3.get("siguiente"):
    sg = r3["siguiente"]
    print("   elegida: %s" % sg["alternativa_elegida"]["accion"][:100])
    print("   por que: %s" % sg["criterio"][:100])
    v("la eleccion va acompanada de su POR QUE", bool(sg.get("por_que")))

print()
print("=" * 74)
print("5) REABRIR: con evidencia nueva si, sin ella no")
print("=" * 74)
# MEDIDO: la seccion 1 ya demostro que el store RECHAZA PROVEN sin refs, asi
# que `binary.cfg` nunca llego a existir. Para reabrir hace falta una
# frontera CERRADA, y la que hay en esta base es la fila defensiva de
# `binary.symbols` (id 9999). Si la superficie publico produjo un ref real,
# esa frontera tambien sirve.
fid = None
if _rid:
    _cand = [e["frontier_id"] for e in
             S.evaluar_saturacion_frontier(c, target="binary.imports")
             ["frontier_evaluaciones"]]
    if _cand:
        fid = _cand[0]
if fid is None:
    fid = c.execute("SELECT id FROM research WHERE id=9999").fetchone()[0]
sin = S.reabrir_frontier(c, fid, "")
v("reabrir SIN evidencia se rechaza", sin.get("estado") == "blocked",
  sin.get("motivo", "")[:90])
estado_antes = c.execute("SELECT status FROM research WHERE id=?",
                         (fid,)).fetchone()[0]
v("y NO cambia el estado", estado_antes == "PROVEN", estado_antes)
print("   frontera de prueba: id=%s estado=%s" % (fid, estado_antes))
con = S.reabrir_frontier(c, fid, "el producer cambio de version")
estado_despues = c.execute("SELECT status FROM research WHERE id=?",
                           (fid,)).fetchone()[0]
print("   motivo: %s" % con.get("motivo", "")[:110])
v("reabrir CON evidencia pasa a OPEN", estado_despues == "OPEN", estado_despues)
v("y deja constancia del POR QUE (nota + audit)",
  con.get("nota_id") and c.execute("SELECT count(*) FROM audit_log WHERE "
                                   "action='reopen_frontier'").fetchone()[0] >= 1)
v("la frontera reabierta vuelve a evaluarse como NO saturada",
  not S.evaluar_saturacion_frontier(c, frontier_id=fid)["frontier_evaluaciones"][0]["saturada"])

c.close()
shutil.rmtree(d, ignore_errors=True)
print("=" * 74)
print("  %d/%d" % (sum(1 for x in ok if x), len(ok)))
sys.exit(0 if all(ok) else 1)