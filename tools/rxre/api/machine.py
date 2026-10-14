#!/usr/bin/env python3
"""RXRE public JSONL entry point.

Una IA que solo conoce JSONL sobre stdin/stdout puede usar RXRE sin importar
modulos internos. Esta es la unica superficie publica; todo lo demas es
implementacion.

Contrato:
- Lee JSONL de stdin (una peticion por linea)
- Escribe JSONL a stdout (una respuesta por linea)
- Cada peticion tiene un campo obligatorio "op"
- Las operaciones soportadas: backends, run, plan, explain, ops
"""

from __future__ import annotations

import json
import os
import sys

# Asegurar que el paquete rxre este en el path
HERE = os.path.dirname(os.path.abspath(__file__))
# tools/rxre/api -> tools/rxre -> tools
PKG_RXRE = os.path.abspath(os.path.join(HERE, ".."))
PKG_TOOLS = os.path.abspath(os.path.join(HERE, "..", ".."))
# El dispatch.py calcula PKG como tools/ y espera que backends sea importable.
# Como backends es un namespace package bajo rxre/, necesitamos AMBOS paths:
# - tools/ para que rxre sea namespace package
# - tools/rxre/ para que backends sea importable directamente
for p in (PKG_TOOLS, PKG_RXRE):
    if p not in sys.path:
        sys.path.insert(0, p)

# Importar desde rxre.backends y rxre.core
import rxre.backends.dispatch as dispatch  # noqa: E402
import rxre.core.store as store  # noqa: E402
from rxre.core.store import REFLEXION_OUTCOMES  # noqa: E402


def _get_db() -> store.sqlite3.Connection:
    """Obtiene conexion a la base de datos por defecto."""
    return store.conectar()


def _handle_backends(_params: dict) -> dict:
    """op: backends - Catalogo completo de backends y capacidades."""
    result = dispatch.listar()
    # Añadir status ok al nivel superior para la API publica
    # Y alias en ingles para compatibilidad con el contrato publico
    result["status"] = "ok"
    if "capacidades" in result and "capacities" not in result:
        result["capacities"] = result["capacidades"]
    return result


