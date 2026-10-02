# 126 · §G: el precio de la coherencia, y por qué esta máquina lo paga

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`124` dejó `p->immediate` como la variable que gobierna el coste de la coherencia
de page tables, y dijo que faltaba derivarla. Esta nota la deriva **entera**.

**Y el resultado es una política, no un accidente: el camino rápido existe y sólo
se usa cuando la GPU ya está parada.**

## Qué cambia exactamente con `immediate`

```
amdgpu_vm_sdma.c:45   enum amdgpu_ib_pool_type pool = p->immediate ? AMDGPU_IB_POOL_IMMEDIATE
amdgpu_vm_sdma.c:46                                                   : AMDGPU_IB_POOL_DELAYED;
amdgpu_vm_sdma.c:47   struct drm_sched_entity *entity = p->immediate ? &p->vm->immediate
amdgpu_vm_sdma.c:48                                                   : &p->vm->delayed;
```

**Precedencia: `?:` antes que `=`**, así que el agrupamiento es como lo leo.

Y lo que dice el propio enum sobre esos pools:

```
amdgpu_ring.h:92   /* Normal submissions to the top of the pipeline.    */
amdgpu_ring.h:93   AMDGPU_IB_POOL_DELAYED,
amdgpu_ring.h:94   /* Immediate submissions to the bottom of the pipeline. */
amdgpu_ring.h:95   AMDGPU_IB_POOL_IMMEDIATE,
```

**Una precisión que tengo que hacer, porque es donde iba a equivocarme:** `immediate`
**no** cambia la cola. Las dos entidades se enlazan a los mismos schedulers:

```
amdgpu_vm.c:544   drm_sched_entity_init(&vm->immediate, ..., adev->vm_manager.vm_pte_scheds, ...)
amdgpu_vm.c:550   drm_sched_entity_init(&vm->delayed,   ..., adev->vm_manager.vm_pte_scheds, ...)
```

**Dos entidades en un conjunto de colas, no dos colas.** Lo que `immediate`
selecciona es (a) el pool de SA del que sale el IB, y (b) la entidad. Lo que de
verdad cambia el comportamiento es el flag de `124`:

```
amdgpu_vm_sdma.c:135   if (fence && !p->immediate) {
amdgpu_vm_sdma.c:141       set_bit(DRM_SCHED_FENCE_DONT_PIPELINE, &f->flags);
```

## Y sí hay cola de page tables separada: la premisa del comentario se cumple

El comentario de `amdgpu_vm_sdma.c:137-139` dice *"Most hw generations now have a
separate queue for page table updates"*. Eso es una afirmación sobre la
generación, y en el caso de una GPU nueva habría que comprobarlo. Se comprueba:

```
amdgpu_vm.c:3266   adev->vm_manager.vm_pte_scheds[i] = sched;
amdgpu_vm.c:3268   adev->vm_manager.vm_pte_num_scheds = adev->sdma.num_instances;
amdgpu_vm_sdma.c:113   ring = container_of(p->vm->delayed.rq->sched, struct amdgpu_ring, sched);
```

**Una cola de paging por instancia SDMA, y las actualizaciones de page tables
corren en un anillo SDMA, no en el anillo GFX.** La premisa se cumple en esta
generación: `PROVEN`, no suponer por el comentario.

## Quién usa `immediate = true`: exactamente uno

Todos los call sites de `amdgpu_vm_update_pdes`, con su argumento:

| call site | `immediate` | camino |
|---|---|---|
| **`amdgpu_cs.c:1164`** | **`false`** | **scheduler de graphics — el que corre aquí** |
| `amdgpu_gem.c:775` | `false` | GEM, buffers liberados |
| `amdgpu_userq.c:1061` | `false` | cola de usuario |
| `amdgpu_amdkfd_gpuvm.c:506` | `false` | GPUVM de KFD |
| `mes_v12_1.c:2009` | `false` | MES, sólo GFX9.4+ |
| **`amdgpu_vm.c:3079`** | **`true`** | **el único, en `amdgpu_vm_handle_fault`** |

Y dentro del manejador de fallo, las dos llamadas:

```
amdgpu_vm.c:3013   bool amdgpu_vm_handle_fault(struct amdgpu_device *adev, u32 pasid, ...)
amdgpu_vm.c:3074       r = amdgpu_vm_update_range(adev, vm, true, false, false, false, NULL, ...);
amdgpu_vm.c:3079       r = amdgpu_vm_update_pdes(adev, vm, true);
```

**`immediate = true` es exclusivamente el camino de page fault.**

## La política, ya legible entera

