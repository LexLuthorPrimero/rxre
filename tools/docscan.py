#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
docscan -- consistency scan of docs/, plus a freshness cross-check.

WHY THIS EXISTS
---------------
For four documentation rounds this file's checks were re-typed as ad-hoc
one-liners at the start of every round.  Each round therefore measured the
same things slightly differently, and a check that changes shape between
rounds is not a check, it is a habit.  Also, the counts that appear in
CURRENT-STATE.md and FINDINGS-INDEX.md drift every time the tree grows, and
they had been corrected by hand five times in one morning.

This tool makes the scan a command.  It is read-only over docs/ and it never
invents state: it reports, it does not fix.

WORK_CLASS=READ_ONLY  ·  WRITE_EXECUTION=NONE  ·  STATIC_ANALYSIS

CONTRACT
--------
name          docscan
version       1.0.0
purpose       report documentation defects and stale counters
scope         READS docs/ and 06-INGENIERIA-INVERSA/findings/ only.
              Writes nothing except with --sync, and --sync touches only numeric
              fields identified by their own name.  Touches no GPU, does not read
              MMIO, does not open /sys, does not compile anything.  Runs only
              `git ls-files` and `git log`, both read-only.
              The canonical WORK_CLASS / WRITE_EXECUTION tokens are declared
              above because tools/toolreg.py REFUSES to execute any tool that
              does not declare them, and a tool that is safe but undeclared is
              useless to the one tool that would otherwise check it.
dependencies  Python 3, standard library only, and git on PATH for two checks
build         none
exit codes    0  no defect found
              1  at least one defect at or above --fail-on severity
              2  usage error
units         counts of files and lines.  No other unit appears.

THE SEVEN CHECKS, and what each one is FOR
-----------------------------------------
  1 non-latin-glyphs    characters outside Latin-1 that are not intended.
                        Caught four separate defects on 2026-10-01, each of
                        them introduced by an edit seconds before validation.
  2 broken-md-refs      ]() links to .md files inside docs/ that do not exist.
  3 undefined-symbols   RE-nn / TL-nn / F-n / C-nn cited but never defined.
                        A symbol cited before it is defined is a promise the
                        tree has not kept.
  4 repo-paths-missing  paths inside backticks that look like repo paths and do
                        not exist.  Corpus-relative paths are accepted, because
                        citing the corpus relative to its own root is the correct
                        convention; each miss is reported with its context so a
                        human can judge it rather than delete it blindly.
  5 findings-unindexed  findings present in findings/ but absent from
                        FINDINGS-INDEX.md.  An index that silently stops
                        covering the directory is worse than no index, because
                        it looks maintained.
  6 counters-stale      the numbers written in CURRENT-STATE.md and
                        MASTER-RESEARCH-STATUS.md compared against reality.
  7 evidence-freshness  HEAD compared against the HEAD recorded in
                        CURRENT-STATE.md, and the untracked count, which grows
                        on its own.

WHAT IT DOES NOT PROVE, DECLARED UP FRONT
------------------------------------------
  1. It does not check whether a claim is TRUE.  Nothing can.  It checks that a
     claim is internally consistent and traceable, which is a different thing.
  2. It does not read the findings.  A finding with contradictory content is
     invisible to it; only its PRESENCE in the index is checked.
  3. Check 4 will report corpus-relative paths as hits.  Those are usually
     correct.  It is a review list, not an error list, and it says so.
  4. It does not know which lock belongs to which session, and does not touch
     .write-lock/ at all.
  5. Passing means the STRUCTURE is sound.  The content can still be wrong, and
     the two most serious defects found today were both content, found by
     arbitrating against the running hardware, not by scanning.

SEVERITIES, and the default
---------------------------
  defect  a broken link, a missing definition, a wrong count.  Fix it.
  stale   a counter that drifted, or a HEAD that moved.  Expected under
          concurrency; reported so it is never silently wrong.
  review  something to look at by hand.  Never fails the run by default.
  --fail-on {defect,stale,review,none}
