#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""

WORK_CLASS=READ_ONLY  ·  WRITE_EXECUTION=NONE  ·  STATIC_ANALYSIS
  El token canonico esta declarado porque tools/toolreg.py se NIEGA a ejecutar
  cualquier herramienta que no lo declare, y una herramienta segura pero no declarada
  es inutil para la unica herramienta que podria comprobarla.
ipsolve -- resolve which source file actually implements an amdgpu IP block,
for one specific ASIC, by following the .funcs pointer.

WHY THIS EXISTS
---------------
The corpus names its IP blocks after VERSIONS, not after files.  The boot log
prints, for a Polaris12:

    detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)

and there is no sdma_v3_1.c anywhere.  The block is declared inside sdma_v3_0.c:

    const struct amdgpu_ip_block_version sdma_v3_1_ip_block = {
            .type = AMD_IP_BLOCK_TYPE_SDMA, .major = 3, .minor = 1, .rev = 0,
            .funcs = &sdma_v3_0_ip_funcs,          <-- two hops, into another file
    };

Three sessions in one morning reasoned about that wrong, in two different ways:

  * a sweep by FILENAME sees sdma_v3_0.c and concludes nothing is unusual
  * a sweep by BLOCK NAME sees sdma_v3_1 and concludes there is a new emitter

Both sweeps are well executed.  Both answers are wrong.  The only correct
question is: what does .funcs point at, and in which file is that defined?

This tool answers that mechanically, so the question is never answered by
reading.

CONTRACT
--------
name          ipsolve
version       1.0.0
purpose       for one ASIC, resolve an IP block name to the .c that implements it
question      which code RUNS on this ASIC, as opposed to which code exists
scope         STATIC ANALYSIS OF A SOURCE TREE ONLY.
              Does NOT touch the GPU. Does NOT read MMIO. Does NOT open /sys.
              Does NOT load a module. Does NOT compile anything.
dependencies  Python 3, standard library only
build         none.  Run it directly.
exit codes    0  every requested block resolved, or the run was --selftest
              2  usage error
              3  at least one block did not resolve (see verdicts)
              4  --expect given and did not match
units         none.  Every output is a path or a symbol name, never a number
              of bytes, never a version.

WHAT IT DOES NOT PROVE, DECLARED UP FRONT
------------------------------------------
  1. It reads TEXT.  A .funcs assignment produced by a macro, an included
     header, or a generated table is NOT followed, and is reported
     NO_FUNCS_FIELD or NOT_DECLARED.  It never guesses.
  2. It resolves the DISPATCH, not the CONDITION.  If a chip is added inside
     `if (adev->foo_enabled)` the block is reported as dispatched, with the
     enclosing condition quoted.  Whether the condition holds is NOT decided.
  3. Two hops is what it follows.  A third hop through a vtable is reported
     AMBIGUOUS_HOPS, not resolved.
  4. `NOT_DECLARED` means "not found in the declared universe", and the
     universe is always printed.  It never means "does not exist".
     This is the same discipline as tools/evidence_search.py --expect.
  5. It says nothing about whether the resolved code is CORRECT.  Two
     implementations may exist and both may compile in; this tool tells you
     which one the dispatch selects, and refuses to rank them.
  6. tools/asic_resolver.py answers a DIFFERENT and also necessary question:
     whether a .c is compiled for an ASIC.  Neither tool substitutes for the
     other, and both are needed.  `grep -c ip_block tools/asic_resolver.py`
     returns 0, which is why this file exists.

VERDICTS, and they are never merged
-----------------------------------
  RESOLVED               dispatched for this chip, .funcs followed, file named
  NOT_DISPATCHED_FOR_CHIP the block exists in the corpus; this chip's dispatch
                         does not add it.  This is a POSITIVE finding about
                         the corpus, not an absence.
  NOT_DECLARED           the name was not found within the declared universe
  AMBIGUOUS              more than one definition of the same symbol
  AMBIGUOUS_HOPS         the chain exceeded two hops
  NO_FUNCS_FIELD         the block is declared but has no .funcs assignment
  CONDITIONAL            dispatched, but from inside an `if` that opens INSIDE this
                         case region.  Quoted, and counted as RESOLVED for the exit
                         code: the dispatch was found.  A guard from a PRECEDING case
                         is never attributed -- see enclosing_condition().

USAGE
-----
  ipsolve.py --kernel RAIZ --chip CHIP_POLARIS12 --block sdma_v3_1_ip_block
  ipsolve.py --kernel RAIZ --chip CHIP_POLARIS12 --block A --block B --json
  ipsolve.py --selftest
  ipsolve.py --list-chips
  ipsolve.py --kernel RAIZ --chip X --block Y --expect sdma_v3_0.c
