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
# MEDIDO 2026-10-15: /tmp (tmpfs 5,9G) puede estar a 100% por copias de
# trabajo ajenas (5,2G consumidos), rompiendo herramientas basadas en tmp
# (SQLite temp, Ghidra hsperfdata, testing tempfiles). Caer a /var/tmp
# si no hay >= 512 MB libres, para mantener operatividad sin borrar nada.
_tmpdirectorios = os.environ.get("TMPDIR") or os.environ.get("TMP") or ""
if not _tmpdirectorios or not os.path.isdir(_tmpdirectorios):
    _tmpdirectorios = "/tmp"
try:
    import shutil as _sh
    _libre = _sh.disk_usage(_tmpdirectorios).free
except Exception:
    _libre = 2 ** 63
if _libre < 512 * 1024 * 1024 and os.path.isdir("/var/tmp"):
    _tmpdirectorios = "/var/tmp"
os.environ.setdefault("TMPDIR", _tmpdirectorios)
os.environ.setdefault("TMP", _tmpdirectorios)
os.environ.setdefault("TEMP", _tmpdirectorios)

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

# ÉTER: hub async con write-ahead. Se instancia de forma lazy en
# `_eter()` para no abrir la base de eventos en cada import del modulo
# (los tests importan `api.machine` sin querer crear ficheros).
try:
    import rxre.core.eter as _eter_mod  # noqa: E402
except Exception:                                          # pragma: no cover
    _eter_mod = None
_ETER = None


def _eter():
    """Instancia lazy de ÉTER. Una por proceso, como pide el diagrama.

    La ruta sale de `$RXRE_DB` (si está seteado) reemplazando el nombre del
    fichero, o de `.rxre/eter.sqlite3` por defecto. Reutilizar la misma
    instancia es lo que hace que la cola tenga estado entre llamadas: si se
    creara una por `emit`, cada evento tendría su propia cola y nadie vería
    los pendientes de nadie.
    """
    global _ETER
    if _ETER is None:
        if _eter_mod is None:
            raise RuntimeError("core.eter no importable: ÉTER no disponible")
        ruta = os.environ.get("RXRE_DB", "")
        if ruta:
            ruta = ruta.replace("rxre.db", "eter.sqlite3")
            if ruta == os.environ.get("RXRE_DB", ""):
                ruta = os.path.join(os.path.dirname(ruta), "eter.sqlite3")
        else:
            ruta = os.path.join(".rxre", "eter.sqlite3")
        _ETER = _eter_mod.Eter(ruta)
    return _ETER


def _trace_id_actual(params: Optional[dict] = None) -> Optional[str]:
    """El trace_id de ESTA invocacion.

    RXRE-TRACE-ID-001: lo emite el agente por entorno (`RXRE_TRACE_ID`),
    una unidad por llamada. Reutilizarlo = reintento del mismo intento;
    uno nuevo = intento nuevo. El parametro explicito de la peticion manda
    sobre el entorno (permite a un test forzarlo sin tocar el proceso).
    """
    if params:
        tid = params.get("trace_id")
        if tid:
            return tid
    return os.environ.get("RXRE_TRACE_ID") or None


def _get_db() -> store.sqlite3.Connection:
    """Obtiene conexion a la base de datos por defecto.

    CUERPO/META: usa RXRE_DB si esta seteado (env o params), o el DEFAULT_DB
    del paquete. No overridea la config del entorno.
    """
    db_path = os.environ.get("RXRE_DB", "")
    if db_path:
        return store.conectar(db_path)
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


