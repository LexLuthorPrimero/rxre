# RX550 (Polaris12/GFX8) — Technical Map (Kernel + Mesa)
**Fecha:** 2026-10-15  
**Alcance:** Análisis de código fuente, sin escrituras hardware, sin modificaciones  
**Principios:** CUERPO/MENTE/ALMA/TIERRA/FUEGO/AIRE/AGUA/ÉTER — verificados con evidencia  

---

## 1. Identificación de Hardware

| Campo | Valor | Fuente |
|-------|-------|--------|
| PCI Vendor ID | 0x1002 | `amdgpu_drv.c:2041` |
| PCI Device ID | 0x699F | `amdgpu_drv.c:2041` (Polaris12 block) |
| ASIC Type | CHIP_POLARIS12 | `amdgpu_drv.c`, `amd_family.h:98` |
| GFX Level | GFX8 | `amd_family.c` |
| Mesa family name | "polaris11" | `amd_family.c:134` (alias: POLARIS11+POLARIS12+VEGAM) |
| Mesa device name | "polaris12" | `amdgpu_devices.c:552` |

**Políx 0x699F** está mapeado explícitamente a `CHIP_POLARIS12` en la tabla de PCI IDs del kernel.

---

## 2. Flujo de Inicialización del Kernel (Linux 7.1.3)

### 2.1 PCI Probe → Device Setup
```
amdgpu_pci_probe(pdev, ent)
  └─ flags = ent->driver_data → CHIP_POLARIS12
  └─ amdgpu_driver_load_kms()
       └─ amdgpu_device_init(adev, flags)
            └─ adev->asic_type = CHIP_POLARIS12
```

### 2.2 IP Block Selection (GFX8/Polaris12)
El kernel selecciona bloques IP basados en versión de hardware (descoberta en tiempo de ejecución):

| IP Block | Versión | Función |
|----------|---------|---------|
| GMC | gmc_v8_0 | Graphics Memory Controller (GPUVM) |
| SDMA | sdma_v4_0 | DMA engine (page table updates via IB) |
| GFX/CP | gfx_v8_0 | Graphics command processor |

La selección de SDMA ocurre en `amdgpu_discovery.c:amdgpu_discovery_set_sdma_ip_blocks()` — `SDMA0_HWIP` → `IP_VERSION(4,0,x)` → `sdma_v4_0_ip_block`.

### 2.3 GMC v8.0 Software Init (`gmc_v8_0_sw_init`)
```
┌─ Sets vmhubs_mask (GFXHUB)
├─ Reads mmMC_SEQ_MISC0 MMIO (VRAM type detection)
├─ amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
│    └─ 64 VMIDs, 9-bit fragment, 1-level PT depth, 40-bit address space
├─ mc_mask = 0xffffffffffULL (40-bit)
├─ pte_addr_mask = 0x000000FFFFFFF000ULL
└─ Adds VM fault IRQs (GFX_PAGE_INV_FAULT, GFX_MEM_PROT_FAULT)
```

### 2.4 GMC v8.0 Hardware Init (`gmc_v8_0_hw_init`)
```
┌─ gmc_v8_0_polaris_mc_load_microcode(adev)   → MC firmware load
├─ gmc_v8_0_gart_enable(adev):
│   ├─ Configura L1/L2 TLB caches (mc_vm_mx_l1_tlb_cntl, vm_l2_cntl)
│   ├─ mmVM_CONTEXT0_PAGE_TABLE_START_ADDR = gart_start >> 12
│   ├─ mmVM_CONTEXT0_PAGE_TABLE_END_ADDR   = gart_end >> 12
│   ├─ mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR  = table_addr >> 12  ← PTE/PDE base
│   ├─ mmVM_CONTEXT0_CNTL                  = enable context (PAGE_TABLE_DEPTH=0)
│   ├─ Configura contexts 1-15 (idéntico base, protección completa)
│   └─ gmc_v8_0_flush_gpu_tlb(adev, 0, 0, 0)
└─ amdgpu_vmid_reset_all(adev) → limpia todos los VMIDs
```

**Hallazgo clave:** `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` se escribe vía **WREG32 (MMIO)** durante la inicialización del GART, no vía PM4. Es un registro de hardware real.

---

## 3. VM Manager y VMID

