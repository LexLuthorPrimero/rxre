#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · IER · REGION_ANALYZER_AIL — adaptador experimental AIL → region_analyzer.

## QUÉ ES

Adaptador desacoplado que traduce una **instantánea declarativa** de evidencia
AIL (los hechos relevantes observados en la decompilación de cancel.sys, M10.3)
a un payload del contrato de ``region_analyzer``.  NO importa angr, NO ejecuta
nada, NO reconstruye el binario.

## PÉRDIDA DE INFORMACIÓN (declarada, no oculta)

    1. Las identidades SSA (vvar_253/vvar_252) se conservan como "storage"
       declarado; el adaptador asigna storage "frame:-44:20" a ambos, que es la
       evidencia correcta (mismo intervalo). Alias no demostrables geométricamente
       se modelan con eventos ``alias``.
    2. La transformación XOR del loop se conserva como ``xor.index_base`` y los
       bytes almacenados como ``value`` en cada store; la reconstrucción del
       contenido SOLO se realiza cuando los operandos están demostrados.
    3. Las direcciones de bloque y los índices de sentencia son los del AIL
       post-simplificación; instrucciones VEX individuales no están incluidas.
    4. Los targets de llamada se resuelven fuera del adaptador; aquí viajan
       como resúmenes de callee declarados (``call_summaries`` del payload).
    5. Las estructuras UNICODE_STRING/objetos kernel no se modelan; solo
       intervalos de bytes y consumo textual declarado.
    6. El solape ``vvar_253``/``vvar_271`` NO se resuelve: sin procedencia de
       memoria suficiente, el analizador mantiene ABSTAIN (por diseño).

## USO

    from ier import region_analyzer_ail as ail
    payload = ail.build_cancel_sys_payload(callee_evidence="partial")  # default honesto
    result = region_analyzer.analyze(payload)

