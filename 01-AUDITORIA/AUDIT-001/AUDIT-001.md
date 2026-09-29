# AUDIT-001.md — Auditoría Histórica Completa

**Fecha:** 2026-09-21
**Versión:** 1.0
**Alcance:** Auditoría sistemática de todos los experimentos históricos del proyecto RX 550 Iterative Research
**Metodología:** Revisión de evidencia documental, cruce de fuentes, clasificación por evidencia (VERIFICADO/REPRODUCIBLE/OBSERVADO/NO REPRODUCIBLE/HIPÓTESIS/DESCARTADO/INVALIDADO/DESCONOCIDO)

> **Reconciliación terminológica 2026-09-24:** las cifras procedentes de
> `power1_input` se escriben como `W_SMU`/potencia estimada por sensor SMU. No existe
> vatímetro independiente; las asociaciones de workload son correlacionales.

---

## 1. Resumen Ejecutivo

Esta auditoría revisa **14 experimentos/corridas históricas** (E1, E3, E5, Fase A, Fase B, EP-05, EP-06, EP-08, M1, Superposition, GravityMark, E-03 corregida, ES-01, F2) y **4 informes de investigación** (R-01 a R-13, ES-01) para corregir el registro histórico antes de nuevos experimentos.

**Hallazgos críticos:**
1. **El régimen histórico E1/E3/E5 (25W / 350-390 MHz / MCLK 1250-1500 / 74-92°C) NO es reproducible** bajo parámetros autorizados actuales. Ocurrió SIN Kalm activo (17/09) y no se ha reproducido ni con cap 25W + soak térmico hasta 71°C, ni con Mesa CUSTOM, ni con escenas pesadas.
2. **Kalm NO fue causa** del régimen 25W; ocurrió cuando Kalm estaba **inactivo** (17/09). Con Kalm activo (18-19/09), la GPU opera en régimen libre (1071 MHz).
3. **power1_input ≠ potencia real:** Es estimador SMU. En E1/E3 reportaba el target de regulación (≈cap). `W_SMU` máximo observado: **13.6 W** (EP-06) y **23.7 W pico** (Superposition).
4. **Mesa CUSTOM NO reproduce E5:** EP-05 A/B controlado muestra CUSTOM = STOCK para 3 escenas; no reproduce el régimen E5.
5. **E1/E3 NO midieron la iGPU:** La telemetría proviene de la RX 550 real (amdgpu card1, mem_info_* existe solo allí).
5. **Cuello de botella actual:** la evidencia sintética es consistente con **fetch-latency bound**
   (auto-pacing); no es una causalidad de potencia física demostrada. Superposition muestra una
   asociación diferente, no una causa aislada.

**Correcciones registradas:** 5 Errata en `ERRATA.md` (Kalm, power1_input, Mesa CUSTOM, métricas sin etiquetar, iGPU).

---

## 2. Cronología de Experimentos Históricos

| Fecha | Experimento | Parámetros Clave | Resultado Clave | Clasificación |
|---|---|---|---|---|
| 17/09 | E1 (vk-phong 640p) | cap 25W, cold start | 25W / 350-390 MHz / 1285 FPS | **NO REPRODUCIBLE** |
| 17/09 | E3 (vk-phong 1080p) | cap 25W, caliente | 25W / 350-390 MHz / 443 FPS | **NO REPRODUCIBLE** |
| 17/09 | E5 (línea completa) | cap 25W, Mesa CUSTOM | 25-31W / 600-750 MHz / 74-92°C | **NO REPRODUCIBLE** |
| 18/09 | Fase A (sweep) | cap 25→35W, cold | Curva plana, SCLK 1071 | **VERIFICADO** |
| 19/09 | Fase B (cap probe) | cap 25W vs 35W | Cap 25W no liga SCLK | **VERIFICADO** |
| 19/09 | EP-06 (soak + réplica) | cap 25W, caliente 71°C | No reproduce E1/E3; máx 13.6W | **VERIFICADO** |
| 19/09 | EP-05 (Mesa A/B) | CUSTOM vs STOCK | Indistinguibles; no reproduce E5 | **VERIFICADO** (3 escenas) |
| 20/09 | M1 (vkmark 35/30W) | 10 runs pareados | 12.27W @35W → NO DISCRIMINATIVO | **VERIFICADO** |
| 20/09 | Superposition | motor directo, 1600x900 | 18.8W avg / 23.7W max | **OBSERVADO** |
| 20/09 | GravityMark 200k | 1080p Vulkan | 12.4W avg / 14.8W max | **OBSERVADO** |
| 21/09 | E-03 corr (Diseño B) | 1920x1080, 4 capas | 13.4W full / 15.75W steady | **VERIFICADO** |
| 21/09 | ES-01 (escalado) | A/B/C/D/E screening | SIN EFECTO potencia | **VERIFICADO** |
| 21/09 | F2 (8 fetches) | 2× fetches vs E1 | 2× frametime, power invariante | **VERIFICADO** |

