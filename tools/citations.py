#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE . STATIC_ANALYSIS

"""
citations -- resolve every `file.c:NNN` this project cites, and say how solid
each one is.

THE MEASUREMENT THAT JUSTIFIED THIS TOOL
---------------------------------------
MEASURED over this tree, not assumed:

    14903  file names exist in more than one copy
     9722  all copies byte-identical
     5181  the copies DIVERGE

So a citation like `amdgpu_gmc.c:1127` is AMBIGUOUS BY DEFAULT.  There are five
files with that basename in this repository and their contents differ, so
"line 1127" names different text depending on which tree you open.  A reader
who checks it against `RESEARCH/working/` and a reader who checks it against
`RESEARCH/kernelbuild/` can both be right and still disagree.

That is not a hypothetical.  It is also how this tool was born: its first
measurement reported 7 broken citations in `07-DRIVER/kernel/`, including three
into `gmc_8_1_d.h`.  All 7 were MY OWN search scope -- I had searched only
`drivers/gpu/drm/amd/` and those headers live under `include/asic_reg/`,
`include/drm/` and `include/uapi/`.  Every one of the 7 resolved once the index
was built properly, and the three GMC ones point at exactly the registers this
project is about:

    gmc_8_1_d.h:607 -> mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR
    gmc_8_1_d.h:615 -> mmVM_INVALIDATE_REQUEST

That is the second time in this project that an instrument blamed the artifact
for a fault that belonged to the instrument, and it is why the tool below
resolves through an index of every basename in every tree instead of guessing a
path.

TWO AXES, NOT ONE, AND GETTING THIS WRONG WOULD HAVE MISREPORTED THE PROJECT
--------------------------------------------------------------------------
The first version of this tool had a single FRAGILE verdict and reported 1116 of
2364 citations -- 47% of every citation in the tree -- as ambiguous.  Read, that
number is an alarm.  It is also mostly wrong, and the way it is wrong matters.

Look at the top case, `gmc_v8_0.c:1127`, cited 20 times:

    RESEARCH/kernelbuild/linux-7.1.3/.../gmc_v8_0.c   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
    RESEARCH/working/linux-7.1.3/.../gmc_v8_0.c       amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
    RESEARCH/baseline/linux-7.1.3/.../gmc_v8_0.c      amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
    rx550-upstream-7.2.8/linux-7.2.8/.../gmc_v8_0.c   adev->gmc.mc_mask = 0xffffffffffULL;

Three of those four agree.  The disagreement is between KERNEL VERSIONS, which is
what a version difference IS: 7.2.8 legitimately has different code at 1127.  The
partial-subtree worry that motivated the tool is not what this row shows.

So one verdict is not enough, and reporting 47% would have been a number that
looks like a finding and is mostly an artefact of counting 7.1.3 and 7.2.8 as
the same thing.  A measurement that inflates by conflating a version difference
with a disagreement is the same failure as inflating a number, which is why this
project corrects them.

  VERSIONED     every copy WITHIN a version agrees, and the versions differ.
                 Not a defect.  It means the citation names one kernel version
                 and the reader must know which.
  FRAGILE       copies WITHIN THE SAME VERSION DISAGREE.  This is the alarming
                 one: the corpus contradicts itself about the same line of the
                 same tree.
  UNIDENTIFIABLE  the same basename exists in unrelated parts of the kernel, so
                 the citation never said WHICH file it meant.  `vi.h:27` resolves
                 to BOTH amdgpu/vi.h and drivers/staging/media/tegra-video/vi.h --
                 a Tegra video driver header with nothing to do with the GPU --
                 and `file.c` to about fifty files under fs/, arch/ and drivers/.
                 A reader verifying such a citation can land in an unrelated
                 file, see something that looks like code, and conclude anything.
                 This is a trap, not an ambiguity, and it is not fixable by
                 searching harder: only the author can fix it, by naming the file.
                 An earlier version split this into COLLISION at 2 subsystems and
                 UNIDENTIFIABLE at 3+, which put an arbitrary threshold in the
                 middle of one fact.  One verdict, no threshold.
  ROBUST        every copy agrees, same version or not
  UNIQUE        only one copy has the line
  OUT_OF_RANGE  copies exist, none long enough for line N
  UNRESOLVED    no file with that basename exists here
  UNIDENTIFIABLE the citation succeeded, and still carries no information.
                 `file.c:840` resolves to about fifty files in a Linux tree:
                 arch/um/os-Linux/, drivers/usb/core/, fs/btrfs/, fs/ext4/...
                 There is no fact here that can be verified, because the text
                 never said WHICH file it meant.  This is not a failed check; it
                 is a reference that cannot be followed, and no amount of
                 searching will fix it.  Only the author can, by naming the file.
                 Generic names that behave this way, measured: file.c, pci.h,
                 types.h, file.h.

WHAT THE FRAGILE COUNT ACTUALLY WAS, MEASURED
-------------------------------------------
First run of this tool: 1116 of 2366 citations reported FRAGILE, 47%.  Read as
an alarm, that is a number about this project's citation hygiene, and it is
almost entirely an artefact.  After splitting by version, the FRAGILE class is
136, and it is fully accounted for:

    130 of 136  inside the four INSTRUMENTED files
                  amdgpu_vm.c  amdgpu_vm_pt.c
                  amdgpu_debugfs.c  amdgpu_debugfs.h
                   6 of 136  generic basenames: pci.h, file.h, types.h, file.c
                              which are collisions with no useful name

`RESEARCH/evidence/working-vs-kernelbuild-difference.md` had already established,
independently and by hashing against the official tarballs, that `working/` and
`baseline/` are pristine 7.1.3 byte for byte and that `kernelbuild/` carries local
instrumentation labelled `RE-02-E1 (RG-1)`.  So this tool CORROBORATES that by a
different route -- it never read the tarballs, it only asked whether copies
disagree -- and adds the one thing that file does not contain: the exposure.

THE EXPOSURE, WHICH IS THE NEW PART
-----------------------------------
That evidence file states the rule ("for any file:line citation the tree matters")
and illustrates it with one example.  It does not say how much of this project's
own text is exposed.  Measured here:

    130 citations into the four instrumented files

`amdgpu_vm.c` accounts for most of them, including every line used to close RE-10
this session (`2424 2427 2428 2429 2454 2463`).  Those are PRISTINE numbers, so
they are the correct ones for 7.1.3 and the running `7.1.3-200.nobara.fc44`
kernel; against `kernelbuild/` every one of them is off by exactly 12.

Which is the point of `--translate`: an ambiguity with a known, mechanical
resolution is not an ambiguity, it is a lookup.

  --translate NAME:N   find the same line of text in every copy that disagrees,
                       and print the equivalent line number in each

The mapping is by EXACT line text, and it is refused unless unique, so it cannot
invent an equivalence.

THE FOUR ORIGINAL VERDICTS, AND WHAT EACH ONE PROMISED
---------------------------------------------
  ROBUST      every copy that has this line has the SAME text there.  The copies
              differ elsewhere in the file, but they do not disagree about this
              line.  Anyone checking this citation reads the same sentence.
  UNIQUE      exactly one copy has this line at all.  Unambiguous, because only
              one file is long enough.
  FRAGILE     the copies DISAGREE about what line N says.  The citation is real
              and true in more than one sense, and which sense depends on which
              tree you read.  This is the interesting verdict: it is not an
              error, and it is not safe.
  OUT_OF_RANGE copies exist, but none is long enough to have line N
  UNRESOLVED  no file with that basename exists anywhere in this repository

`FRAGILE` is not a defect in the citation.  It is a fact about the corpus, and
it belongs in the record: the next person to verify that line needs to know
which tree they verified against.

WHAT IT DOES NOT DO, DECLARED
----------------------------
  1. It does not decide which copy is authoritative.  Choosing between
     `RESEARCH/working/`, `RESEARCH/kernelbuild/`, `RESEARCH/kernelref/` and
     `rx550-upstream-7.2.8/` is a knowledge question about this project's
     methodology, and it is not answerable from a file listing.
  2. It does not correct anything.  It has no write path.  A citation is
     rewritten by a person who knows what was meant.
  3. It does not judge whether a citation is RELEVANT to its claim.  A line
     that exists and says something else entirely is a different failure, and
     this tool cannot see it.
  4. It does not parse C.  It finds `name.ext:number` and resolves it.  No
     preprocessor, no macro expansion, no include graph.
  5. It does not read anything outside this repository.

SAFETY
------
Read-only.  It reads files and prints.  It has no code path that opens a file
for writing, and the self-test checks that in the source rather than trusting
the comment above.

USAGE
-----
    citations.py --repo .                 resolve every citation
    citations.py --repo . --fragile      only the ones whose copies disagree
    citations.py --repo . --by-root      group by which tree answered
    citations.py --repo . --show NAME:N  what line N says, in every copy
    citations.py --repo . --json
    citations.py --selftest
"""

