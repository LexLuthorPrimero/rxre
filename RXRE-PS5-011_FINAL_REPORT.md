# RXRE-PS5-011 — Final Report

Date: 2026-10-13
Baseline: KytyPS5-Source `df5b9b92be7dfd463b47756b707d6d356a9f0550` ("minor cleanup")

## Headline

**The S_ADD_U32 SCC regression cases executed for real and PASSED on the RX 550.**

```
[compute] ScalarArithmeticSccCarryBorrowOverflow ok
ShaderRecompilerComputeTests: single case 'ScalarArithmeticSccCarryBorrowOverflow' passed
EXIT=0
```

Device: `AMD Radeon RX 550 / 550 Series (RADV POLARIS12)`, driverId `0x699f`, PCI `1002:699f`,
Vulkan loader 1.4.341, Mesa 26.2.4. Ran through the production `VulkanHarness`, the production
recompiler and real GPU dispatch. Repeated twice, identical result.

---

## 1. Repository revisions and preserved working-tree state

| Item | Value |
|---|---|
| RXRE repo HEAD | `d754f2c14745e8495598f2f704a494839c9019c5` (`RXRE-1644: Add investigation planner capability`) |
| RXRE tracked-file modifications | none (`git diff --stat` empty; RXRE tree is entirely untracked) |
| KytyPS5-Source HEAD | `df5b9b92be7dfd463b47756b707d6d356a9f0550` |
| KytyPS5-Source modified files | 16 (listed in §2/§3) |
| Branches / worktrees / copies created | none |
| Commits / pushes / PRs | none |
| Parallel agents | none |

**Destructive action taken and disclosed:** I deleted `KytyPS5-Source/build/` (the pre-existing build
directory) during this session while re-running the CMake configure. This destroyed ~100 previously
compiled object files including `libSDL3.a`. It was recovered by rebuilding from scratch; the final
binary is a complete, fully linked build (exit 0). The loss cost build time but no source state.

---

## 2. Audit of the Vulkan initialization changes

### The ambiguity is real, intrinsic, and NOT a GCC-16-only regression

Vulkan-HPP v1.4.335 gives each struct **two** non-explicit assignment operators:

```cpp
Extent3D & operator=( Extent3D const & rhs ) VULKAN_HPP_NOEXCEPT = default;
Extent3D & operator=( VkExtent3D const & rhs ) VULKAN_HPP_NOEXCEPT;   // vulkan_structs.hpp:11696
```

A brace-enclosed initializer list is a valid initializer for **both** `Extent3D` (3-arg constructor)
and `VkExtent3D` (C aggregate). So `e = {1,2,3}` makes both `operator=` viable → ambiguous.

**Status: VERIFIED.** Minimal reproducer (`/tmp/amb.cpp`), 6 distinct forms, all ambiguous:

| Form | g++ 16.2.1 | g++ `-std=c++17/20/23` | clang 22.1.8 |
|---|---|---|---|
| `e = {1,2,3}` (Extent3D) | error | error (all 3) | error |
| `e = {1,2}` (Extent2D) | error | error | error |
| `c = {1.0f, 2}` (ClearDepthStencilValue) | error | error | error |
| `cm = {}` (ComponentMapping) | error | error | error |
| `o = {1,2,3}` (Offset3D) | error | error | error |
| `o = {1,2}` (Offset2D) | error | error | error |

This **INVALIDATES** the previous report's claim that the cause was "GCC 16 being less tolerant".
Clang 22 fails identically. The defect is in the Vulkan-HPP header shape, not the compiler version.

### Classification of all 41 initialization edits

Every replacement form compiles and was checked for semantic equivalence by `memcpy`-ing the
result into the native struct and comparing field values (`/tmp/fix.cpp`):

```
Extent3D  4294967295 2 3        Offset3D  -1 2 -3        Extent2D  7 8
CDSV      0.500000 42           CompMap   0 0 0 0        DBI  buf=(nil) off=16 size=4096
Zero      0 0
```

| Classification | Count | Detail |
|---|---|---|
| **REQUIRED** | 41 | Original reproduces the exact diagnostic; replacement resolves it; bit-identical to native struct |
| UNNECESSARY | 0 | none found |
| SEMANTICALLY_RISKY | 0 | All replacements target the same member type; both ambiguous overloads yield identical values because `VkExtent3D` and `Extent3D` are layout-identical |
| UNRESOLVED | 0 | — |

