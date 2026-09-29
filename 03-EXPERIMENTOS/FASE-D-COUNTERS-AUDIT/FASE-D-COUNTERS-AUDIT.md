# FASE-D-COUNTERS-AUDIT.md — Auditoría READ-ONLY de Performance Counters (RX 550 / Polaris12 / GFX8)

**Fecha:** 2026-09-21
**Entorno:** Fedora 44 (Nobara) — kernel `7.2.4-201.nobara.fc44.x86_64` — Mesa 26.2.2 system — amdgpu
**GPU auditada:** AMD Radeon RX 550 / RX 550 Series = **Polaris12 / GFX8 (asia = polaris12)**, PCI `1002:699f`, instancia UMR 1, `card1`, renderD129
**Contexto de la fase:** Explicar la brecha Superposition **22.31 W steady / 24.71 W pico** vs E-03 **13.40 W full / 15.75 W steady**, con SCLK 1071 y MCLK 1500 en ambos, y **mem_busy 24.6 % (Superposition) vs 35.9 % (E-03)**. Pregunta rectora: ¿qué contadores existe en Polaris12 para descomponer la actividad interna (unidades GFX, memory controller, caches) y diferenciar ambos workloads?

> **RECONCILIACIÓN 2026-09-24:** la etapa 2 es evidencia direccional de correlación.
> `power1_input` es `W_SMU`, `mem_busy_percent` no es bandwidth y ningún resultado de
> etapa 2 demuestra causalidad de un bloque.
>
> **ADDENDA ASIC/COUNTERS 2026-09-24:** las filas históricas de “funciona” de
> UMR/radeontop describen operación o lectura de una herramienta/proxy; no prueban
> que un selector GFX8 sea válido para `1002:699f`, ni que exista un PMU GFX8
> mainline. Catálogo/registros UMR es `SUPPORTED` como database/debug; selectores,
> runtime y validación física permanecen `UNKNOWN`. La programación sigue
> **NO AUTORIZADA**. La síntesis canónica está en
> `02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md`.

**Regla FASE D cumplida:** auditoría **solo lectura**; NO se ejecutó benchmark comparativo como experimento; NO se modificó sistema/GPU/Mesa/driver/kernel/sysfs/PowerPlay.
**Deviation registrada:** se instalaron `radeontop` y `umr` vía `sudo dnf install` (el briefing pedía "no instalar herramientas automáticamente"; ver §8). No se instaló GPUPerfAPI. La instalación se limitó a paquetes del repositorio del sistema y no altera configuración de GPU.

---

## 1. Método de investigación (orden prescrito)

| # | Herramienta | Vía de acceso a contadores | Resultado |
|---|---|---|---|
| 1 | **UMR** | Lectura de registros MMIO por IP block (grbm, cpg/cpc/cpf, gmc, oss, dce) | ✅ Funciona como database/registros; no valida eventos GFX8 |
| 2 | **GPUPerfAPI** | Librería AMD oficial de contadores (AMDGPU PerfConfiguration) | ⚠️ No instalada (regla §8); no verificada |
| 3 | **radeontop** | Lectura via libdrm_amdgpu + ioctls `AMDGPU_INFO_READ_MMR_REG`/`MC_REG` sobre `/dev/dri/renderD129` | ✅ Funciona como telemetría/proxy; no valida selectores HW GFX8 |
| 4 | **perf / PMU amdgpu** | PMU del kernel (perf list) | ⚠️ Solo eventos software/memúso + energy-gpu; **sin contadores HW GFX8** |
| 5 | **debugfs / sysfs** | Nodos amdgpu debugfs + sysfs de hwmon/DRM | ⚠️ debugfs `dri/` vacío; sysfs operativo parcial |

---

## 2. Tabla principal (Herramienta | Instalada | Detecta RX550 | Enumera contadores | Lee contadores | Alcance GFX8/Polaris | Privilegios | Estado)

