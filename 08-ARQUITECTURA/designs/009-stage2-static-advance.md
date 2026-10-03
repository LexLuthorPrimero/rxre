# 009 — Stage 2 static advance

`STATIC_IMPLEMENTATION` / `READ_ONLY-EVIDENCE` · 2026-09-29 · host `7.1.3-200.nobara.fc44.x86_64` · GPU
identificada por identidad PCI `1002:699f`, nunca por nombre de nodo.

Sin commits. Sin runtime. `07-DRIVER/kernel/*` intacto.

## Resultado por pista

| Pista | Estado | Discriminante mínimo restante |
|---|---|---|
| A · DRM 7.1.3 | `PROVEN` — encontrado y leído | ninguno |
| B · MMIO_MAPPING | `SUPPORTED` — 3 rutas delimitadas | semántica de caché/acceso |
| C · U-1/U-2/U-3 | `PROVEN` (U-1, U-2) / `SUPPORTED` (U-3) | `num_scheds` para Polaris12 en runtime |
| D · P-8 | `NOT_DETERMINED` — con frontera delimitada | ver §5 |

---

## Pista A — `DRM_REFC_SEMANTICS` de 7.1.3: `PROVEN`

`FIX_DIRECTION` queda **determinado**. La fuente que yo había declarado ausente estaba en la
host, y la había declarado ausente buscando el nombre equivocado de fichero en un árbol
equipo equivocado.

**Artefacto encontrado**, `RESEARCH/kernelbuild/linux-7.1.3/`, dentro del propio proyecto:

| Dato | Valor |
|---|---|
| versión declarada | `VERSION=7 PATCHLEVEL=1 SUBLEVEL=3` (`Makefile`) |
| fichero | `drivers/gpu/drm/drm_drv.c` |
| sha256 | `aefc9af7a9f8e6db0282ee4bc923e32b90842e6c2f2900d270e1bf498cb12c3c` |
| 7.2.8, sha256 | `d55f9190e0a17538…` (`linux-7.2.8/drivers/gpu/drm/drm_drv.c`) |

**Comparación por bloque, no por versión.** Los tres bloques que deciden el teardown son
**byte a byte idénticos** entre 7.1.3 y 7.2.8:

| Bloque | 7.1.3 | 7.2.8 | sha256 del bloque (ambos) |
|---|---|---|---|
| `drm_dev_get` + `drm_dev_put` | :932-958 | :939-965 | `464d8d38235974e2` |
| `drm_dev_unregister` | :1148-1163 | :1164-1185 | `162e73409f28af7d` |
| `__devm_drm_dev_alloc` | :820-842 | :828-850 | idénticos, 494 B |

`diff` de los tres: vacío.

Semántica, con líneas de **7.1.3**:

| Operación | Línea 7.1.3 | Efecto en refcount |
|---|---|---|
| `kref_init(&dev->ref)` en `drm_dev_init` | `drm_drv.c:718` | 0 → 1 |
| `devm_add_action_or_reset(parent, devm_drm_dev_init_release, dev)` | `drm_drv.c:816-817` | registra unwind |
| `devm_drm_dev_init_release() { drm_dev_put(data); }` | `drm_drv.c:801-804` | 1 → 0 al desenrollar |
| `drm_dev_register()` | — | **no toca refcount** (0 ocurrencias de `kref_`) |
| `drm_dev_unregister()` | `drm_drv.c:1148-1163` | **no toca refcount** (cuerpo sin `kref_put`) |
| `drm_dev_put()` | `drm_drv.c:947-951` | `kref_put` sin guarda |

Contrato textual, `7.1.3 drm_drv.c:1138-1142`, literal:

> "The caller must call `drm_dev_put()` to drop their final reference, **unless it is managed
> with devres (as devices allocated with `devm_drm_dev_alloc()` are), in which case there is
> already an unwind action registered**."

Confirmación independiente, `7.1.3 drm_drv.c:424-437`: `drm_put_dev()` existe **precisamente**
para el par `unregister` + `put`, es decir el caso no-devm.

`__devm_drm_dev_alloc()` retorna `container`, `7.1.3 drm_drv.c:835-841`:
`container = kzalloc(size); drm = container + offset; …; return container;`

