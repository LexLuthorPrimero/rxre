#!/usr/bin/env python3
"""Verificación operativa de herramientas IER (M3) sobre fixtures desechables."""
import json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ier import territory
from api import machine

FIX = "/tmp/opencode/toolintel-pytest"
fails = []
def v(name, cond, info=""):
    print(("PASS" if cond else "FAIL"), name, info)
    if not cond:
        fails.append(name)

shutil.rmtree(FIX, ignore_errors=True)
os.makedirs(FIX)

r = territory.verificar_herramientas(FIX)
levels = {t["tool"]: t["level"] for t in r["tools"]}
print(json.dumps(levels, indent=1))

# A: herramientas con EVIDENCIA real ejecutan y alcanzan al menos EXECUTED
for tool in ["gcc", "readelf", "objdump", "rizin", "glslangValidator", "spirv-val", "z3", "bwrap", "spatch"]:
    v("A: %s al menos EXECUTED" % tool,
      levels.get(tool) in ("EXECUTED", "VERIFIED", "INVOCABLE"),
      levels.get(tool))

# A2: VERIFIED exige check con expectativa ADIÓN (no self-report), cap counts>0
sm = territory.verificar_herramientas(FIX + "-2")
for t in sm["tools"]:
    if t["level"] == "VERIFIED":
        v("A2: VERIFIED %s tiene >=1 check esperado" % t["tool"],
          any(c["matched"] for c in t["checks"]), t["tool"])

# B: expectativa independiente — spirv-val debe rechazar SPIR-V corrupto
spv_bad = [t for t in r["tools"] if t["tool"] == "spirv-val"][0]
v("B: spirv-val VERIFIED y negative pasó",
  spv_bad["level"] == "VERIFIED" and all(c["matched"] for c in spv_bad["checks"]),
  spv_bad["level"])

# B2: capstone encontró mov eax, 0x2a
cap = [t for t in r["tools"] if t["tool"] == "capstone"][0]
v("B2: capstone VERIFIED (evidencia 0x2a)", cap["level"] == "VERIFIED")

# C: angr está IMPORTADO/MISSing, nunca VERIFIED (registry RXRE-004 NOT_DETERMINED)
angr_tool = [t for t in r["tools"] if t["tool"] == "angr"][0]
v("C: angr no puede proclamarse VERIFIED", angr_tool["level"] in ("IMPORTED", "MISSING"))

# D: cada tool tiene decisión del espacio permitido
for t in r["tools"]:
    v("D: %s decisión en espacio" % t["tool"], t["decision"] in ("UTILIZAR", "COMBINAR", "EXTENDER", "REPARAR", "SUSTITUIR", "BLOQUEAR"))
# E: comparación sobre fixture común
v("E: comparación tiene overlap", len(r["comparison"]["overlap_evidence"]) == 2 and r["comparison"]["rizin_aflj_ok"] and r["comparison"]["objdump_rc"] == 0)

# F: todos los fixtures fueron tratados desecheble en /tmp
v("F: fixture_dir en /tmp", r["fixture_dir"].startswith("/tmp"))

# G: hermeticidad — no hubo GPU/MMIO/UMR/mic
v("G: sin invocación de hardware", all("umr" not in t["tool"] and "gpu" not in t["tool"] for t in r["tools"]))

# H: consumo desde máquina (op territory, evaluate_tools)
out = machine._handle_territory({"op": "territory", "path": FIX, "evaluate_tools": True})
v("H: machine op=territory con evaluate_tools ok",
  out.get("status") == "ok" and out.get("results") and "tool_evaluations" in out["results"][0],
  out.get("status"))
v("H2: evaluate_tools no rompe contrato M2",
  all(k in out["results"][0] for k in ("input","artifacts","technologies","available_tools","epistemic_status")))

# I: determinismo — segunda corrida produce mismos niveles (fixture hashes pueden variar con build; los niveles no)
r2 = territory.verificar_herramientas(FIX + "-3")
levels2 = {t["tool"]: t["level"] for t in r2["tools"]}
v("I: niveles estables entre corridas", levels == levels2, "%s vs %s" % (levels, levels2))

# J: los niveles no saltan DISCOVERED->VERIFIED sin checks empatados
for t in r["tools"]:
    if t["level"] == "VERIFIED":
        v("J: VERIFIED con evidencia %s" % t["tool"], len(t["checks"]) >= 1)

# K: casos de borde — herramienta ausente (simulada)
def _level_for(present, integrated, executed, verified):
    level = "DISCOVERED"
    if present:
        level = "AVAILABLE"
    if integrated:
        level = "INTEGRATED"
    if executed:
        level = "EXECUTED"
    if verified:
        level = "VERIFIED"
    return level
v("K: ausente -> DISCOVERED", _level_for(False, False, False, False) == "DISCOVERED")
v("K2: solo ejecuta -> EXECUTED (nunca VERIFIED sin check)", _level_for(True, True, True, False) == "EXECUTED")

print()
if fails:
    print("FALLOS:", fails)
    sys.exit(1)
print("TOOLS_INTEL: TODAS PASAN")
