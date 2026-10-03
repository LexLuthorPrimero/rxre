# CONTRACTS — visibility, PDB0/PTE, and the rx550-mem ↔ rx550-pm4 boundary

Closes batch A, B, C, D. Sources: project kernel corpus
(`RESEARCH/kernelbuild/linux-7.1.3`), paths relative to `drivers/gpu/drm/amd/`.
Classification per project rules. `REFERENCE ≠ PRESERVATION`: where amdgpu's
behaviour is a policy choice rather than a hardware constraint, it is labelled
as policy and the divergence from it is stated.

---

# A — CPU→GPU VISIBILITY

## A.1 What `AMDGPU_IB_FLAG_EMIT_MEM_SYNC` is

| question | answer | evidence |
|---|---|---|
| who requests it | **every** `amdgpu_ib_get()`, unconditionally | `amdgpu_ib.c:80` — `ib->flags = AMDGPU_IB_FLAG_EMIT_MEM_SYNC` |
| where it is decided | there is no decision; it is always on for a suballocator IB | same |
| who consumes it | `amdgpu_ib_schedule()` → `ring->funcs->emit_mem_sync` | `amdgpu_ib.c:235-236` |
| when | **before** `amdgpu_ring_emit_ib()` | `:235` vs `:283` |
| which HW unit | the GFX IP's ring func table | `gfx_v8_0.c:6913` (gfx ring) / `:6947` (compute ring) |

## A.2 SURFACE_SYNC vs ACQUIRE_MEM — two different packets

| | gfx ring | compute ring |
|---|---|---|
| function | `gfx_v8_0_emit_mem_sync` | `gfx_v8_0_emit_mem_sync_compute` |
| source | `gfx_v8_0.c:6761` | `gfx_v8_0.c:6774` |
| packet | `PACKET3_SURFACE_SYNC` opcode `0x43` | `PACKET3_ACQUIRE_MEM` opcode `0x58` |
| header | `0xC0034300` (count 3) | `0xC0055800` (count 5) |
| total DW | 5 | 7 |
| size/base width | 32-bit only | 64-bit (`_SIZE_HI`, `_BASE_HI` present) |
| opcodes | `vid.h:201`, `vid.h:334` | |

**Both use the identical coherence control word** `0x28C40000`, being
`TCL1(22) | TC(23) | SH_KCACHE(27) | SH_ICACHE(29) | TC_WB(18)`
(`vid.h:215-224`), with `CP_COHER_SIZE = 0xFFFFFFFF`, `CP_COHER_BASE = 0`,
poll interval `0x0A`.

`DESIGN_CHOICE` / **AMDGPU POLICY, not a hardware requirement**: that these
*five* caches are the ones invalidated, that the size is "all ones", and that
the poll interval is 10. The corpus shows what this driver chose. No ISA
document was available, so what the hardware *requires* is `NOT_DETERMINED`.

`DERIVED`: the invalidated set is texture (TCL1), L2 (TC, TC_WB) and shader
instruction/data caches (SH_ICACHE, SH_KCACHE). The IB body is a command
stream the CP fetches; whether the CP's own path is covered by these bits is
`NOT_DETERMINED`.

## A.3 Direction

**CPU→GPU.** The mechanism is a *packet in the ring*, not a CPU barrier. It
does not make the CPU wait, and it carries no CPU-side ordering. The ordering
it establishes is *within the command stream*: the invalidate is encountered
before the descriptor that points at freshly written memory.

`NOT_DETERMINED`: whether a CPU-side barrier is *also* required before
publishing the ring. The corpus does not settle it, and a Linux
`wmb()`-equivalent is a **LINUX REQUIREMENT** question, not a hardware one.

## A.4 What the first driver must expose

A contract, not a mechanism: *the coherence packet must appear in the ring
before the IB descriptor that points at CPU-written memory.*
`rx550_vis_order_ok(sync_off, desc_off)` encodes exactly that and rejects
equality (overlap is not ordering) and absence.

## A.5 Status

`CLOSED` for the ordering contract and the packet bytes.
`DEFERRED_RUNTIME`: whether the hardware accepts the stream without a
coherence packet, i.e. whether the packet is load-bearing or merely
conservative. This is directly testable on hardware later and is the natural
discriminator for the EP08 arm B.

---

# B + C — VMID-0 PAGE TABLE

## B.1 Geometry — PROVEN

