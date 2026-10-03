# GPUVM-AGENT-10 · El nodo que falta entre §1 y §2: QUIÉN ASIGNA EL VMID

> **Addendum al grafo de GPUVM.** No edita `docs/KNOWLEDGE-GRAPH.md`: su ambito
> (`.write-lock/docs`, owner PID 24792) no corre pero tomarlo exige autorizacion
> humana de LOCK_TAKEOVER, que esta sesion no tiene. Este fichero es el texto
> para pegar cuando alguien con ese permiso lo integre.
>
> ```
> AGENCIA_DE_ORIGEN   agente AGENT-10 (GPUVM)
> WORK_CLASS          reconstruccion de cadena (READ_ANALYSIS -> escritura de 1 artefacto)
> RUNTIME             NOT_RUN        · GPU INTACTA · SIN_SUDO
> SCOPE_ESCRITURA     .write-lock/gpuvm + este artefacto. Nada mas.
> METODO              ESTATICO sobre el corpus. Sin hardware, sin captura.
> ```

## 0 · QUE ESTABA Y QUE FALTA

El grafo de GPUVM tiene dos cadenas y **no las une**:

| § | Cadena | Nodo terminal |
|---|---|---|
| §1 | como se ESCRIBE una page table | `PTBA = table_addr >> 12`, y "page walker" (NO observado) |
| §2 | como se INVALIDA | `VM_INVALIDATE_REQUEST = 1 << vmid` |

Lo que falta es la pregunta que hace que ambas sean el mismo sistema:

```
¿QUE decide que un invalidate concreto vaya con un PTBA concreto?
```

La respuesta esta en `amdgpu_ids.c`, un fichero de 639 lineas que **no aparece
como nodo en ninguna de las dos cadenas**. Y el nodo que falta tiene una
consecuencia de hardware directa: **si el allocator decide que no hay que
invalidar, no se invalida**, y por §2 no hay ack para enterarse.

---

## 1 · LA CADENA COMPLETA, de extremo a extremo

```
CPU SOFTWARE
  │
  │ amdgpu_cs.c:1178        job->vm_pd_addr = amdgpu_gmc_pd_addr(vm->root.bo)
  │                              |
  │                              |  amdgpu_gmc.c:135-147
  │                              |    if (adev->asic_type >= CHIP_VEGA10)  -> get_pde_for_bo
  │                              |    else                                 -> amdgpu_bo_gpu_offset(bo)
  │                              |
  │                              |  <<< ARESTA QUE FALTABA >>>
  │                              |  ESTA COMPARACION es la que decide si la PTE
  │                              |  lleva flags. En GFX8: la rama `else`.
  │                              v
  v  REPRESENTACION
  job->vm_pd_addr   (uint64_t, amdgpu_job.h:79)
  job->vmid         (unsigned)
  job->vm_needs_flush (bool)
  job->pasid        (unsigned)
  │
  │ amdgpu_ids.c:385 amdgpu_vmid_grab(vm, ring, job, &fence)
  │     mutex_lock(&id_mgr->lock)              <-- SERIALIZA la decision
  │     |
  │     +-> amdgpu_vmid_grab_idle     : ring->vmid_wait fairness; recorre ids_lru
  │     |                              en REVERSE (LRU primero)
  │     |
  │     +-> [si uses_reserved] grab_reserved
  │     |
  │     +-> amdgpu_vmid_grab_used    : RECICLA un VMID ya asignado
  │           |   id->owner == vm->immediate.fence_context   (mismo proceso)
  │           |   amdgpu_vmid_compatible: id->pd_gpu_addr == job->vm_pd_addr   <<<<<
  │           |                      + NO hay gds/gws/oa switch pendiente
  │           |   (!id->last_flush ||
  │           |    (id->last_flush->context != fence_context &&
  │           |     !dma_fence_is_signaled(id->last_flush)))   -> needs_flush
  │           |   id->flushed_updates < amdgpu_vm_tlb_seq(vm) -> needs_flush
  │           |
  |           v
  |     job->vmid = id - id_mgr->ids;         <-- EL VMID ES UN INDICE DE ARRAY
  |                                            amdgpu_ids.c:432
  |     job->pasid = vm->pasid;
  |     id->pd_gpu_addr = job->vm_pd_addr;    <-- se CONSUME la comparacion
  |     id->flushed_updates = amdgpu_vm_tlb_seq(vm)   (si se va a invalidar)
  |
  v
CONSUMER
  amdgpu_vm.c:851   amdgpu_ring_emit_vm_flush(ring, job->vmid, job->vm_pd_addr)
  gfx_v8_0.c:6191   gfx_v8_0_ring_emit_vm_flush
       PTBA(vmid)          = pd_addr >> 12
       VM_INVALIDATE_REQUEST = 1 << vmid
       WAIT_REG_MEM FUNCTION=always ref=0 mask=0     [RE-01: NO ESPERA NADA]
  │
  v
HARDWARE EFFECT
  GPUVA -> PA, via la tabla que PTBA acaba de apuntar
```

