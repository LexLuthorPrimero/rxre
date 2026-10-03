# 008-E — Cierre de los `NOT_DETERMINED` de 008-b/c/d y equivalencia `drm_dev` 7.1.3 ↔ 7.2.8

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 15
**Tipo**: `READ_ONLY/EVIDENCE` — análisis estático. Sin hardware, sin carga de módulos, sin commit.
**Árboles**: `RESEARCH/kernelbuild/linux-7.1.3` · `rx550-upstream-7.2.8/linux-7.2.8`
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, `008-a/b/c/d`, Q-5, cerrojo ajeno.

---

## 0. Resultado en una línea

**3 de 5 cerrados, 1 cerrado con corrección a mi propio artefacto, 1 `NOT_DETERMINED` con causa
estructural identificada.** La equivalencia `drm_dev` se cierra **parcialmente** y con un límite
que hay que decir en voz alta.

---

## 1. `008-b` U-1 — ¿Qué BAR usa la RX 550? → **`PROVEN`, y era BAR 5

```
amdgpu_device.c:3812   if (adev->asic_type >= CHIP_BONAIRE) {
amdgpu_device.c:3813       adev->rmmio_base = pci_resource_start(adev->pdev, 5);
amdgpu_device.c:3814       adev->rmmio_size = pci_resource_len(adev->pdev, 5);
amdgpu_device.c:3815   } else {
amdgpu_device.c:3816       adev->rmmio_base = pci_resource_start(adev->pdev, 2);
amdgpu_device.c:3817       adev->rmmio_size = pci_resource_len(adev->pdev, 2);
amdgpu_device.c:3818   }
amdgpu_device.c:3823   adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size);
```

La condición es `asic_type >= CHIP_BONAIRE`. `CHIP_POLARIS12` está por encima de Bonaire en la
enumeración de `chip.h`, y `vi_set_ip_blocks` lo confirma como ASIC de la familia VI
(`vi.c:2105-2108`). **La RX 550 usa BAR 5.** El fallback a BAR 2 es solo para ASICs
anteriores a Bonaire.

**Cierra el discriminante de `008-b` U-1**, que era estático y de bajo coste, como había anotado.

## 2. `008-b` U-2 — Semántica de `*_NO_KIQ` → **`PROVEN`, y no es lo que yo suponía

```
amdgpu.h:1284   #define RREG32_NO_KIQ(reg) amdgpu_device_rreg(adev, (reg), AMDGPU_REGS_NO_KIQ)
amdgpu.h:1285   #define WREG32_NO_KIQ(reg, v) amdgpu_device_wreg(adev, (reg), (v), AMDGPU_REGS_NO_KIQ)
amdgpu.h:1287   #define RREG32_KIQ(reg) amdgpu_kiq_rreg(adev, (reg), 0)
amdgpu.h:1288   #define WREG32_KIQ(reg, v) amdgpu_kiq_wreg(adev, (reg), (v), 0)
```

**La distinción NO es de ordenamiento de memoria.** Es **directo frente a encolado en la KIQ**:
`NO_KIQ` accede al registro MMIO directamente; `KIQ` emite la lectura/escritura como un comando en
la ring de la KIQ y espera. Son dos caminos de acceso **al mismo registro**, y la elección depende
del contexto (no se puede usar la KIQ desde dentro de la KIQ).

Mi `008-b` dejó esto como «semántica de caché y ordenamiento `NOT_DETERMINED`». Era un
`NOT_DETERMINED` mal planteado: la pregunta correcta era «directo o KIQ», y esa tiene respuesta
inmediata.

## 3. `008-c` U-1 — Puente `sched_job` → `ring` → **`PROVEN`, y confirma tu intuición

```
amdgpu_job.c:428   struct amdgpu_ring *ring = to_amdgpu_ring(sched_job->sched);
amdgpu_job.c:435   job = to_amdgpu_job(sched_job);
amdgpu_job.c:451   r = amdgpu_ib_schedule(ring, job->num_ibs, job->ibs, job, &fence);
amdgpu_job.c:459   fence = r ? ERR_PTR(r) : fence;
```

**La relación es de estructura de datos, no de llamada**: `drm_sched_job` contiene embebido
`sched`, y `to_amdgpu_ring()` lo convierte de vuelta a `amdgpu_ring`. Un grafo de llamadas no
puede expresar `to_amdgpu_ring(sched_job->sched)`: no hay llamada, hay un `container_of`.

Cadena completa, ahora cerrada:

```
drm_sched_entity_init(&entity, ...)        amdgpu_gfx.c:1657
   │
   ▼  el job del usuario se encola a esa entity
drm_sched_job  { ... sched; ... }           (el .sched embebido)
   │
   ▼  el core DRM invoca .run_job
amdgpu_job_run()                             amdgpu_job.c:426
   │  to_amdgpu_ring(sched_job->sched)       amdgpu_job.c:428   <-- container_of, NO llamada
   ▼
amdgpu_ib_schedule(ring, ...)                amdgpu_job.c:451
```

