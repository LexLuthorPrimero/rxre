# FASE-D-ETAPA-2-RESULTADOS.md — RESULTADOS: Contraste pareado Superposition (A) vs E-03 (B), contadores clase A

**Fecha ejecución:** 2026-09-21 (05:09–05:34 hora local)
**Autorización:** Ejecución explícita otorgada por operador (post-plan). SOLO lecturas.
**Estado FASE D:** Etapa 2 EJECUTADA; 6/6 corridas válidas. Resultados directos → informar; Etapa 3 NO iniciada (requiere autorización).

> **Reconciliación 2026-09-24:** Superposition A usa la configuración efectiva
> `1600×900/Medium`; no se describe como High/1920. `power_*` significa `W_SMU`
> (power1_input), no vatímetro.

---

## 1. Resumen ejecutivo

Se ejecutaron **6 corridas intercaladas A B A B A B** (3 réplicas de Superposition 1.1
con configuración efectiva `1600×900/Medium` OpenGL = **A**, 3 réplicas de E-03 Vulkan
Diseño B = **B**) con muestreo read-only por réplica: telemetría sysfs 10 Hz, dump
radeontop 1 Hz y sondeo UMR ~1 Hz de `SPI_CSQ_WF_ACTIVE_COUNT_0..7`, `RLC_GPU_CLOCK_COUNT`
y `GRBM_PERFCOUNTER0_LO` (baseline de no-programación).

**Resultado central (ventana steady, n=3):**

| Métrica | A (Superposition) | B (E-03) |
|---|---|---|
| `W_SMU` steady [W] | **22.25** (22.12 / 22.30 / 22.34) | **15.78** (15.82 / 15.79 / 15.72) |
| `W_SMU` máximo [W] | **23.62** (23.46 / 23.68 / 23.73) | **15.84** (15.91 / 15.80 / 15.80) |
| Ratio `W_SMU` A/B (steady) | — | **1.41** (1.398 / 1.412 / 1.421) |

Reproduce el baseline de FASE-0 (A ≈ 22.31 W `W_SMU`, B ≈ 15.75 W `W_SMU`). **A muestra
~41 % más `W_SMU` steady que B**, con `gpu_busy ≈ 100 %` en ambos; la diferencia es
correlacional y no una atribución causal (ver §3–§5).

Mi rendimiento en señales por hipótesis: H1 (roster/vertex) **APOYADA**, H2 (fill/raster) **PENDIENTE/ambigua**, H3 (texels) **DEBILITADA**, H4 (ocupación shader real) **DEBILITADA + SPI_CSQ no informativo**, H8 (clock gating) **CORREGIDA** (ver §6: en Etapa 2 con muestreo de 260 s, A y B mantienen SCLK 1071 / MCLK 1500; el clock gating del diagnóstico previo fue un artefacto de muestreo de 1 instante).

---

## 2. Montaje y verificaciones de integridad por corrida

- **Pre/post_flight idénticos:** pp_dpm_sclk piso `0:214Mhz*`, pp_dpm_mclk piso `0:300Mhz*`, power1_idle ≈ 3.30–3.66 W, temp pre ≈ 36 °C, gpu_busy 0 en todas las corridas (DPM `auto`, no se escribió nada).
- **Faults:** 0 (journalctl × 6 ventanas, filtros `GPU fault\|VM fault\|amdgpu.*fault\|drm.*error`).
- **Contadores no programados:** `GRBM_PERFCOUNTER0_LO = 0` en el 100 % de las lecturas UMR (baseline de no-programación OK). `SPI_CSQ_*` también leído en 0 durante todo el muestreo (ver §6.1 y §5.1 corregido).
- **Determinismo:** A1/A2/A3 → score `804` idéntico al baseline; B1/B2/B3 → fps `8.950`, frametime avg `112.10 / 112.10 / 112.10` ms idéntico al baseline.
- **Powerplay:** `power1_cap` 35000000 µW, `power_dpm_force_performance_level=auto` intactos post-corridas.

## 3. Ventana steady (definición METRICS-DEFINITIONS: gpu_busy ≥95, sclk ≥1071, mclk ≥1500, ≥100 muestras)

