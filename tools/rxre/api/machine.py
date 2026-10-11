#!/usr/bin/env python3
"""Entrada machine-readable de RXRE-002. JSON Lines sobre stdin/stdout.

POR QUE JSONL Y NO JSON-RPC NI UN SOCKET.

§27 pide JSONL o JSON-RPC local. JSONL gana por una razon concreta: es lo unico
que no necesita ni un puerto ni un demonio ni una negociacion, y se puede
ejecutar desde una shell, desde Python, o desde un pipe sin cambiar nada. Un
socket es infraestructura que hay que mantener viva; un JSONL es un proceso que
termina. Para una IA que lanza comandos, un proceso que termina es mas simple de
razonar que un servidor al que hay que reconectar.

Y hay una propiedad que importa para este proyecto: cada linea es un envelope
completo e independiente, con su `request_id` y su `status`. Si una linea se
corrupte, las demas siguen siendo validas. Un unico JSON grande que se parsea
todo o nada convierte un error de una linea en la perdida de todas.

EL CONTRATO, en una linea:

    {"contract_version":"1.0","op":"query","question":"...","target":"..."}
    -> envelope con status, results, evidence, provenance, limitations,
       next_actions

Y lo que NO hay: ningun estado global entre lineas. Cada `query` es completa.
La memoria entre invocaciones vive en SQLite, que es consultable, y no en el
proceso, que se pierde.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

# MEDIDO 2026-10-05: `sys.path` necesita la raiz de PAQUETE (`tools/rxre/`), no
# el directorio de este fichero (`tools/rxre/api/`). Con `api/` en el path,
# `from api import ...` no encuentra nada porque buscaria `api/api/`.
_PKG = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from api import envelope as E           # noqa: E402
from api.request import CONTRACT_VERSION  # noqa: E402
from commands import query as Q         # noqa: E402
from core import capabilities as caps    # noqa: E402

VERSION = "0.2.0"


def _ops() -> Dict[str, Any]:
    """Catalogo de operaciones de la interfaz. Se responde con `ops`."""
    return {
        "query": {"que_hace": "responde una pregunta de RE reutilizando las "
                               "capacidades existentes",
                  "campos": ["question", "target", "inputs", "scope", "capability"],
                  "ejemplo": {"op": "query", "target": "0000:01:00.0",
                              "question": "quien escribe VM_CONTEXT0_CNTL"}},
        "capabilities": {"que_hace": "que puedo investigar y que responde de verdad",
                         "campos": [], "ejemplo": {"op": "capabilities"}},
        "explain": {"que_hace": "de donde sale un resultado (result_id) o una "
                                 "operacion completa (operation_id)",
                    "campos": ["result_id", "operation_id"],
                    "ejemplo": {"op": "explain", "result_id": "..."}},
        "relation": {"que_hace": "consulta aristas del dominio que una "
                                 "herramienta produjo",
                     "campos": ["clase", "nodo"],
                     "ejemplo": {"op": "relation", "clase": "writers",
                                 "nodo": "drivers/.../gfxhub_v1_0.c:223"}},
        "case": {"que_hace": "paquete de handoff: todo lo registrado para un "
                             "target, por REFERENCIAS. Sin esto, una IA que "
                             "cierra el contexto pierde todo (T8=100%)",
                 "campos": ["target", "question"],
                 "ejemplo": {"op": "case", "target": "0000:01:00.0"}},
        "ops": {"que_hace": "este catalogo", "campos": [], "ejemplo": {"op": "ops"}},
        # --- RXRE-004: el acceso a los backends -------------------------
        "backends": {"que_hace": "que backends hay, que capacidades declara "
                                 "cada uno, cuales se pueden ejecutar y por "
                                 "que las otras no",
                     "campos": [],
                     "ejemplo": {"op": "backends"}},
        "run": {"que_hace": "ejecuta UNA capacidad de reverse engineering. La "
                            "capability es un identificador cerrado y solo se "
                            "acepta si el registry la declara, tiene adapter "
                            "y esta en estado AVAILABLE o PARTIAL",
                "campos": ["capability", "artefacto", "backend_id"],
                "ejemplo": {"op": "run", "capability": "binary.inspect",
                            "artefacto": "/ruta/a/un.elf"}},
        "plan": {"que_hace": "el CAMINO hacia una capacidad SIN ejecutarlo. "
                             "Dice que pasos existen, cuales se pueden pedir "
                             "ahora y cuales no, y por que. execution siempre "
                             "vale 'not_started'",
                 "campos": ["capability", "question"],
                 "ejemplo": {"op": "plan",
                             "capability": "binary.decompile",
                             "question": "que funcion escribe este registro"}},
        "record": {"que_hace": "graba UNA entrada del estado de "
                               "investigacion: hipotesis, claim, nota, "
                               "frontera o siguiente accion. Es lo unico que "
                               "ESCRIBE razonamiento. Una interpretacion NO "
                               "es evidencia y va aqui, no en results",
                   "campos": ["kind", "text", "status", "refs", "session",
                               "target", "gap_kind"],
                   "ejemplo": {"op": "record", "kind": "hypothesis",
                               "status": "OPEN", "session": "s1",
                               "target": "0000:01:00.0",
                               "text": "VM_CONTEXT0_CNTL lo escribe el reset, "
                                       "no el resume"}},
        "checkpoint": {"que_hace": "el paquete de continuidad: que se sabe, "
                                   "que hipotesis quedan abiertas, cuales se "
                                   "refutaron, y cual es la siguiente accion. "
                                   "Para leerlo tras perder el contexto, o "
                                   "para dejarlo al final de una jornada",
                       "campos": ["session", "target"],
                       "ejemplo": {"op": "checkpoint",
                                   "session": "s1",
                                   "target": "0000:01:00.0"}},
    }


def _responder(linea: Dict[str, Any]) -> Dict[str, Any]:
    op = (linea.get("op") or linea.get("operation") or "").strip()
    if not op:
        return E.envelope("query", status=E.ST_ERROR,
                          limitations=["falta 'op' en la peticion",
                                       "operaciones: %s" % ", ".join(sorted(_ops()))])
    if op == "ops":
        # MEDIDO 2026-10-05: `envelope()` no acepta claves arbitrarias, y por
        # eso NO se le pasa `capabilities=`. `envelope` es el contrato cerrado de
        # RXRE-001 y no se le abre una puerta por comodidad. Lo que se anade va
        # en `evidence`, que ya existe para eso.
        catalogo = caps.disponibles()
        env = E.envelope("ops", status=E.ST_OK,
                         results=[{"op": k, **v} for k, v in sorted(_ops().items())],
                         evidence=[{"kind": "capacidades", "n": len(catalogo),
                                    "catalogo": catalogo}],
                         limitations=[])
        env["capabilities"] = catalogo
        return env
    if op == "capabilities":
        # Se reusa el de RXRE-001, que ya verifica por ejecucion.
        #
        # MEDIDO 2026-10-05: aqui SOLO se adjuntaba `capabilities` con el
        # catalogo cuando la peticion traia `op: capabilities`. La prueba de
        # usabilidad la recibio VACIA, y la IA se quedo sin capacidades que
        # elegir -- T1 no se cumplio. El catalogo vive en `ops`, y una IA que
        # pregunta `capabilities` no lo ve.
        #
        #     un catalogo en un sitio al que no se pregunta no es un catalogo
        #
        # Ahora `capabilities` responde con DOS COSAS que no son lo mismo y por
        # eso se separan en el envelope, no se mezclan:
        #   results[]      los SCRIPTS de tools/ y si responden  (RXRE-001)
        #   capabilities[] las INTENCIONES y sus limites        (RXRE-002)
        from commands import handlers
        env, _ = handlers.capabilities({"timeout": 300, "probe_timeout": 60})
        env["capabilities"] = caps.disponibles()
        env["evidence"] = list(env.get("evidence") or []) + [
            {"kind": "nota", "value": "results[] son SCRIPTES (tools/) y "
             "comprueban si responden. capabilities[] son INTENCIONES de "
             "investigacion (que pregunta responde cada una). No son el mismo "
             "catalogo y no se mezclan."}]
        return env
    if op == "explain":
        rid = linea.get("result_id") or ""
        oid = linea.get("operation_id") or ""
        if not rid and not oid:
            return E.envelope("explain", status=E.ST_ERROR,
                              limitations=["falta 'result_id' o 'operation_id'"])
        return Q.explain(rid, operation_id=oid)
    if op == "relation":
        return Q.relation_queries({"clase": linea.get("clase"),
                                   "nodo": linea.get("nodo")})
    if op == "case":
        # §9/§10: el paquete de handoff. Devuelve REFERENCIAS, no copias.
        return Q.case({"target": linea.get("target"),
                       "question": linea.get("question"),
                       "case_id": linea.get("case_id")})
    if op == "query":
        return Q.responder(linea)
    if op == "backends":
        # RXRE-004. Lo que responde esto es lo que una IA necesita para saber
        # si puede pedir algo, y NO necesita saber que hay un `rz-bin`.
        from backends import dispatch as D
        return _env_backends(D.listar())
    if op == "run":
        return _env_run(linea)
    if op == "plan":
        return _env_plan(linea)
    if op == "record":
        return _env_record(linea)
    if op == "checkpoint":
        return _env_checkpoint(linea)
    return E.envelope(op, status=E.ST_ERROR,
                      limitations=["operacion desconocida: %s" % op,
                                   "operaciones: %s" % ", ".join(sorted(_ops()))])


def _env_plan(linea: Dict[str, Any]) -> Dict[str, Any]:
    """El plan sin ejecutar. `execution` vale SIEMPRE `not_started`.

    MEDIDO (B6): `plan` no invoca NINGUN backend. Eso no es una economia: es lo
    que permite a una IA ver el callejon antes de recorrerlo. Un plan que
    ejecutase sus pasos seria un pipeline, y un pipeline no dice que tiene
    puertas cerradas.
    """
    from backends import dispatch as D
    cap = linea.get("capability") or ""
    p = D.planificar(cap, linea.get("question") or "")
    if p.get("status") != "ok":
        env = E.envelope("plan", status=E.ST_EMPTY, results=[],
                         limitations=[p.get("motivo", "")])
    else:
        env = E.envelope("plan", status=E.ST_OK, results=[p],
                         limitations=[])
    env["capability"] = cap
    env["execution"] = "not_started"
    env["plan"] = p.get("plan") or []
    env["resumen"] = p.get("resumen") or {}
    env["advertencia"] = p.get("advertencia") or D.ADVERTENCIA_PLAN
    env["nota"] = p.get("nota", "")
    # Y `next_actions` solo ofrece lo que el plan ha declarado ejecutable. Un
    # paso bloqueado NO se propone como accion ejecutable: RXRE-003 exige que
    # toda accion sea ejecutable o declare `available: false` con su motivo.
    acciones: List[Dict[str, Any]] = []
    for paso in env["plan"]:
        acciones.append({
            "description": "paso %d: %s" % (paso.get("orden", 0),
                                           paso.get("operation")),
            "op": "run",
            "args": {"capability": paso.get("operation")},
            "available": bool(paso.get("available")),
            **({"reason": paso.get("reason", "")} if not paso.get("available")
               else {}),
        })
    env["next_actions"] = acciones
    return env


def _env_backends(datos: Dict[str, Any]) -> Dict[str, Any]:
    """El catalogo de backends como envelope. Sin backend, la IA no puede elegir.

    MEDIDO 2026-10-05: un catalodo en un sitio al que no se pregunta no es un
    catalogo. Aqui latdocumentacion vive en `ops`, y `backends` la responde.
    """
    env = E.envelope("backends", status=E.ST_OK,
                     results=[datos],
                     evidence=[{"kind": "backends",
                                "n": len(datos.get("backends") or []),
                                "ejecutables": len(datos.get("ejecutables") or []),
                                "no_ejecutables": len(datos.get("no_ejecutables") or [])}],
                     limitations=[])
    env["backends"] = datos.get("backends") or []
    env["capacities"] = datos.get("capacidades") or {}
    env["ejecutables"] = datos.get("ejecutables") or []
    env["no_ejecutables"] = datos.get("no_ejecutables") or []
    env["reglas"] = datos.get("reglas") or {}
    env["contracto"] = datos.get("contracto") or {}
    env["decision"] = datos.get("decision") or {}
    env["recuento_real"] = datos.get("recuento_real") or {}
    env["not_verificables"] = datos.get("not_verificables") or []
    return env


def _env_run(linea: Dict[str, Any]) -> Dict[str, Any]:
    """El dispatch de una capacidad. SIEMPRE envelope, nunca excepcion.

    El estado de retorno lo decide el contrato del backend, no `envelope()`:
    `blocked` de la allow-list y `unsupported` del producer son cosas
    distintas y ambas tienen que llegar a la IA con su motivo.
    """
    from backends import dispatch as D
    cap = linea.get("capability") or ""
    res = D.ejecutar(cap, {k: linea.get(k) for k in
                           ("artefacto", "backend_id", "timeout")})
    st = res.get("status", "error")
    # `envelope` conoce cuatro estados. `unsupported`, `empty` e `invalid_input`
    # no estan entre ellos, y si los aplana a `blocked` una IA pierde la
    # distincion entre "no lo se" y "no me dejan".
    mapa = {"ok": E.ST_OK, "empty": E.ST_EMPTY, "blocked": E.ST_BLOCKED,
            "error": E.ST_ERROR, "unsupported": E.ST_BLOCKED,
            "invalid_input": E.ST_ERROR}
    # Las limitaciones son la voz del motivo. Se recogen de donde ESTE, sin
    # inventar una prioridad: el motivo del dispatch si lo hay (no se ejecuto),
    # y si se ejecuto, las del propio producer.
    lim: List[str] = []
    if res.get("motivo"):
        lim.append(res["motivo"])
    # MEDIDO (B4): el adapter devuelve `limitations` en DOS sitios. Las
    # salidas tempranas (no existe / no es ELF / faltan parametros) las ponen
    # en el nivel superior; las del producer van en `ejecucion.limitations`.
    # Leyendo solo una de las dos, los rechazos llegaban a la IA SIN MOTIVO, que
    # es un `blocked` indistinguible de un bug.
    lim.extend(res.get("limitations") or [])
    lim.extend((res.get("ejecucion") or {}).get("limitations") or [])
    for r in (res.get("results") or []):
        if isinstance(r, dict):
            lim.extend(r.get("limitations") or [])
    # MEDIDO: `envelope()` RECHAZA `empty` sin limitaciones. Un `empty` sin
    # motivo es exactamente el defecto que RXRE-001 prohibe: "vacio" no dice
    # "vacio de que". Si el producer no dio ninguna, se dice eso, que es verdad.
    if st == "empty" and not lim:
        lim.append("el backend se ejecuto y no produjo salida. Eso NO es que "
                   "el objeto no exista: es que no hubo nada. El motivo "
                   "concreto no vino del producer.")
    prov = res.get("provenance")
    env = E.envelope("run", status=mapa.get(st, E.ST_ERROR),
                     results=res.get("results") or [],
                     limitations=lim,
                     provenance=[prov] if isinstance(prov, str)
                     else (prov or None))
    env["backend_status"] = st
    env["backend_rc"] = res.get("rc")
    env["capability"] = cap
    env["ejecutada"] = bool(res.get("ejecutada"))
    env["precheck"] = res.get("precheck")
    env["ejecucion"] = res.get("ejecucion")
    env["backend_identity"] = res.get("backend")
    env["operation_id"] = res.get("operation_id")
    env["persistido"] = res.get("persistido")
    env["nota_persistencia"] = res.get("nota_persistencia")
    env["regla"] = res.get("regla")
    env["parametros"] = res.get("parametros")
    # El rc del backend viaja. §26 lo exige: un `exit 0` del producer NO es un
    # resultado, y por eso el rc se expone aunque el status ya lo diga.
    env["next_actions"] = _siguientes_tras_run(cap, res)
    return env


def _siguientes_tras_run(capability: str, res: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`next_actions` de RXRE-003: ejecutable o `available:false`, nunca adorno.

    MEDIDO 2026-10-05 (F1/F7): las acciones propuestas tienen que poder
    EJECUTARSE. Aqui una accion apunta a `op: run` con una capability real, y
    si la capability no es ejecutable la accion lo DICE en vez de fingir.
    """
    acts: List[Dict[str, Any]] = []
    rid = None
    for r in (res.get("results") or []):
        if isinstance(r, dict) and r.get("result_id"):
            rid = r["result_id"]
            break
    if rid:
        acts.append({"description": "reconstruir de donde sale este resultado",
                     "op": "explain",
                     "args": {"result_id": rid},
                     "available": True})
    acts.append({"description": "que capacidades de reverse engineering hay y "
                                "cuales se pueden pedir",
                 "op": "backends", "args": {}, "available": True})
    # Lo que NO se puede hacer se declara. `binary.decompile` tiene producer en
    # un repo clonado que no es verificable: `NOT_DETERMINED`, no `AVAILABLE`,
    # y una accion que lo prometiese seria un callejon.
    from backends import dispatch as D
    for cap in ("binary.decompile",):
        if cap in D._todas_las_fichas():
            p = D.esta_permitida(cap)
            if not p["permitida"]:
                acts.append({"description": "%s" % cap,
                             "op": "run",
                             "args": {"capability": cap},
                             "available": False,
                             "reason": p["motivo"]})
    return acts