| | `immediate = false` | `immediate = true` |
|---|---|---|
| quién lo usa | **todo**, incluido el scheduler de graphics | **sólo page faults** |
| pool de IB | `DELAYED` — normal, arriba del pipeline | `IMMEDIATE` — abajo del pipeline |
| entidad | `vm->delayed` | `vm->immediate` |
| `DONT_PIPELINE` | **se pone** | no |
| viaje por la CPU | **sí** | no |
| cuándo | la GPU está trabajando | **la GPU ya está bloqueada** |

**El driver reparte el coste según si puede permitirse pagarlo.** El camino
rápido existe, está implementado, y se reserva para el caso en que no importa
la latencia porque el hardware ya está parado esperando la traducción.

**Y en el caso normal paga la CPU aunque la GPU esté ocupada**, porque el
invalidate no puede ir antes que la escritura y eso es un requisito de
corrección, no de rendimiento.

**Para esta máquina: `immediate = false` en el camino que corre. Se paga el viaje
por la CPU.** `PROVEN_DERIVED` — la composición es `amdgpu_cs.c:1164` da
`false`, y `amdgpu_vm_sdma.c:135` con `fence` no nulo cumple la condición.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `immediate` elige pool y entidad, no cola | `PROVEN` (`amdgpu_vm.c:544` `:550`) |
| Las dos entidades comparten `vm_pte_scheds` | `PROVEN` (`amdgpu_vm.c:544` `:550`) |
| Hay una cola de paging por instancia SDMA | `PROVEN` (`amdgpu_vm.c:3268`) |
| Las page tables se escriben en un anillo SDMA | `PROVEN` (`amdgpu_vm_sdma.c:113`) |
| `immediate = true` sólo en page faults | `PROVEN` (6 call sites, 1 con `true`) |
| Esta máquina paga el viaje por la CPU | `PROVEN_DERIVED` |
| Cuántas instancias SDMA hay | **`PROVEN_DERIVED`** — 2 |
| Cuántas actualizaciones de page tables ocurren por frame | **`NOT_DETERMINED`** |
| Si el coste es medible en esta máquina | **`NOT_DETERMINED`** — sin placa |

### El que cerré al terminar, que era software y no placa

```
sdma_v3_0.c:1097   switch (adev->asic_type) {
sdma_v3_0.c:1098   case CHIP_STONEY:
sdma_v3_0.c:1099       adev->sdma.num_instances = 1;
sdma_v3_0.c:1101   default:
sdma_v3_0.c:1102       adev->sdma.num_instances = SDMA_MAX_INSTANCE;
sid.h:555          #define SDMA_MAX_INSTANCE 2
amdgpu_device.c:1980   case CHIP_POLARIS12:      <- case distinto de
amdgpu_device.c:1983   case CHIP_STONEY:            CHIP_STONEY, no comparten
```

**Polaris12 cae en `default`: `num_instances = 2`, luego `vm_pte_num_scheds = 2`.**

**DOS COLAS DE PAGING, UNA POR INSTANCIA SDMA.** Que es lo que hace real la
afirmación del comentario de `amdgpu_vm_sdma.c:137` que `124` aceptó sin
comprobar: la cola de page tables está separada de la de graphics porque **los
SDMA son un recurso distinto del anillo GFX**, y hay dos.

**Y esto refina lo que dije en `124`.** Escribí "una cola de paging por instancia
SDMA" como si fuera una generalidad. **En esta GPU son exactamente dos**, y no
por diseño sino porque el `switch` del `early_init` sólo baja a 1 para Stoney.

**Lo que queda necesita placa: cuántas veces ocurren las actualizaciones de
page tables.**

**Un apunte que no es cierre pero que importa:** el commentary de
`amdgpu_vm_sdma.c:137` describe *"most hardware generations"*. En una GPU de la
que no tengo evidencia, ese comentario es una afirmación sobre otra generación,
no sobre esta. **Aquí se cumplen las dos condiciones — cola separada y SDMA
dedicado—, y lo comprobé en vez de Repetirlo.**

## Procedencia

- `STATIC` -- `amdgpu_vm_sdma.c:42-48` `:113` `:135-141`, `amdgpu_vm.c:544-552`
  `:984-985` `:1008` `:3013` `:3074` `:3079` `:3255-3268`,
  `amdgpu_ring.h:91-100`, `amdgpu_cs.c:1164`, `amdgpu_gem.c:775`,
  `amdgpu_userq.c:1061`, `amdgpu_amdkfd_gpuvm.c:506`, `mes_v12_1.c:2009`.
- Sin MMIO write, sin TLB, sin módulos, sin lectura de debugfs.
- Encadenada con `124` (la coherencia es orden por fence), `115` (`tlb_seq` y
  `flushed_updates`), `113` (el scheduler pide el vm_flush), `103`/`104`/`106`
  (el registro de invalidate), `116` (`use_cpu_for_update` nunca dispara).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Iba a escribir que `immediate` elegía la cola, y no es así: elige la entidad.**
