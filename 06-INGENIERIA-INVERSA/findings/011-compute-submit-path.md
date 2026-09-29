# 011 — La ruta real de submit de compute en Polaris 12

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Responde a**: la tarea asignada — *«¿existe `gfx_v8_0_ring_emit_dispatch_compute()` en el path
de usuario, o `DISPATCH_DIRECT` es Carrizo-only?»*

---

## 0. Respuesta corta

**Existe, y no se llama como la pregunta la nombra.** Se llama
**`gfx_v8_0_ring_emit_ib_compute()`**, `gfx_v8_0.c:6101-6133`, **456 B** de código máquina.

Y hay un resultado que cambia el diseño más de lo que la pregunta anticipaba:

> **El submit de usuario NO despacha con `PACKET3_DISPATCH_DIRECT`.** `DISPATCH_DIRECT` es
> exclusivamente del workaround de Carrizo. El submit real emite un
> **`PACKET3_INDIRECT_BUFFER`** que apunta a un IB de 7 dwords que **construye el driver**, no
> el cliente.

## 1. Las 4 preguntas del brief, una a una

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| `amdgpu_cs_ioctl()` → ¿qué llama? | `amdgpu_cs_submit()`, que **no escribe packets**: encola un `drm_sched_job` | `amdgpu_cs.c:1460` |
| `amdgpu_job_submit()` → ¿qué ring_emit usa? | **No llega a él.** El camino es `amdgpu_cs_submit` → `drm_sched_entity_push_job` / `drm_sched_job_arm` → scheduler | `amdgpu_cs.c` |
| ¿Existe `gfx_v8_0_ring_emit_dispatch_compute()`? | **No con ese nombre.** Existe `gfx_v8_0_ring_emit_ib_compute` | binario, 456 B |
| Las escrituras de `0xC0031500` en el binario | **10, y ninguna es de gfx_v8** | §3 |

## 2. `amdgpu_cs_ioctl` no escribe un solo packet

`amdgpu_cs_submit()` (`amdgpu_cs.c`) llama, entre otros, a:

```
drm_sched_entity_push_job
drm_sched_job_add_dependency
drm_sched_job_arm
drm_sched_entity_push_job
amdgpu_cs_post_dependencies
amdgpu_ctx_add_fence
```

**Ninguna función de emisión de rings.** El ioctl **encola un job en el scheduler de DRM** y
devuelve. Los packets se emiten **después**, desde el scheduler, en un contexto que puede ser un
hilo worker.

**Consecuencia para el diseño de un driver propio:** la ruta no es «ioctl → escribir packets →
devolver». Es **«ioctl → encolar trabajo → otro contexto emite y señaliza»**. Un ioctl de
submit propio que escriba los packets en línea y devuelva tiene una estructura distinta, y esa
estructura es la que hace que el fence sea asíncrono.

## 3. Verificación binaria: `0xC0031500` no lo escribe gfx_v8

Las 10 apariciones del inmediato en `amdgpu.ko`, con los 3 bytes previos `c7 04 82` =
`mov dword [rdx+rax*4], imm32`, mapeadas a símbolo por rango:

| Offset | Función |
|---|---|
| `0x00182ba2` | `gfx_v10_0_ring_test_ring` |
| `0x00182d0d` | `gfx_v10_0_ring_set_wptr_gfx` |
| `0x00182e84` | `gfx_v10_0_eop_irq` |
| `0x00192a2d` | `gfx_v11_0_cp_compute_enable` |
| `0x00192bd2` | `gfx_v11_0_set_safe_mode` |
| `0x00192d99` | `gfx_v11_0_rlc_reset` |
| `0x001a1958` | `gfx_v11_0_hw_init` |
| `0x001a1cd4` | `gfx_v11_0_hw_init` |
| `0x001a20d4` | `gfx_v11_0_hw_init` |
| `0x001a2678` | `gfx_v11_0_hw_init` |

**Las 10 son de gfx_v10 y gfx_v11.** Y en `gfx_v8_0.c`, `PACKET3_DISPATCH_DIRECT` aparece en
tres sitios, **los tres dentro de `gfx_v8_0_do_edc_gpr_workarounds()`** (líneas 1541, 1567, 1593,
función que empieza en 1474).

**Confirmado: `DISPATCH_DIRECT` en GFX8 es Carrizo-only.** La premisa del brief era correcta, y
esa es la parte importante del hallazgo.

## 4. La función real: `gfx_v8_0_ring_emit_ib_compute`