---

## 3. Hallazgos por Tema

### 3.1 Kalm y el Régimen Histórico (17/09)

**Evidencia documental:**
- Journal 17/09: `kalm-gpu.service` **inactivo** (murió TERM 18/09 14:34). Cero eventos kalm el 17/09.
- Journal 18-19/09: `kalm real` (`kalmd.py` PID 4087, `kalm-lite.py` PID 4086) **activo**. `kalm-gpu.service` muerto.
- Con Kalm activo (18-19/09): Régimen **libre** 1071 MHz / ~10 W.
- Sin Kalm (17/09): Régimen **regulatorio** power1≈cap 25W / SCLK 350-390 MHz.

**Conclusión:** Kalm **NO fue causa** del régimen 25W/360MHz; ocurrió cuando Kalm estaba **inactivo**. El régimen "regulatorio" (power1≈cap) ocurrió SIN kalm; el régimen "libre" (1071 MHz) ocurrió CON kalm activo.

**Clasificación:** "Kalm limitó a 25W" = **INVALIDADO** (ERRATUM-001)

---

### 3.2 Power1_input y Potencia Real

**Evidencia:**
- Kernel docs: `power1_input`/`power1_average` = estimador SMU en µW (no vatímetro físico).
- E1/E3/E5: `power1_input ≈ power1_cap` (25W) → estimador reportaba **target de regulación**, no `W_SMU` physical.
- EP-06: `W_SMU` máximo observado = **13.6 W** (2560×1440 texturizado, cap 35W).
- Superposition: **18.8 W media / 23.7 W pico** `W_SMU` en fase activa.
- M1: `power1_input @35W` = 12.27 W media.

**Conclusión:** `power1_input` es **estimador SMU en estado [regulatorio/libre]**, no
`W_SMU` física independiente. En estado regulatorio reportaba el target (≈cap); en estado
libre observamos ~10–16 W.

**Clasificación:** "power1_input = potencia real" = **INVALIDADO** (ERRATUM-002)

---

### 3.3 Mesa CUSTOM y Régimen E5

**Evidencia (EP-05, 19/09):**
- A/B controlado intercalado CUSTOM vs STOCK, N=2/escena, arranque frío (42°C).
- Escenas: A desktop, B jellyfish, C shading (1080p, 15s).
- **CUSTOM vs STOCK indistinguibles:** ΔFPS ≤1%, ΔP ≤0.3 W, mismo SCLK/MCLK.
- **Ningún brazo reprodujo régimen E5** (25-31 W, MCLK ≥1250, 74-92°C).
- Maps verificaron carga: CUSTOM → `/opt/mesa-.../libgallium-26.2.2.so`, STOCK → `/usr/lib64/...`.

**Conclusión:** Mesa CUSTOM **NO reproduce E5** en arranque frío. H8 (Mesa CUSTOM = causa E5) = **NO CONFIRMADA**.

**Matiz crítico:** La indistinguibilidad es **solo para 3 escenas probadas** (A/B/C, 1080p, 15s, arranque frío). NO se generaliza a toda la RX 550.

**Clasificación:** "Mesa CUSTOM causó E5" = **INVALIDADO** (ERRATUM-003)

---

### 3.4 E1/E3: iGPU vs RX 550

**Evidencia (EP-08):**
- Header E1: `ts,busy,freq_hz,power_uw,temp_mc,vram_used,gtt_used`
- `mem_info_vram_used` y `mem_info_gtt_used` existen **SOLO** en amdgpu card1. En card0 (i915) NO existen.
- Telemetría E1/E3 (freq 298-1029MHz, power ~25W, temp 75-79°C, vram/gtt) → **RX 550 real (amdgpu card1)**.

**Conclusión:** O1-b ("E1/E3 midieron iGPU") = **REFUTADA** (ERRATUM-005)

---

### 3.4 Métricas de Potencia Sin Etiquetar

**Problema:** Múltiples informes compararon `power_avg_full` (ventana completa) con `power_avg_steady` (régimen estable) como si fueran iguales.

**Ejemplo:** E-03 original: "13.40 W avg / 15.81 W max" (ventana completa) vs régimen estable: "15.75 W avg / 15.80 W max". Comparados sin etiquetar.

**Corrección:** Ver `METRICS-DEFINITIONS.md` para definiciones formales. Todas las comparaciones históricas que mezclen definiciones deben etiquetarse `NOT DIRECTLY COMPARABLE`.

**Clasificación:** Error metodológico = **INVALIDADO** (ERRATUM-004)

---

### 3.5 Cuellos de Botella: Auto-Pacing Fetch-Bound

**Evidencia transversal (ES-01 + F2):**

