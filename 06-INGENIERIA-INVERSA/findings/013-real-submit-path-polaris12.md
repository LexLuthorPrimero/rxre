# 013 — La ruta real de submit de compute de usuario en Polaris 12

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Tarea**: la ruta real `amdgpu_cs_ioctl` → `ring_emit` para la RX 550, y qué parte es del
driver y qué parte es del cliente.
**Clase**: `READ_ONLY/EVIDENCE` — nada ejecutado sobre la GPU.

## Procedencia

Igual que `012`: fuente **upstream 7.2.8** (`linux-7.2.8.tar.xz`, sha256
`12e8d5a9…941`, verificado), y binario `amdgpu.ko` de `7.1.3-200.nobara.fc44`, sha256
`a1a44c24…c024`, srcversion `D68004925455E20A24C2B87`, verificados. Todas las líneas citadas
son de 7.2.8 salvo donde se indica 7.1.3.

---

## 1. La cadena completa

```
userspace:  ioctl(AMDGPU_CS = 0x04, union drm_amdgpu_cs)
              |
   amdgpu_cs.c:1438   amdgpu_cs_ioctl()
              +-- 1456  amdgpu_cs_pass1()      [184]  valida chunks, calcula dispatch_info
              +-- 1460  amdgpu_cs_pass2()      [628]  crea amdgpu_job por IB
              +-- 1464  amdgpu_cs_parser_bos()        traduce y fija BOs
              +-- 1473  amdgpu_cs_patch_jobs()
              +-- 1477  amdgpu_cs_vm_handling()
              +-- 1481  amdgpu_cs_sync_rings()
              +-- 1487  amdgpu_cs_submit()     [1288] drm_sched_job_arm()
              |
   amdgpu_ib.c:124    amdgpu_ib_schedule()
              +-- 200   amdgpu_ring_alloc()
              +-- 230   amdgpu_ring_ib_begin()
              +-- 253   amdgpu_device_flush_hdp()          <-- ANTES de escribir
              +-- 283   amdgpu_ring_emit_ib()               <-- macro -> ring->funcs->emit_ib
              +-- 290   amdgpu_device_invalidate_hdp()     <-- DESPUES
              +-- 300   amdgpu_ring_emit_fence()           (solo si job->uf_addr)
              |
   gfx_v8_0.c:6139    gfx_v8_0_ring_emit_ib_compute()   (4 escrituras)
              |
   gfx_v8_0.c:6234    gfx_v8_0_ring_set_wptr_compute()
                       *ring->wptr_cpu_addr = wptr
                       WDOORBELL32(ring->doorbell_index, wptr)   <-- el doorbell
```

`amdgpu_ring_emit_ib` es una macro (`amdgpu_ring.h:438`):
`((r)->funcs->emit_ib((r), (job), (ib), (flags)))`. El dispatch es por tabla de funciones, no
por switch de chip.

## 2. Por qué esta función y no otra: la tabla, medida

`gfx_v8_0.c:6979 gfx_v8_0_set_ring_funcs()` asigna **sin condición de chip**:

```c
adev->gfx.kiq[0].ring.funcs   = &gfx_v8_0_ring_funcs_kiq;
for (i = 0; i < adev->gfx.num_gfx_rings; i++)
        adev->gfx.gfx_ring[i].funcs     = &gfx_v8_0_ring_funcs_gfx;
for (i = 0; i < adev->gfx.num_compute_rings; i++)
        adev->gfx.compute_ring[i].funcs = &gfx_v8_0_ring_funcs_compute;   // :6989
```

`gfx_v8_0_ring_funcs_compute` (`gfx_v8_0.c:6919-6951`):

| Campo | Valor |
|---|---|
| `.type` | `AMDGPU_RING_TYPE_COMPUTE` |
| `.align_mask` | `0xff` |
| `.nop` | `PACKET3(PACKET3_NOP, 0x3FFF)` |
| `.support_64bit_ptrs` | **`false`** |
| `.get_wptr` / `.set_wptr` | `gfx_v8_0_ring_get_wptr_compute` / `..._set_wptr_compute` |
| `.emit_ib_size` | **`7`** (máximo, no fijo) |
| `.emit_ib` | **`gfx_v8_0_ring_emit_ib_compute`** |
| `.emit_fence` | `gfx_v8_0_ring_emit_fence_compute` |
| `.emit_pipeline_sync` | `gfx_v8_0_ring_emit_pipeline_sync` |
| `.emit_vm_flush` | `gfx_v8_0_ring_emit_vm_flush` |
| `.emit_hdp_flush` | `gfx_v8_0_ring_emit_hdp_flush` |
| `.pad_ib` | `amdgpu_ring_generic_pad_ib` |
| `.emit_cntxcntl` | **ausente** |
| `.emit_frame_cntl` | **ausente** |

**Carrizo, Tonga, Fiji, Polaris 10/11/12 y Vega10-compat comparten esta tabla.** Verificado en
binario: `gfx_v8_0_ring_emit_ib_compute` es un **símbolo out-of-line** en `amdgpu.ko`
(0x1472b1 cae dentro de él), así que se puede desensamblar directamente.