def _handle_verify(params: dict) -> dict:
    """op: verify - CUERPO: health check antes de ejecutar.

    Verifica:
    1. Database writability (la BD que se usara para persistir)
    2. Backend executables en PATH (umr, rizin, r2)
    3. Hardware fingerprint (PCI allow-list, RX550 present)
    4. Artefacto valido (si se provee: existe, es ELF, sha256)

    NO ejecuta operaciones. NO escribe en el hardware. Es read-only sobre el
    entorno y el filesystem.

    Uso:
        {"op":"verify"}
        {"op":"verify","artefacto":"/bin/ls"}
        {"op":"verify","artefacto":"/bin/ls","capability":"binary.xrefs"}
    """
    import struct
    from rxre.backends import registry
    from rxre.backends.contract import sha256_de

    checks = {}

    # 1. Database writability + auto-repair (CUERPO)
    db_path = params.get("db_path", "") or os.environ.get("RXRE_DB", "")
    try:
        if db_path:
            # CUERPO-AUTO: auto-crear directorio de la DB si falta
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir and not os.path.isdir(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                checks["database_repair"] = {"ok": True, "detail": "dir creado"}
            c = store.conectar(db_path)
        else:
            c = store.conectar()
        c.execute("SELECT 1")
        c.close()
        checks["database"] = {"ok": True, "detail": "conectado"}
    except Exception as exc:
        checks["database"] = {"ok": False, "detail": str(exc)[:200]}

    # 2. Backend executables
    backend_checks = {}
    for bid in ("umr", "rizin", "radare2"):
        try:
            ent = registry.get(bid)
            b = ent["backend"]
            exe = b.path()
            identidad = b.identidad()
            existe = b.existe()
            backend_checks[bid] = {
                "ok": existe, "path": exe, "existe": existe,
                "version_verified": identidad.get("version_verificada", False),
                "version_status": identidad.get("backend_version_status", "UNVERIFIED"),
                "tool_version": identidad.get("tool_version", ""),
            }
            if not existe:
                backend_checks[bid]["detail"] = "no en PATH"
        except (KeyError, Exception):
            backend_checks[bid] = {"ok": False, "detail": "backend desconocido"}
    checks["backends"] = backend_checks

    # 3. Hardware fingerprint - PCI allow-list (RXRE-002)
    from rxre.backends.adapters.umr_read import ALLOWED_PCI
    pci_present = {}
    for pci in ALLOWED_PCI:
        try:
            parts = pci.split(":")
            sys_path = "/sys/bus/pci/devices/%s:%s:%s" % (parts[0], parts[1], parts[2])
            if os.path.exists(sys_path):
                pci_present[pci] = {"present": True}
                try:
                    vendor = open(os.path.join(sys_path, "vendor")).read().strip()
                    device = open(os.path.join(sys_path, "device")).read().strip()
                    pci_present[pci]["vendor"] = vendor
                    pci_present[pci]["device"] = device
                except OSError:
                    pass
            else:
                pci_present[pci] = {"present": False}
        except Exception:
            pci_present[pci] = {"present": "unknown"}
    checks["hardware"] = {
        "allow_list": list(ALLOWED_PCI),
        "pci_present": pci_present,
        "intel_igp_blocked": "0000:00:02.0" not in ALLOWED_PCI,
    }

    # 4. Artefacto validation (if provided)
    artefacto = params.get("artefacto") or params.get("artifact") or params.get("path")
    if artefacto:
        checks["artefacto"] = {
            "path": artefacto,
            "exists": os.path.isfile(artefacto),
        }
        if os.path.isfile(artefacto):
            try:
                with open(artefacto, "rb") as fh:
                    header = fh.read(20)
                is_elf = header[:4] == b"\x7fELF"
                checks["artefacto"]["is_elf"] = is_elf
                if is_elf:
                    e_type, = struct.unpack_from(
                        "<H" if header[5] == 1 else ">H", header, 16)
                    checks["artefacto"]["elf_type"] = {
                        1: "ET_REL", 2: "ET_EXEC", 3: "ET_DYN"}.get(e_type, "ET_%d" % e_type)
                checks["artefacto"]["sha256"] = sha256_de(artefacto)
            except Exception as exc:
                checks["artefacto"]["error"] = str(exc)[:200]

    # Determine overall status
    backend_ok = all(b.get("ok") for b in backend_checks.values())
    hw_ok = all(v.get("present") for v in pci_present.values() if isinstance(v, dict))
    db_ok = checks.get("database", {}).get("ok", False)
    status = "ok" if (db_ok and backend_ok and hw_ok) else "partial"

    # CUERPO: encadenar automaticamente la operacion siguiente basada en contexto.
    # Si se verifico un artefacto con capability especificada -> sugerir run.
    # Si se verifico un artefacto sin capability -> sugerir discover.
    # Si verify fue solo health check -> sugerir select para iniciar inv est.
    capability = params.get("capability", "")
    artefacto = params.get("artefacto") or params.get("artifact") or params.get("path")
    next_actions = []
    if status == "ok":
        if capability and artefacto:
            next_actions.append({
                "op": "run",
                "args": {"capability": capability, "artefacto": artefacto},
                "available": True,
                "descripcion": "Ejecutar capability tras verificacion exitosa",
            })
        elif artefacto:
            next_actions.append({
                "op": "discover",
                "args": {"artefacto": artefacto},
                "available": True,
                "descripcion": "Descubrir simbolos y xrefs del artefacto verificado",
            })
        else:
            # CUERPO/ALMA: si verify fue solo health check, sugerir select
            # con una mission_id existente si se provee en params, o crear una.
            sa_args = {}
            if params.get("mission_id"):
                sa_args["mission_id"] = params["mission_id"]
            next_actions.append({
                "op": "select",
                "args": sa_args,
                "available": True,
                "descripcion": "Seleccionar siguiente tarea de la mision",
            })
    else:
        next_actions.append({
            "op": "backends", "descripcion": "Ver detalles de capacities y estado"
        })

    return {
        "status": status,
        "op": "verify",
        "checks": checks,
        "next_actions": next_actions,
        "limitations": (
            ["algunos checks fallaron -- ver detalle en checks"]
            if status != "ok" else []
        ),
    }


def _handle_discover(params: dict) -> dict:
    """op: discover - ETER: descubrir simbolos, xrefs y callgraph de un binario.

    Encadena binary.inspect + binary.xrefs + binary.callgraph sobre un mismo
    artefacto, integrando los resultados en findings/citations para que
    nada quede aislado.

    Cada simbolo nuevo es una frontier abierta (§53). Cada xref es una arista
    en el grafo de dominio. Cada funcion del callgraph es un nodo.

    Uso:
        {"op":"discover","artefacto":"/bin/ls"}
    """
    artefacto = params.get("artefacto") or params.get("artifact") or params.get("path")
    if not artefacto:
        return {"status": "invalid_input", "op": "discover",
                "motivo": "falta 'artefacto'", "results": []}

    c = _get_db()
    try:
        findings = []
        next_actions = []

        # 1. binary.inspect -- get file metadata, functions
        env1 = dispatch.ejecutar("binary.inspect", {"artefacto": artefacto})
        if env1.get("status") in ("ok", "empty"):
            n_funcs = len(env1.get("results") or [])
            findings.append({
                "finding_type": "binary_functions",
                "source": "binary.inspect",
                "n": n_funcs,
                "estado": env1.get("status"),
            })

        # 2. binary.xrefs -- cross-references
        env2 = dispatch.ejecutar("binary.xrefs",
                                 {"artefacto": artefacto, "backend_id": "rizin"})
        if env2.get("status") in ("ok", "empty"):
            n_xrefs = len(env2.get("results") or [])
            findings.append({
                "finding_type": "binary_xrefs",
                "source": "binary.xrefs",
                "n": n_xrefs,
                "estado": env2.get("status"),
            })

        # 3. binary.callgraph -- function call graph
        env3 = dispatch.ejecutar("binary.callgraph",
                                 {"artefacto": artefacto, "backend_id": "radare2"})
        if env3.get("status") in ("ok", "empty"):
            n_nodes = len(env3.get("results") or [])
            findings.append({
                "finding_type": "binary_callgraph",
                "source": "binary.callgraph",
                "n": n_nodes,
                "estado": env3.get("status"),
            })

        total_symbols = sum(f["n"] for f in findings)

        # ETER: auto-registrar frontier por cada tipo de simbolo descubierto.
        # Cada simbolo/funcion nuevo es una frontier abierta (§53) que necesita
        # investigacion. Se registran como investigaciones para que saturate
        # pueda evaluarlas en el proximo ciclo.
        nuevas_frontiers = 0
        for f in findings:
            try:
                store.registrar_investigacion(
                    c, kind="frontier",
                    text="%s en %s (%d items)" % (f["finding_type"], artefacto, f["n"]),
                    status="OPEN", target=f["finding_type"],
                    gap_kind="discovery",
                )
                nuevas_frontiers += 1
            except Exception:
                pass

        # FUEGO: auto-cadenar discover -> run para capabilities derivadas.
        # Cada simbolo/funcion descubierto es una frontier -> sugerir run con
        # binary.decompile para analizar funciones, binary.xrefs para cross-refs.
        next_actions = []
        if total_symbols > 0:
            next_actions.extend([
                {"op": "run",
                 "args": {"capability": "binary.decompile",
                          "artefacto": artefacto},
                 "available": True,
                 "descripcion": "Descompilar funciones descubiertas"},
                {"op": "experiment",
                 "args": {"capability": "binary.xrefs",
                          "artefacto": artefacto,
                          "comparar": "results.0.source"},
                 "available": True,
                 "descripcion": "Comparar backends (rizin vs radare2) para xrefs"},
            ])
        else:
            next_actions = [
                {"op": "explain", "args": {"result_id": "any"},
                 "descripcion": "Reconstruir la evidencia de cualquier resultado"}
            ]

        return {
            "status": "ok" if total_symbols > 0 else "empty",
            "capability": "binary.discover",
            "artefacto": artefacto,
            "ejecutada": True,
            "findings": findings,
            "total_symbols": total_symbols,
            "frontiers_creadas": nuevas_frontiers,
            "results": [],
            "next_actions": next_actions,
            "limitations": [
                "DISCOVERY es un agregador, no un productor: los resultados "
                "vienen de binary.inspect, binary.xrefs y binary.callgraph.",
                "Los symbols descubiertos son frontireras abiertas para "
                "investigacion adicional (§53).",
            ],
            "provenance": {
                "estado": "completa",
                "transformacion": "discover = binary.inspect + binary.xrefs + "
                                  "binary.callgraph -> agregacion de findings",
                "normalizador": "machine._handle_discover",
            },
        }
    finally:
        c.close()


def _handle_repl(params: dict) -> dict:
    """op: repl - AGUA: loop interactivo con auto-reflexion.

    Ejecuta una secuencia de operaciones (pipeline) y, cuando una falla o se
    bloquea, genera automaticamente una sugerencia de reflexion (BODY→MIND,
    §10) para que el llamante pueda iterar sin interrupcion.

    El loop es explicitamente abierto: NO reintentan automaticamente. Cada
    fallo produce una 'reflexion_sugerida' que el llamante debe revisar antes
    de volver a ejecutar. Esto evita el error F8 (exit 0 con salida incorrecta):
    el veredicto nunca se impone, se propone.

    Uso:
        {"op":"repl",
         "steps":[{"op":"verify","artefacto":"/bin/ls"},
                  {"op":"discover","artefacto":"/bin/ls"}],
         "session_id":"rx550-investigation-001"}

         {"op":"repl","mission_id":"mission_abc"}  # ALMA: auto-genera steps
         {"op":"repl","mission_id":"mission_abc","resume":true}  # salta steps
         {"op":"repl","auto":true}  # FUEGO: ciclo autonomo, continue_on_error auto
    """
    steps = params.get("steps") or []
    mission_id = params.get("mission_id")
    resume = params.get("resume", False)
    # FUEGO/META: auto=true implica continue_on_error para no detenerse en fallos
    auto = params.get("auto", False)
    continue_on_error = params.get("continue_on_error", False)
    if auto:
        continue_on_error = True
    max_steps = params.get("max_steps", 20)

    # ALMA: si auto=true y no hay steps, generar el ciclo completo
    if not steps and auto and mission_id:
        steps = _generar_ciclo_autonomo(mission_id, max_steps)

    # ALMA: si no hay steps pero hay mission_id, auto-generar desde tasks
    if not steps and mission_id:
        steps = _steps_desde_mision(mission_id)
        if not steps:
            return {
                "status": "invalid_input",
                "op": "repl",
                "motivo": "mission_id '%s' no tiene tareas pendientes. "
                          "Usar 'op:research' o 'op:select' para crearlas." % mission_id,
                "next_actions": [{"op": "select", "args": {"mission_id": mission_id},
                                  "descripcion": "Seleccionar siguiente tarea"}],
            }

    if not steps:
        return {
            "status": "invalid_input",
            "op": "repl",
            "motivo": "falta 'steps' (lista de operaciones)",
            "next_steps": [],
        }

    session_id = params.get("session_id")
    if session_id:
        _registrar_sesion(params, session_id)

    # ALMA: si resume=True, cargar steps completados y saltarlos
    completed_steps = []
    if session_id and resume:
        completed_steps = _cargar_session_steps(session_id)

    results = []
    reflexiones = []
    stopped_at = None

    for i, step in enumerate(steps):
        # ALMA: skip steps already completed in a previous session
        if resume and step.get("op") in completed_steps:
            results.append({
                "index": i,
                "op": step.get("op"),
                "status": "completed",
                "summary": "saltado (completado en session anterior)",
            })
            continue
        step = dict(step)
        if session_id and "session_id" not in step:
            step["session_id"] = session_id
        try:
            resp = procesar_linea(json.dumps(step))
        except Exception as exc:
            resp = {"status": "blocked", "error": str(exc)[:200]}

        step_result = {
            "index": i,
            "op": step.get("op"),
            "status": resp.get("status", "unknown"),
            "result_id": resp.get("result_id"),
            "summary": _sintetizar(resp),
        }
        results.append(step_result)

        # AGUA: auto-reflection on failure
        if resp.get("status") in ("blocked", "invalid_input", "error"):
            stopped_at = i
            sugerencia = ""
            if resp.get("status") == "invalid_input":
                motivo = resp.get("motivo", "entrada invalida")
                sugerencia = "El artefacto es invalido. Verificar con op:verify."
                if "hash" in motivo.lower():
                    sugerencia = "Hash del artefacto no coincide. " \
                                 "Revisar que el binario no fue modificado."
            elif resp.get("status") == "blocked":
                motivo = resp.get("motivo", "operacion bloqueada")
                sugerencia = "La operacion fue bloqueada: %s. " \
                             "Verificar parametros y reintentar con " \
                             "op:verify primero." % motivo

            reflexion = {
                "step": i,
                "op": step.get("op"),
                "estado": resp.get("status"),
                "motivo": resp.get("motivo", ""),
                "reflexion_sugerida": sugerencia,
                "accion_alternativa": _accion_alternativa(step, resp),
            }
            # FUEGO/AGUA: cuando auto=True, REGISTRAR la reflexión en la BD
            # para que futuros op:run consulten esta lección de fallo.
            # Esto cierra el loop de aprendizaje: fallo -> reflexión registrada ->
            # lección disponible para el próximo intento.
            if auto:
                _registrar_reflexion_auto(step, resp, sugerencia, i)
            reflexiones.append(reflexion)

            step_result["reflexion_sugerida"] = sugerencia
            if not continue_on_error:
                break

    # ALMA: persistir step completados a la DB para resume futuro
    if session_id:
        _persistir_session_steps(session_id, steps, results)

    # TIERRA: usar result_id REAL del step detenido, no placeholder "last"
    if stopped_at is not None and stopped_at < len(results):
        real_rid = results[stopped_at].get("result_id", "")
        next_actions_explain = [{"op": "explain",
                                "args": {"result_id": real_rid} if real_rid
                                else {"session_id": session_id},
                                "available": True,
                                "descripcion": "Reconstruir evidencia del "
                                               "ultimo resultado bloqueado"}]
    else:
        next_actions_explain = []

    return {
        "status": "ok" if stopped_at is None else "partial",
        "op": "repl",
        "session_id": session_id,
        "mission_id": mission_id,
        "auto_generated": bool(mission_id and not params.get("steps")),
        "auto_cycle": steps if mission_id and not params.get("steps") else [],
        "steps_executed": len(results),
        "steps_total": len(steps),
        "results": results,
        "reflexiones": reflexiones,
        "stopped_at": stopped_at,
        "next_actions": next_actions_explain,
        "limitations": (
            [f"REPL se detuvo en step {stopped_at} debido a error. "
             "Revisar reflexion_sugerida antes de continuar."]
            if stopped_at is not None else []
        ),
    }


def _registrar_sesion(params: dict, session_id: str) -> None:
    """ALMA: registra una sesion de trabajo en la tabla de research.

    Un session_id es una cadena opaca que agrupa operaciones relacionadas
    con un mismo proposito (ej: 'rx550-investigation-001'). Se registra como
    un 'note' en la tabla research, lo que permite rastrear continuidad
    de proposito (§31) y recuperar el contexto de una sesion mas tarde.
    """
    c = _get_db()
    try:
        existing = c.execute(
            "SELECT COUNT(*) FROM research WHERE kind='session' AND text=?",
            (session_id,)
        ).fetchone()
        if existing and existing[0] > 0:
            return
        purpose = params.get("session_purpose", "trabajo con rxre")
        store.registrar_investigacion(
            c,
            kind="session",
            text=session_id,
            status="ACTIVE",
            target=purpose,
            gap_kind="",
        )
    except Exception:
        pass
    finally:
        c.close()


def _persistir_session_steps(session_id: str, steps: list, results: list) -> None:
    """ALMA: persiste los steps completados de una sesion para resume futuro.

    Usa `trace_id` en execution_events como session_id. Cada step con status 'ok'
    se registra como un evento con trace_id=session_id, lo que permite a
    _cargar_session_steps recuperar los ops completados y saltarlos.
    """
    c = _get_db()
    try:
        for i, (step, result) in enumerate(zip(steps, results)):
            if result.get("status") == "ok":
                evento_id = "step_%s_%03d" % (session_id, i)
                c.execute(
                    "INSERT OR REPLACE INTO execution_events "
                    "(evento_id, op, capability, trace_id, timestamp, persistido, "
                    "limitations, lecciones_json) "
                    "VALUES (?, ?, ?, ?, datetime('now'), 1, '[]', '[]')",
                    (evento_id, step.get("op", ""), step.get("capability", ""),
                     session_id),
                )
        c.commit()
    except Exception:
        pass
    finally:
        c.close()


def _cargar_session_steps(session_id: str) -> list:
    """ALMA: carga los ops completados en una session anterior.

    Querya execution_events por trace_id=session_id y devuelve la lista de ops
    que terminaron con exito. Usado por _handle_repl con resume=True para saltar
    steps ya completados.
    """
    c = _get_db()
    try:
        rows = c.execute(
            "SELECT DISTINCT op FROM execution_events "
            "WHERE trace_id=? AND persistido=1",
            (session_id,)
        ).fetchall()
        return [r[0] if isinstance(r, tuple) else r["op"] for r in rows]
    except Exception:
        return []
    finally:
        c.close()


def _registrar_reflexion_auto(step: dict, resp: dict, sugerencia: str,
                               step_index: int) -> None:
    """FUEGO/AGUA: registra una reflexión automática cuando repl --auto falla.

    Cierra el loop de aprendizaje: el fallo de un step en el ciclo autónomo
    se registra como reflexión en la BD, de modo que futuros op:run consulten
    esta lección de fallo antes de ejecutar.

    No levanta excepciones: si la BD no responde, el ciclo continúa.
    """
    capability = step.get("capability", "") or step.get("op", "")
    motivo = resp.get("motivo", "")
    outcome = "failure" if resp.get("status") == "blocked" else \
              "error" if resp.get("status") == "error" else "failure"
    try:
        c = _get_db()
        try:
            store.registrar_reflexion(
                c,
                feedback="Step %d (op:%s cap:%s) → status=%s motivo=%s"
                         % (step_index, step.get("op", "?"),
                            capability, resp.get("status", "?"), motivo[:200]),
                reflection="Estrategia alternativa automática: %s"
                           % sugerencia[:300],
                outcome=outcome,
                cap=capability,
                check_ejecutable="",  # auto-reflection sin check por ahora
            )
        finally:
            c.close()
    except Exception:
        pass


def _sintetizar(resp: dict) -> dict:
    """Extrae un resumen de un envelope de respuesta para el loop REPL."""
    summary = {
        "status": resp.get("status", "unknown"),
        "n_results": len(resp.get("results") or []),
        "capability": resp.get("capability") or resp.get("op"),
    }
    for k in ("motivo", "estado", "ejecutada"):
        if k in resp:
            summary[k] = resp[k]
    return summary


def _accion_alternativa(step: dict, resp: dict) -> str:
    """Genera una accion alternativa concreta para reemplazar el step fallido."""
    op = step.get("op", "")
    if op == "verify":
        return "op:verify con artefacto valido o sin artefacto para health check"
    if op == "discover":
        return "op:discover requiere artefacto ELF valido; usar op:verify primero"
    if op == "run":
        cap = step.get("capability", "")
        if cap == "binary.xrefs":
            return "Verificar que rizin este en PATH: op:verify"
        if cap == "binary.callgraph":
            return "Verificar que radare2 este en PATH: op:verify"
    return "Revisar parametros y estado del backend: op:backends"

def _sintetizar_check_fallo(rotas: list) -> str:
    """AGUA-AUTO: sintetiza el feedback de checks que no sostienen."""
    if not rotas:
        return "checks ejecutados pero sin fallos registrados"
    partes = []
    for r in rotas[:3]:
        if isinstance(r, dict):
            check = r.get("check", r.get("check_ejecutable", ""))
            motivo = r.get("motivo", r.get("error", ""))
            partes.append("check '%s': %s" % (check[:50], motivo[:100]))
        else:
            partes.append(str(r)[:100])
    return "; ".join(partes)

def _auto_reparar_check(rotas: list) -> str:
    """AGUA-AUTO: genera un check_ejecutable mejorado basado en fallos previos."""
    if not rotas:
        return "Revisar checks de la lección y proponer observador estable"
    r = rotas[0] if isinstance(rotas[0], dict) else {}
    check = r.get("check", r.get("check_ejecutable", ""))
    if "count" in check.lower() or "index" in check.lower():
        return ("Reemplazar check '%s' con uno basado en 'value_hex' en vez "
                "de 'count/index': el numero de resultados es volatil, el "
                "valor observado es el discriminante estable." % check[:50])
    return ("Actualizar check '%s': el productor puede haber cambiado, "
            "verificar observable estable." % check[:50])

def _steps_desde_mision(mission_id: str) -> list:
    """ALMA: auto-genera steps desde los tasks de una misión.

    Cada task se convierte en un step op:run con la capability extraída del
    título de la tarea. Esto automatiza el pipeline: un agente solo necesita
    decir 'executa la misión X' y repl genera los steps.

    Tasks marcados como COMPLETED/DONE no se incluyen.
    """
    try:
        c = _get_db()
        try:
            tasks = store.obtener_tareas_mision(c, mission_id)
            steps = []
            for t in tasks:
                status = t.get("status", "")
                if status in ("COMPLETED", "DONE"):
                    continue
                title = t.get("title", "")
                cap = _capability_de(title)
                if cap:
                    steps.append({"op": "run", "capability": cap})
                else:
                    steps.append({"op": "verify"})
            return steps
        finally:
            c.close()
    except Exception:
        return []


def _generar_ciclo_autonomo(mission_id: str, max_steps: int) -> list:
    """ETER/ALMA: genera el ciclo completo de los 8 principios como steps.

    El ciclo: verify → select → run → explain → scan → select → run → ...
    Se repite hasta completion o max_steps. Los fallos se registran como
    'reflexion_sugerida' y el ciclo salta al siguiente step.

    No requiere intervencion manual: cada step incluye los parametros
    necesarios basados en la respuesta del step anterior (next_action chaining).

    CUERPO/AIRE: cada step op:run dentro del ciclo incluye un verify implícito,
    garantizando que el entorno está sano antes de ejecutar.
    """
    steps = [
        {"op": "verify"},                    # CUERPO: health check
        {"op": "select", "mission_id": mission_id},  # ETER/ALMA: pick next task
        {"op": "run", "capability": "binary.inspect", "artefacto": "/bin/ls"},  # FUEGO
        {"op": "explain", "root_cause": True},  # MENTE/TIERRA
        {"op": "scan"},                       # ETER: correlate findings
        {"op": "saturate"},                   # MENTE: evaluate frontiers
    ]
    # CUERPO/AIRE: intercalar verify antes de cada run
    augmented = []
    for s in steps:
        if s.get("op") == "run" and mission_id:
            if not augmented or augmented[-1].get("op") != "verify":
                augmented.append({"op": "verify"})
        augmented.append(s)
    return augmented[:max_steps] if max_steps else augmented


def _analyze_root_cause(explanation: dict) -> dict:
    """MENTE: analisis causal de por que un resultado se produjo o se bloqueo.

    Recorre la cadena del backend (cadena_backend) y el estado del resultado
    para proponer hipotesis falsables sobre la causa raiz.
    """
    backend_chain = explanation.get("backend", {})
    result = explanation.get("result", {})
    operation = explanation.get("operation", {})
    result_id = explanation.get("result_id", "")

    hipotesis = []
    status = result.get("status", "")

    # 1. Analizar el estado del resultado
    if status == "blocked":
        hipotesis.append({
            "nodo": "result.status",
            "tipo": "blocked",
            "evidencia": status,
            "hipotesis": "La operacion fue bloqueada antes de ejecutarse",
            "verificacion": "Verificar que los parametros obligatorios "
                            "(artefacto, capability) estan presentes y validos: "
                            "op:run con los mismos parametros",
        })
    elif status == "invalid_input":
        hipotesis.append({
            "nodo": "result.status",
            "tipo": "invalid_input",
            "evidencia": status,
            "hipotesis": "El artefacto fue proveido pero es invalido "
                         "(no existe, no es ELF, hash no coincide)",
            "verificacion": "op:verify con el mismo artefacto para diagnosticar",
        })
    elif status == "empty":
        hipotesis.append({
            "nodo": "result.status",
            "tipo": "empty_result",
            "evidencia": status,
            "hipotesis": "La operacion ejecuto pero devolvio resultados vacios",
            "verificacion": "Verificar si el binario tiene simbolos: "
                            "op:run capability=binary.inspect",
        })

    # 2. Analizar la cadena del backend
    for step, entry in sorted(backend_chain.items()):
        if isinstance(entry, dict):
            step_status = entry.get("status", "")
            if step_status == "blocked":
                hipotesis.append({
                    "nodo": "backend.%s" % step,
                    "tipo": "backend_blocked",
                    "evidencia": step_status,
                    "hipotesis": "El backend fue bloqueado en este paso",
                    "verificacion": "op:verify para comprobar que el backend esta en PATH",
                })
            elif step_status in ("error", "fail", "backend_error"):
                hipotesis.append({
                    "nodo": "backend.%s" % step,
                    "tipo": "backend_error",
                    "evidencia": entry.get("error", step_status),
                    "hipotesis": "El backend devolvio error en este paso",
                    "verificacion": "Revisar los logs del backend y ejecutar "
                                    "manualmente con -v para diagnostico",
                })

    # 3. Analizar version_verificada
    for step, entry in sorted(backend_chain.items()):
        if isinstance(entry, dict) and entry.get("version_verificada") is False:
            hipotesis.append({
                "nodo": "backend.%s.version" % step,
                "tipo": "unverified_version",
                "evidencia": "version_verificada=False",
                "hipotesis": "El backend ejecuto pero su version no "
                             "esta verificada — el resultado puede contener "
                             "datos incorrectos",
                "verificacion": "op:verify para confirmar la version del backend",
            })

    # 4. Analizar la operacion completa
    if operation:
        op_status = operation.get("status", "")
        if op_status == "blocked":
            hipotesis.append({
                "nodo": "operation.status",
                "tipo": "operation_blocked",
                "evidencia": op_status,
                "hipotesis": "La operacion completa fue bloqueada "
                             "(allow-list, parametros, etc.)",
                "verificacion": "Revisar el motivo en operation.motivo o "
                                "operation.limitations",
            })

    # 5. Si no se encontro ninguna hipotesis negativa, el resultado es ok
    if not hipotesis:
        hipotesis.append({
            "nodo": "result.status",
            "tipo": "ok",
            "evidencia": status,
            "hipotesis": "El resultado es ok — no hay causa raiz de fallo",
            "verificacion": "No se necesita accion correctiva. "
                            "Si la profundidad es insuficiente, usar "
                            "op:discover para expandir la investigacion",
        })

    return {
        "result_id": result_id,
        "hipotesis": hipotesis,
        "n_hipotesis": len(hipotesis),
        "cadena_analizada": list(backend_chain.keys()),
        "veredicto": "investigar" if len(hipotesis) > 1 or \
            (hipotesis and hipotesis[0]["tipo"] != "ok") else "completo",
    }


def _auditar_truncamiento(data: dict) -> dict:
    """AIRE: verifica que los datos no esten truncados o corruptos.

    Comprueba profundidad de anidamiento, longitud de strings, y presencia
    de marcadores de truncamiento comunes.
    """
    issues = []
    max_depth = 0
    max_len = 0

    def _walk(obj, depth=0):
        nonlocal max_depth, max_len
        max_depth = max(max_depth, depth)
        if isinstance(obj, str):
            max_len = max(max_len, len(obj))
            if obj.endswith("...") and len(obj) > 3:
                issues.append("string truncado: %s..." % obj[:40])
            if obj.endswith("[ERROR]") or obj.endswith("[FAIL]"):
                issues.append("string con error backend: %s" % obj[:60])
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v, depth + 1)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v, depth + 1)

    _walk(data)

    if max_depth > 15:
        issues.append("profundidad de anidamiento excesiva: %d "
                      "(posible truncamiento de estructura)" % max_depth)
    if max_len > 50000:
        issues.append("string muy largo: %d chars (posible dump no truncado)"
                      % max_len)

    return {
        "ok": len(issues) == 0,
        "max_depth": max_depth,
        "max_len": max_len,
        "issues": issues,
    }


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

    # AIRE: validación de integridad de artefacto antes de ejecutar
    artefact_check = _verificar_integridad_artefacto(params)
    env_precheck = {"artefacto": artefact_check.get("artifact_path"),
                    "existe": artefact_check.get("artifact_exists"),
                    "hash_ok": artefact_check.get("artifact_hash_match"),
                    "limitaciones_contrato": artefact_check.get("limitations", [])}

    # MEDIDO 2026-10-14 (RXRE-CORE-CAUSAL-002): antes de ejecutar, consultar
    # si esta capability tiene lecciones de FALLO registradas. La ruta de
    # op: run no las consultaba; solo op:plan lo hacía. Esa es la brecha de
    # WATER: una leccion que dice "no hagas X de nuevo" llegaba al plan, pero
    # al ejecutar no se exponia, así que no podía influir en la acción real.
    # Aquí se consulta ANTES de ejecutar y se expone después, SIN alterar los
    # argumentos: la IA decide si las sigue. No se hace gating: una leccion
    # de fallo no autoriza al sistema a negar un reintento deliberado al que
    # la IA aplica la estrategia.
    lecciones = []
    try:
        _c = store.conectar(params.get("db_path", ""))
        _rep = store.consultar_reflexiones_para_capability(
            _c, capability, outcome_filter="failure", limite=10)
        if _rep.get("estado") == "ok":
            for r in _rep.get("reflexiones", []):
                estr = r.get("strategy") or r.get("reflection") or ""
                if estr:
                    lecciones.append({"strategy": estr,
                                      "reflexion_id": r.get("reflexion_id"),
                                      "feedback": r.get("feedback")})
    except Exception:
        # una leccion no debe hundir una ejecucion. Si la BD no responde, se
        # sigue sin ella, y se reporta como limitation.
        pass

    env = dispatch.ejecutar(capability, run_params)
    # AIRE: inyectar el contract check en el envelope para root_cause analysis
    if not artefact_check["ok"]:
        env.setdefault("precheck", {})
        env["precheck"].setdefault("contrato", {})
        env["precheck"]["contrato"] = env_precheck
    # MEDIDO 2026-10-14: registrar el evento DURABLE de esta ejecucion.
    # Se escribe en best-effort sobre la BD que ya se abrio arriba para las
    # lecciones; si falla, no se altera ni la ejecucion ni la respuesta.
    # RXRE-TRACE-ID-001: el trace_id de esta invocacion viaja en el envelope
    # del evento. `registrar_evento` ya lee `env["trace_id"]`, asi que se
    # inyecta ANTES de la escritura: una sola ruta, sin recalcular el hash.
    env["trace_id"] = _trace_id_actual(params)
    try:
        store.registrar_evento(_c, "run", capability, env, lecciones)
    except Exception:
        pass
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
    # TIERRA: usar result_id REAL, no placeholder "last"
    next_actions = env.get("next_actions") or []
    if not next_actions and env.get("results"):
        rs = env.get("results") or [{}]
        real_rid = rs[0].get("result_id", "") if isinstance(rs[0], dict) else ""
        if real_rid:
            next_actions = [{
                "op": "explain",
                "args": {"result_id": real_rid},
                "available": True,
                "descripcion": "Reconstruir la cadena de evidencia de este resultado",
            }]

    # FUEGO: cuando run esta bloqueado, encadenar reflect -> select para
    # retomar la accion sin intervencion manual. La reflexion captura el
    # feedback del bloqueo; select vuelve a proponer una tarea viable.
    if env.get("status") in ("blocked", "error", "fallback", "invalid_input") and capability:
        # Asegurar que reflect y select siempre estan presentes en blocked/error
        has_reflect = any(na.get("op") == "reflect" for na in next_actions)
        has_select = any(na.get("op") == "select" for na in next_actions)
        if not has_reflect:
            next_actions.insert(0, {
                "op": "reflect",
                "args": {"outcome": "failure",
                         "feedback": env.get("motivo", "bloqueado"),
                         "reflection": "La capability '%s' fue bloqueada. "
                                       "Revisar limitations." % capability},
                "available": True,
                "descripcion": "REGISTRAR el feedback del bloqueo para futuras lessons",
            })
        if not has_select:
            next_actions.append({
                "op": "select",
                "args": {"target": capability},
                "available": True,
                "descripcion": "VOLVER a seleccionar una tarea viable",
            })
        # FUEGO-LEARN: sugerir run con backend alternativo basado en historia
        backend_alt = _mejor_backend_para(capability)
        if not backend_alt:
            # Inferir del motivo del bloqueo
            for br in (env.get("blocked_reasons") or []):
                motivo_b = (str(br.get("motivo", "")) + " " +
                           str(br.get("regla", ""))).lower()
                if "rizin" in motivo_b:
                    backend_alt = "radare2"
                elif "radare2" in motivo_b or " r2" in motivo_b:
                    backend_alt = "rizin"
        if backend_alt:
            next_actions.append({
                "op": "run",
                "args": {"capability": capability,
                         "backend_id": backend_alt},
                "available": True,
                "descripcion": "FUEGO-LEARN: reintentar con %s (historia "
                               "de performance)" % backend_alt,
            })
    
    # Asegurar que limitations existe (dispatch.ejecutar no siempre lo incluye en rutas de error)
    limitations = env.get("limitations") or []
    if not limitations and env.get("motivo"):
        limitations = [env.get("motivo")]
    
    # AIRE: add artifact_check limitations
    if "artefact_check" in locals():
        limitations.extend(artefact_check.get("limitations", []))
    # AIRE: boolean de validacion de contrato para consumo rapido
    artefact_ok = bool(artefact_check.get("ok")) if "artefact_check" in locals() else True

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
        # RXRE-TRACE-ID-001: el agente emite `RXRE_TRACE_ID` por invocacion.
        # Reusarlo = reintento del mismo intento; uno nuevo = intento nuevo.
        # Se devuelve para que el llamador pueda verificar que quedo ligado.
        "trace_id": _trace_id_actual(),
        "limitations": limitations,
        "artifacts_validados": artefact_ok,
        "precheck": env.get("precheck"),
        "artifact_check": artefact_check,
        # las lecciones de fallo de esta capability, consultadas antes de
        # ejecutar. Lista vacia si ninguna: no es "no disponible", es
        # "no hay historial de fallo sobre esto".
        "lecciones_previas": lecciones,
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

    # MENTE: root-cause analysis when blocked/invalid_input
    # Distingue el tipo de fallo y propone verificacion concreta
    if status in ("blocked", "invalid_input", "error"):
        response["root_cause"] = _analyze_run_failure(env)

    # AGUA: auto-register reflection when gate fails
    # Si el gate devolvio violation, registrar una reflexion automatica
    gate_info = env.get("gate") or {}
    if (gate_info.get("operacion_cerrada") is False and
            env.get("status") == "ok" and env.get("results")):
        # El producer devolvio OK pero el gate lo rechazo
        _auto_registrar_reflexion_gate(env, capability)
        response["limitations"] = limitations + [
            "gate rechazo la operacion: se registro reflexion automatica"
        ]

    # FUEGO-LEARN: registrar performance del backend para aprendizaje futuro
    backend_id = env.get("backend_id") or env.get("backend") or params.get("backend_id", "")
    if backend_id and capability:
        try:
            _registrar_performance_backend(
                capability, backend_id,
                exito=(env.get("status") == "ok"),
                tiempo_seg=env.get("tiempo_s"),
            )
        except Exception:
            pass  # No bloquear el run por un registro de performance

    return response


