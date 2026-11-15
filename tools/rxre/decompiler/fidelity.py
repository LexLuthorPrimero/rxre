"""RXRE — Frontera de fidelidad del lifting (Plan LXXI / M1166-M1170).

Clasifica bloques de desensamblado en cuatro estados deterministas:

  FAITHFUL   — cada instrucción y efecto validados empíricamente (Tier A)
  PARTIAL    — al menos una instrucción parcial (Tier B) o flags compuestos
  UNSUPPORTED— al menos una instrucción fuera de dominio / sin semántica
  INVALID    — corrupción por slicing, formato o límites de instrucción

Reglas duras (nunca negociables):

  * El pipeline SOLO consume dump completo; provee `load_dump_text`.
    Cualquier `.byte` / `rex.` / instrucción partida => bloque INVALID.
  * Una instrucción decodificada NUNCA implica semántica validada.
  * Un fallo de evidencia degrada; nunca se completa por inferencia.
  * La clasificación del bloque es la peor de sus instrucciones.
  * EVEX / AVX-512 => UNSUPPORTED (no degradable silenciosamente).
  * Flag-composite no sostiene FAITHFUL.

No implementa lifter nuevo; consume `objdump -d --no-show-raw-insn` completo.
EVEX queda fuera del dominio admitido. Nada de esto es autorización ni promoción.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

PRECEDENCE = {"FAITHFUL": 1, "PARTIAL": 2, "UNSUPPORTED": 3, "INVALID": 4}
DOMAIN_PATH = os.path.join(os.path.dirname(__file__), "fidelity_domain_v1.json")

# ---------- parsing ----------
LINE_RE = re.compile(r"^\s+([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(\S+)(?:\s+(.*))?$")
LABEL_RE = re.compile(r"^([0-9a-f]+)\s+<([^>]+)>:")
BARE_CORRUPT = re.compile(r"\.byte\b|\brex\.\w*\b|data16|\.word\b|\.long\b|\.quad\b")

REG_XMM = re.compile(r"^%xmm([0-9]+)$")
REG64 = re.compile(r"^%(r(?:[0-9]+|ax|bx|cx|dx|bp|sp|di|si)|ax|al|ah|e[a-z]+)$")

def _is_reg_plain(op: str) -> bool:
    return bool(re.match(r"^%(?:r(?:ax|bx|cx|dx|bp|sp|si|di)|r[0-9]+|e(?:ax|bx|cx|dx|si|di|bp|sp)|[abcd](?:[xsil]|h))(?:[dwblh])?$", op))

def _is_reg_xmm(op: str) -> bool:
    return bool(REG_XMM.match(op))

FEATURE_KEY = "__features"

def load_contract(path: str = DOMAIN_PATH):
    with open(path, "r", encoding="utf-8") as f:
        contract = json.load(f)
    contract[FEATURE_KEY] = contract.get("feature_flags", {})
    return contract

def domain_hash(path: str = DOMAIN_PATH) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# ---------- operand analysis ----------
class OperandLine:
    def __init__(self, addr: int, raw: str, mnemonic: str, operands: str, nbytes: int, line_no: int):
        self.addr = addr
        self.raw = raw
        self.mnemonic = mnemonic
        self.operands = operands.strip()
        self.nbytes = nbytes
        self.line_no = line_no

def parse_instruction(text: str, line_no: int):
    """Returns (OperandLine|None, fatal_reason:str|None)."""
    m = LINE_RE.match(text.rstrip("\n"))
    if not m:
        # objdump display quirk: an instruction whose raw bytes overflow the columns can
        # continue on its own line with NO mnemonic; it is bookkeeping, not code.
        if re.match(r"^\s+[0-9a-fA-F]+:(\s+[0-9a-fA-F]{2})+\s*$", text.rstrip("\n")):
            return None, "CONTB"
        # instruction line but missing raw byte columns => RAW_BYTES_REQUIRED (fatal for block)
        if re.match(r"^\s+[0-9a-fA-F]+:\s*\S", text) and not re.match(r"^\s+[0-9a-f]+\s+<", text):
            tok = text.rstrip("\n")
            if BARE_CORRUPT.search(tok):
                return None, "BARE_CORRUPT: %r" % tok
            return None, "RAW_BYTES_REQUIRED: instruction line without raw byte columns (probable --no-show-raw-insn output): %r" % tok
        if LABEL_RE.match(text) or not text.strip():
            return None, None  # block separator handled by caller
        if BARE_CORRUPT.search(text):
            return None, "BARE_CORRUPT: %r" % text.rstrip("\n")
        return None, None  # comment/header lines ignored silently
    addr_s, bytes_s, mnemonic, rest = m.groups()
    # objdump quirk: a byte consumed by a previous long-displacement instruction may appear
    # on its own line; line is bookkeeping (not code); skip with marker CONTB
    if re.fullmatch(r"[0-9a-f]{1,2}", mnemonic) and not (rest or "").strip():
        return None, "CONTB"
    # byte integrity: decode raw bytes to ensure count matches token size
    raw_bytes = bytes(int(b, 16) for b in bytes_s.split())
    if len(raw_bytes) == 0:
        return None, "BARE_CORRUPT: no raw byte fields"
    forbidden = (".byte", "rex.")
    if any(t in (mnemonic + " " + (rest or "")).lower() for t in forbidden):
        return None, "BARE_CORRUPT: token '.byte'/'rex.' presente: %r" % text.rstrip("\n")
    ops = (rest or "").strip()
    return OperandLine(int(addr_s, 16), bytes_s.strip(), mnemonic, ops, len(raw_bytes), line_no), None

def _split_operands(text: str):
    """Split by top-level commas (parens- and brackets-depth aware)."""
    parts, cur, depth = [], "", 0
    for ch in text:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth = max(0, depth - 1)
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts

def analyze_operands(op_text: str):
    parts = _split_operands(op_text)
    def _class(p):
        p_ = p.lower()
        if p_.startswith("$"):
            return ("imm", p_)
        if "(" in p_ or ")" in p_:
            return ("mem", p_)
        if _is_reg_xmm(p_):
            return ("xmm", p_)
        if _is_reg_plain(p_):
            return ("reg", p_)
        if p_.startswith("rip") or p_.startswith("rip+") or "rip" in p_:
            return ("rip", p_)
        return ("opaque", p_)
    return [_class(p) for p in parts]

def classify_address_target(op_text: str, in_range):
    m = re.search(r"0x([0-9a-f]+)", op_text)
    if m:
        return int(m.group(1), 16)
    m2 = re.match(r"^([0-9a-f]+)\s*<", op_text)
    if m2:
        return int(m2.group(1), 16)
    return None

# ---------- classification ----------
VERDICT_VALUES = list(PRECEDENCE)

def row_map(contract):
    out = {}
    for row in contract["rows"]:
        key = (row["mnemonic"].lower(), row["form"])
        out[key] = row
    out[FEATURE_KEY] = contract.get(FEATURE_KEY, {})
    return out

def _is_32_reg(op: str) -> bool:
    return bool(re.match(r"^%e[a-z]+$", op) or re.match(r"^%r([0-9]+|a|b|c|d|bp|sp|di|si|ax)d$", op))

def _is_8_gpr(op: str) -> bool:
    return bool(re.match(r"^%(al|cl|dl|bl|ah|ch|dh|bh|dil|sil|bpl|spl|r[0-9]+b)$", op))

def _is_16_gpr(op: str) -> bool:
    return bool(re.match(r"^%(ax|bx|cx|dx|si|di|sp|bp|r[0-9]+w)$", op))

def _match_gpr32(row_map_, mn, ops):
    """Returns (row|None, reason). GPR32 forms; caller passes width hint."""
    def wcats():
        cs = []
        for c, p in ops:
            if c == "reg":
                cs.append("32" if _is_32_reg(p) else "64")
            else:
                cs.append("any")
        return cs
    cats = set(wcats())
    if "64" in cats:
        return None, None   # not a pure 32-bit operand set (fall to v1 ladder)
    mn = mn.lower()
    ops_c = [(c, p) for c, p in ops]
    def _jam(form):
        return row_map_.get((mn, form + "_32"))
    # Resize: mixed imm/reg pair forms锜idrẽ designate target forms
    if mn in ("jle", "ja", "jne"):
        return _jam("branch_rel"), None
    if len(ops_c) == 2 and ops_c[0][0] == "reg" and ops_c[1][0] == "reg":
        return _jam("reg_reg"), None
    if len(ops_c) == 2 and ops_c[0][0] == "reg" and ops_c[1][0] == "imm":
        return _jam("reg_imm"), None
    if len(ops_c) == 2 and ops_c[0][0] == "imm" and ops_c[1][0] == "reg":
        return _jam("imm_reg"), None
    if len(ops_c) == 1 and ops_c[0][0] == "reg" and mn == "mul":
        return row_map_.get(("mul", "reg_x_32")), None
    return None, "NO_CONTRACT_ROW_32"


def match_row(row_map_, mnemonic, operands):
    """v2-aware matcher. v1 behavior preserved when feature flags absent."""
    feats = row_map_.get(FEATURE_KEY, {})
    mflow = False
    mn_raw = mnemonic.lower()
    if mn_raw == "ret" or mn_raw.startswith("ret "):
        if feats.get("allow_ret", False):
            ops_ = analyze_operands(operands)
            if len(ops_) == 0 and (mn_raw in ("ret", "retq")):
                return row_map_.get(("ret", "return")), None
            if len(ops_) == 1 and ops_[0][0] == "imm" and feats.get("allow_ret_imm16", False):
                return row_map_.get(("ret", "return_imm16")), None
            return None, "RET_FORM_UNSUPPORTED"
    _match_gpr_waypoints = None
    ops_probe = analyze_operands(operands)
    if any(c == "reg" and _is_32_reg(p) for c, p in ops_probe):
        if feats.get("allow_gpr32_epl", False):
            r32, why = _match_gpr32(row_map_, mnemonic, ops_probe)
            if r32 is not None:
                return r32, None
            return None, why or "NO_CONTRACT_ROW_32"
        return None, "WIDTH_OUT_OF_DOMAIN_32BIT: 32-bit operand present (v2 flag disabled)"
    op_probe_only = True
    regs8_16 = any(c == "reg" and (_is_8_gpr(p) or _is_16_gpr(p)) for c, p in ops_probe)
    if regs8_16:
        return None, "WIDTH_8_OR_16_BIT_GPR_UNSUPPORTED_IN_v2"
    return _legacy_match_row(row_map_, mnemonic, operands)


def _legacy_match_row(row_map_, mnemonic, operands):
    ops = analyze_operands(operands)
    """Return (row|None, reason)."""
    def _cat(p): return p[0]
    mn = mnemonic.lower()
    # special case: VEX self-xor of a single xmm register
    if mn == "vpxor" and len(ops) == 3:
        if all(c == "xmm" for c, _ in ops):
            xs = [p for _, p in ops]
            if len(set(xs)) == 1:
                return row_map_.get(("vpxor", "xmm_xmm_xmm_self")), None
        return row_map_.get(("vpxor", "xmm_other")), None
    # width gate: ANY 32-bit GPR operand (%eax..%r11d..) -> U (fuera de dominio)
    def _is_32(op):
        return bool(re.match(r"^%e[a-z]+$", op) or re.match(r"^%r([0-9]+|a|b|c|d|bp|sp|di|si|ax)d$", op))
    for c, p in ops:
        if c == "reg" and _is_32(p):
            return None, "WIDTH_OUT_OF_DOMAIN_32BIT: %s" % p
    # lea special-case MUST come before the generic memory-filter: lea is address-arith
    if mn == "lea" and len(ops) == 2 and ops[0][0] == "mem" and ops[1][0] == "reg":
        return row_map_.get(("lea", "reg_sib")), None
    # memory op present (any operand)
    has_mem = any(c in ("mem", "rip") for c, _ in ops)
    if has_mem:
        if mn == "mov" and len(ops) == 2:
            regs = [p for c, p in ops if c == "reg"]
            if len(regs) == 1 and re.match(r"^%a[lhx]?l?$", regs[0]):
                # MOV_RM8_STORE: mov %al,(%rdi)
                return row_map_.get(("mov", "reg8_mem")), None
            if ops[0][0] == "mem" and ops[1][0] == "reg":
                return row_map_.get(("mov", "mem_reg")), None
            return row_map_.get(("mov", "reg_mem")), None
        # memory read/write sin contrato explicito
        return None, "MEMORY_OP_NO_VALIDATED_ROW"
    # reg,reg
    if len(ops) == 2 and ops[0][0] == "imm" and ops[1][0] == "reg":
        r = row_map_.get((mn, "imm_reg"))
        if r: return r, None
        return None, "NO_CONTRACT_ROW"
    if len(ops) == 2 and ops[0][0] == "reg" and ops[1][0] == "reg":
        r = row_map_.get((mn, "reg_reg"))
        if r: return r, None
        return None, "NO_CONTRACT_ROW"
    if len(ops) == 2 and ops[0][0] == "reg" and ops[1][0] == "imm":
        r = row_map_.get((mn, "reg_imm"))
        if r: return r, None
        return None, "NO_CONTRACT_ROW"
    if len(ops) == 1 and ops[0][0] == "reg":
        if mn == "mul":
            return row_map_.get(("mul", "reg")), None
        return None, "NO_CONTRACT_ROW"
    if mn == "lea" and len(ops) == 2 and ops[0][0] == "reg" and "(" in ops[1][1]:
        # lea reg, mem-sib (SIB adress-arith; no real memory access)
        return row_map_.get(("lea", "reg_sib")), None
    if mn == "jle" or mn == "jne" or mn == "ja":
        return row_map_.get((mn, "branch_rel")), None
    if len(ops) == 2 and ops[0][0] == "reg" and ops[1][0] == "imm":
        return row_map_.get((mn, "reg_imm")), None
    return None, "NO_CONTRACT_ROW"

FLAGS_YES = {"yes", "composite"}  # composite degrades but still "represented"
def flag_class(row):
    return row.get("flag_evidence") or row.get("flags") or "no"

def worst(a, b):
    return a if PRECEDENCE[a] >= PRECEDENCE[b] else b

def classify_block(block_lines, contract, binary_size=None):
    """block_lines: list of raw objdump text lines. Returns dict verdict."""
    rows = row_map(contract)
    instructions = []
    verdict = "FAITHFUL"
    reasons = []
    skipped_cont = 0
    last_flag_producer = None  # row for flag source tracking
    n_sig = 0

    # NOP class detection (multibyte/space no-ops parsed as mnemonics like nopl, data16, cs nopw...)
    NOP_RE = re.compile(r"^(data16|cs|fs|gs|ss|nopl|nopw|nop|endbr64)\b")
    for ln, line in enumerate(block_lines):
        inst, err = parse_instruction(line, ln)
        if err == "CONTB":
            skipped_cont += 1
            continue
        if err:
            return {"verdict": "INVALID", "reasons": [err], "instructions": [], "block_index": None}
        if inst is None:
            if LABEL_RE.match(line):
                continue
            if line.strip().startswith("#"):
                continue
            # un-parseable line: suspicious but not necessarily fatal
            # (objdump prints '...' lines for elided regions with NOP-like semantics — treat
            # as neutral padding, skip)
            if BARE_CORRUPT.search(line):
                return {"verdict": "INVALID", "reasons": ["BARE_CORRUPT: %r" % line.rstrip("\n")], "instructions": [], "block_index": None}
            continue
        # NOP class
        m_low = inst.mnemonic.lower()
        if NOP_RE.match(m_low):
            instructions.append({"addr": hex(inst.addr), "mnemonic": inst.mnemonic, "operands": inst.operands,
                                 "nbytes": inst.nbytes, "tier": "A", "row": "NOP_CLASS", "verdict": "FAITHFUL", "reasons": ["NOP_CLASS"]})
            n_sig += 1
            continue
        row, why = match_row(rows, inst.mnemonic, inst.operands)
        # hard exclusions / out-of-domain
        if inst.mnemonic.lower() in ["vmovdqa32", "vpternlogd", "vpcmpb", "vpaddq", "vpmovzxdq", "vpmovzxwd"]:
            verdict = worst(verdict, "UNSUPPORTED")
            reasons.append("EVEX_OUT_OF_DOMAIN: %s @0x%x" % (inst.mnemonic, inst.addr))
            instructions.append({"addr": hex(inst.addr), "mnemonic": inst.mnemonic, "operands": inst.operands,
                                 "nbytes": inst.nbytes, "tier": "U", "row": None, "verdict": "UNSUPPORTED", "reasons": ["EVEX_OUT_OF_DOMAIN"]})
            n_sig += 1
            last_flag_producer = None
            continue
        if row is None:
            verdict = worst(verdict, "UNSUPPORTED")
            reasons.append("UNSUPPORTED_INSTRUCTION: %s @0x%x (%s)" % (inst.mnemonic, inst.addr, why or "NO_CONTRACT_ROW"))
            instructions.append({"addr": hex(inst.addr), "mnemonic": inst.mnemonic, "operands": inst.operands,
                                 "nbytes": inst.nbytes, "tier": "U", "row": None, "verdict": "UNSUPPORTED",
                                 "reasons": [why or "NO_CONTRACT_ROW"]})
            n_sig += 1
            last_flag_producer = None
            continue
        tier = row["tier"]
        if tier == "A":
            inst_verdict = "FAITHFUL"
        elif tier == "A-weak":
            inst_verdict = "PARTIAL"
            reasons.append("WEAK_VALIDATION: %s @0x%x (composite)" % (inst.mnemonic, inst.addr))
        elif tier == "B":
            inst_verdict = "PARTIAL"
            reasons.append("PARTIAL_INSTRUCTION: %s @0x%x (tier B)" % (inst.mnemonic, inst.addr))
        else:
            inst_verdict = "UNSUPPORTED"
            reasons.append("UNSUPPORTED_INSTRUCTION: %s @0x%x (tier %s)" % (inst.mnemonic, inst.addr, tier))
        verdict = worst(verdict, inst_verdict)
        # flag consumption & validity
        reads = row.get("reads_flags") or []
        if inst.mnemonic.lower() in ("jle", "ja", "jne", "je", "jl", "jg", "jge", "jle"):
            # check producing flags
            if last_flag_producer is None:
                verdict = worst(verdict, "PARTIAL")
                reasons.append("FLAGS_PRODUCER_UNKNOWN: %s @0x%x reads flags without tracked valid producer" % (inst.mnemonic, inst.addr))
            else:
                fe = flag_class(last_flag_producer)
                if fe not in ("yes",):
                    verdict = worst(verdict, "PARTIAL")
                    reasons.append("FLAGS_WEAK: %s @0x%x reads flags produced by %s (%s not sufficient for FAITHFUL)" % (inst.mnemonic, inst.addr, last_flag_producer["mnemonic"], fe))
        # memory effects
        mem = row.get("effects", {}).get("memory", "none")
        if mem not in ("none",):
            row_mem = worst(verdict, "PARTIAL")
            if inst_verdict == "UNSUPPORTED":
                pass  # already worse
            elif mem != "none":
                # any unvalidated memory escápe: degrade to PARTIAL (write or read)
                verdict = worst(verdict, "PARTIAL")
                reasons.append("MEMORY_EFFECT_UNVALIDATED: %s @0x%x (%s)" % (inst.mnemonic, inst.addr, mem))
        instructions.append({"addr": hex(inst.addr), "mnemonic": inst.mnemonic, "operands": inst.operands,
                             "nbytes": inst.nbytes, "tier": tier, "row": row["id"], "verdict": inst_verdict,
                             "reasons": [], "reads_flags": reads or []})
        n_sig += 1
        if row.get("effects", {}).get("flags") == "write" or inst.mnemonic.lower() in ("and", "sub", "add", "cmp", "test", "shr", "or", "xor"):
            last_flag_producer = row
        else:
            # non-flag-writing instruction; flags untouched
            pass
    # branch target sanity against block bounds handled by caller (needs file bounds)
    if n_sig == 0:
        # un bloque etiquetado sin instrucciones analizables: roto (formato inesperado)
        return {"verdict": "INVALID", "reasons": ["EMPTY_BLOCK: bloque etiquetado sin instrucciones"], "instructions": [], "block_index": None}
    if verdict == "FAITHFUL" and any(i["verdict"] != "FAITHFUL" for i in instructions):
        verdict = "PARTIAL"
    return {"verdict": verdict, "reasons": sorted(set(reasons)), "instructions": instructions, "skipped_cont": skipped_cont, "block_index": None}

def split_blocks(dump_text):
    """Split objdump -d --no-show-raw-insn output into (label|None, lines) blocks."""
    blocks = []
    cur, name = [], None
    for line in dump_text.splitlines(keepends=True):
        if LABEL_RE.match(line):
            if cur:
                blocks.append((name, cur))
            name = LABEL_RE.match(line).group(2)
            cur = [line]
        else:
            cur.append(line)
    if cur:
        blocks.append((name, cur))
    # normalize: strip comment/header noise lines; keep instruction lines + labels
    cleaned = []
    for name, lines in blocks:
        cleaned.append((name, lines))
    return cleaned

def classify_dump(dump_text, domain_file: str = DOMAIN_PATH):
    """Top-level: dump text -> {verdict, blocks, summary}."""
    contract = load_contract(domain_file)
    blocks = split_blocks(dump_text)
    out = []
    for name, lines in blocks:
        res = classify_block(lines, contract)
        res["label"] = name
        res["size"] = len([1 for l in lines if LINE_RE.match(l or "")])
        # preamble/header junk objdump emite antes del primer simbolo no es un bloque de codigo;
        # no propagar como bloque de codigo (evita INVALID espurio)
        if name is None and not res.get("instructions"):
            continue
        out.append(res)
    counts = {s: 0 for s in PRECEDENCE}
    for b in out:
        counts[b["verdict"]] += 1
    global_verdict = "FAITHFUL"
    for b in out:
        global_verdict = worst(global_verdict, b["verdict"])
    return {
        "verdict": global_verdict,
        "blocks": out,
        "summary": {
            "n_blocks": len(out),
            **counts,
        },
        "domain_file": domain_file,
        "domain_hash": domain_hash(domain_file),
        "contract_version": contract["contract_version"],
    }

def promotion_gate(summary):
    """Gate: is any part of this dump eligible for treating as reconstructed?"""
    blocked = {"PARTIAL", "UNSUPPORTED", "INVALID"}
    return (summary["verdict"] == "FAITHFUL"), {
        "reason": "" if summary["verdict"] == "FAITHFUL" else "bloque no FAITHFUL: gate de promocion deniega",
        "verdict": summary["verdict"],
    }

def main(argv=None):
    ap = argparse.ArgumentParser(description="RXRE fidelity frontier (Plan LXXI)")
    ap.add_argument("command", choices=["dump", "binary"])
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.command == "binary":
        import subprocess
        dump_text = subprocess.check_output(["objdump", "-d", args.path], text=True)
    else:
        with open(args.path, "r", encoding="utf-8", errors="replace") as f:
            dump_text = f.read()
    result = classify_dump(dump_text)
    verdict, blocks, summary = result["verdict"], result["blocks"], result["summary"]
    ok, gate = promotion_gate(result)
    result["gate"] = gate
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("verdict:", verdict)
        print("blocks:", summary["n_blocks"], {k: v for k, v in summary.items() if k != "n_blocks"})
        for b in blocks:
            print(" ", b.get("label"), hex(1) if False else b["verdict"], len(b["instructions"]), "insn")
    return 0 if verdict == "FAITHFUL" else (2 if verdict == "PARTIAL" else (3 if verdict == "UNSUPPORTED" else 4))

if __name__ == "__main__":
    sys.exit(main())
