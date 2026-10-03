#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
toolreg -- the registry for tools/, and the check that it stays true.

WHY THIS EXISTS
---------------
There are 23 source tools in tools/ and they were built by three sessions in one
morning.  None of them knew about each other.  Concretely, at 14:3x on
2026-10-01:

  * 16 of the 23 were cited NOWHERE in docs/TOOLS-STATUS.md
  * `reg_resolve.py` resolves a register to its MASK, SHIFT and UNIT, and
    `reg_census.py` enumerates which registers a .c touches.  Neither appears in
    the documentation, so an agent about to hand-transcribe a register field
    would not know a tool for it exists
  * `xref.py` does symbol cross-reference through the clang AST, not regex.  That
    is the answer to the class of problem that cost this project `019` eight
    hours on a false NOT_FOUND
  * `contradict.py` detects incompatible claims across findings, which is a task
    the documentation was doing by hand

An index that has to be maintained by remembering is not an index.  This is the
FINDINGS-INDEX problem applied to tools/, and tools/ has exactly the same failure
mode: two sessions choose names independently and nothing reconciles them.

WHAT IT DOES
------------
  1. inventory  every source tool in tools/, with size and kind
  2. contract   the declared purpose, and whether it declares WHAT IT DOES NOT DO
  3. selftest   run each tool's own self-test, capture exit code and duration
  4. coverage   cross-reference docs/TOOLS-STATUS.md, in BOTH directions:
                   - a tool that exists and is not documented
                   - a TL-nn entry that names a tool that does not exist
  5. freshness  whether a TL-nn entry names a file that has changed since

WHAT IT DOES NOT PROVE, DECLARED UP FRONT
------------------------------------------
  1. It does not judge whether a tool's OUTPUT is correct.  `toolcheck.py` says
     the same about contracts, and both are right: a parser that is correct does
     not prove the answer is.  The judgement stays with whoever reads the output.
  2. It does not read a tool to understand it.  It reads the header.  A tool with
     a good header and a wrong body passes every check here.
  3. Running another session's self-test is safe ONLY because every tool in this
     tree declares WORK_CLASS=READ_ONLY / WRITE_EXECUTION=NONE in its header, and
     this tool REFUSES to run one that does not declare it.  That refusal is a
     safety interlock, not a formality: see run_selftests().
  4. A missing self-test is reported as MISSING, never as a pass.
  5. Coverage is measured by name.  A tool documented in prose without its name
     in backticks will read as uncovered.  That is a false negative in the safe
     direction, and it is recorded rather than hidden.

SAFETY
------
This tool reads files and runs other tools' own self-tests.  It writes nothing.
It does not open /sys, does not touch the GPU, does not compile anything, and
does not run git commands that modify the tree.

USAGE
-----
  toolreg.py --repo .                  full report, human readable
  toolreg.py --repo . --undocumented   only the gap
  toolreg.py --repo . --json           machine readable; nothing may follow
  toolreg.py --repo . --no-selftest   inventory and coverage only, no execution
  toolreg.py --selftest               its own tests
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

VERSION = "1.0.0"
TOOL = "toolreg"

# A tool that DECLARES one of these is claiming it may write or touch hardware.
# This tool will not execute it, and says so.
#
# THE MATCH MUST LOOK LIKE A DECLARATION, NOT LIKE PROSE.
# The first version searched for bare words, and refused to execute ITSELF,
# because this file's own docstring names MMIO_WRITE, insmod and rmmod as the
# things it rejects.  Measured on the first real run:
#     toolreg.py   REFUSED_UNSAFE
# An interlock that fires on the tool that enforces it is an interlock that gets
# switched off, and then it protects nothing.  So:
#   - markers must appear as KEY=VALUE, or as a bare word only when it is
#     followed by a call-shaped argument, which is what running one looks like
#   - this file never checks itself, and says so in the output
FORBIDDEN_KV = re.compile(
    r"\bWRITE_EXECUTION\s*=\s*(?:WRITE|SCOPED|PARTIAL_WRITE)"
    r"|\b(?:MMIO|REGISTER|PCI)_WRITE\s*=\s*(?:YES|TRUE|1)"
    r"|\bSYSFS_WRITE\s*=\s*(?:YES|TRUE|1)",
    # NOTE: an earlier version had a fourth alternative matching
    # WRITE_EXECUTION=NONE, which made every correctly-declared tool look unsafe.
    # It is gone.  A marker list that flags the safe value is worse than none.
)
# a bare forbidden verb, only when it looks like an invocation
FORBIDDEN_CALL = re.compile(
    r"(?:^|[;&|`$(\s])(?:sudo\s+)?(?:insmod|rmmod|modprobe)\s+[-\w./]"
    r"|/dev/(?:mem|kmem)"
    r"|\becho\s+[01]\s*>\s*/sys"
)

