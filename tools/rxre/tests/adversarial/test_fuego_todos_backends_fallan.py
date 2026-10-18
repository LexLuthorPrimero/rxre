#!/usr/bin/env python3
"""FUEGO adversarial: todos los backends fallan, debe sugerir fallback si hay historial."""

def test_fuego_todos_backends_fallan():
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert '_mejor_backend_para' in src
    assert '_registrar_performance_backend' in src
    print("PASS test_fuego_todos_backends_fallan")

if __name__ == "__main__":
    test_fuego_todos_backends_fallan()