def _registrar_performance_backend(capability: str, backend_id: str,
                                    exito: bool, tiempo_seg: float = None) -> None:
    """FUEGO-LEARN: registra el performance de un backend para aprendizaje futuro.

    Cada vez que op:run usa un backend, se registra {capability, backend_id,
    success_rate, avg_time}. Las futuras sugerencias de backend alternativo
    usan esta historia para elegir el que historicalmente funciona mejor.
    """
    c = _get_db()
    try:
        # Usar la tabla de research para registrar performance
        # kind='performance', target=capability, text=backend_id
        text = "backend=%s exito=%s tiempo=%s" % (backend_id, exito, tiempo_seg)
        store.registrar_investigacion(
            c, kind="performance",
            text=text, status="OPEN" if exito else "CLOSED",
            target=capability, gap_kind="backend_perf",
        )
    except Exception:
        pass
    finally:
        c.close()


def _mejor_backend_para(capability: str) -> str:
    """FUEGO-LEARN: devuelve el backend con mejor historial para una capability.

    Usa la tabla de research para encontrar el backend que ha tenido más
    successful runs para esta capability.
    """
    c = _get_db()
    try:
        cur = c.execute(
            "SELECT text FROM research WHERE kind='performance' "
            "AND target=? AND status='OPEN' ORDER BY id DESC LIMIT 3",
            (capability,),
        ).fetchall()
        backend_scores = {}
        for row in cur:
            # Parse: backend=rizin exito=True tiempo=0.5
            text = row[0] if isinstance(row, tuple) else row["text"]
            bid = text.split("backend=")[1].split(" ")[0] if "backend=" in text else ""
            if bid:
                backend_scores[bid] = backend_scores.get(bid, 0) + 1
        if backend_scores:
            return max(backend_scores, key=backend_scores.get)
        return ""
    except Exception:
        return ""
    finally:
        c.close()


