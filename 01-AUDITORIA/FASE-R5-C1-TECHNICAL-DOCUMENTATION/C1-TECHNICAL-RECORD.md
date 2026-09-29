# RX550 — Registro técnico consolidado de investigación, C1 y automatizador v1.1.0

**Tipo:** documentación técnica / auditoría de trazabilidad
**Fecha de consolidate:** 2026-09-24
**Modo:** sólo lectura; no es autorización de ejecución
**Fuente primaria del estado:** `00-INDICE/MASTER-RESEARCH-STATUS.md` y Addendas
**Gate del entorno actual:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`

## 0. Reglas de lectura y clasificación

Este documento mantiene separados los tipos de enunciado:

- **Hecho observado:** lectura directa de hardware, sysfs, journal, proceso, archivo o log.
- **Inferencia:** conclusión razonada a partir de uno o más hechos, sin causalidad no demostrada.
- **Hipótesis:** explicación candidata todavía no discrimada.
- **Propuesta:** acción o diseño definido por el proyecto, todavía no ejecutado.
- **Criterio operativo:** regla de precheck, guard, aborto, validez o seguridad.
- **Resultado experimental:** dato producido por una corrida identificada.
- **UNKNOWN / NOT_AVAILABLE / CONFLICT:** ausencia de evidencia, ausencia del artefacto o desacuerdo entre fuentes.

Una cifra de `power1_input` se escribe como `W_SMU`/potencia estimada por el sensor SMU. No se presenta como vatímetro independiente salvo que una fuente indique lo contrario; no hay tal vatímetro en la evidencia del proyecto.

## 1. Arquitectura general

### 1.1 Objetivo

Investigar la RX550 Polaris12/GFX8, sus límites de energía, clocks, VRAM/GTT, submits y latencia, y construir una ruta reproducible que permita distinguir:

1. **hecho de la GPU/sistema**;
2. **estimador o proxy disponible**;
3. **métrica científica del workload**;
4. **hipótesis de bottleneck**;
5. **decisión o diseño de implementación**.

El objetivo no es declarar la GPU rápida/lenta por un único FPS, ni convertir una telemetría de sysfs en causalidad física, ni convertir una ruta de automatización en validación científica.

### 1.2 Hardware y contexto

| Elemento | Hecho observado | Fuente / límite |
|---|---|---|
| GPU | RX 550, Polaris12/GFX8, PCI `1002:699f`, BDF `0000:01:00.0`, driver `amdgpu` | `02-ARQUITECTURA/knowledge.md`, Gate P0; identidad reproducible |
| Nodo DRM | `card1`, `renderD129`, `hwmon2` | Preflight C1; rutas de una configuración concreta |
| Display | Intel HD 4600 en `card0`; la RX550 es GPU secundaria sin salida de video activa | Decisión de seguridad documentada; no usar RX550 como GPU de pantalla durante experimentos |
| Memoria GPU | VRAM 2 GiB; GTT observado ≈6.2 GB (≈5.77 GiB) | KNOWLEDGE Addenda; lectura del host, no capacidad de benchmark |
| DPM | `sclk` 214–1071 MHz (8 estados), `mclk` 300/625/1500 MHz (3 estados) | KNOWLEDGE/EP-08 |
| Power cap | `power1_cap` default/max 35 W; probe autorizado 25/28/32/35 W | Fase B, EP-06, M1; restores documentados |
| CPU | Intel Core i7-4790, 4C/8T, 12 GiB DDR3, Nobara Linux | Host documentado; no es evidencia de la GPU |
| Kernel | El C1 v1.1.0 espera `7.2.6-201.nobara.fc44.x86_64`; documentos históricos mencionan `7.2.4-201` | **CONFLICT** de snapshots; usar el valor vigente del Gate/C1 para esa fase |

El host, su almacenamiento y sus agentes pueden alterar latencia, D-state, PSI y telemetría. Por eso el proyecto no trata una corrida contaminada como atribución exclusiva de la RX550.

### 1.3 Software y componentes

- **Kernel/DRM/PowerPlay:** sysfs de `amdgpu`, DPM, `power1_*`, runtime PM y telemetría legible.
- **Mesa del sistema:** `/usr/lib64/...`; renderer stock observado.
- **Mesa CUSTOM de investigación:** `/opt/mesa-26.2.2-rx550-haswell`; se carga por entorno/proceso en EP-05, no es una configuración permanente.
- **Vulkan:** RADV/radeonsi; la selección debe confirmar explícitamente `0x699f`. `MESA_VK_DEVICE_SELECT=1002:699f` es insuficiente como prueba y históricamente seleccionó Intel.
- **C1:** binario `WORKLOAD-SINTETICO/main-graphics`, fuente `src/graphics.cpp`, observer `c1_observer.py`.
- **Automatizador:** `04-IMPLEMENTACION/c1_isolation_automator.py`, versión `1.1.0`.
- **Agentes/escenas:** Kalm, autopilot, tuned, irqbalance, Xwayland/KWin y clientes de escritorio se observan como fuentes de posible contaminación; no se modifica su configuración desde este registro.
- **Almacenamiento:** Btrfs/`sda`, PSI y D-state son capas de contexto relevantes para la validez y latencia, no métricas causalmente atribuibles a la GPU.

### 1.4 Relación entre capas

```text
GPU/ASIC y kernel
      ↓ sysfs/journal/PMU disponible
registro de telemetría
      ↓ jsonl/csv/manifest
workload y condición de corrida
      ↓ métricas observables
hipótesis/inferencia/claim
      ↓ gate de validez
