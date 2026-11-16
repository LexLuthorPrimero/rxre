#!/usr/bin/env python3
"""Pruebas del detector de centinelas de borrado (issue openai/codex#40995)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import cleanup_guard

fails = []
def v(name, cond, info=""):
    print(("PASS" if cond else "FAIL"), name, info)
    if not cond:
        fails.append(name)

INCIDENT_SHAPE = """
from pathlib import Path
import shutil, tempfile
def build(output_dir: Path, parent_dir: Path) -> dict:
    stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=output_dir.parent))
    try:
        pass
        stage = Path()
        return {}
    finally:
        if stage and stage.exists():
            shutil.rmtree(stage)
"""

SAFE_SHAPE = """
from pathlib import Path
import shutil
def build(output_dir: Path) -> dict:
    stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=output_dir.parent))
    try:
        return {}
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)
"""

src = cleanup_guard.analyze_source(INCIDENT_SHAPE)
rules = set(src["rules_matched"])
v("A: incidente real detectado R1", "R1" in rules, str(src["summary"]))
v("A: incidente real detectado R2", "R2" in rules, str(src["summary"]))
v("A: incidente no marcado R3", "R3" not in rules)

src = cleanup_guard.analyze_source(SAFE_SHAPE)
v("B: código seguro sin hallazgos", src["findings"] == [], str(src["summary"]))

src = cleanup_guard.analyze_source("import shutil\nshutil.rmtree('.')\n")
v("C: rmtree de literal '.' detectado R3", any(f["rule"] == "R3" for f in src["findings"]))

src = cleanup_guard.analyze_source("import shutil\nshutil.rmtree('..')\n")
v("C2: rmtree de literal '..' detectado R3", any(f["rule"] == "R3" for f in src["findings"]))

src = cleanup_guard.analyze_source("import shutil\nshutil.rmtree('')\n")
v("C3: rmtree de literal '' detectado R3", any(f["rule"] == "R3" for f in src["findings"]))

src = cleanup_guard.analyze_source("from pathlib import Path\nshutil_path = Path('.')\nshutil_path = Path('data')\nprint(shutil_path)\n")
v("D: Path('.') solo aún da R1 (declaración honesta de ambigüedad)", src["findings"] and src["findings"][0]["rule"] == "R1")

src = cleanup_guard.analyze_source("def f():\n    x = 1\n    return x\n")
v("E: código trivial limpio", src["findings"] == [])

src = cleanup_guard.analyze_source("def f(:\n")
v("F: syntax error -> BLOCKED, no crash", src["estado"] == "BLOCKED")

src = cleanup_guard.analyze_source("import os\nos.removedirs('.')\n")
v("G: os.removedirs de literal '.' detectado", any(f["rule"] == "R3" for f in src["findings"]))

v("H: incidente: severidad crítica en R2/R3", all(f["severity"] == "critical" for f in cleanup_guard.analyze_source(INCIDENT_SHAPE)["findings"] if f["rule"] in ("R2", "R3")))

print()
if fails:
    print("FALLOS:", fails)
    sys.exit(1)
print("LIMPIEZA_GUARD: TODAS PASAN")
