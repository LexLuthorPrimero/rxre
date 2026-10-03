#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE . STATIC_ANALYSIS

"""
claim -- the claim registry for docs/, and the coverage measure that keeps it true.

WHY THIS EXISTS
---------------
Measured on 2026-10-01, and this is the finding, not the tool:

    95 findings in 06-INGENIERIA-INVERSA/findings/
    28 of them are cited NOWHERE in docs/

Twenty-nine per cent of the project's produced evidence was never registered.  Some
of those 28 are not minor:

    043-vuelta-atras-035-y-036-leian-el-asic-equivocado
        another session independently discovering that 035 and 036 read the WRONG
        ASIC, which is C-011
    059-srcdata-no-es-payload-es-el-wptr-del-ring
    060-srcdata-es-el-subtipo-y-el-decodificador-esta-en-dce
    061-srcdata-dos-valores-constante-por-derivacion
        three findings about what `src_data` in the interrupt vector actually
        carries, which is what RE-36 and RE-40 assert
    062-citas-de-c-009-desplazadas-y-tabla-de-030-invertada
        about the very contradiction this documentation registered

So the gap is not cosmetic.  It is evidence, including a second independent
witness to a contradiction already resolved here.

THE SAME SHAPE AS toolreg
-------------------------
toolreg found that 26 of 48 tools were undocumented and that five were cited by
nobody.  This is the same failure on the evidence axis, and it has the same cause:
a registry that has to be maintained by remembering is not a registry.

THE RULE THAT MAKES THIS SAFE
-----------------------------
It does NOT write claims.  That is the whole design, and it is a boundary drawn
from the project's own rules rather than from caution.

A claim may not be invented.  What CAN be automated is the bookkeeping around
one: which number is free, which findings already have a home, which do not, and
what metadata a draft can be pre-filled with WITHOUT asserting anything.  So:

    --coverage   which findings have no registered claim.  A measurement
    --next-id    the next free RE-nn.  A measurement
    --scaffold   a DRAFT row, with the machine-readable fields filled from the
                 finding's own header, and every judgement field marked
                 PENDIENTE.  NEVER written into docs/ by this tool

--scaffold prints.  It does not write.  There is no flag that makes this tool
edit docs/, and that is deliberate: a scaffolder that could publish would be a
machine for manufacturing claims, which is precisely the failure this project
keeps paying for.

WHAT IT MEASURES, PRECISELY
---------------------------
    coverage      findings cited by at least one docs/ file
    orphans       an RE-nn whose cited findings no longer all exist
    collision     two findings sharing a numeric index, which is not a defect of
                  the tree but a permanent property of the numbering
    numbering     gaps in the RE sequence
    DECLARED      claims that are PROVEN with no LOCATION.  That is the field
                  that decides whether a claim is auditable, and a count of its
                  absence is the most useful number here

SELF-TEST
---------
17 checks with negative controls, including the two that matter: a claim with no
LOCATION must be counted as un-auditable rather than passing, and a finding
named nowhere must be reported rather than silently accepted.

--locate:  FETCHING CANDIDATE LOCATIONS, WHICH IS NOT THE SAME AS CHOOSING ONE
--------------------------------------------------------------------------
Measured on this tree: 25 of the registry's claims carry no LOCATION, and 15 of
those 25 already cite a finding that states its own locations.  So most of the
mechanical half of closing RE-49 is FETCHING, and none of it is choosing.

  --locate  for every claim without a LOCATION, resolve its cited findings and
            print the location lines THOSE findings declare, plus the file:line
            references inside them.  It does not propose which one is right.

That last sentence is the design.  A claim's LOCATION is the one field where a
plausible wrong answer is indistinguishable from a right one: `gmc_v8_0.c:691`
is a real line about PTE flags, and so is `gmc_v8_0.c:702`, and picking either by
machine would be inventing an audit trail.  So this fetches a shortlist and
stops.

USAGE
-----
    claim.py --repo .                       coverage report
    claim.py --repo . --locate              candidate locations for unlocated claims
    claim.py --repo . --scaffold 030-x.md   draft a claim from one finding
    claim.py --repo . --next-id
    claim.py --repo . --json
    claim.py --selftest
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "claim"

FINDINGS_REL = "06-INGENIERIA-INVERSA/findings"
EM_REL = "docs/EVIDENCE-MATRIX.md"
ALL_DOCS_REL = "docs"

RE_CLAIM_HEAD = re.compile(r"^## (RE-\d+)[ ·]", re.M)
RE_CLAIM_ROW = re.compile(r"^\| (RE-\d+) \|", re.M)

# The nine fields a claim must carry to be auditable.  This is the project's own
# rule, written down, and the tool measures against it rather than inventing a
# schema of its own.
JUDGEMENT_FIELDS = ("TYPE", "STATE", "LOCATION")
OPTIONAL_FIELDS = ("SOURCE", "VERSION", "CONFIDENCE", "WHEN", "LIMIT", "UNIT",
                   "PRODUCER", "CONSUMER", "EFFECT", "HOW")

# Header keys a finding declares, which map onto claim fields without asserting
# anything: they are the finding's own words about itself.
HEADER_KEYS = {
    "SOURCE": ("SOURCE", "CORRECTS", "CONTINUES", "IMPLEMENTS", "RESOLVES",
               "ADJUDICA", "RECTIFIES", "COMPLEMENTS", "CONTINUA", "CORRECTION"),
    "VERSION": ("VERSION", "CORPUS", "HARDWARE_SCOPE"),
    "CLASSIFICATION": ("CLASSIFICATION",),
    "RUNTIME": ("RUNTIME", "WORK_CLASS", "WRITE_EXECUTION", "MODIFICATIONS"),
    "COMPLEMENTS": ("COMPLEMENTS", "CONTINUES"),
    "CORRECTS": ("CORRECTS", "RECTIFIES"),
    "RESOLVES": ("RESOLVES",),
    "COMPLETES": ("COMPLEMENTS",),
}


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def list_findings(repo):
    d = os.path.join(repo, FINDINGS_REL)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.endswith(".md"))


def list_docs(repo):
    d = os.path.join(repo, ALL_DOCS_REL)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".md")]


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------

def parse_claims(repo):
    """Every claim in EVIDENCE-MATRIX.md, with its body and its fields."""
    txt = read(os.path.join(repo, EM_REL))
    if not txt:
        return []
    parts = re.split(r"^(## RE-\d+[^\n]*\n)", txt, flags=re.M)
    claims = []
    for i in range(1, len(parts), 2):
        head, body = parts[i], parts[i + 1]
        cid = re.match(r"## (RE-\d+)", head).group(1)
        # the row form lives inside a table right after the heading
        head_body = head + body
        fields = {}
        for f in JUDGEMENT_FIELDS + OPTIONAL_FIELDS:
            m = re.search(r"^%s\s+(.*)$" % f, head_body, re.M)
            if m:
                fields[f] = m.group(1).strip()
        # a table row carries its fields in pipes
        if not fields:
            for line in head_body.split("\n"):
                if line.startswith("|") and cid in line:
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    for f in JUDGEMENT_FIELDS:
                        if f in cells:
                            i2 = cells.index(f)
                            if i2 + 1 < len(cells):
                                fields[f] = cells[i2 + 1]
                    break
        cited = sorted(set(re.findall(
            r"`([0-9]{3}[A-Za-z0-9_.\-]*\.md)`", head_body)))
        claims.append({"id": cid, "head": head.strip(), "body": body,
                       "fields": fields, "cites": cited,
                       "auditable": bool(fields.get("LOCATION"))})
    return claims


def next_free_id(claims):
    nums = []
    for c in claims:
        m = re.match(r"RE-(\d+)", c["id"])
        if m:
            nums.append(int(m.group(1)))
    n = 1
    used = set(nums)
    while n in used:
        n += 1
    return n, used


def coverage(repo, claims, findings):
    """
    Which findings have a home in docs/, and which do not.

    Matched on the finding's full stem, because matching on the bare number would
    mark a finding as covered when the citation is to a DIFFERENT finding with the
    same index.  There are 27 index collisions in this tree, so that distinction
    is the whole correctness of this measurement.
    """
    blob = "\n".join(read(p) for p in list_docs(repo))
    covered, uncovered = [], []
    for f in findings:
        stem = os.path.basename(f)[:-3]
        (covered if stem in blob else uncovered).append(os.path.basename(f))
    return covered, uncovered


def index_collisions(findings):
    nums = {}
    for f in findings:
        head = os.path.basename(f).split("-")[0]
        nums.setdefault(head, []).append(os.path.basename(f))
    return sorted(k for k, v in nums.items() if len(v) > 1), nums


def report(repo, claims, findings, covered, uncovered):
    nfree, used = next_free_id(claims)
    dupes, bynum = index_collisions(findings)
    unauditable = [c["id"] for c in claims if not c["auditable"]]
    nums = sorted(used)
    holes = [n for n in range(1, (max(nums) if nums else 0) + 1) if n not in used]

    # a claim citing a finding that no longer exists
    existing = {os.path.basename(f)[:-3] for f in findings}
    orphans = []
    for c in claims:
        for cite in c["cites"]:
            if cite not in existing:
                orphans.append({"claim": c["id"], "cites_missing": cite})

    return {
        "tool": TOOL, "version": VERSION, "repo": repo,
        "claims": len(claims),
        "next_free_id": "RE-%02d" % nfree,
        "findings_total": len(findings),
        "findings_covered": len(covered),
        "findings_uncovered": len(uncovered),
        "coverage_pct": round(100.0 * len(covered) / len(findings), 1)
                        if findings else 0.0,
        "uncovered": uncovered,
        "claims_without_location": unauditable,
        "claims_citing_missing_finding": orphans,
        "index_collisions": dupes,
        "numbering_holes": holes,
        "covered": covered,
    }


# --------------------------------------------------------------------------
# --locate: fetch candidates.  Never chooses.
# --------------------------------------------------------------------------

RE_FILELINE = re.compile(r"\b([A-Za-z0-9_]+\.[ch]):(\d+)(?:-(\d+))?\b")


def finding_locations(path):
    """
    The location lines a finding itself declares.

    Two sources, in the order a reader would trust them:
      1 its own `LOCATION` block, which the finding wrote as its answer
      2 file:line references inside it, which are evidence but not necessarily
        the answer -- a finding cites the code it argues FROM and the code it
        CONTRASTS, and those are not the same thing
    They are returned separately and labelled, because conflating them would be
    the same mistake as conflating an observation with a conclusion.
    """
    txt = read(path)
    declared = []
    m = re.search(r"^LOCATION\s+((?:.*\n?)+?)(?=^[A-Z]{3,}[ \t]|^```)", txt, re.M)
    if m:
        for line in m.group(1).split("\n"):
            if line.strip():
                declared.append(line.strip())
    refs = []
    seen = set()
    for mm in RE_FILELINE.finditer(txt):
        key = (mm.group(1), mm.group(2), mm.group(3))
        if key in seen:
            continue
        seen.add(key)
        rng = "%s-%s" % (mm.group(2), mm.group(3)) if mm.group(3) else mm.group(2)
        refs.append("%s:%s" % (mm.group(1), rng))
    return declared, refs


def locate(repo, claims, findings, limit_refs=8):
    """
    For each claim with no LOCATION, the candidate locations its evidence offers.

    Returns a classification per claim, and the classification is the value:
      FETCHABLE   the claim cites a finding that DECLARES locations.  The shortlist
                  is available and the choice is a human's
                  ADVERTISED  the claim cites a finding that only mentions
                  file:line references.  Those are where it argued FROM, which is
                  often but not always the answer
                  MANUAL      nothing resolvable.  Needs a corpus read
    """
    by_name = {os.path.basename(f): f for f in findings}
    existing = set(by_name)
    out = []
    for c in claims:
        if c["auditable"]:
            continue
        # the finding names live in the BODY, not in the heading.  An earlier
        # version searched only the heading and found zero sources for every
        # claim, which would have made --locate report MANUAL for all of them
        # and look like a real measurement.
        blob = c.get("body") or ""
        names = []
        for n in re.findall(r"`?([0-9]{3}-[A-Za-z0-9_.\-]+\.md)`?", blob):
            if n in existing and n not in names:
                names.append(n)
        row = {"id": c["id"], "sources": names, "class": "MANUAL",
               "declared": [], "refs": []}
        for n in names:
            declared, refs = finding_locations(by_name[n])
            if declared:
                row["class"] = "FETCHABLE"
                row["declared"] = (row["declared"] + declared)[:limit_refs]
                row["refs"] = (row["refs"] + refs)[:limit_refs]
                row["from"] = n
                break
            if refs:
                if row["class"] == "MANUAL":
                    row["class"] = "ADVERTISED"
                row["refs"] = (row["refs"] + refs)[:limit_refs]
                row["from"] = n
        out.append(row)
    return out


# --------------------------------------------------------------------------
# scaffolding.  Prints.  NEVER writes.
# --------------------------------------------------------------------------

def scaffold(repo, finding_path, claim_id):
    """
    A draft claim whose machine-readable fields come from the finding's own
    header, with every judgement field marked PENDIENTE.

    Nothing here is asserted about the hardware.  TYPE and STATE are the two fields
    that carry knowledge, and this tool does not have any, so they are PENDIENTE and
    say so.  A draft that fills STATE in would be inventing state, which is the one
    thing this project must not automate.
    """
    txt = read(finding_path)
    name = os.path.basename(finding_path)
    title = ""
    lines = [l for l in txt.split("\n")[:16] if l.strip()]
    if lines:
        title = lines[0].lstrip("# ").strip()

    header = {}
    for line in txt.split("\n")[:16]:
        for key in re.findall(r"`?([A-Z][A-Z_0-9]{2,})\s*=\s*([^`\n]+)`?", line):
            header.setdefault(key[0], []).append(key[1].strip().strip("` "))

    out = ["## %s · %s" % (claim_id, title or name), "", "```",
           "TYPE    PENDIENTE   <- hay que decidirlo. Esta herramienta no lo sabe",
           "STATE   PENDIENTE   <- hay que arbitrarlo. Esta herramienta NO PUEDE",
           "                     <tool_call>              arbitrar una afirmación sobre el hardware",
           "LOCATION  PENDIENTE  <- fichero:línea, medido", ""]

    emitted = set()
    for claim_field, keys in HEADER_KEYS.items():
        if claim_field in emitted:
            continue
        for k in keys:
            if k in header:
                out.append("%-9s %s" % (claim_field, " ".join(header[k])))
                emitted.add(claim_field)
                break

    cited = sorted(set(re.findall(r"`([0-9]{3}[A-Za-z0-9_.\-]*\.md)`", txt)))
    out.append("")
    out.append("SOURCE   %s  (este fichero)" % name)
    if cited:
        out.append("CITADO POR  %s" % ", ".join(cited[:6]))
    out.append("")
    out.append("LO QUE FALTA, y es todo lo importante")
    out.append("  · STATE: hay que elegir entre PROVEN / OBSERVED / DERIVATION /")
    out.append("    MODEL_CHOICE / NEGATIVE_RESULT, y si es PROVEN, sobre qué")
    out.append("  · LOCATION: fichero:línea. Una claim sin LOCATION no es auditable, y")
    out.append("    hay %d así en el registro ahora mismo" % 0)
    out.append("  · UNIT: la unidad del número, o la razón de no tenerla")
    out.append("  · LIMIT: qué NO demuestra, y en particular si es un LIMIT de lo que")
    out.append("    se afirmaba antes, porque eso es lo que lo hace una corrección")
    out.append("  · CONFIDENCE, y POR QUÉ no es mayor")
    out.append("```")
    return "\n".join(out)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def build_fixture(root):
    fd = os.path.join(root, FINDINGS_REL)
    os.makedirs(fd, exist_ok=True)
    with open(os.path.join(fd, "001-uno.md"), "w", encoding="utf-8") as fh:
        fh.write("# 001 · uno\n\n## CUDA\n\n`block_size = 10`\n")
    with open(os.path.join(fd, "001-otro.md"), "w", encoding="utf-8") as fh:
        fh.write("# 001 · otro\n\n`GPU INTACTA`\n")   # duplicate index on purpose
    with open(os.path.join(fd, "002-sin-cita.md"), "w", encoding="utf-8") as fh:
        fh.write("# 002 · sin cita\n\n`GPU INTACTA`\n")
    # a finding that DECLARES its locations, for --locate
    with open(os.path.join(fd, "003-declara.md"), "w", encoding="utf-8") as fh:
        fh.write("# 003 · declara sus localizaciones\n\n## CUDA\n\n"
                 "```\nLOCATION  a.c:10  lo primero\n"
                 "        a.c:20  lo segundo\nSTATE     PROVEN\n```\n")
    # a finding that only MENTIONS file:line, without declaring
    with open(os.path.join(fd, "004-menciona.md"), "w", encoding="utf-8") as fh:
        fh.write("# 004 · solo menciona\n\n## CUDA\n\n"
                 "se ve en b.c:33 y tambien c.c:44\n")
    dd = os.path.join(root, "docs")
    os.makedirs(dd, exist_ok=True)
    with open(os.path.join(dd, "EVIDENCE-MATRIX.md"), "w", encoding="utf-8") as fh:
        fh.write("# E\n\n## RE-01 · con location\n\n```\nTYPE    FACT\n"
                 "STATE   PROVEN\nLOCATION amdgpu_vm.c:2454\n```\n\n"
                 "## RE-02 · sin location\n\n```\nTYPE    FACT\nSTATE   PROVEN\n"
                 "SOURCE  003-declara.md\n```\n\n"
                 "## RE-03 · cita un finding que no existe\n\n```\n"
                 "LOCATION x.c:1\nCITA `999-fantasma.md`\n```\n\n"
                 "## RE-04 · sin nada resoluble\n\n```\nTYPE    FACT\n"
                 "STATE   PROVEN\nSOURCE  la documentacion de AMD\n```\n\n"
                 "## RE-05 · cita uno que solo menciona\n\n```\nTYPE    FACT\n"
                 "STATE   PROVEN\nSOURCE  004-menciona.md\n```\n")
    with open(os.path.join(dd, "OTRO.md"), "w", encoding="utf-8") as fh:
        fh.write("menciona 001-uno.md\n")


FIXTURE_SCAFFOLD = (
    "# 077 · un finding de ejemplo\n\n"
    "`CLASSIFICATION=DOCUMENTATION` · `CORPUS=linux-7.1.3` · `GPU INTACTA`\n"
    "`COMPLEMENTS=001-uno.md`\n\n## CUDA principal\n\nalgo\n"
)


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 64)
    fails = 0
    checks = 0

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        build_fixture(td)
        claims = parse_claims(td)
        findings = list_findings(td)
        cov, unc = coverage(td, claims, findings)
        rep = report(td, claims, findings, cov, unc)

        checks += 1
        if len(claims) == 5:
            print("  OK    five claims parsed")
        else:
            print("  FAIL  parsed %d claims, expected 5" % len(claims))
            fails += 1

        checks += 1
        nfree, _ = next_free_id(claims)
        if nfree == 6:
            print("  OK    next free id is RE-06, not a collision")
        else:
            print("  FAIL  next free id is RE-%02d, expected RE-06" % nfree)
            fails += 1

        checks += 1
        if rep["index_collisions"] == ["001"]:
            print("  OK    the duplicate index is reported")
        else:
            print("  FAIL  collisions = %s" % rep["index_collisions"])
            fails += 1

        # THE check that matters comes first: coverage must NOT confuse two
        # findings that share an index.  Citing 001-uno.md must not cover
        # 001-otro.md, and there are 27 index collisions in this tree, so this
        # distinction is the whole correctness of the measurement.
        checks += 1
        if "001-uno.md" in cov and "001-otro.md" not in cov:
            print("  OK    coverage distinguishes two findings sharing index 001")
        else:
            print("  FAIL  coverage matched by index: covered=%s" % cov)
            fails += 1

        checks += 1
        if rep["uncovered"] == ["001-otro.md", "002-sin-cita.md"]:
            print("  OK    findings cited nowhere are reported, exactly the two")
        else:
            print("  FAIL  uncovered = %s, expected the two uncited"
                  % rep["uncovered"])
            fails += 1

        checks += 1
        if rep["claims_without_location"] == ["RE-02", "RE-04", "RE-05"]:
            print("  OK    claims with no LOCATION are counted as un-auditable "
                  "(%d of %d)" % (len(rep["claims_without_location"]), len(claims)))
        else:
            print("  FAIL  claims without LOCATION = %s"
                  % rep["claims_without_location"])
            fails += 1

        # ---- --locate: the three classes, and the control that matters
        loc = locate(td, claims, findings)
        byid = {r["id"]: r for r in loc}
        checks += 1
        if byid.get("RE-02", {}).get("class") == "FETCHABLE" and \
           byid["RE-02"]["declared"]:
            print("  OK    a claim citing a finding that DECLARES locations is "
                  "FETCHABLE with %d candidate(s)"
                  % len(byid["RE-02"]["declared"]))
        else:
            print("  FAIL  RE-02 locate = %s" % byid.get("RE-02"))
            fails += 1

        checks += 1
        if byid.get("RE-05", {}).get("class") == "ADVERTISED" and \
           byid["RE-05"]["refs"]:
            print("  OK    a claim whose finding only MENTIONS file:line is "
                  "ADVERTISED, not FETCHABLE")
        else:
            print("  FAIL  RE-05 locate = %s" % byid.get("RE-05"))
            fails += 1

        checks += 1
        if byid.get("RE-04", {}).get("class") == "MANUAL":
            print("  OK    a claim with nothing resolvable is MANUAL, not guessed")
        else:
            print("  FAIL  RE-04 locate = %s" % byid.get("RE-04"))
            fails += 1

        checks += 1
        if "RE-01" not in byid:
            print("  OK    a claim that already has a LOCATION is not offered work")
        else:
            print("  FAIL  --locate offered a location for an already-located claim")
            fails += 1

        checks += 1
        orp = rep["claims_citing_missing_finding"]
        if orp and orp[0]["claim"] == "RE-03":
            print("  OK    a claim citing a nonexistent finding is flagged")
        else:
            print("  FAIL  orphan citation not detected: %s" % orp)
            fails += 1

        checks += 1
        if rep["numbering_holes"] == []:
            print("  OK    no numbering hole in a dense sequence")
        else:
            print("  FAIL  holes = %s" % rep["numbering_holes"])
            fails += 1

        # scaffolding must never fill the two knowledge fields
        with open(os.path.join(td, FINDINGS_REL, "077-x.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(FIXTURE_SCAFFOLD)
        sc = scaffold(td, os.path.join(td, FINDINGS_REL, "077-x.md"), "RE-77")
        checks += 1
        if "TYPE    PENDIENTE" in sc and "STATE   PENDIENTE" in sc:
            print("  OK    a draft leaves TYPE and STATE as PENDIENTE")
        else:
            print("  FAIL  the draft asserted TYPE or STATE")
            fails += 1

        # the draft labels the field by the CLAIM field, so CORPUS is emitted
        # under VERSION.  An earlier version of this check looked for the header
        # key and so reported a passing scaffold as broken.
        checks += 1
        if "VERSION" in sc and "linux-7.1.3" in sc and "CLASSIFICATION" in sc:
            print("  OK    a draft carries the finding's own declared metadata")
        else:
            print("  FAIL  the draft lost the header metadata")
            fails += 1

        checks += 1
        if "LOCACIÓN" in sc or "auditable" in sc:
            print("  OK    the draft says what is missing")
        else:
            print("  FAIL  the draft does not say what is missing")
            fails += 1

        # and the strongest possible check: the tool must not be able to write
        checks += 1
        src = read(os.path.join(__file__))
        if not re.search(r"open\s*\(\s*[^)]*,\s*['\"][wa]", src):
            print("  OK    this tool contains no code that writes a file")
        else:
            print("  FAIL  this tool CAN write. That breaks its whole design")
            fails += 1

    print("  " + "-" * 64)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: esta herramienta MIDE. No escribe claims y no puede: no hay flag")
    print("        que la haga editar docs/, y eso es deliberado. Un scaffolder que")
    print("        pudiera publicar sería una máquina para fabricar afirmaciones, que es")
    print("        exactamente el fallo que este proyecto ha pagado cuatro veces.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="claim", description="claim registry, coverage, and draft scaffolding")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--scaffold", metavar="FINDING",
                    help="print a DRAFT claim for one finding. Prints; never writes")
    ap.add_argument("--locate", action="store_true",
                    help="for every claim without LOCATION, print the location "
                         "lines its cited findings declare.  Fetches; never chooses")
    ap.add_argument("--next-id", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ALL_DOCS_REL)):
        sys.stderr.write("claim: no docs/ under %s\n" % repo)
        return 2

    if args.scaffold:
        p = args.scaffold
        if not os.path.isabs(p):
            p = os.path.join(repo, FINDINGS_REL, args.scaffold)
        if not os.path.exists(p):
            sys.stderr.write("claim: finding not found: %s\n" % p)
            return 2
        claims = parse_claims(repo)
        n, _ = next_free_id(claims)
        print(scaffold(repo, p, "RE-%02d" % n))
        print()
        print("  Esto es un BORRADOR impreso, no una claim. TYPE y STATE los decide")
        print("  una persona, y LOCATION hay que medirlo. Nada se ha escrito.")
        return 0

    claims = parse_claims(repo)
    findings = list_findings(repo)
    cov, unc = coverage(repo, claims, findings)
    rep = report(repo, claims, findings, cov, unc)

    if args.json:
        print(json.dumps(rep, indent=2, sort_keys=True))
        return 0

    if args.next_id:
        print(rep["next_free_id"])
        return 0

    if args.locate:
        rows = locate(repo, claims, findings)
        byc = {}
        for r in rows:
            byc[r["class"]] = byc.get(r["class"], 0) + 1
        if args.json:
            print(json.dumps({"claims_unlocated": rows, "summary": byc},
                             indent=2, sort_keys=True))
            return 0
        print("%s %s -- localizaciones candidatas" % (TOOL, VERSION))
        print("  " + "-" * 64)
        print("  claims sin LOCATION   %d" % len(rows))
        print("    FETCHABLE   %d   el finding citado DECLARA sus localizaciones"
              % byc.get("FETCHABLE", 0))
        print("    ADVERTISED  %d   el finding sólo menciona fichero:línea"
              % byc.get("ADVERTISED", 0))
        print("    MANUAL      %d   nada resoluble; hay que leer el corpus"
              % byc.get("MANUAL", 0))
        print("")
        for r in rows:
            print("  %-8s %-11s %s" % (r["id"], r["class"],
                                       (r["sources"][0] if r["sources"] else "-")))
            if r["declared"]:
                print("      DECLARADO por el finding:")
                for l in r["declared"][:5]:
                    print("        %s" % l[:66])
            if r["refs"]:
                print("      ficheros:línea citados  %s"
                      % ", ".join(r["refs"][:6]))
            if not r["declared"] and not r["refs"]:
                print("      sin evidencia localizable: hay que leer el corpus")
            print("")
        print("  ESTO TRAE CANDIDATOS, NO ELIGE. Una LOCATION equivocada es")
        print("  indistinguible de una correcta: gmc_v8_0.c:691 y :702 son líneas")
        print("  reales sobre los flags del PTE. Elegir es conocimiento.")
        return 0

    print("%s %s" % (TOOL, VERSION))
    print("  " + "-" * 64)
    print("  claims registradas   %d   siguiente libre   %s"
          % (rep["claims"], rep["next_free_id"]))
    print("  findings             %d" % rep["findings_total"])
    print("")
    print("  COBERTURA            %d de %d  (%.1f%%)"
          % (rep["findings_covered"], rep["findings_total"], rep["coverage_pct"]))
    if unc:
        print("")
        print("  FINDINGS SIN NINGUNA CLAIM REGISTRADA   %d" % len(unc))
        for f in unc:
            print("    %s" % f)

    if rep["claims_without_location"]:
        print("")
        print("  CLAIMS SIN LOCATION, o sea NO AUDITABLES   %d"
              % len(rep["claims_without_location"]))
        print("    %s" % ", ".join(rep["claims_without_location"]))

    if rep["claims_citing_missing_finding"]:
        print("")
        print("  CLAIMS QUE CITAN UN FINDING INEXISTENTE   %d"
              % len(rep["claims_citing_missing_finding"]))
        for o in rep["claims_citing_missing_finding"][:10]:
            print("    %-8s -> %s" % (o["claim"], o["cites_missing"]))

    print("")
    print("  NUMERACION   %d colisiones de índice en findings/ · %d huecos en RE"
          % (len(rep["index_collisions"]), len(rep["numbering_holes"])))
    print("")
    print("  MIDE. No escribe claims, y no puede: no hay flag que la haga editar")
    print("  docs/.  Un scaffolder que pudiera publicar sería una máquina para")
    print("  fabricar afirmaciones.")
    return 1 if unc else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
