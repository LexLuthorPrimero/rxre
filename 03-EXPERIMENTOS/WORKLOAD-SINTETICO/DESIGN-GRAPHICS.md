# DESIGN-GRAPHICS — Diseño de workload Vulkan de GRÁFICOS para la RX 550 (fase de diseño)

Registro de diseño de la segunda fase del workload sintético (rama §J). Este documento
**NO implementa ni ejecuta nada**: define el diseño multi-opción, sus parámetros, variables,
criterios y plan, conforme a la regla DN-13. La investigación asociada está en `RESEARCH.md`
(R-06..R-09) y en este documento se remite a ella. Ningún código se escribió ni se modificó en
esta fase; kalm, Mesa, amdgpu y los artefactos de E-01/E-02 permanecen intactos.

Convención de estado (heredada): `[VERIFICADO]` · `[REPRODUCIBLE]` · `[OBSERVADO]` ·
`[NO REPRODUCIBLE]` · `[HIPÓTESIS]` · `[DESCARTADO]` · `[DESCONOCIDO]`.

---

## 1. Objetivo

Diseñar un segundo workload sintético **Vulkan de gráficos** para la RX 550 (Polaris12,
`1002:699F`, cap=35 W por defecto) que determine experimentalmente si **una carga gráfica real
puede alcanzar un draw sostenido ≥ 27 W con cap=35 W**, haciendo medible la separación entre
`cap=35 W` y `cap=30 W` (criterio DISCRIMINATIVO de M1 / MASTER-PLAN).

Dos metas operativas:

1. **Mecanismo**: activar simultáneamente los subsistemas que los workloads previos no activaron —
   SCLK pegado (1071) Y presión DRAM real (MCLK saliendo del piso 300 → hasta 1500) — mediante la
   ruta gráfica (render back-end / CB / texturas), que es la única evidencia local de draw alto.
2. **Criterio**: clasificar la corrida como DISCRIMINATIVO / NO DISCRIMINATIVO / INVÁLIDO / REQUIERE
   ITERACIÓN según los criterios del §6.

## 2. Requisitos (heredados + de fase)

1. Selección **estricta** de la RX 550 por `vendor=0x1002 device=0x699F` en runtime (enumeración +
   verificación), como el prototipo `main` (R-03). `--any-gpu` solo para desarrollo.
2. **NO modificar** código existente (rx550-torneo, M1, Kalm, Mesa, amdgpu). **NO escribir sysfs**
   (cap/control/DPM/clocks intactos; cap=35 W por defecto). Sin forcing de clocks/DPM.
3. Reproducible/determinista: el patrón del shader se deriva de `gl_FragCoord` y push constants
   (seed fija), sin estado aleatorio no reproducible.
4. Medible: compatible con la telemetría actual 10 Hz (`telemetria.sh`, campos
   power/temp/busy/mem_busy/vram/gtt/sclk/mclk) + FPS/frametime medidos por fence.
5. Reversible: solo env vars por proceso (`VK_ICD_FILENAMES`, `MESA_VK_DEVICE_SELECT`); al salir se
   liberan todos los recursos; no queda config del sistema alterada.
6. Independiente de kalm (no interactúa; se verifica pre/post).
7. Sin OOM / device lost / reset en el funcionamiento previsto: presupuesto de VRAM < 1 GB.
8. Duración de fase activa ≥ 20 s (régimen E-01/E-02) con warm-up previo para que DPM responda.

## 3. Investigación (resumen; detalle en RESEARCH.md)

- **R-06 / CB-ROP-DCC**: los render backends escriben el color final fuera de la L2 (documentado en
  GCN1: "final pixel colors are written to the memory controllers and bypass the L2 cache");
  en GFX6-8 la L2 sirve a shaders y el CB/DB se gestiona aparte [VERIFICADO para GCN1, HIPÓTESIS
  para Polaris]. DCC comprime el CB (lossless, bloques dinámicos, pico 8:1) para ahorrar banda →
  escribir **salida de alta entropía derrota DCC** y fuerza el CB a DRAM. RADV habilita DCC por
  defecto en color; lo deshabilitan storage/linear/scanout (y `radv_disable_dcc=1`).
- **R-07 / MCLK-DPM**: smu7 (Polaris, bus 128-bit): `mclk_activity=20`, `up_hyst=5`, `down_hyst=16`
  → MCLK sube cuando la actividad de memoria está **sostenida ≥ ~20 %** (explica E-01/E-02:
  mem_busy 3–7 % → MCLK piso).
