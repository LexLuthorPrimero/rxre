# Addenda incremental — ASIC, counters, telemetry y valor informacional

**Fecha:** 2026-09-24
**Tipo:** actualización documental focalizada; no es una auditoría integral nueva.
**Modo:** no se ejecutaron probes, benchmarks, scripts, tuning ni escrituras de sistema. No se programaron selectors.

## 1. Propósito y alcance

Esta addenda incorpora al mapa de conocimiento la investigación específica sobre:

- identidad ASIC/PCI;
- catálogo GFX8;
- PMU y sysfs;
- RADV/radeonsi;
- GPUPerfAPI/CodeXL/UMR/RGP/Perfetto;
- límites entre source, catálogo, API, runtime y validación física.

No se modifica el estado de los experimentos históricos. Las afirmaciones anteriores se conservan y se corrigen sólo cuando una afirmación fuerte interpretaba catálogo o presencia de herramienta como capacidad runtime.

## 2. Correcciones conceptuales y trazabilidad

### 2.1 Correcciones de afirmaciones anteriores

| Afirmación anterior | Corrección vigente | Trazabilidad |
|---|---|---|
| “UMR + radeontop funcionales” como evidencia de counters HW GFX8 | La operación/readout histórico de una herramienta no demuestra selectors válidos ni validación ASIC. UMR es principalmente debugger/registros; radeontop/pf/sensores son proxies o accounting según la interfaz. | `FASE-D-GFX8-EVENT-ID-AUDIT.md`; `POLARIS12-MAP.md`; esta addenda |
| “GPUPerfAPI soporta GFX8” como si validara la RX550 | GPUPerfAPI tiene catálogo GFX8 genérico. `GDT_GFX8_0_4` activa definitions `gfx8_baffin`, pero eso no prueba identidad comercial Baffin ni selectores físicos. | `device_info`, GPUPerfAPI v3.17/v3.11.1 |
| “GRBM=2 / SQ=4” como eventos GFX8 utilizables | Son entradas de catálogo y/o constantes de generaciones GFX10/GFX11. No son selectores validados para `1002:699f`. | `FASE-D-GFX8-EVENT-ID-AUDIT.md`; esta addenda |
| “perf/radeontop exponen contadores GFX8” sin distinguir runtime | El PMU mainline no registra GFX8/Polaris12 en los tags inspeccionados. Una extensión, backport o herramienta externa no se cuenta como capability local. | Linux `amdgpu_pmu.c`; esta addenda |
| “RADV performance counters disponibles para GFX8” | La feature pública `VK_KHR_performance_query` no se anuncia para GFX8 en el source RADV comparado. El código legacy no equivale a runtime. | Mesa 26.2.2/26.2.3 source |
| “equivalencia `gfx803/gfx804` resuelta” | El mapa neutral `Polaris12/GFX8` es correcto; la equivalencia exacta nominal `gfx803/gfx804` no se fuerza. `1002:699f` queda catalogado como `GDT_GFX8_0_4/gfx804`, mientras Mesa identifica el camino local como `CHIP_POLARIS12`. | `device_info`; Mesa `amd_family` |

### 2.2 Cadena de conocimiento: GPU → counters → telemetry → workload → bottleneck

```text
GPU/ASIC identity
  ↓
hardware counter capability
  ↓
source/catalog definitions
  ↓
API exposure
  ↓
runtime capability
  ↓
physical counter validation
  ↓
telemetry usable
  ↓
workload phase and demand
  ↓
bottleneck attribution
  ↓
controlled optimization decision
```

Reglas:

1. Un catálogo no sustituye API exposure.
2. Una API source-level no sustituye runtime capability.
3. Una feature runtime no sustituye validación física del counter.
4. `gpu_busy_percent`, `mem_busy_percent` y `pcie_bw` no son selectores programables.
5. Un proxy no se convierte en bandwidth, wattmeter, vblank o first pixel.
6. Un counter no validado no debe entrar en una decisión de optimización.
7. El workload sólo puede atribuirse a un bottleneck cuando la telemetría disponible tiene alcance y unidades defendibles.

## 3. Identidad y capas de evidencia

