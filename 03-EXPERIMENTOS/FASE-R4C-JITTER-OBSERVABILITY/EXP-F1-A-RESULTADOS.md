# EXP-F1-A — Jitter Observability — RESULTADOS

**FASE:** R-4C (EJECUCIÓN COMPLETADA)
**Estado:** COMPLETADA — HARNESS CREADO/COMPILADO/EJECUTADO BAJO AUTORIZACIÓN
**Fecha:** 2026-09-22
**Autor citado:** MASTER-RESEARCH-STATUS v2.10

> Informe final de FASE R-4C / EXP-F1-A. Documenta **solamente resultados observados**, generados por el
> harness Vulkan ejecutado bajo autorización explícita, con las condiciones del mandato R-4C (todo local en
> `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/harness/` y `results/`, drivers RADV real + lavapipe, capa vía
> `VK_LAYER_PATH` local, CERO modificaciones al sistema, CERO benchmarks de rendimiento, jitter ≠ motion vector).

---

## 1. Resumen ejecutivo

| Nivel | Canal | MAE total [px] | RMS [px] | Máx error [px] | Frames correctos | Correlación (jx, jy) | Criterio MAE<0.01px |
|---|---|---|---|---|---|---|---|
| **A** | `vkCmdPushConstants` (canal dedicado) | **0.000000000** | 0.0 | 0.0 | **320/320 (100 %)** | (1.000, 1.000) | **PASS (margen ∞)** |
| **B** | Reconstrucción desde matriz de proyección en UBO host-visible | **3.66×10⁻¹⁰** | 3.07×10⁻⁹* | 3.0×10⁻⁸ | **320/320 (100 %)** | (1.000, 1.000) | **PASS (margen ≈×10⁷)** |

\* RMS combinado aproximado (√(RMS_x²+RMS_y²)); valores exactos en §4.

**Veredicto:** Q1, Q2 y Q3 respondidas con **PASS** en ambos niveles y ambos drivers (RADV RX 550 real y
lavapipe), con 2 réplicas por celda y resultados deterministas idénticos entre réplicas. El costo de
reconstrucción de NIVEL B es el piso FP32 esperado para W=1920 (máx 3×10⁻⁸ px), consistente con el margen
predicho en el PRECHECK (PRIOR-ART §4 y EXP-F1-A §3).

---

## 2. Configuración exacta ejecutada

**Hardware / drivers:**
- **RADV (real):** `AMD Radeon RX 550 / 550 Series (RADV POLARIS12)`, vendor `0x1002`, device `0x699f` — vía `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json`.
- **lavapipe (software):** vendor `0x10005` — `lvp_icd.x86_64.json`.
- **ANV (Intel):** opcional en el mandato — **EXCLUIDO**: `vkEnumeratePhysicalDevices` no devuelve ningún device físico con `intel_icd.x86_64.json` (iGPU sin exposición en este entorno); documentado como NO EJECUTADO, no como fallo del harness.

**Capa (local, sin instalación):**
- `VK_LAYER_PATH=<experimento>/harness/build/layer` (manifiesto `VkLayer_iterativero_jitter_observer.json`).
- `LD_LIBRARY_PATH=<experimento>/harness/build/layer` (resolución `dlopen` de `library_path: libjitter_layer.so`).
- Gating por nivel: `ITER_JITTER_LAYER_LEVEL_A=1` o `ITER_JITTER_LAYER_LEVEL_B=1` (comparación estricta a `"1"`).

**Secuencia (idéntica en cada corrida):** 324 frames = 4 preludio + 320 medidos (5 magnitudes
{0.5,0.25,0.125,0.0625,0.01} px × 8 direcciones × 6 = 240 + Halton[2,3] 16 + xorshift64 64); seed `0x5EED0000`
(1592590336); tamaño `1920×1080`; `--vendor` filtro por fabricante; preludio excluido de métricas.

**Matriz ejecutada:** NIVEL A y NIVEL B × {RADV, lavapipe} × 2 réplicas = **8 corridas**, todas exitosas
(324/324 frames capturados por la capa en cada una).