- **R-08 / límites**: fullscreen triangle bufferless válido (3 vértices, UV de `gl_VertexIndex`);
  límites RADV/GFX8 holgados para 1080p (máx imagen 16384 px, 256 B push constants); sample counts
  de color hasta 8 (verificar en runtime).
- **R-09 / evidencia local**: el draw máximo de la sesión actual fue GRÁFICO: Superposition
  18.8/23.7 W ≫ GravityMark 12.4/14.8 W ≫ compute propio 13.2/12.4 W. El compute satura SCLK pero
  no memoria ni render back-end.

## 4. Diseños considerados (≥2)

### Diseño A — Compute extendido con texturas grandes (sin pipeline gráfico)

- Extiende el prototipo: shader compute lee 4 imágenes de 4096² RGBA8 (64 MiB c/u) con coordenadas
  incoherentes (derivadas deterministas), cadena de fma, y escribe el resultado en una **storage
  image** del tamaño del CB.
- Activa: SPs/ALU, TMUs (lectura de imagen), misses de L1/L2 (w/s > 512 KB).
- NO activa: rasterizador, ROPs/render back-end, blending, overdraw, ruta CB→DRAM
  (los writes de storage images van por L1/L2 write-back, absorbidos por L2 [R-06]).
- Pros: reutiliza infraestructura, sin render pass, bajo riesgo, sirve de **testigo** (contrafactual
  interno del eje "ruta gráfica").
- Contras: sin multiplicadores (overdraw/MSAA); el tráfico DRAM se limita a reads que fallen de
  L1/L2; predicción de draw parecida a E-02 (≈13 W) o discretamente mayor.
- Clasificación predicha: **probablemente NO DISCRIMINATIVO** (no presiona banda ni ROPs).

### Diseño B — Fullscreen triangle + fragment pesado + CB de alta entropía + overdraw/MSAA (SELECCIONADO)

Pipeline gráfica completa, offscreen (sin presentar):

- **Vertex**: fullscreen triangle bufferless (3 invocaciones, UV de `gl_VertexIndex`) [R-08].
- **Fragment** (por píxel):
  - UV de sampleo *fragmentadas* derivadas de `gl_FragCoord` (escala grande + offset por capa) →
    accesos de textura incoherentes/high-frequency (deterministas).
  - 4 samples de textura (bilinear) de 4 texturas de 4096² RGBA8 (≥ 256 MiB juntas, > 512 KB L2)
    → misses de L1/L2 → lecturas DRAM.
  - Cadena de ~24 fma sobre los samples → mantiene ALU ocupada y SCLK pegado (1071).
  - **Salida de alta varianza** (bits de `gl_FragCoord` combinados con los samples) → derrota DCC →
    el CB sale a DRAM sin comprimir [R-06].
  - Blending **aditivo** → fuerza read-modify-write del CB por capa.
- **Render pass**: un color attachment `R8G8B8A8_UNORM` 1920×1080; sin present/swapchain.
- **Overdraw**: N capas fullscreen acumulativas (base N=4; eje 1–8) → multiplica fragment + CB.
- **Ejes opcionales**: MSAA 2x/4x/8x (validado en runtime); N capas; cantidad de texturas/samples.
- Bucle de frames: sin semáforos de present, fence por frame → FPS/frametime medibles.
- Activa: rasterizador, SPs/ALU, TMUs/textura, ROPs con blending, CB→controlador de memoria,
  banda (reads de textura + writes de CB) → candidata a `mem_busy ≥ 20 %` → MCLK > piso [R-07].
- Pros: coincide con el conjunto de subsistemas que dio el draw máximo local (Superposition 23.7 W);
  multiplicadores deterministas para empujar por encima de ese techo.
- Contras: más complejo; riesgo de OOM con MSAA alto; riesgo de cuello de botella del fragment
  dejando la banda baja (se equilibra con parámetros).

| Criterio | A | B |
|---|---|---|
| Unidades activadas | SP/TMU/cache L1·L2 | + Raster + ROP/blending + CB→mem |
| Presión DRAM | reads únicamente (L2 write-back) | reads + writes de CB descomprimidas |
| Multiplicadores | ninguno | overdraw, MSAA, samples de textura |
| Riesgo | bajo | medio (mismo, OOM si MSAA alto) |
| Draw predicho | ≈13–15 W | 15–30 W según ejes |

## 5. Diseño seleccionado