### 3.1 Inicialización de VM Manager (`amdgpu_vm_manager_init`)
```
┌─ concurrent_flush = !(asic < VEGA10 || NAVI10 || NAVI14) → GFX8: falso
├─ amdgpu_vmid_mgr_init(adev)
│    ├─ Crea 16 VM hub managers
│    ├─ Para GFX8: gestiona VMIDs 1..15 (VMID 0 = system)
│    └─ amdgpu_vmid_reset(adev, hub, id) para cada VMID > 0
└─ xa_init(&pasids)
```

### 3.2 Creación de VM por Proceso (`amdgpu_vm_init`)
```
┌─ Asigna page table BO (VRAM o GTT)
├─ Establece update_funcs:
│    ├─ CPU path: amdgpu_vm_cpu_funcs (kmap)
│    └─ SDMA path: amdgpu_vm_sdma_funcs (IB submission)
└─ VM update mode basado en vm_update_mode (CPU para compute, SDMA para GFX por defecto)
```

### 3.3 Observabilidad VMID (Hallazgo 1614, verificado)
| Registro | Valor observado | Significado |
|----------|-----------------|-------------|
| `mmCOMPUTE_VMID` | 0xac43ff6f | Bitmap VMIDs asignados (~13 bits) |
| `mmCP_VMID` | 0x5 | CP en VMID 5 |
| `mmCP_VMID_STATUS` | 0x0 | Sin preempt |
| `mmGDS_GWS_VMID0` | BASE=0, SIZE=64 | GDS grant VMID 0 |

---

## 4. Page Table Base Addresses (PTE/PDE)

### 4.1 Registros Definidos (`gmc_7_1_d.h` — GMC v7.x para GFX8)
```
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR  0x54f
mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR  0x550
mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR  0x551
...
mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR  0x50e
...
mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR 0x515
```

### 4.2 Programación en Kernel
Durante `gmc_v8_0_gart_enable()`:
```c
WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, table_addr >> 12);
```
También usado vía `PACKET3_SET_CONTEXT_REG` (PM4 packet 0x69) para switching de VMID durante ejecución de comandos.

### 4.3 Gap de Observabilidad (Hallazgo 1614 — CONFIRMADO)
- **Estado:** Los registros EXISTEN en hardware (MMIO 0x54f-0x55e)
- **Gap:** No están en el regdb de UMR (`gfx_8_0_0.reg` + `oss_2_0_0.reg`)
- **Causa:** Limitación de la herramienta UMR, no del hardware
- **Evidencia:** `WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR, ...)` en `gmc_v8_0.c`

---

## 5. Detección de Mesa (RadeonSI + RADV)

### 5.1 Detección de Dispositivo
```c
// amdgpu_devices.c — entrada explícita para POLARIS12
.name = "polaris12",
.radeon_family = CHIP_POLARIS12,
.hw_ip_gfx = { .major=8, .minor=0, ... },
.hw_ip_compute = { .major=8, .minor=0, ... },
.fw_gfx_me   = { .ver=167, .feature=49 },
.fw_gfx_pfp  = { .ver=254, .feature=49 },
.fw_gfx_mec  = { .ver=730, .feature=49 },
```

### 5.2 Mapping de Familia
```c
// amd_family.c — POLARIS11 y POLARIS12 comparten nombre "polaris11"
case CHIP_POLARIS11:
case CHIP_POLARIS12:
case CHIP_VEGAM:
   return "polaris11";
```
Esto significa: Mesa trata a RX 550 (Polaris12) bajo el mismo nombre de familia que RX 560 (Polaris11).

### 5.3 Ruta de Envío de Comandos (RadeonSI)
```
si_flush_gfx_cs(ctx, flags, fence)
  ├─ Prepara IB (si_begin_new_gfx_cs)
  ├─ ws->cs_flush(cs, flags, &fence)  ← envía al kernel via DRM
  ├─ Kernel procesa PM4 IBs
  │    └─ PACKET3_SET_CONTEXT_REG → setup de contexto VM/page tables
  └─ si_begin_new_gfx_cs(ctx, false)  ← prepara siguiente IB
```

### 5.4 Ruta de Envío de Comandos (RADV/Vulkan)
Igual camino: `radv_queue.c` → submit IBs → kernel DRM → amdgpu device.

---

