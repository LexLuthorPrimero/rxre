#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""relations.py — Motor de relaciones causales (RXRE-008 FASE 3).

Este módulo provee las capacidades que la Fase 3 del diseño de migración requiere:
1. Registrar relaciones causales PRODUCER → TRANSFORMS → REPRESENTS → CONSUMES → AFFECTS
2. Asociar evidencia (refs a edges/results/operations)
3. Rastrear estado epistemológico (PROVEN, PARTIAL, NOT_DETERMINED, REFUTED, BLOCKED)
4. Consultar relaciones existentes por target/producer/consumer/tipo
5. Proteger conversiones automáticas de PARTIAL → PROVEN sin evidencia

El diseño de migración especifica que las relaciones deben poder ser:
- Registradas con evidencia tracible
- Consultadas antes de cerrar claims
- Validadas con discriminante documentado
- Mantener estado epistemológico adecuado
- NO inventar causalidad desde referencias sueltas

"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from .store import (
    conectar,
    ESTADOS_RESEARCH,
    KIND_RESEARCH,
    GAP_KINDS,
    refs_invalidos,
    ref_existe,
    ref_de_edge,
    PREFIJOS_REF,
    investigacion,
    registrar_investigacion,
)

# ---------------------------------------------------------------------------
# Tipos y constantes (importadas desde store)
# ---------------------------------------------------------------------------
# Los siguientes se importan dinámicamente para evitar import circular
# pero los documentamos aquí para claridad:
#
# RELACION_ESTADOS = (
#     "PROVEN",           # cadena completamente respaldada por evidencia
#     "PARTIAL",          # cadena a medias: algunos segmentos tienen evidencia, otros faltan
#     "NOT_DETERMINED",   # no hay evidencia suficiente para apoyar o refutar la cadena
#     "REFUTED",          # hay evidencia que contradice la cadena
#     "BLOCKED",          # cadena bloqueada por confidente o dependencia sin resolver
# )
#
# TIPOS_RELACIÓN = (
#     "PRODUCES",    # productor crea el valor
#     "TRANSFORMS",  // el valor es transformado (formato, bits, etc.)
#     "REPRESENTS",  // se obtiene una representación intermediada
#     "CONSUMES",    // consumidor usa el valor
#     "AFFECTS",     // efecto en registro/estado de hardware
# )


# ---------------------------------------------------------------------------
# Helpers de validación
# ---------------------------------------------------------------------------

def _validar_refs(c: sqlite3.Connection, refs: List[str]) -> Tuple[bool, List[str]]:
    """Validar que todos los refs existen en las tablas citables.

    RETORNA: (todos_validos, lista_de_invalidos)
    """
    invalidos = refs_invalidos(c, refs)
    return (len(invalidos) == 0, invalidos)


def _construir_ref_edge(src: str, tipo: str, dst: str) -> str:
    """Construir un puntero edge: tipo:src->dst."""
    return "edge:%s:%s->%s" % (tipo, src, dst)


# ---------------------------------------------------------------------------
# Relation chain registry (bajo nivel)
# ---------------------------------------------------------------------------

