#!/usr/bin/env python3
"""RXRE-003. Vectores de ESTABILIDAD, no de funcionalidad.

QUE PRUEBA Y QUE NO.

`test_rxre.py` prueba la FORMA del envelope por capacidad.
`test_rxre002.py` prueba la CAPA que las combina.
`test_fixtures.py` prueba VALORES reales del corpus.
ESTE prueba que las decisiones de una IA son EJECUTABLES y que el contrato
impide las tres trampas que RXRE-003 nombra:

    blocked -> empty
    resultado parcial -> completo
    patron textual -> semantica demostrada

Y no vuelve a contar lo que ya cuentan los otros tres.

LO MAS IMPORTANTE DE ESTE FICHERO, y es la leccion de RXRE-002 escrita en codigo:

    un vector que comprueba que una accion tiene nombre no prueba que la accion
    funcione

La version anterior de la prueba de usabilidad hacia exactamente eso --
comparaba el NOMBRE de la accion contra la lista de ops -- y una accion podia
llamar a una op existente y estar mal formada. De ahi que estos vectores
EJECUTEN cada `next_action` y comprueben el estado que devuelve.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MACHINE = os.path.join(PKG, "api", "machine.py")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

fails: List[str] = []
n = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def rx(lineas, timeout=2400) -> List[Dict[str, Any]]:
    entrada = "\n".join(json.dumps(x) for x in lineas) + "\n"
    p = subprocess.run([sys.executable, MACHINE], input=entrada,
                       capture_output=True, text=True, timeout=timeout)
    return [json.loads(ln) for ln in p.stdout.splitlines() if ln.strip()]


OPS = [r["op"] for r in rx([{"op": "ops"}])[0]["results"]]

# --- 1. EL CATALOGO ESTA DONDE UNA IA LO BUSCA --------------------------
# MEDIDO: el catalogo de intenciones vivia SOLO en `ops`. Una IA que preguntaba
# `capabilities` -- que es lo natural -- recibia `capabilities: []` y se quedaba
# sin nada que elegir.

env_cap = rx([{"op": "capabilities"}])[0]
v("capabilities expone el catalogo de intenciones", len(env_cap.get("capabilities", [])) >= 8,
  len(env_cap.get("capabilities", [])))
v("y los scripts, que son otra cosa", len(env_cap.get("results", [])) >= 5,
  len(env_cap.get("results", [])))
v("las dos listas no se confunden",
  bool(env_cap.get("capabilities")) and bool(env_cap.get("results")),
  "una de las dos falta")

_ops = rx([{"op": "ops"}])[0]
v("ops tambien expone el catalogo", len(_ops.get("capabilities", [])) >= 8,
  len(_ops.get("capabilities", [])))

# Y una IA puede pasar de uno a otro: el catálogo de ops tiene el MISMO
# contenido que el de capabilities. Si divergieran, habria dos verdades.
v("el catalogo es el mismo en ops y en capabilities",
  [c["capability"] for c in _ops.get("capabilities", [])] ==
  [c["capability"] for c in env_cap.get("capabilities", [])])

# --- 2. CADA CAPACIDAD DICE SI SE PUEDE LLAMAR ----------------------------
# Una capacidad sin `available` es una trampa: la IA la elige y falla.
for c in env_cap.get("capabilities", []):
    # MEDIDO: el catalogo declaraba `resolved_by` (verbos internos) pero no
    # COMO se pide por la interfaz. Sin esto, una IA leia
    # `resolved_by: ["register","search"]` y no podia saber si escribir
    # `{"op":"register"}` -- que no existe -- o lo que si.
    v("la capacidad %s dice como invocarla" % c["capability"],
      bool(c.get("invocable", {}).get("op")), c["capability"])
    v("la capacidad %s tiene limitations" % c["capability"],
      bool(c.get("limitations")), c["capability"])
    # Y lo declarado tiene que ser LLAMABLE de verdad. Un `invocable` que da
    # error es peor que no tenerlo: la IA lo sigue y se estrella.
    _r = rx([c["invocable"]])[0]
    v("la capacidad %s es invocable de verdad" % c["capability"],
      _r.get("status") in ("ok", "empty"),
      "%s: %s" % (_r.get("status"), (_r.get("limitations") or ["?"])[0][:50]))

# --- 3. NEXT_ACTIONS EJECUTABLES, DE VERDAD -----------------------------
# ESTA es la prueba de RXRE-003. No basta el nombre: se EJECUTA.
_pregunta = "quien escribe VM_CONTEXT0_CNTL"
env = rx([{"op": "query", "target": "0000:01:00.0", "question": _pregunta}])[0]
acciones = env.get("next_actions") or []
v("query ok con acciones", env.get("status") == "ok" and acciones,
  (env.get("status"), len(acciones)))

for a in acciones:
    v("accion %s declara available" % a["action"], "available" in a)
    v("accion %s tiene porque" % a["action"], bool(a.get("why")), a)
    if a.get("available"):
        v("accion %s tiene op" % a["action"], bool(a.get("op")), a)
        v("accion %s tiene args" % a["action"], "args" in a, a)
        v("accion %s tiene criterio de exito" % a["action"],
          bool(a.get("success")), a)
        v("accion %s tiene criterio de stop" % a["action"],
          bool(a.get("stop")), a)
        v("accion %s nombra una op real" % a["action"], a["op"] in OPS,
          "%s no esta en %s" % (a["op"], OPS))
        # Y LA EJECUCION. aqui esta el vector que la version anterior no tenia.
        linea = dict(a.get("args") or {})
        linea["op"] = a["op"]
        r = rx([linea])[0]
        # MEDIDO (RXRE-005): este vector comprobaba `status != "error"`, y eso
        # deja pasar `blocked`, que NO es una ejecucion. Una accion que el
        # propio RXRE bloquea esta tan rota como una que da error, y era
        # exactamente lo que pasaba: `cross_check_uses` copiaba el SIMBOLO a la
        # raiz del request, `target_permitido` lo leia como dispositivo y
        # respondia `blocked` con la maxima confianza del envelope.
        #
        #     una accion bloqueada no es una accion ejecutada
        v("accion %s SE EJECUTA sin error" % a["action"],
          r.get("status") != "error",
          (r.get("limitations") or ["?"])[0][:70])
        v("accion %s SE EJECUTA de verdad (no basta con no ser error)" % a["action"],
          r.get("status") in ("ok", "empty"),
          "%s: %s" % (r.get("status"), (r.get("limitations") or ["?"])[0][:60]))
    else:
        # Una accion no disponible tiene que DECIR por que, no desaparecer.
        v("accion %s no disponible dice el motivo" % a["action"],
          bool(a.get("why")), a)

# --- 3b. T4 SOBRE MAS DE UNA PREGUNTA -----------------------------------
# MEDIDO (RXRE-005): la seccion 3 solo ejecutaba las acciones de UNA pregunta
# ("quien escribe VM_CONTEXT0_CNTL"). Con una sola, el hueco de cobertura no se
# veia: hay capacidades (`register.uses`) cuyas acciones solo se generan con
# otro enunciado, y ahi es donde la accion rompia.
#
# Un contrato verificado con una sola instancia no es un contrato verificado.
for _q in ("donde esta VM_CONTEXT0_CNTL",
           "donde esta el registro GFX_VM_CNTL",
           "donde esta CP_RB0_CNTL"):
    _e = rx([{"op": "query", "target": "0000:01:00.0", "question": _q}])[0]
    for _a in (_e.get("next_actions") or []):
        if _a.get("available") is not True:
            continue
        _l = dict(_a.get("args") or {})
        _l["op"] = _a["op"]
        _r = rx([_l])[0]
        v("accion %s de %r SE EJECUTA (ok/empty, no blocked)"
          % (_a["action"], _q[:26]),
          _r.get("status") in ("ok", "empty"),
          "%s: %s" % (_r.get("status"),
                      (_r.get("limitations") or ["?"])[0][:60]))

# --- 4. LAS TRES TRAMPAS DEL CONTRATO ------------------------------------
# 4a: blocked -> empty. La Intel no se ejecuta y no se dice "vacio".
_int = rx([{"op": "query", "target": "0000:00:02.0", "question": _pregunta}])[0]
v("Intel: blocked, no empty", _int.get("status") == "blocked", _int.get("status"))
v("Intel: no hay resultados", _int.get("results") == [])

# 4b: resultado parcial -> completo. Un PROVEN_ABSENT acotado no es hallazgo.
_aus = rx([{"op": "query", "target": "0000:01:00.0",
            "question": "donde esta ESTE_NO_EXISTE_XYZ_98765"}])[0]
v("un simbolo inexistente NO da ok", _aus.get("status") != "ok",
  _aus.get("status"))
v("y tiene limitations", bool(_aus.get("limitations")))

# 4c: patron textual -> semantica demostrada. Cada arista WRITES nace
# observed con su limitacion, y el fixture lo comprueba.
_escritores = [a for a in env.get("aristas", []) if a["tipo"] == "WRITES"]
v("hay aristas WRITES", len(_escritores) > 0, len(_escritores))
for a in _escritores[:3]:
    v("la arista WRITES nace observed", a["status"] == "observed", a["status"])
    v("la arista WRITES declara que es un candidato",
      bool(a.get("limitations")), a)
v("el resumen de relaciones cuenta WRITES",
  (env.get("relations_summary") or {}).get("WRITES", 0) == len(_escritores),
  (env.get("relations_summary"), len(_escritores)))

# --- 5. EXPLAIN POR LAS DOS VIA -----------------------------------------
# MEDIDO: `explain` solo aceptaba `result_id`, y la accion `explain_operation`
# pasaba `operation_id` -> error. La propia accion propuesta era un callejon.
rid = (env.get("results") or [{}])[0].get("result_id")
oid = env.get("operation_id")
if rid:
    e1 = rx([{"op": "explain", "result_id": rid}])[0]
    v("explain por result_id", e1.get("status") == "ok", e1.get("status"))
else:
    v("hay un result_id que explicar", False)
if oid:
    e2 = rx([{"op": "explain", "operation_id": oid}])[0]
    v("explain por operation_id", e2.get("status") == "ok", e2.get("status"))
    if e2.get("status") == "ok":
        _r = e2["results"][0]
        v("explain de operacion lista sus etapas", bool(_r.get("stages")))
        v("y la cadena con valores, no solo nombres",
          bool(_r.get("chain")) and len(_r["chain"]) >= 5, _r.get("chain"))
else:
    v("hay un operation_id que explicar", False)

e3 = rx([{"op": "explain"}])[0]
v("explain sin ningun id da error", e3.get("status") == "error",
  e3.get("status"))
v("y dice que falta", "falta" in (e3.get("limitations") or [""])[0],
  e3.get("limitations"))

# --- 5b. LAS TRAMPAS DE LA MUTACION: lo que debe ROMPERSE --------------
# MEDIDO 2026-10-05: seis mutaciones contractuales SOBREVIVIERON a las pruebas.
# Tres de estas comprobaciones nacen de ahi, y cada una existe porque una
# mutacion concreta paso sin que nada lo notara. No son comprobaciones
# hipoteticas: son el agujero que rellenan.
#
# (a) `result_id` constante. Todos los resultados con el mismo id no se pueden
#     distinguir, y `explain` deja de saber cual es cual.
_ids = [r.get("result_id") for r in (env.get("results") or [])]
v("todos los resultados tienen result_id", all(_ids), _ids[:2])
v("los result_id son UNICOS", len(set(_ids)) == len(_ids),
  "%d ids, %d distintos" % (len(_ids), len(set(_ids))))
v("un result_id no es una constante",
  len(set(_ids)) > 1 or len(_ids) <= 1, _ids[:2])
# Y el determinismo: dos consultas iguales dan los mismos ids. Un id que cambia
# con cada llamada no es un identificador, es un evento.
_rep = rx([{"op": "query", "target": "0000:01:00.0", "question": _pregunta}])[0]
_ids2 = [r.get("result_id") for r in (_rep.get("results") or [])]
v("dos consultas iguales dan los mismos result_id", _ids == _ids2,
  "%d ids distintos entre dos llamadas" % len(set(_ids) ^ set(_ids2)))

# (b) `provenance` vacia. Sin ella no se sabe de donde salio nada, y una IA
#     tiene que volver a ejecutar para averiguarlo.
v("la respuesta trae provenance", bool(env.get("provenance")),
  env.get("provenance"))
v("cada etapa del pipeline queda registrada",
  len(env.get("provenance") or []) >= len(env.get("stages") or []),
  (len(env.get("provenance") or []), len(env.get("stages") or [])))

# (c) `chain` vacia en explain. Una cadena vacia no dice de donde sale el dato;
#     es la misma trampa que la anterior, en la otra vista.
if rid:
    _e = rx([{"op": "explain", "result_id": rid}])[0]
    _rr = (_e.get("results") or [{}])[0]
    v("explain trae chain con pasos", bool(_rr.get("chain")), _rr.get("chain"))
    v("la chain no es una lista de una palabra sola",
      len(_rr.get("chain") or []) >= 3, _rr.get("chain"))

# --- 6. EL CATALOGO DICE SI UNA CAPACIDAD RESPONDE -----------------------
# Una capacidad que esta en el catalogo pero no tiene script detras es una
# trampa silenciosa: la IA la elige y solo se entera al ejecutarla.
from core import capabilities as C  # noqa: E402
from core import dispatch as D  # noqa: E402
for c in C.disponibles():
    usados = c.get("resolved_by") or []
    faltan = [u for u in usados if u not in D.ADAPTERS]
    v("la capacidad %s no nombra operaciones inexistentes" % c["capability"],
      not faltan, "faltan %s" % faltan)

# --- 7. TARGET: LAS CUATRO CASOS -----------------------------------------
v("target permitido se ejecuta", env.get("status") in ("ok", "empty"),
  env.get("status"))
v("target Intel se bloquea", _int.get("status") == "blocked")
_amb = rx([{"op": "query", "target": "unknown", "question": _pregunta}])[0]
v("target ambiguo no se ejecuta como si fuera la RX550",
  _amb.get("status") != "ok",
  "%s (%d resultados)" % (_amb.get("status"), len(_amb.get("results", []))))

# --- RESULTADO -----------------------------------------------------------
if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: catalogo dual, capacidades "
        "descubribles, next_actions EJECUTADAS, las tres trampas, explain por "
        "las dos vias, capacidad sin script huerfano, los cuatro casos de "
        "target)" % n)
sys.exit(0)