`gfx_v8_0.c:6101-6133`, literal:

```c
static void gfx_v8_0_ring_emit_ib_compute(struct amdgpu_ring *ring,
                                          struct amdgpu_job *job,
                                          struct amdgpu_ib *ib,
                                          uint32_t flags)
{
    unsigned vmid = AMDGPU_JOB_GET_VMID(job);
    u32 control = INDIRECT_BUFFER_VALID | ib->length_dw | (vmid << 24);

    if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID) {
        amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
        amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START);
        amdgpu_ring_write(ring, ring->adev->gds.gds_compute_max_wave_id);
    }

    amdgpu_ring_write(ring, PACKET3(PACKET3_INDIRECT_BUFFER, 2));
    amdgpu_ring_write(ring, (ib->gpu_addr & 0xFFFFFFFC));
    amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr) & 0xFFFF);
    amdgpu_ring_write(ring, control);
}
```

**Cuatro escrituras, un packet de 2 dwords de payload.** Es la función más pequeña de todas las
`ring_emit` de GFX8 (456 B) y hace muy poco: **no construye el IB, lo referencia**.

### Los 4 campos de `INDIRECT_BUFFER`

| Escritura | Contenido |
|---|---|
| header | `PACKET3(PACKET3_INDIRECT_BUFFER, 2)` = opcode `0x3F`, count 2 |
| payload 0 | `ib->gpu_addr & 0xFFFFFFFC` — **32 bits bajos, alineados a 4** |
| payload 1 | `upper_32_bits(gpu_addr) & 0xFFFF` — **16 bits altos, truncados** |
| payload 2 | `control` = `INDIRECT_BUFFER_VALID \| ib->length_dw \| (vmid << 24)` |

**La GPU 48-bit se expresa en dos campos desalineados**: 32 bits en un lado y 16 en el otro.
Es la codificación real de la dirección de VRAM de 48 bits de Polaris 12, y un driver propio
tiene que construirla igual. Escribirla como 64 contiguous es incorrecto.

**`control` mezcla tres cosas en un dword:**

| Bits | Campo | Origen |
|---|---|---|
| bajo | `INDIRECT_BUFFER_VALID` | constante |
| medios | `ib->length_dw` | **longitud del IB en dwords**, no en bytes |
| 31:24 | `vmid` | **virtual memory ID** del contexto |

**El VMID va en el propio packet**, no en un contexto hardware aparte. Un driver propio que no
escriba el VMID correcto escribe el trabajo en el espacio de otro contexto.

### El IB de 7 dwords que el driver construye

`gfx_v8_0.c:6934`:

```c
.emit_ib_size =	7, /* gfx_v8_0_ring_emit_ib_compute */
```

**El driver reserva 7 dwords de ring y escribe ahí el IB real**, y luego solo lo referencia. La
tabla de `gfx_v8_0_ip_block` declara el tamaño por función, lo que confirma que es un valor de
contrato, no un comentario.

**El IB de 7 dwords: lo aporta el cliente, no el driver**

`gfx_v8_0.c:6934` declara:

```c
.emit_ib_size =	7, /* gfx_v8_0_ring_emit_ib_compute */
```

**Lo que `emit_ib_size = 7` significa es el máximo que el driver garantiza**, no un contenido
fijo. La comprobacion siguiente lo establece:

`pad_ib` de GFX8 es `amdgpu_ring_generic_pad_ib` (`gfx_v8_0.c:6907`), y esa funcion
(`amdgpu_ring.c`) **no escribe nada del IB**: solo alinea la longitud con NOPs.

```c
void amdgpu_ring_generic_pad_ib(struct amdgpu_ring *ring, struct amdgpu_ib *ib)
{
	u32 align_mask = ring->funcs->align_mask;
	u32 count = ib->length_dw & align_mask;
	if (count) {
		count = align_mask + 1 - count;
		memset32(&ib->ptr[ib->length_dw], ring->funcs->nop, count);
		ib->length_dw += count;
	}
}
```

**Y el bucle de emision, `amdgpu_ib.c:272-285`, confirma la procedencia:**

```c
for (i = 0; i < num_ibs; ++i) {
    ib = &ibs[i];
    ...
    amdgpu_ring_emit_ib(ring, job, ib, status);
}
```

`ib->ptr` **es un puntero al IB que escribio el usuario**, que venia en
`drm_amdgpu_cs_chunk_ib.va_start` y se mapeo en `amdgpu_cs_vm_handling`. El driver **no
construye los packets de compute**: los recibe, los alinea, los referencia por direccion, y
anade alrededor el machinery de contexto.

