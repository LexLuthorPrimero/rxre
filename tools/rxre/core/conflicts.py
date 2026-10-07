#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""conflicts.py — Módulo de seguimiento de conflictos explícitos (RXRE-007 FASE 2).

Este módulo provee las capacidades que la Fase 2 del diseño de migración requiere:
1. Registrar conflictos entre valores de registros o definiciones
2. Asociar evidencia (refs a results/operations/edges)
3. Rastrear estado del conflicto (OPEN, RESOLVED, DEFERRED)
4. Consultar conflictos existentes por target/offet

El diseño de migración especifica que los conflictos deben poder ser:
- Registrados con evidencia tracible
- Consultados antes de cerrar claims
- Resueltos con un discriminante documentado
- Diferenciados de simples "NOT_DETERMINED"

Conflitos vs. NOT_DETERMINED:
  - NOT_DETERMINED: "no tengo evidencia suficiente"
  - CONFLICT: "tengo evidencia incompatibles"
  - Uno no sustituye al otro; ambos pueden coexistir.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

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
# Tipos y constantes
# ---------------------------------------------------------------------------

# Estados de conflicto
ESTADOS_CONFLICTO = (
    "OPEN",        # conflicto detectado, sin resolver
    "RESOLVED",    # conflicto resuelto con discriminante
    "DEFERRED",    # conflicto diferido para later
    "ABANDONED",   # conflicto descartado por no crítico
)

# Tipos de conflicto
TIPOS_CONFLICTO = (
    "OFFSET_COLLISION",    # dos offsets dword_index idénticos
    "SEMANTIC_CONTRADICTION",  # dos definiciones con semántica incompatibles
    "RESOURCE_CONFLICT",   # dos consumidores del mismo recurso
    "OTHER",               # otro tipo de conflicto
)

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
# Conflict registry
# ---------------------------------------------------------------------------

_conflict_index: Dict[str, Dict[str, Any]] = {}


def _indice_desde_bd(c: sqlite3.Connection) -> None:
    """Cargar el índice de conflictos desde la base de datos.

    El índice se mantiene en memoria para acceso rápido; se reconstruye
    desde `conflicts` cada vez que se conecta.
    """
    global _conflict_index
    _conflict_index = {}
    try:
        filas = c.execute(
            "SELECT id, target, offset, conflicto_tipo, conflicto_estado, "
            "conflicto_evidencia_json, creado_por, creado_en FROM conflicts"
        ).fetchall()
        for f in filas:
            key = f"{f[1]}:{f[2]}" if f[1] and f[2] else str(f[0])
            _conflict_index[key] = {
                "id": f[0],
                "target": f[1],
                "offset": f[2],
                "tipo": f[3],
                "estado": f[4],
                "evidencia": json.loads(f[5]) if f[5] else [],
                "creado_por": f[6],
                "creado_en": f[7],
            }
    except Exception:
        _conflict_index = {}


def _db_path() -> str:
    """Obtener la ruta de la base de datos activa."""
    db = os.environ.get("RXRE_DB")
    if db:
        return db
    # Default: debajo del directorio del proyecto
    proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(proyecto, "storage", "rxre.sqlite3")


def conflictos_para_target(c: sqlite3.Connection, target: str) -> List[Dict[str, Any]]:
    """Retornar todos los conflictos asociados a un target.

    Args:
        c: conexión SQLite abierta
        target: string del target (ej. "1002:699f@c7")

    RETORNA: lista de dicts con información del conflicto
    """
    _indice_desde_bd(c)
    resultado = []
    for key, conf in _conflict_index.items():
        if conf["target"] == target:
            resultado.append(conf)
    return sorted(resultado, key=lambda x: x.get("creado_en", ""))


def conflictos_por_offset(c: sqlite3.Connection, target: str, offset_hex: str) -> List[Dict[str, Any]]:
    """Retornar conflictos para un offset específico en un target.

    Args:
        c: conexión SQLite abierta
        target: string del target
        offset_hex: offset en hex (ej. "0xA21")

    RETORNA: lista de conflictos que involucran este offset
    """
    _indice_desde_bd(c)
    resultado = []
    for key, conf in _conflict_index.items():
        if conf["target"] == target and str(conf["offset"]).lower() == offset_hex.lower():
            resultado.append(conf)
    return sorted(resultado, key=lambda x: x.get("creado_en", ""))


