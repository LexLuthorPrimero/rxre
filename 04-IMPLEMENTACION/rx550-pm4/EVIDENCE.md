# EVIDENCE — rx550-pm4 GFX8 command layer

Corpus: project kernel tree `RESEARCH/kernelbuild/linux-7.1.3` (copy of
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64`). Every value below was read
from that tree, and the opcodes were additionally confirmed with the
preprocessor on the exact include chain that `gfx_v8_0.c` compiles against.

Paths are relative to `drivers/gpu/drm/amd/`.

## 0. Target identity (why GFX8 packet set)

| field | value | source |
|---|---|---|
| PCI BDF | `0000:01:00.0` | `/sys/bus/pci/devices/0000:01:00.0` |
| device id | `0x699f` | `…/device` |
| class | `0x030000` | `…/class` |
| driver | `amdgpu` | `…/driver` symlink |
| modalias | `pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00` | `…/modalias` |
| module alias | `alias pci:v00001002d0000699Fsv*sd*bc*sc*i* amdgpu` | `/lib/modules/$(uname -r)/modules.alias` |

`GENERATION_SCOPE`: GFX8 (Polaris 8/10/12). RX 550 = Polaris 12 = GFX8.
`GENERATION_SCOPE` of every constant below is this generation only.

## 1. Packet3 header — FACT

`vid.h:105-107`
```c
#define PACKET3(op, n)  ((PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) | ((n) & 0x3FFF) << 16)
```
Decoders, `vid.h:92-95`: `CP_PACKET_GET_TYPE(h) = (h>>30)&3`,
`CP_PACKET_GET_COUNT(h) = (h>>16)&0x3FFF`, `CP_PACKET3_GET_OPCODE(h) = (h>>8)&0xFF`.

| field | bits | value |
|---|---|---|
| header type | 31:30 | `3` |
| opcode | 15:8 | — |
| count | 29:16 | `payload_dw - 1` (see §5) |

`GENERATION_SCOPE`: GFX8, 32-bit header. GFX9+ uses a 64-bit header and is
**out of scope**; none of this transfers.

## 2. Opcodes — FACT, with one hazard

| name | value | source |
|---|---|---|
| `PACKET3_INDIRECT_BUFFER` | `0x3F` | `vid.h:190` |
| `PACKET3_INDIRECT_BUFFER_CONST` | `0x33` | `vid.h:137` |
| `PACKET3_DISPATCH_DIRECT` | `0x15` | `vid.h:118` |
| `PACKET3_SET_SH_REG` | `0x76` | `vid.h:347` |
| `PACKET3_EVENT_WRITE` | `0x46` | `vid.h:226` |
| `PACKET3_WRITE_DATA` | `0x37` | `vid.h:141` |
| `PACKET3_SET_SH_REG_START` | `0x00002c00` | `vid.h:348` |
| `INDIRECT_BUFFER_VALID` | `1 << 23` | `vid.h:192` |
| `INDIRECT_BUFFER_PRE_ENB(x)` | `(x) << 21` | `vid.h:198` |
| `EVENT_TYPE(x)` | `(x) << 0` | `vid.h:227` |
| `EVENT_INDEX(x)` | `(x) << 8` | `vid.h:228` |

Confirmed by preprocessor on the real include order of `gfx_v8_0.c`:
`gcc -E -dM` over `#include "vi.h" / "vi_structs.h" / "vid.h"` emits exactly
these values, and the tree is three headers — `sid.h` is **not** loaded.

### HAZARD — recorded, not resolved by copying

`amdgpu/sid.h:372` defines `PACKET3_INDIRECT_BUFFER_CONST` as **`0x31`**, not
`0x33`. `vid.h:137` defines `0x33`. These are different families, not an
include-order conflict: `sid.h` is not in the GFX8 translation unit at all
(verified with `gcc -E -H`; only `vi.h`, `vi_structs.h`, `vid.h` load).
`sid.h`'s value governs TUs that do include it (`si.c`, `gfx_v6_0.c`,
`si_dma.c`, `si_ih.c`, `uvd_v3_1.c`, `vce_v1_0.c`, `dce_v6_0.c`).

Copying any constant from `sid.h` instead of `vid.h` yields a wrong opcode.
The values here come from `vid.h` only. A mutation test substitutes `0x31`
and asserts the suite fails.

## 3. Payload layouts — FACT

`gfx_v8_0.c:6091-6098` (INDIRECT_BUFFER) and `:1529-1550` (IB content):

| packet | DW0 | DW1 | DW2 | DW3 |
|---|---|---|---|---|
| `SET_SH_REG` count 1 | header | `reg - 0x2c00` | value | — |
| `SET_SH_REG` count 2 | header | `reg - 0x2c00` | lo | hi |
| `DISPATCH_DIRECT` count 3 | header | x | y | z, initiator |
| `EVENT_WRITE` count 0 | header | `EVENT_TYPE(t)\|EVENT_INDEX(i)` | — | — |
| `INDIRECT_BUFFER` count 2 | header | `gpu_addr & 0xFFFFFFFC` | `(gpu_addr>>32) & 0xFFFF` | control |
| `WRITE_DATA` count 3 | header | `dst_sel\|confirm` | addr lo | addr hi, data |

`control = flags | length_dw | (vmid << 24)` — `gfx_v8_0.c:6082`, `:6107`.

## 4. Register and field values — FACT

| name | value | source |
|---|---|---|
| `mmCOMPUTE_PGM_LO` | `0x2e0c` (**register index**, not a byte offset) | `include/asic_reg/gca/gfx_8_0_d.h:1293` |
| `mmCOMPUTE_PGM_HI` | `0x2e0d` | `gfx_8_0_d.h:1294` |
| `COMPUTE_DISPATCH_INITIATOR.COMPUTE_SHADER_EN` | mask `0x1`, shift `0` | `gfx_8_0_sh_mask.h:8235-8236` |

