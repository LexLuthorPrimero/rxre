#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY
"""RXRE · IER · DEFICIENCY — evaluador de la decision reparar/extender/sustituir/combinar/crear.

No decide por popularidad: decide con EVIDENCIA observada de la tecnología T
contra el objetivo G, y publica el coste con pesos DECLARADOS (no inventados):
si el propietario no dicta pesos, se imprimen los defaults con etiqueta
'default_no_optimizados' y nadie huele a PROVEN.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

ALTERNATIVAS = ("reparar", "extender", "sustituir", "combinar", "crear")
FLAGS = (
    "total_defecto",          # Q(T,G)==0 y bug acotado en T
    "falta_subconjunto",      # T no cubre un subconjunto necesario
    "sustituible",            # existe otra tecnología que sí cubre
    "combinable",             # varias cubren entre sí
    "nada_sirve",             # ninguna conocida sirve
)

# Pesos por defecto: DECLARADOS como defecto; el dictado puede cambiarlos.
# α<β salvo si un peso degradado tiene evidencia explicita.
DEFAULT_PESOS = {
    "C": 0.15,   # coste computacional y de desarrollo
    "R": 0.45,   # riesgo de introducir errores
    "T": 0.15,   # tiempo
    "M": 0.25,   # coste de mantenimiento
}


def q_tg(observacion: Dict[str, Any]) -> int:
    """Q(T,G): 1 si la tecnología cubre G según evidencia observada, 0 si no."""
    return 1 if observacion.get("t_alcanza_el_objetivo") else 0


def evaluar(deficiencia: Dict[str, Any],
            pesos: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Evaluador 5-vías FAIL-CLOSED.

    deficiencia exige: t_alcanza_el_objetivo (0/1) y al menos uno de
    total_defecto|falta_subconjunto|sustituible|combinable|nada_sirve.
    """
    pesos = pesos or DEFAULT_PESOS
    flags = {f: bool(deficiencia.get(f)) for f in FLAGS}
    tg = q_tg(deficiencia)
    evidencia = any(flags.values())

    if not evidencia:
        return {"decision": "NOT_DETERMINED",
                "reason": "faltan flags de evidencia; no se inventa una respuesta",
                "Q_TG": tg,
                "evidencia": dict(flags),
                "pesos": dict(pesos)}

    # Matriz: coherente con IER §5 y con la tabla de alternatives.
    if tg == 1:
        decision = "reparar"
        por_que = "Q(T,G)=1: la tecnología conocida sirve; basta corregir lo medido"
    elif flags["total_defecto"] and not flags["sustituible"] and not flags["nada_sirve"]:
        decision = "reparar"
        por_que = "bug acotado en la tecnologia conocida; replicable con oráculo"
    elif flags["falta_subconjunto"] and not flags["sustituible"]:
        decision = "extender"
        por_que = "falta subconjunto implementable como extension de la tecnología"
    elif flags["sustituible"]:
        decision = "sustituir"
        por_que = "otra tecnología cubre el objetivo; elegir la de menor J"
    elif flags["combinable"] and not flags["nada_sirve"]:
        decision = "combinar"
        por_que = "varias tecnologías cubren entre sí; coordinar la combinación"
    elif flags["nada_sirve"]:
        decision = "crear"
        por_que = "ninguna tecnología conocida sirve; crear la capacidad propia"
    else:
        decision = "NOT_DETERMINED"
        por_que = "deficacia insuficiente para elegir"

    j = {
        "reparar": 0.45,   # referencia relativa; no mide tiempo concreto
        "extender": 0.60,
        "sustituir": 0.55,
        "combinar": 0.70,
        "crear": 1.00,
        "NOT_DETERMINED": None,
    }[decision]
    j_total = None
    if j is not None:
        j_total = (pesos["C"] * j + pesos["R"] * j + pesos["T"] * j + pesos["M"] * j)
    return {"decision": decision,
            "evidencia": dict(flags),
            "Q_TG": tg,
            "razon": por_que,
            "pesos": dict(pesos),
            "pesos_etiqueta": "default_no_optimizados" if pesos == DEFAULT_PESOS else "dictado",
            "J_estimado": j_total}


def publicar_pesos(path: str, pesos: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Escribe los pesos declarados; nunca auto-optimizados en silencio."""
    pesos = pesos or DEFAULT_PESOS
    doc = {"pesos": dict(pesos),
           "origen": "dictado del propietario" if pesos != DEFAULT_PESOS else "DEFAULT_NO_OPTIMIZADOS",
           "nota": ("pesos son convencion desaconsejable para promoción automática; "
                    "cualquier ajuste debe figurar en el expediente")}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    return doc