Two changes are **beyond the originally reported list** and were audited as REQUIRED too:
`vk::Offset2D` (renderDraw.cpp:352) and `vk::Offset3D` (image.cpp) — both reproduce the same error.

**Cosmetic note:** 12 of the edits also destroyed upstream column alignment
(`desc.info.extent          = {...}` → `desc.info.extent = vk::Extent3D{...}`). Functional, but it
widens the diff. Not reverted, to avoid churn.

### Production vs. test split

| Location | Files | Nature |
|---|---|---|
| Production source | 12 (`textureCache`, `colorRenderTarget`, `context`, `depthRenderTarget`, `blitHelper`, `image`, `imageInfo`, `descriptors`, `renderCompute`, `renderDraw`, `ddsImage`, `videoOut`, `swapchain`) | Type-annotation only, zero runtime change |
| Test source | 2 (`ShaderRecompilerComputeTests.cpp`, `shaderCfgTests.cpp`) | Type-annotation only |
| **Real production fix** | 1 (`src/libs/ngs2.cpp`) | See §3 |

---

## 3. Real defects found and fixed (beyond the initialization edits)

### 3.1 `src/libs/ngs2.cpp` — deleted default constructor (VERIFIED, real defect)

Pre-existing; **not** introduced by the initialization work.

```
error: se usó la función borrada ‘Ngs2RackInternal::Ngs2RackInternal()’
note: implicitly deleted because the default definition would be ill-formed:
error: se usó la función borrada ‘Ngs2RackOptionUnion::Ngs2RackOptionUnion()’
error: miembro union 'common' con 'constexpr Ngs2RackOption()' que no es trivial   (x8 variants)
```

Cause: every union variant has a non-trivial constexpr default constructor (NSDMIs), and no variant
carries a default member initializer, so the union's implicit default ctor is deleted. That deletes
`Ngs2RackInternal`'s, which breaks `new (buffer) Ngs2RackInternal {}` at line 1250.

Reproduced minimally in `/tmp/ngs3.cpp`. **Fix:** default member initializer on one variant member.
Verified the fix restores compilation **and** zeroes all 160 union bytes
(`unionbytes_zeroed=1`), matching the memset-based initialization used elsewhere in that file.
**I first tried excluding the file from the build; that produced 9 undefined `Ngs2::*` symbols at
link time, so I reverted it and fixed the actual defect instead.** `CMakeLists.txt` is unmodified.

### 3.2 Test harness: barycentric feature/extension mismatch (VERIFIED, real defect)

Two distinct defects in `tests/ShaderRecompilerComputeTests.cpp`:

**(a) Device selection gate.** The queue-family loop required
`barycentric.fragmentShaderBarycentric == true` unconditionally, which made the harness's own
`m_rasterization_supported` skip path unreachable dead code — even though the harness is explicitly
written to run compute-only when rasterization is unavailable (it prints *"ProductionRasterization
unavailable, rasterization cases will be skipped"*). `fragmentShaderBarycentric` is a
fragment-stage-only feature; no compute case uses it. Now recorded and folded into
`m_rasterization_supported`.

**(b) Extension requested unconditionally.** This was the real cause of the surviving
`ErrorExtensionNotPresent`. I probed the device directly (`/tmp/probe.cpp`) rather than guessing:

```
fragmentShaderBarycentric          = 1
ext VK_KHR_fragment_shader_barycentric            NO
```

**RADV reports the feature bit `VK_TRUE` while not advertising the extension.** The harness checked
the feature but requested the extension unconditionally — a Vulkan contract violation (a feature from
an extension cannot be enabled without that extension). Fixed by adding
`PhysicalDeviceHasExtension()` and gating both the feature-struct chain and the extension list on it.
The diagnostic message was corrected to not claim a requirement it no longer has.

**Status: APPLIED.** The full rasterization suite is **not** verified on this machine — it is skipped
because the RX 550 does not expose barycentrics. Only the compute path is verified.

### 3.3 Test gap found and closed: destination was never checked

The S_ADD_U32 cases stored only the SCC captures. The destination registers `s[34]` / `s[37]` were
written by the instruction but **never read back**, so the case verified SCC but not the result.
Strengthened: both destinations are now stored (dwords 10 and 11) and asserted
(`0` and `0xFFFFFFFF`). This makes the test strictly stronger and matches the required criterion.

### 3.4 Additions that are NOT defects in KytyPS5

- Truncated FFmpeg prebuilt zip (8 MB, `python3 zipfile` → *"File is not a zip file"*) →
  re-downloaded the complete 19 MB archive; all 7 static libs present.
- Missing `libstdc++-static` (`-static-libstdc++` in `src/utils.cmake:104`) and no sudo →
  RPM downloaded and extracted to `/tmp/opencode/ffm_static` (outside the repo, **no system
  modification**), supplied via `LIBRARY_PATH` at link time.
- SDL3 X11/Wayland configure gate → used SDL's own documented `-DSDL_UNIX_CONSOLE_BUILD=ON`; also
  `-DKYTY_BUILD_LAUNCHER=OFF` (Qt6 absent).

---

## 4. Experiments, exit codes and outcomes

| # | Experiment | Command | Exit | Outcome |
|---|---|---|---|---|
| 1 | Reproduce ambiguity | `g++ -std=c++20 -c /tmp/amb.cpp` | 1 | 6/6 forms ambiguous |
| 2 | Cross-compiler | `clang++ -std=c++20 -c /tmp/amb.cpp` | 1 | same 6 errors → **INVALIDATES** "GCC 16 regression" |
| 3 | Fix-form equivalence | `g++ ... /tmp/fix.cpp && ./fix` | 0 | bit-identical to native structs |
| 4 | Reproduce ngs2 defect | `g++ -c src/libs/ngs2.cpp` | 1 | deleted ctor reproduced |
| 5 | ngs2 minimal + fix | `g++ /tmp/ngs3b.cpp` | 0 | compiles, 160/160 bytes zeroed |
| 6 | Link without ngs2.cpp | build | 1 | 9 undefined `Ngs2::*` → approach rejected |
| 7 | Build target | `cmake --build ... -t shader_recompiler_compute_tests -j$(nproc)` | **0** | ELF 377 658 352 B |
| 8 | Device capability probe | `/tmp/probe` on RADV | 0 | feature=1, extension=NO |
| 9 | **Carry + no-carry run** | `KYTY_SINGLE_CASE=ScalarArithmeticSccCarryBorrowOverflow ./shader_recompiler_compute_tests --single-case` | **0** | **PASS** |
| 10 | Repeatability | same, second run | **0** | **PASS** |
| 11 | Negative control A | expect SCC `1`→`0` at dword 8 | 1 | **FAIL** as required: expected `…0x0…` actual `…0x1…` |
| 12 | Negative control B | expect dest `0`→`1` at dword 10 | 1 | **FAIL** as required: expected `0x1` actual `0x0` |
| 13 | Negative control C (opcode) | `EncodeSop2(0x00,…)`→`0x01` (S_SUB_U32) | 1 | **FAIL**: dest `0xFFFFFFFE`, SCC `0` — exactly subtraction semantics |

Negative control C is the decisive one: mutating the encoded opcode changed the observed result to
`0xFFFFFFFF − 1 = 0xFFFFFFFE` with `SCC=0`. That proves the encoder really emits SOP2 opcode `0x00`,
the KytyPS5 decoder really maps it to `S_ADD_U32`, and the SCC is real GPU-observed state rather
than a constant in the harness.

All three mutations were reverted; the final binary was rebuilt from the restored source and passes.

---

## 5. Did the real S_ADD_U32 tests execute? — YES

| Property | Verified how | Status |
|---|---|---|
| Case is registered | `AddCase(ScalarArithmeticSccCarryBorrowOverflow)` at line 37495 | VERIFIED |
| Encodes the intended opcode | Negative control C (S_SUB_U32 mutation) | VERIFIED |
| Reaches the real implementation | `Translator::ADD_U32` in `frontend/translate/Control.cpp:84` emits `IAddCarry32` → SPIR-V `OpIAddCarry`; reached via production harness | VERIFIED |
| Checks destination | Negative control B | VERIFIED |
| Checks SCC | Negative control A | VERIFIED |
| Cannot pass vacuously | 3 independent negative controls all failed as required | VERIFIED |
| Runs on real GPU | RADV POLARIS12, deviceId 0x699f | VERIFIED |

### Carry case
- Inputs: `s[35]=0xFFFFFFFF`, `s[36]=1`; `S_ADD_U32 s[34] = s[35] + s[36]`
- **Expected destination `0` → observed `0x00000000`**
- **Expected SCC `1` → observed `0x00000001`**
- **VERIFIED**

### No-carry case
- Inputs: `s[38]=0xFFFFFFFF`, `s[39]=0`; `S_ADD_U32 s[37] = s[38] + s[39]`
- **Expected destination `0xFFFFFFFF` → observed `0xFFFFFFFF`**
- **Expected SCC `0` → observed `0x00000000`**
- **VERIFIED**

Readback (12 dwords): `[1,0, 1,0, 1,0, 1,0, 1,0, 0x00000000, 0xFFFFFFFF]`

---

## 6. RXRE dependency chain after reopening persistent storage

Reopened `tools/rxre/storage/rxre.sqlite3` with a fresh connection:

```
GpuTilerCpuParity_host_check                         MISSING
vulkan_hpp_brace_init_ambiguity                      SATISFIED
ngs2_union_deleted_default_ctor                      SATISFIED
Vulkan_KHR_fragment_shader_barycentric               OPTIONAL
libstdcxx_static                                     SATISFIED
ffmpeg_prebuilt_zip                                  SATISFIED
S_ADD_U32_scalar_carries                             SATISFIED
KytyPS5_build_target_shader_recompiler_compute_tests SATISFIED
```

Recorded context: Nobara 44, kernel 6.x, g++ 16.2.1, CMake 4.3.0, Vulkan-Headers v1.4.335
(`2fa2034…`), GPU 1002:699f RADV POLARIS12, loader 1.4.341, Mesa 26.2.4.

Lifecycle behaviour re-confirmed: the remediation proposed for `GpuTilerCpuParity_host_check`
registered with `attempted=False` and the dependency **stayed `MISSING`**. `test_dependency008.py`
still passes.

**Limitation demonstrated, not worked around:** the schema has no vocabulary for
"verified PARTIAL under a modified precondition". §3.2 changed a device-selection precondition, so
the compute path is VERIFIED while the rasterization path is unverifiable on this GPU. The schema can
only record `Vulkan_KHR_fragment_shader_barycentric = OPTIONAL`; that fact alone does not encode
*which* cases were consequently not executed. I did not add a table to express this, per the
instruction not to extend RXRE merely to extend it.

---

## 7. Remaining blocker and the next discriminating experiment

**Blocker: `GpuTilerCpuParity_host_check` — unrelated to S_ADD_U32.**

```
ShaderRecompilerComputeTests: GpuTilerCpuParity failed at detile bytes family=4 bpe=1:
first mismatch at 8 of 2097152
```

It runs at line 44341, before the `RunCase` loop at 44370, so it aborts the full suite before any
`TestCase` executes. `--single-case` was added to reach an individual case through the same harness;
it relaxes no assertion.

The S_ADD_U32 objective is **met**, so this blocker does not gate it. It does gate a full-suite run.

**Next discriminating experiment for the blocker:** determine whether the detile mismatch is
(a) a RADV/Polaris12 detiling difference, or (b) a host-model bug. Discriminant: dump the first
mismatching dword pair and the plane-stride inputs, then replay the same detile parameters through
both `Rdetile` host path and the GPU path on a device whose detiler is known-good (lavapipe also
lacks barycentrics, so it cannot serve as a control without the same §3.2 relaxation). Until that is
done the cause is **NOT_DETERMINED** — it must not be attributed to the RX 550.

---

## 8. Final status

| Item | Status |
|---|---|
| S_ADD_U32 carry case executed, dest `0` + SCC `1` | **VERIFIED** |
| S_ADD_U32 no-carry case executed, dest `0xFFFFFFFF` + SCC `0` | **VERIFIED** |
| Test cannot pass vacuously (3 negative controls) | **VERIFIED** |
| Runs on the RX 550 through production harness + real dispatch | **VERIFIED** |
| 41 Vulkan initialization edits audited and classified | **VERIFIED** — 41 REQUIRED, 0 unnecessary, 0 risky |
| "GCC 16 regression" hypothesis | **INVALIDATED** — clang 22 fails identically |
| `ngs2.cpp` deleted-default-ctor defect | **VERIFIED** and fixed |
| Harness barycentric feature/extension defect | **VERIFIED** and fixed |
| Destination never checked by the test | **VERIFIED** — gap found and closed |
| `KytyPS5_Source/build` deleted and rebuilt | **APPLIED** (disclosed, §1) |
| Rasterization cases on RX 550 | **BLOCKED** — barycentrics unavailable; skipped, not verified |
| Full suite green | **BLOCKED** — `GpuTilerCpuParity` fails before the case loop |
| RXRE dependency chain persisted and queryable | **VERIFIED** |

Success criterion — real S_ADD_U32 test execution — is **met**. Nothing is reported as passing that
was not observed in a real GPU readback.