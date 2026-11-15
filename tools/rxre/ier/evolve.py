#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY
"""RXRE · IER · EVOLVE — promotor bajo Triple Condicion ejecutable.

Una capacidad solo entra al registro STABLE (PROMOTED) si las TRES pasan:
  A. Correccion: el test que motivó la capacidad ha sido ejecutado y PASA.
  B. No regresion: baseline público no rompe (158/118/132/165/120).
  C. Compatibilidad: contratos previos intactos (interface, exit codes).

A efectos prácticos, promoción = dictado del propietario; este módulo
EXIGE dictado y nunca lo emite; produce un veredicto de candidatos.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def evaluacion_triple_condicion(capacidad: Dict[str, Any],
                                dictado_propietario: Optional[str]) -> Dict[str, Any]:
    """Evaluacion Triple Condicion. Devolver dictamen objetivo.

    No promociona automáticamente; dictado vacío => solo propuesta.
    """
    res = {}
    # A. Corrección: evidence obligatoriamente presente y PASADA
    ev = capacidad.get("evidencia", [])
    ev_pass = [e for e in ev if e.get("result") == "PASS"]
    res["correccion"] = {
        "evidencias_totales": len(ev),
        "evidencias_pass": len(ev_pass),
        "pasa": len(ev_pass) > 0,
    }
    # B. No regresión: la capacidad declara que baseline público sigue verde
    regression = capacidad.get("regression", {})
    res["no_regresion"] = dict(regression)
    # C. Compatibilidad: contratos intactos
    compat = capacidad.get("compatibility")
    res["compatibilidad"] = compat if isinstance(compat, dict) else {
        "presente": bool(compat)}

    # Veredicto fiinal honesto
    correccion_ok = res["correccion"]["pasa"]
    regression_ok = bool(res["no_regresion"].get("baseline_verde", False))
    compatibilidad_ok = bool(
        isinstance(res["compatibilidad"], dict)
        and bool(res["compatibilidad"].get("presente", False) is True))

    if dictado_propietario is None:
        veredicto = "PENDIENTE_DICTADO" if (correccion_ok and regression_ok and compatibilidad_ok) else "RECHAZO_POR_INSUFICIENTE"
    elif dictado_propietario.startswith("dictado"):
        if correccion_ok and regression_ok and compatibilidad_ok:
            veredicto = ("PROMOVED" if dictado_propietario == "dictado propietario"
                          else "PENDIENTE_DICTADO")
        else:
            veredicto = "RECHAZO_POR_INSUFICIENTE"
    else:
        veredicto = "RECHAZO_POR_INSUFICIENTE"

    # PASS PARTIAl documentado honesto: nunca más de PARTIAL sin dictado correcto
    if veredicto == "PROMOVED":
        veredicto = "PROMOTED"  # solo si todo arriba puntuó y dictado == exact
    return {"veredicto": veredicto,
            "correccion_ok": correccion_ok,
            "no_regresion_ok": regression_ok,
            "compatibilidad_ok": compatibilidad_ok,
            "detail": res}


def resumen_reporte(capacidad: Dict[str, Any],
                    dictado_propietario: Optional[str]) -> str:
    e = evaluacion_triple_condicion(capacidad, dictado_propietario)
    v = e["veredicto"]
    lineas = [
        "veredicto: %s" % v,
        "corrección: %s  evidencias %d/%d" % (e["correccion_ok"],
                                               e["detail"]["correccion"]["evidencias_pass"],
                                               e["detail"]["correccion"]["evidencias_totales"]),
        "regresión:    %s" % (e["no_regresion_ok"]),
        "compatibilidad: %s" % (e["compatibilidad_ok"]),
    ]
    if v == "PROMOTED":
        lineas.append("capability PROMOTED bajo dictado del propietario y Triple Condición")
    elif v == "PENDIENTE_DICTADO":
        lineas.append("propuesta lista para dictado; no se promociona sin autorización")
    else:
        lineas.append("promoción denegada: insuficientes condiciones o dictado incorrecto")
    return "\n".join(lineas)
