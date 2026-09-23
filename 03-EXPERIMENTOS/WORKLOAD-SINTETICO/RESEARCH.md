# RESEARCH — Workload sintético GPU (rama §J)

Registro permanente de investigación y experimentación para el diseño del workload
sintético de la RX 550 (Polaris12/RADV). Cumple la regla del proyecto **DN-13**
(`decisions.md`): documentar NO SOLO resultados, sino también la metodología.

Convención de estado (heredada de `MASTER-PLAN.md`):
`[VERIFICADO]` · `[REPRODUCIBLE]` · `[OBSERVADO]` · `[NO REPRODUCIBLE]` ·
`[HIPÓTESIS]` · `[DESCARTADO]` · `[DESCONOCIDO]`.

Los registros E-01/E-02 documentan corridas ya autorizadas y ejecutadas (resultados
contenidos en `runs/exploratorio-01/` y `runs/exploratorio-02/`); NO se reejecutan,
las conclusiones originales se preservan.

Segunda fase (diseño de un workload **gráfico**, sin ejecución): la investigación
R-06..R-09 y el diseño multiopción quedan en `DESIGN-GRAPHICS.md`. Ningún experimento
de esta fase fue ejecutado; NO se modificó código, kalm, Mesa ni amdgpu (regla del
proyecto).

---

## R-01 — Especificación de Polaris12 / Radeon RX 550

### 1. Pregunta
¿Qué capacidad real de cómputo, memoria y potencia tiene la RX 550 (Polaris12) para
diseñar un workload que eleve el draw por encima de ~27 W con cap=35 W?

### 2. Fecha
2026-09-20/21.

### 3. Metodología de investigación
- Términos/consultas usadas:
  - `Radeon RX 550 specs power consumption Polaris12`
  - `RX 550 Polaris12 memory bandwidth L2 cache GDDR5`
  - `amdgpu power1_input power1_average microWatts SMU`
  - `gpu_busy_percent mem_busy_percent amdgpu meaning`
  - `texture sampler wavefront GCN polaris power fill rate`