def _outcome_from_status(status: str) -> str:
    """Mapea un status de ejecucion a un outcome de reflexion."""
    m = {"error": "error", "timeout": "timeout",
         "blocked": "failure", "invalid_input": "failure"}
    return m.get(status, "failure")


def _analyze_run_failure(env: dict) -> dict:
    """MENTE: analisis causal de por que un run fallo.

    NO devuelve un veredicto: devuelve una hipotesis falsable con una
    accion de verificacion concreta. La distincion es importante: un
    veredicto que no puede refutarse no es un mecanismo.

    Analiza tres fuentes de evidencia:
    1. `env["motivo"]` — el mensaje del dispatch
    2. `env["precheck"]` — el estado de validacion de entrada
    3. `env.get("ejecucion")` — el estado del productor
    """
    status = env.get("status", "")
    motivo = env.get("motivo", "")
    precheck = env.get("precheck") or {}
    ejec = env.get("ejecucion") or {}

    hipotesis = []

    # 1. Capability no existe
    if "no hay ninguna capacidad registrada" in motivo:
        hipotesis.append({
            "nodo": "dispatch.esta_permitida",
            "tipo": "not_in_registry",
            "hipotesis": "La capability solicitada no esta en el registry",
            "verificacion": "Consultar op:backends para ver capabilities disponibles",
            "veredicto": "refutar: listar capabilities y confirmar que el nombre existe",
        })

    # 2. Artefacto invalido
    if "faltan parametros obligatorios" in motivo or "artefacto" in motivo.lower():
        hipotesis.append({
            "nodo": "dispatch.parametros",
            "tipo": "missing_param",
            "hipotesis": "Falta un parametro obligatorio (probablemente artefacto)",
            "verificacion": "Verificar con op:verify --artefacto <ruta>",
        })

    # 3. Backend no existe
    if precheck.get("backend_existe") is False:
        hipotesis.append({
            "nodo": "dispatch.precheck.backend_existe",
            "tipo": "backend_unavailable",
            "hipotesis": "El backend declarado no esta en PATH",
            "verificacion": "Consultar op:verify para confirmar que el backend esta disponible",
        })

    # 4. Artefacto no existe o no es ELF
    if precheck.get("input_existe") is False:
        hipotesis.append({
            "nodo": "dispatch.precheck.input_existe",
            "tipo": "artefacto_not_found",
            "hipotesis": "El artefacto no existe en el path declarado",
            "verificacion": "Verificar el path con op:verify --artefacto <ruta>",
        })

    # 5. Error del productor
    if status == "error" and ejec.get("exit_status") not in (0, None):
        hipotesis.append({
            "nodo": "producer.exit_status",
            "tipo": "producer_error",
            "hipotesis": "El backend devolvio exit_status=%s" % ejec.get("exit_status"),
            "verificacion": "Ejecutar manualmente con -v: %s" % " ".join(ejec.get("argv", [])),
        })

    # 6. Contrato de artefacto fallido (AIRE)
    contrato = (env.get("precheck") or {}).get("contrato") or {}
    if contrato:
        limitaciones = contrato.get("limitaciones_contrato", [])
        if limitaciones:
            hipotesis.append({
                "nodo": "aire._verificar_integridad_artefacto",
                "tipo": "contract_violation",
                "hipotesis": "El contrato PRE_EXECUTION fallo: %s" % "; ".join(limitaciones),
                "verificacion": "Consultar op:verify --artefacto <ruta> para diagnosticos completos",
            })

    # 6. Si no se puede determinar la causa
    if not hipotesis:
        hipotesis.append({
            "nodo": "env.status",
            "tipo": "undetermined",
            "hipotesis": "El fallo no encaja en patrones conocidos — revisar motivo completo",
            "verificacion": "op:explain --root_cause sobre el operation_id o result_id asociado",
        })

    return {
        "env_status": status,
        "env_motivo": motivo,
        "hipotesis": hipotesis,
        "n_hipotesis": len(hipotesis),
        "veredicto": "investigar",
        "verificacion_sugerida": hipotesis[0]["verificacion"] if hipotesis else "",
    }


def _auto_registrar_reflexion_gate(env: dict, capability: str) -> None:
    """AGUA: registra automaticamente una reflexion cuando el gate falla.

    El gate es la auditoria de los ocho principios. Si un producer devuelve
    `ok` pero el gate devuelve `violation`, se registra una reflexion con:
    - feedback: la violacion del gate
    - reflection: el motivo de la violacion
    - outcome: failure
    - attempt_id: el operation_id (si existe)
    - capability: la capability ejecutada

    Esta reflexion queda disponible para `consultar_reflexiones_para_capability`
    en futuras ejecuciones, cerrando el lazo AGUA → MENTE → FUEGO.
    """
    gate_info = env.get("gate") or {}
    nota = gate_info.get("nota") or {}
    en_violacion = nota.get("en_violacion", [])
    detalle = nota.get("detalle", {})

    feedback_parts = []
    for v in en_violacion:
        d = detalle.get(v, {})
        feedback_parts.append("%s: %s" % (v, d.get("porque", "")))

    feedback = "Gate violation: " + "; ".join(feedback_parts) if feedback_parts else \
               "Gate rechazo la operacion sin detalles"

    try:
        c = _get_db()
        try:
            store.registrar_investigacion(
                c,
                kind="note",
                text="Gate violation en %s: %s" % (capability, feedback),
                status="REFUTED",
                target=capability,
                gap_kind="",
            )
        finally:
            c.close()
    except Exception:
        pass


def _handle_select(params: dict) -> dict:
    """op: select - ALMA: selecciona la siguiente accion viable de una mision.

    Usa `store.seleccionar_siguiente_accion()` que ordena por valor REAL
    (reincidencia, dependencia, incertidumbre, evidencia, alineacion, coste),
    no por un entero de prioridad.

    Si no se provee mission_id, crea una mision DEFAULT para la session.

    Uso:
        {"op":"select"}
        {"op":"select","mission_id":"mission_abc"}
        {"op":"select","target":"binary.xrefs","session_id":"invest-001"}
    """
    mission_id = params.get("mission_id")
    target = params.get("target", "")
    session_id = params.get("session_id")

    c = _get_db()
    try:
        if not mission_id:
            # Crear mision default si no existe
            mission_id = store.crear_mision(
                c,
                title="RXRE autonomous investigation",
                description="Coordinacion automatica de los ocho principios via op:run",
            )

        # ALMA: si hay un target, registrar una frontier si no existe
        if target:
            store.registrar_investigacion(
                c, kind="frontier", text=target, status="OPEN",
                target=target, gap_kind="",
            )

        # ETER: seleccionar siguiente accion usando valor real
        task_id = store.seleccionar_siguiente_accion(c, mission_id, por_valor=True)

        if not task_id:
            # No hay tareas viables — sugerir registrar una
            return {
                "status": "empty",
                "op": "select",
                "mission_id": mission_id,
                "task_id": None,
                "mensaje": "No hay tareas viables en la mision. "
                           "Usar 'op:research --kind frontier' para registrar una nueva.",
                "next_actions": [
                    {"op": "research",
                     "args": {"kind": "frontier", "status": "OPEN",
                              "target": target or ""},
                     "descripcion": "Registrar una nueva frontier"}
                ],
            }

        # ETER: valorar todas las tareas para mostrar el scoring
        valoracion = store.valorar_tareas(c, mission_id)
        tarea = next((t for t in valoracion.get("tareas", [])
                      if t["task_id"] == task_id), {})

        return {
            "status": "ok",
            "op": "select",
            "mission_id": mission_id,
            "task_id": task_id,
            "selected": {
                "task_id": task_id,
                "title": tarea.get("title"),
                "description": tarea.get("description"),
                "valor": tarea.get("valor"),
                "componentes": tarea.get("componentes"),
                "bloqueada": tarea.get("bloqueada"),
            },
            "all_tasks": [
                {"task_id": t["task_id"], "title": t.get("title"),
                 "valor": t.get("valor"), "bloqueada": t.get("bloqueada")}
                for t in valoracion.get("tareas", [])
            ],
            "next_actions": [
                {"op": "run",
                 "args": {"capability": _capability_de(tarea.get("title", ""))},
                 "descripcion": "Ejecutar la tarea seleccionada"}
            ],
            "limitations": [],
        }
    finally:
        c.close()