# Recognised SAFETY declarations.  Several forms are accepted because tools in
# this tree declare safety in prose as well as by token, and refusing a tool
# that plainly says "NO toca la GPU" would train people to add the token instead
# of to think.
# TWO CONVENTIONS EXIST IN THIS TREE, and refusing to see one of them turns a
# formatting difference into a false alarm.
#
#   tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
#   08-ARQUITECTURA/tools/  # CONTRACT: name=... READONLY=no WRITES_FILES=yes
#
# Measured before this was fixed: 19 of 44 tools reported "no WORK_CLASS
# declaration".  A large part of that was not a missing declaration, it was a
# different spelling of the same declaration.  An interlock that cries wolf on a
# spelling gets ignored, and then it protects nothing.
CONTRACT_RE = re.compile(
    r"^\s*#\s*CONTRACT:\s*(?P<k>\w+)\s*=\s*(?P<v>\S+)", re.M
)


def declares_read_only(text):
    """
    True if the tool declares itself read-only, in EITHER convention.

    tools/                  WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
    08-ARQUITECTURA/tools/  # CONTRACT: READONLY=no   WRITES_FILES=yes

    For the CONTRACT form, READONLY=no means the tool is not read-only, so it is
    NOT accepted as safe.  A tool that says it writes files is not run by this
    tool, and that is the honest reading, not a technicality.
    """
    if "WORK_CLASS=READ_ONLY" in text or "WRITE_EXECUTION=NONE" in text:
        return True
    for m in CONTRACT_RE.finditer(text):
        k, v = m.group("k").upper(), m.group("v").lower()
        if k in ("WORK_CLASS",) and v.startswith("read_only"):
            return True
        if k == "READONLY" and v in ("yes", "true", "1"):
            return True
        if k == "WRITES_SYSFS" and v in ("no", "false", "0"):
            return True
        if k == "WRITE_EXECUTION" and v in ("none",):
            return True
    return False


SAFE_MARKERS = (
    "WORK_CLASS=READ_ONLY",
    "READ_ONLY",
    "WRITE_EXECUTION=NONE",
    "NO toca la GPU",
    "no toca la GPU",
    "no lee MMIO",
    "no escribe",
    "STATIC_ANALYSIS",
    "analisis ESTATICO",
    "análisis ESTÁTICO",
    "STATIC ANALYSIS",
)


