#!/usr/bin/env python3
"""RXRE-1639 — THUMB ORACLE diferencial para LDR/LDRB (literal, T2).

Capacidad de RXRE: comparar el decodificador externo (p. ej. miasm) contra el
oraculo interno RXRE (adapter cs_disasm sobre capstone), familia por familia,
over 4096 offsets por familia.

    RXRE (capstone 5.0.7 in-process)  vs  decodificador candidato

    Devuelve:
      - status: ok/blocked/error
      - bytes_compared, bytes_matched, coverage_pct
      - disagreements: [{imm, rxre, candidate}] (vacio si concuerdan)

Caso real: MIASM issue #1570 (LDR/LDRB literal U=0 decoded as register-offset / PC-writeback).

Uso:
    MIASM_CLONE=/path/al/clone python3 outils/rxre/analysis/thumb_literal_oracle.py \
        --family ldr_neg --candidate-python /path/a/su_venv_python
"""
import os
import sys
import subprocess
import tempfile
import json
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.adapters import cs_disasm

CASES = {
    "ldr_neg":  {"prefix": bytes([0x5f, 0xf8]), "kind": "LDR"},
    "ldrb_neg": {"prefix": bytes([0x1f, 0xf8]), "kind": "LDRB"},
    "ldr_pos":  {"prefix": bytes([0xdf, 0xf8]), "kind": "LDR"},
    "ldrb_pos": {"prefix": bytes([0x9f, 0xf8]), "kind": "LDRB"},
}

_CANDIDATE = r'''
import sys
sys.path.insert(0, sys.argv[1])
from miasm.arch.arm.arch import mn_armt
from miasm.core.bin_stream import bin_stream_str
cases = CASES_JSON
for name, spec in cases.items():
    prefix = bytes(spec['prefix'])
    for imm in range(4096):
        b = prefix + bytes([imm & 0xff, (imm >> 8) & 0xff])
        try:
            ins = mn_armt.dis(bin_stream_str(b), 'l', 0)
            mn = str(ins).replace('\t', ' ').replace('\n', ' ')
            length = ins.l
        except Exception as e:
            mn = 'EXC:%s' % e.__class__.__name__
            length = -1
        print('%s\t%d\t%s\t%d' % (name, imm, mn, length))
'''


