# RXRE-PS5-012 — Final Report

Date: 2026-10-13
Subject: `GpuTilerCpuParity` investigation + RXRE causal-reasoning exercise

---

## A. State and preservation

| Item | Value |
|---|---|
| RXRE HEAD | `d754f2c14745e8495598f2f704a494839c9019c5` (unmodified this session) |
| KytyPS5-Source HEAD | `df5b9b92be7dfd463b47756b707d6d356a9f0550` |
| Build dir | `KytyPS5-Source/build` — **preserved throughout**, never deleted |
| Commits / branches / worktrees / PRs | none |
| S_ADD_U32 regression | re-verified passing after all changes (§E) |

**Provenance verified.** Before acting I confirmed the binary is newer than every modified source
(`find src tests -newer <binary>` → empty), so the executable corresponds to the current sources.

**No destructive cleanup.** The build directory, all objects and the SDL3/FFmpeg externals were kept.
The one destructive event is disclosed in the RXRE-PS5-011 report and did not recur here.

**Diagnostic instrumentation added** to `tests/ShaderRecompilerComputeTests.cpp` (see §C). Every block
is gated behind an environment variable and is **inert by default** — verified: a default run produces
zero `RXRE_DIAG`/`RXRE_HOST_CHECK`/`input-buffer check` output and fails at exactly the original point.

---

## B. GpuTilerCpuParity

### Reproduction (VERIFIED)

```
cd KytyPS5-Source/build
RXRE_HOST_CHECK=GpuTilerCpuParity \
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
  ./shader_recompiler_compute_tests
```

```
ShaderRecompilerComputeTests: GpuTilerCpuParity failed at detile bytes family=4 bpe=1: first mismatch at 8 of 2097152
```

Exit: abort via `Fail()` → `std::abort()`. **Deterministic**: identical message in 5 independent runs
across 2 binaries and 2 ICDs. Reported values independently confirmed, not assumed.

### Failing parameters (VERIFIED, measured at runtime)

`family=4` was **not** inferred from the number. Resolved through the enum at
`src/graphics/guest_gpu/tile.h:29-40` (0-based) → **`TileBlockFamily::Standard64KB3D`**.
The harness's own runtime probe printed:

```
block 64x32x32 size 65536  image 195x99x33  pitch 256
block_columns 4 block_rows 4 block_slices 2 storage 2097152
linear_pitch 256 linear_size 25344 linear_slice_stride 25344
tiled_slice_stride 1048576 info.LinearSize() 836352
width=195 height=99 depth=33 texels=637065 blocks_per_row=4
```

`4 × 4 × 2 × 65536 = 2,097,152` — reproduces the reported size exactly.

### Causal trace

```
TEST_INPUT   fill(&tiled, 28)  deterministic splitmix64 hash
   -> FORMAT_AND_LAYOUT   ImageInfo{extent 195x99x33, pitch 256, block 64x32x32, linear_size 25344}
   -> CPU_DETILE_PATH     convert_reference(): cpu[x] = tiled[s64_3d(x)]  (tile.cpp:876+)
   -> GPU_REFERENCE_PATH  TileManager::Detile -> fillBuffer(0) -> gpu_tiler_standard64_3d.comp -> copyBuffer -> readback
   -> COMPARISON          CompareWords-equivalent byte compare over 2097152
   -> FIRST_MISMATCH      linear 8
```

### Scope of the failure (VERIFIED)

Diagnostic sweep (`RXRE_DIAG_PARITY=1`, records instead of aborting) — **93 byte-level mismatches**:

| Families | Result |
|---|---|
| 0 Standard256B, 1 Standard4KB, 2 Standard4KB3D, 3 Standard64KB, 7 RenderTarget64KB, 8 Depth64KB | **pass** |
| **4 Standard64KB3D, 5 Prt64KB, 6 Prt64KB3D** | **fail** (detile *and* tile, all bpe 1/2/4/8) |

### Hypotheses and outcomes

| # | Hypothesis | Prediction if true | Result | Verdict |
|---|---|---|---|---|
| H1 | RX 550 / RADV / driver | lavapipe would pass | lavapipe fails **identically** | **REFUTED** |
| H2 | Embedded SPIR-V stale | fresh compile differs | byte-identical (14616 B) | **REFUTED** |
| H3 | Host fixture not reaching GPU | input readback differs | 472/472 readbacks, 0 diffs | **REFUTED** |
| H4 | `tile.cpp` vs shader formula differ | disassembly shows different ops | identical term-for-term; `spirv-dis` confirms | **REFUTED** |
| H5 | CPU oracle is wrong | independent model disagrees | independent Python model: **0/64** discrepancies | **not supported** |
| H6 | Wrong tiled address | GPU bytes found elsewhere in `tiled` | run `fe dc 41 7c 98 4d 3a 3c` occurs **nowhere** in 2 MiB, nor in any of salts 0–39 | **REFUTED** |
| H7 | Random/stale GPU state | varies run to run | bit-identical across runs and devices | **REFUTED** |
| **H8** | **Duplicated values ⇒ an additional writer** | observed duplication cannot be produced by the verified shader alone | **confirmed** | **PROVEN** |