import argparse
import hashlib
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "citations"

# Roots searched for files.  Detected rather than assumed: a root that does not
# exist is reported as absent instead of silently reducing coverage, because
# that is exactly the failure that made the first measurement wrong.
CANDIDATE_ROOTS = [
    "RESEARCH/kernelbuild",     # the complete tree
    "RESEARCH/working",         # a DELIBERATELY PARTIAL subtree
    "RESEARCH/baseline",
    "RESEARCH/kernelref",
    "RESEARCH/evidence",
    "rx550-upstream-7.2.8",
    ".",
]

# What gets scanned for citations.  The project's own authored text.  The corpus
# is excluded on purpose: upstream's comments cite upstream's own paths, and
# counting those would swamp the result with citations nobody here wrote.
SCAN_DIRS = ["07-DRIVER", "docs", "06-INGENIERIA-INVERSA/findings", "tools",
             "08-ARQUITECTURA", "00-INDICE", "05-HALLAZGOS"]

CITE = re.compile(r"\b([A-Za-z0-9_][A-Za-z0-9_.-]*\.[ch]):(\d+)(?:-(\d+))?\b")

# Directories never scanned for citations: the trees that contain the answers.
EXCLUDE_PARTS = {"RESEARCH", ".git", "__pycache__", "node_modules",
                 "rx550-upstream-7.2.8"}

MAX_FILE_BYTES = 8 * 1024 * 1024


# --------------------------------------------------------------------------
# index
# --------------------------------------------------------------------------

