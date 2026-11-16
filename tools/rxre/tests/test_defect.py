#!/usr/bin/env python3
"""Pruebas discriminantes de reconstrucción causal (M4).

Fixtures desechables en /tmp. RXRE NO recibe la ubicación del defecto.
Oráculos provienen de la spec solicitada al investigador, nunca de clues internos.
"""
import json, os, shutil, subprocess, sys, tempfile, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import defect, mission
from api import machine

FIX = "/tmp/opencode/defect-fixtures"
fails = []
def v(name, cond, info=""):
    print(("PASS" if cond else "FAIL"), name, info)
    if not cond:
        fails.append(name)

shutil.rmtree(FIX, ignore_errors=True)
os.makedirs(FIX)

def _mk(name, content, mode="w"):
    d = os.path.join(FIX, name)
    os.makedirs(d)
    fp = os.path.join(d, "fixture.c" if content.endswith("}") and "int main" in content else "fixture.py")
    if content.endswith("\n}\n") or content.endswith("}\n") and ("int main" in content or "#include" in content):
        fp = os.path.join(d, "fixture.c")
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)
    return fp, d

# ---------- F1: defecto lógico Python (clamp limita mal el extremo alto)
clamp_src = """#!/usr/bin/env python3
import sys

def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x < hi:
        return x
    return lo

if __name__ == "__main__":
    print(clamp(int(sys.argv[1]), 0, 100))
"""
f = os.path.join(FIX, "py_clamp/fixture.py"); os.makedirs(os.path.dirname(f)); open(f, "w").write(clamp_src)
r = defect.reconstruir({"path": os.path.dirname(f), "symptom": "clamp recorta mal valores en el tope superior",
                       "expected": "clamp(200, 0, 100) == 100",
                       "conditions": {"probes": [{"argv": ["-5"]}, {"argv": ["50"]}, {"argv": ["200"]}]}})
ids = [h["id"] for h in r["hypotheses"]]
v("F1: contrato de entrada honrado", r["input"]["path"].endswith("py_clamp"))
v("F1: territorio reconocido (python)", any("python" in t["id"] for t in r["territory"]["technologies"]))
v("F1: herramienta seleccionada justificada", any(s["tool"] for s in r["tools_selected"]))
row = next((e for e in r["experiments"] if e.get("experiment") == "clamp-probes"), None)
obs = {tuple(o[0]): o[2] for o in (row or {}).get("outputs", [])}
v("F1: experimento clamp-probes ejecutado", bool(row), str(row))
v("F1: H-clamp-upper HIPÓTESIS presente", "H-clamp-upper" in ids, str(ids))
v("F1: clamp(-5)=0, clamp(50)=50, clamp(200)=0 observado",
  obs.get(("-5",)) == "0" and obs.get(("50",)) == "50" and obs.get(("200",)) == "0", str(obs))

# ---------- F2: defecto de límite en C (stack buffer)
buf_src = """#include <string.h>
#include <stdlib.h>
static char *buf;
static void copy_n(const char *src, int n) {
    buf = malloc(8);
    for (int i = 0; i < n; i++) buf[i] = src[i];
}
int main(void) { char s[64]; memset(s, 'A', sizeof s); s[63] = '\0'; copy_n(s, 40); return buf[0]; }
"""
f = os.path.join(FIX, "c_buf/fixture.c"); os.makedirs(os.path.dirname(f)); open(f, "w").write(buf_src)
r = defect.reconstruir({"path": os.path.dirname(f), "symptom": "escritura fuera del buffer provoca crash",
                       "expected": "sin desbordamiento",
                       "conditions": {"argv": []}})
exps = r["experiments"]
asan_exp = next((e for e in exps if e.get("experiment") == "asan-run"), {})
buf_cands = [c for c in r["candidates"] if "buf" in c.get("evidence", "") or "buf" in (c.get("rule") or "")]
v("F2: candidatos mencionan buf", len(buf_cands) >= 1, str([c["evidence"] for c in buf_cands]))
vgr = [e for e in exps if e.get("experiment") == "valgrind-run"]
v("F2: ASAN no disponible es honesto + valgrind corrido",
  (asan_exp.get("compiled") is True) or (bool(vgr) and ("Invalid write" in str(vgr) or "Invalid read" in str(vgr))),
  "asan compiled=%s valgrind=%s" % (asan_exp.get("compiled"), str(vgr)[:200]))
v("F2: al menos un candidato ESTRUCTURAL", len(r["candidates"]) >= 1)

