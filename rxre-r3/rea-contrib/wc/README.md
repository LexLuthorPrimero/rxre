# wc — RXRE differential-verified reconstruction of GNU `wc`

A self-contained contribution case: semantic reconstruction of `/usr/bin/wc`
(GNU coreutils 9.10) verified differentially against the real stripped binary,
with zero divergences, over **~38,700 sealed corpus checks** in two locales.

## Provenance

Everything in this directory except this `README.md` is **byte-identical** to
the published public package *rxre-cleanroom* (released 2026-11-12).
Verify it against the sealed manifest:

```sh
cd <contrib-root>   # directory containing this 'wc/'
sha256sum -c wc/SHA256SUMS
```

Only failures to match should be accepted as tampering; a clean run confirms
integrity of `src/wc_count.c`, `harness/verify_wc.c`, all 14 corpus files,
`INDEX.md` and `SEAL_WC.txt`.

Target binary: sha256 `81d614595c717be908fce809713702efd35ce5a56f5ab7cbc497d1a61eb1a38f`
· BuildID `07a56ef5bcfd9b400c0dc0441530607b3c7d65f8` · 61,448 B · stripped · dynamic ·
GNU coreutils 9.10 (see `wc/INDEX.md`).

## What is verified

| Corpus | Mode | Cases | Divergences |
|---|---|---|---|
| `cases_seed20261114.txt` | C locale, default L W B | 4,899 | 0 |
| `cases_seed20261115.txt` | C locale, default L W B | 4,914 | 0 |
| `cases_wcflags_seed20261116.txt` | C locale, 8 flag sets | 11,872 | 0 |
| `cases_wcL_seed20261117.txt` | C locale, `-L` + 16 flag sets | 13,072 | 0 |
| `cases_high_seed20261118.txt` | C + es_AR.utf8 (bytes altos + NBSP) | 2 × 1,184 | 0 |
| `cases_highutf8_seed20261120.txt` | C + es_AR.utf8 (multibyte) | 2 × 1,184 | 0 |

## Reproduce (anyone, ~2 min)

```sh
gcc -std=c11 -O2 -o verify_wc wc/src/wc_count.c wc/harness/verify_wc.c
./verify_wc wc/corpus/cases_seed20261114.txt wc/corpus/matrix_native_wc.txt C
#   total=4899 mismatches=0
```

All commands are listed in `wc/INDEX.md`. Use an explicit `C`/`utf8` mode argument
matching how the oracle was generated — auto-detection from the ambient locale
can produce spurious divergences.

## What is NOT claimed

- Not a 1:1 port of the disassembly (observational, seal-verified semantic
  reconstruction). Not a production drop-in for `wc`.
- `-m` only shown ≡ `-c` in LC_ALL=C (MB_CUR_MAX=1); wide Unicode chars (CJK
  width 2) not modeled — NOT_EXECUTED.
- UTF-8 `-L` full audit NOT_EXECUTED.
- Third-party verification (outside the original author) NOT_EXECUTED.
- No `PASS`/`PROVEN` claim is made beyond the sealed corpora and locales above.

## Why this matters for REA

REA's agent-facing workflows depend on claims that binary reconstruction and
analysis outputs are trustworthy. This package is a minimal, fully reproducible
demonstration of the *differential-verification* workflow applied to a real GNU
coreutils binary: how evidence of semantic fidelity can be packaged so that an
independent observer can falsify it with one compile and one command.

Contribution intent for `morluto/rea`: a worked example / cookbook entry, not a
runtime dependency. No code in REA needs to link against `wc_count.c`.
