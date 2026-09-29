# RX550 BC3/DXT5 GPU decompressor — Fase 2

Translation of the CPU reference decoder to a GCN compute shader, targeting
Polaris 12 (Lexa) on the RX 550.

---

## ⚠️ STATUS: RECONCILED AGAINST C, NOT RUN ON HARDWARE

**This shader has never executed on a GPU.**

- **Not run on hardware.** It has not been dispatched on the RX 550, the Intel
  iGPU, or any device. Nothing here has been observed to produce a pixel.
- **Not compiled by a GLSL front end.** `glslangValidator` was not installed
  when the SPIR-V in this directory was produced, so the GLSL has never been
  through a compiler. See "Compilation status" below for what changed.
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

## Format: RX550_BC4X, not BC3/DXT5

This directory was named `decompress_bc3.comp` until 2026-09-28 and the format
was called "BC3/DXT5" throughout. That name was false. The format is
**RX550_BC4X**:

| part | rule | conformant? |
|---|---|---|
| container | 8 B alpha with 3-bit indices + 8 B colour with 4-bit indices, 16 B, 4:1 | matches BC3 |
| colour | standard BC1: RGB565 endpoints, 4 values, interpolation in 5-bit space | **yes** |
| alpha, 8-value mode | `a[i] = ((8-i)*a0 + (i-1)*a1 + 3)/7`, `i = 2..7` | yes |
| alpha, 6-value mode | `a[i] = ((6-i)*a0 + (i-1)*a1 + 2)/5`, `i = 2..5`, then `a[6]=0`, `a[7]=255` | **BC4, not BC3** |

BC3's 6-value mode ends with `a[7] = a1`, a duplicate endpoint. This one spends
the two spare codes on the fixed extremes, which is BC4's rule. No shipping
Microsoft format combines them, so **there is no hardware block decoder for
RX550_BC4X**.

Two consequences, stated so they are not rediscovered:

- Every block whose alpha endpoints satisfy `a0 <= a1` — half the endpoint
  space — decodes differently in a real BC3 sampler than it does here. Do not
  be uploaded as `DRM_FORMAT_BC3` and sampled by any BC3 implementation.
- This compute shader *is* the decoder. That is the correct architecture for
  this format, not a workaround.

The colour sub-block is standard and is not in question. An earlier note in this
README suggested it was also non-standard; it is not.

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
| `decompress_bc3.spv` | see "Compilation status" |
| `test_decompress.c` | **not written** — needs `vulkan.h` and a live device |
| `Makefile` | **not written** — needs `glslangValidator` |

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

`decompress_bc3.spv` exists in this directory and is dated after the source was
last edited. It was **not produced by `glslangValidator`** — that tool is not
installed on this host. Its provenance is not established by anything in this
repository, and it is retained under `UNVERIFIED_UNTIL_RECHECKED` rather than
deleted, because deleting an artifact because a newer one appeared is the loss
this project has recorded before.

Its name matches the format. Do not infer from the `.spv`
extension that the file is valid SPIR-V for this shader.

To establish compilation properly:

```sh
sudo dnf install glslang-tools spirv-tools   # not yet done, needs authorization
glslangValidator -V decompress_bc3.comp -o decompress_bc3.spv
```

---

## To finish this file

1. Compile with `glslangValidator`, and establish the provenance of the existing
   `.spv` or discard it.
2. Write `test_decompress.c`: decode a corpus produced by
   `rx550_compress_block()` on the CPU, dispatch the same corpus through the
   shader on the GPU, and require byte-for-byte equality against
   `rx550_decompress_block()`.
3. Only then is the "not run on hardware" caveat at the top of this file lifted.
