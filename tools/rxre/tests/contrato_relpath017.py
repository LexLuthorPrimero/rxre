#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-017 · ¿rompe el cambio concurrente el contrato de `rel`?

El hunk 1 del cambio ajeno cambia

    "rel": os.path.relpath(p, amd_root)     ->  os.path.relpath(p, base)

donde  base = <amd_root>/include/asic_reg.  Eso convierte

    include/asic_reg/gmc/gmc_8_1_d.h   ->   gmc/gmc_8_1_d.h

y `rel` no es un campo decorativo:  ordena las definiciones  (hits.sort)  y
sale en `defined_in`,  que es la salida que ve el usuario y la que consumes
`normalize.py`.

La pregunta NO es "que parece bien".  Es:  ¿que consumidores tienen un
CONTRATO escrito sobre ese formato,  y cuáles se rompen?

Se mide,  no se razona:  dos árboles desechables  (HEAD  y  HEAD + el cambio
concurrente de reg_resolve.py)  y la misma batería de tests en los dos.

NO se toca reg_resolve.py.  NO se toca el árbol compartido.  Nada de git
worktree:  el árbol está en un estado concurrente y no se toca su estado git.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONC = ROOT / "tools/reg_resolve.py"          # el que tiene el cambio ajeno
HEAD_F = "tools/reg_resolve.py"

TESTS = [
    ("test_vm8_register009", "ARISTA DE INCLUSION: asserta el string exacto de rel"),
    ("test_p003", "P0.3 unidad + T0302"),
    ("test_p004", "P1"),
    ("test_p005", "Conflict tracking"),
    ("test_target_identity009", "Identidad PCI"),
    ("test_p0_2_conflict014", "P0.2 semantica (014)"),
    ("test_p0_2_consumer015", "P0.2 CONSUMER"),
    ("test_cobertura_root013", "Cobertura GFX8: arbol y unidad"),
    ("test_cobertura_drift015b", "Cobertura: guard de productor"),
]


def iso(tmp, reg_resolve_src: Path):
    dst = Path(tmp)
    shutil.copytree(ROOT / "tools/rxre", dst / "tools/rxre",
                    ignore=shutil.ignore_patterns("__pycache__", "github",
                                                  "storage"),
                    dirs_exist_ok=True)
    (dst / "tools").mkdir(exist_ok=True)
    shutil.copy(reg_resolve_src, dst / "tools/reg_resolve.py")
    shutil.copy(ROOT / "tools/rxre_cobertura_gfx8.py",
                dst / "tools/rxre_cobertura_gfx8.py")
    (dst / "RESEARCH").symlink_to(ROOT / "RESEARCH")
    return dst


def main():
    print("=" * 74)
    print("RXRE-017 · CONTRATO del campo `rel` bajo el cambio concurrente")
    print("=" * 74)

    # ── 1 · qué dice exactamente el hunk ────────────────────────────────
    src = CONC.read_text(encoding="utf-8")
    m = re.search(r"base = (os\.path\.join\([^\n]+)\)", src)
    print("\n  1 · EL HUNK")
    print("      base = %s" % (m.group(1) if m else "NOT_FOUND"))
    print("      rel  = os.path.relpath(p, base)")
    print("      ANTES  relpath(p, amd_root) -> 'include/asic_reg/.../x_d.h'")
    print("      AHORA relpath(p, base)     -> '.../x_d.h'")

    # ── 2 · el contrato escrito, buscado en el arbol ────────────────────
    print("\n  2 · CONSUMIDORES CON CONTRATO ESCRITO sobre el formato")
    contrato = []
    for pat, desc in (
            (r'assertEqual\([^)]*\["rel"\]\s*,\s*"([^"]+)"\)',
             "assertion exacta del string"),
            (r'==\s*"include/asic_reg/([^"]+)"', "comparacion literal con prefijo"),
            (r'startswith\("include/asic_reg', "startswith con prefijo")):
        for f in sorted((ROOT / "tools").rglob("*.py")):
            if "rxre/github" in str(f):
                continue
            txt = f.read_text(encoding="utf-8", errors="replace")
            for mt in re.finditer(pat, txt):
                contrato.append((str(f.relative_to(ROOT)),
                                 mt.group(0)[:70].replace("\n", " "), desc))
    for f, frag, desc in contrato:
        print("      %-52s %-42s %s" % (f, frag, desc))
    print("      total con contrato escrito: %d" % len(contrato))

    # ── 3 · MEDIR:  HEAD  vs  HEAD + cambio concurrente ─────────────────
    print("\n  3 · MEDICION  (mismos tests,  dos arboles desechables)")
    head_src = Path(tempfile.mkdtemp(dir="/tmp/opencode", prefix="head-")) / "r.py"
    head_src.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:" + HEAD_F],
        capture_output=True).stdout)
    res = {}
    for etiqueta, fuente in (("HEAD", head_src),
                             ("CONCURRENTE", CONC)):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode",
                                         prefix="iso-") as tmp:
            dst = iso(tmp, fuente)
            for nombre, _desc in TESTS:
                t = dst / "tools/rxre/tests" / (nombre + ".py")
                if not t.is_file():
                    res[(etiqueta, nombre)] = "AUSENTE"
                    continue
                p = subprocess.run([sys.executable, "-B", str(t)], cwd=dst,
                                   capture_output=True, text=True, timeout=2400,
                                   env=dict(os.environ,
                                            PYTHONDONTWRITEBYTECODE="1"))
                if p.returncode == 0:
                    res[(etiqueta, nombre)] = "VERDE"
                else:
                    fallos = [l.strip() for l in p.stdout.splitlines()
                              if l.startswith("  [NO ")]
                    AssertionErr = re.findall(
                        r'AssertionError:.*', p.stdout + p.stderr)
                    res[(etiqueta, nombre)] = "ROJO: " + (
                        fallos[0][6:60] if fallos else
                        (AssertionErr[0][:60] if AssertionErr else
                         "rc=%d" % p.returncode))
    print("      %-26s %-34s %-46s %s" % ("test", "HEAD", "CONCURRENTE", "clase"))
    regres = []
    improve = []
    cambia = []
    for nombre, desc in TESTS:
        a, b = res[("HEAD", nombre)], res[("CONCURRENTE", nombre)]
        va, vb = a.startswith("VERDE"), b.startswith("VERDE")
        if va and not vb:
            clase = "REGRESION"
            regres.append((nombre, b))
        elif (not va) and vb:
            clase = "MEJORA"
            improve.append((nombre, a))
        elif a != b:
            clase = "CAMBIO_DE_MOTIVO"
            cambia.append((nombre, a, b))
        else:
            clase = "igual"
        print("      %-26s %-34s %-46s %s"
              % (nombre, a[:34], b[:46], clase))

    # ── 4 · veredicto ───────────────────────────────────────────────────
    print("\n  4 · VEREDICTO")
    print("      REGRESIONES (VERDE->ROJO): %d" % len(regres))
    for n, r in regres:
        print("        %-28s %s" % (n, r))
    print("      MEJORAS (ROJO->VERDE): %d  (trabajo ajeno aterriza, no es"
          % len(improve))
    print("        cuenta como regresion mia)")
    for n, _ in improve:
        print("        %-28s" % n)
    print("      CAMBIO DE MOTIVO: %d" % len(cambia))
    for n, a, b in cambia:
        print("        %-28s antes: %.50s" % (n, a))
        print("        %-28s ahora: %.50s" % ("", b))


if __name__ == "__main__":
    sys.exit(main())