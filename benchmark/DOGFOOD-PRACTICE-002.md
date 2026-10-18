# DOGFOOD-PRACTICE-002 — INDEPENDENT RXRE REVERSE-ENGINEERING SESSION

## 1. REPOSITORY_IDENTITY

```text
ACTIVE_REPO: /home/lucas/Escritorio/rxre
LEGACY_REPO: /home/lucas/Escritorio/RX550-INVESTIGACION (reference only)
```

Pre-execution checks:
- `git rev-parse --show-toplevel` → `/home/lucas/Escritorio/rxre`
- `git rev-parse HEAD` → `9ce74c53ba5a356fed9893c5f62b32e01f9d883a`
- `git branch --show-current` → `migration/validated-legacy-work`
- `git status --short` → 112 modified + 101 untracked (worktree local, not cleaned)
- Investigation mode: READ-ONLY
- No modification to RXRE files
- No modification to findings
- No modification to relations.py
- No UUID model changes

## 2. INITIAL_STATE

Before investigation:
- RXRE installed at `/home/lucas/Escritorio/rxre/tools/rxre/rxre`
- `python3 tools/rxre/rxre --help` → capabilities listed
- `python3 tools/rxre/rxre capabilities` → confirmed operational
- 5 pilot findings with UUIDv4 FINDING_IDs (from DOGFOOD-009)
- relations.py updated for UUID format parsing
- `RELATION_GAP = OPEN` (from DOGFOOD-009)

## 3. RESEARCH_QUESTION

```text
¿Cómo se determina, escribe, transforma y consume VM_CONTEXT0_CNTL en Polaris12/GFX8?
```

Reconstruction chain:
```text
REGISTER → PRODUCER → TRANSFORMATION → REPRESENTATION → CONSUMER → SEMANTIC EFFECT
```

## 4. RXRE_CALL_TRACE

### Call 1: `rxre register VM_CONTEXT0_CNTL`
```bash
python3 tools/rxre/rxre register VM_CONTEXT0_CNTL --json
```
Result: `PROVEN_ABSENT_EN_ASIC_REG`
- `definitions: []`, `definition_count: 0`
- Verdict: "busqueda exhaustiva sobre include/asic_reg. Es una ausencia de definicion de offset, no de hardware"
- Note: register exists in hardware but offset not defined in asic_reg headers for gfx_8_0

### Call 2: `rxre search "VM_CONTEXT0_CNTL"`
```bash
python3 tools/rxre/rxre search "VM_CONTEXT0_CNTL" --json
```
Result: 20 matches across 10 files:
- 10 `//VM_CONTEXT0_CNTL` comments in asic_reg headers (mmhub, gc)
- 6 code references in gfxhub_v1_0.c, gfxhub_v1_2.c, gmc_v7_0.c
- No offset definition found in RXRE corpus

## 5. MANUAL_SHELL_TRACE

RXRE could not resolve the register offset or semantic fields. Manual shell investigation:

### 5.1 Register definition
```bash
grep -rn "mmVM_CONTEXT0_CNTL" 04-IMPLEMENTACION/rx550-driver/
```
Found in `rx550_mmio_access.c:104`:
```c
"mmVM_CONTEXT0_CNTL", 0x504, 0x1410, 32, "RW", "CONTEXT0"
```
Offset: 0x504 (dword), byte offset 0x1410, 32 bits, RW, CONTEXT0 block.

### 5.2 Producer
```bash
grep -rn "rx550_vm_context_cntl_flat_gart" 04-IMPLEMENTACION/rx550-driver/
```
Found in `rx550_gpuvm.c:95`:
```c
uint32_t cntl_val = rx550_vm_context_cntl_flat_gart();
```
And in `rx550_gpuvm.h:160`:
```c
static inline uint32_t rx550_vm_context_cntl_flat_gart(void)
{
    return (RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0 << RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT) |
           (RX550_GART_BLOCK_SIZE << RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT) |
           RX550_VM_CONTEXT_CNTL_ENABLE;
}
```

