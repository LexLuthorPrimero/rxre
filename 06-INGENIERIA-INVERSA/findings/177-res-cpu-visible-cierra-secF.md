# 177 · `amdgpu_res_cpu_visible` cierra §F: la ventana de 256 MiB se impone dos veces, y el fallo de CPU puede acabar en `SIGBUS`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=el UNLOCK de 169 ("con eso secF queda cerrado por completo")`

## Cuestión principal

`169` dejó esto:

> *Siguiente paso: `amdgpu_res_cpu_visible()` aparece en cuatro de los cinco
> sitios. Es el otro predicado, y determina qué BOs están sujetos al
> presupuesto. Con eso, §F queda cerrado por completo.*

## Criterio de terminación

Definir exactamente qué significa "accesible desde la CPU" en este driver, y
enumerar las consecuencias cuando no lo es. **Cumplido.**

## La definición completa

`amdgpu_ttm.c:455-478`:

```c
bool amdgpu_res_cpu_visible(struct amdgpu_device *adev, struct ttm_resource *res)
{
        if (!res)
                return false;

        if (res->mem_type == TTM_PL_SYSTEM || res->mem_type == TTM_PL_TT ||
            res->mem_type == AMDGPU_PL_PREEMPT || res->mem_type == AMDGPU_PL_DOORBELL ||
            res->mem_type == AMDGPU_PL_MMIO_REMAP)
                return true;

        if (res->mem_type != TTM_PL_VRAM)
                return false;

        amdgpu_res_first(res, 0, res->size, &cursor);
        while (cursor.remaining) {
                if ((cursor.start + cursor.size) > adev->gmc.visible_vram_size)
                        return false;
                amdgpu_res_next(&cursor, cursor.size);
        }
        return true;
}
```

Tres clases, y la tercera es la que importa:

1. **`true` por `mem_type`**, sin mirar el sitio: `TTM_PL_SYSTEM`, `TTM_PL_TT`,
   `AMDGPU_PL_PREEMPT`, `AMDGPU_PL_DOORBELL`, `AMDGPU_PL_MMIO_REMAP`. Son RAM de
   sistema o aperturas MMIO, que la CPU ve por definición.
2. **`false`** si no es VRAM y no está en la lista anterior.
3. **VRAM: comprobación por segmento.** Recorre el cursor del recurso y exige
   que **cada** segmento cumpla `start + size <= visible_vram_size`.

O sea: **un BO es CPU-visible si, y solo si, está íntegramente dentro de la
ventana del BAR.** Una sola página fuera basta para que el BO entero deje de
ser visible.

## Los cinco mem_types de la lista "siempre true" están vivos aquí

Comprobé que no son nombres muertos:

- `TTM_PL_SYSTEM`, `TTM_PL_TT`: los usa la TTM de siempre.
- `AMDGPU_PL_PREEMPT`: **`amdgpu_preempt_mgr_init()` se llama desde
  `amdgpu_ttm.c:2195` sin condición**, así que el manager está registrado en
  esta placa.
- `AMDGPU_PL_DOORBELL`: las BOs de doorbell de KFD.
- `AMDGPU_PL_MMIO_REMAP`: `amdgpu_ttm_alloc_mmio_remap_bo()` en
  `amdgpu_ttm.c:2190`, y `169` ya cerró que su placement es
  `num_placement = 0`, o sea "nunca desconectable".

Ninguno de los cinco es una rama muerta en GFX8.

## La ventana se impone **dos veces**, y eso es defensa en profundidad

| | dónde | qué hace |
|---|---|---|
| **colocación** | `amdgpu_ttm.c:148` (`169`) | `placements[0].fpfn = visible_vram_size >> PAGE_SHIFT` — el BO **empieza** dentro de la ventana |
| **consulta** | `amdgpu_res_cpu_visible()` | el BO es visible si **todo** cabe dentro de la ventana |

La primera pone el techo; la segunda lo comprueba. Un driver propio necesita las
dos, y si implementa solo la primera acaba con BOs que empiezan dentro pero
crecen fuera.

**El número, de `169`:** `fpfn = 65536` páginas, con `visible_vram_size` =
256 MiB medido por `lspci`.

## La consecuencia runtime: `SIGBUS`

`amdgpu_object.c:1358-1387`, el manejador de "la CPU tocó un BO de VRAM":