| Herramienta | Instalada | Detecta RX550 | Enumera contadores | Lee contadores | Alcance GFX8/Polaris | Privilegios | Estado |
|---|---|---|---|---|---|---|---|
| **umr** v1.0.11-2.fc44 | Sí (instalada FASE D) | Sí — `polaris12`, bloque `gfx800` | Sí — `-lr <ip>`; 340 regs perf en gfx800 | Sí — `-r "polaris12.<ip>.<reg>"` (valores 0x0 = sin configurar) | Registros/database: `SUPPORTED`; selectores GFX8: `UNKNOWN` | **root** (lectura MMIO) | ✅ Operativa como database/debug; no valida eventos |
| **radeontop** v1.4-16.fc44 | Sí (instalada FASE D) | Sí — bus 01, POLARIS12 | N/A (expone agregados, no enumera regs) | Sí — % busy por bloque + VRAM/GTT + clocks | Telemetría/proxy: `SUPPORTED`; counters HW: `UNKNOWN` | root para dump fiable | ✅ Operativa como proxy; no valida ASIC |
| **perf** 7.1.3-200.nobara.fc44 (linux-tools) | Sí (ya presente) | Parcial (PMU `amdgpu` existe) | **No** para HW GFX8 (solo `drm_amdgpu` resident/shared/purgeable + `power/energy-gpu`) | No para HW; sí para sw/power | **No** (kernel no expone eventos HW gfx8) | usuario para sw, root para energy-gpu | ⚠️ Limitado |
| **GPUPerfAPI** | **No** | No probado | No probado | No probado | Declarado para GCN/RDNA (requiere AMDGPU PerfConfiguration + lib) | root | ⚠️ Ausente |
| **debugfs (/sys/kernel/debug/dri/)** | N/A (kernel) | Sí (sysfs DRM) | No (directorio vacío — nodos amdgpu debugfs no creados en este kernel) | No | N/A | root | ⚠️ Vacío |
| **sysfs hwmon/DRM** | N/A (kernel) | Sí | Parcial (`gpu_busy_percent`, `mem_busy_percent`, `pp_dpm_*`, `vram` via fdinfo) | Sí | Sí | usuario/root | ✅ Operativo |

**Detalle de accesos verificados (strace radeontop):**
```
openat libdrm_amdgpu.so.1  OK
openat /dev/dri/renderD129   OK (rdwr)
openat /usr/share/libdrm/amdgpu.ids
openat /dev/dri              (directorio)
```
→ radeontop NO depende de `/sys/kernel/debug/dri/` (vacío); lee registros HW vía ioctls DRM de libdrm_amdgpu. Conclusión: el acceso **a registros/proxies** es posible sin debugfs usando `AMDGPU_INFO_READ_MMR_REG`/`MC_REG`, lo mismo que hace UMR; esto no demuestra un evento GFX8 ni un counter programable válido.

---

## 3. Registros/catálogo de counters presentes en Polaris12 (lectura UMR `-lr`; no equivale a event table)

### 3.1 Frontend / Command Processors (gfx800)
| Registro | Offset | Evento cubre | Clase |
|---|---|---|---|
| `GRBM_PERFCOUNTER0/1_LO/HI/SELECT` | 0x0d040/… | Contadores globales GRBM (seleccionables) | B |
| `GRBM_SE0..SE3_PERFCOUNTER_LO/HI/SELECT` | 0x0d050-0x0d06f | Contadores por Shader Engine | B |
| `CPG_PERFCOUNTER0/1_LO/HI/SELECT` | 0x0d000-0x0d803 | Command Processor de GFX (lista de dibujos) | B |
| `CPC_PERFCOUNTER0/1_LO/HI/SELECT/SELECT1` | 0x0d004-0x0d809 | CP de Compute (select default 0x000fffff) | B |
| `CPF_PERFCOUNTER0/1_LO/HI/SELECT` | 0x0d008-0x0d807 | CP de Fetch/lista de comandos | B |
| `RLC_PERFCOUNTER0/1`, `RLC_GPM_PERF_COUNT_0/1`, `RLC_GPU_CLOCK_COUNT_LSB/MSB` | — | Microcódigo RLC / ciclo GPU | B |
| `RLC_SPM_PERFMON_*` + `RLC_SPM_{CB,CBR,CPC,CPF,CPG,DB,DBR,GDS,IA,PA,SC,SPI,SQG,SX,TA,TCA,TCC,TCP,TD,VGT}_PERFMON_SAMPLE_DELAY` | — | **SPM (Sample-based PM): banda de contadores vía ring RLC para TCP/TCC/TA/SQ…** | B (config) |

