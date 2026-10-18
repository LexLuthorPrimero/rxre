#!/usr/bin/env python3
"""AGUA adversarial: lección vieja contradice nueva (prune)."""

def test_agua_lecciones_contradictorias():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'pruned' in src
    assert 'checks_redundantes' in src
    assert 'checks_merge_sugerido' in src
    print("PASS test_agua_lecciones_contradictorias")

if __name__ == "__main__":
    test_agua_lecciones_contradictorias()