## 6. Mapas de Flujo End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│ PCI ID 1002:699F                                                  │
│   ↓                                                               │
│ amdgpu_pci_probe() → amdgpu_device_init()                         │
│   ↓                                                               │
│ adev->asic_type = CHIP_POLARIS12                                  │
│   ↓                                                               │
│ IP Blocks: GMC v8.0, SDMA v4.0, GFX v8.0                          │
│   ↓                                                               │
│ gmc_v8_0_sw_init() → VM size config (40-bit, 64 VMID)             │
│   ↓                                                               │
│ gmc_v8_0_hw_init() → GART enable + PAGE_TABLE_BASE_ADDR (MMIO)    │
│   ↓                                                               │
│ amdgpu_vmid_reset_all() → VMIDs limpios                           │
│   ↓                                                               │
│ Mesa detecta POLARIS12 → CHIP_POLARIS12 → GFX8                    │
│   ↓                                                               │
│ Mesa envía PM4 IBs via amdgpu winsys                              │
│   ↓                                                               │
│ Kernel procesa IBs → SET_CONTEXT_REG → switching de VMID          │
│   ↓                                                               │
│ GPUVM: page tables basadas en PAGE_TABLE_BASE_ADDR (GMC v7.x)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Relación con Findings Existentes

| Finding | Estado | Verificación en código fuente |
|---------|--------|-------------------------------|
| 1610 | VRAM footprint | Confirmado via amdgpu_bo_gpu_offset + GART |
| 1611 | Firefox RDD offload | No contradicto: offload standby explica VRAM idle |
| 1612 | Ring buffer EINVAL | SDMA IB submission path documentado |
| 1613 | CP idle + VMIDs activos | Confirmado: mmCP_VMID=5, bitmap 0xac43ff6f |
| 1614 | PTE/PDE gap | **CONFIRMADO**: registros existen en `gmc_7_1_d.h`, ausentes en umr regdb |
| 1615 | SDMA gap | SDMA v4.0 es el bloque correcto para GFX8 |

---

## 8. Limitaciones Documentadas (sin declarar defectos)

| Limitación | Evidencia | Origen |
|------------|-----------|--------|
| UMR no lee PTE/PDE base | Registros en `gmc_7_1_d.h` no en `gfx_8_0_0.reg` | Tool limitation |
| SDMA0 regs no legibles via umr -r | Falla rc=1 en findings 1613 | Tool limitation |
| debugfs no disponible | Entorno actual sin montaje debugfs | Contexto limitación |
| No PM4 IB captura | Sin acceso root/hardware | Observabilidad limitada |

---

## 9. Conclusiones Técnicas (DEMOSTRADA)

1. **PCI → CHIP_POLARIS12**: Confirmado en kernel y Mesa
2. **GMC v8.0 IP block**: Configura GPUVM para GFX8/Polaris12 con 40-bit address space
3. **PTE/PDE base registers**: Existen en MMIO (0x54f-0x55e), programados vía WREG32 durante GART init
4. **VMID allocation**: 16 VMIDs por hub, VMID 0 reservado, 1-15 dinámicos
5. **Page table updates**: CPU (kmap) o SDMA (IB) según vm_update_mode
6. **Mesa detection**: POLARIS12 → GFX8, family "polaris11"
7. **Observability gap**: Limitación del regdb de UMR, no del hardware

---

## 10. Siguiente Pregunta Técnica Justificada

**Pregunta:** ¿Puede actualizarse el regdb de UMR para incluir los registros GMC v7.x (mmVM_CONTEXTn_PAGE_TABLE_BASE_ADDR y relacionados) permitiendo observación read-only directa de las bases de página tabla en Polaris12?

**Justificación técnica:**
- Los registros existen y son legibles vía MMIO (WREG32 demostrado en kernel)
- El gap es puramente del regdb de la herramienta
- Una actualización del regdb permitiría cierre completo del nodo GPUVM/PTE en finding 1614
- Es una operación read-only (no escritura hardware), dentro del alcance autorizado
- No requiere cambios al kernel, driver, firmware ni hardware

**Próximos pasos:**
1. Extraer definiciones de registro de `gmc_7_1_d.h` (mmVM_CONTEXTn_*)
2. Comparar con formato del regdb de UMR (gfx_8_0_0.reg)
3. Documentar registros faltantes para posible actualización del regdb
4. Validar que otros registros GMC v7.x (mmVM_CONTEXTn_CNTL, START_ADDR, END_ADDR) también faltan

---