---

## 3. Configuración por celda (verificado en `results/<tag>_config.txt`)

| Tag | ICD | Vendor | Nivel | Frames | Seed | Layer path |
|---|---|---|---|---|---|---|
| `A_radv_r{1,2}` | radeon_icd | 0x1002 | A | 324 | 1592590336 | `harness/build/layer` |
| `A_lvp_r{1,2}` | lvp_icd | 0x10005 | A | 324 | 1592590336 | `harness/build/layer` |
| `B_radv_r{1,2}` | radeon_icd | 0x1002 | B | 324 | 1592590336 | `harness/build/layer` |
| `B_lvp_r{1,2}` | lvp_icd | 0x10005 | B | 324 | 1592590336 | `harness/build/layer` |

---

## 4. Resultados observados

### NIVEL A — canal directo (`vkCmdPushConstants`)

| Corrida | MAE x [px] | MAE y [px] | MAE total [px] | RMS x [px] | RMS y [px] | Máx [px] | OK/frames | Pearson jx | Pearson jy |
|---|---|---|---|---|---|---|---|---|---|
| A_radv_r1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 320/320 | 1.000000000 | 1.000000000 |
| A_radv_r2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 320/320 | 1.000000000 | 1.000000000 |
| A_lvp_r1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 320/320 | 1.000000000 | 1.000000000 |
| A_lvp_r2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 320/320 | 1.000000000 | 1.000000000 |

Los 324 valores recuperados son **bit-idénticos** a la GT (la capa lee `pValues` host en tiempo de recording;
no hay aritmética entre magnitud y recuperación).

### NIVEL B — reconstrucción algebraica desde matriz (M_jit = translate(jx_ndc,jy_ndc,0)·M_base)

| Corrida | MAE x [px] | MAE y [px] | MAE total [px] | RMS x [px] | RMS y [px] | Máx [px] | OK/frames | Pearson jx | Pearson jy |
|---|---|---|---|---|---|---|---|---|---|
| B_radv_r1 | 2.344×10⁻¹⁰ | 1.313×10⁻¹⁰ | 3.656×10⁻¹⁰ | 2.516×10⁻⁹ | 1.750×10⁻⁹ | 3.000×10⁻⁸ | 320/320 | 1.000000000 | 1.000000000 |
| B_radv_r2 | 2.344×10⁻¹⁰ | 1.313×10⁻¹⁰ | 3.656×10⁻¹⁰ | 2.516×10⁻⁹ | 1.750×10⁻⁹ | 3.000×10⁻⁸ | 320/320 | 1.000000000 | 1.000000000 |
| B_lvp_r1 | 2.344×10⁻¹⁰ | 1.313×10⁻¹⁰ | 3.656×10⁻¹⁰ | 2.516×10⁻⁹ | 1.750×10⁻⁹ | 3.000×10⁻⁸ | 320/320 | 1.000000000 | 1.000000000 |
| B_lvp_r2 | 2.344×10⁻¹⁰ | 1.313×10⁻¹⁰ | 3.656×10⁻¹⁰ | 2.516×10⁻⁹ | 1.750×10⁻⁹ | 3.000×10⁻⁸ | 320/320 | 1.000000000 | 1.000000000 |

Notas NIVEL B:
- La reconstrucción de la capa usa `T = projJit · inv(projBase)`, `jx_px = T[12]·W/2`, `jy_px = −T[13]·H/2` (validada por `--selftest`: `SELFTEST OK maxerr=0.0e+00 px`, 0 casos fallidos).
- El error residual (máx 3×10⁻⁸ px) es el **piso FP32 de la ruta matriz** para W=1920: el jitter más grande (0.5 px → jx_ndc ≈ 5.2×10⁻⁴) transita por mantisa FP32 y al multiplicar por W/2=960 devuelve el ULP correspondiente (~1 ULP de 2.5×10⁻⁴ ≈ 6×10⁻⁸ px en la cota superior). Resultado **consistente con el margen ~×50–500 sobre piso FP32** predicho en PRECHECK: el observado (×10⁷ sobre el target de 0.01 px) lo supera porque el piso real del harness (matrices exactas, sin acumulación) resultó menor que la cota conservadora del análisis.

