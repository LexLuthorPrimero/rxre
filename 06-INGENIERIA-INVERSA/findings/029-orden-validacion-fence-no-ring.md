# 029 · La garantía de orden de la invalidación no está en el ring: está en `dma_fence_is_signaled`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `CONTINUES=017, 018`

## CUDA principal

La pregunta abierta desde `018 §4` —*¿qué garantiza que el siguiente IB no vea la TLB
vieja?*— tiene respuesta, y no es la que suponía.

**El ring no garantiza nada intra-envío. La serialización es cross-submission y la hace el
CPU, con una consulta a un fence.** Y en GFX8 hay un refuerzo adicional: `concurrent_flush`
es `false`, así que un VMID que necesite flush **no se reutiliza**.

Eso no invalida `017` ni `018`: los confirma. El hardware no ofrece completion, y el software
no la pide intra-envío; la resuelve fuera del ring.

## Corrección previa

En el cierre de `025` escribí que `amdgpu_fence_emit` *"emite un fence con `FUNCTION(3)` y
`mask=0xffffffff`, que sí compara"*. **Falso.** Confunde dos emisores distintos:

- `gfx_v8_0_ring_emit_fence_gfx` (`:6141-6172`) emite **dos** `EVENT_WRITE_EOP` con
  `CACHE_FLUSH_AND_INV_TS_EVENT`. Escribe `seq` en memoria. **No espera nada.**
- `gfx_v8_0_ring_emit_pipeline_sync` (`:6174-6194`) es el que emite
  `WAIT_REG_MEM` con `FUNCTION(3)` y `mask=0xffffffff`. **Sí compara.**

Y `pipeline_sync` se emite en la pierna 2 de la ruta, **antes** del invalidate (pierna 3).
No puede ordenar la invalidación contra el IB que viene después: ocurre antes.

## Alcance exacto

1. Localizar el mecanismo que decide si un envío invalida o no.
2. Determinar qué lo fuerza.
3. Separar la garantía intra-envío de la cross-submission.
4. Clasificar el punto abierto de `018:141`.

## Criterio de terminación (cumplido)

La cadena desde `tlb_seq` hasta `job->vm_needs_flush` está cerrada y leída entera.

---

## 1 · La cadena completa

### 1.1 · El número de secuencia se incrementa cuando el fence señala

```c
/* amdgpu_vm.c:1052-1071, amdgpu_vm_tlb_flush */
if (!dma_fence_add_callback(*fence, &tlb_cb->cb, amdgpu_vm_tlb_seq_cb)) {
        dma_fence_put(vm->last_tlb_flush);
        vm->last_tlb_flush = dma_fence_get(*fence);
} else {
        amdgpu_vm_tlb_seq_cb(NULL, &tlb_cb->cb);
}
```

`atomic64_inc(&vm->tlb_seq)` ocurre **en el callback del fence**, es decir cuando la GPU
ha terminado el trabajo, no cuando el driver lo escribió. `PROVEN` por lectura.

### 1.2 · El envío siguiente decide con una consulta al fence

```c
/* amdgpu_ids.c:347-353, amdgpu_vmid_grab_used */
if (!(*id)->last_flush ||
    ((*id)->last_flush->context != fence_context &&
     !dma_fence_is_signaled((*id)->last_flush)))
        needs_flush = true;

if ((*id)->flushed_updates < updates)
        needs_flush = true;
```

`dma_fence_is_signaled((*id)->last_flush)` es la condición. Si el flush anterior **no ha
señalado**, `needs_flush` es `true` y este envío invalida también.

### 1.3 · `id->last_flush` es el fence emitido después del invalidate

```c
/* amdgpu_vm.c:861-873 */
amdgpu_fence_emit(ring, job->hw_vm_fence, 0);
fence = &job->hw_vm_fence->base;
...
if (vm_flush_needed) {
        id->last_flush = dma_fence_get(fence);
        id->current_gpu_reset_count = atomic_read(&adev->gpu_reset_counter);
}
```

Y ese fence es el `EVENT_WRITE_EOP` de la pierna 7. Los dos EOP events llevan
`EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN` y
`CACHE_FLUSH_AND_INV_TS_EVENT`: el evento recorre **el pipeline completo** antes de escribir
el contador.

## 2 · El refuerzo específico de GFX8: no reutilizar un VMID sucio

```c
/* amdgpu_vm.c:2842-2843 */
adev->vm_manager.concurrent_flush = !(adev->asic_type < CHIP_VEGA10 ||
                                      adev->asic_type == CHIP_NAVI10 ||
                                      adev->asic_type == CHIP_NAVI14);
```

`CHIP_POLARIS12` (índice 17 en `amd_asic_type.h`) es `< CHIP_VEGA10` (índice 19), luego
`concurrent_flush = false`. Consecuencia en `amdgpu_ids.c:355`:

```c
if (needs_flush && !adev->vm_manager.concurrent_flush)
        continue;      /* este VMID no sirve; busca otro o pide uno nuevo */
```

**GFX8 no reutiliza un VMID cuyo flush no ha completado.** O encuentra otro VMID ya
limpiado, o `amdgpu_vmid_grab_id` asigna uno nuevo con `job->vm_needs_flush = true`
(`amdgpu_ids.c:420`).

