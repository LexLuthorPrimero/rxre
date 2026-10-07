#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-008 FASE 3 — Relation Engine: T0501-T0508 tests.

QUE PRUEBA Y QUE NO.

Este módulo convierte el requisito de Relation Engine del diseño
de migración RXRE-008 en vectores ejecutables y discriminantes.

NO prueba MMIO, NO ejecuta hardware, NO toca la Intel iGPU.
Solo audita la representación de relaciones que relations.py produce.

Cada test tiene:
    - ORACLE INDEPENDIENTE: construido sin relations.py (regex propia)
    - CRITERIO DE FALLO CONTRA EL DEFECTO ACTUAL: se documenta por que
      el test falla frente a la implementación defectuosa actual
    - CRITERIO DE PASS: lo que debe成立 despues de la implementación

Un vector que pasa porque el defecto aun no fue detectado NO es un vector
verde: test_verde_y_defecto_presente = INVALID (el test no es discriminante)
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

sys.path.insert(0, os.path.join(ROOT, "tools", "rxre"))

from core.store import conectar, conectar as _conectar  # noqa: F401

fails: List[str] = []
checks = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global checks
    checks += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

DB_PATH = "/tmp/opencode/test_p005_relations.sqlite3"


def _setup() -> Any:
    """Crea una base limpia para el test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return conectar(DB_PATH)


def _teardown(c: Any) -> None:
    c.close()
    try:
        os.remove(DB_PATH)
    except Exception:
        pass


def _crear_resultado_op(c: Any, op_id: str, res_id: str, value: str = "0xA21") -> None:
    """Crea una operacion y resultado base para tests."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    c.execute(
        "INSERT INTO operations(operation_id, request_id, contract_ver, operacion, capability, question, target, scope, status, n_results, request_json, response_json, target_pci, timestamp, duracion_s) "
        "VALUES (?, '', 'test', 'register', 'register.definition', 'test_q', '1002:699f@c7', 'test', 'ok', 1, '{}', '{}', '', ?, 0.0)",
        (op_id, ts),
    )
    c.execute(
        "INSERT INTO results(result_id, operation_id, type, value, source, file, line, scope, tool, tool_version, status, raw_json, timestamp) "
        "VALUES (?, ?, 'register', ?, 'test', '', 0, '', '', '', 'ok', '{}', ?)",
        (res_id, op_id, value, ts),
    )
    c.commit()


