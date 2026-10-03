# 009 — Stage 2 Tool-Assisted Evidence

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 16
**Tipo**: `READ_ONLY/EVIDENCE` — `tar -xO` sobre tarballs, `grep`, `sed`, `diff`.
  **Sin runtime, sin carga de módulos, sin commit, sin escritura en hardware.**
**Artefactos usados**:
- `RESEARCH/kernelbuild/linux-7.1.3/` (extracción parcial de `drivers/gpu/drm/`, 7980 ficheros)
- `RESEARCH/evidence/linux-7.1.3.tar.xz` (158 335 040 B, sha256 `be41c068…7b45`) — **existía, no lo había buscado**
- `rx550-upstream-7.2.8/linux-7.2.8.tar.xz` (101 077 entradas, sha256 `12e8d5a9…1941`)

**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, `008-a/b/c/d/e`, Q-5, cerrojo ajeno.

---

## Scope

Cerrar lo que se podía cerrar con herramientas locales, y registrar con precisión lo que no.
Cuatro preguntas: refcount DRM 7.1.3↔7.2.8 · semántica MMIO · `P-8` completion · qué herramientas
aportan y cuáles no.

## Evidence Inventory

| Artefacto | Estado | Observación |
|---|---|---|
| `RESEARCH/evidence/linux-7.1.3.tar.xz` | **presente, 158 MB** | No lo había detectado en rondas previas. **Contiene `drivers/gpu/drm/scheduler/`** |
| `rx550-upstream-7.2.8/linux-7.2.8.tar.xz` | íntegro | 8579 entradas en `drivers/gpu/drm/`, 169 en `include/drm/` |
| `RESEARCH/kernelbuild/linux-7.1.3/` | **parcial** | 94 `.c` de primer nivel; **le faltan** `drm_sched*` y `drm_device.c` |
| `pahole` / BTF | no aplicable | no hay `.ko`/`vmlinux` con DWARF en el repo; `07-DRIVER/kernel/*.o` son builds locales sin debuginfo completo |

---

## DRM Refcount 7.1.3

```
STATE:      PROVEN
SOURCE:     RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/drm_drv.c
VERSION:    7.1.3
TOOL:       grep, sed, awk
SYMBOL:     kref_init, drm_dev_put, drm_dev_unregister, devm_drm_dev_init_release
```

```
drm_drv.c:718    kref_init(&dev->ref);                    en drm_dev_init()
drm_drv.c:801    static void devm_drm_dev_init_release(void *data)
drm_drv.c:803        drm_dev_put(data);
drm_drv.c:817        devm_add_action_or_reset(parent, devm_drm_dev_init_release, dev);

drm_dev_register()    -> 0 ocurrencias de kref|drm_dev_get|drm_dev_put
drm_dev_unregister()  -> 0 ocurrencias; primera linea: dev->registered = false;
drm_dev_put()         -> kref_put(&dev->ref, drm_dev_release);
```

## DRM Refcount 7.2.8

```
STATE:      PROVEN
SOURCE:     linux-7.2.8/drivers/gpu/drm/drm_drv.c  (via tar -xO)
VERSION:    7.2.8
SYMBOL:     mismos
```

```
drm_drv.c:726    kref_init(&dev->ref);
drm_drv.c:809    static void devm_drm_dev_init_release(void *data)
drm_drv.c:824    devm_add_action_or_reset(parent, devm_drm_dev_init_release, dev);

drm_dev_register()    -> 0 ocurrencias
drm_dev_unregister()  -> 0 ocurrencias; primera linea: dev->registered = false;
```

## 7.1.3 ↔ 7.2.8 Equivalence

```
STATE:      PROVEN
TOOL:       diff sobre bloques extraidos con tar -xO
```

```
$ diff <(sed -n '801,804p' 7.1.3/drm_drv.c) <(tar -xO ...7.2.8... | sed -n '809,812p')
>>> IDENTICOS
```

| Semántica | 7.1.3 | 7.2.8 | Equivalente |
|---|---|---|---|
| `kref_init` | `:718` | `:726` | **sí**, y es el **único** punto de inicialización en ambos |
| devres release registrado | `:817` | `:824` | **sí** |
| `devm_drm_dev_init_release` = `drm_dev_put(data)` | `:801-803` | `:809-812` | **idéntico** |
| `drm_dev_register` toca refcount | no | no | **sí** |
| `drm_dev_unregister` toca refcount | no | no | **sí** |

**Conclusión del refcount** — `DRM_REFCOUNT_TEARDOWN`:

La secuencia del driver