### Detalle de recuperados vs GT (NIVEL B, RADV r1)

| Frame | GT (jx, jy) | Recuperado (jx, jy) | Δx | Δy |
|---|---|---|---|---|
| 4 | 0.500000000, 0.0 | 0.500000000, −0.0 | 0.0 | 0.0 |
| 68 | 0.062500000, 0.0 | 0.062500000, −0.0 | 0.0 | 0.0 |
| 196 | 0.010000000, 0.0 | 0.010000000, −0.0 | 0.0 | 0.0 |
| 260 | 0.441663384, 0.058295965 | 0.441663384, 0.058295965 | 0.0 | 0.0 |
| 300 | 0.390116155, 0.084235549 | 0.390116155, 0.084235549 | 0.0 | 0.0 |
| 319 | 0.006618023, −0.164746225 | 0.006618023, −0.164746225 | 0.0 | 0.0 |

(top-5 outliers: frames 291/268/269/306/286, error máx 3×10⁻⁸ px — zona pseudo-random.)

---

## 5. Respuestas a las preguntas del experimento

- **Q1 (NIVEL A): ¿Puede una capa observar jitter por push constants con MAE<0.01px?** → **SÍ**.
  MAE exacto 0.0 px (bit-idéntico), 320/320, Pearson 1.0, en RADV real y lavapipe.
- **Q2 (NIVEL B): ¿Puede una capa RECONSTRUIR el jitter desde la matriz de proyección (UBO host-visible) con MAE<0.01px?** → **SÍ**.
  MAE 3.66×10⁻¹⁰ px, máx 3×10⁻⁸ px, 320/320, Pearson 1.0 — sin leer ningún campo "jitter" rotulado; solo la aritmética de matrices.
- **Q3 (transversal): ¿Es estable entre drivers?** → **SÍ, determinista**:
  valores idénticos en RADV (RX 550 real) y lavapipe, y entre las 2 réplicas de cada celda. (ANV no presentó devices; fuera del alcance ejecutado.)

---

## 6. Clasificación (VERIFIED / DERIVED / ESTIMATED / UNKNOWN)

| Afirmación | Clase | Base |
|---|---|---|
| NIVEL A: la capa puede observar la secuencia completa (canal dedicado) con error 0.0 px | **VERIFIED (observado)** | 4 corridas (RADV×2, LVP×2), 320/320, MAE=0.0 |
| NIVEL B: la capa puede reconstruir los offsets desde la matriz de proyección jitterizada (UBO host-visible) con MAE<0.01 px | **VERIFIED (observado)** | 4 corridas, MAE=3.66×10⁻¹⁰ px ≤ 0.01 |
| El margen del piso FP32 de reconstrucción para W=1920 es ~×50–500 sobre 0.01 px (PRECHECK) | **CONFIRMADO con holgura** (observado: margen real ~×10⁷) | máx observado 3×10⁻⁸ px |
| La mecánica FSR2 de inyección por matriz (`M_jit = translate·M_base`) se reproduce y es invertible desde los datos per-frame | **VERIFIED (observado)** | recovery bit-exacto en NIVEL B |
| MAE<0.01 px es un estándar publicado de precisión de observación de jitter | **UNKNOWN / NO PUBLICADO** (se mantiene PROVISIONAL) | PRIOR-ART §4 |
| Drivers disponibles para esta matriz | **VERIFIED**: RADV + lavapipe ejecutados; **ANV sin devices → NO EJECUTADO** | vkEnumeratePhysicalDevices vacío |

> Regla del mandato cumplida: en NINGÚN punto se concluye que jitter = motion vector. El MV en el harness es fijo
> y no se correlaciona con la secuencia observada (el canal de observación es el jitter de proyección).

---