**Consecuencia:** `FAIL (doble drm_dev_put)` **deja de ser `EXTERNAL`**. Válido sobre la
semántica de 7.1.3, la que ejecutaría el módulo. `FIX_DIRECTION = DETERMINED`: eliminar el
`drm_dev_put()` explícito de `rx550_remove()`. Sigue sin aplicarse: `CODE_CHANGE` requiere
autorización de escritura en `07-DRIVER/kernel/*`.

Refutación que lo tumbaría: que el bloque del unwind no se ejecutara. `devm_add_action_or_reset`
está registrado sobre el `struct device` padre y se dispara al desvinculación, después de que
`.remove()` regrese; `remove()` no lo cancela.

### CORRECTION_CANDIDATE

→ `07-DRIVER/kernel/STAGE1-SUBSYSTEMS.md` · §"Estado" y el bloque `RUNTIME=NOT_RUN`
→ afirmación actual: no registra `DRM_REFCOUNT_TEARDOWN`; el hallazgo vive sólo en conversación
→ evidencia nueva: la anterior, esta sección
→ estado correcto: incluir el `FAIL` con su cadena de 7.1.3 y la afirmación refutada
  ("`drm_dev_register()` hace `kref_get` y lleva 1→2") marcada como `REFUTED`, porque el
  `kref_get` de `drm_drv.c:934` pertenece a `drm_dev_get()`

---

## Pista B — semántica de acceso MMIO: `SUPPORTED`

Árbol `linux-7.2.8`, `drivers/gpu/drm/amd/amdgpu/`. Este árbol tiene amdgpu completo
(`sha256 amdgpu_reg_access.c = 60ee0b99d513c67b`, `amdgpu_device.c = f1bcaa703df662e2`).

### B.1 El origen de `rmmio` — `FACT`

`amdgpu_device.c:3993-4006`:

```c
if (adev->asic_type >= CHIP_BONAIRE) {
	adev->rmmio_base = pci_resource_start(adev->pdev, 5);
	adev->rmmio_size = pci_resource_len(adev->pdev, 5);
} else {
	adev->rmmio_base = pci_resource_start(adev->pdev, 2);
	adev->rmmio_size = pci_resource_len(adev->pdev, 2);
}
…
adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size);
```

`FACT`, con la condición explícita en el código: `asic_type >= CHIP_BONAIRE` ⇒ **BAR 5**.
Polaris12 está en ese caso, y la ruta de BAR 5 es la que se usa. Coherente con el
`OBSERVED` de Stage 1 (BAR 5 presente, `0xf7d00000`, 4 implementados de 6).

`ioremap()` se llama **una vez**, sobre el BAR completo. No hay lista blanca, no hay
`pci_iomap_range()`, no hay un mapeo por registro. `IOREMAP` es el único origen de
`adev->rmmio`.

Lo que esto **no** demuestra: la semántica de `readl`/`writel` sobre esa región. `ioremap()`
no la declara; la función de mapeo se elige con `ioremap()` a secas, sin
`ioremap_cache()` ni `ioremap_wc()`. `UNKNOWN`, y es el discriminante que mantiene
`MMIO_MAPPING` bloqueado.

### B.2 Las tres rutas de acceso — `FACT`

`amdgpu_reg_access.c:363-386`, `amdgpu_device_rreg()`:

```c
if ((reg * 4) < adev->rmmio_size) {
	if (!(acc_flags & AMDGPU_REGS_NO_KIQ) &&
	    amdgpu_sriov_runtime(adev) &&
	    down_read_trylock(&adev->reset_domain->sem)) {
		ret = amdgpu_kiq_rreg(adev, reg, 0);        /* ruta KIQ  */
		up_read(&adev->reset_domain->sem);
	} else {
		ret = readl(((void __iomem *)adev->rmmio) + (reg * 4));  /* MMIO directo */
	}
} else {
	ret = amdgpu_reg_pcie_rd32(adev, reg * 4);       /* protocolo indirecto */
}
```

Cadena completa, con el punto exacto donde se separan:

```
PCI BAR 5
   │  pci_resource_start/len, ioremap()          amdgpu_device.c:3996,4006
   ▼
adev->rmmio   (void __iomem *)
   │
   ├─── reg*4 < rmmio_size ─────────────────────► readl(rmmio + reg*4)      CPU DIRECTO
   │    (ruta mayoritaria: la ventana completa del BAR es direccionable)
   │
   ├─── reg*4 >= rmmio_size ────────────────────► amdgpu_reg_pcie_rd32()
   │                                                     │
   │                                            soc15.c:937 → pcie.rreg = amdgpu_device_indirect_rreg
   │                                                     │
   │                                     amdgpu_reg_access.c:590-608:
   │                                       writel(reg_addr, rmmio + pcie_index*4)
   │                                       readl(rmmio + pcie_index*4)
   │                                       r = readl(rmmio + pcie_data*4)
   │                                       [spin_lock_irqsave sobre adev->reg.pcie.lock]
   │                                                     ▼
   │                                          PROTOCOLO INDIRECTO  (mmPCIE_INDEX/mmPCIE_DATA)
   │
   └─── !NO_KIQ && amdgpu_sriov_runtime && trylock ──► amdgpu_kiq_rreg()
                                                          amdgpu_gfx.c:1131-1160
                                                          emite RREG al ring KIQ
                                                          amdgpu_fence_emit_polling(ring, &seq, …)
                                                          espera el valor en VRAM
```

**Qué queda demostrado:**

1. La ventana del BAR es direccionable de forma directa, y ese es el camino por defecto.
   No hace falta KIQ ni mmPCIE para un registro dentro de `rmmio_size`.
2. El protocolo indirecto mmPCIE existe y sirve para registros **fuera** de la ventana
   del BAR. Escritura a `pcie_index`, lectura de vuelta del índice (handshake), lectura de
   `pcie_data`. Serializado con `spin_lock_irqsave` sobre `adev->reg.pcie.lock` — el
   índice es un registro compartido de un solo destino, y por eso el lock.
3. KIQ es una tercera vía, y su condición es `amdgpu_sriov_runtime(adev)`.

**`NO_KIQ` no es memory ordering — `REFUTED`, y ahora con la causa.** `amdgpu_virt.h:363-365`:

```c
#define amdgpu_sriov_runtime(adev) \
	((adev)->virt.caps & AMDGPU_SRIOV_CAPS_RUNTIME)
```

`NO_KIQ` es un flag `1<<1` (`amdgpu.h:1249`) que **excluye** la ruta KIQ. La condición de
entrada a KIQ es el estado de virtualización SR-IOV del dispositivo, leído de
`virt.caps`. No hay barrera, ni `mb()`, ni `wmb()`, ni nada de ordenamiento en el
discriminante. La hipótesis de memory ordering queda descartada por lectura, no por
ausencia.

**Lo que sigue `NOT_DETERMINED` para Stage 2:**

| Pregunta | Estado | Discriminante |
|---|---|---|
| ¿`readl`/`writel` bastan para los registros de Polaris12, o hacen falta `RREG32_SOC15` con offsets? | `SUPPORTED` que existe la ruta directa; el offset por IP es `adev->reg_offset[ip][idx][…]` (`soc15_common.h:51`) | lectura de hardware |
| ¿`ioremap()` simple es la política correcta? | `UNKNOWN` | requiere el tipo de acceso que se vaya a usar, decided antes |
| ¿qué registros de Polaris12 caen fuera de `rmmio_size`? | `NOT_DETERMINED` | requiere el tamaño real del BAR 5, que es `evidence denied` sin privilegio |

El último punto es la frontera: **Stage 2 no puede ni elegir el mapeo correcto porque
`rmmio_size` no es legible sin privilegio.** Con `rmmio_size` desconocido, no se puede
decidir si un registro dado va por MMIO directo o por mmPCIE, y esa decisión determina si
basta `ioremap()` o hace falta la ruta indirecta. `MMIO_MAPPING` sigue `BLOCKED`, pero el
bloqueo ya no es "no sé qué hacer": es "falta un número".

---

## Pista C — U-1, U-2, U-3

### U-1 `amdgpu_job_run` y la selección de ring — `PROVEN`

`amdgpu_job.c:426-454`. La selección no es una búsqueda: es una **`container_of` de un solo
paso**.

```c
static struct dma_fence *amdgpu_job_run(struct drm_sched_job *sched_job)
{
	struct amdgpu_ring *ring = to_amdgpu_ring(sched_job->sched);
	struct amdgpu_device *adev = ring->adev;
	…
	job = to_amdgpu_job(sched_job);
	…
	r = amdgpu_ib_schedule(ring, job->num_ibs, job->ibs, job, &fence);
	…
	job->job_run_counter++;
	amdgpu_job_free_resources(job);
	fence = r ? ERR_PTR(r) : fence;
	return fence;
}
```

`to_amdgpu_ring` es `amdgpu_ring.h:69`:
`#define to_amdgpu_ring(s) container_of((s), struct amdgpu_ring, sched)`