decisión, diseño o backlog
```

La cadena no autoriza a saltarse una capa:

- una fuente de Mesa no reemplaza una lectura de la GPU;
- un cap leído no prueba que el regulator de potencia limitó el clock;
- una telemetría de VRAM/GTT no prueba que VRAM sea el bottleneck;
- un FPS no identifica por sí solo GPU, CPU, driver, present o VSync;
- un diseño C1 no equivale a un resultado C1;
- un automatizador fail-closed no equivale a aislamiento científico.

Las áreas del repositorio se relacionan así:

- `03-EXPERIMENTOS/`: datos, protocolos ejecutados, telemetría, resultados y artefactos de corridas.
- `02-ARQUITECTURA/`: identidad, conocimiento, hipótesis, evidencia resumida, preguntas abiertas.
- `01-AUDITORIA/`: reconciliación, gates, readiness, auditorías de propiedad/arquitectura y documentación.
- `04-IMPLEMENTACION/`: C1, observer, automatizador, tests, seguridad y diseño de herramientas; no convierte diseño en ejecución.
- `00-INDICE/`: estado maestro, decisiones, índices y navegación.
- `05-FUENTES-EXTERNAS/`: referencias y manifiestos externos, sin supplantar la evidencia local.

## 2. Línea temporal

La cronología mezcla fechas de resultados, timestamps de runtime y fechas de documentación. La zona horaria se conserva cuando la fuente la entrega; no se completa un timestamp ausente.

| Fecha/hora | Hito | Evidencia / configuración | Resultado o interpretación |
|---|---|---|---|
| 2026-09-17 | Descubrimiento y régimen histórico E1/E3/E5 | Sesión histórica; Mesa CUSTOM; cap 25 W; SCLK 330–390; MCLK ~1250–1500; 74–92 °C; phong ~1285 FPS; desktop ~443 FPS 1080p | **Hecho observado** en esa sesión. No se reprodujo después; la causa permanece `UNKNOWN`, no se convierte en especificación. |
| 2026-09-18 08:17 | Incidente Kalm | `kalm-gpu.service` muere con `Errno 16` al leer `power1_cap_max`; `kalmd.py`/`kalm-lite.py` continúan | Incidente observado. No demuestra que Kalm explique el régimen histórico. |
| 2026-09-18 14:05 | `rx550-power-sweep-20260918-140527` | Caps 25/35 W; kalm real activo; régimen libre 1071 MHz, ~9–10 W | Corrida histórica con CSVs desalineados; sólo raw parcialmente válido. Resultado no se mezcla con base actual. |
| 2026-09-19 11:42 | Fase A, discriminación | 3 GL + 3 VK phong + 3 VK default; device verificado; correcciones de selección Vulkan | Corridas 04–09 inválidas porque usaron iGPU Intel. La fase válida confirma que el selector de workload no resuelve por sí solo la causa histórica. |
| 2026-09-19 12:20 | Fase B, cap probe | 28 corridas; caps 25/28/32/35 W desde frío, N=2 por nivel; restore verificado | Curva plana: 1071 MHz y ~10.5–11.6 W. Rechaza el claim simple “cap 25 W liga SCLK” en esas escenas; no mide consumo eléctrico externo. |
| 2026-09-19 21:16 | EP-06 soak/replica | Soak cap 25 W; display Intel; condición de seguridad; E1 caliente | Sin pinzado hasta 71–72 °C; `W_SMU` observado 9.4–13.6 W, máximo 13.6 W; cap restaurado y verificado. No demuestra un máximo absoluto. |
| 2026-09-19 21:22 | EP-05 Mesa CUSTOM vs STOCK | A/B por proceso, 12 corridas + réplicas; verificar `/proc/<pid>/maps` | CUSTOM y STOCK indistinguibles en las escenas probadas; no se reproduce E5. Limitación: conjunto limitado de escenas y condiciones. |
| 2026-09-20 | M1 cap 35/30 W | `vkmark shading:phong` 1080p; 10 corridas pareadas | `power1_input @35 W` ~12.27 W, compuerta `<27 W` no discriminativa; ΔFPS y ΔSCLK pareados 0. El cap no se valida con esta métrica. |
| 2026-09-20/21 | WORKLOAD-SINTETICO E-01/E-02/E-03 | Vulkan, FMA/render y configuraciones controladas | Auto-pacing/fetch-latency soportado; 2× fetches ⇒ aproximadamente 2× frametime con `W_SMU` estable. Resultado sintético, no generalización a juegos. |
| 2026-09-21 | ES-01, F2 y R-14 | Escalado A–D+E, 8 fetches y superposición | `W_SMU` estable en ALUs/fetches; correlación de workload, no causalidad física demostrada. |
| 2026-09-21 | FASE D etapa 2 | A/B × 3, geometría/superposición, 6/6 válidas | A `W_SMU` ~22.25 W vs B ~15.78 W, ratio ~1.41; variables de exportación/geometría correlacionan. No se programa un counter causal. |
| 2026-09-21 | FASE D etapa 3 | Diseño/precheck/eventos | Diseñada, no ejecutada; UMR/RGP/radeontop fuera de la ruta permitida. |
| 2026-09-22 | R-0, R-1, R-2, R-3/R-3.1 | Knowledge externo, reconciliación, mapa global, novedad/fusión | Documentación y diseño/readiness; no genera una nueva corrida operacional. |
| 2026-09-22 | R-4A bandwidth | PCIe Gen2 x4, lectura de enlaces, estimaciones | Ancho de banda real no medido con carga; bandwidth sigue `NOT_AVAILABLE`. |
| 2026-09-22 | R-4C jitter | Observabilidad del harness, 8/8 corridas, mismo hardware/configuración relativa | MAE de intervalo de frame observado; métricas mejoradas, pero no prueba si el jitter proviene de GPU, driver, Xwayland, VSync o present. |
| 2026-09-23 | R-4B v2.1 → thermal test → v2.2/v2.3 | Ramp térmico N=2; cooldown pasivo; S1 v2.2 y luego S1 v2.3; S2 v2.3 | S1 v2.3 ejecutada/completada; S2 iniciada y detenida por condición D. Veredicto global `INCONCLUSIVE`, nunca `SUPPORTED`; no reintentar S2. |
| 2026-09-24 | Runtime PM / H4, read-only | `power/control=auto`, `runtime_status=active`, `autosuspend_delay_ms=5000`, wakeup no forzado | Se registró estado PM sin escribir `power/control` ni provocar wake; el efecto de wake/primer frame queda `UNKNOWN`, no se convierte en claim. |
| 2026-09-24 | H12-2 WSI r3 | 640×360, Wayland, RADV, 3 imágenes, FIFO, queue 0, timestamps/presentación; sin Programming Pipeline/RGP | `xdg_toplevel.state=4` confirmado; `2nd configure after present` observado. Clasificación B compatible con hipótesis A o B, pero no las separa; causalidad GPU `UNKNOWN`. |
| 2026-09-24 07:16:42–07:24:55 | Gate P0 | Snapshot read-only de host, CPU, IRQ, storage, PM, PCI, clientes y agentes | Gate B `CONTAMINATED_REQUIRES_ISOLATION`; ownership `PARTIAL`; no se autoriza un nuevo A/B hasta aislamiento verificable. |
| 2026-09-24 12:45:59–12:46:00 | C1 legacy run | `RUN_ID=20260924T154559Z-490709`, v1.0.0, `sudo -v` histórico, `isolation_begin` | `TypeError` de BUG 1 antes de primer stop; `actions=[]`; C1 no ejecutado; `system-autopilot.service` cambió PRE activo→POST inactivo y quedó `POST_CONFLICT`; no se probó que el automatizador lo detuviera. |
| 2026-09-24 13:38:13 | Activación nominal de namespace v2 | Marca registrada en código/sidecar; no equivale a instancia creada | `c1-isolation-automator-v2` se define como namespace objetivo; en la verificación read-only posterior el directorio/estado v2 estaba ausente. |
| 2026-09-24 13:48:44 | C1 v1.1.0 closeout | `py_compile`, pyflakes, scans, 24/24 pure tests, prepare, dry-run y status | Validación estática PASS; `--run`, C1 real, sudo/systemctl stop y ventanas reales `NOT_EXECUTED`; `READY_FOR_EXECUTION=NO`, `C1_STATUS=DEFERRED`. |
| 2026-09-24 actual | Estado documental | Sin commit C1; worktree con modificaciones y elementos no trackeados preexistentes | La documentación conserva los artefactos y no crea commit, no migra residual y no convierte el dry-run en autorización. |

## 3. Evidencia experimental

### 3.1 Registro resumido

| Experimento / fecha | Qué se midió | Configuración | Resultado observado | Qué sostiene | Qué NO demuestra | Limitación / estado |
|---|---|---|---|---|---|---|
| E1/E3/E5, 2026-09-17 | FPS, clocks, `power1_input`, temperatura, Mesa | Sesión histórica, cap 25 W, CUSTOM | Régimen 330–390 MHz, MCLK alto, 74–92 °C y FPS alto | Que un régimen existió en esa sesión | Causa, universalidad, reproducibilidad actual | No reproducido; `UNKNOWN` |
| Fase A, 2026-09-19 | Identidad de device, FPS, clocks, temperatura | 3 GL + 3 VK; selector corregido | Corridas 04–09 eran Intel; las 9 restantes válidas usaron RX550 | La invalidação de selección y baseline reproducible | Que el workload explique E1/E3 | Solo escenas concretas; `SUPPORTED` parcial |
| Fase B/EP-08, 2026-09-19 | SCLK/MCLK, cap, W_SMU, telemetría | 28 corridas; 25/28/32/35 W; GPU real | SCLK 1071 y 10.5–11.6 W en curva | Cap simple no fue limitante en esas corridas | Causa del régimen histórico o consumo físico | No vatímetro; `SUPPORTED` acotado |
| EP-06, 2026-09-19 | Soak, temperatura, clocks, `W_SMU` | cap 25, display Intel, cooldown | Sin clamp hasta 71–72 °C; máximo observado 13.6 W | Calor/cap no bastan para E1 | Máximo de hardware, seguridad general | `PARTIAL` |
| EP-05, 2026-09-19 | A/B Mesa y `/proc/maps` | CUSTOM vs STOCK | Sin diferencia en FPS/energía en workload | CUSTOM no reproduce E5 | Equivalencia universal de Mesa | `SUPPORTED` acotado |
| M1, 2026-09-20 | `W_SMU` y Δpaired | cap 35/30, 10 pares | `<27 W` gate no discrimina | Esa métrica no es gate de poder en este workload | Consumo externo o causalidad de regulator | `SUPPORTED` negativo |
| E-01/E-02/E-03, 2026-09-20/21 | FMA/render/fetch y frametime | Vulkan sintético | `W_SMU` estable; fetch sí eleva frametime | Auto-pacing/fetch-lag como contribución | Causalidad física, juego real, generalización | `SUPPORTED` con límites |
| ES-01/F2, 2026-09-21 | Escalado de trabajo y energía | 8 fetches, A–D+E | 2× fetch ≈ 2× frametime; energía estable | Separación workload/energía en ese diseño | Cuello único de producción | `SUPPORTED` parcial |
| R-14, 2026-09-21 | Score, energía, capas | Superposición OpenGL | ~22.31 W estable / 24.71 W pico; score 804 | Correlación de geometría/energía | Causalidad aislada | `PARTIAL` |
| FASE D2, 2026-09-21 | A/B, export, memoria busy, energía | 6/6 válidas, geometría | Ratio ~1.41; mem_busy y variables correlacionan | Hipótesis de geometría/export | Counter causal, causalidad física | `PARTIAL` |
| R-4A, 2026-09-22 | PCIe Gen2 x4 y límites de enlace | Snapshot read-only | 2.0 GB/s teóricos por sentido; 4.0 GB/s agregado (DERIVED) | Techo de enlace como variable de diseño | Bandwidth real de una carga | `NOT_AVAILABLE` para bandwidth real |
| R-4C, 2026-09-22 | Frame-time jitter | Harness y 8/8 corridas | MAE y Media Abs Error observados; afirmación ajustada | Harness puede observar jitter | Componente causal del jitter | `SUPPORTED` parcial |
| R-4B, 2026-09-23 | Ramp, cooldown, freeze, histéresis, Phase 2 | S1 v2.2/v2.3; S2 v2.3 | S1 completa; S2 `PARADA_D`; global INCONCLUSIVE | Protocolo puede detectar throttling térmico en esas corridas | Claim de governor/global; efecto causal final | `CONFLICT` con snapshots pre-D6, resuelto a INCONCLUSIVE por Addenda |
| H12-2 WSI r3, 2026-09-24 | Present, serialización, WSI capabilities | Wayland 640×360, RADV, FIFO | `state=4`; segundo configure después de present | Cumplimiento del camino WSI observado | Si la GPU quedó idle o la CPU starving | `PARTIAL`; `UNKNOWN` causal |
| Gate P0, 2026-09-24 | Ownership, agentes, CPU, IRQ, almacenamiento, PM | Snapshot READ-ONLY | `CONTAMINATED_REQUIRES_ISOLATION` | El entorno actual no es de control exclusivo | Efecto de cada agente sobre una futura corrida | `PARTIAL` |
| C1 legacy, 2026-09-24 | Flujo de aislamiento | v1.0.0; preflight y sudo histórico | BUG 1 antes de stop; POST conflict | Fail path registrado y no C1 | C1/resultado GPU, corrección de v1.1 en runtime | `NOT_AVAILABLE` para C1 |

### 3.2 Qué puede y qué no puede atribuirse

- `W_SMU`, clocks, temperatura y utilization son **observaciones de telemetría**, no medición eléctrica del rail.
- Un aumento de frametime con más fetches apoya una contribución de auto-pacing/fetch en **ese** workload; no demuestra que fetch sea el límite de todos los drivers o juegos.
- Una correlación de geometría, export o `mem_busy` con energía no identifica un ASIC counter ni una instrucción física.
- La ausencia de clamp en EP-06 y Fase B refuta sólo la explicación sencilla de esos parámetros en esas condiciones.
- El P0 invalida la atribución de ownership para nuevas corridas hasta que exista aislamiento y evidencia de readback.
- No hay vatímetro, APERF/MPERF efectivo, PMU GFX8 utilizable, agent-event collector, bandwidth real cargado ni causalidad de VSync documentados como disponibles.

### 3.3 Localizadores de evidencia

Los resultados resumidos arriba conservan como fuentes primarias los siguientes artefactos; las rutas son del árbol canónico actual y no implican que todos los directorios históricos sean de sólo lectura:

- E1/E3/E5 y las preguntas históricas: `02-ARQUITECTURA/research_log.md`, `knowledge.md`, `hypotheses.md`, `rejected_ideas.md` y los directorios de evidencia citados por `evidence.md`.
- Fase A: `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md` y `INVALIDACION-corridas-04-09.md`.
- Fase B/EP-08: `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/RESULTADOS-FASE-B.md` y `EP08-auditoria-telemetria-E1E3.md`.
- EP-05/EP-06/M1: `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/`, `ep06-soak-cap-20260919-205645/` y `M1-cap-35-30/`, con sus `RESULTADOS-*.md`, `CONDICIONES.txt` y telemetría asociada.
- Synthetic E-01/E-02/E-03, ES-01 y F2: `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/`, junto con los resultados y manifiestos de cada corrida.
- R-14: `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/R-14-SUPERPOSITION-DISSECTION.md` y `telemetria.csv`.
- FASE D2: `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-RESULTADOS.md` y la auditoría asociada.
- R-4A/R-4C: `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/` y `FASE-R4C-JITTER-OBSERVABILITY/`.
- R-4B: `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` y `MASTER-RESEARCH-STATUS.md` Addenda D6.
- H12-2: `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` y el diagrama `00-INDICE/DIAGRAMAS/06-H12-WSI-FRAMETIME.md`.
- Gate P0/runtime PM/D-state/PSI: `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`.
- C1: `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md`, su sidecar, `WORKLOAD-SINTETICO/c1_observer.py` y el residual legacy bajo `/run/user/1000/c1-isolation-automator/`.

Las tablas de este registro son resúmenes; para auditoría de un claim hay que volver al artefacto, manifiesto y hash de la corrida correspondiente.

## 4. C1: definición, workload, observer y claims

### 4.1 Objetivo y alcance

C1 es un experimento sintético de Vulkan/offscreen para observar el comportamiento de la RX550 bajo una carga definida y separada. El automatizador no modifica la GPU ni los parámetros científicos: aísla condicionalmente unidades, ejecuta el binario existente, recoge telemetría y restaura sólo lo tocado.

C1 no es:

- un benchmark de rx550-torneo;
- una validación global de la hipótesis de governor;
- un permiso para modificar PM/DPM/cap;
- una prueba de ownership exclusivo mientras permanezcan clientes/agentes visibles;
- un sustituto de un A/B futuro autorizado.

### 4.2 Binario, workload y parámetros

Fuente primaria: `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` §C1 y `03-EXPERIMENTOS/WORKLOAD-SINTETICO/`.

```text
binario       main-graphics
API            Vulkan 1.1; Vulkan 1.2 no se asume para C1
formato       R8G8B8A8_UNORM
resolución    1920x1080
capas         4
texturas      4
tex_size      4096
FMA            --fma-iters=4; efectivo=24 según el contrato del workload
MSAA           1
seeds          0x13579BDF / 0x2468ACE0
warmup         5 s
duration       20 s
presentación    offscreen
argv completo  se registra en state.json; el binario y flags exactos son parte de provenance
```

El término “efectivo=24” es una convención del contrato del workload, no una nueva variable de configuración. No cambiar el binario, seeds, flags, observer o artefactos frozen durante esta fase documental.

### 4.3 Observer

`c1_observer.py` es un recolector user-space de un solo JSONL. No escanea el sistema entero ni imputa valores ausentes.

| Canal | Periodo | Campos/lecturas | Estados relevantes |
|---|---:|---|---|
| GPU | 100 ms | `gpu_busy_percent`, `mem_busy_percent`, SCLK, MCLK, `power1_input`, temperatura, VRAM used, GTT used, runtime status | `NOT_AVAILABLE` si una lectura falta |
| CPU | 200 ms | 8 governors, `scaling_cur_freq`, CPU time del proceso, context switches, `frequency_effective_estimate` | Frecuencia efectiva explícitamente `NOT_AVAILABLE`; no APERF/MPERF |
| IO/PSI | 500 ms | CPU/IO/memory PSI, `/proc/diskstats` para sda, `procs_blocked`, agent events | Agent events `NOT_AVAILABLE`; no se hace polling de servicios |
| IRQ | 500 ms | IRQ 42 `smp_affinity_list` y `effective_affinity` | No escribe IRQ |
| PM | 500 ms | `power/control`, `runtime_status`, `autosuspend_delay_ms` | No cambia PM |
| Stream | durante child | stdout/stderr, markers y resultado del binario | JSONL propio, parseable y fail-closed |

El observer escribe `scheduled_lag_ns` como indicador de pérdida/demora del planificador, pero no lo convierte en atribución causal. El campo `agent_events` no se completa mediante sondeos de servicios o procesos.

### 4.4 Claims A/B/C/D

| Claim | Alcance implementado | Resultado actual | Justificación de “deferred” |
|---|---|---|---|
| A | Validez formal/runtime de C1 | `NOT_TESTED`/no hay ejecución | El estado requiere `EJECUCIÓN_VÁLIDA`, checks JSONL y restore/POST OK; no se ha ejecutado la ruta real |
| B | Frecuencia efectiva y su relación con el resultado | `frequency_effective_estimate=NOT_AVAILABLE` | No hay APERF/MPERF en el collector; una frecuencia nominal no equivale a frecuencia efectiva |
| C | Ownership/control de la corrida | `OWNERSHIP=PARTIAL` | Gate P0 detecta clientes/agentes y la ruta deja clientes visibles |
| D | Contexto de PSI/Btrfs/D-state | Observado como contexto, no causalidad | El observer registra presión y bloqueo, pero no demuestra que el evento origine el resultado de C1 |

`C1_RUNTIME_VALIDATED=YES` sería una comprobación formal separada; no convierte A/B/C/D en claims científicos globales.

### 4.5 Criterios de validez

El automatizador exige, antes de lanzar C1:

1. hostname `lex-luthor` y kernel esperado;
2. BDF/vendor/device/driver RX550 correctos;
3. `card1`, `renderD129`, `hwmon2` y binario ejecutable;
4. hashes de `main-graphics`, `graphics.cpp`, `c1_observer.py` y build ID;
5. `/run/user/1000` tmpfs y sin JSONL v2 previo;
6. ningún C1/observer ajeno;
7. ningún runtime v2 incompleto;
8. legacy allowlisted preservado y clasificado;
9. `D_STATE_COUNT=0`;
10. `procs_blocked=0`;
11. PSI IO `some avg10 <= 10` y `full avg10 <= 10`;
12. GPU accesible y sin colisión de control.

El umbral IO `10.0` es un criterio operacional existente del proyecto, no porcentaje de uso del disco ni ley universal. Los snapshots de `--prepare`/`--dry-run` PASS son evidencia histórica de esa validación; no son readiness actual ni autorización.

### 4.6 Guard, duración y aborto

- `T_GUARD=120 s` antes de la ventana de medición.
- `T_PRE=30 s` inmediatamente antes de C1.
- `T_POST=30 s` después de C1 si es posible.
- Muestreo de guard cada 5 s para D-state, `procs_blocked`, PSI IO, reaparición de unidades, identidad/accesibilidad RX550 y readback de cap/DPM/PM.
- C1 tiene `C1_MAX_SECONDS=180`; cleanup termina el child si corresponde y no reintenta.
- PRE fallido, auth fallida, stop/readback fallido, guard fallido o colisión de runtime: no se lanza C1.
- Fallo de C1: intentar T_POST si es posible y restaurar lo tocado.
- SIGINT/SIGTERM: marcar interrupción, hacer cleanup seguro y priorizar restore sobre el informe.
- No reparar IRQ, sysfs, PM, DPM, unit files, Btrfs o procesos automáticamente.

### 4.7 Resultado formal esperado

`C1_RUNTIME_VALIDATED=YES` requiere todos estos hechos:

- `--check-tmpfs` devuelve 0;
- child C1 y observer devuelven 0;
- JSONL existe y es parseable;
- `c1_exit=0` y `observer_end=0`;
- no hay `observer_error`;
- existen `measure_start`, `measure_end` y `run_end`;
- aparece `result: EJECUCIÓN_VÁLIDA`;
- `RESTORE_OK` y `POST_OK`.

Este checklist está implementado, pero su resultado real es `NOT_AVAILABLE` porque `--run` no se ejecutó.

### 4.8 Por qué C1 está `DEFERRED`

- **Gate P0:** el entorno es `CONTAMINATED_REQUIRES_ISOLATION`; ownership `PARTIAL` y clientes/agentes permanecen visibles.
- **Sin ejecución real:** no existe un resultado C1 nuevo, JSONL formal ni `C1_RUNTIME_VALIDATED=YES`; la ruta v1.1.0 nunca llegó a `--run`.
- **Runtime v2 no creado:** la inspección posterior al closeout no encontró `c1-isolation-automator-v2`; el residual legacy es histórico, inválido como schema activo y no migrable automáticamente.
- **Claims limitados:** B no tiene frecuencia efectiva, C no tiene ownership exclusivo y D sólo puede aportar contexto PSI/Btrfs; ninguno se puede elevar globalmente.
- **Seguridad operativa:** no hay autorización para repetir C1, no hay retry automático y una nueva ruta requiere precondiciones vivas, TTY, sudo normal y aislamiento verificable.

`DEFERRED` no significa que el código o el diseño sean inválidos; significa que la corrida y la inferencia científica todavía no se han producido bajo un runtime válido, autorizado y aislado.

## 5. Automatizador C1 v1.1.0

### 5.1 Componentes

- `c1_isolation_automator.py`: orchestration runtime-only, lock, state/events, precheck, aislamiento, restore y status.
- `c1_observer.py`: telemetría y child process; no modifica el sistema.
- `main-graphics`: workload ya existente; no se reconstruyó ni se cambió.
- `tests/test_c1_isolation_automator.py`: tests puros con directorios temporales y mocks; no invocan sudo, systemctl, C1 ni probes vivos.
- `C1-ISOLATION-AUTOMATOR.sha256`: sidecar de validación y provenance.

Modos soportados por la interfaz documentada:

```text
--dry-run   plan read-only; no crea runtime; no sudo; no C1
--prepare   checks estáticos/read-only; no crea estado; no sudo
--status    lee v2 y clasifica legacy; no restaura ni reintenta
--run       ruta real; TTY + confirmación literal RUN-C1 + sudo interactivo
```

Durante esta actualización no se ejecutó ninguno de esos modos.

### 5.2 Namespace v2 y legacy

Constantes documentadas:

```text
LEGACY_RUNTIME_NAMESPACE=c1-isolation-automator
RUNTIME_NAMESPACE=c1-isolation-automator-v2
RUNTIME_NAMESPACE_VERSION=2
RUNTIME_SCHEMA_VERSION=2
RUNTIME_NAMESPACE_ACTIVATED_AT=2026-09-24T13:38:13-03:00
```

El código verifica que ambos roots sean siblings, usa el namespace v2 para `CURRENT`, state, events y JSONL, y clasifica el legacy como `HISTORICAL_LEGACY_RUNTIME`. El legacy no se carga como active state, no se migra, no se mueve, no se reescribe y cualquier artifact desconocido bloquea como `LEGACY_RUNTIME_UNRECOGNIZED`.

**Hecho observado en la inspección de esta actualización:** el directorio v2 no estaba presente y el sidecar registra `active_namespace_state=NONE`, `active_namespace_created=false`. Por tanto “namespace activo” debe leerse como **namespace configurado/objetivo**, no como runtime creado y validado. El único directorio presente era el legacy residual.

### 5.3 Máquina de estados

```text
[*] → PRE → AUTH → ISOLATION → GUARD → T_PRE → C1 → POST → RESTORE → COMPLETE
          │       │         │          │       │      │          │
          └───────┴─────────┴──────────┴───────┴──────┘          └→ RESTORE/MANUAL