## 4. `008-d` — corrección a mi propio artefacto, en dos puntos

### 4.1 `amdgpu_fence_emit_polling` **no** es lo que escribí

En `008-d` escribí: *«existe una vía de fence por polling»* y lo presenté como mecanismo
alternativo a la IRQ. **Es un error mío.** Los seis llamadores son todos esperas de **registro
KIQ**, no progreso de fence visible:

```
amdgpu_gfx.c:1139    r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
amdgpu_gfx.c:1211    r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
amdgpu_gfx.c:1311    r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
gfx_v9_0.c:4227      r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
amdgpu_gmc.c:835     r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
amdgpu_gmc.c:887     r = amdgpu_fence_emit_polling(ring, &seq, MAX_KIQ_REG_WAIT);
```

Contexto de uno (`amdgpu_gfx.c:1138-1140`): se emite un `amdgpu_ring_emit_rreg()` y
**después** se hace polling para esperar a que el hardware termine esa lectura de registro. Es un
**spin-wait interno del driver** para leer un registro de la KIQ, no un sustituto de la
notificación de completion.

**Consecuencia**: el hecho que yo presenté como «mecanismo alternativo existente» **retira
evidencia** en lugar de aportarla. `P-8` no se estrecha por ahí.

### 4.2 `no_scheduler` no tiene nada que ver con IRQ

```
amdgpu_device.c:2235   if (!ring || ring->no_scheduler)  continue;   /* no setup del GPU scheduler */
amdgpu_xcp.c:601       if (!ring || !ring->sched.ready || ring->no_scheduler)  continue;
amdgpu_ring.c:378      if (!ring->no_scheduler && ...)  registrar en gpu_sched[ip][prio]
```

Los tres usos son **exclusión del registro en el scheduler de GPU**. Ninguno menciona IRQ. Son
conceptos independientes: `no_scheduler` decide si la ring entra en la cola de planificación, no si
el completion se notifica por interrupción.

**Mi `008-d` los lista como un indicador de «submit sin IRQ»**. No lo es.

### 4.3 Estado revisado de `P-8`

| Tramo | Antes | Corregido |
|---|---|---|
| SUBMIT EMISSION | posible sin IRQ | **sin cambios** — `amdgpu_job.c:451` escribe, no pasa por IRQ |
| IRQ DEPENDENCY | `NOT_DETERMINED` | **sin cambios** — `amdgpu_irq.c:345` la instala globalmente |
| FENCE PROGRESS | «existe vía sin IRQ» | **RETIRADO** — `amdgpu_fence_emit_polling` es spin-wait de registro KIQ |
| SCHEDULER | «evitable por diseño» | **reencuadrado** — `no_scheduler` es solo registro en scheduler, no IRQ |
| COMPLETION | `NOT_DETERMINED` | **sin cambios** |

**`P-8` sigue `NOT_DETERMINED`, y la evidencia disponible es MENOR de lo que `008-d` sugería.**
Ese es el resultado honesto de esta ronda: cerré los discriminantes y dos de ellos resultaron no
sostener la hipótesis que planteé. La ronda no avanzó `P-8`; lo depuró.

## 5. Equivalencia `drm_dev` entre 7.1.3 y 7.2.8 → **`PROVEN` parcial, con límite estructural

**Lo que sí se pudo verificar.**

```
$ ls rx550-upstream-7.2.8/linux-7.2.8/include/drm/drm_device.h
No existe el fichero o el directorio
$ find rx550-upstream-7.2.8/ -type f | wc -l
2842
$ find rx550-upstream-7.2.8/ -maxdepth 3 -type d
rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/...
```

**El árbol 7.2.8 del repo es una extracción parcial**: solo `drivers/gpu/drm/amd/`, 2842 ficheros.
**No contiene `include/drm/`.** Por tanto **el layout de `struct drm_device` NO se puede comparar**
con lo que hay en el repo. Eso es `NOT_DETERMINED` por falta del artefacto, no por dificultad.

**Lo que sí es comparable: el lado del driver.**

```
$ diff -w <(sed -n '2415,2455p' 7.1.3/amdgpu_drv.c) <(sed -n '2428,2468p' 7.2.8/amdgpu_drv.c)
>>> REGION IDENTICA (ignorando indentacion)
```

La región de `amdgpu_pci_probe()` alrededor de `drm_dev_register()` es **idéntica** entre 7.1.3
(caída en línea 2435) y 7.2.8 (línea 2448), incluyendo el reintento en `-EAGAIN` con
`msleep(5000)`, `amdgpu_xcp_dev_register()` y `amdgpu_amdkfd_drm_client_create()`. El fichero
entero difiere en 90 líneas, todas fuera de esa región.

**Clasificación**: el **uso que hace AMDGPU de la API de registro DRM es estable** entre 7.1.3 y
7.2.8. **El layout de `struct drm_device` es `NOT_DETERMINED`**, y el discriminante es concreto:
extraer `include/drm/` del tarball, cuyo sha256 está declarado e **coincide** en
`local.sha256` y `upstream.sha256` (`12e8d5a9…1941`) — el tarball es íntegro, **solo está
extraído parcialmente**.