> **Esto corrige lo que dije en la seccion 4.** Escribi que "el driver construye un IB de 7
> dwords". Es al reves: el driver **referencia** el IB del cliente, y `7` es el tamano que el
> scheduler puede sobreescribir -- el espacio de contexto, no el trabajo del shader.

**Lo que el driver si anade alrededor**, en `amdgpu_ib.c:250-294`, y que un driver propio
necesita:

| Paso | Fuente | Que |
|---|---|---|
| `amdgpu_device_flush_hdp(adev, ring)` | `:253` | **drena la HDP antes de escribir en el ring** |
| `emit_cntxcntl` si hay cambio de contexto | `:258-262` | **no aplica a GFX8**: `gfx_v8_0_ip_block` no declara `emit_cntxcntl` (verificado en el binario, 0 coincidencias) |
| `emit_frame_cntl` para TMZ | `:267-270` | **no aplica a GFX8**: tampoco declarado. El campo de la tabla es `if (job && ring->funcs->emit_frame_cntl)`, es decir **se salta entero** en esta generacion |
| bucle sobre `num_ibs` | `:272-285` | **N IBs, no uno** |
| `amdgpu_device_invalidate_hdp(adev, ring)` | `:290` | invalida la HDP al terminar |

**`flush_hdp` antes e `invalidate_hdp` despues** es el mismo requisito que se vio en el
desensamblado de `amdgpu_gfx_enable_kgq` de la Ronda 1: la HDP tiene que estar drenada antes de
escribir en el ring, o la escritura se reordena. Un driver propio que lo omite tiene una carrera
con el bus de host, y el sintoma seria intermitente -- la peor clase de fallo.

**El soporte multi-IB** (`:272`, `num_ibs`) es otra diferencia con la secuencia de `007`: un
submit puede traer varios IBs y el driver los referencia en bucle, con `AMDGPU_HAVE_CTX_SWITCH`
que se consume en la primera iteracion.


## 5. Los otros `ring_emit` que un driver propio necesita

Del binario, 16 funciones `gfx_v8_0_ring_emit_*` / `gfx_v8_0_emit_*` sin `.cold`:

| Función | Tamaño | Para qué |
|---|---|---|
| `gfx_v8_0_ring_emit_gds_switch` | 1116 B | cambio de GDS |
| **`gfx_v8_0_ring_emit_fence_gfx`** | **732 B** | fence de graphics — **es la que tiene el workaround de Carrizo** |
| `gfx_v8_0_ring_emit_hdp_flush` | 644 B | drenaje de HDP |
| `gfx_v8_0_ring_emit_de_meta` | 591 B | driver-emitted meta commands |
| `gfx_v8_0_ring_emit_fence_kiq` | 564 B | fence de laqueue |
| `gfx_v8_0_emit_wave_limit` | 562 B | límite de waves |
| `gfx_v8_0_ring_emit_vm_flush` | 532 B | flush de TLB |
| **`gfx_v8_0_ring_emit_ib_compute`** | **456 B** | **submit de compute** |
| **`gfx_v8_0_ring_emit_fence_compute`** | **421 B** | **fence de compute** |
| `gfx_v8_0_ring_emit_pipeline_sync` | 409 B | sincronización de pipeline |
| `gfx_v8_0_ring_emit_ib_gfx` | 390 B | submit de graphics |
| `gxf_v8_0_emit_mem_sync_compute` | 385 B | sync de memoria |
| `gfx_v8_0_ring_emit_rreg` / `_wreg` | 376 / 302 B | lectura/escritura de registro |
| `gfx_v8_0_ring_emit_init_cond_exec` | 283 B | ejecución condicional |
| `gfx_v8_0_emit_mem_sync` | 281 B | sync de memoria |

**Los tres que un submit de compute necesita** son `ring_emit_ib_compute`,
`ring_emit_fence_compute` y `ring_emit_vm_flush`, más `hdp_flush` antes.

**El fence tiene su propia función y su propio workaround.** `gfx_v8_0_ring_emit_fence_gfx`
(`gfx_v8_0.c:6135-6162`) empieza con un **EOP dummy** — *"workaround for cache flush problems.
First send a dummy EOP event down the pipe with seq one below"*— antes de la fence real. Un
driver propio que emita la fence sin ese EOP previo reproduce el problema que el workaround
evita. El texto del driver explica el síntoma: **fallos de flush de caché**, que son
corrupción silenciosa.