``callee_evidence="partial"`` (por defecto) refleja lo que hoy demuestra el
análisis: ``sub_1400035f4`` inspeccionado pero con efectos no completamente
determinados → NOT_DETERMINED.  ``callee_evidence="complete"`` es un
hipotético explícitamente etiquetado que muestra qué evidencia haría falta
para SAFE_TO_TRANSFORM; NO es un claim de que RXRE haya resuelto angr #7294.
"""
from __future__ import annotations

from typing import Any, Dict, List

ADAPTER_VERSION = "RYI-REGION-ANALYZER-AIL-2"

# Procedencia de los hechos: BINARIO cancel.sys, sha256 sellada en M10.3.
CANCEL_SYS_SHA256 = "bca61fba97ea68566b55c2860a8798650424cd59fec5eaf9aff02e0ec4a3a4d7"
FUNCTION_ADDR = 0x140005234

# CFG completo de la función (ail_pr_head.json · predecessor de cancel.sys),
# usado por el analizador para demostrar vidas disjuntas (temporally_aliased).
CFG_SUCCESSORS = {
    "0x140005234": ["0x14000526e", "0x1400052d9"],
    "0x14000526e": ["0x1400052ac", "0x140005293"],
    "0x1400052d9": ["0x1400052e7"],
    "0x1400052ac": ["0x1400052b9"],
    "0x140005293": ["0x140005293", "0x1400052ac"],
    "0x1400052e7": ["0x14000531e"],
    "0x1400052b9": ["0x1400052c9"],
    "0x14000531e": ["0x14000543a", "0x14000532c"],
    "0x1400052c9": ["0x14000543a", "0x1400052d9"],
    "0x14000543a": ["0x14000544a"],
    "0x14000532c": ["0x140005332"],
    "0x14000544a": [],
    "0x140005332": ["0x140005344"],
    "0x140005344": ["0x1400053ac"],
    "0x1400053ac": ["0x1400053ac", "0x1400053c2"],
    "0x1400053c2": ["0x1400053de"],
    "0x1400053de": ["0x1400053ec"],
    "0x1400053ec": ["0x140005417", "0x1400053fd"],
    "0x140005417": ["0x14000542c"],
    "0x1400053fd": ["0x140005405"],
    "0x140005405": ["0x140005412"],
    "0x14000542c": ["0x140005438"],
    "0x140005438": ["0x14000543a"],
    "0x140005412": ["0x140005417"],
}

LIVE_RANGES = {
    # vvar_253: definido 0x14000526e, último uso 0x1400052c9 (Call a sub_1400035f4).
    "vvar_253": {"start_block": "0x14000526e", "end_block": "0x1400052c9"},
    # vvar_252: rename-v1 de vvar_253 en el mismo almacenamiento; muere en 0x14000526e.
    "vvar_252": {"start_block": "0x14000526e", "end_block": "0x14000526e"},
    # vvar_271: construido por RtlInitUnicodeString (0x1400053c2), último uso 0x1400053de.
    "vvar_271": {"start_block": "0x1400053c2", "end_block": "0x1400053de"},
    # vvar_260: definido 0x140005344, usado por RtlInitUnicodeString (0x1400053c2).
    "vvar_260": {"start_block": "0x140005344", "end_block": "0x1400053c2"},
    # vvar_302: terminador escrito 0x1400052ac (dentro del rango de vvar_253).
    "vvar_302": {"start_block": "0x1400052ac", "end_block": "0x1400052ac"},
}


def _candidates() -> List[Dict[str, Any]]:
    base = {
        "artifact": "cancel.sys",
        "provenance": "AIL(AFTER_SSA_LEVEL1)",
    }
    return [
        dict(base, id="vvar_253", base=-44, size=20, encoding="ascii",
             label="vvar_253{s-44|20b} — 'IoDriverObjectType'",
             storage="frame:-44:20", ssa_version=1,
             live_range=LIVE_RANGES["vvar_253"]),
        dict(base, id="vvar_252", base=-44, size=20, encoding="binary",
             label="vvar_252{s-44|20b} — forma intermedia vvar_252 → vvar_253",
             storage="frame:-44:20", ssa_version=0,
             live_range=LIVE_RANGES["vvar_252"]),
        dict(base, id="vvar_271", base=-48, size=16, encoding="binary",
             label="vvar_271{s-48|16b} — UNICODE_STRING (encarnación post-0x1400053c2)",
             storage="frame:-48:16", ssa_version=0,
             live_range=LIVE_RANGES["vvar_271"]),
        dict(base, id="vvar_260", base=-92, size=4, encoding="unknown",
             label="vvar_260{s-92|4b} — buffer anexo ('ObMakeTemporaryObject')",
             storage="frame:-92:4", ssa_version=0,
             live_range=LIVE_RANGES["vvar_260"]),
        dict(base, id="vvar_302", base=-26, size=1, encoding="binary",
             label="vvar_302{s-26|1b} — terminador NUL de vvar_253",
             storage="frame:-26:1", ssa_version=0,
             live_range=LIVE_RANGES["vvar_302"]),
    ]


# Bytes almacenados por los Stores (verificado contra el AIL del PR en
# 0x14000526e: vvar_253 = Insert(Const(0xd9cb…<128>), 16, 10733521<32>)
# little-endian).  La decodificación del loop (0x140005293) aplica
# byte_i ^ ((i - 111) & 0xff) sobre cada byte individualmente:
#   d8 fd d7 e6 fc e0 f2 ea d6 f8 f1 f9 fe ea cb d9 d1 c7 a3
#   → 'I','o','D',…,'p','e' + NUL (bytes 18)  — verificado ejecutando la fórmula.
_STORE_BYTES = [0xd8, 0xfd, 0xd7, 0xe6, 0xfc, 0xe0, 0xf2, 0xea, 0xd6,
                0xf8, 0xf1, 0xf9, 0xfe, 0xea, 0xcb, 0xd9, 0xd1, 0xc7, 0xa3]
_XOR_INDEX_BASE = 145  # == (i - 111) & 0xff, i.e. lo que el loop computa por byte


def _wide_prefix_events() -> List[Dict[str, Any]]:
    # vvar_260 = 15728862<32> = bytes DE 00 F0 00 (little-endian) = wide chars
    # 0x00DE, 0x00F0 → decodificados con la misma fórmula (0x91, 0x92): 'O','b'
    # (inicio de "ObMakeTemporaryObject", verificado ejecutando la fórmula).
    return [
        {"kind": "store", "region": "vvar_260", "block": hex(0x140005344),
         "stmt": 0, "offset": 0, "size": 2, "value": 0x00DE,
         "data_class": "const", "scope": "function",
         "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
         "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                        "note": "const 15728862<32> bytes DE 00 F0 00"}},
        {"kind": "store", "region": "vvar_260", "block": hex(0x140005344),
         "stmt": 0, "offset": 2, "size": 2, "value": 0x00F0,
         "data_class": "const", "scope": "function",
         "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
         "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                        "note": "const 15728862<32> bytes DE 00 F0 00"}},
        {"kind": "rmw", "region": "vvar_260", "block": hex(0x1400053ac),
         "stmt": 1, "offset": 0, "size": 4,
         "xor": {"index_base": _XOR_INDEX_BASE, "unit_size": 2,
                 "formula": "decoded16[i] = stored16[i] ^ ((i + 145) & 0xffff)",
                 "reversible": True},
         "scope": "function", "source": "AIL(BEFORE_SSA_LEVEL1)",
         "confidence": "HIGH",
         "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                        "note": "loop de decodificación wide-char (XOR, Mul 2)"}},
    ]


def _prefix_stores_events() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for i, b in enumerate(_STORE_BYTES):  # Stores ASCII XOR-codificados (18 bytes)
        events.append({
            "kind": "store", "region": "vvar_253", "block": hex(0x14000526e),
            "stmt": 4 + i, "offset": i, "size": 1, "value": b,
            "scope": "function", "source": "AIL(BEFORE_SSA_LEVEL1)",
            "data_class": "const", "confidence": "HIGH",
            "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                           "byte": b,
                           "stmt_note": "escritura del byte %d (XOR-codificado)" % i},
        })
    events.append({
        "kind": "store", "region": "vvar_253", "block": hex(0x1400052ac),
        "stmt": 2, "offset": 18, "size": 1, "value": 0,
        "scope": "function", "source": "AIL(BEFORE_SSA_LEVEL1)",
        "terminator": True, "confidence": "HIGH"})
    events.append({
        "kind": "rmw", "region": "vvar_253", "block": hex(0x140005293),
        "stmt": 2, "offset": 0, "size": 18,
        "xor": {"index_base": _XOR_INDEX_BASE,
                "formula": "decoded[i] = stored[i] ^ ((i - 111) & 0xff)",
                "reversible": True},
        "scope": "function", "source": "AIL(BEFORE_SSA_LEVEL1)",
        "confidence": "HIGH",
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                       "note": "loop de decodificación byte a byte (XOR)"},
    })
    return events


def build_sub_1400035f4_summary() -> Dict[str, Any]:
    """Resumen SELLADO de sub_1400035f4.

    Derivado del cuerpo decompilado (AIL) y corroborado INDEPENDIENTEMENTE por
    objdump: la función compara byte a byte a1 con entradas de una tabla a0;
    no escribe fuera de su marco (ninguna instrucción con destino memoria fuera
    del prólogo/epílogo), devuelve puntero derivado de a0 o NULL, y el camino
    textual se toma cuando (unsigned)a1 & 0xffff0000 != 0 (cierto para punteros
    de pila del kernel). Nunca retorna a1 ni deriva su valor de a1.
    """
    from . import region_analyzer as ra
    body = {
        "name": "sub_1400035f4",
        "classification": "inspected",
        "reads_args": [0, 1],
        "writes_args": [],
        "writes_through_args": [],
        "preserves_pointer_args": [0, 1],
        "text_consuming": True,
        "writes_candidate_scalar": False,
        "unknown": False,
        "complete": True,
        "side_effects": [],
        "validity": [
            "a0 apunta a una tabla st_1400035f4_0 bien formada (field_18 entradas, strides field_1c/field_20/field_24, descriptor en a0+0x3c)",
            "a1 es una cadena terminada en NUL legible; (unsigned)a1 & 0xffff0000 != 0 ⇒ camino de comparación textual (se toma para punteros de pila del kernel)",
            "a1 y a0 no se modifican; el retorno deriva de a0 o es NULL",
        ],
        "evidence": [
            "AIL: bucle de comparación byte a byte sobre a1 (movzx/cmp sobre BYTE PTR) frente a a0+table — ail_pr_head.json (0x1400035f4..0x1400036c0)",
            "objdump -d 0x1400035f4..0x1400036c2 (oráculo independiente): cero stores fuera de prólogo (rsp+0x8..0x20); bucle movzx+cmp byte; retorno en 0x140003663 (add rax,r9); ret en 0x1400036b2",
            "camino (unsigned)a1 & 0xffff0000 != 0 salta a 0x140003668 (camino textual); para punteros de pila del kernel es no nulo",
            "call_target_analysis.json: textual_use=PROVEN; scalar_use=REFUTED",
            "retorno NULL cuando ninguna entrada coincide (0x14000369c)",
        ],
        "returns": "puntero derivado de a0 (entry_value a0 + índice de entrada) o 0 (NULL); jamás a1",
        "oracle": {"tool": "objdump (cross-check del cuerpo)", "result": "PASS"},
    }
    return ra.seal_call_summary(body)


def _sealed_external_summary(name: str, reads: List[int], writes: List[int],
                             text_src: bool, validity: List[str],
                             evidence: List[str]) -> Dict[str, Any]:
    from . import region_analyzer as ra
    body = {
        "name": name,
        "classification": "external-contract",
        "reads_args": list(reads), "writes_args": list(writes),
        "writes_through_args": [], "preserves_pointer_args": list(reads),
        "text_consuming": bool(text_src),
        "writes_candidate_scalar": False, "unknown": False,
        "complete": True,
        "side_effects": [],
        "validity": list(validity),
        "evidence": list(evidence),
        "oracle": {"tool": "MSDN contract + import table", "result": "PASS"},
    }
    return ra.seal_call_summary(body)


def _callee_summaries(evidence: str) -> Dict[str, Dict[str, Any]]:
    # Resumen de sub_1400035f4 — derivada del cuerpo decompilado (M10.4 §6.2).
    # NUNCA clasificada por nombre; solo por evidencia de cuerpo inspeccionado.
    if evidence == "sealed":
        # M10.7: cierre interprocedimental VERIFICABLE (cuerpo inspeccionado +
        # objdump independiente + resumen sellado). No es una asunción: es un
        # contrato verificado por dos vías independientes.
        sub = build_sub_1400035f4_summary()
        return {
            "sub_1400035f4": sub,
            "RtlInitUnicodeString": _sealed_external_summary(
                "RtlInitUnicodeString", [1], [0], True,
                ["MSDN contract; src NUL-terminated", "dest UNICODE_STRING bien formada"],
                ["MSDN RtlInitUnicodeString", "cancel.sys import table hint=2175"]),
            "MmGetSystemRoutineAddress": _sealed_external_summary(
                "MmGetSystemRoutineAddress", [0], [], True,
                ["MSDN contract", "UNICODE_STRING bien formada"],
                ["MSDN MmGetSystemRoutineAddress", "cancel.sys import table hint=1413"]),
            "ObReferenceObjectByName": _sealed_external_summary(
                "ObReferenceObjectByName", [0], [8], True,
                ["MSDN contract", "UNICODE_STRING bien formada"],
                ["MSDN ObReferenceObjectByName", "cancel.sys import table hint=1635"]),
        }
    if evidence == "complete":
        # HIPOTÉTICO EXPLÍCITO: asumiría que se demostró consumo textual del
        # argumento vvar_253 (iteración byte a byte hasta terminador/match).
        sub = {
            "name": "sub_1400035f4", "classification": "inspected",
            "reads_args": [0, 1], "writes_args": [],
            "text_consuming": True,  # <-- supuesto etiquetado, no demostrado
            "writes_candidate_scalar": False,
            "side_effects": ["none observed"],
            "validity": ["cuerpo inspeccionado", "bucle byte a byte sobre arg[1]"],
            "evidence": ["M10.4 §6.2 (decompilación)"],
        }
    else:
        # Estado honesto actual: cuerpo inspeccionado, efectos del arg[1] no
        # completamente determinados para el analizador (interprocedural parcial).
        sub = {
            "name": "sub_1400035f4", "classification": "inspected",
            "reads_args": [0, 1], "writes_args": [],
            "text_consuming": False,
            "writes_candidate_scalar": False,
            "side_effects": ["none observed in body"],
            "validity": ["cuerpo inspeccionado",
                         "consumo del arg[1] no completamente determinado"],
            "evidence": ["M10.4 §6.2 (decompilación)", "interprocedural parcial"],
        }
    return {
        "sub_1400035f4": sub,
        "RtlInitUnicodeString": {
            "name": "RtlInitUnicodeString", "classification": "external-contract",
            "reads_args": [1], "writes_args": [0],
            "text_consuming": True,
            "side_effects": ["writes UNICODE_STRING dest"],
            "validity": ["MSDN contract; src NUL-terminated"],
        },
        "MmGetSystemRoutineAddress": {
            "name": "MmGetSystemRoutineAddress", "classification": "external-contract",
            "reads_args": [0], "writes_args": [],
            "text_consuming": True,  # lee el UNICODE_STRING (texto) para resolver
            "side_effects": ["kernel lookup (tables)"],
            "validity": ["MSDN contract"],
        },
        "ObReferenceObjectByName": {
            "name": "ObReferenceObjectByName", "classification": "known-object-manipulator",
            "reads_args": [0], "writes_args": [8],
            "text_consuming": True,  # lee UNICODE_STRING por contrato
            "side_effects": ["object reference; locks"],
            "validity": ["MSDN contract"],
        },
    }


def build_cancel_sys_payload(callee_evidence: str = "partial") -> Dict[str, Any]:
    """Payload del contrato region_analyzer para el fixture cancel.sys.

    callee_evidence: "partial" (honesto) | "complete" (hipotético etiquetado)
    """
    if callee_evidence not in ("partial", "complete", "sealed"):
        raise ValueError("callee_evidence debe ser 'partial', 'complete' o 'sealed'")
    callees = _callee_summaries(callee_evidence)
    events: List[Dict[str, Any]] = list(_prefix_stores_events())
    events.extend(_wide_prefix_events())

    events.append({  # vvar_253 → sub_1400035f4 (arg[1], lookup del nombre)
        "kind": "call_arg", "region": "vvar_253", "block": hex(0x1400052ac),
        "stmt": 2, "arg_pos": 1, "scope": "function",
        "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
        "callee": callees["sub_1400035f4"],
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256},
    })
    events.append({  # Reference usada como dirección del Store (no lectura)
        "kind": "reference", "region": "vvar_253", "block": hex(0x1400052ac),
        "stmt": 2, "offset": 18, "size": 1, "scope": "function",
        "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                       "note": "Reference en la dirección del Store del terminador"},
    })
    events.append({  # mirror: arg[0] de sub_1400035f4 (tabla), no vvar_253
        "kind": "call_arg", "region": "vvar_271", "block": hex(0x1400053c2),
        "stmt": 2, "arg_pos": 1, "scope": "function",
        "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
        "callee": callees["RtlInitUnicodeString"],
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256},
    })
    events.append({  # vvar_271 → MmGetSystemRoutineAddress(arg[0] = &v4)
        "kind": "call_arg", "region": "vvar_271", "block": hex(0x1400053de),
        "stmt": 1, "arg_pos": 0, "scope": "function",
        "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
        "callee": callees["MmGetSystemRoutineAddress"],
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256},
    })
    events.append({  # vvar_260 = wide string fuente (arg1) de RtlInitUnicodeString(dest=vvar_271, src=vvar_260)
        "kind": "call_arg", "region": "vvar_260", "block": hex(0x1400053c2),
        "stmt": 2, "arg_pos": 1, "scope": "function",
        "source": "AIL(BEFORE_SSA_LEVEL1)", "confidence": "HIGH",
        "callee": callees["RtlInitUnicodeString"],
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256},
    })
    events.append({  # vvar_252 y vvar_253: mismo slot bajo dos etiquetas SSA
        "kind": "alias", "region": "vvar_252", "other": "vvar_253",
        "confirmed": True, "block": hex(0x14000526e), "stmt": 4,
        "scope": "function", "source": "AIL(AFTER_SSA_LEVEL1)",
        "confidence": "HIGH",
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                       "method": "SSA rename provenance"},
    })
    events.append({  # vvar_253 vs vvar_271: solapamiento parcial 12 bytes
        # la geometría ya lo detecta; este evento no es necesario, pero el
        # adaptador lo registra como procedencia observada del solape.
        "kind": "reference", "region": "vvar_271", "block": hex(0x1400053c2),
        "stmt": 2, "scope": "function", "source": "AIL(BEFORE_SSA_LEVEL1)",
        "confidence": "HIGH",
        "provenance": {"artifact_sha256": CANCEL_SYS_SHA256,
                       "note": "&v4 pasa como dest de RtlInitUnicodeString"},
    })

    return {
        "capability": "region_analyzer",
        "capability_version": "RYI-REGION-ANALYZER-1",
        "artifact": {
            "path": "binaries/tests/x86_64/windows/cancel.sys",
            "sha256": CANCEL_SYS_SHA256,
            "kind": "PE",
            "function": hex(FUNCTION_ADDR),
        },
        "function": {"addr": hex(FUNCTION_ADDR)},
        "candidates": _candidates(),
        "events": events,
        "oracle": {"independent": False},
        "assurance": {
            "coverage": "complete",
            "scope": "function 0x140005234",
            "method": "ail_pr_head.json: enumeración total de usos (AIL completo post-simplificación); vvar_253 último uso 0x1400052c9; vvar_271 construido 0x1400053c2",
        },
        "cfg_successors": CFG_SUCCESSORS,
        "adapter": {
            "name": ADAPTER_VERSION,
            "callee_evidence": callee_evidence,
            "loses": [
                "instr-level precision (VEX)",
                "XOR decode key material",
                "SSA def-use edges entre iteraciones del loop",
                "estructuras UNICODE_STRING internas",
                "targets exactos de llamada sin resolución externa",
            ],
            "retains": [
                "intervalos de bytes por candidato (storage declarado por intervalo exacto)",
                "escrituras de prefijo byte a byte con valores const (offset + size)",
                "terminador NUL",
                "parámetros XOR demostrados (xor.index_base) para reconstrucción condicional",
                "referencias como dirección (sin contenido) vs acceso de contenido",
                "call_arg con resumen de callee declarado",
                "procedencia de artefacto por hash y linaje SSA por versión",
            ],
        },
    }
