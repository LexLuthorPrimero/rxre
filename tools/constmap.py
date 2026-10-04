#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE . STATIC_ANALYSIS

"""
constmap -- check every constant this driver defines against the upstream line
it says it came from.

THE GAP THIS CLOSES, AND IT IS THE ONE F3d NAMED
-------------------------------------------------
`F3d` in docs/OPEN-FRONTIERS.md is a working driver whose compiled-in constant
`rx550_pm4.c:277` disagrees with what the code it was written against does.  That
was found by reading, late.  The structural reason it could be found late is that
nothing checked the constants themselves.

The header already carries the evidence needed, and nobody was reading it.  Every
constant cites the upstream line it came from, in a trailing comment:

    #define RX550_PKT3_NOP           0x10    /* sid.h:343 */
    #define RX550_PKT3_WAIT_REG_MEM  0x3C    /* sid.h:397 */

So each one is a falsifiable claim with a witness:

    RX550_PKT3_NOP = 0x10   CLAIMS to be   sid.h:343
    sid.h:343               WHICH SAYS     #define PACKET3_NOP  0x10

    AGREE       the value at the cited line is the value we wrote
    DISAGREE    the cited line defines a DIFFERENT value.  This is the finding
                that would have caught F3d before the code was written
    AGREE_COMMENT  the witness is a COMMENT that enumerates the value.  vid.h keeps
                 its encodings as prose: `WAIT_REG_MEM_ENGINE(x)` is the #define at
                 186, and 187-188 are `/* 0 - me` and ` * 1 - pfp`.  A constant
                 citing 187 with value 0 has a witness that really does carry 0.
    WITNESS_USAGE the witness is code that USES the encoding without carrying the
                 value.  `RX550_WAIT_REG_MEM_OP_WWW = 1u` cites `gfx_v8_0.c:6054`,
                 which is `amdgpu_ring_write(ring, ref_and_mask);` — the body of the
                 WAIT_REG_MEM packet emitted at 6047, three lines above the comment
                 that says `WAIT_REG_MEM_OPERATION(1) /* write, wait, write */`.
                 Topically correct, but it cannot arbitrate a value.  Reported
                 rather than hidden, and NOT called a defect: the line is in the
                 right function.
    UNCITED     a constant with no witness: nothing to check it against
    UNRESOLVED  it cites a line, and no file with that name has it here
    AMBIGUOUS   it cites `sid.h`, and there are TEN sid.h files in this tree,
                including drivers/gpu/drm/radeon/sid.h -- a different driver with
                a different set of macros at the same line number.  The citation
                does not say WHICH sid.h, so the value check cannot be trusted
                until a human picks.  Reported, never resolved by guess.

WHY THE VALUE IS THE ARBITER AND NOT THE NAME
---------------------------------------------
`RX550_PKT3_WAIT_REG_MEM` and `PACKET3_WAIT_REG_MEM` are the same concept, and
matching them means knowing that PKT3 abbreviates PACKET3.  That abbreviation is
knowledge, and writing it into a tool would put a guess where a measurement
belongs -- it could match two different constants to one and never say so.

So the VALUE arbitrates, because it is exact, and the upstream NAME is printed
beside it for a human to confirm.  The tool reports both and asserts neither.

COMPOSITION, NOT REIMPLEMENTATION
----------------------------------
Line resolution is `citations.py`'s job and its resolver is imported, not copied.
That resolver already knows the thing that matters here and that a naive `grep`
misses twice over:

    $ citations.py --show sid.h:343
      10 copies with that name
      7.1.3  drivers/gpu/drm/amd   #define PACKET3_NOP   0x10
      7.1.3  drivers/gpu/drm/       #define SOFT_RESET_BIF (1 << 1)
                                 drivers/gpu/drm/radeon/sid.h

`sid.h` in the radeon driver is a different file with a different macro at line
343.  Anyone verifying an amdgpu packet header by grepping `sid.h` may land there
and see something plausible.  That is the same trap `citations.py` was built for,
met from the other side.

WHAT IT DOES NOT DO, DECLARED
-----------------------------
  1. It does not decide which copy of an ambiguous header is meant.
  2. It does not evaluate macros.  A value like `((x) << 8)` is not computed; it
     is reported as NOT_COMPARABLE, because evaluating it needs the preprocessor
     and the kernel's include graph, and a regex that guessed would be wrong
     silently.
  3. It does not judge whether a constant with no witness is correct.  UNCITED
     means uncheckable here, not wrong.
  4. It does not edit anything.  A constant that disagrees is a claim that a
     person resolves.
  5. It does not treat AGREE as proof that the SEMANTICS are right.  It proves the
     number matches a line in a header.  What the number means is F3d's other
     question, and it stays open.

SAFETY
------
Read-only.  Reads a header, resolves lines in the corpus, prints.  No write path,
asserted in the source by the self-test.

USAGE
-----
    constmap.py --repo .              every RX550_* constant against its witness
    constmap.py --repo . --disagree   only the ones that disagree
    constmap.py --repo . --json
    constmap.py --selftest
"""