```c
/* Remember that this BO was accessed by the CPU */
abo->flags |= AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED;

if (amdgpu_res_cpu_visible(adev, bo->resource))
        return 0;                       /* ya visible: nada que hacer */

/* Can't move a pinned BO to visible VRAM */
if (abo->tbo.pin_count > 0)
        return VM_FAULT_SIGBUS;          /* <-- SIGBUS al proceso */

/* hurrah the memory is not visible ! */
atomic64_inc(&adev->num_vram_cpu_page_faults);
amdgpu_bo_placement_from_domain(abo, AMDGPU_GEM_DOMAIN_VRAM | AMDGPU_GEM_DOMAIN_GTT);
abo->placements[0].flags |= TTM_PL_FLAG_DESIRED;

r = ttm_bo_validate(bo, &abo->placement, &ctx);
if (unlikely(r == -EBUSY || r == -ERESTARTSYS))
        return VM_FAULT_NOPAGE;          /* reintentar luego */
else if (unlikely(r))
        return VM_FAULT_SIGBUS;

/* this should never happen */
if (bo->resource->mem_type == TTM_PL_VRAM &&
    !amdgpu_res_cpu_visible(adev, bo->resource))
        return VM_FAULT_SIGBUS;
```

**Cuatro salidas, y dos son `SIGBUS` al proceso de usuario.** Con un BAR de
256 MiB sobre VRAM de 2 GiB, la probabilidad de tocar fuera de la ventana no es
teórica: es la mitad del espacio de direcciones.

Los tres caminos posibles cuando la página no es visible:

| condición | resultado |
|---|---|
| ya visible | `return 0` |
| BO pinneado | **`VM_FAULT_SIGBUS`** |
| la mudanza da `-EBUSY` | `VM_FAULT_NOPAGE` (reintento) |
| la mudanza falla de otro modo | **`VM_FAULT_SIGBUS`** |
| sigue no visible después | **`VM_FAULT_SIGBUS`** |

El comentario del propio driver en el último caso —*"this should never happen"*—
es una afirmación sobre su propia invariante, y la invariante depende
exactamente de que `fpfn` se cumpla.

## El contador existe, pero no se puede leer con lo que hay

`atomic64_inc(&adev->num_vram_cpu_page_faults)` y, junto a él, la familia
completa de `169`:

```
amdgpu_kms.c:793   AMDGPU_INFO_NUM_BYTES_MOVED
amdgpu_kms.c:796   AMDGPU_INFO_NUM_EVICTIONS
amdgpu_kms.c:799   AMDGPU_INFO_NUM_VRAM_CPU_PAGE_FAULTS
amdgpu_kms.c:802   AMDGPU_INFO_VRAM_USAGE
amdgpu_kms.c:805   AMDGPU_INFO_VIS_VRAM_USAGE
```

**Seis contadores que observarían directamente todo §F.** Y son ioctls, no
atributos de sysfs: no hay entrada en `/sys` para ninguno
(`find /sys -name "*vram_cpu_page_faults*"` → vacío).

### Por qué no puedo leerlos

```
$ find /usr/include /lib/modules -name drm_amdgpu.h   -> nada
$ find RESEARCH -name drm_amdgpu.h -o -name amd_drm.h  -> nada
```

**`include/uapi/drm/` no existe en este snapshot.** `linux-7.1.3/` contiene
solo `Documentation/`, `drivers/` e `include/`, y `include/` solo `linux/`. Es
una reducción deliberada del árbol.

Sin ese header no tengo el valor numérico de `AMDGPU_INFO_NUM_VRAM_CPU_PAGE_FAULTS`
ni el de `DRM_IOCTL_AMDGPU_INFO`, y **construir el ioctl asumiendo el layout
sería exactamente lo que `AGENTS.md` prohíbe**: *implementar una semántica solo
porque existe en AMDGPU*. El ioctl malcodificado no da error: mueve memoria de
otro sitio.

También miré si el número se podía recuperar del `.ko` cargado, como se hizo con
la tabla de ASIC en `052`. La tabla de descriptores DRM (`amdgpu_drm_ioctl_desc`)
**no está en este `amdgpu_kms.c`**, así que esa vía tampoco está.

### El artefacto que falta, nombrado

```
include/uapi/drm/drm_amdgpu.h    (y su dependencia drm_drm.h)
```

**Un solo fichero.** Con él, §F pasa de `DERIVATION` a `OBSERVED` en seis
mediciones, sin tocar la placa.

## Clasificación

