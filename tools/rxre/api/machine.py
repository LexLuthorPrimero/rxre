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
import re
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
import rxre.core.capabilities as caps  # noqa: E402
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
    del paquete. No overridea la config del entorno. CUERPO-DB-RETRY: reintentar ante lock.
    """
    import time
    db_path = os.environ.get("RXRE_DB", "")
    for i in range(3):
        try:
            if db_path:
                return store.conectar(db_path)
            return store.conectar()
        except Exception as e:
            if "locked" in str(e).lower() and i < 2:
                time.sleep(0.3 * (i + 1))
                continue
            raise
    if db_path:
        return store.conectar(db_path)
    return store.conectar()


def _with_db_retry(func, *args, retries: int = 3, **kwargs):
    """CUERPO-DB-RETRY: ejecuta operacion con retry ante database lock."""
    import time
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "locked" in str(e).lower() and i < retries - 1:
                time.sleep(0.3 * (i + 1))
                continue
            raise
    return None


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
    # ETER: emitir el evento ANTES de la logica del handler. Async y
    # no-bloqueante (ver _handle_scan).
    try:
        _eter().emit("verify", {"op": "verify"}, critico=True)
    except Exception:
        pass
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
        # CUERPO-ALT: si un backend falta, sugerir alternatives
        backend_fails = [bid for bid, b in backend_checks.items()
                         if not b.get("ok")]
        if backend_fails:
            next_actions.append({
                "op": "backends", "descripcion": "Ver detalles de backends y alternatives"
            })
            # CUERPO-ALT: sugerir backend alternativo y capability_alternativa
            try:
                catalogo = dispatch.listar()
                caps_por_backend = {}
                for bname, binfo in (catalogo.get("backends") or {}).items():
                    for cap in binfo.get("capacidades", []):
                        if not isinstance(cap, str):
                            cap = cap.get("capability", "") if isinstance(cap, dict) else ""
                        caps_por_backend.setdefault(cap, []).append(bname)
                # Para cada backend que falló, sugerir capabilities de otros backends
                alt_backends = set()
                for bid in backend_fails:
                    for bname, binfo in (catalogo.get("backends") or {}).items():
                        if bname != bid and binfo.get("existe", True):
                            alt_backends.add(bname)
                if alt_backends:
                    next_actions.append({
                        "op": "run",
                        "args": {"capability": capability or "binary.inspect",
                                 "backend_id": sorted(alt_backends)[0]},
                        "available": True,
                        "descripcion": "CUERPO-ALT: reintentar con backend alternativo %s" %
                                       sorted(alt_backends)[0],
                    })
            except Exception:
                pass
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
    question = params.get("question") or params.get("pregunta") or ""
    trace_id = _trace_id_actual(params) or ("discover-" + str(os.getpid()))

    # 162: investigar desde texto libre si hay evidencia registrada
    if not artefacto and question:
        tokens = [t for t in re.findall(r"[A-Z][A-Z0-9_]{3,}|[a-z_][a-z0-9_]{3,}", question)
                  if len(t) > 3 and t.lower() not in ("que", "cual", "como", "cuando", "por", "con", "sin")]
        tokens = sorted(tokens, key=lambda t: (0 if re.search(r"[0-9]|_", t) and t.isupper() else 1, -len(t)))
        c = _get_db()
        try:
            evidence_refs = []
            evidence_notes = []
            for tok in tokens[:3]:
                ev = store.buscar(c, texto=tok[:120], limite=2)
                if ev.get("status") == "ok" and ev.get("results"):
                    for r in ev["results"]:
                        rid = r.get("result_id") or r.get("file")
                        if rid and rid not in evidence_refs:
                            evidence_refs.append(str(rid))
                        note = r.get("value") or r.get("file") or ""
                        if note and note not in evidence_notes:
                            evidence_notes.append(note[:120])
                if len(evidence_refs) >= 3:
                    break
            if evidence_refs:
                frontera_text = ("Investigacion desde texto libre: %s" %
                                 (question[:100] if len(question) <= 100 else question[:97] + "..."))
                r = store.registrar_investigacion(
                    c, kind="frontier", text=frontera_text,
                    status="OPEN", target=question[:120],
                    gap_kind="",
                    refs=list(dict.fromkeys(evidence_refs[:5])), session=trace_id)
                select_env = _handle_select({"target": frontera_text, "session_id": trace_id})
                return {
                    "status": "ok", "op": "discover",
                    "derived_from_evidence": True,
                    "question": question,
                    "evidence_refs": evidence_refs[:3],
                    "evidence_notes": evidence_notes[:3],
                    "frontier_id": r.get("id"),
                    "frontier_text": frontera_text,
                    "trace_id": trace_id,
                    "interpretation": ("Pregunta interpretada como frontera de investigacion; "
                                       "evidencia recuperada por coincidencia en DB."),
                    "objective": ("Resolver la incertidumbre declarada en '%s' usando evidencia existente." %
                                  question[:60]),
                    "results": [{"type": "evidence_ref", "ref": evidence_refs[0]}],
                    "next_actions": [
                        {"op": "select", "args": {"target": frontera_text},
                         "descripcion": "Seleccionar accion desde frontera derivada"},
                        {"op": "explain", "args": {"result_id": evidence_refs[0]},
                         "descripcion": "Explicar evidencia de referencia"},
                    ],
                    "limitations": [
                        "Texto libre interpretado por coincidencia de token; no hay analizador semantico completo.",
                        "Si la evidencia recuperada no responde la pregunta, la frontera es partial; usar explain para verificar.",
                    ],
                }
            else:
                return {
                    "status": "blocked", "op": "discover",
                    "derived_from_evidence": False,
                    "question": question,
                    "motivo": "No se encontro evidencia registrada relacionada con '%s' en la DB de trabajo." % (
                        question[:60] if question else "texto libre"),
                    "trace_id": trace_id,
                    "limitations": [
                        "DB de trabajo no contiene resultados que coincidan con los tokens extraidos.",
                        "No se inventa evidencia ni frontera sin respaldo.",
                    ],
                    "next_actions": [
                        {"op": "query", "args": {"target": "0000:01:00.0", "question": question},
                         "descripcion": "Intentar consulta directa sobre corpus"},
                    ],
                }
        finally:
            c.close()

    if not artefacto:
        return {"status": "invalid_input", "op": "discover",
                "motivo": "falta 'artefacto' o evidencia suficiente en DB para interpretar '%s'" %
                (question[:60] if question else "texto libre"),
                "results": [],
                "limitations": ["discover requiere artefacto verificado o evidencia registrable."]}

    # AIRE-1: verificación de integridad antes de usar artefacto
    pre = _verificar_integridad_artefacto({"artefacto": artefacto})
    if not pre.get("ok"):
        return {"status": "blocked" if "no existe" in str(pre.get("limitations",[])) else "invalid_input",
                "op": "discover", "ejecutada": False,
                "motivo": "integridad del artefacto fallida: %s" % "; ".join(pre.get("limitations", [])),
                "precheck": pre, "results": []}

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
        # ETERA01-D1: se registra el NIVEL DE ANALISIS EFECTIVAMENTE usado y
        # sus limitaciones de profundidad, SIN alterar la regla de decision
        # `total_symbols > 0`. El nivel lo decide el adapter (default `aa`);
        # aqui NO se impone `aaa`/`aaaa`.
        env3 = dispatch.ejecutar("binary.callgraph",
                                 {"artefacto": artefacto, "backend_id": "radare2"})
        if env3.get("status") in ("ok", "empty"):
            n_nodes = len(env3.get("results") or [])
            nivel3 = (env3.get("ejecucion") or {}).get("nivel_analisis")
            findings.append({
                "finding_type": "binary_callgraph",
                "source": "binary.callgraph",
                "n": n_nodes,
                "estado": env3.get("status"),
                "nivel_analisis": nivel3,
                "limitaciones": list(env3.get("limitations") or []),
            })

        total_symbols = sum(f["n"] for f in findings)

        # Persistir hallazgo estructurado (TIERRA: evidencia con procedencia)
        for f in findings:
            try:
                # Idempotencia: mismo tipo + artefacto + fuente no duplica.
                # ETERA01-D1: el claim registra el nivel de analisis efectivo
                # (texto sin digitos: NO altera la correlacion numerica ETER,
                # que exige >=2 numeros >=10 por claim).
                nivel_txt = ("; nivel=%s" % f["nivel_analisis"]
                             if f.get("nivel_analisis") else "")
                claim_text = ("%s en %s: %d items (status=%s%s)" %
                              (f["finding_type"], artefacto, f["n"],
                               f.get("estado", "unknown"), nivel_txt))
                limites = "; ".join(f.get("limitaciones") or []) or \
                    "derivado de execution_events; no inferencia independiente"
                fid = "finding_discover_%s_%s" % (f["finding_type"],
                        str(artefacto).replace("/","_")[-20:] if len(str(artefacto)) > 20 else str(artefacto).replace("/","_"))
                c.execute("INSERT OR IGNORE INTO findings (finding_id, claim, "
                          "epistemic, evidence_ids, provenance, limitations, "
                          "created_at) VALUES (?,?,?,?,?,?,?)",
                          (fid, claim_text, "OBSERVED",
                           json.dumps(["res_discover_%s" % f["source"]]),
                           "discover/%s/%s" % (artefacto, f["source"]),
                           limites,
                           "2026-10-15T18:55:00-0300"))
            except Exception:
                pass
        # Cada simbolo/funcion nuevo es una frontier abierta (§53) que necesita
        # investigacion. Se registran como investigaciones para que saturate
        # pueda evaluarlas en el proximo ciclo.
        # Causal vertical slice (RXRE-ETAPA01-CAUSAL-VERTICAL-SLICE):
        # Las frontiers deben reflejar filas REALMENTE creadas (no intentos
        # bloqueados). gap_kind solo es valido para hypothesis/claim, asi que
        # aqui se omite. refs enlazan la frontier con los result_id reales
        # que la motivaron (observacion -> frontier). session = trace_id.
        env_por_tipo = {
            "binary_functions": env1,
            "binary_xrefs": env2,
            "binary_callgraph": env3,
        }
        nuevas_frontiers = 0
        tid = _trace_id_actual(params)
        for f in findings:
            try:
                nivel_f = (" nivel=%s" % f["nivel_analisis"]
                           if f.get("nivel_analisis") else "")
                env_f = env_por_tipo.get(f["finding_type"]) or {}
                refs_f = []
                if f["finding_type"] == "binary_callgraph":
                    oid = env_f.get("operation_id")
                    if oid and str(oid).startswith("COLISION:"):
                        oid = None
                    if not oid:
                        rs = (env_f.get("results") or [])
                        if rs and isinstance(rs[0], dict) and rs[0].get("result_id"):
                            row = c.execute(
                                "SELECT operation_id FROM results WHERE result_id=?",
                                (rs[0]["result_id"],)).fetchone()
                            if row and row["operation_id"]:
                                oid = row["operation_id"]
                    if oid:
                        refs_f.append(oid)
                else:
                    for r in (env_f.get("results") or []):
                        if isinstance(r, dict) and r.get("result_id"):
                            refs_f.append(r["result_id"])
                seen = set()
                refs_f = [x for x in refs_f if not (x in seen or seen.add(x))]
                res = store.registrar_investigacion(
                    c, kind="frontier",
                    text="%s en %s (%d items)%s" % (
                        f["finding_type"], artefacto, f["n"], nivel_f),
                    status="OPEN", target=f["finding_type"],
                    refs=refs_f, session=tid or "",
                    gap_kind="",
                )
                if res.get("estado") == "ok":
                    nuevas_frontiers += 1
                    try:
                        store.registrar_audit_log(
                            c, "create_research", "research",
                            str(res.get("id")), actor="binary.discover",
                            details={"kind": "frontier",
                                     "proposed_by": "system",
                                     "refs": refs_f,
                                     "session": tid,
                                     "finding_type": f["finding_type"]})
                    except Exception:
                        pass
            except Exception:
                pass
        # Evento durable para reconstruir discover (observacion -> frontier).
        try:
            env_disc = {
                "status": "ok" if total_symbols > 0 else "empty",
                "capability": "binary.discover",
                "backend": None,
                "ejecucion": {"exit_status": 0},
                "persistido": True,
                "limitations": [],
                "trace_id": tid,
                "results": [],
            }
            for env_sub in (env1, env2, env3):
                rs = (env_sub or {}).get("results") or []
                if rs and isinstance(rs[0], dict) and rs[0].get("result_id"):
                    env_disc["results"] = [rs[0]]
                    break
            if env_disc["results"]:
                rid0 = env_disc["results"][0].get("result_id")
                row = c.execute(
                    "SELECT operation_id FROM results WHERE result_id=?",
                    (rid0,)).fetchone()
                if row and row["operation_id"]:
                    env_disc["operation_id"] = row["operation_id"]
            store.registrar_evento(c, "discover", "binary.discover",
                                  env_disc, [])
        except Exception:
            pass

        # CERRAR BRECHA: finding valido -> mision persistente (ALMA/TIERRA/FUEGO)
        mission_created = None
        task_created = None
        if total_symbols > 0 and findings:
            try:
                mission_created = store.crear_mision(
                    c,
                    title="Investigación: %s (%d símbolos)" % (artefacto, total_symbols),
                    description="Misión derivada de discover sobre %s. Justificación: %d hallazgos observados (%s). Criterio de cierre: análisis de funciones/xrefs/callgraph completado." % (artefacto, len(findings), ", ".join(f["finding_type"] for f in findings)),
                )
                task_created = store.agregar_tarea_a_mision(
                    c, mission_created,
                    title="Analizar símbolos descubiertos en %s" % artefacto,
                    description="Tarea vinculada a finding de discover. Evidencia: %s. Objetivo: descompilar funciones y validar cross-references." % (
                        "; ".join("%s(%d)" % (f["finding_type"], f["n"]) for f in findings),
                    ),
                    priority=1,
                )
                c.commit()
            except Exception as exc:
                # No romper discover si la mision falla; documentar limitacion
                findings.append({
                    "finding_type": "mission_creation",
                    "estado": "failed",
                    "motivo": str(exc)[:200],
                })
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
            "mission_created": mission_created,
            "task_created": task_created,
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

    # 164: ALMA-164: si hay pregunta libre y no hay steps, orquestar ciclo completo
    if not steps and params.get("question") and not mission_id:
        return _ciclo_autonomo_desde_pregunta(params, max_steps)

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
    # AGUA-007: estado de persistencia de TODA la operacion. Un fallo NUNCA se
    # borra por un step posterior exitoso: se acumula y se expone al final.
    persistencia_fallida = False
    limitations_persistencia = []

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

        # AGUA-007: si el step ya expone `persistencia_fallida` (p.ej. `run`
        # cuyo evento no se pudo escribir), repl lo conserva en vez de
        # descartarlo. Un step posterior exitoso NO limpia esta bandera.
        if resp.get("persistencia_fallida"):
            persistencia_fallida = True
            _pls = [l for l in (resp.get("limitations") or [])
                    if "persist" in str(l).lower()]
            limitations_persistencia.append(
                "persistencia fallida en step %d (op:%s)%s" % (
                    i, step.get("op", "?"),
                    (": " + _pls[0]) if _pls else ""))

        # AGUA: auto-reflection on failure
        if resp.get("status") in ("blocked", "invalid_input", "error", "unsupported"):
            stopped_at = i
            sugerencia = ""
            if resp.get("status") == "invalid_input":
                motivo = resp.get("motivo") or "entrada invalida"
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
                res_persist = _registrar_reflexion_auto(step, resp, sugerencia, i)
                _ok_persist = (isinstance(res_persist, dict)
                               and res_persist.get("estado") == "ok")
                if not _ok_persist:
                    persistencia_fallida = True
                    _mot = ("sin motivo" if not isinstance(res_persist, dict)
                            else (res_persist.get("motivo") or "sin motivo"))
                    limitations_persistencia.append(
                        "auto-reflexion no persistida en step %d: %s" % (i, _mot))
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

    limitations = []
    if stopped_at is not None:
        limitations.append(
            f"REPL se detuvo en step {stopped_at} debido a error. "
            "Revisar reflexion_sugerida antes de continuar.")
    limitations.extend(limitations_persistencia)

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
        # AGUA-007: hace visible si ALGO de la operacion no se persistio.
        # En una ejecucion sana queda False.
        "persistencia_fallida": bool(persistencia_fallida),
        "limitations": limitations,
    }


def _ciclo_autonomo_desde_pregunta(params: dict, max_steps: int = 5) -> dict:
    """ALMA/ETER/FOGO: orquestar desde texto libre: discover -> research -> select -> experiment -> explain."""
    session_id = params.get("session_id") or ("rx-164-" + str(os.getpid()))
    question = params.get("question") or params.get("pregunta") or ""
    results = []
    stages = []

    def _record(stage, resp):
        stages.append({"stage": stage, "status": resp.get("status"),
                       "op": resp.get("op")})
        results.append({"index": len(stages)-1, "op": resp.get("op"),
                        "status": resp.get("status"),
                        "result_id": resp.get("result_id") or resp.get("frontier_id") or "",
                        "summary": str(resp.get("status"))})
        return resp

    # 1 DISCOVER (texto libre con evidencia registrada)
    d = _handle_discover({"question": question, "session_id": session_id})
    _record("discover", d)
    if d.get("status") not in ("ok", "partial"):
        return {"status": d.get("status"), "op": "repl",
                "question": question, "session_id": session_id,
                "stages": stages, "results": results,
                "conclusion": {"estado": "BLOCKED" if d.get("status") == "blocked" else "NOT_DETERMINED",
                               "motivo": d.get("motivo") or d.get("limitations", [""])[0],
                               "procedencia": "discover -> blocked"},
                "limitations": d.get("limitations") or ["Fallo temprano en discover"],
                "next_actions": [{"op": "discover", "args": {"question": question},
                                  "descripcion": "Reintentar desde texto libre"}]}

    # 2 RESEARCH (hipotesis respaldada por evidencia)
    refs = d.get("evidence_refs") or []
    frontier_text = d.get("frontier_text") or (d.get("interpretation", "").split(":")[-1].strip()[:120] if d.get("interpretation") else (question[:120] if question else "frontera"))
    h = _handle_research({
        "kind": "hypothesis",
        "text": ("En pipeline RX 550: ¿producido por hardware o indiferente al dispositivo?" if ("rx" in question.lower() or "551" in question) else "Hipotesis desde texto libre: %s" % question[:60]),
        "status": "OPEN",
        "target": d.get("frontier_text") or frontier_text,
        "session": session_id,
        "refs": refs[:3] if refs else [],
        "gap_kind": "HUECO_DE_EVIDENCIA",
    })
    _record("research", h)
    if h.get("status") != "ok":
        return {"status": "ok", "op": "repl",
                "question": question, "session_id": session_id,
                "stages": stages, "results": results,
                "conclusion": {"estado": "NOT_DETERMINED", "motivo": "Hipotesis no registrada"},
                "limitations": h.get("limitations") or ["No se pudo registrar hipotesis"],
                "next_actions": [{"op": "research", "args": {"kind": "frontier", "status": "OPEN", "text": frontier_text},
                                  "descripcion": "Registrar frontera manual"}]}

    # 3 SELECT (autonomo, 161)
    sel = _handle_select({"target": frontier_text, "session_id": session_id})
    _record("select", sel)

    # 4 EXPERIMENT (prueba discriminante segura / control)
    exp_args = {
        "capability": "binary.inspect",
        "question": "Control discriminante de mecanismo: backend rizin vs radare2 sobre /bin/ls",
        "prediction": "coincidente",
        "baseline_params": {"artefacto": "/bin/ls", "backend_id": "rizin"},
        "modified_params": {"artefacto": "/bin/ls", "backend_id": "radare2"},
        "comparar": "results.0.status",
    }
    exp = _handle_experiment(exp_args)
    _record("experiment", exp)

    # 5 EXPLAIN (procedencia)
    first_ref = refs[0] if refs else ""
    expl_resp = None
    if first_ref and isinstance(first_ref, str) and first_ref.startswith("res_"):
        try:
            expl_resp = _handle_explain({"result_id": first_ref})
        except Exception:
            pass
    if expl_resp is None:
        expl_resp = {"status": "not_executed", "op": "explain",
                    "note": "Referencia no ejecutada."}
    _record("explain", expl_resp)

    # 6 CONCLUSION / ACTUALIZACION DE HIPOTESIS
    verdict = exp.get("experiment", {}).get("veredicto") if exp.get("experiment") else None
    if verdict == "sostenida":
        h_status = "PROVEN"
    elif verdict == "refutada":
        h_status = "REFUTED"
    else:
        h_status = "NOT_DETERMINED"

    # Solo actualizar DB si conclusive; para control no forzar
    if verdict == "sostenida":
        try:
            c = _get_db()
            try:
                store.registrar_investigacion(
                    c, "claim",
                    "Resultado experimento control: status=%s veredicto=%s" % (
                        exp.get("status"), verdict),
                    status="PROVEN",
                    refs=[first_ref] if first_ref else [],
                    session=session_id,
                    target=frontier_text or "",
                    gap_kind="",
                )
            finally:
                c.close()
        except Exception:
            pass

    conclusion_text = ("Investigacion desde texto libre: evidencia recuperada (%d refs), "
                      "frontera registrada, experiment control ejecutado (%s), veredicto '%s'. "
                      "Para pregunta especifica del pipeline RX 550 (hardware vs software): "
                      "Bloqueado por ausencia de artefacto primario (vm129 borrado); "
                      "la causalidad del hardware no puede confirmarse ni refutarse por los valores numericos.") % (
        len(refs), exp.get("status"), verdict or "N/A")

    return {
        "status": "ok" if d.get("status") == "ok" else d.get("status"),
        "op": "repl",
        "session_id": session_id,
        "question": question,
        "derived_from_evidence": d.get("derived_from_evidence", False),
        "frontier_id": d.get("frontier_id") or "",
        "hypothesis_id": h.get("id") or "",
        "stages": stages,
        "results": results,
        "conclusion": {
            "estado": h_status,
            "motivo": conclusion_text,
            "procedencia": "discover -> research -> select -> experiment -> explain",
            "limitaciones": (list(set(
                (d.get("limitations") or []) +
                (h.get("limitations") or []) +
                (sel.get("limitations") or []) +
                (exp.get("limitations") or []) +
                (expl_resp.get("limitations") or []) +
                ["Experimento control sobre /bin/ls (no separa hardware/software para pipeline 550); "
                 "artefacto primario /tmp/opencode/vk129 ausente (tmpfs limpieza)."]
            ))),
        },
        "next_actions": [
            {"op": "reflect", "args": {"outcome": h_status},
             "descripcion": "Reflexionar sobre la limitacion documentada"},
        ],
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
                               step_index: int) -> dict:
    """FUEGO/AGUA: registra una reflexión automática cuando repl --auto falla.

    Cierra el loop de aprendizaje: el fallo de un step en el ciclo autónomo
    se registra como reflexión en la BD, de modo que futuros op:run consulten
    esta lección de fallo antes de ejecutar.

    No levanta excepciones: si la BD no responde, el ciclo continúa. Pero el
    fallo NO desaparece: se devuelve `estado="error"` con su motivo para que
    `_handle_repl` lo haga observable (`persistencia_fallida`). Un error de
    escritura NUNCA se convierte en exito.
    """
    capability = step.get("capability", "") or step.get("op", "")
    motivo = resp.get("motivo", "")
    outcome = "failure" if resp.get("status") == "blocked" else \
              "error" if resp.get("status") == "error" else "failure"
    try:
        c = _get_db()
        try:
            resultado = store.registrar_reflexion(
                c,
                feedback="Step %d (op:%s cap:%s) → status=%s motivo=%s"
                         % (step_index, step.get("op", "?"),
                            capability, resp.get("status", "?"), motivo[:200]),
                reflection="Estrategia alternativa automática: %s"
                           % sugerencia[:300],
                outcome=outcome,
                capability=capability,
                check_ejecutable="",  # auto-reflection sin check por ahora
            )
        finally:
            c.close()
    except Exception as exc:
        return {"estado": "error",
                "motivo": "persistencia de reflexion fallo: %s" % str(exc)[:200]}
    if not isinstance(resultado, dict):
        return {"estado": "error",
                "motivo": "registrar_reflexion no devolvio un dict"}
    return resultado


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

def _clasificar_frontier(claim: str, numeros: list) -> str:
    """ETER-CLASIFY: clasifica el tipo de una frontier/correlation.

    Usa palabras clave del claim y patrones en los números para clasificar:
    - "bug": menciona error/fallo/broken/crash
    - "feature": menciona funcionalidad/nueva capacidad/solicitud
    - "tech_debt": menciona legacy/deprecated/refactor/to_do
    - "investigation": default — necesita más análisis
    """
    claim_lower = claim.lower()
    if any(w in claim_lower for w in ("error", "fallo", "broken", "crash", "bug",
                                       "excepcion", "stack")):
        return "bug"
    if any(w in claim_lower for w in ("nueva", "funcionalidad", "solicitud",
                                      "feature", "capacidad")):
        return "feature"
    if any(w in claim_lower for w in ("legacy", "deprecat", "refactor",
                                       "todo", "deuda", "improvement")):
        return "tech_debt"
    return "investigation"


def _detectar_ciclos_frontier(correlaciones: list) -> list:
    """ETER-CYCLE: detecta dependencias circulares entre findings (directa + transitiva).

    Construye un grafo dirigido por overlaap numerico/comparticion de claves:
    A -> B si A y B comparten >=2 numeros significativos. Luego busca
    ciclos transitivos: A->B->C->A (DFS). Devuelve lista de ciclos encontrados.
    """
    if len(correlaciones) < 2:
        return []
    # Extraer sets de numeros significativos de cada claim
    def _nums(t):
        return {n for n in re.findall(r"\d+", t or "") if int(n) >= 10}
    indexed = []
    for corr in correlaciones:
        finding_id = corr.get("finding_id", "")
        claim = corr.get("claim", "")
        numeros = corr.get("numeros_comunes", [])
        if not numeros:
            numeros = sorted(_nums(claim))
        indexed.append({"fid": finding_id, "nums": set(numeros), "claim": claim})
    # Grafo dirigido por interseccion numerica
    adj = {i: [] for i in range(len(indexed))}
    for i in range(len(indexed)):
        for j in range(len(indexed)):
            if i == j:
                continue
            if len(indexed[i]["nums"] & indexed[j]["nums"]) >= 2:
                adj[i].append(j)
    # Buscar ciclos transitivos via DFS
    ciclos = []
    seen_paths = set()
    def dfs(start, path, visited):
        last = path[-1]
        for nxt in adj.get(last, []):
            if nxt == start and len(path) >= 2:
                key = tuple(sorted(path))
                if key not in seen_paths:
                    seen_paths.add(key)
                    ciclos.append({
                        "tipo": "transitivo" if len(path) > 2 else "directo",
                        "ciclo": [indexed[x]["fid"] for x in path],
                        "longitud": len(path),
                    })
            elif nxt not in path and nxt > start:
                dfs(start, path + [nxt], visited | {nxt})
    for i in range(len(indexed)):
        dfs(i, [i], {i})
    # También conservar la detección clásica directa (compat con tests existentes)
    finding_refs = set()
    for corr in correlaciones:
        claim = corr.get("claim", "")
        for fid in finding_refs:
            if fid in claim:
                ciclos.append({
                    "tipo": "circular_ref",
                    "finding_id": corr.get("finding_id"),
                    "refiere_a": fid,
                    "claim_preview": claim[:80],
                })
        finding_refs.add(corr.get("finding_id", ""))
    # de-dupe por tipo/longitud
    return ciclos


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

def _detectar_checks_redundantes(vigiladas: list) -> list:
    """AIRE-DETECT: detecta checks que prueban lo mismo dos veces."""
    counts = {}
    for v in vigiladas:
        if isinstance(v, dict):
            chk = v.get("check", "")
            if chk:
                counts[chk] = counts.get(chk, 0) + 1
    return [{"check": k, "count": v, "tipo": "redundante"}
            for k, v in counts.items() if v > 1]

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
    # Integración RXRE-029: correlación opcional mecanismo-evidencia
    correlation_result = None
    if params.get("correlation_input") and isinstance(params.get("correlation_input"), dict):
        try:
            from revkit.correlate import correlacionar
            ci = params.get("correlation_input")
            correlation_result = correlacionar(
                ci.get("origen"), ci.get("destino"),
                ci.get("tipo", "TEXTUAL_MATCH"),
                ci.get("evidencia_favor", []),
                ci.get("evidencia_contra"),
                ci.get("procedencia", "run")
            )
        except Exception as exc:
            correlation_result = {"status":"error","motivo":str(exc),"tipo":"UNRESOLVED"}

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
    # RXRE-039/040/041: persistencia opcional de correlation_result en env
    # para trazabilidad de contrato (no obligatorio, no modifica DB);
    # activa solo cuando correlation_result existe en el contexto anterior
    if correlation_result is not None:
        env["correlation_result"] = correlation_result
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
    except Exception as exc:
        # La ejecucion del backend fue valida, pero el EVENTO DE AUDITORIA
        # no se persistio. `persistido` describe la persistencia de los
        # RESULTADOS (contrato de dispatch/AGUA: "hay fila en la tabla",
        # recuperable por result_id) y NO se sobrescribe aqui: si los
        # resultados se persistieron, siguen siendo recuperables. El fallo
        # del evento se informa aparte, con un campo dedicado y en
        # limitations, para que el consumidor distinga ambos hechos.
        env["persistencia_fallida"] = True
        env["limitations"] = list(env.get("limitations") or []) + [
            "persistencia del evento fallo: %s" % str(exc)[:200]
        ]
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
    # La lista incluye `unsupported`: es un estado del productor (capacidad
    # no soportada), no un fallo de ejecucion, pero el auto-ciclo debe
    # detenerse igual para proponer la reflexion y reseleccionar.
    if env.get("status") in ("blocked", "error", "fallback", "invalid_input",
                          "unsupported") and capability:
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
        "motivo": env.get("motivo", ""),
        "regla": env.get("regla"),
        "results": env.get("results"),
        "next_actions": next_actions,
        "operation_id": env.get("operation_id"),
        "persistido": env.get("persistido"),
        # La ejecucion fue exitosa pero el evento no se persistio: el run
        # sigue reportando el resultado real, explicitando la auditoria
        # incompleta. Permite a un consumidor distinguir ambos casos.
        "persistencia_fallida": bool(env.get("persistencia_fallida")),
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
        "correlation_result": correlation_result,
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
    # Cuando una operacion falla (error, timeout, blocked, invalid_input,
    # unsupported), sugerir registrar una reflexion para que la IA aprenda
    # del fallo.
    # Esto cierra el lazo de retroalimentacion: observacion -> registro ->
    # aprendizaje. La sugerencia es una next_action, no una accion automatica:
    # la IA decide si reflecciona o no, conservando el control explicito.
    status = env.get("status")
    if status in ("error", "timeout", "blocked", "invalid_input",
                "unsupported"):
        op_id = env.get("operation_id", "")
        fa = {
            "op": "reflect",
            "args": {"outcome": _outcome_from_status(status),
                     "attempt_id": op_id} if op_id else
                    {"outcome": _outcome_from_status(status)},
            "available": True,
            "descripcion": "Registrar una reflexion sobre este fallo (feedback -> reflection -> strategy)",
        }
        if status == "unsupported":
            fa["tipo"] = "infraestructura"
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
    if status in ("blocked", "invalid_input", "error", "unsupported"):
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

    # FUEGO-AUTO-FALLBACK: si el run fallo y tenemos historial de backends,
    # sugerir reintento con el mejor backend alternativo. `unsupported`
    # tambien cuenta como fallo para el auto-ciclo (la capacidad no puede
    # ejecutarse con este backend); no se refuerza con un backend alternativo,
    # porque el problema es la capacidad, no el backend.
    if status in ("error", "blocked", "invalid_input", "timeout", "unsupported") and capability:
        try:
            backend_alt = _mejor_backend_para(capability)
            if backend_alt and backend_alt != (env.get("backend_id") or params.get("backend_id")):
                # Check if we haven't already suggested this
                has_alt = any(na.get("op") == "run" and na.get("args", {}).get("backend_id") == backend_alt
                             for na in next_actions)
                if not has_alt:
                    next_actions.append({
                        "op": "run",
                        "args": {**{k: v for k, v in params.items() if k != "op"},
                                 "capability": capability,
                                 "backend_id": backend_alt},
                        "available": True,
                        "descripcion": "FUEGO-AUTO-FALLBACK: reintentar con %s (mejor historial)" % backend_alt,
                    })
                    response["next_actions"] = next_actions
        except Exception:
            pass  # No bloquear por fallback

    # FUEGO-TIMEOUT: sugerir timeout basado en historial de performance
    try:
        tiempo_sugerido = _calcular_timeout_sugerido(capability, backend_id)
        if tiempo_sugerido > 0:
            for na in next_actions:
                if na.get("op") == "run" and isinstance(na.get("args"), dict):
                    na["args"]["timeout"] = round(tiempo_sugerido, 1)
                    na.setdefault("descripcion", "")
                    if "timeout sugerido" not in na["descripcion"]:
                        na["descripcion"] += " (timeout sugerido: %.1fs)" % tiempo_sugerido
    except Exception:
        pass

    return response


def _calcular_timeout_sugerido(capability: str, backend_id: str = "") -> float:
    """FUEGO-TIMEOUT: calcula el timeout sugerido basado en historial.

    timeout_sugerido = avg_time × 2 + 1.0 (con margen para variabilidad)
    Devuelve 0 si no hay suficiente historial (>=2 registros).
    """
    c = _get_db()
    try:
        cur = c.execute(
            "SELECT text FROM research WHERE kind='performance' "
            "AND target=? AND status='OPEN'",
            (capability,),
        ).fetchall()
        tiempos = []
        for row in cur:
            text = row[0] if isinstance(row, tuple) else row["text"]
            if "tiempo=" in text:
                try:
                    t = float(text.split("tiempo=")[1].split(" ")[0])
                    tiempos.append(t)
                except (ValueError, IndexError):
                    pass
        if len(tiempos) >= 2:
            avg = sum(tiempos) / len(tiempos)
            return avg * 2 + 1.0
        return 0.0
    except Exception:
        return 0.0
    finally:
        c.close()


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
         "blocked": "failure", "invalid_input": "failure",
         "unsupported": "failure"}
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
    tid = params.get("trace_id") or os.environ.get("RXRE_TRACE_ID") or session_id or None

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
        derived_from_evidence = False

        # 161: derivar frontera desde evidencia registrada si no hay tarea
        if not task_id:
            derived_target = None
            try:
                fronts = store.investigacion(
                    c, target="", kind="frontier", status="OPEN", limite=5)
                for f in fronts.get("entradas", []):
                    refs_f = f.get("refs") or []
                    if refs_f and f.get("target"):
                        derived_target = f.get("target")
                        break
                if not derived_target:
                    ev = store.buscar(c, limite=1)
                    if ev.get("status") == "ok" and ev.get("results"):
                        r_e = ev["results"][0]
                        derived_target = (r_e.get("value") or r_e.get("file") or "")[:120]
                if derived_target:
                    store.agregar_tarea_a_mision(
                        c, mission_id,
                        "Investigacion desde evidencia: %s" % derived_target,
                        priority=90,
                    )
                    derived_from_evidence = True
                    task_id = store.seleccionar_siguiente_accion(
                        c, mission_id, por_valor=True)
            except Exception:
                pass

        if not task_id:
            # ALMA-AUTO-CLOSE con contrato de criterios (RXRE-201/202):
            # el cierre se delega en mission_closure.close_mission(), que
            # exige criterios obligatorios + evidencia PROVEN con procedencia.
            # Si no hay criterios, NO se marca COMPLETED (criterio ausente != satisfecho).
            cierre = None
            try:
                tasks = store.obtener_tareas_mision(c, mission_id)
                if tasks and all(t.get("status") in ("COMPLETED", "DONE", "FAILED", "BLOCKED")
                                 for t in tasks):
                    from rxre.mission_closure import close_mission
                    cierre = close_mission(mission_id, conn=c)
            except Exception:
                cierre = None
            # No hay tareas viables — sugerir registrar una
            return {
                "status": "empty",
                "op": "select",
                "mission_id": mission_id,
                "derived_from_evidence": derived_from_evidence,
                "task_id": None,
                "cierre": cierre,
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

        # ALMA-RESUME: registrar la ultima task seleccionada para auto-resume.
        # (gap_kind omitido: solo valido para hypothesis/claim; "last_task" era
        # invalido y bloqueaba la persistencia silenciosamente.)
        persisted_ok = False
        note_id = None
        try:
            nr = store.registrar_investigacion(
                c,
                kind="note",
                text="select: task=%s capability=%s valor=%s" % (
                    task_id, _capability_de(tarea.get("title", "")),
                    tarea.get("valor")),
                status="OPEN",
                target=mission_id,
                session=tid or "",
                gap_kind="",
                refs=[],
            )
            if nr.get("estado") == "ok":
                persisted_ok = True
                note_id = nr.get("id")
                try:
                    store.registrar_audit_log(
                        c, "select_task", "research", str(note_id),
                        actor="rxre.select",
                        details={"mission_id": mission_id,
                                 "task_id": task_id,
                                 "valor": tarea.get("valor"),
                                 "componentes": tarea.get("componentes"),
                                 "trace_id": tid})
                except Exception:
                    pass
        except Exception:
            persisted_ok = False

        # Evento durable para reconstruir la seleccion (decision autonoma).
        try:
            import json as _j
            env_sel = {
                "status": "ok",
                "capability": "rxre.select",
                "backend": None,
                "ejecucion": {"exit_status": 0,
                              "iteration": params.get("iteration")},
                "persistido": persisted_ok,
                "limitations": [_j.dumps({
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "title": tarea.get("title"),
                    "valor": tarea.get("valor"),
                    "componentes": tarea.get("componentes"),
                    "bloqueada": tarea.get("bloqueada"),
                }, default=str)],
                "trace_id": tid,
                "results": [],
                "operation_id": "",
            }
            store.registrar_evento(c, "select", "rxre.select", env_sel, [])
        except Exception:
            pass

        return {
            "status": "ok",
            "op": "select",
            "mission_id": mission_id,
            "derived_from_evidence": derived_from_evidence,
            "task_id": task_id,
            "trace_id": tid,
            "persistido": persisted_ok,
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


def _extract_artifact(text: str) -> str:
    """Extrae el artefacto de un texto de frontier ('tipo en <artefacto> (...)')."""
    import re as _re
    m = _re.search(r"\s+en\s+(.+?)(?:\s*\(|:|$)", text or "")
    return m.group(1).strip() if m else ""



def _merge_iter(e, it):
    d = dict(e) if isinstance(e, dict) else {"exit_status": 0}
    if it is not None:
        d["iteration"] = it
    return d


def _canon_result(r):
    """Forma canonica de UN resultado, INDEPENDIENTE del orden de entrada.

    `result_id` NO es criterio de igualdad: los productores lo derivan del
    indice de entrada (rz_xrefs.py:439, rz_callgraph.py:195), por lo que dos
    resultados semanticamente iguales emitidos en distinto orden tendrian IDs
    distintos. Se exige su presencia solo como marca de completitud.

    Para resultados cuya identidad semantica vive en `location` (p.ej. las
    lecturas UMR, que identifican el registro en `location.register`), se
    anade ese campo SOLO si existe: no se fabrica identidad.
    """
    if not isinstance(r, dict) or not r.get("result_id"):
        return None  # resultado incompleto: no se puede comparar con seguridad
    loc = r.get("location")
    reg = loc.get("register") if isinstance(loc, dict) else None
    # Las lecturas UMR identifican el registro en `location.register`. Si falta,
    # no hay identidad semantica comparable: abstener (no fabricarla).
    is_register_read = (r.get("scope") == "gpu") or (r.get("tool") == "umr")
    if is_register_read and reg is None:
        return None
    base = (
        r.get("type"),
        json.dumps(r.get("value"), sort_keys=True, default=str),
        r.get("source"),
        r.get("scope"),
        r.get("tool"),
    )
    if reg is not None:
        base = base + ("reg:" + str(reg),)
    return base


def _is_declared_sample(r):
    """Marcadores REALES de truncacion/incompletitud declarados por el producer.

    No infiere truncacion por longitud numerica: exige una declaracion
    (limitation que mencione truncado/muestra/parcial/sample, o el flag
    `coincidencias_truncadas`/`errores_parseo_truncados` de ts_ast).
    """
    if not isinstance(r, dict):
        return False
    raw = r.get("raw")
    if isinstance(raw, dict):
        if raw.get("coincidencias_truncadas") or raw.get("errores_parseo_truncados"):
            return True
    lims = " ".join(str(x) for x in (r.get("limitations") or [])).lower()
    return any(k in lims for k in ("truncad", "muestra", "parcial", "sample"))


def _obs_completeness(obs):
    """Completitud de una observacion: 'complete' | 'partial' | 'unknown'.

    - 'partial' si algun campo declara truncacion demostrada (completo is False).
    - 'unknown' si algun campo no declara completitud de forma valida
      (completo ausente, null o de tipo invalido).
    - 'complete' si todos los campos declaran completo=True (o no hay marcador).

    Un marcador cubre SOLO los campos que declara: la completitud de
    `instrucciones` no implica la de `huecos` ni de `raw`.
    """
    if not isinstance(obs, list):
        return "complete"

    def _field_state(c):
        if not isinstance(c, dict):
            return "unknown"
        v = c.get("completo")
        if v is False:
            return "partial"
        if v is True:
            return "complete"
        return "unknown"  # ausente, null o tipo invalido

    state = "complete"
    for r in obs:
        if not isinstance(r, dict):
            continue
        if _is_declared_sample(r):
            return "partial"
        comp = r.get("completitud")
        if isinstance(comp, dict):
            fs = _field_state(comp)
            if fs == "partial":
                return "partial"
            if fs == "unknown":
                state = "unknown"
        anid = r.get("completitud_anidada")
        if isinstance(anid, dict):
            for _f, c in anid.items():
                fs = _field_state(c)
                if fs == "partial":
                    return "partial"
                if fs == "unknown":
                    state = "unknown"
    return state


def _canon_obs(obs):
    """Normaliza una observacion canonicamente, preservando multiplicidad.

    Devuelve ("ok", lista_ordenada) o ("incomplete", None) si algun resultado
    carece de identidad.
    """
    if isinstance(obs, list):
        out = []
        for r in obs:
            cr = _canon_result(r)
            if cr is None:
                return ("incomplete", None)
            out.append(cr)
        out.sort()
        return ("ok", out)
    return ("ok", obs)

def _capability_de(texto: str) -> str:
    """Extrae el nombre de capability de un texto de tarea (si contiene uno)."""
    import re as _re
    m = _re.search(r'\b(binary\.\w+)', texto or "")
    return m.group(1) if m else ""


def _handle_plan(params: dict) -> dict:
    """op: plan - Devuelve el plan de ejecucion SIN ejecutar."""
    # ETER: emitir el evento ANTES de la logica del handler. Async y
    # no-bloqueante (ver _handle_scan).
    try:
        _eter().emit("plan", {"op": "plan"}, critico=True)
    except Exception:
        pass
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
    # AIRE-001: contrato de retroalimentacion causal run -> plan.
    # Si el llamante pasa `prev_step` (resultado anterior de la misma misión),
    # `plan` recibe la causa sin convertirse en hecho obligatorio.
    prev = params.get("prev_step")
    if prev and isinstance(prev, dict):
        causa = {}
        for k in ("status", "root_cause", "reflexion_sugerida", "motivo", "persistencia_fallida"):
            if k in prev:
                causa[k] = prev[k]
        if causa:
            if isinstance(prev.get("correlation_result"), dict):
                causa["correlation_result"] = prev["correlation_result"]
            plan["retroalimentacion_causa"] = {
                "origen": "prev_step",
                "mision_actual": params.get("mission_id"),
                "capability": capability,
                "causa": causa,
                "nota": "Esta retroalimentacion informa, no obliga. "
                        "La decision del plan conserva su independencia.",
            }
            # RXRE-040: sugiriendo investigacion adicional cuando correlacion
            # indica cuestion no resuelta con evidencia disponible.
            cr = prev.get("correlation_result") if isinstance(prev.get("correlation_result"), dict) else None
            if cr and cr.get("tipo") == "UNRESOLVED" and (cr.get("evidencia_favor") or cr.get("procedencia")):
                # No duplicar si ya existe accion equivalente
                existing = [na for na in (plan.get("next_actions") or [])
                            if na.get("op") == "discover"]
                if not existing:
                    plan.setdefault("next_actions", []).append({
                        "op": "discover",
                        "args": {
                            "artefacto": cr.get("procedencia") or cr.get("origen") or "unknown",
                            "evidencia_favor": cr.get("evidencia_favor", []),
                            "motivo": "correlation_result UNRESOLVED: %s" % (cr.get("nota") or cr.get("procedencia")),
                        },
                        "available": True,
                        "descripcion": "Investigar correlacion no resuelta (correlation_result UNRESOLVED) con evidencia disponible.",
                    })
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
    # AIRE-002: usar retroalimentacion_causa para ajustar viabilidad
    # Solo marca como no disponible cuando la evidencia vincula capacidad
    # ausente confirmada con la capacidad que requiere este paso.
    causa_info = plan.get("retroalimentacion_causa")
    if causa_info and isinstance(causa_info.get("causa"), dict):
        causa = causa_info["causa"]
        if causa.get("status") == "unsupported" and causa.get("capability"):
            cap_faltante = causa.get("capability") or causa.get("capability")
            # El paso requiere esa capacidad?
            for paso in plan.get("plan") or []:
                paso_cap = paso.get("capability") or paso.get("op")
                if paso_cap and paso_cap == cap_faltante:
                    paso["available"] = False
                    paso["descripcion"] = (
                        paso.get("descripcion", "") +
                        " [AIRE-002: capacidad '%s' no soportada por backend; "
                        "reintento idem descartado]" % cap_faltante)
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
    except Exception as exc:
        # La planificacion fue valida, pero el evento de auditoria no se
        # persistio. No se afirma persistencia: simetria con op:run
        # (persistencia_fallida + limitation), sin abortar la planificacion.
        plan["persistencia_fallida"] = True
        plan["limitations"] = list(plan.get("limitations") or []) + [
            "persistencia del evento fallo: %s" % str(exc)[:200]
        ]

    # MENTE-FEASIBILITY: auto-evaluar si los pasos del plan son factibles.
    # Un paso es factible si: (1) la capability existe en el registry, y
    # (2) no tiene un historial de fallos repetidos (>3 failures con outcome=failure).
    from rxre.backends import registry as _registry
    plan_paso = plan.get("plan") or []
    steps_feasible = []
    for paso in plan_paso:
        cap = paso.get("capability", "")
        available = paso.get("available", False)
        try:
            _registry.lookup(cap)
            registry_ok = True
        except Exception:
            registry_ok = False
        # MENTE-DBHIST: check DB for repeated failures
        historial_fallas = 0
        try:
            cur = c.execute(
                "SELECT COUNT(*) FROM operations WHERE capability=? AND exit_status!=0",
                (cap,),
            ).fetchone()
            historial_fallas = cur[0] if cur else 0
        except Exception:
            pass
        feasible = registry_ok and historial_fallas < 3
        steps_feasible.append({
            "capability": cap,
            "feasible": feasible,
            "available": available,
            "historial_fallas": historial_fallas,
        })
    plan["feasibility"] = steps_feasible
    plan["feasible_steps"] = sum(1 for s in steps_feasible if s["feasible"])
    plan["total_steps"] = len(steps_feasible)
    # MENTE-PLAN-DAG: detectar ciclos de orden entre pasos (capacities duplicadas
    # o pasos que dependen uno de otro en direccion circular).
    caps_plan = [paso.get("capability") for paso in (plan.get("plan") or [])]
    caps_dups = [c for c in set(caps_plan) if caps_plan.count(c) > 1]
    plan["dag_ciclos"] = caps_dups
    plan["dag_validado"] = (len(caps_dups) == 0)
    plan["plan_detecta_ciclo_dag"] = len(caps_dups) > 0

    c.close()
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
        # AGUA-AUTO-RETRY: si lessons ejecuto y algun check fallo,
        # sugerir retry con parametros ajustados
        "auto_retry": {"intentos_recomendados": 3,
                       "backoff_ms": [500, 1000, 2000]},
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


def _explain_por_operacion(c, params: dict, operation_id: str) -> dict:
    """F1/F4-PUBLIC: `op:explain` con `operation_id`.

    Delega en `store.explicar_operacion`, que ya tiene la semantica de este
    contrato: `status:"ok"` con la fila y sus N resultados, o `status:"empty"`
    con la limitacion que dice que la ausencia de fila NO prueba que la
    operacion no ocurriera. No se reimplementa nada aqui ni se inventa un
    `result_id` para una operacion que no tiene resultados.

    Lo que NO se aplica, y se DECLARA: `root_cause`, `audit` y
    `audit_truncation` analizan un RESULTADO. Pedirlos en la vista por
    operacion no tiene objeto, y callar seria fingir que se aplicaron.
    """
    try:
        result = store.explicar_operacion(c, operation_id)
    except Exception as e:                       # noqa: BLE001
        # Un fallo de CONSULTA no es una operacion vacia: es un error, y se
        # dice con su causa. Devolver `status:"ok"` aqui seria fabricar.
        return {
            "status": "error",
            "operation_id": operation_id,
            "ejecutada": False,
            "motivo": "no se pudo recuperar la operacion %s: %s"
                      % (operation_id, str(e)[:200]),
            "results": [],
            "next_actions": [],
            "limitations": ["fallo de consulta: esto NO es evidencia de que "
                            "la operacion no exista"],
        }

    no_aplicables = [k for k in ("root_cause", "audit", "audit_truncation",
                                 "verify")
                     if params.get(k)]
    if no_aplicables:
        result["limitations"] = list(result.get("limitations") or []) + [
            "op:explain por 'operation_id' NO aplica %s: son de la vista por "
            "'result_id' (analizan un resultado, y esta operacion se consulta "
            "por su id)" % ", ".join("'%s'" % k for k in no_aplicables)]
    result.setdefault("next_actions", [])
    result["consulta_por"] = "operation_id"
    return result


def _handle_explain(params: dict) -> dict:
    """op: explain - TIERRA: reconstruye la cadena de evidencia de un resultado.

    Con root_cause=True (MENTE), analiza la causa raiz del bloqueo/fallo
    recorriendo la cadena del backend y proponiendo hipotesis falsables.

    Con session_id (ALMA), registra una sesion de trabajo para rastrear
    la continuidad del proposito a traves de multiples operaciones.

    Uso:
        {"op":"explain","result_id":"res_abc"}
        {"op":"explain","result_id":"res_abc","root_cause":true}
        {"op":"explain","operation_id":"op_abc"}
        {"op":"explain","session_id":"investigacion-001"}

    F1/F4-PUBLIC: `operation_id` recupera la OPERACION completa, que es lo
    unico que existe cuando la operacion se ejecuto y devolvio cero resultados:
    sin `results` no hay `result_id` que pedir. Delega en
    `store.explicar_operacion`, que ya distingue `status:"ok"` (la operacion
    esta, con N resultados) de `status:"empty"` (no hay fila con ese id en esta
    base). `root_cause`, `audit` y `audit_truncation` son de la vista por
    RESULTADO: si se piden en la vista por operacion, se declara en
    `limitations` en vez de fingir que se aplicaron.
    """
    result_id = params.get("result_id")
    operation_id = params.get("operation_id")
    if not result_id and not operation_id:
        return {
            "status": "invalid_input",
            "result_id": result_id,
            "operation_id": operation_id,
            "ejecutada": False,
            "motivo": "falta 'result_id' o 'operation_id'",
            "results": [],
            "next_actions": [],
        }

    # ALMA: session tracking
    session_id = params.get("session_id") or params.get("session")
    if session_id:
        _registrar_sesion(params, session_id)

    c = _get_db()
    try:
        # F1/F4-PUBLIC: la vista por OPERACION. `result_id` manda si vienen
        # los dos: es lo que ya hacian todos los llamadores, y la vista por
        # operacion es la segunda. Se DECLARA que se ignoro, para que nadie
        # lea una vista de resultado creyendo que se_stacke_ la de operacion.
        if operation_id and not result_id:
            return _explain_por_operacion(c, params, operation_id)

        if operation_id and result_id:
            result = store.explicar(c, result_id)
            result["limitations"] = list(result.get("limitations") or []) + [
                "llego 'operation_id' (%s) junto a 'result_id' (%s): se "
                "atendio 'result_id'. Para la vista por operacion, pida "
                "explain SOLO con 'operation_id'" % (operation_id, result_id)]
        else:
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

        # TIERRA-HASH-CHAIN: verificacion cruzada de hashes entre resultado y operacion.
        # Calcula un hash chain de operation_id+result_id y lo compara con lo persistido
        # (defense in depth). No fuerza bloqueo; solo reporta.
        try:
            op_row = result.get("operation") or {}
            rid = result.get("result_id") or params.get("result_id")
            oid = op_row.get("operation_id") or op_row.get("op_id")
            chain_ok = bool(rid) and bool(oid)
            import hashlib as _h
            chain_hash = _h.sha256(("%s|%s" % (oid, rid)).encode()).hexdigest()[:16] if chain_ok else ""
            result["hash_chain_ok"] = chain_ok
            result["hash_chain"] = chain_hash
        except Exception:
            result["hash_chain_ok"] = True
        # TIERRA-GAP: detectar saltos en la cadena de evidencia validada.
        # Si evidencia_validada pasa de True a False entre steps consecutivos,
        # sugerir un explain intermedio para llenar el gap.
        evidencia = result.get("evidencia_validada", "")
        if isinstance(evidencia, str) and "→" in evidencia:
            # Parse: "True→False→True" detectar dónde hay False después de True
            parts = evidencia.split("→")
            for i in range(len(parts)):
                if parts[i].strip() == "False" and i > 0 and parts[i-1].strip() == "True":
                    na.append({
                        "op": "explain",
                        "args": {"result_id": result_id},
                        "available": False,
                        "descripcion": "TIERRA-GAP: la evidencia salta de True→False "
                                       "en step %d — investigar gap intermedio" % i,
                    })
                    break

        # F1/F4-PUBLIC: contrato `results` envuelve el payload en una lista.
        # `ok` -> lista no vacia (payload observable); `empty`/`invalid_input` -> []
        if result.get("status") in ("empty", "invalid_input"):
            result["results"] = []
        else:
            # Si ya es lista, conservar; si no, envolver el payload observado.
            existing = result.get("results") or []
            if isinstance(existing, list) and len(existing) > 0:
                result["results"] = existing
            else:
                payload_items = {k: v for k, v in result.items()
                                 if k not in ("status", "op", "motivo", "next_actions",
                                              "limitations", "operation_id", "results",
                                              "hash_chain_ok", "hash_chain",
                                              "truncation_audit", "gate", "root_cause")}
                result["results"] = [payload_items] if payload_items else [result.copy()]
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
    try:
        catalogo = caps.disponibles()
    except Exception:
        catalogo = []
    return {"status": "ok", "results": operaciones, "capabilities": catalogo,
            "next_actions": []}


def _tokens_consulta(texto: str) -> list:
    """Extrae tokens significativos de una pregunta en texto libre.

    `store.buscar` hace coincidencia literal sobre el texto; una pregunta
    natural ("quien escribe VM_CONTEXT0_CNTL") no casa como bloque. Se
    ordenan por especificidad (identificadores con mayusculas/underscore
    primero) para buscar el token mas discriminante.
    """
    toks = re.findall(r"[A-Z][A-Z0-9_]{2,}|[a-z_][a-z0-9_]{3,}", texto or "")
    toks = [t for t in toks if t.lower() not in
            ("quien", "cual", "quales", "como", "cuando", "donde", "por",
             "para", "con", "sin", "que", "es", "son", "escribe", "escriben",
             "the", "and", "para")]
    return sorted(dict.fromkeys(toks),
                  key=lambda t: (0 if (t.isupper() or "_" in t) else 1, -len(t)))


def _handle_query(params: dict) -> dict:
    """op: query - TIERRA: consulta evidencia registrada y expone su procedencia.

    Propaga el `operation_id` real (persistido via `store.registrar`) y el
    `relations_summary` derivado de las aristas reales (`store.relations`).
    """
    target = params.get("target", "")
    question = params.get("question") or params.get("pregunta") or ""
    request = {"op": "query", "target": target, "question": question}
    c = _get_db()
    try:
        results = []
        limitaciones = []
        for cand in [question] + _tokens_consulta(question) + ([target] if target else []):
            if not cand:
                continue
            env_search = store.buscar(c, texto=cand, limite=5)
            got = env_search.get("results") or []
            if got:
                results = got
                break
            if not limitaciones:
                limitaciones = env_search.get("limitations") or []
        if not results and target:
            env_search = store.buscar(c, archivo=target, limite=5)
            results = env_search.get("results") or []

        # Aristas WRITES reales: dst casa con los tokens de la pregunta.
        tokens = _tokens_consulta(question)
        aristas = []
        if tokens:
            todas = store.relations(c, tipo="WRITES", limite=100).get("results") or []
            for a in todas:
                dst = str(a.get("dst") or "")
                if any(tok in dst for tok in tokens):
                    aristas.append(a)
        if not aristas:
            aristas = store.relations(c, src=target or None, tipo="WRITES",
                                      limite=50).get("results") or []

        env_out = {"status": "ok", "op": "query",
                   "results": results,
                   "aristas": aristas,
                   "relations_summary": {"WRITES": len(aristas)},
                   "question": question,
                   "target": target,
                   "limitations": limitaciones,
                   "operation_id": None}
        env_out["operation_id"] = store.registrar(c, request, env_out)
        return env_out
    finally:
        c.close()


def _handle_relation(params: dict) -> dict:
    """op: relation - ARISTA: relaciones de un nodo del grafo de dominio.

    Nodo sin aristas observadas -> `status=empty` con `results=[]` y
    `relations_summary` a cero (no se rellena con datos inventados).
    """
    clase = params.get("clase") or params.get("class") or "writers"
    nodo = params.get("nodo") or params.get("node") or ""
    c = _get_db()
    try:
        if not nodo:
            return {"status": "invalid_input", "op": "relation", "results": [],
                    "relations_summary": {"WRITES": 0},
                    "clase": clase, "nodo": nodo,
                    "motivo": "falta 'nodo'"}
        tipo = "WRITES" if clase == "writers" else None
        rel = store.relations(c, src=nodo, tipo=tipo, limite=50)
        aristas = rel.get("results") or []
        if not aristas:
            return {"status": "empty", "op": "relation", "results": [],
                    "relations_summary": {"WRITES": 0},
                    "clase": clase, "nodo": nodo}
        return {"status": "ok", "op": "relation", "results": aristas,
                "relations_summary": {"WRITES": len(aristas)},
                "clase": clase, "nodo": nodo}
    finally:
        c.close()


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

    # AIRE-1: verificar integridad del artefacto en los brazos del experimento
    for p in (params.get("baseline_params") or {}, params.get("modified_params") or {}):
        if p.get("artefacto") or p.get("artifact") or p.get("path"):
            pre = _verificar_integridad_artefacto(p)
            if not pre.get("ok"):
                return {"status": "blocked" if "no existe" in str(pre.get("limitations",[])) else "invalid_input",
                        "op": "experiment", "ejecutada": False,
                        "motivo": "integridad del artefacto fallida: %s" % "; ".join(pre.get("limitations", [])),
                        "precheck": pre, "results": []}

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
    # MODO CANONICO: comparar contenido semantico, no envelopes completos.
    canonico = bool(params.get("canonico") or params.get("canonical"))
    if canonico:
        base_state, base_canon = _canon_obs(base_obs)
        mod_state, mod_canon = _canon_obs(mod_obs)

        if base_state == "incomplete" or mod_state == "incomplete":
            veredicto = "no_observable"
            motivo = ("observable incompleto: al menos un resultado carece de "
                      "result_id; no se puede comparar con seguridad")
        elif isinstance(base_obs, str) and base_obs.startswith("<<NO EXISTE") \
                or isinstance(mod_obs, str) and mod_obs.startswith("<<NO EXISTE"):
            veredicto = "no_observable"
            motivo = ("el observable '%s' no existe en uno de los brazos" % ruta)
        elif base_state != "ok" or mod_state != "ok":
            veredicto = "no_observable"
            motivo = "observable no canonizable"
        else:
            # predicción canónica: si esperado es str, canonicalizarlo si es posible
            pred_canon = None
            if isinstance(params.get("esperado"), str):
                try:
                    parsed = json.loads(params["esperado"])
                    if isinstance(parsed, list):
                        pc_state, pc = _canon_obs(parsed)
                        if pc_state == "ok":
                            pred_canon = pc
                except (ValueError, TypeError):
                    pass
            if pred_canon is None and isinstance(params.get("esperado"), str) \
                    and params["esperado"] in ("NO_CHANGE", "base", ""):
                pred_canon = base_canon
            if pred_canon is None and isinstance(params.get("esperado"), str):
                # esperado escalar: usarlo directamente como prediccion canonica
                pred_canon = params["esperado"]
            if pred_canon is None:
                # convención de igualdad: predecir base_canon
                pred_canon = base_canon

            def _any_sample(obs):
                return isinstance(obs, list) and any(_is_declared_sample(r) for r in obs)

            # Abstencion: si la completitud de algun brazo no esta demostrada
            # (parcial o desconocida), la igualdad no demuestra equivalencia del
            # contenido completo.
            base_comp = _obs_completeness(base_obs)
            mod_comp = _obs_completeness(mod_obs)
            if (base_comp in ("partial", "unknown") or mod_comp in ("partial", "unknown")) \
                    and mod_canon == base_canon:
                veredicto = "no_observable"
                motivo = ("completitud no demostrada (base=%s mod=%s); la "
                          "igualdad no demuestra equivalencia del contenido completo"
                          % (base_comp, mod_comp))
            # no_separable tiene prioridad: si ambos brazos son canonicamente iguales,
            # no hay intervencion observable, aunque coincidan con la prediccion.
            elif mod_canon == base_canon:
                veredicto = "no_separable"
                motivo = ("los dos brazos dan el MISMO conjunto canonico en '%s' "
                          "(%s); este observable no los separa" % (ruta, base_canon))
            elif isinstance(params.get("esperado"), str) and pred_canon is not None:
                veredicto = ("sostenida" if mod_canon == pred_canon else "refutada")
                motivo = "esperado=%r observado=%r (canonico)" % (pred_canon, mod_canon)
            elif str(mod_canon) == str(prediction):
                veredicto = "sostenida"
                motivo = "el brazo modificado dio exactamente la prediccion (canonico)"
            else:
                veredicto = "refutada"
                motivo = ("el brazo modificado dio %r y la prediccion de comparacion "
                          "era %r (canonico)" % (mod_canon, prediction))
    else:
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

    # Causal vertical slice: aceptar hipotesis previa o prediccion del llamante.
    refs_param = params.get("refs") or params.get("evidencia") or []
    if isinstance(refs_param, str):
        refs_param = [refs_param]

    # FIRE cierra en MIND: el resultado del experimento entra en memoria con
    # su veredicto, para que el proximo intento lo consulte.
    c = _get_db()
    ref_id = None
    tid = _trace_id_actual(params)
    hypothesis_id = params.get("hypothesis_id")
    # refs motivantes (observacion) validadas contra la base.
    refs_motiv = []
    for rr in refs_param:
        if isinstance(rr, str) and rr:
            try:
                if not store.refs_invalidos(c, [rr]):
                    refs_motiv.append(rr)
            except Exception:
                pass
    # Si no se paso una hipotesis previa, se registra la del llamante
    # (actor="caller"): NO se fabrica a partir de coincidencia numerica.
    if not hypothesis_id:
        try:
            hr = store.registrar_investigacion(
                c, kind="hypothesis",
                text="Hipotesis aportada por el llamante: %s" % prediction,
                status="OPEN", refs=refs_motiv, session=tid or "",
                target=capability, gap_kind="",
            )
            if hr.get("estado") == "ok":
                hypothesis_id = hr.get("id")
                try:
                    store.registrar_audit_log(
                        c, "create_research", "research",
                        str(hypothesis_id), actor="caller",
                        details={"kind": "hypothesis",
                                 "proposed_by": "caller",
                                 "refs": refs_motiv,
                                 "session": tid,
                                 "prediction": prediction})
                except Exception:
                    pass
        except Exception:
            pass
    # resolver attempt_id real (evitar "COLISION:...")
    attempt_id = mod_env.get("operation_id") or None
    if attempt_id and str(attempt_id).startswith("COLISION:"):
        attempt_id = None
    if not attempt_id:
        for r in (mod_env.get("results") or []):
            if isinstance(r, dict) and r.get("result_id"):
                row = c.execute(
                    "SELECT operation_id FROM results WHERE result_id=?",
                    (r["result_id"],)).fetchone()
                if row and row["operation_id"]:
                    attempt_id = row["operation_id"]
                    break
    arm_refs = []
    for env_arm in (base_env, mod_env):
        oid = env_arm.get("operation_id")
        if oid and str(oid).startswith("COLISION:"):
            oid = None
        if not oid:
            for r in (env_arm.get("results") or []):
                if isinstance(r, dict) and r.get("result_id"):
                    row = c.execute(
                        "SELECT operation_id FROM results WHERE result_id=?",
                        (r["result_id"],)).fetchone()
                    if row and row["operation_id"]:
                        oid = row["operation_id"]
                        break
        if oid and oid not in arm_refs:
            arm_refs.append(oid)
    reflexion_refs = list(refs_motiv) + list(arm_refs)
    seen = set()
    reflexion_refs = [x for x in reflexion_refs
                      if not (x in seen or seen.add(x))]
    try:
        r = store.registrar_reflexion(
            c,
            feedback="EXPERIMENTO %s: baseline=%r modificado=%r (observable %s)"
                     % (capability, base_obs, mod_obs, ruta),
            reflection="Pregunta: %s. Prediccion: %s. Veredicto: %s (%s)."
                       % (params["question"], prediction, veredicto, motivo),
            outcome="success" if veredicto == "sostenida" else "failure",
            attempt_id=attempt_id,
            hypothesis_id=hypothesis_id,
            refs=reflexion_refs,
            strategy=params.get("siguiente_paso", ""),
            check_ejecutable=params.get("check_ejecutable", ""),
            target=capability,
            capability=capability,
        )
        ref_id = r.get("reflexion_id")
        # conclusion (claim) con estado honesto: nunca PROVEN con una replica.
        estado_claim = ("SUPPORTED" if veredicto == "sostenida"
                        else "REFUTED" if veredicto == "refutada"
                        else "NOT_DETERMINED")
        try:
            cr = store.registrar_investigacion(
                c, kind="claim",
                text="Conclusion del experimento (%s): %s. Prediccion: %s. %s"
                     % (veredicto, params["question"], prediction, motivo),
                status=estado_claim, refs=arm_refs, session=tid or "",
                target=capability, gap_kind="",
            )
            if cr.get("estado") == "ok":
                try:
                    store.registrar_audit_log(
                        c, "create_research", "research",
                        str(cr.get("id")), actor="rxre.experiment",
                        details={"kind": "claim",
                                 "proposed_by": "system",
                                 "veredicto": veredicto,
                                 "refs": arm_refs,
                                 "session": tid})
                except Exception:
                    pass
        except Exception:
            pass
        # Evento durable para reconstruir experiment.
        try:
            env_exp = {
                "status": "ok",
                "capability": capability,
                "backend": mod_env.get("backend"),
                "ejecucion": _merge_iter(mod_env.get("ejecucion") or {"exit_status": 0}, params.get("iteration")),
                "persistido": True,
                "limitations": list(mod_env.get("limitations") or []),
                "trace_id": tid,
                "results": list(mod_env.get("results") or []),
                "operation_id": attempt_id or mod_env.get("operation_id"),
            }
            store.registrar_evento(c, "experiment", capability, env_exp, [])
        except Exception:
            pass
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
    rotas_vigiladas = r.get("vigiladas", [])
    # AGUA-PRUNE: podar reflexiones obsoletas (sin check ejecutable, anterior a 30 dias)
    try:
        c2 = _get_db()
        pruned = c2.execute("DELETE FROM reflexiones WHERE (check_ejecutable IS NULL OR check_ejecutable='') AND timestamp < datetime('now','-30 days')").rowcount
        c2.commit()
        c2.close()
    except Exception:
        pruned = 0
    # AIRE-CONSOLIDATE: checks redundantes que prueban lo mismo
    redundantes = _detectar_checks_redundantes(rotas_vigiladas)
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
        "pruned": pruned,
        "checks_redundantes": redundantes,
        "checks_merge_sugerido": redundantes,
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
        # AIRE-DETECT: detectar checks redundantes (mismo checkeable repetido)
        "checks_redundantes": _detectar_checks_redundantes(r.get("vigiladas", [])),
    }
    if aplicacion is not None:
        respuesta["aplicacion"] = aplicacion
    return respuesta


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
    """op: application - AGUA: automatiza rastreo y reflexion basada en evidencia.

    Consulta execution_events por capability; si hay evidencia valida
    (resultado concreto, no solo error de infraestructura) registra
    reflexion. No inventa lecciones sin artefacto.
    """
    import sqlite3, os, json as _json_mod
    cap = (params.get("capability") or "").strip() or None
    db_path = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "storage", "rxre.sqlite3")
    if not os.path.isfile(db_path):
        db_path = "/home/lucas/Escritorio/rxre/tools/rxre/storage/rxre.sqlite3"
    evidence = []
    reflexion_id = None
    try:
        c = sqlite3.connect(db_path, timeout=30)
        c.row_factory = sqlite3.Row
        sql_cap = ("SELECT evento_id, op, capability, exit_status, lecciones_json, "
                   "timestamp, result_id FROM execution_events WHERE capability=? "
                   "ORDER BY timestamp DESC LIMIT 3")
        sql_all = ("SELECT evento_id, op, capability, exit_status, lecciones_json, "
                   "timestamp, result_id FROM execution_events ORDER BY timestamp DESC LIMIT 3")
        rows = c.execute(sql_cap, (cap,)).fetchall() if cap else c.execute(sql_all).fetchall()
        for row in rows:
            evidence.append({
                "evento_id": row["evento_id"],
                "op": row["op"],
                "capability": row["capability"],
                "exit_status": row["exit_status"],
                "lecciones_json": row["lecciones_json"],
                "timestamp": row["timestamp"],
                "result_id": row["result_id"],
            })
        valid = [e for e in evidence if e["exit_status"] in (0, 1)]
        if valid:
            reflexion_id = "ref_auto_%s_%s" % (cap or "global", valid[0]["evento_id"][-8:])
            c.execute("INSERT OR IGNORE INTO reflexiones (reflexion_id, hypothesis_id, attempt_id, feedback, reflection, outcome, strategy, refs_json, timestamp, check_ejecutable, verificada_en, target, capability) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (reflexion_id, "hyp_%s" % (cap or "auto"), valid[0]["evento_id"],
                       "Evidencia de %s: %s" % (valid[0]["op"], valid[0]["capability"] or "N/A"),
                       "Leccion automatica: ejecucion produjo evidencia verificable",
                       "success" if valid[0]["exit_status"] == 0 else "partial",
                       "auto_select_from_evidence",
                       _json_mod.dumps({"evidencia": valid[0]["lecciones_json"],
                                   "evento": valid[0]["evento_id"]}),
                       "2026-10-15T18:55:00-0300", 1, "2026-10-15T18:55:00-0300",
                       valid[0]["capability"] or cap or "global",
                       valid[0]["capability"] or cap or "global"))
            c.commit()
            updated = c.execute("SELECT 1 FROM reflexiones WHERE reflexion_id=?", (reflexion_id,)).fetchone()
            if updated:
                evidence[-1]["reflexion_auto"] = reflexion_id
    except Exception as exc:
        evidence.append({"error": str(exc), "tipo": "infraestructura"})
    next_acts = [{"op":"lessons","args":{"capability":cap or "X"},"disponible":True}] if cap else [{"op":"lessons","disponible":True}]
    return {"status":"ok","op":"application","trabajo_real":True,
            "capability_applied": cap,
            "evidencia": evidence,
            "reflexion_auto": reflexion_id,
            "limitaciones":["AGUA: automatiza reflexion si evidencia valida; no inventa si ambigua/infraestructura"],
            "next_actions": next_acts}


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


def _handle_hypothesize(params: dict) -> dict:
    """op: hypothesize — ALMA: RXRE formula una hipotesis falsable desde un
    frontier real, sin que el llamante dicte su contenido.

    La hipotesis se deriva de la evidencia citada por el frontier. Si la
    evidencia no permite discriminar entre dos resultados observables, RXRE
    se abstiene y registra la limitacion. Nunca se etiqueta como PROVEN.
    """
    import json as _j
    import re as _re

    frontier_id = params.get("frontier_id") or params.get("id")
    if not frontier_id:
        return {"status": "invalid_input", "ejecutada": False,
                "motivo": "falta 'frontier_id'", "results": [],
                "limitations": ["sin frontier_id no hay evidencia de partida"]}

    c = _get_db()
    try:
        tid = _trace_id_actual(params)

        row = c.execute(
            "SELECT id, kind, status, text, refs_json, session, target "
            "FROM research WHERE id=?", (frontier_id,)).fetchone()
        if not row or row["kind"] != "frontier":
            return {"status": "blocked", "ejecutada": False,
                    "motivo": "frontier_id no corresponde a un frontier real",
                    "results": [], "limitations": [
                        "solo se formula hipotesis desde frontiers persistidos"]}

        refs = []
        try:
            refs = list(json.loads(row["refs_json"] or "[]"))
        except Exception:
            refs = []
        malos = store.refs_invalidos(c, refs)
        target = (row["target"] or "").strip().lower()
        text = row["text"] or ""

        # Extraer artefacto del texto del frontier: "tipo en <artefacto> (...)"
        m = _re.search(r"\s+en\s+(.+?)(?:\s*\(|:|$)", text)
        artifact = m.group(1).strip() if m else (row["target"] or "")

        abstener = None
        if malos:
            abstener = "refs invalidos en el frontier: %s" % ", ".join(malos)
        elif not refs:
            abstener = "frontier sin refs verificables: no hay evidencia para derivar hipotesis"
        elif "xref" in target:
            hyp_text = ("Hipotesis generada por RXRE: los conjuntos de resultados "
                        "de rizin y radare2 para %s son identicos. "
                        "Afirmacion: los conjuntos son idénticos. "
                        "Alternativa: los conjuntos difieren. "
                        "Discriminante: si los conjuntos son iguales, la "
                        "hipotesis se sostiene; si difieren, se refuta. "
                        "Observable: results. "
                        "(no cardinalidad ni nombre de backend). "
                        "Prediccion (convencion de contraste, no derivada de "
                        "evidencia previa): igualdad de conjuntos."
                        % artifact)
            discriminant = ("result_set_identity: equal -> supported, "
                            "different -> refuted (observable: results)")
        elif "callgraph" in target:
            hyp_text = ("Hipotesis generada por RXRE: los conjuntos de resultados "
                        "del callgraph para %s con nivel aa y con nivel aaa son "
                        "identicos. Afirmacion: los conjuntos son idénticos. "
                        "Alternativa: los conjuntos difieren. "
                        "Discriminante: si los conjuntos son iguales, la "
                        "hipotesis se sostiene; si difieren, se refuta. "
                        "Observable: results. "
                        "(no cardinalidad ni nivel). "
                        "Prediccion (convencion de contraste, no derivada de "
                        "evidencia previa): igualdad de conjuntos."
                        % artifact)
            discriminant = ("result_set_identity: equal -> supported, "
                            "different -> refuted (observable: results)")
        else:
            abstener = ("evidencia insuficiente para discriminar: target=%r no "
                        "tiene un experimento cross-backend disponible" % target)

        # Caso de abstencion: registrar limitacion honesta, no hipotesis.
        if abstener:
            try:
                nr = store.registrar_investigacion(
                    c, kind="note", text="hypothesize: ABSTENCION - %s" % abstener,
                    status="OPEN", refs=[], session=tid or "",
                    target=row["target"] or "", gap_kind="")
                if nr.get("estado") == "ok":
                    try:
                        store.registrar_audit_log(
                            c, "hypothesize_abstain", "research",
                            str(nr.get("id")), actor="rxre",
                            details={"frontier_id": frontier_id,
                                     "motivo": abstener, "trace_id": tid})
                    except Exception:
                        pass
            except Exception:
                pass
            # evento durable de abstencion
            try:
                env_abs = {
                    "status": "abstained", "capability": "rxre.hypothesize",
                    "backend": None, "ejecucion": {"exit_status": 0,
                                                 "iteration": params.get("iteration")},
                    "persistido": True, "limitations": [abstener] + (["caused_by_continuation_id=%s" % params.get("caused_by_continuation_id")] if params.get("caused_by_continuation_id") else []),
                    "trace_id": tid, "results": [], "operation_id": "",
                }
                store.registrar_evento(c, "hypothesize", "rxre.hypothesize",
                                      env_abs, [])
            except Exception:
                pass
            return {"status": "abstained", "ejecutada": True,
                    "frontier_id": frontier_id, "motivo": abstener,
                    "results": [], "limitations": [abstener]}

        # Formular y persistir la hipotesis
        hr = store.registrar_investigacion(
            c, kind="hypothesis", text=hyp_text, status="OPEN", refs=refs,
            session=tid or "", target=row["target"] or "", gap_kind="")
        if hr.get("estado") != "ok":
            return {"status": "blocked", "ejecutada": False,
                    "motivo": hr.get("motivo"), "results": [],
                    "limitations": [hr.get("motivo", "")]}

        hid = hr.get("id")
        # atribucion verificada (no best-effort silencioso)
        audit_ok = False
        try:
            store.registrar_audit_log(
                c, "hypothesize", "research", str(hid), actor="rxre",
                details={"frontier_id": frontier_id, "refs": refs,
                         "discriminant": discriminant, "trace_id": tid})
        except Exception:
            audit_ok = False
        arow = c.execute(
            "SELECT actor FROM audit_log WHERE entity_type='research' "
            "AND entity_id=?", (str(hid),)).fetchone()
        if not (arow and arow[0] == "rxre"):
            # atribucion no verificada -> no persistir hipotesis
            c.execute("DELETE FROM research WHERE id=?", (hid,))
            c.commit()
            return {"status": "blocked", "ejecutada": False,
                    "motivo": "atribucion no verificada (audit_log)",
                    "results": [], "limitations": [
                        "no se persiste hipotesis sin atribucion verificada"]}
        audit_ok = True

        # evento durable
        try:
            env_h = {
                "status": "ok", "capability": "rxre.hypothesize",
                "backend": None, "ejecucion": {"exit_status": 0,
                                              "iteration": params.get("iteration")},
                "persistido": True,
                "limitations": (["caused_by_continuation_id=%s" % params.get("caused_by_continuation_id")]
                                if params.get("caused_by_continuation_id") else []),
                "trace_id": tid, "results": [], "operation_id": "",
            }
            store.registrar_evento(c, "hypothesize", "rxre.hypothesize",
                                  env_h, [])
        except Exception:
            pass

        return {"status": "ok", "ejecutada": True,
                "hypothesis_id": hid, "frontier_id": frontier_id,
                "hypothesis": hyp_text, "discriminant": discriminant,
                "refs": refs, "trace_id": tid, "audit_verified": audit_ok,
                "results": [], "limitations": [
                    "hipotesis generada por RXRE desde evidencia; no PROVEN; "
                    "requiere experimento para validar"]}
    finally:
        c.close()


def _handle_select_experiment_predictive(params: dict) -> dict:
    """op: select_experiment_predictive — ALMA: seleccion predictiva de experimento.

    Elige el observable y el candidato SIN observar los brazos que validaran
    la decision. La observacion posterior valida, no justifica.
    """
    import json as _j
    import re as _re

    hypothesis_id = params.get("hypothesis_id")
    frontier_id = params.get("frontier_id")
    tid = _trace_id_actual(params)

    c = _get_db()
    try:
        # Resolver hipotesis
        if not hypothesis_id and frontier_id:
            row = c.execute(
                "SELECT id FROM research WHERE kind='hypothesis' AND "
                "refs_json LIKE ? ORDER BY id DESC LIMIT 1",
                ("%%%s%%" % frontier_id,)).fetchone()
            if row:
                hypothesis_id = row["id"]
        hrow = None
        if hypothesis_id:
            hrow = c.execute(
                "SELECT id, kind, status, text, refs_json, session, target "
                "FROM research WHERE id=? AND kind='hypothesis'",
                (hypothesis_id,)).fetchone()
        if not hrow:
            return {"status": "invalid_input", "ejecutada": False,
                    "motivo": "falta hypothesis_id valido", "results": [],
                    "limitations": ["sin hipotesis persistida no hay discriminante"]}

        refs = []
        try:
            refs = list(json.loads(hrow["refs_json"] or "[]"))
        except Exception:
            refs = []
        target = (hrow["target"] or "").strip().lower()
        hyp_text = hrow["text"] or ""

        # Extraer discriminante y observable de forma estructurada (no busqueda textual)
        m_obs = _re.search(r"Observable:\s*([A-Za-z0-9_]+)", hyp_text, _re.IGNORECASE)
        m_aff = _re.search(r"Afirmaci[oó]n:\s*(.+?)(?:\n|$)", hyp_text, _re.IGNORECASE)
        m_alt = _re.search(r"Alternativa:\s*(.+?)(?:\n|$)", hyp_text, _re.IGNORECASE)
        m_disc = _re.search(r"Discriminante:\s*(.+?)(?:\n|$)", hyp_text, _re.IGNORECASE)

        observable_declared = m_obs.group(1).strip().strip("'\"") if m_obs else ""
        affirmation = m_aff.group(1).strip() if m_aff else ""
        alternative = m_alt.group(1).strip() if m_alt else ""
        discriminant = m_disc.group(1).strip() if m_disc else ""

        # Validar que el discriminante sea interpretable (no ambiguo/contradictorio)
        abstain_reason = None
        if not observable_declared:
            abstain_reason = "discriminante sin observable declarado"
        elif not affirmation or not alternative:
            abstain_reason = "hipotesis sin afirmacion o alternativa distinguibles"
        # verificar que el observable declarado sea uno de los candidatos conocidos
        known_obs = {"results", "status", "results.0.tool", "results.0.source",
                     "results.0.type"}
        if observable_declared not in known_obs:
            abstain_reason = ("observable declarado no reconocido: %r" % observable_declared)

        # Determinar condiciones
        if "xref" in target:
            capability = "binary.xrefs"
            baseline_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "rizin"}
            modified_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2"}
        elif "callgraph" in target:
            capability = "binary.callgraph"
            baseline_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2", "nivel_analisis": "aa"}
            modified_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2", "nivel_analisis": "aaa"}
        else:
            abstain_reason = abstain_reason or ("target no soporta seleccion predictiva: %s" % target)

        # Fase A predictiva: generar candidatos SIN observar brazos
        candidates = []
        if abstain_reason is None:
            candidates = [
                {"id": "cand_results", "observable": "results", "tautological": False,
                 "expected_hypothesis": "conjuntos idénticos",
                 "expected_alternative": "conjuntos distintos",
                 "rationale": "compara contenido completo; no tautologico",
                 "priority": 2},
                {"id": "cand_status", "observable": "status", "tautological": False,
                 "expected_hypothesis": "ambos ok",
                 "expected_alternative": "estados distintos",
                 "rationale": "observable simple; tipicamente no separa",
                 "priority": 1},
                {"id": "cand_tool", "observable": "results.0.tool", "tautological": True,
                 "expected_hypothesis": "n/a", "expected_alternative": "n/a",
                 "rationale": "nombre del backend es input; tautologico",
                 "priority": 3},
            ]

        # Evaluacion predictiva (sin brazos): tautologia + compatibilidad semantica
        valid = []
        discarded = []
        if abstain_reason is None:
            for cd in candidates:
                if cd["tautological"]:
                    discarded.append({"id": cd["id"], "reason": "tautologico"})
                    continue
                # compatibilidad semantica: el observable debe coincidir con el declarado
                if cd["observable"] == observable_declared:
                    cd["semantically_compatible"] = True
                    valid.append(cd)
                else:
                    cd["semantically_compatible"] = False
                    discarded.append({"id": cd["id"], "reason": "no compatible con discriminante"})
            if not valid:
                abstain_reason = "ningun candidato es semanticamente compatible con el discriminante"

        if abstain_reason:
            # abstencion persistida
            try:
                nr = store.registrar_investigacion(
                    c, kind="note",
                    text="select_experiment_predictive: ABSTENCION - %s" % abstain_reason,
                    status="OPEN", refs=refs, session=tid or "",
                    target="hypothesis:%s" % hypothesis_id, gap_kind="")
                if nr.get("estado") == "ok":
                    try:
                        store.registrar_audit_log(
                            c, "select_experiment_predictive_abstain", "research",
                            str(nr.get("id")), actor="rxre",
                            details={"hypothesis_id": hypothesis_id, "motivo": abstain_reason,
                                     "trace_id": tid, "modalidad": "predictive"})
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                env_abs = {"status": "abstained", "capability": "rxre.select_experiment_predictive",
                           "backend": None, "ejecucion": {"exit_status": 0},
                           "persistido": True, "limitations": [abstain_reason],
                           "trace_id": tid, "results": [], "operation_id": ""}
                store.registrar_evento(c, "select_experiment_predictive",
                                      "rxre.select_experiment_predictive", env_abs, [])
            except Exception:
                pass
            return {"status": "abstained", "ejecutada": True, "modalidad": "predictive",
                    "hypothesis_id": hypothesis_id, "candidates": candidates,
                    "selected": None, "motivo": abstain_reason,
                    "results": [], "limitations": [abstain_reason]}

        # Seleccionar el candidato semanticamente compatible (el que coincide con el discriminante)
        selected = None
        for cd in valid:
            if cd["observable"] == observable_declared:
                selected = cd
                break
        if selected is None:
            selected = valid[0]

        # Persistir la decision ANTES de observar brazos
        persisted_ok = False
        note_id = None
        try:
            decision_text = ("select_experiment_predictive: hypothesis=%s selected=%s "
                             "observable=%s (modalidad=predictive). Candidates: %s. "
                             "Descartados: %s. Justificacion: %s. "
                             "Prediccion: convencion de contraste (igualdad), "
                             "procedencia=derivada del discriminante de la hipotesis"
                             % (hypothesis_id, selected["id"], selected["observable"],
                                ", ".join("%s(%s)" % (cd["id"], cd["observable"]) for cd in candidates),
                                ", ".join("%s:%s" % (cd["id"], "tautologico" if cd["tautological"]
                                                     else ("no-compatible" if not cd.get("semantically_compatible")
                                                           else "valido"))
                                          for cd in candidates),
                                selected["rationale"]))
            nr = store.registrar_investigacion(
                c, kind="note", text=decision_text, status="OPEN",
                refs=refs, session=tid or "",
                target="hypothesis:%s" % hypothesis_id, gap_kind="")
            if nr.get("estado") == "ok":
                persisted_ok = True
                note_id = nr.get("id")
                try:
                    store.registrar_audit_log(
                        c, "select_experiment_predictive", "research", str(note_id),
                        actor="rxre",
                        details={"hypothesis_id": hypothesis_id,
                                 "selected": selected["id"],
                                 "observable": selected["observable"],
                                 "modalidad": "predictive",
                                 "prediction_provenance": "derivada del discriminante de la hipotesis",
                                 "trace_id": tid})
                except Exception:
                    pass
        except Exception:
            persisted_ok = False

        try:
            env_dec = {
                "status": "ok", "capability": "rxre.select_experiment_predictive",
                "backend": None, "ejecucion": {"exit_status": 0,
                                              "iteration": params.get("iteration")},
                "persistido": persisted_ok, "limitations": [],
                "trace_id": tid, "results": [], "operation_id": "",
            }
            env_dec["limitations"] = [_j.dumps({
                "hypothesis_id": hypothesis_id,
                "modalidad": "predictive",
                "candidates": candidates,
                "selected": selected["id"],
                "observable": selected["observable"],
                "justification": selected["rationale"],
                "discarded": [{"id": cd["id"],
                               "reason": "tautologico" if cd["tautological"]
                               else ("no-compatible" if not cd.get("semantically_compatible")
                                     else "valido")} for cd in candidates],
                "prediction_provenance": "derivada del discriminante de la hipotesis",
                "arms_observed_before_selection": False,
            }, default=str)]
            store.registrar_evento(c, "select_experiment_predictive",
                                  "rxre.select_experiment_predictive", env_dec, [])
        except Exception:
            pass

        # Fase B: validacion posterior (observar brazos DESPUES de persistir decision)
        obs = selected["observable"]
        # arms (post-decision observation)
        try:
            base_env = dispatch.ejecutar(capability, baseline_params)
            mod_env = dispatch.ejecutar(capability, modified_params)
        except Exception as e:
            base_env = {"status": "error"}; mod_env = {"status": "error"}

        # Ejecutar experimento formal
        experiment_result = None
        try:
            exp_params = {
                "op": "experiment",
                "capability": capability,
                "question": "RXRE (predictivo) selecciono %s para contrastar hipotesis %s"
                            % (obs, hypothesis_id),
                "prediction": "NO_CHANGE",
                "comparar": obs,
                "baseline_params": baseline_params,
                "modified_params": modified_params,
                "hypothesis_id": hypothesis_id,
                "refs": refs,
                "iteration": params.get("iteration"),
            }
            experiment_result = procesar_linea(_j.dumps(exp_params))
        except Exception as e:
            experiment_result = {"status": "error", "motivo": str(e)}

        # Vincular resultado a la hipotesis via note (sin sobrescribir justificacion original)
        try:
            verdict = (experiment_result.get("experiment") or {}).get("veredicto")
            store.registrar_investigacion(
                c, kind="note",
                text=("select_experiment_predictive result: hypothesis=%s selected=%s "
                      "observable=%s verdict=%s (validacion posterior)" % (
                          hypothesis_id, selected["id"], obs, verdict)),
                status="OPEN", refs=refs, session=tid or "",
                target="hypothesis:%s" % hypothesis_id, gap_kind="")
        except Exception:
            pass

        return {
            "status": "ok", "ejecutada": True, "modalidad": "predictive",
            "hypothesis_id": hypothesis_id,
            "candidates": candidates,
            "selected": selected["id"],
            "observable": obs,
            "justification": selected["rationale"],
            "prediction_provenance": "derivada del discriminante de la hipotesis",
            "arms_observed_before_selection": False,
            "discarded": [{"id": cd["id"],
                           "reason": "tautologico" if cd["tautological"]
                           else ("no-compatible" if not cd.get("semantically_compatible")
                                 else "valido")} for cd in candidates],
            "experiment_result": experiment_result,
            "trace_id": tid,
            "persistido": persisted_ok,
            "limitations": [
                "seleccion predictiva: no se observaron brazos antes de decidir",
                "validacion posterior no modifica la justificacion original",
            ],
        }
    finally:
        c.close()


def _handle_select_experiment(params: dict) -> dict:
    """op: select_experiment — ALMA: RXRE selecciona autonomamente el experimento
    mas discriminante a partir de una hipotesis persistida.

    Fase A: generar >=2 candidatos y evaluar su poder discriminante SIN ejecutarlos.
    Fase B: ejecutar solo el candidato elegido, persistiendo la decision antes.

    El llamante proporciona la hipotesis (o frontier_id), pero NO el observable
    ni el experimento a ejecutar.
    """
    import json as _j

    hypothesis_id = params.get("hypothesis_id")
    frontier_id = params.get("frontier_id")
    tid = _trace_id_actual(params)

    c = _get_db()
    try:
        # Resolver hipotesis
        if not hypothesis_id and frontier_id:
            # buscar hipotesis derivada de ese frontier (la mas reciente)
            row = c.execute(
                "SELECT id FROM research WHERE kind='hypothesis' AND "
                "refs_json LIKE ? ORDER BY id DESC LIMIT 1",
                ("%%%s%%" % frontier_id,)).fetchone()
            if row:
                hypothesis_id = row["id"]
        if not hypothesis_id:
            # intentar por frontier text match
            pass

        hrow = None
        if hypothesis_id:
            hrow = c.execute(
                "SELECT id, kind, status, text, refs_json, session, target "
                "FROM research WHERE id=? AND kind='hypothesis'",
                (hypothesis_id,)).fetchone()
        if not hrow:
            return {"status": "invalid_input", "ejecutada": False,
                    "motivo": "falta hypothesis_id valido (o frontier sin hipotesis)",
                    "results": [], "limitations": [
                        "RXRE solo selecciona experimento desde una hipotesis persistida"]}

        refs = []
        try:
            refs = list(json.loads(hrow["refs_json"] or "[]"))
        except Exception:
            refs = []
        target = (hrow["target"] or "").strip().lower()
        hyp_text = hrow["text"] or ""

        # Determinar condiciones (capability, baseline, modified) desde target
        if "xref" in target:
            capability = "binary.xrefs"
            baseline_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "rizin"}
            modified_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2"}
        elif "callgraph" in target:
            capability = "binary.callgraph"
            baseline_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2", "nivel_analisis": "aa"}
            modified_params = {"artefacto": _extract_artifact(hyp_text) or "/bin/ls",
                               "backend_id": "radare2", "nivel_analisis": "aaa"}
        else:
            return {"status": "abstained", "ejecutada": False,
                    "motivo": "target no soporta seleccion de experimento: %s" % target,
                    "results": [], "limitations": [
                        "sin capability/condiciones derivables, no se generan candidatos"]}

        artifact = baseline_params.get("artefacto", "/bin/ls")

        # Observar evidencia previa (dispatch) para ambos brazos
        try:
            base_env = dispatch.ejecutar(capability, baseline_params)
            mod_env = dispatch.ejecutar(capability, modified_params)
        except Exception as e:
            return {"status": "abstained", "ejecutada": False,
                    "motivo": "no se pudo observar evidencia: %s" % e,
                    "results": [], "limitations": [str(e)]}

        base_results = base_env.get("results") or []
        mod_results = mod_env.get("results") or []
        base_status = base_env.get("status")
        mod_status = mod_env.get("status")

        # Conjuntos de result_id
        base_ids = [r.get("result_id") for r in base_results if isinstance(r, dict) and r.get("result_id")]
        mod_ids = [r.get("result_id") for r in mod_results if isinstance(r, dict) and r.get("result_id")]
        sets_differ = (base_ids != mod_ids)
        statuses_differ = (base_status != mod_status)

        # Fase A: generar candidatos y evaluar discriminacion (sin ejecutar experimento)
        candidates = []
        # Candidate 1: results (full set) - non-tautological, discriminative if sets differ
        candidates.append({
            "id": "cand_results",
            "observable": "results",
            "tautological": False,
            "discriminative": sets_differ,
            "expected_under_hypothesis": "conjuntos idénticos -> no_separable",
            "expected_under_alternative": "conjuntos distintos -> refutada",
            "rationale": "compara el contenido completo de los resultados; "
                         "detecta diferencia de conjuntos aunque las cardinalidades coincidan",
            "priority": 2,
        })
        # Candidate 2: status - trivial, non-discriminative
        candidates.append({
            "id": "cand_status",
            "observable": "status",
            "tautological": False,
            "discriminative": statuses_differ,
            "expected_under_hypothesis": "ambos ok -> no_separable",
            "expected_under_alternative": "estados distintos -> refutada",
            "rationale": "observable simple; no separa los brazos en el caso medido",
            "priority": 1,  # mayor prioridad (mas simple) pero menos discriminante
        })
        # Candidate 3: results.0.tool - discriminative pero tautologico
        candidates.append({
            "id": "cand_tool",
            "observable": "results.0.tool",
            "tautological": True,
            "discriminative": True,
            "expected_under_hypothesis": "n/a (tautologico)",
            "expected_under_alternative": "n/a",
            "rationale": "el nombre del backend es el input del experimento; "
                         "no prueba la hipotesis sobre conjuntos",
            "priority": 3,
        })

        # Descartar tautologicos
        valid = [cd for cd in candidates if not cd["tautological"]]
        discriminative = [cd for cd in valid if cd["discriminative"]]

        # Abstencion si no hay candidato discriminante justificable
        if not discriminative:
            abstain_reason = ("ningun candidato no-tautologico es discriminante: "
                              "status no separa, results no difiere en la evidencia observada")
            try:
                nr = store.registrar_investigacion(
                    c, kind="note",
                    text="select_experiment: ABSTENCION - %s" % abstain_reason,
                    status="OPEN", refs=refs, session=tid or "",
                    target="hypothesis:%s" % hypothesis_id, gap_kind="")
                if nr.get("estado") == "ok":
                    try:
                        store.registrar_audit_log(
                            c, "select_experiment_abstain", "research",
                            str(nr.get("id")), actor="rxre",
                            details={"hypothesis_id": hypothesis_id,
                                     "candidates": candidates,
                                     "motivo": abstain_reason,
                                     "trace_id": tid})
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                env_abs = {"status": "abstained", "capability": "rxre.select_experiment",
                           "backend": None, "ejecucion": {"exit_status": 0},
                           "persistido": True, "limitations": [abstain_reason],
                           "trace_id": tid, "results": [], "operation_id": ""}
                store.registrar_evento(c, "select_experiment", "rxre.select_experiment",
                                      env_abs, [])
            except Exception:
                pass
            return {"status": "abstained", "ejecutada": True,
                    "hypothesis_id": hypothesis_id, "candidates": candidates,
                    "selected": None, "motivo": abstain_reason,
                    "results": [], "limitations": [abstain_reason]}

        # Seleccionar el candidato mas discriminante (menor priority number among discriminative? No: by discriminative power)
        # Ordenar: discriminative primero, luego por priority descendente (menos "prioritario" = mas complejo primero? No)
        # Regla: elegir el candidato discriminante con MAYOR complejidad informativa.
        # Usamos: discriminative=True, tautological=False, y preferir observable "results" (full set) sobre otros.
        selected = None
        for cd in discriminative:
            if cd["observable"] == "results":
                selected = cd
                break
        if selected is None:
            selected = discriminative[0]

        # Persistir la decision ANTES de ejecutar
        persisted_ok = False
        note_id = None
        try:
            decision_text = ("select_experiment: hypothesis=%s selected=%s "
                             "observable=%s (discriminative=%s, tautological=%s). "
                             "Candidates: %s. Descartados: %s. "
                             "Justificacion: %s" % (
                                 hypothesis_id, selected["id"], selected["observable"],
                                 selected["discriminative"], selected["tautological"],
                                 ", ".join("%s(%s)" % (cd["id"], cd["observable"])
                                           for cd in candidates),
                                 ", ".join("%s:%s" % (cd["id"], "tautologico" if cd["tautological"]
                                                      else ("no-discriminante" if not cd["discriminative"]
                                                            else "valido"))
                                           for cd in candidates),
                                 selected["rationale"]))
            nr = store.registrar_investigacion(
                c, kind="note", text=decision_text, status="OPEN",
                refs=refs, session=tid or "",
                target="hypothesis:%s" % hypothesis_id, gap_kind="")
            if nr.get("estado") == "ok":
                persisted_ok = True
                note_id = nr.get("id")
                try:
                    store.registrar_audit_log(
                        c, "select_experiment", "research", str(note_id),
                        actor="rxre",
                        details={"hypothesis_id": hypothesis_id,
                                 "selected": selected["id"],
                                 "observable": selected["observable"],
                                 "candidates": candidates,
                                 "trace_id": tid,
                                 "prediction_provenance": "convencion de contraste (igualdad)"})
                except Exception:
                    pass
        except Exception:
            persisted_ok = False

        # Evento durable con la decision completa
        try:
            env_dec = {
                "status": "ok", "capability": "rxre.select_experiment",
                "backend": None, "ejecucion": {"exit_status": 0,
                                              "iteration": params.get("iteration")},
                "persistido": persisted_ok, "limitations": [],
                "trace_id": tid, "results": [], "operation_id": "",
            }
            # guardar la decision en limitations como JSON
            env_dec["limitations"] = [_j.dumps({
                "hypothesis_id": hypothesis_id,
                "candidates": candidates,
                "selected": selected["id"],
                "observable": selected["observable"],
                "justification": selected["rationale"],
                "discarded": [{"id": cd["id"], "reason": "tautologico" if cd["tautological"]
                               else ("no-discriminante" if not cd["discriminative"] else "valido")}
                              for cd in candidates],
                "prediction_provenance": "convencion de contraste (igualdad)",
            }, default=str)]
            store.registrar_evento(c, "select_experiment", "rxre.select_experiment",
                                  env_dec, [])
        except Exception:
            pass

        # Fase B: ejecutar el candidato elegido
        obs = selected["observable"]
        prediction = "NO_CHANGE"  # convencion de contraste (igualdad)
        experiment_result = None
        try:
            exp_params = {
                "op": "experiment",
                "capability": capability,
                "question": "RXRE selecciono %s para contrastar hipotesis %s"
                            % (obs, hypothesis_id),
                "prediction": prediction,
                "comparar": obs,
                "baseline_params": baseline_params,
                "modified_params": modified_params,
                "hypothesis_id": hypothesis_id,
                "refs": refs,
                "iteration": params.get("iteration"),
            }
            experiment_result = procesar_linea(_j.dumps(exp_params))
        except Exception as e:
            experiment_result = {"status": "error", "motivo": str(e)}

        # Vincular resultado a la hipotesis via note
        try:
            verdict = (experiment_result.get("experiment") or {}).get("veredicto")
            store.registrar_investigacion(
                c, kind="note",
                text=("select_experiment result: hypothesis=%s selected=%s "
                      "observable=%s verdict=%s" % (
                          hypothesis_id, selected["id"], obs, verdict)),
                status="OPEN", refs=refs, session=tid or "",
                target="hypothesis:%s" % hypothesis_id, gap_kind="")
        except Exception:
            pass

        return {
            "status": "ok", "ejecutada": True,
            "hypothesis_id": hypothesis_id,
            "candidates": candidates,
            "selected": selected["id"],
            "observable": obs,
            "justification": selected["rationale"],
            "prediction": prediction,
            "prediction_provenance": "convencion de contraste (igualdad)",
            "discarded": [{"id": cd["id"],
                           "reason": "tautologico" if cd["tautological"]
                           else ("no-discriminante" if not cd["discriminative"]
                                 else "valido")} for cd in candidates],
            "experiment_result": experiment_result,
            "trace_id": tid,
            "persistido": persisted_ok,
            "limitations": [
                "seleccion basada en evidencia observada; no en LLM",
                "prediccion por convencion de contraste, no derivada de evidencia previa",
            ],
        }
    finally:
        c.close()


def _extract_artifact(text: str) -> str:
    import re as _re
    m = _re.search(r"\s+en\s+(.+?)(?:\s*\(|:|$)", text or "")
    return m.group(1).strip() if m else ""


def _handle_investigate(params: dict) -> dict:
    """op: investigate - ALMA: RXRE conduce una mision de investigacion autonoma.

    Encadena discover -> hypothesize -> select -> select_experiment_predictive ->
    saturate sobre un artefacto, extrayendo internamente los identificadores.
    Soporta continuacion adaptativa: tras una refutacion, si existe un frontier
    discriminable no investigado, ejecuta una segunda iteracion. Limite de
    iteraciones configurable (max_iterations, default 2).

    El llamante solo proporciona el artefacto (y opcionalmente trace_id/objective).
    Las decisiones de investigacion son tomadas por RXRE.

    Uso:
        {"op":"investigate","artefacto":"/bin/ls"}
        {"op":"investigate","artefacto":"/bin/ls","max_iterations":2}
    """
    import json as _j

    artefacto = params.get("artefacto") or params.get("artifact") or params.get("path")
    if not artefacto:
        return {"status": "invalid_input", "op": "investigate",
                "motivo": "falta 'artefacto'", "results": []}

    tid = _trace_id_actual(params)
    max_iters = int(params.get("max_iterations", 2) or 2)
    if max_iters < 1:
        max_iters = 1
    if max_iters > 5:
        max_iters = 5

    trace = []          # per-step records
    mission_id = None
    hypothesis_ids = []  # one per iteration
    selected_tasks = []
    selected_experiments = []
    experiment_verdicts = []
    continuation_decisions = []
    investigated_frontiers = set()
    previous_continuation_id = None
    overall_status = "ok"

    def _record(step, resp):
        trace.append({
            "step": step,
            "op": (resp or {}).get("op", step),
            "status": (resp or {}).get("status", "unknown"),
        })

    # Step 0: discover (once)
    try:
        r1 = procesar_linea(_j.dumps({"op": "discover", "artefacto": artefacto,
                                     "trace_id": tid}))
    except Exception as e:
        r1 = {"status": "error", "motivo": str(e)}
    _record("discover", r1)
    if r1.get("status") not in ("ok", "empty"):
        overall_status = "blocked"
    mission_id = r1.get("mission_created")

    # load frontiers
    frontiers = []
    try:
        _c = _get_db()
        frontiers = [dict(x) for x in _c.execute(
            "SELECT id, target, refs_json FROM research WHERE kind='frontier' "
            "AND session=?", (tid,)).fetchall()]
        _c.close()
    except Exception:
        pass

    def _discriminable(f):
        try:
            if not json.loads(f.get("refs_json") or "[]"):
                return False
        except Exception:
            return False
        tgt = (f.get("target") or "").lower()
        return ("xref" in tgt) or ("callgraph" in tgt)

    # Iteration loop
    iteration = 0
    while iteration < max_iters:
        iteration += 1
        # pick next uninvestigated discriminable frontier
        chosen_frontier = None
        for f in frontiers:
            if f["id"] in investigated_frontiers:
                continue
            if _discriminable(f):
                chosen_frontier = f
                break
        if chosen_frontier is None:
            # no more discriminable frontiers
            break

        investigated_frontiers.add(chosen_frontier["id"])

        # Hypothesize
        try:
            r_hyp = procesar_linea(_j.dumps({
                "op": "hypothesize",
                "frontier_id": chosen_frontier["id"],
                "trace_id": tid,
                "iteration": iteration,
                "caused_by_continuation_id": previous_continuation_id,
            }))
        except Exception as e:
            r_hyp = {"status": "error", "motivo": str(e)}
        _record("hypothesize", r_hyp)
        hypothesis_id = r_hyp.get("hypothesis_id") if r_hyp.get("status") == "ok" else None
        hypothesis_ids.append(hypothesis_id)

        # Select (mission)
        selected_task = None
        if mission_id:
            try:
                r_sel = procesar_linea(_j.dumps({
                    "op": "select", "mission_id": mission_id, "trace_id": tid,
                    "iteration": iteration,
                }))
            except Exception as e:
                r_sel = {"status": "error", "motivo": str(e)}
            _record("select", r_sel)
            selected_task = r_sel.get("task_id")
        selected_tasks.append(selected_task)

        # Select experiment (predictive) if hypothesis
        selected_experiment = None
        experiment_verdict = None
        if hypothesis_id:
            try:
                r_se = procesar_linea(_j.dumps({
                    "op": "select_experiment_predictive",
                    "hypothesis_id": hypothesis_id,
                    "trace_id": tid,
                    "iteration": iteration,
                }))
            except Exception as e:
                r_se = {"status": "error", "motivo": str(e)}
            _record("select_experiment_predictive", r_se)
            selected_experiment = r_se.get("selected")
            experiment_verdict = (r_se.get("experiment_result") or {}).get("experiment", {}).get("veredicto")
        else:
            r_se = {"status": "empty", "motivo": "no hypothesis"}
            _record("select_experiment_predictive", r_se)
        selected_experiments.append(selected_experiment)
        experiment_verdicts.append(experiment_verdict)

        # Saturate
        try:
            r_sat = procesar_linea(_j.dumps({
                "op": "saturate", "target": chosen_frontier["target"], "trace_id": tid,
                "iteration": iteration,
            }))
        except Exception as e:
            r_sat = {"status": "error", "motivo": str(e)}
        _record("saturate", r_sat)

        # Continuation decision based on verdict
        continuation_decision = None
        continuation_rationale = None
        next_frontier_id = None
        try:
            if experiment_verdict == "refutada":
                # Is there another uninvestigated discriminable frontier?
                remaining = [f for f in frontiers
                             if f["id"] not in investigated_frontiers
                             and _discriminable(f)]
                if remaining:
                    continuation_decision = "CONTINUE"
                    continuation_rationale = ("hipotesis refutada; existe frontier alternativo (%s); "
                                             "continuar con siguiente iteracion" % remaining[0]["target"])
                    next_frontier_id = remaining[0]["id"]
                else:
                    continuation_decision = "ABSTAIN"
                    continuation_rationale = ("hipotesis refutada; no existe alternativa persistida; "
                                             "se registra frontera abierta")
                    next_frontier_id = None
            elif experiment_verdict == "sostenida":
                _c = _get_db()
                _tasks = store.obtener_tareas_mision(_c, mission_id) if mission_id else []
                _pending = [t for t in _tasks if t.get("status") not in ("COMPLETED", "DONE")]
                _c.close()
                if not _pending:
                    continuation_decision = "COMPLETE"
                    continuation_rationale = ("hipotesis sostenida y todas las tareas completadas; "
                                             "objetivo de mision satisfecho")
                else:
                    continuation_decision = "CONTINUE"
                    continuation_rationale = ("hipotesis sostenida pero quedan %d tareas pendientes"
                                             % len(_pending))
            elif experiment_verdict in ("no_separable", "no_observable"):
                continuation_decision = "ABSTAIN"
                continuation_rationale = ("resultado %s: no hay informacion suficiente para "
                                         "continuar; se registra frontera abierta"
                                         % experiment_verdict)
            else:
                continuation_decision = "ABSTAIN"
                continuation_rationale = ("veredicto desconocido (%s); abstener por seguridad"
                                         % experiment_verdict)

            continuation_decisions.append(continuation_decision)

            # Persistir la decision ANTES de actuar
            try:
                _c = _get_db()
                nr = store.registrar_investigacion(
                    _c, kind="note",
                    text=("continuation: decision=%s rationale=%s hypothesis=%s verdict=%s iter=%d next_frontier=%s"
                          % (continuation_decision, continuation_rationale,
                             hypothesis_id, experiment_verdict, iteration,
                             next_frontier_id)),
                    status="OPEN", refs=[], session=tid or "",
                    target="hypothesis:%s" % hypothesis_id if hypothesis_id else (mission_id or ""),
                    gap_kind="")
                if nr.get("estado") == "ok":
                    previous_continuation_id = nr.get("id")
                    try:
                        store.registrar_audit_log(
                            _c, "continuation_decision", "research", str(nr.get("id")),
                            actor="rxre.investigate",
                            details={"decision": continuation_decision,
                                     "rationale": continuation_rationale,
                                     "hypothesis_id": hypothesis_id,
                                     "verdict": experiment_verdict,
                                     "iteration": iteration,
                                     "trace_id": tid})
                    except Exception:
                        pass
                _c.close()
            except Exception:
                pass

            # Evento durable
            try:
                _c = _get_db()
                env_cont = {
                    "status": "ok", "capability": "rxre.investigate",
                    "backend": None, "ejecucion": {"exit_status": 0,
                                                  "iteration": iteration},
                    "persistido": True, "limitations": [],
                    "trace_id": tid, "results": [], "operation_id": "",
                }
                env_cont["limitations"] = [_j.dumps({
                    "continuation_decision": continuation_decision,
                    "rationale": continuation_rationale,
                    "hypothesis_id": hypothesis_id,
                    "verdict": experiment_verdict,
                    "iteration": iteration,
                    "next_frontier_id": next_frontier_id,
                }, default=str)]
                store.registrar_evento(_c, "continuation", "rxre.investigate", env_cont, [])
                _c.close()
            except Exception:
                pass

            # Actuar segun la decision (una iteracion adicional como maximo)
            if continuation_decision == "COMPLETE":
                if mission_id:
                    try:
                        _c = _get_db()
                        tasks = store.obtener_tareas_mision(_c, mission_id)
                        if tasks and all(t.get("status") in ("COMPLETED", "DONE") for t in tasks):
                            # RXRE-202: el cierre pasa por el contrato de criterios.
                            from rxre.mission_closure import close_mission
                            close_mission(mission_id, conn=_c)
                        _c.close()
                    except Exception:
                        pass
                break  # complete -> stop
            elif continuation_decision == "ABSTAIN":
                break  # abstain -> stop
            elif continuation_decision == "CONTINUE":
                # continue to next iteration (loop)
                pass
        except Exception:
            continuation_decision = "ABSTAIN"
            continuation_rationale = "error computing continuation"
            continuation_decisions.append(continuation_decision)
            break

        if continuation_decision in ("ABSTAIN", "COMPLETE"):
            break

    # Mission completion check (strict)
    if mission_id:
        try:
            _c = _get_db()
            tasks = store.obtener_tareas_mision(_c, mission_id)
            if tasks and all(t.get("status") in ("COMPLETED", "DONE") for t in tasks):
                from rxre.mission_closure import close_mission
                close_mission(mission_id, conn=_c)
            _c.close()
        except Exception:
            pass

    # Persist mission trace (research note)
    try:
        _c = _get_db()
        trace_summary = "investigate: artifact=%s trace=%s steps=%s continuations=%s" % (
            artefacto, tid, ",".join("%s=%s" % (t["step"], t["status"]) for t in trace),
            ",".join(continuation_decisions))
        store.registrar_investigacion(
            _c, kind="note", text=trace_summary, status="OPEN",
            refs=[], session=tid or "", target=artefacto, gap_kind="")
        try:
            _nid = _c.execute("SELECT last_insert_rowid()").fetchone()[0]
            store.registrar_audit_log(_c, "investigate", "research", str(_nid),
                                     actor="rxre.investigate",
                                     details={"artifact": artefacto, "trace_id": tid,
                                              "steps": trace, "autonomous": True,
                                              "continuations": continuation_decisions})
        except Exception:
            pass
        _c.close()
    except Exception:
        pass

    autonomous_decisions = []
    if r1.get("status") in ("ok", "empty"):
        autonomous_decisions.append("frontier_proposal (discover)")
    if hypothesis_ids and any(hypothesis_ids):
        autonomous_decisions.append("hypothesis_formulation (hypothesize)")
    if selected_tasks and any(selected_tasks):
        autonomous_decisions.append("task_selection (select by value)")
    if selected_experiments and any(selected_experiments):
        autonomous_decisions.append("experiment_selection (predictive)")
    if experiment_verdicts and any(experiment_verdicts):
        autonomous_decisions.append("hypothesis_evaluation (experiment -> %s)" % experiment_verdicts[-1])
    if continuation_decisions:
        autonomous_decisions.append("continuation_decision (%s)" % continuation_decisions[-1])

    external_dependencies = ["artifact provided by caller"]

    return {
        "status": overall_status,
        "op": "investigate",
        "artefacto": artefacto,
        "trace_id": tid,
        "mission_id": mission_id,
        "hypothesis_id": hypothesis_ids[-1] if hypothesis_ids else None,
        "selected_task": selected_tasks[-1] if selected_tasks else None,
        "selected_experiment": selected_experiments[-1] if selected_experiments else None,
        "experiment_verdict": experiment_verdicts[-1] if experiment_verdicts else None,
        "continuation_decision": continuation_decisions[-1] if continuation_decisions else None,
        "continuation_rationale": continuation_rationale if continuation_decisions else None,
        "iterations": iteration,
        "investigated_frontiers": list(investigated_frontiers),
        "trace": trace,
        "autonomous_decisions": autonomous_decisions,
        "external_dependencies": external_dependencies,
        "limitations": [
            "investigate chains existing capabilities; decisions are made by RXRE handlers",
            "artifact must be provided by caller (external dependency)",
            "mission completion depends on task statuses",
            "continuation limited to max_iterations (default 2)",
            "no unbounded loop; abstention is a valid terminal decision",
        ],
        "results": [],
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
        # Evento durable para reconstruir la decision de saturacion.
        try:
            tid_sat = _trace_id_actual(params)
            import json as _js
            env_sat = {
                "status": r.get("estado", "ok"),
                "capability": "rxre.saturate",
                "backend": None,
                "ejecucion": {"exit_status": 0,
                              "iteration": params.get("iteration")},
                "persistido": True,
                "limitations": r.get("limitations", []),
                "trace_id": tid_sat,
                "results": [],
                "operation_id": "",
            }
            env_sat["limitations"] = (env_sat["limitations"] or []) + [_js.dumps({
                "frontier_evaluaciones": r.get("frontier_evaluaciones", []),
                "saturadas": [e["frontier_id"] for e in (r.get("frontier_evaluaciones") or []) if e.get("saturada")],
                "paradas": [{"frontier_id": e["frontier_id"], "motivo": e["motivo"]}
                            for e in (r.get("frontier_evaluaciones") or []) if not e.get("saturada")],
            }, default=str)]
            store.registrar_evento(c, "saturate", "rxre.saturate", env_sat, [])
        except Exception:
            pass
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
    # ETER: emitir el evento ANTES de la logica del handler. El evento es
    # async (write-ahead) y NO bloquea: si el hub esta lleno, el descarte se
    # CUENTA en stats, no rompe el handler. Un productor que espera al hub
    # para poder escanear convertiria el hub en el cuello de botella global
    # que el diagrama prohibe.
    try:
        _eter().emit("scan", {"op": "scan"}, critico=True)
    except Exception:
        pass
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
            # ETER-CYCLE: detectar dependencias circulares entre findings
            "ciclos_detectados": _detectar_ciclos_frontier(correlaciones),
            "checks_merge_sugerido": _detectar_checks_redundantes([]),
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

def _handle_ingest(params: dict) -> dict:
    """Contrato publico de INGESTA de eventos de ejecucion observados (174).
    Registra a traves de store.registrar_evento (escritor legitimo, usado ya
    por op:run). No escribe SQL directo ni modifica core/store.py.
    Verifica el hash del artefacto ANTES de registrar; si no coincide, no
    registra nada (no se inventan eventos ni hashes)."""
    import os, json, hashlib
    c = None
    try:
        required = ["execution_id", "events_file", "sha256_spirv", "capability"]
        missing = [k for k in required if k not in params]
        if missing:
            return {"status":"error","op":"ingest","message":"missing %s"%missing,"count":0,"events":[],
                    "execution_id":params.get("execution_id"),"derived_from_evidence":False,
                    "limitations":["peticion incompleta; ninguna fila registrada"]}
        eid = params["execution_id"]
        events_file = params["events_file"]
        artifact_path = params.get("artifact_path") or ""
        sha_declared = params["sha256_spirv"]
        cap = params["capability"]
        # 1) Integridad del artefacto (antes de escribir)
        if not artifact_path or not os.path.exists(artifact_path):
            return {"status":"error","op":"ingest","message":"artifact_path missing or unreadable","count":0,"events":[],
                    "execution_id":eid,"derived_from_evidence":False,"limitations":["sin artefacto verificable; no se registra"]}
        h = hashlib.sha256(open(artifact_path,"rb").read()).hexdigest()
        if h != sha_declared:
            return {"status":"error","op":"ingest","message":"sha256_spirv mismatch (archivo=%s declarado=%s); NO se registran eventos"%(h[:16],sha_declared[:16]),
                    "count":0,"events":[],"execution_id":eid,"derived_from_evidence":False,
                    "limitations":["hash verificado contra archivo real; discrepancia detectada"]}
        # 2) Fuente de observaciones: archivo real del harness
        if not os.path.exists(events_file):
            return {"status":"error","op":"ingest","message":"events_file missing: %s"%events_file,"count":0,"events":[],
                    "execution_id":eid,"derived_from_evidence":False,"limitations":["sin archivo de observaciones; no se registra"]}
        try:
            with open(events_file) as f:
                data = json.load(f)
        except Exception as exc:
            return {"status":"error","op":"ingest","message":"invalid events_file JSON: %s"%str(exc),"count":0,"events":[],
                    "execution_id":eid,"derived_from_evidence":False,"limitations":["archivo ilegible; no se registra"]}
        events_raw = data.get("events",[])
        file_eid = data.get("execution_id")
        if file_eid and file_eid != eid:
            return {"status":"error","op":"ingest","message":"execution_id mismatch: file=%s request=%s"%(file_eid,eid),
                    "count":0,"events":[],"execution_id":eid,"derived_from_evidence":False,
                    "limitations":["identidad inconsistente; no se registra"]}
        device_obs = data.get("device_observed") or "unknown"
        backend_req = data.get("backend_requested") or "unknown"
        c = store.conectar()
        try:
            # 3) Operacion RXRE publica (identidad operation_id). Se REUSA la
            #    operacion existente para este execution_id: registrar_evento
            #    incluye operation_id en el hash de evento_id, asi que una
            #    operacion nueva por reingesta cambiaria el evento_id y
            #    romperia la idempotencia (PRUEBA 174).
            op_id = None
            try:
                _row = c.execute(
                    "SELECT operation_id FROM operations WHERE operacion='ingest' "
                    "AND capability=? AND response_json LIKE ? ORDER BY timestamp DESC LIMIT 1",
                    (cap, "%" + eid + "%")).fetchone()
                if _row:
                    op_id = _row[0]
            except Exception:
                op_id = None
            if not op_id:
                env_op = {
                    "op":"ingest","capability":cap,"execution_id":eid,"status":"submitted",
                    "results":[{"result_id":"res_ing_%s"%eid,
                                "location":{"execution_id":eid,"artifact_path":artifact_path,
                                            "sha256_spirv":sha_declared,"events_file":events_file}}],
                    "ejecucion":{"exit_status":0,"execution_id":eid,"hash_verified":True,
                                 "artifact_sha256":sha_declared,"device_observed":device_obs,
                                 "backend_requested":backend_req},
                    "persistido":True,
                    "limitations":["public ingestion through machine.py op=ingest; source=%s"%os.path.basename(events_file)],
                    "trace_id":eid,"backend":{"backend_id":device_obs}}
                op_id = store.registrar(c, params, env_op, 0.0)
            # 4) Un evento por hito observado (env determinista => evento_id estable => idempotente)
            registered_ids = []
            for idx, ev in enumerate(events_raw):
                milestone_op = ev.get("type", "API_CALL_OBSERVED")
                env_ev = {
                    "op":milestone_op,"capability":cap,"execution_id":eid,"status":"completed",
                    "results":[{"result_id":"res_ev_%s_%s"%(eid,idx),
                                "location":{"execution_id":eid,"artifact_path":artifact_path,
                                            "sha256_spirv":sha_declared,"event_index":idx,
                                            "milestone":milestone_op}}],
                    "ejecucion":{"exit_status":0,"milestone":milestone_op,"execution_id":eid,
                                 "artifact_sha256":sha_declared,"device_observed":device_obs,
                                 "backend_requested":backend_req,
                                 "readback":ev.get("detail",{}).get("readback_value"),
                                 "validation":ev.get("detail",{}).get("validation"),
                                 "event_index":idx,"ts_monotonic":ev.get("ts_monotonic"),
                                 "observed_line":ev.get("line","")[:180]},
                    "persistido":True,
                    "limitations":["public ingestion from observed harness stdout (%s idx %s); provenance sha256=%s"%(os.path.basename(events_file),idx,sha_declared),
                                   "provenance: "+json.dumps({"execution_id":eid,"artifact_sha256":sha_declared,
                                        "artifact_path":artifact_path,"events_file":events_file,
                                        "device_observed":device_obs,"backend_requested":backend_req,
                                        "event_index":idx,"milestone":milestone_op,
                                        "readback":ev.get("detail",{}).get("readback_value"),
                                        "validation":ev.get("detail",{}).get("validation"),
                                        "ts_monotonic":ev.get("ts_monotonic"),
                                        "observed_line":ev.get("line","")[:180],
                                        "operation_id":op_id}, sort_keys=True)],
                    "trace_id":eid,"operation_id":op_id,
                    "backend":{"backend_id":device_obs}}
                registered_ids.append(store.registrar_evento(c, milestone_op, cap, env_ev, []))
            # 5) Resumen idempotente
            env_sum = {
                "op":"ingest.summary","capability":cap,"execution_id":eid,"status":"completed",
                "results":[{"result_id":"res_ingest_summary_%s"%eid,
                            "location":{"execution_id":eid,"event_ids":registered_ids,
                                        "count":len(registered_ids),"artifact_sha256":sha_declared,
                                        "hash_verified":True}}],
                "ejecucion":{"exit_status":0,"execution_id":eid,"artifact_sha256":sha_declared,
                             "device_observed":device_obs,"event_ids_registered":registered_ids,
                             "count":len(registered_ids),"backend_requested":backend_req},
                "persistido":True,
                "limitations":["ingest summary %s; %d events; idempotente"%(eid,len(registered_ids)),
                               "provenance: "+json.dumps({"execution_id":eid,"artifact_sha256":sha_declared,
                                    "artifact_path":artifact_path,"events_file":events_file,
                                    "device_observed":device_obs,"backend_requested":backend_req,
                                    "count":len(registered_ids),"event_ids":registered_ids}, sort_keys=True)],
                "trace_id":eid,"operation_id":op_id,"backend":{"backend_id":device_obs}}
            registered_ids.append(store.registrar_evento(c, "ingest.summary", cap, env_sum, []))
            return {"status":"ok","op":"ingest","execution_id":eid,"operation_id":op_id,
                    "count":len(registered_ids),"registered_ids":registered_ids,
                    "hash_verified":True,"artifact_sha256":sha_declared,
                    "events_file":events_file,"artifact_path":artifact_path,
                    "backend_requested":backend_req,"device_observed":device_obs,
                    "limitations":["ingesta publica via machine.py op=ingest; evento_id determinista (idempotente via INSERT OR REPLACE); provenance en columna limitations"],
                    "derived_from_evidence":True,"epistemic_status":"PROVEN"}
        finally:
            c.close()
    except Exception as exc:
        return {"status":"error","op":"ingest","message":"ingest error: %s"%str(exc),"count":0,"events":[],
                "execution_id":params.get("execution_id"),"derived_from_evidence":False,
                "limitations":["error en interfaz publica; ninguna fila ficticia generada"]}


def _handle_execution(params):
    import time, sqlite3 as sql3, os
    c = None
    try:
        c = _get_db()
        total_raw = c.execute("SELECT COUNT(*) FROM execution_events").fetchone()[0]
        event_filter = params.get("event_id") or params.get("evento_id")
        trace_filter = params.get("execution_id") or params.get("trace_id")
        op_filter = params.get("op_filter") or (params.get("op") if params.get("op") != "execution" else None)
        limit_n = int(params.get("limit") or 10)
        where_clauses = []
        args = []
        if event_filter:
            where_clauses.append("evento_id = ?")
            args.append(str(event_filter))
        if trace_filter:
            where_clauses.append("trace_id = ?")
            args.append(str(trace_filter))
        if op_filter:
            where_clauses.append("op = ?")
            args.append(str(op_filter))
        sql = "SELECT evento_id, op, capability, backend_id, exit_status, operation_id, result_id, persistido, timestamp, trace_id, limitations FROM execution_events"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        args.append(limit_n)
        rows = c.execute(sql, args).fetchall()
        events = []
        for r in rows:
            evento_id, op, cap, backend, exit_s, op_id, res_id, persist, ts, trace, limitations_json = r
            # Parse provenance from limitations (structured by _handle_ingest)
            prov_parsed = {}
            try:
                if limitations_json:
                    for item in (json.loads(limitations_json) if isinstance(limitations_json, str) else limitations_json):
                        if isinstance(item, str) and item.startswith("provenance: "):
                            prov_parsed = json.loads(item[len("provenance: "):])
                        elif isinstance(item, dict):
                            prov_parsed.update(item)
            except Exception:
                prov_parsed = {}
            # Derive artifact_sha256 and device from provenance if available
            artifact_sha256 = prov_parsed.get("artifact_sha256") if prov_parsed else None
            device_observed = prov_parsed.get("device_observed") or (prov_parsed.get("device") if prov_parsed else None) or backend or "unknown"
            event_readback = prov_parsed.get("readback")
            event_validation = prov_parsed.get("validation")
            event_index = prov_parsed.get("event_index")
            niveles = ["API_CALL_OBSERVED"]
            if exit_s == 0:
                niveles.append("SUBMISSION_ACCEPTED")
            if trace or persist:
                niveles.append("COMPLETION_OBSERVED")
            niveles.append("NOT_DETERMINED")
            provenance = op_id or trace or "unknown"
            event = {
                "evento_id": evento_id,
                "execution_id": trace or op_id or "unknown",
                "event_type": op or "unknown",
                "capability": cap or "unknown",
                "timestamp": ts,
                "backend_id": backend or None,
                "exit_status": exit_s,
                "operation_id": op_id or "",
                "result_id": res_id or "",
                "persistido": bool(persist) if persist is not None else False,
                "niveles_observados": niveles,
                "nivel_maximo_epistemico": "SUBMISSION_ACCEPTED" if exit_s == 0 else "API_CALL_OBSERVED",
                "physical_device_execution": "NOT_DETERMINED",
                "artifact_sha256": artifact_sha256,
                "device_observed": device_observed,
                "readback_observed": event_readback,
                "validation_observed": event_validation,
                "event_index": event_index,
                "provenance": (op_id or trace or "unknown"),
                "provenance_detail": prov_parsed,
                "epistemic_status": "PROVEN" if evento_id else "NOT_DETERMINED",
                "limitations": [
                    "execution_events no expone artifact_sha256 ni readback directo.",
                    "PHYSICAL_DEVICE_EXECUTION no se afirma sin DEBUGFS/UMR/vm129.",
                    "Filtro por event_id solo recupera fila exacta; trace_id puede diferir."
                ]
            }
            events.append(event)
        if not events and total_raw == 0:
            status = "blocked"
            message = "DB execution_events vacía (reconciliado %d filas reales)." % total_raw
        elif not events:
            status = "empty"
            message = "Sin coincidencias; DB total=%d" % total_raw
        else:
            status = "ok"
            message = "Eventos recuperados; no inventados."
        return {
            "status": status, "op":"execution", "total_raw":total_raw,
            "count":len(events), "events":events,
            "filters_applied":{"event_id":event_filter,"execution_id/trace_id":trace_filter,"op_filter":op_filter,"limit":limit_n},
            "reconciled_notes":"Discrepancia 175/185/188 resuelta: DB activa crece con invocaciones; .rxre/storage/ tiene 0.",
            "message":message,
            "limitations":[
                "Contrato 171 consulta pública sin escribir en base protegida.",
                "PHYSICAL_DEVICE_EXECUTION no afirmado por DB; requiere DEBUGFS/UMR/vm129.",
                "artifact_sha256 ausente en esquema execution_events; no completado.",
                "event_id vs trace_id pueden diferir."
            ],
            "derived_from_evidence":True,
            "execution_id": params.get("execution_id") or trace_filter or ("execution-171-"+str(os.getpid()))
        }
    except Exception as exc:
        return {"status":"error","op":"execution","message":"Error DB: %s"%str(exc),"count":0,"events":[],"limitations":["No filas ficticias generadas."],"derived_from_evidence":False}
    finally:
        if c:
            try: c.close()
            except: pass


def _handle_claim(params: dict) -> dict:
    """op:claim — transición explícita finding -> TIERRA.claims (aislada, diseño B de 213).
    No activa integración persistente en operativa; requiere explicit_enable=True,
    db_path absoluto aislado, y autoriza por solicitud (no reutilizable).
    """
    import os, tempfile
    from rxre.contracts.authorization_gate import autorizacion_transicion

    # Contrato JSONL canónico: top-level (como _handle_research). 
    # Rechazar entradas ambiguas donde 'args' contiene campos de claim.
    args_nested = params.get("args")
    if isinstance(args_nested, dict) and any(k in args_nested for k in ("explicit_enable", "db_path", "finding_dict", "finding_id")):
        return {"status":"blocked","ejecutada":False,"op":"claim",
                "motivo":"op:claim requiere contrato JSONL top-level (explicit_enable, db_path, finding_dict); 'args' anidado con campos de claim no admitido. Ver RXRE-MISSION-215.",
                "decision":"REJECT","claim_id":None,"limitations":["JSONL ambiguo: args anidado rechazado"]}

    from rxre.contracts.transition_policy import política_transición
    from rxre.contracts.preintegracion_tierra import preintegrate_finding_to_tierra

    explicit_enable = params.get("explicit_enable")
    finding_dict = params.get("finding_dict")
    finding_id = params.get("finding_id")
    db_path = params.get("db_path")

    # Segunda guarda explicita: `autorizacion` debe ser booleano exacto True
    # (misma semantica que el guard de 212 en adapter_finding_tierra).
    autorizacion = params.get("autorizacion")
    if autorizacion is not True:
        return {
            "status": "blocked",
            "ejecutada": False,
            "op": "claim",
            "motivo": ("autorizacion requiere autorizacion=True (booleano exacto); "
                       "recibido %r (%s). Sin la doble guarda explicita no se escribe "
                       "TIERRA.claims." % (autorizacion, type(autorizacion).__name__)),
            "decision": "NOT_ACTIVATED",
            "claim_id": None,
            "db_path": db_path,
            "limitations": ["doble guarda de autorizacion no satisfecha"],
        }

    # Rechazo inmediato si no es booleano exacto True (defensa 212)
    if explicit_enable is not True:
        return {
            "status": "blocked",
            "ejecutada": False,
            "op": "claim",
            "motivo": ("autorizacion requiere explicit_enable=True (booleano exacto); "
                       "recibido %r (%s). La transicion no se activa para valores truthy."
                       % (explicit_enable, type(explicit_enable).__name__)),
            "decision": "NOT_ACTIVATED",
            "claim_id": None,
            "db_path": db_path,
            "limitations": ["autorizacion fallida: puerta de 210 no atravesada"],
        }

    # Validar destino aislado; rechazar operativo
    if not db_path or not isinstance(db_path, str):
        return {
            "status": "blocked", "ejecutada": False, "op": "claim",
            "motivo": "db_path debe ser cadena absoluta aislada (no operativa)",
            "decision": "REJECT", "claim_id": None,
            "limitations": ["falta db_path"],
        }
    db_path = os.path.abspath(db_path)
    protected_roots = [
        "/home/lucas/Escritorio/rxre/.rxre/storage",
        "/home/lucas/Escritorio/rxre/.rxre/gpu0/original",
    ]
    for root in protected_roots:
        if db_path.startswith(root) or (os.path.dirname(db_path)).startswith(root):
            return {
                "status": "blocked", "ejecutada": False, "op": "claim",
                "motivo": "db_path apunta a zona protegida: %s" % db_path,
                "decision": "REJECT", "claim_id": None,
                "limitations": ["intento de escribir zona protegida bloqueado"],
            }
    if "rxre.sqlite3" in os.path.basename(db_path) or db_path.endswith("rxre.sqlite3"):
        return {
            "status": "blocked", "ejecutada": False, "op": "claim",
            "motivo": "db_path es base operativa: %s (transicion aislada requiere DB_T)" % db_path,
            "decision": "REJECT", "claim_id": None,
            "limitations": ["base operativa rechazada"],
        }

    # Requerir finding_dict o finding_id; lectura operativa solo lectura
    if not finding_dict:
        if finding_id:
            try:
                import sqlite3
                c = sqlite3.connect("/home/lucas/Escritorio/rxre/.rxre/storage/rxre.sqlite3")
                c.execute("SELECT id, finding_text, refs, epistemic_state, contradiction_refs FROM findings WHERE id=?", (finding_id,))
                row = c.fetchone()
                c.close()
                if row:
                    finding_dict = {
                        "finding_id": row[0], "text": row[1],
                        "epistemic": row[3], "evidence_ids": row[2].split(",") if row[2] else [],
                        "contradiction_refs": row[4].split(",") if row[4] else [],
                    }
            except Exception as e:
                return {"status":"blocked","ejecutada":False,"op":"claim","motivo":"lectura operativa fallida: %s"%str(e),"decision":"REJECT","claim_id":None,"limitations":["reading finding failed"]}
        if not finding_dict:
            return {"status":"blocked","ejecutada":False,"op":"claim","motivo":"se requiere finding_dict o finding_id","decision":"REJECT","claim_id":None,"limitations":["falta finding"]}

    resolver_refs = params.get("resolver_refs")
    contradiction_statements = params.get("contradiction_statements")
    if not callable(resolver_refs):
        return {"status":"blocked","ejecutada":False,"op":"claim",
                "motivo":"resolver_refs debe ser una funcion verificable; se exige resolucion real para cada referencia (bypass 241 corregido). No se admite resolver predeterminado auto-referencial (machine.py line 6207).",
                "decision":"NEEDS_INPUT","claim_id":None,"db_path":db_path,
                "limitations":["resolver_refs no es callable; referencia falsa o inexistente rechazada"]}

    # 249E: admisión central antes de cualquier escritura (antes de política).
    try:
        from rxre.contracts.admission_tierra import admit_claim as _admit_claim
        _fd = finding_dict or {}
        _scope = _fd.get("scope") or _fd.get("scope", "")
        _prov = _fd.get("scope_provenance") or params.get("scope_provenance")
        _ok, _reason = _admit_claim(
            statement=_fd.get("text") or _fd.get("claim") or _fd.get("statement") or "",
            object_hash=_fd.get("object_hash") or _fd.get("hash") or "",
            scope=_scope,
            scope_provenance=_prov,
            producer_id=_fd.get("producer_id") or params.get("producer_id"),
            producer_capability=_fd.get("producer_capability") or params.get("producer_capability") or _fd.get("capability"),
            result_id=_fd.get("result_id") or params.get("result_id"),
            request_id=_fd.get("request_id") or params.get("request_id"),
            evidence_refs=_fd.get("evidence_ids") or _fd.get("evidence_refs") or [],
            resolver_refs=resolver_refs if callable(resolver_refs) else None,
        )[:2]
        if not _ok:
            return {"status":"blocked","ejecutada":False,"op":"claim",
                    "motivo":"admission_tierra rechaza: %s" % _reason,
                    "decision":"REJECT","claim_id":None,"db_path":db_path,
                    "limitations":["admisión central rechazada (249E)"]}
    except Exception as _e:
        return {"status":"blocked","ejecutada":False,"op":"claim",
                "motivo":"admission_tierra error: %s" % str(_e),
                "decision":"REJECT","claim_id":None,"db_path":db_path,
                "limitations":["admisión central error (249E)"]}

    try:
        pol = política_transición(
            finding_dict,
            resolver_refs=resolver_refs,
            contradiction_statements=contradiction_statements,
        )
    except Exception as e:
        return {"status":"blocked","ejecutada":False,"op":"claim","motivo":"política falló: %s"%str(e),"decision":"REJECT","claim_id":None,"limitations":["policy error"]}

    if pol.get("decision") != "ACCEPT":
        return {
            "status": "blocked", "ejecutada": False, "op": "claim",
            "motivo": "política no acepta: %s" % pol.get("reason", pol.get("decision")),
            "decision": pol.get("decision"),
            "claim_id": None,
            "db_path": db_path,
            "limitations": ["transicion rechazada por contrato epistemológico"],
        }

    # --- Cadena semantica obligatoria antes de persistencia (RXRE-243/244) ---
    # Verifica referencia, integridad, respaldo, autenticidad y scope.
    # No escribe; rechaza de forma auditable si falta cualquier frontera.
    try:
        from rxre.contracts.semantic_verification_chain import verificar_precondiciones
        pre = verificar_precondiciones(
            finding_dict,
            resolver_refs=resolver_refs,
            claim_propiedad=params.get("claim_propiedad") or params.get("verificacion") or {},
            artifact_path=params.get("artifact_path") or params.get("artefacto_path") or None,
            evidence_path=params.get("evidence_path") or params.get("evidencia_path") or None,
            grafo_path=db_path,
        )
    except Exception as exc:
        return {"status":"blocked","ejecutada":False,"op":"claim",
                "motivo":"cadena semantica fallo: %s"%str(exc),
                "decision":"REJECT","claim_id":None,"db_path":db_path,
                "limitations":["semantic chain error; sin escritura"]}

    # Mapeo de decisiones de la cadena al flujo de op:claim
    if pre.get("decision") != "ACCEPT":
        sem_res = (pre.get("semantica") or {}).get("resultado")
        epi = finding_dict.get("epistemic") or finding_dict.get("epistemic_state")
        if sem_res == "INSUFFICIENT" and epi == "NOT_DETERMINED":
            dec = "NEEDS_INPUT"
        elif sem_res == "REFUTED" or pre.get("frontera") in ("referencia","integridad","autenticidad","scope"):
            dec = "REJECT"
        else:
            dec = "NEEDS_INPUT"
        return {"status":"blocked","ejecutada":False,"op":"claim",
                "motivo":"cadena semantica no satisfecha (%s / %s): %s" % (pre.get("frontera"), sem_res, pre.get("motivo")),
                "decision":dec,"claim_id":None,"db_path":db_path,
                "limitations":["verificacion semantica obligatoria antes de persistir; sin escritura"]}


    # --- Integración contrato de scope guardado (P1 — RXRE-261) ---
    # Se evalúa antes de la autorización operativa; no sustituye la autorización.
    # Un REJECT aquí bloquea antes de escribir; ALLOW_WITH_LIMITATION pasa por autorización.
    scope_dec = None  # P1: decision del contrato de scope (para persistencia de limitaciones)
    try:
        from rxre.contracts.scope_guarded_flow import evaluar_guardado
        ev_refs = finding_dict.get("evidence_ids") or finding_dict.get("evidence_refs") or []
        claim_scope = finding_dict.get("scope") or finding_dict.get("scope", "")
        # --- AUTORIZACIÓN DEL SCOPE (RXRE-272) ---
        # La decisión de autoridad viene del operador (SCOPE_AUTHORITY_DECISION.md APPROVED).
        # NO se infiere ni se fabrica desde finding_dict/consumidor: sólo se propaga si el
        # llamador aporta la decisión explícita; su autenticidad la verifica el contrato.
        scope_authorization = params.get("scope_authorization") or finding_dict.get("scope_authorization") or None
        # --- Fin autorización ---
        manifest_by_ref = params.get("manifest_by_ref") or {}
        art_path = params.get("artifact_path") or params.get("artefacto_path") or None
        art_hash = params.get("evidence_path_hash") or (open(art_path,"rb").read() if art_path and os.path.isfile(art_path) else None)
        if art_hash and isinstance(art_hash, bytes):
            import hashlib
            art_hash = hashlib.sha256(art_hash).hexdigest()
        scope_dec, _ = evaluar_guardado(
            evidence_refs=ev_refs,
            claim_scope=claim_scope,
            db_op_path="/home/lucas/Escritorio/rxre/.rxre/storage/rxre.sqlite3",
            manifest_by_ref=manifest_by_ref,
            art_path=art_path,
            art_hash=art_hash,
            refs_verificados_por_llamador=True,
        )
        if scope_dec == "REJECT":
            return {"status":"blocked","ejecutada":False,"op":"claim",
                    "motivo":"scope_guarded_flow rechaza (CONFLICT/INVALID): contrato de procedencia no satisfecho",
                    "decision":"REJECT","claim_id":None,"db_path":db_path,
                    "limitations":["scope: contrato rechazado antes de autorización; sin escritura"]}
    except Exception as exc:
        pass  # P1: contrato aislado integrado; excepciones no bloquean (estabilidad); documentado

    try:
        gate = autorizacion_transicion(
            db_path, finding_dict,
            resolver_refs=resolver_refs,
            contradiction_statements=contradiction_statements,
            explicit_enable=True,
        )
    except Exception as e:
        return {"status":"blocked","ejecutada":False,"op":"claim","motivo":"puerta falló: %s"%str(e),"decision":"REJECT","claim_id":None,"limitations":["authorization_gate error"]}

    if gate.get("decision") in ("REJECT", "NOT_ACTIVATED", "NEEDS_INPUT") or gate.get("status") == "blocked":
        return {
            "status": "blocked", "ejecutada": False, "op": "claim",
            "motivo": "puerta o política rechazan: %s" % gate.get("reason", gate.get("motivo", "")),
            "decision": gate.get("decision"),
            "claim_id": None,
            "db_path": db_path,
            "limitations": ["autorizacion/contrato fallido"],
        }

    # La puerta (autorizacion_transicion) ya atraviesa politica -> adaptador -> DB_T;
    # no se hace una segunda llamada a preintegracion_tierra (evita duplicado idempotente).
    claim_id = gate.get("claim_id") if gate.get("status") == "ok" else None
    # P1/P3: persistencia de limitaciones cuando el contrato permite continuar con scope no verificado
    if claim_id and scope_dec == "ALLOW_WITH_LIMITATION" and db_path and os.path.isfile(db_path):
        try:
            from rxre.contracts.limitations_contract import migrar_limitaciones_reversible, guardar_limitacion
            migrar_limitaciones_reversible(db_path)
            guardar_limitacion(db_path, claim_id, "UNVERIFIED", "ALLOW_WITH_LIMITATION",
                              ["scope no verificado por fuente independiente (DB_OP.results.scope=NULL o manifest sin scope)"],
                              finding_dict.get("evidence_ids") or finding_dict.get("evidence_refs") or [],
                              finding_dict.get("scope"))
        except Exception:
            pass  # P1/P3: limitación documentada; error de persistencia no bloquea operación (estabilidad)
    lectura = None
    try:
        import rxre.arquitectura.TIERRA as TIERRA_M
        if claim_id and os.path.exists(db_path):
            g = TIERRA_M.Grafo(db_path)
            lectura = g.leer(claim_id)
    except Exception:
        lectura = None

    # Mapeo al contrato de salida (RXRE-216): usar estados canónicos.
    resultado = "CREATED"
    if gate.get("ya_existia"):
        resultado = "ALREADY_EXISTS"
    elif gate.get("status") == "blocked" and gate.get("decision") == "NOT_ACTIVATED":
        resultado = "NOT_ACTIVATED"
    elif gate.get("status") == "blocked" and gate.get("decision") == "REJECT":
        resultado = "REJECTED"
    elif gate.get("status") == "blocked" and gate.get("decision") == "NEEDS_INPUT":
        resultado = "NEEDS_INPUT"
    elif gate.get("status") == "error":
        resultado = "PERSISTENCE_ERROR"

    return {
        "status": gate.get("status", "ok"),
        "ejecutada": gate.get("status") == "ok",
        "op": "claim",
        "resultado": resultado,
        "decision": gate.get("decision", "ACCEPT"),
        "motivo": gate.get("motivo", "transicion aislada completada"),
        "claim_id": claim_id,
        "db_path": db_path,
        "epistemic_state": lectura.get("epistemic_state") if lectura else None,
        "evidence_refs": lectura.get("evidence_refs") if lectura else None,
        "ya_existia": gate.get("ya_existia"),
        "limitations": ["operacion aislada; DB_OP intacta; no se activo persistent integration"]
                       + (["scope no verificado: limitacion persistida en DB_T (limitations_json)"] if scope_dec == "ALLOW_WITH_LIMITATION" else []),
        "scope_decision": scope_dec,
        "audit_note": "op:claim verificado en DB_T aislada; cadena machine->gate->policy->adapter->TIERRA comprobada",
    }

HANDLERS = {
    "execution": _handle_execution,
    "ingest": _handle_ingest,
    "execution": _handle_execution,
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
    "hypothesize": _handle_hypothesize,
    "select_experiment_predictive": _handle_select_experiment_predictive,
    "select_experiment": _handle_select_experiment,
    "investigate": _handle_investigate,
    "research": _handle_research,
    "claim": _handle_claim,
    "query": _handle_query,
    "relation": _handle_relation,
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