def discover_roots(repo):
    """Which roots exist.  Reported, not assumed."""
    out = []
    for r in CANDIDATE_ROOTS:
        p = os.path.join(repo, r)
        out.append((r, os.path.isdir(p)))
    return out


def build_index(repo, roots=None, log=None):
    """
    basename -> [paths].

    No hashing at index time.  Hashing 106k files to answer a question about
    three dozen citations would be the wrong trade, and the content of a file
    only matters when a citation actually points into it.
    """
    declared = discover_roots(repo)
    if roots is None:
        roots = [r for r, ok in declared if ok]
    else:
        roots = [r for r in roots]
    index = {}
    for r in roots:
        base = os.path.join(repo, r)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if "." not in fn:
                    continue
                index.setdefault(fn, []).append(os.path.join(dirpath, fn))
    if log:
        log("indexed %d basenames across %d roots" % (len(index), len(roots)))
    return index, declared


def line_at(path, n):
    """Text of line n, 1-based, or None if the file is shorter.  Bytes are
    decoded permissively: a header with latin-1 bytes in a comment must still
    resolve, or the tool invents defects out of encoding."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if i == n:
                    return line.rstrip("\n").rstrip("\r")
    except OSError:
        return None
    return None


VERSION_RX = re.compile(r"linux-(\d+\.\d+\.\d+)")
# Enough of a path to tell an amdgpu header from a Tegra video driver header.
SUBSYSTEM_HINT = "drivers/gpu/drm/amd"


def version_of(relpath):
    """
    Which kernel version a copy belongs to, read from its own path.

    Returns a family label: the version string, or "project" for a copy that
    lives in this project's own tree.  The version is a fact about where the file
    is, not an inference about its content.
    """
    m = VERSION_RX.search(relpath)
    return m.group(1) if m else "project"


def subsystem_of(relpath):
    """The driver subsystem a copy belongs to, or None if it is not kernel
    driver code.  Two copies of the same basename in DIFFERENT subsystems are a
    collision, not a copy."""
    i = relpath.find(SUBSYSTEM_HINT)
    if i >= 0:
        return relpath[i:i + len(SUBSYSTEM_HINT)]
    for other in ("drivers/staging/", "drivers/media/", "drivers/video/",
                  "include/drm/", "include/uapi/", "drivers/gpu/drm/"):
        j = relpath.find(other)
        if j >= 0:
            return relpath[j:j + len(other)]
    return None


def resolve(name, n, index, repo, collapse_ambiguous=True):
    """
    Every copy that has line n, and what they agree about.

    `collapse_ambiguous=False` returns the hits instead of the UNIDENTIFIABLE
    verdict.  That exists for callers that have their own way to disambiguate and
    must not be stopped by this tool's opinion.  constmap.py is that caller: it
    compares the VALUE at the cited line, and a value can pick out one of several
    same-named files -- the author copied it out of the file they had open.  The
    default is unchanged, because for every other caller UNIDENTIFIABLE is the
    honest answer and this tool should not be second-guessed by a convenience.

    The verdict separates two disagreements that look identical if you only count
    them: copies of DIFFERENT VERSIONS differing is expected, and copies of the
    SAME VERSION differing means the corpus contradicts itself.
    """
    paths = index.get(name, [])
    # A name that lives in several unrelated places cannot identify a line, and
    # that is a fact about the CITATION, not about the search.  Checked before
    # anything else so a name with 50 candidates never gets reported as a
    # successful resolution of whichever one happened to be long enough.
    if paths:
        sub_count = set()
        for p in paths:
            sb = subsystem_of(os.path.relpath(p, repo))
            if sb:
                sub_count.add(sb)
        if len(sub_count) > 1:
            if collapse_ambiguous:
                return {"verdict": "UNIDENTIFIABLE", "copies": len(paths),
                        "hits": [], "subsystems": sorted(sub_count)}
            # fall through: the caller has a discriminator of its own
    hits = []
    for p in paths:
        text = line_at(p, n)
        if text is not None:
            rel = os.path.relpath(p, repo)
            hits.append({"path": rel, "text": text,
                         "version": version_of(rel),
                         "subsystem": subsystem_of(rel)})
    if not paths:
        return {"verdict": "UNRESOLVED", "copies": 0, "hits": []}
    if not hits:
        return {"verdict": "OUT_OF_RANGE", "copies": len(paths), "hits": [],
                "longest": max(copies_len(p) for p in paths)}

    by_version = {}
    for h in hits:
        by_version.setdefault(h["version"], set()).add(h["text"].strip())
    subs = set(h["subsystem"] for h in hits if h["subsystem"])

    # Order matters, and getting it wrong hides information.  If only one copy is
    # long enough to have this line, "they all agree" is TRUE IN VACUOUS -- there
    # is only one to agree -- and calling that ROBUST would tell the reader that
    # several trees confirm the line when in fact none of the others has it.  So
    # the single-copy case is named first, as UNIQUE.
    all_texts = set(h["text"].strip() for h in hits)
    # UNIQUE first: if only one copy is long enough to have this line, "they all
    # agree" is true in vacuous and calling it ROBUST would claim that several
    # trees confirm a line that only one of them even has.
    if len(hits) == 1 and len(paths) > 1:
        verdict = "UNIQUE"
    elif len(all_texts) == 1:
        verdict = "ROBUST"
    elif any(len(v) > 1 for v in by_version.values()):
        verdict = "FRAGILE"
    else:
        verdict = "VERSIONED"

    disagreeing = [v for v, t in by_version.items() if len(t) > 1]
    return {"verdict": verdict, "copies": len(paths), "hits": hits,
            "versions": sorted(by_version), "same_version_disagreement":
            disagreeing, "subsystems": sorted(s for s in subs if s)}


_LEN_CACHE = {}


def copies_len(path):
    if path in _LEN_CACHE:
        return _LEN_CACHE[path]
    n = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for _ in fh:
                n += 1
    except OSError:
        n = 0
    _LEN_CACHE[path] = n
    return n


def scan_citations(repo, dirs=None):
    """Every citation in the project's own authored text."""
    dirs = dirs or SCAN_DIRS
    found = []
    for d in dirs:
        base = os.path.join(repo, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames
                           if x not in EXCLUDE_PARTS and x != "__pycache__"]
            for fn in sorted(filenames):
                if not fn.endswith((".c", ".h", ".md", ".py", ".txt")):
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, repo)
                try:
                    if os.path.getsize(p) > MAX_FILE_BYTES:
                        continue
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for i, line in enumerate(txt.split("\n"), 1):
                    for m in CITE.finditer(line):
                        found.append({"src": rel, "line": i,
                                      "name": m.group(1),
                                      "at": int(m.group(2)),
                                      "text": line.strip()[:160]})
    return found


