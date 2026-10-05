# 1434 — el mapa de los nueve bloques que sí se ejecutan, y ocho cosas que el proyecto tenía mal

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=ESPECIFICACION+REFUTACIONES-MULTIPLES
TRACK=STATIC(corpus) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=04-IMPLEMENTACION/rx550-driver/  en bloque — ocho correcciones, abajo §5
         08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md:192-196   (16 golden settings -> 17)
         el diseno de SDMA, IH y VMID del driver propio
ORIGEN=el hallazgo 1418 abrio la pregunta "cuales son los nueve bloques y que registros
       tienen".  Esta es la respuesta, y trae correcciones que habrian costado un kernel
       panic si se hubieran escrito al codigo sin comprobarlas.
ESTADO=PROBADO · los nueve bloques, su fichero de codigo y su cabecera de registros
       · la direccion es indice dword ABSOLUTO dentro de BAR5, no base-relativa
       · ocho correcciones, cuatro de ellas de cosas que NO existen en esta ASIC
```

## 0. La decisión de método: por qué aquí NO hay una tabla de offsets

Este hallazgo **no transcribe los ~300 offsets** al árbol del proyecto, y es deliberado:

> Los hallazgos 1428 y 1434 juntos dicen que las cabeceras `asic_reg/*_d.h` del vendor son
> **la única autoridad posible** para los offsets en esta tarjeta. Copiar ~300 números a
> un `.h` nuestro crea **una segunda autoridad** que se desincroniza sin que nadie lo note,
> que es exactamente el modo de fallo que el proyecto ya ha sufrido con
> `RX550_PDB0_ENTRIES 512` (hallazgo 1416).

**La especificación es: "usa estas cabeceras, con estas correcciones de cabecera".** Los
offsets se leen del original, que es lo correcto, y el original no se puede desincronizar.
Lo que se fija aquí es **qué cabecera es cuál**, **el orden**, y **lo que no existe**.

## 1. Los nueve bloques: fichero de código y cabecera de registros

Medido del log (1418), y cada fila verificada contra el `ip_block` que la registra.

| # | log | fichero de código | cabecera que incluye | ¿`asic_reg/gfx/` o `ih/`? |
|---|---|---|---|---|
| 0 | `common_v1_0_0` | `vi.c` | `vi.h`, `vid.h`, `gca/gfx_8_0_d.h` | — |
| 1 | `gmc_v8_1_0` | **`gmc_v8_0.c`** | **`gmc/gmc_8_1_d.h`** | — |
| 2 | `ih_v3_0_0` | **`tonga_ih.c`** | **`oss/oss_3_0_d.h`** + `bif/bif_5_1_d.h` | **`ih/` NO existe** |
| 3 | `gfx_v8_0_0` | **`gfx_v8_0.c`** | **`gca/gfx_8_0_d.h`** | **`gfx/` NO existe** |
| 4 | `sdma_v3_1_0` | **`sdma_v3_0.c`** | **`oss/oss_3_0_d.h`** | — |
| 5 | `smu_v1_0_0` | `NOT_FOUND` (corpus podado) | `NOT_FOUND` | — |
| 6 | `dce_v1_0_0` | `NOT_FOUND` (corpus podado) | `NOT_FOUND` | — |
| 7 | `uvd_v6_3_0` | `uvd_v6_0.c` | `uvd/uvd_6_0_d.h` | — |
| 8 | `vce_v3_4_0` | `vce_v3_0.c` | `vce/vce_3_0_d.h` | — |

**Tres de los cuatro directorios de cabecera que se adivinarían están en otro sitio:**
no existe `asic_reg/gfx/`, ni `asic_reg/ih/`, ni `asic_reg/sdma3/` para esta ASIC. El
nombre del bloque no adivina el nombre del fichero, y esa es una trampa de compilación, no
de semántica: un driver que incluya `asic_reg/gfx/gfx_8_0_d.h` **no compila**.

Las filas 5 y 6 son `NOT_FOUND` **por podado del corpus**, no porque los registros no
existan. Queda dicho para que nadie lo lea como un hecho del hardware.

## 2. La dirección de acceso: un dato que cambia el modelo mental

```text
RREG32(reg) -> amdgpu_device_rreg(adev, reg, 0)        amdgpu.h:1261
WREG32(reg,v) -> amdgpu_device_wreg(adev, reg, v, 0)   amdgpu.h:1263
```

**No hay `SOC15_REG_OFFSET`, no hay `reg_offset[][]`, no hay despacho por bloque.** El
offset es **un índice dword absoluto dentro de BAR5**:

```text
direccion = BAR5_base + (offset << 2) = 0xF7D00000 + offset*4
```

Comprobación de rango contra los máximos de cada cabecera:

| cabecera | offset máximo | bytes | ¿cabe en BAR5 (256 KiB)? |
|---|---|---|---|
| `gmc/gmc_8_1_d.h` | `0xf9cd` | `0x3E734` | sí |
| `gca/gfx_8_0_d.h` | `0xfb56` | `0x3ED58` | sí |
| `oss/oss_3_0_d.h` | `0xfe35` | `0x3F8D4` | sí |

> **Esto cierra por qué la contradicción de `arct_ip_offset.h` (hallazgo de Arcturus) era
> irrelevante**: aquel era el mecanismo *soc15*, con `reg_offset[][]` sobrescrito por un
> blob. **En gfx8 no existe ese mecanismo en absoluto.** Los offsets son constantes de
> compilación y punto.

**Y los doorbells NO están en BAR5.** `amdgpu_mm_wdoorbell()` escribe en
`adev->doorbell.cpu_addr + index` (`amdgpu_doorbell_mgr.c:56-65`), que es **BAR2**
(`:211-215`), y los `AMDGPU_DOORBELL_*` son **offsets en bytes**:

```text
KIQ 0x000 · GFX_RING0 0x020 · sDMA_ENGINE0 0x1E0 · IH 0x1E8   amdgpu_doorbell.h:100-114
```

Asignados por `legacy_doorbell_index_init()` en `vi.c:2177-2191`.

## 3. Las correcciones. Las cuatro primeras son "esto NO existe"

### 3.1 `SDMA_VMID`, `SDMA_RING_CONTROL`, `SDMA_RING_STATUS`, `SDMA_SEMAPHORE_*`, `*GCR*` — **cero apariciones en todo el árbol**

```text
grep de los cinco en drivers/gpu/drm/amd/   ->  0 resultados
```

Los nombres gfx8 son otros, y están en la cabecera OSS:

| nombre soc15 (inexistente aquí) | nombre gfx8 real | offset | quién lo escribe |
|---|---|---|---|
| `SDMA_VMID` | **`mmSDMA0_GFX_VIRTUAL_ADDR`** | `0x34a7` | `sdma_v3_0.c:652-655`, valor **0** para los 16 VMIDs |
| `SDMA_RING_CONTROL` | **`mmSDMA0_GFX_DOORBELL`** | `0x3492` | `sdma_v3_0.c:694-703` |
| `SDMA_RING_STATUS` | `mmSDMA0_STATUS_REG` | `0x340d` | sólo lectura |
| semáforo | **ninguno: es del microcode RLC** | — | — |

**El semáforo de SDMA en gfx8 lo programa el RLC, no el host.** Escribir un
`SDMA_SEMAPHORE_SIGNAL` en un driver para esta tarjeta es importar un nombre de otra
generación. Y `SDMA0_GFX_RB_CNTL__RB_VMID` / `SDMA0_GFX_IB_CNTL__CMD_VMID` **existen pero no
se escriben**: el VMID viaja en el paquete, no en un registro.

Además: **`sdma_v3_0_rlc_resume()` es un stub**, cuerpo `/* XXX todo */ return 0;`
(`sdma_v3_0.c:758-763`). Los registros `mmSDMA0_RLC0_*` / `RLC1_*` están **definidos**
(`oss_3_0_d.h:375-441`) y **ningún código los escribe**.

> **Consecuencia para el driver**: el DMA de cómputa en esta tarjeta no se programa con un
> ring SDMA escrito por el host, sino por el microcode RLC + la vía MEC del GFX. **No hay
> que presupuestar trabajo de driver sobre `mmSDMA0_RLC*`.**

### 3.2 `mmVM_DUMMY_PAGE_FAULT_CNTL/ADDR` existen y **nadie los escribe**

`0x506` / `0x507` están definidas (`gmc_8_1_d.h:603-604`) con sus máscaras
(`gmc_8_1_sh_mask.h:6669-6676`), y **no hay escritor en el corpus**. La página dummy real
de este driver va en otro sitio:

```text
mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR  0x546   gmc_8_1_d.h:633
mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR  0x547   gmc_8_1_d.h:634
   valor = adev->dummy_page_addr >> 12         gmc_v8_0.c:884-885, 914-915
   y además en mmINTERRUPT_CNTL2 0x151b como >>8    tonga_ih.c:112
