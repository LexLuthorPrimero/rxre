# FASE-D-ETAPA-2-AUDIT.md — AUDITORÍA de los resultados de Etapa 2 (Superposition A vs E-03 B, contadores clase A)

**Fecha:** 2026-09-21 (post-ejecución de 6/6 corridas)
**Modo:** SOLO lectura/análisis de artefactos. Sin corridas, sin Etapa 3, sin programación de contadores, sin MMIO/sysfs/PowerPlay/Mesa/Kalm/rx550-torneo.
**Referencia:** `FASE-D-ETAPA-2-RESULTADOS.md` (informe original) · artefactos en `runs/etapa2/A{1,2,3},B{1,2,3}/`
**Método de auditoría:** reconstrucción independiente de TODAS las métricas desde los CSV crudos (`auditoria_reconstruccion.py`) y contraste célula-a-célula con el informe. Estados de hipótesis restringidos a `APOYADA / DEBILITADA / NO RESUELTA / NO DISCRIMINADA` (sin causalidad asumida).

---

## 1. Resumen ejecutivo de la auditoría

1. **Potencia y ventanas steady: la reconstrucción reproduce el informe EXACTAMENTE** (mismo resultado en todos los dígitos publicados). Este bloque es sólido.
2. **Error objetivo n.º 1 — Tabla §4 del informe no es reproducible con un único método.** Las celdas de radeontop mezclan cómputo «sin filtrar (todas las muestras de la ventana)» y «filtrado gpu≥95» sin declararlo. Se aportan las dos tablas limpias y reproducibles (§4 aquí). Las conclusiones cualitativas NO cambian (robustas a ambos métodos).
3. **Error objetivo n.º 2 — Conteo SPI_CSQ.** El informe §5.1 declara «3306 lecturas»; la reconstrucción da **8408 lecturas** (1051 muestras UMR × 8 registros). Todas cero (0.0000 %), como decía el informe.
4. **Semántica confirmada:** radeontop mide **ciclo de trabajo** (duty cycle) de bits `busy` de `GRBM_STATUS`, NO trabajo contado; un «0 %» no prueba ausencia absoluta. `SPI_CSQ_WF_ACTIVE_COUNT_*` es registro *snapshot* por cola que en kernel exige programar el SELECT GRBM (MEID/PIPEID/QUEUEID/VMID); leído sin programar → ceros no informativos, no evidencian «0 wavefronts».
5. **Relojes (H8):** en las 6 corridas, el 100 % de las muestras steady tienen `sclk` nivel 7 (1071 MHz) y `mclk` nivel 2 (1500 MHz); `RLC_GPU_CLOCK_COUNT` Δ/Δt ≈ 24–26 MHz en ambas cargas. Reforzado: no se observa gating diferencial en régimen steady a esta resolución.
6. **Matriz de hipótesis (§7):** H1 → **APOYADA** (direccional); H4 → **APOYADA** (direccional) para sh/sx; H2/H3/H6 → **DEBILITADAS** (la dirección observada no apunta a A); H5 → **NO RESUELTA**; H7 → **NO DISCRIMINADA**; H8 → reformulación **APOYADA** en steady (no hay gating diferencial observado), gating fino sub-ms → NO RESUELTA.

---

## 2. Metodología de auditoría

- Script reescrito desde cero (`runs/etapa2/auditoria_reconstruccion.py`) que NO usa el pipeline del informe original.
- Ventana steady definida con las reglas de METRICS-DEFINITIONS: filas de telemetría `[50:-1]` con `gpu_busy≥95` y `sclk_level==7` y `mclk_level==2`, exigiendo ≥100 muestras. Igual que en el informe.
- radeontop alineado por timestamp a la ventana steady de telemetría; se computan DOS variantes reproducibles: `(a)` todas las muestras dentro de la ventana (= sin filtrar), `(b)` solo las muestras de la ventana con `gpu>=95` (= filtrado).
- UMR: conteo manual por regex de `SPI_CSQ_WF_ACTIVE_COUNT_0..7`, `RLC_GPU_CLOCK_COUNT` y `GRBM_PERFCOUNTER0_LO`.
- Integridad: conteo de faults en `journal_pres.txt`, lectura de `pre/post_flight.txt`, `metadata.txt`.

---

## 3. Verificación 1 — Potencias y ventanas steady: EXACTO

