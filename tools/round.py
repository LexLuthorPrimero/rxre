#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY  .  WRITE_EXECUTION=NONE  .  STATIC_ANALYSIS

"""
round -- the documentation round, as a pipeline.

WHY THIS EXISTS
---------------
For twenty rounds the same eleven steps were performed by hand, in the same order,
with the same ad-hoc shell.  Each round re-derived the same measurements slightly
differently, and a check that changes shape between rounds is not a check.

The step that cost the most was not any of them.  It was this one:

    read every new finding, extract its numbers, and decide whether it agrees with
    what the running kernel printed at boot

That step, done by hand, decided three of the day's substantive results:

    C-009   block_size = 10 vs 22 vs 13
            arbitrated by the `dev_info` of amdgpu_vm.c:2463, which prints
            "block size is 10-bit"
    C-010   the PM4 specification does not exist
            arbitrated by COUNTING 637 pages of a document already on disk
    C-011   the PTE emitter is sdma_v3_0, not sdma_v4_0
            arbitrated by the ip-block dispatch and the boot log's funcs->name

Each of those was reachable by a command.  None of them was run as a command,
because no command existed.  This file is that command, generalised.

WHAT IT DOES, AND WHAT IT DELIBERATELY DOES NOT
-----------------------------------------------
It PROPOSES.  It never writes a claim into docs/ and never edits a finding.

  1 scan        compose docscan and toolreg, report their verdicts
  2 new         which findings have appeared that this round has never seen
  3 claims      extract the numeric claims of those findings
  4 arbitrate   for the claims that have a HOST ARBITER, check them against the
                running kernel, and say which agree and which do not
  5 conflicts   COMPOSED, not reimplemented.  `causal_map.py --contradictions`
                already indexes the findings' classified claims, weights them by
                STATE (PROVEN over debil) and finds the disagreement from the FIRST
                document rather than the third.  An earlier version of this file grew
                its own conflict detector, which duplicated that work and did it worse.
                The composition rule says prefer the existing tool, so it is composed
                here and the local one is gone
  6 verdict     a machine-readable TOOL_PARTIAL / TOOL_VALIDATED classification

The line between what it decides and what it proposes is the whole design.  Step 4
decides only "does this number appear in the kernel's own output", which is a
measurement.  It never decides that a finding is wrong.  A disagreement is
REPORTED as `CONFLICT`, and what it means is left to whoever reads it.

HOST ARBITERS, DECLARED, AND WHY THE LIST IS SHORT
-------------------------------------------------
An arbitrator is a value the running kernel prints, so it can settle a static
reading without a human.  There are four, and the list is deliberately short:

    amdgpu vm size is <N> GB, <M> levels, block size is <B>-bit,
                             fragment size is <F>-bit
        -> vm_size, num_level (as M-1), block_size, fragment_size
    detected ip block number <N> <TYPE_vM_m_r> (<FUNCS_NAME>)
        -> SDMA0_HWIP per block type, and the funcs->name that is actually installed
    amdgpu <BDF>: VRAM: <total> Kbyte visible
        -> visible VRAM
    <BDF>: amdgpu device <...>
        -> nothing.  Declared so the list is exhaustive, not because it arbitrates

Anything not in that list gets no verdict.  A tool that reports "no evidence" for
most of its inputs, and a firm verdict for the few it can actually settle, is
worth more than one that guesses on all of them.

PIPELINE
--------
    round.py --repo .                 the whole pipeline, one report
    round.py --repo . --only arbitrate
    round.py --repo . --json
    round.py --repo . --accept        record the findings it has seen, so "new" means new
    round.py --selftest

SAFETY
------
Reads files.  Reads the kernel's ring buffer via `journalctl -k -b`, which is a
read of a log.  Does not write to docs/, does not edit findings, does not touch
the GPU, does not open /sys, does not load modules, does not compile.

The ONLY file it ever writes is its own state file, and only with --accept.
Without --accept it is strictly read-only, which is why that flag exists as a
separate, visible act.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

VERSION = "1.0.0"
TOOL = "round"

STATE_REL = "docs/.round-state.json"


# --------------------------------------------------------------------------
# kernel arbiter
# --------------------------------------------------------------------------

RE_VM_SIZE = re.compile(
    r"vm size is (?P<vm_size>\d+)\s*GB,\s*(?P<levels>\d+)\s*levels,\s*"
    r"block size is (?P<block_size>\d+)-bit,\s*fragment size is (?P<fragment>\d+)-bit"
)

RE_IPBLOCK = re.compile(
    r"detected ip block number\s+\d+\s+<(?P<type>\w+?)_v(?P<maj>\d+)_(?P<min>\d+)_"
    r"(?P<rev>\d+)>\s+\((?P<funcs>\w+)\)"
)

# The ONLY arbitrable subjects.  Each maps a claim key to the kernel field that
# settles it.  Nothing outside this table gets a verdict.
ARBITER_TABLE = {
    "block_size":     ("vm_size", "block_size"),
    "fragment_size":  ("vm_size", "fragment"),
    "vm_size_gb":     ("vm_size", "vm_size"),
    "num_level":      ("vm_size", "levels_minus_one"),
    "sdma_hwip":      ("ipblock", "sdma"),
    "gfx_hwip":       ("ipblock", "gfx"),
    "gmc_hwip":       ("ipblock", "gmc"),
    "sdma_funcs":     ("ipblock", "sdma"),
    "ih_funcs":       ("ipblock", "ih"),
    "vce_funcs":      ("ipblock", "vce"),
    "uvd_funcs":      ("ipblock", "uvd"),
}

# How a kernel field is derived into a comparable claim value.
DERIVE = {
    "vm_size": lambda f: int(f["vm_size"]),
    "block_size": lambda f: int(f["block_size"]),
    "fragment": lambda f: int(f["fragment"]),
    "levels_minus_one": lambda f: int(f["levels"]) - 1,
}

IPBLOCK_TYPE_BY_FUNCS = {
    "sdma_v3_0": "sdma", "sdma_v4_0": "sdma", "sdma_v5_0": "sdma",
    "gfx_v8_0": "gfx", "gmc_v8_0": "gmc", "tonga_ih": "ih",
    "vce_v3_0": "vce", "uvd_v6_0": "uvd", "uvd_v5_0": "uvd",
    "powerplay": "smu", "dm": "dce", "vi_common": "common",
}

IPBLOCK_HWIP_KEY = {"sdma": "sdma_hwip", "gfx": "gfx_hwip", "gmc": "gmc_hwip"}


def read_kernel_log(timeout=45):
    """
    The kernel's own self-report, read from the ring buffer.

    `journalctl -k -b` is a LOG READ.  It is not a hardware access, it cannot
    change state, and it is the source that settled C-009 and C-011.  If it is
    unavailable the tool says NOT_AVAILABLE and produces no verdict; it never
    falls back to guessing.
    """
    try:
        r = subprocess.run(["journalctl", "-k", "-b", "--no-pager"],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if r.returncode != 0 or not r.stdout.strip():
        return None, "journalctl rc=%d" % r.returncode
    return r.stdout, None


def kernel_facts(text):
    """The arbitrable values, extracted from the kernel's own words."""
    facts = {}
    vm = RE_VM_SIZE.search(text)
    if vm:
        f = vm.groupdict()
        for key, fn in DERIVE.items():
            facts[key] = fn(f)
    blocks = {}
    for m in RE_IPBLOCK.finditer(text):
        blocks[m.group("funcs")] = {
            "type": m.group("type"),
            "version": "%s.%s.%s" % (m.group("maj"), m.group("min"), m.group("rev")),
            "mac": (int(m.group("maj")), int(m.group("min")), int(m.group("rev"))),
        }
    if blocks:
        facts["ipblocks"] = blocks
        for funcs, info in blocks.items():
            t = IPBLOCK_TYPE_BY_FUNCS.get(funcs)
            if t and t in IPBLOCK_HWIP_KEY:
                facts[IPBLOCK_HWIP_KEY[t]] = info["version"]
    return facts


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