```

Transiciones y reglas:

1. **PRE:** snapshot de host/GPU/unidades/D-state/PSI/provenance; falla antes de sudo si un criterio falla.
2. **AUTH:** TTY y `sudo -v`; si falla, no hay stop.
3. **ISOLATION:** registrar PRE por unidad; detener sólo unidades activas dentro del allowlist; readback inmediato; `touched[]` antes de cada comando.
4. **GUARD:** 120 s, sin polling indefinido; una falla nunca conduce a C1.
5. **T_PRE:** ventana de 30 s y readback final antes del child.
6. **C1:** ejecutar observer/binario con timeout; no retry.
7. **T_POST:** 30 s si es posible.
8. **RESTORE:** iniciar sólo unidades PRE activas y efectivamente tocadas; comparar ActiveState, SubState, UnitFileState, MainPID y controles GPU.
9. **COMPLETE:** sólo con restore y POST válidos; una discrepancia no se corrige automáticamente.

### 5.4 Unidades y readback

El alcance documentado incluye:

- system: `system-autopilot.timer`, `system-autopilot.service`;
- system: `sys-tuned.timer`, `sys-tuned.service`;
- system: `kalm-gpu.service`, `kalm.service`, `irqbalance.service`, `kalm-lite.service`;
- system: `sysstat-collect.timer`, `sysstat-collect.service`;
- user: `kde-baloo.service`.

Una unidad que estaba inactiva en PRE se marca `SKIP_INACTIVE_PRE` y no se inicia al restaurar. No hay `enable`, `disable`, `mask`, `unmask`, `kill`, `pkill` ni `systemctl kill` en el automatizador. `systemd` puede resurrectar una unidad o un oneshot puede terminar naturalmente; eso se clasifica como transición externa, no como stop probado del automatizador.

### 5.5 Fail-closed, POST_CONFLICT y provenance

- PRE/auth/isolation/guard/T_PRE fallidos: no C1; restore de lo tocado cuando corresponda.
- Restore parcial o readback no coincidente: `RESTORE_PARTIAL`/`RESTORE_FAILED` y atención manual; no reparación automática.
- Discrepancia PRE/POST o de controles: `POST_CONFLICT`; no se repara ni se atribuye automáticamente.
- `--status` nunca restaura, migra ni reintenta por sí solo.
- Escrituras de state son atómicas y runtime-only; lock con `flock`, permisos privados y validación de layout.
- El schema v2 incluye versión de automatizador, hash, schema/namespace version, parents, legacy reference, timestamps, run ID, initial/final state y eventos.

La clasificación de una transición externa es:

```text
EXTERNAL_TRANSITION_OR_NATURAL_ONESHOT_COMPLETION
automator_stop_recorded=false
causality=NOT_PROVEN
```

### 5.6 Autorización, TTY y sudo

`--run` exige TTY y confirmación literal `RUN-C1`; usa `sudo -v` sin `-n` y `sudo systemctl` para unidades system. No captura ni almacena credenciales. Las interfaces read-only (`--dry-run`, `--prepare`, `--status`) no invocan sudo. La ruta real no fue probada con privilegios y permanece `NOT_EXECUTED_REQUIRES_SUDO` como contrato, no como resultado actual.

### 5.7 Runtime esperado

```text
/run/user/1000/c1-isolation-automator-v2/
├── .lock
├── CURRENT
├── c1-observer-v1.jsonl
└── runs/<run-id>/
    ├── state.json
    ├── events.jsonl
    ├── t_guard.jsonl
    ├── t_pre.jsonl
    ├── t_post.jsonl
    ├── c1.stdout
    ├── c1.stderr
    ├── tmp/
    └── cache/