| Capa | Hecho vigente | Estado | Lo que no demuestra |
|---|---|---|---|
| PCI/local | `1002:699f`, RX550, Polaris12/GFX8 | `CONFIRMED` | Revisión PCI, stepping, VBIOS o equivalencia comercial universal |
| Catálogo `device_info` | `GDT_GFX8_0_4` / `gfx804` | `SUPPORTED` | Identidad física marketing o equivalencia Baffin |
| Mesa | `CHIP_POLARIS12`, camino GFX8 | `SUPPORTED` | Que todos los paths de una versión de Mesa estén en runtime |
| Catálogo GPUPerfAPI | `GDT_GFX8_0_4` recibe definitions `gfx8_baffin` | `SUPPORTED` | Selectores válidos para `1002:699f` |
| API RADV | `VK_KHR_performance_query` no anunciado para GFX8 | `NOT_AVAILABLE` | Que no exista otra API de instrumentación |
| API radeonsi | `groups_VI` / `GL_AMD_performance_monitor` source-level GFX8 | `SUPPORTED` | Runtime local y stepping concreto |
| PMU mainline amdgpu | No hay caso GFX8/Polaris12 en `amdgpu_pmu_init()` de los tags inspeccionados | `NOT_AVAILABLE` | Que un kernel out-of-tree o backport no añada otro camino |
| UMR | Database tiene `0x699F/polaris12.asic` y registros | `SUPPORTED` como database/debug | Tabla de eventos o lectura runtime |
| Perfetto | `gpu.counters` es un esquema/producer | `SUPPORTED` como framework | PMU o counter físico |

### 3.1 Matriz explícita de niveles de soporte

| Nivel | Pregunta que responde | Estado GFX8 local | Evidencia que lo sostiene | No sustituye a |
|---|---|---|---|---|
| **Source-level support** | ¿Existe una implementación, registro o ruta en el código? | `PARTIALLY_SUPPORTED` | Mesa/kernel/radeonsi/UMR source | catalog, API ni runtime |
| **Catalog support** | ¿Existe una definición/evento en un catálogo? | `SUPPORTED` | GPUPerfAPI/CodeXL/UMR catalogs | API, runtime ni ASIC |
| **API exposure** | ¿La función está expuesta públicamente por la API? | `NOT_AVAILABLE` para RADV GFX8; `SUPPORTED` source-only para radeonsi | Source gates/headers | runtime ni validación física |
| **Runtime capability** | ¿La función está disponible y usa la placa local? | `UNKNOWN` | No hay consulta runtime nueva autorizada | evidencia física ni causalidad |
| **Physical counter validation** | ¿Un selector/evento fue leído y validado en `1002:699f`? | `UNKNOWN` | No realizada; programación prohibida | — |

Una afirmación sólo puede avanzar de nivel cuando existe evidencia del nivel siguiente;
una versión de catálogo o una ruta source-level no se sustituyen entre sí.

## 4. Estado actualizado de counters

**Estado agregado del bloque:** `PARTIALLY_SUPPORTED` a nivel catálogo/source;
`NOT_AVAILABLE` para el PMU mainline GFX8 confirmado; `UNKNOWN` para runtime,
selectores y validación física.

| Elemento | Estado final | Uso permitido |
|---|---|---|
| Catálogo GFX8 | `SUPPORTED` como referencia source/catalog | Investigar denominadores y nomenclatura, nunca escribir selectores |
| Selectores concretos para `1002:699f` | `UNKNOWN` | No usar para causalidad |
| Programación GFX8 | `UNKNOWN` | No ejecutar; prohibida por ahora |
| PMU mainline GFX8 | `NOT_AVAILABLE` como PMU confirmado | No inferir que el hardware no tenga contadores internos |
| `gpu_busy_percent` | `SUPPORTED` como proxy SMU | Actividad agregada, no PMU |
| `mem_busy_percent` | `SUPPORTED` como proxy SMU | Actividad de memoria, no bytes/s |
| `pcie_bw` | `SUPPORTED` como estimación/accounting PCIe | Diagnóstico, no selector programable |
| UAPI sensors/timestamps | `SUPPORTED` como consultas | No equivalen a events programables |
| RADV `VK_KHR_performance_query` GFX8 | `NOT_AVAILABLE` como feature pública comparada | No usar como API GFX8 |
| radeonsi GFX8 perf path | `PARTIALLY_SUPPORTED` (source `SUPPORTED`; runtime `UNKNOWN`) | Sólo referencia de implementación |
| UMR | `SUPPORTED` como database/debug | No como tabla de eventos validada |
| CodeXL/GPUPerfAPI | `SUPPORTED` como catálogo/histórico | No como runtime/ASIC |
| RGP actual | `NOT_AVAILABLE` como soporte GFX8 documentado | No seguir esta rama ahora |
| Perfetto | `SUPPORTED` como framework | No usarlo como prueba de counter físico |