```

**Son dos mecanismos distintos.** Escribir `0x506`/`0x507` desde una suposición sería
inventar.

### 3.3 `mmGRBM_GFX_CNTL` es de **Navi10**, no de esta ASIC

```text
include/asic_reg/gc/gc_10_1_0_offset.h:2089   mmGRBM_GFX_CNTL = 0x0dc2   <-- Navi10, soc15
```

El equivalente gfx8 es **`mmSRBM_GFX_CNTL 0x391`**, en **`oss/oss_3_0_d.h:88`**, con
coincidencia en tres ASIC distintos (`oss_3_0_d.h:88`, `oss_3_0_1_d.h:76`, `oss_2_4_d.h:78`
para Tonga). El mecanismo de selección:

```c
/* vi.c:578-587, vi.h:29 */
srbm_gfx_cntl = REG_SET_FIELD(0, SRBM_GFX_CNTL, PIPEID,  pipe)   // bits 1:0
              | REG_SET_FIELD(0, SRBM_GFX_CNTL, MEID,    me)     // bits 3:2
              | REG_SET_FIELD(0, SRBM_GFX_CNTL, VMID,    vmid)   // bits 7:4
              | REG_SET_FIELD(0, SRBM_GFX_CNTL, QUEUEID, queue); // bits 10:8