| item | value | source |
|---|---|---|
| PDB0 depth | **0 → flat, one level** | `gfxhub_v1_0.c:218-230` programs `PAGE_TABLE_DEPTH` from `vmid0_page_table_depth`, which `gmc_v8_0.c` **never assigns** (0 matches) |
| block size | **0** | same absence, `amdgpu_gmc.h:325` |
| translation granularity | **2 MiB** | `amdgpu_gmc.c:1136-1139` — `2^block_size << 21` |
| PTE physical address | mask `0x000000FFFFFFF000`, **40-bit PA**, 4 KiB | `gmc_v8_0.c:1134` — the source comments it "40 bit PA" |
| PDB0 location | VRAM, `PAGE_SIZE` aligned, contiguous, CPU-accessible | `amdgpu_gmc.c:1145-1150` |
| layout | first *n* entries are PTEs for VRAM; entry *n+1* points to a large block for system memory | `amdgpu_gmc.c:1125-1141` |
| VMID for a job-less submission | **0** | `amdgpu_job.h:42` — `AMDGPU_JOB_GET_VMID(job) = ((job) ? job->vmid : 0)`; the test path passes `job = NULL` (`gfx_v8_0.c:898`) |

## B.2 Flag word — PROVEN positions, POLICY for the values

Bit positions from `amdgpu_vm.h:57-70`: `VALID` 0, `SYSTEM` 1, `SNOOPED` 2,
`EXECUTABLE` 4, `READABLE` 5, `WRITEABLE` 6, `FRAG(x)` 11:7.
`AMDGPU_PDE_PTE` = bit 54 for any gfx below v12 (`amdgpu_vm.h:141-142`),
which includes GFX8. Bit 63 (`PDE_PTE_GFX12`) does **not** apply.

The word `amdgpu_gmc.c:1147-1151` installs:

```
EXECUTABLE | VALID | READABLE | WRITEABLE | SNOOPED | FRAG(0+9) | PDE_PTE
= 0x00400000000004F5
```

Classification, separated as required:

| bit | classification |
|---|---|
| positions of VALID/READABLE/WRITEABLE/SNOOPED | **HW REQUIREMENT** (field layout) |
| **which** of them are set | **AMDGPU POLICY** |
| `EXECUTABLE` set by default | **AMDGPU POLICY** — a GART for commands may not need it; `gmc_v8_0.c:961` sets it, and a read-only GART would not |
| `FRAG = 9` | **AMDGPU POLICY**; hardware meaning of FRAG is `NOT_DETERMINED` |
| `SYSTEM` not set | **AMDGPU POLICY** |

**MTYPE does not exist on GFX8.** `AMDGPU_PTE_MTYPE_*` are defined only for
VG10 (v9+), NV10 and GFX12 (`amdgpu_vm.h:97-126`); `gmc_v8_0.c:961` sets no
MTYPE at all, while v6/v7 set the flags to 0. The corpus comment
`//TODO it is UC` at `amdgpu_gmc.c:1135` is about MTYPE and **does not apply
to GFX8** — there is no cacheability field to set.

## B.3 The design consequence that matters

**With depth 0 and 2 MiB granularity, a 20-byte IB consumes an entire 2 MiB
PDB0 entry.** The hardware translates per entry, not per buffer. This is
`DERIVED` from B.1 and is asserted in `t_index()`
(`rx550_pdb0_entries_for(va, 20, base) == 1`).

It has a real cost: a first driver mapping a handful of small IBs into a flat
table pays 2 MiB of address space per mapping. The alternative — a
multi-level table — is exactly what depth 0 avoids, and depth 0 is what GFX8's
VMID 0 uses. `NOT_DETERMINED`: whether a non-flat table is even expressible
for VMID 0 on this ASIC.

## C.1 Contract

```
GPUVA ──(>>21 from window base)──▶ PDB0 entry index
                                     │
        entry = (system_PA & 0x000000FFFFFFF000) | flags
```

| property | value | enforced by |
|---|---|---|
| units | index in 2 MiB units; PA in bytes; entry in 64-bit words | `rx550_vm.c` |
| alignment | index boundary 2 MiB; PA boundary 4 KiB | `RX550_PDE_PTE_FLAG`, `pte_addr_mask` |
| bounds | PA must fit 40 bits; index must fit 32 bits | `rx550_pdb0_index` |
| permissions | VALID/READABLE/WRITEABLE bits, caller-supplied flags | `rx550_pdb0_entry` |
| lifetime | the page table is driver-global static state, not per-buffer | `amdgpu_gmc.c:1126` "PDB0 is static, initialized once" |
| ownership | the driver owns PDB0; buffers do not | same |
| invalidation | **`NOT_DETERMINED`** — no ISA document, no evidence of what a
  TLB flush requires for a GFX8 flat table | — |
| VMID relation | this IS the VMID 0 table; no per-process VM involved | `gfxhub_v1_0.c:218-230` |
| IB relation | the IB's GART VA selects the entry; the descriptor carries the VA | `ADDRESS-SPACE.md` |

## C.2 Invalidation — DEFERRED

`VM_CONTEXT0_CNTL.RETRY_PERMISSION_OR_INVALID_PAGE_FAULT` is set to 0 by
`gfxhub_v1_0.c:220`. What happens on a miss, and what a TLB flush costs, is
`NOT_DETERMINED` from this corpus. Marked `DEFERRED_RUNTIME`: it is only
reachable once a real IB address is mapped.