## 5. Cadena de telemetría y atribución

| Relación | Estado | Consecuencia |
|---|---|---|
| GPU → source/catalog | `SUPPORTED` | Permite identificar mecanismos y denominadores |
| Source/catalog → API | `PARTIALLY_SUPPORTED` | No toda definición tiene feature pública |
| API → runtime | `UNKNOWN` para counters GFX8 | No se puede afirmar capacidad local |
| Runtime → physical counter | `UNKNOWN` | No se puede cerrar selector ASIC |
| GPU → SMU busy | `SUPPORTED` como proxy | Sirve para fases, no para unidades específicas |
| SMU busy → bottleneck | `NOT_INFERABLE` por sí solo | Necesita correlación con workload y otras métricas |
| Workload → bottleneck | `HYPOTHESIS` hasta separar CPU/GPU/memory/WSI | No convertir correlación en causalidad |
| Bottleneck → optimización | `UNKNOWN` hasta medir gain reproducible | No ofrecer tuning como resultado |

## 6. Evaluación incremental de las áreas A–K

| Área | Conocimiento actual/evidencia | UNKNOWN principal | Impacto FPS / frametime / validez | Coste, riesgo y dependencias | Read-only | Prioridad | Decisión que puede cambiar |
|---|---|---|---|---|---|---|---|
| A. CPU/Haswell | 4C/8T, 8 MB cache, DDR3-1600 teórico; Intel ARK; `intel_pstate`/governor y frecuencia real por verificar | governor/frecuencia real, thermal throttling, single-thread/draw-call headroom | Alto FPS/frametime; validity alta si CPU varía | Coste medio; riesgo bajo observacional; depende de ownership | Sí | P0 | Elegir workload, thread strategy o declarar CPU-bound |
| B. Agentes/servicios | Kalm/Kalm CPU/Kalm GPU documentados; `system-autopilot`, `sys-tuned`, `irqbalance` y otros agentes requieren estado de corrida | qué agentes tocan CPU/GPU/IRQ/almacenamiento/procesos | FPS/frametime/validity muy altos | Coste medio; riesgo de inspección bajo; depende de permisos/procesos | Sí | P0 | Excluir, congelar o aceptar un entorno contaminado |
| C. Scheduler/IRQ/HDD | Gen2×4, HDD, IRQ/PM source-level; particiones | IRQ affinity, read-ahead, HDD stalls, scheduler credits | FPS/frametime/validity | Coste medio; riesgo bajo si sólo lectura; depende de ownership | Sí | P1 | Elegir si la comparación es reproducible |
| D. Runtime PM | GPU puede suspenderse; documentación PM | modo real, wake, ASPM, first-frame penalty | FPS/frametime/validity | Coste bajo observación; riesgo alto si se cambia PM | Sí | P1 | Separar wake penalty o congelar runtime PM |
| E. Ownership/workload | Históricamente hubo conflictos/paranoid; DRI_PRIME target explícito | procesos GPU activos, colas, contaminación, concurrencia | FPS/frametime/validity altísimos | Coste bajo/medio; riesgo bajo si no se modifica; precede todo | Sí | P0 | Invalidar, repetir o aceptar corridas |
| F. CPU/GPU/WSI | WSI/timing capability limitada | CPU submit, GPU completion, compositor/display | Alto en todas | Depende de ownership y telemetría | Parcialmente | P1 | Elegir backend/objetivo de optimización |
| G. VRAM/GTT | 2 GiB, VIS/GTT observados | placement, evictions, bandwidth, working set | Alto si hay spill; validity | Coste medio; riesgo OOM; depende de memoria | Sí | P1 | Elegir resident/streaming path |
| H. MCLK | 300/625/1500; `CONFLICT` entre política upstream 5/16/20 y readout local 3/16/20 | trigger, histéresis, VBIOS/PPTable mapping | Alto si memoria/thermal; validity media | Coste medio; riesgo bajo observacional; depende de workload | Sí | P1 | Diseñar o congelar DPM/MCLK experiments |
| I. Power cap | 35W, 25/28/32/35 históricos; M1 no discriminativo; `699F:CF` containment desconocido | revisión exacta, feature containment, demanda que hace ligar | Alto si liga; frametime/validity | Coste bajo para identity, alto para write; depende de revisión/SMU | Sí | P0/P1 | Decidir si cap branch es válida o se congela |
| J. Mesa/ACO/DCC | Mesa 26.2.2, ACO default source; DCC/HTILE condicional; FMASK | code quality, DCC/HTILE, compiler variants, workload benefit | Medio/alto; validity de A/B | Riesgo medio process-local; depende de GPU counters/telemetría | Sí | P2 | Elegir A/B de Mesa o congelarlo |
| K. Counters | Catálogo source; PMU mainline no GFX8; runtime `UNKNOWN` | selector ASIC, physical validation, units | No usable para causalidad hasta resolver | Coste técnico alto; riesgo de programación muy alto; no es un prerrequisito actual | Parcialmente | P3 | Sólo reabrir si una decisión concreta necesita un counter |

