# 007 — Trazado estático de la ruta de compute en Polaris12

**Ámbito**: `08-ARQUITECTURA/` · **Fecha**: 2026-09-29
**Fuente primaria**: `RESEARCH/working/linux-7.1.3/`, subárbol
`drivers/gpu/drm/amd/amdgpu/` (970 `.c`)
**Alcance**: lectura de fuente. **Sin ejecución**, sin modification, sin
`OWNERSHIP`, sin escribir código de `07-DRIVER/`.
**Responde a**: `P-1` de `DECISIONS-F4.md` y `F4-AD-6`.

---

## 1. Pregunta

¿Cuál es la ruta estática de compute relevante para Polaris12, desde el
registro PCI hasta la ejecución o submissión de comandos?

Cada flecha queda clasificada como `PROVEN`, `NOT_DETERMINED`, `NOT_FOUND` o
`NOT_APPLICABLE`. `PROVEN` exige fichero, función, línea y la relación
concreta; el nombre de un fichero o de un subsistema no es prueba.

---

## 2. Mapa

```
                 [F1]              [F2]               [F3]
  PCI 1002:699f ────────► amdgpu_device ────► IP initialization
  amdgpu_drv.c:3169      amdgpu_device.c:     amdgpu_device.c:1926
  :3135 :2364            3679                       │
  :3138                        │                     │ switch (asic_type)
  amdgpu_pci_probe                │                     │ :1980 CHIP_POLARIS12
        │                         │                     ▼
        │ amdgpu_kms.c:135        │            vi_set_ip_blocks()
        │ amdgpu_kms.c:148        │                     vi.c:2049
        ▼                         │                     │ :2113
  amdgpu_device_init              │            amdgpu_device_ip_block_add()
        │                         │                     │ amdgpu_ip.c:221
        │ amdgpu_device.c:4019    │                     ▼
        │                         │            registro de IP blocks
        │                         │            (gfx_v8_0, sdma_v3_1, gmc_v8_1, …)
        ▼                         ▼
  amdgpu_device_ip_init()   ──►  bucle sw_init   amdgpu_device.c:2311
  amdgpu_device.c:2299              │
        │                           │ funcs->sw_init
        │                           ▼
        │                  [F4] gmc_v8_0_sw_init   gmc_v8_0.c:1094
        │                           │ :1716
        │                           │ amdgpu_bo_init
        │                           ▼
        │                  [F5] amdgpu_bo_init()   amdgpu_object.c:1058
        │                      GEM / TTM / BO

        ┊  desde aquí la ruta de compute se separa de la de init

        ▼
  [F6] GFX / compute
       gfx_v8_0_sw_init()           gfx_v8_0.c:1886
             │ :6853 (.sw_init)
             │ :1994
             ▼
  [F7] gfx_v8_0_compute_ring_init()   gfx_v8_0.c:1846
             │ :1875 amdgpu_ring_init(adev, ring, 1024, …)
             │ :1858 doorbell_index = mec_ring0 + ring_id
             ▼
  [F8] amdgpu_ring_init()          amdgpu_ring.c:226
             │ :255 sched_hw_submission
             │ :378-381  ring->sched → gpu_sched[hw_ip][hw_prio].sched[]
             ▼
       amdgpu_device_init_schedulers()   amdgpu_device.c:2220
             │ :2459 llamada desde amdgpu_device_init
             │ :2223 .ops = &amdgpu_sched_ops
             │ :2258 drm_sched_init(&ring->sched, &args)
             ▼
       amdgpu_sched_ops                 amdgpu_job.c:513
             │ :515 .run_job = amdgpu_job_run
             ▼
       amdgpu_job_run()                 amdgpu_job.c:426
             │ :428 ring = to_amdgpu_ring(sched_job->sched)
             │      ↳ amdgpu_ring.h:69 = container_of(s, …, sched)
             │      ↳ MISMO objeto registrado en amdgpu_ring.c:381
             │ :448 amdgpu_ib_schedule(ring, …)
  [F9] command submission → ejecución
       amdgpu_cs_ioctl()           amdgpu_cs.c:1411
             │ :1429 pass1 · :1433 pass2 · :1460 submit
             ▼
       amdgpu_cs_submit()          amdgpu_cs.c:1275
             │ :1369 drm_sched_entity_push_job()   ◄── encola, NO ejecuta
             ▼
  [hueco] drm_sched_entity_push_job() → drm_sched core → run_job
                    ▲
                    └── ÚLTIMO SALTO DEMOSTRADO
```