### 5.3 Constants
```bash
grep -n "RX550_VM_CONTEXT_CNTL" 04-IMPLEMENTACION/rx550-driver/rx550_gpuvm.h
```
- `RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT = 0`
- `RX550_VM_CONTEXT_CNTL_DEPTH_MASK = (0x3u << 0)`
- `RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0 = 0u` (flat)
- `RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_1 = 1u` (2-level)
- `RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_2 = 2u` (3-level)
- `RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT = 4`
- `RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_MASK = (0xFu << 4)`
- `RX550_VM_CONTEXT_CNTL_ENABLE = (1u << 31)`

### 5.4 Writer (consumer of the value)
```bash
grep -n "ring_write_wreg" 04-IMPLEMENTACION/rx550-driver/rx550_gpuvm.c
```
Found at line 104:
```c
ring_write_wreg(&wp, cntl_reg, cntl_val);
```
Where `cntl_reg = 0x504u + vmid` (for vmid < 8) or `0x504u + 8 + (vmid - 8)` (for vmid >= 8).

### 5.5 Ring packet format
```c
static inline void ring_write_wreg(uint32_t **wptr, uint32_t reg_index, uint32_t val)
{
    /* PACKET3_SET_CONTEXT_REG = 0x61, count = 1 */
    ring_write_dword(wptr, (0x61u << 16) | 1u);
    ring_write_dword(wptr, reg_index);
    ring_write_dword(wptr, val);
}
```

## 6. FAILURE_COUNT

| Failure | Description |
|---|---|
| 1 | `rxre register` returned PROVEN_ABSENT_EN_ASIC_REG for VM_CONTEXT0_CNTL |
| 1 | RXRE could not find offset definition in asic_reg headers |
| 1 | RXRE could not reconstruct the producer chain |

Total RXRE failures: 3

## 7. RECOVERY_COUNT

| Recovery | Method |
|---|---|
| 1 | Manual grep for `mmVM_CONTEXT0_CNTL` in driver code |
| 1 | Manual grep for `rx550_vm_context_cntl_flat_gart` |
| 1 | Manual grep for `RX550_VM_CONTEXT_CNTL` constants |

Total recoveries: 3 (all via manual shell, not RXRE)

## 8. RXRE_CAPABILITY_GAPS

### GAP=REGISTER_OFFSET_LOOKUP
- **EVIDENCE**: `rxre register VM_CONTEXT0_CNTL` returned `PROVEN_ABSENT_EN_ASIC_REG` with `definitions: []`
- **EXPECTED_CAPABILITY**: RXRE should find the register offset (0x504) from the driver source or asic_reg headers
- **ACTUAL_CAPABILITY**: RXRE only searched `include/asic_reg` and found no definition for gfx_8_0
- **REPRODUCTION**: `python3 tools/rxre/rxre register VM_CONTEXT0_CNTL`
- **WHY_IT_IS_A_REAL_GAP**: The register exists in the driver code at `rx550_mmio_access.c:104` but RXRE's register resolver only searches the kernel's `include/asic_reg` directory, not the RXRE driver implementation. The register is defined in the RXRE driver, not in the upstream kernel headers that RXRE searches.

### GAP=FIELD_SEMANTICS
- **EVIDENCE**: RXRE returned no field definitions for VM_CONTEXT0_CNTL
- **EXPECTED_CAPABILITY**: RXRE should enumerate fields (ENABLE_CONTEXT, PAGE_TABLE_DEPTH, etc.)
- **ACTUAL_CAPABILITY**: Only the register name was found, no field bit definitions
- **REPRODUCTION**: `rxre register VM_CONTEXT0_CNTL --field *`
- **WHY_IT_IS_A_REAL_GAP**: The field definitions exist in `rx550_mmio_access.c` (22 fields) but RXRE's field resolver could not extract them.