import argparse
import importlib.util
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "constmap"

HERE = os.path.dirname(os.path.abspath(__file__))
# The repo root comes from __file__, NEVER from the current directory.
#
# This was a real portability defect, and it was found by toolreg.py rather than by
# this tool's own self-test: toolreg runs every self-test with cwd=tools/, and the
# self-test used os.getcwd(), so it looked for tools/07-DRIVER/kernel/rx550_pm4.h,
# did not find it, and reported 2 failures on a tool whose self-test passes 17/17
# from the repo root.
#
# A self-test that only passes when invoked the way its author happens to invoke it
# is not a self-test.  This is also the second time in this session that running a
# thing in an unintended CONTEXT found something that running it as intended could
# not, after the collision between generic basenames and the real corpus.
REPO_ROOT = os.path.dirname(HERE)

# Our own naming convention, recognised mechanically and only for stripping.
OUR_PREFIX = re.compile(r"^RX550_?")

# `#define RX550_FOO   0x3C   /* sid.h:397 */`  and the citation-less form
DEFINE = re.compile(
    r"^\s*#\s*define\s+(RX550_[A-Za-z0-9_]+)\s+(.+?)\s*$", re.M)
CITE = re.compile(r"/\*\s*([A-Za-z0-9_][A-Za-z0-9_.-]*\.[ch]):(\d+)\s*\*/")

LITERAL = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)[uUlL]*$")