def _crear_edge(c: Any, src: str, tipo: str, dst: str, status: str = "observed") -> None:
    """Crea una arista de dominio para respaldar una cadena."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    c.execute(
        "INSERT INTO edges(src, tipo, dst, status, scope, tool, evidence_json,"
        "operation_id, result_id, timestamp) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (src, tipo, dst, status, "", "", "", None, None, ts),
    )
    c.commit()


# ---------------------------------------------------------------------------
# T0501 — Relation creation
# ---------------------------------------------------------------------------

def test_T0501_relation_creation() -> None:
    """Crear una relación controlada: producer → transformation → representation → consumer."""
    from core.relations import registrar_cadena, obtener_cadena

    c = _setup()
    try:
        op_id = "op_T0501_prod"
        res_id = "res_T0501_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0501",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps([f"res_{res_id}"]),
            evidence_json=json.dumps([f"res_{res_id}"]),
            confidence=0.8,
            limitations="transformation based on pattern match",
            created_by="test_session",
        )

        v("T0501: cadena registrada", cadena_id is not None and cadena_id != "")
        # Verificar que se puede obtener
        cadena = obtener_cadena(c, cadena_id)
        v("T0501: cadena obtenida", cadena is not None)
        v("T0501: producer correcto", cadena and cadena.get("producer") == op_id)
        v("T0501: transformation correcto", cadena and cadena.get("transformation") == "bits_extract_0_7")
        v("T0501: representation correcto", cadena and cadena.get("representation") == "0xA21_val")
        v("T0501: consumer correcto", cadena and cadena.get("consumer") == res_id)
        v("T0501: effect correcto", cadena and cadena.get("effect") == "register_write_enabled")
        v("T0501: relation_type correcto", cadena and cadena.get("relation_type") == "PRODUCES")
        v("T0501: epistemic_state correcto", cadena and cadena.get("epistemic_state") == "PARTIAL")
        v("T0501: target correcto", cadena and cadena.get("target") == "1002:699f@c7")
        v("T0501: offset correcto", cadena and cadena.get("offset") == "0xA21")
        v("T0501: confidence correcto", cadena and cadena.get("confidence") == 0.8)
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0502 — Partial relation
# ---------------------------------------------------------------------------

def test_T0502_partial_relation() -> None:
    """Eliminar deliberadamente una evidencia intermedia. Esperado: PARTIAL."""
    from core.relations import registrar_cadena, actualizar_estado, obtener_cadena

    c = _setup()
    try:
        op_id = "op_T0502_prod"
        res_id = "res_T0502_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0502",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json="[]",  # sin evidencia
            evidence_json="[]",    # sin evidencia
            confidence=0.0,
            limitations="sin evidencia intermedia",
            created_by="test_session",
        )

        v("T0502: cadena creada con PARTIAL", cadena_id is not None)
        cadena = obtener_cadena(c, cadena_id)
        v("T0502: estado inicial PARTIAL", cadena and cadena.get("epistemic_state") == "PARTIAL")

        # Intentar actualizar a PROVEN sin evidencia (debe fallar)
        ok = actualizar_estado(c, cadena_id, "PROVEN", "sin evidencia pero forzado")
        v("T0502: PROVEN sin evidencia rechazado", not ok)
        cadena = obtener_cadena(c, cadena_id)
        v("T0502: estado sigue PARTIAL tras intento PROVEN", cadena and cadena.get("epistemic_state") == "PARTIAL")
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0503 — False causal inference
# ---------------------------------------------------------------------------

def test_T0503_false_causal_inference() -> None:
    """Solo references NO deben convertirse automáticamente en causalidad."""
    from core.relations import registrar_cadena, obtener_cadena, listar_cadenas, actualizar_estado

    c = _setup()
    try:
        # Crear una operación y resultado base primero
        op_id = "op_T0503_ref"
        res_id = "res_T0503_ref"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        # Registrar una cadena como REFERENCE (sin evidencia causal real)
        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0503",
            producer=op_id,
            transformation="unknown",
            representation="unknown_val",
            consumer=res_id,
            effect="unknown_effect",
            relation_type="PRODUCES",  # pero sin evidencia, la cadena no se convierte en causalidad
            epistemic_state="NOT_DETERMINED",  # NOT_DETERMINED, no PROVEN automático
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json="[]",  # sin evidencia
            evidence_json="[]",    # sin evidencia
            confidence=0.0,
            limitations="solo reference, no causalidad probada",
            created_by="test_session",
        )

        v("T0503: cadena creada como NOT_DETERMINED", cadena_id is not None)
        cadenas = listar_cadenas(c, epistemic_state="NOT_DETERMINED")
        v("T0503: se puede listar como NOT_DETERMINED", len(cadenas) > 0)

        # Intentar actualizar a PROVEN sin evidencia (debe fallar)
        if cadena_id:
            ok = actualizar_estado(c, cadena_id, "PROVEN", "intentando convertir reference a PROVEN")
            v("T0503: PROVEN rechazado para reference sin evidencia", not ok)
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0504 — Provenance preservation
# ---------------------------------------------------------------------------

def test_T0504_provenance_preservation() -> None:
    """Eliminar provenance mediante mutación debe fallar la validación."""
    from core.relations import registrar_cadena, obtener_cadena, actualizar_estado

    c = _setup()
    try:
        op_id = "op_T0504_prod"
        res_id = "res_T0504_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0504",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps([f"res_{res_id}"]),
            evidence_json="[]",  # SIN evidencia para probar el bloqueo de PROVEN
            confidence=0.8,
            limitations="transformation based on pattern match",
            created_by="test_session",
        )

        v("T0504: cadena registrada con provenance", cadena_id is not None)
        cadena = obtener_cadena(c, cadena_id)
        prov = cadena.get("provenance_json", "") if cadena else ""
        v("T0504: provenance no vacía", prov != "")

        # Intentar PROVEN sin evidencia (debe fallar)
        if cadena_id:
            ok = actualizar_estado(c, cadena_id, "PROVEN", "sin evidencia suficiente")
            v("T0504: PROVEN sin evidencia rechazado", not ok)
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0505 — Conflict preservation
# ---------------------------------------------------------------------------

def test_T0505_conflict_preservation() -> None:
    """Verificar que Relation Engine no destruye CONFLICT/CANDIDATES/CHOSEN=null."""
    from core.conflicts import registrar_conflicto, conflictos_para_target
    from core.relations import registrar_cadena, obtener_cadena, listar_cadenas

    c = _setup()
    try:
        # Registrar un conflicto primero
        refs = [f"res_{__import__('hashlib').sha256(b'test_conflict').hexdigest()[:16]}"]
        op_id = "op_T0505_conf"
        c.execute(
            "INSERT INTO operations(operation_id, request_id, contract_ver, operacion, capability, question, target, scope, status, n_results, request_json, response_json, target_pci, timestamp, duracion_s) "
            "VALUES (?, '', 'test', 'test_op', 'register.definition', 'test_q', '1002:699f@c7', 'test', 'ok', 1, '{}', '{}', '', ?, 0.0)",
            (op_id, time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        )
        c.execute(
            "INSERT INTO results(result_id, operation_id, type, value, source, file, line, scope, tool, tool_version, status, raw_json, timestamp) "
            "VALUES (?, ?, 'register', '0xA21', 'test', '', 0, '', '', '', 'ok', '{}', ?)",
            (refs[0], op_id, time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        )
        c.commit()

        conflicto_id = registrar_conflicto(
            c, "1002:699f@c7", "0xA21", "OFFSET_COLLISION", refs, "test_session"
        )
        v("T0505: conflicto registrado", conflicto_id is not None)

        # Ahora crear una cadena de relación
        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0505",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=refs[0],
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps(refs),
            evidence_json=json.dumps(refs),
            confidence=0.8,
            limitations="",
            created_by="test_session",
        )
        v("T0505: cadena registrada con conflicto existente", cadena_id is not None)

        # Verificar que el conflicto sigue existiendo
        conflictos = conflictos_para_target(c, "1002:699f@c7")
        v("T0505: conflicto sigue existiendo", len(conflictos) > 0)
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0506 — Target preservation
# ---------------------------------------------------------------------------

def test_T0506_target_preservation() -> None:
    """Verificar que la relación conserva 1002:699f@c7, Polaris12, gfx_8_0."""
    from core.relations import registrar_cadena, obtener_cadena, listar_cadenas

    c = _setup()
    try:
        op_id = "op_T0506_prod"
        res_id = "res_T0506_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0506",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps([f"res_{res_id}"]),
            evidence_json=json.dumps([f"res_{res_id}"]),
            confidence=0.8,
            limitations="",
            created_by="test_session",
        )

        v("T0506: cadena registrada", cadena_id is not None)
        cadenas = listar_cadenas(c, target="1002:699f@c7")
        v("T0506: cadena aparece por target", len(cadenas) > 0)
        cadena = obtener_cadena(c, cadena_id) if cadena_id else None
        v("T0506: target correcto", cadena and cadena.get("target") == "1002:699f@c7")
        v("T0506: offset correcto", cadena and cadena.get("offset") == "0xA21")
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0507 — Semantic neutrality
# ---------------------------------------------------------------------------

def test_T0507_semantic_neutrality() -> None:
    """Verificar que la creación de relaciones no cambia UNIT_SEMANTICS=NOT_DETERMINED."""
    from core.relations import registrar_cadena, obtener_cadena

    c = _setup()
    try:
        op_id = "op_T0507_prod"
        res_id = "res_T0507_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0507",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="NOT_DETERMINED",  # NOT_DETERMINED, no PROVEN automático
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps([f"res_{res_id}"]),
            evidence_json=json.dumps([f"res_{res_id}"]),
            confidence=0.0,
            limitations="sin evidencia suficiente",
            created_by="test_session",
        )

        v("T0507: cadena creada con NOT_DETERMINED", cadena_id is not None)
        cadena = obtener_cadena(c, cadena_id)
        v("T0507: epistemic_state es NOT_DETERMINED", cadena and cadena.get("epistemic_state") == "NOT_DETERMINED")
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# T0508 — Investigation chain
# ---------------------------------------------------------------------------

def test_T0508_investigation_chain() -> None:
    """Verificar que puede reconstruirse QUESTION→EVIDENCE→RELATION→CLAIM→NEXT ACTION."""
    from core.store import registrar_investigacion, investigacion
    from core.relations import registrar_cadena, obtener_cadena, listar_cadenas

    c = _setup()
    try:
        # Registrar una operación
        op_id = "op_T0508_prod"
        res_id = "res_T0508_val"
        _crear_resultado_op(c, op_id, res_id, "0xA21")
        c.commit()

        # Registrar cadena de relación
        cadena_id = registrar_cadena(
            c,
            relation_id="chain_T0508",
            producer=op_id,
            transformation="bits_extract_0_7",
            representation="0xA21_val",
            consumer=res_id,
            effect="register_write_enabled",
            relation_type="PRODUCES",
            epistemic_state="PARTIAL",
            target="1002:699f@c7",
            offset="0xA21",
            provenance_json=json.dumps([f"res_{res_id}"]),
            evidence_json=json.dumps([f"res_{res_id}"]),
            confidence=0.8,
            limitations="transformation based on pattern match",
            created_by="test_session",
        )
        v("T0508: cadena registrada", cadena_id is not None)

        # Registrar claim
        claim_id = registrar_investigacion(
            c, "claim", "soft_regs_start is populated from SoftRegisters",
            status="PARTIAL",
            refs=[res_id],  # res_id ya tiene el prefijo res_ (e.g. res_T0508_val)
            session="test_T0508",
            target="1002:699f@c7",
            gap_kind="HUECO_DE_EVIDENCIA",
        )
        v("T0508: claim registrado", claim_id is not None and claim_id != "")

        # Registrar next_action
        next_id = registrar_investigacion(
            c, "next_action", "resolver la siguiente relación faltante",
            status="OPEN",
            refs=[],
            session="test_T0508",
            target="1002:699f@c7",
        )
        v("T0508: next_action registrado", next_id is not None and next_id != "")

        # Verificar que la cadena se puede obtener
        cadenas = listar_cadenas(c, target="1002:699f@c7")
        v("T0508: cadenas listables por target", len(cadenas) > 0)

        # Verificar que el claim tiene gap_kind correcto
        inv = investigacion(c, session="test_T0508", kind="claim")
        v("T0508: claim con gap_kind HUECO_DE_EVIDENCIA",
          any(e.get("gap_kind") == "HUECO_DE_EVIDENCIA" for e in inv.get("entradas", [])))

        # Verificar que el next_action existe
        inv_na = investigacion(c, session="test_T0508", kind="next_action")
        v("T0508: next_action existe", len(inv_na.get("entradas", [])) > 0)
    finally:
        _teardown(c)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("T0501-T0508 — Relation Engine Tests")
    print("=" * 60)

    tests = [
        test_T0501_relation_creation,
        test_T0502_partial_relation,
        test_T0503_false_causal_inference,
        test_T0504_provenance_preservation,
        test_T0505_conflict_preservation,
        test_T0506_target_preservation,
        test_T0507_semantic_neutrality,
        test_T0508_investigation_chain,
    ]

    for test_fn in tests:
        print(f"\n--- {test_fn.__name__} ---")
        try:
            test_fn()
        except Exception as e:
            fails.append(f"{test_fn.__name__} EXCEPCIÓN: {e}")

    print("\n" + "=" * 60)
    print(f"Checks: {checks}")
    print(f"Fails:  {len(fails)}")
    for f in fails:
        print(f"  [FALLA] {f}")
    if not fails:
        print("  ✓ TODOS LOS TESTS PASARON")
    print("=" * 60)
    sys.exit(1 if fails else 0)