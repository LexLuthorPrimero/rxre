# FASE-D-ETAPA-2-PLAN.md — PLAN (NO EJECUTAR): Contraste pareado Superposition vs E-03 (contadores clase A)

**Fecha:** 2026-09-21
**Documento:** PLAN SOLO LECTURA — no se ejecutó ninguna corrida con este plan.
**Estado de FASE D:** Etapa 2 planificada; ejecución pendiente de autorización.

> REGLA CRÍTICA: Todo lo descrito aquí es **planificación**. La §13 contiene los comandos *que se ejecutarían*; NO fueron ejecutados. Este documento NO autoriza ejecución — la autorización de ejecución es un acto separado del operador.

---

## 1. Objetivo

Determinar qué actividad de hardware (por bloque GFX y por memoria) diferencia:

- **Superposition 1.1 `1600×900/Medium`** (OpenGL/radeonsi): `W_SMU` steady ≈ 22.31 W, SCLK 1071 MHz, MCLK 1500 MHz, `gpu_busy ≈ 100 %`, `mem_busy ≈ 24.6 %`, VRAM ≈ 1.55 GB.
- **WORKLOAD-SINTETICO E-03** (Diseño B, Vulkan/RADV): `power_avg_steady ≈ 15.75 W`, SCLK/MCLK según evidencia histórica (`power_avg_full 13.40`, steady 15.75), con **clock gating observado en FASE D etapa 1** (gpu ~19 %, MCLK 300 MHz, sclk ~433 MHz durante la medida E-03 en diagnóstico puntual).

Pregunta rectora: **¿qué señales de clase A (lectura pura, auditadas en FASE D etapa 1)
muestran actividad interna distinta** —texels, wavefronts activos, raster/fill, presión de
memoria— que correlacione con la `W_SMU` observada (+6.5 W; 22.31 vs 15.75)?

La comparación **conserva el comportamiento natural** de cada workload. **No** se fuerzan frecuencias ni se igualan clocks (prohibido).

---

## 2. Variables independientes

| Variable | Niveles | Nota |
|---|---|---|
| Workload | **A = Superposition `1600×900/Medium` (OpenGL/radeonsi)** / **B = E-03 base (Diseño B)** | Configuración efectiva histórica conservada; no reejecutar |
| Orden de corridas | Intercalado **A B A B A B** (3 réplicas c/u) | Mitiga deriva térmica y de PowerPlay |
| Pausa inter-runs | 30 s idle (misma workload) / 60 s idle (cambio de workload) | Vuelve clocks a piso y estabiliza térmico |

**No se varía:** frecuencia (DPM `auto`, no se toca), calidad de Superposition, config de E-03, Mesa, kernel, sysfs, PowerPlay, Kalm.

**No se controla (a propósito):** la frecuencia interna con que cada workload activa unidades — ese es precisamente lo que se pretende *observar*.

---

## 3. Variables dependientes

Todas reportadas con las 4 métricas de `METRICS-DEFINITIONS.md` (¡no mezclar!):

```
power_avg_full / power_avg_steady / power_max_full / power_max_steady
steady_window_samples / steady_window_duration_s
```

Más variables de contadores (todas dentro de la **ventana steady** a menos que se indique):

| Grupo | Variable | Fuente | Unidad |
|---|---|---|---|
| Potencia | power1_input | hwmon | W (µW/1e6) |
| Térmico | temp1_input | hwmon | °C |
| Ocupación global | gpu_busy_percent, mem_busy_percent | sysfs | % |
| Clocks | nivel SCLK, nivel MCLK (pp_dpm_*) | sysfs | nivel + MHz (del map DPM: 7=1071, 2=1500) |
| Memoria | mem_info_vram_used, mem_info_gtt_used | sysfs | MB |
| Bloques GFX | gpu/vgt/ta/sx/sh/spi/sc/pa/db/cb/ee | radeontop dump | % busy |
| Ocupación shader | SPI_CSQ_WF_ACTIVE_COUNT_0..7 | umr | wavefronts activos |
| Reloj GPU (ref) | RLC_GPU_CLOCK_COUNT_LSB/MSB | umr | ticks GPU (acumulativo) |
| Auditoría no-programación | GRBM_PERFCOUNTER0/1_LO/HI, GRBM_SE0..3_LO/HI | umr | valor crudo (esperado 0) |

---

## 4. Controles

