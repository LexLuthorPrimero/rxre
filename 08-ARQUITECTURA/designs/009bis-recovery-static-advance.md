# 009bis — Recuperación: contenido único de `009-stage2-static-advance.md`

**Este fichero es una recuperación, no una tercera línea de trabajo.**

`08-ARQUITECTURA/designs/009-stage2-static-advance.md` (684 líneas, escrito por
esta línea) fue **sobrescrito** a las 05:44–05:46 por la otra sesión, que
escribió sobre el mismo nombre de fichero. El contenido de aquella versión
**no está en git** (el path era untracked). Este fichero conserva
**únicamente** el material que la versión actual **no** contiene, más dos
retractaciones.

Fuente primaria: `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
+ `RESEARCH/evidence/linux-7.1.3.tar.xz` (sha256 `be41c068…7b45`, 158 335 040 B).

`RUNTIME = NOT_RUN` · `COMMIT = NO` · `UMR = NOT_RUN`

---

## 1. RETRACTACIÓN — dos `OPEN_BOUNDARY` que declaré y eran falsas

Escribí que `drivers/gpu/drm/scheduler/` y que el enum de ASIC **no estaban
en ninguna fuente disponible**. **Es falso**: ambos están en
`RESEARCH/evidence/linux-7.1.3.tar.xz`, que estaba en el repositorio.

```
$ tar -tJf RESEARCH/evidence/linux-7.1.3.tar.xz | grep drm/scheduler/
linux-7.1.3/drivers/gpu/drm/scheduler/sched_entity.c
linux-7.1.3/drivers/gpu/drm/scheduler/sched_fence.c
linux-7.1.3/drivers/gpu/drm/scheduler/sched_main.c
```

**Causa**: hice `grep -rln "CHIP_POLARIS12" --include=*.h` sobre el subárbol
amd que tenía extraído, y concluí ausencia. Es exactamente el error que
`AGENTS.md` nombra — *«asserting absence from a neighbouring check»* — y el
**tercer** de la misma forma en este trabajo: inferí una ausencia desde una
fuente parcial en vez de comprobar la fuente completa, que estaba a un `ls`.

**Consecuencia**: los `OPEN_BOUNDARY` de F9 y del enum de ASIC que
escribí eran límites de *mi* extracción, no de la evidencia. Ambos están
cerrados abajo.

---

## 2. ENUM DE ASIC — `OPEN_BOUNDARY` cerrado, BAR 5 `PROVEN`

El enum vive en `include/drm/amd_asic_type.h`, **`enum amd_asic_type` (`:31`)**,
con ordinales explícitos en comentario:

```
include/drm/amd_asic_type.h:37    CHIP_BONAIRE,      /* 5  */
include/drm/amd_asic_type.h:49    CHIP_POLARIS12,    /* 17 */
```

```
CHIP_POLARIS12 (17) >= CHIP_BONAIRE (5)   →   VERDADERO

amdgpu_device.c:3812   if (adev->asic_type >= CHIP_BONAIRE)
amdgpu_device.c:3813       adev->rmmio_base = pci_resource_start(adev->pdev, 5);
amdgpu_device.c:3814       adev->rmmio_size = pci_resource_len(adev->pdev, 5);
amdgpu_device.c:3823   adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size);
```

**Polaris12 → BAR 5 → `rmmio` → `ioremap()`. `PROVEN`.** La rama BAR 2
(`:3816`) es para ASICs anteriores a Bonaire, y **no aplica a Polaris12**.

---

## 3. TRES ROLES DE BAR — no uno

Los 24 usos de `pci_resource_start/len` del subárbol se reducen a:

| BAR | Rol | Condición | Evidencia |
|---|---|---|---|
| **0** | apertura de VRAM `gmc.aper_base/size` | por función GMC | `gmc_v8_0.c:575-576` (GMC de Polaris12) |
| **0** | BIOS / `vram_base` | — | `amdgpu_bios.c:117` |
| **2** | **doorbell** `adev->doorbell.base` | **incondicional** | `amdgpu_doorbell_mgr.c:209-210` |
| **5** | **registros** `adev->rmmio` | `asic_type >= CHIP_BONAIRE` → **verdadera** | `amdgpu_device.c:3812-3814`, enum §2 |

El «2» de `amdgpu_doorbell_mgr.c:210` y el «5» de `amdgpu_device.c:3813` son
** apertures distintas**. Cualquier lectura que los identifique confunde
puertas con registros. Para Polaris12 son **BAR 5 (registros)** y
**BAR 2 (doorbells)**, y esto último es lo que permite que la rama
`else` de `:3816` sea irrelevante y no una ambigüedad.

---

## 4. `GFX_HWIP` — tres objetos, dos `PROVEN`

El término «HWIP» nombra **dos** cosas distintas. Separarlas es el resultado.

```
A  registro de IP block
   vi.c:2107   case CHIP_POLARIS12:
   vi.c:2112       amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
   → PROVEN.  Dice QUÉ implementación se usa.