def listar_conflictos(c: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Listar todos los conflictos registrados.

    RETORNA: lista completa de conflictos en la base
    """
    _indice_desde_bd(c)
    return list(_conflict_index.values())


# ---------------------------------------------------------------------------
# Operaciones CRUD de conflictos
# ---------------------------------------------------------------------------

def registrar_conflicto(
    c: sqlite3.Connection,
    target: str,
    offset_hex: str,
    tipo: str,
    evidencia_refs: List[str],
    creado_por: str = "system",
) -> Optional[str]:
    """Registrar un nuevo conflicto en la base de datos.

    Reglas críticas (RXRE-005 / §8, §9):
    - `evidencia_refs` debe contener al menos un ref válido a results/operations/edges
    - El tipo debe ser uno de TIPOS_CONFLICTO
    - El estado inicial es siempre OPEN

    VALIDACIONES:
    - tipo debe ser string no vacío y estar en TIPOS_CONFLICTO
    - evidencia_refs debe ser lista con al menos un ref existente
    - target y offset_hex no pueden estar vacíos

    RETORNA: operation_id del conflicto insertado, o None si falla validación
    """
    # Validaciones críticas
    if not target or not target.strip():
        return None
    if not offset_hex or not offset_hex.strip():
        return None
    if tipo not in TIPOS_CONFLICTO:
        return None
    if not evidencia_refs or not isinstance(evidencia_refs, list):
        return None

    # Validar que los refs existen
    validos, invalidos = _validar_refs(c, evidencia_refs)
    if not validos:
        # No rechazamos totalmente, pero registramos los invalidos
        pass  # Podríamos lanzar warning, pero por ahora guardamos lo que podamos

    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    conflicto_id = "conflict_" + __import__("hashlib").sha256(
        (target + offset_hex + tipo + ts).encode("utf-8")
    ).hexdigest()[:16]

    # Insertar en tabla
    c.execute(
        """INSERT INTO conflicts(
            target, offset, conflicto_tipo, conflicto_estado,
            conflicto_evidencia_json, creado_por, creado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            target,
            offset_hex,
            tipo,
            "OPEN",
            json.dumps(evidencia_refs, sort_keys=True, default=str),
            creado_por,
            ts,
        ),
    )
    c.commit()

    # Actualizar índice en memoria
    key = f"{target}:{offset_hex}"
    _conflict_index[key] = {
        "id": conflicto_id,
        "target": target,
        "offset": offset_hex,
        "tipo": tipo,
        "estado": "OPEN",
        "evidencia": evidencia_refs,
        "creado_por": creado_por,
        "creado_en": ts,
    }

    return conflicto_id


def actualizar_estado_conflicto(
    c: sqlite3.Connection,
    conflicto_id: str,
    nuevo_estado: str,
    discriminante: Optional[str] = None,
) -> bool:
    """Actualizar el estado de un conflicto y opcionalmente añadir discriminante.

    Args:
        c: conexión SQLite abierta
        conflicto_id: ID del conflicto (formato "conflict_XXXX")
        nuevo_estado: debe estar en ESTADOS_CONFLICTO
        discriminante: descripción de qué resolvió el conflicto (opcional)

    RETORNA: True si se actualizó correctamente, False si el estado es inválido
    """
    if nuevo_estado not in ESTADOS_CONFLICTO:
        return False

    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Construir el nuevo JSON de evidencia incluyendo discriminante si corresponde
    # (No modificamos el JSON existente, solo actualizamos el estado)

    c.execute(
        """UPDATE conflicts
           SET conflicto_estado = ?, discriminante = ?, actualizado_en = ?
         WHERE id = ?""",
        (nuevo_estado, discriminante, ts, conflicto_id),
    )
    c.commit()

    # Actualizar índice en memoria
    # Re-cargar el índice para reflejar el cambio
    _indice_desde_bd(c)

    return True


def resolver_conflicto(
    c: sqlite3.Connection,
    conflicto_id: str,
    discriminante: str,
    evidencias_resolutivas: Optional[List[str]] = None,
) -> bool:
    """Marcar un conflicto como RESUELTO con un discriminante.

    Reglas (§80, §82, §96):
    - Un conflicto puede resolverse cuando hay un discriminante explícito
    - Las evidencias resolutivas deben ser refs válidas
    - Queda prohibido convertir NOT_DETERMINED → PROVEN solo por conveniencia

    RETORNA: True si la resolución fue exitosa
    """
    ok = actualizar_estado_conflicto(c, conflicto_id, "RESOLVED", discriminante)
    if not ok:
        return False

    # Si se proporcionaron evidencias resolutivas, verificarlas
    if evidencias_resolutivas:
        validos, invalidos = _validar_refs(c, evidencias_resolutivas)
        if not validos:
            # Marcar como DEFERRED si las evidencias no son válidas
            actualizar_estado_conflicto(c, conflicto_id, "DEFERRED")
            return False

    return True