| Workload | Fetches/frag | FPS | Frametime | Power Steady | mem_busy steady |
|---|---|---|---|---|---|
| E-03 base (E1) | 4 | 8.95 | 112 ms | 15.75 W | 36% |
| A (layers 8) | 4 | 4.50 | 223 ms | 15.76 W | 36% |
| A (layers 16) | 4 | 2.30 | 442 ms | 15.78 W | 36% |
| B (FMA 96) | 4 | 8.95 | 112 ms | 16.18 W | 36% |
| C (tex 8192) | 4 | 8.95 | 112 ms | 16.09 W | 36% |
| D (MSAA 8x) | 4 | 8.90 | 112.5 ms | 16.11 W | 36% |
| **F2 (8 fetches)** | **8** | **4.55** | **222 ms** | **15.76 W** | **36%** |

**Patrón descubierto:**
- **Frametime escala linealmente con fetches por fragmento** (4 → 8 fetches = 2× frametime).
- **Potencia y mem_busy INVARIANTES** (~16 W, 36%) → **Auto-pacing**: más trabajo/frame → menos fps → misma tasa de fetches/seg → misma potencia.
- ALU (FMA) y CB (MSAA) **no son cuellos**; el límite es **latencia de fetch** (miss L1/L2 → DRAM ~350 ciclos).

**Conclusión:** GPU se autolimita al equilibrio de reloj (SCLK 1071 + MCLK 1500 fijos). Clock-gating de unidades ociosas anula efecto de más trabajo/frame.

---

## 4. Verificación Mesa/ICD por Experimento

| Experimento | Mesa | ICD Vulkan | Renderer GL | Verificación |
|---|---|---|---|---|
| E1/E3/E5 (17/09) | **SYSTEM MESA** | System radeon_icd | radeonsi | EP-05 maps no apuntan a `/opt/` ese día |
| Fase A/B | **SYSTEM MESA** | System radeon_icd | radeonsi | EP-06 usa stock |
| EP-05 CUSTOM | **CUSTOM MESA** (`/opt/mesa-26.2.2-rx550-haswell`) | `/opt/.../radeon_icd` | radeonsi (git-3281a69a8b) | Maps: `/opt/.../libgallium-26.2.2.so` |
| EP-05 STOCK | **SYSTEM MESA** | System radeon_icd | radeonsi (26.2.2) | Maps: `/usr/lib64/libgallium-26.2.2.so` |
| M1 | **SYSTEM MESA** | System radeon_icd | radeonsi | Maps + glxinfo verificados |
| Superposition | **SYSTEM MESA*** | System radeon_icd | radeonsi | `DRI_PRIME=1002:699f` + binary directo |
| GravityMark | **SYSTEM MESA*** | System radeon_icd | — (Vulkan) | `VK_ICD_FILENAMES=system` + `MESA_VK_DEVICE_SELECT` |
| E-03 corr / ES-01 / F2 | **SYSTEM MESA** | System radeon_icd | — (Vulkan) | Binario `main-graphics` compila contra system |

*\* Clasificación: **PROBABLE SYSTEM MESA** (OBSERVADO, no VERIFICADO) — ausencia de env CUSTOM y uso de ICD system, pero sin `/proc/maps` capturado.*

**Nota crítica:** La existencia de `/opt/mesa-26.2.2-rx550-haswell` **NO implica** que fue usado. La evidencia debe demostrar qué bibliotecas cargó el proceso (`/proc/<pid>/maps`, `glxinfo`, `vulkaninfo`).

---

## 5. DPM y Comportamiento de Clocks

| Experimento | SCLK Régimen | MCLK Régimen | power1_cap | power_avg_full | power_avg_steady |
|---|---|---|---|---|---|
| E1/E3/E5 (17/09) | 350-390 MHz | 1250-1500 MHz | 25W | ~25 W | N/A |
| Fase B cap25 | **1071 MHz** | 625 (+picos 1500) | 25W | ~10-11 W | N/A |
| EP-06 soak | 1071 MHz | 625 (+picos 1500) | 35W | 10-13 W | N/A |
| EP-05 CUSTOM | 1071 MHz | 625 (+1500*) | 35W | 9.4-12.2 W | N/A |
| M1 | 1071 MHz | 625 | 35W/30W | 12.27 W | N/A |
| Superposition | 1071 + bajos | 300-1500 | 35W | 13.8 W | **18.8 W** |
| E-03 corr | 1071 MHz | **1500 MHz** | 35W | **13.4 W** | **15.75 W** |
| ES-01 base | 1071 MHz | 1500 MHz | 35W | 13.4 W | 15.75 W |
| F2 | 1071 MHz | 1500 MHz | 35W | 15.76 W | 15.76 W |