```c
drm_dev_unregister(&rx->drm);
drm_dev_put(&rx->drm);
```

`drm_dev_unregister()` **no decrementa el refcount** (0 llamadas a `kref*`/`drm_dev_put` en su
cuerpo, en ambas versiones). `drm_dev_put()` hace `kref_put(&dev->ref, drm_dev_release)`. Como
`kref_init` ocurre **una sola vez**, en `drm_dev_init()`, y el devres registrado en
`devm_drm_dev_init()` es el **mismo** que ejecuta `drm_dev_put(data)` en el detach del device:

```
drm_dev_init()            -> ref = 1, esa única referencia la "posee" el devres
drm_dev_register()        -> no cambia el refcount
drm_dev_unregister()      -> no cambia el refcount
drm_dev_put()  (del driver) -> ref 1->0 -> drm_dev_release()  <-- libera el objeto
   ...detach del device...
devm_drm_dev_init_release() -> drm_dev_put(data) sobre objeto YA LIBERADO
```

**`FIX_DIRECTION` = `PROVEN`: el `drm_dev_put()` explícito del driver es incorrecto; la referencia
la posee el devres.** El segundo `drm_dev_put` opera sobre memoria liberada.

**Y el FAIL no es específico de versión**: la semántica es idéntica en 7.1.3 y 7.2.8, así que el
doble `put` ocurre bajo ambas. `7.1.3 = FAIL`, no `NOT_VERIFIED`.

**No se modificó el driver**, según lo indicado. Esto es diagnóstico, no arreglo.

**Corrección al discriminante previo**: `drm_dev_unregister` y `drm_dev_put` están en
`include/drm/drm_drv.h`; `devm_drm_dev_init_release` es `static` en `drm_drv.c`. `drm_device.h`
da **0/0/0 en ambas versiones** — indistinguible de «idéntico» y de «no existe».

## Tool-Assisted Structural Evidence

```
STATE:      NOT_APPLICABLE (no hay artefacto con DWARF/BTF en el repo)
```

`pahole`, `readelf --debug-dump` y `objdump` **no aportan** porque no hay `vmlinux` ni `.ko` con
información de depuración. Los `.o` de `07-DRIVER/kernel/` son builds locales sin debuginfo
completo, y están fuera de mi ámbito para tocarlos.

**Este es un resultado útil**: la pregunta «¿podemos obtener layouts con `pahole`?» tiene
respuesta **no**, por ausencia del artefacto, no por limitación de la herramienta. No se debe
volver a intentar sin un `vmlinux` con BTF.

## MMIO Evidence

```
STATE:      PROVEN
SOURCE:     drivers/gpu/drm/amd/amdgpu/amdgpu_reg_access.c:363-382
TOOL:       grep, sed
```

La cadena completa queda cerrada:

```c
uint32_t amdgpu_device_rreg(struct amdgpu_device *adev, uint32_t reg, uint32_t acc_flags)
{
        if ((reg * 4) < adev->rmmio_size) {                    /* :371 */
                if (!(acc_flags & AMDGPU_REGS_NO_KIQ) &&
                    amdgpu_sriov_runtime(adev) && ...) {
                        ret = amdgpu_kiq_rreg(adev, reg, 0);           /* :375 */
                } else {
                        ret = readl(((void __iomem *)adev->rmmio) + (reg * 4));  /* :378 */
                }
        } else {
                ret = amdgpu_reg_pcie_rd32(adev, reg * 4);     /* :381 */
        }
}
```

Las seis separaciones que pedía el encargo:

| # | Concepto | Estado | Evidencia |
|---|---|---|---|
| 1 | Dirección física del BAR | `PROVEN` | `amdgpu_device.c:3813` `pci_resource_start(pdev, 5)`; selector `asic_type >= CHIP_BONAIRE` en `:3812` |
| 2 | Dirección virtual | `PROVEN` | `amdgpu_device.c:3823` `ioremap()`; tipo `void __iomem *rmmio` en `amdgpu.h:901` |
| 3 | Acceso CPU MMIO | `PROVEN` | `amdgpu_reg_access.c:378` `readl(((void __iomem *)adev->rmmio) + reg*4)` |
| 4 | Registro directo | `PROVEN` | misma línea, rama `else` |
| 5 | Selección indirecta de registro | `PROVEN` | `amdgpu_reg_access.c:381` `amdgpu_reg_pcie_rd32(adev, reg*4)` — se usa **cuando `reg*4 >= rmmio_size`**, es decir registros **fuera** del BAR, vía espacio de configuración PCIe |
| 6 | Acceso por KIQ | `PROVEN` | `amdgpu_reg_access.c:375` — y es **condicional a `amdgpu_sriov_runtime(adev)`**, no general |