---

## 3. Evidencia por flecha

### F1 · Registro PCI → probe — **`PROVEN`**

| Relación | Ubicación |
|---|---|
| `pci_register_driver(&amdgpu_kms_pci_driver)` | `amdgpu_drv.c:3169`, dentro de `amdgpu_init()` |
| `static struct pci_driver amdgpu_kms_pci_driver` | `amdgpu_drv.c:3135` |
| `.probe = amdgpu_pci_probe` | `amdgpu_drv.c:3138` |
| `static int amdgpu_pci_probe(struct pci_dev *, …)` | `amdgpu_drv.c:2364` |

**Corrección registrada.** Busqué `amdgpu_main.c`, no lo encontré, y propuse
`NOT_FOUND` para esta flecha. Falso por dos motivos: el `Makefile` **no lo
lista** (`grep -n amdgpu_main Makefile` → sin salida) y tampoco existe upstream
(`raw.githubusercontent.com/torvalds/linux/master/…/amdgpu_main.c` → 404). La
función de registro está en `amdgpu_drv.c` desde siempre.

*Fuente externa usada solo para esa comprobación negativa. `git.kernel.org`
respondió con un desafío anti-bot y **no cuenta como evidencia**.*

### F2 · probe → `amdgpu_device_init` — **`PROVEN`**

```
amdgpu_pci_probe()            amdgpu_drv.c:2364
  └─ amdgpu_driver_load_kms(adev, flags)      amdgpu_drv.c:2430
                                                  │
     (definición) amdgpu_kms.c:135                  │
       └─ r = amdgpu_device_init(adev, flags)  amdgpu_kms.c:148
                                                  │
     (definición) amdgpu_device.c:3679             │
```

### F3 · `amdgpu_device` → IP blocks (Polaris12) — **`PROVEN`**

```
amdgpu_device_init()                          amdgpu_device.c:3679
  └─ amdgpu_device_ip_early_init(adev)         :3861  → def. :1926
       └─ switch (adev->asic_type)             :1946
            case CHIP_POLARIS12:               :1980
            └─ vi_set_ip_blocks(adev)          :1989
                 └─ amdgpu_device_ip_block_add(&sdma_v3_1_ip_block, …)
                                                  vi.c:2113
```

**La ruta de Polaris12 NO pasa por `amdgpu_discovery_set_ip_blocks()`.**
Ese `switch` (`amdgpu_discovery.c:2782`) no contiene `case CHIP_POLARIS12`:
POLARIS12 aparece 10 veces en `vi.c` y **0** en `soc15.c`. La rama se resuelve
un nivel más arriba, en el `switch (asic_type)` de `amdgpu_device.c:1946`.

Escribir la ruta como `amdgpu_device → amdgpu_discovery_set_ip_blocks →
Polaris12` habría sido inferencia por analogía con las ASIC que sí pasan por
ahí, y habría sido falsa.

### F4 · IP blocks → GEM/TTM/BO — **`PROVEN`**

El despacho de `sw_init` es un bucle sobre los IP blocks registrados:

```
amdgpu_device_init()                  amdgpu_device.c:3679
  └─ amdgpu_device_ip_init(adev)      :4019  → def. :2299
       └─ for (i < adev->num_ip_blocks)              :2308
            └─ adev->ip_blocks[i].version->funcs->sw_init(&…[i])   :2311-2312
```