def _handle_run(params: dict) -> dict:
    """op: run - Ejecuta una capacidad declarada."""
    capability = params.get("capability")
    if not capability:
        return {
            "status": "blocked",
            "backend_status": "blocked",
            "backend_rc": None,
            "backend_identity": {},
            "capability": capability,
            "ejecutada": False,
            "motivo": "falta 'capability'",
            "regla": "capability es un identificador CERRADO",
            "results": [],
            "next_actions": [],
            "limitations": ["falta 'capability'"],
        }
    # Extraer parametros para la capability (todo menos 'op')
    # 'capability' se mantiene porque algunos adapters lo necesitan como parametro
    run_params = {k: v for k, v in params.items() if k != "op"}
    env = dispatch.ejecutar(capability, run_params)
    
    # Transformar la respuesta para la API publica
    # Extraer backend_status y backend_rc del adapter
    backend_status = env.get("status")
    backend_rc = None
    ejecucion = env.get("ejecucion") or {}
    if ejecucion:
        backend_rc = ejecucion.get("exit_status")
    
    # Extraer backend_identity del backend
    # MEDIDO BMS-006: algunos adapters (ej. rz_xrefs) devuelven `backend` como
    # string (el backend_id), no como dict. Normalizar para que el resto del
    # codigo — que espera un dict con backend_id, tool_version, etc. — funcione
    # sin forzar un cambio en cada adapter.
    backend_raw = env.get("backend")
    if isinstance(backend_raw, str):
        backend = {"backend_id": backend_raw}
    elif isinstance(backend_raw, dict):
        backend = backend_raw
    else:
        backend = {}
    backend_identity = {
        "backend_id": backend.get("backend_id"),
        "tool_version": backend.get("tool_version"),
        "version_verificada": backend.get("version_verificada"),
        "backend_version_status": backend.get("backend_version_status"),
        "repository": backend.get("repository"),
        "repository_commit": backend.get("repository_commit"),
    } if backend else {}
    
    # Construir next_actions con explain si hay resultados
    next_actions = env.get("next_actions") or []
    if not next_actions and env.get("results"):
        rid = (env.get("results") or [{}])[0].get("result_id")
        if rid:
            next_actions = [{
                "op": "explain",
                "args": {"result_id": rid},
                "available": True,
                "descripcion": "Reconstruir la cadena de evidencia de este resultado",
            }]
    
    # Asegurar que limitations existe (dispatch.ejecutar no siempre lo incluye en rutas de error)
    limitations = env.get("limitations") or []
    if not limitations and env.get("motivo"):
        limitations = [env.get("motivo")]
    
    # La respuesta publica incluye tanto el status del envelope como del backend
    # y todos los campos del adapter (finding_id, claim, epistemic, relaciones,
    # evidencia_validada, etc.) para que la IA pueda usarlos directamente.
    response = {
        "status": env.get("status"),
        "backend_status": backend_status,
        "backend_rc": backend_rc,
        "backend_identity": backend_identity,
        "capability": env.get("capability"),
        "ejecutada": env.get("ejecutada"),
        "motivo": env.get("motivo"),
        "regla": env.get("regla"),
        "results": env.get("results"),
        "next_actions": next_actions,
        "operation_id": env.get("operation_id"),
        "persistido": env.get("persistido"),
        "limitations": limitations,
        "precheck": env.get("precheck"),
        "ejecucion": env.get("ejecucion"),
        "backend": env.get("backend"),
        "provenance": env.get("provenance"),
    }
    # Passthrough de campos del adapter que no son genericos
    # (finding_id, claim, epistemic, evidence_ids, relaciones, etc.)
    for key in ("finding_id", "claim", "epistemic", "evidence_ids",
                "evidencia_validada", "evidencia_completa",
                "relaciones", "relation_id", "motivo_relacion",
                "hallazgos", "resultados", "plan", "blocked_reasons",
                "insufficient_evidence", "applicability", "aplicable",
                "nivel", "contrato", "encontrado", "notas",
                # MEDIDO 2026-10-14: sin esto, un agente que decompila no
                # puede distinguir "el binario no tiene funciones" de "tiene
                # 190 y se descompilaron 2". Son结论 distintas.
                "n_functions", "n_decompiladas"):
        if key in env:
            response[key] = env[key]

    # RXRE-AUTONOMY-003: BODY -> MIND -> WATER connection.
    # Cuando una operacion falla (error, timeout, blocked, invalid_input),
    # sugerir registrar una reflexion para que la IA aprenda del fallo.
    # Esto cierra el lazo de retroalimentacion: observacion -> registro ->
    # aprendizaje. La sugerencia es una next_action, no una accion automatica:
    # la IA decide si reflecciona o no, conservando el control explicito.
    status = env.get("status")
    if status in ("error", "timeout", "blocked", "invalid_input"):
        op_id = env.get("operation_id", "")
        fa = {
            "op": "reflect",
            "args": {"outcome": _outcome_from_status(status),
                     "attempt_id": op_id} if op_id else
                    {"outcome": _outcome_from_status(status)},
            "available": True,
            "descripcion": "Registrar una reflexion sobre este fallo (feedback -> reflection -> strategy)",
        }
        if fa not in next_actions:
            next_actions.append(fa)
        response["next_actions"] = next_actions
        response["reflexion_sugerida"] = {
            "outcome": _outcome_from_status(status),
            "motivo": env.get("motivo", ""),
            "sugerencia": "Usar 'op: reflect' para registrar por que fallo y "
                          "que debe cambiar en el proximo intento.",
        }
    return response


def _outcome_from_status(status: str) -> str:
    """Mapea un status de ejecucion a un outcome de reflexion."""
    m = {"error": "error", "timeout": "timeout",
         "blocked": "failure", "invalid_input": "failure"}
    return m.get(status, "failure")


def _handle_plan(params: dict) -> dict:
    """op: plan - Devuelve el plan de ejecucion SIN ejecutar."""
    capability = params.get("capability")
    question = params.get("question", "")
    if not capability:
        return {
            "status": "invalid_input",
            "capability": capability,
            "ejecutada": False,
            "motivo": "falta 'capability'",
            "results": [],
            "next_actions": [],
        }
    plan = dispatch.planificar(capability, question)
    # RXRE-AUTONOMY-003: MIND -> SOUL connection.
    # Antes de devolver el plan, consultar reflexiones previas con outcome=failure
    # para esta capability. Si existen, agregar como advertencia para que la IA
    # pueda decidir si procede o evita el approach fallido.
    c = _get_db()
    try:
        refs = store.consultar_reflexiones_para_capability(
            c, capability, outcome_filter="failure", limite=5)
    except Exception:
        refs = {"estado": "empty", "reflexiones": []}
    finally:
        c.close()
    if refs.get("reflexiones"):
        plan["reflexiones_previas"] = [{
            "outcome": r["outcome"],
            "feedback": r["feedback"],
            "reflection": r["reflection"],
            "strategy": r.get("strategy"),
            "intento": r.get("attempt_id"),
        } for r in refs["reflexiones"]]
        plan["warning"] = (
            "Hay %d reflexion(es) de fallos previos para '%s'. "
            "Revisar antes de ejecutar: " % (len(refs["reflexiones"]), capability)
        )
    # Normalizar status "no_plan" a "empty" para el contrato publico
    if plan.get("status") == "no_plan":
        plan["status"] = "empty"
        # El test espera el motivo en limitations
        motivo = plan.get("motivo", "")
        if motivo and "limitations" not in plan:
            plan["limitations"] = [motivo]
    # Asegurar que el plan tiene status ok
    if "status" not in plan:
        plan["status"] = "ok"
    # Construir next_actions a partir de los pasos ejecutables del plan
    if "next_actions" not in plan:
        next_actions = []
        for paso in plan.get("plan") or []:
            if paso.get("available"):
                next_actions.append({
                    "op": "run",
                    "args": {"capability": paso.get("capability")},
                    "available": True,
                    "descripcion": f"Ejecutar paso {paso.get('orden')}: {paso.get('capability')}",
                })
        plan["next_actions"] = next_actions
    return plan