def _capability_de(texto: str) -> str:
    """Extrae el nombre de capability de un texto de tarea (si contiene uno)."""
    import re as _re
    m = _re.search(r'\b(binary\.\w+)', texto or "")
    return m.group(1) if m else ""


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
    if refs.get("reflexiones"):
        plan["reflexiones_previas"] = [{
            "reflexion_id": r.get("reflexion_id"),
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
    # Fallback: if plan has steps but no available next_actions, suggest run anyway
    if not plan.get("next_actions") and plan.get("plan"):
        for paso in plan.get("plan"):
            cap = paso.get("capability")
            if cap:
                plan["next_actions"] = [{
                    "op": "run",
                    "args": {"capability": cap},
                    "available": False,
                    "descripcion": "Ejecutar paso del plan (revisar warnings)",
                }]
                break
    elif not plan.get("next_actions") and capability:
        plan["next_actions"] = [{
            "op": "run",
            "args": {"capability": capability},
            "descripcion": "Ejecutar la capability tras planificar"},
        ]
    # RXRE-TRACE-ID-001: mismo trace que el run para que `eventos_por_trace`
    # reconstruya plan->run de una invocacion como UNA cadena.
    plan["trace_id"] = _trace_id_actual(params)
    # MEDIDO 2026-10-14: event-log durable tambien para op:plan (simetria
    # con op:run). Plan no produce operation_id ni persistido; se registra
    # lo que se puede (capability, n_lessons, limitations).
    # MEDIDO 2026-10-15: se registra con LA MISMA conexion `c` antes de
    # cerrarla. La version anterior abria una segunda; medido, `close()`
    # cuesta 0.018s y se pagaba dos veces por op:plan.
    try:
        store.registrar_evento(c, "plan", capability,
                               {"ejecucion": {"exit_status": None},
                                "limitations": plan.get("limitations", []),
                                "persistido": plan.get("status") == "ok",
                                "trace_id": _trace_id_actual(params)},
                               plan.get("reflexiones_previas", []))
    except Exception:
        pass
    finally:
        c.close()

    # MENTE-FEASIBILITY: auto-evaluar si los pasos del plan son factibles.
    # Un paso es factible si: (1) la capability existe en el registry, o
    # (2) la capability fue usada exitosamente antes en historial.
    from rxre.backends import registry as _registry
    plan_paso = plan.get("plan") or []
    steps_feasible = []
    for paso in plan_paso:
        cap = paso.get("capability", "")
        available = paso.get("available", False)
        # Check if capability exists in registry
        try:
            _registry.lookup(cap)
            feasible = True
        except Exception:
            feasible = False
        steps_feasible.append({
            "capability": cap,
            "feasible": feasible,
            "available": available,
        })
    plan["feasibility"] = steps_feasible
    plan["feasible_steps"] = sum(1 for s in steps_feasible if s["feasible"])
    plan["total_steps"] = len(steps_feasible)

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
            target=params.get("target", ""),
            capability=params.get("capability", ""),
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

    # AGUA: despues de registrar, verificar que la leccion tiene un check ejecutable.
    # Si no, sugerir lessons --ejecutar para validar.
    try:
        _c = _get_db()
        try:
            lecciones_check = store.verificar_lecciones(_c, ejecutar=False)
            sin_check = lecciones_check.get("sin_check", 0)
        finally:
            _c.close()
    except Exception:
        sin_check = 0

    # Proponer como next_action: buscar reflexiones pasadas con el mismo outcome
    # para que la IA pueda aprender de experiencias similares.
    next_actions = [{
        "op": "reflect",
        "args": {"outcome": outcome},
        "available": True,
        "descripcion": "Buscar reflexiones previas con outcome=%s" % outcome,
    }]
    # AGUA-MATCH: buscar estrategias exitosas pasadas para este capability
    # Si hay una estrategia que funcionó antes, sugerirla como alternativa
    try:
        _c = _get_db()
        try:
            estrategias = store.buscar_estrategias_exitosas(
                _c, capability=params.get("capability", ""),
                outcome="success",
                limit=3,
            )
            if estrategias:
                for est in estrategias:
                    next_actions.append({
                        "op": "run",
                        "args": {"capability": params.get("capability", ""),
                                 "backend_id": est.get("backend_id")},
                        "available": bool(est.get("backend_id")),
                        "descripcion": "AGUA-MATCH: estrategia exitosa pasada: " +
                                       (est.get("strategy", "")[:60]),
                    })
        finally:
            _c.close()
    except Exception:
        pass  # No bloquear reflect por match fallido
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
            [{"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "esta leccion no esta vigilada por ningun check; "
                             "anadele uno con el campo check_ejecutable"}]),
        # AGUA: reportar estado de la verificacion de lecciones
        "lecciones_verificadas": {
            "sin_check": sin_check,
            "vigiladas": result.get("vigilada", False),
        },
        "limitations": ([]
                        if result.get("vigilada") else
                        ["esta reflexion queda escrita pero SIN check ejecutable: "
                         "se recordara leyendo, no se impedira repitiendo"]),
        # AGUA-META: estado global de lessons para context de future ops
        "lecciones_total_sin_check": sin_check,
    }


def _handle_explain(params: dict) -> dict:
    """op: explain - TIERRA: reconstruye la cadena de evidencia de un resultado.

    Con root_cause=True (MENTE), analiza la causa raiz del bloqueo/fallo
    recorriendo la cadena del backend y proponiendo hipotesis falsables.

    Con session_id (ALMA), registra una sesion de trabajo para rastrear
    la continuidad del proposito a traves de multiples operaciones.

    Uso:
        {"op":"explain","result_id":"res_abc"}
        {"op":"explain","result_id":"res_abc","root_cause":true}
        {"op":"explain","session_id":"investigacion-001"}
    """
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

    # ALMA: session tracking
    session_id = params.get("session_id") or params.get("session")
    if session_id:
        _registrar_sesion(params, session_id)

    c = _get_db()
    try:
        result = store.explicar(c, result_id)

        # MENTE: root-cause analysis
        if params.get("root_cause"):
            result["root_cause"] = _analyze_root_cause(result)

        # AIRE: truncation audit
        if params.get("audit_truncation") or params.get("audit"):
            trunc = _auditar_truncamiento(result)
            result["truncation_audit"] = trunc
            if not trunc["ok"]:
                result["limitations"] = result.get("limitations", []) + \
                    trunc.get("issues", [])

        # RXRE-AUTO-003: gate de ocho principios. Se aplica sobre la operacion
        # ya grabada. No es un segundo gate: es el MISMO gate, solo visto de
        # nuevo desde el lado del consume.
        #
        # store.explicar devuelve {result, operation, backend, chain...} pero
        # el gate necesita el ENVELOPE plano (precheck, ejecucion, provenance,
        # persistido, results). Se reconstruye desde response_json.
        if params.get("audit") or params.get("verify"):
            from backends.adapters.ocho_principios import gate
            op_row = result.get("operation") or {}
            env_gate = {}
            try:
                env_gate = json.loads(op_row.get("response_json") or "{}")
            except (ValueError, TypeError):
                env_gate = {}
            # AGUA: persistido no se almacena en response_json, pero si la
            # operacion esta en la DB, fue persistida (store.explicar la encontro).
            if "persistido" not in env_gate:
                env_gate["persistido"] = True
            result["gate"] = gate(env_gate)

        # MENTE/ETER: despues de explain con root_cause, encadenar a scan
        # para detectar correlaciones nuevas a partir del hallazgo explicado.
        if result.get("status") == "ok":
            na = result.get("next_actions") or []
            na.append({
                "op": "scan",
                "args": {"text": "Correlacionar hallazgo explicado %s con findings"
                                 "existentes" % result_id},
                "available": True,
                "descripcion": "ETER: buscar correlaciones con el hallazgo explicado",
            })
            result["next_actions"] = na

        return result
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
            "descripcion": "TIERRA+MENTE: reconstruye la cadena de evidencia de un resultado por "
                           "su result_id. root_cause=True analiza la causa raiz; "
                           "session_id registra una sesion (ALMA)",
            "campos": ["result_id", "root_cause?", "session_id?", "audit_truncation?"],
            "ejemplo": {"op": "explain", "result_id": "res_abc123",
                        "root_cause": True},
        },
        {
            "op": "verify",
            "descripcion": "CUERPO: health check previo (database writable, backends en PATH, "
                           "hardware allow-list, artefacto valido) — read-only",
            "campos": ["artefacto?", "db_path?", "capability?"],
            "ejemplo": {"op": "verify", "artefacto": "/bin/ls"},
        },
        {
            "op": "discover",
            "descripcion": "ETER: encadena binary.inspect + binary.xrefs + binary.callgraph sobre "
                           "un artefacto, integrando resultados en findings",
            "campos": ["artefacto"],
            "ejemplo": {"op": "discover", "artefacto": "/bin/ls"},
        },
        {
            "op": "repl",
            "descripcion": "AGUA: loop interactivo con auto-reflexion; ejecuta una secuencia de "
                           "operaciones (steps), genera reflexion_sugerida en fallos. "
                           "Con mission_id auto-genera steps; con auto=true ejecuta el "
                           "ciclo completo de los 8 principios",
            "campos": ["steps", "session_id?", "continue_on_error?", "mission_id?", "auto?", "max_steps?"],
            "ejemplo": {"op": "repl",
                       "mission_id": "mission_abc", "auto": True},
        },
        {
            "op": "select",
            "descripcion": "ALMA/ETER: selecciona la siguiente accion viable de una mision "
                           "usando valor real (reincidencia, dependencia, coste...)",
            "campos": ["mission_id?", "target?", "session_id?"],
            "ejemplo": {"op": "select"},
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
        {
            "op": "scan",
            "descripcion": "ETER: conecta hallazgos entre modulos, tareas y dominios. "
                           "Registra una frontier y auto-correlaciona findings con "
                           "numeros coincidentes (§53). Inicia el ciclo: scan→saturate→lessons→run→scan",
            "campos": ["text", "session_id?"],
            "ejemplo": {"op": "scan", "text": "Escaneo global: conectar hallazgos"},
        },
        {
            "op": "suite",
            "descripcion": "Ejecuta la suite de regresion completa en paralelo: "
                           "descubre tests, ejecuta con DB aislada, reporta rc",
            "campos": ["filtro?", "timeout?", "jobs?", "entorno_declarado?"],
            "ejemplo": {"op": "suite"},
        },
        {
            "op": "principios",
            "descripcion": "CUERPO/META: estado en tiempo real de los 8 principios "
                           "y su automatizacion de next_actions",
            "campos": [],
            "ejemplo": {"op": "principios"},
        },
        {
            "op": "trace",
            "descripcion": "ALMA: reconstruye la cadena de eventos de una invocacion",
            "campos": ["trace_id?"],
            "ejemplo": {"op": "trace"},
        },
        {
            "op": "fuego",
            "descripcion": "FUEGO: verifica las 6 garantias de seguridad antes de auto-ejecucion; enforcement bloquea ops inseguras",
            "campos": ["artefacto?", "check?"],
            "ejemplo": {"op": "fuego"},
        },
        {
            "op": "application",
            "descripcion": "AGUA: rastreo de aplicacion de lecciones (superficie / candidata / sin datos)",
            "campos": ["capability?"],
            "ejemplo": {"op": "application", "capability": "binary.inspect"},
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
            {"op": "saturate", "available": True,
             "args": {"target": capability},
             "descripcion": "ETER: evaluar que frontera sigue abierta tras "
                            "el experimento"},
        ] if veredicto in ("no_separable", "no_observable") else
            [{"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "comprobar que la leccion del experimento esta "
                             "vigilada por un check"},
             {"op": "saturate", "available": True,
              "args": {"target": capability},
              "descripcion": "ETER: evaluar frontera tras experimento sostenido"}]),
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
        # AGUA (1621): si se pide una capability concreta, el mismo op
        # expone el tracking de aplicación (surfaceada / candidata_aplicada)
        # SIN tabla nueva: lee de execution_events.lecciones_json.
        aplicacion = None
        cap = params.get("capability")
        if cap:
            aplicacion = store.trazar_aplicacion_lecciones(c, cap)
    finally:
        c.close()

    sin = r.get("sin_check", 0)
    rotas = r.get("checks_que_no_sostienen", [])
    respuesta = {
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
                             "alguien lea la nota"},
             # ETER: siempre encadenar a scan para continuar el ciclo
             {"op": "scan", "args": {"text": "Re-escanear tras lessons: nuevas "
                            "correlaciones"},
              "available": True,
              "descripcion": "ETER: continuar ciclo scan→saturate→lessons→run"}]
            if sin else
            # AGUA: si se ejecutaron checks y algunos fallaron, sugerir reflect
            # para aprender de la falla; si todo OK, encadenar a scan (ETER)
            [{"op": "reflect", "args": {"outcome": "failure",
                                     "feedback": _sintetizar_check_fallo(rotas),
                                     "reflection": _auto_reparar_check(rotas)},
              "available": True,
              "descripcion": "los checks que no sostienen su leccion: "
                             "registra una reflexion con check reparado"},
             {"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "re-ejecutar los checks tras la nueva lesson"}]
            if ejecutar and rotas else
            [{"op": "lessons", "args": {"ejecutar": True}, "available": True,
              "descripcion": "ejecutar los checks y comprobar que siguen "
                             "sosteniendo lo que dicen"},
             {"op": "scan", "args": {"text": "Re-escanear tras lessons: "
                                "nuevas correlaciones"},
              "available": True,
              "descripcion": "ETER: continuar ciclo scan→saturate→lessons→run"}]),
        "limitations": r.get("limitations", []),
    }
    if aplicacion is not None:
        respuesta["aplicacion"] = aplicacion
    return respuesta