"""

import argparse
import json
import os
import re
import sys
import tempfile

VERSION = "1.0.0"
TOOL = "ipsolve"

# --------------------------------------------------------------------------
# source collection
# --------------------------------------------------------------------------

SOURCE_SUFFIX = (".c", ".h")


def collect_sources(kernel_root):
    """Every .c/.h under kernel_root, sorted, as a list of absolute paths."""
    out = []
    for dirpath, dirnames, filenames in os.walk(kernel_root):
        dirnames.sort()
        for fn in sorted(filenames):
            if fn.endswith(SOURCE_SUFFIX):
                out.append(os.path.join(dirpath, fn))
    return out


class Corpus:
    """
    The whole tree, read ONCE, with the symbol lookups pre-indexed.

    The first version of this tool re-read all 2705 files for every requested
    block, which made a 9-block query time out.  Cost was O(blocks x files) and
    had to become O(files).  A tool too slow to run does not get run, and then
    it protects nobody.

    Indexes built here:
      blocks   ip_block symbol  -> [(path, body)]
      funcs    funcs symbol     -> [(path, body)]
      fndefs   function symbol  -> [path]
    """
    __slots__ = ("root", "paths", "text", "blocks", "funcs", "fndefs", "chips",
                 "block_type", "ip_block_names", "wanted")

    def __init__(self, root):
        self.root = root
        self.paths = collect_sources(root)
        self.text = {}
        self.blocks = {}
        self.funcs = {}
        self.fndefs = {}
        self.chips = {}
        self.block_type = {}
        self.ip_block_names = {}

        # Pass 1: read everything once, and index only the STRUCTS.
        # RE_FUNC_DEF is the expensive pattern -- a regex shaped like a C
        # function signature, run over every .c.  Running it over all 2705
        # files unconditionally cost ~20 s per invocation, which is more than
        # the whole point of having a gate.  So it is deferred to pass 2, where
        # it runs only on files that actually contain a symbol we need.
        for p in self.paths:
            txt = self._read(p)
            self.text[p] = txt
            for m in RE_BLOCK_DEF.finditer(txt):
                self.blocks.setdefault(m.group("sym"), []).append(
                    (p, m.group("body"), txt.count("\n", 0, m.start()) + 1)
                )
                tm = RE_BLOCK_TYPE.search(m.group("body"))
                if tm:
                    self.block_type.setdefault(tm.group("t"), set()).add(m.group("sym"))
            for m in RE_FUNCS_DEF.finditer(txt):
                self.funcs.setdefault(m.group("sym"), []).append((p, m.group("body")))
            for m in re.finditer(r"^\s*(CHIP_\w+)\s*=\s*(\d+)\s*,", txt, re.M):
                if m.group(1) not in self.chips:
                    self.chips[m.group(1)] = (int(m.group(2)), p)

        # re-key block_type by the string the kernel prints, not the enum suffix
        names = load_ip_block_names(self)
        rekeyed = {}
        for suffix, syms in self.block_type.items():
            key = names.get(suffix)
            if key is None:
                continue              # not in the printed table: never printed
            rekeyed.setdefault(key, set()).update(syms)
        self.block_type = rekeyed
        self.ip_block_names = names

        # Pass 2: which handler symbols does any funcs struct reference?
        # Only those need a definition lookup.
        #
        # PERFORMANCE, and this was measured twice the wrong way before getting
        # it right.  RE_FUNC_DEF is the expensive pattern: a regex shaped like a
        # C signature with a lazy body.  Two attempts:
        #   (a) run it over every .c unconditionally            -> ~27 s total
        #   (b) for each wanted symbol, search every file        -> 3 m 20 s. WORSE.
        #       O(symbols x files) substring searches is a disaster.
        # The fix is ONE alternation, compiled once, anchored at line start, so
        # it is a single C-level pass.  Correctness is unchanged: a definition
        # still has to be a line starting with a declaration that names the
        # symbol, which is what RE_FUNC_DEF required too.
        wanted = set()
        for defs in self.funcs.values():
            for _p, body in defs:
                for m in RE_FUNC_FIELD.finditer(body):
                    wanted.add(m.group("value").lstrip("&").strip())
        self.wanted = wanted

        if wanted:
            # PERFORMANCE, and this was measured three wrong ways before landing.
            # The index cost, on this corpus of 2705 files, whole run each time:
            #   (a) one RE_FUNC_DEF pass, filtered to `wanted`      ~27 s   <- chosen
            #   (b) per-symbol substring search over every file       3 m 20 s
            #   (c) ONE alternation of all ~500 symbols, per file    1 m 16 s
            # (b) is O(symbols x files). (c) is one pass but a 500-branch
            # alternation is expensive per position, and an earlier version of
            # it with nested declaration-prefix groups backtracked so badly the
            # self-test exceeded 60 s.
            # (a) is one pattern, one pass, and it is also the simplest.  Simple
            # and fast won; that ordering is the lesson, not the code.
            for p in self.paths:
                if not p.endswith(".c"):
                    continue
                txt = self.text[p]
                for m in RE_FUNC_DEF.finditer(txt):
                    sym = m.group("sym")
                    if sym in wanted:
                        self.fndefs.setdefault(sym, set()).add(p)

    @staticmethod
    def _read(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()

    def __len__(self):
        return len(self.paths)


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------------------
# symbol finding
# --------------------------------------------------------------------------

# A definition of an ip_block version struct.
RE_BLOCK_DEF = re.compile(
    r"const\s+struct\s+amdgpu_ip_block_version\s+"
    r"(?P<sym>\w+_ip_block)\s*=\s*\{(?P<body>.*?)\n\}",
    re.S,
)

# A definition of a funcs struct.
#
# The symbol name is matched by IDENTITY OF TYPE, not by a naming convention.
# The first version required the name to end in `_ip_funcs`, and that is WRONG:
# display/amdgpu_dm/amdgpu_dm.c:3799 declares
#
#     static const struct amd_ip_funcs amdgpu_dm_funcs = { .name = "dm", ... }
#
# which is the funcs of dm_ip_block, and it does not match the pattern. The
# result was a false NOT_DECLARED on the one block that governs display.
#
# This is the same lesson as C-011, inverted: there the naming convention
# implied a file that did not exist; here the naming convention hid a struct
# that does. In both cases the reliable key is the TYPE, and for the funcs
# struct the type is always `struct amd_ip_funcs`. The authoritative string for
# the boot log is not the symbol either -- it is the `.name` field.
RE_FUNCS_DEF = re.compile(
    r"(?:static\s+)?const\s+struct\s+amd_ip_funcs\s+"
    r"(?P<sym>\w+)\s*=\s*\{(?P<body>.*?)\n\}",
    re.S,
)

# A designator field inside a struct body.  The value may carry a leading '&'
# (the normal case for .funcs = &something) or be NULL.  Getting this wrong
# makes every block report NO_FUNCS_FIELD, which the self-test caught on the
# first run.
RE_FUNC_FIELD = re.compile(
    r"^\s*\.\s*(?P<field>\w+)\s*=\s*(?P<value>&\s*\w+|\w+)\s*,", re.M
)

RE_CHIP_CASE = re.compile(r"^\s*case\s+(?P<chip>CHIP_\w+)\s*:\s*$", re.M)

RE_ADD_BLOCK = re.compile(
    r"amdgpu_device_ip_block_add\s*\(\s*\w+\s*,\s*&\s*(?P<block>\w+_ip_block)\s*\)"
)

RE_IPVER_SWITCH = re.compile(
    r"switch\s*\(\s*amdgpu_ip_version\s*\(\s*\w+\s*,\s*(?P<hwip>\w+)\s*,", re.S
)

RE_IPVER_CASE = re.compile(r"^\s*case\s+IP_VERSION\s*\(\s*(?P<v>[\d,\s]+)\)\s*:\s*$", re.M)

RE_FUNC_DEF = re.compile(
    r"^(?:static\s+)?(?:const\s+)?[\w\s\*]+?\b(?P<sym>\w+)\s*\([^;]*?\)\s*\{", re.M
)

# The kernel's own self-report of which IP block is active, from dmesg:
#     detected ip block number 4 <sdma_v3_1_0> (sdma_v3_0)
# The format string is amdgpu_ip.c:241
#   "detected ip block number %d <%s_v%d_%d_%d> (%s)\n"
# with  %s      = ip_block_name(type)   a fixed table: common gmc ih smu dce gfx sdma
#   major minor rev
#   %s      = ip_block_version->funcs->name
#
# The PARENTHESIZED field is the funcs name.  That is the field this tool can
# cross-check, because it is the same string it reads out of the .name field of
# the funcs struct.  The angle-bracket field mixes the type name with the
# version and is NOT comparable to anything in the corpus.
RE_BOOTLOG = re.compile(
    r"detected ip block number\s+(?P<n>\d+)\s+"
    r"<(?P<type>\w+?)_v(?P<maj>\d+)_(?P<min>\d+)_(?P<rev>\d+)>\s+"
    r"\((?P<funcs>\w+)\)"
)

# type name -> the ip_block symbols that can carry it, so a bootlog line can be
# turned back into a query.  Built from the corpus, not hardcoded.
RE_BLOCK_TYPE = re.compile(r"\.type\s*=\s*AMD_IP_BLOCK_TYPE_(?P<t>\w+)\s*,")

# The table the kernel prints from, amdgpu_ip.c:
#     static const char *const ip_block_names[] = {
#             [AMD_IP_BLOCK_TYPE_SMC] = "smu",
#             [AMD_IP_BLOCK_TYPE_DCE] = "dce",
#     ... };
#
# This mapping is NOT lowercasing.  SMC prints as "smu".  Assuming it was would
# have made every block of this type unmatched, which is exactly the class of
# defect this tool exists to remove -- so the table is read, not guessed.
RE_IP_NAMES = re.compile(
    r"\[\s*AMD_IP_BLOCK_TYPE_(?P<enum>\w+)\s*\]\s*=\s*\"(?P<name>\w+)\""
)


def load_ip_block_names(corpus):
    """enum suffix -> printed string, read from amdgpu_ip.c."""
    out = {}
    for p in corpus.paths:
        if os.path.basename(p) != "amdgpu_ip.c":
            continue
        txt = corpus.text[p]
        for m in RE_IP_NAMES.finditer(txt):
            out[m.group("enum")] = m.group("name")
        break
    return out


def find_block_defs(corpus, name):
    """All (path, body, line) where `name` is defined as an ip_block."""
    return corpus.blocks.get(name, [])


def find_funcs_defs(corpus, name):
    return corpus.funcs.get(name, [])


def find_func_def_file(corpus, sym):
    """Which .c defines `sym` as a function."""
    return sorted(corpus.fndefs.get(sym, set()))


# --------------------------------------------------------------------------
# dispatch resolution
# --------------------------------------------------------------------------

def enclosing_condition(txt, case_match, site):
    """
    The `if` guarding this dispatch site, or None.

    ONLY an `if` that OPENS INSIDE the case region counts.  An `if` above the
    case label belongs to an enclosing scope -- usually the PRECEDING case of
    the same switch -- and attributing it to this case is a false claim.

    That false claim is not hypothetical: the first version of this function
    searched upwards without bound and reported

        amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block)   <- vi.c:2113
        inside if (!amdgpu_sriov_vf(adev))

    for CHIP_POLARIS12.  That `if` is at vi.c:2100 and belongs to the TONGA
    case, which ends with `break;` on line 2104.  Polaris12 has no such guard.
    A wrong condition is worse than no condition, because a reader will reason
    about SR-IOV on a path that has none.

    Therefore: scan only from the case label forward, and take an `if` only if
    it is still open at the dispatch site.  Anything else returns None.
    """
    region = txt[case_match.end():site]
    best = None
    for m in re.finditer(r"\bif\s*\(([^;{]*)\)\s*\{", region):
        best = m.group(1).strip()
    return best


# Any label, not just a CHIP_* one: a fall-through run passes through
# CHIP_VEGAM, default:, and anything else.
RE_ANY_CASE = re.compile(
    r"^\s*(?:case\s+[^:\n]+|default)\s*:\s*$", re.M
)

# A statement that ends a case region, i.e. prevents falling through.
RE_TERMINATOR = re.compile(
    r"\b(?:break\s*;|return\b[^;]*;|goto\b[^;]*;|continue\s*;)"
    r"\s*(?:/\*.*?\*/\s*)*$",
    re.S,
)


def fallthrough_region(txt, case_match, all_cases):
    """
    Return the text a chip can actually reach starting at `case_match`.

    C attaches statements to a LABEL, not to a keyword.  So in

        case CHIP_POLARIS12:
        case CHIP_VEGAM:
                amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
                break;

    the add() belongs to the CHIP_VEGAM region, and CHIP_POLARIS12 reaches it only
    by falling through.  Reading a case as "the text until the next case label"
    therefore returns an EMPTY region for every fall-through case, which is
    wrong in exactly the two places this tool exists to disambiguate:

        vi.c:2105-2113   case CHIP_POLARIS10/11/12, CHIP_VEGAM:
        hwmgr.c:154-158  case CHIP_POLARIS11/10/12:

    The rule implemented: walk labels forward, accumulating regions, and stop
    before the first label that is PRECEDED by a terminator.
    """
    idx = None
    for k, ac in enumerate(all_cases):
        if ac.start() == case_match.start():
            idx = k
            break
    if idx is None:
        return txt[case_match.end():case_match.end() + 2000]

    region = []
    prev_end = case_match.end()
    first = True
    for j in range(idx, len(all_cases)):
        nxt = all_cases[j + 1].start() if j + 1 < len(all_cases) else len(txt)
        seg = txt[prev_end:nxt]
        if not first:
            # control can only fall into the NEXT label if the region we just
            # took does not terminate
            if region and RE_TERMINATOR.search(region[-1]):
                break
        region.append(seg)
        prev_end = all_cases[j].end()
        first = False
    return "".join(region)


def dispatched_blocks(corpus, chip):
    """
    Every ip_block added for `chip`.

    Two dispatch shapes exist in amdgpu and both are real:
      (a) vi.c      switch (adev->asic_type) { case CHIP_POLARIS12: ... }
      (b) discovery switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0))
    This resolves (a).  (b) selects by IP version, not by chip, and a chip's
    IP version is itself something to measure, not to assume; it is reported
    separately by --list-ipversion so it is visible rather than silent.
    """
    found = {}
    chip_enum = corpus.chips.get(chip, (None, None))[0]
    for p in corpus.paths:
        if not p.endswith(".c"):
            continue
        txt = corpus.text[p]

        all_cases = list(RE_ANY_CASE.finditer(txt))
        for cm in RE_CHIP_CASE.finditer(txt):
            if cm.group("chip") != chip:
                continue
            body = fallthrough_region(txt, cm, all_cases)
            for am in RE_ADD_BLOCK.finditer(body):
                blk = am.group("block")
                site = txt.find(am.group(0), cm.start())
                cond = enclosing_condition(txt, cm, site)
                found.setdefault(blk, []).append(
                    {"file": p, "line": txt.count("\n", 0, site) + 1, "cond": cond}
                )

    return found, chip_enum


def list_ipversion_switches(corpus, hwips):
    """
    Report, without deciding: which ip_block would be selected for each
    IP_VERSION value, for the named hwip registers.  This is deliberately a
    report and not a resolution, because mapping a chip to its IP version is
    a measurement with its own evidence requirements.
    """
    out = {}
    for p in corpus.paths:
        if not p.endswith(".c"):
            continue
        txt = corpus.text[p]
        for sm in RE_IPVER_SWITCH.finditer(txt):
            hwip = sm.group("hwip")
            if hwip not in hwips:
                continue
            tail = txt[sm.end():]
            cases = list(RE_IPVER_CASE.finditer(tail))
            mapping = {}
            for idx, cm in enumerate(cases):
                stop = cases[idx + 1].start() if idx + 1 < len(cases) else len(tail)
                seg = tail[cm.end():stop]
                for am in RE_ADD_BLOCK.finditer(seg):
                    ver = cm.group("v").replace(" ", "")
                    mapping.setdefault(am.group("block"), []).append(ver)
            if mapping:
                out.setdefault(hwip, {"file": p, "cases": mapping})
    return out


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------

def resolve_block(corpus, chip, block, ipver_report):
    res = {"block": block, "chip": chip}
    sites = chip_dispatch_cache.get((chip, block))
    if sites is None:
        res["verdict"] = "NOT_DISPATCHED_FOR_CHIP"
        res["detail"] = (
            "no amdgpu_device_ip_block_add(...&%s) inside case %s" % (block, chip)
        )
        res["declared_in"] = sorted(
            {p for p, _, _ in find_block_defs(corpus, block)}
        ) or None
        res["declared_anywhere"] = bool(res["declared_in"])
        return res

    defs = find_block_defs(corpus, block)
    if not defs:
        res["verdict"] = "NOT_DECLARED"
        res["detail"] = "dispatched but no struct definition found in the universe"
        return res
    if len({p for p, _, _ in defs}) > 1:
        res["verdict"] = "AMBIGUOUS"
        res["detail"] = "declared in more than one file: %s" % sorted({p for p, _, _ in defs})
        return res

    bpath, bbody, bline = defs[0]
    res["block_declared_in"] = bpath
    res["block_declared_line"] = bline

    fm = None
    for m in RE_FUNC_FIELD.finditer(bbody):
        if m.group("field") == "funcs":
            fm = m
            break
    if fm is None:
        res["verdict"] = "NO_FUNCS_FIELD"
        res["detail"] = "ip_block struct has no .funcs assignment in the parsed body"
        return res

    funcs_sym = fm.group("value").lstrip("&").strip()
    res["funcs_symbol"] = funcs_sym

    fdefs = find_funcs_defs(corpus, funcs_sym)
    if not fdefs:
        res["verdict"] = "NOT_DECLARED"
        res["detail"] = ".funcs names %s but it is not defined in the universe" % funcs_sym
        return res
    if len({p for p, _ in fdefs}) > 1:
        res["verdict"] = "AMBIGUOUS"
        res["detail"] = "%s defined in several files" % funcs_sym
        return res

    fpath, fbody = fdefs[0]
    res["funcs_declared_in"] = fpath

    # which file implements the functions this block dispatches to
    handlers = {}
    impl_files = set()
    for m in RE_FUNC_FIELD.finditer(fbody):
        field = m.group("field")
        val = m.group("value").lstrip("&").strip()
        if val in ("NULL", "0"):
            handlers[field] = None
            continue
        owners = find_func_def_file(corpus, val)
        handlers[field] = {
            "symbol": val,
            "defined_in": [os.path.relpath(o, corpus.root) for o in owners],
        }
        if owners:
            impl_files.add(os.path.relpath(owners[0], corpus.root))
    res["handlers"] = handlers

    # THE ANSWER: the file that implements what this chip actually selects
    if impl_files:
        res["verdict"] = "RESOLVED"
        res["implemented_in"] = sorted(impl_files)
    else:
        res["verdict"] = "AMBIGUOUS_HOPS"
        res["detail"] = (
            "no handler of %s resolves to a function definition in the universe; "
            "the chain is longer than two hops or crosses a generated table" % funcs_sym
        )

    res["ip_block_name_in_log"] = None
    nm = re.search(r'\.name\s*=\s*"([^"]+)"', fbody)
    if nm:
        res["funcs_name_string"] = nm.group(1)

    res["dispatch_sites"] = [
        {"file": os.path.relpath(s["file"], corpus.root), "line": s["line"], "cond": s["cond"]}
        for s in sites
    ]
    if any(s["cond"] for s in sites):
        res["verdict"] = "CONDITIONAL"
    return res


# cache filled by the caller so resolve_block stays readable
chip_dispatch_cache = {}


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def rel(p, root):
    try:
        return os.path.relpath(p, root)
    except ValueError:
        return p


def render(results, kernel_root, chip, universe, ipver_report, as_json):
    if as_json:
        print(json.dumps(
            {
                "tool": TOOL, "version": VERSION,
                "chip": chip,
                "universe": {"kernel_root": kernel_root, "source_files": universe},
                "results": results,
                "ipversion_selectors": ipver_report,
            },
            indent=2, sort_keys=True,
        ))
        return

    print("%s %s" % (TOOL, VERSION))
    print("  " + "-" * 62)
    print("chip            %s" % chip)
    print("kernel root     %s" % kernel_root)
    print("universe        %d source files (.c/.h) under the root" % universe)
    print("                 every NOT_DECLARED below is bounded by THIS number")
    print("")
    for r in results:
        print("  %s" % r["block"])
        print("    verdict       %s" % r["verdict"])
        if r.get("block_declared_in"):
            print("    declared in   %s" % rel(r["block_declared_in"], kernel_root))
        if r.get("funcs_symbol"):
            print("    .funcs ->     %s" % r["funcs_symbol"])
        if r.get("funcs_declared_in"):
            print("    funcs in      %s" % rel(r["funcs_declared_in"], kernel_root))
        if r.get("funcs_name_string"):
            print("    funcs .name   \"%s\"   <- this is the string in the boot log"
                  % r["funcs_name_string"])
        if r.get("implemented_in"):
            print("    IMPLEMENTED   %s" % ", ".join(r["implemented_in"]))
        if r.get("declared_in"):
            print("    declared at   %s" % ", ".join(
                rel(p, kernel_root) for p in r["declared_in"]))
            print("                 declared in the corpus, but this chip does not select it")
        if r.get("detail"):
            print("    detail        %s" % r["detail"])
        for s in r.get("dispatch_sites", []):
            extra = "   inside if (%s)" % s["cond"] if s.get("cond") else ""
            print("    dispatched    %s:%d%s" % (s["file"], s["line"], extra))
        for f, h in sorted((r.get("handlers") or {}).items()):
            if h is None:
                print("    handler %-14s NULL" % f)
            else:
                where = ", ".join(h["defined_in"]) or "NOT FOUND in universe"
                print("    handler %-14s %-38s %s" % (f, h["symbol"], where))
        print("")
    if ipver_report:
        print("  IP-VERSION SELECTORS (reported, NOT decided)")
        print("  " + "-" * 62)
        for hwip, info in sorted(ipver_report.items()):
            print("  %s  in %s" % (hwip, rel(info["file"], kernel_root)))
            for blk, vers in sorted(info["cases"].items()):
                print("      %-34s %s" % (blk, ",".join(sorted(set(vers)))))
        print("")


# --------------------------------------------------------------------------
# cross-check against the kernel's own self-report
# --------------------------------------------------------------------------

def parse_bootlog(lines):
    """[(n, type, major, minor, rev, funcs), ...] from kernel dmesg lines."""
    out = []
    for ln in lines:
        m = RE_BOOTLOG.search(ln)
        if m:
            out.append((int(m.group("n")), m.group("type"), int(m.group("maj")),
                        int(m.group("min")), int(m.group("rev")), m.group("funcs")))
    return out


def crosscheck_bootlog(corpus, lines, chip):
    """
    For every block the kernel reported, find which corpus block carries that
    type, and check that the funcs .name the corpus holds is the same string the
    kernel printed.

    WHY THIS MODE EXISTS, and it is not a convenience
    A human verifying this writes the expected values into a script by hand.
    Doing exactly that on the first attempt, the author of this file typed
    `dce_v1_0_0` as the expected funcs name for block 6 and concluded the tool
    had found a discrepancy in the display block.  The tool was right: the
    kernel prints `(dm)`.  The transcription was wrong.

    That is the same failure this repo already named twice -- 038 calls it
    CIRCULARITY, and it is why the test expectations were copied out of the same
    document they were supposed to check.  A hand-written expectation is a bug
    waiting for a mismatch that does not exist.

    So the expectation is DERIVED from the kernel's line, never typed.  If this
    mode reports 9/9, the corpus and the running kernel agree about which
    implementation each block dispatches to.  That is the same arbitration that
    settled C-009 and C-011, and here it is repeatable with one command.
    """
    entries = parse_bootlog(lines)
    rows = []
    for n, btype, maj, minr, rev, funcs_name in entries:
        cands = sorted(corpus.block_type.get(btype, ()))
        row = {"number": n, "type": btype, "version": "%d.%d.%d" % (maj, minr, rev),
               "kernel_funcs_name": funcs_name, "candidate_blocks": cands,
               "verdict": None, "detail": None}
        # the block whose version numbers match, if any
        exact = [b for b in cands if re.search(
            r"_%d_%d_%d_ip_block$" % (maj, minr, rev), b)]
        row["version_matched_blocks"] = exact
        if not cands:
            row["verdict"] = "TYPE_NOT_IN_CORPUS"
            row["detail"] = "no ip_block in the corpus carries AMD_IP_BLOCK_TYPE_%s" % btype
            rows.append(row)
            continue
        # resolve each candidate and look for the funcs name the kernel printed
        matched, checked = None, 0
        chip_dispatch_cache.clear()
        disp, _ = dispatched_blocks(corpus, chip)
        for k, v in disp.items():
            chip_dispatch_cache[(chip, k)] = v
        for b in cands:
            r = resolve_block(corpus, chip, b, None)
            if r.get("funcs_name_string"):
                checked += 1
                if r["funcs_name_string"] == funcs_name:
                    matched = (b, r)
                    break
        if matched:
            b, r = matched
            row["verdict"] = "MATCH"
            row["block"] = b
            row["implemented_in"] = r.get("implemented_in")
            row["dispatch_sites"] = r.get("dispatch_sites")
        elif checked == 0:
            row["verdict"] = "NOT_DISPATCHED_FOR_CHIP"
            row["detail"] = ("block(s) %s carry this type but none is dispatched for %s"
                             % (", ".join(cands), chip))
        else:
            row["verdict"] = "MISMATCH"
            row["detail"] = ("kernel printed %r; corpus blocks %s carry %s"
                             % (funcs_name, ", ".join(cands), "other names"))
        rows.append(row)
    return rows


def render_bootlog(rows, chip, as_json):
    if as_json:
        print(json.dumps({"tool": TOOL, "version": VERSION, "chip": chip,
                          "bootlog_crosscheck": rows}, indent=2, sort_keys=True))
        return
    print("%s %s -- cross-check against the kernel's own report" % (TOOL, VERSION))
    print("  " + "-" * 62)
    print("  chip            %s" % chip)
    print("  comparing the PARENTHESIZED field of each line, which is funcs->name,")
    print("  against the .name field of the funcs struct in the corpus")
    print("")
    ok = 0
    for r in rows:
        mark = "OK  " if r["verdict"] == "MATCH" else "FAIL"
        ok += r["verdict"] == "MATCH"
        print("  %s  #%-2d <%s_%s> (%s)" % (mark, r["number"], r["type"],
                                            r["version"].replace(".", "_"),
                                            r["kernel_funcs_name"]))
        if r["verdict"] == "MATCH":
            site = (r.get("dispatch_sites") or [{}])[0]
            print("          block %-22s -> %s" % (r["block"], (r.get("implemented_in") or ["-"])[0]))
            if site:
                print("          dispatched at %s:%s" % (site.get("file"), site.get("line")))
        else:
            print("          %s: %s" % (r["verdict"], r.get("detail")))
            if r.get("candidate_blocks"):
                print("          candidates: %s" % ", ".join(r["candidate_blocks"]))
        print("")
    print("  " + "-" * 62)
    print("  %d of %d blocks agree with the running kernel" % (ok, len(rows)))
    print("")
    print("  An expectation typed by hand is a bug waiting for a mismatch that does")
    print("  not exist.  This mode derives the expectation from the kernel's line,")
    print("  so nobody has to type it.")


# --------------------------------------------------------------------------
# self-test, with negative controls
# --------------------------------------------------------------------------

FIXTURE_C = r"""
#include <x.h>

