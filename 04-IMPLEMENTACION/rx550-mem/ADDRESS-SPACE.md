# ADDRESS-SPACE — the IB address on RX 550 / Polaris12 / GFX8

Answers PRIORITY 1. Sources are the project's own kernel corpus
(`RESEARCH/kernelbuild/linux-7.1.3`, copy of
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64`). Paths are relative to
`drivers/gpu/drm/amd/`.

Classification per project rules. Nothing below is inferred from a name, a
convention, or "amdgpu does it this way".

---

## 1. What the address in `PACKET3_INDIRECT_BUFFER` is

**PROVEN — it is a GART virtual address, and the IB lives in system memory.**

| step | evidence |
|---|---|
| The IB pool is allocated in the **GTT domain** | `amdgpu_ib.c:360-362` — `amdgpu_sa_bo_manager_init(adev, &adev->ib_pools[i], AMDGPU_IB_POOL_SIZE, 256, AMDGPU_GEM_DOMAIN_GTT)` for all three pools |
| The address handed to the packet is that allocation's GPU address | `amdgpu_ib.c:78-83` — `ib->ptr = amdgpu_sa_bo_cpu_addr(...)`, `ib->gpu_addr = amdgpu_sa_bo_gpu_addr(...)` |
| The packet carries `ib->gpu_addr` | `gfx_v8_0.c:6091-6098` |
| GTT-domain GPU addresses are allocated inside the GART window | `amdgpu_gtt_mgr.c:340` — `drm_mm_init(&mgr->mm, 0, adev->gmc.gart_size >> PAGE_SHIFT)` |

So: **not** a VRAM aperture address, **not** a CPU pointer, **not** a PCI BAR
offset. It is the GART address of a system-memory allocation.

**Note for the other session:** the IB pool alignment is `256`
(`amdgpu_ib.c:361`, third argument to the manager init), while the *packet
field* only requires 4-byte granularity. 256 is pool policy, not a hardware
constraint. `rx550_addr.h` records both and does not conflate them.

## 2. Who produces it

The allocator. In the reference the chain is
`amdgpu_sa_bo_new` → suballocator → `drm_mm` over the GART window. The first
driver needs only: *a GART address inside the window, 4-byte aligned, backed
by memory the CPU can write*.

**STATICALLY_SUPPORTED**: a first driver can reserve its own GART range and
hand out addresses directly, without a suballocator, provided the range comes
from the declared window and the backing is system memory.

## 3. Who establishes the translation

The GPU's page table, loaded into `VM_CONTEXT0` for VMID 0.

**PROVEN — GFX8 uses a FLAT (depth 0) VMID-0 page table.**

| fact | evidence |
|---|---|
| `gfxhub_v1_0_enable_system_domain` programs `ENABLE_CONTEXT=1`, `PAGE_TABLE_DEPTH=adev->gmc.vmid0_page_table_depth`, `PAGE_TABLE_BLOCK_SIZE=adev->gmc.vmid0_page_table_block_size` | `gfxhub_v1_0.c:218-230` |
| For GFX8 those two fields are **never assigned** | `grep -c vmid0 gmc_v8_0.c` = **0**; they are assigned only in `gmc_v9_0.c:1779`, `gmc_v12_0.c:786`, `gmc_v12_1.c`. Struct is zero-initialised (`amdgpu_gmc.h:324-325`) |
| therefore depth = 0, block size = 0 | derived from the two rows above |
| each PDE0 (used as PTE) covers `2^block_size * 2 MiB` = **2 MiB** | `amdgpu_gmc.c:1136-1139` — `pde0_page_size = (1ULL<<block_size)<<21` |
| PDB0 layout: first *n* entries are PTEs mapping VRAM; entry *n+1* points to a large block covering system memory | `amdgpu_gmc.c:1125-1141` |

`gfxhub_v1_0.c` is the gfxhub for GFX8 (gfx9+ use `gfxhub_v1_2`, v3_x, v4_x).

## 4. What unit consumes the address

**NOT_DETERMINED** from static evidence. The descriptor is fetched by the
command processor / the IB-fetch engine. This corpus does not establish
whether the fetch is performed by the CP, by the GART, or by a front end, and
no ISA document was available. This component makes no claim.

## 5. Alignment per level

| level | requirement | source |
|---|---|---|
| packet field | 4 bytes; low 2 bits are masked off | `gfx_v8_0.c:6096` — `ib->gpu_addr & 0xFFFFFFFC` |
| reference pool | 256 bytes | `amdgpu_ib.c:361` |
| VMID 0 page granularity | 2 MiB | `amdgpu_gmc.c:1136-1139` |
| page size | `PAGE_SIZE`; GTT mm in `PAGE_SHIFT` units | `amdgpu_gtt_mgr.c:214, 340` |

`RX550_IB_ALIGN_MIN = 4` is the only one the *packet* imposes.

## 6–9. Significant and reserved bits, where the space is configured

| field | width | source |
|---|---|---|
| low DWORD | address bits 31:2 (`& 0xFFFFFFFC`) | `gfx_v8_0.c:6096` |
| high DWORD | address bits 47:32 (`upper_32_bits(gpu_addr) & 0xFFFF`) | `gfx_v8_0.c:6097` |
| ⇒ significant address bits | **46** | derived; mutation-tested |

Window placement: `gart_end = gart_start + gart_size - 1`
(`amdgpu_gmc.c:264`), and `gart_start = max_mc_address - gart_size + 1`
(`amdgpu_gmc.c:314`) — the GART sits at the **top** of the MC address range.

GART size: **256 MiB** without 4 GB pages, **1024 MiB** with
(`gmc_v8_0.c:595, 601`), plus `pm.smu_prv_buffer_size` (`gmc_v8_0.c:608`),
then clamped to what the MC can map (`amdgpu_gmc.c:307-333`).

**The driver must be given the window. It is not guessable from this corpus,
because it depends on the board's aperture carve-out.** The component
therefore takes `base` and `size` as inputs and validates them.

## 10–13. VMID

| question | answer | evidence |
|---|---|---|
| Does a VMID exist on GFX8? | Yes, via the VM context registers | `gfxhub_v1_0.c:218-230` |
| Which VMID does a context-less submission use? | **0** | `amdgpu_job.h:42` — `AMDGPU_JOB_GET_VMID(job) = ((job) ? (job)->vmid : 0)`; the test path passes `job = NULL` (`gfx_v8_0.c:898`) |
| Can a first driver use a fixed VMID 0? | Yes, for a single-context first path | `gfxhub_v1_0.c:218-230` programs `VM_CONTEXT0` with depth 0 |
| Must it multiplex VMIDs? | No, for the first path | no evidence that one context is insufficient; no evidence either way about multi-process |
| Is DRM GPUVM required? | **NOT_DETERMINED** | nothing in the path above requires a per-process VM |

**MODEL_MÍNIMO, not a general claim**: one address space, VMID 0, flat page
table, 2 MiB granularity for the VRAM-identity region, one large block for
system memory. This is the smallest configuration the corpus *demonstrates
being used*, not a statement about what the hardware requires in general.

## 14. What the first driver needs, in order

1. GART window `base`/`size`, read from the MC aperture state. **RUNTIME**
2. A page table in VRAM (PDB0), CPU-writable, `PAGE_SIZE` aligned.
   `amdgpu_gmc.c:1145-1150` shows the reference allocating it in
   `AMDGPU_GEM_DOMAIN_VRAM` with `AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED`
3. `VM_CONTEXT0` programmed: enable, depth 0, block size 0. **RUNTIME**
4. A GART range for the IB, 4-byte aligned, backed by system memory
5. A CPU mapping to write the IB
6. The PM4 descriptor, which this component already emits

Steps 1–3 and 5 are `RUNTIME_REQUIRED`. Steps 4 and 6 are pure and are built.

## Open questions left open on purpose

- **Which unit fetches the IB** — `NOT_DETERMINED`, no ISA document.
- **Cache/ordering requirements** for CPU→GPU visibility of the IB.
  `amdgpu_ib.c:80` sets `AMDGPU_IB_FLAG_EMIT_MEM_SYNC`, which is a strong hint
  that a sync is required, but the mechanism and whether it is mandatory for
  the first path is `NOT_DETERMINED`. This is the next secondary frontier.
- **Whether VRAM is needed at all** for the first path, given the IB is GTT
  and the page table itself lives in VRAM. **DERIVED**: some VRAM is needed
  because PDB0 is a VRAM allocation.
- **4 GB page support on this specific board** — determines 256 vs 1024 MiB.
  `RUNTIME_REQUIRED`; the value is not statically determinable.
