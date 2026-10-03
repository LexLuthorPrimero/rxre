```
CLASE      PROVEN · tablas CALCULADAS, no escritas a mano
FUENTE     corpus linux-7.1.3 · /var/tmp/rx550-incident-pre-reboot-dmesg.txt
GENERADO   report 1.0 · cada tabla lleva el comando que la produce
REGENERAR  una regeneracion sin cambios da un fichero byte-identico
UBICACION  /var/tmp/rx550/  (durable; sobrevivio a 3 reinicios)
```


## 1. Ruta Polaris12 — alcance de los accesos

```
  accesos totales   578
  offset UNICO      563   <- lo que veria el preprocesador
  conflicto REAL    0   <- >0 seria hallazgo del corpus
  bloque shader     292 accesos, 292 con offset unico (antes invisible: solo SOC15)
  bloque IH         14 accesos, 0 con offset unico (acceso indirecto)
```

```text
regctx --causal   # o: kit.py <raiz> --causal --hdr-auto
```

## 2. Guardas — deben ser 0 salvo explicación

```
  ficheros con #include pero 0 cabeceras : 0
  accesos sin simbolo resuelto         : 1
      mmMC_SEQ_MISC0_FIJI  gmc_v8_0.c:1108  RREG32
```

## 3. Espacios de offset — por qué hay dos valores

```
  SOC15    48 registros distintos
  plano   210 registros distintos
```

GFX8 tiene numeracion **plano** (`gca/*_d.h`) y **SOC15**
(`gc_*_offset.h`). El mismo simbolo tiene dos offsets y **ambos
son correctos**. Confundirlos produce el offset equivocado con
apariencia de error de lectura.

### Registros con dos valores (1)

| registro | plano | SOC15 |
|---|---|---|
| mmGRBM_STATUS2 | 0x02002 | 0x00da2 |

## 4. Offset de la ruta VI/GFX8.1

_offset deducido del grafo de includes del propio .c_

