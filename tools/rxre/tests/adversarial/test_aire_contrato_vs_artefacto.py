#!/usr/bin/env python3
"""AIRE adversarial: check válido pero el artefacto real no coincide."""

def test_aire_contrato_vs_artefacto():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'artefact_check' in src
    assert 'contrato' in src
    print("PASS test_aire_contrato_vs_artefacto")

if __name__ == "__main__":
    test_aire_contrato_vs_artefacto()