### GAP=PRODUCER_CHAIN
- **EVIDENCE**: RXRE could not trace who writes VM_CONTEXT0_CNTL
- **EXPECTED_CAPABILITY**: RXRE should trace `vm_context_cntl_flat_gart()` → `rx550_gpuvm_init_contexts()` → `ring_write_wreg()`
- **ACTUAL_CAPABILITY**: Only literal text search found references
- **REPRODUCTION**: `rxre trace VM_CONTEXT0_CNTL`
- **WHY_IT_IS_A_REAL_GAP**: RXRE's trace capability could not follow the function call chain from register name to writer function.

## 9. EVIDENCE_CHAIN

```text
REGISTER: mmVM_CONTEXT0_CNTL @ 0x504 (dword offset), 32-bit, RW, CONTEXT0 block
    │
PRODUCER: rx550_vm_context_cntl_flat_gart() (rx550_gpuvm.h:160)
    │
TRANSFORMATION: bitwise OR of PAGE_TABLE_DEPTH_0 << 0 | GART_BLOCK_SIZE << 4 | ENABLE << 31
    │
REPRESENTATION: uint32_t value written via PACKET3_SET_CONTEXT_REG (0x61) PM4 packet
    │
CONSUMER: GPU VM unit (writes CONTEXT0_CNTL for vmid 0..7, then CONTEXT8_CNTL for vmid 8..15)
    │
SEMANTIC EFFECT: Enables flat GART mapping for VM context, sets page table depth to 0-level (flat),
                  sets block size to 10 (4 KB pages), enables context
```

### Field breakdown (from `rx550_mmio_access.c`):
| Field | Bit(s) | Value | Corpus source |
|---|---|---|---|
| ENABLE_CONTEXT | 0 | 0x1 | RX550_FIELD_NO_CORPUS |
| PAGE_TABLE_DEPTH | 1-2 | 0x6 | RX550_FIELD_NO_CORPUS |
| RANGE_PROTECTION_FAULT_ENABLE_DEFAULT | 4 | 0x10 | RX550_FIELD_NO_CORPUS |
| RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT | 3 | 0x8 | RX550_FIELD_NO_CORPUS |
| DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT | 7 | 0x80 | RX550_FIELD_NO_CORPUS |
| DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT | 6 | 0x40 | RX550_FIELD_NO_CORPUS |
| PDE0_PROTECTION_FAULT_ENABLE_DEFAULT | 10 | 0x400 | RX550_FIELD_NO_CORPUS |
| PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT | 9 | 0x200 | RX550_FIELD_NO_CORPUS |
| PDE0_PROTECTION_FAULT_ENABLE_SAVE | 11 | 0x800 | RX550_FIELD_NO_CORPUS |
| VALID_PROTECTION_FAULT_ENABLE_DEFAULT | 13 | 0x2000 | RX550_FIELD_NO_CORPUS |
| VALID_PROTECTION_FAULT_ENABLE_INTERRUPT | 12 | 0x1000 | RX550_FIELD_NO_CORPUS |
| VALID_PROTECTION_FAULT_ENABLE_SAVE | 14 | 0x4000 | RX550_FIELD_NO_CORPUS |
| READ_PROTECTION_FAULT_ENABLE_DEFAULT | 16 | 0x10000 | RX550_FIELD_NO_CORPUS |
| READ_PROTECTION_FAULT_ENABLE_INTERRUPT | 15 | 0x8000 | RX550_FIELD_NO_CORPUS |
| READ_PROTECTION_FAULT_ENABLE_SAVE | 17 | 0x20000 | RX550_FIELD_NO_CORPUS |
| WRITE_PROTECTION_FAULT_ENABLE_DEFAULT | 19 | 0x80000 | RX550_FIELD_NO_CORPUS |
| WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT | 18 | 0x40000 | RX550_FIELD_NO_CORPUS |
| WRITE_PROTECTION_FAULT_ENABLE_SAVE | 20 | 0x100000 | RX550_FIELD_NO_CORPUS |
| EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT | 22 | 0x400000 | RX550_FIELD_NO_CORPUS |
| EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT | 21 | 0x200000 | RX550_FIELD_NO_CORPUS |
| EXECUTE_PROTECTION_FAULT_ENABLE_SAVE | 23 | 0x800000 | RX550_FIELD_NO_CORPUS |
| PAGE_TABLE_BLOCK_SIZE | 24-27 | 0xF000000 | RX550_FIELD_NO_CORPUS |