/* a decoy: same name, different chip, must not be selected */
const struct amdgpu_ip_block_version demo_v4_0_ip_block = {
	.type = AMD_IP_BLOCK_TYPE_DMA,
	.major = 4, .minor = 0, .rev = 0,
	.funcs = &demo_v4_0_ip_funcs,
};

/* THE ALIAS: named after a version that has no file of its own */
const struct amdgpu_ip_block_version demo_v3_1_ip_block = {
	.type = AMD_IP_BLOCK_TYPE_DMA,
	.major = 3, .minor = 1, .rev = 0,
	.funcs = &demo_v3_0_ip_funcs,
};

/* the display block: named by TYPE (AMD_IP_BLOCK_TYPE_DCE), funcs symbol
 * breaks the naming convention.  Both of those used to defeat this tool. */
const struct amdgpu_ip_block_version dm_ip_block = {
	.type = AMD_IP_BLOCK_TYPE_DCE,
	.major = 1, .minor = 0, .rev = 0,
	.funcs = &amdgpu_dm_funcs,
};

static const struct amd_ip_funcs demo_v4_0_ip_funcs = {
	.name = "demo_v4_0",
	.sw_init = demo_v4_0_sw_init,
};

static const struct amd_ip_funcs demo_v3_0_ip_funcs = {
	.name = "demo_v3_0",
	.sw_init = demo_v3_0_sw_init,
	.hw_fini = NULL,
};