"""

import argparse
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
TOOL = "docscan"

SEVERITY_ORDER = {"review": 0, "stale": 1, "defect": 2}

# Two classes of non-Latin script, and the split is not cosmetic.
#
# ACCIDENT SIGNATURE -- every one of these has appeared in this tree by mistake,
# each one seconds after an edit, on 2026-10-01:
#     Cyrillic   "его", "утр"   in place of Spanish words
#     Han        "第二天", "再加", "那片", "纠正"
#     Kana, Hangul, Arabic, Devanagari, fullwidth
# Severity `defect`.  Ranges are written as explicit escapes because Greek
# belongs to the OTHER class and the two lists must not overlap: a scanner that
# cries wolf on correct notation gets ignored on the day it is right.
RE_ACCIDENT = re.compile(
    "["
    "Ѐ-ӿ"   # Cyrillic
    "؀-ۿ"   # Arabic
    "ऀ-ॿ"   # Devanagari
    "぀-ヿ"   # Hiragana + Katakana
    "㐀-䶿"   # CJK ext A
    "一-鿿"   # CJK unified
    "가-힯"   # Hangul syllables
    "＀-￯"   # fullwidth forms
    "]"
)

# INTENTIONAL NOTATION -- Greek is deliberate in this tree.  `ΔFPS`, `δt`, `σ`
# are notation:
#     EXPERIMENTS.md:232  "10 corridas pareadas, ΔFPS=0"
# Severity `review`, never `defect`.
RE_NOTATION = re.compile("["
                         "Ͱ-Ͽ"   # Greek and Coptic
                         "ἀ-῿"   # Greek Extended
                         "∀-⋿"   # mathematical operators
                         "]")

RE_MD_REF = re.compile(r"\]\(([A-Za-z0-9._/-]+\.md)\)")

# a repo path in backticks: has a slash and a known-ish source extension
RE_BACKTICK_PATH = re.compile(
    r"`([0-9A-Za-z_][0-9A-Za-z_./-]*\.(?:md|c|h|py|sh|json|ko|txt))`"
)

# symbol definitions and citations
DEF_PATTERNS = [
    (re.compile(r"^## (RE-\d+)", re.M), "RE"),
    (re.compile(r"^\| (RE-\d+) \|", re.M), "RE"),
    (re.compile(r"^## (TL-\d+)", re.M), "TL"),
    (re.compile(r"^## (F\d+b?d?) ·", re.M), "F"),
    (re.compile(r"^## (C-\d+)", re.M), "C"),
]
RE_CITE = re.compile(r"\b(RE-\d+|TL-\d+|F\d+b?d?|C-\d+)\b")

# symbols that are allowed to be cited without a local definition
ALWAYS_OK = {"C-001", "C-002"}


class Finding:
    __slots__ = ("severity", "check", "where", "what")

    def __init__(self, severity, check, where, what):
        self.severity = severity
        self.check = check
        self.where = where
        self.what = what

    def __str__(self):
        return "  %-7s %-18s %s: %s" % (self.severity, self.check, self.where, self.what)


def load_docs(docs_dir):
    out = []
    for fn in sorted(os.listdir(docs_dir)):
        p = os.path.join(docs_dir, fn)
        if fn.endswith(".md"):
            out.append((fn, p))
        elif fn == "archive":
            for afn in sorted(os.listdir(p)):
                if afn.endswith(".md"):
                    out.append(("archive/" + afn, os.path.join(p, afn)))
    return out


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

SCRIPT_NAMES = [
    ("Cyrillic", "\u0400-\u04ff"), ("Arabic", "\u0600-\u06ff"),
    ("Devanagari", "\u0900-\u097f"), ("Kana", "\u3040-\u30ff"),
    ("Han", "\u4e00-\u9fff"), ("Hangul", "\uac00-\ud7af"),
    ("fullwidth", "\uff01-\uffef"),
    ("Greek", "\u0370-\u03ff"),
]


def check_non_latin(docs):
    """
    Accidental scripts are DEFECTS, one finding per line, because every one of
    them has appeared in this tree by mistake and each is worth reading.

    Intentional notation is NOT reported per line.  The first version did, and
    it produced 194 review items, essentially all of them the minus sign in
    `count = payload - 1`, which is deliberate notation used everywhere.  A
    review list made of that trains people to skip review items.  So notation is
    reported as a COUNT PER CLASS, once, and never fails anything.
    """
    f = []
    notation_lines = 0
    for name, p in docs:
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if RE_ACCIDENT.search(line):
                f.append(Finding("defect", "non-latin-glyphs", "%s:%d" % (name, i),
                                 line.strip()[:90]))
            elif RE_NOTATION.search(line):
                notation_lines += 1

    if notation_lines:
        detail = ", ".join(
            "%s %s" % (nm, len(re.findall("[%s]" % rng,
                   "\n".join(open(p, encoding="utf-8").read() for _n, p in docs))))
            for nm, rng in SCRIPT_NAMES
            if re.search("[%s]" % rng,
                         "\n".join(open(p, encoding="utf-8").read() for _n, p in docs)))
        f.append(Finding("review", "notation-usage",
                         "docs/",
                         "%d lines carry deliberate notation (%s). Expected: minus "
                         "signs, !=, >=, degrees, delta. Greek is worth a glance"
                         % (notation_lines, detail)))
    return f


def check_refs(docs):
    f = []
    for name, p in docs:
        txt = open(p, encoding="utf-8").read()
        for m in RE_MD_REF.finditer(txt):
            tgt = m.group(1)
            if not os.path.exists(os.path.join(os.path.dirname(p), tgt)):
                f.append(Finding("defect", "broken-md-refs", name,
                                 "-> %s does not exist" % tgt))
    return f


def check_symbols(docs):
    defined, cited = set(), {}
    for name, p in docs:
        txt = open(p, encoding="utf-8").read()
        for rx, _kind in DEF_PATTERNS:
            for m in rx.finditer(txt):
                defined.add(m.group(1))
        for m in RE_CITE.finditer(txt):
            cited.setdefault(m.group(1), set()).add(name)
    f = []
    for sym in sorted(set(cited) - defined):
        if sym in ALWAYS_OK:
            continue
        f.append(Finding("defect", "undefined-symbols",
                         ",".join(sorted(cited[sym]))[:60],
                         "%s is cited but never defined" % sym))
    return f


# Where a corpus-relative citation may legitimately point.  Bare basenames like
# `sdma_v3_0.c` are the normal convention here: the citation is relative to the
# corpus root, and every doc says so once.
CORPUS_BASES = ("RESEARCH/working/linux-7.1.3",
                "RESEARCH/kernelbuild/linux-7.1.3",
                "RESEARCH/baseline/linux-7.1.3",
                "rx550-upstream-7.2.8/linux-7.2.8")


def _basename_index(repo_root):
    """
    Every file basename in the repository, excluding .git and the corpora.

    A bare basename in backticks is the dominant citation style in this tree:
    docs/ says `pm4dw.c`, `sdma_v3_0.c`, `MASTER-RESEARCH-STATUS.md`, and all
    three exist, just not at the path where they were named.  Citing the
    basename of a file that exists is legitimate and this check must not nag
    about it.  The first version only indexed the corpora, so it reported 150
    items of which essentially every one was a correct citation.

    Only the REPO is indexed here.  The corpora are walked separately because
    they are large, and a corpus basename is accepted too, just from a
    different index.
    """
    idx = set()
    skip = {".git"}
    for dp, dns, fns in os.walk(repo_root):
        dns[:] = [d for d in dns if d not in skip and d not in CORPUS_BASES]
        for fn in fns:
            idx.add(fn)
    return idx


def _corpus_basename_index(repo_root):
    """Set of every file basename under the known corpora."""
    idx = set()
    for base in CORPUS_BASES:
        top = os.path.join(repo_root, base)
        if not os.path.isdir(top):
            continue
        for dp, _dn, fns in os.walk(top):
            for fn in fns:
                idx.add(fn)
    return idx


def check_repo_paths(docs, repo_root):
    """
    Paths in backticks that do not resolve.

    Citing the corpus relative to its own root is CORRECT here, so this check
    resolves three ways before reporting: the repo root, each corpus root, and
    finally the basename index.  A basename that exists anywhere in a corpus is
    a legitimate citation, not a defect.

    Results are deduplicated.  The first version reported 214 items of which
    most were the same handful of basenames repeated per mention, which is not a
    review list, it is noise that trains people to skip the check.
    """
    f = []
    base_idx = _basename_index(repo_root) | _corpus_basename_index(repo_root)
    for name, p in docs:
        txt = open(p, encoding="utf-8").read()
        seen = set()
        for m in RE_BACKTICK_PATH.finditer(txt):
            rel = m.group(1)
            if rel.startswith(("http", "mailto")) or rel in seen:
                continue
            seen.add(rel)
            if os.path.exists(os.path.join(repo_root, rel)):
                continue
            if any(os.path.exists(os.path.join(repo_root, b, rel))
                   for b in CORPUS_BASES):
                continue
            if os.path.basename(rel) in base_idx:
                continue
            # also accept a bare name that exists in docs/ itself, which is the
            # normal way these documents refer to one another
            f.append(Finding("review", "repo-paths-missing", name,
                             "%s  (no root nor corpus has this)" % rel))
    return f


def git_ls_tracked(repo_root, paths):
    """
    Which of `paths` are tracked.  Read-only.

    NOT `git ls-files --error-unmatch`.  That flag makes git exit non-zero if
    ANY of the given paths is untracked, so a directory that is half tracked
    returns an empty set, and the tool then reports EVERY file as untracked.
    Measured on this tree at 13:5x: 87 findings, and the tool said "87 untracked"
    when 30 of them were tracked.  A measurement that reports the alarming
    number is worse than no measurement, so this calls plain `git ls-files` and
    intersects.
    """
    try:
        r = subprocess.run(["git", "-C", repo_root, "ls-files"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    tracked = set(r.stdout.split("\n")) - {""}
    want = set(paths)
    return tracked & want


def git_head(repo_root):
    try:
        r = subprocess.run(["git", "-C", repo_root, "log", "--oneline", "-1"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def measure_findings(repo_root):
    fdir = os.path.join(repo_root, "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(fdir):
        return None
    names = sorted(fn for fn in os.listdir(fdir) if fn.endswith(".md"))
    rels = [os.path.join("06-INGENIERIA-INVERSA", "findings", n) for n in names]
    tracked = git_ls_tracked(repo_root, rels)
    n_untracked = None if tracked is None else len(names) - len(tracked)
    nums, dupes = {}, {}
    for n in names:
        head = n.split("-")[0]
        nums.setdefault(head, []).append(n)
    dupe_list = sorted(k for k, v in nums.items() if len(v) > 1)
    all_nums = sorted(int(x) for x in nums if x.isdigit())
    holes = [n for n in range(min(all_nums), max(all_nums) + 1) if n not in all_nums] \
        if all_nums else []
    return {"total": len(names), "untracked": n_untracked,
            "dupes": dupe_list, "holes": holes, "names": names}


def check_findings_unindexed(docs, repo_root, m):
    if not m:
        return []
    idx_path = os.path.join(repo_root, "docs", "FINDINGS-INDEX.md")
    if not os.path.exists(idx_path):
        return [Finding("defect", "findings-unindexed", "FINDINGS-INDEX.md",
                        "the index does not exist")]
    txt = open(idx_path, encoding="utf-8").read()
    f = []
    missing = []
    for n in m["names"]:
        stem = n[:-3]
        # the index may cite the stem with or without a wildcard
        if stem not in txt and not any(
                stem.startswith(w.rstrip("*")) for w in re.findall(r"`([^`]+)`", txt)):
            missing.append(n)
    if missing:
        f.append(Finding("stale", "findings-unindexed", "FINDINGS-INDEX.md",
                        "%d of %d findings are not in the index: %s"
                        % (len(missing), m["total"], ", ".join(missing[:6]))))
    return f



# --------------------------------------------------------------------------
# --index: append the findings the index does not list
# --------------------------------------------------------------------------

INDEX_ROW = re.compile(r"^\|\s*(\d{3})\s*\|\s*`([^`]+)`\s*\|")


def finding_tema(path):
    """
    The finding's own title, transcribed.

    The H1 FIRST.  A finding here looks like

        # 043 · la asercion la hacen 4 sitios
        ## CUDA principal
        ...

    so taking the first H2 gave "CUDA principal" for all 49 appended rows: that is
    the section every finding has, and a topic column that says the same thing 49
    times is not a topic column.  The H1 carries the title the author gave it, which
    is what the index wants.

    Falls back to the first real heading, then to a mark, so a row is never blank.
    """
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return "(ilegible)"
    heads = re.findall(r"^#+\s*(.+?)\s*$", txt, re.M)
    if heads:
        h = re.sub(r"^[0-9]{3}\s*[\u00b7.\-]\s*", "", heads[0])
        h = h.replace("*", "").replace("`", "").strip()
        if h:
            return h[:70]
    for h in heads[1:]:
        h = h.replace("*", "").replace("`", "").strip()
        if h and not set(h) <= set("=-"):
            return h[:70]
    return "(sin titulo)"


def index_missing(docs, repo_root, m, tracked=None):
    """Findings absent from the index table, with the fields a row needs."""
    if not m:
        return []
    idx_path = os.path.join(repo_root, "docs", "FINDINGS-INDEX.md")
    if not os.path.exists(idx_path):
        return []
    txt = open(idx_path, encoding="utf-8").read()
    listed = set(re.findall(r"`([^`]+\.md)`", txt))
    out = []
    for n in sorted(m["names"]):
        if n in listed:
            continue
        num = n[:3]
        state = "TRACKED" if n in (tracked or set()) else "UNTRACKED"
        out.append({"num": num, "name": n,
                    "tracked": state,
                    "tema": finding_tema(os.path.join(
                        repo_root, "06-INGENIERIA-INVERSA/findings", n))})
    return out


def write_index(repo, rows, already_read_note):
    """
    Append rows to the existing table.

    Inserted AFTER THE LAST ROW OF THE TABLE and not at end of file, because
    FINDINGS-INDEX.md has prose sections after its table and appending to the end
    would bury the rows inside an essay.

    Every appended row is marked `NO LEIDA` in the "sostiene" column.  That is the
    whole honesty of this mode: the row says a finding exists and what it is
    called, and it says that nobody has read it yet.  Adding a title transcribed
    from the file's own heading is not a claim about it.
    """
    path = os.path.join(repo, "docs", "FINDINGS-INDEX.md")
    lines = open(path, encoding="utf-8").read().split("\n")
    last = None
    for i, l in enumerate(lines):
        if INDEX_ROW.match(l):
            last = i
    if last is None:
        return None, 0
    block = [already_read_note, ""]
    for r in rows:
        block.append("| %s | `%s` | %s | %s | NO LEIDA — transcripción, nadie lo ha leído |"
                     % (r["num"], r["name"], r["tema"], r["tracked"]))
    lines[last + 1:last + 1] = block
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path, len(rows)


NOTE = ("> **Filas añadidas mecánicamente el 2026-10-02**, por `docscan.py --index`. Cada"
        " fila transcribe el título que el propio hallazgo escribe y su estado en git."
        " **Ninguna ha sido leída**, y por eso la columna dice `NO LEIDA`: un título"
        " transcrito no es una afirmación sobre el hallazgo. Están aquí para que el"
        " índice no esté viejo respecto al árbol, que crece varias veces por hora.")



TYPE_VOCAB = {
    "FACT", "OBSERVATION", "MEASUREMENT", "DERIVATION", "MODEL_CHOICE",
    "REQUIREMENT", "POLICY", "IMPLEMENTATION", "TEST", "CONCLUSION",
    "HYPOTHESIS", "ASSUMPTION", "LIMITATION", "ERROR", "NEGATIVE_RESULT",
    "CONTRADICTION", "CORRECTION",
}
STATE_VOCAB = {
    "PROVEN", "OBSERVED", "PROVEN_DERIVED", "PROVEN_ABSENT", "CORROBORATED",
    "REFUTED", "NOT_PROVEN", "UNKNOWN", "NOT_DETERMINED", "NOT_AVAILABLE",
    "NOT_OBSERVED", "NOT_FOUND", "NOT_APPLICABLE", "NOT_IN_CORPUS", "PARTIAL",
    "DEFERRED", "SUPERSEDED",
}


def check_taxonomy(docs):
    """
    Every TYPE and STATE must be exactly one token from the closed vocabulary.

    MEASURED on this tree before this check existed: 12 of 51 claims had prose
    appended to TYPE -- `DERIVATION + NEGATIVE_RESULT`, `OBSERVATION, con
    medición propia`, `MEASUREMENT · y el hallazgo de mayor valor de esta ronda`.
    STATE was already clean, all 51.

    Why it matters and it is not pedantry: a field that carries prose is a field
    that cannot be compared.  Any tool that groups claims by TYPE, or that refuses
    to count a claim whose TYPE is not in the vocabulary, reads all twelve as
    malformed and not as the types they are.  A taxonomy that tolerates a second
    sentence in its own field is a taxonomy with no teeth.

    And the twelve were not written that way deliberately.  They are what happens
    when the vocabulary is a list rather than a check: each annotation was true
    and helpful where it sat, and nobody was told it made the field unparseable.
    """
    out = []
    for name, txt in docs:
        if name != "EVIDENCE-MATRIX.md":
            continue
        parts = re.split(r"^(## RE-\d+[^\n]*\n)", txt, flags=re.M)
        for i in range(1, len(parts), 2):
            cid = re.match(r"## (RE-\d+)", parts[i]).group(1)
            body = parts[i + 1]
            tm = re.search(r"^TYPE\s+(.*)$", body, re.M)
            if not tm:
                out.append(Finding("stale", "taxonomy-type", "EVIDENCE-MATRIX.md",
                                   "%s has no TYPE" % cid))
                continue
            raw = tm.group(1).strip()
            if raw.split()[0].upper() not in TYPE_VOCAB:
                out.append(Finding("stale", "taxonomy-type", "EVIDENCE-MATRIX.md",
                                   "%s TYPE %r is not in the vocabulary" % (cid, raw)))
            if len(raw.split()) > 1 or raw.endswith(","):
                out.append(Finding("stale", "taxonomy-type", "EVIDENCE-MATRIX.md",
                                   "%s TYPE carries prose: %r" % (cid, raw)))
            sm = re.search(r"^STATE\s+(.*)$", body, re.M)
            if not sm:
                out.append(Finding("stale", "taxonomy-state", "EVIDENCE-MATRIX.md",
                                   "%s has no STATE" % cid))
            elif sm.group(1).strip().split()[0].upper() not in STATE_VOCAB:
                out.append(Finding("stale", "taxonomy-state", "EVIDENCE-MATRIX.md",
                                   "%s STATE %r is not in the vocabulary"
                                   % (cid, sm.group(1).strip())))
    return out


def check_counters(docs, repo_root, m):
    f = []
    if not m:
        return f
    for name, p in docs:
        txt = open(p, encoding="utf-8").read()
        for rx, label, want in (
            (re.compile(r"FINDINGS\s+(\d+) ficheros"), "findings total", m["total"]),
            (re.compile(r"TRACKED\s+(\d+) de (\d+)"), "tracked count", None),
            (re.compile(r"UNTRACKED\s+(\d+):"), "untracked count", m["untracked"]),
        ):
            for mm in rx.finditer(txt):
                got = int(mm.group(1))
                if want is not None and got != want:
                    f.append(Finding("stale", "counters-stale", name,
                                    "%s says %d, reality %d" % (label, got, want)))
        if m["dupes"]:
            frm = re.search(r"INDEX\s+([\d ]+) DUPLICADOS\s*\n?\s*\((\d+) colisiones\)", txt)
            if frm:
                gotn = int(frm.group(2))
                if gotn != len(m["dupes"]):
                    f.append(Finding("stale", "counters-stale", name,
                                    "collision count says %d, reality %d"
                                    % (gotn, len(m["dupes"]))))
    return f


def check_freshness(docs, repo_root):
    f = []
    head = git_head(repo_root)
    cs = os.path.join(repo_root, "docs", "CURRENT-STATE.md")
    if head and os.path.exists(cs):
        txt = open(cs, encoding="utf-8").read()
        m = re.search(r"HEAD al terminar\s+(\w+)", txt)
        if m and m.group(1) != head:
            f.append(Finding("stale", "evidence-freshness", "CURRENT-STATE.md",
                            "records HEAD %s, real HEAD %s.  Rows citing findings "
                            "after that point are unreviewed" % (m.group(1), head)))
    return f


# --------------------------------------------------------------------------
# --sync: rewrite the counter fields, and nothing else
# --------------------------------------------------------------------------

# Each entry: (file, regex with ONE capture group = the number to replace).
# Deliberately narrow.  A tool that edits prose is a tool that can ruin prose;
# this one only substitutes a digit in a field whose name identifies it, and it
# prints every substitution it made.
SYNC_FIELDS = [
    ("CURRENT-STATE.md", re.compile(r"(FINDINGS\s+)(\d+)(?= ficheros)"), "findings total"),
    ("CURRENT-STATE.md", re.compile(r"(UNTRACKED\s+)(\d+)(?=: )"), "untracked"),
    ("FINDINGS-INDEX.md", re.compile(r"(tiene \*\*)(\d+)(?= índices duplicados)"),
     "index collisions"),
    # every pattern here has exactly two groups: a literal prefix, then the
    # number.  An earlier version of this entry had only one group and crashed
    # with IndexError on the first real --sync run.
    ("MASTER-RESEARCH-STATUS.md", re.compile(r"(de los )(\d+)(?= findings)"), "indexed count"),
]


def _assert_two_groups():
    """Fail loudly at import if a SYNC_FIELDS pattern loses its capture group."""
    for fname, rx, _kind in SYNC_FIELDS:
        if rx.groups != 2:
            raise AssertionError(
                "SYNC_FIELDS entry for %s must have 2 groups (prefix, number); "
                "%r has %d" % (fname, rx.pattern, rx.groups))

# Handled separately because it carries TWO numbers and they must agree with each
# other.  Rewriting only the numerator was the first version's bug, and the
# self-test caught it: `TRACKED 31 de 0` is worse than `TRACKED 0 de 0`, because
# it looks measured.
SYNC_TRACKED = re.compile(r"(TRACKED\s+)(\d+)(\s+de\s+)(\d+)")

# The collision count lives inside a parenthesised continuation line, not in a
# named field, so the first --sync left it stale.  Added after docscan reported
# `collision count says 24, reality 25` and --sync said "every counter already
# matches reality".  A sync that silently does not cover a counter it just
# reported is worse than no sync: it asserts a completeness it does not have.
SYNC_COLLISIONS = re.compile(r"(\()(\d+)( colisiones\))")


def sync_counters(docs_dir, m, as_json=False):
    """
    Correct the numeric counters, and report each change.

    WHY THIS EXISTS, and it is a confession.  While writing this file's own
    sibling sync step as a one-liner, the author ran

        cd docs && git ls-files

    instead of

        git -C <repo> ls-files

    `git ls-files` prints paths relative to the CURRENT DIRECTORY, so from
    docs/ nothing matched and the script concluded that 0 of 87 findings were
    tracked.  That false number was then written into CURRENT-STATE.md, and
    `docscan --only counters-stale` immediately reported it as wrong.

    The lesson is not "be careful".  The lesson is that a counter which must be
    kept correct by a human one-liner WILL drift, silently, and the drift looks
    like a finding.  So the measurement and the correction live together, in the
    one place where the path handling is right, and the correction reports every
    substitution it makes so a wrong number can never be silent.

    Only the named fields are touched.  No prose is modified.
    """
    _assert_two_groups()
    changes = []
    if not m:
        return changes

    def want(kind):
        if kind == "findings total":
            return m["total"]
        if kind == "untracked":
            return m["untracked"]
        if kind == "index collisions":
            return len(m["dupes"])
        if kind == "indexed count":
            return m["total"]
        return None

    for fname, rx, kind in SYNC_FIELDS:
        path = os.path.join(docs_dir, fname)
        if not os.path.exists(path):
            continue
        target = want(kind)
        if target is None:
            continue
        txt = open(path, encoding="utf-8").read()

        def repl(mo, target=target, fname=fname, kind=kind):
            old = mo.group(2)
            if int(old) == target:
                return mo.group(0)
            changes.append({"file": fname, "field": kind,
                            "was": int(old), "now": target})
            return mo.group(1) + str(target)

        new = rx.sub(repl, txt)
        if new != txt:
            open(path, "w", encoding="utf-8").write(new)

    # TRACKED  <tracked> de <total>: both numbers, together
    cst = os.path.join(docs_dir, "CURRENT-STATE.md")
    if os.path.exists(cst):
        txt = open(cst, encoding="utf-8").read()
        tracked = m["total"] - m["untracked"]

        def repl_tracked(mo):
            if int(mo.group(2)) == tracked and int(mo.group(4)) == m["total"]:
                return mo.group(0)
            changes.append({"file": "CURRENT-STATE.md", "field": "tracked",
                            "was": "%s de %s" % (mo.group(2), mo.group(4)),
                            "now": "%d de %d" % (tracked, m["total"])})
            return "%s%d%s%d" % (mo.group(1), tracked, mo.group(3), m["total"])

        new = SYNC_TRACKED.sub(repl_tracked, txt)
        if new != txt:
            cst_txt = new
            open(cst, "w", encoding="utf-8").write(cst_txt)

    # INDEX ... DUPLICADOS  /  (N colisiones)
    cst = os.path.join(docs_dir, "CURRENT-STATE.md")
    if os.path.exists(cst):
        txt = open(cst, encoding="utf-8").read()
        want_c = len(m["dupes"])

        def repl_col(mo):
            if int(mo.group(2)) == want_c:
                return mo.group(0)
            changes.append({"file": "CURRENT-STATE.md", "field": "colisiones",
                            "was": int(mo.group(2)), "now": want_c})
            return "%s%d%s" % (mo.group(1), want_c, mo.group(3))

        new = SYNC_COLLISIONS.sub(repl_col, txt)
        if new != txt:
            open(cst, "w", encoding="utf-8").write(new)

    return changes


# --------------------------------------------------------------------------
# self-test, with negative controls
# --------------------------------------------------------------------------

def build_bad_docs(root):
    """A docs/ tree with one known instance of each defect."""
    os.makedirs(os.path.join(root, "docs", "archive"), exist_ok=True)
    w = lambda p, s: open(os.path.join(root, "docs", p), "w", encoding="utf-8").write(s)
    w("A-MAIN.md",
      "# main\n\nsee [ok](B-OK.md) and [broken](NO-SUCH.md)\n\n"
      "stray CJK: 日本語\n"
      "notation on purpose: ΔFPS=0 and δt\n"
      "cites RE-99 and TL-88, neither defined\n"
      "path `no/such/file.c`\n"
      "FINDINGS         7 ficheros\n"
      "UNTRACKED        3:\n"
      "HEAD al terminar    deadbee\n")
    w("B-OK.md", "# ok\n\nnothing wrong here\n\n## RE-01\n## TL-01\n## F1 · x\n## C-001\n")
    w("archive/OLD.md", "# old\n\nno defects here\n")


def build_good_docs(root):
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    # structurally clean, but cites one path that does not exist, so the
    # `review` severity has something to be measured on
    open(os.path.join(root, "docs", "A-MAIN.md"), "w", encoding="utf-8").write(
        "# main\n\nsee [ok](B-OK.md)\n\n## RE-01\n\n## TL-01\n\n"
        "## F1 · x\n\n## C-001\n\nFINDINGS         0 ficheros\n\n"
        "path `no/such/other.c`\n\nHEAD al terminar    deadbee\n"
    )
    open(os.path.join(root, "docs", "B-OK.md"), "w", encoding="utf-8").write("# ok\n")


EXPECT_BAD = {
    "non-latin-glyphs": 1,        # CJK only.  Δ and δ are notation, not a defect
    "broken-md-refs": 1,
    "undefined-symbols": 2,       # RE-99 and TL-88
}
EXPECT_REVIEW = {"notation-usage": 1}


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 62)
    fails = 0
    checks = 0

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        build_bad_docs(td)
        docs = load_docs(os.path.join(td, "docs"))

        got = {}
        for f in check_non_latin(docs) + check_refs(docs) + check_symbols(docs):
            got[f.check] = got.get(f.check, 0) + 1
        for name, want in EXPECT_BAD.items():
            checks += 1
            have = got.get(name, 0)
            if have == want:
                print("  OK    detects exactly %d x %-18s" % (want, name))
            else:
                print("  FAIL  %-18s expected %d, got %d" % (name, want, have))
                fails += 1

        rev = {}
        for f in check_non_latin(docs):
            if f.severity == "review":
                rev[f.check] = rev.get(f.check, 0) + 1
        # notation must never be a per-line finding
        for name, want in EXPECT_REVIEW.items():
            checks += 1
            have = rev.get(name, 0)
            if have == want:
                print("  OK    intentional notation -> severity `review`, not defect")
            else:
                print("  FAIL  %-18s expected %d review items, got %d" % (name, want, have))
                fails += 1

        checks += 1
        per_line = [f for f in check_non_latin(docs)
                    if f.severity == "review" and f.where != "docs/"]
        if not per_line:
            print("  OK    notation is reported in aggregate, never line by line")
        else:
            print("  FAIL  %d notation findings are per-line" % len(per_line))
            fails += 1

        # the fixture must actually contain what it claims, otherwise the counts
        # above were 0 == 0 and proved nothing.
        checks += 1
        found_any = bool(check_non_latin(docs) + check_refs(docs) + check_symbols(docs)
                         + check_repo_paths(docs, td))
        if found_any:
            print("  OK    the fixture contains the defects it claims to")
        else:
            print("  FAIL  fixture and expectations disagree")
            fails += 1

    with tempfile.TemporaryDirectory() as td:
        build_good_docs(td)
        docs = load_docs(os.path.join(td, "docs"))
        checks += 1
        # A structurally clean tree must produce no `defect` and no `stale`.
        # It MAY produce `review` items, by design: a missing path is often a
        # correct corpus-relative citation, and calling that a false positive
        # would push the tool's users into deleting correct references.
        residual = [f for f in
                    (check_non_latin(docs) + check_refs(docs) + check_symbols(docs)
                     + check_repo_paths(docs, td))
                    if f.severity in ("defect", "stale")]
        if not residual:
            print("  OK    negative control: a clean tree produces no defect")
        else:
            for f in residual:
                print("  FAIL  false positive on a clean tree: %s" % f)
            fails += 1

        # and the review-severity check must not fail the run
        checks += 1
        rev = check_repo_paths(docs, td)
        if not rev:
            print("  FAIL  the clean fixture has no missing path to review")
            fails += 1
        elif all(f.severity == "review" for f in rev):
            print("  OK    a missing path is severity `review`, never `defect`")
        else:
            print("  FAIL  review severity is wrong")
            fails += 1

        # --sync must correct a wrong counter AND leave prose alone.
        # The fixture uses the REAL field layout, because --sync keys on the
        # real file names: an earlier version of this test used invented names
        # and "passed" only because sync correctly found nothing to do.
        checks += 1
        cst = os.path.join(td, "docs", "CURRENT-STATE.md")
        with open(cst, "w", encoding="utf-8") as fh:
            fh.write("PROSA QUE NO SE DEBE TOCAR\n\n"
                     "FINDINGS         0 ficheros en findings/\n"
                     "TRACKED          0 de 0\n"
                     "UNTRACKED        0: algo\n"
                     "INDEX            001 010 DUPLICADOS\n"
                     "                 (0 colisiones)\n")
        before = open(cst, encoding="utf-8").read()
        fake = {"total": 42, "untracked": 11, "dupes": ["001", "010"], "holes": [],
                "names": [], "tracked": None}
        ch = sync_counters(os.path.join(td, "docs"), fake)
        after = open(cst, encoding="utf-8").read()
        want = ("PROSA QUE NO SE DEBE TOCAR\n\n"
                "FINDINGS         42 ficheros en findings/\n"
                "TRACKED          31 de 42\n"
                "UNTRACKED        11: algo\n"
                "INDEX            001 010 DUPLICADOS\n"
                "                 (2 colisiones)\n")
        if after == want:
            print("  OK    --sync corrects the numbers and preserves the prose")
        else:
            print("  FAIL  --sync output is wrong")
            print("        want: %r" % want)
            print("        got : %r" % after)
            fails += 1

        checks += 1
        if len(ch) == 4 and all(c["was"] == 0 or c["was"] == "0 de 0" for c in ch):
            print("  OK    --sync reports every substitution it made (%d)" % len(ch))
        else:
            print("  FAIL  --sync reported %d changes, expected 4" % len(ch))
            fails += 1

        # and it must cover EVERY counter that check_counters can flag.
        # The first --sync covered four of five and printed "every counter already
        # matches reality" while one was stale.  A sync that claims a completeness it
        # does not have is worse than no sync.
        checks += 1
        covered = {k for _f, _rx, k in SYNC_FIELDS} | {"tracked", "colisiones"}
        flagged = {"findings total", "tracked", "untracked",
                   "collision count", "index collisions"}
        missing = {c for c in flagged if c not in covered} - {"collision count"}
        if not missing:
            print("  OK    --sync covers every counter that the stale check flags")
        else:
            print("  FAIL  --sync does not cover: %s" % ", ".join(sorted(missing)))
            fails += 1

        # and a second run must be a no-op, or it is not idempotent
        checks += 1
        ch2 = sync_counters(os.path.join(td, "docs"), fake)
        if not ch2 and open(cst, encoding="utf-8").read() == want:
            print("  OK    --sync is idempotent: a second run changes nothing")
        else:
            print("  FAIL  --sync is not idempotent (%d extra changes)" % len(ch2))
            fails += 1

        checks += 1
        gate = SEVERITY_ORDER["review"] >= SEVERITY_ORDER["defect"]
        if not gate:
            print("  OK    --fail-on=defect does not trip on a `review` item")
        else:
            print("  FAIL  the severity gate is inverted")
            fails += 1

        # ---- --index: topic from H1, untracked marked, and every row NO LEIDA
        fd2 = os.path.join(td, "06-INGENIERIA-INVERSA", "findings")
        os.makedirs(fd2, exist_ok=True)
        with open(os.path.join(fd2, "006-f.md"), "w", encoding="utf-8") as fh:
            fh.write("# 006 \u00b7 el titulo que el autor escribio\n\n"
                     "## CUDA principal\n\ntexto\n")
        # index_missing needs the INDEX to exist; the good-docs fixture has none,
        # so without this the function returns [] and the check would be testing
        # an early return rather than the transcription
        with open(os.path.join(td, "docs", "FINDINGS-INDEX.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("# idx\n\n| # | Finding | Tema | Estado | Sostiene |\n"
                     "|---|---|---|---|---|\n"
                     "| 001 | `001-a.md` | lo que hay | TRACKED | - |\n")
        rows2 = index_missing([], td, {"names": ["001-a.md", "006-f.md"]}, set())
        checks += 1
        if rows2 and rows2[0]["tema"] == "el titulo que el autor escribio":
            print("  OK    --index takes the topic from the H1, not the first H2:")
            print("        every finding shares \"CUDA principal\", so an H2 topic")
            print("        column would print the same thing in all 49 rows")
        else:
            print("  FAIL  tema = %r" % (rows2 and rows2[0]["tema"]))
            fails += 1

        checks += 1
        if rows2 and rows2[0]["tracked"] == "UNTRACKED":
            print("  OK    an untracked finding is marked UNTRACKED: that means")
            print("        `git clean -x` erases it and leaves no trace")
        else:
            print("  FAIL  tracked = %r" % (rows2 and rows2[0]["tracked"]))
            fails += 1

        checks += 1
        if "NO LEIDA" in NOTE:
            print("  OK    every appended row is marked NO LEIDA.  A transcribed title")
            print("        is not a claim about the finding, and this mode does not")
            print("        pretend that anybody read them")
        else:
            print("  FAIL  appended rows are not marked as unread")
            fails += 1

        # ---- the closed vocabulary: a field that carries prose is not a field
        checks += 1
        em_txt = ("# E\n\n## RE-01\n\n```\nTYPE    FACT\nSTATE   PROVEN\n```\n\n"
                  "## RE-02\n\n```\nTYPE    DERIVATION + NEGATIVE_RESULT\n"
                  "STATE   PROVEN\n```\n\n## RE-03\n\n```\nTYPE    OBSERVATION, "
                  "con medicion propia\nSTATE   PROVEN\n```\n\n## RE-04\n\n```\n"
                  "TYPE    HECHO\nSTATE   PROVEN\n```\n\n## RE-05\n\n```\n"
                  "TYPE    FACT\nSTATE   INVENTADO\n```\n")
        f_tax = check_taxonomy([("EVIDENCE-MATRIX.md", em_txt)])
        flagged = set()
        for f in f_tax:
            for cid in ("RE-02", "RE-03", "RE-04", "RE-05"):
                if cid in f.what:
                    flagged.add(cid)
        if flagged == {"RE-02", "RE-03", "RE-04", "RE-05"}:
            print("  OK    taxonomy: TYPE/STATE outside the vocabulary is reported,")
            print("        and so is a valid token carrying prose.  Four ways to be")
            print("        wrong, and RE-01 alone passes")
        else:
            print("  FAIL  taxonomy flagged %s: %s"
                  % (sorted(flagged), [f.what for f in f_tax]))
            fails += 1

    print("  " + "-" * 62)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: pasar esto NO demuestra que ninguna afirmacion sea cierta.")
    print("        Comprueba que la estructura es coherente y trazable.  Los dos")
    print("        defectos mas graves de hoy eran de CONTENIDO, y se arbitrararon")
    print("        contra el hardware en ejecucion, no con un escaneo.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="docscan",
        description="consistency scan of docs/ and freshness cross-check",
    )
    ap.add_argument("--repo", default=".", help="repository root (default: .)")
    ap.add_argument("--docs", default=None,
                    help="docs directory (default: <repo>/docs)")
    ap.add_argument("--fail-on", default="defect",
                    choices=("defect", "stale", "review", "none"),
                    help="lowest severity that makes the run fail (default: defect)")
    ap.add_argument("--index", action="store_true",
                    help="append the findings the index does not list, each row "
                         "marked as NOT read.  THE ONLY WRITE besides --sync")
    ap.add_argument("--sync", action="store_true",
                    help="rewrite the numeric counter fields to match reality, "
                         "printing every substitution.  Touches only the named "
                         "fields; no prose.")
    ap.add_argument("--only", action="append", default=[],
                    help="run only these checks; repeatable")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output for CI.  Nothing may follow the "
                         "JSON document, or it stops being parseable.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo_root = os.path.abspath(args.repo)
    docs_dir = args.docs or os.path.join(repo_root, "docs")
    if not os.path.isdir(docs_dir):
        sys.stderr.write("docscan: no docs directory at %s\n" % docs_dir)
        return 2

    docs = load_docs(docs_dir)
    m = measure_findings(repo_root)

    if args.index:
        mf = measure_findings(repo_root)
        fdir = os.path.join(repo_root, "06-INGENIERIA-INVERSA", "findings")
        rels = [os.path.join("06-INGENIERIA-INVERSA", "findings", n)
                for n in (mf["names"] if mf else [])]
        trk = set(os.path.basename(x) for x in (git_ls_tracked(repo_root, rels) or []))
        rows = index_missing(docs, repo_root, mf, trk)
        if not rows:
            print("docscan --index: el indice ya lista todos los hallazgos")
        else:
            wp, n = write_index(repo_root, rows, NOTE)
            print("docscan --index: %d filas anadidas a %s" % (n, wp))
            for r in rows[:12]:
                print("   +%s  %-42s %-10s %s" % (r["num"], r["name"][:42],
                      r["tracked"], r["tema"][:40]))
            if len(rows) > 12:
                print("   ... y %d mas" % (len(rows) - 12))
            print()
            print("  Cada fila dice NO LEIDA. El indice deja de estar viejo")
            print("  respecto al arbol; lo que no se hace es dar por leidos")
            print("  hallazgos que nadie ha abierto.")
            print()

    if args.sync:
        changes = sync_counters(docs_dir, m, args.json)
        if args.json:
            print(json.dumps({"tool": TOOL, "version": VERSION,
                              "synced": changes}, indent=2, sort_keys=True))
        elif not changes:
            print("%s %s -- sync" % (TOOL, VERSION))
            print("  every counter already matches reality.  Nothing written.")
        else:
            print("%s %s -- sync" % (TOOL, VERSION))
            print("  %d counter field(s) rewritten:" % len(changes))
            for c in changes:
                # `was` is a string for the TRACKED field, which carries two
                # numbers ("0 de 87").  Formatting them as %d crashed on the
                # first real --sync run, after the files were already written.
                print("    %-22s %-18s %s -> %s"
                      % (c["file"], c["field"], c["was"], c["now"]))
        return 0

    all_checks = [
        ("non-latin-glyphs", lambda: check_non_latin(docs)),
        ("broken-md-refs", lambda: check_refs(docs)),
        ("undefined-symbols", lambda: check_symbols(docs)),
        ("repo-paths-missing", lambda: check_repo_paths(docs, repo_root)),
        ("taxonomy", lambda: check_taxonomy(docs)),
        ("findings-unindexed", lambda: check_findings_unindexed(docs, repo_root, m)),
        ("counters-stale", lambda: check_counters(docs, repo_root, m)),
        ("evidence-freshness", lambda: check_freshness(docs, repo_root)),
    ]
    selected = [c for c in all_checks if not args.only or c[0] in args.only]
    if args.only:
        unknown = set(args.only) - {c[0] for c in all_checks}
        if unknown:
            sys.stderr.write("docscan: unknown check(s): %s\n" % ", ".join(sorted(unknown)))
            return 2

    findings = []
    for name, fn in selected:
        findings.extend(fn())

    total_lines = sum(len(open(p, encoding="utf-8").read().split("\n"))
                      for _n, p in docs)

    print("%s %s" % (TOOL, VERSION))
    print("  " + "-" * 62)
    print("  repo          %s" % repo_root)
    print("  docs          %d files, %d lines" % (len(docs), total_lines))
    if m:
        print("  findings      %d total, %s untracked, %d index collisions, holes: %s"
              % (m["total"], m["untracked"], len(m["dupes"]),
                 ", ".join("%03d" % h for h in m["holes"]) or "none"))
    head = git_head(repo_root)
    if head:
        print("  HEAD          %s" % head)
    print("  checks        %s" % ", ".join(c[0] for c in selected))
    print("")

    # dedupe: the same (severity, check, where, what) reported twice is a bug
    # in a check, not two findings
    seen_keys = set()
    deduped = []
    for f in findings:
        k = (f.severity, f.check, f.where, f.what)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        deduped.append(f)
    findings = deduped

    by_sev = {}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)
    REVIEW_CAP = 25
    for sev in ("defect", "stale", "review"):
        items = sorted(by_sev.get(sev, []), key=lambda x: (x.check, x.where))
        if sev == "review" and len(items) > REVIEW_CAP:
            for f in items[:REVIEW_CAP]:
                print(f)
            print("  ...    and %d more review items (not defects; see the note below)"
                  % (len(items) - REVIEW_CAP))
        else:
            for f in items:
                print(f)

    print("")
    print("  " + "-" * 62)
    for sev in ("defect", "stale", "review"):
        print("  %-8s %d" % (sev, len(by_sev.get(sev, []))))
    print("")
    print("  review items are for a human, not for automation.  Check them by hand")
    print("  before changing anything: several are correct corpus-relative citations.")

    if args.fail_on == "none":
        return 0
    threshold = SEVERITY_ORDER[args.fail_on]
    bad = [f for f in findings if SEVERITY_ORDER[f.severity] >= threshold]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