Y `amdgpu.h:930` lo confirma por el lado de la declaración:
`struct amdgpu_sched gpu_sched[AMDGPU_HW_IP_NUM][AMDGPU_RING_PRIO_MAX];`

**Resultado:** `amdgpu_ring` **contiene** a `struct drm_gpu_scheduler` como miembro `sched`.
`sched_job->sched` es el puntero al scheduler; `container_of` reconstruye el anillo que lo
contiene. La relación es **contención, no tabla de búsqueda**.

Consecuencia para el diseño: no hay ningún índice `hw_ip`→`ring` que mantener en
`amdgpu_job_run`. La pregunta "¿cómo selecciona el ring?" tiene una respuesta sin búsqueda:
no selecciona, **desenvuelve**.

Relación de los cuatro conceptos, `OBSERVED`:

| Concepto | Papel | Evidencia |
|---|---|---|
| `sched_job` |cola el driver; contiene `s_fence` | `amdgpu_job.c:429` |
| `drm_sched` | el planificador; contiene `struct amdgpu_ring` como miembro | `amdgpu_ring.h:69` |
| `amdgpu_ring` | el anillo; contiene `sched` | `amdgpu.h:930` |
| submission | `amdgpu_ib_schedule()` emite los IB al ring | `amdgpu_job.c:442` |

Y el retorno de `run_job` es una `dma_fence`, con el contrato en
`sched_main.c:1055-1059`: *"The `run_job()` callback must by definition return a fence
whose refcount has been incremented for the scheduler already."*

### U-2 Recorridos de `adev->gpu_sched[hw_ip][hw_prio].sched[]` — `PROVEN`

`amdgpu_ctx.c` tiene **cuatro** usos, no los dos que la consigna mencionaba. Los cuatro:

| Línea | Uso | Qué demuestra |
|---|---|---|
| 163 | `if (adev->gpu_sched[hw_ip][hw_prio].num_scheds == 0) hw_prio = AMDGPU_RING_PRIO_DEFAULT;` | **consulta**, no recorrido: el array se indexa por `hw_prio` y si no hay schedulers se degrada a la prioridad por defecto |
| 229-230 | `scheds = …gpu_sched[hw_ip][hw_prio].sched; num_scheds = ….num_scheds;` | **extracción del par** `(puntero, longitud)` |
| 872-873 | idem | segunda ruta, la de `xcp_mgr` |

**Propiedad que el array demuestra realmente:** es un **directorio de dos niveles,
`[hw_ip][hw_prio]`, cuyo valor es un vector de schedulers con longitud explícita**, no un
array de longitud implícita. La prueba de que la longitud es explícita es `:163`: para saber
si hay schedulers hay que mirar `num_scheds`, no `sched[0]`.

Y hay una bifurcación por presencia de `xcp_mgr` (`amdgpu_ctx.c:228-238`):

```c
if (!(adev)->xcp_mgr) {
	scheds = adev->gpu_sched[hw_ip][hw_prio].sched;
	num_scheds = adev->gpu_sched[hw_ip][hw_prio].num_scheds;
} else {
	…
	r = amdgpu_xcp_select_scheds(adev, hw_ip, hw_prio, fpriv, &num_scheds, &scheds);
}
```

Para una GPU sin particionado XCP —RX 550 Polaris12 es de un solo XCP, aunque eso es
`UNKNOWN` y no lo doy por probado— la ruta es la primera: **`gpu_sched[][]` directo, sin
`amdgpu_xcp_select_scheds`**. Eso es `SUPPORTED` por lectura del discriminante
`adev->xcp_mgr`, no por conocimiento del hardware.

### U-3 `num_scheds` y `amdgpu_xcp.c` — `SUPPORTED`, con frontera

`amdgpu_ring.h:110-113`:

```c
struct amdgpu_sched {
	u32				num_scheds;
	struct drm_gpu_scheduler	*sched[AMDGPU_MAX_HIWIP_RINGS];
};
```

`num_scheds` es la **longitud válida** de `sched[]`, y el array tiene tope
`AMDGPU_MAX_HIWIP_RINGS`.

`amdgpu_xcp_select_scheds`, `amdgpu_xcp.c:482-517`, hace tres cosas:

1. Si el `fpriv` no tiene partición asignada, elige la de **menor `ref_cnt`**:
   `for (i = 0; i < xcp_mgr->num_xcps; i++) { total_ref_cnt = atomic_read(&xcp_mgr->xcp[i].ref_cnt); … }`.
   Es balanceo de carga por recuento de referencias atómico.
2. Devuelve `num_scheds` y `sched` de la partición elegida, e **incrementa** su `ref_cnt`.
3. Si `num_scheds == 0` en esa partición, devuelve `-ENOENT` y registra
   `"Failed to schedule partition #%d."`.

**Lo que esto demuestra sobre organización:** hay dos niveles, partición (XCP) y luego
`[hw_ip][hw_prio]`, y `num_scheds` es un recuento **variable por celda**, no una constante.
Que un ASIC tenga partición y cuántas tiene no se deduce de aquí.

**Frontera, sin extenderla:** el número de schedulers de Polaris12 por IP y por prioridad
**no es determinable estáticamente**. `num_scheds` lo establece el ASIC al inicializar sus
anillos, en runtime. `008-c` loolve como `ESTATIC` y barato; es correcto que sea barato
*leer el mecanismo*, y no lo es *obtener el valor*. La corrección:

> `CORRECTION_CANDIDATE` → `08-ARQUITECTURA/designs/008-c-scheduler-ring.md` · §"línea 136",
> fila U-3 · afirmación actual: *"`num_scheds` lo dice; leer la inicialización — estático"* ·
> evidencia nueva: `struct amdgpu_sched` en `amdgpu_ring.h:110-113` y
> `amdgpu_xcp_select_scheds` en `amdgpu_xcp.c:482-517` muestran que `num_scheds` se escribe
> en la inicialización de anillos del ASIC, y `amdgpu_xcp.c:491-501` confirma que el valor
> varía por celda · estado correcto: el **mecanismo** es estático y queda leído; el **valor
> para Polaris12** requiere runtime. `U-3` no se cierra estáticamente.

La frontera exacta: la lectura estática cierra *cómo se consulta y qué significa*; no cierra
*cuántos hay*. Confundir esas dos cosas es lo que hace parecer la pregunta más barata de lo
que es.

---

## Pista D — P-8: completion sin IRQ — `NOT_DETERMINED`, frontera delimitada

Pregunta: *¿existe en el código una ruta demostrable de completion de un submission que no
dependa de que una IRQ sea procesada?*

**Respuesta: `NO`, no para el camino de un job de compute.** Y esto es `SUPPORTED` por
cadena completa, no por ausencia de polling.

### La cadena de completion, trazada

```
submit → amdgpu_job_run()                     amdgpu_job.c:426
   │
   └── amdgpu_ib_schedule() devuelve una fence amdgpu     amdgpu_ib.c:124
              │
              │  esa fence se registra con dma_fence_add_callback(s_fence, cb,
              │  drm_sched_job_done_cb)                 sched_main.c:1065-1067
              ▼
   ◄── ¿qué la señala?
```

Para que el job se complete, esa fence debe ser señalada, y el señalador es la IRQ:

```
IRQ física
  └─ amdgpu_irq_handler()                    amdgpu_irq.c:200
      └─ amdgpu_ih_process()                 amdgpu_ih.c:209
          └─ amdgpu_irq_dispatch()           amdgpu_irq.c:468
              └─ src->funcs->process()       amdgpu_irq.c:511
                  └─ gfx_v8_0_eop_irq()      gfx_v8_0.c:6578   ← EOP, Polaris12
                      └─ amdgpu_fence_process(ring)   gfx_v8_0.c:6593, 6603
                          └─ dma_fence_signal(fence)   amdgpu_fence.c:233
```

`amdgpu_fence_emit` marca la fence con `AMDGPU_FENCE_FLAG_INT`
(`amdgpu_fence.c:116-117`): **el propio hardware tiene que interrumpir para completarla.**

`gfx_v8_0.c:1886-1900` confirma que `CHIP_POLARIS12` está en la lista deasic types serviced
por `gfx_v8_0_sw_init`, y `gfx_v8_0_eop_irq` es el handler de EOP que registra
(`gfx_v8_0.c:6994`, `7019-7020`).

### Las tres vías que existen, y por qué ninguna cierra P-8

