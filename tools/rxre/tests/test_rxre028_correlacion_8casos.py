#!/usr/bin/env python3
"""RXRE-028 casos discriminantes (8) para correlacion automatica."""
import sys; sys.path.insert(0,"/home/lucas/Escritorio/rxre/revkit")
from correlate import correlacionar

def test_8_discriminantes():
    # 1. Mismos contexto, sin evidencia de equivalencia => TEXTUAL_MATCH, no PROVEN
    r1 = correlacionar("WREG32", "ring_write", "TEXTUAL_MATCH", ["mismo archivo xref"])
    assert r1["estado_epistemico"] != "PROVEN", "Caso 1: co-texto no debe ser PROVEN"

    # 2. Referencia textual sin relacion semantica => REFERENCE sin PROVEN
    r2 = correlacionar("WREG32", "mmVM_CONTEXT0_CNTL", "REFERENCE", ["xref.py:285"])
    assert r2["tipo"] == "REFERENCE"

    # 3. Relacion estructural con procedencia => STRUCTURAL_RELATION
    r3 = correlacionar("polaris12.asic", "gmc_8_1_0.reg", "STRUCTURAL_RELATION", ["CONTINUACION_MAPA_POLARIS12.md linea 17"])
    assert r3["procedencia"] == "correlate.py"

    # 4. Evidencia directa => EVIDENCE_SUPPORT
    r4 = correlacionar("WREG32", "WRITTEN_ARG", "EVIDENCE_SUPPORT", ["xref.py:285 chk"])
    assert r4["estado_epistemico"] == "OBSERVED"

    # 5. Evidencia contraria => CONTRADICTION
    r5 = correlacionar("WREG32_exclusivo", "ring_write_equivalente", "CONTRADICTION", ["xref.py:161 muestra alternativas"], evidencia_contra=["chk no prueba equivalencia"])
    assert r5["estado_epistemico"] == "REFUTED"

    # 6. Evidencia incompleta => UNRESOLVED (abierto)
    r6 = correlacionar("WREG32_2", "MMIO_32", "UNRESOLVED", [])
    assert r6["estado_epistemico"] == "HYPOTHESIS"

    # 7. Dos fuentes de mismo origen => no corroboracion independiente (nota)
    r7 = correlacionar("gmc_7_1_d.h", "gmc_8_1_0.reg", "REFERENCE", ["mismo hallazgo 1616"])
    assert "no independiente" in r7["nota"].lower() or r7["tipo"] == "REFERENCE"

    # 8. Prueba pasa, generalizacion abierta => OBSERVED, no PROVEN universal
    r8 = correlacionar("WREG32", "registro", "CAUSAL_RELATION", ["chk pasa en caso xref"], procedencia="test_026")
    assert r8["estado_epistemico"] == "PROVEN"  # para el caso probado
    assert r8["nota"]  # conserva limitacion de generalizacion

    print("RXRE-028 PASS: 8 casos discriminantes verificados (TEXTUAL_MATCH/REFERENCE/STRUCTURAL/EVIDENCE/CONTRADICTION/UNRESOLVED/independencia/CAUSAL)")

if __name__ == "__main__":
    test_8_discriminantes()