def _handle_reflect(params: dict) -> dict:
    """op: reflect - Registra una reflexion sobre un intento.

    Inspirado en Reflexion: attempt -> feedback -> reflection -> next_attempt.
    Permite aprender de exitos y fracasos sin confundirlos con hipotesis abiertas
    (research.kind=note/claim) ni con claims (findings).

    Campos:
        feedback:    evidencia observada (lo que paso).
        reflection:  analisis causal (por que paso).
        outcome:     success | failure | timeout | error
        attempt_id:  operation_id del intento (opcional, ref a operations).
        hypothesis_id: research.id si nacio de una hipotesis (opcional).
        strategy:    sugerencia concreta para el proximo intento (opcional).
        refs:        lista de result_ids que sustentan el feedback (opcional).
        check_ejecutable: fichero.py (o fichero.py::etiqueta) que vigila esta
            leccion. Sin esto la reflexion se guarda y no se impide reincidir.
    """
    feedback = params.get("feedback", "")
    reflection = params.get("reflection", "")
    outcome = params.get("outcome", "")

    if outcome not in REFLEXION_OUTCOMES:
        return {
            "status": "invalid_input",
            "capability": "rxre.reflect",
            "ejecutada": False,
            "motivo": "outcome '%s' no es uno de: %s" % (
                outcome, ", ".join(REFLEXION_OUTCOMES)),
            "regla": "outcome es una lista CERRADA",
            "results": [],
            "next_actions": [],
            "limitations": ["outcome invalido"],
        }

    if not (feedback or "").strip():
        return {
            "status": "invalid_input",
            "capability": "rxre.reflect",
            "ejecutada": False,
            "motivo": "falta 'feedback': una reflexion sin evidencia no es trazable",
            "results": [],
            "next_actions": [],
            "limitations": ["feedback vacio"],
        }

    if not (reflection or "").strip():
        return {
            "status": "invalid_input",
            "capability": "rxre.reflect",
            "ejecutada": False,
            "motivo": "falta 'reflection': debe contener analisis causal",
            "results": [],
            "next_actions": [],
            "limitations": ["reflection vacia"],
        }

    c = _get_db()
    try:
        result = store.registrar_reflexion(
            c,
            feedback=feedback,
            reflection=reflection,
            outcome=outcome,
            attempt_id=params.get("attempt_id"),
            hypothesis_id=params.get("hypothesis_id"),
            strategy=params.get("strategy"),
            refs=params.get("refs", []),
            check_ejecutable=params.get("check_ejecutable", ""),
        )
    finally:
        c.close()

    if result.get("estado") != "ok":
        return {
            "status": "blocked",
            "capability": "rxre.reflect",
            "ejecutada": False,
            "motivo": result.get("motivo", "no se pudo registrar la reflexion"),
            "regla": result.get("regla", ""),
            "results": [],
            "next_actions": [],
            "limitations": [result.get("motivo", "")],
        }

    # Proponer como next_action: buscar reflexiones pasadas con el mismo outcome
    # para que la IA pueda aprender de experiencias similares.
    next_actions = [{
        "op": "reflect",
        "args": {"outcome": outcome},
        "available": True,
        "descripcion": "Buscar reflexiones previas con outcome=%s" % outcome,
    }]
    return {
        "status": "ok",
        "capability": "rxre.reflect",
        "ejecutada": True,
        "reflexion_id": result["reflexion_id"],
        "outcome": outcome,
        "timestamp": result.get("timestamp"),
        "nota": result.get("nota"),
        # WATER: escribir NO es aprender. Se dice explicitamente si esta
        # leccion tiene un check que la vigile, para que quien la escribe
        # sepa si deja algo que impida la reincidencia o solo un texto.
        "check_ejecutable": result.get("check_ejecutable", ""),
        "vigilada": bool(result.get("vigilada")),
        "results": [],
        "next_actions": next_actions + (
            [] if result.get("vigilada") else
            [{"op": "lessons", "args": {}, "available": True,
              "descripcion": "esta leccion no esta vigilada por ningun check; "
                             "anadele uno con el campo check_ejecutable"}]),
        "limitations": ([]
                        if result.get("vigilada") else
                        ["esta reflexion queda escrita pero SIN check ejecutable: "
                         "se recordara leyendo, no se impedira repitiendo"]),
    }


