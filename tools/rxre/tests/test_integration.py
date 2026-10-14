#!/usr/bin/env python3
"""Integration test: complete mission lifecycle with evidence capture."""

import sys
import tempfile
import os
import subprocess
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from store import (
    conectar, crear_mision, crear_criterio_mision, agregar_tarea_a_mision,
    marcar_tarea_completada, verificar_criterios_mision, seleccionar_siguiente_accion,
    resumir_mision, marcar_mision_completada, capturar_evidencia_desde_ejecucion
)


def test_integration():
    """Test complete mission lifecycle with GAME-001 evidence."""
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as f:
        db_path = f.name

    c = conectar(db_path)

    # 1. Create mission
    mid = crear_mision(c, 'GAME-001: Vertical Slice', 'Verify window and input')
    print(f'1. Mission: {mid}')

    # 2. Add criteria (no evidence_ids yet)
    crear_criterio_mision(c, mid, 'Window renders', 'PROVEN', [], 1)
    crear_criterio_mision(c, mid, 'Input handled', 'PROVEN', [], 1)
    print('2. Added 2 PROVEN criteria')

    # 3. Add tasks
    agregar_tarea_a_mision(c, mid, 'Run GAME-001', 'Execute mad_nexus', priority=10)
    agregar_tarea_a_mision(c, mid, 'Verify shutdown', 'Check exit code', priority=8)
    print('3. Added 2 tasks')

    # 4. Select next action
    next_task = seleccionar_siguiente_accion(c, mid)
    print(f'4. Next task: {next_task}')

    # 5. Execute GAME-001
    print('5. Executing GAME-001...')
    result = subprocess.run(
        ['timeout', '5s', 'RESEARCH/GAME-001/reconstruction/build/mad_nexus'],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout + result.stderr
    exit_code = result.returncode
    print(f'   Exit: {exit_code}, Output lines: {len(output.splitlines())}')

    # 6. Capture evidence
    exec_result = {
        'rc': exit_code,
        'status': 'ok' if exit_code == 0 else 'error',
        'stdout': output[:500],
        'stderr': '',
        'capability': 'GAME-001',
        'timeout': False
    }
    finding_id = capturar_evidencia_desde_ejecucion(c, exec_result, 'GAME-001')
    print(f'6. Evidence captured: {finding_id}')

    # 7. Update criteria to reference the finding
    # Get the first criterion ID
    criterios = c.execute(
        "SELECT criterion_id FROM mission_criteria WHERE mission_id = ?", (mid,)
    ).fetchall()
    if criterios:
        c.execute(
            "UPDATE mission_criteria SET evidence_ids = ? WHERE criterion_id = ?",
            (json.dumps([finding_id]), criterios[0][0])
        )
        c.commit()

    # Re-verify
    result = verificar_criterios_mision(c, mid)
    print(f'7. Criteria: {result["criterios_cumplidos"]}/{result["total_criterios"]} pass')
    for r in result['resultados']:
        print(f'   {r["status"]}: {r["reason"]}')

    # 8. Complete task
    marcar_tarea_completada(c, next_task)
    print(f'8. Task completed')

    # 9. Try to complete mission
    complete = marcar_mision_completada(c, mid)
    print(f'9. Mark complete: success={complete["success"]}')

    # 10. Summary
    summary = resumir_mision(c, mid)
    print(f'10. Summary: {summary["criterios_cumplidos"]}/{summary["total_criterios"]} criteria pass, status={summary["status"]}')

    c.close()
    os.unlink(db_path)
    print()
    print('=== INTEGRATION TEST COMPLETE ===')


if __name__ == '__main__':
    test_integration()