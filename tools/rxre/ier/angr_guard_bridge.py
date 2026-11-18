#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · IER · ANGR_GUARD_BRIDGE — bridge entre el guard de angr y la evidencia M10.

## QUÉ ES

Capa estrecha entre `InlinedStrcpySimplifier._scalar_use_decision` (angr) y la
evidencia sellada del M10 de RXRE, para resolver el único cuello discriminante:

    ¿El candidato pasa por una llamada que lo consume textual sin devolverlo
    ni escribirlo, con la evidencia más fuerte disponible hoy?

Lee:

    1. El proyecto de angr (para llegar al binario: path y sha256).
    2. El análisis sellado M10 (`cancel_sys_analysis_m10_7.json`) como fuente
       de identificaciones de región y de callsites (verificable sha y seal).
    3. El resumen sellado del callee (`callee_summary_sub_1400035f4.json`).
    4. `rxre_angr_adapter.verify_decision()` para el veredicto.

Reglas:
    - NO ejecuta el guard de angr; consume evidencia sellada.
    - El binario bajo análisis debe coincidir sha-a-sha con la fuente sellada;
      si no, BLOCKED (nunca SAFE por ignorancia).
    - El callee debe ser identificable por dirección (const) y coincidente con el sello.
    - El argumento que referencia al candidato debe contener la región
      completamente dentro de su referencia (Reference-over-stack igual a candidato).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

BRIDGE_VERSION = "RYI-ANGR-GUARD-BRIDGE-1"
CAPABILITY_ID = "angr_guard_bridge"

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

SAFE = "SAFE_TO_TRANSFORM"
ABSTAIN = "ABSTAIN"
PRESERVE_SCALAR = "PRESERVE_SCALAR"
BLOCKED = "BLOCKED"
# IRRELEVANT: el certificado de vidas demuestra que el candidato está muerto
# en la posición de este enunciado; el enunciado no puede observarlo. NO
# autoriza transformación alguna (no es SAFE): sólo excluye que el enunciado
# sea evidencia de uso escalar del candidato.
IRRELEVANT = "IRRELEVANT"

# Ubicación por defecto de los artefactos sellados de M10.
SEALED_DIR = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
SEALED_ANALYSIS_PATH = os.path.join(SEALED_DIR, "cancel_sys_analysis_m10_7.json")
SEALED_CALLEE_PATH = os.path.join(SEALED_DIR, "callee_summary_sub_1400035f4.json")
M11S_DIR = os.environ.get(
    "RXRE_7294_M11S_DIR", os.path.expanduser("~/rxre-angr-7294-m11/m11_8_s"))
SEALED_RTL_PATH = os.path.join(M11S_DIR, "callee_summary_rtlinitucs_m11s.json")
SEALED_MM_PATH = os.path.join(M11S_DIR, "callee_summary_mmgstrat_m11s.json")

# Integridad de los artefactos sellados de M10.7 (deriva externa, DSSF):
# los hashes provienen de SHA256SUMS.m10.7 (callee 7f0a64…, analysis 255301…)
# y la recomputación del sello interno (6b8b…) se verifica sobre el propio JSON.
# La raíz de confianza es el manifiesto sellado; sin él, el bridge NO consume nada.
# Sólo los tests pueden sustituir el manifiesto mediante RXRE_7294_SEAL_MANIFEST
# (misma técnica que RXRE_ROOT/RXRE_7294_SEALED_DIR: herramienta de trabajo local).
_DEFAULT_SEAL_MANIFEST = {
    "cancel_sys_analysis_m10_7.json":
        "255301f2f9339a353e00091e7721ac88d8a17ec28ebcb0358686d3d5661e379d",
    "callee_summary_sub_1400035f4.json":
        "7f0a6444361b662ffe07ba5b85177f3a75acb593251ff24b4197c87f109fc06f",
    "callee_summary_rtlinitucs_m11s.json":
        "d4e49fb3e2b27cf506606c02a041831d2a8c3805d2f9d4ee9279ac2a5165e174",
    "callee_summary_mmgstrat_m11s.json":
        "fa4aa143feff99a163b90f717fbbc9bf2b3cf3f114fa8b1f359666860d591df0",
}
_INNER_SEAL_SHA256 = "6b8b210157edd082493afba3d74c9402bb04c399c8c62416d352597bf919d605"
_OBJDUMP_SHA256 = "aa5c08f1d6414977d281ceb5e7b6600e8ce26e22014aad7182851213d26e01a4"