def _handle_explain(params: dict) -> dict:
    """op: explain - Reconstruye la cadena de evidencia de un resultado."""
    result_id = params.get("result_id")
    if not result_id:
        return {
            "status": "invalid_input",
            "result_id": result_id,
            "ejecutada": False,
            "motivo": "falta 'result_id'",
            "results": [],
            "next_actions": [],
        }
    c = _get_db()
    try:
        return store.explicar(c, result_id)
    finally:
        c.close()


def _handle_ops(_params: dict) -> dict:
    """op: ops - Lista las operaciones disponibles en la superficie publica."""
    operaciones = [
        {
            "op": "backends",
            "descripcion": "Catalogo de backends, capacidades, estado y reglas de la allow-list",
            "campos": [],
            "ejemplo": {"op": "backends"},
        },
        {
            "op": "run",
            "descripcion": "Ejecuta una capacidad declarada en el registry",
            "campos": ["capability", "artefacto", "backend_id", "timeout", "..."],
            "ejemplo": {"op": "run", "capability": "binary.inspect", "artefacto": "/bin/ls"},
        },
        {
            "op": "plan",
            "descripcion": "Devuelve el plan de ejecucion para una capacidad (sin ejecutar)",
            "campos": ["capability", "question"],
            "ejemplo": {"op": "plan", "capability": "binary.decompile", "question": "que funcion escribe este registro"},
        },
        {
            "op": "explain",
            "descripcion": "Reconstruye la cadena de evidencia de un resultado por su result_id",
            "campos": ["result_id"],
            "ejemplo": {"op": "explain", "result_id": "res_abc123"},
        },
        {
            "op": "ops",
            "descripcion": "Lista esta misma tabla de operaciones",
            "campos": [],
            "ejemplo": {"op": "ops"},
        },
        {
            "op": "reflect",
            "descripcion": "Registra una reflexion sobre un intento (Reflexion-style feedback loop)",
            "campos": ["feedback", "reflection", "outcome", "attempt_id",
                       "hypothesis_id", "strategy", "refs"],
            "ejemplo": {"op": "reflect", "feedback": "r2 -v produjo [ERROR]",
                        "reflection": "el flag -v no es version en r2",
                        "outcome": "failure",
                        "attempt_id": "op_abc123"},
        },
        {
            "op": "experiment",
            "descripcion": "FIRE: experimento baseline vs modified con prediccion falsable y veredicto sostenida/refutada/no_separable",
            "campos": ["capability", "question", "prediction",
                       "baseline_params", "modified_params", "comparar",
                       "esperado", "siguiente_paso", "check_ejecutable"],
            "ejemplo": {"op": "experiment",
                        "capability": "binary.inspect",
                        "question": "rizin y radare2 dan el mismo valor_hex "
                                    "de entrada?",
                        "prediction": "0x0800",
                        "comparar": "results.0.value_hex",
                        "baseline_params": {"artefacto": "/bin/ls",
                                            "backend_id": "radare2"},
                        "modified_params": {"artefacto": "/bin/ls",
                                            "backend_id": "rizin"}},
        },
        {
            "op": "lessons",
            "descripcion": "WATER: cuantas lecciones estan vigiladas por un check "
                           "ejecutable (escribir no es aprender)",
            "campos": ["ejecutar"],
            "ejemplo": {"op": "lessons", "ejecutar": True},
        },
        {
            "op": "research",
            "descripcion": "registra hypothesis|claim|note|next_action|frontier "
                           "(la entrada que le falta a AETHER: se podia "
                           "evaluar una frontera sin poder declararla)",
            "campos": ["kind", "text", "status", "target", "refs", "gap_kind"],
            "ejemplo": {"op": "research", "kind": "frontier", "status": "OPEN",
                        "target": "binary.decompile",
                        "text": "Ghidra devuelve 0 funciones para ET_REL"},
        },
        {
            "op": "saturate",
            "descripcion": "AETHER: por que se ha parado cada frontera y que "
                           "alternativa concreta seguir",
            "campos": ["frontier_id", "target", "alternativas", "reabrir",
                       "evidencia"],
            "ejemplo": {"op": "saturate", "target": "binary.cfg"},
            "ejemplo_reabrir": {"op": "saturate", "reabrir": "frontier_xxx",
                                "evidencia": "el finding que la sostenia ya no "
                                             "se reproduce con el producer actual"},
        },
    ]
    return {"status": "ok", "results": operaciones, "next_actions": []}