```

El layout es una especificación de diseño. En la inspección read-only posterior al closeout no había `CURRENT`, `state.json` ni `c1-observer-v1.jsonl` v2.

### 5.8 Tests y validación registrada

El sidecar de 2026-09-24 registra:

```text
pure_tests=24/24_PASS
py_compile=PASS
pyflakes=PASS
static_scans=PASS
namespace_invariant=PASS
legacy_allowlist=PASS
active_writer_compatibility=PASS
prepare=PASS
dry_run_mode=PASS
dry_run_plan_only=true
dry_run_pre_current=PASS
dry_run_precheck_errors=NONE
active_namespace_state=NONE
active_namespace_created=false
legacy_classification=HISTORICAL_LEGACY_RUNTIME
legacy_schema_status=INVALID_LEGACY
legacy_active=false
legacy_blocking=false
legacy_preserved=true
--run=NOT_EXECUTED
C1=NOT_EXECUTED
sudo=NOT_EXECUTED
systemctl_stop_start_restart=NOT_EXECUTED
c1_runtime_validated=NO
ready_for_execution=NO
```

La cobertura de tests incluye state v2, metadata, transición `unit_pre`, stop/readback/restore, AST de llamadas `update_state`, schema de las tres ventanas, abort temprano, restore parcial, POST transition, residual legacy allowlisted, namespace inválido, lock, writer mismatch, paths siblings y status que no carga legacy. Los tests no ejecutan sudo, systemctl, C1, observer runtime ni guard real.

## 6. Historial de fallos y resultados negativos

### F-01 — BUG 1: colisión de argumento `update_state()`

- **RUN_ID:** `20260924T154559Z-490709`.
- **Timestamp:** `2026-09-24T12:46:00-03:00` (evento `execution_failure`).
- **Causa observada:** llamada con keyword `state=` que colisionaba con el parámetro `state` de `update_state()`: `TypeError: update_state() got multiple values for argument 'state'`.
- **Evidencia:** `events.jsonl` línea 5; `state.json` conserva `error`, `phase=ISOLATING`, `actions=[]`, `C1.executed=false`.
- **Impacto:** el flujo abortó antes del primer stop; no se pudo atribuir la transición de `system-autopilot.service` al automatizador.
- **Qué NO ocurrió:** no hubo stop registrado, no hubo C1, no hubo restore de unidades tocadas porque `touched[]` estaba vacío; `sudo -v` sí figura como autenticación histórica previa, con retorno 0.
- **Resultado:** `ABORTED_FAILURE_RESTORED`; `legacy_schema_status=INVALID_LEGACY`; `UNITS_STOPPED=NONE`; `C1_EXECUTED=NO`.
- **Corrección aplicada:** firma con `runtime_state` y evidencia `unit_state`; revisión AST de todas las llamadas.
- **Prevención:** tests de transición y scan estático de keywords; fail-closed antes de cualquier stop.

### F-02 — BUG 2: schema incompleto de guard

- **RUN_ID:** no existe un run independiente; se detectó durante la corrección de F-01. Se referencia el residual `20260924T154559Z-490709` sólo como contexto.
- **Timestamp:** `UNKNOWN/NOT_AVAILABLE`; no se conserva un timestamp de descubrimiento separado.
- **Causa observada:** el inicializador no garantizaba entradas completas para `guard.T_GUARD.status`, `guard.T_PRE.status` y `guard.T_POST.status`.
- **Evidencia:** descripción de la corrección y validador en `C1-ISOLATION-AUTOMATOR.md`; tests de schema/ventanas.
- **Impacto potencial:** un abort temprano podía dejar un state estructuralmente inválido o no distinguir ventanas no ejecutadas de estados válidos.
- **Qué NO ocurrió:** no hay evidencia de que BUG 2 causara por sí solo una corrida adicional ni de que hubiera C1 real.
- **Corrección aplicada:** cada ventana incluye `status`, `reason`, `sample_count`, `elapsed_seconds` y `log`; se rechazan valores no canónicos `NOT_RUN` y schema incompleto.
- **Prevención:** tests de schema, validación de `state.json`/`final_state`, y `--run` permanece no ejecutado hasta corregir y auditar.

### F-03 — `POST_CONFLICT` por transición externa

- **RUN_ID:** `20260924T154559Z-490709`.
- **Timestamp:** POST posterior a la falla, registrado en el residual; el log conservado no ofrece un timestamp independiente confiable para la transición.
- **Causa observada:** `system-autopilot.service` figuraba PRE activo y POST inactivo, aunque `actions=[]` y no había `touched[]`.
- **Impacto:** fail-closed; no se corrigió automáticamente y no se probó causalidad.
- **Qué NO ocurrió:** no se atribuyó a un `stop` del automatizador, no se probó que Kalm/autopilot fuera la causa, no hubo C1.
- **Corrección aplicada en v1.1.0:** `external_transitions[]` y clasificación `EXTERNAL_TRANSITION_OR_NATURAL_ONESHOT_COMPLETION`, `automator_stop_recorded=false`, `causality=NOT_PROVEN`.
- **Prevención:** no reparar ni reintentar automáticamente; exigir clasificación explícita y preservar evidencia.

### F-04 — Corridas Vulkan inválidas por iGPU

- **RUN_ID:** el archivo de invalidación identifica las corridas 04–09 de Fase A; no se sustituye el nombre del directorio por un ID inventado.
- **Timestamp:** 2026-09-19; la granularidad exacta depende de `INVALIDACION-corridas-04-09.md`.
- **Causa observada:** el selector Vulkan no explícito caía en Intel `0x412` en vez de RX550 `0x699f`.
- **Evidencia:** `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/INVALIDACION-corridas-04-09.md`.
- **Impacto:** esas corridas no sirven para claims de RX550.
- **Qué NO ocurrió:** no prueban que la RX550 fallara ni que el selector numérico fuera suficiente.
- **Corrección aplicada:** forzar ICD RADV y verificar device `0x699f` por corrida.
- **Prevención:** gate de identidad previo y clasificación explícita de runs contaminados.

### F-05 — R-4B S2 v2.3: PARADA D

- **RUN_ID:** S2-v2.3; la fuente de resultados `EXP-F4-A-RESULTADOS-v2.3.md` y Addenda D6 son la referencia canónica.
- **Timestamp:** 2026-09-23; la duración exacta queda en los artefactos de esa fase, no se reescribe aquí.
- **Causa observada:** condición operativa D durante cooldown antes de Phase 2 utilizable.
- **Evidencia:** `MASTER-RESEARCH-STATUS.md` y `EXP-F4-A-RESULTADOS-v2.3.md`.
- **Impacto:** no hay veredicto global; S1 completada no compensa la parada de S2.
- **Qué NO ocurrió:** no se reintentó S2, no se declararon `SUPPORTED` ni se extrapoló S1 a Phase 2.
- **Corrección/prevención:** estado `INCONCLUSIVE`; regla de no reintento automático y necesidad de autorización/precondiciones nuevas.

### F-06 — Resultado negativo del régimen histórico

- **RUN_ID:** E1/E3/E5 y réplicas; los nombres exactos están en los directorios y bitácora.
- **Timestamp:** 2026-09-17 y sesiones de reproducción 2026-09-19 en adelante.
- **Causa:** `UNKNOWN`; cap, calor, Kalm, Mesa CUSTOM y otra GPU fueron discriminados y no bastan para explicarlo en las condiciones autorizadas.
- **Impacto:** no se puede afirmar una explicación causal ni una especificación de tuning.
- **Qué NO ocurrió:** no se convirtió el régimen en baseline operativo ni se aplicó una política para reproducirlo.
- **Prevención:** mantenerlo como histórico no reproducible y no usarlo como base de validez de C1/claims futuros.

## 7. Estado actual

### 7.1 Bloque normativo C1 v1.1.0

```text
CODE_MODIFIED=YES
TESTS=PASS
PREPARE=PASS
DRY_RUN=PASS
NO_SYSTEM_CHANGES=YES
C1_EXECUTED=NO
C1_RUNTIME_VALIDATED=NO
READY_FOR_EXECUTION=NO
C1_STATUS=DEFERRED
PERSISTENT_SYSTEM_CHANGES=NONE
UNITS_STOPPED=NONE
AUTOMATIC_RETRY=DISABLED
```

Interpretación exacta:

- `CODE_MODIFIED=YES` se refiere al automatizador v1.1.0 y sus correcciones; no implica commit.
- `TESTS=PASS` es la validación pura/estática registrada a las 13:48:44; no se volvió a ejecutar en esta sesión documental.
- `PREPARE=PASS` y `DRY_RUN=PASS` son resultados registrados de esa validación; el dry-run fue sólo plan.
- `NO_SYSTEM_CHANGES=YES` significa que esa validación no cambió configuración persistente, controles GPU ni servicios. El proyecto histórico sí contiene writes autorizados de cap documentados; no se ocultan.
- `C1_EXECUTED=NO` significa que el child C1 no llegó a ejecutarse; el residual v1.0.0 llegó a autenticación/isolation begin y falló antes de C1.
- `UNITS_STOPPED=NONE` corresponde al residual: `actions=[]`; no se cuenta el POST conflict como stop probado.
- `AUTOMATIC_RETRY=DISABLED` está implementado y verificado estáticamente.

### 7.2 Runtime actual y residual

```text
ACTIVE_RUNTIME_STATE=NONE
ACTIVE_NAMESPACE_CREATED=false
LEGACY_RUNTIME_ROOT=/run/user/1000/c1-isolation-automator
LEGACY_RUN_ID=20260924T154559Z-490709
LEGACY_CLASSIFICATION=HISTORICAL_LEGACY_RUNTIME
LEGACY_SCHEMA_STATUS=INVALID_LEGACY
LEGACY_ACTIVE=false
LEGACY_BLOCKING=false
LEGACY_PRESERVED=true
V2_ROOT=/run/user/1000/c1-isolation-automator-v2
V2_ROOT_OBSERVED=ABSENT
```

`legacy_blocking=false` significa que el residual allowlisted no bloquea el precheck del namespace v2; no significa que su schema sea válido ni que pueda ignorarse cualquier artifact desconocido.

### 7.3 Estado de la investigación

- El estado maestro vigente es R-4B v2.3: S1 ejecutada/completada, S2 iniciada/parada D, veredicto `INCONCLUSIVE`.
- Gate P0 vigente: `CONTAMINATED_REQUIRES_ISOLATION`; ownership `PARTIAL`; no se autoriza un nuevo A/B sin aislamiento.
- C1 está `DEFERRED`; `--run` no fue ejecutado.
- No hay cambios persistentes de C1, unidades detenidas por el automatizador ni retry automático.
- El RX550 sigue sin ser la GPU de display en la arquitectura de seguridad.
- No se deben convertir H12, R-4B, W_SMU o el régimen histórico en causalidad.

## 8. Provenance

### 8.1 Hashes conocidos y verificados por lectura

| Artefacto | SHA-256 exacto | Observación |
|---|---|---|
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/main-graphics` | `f278f48c320f3f14edb5d796c75b3df8358e6ca2daf6b9d7d119aa86e0c65e81` | Hash conservado; no se reconstruyó |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp` | `7f1bf813d577a456d485a55ae01bd684bd746e9a3e03a084db2edcab57943615` | Hash conservado |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/c1_observer.py` | `0ddae72a65f9c687550be1d491858802c6c133a06b75fa29cc0d30725bd030c1` | Hash conservado |
| `main-graphics` build ID | `c18acae12e6a4ead407ba15c2bed66e057c2676a` | Nota ELF verificada |
| Git HEAD | `c6146788e0d4fb12d9b0ec1209fa2840692de0c5` | Baseline de referencia; no es commit C1 |
| `04-IMPLEMENTACION/c1_isolation_automator.py` | `fd61816bbcc2aa18b6a769312818baa074bcaeaee7affda4c9475047703d1049` | Sidecar y lectura coinciden |
| `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py` | `1a03c784ac65c977750ee111853ec36e6c973818338a4144dfcedb56135b5d08` | Sidecar y lectura coinciden |
| `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` | `cdc593848f145fc4b396c50031fb54f16792900409bed5700b833c56a1b88ed4` | Documento existente; no se editó |
| `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.sha256` | `796be138803b06fedf3b5b1b95adb1c60a64454848f25628e0c1232e78ef4f6a` | Hash de este sidecar, calculado read-only; no se editó |