B  hw_ip del scheduler
   gfx_v8_0.c:6916-6917  gfx_v8_0_ring_funcs_compute.type = AMDGPU_RING_TYPE_COMPUTE
   gfx_v8_0.c:6986       adev->gfx.compute_ring[i].funcs = &gfx_v8_0_ring_funcs_compute
   gfx_v8_0.c:6976       gfx_v8_0_set_ring_funcs(), llamado desde
                         gfx_v8_0_early_init (:5259) en :5268
   amdgpu_ring.h:75      AMDGPU_RING_TYPE_COMPUTE = AMDGPU_HW_IP_COMPUTE
   amdgpu_ring.c:379     hw_ip = ring->funcs->type;
   → PROVEN.  El enum de ring type ES un alias del enum de HW IP, luego
     hw_ip = AMDGPU_HW_IP_COMPUTE es una CONSTANTE DE COMPILACIÓN.
     Sin hardware, sin runtime, sin condición.

C  configuración efectiva del silicio
   amdgpu_discovery.c:1721  amdgpu_discovery_get_gfx_info()
   amdgpu_discovery.c:1740  gc_info = (union gc_info *)(discovery_bin + offset)
   amdgpu_discovery.c:1744  … gc_info->v1.gc_num_se, :1750 gc_num_gprs,
                            :1755 gc_wave_size
   amdgpu_discovery.c:327-332  discovery.size = DISCOVERY_TMR_SIZE
                              discovery.bin  = kzalloc(size)
   → NOT_DETERMINED.  Los valores están en TMR del ASIC, leídos en runtime.
```

**Estado correcto, sin colapsar:**

```
GFX_HWIP
├── IP block registration            PROVEN   vi.c:2112
├── scheduler hw_ip = AMDGPU_HW_IP_COMPUTE   PROVEN   amdgpu_ring.h:75
└── effective silicon configuration  NOT_DETERMINED  amdgpu_discovery.c:1740
```

Escribir solo `GFX_HWIP = NOT_DETERMINED` **pierde información**: el objeto B
es determinable sin hardware.

> **ADDENDUM 2026-09-29 — la afirmación `NOT_FOUND` de este párrafo queda
> REFUTADA.** No la retiro sin añadir la evidencia que la refuta.
>
> El valor entero **es 1**, y la definición existe en el corpus:
>
> ```
> include/uapi/drm/amdgpu_drm.h:933   #define AMDGPU_HW_IP_GFX          0
> include/uapi/drm/amdgpu_drm.h:934   #define AMDGPU_HW_IP_COMPUTE      1
> include/uapi/drm/amdgpu_drm.h:935   #define AMDGPU_HW_IP_DMA          2
> include/uapi/drm/amdgpu_drm.h:947   #define AMDGPU_HW_IP_NUM          10
> ```
>
> Son **macros**, no valores de enum. 7.2.8 los tiene idénticos y en las
> mismas líneas (`:933`, `:934`).
>
> **Por qué la affirmation original falló**: `include/uapi/` **no existe en
> `RESEARCH/working/linux-7.1.3/`** — ese árbol solo trae `include/linux`. Yo
> había escrito «la definición está fuera del subárbol `amd/amdgpu/`», que es
> cierto pero irrelevante: la fuente searched era el subárbol extraído, no el
> corpus. **Cuarta vez con el mismo mecanismo** (ver §1). `NOT_FOUND` por
> búsqueda no exhaustiva no es `NOT_FOUND`; es `NOT_DETERMINED` y así debió
> declararse.
>
> **Consecuencia añadida, no prevista al redactar el §4**: el guardián de
> `amdgpu_ring.c:378`
>
> ```c
> if (!ring->no_scheduler && ring->funcs->type < AMDGPU_HW_IP_NUM)
> ```
>
> queda **demostrado cierto** para un ring de compute de Polaris12:
> `AMDGPU_RING_TYPE_COMPUTE` = `AMDGPU_HW_IP_COMPUTE` = `1` < `10`. Antes solo
> había comprobado el guardián existía, no que se cumpliera.
>
> **Y la distinción pedida queda probada numéricamente, no solo por nombre**:
>
> ```
> CHIP_POLARIS12      = 17   include/drm/amd_asic_type.h:49      (enum amd_asic_type)
> AMDGPU_HW_IP_COMPUTE = 1   include/uapi/drm/amdgpu_drm.h:934  (macro)
>
> 1 != 17
> ```
>
> Dos espacios de numeración distintos. Que `CHIP_POLARIS12 = 17` esté probado
> no dice nada sobre el valor de `AMDGPU_HW_IP_COMPUTE`, y ahora se ve por
> qué: **no son el mismo tipo y no comparten escala.**

### Estado corregido del §4

```
GFX_HWIP
├── IP block registration                   PROVEN   vi.c:2112
├── scheduler hw_ip = AMDGPU_HW_IP_COMPUTE  PROVEN   amdgpu_ring.h:75
│   └── valor entero = 1                    PROVEN   amdgpu_drm.h:934
│       y 1 < AMDGPU_HW_IP_NUM (10)         PROVEN   amdgpu_drm.h:947
│           → guardián de amdgpu_ring.c:378  PROVEN
└── effective silicon configuration         NOT_DETERMINED  amdgpu_discovery.c:1740
```

---

## 5. F9 — cerrado. El despacho completo

`drivers/gpu/drm/scheduler/` sí está (tarball). El tramo que declaré
`OPEN_BOUNDARY` es trazable:

```
ENCOLADO
  amdgpu_cs.c:1369    drm_sched_entity_push_job(&p->jobs[i]->base)
  sched_entity.c:600  spsc_queue_push(&entity->job_queue, &sched_job->queue_node)