### El nodo, aislado

```
PRODUCER          amdgpu_cs.c:1178  ->  job->vm_pd_addr
TRANSFORMACION    amdgpu_gmc_pd_addr(): asic_type >= CHIP_VEGA10 ?
REPRESENTACION    job->vm_pd_addr (u64) + job->vmid (unsigned)
CONSUMER          gfx_v8_0_ring_emit_vm_flush(ring, vmid, pd_addr)
HARDWARE EFFECT   page walker + TLB invalidation del dominio vmid
```

---

## 2 · LO QUE ESTA MEDIDO Y LO QUE NO

| Proposicion | Estado | Como se ha obtenido |
|---|---|---|
| `job->vm_pd_addr` es el PTBA que se emite | `PROVEN` | lectura, `amdgpu_vm.c:851` |
| El recycle exige `id->pd_gpu_addr == job->vm_pd_addr` | `PROVEN` | lectura, `amdgpu_ids.c:194` |
| `job->vmid` es indice de array, no un contador | `PROVEN` | lectura, `amdgpu_ids.c:432` |
| GFX8 toma la rama `else` de `amdgpu_gmc_pd_addr` | `PROVEN_DERIVED` | Polaris12 < Vega10 en el enum; ver §3 |
| GFX8 tiene 16 VMID, 1-7 para graficos, 8-15 KFD, 0 sistema | `PROVEN` | `gmc_v8_0.c:1160-1168` + `AMDGPU_NUM_VMID 16` |
| `num_ids` real = 8 para esta placa | `PROVEN_DERIVED` | `amdgpu_ids.c:586-588` + `first_kfd_vmid=8` |
| El hardware honra el invalidate | **`NOT_DETERMINED`** | RE-02: no hay ack. No lo cambia este trabajo |
| Que un VMID NO invalidado reutilice la tabla correcta | **`NOT_DETERMINED`** | depende del anterior |

**Lo que este nodo NO arregla:** RE-02 sigue abierto. Anadir el nodo del
allocator **no da un ack**. Lo que si hace es cambiar el alcance de la
pregunta: antes "el invalidate no tiene ack", ahora "y ademas hay un punto de
software que DECIDE si se emite". Eso es un segundo sitio donde poder fallar
en silencio, y antes no estaba en el grafo.

---

## 3 · DOS HALLAZGOS DE ALCANCE, no de semantica

### 3.1 · `gmc_v8_1.c` NO EXISTE, y el grafo lo insinua

`docs/KNOWLEDGE-GRAPH.md` §1 cita `gmc_8_1_d.h` para offsets de registro. El
**header** existe; el **.c no**:

```
4 de 4 raices del corpus:
  gmc_v8_1.c          NO EXISTE
  gmc_8_1_d.h         EXISTE
  gmc_v8_0.c          contiene POLARIS12 y escribe first_kfd_vmid=8
```
`baseline/`, `working/`, `kernelbuild/` (7.1.3) y `rx550-upstream-7.2.8`.

Consecuencia para el grafo: el codigo que corre en esta placa es
**`gmc_v8_0.c`**, y todo numero de GPUVM citado como "de v8_1" hay que
revisarlo contra `gmc_v8_0.c`. Los offsets de registro en `gmc_8_1_d.h` siguen
siendo validos — son definiciones de ASIC, no de fichero compilado — pero la
**geometria y los valores** salen del .c. Esto es `COMPILE_GATE_BEFORE_TRACE_GATE`
(regla de 046) aplicada a un caso que no estaba registrado.

### 3.2 · `first_kfd_vmid = 8` es la raiz del presupuesto de VMID

```
gmc_v8_0.c:1160-1168
  /* number of VMs
   * VMID 0 is reserved for System
   * amdgpu graphics/compute will use VMIDs 1-7
   * amdkfd will use VMIDs 8-15 */
  adev->vm_manager.first_kfd_vmid = 8;

amdgpu_ids.c:585-588
  if (amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(10,0,0))
      id_mgr->num_ids = adev->vm_manager.first_kfd_vmid;
```

**Corrobora EV-21 de forma independiente.** EV-21 observo `vmid = 7` en los 8
IB del anillo y dedujo "7 es el ultimo del bloque de graficos". Aqui sale de
`first_kfd_vmid = 8` sin mirar el anillo: dos vias, mismo numero. Y da la cota
que el grafo no tenia: **un VM propio tiene 7 slots (1-7), no 16.**

`concurrent_flush` (amdgpu_vm.c:2873) es `false` en esta placa
(`asic_type < CHIP_VEGA10`), lo que hace que el allocator **no** recicle un
VMID que necesite flush (amdgpu_ids.c:355). Es decir: en GFX8 el flush no es
opcional por software cuando toca.