### 6.1 Anclas de evidencia disponible (sin nueva ejecución)

| Área | Evidencia documental/observacional ya disponible | Lo que no cubre |
|---|---|---|
| A | CPU/ARK, identificación i7-4790, governor/thermal y R-4B | Frecuencia efectiva y throttling de cada corrida |
| B | `MASTER-RESEARCH-STATUS.md`, auditorías read-only de agentes/background, Kalm, `system-autopilot`, `sys-tuned` e `irqbalance` | instantánea del estado de cada proceso en una corrida futura |
| C | R-4A PCIe, inventario de almacenamiento, IRQ/PM source-level | afinidad, readahead y stalls de una workload concreta |
| D | Kernel PM source/docs, estado DPM y Telemetría histórica | wake-ups, residence y first-frame de la RX550 |
| E | DRI_PRIME/ICD explícito, H12-2 r3, ownership histórico | lista completa de clientes concurrentes en cada corrida |
| F | H12-2 WSI evidence, Vulkan headers/source, timestamps | atribución causal CPU/GPU/WSI |
| G | R-4A VRAM/GTT, `mem_info_*`, RADV/radeonsi source | working set, evictions y placement por frame |
| H | `pp_dpm_mclk`, R-0-2 policy source, DPM logs | trigger local, histéresis y relación causal con workload |
| I | R-4A, power docs, M1/EP-06 cap observations | revisión/containment exacto y demanda que haga ligar el cap |
| J | Mesa 26.2.2 source, R-0-3 workarounds, DCC/FMASK source | ganancia de A/B y efecto runtime por workload |
| K | FASE-D audit, R-0/R-1 catalogs, kernel/Mesa source comparatives | selector ASIC y lectura física validada |

## 7. Ranking por valor informacional

El criterio es: **cuánta capacidad tiene la incógnita para cambiar las siguientes decisiones**, no cuánto resultado resultaría interesante.

### Rank 1 — P0: gate de entorno, ownership y reproducibilidad

**Incógnita:** ¿los resultados observados son atribuibles a la workload de la RX550 o están alterados por clientes, Kalm/agentes, CPU governor, IRQ, PM, scheduler, HDD, almacenamiento y estado térmico?

- Puede invalidar o cambiar prácticamente todos los experimentos.
- Es resoluble read-only.
- No requiere counters, tuning ni escrituras.
- Es dependencia de CPU/GPU/memory/WSI/MCLK/cap.

### 7.1 P0 — alcance READ-ONLY del siguiente bloque (NO EJECUTADO)