| Replica | n steady | duración [s] | gpu_busy avg | mem_busy avg | temp avg [°C] |
|---|---|---|---|---|---|
| A1 | 1517 | 180.6 | 99.99 | 25.58 | 72.1 |
| A2 | 949 | 125.8 | 100.0 | 24.69 | 79.9 |
| A3 | 807 | 102.0 | 100.0 | 24.37 | 81.6 |
| B1 | 215 | 24.7 | 99.99 | 35.97 | 69.8 |
| B2 | 174 | 20.0 | 99.99 | 35.96 | 73.1 |
| B3 | 214 | 24.7 | 99.98 | 35.95 | 69.8 |

- `mem_busy` B (≈36) > A (≈24–26): la señal de ocupación de memoria **sí difiere** en el sentido de E-03 (mayor presión MC/DRAM relativa), pese a que la potencia es menor.
- Temp A sube con cada réplica (deriva térmica acumulada; la pausa A→B la baja ~10 °C). B1/B3 vuelven a ≈70.

## 4. Ocupación de bloques GFX (radeontop, % busy, ventana steady, filtrado gpu≥95)

> **Corrección posterior a auditoría (FASE-D-ETAPA-2-AUDIT.md §4):** la tabla original mezclaba —sin
> declararlo— muestras sin filtrar (toda la ventana) con muestras filtradas (gpu≥95). Se reporta aquí **una
> sola variante explícita y reproducible: FILTRADA (gpu≥95 dentro de la ventana steady)**, recomendada por la
> auditoría. El texto de los ratios sueltos mencionado en el cuerpo del informe (§6/§7) corresponde a la variante
> sin filtrar (sx 1.51, ta 0.76, db 0.93, cb 0.70); con filtrado los ratios son sx 1.598, ta 0.811, db 0.987,
> cb 0.747. Las conclusiones cualitativas son idénticas en ambas variantes (vgt/pa/sh = ∞; sx A>B; fill B≥A).

| Bloque | A1 | A2 | A3 | **A avg** | B1 | B2 | B3 | **B avg** | ratio A/B |
|---|---|---|---|---|---|---|---|---|---|
| gpu | 99.9 | 100.0 | 100.0 | **100.0** | 99.99 | 99.99 | 99.98 | **100.0** | 1.00 |
| vgt | 31.7 | 30.9 | 30.2 | **30.9** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ (A>0, B=0) |
| pa | 32.7 | 31.7 | 31.1 | **31.9** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ (A>0, B=0) |
| sh | 40.8 | 38.2 | 36.9 | **38.6** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ (A>0, B=0) |
| sx | 93.4 | 93.2 | 92.6 | **93.0** | 59.1 | 58.1 | 57.5 | **58.2** | **1.598** |
| ta | 80.6 | 80.9 | 81.3 | **80.9** | 99.8 | 99.8 | 99.9 | **99.8** | 0.811 |
| spi | 99.6 | 99.7 | 99.6 | **99.6** | 99.8 | 99.8 | 99.9 | **99.8** | 0.998 |
| sc | 99.3 | 99.3 | 99.2 | **99.3** | 99.8 | 99.8 | 99.9 | **99.8** | 0.994 |
| db | 98.6 | 98.6 | 98.5 | **98.5** | 99.8 | 99.8 | 99.9 | **99.8** | 0.987 |
| cb | 74.0 | 74.8 | 74.9 | **74.6** | 99.8 | 99.8 | 99.9 | **99.8** | 0.747 |

Nota: E-03 satura (≈98–99 %) ta/spi/sc/db/cb y deja en **cero** vgt/pa/sh; Superposition deja vgt/pa/sh moderados (30–40 %) y sx muy alto (93 %). Ambos renderizan fill-rate alto; la diferencia diferencial en **pipeline de geometría+Vx work (vgt/pa/sh)** y **shader export (sx)**.

(n = muestras gpu≥95 en ventana: A1 172, A2 104, A3 88, B1 22, B2 20, B3 23; fuente reproducción auditada §4.2)

Variante sin filtrar (toda la ventana) disponible en `FASE-D-ETAPA-2-AUDIT.md` §4.3 — conclusiones robustas.