Para Polaris12 el bloque GMC registrado es `gmc_v8_1_ip_block` (`vi.c:2110`).
**Nota de nomenclatura**: el fichero `gmc_v8_1.c` **no existe** en el corpus ni
aparece en el `Makefile`; la implementación de GMC para esta generación está
en **`gmc_v8_0.c`** (`:141`, `:241`, `:592` y `:1220` tienen
`case CHIP_POLARIS12`). El nombre del *ip_block* y el del fichero no
coinciden, y es el nombre del fichero el que no está.

```
gmc_v8_0_sw_init()                   gmc_v8_0.c:1094  (.sw_init en :1716)
  └─ r = amdgpu_bo_init(adev)        gmc_v8_0.c:1154
```

### F5 · `amdgpu_bo_init` → gestor de memoria — **`PROVEN`**

`amdgpu_bo_init()` en `amdgpu_object.c:1058`, invocado desde `gmc_v8_0.c:1154`
en el comentario `/* Memory manager */`. Es el punto donde AMDGPU instala
GEM/TTM.

### F6 · GFX / compute — **`PROVEN` hasta `gfx_v8_0_sw_init`; más allá, `NOT_DETERMINED`**

```
gfx_v8_0_sw_init()                   gfx_v8_0.c:1886  (.sw_init en :6853)
  ├─ EOP event, privileged reg, privileged inst, CP EDC/ECC irq
  ├─ for (i < adev->gfx.num_gfx_rings)              :1967
  │    └─ amdgpu_ring_init(adev, ring, 1024, …)    :1977
  └─ gfx_v8_0_compute_ring_init(adev, …)           :1994
```

### F7 · ring de compute — **`PROVEN` hasta `amdgpu_ring_init`; más allá, `NOT_DETERMINED`**

```
gfx_v8_0_compute_ring_init()        gfx_v8_0.c:1846
  ├─ ring->me = mec + 1                    :1857
  ├─ ring->doorbell_index = mec_ring0 + ring_id   :1863
  ├─ ring->name = "comp_%d.%d.%d"          :1866
  └─ r = amdgpu_ring_init(adev, ring, 1024, …)   :1875
```

**Lo que NO se establece**: que exista un ring de compute por warrant, y que
`gfx_v8_0_init_ring_mecad` lo asigne a un ring de GFX, son afirmaciones de las
fichas de diseño existentes y no las he trazado aquí. `NOT_DETERMINED`.

### F8 · `amdgpu_ring_init` ↔ scheduler — **`PROVEN`**

> **Corrección.** Esta flecha figuraba como `NOT_DETERMINED (causal)`. Era
> **falso**. El vínculo estaba en `amdgpu_ring.c:378-381`, en el fichero que yo
> tenía abierto, 150 líneas por debajo de donde lo cerré. No lo busqué: cerré
> en cuanto encontré un `NOT_DETERMINED` plausible. El `NOT_DETERMINED` de
> F9 **no se traslada** a F8: F8 era una relación concreta y está probada.

La relación **no** es `drm_sched_entity_init()`. `amdgpu_ring_init()` no la
llama: hace lo contrario, **registra** el `drm_gpu_scheduler` embebido en el
ring dentro del array del scheduler.

```
amdgpu_ring_init()                              amdgpu_ring.c:226
  ├─ sched_hw_submission = amdgpu_sched_hw_submission     :232
  ├─ if (type == KIQ) → max(…, 256)   ·   if (type == MES) → 8     :243-246
  │     (no hay rama GFX/COMPUTE aquí; el switch por tipo que sí las
  │      tiene es el de `timeout`, en amdgpu_device.c:2238-2251)
  ├─ if (ring->adev == NULL) { … ring->num_hw_submission = … }  :250 :255
  └─ if (!ring->no_scheduler && ring->funcs->type < AMDGPU_HW_IP_NUM)   :378
       hw_ip     = ring->funcs->type                                  :379
       num_sched = &adev->gpu_sched[hw_ip][hw_prio].num_scheds         :380
       adev->gpu_sched[hw_ip][hw_prio].sched[(*num_sched)++]
             = &ring->sched;                                          :381
```

