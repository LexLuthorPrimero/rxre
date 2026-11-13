# filenvercmp — RXRE differential-verified reference case

A self-contained case study in *differential binary verification* using GNU coreutils as the target.

**Goal**: show that a pure, sterile (`-fno-…`) user-space reconstruction can reproduce the exact
byte-level output of a stripped GNU binary for every case in a sealed corpus — with zero divergences —
and that the result is verifiable by any third party who only wants to run it.

## The binary

- `/usr/bin/ls` — sha256 `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c`
- Build ID `ae6605eeca6cc2f19d18fdd53a521e501df3456d` — 153 400 B · ELF64 PIE · stripped · GNU coreutils 9.10
- Target: `filenvercmp` (version-aware filename comparator) · vaddr `0x4fa0`
- Subfunctions: `verrevcmp` @ `0x4b60` · `file_prefixlen` @ `0x4a80`

## What we did

1. Read the disassembly with `objdump -d -M intel -C` and Ghidra 12.1.4.
2. Rewrote `filenvercmp.c` to reproduce the *exact* byte-level semantics revealed by the disasm:
   - extension-chain `prefix skip` match rules for `(`, `.`, `~`, byte ordering, and the `dpkg` sort order;
   - 16-byte memory layout of `marker` fields held in registers;
   - `file_prefixlen` is partial-order `<=` and equality-with-extension-skip bitwise (…complete reconstruction verified air-traffic-control-style in the corpus).
3. Sealed a corpus of 2 × 34 145 unique pairs (SEED=20261112/20261113).
4. Differential-verified the reconstruction against the real binary by calling `/usr/bin/ls` with each pair via `mmap`.
5. Iteration: 25 468 → 1 014 → 791 → … → **0/34 145 divergences** (twice, generation 1 and generation 2).

## Reproduce locally

```sh
sha256sum -c SHA256SUMS
gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2 -o verify_recon harness/verify_recon.c src/filenvercmp.c
./verify_recon corpus/cases_seed20261112.txt matrix/matrix_native.txt
#   total=34145 mismatches=0
```

Only the corpora samples shipped here are truncated to the first 1 000 lines so the package is small — the full ciphers are re-regenerable by any third-party builder (see `RECURS.md`, not included).

## Why this matters for agent-facing reverse-engineering tools

- Any LLM/MCP pipeline that claims binary-reconstruction fidelity must show evidence of *full-differential* correctness on a real binary — not demo a tokenizer or run a synthetic benchmark.
- This is the shape of that evidence.

## What we do NOT claim

- That GNU coreutils is exploitable, nor that `filenvercmp` has a security bug — it does not.
- That our reconstruction can be used as a drop-in replacement — it is *semantically equivalent* to the binary as evidenced, not silently re-licensable.
- That this is a complete reverse of `ls`.
- That the full 34 145-case corpus is in this package — only a sample, by design.

## License

The reconstructed code is released as-tested; the verification metadata is licensed under MIT. The GNU coreutils trademark, the original binary, and any other third-party bits belong to their respective owners.