DESPACHO
  sched_main.c:345    drm_sched_run_job_queue(sched)
  sched_main.c:348      queue_work(sched->submit_wq, &sched->work_run_job)
  sched_main.c:1231   drm_sched_run_job_work(w)
    :1242   entity    = drm_sched_select_entity(sched)
    :1251   sched_job = drm_sched_entity_pop_job(entity)
    :1260   atomic_add(sched_job->credits, &sched->credit_count)
    :1261   drm_sched_job_begin(sched_job)
    :1268   fence     = sched->ops->run_job(sched_job)      ◄ amdgpu_job_run
    :1270   drm_sched_fence_scheduled(s_fence, fence)
    :1273   dma_fence_add_callback(fence, &sched_job->cb,
                                   drm_sched_job_done_cb)
    :1275   if (r == -ENOENT)          ◄ el fence YA estaba señalado
    :1276       drm_sched_job_done(sched_job, fence->error)
```

**El scheduler al que atiende el job** no es el array `gpu_sched[][]` de
AMDGPU: `drm_sched_select_entity` (`sched_main.c:1242`) elige entre las
entidades de una runqueue. El array `gpu_sched[hw_ip][hw_prio].sched[]` se
consume en el otro sentido — `amdgpu_ctx.c:838-840`
`drm_sched_entity_modify_sched(&aentity->entity, scheds, num_scheds)` le
dice a la entidad **a qué schedulers puede pertenecer**. Son dos direcciones
distintas y no deben fusionarse.

---

## 6. P-8 — clasificación corregida, y el eslabón que faltaba

`amdgpu_fence_process` señaliza el fence **de hardware**, y el scheduler
registró su callback **sobre ese mismo objeto**:

```
amdgpu_ib.c:311        *f = &af->base;            ◄ el fence del job
amdgpu_job.c:459-460   return fence;               ◄ run_job lo devuelve
sched_main.c:1268      fence = sched->ops->run_job(sched_job)
sched_main.c:1273      dma_fence_add_callback(fence, &sched_job->cb,
                                              drm_sched_job_done_cb)
        … el hardware termina …
gfx_v8_0.c:6600       amdgpu_fence_process(compute_ring[i])
amdgpu_fence.c:243     dma_fence_signal(fence)      ◄ dispara el callback
sched_main.c:389       drm_sched_job_done_cb → :393 drm_sched_job_done(s_job, f->error)
sched_main.c:368       drm_sched_job_done
sched_main.c:379         drm_sched_fence_finished(s_fence, result)
sched_fence.c:80          drm_sched_fence_finished
sched_fence.c:84            dma_fence_signal(&fence->finished)   ◄ JOB COMPLETO
```

**Un solo objeto `dma_fence` conecta la señalización del hardware con el
completado del job.** No son dos cadenas paralelas.

Y el disparador, con identificador concreto:

```
gfx_v8_0.c:1914  amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY,
                                  VISLANDS30_IV_SRCID_CP_END_OF_PIPE,
                                  &adev->gfx.eop_irq)
