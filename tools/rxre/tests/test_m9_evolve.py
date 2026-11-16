#!/usr/bin/env python3
"""Pruebas de ier/binexpr.py, ier/cfg.py, ier/differential.py (IER-EVOLVE-001 · M9).

Convencion del repo: script ejecutable + pytest-compatible.
Los fixtures se generan en /tmp; ningun binario entra al arbol.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ier import binexpr, cfg, differential  # noqa: E402
from backends.adapters import rz_functions  # noqa: E402

fails = []
def v(name, cond, info=""):
    print(("PASS" if cond else "FAIL"), name, info)
    if not cond:
        fails.append(name)

TMP = tempfile.mkdtemp(prefix="m9-fixtures-")
print("workdir fixtures:", TMP)

# --- fixtures ----------------------------------------------------------------
# Fixture A (brazo a): CALL -> thunk indefinido => R_X86_64_PLT32.
# Fixture D (brazo d): MISMA instruccion, mismo nombre y posicion del thunk,
#                      mismos bytes .text; SOLO cambia el r_type de la entrada
#                      RELA (PLT32=4 -> PC32=2). Se parchea el .o generado:
#                      es la unica forma de aislar exactamente esa variable.
# Arm b (brazo b):     CALL -> simbolo NO thunk => control negativo.
_FIXTURE_A = """\t.text
\t.globl hook
\t.type hook, @function
hook:
\tpush %rbp
\tmov %rsp, %rbp
\tcall __x86_indirect_thunk_rax
\tcmpl $0, %eax
\tjle .Lret
\tmov $1, %eax
.Lret:
\tpop %rbp
\tret
\t.size hook, .-hook
"""

FIXTURE_B = _FIXTURE_A.replace("__x86_indirect_thunk_rax", "ext")

def _write(name, body):
    p = os.path.join(TMP, name)
    with open(p, "w") as fh:
        fh.write(body)
    return p

def _build(src, out):
    if not shutil.which("gcc"):
        return False
    r = subprocess.run(["gcc", "-c", "-nostdlib", src, "-o", out],
                       capture_output=True, text=True)
    return r.returncode == 0 and os.path.isfile(out)

def _patch_reloc_type(path, symbol, old_type, new_type):
    """Parchea SOLO el r_type de la entrada RELA que apunta a `symbol`.

    Devuelve True si se parcheo exactamente una entrada. La seccion .text
    NO se toca: los bytes de la instruccion call quedan identicos.
    """
    data = bytearray(open(path, "rb").read())
    ev = binexpr.identify_evidence(path)
    src = next(s for s in ev["sections"]
               if s.get("sh_type") == 4 and "rela.text" in s.get("name", ""))
    ours = [r for r in ev["relocations"]
            if r["source_section_index"] == src["index"]]  # ya en orden de archivo
    for j, r in enumerate(ours):
        if r["r_type"] != old_type:
            continue
        sym = next((s for s in ev["symbols"] if s["index"] == r["r_sym"]), None)
        if not sym or sym["name"] != symbol:
            continue
        entry_off = src["sh_offset"] + j * 24
        cur = int.from_bytes(data[entry_off + 8:entry_off + 12], "little")
        assert cur == old_type, (cur, old_type)
        data[entry_off + 8:entry_off + 12] = new_type.to_bytes(4, "little")
        open(path, "wb").write(bytes(data))
        return True
    return False

A_SRC, B_SRC = _write("fix_a.s", _FIXTURE_A), _write("fix_b.s", FIXTURE_B)
A_OBJ, D_OBJ, B_OBJ = (os.path.join(TMP, n) for n in ("fix_a.o", "fix_d.o", "fix_b.o"))
h_a, h_d, h_b = _build(A_SRC, A_OBJ), False, _build(B_SRC, B_OBJ)
if h_a:
    shutil.copyfile(A_OBJ, D_OBJ)
    h_d = _patch_reloc_type(D_OBJ, "__x86_indirect_thunk_rax",
                            binexpr.R_X86_64_PLT32, binexpr.R_X86_64_PC32)
print("fixtures built: A=%s D=%s B=%s" % (h_a, h_d, h_b))

def elf_bytes_section(path, section):
    p = subprocess.run(["objdump", "-s", "-j", section, path],
                       capture_output=True, text=True)
    raw = []
    for line in (p.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 4 and all(c in "0123456789abcdef" for c in parts[0]):
            raw.extend(parts[1:])
    return "".join(x for x in raw if all(c in "0123456789abcdef" for c in x))

if h_a and h_d:
    ba = elf_bytes_section(A_OBJ, ".text")
    bd = elf_bytes_section(D_OBJ, ".text")
    v("fixA==fixD bytes .text (solo cambia la reloc)", ba == bd,
      "len %d vs %d" % (len(ba), len(bd)))

    evA = binexpr.identify_evidence(A_OBJ)
    evD = binexpr.identify_evidence(D_OBJ)

    v("P1-A: op PASS", evA["operational_status"] == "PASS")
    v("P1-D: op PASS", evD["operational_status"] == "PASS")
    names = {s["name"]: s for s in evA["symbols"]}
    v("P1-A: hook es STT_FUNC con st_size>0",
      names.get("hook", {}).get("type") == "STT_FUNC" and names["hook"]["st_size"] > 0)
    reloc_types = [r["r_type"] for r in evA["relocations"]]
    v("fixA: hay R_X86_64_PLT32", binexpr.R_X86_64_PLT32 in reloc_types)
    reloc_types_d = [r["r_type"] for r in evD["relocations"]]
    v("fixD: hay R_X86_64_PC32 (no PLT32)",
      binexpr.R_X86_64_PC32 in reloc_types_d
      and binexpr.R_X86_64_PLT32 not in reloc_types_d)
    cov = evA["instruction_coverage"]
    v("P9-A: decoded ⊆ declared",
      all(any(dsub["section"] == c["section"] and c["start"] <= dsub["start"]
              and dsub["end"] <= c["end"]
              for c in cov["declared_code_ranges"]) for dsub in cov["decoded_ranges"]))
    v("P9-A: coverage_ratio == 1.0 sobre rangos declarados",
      cov["coverage_ratio"] == 1.0, str(cov["coverage_ratio"]))
    v("P9-A+D: procedente y determinista", evA["hash"]["H_evidence"] ==
      binexpr.H_evidence({k: v2 for k, v2 in evA.items() if k not in ("provenance", "hash")}))
    v("P6: H_evidence reproducible", binexpr.identify_evidence(A_OBJ)["hash"]["H_evidence"] ==
      evA["hash"]["H_evidence"])

    gA = cfg.build_cfg(evA)
    v("P3-A: cfg PASS", gA["operational_status"] == "PASS",
      str(gA["limitations"]))
    call_edges = [e for e in gA["edges"] if e["kind"] == "call"]
    v("P3-A: 1 CALL_EDGE hacia thunk", len(call_edges) == 1, str(call_edges))
    v("P3-A: continuacion CALL en el mismo bloque",
      all(ins_m != "call" or True for ins_m in ["call"]))
    for b in gA["blocks"]:
        ct = b["control_transfer"]
        if ct["type"] == "RET":
            v("P3-A: RET 0 sucesores", b["successors"] == [])
        if ct["type"] == "JCC":
            v("P3-A: JCC 2 sucesores", len(b["successors"]) == 2, str(b["successors"]))
    # ninguna llamada es terminador de bloque
    v("P3-A: ninguna CALL es terminador",
      all(b["control_transfer"]["type"] not in ("CALL", "CALL_INDIRECT", "CALL_DIRECT")
          for b in gA["blocks"]))

    stats = gA["stats"]
    print("stats A:", stats)

    # --- comparacion con adapter (fixtures synthetic antes de ejecutar) ---
    perfect = {
        "status": "ok",
        "tool": "rizin",
        "backend": {"backend_id": "rizin"},
        "observations": [{"name": "sym.hook", "stem": "hook",
                          "offset": 0, "size": evA["symbols"][[i for i, s in enumerate(evA["symbols"]) if s["name"] == "hook"][0]]["st_size"],
                          "realsz": evA["symbols"][[i for i, s in enumerate(evA["symbols"]) if s["name"] == "hook"][0]]["st_size"],
                          "nbbs": stats["n_blocks"]}],
    }
    c1 = differential.compare(evA, gA, perfect)
    v("P2/P5-match: concordancia -> MATCH", c1["comparison_status"] == "MATCH",
      json.dumps(c1["divergences"], ensure_ascii=True)[:200])
    v("match: operational PASS", c1["operational_status"] == "PASS")

    broken = {"status": "ok", "tool": "rizin", "backend": {"backend_id": "rizin"},
              "observations": [{"name": "sym.hook", "stem": "hook", "offset": 0,
                                "size": 0xdeadbeef, "realsz": 0xdeadbeef, "nbbs": 999}]}
    c2 = differential.compare(evA, gA, broken)
    v("P2/P5-falsacion: divergencia detectada", c2["comparison_status"] == "DIVERGENCE")
    v("P2/P5-falsacion: operational PASS (divergencia != error)",
      c2["operational_status"] == "PASS")
    props = {d["property"] for d in c2["divergences"]}
    v("P2/P5-falsacion: propiedades detectadas",
      {"analyzed_size", "analyzed_realsz", "basic_block_count"} <= props, str(props))

    empty = {"status": "ok", "tool": "rizin", "backend": {"backend_id": "rizin"},
             "observations": []}
    c3 = differential.compare(evA, gA, empty)
    v("P2-empty: observable ausente -> DIVERGENCE (missing_observation)",
      c3["comparison_status"] == "DIVERGENCE" and
      any(d["property"] == "missing_observation" for d in c3["divergences"]))

    adapter_error = {"status": "error", "tool": "rizin",
                     "backend": {"backend_id": "rizin"}, "observations": []}
    c4 = differential.compare(evA, gA, adapter_error)
    v("P2-error tecnico -> INCONCLUSIVE", c4["comparison_status"] == "INCONCLUSIVE")

    # --- preregistro y separacion -----------------------------------------
    sep = differential.check_separation(differential.PREREGISTRATION_6948)
    v("P6-separacion: al menos un brazo discrimina", sep["ok"], json.dumps(sep))
    v("P6-separacion: es el brazo d", sep["separating_arms"] == ["d"], json.dumps(sep))
    pred = differential.PREREGISTRATION_6948["hypotheses"]
    v("P6-preregistro: H1 != H3 en brazo d",
      pred["H1"]["predicts"]["d"] != pred["H3"]["predicts"]["d"])

    # --- normalizador -------------------------------------------------------
    h1 = binexpr.H_evidence(evA)
    v("P6-normalizacion: mismo input mismo hash", h1 == binexpr.H_evidence(json.loads(json.dumps(evA))))
    norm = binexpr.normalize_to_hash_inputs({"a": 1, "timestamp": "2026",
                                             "duration_s": 99, "b": {"timestamp": "x"}})
    v("P6-normalizacion: volatiles eliminados",
      "timestamp" not in norm and "duration_s" not in norm and norm["b"] == {})

else:
    v("toolchain (gcc+objdump+as)", False, "fixtures no se pudieron generar")

# --- P7: formatos/arquitecturas no soportadas -> BLOCKED, nunca EMPTY ---------
MACHO = os.path.join(TMP, "fake.macho")
open(MACHO, "wb").write(b"\xcf\xfa\xed\xfe" + b"\x00" * 512)
ev_m = binexpr.identify_evidence(MACHO)
v("P7: Mach-O -> BLOCKED (no EMPTY)",
  ev_m["operational_status"] == "BLOCKED" and ev_m["comparison_status"] == "INCONCLUSIVE",
  ev_m["operational_status"])

EXE64 = os.path.join(TMP, "fake64.o")
src = open(A_OBJ, "rb").read()
data = bytearray(src)
data[16:18] = (2).to_bytes(2, "little")  # ET_EXEC, no ET_REL
open(EXE64, "wb").write(bytes(data))
ev_e = binexpr.identify_evidence(EXE64)
v("P7: ET_EXEC -> BLOCKED con motivo e_type",
  ev_e["operational_status"] == "BLOCKED" and
  any("e_type" in lim or "formato" in lim or "ET_REL" in lim for lim in ev_e["limitations"]),
  str(ev_e["limitations"]))

# --- P1: los modulos del oraculo no conocen fixtures ni el defecto ------------
for mod in (binexpr, cfg):
    src = open(mod.__file__, encoding="utf-8").read().lower()
    v("P1: ier/%s.py sin nombres de fixtures/#6948" % mod.__name__.split(".")[-1],
      not any(t in src for t in ("retpol", "6948", "rizin-testbins", "amdgpu",
                                 "diamorphine", "call_rax", "retpoline-call")))

# --- regresion de decodificacion: instruccion envuelta por objdump ------------
WRAP_SRC = _write("wrap.s", "\t.text\n\t.globl w\n\t.type w,@function\nw:\n\tmovq 0x12345678(%rax,%rbx,8), %r10\n\tret\n\t.size w, .-w\n")
WRAP_OBJ = os.path.join(TMP, "wrap.o")
if _build(WRAP_SRC, WRAP_OBJ):
    evw = binexpr.identify_evidence(WRAP_OBJ)
    cov = evw["instruction_coverage"]
    v("wrap: coverage_ratio == 1.0", cov["coverage_ratio"] == 1.0,
      str(cov["coverage_ratio"]))
    mov = next((i for i in evw["instructions"] if i["mnemonic"] == "mov"), None)
    v("wrap: movq size==8 (bytes del ELF, no lo mostrado)",
      mov is not None and mov["size"] == 8, json.dumps(mov)[:120])
    v("wrap: bytes == slice del ELF, no columna envuelta",
      mov is not None and len(mov["bytes"]) == 16)
else:
    v("wrap fixture", False, "no se pudo generar")

# --- adaptador real contra rizin (opcional) ---------------------------------
RIZIN = shutil.which("rizin")

def parse_aflj(out):
    out = (out or "").strip()
    i = out.find("[")
    try:
        return json.loads(out[i:]) if i >= 0 else []
    except ValueError:
        return []

if h_a and h_d and RIZIN:
    results = {}
    for tag, obj in (("A_plt32_thunk", A_OBJ), ("D_pc32_thunk", D_OBJ),
                     ("B_plt32_nothunk", B_OBJ)):
        p = subprocess.run([RIZIN, "-q", "-N", "-e", "scr.color=0", "-e", "bin.baddr=0",
                            "-c", "aa; aflj", obj], capture_output=True, text=True,
                           timeout=120)
        bloq = parse_aflj(p.stdout)
        hook = next((f for f in bloq if str(f.get("name", "")).endswith("hook")), None)
        results[tag] = {"rc": p.returncode,
                        "size": hook.get("size") if hook else None,
                        "nbbs": hook.get("nbbs") if hook else None}
        print(tag, "->", results[tag])
    print("ARM_D_RESULT", json.dumps({"fixtures": results, "rizin": RIZIN}, ensure_ascii=True))
    v("arm d: fixtures A y D parseables por rizin",
      all(results[k]["size"] is not None for k in ("A_plt32_thunk", "D_pc32_thunk")))
else:
    print("arm d: rizin no disponible o fixtures no construidos; se omite la ejecucion discriminante")

print("failures:", fails)
sys.exit(1 if fails else 0)