def _ejecutables(env: Dict[str, Any]) -> Dict[str, Any]:
    """Anade `request` a cada `next_action`: la linea EXACTA que se envia.

    MEDIDO (RXRE-005, BLOCKER 1): las acciones se emitian como
    `{"op": ..., "args": {...}}`, y `args` NO lleva el `op` dentro. Enviar
    `args` tal cual da `error: falta 'op' en la peticion`:

        next_action = {"op":"query","args":{"question":"...","target":"..."}}
        enviar(args)             -> error
        enviar({"op":**args})    -> ok

    La convencion existe y es uniforme en los seis productores, pero no
    estaba DOCUMENTADA, asi que una IA que solo lee el contrato tiene que
    adivinarla. Y una accion que hay que reconstruir para poder seguirla es,
    en la practica, una accion que no se sigue.

    Por eso se anade `request`: el payload completo y enviable. `op` y `args`
    SE MANTIENEN, porque son legibles y porque los tests de RXRE-003 comprueban
    esa forma. Se anade el campo, no se cambia el contrato.

        un next_action que hay que interpretarse no es un next_action
    """
    na = env.get("next_actions")
    if not isinstance(na, list):
        return env
    for a in na:
        if not isinstance(a, dict):
            continue
        if a.get("available") is False:
            # Una accion NO disponible no se envia: se explica. Ponerle un
            # `request` seria invitar a intentar algo que ya se sabe que no.
            continue
        op = a.get("op") or a.get("action")
        args = a.get("args")
        if op and isinstance(args, dict):
            a["request"] = dict(args, op=op)
    return env