| Control | Método |
|---|---|
| **GPU correcta** | runs con `DRI_PRIME=1002:699f` (Superposition); E-03 exige RX 550 vía `requireRx550` (default) y devuelve `device: AMD Radeon RX 550 (RADV POLARIS12)` |
| **Display en iGPU** | No tocar; salida de video en Intel HD 4600 (card0) — la RX 550 es render-only |
| **Pre/Post flight idéntico** | Capturar `pre_flight.txt`/`post_flight.txt` por corrida: pp_dpm_sclk, pp_dpm_mclk, gpu_busy, power1, temp, mem_info. Debén coincidir (DPM `auto` + piso 214/300 MHz) |
| **Sin procesos extra** | `lsof /dev/dri/renderD129` previo: solo el workload |
| **Kalm intacto** | Verificar PIDs kalmd/kalm-lite activos antes y después (no tocar) |
| **Faults = 0** | `journalctl` filtrando `GPU fault\|VM fault` en la ventana temporal de cada corrida (como E-03) |
| **Baseline contadores no programados** | Sanity: GRBM/SE LO/HI = 0 antes y durante → confirma que naada programa contadores |

**Control explícito de no-igualación:** NO se escribe `pp_dpm_sclk`/`pp_dpm_mclk` ni `power1_cap`; cada workload corre bajo DPM `auto`.

---

## 5. Contadores (qué representa, semántica, normalización, hipótesis, candidatura)

### 5.1 Clase A — **incluidos en Etapa 2** (lectura pura, validada en etapa 1)

| # | Contador | Qué representa | Unidad/semántica | Acum/Instant | Normalización | Hipótesis | Vía de lectura |
|---|---|---|---|---|---|---|---|
| C1 | `power1_input` | Estimador SMU de consumo de la placa (NO potencia eléctrica directa) | W | Instant (10 Hz) | media/máx en ventana steady (4 métricas) | H8 | sysfs hwmon (`telemetria.sh`) |
| C2 | `gpu_busy_percent` | % del período en que GFX estuvo activo (front + shader apertado) | % | Instant | media steady | H8 (comparado contra bloques) | sysfs |
| C3 | `mem_busy_percent` | % del período que MC/DRAM vio actividad | % (NO = bandwidth absoluto) | Instant | media steady | H6 (proxi direccional) | sysfs |
| C4 | `pp_dpm_sclk`/`pp_dpm_mclk` (nivel `*`) | Nivel DPM activo (SCLK 0-7, MCLK 0-2) | nivel → MHz | Instant | distribución en steady | H8 (frecuencia real vs nominal) | sysfs |
| C5 | `temp1_input` | Temp del sensor `edge` de la GPU | °C (mC/1e3) | Instant | media/máx steady | contexto térmico (confusor) | sysfs |
| C6 | `mem_info_vram_used` / `mem_info_gtt_used` | Bytes residentes en VRAM / GTT | MB | Instant | media steady | H6 (presión de memoria) | sysfs |
| C7 | radeontop `gpu/vgt/ta/sx/sh/spi/sc/pa/db/cb/ee` | % busy por bloque de pipeline GFX8 (vgt=vertex grouper, ta=texture addresser, sh=shader, spi=shader processor input, sc=scan converter, pa=primitive asm, db=depth, cb=color, sx=shader export, ee=event engine) | % busy en intervalo (~1 s) | Instant por intervalo | media en steady; ratio Sup/E03 por bloque | **H1** (vgt/pa), **H2** (sc/db/cb), **H3** (ta), **H4** (sh/spi/sx), **H8** (ee y divergencia bloques vs gpu_busy) | `radeontop -d <file>` |
| C8 | `SPI_CSQ_WF_ACTIVE_COUNT_0..7` | Wavefronts (wavefronts) activos por cuarto/SE del shader processor input | conteo (0~n) | Instantáneo | media steady; Δ/frame; por CU (8 CUs) | **H4** (ocupación ALU real), **H8** (actividad no visible en busy %) | `umr -r` |
| C9 | `RLC_GPU_CLOCK_COUNT_MSB/LSB` | Contador 64-bit de ticks de reloj GPU (free-running reference) | ticks GPU | **Acumulativo** | **Δ_ticks/Δ_wall_s** → ≈ frecuencia real; Δ_ticks/frame | **H8**/validación de sclk real bajo clock gating | `umr -r` |
| C10 | `GRBM_PERFCOUNTER0/1_LO/HI`, `GRBM_SE0..3_LO/HI` | Contadores globales GRBM (sin SELECT no cuentan eventos) | valor crudo | Acumulativo | Δ/Δt si llegaran a ser ≠ 0 (auditoría de no-programación); si = 0 → neutral | H1/H8 (eventos IA-VGT) **pero solo como baseline** | `umr -r` |

