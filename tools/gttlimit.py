#!/usr/bin/env python3
# gttlimit.py -- reproduce the GTT page limit of THIS host from primary sources.
#
# QUESTION (AGENT-09, GART chain: SYSTEM MEMORY -> GART):
#   De donde sale exactamente el limite de paginas de TTM que amdgpu imprime
#   como "5907M of GTT memory ready"?
#
# WHY IT EXISTS:
#   Finding 204 registered this as NOT_DETERMINED with the written reason
#   "es una funcion de TTM que no esta en este corpus". That blocker was
#   falsifiable and it is now falsified: RESEARCH/kernelbuild/linux-7.1.3 now
#   contains drivers/gpu/drm/ttm/. This tool exists so the closure is
#   re-executable instead of asserted in prose.
#
# SCOPE / SAFETY: read-only. Reads /proc/meminfo, /sys/module/ttm/parameters,
#   /sys/class/drm/card*/device. No MMIO, no writes, no GPU state change,
#   no sudo, uid 1000.
#
# PASS: every relation below holds exactly (bit-for-bit), and the printed MiB
#       equals the "5907M" the kernel logged at boot.
# FAIL: any relation is off by a non-zero amount -> the chain is NOT closed and
#       the residual is printed as a page count, not explained away.
#
# Per finding 204 section 4: no number that decides a conclusion is computed
# mentally. Everything below is computed here.
#
# usage: python3 tools/gttlimit.py [--json]

import json
import os
import sys

PAGE_SHIFT = 12
PAGE_SIZE = 1 << PAGE_SHIFT


def read(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError as exc:
        return "UNREADABLE(%s)" % exc.strerror


def first_drm_dev():
    """Return the DRM device that actually publishes mem_info_gtt_total.

    First measured version of this tool took the FIRST card directory and
    reported UNREADABLE for mem_info_gtt_total. That was a defect of the tool,
    not a fact about the machine: the first card is the Intel iGPU, which has no
    mem_info_gtt_* at all. Selecting by "first card" and then concluding
    "the file does not exist" is the NAME_NOT_FOUND-treated-as-absence error
    this project records nine times. The selector now asks for the capability
    the check needs.
    """
    base = "/sys/class/drm"
    try:
        cards = sorted(os.listdir(base))
    except OSError:
        return None
    for card in cards:
        dev = os.path.join(base, card, "device")
        if os.path.isdir(dev) and os.path.exists(os.path.join(dev,
                                                             "mem_info_gtt_total")):
            return dev
    return None


def meminfo_totalram_pages():
    """MemTotal kB -> pages. /proc/meminfo MemTotal = nr_pages << (PAGE_SHIFT-10)."""
    with open("/proc/meminfo") as fh:
        for line in fh:
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return kb * 1024 // PAGE_SIZE
    return None


def main():
    as_json = "--json" in sys.argv

    pages_limit = read("/sys/module/ttm/parameters/pages_limit")
    totalram_pages = meminfo_totalram_pages()

    dev = first_drm_dev()
    gtt_total = read(os.path.join(dev, "mem_info_gtt_total")) if dev else "NO_DRM_DEV"

    r = {}

    # --- OBSERVED -------------------------------------------------------
    r["OBSERVED_ttm_pages_limit"] = pages_limit
    r["OBSERVED_totalram_pages"] = totalram_pages
    r["OBSERVED_mem_info_gtt_total_bytes"] = gtt_total

    # --- DERIVED FROM ttm_device.c:91-92 --------------------------------
    #   num_pages = ((u64)si.totalram * si.mem_unit) >> PAGE_SHIFT; num_pages /= 2;
    limit_from_mem = (totalram_pages >> 1) if totalram_pages else None
    r["DERIVED_expected_pages_limit_half_of_totalram"] = limit_from_mem

    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    # CHECK 1: the limit really is half of totalram pages.
    if pages_limit.isdigit() and limit_from_mem is not None:
        resid = int(pages_limit) - limit_from_mem
        r["RESIDUAL_limit_minus_half_totalram_pages"] = resid
        check(
            "pages_limit == totalram_pages/2",
            resid == 0,
            "pages_limit=%s  totalram/2=%d  residual=%+d pages"
            % (pages_limit, limit_from_mem, resid),
        )
    else:
        check("pages_limit == totalram_pages/2", False, "unreadable input")

    # CHECK 2: gtt_size == pages_limit << PAGE_SHIFT  (amdgpu_ttm.c:2140)
    if pages_limit.isdigit() and gtt_total.isdigit():
        gtt_bytes = int(pages_limit) << PAGE_SHIFT
        r["DERIVED_gtt_size_bytes"] = gtt_bytes
        resid_b = int(gtt_total) - gtt_bytes
        r["RESIDUAL_gtt_total_minus_derived_bytes"] = resid_b
        check(
            "mem_info_gtt_total == pages_limit << 12",
            resid_b == 0,
            "sysfs=%s  derived=%d  residual=%+d bytes (%+d pages)"
            % (gtt_total, gtt_bytes, resid_b, resid_b // PAGE_SIZE),
        )
    else:
        check("mem_info_gtt_total == pages_limit << 12", False, "unreadable input")

    # CHECK 3: the boot log line "5907M" is this same number truncated by the
    #   (unsigned int) cast at amdgpu_ttm.c:2160-2161.
    if pages_limit.isdigit():
        mib = (int(pages_limit) << PAGE_SHIFT) // (1024 * 1024)
        r["DERIVED_gtt_mib_truncated"] = mib
        check(
            "truncated MiB == 5907 as logged at boot",
            mib == 5907,
            "computed=%d MiB, kernel logged 5907M" % mib,
        )

    r["CHECKS"] = checks
    r["VERDICT"] = "CLOSED" if all(c["ok"] for c in checks) else "NOT_CLOSED"
    r["SOURCE"] = {
        "producer": "drivers/gpu/drm/ttm/ttm_device.c:91-92 (si_meminfo, /2)",
        "carrier": "drivers/gpu/drm/ttm/ttm_tt.c:480-481,532-536",
        "consumer": "drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c:2140,2160",
        "corpus": "RESEARCH/kernelbuild/linux-7.1.3",
    }

    if as_json:
        print(json.dumps(r, indent=2))
        return 0 if r["VERDICT"] == "CLOSED" else 1

    print("GTT limit chain, this host, read-only")
    print("-" * 62)
    for k in (
        "OBSERVED_ttm_pages_limit",
        "OBSERVED_totalram_pages",
        "OBSERVED_mem_info_gtt_total_bytes",
        "DERIVED_expected_pages_limit_half_of_totalram",
        "DERIVED_gtt_size_bytes",
        "DERIVED_gtt_mib_truncated",
    ):
        if k in r:
            print("  %-44s %s" % (k, r[k]))
    for k in ("RESIDUAL_limit_minus_half_totalram_pages",
              "RESIDUAL_gtt_total_minus_derived_bytes"):
        if k in r:
            print("  %-44s %+d" % (k, r[k]))
    print()
    for c in checks:
        print("  [%s] %-42s %s" % ("PASS" if c["ok"] else "FAIL",
                                    c["check"], c["detail"]))
    print()
    print("VERDICT: %s" % r["VERDICT"])
    return 0 if r["VERDICT"] == "CLOSED" else 1


if __name__ == "__main__":
    sys.exit(main())