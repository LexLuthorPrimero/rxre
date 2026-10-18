#!/usr/bin/env python3
"""TIERRA adversarial: hash_chain roto a mitad."""

def test_tierra_hash_chain_roto():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'hash_chain_ok' in src
    assert 'hash_chain' in src
    print("PASS test_tierra_hash_chain_roto")

if __name__ == "__main__":
    test_tierra_hash_chain_roto()