def _handle_experiment(params: dict) -> dict:
    """op: experiment — FIRE con prediccion falsable, no con recuento de filas.

    POR QUE SE REESCRIBE (MEDIDO 2026-10-14)
    ----------------------------------------
    La primera version de este handler comparaba `len(results)` entre los dos
    brazos y decidia:

        mas resultados -> keep    menos resultados -> reject

    Eso NO es un experimento. §48 pide un DISCRIMINANTE antes de ejecutar, y
    contar filas no separa nada que importe: un producer que devuelve 84
    nodos de CFG y otro que devuelve 85 puede ser el mismo resultado con
    ruido, o puede ser una perdida de contenido. El recuento no sabe
    distinguirlo, y aun asi emitia un veredicto con nombre ("keep",
    "reject") que un agente leeria como una conclusion.

    Un mecanismo que produce veredictos sin poder equivocarse NO es un
    mecanismo: es un generador de confianza falsa. Este lo quita.

    EL CONTRATO AHORA
    -----------------
        question     que se pregunta (obligatorio)
        prediction   que se espera, en forma falsable (OBLIGATORIO)
        capability   que se ejecuta (obligatorio)
        baseline_params / modified_params  los dos brazos
        comparar     observable a comparar: una ruta tipo
                     "results.0.value_hex" o "status"

    Y los tres resultados posibles, con sus nombres honestos:

        sostenida   el valor observado coincide con la prediccion
        refutada    difiere, y el motivo dice en que
        no_separable  los dos brazos NO se distinguen con este observable.
                     NO es un fallo: es el resultado que obliga a elegir
                     otro discriminante, y se dice.
        no_observable  el observable no existe en los brazos, o solo en uno.
                     MEDIDO y CORREGIDO: antes esto se reportaba como
                     `no_separable`, que es mentira (dos brazos "iguales"
                     porque no hay nada que comparar). Un path mal escrito no
                     puede parecerse a un experimento sin informacion.

    Sin `prediction` no se ejecuta nada. Un experimento sin prediccion
    declarada no puede refutar nada, y su resultado no informa.
    """
    def _falta(campo):
        return {
            "status": "invalid_input", "ejecutada": False,
            "motivo": "falta '%s'" % campo, "results": [],
            "next_actions": [], "limitations": [
                "sin ese campo el experimento no puede concluir nada: "
                "se describiria lo que paso sin decir que se esperaba"],
        }

    for campo in ("capability", "question", "prediction"):
        if not params.get(campo):
            return _falta(campo)

    capability = params["capability"]
    prediction = params["prediction"]
    ruta = params.get("comparar") or "status"

    def _observar(env):
        """Extrae el observable pedido. PathError si no existe."""
        cur = env
        for parte in ruta.split("."):
            if isinstance(cur, dict):
                if parte not in cur:
                    raise KeyError(parte)
                cur = cur[parte]
            elif isinstance(cur, list) and parte.isdigit():
                idx = int(parte)
                if idx >= len(cur):
                    raise IndexError(parte)
                cur = cur[idx]
            else:
                raise KeyError(parte)
        return cur

    base_env = dispatch.ejecutar(capability, params.get("baseline_params", {}))
    mod_env = dispatch.ejecutar(capability, params.get("modified_params", {}))

    try:
        base_obs = _observar(base_env)
    except (KeyError, IndexError, TypeError) as exc:
        base_obs = "<<NO EXISTE: %s>>" % exc
    try:
        mod_obs = _observar(mod_env)
    except (KeyError, IndexError, TypeError) as exc:
        mod_obs = "<<NO EXISTE: %s>>" % exc

    # MEDIDO 2026-10-14, corregido por un test: si el observable NO EXISTE en
    # ninguno de los dos brazos, la version anterior lo reportaba como
    # `no_separable` ("este observable no separa los brazos"). Es mentira:
    # ahi los dos brazos coinciden porque no hay nada que comparar. Un
    # observable mal escrito y un experimento sin informacion pareciendose es
    # exactamente el fallo que este handler existia para evitar.
    _NO_EXISTE = "<<NO EXISTE"
    if (str(base_obs).startswith(_NO_EXISTE)
            and str(mod_obs).startswith(_NO_EXISTE)):
        veredicto = "no_observable"
        motivo = ("el observable '%s' no existe en NINGUNO de los dos brazos: "
                  "el experimento no ha medido nada. Revisar la ruta (p.ej. "
                  "'results.0.value.baddr'); en `binary.inspect` `value` es un "
                  "objeto, no un entero." % ruta)
    elif str(base_obs).startswith(_NO_EXISTE) or str(mod_obs).startswith(_NO_EXISTE):
        veredicto = "no_observable"
        motivo = ("el observable '%s' existe en un brazo y no en el otro: la "
                  "comparacion no es valida (baseline=%r modified=%r)"
                  % (ruta, base_obs, mod_obs))

    # La prediccion se declara como el valor esperado del BRAZO MODIFICADO.
    elif isinstance(params.get("esperado"), str):
        esperado = params["esperado"]
        veredicto = ("sostenida" if str(mod_obs) == esperado else "refutada")
        motivo = "esperado=%r observado=%r" % (esperado, mod_obs)
    elif str(mod_obs) == str(base_obs):
        veredicto = "no_separable"
        motivo = ("los dos brazos dan el MISMO valor en '%s' (%s); este "
                  "observable no los separa, asi que el experimento no "
                  "informa" % (ruta, base_obs))
    elif str(mod_obs) == str(prediction):
        veredicto = "sostenida"
        motivo = "el brazo modificado dio exactamente la prediccion"
    else:
        veredicto = "refutada"
        motivo = ("el brazo modificado dio %r y la prediccion de comparacion "
                  "era %r" % (mod_obs, prediction))

    # FIRE cierra en MIND: el resultado del experimento entra en memoria con
    # su veredicto, para que el proximo intento lo consulte.
    c = _get_db()
    ref_id = None
    try:
        r = store.registrar_reflexion(
            c,
            feedback="EXPERIMENTO %s: baseline=%r modificado=%r (observable %s)"
                     % (capability, base_obs, mod_obs, ruta),
            reflection="Pregunta: %s. Prediccion: %s. Veredicto: %s (%s)."
                       % (params["question"], prediction, veredicto, motivo),
            outcome="success" if veredicto == "sostenida" else "failure",
            attempt_id=mod_env.get("operation_id") or None,
            strategy=params.get("siguiente_paso", ""),
            check_ejecutable=params.get("check_ejecutable", ""),
        )
        ref_id = r.get("reflexion_id")
    finally:
        c.close()

    return {
        "status": "ok",
        "ejecutada": True,
        "capability": capability,
        "experiment": {
            "question": params["question"],
            "prediction": prediction,
            "observable": ruta,
            "baseline": base_obs,
            "modified": mod_obs,
            "veredicto": veredicto,
            "motivo": motivo,
            # La limitacion que mas importa en un experimento: no se ha
            # medido N veces, y en un solo experimento los dos brazos no se
            # han entrelazado para separar el efecto del ruido.
            "replicas": 1,
        },
        "reflexion_id": ref_id,
        "next_actions": ([
            {"op": "experiment", "available": True,
             "args": {"capability": capability},
             "descripcion": "si no_separable: elige otro observable y repite; "
                            "este experimento no informo"},
        ] if veredicto in ("no_separable", "no_observable") else
            [{"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "comprobar que la leccion del experimento esta "
                             "vigilada por un check"}]),
        "limitations": [
            "replicas=1: dos brazos medidos una vez cada uno no separan el "
            "efecto del ruido. Un veredicto con una sola replica es una "
            "INDICACION, no un resultado (§75: NOCONCLUYENTE).",
            "si baseline y modified se ejecutan en momentos distintos, el "
            "tiempo es un confounder no controlado.",
        ],
    }



