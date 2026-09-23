# I-03 — PRIOR ART — TAA JITTER AS REPROJECTION SIGNAL

> Fuente primaria > comunidad. Fecha: 2026-09-22. Consultas base:
> "TAA jitter reprojection", "motion vectors no motion vectors temporal reprojection",
> "temporal reprojection without motion vectors", "camera reprojection jitter",
> "FSR2 motion vectors velocity buffer", "DLSS motion vectors", "XeSS motion vectors",
> "checkerboard rendering motion", "jitter motion vector DLSS MVJittered",
> "temporal anti-aliasing static camera", "image-based reprojection Hanika".

---

## 1. ACADÉMICO — EL CORPUS CENTRAL DEL TAA (la base "jitter/reproyección")

### 1.1 A Survey of Temporal Antialiasing Techniques — Yang, Liu, Salvi (UoK/Western Digital/Intel)
Referencia canónica. Cubre: jitter subpixel, reproyección dada MV por píxel, **history clamping** y la ecuación
fundamental p_{t-1} = M_{t-1}·M_t^{-1}·p_t (reproyección solo-cámara es exacta cuando no hay movimiento de objeto), fallo
en disocclusion/obj dinámicos (ghosting), y el hecho de que sombras/reflexiones/transparencia rompen la correspondencia.
- http://behindthepixels.io/assets/files/TemporalAA.pdf
- Descripción (post de Marc Beaumont, behindthepixels.io): de la misma página.

### 1.2 TXAA 3.0 / NVIDIA
Documenta TAA donde la **reproyección de cámara se hace vía depth + matrices** (componente de cámara) y las MVs solo
traen el componente de objeto; es el precedente inmediato de "solo-cámara es válido si nada se mueve".
- https://archive.docs.nvidia.com/gameworks/content/gameworkslibrary/postworks/product.html

### 1.3 Adaptive Temporal Antialiasing (ATAA) — NVIDIA 2018
Prueba de que el fallo de la reproyección ocurre precisamente en **sombras/reflexiones/partículas** (donde el MV del
objeto no describe el movimiento de la señal): usa un detect de "temporal availability" para re-muestrear donde la
historia no es válida. Pieza clave del análisis "qué se rompe".
- https://research.nvidia.com/sites/default/files/pubs/2018-08_Adaptive-Temporal-Antialiasing/adaptive-temporal-antialiasing-preprint.pdf

### 1.4 Fast Temporal Reprojection without Motion Vectors — Hanika, Tessari, Dachsbacher (JCGT 2021)
**El análogo documental más cercano al claim de I-03.** Cuando los MV reales son imposibles (nubes, cristal, sombras,
partículas), usa **correspondencia de parches de imagen** (búsqueda temporal con kits de vecinos) para reproyectar la
historia. No usa jitter como señal: usa **correspondencia de imagen**, con un coste computacional explícito.
- Paper: https://jcgt.org/published/0010/03/02/
- PDF: https://jcgt.org/published/0010/03/02/paper-lowres.pdf
- Código réplica comentado: https://gist.github.com/dragon-slayer/SEMLASRTMPI_REFERENCE (TS: referencia; si no existe,
  el paper es auto-contenido).

### 1.5 Render cache + reprojection (Nehab 2007, Scherzer 2010, Toma 2011)
La familia "render cache / reverse reprojection" muestra que el reuse **con MV**, incluso inferido por diferencias de
profundidad, es computacionalmente viable en TBR/IMR y da hit-ratios >90% en walkthroughs estáticos — refuerza que la
reproyección solo-cámara es la frontera inferior del problema (matching exacto vs. correspondencia).
- https://www.cse.ust.hk/~psander/docs/tempcoj.pdf
- https://www.cse.ust.hk/~psander/docs/scache.pdf

---

## 2. COMERCIAL — LOS UPSCALERS REQUIEREN MVs (contradicen el claim "no hacen falta MVs")