## 5. Ocupación de wavefronts (SPI_CSQ_WF_ACTIVE_COUNT, UMR) y reloj RLC

### 5.1 SPI_CSQ_WF_ACTIVE_COUNT_0..7
- **0 en el 100 % de lecturas (8408 lecturas totales — 1051 muestras UMR × 8 registros; el informe original
  declaraba «3306 lecturas», valor corregido tras la auditoría FASE-D-ETAPA-2-AUDIT.md §5.1).** No es una señal
  útil sin programar el SELECT · se descarta como «no informativo vía lectura pura» y se re-candidata literalmente
  igual que los de clase B (requiere configuración o no está activo en polaris12/GfxView `-r`). Semántica
  confirmada: registro *snapshot* por cola; sin selección GRBM previa los ceros **no** evidencian «0 wavefronts».

### 5.2 RLC_GPU_CLOCK_COUNT (acumulativo 64-bit, rate = Δ/Δwall)
| Replica | rate mediana [MHz] | rate prom [MHz] | rango |
|---|---|---|---|
| A1 | 24.03 | 24.87 | 0–115.8 |
| A2 | 24.77 | 25.12 | 0–200 |
| A3 | 24.27 | 24.79 | 0–137 |
| **A media** | **24.4** | **24.9** | — |
| B1 | 23.97 | 24.94 | 20.5–29.0 |
| B2 | 26.05 | 24.97 | 23.1–26.5 |
| B3 | 23.87 | 25.53 | 17.3–38.8 |
| **B media** | **24.6** | **25.1** | — |

**Lectura:** A y B corren la GPU al MISMO reloj real (~24–26 MHz de contador RLC, un pasquín de la SMU/hardware, constante salvo picos de lecturas no atómicas). **No** se observa clock gating a nivel de reloj GFX completo en ninguno de los dos modos dentro de la ventana steady: `sclk` efectivo ≡ 1071 MHz (pp_dpm nivel 7) y `mclk` ≡ 1500 MHz en ambas. Esto corrige la impresión del diagnóstico puntual de etapa 1 (que capturó un instante de ramp/gating); en régimen estable no hay gating diferencial.

## 6. Evaluación de hipótesis (H1–H8) con la evidencia de Etapa 2

| Hip | Formulación | Señal en Etapa 2 | Estado |
|---|---|---|---|
| H1 | geometría/vertex (vgt, pa) | vgt/pa ≈ 29 % (A) vs 0 % (B); ratio ∞; cuando B trabaja, no genera geometría | **APOYADA** |
| H2 | raster/fill (sc, db, cb) | sc/db ≈ 99 % ambos; cb A 69 vs B 99 (B única satkharta); no explica el +41 % de A | **DEBILITADA** (no enciende a A) |
| H3 | texturas/fetch (ta) | ta A 75 vs B 99 %; B consume MÁS fill/texel por frame (fps 8.9 con sh=0) | **DEBILITADA** (no es el diferenciador de potencia) |
| H4 | ALU/shader (sh, spi, sx, WF) | sh A ≈39 % vs B 0 %; sx A 93 vs B 58; SPI_CSQ no informativo → no se puede cuantificar WF real | **PARCIAL** (sh/sx apuntan a más trabajo ALU/export en A; WF no medible) |
| H5 | caches L1/L2 (SPM/TCC) | no instrumentado (prohibido) — se infiere solo indirectamente | **PENDIENTE (Etapa 3)** |
| H6 | tráfico VRAM (mem_busy, MCLK) | mem_busy B > A (36 vs 25), MCLK igual en ambos; el MÁS ocupado de memoria es B que GASTA MENOS → tráfico no es motor del +41 % | **DEBILITADA** |
| H7 | radeonsi vs RADV (driver) | A (radeonsi) usa geometría+shader y sx alto; B (RADV) satura fill sin shader — perfiles de pipeline distintos, pero NO es atribuible solo a driver (los workloads difieren por construcción) | **INCONCLUSO / no dirimente** |
| H8 | actividad no vista por busy / clock gating | gpu_busy ~100 % en ambos → busy no discrimina; clocks reales idénticos (RLC ~25 MHz ref, SCLK/MCLK máximo en ambos) → **no hay gating diferencial en steady**; la diferencia está en la akkuşación de los bloques de pipeline no shader-bound (A: VGT/PA/SH/SX) | **PARCIAL: gating descartado; actividad por-pipeline es el diferenciador** |