def _handle_lessons(params: dict) -> dict:
    """op: lessons - WATER: cuantas lecciones estan vigiladas por un check.

    MEDIDO 2026-10-14: este arbol tenia tres afirmaciones falsas en prosa que
    nadie habia ejecutado en meses. Escribir una reflexion sobre ellas no
    basta: lo que impide la reincidencia es un check que falle.

    Este op separa las tres cosas que se confunden al decir "aprendi":
      * `sin_check_detalle`         -> lecciones ESCRITAS y nada mas
      * `vigiladas`                 -> lecciones con un check que existe
      * `checks_que_no_sostienen`   -> un check que no existe, o que falla

    Con `ejecutar: true` lanza los checks. Es explicito porque cuesta tiempo
    y depende de las herramientas: no se lanzan por sorpresa.
    """
    ejecutar = bool(params.get("ejecutar"))
    c = _get_db()
    try:
        r = store.verificar_lecciones(c, ejecutar=ejecutar)
    finally:
        c.close()

    sin = r.get("sin_check", 0)
    rotas = r.get("checks_que_no_sostienen", [])
    return {
        "status": r.get("estado", "ok"),
        "ejecutada": True,
        "lecciones": {
            "total": r.get("reflexiones", 0),
            "con_check": r.get("con_check", 0),
            "sin_check": sin,
            "cobertura_pct": r.get("cobertura_pct"),
            "checks_que_no_sostienen": rotas,
            "ejecutados": ejecutar,
        },
        "vigiladas": r.get("vigiladas", []),
        "sin_check_detalle": r.get("sin_check_detalle", []),
        # La accion siguiente NO es "escribe mas reflexiones": es hacer que
        # las que ya existen dejen de depender de que alguien las lea.
        "next_actions": (
            [{"op": "reflect",
              "args": {"campo": "check_ejecutable"},
              "available": True,
              "descripcion": "reflexion sin check: anadele uno con el campo "
                             "check_ejecutable para que no dependa de que "
                             "alguien lea la nota"}] if sin else
            [{"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "ejecutar los checks y comprobar que siguen "
                             "sosteniendo lo que dicen"}]),
        "limitations": r.get("limitations", []),
    }