def compare_family(family, candidate_python):
    miasm_clone = os.environ.get("MIASM_CLONE")
    if not miasm_clone:
        return {"status": "BLOCKED",
                "limitations": ["MIASM_CLONE no apunta al clone de miasm. "
                                "Exporta MIASM_CLONE=/ruta/al/clone."]}
    if family not in CASES:
        return {"status": "BLOCKED",
                "limitations": ["familia desconocida: %r. Use %s." % (family, sorted(CASES))]}

    with tempfile.TemporaryDirectory(prefix="rxre-tlo-") as td:
        script = os.path.join(td, "candidate.py")
        with open(script, "w") as f:
            f.write(_CANDIDATE.replace("CASES_JSON",
                                       json.dumps({k: {"prefix": list(v["prefix"])}
                                                    for k, v in CASES.items()})))
        out = subprocess.run([candidate_python, script, miasm_clone],
                             capture_output=True, text=True, timeout=600)
        if out.returncode != 0:
            return {"status": "ERROR",
                    "limitations": ["candidato error rc=%d: %s" % (out.returncode, out.stderr.strip()[:400])]}

        art_dir = tempfile.mkdtemp(prefix="rxre-tlo-art-")
        art = os.path.join(art_dir, "case.bin")
        prefix = CASES[family]["prefix"]
        buf = bytearray()
        for imm in range(4096):
            buf += prefix + bytes([imm & 0xff, (imm >> 8) & 0xff])
        with open(art, "wb") as fh:
            fh.write(buf)

    # El adapter cs_disasm devuelve hasta 4000 instrucciones (limite de
    # contrato). Decodificamos en ventanas de 1024 instrucciones (4096 bytes).
    rxre_instr = []
    cobertura = []
    for w in range(4):
        inicio = w * 1024 * 4
        try:
            res = cs_disasm.desensamblar(artefacto=art, inicio=inicio, longitud=4096,
                                         arquitectura="thumb", fixture_bin=art)
        except TypeError:
            res = cs_disasm.desensamblar(artefacto=art, inicio=inicio, longitud=4096,
                                         arquitectura="thumb")
        if res.get("status") != "ok":
            return {"status": "ERROR",
                    "limitations": ["RXRE capstone fallo en la ventana %d: %s / limitations=%s" % (inicio, res.get("status"), res.get("limitations", [])[:3])]}
        ventana = res["results"][0]["value"]["instrucciones"]
        rxre_instr += ventana
        cobertura.append(res.get("cobertura", {}).get("cobertura_pct", 0.0))
    if len(rxre_instr) != 4096:
        return {"status": "ERROR",
                "limitations": ["RXRE devolvio %d instrucciones en ventanas, se esperaban 4096" % len(rxre_instr)]}

    rows = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        fam, imm, mn, length = parts
        rows[(fam, int(imm))] = {"mn": mn, "len": int(length)}

    disagreements = []
    for imm in range(4096):
        r = _categorize_rxre(rxre_instr[imm]);
        row = rows.get((family, imm))
        c = _categorize_candidate(row["mn"] if row else "")
        if r is None or c is None:
            disagreements.append({"imm": imm, "rxre": r, "candidate": row})
            continue
        if (r.get("base") != c.get("base")
                or r.get("reg") != c.get("reg")
                or (r.get("disp") is not None and c.get("disp") is not None
                    and int(r["disp"]) != int(c["disp"]))
                or (r.get("disp") is not None) != (c.get("disp") is not None)):
            disagreements.append({"imm": imm, "rxre": r, "candidate": row})

    return {"status": "ok", "family": family,
            "bytes_compared": 4096, "bytes_matched": 4096 - len(disagreements),
            "coverage_pct": min(cobertura) if cobertura else 0.0,
            "disagreements": disagreements}


def _categorize_rxre(instr):
    mn = (instr.get("mnemonico") or "").lower()
    ops = instr.get("operandos", [])
    if not ops:
        return None
    dest = None
    base = None
    disp = None
    for o in ops:
        if o.get("tipo") == "reg":
            dest = o.get("reg")
        elif o.get("tipo") == "mem":
            base = o.get("base")
            disp = o.get("desplazamiento")
    return {"op": mn.lstrip(".w").lower(), "base": base, "disp": disp, "reg": dest}


_OP_ID = {"ldr": "ldr", "ldrb": "ldrb", "ldrh": "ldrh"}

def _categorize_candidate(texto):
    t = texto.replace(' ', '').lower()
    m = re.match(r'^(ldr|ldrb|ldrh)(r0|r1|r2|r3|r4|r5|r6|r7|r8|r9|r10|r11|r12|lr|pc|sp|r7|r8|r9|r10|r11|r12|fp),\[([^\]]+)\]', t)
    if not m:
        return None
    mn, dest, mem = m.groups()
    parts = [p.strip() for p in mem.split(',')]
    if len(parts) == 1:
        base = parts[0]
        return {"op": _OP_ID.get(mn, mn), "base": base, "disp": 0, "reg": dest}
    if len(parts) == 2:
        base = parts[0]
        off = parts[1].rstrip(']')
        if off.startswith('r') or off in ('pc', 'sp'):
            return {"op": _OP_ID.get(mn, mn), "base": base, "disp": None, "reg": dest}
        try:
            val = int(off, 16)
            if val & 0x80000000:
                val -= 0x100000000
            return {"op": _OP_ID.get(mn, mn), "base": base, "disp": val, "reg": dest}
        except ValueError:
            return None
    return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=sorted(CASES))
    ap.add_argument("--candidate-python", required=True)
    a = ap.parse_args()
    out = compare_family(a.family, a.candidate_python)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