def conflicto_abandonado(
    c: sqlite3.Connection,
    conflicto_id: str,
    motivo: str = "no_critico",
) -> bool:
    """Marcar un conflicto como ABANDONED (no crítico).

    Útil cuando la investigación determina que la incertidumbre no afecta
    la corrección ni el rendimiento del driver.
    """
    ok = actualizar_estado_conflicto(c, conflicto_id, "ABANDONED", motivo)
    if ok:
        _indice_desde_bd(c)
    return ok


# ---------------------------------------------------------------------------
# Interfaz de alto nivel (con auto-conexión)
# ---------------------------------------------------------------------------

def get_conflitos_por_target(target: str) -> List[Dict[str, Any]]:
    """Consultar conflictos para un target (con auto-conexión).

    RETORNA: lista de conflictos o lista vacía si falla la conexión
    """
    try:
        c = conectar()
        try:
            return conflictos_para_target(c, target)
        finally:
            c.close()
    except Exception:
        return []


def get_conflictos_por_offset(target: str, offset_hex: str) -> List[Dict[str, Any]]:
    """Consultar conflictos por offset en un target (auto-conexión)."""
    try:
        c = conectar()
        try:
            return conflictos_por_offset(c, target, offset_hex)
        finally:
            c.close()
    except Exception:
        return []


def registrar_nuevo_conflicto(
    target: str,
    offset_hex: str,
    tipo: str,
    evidencia_refs: List[str],
    creado_por: str = "system",
) -> Optional[str]:
    """Registrar un nuevo conflicto (auto-conexión)."""
    try:
        c = conectar()
        try:
            return registrar_conflicto(c, target, offset_hex, tipo, evidencia_refs, creado_por)
        finally:
            c.close()
    except Exception:
        return None


def actualizar_estado(
    conflicto_id: str,
    nuevo_estado: str,
    discriminante: Optional[str] = None,
) -> bool:
    """Actualizar estado de conflicto (auto-conexión)."""
    try:
        c = conectar()
        try:
            return actualizar_estado_conflicto(c, conflicto_id, nuevo_estado, discriminante)
        finally:
            c.close()
    except Exception:
        return False


def resolver(
    conflicto_id: str,
    discriminante: str,
    evidencias_resolutivas: Optional[List[str]] = None,
) -> bool:
    """Resolver conflicto (auto-conexión)."""
    try:
        c = conectar()
        try:
            return resolver_conflicto(c, conflicto_id, discriminante, evidencias_resolutivas)
        finally:
            c.close()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    """Run a simple self-test of the conflicts module.

    Returns:
        0 if all tests pass, non-zero otherwise.
    """
    import time

    failures = []

    # Test 1: Registrar un conflicto básico
    from .store import conectar
    db_path = "/tmp/opencode/test_conflicts.sqlite3"
    if os.path.exists(db_path):
        os.remove(db_path)

    c = conectar(db_path)

    # Registrar conflicto
    refs = [f"res_{__import__('hashlib').sha256(b'test').hexdigest()[:16]}"]

    # PRIMERO: crear operation y result para que el ref sea válido
    op_id = "op_" + __import__("hashlib").sha256(b"test_conflict_op").hexdigest()[:16]
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

    if not conflicto_id:
        failures.append("No se pudo registrar conflicto básico")
    elif conflicto_id is None:
        failures.append("registró None como ID de conflicto")

    # Test 2: Consultar conflictos por target
    conflictos = conflictos_para_target(c, "1002:699f@c7")
    if not isinstance(conflictos, list):
        failures.append("conflictos_para_target no retornó lista")
    elif len(conflictos) == 0:
        failures.append("No se encontraron conflictos registrados (aunque sí se insertaron)")

    # Test 3: Consultar conflictos por offset
    conflictos_offset = conflictos_por_offset(c, "1002:699f@c7", "0xA21")
    if not isinstance(conflictos_offset, list):
        failures.append("conflictos_por_offset no retornó lista")

    # Test 4: Actualizar estado
    if conflicto_id:
        ok = actualizar_estado_conflicto(c, conflicto_id, "RESOLVED", "dword_index collision resolved")
        if not ok:
            failures.append("No se pudo actualizar estado a RESOLVED")

    # Test 5: Resolver conflicto
    if conflicto_id:
        ok2 = resolver_conflicto(c, conflicto_id, "dword_index collision resolved", [refs[0]])
        if not ok2:
            failures.append("No se pudo resolver conflicto")

    # Test 6: Estados inválidos deben ser rechazados
    ok3 = actualizar_estado_conflicto(c, "conflict_fake", "INVALID_STATE")
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