def _linea_error(op: str, limitations: List[str], request=None) -> Dict[str, Any]:
    """Envelope de error para una linea que no se pudo atender."""
    env = E.envelope(op or "query", status=E.ST_ERROR, limitations=limitations)
    env["contract_version"] = CONTRACT_VERSION
    env["engine_version"] = VERSION
    if request is not None:
        env["request_echo"] = {k: request.get(k) for k in
                               ("op", "question", "target") if k in request}
    env["next_actions"] = [{"action": "ops",
                            "why": "pedir el catalogo de operaciones validas",
                            "produces": "que pedir"}]
    return env


def main() -> int:
    """Lee JSONL de stdin, escribe un envelope por linea."""
    rc_max = 0
    for linea in sys.stdin:
        s = linea.strip()
        if not s:
            continue
        try:
            req = json.loads(s)
        except ValueError as e:
            env = _linea_error("query", ["linea no es JSON: %s" % e])
            rc_max = max(rc_max, 1)
            continue
        # MEDIDO 2026-10-05: sin este `try`, un request que violase el contrato
        # reventaba el proceso y se perdian las lineas SIGUIENTES. La propiedad
        # de JSONL de la que depende este interfaz -- una linea corrupta no
        # invalida las demas -- solo es cierta si el error se convierte en
        # envelope y el bucle sigue.
        #
        #     una linea rota no puede tumbar el lote
        try:
            env = _responder(req)
        except Exception as e:      # noqa: BLE001: aqui toda excepcion es un envelope
            env = _linea_error(str((req or {}).get("op") or "query"),
                               ["%s: %s" % (type(e).__name__, e)],
                               request=req)
        env["contract_version"] = CONTRACT_VERSION
        env["engine_version"] = VERSION
        # Un solo sitio donde se hace ejecutable una accion, para que los seis
        # productores no puedan divergir. MEDIDO: enviar `args` sin `op` da
        # `error: falta 'op'`.
        env = _ejecutables(env)
        sys.stdout.write(json.dumps(env, default=str) + "\n")
        sys.stdout.flush()
        rc = {E.ST_OK: 0, E.ST_EMPTY: 0, E.ST_BLOCKED: 2, E.ST_ERROR: 1}.get(
            env.get("status"), 1)
        rc_max = max(rc_max, rc)
    return rc_max