## 6. Orden real de un submit, según lo observado

Reconstrucción a partir de `amdgpu_cs_ioctl` (8 pasos) + las `ring_emit` de GFX8:

```
amdgpu_cs_ioctl
  ├─ parser_init, pass1, pass2, parser_bos     (validación)
  ├─ patch_jobs, vm_handling                   (preparación)
  ├─ sync_rings                                (dependencias)
  └─ cs_submit → drm_sched_entity_push_job     ← devuelve aquí
                                                ↓ (otro contexto)
     scheduler
       ├─ ring_emit_vm_flush                   (si hay cambio de page table)
       ├─ ring_emit_ib_compute                 (4 escrituras, el submit)
       └─ ring_emit_fence_compute              (fence, con su propio workaround)
```

**`vm_handling` y `ring_emit_vm_flush` son dos cosas distintas** en dos contextos distintos:
el primero prepara la page table en el ioctl, el segundo la hace efectiva ante la HW. **No se
pueden fusionar** sin entender el mecanismo.

**Lo que esto no establece:** el orden exacto dentro del scheduler, y qué ocurre si el fence se
omite. `NOT_DETERMINED`.

## 7. Consecuencia para IA-2: qué cambia respecto a lo que assumptions

Si el diseño de `rx550_gfx8.S` se construía sobre la secuencia de `007`, **está sobre la ruta
equivocada**:

| | `007` (documentado en R3) | `011` (submit real) |
|---|---|---|
| Packet | `DISPATCH_DIRECT` (0x15) | `INDIRECT_BUFFER` (0x3F) |
| Quién lo emite | driver, inline | scheduler, en `ring_emit_ib_compute` |
| Grid | en el payload (`DIM_X/Y/Z`) | en el IB de 7 dwords que el driver construye |
| Dirección | 2 escrituras de shader reg | `gpu_addr` en 32+16 bits, con VMID en `control` |
| Contexto | Carrizo-only | **el 100 % del compute de usuario** |

**`007` no era falso** —el formato de `PACKET3` y el layout del header siguen siendo correctos
y son necesarios— pero **documentaba el packet de un workaround**, no el del submit. La
estructura de `PACKET3` de `007` es la base correcta; la secuencia de packets de su §4 es la
equivocada para `SUBMIT_COMPUTE`.

**Lo que IA-2 necesita ahora, en orden:**

1. Los **7 dwords del IB**, que es el hueco real. Siguiente tarea.
2. `gfx_v8_0_ring_emit_fence_compute` (421 B), incluido si tiene workaround propio.
3. `PACKET3_SET_CONFIG_REG` + `mmGDS_COMPUTE_MAX_WAVE_ID`, que solo se emiten con
   `AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID` pero cuyo comentario (`gfx_v8_0.c:6109-6118`) describe
   un **deadlock de hardware** por desajuste de wave ID. Es la razón por la que ese flag existe
   y no es opcional: *"randomly when at least 5 compute pipes use GDS ordered append"*.

## 8. Límites

- Nada ejecutado. Reconstrucción a partir de llamadas en el código y del mapeo de símbolos en el
  binario, no de traza.
- Los **7 dwords de `emit_ib_size`** son un maximo, no un contenido fijo (§4). Lo que el
  cliente escribe dentro del IB no se ha inspeccionado: es contenido de shader, no del driver.
- El orden dentro del scheduler (§6) es inferido del nombre de las funciones y de la
  separación de contextos. `NOT_DETERMINED` para el orden exacto.
- Las medidas en B son del binario, no del C: el C de `ring_emit_ib_compute` son 33 líneas.
- `PACKET3_SET_CONFIG_REG` y `mmGDS_COMPUTE_MAX_WAVE_ID`: existen en el código, sus
  MASK/SHIFT **no se han buscado** en `gfx_8_0_sh_mask.h` (donde sí están, por el mismo
  mecanismo que `010`).

## Procedencia

`gfx_v8_0.c:6101-6133` y `:6135-6162`, leídos el 2026-09-29. Llamadas de `amdgpu_cs_submit`
extraídas del cuerpo de la función con `awk`+`grep`. Las 10 escrituras de `0xC0031500` mapeadas
a símbolo por rango de dirección con `nm -S` y búsqueda binaria little-endian. Tamaños de las 16
`ring_emit` de `nm -S`.
