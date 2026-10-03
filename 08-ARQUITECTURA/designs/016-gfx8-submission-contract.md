# 016 — GFX8 submission contract: IB → WPTR → doorbell → RPTR → completion

**CLASSIFICATION** `STATIC_ONLY` · no runtime was executed · no MMIO · no GPU
**TARGET** RX 550, `0000:01:00.0`, device `0x699f`, Polaris12 / GFX8
**EVIDENCE** `RESEARCH/kernelbuild/linux-7.1.3`, paths relative to
`drivers/gpu/drm/amd/`
**MODEL** `04-IMPLEMENTACION/rx550-mem/rx550_sub.{h,c}` — 100 asserts

`REFERENCE ≠ PRESERVATION`. Every entry below is separated into what the
hardware forces, what the Linux ABI forces, what amdgpu *chose*, and what
this driver decides.

---

## 1. The minimum path, reconstructed from the corpus

```
amdgpu_ib_schedule          amdgpu_ib.c:124
  ├─ amdgpu_ring_begin
  ├─ [AMDGPU_IB_FLAG_EMIT_MEM_SYNC] ring->funcs->emit_mem_sync   :235
  ├─ amdgpu_ring_emit_ib → gfx_v8_0_ring_emit_ib_gfx            :283
  ├─ amdgpu_fence_emit                                          :310
  └─ amdgpu_ring_commit → gfx_v8_0_ring_set_wptr_gfx            :333
```

**PROVEN — the ordering above is the code's own order.** It is not inferred.

`gfx_v8_0_ring_set_wptr_gfx` (`gfx_v8_0.c:6022-6034`) has **two mutually
exclusive publication mechanisms**:

| | branch | mechanism |
|---|---|---|
| A | `ring->use_doorbell == false` | `WREG32(mmCP_RB0_WPTR, wptr)` + `(void)RREG32(mmCP_RB0_WPTR)` readback |
| B | `ring->use_doorbell == true` | `*ring->wptr_cpu_addr = wptr` (WB memory) **and** `WDOORBELL32(ring->doorbell_index, wptr)` |

On GFX8, **branch B is the one taken**: `gfx_v8_0.c:1862` and `:1973` set
`ring->use_doorbell = true` and assign `ring->doorbell_index` from
`adev->doorbell_index.gfx_ring0` (gfx ring) or `mec_ring0 + ring_id` (MEC),
both guarded by `asic_type != CHIP_TOPAZ`.

**Correction to an earlier statement in this session.** I asserted that
GFX8 leaves `use_doorbell` false, from a `grep … | head -12` that truncated
before `gfx_v8_0.c`. `gfx_v8_0.c` has **7** occurrences, not 0. The refuting
evidence is `gfx_v8_0.c:1862`/`:1973`. The corrected claim is the opposite:
**GFX8 uses the doorbell path.**

## 2. Register table

Byte offset = register index × 4. Re-derived here from `gfx_8_0_d.h`
independently of the EP08 harness; **all nine agree exactly**, which is a
two-derivation cross-check, not a copy.

| register | index | byte offset | w | R/W | writer | reader | purpose | confidence |
|---|---|---|---|---|---|---|---|---|
| `mmCP_RB0_RPTR` | `0x21C0` | `0x008700` | 32 | R | hardware CP | driver, tests | read pointer: CP consumption cursor | HIGH — used at `gfx_v8_0.c` ring tests and by `amdgpu_test_ib` consumers |
| `mmCP_RB0_WPTR` | `0x3045` | `0x00C114` | 32 | W | driver branch A | hardware | write pointer publication (MMIO path) | HIGH — `gfx_v8_0.c:6031` |
| `mmCP_RB_WPTR_POLL_ADDR_LO` | `0x3046` | `0x00C118` | 32 | W | driver | hardware | low half of the address CP watches for completion | HIGH — `gfx_v8_0.c:4263` |
| `mmCP_RB_WPTR_POLL_ADDR_HI` | `0x3047` | `0x00C11C` | 32 | W | driver | hardware | high half of that address | HIGH — `gfx_v8_0.c:4264` |
| `mmCP_RB_WPTR_POLL_CNTL` | `0x21C2` | `0x008708` | 32 | W | **not on this path** | hardware | poll control | MEDIUM — see §5 |
| `mmCP_RB_DOORBELL_CONTROL` | `0x3059` | `0x00C164` | 32 | W | driver, **once at init** | hardware | *configures* which aperture is the doorbell | HIGH — `gfx_v8_0.c:4213` |
| `mmGRBM_STATUS` | `0x2004` | `0x008010` | 32 | R | hardware | driver | graphics engine status | LOW — no GFX8 consumer in this corpus |
| `mmGRBM_STATUS2` | `0x2002` | `0x008008` | 32 | R | hardware | driver | graphics pipe status; `!= 0` ⇒ busy | MEDIUM — `gfx_v8_0.c` idle checks compare against 8 |
| `mmCP_BUSY_STAT` | `0x219F` | `0x00867C` | 32 | R | hardware | driver | command processor busy | LOW — no GFX8 consumer in this corpus |

