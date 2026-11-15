#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-RESEARCH-GATE: evaluación de propuestas antes de ejecución.

Estado: `DISEÑO IMPLEMENTADO BASICO` (PROVEN por referencia al contrato
`RESEARCH_GATE_DESIGN_004.md`; NO integrado en flujo de producción hasta
`RESEARCH_GATE_INTEGRATION_006.md`; `DEBUGFS`/`MMIO`/`sudo` no usados).

Responsabilidad separada de `operational_gate` (`backends/gate.py`).
Este módulo decide si una propuesta de investigación avanza (AVAILABLE),
quede bloqueada (BLOCKED), rechazada (REJECTED) o indeterminada
(NOT_DETERMINED) según evidencia nueva, discriminante, preregistro,
acceso viable y referencias a vías cerradas.

No modifica DB, mecanismo MMR, `PUBLISHED_VERIFIED`, pre-registros ni
resultados protegidos (PROVEN por diseño y por ausencia de código de
persistencia en este archivo).
"""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

# Referencia al contrato: audit/debugfs/RESEARCH_GATE_DESIGN_004.md
# Repo raiz: subir hasta que exista audit/ (evidencias como 058/001/004/010).
def _repo_raiz() -> str:
    cur = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "audit")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return cur

REPO = _repo_raiz()

# Regla de admisión 012: requisitos ejecutables del contrato (§1.2, req 7).
# Cada requisito es una condición necesaria para que el veredicto sea
# `AVAILABLE`; si alguno falla, el veredicto NO puede ser `AVAILABLE` y la
# ejecución queda bloqueada (fail-closed).
REQUISITOS_ADMISION = (
    ("contrato_completo", "los 7 campos del contrato presentes y tipados"),
    ("evidencia_nueva", "evidencia_nueva == True"),
    ("evidencia_verificable", "cada evidencia_ref existe y su sha256 coincide"),
    ("discriminativa", "discriminativa == True"),
    ("preregistrada", "preregistrada == True"),
    ("acceso_viable", "acceso_viable == True"),
)

# Registro mínimo de vías cerradas (puede extenderse sin tocar código de
# ejecución; referencia a contratos de cierre como 055/058/002).
VIAS_CERRADAS: Dict[str, Dict[str, List[str]]] = {
    "indicador_sysfs": {"closure_refs": [
        "audit/debugfs/POWER_SENSOR_SEMANTICS_055.md"]},
    "ppt_sysfs": {"closure_refs": [
        "audit/debugfs/PPT_DISCRIMINATION_056.md",
        "audit/debugfs/PPT_RESULT_RECONCILIATION_057.md",
        "audit/debugfs/PPT_INVESTIGATION_CLOSURE_058.md"]},
    "mmr_read": {"closure_refs": [
        "audit/debugfs/SMU_STATICAL_VALIDATION_054.md"]},
}


def _sha256(p: str) -> Optional[str]:
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _vacia_sustentada(propuesta: Dict[str, Any],
                       vias_cerradas: Dict[str, Dict[str, List[str]]] = None,
                       raiz: str = REPO) -> bool:
    """Regla de sustanciación (diseño 004 / 005, resolución de ambigüedad)."""
    if vias_cerradas is None:
        vias_cerradas = VIAS_CERRADAS
    if not propuesta.get("evidencia_nueva"):
        return False
    refs = list(propuesta.get("evidencia_ref") or [])
    if not refs:
        return False
    via = propuesta.get("via", "")
    cerrada = vias_cerradas.get(via)
    cierre_refs = set(cerrada["closure_refs"]) if cerrada else set()
    nuevas = [r for r in refs if r not in cierre_refs]
    if not nuevas:
        return False
    hashes = propuesta.get("evidencia_hash") or {}
    for r in nuevas:
        esperado = hashes.get(r)
        if esperado is None:
            return False
        real = _sha256(os.path.join(raiz, r))
        if real is None or real != esperado:
            return False
    return True


def evaluar(propuesta: Dict[str, Any],
            vias_cerradas: Dict[str, Dict[str, List[str]]] = None,
            raiz: str = REPO) -> Dict[str, Any]:
    """Evaluación del contrato del Research Gate (PROVEN por referencia 004).

    No lanza excepciones al llamador (seguridad del gate): cualquier error
    interno se envuelve como NOT_DETERMINED explícito, sin ejecutar adapter.
    """
    try:
        return _evaluar(propuesta, vias_cerradas, raiz)
    except Exception as e:
        return {
            "estado": "NOT_DETERMINED",
            "motivo": "error interno del gate: %s: %s" % (type(e).__name__, e),
            "evidencia_ref": propuesta.get("evidencia_ref") or [],
            "referencia_via_cerrada": propuesta.get("referencia_via_cerrada") or None,
            "recomendacion": "requiere revision del gate",
        }


def _evaluar(propuesta, vias_cerradas, raiz):
    # 1) contrato inválido → NOT_DETERMINED
    campos = ("propuesta_id", "via", "evidencia_nueva", "evidencia_ref",
              "discriminativa", "preregistrada", "acceso_viable")
    if not isinstance(propuesta, dict):
        return _v("NOT_DETERMINED", "propuesta no es diccionario")
    faltan = [c for c in campos if c not in propuesta]
    if faltan:
        return _v("NOT_DETERMINED", "contrato invalido: faltan campos %s" % ",".join(faltan))
    for c in ("evidencia_nueva", "discriminativa", "preregistrada", "acceso_viable"):
        if not isinstance(propuesta.get(c), bool):
            return _v("NOT_DETERMINED", "contrato invalido: %s no es booleano" % c)
    if not isinstance(propuesta.get("evidencia_ref"), list):
        return _v("NOT_DETERMINED", "contrato invalido: evidencia_ref no es lista")

    via = propuesta.get("via", "")
    cerrada = (vias_cerradas or VIAS_CERRADAS).get(via)
    referencia_cerrada = propuesta.get("referencia_via_cerrada") or (via if cerrada else None)
    sustentada = _vacia_sustentada(propuesta, vias_cerradas or VIAS_CERRADAS, raiz)

    # 2) vía cerrada sin evidencia nueva sustentada → REJECTED
    if referencia_cerrada and not sustentada:
        return _v("REJECTED",
                  "vía cerrada (%s) sin evidencia discriminante nueva sustentada" % referencia_cerrada,
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []))

    # 3) acceso no viable → BLOCKED
    if not propuesta.get("acceso_viable"):
        return _v("BLOCKED",
                  "acceso no viable: la vía no puede ejecutarse ahora",
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []))

    # 4) evidencia insuficiente → NOT_DETERMINED (requiere evidencia_nueva yes per 004 §1.2)
    if not propuesta.get("evidencia_nueva"):
        return _v("NOT_DETERMINED",
                  "falta evidencia nueva declarada (evidencia_nueva == False): el contrato exige evidencia_nueva == True",
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []))
    if not propuesta.get("discriminativa"):
        return _v("NOT_DETERMINED",
                  "evidencia no discriminante: el criterio no puede pasar",
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []))
    if not propuesta.get("preregistrada"):
        return _v("NOT_DETERMINED",
                  "sin preregistro: no hay criterio fijado para validar",
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []))

    # 5) AVAILABLE: exige procedencia verificable (requisito 7 del contrato)
    verif, motivo_ev = _evidencia_verificada(propuesta, raiz)
    if not verif:
        return _v("NOT_DETERMINED",
                  "evidencia no verificable: %s" % motivo_ev,
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []),
                  evidencia_verificada=False)
    if not propuesta.get("evidencia_ref"):
        return _v("NOT_DETERMINED",
                  "AVAILABLE sin procedencia: evidencia_ref vacío",
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=[])
    if referencia_cerrada:
        return _v("AVAILABLE",
                  "vía cerrada (%s) reabierta con evidencia nueva discriminante" % referencia_cerrada,
                  referencia_cerrada=referencia_cerrada,
                  evidencia_ref=list(propuesta.get("evidencia_ref") or []),
                  evidencia_verificada=True)
    return _v("AVAILABLE",
              "propuesta con evidencia nueva discriminante, preregistrada y acceso viable",
              referencia_cerrada=None,
              evidencia_ref=list(propuesta.get("evidencia_ref") or []),
              evidencia_verificada=True)


def _evidencia_verificada(propuesta: Dict[str, Any], raiz: str = REPO) -> tuple:
    """Verifica que todas las referencias tengan archivo real y hash coincidente.
    Devuelve (True, "") si todo coincide; (False, motivo) si hay error."""
    refs = list(propuesta.get("evidencia_ref") or [])
    if not refs:
        return False, "evidencia_ref vacio"
    hashes = propuesta.get("evidencia_hash") or {}
    for r in refs:
        esperado = hashes.get(r)
        if esperado is None:
            return False, "sin sha256 declarado para %s" % r
        real = _sha256(os.path.join(raiz, r))
        if real is None:
            return False, "artefacto de evidencia ausente: %s" % r
        if real != esperado:
            return False, "sha256 no coincide para %s" % r
    return True, ""


def _v(estado: str, motivo: str, referencia_cerrada: Optional[str] = None,
       evidencia_ref: Optional[List[str]] = None,
       evidencia_verificada: bool = False) -> Dict[str, Any]:
    return {
        "estado": estado,
        "motivo": motivo,
        "evidencia_ref": evidencia_ref or [],
        "referencia_via_cerrada": referencia_cerrada,
        "evidencia_verificada": evidencia_verificada,
        "recomendacion": {
            "AVAILABLE": "ejecutar",
            "BLOCKED": "bloquear",
            "REJECTED": "rechazar",
            "NOT_DETERMINED": "requiere evidencia nueva",
        }.get(estado, "requiere revision del gate"),
    }


def permitir_ejecucion(veredicto: Any) -> bool:
    """¿El veredicto permite ejecutar un adapter? Solo AVAILABLE bien formado y verificado."""
    if not isinstance(veredicto, dict):
        return False
    if veredicto.get("estado") != "AVAILABLE":
        return False
    if not veredicto.get("motivo"):
        return False
    if not veredicto.get("evidencia_ref"):
        return False
    # 012: AVAILABLE debe exigir procedencia verificable (req 7)
    if veredicto.get("evidencia_verificada") is not True:
        return False
    return True


# ---------------------------------------------------------------------------
# Helpers de integración común (sin duplicar lógica de decisión)
# ---------------------------------------------------------------------------

def veredicto_de(contenedor: Any) -> Dict[str, Any]:
    """Devuelve el veredicto del gate si el contenedor contiene una propuesta
    formal declarada bajo la clave 'investigacion'.

    Si NO hay propuesta formal, retorna un veredicto neutro 'SIN_PROPUESTA'
    que NO bloquea la ejecución. Esto permite que las operaciones operativas
    sigan su curso sin modificación.
    """
    if not isinstance(contenedor, dict):
        return {"estado": "SIN_PROPUESTA", "motivo": "contenedor no es diccionario"}
    if "investigacion" not in contenedor:
        return {"estado": "SIN_PROPUESTA", "motivo": "no hay propuesta formal declarada"}
    prop = contenedor.get("investigacion")
    # 012: propuesta declarada pero malformada / incompleta → NOT_DETERMINED (fail-closed).
    # Solo cuando no hay clave `investigacion` se conserva SIN_PROPUESTA (operativo).
    if not isinstance(prop, dict) or not prop:
        return _v("NOT_DETERMINED",
                  "propuesta formal declarada pero incompleta o malformada: requiere contrato completo",
                  evidencia_ref=[])
    return evaluar(prop)


def bloquear_ejecucion(veredicto: Any) -> bool:
    """True si la ejecución debe bloquearse (fail-closed).

    - 'SIN_PROPUESTA': no bloquea (operación normal).
    - 'AVAILABLE': no bloquea (propuesta admitida).
    - 'REJECTED', 'BLOCKED', 'NOT_DETERMINED': bloquea.
    - Errores de contrato o internos -> NOT_DETERMINED -> bloquea.
    """
    if not isinstance(veredicto, dict):
        return True  # fail-closed ante veredicto inesperado
    estado = veredicto.get("estado")
    if estado == "SIN_PROPUESTA":
        return False
    return not permitir_ejecucion(veredicto)


def respuesta_bloqueo(veredicto: Any, capability: str = None) -> Dict[str, Any]:
    """Envelope de respuesta estándar para un bloqueo por Research Gate."""
    if not isinstance(veredicto, dict):
        veredicto = {"estado": "NOT_DETERMINED", "motivo": "veredicto inválido"}
    estado = veredicto.get("estado", "NOT_DETERMINED")
    return {
        "status": "blocked",
        "capability": capability,
        "ejecutada": False,
        "motivo": "RESEARCH-GATE: %s (%s)" % (estado, veredicto.get("motivo", "")),
        "regla": "research-gate",
        "research_gate": veredicto,
        "results": [],
        "next_actions": [],
    }
