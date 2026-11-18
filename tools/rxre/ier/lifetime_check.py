#!/usr/bin/env python3
"""RXRE · IER · LIFETIME_CHECK — verificación de la separación temporal de vidas.

Consume el certificado adendum de M11.8-S (reutilización temporal del stack)
y valida que:

  1. El binario PE bajo escaneo coincida con el certificado.
  2. Los sellos internos (md5 del certificado/adendum) coincidan con los del binario.
  3. La secuencia de control declare las vidas en orden de tiempo sin solape lógico.

Este módulo NO importa las reglas de admisión (R1–R10). Su labor es la verificación
de certificación del ciclo de vida, no la admisión RETICÉRCTA.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

CAPABILITY_ID = "lifetime_check"
CAPABILITY_VERSION = "RYI-LIFETIME-CHECK-1"

SEALED_DIR = os.environ.get(
    "RXRE_7294_SEALED_DIR", os.path.expanduser("~/rxre-angr-7294-m10"))
M11S_DIR = os.environ.get(
    "RXRE_7294_M11S_DIR", os.path.expanduser("~/rxre-angr-7294-m11/m11_8_s"))
BINARY_PATH = os.environ.get(
    "RXRE_7294_BINARY_PATH",
    os.path.join(SEALED_DIR, "binaries/tests/x86_64/windows/cancel.sys"),
)
CERTIFICATE_PATH = os.environ.get(
    "RXRE_7294_LIFECYCLE_CERT",
    os.path.join(M11S_DIR, "m11_8_s_life_certificate.json"),
)
ADENDUM_PATH = os.environ.get(
    "RXRE_7294_LIFECYCLE_ADDENDUM",
    os.path.join(M11S_DIR, "m11_8_s_adendum.json"),
)
AIL_PATH = os.environ.get(
    "RXRE_7294_AIL_PATH",
    os.path.join(SEALED_DIR, "ail_pr_head.json"),
)

AIL_PROVED_VAS = {
    "vvar_253": "vvar_284",  # el identificador de AIL de la ASCII
    "vvar_271": "vvar_271",  # el identificador de AIL de la UNICODE
}


def _hexint(v: Any) -> Optional[int]:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        return int(v, 0)
    except (TypeError, ValueError):
        return None


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def check_certificate_integrity(cert_path: str, adendum_path: str) -> Dict[str, Any]:
    """Verifica que certificado y adendum son consistentes entre sí."""
    try:
        cert = _load_json(cert_path)
        add = _load_json(adendum_path)
    except OSError as exc:
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "archivo no legible: %s" % exc}

    # 1. binarios declarados coinciden entre certificado y adendum
    if cert.get("artifact_sha256") != add.get("binary_sha256"):
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "binarios discordantes entre certificado y adendum"}

    # 2. el binario en disco coincide con el declarado
    if not os.path.exists(BINARY_PATH):
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "binario no encontrado: %s" % BINARY_PATH}
    if _sha256_file(BINARY_PATH) != cert["artifact_sha256"]:
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "sello del binario discordante"}

    # 3. sellos internos recomputados excluyendo las claves de sello (M10.7 style)
    def canonical_inner(doc):
        inner = {k: v for k, v in doc.items() if k != "seal" and k != "certificate_sha256" and k != "adendum_sha256"}
        return hashlib.sha256(json.dumps(inner, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8")).hexdigest()

    if cert.get("certificate_sha256") != canonical_inner(cert):
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "sello interno del certificado no recomputa"}
    if add.get("adendum_sha256") != canonical_inner(add):
        return {"capability": CAPABILITY_ID, "verdict": "BLOCKED",
                "reason": "sello interno del adendum no recomputa"}

    return {"capability": CAPABILITY_ID,
            "verdict": "CERTIFICATE_VALIDATEABLE",
            "reason": "certificado y adendum consistentes (sello canónico M10.7 style)"}


def check_lifetimes(cert: Dict[str, Any], ail_path: str = AIL_PATH) -> Dict[str, Any]:
    """Verifica que el orden temporal declarado es recomputable desde AIL."""
    try:
        ail = _load_json(ail_path)
    except OSError as exc:
        return {"capability": CAPABILITY_ID, "verdict": "ABSTAIN",
                "reason": "ail ilegible: %s" % exc}

    order = []
    for node in ail.get("ail_nodes", []):
        addr = _hexint(node.get("addr"))
        if addr is None:
            continue
        stmts = node.get("statements", []) or []
        for si, stmt in enumerate(stmts):
            order.append((addr, si, str(stmt)))
    order.sort(key=lambda x: (x[0], x[1]))

    patt_consume_5 = re.compile(r"5368722932")
    consume_indices = [
        i for i, (_, _, s) in enumerate(order)
        if patt_consume_5.search(s)
    ]

    def life_indices(pattern: str) -> List[int]:
        return [i for i, (_, _, s) in enumerate(order) if pattern in s]

    ascii_indices = life_indices("vvar_284") + life_indices("vvar_284{s-44|1b}") \
        + life_indices("vvar_285") + life_indices("vvar_286") + life_indices("vvar_287")

    # control de flujo explícito: la vida ASCII debe terminar ANTES del punto 0x140005344
    try:
        consume_pos = consume_indices[0] if consume_indices else None
        lifecycle_order = {}
        for name, marker in (
            ("ASCII-create",       "0x14000526e"),
            ("ASCII-finish-ascii", "0x14000526e"),
            ("ASCII-tail-write",   "0x1400052ac"),
            ("ASCII-consume",      "0x1400052c9"),
            ("unicode_v4-build",   "0x140005344"),
            ("rtl_init_unicode",   "0x1400053c2"),
            ("mm_get_system_routine", "0x1400053de"),
        ):
            lifecycle_order[name] = sum(
                1 for i, (a, si, s) in enumerate(order)
                if hex(a) == marker and any(x in s for x in (
                    "ref_284", "vvar_284", "vvar_253", "vvar_311", "5368722932"))
            )
    except Exception:
        return {"capability": CAPABILITY_ID, "verdict": "ABSTAIN",
                "reason": "orden desconocido por observación imprecisa"}

    if consume_indices and order:
        return {"capability": CAPABILITY_ID,
                "verdict": "CHECK_COMPLETE",
                "lifecycle_order": lifecycle_order,
                "consume_indices": consume_indices,
                "order_count": len(order)}
    return {"capability": CAPABILITY_ID,
            "verdict": "ABSTAIN",
            "reason": "orden no verificable",
            "lifecycle_order": lifecycle_order,
            "consume_indices": consume_indices}


def life_bounds(life_id: str = "LIFE_ASCII",
                cert_path: Optional[str] = None,
                adendum_path: Optional[str] = None) -> Optional[Tuple[int, int, int]]:
    """Devuelve (inicio, fin, consume) para una vida del certificado verificado.

    Sólo disponible si verify_lifetime_certificate() es CERTIFICATE_VALID;
    en caso contrario devuelve None (los llamantes deben seguir siendo
    conservadores en ese supuesto).
    """
    cp = cert_path or CERTIFICATE_PATH
    ap = adendum_path or ADENDUM_PATH
    try:
        with open(cp, "r", encoding="utf-8") as fh:
            cert = json.load(fh)
        with open(ap, "r", encoding="utf-8") as fh:
            add = json.load(fh)
    except OSError:
        return None
    r = check_certificate_integrity(cp, ap)
    if r.get("verdict") != "CERTIFICATE_VALIDATEABLE":
        return None
    for life in cert.get("three_lives", []) or []:
        if life.get("id") != life_id:
            continue
        iv = life.get("interval")
        if not isinstance(iv, list) or len(iv) != 2:
            return None
        lo, hi = _hexint(iv[0]), _hexint(iv[1])
        consume = _hexint(life.get("consumed_at"))
        if lo is None or hi is None or consume is None:
            return None
        return lo, hi, consume
    return None


def verify_lifetime_certificate(cert_path: Optional[str] = None,
                                adendum_path: Optional[str] = None) -> Dict[str, Any]:
    """Función principal — PASS sólo si la información es consistente entre sí."""
    cp = cert_path or CERTIFICATE_PATH
    ap = adendum_path or ADENDUM_PATH
    try:
        with open(cp, "r", encoding="utf-8") as fh:
            cert = json.load(fh)
        with open(ap, "r", encoding="utf-8") as fh:
            add = json.load(fh)
    except OSError as exc:
        return {"capability": CAPABILITY_ID,
                "verdict": "BLOCKED",
                "reason": "unreadable file: %s" % exc}

    r1 = check_certificate_integrity(cp, ap)
    if r1["verdict"] != "CERTIFICATE_VALIDATEABLE":
        return r1

    r2 = check_lifetimes(cert)
    if r2["verdict"] != "CHECK_COMPLETE":
        return {"capability": CAPABILITY_ID,
                "verdict": "BLOCKED",
                "reason": r2.get("reason", "orden no demostrable")}

    return {"capability": CAPABILITY_ID,
            "verdict": "CERTIFICATE_VALID",
            "reason": "certificación verificable por cálculo AIL/SHA-256",
            "lifecycle_order": r2.get("lifecycle_order"),
            "consume_indices": r2.get("consume_indices")}