`GRBM_STATUS` and `CP_BUSY_STAT` are carried because the EP08 harness reads
them, **not** because a consumer was found. Stated as such rather than
inferred from the name.

`CP_RB_DOORBELL_CONTROL` field layout (`gfx_8_0_sh_mask.h:1745-1752`):
`DOORBELL_OFFSET` mask `0x7ffffc` shift 2 · `DOORBELL_EN` mask `0x40000000`
shift 30 · `DOORBELL_HIT` mask `0x80000000` shift 31.

## 3. The two publication mechanisms are different things

`gfx_v8_0_set_cpg_door_bell` (`gfx_v8_0.c:4193-4220`) runs **once at
initialisation** and only *configures* the register:

```
if (ring->use_doorbell)  OFFSET = doorbell_index, HIT = 0, EN = 1
else                     EN = 0
```

It is **not** the per-submission trigger. The trigger is
`WDOORBELL32(ring->doorbell_index, wptr)` → `amdgpu_mm_wdoorbell()`
(`amdgpu_doorbell.h:398`), a write to a **BAR aperture** at
`doorbell_index`, i.e. `byte = 4 × index`.

Therefore, and this is the distinction the contract must hold:

> **WB WPTR publication is not a doorbell, and
> `CP_RB_DOORBELL_CONTROL` is not a doorbell write.**
> The doorbell is a write to a *different aperture* than any of the nine
> registers above.

`rx550_sub_doorbell_published()` reports them as separate booleans, and
`t_doorbell_distinction` asserts that setting `doorbell_configured` does
**not** make `doorbell_published` true.

## 4. Ordering — what the code demonstrates, and what it does not

| step | demonstrated by | classification |
|---|---|---|
| coherence packet before descriptor | `amdgpu_ib.c:235` before `:283` | **PROVEN** (code order) |
| IB descriptor written, then fence, then commit | `:283`, `:310`, `:333` | **PROVEN** (code order) |
| WB WPTR write **and** doorbell write, doorbell second | `gfx_v8_0.c:6028-6029` | **PROVEN** (statement order) |
| doorbell write is *after* the WB write for a reason | — | **`NOT_DETERMINED`** |
| GPU observes the WB write before the doorbell | — | **`NOT_DETERMINED`** — needs a CPU/PCIe memory-ordering argument this corpus does not make |
| CP fetches the IB after the doorbell | — | **`NOT_DETERMINED`** — fetch semantics, no ISA document |
| RPTR advances after consumption | — | **observable**, but causal link to execution is **`NOT_DETERMINED`** |

The corpus orders the *statements*. It does not justify the ordering
*semantics*. Those two are separated deliberately and must not be merged.

## 5. WPTR polling on Polaris 12

**PROVEN — `mmCP_RB_WPTR_POLL_CNTL` is not programmed on the Polaris 12 path.**

`gfx_v8_0.c` writes it in exactly four places, all inside `*_mgcg_cgcg_init[]`
tables: `tonga` (`:303`), `fiji` (`:466`), `iceland` (`:567`), `cz` (`:673`).
The `case CHIP_POLARIS12` branch (`gfx_v8_0.c:783-788`) programs
`golden_settings_polaris11_a11` and `polaris11_golden_common_all`, and
**neither contains the register** (verified by scanning every
`static const u32 …[]` array in the file and reporting which contain it).

`POLL_ADDR_LO`/`HI` **are** written on this path, at `gfx_v8_0.c:4263-4264`,
with `wptr_gpu_addr`.

**This is an absence of programming and nothing more.** It does **not**
establish that polling is enabled, disabled, sufficient, or irrelevant —
those require hardware observation. `rx550_sub_poll_cntl_value()` returns a
value, not a conclusion.

## 6. Contract — the model

`rx550_sub.h` defines the submission object and a strictly forward state
machine:

```
CREATED → READY → PUBLISHED → CONSUMPTION_OBSERVED → COMPLETED → RETIRED
```

`RX550_SUB_CREATED` … `RX550_SUB_RETIRED` — six states, no others.

**`EXECUTED` is deliberately absent.** The corpus provides no observation
distinguishing "the CP consumed the commands" from "the CP executed them on
the shader". Carrying that state would manufacture the inference this
project is forbidden to make. `rx550_claim` therefore has exactly one
reachable value, `RX550_CLAIM_CONSUMPTION`; `RX550_CLAIM_EXECUTION` exists
in the enum as an explicit, unreachable, EXTERNAL boundary.

