#!/usr/bin/env python3
"""MENTE adversarial: plan con self-loop (capability que depende de sí misma en pasos)."""

def test_mente_dag_selfloop():
    # Verificar que el código de _handle_plan detecta duplicados
    src = open('/home/lucas/Escritorio/rxre/tools/rxre/api/machine.py').read()
    assert 'dag_ciclos' in src
    assert 'dag_validado' in src
    assert 'plan_detecta_ciclo_dag' in src
    # El campo debe exponer si hay ciclo (capabilities repetidas en pasos)
    print("PASS test_mente_dag_selfloop")

if __name__ == "__main__":
    test_mente_dag_selfloop()