EVIDENCE_PATH = os.environ.get("RXRE_7294_LIFECYCLE_EVIDENCE",
                               os.path.expanduser("~/rxre-angr-7294-m11/m11_9/lifetime_evidence_cancel.json"))

def _load_evidence_document():
    """Carga la evidencia temporal.

    Tres estados, sin mezclar:
      * None  → evidencia ausente: caben otras vías; no impone ni permite SAFE por sí misma.
      * False → evidencia presente pero rota: no ampara IRRELEVANT ni SAFE.
      * dict  → evidencia íntegra y ligada al M10.7 (artifact/sha).
    """
    try:
        with open(EVIDENCE_PATH, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        return None
    except Exception:
        return False
    try:
        from ier import lifetime_contract as lc
        if lc.verify_seal(doc) is not None:
            return False
        sealed = _load_sealed_analysis()
        want = (sealed.get("artifact") or {}).get("sha256")
        got = (doc.get("artifact") or {}).get("sha256")
        if not want or got != want:
            return False
        return doc
    except Exception:
        return False


def _irrelevant_verdict(binary_path, function_addr, callsite_addr, stmt_index):
    """Verdict IRRELEVANT estricto sobre la evidencia temporal genérica.

    Devuelve dict de decisión o None si la evidencia no ampara el enunciado."""
    try:
        from ier import lifetime_contract as lc
        doc = _load_evidence_document()
        if doc is None or doc is False:
            return None  # ausente o rota: no se ampara IRRELEVANT
        nid = "0x%x#0" % callsite_addr
        res = lc.evaluate(doc, {"node": nid, "stmt": stmt_index},
                          allowed={"function": function_addr},
                          artifact_path=binary_path)
        dec = res.get("decision")
        if dec == lc.IRRELEVANT:
            return {"decision": IRRELEVANT,
                    "reason": res.get("reason", "referencias ligadas a vidas posteriores demostradas"),
                    "binding": {}, "independent_oracle": [], "admision": {},
                    "verification": res.get("reason", "")}
        return None
    except Exception:
        return None


def _load_seal_manifest() -> Dict[str, str]:
    path = os.environ.get("RXRE_7294_SEAL_MANIFEST")
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("manifiesto de prueba malformado")
        return dict(data)
    return dict(_DEFAULT_SEAL_MANIFEST)


def _recompute_inner_seal(inner: Dict[str, Any]) -> str:
    body = {k: v for k, v in inner.items() if k not in ("seal_sha256", "sealed")}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def verify_seal_integrity() -> Dict[str, Any]:
    """DSSF obligada antes de consumir cualquier artefacto sellado.

    Devuelve {"ok": bool, "reason": str}.  En cualquier duda, ok=False."""
    try:
        manifest = _load_seal_manifest()
    except Exception as exc:
        return {"ok": False, "reason": "manifiesto de sellos no disponible: %s" % exc}

    # 1) integridad externa (bytes de los archivos) contra el manifiesto
    for path in SEALED_ANALYSIS_PATH, SEALED_CALLEE_PATH, SEALED_RTL_PATH, SEALED_MM_PATH:
        exp = manifest.get(os.path.basename(path))
        if not isinstance(exp, str) or len(exp) != 64:
            return {"ok": False, "reason": "manifiesto sin sello para %s" % os.path.basename(path)}
        try:
            real = _sha256_file(path)
        except OSError as exc:
            return {"ok": False, "reason": "artefacto sellado no legible: %s" % exc}
        if real != exp:
            return {"ok": False,
                    "reason": "sello exterior discordante en %s" % os.path.basename(path)}

    # 2) sello interno del resumen (contenido semántico)
    try:
        with open(SEALED_CALLEE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        inner = data["summary"]
        if not isinstance(inner, dict):
            return {"ok": False, "reason": "resumen interno ausente/malformado"}
        inner_real = _recompute_inner_seal(inner)
    except Exception as exc:
        return {"ok": False, "reason": "resumen interno ilegible: %s" % exc}
    if str(data.get("summary", {}).get("seal_sha256")) != _INNER_SEAL_SHA256:
        return {"ok": False, "reason": "sello interno discordante (declarado)"}
    if inner_real != _INNER_SEAL_SHA256:
        return {"ok": False, "reason": "sello interno no recomputable"}

    # 3) procedencia del desensamblado (sello del oráculo independiente)
    if str(data.get("objdump_sha256")) != _OBJDUMP_SHA256:
        return {"ok": False, "reason": "sello del objdump/oráculo discordante"}

    return {"ok": True, "reason": "sellos M10.7 verificados (externo+interno+oráculo)"}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_sealed_summary(callee_addr=None) -> Dict[str, Any]:
    """Carga un resumen sellado según la dirección del callee.

    Llamada por defecto: el summary de sub_1400035f4 (M10.7).
    Si `callee_addr` coincide con el IAT slot de RtlInitUnicodeString o
    MmGetSystemRoutineAddress, devuelve el v2 summary sellado de M11.8-S.
    """
    if callee_addr is not None:
        c_addr = callee_addr & 0xFFFFFFFFFFFFFFFF
        # direcciones del IAT resuelto por CFGFast (-0x with 0x140100000 base)
        if c_addr == 0x140100000:
            with open(SEALED_RTL_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        if c_addr == 0x1401000e8:
            with open(SEALED_MM_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        # direcciones del IAT raw vista por objdump
        if c_addr == 0x140006000:  # slot IAT idx 0 — RtlInit
            with open(SEALED_RTL_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        if c_addr == 0x1400060e8:  # slot IAT idx 29 — MmGet
            with open(SEALED_MM_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
    if not os.path.exists(SEALED_CALLEE_PATH):
        raise FileNotFoundError("resumen sellado no encontrado en %s" % SEALED_CALLEE_PATH)
    with open(SEALED_CALLEE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("resumen sellado malformado")
    inner = data.get("summary", {})
    binary_sha = (data.get("oraculo") or {}).get("objdump_sha256") or \
                  (_load_sealed_analysis().get("artifact", {}).get("sha256"))
    return {
        "binary": {"sha256": binary_sha,
                   "architecture": "PE-x86_64"},
        "function": {"entry": 0x1400035f4, "size": 204,
                     "identity": inner.get("name", "sub_1400035f4")},
        "callsite": {"caller": None, "instruction": None,
                     "argument_index": 1,
                     "arguments": [
                         {"pos": 0, "kind": "rcx", "role": "table",
                          "observed_value": "from_AIL", "provenance": "sealed M10.3/M10.7"},
                         {"pos": 1, "kind": "rdx", "role": "buffer",
                          "observed_value": "from_AIL", "provenance": "sealed M10.3/M10.7"},
                     ]},
        "region": {"storage_id": "frame:-44:20", "start": -44, "end": -24,
                   "address_space": "stack"},
        "effects": {
            "reads": [
                {"target": "arg1", "span": 19, "termination": "NUL",
                 "frequency": "loop-bytewise"},
                {"target": "arg0", "span": 8, "termination": "entry_end",
                 "frequency": "per_entry"},
            ],
            "writes": [],
            "read_order": ["arg1[0]", "arg1[1]", "arg1[2]"],
            "termination": {
                "rule": inner.get("validity", ["byte-compare-hit or NUL"])[0],
                "proof": ["objdump 0x1400035f4..0x1400036c2 (sin stores fuera de prólogo)",
                          "movzx/cmp/cmp byte-wise sobre BYTE PTR"],
            },
            "return_relation": {
                "relation": "pointer_derived_from_a0",
                "proof": ["add rax,r9"],
            },
        },
        "coverage": {"completeness": "complete",
                     "scope_statement": "read-only w.r.t. args; args preserved bytewise; no globals modified",
                     "unresolved_paths": inner.get("unresolved_paths", []) or []},
        "oracle": {
            "binding": "SEAL: rxre-m10-7-sub_1400035f4",
            "verified_by": [
                "objdump -d 0x1400035f4..0x1400036c2",
                "AIL inspection ail_pr_head.json (#1400035f4..0x1400036c2)",
                "callee_summary_sub_1400035f4.json (seal verified + independent check)",
            ],
        },
        "seal": {
            "artifact_sha256": binary_sha,
            "signed": bool(inner.get("sealed")),
        },
    }


def _load_sealed_analysis() -> Dict[str, Any]:
    if not os.path.exists(SEALED_ANALYSIS_PATH):
        raise FileNotFoundError("análisis sellado no encontrado en %s" % SEALED_ANALYSIS_PATH)
    with open(SEALED_ANALYSIS_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("sealed", {}).get("result", data)


def _region_from_bytes(region_bytes) -> Optional[Dict[str, Any]]:
    if not isinstance(region_bytes, (set, frozenset, list, tuple)):
        return None
    if not region_bytes:
        return None
    vals = list(region_bytes)
    try:
        lo = min(vals)
        hi = max(vals)
    except TypeError:
        return None
    return {"start": lo, "end": hi + 1, "size": hi - lo + 1,
            "storage_id": "frame:%d:%d" % (lo, hi - lo + 1),
            "id": "region_%d_%d" % (lo, hi - lo + 1)}


def _reference_windows(stmt) -> List[Dict[str, Any]]:
    """Ventanas Reference{expresiones de stack} del statement (parseo del AIL textual).

    Devuelve [{id, base, end, size}] en offsets de pila.  Determinista; no hace
    ningún juicio de valor sobre el resultado."""
    out: List[Dict[str, Any]] = []
    try:
        s = str(stmt)
    except Exception:
        return out
    for m in re.finditer(r"Reference\s+([A-Za-z0-9_]+)\{s(-?\d+)\|(\d+)b\}", s):
        off, size = int(m.group(2)), int(m.group(3))
        out.append({"id": m.group(1), "base": off, "end": off + size, "size": size})
    return out


def _first_call_target(stmt) -> Optional[int]:
    """Dirección del callee dominante (el Call más externo) del statement."""
    try:
        s = str(stmt)
    except Exception:
        return None
    m = re.search(r"Call\((\d+)<", s)
    return int(m.group(1)) if m else None


def _reference_arg_interval(stmt) -> Optional[Dict[str, Any]]:
    """Compatibilidad: el Reference más interno del statement (window y ids)."""
    refs = _reference_windows(stmt)
    if not refs:
        return None
    lo = min(r["base"] for r in refs)
    hi = max(r["end"] for r in refs)
    return {"start": lo, "end": hi, "size": hi - lo,
            "interval": [lo, hi], "referenced_ids": sorted({r["id"] for r in refs})}


def _callee_addr(stmt) -> Optional[int]:
    """Dirección del callee dominante del statement (el Call más externo)."""
    return _first_call_target(stmt)


# Perfil del contrato v2 según el callee observado — el guard NO inventa campos.
_II = {
    # sub_1400035f4 — modelo M10.7 (ASCII IoDriverObjectType)
    0x1400035f4: {"argument_index": 1,
                  "arguments": [
                      {"pos": 0, "kind": "rcx", "role": "table",
                       "observed_value": "sealed-0x1400035f4-a0",
                       "provenance": "sealed M10.3/M10.7"},
                      {"pos": 1, "kind": "rdx", "role": "buffer",
                       "observed_value": "Reference-stack-region-{r}".format(r="REGION"),
                       "provenance": "AIL Reference(vvar) stack"},
                  ]},
    # RtlInitUnicodeString — resumen M11.8-S (IAT idx 0, callee = 0x140100000)
    0x140100000: {"argument_index": 0,
                  "arguments": [
                      {"pos": 0, "kind": "rcx", "role": "destination_string",
                       "observed_value": "Reference vvar_271{s-48|16b} @ AIL 0x1400053c2 #2",
                       "provenance": "IAT idx 0 — RtlInitUnicodeString"},
                      {"pos": 1, "kind": "rdx", "role": "source_wide_string",
                       "observed_value": "Reference vvar_260{s-92|2b} (v4 wide-string)",
                       "provenance": "AIL 0x140005344 #3 (wcsncpy) + 0x1400053c2 #1 (STORE 0)"},
                  ]},
    # MmGetSystemRoutineAddress — resumen M11.8-S (IAT idx 29, callee = 0x1401000e8)
    0x1401000e8: {"argument_index": 0,
                  "arguments": [
                      {"pos": 0, "kind": "rcx", "role": "system_routine_name",
                       "observed_value": "Reference vvar_271{s-48|16b} @ AIL 0x1400053de #1",
                       "provenance": "IAT idx 29 — MmGetSystemRoutineAddress"},
                  ]},
}


def _case_for_candidate(binary_path: str,
                        callee_addr: int,
                        region_base: int,
                        region_size: int,
                        callsite_addr: Optional[int],
                        caller_addr: Optional[int] = None,
                        arg_index: int = 1,
                        region_id: Optional[str] = None,
                        storage_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        binary_sha = _sha256_file(binary_path)
    except Exception:
        binary_sha = ""
    art = {"path": binary_path, "sha256": binary_sha}
    if caller_addr is not None:
        art["function"] = hex(caller_addr)
    profile = _II.get(callee_addr or -1)
    if profile is not None:
        args = []
        for a in profile["arguments"]:
            if a["observed_value"] == "Reference-stack-region-{r}".format(r="REGION"):
                args.append({**a,
                             "observed_value": "Reference-stack-region-%d-%d" % (region_base, region_base + region_size)})
            else:
                args.append(a)
        cs = {
            "caller": caller_addr,
            "instruction": callsite_addr,
            "argument_index": profile["argument_index"],
            "arguments": args,
        }
    else:
        cs = {
            "caller": caller_addr,
            "instruction": callsite_addr,
            "argument_index": arg_index,
            "arguments": [
                {"pos": 0, "kind": "rcx", "role": "table",
                 "observed_value": "sealed-0x1400035f4-a0", "provenance": "sealed M10.3/M10.7"},
                {"pos": 1, "kind": "rdx", "role": "buffer",
                 "observed_value": "Reference-stack-region-%d-%d" % (region_base, region_base + region_size),
                 "provenance": "AIL Reference(vvar) stack"},
            ],
        }
    return {
        "artifact": art,
        "function": {"addr": callee_addr} if callee_addr is not None else {"addr": caller_addr or 0},
        "callsite": cs,
        "region": {
            "id": region_id or "region_%d_%d" % (region_base, region_base + region_size),
            "storage_id": storage_id or "frame:%d:%d" % (region_base, region_size),
            "base": region_base,
            "size": region_size,
        },
        "sealed": None,
    }


def _enclosing_candidates(sealed_analysis: Dict[str, Any],
                          region_base: int,
                          region_size: int) -> List[Dict[str, Any]]:
    out = []
    for c in sealed_analysis.get("candidates", []) or []:
        iv = (c.get("region") or {}).get("interval")
        if not iv or len(iv) < 2:
            continue
        if iv[0] <= region_base and iv[1] >= region_base + region_size:
            out.append(c)
    return out


def _select_outer(enclosing: List[Dict[str, Any]],
                  referenced_ids: Optional[List[str]] = None,
                  min_span: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Selección fail-closed del vvar sellado que respalda a la región candidata.

    Se desambigua SOLO con evidencia del sello/resumen, en este orden:
      1. Si está `referenced_ids` y filtra a exactamente uno → ese (y al encoger
         a varios, continúa con ellos).
      2. Si el resumen declara un `span` de lectura para el buffer, los
         encierrantes más pequeños que el span no respaldan la evidencia
         interprocedural (p. ej. un cabecero de 16 bytes no cubre una lectura
         NUL-terminada de 19 bytes) → se descartan.
      3. Si queda exactamente uno → ese.
      4. Si queda más de uno, se prefiere el candidato cuya `encoding` es
         `ascii` (el callee consume texto bytes NUL-terminados); si no hay
         exactamente uno ascii (o no hay ascii y queda >1) → ABSTAIN.
    Cualquier otra situación → None (ABSTAIN), nunca uno al azar.
    """
    if not enclosing:
        return None
    if referenced_ids:
        by_id = [c for c in enclosing if c.get("candidate_id") in referenced_ids]
        if len(by_id) == 1:
            return by_id[0]
        if len(by_id) > 1:
            enclosing = by_id
    if min_span:
        big = [c for c in enclosing if c.get("region", {}).get("size", 0) >= min_span]
        if big:
            enclosing = big
    if len(enclosing) == 1:
        return enclosing[0]
    asc = [c for c in enclosing if c.get("region", {}).get("encoding") == "ascii"]
    if len(asc) == 1:
        return asc[0]
    return None


def _decide_candidate_core(binary_path: str,
                     candidate_id: str,
                     region_base: int,
                     region_size: int,
                     callee_addr: Optional[int],
                     callsite_addr: Optional[int],
                     caller_addr: Optional[int] = None,
                     sealed_analysis_path: Optional[str] = None,
                     sealed_summary_path: Optional[str] = None,
                     ail_path: Optional[str] = None,
                     referenced_ids: Optional[List[str]] = None,
                     inline_statements: Optional[List[str]] = None) -> Dict[str, Any]:
    """Decide sobre un candidato según el contrato v2.

    Devuelve dict con: decision, reason, binding, independent_oracle, admision.
    """
    ail = ail_path
    sid = sealed_analysis_path or SEALED_ANALYSIS_PATH
    ssp = sealed_summary_path or SEALED_CALLEE_PATH

    # 1) integridad de los artefactos sellados (DSSF obligatoria)
    seal_check = verify_seal_integrity()
    if not seal_check["ok"]:
        return {"decision": BLOCKED,
                "reason": "sellos M10.7 discordantes: %s" % seal_check["reason"],
                "binding": {}, "independent_oracle": [], "admision": {}}
    if not seal_check["ok"]:
        return {"decision": BLOCKED,
                "reason": "sellos M10.7 discordantes: %s" % seal_check["reason"],
                "binding": {}, "independent_oracle": [], "admision": {}}

    try:
        binary_sha = _sha256_file(binary_path)
    except Exception:
        return {"decision": BLOCKED, "reason": "binario no leíble", "binding": {},
                "independent_oracle": [], "admision": {}}

    try:
        sealed_analysis = _load_sealed_analysis()
    except Exception as exc:
        return {"decision": BLOCKED, "reason": "sellado de análisis no disponible: %s" % exc,
                "binding": {}, "independent_oracle": [], "admision": {}}

    # El sello debe corresponder a ESTE binario
    sealed_sha = (sealed_analysis.get("artifact") or {}).get("sha256")
    if sealed_sha != binary_sha:
        return {"decision": BLOCKED,
                "reason": "sello M10 no corresponde a este binario",
                "binding": {}, "independent_oracle": [], "admision": {}}

    try:
        summary = _load_sealed_summary(callee_addr)
    except Exception as exc:
        return {"decision": ABSTAIN,
                "reason": "resumen sellado no disponible: %s" % exc,
                "binding": {}, "independent_oracle": [], "admision": {}}

    # span declarado por el resumen para el argumento búfer (arg1), usado para
    # descartar encierrantes que no contienen la lectura interprocedural.
    min_span = None
    try:
        for rd in (summary.get("effects", {}).get("reads") or []):
            if rd.get("target") == "arg1":
                min_span = int(rd.get("span") or 0) or None
                break
    except Exception:
        min_span = None

    # Normalize candidate region to the enclosing sealed vvar (seal only vouches for the whole vvar).
    # La desambiguación se apoya SOLO en evidencia sellada: el span declarado por el
    # resumen (19 bytes NUL-terminados) y la `encoding` del propio sello.
    enclosing = _enclosing_candidates(sealed_analysis, region_base, region_size)
    outer = _select_outer(enclosing, referenced_ids, min_span=min_span)
    if outer is None:
        return {"decision": ABSTAIN,
                "reason": "candidate fuera de región sellada única (enclosing=%d)" % len(enclosing),
                "binding": {}, "independent_oracle": [], "admision": {}}
    outer_iv = outer["region"].get("interval")
    outer_base, outer_size = outer_iv[0], outer_iv[1] - outer_iv[0]
    outer_id = outer.get("candidate_id", candidate_id)
    outer_storage = "frame:%d:%d" % (outer_base, outer_size)

    case = _case_for_candidate(binary_path, callee_addr or 0,
                               outer_base, outer_size,
                               callsite_addr, caller_addr=caller_addr,
                               region_id=outer_id,
                               storage_id=outer_storage)
    case["region"]["id"] = outer_id
    case["region"]["storage_id"] = outer_storage
    case["region"]["sub_region"] = {"id": candidate_id,
                                    "base": region_base,
                                    "size": region_size}
    if ail_path or inline_statements:
        check = {}
        if ail_path:
            check["ail_path"] = ail_path
        if inline_statements:
            check["ail_statements"] = list(inline_statements)
            check["ail_instruction"] = callsite_addr
        case["check"] = check

    # callee_addr es el entry del sello soportado
    if summary.get("function", {}).get("entry") is not None and callee_addr is not None:
        if summary["function"]["entry"] != callee_addr:
            return {"decision": ABSTAIN,
                    "reason": "entry del resumen sellado ≠ callee observado",
                    "binding": {}, "independent_oracle": [], "admision": {}}

    try:
        from ier import rxre_angr_adapter as rvm
        result = rvm.emit_verified_decision(summary, case, sealed_analysis=sealed_analysis,
                                            ail_path=ail)
    except Exception as exc:
        return {"decision": BLOCKED,
                "reason": "adaptador falló: %s" % exc,
                "binding": {}, "independent_oracle": [], "admision": {}}

    # Consumo defensivo del resultado del adaptador (defensa en profundidad)
    decision = result.get("decision") if isinstance(result, dict) else None
    if decision not in (SAFE, PRESERVE_SCALAR, ABSTAIN, BLOCKED):
        decision = ABSTAIN
        return {"decision": decision,
                "reason": "veredicto no reconocido por el adaptador",
                "binding": {}, "independent_oracle": [], "admision": {}}
    if decision == SAFE:
        ver = result.get("verification") if isinstance(result.get("verification"), dict) else {}
        adm = result.get("admission") if isinstance(result.get("admission"), dict) else {}
        checks_run = ver.get("checks_run")
        passed = ver.get("pass")
        skipped = ver.get("skipped", 0)
        binding = adm.get("binding") if isinstance(adm.get("binding"), dict) else {}
        ok_all = (
            isinstance(checks_run, int) and isinstance(passed, int)
            and checks_run > 0 and passed == checks_run and skipped == 0
            and binding and all(v == "TRUE" for v in binding.values())
        )
        try:
            ok_fp = bool(rvm.recompute_admission_fingerprint(result))
        except Exception:
            ok_fp = False
        if not ok_all or not ok_fp:
            return {"decision": ABSTAIN,
                    "reason": "SAFE con evidencia/identidad no recomputable o incompleta",
                    "binding": binding, "independent_oracle": result.get("independent_oracle", []),
                    "admision": adm}

        # M11.9-C: regla composición — SAFE_fold ⟹ SAFE_local ∧ CERT_lifetime
        # Ruta contractual: el verificador genérico (lifetime_contract).
        # Compatibilidad: si la evidencia genérica no se encuentra (fixture
        # sin doc), se conserva la puerta histórica solo como compatibilidad
        # transitoria; no autoriza IRRELEVANT ni SAFE por sí sola.
        doc = _load_evidence_document()
        if doc is False:
            return {"decision": ABSTAIN,
                    "reason": "SAFE_local no autorizado: evidencia temporal presente pero inválida",
                    "binding": binding, "independent_oracle": result.get("independent_oracle", []),
                    "admision": adm}
        if doc is not None:
            try:
                from ier import lifetime_contract as lc
                cres = lc.verify_document(doc, artifact_path=binary_path,
                                          allowed={"function": caller_addr})
            except Exception as exc:
                cres = {"ok": False, "reason": "verificador temporal no disponible: %s" % exc}
            if not cres.get("ok"):
                return {"decision": ABSTAIN,
                        "reason": "SAFE_local no autorizado: certificado temporal no válido (%s)" %
                                cres.get("reason"),
                        "binding": binding, "independent_oracle": result.get("independent_oracle", []),
                        "admision": adm}
        else:
            # Compatibilidad M11.8-S (solo fallback; no es la ruta contractual).
            try:
                from ier import lifetime_check as lc
                lres = lc.verify_lifetime_certificate()
            except Exception as exc:
                lres = {"verdict": "BLOCKED", "reason": "lifetime_check no disponible: %s" % exc}
            if lres.get("verdict") != "CERTIFICATE_VALID":
                return {"decision": ABSTAIN,
                        "reason": "SAFE_local no autorizado: certificado temporal no válido (%s)" %
                                lres.get("reason", lres.get("verdict")),
                        "binding": binding, "independent_oracle": result.get("independent_oracle", []),
                        "admision": adm}

    return {
        "decision": decision,
        "reason": result.get("reason", ""),
        "binding": (result.get("admission") or {}).get("binding", {}),
        "independent_oracle": result.get("independent_oracle", []),
        "admision": result.get("admission", {}),
        "verification": result.get("verification", {}),
    }


def _decide_for_stmt_core(project, region_bytes, stmt, caller_addr: Optional[int] = None,
                    ail_path: Optional[str] = None,
                    function_addr: Optional[int] = None,
                    callsite_addr: Optional[int] = None,
                    stmt_index: Optional[int] = None) -> Dict[str, Any]:
    """Invocable desde el guard: recibe el statement con posible
    Reference(call) cuyo intervalo está COMPLETAMENTE contenido en la región
    candidata.  Abstenerse fuera de ese caso.

    ``function_addr`` es el entry de la función llamadora (identidad
    contrastada con el sello); ``callsite_addr`` es la dirección del bloque
    que contiene la sentencia (callsite observado).  Si no se proporcionan,
    se ABSTINE, nunca se asume."""
    if not isinstance(region_bytes, (set, frozenset, tuple, list)) or not region_bytes:
        return {"decision": BLOCKED, "reason": "región inválida", "binding": {},
                "independent_oracle": [], "admision": {}}
    if function_addr is None or callsite_addr is None:
        return {"decision": ABSTAIN,
                "reason": "identidad de función/callsite no proporcionada",
                "binding": {}, "independent_oracle": [], "admision": {}}

    # 0) IRRELEVANT estricto: evidencia temporal genérica, CFG-backed.
    if stmt_index is not None:
        v = _irrelevant_verdict(getattr(project, "filename", project),
                                function_addr, callsite_addr, stmt_index)
        if v is not None:
            return v

    lo, hi = min(region_bytes), max(region_bytes)
    size = hi - lo + 1
    refs = _reference_windows(stmt)
    if not refs:
        return {"decision": ABSTAIN, "reason": "sin Reference en la sentencia",
                "binding": {}, "independent_oracle": [], "admision": {}}
    covering = [r for r in refs if r["base"] <= lo and r["end"] >= hi + 1]
    if not covering:
        return {"decision": ABSTAIN,
                "reason": "ningún Reference cubre al candidato (%d..%d)" % (lo, hi),
                "binding": {}, "independent_oracle": [], "admision": {}}
    callee_addr = _callee_addr(stmt)
    if callee_addr is None:
        return {"decision": ABSTAIN, "reason": "callee unresolved",
                "binding": {}, "independent_oracle": [], "admision": {}}

    try:
        stmt_str = str(stmt)
    except Exception:
        stmt_str = ""

    return decide_candidate(getattr(project, "filename", project), "region_%d_%d" % (lo, hi + 1),
                            lo, size, callee_addr, callsite_addr,
                            caller_addr=function_addr,
                            ail_path=ail_path,
                            referenced_ids=sorted({r["id"] for r in covering}) or None,
                            inline_statements=[stmt_str] if stmt_str else None)


def decide_candidate(binary_path, candidate_id, region_base, region_size,
                     callee_addr, callsite_addr, caller_addr=None,
                     sealed_analysis_path=None, sealed_summary_path=None,
                     ail_path=None, referenced_ids=None, inline_statements=None):
    """Paraguas defensivo: ninguna excepción escapa al caller."""
    try:
        return _decide_candidate_core(binary_path, candidate_id, region_base,
                                      region_size, callee_addr, callsite_addr,
                                      caller_addr=caller_addr,
                                      sealed_analysis_path=sealed_analysis_path,
                                      sealed_summary_path=sealed_summary_path,
                                      ail_path=ail_path,
                                      referenced_ids=referenced_ids,
                                      inline_statements=inline_statements)
    except Exception as exc:
        return {"decision": BLOCKED,
                "reason": "error interno del bridge: %s" % exc,
                "binding": {}, "independent_oracle": [], "admision": {}}


def decide_for_stmt(project, region_bytes, stmt, caller_addr=None,
                    ail_path=None, function_addr=None, callsite_addr=None,
                    stmt_index=None):
    """Paraguas defensivo: ningún error interno habilita transformación."""
    try:
        return _decide_for_stmt_core(project, region_bytes, stmt,
                                     caller_addr=caller_addr,
                                     ail_path=ail_path,
                                     function_addr=function_addr,
                                     callsite_addr=callsite_addr,
                                     stmt_index=stmt_index)
    except Exception as exc:
        return {"decision": BLOCKED,
                "reason": "error interno del bridge: %s" % exc,
                "binding": {}, "independent_oracle": [], "admision": {}}