**Diseño B**, con **Diseño A como testigo experimental opcional**: si en una futura corrida B ≫ A
con la misma intensidad de banda, se aísla la contribución del pipeline gráfico (ROP/CB) al draw.

Config base (primera corrida, conservadora):

| Parámetro | Valor |
|---|---|
| Resolución | 1920×1080 (2.0736 MPix/layer) |
| Formato CB | `R8G8B8A8_UNORM` |
| MSAA | 1x (eje: 2/4/8, si `vkGetPhysicalDeviceFormatProperties` lo confirma) |
| Texturas | 4 × 4096² RGBA8 (4 × 64 MiB = 256 MiB VRAM), contenido determinista (patrón por posición; no uniforme para no reducir entropía) |
| Overdraw | N = 4 capas fullscreen (eje 1–8) |
| Blending | aditivo (fuerza RMW del CB) |
| Fragment work | ≈4 sampleos bilineal + ~24 fma + salida ruidosa |
| DCC | ON por defecto (se derrota por entropía); lever de reserva documentado: off (`radv_disable_dcc=1` o storage usage) |
| Env | `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json MESA_VK_DEVICE_SELECT=1002:699f` |
| Selección device | enumeración + validación `0x699F` en runtime |
| Duración | warm-up 5 s + fase medida 20 s |
| Determinismo | patrón y offsets derivados de `gl_FragCoord` + push constants (seed fija) |
| Present | OFF (offscreen; sin swapchain) |

## 6. Variables de medición y criterios de validez

### Variables
- Del workload: FPS, frametime (fence por frame), capas/seg, VRAM usada.
- De telemetría 10 Hz: `power1_input` (µW), temp, `gpu_busy`, `mem_busy`, nivel SCLK (MHz),
  nivel MCLK (MHz), `vram_used`, `gtt_used`.
- Estabilidad: RC, stderr, journal pre/post, sin device lost/reset/hang/OOM.
- Indicadores de mecanismo: `mem_busy ≥ 20 %` sostenido y/o MCLK > piso (R-07); SCLK ≈ 1071.

### Clasificación de la corrida
- **DISCRIMINATIVO**: (a) draw fase activa ≥ 27 W sostenido (media en ventana estable); (b)
  reproducible entre corridas (N≥2, CV ≤ 5 %); (c) sin resets/errores; (d) diferencia medible
  35 W vs 30 W (Δ potencia y/o SCLK/FPS ≥ margen definido, p.ej. ≥ 2 W).
- **NO DISCRIMINATIVO**: ejecuta correcto pero draw sostenido < 27 W, o Δ(caps) indistinguible.
- **INVÁLIDO**: OOM/device lost/reset/hang/timeout/VK_ERROR/stderr no vacío/telemetría incompleta,
  o el mecanismo falló (MCLK en piso y mem_busy < 10 % durante toda la fase activa → el diseño no
  presionó DRAM).
- **REQUIERE ITERACIÓN**: ejecuta sin errores, activa memoria (MCLK > piso o mem_busy ≥ 20 %) y
  SCLK ~1071, pero draw entre 20 y 27 W → ajustar ejes (overdraw/MSAA/texturas) y repetir.

## 7. Riesgos

1. **DCC comprime pese a la entropía** → MCLK no sube. Mitigación: garantizar salida high-frequency;
   lever de reserva DCC off (documentado, criterio mínimo).
2. **Cuello de botella del fragment** → SCLK pegado pero banda baja (mem_busy < 20 %). Mitigación:
   balance texturas/ALU, monitoreo en vivo, ajuste de parámetros en iteración.
3. **OOM / device lost** con MSAA alto o texturas grandes. Mitigación: presupuesto < 1 GB, 1080p,
   MSAA validado en runtime antes de usarlo.
4. **reset/device lost por watchdog**: mitigado por offscreen sin present; fences por frame; tiempos
   cortos.
5. **Determinismo roto** por rutas no deterministas del driver: se usa `gl_FragCoord` + push
   constants; sin PRNG global.
6. **Interferencia con kalm/sistema**: no se toca; pre/post registro igual que E-01/E-02.

## 8. Fallos posibles (diagnóstico)

- **F-mem** (no se activa banda): MCLK piso y mem_busy < 10 % → rediseñar accesos/entropía/DCC.
- **F-p** (mecanismo ok, potencia < umbral): 20–27 W → subir overdraw/MSAA/entropía.
- **F-res** (reset/hang/OOM/device lost): bajar intensidad, revisar VRAM, clasificar INVÁLIDO.
- **F-sys** (entorno: env, telemetría, cap): pre-flight; repetir medición.

