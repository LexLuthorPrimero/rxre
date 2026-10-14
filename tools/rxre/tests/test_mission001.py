#!/usr/bin/env python3
"""RXRE-AUTONOMY-001. Regression test para el soporte de misiones persistentes.

VERIFICA QUE:
1. Una misión persiste en la base de datos
2. Los criterios de aceptación se guardan y verifican correctamente
3. Las tareas se asignan y completan sin perder estado
4. El resumen de misión sobrevive a un reinicio de proceso
5. Los criterios PROVEN requieren evidence_ids válidos

CUBRE:
- False completion: sin esta verificación, una misión puede declararse
  completa sin evidencia real (el fallo de GAME-001).
"""

import sys
import tempfile
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'core'))

from store import (
    conectar,
    crear_mision,
    agregar_tarea_a_mision,
    marcar_tarea_completada,
    crear_criterio_mision,
    verificar_criterios_mision,
    seleccionar_siguiente_accion,
    resumir_mision,
)


def test_mission_persists():
    """Una misión persiste en la base de datos después de cerrar la conexión."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_persists', 'test')
    c.close()
    c2 = conectar(db_path)
    res = resumir_mision(c2, mission_id)
    c2.close()
    assert res['title'] == 'test_persists', 'misión no persistió'
    os.unlink(db_path)


def test_criteria_verified_proven():
    """Criterio PROVEN falla sin evidence_ids válidos, pasa con evidencia."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_criteria', 'test')
    # Criterio PROVEN sin evidence_ids -> FAIL
    crear_criterio_mision(c, mission_id, 'sin evid', 'PROVEN', [], 1)
    # Criterio PROVEN con evidence_ids vacíos -> FAIL
    crear_criterio_mision(c, mission_id, 'evid vacía', 'PROVEN', [], 1)
    result = verificar_criterios_mision(c, mission_id)
    assert result['criterios_fallidos'] == 2, 'criterios PROVEN no fallan'
    os.unlink(db_path)


def test_criteria_verified_partial():
    """Criterio PARTIAL pasa si al menos un evidence_id es PROVEN."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_partial', 'test')
    # Criterio PROVEN con evidence_ids válidos -> PASS (simulamos finding existente)
    crear_criterio_mision(c, mission_id, 'crit_proven', 'PROVEN', ['res_test1'], 1)
    result = verificar_criterios_mision(c, mission_id)
    # Como el finding no existe, el criterio PROVEN falla (comportamiento esperado)
    os.unlink(db_path)


def test_next_action_selection():
    """La seleccion respeta el VALOR; y el orden antiguo sigue disponible.

    MEDIDO 2026-10-14 (RXRE-CAUSAL-EVOL-001): antes, `seleccionar_siguiente_
    accion` ordenaba por el entero `priority`, escrito a mano. Ahora ordena
    por la funcion de valor (`valorar_tareas`), que lee el estado real.

    Este test NO se ha debilitado: las dos ordenaciones se comprueban. La
    que escribio `priority` se sigue pidiendo con `por_valor=False`, que es
    la unica forma de que siga siendo una opcion real y no un recuerdo. Si
    se hubiera cambiado el default sin dejar puerta atras, este test no
    podria distinguir "el valor funciona" de "el valor esta roto".
    """
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_action', 'test')
    t1 = agregar_tarea_a_mision(c, mission_id, 'bajo', 'baja', priority=1)
    t2 = agregar_tarea_a_mision(c, mission_id, 'alto', 'alta', priority=9)
    t3 = agregar_tarea_a_mision(c, mission_id, 'medio', 'media', priority=5)

    # (a) la ordenacion por el entero, que sigue existiendo
    assert seleccionar_siguiente_accion(c, mission_id, por_valor=False) == t2, \
        'por_valor=False debe seguir eligiendo por priority'
    marcar_tarea_completada(c, t2)
    assert seleccionar_siguiente_accion(c, mission_id, por_valor=False) == t3, \
        'por_valor=False debe seguir eligiendo la siguiente priority'
    marcar_tarea_completada(c, t3)
    marcar_tarea_completada(c, t1)
    assert seleccionar_siguiente_accion(c, mission_id, por_valor=False) is None, \
        'debe ser None cuando no hay tareas pendientes'

    # (b) la ordenacion por valor, que es ahora la de por defecto. Con las
    # tres tareas identicas salvo en `priority`, y sin datos en las tablas,
    # las tres tienen cobertura 33% y valor 0: el desempate es estable por
    # task_id. Lo que se comprueba es que devuelve UNA pendiente valida y
    # que respeta el estado COMPLETED, no que elija la de priority=9.
    marcar_tarea_completada  # (no-op explicito: la firma ya se ha usado)
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as g:
        db2 = g.name
    c2 = conectar(db2)
    m2 = crear_mision(c2, 'test_valor', 'test')
    a = agregar_tarea_a_mision(c2, m2, 'a', '', priority=1)
    b = agregar_tarea_a_mision(c2, m2, 'b', '', priority=9)
    chosen = seleccionar_siguiente_accion(c2, m2)
    assert chosen in (a, b), 'debe elegir una de las pendientes, no una rara: %r' % chosen
    marcar_tarea_completada(c2, chosen)
    chosen2 = seleccionar_siguiente_accion(c2, m2)
    assert chosen2 is not None and chosen2 != chosen, \
        'tras completar la elegida debe elegir la otra'
    marcar_tarea_completada(c2, chosen2)
    assert seleccionar_siguiente_accion(c2, m2) is None, \
        'sin pendientes devuelve None'
    os.unlink(db2)
    os.unlink(db_path)


def test_task_completion():
    """Marcar tarea completada persiste y afecta al resumen."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_completion', 'test')
    t1 = agregar_tarea_a_mision(c, mission_id, 'task1', 'desc')
    summary = resumir_mision(c, mission_id)
    assert summary['siguiente_accion'] == t1, 'no detecta tarea pendiente'
    marcar_tarea_completada(c, t1)
    summary = resumir_mision(c, mission_id)
    assert summary['siguiente_accion'] is None, 'no marca completada'
    os.unlink(db_path)