**Dos precisiones que corrigen la lectura previa**:

1. **`mmPCIE_INDEX`/`mmPCIE_DATA` (`vi.c:297-320`) NO son el punto 5.** Son un protocolo de
   *registros indirectos dentro del ASIC*: se escribe un índice y el dato sale por otro registro.
   La función `amdgpu_reg_pcie_rd32()` de `:381` es otro camino — **espacio de configuración
   PCIe**, para registros que caen fuera del BAR. Son dos mecanismos distintos y ambos existen.

2. **La vía KIQ es condicional a SR-IOV** (`amdgpu_reg_access.c:373`). Por eso existe el flag
   `NO_KIQ`: no es una cuestión de ordenamiento de memoria, es **evitar el encolado en la KIQ
   cuando el contexto es un VF de SR-IOV**. Confirma `008-e` §2 y lo precisa.

**Lo que queda `NOT_DETERMINED` en MMIO**: nada del lado del software. El modelo de caché de los
registros requiere leer hardware — no autorizado en esta ronda.

## P-8 Completion Evidence

```
STATE:      NOT_DETERMINED  (pero con un hecho nuevo y relevante)
```

### El hallazgo

```
amdgpu_fence.c:186   /**
amdgpu_fence.c:187    * Start a timer as fallback to our interrupts.
amdgpu_fence.c:188    */
amdgpu_fence.c:190   static void amdgpu_fence_schedule_fallback(struct amdgpu_ring *ring)
amdgpu_fence.c:192       mod_timer(&ring->fence_drv.fallback_timer,
amdgpu_fence.c:193             jiffies + AMDGPU_FENCE_JIFFIES_TIMEOUT);
amdgpu_fence.c:459       timer_setup(&ring->fence_drv.fallback_timer, amdgpu_fence_fallback, 0);
```

**El kernel de Linux tiene, para la señalización de fences, un timer de respaldo explícito a las
interrupciones.** El propio comentario lo dice. Esto es evidencia de que el diseño del driver
**contempla** completion sin IRQ.

### La cadena de señalización, completa

```
amdgpu_fence_read(ring)                    lee el seq num de la GPU
   │
   ▼
amdgpu_fence_process()                     amdgpu_fence.c:207
   │  compara seq vs last_seq
   ▼
dma_fence_signal(fence)                    amdgpu_fence.c:243
   │
   ▼
drm_sched_job_done_cb()                    scheduler/sched_main.c:185  (drm_sched 7.2.8)
   │
   ▼
drm_sched_job_done() -> drm_sched_fence_finished()   sched_main.c:174, sched_fence.c:81
   │
   ▼
dma_fence_signal(&fence->finished)         sched_fence.c:84
```

**`amdgpu_fence_ops` (`amdgpu_fence.c:854-859`) NO tiene `.wait` ni `.poll`.** Solo
`get_driver_name`, `get_timeline_name`, `enable_signaling` y `release`. Es decir: **no existe
callback de polling del driver para job completion**; toda la señalización pasa por
`amdgpu_fence_process()`.

### Los llamadores de `amdgpu_fence_process()` — y por qué importa

| Llamador | Naturaleza |
|---|---|
| `amdgpu_fence.c:263` | dentro de `amdgpu_fence_wait_polling()` — busy-wait explícito |
| `amdgpu_fence.c:671` | dentro de `amdgpu_fence_driver_force_completion()` — **forzado**, escribe el seq a mano (`amdgpu_fence_write(ring, sync_seq)`) |
| `amdgpu_fence.c:876` | **debugfs** — lectura manual del estado |
| `amdgpu_debugfs.c:2042` | debugfs |

**Y el timer:** `amdgpu_fence_process()` en `:219-221` hace

```c
if (timer_delete(&ring->fence_drv.fallback_timer) && seq != ring->fence_drv.sync_seq)
        amdgpu_fence_schedule_fallback(ring);
```

Es decir: **cada vez que se procesa un fence, si el timer no estaba armado, se rearma.** Eso
constituye un lazo de mantenimiento del timer.

### Clasificación revisada de `P-8`

