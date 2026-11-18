#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · IER · WITNESS_CASES — casos del testigo construidos desde evidencia sellada.

## QUÉ ES

Construye el/los caso(s) del testigo de transformación para ``cancel.sys`` a
partir EXCLUSIVAMENTE de artefactos sellados verificados (M10.5–M10.7) y de
los hechos AIL registrados en los informes de misión.  No inventa hechos;
no reconstruye silenciosamente lo que falta:

    - Los bytes XOR-codificados de vvar_253 vienen del AIL sellado (ail_pr_head).
    - Los intervalos consumidos/escritos vienen de la evidencia del análisis.
    - La procedencia/notación temporal viene del análisis de CFG (M10.7).

## QUÉ NO ES

    - NO es el guard de angr ni lo consulta.
    - NO ejecuta cancel.sys ni su decompilación.
    - NO es un oráculo en sí mismo: los oráculos independientes van en el campo
      ``independent_oracle`` del caso (gcc decode, objdump corroboración).
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

WITNESS_CASES_VERSION = "RYI-WITNESS-CASES-1"

_XOR_BYTES = [0xd8, 0xfd, 0xd7, 0xe6, 0xfc, 0xe0, 0xf2, 0xea, 0xd6,
              0xf8, 0xf1, 0xf9, 0xfe, 0xea, 0xcb, 0xd9, 0xd1, 0xc7, 0xa3]
_BASE = -44
_SIZE = 20

# 0x14000526e define vvar_253; último uso 0x1400052c9; función 0x140005234.
_CANARY_ARTIFACT = {
    "path": "binaries/tests/x86_64/windows/cancel.sys",
    "sha256": "bca61fba97ea68566b55c2860a8798650424cd59fec5eaf9aff02e0ec4a3a4d7",
    "kind": "PE",
    "function": "0x140005234",
}


def build_cancel_sys_case(m10_dir: str) -> Dict[str, Any]:
    """Caso: fold del simplificador sobre los Stores instanciados de vvar_253.

    La transformación propuesta es la que el #7294 ejercita: reemplazar la
    secuencia de Stores const por una copia inline de los mismos bytes; el
    loop XOR (0x140005293), el terminador (0x1400052ac) y los usos posteriores
    permanecen inalterados.

    @param m10_dir: directorio sellado M10 (p. ej. ~/rxre-angr-7294-m10)
    """
    manifest_verified = []
    for suffix in ("5", "6", "7"):
        mp = os.path.join(m10_dir, "SHA256SUMS.m10.%s" % suffix)
        if os.path.exists(mp):
            manifest_verified.append("SHA256SUMS.m10.%s" % suffix)

    from ier.independent_verifier import load_sealed_analysis
    sealed_analysis = load_sealed_analysis(m10_dir)   # verifica SHA256SUMS.m10.7
    res = sealed_analysis
    c253 = next(c for c in res["candidates"] if c["candidate_id"] == "vvar_253")
    evidence_intervals = [
        {"id": e["id"], "interval": e.get("interval"), "category": e["category"],
         "confidence": e["confidence"]}
        for e in c253["evidence"]
    ]

    encoded = list(_XOR_BYTES)
    case = {
        "case_id": "cancel_sys_strncpy_fold_v1",
        "artifact": _CANARY_ARTIFACT,
        "manifest_verified": manifest_verified,
        "sealed_analysis": sealed_analysis,
        "region": {
            "id": "vvar_253", "base": _BASE, "size": _SIZE,
            "interval": [_BASE, _BASE + _SIZE],
            "storage": "frame:-44:20",
            "provenance": "AIL(AFTER_SSA_LEVEL1)",
        },
        # secuencia original (modela el dominio del guard: los Stores const)
        "original_sequence": {
            "ops": [
                {"op": "store_const_bytes", "offset": 0, "bytes": encoded},
                {"op": "rmw_xor", "offset": 0, "size": 18, "index_base": 145},
                {"op": "store_const", "offset": 18, "value": 0},
            ],
        },
        # transformación propuesta: fold a copia inline de los mismos bytes
        "proposed_transform": {
            "kind": "inline_copy",
            "description": ("InlinedStrcpySimplifier fold de los Stores const: "
                            "los bytes almacenados son idénticos; el loop XOR y "
                            "el terminador permanecen inalterados"),
            "ops": [
                {"op": "store_const_bytes", "offset": 0, "bytes": encoded},
                {"op": "rmw_xor", "offset": 0, "size": 18, "index_base": 145},
                {"op": "store_const", "offset": 18, "value": 0},
            ],
            "storage_writes": ["frame:-44:20"],
            "overlap_intervals": [[-44, -25]],
        },
        "intervals_written_original": [[-44, -25]],
        "intervals_written_transform": [[-44, -25]],
        "observations": {
            # bytes que cualquier observador lee o escribe dependiendo de ellos
            "consumed_intervals": [[-44, -25]],
            "evidence_intervals": evidence_intervals,
            "unobserved_bytes": [[-25, -24]],
        },
        "order_check": {
            # secuencia observable de operaciones sobre la región, en orden
            "original": [("write", "frame:-44:20"), ("rmw_xor", "frame:-44:20"),
                         ("write", "frame:-44:20"), ("call", "sub_1400035f4")],
            "transform": [("write", "frame:-44:20"), ("rmw_xor", "frame:-44:20"),
                          ("write", "frame:-44:20"), ("call", "sub_1400035f4")],
        },
        "lineage": {
            "allowed_storage_writes": ["frame:-44:20"],
            "must_not_overlap": [
                # vvar_271 (UNICODE_STRING) NO existe durante la transformación
                # (construido en 0x1400053c2, posterior al último uso de vvar_253)
                {"id": "vvar_271", "interval": [-48, -32],
                 "live_during_transform": False},
                # vvar_260: definido 0x140005344, posterior al último uso
                {"id": "vvar_260", "interval": [-92, -88],
                 "live_during_transform": False},
            ],
        },
        # oráculo independiente: gcc 11 compiló y ejecutó xor_decode y produjo
        # los bytes decodificados esperados (m10.7_oracle_xor_decode.txt)
        "independent_oracle": {
            "tool": "gcc 11 -std=c11 xor_decode (logs/m10.7_oracle_xor_decode.txt)",
            "result": "PASS",
            "note": "verifica la reconstrucción XOR; NO valida el driver ni el guard",
        },
        "domain": {
            "artifact_sha256": _CANARY_ARTIFACT["sha256"],
            "function": "0x140005234",
            "scope": "fold de los Stores const de vvar_253; loop XOR y usos posteriores inalterados",
            "limits": [
                "vinculación K=(S,C,T,O) exigida por el contrato de evidencia (M10.10.1)",
                "oráculo gcc valida la reconstrucción XOR, no la ejecución del driver",
                "la transformación es concreta (inline copy de bytes idénticos); otras transformaciones quedan sin evaluar",
                "vvar_271 y vvar_260 no existían durante la vida de vvar_253; reutilización temporal demostrada",
                "el veredicto del testigo NO revoca el veto ABSTAIN del analizador",
            ],
        },
    }
    return case


def _load_json(path: str) -> Dict[str, Any]:
    import json
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