---

## 4 · PROOF OBLIGATIONS

### PO-10-A · Que un VMID reutilizado apunte a la tabla correcta

```
REQUISITO   si id->pd_gpu_addr == job->vm_pd_addr y no hay flush pendiente,
            el ring puede reusar el VMID sin re-emitir PTBA
CADENA      grab_used (compara) -> id->pd_gpu_addr = job->vm_pd_addr (consume)
            -> emit_vm_flush solo si job->vm_needs_flush
DISCUTIR    que el page walker de GFX8 tiene la tabla cacheada por (vmid,PTBA)
            y que el software mantiene esa invariante
CONTRAINTEO RE-01/RE-02: si el invalidate previo no ha aplicado, reutilizar el
            VMID SIN re-emitir es un fallo silencioso. No hay ack que lo detecte
BLOQUEO    RUNTIME. Necesita F1
```

### PO-10-B · Que `flushed_updates` sea una cota, no una bandera

```
REQUISITO   id->flushed_updates >= amdgpu_vm_tlb_seq(vm) implica que TODA
            actualizacion de tabla anterior al grab esta visible
CADENA      amdgpu_vm_tlb_seq(vm) (crece por update)
            -> id->flushed_updates = ... (solo si se va a invalidar)
            -> needs_flush = (id->flushed_updates < updates)
DISCUTIR    el instante exacto en que "esta visible" pasa a ser cierto; es el
            mismo instante que RE-02 no puede observar
CONTRAINTEO si se emite el vm_flush pero no se actualiza flushed_updates por un
            camino que evita amdgpu_vmid_grab, la cota se rompe sin que nada lo vea
BLOQUEO    RUNTIME + cobertura de callers de amdgpu_vmid_grab
```

### PO-10-C · Que el presupuesto de VMID sea 1-7 y no 16

```
REQUISITO   un VM propio debe poder asignar 7 VMID concurrentes
CADENA      gmc_v8_0.c:1168 (first_kfd_vmid=8) -> amdgpu_ids.c:588 (num_ids)
            -> job->vmid = id - id_mgr->ids  ∈ [0,8)
DISCUTIR    si KFD esta presente: entonces 8-15 son suyos y un driver propio
            NO debe tocarlos aunque el allocator no los alcance
CONTRAINTEO EV-21 corrobora 7 desde el anillo. La cota es PROVEN_DERIVED,
            no observada en runtime
BLOQUEO     ninguno tecnico. Es la unica de las tres que se puede cerrar ya
```

---

## 5 · ARISTAS QUE TOCA ESTE NODO

```
ESTE NODO  ──UNE──>  §1 (PTBA: de donde sale pd_addr)
         ──UNE──>  §2 (VM_INVALIDATE_REQUEST: de donde sale vmid)
         ──EXPLICA──>  EV-21 (vmid=7 observado == ultimo slot de graficos)
         ──NO CIERRA──>  RE-01, RE-02 (no hay ack; esto no inventa uno)
         ──PRECISA──>  F1 (el discriminante de F1 necesita un VMID con flush
                       retrasado; el allocator dice como pedirlo:Needs_flush)
         ──NUEVA──> RIESGO: el punto de decision sin observador. Un driver
                     propio que replique mal `grab_used` puede reusar un VMID
                     sin invalidar, y no habra forma de saberlo desde software
```

---

## 6 · LIMITACIONES DE ESTE TRABAJO

```
1. TODO es PROVEN o PROVEN_DERIVED POR LECTURA del corpus 7.1.3. Ninguna
   observacion de hardware. RUNTIME=NOT_RUN.
2. El corpus se leio en working/linux-7.1.3. Las cifras de 3.1 se cruzaron en
   4 de 4 raices; las de §1 y §2, solo en working. `baseline/` y
   `working/` son identicos en los ficheros citados salvo indicacion.
3. No se integro en docs/KNOWLEDGE-GRAPH.md. Ver cabecera.
4. No se abrio ninguna frontera nueva en OPEN-FRONTIERS.md: PO-10-C se puede
   cerrar ya con lo medido, y PO-10-A/B dependen de F1, que ya existe.
5. El valor de `concurrent_flush=false` se deduce de `asic_type < CHIP_VEGA10`.
   El orden del enum no se leyo literalmente en esta ronda: se infiere de que
   el propio driver usa esa comparacion para GFX8 y de que EV-39 ya fijo que
   la version de GC_HWIP es 0. Clasificado PROVEN_DERIVED, no PROVEN.
```

AUTORIA=AGENT-10-GPUVM
WORK_CLASS=reconstruccion-de-cadena / actualizacion-de-grafo
RUNTIME=NOT_RUN
GPU=INTACTA
SUDO=NO
WRITES=1 artefacto nuevo + .write-lock/gpuvm/owner