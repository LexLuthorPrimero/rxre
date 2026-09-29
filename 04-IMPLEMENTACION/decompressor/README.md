# RX550 BC3/DXT5 GPU decompressor — Fase 2

Translation of the CPU reference decoder to a GCN compute shader, targeting
Polaris 12 (Lexa) on the RX 550.

---

## ⚠️ STATUS: RECONCILED AGAINST C, NOT RUN ON HARDWARE

**This shader has never executed on a GPU.**

- **Not run on hardware.** It has not been dispatched on the RX 550, the Intel
  iGPU, or any device. Nothing here has been observed to produce a pixel.
- **Now compiled by a GLSL front end.** `glslangValidator` 11:16.3.0 builds it
  from this directory: `rc=0`, 11 944 B, 2 986 SPIR-V words, magic `07230203`.
  An earlier revision of this file said the GLSL had never been through a
  compiler; that was true when written and is no longer. `glslangValidator` is
  not installed system-wide, it is invoked by path from the `Makefile`.
  See "Compilation status" below.
- **Agreement with the C is established arithmetically**, by
  `shader_vs_c.c`: the palette and index-extraction arithmetic is reconciled
  channel by channel against `rx550_decompress_block()`. 0 of 4096 channels
  disagree over a 64-block corpus.

That last item is `SIMULATED_ARITHMETIC`, not hardware evidence. A validator that
models the shader in C proves the two agree under the model; it cannot prove the
GLSL compiles, that the compiler preserves the arithmetic, or that the GPU
produces the modelled values. The same failure mode that produced the
non-conformant alpha ramp in commit `05c6297` — two implementations agreeing
with each other and both disagreeing with the format — is what a modelled
comparison cannot rule out on its own.

---

## Format: BC3/DXT5

| part | rule | conformant? |
|---|---|---|
| container | 8 B alpha with 3-bit indices + 8 B colour with 4-bit indices, 16 B, 4:1 | **yes** |
| colour | standard BC1: RGB565 endpoints, 4 values, interpolation in 5-bit space, always 4-colour mode | **yes** |
| alpha, 8-value mode (`a0 > a1`) | `a[i] = ((8-i)*a0 + (i-1)*a1 + 3)/7`, `i = 2..7` | **yes** |
| alpha, 6-value mode (`a0 <= a1`) | `a[i] = ((6-i)*a0 + (i-1)*a1 + 2)/5`, `i = 2..5`, then `a[6]=0`, `a[7]=255` | **yes** |

Endpoint order is BC3's: `a0` is the block alpha **maximum**, `a1` the **minimum**, so `a0 > a1`
is the ordinary case and selects the 8-value ramp. The encoder now follows that convention
(D19a, commit `44bc133`); before it, `a0 = mn + inset` and `a1 = mx - inset` meant `a0 <= a1`
always, and the 8-value branch was never exercised. Measured by
`test_corpus_validate`: coverage of the 8-value branch went from **0 of 64 blocks to 59 of 64**.

**Two claims this file previously made, both wrong, and now removed.** It is worth recording
because both were asserted confidently and both would have misled a reader:

1. That the format was "**RX550_BC4X**, not BC3/DXT5", on the grounds that the 6-value mode's
   `a[6]=0, a[7]=255` is BC4's rule rather than BC3's. It is BC3. BC3's alpha sub-block uses the
   *same* two-mode ramp as BC4 — the formats differ in container (BC3 carries a colour block, BC4
   does not), not in the ramp. The name `RX550_BC4X` denoted a format that does not exist. See
   AD-8.
2. That blocks "decode differently in a real BC3 sampler". They do not: the ramp is indexed by
   whichever pair the block declares, so a conformant BC3 decoder reproduces these blocks exactly.

Rounding: the `+3` and `+2` are rounding terms of the Microsoft D3D9/DXT5 definition (AD-11).
`bcdec` v0.985 truncates instead and therefore diverges from the specification on ~82.9 % of
endpoint pairs, with a maximum error of 1 of 255. Blocks here follow the specification, not
`bcdec`, and will render 1 LSB differently in tools built on `bcdec`.

---

## Validation status

**Fase B (GPU dispatch): COMPLETE. The shader runs on the RX 550.**

```
[0] 1002:699f  AMD Radeon RX 550 / 550 Series (RADV POLARIS12)   <- target, by PCI identity
[2] 10005:0000 llvmpipe                                           <- present, NOT selected
[ OK ] vkCmdDispatch(4,1,1), submit and fence completed
[ OK ] 4005 of 4096 bytes non-zero
[ OK ] no word retains the 0xDEADBEEF poison pattern
  blocks differing : 0 of 64
  bytes differing  : 0 of 4096
RESULT: GPU == CPU.          rc=0
```

