#!/usr/bin/env python3
"""RXRE baseline runner - reproducible (committeado en tools/rxre/tests/).

Descubre `test_*.py` (excluye *.backup, __pycache__) en este directorio, los ejecuta con
RXRE_DB aislada + PYTHONPATH configurado, y reporta PASS/FAIL. Corresponde a la "lista de
suites" / "26 suites verdes sobre main@53173f2" mencionada en el README; el numero exacto
de verdes depende del host (umr/GPU necesita root + amdgpu + RX550).

Uso:
    python3 tools/rxre/tests/run_baseline.py            # lucas (suites sin GPU/root)
    sudo -S python3 tools/rxre/tests/run_baseline.py     # root (incluye umr sobre RX550)
    # pw via stdin al prompt de sudo; no se persiste secret en disco (regla de privilegios).

iGPU 0000:00:02.0 prohibida; la RX550 (0000:01:00.0) solo probes read-only (umr -r).
"""
import glob, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))            # tools/
RXRE = os.path.join(PKG, "rxre")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE}
tests = sorted(g for g in glob.glob(os.path.join(HERE, "test_*.py"))
               if not g.endswith(".backup"))
db = tempfile.mktemp(suffix=".sqlite3")
env["RXRE_DB"] = db
passed = failed = errored = 0
rows = []
for t in tests:
    name = os.path.basename(t)
    try:
        p = subprocess.run([sys.executable, "-B", t], capture_output=True,
                           text=True, timeout=300, env=env)
        ok = (p.returncode == 0)
        rows.append((name, ok, p.returncode))
        if ok: passed += 1
        else: failed += 1
    except subprocess.TimeoutExpired:
        rows.append((name, False, "TIMEOUT")); errored += 1
    except Exception as ex:
        rows.append((name, False, "ERR:%s" % ex)); errored += 1
for name, ok, rc in rows:
    print(("PASS " if ok else "FAIL ") + name + (" rc=%s" % rc))
print("\n=== BASELINE %d passed / %d failed / %d errored (of %d) ==="
      % (passed, failed, errored, len(rows)))
if os.path.exists(db):
    try: os.remove(db)
    except OSError: pass
sys.exit(0 if (failed == 0 and errored == 0) else 1)