| Replica | n steady | ventana [s] | gpu avg | mem avg | temp avg | power avg [W] | power med [W] | power max [W] | Informe (avg/max) |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 1517 | 180.6 | 99.99 | 25.58 | 72.1 | **22.123** | 22.219 | 23.461 | 22.12 / 23.46 |
| A2 | 949 | 125.8 | 100.0 | 24.69 | 79.9 | **22.301** | 22.422 | 23.676 | 22.30 / 23.68 |
| A3 | 807 | 102.0 | 100.0 | 24.37 | 81.6 | **22.344** | 22.484 | 23.727 | 22.34 / 23.73 |
| B1 | 215 | 24.7 | 99.99 | 35.97 | 69.8 | **15.822** | 15.836 | 15.910 | 15.82 / 15.91 |
| B2 | 174 | 20.0 | 99.99 | 35.96 | 73.1 | **15.793** | 15.797 | 15.801 | 15.79 / 15.80 |
| B3 | 214 | 24.7 | 99.98 | 35.95 | 69.8 | **15.720** | 15.770 | 15.801 | 15.72 / 15.80 |

- Media steady: A **22.256 W** (SD 0.117; rango 22.123–22.344); B **15.778 W** (SD 0.053; rango 15.720–15.822).
- Separación mínima A−B **6.30 W**; **los rangos no se solapan** (A≥22.12 siempre > B≤15.91).
- Ratios por par: **1.398 / 1.412 / 1.421** → media **1.411**. Idénticos al informe.
- `power_full_avg`/`power_full_max` (toda la telemetría): A1 17.35, A2 15.49, A3 15.14, B1 11.15, B2 15.35, B3 13.35 — coherentes con las ventanas (A2/A3 incluyen rampa; B1/B3 incluyen init).

**Veredicto:** el resultado central (A consume ~41 % más que B, con gpu_busy≈100 % en ambos) **se reproduce íntegramente y es repetible** en los 3 pares intercalados.

---

## 4. Verificación 2 — Tabla de bloques radeontop: ERROR DE MÉTODO en el informe §4

### 4.1 Hallazgo

El informe §4 encabeza «(% busy, ventana steady, gpu≥95)». La reconstrucción **no puede reproducir esas celdas con un único método**; las celdas provienen de métodos mezclados:

- Fila **A2** del informe: `vgt 27.1 ta 70.7 sx 81.3 sh 38.2 spi 86.8 sc 86.4 pa 27.8 db 85.9 cb 65.1` → coincide con el cómputo **SIN FILTRAR** (las 126 muestras de la ventana), salvo `sh` (38.2) que coincide con el **FILTRADO** (gpu≥95).
- Fila **A3**: misma estructura, sin filtrar salvo `sh`.
- Fila **A1**: mezcla (vgt/pa sin filtrar; sx/spi/sc/db/cb filtrado; sh filtrado).
- Filas **B**: mezcla similar (ej. B ta 99.9 = filtrado ≈99.85; B3 ta 96.8 = sin filtrar ≈96.8).
- Las columnas «A avg» y «ratio A/B» del informe coinciden con el cómputo **SIN FILTRAR** (`sx 1.51` = 85.73/56.74; `ta 0.76`, `db 0.93`, `cb 0.70`), no con el filtrado (`sx 1.60`, `ta 0.81`, `db 0.99`, `cb 0.75`).

**Conclusión auditada:** como documento científico, la tabla §4 del informe NO es reproducible tal como se publica y su enunciado de método («gpu≥95») es incorrecto para la mayoría de las celdas. **Corrección objetiva requerida** (ver §9).

### 4.2 Tabla reproducible A — variante FILTRADA (gpu≥95, dentro de ventana steady)

| Bloque | A1 | A2 | A3 | **A avg** | B1 | B2 | B3 | **B avg** | ratio A/B |
|---|---|---|---|---|---|---|---|---|---|
| vgt | 31.7 | 30.9 | 30.2 | **30.9** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| ta | 80.6 | 80.9 | 81.3 | **80.9** | 99.8 | 99.8 | 99.9 | **99.8** | 0.811 |
| sx | 93.4 | 93.2 | 92.6 | **93.0** | 59.1 | 58.1 | 57.5 | **58.2** | 1.598 |
| sh | 40.8 | 38.2 | 36.9 | **38.6** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| spi | 99.6 | 99.7 | 99.6 | **99.6** | 99.8 | 99.8 | 99.9 | **99.8** | 0.998 |
| sc | 99.3 | 99.3 | 99.2 | **99.3** | 99.8 | 99.8 | 99.9 | **99.8** | 0.994 |
| pa | 32.7 | 31.7 | 31.1 | **31.9** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| db | 98.6 | 98.6 | 98.5 | **98.5** | 99.8 | 99.8 | 99.9 | **99.8** | 0.987 |
| cb | 74.0 | 74.8 | 74.9 | **74.6** | 99.8 | 99.8 | 99.9 | **99.8** | 0.747 |