### 8.2 Sidecar v1.1.0

El sidecar registra:

```text
automator_version=1.1.0
runtime_namespace=c1-isolation-automator-v2
runtime_namespace_version=2
runtime_schema_version=2
runtime_namespace_activated_at=2026-09-24T13:38:13-03:00
legacy_namespace=c1-isolation-automator
legacy_manifest_id=legacy-c1-isolation-automator-20260924T154559Z-490709-v1
recorded_local=2026-09-24T13:48:44-03:00
git=c6146788e0d4fb12d9b0ec1209fa2840692de0c5
script_sha256=fd61816bbcc2aa18b6a769312818baa074bcaeaee7affda4c9475047703d1049
documentation_sha256=cdc593848f145fc4b396c50031fb54f16792900409bed5700b833c56a1b88ed4
test_sha256=1a03c784ac65c977750ee111853ec36e6c973818338a4144dfcedb56135b5d08
pure_tests=24/24_PASS
commit=NONE
run=NOT_EXECUTED
c1=NOT_EXECUTED
sudo=NOT_EXECUTED
systemctl_stop_start_restart=NOT_EXECUTED
c1_runtime_validated=NO
ready_for_execution=NO
```

### 8.3 Hashes del residual legacy

```text
run_id=20260924T154559Z-490709
state_sha256=f368fa91d050267b9fe30fb2e331e87a8a82e43f16f439470cc4b53d167bf99c
events_sha256=8e7ffbe3693545144037d07727d834422bbb7c8fab81665bc6b7c123bc5d422d
CURRENT_sha256=a06971fcfef0f3fb2f843ed836a7ffc5517a600e345c4838714eb52ab319f31f
```