Lo dice `amdgpu_vm.c:544` frente a `:550`, los dos `drm_sched_entity_init` con los
mismos `vm_pte_scheds`. Lo vi antes de escribirlo porque ya me había pasado con
`amdgpu_job_alloc_with_ib`, donde también me equivoqué con la firma.

**Es la segunda vez en dos notas que un puntero a función o una firma me hace
confundir "qué argumento" con "qué cola". Y las dos veces la respuesta estaba en
leer la firma entera, no en la línea que estaba mirando.**

La regla que sale: **una llamada con dos punteros a función de la misma tabla
puede elegir entre dos cosas distintas, y hay que leer qué puntero se está
poniendo.**

Y una segunda, que es la tercera vez que me pasa y por eso la dejo escrita.

**`grep -h` borra el nombre del fichero, y con él se borra la evidencia de a qué
fichero se resolvió.** Me pasó aquí: `SDMA_MAX_INSTANCE` aparece en `sid.h:555`,
`vid.h:28` y `cikd.h:493`, los tres con el mismo valor. Busqué con `-h`, vi
"493", y lo atribuí a `sdma_v3_0.h`, que tiene 30 líneas y no puede llegar a 493.

**Es el mismo error tres veces con tres disguises:**

| | el mecanismo |
|---|---|
| `111` | el atajo `:NNNN` sin fichero, y `citecheck` heredaba el anterior |
| `124` | cité `amdgpu_vm_sdma.c` con números que son de `amdgpu_vm.c` |
| `126` | `grep -h` me devolvió una línea sin decirme de qué fichero |

**Los tres son: una cadena que parece una cita y no lleva el fichero.**

**La regla que sale, y es la que me llevo:**

> *Una cita es el par fichero-línea, y el fichero es la mitad de la evidencia.*
> *Si lo escribo a medias, la otra mitad la pone quien lee, que no lo sabe.*

Y la anterior sigue valiendo: una llamada con dos punteros a función de la misma
tabla puede elegir entre dos cosas distintas, y hay que leer qué puntero se está
poniendo.
---

# CORRECCION POSTERIOR — la cita es de 7.1.3 y no lo declara

Este documento **no se reescribe**. Lo que sigue corrige el árbol de una cita.
La afirmación **no cambia** y es verificable en el corpus declarado.

## Lo que se corrige

La tabla de «Lo que NO cierra» cita `amdgpu_vm.c:3268`, y el bloque de código de
la cabecera reproduce:

```
amdgpu_vm.c:3266   adev->vm_manager.vm_pte_scheds[i] = sched;
amdgpu_vm.c:3268   adev->vm_manager.vm_pte_num_scheds = adev->sdma.num_instances;
```

**Esas líneas son de `linux-7.1.3`, no de `linux-7.2.8`.** Medido:

```
7.2.8  amdgpu_vm.c   3228 lineas      -> 3268 no existe
7.1.3  amdgpu_vm.c   3282 lineas      -> 3268 existe

7.2.8  amdgpu_vm.c:3213  void amdgpu_sdma_set_vm_pte_scheds(struct amdgpu_device *adev, ...)
7.2.8  amdgpu_vm.c:3226  adev->vm_manager.vm_pte_num_scheds = adev->sdma.num_instances;
```

## Lo que NO cambia

La afirmación «hay una cola de paging por instancia SDMA» **sigue siendo
correcta**, y ahora es citable en el árbol declarado: `amdgpu_vm.c:3226` en
7.2.8. La cadena de este hallazgo no depende del número de línea, sino del
hecho de que el array se dimensiona por `adev->sdma.num_instances`.

## Por qué se registra

Porque el proyecto tiene **cuatro** árboles de fuentes con
`drivers/gpu/drm/amd/amdgpu/` y **ninguna** herramienta de las que existían
comprobaba el árbol de las citas de los hallazgos: `audit_citations.sh` resuelve
contra 7.2.8 pero sólo sobre `07-DRIVER/`, y `artifacts.py --solo-referencias`
resuelve por nombre de fichero sin mirar la línea. El hueco lo encontró
`tools/treescope.py`, y antes de encontrarlo ya había producido una cita falsa
en otro hallazgo — `127-align-mask-no-se-opone-a-emit-ib-size.md:71-80`, que
citaba `amdgpu_gfx.c:1682` y esa línea solo existe en `RESEARCH/kernelbuild/
linux-7.1.3`.

**Una cita que resuelve, en el árbol equivocado, es indistinguible de una
correcta si nadie declara el árbol.**

`CORRECTED_BY=126-CORRECCION-POSTERIOR`.