(muestras gpu≥95 en ventana: A1 n=172, A2 n=104, A3 n=88, B1 n=22, B2 n=20, B3 n=23)

### 4.3 Tabla reproducible B — variante SIN FILTRAR (todas las muestras de la ventana)

| Bloque | A1 | A2 | A3 | **A avg** | B1 | B2 | B3 | **B avg** | ratio A/B |
|---|---|---|---|---|---|---|---|---|---|
| vgt | 31.0 | 27.1 | 27.9 | **28.7** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| ta | 78.6 | 70.7 | 74.5 | **74.6** | 94.9 | 99.8 | 96.8 | **97.2** | 0.767 |
| sx | 91.1 | 81.3 | 84.8 | **85.7** | 56.4 | 58.1 | 55.7 | **56.7** | 1.511 |
| sh | 39.8 | 33.5 | 33.9 | **35.7** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| spi | 97.1 | 86.8 | 91.1 | **91.7** | 94.9 | 99.8 | 96.8 | **97.2** | 0.944 |
| sc | 96.8 | 86.4 | 90.7 | **91.3** | 94.9 | 99.8 | 96.8 | **97.2** | 0.940 |
| pa | 32.0 | 27.8 | 28.7 | **29.5** | 0.0 | 0.0 | 0.0 | **0.0** | ∞ |
| db | 96.1 | 85.8 | 90.0 | **90.6** | 94.9 | 99.8 | 96.8 | **97.2** | 0.933 |
| cb | 72.1 | 65.0 | 68.4 | **68.5** | 94.9 | 99.8 | 96.8 | **97.2** | 0.705 |

(todas las muestras radeontop de la ventana: A1 n=180, A2 n=126, A3 n=102, B1 n=24, B2 n=20, B3 n=24)

### 4.4 Robustez de las conclusiones frente al método

En **ambas** variantes (y en cada uno de los 3 pares): `vgt/pa/sh = 0.0` en B vs 29–39 % en A (ratio ∞); `sx` A>B (1.51–1.60); `ta/spi/sc/db/cb` B≥A (B satura); `cb` B>A en las dos. **Las conclusiones cualitativas de la Etapa 2 no dependen del método**; solo los valores exactos varían. Regla para el informe corregido (~§9): reportar una sola variante explícita (recomendada: filtrada, coherente con la definición de ventana steady y con `gpu_busy≈100` en telemetría).

---

## 5. Verificación 3 — SPI_CSQ_WF_ACTIVE_COUNT y registro GRBM

### 5.1 Conteo corregido (error objetivo n.º 2)

Muestras UMR por corrida: A1=287, A2=354, A3=313, B1=42, B2=24, B3=31 → **1051 muestras totales**. Tamaño de lectura por muestra: 8 registros SPI + 2 RLC + 1 GRBM.

- **Lecturas SPI_CSQ_WF_ACTIVE_COUNT_0..7: 1051 × 8 = 8408** (el informe declara 3306 — incorrecto).
- **No-cero: 0** → **0.0000 %** de lecturas con valor distinto de 0 (confirmado).
- `GRBM_PERFCOUNTER0_LO`: 1051 lecturas, **0 no-cero (100 % ceros)** → baseline de no-programación OK, según afirma el informe.

### 5.2 Semántica (por qué los ceros NO son evidencia de «0 wavefronts»)

- Este registro es un **snapshot instantáneo** por cola (`wave_cnt = reg & COUNT_MASK`), no un contador acumulador. Solo cobra sentido en la cola seleccionada por el programador de GRBM (`MEID/PIPEID/QUEUEID/VMID`) que el kernel driver configura antes de leerlo (`amdgpu_gfx_select_se_sh`; path KFD `get_wave_count`).
- Leído por UMR con `-r` **sin programar el SELECT** → devuelve el estado por defecto (cola no seleccionada/no activa) → ceros esperables **aunque haya wavefronts en vuelo**.
- Además, en GFX8/SI la familia gestiona colas de cómputo (CSQ compute); cargas que usan el ring de gráficos (GL radeonsi y Vulkan RADV) no transitan necesariamente por la cola que este registro observa.
- **Conclusión:** SPI_CSQ leído en modo read-only es **informativo-por-ausencia pero no probatorio**; «8408 lecturas a 0» no puede leerse como «no hubo wavefronts», sino como «el registro no captura la actividad de estas cargas por esta vía». El informe ya lo descartaba como «no informativo» — se confirma, con la causa semántica correcta.
- Implicación para Etapa 3: leer WF reales requeriría programar previamente `GRBM_SE_SEL/ME/PIPE/QUEUE` (o usar `SPI_GFX_WF_ACTIVE` / SQ counters), lo que excede el modo autorizado.