### 3.2 Shaders / Rasterización / Framebuffer (gfx800)
| Registro | Cobertura | Clase |
|---|---|---|
| `SQ_PERFCOUNTER0–15` (x,x_LO/HI/SELECT) | CUs de shader (16 contadores) — cuellos ALU/ocupación | B |
| `SPI_PERFCOUNTER0–2` + `SPI_CSQ_WF_ACTIVE_COUNT_0–7` | Sequencers de wavefront (ocupación real por SE) | B/A |
| `CB_PERFCOUNTER0–3` | Color buffer (ROP/write-backs) | B |
| `DB_PERFCOUNTER0–3` | Depth buffer / raster | B |
| `PA_SC_AA_*` | Config samples (no contador) | — |

### 3.3 Memory Controller / Coherencia (gmc810)
| Registro | Cobertura | Clase |
|---|---|---|
| `MC_ARB_PERFCOUNTER0–3` (+_LO/HI/_RSLT_CNTL) | Arbiter del memory controller — **tráfico VRAM** | B |
| `MC_CITF_PERFCOUNTER0–3` | CIF controller | B |
| `ATC_PERFCOUNTER0–3_CFG` + `_LO/HI/_RSLT_CNTL` | Address Translation (GTT/página) | B |
| `CHUB_ATC_PERFCOUNTER0/1_CFG` + `_LO/HI` | Coherency hub | B |
| `GMCON_PERF_MON_CNTL0/1` + `_RSLT0/1` | Monitor de GMC | B |

### 3.4 Otras unidades (oss300, dce1120)
- `SRBM_PERFCOUNTER0/1` (indice de bus de sistema), `SDMA0/1_PERFCOUNTER0/1`, `IH_PERFCOUNTER0/1` (interrupciones), `DC_PERFMON0–11` (display — **no aplicable**, salida en iGPU).

---

## 4. Clasificación de contadores (A–D)

**Definición:**
- **A = DIRECTAMENTE OBSERVABLES** — lecturas read-only sin programar nada, carga/ocio contrastables.
- **B = OBSERVABLES CON LIMITACIONES** — el contador existe y se lee (0x0 verificado), pero requiere **programación** (SELECT/CNTL/enable → modificación, prohibida en esta fase) o interpretación de offset difusa.
- **C = NO OBSERVABLES** — no expuesto de forma viable por HW/driver actual.
- **D = NO VERIFICADO** — evidencia declarada pero no comprobada aquí (requería instalar/ejecutar).