### 5.2 Clase B — **EXCLUIDOS de Etapa 2 → candidatos Etapa 3** (requieren escritura de SELECT/CNTL para ser informativos)

| Contador | Representaría | Por qué Etapa 3 |
|---|---|---|
| `SQ_PERFCOUNTER0–15` | ciclos/datos por CU de shader | requiere programar SELECT+enable (escritura) |
| `CB_PERFCOUNTER0–3` | color buffer / ROP writes | requiere programar |
| `DB_PERFCOUNTER0–3` | depth / raster fill | requiere programar |
| `MC_ARB_PERFCOUNTER0–3` | tráfico VRAM arbiter | requiere CNTL |
| `MC_CITF_PERFCOUNTER0–3` | tráfico MC-CIF | requiere CNTL |
| `ATC_PERFCOUNTER0–3` | traducciones/GTT | requiere CFG |
| `CHUB_ATC_PERFCOUNTER0/1` | coherencia | requiere CFG |
| `GMCON_PERF_MON_CNTL0/1 + RSLT` | monitor GMC | requiere CNTL |
| `CPG/CPC/CPF_PERFCOUNTER*` | command processors | requiere SELECT |
| `RLC_PERFCOUNTER0/1`, `RLC_GPM_PERF_COUNT*` | microcódigo | parcialmente configurados por FW; interpretación dudosa |
| `TCP/TCC/TA` (texture/L2 caches) | texel/hit-miss L1/L2 | **solo vía SPM** (RLC ring), prohibido en Etapa 2 |

> Regla aplicada: *"Si algún contador requiere escritura/programación, excluirlo de Etapa 2 y marcarlo como candidato para Etapa 3"* → los de §5.2 **no** se instrumentarán en Etapa 2; se leerán **cero lecturas**.

---

## 6. Metodología

1. **Secuencia por workload/replica (`run`):** pre_flight capture → arrancar samplers (telemetría + radeontop + UMR) → lanzar workload → detectar inicio de régimen → mantener N s de telemetría → detener workload (superposition: esperar score o timeout 260 s; E-03: termina solo) → detener samplers → post_flight capture → verificar faults/DPM.
2. **Orden:** A1 B1 A2 B2 A3 B3 (Superposition A, E-03 B) con pausas idle 30/60 s.
3. **Inicio de régimen:** alineado por timestamp de la línea "Benchmark running" (Superposition) o inicio de measure `warmup` (E-03, frame 46+). Todos los samplers registran epoch-ns → alineación exacta offline.
4. **Ventana steady:** definición de `METRICS-DEFINITIONS.md` §1.4: `gpu_busy ≥ 95` Y `sclk ≥ 1071 MHz` Y `mclk ≥ 1500 MHz`, tras descartar ~5 s iniciales; ≥ 100 muestras (≥10 s). Si no se alcanza → `power_avg_steady = N/A` (no inventar).
5. **Muestreo:** sysfs 10 Hz (script `telemetria.sh`); radeontop 1 Hz (`-l N -i 1` cubre toda la ventana); UMR ~1 Hz (8× SPI_CSQ + RLC clock + GRBM baseline por tick).
6. **Duración telemetría por run:** Superposition 260 s (world_load + benchmark hasta score), E-03 40 s (5 warmup + 20 measure + margen). El corte de análisis usa la ventana steady alineada.
7. **Repeticiones:** 3 por workload (6 corridas totales) — suficiente para rangos/CI exploratorios; no se declara significancia paramétrica con n=3.

---

## 7. Normalización

- **Potencia:** 4 métricas exactamente como `METRICS-DEFINITIONS.md` (nunca mezclar `_full` con `_steady`; etiquetar `NOT DIRECTLY COMPARABLE` si se cruzan).
- **Instantáneos (% busy, WF activos, temp, VRAM):** media aritmética en ventana steady (`avg_steady`) + máx steady.
- **Acumulativos (C9 RLC clock; C10 si ≠ 0):**
  - `rate_per_wall_s = Δ_counter / Δ_wall_time_s`
  - `per_frame = Δ_counter / F (frames en ventana)` — F conocido: E-03 fps ≈ 8.95 (measure 179 frames); Superposition frames = wall_s × fps medio del log si está disponible, si no → solo `rate_per_wall_s`.
  - `per_work_unit = per_frame / (1920×1080)` (por pixel renderizado; capas: E-03 ×4) — opcional informativo.