FINDINGS_REL = "06-INGENIERIA-INVERSA/findings"

RE_SECTION = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.M)

# A numeric claim: an identifier, an operator, a number.
RE_NUMCLAIM = re.compile(
    r"`?\b(?P<key>[A-Za-z_][A-Za-z0-9_]{2,})\s*(?P<op>=|==|is|→)\s*"
    r"(?P<val>-?\d+)\b`?"
)

# Keys the ARBITER_TABLE understands, tolerant of case and separators.
def canon_key(k):
    return k.lower().replace("-", "_")


def list_findings(repo):
    d = os.path.join(repo, FINDINGS_REL)
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".md"):
            out.append(os.path.join(d, fn))
    return out


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def sha(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def finding_head(path):
    txt = read_text(path)
    lines = [l for l in txt.split("\n")[:14] if l.strip()]
    title = lines[0].lstrip("# ").strip() if lines else ""
    cls = ""
    for l in lines:
        m = re.search(r"CLASSIFICATION\s*=\s*([A-Z_/]+)", l)
        if m:
            cls = m.group(1)
            break
    return title, cls


def finding_cuda(path, max_chars=1800):
    """The §CUDA section, which is what the documentation actually ingests."""
    txt = read_text(path)
    m = RE_SECTION.search(txt)
    if not m:
        return txt[:max_chars]
    start = m.end()
    nxt = RE_SECTION.search(txt, start)
    body = txt[start:nxt.start() if nxt else len(txt)]
    return body[:max_chars]


# A deliberate mutation injected to prove a detector works.  Finding 041 says,
# verbatim: "y valida por mutacion: anado `block_size = 33 | PROVEN` a un documento y
# lo detecta".  The first version of this extractor read that 33 as a claim about
# the hardware and reported DISAGREE against the kernel, which is a false positive
# on a value that is wrong ON PURPOSE.
MUTATION_RE = re.compile(
    r"mutaci[oó]n|injected|inject|inyect|prueba de (?:que )?funciona|"
    r"mutation|added to a document|for the detector"
)

# A soft claim: the key is named, and the value is a bolded number run, e.g.
#     "declaring block_size as 13, 10 and **22/23/24**"
# The hard form `key = N` misses these entirely, and those are exactly the numbers
# C-009 was about.  Soft claims are reported as a SEPARATE class and never mixed
# into the hard set, because their precision is lower.
# Built from ARBITER_TABLE, so by construction it can only match a key that is
# actually arbitrable.  The first version allowed any word of three or more
# letters and matched the Spanish word "equivoque" in
#     "**Y me equivoque en `block_size`.** Reporte 13/14/15. Es **22/23/24**."
# with the value 13/14/15, and because that match consumed the text it never
# reached the real claim.  A key pattern that can match prose is not a key
# pattern.
_SOFT_ALT = "|".join(sorted((re.escape(k) for k in ARBITER_TABLE),
                             key=len, reverse=True))
RE_SOFTCLAIM = re.compile(
    r"\b(?P<key>%s)\b[^\n]{0,80}?\*\*(?P<val>-?\d+(?:/\d+)*)\*\*" % _SOFT_ALT
)


def split_soft(text):
    """
    Values written as a bolded number run, e.g. **22/23/24**.

    A slash run is ONE claim with three candidate values, not three claims.  They
    are reported as a set so that whoever reads can see that a single sentence
    published three numbers for the same quantity, which is itself the shape of
    C-009 and C-010.
    """
    out = []
    seen = set()
    for m in RE_SOFTCLAIM.finditer(text):
        key = canon_key(m.group("key"))
        if key not in ARBITER_TABLE:
            continue
        if MUTATION_RE.search(text):
            continue
        vals = tuple(int(x) for x in m.group("val").split("/"))
        if (key, vals) in seen:
            continue
        seen.add((key, vals))
        out.append({"key": key, "values": list(vals), "class": "SOFT",
                    "arbitrable": True})
    return out


def extract_claims(text):
    """
    Numeric claims in a text, deduplicated, with the arbitrable ones marked.

    It does NOT interpret them.  It reports what a line says, and which of those
    are arbitrable.  A claim it cannot parse is not a claim it invents: it is
    simply absent, and the coverage line says so.
    """
    claims = []
    seen = set()
    # A text that announces a mutation is a test, not a claim set.  Skipping it
    # whole is safer than trying to tell the mutation line from the real ones,
    # because a single injected wrong value outranks any precision gained.
    if MUTATION_RE.search(text):
        return []
    for m in RE_NUMCLAIM.finditer(text):
        key = canon_key(m.group("key"))
        val = int(m.group("val"))
        arbitrable = key in ARBITER_TABLE
        k = (key, val)
        if k in seen:
            continue
        seen.add(k)
        claims.append({"key": key, "raw_key": m.group("key"),
                       "value": val, "arbitrable": arbitrable,
                       "class": "HARD"})
    return claims


# --------------------------------------------------------------------------
# conflicts
# --------------------------------------------------------------------------

def claims_from_docs(repo):
    """Every numeric claim in docs/, per file, for cross-file conflict search."""
    d = os.path.join(repo, "docs")
    if not os.path.isdir(d):
        return {}
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        out[fn] = extract_claims(read_text(os.path.join(d, fn)))
    return out


def find_conflicts_local(all_sources):
    """
    THE LOCAL VERSION IS KEPT ONLY FOR THE SELF-TEST, and it is NOT used in the
    pipeline.

    It exists so the arbitration step has something to test against without
    depending on another tool being installed, and because writing the naive
    version first is what showed that `causal_map.py` does the job properly: the
    local one has no notion of STATE, so it cannot tell PROVEN from debil, and it
    found the block_size disagreement only on the third document instead of the
    first.  Measured, not assumed.
    """
    """
    The same claim key carrying different values in different places.

    This is the shape every contradiction in this project has taken:
    C-003 block_size 13 vs 10, C-009 block_size 22 vs 10, C-011 emitter v3 vs v4.
    None of them was found by a tool.  All three were found by a human noticing a
    sentence that looked wrong.

    A conflict is a CANDIDATE.  It is not a contradiction: the two values may
    legitimately apply to different ASICs or different corpora.  Naming it is the
    whole value; judging it is not this tool's job.
    """
    by_key = {}
    for src, claims in all_sources.items():
        for c in claims:
            by_key.setdefault(c["key"], {}).setdefault(c["value"], set()).add(src)

    out = []
    for key, vals in by_key.items():
        if len(vals) < 2:
            continue
        ordered = sorted(vals.items())
        out.append({
            "key": key,
            "arbitrable": key in ARBITER_TABLE,
            "values": [{"value": v, "sources": sorted(s)} for v, s in ordered],
            "n_sources": len(set().union(*vals.values())),
        })
    return sorted(out, key=lambda c: (-c["n_sources"], c["key"]))


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------

def load_state(repo):
    p = os.path.join(repo, STATE_REL)
    if not os.path.exists(p):
        return {"seen": {}, "version": VERSION}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            st = json.load(fh)
        if not isinstance(st, dict) or "seen" not in st:
            return {"seen": {}, "version": VERSION}
        return st
    except (OSError, ValueError):
        return {"seen": {}, "version": VERSION}


def save_state(repo, state):
    """The ONLY write this tool ever performs, and only under --accept."""
    p = os.path.join(repo, STATE_REL)
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        return None
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
    return p


# --------------------------------------------------------------------------
# steps
# --------------------------------------------------------------------------

def step_new(findings, state):
    out = []
    for f in findings:
        name = os.path.basename(f)
        h = sha(f)
        prev = state["seen"].get(name)
        if prev != h:
            out.append({"name": name, "sha256": (h or "")[:12],
                        "state": "new" if prev is None else "CHANGED"})
    return out


def step_arbitrate(claims, facts, kernel_err):
    """
    Compare arbitrable claims against the kernel.

    Verdict vocabulary, and the distinctions are load-bearing:
      AGREE        the claim equals what the kernel printed.  That is a fact
      DISAGREE     the claim differs.  ALSO A FACT.  What it MEANS is not decided
      NO_KERNEL    the kernel did not print that field
      NOT_ARBITRABLE  the claim key is outside the declared arbiter table
    No verdict is ever upgraded.  AGREE does not make a claim TRUE, it makes it
    consistent with the hardware's own report, which is one kind of evidence and
    not the strongest.
    """
    rows = []
    for c in claims:
        if not c["arbitrable"]:
            rows.append({**c, "verdict": "NOT_ARBITRABLE"})
            continue
        kind, field = ARBITER_TABLE[c["key"]]
        if kernel_err or facts is None:
            rows.append({**c, "verdict": "NO_KERNEL",
                         "detail": kernel_err or "no kernel log"})
            continue
        if kind == "vm_size":
            if field not in facts:
                rows.append({**c, "verdict": "NO_KERNEL",
                             "detail": "no vm-size line in the kernel log"})
                continue
            kern = facts[field]
        else:
            f = facts.get("ipblocks") or {}
            target = IPBLOCK_TYPE_BY_FUNCS.get(field)
            # find the installed block whose TYPE matches
            found = None
            for funcs, info in f.items():
                if IPBLOCK_TYPE_BY_FUNCS.get(funcs) == target:
                    found = (funcs, info)
                    break
            if found is None:
                rows.append({**c, "verdict": "NO_KERNEL",
                             "detail": "no %s block in the kernel log" % field})
                continue
            if field == "sdma_hwip":
                kern = found[1]["version"]
            else:
                rows.append({**c, "verdict": "NO_KERNEL",
                             "detail": "string-valued: see kernel_facts"})
                continue
        verdict = "AGREE" if c["value"] == kern else "DISAGREE"
        rows.append({**c, "verdict": verdict, "kernel_value": kern})
    return rows


# Tools live in two directories.  Looking only in tools/ reported causal_map as
# NOT INSTALLED, which is the same mistake toolreg had and had to be corrected
# for.  A composition that cannot find the thing it composes is not a composition.
TOOL_DIRS = ("tools", "08-ARQUITECTURA/tools")


def find_tool(repo, name):
    for rel in TOOL_DIRS:
        for cand in (os.path.join(repo, rel, name + ".py"),
                     os.path.join(repo, rel, name)):
            if os.path.exists(cand):
                return cand
    return None


def run_composed(repo, name, args):
    """Compose an existing tool.  Never reimplement what already exists."""
    for cand in [c for c in (find_tool(repo, name),) if c]:
        if os.path.exists(cand):
            cmd = [sys.executable, cand] if cand.endswith(".py") else [cand]
            cmd += args
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=600, cwd=repo)
                return {"tool": name, "rc": r.returncode,
                        "tail": (r.stdout.strip().splitlines() or [""])[-3:]}
            except subprocess.TimeoutExpired:
                return {"tool": name, "rc": None, "tail": ["TIMEOUT"]}
    return {"tool": name, "rc": None, "tail": ["NOT INSTALLED"]}


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def build_fixture(root):
    fd = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    os.makedirs(fd, exist_ok=True)
    with open(os.path.join(fd, "001-bueno.md"), "w", encoding="utf-8") as fh:
        fh.write("# 001 · uno bueno\n\n`GPU INTACTA`\n\n## CUDA principal\n\n"
                 "El valor medido es block_size = 10 y num_level = 1.\n"
                 "herramientas = 44 y algo_raro = 7.\n")
    with open(os.path.join(fd, "002-contradice.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · otro que no coincide\n\n## CUDA principal\n\n"
                 "Reporté block_size = 22 y fragment_size = 9.\n")
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "E.md"), "w", encoding="utf-8") as fh:
        fh.write("block_size = 10 en docs\n")