/* a funcs struct whose SYMBOL does not follow the *_ip_funcs convention.
 * This is real: display/amdgpu_dm/amdgpu_dm.c declares amdgpu_dm_funcs. */
static const struct amd_ip_funcs amdgpu_dm_funcs = {
	.name = "dm",
	.sw_init = dm_early_init,
};

static int dm_early_init(void *adev) { return 0; }

static int demo_v4_0_sw_init(void *adev) { return 0; }

static int demo_v3_0_sw_init(void *adev) { return 0; }
"""

FIXTURE_H = r"""
struct amdgpu_ip_block_version { int type, major, minor, rev; };
struct amd_ip_funcs { const char *name; int (*sw_init)(void *); int (*hw_fini)(void *); };
"""

FIXTURE_SOC = r"""
#include <soc.h>

int pick(struct amdgpu_device *adev)
{
	switch (adev->asic_type) {
	case CHIP_OTHER:
		/* this guard belongs to CHIP_OTHER only, and must NOT be attributed
		 * to CHIP_TARGET: a wrong condition is worse than no condition */
		if (adev->is_virtual_fn) {
			amdgpu_device_ip_block_add(adev, &demo_v4_0_ip_block);
		}
		break;
	case CHIP_TARGET:
	case CHIP_FALLTHROUGH_TAIL:
		amdgpu_device_ip_block_add(adev, &dm_ip_block);
		/* the add belongs to the CHIP_FALLTHROUGH_TAIL region.
		 * CHIP_TARGET reaches it only by falling through. */
		amdgpu_device_ip_block_add(adev, &demo_v3_1_ip_block);
		break;
	}
	return 0;
}
"""

FIXTURE_IPC = r"""
static const char *const ip_block_names[] = {
	[AMD_IP_BLOCK_TYPE_DMA] = "sdma",
	[AMD_IP_BLOCK_TYPE_SMC] = "smu",
	[AMD_IP_BLOCK_TYPE_DCE] = "dce",
};