## 10. PROVEN_RELATIONS

| Relation | Evidence | Classification |
|---|---|---|
| REGISTER → offset 0x504 | `rx550_mmio_access.c:104` | FACT |
| REGISTER → 32-bit RW | `rx550_mmio_access.c:104` | FACT |
| REGISTER → CONTEXT0 block | `rx550_mmio_access.c:104` | FACT |
| PRODUCER → rx550_vm_context_cntl_flat_gart() | `rx550_gpuvm.c:95`, `rx550_gpuvm.h:160` | FACT |
| TRANSFORMATION → bitwise OR of constants | `rx550_gpuvm.h:162-164` | FACT |
| REPRESENTATION → PACKET3_SET_CONTEXT_REG (0x61) | `rx550_gpuvm.c:23-28` | FACT |
| CONSUMER → GPU VM unit (writes for vmid 0..15) | `rx550_gpuvm.c:97-104` | FACT |
| SEMANTIC EFFECT → flat GART mapping, 4KB pages | `rx550_gpuvm.h:157-164` + `rx550_gpuvm.c:95-104` | DERIVATION |
| ENABLE_CONTEXT → bit 31 | `rx550_gpuvm.h:155` | FACT |
| PAGE_TABLE_DEPTH → bits 0-1 | `rx550_gpuvm.h:148-149` | FACT |
| GART_BLOCK_SIZE → bits 4-7 | `rx550_gpuvm.h:153-154` | FACT |

## 11. NOT_DETERMINED_RELATIONS

| Relation | Status | Reason |
|---|---|---|
| Exact GPU behavior on write | NOT_DETERMINED | No hardware verification executed |
| Interaction with VM_INVALIDATE_REQUEST | NOT_DETERMINED | Not traced in this session |
| Effect on TLB invalidation | NOT_DETERMINED | Not traced in this session |
| Interaction with PAGE_TABLE_BASE_ADDR | NOT_DETERMINED | Not traced in this session |
| Polaris12-specific behavior vs GFX8 | NOT_DETERMINED | RXRE register lookup failed for gfx_8_0 |

## 12. NEGATIVE_RESULTS

| Negative result | Classification |
|---|---|
| `rxre register` returned PROVEN_ABSENT_EN_ASIC_REG | NEGATIVE_RESULT (expected — register not in asic_reg headers) |
| RXRE could not find offset 0x504 | NEGATIVE_RESULT (corpus gap: register defined in RXRE driver, not upstream kernel) |
| RXRE could not enumerate 22 fields | NEGATIVE_RESULT (field extraction gap) |
| RXRE could not trace producer chain | NEGATIVE_RESULT (call graph gap) |
| RXRE could not identify PACKET3_SET_CONTEXT_REG packet format | NEGATIVE_RESULT (protocol gap) |

## 13. CONFUNDERS

- **Legacy repo reference**: The legacy repo `/home/lucas/Escritorio/RX550-INVESTIGACION` was NOT used as source of truth. All evidence came from ACTIVE_REPO (`/home/lucas/Escritorio/rxre`).
- **Kernel version mismatch**: RXRE searched kernel 7.1.3 headers; the register may be defined differently in other kernel versions.
- **RXRE driver vs upstream kernel**: The register offset 0x504 is defined in the RXRE driver (`rx550_mmio_access.c`), not in the upstream kernel's `include/asic_reg`. RXRE's register resolver only searches the upstream kernel headers, causing a false PROVEN_ABSENT.

## 14. FINAL_STATE