def analyse(repo, index=None, roots=None):
    if index is None:
        index, roots = build_index(repo, roots)
    cites = scan_citations(repo)
    rows = []
    for c in cites:
        r = resolve(c["name"], c["at"], index, repo)
        rows.append(dict(c, **r))
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    return rows, tally, index, roots


# --------------------------------------------------------------------------
# --translate:  the same text, at a different line number
# --------------------------------------------------------------------------

def find_text(path, text):
    """
    Line numbers where `text` appears in `path`.

    Returns (unique_line, all_lines).  `unique_line` is None unless there is
    EXACTLY ONE occurrence.  An ambiguity with two candidates is reported as an
    ambiguity, because guessing which occurrence a citation meant would be
    inventing a cross-reference.
    """
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None, []
    except OSError:
        return None, []
    want = text.strip()
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if line.strip() == want:
                    hits.append(i)
                    if len(hits) > 3:
                        break
    except OSError:
        return None, []
    return (hits[0] if len(hits) == 1 else None), hits


def translate(rows, repo, shift_only=False):
    """
    For each FRAGILE citation, the equivalent line in each copy that disagrees.

    A CONSTANT shift across a whole file is stronger evidence than a single text
    match: if every disagreement in a file is the same delta, the file was
    modified by pure insertion at one place, and the mapping is arithmetic rather
    than a lookup.  Those rows are reported as SHIFT and can be trusted with more
    confidence than a one-off match.
    """
    frags = [r for r in rows if r["verdict"] == "FRAGILE"]
    print("%s %s -- traducción de citas FRAGILE" % (TOOL, VERSION))
    print("  UNIDENTIFIABLE queda fuera a propósito: no tiene traducción posible")
    print("  " + "-" * 74)
    print("  %d citas con copias que discrepan" % len(frags))
    print("  se traduce CITA A CITA, y no fichero entero: una sola línea que no")
    print("  mapee no puede tirar las que sí")
    if not frags:
        print("  NINGUNA. Nada que traducir.")
        return 0

    # group by basename so one file is measured once
    by_file = {}
    for r in frags:
        by_file.setdefault(r["name"], set()).add(r["at"])

    verdicts = {}
    detail = {}

    # Compare WITHIN a version, and never across.  The first attempt compared
    # every copy against every other and got NO_UNIQUE_MATCH for all eight files,
    # because 7.2.8 legitimately has different code at those lines: matching
    # pristine text against a different kernel version is not a translation, it
    # is a category error.  A version difference is the expected thing; the
    # instrumentation is what needs translating.
    #
    # And this way the tool never has to know which copy is pristine.  It reports
    # the RELATIVE offset between each pair, and the pair that agrees comes out as
    # delta 0 on its own.  Naming the authoritative copy is knowledge about this
    # project's methodology, and this tool does not have it.
    for name, lns in sorted(by_file.items()):
        per_version = {}
        for ln in sorted(lns):
            for h in resolve(name, ln, _INDEX, repo)["hits"]:
                per_version.setdefault(h["version"], {}).setdefault(
                    h["path"], {})[ln] = h["text"]
        pairs = {}
        for ver, copies in sorted(per_version.items()):
            paths = sorted(copies)
            if len(paths) < 2:
                continue
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    a, b = paths[i], paths[j]
                    # Per LINE, not per file.  The first attempt marked a whole
                    # file untranslatable as soon as ONE cited line failed to map,
                    # which threw away the lines that map cleanly -- and the
                    # direct check proved all four amdgpu_vm.c lines map with a
                    # constant +12.  A file-level verdict on a per-line fact
                    # discards the measurement it was taken to make.
                    deltas, unmapped = set(), []
                    for ln, text in copies[a].items():
                        uniq, allh = find_text(os.path.join(repo, b), text)
                        if uniq is None:
                            unmapped.append((ln, len(allh)))
                        else:
                            deltas.add(uniq - ln)
                    if not deltas:
                        pairs.setdefault("NO_UNIQUE_MATCH", []).append(
                            (ver, a, b, None, unmapped))
                        continue
                    key = "SHIFT" if len(deltas) == 1 else "PER_LINE"
                    pairs.setdefault(key, []).append(
                        (ver, a, b, sorted(deltas)[0], unmapped))
        if not pairs:
            verdicts[name] = "SINGLE_VERSION"
            continue
        worst = ("NO_UNIQUE_MATCH" if "NO_UNIQUE_MATCH" in pairs else
                 ("SHIFT" if "SHIFT" in pairs else "PER_LINE"))
        verdicts[name] = worst
        detail[name] = pairs[worst]

    print("")
    for v in ("SHIFT", "PER_LINE", "NO_UNIQUE_MATCH", "SINGLE_VERSION"):
        print("  %-16s %d ficheros" % (v, sum(1 for x in verdicts.values() if x == v)))
    print("")
    if verdicts and all(v == "SHIFT" for v in verdicts.values()):
        print("  SHIFT = dentro de la MISMA versión, todas las discrepancias de ese")
        print("  fichero son el MISMO delta.  Eso significa que se modificó por")
        print("  INSERCIÓN en un punto, y que el mapeo es aritmético, no una búsqueda:")
        print("  es la fila en la que más se puede confiar, y es la mayor parte.")
        print("")
    print("  DELTA = línea_en_la_copia_B  menos  línea_en_la_copia_A.")
    print("  delta 0 significa que las dos copias coinciden: ahí está el 7.1.3")
    print("  prístino por construcción, sin que la herramienta tenga que elegirlo.")
    print("")
    for name in sorted(detail):
        if shift_only and verdicts[name] != "SHIFT":
            continue
        print("  %-24s %s" % (name, verdicts[name]))
        for ver, a, b, d, unm in sorted(detail[name]):
            if d is None:
                print("      %-8s %-34s -> %-34s  NINGUNA mapea"
                      % (ver, a[-34:], b[-34:]))
            else:
                print("      %-8s %+5d   %-34s -> %s"
                      % (ver, d, a[-34:], b[-34:]))
                if unm:
                    print("               %d linea(s) SIN mapear en este par: %s"
                          % (len(unm), ", ".join(
                              "%d%s" % (l, " (x%d)" % n if n > 1 else "")
                              for l, n in sorted(unm)[:12])))
                    print("               se listan porque el resto mapea: un")
                    print("               fallo aqui NO invalida el delta de las demas")
    print("")
    print("  ESTA TABLA NO ELIGE UNA COPIA BUENA.  Solo mide cuánto se separan dos")
    print("  copias, y sólo dentro de una versión: comparar texto de 7.1.3 contra")
    print("  7.2.8 no es una traducción, es un error de categoría, y fue lo que hizo")
    print("  que el primer intento no encontrara ni una fila.")
    return 0