El bloque resolvería una sola pregunta de atribución: **¿la corrida pertenece a la workload
de la RX550 y conserva un entorno estable?** La observación sería puntual y comparativa,
sin cambiar procesos, servicios, governors, IRQ, scheduler, runtime PM, DPM ni power cap.

| Componente | Lectura permitida | Salida esperada |
|---|---|---|
| Ownership | procesos, file descriptors y clientes que referencian `card1`/`renderD129`/`1002:699f` | lista de clientes, PID, workload y target |
| Agentes | unidades/timers enabled, procesos Kalm/CPU/GPU, `system-autopilot`, `sys-tuned`, `irqbalance` y candidatos | tabla de mecanismo → recurso que podría afectar |
| CPU | `intel_pstate`/governor, frecuencia instantánea, temperatura y política de escalado | rangos y eventos de throttling |
| IRQ/scheduler | afinidad IRQ, threads del proceso, scheduling policy y read-ahead de HDD | afinidad/stall/read-ahead potencialmente explicados |
| Runtime PM | estado PM, autosuspend, ASPM y residency de la RX550 | wake/residency observados, sin write |
| Identidad/power | BDF, revisión PCI, VBIOS/PPTable/SMU metadata, enlace y containment | Revisión exacta y validez de la rama de cap |
| Telemetría | timestamps, procesos, lectura de sysfs/hwmon, logs de error y target Vulkan/GL | snapshot sincronizado por corrida |

No se deduce causalidad de una sola muestra. Una lectura de PM/IRQ puede despertar el
dispositivo o cambiar el estado observado; por eso se registra antes/después y una
lectura que perturbe el residency se marca `CONFLICT` o `NOT_INFERABLE`, no se
interpreta como estado natural. Si se observan clientes o agentes que alteran el
entorno, la corrida queda marcada `CONFLICT` o `NOT_INFERABLE` según el caso; no se
corrige el entorno automáticamente.

### Rank 2 — P0: identidad PCI/revisión, containment y coherencia firmware

**Incógnita:** ¿qué revisión real es `1002:699f`, está activo el path de power containment y qué VBIOS, PPTable y estado de carga SMU están presentes?

- Decide si la rama de power cap tiene una base válida.
- Puede evitar seguir persiguiendo una variável sin efecto físico.
- Coste read-only bajo; no autoriza escrituras.

### Rank 3 — P1: demanda que hace ligar cap/DPM

**Incógnita:** ¿qué workload y qué fase elevan `W_SMU`/clocks hasta un punto donde el cap pueda ser discriminante?

- Decide si cap 25/28/32/35W merece un experimento futuro.
- Depende de ownership y workload estable.
- Primero observación; cualquier escritura queda fuera de alcance.

### Rank 4 — P1: VRAM/GTT/TTM working set

**Incógnita:** ¿la workload se mantiene resident en VRAM o produce migraciones/evictions hacia GTT?

- Puede cambiar de forma material FPS, p99 y memoria host.
- Read-only para estado; el diseño de carga futura requiere autorización.
- Counters no son un prerrequisito: VRAM/GTT usage, page/allocations y timing pueden iniciar la clasificación.

### Rank 5 — P1: CPU/driver/WSI attribution

**Incógnita:** ¿el frame está limitado por CPU/submission/queue, GPU execution, memory o WSI?

- Decide si optimizar shaders, compiler, allocator, CPU batching o presentación.
- Depende de ownership limpio y de metrics de submit/queue.
- No se puede resolver sólo con `gpu_busy_percent`.

### Rank 6 — P1: MCLK trigger

**Incógnita:** ¿qué working set/fase provoke MCLK 1500 y con qué histéresis?

- Importa si la carga es memory-sensitive.
- No debe inferirse de `mem_busy_percent` ni de la policy 5/16/20.
- Puede quedar congelada hasta que P0 y P4 estén resueltos.

### Rank 7 — P2: DPM, thermal y residence

**Incógnita:** ¿la variabilidad de clocks/thermal explica tails sólo bajo demanda?

- Importa para reproducibilidad y p95/p99.
- Depende de una workload controlable y baseline estable.
- No se debe modificar DPM/thermal governor en esta fase.

