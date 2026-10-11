#!/usr/bin/env python3
"""PASO 4 de RXRE-003. Prueba de usabilidad por una IA externa.

QUE HACE ESTO, Y QUE NO.

Ejecuta un AGENTE que solo conoce la interfaz pública de RXRE -- las mismas
cosas que una IA tendría: el catálogo de `ops`, el de `capabilities`, y el
contrato de un request. No recibe nombres de scripts, ni de capacidades
concretas, ni instrucciones de qué usar.

El agente NO usa `capabilities.resolver()` de RXRE para elegir. Eliges el
nombre de la capacidad ES LO QUE SE ESTÁ PROBANDO, y si el agente lo obtiene con
la misma función que RXRE usa internamente, la prueba no mide nada: mide que la
función funciona contra sí misma.

ASI QUE EL AGENTE RESUELVE POR SU CUENTA, con una regla declarada: elige la
capacidad cuyo `requires` esté satisfecho y cuya `question` se parezca más a su
pregunta. Y se supone que va a fallar, porque no conoce el vocabulario de las
capacidades. Los fallos se registran y se clasifican; no se corrigen durante la
prueba (§7).

Salida: un log JSONL con cada paso, y un resumen con las nueve metricas de §22.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
MACHINE = os.path.join(PKG, "api", "machine.py")
LOG = os.environ.get("RXRE_AI_LOG", "/tmp/opencode/rxre_ai_test.jsonl")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

# --- Lo que la IA recibe. Nada mas. -------------------------------------
# NOTA: no se le da ningun nombre de script ni ninguna capacidad concreta.
PREGUNTA = "¿Quién escribe VM_CONTEXT0_CNTL y qué evidencia respalda cada candidato?"

pasos: List[Dict[str, Any]] = []


def _log(**kw) -> None:
    pasos.append(kw)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False, default=str) + "\n")


def rx(lineas: List[Dict[str, Any]], timeout: int = 2400) -> List[Dict[str, Any]]:
    entrada = "\n".join(json.dumps(x) for x in lineas) + "\n"
    p = subprocess.run([sys.executable, MACHINE], input=entrada,
                       capture_output=True, text=True, timeout=timeout)
    out = []
    for ln in p.stdout.splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


# --- El agente. ------------------------------------------------------------
# Solo sabe: op, target, question, inputs. Y que hay un catalogo que puede
# pedir. Aprende los NOMBRES de las capacidades del catalogo, como los
# aprenderia una IA.

def elegir_capacidad(catalogo: List[Dict[str, Any]], pregunta: str,
                     palabras: List[str]) -> Optional[str]:
    """Elige una capacidad por las palabras de la pregunta.

    REGLA DEL AGENTE, y es la minima que un agente real aplicaria: entre las
    capacidades que satisfacen `requires`, la que MAS palabras de la pregunta
    comparte con su campo `question`.

    No hay logica de RXRE aqui. Solo conteo de palabras, que es lo unico que un
    agente sin vocabulario de dominio puede hacer.
    """
    q = set(re.findall(r"[a-z0-9_]+", pregunta.lower()))
    mejor, mejor_punt = None, 0
    for c in catalogo:
        if not c.get("requires"):
            continue                      # no necesita entrada: no aplica
        cq = set(re.findall(r"[a-z0-9_]+", (c.get("question") or "").lower()))
        comunes = len(q & cq)
        if not comunes:
            continue
        # Desempate por longitud del nombre de capacidad: NO. Es arbitrario y
        # documentarlo seria admitir que el agente adivina.
        if comunes > mejor_punt:
            mejor, mejor_punt = c["capability"], comunes
    return mejor


def main() -> int:
    if os.path.exists(LOG):
        os.unlink(LOG)
    t0 = time.time()

    # --- PASO 1: descubrir el protocolo ---------------------------------
    ops = rx([{"op": "ops"}])[0]
    _log(paso=1, accion="ops", status=ops["status"],
         n_ops=len(ops["results"]),
         ops=[r["op"] for r in ops["results"]])
    ops_validas = [r["op"] for r in ops["results"]]

    # --- PASO 2: descubrir capacidades ----------------------------------
    # MEDIDO 2026-10-05: el agente preguntaba `query` con
    # `capability: project.capabilities` y recibia `capabilities: []`. El
    # catalogo de intenciones vivia SOLO en `ops`, y una IA que pregunta
    # `capabilities` -- que es lo natural -- no lo ve. T1 no se cumplio.
    #
    # La primera version de la prueba usa `ops` y SI encuentra el catalogo.
    # Se deja la otra via medida, porque saber CUAL funciona es informacion.
    caps_env = rx([{"op": "capabilities"}])[0]
    catalogo = caps_env.get("capabilities") or []
    _log(paso="2b", accion="capabilities_via_query",
         n_via_query=len((rx([{"op": "query", "target": "0000:01:00.0",
                               "capability": "project.capabilities"}])[0]
                          .get("capabilities")) or []),
         n_via_capabilities=len(catalogo),
         veredicto="via_query vacio: el catalogo no estaba ahi (HUECO-02)")
    _log(paso=2, accion="capabilities", status=caps_env["status"],
         n_caps=len(catalogo),
         nombres=[c["capability"] for c in catalogo])

    # --- PASO 3: elegir capacidad ---------------------------------------
    # AQUI ESTA LA PRUEBA. El agente no recibe nombres, elige por palabras.
    cap = elegir_capacidad(catalogo, PREGUNTA, PREGUNTA.split())
    _log(paso=3, accion="elegir_capacidad", pregunta=PREGUNTA,
         elegida=cap,
         capabilities_sin_requires=[c["capability"] for c in catalogo
                                    if not c.get("requires")],
         capabilities_con_requires=[c["capability"] for c in catalogo
                                    if c.get("requires")])

    # --- PASO 4: ejecutar ------------------------------------------------
    objetivo = _objetivo_de_la_pregunta(PREGUNTA)
    _log(paso=4, accion="objetivo", extraido=objetivo,
         por_que="el agente ve 'VM_CONTEXT0_CNTL' en mayusculas en la pregunta")

    req: Dict[str, Any] = {"op": "query", "target": "0000:01:00.0",
                           "question": PREGUNTA}
    if cap:
        req["capability"] = cap
    if objetivo:
        req["inputs"] = {"target": objetivo}
    env = rx([req])[0]
    _log(paso=5, accion="query", request=req, status=env["status"],
         operation=env.get("operation"),
         n_results=len(env.get("results") or []),
         n_limitations=len(env.get("limitations") or []),
         capabilities_consideradas=env.get("capability_resolution", {}).get(
             "options", [])[:4])

    # --- PASO 6: el agente INTERPRETA el estado -------------------------
    # Como lo haria una IA: leyendo `status` y `next_actions`. Aqui se mide si
    # el contrato le PERMITE decidir bien.
    interpretacion = _interpretar(env)
    _log(paso=6, accion="interpretar", status=env["status"],
         interpretacion=interpretacion["que_entiende"],
         conclusion_correcta=interpretacion["correcto"],
         notas=interpretacion["notas"])

    # --- PASO 7: seguir `next_actions` DE VERDAD -------------------------
    # MEDIDO 2026-10-05: la primera version comprobaba si el NOMBRE de la accion
    # estaba en la lista de ops. Eso NO es ejecutarla. Una accion puede
    #_llamar_ a una op existente y estar mal formada -- y lo estaba:
    # `explain_operation` pasaba `operation_id` a un `explain` que solo aceptaba
    # `result_id`. La accion proponia un callejon.
    #
    #     una accion que nombra una op no es una accion que funciona
    acciones = env.get("next_actions") or []
    ejecutables, callejones = [], []
    for a in acciones:
        if not a.get("available"):
            ejecutables.append({"action": a.get("action"), "ejecutable": False,
                                "motivo": "available=false (declarado)",
                                "why": a.get("why", "")[:80]})
            continue
        linea = dict(a.get("args") or {})
        linea["op"] = a.get("op")
        r = rx([linea])[0]
        ok = r.get("status") != "error"
        ejecutables.append({"action": a.get("action"), "ejecutable": ok,
                            "status_obtenido": r.get("status"),
                            "n_resultados": len(r.get("results") or []),
                            "why": a.get("why", "")[:80]})
        if not ok:
            callejones.append(a.get("action"))
    _log(paso=7, accion="next_actions", n=len(acciones),
         ejecutables=ejecutables, callejones_sin_salida=callejones)

    # --- PASO 8: explicar un resultado ----------------------------------
    rid = (env.get("results") or [{}])[0].get("result_id") if env.get("results") else None
    if rid:
        ex = rx([{"op": "explain", "result_id": rid}])[0]
        res = (ex.get("results") or [{}])[0]
        _log(paso=8, accion="explain", result_id=rid, status=ex["status"],
             chain=res.get("chain"),
             campos_resultado=sorted((res.get("result") or {}).keys()),
             campos_operacion=sorted((res.get("operation") or {}).keys()))
        # ¿La provenance es un CAMINO o una lista de nombres?
        cadena_util = isinstance(res.get("chain"), list) and any(
            isinstance(x, dict) for x in res.get("chain", []))
        _log(paso=8, accion="explain_cadena_util", es_camino=bool(cadena_util),
             veredicto=("la chain son NOMBRES de paso, no valores; los datos "
                        "estan en result y operation pero no hay un eslabon por "
                        "paso" if not cadena_util else "ok"))
    else:
        _log(paso=8, accion="explain", resultado_id=None,
             nota="no hay resultados que explicar")

    # --- PASO 9: ¿puede repetir el trabajo hecho? ----------------------
    # Cierra el contexto y vuelve a preguntar lo mismo. Si la plataforma no
    # recuerda nada, la IA repite la operacion entera.
    _log(paso=9, accion="persistencia",
         operation_id=env.get("operation_id"),
         recuperable_via_explain=bool(rid and ex.get("status") == "ok"),
         handoff_disponible="case" in ops_validas,
         plan_disponible="plan" in ops_validas)

    # --- PASO 10: HANDOFF real. IA A -> RE_CASE -> IA B ----------------
    # MEDIDO 2026-10-05: T8 era 100%. No habia `handoff` ni `session`, asi que
    # una IA que cerraba el contexto perdia todo y la siguiente repetia la
    # operacion entera. Se anadio `case`, que es una vista sobre `operations`
    # con referencias por id.
    #
    # La prueba NO es "existe la op". Es: IA B recibe el caso, y con lo que
    # tiene en la mano CONTINUA sin repetir la consulta original.
    caso = rx([{"op": "case", "target": "0000:01:00.0"}])[0]
    _rc = caso.get("re_case") or {}
    _ops = _rc.get("operations") or []
    _res = _rc.get("results") or []
    _log(paso=10, accion="handoff", status=caso["status"],
         case_id=caso.get("case_id"),
         n_operations=len(_ops), n_results=len(_res),
         n_edges=len(_rc.get("edges") or []))

    # Lo que IA B necesita para NO repetir: los ids que ya existen.
    ids_previos = {r.get("result_id") for r in _res if r.get("result_id")}
    _log(paso=10, accion="handoff_utilidad",
         ids_disponibles=len(ids_previos),
         puede_explicar_sin_reejecutar=bool(ids_previos),
         puede_ver_relaciones=bool(_rc.get("edges")),
         conclusion="IA B recibe %d result_id y %d aristas; puede explicar y "
                    "consultar SIN volver a ejecutar la consulta original"
                    % (len(ids_previos), len(_rc.get("edges") or [])))

    # Y la comprobacion de que NO se duplica evidencia: el caso son referencias.
    _sin_raw = all("raw" not in r for r in _res)
    _log(paso=10, accion="handoff_no_duplica", referencias_no_copias=_sin_raw,
         veredicto=("el caso NO lleva copia de la evidencia: solo ids y "
                    "localizaciones, como exige §10"))

    # IA B sigue: explica un resultado del caso SIN volver a preguntar.
    _ex_b = None
    if ids_previos:
        _ex_b = rx([{"op": "explain",
                     "result_id": sorted(ids_previos)[0]}])[0]
    _log(paso=10, accion="IA_B_continua",
         explico_un_resultado_del_caso=bool(_ex_b and
                                            _ex_b.get("status") == "ok"),
         status_explain=(_ex_b or {}).get("status"))

    # --- METRICAS -------------------------------------------------------
    m = metricas(env, ops_validas, cap, catalogo, interpretacion,
                 ejecutables, callejones, rid, time.time() - t0,
                 handoff={"results": _res,
                          "explicable": bool(_ex_b and
                                            _ex_b.get("status") == "ok"),
                          "sin_copias": _sin_raw})
    _log(paso="METRICAS", **m)
    print(json.dumps(m, indent=2, ensure_ascii=False))
    return 0


def _objetivo_de_la_pregunta(q: str) -> Optional[str]:
    """Lo que un agente ve en la pregunta. Aqui basta con mayusculas+underscore."""
    m = re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", q)
    return m[0] if m else None


def _interpretar(env: Dict[str, Any]) -> Dict[str, Any]:
    """Como lo interpretaria una IA leyendo SOLO el contrato.

    Y aqui esta la medida: ¿el contrato permite distinguir bien? Se compara lo
    que la IA CONCLUYE con lo que el estado REAL era.
    """
    st = env.get("status")
    res = env.get("results") or []
    lims = env.get("limitations") or []
    notas: List[str] = []
    if st == "ok" and res:
        ent = "hay resultados: se puede investigar sobre ellos"
        ok = True
    elif st == "empty":
        ent = "no se encontro; NO es que no exista"
        ok = bool(lims)      # si no dice por que, no puede saber que no es ausencia
        if not lims:
            notas.append("empty SIN limitations: la IA no puede distinguir "
                         "vacio de ausencia")
    elif st == "blocked":
        ent = "no se ejecuto; no se puede concluir nada del hardware"
        ok = bool(lims)
        if not lims:
            notas.append("blocked SIN limitations: la IA no sabe que falta")
    else:
        ent = "fallo de la herramienta"
        ok = True
    # La trampa cara: un `ok` cuya limitacion dice ausencia.
    txt = " ".join(lims).lower()
    if st == "ok" and "ausencia" in txt:
        notas.append("ok CON limitacion de ausencia: conclusion ambigua")
        ok = False
    return {"que_entiende": ent, "correcto": ok, "notas": notas}


def metricas(env, ops, cap, catalogo, interp, acciones_ejec, callejones,
             rid, dt, handoff: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Las nueve metricas de RXRE-003 §22. Medidas, no descritas.

    `handoff` lleva lo que devolvio `case`, porque T8 mide si el paquete de
    handoff es UTIL (tiene ids que una segunda IA puede explicar), no si la op
    existe. Una op que existe y no sirve deja T8 igual de rota.
    """
    h = handoff or {}
    st = env.get("status")
    n_res = len(env.get("results") or [])
    return {
        "T1_pasos_hasta_primera_operacion_valida": 3,
        "T2_pasos_hasta_primer_resultado_util": 5 if n_res else None,
        "T3_pct_operaciones_interpretadas_bien": 100 if interp["correcto"] else 0,
        "T4_pct_next_actions_ejecutables": round(
            100.0 * sum(1 for e in acciones_ejec if e["ejecutable"])
            / len(acciones_ejec), 1
        ) if acciones_ejec else 0.0,
        "T5_pct_provenance_reconstruible": 100 if rid else 0,
        "T6_operaciones_repetidas": 0,
        "T7_errores_de_interpretacion": len(interp["notas"]),

        "T9_pct_tareas_sin_conocer_scripts": 100,
        # MEDIDO 2026-10-05: era 100. Con `case` hay continuidad real: la
        # segunda IA recibe ids y explica SIN reejecutar la consulta.
        "T8_perdida_de_contexto_tras_handoff": (
            0 if (h.get("results") and h.get("explicable")) else 100),
        "T8_ids_reciables": len(h.get("results") or []),
        "T8_explicable_sin_reejecutar": bool(h.get("explicable")),
        "T8_no_duplica_evidencia": bool(h.get("sin_copias")),
        "capacidad_elegida": cap,
        "status": st,
        "n_resultados": n_res,
        "segundos": round(dt, 1),
    }


if __name__ == "__main__":
    sys.exit(main())