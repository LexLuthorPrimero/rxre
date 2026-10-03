```
CLASE      contrato · lectura pura · no compila, no escribe en el arbol
GENERADO   contract 1.0
DRIVER     rx550_target.c + target_regs.h + rx550_mmio_access.h
METODO     cada offset del driver se resuelve por GRAFO DE INCLUDES (regctx)
           y se compara con el valor que el propio codigo del driver asume
REGLA      un registro que el driver nombra y el corpus NO confirma NO es
           evidencia: es una asuncion pendiente.  Se listan aparte.
```


## 1. Alcance

```
  driver leido            rx550_target.c sha ce0aa79eb0d02f4d30834302952274be
  defines de offset      5
  registros nombrados    26
  confirmados por corpus 26
  SIN resolver           0
```

> `0x2002` en `RX550_PROBE_READ_INDEX` **coincide** con `mmGRBM_STATUS2 = 0x2002` (espacio plano) que la cadena de evidencia establecio por otro camino. Es corroboracion entre dos roads independientes.

## 2. Registros que el driver nombra y el corpus confirma

| registro | offset | espacio | cabecera | primer uso |
|---|---|---|---|---|
| `mmCP_BUSY_STAT` | `0x0219f` | plano | `gfx_8_0_d.h` | target_regs.h:90 |
| `mmCP_RB0_RPTR` | `0x021c0` | plano | `gfx_8_0_d.h` | target_regs.h:100 |
| `mmCP_RB0_WPTR` | `0x03045` | plano | `gfx_8_0_d.h` | target_regs.h:120 |
| `mmCP_RB_DOORBELL_CONTROL` | `0x03059` | plano | `gfx_8_0_d.h` | target_regs.h:145 |
| `mmCP_RB_WPTR_POLL_ADDR_HI` | `0x03047` | plano | `gfx_8_0_d.h` | target_regs.h:137 |
| `mmCP_RB_WPTR_POLL_ADDR_LO` | `0x03046` | plano | `gfx_8_0_d.h` | target_regs.h:129 |
| `mmCP_RB_WPTR_POLL_CNTL` | `0x021c2` | plano | `gfx_8_0_d.h` | target_regs.h:110 |
| `mmGRBM_STATUS` | `0x02004` | plano | `gfx_8_0_d.h` | target_regs.h:81 |
| `mmGRBM_STATUS2` | `0x02002` | plano | `gfx_8_0_d.h` | rx550_target.c:120 |
| `mmMC_VM_MX_L1_TLB_CNTL` | `0x00819` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:196 |
| `mmMC_VM_SYSTEM_APERTURE_DEFAULT_ADDR` | `0x0080f` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:191 |
| `mmMC_VM_SYSTEM_APERTURE_HIGH_ADDR` | `0x0080e` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:186 |
| `mmMC_VM_SYSTEM_APERTURE_LOW_ADDR` | `0x0080d` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:181 |
| `mmSCRATCH_REG0` | `0x0c040` | plano | `gfx_8_0_d.h` | target_regs.h:155 |
| `mmVM_CONTEXT1_CNTL` | `0x00505` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:89 |
| `mmVM_CONTEXT1_CNTL2` | `0x0050d` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:94 |
| `mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR` | `0x00550` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:126 |
| `mmVM_CONTEXT1_PAGE_TABLE_END_ADDR` | `0x00560` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:136 |
| `mmVM_CONTEXT1_PAGE_TABLE_START_ADDR` | `0x00558` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:131 |
| `mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR` | `0x00547` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:120 |
| `mmVM_INVALIDATE_REQUEST` | `0x0051e` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:99 |
| `mmVM_INVALIDATE_RESPONSE` | `0x0051f` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:115 |
| `mmVM_L2_CNTL4` | `0x00578` | plano | `gmc_8_1_d.h` | rx550_mmio_access.c:176 |
| `mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR` | `0x00576` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:166 |
| `mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR` | `0x00575` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:161 |
| `mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET` | `0x00577` | plano | `gmc_7_1_d.h` | rx550_mmio_access.c:171 |

## 3. Registros que el driver nombra y el corpus NO resuelve

_Estos son **asunciones pendientes**, no evidencia. Cada uno necesita justification antes de considerarse cerrado._

_(ninguno)_

## 4. Constantes de offset del driver

```
  RX550_PROBE_READ_INDEX                   0x2002   (rx550_target.c:123)
  RX550_BAR_INDEX                          0x5   (rx550_mmio.h:34)
  RX550_PM4_SET_SH_REG_DWORDS              0x4   (rx550_submission.h:65)
  TARGET_REG_BAR_INDEX                     0x5   (target_resource.h:56)
  TVM_NR_BASE_REGS                         0x8   (target_vm.h:69)
```

## 4c. SOLAPAMIENTO ENTRE BLOQUES IP

_Un registro que dos IP escriben es donde una implementacion propia puede pisar a otra._

```
  GFX        escribe  73 registros
  GFXHUB     escribe  44 registros
  GMC        escribe  62 registros
  SDMA       escribe  25 registros
```

**GFX ∩ GMC**: 1 registro(s) — `mmSRBM_SOFT_RESET`

**GFX ∩ SDMA**: 1 registro(s) — `mmSRBM_SOFT_RESET`