- **NUNCA** comparar valores brutos de contadores acumulativos entre workloads de distinta duración.
- **Ratio diferencial:** `ratio_bloque = avg_steady(Sup) / avg_steady(E03)` por bloque; reportar con rango min–max entre réplicas.

---

## 8. Hipótesis evaluables (sin confirmar)

| Hip | Formulación medible en Etapa 2 |
|---|---|
| **H1** geometría/vertex | `vgt`/`pa` (C7) y baseline GRBM (C10) notablemente > en Superposition |
| **H2** rasterización/ROPs | `sc`/`db`/`cb` (C7) > en Superposition |
| **H3** texture units/fetch | `ta` (C7) alta en ambos pero distinta por-frame; ocupación de fetch vs idle |
| **H4** ALU/shader | `sh`/`spi`/`sx` (C7) + `SPI_CSQ_WF_ACTIVE_COUNT` (C8): ocupación real de wavefronts |
| **H5** caches L1/L2 | **NO medible en Etapa 2** (requiere SPM/TCC → Etapa 3). Se marca pendiente; se infiere indirecto por `ta`/`mem_busy` |
| **H6** VRAM traffic | `mem_busy` (C3), `vram/gtt` (C6) + contexto MCLK (C4): si mem_busy no difiere y MCLK igual → tráfico no es el diferenciador |
| **H7** radeonsi vs RADV | Diferencia sistemática en ocupación/bloques al mismo tipo de carga; análisis cualitativo cross-workload (A vs B) |
| **H8** actividad interna no vista por busy | Divergencia gpu_busy ~100 % vs bloques individuales bajos (E-03: gpu 19 % en diagnóstico); RLC_GPU_CLOCK_COUNT (C9) para frecuencia real efectiva bajo clock gating |

Ninguna hipótesis se declara confirmada; el producto de Etapa 2 es evidencia direccional para V/O.

---

## 9. Criterios de interpretación

| Señal | Lectura |
|---|---|
| `ratio_bloque ≥ 1.5` (y rangos no solapados) | Fortalece la hipótesis del bloque |
| `ratio_bloque ≈ 1` en mem_busy pero `ratio_potencia 1.42` (22.31/15.75) | H6 debilitado; el diferenciador es ocupación de unidades GFX |
| `SPI_CSQ_WF_ACTIVE_COUNT` alto en Sup + `sh`/`spi`/`sx` altos | H4 fuerte |
| `ta` alto en ambos pero por-frame distinto | H3 → texturas por fotograma, no por unidad |
| `RLC_GPU_CLOCK_COUNT/Δwall` ≈ 1071 MHz en Sup pero ≪ en E-03 | H8: clock-gating real de GFX en E-03 |
| `gpu_busy ~100 %` con `vgt/pa/sh` bajos en E-03 (busy sin actividad de bloques) | H8: busy agregado no captura microactividad |
| Todos los bloques bajos en E-03 (como diagnóstico etapa 1, gpu 19 %) | H8/H1-H4: E-03 pasa gran parte del tiempo idle (fetch-latency) — potencia de fondo |

Regla de no-confirmación: ninguna hipótesis se marca `VERIFICADA`; solo `APOYADA`/`DEBILITADA`/`PENDIENTE (Etapa 3)`.

---

## 10. Posibles confusores

| Confusor | Mitigación |
|---|---|
| Deriva térmica / PowerPlay auto | Intercalado A/B, pausas idle 30/60 s, temporal cap 260 s |
| Clock gating race (GFX off) | Leer SPI/RLC en cada tick (si devuelve 0 durante gate, se marca `gated`); pre/post verify |
| Overhead de samplers (sudo UMR ~30-60 ms/tick) | 1 Hz suficiente; se documenta pérdida ≤ ~6 % del intervalo |
| Lecturas MMR de radeontop | Mínimas (ioctl kernel, no bloquean); aceptado |
| Superposition sin FPS textual en algunos logos | Calcular F pot per wall_s × fps log; si no, solo `rate_per_wall_s` |
| Afinidad CPU / sync GL | i7-4790 con HT; sin cambios de CPU governor (no tocar) |
| Idle residual earlier/later en telemetría | Ventana steady strict (METRICS-DEFINITIONS); descartar fuera |
| Los 4 textos de E-03 vs texturas completas de Sup | No pretendemos igualar; la VRAM distinta queda como variable observada (C6), no control |