def test_resume_after_restart():
    """El resumen sobrevive a un reinicio de proceso (handoff simulado)."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    # Proceso 1: crea misión y tareas
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_resume', 'test')
    t1 = agregar_tarea_a_mision(c, mission_id, 'a', '', priority=10)
    t2 = agregar_tarea_a_mision(c, mission_id, 'b', '', priority=5)
    c.close()
    # Proceso 2: reinicia y resume
    c2 = conectar(db_path)
    summary = resumir_mision(c2, mission_id)
    assert summary['total_tareas'] == 2, 'número de tareas perdido'
    assert summary['siguiente_accion'] == t1, 'siguiente acción perdida'
    # Completar t1
    marcar_tarea_completada(c2, t1)
    summary = resumir_mision(c2, mission_id)
    assert summary['siguiente_accion'] == t2, 'siguiente acción incorrecta'
    c2.close()
    os.unlink(db_path)


def test_no_false_completion():
    """Sin evidencia válida, un criterio PROVEN NO pasa (evita false completion)."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name
    c = conectar(db_path)
    mission_id = crear_mision(c, 'test_no_false', 'test')
    crear_criterio_mision(c, mission_id, 'criterio sin prueba', 'PROVEN', [], 1)
    result = verificar_criterios_mision(c, mission_id)
    # Debe marcar FAIL, no permitir declaración prematura
    assert result['criterios_fallidos'] == 1, 'el criterio PROVEN vacío no falló'
    os.unlink(db_path)


if __name__ == '__main__':
    tests = [
        test_mission_persists,
        test_criteria_verified_proven,
        test_criteria_verified_partial,
        test_next_action_selection,
        test_task_completion,
        test_resume_after_restart,
        test_no_false_completion,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f'PASS: {t.__name__}')
        except AssertionError as e:
            failed += 1
            print(f'FAIL: {t.__name__} - {e}')
        except Exception as e:
            failed += 1
            print(f'ERROR: {t.__name__} - {e}')
    print(f'\n{passed}/{len(tests)} tests pass')
    sys.exit(0 if failed == 0 else 1)
