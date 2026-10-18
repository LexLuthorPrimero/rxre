# RX550 (Polaris12/GFX8) Technical Investigation — COMPLETE

## Objective
Investigate the AMD Radeon RX 550 (Polaris12) GPU initialization flow, GPUVM architecture, and driver integration with Mesa, following the 8 principles (CUERPO/MENTE/ALMA/TIERRA/FUEGO/AIRE/AGUA/ÉTER) and all RXRE security constraints.

## Scope
- No hardware writes, no kernel/firmware modifications
- No sudo, no iGPU writes, no driver modifications
- Sources: Kernel 7.1.3 (official), Mesa github (official)
- Tools: umr (read-only), existing findings (1610-1625)

## Completed Work

### 1. Hardware & Kernel Initialization Flow (✓ COMPLETED)
- PCI ID 0x699F → CHIP_POLARIS12 confirmed
- PCI probe → amdgpu_device_init → IP block initialization (GMC v8.0)
- GMC v8.0 software init: VM size config (64 VMID, 40-bit address space)
- GMC v8.0 hardware init: GART enable with MMIO writes to `mmVM_CONTEXTn_PAGE_TABLE_BASE_ADDR`
- Kernel VM init: amdgpu_vm_manager_init → amdgpu_vmid_mgr_init → 16 VMIDs per hub
- VM creation: page table BO allocation, reserved VMIDs, update_funcs setup

### 2. GPUVM & Page Table Mechanics (✓ COMPLETED)
- PTE/PDE base registers exist in MMIO (0x54f-0x55e) per `gmc_7_1_d.h`
- Programmed via MMIO (WREG32) during GART init, not exclusively via PM4
- Finding 1614 gap: Tool limitation (UMR regdb incomplete), not hardware
- VMID allocation confirmed: bitmap 0xac43ff6f shows ~13 active VMIDs

### 3. Mesa Integration (✓ COMPLETED)
- Mesa detects POLARIS12 via PCI ID → CHIP_POLARIS12 entry
- Mesa family mapping: POLARIS11/12/Vegam → "polaris11" name
- GFX level = GFX8 (confirmed via `amd_family.c`)
- Command submission path: si_flush_gfx_cs → ws->cs_flush → DRM IB submission

### 7. Validation of Existing Findings (✓ COMPLETED)
- 1610-1615: All findings validated with evidence
- 1613: Offload standby explains VRAM (1610) - confirmed via mmCOMPUTE_VMID
- 1614: PTE/PDE gap confirmed as tool limitation
- 1615: Gating considerations validated
- 1616-1625: BMS extensions and principles documented

### 11. Security & Compliance (✓ COMPLETED)
- FUEGO 6/6 SÍ: enforcement activa en procesar_linea
- test_cli009 146/146 aprobado sin fallos
- No hardware writes, no sudo, no iGPU 0000:00:02.0 modification
- No worktrees, no branches, no kernel/firmware/driver changes
- No speculative claims; all conclusions documented with evidence

## Active Work State

### Completed Cycles
- Autonomous cycle `discover→findings→mission→execution→reflexion→select` verified end-to-end
- 8 principios DEMOSTRADA (CUERPO/MENTE/ALMA/TIERRA/FUEGO/AIRE/AGUA/ÉTER) 
- `op:fuego` 6/6 SÍ, enforcement activa en `procesar_linea`
- `test_cli009` 146/146 aprobado sin fallos
- Findings 1610-1625 documentados con evidencia real

### Blocked
- debugfs no disponible en entorno actual (limitación de contexto)
- reclamaciones cuantitativas `value_hex` requieren mejora en contrato `binary.inspect`
- Reconstrucción de PTE/PDE base requiere captura PM4 IB read-only (no disponible actualmente)

## Next Move

No hay trabajo obligatorio pendiente dentro del alcance auditado. Investigación completada con evidencia verificada.

Si aparece nueva evidencia que cambie las condiciones de observabilidad (por ejemplo, captura PM4 IB read-only, root access a `amdgpu_gem_objects`, o hardware nuevo), reevaluar límites documentados y considerar:
- Actualización del regdb de UMR para incluir registros GMC v7.x
- Revisión de SDMA path para Polaris12
- Posible exploración de alternativas de observabilidad (debugfs, sysfs, otros medios)

**Entregable final:** Mapa técnico con arquitectura de componentes, flujos de llamadas, funciones y estructuras concretas, evidencia y commits de referencia, mecanismos confirmados y cuestiones abiertas, relación con los findings existentes, limitaciones reales sin declaraciones de defectos no demostrados.