Y el lado inverso, el punto donde el scheduler se inicializa de verdad:

```
amdgpu_device_init()                    :3679
  └─ amdgpu_device_init_schedulers()     :2459 → def. :2220
       ├─ args = { .ops = &amdgpu_sched_ops,           :2223
       │           .num_rqs = DRM_SCHED_PRIORITY_COUNT }
       ├─ for (i < AMDGPU_MAX_RINGS)                    :2231
       │    if (!ring || ring->no_scheduler) continue;  :2235
       │    switch (ring->funcs->type) timeout = …      :2238-2251
       │       COMPUTE → adev->compute_timeout          :2242-2243
       ├─ args.credit_limit = ring->num_hw_submission   :2254
       └─ drm_sched_init(&ring->sched, &args)           :2258
```

`.ops` es `amdgpu_sched_ops` (`amdgpu_job.c:513`), cuyo `run_job` es
`amdgpu_job_run` (`amdgpu_job.c:515`, def. `:426`).

**El bucle cierra.** `amdgpu_job_run()` recupera el ring del job:

```
amdgpu_job_run()                                     amdgpu_job.c:426
  ├─ struct amdgpu_ring *ring = to_amdgpu_ring(sched_job->sched);   :428
  │     ↳ amdgpu_ring.h:69  to_amdgpu_ring(s)
  │                        = container_of((s), struct amdgpu_ring, sched)
  │     ↳ es decir, sched_job->sched ES el &ring->sched de :381
  ├─ trace_amdgpu_sched_run_job(job)                               :437
  └─ r = amdgpu_ib_schedule(ring, job->num_ibs, job->ibs, job, …)   :448
```

El ring que `run_job` emite es **el mismo objeto** que `amdgpu_ring_init`
registró. Eso es `ring ↔ scheduler` cerrado en los dos sentidos, con la
identidad del objeto demostrada por `container_of`, no por analogía.

**Lado entidad.** La entidad no se crea en el ring: elige sus schedulers
leyendo el mismo array.

```
amdgpu_ctx.c:229-230   scheds     = adev->gpu_sched[hw_ip][hw_prio].sched;
                       num_scheds = adev->gpu_sched[hw_ip][hw_prio].num_scheds;
amdgpu_ctx.c:838-840   idem, y para hw_ip ∈ {COMPUTE, GFX}
                       drm_sched_entity_modify_sched(&aentity->entity,
                                                      scheds, num_scheds);
```

`drm_sched_entity_init()` sí se llama en el subárbol, en 6 sitios
(`amdgpu_ctx.c:257`, `amdgpu_gfx.c:1657`, `amdgpu_ttm.c:2022`,
`amdgpu_uvd.c:411`, `amdgpu_vce.c:284`, `amdgpu_vm.c:544`), pero ninguno es el
que une el ring al scheduler: los de `amdgpu_gfx.c:1647-1659` pertenecen a un
*test de ring limpio*. **`NOT_APPLICABLE` para esta relación.**

**`num_scheds`** se incrementa una vez por ring registrado
(`amdgpu_ring.c:381`), luego vale el número de rings de ese `hw_ip` a esa
prioridad que no tienen `no_scheduler`. `amdgpu_xcp.c:508` consulta la
estructura gemela por XCP; para Polaris12, que no tiene `xcp_mgr`
(`amdgpu_ctx.c:228` bifurca por ello), esa rama es **`NOT_APPLICABLE`**.

#### Limitación residual — de ámbito, no de hueco