gfx_v8_0.c:6991  gfx_v8_0_eop_irq_funcs = { … .process = gfx_v8_0_eop_irq }
gfx_v8_0.c:6584  me_id    = (entry->ring_id & 0x0c) >> 2
gfx_v8_0.c:6585  pipe_id  = (entry->ring_id & 0x03) >> 0
gfx_v8_0.c:6586  queue_id = (entry->ring_id & 0x70) >> 4
gfx_v8_0.c:6599  if (ring->me == me_id && ring->pipe == pipe_id
                     && ring->queue == queue_id)
gfx_v8_0.c:6600      amdgpu_fence_process(ring)
```

El `(me, pipe, queue)` que asigna `gfx_v8_0_compute_ring_init`
(`gfx_v8_0.c:1857-1859`) es **la misma clave** con la que el IRQ localiza el
ring. Cierre por coincidencia de esquema de direccionamiento, no analogía.

### Clasificación corregida

```
P-8
SUBMIT EMISSION sin IRQ            PROVEN    amdgpu_ib.c:283 :310
FENCE SIGNAL por IRQ               PROVEN    amdgpu_fence.c:243
IRQ identifica ring                PROVEN    gfx_v8_0.c:6599-6600
amdgpu_fence_process desde IRQ     PROVEN    gfx_v8_0.c:6600
COMPLETION por IRQ                 PROVEN    sched_fence.c:84

FALLBACK TIMER                     PROVEN    amdgpu_fence.c:459 :263
TIMER armado inicialmente sin IRQ  NO PROVEN
TIMER como vía independiente       NO PROVEN

IRQ DEPENDENCY para completion     PROVEN
```

**La corrección conceptual**: el timer **no** demuestra una segunda vía
independiente. Se arma en `amdgpu_fence.c:459` (`timer_setup`) y se rearma en
`:219-221`, **dentro** de `amdgpu_fence_process`. Si el IRQ nunca hubiera
llegado, el primer `amdgpu_fence_process` no habría ocurrido y el timer no
existiría. **Iniciación requiere IRQ; consumación puede no requerirlo.**

**Corrección de atribución**: `amdgpu_fence.c:263` está dentro de
`amdgpu_fence_fallback()` (def `:258`), **no** de
`amdgpu_fence_wait_polling()` (que existe, def `:310`, llamado desde `:169`
dentro de `amdgpu_fence_emit_polling` — evidencia retirada).

---

## 7. `pahole` SÍ aplica — contradice `NOT_APPLICABLE`

La otra línea registra `Tool-Assisted Structural Evidence = NOT_APPLICABLE`
por no haber artefacto con DWARF. **Hay, y produce resultado:**

```
$ readelf -S …/amdgpu/amdgpu_vm.o | grep -c debug
2
$ pahole -C amdgpu_sched …/amdgpu_vm.o
struct amdgpu_sched {
        u32                        num_scheds;   /*    0     4 */
        struct drm_gpu_scheduler * sched[64];     /*    8   512 */
        /* size: 520, cachelines: 9, members: 2 */
};
```

`RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/` contiene 3
objetos con DWARF: `amdgpu_debugfs.o`, `amdgpu_vm.o`, `amdgpu_vm_pt.o`. Los
headers comunes bastan para jobs, rings y fences.

Dos propiedades **que el fuente no da**, por vía independiente:

1. **`sched[]` tiene 64 ranuras.** El `(*num_sched)++` de
   `amdgpu_ring.c:381` no puede exceder 64 sin corromper la estructura, y
   **no hay comprobación de límites**. Dato estructural; no dice cuántos hay
   realmente.
2. **`struct amdgpu_job.base` está en offset 0**, luego
   `to_amdgpu_job(sched_job) == (struct amdgpu_job *)sched_job`. Confirma
   `amdgpu_job.h:39-40` (`container_of(…, base)`) por vía distinta.

```
struct amdgpu_job {
        struct drm_sched_job  base;      /*    0   144 */  ◄ primer miembro
        struct amdgpu_vm    * vm;         /*  144     8 */
        struct amdgpu_fence * hw_fence;   /*  280     8 */  ◄ amdgpu_ib.c:158
        struct amdgpu_fence * hw_vm_fence;/*  288     8 */
        uint64_t              generation; /*  360     8 */  ◄ amdgpu_job.c:440
};
```

Layout, no semántica. Eso es todo lo que se extrae.

---

## 8. Teardown del driver AMDGPU — objeto DISTINTO del `FIX_DIRECTION` de la otra línea

**No contradictorio, no duplicado.** La otra línea analiza `drm_dev_put` doble
en el driver local `07-DRIVER/`. Esto es el **driver upstream** y su camino
de fallo de `probe`.

```
amdgpu_device_fini_sw()  tiene UN SOLO caller en todo el subárbol:
    amdgpu_kms.c:1603  amdgpu_driver_release_kms(drm_device *dev)
    amdgpu_kms.c:1607      amdgpu_device_fini_sw(adev);
        └─ es el callback unload del driver DRM; lo invoca el core DRM,
           tras drm_dev_register con éxito y la notificación a userspace.