KERNEL_FIXTURE = (
    "amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, "
    "fragment size is 9-bit\n"
    "amdgpu 0000:01:00.0: detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)\n"
    "amdgpu 0000:01:00.0: detected ip block number 3 <gfx_v8_0_0> (gfx_v8_0)\n"
)

KERNEL_WRONG = (
    "amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 22-bit, "
    "fragment size is 9-bit\n"
)


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 66)
    fails = 0
    checks = 0

    # --- the kernel parser, on both a right and a wrong log
    facts = kernel_facts(KERNEL_FIXTURE)
    # These are the INTERNAL fact names produced by DERIVE, which are not the
    # claim names in ARBITER_TABLE.  An earlier version of this test asserted
    # on the claim names and so failed on four checks that were actually
    # passing, which is how a test can hide a working tool.
    cases = [
        ("block_size", 10),
        ("fragment", 9),
        ("levels_minus_one", 1),
        ("vm_size", 64),
    ]
    for key, want in cases:
        checks += 1
        got = facts.get(key)
        if got == want:
            print("  OK    kernel log  %-18s = %s" % (key, got))
        else:
            print("  FAIL  kernel log  %-18s got %r, expected %s" % (key, got, want))
            fails += 1

    checks += 1
    if facts.get("sdma_hwip") == "3.1.0":
        print("  OK    kernel log  sdma_hwip       = %s" % facts["sdma_hwip"])
    else:
        print("  FAIL  sdma_hwip = %r, expected 3.1.0" % facts.get("sdma_hwip"))
        fails += 1

    # --- the negative control that matters: a wrong log must NOT be trusted
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        build_fixture(td)
        findings = list_findings(td)

        checks += 1
        if len(findings) == 2:
            print("  OK    inventory finds both fixture findings")
        else:
            print("  FAIL  inventory found %d, expected 2" % len(findings))
            fails += 1

        # arbitration: AGREE / DISAGREE, and DISAGREE on a real disagreement
        claims = extract_claims(finding_cuda(findings[0]))
        rows = step_arbitrate(claims, facts, None)
        by = {(r["key"]): r for r in rows}
        checks += 1
        if by.get("block_size", {}).get("verdict") == "AGREE":
            print("  OK    a claim equal to the kernel's is AGREE")
        else:
            print("  FAIL  block_size verdict = %r"
                  % by.get("block_size", {}).get("verdict"))
            fails += 1

        checks += 1
        wrong_claims = extract_claims(finding_cuda(findings[1]))
        wrows = step_arbitrate(wrong_claims, facts, None)
        wb = {r["key"]: r for r in wrows}
        checks += 1
        if wb.get("block_size", {}).get("verdict") == "DISAGREE" and \
           wb.get("fragment_size", {}).get("verdict") == "AGREE":
            print("  OK    22 vs 10 is DISAGREE, and 9 vs 9 is AGREE")
        else:
            print("  FAIL  wrong-log verdicts: %s"
                  % {k: v.get("verdict") for k, v in wb.items()})
            fails += 1

        # a non-arbitrable key must be marked, never guessed
        checks += 1
        nonarb = [r for r in rows if r["verdict"] == "NOT_ARBITRABLE"]
        if nonarb and all(r["key"] in ("herramientas", "algo_raro")
                          for r in nonarb):
            print("  OK    %d non-arbitrable claims marked, not guessed: %s"
                  % (len(nonarb), ", ".join(sorted(r["key"] for r in nonarb))))
        else:
            print("  FAIL  non-arbitrable claims handled wrong: %s"
                  % [(r["key"], r["verdict"]) for r in rows])
            fails += 1

        # NO_KERNEL: the tool must produce no verdict when the log is absent
        checks += 1
        nrows = step_arbitrate(claims, None, "journalctl not available")
        if all(r["verdict"] in ("NO_KERNEL", "NOT_ARBITRABLE") for r in nrows):
            print("  OK    no kernel log -> NO_KERNEL, never a guess")
        else:
            print("  FAIL  without a kernel log some verdict was invented")
            fails += 1

        # and a kernel log that says something else must DISAGREE, not pass
        checks += 1
        f2 = kernel_facts(KERNEL_WRONG)
        r2 = step_arbitrate(extract_claims(finding_cuda(findings[0])), f2, None)
        b2 = {r["key"]: r for r in r2}
        if b2.get("block_size", {}).get("verdict") == "DISAGREE":
            print("  OK    a kernel log saying 22 makes our 10 DISAGREE")
        else:
            print("  FAIL  the wrong-log control did not flip the verdict")
            fails += 1

        # conflict detection across findings AND docs
        checks += 1
        allsrc = {os.path.basename(f): extract_claims(finding_cuda(f))
                  for f in findings}
        allsrc.update(claims_from_docs(td))
        conf = find_conflicts_local(allsrc)
        keys = {c["key"] for c in conf}
        if "block_size" in keys:
            c = [x for x in conf if x["key"] == "block_size"][0]
            vals = sorted(v["value"] for v in c["values"])
            print("  OK    conflict named: block_size carries %s across %d sources"
                  % (vals, c["n_sources"]))
        else:
            print("  FAIL  block_size conflict not found; keys=%s" % keys)
            fails += 1

        # state: new, then not new
        checks += 1
        st = load_state(td)
        new = step_new(findings, st)
        if len(new) == 2:
            print("  OK    both fixture findings are new to an empty state")
        else:
            print("  FAIL  step_new reported %d" % len(new))
            fails += 1

        checks += 1
        st["seen"] = {os.path.basename(f): sha(f) for f in findings}
        if step_new(findings, st) == []:
            print("  OK    a second scan finds nothing new (idempotent)")
        else:
            print("  FAIL  step_new is not idempotent")
            fails += 1

        # BOTH files present in seen, one with the right hash and one wrong:
        # then one must be unchanged and one must be CHANGED, and neither new.
        checks += 1
        partial = {os.path.basename(findings[0]): sha(findings[0]),
                   os.path.basename(findings[1]): "stale"}
        got = step_new(findings, {"seen": partial})
        states = sorted(n["state"] for n in got)
        if states == ["CHANGED"]:
            print("  OK    a CHANGED file is distinguished from a new one")
        else:
            print("  FAIL  expected exactly one CHANGED, got %s" % states)
            fails += 1

        # --accept writes, and nothing else does
        checks += 1
        p = save_state(td, st)
        if p and os.path.exists(p):
            print("  OK    --accept writes the state file")
        else:
            print("  FAIL    the state file was not written")
            fails += 1

    print("  " + "-" * 66)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: esta herramienta PROPONE. No escribe ninguna afirmación en docs/ y")
    print("        no edita ningún hallazgo. Un AGREE significa «consistente con el")
    print("        autoinforme del kernel», que es una clase de evidencia, no la más")
    print("        fuerte. Un DISAGREE es un hecho medido sobre lo que dice el kernel; lo")
    print("        que SIGNIFICA lo decide quien lee.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="round", description="the documentation round, as a pipeline")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--only", action="append", default=[],
                    choices=("scan", "new", "claims", "arbitrate", "conflicts"))
    ap.add_argument("--accept", action="store_true",
                    help="record the findings seen. THE ONLY WRITE this tool performs")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    steps = set(args.only) if args.only else {"scan", "new", "claims",
                                              "arbitrate", "conflicts"}
    findings = list_findings(repo)
    state = load_state(repo)
    ktext, kerr = read_kernel_log()
    facts = kernel_facts(ktext) if ktext else None

    report = {"tool": TOOL, "version": VERSION, "repo": repo,
              "kernel_log": "read" if ktext else ("unavailable: %s" % kerr)}

    if "scan" in steps:
        report["scan"] = {
            "docscan": run_composed(repo, "docscan", ["--repo", repo]),
            "toolreg": run_composed(repo, "toolreg", ["--repo", repo,
                                                      "--no-selftest"]),
        }
    if "new" in steps:
        report["new"] = step_new(findings, state)
    if "claims" in steps:
        report["claims"] = {}
        report["soft_claims"] = {}
        for f in findings:
            cuda = finding_cuda(f)
            cs = extract_claims(cuda)
            arbitrable = [c for c in cs if c["arbitrable"]]
            if arbitrable:
                report["claims"][os.path.basename(f)] = arbitrable
            soft = split_soft(cuda)
            if soft:
                report["soft_claims"][os.path.basename(f)] = soft
    if "arbitrate" in steps:
        allc = []
        for f in findings:
            allc += extract_claims(finding_cuda(f))
        rows = [r for r in step_arbitrate(allc, facts, kerr)
                if r["verdict"] != "NOT_ARBITRABLE"]
        # soft claims are arbitrated as SETS: a slash run publishes several
        # candidate values, so the verdict is per value and the set is reported
        # whole.  This is what catches **22/23/24**, which the hard form misses.
        softrows = []
        for f in findings:
            for sc in split_soft(finding_cuda(f)):
                kind, field = ARBITER_TABLE[sc["key"]]
                kern = None
                if facts is not None and kind == "vm_size" and field in facts:
                    kern = facts[field]
                for v in sc["values"]:
                    softrows.append({
                        "key": sc["key"], "value": v,
                        "kernel_value": kern,
                        "verdict": ("NO_KERNEL" if kern is None else
                                    ("AGREE" if v == kern else "DISAGREE")),
                        "source": os.path.basename(f),
                    })
        report["arbitration"] = {"kernel_facts": facts, "rows": rows,
                                 "soft_rows": softrows}
    if "conflicts" in steps:
        report["conflicts"] = run_composed(
            repo, "causal_map", ["--contradictions"])

    if args.accept:
        state["seen"] = {os.path.basename(f): sha(f) for f in findings}
        state["version"] = VERSION
        state["last"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        p = save_state(repo, state)
        report["accepted"] = {"state_file": p,
                              "findings_recorded": len(findings)}

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("%s %s -- documentation round" % (TOOL, VERSION))
    print("  " + "-" * 66)
    print("  repo           %s" % repo)
    print("  findings       %d" % len(findings))
    print("  kernel log     %s" % report["kernel_log"])
    if facts:
        ks = {k: v for k, v in facts.items() if k != "ipblocks"}
        print("  kernel facts   %s" % ks)

    if "new" in steps:
        new = report["new"]
        print("")
        print("  NEW SIN VER    %d" % len(new))
        for n in new[:14]:
            print("    %-10s %s" % (n["state"], n["name"]))
        if len(new) > 14:
            print("    ... and %d more" % (len(new) - 14))
        if not new:
            print("    (every finding has been seen and is unchanged)")

    if "arbitrate" in steps:
        rows = report["arbitration"]["rows"]
        softrows = report["arbitration"].get("soft_rows") or []
        sdis = [r for r in softrows if r["verdict"] == "DISAGREE"]
        if softrows:
            print("")
            print("  ARBITRACION DE CLAIMS DEBILES  (forma **N/M/K**, menor precision)")
            print("    %d valores, %d AGREE, %d DISAGREE, %d NO_KERNEL"
                  % (len(softrows),
                     len([r for r in softrows if r["verdict"] == "AGREE"]),
                     len(sdis),
                     len([r for r in softrows if r["verdict"] == "NO_KERNEL"])))
            seenpair = set()
            for r in sdis:
                k = (r["key"], r["source"])
                if k in seenpair:
                    continue
                seenpair.add(k)
                print("      %-16s %-4s vs kernel %-5s   en %s"
                      % (r["key"], r["value"], r["kernel_value"], r["source"]))
        dis = [r for r in rows if r["verdict"] == "DISAGREE"]
        agr = [r for r in rows if r["verdict"] == "AGREE"]
        nok = [r for r in rows if r["verdict"] == "NO_KERNEL"]
        print("")
        print("  ARBITRACION CONTRA EL KERNEL")
        print("    %d claims arbitrables en los findings" % len(rows))
        print("    AGREE     %d" % len(agr))
        print("    DISAGREE  %d" % len(dis))
        print("    NO_KERNEL %d" % len(nok))
        if dis:
            print("")
            print("    Las que NO coinciden con el autoinforme del kernel:")
            # the per-finding claim map only exists if the claims step ran, so
            # this must not assume it.  It did, and --only arbitrate crashed.
            bysrc = report.get("claims") or {}
            for r in dis:
                where = sorted(n for n, cs in bysrc.items()
                               if any(x["key"] == r["key"] and x["value"] == r["value"]
                                      for x in cs))
                print("      %-16s afirma %-4s el kernel dice %-5s"
                      % (r["key"], r["value"], r.get("kernel_value")))
                if where:
                    print("          en: %s" % ", ".join(where[:3]))
                else:
                    print("          en: (finding no identificado: paso claims no corrió)")
        if nok:
            print("")
            print("    Sin campo en el log del kernel (NO se inventa veredicto):")
            for r in nok[:6]:
                print("      %-16s %s" % (r["key"], r.get("detail")))

    if "conflicts" in steps:
        print("")
        print("  CONFLICTOS  (compuesto: causal_map.py --contradictions)")
        for l in report["conflicts"]["tail"]:
            if l.strip():
                print("    %s" % l.rstrip()[:70])

    if "scan" in steps:
        print("")
        print("  HERRAMIENTAS COMPUESTAS")
        for k, v in report["scan"].items():
            print("    %-10s rc=%s" % (k, v["rc"]))
            for l in v["tail"]:
                if l.strip():
                    print("        %s" % l.strip()[:64])

    if args.accept:
        print("")
        print("  ACCEPTED  %d findings recorded in %s"
              % (report["accepted"]["findings_recorded"], STATE_REL))

    print("")
    print("  ESTA HERRAMIENTA PROPONE. No escribe afirmaciones ni edita hallazgos.")
    print("  AGREE es «consistente con el autoinforme del kernel», no «verdadero».")
    print("  DISAGREE es un hecho medido sobre lo que el kernel dice; lo que significa")
    print("  lo decide quien lee.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