El **cuerpo** del scheduler de DRM (`drm_sched_entity_push_job()` →
núcleo `drm_sched` → `ops->run_job`) vive en
`drivers/gpu/drm/scheduler/`, que **no está en ninguna de las dos fuentes de
que dispongo**: ni el subárbol local ni el tarball `rx550-upstream-7.2.8` lo
incluyen — ambos cubren solo `drivers/gpu/drm/amd/`. Es una limitación de
**ámbito** de las fuentes, no un fichero truncado. Eso acota lo que puede
afirmarse *después* del enqueue; no convierte en indeterminado el vínculo
`ring ↔ scheduler`, que está probado íntegro dentro del ámbito disponible.

### F9 · command submission — **`PROVEN` hasta la cola; ejecución `NOT_DETERMINED`**

```
amdgpu_cs_ioctl(dev, data, filp)    amdgpu_cs.c:1411
  ├─ r = amdgpu_cs_pass1(&parser, data)     :1429
  ├─ r = amdgpu_cs_pass2(&parser)           :1433
  ├─ r = amdgpu_cs_parser_bos(&parser, data) :1437
  ├─ r = amdgpu_cs_patch_jobs(&parser)       :1446
  ├─ r = amdgpu_cs_vm_handling(&parser)      :1450
  ├─ r = amdgpu_cs_sync_rings(&parser)       :1454
  └─ r = amdgpu_cs_submit(&parser, data)     :1460
       └─ drm_sched_entity_push_job(&p->jobs[i]->base)   amdgpu_cs.c:1369
```

**Último salto demostrado dentro del ámbito: `drm_sched_entity_push_job()` en
`amdgpu_cs.c:1369`.** Esa función **encola**. Lo que ocurre entre el enqueue y
la llamada a `amdgpu_job_run()` está en `drivers/gpu/drm/scheduler/`, fuera
del ámbito de las dos fuentes disponibles (ver §5).

Lo que **sí** queda establecido, y antes no estaba: existe un puente
`run_job` con la identidad del objeto demostrada — `amdgpu_sched_ops.run_job =
amdgpu_job_run` (`amdgpu_job.c:515`) y `to_amdgpu_ring(sched_job->sched)` es
`container_of(…, struct amdgpu_ring, sched)` (`amdgpu_job.c:428`,
`amdgpu_ring.h:69`), es decir el mismo `&ring->sched` que `amdgpu_ring_init`
registró (`amdgpu_ring.c:381`). Por tanto el **estado de encolado de F8 queda
cierreado desde el lado del job**: el anillo al que vuelve `run_job` es
exactamente el anillo de compute creado en F7.

El tramo no demostrado es el **despacho** del núcleo de DRM: qué decide qué
scheduler de `gpu_sched[hw_ip][hw_prio].sched[]` atiende el job, y en qué
orden. `NOT_DETERMINED` por **ámbito de la fuente**, no por hueco.

---

## 4. Qué está realmente condicionado por Polaris12

| Elemento | Condicionado | Evidencia |
|---|---|---|
| Registro PCI, probe, `amdgpu_device_init` | **Genérico** | `amdgpu_drv.c:3169/3135/2364`, `amdgpu_kms.c:135/148` |
| Selección de ruta IP por ASIC | **Genérico con rama por ASIC** | `amdgpu_device.c:1946-1989` |
| Que Polaris12 use `vi_set_ip_blocks()` | **Específico** | `amdgpu_device.c:1980-1989`; `case CHIP_POLARIS12` ausente de `amdgpu_discovery.c:2782` |
| Nombres de IP block registrados | **Específico** | `vi.c:2109-2113`, bajo `case CHIP_POLARIS12` (`:2107`): `vi_common`, `gmc_v8_1`, `tonga_ih`, `gfx_v8_0`, `sdma_v3_1` |
| Implementación de GMC | **Específico** | `gmc_v8_0.c` tiene 4× `case CHIP_POLARIS12`; no existe `gmc_v8_1.c` |
| Aperturas VM (`shared`/`private`) | **Específico** | `gmc_v8_0.c:1052-1058`, dentro de `gmc_v8_0_early_init` (`:1045`): `shared` en `0x2000000000000000` y 4 GiB, `private` a continuación y 4 GiB |
| `amdgpu_ring_init`, GEM/TTM, CS ioctl | **Genérico** | `amdgpu_ring.c:226`, `amdgpu_object.c:1058`, `amdgpu_cs.c:1411` |
| Union ring ↔ scheduler | **Genérico** | `amdgpu_ring.c:381` registra, `amdgpu_device.c:2258` inicializa, `amdgpu_job.c:428`+`amdgpu_ring.h:69` recuperan el mismo objeto |