`gfx_8_0_d.h` holds register **indices**. A byte offset would be index × 4.
This component consumes indices; it never converts them.

## 5. Count field — FACT (corpus-derived), hardware meaning NOT_DETERMINED

Across every packet instance in `gfx_v8_0.c`, count = payload DW − 1:

| instance | line | count | payload |
|---|---|---|---|
| `SET_SH_REG` 1 DW | 1529 | 1 | 2 |
| `SET_SH_REG` 2 DW | 1535 | 2 | 3 |
| `DISPATCH_DIRECT` | 1541 | 3 | 4 |
| `EVENT_WRITE` | 1549 | 0 | 1 |
| `INDIRECT_BUFFER` | 6125 | 2 | 3 |
| `WRITE_DATA` | 891 | 3 | 4 |

Six independent instances, all consistent. The **hardware** interpretation of
the field is `NOT_DETERMINED`: no GCN3 ISA document was available to this
component. A mutation replacing `payload_dw - 1` with `payload_dw` is caught
by 9 assertions.

## 6. What is NOT established

- `SUBMISSION` — `NOT_DETERMINED`. No ring, no wptr, no doorbell is touched.
- `FETCH` — `NOT_DETERMINED`. Nothing observes the GPU reading the buffer.
- `EXECUTION` — `NOT_DETERMINED`. Encoded is not executed.
- `ADDRESS_SEMANTICS` — **partial**. The *field encoding* is established
  (§3: 46 address bits, 4-byte granularity, `& 0xFFFFFFFC` / `& 0xFFFF`). The
  *meaning* of the address — which VA space, whose allocation — is
  `NOT_DETERMINED` here and belongs to the device object / memory component.
  This component never discovers or allocates an address; it encodes one the
  caller supplies.
- `DISPATCH_DIRECT` field semantics (what the GPU does with x/y/z) —
  `NOT_DETERMINED`. Only the wire order is implemented, from §3.
- `SET_SH_REG` register semantics — `NOT_DETERMINED`. Only the address
  arithmetic `reg - 0x2c00` is implemented.

## 7. `NOT_IMPLEMENTED` and why

- `PACKET3_WRITE_DATA` — opcode `0x37` established (`vid.h:141`), but its
  `WRITE_DATA_DST_SEL` / `WR_CONFIRM` masks live only in `sid.h:378,387`,
  which is not in the GFX8 TU. The masks cannot be sourced for this
  generation from the corpus. **Deferred**, not guessed.
- `PACKET3_INDIRECT_BUFFER_CONST` — implemented as a variant of the same
  encoder; the only difference in the corpus is the opcode
  (`gfx_v8_0.c:6078` vs `:6080`).
- `PACKET3_SET_SH_REG_OFFSET` (`0x77`) — `NOT_EVALUATED`; not required and no
  GFX8 payload instance was examined.

## 8. Divergences from the reference, and why

| behaviour | reference | here | reason |
|---|---|---|---|
| IB address low 2 bits | masked away (`& 0xFFFFFFFC`) | rejected, `ERANGE` | silently dropping bits means the encoded address is not the one requested |
| IB address > 46 bits | truncated by `& 0xFFFF` | rejected, `ERANGE` | same |
| `vmid` | no check | rejected above `0xFF` | vmid occupies 8 bits at `<<24` |
| partial write on overflow | n/a | none, append is all-or-nothing | a half-written packet is not a packet |
| buffer allocation | `amdgpu_sa_bo_new` | caller-owned `uint32_t[]` | no allocator, no GPU memory in this component |

## 9. Test discrimination record

Baseline: 104 assertions, 0 failures, 0 compiler warnings under
`-Wall -Wextra -Wpedantic -Werror -Wshadow -Wconversion -Wsign-conversion
-Wcast-qual -Wstrict-prototypes`.

Mutations applied to the implementation and re-run; each must break the suite:

| mutation | result |
|---|---|
| opcode `0x3F` → `0x31` (the `sid.h` trap) | detected, 3 asserts |
| count = payload (drop `-1`) | detected, 9 |
| append without capacity guard | detected, 4 |
| reset clears only 1 DW | detected, 3 |
| reset clears only `cap-1` | detected, 1 |
| `n_dw == 0` guard removed | detected, 1 |
| `buf_dw` range check removed | detected, 2 |
| unaligned address accepted | detected, 1 |
| address > 46 bits accepted | detected, 2 |
| `reg < SET_SH_REG_START` accepted | detected, 1 |
| `SET_SH_REG_START` 0x2c00 → 0x2c01 | detected, 3 |
| `vmid << 24` removed from control | detected, 2 |
| `EVENT_INDEX` removed | detected, 1 |
| `EVENT_WRITE` 0x46 → 0x47 | detected, 2 |
| `SET_SH_REG` 0x76 → 0x77 | detected, 3 |
| header type 3 → 2 | detected, 8 |
| dispatch x↔y / y↔z / z↔initiator / x↔initiator / x↔z | all 5 detected |
| `set_reg64` lo/hi swapped | detected, 1 |
| `ioremap` injected into `pm4.c` (`make check-nohw`) | detected, rc≠0 |

Two mutations are **equivalent, not missed**: removing the
`& 0xFFFFFFFC` / `& 0xFFFF` masks. Under the alignment and 46-bit validation
those masks are unreachable dead code, so removing them cannot change any
output. The validation is the observable property and it is tested.
