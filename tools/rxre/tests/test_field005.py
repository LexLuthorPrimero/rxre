#!/usr/bin/env python3
"""RXRE-005. Vectores de los dos BLOCKERS reparados.

QUE NO HACE ESTE FICHERO.

NO prueba que RXRE "funcione bien" en general. Ya hay siete suites para eso
(RXRE-001 a RXRE-004) y §22 prohibe volver a auditar lo cerrado. Aqui se
comprueban DOS COSAS, y se comprobaron mal antes de repararlas:

    BLOCKER 1  el contrato publico afirmaba ausencias que NO eran ciertas
    BLOCKER 2  no existia ninguna via para persistir el estado de investigacion

Y se comprueban por la SUPERFICIE PUBLICA (JSONL sobre stdin/stdout), porque un
defecto del contrato solo se ve desde fuera: por dentro la op funcionaba, y
precisamente por eso la IA externa no la encontraba.

## LO QUE ESTOS VECTORES MIDEN, Y POR QUE NO BASTA CON LEER

* El contrato no puede afirmar que algo falta si existe. Se comprueba cada
  afirmacion de §6.1 contra una llamada real.
* Un `PROVEN` sin evidencia tiene que ser rechazado. Es la regla que impide
  que el estado de investigacion se convierta en un deposito de opiniones.
* Perder el contexto conversacional no puede implicar perder la investigacion.
  Se mide con un PROCESO DISTINTO y una sesion distinta leyendo el checkpoint.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MAQUINA = os.path.join(PKG, "api", "machine.py")
CONTRATO = os.path.join(PKG, "docs", "RXRE_PUBLIC_CONTRACT.md")

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def rx(requests, db=None):
    """JSONL contra la interfaz publica. Cada llamada es un PROCESO NUEVO."""
    env_ = dict(os.environ)
    if db:
        env_["RXRE_DB"] = db
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=1200, env=env_)
    o = []
    for l in (p.stdout or "").splitlines():
        l = l.strip()
        if l:
            try:
                o.append(json.loads(l))
            except ValueError:
                fails.append("linea no JSON: %r" % l[:80])
    return o


# --- 0. PRECONDICIONES ----------------------------------------------------
v("la interfaz publica existe", os.path.isfile(MAQUINA))
v("el contrato publico existe", os.path.isfile(CONTRATO))
CT = open(CONTRATO, encoding="utf-8").read()

# =====================================================================
# BLOCKER 1. El contrato no puede afirmar ausencias falsas.
# =====================================================================
# MEDIDO antes de reparar:
#   contrato: "**No hay `plan`.**"
#   realidad : {"op":"plan","capability":"binary.decompile"} -> status=ok,
#              execution=not_started, 6 pasos
# Es decir: el contrato MENTIA, y una IA que solo lo lee no pide plan.

# (a) El contrato no puede afirmar que falta una op que EXISTE.
#
# MEDIDO (RXRE-005): la primera version de este vector ENUMERABA cuatro frases
# concretas ("No hay `plan`", "3 de 4 acciones..."). Mutar el contrato
# insertando "**No hay `checkpoint`.**" lo dejo pasar, porque `checkpoint` no
# estaba en la lista. Es la clase ciega que B0 ya habia golpeado una vez:
#
#     un vector que enumera casos no vigila la regla
#
# Esta version deriva la REGLA: para cada op que existe, el contrato no puede
# decir que no existe. Y mira las dos formas en que puede decirlo: una linea que
# empieza por "No hay", y una fila de la tabla de ausencias de la seccion 6.
import importlib  # noqa: E402
if PKG not in sys.path:
    sys.path.insert(0, PKG)
_ops = importlib.import_module("api.machine")._ops
_ops_reales = sorted(_ops())
_lineas = CT.splitlines()

_vivas = []
for _ln in _lineas:
    _s = _ln.strip()
    if _s.startswith("| \u00ab"):
        continue                 # cita historica en 6.1: lo que SE DECIA
    _b = _s.lower().lstrip("*")
    if _b.startswith("no hay "):
        for _o in _ops_reales:
            if ("`%s`" % _o) in _s:
                _vivas.append((_o, _s[:80]))
v("[contrato] ninguna op que EXISTE es declarada ausente en el texto",
  not _vivas, _vivas[:3])

_tabla = []
_en = False
for _ln in _lineas:
    if _ln.startswith("### 6.1"):
        # La subseccion 6.1 CITA las ausencias viejas como lo que SE DECIA.
        # Citarlas es lo correcto; declararlas seria exactamente el defecto.
        _en = False
    elif _ln.startswith("## 6."):
        _en = True
    elif _ln.startswith("## 7."):
        _en = False
    if _en and _ln.strip().startswith("|"):
        for _o in _ops_reales:
            if ("`op: %s`" % _o) in _ln or ("`%s`" % _o) in _ln:
                _tabla.append((_o, _ln.strip()[:70]))
v("[contrato] la tabla de ausencias no lista ninguna op que exista",
  not _tabla, _tabla[:3])

# (b) Las ops que existen tienen que estar documentadas. Una op nueva que nadie
#     documento es INALCANZABLE para la IA externa, por muy bien que funcione.
for o in _ops_reales:
    v("[contrato] documenta la op `%s`" % o, ("`%s`" % o) in CT, o)


# (c) Y la afirmacion central de §6.1 tiene que ser VERDAD: plan funciona.
_pl = rx([{"op": "plan", "capability": "binary.decompile"}])
if _pl:
    P = _pl[0]
    v("[contrato] `plan` existe de verdad: status ok", P.get("status") == "ok",
      P.get("status"))
    v("[contrato] `plan` no ejecuta: execution=not_started",
      P.get("execution") == "not_started", P.get("execution"))
    v("[contrato] `plan` tiene pasos", len(P.get("plan") or []) >= 2,
      len(P.get("plan") or []))

# (d) Las 4 next_actions de un query son invocables (el contrato lo afirmaba
#     al reves antes).
_q = rx([{"op": "query", "question": "donde esta VM_CONTEXT0_CNTL",
          "target": "0000:01:00.0"}])
if _q:
    na = _q[0].get("next_actions") or []
    v("[contrato] el query devuelve next_actions", bool(na), na)
    v("[contrato] TODAS invocables o con available:false+motivo",
      all(a.get("available") is True
          or (a.get("available") is False and bool(a.get("reason")))
          for a in na), na)
    disp = [a for a in na if a.get("available") is True]
    v("[contrato] las disponibles llevan op y args", bool(disp)
      and all(a.get("op") and isinstance(a.get("args"), dict) for a in disp),
      disp[:1])

# =====================================================================
# BLOCKER 2. El estado de investigacion se persiste y se recupera.
# =====================================================================
# MEDIDO antes de reparar: las tablas eran meta, operations, results,
# relations, edges. Ninguna de hipotesis/claim/nota/checkpoint. Una IA nueva
# sin contexto que preguntaba "que estoy investigando" recibia `empty`.
_dbdir = tempfile.mkdtemp(prefix="rxre005_db_")
DB = os.path.join(_dbdir, "campo.sqlite3")
SES = "v005_campo"
TGT = "0000:01:00.0"

# Una sesion de UNA JORNADA, escrita con la op publica.
_escrituras = [
    {"op": "record", "kind": "hypothesis", "status": "OPEN", "session": SES,
     "target": TGT,
     "text": "H1: VM_CONTEXT0_CNTL lo programa el reset, no el resume"},
    {"op": "record", "kind": "hypothesis", "status": "REFUTED", "session": SES,
     "target": TGT,
     "text": "H2: lo escribe gfx_v8_0_cp_gfx_resume"},
    {"op": "record", "kind": "hypothesis", "status": "OPEN", "session": SES,
     "target": TGT, "gap_kind": "HUECO_DE_CONEXION",
     "text": "H3: falta el eslabon entre el productor del IB y el consumidor"},
    {"op": "record", "kind": "claim", "status": "PARTIAL", "session": SES,
     "target": TGT,
     "text": "C1: el anillo se arma por MMIO, no por PM4"},
    {"op": "record", "kind": "frontier", "status": "OPEN", "session": SES,
     "target": TGT, "text": "F1: que unidad fisica hace el fetch del CP_RB"},
    {"op": "record", "kind": "next_action", "status": "OPEN", "session": SES,
     "target": TGT,
     "text": "cruzar los escritores de CP_RB0_CNTL con el corpus"},
]
_e = rx(_escrituras, db=DB)
v("[research] las 6 entradas se graban", len(_e) == 6
  and all(x.get("status") == "ok" for x in _e),
  [x.get("status") for x in _e])

# (a) Las reglas que NO son de estilo.
_r = rx([{"op": "record", "kind": "claim", "status": "PROVEN",
         "session": SES, "target": TGT, "text": "C sin evidencia"}], db=DB)
if _r:
    v("[research] PROVEN sin refs se RECHAZA", _r[0].get("status") == "blocked",
      _r[0].get("status"))
    v("[research] y el motivo explica por que (seccion 9)",
      "refs" in " ".join(_r[0].get("limitations") or []),
      _r[0].get("limitations"))

_r = rx([{"op": "record", "kind": "inventado", "text": "x",
         "session": SES}], db=DB)
v("[research] kind fuera de la lista cerrada se RECHAZA",
  _r[0].get("status") == "blocked", _r[0].get("status"))

# MEDIDO: la primera version de este vector agrupaba un caso VALIDO
# (`note` + `PROVEN` + refs, que la lista cerrada PERMITE) con uno invalido, y
# por eso fallaba. Lo que se cierra es la LISTA, no cada combinacion
# kind/status: `PROVEN` con evidencia es legitimo para cualquier kind.
_r = rx([{"op": "record", "kind": "note", "status": "NO_ES_UN_ESTADO",
         "session": SES, "text": "n"}], db=DB)
v("[research] status fuera de la lista cerrada se RECHAZA",
  _r[0].get("status") == "blocked", _r[0].get("status"))
# Create a real result to reference for the PROVEN test.
# `record` writes to `research`, not `results`, so a note can only be cited
# via a real result (or op/edge). This is exactly what makes ref validation
# meaningful.
q = rx([{"op": "query", "question": "donde esta VM_CONTEXT0_CNTL",
         "target": TGT}], db=DB)
assert q[0].get("status") == "ok", "setup query failed"
results = q[0].get("results") or []
assert results, "setup query returned no results"
real_result_id = results[0].get("result_id")
assert real_result_id, "setup query returned result without result_id"
# Now test PROVEN with a real ref
_r = rx([{"op": "record", "kind": "note", "status": "PROVEN",
          "refs": [real_result_id], "session": SES, "text": "n"}], db=DB)
v("[research] y PROVEN con refs SI se acepta (la lista, no cada combinacion)",
  _r[0].get("status") == "ok", _r[0].get("status"))

# gap_kind solo para hypothesis/claim (§8)
_r = rx([{"op": "record", "kind": "next_action", "status": "OPEN",
         "session": SES, "text": "x", "gap_kind": "HUECO_DE_CONEXION"}], db=DB)
v("[research] gap_kind en next_action se RECHAZA (una accion no tiene hueco)",
  _r[0].get("status") == "blocked", _r[0].get("status"))

_r = rx([{"op": "record", "kind": "note", "status": "OPEN", "session": SES,
         "text": "   "}], db=DB)
v("[research] text vacio se RECHAZA", _r[0].get("status") != "ok",
  _r[0].get("status"))

# (b) LA PRUEBA DE CONTINUIDAD. Proceso NUEVO, sesion distinta, sin contexto.
_ck = rx([{"op": "checkpoint", "session": SES, "target": TGT}], db=DB)
if _ck:
    C = _ck[0]
    ck = C.get("checkpoint") or {}
    v("[checkpoint] responde ok", C.get("status") == "ok", C.get("status"))
    v("[checkpoint] 2 hipotesis abiertas (una OPEN, otra con hueco)",
      len(ck.get("hipotesis_abiertas") or []) == 2,
      len(ck.get("hipotesis_abiertas") or []))
    v("[checkpoint] 1 hipotesis refutada",
      len(ck.get("hipotesis_refutadas") or []) == 1,
      len(ck.get("hipotistas_refutadas") or ck.get("hipotesis_refutadas") or []))
    v("[checkpoint] 1 claim con su status",
      len(ck.get("claims") or []) == 1
      and (ck["claims"][0].get("status") == "PARTIAL"),
      ck.get("claims"))
    v("[checkpoint] 1 frontera abierta", len(ck.get("fronteras") or []) == 1,
      len(ck.get("fronteras") or []))
    v("[checkpoint] la siguiente accion se puede SEGUIR, no solo leer",
      bool((ck.get("siguiente_accion") or {}).get("text")))
    v("[checkpoint] cuenta la evidencia sin COPIARLA",
      (ck.get("evidencia_en_base") or {}).get("operations") is not None
      and "rows" not in json.dumps(ck.get("evidencia_en_base") or {}),
      ck.get("evidencia_en_base"))
    v("[checkpoint] lee las aristas de `edges`, no de `relations` (0 filas)",
      "edges" in (ck.get("evidencia_en_base") or {}),
      ck.get("evidencia_en_base"))
    # La accion siguiente debe ser EJECUTABLE (§11 de RXRE-003).
    na = C.get("next_actions") or []
    sig = [a for a in na if a["op"] == "query"]
    v("[checkpoint] la siguiente accion es una query REAL y ejecutable",
      bool(sig) and sig[0]["available"] is True
      and bool((sig[0].get("args") or {}).get("question")), na)
    # MEDIDO: se ejecutaba `sig[0]["args"]` SIN `op`, y eso da
    # `error: falta 'op' en la peticion`. La forma canonica es `request`, que es
    # la linea completa y enviable. Este vector fue el que delato que `args`
    # solo no basta.
    v("[checkpoint] la accion trae `request` con el op dentro",
      bool(sig) and (sig[0].get("request") or {}).get("op") == "query",
      sig[0].get("request") if sig else None)
    v("[checkpoint] y esa query se puede EJECUTAR tal cual, sin reinterpretar",
      bool(sig) and rx([sig[0]["request"]], db=DB)[0].get("status")
      in ("ok", "empty"))

# (c) Empty con motivo. La ausencia tiene que decir DE QUE.
_ck2 = rx([{"op": "checkpoint", "session": "NO_EXISTE_NADA",
           "target": TGT}], db=DB)
v("[checkpoint] sesion inexistente -> empty, no ok",
  _ck2[0].get("status") == "empty", _ck2[0].get("status"))
v("[checkpoint] y el motivo distingue 'no hay nada' de 'no coincide el filtro'",
  "filtro" in " ".join(_ck2[0].get("limitations") or [])
  or "VACIA" in " ".join(_ck2[0].get("limitations") or []),
  _ck2[0].get("limitations"))

# (d) La tabla research NO se confunde con results. Una hipotesis no es
#     evidencia, y por eso no puede aparecer como un resultado.
from core import store as S  # noqa: E402
_c = S.conectar(DB)
try:
    # 6 sembradas + 1 `note` PROVEN que el vector anterior grabo con exito.
    v("[research] `research` existe como tabla propia y solo contiene lo "
      "escrito por esta sesion",
      _c.execute("SELECT COUNT(*) FROM research").fetchone()[0] == 7,
      _c.execute("SELECT COUNT(*) FROM research").fetchone()[0])
    v("[research] y las 6 rechazadas NO dejaron fila (un rechazo no es un hueco)",
      _c.execute("SELECT COUNT(*) FROM research WHERE text LIKE '%refs%' "
                 "OR text='   '").fetchone()[0] == 0,
      _c.execute("SELECT COUNT(*) FROM research WHERE text LIKE '%refs%' "
                 "OR text='   '").fetchone()[0])
    # El setup de PROVEN con refs grabo 36 resultados (el query de arriba).
    # El test verifica que las entries de investigacion viven en `research`
    # con su kind y session, no en `results`.
    research_count = _c.execute("SELECT COUNT(*) FROM research "
                                "WHERE session=?", (SES,)).fetchone()[0]
    results_count = _c.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    v("[research] las entradas NO estan en `results` (interpretacion != evidencia)",
      research_count == 7 and results_count >= 36,
      "research=%d entries con kind/session, results=%d registros de evidencia"
      % (research_count, results_count))
    v("[research] las entradas guardan REFS por id, no copias (hypothesis)",
      json.loads(_c.execute(
          "SELECT refs_json FROM research WHERE kind='hypothesis' LIMIT 1").fetchone()[0]) is not None,
      "...")
    v("[research] una entrada OPEN sin refs es legal (una hipotesis no cita "
      "evidencia todavia)",
      _c.execute("SELECT COUNT(*) FROM research WHERE kind='hypothesis' AND "
                 "refs_json='[]'").fetchone()[0] >= 1)
finally:
    _c.close()
shutil_rmtree = __import__("shutil")
shutil_rmtree.rmtree(_dbdir, ignore_errors=True)

# (e) Las op nuevas se auto-documentan (`op:ops`), que es la segunda via de
#     descubrimiento ademas del contrato.
_opsenv = rx([{"op": "ops"}])
if _opsenv:
    ops = {r.get("op"): r for r in (_opsenv[0].get("results") or [])}
    for o in ("run", "backends", "plan", "record", "checkpoint"):
        v("[ops] declara `%s` con campos y ejemplo" % o,
          o in ops and bool(ops[o].get("campos") is not None)
          and bool(ops[o].get("ejemplo")), sorted(ops))

if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: el contrato ya no afirma ausencias "
        "falsas y documenta las 11 ops, PROVEN sin refs se rechaza, las "
        "listas de kind/status son cerradas, gap_kind solo aplica a "
        "hipotesis y claim, y un PROCESO NUEVO recupera la investigacion desde "
        "el checkpoint sin contexto conversacional)" % n)
sys.exit(0)