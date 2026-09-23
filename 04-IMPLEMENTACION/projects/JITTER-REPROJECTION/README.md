# I-03 — "TAA JITTER AS REPROJECTION SIGNAL" — Documentary Novelty Audit

> **Proyecto:** RX550/Polaris12 iterative rendering research
> **Fase:** FASE R-3 — Documentary novelty audit (SOLO DOCUMENTAL; no code, no system changes, no benchmarks, no installs)
> **Fecha:** 2026-09-22
> **Modo:** DOCUMENTAL ONLY
> **Archivo principal:** `projects/JITTER-REPROJECTION/`
> **Archivos:** `README.md`, `PRIOR-ART.md`, `POLARIS12-FEASIBILITY.md`, `EXPERIMENT-DESIGN.md`
> **Relación:** input crítico de I-02 (detección de tiles "locked"/estáticos vs no, según cómo se comporte la reproyección).

---

## 1. IDEA EN UNA LÍNEA

Usar el **patrón de jitter subpixel del TAA** como señal para reproyectar: dado que el jitter desplaza la proyección de
cada frame en una fracción de píxel conocida, estudiar **cuánta reproyección de historia es recuperable solo de cámara +
depth + jitter** (sin motion vectors por objeto), y qué se rompe cuando los objetos se mueven.

## 2. ESTADO

| Atributo | Valor |
|---|---|
| **IDEA** | I-03 — TAA Jitter as Reprojection Signal |
| **NOVELTY STATUS** | **KNOWN VARIANT** (core conocido; sub-ángulo "jitter como señal" se acerca a Hanika 2021 / optical-flow; el eje estricto "el jitter reemplaza los MV" está **CONTRADICTED BY PRIOR ART** como claim universal) |
| **Sub-claims** | 1) reproyección **solo-cámara** (depth + matrices, sin MV por objeto) → **KNOWN** (TAA survey; UE4/TXAA default; XeSS MV se descompone en componente de cámara)<br>2) jitter depende de matrices por frame y **NO es movimiento**: los upscalers/MV lo **sustraen** (MVJittered, jitter-not-applied) → **KNOWN**<br>3) "el jitter aporta información de subpíxel para la acumulación" → **KNOWN** (TAA core)<br>4) **"inferir motion de la correspondencia a-espacial entre el frame jitterado y el previo"** → **KNOWN VARIANT** (Hanika "Fast Temporal Reprojection without Motion Vectors" es el análogo documental más cercano; DLSS3/4 usan Optical Flow, no jitter)<br>5) los upscalers comerciales **requieren MVs por objeto** (FSR2/DLSS/XeSS) → **KNOWN** |
| **DOCUMENTAL depth** | 15+ fuentes primarias en `PRIOR-ART.md` |
| **Patents** | NOT AUDITED (ver `PRIOR-ART.md` §7 — flagged) |
| **RECOMMENDED STATUS** | **C** — si el valor del proyecto está en "cuánto aguanta la reproyección solo-cámara en escenas simples Polaris12 y cómo eso alimenta el dirty-tile de I-02", el claim útil es ese, y en esa forma es **PARTIALLY NOVEL** solo en la **combinación con el tile-tracking estático**; el claim "reemplazo de MVs con jitter" es **B** (usar como referencia, no como descubrimiento) |

## 3. NOVELTY STATUS — POR CLAIM

| Claim | Estado |
|---|---|
| La reproyección de historia necesita MV por **objeto** para evitar ghosting | KNOWN (TAA survey; FSR2; DLSS guide) |
| Reproyección **solo-cámara** es correcta solo si los objetos están estáticos o los MVs reales se descomponen en cámara+objeto | KNOWN |
| Sin MV por objeto → ghosting en prims dinámicos | KNOWN (TAA survey §6; FSR2 docs; DLSS "incorrect motion vectors #1 cause of artifacts") |
| El **jitter** se sustrae de / se excluye de los MVs (MVJittered; FSR2 "do not apply jitter to velocity") | KNOWN (DLSS Programming Guide; GPUOpen FSR2 manual) |
| El jitter es un **offset de muestreo**, no una señal de movimiento; corrije acumulación pero no la correspondencia | KNOWN (TAA survey; TXAA; todas las implementaciones) |
| Correspondencia de imagen a nivel de frame para reproyectar cuando no hay MVs reales (nubes, cristal, sombras) | KNOWN VARIANT → Hanika 2021 (JCGT) |
| Estimar motion con **optical flow** (no jitter) en ausencia de MVs | KNOWN VARIANT → DLSS3 Optical Flow Accelerator (híbrido MVs reyes) |
| "El jitter pedros a detectar tiles estáticos (windowing de subpíxel estable) para alimentar I-02" | **PARTIALLY NOVEL** (no encontrado combinación documentada; pero ver §6 limitation) |