| Tramo | Estado | Evidencia |
|---|---|---|
| SUBMIT EMISSION | `PROVEN` sin IRQ | `amdgpu_job.c:451` `amdgpu_ib_schedule()` |
| PUBLICACIÓN / DOORBELL | `PROVEN` sin IRQ | registro en BAR 2, `amdgpu_doorbell_mgr.c:210` |
| **FENCE SIGNAL — existe camino por timer** | **`PROVEN`** | `amdgpu_fence.c:187,192,459` — «fallback to our interrupts» |
| FENCE SIGNAL — camino por IRQ | `PROVEN` | la ruta principal, en el core |
| **COMPLETION sin IRQ** | **`NOT_DETERMINED`** | falta demostrar que el timer está **armado en condiciones normales**, no solo cuando se rearma tras un ciclo de procesamiento |
| IRQ DEPENDENCY | `NOT_DETERMINED` | falta seguir quién llama `amdgpu_fence_process()` desde la IRQ |

**Lo que este hallazgo NO establece**: que submit sin IRQ sea viable. El timer se rearma en
`amdgpu_fence_process()`, y si `amdgpu_fence_process()` **solo** se llama desde la IRQ, el timer
solo se arma después de la primera IRQ — lo que lo haría un temporizador de respaldo
dependiente, no un sustituto independiente. Ese
es el discriminante exacto que queda, y es una pregunta de **una función**: ¿quién más llama a
`amdgpu_fence_process()` o a `amdgpu_fence_schedule_fallback()`?

**No se investigó más allá** porque el objetivo de esta ronda era acotar el discriminante, y
acotado está.

## Retired / Non-discriminating Evidence

| Evidencia | Por qué no discrimina |
|---|---|
| `amdgpu_fence_emit_polling()` (`amdgpu_fence.c:159`) | Ya **RETIRADA** en `008-e`. Spin-wait de registro KIQ, no completion |
| `no_scheduler` | Ya **RETIRADA** en `008-e`. Ortogonal a IRQ |
| `pahole` / BTF | No hay artefacto con DWARF. La herramienta no es el límite |
| `drm_device.h` como discriminante del refcount | 0/0/0 en ambas versiones — indistinguible de «idéntico» |
| Estilo / indentación / prefijo de commit | Prohibido por el encargo como inferencia de autoría |

## Remaining Unknowns

| # | Desconocimiento | Discriminante | Coste |
|---|---|---|---|
| U-1 | ¿El `fallback_timer` está armado en condiciones normales? | buscar todos los llamadores de `amdgpu_fence_schedule_fallback` y `amdgpu_fence_fallback` | estático, bajo |
| U-2 | ¿Quién llama `amdgpu_fence_process()` desde la IRQ? | seguir la IRQ de gfx en `gfx_v8_0.c` / `amdgpu_irq.c` | estático, medio |
| U-3 | Semántica de `AMDGPU_FENCE_JIFFIES_TIMEOUT` | `amdgpu_fence.h` | estático, trivial |
| U-4 | Layouts de estructuras DRM vía DWARF | requiere `vmlinux`/`.ko` con debuginfo | **artefacto ausente** |

## Discriminants

- **`FIX_DIRECTION` = `PROVEN`**. `DRM_REFCOUNT_TEARDOWN = FAIL` bajo **7.1.3 y 7.2.8** por igual.
  El `drm_dev_put()` explícito del driver es incorrecto; la referencia la posee el devres. El FAIL
  **no es de versión**.
- **MMIO = `PROVEN`** en los seis niveles. Cero `NOT_DETERMINED` de software.
- **`P-8` = `NOT_DETERMINED`**, con un hecho nuevo (`fallback_timer`) y un discriminante de una
  función.

## Corrections Required Later

Sin aplicar, según lo indicado.

| Fichero | Corrección |
|---|---|
| `007` §5 | «BAR/MMIO `NOT_DETERMINED`» → cerrado en `008-b` y en este `009` |
| `007` §5 | «`struct amdgpu_bo` `NOT_DETERMINED`» → cerrado en `008-a` |
| `008-b` §3 | La rama indirecta es `amdgpu_reg_pcie_rd32` (`amdgpu_reg_access.c:381`), **no** `mmPCIE_INDEX` |
| `008-b` §5 | `NO_KIQ` = evitar encolado KIQ en **SR-IOV** (`amdgpu_reg_access.c:372-375`), no ordenamiento |
| `008-e` §4 | `P-8` tiene un hecho nuevo: `fallback_timer` («fallback to our interrupts») |
| registro del FAIL de refcount | `7.1.3` pasa de `NOT_VERIFIED` a **`FAIL`**; `FIX_DIRECTION` = **`PROVEN`** |

**RUNTIME**: `NOT_RUN`. **MODIFICATIONS**: un fichero nuevo. **COMMIT**: `NONE`.