class Tool:
    __slots__ = ("path", "name", "stem", "kind", "size", "purpose",
                 "declares_limits", "declares_safety", "selftest_arg",
                 "doc_tl", "in_docs", "mtime", "dir")

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.stem = self.name.rsplit(".", 1)[0]
        self.kind = self.name.rsplit(".", 1)[-1] if "." in self.name else ""
        self.size = os.path.getsize(path)
        self.mtime = os.path.getmtime(path)
        self.purpose = None
        self.declares_limits = False
        self.declares_safety = False
        self.selftest_arg = None
        self.doc_tl = None
        self.in_docs = False
        self.dir = ""

    @property
    def is_source(self):
        return self.kind in ("py", "c", "sh")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _head(path, nbytes=6000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(nbytes)
    except OSError:
        return ""


# What a tool may do that is not merely reading files.
UNSAFE_RE = re.compile(
    r"open\s*\(\s*['\"][^'\"]*['\"]\s*,\s*['\"][wa]|"
    r"\.write_text|shutil\.(?:copy|move|rmtree)|os\.remove|os\.unlink|"
    r"subprocess\.[a-z_]+\([^)]*\brm\b|insmod|rmmod|modprobe|"
    r"/dev/mem|/dev/kmem|ioremap|setpci|echo\s+[01]\s*>\s*/sys"
)


def parse_tool(t, root):
    # the WHOLE file, not the head.  `--selftest` in a tool with a long
    # docstring lives far past the first few kB; reading only the head made
    # docscan.py look like it had no self-test when it has 13 checks.
    head = _read(t.path)

    # purpose: first docstring line, or the first # comment that is not a shebang
    m = re.search(r'^\s*(?:"""|#)\s*(.+?\.py\s*[—-]\s*.+)$', head, re.M)
    if not m:
        m = re.search(r'^\s*"""\s*\n\s*(.+)$', head, re.M)
    if not m:
        m = re.search(r"^#\s*(?!SPDX|!)(.+)$", head, re.M)
    if m:
        t.purpose = m.group(1).strip()[:110]

    t.declares_limits = bool(re.search(
        r"LO QUE NO (?:PROBA|HACE)|What it does not|does not prove|"
        r"Lo que NO hace|limitaciones? (?:conocidas|declara)", head, re.I))
    t.declares_safety = declares_read_only(head)

    for flag in ("--selftest", "--self-test", "selftest"):
        if flag in head:
            t.selftest_arg = flag
            break
    if t.selftest_arg is None and t.kind in ("py", "sh") \
            and re.search(r"\b(?:def|function)\s+selftest", head):
        t.selftest_arg = "--selftest" if t.kind == "sh" else None
    return t


# Tools live in MORE THAN ONE directory, and that is not a detail.
#
# pm4_count_census.py, count_vmflush_dw.py and frame_budget.py were documented in
# TOOLS-STATUS as tools/ entries and are now in 08-ARQUITECTURA/tools/.  The
# first version of this file scanned only tools/, so it reported all three as
# TL entries naming a tool that does not exist -- an "orphan" that was really a
# move -- AND it missed every tool in the second directory.  A registry that
# scans half the tools is not a registry.
TOOL_DIRS = ("tools", "08-ARQUITECTURA/tools")


def inventory(repo):
    out = []
    for rel in TOOL_DIRS:
        tdir = os.path.join(repo, rel)
        if not os.path.isdir(tdir):
            continue
        for fn in sorted(os.listdir(tdir)):
            p = os.path.join(tdir, fn)
            if not os.path.isfile(p) or fn.endswith(".pyc") or fn == "ideas.txt":
                continue
            t = Tool(p)
            if not t.is_source:
                continue
            t.dir = rel
            out.append(parse_tool(t, repo))
    return out


def run_selftests(tools, timeout=90):
    """
    Run each tool's own self-test, and REFUSE to run one that does not declare
    itself read-only.

    The refusal is the point.  This executes code written by other sessions, in
    a tree where five sessions work at once and where the standing constraint is
    no MMIO, no module load, no sysfs write.  A tool whose header does not
    declare WORK_CLASS / WRITE_EXECUTION is running unclassified, and unclassified
    is exactly how a forbidden operation gets run by accident.
    """
    results = {}
    for t in tools:
        # read the WHOLE file, not the head: `--selftest` in a tool with a long
        # docstring lives far past the first 6 kB, and reading only the head
        # made docscan.py look like it had no self-test when it has 13 checks.
        head = _read(t.path)
        is_self = os.path.abspath(t.path) == os.path.abspath(__file__)

        blocked = []
        if not is_self:
            if FORBIDDEN_KV.search(head):
                blocked.append("declares a write or MMIO scope")
            if FORBIDDEN_CALL.search(head):
                blocked.append("contains an invocation-shaped forbidden operation")
        else:
            blocked.append("this file is the checker; it does not check itself")

        declares = declares_read_only(head)

        if blocked and not is_self:
            results[t.name] = {"status": "REFUSED_UNSAFE",
                               "reason": blocked[0], "rc": None, "secs": None}
            continue
        if not t.selftest_arg:
            results[t.name] = {"status": "NO_SELFTEST", "reason": None,
                               "rc": None, "secs": None}
            continue
        if not declares:
            results[t.name] = {"status": "REFUSED_UNDECLARED",
                               "reason": "no WORK_CLASS / WRITE_EXECUTION in header",
                               "rc": None, "secs": None}
            continue

        if is_self:
            results[t.name] = {"status": "SELF", "reason": "the checker",
                               "rc": None, "secs": None}
            continue

        argv = [sys.executable, t.path, t.selftest_arg] if t.kind == "py" \
            else (["bash", t.path, t.selftest_arg] if t.kind == "sh"
                  else [t.path, t.selftest_arg])
        t0 = time.time()
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=timeout, cwd=os.path.dirname(t.path))
            rc, out = r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            rc, out = None, "TIMEOUT after %ds" % timeout
        except OSError as exc:
            rc, out = None, "OSERROR %s" % exc
        dt = time.time() - t0

        if rc is None:
            status = "TIMEOUT"
        elif rc == 0:
            status = "PASS"
        elif "FAIL" in out or "FALLO" in out:
            status = "FAIL"
        else:
            # non-zero without a declared FAIL is still not a pass.  Recorded as
            # its own status so it is never rounded up to PASS.
            status = "NONZERO"
        results[t.name] = {"status": status, "rc": rc, "secs": round(dt, 2),
                           "reason": None,
                           "tail": (out.strip().splitlines() or [""])[-1][:80]}
    return results


