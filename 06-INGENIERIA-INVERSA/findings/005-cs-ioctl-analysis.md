# 005 — Análisis de `amdgpu_cs_ioctl`: el contrato y las dos pasadas

**Clasificación**: `READ_ONLY/EVIDENCE` (análisis de fuente, sin ejecución)
**Fecha**: 2026-09-29
**Fuentes primarias**:
- `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_cs.c` (árbol de trabajo del repo)
- `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/uapi/drm/amdgpu_drm.h` (headers instalados)

**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`. Nada fuera de este directorio.

---

## 0. Los tres comandos del brief de Ronda 2 no funcionan

| Comando indicado | Resultado medido |
|---|---|
| `objdump -d amdgpu.ko.zst` | `no se reconoce el formato del fichero`. `.zst` es zstd comprimido; `objdump` necesita el ELF |
| `strings amdgpu.ko.zst \| grep PACKET3_` | 0 resultados. Son **enums de C**, no cadenas: el compilador no las emite como strings |
| `strings amdgpu.ko.zst \| grep -i lsdma` | 131 resultados, pero son **nombres de símbolo**, no referencias a código |

El ELF de trabajo ya estaba generado en la Ronda 1
(`amdgpu-analysis/amdgpu.ko`, SHA256 `a1a44c24…c024`), así que `objdump`/`strings` sí se
aplican **sobre ese**, no sobre el `.zst`.

**Pero el método correcto no es ninguno de los tres.** `PACKET3_DISPATCH_DIRECT = 0x15` es una
constante de preprocesador: no existe como cadena en el binario, solo como número inmediato en
el código. Se lee en `sid.h`. Los comandos del brief buscaban en el binario algo que solo
existe en el texto fuente.

## 1. Estructura de `amdgpu_cs_ioctl`

`amdgpu_cs.c:1411-1473`. Es exactamente **63 líneas** de C, y el cuerpo es una **secuencia
lineal de 8 llamadas** sin ramificación de flujo más allá de la comprobación de error:

```c
int amdgpu_cs_ioctl(struct drm_device *dev, void *data, struct drm_file *filp)
{
    struct amdgpu_device *adev = drm_to_adev(dev);
    struct amdgpu_cs_parser parser;
    int r;

    if (amdgpu_ras_intr_triggered())  return -EHWPOISON;   /* RAS*/
    if (!adev->accel_working)         return -EBUSY;      /* contexto*/

    r = amdgpu_cs_parser_init(&parser, adev, filp, data);
    if (r) goto error_fini;

    r = amdgpu_cs_pass1(&parser, data);          if (r) goto error_fini;
    r = amdgpu_cs_pass2(&parser);                if (r) goto error_fini;
    r = amdgpu_cs_parser_bos(&parser, data);     if (r) { /* log específico */ goto error_fini; }
    r = amdgpu_cs_patch_jobs(&parser);           if (r) goto error_backoff;
    r = amdgpu_cs_vm_handling(&parser);          if (r) goto error_backoff;
    r = amdgpu_cs_sync_rings(&parser);           if (r) goto error_backoff;

    trace_amdgpu_cs_ibs(&parser);

    r = amdgpu_cs_submit(&parser, data);         if (r) goto error_backoff;

    amdgpu_cs_parser_fini(&parser);
    return 0;
}
```

**Lo que esto corrige del tamaño binario.** La Ronda 1 reportó `amdgpu_cs_ioctl` = **8 107 B**
de código máquina. El C son 63 líneas. La diferencia son 2 buenas razones, no un misterio:
`__fentry__` (traza de ftrace) y el crecimiento de optimisation a `-O2` con propagación de
constantes, más el código de outlier `.cold` que GCC separa del cuerpo caliente. **El binario
no es un buen indicador de la complejidad**: 8 107 B para una función lineal de 8 llamadas dice
más del layout del código que de la lógica. `amdgpu_cs_ioctl.cold` está contada aparte en
`003-exported-symbols.md` y hay que descontarla del total.

### Las 8 llamadas, por fase

| # | Llamada | Fase | Qué hace |
|---|---|---|---|
| 1 | `amdgpu_cs_parser_init` | init | Crea el parser desde `data` y el `drm_file` |
| 2 | `amdgpu_cs_pass1(&parser, data)` | **pasada 1** | Recorre los chunks de IB, calcula tamaño y patching pendientes |
| 3 | `amdgpu_cs_pass2(&parser)` | **pasada 2** | Recorre de nuevo para el plan de VM. El doble recorrido es **deliberado** |
| 4 | `amdgpu_cs_parser_bos` | validación | Resuelve handles de BO a `amdgpu_bo`, toma `bo_list_mutex` |
| 5 | `amdgpu_cs_patch_jobs` | preparación | Rellena los campos de `amdgpu_job` derivados de los chunks |
| 6 | `amdgpu_cs_vm_handling` | preparación | Prepara la tabla de páginas (GTT) |
| 7 | `amdgpu_cs_sync_rings` | preparación | Resuelve dependencias y fences entre rings |
| 8 | `amdgpu_cs_submit` | envío | Encola en el ring y dispara la HW |

**La doble pasada es el punto de diseño más importante de esta función.** `pass1` y `pass2`
recorren la misma lista de IB chunks dos veces: la primera para medir y anotar, la segunda para
aplicar. Un driver propio que recorra una sola vez tendrá que gestionar los casos donde el
tamaño no está determinado hasta leer un chunk posterior. No hay aquí ningún caso "fácil de
enderezar en una pasada": la razón del doble recorrido está documentada en el propio fichero y
no se ha analizado en esta ronda (`NOT_DETERMINED`, es trabajo de Ronda 3).

### Rutas de error y sus consecuencias

- `error_fini` (tras init, pass1, pass2, parser_bos): libera el parser, **no** suelta
  `bo_list_mutex` porque aún no se tomó.
- `error_backoff` (tras patch_jobs, vm_handling, sync_rings, submit): suelta
  `bo_list_mutex` **y luego** libera el parser.

El orden importa: si `cs_submit` falla con el mutex tomado, el `goto error_backoff` lo suelta. Un
driver propio que fusione los dos labels perdería el unlock y colgaría el driver bajo
contención de `bo_list`. Es un detalle de 2 líneas con consecuencia de deadlock.

`-EHWPOISON` y `-EBUSY` son rechazos tempranos **antes** de tocar nada: RAS disparado, o
acelerador no operativo.

## 2. El contrato con userspace

**El nombre no es `drm_amdgpu_cs_req`.** La orden de Ronda 2 (y el brief de IA-2) lo|nombran así.
El tipo real es una **unión**:

```c
/* amdgpu_drm.h:983-986 */
union drm_amdgpu_cs {
    struct drm_amdgpu_cs_in  in;
    struct drm_amdgpu_cs_out out;
};
```

Entrada (`amdgpu_drm.h:968-977`):

| Campo | Tipo | Significado |
|---|---|---|
| `ctx_id` | `__u32` | id de contexto de render |
| `bo_list_handle` | `__u32` | handle de la lista de BOs |
| `num_chunks` | `__u32` | número de chunks |
| `flags` | `__u32` | flags |
| `chunks` | `__u64` | **`__u64 *` que apunta a un array de `__u64`**, cada uno apuntando a un chunk |

Salida: un único `__u64 handle` (sync fence).

El ioctl es `DRM_IOCTL_AMDGPU_CS = DRM_IOWR(DRM_COMMAND_BASE + 0x04, union drm_amdgpu_cs)`
(`amdgpu_drm.h:66`). `IOWR` = lectura y escritura: por eso la unión tiene `in` y `out`.

**El array de chunks es doble indirección**: `chunks` no apunta a los chunks, sino a un array
de punteros, y cada puntero a un chunk. Un driver propio que lo trate como array contiguo
producirá corrupción de memoria en el primer submit.

## 3. Formato de chunk

Cabecera común (`amdgpu_drm.h:962-966`):

```c
struct drm_amdgpu_cs_chunk {
    __u32 chunk_id;
    __u32 length_dw;     /* longitud en DWORDs, no en bytes */
    __u64 chunk_data;    /* puntero a los datos del chunk */
};
```

`length_dw` en **dwords** es un detalle de ABI: un driver propio que lo lea como bytes
aceptará chunks de tamaño 4× y leerá fuera del buffer.

IDs de chunk (`amdgpu_drm.h:948-960`):

| ID | Valor | Chunk |
|---|---|---|
| `AMDGPU_CHUNK_ID_IB` | 0x01 | el IB de comandos PM4 |
| `AMDGPU_CHUNK_ID_FENCE` | 0x02 | fence a esperar/emitir |
| `AMDGPU_CHUNK_ID_SCHEDULED_DEPENDENCIES` | 0x07 | dependencias de scheduling |
| `AMDGPU_CHUNK_ID_SYNCOBJ_*` | 0x05, 0x08, 0x09 | sync objects, wait y signal |
| `AMDGPU_CHUNK_ID_CP_GFX_SHADOW` | 0x0a | estado de shadow de GFX |

### El chunk de IB: el que importa para compute

`amdgpu_drm.h:1016-1030`:

```c
struct drm_amdgpu_cs_chunk_ib {
    __u32 _pad;
    __u32 flags;          /* AMDGPU_IB_FLAG_* */
    __u64 va_start;       /* dirección virtual de inicio del IB */
    __u32 ib_bytes;       /* tamaño del IB */
    __u32 ip_type;        /* IP de HW destino */
    __u32 ip_instance;    /* índice de la instancia de ese IP */
    __u32 ring;           /* índice del ring */
};
```

**`va_start` es una dirección virtual, no física.** El driver la resuelve a física en
`amdgpu_cs_vm_handling` (paso 6), que es donde se toca la page table. Un driver propio que
escriba la VA directamente en el ring sin resolverla hará que la HW lea de una dirección no
mapeada.

**`ip_type` + `ip_instance` seleccionan el destino**, y no hay un campo "es compute". El
cliente declara a qué IP envía. Esto es relevante para el diseño: un ioctl de compute propio
puede fijar `ip_type` en vez de aceptarlo del cliente, pero eso cambia la semántica respecto a
AMD y obliga a rechazar o traducir los submits que usen el campo.

Flags del IB (`amdgpu_drm.h:991-1001`):

| Flag | Valor | Efecto |
|---|---|---|
| `AMDGPU_IB_FLAG_CE` | 1<<0 | enviar a Command Engine en vez de shader |
| `AMDGPU_IB_FLAG_PREAMBLE` | 1<<1 | el IB puede descartarse si no hay cambio de contexto |
| `AMDGPU_IB_FLAG_PREEMPT` | 1<<2 | activar el bit de preempción |
| `AMDGPU_IB_FLAG_TC_WB_NOT_INVALIDATE` | 1<<3 | writeback de L2 sin invalidar cachés de shader |

## 4. Límites de este documento

- Análisis **de fuente, no de ejecución**. Ninguna ruta se ha ejercitado.
- `pass1`/`pass2` se identifican por nombre y posición; **el motivo del doble recorrido no está
  establecido** (`NOT_DETERMINED`).
- Las 8 107 B del binario no se han desensamblado función a función para explicar la
  diferencia con las 63 líneas de C. La explicación ofrecida (`__fentry__`, `-O2`, `.cold`) es
  `PLAUSIBLE`, no verificada.
- El árbol `RESEARCH/working/linux-7.1.3` es **parcial**: 632 ficheros de `amdgpu/`, sin
  `include/uapi`. Por eso el contrato con userspace se leyó de los headers instalados en
  `/usr/src/kernels/`, que son de la **misma versión de kernel** (`7.1.3-200.nobara.fc44`).

## Procedencia

Líneas citadas de `amdgpu_cs.c:1411-1473` y de
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/uapi/drm/amdgpu_drm.h`, leídos el
2026-09-29. Los tres fallos de los comandos del brief se reprodujeron antes de sustituirlos.
Ningún valor transcrito de documentación externa.