Three consecutive runs, identical. Alpha and colour both match: the comparison covers all 4096
bytes, not one channel.

**Fase A (CPU, no GPU): COMPLETE**

| check | result |
|---|---|
| `shader_vs_c` | **0 of 4096** channels differ from `rx550_decompress_block()` |
| `test_alpha_ramp` | **0 of 65 536** endpoint pairs, against two independent transcriptions of the spec |
| `test_corpus_validate` | SPIR-V header valid; corpus deterministic; both alpha-ramp branches covered |
| `glslangValidator` | `rc=0`, 11 672 B, 2 918 words, magic `07230203` |

### What each test can and cannot detect

This is the part worth reading. The three defects that made the shader wrong were **all invisible
to the CPU-side validator**, which reported 0 of 4096 with every one of them present:

| defect | caught by |
|---|---|
| colour index: `& 0xFF` where the C reads 2 bits, so the `& 3` kept the byte's **high** two bits; pixels 2 and 3 of each group of 4 took a neighbour's index. The `else` branch also read past the block for `p = 8..15` | GPU execution only |
| `vkCmdPushConstants` never issued, so the shader bounded its dispatch with uninitialised memory | GPU execution only |
| `DISPATCHES` computed as `ceil(64/256) = 1` when the shader maps one invocation to a **pixel**: a 256-invocation workgroup covers 16 blocks, so 4 were needed | GPU execution only |

`shader_vs_c` models the shader's arithmetic in C and **does not compile the GLSL**. It cannot see
a missing Vulkan call, a wrong dispatch count, or an out-of-bounds read. Its result is worth
having and is narrower than its name suggests.

### Why the output is validated before it is compared

A dispatch that never runs leaves the output buffer as it was initialised. Compared byte for byte
against the CPU reference that gives **zero discrepancies and a pass**. The two checks above —
the output is non-trivial, and no word retains the poison pattern — are what make the result
evidence. Without them, defect 2 would have produced an empty `PASS`.

### What a pass does not establish

- `GFX_HWIP` remains `NOT_DETERMINED`; this test neither queries nor infers the gfx generation.
- Schema validity of the SPIR-V is `NOT_AVAILABLE` — `spirv-val` is not installed. A driver
  accepting a module is evidence about that driver.
- The corpus is deterministic and synthetic: a regression guard, not an exhaustive proof.
- One dispatch measures no performance.

## Why a translation and not a reimplementation

`rx550_decompress_block()` in `../compressor/rx550_compress.c` is the
specification for this shader. Every arithmetic operation in the `.comp` mirrors
it, including rounding offsets, the bit-extraction straddle, and the masks.
Where a shorter GLSL form would be valid GLSL but an invalid translation, the C
form is kept and marked.

This file has been wrong before, in both directions, and the record is worth
keeping:

- A version asserted "the C is the specification; it is **not** DXT5 as
  published, and where the two disagree the C wins." It encoded a `/7`-everywhere
  alpha ramp. At the time it was written, `rx550_compress.c` carried the same
  non-conformant ramp, so encoder and decoder agreed by construction while both
  disagreed with the format. A mutually consistent pair of wrong
  implementations passes every round-trip test. That is the failure mode, not a
  proof of conformance.
- The next version inverted the claim to "DXT5/BC3 conformant" while keeping
  `/5` with the `0`/`255` extremes — which is the BC4 rule, not DXT5's.

The resolution is that neither "conformant to DXT5" nor "the C overrides the
spec" is a usable description of this project. The format is standard BC3/DXT5, it is
defined by the C, and its conformance is established against the transcribed
rule, not against the C it is derived from.

---

## File inventory

| file | state |
|---|---|
| `decompress_bc3.comp` | **written; arithmetically reconciled with C; not run on hardware** |
| `shader_vs_c.c` | **written and run** — the arithmetic reconciliation |
| `shader_vs_c` | built binary of the above |
| `decompress_bc3.spv` | built by `make`; see "Compilation status" |
| `test_corpus_validate.c` | **written and run** — Fase A: validates the artefact, builds a deterministic corpus, measures coverage of both alpha-ramp branches |
| `test_decompress.c` | **written and run** — Phase B, the GPU agreement test. 0 of 4096 bytes differ |
| `vk_pipeline_min.c` | abandoned: hand-declared Vulkan structs, `SIGSEGV` on RADV and llvmpipe. Superseded by `test_decompress.c`, which uses the real headers |
| `Makefile` | **written** — `all` · `test` · `check-codec` · `check-spirv` · `clean` |

