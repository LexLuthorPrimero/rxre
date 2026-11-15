#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""IER-001 · discover no debe crear misiones duplicadas del mismo artefacto.

Problema (fallas_rxre_8_principios.md #8, IER F2):
`op:discover`, al hallar símbolos, fuerza `store.crear_mision` (que aleatoriza
`mission_id`) sin comprobar si ya existe una misión PENDING del mismo
artefacto. Dos invocaciones consecutivas sobre el mismo binario producen dos
misiones y dos tareas idénticas en la base.

Hipótesis rival: una misión PENDING con el mismo título es la MISMA misión;
crear otra no aporta evidencia, contamina el tablero y rompe el recuento
posterior de tareas del cierre automático.

Criterio de refutación: contar filas en `missions` y `mission_tasks` tras dos
invocaciones equivalentes de `op:discover` sobre el mismo artefacto. Ambas
conteo debe ser 1. Si no lo son, la hipótesis queda refutada.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))          # tools/rxre
ROOT = os.path.abspath(os.path.join(PKG, "..", ".."))    # repo
MAQUINA = os.path.join(PKG, "api", "machine.py")
ARTEFACTO = "/bin/ls"
ARTEFACTO_NOMBRE = os.path.basename(ARTEFACTO)


def _invoke(env, n=2):
    out = []
    for _ in range(n):
        req = json.dumps({"op": "discover", "artefacto": ARTEFACTO}) + "\n"
        p = subprocess.run([sys.executable, MAQUINA], input=req,
                           capture_output=True, text=True, timeout=600,
                           env=env)
        lineas = [l for l in (p.stdout or "").strip().splitlines() if l]
        if lineas:
            out.append(json.loads(lineas[0]))
    return out


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="ier001_")
    db = os.path.join(tmpdir, "discover.sqlite3")
    env = {
        **os.environ,
        "PYTHONPATH": os.path.join(ROOT, "tools") + os.pathsep + PKG,
        "RXRE_DB": db,
    }
    respuestas = _invoke(env, n=2)
    assert respuestas, "machine.py no produjo respuestas"
    fallas = []

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    titulo_like = "Investigación: %s%%" % ARTEFACTO
    n_mis = con.execute(
        "SELECT count(*) FROM missions WHERE title LIKE ?",
        (titulo_like,)).fetchone()[0]
    n_tareas = con.execute(
        "SELECT count(*) FROM mission_tasks WHERE mission_id IN "
        "(SELECT mission_id FROM missions WHERE title LIKE ?)",
        (titulo_like,)).fetchone()[0]
    con.close()

    if n_mis != 1:
        fallas.append("se crearon %d misiones para el mismo artefacto" % n_mis)
    if n_tareas != 1:
        fallas.append("se crearon %d tareas para el mismo artefacto" % n_tareas)

    print()
    if fallas:
        print("IER-001 FALLA:")
        for f in fallas:
            print("  - %s" % f)
        print("respuestas:", [r.get("status") for r in respuestas])
        return 1
    print("IER-001 OK: discover es idempotente con el mismo artefacto (1 misión, 1 tarea)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