WREG32(mmSRBM_GFX_CNTL, srbm_gfx_cntl);
```

Escribe los 32 bits, y el driver restaura `vi_srbm_select(0,0,0,0)` bajo `srbm_mutex`.

Y **`mmGRBM_GFX_INDEX 0xc200`** es otra cosa: selección de instancia SE/SH
(`gfx_v8_0.c:3671-3771`), no VMID/cola. Es además el **primer golden setting** de esta
placa: `0xe0000000`.

### 3.4 El I2C workaround de `0x67DF` **no aplica a esta tarjeta**

```c
/* gfx_v8_0.c:1268 */
if (adev->pdev->device == 0x67DF && revision == 0xc7)   /* 0x67DF = Polaris11 / 560 */
```

Nuestra tarjeta es **`0x699F`**. El `0xc7` es compartido por Polaris10/11/12, pero la
condición está keyed **por device ID**. **No portar.**

## 4. Las otras cuatro correcciones

| # | el proyecto dice | la verdad | cita |
|---|---|---|---|
| 5 | `golden_settings_polaris11_a11` = 16 registros | **17** | `gfx_v8_0.c:341-357` (contados) |
| 6 | — | el mismo nombre de símbolo existe en **GMC con 4 registros** y en **GFX con 17**. Polaris12 recibe ambos: 4 + 23 = 27 escrituras golden | `gmc_v8_0.c:92-97` / `gfx_v8_0.c:339-358` |
| 7 | `mmVM_CONTEXTS_DISABLE 0x535`, `mmVM_FAULT_CLIENT_ID 0x54e` están disponibles | definidos, y **cero referencias** en `amdgpu/` | `gmc_8_1_d.h:626,635` |
| 8 | el driver podría esperar interrupción | **hay alternativa por hardware**: rptr y wptr se leen de **memoria del host** sin interrupción (`gfx_v8_0.c:6012-6015`, `tonga_ih.c:200`). La interrupción sigue siendo la única señal **asíncrona**, pero *polling* es real | — |

La 8 importa porque el plan de la arista fence/IRQ asumía que sin IRQ no hay oráculo.
**Sí lo hay, y es un oráculo mejor: no necesita privileged access.**

## 5. Confirmación independiente del hallazgo 1428

```c
/* amdgpu/amdgpu_irq.c:318-320 */
/* we only need one vector */
r = pci_alloc_irq_vectors(adev->pdev, 1, 1, flags);
```

**Un vector, y el comentario del propio driver lo dice.** No existe
`AMDGPU_MAX_MSIX_VECTOR_NUM` en el árbol. Además:

- `adev->irq.ih1` / `ih2` **nunca se inicializan** en esta ruta
  (`tonga_ih.c:311-317`), así que `amdgpu_irq_handle_ih1/ih2` no se ejecutarán jamás. El
  reparto en cuatro vectores es de soc15.
- **No existe máscara de interrupción por fuente en MMIO.** No hay `mmGPC_INT_MASK` /
  `mmGPC_INT_CLEAR` en esta ASIC: el enable se hace escribiendo bits en el registro de
  estado **del propio bloque** (`mmSDMA0_CNTL.TRAP_ENABLE`, `mmCP_INT_CNTL_RING0.*`,
  `mmVM_CONTEXT*_CNL.*_INTERRUPT`), y `amdgpu_irq` es contabilidad en software.

> **Dos líneas independientes ahora coinciden**: el PCI config space reporta
> `MSI: Count=1/1` (hallazgo 1428, medido) y el código pide `1, 1` (aquí, leído). **Una
> sola línea de interrupción para toda la GPU, y desmultiplexado por `src_id` en el anillo
> IH, no por vector.**

## 6. Orden mínimo de escritura, en la secuencia del vendor

```
IRQ    mmINTERRUPT_CNTL2 0x151b -> mmINTERRUPT_CNTL 0x151a
     -> mmIH_RB_BASE 0xe31 -> mmIH_RB_CNTL 0xe30 (RB_SIZE | MC_VMID=0 | RPTR_REARM)
     -> mmIH_RB_WPTR_ADDR_LO/HI 0xe35/0xe34 -> RPTR/WPTR = 0
     -> mmIH_DOORBELL_RPTR 0xe42 -> mmIH_RB_CNTL (RB_ENABLE | ENABLE_INTR)