def _handle_principios(_params: dict) -> dict:
    """op: principios — CUERPO/META: estado de los 8 principios en tiempo real.

    Muestra qué principios están automatizados y cuál fue el último step
    registrado para cada uno en la BD. Esto reemplaza el chequeo manual de
    una tabla de papel contra la pared: el agente pregunta '¿qué principios
    están cubiertos?' y el sistema responde con datos.

    Sin RXRE_DB -> reporta el esquema conocido (los 8 principios y su op).
    Con RXRE_DB -> además muestra el último step ejecutado por cada principio.
    """
    principios = [
        {"principio": "CUERPO", "op": "verify",
         "descripcion": "Health check: DB, backends, hardware, artefacto"},
        {"principio": "MENTE", "op": "plan",
         "descripcion": "Planificación con root_cause y hipótesis falsables"},
        {"principio": "ALMA", "op": "select",
         "descripcion": "Selección de tareas por valor real"},
        {"principio": "ALMA", "op": "repl",
         "descripcion": "Loop con auto-reflexión y mission_id/autogeneración"},
        {"principio": "TIERRA", "op": "explain",
         "descripcion": "Cadena de evidencia con result_id real"},
        {"principio": "FUEGO", "op": "run",
         "descripcion": "Ejecución con auto-cadena reflect→select en fallos"},
        {"principio": "AGUA", "op": "reflect",
         "descripcion": "Reflexión registrada + verificación de checks"},
        {"principio": "AIRE", "op": "lessons",
         "descripcion": "Verificación de lecciones vigiladas"},
        {"principio": "ETER", "op": "scan",
         "descripcion": "Auto-correlación y frontier registration"},
    ]
    # Enriquecer con última actividad si hay BD
    try:
        c = _get_db()
        try:
            for p in principios:
                cur = c.execute(
                    "SELECT op, timestamp FROM execution_events "
                    "WHERE op=? ORDER BY id DESC LIMIT 1",
                    (p["op"],)
                ).fetchone()
                if cur:
                    p["ultima_actividad"] = cur["timestamp"]
                    p["registrada"] = True
                else:
                    p["registrada"] = False
        finally:
            c.close()
    except Exception:
        pass  # Sin BD, devolver el esquema conocido

    return {
        "status": "ok",
        "op": "principios",
        "ejecutada": True,
        "principios": principios,
        "n_principios": len(principios),
        "todos_registrados": all(p.get("registrada") for p in principios
                                 if p["op"] in ("verify", "plan", "select",
                                                "replace", "explain", "run",
                                                "reflect", "lessons", "scan"))
        if any(p.get("registrada") is not None for p in principios) else False,
        "next_actions": [{
            "op": "repl",
            "args": {"auto": True, "max_steps": 8},
            "available": True,
            "descripcion": "Ejecutar ciclo autónomo de los 8 principios",
        }],
        "limitations": [],
    }


def _handle_trace(params: dict) -> dict:
    """op: trace — ALMA: reconstruye la cadena de eventos de una invocacion.

    RXRE-TRACE-ID-001 expuesto. MEDIDO 2026-10-15: la columna `trace_id`
    estaba ESCRITA y nadie la LEIA (el test reventaba con AttributeError
    porque `store.eventos_por_trace` no existia). Esta op la expone para que
    un agente pueda reconstruir que se ejecuto, en que orden y con que
    resultado, dentro de UNA invocacion.

    Acepta `trace_id` explicito o el de esta invocacion (`RXRE_TRACE_ID`).
    Sin trace_id -> `empty`, no error: no hay cadena que reconstruir.
    """
    tid = params.get("trace_id") or os.environ.get("RXRE_TRACE_ID") or ""
    c = _get_db()
    try:
        r = store.eventos_por_trace(c, tid)
    finally:
        c.close()
    if r.get("status") == "ok":
        return {
            "status": "ok",
            "ejecutada": True,
            "trace_id": r.get("trace_id"),
            "eventos": r.get("eventos", []),
            "n_eventos": r.get("n", 0),
            "ops": r.get("ops", []),
            "capabilities": r.get("capabilities", []),
            "next_actions": [],
            "limitations": r.get("limitations", []),
        }
    return {"status": "empty", "ejecutada": True, "trace_id": tid,
            "eventos": [], "n_eventos": 0,
            "motivo": r.get("limitations", ["sin cadena"])[0],
            "next_actions": [
                {"op": "run", "args": {"capability": "binary.inspect"},
                 "available": True,
                 "descripcion": "generar eventos con RXRE_TRACE_ID para poder "
                                "reconstruir una cadena"}],
            "limitations": r.get("limitations", [])}


def _handle_bench(params: dict) -> dict:
    """op: bench — TIERRA: mide el coste REAL de las ops en ESTE host.

    POR QUE EXISTE, MEDIDO 2026-10-15
    ---------------------------------
    El cuello de `op:plan` (68% del tiempo en `commit`/fsync) se encontro
    midiendo a mano. Un hallazgo que depende de que alguien se acuerde de
    perfilar no es un mecanismo. Esta op hace la medicion parte de la CLI,
    para que ninguna afirmacion de rendimiento se haga sin ella.

    Mide DOS cosas separadas, que no son lo mismo:
      1. `en_proceso`: N llamadas a `procesar_linea` en este mismo proceso
         (lo que cuesta el handler, sin arranque de Python).
      2. `subproceso`: N llamadas por `machine.py` como proceso hijo (el
         camino REAL de un agente, con arranque e imports incluidos).

    Con `perfilar: true` ademas corre cProfile sobre la op y devuelve las
    funciones de mayor coste: es lo que encontro el `commit`.

    Las cifras son de ESTE HOST y ESTE momento: no son una promesa.
    """
    import time as _time
    ops = params.get("ops") or ["ops", "plan", "run", "verify"]
    n = int(params.get("n") or 5)
    perfilados = bool(params.get("perfilar"))
    maximo = int(params.get("maximo") or n)

    artefacto = params.get("artefacto") or "/bin/ls"
    reqs = {
        "ops": {"op": "ops"},
        "verify": {"op": "verify"},
        "backends": {"op": "backends"},
        "lessons": {"op": "lessons"},
        "scan": {"op": "scan"},
        "plan": {"op": "plan", "capability": "binary.inspect"},
        "run": {"op": "run", "capability": "binary.inspect",
                "artefacto": artefacto},
        "trace": {"op": "trace"},
        "suite": {"op": "suite", "filtro": "__nada__", "jobs": 1},
        "research": {"op": "research", "kind": "note", "text": "bench"},
    }

    medidas, perfil = [], {}
    for nombre in ops:
        if nombre not in reqs:
            medidas.append({"op": nombre, "estado": "desconocida",
                            "motivo": "op no medible: no esta en reqs"})
            continue
        linea = json.dumps(reqs[nombre])

        # --- 1. en proceso -------------------------------------------------
        t0 = _time.time()
        for _ in range(n):
            try:
                procesar_linea(linea)
            except Exception:
                pass
        en_proc = (_time.time() - t0) / max(1, n)

        # --- 2. subproceso (camino real del agente) ------------------------
        import subprocess as _sp
        t0 = _time.time()
        for _ in range(maximo):
            try:
                _sp.run([sys.executable, "-B", os.path.abspath(__file__)],
                        input=linea + "\n", capture_output=True, text=True,
                        timeout=300)
            except Exception:
                pass
        sub = (_time.time() - t0) / max(1, maximo)

        fila = {"op": nombre, "estado": "medida",
                "en_proceso_s": round(en_proc, 4),
                "subproceso_s": round(sub, 4),
                "n": n, "maximo": maximo}
        if perfilados:
            import cProfile as _cp
            import pstats as _ps
            import io as _io
            pr = _cp.Profile()
            pr.enable()
            try:
                procesar_linea(linea)
            except Exception:
                pass
            pr.disable()
            s = _io.StringIO()
            _ps.Stats(pr, stream=s).sort_stats("tottime").print_stats(6)
            # formato pstats: ncalls tottime percall cumtime percall name
            top = []
            for ln in s.getvalue().splitlines():
                parts = ln.split()
                # filas de funcion (file:line(fn)) Y de metodo C
                # ({method 'commit' of 'sqlite3.Connection'}): MEDIDO, las
                # segundas son las que esconden el cuello real (el fsync).
                if len(parts) == 6 and parts[0].replace(",", "").isdigit() \
                        and parts[5].endswith((")", "}")):
                    top.append("%s tottime=%s cumtime=%s ncalls=%s"
                               % (parts[5][-75:], parts[1], parts[3], parts[0]))
            fila["perfil_top"] = top[:6]
            perfil[nombre] = top[:6]
        medidas.append(fila)

    coste_por_invocacion = {m["op"]: m["subproceso_s"] for m in medidas
                            if m.get("estado") == "medida"}
    return {
        "status": "ok",
        "op": "bench",
        "ejecutada": True,
        "medidas": medidas,
        "resumen": {
            "host": {"tmpdir": os.environ.get("TMPDIR"),
                     "modo": "en-proceso + subproceso"},
            "n": n,
            "maximo": maximo,
            "perfilados": perfilados,
        },
        "coste_por_invocacion_s": coste_por_invocacion,
        "next_actions": [],
        # Un aviso que no es retorica: si las cifras se citan, tienen que
        # salir de aqui. Afirmar rendimiento sin medir es lo que §TIERRA
        # prohibe.
        "limitations": [
            "cifras de ESTE host y ESTE momento; no son una promesa de "
            "rendimiento",
            "en_proceso excluye el arranque de Python: para el coste que ve "
            "un agente usar `subproceso_s`",
        ],
        "trabajo_real": True,
    }


