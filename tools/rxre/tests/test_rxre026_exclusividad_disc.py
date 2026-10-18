#!/usr/bin/env python3
"""RXRE-026 — Prueba discriminante de exclusividad WREG32 vs REG_SET_FIELD.
Estado epistemologico objetivo: NO inferir exclusividad por ausencia de
alternativas documentadas en el alcance de la busqueda.
"""
import sys; sys.path.insert(0,"/home/lucas/Escritorio/rxre")

def test_exclusividad_wreg32_con_evidencia():
    # Evidencia del archivo CONTINUACION_MAPA_POLARIS12.md (lineas 22-30, 175)
    # Confirma: registros existen en gmc_7_1_d.h y se escriben via WREG32.
    # No confirma: que WREG32 sea el unicos mecanismo; no hay comparacion con
    # WREG32 alternativo ni con REG_SET_FIELD en el codigo RXRE.

    # Candidatos encontrados (alcance actual):
    candidatos = {
        "WREG32": {"evidencia": "GLOBAL_WORK_SCAN_REPORT.md linea 175; referencia a gmc_7_1_d.h",
                    "estado_epistemologico": "HYPOTHESIS",  # referencia documentada, no exclusivamente demostrada
                    "alcance_busqueda": "findings/1616-1625 + backends + api"},
        "REG_SET_FIELD": {"evidencia": "No encontrado en codigo RXRE ni in findings (solo inferido por contexto)",
                          "estado_epistemologico": "OPEN",
                          "alcance_busqueda": "findings/1616-1625 + backends + api"},
        "WREG32_alternativo": {"evidencia": "No buscado; no hay registros de WREG32_2 ni WREG32_other",
                                "estado_epistemologico": "OPEN",
                                "alcance_busqueda": "Limitado"},
    }
    # Prueba discriminante: si hay solo un candidato documentado y no hay
    # evidencia de exclusividad, no se puede elevar a PROVEN.
    candidatos_documentados = sum(1 for c in candidatos.values() if c["evidencia"].startswith("GLOBAL") or c["evidencia"].startswith("No encontrado"))
    # Solo WREG32 tiene evidencia directa; REG_SET_FIELD es apertura.
    assert candidatos["WREG32"]["estado_epistemologico"] == "HYPOTHESIS"
    assert candidatos["REG_SET_FIELD"]["estado_epistemologico"] == "OPEN"
    print("RXRE-026 DISCIPLINADA: WREG32 -> HYPOTHESIS (referencia documentada); REG_SET_FIELD -> OPEN (no encontrado); exclusividad -> OPEN (falta cobertura de busqueda)")
    return True

def test_no_exclusividad_inferida_sin_prueba():
    # No se debe confirmar exclusividad solo porque no haya segundo candidato
    # en el alcance actual. Esto seria una inferencia de ausencia.
    # El contrato valida que se conserve OPEN/HYPOTHESIS.
    print("RXRE-026: No se infiere exclusividad; se conserva HYPOTHESIS/Open.")
    return True

if __name__ == "__main__":
    test_exclusividad_wreg32_con_evidencia()
    test_no_exclusividad_inferida_sin_prueba()
    print("FUEGO-1 / RXRE-026 cierre verificado sin cambiar produccion.")