GMC   mmMC_VM_MX_L1_TLB_CNTL 0x819 -> mmVM_L2_CNTL 0x500 -> _2 0x501 -> _3 0x502 -> _4 0x578
VMID0 CTX0_PT_START 0x557 -> END 0x55f -> BASE 0x54f -> PF_DEFAULT 0x546 -> CNTL2 0x50c=0
     -> CTX0_CNTL 0x504 { ENABLE_CONTEXT | PAGE_TABLE_DEPTH=0 | RANGE_FAULT_DEF }
VMID1 CTX1_PT_START 0x558=0 -> END 0x560=max_pfn-1 -> CTX{0,8}_PT_BASE+i
     -> PF_DEFAULT 0x547 -> CNTL2 0x50d=4
     -> CTX1_CNTL 0x505 { ENABLE_CONTEXT | PAGE_TABLE_DEPTH=1 | 7xFAULT_DEF=1
                        | PAGE_TABLE_BLOCK_SIZE = block_size-9 }
FLUSH mmVM_INVALIDATE_REQUEST 0x51e = 1<<vmid        (respuesta en 0x51f)
GFX   23 golden -> mmRLC_CNTL 0xec00 (RLC_ENABLE_F32=1)
     -> mmCP_RB0_CNTL 0x3041 / WPTR 0x3045 / RPTR_ADDR 0x3043-44 / POLL_ADDR 0x3046-47
        / BASE 0x3040+0x30b1 -> mmCP_RB_DOORBELL_CONTROL 0x3059 (+ RANGE 0x305a-5b)
     -> mmCP_MAX_CONTEXT 0x30ae / ENDIAN_SWAP 0x3050 / DEVICE_ID 0x304b / ME_CNTL 0x21b6
     -> KIQ: mmRLC_CP_SCHEDULERS 0xecaa + PACKET3_MAP_QUEUES
     -> HQD: mmCP_PQ_WPTR_POLL_CNTL 0x3083 .EN=0
            -> 0x3248..0x326c, [0x326d..0x3279], 0x326f..0x3278, 0x3245..0x3247 ULTIMO
SDMA  por instancia (+0x200), bucle VMID bajo srbm_mutex:
     GFX_VIRTUAL_ADDR=0 0x34a7 -> GFX_APE1_CNTL=0 0x34a8 -> TILING_CONFIG 0x3406
     -> SEM_WAIT_FAIL_TIMER_CNTL 0x3409 -> GFX_RB_CNTL RB_SIZE 0x3480
     -> RB_RPTR/WPTR/IB_RPTR/IB_OFFSET = 0 -> RB_RPTR_ADDR_HI/LO 0x3488/9
     -> RB_BASE/BASE_HI 0x3481/2 -> GFX_DOORBELL 0x3492
     -> RB_WPTR_POLL_ADDR_LO/HI 0x3487/6 -> POLL_CNTL 0x3485
     -> GFX_RB_CNTL RB_ENABLE=1 -> GFX_IB_CNTL IB_ENABLE=1 0x348a
     -> F32_CNTL HALT=0 0x3412 -> SDMA_CNTL AUTO_CTXSW|ATC_L1 0x3404