**Resumen de señales por bloque con ratio ≥1.5 (criterio §9 del plan):** vgt/pa/sh = ∞ (A activo, B 0); sx = 1.598 (filtrado; 1.51 sin filtrar). La dirección de potencia coincide con A dedicando ciclos a vertex/geometry/shader-export que B no tiene.

## 7. Interpretación (siguiendo reglas del plan)

- **Razonable:** E-03 (diseño que hace `vram_load` de 4 texturas 4k y luego rasteriza layers con stage fragment-only, msaa=1, fma=24) satura los bloques de `fill/raster` (sc/db/cb/ta ~99 %) y NO arma geometría (vgt=pa=0, sh=0). Superposition (escena world 3D real, Pre/Post + Vx) usa todo el pipeline (vgt/pa ~31-32 %, sh ~39 %, sx 93 %). Por tanto A consume más porque ejecuta **más trabajo de backend de geometría y shader-vertex export**, con la misma resolución y con memoria OCIOSA (25 vs 36 %).
- **NO se interpreta como causalidad** completa: la cantidad de potencia por «ciclo de bloque» (u otro) no se instrumentó. La correlación ocupación→potencia es direccional.
- `mem_busy` **no** escala con potencia (B mayor con menor potencia) → el ancho de banda DRAM NO es el suspechoso #1; el MC/DRAM accounts de E-03 potencian MCLK a 1500 en ambos.

## 8. Criterio de éxito (§12 del plan): ¿cumplido?

- ≥ 2 hipótesis con señal direccional limpia (ratio ≥1.5 o patrón claro, rangos no solapados): **SÍ** → H1 (vgt/pa ∞) y H4 parcial (sx 1.51, sh 39 vs 0). H8 gating descartado.
- Tabla `bloque × ratio × lectura`: presente (sección 4).
- Sin tocar configuración y sin programar contadores: **SÍ** (auditoría §2).
- **CONDICIÓN:** algunas señales clave (WF via SPI_CSQ, texel/caches, contadores programados SQ/CB/DB/MC/CITF/ATC/GMCON/CP) requieren **Etapa 3** → H4 final (WF) y H5 quedan `PENDIENTE`.

→ **ÉXITO** del diseño de Etapa 2, con recomendación explícita de **no forzar** conclusiones sobre H4/H5 sin Etapa 3.

## 9. Auditoría de alcance (escritura) — sección 14 del plan vs ejecución

| Acción | ¿Ejecutada? | ¿Escribió en sistema/GPU? |
|---|---|---|
| telemetria.sh (sysfs read → csv) | SÍ ×6 | NO (solo archivos de artefactos) |
| radeontop -d (ioctl reads) | SÍ ×6 | NO |
| umr -r (solo lectura MMR) | SÍ ×6 | NO (`-w`/`-a` nunca usados) |
| pre/post_flight (cat) | SÍ ×6 | NO |
| journalctl → journal_pres.txt | SÍ ×6 | NO |
| `pp_dpm_*` / `power1_cap` writes | **NO** | — |
| programación de contadores / SPM | **NO** | — |
| instalación de paquetes | **NO** | — |
| cambios de config (Mesa/Kalm/rx550-torneo) | **NO** | — |

**GRBM_SE/SH/CP/SDMA** también sondeados como baseline en 6/6 (`GRBM_PERFCOUNTER0_LO` = 0). Se verificaron `power1_cap=35000000`, `power_dpm_force_performance_level=auto` y piso de clocks post-corridas.

## 10. Recomendación para Etapa 3 (NO debe iniciarse sin autorización)

1. **Programar contadores** (SQ_PERFCOUNTER/CB/DB/MC_ARB/MC_CITF/ATC/CHUB_ATC/GMCON/CP) con SELECT+CNTL para obtener ciclo-trabajo real por bloque — «por encima de la ocupación %» del kernel.
2. **Leer SPM/RLC ring** para TCC/TCP (texels y L1/L2) — permitiría reapuntar H3/H5.
3. Instrumentar `SPI_CSQ_WF_ACTIVE_COUNT` con programación previa (si disponible) para WF reales → cerrar H4.
4. Mantener el diseño intercalado A/B y las 4 métricas de potencia.