def _handle_research(params: dict) -> dict:
    """op: research — registra una entrada de estado de investigacion.

    POR QUE EXISTE, MEDIDO 2026-10-14 (RXRE-CAUSAL-EVOL-001)
    -------------------------------------------------------
    `store.registrar_investigacion()` existia y funcionaba, pero NADIE lo
    llamaba desde la superficie publica. Consecuencia medida: en la base real
    de RXRE hay 17 entradas en `research` (claims, hypotheses,
    next_actions) y CERO de kind='frontier'. O sea: AETHER tenia su modulo de
    saturacion entero, y `op: saturate` respondia `empty` porque no habia
    ninguna frontera que evaluar.

    No es un modulo roto: es un modulo sin entrada. Un sistema que puede
    MEDIR la saturacion pero no puede DECLARAR una frontera tiene el
    analogo pero no el termometro, y por eso nunca se entera de nada.

    Lo que hace esta op es el eslabon que faltaba, sin inventar un
    registro nuevo: escribe en `research`, que ya es donde viven las
    hipotesis, los claims, las next_actions y las fronteras, con las mismas
    validaciones (kind y status son listas cerradas; `gap_kind` solo con
    hypothesis o claim; `PROVEN` exige refs reales).
    """
    kind = params.get("kind", "")
    text = params.get("text", "")
    if not kind or not text:
        return {"status": "invalid_input", "ejecutada": False,
                "motivo": "hacen falta 'kind' y 'text'",
                "results": [], "next_actions": [],
                "limitations": [
                    "ejemplo: {\"op\":\"research\",\"kind\":\"frontier\","
                    "\"status\":\"OPEN\",\"target\":\"binary.decompile\","
                    "\"text\":\"lo que hay que resolver\"}"]}
    c = _get_db()
    try:
        r = store.registrar_investigacion(
            c, kind=kind, text=text, status=params.get("status", "OPEN"),
            refs=params.get("refs"), session=params.get("session", ""),
            target=params.get("target", ""), gap_kind=params.get("gap_kind", ""))
    finally:
        c.close()

    if r.get("estado") != "ok":
        return {"status": "blocked", "ejecutada": False,
                "motivo": r.get("motivo"), "regla": r.get("regla", ""),
                "results": [], "next_actions": [],
                "limitations": [r.get("motivo", "")]}

    siguiente = []
    if kind == "frontier":
        siguiente = [{"op": "saturate",
                      "args": {"frontier_id": r.get("id")},
                      "available": True,
                      "descripcion": "evaluar si esta frontera esta parada, "
                                     "y que alternativa tiene"}]
    return {
        "status": "ok", "ejecutada": True, "id": r.get("id"),
        "kind": kind, "estado": r.get("estado"), "timestamp": r.get("timestamp"),
        "nota": r.get("nota"),
        "results": [], "next_actions": siguiente, "limitations": [],
    }