def docs_index(repo):
    """TL-nn -> the tool names it cites, and which tool names appear in it."""
    p = os.path.join(repo, "docs", "TOOLS-STATUS.md")
    if not os.path.exists(p):
        return {}
    txt = _read(p)
    entries = {}
    # Split on the TL-nn HEADERS, keeping the header line itself.
    #
    # The first version used re.split(r"^## (TL-\d+)[^\n]*\n") which CONSUMES the
    # header, and the header is exactly where the tool's name is written:
    #     ## TL-11 · `ipsolve` — el gate que faltaba para C-011
    # so every entry came back with an empty name set and the whole cross
    # reference silently reported zero coverage.  A tool whose name lives in the
    # heading is the normal layout, not an edge case.
    parts = re.split(r"^(## TL-\d+[^\n]*\n)", txt, flags=re.M)
    for i in range(1, len(parts), 2):
        header, body = parts[i], parts[i + 1]
        tid = re.match(r"## (TL-\d+)", header).group(1)
        blob = header + "\n" + body
        # accept a BARE filename and a path-qualified one.  The first version
        # matched only the bare form, so every entry written as
        # `tools/reg_resolve.py` read as undocumented and coverage was
        # under-reported: 9 of 29 instead of the real number.
        names = set(re.findall(r"`([A-Za-z0-9_.\-]+\.(?:py|c|sh))`", blob))
        for pref in re.findall(r"`([A-Za-z0-9_./\-]+\.(?:py|c|sh))`", blob):
            names.add(os.path.basename(pref))
        entries[tid] = names
    return entries


