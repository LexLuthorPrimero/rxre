#!/usr/bin/env python3
"""FASE A. Contrato REQUEST/RESPONSE para RXRE-002.

POR QUE ESTE FICHERO EXISTE Y QUE NO ROMPE.

RXRE-001 tiene un `envelope()` de RESPUESTA. Lo que no tenia era un contrato de
ENTRADA: `rxre search X` es un contrato de linea de ordenes, y una IA tiene que
saber los flags. Este modulo define el request como OBJETO, y devuelve la
respuesta con dos campos nuevos: `request` (lo que se pidio, para que la IA
pueda confirmar sin recordar) y `next_actions` (que se puede hacer con esto).

Lo que NO hace, deliberadamente:

* No crea un segundo envelope. `api/envelope.py` sigue siendo el unico formato
  de salida. Este modulo lo CONSUME y lo enriquece.
* No reinterpreta estados. `empty` sigue siendo `empty` y `blocked` sigue
  siendo `blocked`. FASE A no toca la semantica, solo la envuelve.
* No toca el CLI. El CLI de RXRE-001 sigue igual; esto es la via de maquina.

LA REGLA QUE ESTE FICHERO PROTEGE.

Una IA que recibe `status: "empty"` tiene que poder distinguir tres cosas que
se parecen y NO son lo mismo:

    la herramienta corrio y no encontro      -> empty
    la herramienta no se pudo ejecutar       -> blocked
    la herramienta no existe                 -> error

Y por encima de eso, una cuarta, que es la que este proyecto cuenta como el
defecto de su clase: **`empty` no es ausencia**. Por eso `next_actions`
nunca propone "concluir que no existe" sobre un `empty`: propone mirarlo con
otra herramienta.

    una respuesta que no dice QUE SE PUEDE HACER SIGUIENTE obliga a la IA
    a inventarlo, y ahi es donde empieza la alucinacion
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from api.envelope import ST_BLOCKED, ST_EMPTY, ST_ERROR, ST_OK, VALID_STATUS

CONTRACT_VERSION = "1.0"

#: Los campos que un request DEBE traer. `question` es obligatorio y separado
#: de `operation` a proposito: una IA puede saber la respuesta que quiere y no
#: saber todavia como se llama la operacion. `operation` es opcional cuando hay
#: `question`, y es lo que resuelve la FASE B.
CAMPOS_REQUEST = ("operation", "question", "target", "inputs", "scope",
                  "constraints", "requested_evidence")

#: Target autorizado. §31 y §32: la unica superficie sobre la que RXRE-002
#: opera. Cualquier request cuyo `target` sea otro gets `blocked`, no un error,
#: porque "no lo hago por politica" no es "lo intente y fallo".
TARGET_PERMITIDO = "0000:01:00.0"
#: La Intel. Constante nombrada para que aparezca en el codigo de la regla y no
#: solo en un comentario.
TARGET_PROHIBIDO = "0000:00:02.0"

#: Lista BLANCA. Se acepta el dominio completo del bus, la forma sin dominio, y
#: la forma corta de 8 caracteres; y SOLO el slot de la RX550 dentro de cada
#: una. El resto del bus no se reconoce y por tanto no se ejecuta.
#:
#: MEDIDO 2026-10-05: esto era una lista negra. Con lista negra, `i915`,
#: `0000:03:00.0` y `unknown` pasaban los tres.
def _blanco(slot: str) -> Dict[str, Any]:
    return {
        "pci_completo": "0000:%s" % slot,
        "pci_sin_dominio": slot,
        "pci_corto": slot[-7:],
        "alias": "rx550",
    }


TARGETS_PERMITIDOS = frozenset(_blanco("01:00.0").values())


class RequestInvalido(ValueError):
    """El request no cumple el contrato. Es un error de la IA, no del target."""


def _sha(obj: Any) -> str:
    """Hash canonico de un request. Da reproducibilidad (§16) sin depender del orden de las claves."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def construir_request(campos: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza y valida un request. Devuelve el request completo.

    No lanza por reglas de target: eso lo decide `plan()`, porque un target
    equivocado tiene que salir como `blocked` en la RESPUESTA, no como una
    excepcion. Aqui solo se valida la FORMA.
    """
    if not isinstance(campos, dict):
        raise RequestInvalido("el request tiene que ser un objeto, no %s"
                              % type(campos).__name__)
    faltan = [c for c in ("operation", "question")
              if not campos.get(c) and campos.get("capability") is None]
    # `operation` y `question` no son ambos obligatorios: la IA puede dar uno.
    # Pero al menos uno tiene que estar, o no hay nada que hacer.
    if not campos.get("operation") and not campos.get("question"):
        raise RequestInvalido(
            "hace falta al menos uno de: 'operation' (que ejecutar) o "
            "'question' (que quieres saber). Campos del contrato: %s"
            % ", ".join(CAMPOS_REQUEST))

    r: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "operation": campos.get("operation") or "",
        "question": campos.get("question") or "",
        "capability": campos.get("capability") or "",
        "target": campos.get("target") or TARGET_PERMITIDO,
        "inputs": dict(campos.get("inputs") or {}),
        "scope": campos.get("scope") or "linux-7.1.3",
        "constraints": dict(campos.get("constraints") or {}),
        "requested_evidence": bool(campos.get("requested_evidence", True)),
        "timestamp": campos.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    # El objetivo tambien puede venir dentro de `inputs`, que es como lo
    # escribiria una IA que ya conoce la forma de RXRE-001. Se acepta desde ahi
    # y no se obliga a la forma nueva.
    if not campos.get("target") and r["inputs"].get("target"):
        r["target"] = r["inputs"]["target"]
    r["request_id"] = "req_" + _sha({k: r[k] for k in
                                     ("operation", "question", "capability",
                                      "target", "inputs", "scope")})
    return r


def target_permitido(target: str) -> bool:
    """§17/§32. Lista BLANCA, no negra.

    MEDIDO 2026-10-05: esto era una lista negra que rechazaba solo
    `0000:00:02.0`, `0000:02.0` y `02.0`. Con lista negra, TODO lo demas pasaba:

        'i915'              -> True
        '0000:03:00.0'      -> True    (otro dispositivo del bus)
        'unknown'           -> True
        'GPU'               -> True
        ''                  -> True

    Una lista negra concede por omision, y concede a la Intel en cuanto se
    escribe su nombre de otra forma. RXRE-003 §17 pide exactamente lo que hacia
    falta:

        RX550           -> permitido
        Intel           -> blocked
        target ambiguo  -> blocked

    Asi que la pregunta no es `¿es el prohibido?` sino `¿es el permitido?`, y
    todo lo que no se puede identificar como la RX550 se bloquea. Es la
    diferencia entre una puerta con una lista deEaqui y una con una lista de
    los que pueden entrar.

    Que RXRE no lea hardware no hace inocuo el error: el target viaja en el
    request, y una IA que lo pase mal tiene que ver `blocked`, no `ok` con
    resultados de la RX550. Un `target` que no se reconoce tambien se bloquea,
    porque "no se de que me hablas" y "es la RX550" no son la misma respuesta.
    """
    t = (target or "").strip().lower()
    if not t:
        return False
    return t in TARGETS_PERMITIDOS


#: Acciones que RXRE sabe EJECUTAR. Un `next_action` que no esta aqui no se
#: propone como paso: se propone como `available: false`, o no se propone.
#:
#: MEDIDO 2026-10-05 (prueba de usabilidad, T4=50%): de las acciones que
#: `next_actions` proponia, SIETE de diez NO eran operaciones invocables.
#: `provenance`, `cross_check`, `widen_scope`, `read_blocked_reason` y
#: `relations` no existian como `op`, y una IA que las siguiera se encontraba un
#: `error: operacion desconocida` en un callejon sin salida.
#:
#:     un siguiente paso que no se puede ejecutar es una trampa, no un paso
#:
#: Cada accion lleva la forma que RXRE-003 §8 exige: operacion, argumentos,
#: resultado esperado, criterio de exito y criterio de stop.
_ACCIONES: Dict[str, Dict[str, Any]] = {
    "explain": {
        "op": "explain", "args_requiere": ["result_id"],
        "por_que": "cada resultado lleva result_id y su procedencia es "
                   "consultable sin volver a ejecutar la herramienta",
    },
    "explain_operation": {
        "op": "explain", "args_requiere": ["operation_id"],
        "por_que": "la cadena completa de la operacion, para reproducirla o "
                   "entender que se hizo",
    },
    "relations_writers": {
        "op": "relation", "args_requiere": ["nodo"],
        "args_fijos": {"clase": "writers"},
        "por_que": "las relaciones de un hallazgo suelen estar en otra "
                   "herramienta; esta consulta lo que YA produjo otra",
    },
    "cross_check_readers": {
        "op": "query",
        "args_requiere": ["target"],
        "args_fijos": {"capability": "register.readers"},
        "por_que": "la herramienta corrio y no encontro. Falta un SEGUNDO "
                   "metodo antes de decir que no esta: este es el contrario",
    },
    "cross_check_uses": {
        "op": "query",
        "args_requiere": ["target"],
        # MEDIDO (RXRE-005): estas dos piden el OBJETO (un registro), no el
        # dispositivo. Sin marcarlo, `target` significa lo contrario y la accion
        # se rechaza. El simbolo va en `inputs`, el dispositivo en la raiz.
        "args_target_es_objeto": True,
        "args_fijos": {"capability": "register.uses"},
        "por_que": "segunda via al mismo objeto, por uso en el codigo en vez "
                   "de por definicion de offset",
    },
    "widen_scope": {
        "op": "query",
        "args_requiere": ["target"],
        "args_target_es_objeto": True,
        "args_fijos": {"capability": "register.uses", "root": "widen"},
        "por_que": "puede que el universo declarado no contenga el objeto. "
                   "Cambiar el universo es el unico modo de distinguir 'no esta' "
                   "de 'no mire donde toca'",
    },
    "capabilities": {
        "op": "capabilities", "args_requiere": [],
        "por_que": "comprobar que la capacidad existe y responde antes de "
                   "reintentar",
    },
    "ops": {
        "op": "ops", "args_requiere": [],
        "por_que": "el catalogo de operaciones, con ejemplo cada una",
    },
    "leer_limitaciones": {
        "op": None, "args_requiere": [],
        "por_que": "no se ejecuto. Un blocked NO es un empty y no admite "
                   "conclusion sobre el hardware. La razon YA esta en "
                   "`limitations` de esta misma respuesta",
    },
}


def _accion(nombre: str, request: Dict[str, Any], contexto: Dict[str, Any]
            ) -> Dict[str, Any]:
    """Construye una accion EJECUTABLE con sus argumentos resueltos.

    MEDIDO (RXRE-005): estas acciones NO eran ejecutables, y el motivo es una
    colision de significado en la MISMA clave `target`:

        `target` en la raiz de un request  =  el DISPOSITIVO (0000:01:00.0)
        `inputs.target`                    =  el OBJETO (el simbolo)

    `responder()` rellena `inputs["target"]` con el objetivo extraido del
    enunciado -- un nombre de registro -- y `_accion` lo copiaba a la raiz del
    request siguiente. Alli `target_permitido()` lo leia como un dispositivo y
    lo rechazaba:

        {"op":"query","args":{"target":"VM_CONTEXT0_CNTL", ...}}
          -> blocked: target fuera del alcance de RXRE-002

    Es decir: RXRE proponia una accion que el propio RXRE rechazaba de forma
    determinista. Una accion propuesta que no se puede ejecutar no es una
    accion, y medirlo fue lo que lo delato (no leerlo: el codigo parecia
    razonable, porque `ins.get("target")` era de verdad el simbolo).

    LA REPARACION: la accion lleva el DISPOSITIVO en la raiz y el OBJETO en
    `inputs`. MEDIDO que esa forma responde `ok` con 36 resultados, donde la
    forma anterior respondia `blocked`. Y se conservan `op` y `args`, porque
    los tests de RXRE-003 comprueban esa forma.
    """
    esp = _ACCIONES[nombre]
    ins = request.get("inputs") or {}
    rid = contexto.get("result_id")
    opid = contexto.get("operation_id")
    nodo = contexto.get("nodo")
    # OBJETO: lo que se esta investigando. Vive en `inputs`, no en la raiz.
    objetivo = ins.get("target") or ins.get("register_name") \
        or ins.get("symbol_name") or ins.get("query") or ""
    # DISPOSITIVO: lo que hay en la raiz del request original.
    tgt = request.get("target") or ""

    args: Dict[str, Any] = {}
    faltan: List[str] = []
    for req in esp.get("args_requiere", []):
        # `target` significa OBJETO dentro de `inputs` y DISPOSITIVO en la raiz.
        # Cada consumidor de la tabla `_ACCIONES` dice cual de los dos quiere.
        if req == "target":
            val = objetivo if esp.get("args_target_es_objeto") else tgt
        else:
            val = {"result_id": rid, "operation_id": opid,
                   "nodo": nodo}.get(req)
        if val:
            args[req] = val
        else:
            faltan.append(req)
    args.update(esp.get("args_fijos", {}))
    if args.get("root") == "widen":
        args["root"] = "working=RESEARCH/working/linux-7.1.3"

    # MEDIDO (RXRE-005): si la accion pide el OBJETO, ese objeto NO puede ir en
    # la raiz del request siguiente, porque ahi `target` es el dispositivo. Va
    # en `inputs`, que es donde `responder()` lo lee. Y la raiz lleva el
    # dispositivo original, para que la allow-list lo acepte.
    if esp.get("args_target_es_objeto") and objetivo:
        args = {k: v for k, v in args.items() if k != "target"}
        args["inputs"] = dict(args.get("inputs") or {})
        args["inputs"]["target"] = objetivo
        args["question"] = request.get("question", "")
        # Y el DISPOSITIVO tiene que ir en la raiz. MEDIDO: si la raiz no lleva
        # `target`, la normalizacion de `request.py` PROMUEVE
        # `inputs.target` (el simbolo) a la raiz, y `target_permitido` vuelve a
        # rechazarlo. Por eso las dos mitades viajan: objeto en `inputs`,
        # dispositivo en la raiz. Sin las dos, `blocked`.
        if tgt:
            args["target"] = tgt

    ejecutable = esp["op"] is not None and not faltan
    a: Dict[str, Any] = {
        "action": nombre,
        "available": ejecutable,
        "why": esp["por_que"],
        "produces": {
            "explain": "de donde salio cada dato",
            "explain_operation": "la cadena de la operacion",
            "relations_writers": "aristas WRITES ya producidas",
            "cross_check_readers": "una segunda via sobre el mismo objeto",
            "cross_check_uses": "usos en el codigo en vez de definicion",
            "widen_scope": "mas cobertura del universo",
            "capabilities": "que capacidades responden de verdad",
            "ops": "el catalogo de operaciones",
            "leer_limitaciones": "nada: ya esta en limitations",
        }.get(nombre, "avance en la investigacion"),
    }
    if ejecutable:
        a["op"] = esp["op"]
        a["args"] = args
        a["expected"] = "un envelope con status y results"
        a["success"] = ("status distinto del actual, o result_ids distintos")
        a["stop"] = ("si vuelve a salir el mismo status con los mismos "
                     "result_ids, la via esta agotada: cambia de capacidad")
    else:
        a["op"] = None
        if faltan:
            a["why"] += " (no se puede ejecutar: falta %s)" % ", ".join(faltan)
    return a


def next_actions(estado: str, request: Dict[str, Any],
                 resultados: int, contexto: Optional[Dict[str, Any]] = None
                 ) -> List[Dict[str, Any]]:
    """Que se puede hacer con ESTA respuesta.

    REGLA UNICA, y es la que mas dinero cuesta si no se cumple:

        NINGUN siguiente paso se propone si no se puede ejecutar

    MEDIDO 2026-10-05: antes esta funcion devolvia nombres de accion sin op ni
    argumentos -- `provenance`, `cross_check`, `widen_scope`,
    `read_blocked_reason`, `relations` -- y ninguno era invocable. Una IA que
    los siguiera recibia `error: operacion desconocida`. T4 de la prueba de
    usabilidad era 50%.

    Ahora cada accion lleva `op` y `args` reales, o `available: false` con el
    motivo. No hay paso a ciegas.
    """
    ctx = dict(contexto or {})
    ops: List[Dict[str, Any]] = []
    tgt = (request.get("inputs") or {}).get("target") or ""

    if estado == ST_OK:
        ops.append(_accion("explain", request, ctx))
        if ctx.get("operation_id"):
            ops.append(_accion("explain_operation", request, ctx))
        if ctx.get("nodo"):
            ops.append(_accion("relations_writers", request, ctx))
        if tgt and request.get("requested_evidence", True):
            ops.append(_accion("cross_check_uses", request, ctx))
    elif estado == ST_EMPTY:
        # Aqui se gana o se pierde la honestidad: un `empty` ofrece MIRAR OTRO
        # LADO, nunca CONCLUIR. Y ahora ademas se puede hacer.
        if tgt:
            ops.append(_accion("cross_check_readers", request, ctx))
            ops.append(_accion("widen_scope", request, ctx))
        ops.append(_accion("leer_limitaciones", request, ctx))
    elif estado == ST_BLOCKED:
        ops.append(_accion("leer_limitaciones", request, ctx))
        ops.append(_accion("capabilities", request, ctx))
    else:  # ST_ERROR
        ops.append(_accion("capabilities", request, ctx))
        ops.append(_accion("ops", request, ctx))
    return ops


def envolver(request: Dict[str, Any], env: Dict[str, Any],
             extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """ Enriquece un envelope de RXRE-001 con el contrato de RXRE-002.

    NO cambia `status` ni `results`. Solo anade `request`, `next_actions` y lo
    que venga en `extras`. La semantica de RXRE-001 se preserva entera, que es
    el requisito de no rehacer lo que ya funciona.

    MEDIDO 2026-10-05: el contexto de las acciones se toma del envelope, porque
    `result_id`, `operation_id` y el nodo de una arista SOLO existen ahi. Sin
    pasarlos, `next_actions` no puede construir los argumentos de `explain` y de
    `relation`, y退回 a proponer acciones sin ejecutar -- que es el defecto que
    esta iteracion repara.
    """
    env = dict(env)
    env["contract_version"] = CONTRACT_VERSION
    env["request"] = {k: request.get(k) for k in
                      ("request_id", "operation", "question", "capability",
                       "target", "scope", "inputs", "constraints")}
    ctx: Dict[str, Any] = {"operation_id": env.get("operation_id")}
    _res = env.get("results") or []
    if _res and isinstance(_res[0], dict):
        ctx["result_id"] = _res[0].get("result_id")
    _aristas = env.get("aristas") or []
    for _a in _aristas:
        if isinstance(_a, dict) and _a.get("tipo") == "WRITES":
            ctx["nodo"] = _a.get("src")
            break
    env["next_actions"] = next_actions(env.get("status", ST_ERROR), request,
                                       len(_res), ctx)
    if extras:
        env.update(extras)
    if env.get("status") not in VALID_STATUS:
        env["status"] = ST_ERROR
    return env