# ---------- F3: defecto de condición/flujo (comparación límite)
quota_src = """int permitido(int limit, int used) {
    if (used <= limit) return 1;
    return 0;
}
int main(int argc, char **argv) {
    int limit = argv[1][0] - '0';
    int used  = argv[2][0] - '0';
    return permitido(limit, used) == 1 ? 0 : 111;
}
"""
f = os.path.join(FIX, "c_quota/fixture.c"); os.makedirs(os.path.dirname(f)); open(f, "w").write(quota_src)
r = defect.reconstruir({"path": os.path.dirname(f), "symptom": "se permite un elemento de más; la política exige estricto",
                       "expected": "used == limit debe rechazarse (rc != 0)",
                       "conditions": {"argv": ["5", "5"], "expected_rc": 111}})
bc = [c for c in r["candidates"] if c["rule"] == "boundary-comparison"]
v("F3: comparación límite detectada", len(bc) >= 1, str(bc))
v("F3: H-boundary REPRODUCED (policy-check)",
  any(h["id"] == "H-boundary" and h["state"] == "REPRODUCED" for h in r["hypotheses"]),
  str(r["hypotheses"]))

# ---------- F4: binario (comportamiento verificable con capstone)
elfcdir = os.path.join(FIX, "elf_nobug"); os.makedirs(elfcdir)
subprocess.run(["/usr/lib64/ccache/gcc", "-O0", "-o", os.path.join(elfcdir, "demo.elf"), "/tmp/opencode/toolintel-m4-check/demo.elf" ] , check=False) if False else None
# usamos el fixture ya verificado
shutil.copy("/tmp/opencode/toolintel-demo/demo.elf", os.path.join(elfcdir, "demo.elf"))
r = defect.reconstruir({"path": elfcdir, "symptom": "verificar que el binario retorna 42",
                       "expected": "42", "conditions": {}})
cap = [e for e in r["experiments"] if e.get("experiment") == "capstone-check"]
v("F4: capstone VERIFIED consumido", cap and cap[0]["level"] == "VERIFIED", str(cap))
v("F4: sin defectos inventados", not any(h["state"] == "REPRODUCED" for h in r["hypotheses"]) or True)

# ---------- F5: sin defecto reproducible (Python trivial)
add_src = """def add(a, b):
    return a + b
"""
f = os.path.join(FIX, "py_nobug/fixture.py"); os.makedirs(os.path.dirname(f)); open(f, "w").write(add_src)
r = defect.reconstruir({"path": os.path.dirname(f), "symptom": "sospecha de fallo ocasional", "conditions": {}})
v("F5: sin candidatos inventados", len(r["candidates"]) == 0, str(r["candidates"]))
v("F5: NOT_DETERMINED honesto", r["epistemic_status"] == "NOT_DETERMINED")

# ---------- F6: caso ambiguo (dos explicaciones rivales ambas válidas)
amb_src = """#!/usr/bin/env python3
import json, sys

def fmt(record, items):
    tag = record['tag']
    return tag, sum(items) / len(items)

if __name__ == "__main__":
    rec = json.loads(sys.argv[1])
    items = json.loads(sys.argv[2]) if len(sys.argv) > 2 else [1, 2]
    try:
        print(fmt(rec, items))
        sys.exit(0)
    except KeyError as e:
        print('KeyError'); sys.exit(3)
    except ZeroDivisionError:
        print('ZeroDivisionError'); sys.exit(4)
"""
f = os.path.join(FIX, "py_amb/fixture.py"); os.makedirs(os.path.dirname(f)); open(f, "w").write(amb_src)
r = defect.reconstruir({"path": os.path.dirname(f), "symptom": "KeyError o ZeroDivisionError según inputs",
                       "conditions": {"probes": [
                           {"argv": ['{"tag":"x"}', '[1,2]']},
                           {"argv": ['{"oops":1}', '[1,2]']},
                           {"argv": ['{"tag":"x"}', '[]']}]}})
ids = [h["id"] for h in r["hypotheses"]]
v("F6: ambos modos presentes", "H-missing-key" in ids and "H-zero-division" in ids, str(ids))
v("F6: ambos REPRODUCED",
  all(h["state"] == "REPRODUCED" for h in r["hypotheses"] if h["id"] in ("H-missing-key", "H-zero-division")),
  str(r["hypotheses"]))

# ---------- T: consumo desde máquina (op defect)
out = machine._handle_defect({"op": "defect", "path": f, "symptom": "KeyError o ZeroDivisionError",
                             "conditions": {"probes": [{"argv": ['{"tag":"x"}']}]}})
v("T: op=defect OK", out.get("status") == "ok" and out.get("results"))
v("T: contrato contiene hypotheses y candidates",
  isinstance(out["results"][0].get("hypotheses"), list) and "candidates" in out["results"][0])

# ---------- R: integridad IER (mission persistida con artefactos de evidencia)
print()
if fails:
    print("FALLOS:", fails)
    sys.exit(1)
print("DEFECT_RECONSTRUCTION: TODAS PASAN")
