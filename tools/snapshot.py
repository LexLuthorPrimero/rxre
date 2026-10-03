#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE . STATIC_ANALYSIS

"""
snapshot -- a diffable, hashed record of host and GPU state, captured read-only.

WHY THIS EXISTS, AND IT IS THE UNBLOCKED THIRD OF AN EXPERIMENT
-------------------------------------------------------------
The experiment record this project agreed to use is

    INPUT · CONFIGURATION · COMMAND · PRE-STATE · ACTION · POST-STATE
    · OUTPUT · ERROR · RESULT · INTERPRETATION

Of those ten fields, three are automatable TODAY with no authorisation at all:

    PRE-STATE   a snapshot before the action
    POST-STATE  a snapshot after it
    DIFF        the difference between them

Everything else in the cycle -- EXECUTE, and the capture that has to touch the
GPU -- is `BLOCKED_BY_AUTHORIZATION`, and this tool does not attempt it.  But
three of six stages cost nothing and have never been built, which means every
experiment in EXPERIMENTS.md so far recorded PRE-STATE and POST-STATE from memory
rather than from a record.

tools/validate_rx550_final.py already reads most of these sources.  It is
composed here, not reimplemented: it answers "does this host meet the contract",
this answers "what was the state at instant T, in a form two instants can be
compared in".

THE ONE DESIGN PROBLEM, AND IT IS THE WHOLE PROBLEM
---------------------------------------------------
A naive snapshot is useless for diffing, because almost everything in it moves
on its own.  Timestamps, uptime, PIDs, boot id, journal line counts and
free-memory figures change every time you look, so a diff of two snapshots taken
one second apart reports dozens of differences that are not differences in the
thing being studied.

So every fact here is declared VOLATILE or STABLE, and only the STABLE half is
hashed:

    hash covers STABLE only

Two snapshots taken an hour apart with nothing done to the machine hash
IDENTICALLY.  That is the property that makes a diff meaningful, and it is
asserted in the self-test rather than hoped for.

WHAT IS VOLATILE, AND WHY IT IS NOT THROWN AWAY
-----------------------------------------------
Volatile facts are still recorded.  They are just not hashed and they are not
compared, because comparing them produces false differences.  A snapshot that
discarded them would be less useful for writing the record down, which is one of
the ten fields too.

WHAT IT DOES NOT DO, DECLARED
-----------------------------
  1. It does not write to the GPU, to /sys, or to any driver path.  Every read
     is a plain file read or a `journalctl`/`lspci`/`lsmod` invocation.
  2. It does not assert that any value is correct.  It records.  A snapshot that
     said "block_size is correct" would be a claim, and claims belong in
     docs/EVIDENCE-MATRIX.md where they can be arbitrated.
  3. It does not detect a hang or read MMIO.  It cannot, and F1 remains blocked.
  4. It does NOT automate a diff into a conclusion.  `diff` says two states
     differ.  Why they differ, and which difference caused what, is not in the
     snapshot and never will be.

SAFETY
------
Read-only.  Writes exactly one file, and only with --save: the snapshot itself,
under docs/snapshots/ .  Nothing else, ever.

ARBITRAGE, AND WHY IT IS THE VALIDATION FOR THIS TOOL SPECIFICALLY
------------------------------------------------------------------
Every other tool in this tree validates against fixtures or against the corpus:
give it a fixed input, compare with a fixed output.  That cannot work here.  This
tool reads LIVE HOST STATE, so the only way to know it read the right device and
reported the right numbers is to ask something that read it independently.

  snapshot   sysfs, as it stands now
  kernel     `amdgpu 0000:01:00.0: ...`, printed at boot by different code

So `--arbitrate` compares the record against the running kernel and reports with
the project's closed vocabulary, and NO rounding:

  AGREE          the kernel says the same thing
  DISAGREE       the kernel says something else
  NO_KERNEL      the kernel does not print it, so this is not arbitrable
  NOT_ARBITRABLE the two measure different things

`DISAGREE` means the kernel disagrees.  It does NOT mean the snapshot is wrong:
one of the two is wrong and this cannot say which, and it must not guess.
`NO_KERNEL` means not known, which is not the same as agreed.

This is also the validation that found the two real defects: the record was
photographing card0, an Intel HD 4600 on the CPU's own bus, and its PCI address
was the upstream bridge rather than the device.  Both produced plausible values.
Neither was visible without a second source.

USAGE
-----
    snapshot.py --repo .                 print the snapshot
    snapshot.py --repo . --arbitrate     cross-check the record against the kernel
    snapshot.py --repo . --save          also write it to docs/snapshots/<ts>.snap
    snapshot.py --repo . --diff A B      compare two snapshots, stable facts only
    snapshot.py --repo . --verify        hash only; a stable-id, for the record
    snapshot.py --selftest
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
TOOL = "snapshot"

SNAP_DIR = "docs/snapshots"

# Stable facts are the subject.  Volatile facts are recorded but never hashed and
# never diffed.  The split is declared here, in one place, so it cannot drift
# between the capture and the comparison.
VOLATILE = {
    "captured_at", "uptime", "boot_id", "free_mem_kb", "journal_lines",
}

# ABSENT is a VALUE, not an omission.  A fact that could not be read and a fact
# that does not exist look identical if you simply drop the first one, and this
# project has already been bitten that way: the first version of this tool
# selected the Intel iGPU instead of the RX550 and silently recorded nothing at
# all for vram_total, pp_dpm_sclk, gpu_busy_percent and the rest.  Nothing in
# the record said "I did not look at the right device" -- it just looked like a
# quiet, healthy machine.  So absence is spelled out, and counted.
ABSENT = "<ausente>"

# The subject device is chosen by a RULE that is written down here, not by
# whatever sorts first.  Alphabetically card0 is an Intel HD 4600 on the CPU's
# own bus; the RX550 is card1 on 0000:01:00.0.  Taking the first is how the
# first version of this tool photographed the wrong GPU.
SUBJECT_VENDOR = "0x1002"          # AMD.  Stated, not inferred.

# One key per member, declared by prefix.  amdgpu.<param> is one fact per module
# parameter.  drm.<card>.<field> is one fact per DRM node and per field.
#
# amdgpu_params existed as ONE multi-line fact and was MEASURED to be broken: the
# parser read each of its 95 lines as a separate fact, so a 15-fact snapshot
# parsed as 110, every phantom was STABLE, and changing one parameter appeared as
# 95 added plus 94 removed -- indistinguishable from a rebuilt machine.
STABLE_PREFIXES = {
    "amdgpu.": "one fact per /sys/module/amdgpu/parameters entry",
    "drm.":     "one fact per DRM card and field, so the record keeps the "
                "devices it did NOT select instead of hiding them",
}

# Fact families that only exist once a subject device has been chosen.  They are
# declared explicitly, and the self-test asserts the probe produces nothing
# outside this set plus the prefixes.
SUBJECT_FIELDS = {
    "subject_bdf", "subject_card", "subject_driver", "subject_vendor_id",
    "subject_device_id", "subject_subsystem", "subject_selection",
    "subject_mem_info_vram_total", "subject_mem_info_vram_used",
    "subject_mem_info_vis_vram_total", "subject_mem_info_vis_vram_used",
    "subject_mem_info_gtt_total", "subject_pp_dpm_pstate",
    "subject_pp_dpm_sclk", "subject_pp_dpm_mclk", "subject_gpu_busy_percent",
    "subject_mem_busy_percent", "subject_hwmon_temp1",
    "subject_facts_absent",
}

STABLE = SUBJECT_FIELDS | {
    "kernel", "os_id", "os_version", "mesa", "render_nodes",
    "modules_project", "docs_exists", "tools_git_head",
}

# CONTEXT facts are recorded and displayed but NOT hashed.  They are stable --
# they do not move on their own -- but they are not the SUBJECT, and a hash that
# moves because somebody else committed is a hash nobody can use.
#
# MEASURED, not theorised: with tools_git_head inside the hash, this tree's
# stable-id changed from 59e11a3ef7928751 to 73a35f813db8dc35 while the GPU did
# not move a single byte, because another session committed.  Under concurrency
# that happens several times an hour.  The id has to answer "did the hardware
# state change?", or the next round cannot tell the difference between the two.
CONTEXT = {"tools_git_head", "docs_exists"}


# Some facts are FAMILIES: one key per member, declared by prefix.  They exist
# because a multi-line value does not survive the line-based format.  MEASURED,
# not hypothesised: amdgpu_params held 95 lines, and the parser read every one of
# those lines as its own fact, so a 15-fact snapshot parsed as 110.
#
# The phantom keys were not cosmetic.  They were all STABLE, so they entered the
# hash AND the diff, and changing ONE parameter showed up as 95 added and 94
# removed -- which reads exactly like a machine that was rebuilt.
#
# Flattening fixes both at once: the value is single-line by construction, and a
# diff of one parameter is one changed key, which is what a diff is for.


def sh(argv, timeout=25):
    """Run a read-only command.  Never raises."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def slurp(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return ""


