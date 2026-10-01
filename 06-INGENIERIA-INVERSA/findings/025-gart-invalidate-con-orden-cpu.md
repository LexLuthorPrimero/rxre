# 025 · La ruta GART: donde el invalidate sí tiene completion observable

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

`017`, `018` y `022` cerraron que **el path de ring** no puede dar completion del
invalidate: no hay ack, y las dos primitivas de espera disponibles estan inertes. Ese
veredicto es correcto y esta bien acotado -- es del path de ring.

Hay un **segundo path de invalidate** en el mismo ASIC, y este sí tiene completion
observable, porque **lo ejecuta la CPU y no el ring**:

```
amdgpu_gart_invalidate_tlb()                    [amdgpu_gart.c:492-505]
  if (!adev->gart.ptr) return;                 <- guarda real
  mb();                                        <- orden de escritura
  amdgpu_device_flush_hdp(adev, NULL);
  for_each vmhub: amdgpu_gmc_flush_gpu_tlb(adev, vmid=0, ...)
        -> gmc_v8_0_flush_gpu_tlb: WREG32(0x51e, 1<<0)
```

`flush_hdp` y el retorno son **sincronos con la funcion que los emite**: cuando
`amdgpu_gart_invalidate_tlb()` vuelve, la escritura del registro ya salio. Esa es una
forma de completion que el path de ring no tiene, y no requiere ningun hardware nuevo.

## Alcance exacto

1. Seguir la cadena `amdgpu_ttm_alloc_gart` hasta el invalidate, capa por capa.
2. Determinar quien lo invoca y con que frecuencia.
3. Comparar su semantica de orden con la del path de ring.
4. Clasificar si el driver propio puede aprovecharlo.

## Criterio de terminacion (cumplido)

La cadena desde el bind de un BO hasta el invalidate esta cerrada, y el CALLERS esta
contado por clase. Agotado.

---

## 1 · La cadena completa del bind

`amdgpu_ttm_alloc_gart` (`amdgpu_ttm.c:970-1008`) es el punto de entrada para hacer
un BO accesible en el espacio de direcciones del device:

```
1. if (bo->resource->start != AMDGPU_BO_INVALID_OFFSET) return 0;   ya tenia sitio
2. addr = amdgpu_gmc_agp_addr(bo);  si != INVALID -> return 0        AGP ya lo cubria
3. placement.lpfn = adev->gmc.gart_size >> PAGE_SHIFT             del rango del GART
4. ttm_bo_mem_space(...)                                             reserva paginas
5. flags = amdgpu_ttm_tt_pte_flags(...)                              flags de la pagina
6. gtt->offset = (u64)tmp->start << PAGE_SHIFT                      offset en el GART
7. amdgpu_ttm_gart_bind(adev, bo, flags)                            ESCRIBE LOS PTEs
8. amdgpu_gart_invalidate_tlb(adev)                                  INVALIDA
9. ttm_resource_free + ttm_bo_assign_mem                            reasigna el BO
```

Paso 7 (`amdgpu_ttm.c:876-895`) escribe los PTE con `amdgpu_gart_bind`, que llama a
`amdgpu_gmc_set_pte_pde(adev, adev->gart.ptr, t, page_base, flags)` sobre
`adev->gart.ptr` — que es `page_to_virt(p)`, una **direccion de CPU** (`amdgpu_gart.c:200`).

Ese detalle es el que Ordena toda la capa: **el page table del GART se escribe desde
la CPU** (`017` ya lo establecia: "la tabla la escribe la CPU"), y
`PAGE_TABLE_BASE_ADDR` recibe la direccion **GPU** del mismo BO
(`amdgpu_bo_gpu_offset(adev->gart.bo)`, `gmc_v8_0.c`). Las dos cosas son el mismo
objeto visto desde dos direcciones, y por eso el paso 8 puede ser una escritura de
registro normal: no hay hardware esperando nada.

## 2 · Por que este invalidate SI tiene completion

Contraste con el path de ring, que es donde `017`/`018`/`022` han medido:

| | path de ring | path GART (este) |
|---|---|---|
| quien ejecuta | CP, asincrono | **la propia funcion, en la CPU** |
| hay que esperar a algo | si, y no se puede | **no: es secuencial** |
| `mb()` / `flush_hdp` | no | **si, antes del invalidate** |
| donde aparece completion | ninguna | **el retorno de la funcion** |
| quien fija el orden | el hardware | **el procesador** |

`mb()` antes de `flush_hdp`, y `flush_hdp` antes del `WREG32`, es la forma en que la
CPU se asegura de que el PTE este visible antes de que el hardware lo use. Es el
mismo requisito de coherencia que `017` describe para el ring,
resuelto aqui por el hecho de que el escritor y el consumidor estan en el mismo hilo.

`HYPOTHESIS`, marcada: que `mb()` + `flush_hdp` basten para que el invalidate vea el
PTE recien escrito. Es la coherencia de la CPU y de la MMIO del host, y es `PROVEN` que
el codigo emite esa secuencia; que el hardware la interprete asi en esta placa concreta
no esta probado. `NOT_DETERMINED` para el efecto, `PROVEN` para la secuencia.

## 3 · Quien lo invoca, y por que importa la frecuencia

12 ficheros del arbol llaman a `amdgpu_ttm_alloc_gart`:

```
amdgpu_gart.c:202       creacion de la tabla GART (una vez, en el init)
amdgpu_object.c:285,402 cualquier BO que se pinne en el GART
amdgpu_cs.c:971, 1816   BOs de userspace
amdgpu_display.c:246    BOs de display
amdgpu_vm_sdma.c:38     tablas de page table creadas por SDMA
amdgpu_amdkfd.c:390, amdgpu_amdkfd_gpuvm.c:2248  BOs de KFD
mes_userqueue.c:81, amdgpu_vkms.c:348
```

**Cada pin de un BO en el GART paga un invalidate sincrono del TLB entero de VMID 0.**
Ese es el coste, y es el lugar donde el modelo plano del que habla `024` se nota: con
`num_level = 1` no hay walkers que invalidar parcialmente, asi que un unico bit cubre
toda la tabla.

`PROVEN` el recuento de call sites. `NOT_DETERMINED` cuanto_freq, con una
consecuencia concreta: `ttm_bo_mem_space` ya invalida, y el TLB se vacia entero en cada
bind. Es la razon por la que el camino de ring **necesita** invalidacion explicita: si
el bind ya lo hizo, la invalidacion por ring cubre el caso de *cambio de PTBA*, no el
de *contenido recien escrito*.

Esa distincion no estaba en los hallazgos previos y es la que separa dos problemas que
`017` tratava como uno.

## 3bis · Por que el invalidate de ring no se dispara en esta host

Cadena completa, verificada con lecturas de sysfs de esta host (sin privilegio, sin
RUNTIME):

```
1. /sys/module/amdgpu/parameters/vm_update_mode          = -1   (sin forzar)
2. amdgpu_vm_update_mode == -1  ->  rama automatica     [amdgpu_vm.c:2885]
3. amdgpu_gmc_vram_full_visible()  =  (real_vram_size == visible_vram_size)
4.   visible_vram_size = aper_size = pci_resource_len(pdev, 0)   [gmc_v8_0.c:576,585]
5.   BAR0 = 256 MiB  vs  VRAM = 2 GiB  ->  NO full visible
6. -> vm_manager.vm_update_mode = 0                  [amdgpu_vm.c:2894]
7. -> use_cpu_for_update = !!(0 & USE_CPU_FOR_GFX) = false   [amdgpu_vm.c:2626]
8. -> job->vm_needs_flush = false                    [amdgpu_ids.c:334]
9. -> amdgpu_ring_emit_vm_flush() NO se emite en esta ruta
```

Medidas en esta host:

```
/sys/bus/pci/devices/0000:01:00.0/resource0   st_size = 268435456 = 256 MiB
/sys/class/drm/card*/device/mem_info_vram_total          = 2147483648 = 2 GiB
/sys/module/amdgpu/parameters/vm_update_mode             = -1
```