### 2.1 FSR2/FSR3.1/FSR 4 — GPUOpen/AMD
Manual oficial: "Motion vectors are **shader outputs (2x float)**, coordinates in range [-width..width, -height..height]".
Señala: **do NOT apply the TAA jitter to the motion vectors** (aplicar jitter a los MV rompe FSR). Jitter remover / apply
por frame es parte del estado de FSR (jitter RRSC pub). Y en contenido dinámico sin MV, FSR produce ghosting.
- https://gpuopen.com/manuals/fidelityfx_sdk2/techniques/super-resolution-temporal/ (motion vectors + jitter)
- Descripción general: https://gpuopen.com/fidelityfx-superresolution-2/
- GDC 2022 talk (Hellblade II deep dive) — confirma que MVs "from camera + object" son input: https://www.youtube.com/watch?v=97JIldpUGE4

### 2.2 DLSS — NVIDIA (Programming Guide)
"Motion vectors are a **key component**… per-pixel motion from the current frame to the previous frame".
**MVJittered flag**: por defecto los MVs yacen en el espacio aparente; si el juego incluye el jitter en los MVs, DLSS
**sustrae** el jitter internamente (¡el jitter NO es señal de motion; es ruido que se elimina). "Incorrect motion vectors
are the **#1 cause** of temporal artifacts".
- PDF (pinned commit): https://raw.githubusercontent.com/NVIDIA/DLSS/d489595a8c5cb19c7a8d770b0cb5bc198cc99018/doc/DLSS_Programming_Guide_Release.pdf
- Resumen público: https://developer.nvidia.com/rtx/streamline (aplicación de MV).

### 2.3 DLSS3 / DLSS4 — NVIDIA
DLSS3 Frame Generation usa **Optical Flow Accelerator** (estimación de movimiento de flujo óptico) **+ MVs** para generar
frames sintéticos entre dost seem; DLSS4 (2025) añade modelos neurales de flujo para contenidos con transparencias/
partículas/UI. Es la prueba end-to-end de que la industria resuelve la falta de MVs por correspondencia/redes, NO por jitter.
- https://www.nvidia.com/en-gb/geforce/news/dlss3-ai-powered-neural-graphics-innovations/
- https://research.nvidia.com/labs/adlr/DLSS4

### 2.4 XeSS / XeSS-FG — Intel
Developer guide: "Motion vectors (float2) from the current frame to the previous frame **must be provided**". XeSS2 split:
MV incl. cámara derivada de matrices de proyección previa/actual (componente de cámara vertical de XeSS) — es decir, la
industria ya separa "cámara vs. objeto" formalmente.
- https://www.intel.com/content/www/us/en/developer/articles/guide/xe-super-sampling-developer-guide.html
- XeSS2 whitepaper: https://www.intel.com/content/www/us/en/developer/articles/technical/xess2-whitepaper.html
- XeSS-FG: https://www.intel.com/content/www/us/en/developer/articles/technical/xess-fg-developer-guide.html

### 2.5 Magpie (upscaler externo) — comunidad
Discusión de incluir reproyección temporal **sin MVs** (no existen MVs en captura pasiva) → recurre a estimación de
correspondencia por similitud (optical flow), la misma vía de Hanika; REAFFIRMA que el jitter, en ausencia de MVs, no
provoca correspondencia usable.
- https://github.com/Blinue/Magpie/discussions/375

---

## 3. IMPLEMENTACIONES OPEN SOURCE QUE ACLARAN EL SEMÁNTICO DEL JITTER

- **playdead/temporal** (MIT): implementation de TAA con "jitter UV" + "motion (velocity)" shaders; demuestra la
  sustracción previa del jitter del espacio de muestreo → la reproyección se computa sobre el espacio **no jogged** de los MVs.
  - https://github.com/playdeadgames/temporal/blob/master/Assets/Shaders/TemporalReprojection.shader