| Vía | Qué hace | Por qué NO cierra P-8 |
|---|---|---|
| `amdgpu_fence_process` | lee la fence de VRAM y señala las completadas | **sus 3 callers son: `amdgpu_fence_fallback` (timer), `amdgpu_fence_driver_force_completion` (error), debugfs**. Ninguno es el camino normal |
| `amdgpu_fence_emit_polling` | busy-wait sobre `amdgpu_fence_read` antes de emitir | **es una espera previa**, no una señalización posterior. Espera a que la GPU alcance el punto, y luego emite. La fence que completa el job no la señala |
| `amdgpu_fence_fallback` (timer) | llama `amdgpu_fence_process` al expirar | **es un seguro contra IRQ perdida**, no una ruta de completion. Se programa *porque* se espera que la IRQ llegue |

`amdgpu_fence_wait_polling`, `amdgpu_fence.c:310-319`, lee `amdgpu_fence_read()` en bucle
con `udelay(2)`, y ese lee `*drv->cpu_addr` — la **dirección de CPU de la fence en VRAM**
(`amdgpu_fence.c:79-90`). Es un spin sobre memoria mapeada, no un estado de la fence.

**Conclusión de P-8, con su frontera:** para un job de compute sobre el camino
`submit → scheduler → ring → EOP`, **el completion depende de que una IRQ sea
procesada**. No hay ruta alternativa demostrable. Las tres vías sin IRQ que existen
(`_polling`, `force_completion`, timer de fallback) son espera previa, forzado por error, o
seguro de IRQ perdida, y ninguna señala la fence de un job completado por la GPU.

**Lo que esto no demuestra, y delimito la frontera sin extenderla:**

- No demuestra que el hardware *no pueda* completarse sin IRQ. Demuestra que **este driver**
  no tiene esa ruta.
- La afirmación es sobre el árbol `linux-7.2.8`. El subárbol
  `drivers/gpu/drm/scheduler/` **está presente y completo** (`sched_main.c`,
  `sched_fence.c`, `sched_entity.c`, `sched_rq.c`), así que esta pista **no** quedó frenada
  por ausencia de fuentes, a diferencia de la suposición previa.
- `NOT_DETERMINED` y no `PROVEN` por una razón concreta: `amdgpu_ib_schedule` devuelve la
  fence de amdgpu, pero **no tracé qué fence concreta** es ni su relación exacta con
  `amdgpu_fence_emit`. Sin ese eslabón, la cadena queda desde
  `dma_fence_add_callback` hasta arriba, que es `SUPPORTED`, y el último tramo, `NOT_DETERMINED`.

**Discriminante mínimo para cerrar P-8:** el punto exacto de `amdgpu_ib_schedule` donde
devuelve `*f`, y si esa fence se emite con `AMDGPU_FENCE_FLAG_INT` o sin él. Es una lectura
de `amdgpu_ib.c:124-260`, ~140 líneas, sin runtime. Si esa fence se emite **sin** el flag
INT, P-8 se cierra en `SUPPORTED` negativo con una excepción concreta; si se emite **con** el
flag, se confirma la cadena completa y P-8 queda `PROVEN` para el camino investigated.

**Por qué el antecedente de `008-c` no convertía esto en nuevo bloqueo:** la ausencia del
subárbol `drm/scheduler` habría sido `NOT_AVAILABLE` para la parte de arriba, no para
`amdgpu_fence_process`, que vive en el driver. La frontera real no era el scheduler.

---

## Lo que NO toqué

`07-DRIVER/kernel/*` (incluido `rx550_drv.c` y el `drm_dev_put()` incorrecto) · `AGENTS.md` ·
`COORDINACION.md` · `007-*` · `008-a-*` `008-b-*` `008-c-*` `008-d-*`. Sin commits. Sin
runtime. Sin instalaciones.

## Procedencia

Árboles: `RESEARCH/kernelbuild/linux-7.1.3/` (VERSION 7.1.3, en el proyecto) ·
`/home/lucas/rx550-analysis-7.2.8/linux-7.2.8/` (VERSION/PATCHLEVEL/SUBLEVEL ausentes del
`Makefile`; identidad 7.2.8 por ruta y por coherencia con el análisis previo — `EXTERNAL`
en cuanto a la versión exacta del árbol). `git log`/`blame` no usados como autoridad
semántica en ninguna afirmación.

Corrección de método registrada: busqué `drm_dev.c` por nombre de fichero en el árbol
equivocado y declaré `NOT_AVAILABLE`. El fichero se llama `drm_drv.c` y el árbol correcto
estaba en el propio proyecto. La búsqueda por símbolo habría encontrado ambas cosas.