## 7. Incidencias resueltas durante la ejecución (documentadas, no ocultas)

1. **`library_path` relativo y `VK_LAYER_PATH`:** el loader resuelve `libjitter_layer.so` por `dlopen`; se
   añade `LD_LIBRARY_PATH` local a la corrida. Sin instalación en el sistema.
2. **Capa implicada con `VK_LAYER_MESA_device_select` (implicit layer del sistema):** la capa intermedia
   altera la cadena `pNext` al despachar `vkCreateInstance`/`vkCreateDevice`; el recorrido de la cadena debe
   distinguir al link por `function == VK_LAYER_LINK_INFO` (no solo por `sType`). Corregido en `layer.c`;
   verificado sin necesidad de desactivar la implicit layer del sistema.
3. **`vkCreateDevice` no se obtiene vía device-GPA con `VK_NULL_HANDLE`** en este loader: se resuelve a través
   del instance-GPA de la cadena (`g_inst.nextGIPA(instance, "vkCreateDevice")`), patrón estándar del loader.
4. **PFN con `VK_NO_PROTOTYPES` (headers Vulkan 1.4.341):** las firmas de los interceptores de device/queue/cmd
   **no** llevan `VkDevice` inicial (`PFN_vkQueueSubmit = (VkQueue, uint32_t, …)`), y las llamadas a
   funcs obtenidas por `GetInstanceProcAddr`/`GetDeviceProcAddr` se convierten al PFN concreto.
5. **Gating por nivel:** se comparan `ITER_JITTER_LAYER_LEVEL_A/B` contra `"1"` (no basta `getenv()!=NULL`).

---

## 8. Archivos de evidencia

```
03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/
├── harness/                      # fuente del harness (perframe, jittergen, app, layer, glsl, scripts, CMakeLists)
│   ├── build/                    # binario jitter_harness, _gen/*.spv, layer/libjitter_layer.so + manifest
│   ├── layer/layer.c             # capa observadora (con correcciones §7)
│   └── scripts/compare.py        # unión GT↔recuperado, métricas MAE/RMS/max/correctos/Pearson/outliers
└── results/
    ├── gt/           A_*_gt.json, B_*_gt.json          (8 archivos, referencia independiente)
    ├── recovered/    A_*.lines, B_*.lines              (8 archivos, canal de la capa: "frame jx jy")
    ├── metrics/      *_metrics.json                    (8 archivos, métricas completas)
    ├── logs/         *.log + run_all.log               (stdout por corrida + resumen)
    └── *_config.txt                                     (8 archivos, configuración exacta por celda)
```

Reproducibilidad: `./harness/run_all.sh` reconstruye y re-ejecuta la matriz completa (build + NIVEL A/B ×
{RADV, lavapipe} × 2 réplicas + análisis).

---

## 9. Limitaciones y notas de honestidad

- **Solo se reportan valores observados.** Las celdas ANV son **NO EJECUTADAS** (sin devices), no "fail".
- El harness es una prueba de **observabilidad de protocolo**, no una medición de rendimiento (mandato: sin
  benchmarks). Todo ocurre a nivel de capa host; no hubo interacción con registros, DPM, PowerPlay ni runtime-PM.
- Reconstrucción NIVEL B limitada a buffers **HOST_VISIBLE** (este harness) — buffers DEVICE_LOCAL puros no son
  legibles por la capa (limitación documentada en PRECHECK).
- La GT es independiente de la capa; el comparador une por `frame`/marker tras descartar el preludio.
- **MAE<0.01 px sigue siendo un PROVISIONAL TARGET** (sin estándar publicado): este experimento lo satisface con
  margen de varios órdenes de magnitud, pero no establece un estándar.

---

## 10. FINAL CLOSURE AUDIT

**Tipo:** auditoría documental y estática del cierre de R-4C / EXP-F1-A (sin compilar, ejecutar ni modificar nada).
**Fecha:** 2026-09-22. **Criterio aplicado:** verificar que NIVEL B es metodológicamente válido y que ningún canal
de recuperación depende del ground truth (GT).