---

## 11. Riesgos

| Riesgo | Impacto | Control |
|---|---|---|
| Lectura MMIO con GFX idle devuelve 0/garbage | Pérdida de datos en E-03 | Marcar `gated`; usar C2/C7 para contexto |
| timeout Superposition (260 s) sin score | Pérdida de réplica | Repetir réplica (n=3) |
| Línea `Benchmark running` ausente | Alineación imprecisa | Alinear por primer steady sample (fallback) |
| sudo UMR interfiere con E-03 (Vulkan) | Jitter frametime | Medir frametime del propio E-03 (log) y descartar anomalías |
| Deriva de clocks tras 60-120 s | Steady inválido | Validar ≥100 muestras steady; si falla, N/A |
| Desborde de RLC_GPU_CLOCK_COUNT (64-bit) | n/d (no alcanzable en 260 s) | Monitoreo Δ |
| Interpretar harden counters sin SELECT como significativos | Falso positivo | GRBM sin SELECT = 0 → NO informativo (solo baseline) |

---

## 12. Criterio de éxito

**ÉXITO =** para al menos **2 hipótesis de H1–H8**, producir una señal direccional limpia (ratio de bloque ≥ 1.5 o comportamiento claramente distinto por-frame) dentro de rangos de réplicas no solapados, **sin tocar** ninguna configuración y **sin programar contadores**. Incluye entregable: tabla `bloque × ratio_Sup/E03 × lectura` y estado `APOYADA/DEBILITADA/PENDIENTE` por hipótesis.

**ÉXITO PARCIAL =** ratios superpuestos pero con patrones sistemáticos → se documenta como inconcluso y se diseña Etapa 3 (contadores programados + SPM).

---

## 13. Comandos exactos que se ejecutarían (PLAN — NO EJECUTADOS)

> Comandos para **una réplica**. Directorios: `WORK=/home/lucas/Escritorio/RX550-INVESTIGACION`; runs en `${WORK}/03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/<A|B><n>/`.

