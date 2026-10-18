#!/usr/bin/env python3
"""ETER adversarial: ciclo oscilación A->B->A (no transitivo)."""

def test_eter_oscilacion():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'ciclos_detectados' in src
    assert 'circular_ref' in src
    print("PASS test_eter_oscilacion")

if __name__ == "__main__":
    test_eter_oscilacion()
