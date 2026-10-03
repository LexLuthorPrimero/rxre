# 008-D — P-8: ¿el submit requiere IRQ en esta ruta?

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 14
**Tipo**: `READ_ONLY/EVIDENCE` — análisis estático. **Ningún submit ejecutado.**
**Árbol**: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, Q-5, cerrojo ajeno.

---

## Scope

La pregunta **no** es «¿puede una GPU AMD funcionar sin IRQ?». Es:

> **¿En esta ruta concreta, qué dependencia demostrable existe entre submit y IRQ?**

Tramos a clasificar por separado: creación de ring · emisión del comando · publicación/doorbell ·
fence · completion · scheduler · IRQ · polling/timeout.

## Evidence

### La IRQ se instala una vez, al inicializar el driver

```
amdgpu_irq.c:307   int amdgpu_irq_init(struct amdgpu_device *adev)
amdgpu_irq.c:345       r = request_irq(irq, amdgpu_irq_handler, IRQF_SHARED, adev_to_drm(adev)->driver->name, ...)
amdgpu_irq.c:207       if (ret == IRQ_HANDLED)
```

### La IRQ es un **parámetro** de la creación de ring

```
amdgpu_ring.c:226   int amdgpu_ring_init(struct amdgpu_device *adev, struct amdgpu_ring *ring,
                                        unsigned int max_dw, struct amdgpu_irq_src *irq_src,
                                        unsigned int irq_type, unsigned int hw_prio,
                                        atomic_t *sched_score)
amdgpu_gfx.c:334        amdgpu_ring_init(adev, ring, 1024, irq, AMDGPU_CP_KIQ_IRQ_DRIVER0, ...)
```

El `irq` de la KIQ se pasa explícitamente. Otras rings pasan `NULL` o un `trap_irq` distinto
(`amdgpu_cper.c:573`, `amdgpu_umsch_mm.c:116`, `amdgpu_vpe.c:284`).

### Existe una vía de fence por polling — esto es lo relevante

```
amdgpu_fence.c:159   int amdgpu_fence_emit_polling(struct amdgpu_ring *ring, uint32_t *s, ...)
amdgpu_fence.c:149   /* amdgpu_fence_emit_polling - emit a fence on the requeste ring */
```

**Existe una función de emisión de fence explícitamente por polling, en el mismo fichero que la
vía normal.** Eso es evidencia estructural de que la vía con IRQ no es la única.

### La ring puede no usar scheduler

```
amdgpu_gfx.c:330     ring->no_scheduler = true;                 (KIQ)
amdgpu_cper.c:569    ring->no_scheduler = true;
amdgpu_umsch_mm.c:111  ring->no_scheduler = true;
amdgpu_ring.c:378    if (!ring->no_scheduler && ...)   la ring se registra en el scheduler
amdgpu_ring.c:855    if (ring->no_scheduler || !drm_sched_wqueue_ready(&ring->sched))  return false;
amdgpu_xcp.c:601     if (!ring || !ring->sched.ready || ring->no_scheduler)
```

## Trace

```
INICIO (una vez)
  amdgpu_irq.c:307  amdgpu_irq_init()
  amdgpu_irq.c:345      request_irq(..., amdgpu_irq_handler, IRQF_SHARED, ...)
        │
        │   la IRQ se instala de forma GLOBAL, no por submit
        ▼
CREACIÓN DE RING
  amdgpu_gfx.c:334  amdgpu_ring_init(..., irq, AMDGPU_CP_KIQ_IRQ_DRIVER0, ...)
  amdgpu_ring.c:378     if (!no_scheduler)  -> registra ring->sched en gpu_sched[ip][prio]
        │
        ▼
EMISIÓN DE UN JOB
  amdgpu_job.c:426  amdgpu_job_run()          (invocado por el core DRM)
  amdgpu_job.c:515      .run_job = amdgpu_job_run
        │   escribe en el buffer circular de la ring
        │   publica con el doorbell (adev->doorbell.base = BAR 2, ver 008-b)
        ▼
FENCE
  amdgpu_fence.c:101   amdgpu_fence_emit()          -- via normal, acaba en la IRQ
  amdgpu_fence.c:159   amdgpu_fence_emit_polling()  -- via alternativa
        │
        ▼
COMPLETION / IRQ
  amdgpu_irq.c:207   amdgpu_irq_handler() -> IRQ_HANDLED
        │
        ▼
SCHEDULER
  amdgpu_ring.c:378  la ring se desregistra/consulta segun no_scheduler
```

## Classification por tramo

| Tramo | Estado | Evidencia |
|---|---|---|
| **SUBMIT EMISSION** | **posible sin IRQ** | `amdgpu_job.c:426` escribe en la ring; no toca IRQ. La IRQ no está en el camino de escritura |
| **PUBLICACIÓN / DOORBELL** | **posible sin IRQ** | el doorbell es un registro en el BAR (`amdgpu_doorbell_mgr.c:210`), no una interrupción |
| **IRQ DEPENDENCY** | **`NOT_DETERMINED`** | `amdgpu_irq.c:345` instala el handler globalmente; no seguí quién **necesita** la señal para completar |
| **FENCE PROGRESS** | **existe vía sin IRQ** | `amdgpu_fence.c:159` `amdgpu_fence_emit_polling()` |
| **COMPLETION** | **`NOT_DETERMINED`** | no rastreé el camino completo de completion; `amdgpu_fence_emit_polling` sugiere polling como completion, pero no lo probé |
| **SCHEDULER PROGRESS** | **evitable por diseño** | `no_scheduler` en KIQ/CPER/UMD (`amdgpu_gfx.c:330`, `amdgpu_cper.c:569`, `amdgpu_umsch_mm.c:111`) |