def load_resolver(repo):
    """
    Import `citations.py` by path, so this tool reuses one index and one set of
    resolution rules instead of growing a second, subtly different one.
    """
    path = os.path.join(HERE, "citations.py")
    spec = importlib.util.spec_from_file_location("citations_resolver", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def strip_comment(rest):
    """The value, with any trailing /* ... */ removed."""
    return re.split(r"/\*", rest, maxsplit=1)[0].strip()


def parse_defines(text):
    """(name, raw_value, cited_file, cited_line) per #define."""
    out = []
    for m in DEFINE.finditer(text):
        name, rest = m.group(1), m.group(2)
        c = CITE.search(rest)
        out.append({
            "name": name,
            "raw": rest,
            "value": strip_comment(rest),
            "cited": c.group(1) if c else None,
            "at": int(c.group(2)) if c else None,
        })
    return out


UPSTREAM_DEFINE = re.compile(
    r"#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$")


def line_kind(raw):
    """
    What KIND of line a witness is.  Three kinds, and they do not carry the same
    weight, which is the whole reason this function exists.

      define   it defines the macro, so it carries the value
      comment  it is prose that enumerates the value, e.g. `/* 0 - me`
      code     it USES the encoding without carrying the value
    """
    t = raw.strip()
    if t.startswith("/*") or t.startswith("*") or t.startswith("//"):
        return "comment"
    if UPSTREAM_DEFINE.search(raw):
        return "define"
    return "code"


def comment_states(raw, value):
    """
    Does a comment witness actually state this value?

    `/* 0 - me` states 0.  A comment that says nothing numeric states nothing, and
    this returns False rather than True, because the alternative is a witness that
    agrees with everything and therefore proves nothing.

    Only the COMMENT PART is searched, and that distinction is not pedantry.  The
    first version of this function scanned the whole line, so
    `amdgpu_ring_write(ring, 0); /* mask */` counted as a witness stating 0 -- it
    does not state anything, the 0 belongs to the code, and the line is the body
    of a packet.  A witness that agrees for the wrong reason is worse than no
    witness, because it looks like corroboration.
    """
    if value is None:
        return False
    c = re.search(r"/\*(.*?)\*/", raw, re.S)
    if c:
        text = c.group(1)
    elif "/*" in raw:
        # An UNTERMINATED block comment is the normal shape here.  vid.h keeps
        # `WAIT_REG_MEM_ENGINE(x)` documented as
        #     186: #define WAIT_REG_MEM_ENGINE(x)  ((x) << 8)
        #     187:     /* 0 - me
        #     188:      * 1 - pfp
        #     189:      */
        # so line 187 opens a comment that closes three lines later, and a regex
        # that insists on the closing delimiter sees no comment at all.
        text = raw.split("/*", 1)[1]
    elif raw.strip().startswith(("*", "//")):
        text = raw
    else:
        return False
    return str(value) in set(re.findall(r"\d+", text))


def upstream_at(text, line_no):
    """
    What the cited line defines: (name, value) or (None, None).

    A line that is not a #define yields nothing, and that is NOT treated as a
    failure of the citation.  `sid.h`, `vid.h` and the gfx files interleave macros
    with prose, and a citation pointing at the prose that enumerates the encoding
    is a perfectly good witness -- it just carries the value differently.
    """
    lines = text.split("\n")
    if line_no < 1 or line_no > len(lines):
        return None, None, "OUT_OF_RANGE"
    raw = lines[line_no - 1]
    m = UPSTREAM_DEFINE.search(raw)
    if not m:
        return None, None, "NOT_A_DEFINE"
    return m.group(1), strip_comment(m.group(2)), None


def norm_value(v):
    """
    Canonical form of a numeric literal, or None if it is not one.

    Only normalisation of the SPELLING: 0x3C, 0X3c and 60 are the same number.
    Anything that needs evaluating is refused, and refused loudly.
    """
    if v is None:
        return None
    v = v.strip().rstrip("uUlL")
    if not LITERAL.match(v.strip()):
        return None
    try:
        return int(v, 0)
    except ValueError:
        return None


def our_bare_name(name):
    """RX550_PKT3_NOP -> pkt3_nop, for DISPLAY next to the upstream name."""
    return OUR_PREFIX.sub("", name).lower()


def check(repo, cites_mod, header=None):
    if header is None:
        header = os.path.join(repo, "07-DRIVER/kernel/rx550_pm4.h")
    text = open(header, encoding="utf-8", errors="replace").read()
    defines = parse_defines(text)

    index, roots = cites_mod.build_index(repo)
    cites_mod._INDEX = index

    rows = []
    for d in defines:
        row = dict(d)
        row["ours"] = our_bare_name(d["name"])
        row["ours_value"] = norm_value(d["value"])

        if not d["cited"]:
            row["verdict"] = "UNCITED"
            rows.append(row)
            continue

        if row["ours_value"] is None:
            row["verdict"] = "NOT_COMPARABLE"
            rows.append(row)
            continue

        # collapse_ambiguous=False on purpose: this tool's discriminator is the
        # VALUE, and it must see every same-named copy in order to use it.  The
        # default of the shared resolver would have refused to hand them over.
        res = cites_mod.resolve(d["cited"], d["at"], index, repo,
                                collapse_ambiguous=False)
        row["copies"] = res["copies"]
        row["subsystems"] = res.get("subsystems", [])
        row["verdict"] = "AGREE"

        if res["copies"] == 0:
            row["verdict"] = "UNRESOLVED"
            rows.append(row)
            continue
        if res["verdict"] == "OUT_OF_RANGE":
            row["verdict"] = "OUT_OF_RANGE"
            rows.append(row)
            continue
        if not res["hits"]:
            row["verdict"] = res["verdict"]
            rows.append(row)
            continue

        # only the copies whose line is actually a #define can arbitrate
        agreeing, notes, kinds = [], [], []
        for h in res["hits"]:
            full = open(os.path.join(repo, h["path"]), encoding="utf-8",
                        errors="replace").read()
            name, val, err = upstream_at(full, d["at"])
            if err:
                notes.append(err)
                raw = full.split("\n")[d["at"] - 1] if err == "NOT_A_DEFINE" else ""
                k = line_kind(raw)
                kinds.append(k)
                if k == "comment" and comment_states(raw, row["ours_value"]):
                    agreeing.append({"path": h["path"], "name": "(prose)",
                                     "value": raw.strip()[:18], "kind": k,
                                     "version": h.get("version", "?"),
                                     "subsystem": h.get("subsystem"),
                                     "norm": row["ours_value"], "same": True})
                continue
            up = norm_value(val)
            agreeing.append({"path": h["path"], "name": name, "value": val,
                             "kind": "define",
                             "version": h.get("version", "?"),
                             "subsystem": h.get("subsystem"),
                             "norm": up,
                             "same": (up is not None and
                                      up == row["ours_value"])})
        row["witnesses"] = agreeing
        row["notes"] = sorted(set(notes))
        row["kinds"] = sorted(set(kinds))

        # AMBIGUOUS is not a dead end, and treating it as one threw away the whole
        # packet-header family.  `sid.h` has ten copies across two subsystems, so
        # the CITATION does not say which file -- but the author copied a VALUE out
        # of the file they had open, so a value that matches exactly one candidate
        # identifies it.  That is an inference from the author's own act, not a
        # guess about intent.
        #
        # And when the value does NOT discriminate -- several copies agree with us
        # and several do not -- that is reported as AMBIGUOUS again, because then
        # the value has not resolved anything and pretending otherwise would be
        # inventing an authority the evidence does not carry.
        hit = [a for a in agreeing if a["same"]]
        miss = [a for a in agreeing if not a["same"]]
        only_code = [a for a in agreeing if a.get("kind") == "code"]
        row["matches"] = len(hit)
        row["defines_at_line"] = len(agreeing)

        if not agreeing:
            if "code" in kinds:
                row["verdict"] = "WITNESS_USAGE"
            else:
                row["verdict"] = notes[0] if notes else "UNRESOLVED"
        elif hit and all(a.get("kind") == "comment" for a in hit):
            row["verdict"] = "AGREE_COMMENT"
        elif hit and not miss:
            row["verdict"] = "AGREE"
        elif hit and miss:
            subs_hit = set(a.get("subsystem") for a in hit)
            subs_all = set(a.get("subsystem") for a in agreeing)
            if subs_hit and subs_hit < subs_all:
                # our value picks out ONE subsystem and the others disagree
                row["verdict"] = "AGREE_DISCRIMINATING"
            else:
                row["verdict"] = "AMBIGUOUS"
        else:
            row["verdict"] = "DISAGREE"
        rows.append(row)

    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    return rows, tally, len(defines)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 70)
    fails = 0
    checks = 0
    # read ONCE, at the top: a check half way through wanted it and found it
    # unbound, which is the same class of mistake as depending on the cwd
    src = open(__file__, encoding="utf-8").read()

    checks += 1
    d = parse_defines("#define RX550_A 0x3C /* sid.h:1 */\n")
    if len(d) == 1 and d[0]["name"] == "RX550_A" and d[0]["value"] == "0x3C" \
       and d[0]["cited"] == "sid.h" and d[0]["at"] == 1:
        print("  OK    a define with a witness citation is split into name, value,")
        print("        cited file and cited line")
    else:
        print("  FAIL  parse_defines gave %s" % d)
        fails += 1

    checks += 1
    d = parse_defines("#define RX550_B 0x1\n")
    if d and d[0]["cited"] is None:
        print("  OK    a define with no witness is UNCITED, not assumed correct")
    else:
        print("  FAIL  %s" % d)
        fails += 1

    checks += 1
    if norm_value("0x3C") == norm_value("60") == norm_value("0X3c"):
        print("  OK    0x3C, 60 and 0X3c are the same number")
    else:
        print("  FAIL  spelling normalisation is wrong")
        fails += 1

    checks += 1
    if norm_value("((x) << 8)") is None and norm_value("(1u << 16)") is None:
        print("  OK    an expression is REFUSED, not evaluated: guessing it would")
        print("        be wrong silently")
    else:
        print("  FAIL  an expression was evaluated by a regex")
        fails += 1

    checks += 1
    n, v, err = upstream_at("a\n#define PACKET3_NOP 0x10\nb\n", 2)
    if (n, v, err) == ("PACKET3_NOP", "0x10", None):
        print("  OK    the cited line yields the upstream name and its value")
    else:
        print("  FAIL  upstream_at gave %s" % ((n, v, err),))
        fails += 1

    checks += 1
    n, v, err = upstream_at("a\n/* a comment */\n", 2)
    if n is None and err == "NOT_A_DEFINE":
        print("  OK    a citation pointing at a comment is NOT_A_DEFINE, not AGREE")
    else:
        print("  FAIL  %s" % ((n, err),))
        fails += 1

    checks += 1
    n, v, err = upstream_at("a\n", 99)
    if err == "OUT_OF_RANGE":
        print("  OK    a cited line past EOF is OUT_OF_RANGE")
    else:
        print("  FAIL  %s" % err)
        fails += 1

    checks += 1
    if our_bare_name("RX550_PKT3_WAIT_REG_MEM") == "pkt3_wait_reg_mem":
        print("  OK    our name is reduced for DISPLAY only: %s"
              % our_bare_name("RX550_PKT3_WAIT_REG_MEM"))
    else:
        print("  FAIL  name reduction")
        fails += 1

    # the composition itself must be live, not just imported
    checks += 1
    try:
        mod = load_resolver(REPO_ROOT)
        if hasattr(mod, "resolve") and hasattr(mod, "build_index"):
            print("  OK    citations.py is imported and used, not reimplemented")
        else:
            print("  FAIL  the imported module lacks the resolver")
            fails += 1
    except Exception as exc:
        print("  FAIL  could not load citations.py: %s" % exc)
        fails += 1

    # the report path, which the primitives above do not exercise
    checks += 1
    try:
        rows, tally, total = check(REPO_ROOT, mod)
        if total > 0 and tally:
            print("  OK    check() runs end to end on the real header: %d "
                  "constants, %d verdicts" % (total, len(tally)))
        else:
            print("  FAIL  check() returned %r / %r" % (tally, total))
            fails += 1
    except Exception as exc:
        print("  FAIL  check() raised %s: %s" % (type(exc).__name__, exc))
        fails += 1

    checks += 1
    import io
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = main(["--repo", REPO_ROOT, "--json"])
        if rc == 0:
            print("  OK    main --json runs end to end (%d bytes of JSON "
                  "captured, not printed)" % len(buf.getvalue()))
        else:
            print("  FAIL  main --json rc=%d" % rc)
            fails += 1
    except SystemExit:
        pass
    except Exception as exc:
        print("  FAIL  main raised %s: %s" % (type(exc).__name__, exc))
        fails += 1

    # The needle is assembled at run time.  Fourth time in this project that a guard
    # written as a literal string matches its own text: toolreg.py's interlock,
    # snapshot.py's default-value guess, constmap's SPECIFICITY check, and this one.
    # The pattern is stable enough to name, and the fix is always the same: build the
    # needle, or assert the behaviour instead of the text.
    checks += 1
    needle = "os.get" + "cwd" + "()"
    self_part = src.split("def run_selftest", 1)[1]
    if needle not in self_part:
        print("  OK    the self-test does not read the current directory, so it")
        print("        passes from any cwd -- which is how toolreg runs it")
    else:
        print("  FAIL  the self-test still depends on the working directory")
        fails += 1

    checks += 1
    tool_part = src.split("def run_selftest", 1)[0]
    writes = re.search(r"open\([^)]*,\s*[\"'][wa]", tool_part) or \
        re.search(r"os\.remove|shutil\.|makedirs|\.write\(", tool_part)
    if not writes:
        print("  OK    the TOOL has no write, move or remove path")
    else:
        print("  FAIL  the tool writes: %s" % writes.group(0))
        fails += 1

    checks += 1
    if line_kind("#define X 0x10") == "define" and \
       line_kind("\t\t/* 0 - me") == "comment" and \
       line_kind("\t * 1 - pfp") == "comment" and \
       line_kind("\tamdgpu_ring_write(ring, 0); /* mask */") == "code":
        print("  OK    a witness line is classified: define / comment / code")
    else:
        print("  FAIL  line_kind misclassified")
        fails += 1

    checks += 1
    if comment_states("/* 0 - me", 0) and not comment_states("/* 0 - me", 1):
        print("  OK    a comment witness states 0 and does NOT state 1")
    else:
        print("  FAIL  comment_states is wrong")
        fails += 1

    checks += 1
    if not comment_states("/* nothing numeric here */", 0):
        print("  OK    a comment with no number states nothing, rather than")
        print("        agreeing with every value and so proving nothing")
    else:
        print("  FAIL  a numeric-free comment was treated as a witness")
        fails += 1

    checks += 1
    if line_kind("\tamdgpu_ring_write(ring, 0); /* mask */") == "code" and \
       not comment_states("\tamdgpu_ring_write(ring, 0); /* mask */", 0):
        print("  OK    CODE carrying a 0 in its trailing comment is NOT accepted as")
        print("        a comment witness: it does not state the encoding")
    else:
        print("  FAIL  a usage line was mistaken for a prose witness")
        fails += 1

    # THE GUARD THAT MATTERS, and it is behavioural on purpose.
    #
    # The previous version of this check was `if "SPECIFICITY" not in src`, and it
    # FAILED, because the string "SPECIFICITY" was inside the check itself.  That
    # is the third time in this project a guard written as a literal string has
    # found itself: toolreg.py shipped an interlock that refused to run, and
    # snapshot.py shipped a "no default-value guess" check that matched its own
    # text.  Three instances is a pattern, not an accident, and the fix is not to
    # grep more carefully -- a grep can always be defeated by the next person who
    # does not remember.  The fix is a guard that cannot be defeated by text at all.
    #
    # So: assert the PROPERTY.  If the value arbitrates and the name is only
    # displayed, then renaming the upstream macro must not change the verdict.  A
    # name-similarity heuristic would change it; this implementation cannot.
    import tempfile
    tmp = tempfile.mkdtemp(prefix="constmap-selftest-")
    try:
        os.makedirs(os.path.join(tmp, "07-DRIVER/kernel"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "d/s"), exist_ok=True)
        hdr = ("#define RX550_PKT3_NOP 0x10 /* w.h:1 */\n")
        open(os.path.join(tmp, "07-DRIVER/kernel/rx550_pm4.h"), "w",
             encoding="utf-8").write(hdr)
        for nm in ("PACKET3_NOP", "TOTALLY_UNRELATED_TOKEN", "ZZZ"):
            open(os.path.join(tmp, "d/s/w.h"), "w",
                 encoding="utf-8").write("#define %s 0x10\n" % nm)
            rows2, t2, _n = check(tmp, mod)
            v = rows2[0]["verdict"] if rows2 else "(none)"
            if v != "AGREE":
                print("  FAIL  renaming upstream to %s changed the verdict to %s"
                      % (nm, v))
                fails += 1
                break
        else:
            checks += 1
            print("  OK    the VALUE arbitrates: renaming the upstream macro to")
            print("        TOTALLY_UNRELATED_TOKEN leaves the verdict AGREE, so no")
            print("        name-similarity score can be driving it")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print("  " + "-" * 70)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  ESTA HERRAMIENTA COMPRUEBA NÚMEROS CONTRA UNA LÍNEA DE TESTIGO.  No")
    print("  dice que una constante sea correcta en su semántica: AGREE prueba que")
    print("  el número coincide con una línea de una cabecera, y qué significa ese")
    print("  número es la OTRA pregunta de F3d, y sigue abierta.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

ORDER = ["DISAGREE", "AMBIGUOUS", "AGREE_DISCRIMINATING", "AGREE_COMMENT",
         "WITNESS_USAGE", "NOT_A_DEFINE", "NOT_COMPARABLE", "UNRESOLVED",
         "OUT_OF_RANGE", "UNCITED", "AGREE"]


def main(argv):
    ap = argparse.ArgumentParser(
        prog="constmap",
        description="check every RX550_* constant against the upstream line it "
                    "cites as its witness")
    ap.add_argument("--repo", default=REPO_ROOT,
                    help="raiz del repositorio.  Por defecto REPO_ROOT, que se deriva de "
                         "__file__ en :128 -- la misma regla que el comentario de :116. "
                         "El camino de la CLI estaba en default='.' con abspath, "
                         "o sea cwd: hallazgo 1051.")
    ap.add_argument("--header", default=None)
    ap.add_argument("--disagree", action="store_true",
                    help="only the constants whose value does not match")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version",
                    version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    mod = load_resolver(repo)
    rows, tally, total = check(repo, mod, args.header)

    if args.json:
        print(json.dumps({"total": total, "tally": tally, "rows": rows},
                         indent=2, sort_keys=True, default=str))
        return 0

    hdr = args.header or "07-DRIVER/kernel/rx550_pm4.h"
    print("%s %s -- constantes propias contra la línea que citan" % (TOOL, VERSION))
    print("  " + "-" * 74)
    print("  cabecera   %s" % hdr)
    print("  constantes %d   con testigo %d   sin testigo %d"
          % (total, sum(1 for r in rows if r["cited"]),
             sum(1 for r in rows if not r["cited"])))
    print("")
    for v in ORDER:
        if tally.get(v):
            print("  %-20s %d" % (v, tally[v]))
    print("")

    shown = [r for r in rows if not args.disagree or
             r["verdict"] in ("DISAGREE", "AGREE_DISCRIMINATING",
                              "AGREE_COMMENT")]
    for r in shown:
        print("  %-20s %-34s = %-18s" % (r["verdict"], r["name"],
                                         r["value"][:18]))
        if r["cited"]:
            print("       testigo %s:%d" % (r["cited"], r["at"]))
            seen = set()
            for w in (r.get("witnesses") or []):
                key = (w["name"], w["value"])
                if key in seen:
                    continue
                seen.add(key)
                print("         %-8s %-7s %-8s %-20s = %-14s %s"
                      % ("coincide" if w["same"] else "DIFIERE", w["version"],
                         w.get("kind", "define")[:8], w["name"][:20],
                         w["value"][:14],
                         w["path"].split("linux-7.1.3/")[-1][:42]))
            if r.get("defines_at_line"):
                print("         el valor discrimina %d de %d copias que definen "
                      "algo en esa línea" % (r.get("matches", 0),
                                             r["defines_at_line"]))
            if r["verdict"] == "AMBIGUOUS":
                print("         AMBIGUO: %d copias de %s en %d subsistemas y el"
                      % (r["copies"], r["cited"], len(r["subsystems"])))
                print("         valor NO discrimina, así que no se decide")
            if r["verdict"] == "AGREE_DISCRIMINATING":
                print("         nuestro valor señala UN subsistema y los otros "
                      "discrepan:")
            if r.get("notes"):
                print("         %s en %d copia(s)" % (", ".join(r["notes"]),
                                                      r["copies"]))
        if r["verdict"] == "NOT_COMPARABLE":
            print("       valor con expresión: no se evalúa, y no se adivina")
        if r["verdict"] == "UNCITED":
            print("       sin testigo: aquí no hay contra qué comprobarlo")
        if r["verdict"] == "WITNESS_USAGE":
            print("       el testigo USA la codificación pero no lleva el valor:")
            print("       corrobora que el tema es ese, no qué número es. No es un")
            print("       defecto: la línea está en la función correcta")
    print("")
    print("  EL VALOR ARBITRA Y EL NOMBRE SE MUESTRA.  Que RX550_PKT3_WAIT_REG_MEM")
    print("  y PACKET3_WAIT_REG_MEM sean lo mismo exige saber que PKT3 abrevia")
    print("  PACKET3, y eso es conocimiento: meterlo en la herramienta pondría una")
    print("  suposición donde va una medición, y podría casar dos constantes")
    print("  distintas con una sin decir nada.")
    print("  AGREE prueba que el número coincide con una línea.  Lo que el número")
    print("  SIGNIFICA es la otra pregunta de F3d, y sigue abierta.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))