### The decisive characterisation (VERIFIED)

The failure has **period 32** in linear space. Per-byte mask (`.` = match, `X` = mismatch):

```
lin   0 msk:........XXXXXXXX      lin  64 msk:........XXXXXXXX
lin  16 msk:........XXXXXXXX      lin  80 msk:........XXXXXXXX
lin  32 msk:XXXXXXXX........      lin  96 msk:XXXXXXXX........
lin  48 msk:XXXXXXXX........      lin 112 msk:XXXXXXXX........
```

Wrong lanes carry values owned by *other* positions, and each value appears **twice**:

```
gpu[8..15] = fe dc 41 7c 98 4d 3a 3c
gpu[40..47]= fe dc 41 7c 98 4d 3a 3c      (identical — a duplicate)
cpu[40..47]= fe dc 41 7c 98 4d 3a 3c      (so gpu[8..15] holds data belonging at 40..47)
```

Effective map: **`g(p) = p XOR (32 · (bit3(p) XOR bit5(p)))`** — effective values always satisfy
`bit5 == bit3`, a constraint the model never imposes. `bit3` feeds offset bit 9 via `(x<<6)&0x200`;
`bit5` feeds bit 15 via `(x>>5)<<15`.

### The deductive step that closes the search (PROVEN, no GPU needed)

The shader's linear address is

```
linear = z*slice_bytes + y*pitch_bytes + x*ELEMENT_BYTES
       = z*25344 + y*256 + x        with x<195<256, y<99<25344
```

This map is **injective**. Therefore *no* execution of the verified shader can write two distinct
values to one linear address. The observed duplication **requires an additional writer into the same
buffer**. This is what eliminates the shader, the driver and the hardware simultaneously.

### Root cause status: **NOT_DETERMINED**

Not VERIFIED, not INVALIDATED. One hypothesis survives and is untested:

> `TileManager::GetScratchBuffer` (`tiler.cpp:391-406`) **reuses** `m_scratch[0]/[1]` across calls and
> across families, reallocating only when `buffer->Size() < size`. An additional or partially-effective
> writer into the same scratch would explain a duplication the shader cannot cause.

I deliberately did **not** patch this speculatively — the injectivity proof predicts the duplication
would *vanish* under a forced-fresh scratch, and that experiment has not been run.

### Next discriminating experiment

Force a fresh scratch (bypass `m_scratch` reuse) and run **only** the family=4 bpe=1 detile.

| Outcome | Conclusion |
|---|---|
| Duplication disappears | scratch reuse is the cause — proceed to fix it and add a regression test |
| Duplication persists | read the scratch immediately before/after `fillBuffer` to determine whether the clear covers `0..836352`; a partial clear points at `scratch.size` vs. `linear_capacity` |

---

## C. Code changes

**No production behaviour was modified.** No defect was demonstrated, so nothing was patched.

All changes are in `tests/ShaderRecompilerComputeTests.cpp` (test-only), **inert unless the
corresponding env var is set** — verified by a default run producing zero diagnostic output:

| Gate | Purpose |
|---|---|
| `RXRE_DIAG_PARITY=1` | Record byte mismatches (index, count, hex window, sentinel flag) instead of aborting, enabling a full sweep in one run; plus a per-element map and the Standard64KB3D parameter dump |
| `RXRE_HOST_CHECK=<name>` | Run one harness self-check so it can be compared across devices without unrelated checks aborting first |
| `KYTY_SINGLE_CASE=<name>` | (from PS5-011) run one named case through the production harness |

Two additions inside `RXRE_DIAG_PARITY` are the ones that produced evidence:
- **input-buffer readback** — compares the GPU's view of the source buffer against the host fixture
  (this is what REFUTED H3);
- **per-element map + mask** — this is what revealed the period-32 duplication.

None relaxes an assertion, skips a test, or alters an expected value. `CompareWords` still aborts
with the original message when the gates are unset.

**Neighbouring regressions:** the 46 host checks preceding `CheckGpuTilerCpuParity` still pass, and
the S_ADD_U32 case still passes on the instrumented binary (§E).

---

## D. RXRE evolution

### Exercised on this real investigation