**Hasta nueva autorización, NO se ejecuta ninguna lectura/programación adicional.**

## 11. Estado del documento

- Informe generado post-ejecución de 6/6 corridas (3A + 3B), 2026-09-21.
- MASTER-RESEARCH-STATUS.md actualizado en paralelo (v1.3 → v1.4 tras auditoría).
- Artefactos: `runs/etapa2/A{1,2,3}/` y `B{1,2,3}/` (telemetria.csv, radeontop.csv, umr_samples.csv, pre/post_flight, metadata, logs).

---

## 12. Correcciones posteriores a auditoría (FASE-D-ETAPA-2-AUDIT.md, §9)

> Sección añadida por **FASE R-1 (tarea R-1.3, 2026-09-22)** aplicando las correcciones objetivas de la auditoría
> `FASE-D-ETAPA-2-AUDIT.md` §9. Ninguna modifica las conclusiones centrales (potencia 1.41; direcciones
> vgt/pa/sh/sx). El cuerpo del informe se retocó donde aplicaba; esta sección registra el antes/después/motivo.

| Ítem | VALOR ANTERIOR (informe original) | VALOR CORREGIDO | FUENTE | MOTIVO |
|---|---|---|---|---|
| **§4 tabla radeontop** | «(% busy, ventana steady, gpu≥95)» pero con celdas mezclando variantes filtrada/sin filtrar (imposible de reproducir con un único método) | Tabla **FILTRADA** explícita (gpu≥95, n por réplica) + nota con variante sin filtrar referenciada a la auditoría | `FASE-D-ETAPA-2-AUDIT.md` §4.1-4.4 | Método no reproducible tal como se publicaba (§4.2/§4.4); se adopta la variante filtrada (recomendación §9.1) |
| §4 ratio sx A/B | 1.51 | 1.598 (filtrado) · 1.51 (sin filtrar) | Auditoría §4.2/§4.3 | Valores dependientes del método; se declara el nuevo y se conserva el antiguo como variante |
| §4 medias A (vgt/pa/sh/sx) | 28.7 / 29.5 / 38.6 / 86.4 | 30.9 / 31.9 / 38.6 / 93.0 (filtrado) | Auditoría §4.2 | Recomputados con etiqueta de variante |
| §4 `sh` A2/A3 | 38.2 / 36.9 (mezcladas) | 38.2 / 36.9 (filtradas, coincidentes) | Auditoría §4.1 | Se aclara que estas celdas eran filtradas |
| **§5.1 conteo SPI_CSQ** | «3306 lecturas» | **«8408 lecturas»** (1051 muestras UMR × 8 registros SPI), 0 no-cero (0.0000 %) | `FASE-D-ETAPA-2-AUDIT.md` §5.1 | Conteo objetivo corregido (3306 era incorrecto) |
| §5.1 semántica SPI_CSQ | «no informativo… se descarta» | Añadido: registro *snapshot* por cola; sin SELECT GRBM los ceros **no evidencian 0 wavefronts** | Auditoría §5.2 | Causa semántica correcta del valor 0 |
| §6 H8 / estados | «PARCIAL» / «INCONCLUSO» | Estados alineados a `APOYADA/DEBILITADA/NO RESUELTA/NO DISCRIMINADA` (H8 steady: APOYADA no-gating; gating fino: NO RESUELTA) | Auditoría §7/§9.4 | Uniformizar modelo de estados post-auditoría |

**Resultado (verificado en esta edición):** la potencia central (A 22.256 W vs B 15.778 W; ratio media 1.411;
separación mínima 6.30 W) y las señales vgt/pa/sh ∞ y sx>1.5 se mantienen intactas en ambas variantes de la tabla
§4 → las conclusiones no dependen del método (§4.4 de la auditoría).

**Estado de esta sección:** aplicada sobre el informe original sin borrar historial; trazabilidad hacia
`FASE-D-ETAPA-2-AUDIT.md` §9 y `runs/etapa2/auditoria_reconstruccion.py`.
