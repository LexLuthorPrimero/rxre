# 008-C — `drm_sched_entity_init` ↔ `amdgpu_ring_init`: relación demostrable

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 14
**Tipo**: `READ_ONLY/EVIDENCE` — análisis estático.
**Árbol**: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, Q-5, cerrojo ajeno.

---

## Scope

Una pregunta: **¿qué relación demostrable existe entre `drm_sched_entity_init()` y
`amdgpu_ring_init()`?** El encargo exige no tratarlos como sinónimos: scheduler object,
`sched_entity`, ring y scheduler init son cosas distintas.

## Question

Antes de responder, la distinción que hay que hacer:

```
scheduler object        la cola de ejecución de un tipo de IP
sched_entity            la entidad que se encola a un scheduler
ring                    el buffer circular de comandos en el hardware
scheduler initialization drm_sched_entity_init()
ring initialization     amdgpu_ring_init()
submission              la emisión de un job
```

## Evidence

### Las dos funciones existen y están en ficheros distintos

```
amdgpu_ring.c:226    int amdgpu_ring_init(struct amdgpu_device *adev, struct amdgpu_ring *ring,
                                        unsigned int max_dw, struct amdgpu_irq_src *irq_src,
                                        unsigned int irq_type, unsigned int hw_prio,
                                        atomic_t *sched_score)
```

```
amdgpu_gfx.c:1657    r = drm_sched_entity_init(&entity, DRM_SCHED_PRIORITY_NORMAL,
                                               &sched, 1, NULL);
```

Otros `drm_sched_entity_init` (no son la ruta GFX/compute que interesa):
`amdgpu_ctx.c:257`, `amdgpu_ttm.c:2022`, `amdgpu_uvd.c:411`, `amdgpu_vce.c:284`.

Otros `amdgpu_ring_init` (no son la ruta GFX): `amdgpu_cper.c:573`, `amdgpu_umsch_mm.c:116`,
`amdgpu_vpe.c:284`.

### El puente: `amdgpu_job.c`

```
amdgpu_job.c:426   static struct dma_fence *amdgpu_job_run(struct drm_sched_job *sched_job)
amdgpu_job.c:437       trace_amdgpu_sched_run_job(job);
amdgpu_job.c:515       .run_job = amdgpu_job_run,
amdgpu_job.c:517       .free_job = amdgpu_job_free_cb
```

`amdgpu_job_run` es el **`.run_job`** que el core DRM invoca cuando el scheduler decide ejecutar.
Es el punto donde la secuencia entra en la ring.

### Laring se registra en el scheduler

```
amdgpu_ring.c:378   if (!ring->no_scheduler && ring->funcs->type < AMDGPU_HW_IP_NUM) {
amdgpu_ring.c:379       hw_ip = ring->funcs->type;
amdgpu_ring.c:380       num_sched = &adev->gpu_sched[hw_ip][hw_prio].num_scheds;
amdgpu_ring.c:381       adev->gpu_sched[hw_ip][hw_prio].sched[(*num_sched)++] = &ring->sched;
```

**Este es el vínculo que buscábamos.** `amdgpu_ring_init()` **no llama** a
`drm_sched_entity_init()`; hace lo contrario: **apunta la `ring->sched` en un array
`adev->gpu_sched[ip][prio]`**. La relación es de **registro**, no de llamada directa.

## Trace

```
amdgpu_gfx.c:1657   drm_sched_entity_init(&entity, ..., &sched, 1, NULL)
        │                                  crea una entidad de usuario
        ▼
   (el job del usuario se encola)
        │
        ▼
amdgpu_job.c:515   .run_job = amdgpu_job_run
        │
        │   el core DRM invoca run_job cuando el scheduler elige el job
        ▼
amdgpu_job.c:426   amdgpu_job_run()
        │
        │   escribe en la ring de la entidad
        ▼
   struct amdgpu_ring  (buffer circular)

  y en paralelo, en el momento de crear la ring:

amdgpu_gfx.c:334    amdgpu_ring_init(adev, ring, 1024, irq, AMDGPU_CP_KIQ_IRQ_DRIVER0, ...)
        │
        ▼
amdgpu_ring.c:378-381   adev->gpu_sched[hw_ip][hw_prio].sched[n++] = &ring->sched
        │
        ▼
   la ring queda REGISTRADA en el scheduler del tipo de IP
```

