# RX550 BC3/DXT5 GPU decompressor — Fase 2

Translation of the CPU reference decoder to a GCN compute shader, targeting
Polaris 12 (Lexa) on the RX 550.

---

## ⚠️ STATUS: WRITTEN, NOT EXERCISED

**This shader has never been compiled and never been run.**

- **Not compiled.** `glslangValidator` is not installed on this host. The GLSL
  has never been through a GLSL front end, so it is not known to be
  syntactically valid GLSL, let alone valid SPIR-V.
- **Not validated against hardware.** The shader has not executed on the
  RX 550, the Intel iGPU, or any device.
- **Agreement test not written.** The byte-for-byte comparison against
  `rx550_decompress_block()` — the criterion that would make this file
  evidence rather than a proposal — has not been run. It does not exist yet.

What *is* verified is the C encoder side (commit `05c6297`), which has 33/33
checks passing including a 65 536-pair exhaustive sweep of the alpha ramp
against the DXT5 specification.

**Do not treat this file as working code.** Treat it as a reviewed draft whose
logic was derived by reading a tested C function line by line, and which is
one compiler invocation away from being checkable.

---

## Why a translation and not a reimplementation

`rx550_decompress_block()` in `../compressor/rx550_compress.c` (banner at
line 492, body at 496–525) is the specification. It is **not** DXT5 as
published — and where the C and the published spec disagree, the C wins.

That distinction is not academic. This project already shipped one version of
this file that implemented the published spec:

- the alpha ramp used the BC4 `/5` divisor with a hardcoded `a[6]=0, a[7]=255`
- colour interpolation ran on 8-bit widened values instead of the quantised
  5-bit space
- it diverged from the encoder on 5 of 8 alpha palette entries

Every one of those would have produced a shader that decodes to plausible
pixels and matches nothing. The encoder at `05c6297` was corrected for the same
family of defect, verified by exhaustive sweep.

So: **every arithmetic operation in the `.comp` mirrors the C, including its
rounding offsets, its bit-extraction straddle, and its masks.** Where a shorter
GLSL form would be valid GLSL but an invalid translation, the C form is kept.

---

## File inventory

| file | state |
|---|---|
| `decompress_bc3.comp` | **written, not compiled, not run** |
| `test_decompress.c` | **not written** — needs `vulkan.h` |
| `Makefile` | **not written** — needs `glslangValidator` |
| `README.md` | this file |

---

## Target, measured

Confirmed on this host after the 2026-09-28 reboot, via `vulkaninfo`, on
`deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU` / `deviceID = 0x699f`
(Lexa), driver `radv`, Mesa 26.2.3, API 1.4.354:

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

**The CU count is not established.** `gfx_v8_0_get_cu_info()` counts CUs by
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
which RGB565 stores in 6 bits (`rx550_compress.c:100`). Only 5 of the 6 green
bits therefore reach the palette.

The shader reproduces the mask exactly. Changing it to `0x3F` for green would
be more correct in the abstract and would silently break byte-exactness with
the C decoder, which is the criterion this project is using.

This is a fidelity observation about the encoder, not a translation error, and
it is **not fixed here** — fixing it changes the encoder and invalidates the
33/33 suite. It is recorded for a later, separate decision.

---

## To finish this file

```sh
sudo dnf install glslang-tools vulkan-devel spirv-tools   # not yet done

glslangValidator -V decompress_bc3.comp -o decompress_bc3.spv
```

Then build the agreement test: decode a corpus of blocks produced by
`rx550_compress_block()` on the CPU, decode the same corpus through the shader
on the GPU, and require byte-for-byte equality against
`rx550_decompress_block()`.

Until that test runs and passes, the status at the top of this file stands.