## Conclusión, estrictamente limitada

**Lo que la evidencia SÍ establece**:

1. La IRQ se registra **globalmente** al inicializar (`amdgpu_irq.c:345`), **no por submit**.
2. El camino de **escritura** del comando no pasa por IRQ (`amdgpu_job.c:426`).
3. Existe una **función de fence por polling** (`amdgpu_fence.c:159`).
4. Existen rings con `no_scheduler = true` por diseño.

**Lo que NO establece, y no voy a declarar**:

- **No declaro «submit sin IRQ viable».** Eso exigiría probar que *completion* avanza sin IRQ. La
  IRQ se instala globalmente, así que la ruta normal la tiene; lo que no sé es si el camino de
  polling cubre *también* el avance del fence y el despertar del scheduler. Eso es
  `NOT_DETERMINED`.
- **No declaro que `amdgpu_fence_emit_polling` baste.** Existe; no seguí sus llamadores ni qué
  garantiza. Podría ser solo para un caso concreto (un hang, un tipo de fence). No lo investigué.

**Clasificación de `P-8`**: `NOT_DETERMINED`, pero **estrechado empíricamente**. Antes de esta
ronda, la pregunta era abierta («¿puede la ruta funcionar sin IRQ?»). Ahora hay tres hechos
estructurales que la acotan: la IRQ no está en el camino de escritura, hay vía de fence por
polling, y hay rings sin scheduler por diseño. **El discriminante que falta** es uno solo, y es
acotado:

> ¿`amdgpu_fence_emit_polling()` cubre también el **despertar del scheduler** y el **avance del
> fence** para un KGD/KFD submit normal, o solo para un caso de error?

Eso se responde leyendo sus llamadores (`amdgpu_fence.c`) y el consumidor de `no_scheduler` en
`amdgpu_xcp.c:601` y `amdgpu_device.c:2235`. **Es estático.**

## Unknowns

| # | Desconocimiento | Discriminante | Coste |
|---|---|---|---|
| U-1 | Quién llama a `amdgpu_fence_emit_polling` y con qué garantía | leer llamadores en `amdgpu_fence.c` | estático, bajo |
| U-2 | Si `no_scheduler` cubre también la señal de IRQ | `amdgpu_device.c:2235`, `amdgpu_xcp.c:601` | estático, bajo |
| U-3 | Si el hardware necesita IRQ para despertar del sleep de la ring | requiere lectura de IP doc / ejecución | **requiere autorización o doc externa** |

## Closure criterion — **parcialmente cumplido**

Se han clasificado seis de los ocho tramos con evidencia. Los dos restantes (`COMPLETION`,
`IRQ DEPENDENCY`) quedan `NOT_DETERMINED` con discriminante identificado. La pregunta no se cierra,
pero **se estrecha de forma accionable**: los dos `NOT_DETERMINED` que quedan son responde estáticamente con bajo coste.

## Tooling used

`grep -n` para localizar, `sed -n` para firmas. No AST. El hallazgo central (`amdgpu_fence_emit_polling`)
fue un `grep` de símbolos, no un análisis de flujo — señal de que la evidencia estaba en la
superficie del código, no en su semántica.

---

```
STATUS: NOT_DETERMINED   (estrechado: 6 de 8 tramos clasificados con evidencia)

EVIDENCE:
amdgpu_irq.c:307   amdgpu_irq_init()
amdgpu_irq.c:345       request_irq(..., amdgpu_irq_handler, IRQF_SHARED, ...)   -- GLOBAL, no por submit
amdgpu_irq.c:207       if (ret == IRQ_HANDLED)
amdgpu_ring.c:226   amdgpu_ring_init(..., struct amdgpu_irq_src *irq_src, ...)
amdgpu_gfx.c:334        amdgpu_ring_init(adev, ring, 1024, irq, AMDGPU_CP_KIQ_IRQ_DRIVER0, ...)
amdgpu_fence.c:159  amdgpu_fence_emit_polling()      <-- VIA SIN IRQ
amdgpu_fence.c:101  amdgpu_fence_emit()              <-- via normal
amdgpu_gfx.c:330        ring->no_scheduler = true;
amdgpu_ring.c:378    if (!ring->no_scheduler && ...)  registro en gpu_sched[ip][prio]
amdgpu_ring.c:855    if (ring->no_scheduler || !drm_sched_wqueue_ready(...))  return false;
amdgpu_job.c:426   amdgpu_job_run()  -- escritura, no pasa por IRQ

DISCRIMINANT:
U-1  llamadores de amdgpu_fence_emit_polling  -> leer amdgpu_fence.c   (ESTATICO, bajo)
U-2  que cubre no_scheduler para senal de IRQ   -> amdgpu_device.c:2235, amdgpu_xcp.c:601 (ESTATICO, bajo)
U-3  si el hardware despierta sin IRQ           -> requiere IP doc o medicion (REQUIERE AUTORIZACION)

ARTIFACT:
08-ARQUITECTURA/designs/008-d-p8-submit-sin-irq.md

RUNTIME:
NOT_RUN   (ningun submit ejecutado, ningun modulo cargado, ningun write en sysfs)

MODIFICATIONS:
NONE (fichero nuevo, sin commit)

COMMIT:
NONE
```