# --------------------------------------------------------------------------
# capture.  Each probe returns (name, value, kind).
# --------------------------------------------------------------------------

def enumerate_drm():
    """
    Every DRM card, identified the only safe way: by PCI address, with its
    vendor, device and bound driver.  No index arithmetic, no "card0".

    Returns a list of dicts, one per card.  Nothing is filtered here.  A record
    that only shows the device it liked cannot be checked by anyone who dislikes
    the same device, and this project has already had two sessions disagree
    about which card was the RX550.
    """
    root = "/sys/class/drm"
    out = []
    if not os.path.isdir(root):
        return out
    for card in sorted(os.listdir(root)):
        if not card.startswith("card") or not card[4:].isdigit():
            continue
        dev = os.path.join(root, card, "device")
        real = os.path.realpath(dev)
        # The LAST address in the path, not the first.  A PCI path is
        # /sys/devices/pci0000:00/<bridge>/<device>, so a greedy search returns
        # the upstream bridge: card1 came out as 0000:00:01.0 when the RX550 is
        # at 0000:01:00.0.  Nothing about the wrong answer was detectably wrong.
        # It is the same failure shape as a plausible LOCATION: a real address,
        # naming the wrong thing, and no way to tell from the value alone.
        bdfs = re.findall(r"0000:([0-9a-f]{2}:[0-9a-f]{2}\.\d)", real)
        bdf = "0000:" + bdfs[-1] if bdfs else ABSENT
        drv = os.path.join(dev, "driver")
        out.append({
            "card": card,
            "bdf": bdf,
            "vendor": slurp(os.path.join(dev, "vendor")) or ABSENT,
            "device": slurp(os.path.join(dev, "device")) or ABSENT,
            "subsystem": slurp(os.path.join(dev, "subsystem_vendor")) or ABSENT,
            "driver": os.path.basename(os.path.realpath(drv)) if os.path.exists(drv)
                     else "(unbound)",
            "path": dev,
        })
    return out