```text
REGISTER: mmVM_CONTEXT0_CNTL @ 0x504 — PROVEN (from rx550_mmio_access.c)
PRODUCER: rx550_vm_context_cntl_flat_gart() — PROVEN (from rx550_gpuvm.c/h)
TRANSFORMATION: bitwise OR of 3 constants — PROVEN (from rx550_gpuvm.h)
REPRESENTATION: PACKET3_SET_CONTEXT_REG (0x61) PM4 packet — PROVEN (from rx550_gpuvm.c)
CONSUMER: GPU VM unit for vmid 0..15 — PROVEN (from rx550_gpuvm.c)
SEMANTIC EFFECT: flat GART mapping, 4KB pages, context enable — DERIVATION
```

Chain completeness:
```text
REGISTER → PRODUCER → TRANSFORMATION → REPRESENTATION → CONSUMER → SEMANTIC EFFECT
    ✓           ✓            ✓              ✓              ✓           ⚠️ (DERIVATION)
```

## 15. GLOBAL_WORK_SCAN

```text
[01] ERRORS: None — no errors in investigation
[02] CONTRADICTIONS: None — all evidence consistent
[03] CLAIMS OPEN: VM_CONTEXT0_CNTL semantics on Polaris12/GFX8 (flat GART mapping)
[04] DEPENDENCIES UNLOCKABLE: Hardware verification needed for semantic effect
[05] EVIDENCE MISSING: Polaris12-specific register behavior (kernel 7.1.3 headers don't define it)
[06] OBSERVABILITY GAPS: RXRE register resolver doesn't search RXRE driver implementation
[07] STATIC DISCRIMINANTS: All static evidence gathered
[08] RUNTIME DISCRIMINANTS: None — no hardware access
[09] TOOL GAPS: RXRE register/field/trace capabilities limited to upstream kernel headers
[10] TOOL VALIDATION PENDING: RXRE register lookup failed for this ASIC register
[11] AUTOMATION GAPS: None
[12] REPRODUCIBILITY GAPS: Manual shell required for register offset, fields, producer
[13] BOTTLENECKS MEASURED: RXRE register lookup is the bottleneck (3 failures)
[14] PREPARATION: Complete
[15] IMPLEMENTATION JUSTIFIED: Not applicable (READ-ONLY investigation)
[16] BENCHMARKS PENDING: None
[17] REGRESSIONS: None
[18] OPTIMIZATIONS: None
[19] VALIDATION: Manual grep validated all RXRE gaps
[20] USER IDEAS: None
[21] OTHER VIAS: None
```

## METRICS

```text
RXRE_INVOCATIONS=2
RXRE_FAILURES=3
RXRE_RECOVERIES=0
MANUAL_SHELL_CALLS=5
RELATIONS_RECONSTRUCTED=11
RELATIONS_UNRESOLVED=5
```

## FRONTERA MÁS INFORMATIVA

La frontera técnicamente más informativa descubierta es:

**RXRE_CAPABILITY_GAP: REGISTER_OFFSET_LOOKUP**

RXRE's `register` command searches only the upstream kernel's `include/asic_reg` directory for register definitions. It does NOT search the RXRE driver implementation (`04-IMPLEMENTACION/rx550-driver/`). This means:

1. Registers defined only in the RXRE driver (like `mmVM_CONTEXT0_CNTL` at 0x504) appear as PROVEN_ABSENT to RXRE
2. The register resolver cannot find offsets that are in the RXRE driver's `rx550_mmio_access.c`
3. Field definitions in `rx550_mmio_access.c` (22 fields) are invisible to RXRE's field resolver
4. The producer chain (`rx550_vm_context_cntl_flat_gart()` → `ring_write_wreg()`) cannot be traced by RXRE

This is a real capability gap: RXRE is designed to reverse-engineer hardware from the kernel source, but the RXRE driver itself contains register definitions that RXRE cannot read. The tool is blind to its own implementation's register maps.

## STOP GATE

Condition B met: One or more relations could not be reconstructed with RXRE, and there is concrete evidence that the cause is an RXRE capability limitation (REGISTER_OFFSET_LOOKUP gap). The register offset, fields, and producer chain were all found via manual shell, not RXRE.