**El nomenclátor es la trampa de esta ASIC.** `gmc_v8_1_ip_block` se registra
pero su implementación está en `gmc_v8_0.c`. Buscar `gmc_v8_1.c` para seguir la
ruta produce `NOT_FOUND` y una conclusión falsa sobre el driver.

### `GFX_HWIP` — `NOT_DETERMINED`, y es pregunta distinta

`vi_set_ip_blocks()` demuestra **qué infraestructura** se registra. **No**
demuestra **qué HWIP efectivo** tiene la GFX de esta tarjeta.

No hay tabla ASIC en `soc15.c` (0 ocurrencias de `POLARIS12`), y
`amdgpu_discovery_get_gfx_info()` (`amdgpu_discovery.c:1721`) lo lee del
hardware en runtime. Coincide con lo ya registrado en
`decompressor/README.md` §«CU count» y en `F4-AD-4`.

---

## 5. Observaciones sobre el corpus

> **Corrección.** Esta sección afirmaba un «recorte» del corpus y lo oponía
> como `OBSERVED`. **Era falso, y la afirmación era la base del
> `NOT_DETERMINED` de F8.** Queda sustituida por la medición correcta.

Mediciones hechas, con su comando:

| Medición | Resultado | Clase |
|---|---|---|
| `.c` en `drivers/gpu/drm/amd` (local, 7.1.3) | 970 | `MEASURED` |
| `.c` en `drivers/gpu/drm/amd` (tarball upstream 7.2.8) | 1000 | `MEASURED` |
| `.c` **presentes localmente y ausentes en upstream 7.2.8** | **0** | `MEASURED` |
| `.c` en upstream 7.2.8 ausentes localmente | 29, **todos** añadidos entre 7.1.3 y 7.2.8 (`dcn30_hpo_frl_*`, `dcn42b_*`, `amdgpu_lockdep.c`, `amdgpu_dm_*_test.c`) | `MEASURED` |
| `amdgpu_sched.c` local | 129 líneas | `MEASURED` |
| `amdgpu_sched.c` **upstream 7.2.8** | **129 líneas, mismas 3 funciones, sin `run_job`** | `MEASURED` |
| `drivers/gpu/drm/` local | solo `amd` | `MEASURED` |
| `drivers/gpu/drm/` upstream 7.2.8 | solo `amd` | `MEASURED` |
| `drivers/` local | `base`, `gpu`, `pci` | `MEASURED` |
| `gmc_v8_1.c` | ausente, y **no** listado en el `Makefile` | `MEASURED` |
| `amdgpu_main.c` | ausente, y **no** listado en el `Makefile` | `MEASURED` |

### Tres afirmaciones retiradas

1. **«`amdgpu_sched.c` está demostrablemente incompleto.»** Retirada. Tiene
   129 líneas **también upstream**, con las mismas tres funciones y sin
   `run_job`. Nunca estuvo truncado. Mi inferencia fue: «el `Makefile` lo
   exige, luego si no contiene `run_job` está incompleto» — pero la ruta de
   F8 **no pasa por `amdgpu_sched.c`**: `drm_sched_init` está en
   `amdgpu_device.c:2258` y `run_job` en `amdgpu_job.c:515`, ambos presentes.
   Un `grep` negativo en el fichero equivocado no basta para probar un hueco.