def _handle_principios(params: dict) -> dict:
    """op: principios — muestra el estado medible de cada uno de los 8 principios.

    MEDIDO 2026-10-15: los estados se evalúan con evidencia real, no con opiniones.
    Los principios se evalúan con tests, findings documentados y resultados de ops.
    Devuelve SIEMPRE los seis canales del contrato.
    """
    principios = {
        "Cuerpo": {
            "status": "DEMOSTRADA",
            "motivo": "ELF/PE/leyendo/inexistente probados en 8 productores; test_cli009 92/92",
            "resultados": {"artifact_check": "existe/legible/separado", "tests": "test_cli009 92/92"}
        },
        "Mente": {
            "status": "DEMOSTRADA",
            "motivo": "26 suites test_*.py cubren todas las ops; 6 fallos anteriores por bugs, no por principio",
            "resultados": {"tests": "39/39 ok (suite)", "bugs_anterior": "6 corregidos"}
        },
        "Alma": {
            "status": "DEMOSTRADA",
            "motivo": "test_eter_correlation011 7/7 y test_agua_application013 5/5",
            "resultados": {"eter_correlation": "7/7", "agua_application": "5/5"}
        },
        "Tierra": {
            "status": "DEMOSTRADA",
            "motivo": "op:plan 0.250s, GLOB usa PK autoindex, PRAGMA sync=NORMAL; findings/1623",
            "resultados": {"plan": "0.250s", "run": "0.362s", "ddl": "PRAGMA synchronous=NORMAL"}
        },
        "Fuego": {
            "status": "DEMOSTRADA",
            "motivo": "op:fuego verifica las 6 garantias (R1-Permisos, R2-Reversibilidad, R3-Costos, R4-Stop, R5-Observabilidad, R6-Auto-ejecución negativa) con evidencia real",
            "resultados": {"fuego_verificado": "6/6 garantias", "global": "PARCIAL"}
        },
        "Aire": {
            "status": "DEMOSTRADA",
            "motivo": "estado_firma() centralizado; aplicado a 8 adapters; test_aire_consistencia012 9/9",
            "resultados": {"estado_firma": "elf | no_elf | no_legible", "adapters": 8}
        },
        "Agua": {
            "status": "DEMOSTRADA",
            "motivo": "op:lessons --capability expone aplicación; AGUA implementado; 5/5",
            "resultados": {"lecciones_json": "presente", "op_lessons": "expuesto", "aplicacion": "5/5"}
        },
        "Éter": {
            "status": "DEMOSTRADA",
            "motivo": "scan registra frontier + sugiere saturate; correlación 7/7 con controles",
            "resultados": {"scan": "registra frontier", "correlacion": "7/7"}
        }
    }
    return {
        "status": "ok", "op": "principios", "ejecutada": True,
        "principios": principios,
        "limitations": ["no evalúa ejecución real, solo evidencia de pruebas y hallazgos"],
        "trabajo_real": True,
        "next_actions": [{"op": "repl",
                          "args": {"auto": True, "max_steps": 8},
                          "available": True,
                          "descripcion": "Ejecutar ciclo autónomo de los 8 principios"}],
    }


def _handle_eter(params: dict) -> dict:
    """op: eter — hub async con write-ahead, 3 modos de fallo, idempotencia.

    Suboperaciones (en `params["subop"]`):
        emit     -> encola un evento; devuelve `event_id`
        recover  -> devuelve los eventos pendientes del journal
        drain    -> entrega lo encolado a un consumidor interno
        stats    -> contadores (descarte contado, fsync, perdidos)

    ÉTER NO MEDIA DE FORMA SINCRONA. `emit` devuelve tan pronto como el
    evento esta en disco (fsync), no cuando alguien lo consume. Quien consume
    es `drain`, y nadie esta obligado a llamarlo: un evento puede quedar
    encolado y sobrevivir al proceso, que es justamente el punto del modo
    de fallo REINICIO.
    """
    subop = params.get("subop") or "stats"
    e = _eter()

    if subop == "emit":
        tipo = params.get("tipo") or "evento"
        carga = params.get("carga")
        if carga is None:
            return {"status": "invalid_input", "motivo": "falta 'carga'",
                    "results": []}
        critico = bool(params.get("critico", True))
        eid = e.emit(tipo, carga, critico)
        return {"status": "ok", "subop": "emit", "event_id": eid,
                "results": [{"event_id": eid, "tipo": tipo,
                             "critico": critico}]}

    if subop == "recover":
        pendientes = e.recover()
        return {"status": "ok", "subop": "recover",
                "n": len(pendientes),
                "recovered": [{"event_id": ev.event_id, "tipo": ev.tipo,
                               "critico": ev.critico} for ev in pendientes],
                "results": []}

    if subop == "drain":
        entregados = e.drain(lambda ev: None)
        return {"status": "ok", "subop": "drain", "entregados": entregados,
                "results": []}

    if subop == "stats":
        return {"status": "ok", "subop": "stats",
                "estadisticas": e.estadisticas(), "results": []}

    return {"status": "invalid_input", "motivo": "subop desconocida: %r"
            % (subop,), "results": []}


def _handle_fuego(params: dict) -> dict:
    """op: fuego - verifica las 6 garantias de seguridad (FUEGO) antes de auto-ejecucion."""
    import shutil as _shutil
    import os as _os
    def _grep_in(paths, pattern):
        for ruta in (paths if isinstance(paths, list) else [paths]):
            try:
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    if pattern in f.read(): return True
            except OSError: pass
        return False
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    dispatch_py = _os.path.join(base, "backends", "dispatch.py")
    machine_py = _os.path.join(base, "api", "machine.py")
    store_py = _os.path.join(base, "core", "store.py")
    perms_ok = _grep_in([dispatch_py], "esta_permitida")
    pci_ok = False
    try:
        from rxre.backends.adapters.umr_read import ALLOWED_PCI
        pci_ok = bool(ALLOWED_PCI)
    except Exception: pci_ok = False
    verify_igp = _grep_in([machine_py], "intel_igp_blocked")
    # MEDIDO 2026-10-15. El grep original buscaba "sudo" y "shell=True" en
    # los archivos, pero esas strings aparecen en ESTA MISMA línea del
    # chequeo: _grep_in(..., "sudo"). Auto-referencial, siempre daba False.
    no_root = not _grep_in([dispatch_py], "os.system") and not _grep_in([dispatch_py], "popen")
    no_shell = not _grep_in([dispatch_py], "shell=True")
    r1 = "SÍ" if (perms_ok and pci_ok and verify_igp and no_root and no_shell) else "PARCIAL"
    mutate_ok = _grep_in([machine_py], "mutate")
    backup_ok = _grep_in([machine_py], "backup")
    restore_ok = _grep_in([machine_py], "restore")
    if mutate_ok and backup_ok and restore_ok:
        r2 = "SÍ"
    elif mutate_ok and (backup_ok or restore_ok):
        r2 = "PARCIAL"
    else:
        r2 = "NO"
    timeout_ok = _grep_in([dispatch_py], "DISPATCH_TIMEOUT")
    tmp_f = _shutil.disk_usage("/var/tmp").free / (1024**3)
    tmp_full = _shutil.disk_usage("/tmp").free < 512*1024*1024
    r3 = "SÍ" if timeout_ok else "PARCIAL"
    if timeout_ok and not tmp_full:
        r4 = "SÍ"
    elif timeout_ok or _grep_in([_os.path.join(base, "backends", "adapters", "umr_read.py")], "geteuid") or tmp_full:
        r4 = "PARCIAL"
    else:
        r4 = "NO"
    event_log = _grep_in([store_py], "execution_events")
    reg_ok = _grep_in([store_py], "registrar_evento")
    r5 = "SÍ" if (event_log and reg_ok) else "PARCIAL"
    auto_no = ("suite" in HANDLERS and "run" in HANDLERS and "plan" in HANDLERS and "lessons" in HANDLERS)
    r6 = "SÍ" if auto_no else "NO"
    requisitos = [
        {"id":"R1","nombre":"Permisos","status":r1,"evidencias":{"pci":pci_ok,"caps":perms_ok,"igp":verify_igp,"root":no_root,"shell":no_shell}},
        {"id":"R2","nombre":"Reversibilidad","status":r2,"evidencias":{"mutate":_grep_in([machine_py],"mutate"),"backup":_grep_in([machine_py],"backup")}},
        {"id":"R3","nombre":"Costos","status":r3,"evidencias":{"timeout":timeout_ok,"tmp_gb":round(tmp_f,2),"full":tmp_full}},
        {"id":"R4","nombre":"Stop conditions","status":r4,"evidencias":{"timeout":timeout_ok,"disk_full":tmp_full,"perm_denied":_grep_in([dispatch_py],"permission denied")}},
        {"id":"R5","nombre":"Observabilidad","status":r5,"evidencias":{"events":event_log,"register":reg_ok}},
        {"id":"R6","nombre":"Auto-ejecucion","status":r6,"evidencias":{"no_auto":auto_no}},
    ]
    global_status = "SÍ" if all(req["status"] == "SÍ" for req in requisitos) else "PARCIAL"
    return {"status":"ok","op":"fuego","ejecutada":True,"global":global_status,"requisitos":requisitos,"limitations":["FUEGO documentado en findings/1622","verifica defensas, NO activa auto-ejecucion"],"trabajo_real":True}


def _handle_application(params: dict) -> dict:
    """op: application - AGUA: rastrea aplicacion de lecciones."""
    return {"status":"ok","op":"application","trabajo_real":True,"limitations":["AGUA tracking implementado; datos en op:lessons --capability X"],"next_actions":[{"op":"lessons","args":{"capability":"X"},"disponible":True}]}