## 4. ANÁLISIS CONCEPTUAL RESUELTO (el corazón de la idea)

El jitter es la **pequeña perturbación determinística** aplicada a la matriz de proyección cada frame para que las
muestras caigan en posiciones subpixel distintas a lo largo del tiempo (TAA survey §2.2).

- **Cámara** ⟶ el desplazamiento es una función **conocida** de (jitter_n, jitter_{n-1}, matrices): p_{n-1} se puede
  reconstruir por univocal **unproject** con la proyección jitterada actual y **project** con la previa jitterada.
  Es matemáticamente exacto para una escena solución de la misma profundidad. → **KNOWN** (es exactamente lo que hace el
  TAA por defecto con o sin MV: UE4/TXAA lo usan cuando las MVs no existen; la "motion" media de la cámara de FSR2/XeSS).
- **Objeto** ⟶ el desplazamiento del objeto NO es función del jitter: es un extra arbitrario en UV.
  Incluso si el objeto se mueve "casi nada", el jitter no aporta información sobre su velocidad; solo el MV (o una
  correspondencia explícita de imagen) lo sabe. El jitter cambia la **posición de muestreo**, no la **posición del objeto**.
- **Píxel** ⟶ a nivel de píxel aislado, el cambio entre frames mezcla 4 fuentes: (1) jitter de la proyección actual,
  (2) jitter previo, (3) motion real de cámara, (4) motion real de objeto. Sólo (1)-(3) son derivables de matrices.
  La ambigüedad de (4) es la razón por la que CE (correspondence estimation Este, Hanika) necesita búsquedas temporales
  (multiples de 8 vecinos, patches), una operación costosa en hardware y NO lo que el jitter codifica.

**Por qué el jitter NO es una señal de reproyección (pero sí de acumulación):**
- El predictor de reproyección funciona con correspondencia **exacta** (un vector por píxel). El jitter produce un campo
  de muestreo desplazado, no un vector de correspondencia.
- La principal fuente de corrección de la que el TAA dispone es el propio vector de reproyección + el área de history
  **clamp/neighbor** (TAA survey §5). El jitter SÓLO mejora la _coverage_ subpixel de la acumulación — no la exactitud de
  a dónde apunta la correspondencia.
- cuando la correspondencia falla (objeto en movimiento, disocclusion) el jitter no la arregla; por eso FSR2 y DLSS
  usan dispositivos específicos: FSR2 aplica jitter a la _resolución_ y movimientos de _historia_ con MV del filtro; DLSS
  usa MVs + red neuronal (DLSS3) que predice MV compuestos (OFA – optical flow).

## 5. VEREDICTO RC-* (RÁPIDO)

| Métrica | Leyenda |
|---|---|
| **FEASIBILITY VERDICT (Polaris12)** | HIGH como **cuantificación** (medir el límite de reproyección solo-cámara) / BAJA como reemplazo real de MVs en contenido dinámico |
| **TECHNICAL PLAUSIBILITY** | HIGH en escenas estáticas / LOW-MEDIUM en movimiento de objetos |
| **IMPLEMENTATION COST** | LOW (pipeline TAA/welcome en el proyecto) |
| **RISK** | Medium: ghosting (sin correspondencia); corrupción de historia en disocclusion; y el sesgo de reportar "nadie usa eso" — sí lo hacen los 2D-only renderizaores |
| **DEPENDENCIES** | harness F1/F2 + runner K; velocidad buffer opcional (pass de MV es barato) |
| **RECOMMENDED STATUS** | **C** (refinar a: "cuánto aguanta reproyección solo-cámara sin MV por objeto, y dónde (tiles)" — como fuel de I-02) |

## 6. LIMITACIONES DEL AUDIT
1. Patentes sin auditar (flag §7 de PRIOR-ART).
2. La búsqueda de "combinación jitter+tile estático" es de baja cobertura: no aparece en N búsquedas, pero hay literatura
   enorme de TAA/upscaling con correspondencia — el claim positivo se limita a lo que sí se encontró (Hanika es el punto
   más cercano verificable de correspondencia sin MV).
3. Se documentará explícitamente que FSR2/DLSS/XeSS **requieren MVs** (no "no hacen falta"), basándose en sus guías
   oficiales.