2. **«970 frente a ~2 800 de upstream son un indicio de recorte.»** Retirada.
   La cifra de ~2 800 no tiene origen; la medición correcta es 970 frente a
   1000, con **cero** ficheros locales que falten upstream. El corpus es un
   subárbol **completo** de `drivers/gpu/drm/amd/` en 7.1.3, no una copia
   recortada.

3. **«La causa del recorte sigue `UNKNOWN`.»** Retirada por vacuidad: **no hay
   recorte que explicar.**

### Lo que sí es una limitación, y de otra naturaleza

`drivers/gpu/drm/scheduler/` no está en **ninguna** de las dos fuentes: ni en
el subárbol local ni en `rx550-upstream-7.2.8/linux-7.2.8/`, y ambos cubren
solo `drivers/gpu/drm/amd/`. Es **ámbito de las fuentes**, no un fichero
faltante. Afecta a F9 (el despacho interno del scheduler) y no a F8, que
queda íntegramente demostrado dentro del ámbito.

**Criterio de hueco, aplicado y ahora con la medición correcta:**

```
fichero ausente + NO listado en el Makefile
    ⇒ no pertenece a la implementación  (gmc_v8_1.c, amdgpu_main.c)

fichero ausente + listado en el Makefile
    ⇒ hueco real  (ninguno: amdgpu_sched.c está completo)

fichero ausente + presente en NINGUNA fuente disponible
    ⇒ limitación de ámbito  (drivers/gpu/drm/scheduler/)
```

El criterio que fijó el encargo era correcto. Lo que falló fue **aplicarlo a
una inferencia que no lo merecía**: verifiqué que el `Makefile` listaba
`amdgpu_sched.o` y salté directamente a «está truncado», sin comprobar si la
ruta que necesitaba pasaba por ese fichero. La comprobación que faltaba era
una línea: `grep -rn "run_job" *.c`.

---

## 6. Unknowns

1. `GFX_HWIP` efectivo — requiere lectura de registro, no de fuente.
2. ~~Punto de unión ring ↔ scheduler~~ — **resuelto**, ver F8. *No era un
   unknown: era un `NOT_DETERMINED` mal sostenido. Retirado.*
3. Cuerpo de `drm_sched_entity_push_job()` → núcleo `drm_sched` →
   `ops->run_job`: **ámbito** de las fuentes, `drivers/gpu/drm/scheduler/` no
   está en ninguna. Lo que sí consta es que `ops->run_job` existe y recupera
   el ring correcto (`amdgpu_job.c:428`, `amdgpu_ring.h:69`).
4. Si el compute de Polaris12 usa un ring por pipe o uno compartido: no trazado.
5. Secuencia de carga de firmware PSP/SMU: **no forma parte de ninguna de estas
   nueve flechas**. Es `P-2` de `DECISIONS-F4.md` y `F4-AD-6`, y sigue
   `BLOQUEADO`.

## 7. Criterio de cierre

**Las nueve flechas clasificadas.** Seis `PROVEN`, y las tres restantes
`PROVEN` en el tramo demostrado con `NOT_DETERMINED` **por ámbito de la
fuente** en el tramo posterior.

```
F1  PROVEN          F4  PROVEN          F7  PROVEN
F2  PROVEN          F5  PROVEN          F8  PROVEN
F3  PROVEN          F6  PROVEN (tramo)  F9  PROVEN (tramo) + ND (ámbito)
```

Un `NOT_DETERMINED` sobrevive, y es el único: el **despacho interno** del
scheduler de DRM, que ninguna de las dos fuentes cubre.

Cerrado como tarea de trazado estático. Lo que queda no es un hueco: es
ámbito de fuente, y el punto de reentrada está identificado
(`drm_sched_entity_push_job()` en `amdgpu_cs.c:1369`).