### Verificación binaria de que `INDIRECT_BUFFER` es el packet

`0xC0023F00` = `PACKET3(PACKET3_INDIRECT_BUFFER, 2)`. 10 apariciones en `.text` y **las 10**
dentro de una función `*_ring_emit_ib_compute`:

| Símbolo | Nº |
|---|---|
| `gfx_v7_0_ring_emit_ib_compute` | 1 |
| **`gfx_v8_0_ring_emit_ib_compute`** | **1** |
| `gfx_v9_0_ring_emit_ib_compute` | 1 |
| `gfx_v9_4_3_ring_emit_ib_compute` | 1 |
| `gfx_v10_0_ring_emit_ib_compute` | 1 |
| `gfx_v11_0_ring_emit_ib_compute` | 1 |
| `gfx_v11_0_ring_emit_ib_gfx` | 1 |
| `gfx_v12_0_ring_emit_ib_compute` | 1 |
| `gfx_v12_0_ring_emit_ib_gfx` | 1 |
| `gfx_v12_1_ring_emit_ib_compute` | 1 |

Un packet por chip, en la función que emite el IB de compute de ese chip. Confirma `011` por
una vía distinta: no hay un segundo emisor de `INDIRECT_BUFFER` escondido en otra parte.

## 3. Las 4 escrituras, y por qué `DISPATCH_DIRECT` no está aquí

`gfx_v8_0.c:6107-6139`, verbatim:

```c
unsigned vmid = AMDGPU_JOB_GET_VMID(job);
u32 control = INDIRECT_BUFFER_VALID | ib->length_dw | (vmid << 24);

if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID) {      // :6125
        amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
        amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START);
        amdgpu_ring_write(ring, ring->adev->gds.gds_compute_max_wave_id);
}

amdgpu_ring_write(ring, PACKET3(PACKET3_INDIRECT_BUFFER, 2));       // 0xC0023F00
amdgpu_ring_write(ring, (ib->gpu_addr & 0xFFFFFFFC));                 // 32 bits bajos
amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr) & 0xFFFF);      // 16 bits altos
amdgpu_ring_write(ring, control);
```

Cuatro cosas que no son evidententes y que un driver propio tiene que respetar:

1. **La dirección de 48 bits va partida y desalineada**: 32 bits en un payload, 16 en otro.
   No es una dirección de 64 bits contigua. Reconstruirla mal da una dirección con los bits
   altos en el sitio equivocado, y el síntoma es un IB en una dirección basura.
2. **`ib->length_dw` va dentro de `control`**, en dwords, no en el header. El `count=2` del
   header cuenta los dos payloads de dirección; `control` es el tercero y no se cuenta.
   Mismo patrón que ya se vio en el `EVENT_WRITE` de `012` §4: **`count` no incluye el
   último dword.** Por eso `emit_ib_size = 7` y no 4: es un máximo para el caso con
   `SET_CONFIG_REG` (4+3).
3. **El VMID va en los bits 31:24 de `control`**, no en un contexto aparte. Sin él, el
   trabajo se ejecuta en el espacio de direcciones de otro proceso.
4. **`AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID` no es opcional en la práctica.** El comentario
   (`gfx_v8_0.c:6115-6124`) dice: *"high possibility to get wave ID mismatch between ME and
   GDS, leading to a **hw deadlock**… This situation happens **randomly** when at least 5
   compute pipes use GDS ordered append."* Deadlock de hardware, aleatorio, con ≥5 pipes de
   compute. `adev->gds.gds_compute_max_wave_id` se lee del hardware en
   `gfx_v8_0.c:7046` (`RREG32(mmGDS_COMPUTE_MAX_WAVE_ID)`), no es una constante del driver.

**`DISPATCH_DIRECT` no aparece en esta función.** Con `012` §4, el cuadro queda cerrado:
en gfx8, `DISPATCH_DIRECT` existe sólo dentro del workaround EDC de Carrizo, y en nuestra
GPU no se ejecuta.

## 4. El IB lo escribe el cliente, y el grid va dentro

Confirmado, y es el punto que más afecta al diseño de IA-2:

- `amdgpu_ib.c:272-285` itera `ibs[i]` con `ib->ptr` apuntando al IB **del usuario**, que
  llegó en `drm_amdgpu_cs_chunk_ib.va_start`. El driver no construye el IB: lo referencia.
- `pad_ib = amdgpu_ring_generic_pad_ib`, que en gfx8 **sólo alinea con NOPs**. No añade
  contexto ni registros.
- El grid (`COMPUTE_DIM_X/Y/Z`) y `COMPUTE_PGM_LO/HI` **van dentro del IB que escribe el
  cliente**, no en el packet `INDIRECT_BUFFER`. Corrección explícita de lo que dije en
  `011`: el driver no pone el grid en ningún sitio del ring.
- `emit_cntxcntl` y `emit_frame_cntl` **no están en la tabla de compute** (§2), así que en
  `amdgpu_ib.c:258` y `:267` esas dos ramas **se saltan enteras** en gfx8. Confirmado por
  tabla, no por búsqueda de símbolo.