SUBMIT wptr doorbell -> BAR2: 0x020 gfx · 0x1E0+0x200·inst sdma · 0x1E8 ih
```

Dos órdenes que no son negociables y que se cobran en kernel panic:

1. **HQD: `mmCP_HQD_ACTIVE 0x3247` se escribe AL FINAL** (`gfx_v8_0.c:4583-4584`), después
   de `0x3248..0x3278`. Y exige que **`struct vi_mqd` sea contigua**, con
   `cp_mqd_base_addr_lo` en el índice 0 y el orden exacto 0x3245, 0x3246, 0x3247… El
   commit indexa por `mqd_reg - mmCP_MQD_BASE_ADDR`, así que **el layout del struct es un
   requisito del hardware**, no una comodidad.
2. **SDMA: `RB_ENABLE` se pone DESPUÉS de programar la dirección del wptr shadow**
   (`sdma_v3_0.c:729`), e `IB_ENABLE` al final. Invertirlo es el cuelgue clásico.

## 7. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/
  vi.c:2049,2105-2123      vi_set_ip_blocks, case CHIP_POLARIS12 — reproduce el log 1:1
  vi.c:578-587             vi_srbm_select
  vi.c:2177-2191           legacy_doorbell_index_init
  gmc_v8_0.c:823-940       secuencia GART + VMID0/VMID1 completa
  gmc_v8_0.c:962-984       gmc_v8_0_gart_disable
  gmc_v8_0.c:35-36,1762    gmc_8_1_d.h ; gmc_v8_1_ip_block
  gfx_v8_0.c:4130-4192,4227-4278   arranque del ring GFX
  gfx_v8_0.c:4399-4587     mqd_init + mqd_commit
  gfx_v8_0.c:339-367,784   golden settings 17 + 6
  gfx_v8_0.c:6012-6038     rptr/wptr desde memoria del host
  sdma_v3_0.c:636-748      secuencia SDMA real
  sdma_v3_0.c:758-763      rlc_resume es un stub
  tonga_ih.c:102-166,311   init del IH ; ih1/ih2 no se inicializan
  amdgpu_irq.c:318-320     pci_alloc_irq_vectors(1,1) — "we only need one vector"
  amdgpu_doorbell_mgr.c:56-65,211   doorbells en BAR2
include/asic_reg/
  gmc/gmc_8_1_d.h · gca/gfx_8_0_d.h · oss/oss_3_0_d.h · bif/bif_5_0_d.h · bif/bif_5_1_d.h
  uvd/uvd_6_0_d.h · vce/vce_3_0_d.h
  (NO existen: gfx/, ih/ ; sdma3/sdma3_4_2_2_offset.h es soc15 y no se usa)
```

```text
ESTADO=PROBADO · los 9 bloques con su .c y su cabecera; direccion = indice dword ABSOLUTO
       en BAR5 (0xF7D00000 + off<<2); los doorbells en BAR2 con offsets en BYTES
       · el mecanismo reg_offset[][] de soc15 NO EXISTE en gfx8: los offsets son constantes
         de compilacion, y por eso la contradiccion de arct_ip_offset.h era ajena
REFUTADO por NO_EXISTIR en esta ASIC:
       SDMA_VMID · SDMA_RING_CONTROL · SDMA_RING_STATUS · SDMA_SEMAPHORE_* · *GCR* · sdma_v4_0.c
REFUTADO por estar en otro ASIC:
       mmGRBM_GFX_CNTL (es Navi10, gc_10_1_0_offset.h:2089) ; el I2C workaround de 0x67DF
REFUTADO por no usarse:
       mmVM_DUMMY_PAGE_FAULT_CNTL/ADDR 0x506/0x507 · mmVM_CONTEXTS_DISABLE · mmVM_FAULT_CLIENT_ID
       mmSDMA0_RLC* (definidos, stub de escritor)
CORREGIDO  golden_settings_polaris11_a11 = 17 (no 16); y existe OTRO con el mismo nombre en
       GMC con 4 registros, mismo ASIC, dos simbolos
NUEVO     hay orACLE por hardware sin IRQ: rptr/wptr se leen de memoria del host
CONFIRMADO 1428 por via independiente: PCI dice MSI Count=1/1; el codigo pide pci_alloc_irq
       (pdev, 1, 1) con el comentario "we only need one vector"
LIMITE    bloques 5 y 6 (powerplay, dm) NOT_FOUND por podado del CORPUS, no del hardware
RIESGO    dos ordenes no negociables: HQD_ACTIVE se escribe ULTIMO y exige struct vi_mqd
       contiguo; en SDMA RB_ENABLE va tras la direccion del wptr shadow, IB_ENABLE al final
DECISION  no se transcriben ~300 offsets al arbol: las cabeceras del vendor son la unica
       autoridad (1428) y copiarlas crearia una segunda que se desincroniza en silencio
Siguiente  1) verificar adversarialmente el §6 antes de escribir una linea de codigo: un
          offset mal puesto en un driver es un kernel panic, no un numero erroneo
       2) bloque 6 (dm) es el que trae la salida de display, y es el que el driver propio
          necesita para NO perder la consola.  Es NOT_FOUND por podado y hay que resolverlo
       3) la arista fence: decidir IRQ (asincrono, 1 vector) vs polling de rptr/wptr, con el
          dato de que el polling es viable y no necesita privileged access
```
