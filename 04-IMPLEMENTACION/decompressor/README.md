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

**Fase A (CPU, no GPU): COMPLETE**

| check | result |
|---|---|
| `shader_vs_c` | **0 of 4096** channels differ from `rx550_decompress_block()` |
| `test_alpha_ramp` | **0 of 65 536** endpoint pairs, against two independent transcriptions of the spec |
| `test_corpus_validate` | SPIR-V header valid; corpus deterministic; both alpha-ramp branches covered |
| `glslangValidator` | `rc=0`, 11 944 B, 2 986 words, magic `07230203` |

**Fase B (GPU dispatch): `NOT_WRITTEN`**

The shader has **never been executed on any GPU** — not the RX 550, not llvmpipe, not anything.
Every statement above is a claim about the algorithm and about the compiled artefact, never
about execution. `GFX_HWIP` remains `NOT_DETERMINED`.

Blocked on `vulkan-devel`, which is not installed and cannot be installed without privileges:

```
/usr/include/vulkan/vulkan.h   absent
dnf info vulkan-devel           no matching package
sudo -n true                   a password is required
```

Declaring the Vulkan structs by hand was attempted and abandoned: 37 compile errors, and a
duplicated `pNext` field that shifts a struct's layout silently rather than failing to compile.
`vk_pipeline_min.c` segfaults on RADV and llvmpipe for a reason that cannot be diagnosed without
the real headers — a layout fault presents as a crash, not a message. See AD-13.

When Fase B is written, two requirements are not optional:

- Identify the RX 550 by **PCI identity** `0x1002:0x699F`, never by enumeration index. This host
  exposes the Intel iGPU, the AMD device, and llvmpipe, and llvmpipe would happily accept the
  dispatch.
- **Validate the buffer before comparing it.** A dispatch that never ran leaves the output
  untouched, a byte-for-byte comparison reports zero discrepancies, and the test passes. Checking
  that the output is non-trivial first is what makes the result evidence.

---

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
| `test_decompress.c` | **not written** — needs `vulkan.h` and a live device. See AD-13 |
| `vk_pipeline_min.c` | abandoned: hand-declared Vulkan structs, `SIGSEGV` on RADV and llvmpipe, cause not diagnosticable without real headers |
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

## To finish this file

1. `sudo dnf install vulkan-devel` — currently absent, and the reason the GPU
   test is not written.
2. Write `test_decompress.c` with `#include <vulkan/vulkan.h>`: build a corpus
   with `rx550_compress_block()` on the CPU, dispatch the same corpus through
   the shader on the GPU, and require byte-for-byte equality against
   `rx550_decompress_block()`. Two requirements are not optional — identify the
   RX 550 by PCI identity rather than enumeration index, and validate the
   output buffer before comparing it, or a dispatch that never ran will pass.
3. Only then is the "not run on hardware" caveat at the top of this file lifted.