### 10.1 Qué se verificó

- Código completo del harness: `harness/app_vulkan.c`, `harness/perframe.{h,c}`, `harness/jittergen.{h,c}`,
  `harness/layer/layer.c` (+ manifiesto), `harness/scripts/compare.py`.
- Datos reales: los 8 `results/gt/*_gt.json`, los 8 `results/recovered/*.lines` (324 líneas cada uno), los 8
  `results/metrics/*_metrics.json` y los `results/logs/*`.
- Flujo de datos por nivel, canal de recuperación por nivel y trazabilidad de variables (puntos 2 y 3 del mandato).

### 10.2 Evidencia concreta

**NIVEL A (canal directo).** La app llena `PushPayload {frameMarker, jitterX, jitterY, pad}` con `jx_px`/`jy_px` y
lo envía por `vkCmdPushConstants` (`app_vulkan.c:475-483`). La capa intercepta esa llamada e interpreta `pValues`
como `PushPayload`, volcando `pp->jitterX`/`pp->jitterY` (`layer.c:311-321`). El GT se escribe a archivo una sola vez
al inicio del proceso (`jitter_write_gt`, `jittergen.c:103-121`, invocado en `app_vulkan.c:566`) y jamás se relee.
El único `fopen` de la capa es su propio log en modo `"w"` (`layer.c:93`): la capa **no puede** leer el archivo GT.
El recovered es el payload real del push constants observado en vivo; la igualdad con GT (MAE=0.0 exacto, 4 corridas)
es consecuencia de que ambos despliegan el mismo float fuente, no de inyección de GT en el canal.

**NIVEL B (reconstrucción).** El struct compartido `PerFrame` (`perframe.h:11-18`) contiene solo
`color, magic, frameMarker, viewport[2], projBase[16], projJit[16]` — **no existe ningún campo `jx`/`jy`** en el UBO.
La app escribe `magic`, `frameMarker`, `viewport`, `projBase` y `projJit` (`app_vulkan.c:429-450`);
`projJit = translate(jx_ndc,jy_ndc,0) · projBase`, con `jx_ndc = 2·jx_px/W` (`app_vulkan.c:74-82`). La capa
(`snapshot_ubo`, `layer.c:114-131`) usa únicamente: `magic` (filtro de identificación `0x4A495443`), `frameMarker`
(marca de frame), `viewport[0..1]` (W,H) y las matrices `projBase`/`projJit` pasadas a
`perframe_recover_jitter` (`perframe.c:68-82`):

1. `invBase = inv(projBase)` (Gauss-Jordan, precisión doble);
2. `T = projJit · inv(projBase)` (producto con acumulación doble);
3. `tx = T[12]; ty = T[13]` (traslación NDC, convención column-major);
4. `jx_px = tx·W/2; jy_px = −ty·H/2` (conversión NDC→píxeles).

No existe variable auxiliar que transporte `jx`/`jy` entre app y capa, no se lee ningún campo rotulado como jitter y
la reconstrucción computa el valor a partir de los elementos de la matriz del UBO. Flujo:
**UBO(projBase, projJit) → inv(projBase) → T = projJit·inv(projBase) → T[12],T[13] → jx_px, jy_px**.

### 10.3 Resultado NIVEL A

**VERIFIED.** El valor recuperado procede de `pValues` de `vkCmdPushConstants` observado por la capa
(`layer.c:315-318`); el GT no se inyecta en el canal (único `fopen` de la capa: su log en `"w"`). 320/320 frames
correctos, MAE=0.0, Pearson 1.0, ambas réplicas y ambos drivers (RADV real RX 550 y lavapipe).

### 10.4 Resultado NIVEL B