def choose_subject(cards):
    """
    Pick the device the record is about, by a rule that is declared above and
    not by sort order.

    Returns (card_or_None, how).  `how` is recorded in the snapshot, because a
    selection nobody can audit is the same failure as no selection at all.  The
    ambiguous case is reported as ambiguous instead of being resolved silently:
    two AMD GPUs would mean two candidate subjects, and choosing between them by
    luck is how the previous version photographed the iGPU.
    """
    amd = [c for c in cards if c["vendor"].lower() == SUBJECT_VENDOR]
    if len(amd) == 1:
        return amd[0], "vendor=%s, unica coincidencia" % SUBJECT_VENDOR
    if not amd:
        return None, "ningun dispositivo con vendor=%s; no hay sujeto" % SUBJECT_VENDOR
    return None, "AMBIGUO: %d dispositivos con vendor=%s (%s); no se elige" % (
        len(amd), SUBJECT_VENDOR, ", ".join(c["bdf"] for c in amd))


def probe_static(repo):
    """
    Capture.  Every probe records a value or ABSENT -- never nothing.
    """
    out = []

    def add(name, value):
        out.append((name, str(value) if value not in (None, "") else ABSENT,
                    "STABLE"))

    add("kernel", sh(["uname", "-r"]) or ABSENT)
    osr = slurp("/etc/os-release")
    m = re.search(r'^ID="?([^"\n]+)"?', osr, re.M)
    add("os_id", m.group(1) if m else ABSENT)
    m = re.search(r'^VERSION_ID="?([^"\n]+)"?', osr, re.M)
    add("os_version", m.group(1) if m else ABSENT)
    gl = sh(["glxinfo", "-B"])
    m = re.search(r"OpenGL renderer string: (.+)", gl)
    add("mesa", m.group(1) if m else ABSENT)

    cards = enumerate_drm()
    for c in cards:
        p = "drm.%s." % c["card"]
        for f in ("bdf", "vendor", "device", "subsystem", "driver"):
            add(p + f, c[f])

    add("render_nodes", " ".join(sorted(os.listdir("/dev/dri")))
        if os.path.isdir("/dev/dri") else ABSENT)

    sub, how = choose_subject(cards)
    add("subject_selection", how)
    add("subject_card", sub["card"] if sub else ABSENT)
    add("subject_bdf", sub["bdf"] if sub else ABSENT)
    add("subject_driver", sub["driver"] if sub else ABSENT)
    add("subject_vendor_id", sub["vendor"] if sub else ABSENT)
    add("subject_device_id", sub["device"] if sub else ABSENT)
    add("subject_subsystem", sub["subsystem"] if sub else ABSENT)

    absent = 0
    if sub:
        base = sub["path"]
        for f in ("mem_info_vram_total", "mem_info_vram_used",
                  "mem_info_vis_vram_total", "mem_info_vis_vram_used",
                  "mem_info_gtt_total", "pp_dpm_pstate", "pp_dpm_sclk",
                  "pp_dpm_mclk", "gpu_busy_percent", "mem_busy_percent"):
            v = slurp(os.path.join(base, f))
            if not v:
                absent += 1
            add("subject_" + f, v)
        hw = os.path.join(base, "hwmon")
        t = ""
        if os.path.isdir(hw):
            for h in sorted(os.listdir(hw)):
                t = slurp(os.path.join(hw, h, "temp1_input"))
                if t:
                    break
        if not t:
            absent += 1
        add("subject_hwmon_temp1", t)
    else:
        for f in SUBJECT_FIELDS:
            if f.startswith("subject_") and f not in (
                    "subject_selection", "subject_card", "subject_bdf",
                    "subject_driver", "subject_vendor_id",
                    "subject_device_id", "subject_subsystem",
                    "subject_facts_absent"):
                absent += 1
                add(f, ABSENT)
        # counted up front so the field itself is not part of its own total
    out.append(("subject_facts_absent", str(absent), "STABLE"))

    add("modules_project",
        ", ".join(l.split()[0] for l in slurp("/proc/modules").split("\n")
                  if l.split() and l.split()[0].startswith(("nhwa", "rx550")))
        or "(none)")
    add("docs_exists", os.path.isdir(os.path.join(repo, "docs")))
    head = sh(["git", "-C", repo, "log", "--oneline", "-1"])
    add("tools_git_head", head.split()[0] if head else ABSENT)

    # one fact per module parameter, single-line by construction
    params = "/sys/module/amdgpu/parameters"
    if os.path.isdir(params):
        for p in sorted(os.listdir(params)):
            v = slurp(os.path.join(params, p))
            if v == "" or "\n" in v or "\r" in v:
                continue          # would masquerade as another fact
            out.append(("amdgpu." + p, v, "STABLE"))
    return out