def _env_record(linea: Dict[str, Any]) -> Dict[str, Any]:
    """Graba una entrada de estado de investigacion. La unica op que escribe
    RAZONAMIENTO, y por eso es la que necesita mas reglas.

    MEDIDO (RXRE-005, BLOCKER 2): antes de esto no existia ninguna via por la
    que una IA pudiera dejar constancia de una hipotesis. Solo se guardaba
    EVIDENCIA (`operations`, `results`, `edges`), que es lo que un producer
    emitio. Una IA nueva sin contexto que preguntaba "que estoy investigando"
    recibia `empty`, y con ella §15 y §16 no eran implementables: el dia 2
    solo podia apoyarse en memoria conversacional, que §16 prohibe.

    Y una entrada de research NO va a `results` a proposito: `results` es lo que
    un producer emitio, con su provenance. Una hipotesis es interpretacion, y
    meterla ahi haria que un grep la encontrara como si fuera un hallazgo
    medido.
    """
    from core import store as S
    kind = linea.get("kind") or ""
    text = linea.get("text") or ""
    status = linea.get("status") or "OPEN"
    refs = linea.get("refs")
    if isinstance(refs, str):
        refs = [refs] if refs else []
    refs = refs if isinstance(refs, list) else []
    session = linea.get("session") or ""
    target = linea.get("target") or ""
    gap = linea.get("gap_kind") or ""
    c = S.conectar()
    try:
        r = S.registrar_investigacion(c, kind=kind, text=text, status=status,
                                      refs=refs, session=session,
                                      target=target, gap_kind=gap)
    finally:
        c.close()
    if r["estado"] == "ok":
        env = E.envelope("record", status=E.ST_OK, results=[r], limitations=[])
        env["recorded"] = r
        env["session"] = session
        # next_actions: el paso siguiente es leer el checkpoint, que es lo que
        # una IA necesita para poder continuar sola.
        env["next_actions"] = [
            {"description": "leer el checkpoint de esta sesion",
             "op": "checkpoint", "args": {"session": session,
                                          "target": target},
             "available": True},
        ]
        return env
    # Rechazo: el estado epistemico del RECHAZO no se pierde. Un `blocked`
    # aqui significa que la IA intento guardar algo mal formado, y tiene que
    # saber por que antes de seguir.
    env = E.envelope("record",
                     status=E.ST_BLOCKED if r["estado"] == "blocked"
                     else E.ST_ERROR,
                     results=[], limitations=[r["motivo"]])
    env["rechazo"] = r
    env["regla"] = r.get("regla", "")
    env["session"] = session
    env["next_actions"] = [
        {"description": "que se puede grabar (kind y status son listas cerradas)",
         "op": "ops", "args": {}, "available": True},
    ]
    return env