```bash
# ===== PRE-FLIGHT (workload-idnetico; no se escribe nada a sysfs) =====
RUN=${WORK}/03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/A1
mkdir -p "$RUN"                                   # crea directorio de artefactos (no sistema)

DEV=/sys/class/drm/card1/device
HWMON=$DEV/hwmon/hwmon2
{ echo "== pre_flight =="; cat $DEV/pp_dpm_sclk $DEV/pp_dpm_mclk;
  cat $HWMON/power1_input $HWMON/temp1_input;
  cat $DEV/gpu_busy_percent $DEV/mem_busy_percent;
  cat $DEV/mem_info_vram_used $DEV/mem_info_gtt_used; } > "$RUN/pre_flight.txt"

# ===== SAMPLERS (read-only) =====
# 1) telemetría sysfs 10 Hz (script existente, read-only):
$WORK/03-EXPERIMENTOS/EXPLORATORIO-GravityMark/telemetria.sh 260 "$RUN/telemetria.csv" &  # A; para B: 40

# 2) radeontop dump 1 Hz durante toda la ventana (solo lee vía ioctls libdrm):
sudo radeontop -p /dev/dri/renderD129 -d "$RUN/radeontop.csv" -l 260 -i 1 &          # A; para B: -l 40

# 3) samplers UMR 1 Hz (LEE solo; comando -r NUNCA escribe registros):
( i=0; while [ $i -lt 266 ]; do
    TS=$(date +%s%N)
    SPI=$(for q in 0 1 2 3 4 5 6 7; do sudo umr -i 1 -r "polaris12.gfx800.mmSPI_CSQ_WF_ACTIVE_COUNT_$q" 2>/dev/null; done | tr '\n' ' ')
    RLC=$(sudo umr -i 1 -r polaris12.gfx800.mmRLC_GPU_CLOCK_COUNT_LSB 2>/dev/null; sudo umr -i 1 -r polaris12.gfx800.mmRLC_GPU_CLOCK_COUNT_MSB 2>/dev/null)
    GRBM=$(sudo umr -i 1 -r polaris12.gfx800.mmGRBM_PERFCOUNTER0_LO 2>/dev/null)  # baseline de no-programación
    printf "%s;%s;%s;%s\n" "$TS" "$(echo $SPI | tr -s ' ' ';')" "$(echo $RLC)" "$GRBM" >> "$RUN/umr_samples.csv"
    sleep 1; i=$((i+1)); done ) &

# ===== WORKLOAD A (snapshot histórico; no ejecutar aquí) =====
# La corrida observada en R-14 fue 1600x900/Medium; la petición High/1920
# no es la configuración efectiva y no debe copiarse como gate.
cd /home/lucas/Escritorio/berchmark/instalados/Unigine_Superposition-1.1/bin
DRI_PRIME=1002:699f ./superposition \
  -project_name "Superposition" -video_mode=-1 \
  -console_command "world_load superposition/superposition" \
  -video_app opengl -quality medium -mode default -iterations 1 \
  -sound 0 -fullscreen 0 -resolution 1600x900 \
  -log_csv "$RUN/superposition.csv" -log_txt "$RUN/superposition.txt" \
  > "$RUN/superposition.log" 2>&1 &
SP_PID=$!
# espera hasta score (máx 260 s); luego termina (si timeout -> kill, igual que R-14)
# ===== POST-FLIGHT ===== (idéntico al pre_flight -> $RUN/post_flight.txt)

# ===== WORKLOAD B (E-03 base Diseño B; config = defaults canónicos) =====
cd $WORK/03-EXPERIMENTOS/WORKLOAD-SINTETICO
DRI_PRIME=1002:699f ./main-graphics --width 1920 --height 1080 --layers 4 --textures 4 --tex-size 4096 --fma-iters 4 --msaa 1 --seed 0x13579BDF --seed-extra 0x2468ACE0 --warmup 5 --duration 20 > "$RUN/stdout.txt" 2> "$RUN/stderr.txt"
# pre_flight/post_flight + fault check ~igual que E-03 (journal_pres.txt con journalctl)
```

---

## 14. Comandos que escriben algo (auditoría explícita de escritura)

Conforme a la regla "Etapa 2 = SOLO lecturas", el **único** "writing" es a **artefactos de output del experimento** (nunca a estado del sistema):

| Comando/acción | Qué escribe | ¿Altera estado GPU/sistema? |
|---|---|---|
| `mkdir -p "$RUN"` | directorio de artefactos | **NO** (sistema de archivos del proyecto) |
| `telemetria.sh` (script existente) | `telemetria.csv` (crea/append) | **NO** (lee sysfs; escribe archivo de output) |
| `radeontop -d "$RUN/radeontop.csv"` | archivo de output del dump | **NO** (solo lee registros vía ioctls) |
| Loop UMR `-r` + `>> "$RUN/umr_samples.csv"` | archivo CSV de muestras | **NO** (`-r` es exclusivamente lectura de registro) |
| `> "$RUN/superposition.log"` / `-log_csv/-log_txt` | logs de la app | **NO** |
| `> "$RUN/pre_flight.txt"`/`post_flight.txt"` | capturas de estado leídas | **NO** |
| `journalctl` a archivo (`journal_pres.txt`) | filtro de log del sistema | **NO** (lectura) |

**Lo que NO se ejecuta (y por qué):**
- `echo … > $DEV/pp_dpm_*`, `echo … > $HWMON/power1_cap` → **NUNCA** (sysfs write prohibido).
- `umr -w` o cualquier `--write` → **NUNCA** (escribiría MMIO; ni siquiera presente en los comandos).
- Selección de evento de contador (SELECT/CNTL/CFG/SPM ring) → **NO** → pospuesto a Etapa 3.
- Instalación de paquetes → **NO** (regla FASE D; herramientas ya presentes/validadas).
- Modificación de configs de Superposition / E-03 / Mesa / kernel / PowerPlay / Kalm / rx550-torneo → **NO**.

Con esto, toda la Etapa 2 es read-only a nivel de GPU/sistema; únicamente se generan ficheros de artefactos en `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/`.

---

## 15. Estado

**Etapa 2 planificada; ejecución pendiente de autorización.**
Este documento es el entregable autorizado; no ejecuta corridas. Para ejecutar, se requiere autorización explícita del operador (no derivable de esta planificación).