| registro | offset | espacio | cabecera | fichero | N |
|---|---|---|---|---|---|
| mmATC_MISC_CG | `0x00cd4` | plano | gmc_8_1_d.h | gmc_v8_0.c | 1529 |
| mmATC_VMID0_PASID_MAPPING | `0x00ce7` | plano | gmc_8_1_d.h | gmc_v8_0.c | 633 |
| mmBIF_FB_EN | `0x01524` | plano | bif_5_0_d.h | gmc_v8_0.c | 184 |
| mmCB_CGTT_SCLK_CTRL | `0x0f0a8` | plano | gfx_8_0_d.h | gfx_v8_0.c | 5778 |
| mmCC_GC_EDC_CONFIG | `0x03098` | plano | gfx_8_0_d.h | gfx_v8_0.c | 1622 |
| mmCC_GC_SA_UNIT_DISABLE | `0x00fe9` | SOC15 | gc_10_3_0_offset.h | gfxhub_v2_1.c | 520 |
| mmCC_GC_SHADER_ARRAY_CONFIG | `0x0226f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 7064 |
| mmCC_RB_BACKEND_DISABLE | `0x0263d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 3421 |
| mmCGTS_SM_CTRL_REG | `0x0f000` | plano | gfx_8_0_d.h | gfx_v8_0.c | 5458 |
| mmCONFIG_MEMSIZE | `0x0150a` | plano | bif_5_0_d.h | gmc_v8_0.c | 560 |
| mmCP_DEVICE_ID | `0x0304b` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4140 |
| mmCP_ENDIAN_SWAP | `0x03050` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4139 |
| mmCP_HQD_ACTIVE | `0x03247` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4369 |
| mmCP_HQD_CNTL_STACK_OFFSET | `0x03273` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4524 |
| mmCP_HQD_CNTL_STACK_SIZE | `0x03274` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4525 |
| mmCP_HQD_CTX_SAVE_BASE_ADDR_HI | `0x03271` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4523 |
| mmCP_HQD_CTX_SAVE_BASE_ADDR_LO | `0x03270` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4522 |
| mmCP_HQD_CTX_SAVE_CONTROL | `0x03272` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4515 |
| mmCP_HQD_CTX_SAVE_SIZE | `0x03276` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4527 |
| mmCP_HQD_DEQUEUE_REQUEST | `0x0325d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4379 |
| mmCP_HQD_EOP_CONTROL | `0x0326c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4422 |
| mmCP_HQD_EOP_DONES | `0x0327a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4531 |
| mmCP_HQD_EOP_EVENTS | `0x0326f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4528 |
| mmCP_HQD_EOP_RPTR | `0x0326d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4520 |
| mmCP_HQD_EOP_WPTR | `0x0326e` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4521 |
| mmCP_HQD_EOP_WPTR_MEM | `0x03279` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4530 |
| mmCP_HQD_ERROR | `0x03278` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4529 |
| mmCP_HQD_IB_CONTROL | `0x0325a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4506 |
| mmCP_HQD_IQ_TIMER | `0x0325b` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4511 |
| mmCP_HQD_PERSISTENT_STATE | `0x03249` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4501 |
| mmCP_HQD_PQ_CONTROL | `0x03256` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4451 |
| mmCP_HQD_PQ_DOORBELL_CONTROL | `0x03254` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4429 |
| mmCP_HQD_PQ_RPTR | `0x0324f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4380 |
| mmCP_HQD_PQ_WPTR | `0x03255` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4381 |
| mmCP_HQD_QUANTUM | `0x0324c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4535 |
| mmCP_HQD_WG_STATE_OFFSET | `0x03275` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4526 |
| mmCP_INT_CNTL_RING0 | `0x0306a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 3846 |
| mmCP_MAX_CONTEXT | `0x030ae` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4138 |
| mmCP_MEC_CNTL | `0x0208d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4283 |
| mmCP_MEC_DOORBELL_RANGE_LOWER | `0x0305c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4656 |

_… y 218 más._

## 5. Bloque shader — acceso SOC15

_antes invisible: el mapa causal no reconocia RREG32_SOC15_

| registro | offset | espacio | cabecera | fichero | N |
|---|---|---|---|---|---|
| mmCB_CGTT_SCLK_CTRL | `0x0f0a8` | plano | gfx_8_0_d.h | gfx_v8_0.c | 5778 |
| mmCC_GC_EDC_CONFIG | `0x03098` | plano | gfx_8_0_d.h | gfx_v8_0.c | 1622 |
| mmCC_GC_SA_UNIT_DISABLE | `0x00fe9` | SOC15 | gc_10_3_0_offset.h | gfxhub_v2_1.c | 520 |
| mmCC_GC_SHADER_ARRAY_CONFIG | `0x0226f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 7064 |
| mmCC_RB_BACKEND_DISABLE | `0x0263d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 3421 |
| mmCGTS_SM_CTRL_REG | `0x0f000` | plano | gfx_8_0_d.h | gfx_v8_0.c | 5458 |
| mmCP_DEVICE_ID | `0x0304b` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4140 |
| mmCP_ENDIAN_SWAP | `0x03050` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4139 |
| mmCP_HQD_ACTIVE | `0x03247` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4369 |
| mmCP_HQD_CNTL_STACK_OFFSET | `0x03273` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4524 |
| mmCP_HQD_CNTL_STACK_SIZE | `0x03274` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4525 |
| mmCP_HQD_CTX_SAVE_BASE_ADDR_HI | `0x03271` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4523 |
| mmCP_HQD_CTX_SAVE_BASE_ADDR_LO | `0x03270` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4522 |
| mmCP_HQD_CTX_SAVE_CONTROL | `0x03272` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4515 |
| mmCP_HQD_CTX_SAVE_SIZE | `0x03276` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4527 |
| mmCP_HQD_DEQUEUE_REQUEST | `0x0325d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4379 |
| mmCP_HQD_EOP_CONTROL | `0x0326c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4422 |
| mmCP_HQD_EOP_DONES | `0x0327a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4531 |
| mmCP_HQD_EOP_EVENTS | `0x0326f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4528 |
| mmCP_HQD_EOP_RPTR | `0x0326d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4520 |
| mmCP_HQD_EOP_WPTR | `0x0326e` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4521 |
| mmCP_HQD_EOP_WPTR_MEM | `0x03279` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4530 |
| mmCP_HQD_ERROR | `0x03278` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4529 |
| mmCP_HQD_IB_CONTROL | `0x0325a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4506 |
| mmCP_HQD_IQ_TIMER | `0x0325b` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4511 |
| mmCP_HQD_PERSISTENT_STATE | `0x03249` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4501 |
| mmCP_HQD_PQ_CONTROL | `0x03256` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4451 |
| mmCP_HQD_PQ_DOORBELL_CONTROL | `0x03254` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4429 |
| mmCP_HQD_PQ_RPTR | `0x0324f` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4380 |
| mmCP_HQD_PQ_WPTR | `0x03255` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4381 |
| mmCP_HQD_QUANTUM | `0x0324c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4535 |
| mmCP_HQD_WG_STATE_OFFSET | `0x03275` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4526 |
| mmCP_INT_CNTL_RING0 | `0x0306a` | plano | gfx_8_0_d.h | gfx_v8_0.c | 3846 |
| mmCP_MAX_CONTEXT | `0x030ae` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4138 |
| mmCP_MEC_CNTL | `0x0208d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4283 |
| mmCP_MEC_DOORBELL_RANGE_LOWER | `0x0305c` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4656 |
| mmCP_MEC_DOORBELL_RANGE_UPPER | `0x0305d` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4657 |
| mmCP_MEM_SLP_CNTL | `0x03079` | plano | gfx_8_0_d.h | gfx_v8_0.c | 5472 |
| mmCP_ME_CNTL | `0x021b6` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4086 |
| mmCP_MQD_CONTROL | `0x03267` | plano | gfx_8_0_d.h | gfx_v8_0.c | 4441 |

_… y 121 más._

## 6. Bloque IH — acceso indirecto

_el offset es una variable; el nombre solo existe en la init_

| registro | offset | espacio | cabecera | fichero | N |
|---|---|---|---|---|---|