Estos tres archivos son evidencia histórica que debe permanecer sin normalizar. El sidecar v1.1.0 exige su allowlist exacta; no se convierte el legacy en active state.

### 8.4 Límites de provenance

- El worktree Git tenía cambios y entradas no trackeadas preexistentes; `git status` no se limpió ni se creó commit.
- `commit=NONE` significa que la reparación C1 no tiene commit propio; no invalidan los hashes de los artefactos.
- El hash de documentación C1 existente es el del documento preexistente, no el hash de este nuevo registro.
- No se generaron hashes para datos que no fueron nombrados en la evidencia; un valor ausente es `NOT_AVAILABLE`, no se estima.

## 9. Matriz de conocimiento

La columna `STATUS` usa exclusivamente: `PROVEN`, `SUPPORTED`, `PARTIAL`, `UNKNOWN`, `NOT_AVAILABLE`, `CONFLICT`, `NOT_TESTED`.

| CLAIM | EVIDENCE | STATUS | LIMITATION |
|---|---|---|---|
| RX550 es Polaris12/GFX8, `1002:699f`, BDF `01:00.0` | KNOWLEDGE, sysfs y preflight C1 | `PROVEN` | Snapshot/configuración concreta |
| Intel HD 4600 es el display y RX550 es secundaria | KNOWLEDGE, P0 y política de display | `PROVEN` | La seguridad depende de mantener ese cableado |
| VRAM 2 GiB y GTT observado ≈6.2 GB (≈5.77 GiB) | lectura sysfs/EP-08 | `PROVEN` | GTT no equivale a VRAM física |
| DPM tiene los estados 214–1071/300/625/1500 MHz | KNOWLEDGE/EP-08 | `PROVEN` | No prueba qué estado será forzable o estable |
| `power1_input` es `W_SMU`/proxy, no vatímetro | Addenda terminológica y M1 | `SUPPORTED` | No permite cálculo de eficiencia eléctrica |
| CUSTOM Mesa carga `/opt/mesa-26.2.2-rx550-haswell` | EP-05 maps y renderer | `PROVEN` | No demuestra que sea la Mesa del sistema |
| CUSTOM reproduce el régimen histórico E5 | EP-05 negativo | `PARTIAL` | Refutado en el conjunto probado, no universal |
| Cap 25 W no liga SCLK en workloads actuales | Fase B/M1/EP-06 | `SUPPORTED` | No descarta límites en otras escenas/condiciones |
| `W_SMU` máximo observado es 13.6 W | EP-06 | `PARTIAL` | Es máximo observado, no máximo del hardware |
| Auto-pacing/fetch-lag contribuye al frametime | E-01/E-02/F2 | `SUPPORTED` | Workload sintético; no prueba causalidad física general |
| Geometría/export explica el aumento de energía | R-14/FASE D2 | `PARTIAL` | Correlación; no counter causal aislado |
| R-4B demuestra soporte del governor | S1/S2 y Addenda D6 | `CONFLICT` | Snapshots pre-D6 contradicen el closeout; prevalece `INCONCLUSIVE` |
| H12-2 confirma `xdg_toplevel.state=4` | WSI r3 | `PROVEN` | Una corrida y un modo concreto |
| H12-2 separa A (GPU) de B (CPU/WSI) | WSI r3 + causalidad ausente | `UNKNOWN` | No se programó RGP ni se aisló owner |
| Ownership actual de la GPU es exclusivo | Gate P0 y legacy POST | `PARTIAL` | Clientes/agentes visibles; C1 deja ownership partial |
| D-state/PSI/HDD pueden afectar latencia | P0, R-4C y telemetría | `SUPPORTED` | No prueban que originen el resultado C1 |
| Existencia de Btrfs con riesgo de I/O | P0 y evidence | `SUPPORTED` | No se ejecutó mantenimiento ni se cambió almacenamiento |
| Frequency effective CPU está medida por C1 | observer `frequency_effective_estimate` | `NOT_AVAILABLE` | No APERF/MPERF |
| C1 runtime formal validado | formal checks implementados, sin `--run` | `NOT_TESTED` | La existencia del checklist no es ejecución |
| C1 claim A validado científicamente | no hay JSONL/resultado C1 | `NOT_TESTED` | Claim deferido por diseño |
| C1 claim C tiene ownership completo | P0 | `NOT_TESTED` | `OWNERSHIP=PARTIAL` |
| C1 claim D prueba causalidad de PSI/Btrfs | sin C1 | `NOT_TESTED` | Sólo contexto, no atribución |
| Automatizador v1.1.0 existe con hash conocido | source + sidecar | `PROVEN` | No hay commit C1 |
| 24 pure tests y scans estáticos pasaron | sidecar de 13:48:44 | `PROVEN` | No se reejecutaron en esta sesión |
| Namespace v2 tiene runtime activo | inspección: root ausente; sidecar `NONE` | `NOT_AVAILABLE` | Namespace objetivo no es instancia creada |
| Residual legacy está preservado y allowlisted | state/events/CURRENT + sidecar | `PROVEN` | Schema legacy inválido y no active |
| No hubo stop de unidades en el residual | `actions=[]`, `touched=[]` | `PROVEN` | El POST transition no fue causado por stop probado |
| No hubo cambios persistentes en validación v1.1.0 | sidecar y no `--run` | `PROVEN` | No niega writes históricos del proyecto |
| No existe retry automático | source, documentación y closeout | `PROVEN` | La ruta real sigue sin probarse |
| Causa del régimen E1/E3/E5 | discriminadores negativos, sin causa | `UNKNOWN` | No crear hipótesis nueva sin autorización |
| Causa del segundo configure H12 | evidencia de coexistencia A/B | `UNKNOWN` | Requiere instrumentación/aislamiento nuevo |
| Causalidad física de `W_SMU` frente a consumo | sin vatímetro/PMU | `NOT_AVAILABLE` | No derivar claims eléctricos |
| GFX8 PMU utilizable para causalidad | catálogo, sin lectura válida | `NOT_AVAILABLE` | Programar UMR/RGP está fuera de alcance |
| Bandwidth PCIe real bajo carga | R-4A sólo límites/enlaces | `NOT_AVAILABLE` | La estimación no es throughput observado |
| El worktree contiene modificaciones y elementos no trackeados | `git status` observa modificaciones y elementos no trackeados | `PROVEN` | No se hizo cleanup ni commit |
| La investigación tiene un veredicto global favorable | R-4B D6 | `CONFLICT` | Estado canónico actual: `INCONCLUSIVE` |