**GMC ∩ SDMA**: 1 registro(s) — `mmSRBM_SOFT_RESET`

```text
El patron es  set-bit -> udelay(50) -> clear-bit  sobre un
registro COMPARTIDO.  Que sea seguro depende de si la
escritura esta DENTRO de una mutex: eso se verifica por
funcion, no por fichero.
```

| bloque | escritura | función | mutex en esa función | serializado |
|---|---|---|---|---|
| GFX | `gfx_v8_0.c:5032` | 5028-5053 | — | **NO** |
| GFX | `gfx_v8_0.c:5038` | 5028-5053 | — | **NO** |
| GMC | `gmc_v8_0.c:1358` | 1352-1372 | — | **NO** |
| GMC | `gmc_v8_0.c:1364` | 1352-1372 | — | **NO** |
| GFX | `gfx_v8_0.c:5032` | 5028-5053 | — | **NO** |
| GFX | `gfx_v8_0.c:5038` | 5028-5053 | — | **NO** |
| SDMA | `sdma_v3_0.c:1313` | 1309-1327 | — | **NO** |
| SDMA | `sdma_v3_0.c:1319` | 1309-1327 | — | **NO** |
| GMC | `gmc_v8_0.c:1358` | 1352-1372 | — | **NO** |
| GMC | `gmc_v8_0.c:1364` | 1352-1372 | — | **NO** |
| SDMA | `sdma_v3_0.c:1313` | 1309-1327 | — | **NO** |
| SDMA | `sdma_v3_0.c:1319` | 1309-1327 | — | **NO** |

**0 serializadas, 12 NO serializadas.**

> Las escrituras NO serializadas son un requisito para un driver propio: si dos bloques pueden tocar ese registro a la vez, el patrón set→delay→clear se pisa.

_mutex presentes en el corpus (no necesariamente en la funcion): `benchmark_mutex`, `enforce_isolation_mutex`, `grbm_idx_mutex`, `notifier_lock`, `srbm_mutex`

### Alcance de la comprobación

```
  escrituras en la ruta VI (agrupadas por funcion) 71
  funciones que escriben >1 registro            40
  de esas, SIN mutex pero en init secuencial   12
  de esas, SIN mutex en RUNTIME (RIESGO)         24
```

> **24 funciones** escriben varios registros sin mutex:
>   - `gfx_v8_0.c` 3474-3580 `gfx_v8_0_write_harvested_raster_co`: `mmPA_SC_RASTER_CONFIG`, `mmPA_SC_RASTER_CONFIG_1`
>   - `gfx_v8_0.c` 4193-4225 `static void gfx_v8_0_set_cpg_door_`: `mmCP_RB_DOORBELL_CONTROL`, `mmCP_RB_DOORBELL_RANGE_LOWER`, `mmCP_RB_DOORBELL_RANGE_UPPER`
>   - `gfx_v8_0.c` 4365-4384 `static int gfx_v8_0_deactivate_hqd`: `mmCP_HQD_DEQUEUE_REQUEST`, `mmCP_HQD_PQ_RPTR`, `mmCP_HQD_PQ_WPTR`
>   - `gfx_v8_0.c` 4546-4581 `static int gfx_v8_0_mqd_commit(str`: `mmCP_HQD_EOP_RPTR`, `mmCP_HQD_EOP_WPTR`, `mmCP_HQD_EOP_WPTR_MEM`
>   - `gfx_v8_0.c` 4653-4661 `static void gfx_v8_0_set_mec_doorb`: `mmCP_MEC_DOORBELL_RANGE_LOWER`, `mmCP_MEC_DOORBELL_RANGE_UPPER`
>   - `gfx_v8_0.c` 4993-5053 `static int gfx_v8_0_soft_reset(str`: `mmGMCON_DEBUG`, `mmGRBM_SOFT_RESET`, `mmSRBM_SOFT_RESET`
>   - `gfx_v8_0.c` 5477-5516 `static void gfx_v8_0_send_serdes_c`: `mmRLC_SERDES_WR_CTRL`, `mmRLC_SERDES_WR_CU_MASTER_MASK`, `mmRLC_SERDES_WR_NONCU_MASTER_MASK`
>   - `gfx_v8_0.c` 5618-5716 `static void gfx_v8_0_update_medium`: `mmCGTS_SM_CTRL_REG`, `mmCP_MEM_SLP_CNTL`, `mmRLC_CGTT_MGCG_OVERRIDE`, `mmRLC_MEM_SLP_CNTL`

## 5. IMPLEMENTATION GATE — que queda NOT_DETERMINED

```text
PROVEN   mmGRBM_STATUS2 = 0x2002 plano (grafos de includes)
         corroborado por el propio driver del mandate
NOT_DETERMINED  semantica de hardware del valor leido
NOT_DETERMINED  polaris12 vs polaris12_32 (MMIO 0xA92 bloqueado)
NOT_DETERMINED  semantica de cada client ID IH
NOT_DETERMINED  PTBA + invalidate atomicidad en hardware
PREDICCION      ao_cu_mask = 0x001E001E si ambos SE coinciden
```

_Este documento no implementa nada: enumera lo que la evidencia sostiene y lo que todavia no._