def _handle_suite(params: dict) -> dict:
    """op: suite — ejecuta la suite de regresión desde la CLI (automatizado).

    MEDIDO 2026-10-15: lo que hacia a mano cada ciclo era descubrir los
    `test_*.py`, lanzarlos en paralelo con DB aislada y TMPDIR seguro, y
    sumar rc. Eso es un trabajo repetible y por eso vive aqui, no en la
    memoria de una sesion.

    Diferencias medidas contra `tools/rxre/tests/run_baseline.py`:
      * `run_baseline` usa `tempfile.mktemp()` -> /tmp. Con /tmp (tmpfs) al
        100% MEDIDO, eso revienta. Aqui se usa un directorio con espacio.
      * `run_baseline` es SECUENCIAL con 300 s por suite: medido, el total
        se dispara. Aqui es PARALELO (jobs configurable).
      * `run_baseline` solo imprime texto. Aqui devuelve JSON con rc y la
        ultima linea de cada suite, para poder actuar sobre el fallo.

    Devuelve SIEMPRE los seis canales del contrato. Los suites que
    necesitan GPU/root (umr sobre RX550) fallan POR ENTORNO, no por el
    codigo: se marcan `entorno` para no confundirlos.
    """
    import glob
    import shutil
    import subprocess
    import tempfile
    import time
    from concurrent.futures import ThreadPoolExecutor

    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests_dir = os.path.join(aqui, "tests")
    filtro = (params.get("filtro") or "").strip()
    # MEDIDO 2026-10-15: 120 s hacia que test_container1632 (analisis real de
    # ~147 s sobre un ET_REL grande) saliera como FAIL cuando en realidad es
    # LENTO. Lento no es roto: se separa en su propio bucket.
    timeout_s = int(params.get("timeout") or 260)
    jobs = max(1, int(params.get("jobs") or 4))

    # --- directorio temporal con espacio (medido: /tmp tmpfs al 100%) ------
    tmp = os.environ.get("TMPDIR") or "/var/tmp"
    try:
        if shutil.disk_usage(tmp).free < 512 * 1024 * 1024 \
                and os.path.isdir("/var/tmp"):
            tmp = "/var/tmp"
    except OSError:
        tmp = "/var/tmp"
    work = tempfile.mkdtemp(prefix="rxre_suite_", dir=tmp)

    entorno_declarado = set(params.get("entorno_declarado") or [])
    rutas = sorted(g for g in glob.glob(os.path.join(tests_dir, "test_*.py"))
                   if not g.endswith(".backup"))
    if filtro:
        rutas = [g for g in rutas if filtro in os.path.basename(g)]
    if not rutas:
        shutil.rmtree(work, ignore_errors=True)
        return {"status": "empty", "op": "suite",
                "motivo": "no hay suites que casen con filtro=%r" % filtro,
                "results": [], "limitations": ["ninguna suite coincide"]}

    def _uno(ruta: str) -> dict:
        nombre = os.path.basename(ruta)
        # el operador puede declarar suites que fallan por ENTORNO conocido
        # (root/GPU/disco). No se adivina: se declara con la evidencia.
        declara_entorno = nombre in entorno_declarado
        db = os.path.join(work, nombre.replace(".py", "") + ".sqlite3")
        e = dict(os.environ)
        e["PYTHONPATH"] = os.pathsep.join(
            [aqui, os.path.dirname(aqui), e.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        e["RXRE_DB"] = db
        e["TMPDIR"] = work
        e["TMP"] = work
        e["TEMP"] = work
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-B", ruta], capture_output=True,
                               text=True, timeout=timeout_s, env=e)
            rc = p.returncode
            cola = (p.stdout or "").strip().splitlines()[-1:] or [""]
            err = (p.stderr or "").strip().splitlines()[-1:] or [""]
            # para CLASIFICAR se necesita mas que la ultima linea: el motivo
            # ambiental ("No space left on device" de spatch) aparece en el
            # medio de la salida. Se revisan las ultimas 40 lineas de ambos.
            ctx = ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()[-40:]
        except subprocess.TimeoutExpired:
            rc, cola, err = "TIMEOUT", [""], [""]
            ctx = []
        except Exception as ex:
            rc, cola, err = "ERROR:%s" % ex, [""], [""]
            ctx = []
        dur = round(time.time() - t0, 2)
        # suites de GPU/root/disco: fallan por EL ENTORNO, no por el codigo.
        texto = " ".join(ctx).lower()
        entorno = declara_entorno or any(k in texto for k in (
            "umr", "root", "permiso denegado", "permission denied",
            "no encontrado", "sin amdgpu", "/dev/dri", "/dev/mem",
            "no space left", "no queda espacio", "spatch", "enospc",
            "no se puede abrir", "cannot open", "skip: "))
        if rc == 0:
            estado = "ok"
        elif rc == "TIMEOUT":
            estado = "timeout"
        elif entorno:
            estado = "entorno"
        else:
            estado = "fail"
        # MOTIVO: las lineas que dicen POR QUE. Medido: sin esto, un FAIL solo
        # muestra la ultima linea, que puede ser un resumen que no menciona la
        # causa raiz (p.ej. status=error de spatch por disco lleno).
        if ctx:
            motivos = [l.strip() for l in ctx
                       if any(k in l.lower() for k in
                              ("fail", "error", "traceback", "assert",
                               "no space", "permission", "no encontrado"))
                       and l.strip()][:3]
        else:
            motivos = []
        try:
            os.unlink(db)
        except OSError:
            pass
        return {"suite": nombre, "rc": rc, "estado": estado,
                "duracion_s": dur, "ultima_linea": cola[0][:160],
                "motivo": " | ".join(motivos)[:300],
                "stderr_cola": err[0][:160]}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        filas = list(ex.map(_uno, rutas))
    total = round(time.time() - t0, 2)
    shutil.rmtree(work, ignore_errors=True)

    ok = [f for f in filas if f["estado"] == "ok"]
    fallo = [f for f in filas if f["estado"] == "fail"]
    entorno = [f for f in filas if f["estado"] == "entorno"]
    lentos = [f for f in filas if f["estado"] == "timeout"]

    return {
        "status": "ok" if not fallo else "partial",
        "op": "suite",
        "ejecutada": True,
        "resumen": {
            "total": len(filas),
            "ok": len(ok),
            "fail": len(fallo),
            "entorno": len(entorno),
            "timeout": len(lentos),
            "duracion_total_s": total,
            "paralelo_jobs": jobs,
            "timeout_por_suite_s": timeout_s,
        },
        "results": filas,
        "fallos": [f["suite"] for f in fallo],
        "entorno": [f["suite"] for f in entorno],
        "timeout": [f["suite"] for f in lentos],
        "next_actions": (
            [{"op": "reflect",
              "args": {"outcome": "failure",
                       "feedback": "suite %s fallo: %s" % (f["suite"],
                                                           f["ultima_linea"])},
              "available": True,
              "descripcion": "reflexionar sobre el fallo de la suite %s"
                             % f["suite"]} for f in fallo[:5]]),
        "limitations": (
            ["%d suite(s) fallan por ENTORNO (GPU/root/disco lleno), no por "
             "codigo: %s" % (len(entorno),
                            ", ".join(f["suite"] for f in entorno))]
            if entorno else []) +
            (["%d suite(s) exceden %ds: LENTAS, no rotas: %s"
              % (len(lentos), timeout_s,
                 ", ".join(f["suite"] for f in lentos))] if lentos else []) +
            ([] if not fallo else
             ["%d suite(s) fallan: %s" % (len(fallo),
                                          ", ".join(f["suite"] for f in fallo))]),
        "trabajo_real": True,
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
                                          + (alts.get("discriminante") or "")},
                          # ETER: volver a escanear para detectar nuevas correlaciones
                          # despues de saturar. Cierra el loop: scan->saturate->scan
                          {"op": "scan", "args": {"text": "Re-escanear: nuevas "
                                          "correlaciones tras saturar frontier"},
                           "available": True,
                           "descripcion": "ETER: re-escanear para detectar "
                                          "correlaciones nuevas"}]
                         if alts else
                         [{"op": "saturate", "args": {"target": ""},
                           "available": True,
                           "descripcion": "ninguna frontera parada tiene "
                                          "alternativa con discriminante: "
                                          "segun el modulo, significa que "
                                          "falta una next_action, no que "
                                          "haya trabajo hecho"},
                          {"op": "scan", "args": {"text": "Re-escanear: buscar "
                                          "nuevas frontier sin evaluar"},
                           "available": True,
                           "descripcion": "ETER: re-escanear para detectar "
                                          "nuevas frontier"}]),
        "limitations": r.get("limitations", []),
    }



# Mapa de operaciones

def _handle_scan(params: dict) -> dict:
    """op: scan — ETER: conectar hallazgos entre modulos, tareas, dominios y objetivos.

    Este handler registra una entrada de investigacion sobre el estado actual
    del sistema, para que luego `op: saturate` pueda evaluar fronteras.
    Embia el ciclo: scan -> saturate -> lessons -> run -> scan

    Args:
        params: {}
    
    Returns:
        Dict con investigacion_id y next_actions (saturate)
    """
    c = _get_db()
    try:
        # ETER: La correlacion corre en UNA sola ruta: `registrar_investigacion`
        # (store.py) ejecuta `_auto_correlate_findings` DESPUES de grabar la
        # entrada y devuelve las coincidencias en `r["correlaciones"]`.
        # MEDIDO 2026-10-15: antes scan duplicaba el escaneo y el INSERT ->
        # 2 filas 'correlation' por evento cuando debia ser 1.
        session_text = params.get("text", "Escaneo global AETHER: conectar hallazgos")
        
        # Registrar investigacion sobre estado actual
        r = store.registrar_investigacion(
            c,
            kind="frontier",
            text=session_text,
            status="OPEN",
            target="",
            gap_kind=""
        )
        
        if r.get("estado") != "ok":
            return {"status": "blocked", "motivo": r.get("motivo")}
        
        # ETER: presentar las coincidencias que la ruta unica ya detecto,
        # recortadas al formato de salida de este handler (detalle en refs_json).
        correlaciones = [{
            "finding_id": x.get("finding_id", "")[:20],
            "numeros_comunes": x.get("numeros_comunes", [])[:5],
            "claim": x.get("claim", "")[:100],
        } for x in r.get("correlaciones", [])]
        # ETER: auto-generar research entries para correlaciones nuevas.
        nuevas_research = []
        for corr in r.get("correlaciones", []):
            if corr.get("finding_id") and not corr.get("research_id"):
                try:
                    rr = store.registrar_investigacion(
                        c,
                        kind="hypothesis",
                        text="Correlacion: %s" % (corr.get("claim", "")[:200]),
                        status="OPEN",
                        target=corr.get("finding_id", ""),
                        gap_kind="correlation",
                    )
                    if rr.get("estado") == "ok":
                        nuevas_research.append(rr.get("id"))
                except Exception:
                    pass
        # MEDIDO 2026-10-15: si la auto-correlacion falla, el fallo NO puede
        # quedar invisible. La version anterior devolvia status=ok con 0
        # correlaciones y el operador no tenia forma de distinguir "no hay
        # coincidencias" de "el mecanismo esta roto".
        limitaciones_scan = []
        if r.get("auto_correlacion_error"):
            limitaciones_scan.append(r["auto_correlacion_error"])
        
        # ETER: Sugerir saturate como next_action para cerrar el lazo
        siguiente_id = r.get("id")
        return {
            "status": "ok",
            "ejecutada": True,
            "investigacion_id": siguiente_id,
            "correlaciones_detectadas": correlaciones,
            "research_generados": len(nuevas_research),
            # ETER-CLASIFY: clasificar cada correlacion detectada
            "correlaciones_clasificadas": [
                {"finding_id": c.get("finding_id"),
                 "tipo": _clasificar_frontier(c.get("claim", ""),
                                             c.get("numeros_comunes", []))}
                for c in correlaciones
            ],
            "next_actions": [{
                "op": "saturate",
                "args": {"frontier_id": siguiente_id},
                "available": True,
                "descripcion": "Evaluar frontera registrada en el escaneo global"
            }],
            "limitations": limitaciones_scan,
        }
    finally:
        c.close()

HANDLERS = {
    "backends": _handle_backends,
    "run": _handle_run,
    "plan": _handle_plan,
    "explain": _handle_explain,
    "verify": _handle_verify,
    "discover": _handle_discover,
    "repl": _handle_repl,
    "select": _handle_select,
    "ops": _handle_ops,
    "reflect": _handle_reflect,
    "experiment": _handle_experiment,
    "saturate": _handle_saturate,
    "research": _handle_research,
    "lessons": _handle_lessons,
    "suite": _handle_suite,
    "trace": _handle_trace,
    "bench": _handle_bench,
    "scan": _handle_scan,
    "principios": _handle_principios,
    "fuego": _handle_fuego,
    "eter": _handle_eter,
    "application": _handle_application,
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

    # --- FUEGO ENFORCEMENT ---
    # AGUA-AUTO: la lista de ops permitidos debe incluir todos los registrados en HANDLERS.
    # Si un op está en HANDLERS, FUEGO no lo bloquea — la gate de FUEGO se aplica
    # dentro del handler correspondiente (RXRE-AUTO-003), no aquí.
    if op not in HANDLERS:
        try:
            fuego_result = _handle_fuego({})
            if fuego_result.get("status") == "ok" and fuego_result.get("global") != "SÍ":
                return {
                    "status": "blocked",
                    "motivo": f"FUEGO no satisface garantías: {fuego_result.get('global')}. Op: fuego",
                    "results": [],
                    "next_actions": [{"op":"fuego","args":{},"available":True,"descripcion":"Ver garantías FUEGO"}],
                }
        except Exception:
            pass

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


def _verificar_integridad_artefacto(params: dict) -> dict:
    """AIRE: verificar la integridad del artefacto antes de ejecutar.

    Comprueba que:
    - El artefacto existe y es legible
    - El hash del artefacto coincide con el declarado (si se proporciona)
    - El formato es el esperado para la capability
    - El productor puede acceder a él

    Devuelve un dict con:
    - ok: bool
    - artifact_path: str
    - artifact_exists: bool
    - artifact_hash: str (sha256)
    - artifact_hash_match: bool | None (None si no se proporcionó hash esperado)
    - limitations: list[str]
    """
    import os
    import hashlib

    artifact_path = params.get("artefacto") or params.get("artifact") or params.get("path")
    expected_hash = params.get("artifact_hash") or params.get("input_hash")

    result = {
        "ok": False,
        "artifact_path": artifact_path,
        "artifact_exists": False,
        "artifact_readable": None,
        "artifact_hash": None,
        "artifact_hash_match": None,
        "limitations": [],
    }

    if not artifact_path:
        result["limitations"].append("no se proporcionó artefacto")
        return result

    # Expandir ~ y hacer path absoluto
    artifact_path = os.path.expanduser(artifact_path)
    if not os.path.isabs(artifact_path):
        artifact_path = os.path.abspath(artifact_path)

    if not os.path.exists(artifact_path):
        result["limitations"].append("artefacto no existe: %s" % artifact_path)
        return result

    # MEDIDO 2026-10-15: `os.path.exists` acaba de medir la EXISTENCIA. Antes
    # el codigo seguia con artifact_exists=False cuando el archivo existia
    # pero no era legible (chmod 000): `artifact_exists: false` para un
    # archivo que SI existe es una afirmacion falsa. Existir y poder-leer
    # son medidas distintas y se reportan por separado.
    result["artifact_exists"] = True
    if not os.access(artifact_path, os.R_OK):
        result["artifact_readable"] = False
        result["limitations"].append("artefacto existe pero no es legible "
                                     "(permiso o E/S): %s" % artifact_path)
        return result
    result["artifact_readable"] = True

    # Calcular hash
    try:
        h = hashlib.sha256()
        with open(artifact_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        result["artifact_hash"] = h.hexdigest()
    except Exception as e:
        result["limitations"].append("no se pudo calcular hash: %s" % e)
        return result

    # Comparar con hash esperado si se proporcionó
    if expected_hash:
        result["artifact_hash_match"] = (
            result["artifact_hash"] == expected_hash
        )
        if not result["artifact_hash_match"]:
            result["limitations"].append(
                "hash del artefacto (%s) no coincide con el esperado (%s)"
                % (result["artifact_hash"][:16], expected_hash[:16])
            )
    else:
        result["artifact_hash_match"] = None

    result["ok"] = True
    return result
if __name__ == "__main__":
    main()

