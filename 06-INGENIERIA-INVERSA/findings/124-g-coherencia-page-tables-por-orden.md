# 124 · §G: la coherencia de las page tables no es un flush de caché, es un fence

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

AGENTS.md §G pide *resolver* `CPU ↔ page tables ↔ GPU ↔ TLB ↔ GPU caches` y
prohíbe *asumir coherencia por analogía*. Esta nota cierra el tramo de page
tables con la cadena completa, de `PROVEN` a `PROVEN`.

**Y el resultado es contraintuitivo: no hay ninguna operación de caché sobre las
page tables.**

## La cadena, sin huecos

```
amdgpu_cs.c:1085   amdgpu_cs_vm_handling(p)                    el job de graphics
amdgpu_cs.c:1164       amdgpu_vm_update_pdes(adev, vm, false)   puede encolar la escritura
        |
        +-> amdgpu_vm_sdma_update() -> amdgpu_vm_sdma_commit()
amdgpu_vm_sdma.c:119          if (p->needs_flush)
amdgpu_vm_sdma.c:120              atomic64_inc(&p->vm->tlb_seq)   marca de agua ANTES de enviar
amdgpu_vm_sdma.c:123          f = amdgpu_job_submit(p->job)      SDMA escribe
        |
        +-> amdgpu_vm.c:1024  commit(&params, &vm->last_update)  el fence se guarda
        |
amdgpu_cs.c:1168       amdgpu_sync_fence(&p->sync, vm->last_update, GFP_KERNEL)
                                                                     el job ESPERA
amdgpu_cs.c:1178       job->vm_pd_addr = amdgpu_gmc_pd_addr(vm->root.bo)
        |
amdgpu_vm.c:761        amdgpu_vm_need_pipeline_sync()  -> vm_needs_flush
amdgpu_vm.c:813        vm_flush_needed &= ...
gfx_v8_0.c:6199-6207   WAIT_REG_MEM + mmVM_INVALIDATE_REQUEST
```

**El orden está escrito en el fuente, y a tres líneas de distancia:**

```
amdgpu_cs.c:1164   amdgpu_vm_update_pdes(...)          /* puede escribir */
amdgpu_cs.c:1168   amdgpu_sync_fence(&p->sync, vm->last_update, ...)
```

**No hay cache flush, ni `SURFACE_SYNC`, ni escritura de PTBA aquí.** La
coherencia es que **el job de graphics no puede pasar de `L1168` hasta que el
fence de la escritura por SDMA ha señalado.**

## Y el propio driver dice por qué cuesta dinero

```
amdgpu_vm_sdma.c:135   if (fence && !p->immediate) {
amdgpu_vm_sdma.c:136       /*
amdgpu_vm_sdma.c:137        * Most hw generations now have a separate queue for page table
amdgpu_vm_sdma.c:138        * updates, but when the queue is shared with userspace we need
amdgpu_vm_sdma.c:139        * the extra CPU round trip to correctly flush the TLB.
amdgpu_vm_sdma.c:140        */
amdgpu_vm_sdma.c:141       set_bit(DRM_SCHED_FENCE_DONT_PIPELINE, &f->flags);
```

**El driver lo dice en prosa: cuando la cola de page tables se comparte con
userspace, hace falta un viaje extra por la CPU para poder vaciar el TLB
correctamente.**

**`DONT_PIPELINE` es exactamente "no me encadenes nada, necesito que la CPU
espere a este fence".** Sin eso, el scheduler podría emitir el invalidate del
anillo GFX sin esperar a que la escritura por SDMA haya terminado, y la
coherencia se rompería.

**Así que la coherencia de page tables se compra con sincronización de CPU, y el
precio lo decide si la cola es compartida o no (`p->immediate`).**

## Dos mecanismos de coherencia distintos en el mismo driver

Esto es lo que hace la nota no obvia, y es el punto que quiero que quede:

| | qué se sincroniza | mecanismo | coste |
|---|---|---|---|
| **IB** (flujo de comandos) | la memoria que el PFP va a leer | **paquete PM4** `SURFACE_SYNC` + `CP_COHER_CNTL` sobre TCL1, TC, KCACHE, ICACHE y `TC_WB` | en GPU |
| **page tables** | la memoria que el page walker va a leer | **fence + orden**. Ninguna operación de caché | **ida y vuelta por la CPU** |

**El IB usa hardware. Las page tables usan ordenación por software.** Y no es
inconsistencia del autor: son dos problemas distintos, y el hardware sólo
resuelve el primero.

## La consecuencia hardware, que sigue sin cerrar

Si no hay flush de caché sobre las page tables, y el invalidate sí es un
registro real (`VM_INVALIDATE_REQUEST`, cerrado en `103`/`104`/`106`), entonces la
única salida es que **el page walker no necesitar una invalidación de caché para
ver las entradas nuevas**.