---

## 6. Verificación 4 — Relojes (RLC, sclk, mclk) y H8

- `sclk` nivel 7 (1071 MHz) en el **100 %** de muestras steady de las 6 corridas (1517/1517, 949/949, 807/807, 215/215, 174/174, 214/214).
- `mclk` nivel 2 (1500 MHz) en el **100 %** de las mismas.
- `RLC_GPU_CLOCK_COUNT` (acumulativo 64-bit, rate = Δ/Δt): medianas A1 24.03, A2 24.77, A3 24.27, B1 23.97, B2 26.05, B3 23.87 MHz → **A ≈ B (≈24–26 MHz)**, reproducido exacto. Picos 0–200 MHz en A = artefacto de lecturas no atómicas LSB/MSB (documentado en el informe).

**Lectura auditada:** el contador RLC corre a ~25 MHz en ambas cargas (dominio de referencia RLC/SMU, NO es el reloj GFX: 1071 MHz solo se sustenta por el estado de DPM nivel 7). No se observa gating diferencial de reloj en régimen steady. Dos límites: (a) `power_dpm_force_performance_level=auto` permite transiciones por debajo del nivel máximo; a 10 Hz de telemetría no se vio ninguna muestra fuera de 7/2; (b) gating por ráfaga sub-ms no es descartable con esta resolución. → H8: **APOYADA para el régimen steady observado**; gating fino → NO RESUELTA.

---

## 7. Matriz de hipótesis (estados restringidos)

| Hip | Formulación | Evidencia auditada (reproducible) | Estado |
|---|---|---|---|
| H1 | geometría/vertex (vgt, pa) | vgt/pa ≈ 30–32 % (A) vs 0.0 (B) en 3/3 pares, ambos métodos | **APOYADA** (direccional; B=0% = bit busy nunca activo en la ventana, no «cero geometría absoluta») |
| H2 | raster/fill (sc, db, cb) | sc/db ≈ 99 % en ambos; **cb A (74) < B (100)**; el más ocupado en fill es B y gasta MENOS → el fill-busy no discrimina en favor de A | **DEBILITADA** (como motor del +41 %) |
| H3 | texturas/fetch (ta) | ta A 81 vs B 99.8 (B> A); dirección contraria a la potencia | **DEBILITADA** (no apunta a A) |
| H4 | ALU/export (sh, sx, WF) | sh 38.6 vs 0 (∞); sx 93.0 vs 58.2 (1.60); SPI_CSQ no informativo → WF no medible | **APOYADA** (direccional, sh/sx) · WF → NO RESUELTA |
| H5 | caches L1/L2 (SPM/TCC) | sin instrumentación (prohibido) | **NO RESUELTA** |
| H6 | tráfico VRAM (mem_busy, MCLK) | mem_busy B (36) > A (25); MCLK 1500 ambos → el más ocupado en memoria gasta menos | **DEBILITADA** (no es el diferenciador) |
| H7 | radeonsi vs RADV | perfiles de pipeline distintos, pero workloads difieren por construcción (no aísla driver) | **NO DISCRIMINADA** |
| H8 | clock gating diferencial | sclk/mclk 7/2 en 100 % steady × 6 corridas; RLC ≈ const. A/B; gpu_busy≈100 ambos | **APOYADA** (no gating observado en steady) · gating fino → NO RESUELTA |

**Señales que discriminan en favor de A (ambos métodos, 3/3 pares):** vgt/pa/sh = ∞, sx ≈ 1.51–1.60. **Señales que apuntan en contra del «trabajo de memoria/fill» como motor:** ta, cb, mem_busy, spi/sc/db ≥ en B.

---

## 8. Confounders y robustez del diseño