**VERIFIED.** La reconstrucción usa exclusivamente los elementos de `projBase`/`projJit` del UBO host-visible
(inspección estática de `layer.c` y `perframe.c`); no depende del GT de forma directa ni indirecta (la capa no abre
el GT; el UBO no contiene valores de jitter). Independencia confirmada en 2 planos:
- **Estática:** `layer.c` solo abre su log en modo `"w"`; `jittergen`/`app_vulkan.c` solo abren archivos con `"r"`
  para los SPV (`app_vulkan.c:320`); el GT es write-only para el proceso y su lectura es análisis post-hoc de
  `compare.py`.
- **Observacional:** si el recovered viniera de una copia del GT o de un campo de jitter, sería bit-idéntico (error
  exacto 0 en los 320), como ocurre en NIVEL A. En NIVEL B el error es ~1 ULP FP32 y distinto de cero en la zona
  pseudo-random (outliers 291, 268, 269, 306, 286), mientras que los offsets exactamente representables en ejes
  (0.5/0.25/0.0625/0.01 px) dan 0.0: patrón propio de una aritmética de reconstrucción, no de una copia.

**Explicación del error pequeño (punto 4):** es el piso FP32 de representación del desplazamiento NDC dentro de la
matriz. Para el máximo jitter (|jx|=0.47 px): `jx_ndc = 2·0.47/1920 ≈ 4.9×10⁻⁴`; el ULP float32 en ese rango es
5.82×10⁻¹¹; medio-ULP × `W/2 = 960` = **2.79×10⁻⁸ px ≈ máximo observado 3.0×10⁻⁸ px** (frame 291: GT
`-0.470924586` vs recovered `-0.470924616`). El MAE 3.66×10⁻¹⁰ es el promedio de errores ~ULP sobre 320 frames
(la mayoría con jitter menor o exactamente representable → error 0). Es el límite de representación/aritmética
esperado, **no** un acoplamiento accidental entre GT y recovered: un acoplamiento daría error 0 en todos los frames
(como en A), no ~medio-ULP en la zona no representable.

**Punto 3 (independencia):** modificar o eliminar el GT después de preparar el UBO **no cambia** el valor recuperado:
el recovered se deriva por frame de la memoria mapeada del UBO en `vkQueueSubmit`→`snapshot_ubo`, el GT es un
archivo downstream que la capa nunca abre, y el proceso secuencial (GT escrita en línea 566, render en 593-594)
no relee el archivo. La única forma de alterar el recovered sería alterar las matrices del UBO (el estímulo), lo que
está fuera del canal de observación auditado.

### 10.5 Limitaciones

- Auditoría **documental/estática**: no se re-ejecutó el harness (mandato de la revisión). Los artefactos auditados
  son los producidos en la corrida autorizada.
- La reconstrucción solo es válida para buffers **HOST_VISIBLE** (el caso de este harness); buffers DEVICE_LOCAL
  puros no son legibles por la capa (documentado en §9 y PRECHECK).
- ANV permanece **NO EJECUTADO** (sin devices físicos en este entorno); no afecta la validez de RADV/lavapipe.
- El error de NIVEL B no es cero por diseño (piso FP32 de la ruta matriz); la cota observada (3×10⁻⁸ px) cumple el
  target provisional (0.01 px) con margen ~×10⁷.

### 10.6 UNKNOWNs restantes

- Valores de precisión bajo otros loaders/ICDs fuera de RADV y lavapipe (p. ej. ANV con hardware real).
- Comportamiento con buffers no host-visibles / memoria device-local (fuera del diseño de NIVEL B).
- Existencia de un estándar público para MAE de observación de jitter (MAE<0.01 px permanece PROVISIONAL, PRIOR-ART §4).
- Independencia de `T[12]`/`T[13]` bajo matrices de proyección no del estilo FSR2 `translate·M_base` (no ejercitado).

### 10.7 Veredicto

Ambos niveles cumplen el diseño: NIVEL A **VERIFIED**, NIVEL B **VERIFIED** (sin dependencia del GT, reconstrucción
exclusiva desde los elementos de la matriz del UBO, error explicado como piso FP32). Sin GAPs metodológicos
encontrados.

**EXP-F1-A = CLOSED.** Sin acciones posteriores (ninguna fase nueva se inicia con esta revisión).