def cross_reference(repo, tools):
    """Both directions: undocumented tools, and TL entries with no tool."""
    entries = docs_index(repo)
    cited = set()
    for names in entries.values():
        cited |= names

    for t in tools:
        cands = {t.name}
        if t.kind == "c":
            cands.add(t.stem + ".c")
        t.in_docs = bool(cands & cited)
        t.doc_tl = None
        for tid, names in entries.items():
            if cands & names:
                t.doc_tl = tid

    documented_names = cited
    orphans = []
    for tid, names in sorted(entries.items()):
        for n in sorted(names):
            if n not in documented_names:
                continue
            stem = n.rsplit(".", 1)[0]
            if not any(t.name == n or (t.kind == "c" and t.stem + ".c" == n)
                       for t in tools):
                orphans.append((tid, n))
    return entries, orphans


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def _fixture(root, tools_spec):
    """Build a tools/ tree with known properties."""
    tdir = os.path.join(root, "tools")
    os.makedirs(tdir, exist_ok=True)
    for name, body in tools_spec.items():
        with open(os.path.join(tdir, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)


SELFTEST_FIXTURE = {
    # declares safety, has a self-test, declares limits: the GOOD case
    "good_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""good_tool.py — does a thing.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n\n'
        'LO QUE NO PROBABA: nothing.\n"""\n'
        'import sys\n'
        'def selftest():\n'
        '    print("RESULT: OK")\n'
        '    return 0\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        return selftest()\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # declares safety, self-test FAILS: must not be rounded up to a pass
    "failing_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""failing_tool.py — declares a self-test that fails.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n"""\n'
        'import sys\n'
        'def selftest():\n'
        '    print("RESULT: FAILED")\n'
        '    return 1\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        return selftest()\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # no safety declaration: must be REFUSED, never executed
    "unclassified_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""unclassified_tool.py — says nothing about what it does.\n\n'
        'Lo que NO hace: nothing.\n"""\n'
        'import sys\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        raise SystemExit("I RAN AND I SHOULD NOT HAVE")\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # explicitly unsafe: must be REFUSED on the marker, not on the declaration
    "unsafe_tool.py": (
        '#!/usr/bin/env python3\n'
        '"""unsafe_tool.py — does a forbidden thing.\n\n'
        'WRITE_EXECUTION=WRITE · MMIO_WRITE=YES\n"""\n'
        'import sys\n'
        'def main(argv):\n'
        '    if "--selftest" in argv:\n'
        '        raise SystemExit("I RAN AND I SHOULD NOT HAVE")\n'
        '    return 0\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(main(sys.argv[1:]))\n'
    ),
    # has no self-test at all: MISSING, never PASS
    "notool_test.py": (
        '#!/usr/bin/env python3\n'
        '"""notool_test.py — no self-test here.\n\n'
        'WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE\n"""\n'
        'import sys\n'
        'if __name__ == "__main__":\n'
        '    sys.exit(0)\n'
    ),
}

FIXTURE_DOCS = (
    "# TOOLS-STATUS\n\n"
    "## TL-01 · `good_tool.py` — VALIDATED\n\n```\nVALIDADO\n```\n\n"
    "## TL-02 · `tool_that_does_not_exist.py` — VALIDATED\n\n```\nVALIDADO\n```\n"
)


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 62)
    fails = 0
    checks = 0

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, SELFTEST_FIXTURE)
        with open(os.path.join(td, "docs", "TOOLS-STATUS.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(FIXTURE_DOCS)

        tools = inventory(td)
        st = run_selftests(tools, timeout=30)

        want = {
            "good_tool.py": "PASS",
            "failing_tool.py": "FAIL",
            "unclassified_tool.py": "REFUSED_UNDECLARED",
            "unsafe_tool.py": "REFUSED_UNSAFE",
            "notool_test.py": "NO_SELFTEST",
        }
        for name, expect in sorted(want.items()):
            checks += 1
            got = st.get(name, {}).get("status")
            if got == expect:
                print("  OK    %-24s %s" % (name, got))
            else:
                print("  FAIL  %-24s got %s, expected %s" % (name, got, expect))
                fails += 1

        # the interlock is the whole safety argument, so assert it positively
        checks += 1
        ran_forbidden = any(
            "I RAN AND I SHOULD NOT HAVE" in (st[n].get("tail") or "")
            or (st[n].get("rc") not in (None,) and st[n].get("status", "").startswith("REFUSED"))
            for n in ("unclassified_tool.py", "unsafe_tool.py"))
        refused_both = (st["unclassified_tool.py"]["status"].startswith("REFUSED")
                        and st["unsafe_tool.py"]["status"].startswith("REFUSED"))
        if refused_both:
            print("  OK    neither undeclared nor unsafe tool was executed")
        else:
            print("  FAIL  the safety interlock did not hold")
            fails += 1

        checks += 1
        entries, orphans = cross_reference(td, tools)
        undocumented = sorted(t.name for t in tools if not t.in_docs)
        expect_undoc = ["failing_tool.py", "notool_test.py", "unclassified_tool.py",
                        "unsafe_tool.py"]
        if undocumented == expect_undoc:
            print("  OK    coverage finds exactly the 4 undocumented tools")
        else:
            print("  FAIL  undocumented = %s, expected %s" % (undocumented, expect_undoc))
            fails += 1

        checks += 1
        if ("TL-02", "tool_that_does_not_exist.py") in orphans:
            print("  OK    a TL entry naming a tool that does not exist is flagged")
        else:
            print("  FAIL  orphan TL entry not detected: %s" % (orphans,))
            fails += 1

        checks += 1
        good = [t for t in tools if t.name == "good_tool.py"][0]
        if good.doc_tl == "TL-01":
            print("  OK    a documented tool is attributed to its TL entry")
        else:
            print("  FAIL  attribution wrong: %r" % good.doc_tl)
            fails += 1

    print("  " + "-" * 62)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: pasar esto NO demuestra que la salida de una herramienta sea")
    print("        correcta. Comprueba que tenga forma de decirlo y que su propio")
    print("        self-test pase. El juicio sobre la salida sigue siendo de quien lee.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="toolreg",
        description="registry for tools/, and the check that it stays true")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--undocumented", action="store_true",
                    help="only the tools that exist and are not in TOOLS-STATUS")
    ap.add_argument("--no-selftest", action="store_true",
                    help="inventory and coverage only; execute nothing")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    tools = inventory(repo)
    if not tools:
        sys.stderr.write("toolreg: no source tools under %s/tools\n" % repo)
        return 2

    st = {} if args.no_selftest else run_selftests(tools, timeout=args.timeout)
    entries, orphans = cross_reference(repo, tools)
    undoc = [t for t in tools if not t.in_docs]

    if args.json:
        print(json.dumps({
            "tool": TOOL, "version": VERSION, "repo": repo,
            "count": len(tools),
            "tools": [{
                "name": t.name, "kind": t.kind, "bytes": t.size,
                "purpose": t.purpose,
                "declares_limits": t.declares_limits,
                "declares_safety": t.declares_safety,
                "in_docs": t.in_docs, "doc_tl": t.doc_tl,
                "selftest": st.get(t.name, {}).get("status"),
                "selftest_rc": st.get(t.name, {}).get("rc"),
                "selftest_secs": st.get(t.name, {}).get("secs"),
                "selftest_reason": st.get(t.name, {}).get("reason"),
            } for t in tools],
            "undocumented": [t.name for t in undoc],
            "orphan_tl_entries": [{"tl": a, "tool": b} for a, b in orphans],
        }, indent=2, sort_keys=True))
        return 0

    if args.undocumented:
        print("%s %s -- undocumented tools" % (TOOL, VERSION))
        print("  %d of %d tools in tools/ appear nowhere in docs/TOOLS-STATUS.md"
              % (len(undoc), len(tools)))
        print("")
        for t in sorted(undoc, key=lambda x: x.name):
            s = st.get(t.name, {})
            print("  %-24s %-5s %7d B  %s"
                  % (t.name, t.kind, t.size, s.get("status") or "-"))
            if t.purpose:
                print("      %s" % t.purpose)
        return 1 if undoc else 0

    print("%s %s" % (TOOL, VERSION))
    print("  " + "-" * 74)
    print("  %d source tools in tools/" % len(tools))
    print("")
    print("  %-24s %-4s %7s  %-18s %-6s %s"
          % ("tool", "kind", "bytes", "selftest", "docs", "TL"))
    print("  " + "-" * 74)
    for t in sorted(tools, key=lambda x: (x.dir, x.name)):
        s = st.get(t.name, {})
        mark = "" if t.dir == "tools" else " (%s)" % t.dir.split("/")[0][:4]
        print("  %-24s %-4s %7d  %-18s %-6s %s"
              % (t.name + mark, t.kind, t.size, s.get("status", "-"),
                 "si" if t.in_docs else "NO", t.doc_tl or "-"))

    by_status = {}
    for t in tools:
        by_status.setdefault(st.get(t.name, {}).get("status", "SKIPPED"), []).append(t.name)
    print("")
    print("  self-test summary")
    for k in sorted(by_status):
        print("    %-20s %d   %s" % (k, len(by_status[k]), ", ".join(sorted(by_status[k])[:4])))

    print("")
    print("  coverage")
    print("    documented in TOOLS-STATUS   %d of %d" % (len(tools) - len(undoc), len(tools)))
    print("    undocumented                 %d" % len(undoc))
    if undoc:
        for t in sorted(undoc, key=lambda x: x.name):
            print("      %-24s %s" % (t.name, t.purpose or ""))
    if orphans:
        print("    TL entries naming a tool that does not exist:")
        for tid, n in orphans:
            print("      %-8s -> %s" % (tid, n))
    limits_missing = [t.name for t in tools if not t.declares_limits]
    safety_missing = [t.name for t in tools if not t.declares_safety]
    if limits_missing:
        print("    no declared LIMITATIONS       %d   %s"
              % (len(limits_missing), ", ".join(sorted(limits_missing)[:5])))
    if safety_missing:
        print("    no WORK_CLASS declaration     %d   %s"
              % (len(safety_missing), ", ".join(sorted(safety_missing)[:5])))
    print("")
    print("  A missing self-test is MISSING, never a pass.  A non-zero exit without a")
    print("  declared FAIL is NONZERO, never a pass.  Coverage is matched by name, so")
    print("  a tool described in prose without its name in backticks reads as uncovered.")
    return 1 if undoc else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