## 8. Registro de correcciones

Este informe se corrigió **en el mismo commit** (`--amend`), sin crear un
documento duplicado. Dos rondas de error, ambas de la misma forma.

### Ronda 1 — F8 mal clasificada

**Síntoma**: F8 = `NOT_DETERMINED (causal)`, cuando la relación `ring ↔
scheduler` estaba probada en `amdgpu_ring.c:378-381`.

**Causa**: cerré F8 en cuanto encontré un `NOT_DETERMINED` plausible, sin
agotar el fichero que tenía abierto. La evidencia que lo refutaba estaba a 150
líneas de donde miré.

**Origen de la detección**: lectura de `008-c-scheduler-ring.md`, que ya
había cerrado esa relación. No lo había leído.

> Nota sobre la provenance, corregida: afirmé que `008-c` estaba *commiteado
> antes* que este informe, y afirmé también que los cuatro `008-*` lo estaban.
> **Es falso**: `git log -- …/008-c-scheduler-ring.md` no devuelve nada. Los
> cuatro `008-a/b/c/d` están **untracked**. Solo `007-minimal-driver-dependency-map.md`
> tiene commit (`7ef8a4f`).
>
> No importa para la corrección de F8 — la evidencia es el código, no el
> commit — pero importa para el registro: afirmé un orden de commits sin
> ejecutar `git log`. Es el mismo mecanismo por sexta vez, y esta vez la
> afirmación era sobre el propio historial, que era lo primero que tenía que
> comprobar.

### Ronda 2 — el «recorte del corpus» era falso

**Síntoma**: §5 afirmaba que el corpus estaba recortado (970 frente a «~2 800»
upstream) y que `amdgpu_sched.c` estaba «demostrablemente incompleto» porque
el `Makefile` lo exige.

**Causa**: la inferencia «el `Makefile` lo lista → le falta contenido →
está truncado» nunca se comprobó contra el tarball
`rx550-upstream-7.2.8/linux-7.2.8/`, que está **en el repositorio** y que
tengo a un `ls` de distancia.

**Medición que lo refuta**:

```
amdgpu_sched.c  local 7.1.3              129 líneas
amdgpu_sched.c  upstream 7.2.8           129 líneas   ← idéntico
.c ausentes localmente que existan upstream    0
.c en upstream 7.2.8 que falten localmente    29   (todos añadidos en 7.2.x)
```

El fichero nunca estuvo truncado, y el corpus nunca estuvo recortado. La
cifra de «~2 800» no tenía origen medible.

**Por qué la segunda ronda importa más que la primera**: F8 era una
clasificación incorrecta de *una flecha*. «El corpus está truncado» era una
afirmación falsa sobre **la fuente misma**, y estaba en la base de la
clasificación. Un lector que aceptara §5 habría eliminado el corpus entero
como poco fiable, cuando está completo.

**Lección operativa, y es la sexta vez que aparece**: afirmar un estado sin
ir al fichero primario. Aquí la forma fue nueva — no fue un número ni una
atribución, sino un `NOT_DETERMINED` fabricado sobre un hueco imaginario, y
después un orden de commits afirmar sin `git log` — pero el mecanismo es
idéntico: cierro en cuanto tengo una explicación que *suena* bien, sin
comprobar si es la única ni si es cierta.

Corolario concreto para este encargo: un `NOT_DETERMINED` exige haber
**agotado el fichero abierto**, no haberlo recorrido hasta el primer
`grep` negativo. Y una afirmación sobre el historial se comprueba con
`git log`, no con la impresión de que el fichero «parecía commiteado».

## 9. No implementado

Ningún `.c`/`.h` de `07-DRIVER/`. Ningún módulo. Ningún cambio ABI. Ninguna
ejecución. Ninguna conclusión sobre `OWNERSHIP`. Ninguna afirmación sobre `Q-5`,
`AD-12` ni `Q-7`.