**Clave:** Solo E-03, ES-01, F2 y Superposition (fase activa) tienen **MCLK 1500 sostenido** y reportan `power_avg_steady` ≥ 15 W.

---

## 6. Gaps Críticos Identificados (DESCONOCIDO)

| Gap | Descripción | Prioridad |
|---|---|---|
| **Causa raíz régimen 17/09** | Qué disparó SCLK 350 / MCLK 1250 / 25W en sesión 17/09 | **ALTA** |
| **MCLK sostenido** | Qué dispara MCLK 1250-1500 sostenido (hoy solo 625 + picos) | **ALTA** |
| **Draw real máximo** | Límite térmico/eléctrico real (>13.6 W medidos) | **ALTA** |
| **Costo real DRAM** | `mem_busy` ≠ % bandwidth; necesidad contadores HW | **ALTA** |
| **Bottleneck GL 640p** | CPU submissions vs present vs VRAM/GTT | **MEDIA** |
| **DCC behavior real** | ¿Superposition usa DCC? ¿Nuestro CB lo deshabilita? | **MEDIA** |
| **PowerPlay internals** | ppfeaturemask, DPM niveles intermedios, voltage behavior | **MEDIA** |
| **Origen "phong 1285 fps"** | ¿Era otra ventana/superficie? | **BAJA** |
| **PCIe x8 vs x4** | Link width/speed negociado real | **BAJA** |
| **BIOS/fuses CUs** | Unidades deshabilitadas: fuse/BIOS/físico | **BAJA** |

---

## 7. Archivos Generados

| Archivo | Descripción |
|---|---|
| `AUDIT-001.md` | Este informe principal |
| `ERRATA.md` | 5 correcciones formales al registro histórico |
| `METRICS-DEFINITIONS.md` | Definiciones formales inmutables de métricas de potencia |
| `EVIDENCE-MATRIX.md` | Matriz evidencia × conclusión × clasificación (14 experimentos) |

---

## 8. Actualización MASTER-RESEARCH-STATUS

Al cierre de FASE A, actualizar `MASTER-RESEARCH-STATUS.md` con:

**VERIFICADO:**
- Cap 25W no liga SCLK (Fase B, EP-06)
- Régimen E1/E3/E5 no reproducible (Fase B, EP-06)
- Kalm no causa 25W (EP-06, journal)
- Mesa CUSTOM no reproduce E5 (EP-05 A/B)
- E1/E3 midieron RX 550 real (EP-08)
- E-03 corregida: 13.4W full / 15.75W steady, MCLK 1500 activo
- ES-01: A/B/C/D/E = SIN EFECTO potencia, auto-pacing fetch-bound
- F2: 2× fetches = 2× frametime, power invariante

**INVALIDADO (con ERRATUM):**
- Kalm limitó a 25W
- Cap 25W liga SCLK
- 25W = techo natural GPU
- power1_input = potencia real
- Mesa CUSTOM causó E5
- E1/E3 midieron iGPU
- Comparaciones de métricas sin etiquetar

**NO REPRODUCIBLE:**
- Régimen E1/E3/E5 completo (17/09)

**OBSERVADO:**
- Superposition 18.8W avg / 23.7W max
- GravityMark 12.4W avg / 14.8W max
- MCLK 1500 sostenido solo en E-03, ES-01, F2, Superposition

**DESCONOCIDO (Gaps):**
- Causa raíz régimen 17/09
- MCLK sostenido 1250-1500
- Draw real máximo >13.6W
- Costo real DRAM / mem_busy meaning
- Origen "phong 1285 fps"

**CONGELADO (no tocar):**
- WORKLOAD-SINTETICO (código, shaders, Makefile, Mesa config, Kalm, kernel, GRUB)
- BIOS, ppfeaturemask, Kalm writes, Mesa system, GRUB/kernel

**EXPERIMENTOS AUTORIZADOS:**
- FASE B → POLARIS12-MAP (investigación read-only)
- FASE C → Superposition dissection (con herramientas no invasivas)
- FASE D → Performance counters (prueba lectura read-only)

---

## 9. Próximos Pasos (FASE B+)

1. **FASE B** — Crear `02-ARQUITECTURA/POLARIS12-MAP/` con subsistemas A–AJ
2. **FASE C** — `R-14-SUPERPOSITION-DISSECTION.md` con herramientas no invasivas
3. **FASE D** — Performance counters: prueba lectura read-only (UMR → GPUPerfAPI → radeontop → debugfs/perf)
4. **FASE E** — Real-game baseline (seleccionar candidato reproducible)
5. **FASE F–J** — Documentación e investigación (GEO, Memory, RADV, PowerPlay, Priority Matrix)

**Regla:** No implementar experimentos GEO, memoria, RADV, PowerPlay hasta documentar y seleccionar mayor valor informativo. WORKLOAD-SINTETICO permanece CONGELADO.