| afirmación | estado |
|---|---|
| CPU-visible ⇔ íntegramente dentro de `visible_vram_size` | `PROVEN` — `amdgpu_ttm.c:471` |
| Cinco `mem_type` son visibles sin comprobar sitio | `PROVEN` — `:462-464` |
| `AMDGPU_PL_PREEMPT` está registrado en esta placa | `PROVEN` — `amdgpu_ttm.c:2195` |
| La ventana se impone en colocación y en consulta | `PROVEN` — dos sitios |
| Un BO pinneado fuera de la ventana da `SIGBUS` | `PROVEN` — `amdgpu_object.c:1367` |
| `-EBUSY` da reintento, no `SIGBUS` | `PROVEN` — `:1380` |
| Seis contadores de §F existen vía ioctl | `PROVEN` — `amdgpu_kms.c:793-805` |
| No hay atributo sysfs para ellos | `PROVEN_ABSENT` |
| `include/uapi/drm/` ausente del snapshot | `PROVEN_ABSENT` |
| Que los contadores valgan >0 en esta placa | `NOT_DETERMINED` — falta el header |
| Que la probabilidad de `SIGBUS` sea alta | `HYPOTHESIS` — no medida |

## Confounders

- **No he seguido `amdgpu_res_cursor`**: el recorrido por segmentos puede tener
  casos límite que no he leído (`amdgpu_res_first` con `res->size`). El
  predicado está bien leído; su implementación de cursor, no.
- **`VM_FAULT_SIGBUS` no es necesariamente un `SIGBUS` del proceso**: es un
  código de retorno de la función de fault. No he seguido el camino hasta el
  `kill()`. Lo digo porque "el driver devuelve SIGBUS" y "el proceso recibe
  SIGBUS" no son la misma afirmación.
- **Los seis ioctls no los he podido construir**, así que su numeración es
  `NOT_DETERMINED` desde la evidencia disponible.
- **`AMDGPU_PL_PREEMPT` registrado no significa preemption activa**: el manager
  se inicializa, pero que haya memoria preemptible reservada es otra cosa.
- **Solo lectura estática.** No he ejecutado ningún ioctl.

## Desfalsificación

- **(a)** El predicado → refutable con `amdgpu_ttm.c:455-478`.
- **(b)** PREEMPT registrado → refutable con `amdgpu_ttm.c:2195`.
- **(c)** `SIGBUS` en BO pinneado → refutable con `amdgpu_object.c:1366-1368`.
- **(d)** Sin sysfs → refutable con `find /sys -name "*vram_cpu_page_faults*"`.
- **(e)** El header ausente → refutable con `find RESEARCH -name drm_amdgpu.h`.
- **(f)** Que los contadores valgan >0 → **no refutable aquí**: falta el header.

## UNLOCKS

- **§F queda cerrado** en su parte estática: qué significa CPU-visible, dónde se
  impone, y qué pasa cuando falla.
- **La invariante del driver, enunciada**: para que un BO sea visible, su `fpfn`
  debe ser ≤ `visible_vram_size >> 12` **y** su tamaño completo debe caber.
  Omitir cualquiera de las dos rompe.
- **La ruta empírica está bloqueada por un artefacto concreto y nombrado**:
  `include/uapi/drm/drm_amdgpu.h`. Es la clase de bloqueo mejor: no "no se
  puede", sino "falta exactamente este fichero y esto se mide con él".
- **Los seis contadores cubren §F entero**: bytes movidos, evictions, faults de
  CPU, uso de VRAM, uso de VRAM visible, uso de GTT.
- **Siguiente paso**: §G. La coherencia ya tiene su flush (`156`) y suwriter
  (`163`). Falta el lado del hardware: qué garantiza el orden entre el invalidate
  de `0x51e` y una lectura de la tabla. Y hay un candidato nuevo sin explorar:
  `concurrent_flush`, que `163` dejó como condición no seguida.

## Evidencia

```
amdgpu_ttm.c:455-478   amdgpu_res_cpu_visible, tres clases
amdgpu_ttm.c:462-464   SYSTEM, TT, PREEMPT, DOORBELL, MMIO_REMAP -> true
amdgpu_ttm.c:471       (start + size) > visible_vram_size -> false
amdgpu_ttm.c:148       placements[0].fpfn = visible_vram_size >> PAGE_SHIFT
amdgpu_ttm.c:2195      amdgpu_preempt_mgr_init(adev), sin condicion
amdgpu_object.c:1360   AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED
amdgpu_object.c:1367   pin_count > 0 -> VM_FAULT_SIGBUS
amdgpu_object.c:1371   atomic64_inc(&num_vram_cpu_page_faults)
amdgpu_object.c:1380   -EBUSY -> VM_FAULT_NOPAGE
amdgpu_object.c:1385   "this should never happen" -> VM_FAULT_SIGBUS

amdgpu_kms.c:793-805   6 contadores via ioctl
$ find /sys -name "*vram_cpu_page_faults*"   -> vacio
$ find RESEARCH -name drm_amdgpu.h            -> vacio
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
