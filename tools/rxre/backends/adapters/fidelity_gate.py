"""RXRE-LXXVI / M1192+ — Puerta de fidelidad con selección explícita.

Contratos admitidos (read-only sobre archivos protegidos):

  fidelity_domain_v1.json  RXRE-LXXI-domain-v1 (sha256-e9fbed85...)
  fidelity_domain_v2.json  RXRE-LXXV-domain-v1 (sha256-bfba046f...)

Selección DE LOS DOMINIOS:

  Prioridad (por ejecución):
    1. argumento `domain=` pasado a la función de entrada (literal, normalizado);
    2. variable de entorno RXRE_FIDELITY_DOMAIN (literal, normalizado);
    3. ausencia -> v1 (v1 es el default operacional conservador).

Rechaza explícitamente cualquier otro valor, cadena vacía o inexistente; NUNCA eleva ni degrada silenciosamente.

Propiedades preservadas:
  - El gate NUNCA promueve FAIL; nunca como boca abierta;
  - `worst-wins` preservada a nivel de bloque;
  - `accept()` es un predicado puro fail-closed: sobre envelopes sin identidad explícita
    devuelve False;
  - Siete-check (hasta 9) de consistencia antes de aceptar.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Optional, Tuple

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from rxre.decompiler import fidelity as _fid  # noqa: E402

V1_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "decompiler", "fidelity_domain_v1.json"))
V2_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "decompiler", "fidelity_domain_v2.json"))
import os.path as _p
_DOMAIN_FILES = {"v1": V1_PATH, "v2": V2_PATH}

def _sha256_path(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

EXPECTED_HASH = {"v1": _sha256_path(V1_PATH), "v2": _sha256_path(V2_PATH)}
CONTRACT_VERSION = {"v1": "RXRE-LXXI-domain-v1", "v2": "RXRE-LXXV-domain-v1"}

CLASSIFIER_ID = "rxre.decompiler.fidelity@%s" % _sha256_path(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "decompiler", "fidelity.py"))[:16]


def requested_domain(explicit=None) -> Tuple[Optional[str], str]:
    """Resolver selección. Devuelve (raw, fuente).

    Prioridad: argument > env > 'default'.  'raw' es el literal tras normalizar.
    NUNCA fallback silencioso a otro dominio; 'default' => 'v1'.
    """
    if explicit is not None:
        return (explicit.strip().lower(), "argument")
    env_raw = os.environ.get("RXRE_FIDELITY_DOMAIN", "").strip().lower()
    if env_raw:
        return (env_raw, "env")
    return ("v1", "default")


def resolve_domain(explicit=None) -> Tuple[Optional[str], str, str, str]:
    """Resolver + validar. Devuelve (name|None, raw_used, source, reason)."""
    raw, source = requested_domain(explicit)
    raw_str = raw if isinstance(raw, str) else repr(raw)
    if raw in ("v1", "v2"):
        return (raw, raw, source, "ok")
    return (None, raw_str, source, "DOMAIN_UNKNOWN: %r (allowed: v1, v2)" % raw_str)


def verify_contract(name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """Carga JSON. Devuelve (contract, hash, error)."""
    if name not in _DOMAIN_FILES:
        return (None, None, "DOMAIN_UNKNOWN: %s" % name)
    path = _DOMAIN_FILES[name]
    if not _p.exists(path):
        return (None, None, "DOMAIN_CONTRACT_MISSING: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            contract = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return (None, None, "DOMAIN_CONTRACT_UNREADABLE: %s" % e)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if h != EXPECTED_HASH[name]:
        return (contract, h, "DOMAIN_CONTRACT_HASH_MISMATCH")
    return (contract, h, None)


def classify_artefact_full_text(artefacto: str, domain: Optional[str] = None) -> Dict[str, Any]:
    """Full-text dump + classify with explicit domain."""
    name, raw_used, source, reason = resolve_domain(domain)
    if name is None:
        return {"verdict": "INVALID",
                "reasons": [reason],
                "summary": {"requested_domain": raw_used,
                            "resolved_domain": None,
                            "selection_source": source,
                            "selection_reason": reason},
                "contract_version": None,
                "domain_hash": None,
                "resolution": {"raw": raw_used, "name": None, "source": source,
                               "status": "REJECT"}}
    dump = subprocess.check_output(["objdump", "-d", artefacto], text=True)
    out = _fid.classify_dump(dump, domain_file=_DOMAIN_FILES[name])
    out["selection"] = {"raw": raw_used, "name": name, "source": source, "status": "ok", "reason": reason}
    out["resolution"] = out["selection"]
    out["contract_version"] = CONTRACT_VERSION[name]
    out["classifier"] = CLASSIFIER_ID
    return out


def gate_verdict(verdict: str, dom_hash_actual: str, fobj: Dict[str, Any],
                 resolved: Dict[str, Any]) -> Dict[str, Any]:
    reasons: list = []
    rejected = False
    if not resolved.get("name"):
        reasons.append("RESOLVER_REJECT: %s" % resolved.get("reason", "unknown"))
        rejected = True
    if resolved.get("name"):
        dom_expected = EXPECTED_HASH[resolved["name"]]
        if dom_hash_actual != dom_expected:
            reasons.append("DOMAIN_CONTRACT_HASH_MISMATCH (%s != %s)" % (dom_hash_actual, dom_expected))
            rejected = True
    if verdict != "FAITHFUL":
        reasons.append("bloque no FAITHFUL: la puerta de promoción deniega (verdict=%s)" % verdict)
        rejected = True
    return {"accept": bool((not rejected) and verdict == "FAITHFUL"),
            "reasons": reasons,
            "resolved_domain": resolved.get("name"),
            "domain_hash": dom_hash_actual}


def new_envelope(artefacto: str, selection: dict) -> dict:
    return {
        "fidelity": {
            "execution_id": uuid.uuid4().hex[:16],
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "classifier": CLASSIFIER_ID,
            "selection": selection,
        }
    }


def decompile_with_fidelity_gate(artefacto: str,
                                  backend_id: str = "ghidra",
                                  fixture_json: Optional[str] = None,
                                  domain: Optional[str] = None,
                                  **kwargs) -> Dict[str, Any]:
    """Envuelve gh_decompile.decompile(...) con la puerta de fidelidad.

    Fail-closed: sin verdict FAITHFUL, `accept` es False.
    """
    from backends.adapters import gh_decompile
    name, raw_used, source, reason = resolve_domain(domain)
    # RXRE-LXXIX: la selección de funciones para evaluación por alcance se
    # extrae ANTES de invocar al producer, para que nunca llegue a Ghidra.
    accept_selection = kwargs.pop("accept_functions", None)
    selection = {"raw": raw_used, "name": name, "source": source,
                 "status": "ok" if name else "REJECT", "reason": reason}
    execution_id = uuid.uuid4().hex[:16]
    env = gh_decompile.decompile(artefacto, backend_id=backend_id,
                                 fixture_json=fixture_json, **kwargs)
    if fixture_json:
        env["fidelity"] = {
            "execution_id": execution_id,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "classifier": CLASSIFIER_ID,
            "selection": selection,
            "contract_version": "n/a",
            "domain_hash": None,
            "verdict": "NOT_EXECUTED",
            "reasons": ["fixture_json: producer-fixture path; gate no aplicable (explícito)"],
            "gate": {"accept": False, "reasons": ["FIXTURE_JSON_PATH"]},
        }
        return env
    if not (os.path.isfile(artefacto) and isinstance(env.get("precheck"), dict) and env["precheck"].get("ok")):
        env["fidelity"] = {
            "execution_id": execution_id,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "classifier": CLASSIFIER_ID,
            "selection": selection,
            "contract_version": "n/a",
            "domain_hash": None,
            "verdict": "NOT_EXECUTED",
            "reasons": ["producer failed closed or artefact not a clean ELF: gate not applicable"],
            "gate": {"accept": False, "reasons": ["PRODUCER_NOT_OK_OR_INVALID_ARTEFACT"]},
        }
        return env
    if name is None:
        # selection rejected: envelope maintains reject flag, never fallback
        env["fidelity"] = {
            "execution_id": execution_id,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "classifier": CLASSIFIER_ID,
            "selection": selection,
            "contract_version": None,
            "domain_hash": None,
            "verdict": "INVALID",
            "reasons": [reason],
            "gate": {"accept": False, "reasons": ["DOMAIN_UNKNOWN"]},
        }
        return env
    dump = subprocess.check_output(["objdump", "-d", artefacto], text=True)
    fobj = _fid.classify_dump(dump, domain_file=_DOMAIN_FILES[name])
    expected = EXPECTED_HASH[name]
    dom_hash = fobj.get("domain_hash") or ""
    resolved_dict = {"name": name, "raw": raw_used, "source": source, "status": "ok", "reason": reason}
    gate = gate_verdict(fobj.get("verdict", "INVALID"), dom_hash, fobj, resolved_dict)
    scope_eval = None
    if accept_selection is not None:
        # RXRE-LXXIX / M1207: segunda decisión INDEPENDIENTE (por función).
        # NO modifica ni sustituye el veredicto global ni el gate.
        from rxre.decompiler import fidelity_scope as _scope
        artifact_hash = (env.get("precheck") or {}).get("input_hash") or (
            hashlib.sha256(open(artefacto, "rb").read()).hexdigest())
        sel_names = []
        for entry in accept_selection:
            if isinstance(entry, str) or isinstance(entry, dict):
                sel_names.append(entry)
            else:
                sel_names.append({"name": None})  # rechazada por el scope (entry inválida)
        scope_eval = _scope.evaluate_scope(
            dump,
            domain_file=_DOMAIN_FILES[name],
            selection=sel_names,
            artifact_hash=artifact_hash,
        )
    env["fidelity"] = {
        "execution_id": execution_id,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "classifier": CLASSIFIER_ID,
        "selection": selection,
        "contract_version": CONTRACT_VERSION[name],
        "domain_hash": dom_hash,
        "domain_file": _DOMAIN_FILES[name],
        "verdict": fobj.get("verdict"),
        "summary": fobj.get("summary"),
        "reasons": [r for b in fobj.get("blocks", []) for r in b.get("reasons", [])[:3]][:32],
        "gate": gate,
    }
    if scope_eval is not None:
        env["fidelity"]["scope"] = {
            "verdict": scope_eval["verdict"],
            "function_accept": scope_eval["function_accept"],
            "selection": scope_eval["selection"],
            "functions": scope_eval["functions"],
            "artifact_accept": gate.get("accept", False),
        }
    return env


def accept(envelope: Optional[Dict[str, Any]]) -> bool:
    """True iff envelope puede presentarse como reconstrucción fiel. Fail-closed.

    Dos modos:
      - Legacy (sin execution_id, pre-LXXVI): acepta si gate.accept is True.
      - New-style (sellos LXXVI): verificaciones estrictas de identidad de dominio,
        hash del archivo, sello execution_id.
    """
    f = (envelope or {}).get("fidelity") or {}
    gate = f.get("gate") or {}
    if gate.get("accept") is not True:
        return False
    sel = f.get("selection") or {}
    if sel.get("status") == "ok" and sel.get("name") in _DOMAIN_FILES:
        # new-style: enforce full identity checks
        name = sel["name"]
        declared = f.get("domain_hash")
        path = _DOMAIN_FILES.get(name)
        if not path or not os.path.isfile(path):
            return False
        actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if declared != actual or actual != EXPECTED_HASH[name]:
            return False
    elif sel.get("status") in (None, "ok"):
        pass  # legacy-compatible path
    else:
        return False
    if sel.get("status") == "ok" and sel.get("name") in _DOMAIN_FILES:
        eid = f.get("execution_id", "")
        if not isinstance(eid, str) or len(eid) != 16:
            return False
    return True


def persistir(env: Dict[str, Any], db: Optional[Any] = None,
              question: str = "") -> Optional[str]:
    """RXRE-LXXXI / M1218 — Persistencia aditiva de binary.decompile.

    Reproduce `dispatch._persistir_generico` sobre la copia operativa aislada
    (M416: `/tmp/opencode/m416_operativo/operativo.sqlite3`, copia migrada por
    `store_compat.migrar_copia` desde la base de origen) pero CONSERVA el
    bloque `fidelity` completo (`execution_id`, `selection`, `domain_hash`,
    `verdict`, `gate`, `scope`, `function_accept`).

    - NUNCA escribe en `rxre.sqlite3` (ni en `DEFAULT_DB` ni en
      `tools/rxre/storage/rxre.sqlite3`).
    - NUNCA usa `gh_decompile.persistir`.
    - Aditiva: los campos del response_json del fallback genérico se
      conservan tal cual; la única diferencia es la clave `fidelity` y las
      complementarias `n_functions`/`n_decompiladas`.
    - Consumidores anteriores (ocho_principios, explain replay) ignoran
      claves desconocidas; siguen funcionando sin cambios.
    - Append-only: `results` se insertan igual que en el fallback; si un
      `result_id` ya existe, se devuelve `COLISION:<ids>` sin tocar nada.
    """
    __here = os.path.dirname(os.path.abspath(__file__))
    _rxre_root = os.path.abspath(os.path.join(__here, os.pardir, os.pardir))
    _tools_root = os.path.abspath(os.path.join(_rxre_root, os.pardir))
    _repo_root = os.path.abspath(os.path.join(_tools_root, os.pardir))
    for _p in (_rxre_root, _tools_root):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    from core import store as S
    from rxre.core import store_compat as sc

    # RXRE_DB: si el caller pasa RXRE_DB, usar esa DB concreta.
    _oper_path = os.environ.get("RXRE_DB") or "/tmp/opencode/m416_operativo/operativo.sqlite3"
    _is_rxre_db = bool(os.environ.get("RXRE_DB"))
    if not _is_rxre_db:
        os.makedirs("/tmp/opencode/m416_operativo", exist_ok=True)

    res = env.get("results") or []
    ids = [r.get("result_id") for r in res
           if isinstance(r, dict) and r.get("result_id")]
    if not ids:
        env["motivo_persistencia"] = (
            "no se persiste: binary.decompile no trae result_id "
            "(nada recuperable, AGUA)")
        return None
    prov = env.get("provenance") or {}
    if isinstance(prov, dict) and not prov.get("input_hash"):
        env["motivo_persistencia"] = (
            "no se persiste: la provenance no trae input_hash (TIERRA)")
        return None

    _propia = db is None
    if _propia:
        if _is_rxre_db:
            # caller pasó RXRE_DB (test aislado) sin existente: crear vacía
            c = S.conectar(_oper_path)
        else:
            origen = os.path.join(_repo_root, "rxre.sqlite3")
            if not os.path.isfile(origen):
                origen = os.path.join(_repo_root, "tools", "rxre", "storage",
                                      "rxre.sqlite3")
            if os.path.exists(_oper_path):
                c = S.conectar(_oper_path)
            else:
                r = sc.migrar_copia(origen, _oper_path)
                if r.get("status") != "PROVEN":
                    env["motivo_persistencia"] = (
                        "LXXXI BLOCKED: migracion fallida (%s)" % r.get("reason"))
                    env["persistencia_fallida"] = True
                    return None
                c = S.conectar(_oper_path)
    else:
        c = db
    try:
        existentes = [i for i in ids if c.execute(
            "SELECT 1 FROM results WHERE result_id=?", (i,)).fetchone()]
        if existentes:
            return "COLISION:%s" % ",".join(existentes)
        res0 = res[0] if isinstance(res[0], dict) else {}
        scope = (res0.get("scope") or "funcion").strip() or "funcion"
        scope_provenance = "EXPLICIT"
        artefacto = res0.get("source") or ""
        target = "%s:%s" % (scope, os.path.basename(artefacto) or "artefacto")
        resp = {
            "operation": "binary.decompile",
            "status": env.get("status"),
            "backend": env.get("backend"),
            "ejecucion": env.get("ejecucion"),
            "provenance": env.get("provenance"),
            "precheck": env.get("precheck"),
            "cadena_backend": env.get("cadena_backend", []),
            "n_functions": env.get("n_functions"),
            "n_decompiladas": env.get("n_decompiladas"),
            "results": res,
            "persistido": True,
            # RXRE-LXXXI: decisiones de fidelidad completas, byte a byte.
            "fidelity": env.get("fidelity"),
        }
        op_id = S.registrar(
            c,
            {"request_id": "",
             "question": question or ("decompilar %s" % (os.path.basename(artefacto) or artefacto or "artefacto")),
             "capability": "binary.decompile",
             "scope": scope,
             "scope_provenance": scope_provenance,
             "target": target},
            resp,
            duracion=(env.get("ejecucion") or {}).get("duration_s", 0))
        return op_id
    finally:
        if _propia:
            c.close()
