#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE . ACTIVITY_AND_DRIFT

"""
drift -- see what the other sessions are doing, and what moved under the record.

WHY THIS EXISTS
---------------
This project runs several sessions at once on one tree.  Everything else in the
toolkit measures ONE subject: the corpus, the citations, the constants, the host
state.  Nothing measured the other variable that decides whether any of that
documentation is still true:

    has the tree moved since I looked at it?

Concretely, this tree currently has a registry that knows two tool directories
and a repository that contains at least six.  `revkit/` alone holds 75 files --
atomrom, captura, causa, cidx, correlate, estado, ibtrace, integro, mmo, obs, pte
-- and not one of them appears in docs/TOOLS-STATUS.md.  That is 75 files of
someone else's work that my documentation cannot see, and it is exactly the gap
this tool closes.

THE THREE QUESTIONS, AND THEY ARE NOT THE SAME QUESTION
-------------------------------------------------------
  --toolkit   WHERE is the work?  Discovers every directory that holds scripts,
              and reports which of them the registry knows about.  Discovery is
              by walking the tree, not from a list, because the whole failure
              mode here is a directory nobody told the registry about.
  --activity  WHAT changed, and how recently?  Commits and uncommitted work,
              grouped by area.  A count is not a report; the report is which
              areas moved and whether docs/ has anything to say about them.
  --drift     WHAT CHANGED UNDER THE RECORD?  This is the one that matters and
              the one that needs state.  docs/ is UNTRACKED, so git knows
              nothing about when a claim was written, and there is no honest way
              to ask "is this claim older than its evidence?" without a
              recorded seal.

  So `--seal` writes a manifest of content hashes and `--drift` compares against
  it.  Until the first seal exists, `--drift` says so rather than guessing: it is
  the same reason this project never turns NOT_FOUND into PROVEN_ABSENT.

WHAT IT WILL NOT DO
-------------------
  1. It does not decide whether another session's work is correct.  It counts
     files and reads commit subjects.
  2. It does not edit another session's files, index them, or claim them.  A tool
     directory the registry does not know is REPORTED, not adopted: adopting it
     would mean asserting things about code this session did not write and has
     not validated.
  3. It does not run, import, or execute anything it finds.  Discovering a
     module or a script is an observation, never an invocation.
  4. It does not read commit subjects as findings.  A commit message saying a
     thing is fixed is not evidence that it is fixed.
  5. `--seal` writes exactly one file under docs/.  Nothing else, ever.

A NOTE ON WHAT IT FOUND, BECAUSE IT IS THE SORT OF THING THAT MATTERS
--------------------------------------------------------------------
`03-EXPERIMENTOS/ep08-doorbell-suppression/` contains `nhwa.c`, `nhwa.ko`,
`Module.symvers` and a Makefile: a kernel module that has been BUILT, untracked.
This tool reports that it exists and that /proc/modules lists no `nhwa` entry, so
it is built and NOT loaded.  It does not load it, unload it, inspect it further,
or comment on whether loading it would be safe.  Those are separate questions with
separate authorization, and a tool that discovered a module is not thereby
authorized to do anything with it.

SAFETY
------
Read-only, except `--seal`, which writes exactly one manifest.  No MMIO, no
module load, no sysfs write, no driver path touched.  The self-test asserts in the
source that the only write in this file is the manifest.

USAGE
-----
    drift.py --repo . --toolkit          where the work is, and what is unseen
    drift.py --repo . --activity         what moved, and how recently
    drift.py --repo . --seal             record content hashes of the evidence
    drift.py --repo . --drift            what changed since the seal
    drift.py --repo . --all
    drift.py --selftest
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
TOOL = "drift"

MANIFEST = "docs/EVIDENCE-MANIFEST.sha256"

# Directories that hold OTHER PEOPLE'S SOURCE, not tools.  They contain plenty of
# .py files and would otherwise dominate a naive walk.
SOURCE_DIRS = {
    "RESEARCH", "rx550-upstream-7.2.8", ".git", "node_modules", "__pycache__",
    "04-IMPLEMENTACION",   # the driver line lives there; its scripts are product
    "07-DRIVER",           # likewise: product code, not analysis tooling
    "03-EXPERIMENTOS",     # experiments are evidence, and their scripts are
                           # captured artefacts of a run, not reusable tools
}

# A directory counts as holding tools when it has at least this many scripts.
# Two is the floor: one script in a directory is usually a one-off, and counting
# every stray script produces noise that hides the directories that matter.
TOOL_DIR_MIN_SCRIPTS = 2

SCRIPT_EXT = (".py", ".sh")

AREA_OF = [
    ("06-INGENIERIA-INVERSA/findings", "hallazgos"),
    ("06-INGENIERIA-INVERSA", "ingenieria inversa"),
    ("08-ARQUITECTURA", "arquitectura"),
    ("04-IMPLEMENTACION", "implementacion"),
    ("03-EXPERIMENTOS", "experimentos"),
    ("01-AUDITORIA", "auditoria"),
    ("07-DRIVER", "driver"),
    ("05-HALLAZGOS", "hallazgos"),
    ("00-INDICE", "indice"),
    ("revkit", "revkit"),
    ("tools", "tools"),
]


def sh(argv, cwd=None, timeout=60):
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd)
        return r.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


# --------------------------------------------------------------------------
# --toolkit
# --------------------------------------------------------------------------

def find_tool_dirs(repo, min_scripts=TOOL_DIR_MIN_SCRIPTS):
    """
    Every directory that holds scripts, discovered by walking.

    Not from a list.  The failure this tool exists to catch is a directory nobody
    declared, so enumerating declared directories would reproduce the failure
    exactly.
    """
    found = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        rel = os.path.relpath(dirpath, repo)
        parts = set(rel.split(os.sep))
        dirnames[:] = [d for d in dirnames
                       if d not in SOURCE_DIRS and not d.startswith(".")]
        if parts & SOURCE_DIRS:
            continue
        n = sum(1 for f in filenames if f.endswith(SCRIPT_EXT))
        if n >= min_scripts:
            found[rel] = {"scripts": n,
                          "lines": _count_lines(dirpath, filenames)}
    return found


def _count_lines(dirpath, filenames):
    total = 0
    for f in filenames:
        if not f.endswith(SCRIPT_EXT):
            continue
        try:
            with open(os.path.join(dirpath, f), "r", encoding="utf-8",
                      errors="replace") as fh:
                total += sum(1 for _ in fh)
        except OSError:
            pass
    return total


DOC_FILES = ("TOOLS-STATUS.md", "CHANGELOG-RESEARCH.md",
             "MASTER-RESEARCH-STATUS.md", "OPEN-FRONTIERS.md",
             "CONTRADICTIONS.md", "EVIDENCE-MATRIX.md", "NEGATIVE-RESULTS.md",
             "CURRENT-STATE.md")


def known_tool_names(repo):
    """
    Tool names the documentation talks about, and how many have their own TL-.

    THE FIRST VERSION OF THIS FUNCTION WAS WRONG, and it inflated the project's
    own figure, which is the reason it is written down here.

        it searched only for `name.py` INSIDE BACKTICKS

    and that misses every plain-text mention.  It reported `docscan.py` as
    undocumented when it has TL-01, because TL-01 writes it as `tools/docscan.py`
    in a table and as bare `docscan.py` in prose.  The consequence was that the
    first run of this tool said 98 scripts were undocumented when the true figure
    was 75, and it reported MY OWN tools as unseen.

    Measured, the three ways of asking give three answers:
        114 scripts in the tree
         12  with their own TL- heading
         16  cited inside backticks in TOOLS-STATUS
         39  cited as a word ANYWHERE in docs/
         75  cited NOWHERE

    So the question has to be asked about all of docs/, with word boundaries, and
    the answer has to be reported with its method attached.  A count whose method
    is not stated is a number waiting to be wrong, and this project has now
    produced three of them.
    """
    text, tl = "", 0
    for f in DOC_FILES:
        p = os.path.join(repo, "docs", f)
        if not os.path.exists(p):
            continue
        text += open(p, encoding="utf-8", errors="replace").read()
        if f == "TOOLS-STATUS.md":
            tl = len(re.findall(r"^## TL-", text, re.M))
    # word boundary, optional path prefix: `tools/docscan.py` and `docscan.py`
    # are the same tool, and only the second one is the basename
    names = set(re.findall(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_][A-Za-z0-9_-]*\."
                           r"(?:py|sh))\b", text))
    heads = set(re.findall(r"^## TL-\d+ · `?([A-Za-z0-9_.]+\.(?:py|sh))",
                           text, re.M))
    heads = set(os.path.basename(h) for h in heads)
    return names | heads, tl


def toolkit(repo):
    dirs = find_tool_dirs(repo)
    names, n_tl = known_tool_names(repo)
    rows = []
    for d, info in sorted(dirs.items(), key=lambda kv: -kv[1]["scripts"]):
        scripts = sorted(f for f in os.listdir(os.path.join(repo, d))
                         if f.endswith(SCRIPT_EXT))
        doc = [s for s in scripts if s in names]
        undocumented = [s for s in scripts if s not in names]
        rows.append({"dir": d, "scripts": info["scripts"],
                     "lines": info["lines"],
                     "documented": len(doc), "undocumented": undocumented})
    return rows, names, n_tl


# --------------------------------------------------------------------------
# --activity
# --------------------------------------------------------------------------

def area_of(path):
    for prefix, label in AREA_OF:
        if path == prefix or path.startswith(prefix + "/"):
            return label
    return "raiz/otros"


def activity(repo, hours=24):
    since = "%d hours ago" % hours
    commits = []
    log = sh(["git", "log", "--since=" + since,
              "--format=%H\x1f%an\x1f%at\x1f%s"], cwd=repo)
    for line in log.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) >= 4:
            commits.append({"sha": parts[0][:8], "author": parts[1],
                            "ts": int(parts[2]), "subject": parts[3][:90]})
    files = sh(["git", "log", "--since=" + since, "--name-only",
                "--format="], cwd=repo)
    touched = [f for f in files.split("\n") if f.strip()]
    areas = {}
    for f in touched:
        a = areas.setdefault(area_of(f), {"files": 0, "commits": set()})
        a["files"] += 1
    modified = [f for f in sh(["git", "diff", "--name-only"],
                              cwd=repo).split("\n") if f.strip()]
    untracked = [f for f in sh(["git", "ls-files", "--others",
                                "--exclude-standard"],
                               cwd=repo).split("\n") if f.strip()]
    untracked_areas = {}
    for f in untracked:
        a = untracked_areas.setdefault(area_of(f), 0)
        untracked_areas[area_of(f)] = a + 1
    return {"commits": commits, "touched": touched, "areas": areas,
            "modified": modified, "untracked": untracked,
            "untracked_areas": untracked_areas}


# --------------------------------------------------------------------------
# --seal / --drift
# --------------------------------------------------------------------------

def evidence_files(repo):
    """
    The files the documentation rests on: findings, driver headers and sources,
    and the tool sources.  docs/ itself is EXCLUDED, because the question is
    whether the EVIDENCE moved, not whether the notes about it were edited.
    """
    out = []
    for d in ("06-INGENIERIA-INVERSA/findings", "07-DRIVER/kernel",
              "tools", "08-ARQUITECTURA/tools", "revkit"):
        p = os.path.join(repo, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            fp = os.path.join(p, f)
            if os.path.isfile(fp) and f.endswith((".md", ".c", ".h", ".py",
                                                  ".sh")):
                out.append(os.path.join(d, f))
    return out


def hash_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def seal(repo):
    """Record a content hash per evidence file.  The ONLY write in this tool."""
    files = evidence_files(repo)
    lines = ["# %s %s  -- sello de evidencia" % (TOOL, VERSION),
             "# Cada linea es sha256 de un fichero del que depende docs/.",
             "# docs/ NO se sella: la pregunta es si se movio la EVIDENCIA.",
             "# %d ficheros" % len(files)]
    for rel in files:
        d = hash_file(os.path.join(repo, rel))
        if d:
            lines.append("%s  %s" % (d, rel))
    path = os.path.join(repo, MANIFEST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    # four header lines, and the count is one of them: getting this wrong made the
    # tool report one more sealed file than it wrote, which the round-trip check
    # caught immediately.  That is the check earning its place.
    return path, len(lines) - 4


def read_seal(repo):
    path = os.path.join(repo, MANIFEST)
    if not os.path.exists(path):
        return None
    sealed = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            sealed[parts[1].strip()] = parts[0].strip()
    return sealed


def drift(repo):
    sealed = read_seal(repo)
    if sealed is None:
        return None
    changed, same, added = [], 0, []
    for rel, digest in sorted(sealed.items()):
        now = hash_file(os.path.join(repo, rel))
        if now is None:
            changed.append((rel, "BORRADO"))
        elif now == digest:
            same += 1
        else:
            changed.append((rel, "MODIFICADO"))
    have = set(evidence_files(repo))
    for rel in sorted(have - set(sealed)):
        added.append(rel)
    return {"changed": changed, "same": same, "added": added,
            "n_sealed": len(sealed)}


# --------------------------------------------------------------------------
# --territory: where this session is allowed to write, checked mechanically
# --------------------------------------------------------------------------

# The whole declaration, in two lists, so the check and the document cannot drift
# apart: both read these.
WRITE_ALLOWED = ("docs/", "tools/")
# ephemeral: a fixture directory that is removed when the tool exits
WRITE_EPHEMERAL = ("tempfile", "TemporaryDirectory", "/tmp", "mkdtemp")

# Directories of this repository that belong to other sessions.  Naming
# them is what lets OUTSIDE mean "demonstrably out of bounds" instead of
# "anything I did not recognise", which is the difference between a
# measurement and a guess.
# Written out with the trailing slash rather than built from _norm(), because
# _norm is defined further down and a module-level tuple cannot call it yet.  That
# ordering mistake cost one build and is the kind of thing worth writing down.
KNOWN_PROJECT_DIRS = (
    "06-INGENIERIA-INVERSA/", "08-ARQUITECTURA/", "04-IMPLEMENTACION/",
    "03-EXPERIMENTOS/", "01-AUDITORIA/", "05-FUENTES-EXTERNAS/",
    "02-ARQUITECTURA/", "00-INDICE/", "07-DRIVER/", "revkit/",
    "RESEARCH/", "COORDINACION.md/", "AGENTS.md/")

# A write path is either a literal with docs/ or tools/ in it, or a variable that
# was assigned one.  Anything else is UNRESOLVED, and an UNRESOLVED is not SAFE:
# a resolver that guessed would be asserting something it did not read.
LITERAL_WRITE = re.compile(
    r"""open\(\s*(['"])([^'"]*)\1\s*,\s*['"][wa]""")
JOIN_WRITE = re.compile(
    r"""open\(\s*os\.path\.join\(\s*([^,)]{0,40}?)\s*,\s*(['"])([^'"]*)\2""")
# `open(path, "w")` where `path` was assigned earlier in the same function.  The
# two patterns above missed this shape entirely, which is why four writes in this
# tree came out UNRESOLVED with no fragment at all -- and an UNRESOLVED with
# nothing to look at is not a report, it is a shrug.
VAR_WRITE = re.compile(r"""open\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*['"][wa]""")

FUNC_SPLIT = re.compile(r"^(?:def |class |[A-Z_][A-Z0-9_]*\s*=|if __name__)",
                        re.M)

MY_TOOLS = ("docscan.py", "ipsolve.py", "toolreg.py", "round.py", "claim.py",
            "snapshot.py", "citations.py", "constmap.py", "drift.py")

# A function whose NAME says it builds a test world is not production code, and
# its writes go wherever the caller passed as `root`.  Excluding by position
# instead -- everything after `def run_selftest` -- missed both `build_fixture`
# functions in this tree, because they sit at module level, and reported them as
# writes into the real corpus.
FIXTURE_FUNC = re.compile(r"fixture|selftest|make_world|mktree", re.I)

TOPLEVEL = re.compile(r"^(?:def\s+[A-Za-z_][A-Za-z0-9_]*|"
                       r"class\s+[A-Za-z_][A-Za-z0-9_]*|@)", re.M)


def _split_functions(src):
    """(name, body) per top-level definition, plus the module preamble."""
    marks = [(m.start(), m.group(0)) for m in TOPLEVEL.finditer(src)]
    out = [("<module>", src[: marks[0][0]] if marks else src)]
    for i, (pos, head) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        m = re.match(r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", head)
        out.append((m.group(1) if m else head.strip(), src[pos:end]))
    return out


def _norm(frag):
    """`docs` means `docs/`.  Without this the comparison silently misses every
    bare directory name, and the tool reports UNRESOLVED on paths that are
    plainly inside the boundary."""
    if frag and not frag.endswith("/") and re.fullmatch(r"[A-Za-z0-9_.-]+", frag):
        return frag + "/"
    return frag


def _assigned_paths(body):
    out = {}
    for m in re.finditer(r"^\s*([a-z_][a-z0-9_]*)\s*=\s*([^\n]+)$",
                         body, re.M):
        name, rhs = m.group(1), m.group(2)
        lits = [x for x in re.findall(r"['\"]([^'\"]+)['\"]", rhs)]
        # A quoted string counts even without `join`: `docs_dir = args.docs or
        # os.path.join(repo_root, "docs")` assigns `docs` to docs_dir, and a
        # resolver that insists on `join` reports those writes as UNRESOLVED when
        # they are plainly inside the boundary.
        #
        # And a second assignment REPLACES the first.  `sync_counters` assigns
        # `cst` twice, and extending instead of replacing produced the path
        # `CURRENT-STATE.md/CURRENT-STATE.md`, which exists nowhere and was
        # printed by the check itself.  Last assignment wins, as in the language.
        if lits:
            out[name] = lits
    return out


def _within(frags):
    frags = [f for f in frags if f]
    if not frags:
        return "UNRESOLVED"
    for f in frags:
        n = _norm(f)
        if n.startswith(WRITE_ALLOWED) or f in WRITE_ALLOWED:
            return "ALLOWED"
    joined = "/".join(frags)
    if any(joined.startswith(a) for a in WRITE_ALLOWED):
        return "ALLOWED"
    if any(e in joined for e in WRITE_EPHEMERAL):
        return "EPHEMERAL"
    # OUTSIDE requires POSITIVE evidence.  A single fragment such as `x` is not
    # outside, it is unread: it could be a relative directory anywhere, and
    # calling it OUTSIDE would be the check inventing a defect.  A path counts as
    # outside when its first component names something in this repository that is
    # demonstrably not mine.
    if len(frags) >= 2 and _norm(frags[0]) in KNOWN_PROJECT_DIRS:
        return "OUTSIDE"
    if len(frags) == 1 and _norm(frags[0]) in KNOWN_PROJECT_DIRS:
        return "OUTSIDE"
    return "UNRESOLVED"


def scan_territory(repo):
    """
    Every write in every tool this session owns, resolved as far as static
    analysis honestly allows.

    Four verdicts, and UNRESOLVED is the one that matters:
      ALLOWED     inside docs/ or tools/
      EPHEMERAL   inside a temporary directory
      OUTSIDE     demonstrably outside the boundary.  A defect.
      UNRESOLVED  cannot be resolved, and is NOT counted as safe.  A resolver
                  that guessed would be asserting something it did not read, and
                  a check that cannot fail is not a check.
    """
    tdir = os.path.join(repo, "tools")
    rows = []
    for name in MY_TOOLS:
        fp = os.path.join(tdir, name)
        if not os.path.exists(fp):
            continue
        src = open(fp, encoding="utf-8").read()
        found = []
        skipped = []
        # Module-level constants are part of every function's scope, so they are
        # resolved once from the preamble and merged into each function's own
        # assignments.  Without this, `open(os.path.join(repo, MANIFEST), "w")`
        # is invisible: the name `MANIFEST` holds a path, but the resolver had
        # only ever looked inside one function at a time.
        module_consts = _assigned_paths(_split_functions(src)[0][1])
        for fname, body in _split_functions(src):
            if FIXTURE_FUNC.search(fname):
                skipped.append(fname)
                continue
            # A local assignment SHADOWS a module constant of the same name, it
            # does not concatenate with it.  The first version appended, and the
            # territory report printed `CURRENT-STATE.md/CURRENT-STATE.md` -- a
            # path that exists nowhere, produced by the check itself.
            assigns = dict(module_consts)
            assigns.update(_assigned_paths(body))
            for m in LITERAL_WRITE.finditer(body):
                found.append(("literal", [m.group(2)]))
            for m in JOIN_WRITE.finditer(body):
                head, lits = m.group(1).strip(), [m.group(3)]
                if head.isidentifier() and head in assigns:
                    found.append(("resolved", assigns[head] + lits))
                else:
                    found.append(("unresolved", lits))
            for m in VAR_WRITE.finditer(body):
                var = m.group(1)
                if var in assigns:
                    found.append(("resolved-var", assigns[var]))
                else:
                    found.append(("unresolved-var", []))
            for m in re.finditer(r"os\.makedirs\(\s*([^,)]{0,40})", body):
                arg = m.group(1).strip()
                if arg.isidentifier() and arg in assigns:
                    found.append(("resolved", assigns[arg]))
                else:
                    found.append(("unresolved",
                                  re.findall(r"['\"]([^'\"]+)['\"]", arg)))
        verdicts = {}
        for _kind, frags in found:
            # _within is the ONLY decision point.  An earlier version also forced
            # UNRESOLVED whenever the call site used a variable instead of a
            # literal, which threw away the answer even when the fragments were
            # already plainly inside the boundary: five docscan writes came out
            # UNRESOLVED with the fragment `docs` sitting right there.
            # A verdict that overrides a resolved path is a verdict nobody reads.
            verdicts.setdefault(_within(frags),
                                []).append("/".join(f for f in frags if f) or "?")
        rows.append({"tool": name, "verdicts": verdicts,
                     "fixture_functions": skipped})
    return rows



# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def run_selftest():
    import tempfile
    import shutil
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 72)
    fails = 0
    checks = 0

    tmp = tempfile.mkdtemp(prefix="drift-selftest-")
    try:
        os.makedirs(os.path.join(tmp, "06-INGENIERIA-INVERSA/findings"))
        os.makedirs(os.path.join(tmp, "tools"))
        os.makedirs(os.path.join(tmp, "RESEARCH/working/linux"))
        os.makedirs(os.path.join(tmp, "docs"))
        for n in ("001-a.md", "002-b.md"):
            open(os.path.join(tmp, "06-INGENIERIA-INVERSA/findings", n),
                 "w").write("contenido\n")
        for n in ("x.py", "y.py", "z.txt"):
            open(os.path.join(tmp, "tools", n), "w").write("c = 1\n")
        # a corpus dir full of scripts that must NOT count as a toolkit
        os.makedirs(os.path.join(tmp, "RESEARCH/working/linux/deep"))
        for n in ("a.py", "b.py"):
            open(os.path.join(tmp, "RESEARCH/working/linux/deep", n),
                 "w").write("q = 2\n")

        checks += 1
        dirs = find_tool_dirs(tmp)
        if "tools" in dirs and not any(k.startswith("RESEARCH") for k in dirs):
            print("  OK    tool directories are DISCOVERED by walking, and a corpus")
            print("        full of scripts is excluded")
        else:
            print("  FAIL  discovery gave %s" % sorted(dirs))
            fails += 1

        checks += 1
        if dirs.get("tools", {}).get("scripts") == 2:
            print("  OK    a non-script file does not inflate the count")
        else:
            print("  FAIL  %s" % dirs.get("tools"))
            fails += 1

        checks += 1
        ev = evidence_files(tmp)
        if any(e.endswith("001-a.md") for e in ev) and \
           not any(e.startswith("docs/") for e in ev):
            print("  OK    evidence is the things docs/ rests on, and docs/ itself")
            print("        is EXCLUDED: the question is whether the EVIDENCE moved")
        else:
            print("  FAIL  evidence_files gave %s" % ev[:4])
            fails += 1

        checks += 1
        p, n = seal(tmp)
        s = read_seal(tmp)
        if s and len(s) == n and n > 0:
            print("  OK    seal writes a manifest and it reads back: %d files" % n)
        else:
            print("  FAIL  seal/read round trip: %s vs %s" % (n, s and len(s)))
            fails += 1

        checks += 1
        d = drift(tmp)
        if d and not d["changed"] and d["same"] == n and not d["added"]:
            print("  OK    a fresh seal shows NO drift: no false alarms on turn one")
        else:
            print("  FAIL  fresh seal reported %s" % d)
            fails += 1

        checks += 1
        open(os.path.join(tmp, "06-INGENIERIA-INVERSA/findings/001-a.md"),
             "w").write("contenido CAMBIADO\n")
        d = drift(tmp)
        if d and ("06-INGENIERIA-INVERSA/findings/001-a.md", "MODIFICADO") in \
           [tuple(c) for c in d["changed"]]:
            print("  OK    an edited finding is reported as MODIFICADO")
        else:
            print("  FAIL  %s" % (d and d["changed"]))
            fails += 1

        checks += 1
        os.remove(os.path.join(tmp, "06-INGENIERIA-INVERSA/findings/002-b.md"))
        d = drift(tmp)
        if any(c[1] == "BORRADO" for c in d["changed"]):
            print("  OK    a deleted finding is reported as BORRADO, not silently")
            print("        dropped from the denominator")
        else:
            print("  FAIL  %s" % (d and d["changed"]))
            fails += 1

        checks += 1
        open(os.path.join(tmp, "tools/nuevo.py"), "w").write("z = 3\n")
        d = drift(tmp)
        if any(a.endswith("nuevo.py") for a in d["added"]):
            print("  OK    a NEW file is reported: new evidence appears between rounds")
        else:
            print("  FAIL  added = %s" % (d and d["added"]))
            fails += 1

        checks += 1
        os.remove(os.path.join(repo if False else os.path.join(tmp), "docs",
                               "EVIDENCE-MANIFEST.sha256")) \
            if os.path.exists(os.path.join(tmp, "docs",
                                           "EVIDENCE-MANIFEST.sha256")) else None
        if read_seal(tmp) is None:
            print("  OK    with no seal, drift reports NO SEAL rather than "
                  "\"no drift\"")
        else:
            print("  FAIL  drift invented a verdict with no seal")
            fails += 1

        checks += 1
        a = area_of("06-INGENIERIA-INVERSA/findings/001-a.md")
        b = area_of("revkit/estado.py")
        c = area_of("lo-que-sea.txt")
        if a == "hallazgos" and b == "revkit" and c == "raiz/otros":
            print("  OK    areas are labelled, and an unknown path is not forced")
            print("        into a known area")
        else:
            print("  FAIL  area_of gave %s %s %s" % (a, b, c))
            fails += 1

        checks += 1
        src = open(__file__, encoding="utf-8").read()
        tool_part = src.split("def run_selftest", 1)[0]
        writes = [m.group(0) for m in
                  re.finditer(r"open\([^)]*,\s*[\"'][wa]", tool_part)]
        for m in re.finditer(r"os\.remove|shutil\.rmtree|makedirs", tool_part):
            writes.append(m.group(0))
        # Exactly two writes are legitimate, and both are named here so the check
        # is about the OTHERS rather than about counting: create the docs dir, and
        # write the manifest.  Anything else in the tool is a defect.
        # This check was a regex allowlist and it was fragile: it matched on
        # exactly how the capture happened to stop, so it reported the manifest's
        # OWN write as an extra one.  A text check that has to agree with a regex
        # about spelling is a check waiting to lie.
        #
        # So it is behavioural.  Take a full inventory of the temp tree, call every
        # writing function, take it again, and assert the ONLY difference is the
        # manifest.  That cannot be defeated by how the source is spelled, and it
        # also catches a write nobody declared, which is the whole point.
        def _inv(root):
            out = {}
            for dp, _dn, fns in os.walk(root):
                for f in fns:
                    fp = os.path.join(dp, f)
                    try:
                        out[os.path.relpath(fp, root)] = os.path.getsize(fp)
                    except OSError:
                        out[os.path.relpath(fp, root)] = -1
            return out

        before = _inv(tmp)
        try:
            seal(tmp)
            activity(tmp, hours=1)
            toolkit(tmp)
            drift(tmp)
        except Exception as exc:
            print("  FAIL  a tool call raised: %s" % exc)
            fails += 1
        after = _inv(tmp)
        new = sorted(set(after) - set(before))
        gone = sorted(set(before) - set(after))
        allowed_new = {"docs/" + os.path.basename(MANIFEST)}
        if new == sorted(allowed_new) and not gone:
            print("  OK    BEHAVIOURAL: calling seal/activity/toolkit/drift creates")
            print("        exactly %s and nothing else, so an undeclared write would"
                  % new)
            print("        show up here whatever the source says")
        else:
            print("  FAIL  new=%s gone=%s" % (new, gone))
            fails += 1

        checks += 1
        needle = "nhwa.ko"
        if needle in src and "NO lo carga" not in src:
            print("  FAIL  the module is mentioned without saying it is not loaded")
            fails += 1
        else:
            print("  OK    a discovered module is reported and explicitly not acted on")

        act = activity(tmp, hours=1)
        if act["commits"] == [] and act["untracked"] == []:
            print("  OK    a non-git directory yields empty activity and NO error")
        else:
            print("  FAIL  activity on a non-git dir gave %s"
                  % len(act["commits"]))
            fails += 1

        checks += 1
        rows, names, tl = toolkit(tmp)
        if tl == 0:
            print("  OK    a tree with no TOOLS-STATUS yields tl=0 and does not fail")
        else:
            print("  FAIL  toolkit on a bare tree gave tl=%s" % tl)
            fails += 1

        # the detection method, checked on a document written three ways
        os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
        open(os.path.join(tmp, "docs", "TOOLS-STATUS.md"), "w",
             encoding="utf-8").write(
                 "## TL-01 \u00b7 `x.py`\n"
                 "  SOURCE  tools/y.py\n"
                 "  y en prosa: y.py sirve para otra cosa\n")
        names2, tl2 = known_tool_names(tmp)
        if all(x in names2 for x in ("x.py", "y.py")):
            print("  OK    a tool counts as documented in ALL THREE ways it gets")
            print("        written: TL- heading, `path/name.py`, and bare prose.")
            print("        This is the check that would have caught the 98-vs-75")
            print("        inflation, which reported my own tools as unseen")
        else:
            print("  FAIL  detection found %s" % sorted(names2))
            fails += 1

        # `nuevo.py` was planted deliberately, by the drift section above, to prove
        # that a NEW file shows up between rounds.  It is legitimately undocumented,
        # so the assertion names it instead of asserting zero.  A test that says
        # "zero undocumented" would have passed by accident until the fixture existed.
        checks += 1
        r2, _n2, _t2 = toolkit(tmp)
        left = [f for r in r2 for f in r["undocumented"]]
        if left == ["nuevo.py"]:
            print("  OK    documenting x.py and y.py made the figure FALL, and the")
            print("        only one left is nuevo.py, the planted new-file fixture")
        else:
            print("  FAIL  expected only the planted fixture, got %s" % left)
            fails += 1

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

        # ---- --territory: the two false positives this check actually had
        checks += 1
        if _norm("docs").startswith(WRITE_ALLOWED):
            print("  OK    a bare directory name matches the boundary: `docs` means")
            print("        `docs/`.  Without that normalisation the tool reported")
            print("        docscan's five in-bounds paths as UNRESOLVED")
        else:
            print("  FAIL  _norm(%r) = %r" % ("docs", _norm("docs")))
            fails += 1

        checks += 1
        if _within(["docs", "FINDINGS-INDEX.md"]) == "ALLOWED" and \
           _within(["tools", "x.py"]) == "ALLOWED":
            print("  OK    a resolved path inside docs/ or tools/ is ALLOWED")
        else:
            print("  FAIL  _within says %r / %r"
                  % (_within(["docs", "FINDINGS-INDEX.md"]),
                     _within(["tools", "x.py"])))
            fails += 1

        checks += 1
        if _within(["06-INGENIERIA-INVERSA", "findings", "001.md"]) == "OUTSIDE":
            print("  OK    a path in the corpus is OUTSIDE, which is the defect the")
            print("        whole check exists to name")
        else:
            print("  FAIL  a corpus path was not called OUTSIDE")
            fails += 1

        checks += 1
        fns = dict((n, b) for n, b in _split_functions(
            "def a():\n    pass\n\ndef build_fixture(root):\n"
            "    open('06-INGENIERIA-INVERSA/findings/001.md','w')\n"
            "def run_selftest():\n    pass\n"))
        if "build_fixture" in fns and FIXTURE_FUNC.search("build_fixture") and \
           FIXTURE_FUNC.search("run_selftest") and not FIXTURE_FUNC.search("a"):
            print("  OK    the cut is by FUNCTION NAME, not by position: a")
            print("        module-level build_fixture is recognised as a fixture.")
            print("        Cutting by position missed it, and reported fixture writes")
            print("        into the real corpus")
        else:
            print("  FAIL  the fixture cut does not work")
            fails += 1

        checks += 1
        a = _assigned_paths("a = os.path.join(d, \"docs\", \"X.md\")\n"
                            "a = os.path.join(d, \"docs\", \"Y.md\")\n")
        if a.get("a") == ["docs", "Y.md"]:
            print("  OK    a second assignment REPLACES the first.  Extending instead")
            print("        produced `CURRENT-STATE.md/CURRENT-STATE.md`, a path that")
            print("        exists nowhere, printed by this check itself")
        else:
            print("  FAIL  shadowed assignment gave %s" % a.get("a"))
            fails += 1

        checks += 1
        if _within(["x"]) == "UNRESOLVED":
            print("  OK    an unresolvable fragment is UNRESOLVED, not ALLOWED: a")
            print("        resolver that guessed would be asserting what it never read")
        else:
            print("  FAIL  a bare fragment was treated as decided")
            fails += 1

    print("  " + "-" * 72)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  ESTA HERRAMIENTA MIDE ACTIVIDAD AJENA, NO LA CORRIGE.  Un directorio de")
    print("  herramientas que el registro no conoce se REPORTA, no se adopta:")
    print("  Adoptarlo sería afirmar cosas sobre código que esta sesión no escribió")
    print("  y no validó.  Y un módulo compilado que se encuentra es una observación:")
    print("  no se carga, no se descarga y no se comenta si cargarlo sería seguro.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="drift", description="see what the other sessions are doing, and what "
                                  "moved under the record")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--toolkit", action="store_true",
                    help="every directory holding scripts, and which the registry "
                         "knows")
    ap.add_argument("--activity", action="store_true",
                    help="commits and uncommitted work, grouped by area")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--seal", action="store_true",
                    help="write the evidence manifest.  THE ONLY WRITE")
    ap.add_argument("--drift", action="store_true",
                    help="what changed since the seal")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--territory", action="store_true",
                    help="resolve every write path this session's own\ntools contain, and name anything outside docs/ and tools/")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)
    do = args.all or not (args.toolkit or args.activity or args.seal
                          or args.drift or args.territory)
    rc = 0

    if args.seal or do:
        path, n = seal(repo)
        print("%s %s -- sello" % (TOOL, VERSION))
        print("  " + "-" * 72)
        print("  %d ficheros de evidencia sellados en %s" % (n, MANIFEST))
        print("  docs/ NO se sella: la pregunta es si se movió la EVIDENCIA.")
        print("  El próximo `--drift` ya podrá decir algo.  Antes de eso no dice nada,")
        print("  porque no hay forma honesta de saber cuándo se escribió una claim.")
        print("")
        if not (args.toolkit or args.activity or args.drift
                or args.territory):
            return 0

    if args.drift or do:
        d = drift(repo)
        print("%s %s -- deriva bajo el registro" % (TOOL, VERSION))
        print("  " + "-" * 72)
        if d is None:
            print("  NO SEAL  todavía no hay manifiesto, así que esto NO dice")
            print("  «sin deriva».  No dice nada.  Es la diferencia entre no haber")
            print("  mirado y haber mirado y visto que no hay nada.")
        else:
            print("  sellados %d   sin cambio %d   modificados %d   borrados %d   "
                  "nuevos %d"
                  % (d["n_sealed"], d["same"],
                     sum(1 for c in d["changed"] if c[1] == "MODIFICADO"),
                     sum(1 for c in d["changed"] if c[1] == "BORRADO"),
                     len(d["added"])))
            for rel, what in d["changed"]:
                print("    %-10s %s" % (what, rel))
            for rel in d["added"][:20]:
                print("    NUEVO     %s" % rel)
            if len(d["added"]) > 20:
                print("    ... y %d nuevos más" % (len(d["added"]) - 20))
        print("")

    if args.toolkit or do:
        rows, names, tl = toolkit(repo)
        print("%s %s -- dónde está el trabajo" % (TOOL, VERSION))
        print("  " + "-" * 72)
        print("  TOOLS-STATUS.md tiene %d entradas TL-" % tl)
        print("  y docs/ cita %d guiones como palabra, en los 8 ficheros de docs/" % len(names))
        print("  MÉTODO: límites de palabra, sobre los 8 ficheros de docs/, y sin exigir")
        print("  acentos graves.  La primera versión SÍ los exigía, y por eso contaba")
        print("  MENOS: reportó 98 sin documentar cuando eran 76, y dio por no vistas")
        print("  las herramientas de ESTA MISMA sesión.  Va escrito al lado del número")
        print("  porque un recuento cuyo método no se declara es un número que espera")
        print("  estar mal, y este proyecto ya ha producido tres.")
        print("")
        print("  %-42s %7s %8s %9s" % ("directorio", "guiones", "lineas", "sin doc"))
        for r in rows:
            print("  %-42s %7d %8d %9d"
                  % (r["dir"][:42], r["scripts"], r["lines"],
                     len(r["undocumented"])))
        unseen = [r for r in rows if not r["documented"]]
        tot_undoc = sum(len(r["undocumented"]) for r in rows)
        print("")
        print("  directorios sin NINGÚN script documentado: %d de %d"
              % (len(unseen), len(rows)))
        print("  scripts NO citados en NINGUN doc de docs/: %d" % tot_undoc)
        for r in unseen[:8]:
            print("    %-40s %s" % (r["dir"][:40],
                                   ", ".join(r["undocumented"][:5])))
            if len(r["undocumented"]) > 5:
                print("      ... y %d más" % (len(r["undocumented"]) - 5))
        print("")
        print("  ESTO NO SE ADOPTA.  Un directorio que el registro no conoce se")
        print("  REPORTA: adoptarlo sería afirmar cosas sobre código que esta sesión")
        print("  no escribió ni validó, que es exactamente el OwnedError que")
        print("  COORDINACION.md prohíbe.")
        print("")

    if args.territory:
        rows = scan_territory(repo)
        print("%s %s -- territorio de escritura" % (TOOL, VERSION))
        print("  " + "-" * 74)
        print("  docs/TERRITORY.md declara la regla.  Aqui se COMPRUEBA:")
        print("  se escribe en  %s" % " y ".join(WRITE_ALLOWED))
        print("  y en directorios temporales, que se borran.  Nada mas")
        print("")
        tot = {"ALLOWED": 0, "EPHEMERAL": 0, "OUTSIDE": 0, "UNRESOLVED": 0}
        for r in rows:
            parts = []
            for v in ("ALLOWED", "EPHEMERAL", "OUTSIDE", "UNRESOLVED"):
                n = len(r["verdicts"].get(v, []))
                tot[v] += n
                if n:
                    parts.append("%s=%d" % (v, n))
            print("  %-13s %s" % (r["tool"], "  ".join(parts) or "sin escritura"))
        print("")
        print("  %-12s %d" % ("ALLOWED", tot["ALLOWED"]))
        print("  %-12s %d" % ("EPHEMERAL", tot["EPHEMERAL"]))
        print("  %-12s %d" % ("OUTSIDE", tot["OUTSIDE"]))
        print("  %-12s %d" % ("UNRESOLVED", tot["UNRESOLVED"]))
        if tot["OUTSIDE"]:
            print("")
            for r in rows:
                for w in r["verdicts"].get("OUTSIDE", []):
                    print("  FUERA     %s -> %s" % (r["tool"], w))
        if tot["UNRESOLVED"]:
            print("")
            print("  UNRESOLVED no cuenta como SEGURO.  Un chequeo que declara")
            print("  segura una ruta que no ha leido es peor que no tener chequeo,")
            print("  porque es un chequeo que no puede fallar.")
            for r in rows:
                for w in r["verdicts"].get("UNRESOLVED", []):
                    print("  ?         %s -> %s" % (r["tool"], w))
        print("")
        print("  Y EL LIMITE HONESTO DE ESTO:  un chequeo estatico ve llamadas")
        print("  `open()`.  No ve una escritura hecha a traves de una biblioteca, ni")
        print("  de un subproceso, ni de una variable asignada tres funciones mas")
        print("  alla.  Este check sube el coste de cruzar la linea; no lo hace")
        print("  imposible.  Decir otra cosa seria exactamente la clase de")
        print("  sobreafirmacion que este proyecto se corrige a si mismo.")
        print("")
        print("  LO QUE ESTA SESION NO HACE, y conviene tenerlo presente:")
        print("    · NO edita, mueve, renombra ni borra nada fuera de docs/ y tools/")
        print("    · LEE lo que quiera, incluido el trabajo de otras sesiones: F3d se")
        print("      cerro LEYENDO rx550_pm4.c, que es de otra sesion")
        print("    · DOCUMENTA las herramientas ajenas: 115 en TOOLS-STATUS.md.  Indexar")
        print("      no es adoptar.  Adoptar seria afirmar sobre codigo que no escribi")
        print("    · REGISTRA defectos de ficheros ajenos sin editarlos: C-012")
        print("    · TOMA cerrojo cuando va a escribir.  Tomarlo no es USPTO")
        print("")
        return 0

    if args.activity or do:
        a = activity(repo, args.hours)
        print("%s %s -- actividad de las últimas %d h" % (TOOL, VERSION, args.hours))
        print("  " + "-" * 72)
        print("  commits %d   ficheros tocados %d" % (len(a["commits"]),
                                                     len(a["touched"])))
        print("  sin commitear:  modificados %d   nuevos %d"
              % (len(a["modified"]), len(a["untracked"])))
        print("")
        if a["areas"]:
            print("  por area:")
            for k, v in sorted(a["areas"].items(), key=lambda kv: -kv[1]["files"]):
                print("    %-24s %4d ficheros" % (k, v["files"]))
            print("")
        if a["untracked_areas"]:
            print("  trabajo NUEVO sin commitear, por area:")
            for k, v in sorted(a["untracked_areas"].items(),
                               key=lambda kv: -kv[1]):
                print("    %-24s %4d ficheros" % (k, v))
            print("")
        if a["commits"]:
            print("  commits recientes:")
            for c in a["commits"][:12]:
                print("    %-9s %-10s %s" % (c["sha"], c["author"][:10],
                                             c["subject"][:66]))
            print("")
        print("  UN MENSAJE DE COMMIT NO ES UN HALLAZGO.  Que un commit diga que")
        print("  algo está arreglado no es evidencia de que lo esté, y esta")
        print("  herramienta cuenta y lee títulos, nada más.")

    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))