| Confounder | Evaluación auditada |
|---|---|
| Temperatura | A deriva 72→80→82 °C entre réplicas; la potencia steady A se mantiene ≈22.1–22.3 (no correlaciona con la deriva en esta escala). B1/B2/B3 a 70–73 °C. Dirigido parcialmente por el diseño intercalado A B A B A B. |
| API/driver | A=radeonsi (GL), B=RADV (Vulkan): confound no aislado (H7). |
| Duración de ventana | A ventanas 102–181 s vs B 20–24.7 s. B cumple ≥100 muestras steady (n 174–215) y ≥20 muestras radeontop (n 20–24). Aceptable pero B tiene estadística menor. |
| gpu_busy | ≈100 % en ambas: no discrimina (como el informe). |
| Relojes | Idénticos estados DPM en steady (7/2). |
| Resolución de muestreo | telemetría 10 Hz, radeontop 1 Hz, UMR ~1 Hz: no captura eventos sub-ms. |
| MRU/DRAM | no instrumentado (H5/H6 finas) — límite formal. |
| Estimador SMU `power1_input` | aproximación del firmware, no potencia física; usado igual en A y B. |

**Robustez:** 3 pares intercalados con resultados casi idénticos (SD potencias A 0.117 W, B 0.053 W; ratios 1.398/1.412/1.421) y separación mínima de 6.3 W → el efecto es grande y estable.

---

## 9. Correcciones objetivas requeridas sobre el informe

Por el mandato de no alterar resultados salvo errores objetivos, se registran AQUÍ (y se recomienda corregir el informe en su próxima edición):

1. **§4:** tabla de bloques NO reproducible con el método declarado (mezcla «sin filtrar» y «gpu≥95»). Corregir a UNA variante explícita (recomendada: filtrada, §4.2) o declarar ambas. Las cifras textuales de «ratio» (`sx 1.51`, `ta 0.76`, `db 0.93`, `cb 0.70`) corresponden a la variante NO filtrada.
2. **§5.1:** «3306 lecturas» → **8408 lecturas** (1051 muestras × 8 registros), 0 no-cero.
3. **§5.2 / §6:** matizar que RLC (~24–26 MHz) es dominio RLC/SMU de referencia y NO establece por sí solo el reloj GFX; el reloj GFX se sustenta por `sclk` nivel 7 (1071 MHz) / `mclk` nivel 2 (1500 MHz) en el 100 % de muestras steady.
4. **§6 H8 / tabla de estados:** alinear estados a `APOYADA/DEBILITADA/NO RESUELTA/NO DISCRIMINADA` (evitar «PARCIAL»/«INCONCLUSO»). Ver §7.

Ninguna de estas correcciones modifica las conclusiones centrales (potencia 1.41, direcciones vgt/pa/sh/sx).

---

## 10. Criterio de éxito y estado

- Potencia: reproducida exacta; 3/3 pares con señales direccionales limpias (vgt/pa/sh ∞, sx 1.51–1.60), rangos no solapados → criterio §12 del plan **CUMPLIDO**.
- Sin tocar configuración y sin programar contadores: verificado en artefactos (SPI y GRBM todos ceros; DPM auto; power1_cap 35 W; 0 faults) → **CUMPLIDO**.
- Auditoría de escritura (§14 del plan): cumplida (solo lecturas; el propio `auditoria_reconstruccion.py` es read-only).
- Quedan abiertas y justificarían Etapa 3 (solo con autorización): cuantificar WF reales (SPI_GFX/SQ con SELECT), texels y caches (TCC/TCP/SPM/RLC ring), ciclos por bloque (SQ_PERFCOUNTER/CB/DB con SELECT+CNTL); aclarar H5 y cerrar H4-WF. Recomendación: **no pronuncie causalidad**; la hipótesis más respaldada para el +41 % es mayor actividad de pipeline geometría + shader/export (VGT/PA/SH/SX) con el reloj máximo idéntico y memoria y fill más ociosos en A.

---

## 11. Estado del documento y artefactos

- Documento de auditoría generado **sin modificar** el informe original ni MASTER salvo lo requerido en §9.
- Artefactos verificados: `runs/etapa2/{A1,A2,A3,B1,B2,B3}/{telemetria.csv, radeontop.csv, umr_samples.csv, pre_flight, post_flight, metadata, journal_pres.txt}`.
- Script de reconstrucción: `runs/etapa2/auditoria_reconstruccion.py` (read-only). Salida: `runs/etapa2/audit_reconstruccion.json`.
- MASTER-RESEARCH-STATUS.md se actualizará a v1.4 registrando esta auditoría y sus errores objetivos.