---

# D — rx550-mem ↔ rx550-pm4 BOUNDARY

## D.1 What each side owns

| | rx550-mem | rx550-pm4 |
|---|---|---|
| knows | which space an address belongs to, whether it is window-legal, whether it is encodable, lifetime, ownership | opcode, count, field placement, byte layout |
| does not know | opcodes, packets, counts, register indices | allocators, windows, domains, owners, lifetimes |
| coupling | **numbers only** | **numbers only** |

`rx550-mem` does not include `pm4.h`; `rx550-pm4` does not include
`rx550_addr.h`. The only shared artefact is the 46-bit / 4-byte contract,
asserted from both sides in `rx550_contract_test.c`.

## D.2 The properties, and how each is tested

| # | property | test |
|---|---|---|
| D1 | both declare 46 bits and 4-byte alignment | `t_shared_constants` |
| D2 | a published buffer's address encodes with the split `gfx_v8_0.c:6096-6097` performs, and the split is **lossless** — reassembling DW1:DW2 returns the address | `t_end_to_end` |
| D3 | the two layers' accept/reject verdicts are **identical** for every candidate address, including one 4-aligned and out of field, one misaligned, and the maximum | `t_layers_agree` |
| D4 | a descriptor is never buildable from a non-published buffer; a released buffer is no longer encodable, and **keeps** its address so stale use is visible | `t_boundary_rule` |
| D5 | units are not silently rounded: a 20-byte buffer yields exactly the 5 DW the corpus uses (`gfx_v8_0.c:896`); a 22-byte buffer yields 5 usable and loses the remainder | `t_units` |

## D.3 No bare address crosses the boundary

Every address in `rx550_addr.h` is paired with a `rx550_addr_space`. The
`RX550_AS_PCI_BAR` and `RX550_AS_GPU_VRAM_PA` cases are tested to be rejected
where the GART space is required. A VRAM physical address is explicitly
**not** descriptor-encodable (`t_publish`, `A2: encodable`).

## D.4 Pool policy vs packet requirement, kept separate

| | value | kind |
|---|---|---|
| packet field granularity | 4 bytes | **HW REQUIREMENT** (`gfx_v8_0.c:6096`) |
| amdgpu IB pool alignment | 256 bytes | **AMDGPU POLICY** (`amdgpu_ib.c:361`) |

`rx550_addr.h` carries both as distinct constants with the classification in
the comment. The model *permits* 4; it does not require 256. Mutation-tested
independently.

## D.5 Deliberate divergences

| behaviour | reference | here | reason |
|---|---|---|---|
| IB address low bits | masked away | rejected | a truncated address is not the requested one |
| IB address > 46 bits | truncated by `& 0xFFFF` | rejected | same |
| partial append on overflow | n/a | none, all-or-nothing | a half-written packet is not a packet |
| re-alloc of a live buffer | n/a | `ESTATE` | silently discarding an owner is a use-after-free |
| released buffer's `gpu_va` | n/a | preserved | a stale use must be visible, not read as 0 |

---

# Verification record

4 binaries, **213 assertions, 0 failures, 0 warnings**
(`-Werror -Wconversion -Wsign-conversion -Wpedantic -Wcast-qual`).

Mutation testing: **19 mutations detected**, 4 inconclusive (build failure —
unused parameter or type error, so the property was never exercised), 3
equivalent-by-construction, 3 sed patterns that did not apply.

The three equivalent mutations, stated so they are not mistaken for coverage:

1. removing `publish`'s 46-bit check — `encodable()` enforces the same limit,
   so the *cross-layer* verdict is unchanged. `rx550_addr_test` **does**
   detect it (verified: 1 assertion fails).
2. removing `encodable`'s alignment check — `publish()` already guarantees
   alignment, so the check can never fail. Redundant defence.
3. removing the `gpu_va < gart_base` check in `rx550_pdb0_index` — correct by
   unsigned wraparound (`gpu_va - gart_base` → ~2^64, still > 0xffffffff
   after `>>21`). **Correct but fragile**: it relies on the wrap rather than
   stating the precondition. Recorded, not changed.

## Defects found and fixed in this batch

| defect | how it surfaced |
|---|---|
| `rx550_addr.h` was not a prerequisite of the contract target, so mutating a header did not rebuild — **a test that could not fail** | mutation reported "not detected" for a change that must be detected |
| `$(BINS:=.d)` is a Make **assignment**, not a substitution; it reassigned `BINS` to `.d` and broke the default goal | link failure with "undefined reference" on symbols that exist |
| the first mutation runner used one `.bak` for a `.c` and a `.h`, overwriting `rx550_addr.c` with header text | link failure; the toolchain caught it, the runner had not |

The Makefile now generates dependencies with `-MMD -MP` and includes them, so
a header edit cannot leave a stale binary behind.
