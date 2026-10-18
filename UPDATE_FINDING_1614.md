# Update to Finding 1614 — PTE/PDE Base Address Analysis

## Summary

Based on source code analysis of Linux kernel 7.1.3 (drivers/gpu/drm/amd/) and Mesa source:

**The PTE/PDE base registers exist as MMIO hardware registers at offsets 0x54f-0x55e (GMC v7.x header `gmc_7_1_d.h`).** They are programmed via `WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, ...)` during `gmc_v8_0_gart_enable()`.

**The observability gap is a UMR tool limitation**, not a hardware limitation: UMR's register database (`gfx_8_0_0.reg` + `oss_2_0_0.reg`) does not include GMC v7.x register definitions.

## Evidence

| Source | File | Line/Function | Key Code |
|--------|------|---------------|----------|
| Register defs | `gmc_7_1_d.h` | 613-619 | `#define mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0x54f` |
| MMIO write | `gmc_v8_0.c` | `gmc_v8_0_gart_enable()` | `WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, table_addr >> 12)` |
| VM config | `gmc_v8_0.c` | `gmc_v8_0_sw_init()` | `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)` |
| VMID reset | `gmc_v8_0.c` | `gmc_v8_0_hw_init()` | `amdgpu_vmid_reset_all(adev)` |

## Impact on RXRE Findings

- Finding 1614 gap remains valid (cannot read via current UMR)
- Root cause corrected: tool regdb incomplete, not hardware limitation
- No contradictions with findings 1610-1615 or 1616-1625

## Recommended Next Step

Update UMR regdb with GMC v7.x register definitions to enable read-only PTE/PDE base observation.

---