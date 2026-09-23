# R-2.1 — Inventario de Experimentos Históricos (E0–E5)

> **Archivo:** `R2-HISTORICAL-EXPERIMENT-INVENTORY.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (read-only; sin ejecución)
> **Clasificación:** [VERIFICADO] — existencia/fuente de cada experimento confirmada por inspección directa del árbol de archivos (backup y repo activo); ningún resultado fue re-ejecutado ni reconstruido.

---

## 0. Objetivo y método

Registrar **qué experimentos históricos existen**, **qué artefactos los prueban**, **dónde están** y
**qué decían**, de forma que ningún investigador futuro dependa del historial de conversaciones.

Regla de oro aplicada: si un experimento **no se encontró como artefacto**, se registra como
**NOT FOUND** indicando **dónde se buscó**. No se reconstruye ningún resultado ni se inventa ninguno.

Método: inspección directa (lista de directorios, manifiestos, reportes `.md` de cabecera) de:
`/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/` (backup Torneo) y
`/home/lucas/Escritorio/RX550_Iterative_Research/` (repo iterativo) + `experiments/WORKLOAD-SINTETICO/`.

---

## 1. Advertencia de nomenclatura: DOS familias "E" distintas

En este proyecto la letra **E** aparece en **dos líneas históricas independientes** que **NO se deben
mezclar** (las declaraciones de estado las tratan como venían del conocimiento histórico):

### Familia 1 — Serie "régimen E" (sesión 17/09/2026, backup Torneo)
Experimentos **titulados E1…E5b** en el backup `RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/`,
producidos en la sesión histórica del 17/09 con glmark2/vkmark sobre RX 550 (Mesa 26.2.2 STOCK/CUSTOM),
cap 25 W. A esta serie pertenece el **"régimen E1/E3/E5"** no reproducible al que MASTER-RESEARCH-STATUS
se refiere (phong 1285 fps / desktop 443@1080 / jelly 691@35W, SCLK 350-390, MCLK 1250-1500, 74-92 °C).
Representan la **base de datos histórica mayormente NO REPRODUCIBLE**.

### Familia 2 — Workload Sintético (repo iterativo, 19-20/09/2026)
Experimentos **E-01 / E-02 / E-03** (README.md + `runs/exploratorio-01|02|03-corrected/`) y los ejes de
**ES-01** (`runs/escalado-01/`, ejes A0..D2, E1, F2) del proyecto `experiments/WORKLOAD-SINTETICO/`.
Esta familia es **REPRODUCIBLE** (workload Vulkan autónomo, telemetría sysfs).

> **Convención para todo el resto de R-2:** cuando se hable de "E1/E3/E5" se refiere a la Familia 1
> (histórica, mayormente NO REPRODUCIBLE); cuando se hable de "E-01/E-02/E-03/ES-01" se refiere a la
> Familia 2 (reproducible). Nunca se mezclan métricas entre familias.

---

## 2. Inventario Familia 1 — Título individual por experimento

### E0 — Escalado por resolución (PRE-E1) — **NOT FOUND como artefacto**

- **Estado: NOT FOUND** como experimento nombrado "E0". No existe ningún directorio ni reporte llamado
  `E0*` en el backup ni en el repo.
- **Dónde se buscó:**
  - `find` sobre `/home/lucas/RX550_Modo_Torneo_Backup_2026-09-19_0836/experiments/` y subdirectorios
    con patrón `*E0*` / `*e0*` → sin coincidencias.
  - Grep por tokens `E0` en todos los `.md`/`.txt` del backup → solo 2 referencias textuales (ver abajo).
- **Evidencia textual de su existencia (2 referencias):**
  1. `mesa-e1-20260917-170430/manifest.txt` (línea 9): *"Power cap: NO MODIFICADO (power1_cap=25W como
     en E0)"*.
  2. `mesa-e1-20260917-170430/E1-report.md` (línea 53): *"fill/ROP en resoluciones altas: PROBABLE
     (E0: 1080->480 x7.4; FPS bajan con resolución aunque busy=100%)"*.
- **Interpretación registrada (inferida de las referencias, NO reconstruida):** E0 = experimento previo
  a E1 de **escalado por resolución** (1080 → 768 → 480) **sin modificar el cap** (25 W), con burn en
  resoluciones altas y FPS inversamente proporcionales a la resolución con GPU busy ≈ 100 %.
- **Candidato a contener los datos crudos de E0 (SIN confirmar):**
  - `mesa-resolution-20260917-113618/` (STOCK/CUSTOM × 1080/768/480, CSVs `res-*.csv`, `gpu` telemetría)
  - `mesa-resolution-20260917-135118/` (ídem, más reps).
  - Ambos **no se titulan "E0"**: son la única operación de barrido por resolución del 17/09 previa a E1.
  → **Registro descriptivo:** "E0 — resolución — NOT FOUND con nombre E0; datos plausibles en
  `mesa-resolution-2026…113618/135118/` sin etiquetar."

### E1 — Descomposición del workload GPU (17/09/2026) — **EXISTE**

- **Artefacto:** `mesa-e1-20260917-170430/` (manifest.txt + `E1-report.md`).
- **Objetivo:** descomponer el workload GPU por categoría (shader/ALU, textura/mem, fill/pixel,
  geometría, buffer/upload, Vulkan) con Mesa 26.2.2 STOCK/CUSTOM a 640x480, sysfs 4 Hz, cap 25 W.
- **Resultados registrados (históricos):** tabla por test (FPS/busy/power/sclk/VRAM/GTT); todos cercanos
  a 24.9–25.1 W con SCLK 330–450; CPU section (perf stat :u).
- **Estatus en MASTER-RESEARCH-STATUS:** "régimen E1" forma parte del régimen 17/09
  **[NO REPRODUCIBLE]** (no se reproduce el desbloqueo de potencia).
- **AUDITADO:** EP-08 (`fase-b-cap-probe…/EP08-auditoria-telemetria-E1E3.md`) confirmó que la telemetría
  de E1/E3 midió la RX 550 real (amdgpu card1), no la iGPU → **REFUTADA** la idea de que E1/E3 midieron
  iGPU (ERRAATUM 005).

### E2 — Workload representativo / fill-rate, upload/PCIe y presentación (17/09/2026) — **EXISTE**

- **Artefactos:** `mesa-e2-20260917-175132/` (datos crudos) + `mesa-e2-20260917-175301/`
  (`E2-report.md`, `e2_summary.tsv`, `manifest.txt`).
- **Objetivo:** fill-rate/ROPs (parte A, escalado por resolución), categorías a 1080 (B), buffer map
  /upload/PCIe (C), presentación (D), STOCK vs CUSTOM (E). "Fallback riguroso" sin juego real: no existía
  workload real reproducible local (juegos online = login; KOF XV = menú sin xdotool/wtype).
- **Resultados registrados:** parte A — resolución 640→1080 factor 4.7–7.6× en FPS vs 9× píxeles
  (escalado no lineal, súper-lineal en 720→1080); busy 100 %, SCLK 328-378, pwr 24.94–25.07 W.
- **Estatus:** histórico **NO REPRODUCIBLE** como régimen de potencia (aunque los valores absolutos de
  cada celda son medidos y registrables).

### E3 — GPU-side Bottleneck Investigation (matriz diferencial) (17/09/2026) — **EXISTE**

- **Artefacto:** `mesa-e3-20260917-213646/` → `GPU-BOTTLENECK-report.md`, `e3_summary.tsv`, subcarpetas
  `e4/`, `e5/`, `e5b/`, `m1/raw/`.
- **Objetivo:** identificar el cuello de botella de lado GPU con matriz diferencial (sin contadores HW:
  no existía PMU amdgpu en perf ni UMR/radeontop accesibles).
- **Resultados registrados (resumen ejecutivo):**
  - La GPU queda **exactamente en el cap de 25 W** (24.88–25.09 W) con SCLK atrapado 330–535 de 1071
    posibles; el limitador proximal es **el presupuesto de potencia**, no térmico.
  - ALU **no importa** (−3…−27 % con 16× pasos), bytes/píxel **no importan**, operaciones por
    muestra/píxel **sí** (MSAA 4× −18…−70 %), geometría importa, escalado ~1/píxeles con cliff 720→1080.
  - Conclusión: **limitado por potencia → SCLK bajo → la unidad por-píxel (ROP/DB) + transacciones L2 del
    framebuffer/profundidad** como cuello más probable; geometría secundaria. Confianza: PROBABLE para
    "no-ALU / no-bandwidth", POSIBLE para "ROP/DB concreto".
- **Contenido `m1/raw/`:** estudio de régimen (marker 1) de la propia sesión — **NO confundir** con el
  experimento **M1 autorizado** de 2026-09-20 (`experiments/M1-cap-35-30/`, vkmark 35/30 W,
  112/112 checks). El `m1/` del backup es anterior y distinto.

### E4 — Separar POWER-LIMIT de UNIT-LIMIT (17/09/2026) — **EXISTE**

- **Artefacto:** `mesa-e3-20260917-213646/e4/` (`E4-report.md`, `e4_summary.tsv`, tele-*, state_initial.txt).
- **Objetivo:** experimento decisivo separando límite de potencia de límite por unidad; método: solo
  `power_dpm_force_performance_level=high` con **cap intacto en 25 W**, N=3/celda, 54 runs válidos,
  cambios sysfs temporales restaurados.
- **Resultados registrados:** forzar DPM `high` a 25 W **reduce** el rendimiento (−41 % a −58 % según
  carga) con SCLK bajando (−23…−29 %) y MCLK subiendo a 1500 → **el cap de potencia domina; forzar
  frecuencias deseadas sin presupuesto de potencia degrada.**

### E5 — GPU bottleneck tras retirar el cap (17/09/2026) — **EXISTE**

- **Artefacto:** `mesa-e3-20260917-213646/e5/` (`E5-report.md`, `e5_summary.tsv`, `state_initial.txt`,
  `e5_phase.log`, 81 runs válidos).
- **Objetivo:** qué cambia al liberar el cap a 35 W (mismas celdas diferenciales).
- **Resultados registrados (ejecutivo):**
  - Liberar a 35 W sube el rendimiento ×2–4 pero aparece **techo térmico** 88–92 °C, potencia 28–31 W,
    SCLK ~600-750 (no 1071, que eran transitorios).
  - **Las penalizaciones relativas por categoría son casi idénticas a 25 y 35 W (±8 %)** → "la
    potencia/frecuencia es un volumen que escala todo; NO emerge una unidad nueva a 35 W".
  - Costes dominantes estables: MSAA/raster 3.13×, geometría 2.35×, textura multi-tap 2.33×, HiZ 1.32×,
    DCC/color 1.31×, ALU 1.25×.
  - DRAM descartada (mem_busy 20-30 %), ALU descartada, filtrado descartado.

### E5b — SCLK-control + control térmico (diferenciales a reloj fijo) (17/09/2026) — **EXISTE**

- **Artefacto:** `mesa-e3-20260917-213646/e5b/` (`E5b-report.md`, `e5b_summary.tsv`, val-*, state_final.txt,
  108 runs válidos + 3 validaciones).
- **Objetivo:** desacoplar SCLK del cap para aislar el coste funcional puro
  (`power_dpm_force_performance_level=manual` + `pp_dpm_sclk`).
- **Resultados registrados (ejecutivo):**
  - Nivel 1 (551 MHz) NO se sostiene a 25 W (cae a ~338), sí a 35 W. Nivel 0 (214 MHz) se sostiene en
    ambos. SCLK común válido 25/35 W = 214 MHz.
  - **Hallazgo central (criterio CUMPLIDO): a igual SCLK=214 MHz, cap 25 vs 35 W dan penalizaciones
    idénticas (±1-2 %)** → "**el cap por sí solo NO altera el coste funcional**".
  - La magnitud de las penalizaciones **depende del SCLK** (crecen hacia los valores de E5 a 551 MHz),
    consistente con la relación SCLK:MCLK (a reloj bajo el MCLK relativamente más rápido enmascara los
    costes sensibles a memoria/compresión).
  - ALU robustamente descartada (1.04–1.14 en todos los relojes). Térmico controlado a reloj fijo bajo
    (66–70 °C).
  - **No se demuestra ineficiencia específica de Mesa** → no se justifica parche; se aporta mapa de rutas
    candidatas (§8 del reporte).

---

## 3. Inventario Familia 2 — WORKLOAD-SINTETICO (reproducible)

| ID | Ruta | Contenido | Estado |
|---|---|---|---|
| **E-01** | `experiments/WORKLOAD-SINTETICO/runs/exploratorio-01/` | Corrida exploratoria compilación/validación del workload Vulkan | **EXISTE** (reproducible como artefacto de corrida) |
| **E-02** | `experiments/WORKLOAD-SINTETICO/runs/exploratorio-02/` | Corrida exploratoria 2 (parámetros/telemetría) | **EXISTE** |
| **E-03** | `experiments/WORKLOAD-SINTETICO/runs/exploratorio-03-corrected/` | **E-03 corregida (Diseño B)**: 13.4 W full / 15.75 W steady; MCLK 1500 activo; 0 faults — [VERIFICADO] en MASTER-RESEARCH-STATUS | **EXISTE [VERIFICADO]** |
| **ES-01** | `experiments/WORKLOAD-SINTETICO/runs/escalado-01/` | Barrido de ejes A-D + E: A/B/C/D/E = SIN EFECTO en potencia; auto-pacing fetch-bound | **EXISTE [VERIFICADO]** |
| **F2** | `experiments/WORKLOAD-SINTETICO/runs/escalado-01/F2-*/` | 8 fetches = 2× frametime (112→222 ms), potencia INVARIANTE (15.76 vs 16.13 W) | **EXISTE [VERIFICADO]** |

> Referencia del estado VERIFICADO: MASTER-RESEARCH-STATUS.md (2026-09-22, filas E-03 / ES-01 / F2).

---

## 4. Otros experimentos históricos del backup (contexto, NO "E")

Existen artefactos adicionales del 17-18/09 que **no son** de la serie E pero se citan para el mapa
documental completo:

| Artefacto | Ruta (backup) | Contenido |
|---|---|---|
| Mesa A/B temprano | `mesa-ab-results-20260917-101506/`, `mesa-ab-results-20260917-103427/` | Primeras corridas STOCK vs CUSTOM (antes de E-series) |
| Profiling CPU | `mesa-p1-20260917-205256/`, `mesa-p2-20260917-211312/` | `PROFILING-CPU-report.md` (p2) |
| Power sweep | `rx550-power-sweep-20260918-132309/`, `rx550-power-sweep-20260918-140527/` | Barrido de potencia 18/09 (contexto del estado regulatorio y de la invalidación de "power1_input = real") |

Estos NO responden a la solicitud explícita E0–E5; se listan solo para no perder trazabilidad.

---

## 5. Registro de búsqueda (dónde se buscó E0-E5)

| Término | Dónde se buscó | Resultado |
|---|---|---|
| `E0` (nombre como artefacto) | Backup `experiments/` + repo activo + WORKLOAD-SINTETICO | **NOT FOUND** (solo 2 refs textuales; candidatos sin etiquetar) |
| `E1` | Backup `experiments/mesa-e1-20260917-170430/` | **FOUND** (`E1-report.md`, `manifest.txt`) |
| `E2` | Backup `experiments/mesa-e2-20260917-175132/` y `...175301/` | **FOUND** (`E2-report.md`, `e2_summary.tsv`) |
| `E3` | Backup `experiments/mesa-e3-20260917-213646/` | **FOUND** (`GPU-BOTTLENECK-report.md`) |
| `E4` | Backup `mesa-e3-…/e4/` | **FOUND** (`E4-report.md`) |
| `E5` | Backup `mesa-e3-…/e5/` | **FOUND** (`E5-report.md`) |
| `E5b` | Backup `mesa-e3-…/e5b/` | **FOUND** (`E5b-report.md`) |
| `E-01/E-02/E-03/ES-01` | Repo `experiments/WORKLOAD-SINTETICO/runs/` | **FOUND** |

> Nota: las rutas **absolutas** de lo encontrado en el backup están completas en los §2/§4; las rutas de
> la Familia 2 son relativas al repo activo.

---

## 6. Conclusión del inventario

1. **E1, E2, E3, E4, E5, E5b EXISTEN** como artefactos con reporte en el backup (Familia 1), con
   resultados **registrados** pero régimen de potencia global **NO REPRODUCIBLE**.
2. **E0 NO EXISTE como artefacto** (solo referencias textuales); sus datos plausibles están en
   `mesa-resolution-20260917-113618|135118/` **sin etiquetar** como E0.
3. **E-01/E-02/E-03/ES-01/F2 (Familia 2) EXISTEN y son VERIFICADOS** en el repo activo.
4. Ningún resultado de los históricos fue re-ejecutado ni reconstruido en esta fase (read-only).