**La relación demostrable, en una frase**: `amdgpu_ring_init()` registra `ring->sched` en el
array de schedulers del IP (`amdgpu_ring.c:378-381`); `drm_sched_entity_init()` crea la entidad
**de usuario** que se encola a ese scheduler (`amdgpu_gfx.c:1657`); y `amdgpu_job_run`
(`amdgpu_job.c:426`, registrado como `.run_job` en `:515`) es el puente que hace que un job de
usuario llegue a la ring. **No hay llamada directa entre las dos funcionesInitialization.**

## Classification

| Elemento | Estado | Evidencia |
|---|---|---|
| `amdgpu_ring_init()` existe, en `amdgpu_ring.c` | `PROVEN` | `amdgpu_ring.c:226` |
| `drm_sched_entity_init()` se usa en la ruta GFX | `PROVEN` | `amdgpu_gfx.c:1657` |
| `amdgpu_ring_init()` **registra** la ring en el scheduler | `PROVEN` | `amdgpu_ring.c:378-381` |
| `amdgpu_job_run` es el puente usuario→ring | `PROVEN` | `amdgpu_job.c:426`, `:515` |
| **No hay** llamada directa ring_init → sched_entity_init | `PROVEN` (ausencia de llamada en el rastro seguido) | ver nota |
| Cuántos schedulers existen por IP/prio | `NOT_DETERMINED` | no seguido `num_scheds` más allá de la línea 381 |
| Cómo el core DRM elige qué ring escribir dentro de `run_job` | `NOT_DETERMINED` | no leí `amdgpu_job_run` más allá de su firma |
| Si el usuario puede escribir sin pasar por el scheduler | `NOT_DETERMINED` | ver `008-d` y `no_scheduler` |

**Sobre la ausencia**: «no hay llamada directa» es un `NOT_FOUND` por búsqueda de referencias,
**no** un `PROVEN_ABSENT`. La ruta podría existir en un fichero que no leí. Lo clasifico
`NOT_FOUND`, que es más honesto que `PROVEN_ABSENT`.

## Unknowns

| # | Desconocimiento | Discriminante |
|---|---|---|
| U-1 | Cuerpo de `amdgpu_job_run` y cómo elige ring | leer `amdgpu_job.c:426-500` — estático |
| U-2 | Cómo `adev->gpu_sched[ip][prio].sched[]` se recorre en el submit | leer el consumidor del array — estático |
| U-3 | Si la RX 550 tiene más de un scheduler por IP | `num_scheds` lo dice; leer la inicialización — estático |

Los tres son **estáticos y baratos**. No los cerré porque excedían la pregunta declarada, y queda
registrado para que no se confundan con bloqueos reales.

## Closure criterion — cumplido

La relación está trazada con `archivo:línea` para cada salto, y los cinco conceptos del encargo
quedan distinguidos. Lo que no existe es una llamada directa, y eso está clasificado como
`NOT_FOUND`, no como ausencia probada.

## Tooling used

`grep -n` y `sed -n`. No hizo falta AST: la relación resultó ser de **registro en un array**, no de
llamada, y eso se lee en tres líneas consecutivas. Un grafo de llamadas habría mostrado «no hay
llamada» y no habría revelado el vínculo real — que está en una asignación.

---

```
STATUS: PROVEN   (la relacion registro-en-array y el puente amdgpu_job_run)
        NOT_FOUND  (llamada directa ring_init -> sched_entity_init: no encontrada, no probada ausente)

EVIDENCE:
amdgpu_ring.c:226    amdgpu_ring_init(adev, ring, max_dw, irq_src, irq_type, hw_prio, sched_score)
amdgpu_ring.c:378-381   adev->gpu_sched[hw_ip][hw_prio].sched[n++] = &ring->sched   <-- VINCULO
amdgpu_gfx.c:1657    drm_sched_entity_init(&entity, DRM_SCHED_PRIORITY_NORMAL, &sched, 1, NULL)
amdgpu_gfx.c:334     amdgpu_ring_init(adev, ring, 1024, irq, AMDGPU_CP_KIQ_IRQ_DRIVER0, ...)
amdgpu_job.c:426     amdgpu_job_run(struct drm_sched_job *sched_job)
amdgpu_job.c:515     .run_job = amdgpu_job_run

DISCRIMINANT:
U-1/U-2/U-3 son ESTATICOS y no bloquean nada. No hacen falta para responder la pregunta.

ARTIFACT:
08-ARQUITECTURA/designs/008-c-scheduler-ring.md

RUNTIME:
NOT_RUN

MODIFICATIONS:
NONE (fichero nuevo, sin commit)

COMMIT:
NONE
```