## 10. Contradicciones, unknowns y datos faltantes

### 10.1 Contradicciones conservadas

1. **Kernel:** `7.2.6-201.nobara.fc44.x86_64` en C1/Gate vigente frente a `7.2.4-201` en knowledge histórico. No se funden; el primero define el precheck C1 de esa fase.
2. **Namespace:** la documentación llama “runtime activo posterior al fix” a v2, pero la inspección read-only encontró v2 ausente y `ACTIVE_RUNTIME_STATE=NONE`; se corrige la lectura a “namespace objetivo/configurado”.
3. **sudo:** el residual histórico registra `sudo -v` con retorno 0; el closeout v1.1.0 registra `sudo=NOT_EXECUTED`. Son actas temporales distintas: una ejecución legacy abortada y una validación v1.1.0 sin `--run`.
4. **R-4B:** snapshots anteriores describen S2 como no iniciada o diagnóstico térmico; Addenda D6 y `MASTER-RESEARCH-STATUS` prevalecen: S1 ejecutada/completada, S2 iniciada/parada D, veredicto global INCONCLUSIVE.
5. **Kalm:** documentos de 2026-09-19 describen `kalm-gpu.service` dead; el Gate P0 de 2026-09-24 documenta agentes/servicios relevantes y exige aislamiento. Son estados temporales distintos, no una historia lineal de un mismo estado.
6. **C1 flags:** `PREPARE=PASS` y `DRY_RUN=PASS` no contradicen `READY_FOR_EXECUTION=NO`; el primero valida interfaces, el segundo conserva el gate P0 y no autoriza ejecución.
7. **“Sin cambios”:** `NO_SYSTEM_CHANGES=YES` se limita a la validación v1.1.0; el proyecto tiene writes históricos autorizados de cap. La frase no debe generalizarse a toda la historia del repositorio.
8. **BUG 2:** no hay un RUN_ID ni timestamp independiente; se marca `NOT_AVAILABLE`, no se fabrica uno a partir del mtime de un archivo.
9. **W_SMU:** algunos documentos históricos usan `draw`/potencia sin unidades; la reconciliación de 2026-09-24 exige `W_SMU`/estimación SMU y no vatímetro.