| Existing capability | Use |
|---|---|
| `registrar()` | 9 operations + 18 `results` rows as evidence (`res_parity_*`) |
| `registrar_investigacion()` | 12 research entries: claim / hypothesis / next_action |
| `investigacion()` | queries by session, kind and epistemic status |
| `registrar_dependency()` / `query_validation_chain()` | 7 dependencies for `GpuTilerCpuParity` |
| `registrar_remediation()` | proposed next experiment, left unverified |

**No schema, table or API was added.** The existing model expressed the whole investigation. The
`dependency_states` vocabulary guard (`MISSING|SATISFIED|OPTIONAL|NOT_DETERMINED`) correctly rejected a
mis-typed `OPEN` state — a working guard, not a gap.

### Questions RXRE answered from persisted data (after reopening the DB)

```
=== DESPUES DE REABRIR LA BASE DE DATOS ===
estado: ok | entradas: 12 | total: 12
PROVEN: 4   REFUTED: 4   SUPPORTED: 2   OPEN: 2
```

- *Earliest known divergence* → PROVEN hypotheses #16 (period-32 duplication), #18 (injectivity).
- *Which hypotheses were invalidated, and by which observation* → 4 REFUTED, each resolving to its
  evidence: `res_parity_lvp`+`res_parity_radv3`, `res_parity_spv`, `res_parity_input`, `res_parity_formula`.
- *Which experiment most sharply distinguished the remaining explanations* → the device ablation
  (`res_parity_lvp` vs `res_parity_radv3`) — it eliminated the entire hardware/driver class at once.
- *What justifies the current status* → every entry carries resolvable refs; none is an unbacked claim.
- *Why is something still OPEN* → `gap_kind=HUECO_DE_EVIDENCIA` on the scratch-reuse hypothesis
  distinguishes "open for want of evidence" from other reasons, without adding a field.
- *What is the next experiment* → `next_action` #22 with its expected discriminating outcomes.

Chronological reconstruction from timestamps works (ids 9→22, 11:34:04→11:34:39).

### Demonstrated limitation and the smallest fix — none was needed

Two real friction points appeared, and **both were resolved by using existing fields**, so no change
was made:

1. `refs` must resolve to real `res_*`/`op_*`/`edge:*` ids. My first attempt used free-text refs and
   was correctly rejected. Fix: record evidence with `registrar()` **first**. This is the system
   working as designed — enforcing traceability.
2. Ref-less duplicate entries from the rejected attempt polluted queries. Fixed by deleting the
   superseded rows. A future tool should surface this, but a manual cleanup was sufficient here,
   so building it would have been metadata growth, not capability.

**Honest assessment:** RXRE's existing model was sufficient for this investigation end-to-end. The
"evolution" demonstrated is *guided use*, not new capability. I am not claiming an improvement I did
not make.

---

## E. Final status

| Item | Evidence | Status |
|---|---|---|
| **S_ADD_U32 carry** (dest `0`, SCC `1`) | `ScalarArithmeticSccCarryBorrowOverflow ok`, EXIT=0, re-run after every change | **VERIFIED** |
| **S_ADD_U32 no-carry** (dest `0xFFFFFFFF`, SCC `0`) | same case, dwords 10–11 of the readback | **VERIFIED** |
| **GpuTilerCpuParity** | reproduced deterministically, 5 runs / 2 ICDs | **NOT_DETERMINED** — reproduced and heavily narrowed, cause not established |
| Root-cause status | 7 hypotheses REFUTED; injectivity proof localises to an additional writer | **NOT_DETERMINED** |
| Next experiment | fresh-scratch ablation | recorded, **not executed** |
| Focused regressions | 46 preceding host checks pass; diagnostic gates inert by default | **VERIFIED** |
| **Full test suite** | aborts at `CheckGpuTilerCpuParity` before the case loop | **BLOCKED** |
| **RXRE investigation lifecycle** | 12 entries / 18 evidence rows / 7 dependencies, reconstructed after reopen | **VERIFIED** |

### Root-cause status, stated plainly

`GpuTilerCpuParity` is **NOT_DETERMINED**. I did not fix it. What this iteration did establish:

- it is **not** the RX 550, RADV, Vulkan, or hardware (identical failure on an independent software driver);
- it is **not** stale SPIR-V, host→GPU corruption, or a `tile.cpp`/shader formula divergence;
- the CPU oracle is consistent with an independent model;
- the failure is a **duplicated-write pattern of period 32** in linear space;
- and a **deductive proof** shows the verified shader alone cannot produce that pattern, so the
  remaining search space is the scratch-buffer lifetime in `TileManager`.

That is a substantially narrower diagnosis than "NOT_DETERMINED, do not assume the RX 550 is
responsible" — the RX 550 is now affirmatively *excluded*, not merely unaccused.