### Rank 8 — P2: Mesa/ACO/DCC/FMASK

**Incógnita:** ¿qué code path y compression/resource policy mejora una workload concreta?

- Tiene valor después de saber qué bottleneck existe.
- No es el siguiente bloque por valor informacional.
- Un cambio de Mesa sin clasificación de bottleneck sería tuning especulativo.

### Rank 9 — P2/P3: Scheduler, IRQ, HDD, ReBAR/ASPM

**Incógnita:** ¿existen stalls o copia/link effects específicos?

- Importan sólo si ownership, CPU, memory o transfers muestran una señal.
- ReBAR y ASPM permanecen `UNKNOWN` de runtime.
- No deben investigarse por curiosidad técnica antes de P0/P3.

### Rank 10 — P3: GFX8 counters

**Incógnita:** ¿qué selector/evento físico puede medirse para `1002:699f`?

- No es el siguiente paso automático.
- Sólo se reabre si una decisión de optimización concreta necesita un counter que no puede sustituirse con telemetría disponible.
- Programación sigue prohibida.

## 8. Knowledge Sufficiency Point

**Estado actual:** `UNKNOWN`; todavía no se ha alcanzado.

El proyecto alcanzó sufficiency cuando:

1. cada corrida tiene target GPU, ownership, procesos, governor, PM, IRQ, storage y thermal metadata reproducibles;
2. se puede separar CPU/submission, GPU execution, memory/VRAM/GTT y WSI con métricas de alcance conocido;
3. el comportamiento de cap/DPM/MCLK está observado bajo workloads con demanda controlada;
4. placement/eviction y PCIe/host-memory effects pueden o no pueden cambiar la decisión de optimización;
5. los counters GFX8 son:
   - validados físicamente; o
   - explícitamente no necesarios para la decisión actual.

No es necesario eliminar todos los UNKNOWN. Basta con que los restantes no puedan cambiar materialmente la siguiente decisión.

## 9. Áreas temporalmente congelables

- **Counters GFX8:** P3; no reabrir sin una pregunta experimental concreta.
- **RGP/CodeXL/UMR:** P3; no instalar ni ejecutar como rama automática.
- **ReBAR/ASPM:** P3 hasta que transfers/PCIe/CPU demanden una explicación.
- **Async compute/ACE:** P2/P3 hasta saber si hay compute concurrency real.
- **DCC/FMASK/compiler tuning:** P2 después de conocer el bottleneck.
- **MCLK forzado, `high`/`profile_peak`, cap writes, PM writes:** congelados; requieren otro gate y autorización.

## 10. Fuentes de esta addenda

- `device_info` commit `7379d082f1d8d64c9d1168b84b7f6b2a9702c82f`, 2024-09-20.
- GPUPerfAPI v3.17 commit `18d231a175e8ddd8011ec5fc9ed8874522ff6c35`, 2024-09-20.
- GPUPerfAPI v3.11.1 commit `3e1d793c8fff22ba5a482ad7175259699991f338`, 2022-07-27.
- Linux v6.16 commit `038d61fd642278bab63ee8ef722c50d10ab01e8f`, 2025-07-27.
- Mesa 26.2.2 commit `3281a69a8bfd9f997e91c15ed0e6290cae12dd32`, 2026-09-02.
— **resuelto 2026-09-28: `RESOLVED_WRONG_OBJECT`; el valor documentado es el correcto (tipo `commit`); el otro SHA es el objeto de tag. Ver `PATCH-SOURCES.md` F12-bis / F12-ter.**
- Mesa 26.2.3 snapshot commit `31e9a6b2e95e30d84bf3177d1f497d063e59b6b2`, 2026-09-16.
- Vulkan local headers 1.4.341; comparativo Vulkan 1.4.363 commit `560d4305e8a6466fa7d07c83ca09429e4d010ff9`.
- Linux kernel local: `7.2.4-201.nobara.fc44.x86_64`.
- Rutas de evidencia histórica: `FASE-D-GFX8-EVENT-ID-AUDIT.md`, `R0-1`, `R1-1`, `POLARIS12-MAP.md`.

**No se ejecutó ninguna acción de sistema como parte de esta addenda.**
