## Problem

REA's agent workflows often produce "reconstructed" or "verified" binary outputs, but there is no
published, self-contained reference case showing **differential verification of a hand-reconstructed
function against a real, stripped GNU coreutils binary** — the kind of case an agent (or a human
reviewer) can use to check its own claims, from scratch, in minutes.

## Desired outcome

A maintainer decision on whether a compact worked example based on the artifacts below would belong
in this repository (e.g. under `docs/guides/native/` next to `binary-diagnostics.md`, under
`website/public/examples/`, or somewhere else you prefer), or whether this does not fit REA's scope.
Either answer is fine. No code is requested to be merged as part of this discussion.

## The artifacts (public, MIT, no GPL code redistributed)

Package: **rxre-cleanroom** — https://github.com/LexLuthorPrimero/rxre-cleanroom (MIT LICENSE;
commit `fe3c6f7`; ~35k–38k sealed differential checks, zero divergences, C and UTF-8 locales).

It contains two reconstructed functions/programs and a "verify from nothing" protocol:

1. **`filenvercmp`** — hand-written semantic reconstruction of the version-aware filename comparator
   inside `/usr/bin/ls` (GNU coreutils 9.10): `filenvercmp` @ `0x4fa0`, `verrevcmp` @ `0x4b60`,
   `file_prefixlen` @ `0x4a80`. Target: sha256 `54e936d3…`, ELF64 PIE stripped. A corpus of
   34,145 sealed (SEED 20261112) and a second 34,145-corpus (SEED 20261113), differential-checked
   against the native binary used only as a runtime oracle (mmap, read-only). Discriminating-test
   iteration found and eliminated 791 real divergences in an earlier empirical model before reaching
   zero. Line-audit: 25,468 → 1,014 → 791 → … → 0/34,145, twice (2 generations).

2. **`wc`** — semantic reconstruction of `/usr/bin/wc` with a sealed corpus
   (cases_seed20261114/15/16/17/18/20; 4,899 + 4,914 + 11,872 + 13,072 + 2×1,184 checks) in two
   locales (LC_ALL=C, es_AR.utf8), zero divergences. Includes byte-audit of all 256 LC_ALL=C
   byte classes vs the native oracle, and a `-m ≡ -c` observation in LC_ALL=C.

Verification needs only `gcc`/`clang` + standard shell tools (`sha256sum -c`, corpus compare).
No accounts, no network, no REA dependency.

Known limits, stated explicitly in the package itself: third-party/blind verification NOT_EXECUTED
(the public repo's issue #1 is still open with 0 reports); the host, UID, human and model were the
same author for all evidence; the reconstruction is a semantic contract, not a production port;
CJK wide chars and UTF-8 `-L` full audit are NOT_EXECUTED.

## What I am asking

- Whether this fits REA as (a) a native-analysis guide, (b) a verification/evidence page,
  (c) an example assets bundle, or (d) not at all.
- If yes, the preferred location and format; I can prepare a PR with the documentation-only change.
- If no, a closed/declined answer is also useful information.

Not claimed: any endorsement of RXRE, any general fitness of this method for other binaries,
and no claim about REA's own correctness. This is one worked example, offered as prior art.

## Grounding references

- REA contributing guide: scope fit and fail-closed integration section; this issue is a
  proposal/question, not an integration request.
- Artifacts: https://github.com/LexLuthorPrimero/rxre-cleanroom (INDEX.md, OUTREACH.md, wc/INDEX.md,
  wc/SEAL_WC.txt, SHA256SUMS for both trees).
- Author affiliation: independent; no employment/NDA relation with GNU or with the REA maintainers.