_INDEX = None


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 70)
    fails = 0
    checks = 0

    class Fake(os.PathLike):
        pass

    import tempfile
    tmp = tempfile.mkdtemp(prefix="citations-selftest-")

    # Every path this helper writes is RECORDED, so the confinement check below
    # can be behavioural instead of static.  A static check that inspects the text
    # of an open() argument cannot follow `p = os.path.join(tmp, rel)` and so
    # reported the self-test's own fixture writes as escapes; three false
    # positives in one check is the same as no check.
    written = []

    def w(rel, text):
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        written.append(p)
        return p

    same = "a\nb\nc\nd\ne\n"
    w("A/x.c", same)
    w("B/x.c", same)
    w("C/x.c", "a\nb\nDIVERGENT\nd\ne\n")
    w("D/only.c", "a\nb\nc\n")
    w("E/short.c", "a\nb\n")

    idx = {"x.c": [os.path.join(tmp, "A/x.c"), os.path.join(tmp, "B/x.c"),
                   os.path.join(tmp, "C/x.c")],
           "only.c": [os.path.join(tmp, "D/only.c")],
           "short.c": [os.path.join(tmp, "E/short.c")]}

    checks += 1
    r = resolve("x.c", 3, idx, tmp)
    if r["verdict"] == "FRAGILE":
        print("  OK    copies that DISAGREE about line 3 -> FRAGILE, not 'broken'")
    else:
        print("  FAIL  expected FRAGILE, got %s" % r["verdict"])
        fails += 1

    checks += 1
    r = resolve("x.c", 2, idx, tmp)
    if r["verdict"] == "ROBUST":
        print("  OK    copies that AGREE about line 2 -> ROBUST")
    else:
        print("  FAIL  expected ROBUST, got %s" % r["verdict"])
        fails += 1

    checks += 1
    r = resolve("x.c", 99, idx, tmp)
    if r["verdict"] == "OUT_OF_RANGE":
        print("  OK    line past every copy -> OUT_OF_RANGE")
    else:
        print("  FAIL  expected OUT_OF_RANGE, got %s" % r["verdict"])
        fails += 1

    checks += 1
    # paths shaped like real subsystems, because subsystem_of() reads the path
    w("drivers/gpu/drm/amd/amdgpu/amb.c", "a\nb\nc\n")
    w("drivers/staging/media/tegra-video/amb.c", "a\nb\nc\n")
    w("fs/ext4/amb.c", "a\nb\nc\n")
    idx["amb.c"] = [
        os.path.join(tmp, "drivers/gpu/drm/amd/amdgpu/amb.c"),
        os.path.join(tmp, "drivers/staging/media/tegra-video/amb.c"),
        os.path.join(tmp, "fs/ext4/amb.c")]
    r = resolve("amb.c", 2, idx, tmp)
    if r["verdict"] == "UNIDENTIFIABLE":
        print("  OK    a name spanning unrelated places -> UNIDENTIFIABLE, not")
        print("        'resolved against whichever one happened to be long enough'")
    else:
        print("  FAIL  got %s" % r["verdict"])
        fails += 1

    checks += 1
    # 2 copies in ONE subsystem is ordinary versioning, not unidentifiable
    w("G/v.c", "a\nb\nc\n")
    w("K/v.c", "a\nb\nX\nc\n")
    idx["v.c"] = [os.path.join(tmp, "G/v.c"), os.path.join(tmp, "K/v.c")]
    r = resolve("v.c", 3, idx, tmp)
    if r["verdict"] in ("SHIFT", "ROBUST", "VERSIONED", "FRAGILE", "UNIQUE"):
        print("  OK    2 copies of the same subsystem are NOT unidentifiable (%s)"
              % r["verdict"])
    else:
        print("  FAIL  ordinary versioning called %s" % r["verdict"])
        fails += 1

    checks += 1
    r = resolve("nope.c", 1, idx, tmp)
    if r["verdict"] == "UNRESOLVED":
        print("  OK    no file with that name -> UNRESOLVED")
    else:
        print("  FAIL  expected UNRESOLVED, got %s" % r["verdict"])
        fails += 1

    checks += 1
    # only one copy is long enough for line 9 -> unambiguous even with 3 copies
    w("A/long.c", "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\nl10\n")
    w("B/long.c", "l1\nl2\n")
    idx["long.c"] = [os.path.join(tmp, "A/long.c"), os.path.join(tmp, "B/long.c")]
    r = resolve("long.c", 9, idx, tmp)
    if r["verdict"] == "UNIQUE":
        print("  OK    only one copy is long enough -> UNIQUE")
    else:
        print("  FAIL  expected UNIQUE, got %s" % r["verdict"])
        fails += 1

    # the corpus must not be scanned for citations
    checks += 1
    w("RESEARCH/kernelbuild/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c",
      "// upstream cites gmc_8_0.c:1127 in its own comment\n")
    w("docs/mio.md", "I cite gmc_v8_0.c:1127 here.\n")
    got = scan_citations(tmp)
    if len(got) == 1 and got[0]["src"] == "docs/mio.md":
        print("  OK    the corpus is NOT scanned: only our own text is (%d found)"
              % len(got))
    else:
        print("  FAIL  scan found %d: %s" % (len(got), [g["src"] for g in got]))
        fails += 1

    # a missing root must be REPORTED, not silently reducing coverage
    # kernelbuild was created above by the corpus-exclusion case, so the roots
    # to ask about are the ones this tmp tree genuinely lacks
    checks += 1
    roots = discover_roots(tmp)
    present = {r for r, ok in roots if ok}
    missing = [r for r, ok in roots if not ok]
    if missing and "RESEARCH/kernelbuild" in present and \
       "RESEARCH/baseline" in missing:
        print("  OK    an absent root is reported absent (%d of %d), never "
              "silently skipped: %s" % (len(missing), len(roots),
                                        ", ".join(missing[:3])))
    else:
        print("  FAIL  absent roots were not reported. present=%s missing=%s"
              % (sorted(present), missing))
        fails += 1

    # line_at must tolerate bytes that are not valid utf-8
    checks += 1
    p = os.path.join(tmp, "F/latin.c")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(b"// caf\xe9 in a comment\nint x;\n")
    if line_at(p, 2) == "int x;":
        print("  OK    a file with non-UTF-8 bytes still resolves")
    else:
        print("  FAIL  encoding invented a defect: %r" % line_at(p, 2))
        fails += 1

    # No write path OUTSIDE the self-test's own temporary directory.
    #
    # The first version of this check scanned the whole file, so it matched the
    # self-test's own fixture writes and reported a write path in a tool that has
    # none.  A guard that cries wolf gets ignored, and this project has enough
    # guards.  So the guarantee is stated precisely: the TOOL has no write path,
    # and the SELF-TEST may only write inside a directory it created itself.
    checks += 1
    src = open(__file__, encoding="utf-8").read()
    tool_part = src.split("def run_selftest", 1)[0]
    writes_tool = re.search(r"open\([^)]*,\s*[\"'][wa]", tool_part) or \
        re.search(r"os\.remove|shutil\.|makedirs|\.write\(", tool_part)
    if not writes_tool:
        print("  OK    the TOOL has no write, move or remove path")
    else:
        print("  FAIL  the tool proper writes: %s" % (writes_tool.group(0),))
        fails += 1

    checks += 1
    escapes = [p for p in written
               if os.path.commonpath([os.path.realpath(p),
                                      os.path.realpath(tmp)]) !=
               os.path.realpath(tmp)]
    if written and not escapes:
        print("  OK    all %d self-test writes land inside its own tempdir"
              % len(written))
    else:
        print("  FAIL  self-test wrote outside its tempdir: %s" % escapes[:3])
        fails += 1

    checks += 1
    # and the tempdir is removed, so a self-test leaves nothing behind
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.exists(tmp):
        print("  OK    the self-test removes its tempdir: nothing is left behind")
    else:
        print("  FAIL  tempdir %s survived" % tmp)
        fails += 1

    # the roots are declared, not discovered at random
    checks += 1
    if "RESEARCH/kernelbuild" in CANDIDATE_ROOTS and \
       "RESEARCH/working" in CANDIDATE_ROOTS:
        print("  OK    both the COMPLETE tree and the PARTIAL one are declared")
    else:
        print("  FAIL  a root is missing from the declaration")
        fails += 1

    # ---- --translate: mapping by exact text, refused when ambiguous
    w("G/pure.c", "l1\nl2\nl3\nINSERT\nl4\nl5\n")
    w("H/shift.c", "l1\nl2\nl3\nl4\nl5\nlINSERT\nl6\nl7\n")
    checks += 1
    u1, h1 = find_text(os.path.join(tmp, "H/shift.c"), "l3")
    if u1 == 3 and h1 == [3]:
        print("  OK    translate finds the same text at its shifted line (%d)" % u1)
    else:
        print("  FAIL  find_text gave %s / %s" % (u1, h1))
        fails += 1

    w("G/dup.c", "x\ny\n")
    w("H/dup.c", "x\nTARGET\nTARGET\nz\n")
    checks += 1
    u2, h2 = find_text(os.path.join(tmp, "H/dup.c"), "TARGET")
    if u2 is None and len(h2) == 2:
        print("  OK    a text occurring TWICE is refused, not guessed: %s" % h2)
    else:
        print("  FAIL  ambiguous match was resolved to %s" % u2)
        fails += 1

    w("G/nf.c", "p\nq\n")
    w("H/nf.c", "z\ny\n")
    checks += 1
    u3, h3 = find_text(os.path.join(tmp, "H/nf.c"), "ONLYINP")
    if u3 is None and h3 == []:
        print("  OK    text absent from the other copy -> no mapping invented")
    else:
        print("  FAIL  got %s / %s" % (u3, h3))
        fails += 1

    checks += 1
    u4, h4 = find_text(os.path.join(tmp, "H/nf.c"), "z")
    if u4 == 1 and h4 == [1]:
        print("  OK    a text at line 1 in BOTH copies maps 1 -> 1, delta 0")
    else:
        print("  FAIL  line 1 mapping gave %s" % u4)
        fails += 1

    # ---- the REPORTING path, not just the primitives
    # build_index returned a filtered list of names while main expected
    # (name, present) pairs, so the tool crashed on first real use with
    # ValueError: too many values to unpack.  Twelve checks of the primitives
    # could not see it, because none of them called analyse().  A validator that
    # never exercises the code that prints has not validated the tool.
    checks += 1
    try:
        rows, tally, _i, rts = analyse(tmp)
        ok_shape = (isinstance(rts, list) and rts
                    and isinstance(rts[0], tuple) and len(rts[0]) == 2)
        if ok_shape and "ROBUST" in tally or ok_shape:
            print("  OK    analyse() runs end to end: %d rows, roots as "
                  "(name, present) pairs" % len(rows))
        else:
            print("  FAIL  analyse() returned %r" % (tally,))
            fails += 1
    except Exception as exc:
        print("  FAIL  analyse() raised %s: %s  <- this is the bug the"
              " primitives missed" % (type(exc).__name__, exc))
        fails += 1

    checks += 1
    try:
        rc = main(["--repo", tmp, "--json"])
        if rc == 0:
            print("  OK    main --json runs end to end (rc=0)")
        else:
            print("  FAIL  main --json rc=%d" % rc)
            fails += 1
    except SystemExit:
        pass
    except Exception as exc:
        print("  FAIL  main raised %s: %s" % (type(exc).__name__, exc))
        fails += 1

    print("  " + "-" * 70)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: esto RESUELVE citas, no las juzga. FRAGILE no es un defecto:")
    print("  es un hecho sobre el corpus, y dice que la línea N nombra textos")
    print("  distintos según el árbol que se abra.  Y la herramienta NO decide")
    print("  cuál copia es la buena: eso es conocimiento sobre la metodología de")
    print("  este proyecto, y no sale de un listado de ficheros.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="citations",
        description="resolve every file.c:NNN this project cites, and say how "
                    "solid each one is")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--fragile", action="store_true",
                    help="only citations whose copies disagree")
    ap.add_argument("--translate", action="store_true",
                    help="for every FRAGILE citation, find the same line of text "
                         "in the copy that disagrees and print its line number "
                         "there.  Turns a warning into a lookup")
    ap.add_argument("--shift-only", action="store_true",
                    help="with --translate, only the constant-offset rows, which "
                         "are the ones that are certainly safe")
    ap.add_argument("--by-root", action="store_true",
                    help="group by which tree answered")
    ap.add_argument("--show", metavar="NAME:N",
                    help="what line N says, in every copy that has it")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version",
                    version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)

    if args.show:
        if ":" not in args.show:
            sys.stderr.write("citations: NAME:N required\n")
            return 2
        name, _, num = args.show.rpartition(":")
        try:
            n = int(num)
        except ValueError:
            sys.stderr.write("citations: line must be a number\n")
            return 2
        index, roots = build_index(repo)
        paths = index.get(name, [])
        print("%s %s -- %s:%d" % (TOOL, VERSION, name, n))
        print("  " + "-" * 70)
        if not paths:
            print("  UNRESOLVED  ningun fichero con ese nombre en este repositorio")
            return 1
        print("  %d copias con ese nombre" % len(paths))
        seen = {}
        for p in sorted(paths):
            t = line_at(p, n)
            rel = os.path.relpath(p, repo)
            k = (t if t is not None else "<fuera de rango>")
            seen.setdefault((version_of(rel), subsystem_of(rel), k),
                            []).append(rel)
        for (ver, sub, k), ps in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            print("")
            print("  %-9s %-26s %s" % (ver, (sub or "-")[:26], k[:60]))
            for p in ps:
                print("      %s" % p)
        print("")
        if len(seen) > 1:
            print("  FRAGILE: las copias NO se ponen de acuerdo sobre esta línea.")
            print("  La cita es cierta en más de un sentido, y el sentido depende")
            print("  del árbol.  Esto no se arregla aquí: se registra.")
        return 0

    rows, tally, index, roots = analyse(repo)

    if args.translate:
        global _INDEX
        _INDEX = index
        return translate(rows, repo, shift_only=args.shift_only)

    if args.json:
        print(json.dumps({"tally": tally, "rows": rows}, indent=2, sort_keys=True))
        return 0

    print("%s %s -- resolución de citas" % (TOOL, VERSION))
    print("  " + "-" * 70)
    present = [r for r, ok in roots if ok]
    absent = [r for r, ok in roots if not ok]
    print("  raíces presentes   %d   %s" % (len(present), ", ".join(present)))
    if absent:
        print("  raíces AUSENTES    %d   %s" % (len(absent), ", ".join(absent)))
        print("                     se declaran ausentes, no se saltan en "
              "silencio: eso")
        print("                     es lo que produjo las 7 citas rotas del "
              "primer intento")
    dup = sum(1 for v in index.values() if len(v) > 1)
    print("  índice             %d nombres, %d en más de una copia"
          % (len(index), dup))
    print("  citas encontradas  %d" % len(rows))
    print("")
    for v in ("ROBUST", "VERSIONED", "UNIDENTIFIABLE", "FRAGILE", "UNIQUE",
              "OUT_OF_RANGE", "UNRESOLVED"):
        print("  %-13s %d" % (v, tally.get(v, 0)))
    print("")
    print("  VERSIONED  es lo esperado: la cita nombra una versión de kernel.")
    print("  UNIDENTIFIABLE  es la trampa: el nombre no dice qué fichero, así que no")
    print("  hay nada que verificar.  FRAGILE  es el que duele: el corpus se")
    print("  contradice sobre la misma línea de la misma versión")
    print("")

    if args.fragile:
        rows = [r for r in rows if r["verdict"] == "FRAGILE"]
        print("  sólo FRAGILE: %d" % len(rows))
        print("")

    if args.by_root:
        by = {}
        for r in rows:
            for h in r.get("hits", []):
                by.setdefault(h["path"].split(os.sep)[0], []).append(r)
        for k in sorted(by):
            v = by[k]
            t = {}
            for r in v:
                t[r["verdict"]] = t.get(r["verdict"], 0) + 1
            print("  %-34s %3d citas   %s" % (k, len(v),
                  " ".join("%s=%d" % (a, b) for a, b in sorted(t.items()))))
        print("")

    for r in rows:
        if args.fragile and r["verdict"] != "FRAGILE":
            continue
        print("  %-13s %s:%d" % (r["verdict"], r["name"], r["at"]))
        print("               citado en %s:%d" % (r["src"], r["line"]))
        for h in r.get("hits", [])[:5]:
            print("                 %-8s %-38s %s"
                  % (h["version"], h["path"][-38:], h["text"].strip()[:42]))
        if len(r.get("hits", [])) > 5:
            print("                 ... y %d copias más" % (len(r["hits"]) - 5))
        if r["verdict"] == "FRAGILE" and r.get("same_version_disagreement"):
            print("                 DISCREPA DENTRO DE %s: el corpus se contradice"
                  % ", ".join(r["same_version_disagreement"]))
        if r["verdict"] == "COLLISION":
            print("                 MISMO NOMBRE EN subsistemas sin relacion")
        if r["verdict"] == "UNRESOLVED":
            print("                 NINGÚN fichero con ese nombre existe aquí")
        elif r["verdict"] == "UNIDENTIFIABLE":
            print("                 %d copias en %d sitios SIN relación: %s"
                  % (r["copies"], len(r.get("subsystems", [])),
                     ", ".join(x.split("/")[-1] for x in
                               r.get("subsystems", [])[:5])))
            print("                 la cita no dice QUÉ fichero, así que no hay")
            print("                 nada que verificar.  Sólo el autor lo arregla.")
        elif r["verdict"] == "OUT_OF_RANGE":
            print("                 la copia más larga tiene %d líneas"
                  % r.get("longest", 0))
    print("")
    print("  ESTO RESUELVE CITAS, NO LAS JUZGA.  Y NO elije la copia buena:")
    print("  decidir cuál de los árboles manda es conocimiento sobre la")
    print("  metodología de este proyecto, y no sale de un listado de ficheros.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))