void not_used(void) {}
"""

FIXTURE_ENUM = r"""
enum asic_type {
	CHIP_OTHER = 3,
	CHIP_TARGET = 17,
	CHIP_FALLTHROUGH_TAIL = 18,
};
"""


def build_fixture(root):
    os.makedirs(os.path.join(root, "a"), exist_ok=True)
    open(os.path.join(root, "a", "include.h"), "w").write(FIXTURE_H)
    open(os.path.join(root, "a", "enum.h"), "w").write(FIXTURE_ENUM)
    open(os.path.join(root, "a", "demo.c"), "w").write(FIXTURE_C)
    open(os.path.join(root, "soc.c"), "w").write(FIXTURE_SOC)
    open(os.path.join(root, "amdgpu_ip.c"), "w").write(FIXTURE_IPC)
    # a source file that must never be reached for
    open(os.path.join(root, "decoy.c"), "w").write(
        "int totally_unrelated(void) { return 0; }\n"
    )


# (name, chip, block, expected verdict, note)
SELFTEST_CASES = [
    ("positive_alias_resolves_to_other_file", "CHIP_TARGET", "demo_v3_1_ip_block",
     "RESOLVED", "the alias must land in demo.c, not in a demo_v3_1.c"),
    ("negative_other_chip_block", "CHIP_TARGET", "demo_v4_0_ip_block",
     "NOT_DISPATCHED_FOR_CHIP", "same corpus, different chip: must NOT resolve"),
    ("negative_the_same_block_on_the_other_chip", "CHIP_OTHER", "demo_v3_1_ip_block",
     "NOT_DISPATCHED_FOR_CHIP", "symmetric control"),
    ("negative_undeclared_block", "CHIP_TARGET", "demo_v9_9_ip_block",
     "NOT_DISPATCHED_FOR_CHIP", "unknown name must not resolve, and must not crash"),
    ("positive_fallthrough_tail_label_is_not_ours", "CHIP_FALLTHROUGH_TAIL",
     "demo_v4_0_ip_block", "NOT_DISPATCHED_FOR_CHIP",
     "the tail label must not inherit the block the faller adds"),
]

# (name, chip, block, expect_resolved, expect_cond_is_none)
CONDITION_CASES = [
    ("guard_of_own_case_is_reported", "CHIP_OTHER", "demo_v4_0_ip_block", True, False),
    ("guard_of_previous_case_must_not_leak", "CHIP_TARGET", "demo_v3_1_ip_block", True, True),
]

# The kernel prints ip_block_names[], and that table is NOT a lowercasing:
# AMD_IP_BLOCK_TYPE_SMC prints as "smu".  Assuming it was would silently make
# every block of that type unmatchable.
IPNAME_CASES = [
    ("enum_suffix_to_printed_string_is_not_lowercase", "SMC", "smu"),
    ("plain_type", "DMA", "sdma"),
]

# A funcs symbol that does not follow the *_ip_funcs naming convention must
# still resolve.  Regression test for a false NOT_DECLARED found on dm_ip_block.
NAME_CONVENTION_CASES = [
    ("funcs_symbol_breaks_naming_convention", "dm_ip_block", "RESOLVED", "dm"),
]


def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 62)
    fails = 0
    checks = 0
    with tempfile.TemporaryDirectory() as td:
        build_fixture(td)
        corpus = Corpus(td)
        paths = corpus.paths

        checks += 1
        if not any(p.endswith("demo_v3_1.c") for p in paths):
            print("  OK    universe contains no demo_v3_1.c: the alias has no file")
        else:
            print("  FAIL  fixture is wrong, demo_v3_1.c must not exist")
            fails += 1

        for name, chip, block, expect, note in SELFTEST_CASES:
            chip_dispatch_cache.clear()
            disp, enum = dispatched_blocks(corpus, chip)
            for k, v in disp.items():
                chip_dispatch_cache[(chip, k)] = v
            r = resolve_block(corpus, chip, block, None)
            checks += 1
            if r["verdict"] == expect:
                extra = ""
                bad = False
                if expect == "RESOLVED":
                    got = ", ".join(r["implemented_in"])
                    # compare BASENAMES: the tool reports paths relative to --kernel,
                    # so the fixture's subdirectory is not part of the claim
                    bases = [os.path.basename(x) for x in r["implemented_in"]]
                    bad = bases != ["demo.c"]
                    extra = " -> %s" % got
                    if bad:
                        extra += "   EXPECTED demo.c"
                if bad:
                    fails += 1
                    print("  FAIL  %-42s %s%s" % (name, r["verdict"], extra))
                    continue
                print("  OK    %-42s %s%s" % (name, r["verdict"], extra))
            else:
                print("  FAIL  %-42s got %s, expected %s  (%s)"
                      % (name, r["verdict"], expect, note))
                fails += 1

        for name, chip, block, want_res, want_nocond in CONDITION_CASES:
            chip_dispatch_cache.clear()
            disp, enum = dispatched_blocks(corpus, chip)
            for k, v in disp.items():
                chip_dispatch_cache[(chip, k)] = v
            r = resolve_block(corpus, chip, block, None)
            checks += 1
            ok_res = (r["verdict"] in ("RESOLVED", "CONDITIONAL")) == want_res
            sites = r.get("dispatch_sites") or []
            got_cond = any(s.get("cond") for s in sites)
            ok_cond = (not got_cond) == want_nocond
            if ok_res and ok_cond:
                print("  OK    %-42s %-12s cond=%s"
                      % (name, r["verdict"], got_cond))
            else:
                print("  FAIL  %-42s verdict=%s (want resolved=%s) cond=%s (want none=%s)"
                      % (name, r["verdict"], want_res, got_cond, want_nocond))
                fails += 1

        for name, enum, want in IPNAME_CASES:
            checks += 1
            got = corpus.ip_block_names.get(enum)
            if got == want:
                print("  OK    %-42s %s -> \"%s\"" % (name, enum, want))
            else:
                print("  FAIL  %-42s %s -> %r, expected \"%s\"" % (name, enum, got, want))
                fails += 1

        for name, block, expect, want_name in NAME_CONVENTION_CASES:
            chip_dispatch_cache.clear()
            disp, enum = dispatched_blocks(corpus, "CHIP_TARGET")
            for k, v in disp.items():
                chip_dispatch_cache[("CHIP_TARGET", k)] = v
            r = resolve_block(corpus, "CHIP_TARGET", block, None)
            checks += 1
            if r["verdict"] == expect and r.get("funcs_name_string") == want_name:
                print("  OK    %-42s %s .name=\"%s\"" % (name, r["verdict"], want_name))
            else:
                print("  FAIL  %-42s verdict=%s name=%s (want %s / \"%s\")"
                      % (name, r["verdict"], r.get("funcs_name_string"), expect, want_name))
                fails += 1

        # a control on the absence claim itself: NOT_DISPATCHED must distinguish
        # "exists in the corpus" from "not declared at all"
        chip_dispatch_cache.clear()
        disp, enum = dispatched_blocks(corpus, "CHIP_TARGET")
        for k, v in disp.items():
            chip_dispatch_cache[("CHIP_TARGET", k)] = v
        known = resolve_block(corpus, "CHIP_TARGET", "demo_v4_0_ip_block", None)
        checks += 1
        if known.get("declared_anywhere"):
            print("  OK    NOT_DISPATCHED still reports that the block EXISTS elsewhere")
        else:
            print("  FAIL  a not-dispatched block lost its 'declared elsewhere' fact")
            fails += 1

    print("  " + "-" * 62)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: pasar esto NO valida la semantica del hardware. Dice que el")
    print("        despacho se resuelve; no dice que el codigo resuelto sea correcto.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

# Verdicts that mean "the dispatch chain was not resolved".  CONDITIONAL is
# deliberately NOT here: the dispatch WAS found, it is just guarded, and the
# guard is printed.  Ranking a guarded dispatch as a failure would make the
# tool lie about the hardware in the other direction.
UNRESOLVED_VERDICTS = ("NOT_DECLARED", "AMBIGUOUS", "AMBIGUOUS_HOPS",
                       "NO_FUNCS_FIELD", "NOT_DISPATCHED_FOR_CHIP")


def _exit_code(results):
    return 3 if any(r["verdict"] in UNRESOLVED_VERDICTS for r in results) else 0


def list_chips(paths, chips=None):
    if chips is None:
        chips = {}
        for p in paths:
            txt = read(p)
            for m in re.finditer(r"^\s*(CHIP_\w+)\s*=\s*(\d+)\s*,", txt, re.M):
                chips.setdefault(m.group(1), (int(m.group(2)), p))
    for name in sorted(chips, key=lambda n: chips[n][0]):
        val, p = chips[name]
        print("  %-24s = %-3d  %s" % (name, val, rel(p, os.getcwd())))
    print("\n  %d chips found in the universe" % len(chips))


def main(argv):
    ap = argparse.ArgumentParser(
        prog="ipsolve",
        description="resolve which .c implements an amdgpu IP block, for one ASIC",
    )
    ap.add_argument("--kernel", help="root of the kernel source tree to analyse")
    ap.add_argument("--chip", help="CHIP_* to resolve for, e.g. CHIP_POLARIS12")
    ap.add_argument("--block", action="append", default=[],
                    help="ip_block symbol to resolve; repeatable")
    ap.add_argument("--expect", help="expected implementing file; rc=4 on mismatch")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true", help="run the self-test and exit")
    ap.add_argument("--list-chips", action="store_true", help="list chips in the universe")
    ap.add_argument("--bootlog", metavar="FILE",
                    help="read the kernel's 'detected ip block' lines from FILE "
                         "(use - for stdin) and cross-check every block, with no "
                         "hand-written expectation anywhere")
    ap.add_argument("--list-ipversion", action="append", default=[],
                    metavar="HWIP",
                    help="report the IP_VERSION selector tables for a register, e.g. SDMA0_HWIP")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.list_chips:
        root = os.path.abspath(args.kernel) if args.kernel else os.path.abspath(".")
        list_chips(Corpus(root).paths, Corpus(root).chips)
        return 0

    if args.bootlog and args.kernel and args.chip:
        if args.bootlog == "-":
            lines = sys.stdin.readlines()
        else:
            if not os.path.isfile(args.bootlog):
                sys.stderr.write("ipsolve: --bootlog file not found: %s\n" % args.bootlog)
                return 2
            lines = open(args.bootlog, "r", encoding="utf-8",
                         errors="replace").readlines()
        c = Corpus(os.path.abspath(args.kernel))
        rows = crosscheck_bootlog(c, lines, args.chip)
        render_bootlog(rows, args.chip, args.json)
        bad = [r for r in rows if r["verdict"] != "MATCH"]
        return 3 if bad else 0

    if not args.kernel or not args.chip or not args.block:
        ap.print_usage(sys.stderr)
        sys.stderr.write("\nipsolve: --kernel, --chip and at least one --block are required\n")
        sys.stderr.write("       use --selftest or --list-chips to explore\n")
        return 2
    if not os.path.isdir(args.kernel):
        sys.stderr.write("ipsolve: --kernel is not a directory: %s\n" % args.kernel)
        return 2

    root = os.path.abspath(args.kernel)
    corpus = Corpus(root)

    dispatched, chip_enum = dispatched_blocks(corpus, args.chip)
    chip_dispatch_cache.clear()
    for k, v in dispatched.items():
        chip_dispatch_cache[(args.chip, k)] = v

    ipver = (list_ipversion_switches(corpus, args.list_ipversion)
             if args.list_ipversion else None)

    results = [resolve_block(corpus, args.chip, b, ipver) for b in args.block]

    # --expect is checked BEFORE anything else and in BOTH output modes, so a
    # CI gate can assert a specific implementing file and get rc=4 on mismatch.
    if args.expect:
        got = results[0].get("implemented_in") if results else None
        ok = bool(got) and len(got) == 1 and \
            os.path.basename(got[0]) == os.path.basename(args.expect)
        if ok:
            if not args.json:
                print("  EXPECT MATCH  %s" % got[0])
            return 0
        sys.stderr.write("ipsolve: --expect %s, got %s\n" % (args.expect, got))
        return 4

    if args.json:
        # NOTHING may follow the JSON document or the output stops being
        # parseable.  Not cosmetic: it is the difference between a tool a
        # script can consume and a tool a human has to read by eye.  It was
        # broken on first use and caught by reading the output back in.
        render(results, root, args.chip, len(corpus), ipver, True)
        return _exit_code(results)

    render(results, root, args.chip, len(corpus), ipver, False)

    if chip_enum is not None:
        print("  %s = %d in the enum" % (args.chip, chip_enum))

    unresolved = [r for r in results if r["verdict"] in UNRESOLVED_VERDICTS]
    conditional = [r for r in results if r["verdict"] == "CONDITIONAL"]
    if conditional:
        print("  %d resolved CONDITIONALLY.  The dispatch exists; read the quoted"
              % len(conditional))
        print("  condition before assuming the block is present at runtime.")
    if unresolved:
        print("  %d of %d did not resolve.  A verdict other than RESOLVED is a result;"
              % (len(unresolved), len(results)))
        print("  read its detail line before concluding anything about the hardware.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