---

## Target, measured

Confirmed on this host after the 2026-09-28 reboot, via `vulkaninfo`, on
`deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU` / `deviceID = 0x699f`
(Lexa), driver `radv`:

| limit | value |
|---|---|
| `maxComputeSharedMemorySize` | 65536 (64 KB) |
| `maxComputeWorkGroupInvocations` | 1024 |
| `maxComputeWorkGroupSize` | 1024 × 1024 × 1024 |
| `maxComputeWorkGroupCount` | 65535 × 65535 × 65535 |
| `maxStorageBufferRange` | 4294967295 |
| `maxPushConstantsSize` | 256 |

`local_size_x = 256` is 4 wavefronts of 64 lanes. It fits inside one CU
without exceeding 10 waves/SIMD, and uses 1/4 of the invocation limit.

**The CU count is `NOT_DETERMINED`.** `gfx_v8_0_get_cu_info()` counts CUs by
reading the hardware register `RLC_CU_BUSY` via
`gfx_v8_0_get_cu_active_bitmap()`; there is no per-ASIC table in the driver
source, and the driver publishes the count through `amdgpu_info` in **debugfs**,
which is not exposed on this host. The `4 CUs` figure that circulated in the
design discussion is unsourced. With 512 shaders and 64 lanes per CU, 8 is
consistent with the hardware; treat it as `NOT_DETERMINED` until read. It
affects dispatch width, not the shader body.

---

## Known deviation, deliberately reproduced

`colour_palette()` masks **all three** channels with `0x1F`, including green,
which RGB565 stores in 6 bits. Only 5 of the 6 green bits therefore reach the
palette.

The shader reproduces the mask exactly. Changing it to `0x3F` for green would
be more correct in the abstract and would silently break byte-exactness with
the C decoder, which is the criterion this project is using.

This is a fidelity observation about the encoder, not a translation error, and
it is **not fixed here** — fixing it changes the encoder. It is recorded for a
later, separate decision. Note that it is a lossy choice in the encoder, not a
format requirement: the BC1 colour rule does not mandate discarding the sixth
green bit.

---

## Compilation status

`decompress_bc3.spv` in this directory is produced from `decompress_bc3.comp` by the `Makefile`:

```sh
make decompress_bc3.spv
# /home/lucas/glslang/build/StandAlone/glslangValidator -V decompress_bc3.comp -o decompress_bc3.spv
```

`glslangValidator` was built on this host on 2026-05-02 and is **not** installed system-wide and
not in `PATH`; the `Makefile` invokes it by absolute path and `GLSLANG=` overrides that. It is
`glslang` 11:16.3.0, SHA256 `202cd086…`.

An earlier revision of this file recorded the module as having **no established provenance**,
retained under `UNVERIFIED_UNTIL_RECHECKED`, because the tool was not available. That is resolved:
the tool exists and the `Makefile` regenerates the module on demand. A stale module is still
possible if the `.comp` is edited without rerunning `make` — `test_corpus_validate` fails when the
`.spv` is older than the `.comp`, which is the check that catches it.

**What compilation does not establish.** `rc=0` means the GLSL is syntactically valid and
translated to SPIR-V. It does **not** mean the module is schema-valid: `spirv-val` is not
installed on this host (`NOT_AVAILABLE`), and a driver accepting a module is evidence about that
driver, not about the specification. It does not mean the codes exist on GFX8 hardware, and it
certainly does not mean the shader runs.

---

## What is left

Fase 2 is complete as a correctness exercise. What it does not do is measure anything:

1. `GFX_HWIP` is `NOT_DETERMINED`. Nothing here queries the gfx generation, and no shader in
   this project has established it. Closing that needs a query against the driver, not a shader.
2. `spirv-val` is not installed, so schema validation is `NOT_AVAILABLE`. Installing
   `spirv-tools` would close it.
3. Performance is unmeasured. One dispatch of 64 blocks says nothing about throughput; a
   benchmark is a separate experiment with its own `NOISE` floor and control.
4. The corpus is 64 synthetic blocks. A representative real-texture corpus would be a stronger
   guard, and would also settle the `RX550_ALPHA_INSET_STEPS` question (AD-10) that the synthetic
   corpus could not.
