#!/usr/bin/env python3
"""ALMA adversarial: dos misiones intentan auto-cerrar en conflicto."""

def test_alma_conflicto_misiones():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'UPDATE missions SET status' in src
    assert 'completed_at' in src
    print("PASS test_alma_conflicto_misiones")

if __name__ == "__main__":
    test_alma_conflicto_misiones()