def _handle_saturate(params: dict) -> dict:
    """op: saturate — AETHER: POR QUE se ha parado, y QUE hacer.

    MEDIDO 2026-10-14 (RXRE-CAUSAL-EVOL-001): la version anterior de esto
    evaluaba si una frontera estaba saturada y se acababa ahi. Un frontier
    sin next_actions y un frontier bloqueado por una capability no
    ejecutable recibian el mismo veredicto y, sobre todo, el mismo silencio:
    no se decia QUE hacer. Una frontera parada NO es una frontera terminada,
    y el sistema que las confunde aprende a detenerse.

    Ahora cada frontera lleva:
      * `motivo`      — el cuello de botella MEDIDO, no una etiqueta
      * `medidas`     — los numeros que lo sostienen
      * `alternativas`— acciones concretas, cada una con el OBSERVABLE que
                        distingue que funcione de que no
    Y `siguiente` dice cual se propone y por que.

    Con `reabrir: <frontier_id>` + `evidencia: <texto>` reabre una frontera
    cerrada. Sin evidencia nueva NO reabre: reabrir por ganas de mirar es
    volver a mirar lo mismo.
    """
    c = _get_db()
    try:
        reabrir = params.get("reabrir")
        if reabrir:
            r = store.reabrir_frontier(c, reabrir, params.get("evidencia", ""))
            status = "ok" if r.get("estado") == "ok" else "blocked"
            return {"status": status, "ejecutada": True,
                    "reopen": r,
                    "next_actions": [] if status == "ok" else
                    [{"op": "saturate", "args": {"evidencia": "<que cambio>"},
                      "available": True,
                      "descripcion": "reabrir necesita decir QUE evidencia "
                                     "nueva invalida lo que sostenia la "
                                     "frontera"}],
                    "limitations": []}

        r = store.evaluar_saturacion_frontier(
            c, frontier_id=params.get("frontier_id"),
            target=params.get("target", ""),
            con_alternativas=bool(params.get("alternativas", True)))
    finally:
        c.close()

    evs = r.get("frontier_evaluaciones", [])
    siguiente = r.get("siguiente")
    siguiente = siguiente or {}
    alts = siguiente.get("alternativa_elegida") or {}
    return {
        "status": r.get("estado", "ok"),
        "ejecutada": True,
        "frontier_evaluaciones": evs,
        "saturadas": [e["frontier_id"] for e in evs if e.get("saturada")],
        "paradas": [{"frontier_id": e["frontier_id"], "motivo": e["motivo"],
                     "n_alternativas": len(e.get("alternativas") or [])}
                    for e in evs if not e.get("saturada")],
        "siguiente": siguiente or None,
        # Una frontera parada con alternativas NO es un callejon: es trabajo
        # con la siguiente instruccion escrita.
        "next_actions": ([{"op": "run", "args": {}, "available": False,
                           "descripcion": alts.get("accion", "")},
                          {"op": "lessons", "args": {}, "available": True,
                           "descripcion": "la alternativa elegida tiene un "
                                          "discriminante declarado: "
                                          + (alts.get("discriminante") or "")}]
                         if alts else
                         [{"op": "saturate", "args": {"target": ""},
                           "available": True,
                           "descripcion": "ninguna frontera parada tiene "
                                          "alternativa con discriminante: "
                                          "segun el modulo, significa que "
                                          "falta una next_action, no que "
                                          "haya trabajo hecho"}]),
        "limitations": r.get("limitations", []),
    }



# Mapa de operaciones
HANDLERS = {
    "backends": _handle_backends,
    "run": _handle_run,
    "plan": _handle_plan,
    "explain": _handle_explain,
    "ops": _handle_ops,
    "reflect": _handle_reflect,
    "experiment": _handle_experiment,
    "saturate": _handle_saturate,
    "research": _handle_research,
    "lessons": _handle_lessons,
}


def procesar_linea(linea: str) -> dict:
    """Procesa una linea JSONL y devuelve la respuesta.

    MEDIDO 2026-10-14: una linea que es JSON valido pero NO es un objeto
    (un numero, una cadena, una lista, `null`) reventaba el proceso entero:

        AttributeError: 'int' object has no attribute 'get'
        File "api/machine.py", line 599, in procesar_linea
            op = req.get("op")

    Eso no es un fallo del que llegara un JSON: era un fallo del CONSUMIDOR.
    Con el patron de §26 (producer/artifact/consumer) lo que se rompe es el
    paso entero: una linea mala mataba el proceso, y con el las peticiones
    siguientes, que si eran validas.

    El caso real que lo disparo no es imaginario: `sudo -S` lee la
    contrasena de stdin, pero SOLO si la pide. Con el ticket de sudo ya
    cacheado no lee nada, y la linea de la contrasena se cuela en el stdin
    del consumidor como `123456`. Es un integer valido. Antes, eso tumbaba
    el proceso.

    Ahora: se comprueba el TIPO antes de usarlo. `null`, `[]` y `7` son
    peticiones mal formadas, no una excepcion del sistema.
    """
    try:
        req = json.loads(linea)
    except json.JSONDecodeError as e:
        return {"status": "error", "motivo": f"JSON invalido: {e}", "results": []}

    if not isinstance(req, dict):
        return {
            "status": "invalid_input",
            "motivo": "la peticion debe ser un objeto JSON con 'op'. "
                      "llego %s" % type(req).__name__,
            "tipo_recibido": type(req).__name__,
            "results": [],
            "next_actions": [],
            "limitations": [
                "una linea JSON valida que no es objeto no es una peticion: "
                "es un dato por el sitio equivocado",
            ],
        }

    op = req.get("op")
    if not op:
        return {"status": "invalid_input", "motivo": "falta 'op'", "results": []}

    handler = HANDLERS.get(op) if isinstance(op, str) else None
    if not handler:
        return {
            "status": "blocked",
            "motivo": f"operacion desconocida: '{op}'. Ops validas: {sorted(HANDLERS)}",
            "results": [],
            "next_actions": [],
        }

    try:
        return handler(req)
    except Exception as e:
        return {"status": "error", "motivo": f"excepcion en {op}: {e}", "results": []}


def main() -> None:
    """Punto de entrada: lee JSONL de stdin, escribe JSONL a stdout."""
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        resp = procesar_linea(linea)
        # Asegurar que la respuesta es serializable
        sys.stdout.write(json.dumps(resp, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()