- **Intel GameTechDev/TAA** (MIT): variante de TAA con velocity jitter handling; lectura de cómo se pesa la history al
  recibir reproyección jitterada.
  - https://github.com/GameTechDev/TAA
- **Fwog** — RSM/ShadowMap example: reproyección en compute con `uv + motion - jitter + lastJitter` (fórmula canónica
  que separa jitter actual, jitter previo y motion). Confirma que en cualquier implementación correcta el jitter se
  compensa EXPLÍCITAMENTE y no se trata como vector de motion.
  - https://github.com/JuanDiegoMontoya/Fwog/blob/main/example/shaders/rsm/Reproject.comp.glsl
- **alextardif/TAA** — explains how jitter changes the projection matrix and why reprojection must use the _previous_
  jittered matrix.
  - https://alextardif.com/TAA.html
- **Wikipedia TAA** (referencia enciclopédica, menor peso): jitter = "offset of the sampling grid", se aplica a la
  proyección y se quita al querer material de sampling normal.
  - https://en.wikipedia.org/wiki/Temporal_anti-aliasing

---

## 4. RELEVANTE PARA LA COMPONENTE "SÓLO-CÁMARA" (cuánto se puede recuperar)

- La **ecuación de reproyección p_{t-1} = M_{t-1}·M_t^{-1}·p_t** es **exacta cuando el objeto está coherente con la
  cámara** (estático salvo cámara). Esto lo expresan explícitamente la survey (§3.1) y em TXAA/UE4 fallback.
- La industria ya descompone MVs en **componente de cámara** (a veces vía depth) + **componente de objeto**: XeSS docs,
  FSR (jitter remover aplica solo a la parte de cámara), DLSS (MVJittered).
- **No se encontró** en fuentes primarias un trabajo que use el **patrón de jitter en sí** para inferir motion; los
  análogos usan correspondencia de imagen o flujo óptico (Hanika, DLSS) — de ahí el "KNOWN VARIANT" para I-03.

---

## 5. FENÓMENOS QUE ROMPEN LA REPROYECCIÓN ANTES QUE EL OBJETO

Documentados en TAA survey §6, ATAA, DLSS4/ FG work (despes el flujo neural):
1. **Disocclusion** (cosas detrás de objetos que quedan al descubierto) — la historia no existe.
2. **Sombras/iluminación** — el cambio de sombra no coincide con el MV de la superficie (Lengyel-Snyder '97;
   ATAA; Hanika).
3. **Reflexiones/especulares** — varían con la cámara, no con el MV del mirror (Lengyel-Snyder).
4. **Transparencias/UI** — operan en otra capa (XeSS-FG).
5. **Sub-pixel alias propios del upscaling** — jitter cambiante entre frames.

=> Estos son exactamente los límites que la idea I-03 debería medir (GHOST/experimental section de `EXPERIMENT-DESIGN.md`).

---

## 6. SÍNTESIS PARA I-03

1. "Reproyección solo-cámara con depth+matrices+jitter" es **estándar** (TAA survey; TXAA; UE4; XeSS (cámara) y se usa
   como fallback cuando no hay MV. NO es nueva.
2. "El jitter es ruido al sampling, se sustrae de los MVs" es **documentado** por FSR2 (do not apply jitter to MV) y DLSS
   (MVJittered). Cualquier claim "el jitter ES la señal de motion" choca con la práctica canónica → **CONTRADICTED** a nivel
   de claim absoluto.
3. Donde sí hay hueco: (a) cuantificar el **límite de la reproyección solo-cámara** en hardware Polaris12 (depth+mats+jitter
   = el único vector disponible sin MV), (b) su uso como **detector de tiles estáticos/locked para I-02**. Esa combinación no
   apareció en las búsquedas → **POTENTIALLY NOVEL solo en su forma acotada**.
4. Si se necesita correspondencia real (objetos móviles): la vía documentada es **correspondencia de imagen (Hanika)** o
   **flujo óptico (DLSS)** — Invertir jitter para eso no está soportado por ninguna fuente.