El comentario de arriba (`amdgpu_vm.c:2840-2841`) dice que el flush concurrente *"are broken
on Navi10 and Navi14"*. GFX8 está excluido por la otra rama, la del silicio previo a Vega.

## 3 · La separación que faltaba

| | qué lo garantiza | estado |
|---|---|---|
| **Intra-envío**: el IB de este envío ve la invalidación que este mismo envío emite | **nada explícito** | `NOT_DETERMINED` |
| **Cross-submission**: el envío N+1 no salta la invalidación hasta que la de N ha completado | `dma_fence_is_signaled(id->last_flush)` | `PROVEN` |
| **Cross-submission**, GFX8 específicamente | `concurrent_flush = false` fuerza VMID distinto | `PROVEN` |

El punto que queda abierto es el primero, y es el correcto: **dentro de un envío, el
invalidate es un `WRITE_DATA` con `WRITE_DATA_ENGINE_SEL(1)` — lo ejecuta el PFP — y el IB
siguiente lo descodifica el mismo PFP, en orden de paquetes.** Que eso baste depende de que
el hardware ejecute el write antes de que el IB dispare sus accesos a memoria. Es
`PROVEN_DERIVED` a partir del orden de emisión, y **`NOT_DETERMINED` a nivel de hardware**.

El propio driver muestra que lo considera suficiente: emite el invalidate y sigue con el IB
sin ninguna espera entre medias. Eso es `CORROBORATED` —el driver de referencia depende de
esa suposición para funcionar—, no `PROVEN`. La diferencia importa: un driver propio puede
replicar la suposición, pero debería saber que está replicando una suposición.

## 4 · Qué cambia respecto a `018`

`018 §4` decía: *"la seguridad del path depende enteramente de un invariante del propio
ring, no de un handshake con el hardware"*. **Era falso, y en la dirección contraria a la
que sospechaba.** No depende del ring: depende del **scheduling**, y el scheduling lo hace
el driver con una consulta a un fence que el hardware sí señala.

Eso no debilita `018`: refuerza su hallazgo central. El hardware no ofrece un registro de
completion de invalidación (`PROVEN_ABSENT`, cinco cabeceras GMC sin uno), y por eso el
driver **no puede** hacer la espera en el ring. La respuesta del driver fue mover la
espera un nivel más arriba, al punto donde sí puede hacerse: "¿puedo_skip la invalidación?",
que es una pregunta al fence, no un `WAIT_REG_MEM`.

Es un diseño mejor que el que yo había supuesto, y es `MODEL_CHOICE`: si un driver propio
quiere completion *intra-envío*, tiene que aportarla él, porque el hardware no da el
registro. Y si acepta el diseño del driver de referencia, hereda su garantía cross-submission
que **sí** es sólida y verificable.

## 5 · UNLOCKS

- La serialización de invalidación en GFX8 es un mecanismo de **dos capas**: fence
  consultado por el CPU, y no-reutilización de VMID. Ninguna de las dos está en el ring.
- `concurrent_flush = false` es un requisito hardware que el driver propio debe respetar o
  reimplementar: sin él, un VMID con flush pendiente puede recibir trabajo.
- `DMA_FENCE` es la abstracción que hace de completion barrier. Para un driver propio sin
  fences, esto es lo que hay que reconstruir.

## 6 · Criterio de falsación

Se refutaría si: (a) `dma_fence_is_signaled(id->last_flush)` resultara ser siempre `true`
en la ruta GFX8, lo que vaciaría la condición; (b) `concurrent_flush` resultara `true` para
`CHIP_POLARIS12`; (c) existiera entre el invalidate y el IB un paquete que la
documentación mostrara bloqueante y que yo no he visto. Ninguno se sostiene contra la
lectura. (c) es `NOT_DETERMINED` por definición — requiere la spec PM4 de GFX8, no el
corpus— y queda `PROVISIONAL`.

## 7 · Evidencia

```
gfx_v8_0.c:      6141-6172 (emit_fence_gfx: dos EOP, no espera),
                 6174-6194 (emit_pipeline_sync: WAIT_REG_MEM FUNCTION(3), sí espera)
amdgpu_vm.c:     772-898 (ruta), 861-873 (last_flush = el fence emitido),
                 1015-1071 (tlb_seq se incrementa en el callback del fence),
                 2593 (need_tlb_fence = amdgpu_userq_enabled)
amdgpu_ids.c:    290-310 (grab_id), 322-369 (grab_used),
                 347-353 (la consulta al fence), 355-356 (concurrent_flush gate),
                 412-431 (VMID nuevo => vm_needs_flush)
amdgpu_vm.c:     2840-2843 (concurrent_flush; "are broken on Navi10 and Navi14")
amd_asic_type.h: CHIP_POLARIS12 = 17 < CHIP_VEGA10 = 19  (orden de la enum)
```

`TEMPORALITY`: `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`, `HOST_SCOPE=n/a` — statements
sobre el driver de referencia, no sobre un host. Ningún registro leído de MMIO.
`RUNTIME=NOT_RUN`. `MODIFICATIONS=0`.