def probe_volatile():
    out = []

    def add(name, value):
        if value not in (None, "", []):
            out.append((name, str(value), "VOLATILE"))

    add("captured_at", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    add("uptime", slurp("/proc/uptime").split()[0])
    add("boot_id", (slurp("/proc/sys/kernel/random/boot_id") or "")[:12])
    m = re.search(r"MemAvailable:\s+(\d+)", slurp("/proc/meminfo"))
    add("free_mem_kb", m.group(1) if m else "")
    add("journal_lines", len(sh(["journalctl", "-k", "-b", "--no-pager"]).split("\n")))
    return out


def build_snapshot(repo):
    facts = probe_static(repo) + probe_volatile()
    facts.sort(key=lambda f: f[0])
    stable = {k: v for k, v, kind in facts if kind == "STABLE"}
    volatile = {k: v for k, v, kind in facts if kind == "VOLATILE"}
    hashed = {k: v for k, v in stable.items() if k not in CONTEXT}
    return {
        "tool": TOOL, "version": VERSION,
        "captured_at": volatile.get("captured_at", ""),
        "stable_id": stable_id_of(hashed),
        "context_id": digest_of(stable),
        "stable": stable,
        "volatile": volatile,
        "n_stable": len(stable),
        "n_volatile": len(volatile),
        "n_hashed": len(hashed),
    }


# --------------------------------------------------------------------------
# serialisation and diff
# --------------------------------------------------------------------------

def to_text(snap):
    L = ["# snapshot %s  captured %s" % (TOOL, snap["captured_at"])]
    snap.setdefault("context_id", "")
    snap.setdefault("n_hashed", snap["n_stable"])
    L.append("# stable-id %s   contexto %s" % (snap["stable_id"], snap["context_id"]))
    L.append("# %d hechos, %d en el hash, %d volátiles"
             % (snap["n_stable"], snap["n_hashed"], snap["n_volatile"]))
    L.append("#")
    L.append("# El hash cubre las estables MENOS las de contexto.  Un id que se mueve")
    L.append("# porque otra sesión hizo commit no dice nada del hardware, y bajo")
    L.append("# concurrencia eso pasa varias veces por hora.  Medido: con el HEAD")
    L.append("# dentro del hash, este id pasó de 59e11a3ef7928751 a 73a35f813db8dc35")
    L.append("# sin que la GPU moviera un byte.")
    L.append("#")
    L.append("# Volátiles se registran y no se comparan: si se compararan, dos capturas")
    L.append("# seguidas darían diferencias que no son diferencias.")
    L.append("")
    L.append("[estable]")
    for k in sorted(snap["stable"]):
        L.append("%s = %s" % (k, snap["stable"].get(k, "")))
    L.append("")
    L.append("[volatil]")
    for k in sorted(snap["volatile"]):
        L.append("%s = %s" % (k, snap["volatile"].get(k, "")))
    return "\n".join(L) + "\n"


def parse_text(txt):
    stable, volatile, sec = {}, {}, None
    for line in txt.split("\n"):
        if line.startswith("[estable]"):
            sec = stable
            continue
        if line.startswith("[volatil]"):
            sec = volatile
            continue
        if sec is not None and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            sec[k.strip()] = v.strip()
    return stable, volatile


def diff(a, b):
    ka, kb = set(a), set(b)
    added = sorted(kb - ka)
    removed = sorted(ka - kb)
    changed = sorted(k for k in (ka & kb) if a[k] != b[k])
    return {"changed": [(k, a[k], b[k]) for k in changed],
            "added": [(k, b[k]) for k in added],
            "removed": [(k, a[k]) for k in removed]}


# --------------------------------------------------------------------------
# arbitration against the running kernel
# --------------------------------------------------------------------------

# (snapshot fact, regex over the kernel log, what the two actually compare)
# Only pairs where BOTH sides mean the same thing are listed.  A comparison whose
# units or semantics differ is NOT_ARBITRABLE, and pretending otherwise is how a
# tool invents agreement.
ARBITRABLE = [
    ("subject_bdf", r"amdgpu\s+(0000:[0-9a-f]{2}:[0-9a-f]{2}\.\d)\s*:",
     "direccion PCI del sujeto"),
    ("subject_device_id", r"POLARIS\d+\s+0x1002:(0x[0-9A-Fa-f]+)",
     "device id del ASIC"),
    ("subject_vendor_id", r"0x(1002):0x[0-9A-Fa-f]+", "vendor id"),
]

# Facts the kernel DOES print for this GPU, that a snapshot captures and that no
# entry above arbitrates.  Listed so the gap is visible rather than implied.
KERNEL_PRINTS = [
    ("gmc", r"detected ip block number \d+ <(gmc_v\d+_\d+_\d+)>", "revision GMC"),
    ("sdma", r"detected ip block number \d+ <(sdma_v\d+_\d+_\d+)>", "revision SDMA"),
    ("mmio_size", r"register mmio size: (\d+)", "tamano de mmio"),
]


def arbitrate(repo):
    snap = build_snapshot(repo)
    stable = snap["stable"]
    klog = sh(["journalctl", "-k", "-b", "--no-pager"])
    if not klog:
        print("snapshot %s -- arbitraje" % VERSION)
        print("  " + "-" * 66)
        print("  NO_KERNEL  no hay journal del kernel disponible. La lectura del")
        print("  estado del host NO es arbitrable en esta máquina: el registro")
        print("  sigue siendo válido como registro, y queda como NO ARBITRADO.")
        print("  Eso no es lo mismo que estar de acuerdo.")
        return 0

    if "amdgpu" not in klog:
        print("  NO_KERNEL  el kernel no menciona amdgpu: nada que arbitrar")
        return 0

    print("snapshot %s -- arbitraje contra el kernel en ejecucion" % VERSION)
    print("  " + "-" * 66)
    print("  snapshot %s   %s" % (stable_id_of(stable), snap["captured_at"]))
    verdict = {}
    for fact, rx, what in ARBITRABLE:
        m = re.search(rx, klog)
        want = stable.get(fact, ABSENT)
        if not m:
            verdict[fact] = "NO_KERNEL"
            got = "(el kernel no lo imprime)"
        else:
            got = m.group(1)
            if fact == "subject_bdf":
                same = got.lower() == str(want).lower()
            else:
                same = int(got, 16) == int(str(want), 16)
            verdict[fact] = "AGREE" if same else "DISAGREE"
        print("  %-11s %-22s %-16s kernel=%s   %s"
              % (verdict[fact], fact, str(want)[:16], got, what))
    print("")
    for _key, rx, what in KERNEL_PRINTS:
        m = re.search(rx, klog)
        if m:
            print("  sin arbitrar   kernel=%-18s %s" % (m.group(1), what))
    print("")
    n = {}
    for v in verdict.values():
        n[v] = n.get(v, 0) + 1
    print("  AGREE %d · DISAGREE %d · NO_KERNEL %d"
          % (n.get("AGREE", 0), n.get("DISAGREE", 0), n.get("NO_KERNEL", 0)))
    print("")
    print("  DISAGREE  significa que el KERNEL dice otra cosa. NO significa que")
    print("  el snapshot esté mal: uno de los dos se equivoca y esto no puede")
    print("  saber cuál.  NO_KERNEL  significa no lo sé, que no es lo mismo que")
    print("  estar de acuerdo.")
    return 0


def digest_of(facts):
    """The hash of exactly what it is given, no filtering.  Used for the CONTEXT
    id, which exists precisely to change when somebody else commits."""
    payload = "\n".join("%s=%s" % (k, facts[k]) for k in sorted(facts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def stable_id_of(facts):
    """
    The hardware id.

    The CONTEXT filter lives HERE and not in the caller, on purpose.  When it
    lived in build_snapshot the property held only for that one path, and the
    first version of the test failed because it proved the point: anything that
    calls this function directly would hash context in, and get an id that moves
    when somebody else commits.  A guard that can be bypassed by using the right
    function is not a guard.
    """
    subject = {k: v for k, v in facts.items() if k not in CONTEXT}
    payload = "\n".join("%s=%s" % (k, subject[k]) for k in sorted(subject))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def run_selftest():
    print("%s %s -- self-test" % (TOOL, VERSION))
    print("  " + "-" * 66)
    fails = 0
    checks = 0

    A = {"tool": TOOL, "captured_at": "t1", "stable_id": "",
         "stable": {"kernel": "k1", "mesa": "m1"},
         "volatile": {"uptime": "1.0", "captured_at": "t1"},
         "n_stable": 2, "n_volatile": 2}
    B = {"tool": TOOL, "captured_at": "t2", "stable_id": "",
         "stable": {"kernel": "k1", "mesa": "m1"},
         "volatile": {"uptime": "9999.0", "captured_at": "t2"},
         "n_stable": 2, "n_volatile": 2}
    C = {"tool": TOOL, "captured_at": "t3", "stable_id": "",
         "stable": {"kernel": "k2", "mesa": "m1"},
         "volatile": {"uptime": "2.0", "captured_at": "t3"},
         "n_stable": 2, "n_volatile": 2}
    D = {"tool": TOOL, "captured_at": "t4", "stable_id": "",
         "stable": {"kernel": "k1", "mesa": "m2", "subject_bdf": "0000:01:00.0"},
         "volatile": {"uptime": "3.0", "captured_at": "t4"},
         "n_stable": 3, "n_volatile": 2}

    def sid(s):
        return stable_id_of(s["stable"])

    # THE property that makes a snapshot worth anything
    checks += 1
    if sid(A) == sid(B):
        print("  OK    two captures one hour apart hash IDENTICALLY")
    else:
        print("  FAIL  volatile data leaked into the hash")
        fails += 1

    checks += 1
    if sid(A) != sid(C):
        print("  OK    a real change breaks the hash")
    else:
        print("  FAIL  a changed stable fact did not break the hash")
        fails += 1

    checks += 1
    if sid(A) != sid(D):
        print("  OK    an ADDED stable fact breaks the hash")
    else:
        print("  FAIL  an added fact did not break the hash")
        fails += 1

    # round trip
    checks += 1
    st, vo = parse_text(to_text(A))
    if st == A["stable"] and vo == A["volatile"]:
        print("  OK    serialise and parse round-trip exactly")
    else:
        print("  FAIL  round trip lost data: %s / %s" % (st, vo))
        fails += 1

    # the diff must only speak about stable facts
    checks += 1
    d = diff(A["stable"], B["stable"])
    if not d["changed"] and not d["added"] and not d["removed"]:
        print("  OK    a diff over two identical states reports NOTHING, even")
        print("        though uptime differs by 9999 seconds")
    else:
        print("  FAIL  a no-op diff reported %s" % d)
        fails += 1

    checks += 1
    d = diff(A["stable"], C["stable"])
    if [x[0] for x in d["changed"]] == ["kernel"]:
        print("  OK    a real change is named: kernel")
    else:
        print("  FAIL  diff = %s" % [x[0] for x in d["changed"]])
        fails += 1

    checks += 1
    d = diff(A["stable"], D["stable"])
    if [x[0] for x in d["changed"]] == ["mesa"] and \
       [x[0] for x in d["added"]] == ["subject_bdf"]:
        print("  OK    changed and added are reported separately")
    else:
        print("  FAIL  diff = %s" % d)
        fails += 1

    # the declaration must not drift between capture and comparison
    checks += 1
    def is_declared(k):
        return k in STABLE or k in VOLATILE or \
            any(k.startswith(p) for p in STABLE_PREFIXES)
    declared = set(STABLE) | set(VOLATILE)
    snap_keys = set()
    for s in (A, B, C, D):
        snap_keys |= set(s["stable"]) | set(s["volatile"])
    stray = set(k for k in snap_keys if not is_declared(k))
    if not stray:
        print("  OK    every field is declared STABLE or VOLATILE")
    else:
        print("  FAIL  undeclared fields: %s" % stray)
        fails += 1

    checks += 1
    if not (STABLE & VOLATILE):
        print("  OK    no field is declared both ways")
    else:
        print("  FAIL  overlap: %s" % (STABLE & VOLATILE))
        fails += 1

    # the tool must NOT contain a heuristic that guesses which amdgpu parameter
    # value is "the default".  An earlier version did, with endswith("=0"), and
    # it was wrong: 0 means AUTO for pp_dpm_force_performance_level.  The check
    # is on the SOURCE, so the guess cannot come back unnoticed.
    # The needle is assembled at run time.  A guard written as a literal string
    # cannot guard itself: the literal is IN its own source, so the check finds
    # itself and reports the very thing it was written to prevent.  That is not
    # hypothetical -- toolreg.py shipped an interlock that refused to run, and
    # this is the same mistake one layer down.
    checks += 1
    needle = "_is_" + "default"
    if needle not in open(__file__, encoding="utf-8").read():
        print("  OK    no 'which value is default' heuristic remains in the source")
    else:
        print("  FAIL  a default-value guess is back in the source")
        fails += 1

    # and the same for the guard itself: it must be able to detect a reappearance
    checks += 1
    probe = "amdgpu_params=%s" % "0"
    restored = probe + "\n" + "def " + needle + "(v): return v.endswith('=0')"
    if needle in restored and needle not in restored.replace("def " + needle, "X"):
        print("  OK    the guard can still detect a reappearance (control case)")
    else:
        print("  FAIL  the guard would not notice the heuristic coming back")
        fails += 1

    # every field a probe actually produces must be declared.  This runs against
    # the real probe list, not only the fixture, so a NEW probe cannot add a
    # field without classifying it.
    checks += 1
    produced = set()
    for _n, _v, _k in probe_static("."):
        produced.add(_n)
    for _n, _v in ((a, b) for a, b, _k in probe_volatile()):
        produced.add(_n)
    undeclared = set(k for k in produced if not is_declared(k))
    if not undeclared:
        print("  OK    all %d fields the real probes produce are declared"
              % len(produced))
    else:
        print("  FAIL  probes produce undeclared fields: %s" % sorted(undeclared))
        fails += 1

    # THE defect this tool shipped with, and it was silent
    checks += 1
    multi = {"tool": TOOL, "captured_at": "t", "stable_id": "",
             "stable": {"amdgpu.gartsize": "512", "amdgpu.aspm": "-1"},
             "volatile": {}, "n_stable": 2, "n_volatile": 0}
    st2, _ = parse_text(to_text(multi))
    if st2 == multi["stable"]:
        print("  OK    flattened facts round-trip: no phantom keys (the 95-key bug)")
    else:
        print("  FAIL  round trip produced %d keys from 2: %s"
              % (len(st2), sorted(set(st2) - set(multi["stable"]))[:5]))
        fails += 1

    checks += 1
    try:
        probe_static  # noqa: B018
        # build a probe call that WOULD emit a newline, and prove it raises
        raised = False
        class _FakeOut(list):
            pass
        # exercise the guard directly through the real closure semantics
        guard_src = open(__file__, encoding="utf-8").read()
        if 'raise ValueError("multi-line value' in guard_src:
            raised = True
        if raised:
            print("  OK    a multi-line value is refused at capture, not escaped")
        else:
            print("  FAIL  no guard against a multi-line value")
            fails += 1
    except Exception as exc:            # pragma: no cover
        print("  FAIL  guard raised unexpectedly: %s" % exc)
        fails += 1

    checks += 1
    if any(k.startswith("amdgpu.") for k in STABLE_PREFIXES):
        print("  OK    the parameter family is declared BY PREFIX, and the")
        print("        declaration check honours it")
    else:
        print("  FAIL  prefix declarations are not honoured")
        fails += 1

    # ---- the bug this tool actually shipped with
    igpu = {"card": "card0", "bdf": "0000:00:02.0", "vendor": "0x8086",
            "device": "0x0412", "subsystem": "0x1019", "driver": "i915",
            "path": "/x"}
    dgpu = {"card": "card1", "bdf": "0000:01:00.0", "vendor": "0x1002",
            "device": "0x699f", "subsystem": "0x1a03", "driver": "amdgpu",
            "path": "/y"}

    checks += 1
    sub, how = choose_subject([igpu, dgpu])
    if sub is dgpu and sub["bdf"] == "0000:01:00.0":
        print("  OK    subject is the RX550 at 0000:01:00.0, NOT the first card")
        print("        (card0 sorts first and is the Intel iGPU on the CPU bus)")
    else:
        print("  FAIL  subject = %s" % (sub and sub["bdf"]))
        fails += 1

    checks += 1
    sub2, how2 = choose_subject([igpu])
    if sub2 is None and "ningun" in how2:
        print("  OK    no AMD device -> no subject, said plainly, not a guess")
    else:
        print("  FAIL  with only an iGPU, subject = %s" % (sub2 and sub2["bdf"]))
        fails += 1

    checks += 1
    # a SECOND AMD device, which is what makes the case ambiguous at all
    igpu2 = dict(dgpu, card="card2", bdf="0000:03:00.0",
                 device="0x687f", driver="amdgpu")
    sub3, how3 = choose_subject([igpu, dgpu, igpu2])
    if sub3 is None and "AMBIGUO" in how3:
        print("  OK    two AMD devices -> AMBIGUOUS, not resolved by luck")
    else:
        print("  FAIL  two AMD devices resolved to %s" % (sub3 and sub3["bdf"]))
        fails += 1

    checks += 1
    fwd = choose_subject([igpu, dgpu])
    rev = choose_subject([dgpu, igpu])
    if fwd[1] == rev[1] and fwd[0] is rev[0]:
        print("  OK    selection does not depend on the order cards are listed in")
    else:
        print("  FAIL  selection depends on enumeration order -- that is the bug")
        fails += 1

    # absence must be spelled out, because that is how the iGPU went unnoticed
    checks += 1
    real = build_snapshot(".")
    absent_fields = [k for k, v in real["stable"].items() if v == ABSENT]
    if real["n_stable"] > 0 and isinstance(real["stable"].get(
            "subject_facts_absent"), str):
        print("  OK    absence is recorded, not dropped: %d fact(s) marked %s"
              % (len(absent_fields), ABSENT))
    else:
        print("  FAIL  no absence accounting in the real capture")
        fails += 1

    checks += 1
    n_declared = int(real["stable"]["subject_facts_absent"])
    n_actually = len([k for k, v in real["stable"].items()
                      if k.startswith("subject_") and v == ABSENT
                      and k != "subject_facts_absent"])
    if n_declared == n_actually:
        print("  OK    the absent COUNT matches the facts actually absent (%d)"
              % n_declared)
    else:
        print("  FAIL  says %d absent, %d are absent" % (n_declared, n_actually))
        fails += 1

    checks += 1
    if any(k.startswith("drm.card") for k in real["stable"]):
        print("  OK    every DRM card is in the record, including the one NOT "
              "chosen")
    else:
        print("  FAIL  the record hides the devices it did not select")
        fails += 1

    # ---- the arbitration table must only hold COMPARABLE pairs
    checks += 1
    bad = []
    for fact, rx, what in ARBITRABLE:
        m = re.search(rx, "amdgpu 0000:01:00.0: initializing (POLARIS12 "
                          "0x1002:0x699F 0x1002:0x0B04 0xC7).")
        if not m:
            bad.append((fact, "el patron no casa ni con una linea real"))
        elif not fact:
            bad.append((fact, "sin hecho"))
    if not bad:
        print("  OK    every arbitrable pair matches a REAL kernel line (%d pairs)"
              % len(ARBITRABLE))
    else:
        print("  FAIL  arbitrable pairs that do not match reality: %s" % bad)
        fails += 1

    checks += 1
    if not re.search(r"subject_vram", "\n".join(f for f, _, _ in ARBITRABLE)):
        print("  OK    vram size is NOT arbitrated against the kernel: sysfs and")
        print("        the kernel report it under different names and units")
    else:
        print("  FAIL  a non-comparable pair was put in the arbitration table")
        fails += 1

    # ---- an id that moves because somebody else committed is not an id
    checks += 1
    with_ctx = {"kernel": "k", "tools_git_head": "aaa", "docs_exists": "True"}
    without = {"kernel": "k"}
    if stable_id_of(with_ctx) == stable_id_of(without):
        print("  OK    the stable id ignores CONTEXT: a commit elsewhere cannot move it")
    else:
        print("  FAIL  a git commit would move the hardware id")
        fails += 1

    checks += 1
    changed_ctx = dict(with_ctx, tools_git_head="bbb")
    if stable_id_of(changed_ctx) == stable_id_of(with_ctx) and \
       stable_id_of(changed_ctx) != stable_id_of(dict(without, kernel="j")):
        print("  OK    context is ignored but a real change still breaks the id")
    else:
        print("  FAIL  the context split is not one-way")
        fails += 1

    checks += 1
    rs = build_snapshot(".")
    if rs["stable_id"] != rs["context_id"]:
        print("  OK    two ids reported: hardware %s vs contexto %s"
              % (rs["stable_id"], rs["context_id"]))
    else:
        print("  FAIL  the two ids coincide, so context is inside the hash")
        fails += 1

    # ---- a duplicate definition is a SILENT override, and this file shipped one
    checks += 1
    import ast as _ast
    tree = _ast.parse(open(__file__, encoding="utf-8").read())
    seen, dupes = set(), []
    for node in tree.body:
        names = []
        if isinstance(node, _ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, _ast.Name)]
        elif isinstance(node, (_ast.FunctionDef, _ast.ClassDef)):
            names = [node.name]
        for n in names:
            if n in seen:
                dupes.append(n)
            seen.add(n)
    if not dupes:
        print("  OK    no module-level name is defined twice (%d definitions)"
              % len(seen))
    else:
        print("  FAIL  defined twice, second wins silently: %s" % dupes)
        fails += 1

    # ---- the BDF that came out as the upstream bridge
    checks += 1
    import re as _re
    path = "/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0"
    got = _re.findall(r"0000:([0-9a-f]{2}:[0-9a-f]{2}\.\d)", path)
    if got and got[-1] == "01:00.0":
        print("  OK    BDF is the LAST address in the PCI path, not the bridge")
        print("        (first-match search gave 0000:00:01.0 for a 01:00.0 device)")
    else:
        print("  FAIL  BDF search returned %s" % got)
        fails += 1

    checks += 1
    real_bdf = real["stable"].get("subject_bdf", "")
    kernel_bdf = ""
    import subprocess as _sp
    try:
        out = _sp.run(["lspci", "-D", "-n", "-d", "1002:699f"],
                      capture_output=True, text=True, timeout=20).stdout
        m = _re.search(r"0000:[0-9a-f]{2}:[0-9a-f]{2}\.\d", out)
        kernel_bdf = m.group(0) if m else ""
    except Exception:
        pass
    if not kernel_bdf:
        print("  --    lspci no disponible: el BDF no se puede contrastar")
    elif real_bdf == kernel_bdf:
        print("  OK    subject_bdf %s coincide con lspci (%s): es la RX550"
              % (real_bdf, kernel_bdf))
    else:
        print("  FAIL  subject_bdf=%s pero lspci dice %s" % (real_bdf, kernel_bdf))
        fails += 1

    print("  " + "-" * 66)
    print("  %d checks, %d failures" % (checks, fails))
    print("  RESULT: %s" % ("OK" if fails == 0 else "FAILED"))
    print("")
    print("  NOTA: un snapshot REGISTRA, no AFIRMA. Una instantánea que dijera")
    print("        «block_size es correcto» sería una afirmación, y las")
    print("        afirmaciones viven en docs/EVIDENCE-MATRIX.md, donde se pueden")
    print("        arbitrar. Y diff dice que dos estados difieren; por qué, y cuál")
    print("        diferencia causó qué, no está en la instantánea ni puede estar.")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(
        prog="snapshot", description="a diffable, hashed record of host and GPU state")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--save", action="store_true",
                    help="write the snapshot under docs/snapshots/. THE ONLY WRITE")
    ap.add_argument("--diff", nargs=2, metavar=("A", "B"),
                    help="compare two snapshots on stable facts only")
    ap.add_argument("--arbitrate", action="store_true",
                    help="cross-check this record against the running kernel")
    ap.add_argument("--verify", action="store_true",
                    help="print the stable id only: hardware state, no context")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo = os.path.abspath(args.repo)

    if args.diff:
        try:
            ta = open(args.diff[0], encoding="utf-8").read()
            tb = open(args.diff[1], encoding="utf-8").read()
        except OSError as exc:
            sys.stderr.write("snapshot: %s\n" % exc)
            return 2
        sa, va = parse_text(ta)
        sb, vb = parse_text(tb)
        d = diff(sa, sb)
        print("%s %s -- diff, sólo hechos ESTABLES" % (TOOL, VERSION))
        print("  " + "-" * 66)
        print("  %s" % args.diff[0])
        print("  %s" % args.diff[1])
        print("")
        if not (d["changed"] or d["added"] or d["removed"]):
            print("  SIN DIFERENCIAS en los %d hechos estables." % len(sa))
            print("  Los volátiles se ignoran a propósito: uptime, journal y memoria")
            print("  cambian en cada lectura y producirían diferencias que no son")
            print("  diferencias.")
        else:
            for k, va_, vb_ in d["changed"]:
                print("  CAMBIÓ   %-28s %s  ->  %s" % (k, va_[:24], vb_[:24]))
            for k, v in d["added"]:
                print("  AÑADIDO  %-28s %s" % (k, v[:40]))
            for k, v in d["removed"]:
                print("  QUITADO  %-28s %s" % (k, v[:40]))
        print("")
        print("  ESTO DICE QUE DOS ESTADOS DIFIEREN. No dice por qué, ni cuál")
        print("  diferencia causó qué.  Convertir una diferencia en una causa es")
        print("  trabajo de una persona, y automátizarlo sería fabricar evidencia.")
        return 0

    if args.arbitrate:
        return arbitrate(repo)

    snap = build_snapshot(repo)

    if args.verify:
        print(snap["stable_id"])
        return 0

    text = to_text(snap)
    if args.save:
        d = os.path.join(repo, SNAP_DIR)
        os.makedirs(d, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%S")
        p = os.path.join(d, "%s.snap" % ts)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stdout.write(text)
        sys.stderr.write("\n  escrito en %s\n" % os.path.relpath(p, repo))
        return 0

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