`t_no_execution_inference` constructs the strongest case the corpus allows —
`WPTR == RPTR == end of submission`, fully consumed, fully completed — and
asserts the claim is still `CONSUMPTION`.

Rules the model enforces:

| rule | why |
|---|---|
| `create` takes a **buffer**, not an address | the address space must not be lost between layers |
| a buffer must be `PUBLISHED` | an unpublished buffer has no GPU-visible address |
| a VRAM physical address is refused | it is not what the descriptor carries |
| WPTR must **strictly** advance | a ring cursor that does not move published nothing |
| an incomparable RPTR reading is refused, not compared | comparing across windows manufactures progress |
| `RPTR == WPTR_before` yields **no** claim | no observable progress |
| completion requires a positive caller statement | this component cannot observe memory |
| ownership is checked on retire | a half-valid ownership chain hides a use-after-free |

No wraparound is modelled: nothing in the closed path needs it, and
inventing a ring size would be inventing a constraint.

## 7. Unknowns

| question | state |
|---|---|
| what hardware unit fetches the IB | `NOT_DETERMINED` |
| whether WB-before-doorbell ordering is required, or incidental | `NOT_DETERMINED` |
| RPTR poll semantics (`POLL_CNTL` unprogrammed) | `NOT_DETERMINED` |
| whether `DOORBELL_HIT` or `DOORBELL_EN` has a functional role per submission | `NOT_DETERMINED` |
| meaning of `GRBM_STATUS2 == 8` as an idle predicate | `NOT_DETERMINED` — the comparison exists, its meaning is not documented here |
| GTT vs VRAM placement of the doorbell aperture | `DEFERRED` — belongs to the BAR/aperture component |

## 8. Discriminants for later runtime work

1. **Doorbell-load-bearing.** Arm B of EP08 suppresses the doorbell write.
   If the ring still consumes, the doorbell is not the sole trigger.
   Discriminates: doorbell ⇒ consumption.
2. **POLL irrelevance.** Observe `POLL_CNTL` and `POLL_ADDR_*` across a
   submission. Discriminates whether polling is active with the register
   unprogrammed on Polaris 12.
3. **RPTR vs execution.** RPTR advance and completion-sequence update are
   *separate* observations. Only if the completion sequence advances
   without RPTR moving, or vice versa, does the two separate.
   Discriminates: consumption ≠ completion.
4. **WB vs doorbell independence.** A submission published by WB write only,
   with the doorbell suppressed, discriminates whether the WB write alone
   can advance the ring.

## 9. Dependencies

| depends on | state |
|---|---|
| GPU address space, GART window, buffer lifetime | `CLOSED` — `ADDRESS-SPACE.md` |
| PDB0 / VMID 0 page table | `CLOSED` — `CONTRACTS.md` §B, §C |
| CPU→GPU coherence packet ordering | `CLOSED` — `CONTRACTS.md` §A |
| PM4 INDIRECT_BUFFER encoder | `CLOSED` — `rx550-pm4` |
| BAR/aperture mapping (where the doorbell write lands) | `OPEN` — next static task |
| Completion mechanism (WRITE_DATA vs EOP) | `PARTIAL` — P-8 `CLOSED` for teardown; first-path choice `DEFERRED` |
| GART window base/size on this board | `DEFERRED_RUNTIME` |

## 10. Validation

5 binaries, **313 assertions, 0 failures, 0 warnings** under
`-Wall -Wextra -Werror -Wconversion -Wsign-conversion -Wpedantic -Wcast-qual
-Wshadow -Wstrict-prototypes`.

Mutation testing: **32 detected**, 6 inconclusive (build failure — the
mutation left a parameter unused, so the property was never exercised),
3 equivalent-by-construction, 3 sed patterns that did not apply.

The equivalent mutations are recorded in `CONTRACTS.md` so they are not
mistaken for missing coverage.

## 11. Corrections made in this task

| claim | correction | refuting evidence |
|---|---|---|
| "GFX8 leaves `use_doorbell` false" | **wrong**; GFX8 uses the doorbell path | `gfx_v8_0.c:1862`, `:1973` — my grep was truncated by `head -12` |
| "`POLL_CNTL` is programmed on GFX8 with `0x00900100`" | **wrong**; that value is in the Tonga table only | array scan: it appears in `tonga/fiji/iceland/cz_mgcg_cgcg_init[]` only, never in the Polaris 12 tables |

The second error was mine and it nearly became a false contradiction against
the task premise. Recording both because a truncated search producing a
confident negative is the exact failure the project rules forbid.