Las dos formas de que eso sea cierto:

| posibilidad | qué implicaría | estado |
|---|---|---|
| las page tables están en memoria no cacheable para la lectura del walker | coherencia por atributos de memoria, no por software | **`NOT_DETERMINED`** |
| el L2 no retiene lecturas del page walker, o las invalida por su cuenta | el invalidate de TLB basta y sobra | **`NOT_DETERMINED`** |

**No sé cuál es, y las dos son hardware.** Con GPU, no con código: la pregunta es
qué caché, si alguna, está en el camino entre la L2 y la lectura del page walker.

**Pero la consecuencia para un driver propio ya no es abstracta.** Si escribo las
page tables desde el SDMA, necesito exactamente lo que hace `amdgpu_cs.c`:
**una barriers que meEnsure el invalidate no se hace visible antes que la
escritura.** El driver resuelve eso con un fence y, cuando hace falta, con un viaje
por la CPU. **Ese es el contrato, y es implementable sin saber cuál de las dos
posibilidades de hardware es la buena.**

**Lo que sí es nuevo aquí, y es la frase que me llevo:** *en GFX8 el invalidate de
TLB es barato y la coherencia de page tables es cara.* Todo el coste está en no
poder encadenar el trabajo, no en la operación de hardware.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| La coherencia de page tables es orden por fence | `PROVEN` (`amdgpu_cs.c:1164` `:1168`) |
| El fence es el de la escritura SDMA | `PROVEN` (`amdgpu_vm.c:1024`) |
| No hay operación de caché sobre page tables | `PROVEN` (leído el camino completo) |
| El invalidate va después de la espera | `PROVEN` (`L1168` → `L1178` → `vm_flush`) |
| `DONT_PIPELINE` fuerza el viaje por la CPU | `PROVEN` (`amdgpu_vm_sdma.c:141`) |
| El coste depende de `p->immediate` | `PROVEN` (`L135`) |
| `tlb_seq` se incrementa antes de enviar el job | `PROVEN` (`L120` antes de `L123`) |
| IB y page tables usan coherencia distinta | `PROVEN` (comparación de las dos cadenas) |
| Qué caché hay en el camino del page walker | **`NOT_DETERMINED`** — hardware |
| Si las page tables están en memoria no cacheable | **`NOT_DETERMINED`** — hardware |
| Cuándo `tlb_seq` lo lee el hardware | **`NOT_PROVEN`** — no hay campo de estado que lo exponga |

**La penúltima y la última son las mismas preguntadas de dos formas, y las dos
requieren placa.** Todo lo demás queda cerrado.

**Y una asimetría que conviene no pasar por alto:** `L120` incrementa la marca de
agua *antes* de que el job se envíe. El driver declara "las page tables ya son la
revisión N+1" mientras todavía las está escribiendo. **Eso sólo es seguro porque
el consumidor espera el fence y no el número.** Para un driver propio la regla es
inevitable: **el número de revisión es una pista, la verdad es el fence.**

## Procedencia

- `STATIC` -- `amdgpu_cs.c:1085`, `amdgpu_cs.c:1155-1195`, `amdgpu_vm.c:751-771`,
  `amdgpu_vm.c:1024`, `amdgpu_vm.c:1069-1090`, `amdgpu_vm.c:1175-1179`,
  `amdgpu_vm.c:2618-2648`, `amdgpu_vm_sdma.c:106-146`, `amdgpu_vm_sdma.c:219`,
  `gfx_v8_0.c:6191-6215`, `gfx_v8_0.c:6761-6772`, `amdgpu_ib.c:197-215`.
- Sin MMIO write, sin TLB, sin módulos, sin lectura de debugfs.
- Encadenada con `115` (la marca `flushed_updates` y `tlb_seq`), `113` (el
  scheduler pide el vm_flush), `116` (`use_cpu_for_update` nunca dispara),
  `103`/`104`/`106` (el registro de invalidate y sus 16 bits), `123` (el IB y su
  `SURFACE_SYNC`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

**Una nota de método, y es la que produjo el hallazgo.**

Entré buscando "qué caché se invalida" y me salió un `DONT_PIPELINE`. Tardé
medio segundo en entender que no era ruido: era **el mecanismo entero**.

**La pregunta que importa en §G no es qué se invalida, sino qué garantiza el
orden.** Y la respuesta no estaba en ningún registro, sino en la distancia entre
la línea 1164 y la 1168 de un fichero que ya tenía abierto.

**Llevo varias notas seguidos entrando por la puerta de los registros y saliendo
por la de la ordenación. Es el mismo hallazgo cuatro veces con distinto
empaquetado: en GFX8 la semántica está en el software y los registros sólo la
ejecutan.**