## 6. Resumen

| Discriminante | Estado | Costo de cierre |
|---|---|---|
| `008-b` U-1: BAR efectivo | **`PROVEN`** — BAR 5 | cerrado |
| `008-b` U-2: semántica `NO_KIQ` | **`PROVEN`** — directo vs KIQ | cerrado |
| `008-c` U-1: `job_run` → ring | **`PROVEN`** — `container_of` | cerrado |
| `008-c` U-2: consumo de `gpu_sched[]` | `NOT_DETERMINED` | estático, bajo, **no necesario** para la pregunta |
| `008-c` U-3: nº de schedulers por IP | `NOT_DETERMINED` | estático, bajo, **no necesario** |
| `008-d` U-1: `fence_emit_polling` | **`PROVEN` con corrección** — solo esperas KIQ | cerrado, y **retira evidencia** |
| `008-d` U-2: `no_scheduler` ↔ IRQ | **`PROVEN` negativo** — ortogonal | cerrado, y **retira evidencia** |
| `008-d` U-3: despertar sin IRQ | `NOT_DETERMINED` | requiere IP doc o medición — **autorización** |
| `drm_dev` 7.1.3 ↔ 7.2.8 (uso del driver) | **`PROVEN`** | cerrado |
| `drm_dev` layout | `NOT_DETERMINED` | extraer `include/drm/` del tarball (sha256 verificado) |

**Balance**: `P-8` no se avanzó. La ronda lo que hizo fue **depurar la evidencia de `P-8`**, y el
resultado es que `008-d` era demasiado optimista en dos puntos. Eso es una mejora del estado

## 7. Correcciones pendientes a mis artefactos

Sin aplicar, porque el encargo vigente dice no modificarlos:

| Fichero | Corrección |
|---|---|
| `008-b` §5 | «semántica de caché y ordenamiento `NOT_DETERMINED`» -> la distinción es directo vs KIQ (`amdgpu.h:1284-1288`) |
| `008-b` §3 U-1 | BAR 5 para Polaris12, cerrado con `amdgpu_device.c:3812` |
| `008-d` §Evidence | `amdgpu_fence_emit_polling` no es una vía de fence alternativa; es spin-wait de registro KIQ |
| `008-d` §Classification | `no_scheduler` no es indicador de IRQ |
| `007` §5 | «mapa BAR / MMIO `NOT_DETERMINED`» → cerrado en `008-b` |
| `007` §5 | «`struct amdgpu_bo` `NOT_DETERMINED`» → cerrado en `008-a` |

## 8. Procedencia

Todo lo de este informe es `MEASURED` por lectura directa con `grep`/`sed`/`diff`, sobre
`RESEARCH/kernelbuild/linux-7.1.3` y `rx550-upstream-7.2.8/linux-7.2.8`. Ningún dato por
declaración, ninguno por inferencia de estilo. El árbol 7.2.8 es una extracción parcial y eso se
comprobó con `find`, no se supuso.

**RUNTIME**: `NOT_RUN`. **MODIFICATIONS**: un fichero nuevo. **COMMIT**: `NONE`.

---

```
STATUS: PROVEN      (008-b U-1, 008-b U-2, 008-c U-1, uso driver de drm_dev)
        PROVEN-NEG  (008-d U-1, 008-d U-2  -- cierran, pero retiran evidencia)
        NOT_DETERMINED  (008-c U-2, U-3, 008-d U-3, layout de struct drm_device)

EVIDENCE:
amdgpu_device.c:3812-3818   asic_type >= CHIP_BONAIRE -> BAR 5      (RX 550 usa BAR 5)
amdgpu.h:1284-1288         RREG32_NO_KIQ vs RREG32_KIQ -> directo vs encolado en KIQ
amdgpu_job.c:428           to_amdgpu_ring(sched_job->sched)        -> container_of, no llamada
amdgpu_gfx.c:1139,1211,1311 / gfx_v9_0.c:4227 / amdgpu_gmc.c:835,887
                           fence_emit_polling solo en esperas MAX_KIQ_REG_WAIT
amdgpu_device.c:2235 / amdgpu_xcp.c:601 / amdgpu_ring.c:378
                           no_scheduler == registro en gpu_sched, ortogonal a IRQ
7.1.3:2435 == 7.2.8:2448   drm_dev_register() identico con diff -w
7.2.8 sin include/drm/      2842 ficheros, solo drivers/gpu/drm/amd/

DISCRIMINANT:
008-c U-2/U-3 y 008-d U-3 siguen abiertos pero NO bloquean nada.
layout de drm_device -> extraer include/drm/ del tarball; sha256 local==upstream==12e8d5a9, integro

ARTIFACT:
08-ARQUITECTURA/designs/008-e-cierre-nd-y-equivalencia-drm-dev.md

RUNTIME:
NOT_RUN

MODIFICATIONS:
NONE (fichero nuevo, sin commit; 008-a/b/c/d y 007 sin modificar)

COMMIT:
NONE
```
