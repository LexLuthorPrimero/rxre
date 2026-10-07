#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-013 mutation testing de la correccion de RAIZ y de la unidad declarada.

Un mutante cuenta como muerto SOLO si el test falla.  El test se ejecuta contra
un arbol desechable montado en /tmp/opencode:  copia de tools/rxre, copia de
tools/reg_resolve.py,  RESEARCH por symlink,  y la herramienta mutada en su
sitio.  Asi el test deriva RAIZ del arbol mutado y no del de trabajo.

Las cinco clases que exige el encargo:
  RAIZ          el arbol deja de derivarse o de poder forzar
  GUARD         la verificacion de arbol se vuelve decorativa
  UNIDAD        la derivacion del byte offset o la unidad declarada cambian
  PROCEDENCIA   un campo de procedencia desaparece o se falsea
  RUTA MUERTA   se afirma que el fallback si se ejecuta
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FUENTE = (ROOT / "tools/rxre_cobertura_gfx8.py").read_text(encoding="utf-8")
TEST = ROOT / "tools/rxre/tests/test_cobertura_root013.py"

MUTACIONES = {
    # ── RAIZ ───────────────────────────────────────────────────────────────
    "R1_raiz_absoluta_al_arbol_ajeno": (
        'RAIZ_DEFECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        'RAIZ_DEFECTO = "/home/lucas/Escritorio/RX550-INVESTIGACION"'),
    "R2_override_argv_suprimido": (
        '        if a.startswith("--raiz="):\n            return os.path.abspath(a.split("=", 1)[1]), "argv:--raiz"',
        '        if False:\n            return os.path.abspath(a.split("=", 1)[1]), "argv:--raiz"'),
    "R3_override_entorno_suprimido": (
        '    ent = os.environ.get("RXRE_ROOT")',
        '    ent = None'),

    # ── GUARD ──────────────────────────────────────────────────────────────
    "G1_prechequeo_de_existencia_suprimido": (
        '    if not os.path.isfile(esperado):',
        '    if False:'),
    "G2_comparacion_de_arbol_suprimida": (
        '    if aqui != esperado:',
        '    if False:'),
    "G3_prechequeo_de_diccionario_suprimido": (
        '    if not os.path.isfile(os.path.join(RAIZ, DICC)):',
        '    if False:'),
    "G5_prechequeo_del_productor_suprimido": (
        '    if not os.path.isfile(os.path.join(RAIZ, "tools/reg_resolve.py")):',
        '    if False:'),
    "G4_ruta_del_byte_offset_por_esperado": (
        '        fila["byte_offset_derivado"] = elegido * 4',
        '        fila["byte_offset_derivado"] = esperado * 4'),

    # ── UNIDAD ─────────────────────────────────────────────────────────────
    "U1_byte_offset_por_shift": (
        'fila["byte_offset_derivado"] = elegido * 4',
        'fila["byte_offset_derivado"] = elegido >> 2'),
    "U2_unidad_declarada_invertida": (
        'UNIDAD = "dword_register_index"',
        'UNIDAD = "byte_offset"'),
    "U3_derivacion_declarada_invertida": (
        'DERIVACION_BYTE = "byte_offset = valor * 4"',
        'DERIVACION_BYTE = "byte_offset = valor >> 2"'),

    # ── PROCEDENCIA ────────────────────────────────────────────────────────
    "P1_git_head_de_la_procedencia_retirado": (
        '        "source_git_head": _git_head(RAIZ),\n',
        ''),
    "P2_sha256_de_reg_resolve_retirado": (
        '        "reg_resolve_sha256": _sha256(reg_resolve),\n',
        ''),

    # ── RUTA MUERTA ────────────────────────────────────────────────────────
    "F1_se_declara_que_el_fallback_si_corrio": (
        '"disparado": FALLBACK_DEAD["disparado"],',
        '"disparado": FALLBACK_DEAD["registros"],'),
}


def monta(dst: Path, fuente: str) -> None:
    (dst / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github",
                                                  "storage"),
                    dirs_exist_ok=True)
    shutil.copy(ROOT / "tools/reg_resolve.py", dst / "tools/reg_resolve.py")
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    (dst / "tools/rxre_cobertura_gfx8.py").write_text(fuente, encoding="utf-8")


def corre(fuente: str):
    ast.parse(fuente)
    with tempfile.TemporaryDirectory(dir="/tmp/opencode", prefix="mut13-") as tmp:
        dst = Path(tmp)
        monta(dst, fuente)
        p = subprocess.run(
            [sys.executable, "-B", str(dst / "tools/rxre/tests/"
                                       "test_cobertura_root013.py")],
            cwd=dst, capture_output=True, text=True, timeout=1800,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return p


def main():
    base = corre(FUENTE)
    if base.returncode != 0:
        print("INVALID baseline: el codigo de partida debe estar verde")
        print(base.stdout[-3000:])
        return 2
    ok = sum(1 for _ in MUTACIONES)
    muertos = 0
    for nombre, (antes, despues) in MUTACIONES.items():
        n = FUENTE.count(antes)
        if n != 1:
            print("INVALID %s: sitio count=%d (se requiere 1)" % (nombre, n))
            return 2
        p = corre(FUENTE.replace(antes, despues, 1))
        if p.returncode == 0:
            print("SURVIVED %s   <-- hueco real de cobertura" % nombre)
            continue
        primeros = [l.strip() for l in p.stdout.splitlines() if l.startswith("  [NO ")]
        muertos += 1
        print("KILLED   %-42s %s" % (nombre, (primeros[0][6:60] if primeros
                                              else "rc=%d" % p.returncode)))
    print("\nmutation: %d/%d killed, %d survivors" % (muertos, ok, ok - muertos))
    return 0 if muertos == ok else 1


if __name__ == "__main__":
    sys.exit(main())