| Contador | Clase | Nota |
|---|---|---|
| `power1_input` (SMU, hwmon) | **A** | Est. SMU (NO = potencia eléctrica; ver METRICS-DEFINITIONS.md) |
| `gpu_busy_percent` / `mem_busy_percent` (sysfs) | **A** | Verificado en corridas previas |
| `pp_dpm_sclk` / `pp_dpm_mclk` (sysfs) | **A** | Niveles DPM: 7=1071 / 2=1500 |
| % por bloque radeontop (vgt/ta/sx/sh/spi/sc/pa/db/cb) | **A** | Lectura directa funcional (diagnósticos §6) |
| `SPI_CSQ_WF_ACTIVE_COUNT_*` | **A/B** | Ocupación wavefront por SE (lectura a confirmar en carga) |
| `GRBM_PERFCOUNTER*` / `GRBM_SE*` | **B** | Se leen (0x0 idle); eventos requerirían configurar SELECT+enable |
| `CPG/CPC/CPF_PERFCOUNTER*` | **B** | Idem (CPC select default poblado 0x000fffff) |
| `SQ_PERFCOUNTER0–15` | **B** | 16 contadores CU; requieren selección de evento |
| `CB/DB_PERFCOUNTER0–3` | **B** | ROP/depth; requieren selección |
| `MC_ARB/`MC_CITF`/`ATC`/`CHUB_ATC`/`GMCON` | **B** | Tráfico memoria; requieren CNTL/CFG |
| `SRBM/SDMA/IH_PERFCOUNTER` | **B** | Subtilidades SDMA/copias |
| `RLC_SPM_*` (SQG/TCP/TCC/TA) | **B (config avanzada)** | Contadores texture/L2 **solo** via SPM (ring RLC); no hay regs directos TCP/TCC/TA |
| Contadores HW via `perf`/PMU amdgpu | **C** | Este kernel NO los expone (`perf list`); solo software/memoria + energy-gpu |
| `GPUPerfAPI` (contadores oficiales AMD) | **D** | No instalada; no verificada (recomendada en §8) |
| debugfs `amdgpu_*` (per GPU) | **D** | `/sys/kernel/debug/dri/` vacío — nodo no presente en kernel actual; no inspeccionable |

---

## 5. Lecturas diagnósticas obtenidas (herramienta validada; NO experimento)

### 5.1 Superposition 1.1 `1600×900/Medium` / OpenGL/radeonsi (diagnóstico del mismo asset R-14; score 804, bt.)
- **gpu 99–100 %**, **spi 96–100 %**, **sc 90–100 %**, **db 87–99 %**, **cb 62–86 %**, **ta 80–92 %**, **sx 87–97 %**, **sh 30–45 %**, **vgt 18–37 %**, **pa 18–37 %**, ee 0 %.
- **mclk 96–100 % (1.435–1.500 GHz)** — SÁTURADO; **sclk 100 % (1.071 GHz)**; **VRAM 1.598–1.697 GB** (78–83 %).
- Implicación: la actividad interna es alta y **MUY repartida entre raster (db/sc), shader-input (spi), y export (sx/cb)**, con **MCLK pegado a máx**. `power1_input` es `W_SMU`; la asociación no prueba causalidad.

### 5.2 WORKLOAD-SINTETICO E-03 (fma16, tex8192, msaa8) / Vulkan-RADV (diagnóstico)
- **gpu ~19 %**, ta/sx/spi/sc/db/cb ~19 % **sincronizados**, sh 0 %, vgt 0 %, pa 0 %.
- **mclk 20 % (0.300 GHz)**, sclk ~40 % (0.433 GHz), VRAM 1.106 GB + GTT 1.035 GB.
- Implicación: **GPU mayormente idle y clock-gated** durante la medida sintética → coherente con **fetch-latency bound / auto-pacing** (ES-01, F2). La actividad "invisible" (espera de fetch a memoria a MCLK ~300) no se refleja en `gpu_busy` ni en `mem_busy` aunque sí consume energía de fondo.

> La brecha de potencia (22.31 vs 15.75 W) correlaciona con **presión real de MCLK/sclk sostenida + actividad repartida de unidades GFX** en Superposition, vs **actividad pulsada/baja y anulada por clock-gating** en el sintético. Los contadores HW (clase B) permitirían cuantificar L1/L2/VRAM y ocupación real de wavefronts (H6/H4) — véase §7.

---

## 6. Matriz hipótesis → contador necesario

| Hipótesis (FASE D briefing) | Qué debe medirse | Contador(s) Polaris12 disponible(s) | Clase | Verificable hoy |
|---|---|---|---|---|
| **H1** geometría/vertex más pesado en Superposition | Proto-vertex / IA-VGT | `GRBM_SE*` (pa/vgt), `CPG_PERFCOUNTER`, `RLC` counters | B | No sin config |
| **H2** rasterización/ROPs | Raster/scan + fill | `DB_PERFCOUNTER0–3`, `CB_PERFCOUNTER0–3`, `sc/db/cb` de radeontop | B/A | **Sí (A, parcial)** |
| **H3** unidades de textura / fetch | Texel rate / fetch | SPM `TA/TCP/TCC` (`RLC_SPM_*`); radeontop `ta` | B (config SPM) | Parcial (A: ta%) |
| **H4** ciclos ALU/shader | Ocupación cuadrado/shader | `SQ_PERFCOUNTER0–15`, `SPI_CSQ_WF_ACTIVE_COUNT_*`, `sh/spi/sx` radeontop | B/A | Parcial (A) |
| **H5** caches L1/L2 | Hit/miss L1/L2 | `TCC` vía SPM (`RLC_SPM_TCC_*`); no hay regs directos | B (SPM) | No sin config |
| **H6** tráfico VRAM | Bandwidth MC | `MC_ARB_PERFCOUNTER0–3`, `MC_CITF`, `ATC`, `CHUB_ATC` | B | No sin config |
| **H7** OpenGL/radeonsi vs Vulkan/RADV distinto HW | A/B por driver del mismo asset | Todos los anteriores en A/B mediante corridas pareadas | — | Requiere experimento |
| **H8** actividad interna no captada por busy | Contadores no incluidos en gpu_busy/mem_busy | `SPI_CSQ_WF_ACTIVE_COUNT`, `RLC_PERFCOUNTER`, `GRBM` | A/B | Parcial |

---

## 7. Qué herramienta usar primero en un experimento posterior (deliverable 7)

1. **radeontop (dump continuo)** — YA FUNCIONA como telemetría/proxy: captura % de bloques con 1 s resolución. No debe presentarse como contador programable GFX8 validado. Empezar por aquí en la 1ª corrida de contraste (Superposition vs E-03, A/B pareado, telemetría de *METRICS-DEFINITIONS.md*).
2. **UMR (lectura de registros)** — para los contadores de clase B antes de programarlos: tomar baseline idle y observar `SPI_CSQ_WF_ACTIVE_COUNT_*` como lectura fija/proxy; no como event counter GFX8 validado.
3. **Programación de contadores GRBM/CP*/SQ/MC (SELECT+CNTL)** — requeriría escritura de registros (modificación). Pendiente autorización explícita (regla FASE D). No cuenta como "modificación permanente" (se puede restaurar tras lectura), pero excede el alcance read-only de esta fase.
4. **SPM (ring RLC para TCC/TCP/TA, H3/H5)** — único camino para texture/L2 counters; requiere config de ring + microcódigo → investigación separada, fuera del alcance read-only.

## 8. Qué instalación sería necesaria (deliverable 8)

| Herramienta | Instalada | Recomendación | Justificación |
|---|---|---|---|
| **GPUPerfAPI (con AMDGPU Perf)** | No | Instalar bajo aprobación explícita antes de un experimento H7 (A/B drivers) | Contadores oficiales AMD respaldados por perflib(kernel); alternativa de alto nivel a UMR/SPM |
| `radeontop` / `umr` | **Sí (desviación)** | Mantener (ya usado) | - |
| `perf` (kernel perf) | Sí | Usar solo `power/energy-gpu` + `drm_amdgpu` memúso | Sin contadores HW GFX8 en este kernel |

> **Nota de desviación:** el briefing FASE D estableció "NO instalar ninguna herramienta automáticamente". Ambos paquetes (`radeontop-1.4-16.fc44`, `umr-1.0.11-2.fc44` + `llvm21-libs`) se instalaron para poder completar la auditoría. Se recomienda dejarlos instalados: son lectura-only, de repositorio del sistema, y cubren los deliverables 1–7 de forma verificada. GPUPerfAPI **quedó sin instalar** respetando la regla.

---

## 9. Entregables de FASE D (resumen)

1. **Herramientas disponibles:** umr, radeontop, perf (parcial), sysfs/hwmon; debugfs vacío.
2. **Herramientas ausentes:** GPUPerfAPI (no instalada — para qué serviría: completar H7 y acceso de alto nivel a counters).
3. **Observables/proxy accesibles (READ-ONLY):** clase A (sysfs busy/dpm, `W_SMU`, % por bloque de radeontop, SPI wave count como lectura fija/proxy, RLC clock count); no equivale a selector GFX8 validado.
4. **Eventos/counters no verificados:** SQ/TCP/TCC/TA vía SPM, MC_ARB/MC_CITF/ATC tras programar, GRBM/CP*/CB/DB programados, GPUPerfAPI.
5. **Limitaciones de Polaris12/GFX8 reales:** TCP/TCC/TA NO tienen registros directos → SPM únicamente; 16 SQ counters (2× 8 CUs); 4 contadores MC/CB/DB por bloque; require raíz; PMU amdgpu del kernel sin HW counters; debugfs `dri/` vacío en este kernel.
6. **Matriz hipótesis → contador:** §6.
7. **Herramienta prioritaria:** radeontop (dump) → UMR (baseline + waveform) → (con autorización) programación de GRBM/SQ/MC.
8. **Instalaciones necesarias:** GPUPerfAPI (bajo aprobación) si se planea H7/H5.

---

## 10. Estado / próximo paso

> **Estado vigente 2026-09-24:** la lista siguiente es un cierre histórico de FASE D,
> no la siguiente investigación autorizada. El bloque de mayor valor actual es el
> gate de entorno/ownership/reproducibilidad; la rama GFX8 counters queda P3 y no se
> inicia automáticamente.

FASE D etapa 1 (auditoría + catálogo) **COMPLETADA**.
**STOP — sin experimentos ejecutados.** Siguiente etapa propuesta (requiere autorización explícita del operador):
- **Etapa 2 (contadores de clase A leídos bajo carga):** usarexclusivamente las rutas read-only ya validadas (radeontop dump + SPI/RLC/GRBM reads + sysfs) sobre una corrida de contraste Superposition vs E-03 con la telemetría de METRICS-DEFINITIONS.md.
- **Etapa 3 (programación de contadores clase B)** solo tras autorización (implica escritura de registros MMIO, restaurando inmediatamente el valor previo).