- Se priorizó: (1) whitepaper oficial AMD de Polaris; (2) docs oficiales del kernel
  (amdgpu); (3) reviews independientes con medición física (igor'sLAB) y agregadores
  de specs (TechPowerUp, videocardz, RelaxedTech, Phoronix).
- Contraste de afirmaciones: las specs de SP/CU/TMU/ROP/L2/bandwidth coincidieron
  entre TechPowerUp, videocardz, RelaxedTech e igor'sLAB; el whitepaper publicitaba
  "L2 duplicado vs gen anterior" (aplicable a Polaris10/11, 1 MB), mientras
  igor'sLAB especifica P12 = 512 KB → se adopta 512 KB para P12 (fuente con medición).

### 4. Fuentes (URLs y aporte)
- https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2947 — specs base: GCN 4, 512 SP, 32 TMU, 16 ROP, 2 GB GDDR5 128-bit, 112 GB/s, boost 1183 MHz.
- https://videocardz.net/amd-radeon-rx-550 — Lexa PRO P12, 101 mm², 2.2 B transistores, 50 W, fillrates (18.9 GPix/s, 37.9 GTex/s).
- https://www.igorslab.de/en/performance-benchmark-power-consumption-rx550-polaris/ — P12 con 512 KB L2 (vs 1 MB), medición física: juego ~47 W (picos 59 W filtrados), stress <50 W con SCLK reducido a ~820 MHz por Power Tune.
- https://www.relaxedtech.com/reviews/amd/radeon-rx-550/1 — tabla completa (base 1100, boost 1183 MHz, 1.126 GFLOPs FP32, TDP 50 W, PCIe 3.0 x8).
- https://www.phoronix.com/review/radeon-rx550-linux — benchmarks en Linux (Mesa), confirma soporte amdgpu/RADV para P12.
- Whitepaper Polaris de AMD/RealWorldTech: http://zqwzjdq.vgamuseum.info/images/doc/amd/polaris-whitepaper.pdf — GCN 4, delta color compression (hasta 8:1, ahorro de ancho de banda y potencia), L2 aumentado en Polaris10 vs gen previa, ACE y estructura de colas.

### 5. Hechos VERIFICADOS
- RX 550 = Polaris12 "Lexa PRO", GCN 4.0, 14 nm FinFET, 101 mm², 2.2 B transistores, 50 W TDP/board power.
- 512 SP en 8 CUs (de 10; 2 CU deshabilitadas), 32 TMU, 16 ROP; buses 128-bit y 7 Gb/s GDDR5 → 112 GB/s; 512 KB L2 (P12).
- Clocks spec: base 1100 MHz, boost 1183 MHz (1203 MHz en algunas variantes OEM); 1.126 GFLOPs FP32.
- Con cap de potencia ~50 W y carga extrema sostenida, el Power Tune bajó SCLK a ~820 MHz (la placa se limita por potencia, no por clock) — igor'sLAB, medición física.

### 6. Hipótesis planteadas
- Un workload de cómputo "puro" (ALU) con la GPU a 100 % busy subirá la potencia apreciablemente.
- La presión de memoria/bandwidth o el llenado de VRAM deberían activar MCLK/GDDR5 y añadir draw.

### 7. Estado de hipótesis
- Abiertas (nunca confirmadas con datos de esta placa → evaluadas en E-01/E-02: ver resultados).
- El Power Tune a 35 W no actúa con draw observado < 14 W [VERIFICADO en este sistema].

### 8..13. (Aplica E-01/E-02 para lo experimental)
Remisión a registros E-01/E-02. Decisión técnica de esta investigación (2026-09-20):
**variar parámetros del prototipo compute actual (iterations/stride/vram) para medir**
el draw en el sistema real antes de rediseñar a otra pipeline (gráfica/fragment o
texture-heavy). Alternativas descartadas por ahora: pipeline gráfica completa (más
complejo sin evidencia previa), forzar clocks/DPM (vetado por regla del proyecto).

---

## R-02 — Kernel/amdgpu: sensores de potencia, busy y gestión DPM

### 1. Pregunta
¿Qué significan exactamente `power1_input`, `gpu_busy_percent`, `mem_busy_percent` y
los modos DPM que usa nuestra telemetría? ¿Qué limita realmente el draw en esta placa?

### 2. Fecha
2026-09-20/21.

### 3. Metodología de investigación
- Consultas: `amdgpu power1_input average microWatts`; `amdgpu mem_busy_percent gpu_busy_percent meaning Polaris`; `amdgpu power_dpm_force_performance_level manual profile_peak`.
- Priorización: documentación oficial del kernel (docs.kernel.org, dri.freedesktop) y
  el commit que introduce `mem_busy_percent`; se contrastó la doc textual con el
  código real (`amdgpu_pm.c`, `read_sensor`) para confirmar el significado.
- Esto respalda a `telemetria.sh` reutilizado de EXPLORATORIO-GravityMark (solo lectura).

### 4. Fuentes (URLs y aporte)
- https://docs.kernel.org/gpu/amdgpu/thermal.html — poder: `power1_average`/`power1_input` en µW (SMU, "SoC"); hwmon con temp/gpu/mem clock; DPM (`auto`, `low`, `high`, `manual`, `profile_standard`, `profile_min_sclk`, `profile_min_mclk`, `profile_peak`); `pp_dpm_sclk/mclk` niveles; `pp_power_profile_mode` heurísticas; menciona GFXOFF.
- https://dri.freedesktop.org/docs/drm/gpu/amdgpu.html — API general; dominios de memoria GEM (VRAM/GTT/CPU), BOs, reset.
- https://git.b0tt0m.xyz/mirror/linux/commit/f120386d74... — commit que añade `mem_busy_percent` (sensor `AMDGPU_PP_SENSOR_MEM_LOAD`, firmware SMU; dGPU only). Confirma que "#" es actividad agregada de IP cores calculada por firmware.
- https://lists.freedesktop.org/archives/amd-gfx/2020-June/050624.html — rename/doc: `gpu_busy_percent` = "how busy the GPU is", `mem_busy_percent` = "how busy the VRAM is", ambos por firmware SMU.

### 5. Hechos VERIFICADOS
- `power1_input`/`power1_average` = estimador del firmware SMU en microWatts (no un vatímetro físico); en dGPU representa la GPU, pero NO incluye CPU.
- `power1_cap` limita draw total de la GPU; en este sistema `power1_cap_max = 35 W` y el valor observado en idle es 3.3–3.7 W.
- `gpu_busy_percent`/`mem_busy_percent` = % de actividad calculado por SMU; `mem_busy` correlaciona con actividad del controlador de memoria (VRAM), presente solo en dGPU.
- `scale_factor` implícito: telemetría usa archivos planos de texto; frecuencias se leen por el nivel marcado `*` en `pp_dpm_sclk/mclk`.
- DPM auto en carga sostenida de este workload: SCLK 1071 MHz dominante; MCLK 300 MHz (piso) [VERIFICADO en E-01/E-02].

### 6..7. Hipótesis
- (planteada) `power1_input` leído a 10 Hz con ventana estable refleja la potencia real durante el run.
- (estado) Confirmada operativamente: en E-01/E-02 los valores quedan por debajo del cap y no plainean en 35 W; el cap NO liga en estas cargas.

### 8..13.
- Método: `telemetria.sh <dur> <out>` (heredado, sin modificaciones), 10 Hz, campos
  `ts;power_uW;temp_mC;gpu_busy;mem_busy;vram_used;gtt_used;sclk_level;mclk_level`.
- Variables medidas: potencia, temp, busy GPU/mem, VRAM/GTT usados, nivel SCLK/MCLK.
- Control de variables: mismo dir, env VK fijo, same input params, seed fija, cap/control/DPM verificados pre/post, journal revisado; "fase activa" = muestras con gpu_busy>0 y ventana estable (descartar ~0.7s iniciales y última muestra, según reglas del laboratorio).
- Criterios de éxito/fallo: RC=0 y sin mensajes de reset/hung/device lost; criterio de descarte: si MCLK no sube y mem_busy permanece bajo, la carga no presionó banda ni memoria.
- Decisión técnica: mantener GTT en mínimo y VRAM moderada (< 2 GB) para no provocar OOM (lección de GravityMark 4m); enviar la carga a device local (DEVICE_LOCAL en allocación).
- Alternativas descartadas: reads de GTT (fuera de foco), usar `profile_peak`/manual (vetado: requiere write y no autorizado).

---

## R-03 — RADV / Vulkan en GFX8 (Polaris12)

### 1. Pregunta
¿Cómo se ejecuta un shader compute bajo RADV en esta RX 550, y qué limita el throughput?

### 2. Fecha
2026-09-20/21.

### 3. Metodología de investigación
- Consultas: `RADV documentation`, `radv GFX8 compute wave64`, `RADV vs AMDVLK Vulkan driver polaris`.
- Priorización: doc oficial de Mesa (docs.mesa3d.org), después artículos de contexto (Phoronix, comparaciones de drivers).
- Contraste: la doc de RADV (UMD sobre amdgpu, ondas 32/64 lanes) se contrastó con lo
  realmente observado en nuestro program (device `AMD Radeon RX 550 / 550 Series (RADV
  POLARIS12) vendor=0x1002 device=0x699F`) [VERIFICADO].

### 4. Fuentes (URLs y aporte)
- https://docs.mesa3d.org/drivers/radv.html — RADV = driver Vulkan UMD que trabaja con el KMD amdgpu vía libdrm/uAPI DRM; invocación shader = CU SIMD; subgroup = wave de 64 o 32 lanes; colas GFX (PM4) y ACE; sección de performance (env overrides, meta paths) y compat GFX6-7 (GCN 1-2 no por defecto en amdgpu).
- https://www.phoronix.com/review/radv-amdvlp-pro — contexto histórico: RADV vs AMDVLK vs AMDGPU-PRO en Polaris/Vega (LLVM vs propio).
- Observación propia del sistema: `vulkaninfo` y salida del prototipo confirman RADV para `1002:699f` (gfx804) [VERIFICADO].

### 5. Hechos VERIFICADOS
- RADV se apoya en amdgpu (KMD) y libdrm; el pipeline compute usa la cola GFX; los shaders se ejecutan en los mismos CUs (no hay hardware dedicado compute).
- El prototipo selecciona físicamente la RX 550 (0x1002:0x699F) y la valida en tiempo de ejecución [VERIFICADO en E-01/E-02: correcto device].
- Vega/GFX8 presentan a veces LDS/occupancy tuning; el shader de prototipo es ALU-light en memoria, por lo que la ocupación no fue el factor crítico en E-01/E-02 (SCLK pegado a 1071, mem_busy bajo).

### 6..7. Hipótesis
- (planteada) la carga Volt compute está limitada por la ejecución del shader (ALU/latencia) y NO por memoria ni por ocupación — evaluada en E-01/E-02.
- (estado) confirmada: al añadir 2× iteraciones + 16× stride el throughput cayó 3× (fps 8.08→2.53) y la potencia NO subió; mem_busy siguió bajo → el cuello de botella es el propio shader en SCLK 1071.

### 8..13.
- Método y decisiones: ver E-01/E-02. Decisión técnica: no rediseñar mientras la causa
  del techo sea la latencia interna del shader; un camino futuro es reducir dependencias
  y/o usar rasterización para saturar ROPs/render back-end (hipótesis R-04).
- Alternativas descartadas: usar pipeline mínima distinta (fragment) sin primero medir compute.

---

## R-04 — Compute vs fragment/textura: patrones que generan consumo

### 1. Pregunta
¿Qué patrón de carga (compute ALU, fill-rate/overdraw + MSAA, texture sampling)
eleva el draw de la RX 550, y por qué?

### 2. Fecha
2026-09-20/21.

### 3. Metodología de investigación
- Consultas: `FurMark GpuTest stress power draw fill rate fragment overdraw vs compute`; `compute shaders vs fragment shaders performance`; `compute shader more efficient pixel shader`; `texture sampling GCN polaris power fill rate stress`.
- Priorización: análisis técnicos de la comunidad (StackExchange Computergraphics) con perfiles
  reales; material de Geeks3D (FurMark/GpuTest) y análisis del "GPU killer".
- Contraste de la afirmación "memoria-bound genera potencia igual que compute": dicha afirmación
  se refiere a benchmarks que saturan DRAM; en NUESTRO caso la DRAM no se saturó (MCLK piso,
  mem_busy 3–7%). Por eso la conclusión de la fuente NO contradice nuestra medición: se debe al
  w/s efectivo del shader (256 KB, cabe en L2) — ver R-05.

### 4. Fuentes (URLs y aporte)
- https://geeks3d.com/furmark/ y https://geeks3d.com/gputest/ y https://www.geeks3d.com/furmark/command-line/ — FurMark/GpuTest: tests de estrés (fill-rate, tessellación, pixel shaders); opciones `--msaa`, `--furmark-vram-test-gb`; pelaje con MSAA como carga intensiva.
- https://specpicks.com/reviews/why-does-furmark-have-gpu-killer-reputation — explica que el "GPU killer" viene de carga plana y sostenida con shader que satura todas las unidades de ejecución; los games son bursty.
- https://www.pchardwarepro.com/en/furmark-how-to-stress-gpu-and-vram-without-dying-in-the-attempt/ — MSAA aumenta carga; FurMark genera carga masiva de lectura/escritura en VRAM; distinción con games.
- https://computergraphics.stackexchange.com/questions/9956/... — el mismo shader como fragment vs compute: con coordenadas coherentes al pixel, fragment ganó ~2× (orden de pixels/colas del vendor y coherencia de texture), con coordenadas aleatorias empataron → la ventaja de fragment es de coherencia de acceso a memoria, NO de hardware especial.
- https://computergraphics.stackexchange.com/questions/54/... — compute salta el paso de ROP/blending (ruta más directa a memoria) y puede ser más rápido para filtrado; pero pierde el packing/diseño de wavefronts por tiles que hace el pipeline de raster.

### 5. Hechos VERIFICADOS
- Compute, vertex y fragment se ejecutan en los mismos SPs/CUs de GCN; no hay unidades dedicadas.
- La ventaja de performance de fragment sobre compute (cuando existe) viene del orden de ejecución/empaquetado coherente de pixels (tiling) y de sampling coherente, no de hardware distinto.
- Fill-rate, overdraw y MSAA incrementan la carga del render back-end y del shading (FurMark/estudios).
- FurMark genera un load plano y sostenido al 100 % de utilización con un shader específico para saturar unidades de ejecución; este patrón plano es el tipo de carga que estresa más la GPU.

### 6..7. Hipótesis (para diseño futuro)
- H-frag: un pipeline gráfico (fragment) con fullscreen quad grande + overdraw bajo MSAA
  satura ROPs/render back-end y produce más draw que compute ALU puro [HIPÓTESIS, no testeada aún].
- H-tex: sampleo de textura con coordenadas incoherentes + working set > 512 KB L2 fuerza
  DRAM (MCLK > piso) y añade draw [HIPÓTESIS, parcialmente soportada por teoría de coherencia].
- H-band: memoria-bound REAL (que genera potencia comparable al compute) requiere saturar
  DRAM; no ocurre si el w/s cabe en L2 (ver R-05) [HIPÓTESIS coerente con E-02].

### 8..13.
- Método experimental relevant: E-01/E-02 solo cubren compute ALU+memoria estridada; ningún
  pipeline gráfico/textura fue ejecutado aún (no autorizado).
- Limitaciones: no se puede concluir sobre fragment/overdraw/texture sampling con los datos actuales.
- Decisión técnica: mantener compute por ahora; documentar las hipótesis H-frag/H-tex para un
  posible rediseño futuro SOLO con autorización explícita.
- Alternativas descartadas: cambiar a pipeline gráfica sin evidencia; ese cambio se deja
  documentado como hipótesis para evaluación futura.

---

## R-05 — Memoria/bandwidth, VRAM/GTT y el límite de los 256 KB

### 1. Pregunta
¿Por qué un SSBO de 512 MiB no generó presión DRAM real (MCLK en piso, mem_busy bajo) en E-02?

### 2. Fecha
2026-09-20/21.

### 3. Metodología de investigación
- Análisis del propio shader (`src/compute.comp`): el índice de acceso es
  `idx = (base + it*37) & 0xFFFF`, con `base = gid * stride`. Como `& 0xFFFF` el w/s
  accesible queda limitado a 64 K floats = **256 KB**, sin importar el tamaño del SSBO.
- Contraste con docs/código: la L2 de P12 es 512 KB (R-01). Un w/s de 256 KB cabe en L2 →
  los accesos se sirven casi siempre desde L2, no desde GDDR5 → MCLK no se activa.
- Consultas: `L2 cache Polaris12 size`; `mem_busy_percent low despite large vram buffer`.

### 4. Fuentes (URLs y aporte)
- `experiments/WORKLOAD-SINTETICO/src/compute.comp` (líneas 16-28) — evidencia del `& 0xFFFF` (límite 256 KB).
- https://www.igorslab.de/en/performance-benchmark-power-consumption-rx550-polaris/ — 512 KB L2 P12.
- https://docs.kernel.org/gpu/amdgpu/thermal.html y https://dri.freedesktop.org/docs/drm/gpu/amdgpu.html — dominios de memoria (VRAM local, GTT sistema) y mem_busy por SMU.
- Datos propios E-01/E-02 (telemetría) — MCLK 300 MHz todo el run, mem_busy ≤7 %, VRAM 0.51 GB.

### 5. Hechos VERIFICADOS
- En E-02 el SSBO de 512 MiB se malloc en VRAM (DEVICE_LOCAL, 0.51 GB) [telemetría], pero el shader SOLO accede a 256 KB (máscara `& 0xFFFF`).
- MCLK quedó en 300 MHz (piso) durante el 100 % del run y mem_busy ≤ 7 % → GDDR5 casi no participó.
- VRAM física no se llenó (0.51 GB < 2 GB) → no hubo spill a GTT; GTT permaneció ~12 MB.

### 6..7. Hipótesis
- (planteadas) H1: quitar el `& 0xFFFF` (o aumentar la máscara) para que el w/s accesible
  supere la L2 y fuerce tráfico DRAM. H2: los accesos estridados amplifican el fallo de caché.
- (estado) H1/H2 NO evaluadas experimentalmente (requeriría modificar el shader → nueva
  autorización; fuera del alcance de esta tarea de investigación).

### 8..13.
- Método: análisis estático del shader + datos de telemetría de E-02 (sin reejecución).
- Conclusiones y límites: el resultado de E-02 NO sirve para juzgar "memoria-bound real" porque
  no hubo presión DRAM; cualquier conclusión sobre presión de banda es inválida con este w/s.
- Decisión técnica: documentar el techo de 256 KB como causa de la falta de presión DRAM, y
  marcar en diseño futuro la necesidad de un selector de w/s mayor a L2 (512 KB+) cuando se
  evalúe el patrón memoria/bandwidth.

---

## E-01 — Corrida exploratoria 01 (compute ALU pura)

### 1. Pregunta
¿Cuánta potencia consume un workload Vulkan compute puro (ALU) en la RX 550 con cap=35 W
y configuración conservadora? ¿Se acerca al umbral de interés (~27 W)?

### 2. Fecha
2026-09-20. Autorizada por el dueño como primera corrida exploratoria.

### 3. Metodología de investigación
N/A (no hubo búsqueda web nueva; se usa la base de R-01..R-05 + prototipo ya construido).

### 4. Fuentes
Internas: MASTER-PLAN §J (gates), `src/main.cpp`, `src/compute.comp`, `runs/exploratorio-01/*`.

### 5. Hechos VERIFICADOS
- Ejecución RC=0, stderr vacío, sin reset/hang/OOM en el journal (pre/post).
- Device correcto: `RADV POLARIS12 vendor=0x1002 device=0x699F`.
- Potencia fase activa: media 13.23 W, máx 13.35 W (< umbral); temp media/máx 40.3/44.0 °C;
  SCLK 1071 dominante; MCLK 300 MHz todo el tiempo; GPU busy 100 %; mem_busy pico 18 %;
  VRAM máx 274 821 120 B; GTT 11.6 MB.

### 6..7. Hipótesis
- (planteada) ALU pura dejaría la GPU 100 % busy y subiría el draw.
- (estado) Confirmada la primera parte (busy 100 %, SCLK 1071), RECHAZADA la parte de
  potencia: 13.2 W ≪ 27 W. La carga ALU pura NO rampa el draw.

### 8. Metodología experimental
- Hardware/software: RX 550 (Polaris12, 1002:699f, card1, amdgpu, RADV/Mesa), display Intel (seguridad); kernel/DRM del sistema; binario `main` (build -O2).
- Config/env: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json MESA_VK_DEVICE_SELECT=1002:699f ./main --duration 20 --vram 268435456 --iterations 512 --stride 16 --seed 42`.
- Parámetros workload: workgroups=4096, local_size=256, iterations=512, stride=16, seed=42, vram=256 MiB (w/s efectivo 256 KB por `& 0xFFFF`).
- Comandos/procedimiento: pre-flight (cap/control/dpm/vendor/idle) → telemetría 10 Hz en paralelo → ejecución → post-flight → revisión journal → archivos en `runs/exploratorio-01/`.
- Variables medidas: potencia (µW), temp, busy, mem_busy, VRAM/GTT, SCLK/MCLK.
- Control externo: seed fija, sin writes sysfs, cap=35 W auto, run único, ventana estable (fase activa gpu_busy>0, descontar ~0.7s + última muestra).
- Criterios éxito/fallo: RC=0 + sin mensajes de reset/hung; descarte si hay device lost/OOM.
- Criterio de gate: superar ~27 W sostenidos → NO superado.

### 9. Resultados y datos
Ver tabla en `RESULTADO-EXPLORATORIO-01.md` (185 muestras, 10 Hz).

### 10. Limitaciones / qué NO puede concluirse
- Un solo run conservador; no evalúa iteraciones altas, w/s grandes ni composición mixta.
- MCLK nunca se activó; no hay señal sobre costo de DRAM.
- La configuración era intencionalmente conservadora (regla del dueño: no aumentar intensidad sin autorización).

### 11/12. Decisión técnica y por qué
- Decisión: autorizar una segunda corrida con más working set y dispersión (memoria/bandwidth).
- Por qué: la hipótesis de que "más memoria" activaría MCLK y subiría el draw seguía abierta;
  alternativas (pipeline gráfica, forcing de clocks) descartadas por ser más invasivas o no autorizadas.

### 13. Contradicciones
- Ninguna a la fecha. Si una futura corrida contradice estos valores, se documentará.

---

## E-02 — Corrida exploratoria 02 (ALU + presión memoria/bandwidth)

### 1. Pregunta
¿Aumentar working set (512 MiB), iteraciones y stride sube el draw y activa la banda de
memoria (MCLK) en la RX 550?

### 2. Fecha
2026-09-20. Autorizada como segunda corrida exploratoria (una sola config).

### 3. Metodología de investigación
N/A (no hubo búsqueda web nueva; se reutiliza la base de R-01..R-05).

### 4. Fuentes
Internas: `runs/exploratorio-02/*`, código/shaders idénticos a E-01 (binario md5 `a7e7ace5...` sin cambios).

### 5. Hechos VERIFICADOS
- RC=0, stderr vacío, journal limpio, mismo device.
- Potencia fase activa media 12.38 W, máx 12.51 W; temp 43/46 °C; SCLK 1071 dominante;
  MCLK 300 MHz (piso) TODO el tiempo; mem_busy 3–7 %; VRAM máx 543 780 864 B; GTT ~12 MB.
- Resultado comparativo: al duplicar iteraciones y multiplicar stride ×16, el throughput cayó
  (fps 2.53 vs 8.08) y la potencia bajó ~0.85 W (13.23 → 12.38 W).
- Los 512 MiB No generaron presión DRAM real: MCLK en piso y mem_busy bajo (R-05: w/s 256 KB por `& 0xFFFF`).

### 6..7. Hipótesis
- (planteada) más memoria + dispersión activa MCLK y sube el draw.
- (estado) RECHAZADA para esta vía de parámetros: la carga siguió limitada por el shader
  (SCLK 1071, mem_busy bajo), no por memoria. El draw NO sube con iteraciones/stride/VRAM por sí solos.

### 8. Metodología experimental
- Igual que E-01 salvo parámetros: `./main --duration 20 --vram 536870912 --iterations 1024 --stride 256 --seed 42`.
- 188 muestras, 10 Hz; fase activa 176 muestras.
- Criterios: mismo que E-01; explícito: si aparecía OOM/device lost/reset → detener y clasificar;
  no se aumentó intensidad automáticamente.

### 9. Resultados y datos
Ver `RESULTADO-EXPLORATORIO-02.md` (tabla comparativa 01 vs 02).

### 10. Limitaciones / qué NO puede concluirse
- La "presión de memoria" fue nominal (VRAM allocada) pero no efectiva (DRAM no usada por el w/s real).
- No se puede concluir nada sobre costo real de banda/memoria en esta placa con estos datos.
- Un solo run por config; sin repetición estadística (aceptable para exploratoria).

### 11/12. Decisión técnica y por qué
- Decisión: no rediseñar todavía; registrar que "más iteraciones + más dispersión" es una vía
  agotada para subir el draw, y que la vía correcta para presión DRAM es ampliar el w/s
  accesible (> L2) eliminando/expandiento la máscara (ver R-05). Ninguna alternativa forzó
  cap/clocks (vetado); pipeline gráfica queda como hipótesis futura (R-04).
- Por qué: la evidencia muestra un cuello de botella de ejecución del shader y no de memoria.

### 13. Contradicciones
- La afirmación genérica de que "carga de memoria genera potencia comparable al compute" se
  retiene como válida SOLO para saturación DRAM real; aquí la DRAM no se saturó → no hay
  contradicción con nuestras mediciones. Si una futura corrida con w/s > L2 mostrara lo contrario,
  se actualizaría este registro.

---

## R-06 — Render back-end, color buffer y compresión DCC (Polaris)

### 1. Pregunta
En un pipeline gráfico, ¿la escritura del color buffer (CB) genera tráfico real hacia
DRAM (necesario para activar MCLK), y qué papel juega la compresión Delta Color
Compression (DCC) de Polaris?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Consultas: `render backend color cache write memory controller bypass L2 render target GCN`;
  `delta color compression DCC GPUOpen color render target`; `radv DCC default color attachment
  GFX8 disable storage GENERAL layout`; `polaris whitepaper render back-end compress color buffer`.
- Priorización: whitepaper oficial de Polaris; documentación y parches upstream de RADV/Mesa
  (lists.freedesktop amd-gfx y mesa-dev, commit de DCC en RADV); análisis de arquitectura con
  perfil real (Chip and Cheese); revisión de Phoronix sobre DCC en RADV. Se contrastaron las
  afirmaciones del whitepaper (marketing: "ahorra 40 % de potencia en transacciones de memoria")
  con el detalle técnico del algoritmo (bloques dinámicos, 8:1) y con el código real de RADV.

### 4. Fuentes (URLs y aporte)
- Whitepaper Polaris: http://zqwzjdq.vgamuseum.info/images/doc/amd/polaris-whitepaper.pdf —
  el render back-end comprime color buffers para ahorrar potencia y ancho de banda; DCC es lossless,
  divide el buffer en bloques de tamaño dinámico según patrones de acceso/datos; pico 8:1 (256 B);
  Polaris es "más agresivo" que gen.3; los shader cores leen y descomprimen transparentemente
  (render-to-texture); el mayor ahorro ocurre cuando el CB se vuelve a leer.
- GPUOpen "Getting the Most Out of DCC": https://gpuopen.com/learn/dcc-overview/ — propiedades de
  DCC en las APIs: usage flags que lo deshabilitan/degradan, interacción con sampleo, métricas y
  micro-benchmarks de bandwidth.
- Chip and Cheese, "GCN, AMD's GPU Architecture Modernization":
  https://chipsandcheese.com/p/gcn-amds-gpu-architecture-modernization — **Tahiti (GCN1)**: los
  exports del pixel shader van a los render backends; cada RB tiene caché de color 16 KB y de
  profundidad 4 KB; "final pixel colors are written to the memory controllers and bypass the L2
  cache"; los RBs están desacoplados de los controladores de memoria. En Vega (GCN5) los RBs se
  colocan delante de la L2 (más bandwidth de escritura).
- Parche RADV "Add DCC support" (ff8b0f6): https://github.com/airlied/mesa/commit/ff8b0f65f5e78da9f8129bf8787eb18a2a51d271 —
  RADV habilita DCC por defecto en color attachments (GFX8+); **deshabilita DCC si** usage incluye
  TRANSFER_SRC/DST o STORAGE, MUTABLE_FORMAT_BIT, tiling LINEAR, chip < VI, o `scanout` (swapchain);
  fast-clear inicialmente restringido.
- Mesa-dev "radv: rename and re-document cache flush flags" (2019):
  https://lists.freedesktop.org/archives/mesa-dev/2019-June/220696.html — en GFX6-8 la L2 sirve a los
  shaders; el CB/DB se invalida con FLUSH_AND_INV_CB/DB aparte (comentario "GFX6-8: used by shaders
  only. GFX9-10: used by everything").
- Documentación RADV: https://kusma.pages.freedesktop.org/mesa/drivers/radv.html — env vars:
  `radv_disable_dcc` (bool, default `false`) desactiva DCC en imágenes de color GFX8–GFX11.5;
  `radv_disable_dcc_mips`, `radv_disable_dcc_stores`, `radv_image_meta_path`.
- Phoronix: https://www.phoronix.com/review/radv-dcc-boost — DCC correcto en RADV = ahorro medible
  de bandwidth en GCN 1.2+.

### 5. Hechos VERIFICADOS
- DCC es compresión lossless de color render targets, presente en Polaris (GCN 1.2+, incl. P12),
  bloques de tamaño dinámico, pico 8:1 (256 B). [VERIFICADO, whitepaper + GPUOpen]
- El propósito de DCC en Polaris es ahorrar **bandwidth y potencia** de memoria: su efecto solo es
  relevante si el CB llega a la interfaz de memoria → evidencia indirecta de que el tráfico del CB
  cuenta para DRAM/consumo. [VERIFICADO como diseño de hardware según whitepaper]
- RADV habilita DCC por defecto para imágenes de color no-scanout en GFX8; lo deshabilitan: usage
  STORAGE/TRANSFER, MUTABLE_FORMAT, LINEAR, `scanout`, y el env `radv_disable_dcc=1`. [VERIFICADO]
- En GFX6-8 la L2 cobija accesos de shaders; el CB/DB se gestiona aparte (flush/inv propia) → el CB
  NO pasa por la L2 como los datos de shader en esta generación. [VERIFICADO, parche mesa-dev]
- La afirmación "el RB escribe a controladores de memoria sin pasar por L2" está documentada para
  **Tahiti (GCN1)**; para Polaris (GCN4, misma familia con RB desacoplado y DCC) se adopta como
  [HIPÓTESIS] hasta medición (ver DESIGN-GRAPHICS, evidencia faltante).

### 6..7. Hipótesis
- H-DCC-entropía: escribir al CB una salida de alta varianza/entropía hace que DCC no comprima → el
  CB sale a DRAM a bandwidth completo → actividad de memoria real (candidata a elevar MCLK).
  [HIPÓTESIS, coherente con el algoritmo de bloques de DCC]
- H-CB-DRAM: en Polaris el tráfico del CB llega a los controladores de memoria (como GCN1) → escribir
  CB es tráfico DRAM adicional (no absorbido por L2). [HIPÓTESIS directa, sin medición]
- Estado: abiertas; requieren un pipeline gráfico (futuro, autorizado).

### 8..13.
- Método propuesto (futuro): medir `mem_busy`/MCLK con CB de alta entropía vs trayectoria DCC off.
- Decisión técnica: usar salida de alta entropía como mecanismo PRINCIPAL para derrotar DCC
  (representativo), con levers de reserva documentados (`VK_IMAGE_USAGE_STORAGE_BIT` / layout
  GENERAL / `radv_disable_dcc=1`).
- Alternativas descartadas: asumir que "más VRAM allocada" activa DRAM (refutado en E-01/E-02).

---

## R-07 — Política DPM de MCLK en smu7 (Polaris): umbrales de actividad

### 1. Pregunta
¿Qué condición hace que MCLK suba desde el piso (300 MHz) en Polaris? ¿Por qué en E-01/E-02 quedó
siempre en piso?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Consultas: `amd-gfx mclk_activity mclk_up_hyst mclk_down_hyst 128-bit Polaris patch`;
  `amdgpu mclk DPM memory activity threshold Polaris`.
- Priorización: parche upstream en la lista amd-gfx (fuente primaria del KMD) contrastado con el
  comportamiento observado en nuestro sistema (E-01/E-02).

### 4. Fuentes (URLs y aporte)
- Lista amd-gfx, parche (sept. 2020):
  https://lists.freedesktop.org/archives/amd-gfx/2020-September/053984.html — ajusta parámetros DPM
  de MCLK en smu7_hwmgr por ancho de bus: para **VRAM 128-bit** (RX 460/550 y afines):
  `mclk_activity = 20`, `mclk_up_hyst = 5`, `mclk_down_hyst = 16`; para 192-bit (RX 470/570):
  `mclk_up_hyst = 10`. La subida de MCLK se decide por actividad de memoria sostenida en ese umbral.

### 5. Hechos VERIFICADOS
- La política DPM de MCLK en Polaris (smu7) eleva MCLK cuando la **actividad de memoria supera ~20 %
  de forma sostenida** (`mclk_activity=20`, caso 128-bit de nuestra placa), con histéresis de subida
  (up_hyst) y bajada (down_hyst). [VERIFICADO, parche upstream]
- Nuestra RX 550 (128-bit) entra exactamente en el caso `mclk_activity=20`.
- Compatible con E-01/E-02: mem_busy 3–7 % < 20 % → MCLK sin incentivo de subir. [VERIFICADO]

### 6..7. Hipótesis
- H-MCLK-umbral: sostener `mem_busy` ≥ ~20 % elevará MCLK por encima del piso (hasta 1500).
  [HIPÓTESIS, soportada por la política DPM; no medida aún]
- Estado: abierta. Es EL mecanismo central para convertir "tráfico DRAM" en draw de MCLK.

### 8..13.
- Método propuesto: cualquier diseño que active banda debe medir mem_busy y nivel MCLK (telemetría
  actual ya registra ambos) y verificar la salida del piso durante la fase activa.
- Decisión técnica: el criterio de validez "presión DRAM real" se define por `mem_busy ≥ 20 %`
  sostenido y/o MCLK > piso (ver DESIGN-GRAPHICS, criterios).
- Alternativas descartadas: forcing de MCLK/`profile_min_mclk` (vetado por regla del proyecto).

---

## R-08 — Límites Vulkan para pipeline gráfico en GFX8/Polaris

### 1. Pregunta
¿Qué límites de Vulkan (resolución máxima, sample counts, attachments, push constants) impone
RADV/GFX8 al diseño del render target, y cómo se hace un fullscreen draw sin buffers?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Consultas: `vulkan.gpuinfo.org RADV POLARIS10 limits`; `fullscreen triangle gl_VertexIndex vulkan
  bufferless`; `maxColorAttachments GFX8 radv`; `MSAA sample counts Polaris GFX8`.
- Priorización: reporte de hardware de vulkan.gpuinfo.org (RADV/POLARIS10), tutorial técnico
  (saschawillems), contrastando el bitmask de sample counts de la base de datos (hasta 64) con el
  máximo físico real para color en GFX6-8 (8 muestras, acorde a whitepaper/DCC y familias GCN).

### 4. Fuentes (URLs y aporte)
- vulkan.gpuinfo.org, reporte RADV POLARIS10 (id=13824): https://vulkan.gpuinfo.org/displayreport.php?id=13824 —
  maxImageDimension2D=16384, maxImageArrayLayers=2048, maxPushConstantsSize=256 B,
  maxSamplerAllocationCount=65536, maxSamplerAnisotropy=16, y bitmask de sample counts para
  framebuffer/sampled con bits hasta 64 (la DB reporta el bitmask; el HW GFX8 en color llega a 8).
- saschawillems.de: https://www.saschawillems.de/blog/2016/08/13/vulkan-tutorial-on-rendering-a-fullscreen-quad-without-buffers/ —
  técnica **bufferless fullscreen triangle**: 3 invocaciones de vertex shader, UV derivadas de
  `gl_VertexIndex`, sin vertex buffers; clásico para post-processing/fullscreen.

### 5. Hechos VERIFICADOS
- El fullscreen triangle bufferless (3 índices de vértice, UV de `gl_VertexIndex`) es una técnica
  válida y estándar sin buffers. [VERIFICADO, tutorial]
- RADV en GFX8 reporta límites amplios: imagen 2D 16384 px, 2048 capas, 256 B push constants,
  16 máximo de anisotropía, 65536 samplers. [VERIFICADO, reporte POLARIS10; familia GFX8 = P12,
  pendiente confirmación en runtime]
- Sample counts para CB de color en GFX8: el máximo físico es 8 (el bitmask de la DB llega a 64
  pero refleja el rango del reporte, no capacidades por formato). [HIPÓTESIS; se verifica con
  `vkGetPhysicalDeviceFormatProperties` en el binario final]

### 6..7. Hipótesis
- H-MSAA: MSAA 4x/8x viable como eje multiplicador de trabajo (fill + ROP + CB escribiendo N
  muestras); si RADV no aplica DCC a MSAA por defecto, un CB con MSAA escribe a bandwidth completo
  → favorece nuestros objetivos. [HIPÓTESIS, ver runtime]
- Estado: abierta; se verifica además sampleShadingEnable para no perder nitidez de diseño.

### 8..13.
- Decisión técnica: resolución 1920×1080 (holgada vs 16384), formato R8G8B8A8_UNORM (compatible
  DCC para el eje de entropía), MSAA como eje opcional 1x/2x/4x/8x con verificación runtime de
  `framebufferColorSampleCounts`; params por push constant (máx 256 B); draw sin vertex buffers.
- Alternativas descartadas: swapchain/presentación (scanout deshabilita DCC y añade riesgo de
  present/hang); mayores a 1080p en primera fase (no aporta y sube el riesgo de OOM con MSAA).

---

## R-09 — Qué subsistemas activa cada pipeline: evidencia de draw (gráfica vs compute)

### 1. Pregunta
¿Qué unidades adicionales activa un pipeline gráfico frente al compute del prototipo, y qué
evidencia (local y externa) hay de que eso produce más draw en esta placa?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Correlación de la investigación previa (R-01..R-08, R-04) con los registros de draw locales de la
  sesión actual (MASTER-PLAN, evidence.md) y los datos de benchmarks "reales" ejecutados sobre esta
  placa (GravityMark, Superposition).
- Consultas: sin nuevas; se consolida lo ya investigado y medido en el sistema.

### 4. Fuentes (URLs y aporte)
- MASTER-PLAN.md (§_histórico, línea 122): régimen actual observado: **Superposition motor
  18.8–23.7 W** (1600x900/Medium, sin reset) y **GravityMark 12.4–14.8 W**; compute propio E-01/E-02
  13.2/12.4 W.
- evidence.md: "Clocks en carga: SCLK 1071, MCLK 625 (picos 1500 transitorios); MCLK idle 300".
- R-04 (computergraphics.SE): la ventaja de fragment vs compute es de coherencia de empaquetado, no
  de HW distinto; fill-rate/overdraw/MSAA estresan el render back-end (Geeks3D).
- Whitepaper Polaris (Anexo A, URL 6): el geometry engine cachea mallas para instancing (menos
  tráfico L2); el render back-end comprime color (R-06).

### 5. Hechos VERIFICADOS
- Sobre ESTA placa, el draw máximo de la sesión actual provino de un benchmark GRÁFICO
  (Superposition: pico 23.7 W) muy por encima de compute propio (13.2 W) y de GL ligero (14.8 W).
  [VERIFICADO, MASTER-PLAN]
- El compute puro satura SCLK 1071 pero no presiona memoria (MCLK piso) ni render back-end
  (E-01/E-02). [VERIFICADO]
- Diferencia estructural: fragment/ROPs/texturas (ruta gráfica) son exactamente los subsistemas que
  Superposition ejercita y que produjeron el draw más alto registrado en esta placa. [VERIFICADO por
  correlación; no por causa aislada]

### 6..7. Hipótesis
- H-gfx: un pipeline gráfico con fragment pesado + CB de alta entropía + texturas grandes > L2 +
  overdraw/MSAA podría sostener draw ≥ 27 W con cap=35 W activando SCLK (1071) Y memoria (1500).
  [HIPÓTESIS central de diseño; NO garantizada]
- Tope conocido: la mejor carga "real" (Superposition) alcanzó ~23.7 W pico; el objetivo 27 W
  sostenido exige superar ese techo con sobrecarga determinista (overdraw/MSAA/entropía de CB).
  El régimen histórico [NO REPRODUCIBLE] llegó a 25–31 W con MCLK 1250–1500 y SCLK bajo; con SCLK
  1071 y MCLK 1500 simultáneos el draw resultado es incierto pero plausiblemente dentro del rango.
- Estado: abierta.

### 8..13.
- Decisión técnica: avanzar al diseño comparativo de ≥2 diseños (compute+texturas vs gráfica
  fullscreen) en `DESIGN-GRAPHICS.md`, con criterios de validez y ejes experimentales definidos,
  SIN ejecutar nada en esta fase.
- Alternativas descartadas: asumir que basta "más compute ALU" (E-01/E-02 lo refutan); forcing de
  clocks (vetado); usar benchmarks de terceros como candidatos (fuera del alcance de workload propio).

---

## R-10 — Verificación en runtime del workload gráfico (smoke run, no exploratoria)

### 1. Pregunta
¿El binario `main-graphics` (Diseño B) compila sin warnings, valida los 3 shaders, selecciona físicamente
la RX 550, crea recursos dentro del presupuesto VRAM y termina sin device lost / OOM / hang?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- `make main-graphics` con `-O2 -std=c++17 -Wall -Wextra` (CXX=g++ 16.2.1); shaders estáticos con
  `glslangValidator -V --target-env vulkan1.1` (vertex/fragment/gen: validan sin error).
- Smoke run controlado (config mínima de desarrollo, NO la exploratoria): `main-graphics
  --width 640 --height 480 --tex-size 512 --warmup 1 --duration 1` con
  `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json MESA_VK_DEVICE_SELECT=1002:699f`.

### 4. Fuentes (URLs y aporte)
- Ninguna consulta externa nueva; verificación empírica local del propio binario.

### 5. Hechos VERIFICADOS
- Compila sin warnings con `-Wall -Wextra` (0 avisos tras limpiar `fragBind[0]` y `t0` muerto). [VERIFICADO]
- Los 3 shaders validan con glslangValidator target vulkan1.1; layout push constant del fragment
  coincide con `struct PCFrag` (28 B: res.uvec2, seed.uvec2, layer, numTextures, fmaIters). [VERIFICADO]
- El binario selecciona la RX 550: `device: AMD Radeon RX 550 / 550 Series (RADV POLARIS12)
  vendor=0x1002 device=0x699F driver=0x06802002`. [VERIFICADO]
- Capacidades en runtime (R-08 confirmado en máquina real): `sample_counts_cb=15` (=MSAA hasta 8x),
  `max_image_dim=16384`, `max_mip=15`, `max_layers=2048`; format RGBA8_UNORM con attach/sampled/storage. [VERIFICADO]
- Presupuesto VRAM: heap device-local reportado por RADV = 1879048192 B (1.75 GiB de los 2 GiB físicos);
  el smoke run reservó 5 MiB en imágenes. Sin exceder heap → no hubo aborto de presupuesto. [VERIFICADO]
- Sync/lifecycle: setup (2 submits + barriers) y loop con fence 10 s; terminó exit=0 sin timeout ni
  device lost ni OOM. Smoke: warmup 66 frames + measure 70 frames @ 70 fps (config mínima;
  reporte determinista completo en stdout). [VERIFICADO, smoke run]
- Regla de seguridad activa: si `totalVram > heapSize` aborta con código 5 (presupuesto); device lost → 2;
  OOM → 4; timeouts de fence → 3.

### 6..7. Hipótesis
- H-aplicable: con la configuración base (1920x1080, 4 capas, 4 texturas 4096², 24 FMA, warmup 5 s +
  duración 20 s) la reserva VRAM sería 4×64 MiB texturas + ~8 MiB CB ≈ 264 MiB, muy por debajo del
  heap 1.75 GiB → sin riesgo de OOM ni de aborto de presupuesto. [PARCIALMENTE VERIFICADO: se calculará
  en la corrida exploratoria; el smoke confirma el mecanismo de reserva]
- Estado: abierta hasta la corrida exploratoria.

### 8..13.
- Decisión técnica: declarar la fase de implementación (Diseño B) FUNCIONAL y proceder a UNA corrida
  exploratoria controlada con la configuración base exacta de `DESIGN-GRAPHICS.md`, con telemetría
  pre/post-flight y journal, sin cambiar ningún parámetro salvo fallo de validez/seguridad.
- Registros asociados: `DESIGN-GRAPHICS.md` (spec), `src/graphics.cpp`, `src/vertex.vert`,
  `src/fragment.frag`, `src/gen.comp`, `Makefile` (target `main-graphics`; binario `main` de E-01/E-02
  intacto).

---

## R-11 — Storage IMAGES en GFX8/RADV: VM faults deterministas y corrección por upload host

### 1. Pregunta
¿Por qué el generador compute de texturas (`gen.comp`, 4 storage images) provocaba VM faults
deterministas de amdgpu en la RX 550, y cómo eliminar el riesgo sin tocar la configuración del sistema?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Bisección con flags de depuración del binario: `--skip-gen` (solo fragment) y `--skip-frag` (solo
  generación), correlacionando con `journalctl` (grep `GPU fault|VM fault`).
- Variantes de codegen del generador: descriptor array corregido (binding 0, count=4),
  `RADV_DEBUG=nodcc`, y driconf temporal en HOME aislado (`/tmp/opencode/fakehome/.drirc`) con
  `radv_disable_shrink_image_store=true` y `radv_wait_for_vm_map_updates=true` (opciones documentadas
  en `/usr/share/drirc.d/00-radv-defaults.conf`).

### 4. Fuentes (URLs y aporte)
- `/usr/share/drirc.d/00-radv-defaults.conf` en este sistema: `radv_disable_shrink_image_store`
  (workaround de The Surge 2 / World War Z) y `radv_wait_for_vm_map_updates` (workaround de Forza) →
  ambos son workarounds de RADV para bugs de GFX8.
- R-06/R-07 (Anexo A): CB/DB sin L2 en GFX6–8 y L2 solo para shaders; los imageStore a storage images
  delinquen en el camino de memoria de Polaris.

### 5. Hechos VERIFICADOS
- El fault es determinista y del camino storage-image: `--skip-frag` (compute + imageStore) → 1–4 VM
  faults; `--skip-gen` (solo fragment) → 0 faults. [VERIFICADO]
- Páginas faultadas fijas entre runs: 774082 (TC3, read 4 B) y 482455 (TC2, 8 B) SIEMPRE; 208283
  (TC1, 68 B) y 47788 (TC0, 72 B) según ruido; lecturas desde TC en el primer segundo del run; sin
  hang/reset (exit 0, DPM intacto pre==post). [VERIFICADO]
- `compute.comp` (storage BUFFER) de E-02 jamás faultó → problema específico de storage IMAGE en GFX8.
  [VERIFICADO]
- Descartados: descriptor array (binding 0 count=4) → persiste; `RADV_DEBUG=nodcc` → persiste;
  `radv_wait_for_vm_map_updates` → sin efecto concluyente; `radv_disable_shrink_image_store` → reduce
  4→2 faults pero no los elimina. [VERIFICADO]
- Solución por diseño: eliminar el compute/storage-image y llenar las texturas en HOST (misma familia
  de hash `hash32` que el fragment shader), subidas con `vkCmdCopyBufferToImage` (texturas con usage
  `SAMPLED|TRANSFER_DST`). Resultado: 0 faults en smoke (512²), gen-only y en la corrida base completa
  (4096²). [VERIFICADO]

### 6..7. Hipótesis
- H-fault: los imageStore de RADV/GFX8 a storage images rozan direcciones bajo DCC/shrink que el VM del
  kernel no tiene mapeadas (clase de bug que esos driconf trabajan). [SUSTENTADA por patrones de
  páginas y workarounds]
- H-solucion: el sampleo del fragment (única fuente de presión) basta para la memoria; la generación
  host no computa en GPU (costo único ~1 s al inicio, fuera de la ventana de medición). [VERIFICADO en E-03]

### 8..13.
- Decisión técnica: el Diseño B conserva su arquitectura gráfica; SOLO el generador de texturas se
  mueve al host. `gen.comp` queda como referencia (no compilado en `main-graphics`).
- Registros asociados: `src/graphics.cpp` (bloque de upload), `src/gen.comp` (referencia), R-11 y E-03
  en este RESEARCH.

---

## E-03 — Corrida exploratoria 03 (Diseño B, configuración base) — REQUIERE CORRECCIÓN → re-ejecución VÁLIDA

### 1. Pregunta
Con la configuración base exacta de `DESIGN-GRAPHICS.md` (1920x1080, 4 capas, 4 texturas 4096², 24 FMA,
warmup 5 s, duration 20 s), ¿el workload gráfico termina sin fallos y qué telemetría produce (power,
busy, DPM, VRAM) para discriminar 35 W vs 30 W?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Corrida 1 (tainted): binario pre-corrección (generador compute storage-image); exit 0 y `result:
  EJECUCIÓN_VÁLIDA` PERO con VM faults en `journalctl` → clasificada REQUIERE CORRECCIÓN.
- Investigación y corrección del generador (ver R-11) y re-ejecución de la MISMA configuración base con
  `main-graphics` corregido (sin tocar ningún parámetro).
- Telemetría `experiments/EXPLORATORIO-GravityMark/telemetria.sh` (10 Hz, 32 s) + pre/post-flight
  (DPM sclk/mclk, busy, vram/gtt, power, temp) + journal. Artefactos en
  `runs/exploratorio-03-corrected/{stdout.txt,stderr.txt,telemetria.csv,pre_flight.txt,post_flight.txt,journal_pres.txt}`;
  corrida tainted en `runs/exploratorio-03/` (evidencia conservada).

### 5. Hechos VERIFICADOS
- Identificación computacional entre corrida tainted y corregida: misma config, mismos FPS 8.950, mismo
  nº de frames (warmup 45, measure 179), misma reserva de imágenes 277,317,656 B y frametime ~112 ms →
  la corrida corregida es la MISMA carga, ahora sin faults. [VERIFICADO]
- 0 líneas de `GPU fault|VM fault` en el rango del journal de la corrida corregida. [VERIFICADO]
- Telemetría (277 muestras): power avg 13.40 W (min 3.38 W piso idle, máx 15.81 W), temp avg 51.1 °C,
  gpu_busy avg 80 % (100 % en régimen; el promedio incluye el arranque), mem_busy avg 28.6 % (36–49 %
  en régimen), SCLK 1071 MHz en 223/277 muestras, MCLK **1500 MHz en 220/277** (la DRAM se activó),
  vram_used avg 234.9 MB, gtt_used avg 232.5 MB (staging de 256 MiB). [VERIFICADO]
- DPM y sensores intactos: pre_flight == post_flight (estado `0: 214Mhz *`, `0: 300Mhz *`, busy=0,
  vram=5.4 MB, gtt=11.2 MB), sin resets ni timeouts. [VERIFICADO]

### 6..7. Hipótesis
- H-gfx: el fragment (CB de alta entropía + sampleo incoherente de 4×64 MiB de texturas + overdraw 4x)
  es la fuente de presión; sostiene SCLK 1071 y activa MCLK 1500 con mem_busy 36–49 % en régimen.
  [SUSTENTADA]
- H-draw: el techo gráfico de esta placa con cap 35 W sigue siendo ~18.8/23.7 W (Superposition); este
  workload llega a 13.4 W avg / 15.8 W pico → AÚN NO discrimina 35 vs 30 W. [VERIFICADO como límite]
- Estado: el workload queda VÁLIDO para exploración de parámetros futura (en otra fase autorizada);
  el rol EXPLORATORIO actual (UNA corrida) queda cumplido y cerrado.

### 10. Limitaciones / qué NO puede concluirse
- Causa raíz EXACTA del fault de RADV (archivo de kernel) no identificada; se circunvaló por diseño.
- La presión DRAM real (w/s ≥ 112 GB/s) todavía no se midió; mem_busy 36–49 % no implica saturación.
- gtt_used 232 MB corresponde al staging host (fuera de la ventana de rendimiento, pero parte del draw).

### 11/12. Decisión técnica y por qué
- Aceptar la corrida corregida como la E-03 oficial (misma config; el fix corrige un bug de VALIDEZ de
  la implementación, permitido). Clasificación final: **VÁLIDA**.
- No forzar clocks ni subir la cap (política: solo lectura del hardware) → para empujar hacia 27–35 W
  se escalarán parámetros del WORKLOAD en otra fase autorizada (overdraw/MSAA/fma/tex-size).

### 13. Contradicciones
- La corrida tainted reportó `result: EJECUCIÓN_VÁLIDA` pese a tener VM faults en journal: el criterio
  del binario (exit 0 + fences OK) NO detecta faults VM del kernel → nueva regla de validación: toda
  corrida futura DEBE verificar journal (0 `GPU fault|VM fault`) además del exit code. [REGLAMENTO NUEVO]

---

## R-12 — Bases del escalado controlado: qué eje presiona cada subsistema (GFX8/BX 550)

### 1. Pregunta
¿Qué dimensión del workload (overdraw, FMA, textura, MSAA) está técnicamente mejor fundamentada
para aumentar la demanda real de la RX 550 (presión DRAM/ROP/ALU) y en qué orden probarla?

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Websearch/webfetch (fuentes abajo) + arquitectura ya registrada en R-02/R-05/R-06/R-07.
- Revisión del shader (`fragment.frag`): muestreo con UV = hash(gl_FragCoord, capa, semillas) ∈ [0,1)
  normalizado, independiente de `texSize`; FMA = `fmaIters × 6`; salida hash por píxel/capa.

### 4. Fuentes (URLs y aporte)
- https://www.rastergrid.com/blog/gpu-tech/2021/10/multisampling-primer/ — en MSAA básico el
  fragment shader se ejecuta UNA vez por píxel (SHS=1) pero el CB almacena N muestras (CCS=N): la
  operación de blend/ROP es por muestra; sin deduplicación (sin DCC) son N escrituras.
- https://docs.vulkan.org/samples/latest/samples/performance/msaa/README.html — MSAA almacenado y
  releído multiplica la banda del attachment por N (p.ej. 4x ≈ 4× los bytes); el almacenado en
  memoria principal es el camino caro.
- lists.freedesktop.org/archives/mesa-dev/2018-November/209606.html — RADV NO habilita DCC para
  MSAA 4x/8x por defecto (`radv_image_can_enable_dcc`: samples ≥ 2 requiere `dcc_msaa_allowed`).
- https://www.igorslab.de/en/performance-benchmark-power-consumption-rx550-polaris/ — P12: 512 KB L2
  (P11 tiene 1 MB); boost real 1141–1164 MHz con PowerTune.
- GCN-primer (Anexo A R-05/R-06): el CB de GFX8 bypassa L2 (color cache del RBE → controladores de
  memoria); sobrecarga del RBE escala con blending/MSAA. Ops full-rate FP32.

### 5. Hechos VERIFICADOS / razonamientos
- OVERDRAW (layers): cada capa redibuja el fullscreen con blending ONE/ONE → RMW del CB por capa
  (N× lecturas+escrituras al mismo CB de 8.3 MiB) + N× invocaciones de fragment + N× muestreos de
  textura. Presiona simultáneamente ROP/CB y fragment. [SUSTENTADO por diseño del loop §605–649]
- FMA: sube VALU (full-rate FP32); si el shader ya espera por texel (memoria), el efecto puede ser
  bajo (ocultamiento de latencia); depende del cuello de botella real. [HIPÓTESIS]
- TEX-SIZE: el patrón de muestreo es uniforme-aleatorio normalizado; el footprint por frame es
  proporcional al nº de texels distintos tocados → con 4×8192² (1.07 GiB) el footprint crece 4×
  respecto de 4096² (57 MiB vs 14 MB a 112 GB/s de banda disponible); el L2 de 512 KB no retiene el
  working set. Si el muestreo es determinista, la SET tocada es la misma cada frame → estimulo de
  cache/DRAM limitado a la "barrida" por frame. [HIPÓTESIS]
- MSAA 8x: SHS=1 (fragment no cambia) pero CCS=8 → ROP escribe 8 muestras/píxel al CB; RADV sin DCC
  para MSAA → escrituras sin comprimir a DRAM (bypass L2 en GFX8). CB de 1920×1080×8 ≈ 66 MiB.
  Implementado como `--msaa 1|2|4|8` (validado contra `sampleCounts`; smoke 640×480 @8x sin faults,
  images_bytes 15.99 MiB). [VERIFICADO el soporte; SUSTENTADA la presión por banda]

### 6..7. Hipótesis de escalado
- Orden de prueba (una variable por corrida, config BASE fija): A) layers 8→16; B) fma-iters 8→16
  (48→96 FMA); C) tex-size 6144→8192 (footprint de 4 tex); D) msaa 4→8. Luego solo COMBINAR el eje
  que más mueva power/mem_busy.
- Objetivo de screening: identificar el eje que más sube `power_avg`/`mem_busy`/MCLK sostenido, NO
  significancia estadística (1 corrida por configuración).

### 8..13.
- Decisión técnica: usar siempre la telemetría de referencia (10 Hz, 32 s), pre/post-flight de DPM,
  journal filtrado (0 `GPU fault|VM fault`) y aborto disciplinado ante cualquier signo de inestabilidad.
- Criterio de clasificación por eje (ver `ESCALADO-E03.md` §Decisión): EFECTIVO / POCO EFECTIVO /
  SIN EFECTO / INESTABLE / DESCARTADO según Δpower, Δmem_busy, ΔMCLK y estabilidad.

---

## ES-01 — Fase de escalado controlado (screening de ejes sobre BASE E-03)

### 1. Pregunta
¿Cuál de los ejes A-D (overdraw, FMA, tex-size, MSAA), y la combinación E1, sube de forma
significativa la potencia sostenida de la RX 550 sobre el BASE E-03 (~13.4 W ventana / ~15.8 W
régimen)? Objetivo: elegir UNA configuración prometedora para una segunda fase. NO es un A/B 35 vs
30 W (vetado hasta identificar una carga que suba el draw).

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- 10 corridas UNA-sola-vez por configuración (screening, sin significancia; regla del dueño),
  misma resolución 1920×1080, warmup 5 s, duration 20 s, selección explícita RX 550.
- Runner reutilizable `/tmp/opencode/run_variant.sh` (pre/post-flight DPM, telemetría 10 Hz 34 s,
  journal `GPU fault|VM fault`); artefactos en `runs/escalado-01/<variante>/`; resumen completo en
  `ESCALADO-E03.md`.
- Indicador: régimen estable = filas con `gpu_busy ≥ 95`, SCLK nivel 7 (1071) y MCLK 1500; se
  compara power_avg/max, mem_busy, fps, frametime, vram.
- Control de deriva térmica: se re-ejecutó BASE al FINAL de la sesión (A0-base-reeval) → deriva
  ambiental medida: BASE inicio 15.75 W vs BASE final 16.08 W = ±0.33 W que enmascara Δ < ~0.4 W.

### 4. Fuentes (URLs y aporte)
- Ver R-12 (Anexo A, URLs 29–32) y R-06/R-07/R-11: MSAA SHS=1/CCS=N, RADV sin DCC para MSAA,
  DPM MCLK ≥20 % de actividad, colección de faults storage-image.

### 5. Hechos VERIFICADOS (régimen estable)
- BASE (inicio) 15.75 W; A1 layers8 15.76 W (fps 4.50, frametime 222.8 ms); A2 layers16 15.78 W
  (fps 2.30, frametime 442.5 ms): overdraw escala el frametime EXACTAMENTE lineal (1×/2×/4×) PERO no
  sube potencia (el GPU ya está al 100 % busy con SCLK 1071 fijo → work/s constante → W constante).
- B1 FMA48 15.94 W / B2 FMA96 16.18 W: fps TRUNCADO a 8.95 (el bucle de FMA, con dependencias
  largas, queda oculto tras la latencia de sampleo) y Δ dentro de la deriva térmica. SIN EFECTO.
- C1 tex6144 16.01 W / C2 tex8192 16.09 W: fps 8.95 sin cambio y mem_busy clavada 35.9 % (el
  patrón de muestreo normalizado es fijo → nº de fetches/frame constante; el footprint crece pero no
  desplaza DRAM). SIN EFECTO. vram real 584 MiB → 1.03 GiB (sin OOM).
- D1 MSAA4 15.94 W / D2 MSAA8 16.11 W (fps 8.90–8.95, frametime 112.3–112.5 ms): el MSAA NO
  amplificó el CB: el triángulo fullscreen cubre TODAS las muestras con el MISMO color
  (deduplicación hardware/DCC) → no 8× escrituras. SIN EFECTO (refuta la expectativa de R-12/MSAA).
- E1 (FMA96+tex8192+MSAA8) 16.17 W, fps 8.90: igual que la deriva → SIN EFECTO aditivo.
- A0-base-reeval (BASE al final de sesión) 16.08 W → mis comparaciones deben anclarse al momento
  térmico correcto; TODS las variantes están en 15.75–16.2 W y mem_busy 35.9–36.0 %.
- Estabilidad: 10/10 exit 0, 0 `GPU fault|VM fault`, DPM restaurado pre==post (sclk 214/mclk 300);
  ninguna temperatura anómala (máx ~67 °C interior), sin resets ni device lost.

### 6..7. Hipótesis
- (planteada) los ejes A-D subirían power/mem_busy/MCLK por encima de BASE.
- (estado) RECHAZADA para este espacio de parámetros en 1 corrida/eje: la placa opera en un
  **equilibrio de latencia** (SCLK 1071 fijo, ALU no saturada de throughput, mem_busy ~36 %), no de
  throughput: añadir trabajo por frame baja FPS pero no sube W. Única palanca restante: cambiar la
  ESTRUCTURA del fragment (acumuladores FMA independientes para subir IPC; más fetches por fragmento;
  per-sample shading con VALOR distinto por muestra para MSAA no deduplicable) + pasar a fase 2.

### 8..13.
- Decisión técnica: seleccionar **FMA 96 + tex 8192 + MSAA 8x** como única config candidata (máxima
  tendencia central 16.17 W, dentro del ruido) para la fase 2, condicionada a la hipótesis
  estructural del §6. NO se declara alcanzable 27–35 W (sigue HIPÓTESIS; ver ESCALADO-E03.md §6).
- Clasificación de ejes: A/B/C/D/E = **SIN EFECTO** en potencia (estables). Ninguno DESCARTAD por
  fallo; descartados como vía para subir W dentro de este diseño de shader.
- Alternativas descartadas: escalar más allá de 8192² el tex-size (mem_busy no se mueve),
  MSAA como amplificador de banda sin per-sample shading, resolver resolución (fijada por regla).
- Regla cumplida: 1 variable por corrida salvo la COMBINACIÓN E1 (etapa E explícita tras elegir el
  mejor eje individual); screening terminado y DETENIDO antes de cualquier A/B 35 vs 30 W.

---

## R-13 — FASE 2: investigación estructural del fragment shader (qué sube el trabajo REAL por fragmento)

### 1. Pregunta
En la RX 550 (GFX8/Polaris12, RADV), ¿qué cambios de ESTRUCTURA del fragment shader aumentan el
trabajo efectivo por fragmento (y la presión sobre unidades reales) — y no solo el frametime —
dado que ES-01 mostró que overdraw/FMA/tex-size/MSAA-idéntico NO mueven `power_avg` ni `mem_busy`?
Pasos exigidos por el dueño: (1) fragment throughput GFX8, (2) dependencias FMA / ILP / ocupación /
presión de registros, (3) coste de fetches de textura, (4) fragment vs per-sample shading vs MSAA,
(5) branching/divergencia, (6) localidad baja, (7) registros↔ocupación↔throughput, (8) mecanismos de
trabajo real sin alargar solo duración.

### 2. Fecha
2026-09-21.

### 3. Metodología de investigación
- Websearch/webfetch priorizando fuentes primarias/upstream: whitepaper Polaris (AMD/RealWorldTech),
  GCN whitepaper (AMD/RealWorldTech), GPUOpen (GDC "Advanced Shader Programming on GCN"; "Understanding
  Memory Coalescing on GCN"; GCN ISA rev1.1), Mesa (src/amd/compiler README-ISA), LLVM AMDGPU
  (GCNSchedStrategy), ORNL intro a presión de registros, blog de Bart Wronski (latency hiding/ocupación),
  AMD "Engine Optimization Hot Lap" (Vega, perfil de latencias), Khronos (sampleShadingEnable +
  fragmentShadingRate), parche RADV "enable sample shading" (mesa-dev 2016).
- Re-inspección del código real (`graphics.cpp` loop, `fragment.frag`) para anclar el modelo a lo que se
  mide: frametime = tiempo GPU por frame (submit→fence), 4 capas, 4 texturas, UV = hash(gl_FragCoord).

### 4. Fuentes (URLs y aporte)
- Whitepaper Polaris (Anexo A, URL 6): GCN consistente, 8 CUs P12, más reloj gating fino.
- GCN whitepaper (Anexo A, URL 21 + techpowerup.com/gpu-specs/docs/amd-gcn1-architecture.pdf): CU = 4
  SIMD × 16 lanes, ondas de 64 threads (4 ciclos/inst/lane-rate), 10 slots/onda por SIMD, hasta 5
  issues/ciclo de threads distintos; 40 ondas/CU; 16 KB V$ por CU, 256 VGPRs/lane; L1D 16 KB x CU.
- GPUOpen "Understanding Memory Coalescing on GCN" (gpuopen.com/learn/gcn-memory-coalescing/): 1 unidad
  TEX por CU; fetch filtrado de 128 bits = **64 ciclos/onda** (point-sampled 128-bit = 16 ciclos);
  filtrado 64-bit = 32 ciclos; 32-bit filtrado = 16 ciclos; los accesos de imagen se agrupan por quads.
- GPUOpen "Advanced Shader Programming on GCN" (GDC2017): **"the GPU is often VALU idle = huge untapped
  capacity"**; la VMEM sufre "memory bubbles" por miss de L1/L2 → mantener la cola de VMEM llena;
  el esquema de issue multi-unidad exige alta ocupación; wave launch: misas de I$/K$ suman latencia.
- AMD "Engine Optimization Hot Lap" (_slides_ Vega): latencias típicas VMEM ~114 ciclos L1-hit,
  ~190 L2-hit, ~350 L2-miss. Nuestro muestreo aleatorio = casi siempre miss L1+L2 → ~350 ciclos/fetch.
- Bart Wronski (bartwronski.com/2014/03/27/gcn-two-ways-of-latency-hiding-and-wave-occupancy/): dos
  formas de ocultar latencia: (a) ILP (ALU independientes entre fetches, más registros) y (b) más ondas
  residentes (ocupa registros bajos). Para "muchas texturas independientes + ALU moderada", baja
  ocupación + alto unroll funciona; demasiada ocupación puede thrash las caches cuando hay mucha banda.
- ORNL "Intro to register pressure" (olcf.ornl.gov/...Intro_Register_pressure_ORNL_20220812): tabla
  VGPR↔ocupación (≤64 VGPR → 8 ondas/SIMD; ≤128 → 4; ≤256 → 2); ILP y ocupación compiten: más ILP =
  más registros = menos ondas. Spilling NO siempre malo; a veces mejora el tiempo.
- LLVM GCNSchedStrategy (llvm-project, src): el scheduler AMDGPU balancea explícitamente ocupación vs
  latencia/ILP con "Critical" register limits (ej. `-amdgpu-schedule-metric-bias`).
- GCN ISA (Anexo A: gpuopen.com/download/AMD_GCN3_ISA...): divergence = para o grabar EXEC; si EXEC=0 el
  HW NO optimiza y ejecuta igual (waste de issue); usar VSKIP/branch. Divergencia multiplica el
  nº de paths ejecutados (fuentes NVIDIA: lineal en k; predication recupera). Nuestro shader: sin branche.
- Khronos (docs.vulkan.org .../VkPipelineMultisampleStateCreateInfo.html): sampleShadingEnable +
  minSampleShading [0,1]; feature `sampleRateShading` obligatorio; VK_KHR_fragment_shading_rate solo si
  se requiere (no). Mesa-dev parche 2016: **RADV habilita `sampleRateShading` en GFX8**; RADV calcula
  `ps_iter_samples = rasterizationSamples × minSampleShading` → per-sample shading REAL disponible.
- Mesa README-ISA (fossies src/amd/compiler/README-ISA.md): GFX8 GFX9: la dirección de VMEM se lee
  immediatamente; los resultados requieren `s_waitcnt` explícitos (latencia no libre).

### 5. Hechos VERIFICADOS (para GFX8/P12) y modelo de cuello de botella
- El cuello de botella del E-01..ES-01 NO es ALU (FMA 24→96 no tocó frametime) ni DRAM (mem_busy 36 %)
  ni CB (MSAA no deduplicado). Es el **camino fetch→uso**: cada fragmento emite 4 fetches dependientes
  de hash (miss garantizado de L1/L2, ~350 ciclos DRAM) y los consume en cadenas semiseriales → la
  cola VMEM se drena y aparecen "memory bubbles". [SUSTENTADO por hechos locales + fuentes GPUOpen]
- ALU/VALU está ENORMEmente infrautilizada (el recurso no crítico); el fetch-heavy es la única vía que
  toca el límite real y que además puede subir `mem_busy` (hoy 36 %, no saturado). [SUSTENTADO]
- Costes por fetch (P12, 1 TEX/CU, 8 CU): filtrado 128-bit = 64 ciclos/onda; con 4 fetches/fragmento
  el TEX unit NO es el límite tampoco (ver §6): el límite es latencia/cola, no throughput del TEX.
- ILP: 8 cadenas independientes por fragmento ocultan mejor la latencia de 8 fetches sin necesitar
  más ondas; aumento moderado de VGPRs (~+16-24) baja ocupación ≤64→≤80... tabla ORNL ○ o se va 8→6
  ondas/SIMD: tradeo aceptable (Bart: caso "muchas lecturas independientes").
- Per-sample shading SÍ está soportado en RADV/GFX8 (`sampleRateShading`=true desde 2016;
  `ps_iter_samples` calculado por el driver); con MSAA 8 + minSampleShading=1 el FS corre 1×/muestra.
  Pero multiplica invocaciones = frametime ~lineal (clase de efecto ya vista, ES-01 eje A) → NO se
  elige como la modificación única; se documenta para fase 3 si hace falta.
- Divergencia en GFX8: ejecución por EXEC mask; ramas divergentes = ambos lados pagados (issue serial)
  → nuestro shader debe mantenerse sin branch (el nuevo diseño lo es). [SUSTENTADO, GCN ISA]
- Localidad baja (UV = hash de gl_FragCoord): ya implementado en E1; se conserva (todas las muestras
  siguen yendo a DRAM; el cambio de tamaño de textura no mueve mem_busy porque el Nº de fetches no
  cambió — el mecanismo correcto es AUMENTAR EL Nº DE FETCHES por fragmento).

### 6..7. Hipótesis y decisión
- H-F2 (HIPÓTESIS de fase 2): un fragment que emita **8 fetches independientes realmente consumidos**
  (+ 8 acumuladores FMA independientes, salida de entropía dependiente de TODOS) duplica el trabajo de
  memoria por fragmento y el ILP → debe levantar `mem_busy` y `power_avg` vs E1, o al menos demostrar
  el efecto en frametime sin tocar ALU-solo. Es la ÚNICA modificación estructural; mantiene countos
  pixel, resolución, capas, texturas, msaa, duración, seeds y cap inmutados.
- DECISIÓN: implementar `fragment2.frag` (muestreo 8× + 8 cadenas ILP) como modificación única,
  seleccionable con `--frag src/fragment2.frag`; `fragment.frag` queda intacto (E1 reproducible).
- NO se eligen ahora: per-sample shading real (multiplica invocaciones, efecto tipo-overdraw; requisito
  estado pipeline + feature), branching (el shader queda sin branch), loops enormes (fijo: 8 fetches +
  bucle de `fmaIters` con 8 cuerpos paralelos), OOM (VRAM idéntica a E1).

### 8..13.
- Método experimental: E1 (baseline intacto, `runs/escalado-01/E1-comb-fma96-tex8192-msaa8`) vs
  F2 = E1 + `--frag src/fragment2.frag`, MISMA CLI (fma-iters 16, tex-size 8192, msaa 8, 1920×1080,
  warmup 5, duration 20) y MISMA telemetría (runner). 1 corrida cada uno.
- Criterio de validez: exit 0 + 0 `GPU fault|VM fault` + DPM restaurado pre==post. Si VM fault/reset/
  device lost/OOM → detener y documentar.
- Clasificación (vs E1): AUMENTO REAL DE CARGA / SIN CAMBIO / MENOR EFICIENCIA / INESTABLE / DESCARTADO.
- Incertidumbres que limitan el modelo: latencia exacta de fetch en P12 (datos ~Vega); ocupación real
  (VGPRs post-llvm); rpm del TEX; por eso la corrida F2 es protocolo, no predicción perfecta.

---

## F2 — Corrida de fase 2 (modificación estructural: muestreo 8× + ILP), resultado

### 1. Pregunta
Tras R-13, ¿la ÚNICA modificación estructural elegida —`src/fragment2.frag`, 8 fetchs independientes
realmente consumidos por 8 cadenas FMA independientes (ILP), salida de entropía dependiente de todos—
sube `power_avg`/`mem_busy` vs E1? Protocolo: E1 (baseline intacto, `fragment.frag`) vs F2 (misma CLI).

### 2. Fecha
2026-09-21.

### 3. Metodología experimental
- Cambio de código mínimo y reversible: nuevo archivo `src/fragment2.frag` + flag `--frag FILE`
  (default `fragment.frag`) en `graphics.cpp`; NO se tocó `vertex.vert`, `fragment.frag`, texturas,
  CB, MSAA, seeds, warmup/duration, cap, ni DPM. Binario: `main-graphics` (md5 `de81536fd94fa51...`);
  `main` intacto (md5 `a7e7ace5...`). `glslangValidator` valida fragment2.
- Smoke (640×480, tex 512): E1 70 fps/14.4 ms vs F2 36 fps/28.3 ms → el nº de fetchs ESCALA el
  frametime ~2× en config mínima (primera señal del modelo fetch-bound).
- Corrida control (misma CLI, shader E1) seguida de F2, telemetría 10 Hz 34 s + pre/post DPM + journal:
  `runs/escalado-01/F2-control-e1-frag/` y `runs/escalado-01/F2-fetch8-ilp/`.
- CLI idéntica a E1 comb: `--fma-iters 16 --tex-size 8192 --msaa 8` (1920×1080, layers 4, warmup 5,
  duration 20; F2 añade `--frag fragment2.frag`).

### 5. Hechos VERIFICADOS
- F2-control: fps 8.90, frametime 112.4 ms, régimen estable power 16.13 W (max 16.19), mem_busy 36.0 %.
- F2 (8 fetchs): fps 4.55, frametime **221.7 ms (2.0 × control)**, power 15.76 W (max 15.81),
  mem_busy **36.0 % (idéntica)**, vram/gtt iguales (1.11 GiB totals, sin OOM).
- El nº de fetchs por fragmento es la variable que escala el frametime de forma exacta (smoke 2×00 y
  221.7/112.4 = 1.97×): confirma que el cuello es el camino FETCH→uso, no ALU ni CB.
- Duplicar el trabajo de memoria por fragmento NO subió potencia ni mem_busy: al duplicar los fetch
  por frame el frametime también se duplica → **fetchs/segundo constante → DRAM/segundo constante →
  potencia al equilibrio del reloj** (SCLK 1071 + MCLK 1500 constantes durante todo el run).
- Estabilidad: 2/2 exit 0, 0 `GPU fault|VM fault`, DPM restaurado pre==post. Sin OOM/reset/device lost.

### 6..7. Hipótesis (estado)
- H-F2 ("más fetchs reales por fragmento sube mem_busy/power"): **RECHAZADA** para el régimen de
  clocks fijos de esta placa: el GPU se autolimita por la tasa de fetch por segundo (bound de latencia)
  y el reloj de bits no entrega más W. El ritmo auto-pacing anula el efecto de añadir trabajo/frame.
- H-clockgating (nueva, coherente con whitepaper Polaris "fine grained clock gating" y con ES-01/F2):
  las unidades ociosas de GFX8 están clock-gateadas y no suman consumo; el consumo de régimen (~16 W)
  viene del reloj fijo (SCLK 1071/MCLK 1500) + actividad DRAM moderada (36 %) — no de "más trabajo".
  [SUSTENTADA por todos los runs: B (ALU libre), D (CB libre), F2 (memoria autopacada)]
- CONCLUSIÓN FASE 2: con DPM en auto y sin forzar clocks (regla del proyecto), este diseño de
  workload no puede subir la potencia sostenida por encima de ~16 W; la palanca de potencia real de
  la placa (clocks más altos / más unidades activas a la vez) no es alcanzable por la estructura del
  fragment. NO se agrega más complejidad (regla del dueño): se documenta y DETIENE.

### 8..13.
- Decisión técnica: quedarse con E1/BASE para cualquier uso posterior; `fragment2.frag` queda como
  variante documentada (no útil para el objetivo de potencia, útil como prueba del modelo fetch-bound).
- Clasificación de la modificación: AUMENTO REAL DE CARGA (trabajo por fragmento 2×, frametime 2.0×)
  y a la vez **SIN CAMBIO en potencia/mem_busy** → para el objetivo del proyecto, SIN CAMBIO (no
  discrimina). RESTRICCIÓN nueva demostrada: frametime ~ (fetchs totales / fetch-rate sostenible).
- Artefactos: `src/fragment2.frag`, flag `--frag`, `runs/escalado-01/F2-control-e1-frag/*`,
  `runs/escalado-01/F2-fetch8-ilp/*`. Anexo B actualizado. Sin A/B 30 vs 35 W.

---

## Anexo A — Fuentes web citadas (URLs completas)

1. https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2947
2. https://videocardz.net/amd-radeon-rx-550
3. https://www.igorslab.de/en/performance-benchmark-power-consumption-rx550-polaris/
4. https://www.relaxedtech.com/reviews/amd/radeon-rx-550/1
5. https://www.phoronix.com/review/radeon-rx550-linux
6. http://zqwzjdq.vgamuseum.info/images/doc/amd/polaris-whitepaper.pdf
7. https://docs.kernel.org/gpu/amdgpu/thermal.html
8. https://dri.freedesktop.org/docs/drm/gpu/amdgpu.html
9. https://docs.mesa3d.org/drivers/radv.html
10. https://git.b0tt0m.xyz/mirror/linux/commit/f120386d74f193301d808ccfec1a778af62b6797
11. https://lists.freedesktop.org/archives/amd-gfx/2020-June/050624.html
12. https://geeks3d.com/furmark/
13. https://geeks3d.com/gputest/
14. https://www.geeks3d.com/furmark/command-line/
15. https://specpicks.com/reviews/why-does-furmark-have-gpu-killer-reputation
16. https://www.pchardwarepro.com/en/furmark-how-to-stress-gpu-and-vram-without-dying-in-the-attempt/
17. https://computergraphics.stackexchange.com/questions/9956/performance-of-compute-shaders-vs-fragment-shaders-for-deferred-rendering
18. https://computergraphics.stackexchange.com/questions/54/when-is-a-compute-shader-more-efficient-than-a-pixel-shader-for-image-filtering
19. https://www.geeks3d.com/20240224/furmark-2-1-0-released/
20. https://gpuopen.com/learn/dcc-overview/ — DCC en APIs (usage flags que lo deshabilitan/degradan, métricas).
21. https://chipsandcheese.com/p/gcn-amds-gpu-architecture-modernization — GCN: RBs con cachés de color (16 KB) y profundidad (4 KB); color final a controladores de memoria (bypass L2, documentado en Tahiti); L2 write-back en slices; Vega mueve RBs delante de L2.
22. https://github.com/airlied/mesa/commit/ff8b0f65f5e78da9f8129bf8787eb18a2a51d271 — RADV: DCC por defecto en color, flags que lo deshabilitan.
23. https://lists.freedesktop.org/archives/mesa-dev/2019-June/220696.html — RADV: en GFX6-8 L2 solo para shaders; CB/DB con flush/inv propia.
24. https://kusma.pages.freedesktop.org/mesa/drivers/radv.html — env vars RADV (`radv_disable_dcc`, etc.).
25. https://www.phoronix.com/review/radv-dcc-boost — DCC en RADV, ahorro de bandwidth.
26. https://lists.freedesktop.org/archives/amd-gfx/2020-September/053984.html — política DPM MCLK smu7 (mclk_activity/up_hyst/down_hyst por ancho de bus; 128-bit: activity 20).
27. https://vulkan.gpuinfo.org/displayreport.php?id=13824 — límites Vulkan reportados para RADV/POLARIS10 (máx imagen 16384, capas 2048, push const 256 B, anisotropy 16).
28. https://www.saschawillems.de/blog/2016/08/13/vulkan-tutorial-on-rendering-a-fullscreen-quad-without-buffers/ — técnica "bufferless fullscreen triangle" (gl_VertexIndex).
29. https://www.rastergrid.com/blog/gpu-tech/2021/10/multisampling-primer/ — MSAA básico: SHS=1, CCS=N; blend/ROP por muestra.
30. https://docs.vulkan.org/samples/latest/samples/performance/msaa/README.html — MSAA: attachment N× más grande; almacenado/releído multiplica banda.
31. https://lists.freedesktop.org/archives/mesa-dev/2018-November/209606.html — RADV: DCC NO habilitado por defecto para MSAA 4x/8x (`dcc_msaa_allowed`).
32. https://www.igorslab.de/en/performance-benchmark-power-consumption-rx550-polaris/ — P12: 512 KB L2 (P11 1 MB); boost real ~1141–1164 MHz.

## Anexo B — Clasificación resumen

- [VERIFICADO] Specs P12 (512 SP/8 CU, 32 TMU, 16 ROP, 128-bit, 112 GB/s, 512 KB L2, 50 W).
- [VERIFICADO] `power1_input`/`power1_average` en µW (SMU); `gpu_busy/mem_busy` por firmware; `power1_cap`=35 W máx en este sistema.
- [VERIFICADO] DPM auto → SCLK 1071 / MCLK 300 piso en E-01/E-02.
- [VERIFICADO] Compute ALU puro: 13.2 W (E-01) y ALU+memoria nominal: 12.4 W (E-02); ambos ≪ 27 W, sin presión DRAM real (w/s 256 KB).
- [VERIFICADO] El techo del shader actual es la ejecución interna (SCLK 1071, mem_busy bajo); MCLK nunca se activó.
- [HIPÓTESIS] H-frag (fragment/overdraw/MSAA satura render back-end, más draw), H-tex (sampleo incoherente + w/s > L2 eleva DRAM/draw), H-band (memoria-bound solo si se satura DRAM real).
- [VERIFICADO] Pipeline gráfico: los RBs escriben el color final fuera de la L2 en GCN1 (Tahiti) y el CB/DB no usa L2 en GFX6-8 (mesa-dev); DCC comprime CB (pico 8:1) y RADV lo habilita por defecto excepto con storage/linear/scanout.
- [VERIFICADO] Política DPM MCLK smu7 para bus 128-bit: `mclk_activity=20`, `up_hyst=5`, `down_hyst=16` → MCLK sube con actividad de memoria sostenida ≥ ~20 % (explica E-01/E-02 con mem_busy 3–7 %).
- [VERIFICADO] En esta placa el draw máximo de la sesión actual fue GRÁFICO: Superposition 18.8/23.7 W ≫ GravityMark 12.4/14.8 W ≫ compute E-01/E-02 13.2/12.4 W.
- [VERIFICADO] Límites RADV/GFX8 (POLARIS10): imagen 16384 px, 2048 capas, 256 B push constants; fullscreen triangle bufferless válido; sample counts de color hasta 8 (verificar en runtime).
- [VERIFICADO R-11] En GFX8/RADV los imageStore a storage IMAGE producen VM faults deterministas
  (páginas fijas 774082/482455, lecturas TC 4/8 B); los storage BUFFER no; los driconf
  `radv_disable_shrink_image_store`/`radv_wait_for_vm_map_updates` solo los reducen (4→2) o no los
  eliminan → se evita por diseño (generación host + vkCmdCopyBufferToImage, 0 faults).
- [VERIFICADO E-03] Diseño B en configuración base: exit 0, 0 faults, SCLK 1071 + MCLK 1500 activos
  (220/277 muestras), mem_busy 28.6 % (36–49 % en régimen), power 13.40 W avg / 15.81 W pico, 8.95 fps;
  DPM restaurado pre==post. Clasificación: VÁLIDA (tras corrección de validez del generador).
- [REGLAMENTO] Criterio de validez ampliado: exit 0 + fences + **0 líneas `GPU fault|VM fault` en
  journal** (el exit 0 por sí solo NO basta; ver E-03 §13).
- [HIPÓTESIS] H-gfx: pipeline gráfico (fragment pesado + CB alta entropía + texturas > L2 + overdraw/MSAA) puede sostener ≥ 27 W con cap 35 W; tope conocido de benchmarks reales ~23.7 W pico.
- [VERIFICADO ES-01] El escalado de parámetros A–D sobre BASE E-03 NO sube la potencia sostenida
  (todos en 15.75–16.18 W en régimen vs BASE 15.75 W; mem_busy clavada 35.9–36.0 %): el pipeline está
  en un equilibrio de LATENCIA (SCLK 1071 fijo, work/s constante) → añadir trabajo por frame solo
  baja FPS (overdraw: frametime 222/442 ms con layers 8/16) o es ocultado (FMA 96, MSAA 8x deduplicado,
  tex 8192² sin cambiar el nº de fetches). 10/10 corridas estables (exit 0, 0 faults, DPM restaurado).
- [VERIFICADO ES-01] MSAA 8x NO genera 8× escrituras al CB con triángulo fullscreen de color único:
  todas las muestras del píxel son idénticas → deduplicación HW/RADV (contradice la suposición de banda
  de R-12/MSAA; documentado, no borra R-12).
- [DESCARTADO como vía] Overdraw, FMA, tex-size y MSAA (sin per-sample shading) para subir W dentro de
  este diseño de shader. Nueva hipótesis fase 2: reestructurar el fragment (throughput ALU: acumuladores
  independientes; más fetches/fragmento; per-sample shading con valor por muestra).
- [VERIFICADO R-13/F2] El cuello del workload gráfico es el camino FETCH→uso (latencia de memoria,
  miss L1/L2 ~350 ciclos; fetchs por segundo constantes): duplicar los fetchs por fragmento duplica el
  frametime (112→222 ms, 1.97×) con mem_busy y potencia invariantes (15.76 vs 16.13 W). El GPU se
  autolimita al equilibrio del reloj (SCLK 1071/MCLK 1500); las unidades ociosas de GFX8 están clock-
  gateadas y NO suman consumo → más trabajo por frame = menos fps, no más W.
- [VERIFICADO R-13/F2] RADV soporta sampleRateShading/per-sample shading en GFX8
  (`ps_iter_samples = rasterizationSamples × minSampleShading`), pero multiplicar invocaciones daría el
  mismo resultado clase-SIN-CAMBIO que overdraw; NO se implementó (documentado como hipótesis futura).
- [DESCONOCIDO] Costo real de banda/VRAM en esta placa; contribución de GTT al draw; si el CB de Polaris efectivamente bypassa L2 (documentado en GCN1); sample counts exactos de P12 (DB: hasta 64 para POLARIS10).
- Lo que NO puede concluirse: nada sobre el coste de DRAM en la RX 550 (ningún run saturó DRAM); nada sobre pipeline gráfica/textura (no ejecutadas).

Regla anti-sobrescritura (DN-13): cualquier futuro hallazgo que contradiga estas
conclusiones se agregará como contradicción documentada, sin borrar estos registros.