## 9. Evidencia faltante (para despejar antes/después de implementar)

- Confirmar en runtime límites P12: `maxImageDimension2D`, `framebufferColorSampleCounts` (¿8?),
  `maxColorAttachments`.
- Confirmar que el CB de Polaris efectivamente bypassa L2 (H-CB-DRAM; documentado en GCN1).
- Confirmar que la política `mclk_activity=20` es la activa en este sistema y qué nivel de
  `mem_busy` sostiene MCLK en 1500.
- Cuantificar cuánta entropía de CB hace que DCC deje de comprimir (micro-bench).
- Costo/drawl de blending + RMW del CB en P12.

## 10. Plan de implementación (SIN autorización en esta fase)

1. **Fase 0 — Verificación runtime**: imprimir props/format props (límites, sample counts).
2. **Fase 1 — Prototipo gráfico**: pipeline (vert bufferless + frag), texturas deterministas,
   render pass offscreen, bucle de frames con fences, parámetros por CLI.
3. **Fase 2 — Corrida base**: pre-flight, warm-up 5 s, fase 20 s con telemetría; depurar hasta
   lograr sin resets.
4. **Fase 3 — Barrido de ejes**: overdraw 1/2/4/8 · MSAA 1/2/4/8 · DCC on/off (N≥2 por config),
   solo con autorización explícita.
5. **Fase 4 — A/B caps 35 vs 30**: réplica del protocolo M1, clasificación según §6.
- Sin writes sysfs; sin tocar kalm/Mesa/amdgpu.

## 11. Por qué este diseño podría discriminar 35 W vs 30 W

1. Los workloads previos quedaron en ~13 W porque **no presionaron memoria**: SCLK pegado pero MCLK
   en piso (R-05, R-07). Este diseño apunta a la **única vía local con evidencia de draw alto**
   (gráfica): CB→DRAM descomprimido + texturas > L2 + overdraw/MSAA, manteniendo SCLK alto.
2. Si logra `mem_busy ≥ 20 %` sostenido, el DPM sube MCLK (R-07) y el draw supera el techo de
   compute; con SCLK 1071 y MCLK 1500 simultáneos la placa puede entrar en el rango 20–27 W donde
   el cap **empieza a ligar** (cerca del límite de 35 W).
3. En esa región, `cap=35 W` vs `cap=30 W` debería producir curvas separables (potencia media y/o
   FPS/SCLK por throttle previo en el 30 W) → la telemetría a 10 Hz lo mediría como DISCRIMINATIVO.
4. Límite honesto: el máximo real observado (Superposition) fue 23.7 W pico; superarlo requiere la
   sobrecarga determinista (overdraw 4–8, MSAA, entropía de CB). Hasta no medir, es [HIPÓTESIS] no
   garantizada; los criterios §6 permiten clasificar cualquier resultado sin modificar el sistema.

## Anexo A — Enmienda al generador de texturas (AMENDMENT, 2026-09-21)

En la implementación se produjo una única desviación de la spec, autorizada por REQ "corregir fallos de
validez": el texto original del §5 decía "contenido determinista (patrón por posición)" sin especificar
el medio de generación; la implementación usaba un compute con **storage images** (`gen.comp`), que en
GFX8/RADV generaba VM faults deterministas (R-11). Se cambió a **generación en HOST (misma familia de
hash) + `vkCmdCopyBufferToImage`**, manteniendo idéntico el contenido y el resto del diseño (fragment,
CB, entropía, overdraw, blending). Cambios:

- Texturas: usage `SAMPLED | TRANSFER_DST` (ya no storage).
- Eliminado: pipeline compute, descriptor/pool/set compute, dispatch.
- Añadido: buffer HOST_VISIBLE|HOST_COHERENT (256 MiB) + barreras UNDEFINED→TRANSFER_DST→
  SHADER_READ_ONLY; copy único al inicio (fuera de la ventana medida).
- `gen.comp` conservado como referencia (no compilado por `main-graphics`).

Validación: 0 `GPU fault|VM fault` en smoke (512²), gen-only y corrida completa base (4096²) — ver
R-11/E-03.

Regla anti-sobrescritura (DN-13): si una corrida futura contradice alguna hipótesis de este
documento, se registra la contradicción, se agregan los datos y se revisa el criterio SIN borrar
el diseño original.