**Consecuencia para nuestro driver**: el contenido del IB es responsabilidad de
`librx550`, y es donde vive el equivalente de lo que hace RADV. Es la parte que **no** se
puede copiar del driver de referencia, porque el driver de referencia también es cliente de
ese IB.

## 5. La fence de compute **no** lleva el workaround de Carrizo

`011` advertía que `gfx_v8_0_ring_emit_fence_gfx` empieza con un EOP dummy y que emitir la
fence sin él da *"fallos de flush de caché: corrupción silenciosa"*. **Eso es cierto y no
aplica a compute.** Medido:

| Función | EOP dummy previo | Evidencia |
|---|---|---|
| `gfx_v8_0_ring_emit_fence_gfx` (`gfx_v8_0.c:6141`) | **sí**, `EVENT_WRITE_EOP` con `seq-1` (líneas 6148-6162) | C |
| `gfx_v8_0_ring_emit_fence_compute` (`gfx_v8_0.c:6237`) | **no**: un único `PACKET3(RELEASE_MEM, 5)` | C |
| `gfx_v8_0_ring_emit_fence_kiq` | no | C |

**El propio driver de referencia no aplica ese workaround a compute**, y el compute de
Polaris 12 funciona con él cargado. Mi advertencia anterior era demasiado general: es un
workaround del **ring de gráficos**, no de la fence en general. `SUPPORTED` por lectura de
las dos funciones.

`gfx_v8_0_ring_emit_fence_compute` (7 dwords): `RELEASE_MEM` con
`EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN |
EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) | EVENT_INDEX(5)`, `DATA_SEL`, `INT_SEL`, y
dirección y secuencia de 64 bits.

## 6. El doorbell de compute

Cerrado, y con fuente:

| Dato | Valor | Fuente |
|---|---|---|
| `ring->doorbell_index` del compute ring | `adev->doorbell_index.mec_ring0 + ring_id` | `gfx_v8_0.c:1863` |
| `mec_ring0` | `AMDGPU_DOORBELL_MEC_RING0` = **`0x010`** | `amdgpu_doorbell.h:103`, `vi.c:2173` |
| Quién lo pone | `legacy_doorbell_index_init`, en `vi_common_ip_funcs` | `vi.c:1441`, `vi.c:2170` |
| Escritura | `writel(v, adev->doorbell.cpu_addr + index)` | `amdgpu_doorbell_mgr.c` |
| Base de la apertura | **PCI resource 2**: `pci_resource_start(adev->pdev, 2)` | `amdgpu_doorbell_mgr.c`, `amdgpu_doorbell_init()` |

El índice es un **offset en bytes** dentro de la apertura, no un índice de registro. Y la
generación VI **no** usa la apertura unificada de SOC15/Navi: ésa es la de
`AMDGPU_SOC_V1_0_DOORBELL_*` (`amdgpu_doorbell.h:351+`) y no aplica aquí.

**Lo que NO está establecido**: el tamaño en dwords de cada anillo de compute para
Polaris 12, y el `ring->size` que corresponde. Requiere leer `gfx_v8_0.c` donde se calculan
`max_compute_rings` / `compute_dw_size`, que no he seguido. `NOT_DETERMINED`, con la vía
identificada.

## 7. Corregí un error mío sobre Polaris 12 y `soc15.c`

Antes de esta ronda escribí que el árbol del repo carecía de los IP versions de Polaris 12
porque no aparecían en `soc15.c`. **Era una inferencia mía, y era falsa**: no faltan, es que
Polaris 12 **no pasa por `soc15.c`**. Entra por `vi.c:2107` (`vi_set_ip_blocks`), la
generación VI. El mismo error de familia se repite por tercera vez en este proyecto —buscar en
el sitio de una generación y concluir que algo no existe—; ya me pasó con `vulkan.h` y con
los headers autogenerados. Lo dejo escrito para que no se repita.

## 8. Lo que sigue sin establecer

| Dato | Estado | Por qué |
|---|---|---|
| Contenido real del IB que emite RADV para esta GPU | `NOT_AVAILABLE` | requiere capturar un submit en runtime; `protocol-dumps/` está vacío y eso es `RUNTIME_EXECUTION` |
| `COMPUTE_DIM_X/Y/Z` que pone el cliente | `NOT_DETERMINED` | los registros existen (`gfx_8_0_sh_mask.h`, MASK `0xffffffff`, SHIFT `0x0`, ya established en `011`) pero su **valor** depende del shader |
| `gds_compute_max_wave_id` para esta GPU | `NOT_DETERMINED` | se lee del hardware (`gfx_v8_0.c:7046`); un valor inventado aquí es un deadlock aleatorio |
| Tamaño del compute ring | `NOT_DETERMINED` | §6 |
| `GFX_HWIP` real | `NOT_DETERMINED` | requiere UMR, no autorizado |

**Ninguna de estas cinco necesita `RUNTIME_EXECUTION` para *cerrarse*, pero cuatro sí para
*medirse*.** `P-6` de IA-3 sigue bloqueado por la que IA-1 no puedo resolver sin hardware.