Camino de fallo:
    amdgpu_drv.c:2430-2432  if (ret) goto err_pci;
    amdgpu_drv.c:2519-2521  err_pci: pci_disable_device(pdev); return ret;
        └─ dos operaciones. SIN drm_dev_unregister, SIN drm_dev_unplug,
           SIN amdgpu_device_fini_sw.

Y lo que sí se intenta, tampoco completa:
    amdgpu_kms.c:167-169    out: if (r) amdgpu_driver_unload_kms(dev);
    amdgpu_kms.c:91-92      if (adev->rmmio == NULL) return;   ◄ salta :98
    amdgpu_kms.c:98         amdgpu_device_fini_hw(adev);

Y la condición que fuerza ese caso:
    amdgpu_device.c:3823    adev->rmmio = ioremap(…)
    amdgpu_device.c:3825    if (!adev->rmmio) return -ENOMEM;
    amdgpu_device.c:3861    amdgpu_device_ip_early_init(adev)   ◄ 38 líneas después
```

```
PROVEN (estructural):
  Si amdgpu_device_init falla en el mapeo de MMIO, entonces
     amdgpu_device_fini_hw  NO se ejecuta   (amdgpu_kms.c:91-92 → :98)
     amdgpu_device_fini_sw  NO se ejecuta   (único caller :1607, vía
                                             drm_dev_unregister)
     drm_dev_unregister     NO se ejecuta   (err_pci :2519-2521)

NOT_DETERMINED:
  que esto cause el DRM_REFCOUNT_TEARDOWN = FAIL observado — requiere
  observar el runtime correspondiente. NO autorizado en esta ronda.
```

**Advertencia explícita**: nada de esto prueba que el test ejercite esta
ruta. Si el fallo ocurre con MMIO correctamente mapeado, `fini_hw` sí corre y
el discriminante no aplica. **El test es lo que distingue ambos casos** — ese
es su valor como discriminante, y no como diagnóstico cerrado.

---

## 9. UMR — sin ejecutar

Ninguna operación ejecutada. Registro de qué resolvería cada una.

| Cuestión | Operación | Naturaleza | Estado |
|---|---|---|---|
| Objeto C §4 (`gc_num_se`, `gc_num_gprs`, `gc_wave_size`) | lectura de la IP discovery en VRAM (`adev->discovery.offset`, `DISCOVERY_TMR_SIZE`, `amdgpu_discovery.c:327-332`) | lectura de memoria de dispositivo; requiere ASIC | `NOT_RUN` |
| `GFX_HWIP` efectivo (objeto C) | lectura del registro de revisión de GFX | lectura de MMIO | `NOT_RUN` |
| §3 — roles de BAR | `lspci -s <slot> -v` → nº y tamaño de BAR, comparado con `rmmio_size` | **config space; no toca la GPU** | `NOT_RUN` |

La tercera es la única estrictamente read-only y sin efecto de estado, y
resuelve §3 comparando tamaños. **No se ejecutó.** Requiere autorización
separada.

---

## 10. Verificación

52 referencias `fichero:línea` de este documento comprobadas una por una
contra el corpus. **0 rotas**. Las de `sched_main.c` / `sched_entity.c` /
`sched_fence.c` comprobadas contra la extracción del tarball.

```
RUNTIME = NOT_RUN   COMMIT = NO   UMR = NOT_RUN
```

Herramientas: `sed`, `awk`, `grep`, `tar -xOJf`, `readelf`, **`pahole` v1.30**.
No usadas: `clang -Xclang -ast-dump` (los tres `container_of` relevantes
verificados contra DWARF, §7), `ctags`, `nm`/`objdump` (los 3 objetos con
DWARF no contienen `amdgpu_job.o` ni `amdgpu_ring.o`; `pahole` cubrió lo que
había).