def _env_checkpoint(linea: Dict[str, Any]) -> Dict[str, Any]:
    """El paquete de §15: lo que una jornada le deja a la siguiente.

    MEDIDO (RXRE-005): las aristas del dominio se leen de `edges` (65
    medidas), NO de `relations` (0 filas). Leer la tabla equivocada daria un
    checkpoint que afirma que no hay relaciones del dominio, que es una
    conclusion FALSA de la clase que §10 prohibe.
    """
    from core import store as S
    session = linea.get("session") or ""
    target = linea.get("target") or ""
    c = S.conectar()
    try:
        ck = S.checkpoint(c, session=session, target=target)
    finally:
        c.close()
    env = E.envelope("checkpoint",
                     status=E.ST_OK if ck["estado"] == "ok" else E.ST_EMPTY,
                     results=[ck], limitations=ck["limitations"])
    env["checkpoint"] = ck
    env["session"] = session
    # El checkpoint es la respuesta a "¿qué sigue?". Se devuelve como accion
    # ejecutable, no como consejo en prosa.
    env["next_actions"] = [
        {"description": "seguir la siguiente accion registrada",
         "op": "query",
         "args": {"question": (ck.get("siguiente_accion") or {}).get("text", ""),
                  "target": target},
         "available": bool((ck.get("siguiente_accion") or {}).get("text"))},
        {"description": "que puedo investigar ahora",
         "op": "capabilities", "args": {}, "available": True},
    ]
    return env


if __name__ == "__main__":
    sys.exit(main())