`PROVEN` en los tres datos, `PROVEN_DERIVED` en la cadena. Y confirma el estado ya
establecido en `AGENTS.md` ("politica efectiva = vm_update_mode = 0", "BAR/full-visible
= FALSE"), ahora con la cadena que lleva de uno al otro y con las medidas que la
sostienen, leidas sin privilegio.

Corolario para el driver propio: **en esta configuracion el path de invalidate de ring
no se ejecuta**. Todo lo que `017`, `018`, `020`, `021` y `022` midieron sobre el es
codigo presente pero no ejecutado en esta placa. Sigue siendo el codigo que un driver
propio necesita para cuando el usuario page table lo escriba el usuario —pero el
reproductor de referencia no lo ejercita aqui.

Eso **no** invalida esos hallazgos: son `PROVEN` sobre el codigo. Lo que cambia es su
relevancia: describen una ruta no tomada en esta host, y hay que decirlo para no
presentarlos como comportamiento observado de la RX550.

## 4 · Lo que esto NO resuelve

Este hallazgo **no da completion al path de ring**. Son dos problemas distintos:

- El bind de un BO: problema de CPU, resuelto por `mb()` + `flush_hdp`. Cerrado.
- El cambio de `PTBA` desde el ring: problema de hardware, sin ack. `NOT_IMPLEMENTABLE`
  segun `018`.

Confundirlos seria el error facil aqui, y seria un error grave porque el segundo no
tiene arreglo con lo que hay. `CONTRADICTION` no: son afirmaciones sobre objetos
distintos y ambas son correctas.

## 5 · Clasificacion

| Afirmacion | Estado |
|---|---|
| `amdgpu_ttm_alloc_gart` escribe PTEs y luego invalida, en ese orden | `PROVEN` (fuente, `amdgpu_ttm.c:996-997`) |
| El page table del GART se escribe desde la CPU (`gart.ptr` es CPU) | `PROVEN` (`page_to_virt`, `amdgpu_gart.c:200`) |
| `PAGE_TABLE_BASE_ADDR` recibe la direccion GPU del mismo BO | `PROVEN` (`amdgpu_bo_gpu_offset`) |
| El invalidate emite `mb()` y `flush_hdp` antes del `WREG32` | `PROVEN` (`amdgpu_gart.c:499-504`) |
| Ese path tiene completion por synchronous execution | `PROVEN_DERIVED` |
| Que `mb()`+`flush_hdp` basten para esta placa | `NOT_DETERMINED` (efecto hardware) |
| 12 ficheros llaman a `amdgpu_ttm_alloc_gart` | `PROVEN` (call sites) |
| Con que frecuencia, en esta carga de trabajo | `NOT_DETERMINED` — requiere medicion |
| Que el invalidate de ring se dispare solo por cambio de PTBA | `REFUTED` — se dispara por `use_cpu_for_update` (§3bis) |
| En esta host `vm_needs_flush` nunca es true | `PROVEN_DERIVED` (§3bis) |

Ultima fila necesita una correccion: mi primera redaccion decia que el invalidate de
ring cubre "solo el cambio de PTBA". **Incorrecto**, y el corpus lo contradice en una
linea. La condicion que lo dispara es `vm_needs_flush`, y su productor real es
`vm->use_cpu_for_update`:

```
amdgpu_ids.c:334    job->vm_needs_flush = vm->use_cpu_for_update;
amdgpu_vm.c:2626    vm->use_cpu_for_update = !!(vm_update_mode & AMDGPU_VM_USE_CPU_FOR_GFX);
```

O sea: el invalidate de ring se dispara precisamente **cuando la tabla la escribe la
CPU** — es el caso del GART de `§1`, no el cambio de PTBA. Y en esta host no se
dispara nunca, por la cadena de `§3bis`.

Lo que si queda en pie de la version previa: `flush_gpu_tlb` cubre el bind por CPU, luego
el invalidate de ring cubre **un caso distinto**. Mi error fue *cual*; la distincion de
los dos problemas era correcta.

## 6 · Confounders

- El recuento de call sites es de **arbol**, no de runtime. Un BO puede fijarse mas de
  una vez (reserva, pin, unpin) y eso no se ve leyendo.
- `amdgpu_gmc_flush_gpu_tlb(adev, 0, i, 0)` itera `vmhubs_mask`, que en GFX8 tiene un
  solo hub. El bucle es de codigo, no de comportamiento en esta placa.
- La coherencia de la CPU no es la coherencia del GART: `mb()` ordena la vista de la
  CPU, no garantiza que la MMIO del dispositivo la vea sin `flush_hdp`. Por eso estan
  los dos, y por eso la `HYPOTHESIS` de arriba es sobre el par, no sobre `mb()` solo.

## 7 · UNLOCKS

- El driver propio tiene un **patron de invalidate correcto ya establecido** para la
  parte de CPU: escribir PTE, `mb()`, `flush_hdp`, invalidar. Es copiable como
  `MODEL_CHOICE` con la garantia que ofrece y sin prometer la que no.
- El invalidate de ring queda **reencuadrado**: se dispara cuando la tabla la escribe
  la CPU (`use_cpu_for_update`), y en esta host **no se dispara nunca** (§3bis). Separar
  eso de "el invalidate de ring cubre el cambio de PTBA" es la correccion que este
  documento se hace a si mismo.
- `017`, `018`, `020`, `021` y `022` miden codigo de una ruta que **esta host no
  ejercita**. No quedan refutados — son `PROVEN` sobre el fuente — pero su relevancia
  cambia y ahora se dice explicitamente en lugar de presentarlos como comportamiento
  de la RX550.
- Los 12 call sites son el mapa de donde el driver propio necesita decidir si invalida.
  Es la lista de lugares donde un fallo de coherencia seria silencioso.

## 8 · Criterio de falsificacion

Se refutaria si: (a) `mb()`+`flush_hdp` no bastaran y el PTE recien escrito no fuera
visible para el invalidate, lo que haria este path tan invalido como el de ring —
discriminante runtime: escribir un PTE, invalidar, y leer a traves de el GART sin
intervencion; (b) `amdgpu_gmc_flush_gpu_tlb(adev, 0, ...)` no se ejecutara por el
`trylock` fallido en `reset_domain->sem` durante un reset, dejando la invalidacion sin
hacer — `PROVEN` por codigo que el `trylock` puede fallar en silencio; (c) la lectura
de PTE por el hardware no pasara por la L2 que hay que invalidar. (a) y (c) exigen
RUNTIME; (b) es `PROVEN` que **no** hay garantia durante un reset, y queda registrado
como `LIMITATION` del patron.

## 9 · Evidencia

```
amdgpu_ids.c:     334 (vm_needs_flush = use_cpu_for_update), 307, 420
amdgpu_vm.c:      2626 (use_cpu_for_update), 2885-2898 (vm_update_mode auto),
                  2349-2369 (get_block_size), 2379-2465 (adjust_size)
amdgpu_gmc.h:     394 (vram_full_visible = real == visible)
gmc_v8_0.c:       576 (aper_size = pci_resource_len), 585 (visible = aper)
host: /sys/.../resource0 st_size = 268435456        (256 MiB)
      /sys/class/drm/card*/mem_info_vram_total       (2 GiB)
      /sys/module/amdgpu/parameters/vm_update_mode   (-1)

amdgpu_gart.c:    200 (gart.ptr = page_to_virt), 331-370 (gart_map escribe PTE),
                  492-505 (invalidate_tlb: mb, flush_hdp, flush_gpu_tlb vmid 0)
amdgpu_ttm.c:     876-895 (gart_bind), 970-1008 (alloc_gart completo)
gmc_v8_0.c:       655-666 (flush_gpu_tlb -> WREG32 0x51e, 1<<vmid), 668-681 (emit_flush)
                  gart_enable (PAGE_TABLE_BASE_ADDR = bo_gpu_offset)
callers de ttm_alloc_gart: 12 ficheros (lista en §3)
```

Los tres datos de host son lecturas de sysfs: sin privilegio, sin RUNTIME, sin
escritura. `GPU INTACTA`.

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador contenia texto en otro idioma en el alcance y en dos
lineas del cuerpo. Corregido. Sexto caso del mismo defecto al escribir; la nota se
conserva porque el patron es mio y se repite.