### 10.2 Unknown / NOT_AVAILABLE

- causa del régimen histórico;
- vatímetro/rail eléctrico independiente;
- frecuencia efectiva CPU por APERF/MPERF;
- `agent_events` del observer;
- causalidad A/B de H12-2;
- bandwidth real de carga PCIe;
- counters PMU GFX8 lectura válida;
- aislamiento ownership exclusivo actual;
- preparación (readiness) y resultado de una ruta C1 real;
- timestamp independiente de descubrimiento de BUG 2;
- causalidad de la transición `system-autopilot.service` PRE→POST;
- estado que habría tenido el namespace v2 después de un `--run` exitoso, porque no se ejecutó.

## 11. Próximos pasos ya definidos por el proyecto

Sólo se reproducen pasos que ya están definidos en documentos existentes:

1. Mantener C1 en `DEFERRED`; no ejecutar `--run` hasta autorización explícita, TTY, sudo normal, precondiciones vivas y aislamiento verificable.
2. Resolver el Gate P0 `CONTAMINATED_REQUIRES_ISOLATION`: separar clientes/agentes y demostrar propiedad/readback antes de un nuevo A/B.
3. Si una corrida C1 fuera autorizada en el futuro, conservar el orden documentado `PRE → AUTH → ISOLATION → GUARD → T_PRE → C1 → POST → RESTORE`; no eliminar guardas para forzar un resultado.
4. No reintentar S2 de R-4B automáticamente; el estado vigente es `INCONCLUSIVE` y requiere una nueva decisión/autorización, no un retry.
5. Mantener los counters/PMU como catálogo o diseño no ejecutado; no programar UMR/RGP ni inferir causalidad sin el gate y la autorización que faltan.
6. Mantener el display Intel y la política de no usar la RX550 como GPU de pantalla durante investigación.
7. Preservar los datos crudos, sus hashes, el residual legacy y la documentación; cualquier nueva fuente debe reconciliarse con este registro.
8. No introducir nuevas acciones de sistema, benchmarks o políticas de tuning desde este documento; cualquier acción futura requiere su propio encargo y autorización.

## 12. Cierre de esta actualización

Se han creado únicamente documentos en:

- `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/README.md`;
- `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md`;
- `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/DOCUMENT-HASHES.txt`.

Los hashes de `README.md` y `C1-TECHNICAL-RECORD.md` están consignados en `DOCUMENT-HASHES.txt`; el manifiesto excluye su propio hash para evitar una referencia circular. No se modificó `c1_isolation_automator.py`, `c1_observer.py`, `graphics.cpp`, tests, servicios, GPU, kernel, Mesa, PM/DPM, governor, IRQ, scheduler, read-ahead, Btrfs ni hashes existentes. No se ejecutó ninguna acción operacional durante esta actualización documental.
