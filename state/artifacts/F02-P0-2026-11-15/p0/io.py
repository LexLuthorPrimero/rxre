import json, os
DEFAULT_SCRATCH = os.environ.get("P0_SCRATCH", "/tmp/opencode/p0-scratch")

def scratch_dir(case_id, stage):
    import time
    ts = time.strftime("%Y%m%dT%H%M%S")
    path = os.path.join(DEFAULT_SCRATCH, f"{case_id}-{stage}-{ts}")
    os.makedirs(path, exist_ok=True)
    return path

def cargar_caso(case_id):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(here, "cases", case_id, "payload.json")
    return json.load(open(p, encoding="utf-8"))

def cargar_expected():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(here, "expected.json")
    return json.load(open(p, encoding="utf-8"))