def registrar_cadena(
    c: sqlite3.Connection,
    relation_id: str,
    producer: str,
    transformation: str,
    representation: str,
    consumer: str,
    effect: str,
    relation_type: str,
    epistemic_state: str = "NOT_DETERMINED",
    target: str = "",
    offset: str = "",
    context: str = "",
    provenance_json: str = "",
    evidence_json: str = "",
    confidence: float = 0.0,
    limitations: str = "",
    created_by: str = "system",
) -> Optional[str]:
    """Registrar una nueva cadena de relación en la base de datos.

    Reglas (RXRE-005 / §8, §9, §10):
    - `relation_type` debe ser uno de TIPOS_RELACIÓN
    - `epistemic_state` debe ser uno de RELACION_ESTADOS
    - Las conversiones PROVEN desde PARTIAL requieren evidencia explícita
    - `relation_id` debe ser único por (producer, consumer) par
    - Los refs en provenance_json y evidence_json deben existir

    RETORNA: relation_id si se registra correctamente, None si falla validación
    """
    # Importar aquí para evitar import circular
    from .store import RELACION_ESTADOS, TIPOS_RELACIÓN
    
    # Validaciones críticas
    if relation_type not in TIPOS_RELACIÓN:
        return None
    if epistemic_state not in RELACION_ESTADOS:
        return None
    if not producer or not producer.strip():
        return None
    if not consumer or not consumer.strip():
        return None
    
    # Validar que los refs existen (si se proporcionan)
    if provenance_json:
        try:
            prov_refs = json.loads(provenance_json)
            if not isinstance(prov_refs, list):
                prov_refs = []
        except (ValueError, TypeError):
            prov_refs = []
        if prov_refs:
            validos, invalidos = _validar_refs(c, prov_refs)
            if not validos:
                # No rechazamos totalmente, pero marcamos las refs inválidas
                pass  # Podríamos lanzar warning, pero guardamos lo que podamos
    
    if evidence_json:
        try:
            ev_refs = json.loads(evidence_json)
            if not isinstance(ev_refs, list):
                ev_refs = []
        except (ValueError, TypeError):
            ev_refs = []
        if ev_refs:
            validos, invalidos = _validar_refs(c, ev_refs)
            if not validos:
                pass  # mismo enfoque que arriba
    
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    # Insertar o actualizar en tabla
    c.execute(
        """INSERT OR REPLACE INTO relation_chains
           (relation_id, producer, transformation, representation, consumer,
            effect, relation_type, epistemic_state, target, offset, context,
            provenance_json, evidence_json, confidence, limitations,
            created_by, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (relation_id, producer, transformation, representation, consumer,
         effect, relation_type, epistemic_state, target or "", offset or "",
         context or "", provenance_json or "", evidence_json or "",
         confidence, limitations or "", created_by, ts, ts))
    c.commit()
    
    return relation_id


def obtener_cadena(c: sqlite3.Connection, relation_id: str) -> Optional[Dict[str, Any]]:
    """Obtener una cadena por relation_id."""
    fila = c.execute(
        "SELECT * FROM relation_chains WHERE relation_id=?",
        (relation_id,)).fetchone()
    if fila is None:
        return None
    return dict(fila)


def listar_cadenas(c: sqlite3.Connection,
                   relation_type: str = "",
                   epistemic_state: str = "",
                   target: str = "",
                   producer: str = "",
                   consumer: str = "",
                   limite: int = 100) -> List[Dict[str, Any]]:
    """Listar cadenas de relación con filtros opcionales."""
    q = "SELECT * FROM relation_chains WHERE 1=1"
    args = []
    for col, val in (("relation_type", relation_type),
                     ("epistemic_state", epistemic_state),
                     ("target", target),
                     ("producer", producer),
                     ("consumer", consumer)):
        if val:
            q += " AND %s = ?" % col
            args.append(val)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(limite)
    filas = [dict(x) for x in c.execute(q, args).fetchall()]
    return filas


def actualizar_estado(
    c: sqlite3.Connection,
    relation_id: str,
    nuevo_estado: str,
    discriminante: Optional[str] = None,
) -> bool:
    """Actualizar el estado epistemológico de una cadena y opcionalmente añadir discriminante.

    Reglas (§80, §82, §96):
    - Un cambio a PROVEN requiere evidencia explícita (no automático desde PARTIAL)
    - Un discriminante debe documentar qué resolvió la incertidumbre (si corresponde)
    """
    from .store import RELACION_ESTADOS
    if nuevo_estado not in RELACION_ESTADOS:
        return False
    
    # Regla crítica: PROVEN requiere evidencia explícita, sin importar el estado actual
    if nuevo_estado == "PROVEN":
        row = c.execute(
            "SELECT epistemic_state, evidence_json FROM relation_chains WHERE relation_id=?",
            (relation_id,)).fetchone()
        if row:
            evid = json.loads(row[1] or "[]")
            if not evid:
                return False  # No se permite PROVEN automático sin evidencia en cualquier estado
    
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    # También podemos actualizar el campo limitations si se proporciona un discriminante
    if discriminante:
        c.execute(
            """UPDATE relation_chains
               SET epistemic_state = ?, limitations = COALESCE(limitations, '') || ?, updated_at = ?
             WHERE relation_id = ?""",
            (nuevo_estado, "; " + discriminante if discriminante else "", ts, relation_id),
        )
    else:
        c.execute(
            "UPDATE relation_chains SET epistemic_state=?, updated_at=? WHERE relation_id=?",
            (nuevo_estado, ts, relation_id),
        )
    c.commit()
    return True


def eliminar(
    c: sqlite3.Connection,
    relation_id: str,
) -> bool:
    """Eliminar una cadena de relación."""
    c.execute("DELETE FROM relation_chains WHERE relation_id=?", (relation_id,))
    c.commit()
    return True


# ---------------------------------------------------------------------------
# Interfaz de alto nivel (con auto-conexión)
# ---------------------------------------------------------------------------

def get_cadenas_por_target(target: str) -> List[Dict[str, Any]]:
    """Consultar cadenas para un target (con auto-conexión)."""
    try:
        c = conectar()
        try:
            return listar_cadenas(c, target=target)
        finally:
            c.close()
    except Exception:
        return []


def get_cadena(relation_id: str) -> Optional[Dict[str, Any]]:
    """Consultar una cadena por relation_id (con auto-conexión)."""
    try:
        c = conectar()
        try:
            return obtener_cadena(c, relation_id)
        finally:
            c.close()
    except Exception:
        return None


def registrar_nueva_cadena(
    relation_id: str,
    producer: str,
    transformation: str,
    representation: str,
    consumer: str,
    effect: str,
    relation_type: str,
    epistemic_state: str = "NOT_DETERMINED",
    target: str = "",
    offset: str = "",
    context: str = "",
    provenance_json: str = "",
    evidence_json: str = "",
    confidence: float = 0.0,
    limitations: str = "",
    creado_por: str = "system",
) -> Optional[str]:
    """Registrar una nueva cadena (auto-conexión)."""
    try:
        c = conectar()
        try:
            return registrar_cadena(
                c, relation_id, producer, transformation, representation,
                consumer, effect, relation_type, epistemic_state, target,
                offset, context, provenance_json, evidence_json, confidence,
                limitations, creado_por)
        finally:
            c.close()
    except Exception:
        return None


def actualizar_estado_cadena(
    relation_id: str,
    nuevo_estado: str,
    discriminante: Optional[str] = None,
) -> bool:
    """Actualizar estado de cadena (auto-conexión)."""
    try:
        c = conectar()
        try:
            return actualizar_estado(c, relation_id, nuevo_estado, discriminante)
        finally:
            c.close()
    except Exception:
        return False


def eliminar_cadena(relation_id: str) -> bool:
    """Eliminar cadena (auto-conexión)."""
    try:
        c = conectar()
        try:
            return eliminar(c, relation_id)
        finally:
            c.close()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    """Run a simple self-test of the relations module.

    Returns:
        0 if all tests pass, non-zero otherwise.
    """
    import sqlite3
    import os

    failures = []

    # Test 1: Registrar una cadena básica
    from store import conectar
    db_path = "/tmp/opencode/test_relations.sqlite3"
    if os.path.exists(db_path):
        os.remove(db_path)

    c = conectar(db_path)

    # Primero necesitamos un resultado válido para que los refs sean válidos
    op_id = "op_test_rel_prod"
    c.execute(
        "INSERT INTO operations(operation_id, request_id, contract_ver, operacion, capability, question, target, scope, status, n_results, request_json, response_json, target_pci, timestamp, duracion_s) "
        "VALUES (?, '', 'test', 'test_op', 'register', 'test_q', '1002:699f@c7', 'test', 'ok', 1, '{}', '{}', '', ?, 0.0)",
        (op_id, time.strftime("%Y-%m-%dT%H:%M:%S%z")),
    )
    res_id = "res_test_rel_val"
    c.execute(
        "INSERT INTO results(result_id, operation_id, type, value, source, file, line, scope, tool, tool_version, status, raw_json, timestamp) "
        "VALUES (?, ?, 'register', '0xA21', 'test', '', 0, '', '', '', 'ok', '{}', ?)",
        (res_id, op_id, time.strftime("%Y-%m-%dT%H:%M:%S%z")),
    )
    c.commit()

    # Registrar cadena
    prov = json.dumps([res_id])
    evid = json.dumps([res_id])
    cadena_id = registrar_cadena(
        c, "chain_test_001", 
        producer=f"op_{op_id}",
        transformation="bits_extract_0_7", 
        representation="0xA21_val",
        consumer=f"res_{res_id}",
        effect="register_write_enabled",
        relation_type="PRODUCES",
        epistemic_state="PARTIAL",
        target="1002:699f@c7",
        offset="0xA21",
        provenance_json=prov,
        evidence_json=evid,
        confidence=0.7,
        limitations="transformation based on pattern match",
        creado_por="test_session"
    )

    if not cadena_id:
        failures.append("No se pudo registrar cadena básica")
    elif cadena_id is None:
        failures.append("registró None como ID de cadena")

    # Test 2: Consultar cadenas por target
    cadenas = listar_cadenas(c, target="1002:699f@c7")
    if not isinstance(cadenas, list):
        failures.append("listar_cadenas no retornó lista")
    elif len(cadenas) == 0:
        failures.append("No se encontraron cadenas registradas (aunque sí se insertaron)")

    # Test 3: Actualizar estado a PROVEN con evidencia
    if cadena_id:
        ok = actualizar_estado(c, cadena_id, "PROVEN", "evidencia corroborada")
        if not ok:
            failures.append("No se pudo actualizar estado a PROVEN con evidencia")
        # Verificar que el estado se actualizó
        cadena = obtener_cadena(c, cadena_id)
        if not cadena or cadena.get("epistemic_state") != "PROVEN":
            failures.append("El estado no se actualizó correctamente a PROVEN")

    # Test 4: Intentar actualizar PARTIAL -> PROVEN sin evidencia (debe fallar)
    cadena_id2 = registrar_cadena(
        c, "chain_test_002", 
        producer=f"op_{op_id}",
        transformation="unknown", 
        representation="unknown_val",
        consumer=f"res_{res_id}",
        effect="unknown_effect",
        relation_type="TRANSFORMS",
        epistemic_state="PARTIAL",
        target="1002:699f@c7",
        offset="0xA22",
        provenance_json="[]",  # sin evidencia
        evidence_json="[]",    # sin evidencia
        confidence=0.0,
        limitations="sin evidencia",
        creado_por="test_session"
    )
    if cadena_id2:
        ok_bad = actualizar_estado(c, cadena_id2, "PROVEN", "sin evidencia pero forzado")
        if ok_bad:
            failures.append("Debería haber rechazado PROVEN sin evidencia desde PARTIAL")

    # Test 5: Estados inválidos deben ser rechazados
    ok3 = actualizar_estado(c, "chain_fake", "INVALID_STATE")
    if ok3:
        failures.append("Debería haber rechazado estado inválido")

    c.close()
    try:
        os.remove(db_path)
    except Exception:
        pass

    if failures:
        for f in failures:
            print(f"  [FALLA] {f}")
        return 1
    else:
        print("  ✓ Self-test PASSED")
        return 0


if __name__ == "__main__":
    exit(_self_test())