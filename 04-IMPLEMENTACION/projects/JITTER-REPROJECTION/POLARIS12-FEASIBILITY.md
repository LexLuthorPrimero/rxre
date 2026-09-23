# I-03 — POLARIS12-FEASIBILITY — TAA JITTER AS REPROJECTION SIGNAL

> Fecha: 2026-09-22 · FASE R-3 · DOCUMENTAL ONLY
> Hardware: RX 550 (Polaris12 / GFX8), 512 shaders, 16 ROPs, V$ 16KB/CU, 128-bit GDDR5.

## 1. CONTEXTO DE LA IDEA EN POLARIS12

La pregunta práctica del proyecto (vinculada a I-02): en escenas de cámara estática con pocos/sin objetos dinámicos,
¿qué tan lejos llega la reproyección **sin motion vectors por objeto** (solo cámara + jitter + depth)?
La respuesta afecta directamente I-02: los tiles que la reproyección marca como "locked" son los que vale la pena
re-render.

## 2. REPROYECCIÓN SOLO-CÁMARA — QUÉ ES EN LA PRÁCTICA

En TAA canónico (TAA survey §3.1), la ecuación es:

```
p_{t-1} = M_{t-1} · M_t^{-1} · p_t
```

Con:
- `p_t` = punto en espacio de clip (current frame) — se calcula con la proyección jitterada actual.
- `M_t^{-1}` = inversa de la proyección jitterada actual → back-projection a world/view.
- `M_{t-1}` = proyección jitterada previa → proyectar al previous frame.
- El resultado `p_{t-1}` es la posición UV de este mismo punto en el frame anterior → se samplea allá (history lookup).

**Este es EXACTAMENTE el "reproyección solo-cámara"** y es lo que hace TAA por defecto cuando no hay MVs reales.
Funciona **solo si el objeto está estático**: si se mueve, `p_{t-1}` cae en la posición incorrecta → ghosting.

### ¿Qué aporta el jitter a este cálculo?

El jitter es la razón por la que la posición de muestra de `p_t` NO está centrada en el pixel: está desplazada
`[-0.5..0.5)` en x y y (por la perturbación a la proyección). Al reproyectar, este desplazamiento se convierte
en un offset preciso que hace que la historia sea subpixelmente coherente con la nueva posición de muestra:
**el jitter mejora la cobertura de la acumulación**, pero NO cambia la dirección del vector de correspondencia.

```
# Ejemplo: Fwog Reproject.comp.glsl (ver §3 de PRIOR-ART)
vec2 jitteredUV = uv + motion - jitterOffset + lastFrameJitterOffset;
```

Los jitter offsets (current y prev) se compensan explícitamente: el jitter entra al cálculo de la proyección
(`p_t` lo porta) y se resta del UV final. Sin esto, la historia sampleada estaría desplazada → ghosting artificial.
Esto se demuestra en todas las implementaciones open source:
- playdead/temporal
- Fwog
- GameTechDev/TAA
- alextardif/TAA
- FSR2 (FSR jitter compensation)

**Conclusión:** el jitter es un parámetro de calibración del muestreo, no un vector de motion.

## 3. QUÉ SE ROMPE SIN MVs POR OBJETO

Documentado en TAA survey §6, ATAA, DLSS guide:

| Fenómeno | ¿Por qué rompe solo-cámara? | ¿Cuándo es grave? |
|---|---|---|
| **Objeto en movimiento** | MV real ≠ MV de cámara; el historial se samplea en posición incorrecta | Siempre (más cuanto más rápido) |
| **Disocclusion** | El punto que existía atrás del objeto en el frame previo no está en la profundidad previa; se samplea "punto equivocado" | Aparece en bordes de objetos que se mueven |
| **Sombras dinámicas** | La sombra se mueve con la luz, no con la geometría; la superficie subyacente estática → MV de cámara dice "estático", pero el píxel ha cambiado | Escenas con luz dinámica |
| **Especulares/reflexiones** | El pixel del mirror no tiene MV de la superficie reflejada; la sombra/specular es función de la cámara y de la geometría reflejada | Escenas especulares con movimiento |
| **Transparencias** | Las capas blendeadas no preservan depth; la reproyección solo-cámara no puede separar capas | Partículas, viento |
| **UI/HUD** | La HUD se samplea como si fuera 3D → ghosting en movimiento de cámara | Menúes sobre 3D |

## 4. APLICACIÓN EN POLARIS12 — QUÉ HACE ESTA GPU

Polaris12 tiene la **aceleración de depth-test (HTILE)** y es **IMR**: la reproyección solo-cámara cuesta:

1. Leer depth buffer (puede leer DCC-compressed vía shader; el read es L2-friendly por ser solo-lectura).
2. Hacer el unproject/project por píxel (2×matmul 4×4, un sqrt de W, y un bilinear sample del historial).
3. Comparar/validar (history clamp, neighborhood clip — coste O(1) por píxel).

En una pantalla 720p (≈0.92M píxeles), a FP32 este coste es de **unas décimas de milisegundos** → despreciable
ante el coste de un full pass de sombreado de la escena completa. Es por eso que la reproyección solo-cámara
**ya se ejecuta** en este hardware como parte de TAA (incluso sin MVs reales, con el componente de cámara).

### 512 shaders × 16 ROPs — dónde duele

En Polaris12, el cuello es **fill/shading** (512 shaders / 16 ROPs); por eso:
- La reproyección solo-cámara (un compute-like pass ligero) NO es el cuello → no la eliminamos.
- El cuello es el **full draw/shading de la escena completa** → es ahí donde I-02 intenta saltar tiles.
- La reproyección solo-cámara **sirve** como señal barata para decirle a I-02 "este tile no cambió".

### ¿Por qué FSR2/DLSS/XeSS no se usan en Polaris12 directamente?

No es cuestión de "no poder" (FSR2 corre en GPU con Vulkan DX12 FP16; Polaris12 tiene Vulkan 1.3 y FP32; FP16 se emula
pero es factible). Es que:
1. **Requieren MVs por objeto** (FSR2 manual; DLSS guide; XeSS guide): la implementación debe escribir un velocity buffer
   en el harness.
2. **FSR2/XeSS son open source** (MIT) → viables como referencia en el proyecto si se añade el velocity buffer.
3. La pregunta del proyecto NO es "correr FSR2" sino "cuánto aguanta solo-cámara sin el MV de objeto" → esto es medible
   sin instalar FSR2: basta con un TAA propio o un reprojection pass simple con depth + matrices.

## 5. ¿CÓMO SE INTEGRA CON I-02?

La señal de I-03 (reproyección solo-cámara + jitter) permite a I-02:
1. **Detectar tiles estáticos** con confianza: si la reproyección solo-cámara es válida en un tile (historia matcheada con
   error < ε), ese tile **no se redibuja**. Si el error es alto → tile dinámico → sí se redibuja.
2. **Coste de la señal**: un depth read + matmul + comparación = O(1) por tile → baratísimo vs el coste de sombrear 32×32
   píxeles de escena (shading + texturas + raster).
3. **Límites de la señal**: si hay objetos en movimiento sin MVs, los tiles que los cubren marcarán error alto
   (disocclusion en bordes, ghosting) → I-02 los marcará como dinámicos (correcto) o como "necesita MV real"
   (la señal solo-cámara no alcanza).

**Conclusión:** la integración I-03 → I-02 es técnicamente plausible y es la razón por la que el claim se acota a
"escenas de cámara estática y objetos fijos" (donde solo-cámara basta). Para escenas dinámicas, la integración necesita
velocity buffer real (FSR2-style) → se marca como trabajo futuro.

## 6. VEREDICTO DE VIABILIDAD EN POLARIS12

| Aspecto | Veredicto |
|---|---|
| Coste de reproyección solo-cámara | Despreciable (décimas de ms en 720p) |
| Calidad de la señal solo-cámara | ALTA en cámara estática, cero dinámicos (tiles lockeados perfectos); decae a cero en escena dinámica completa |
| Integración con I-02 (tile locked map) | PLAUSIBLE — se puede usar como señal de entrada al dirty-tile decision |
| ¿Necesita FSR2/DLSS/XeSS? | NO — se puede implementar un reprojection pass simple propio (TAA canónico); FSR2 es interesante como referencia pero no es el claim |
| ¿Necesita velocity buffer (MV)? | NO para la hipótesis "solo-cámara"; SÍ si se quiere calidad general |
| Feasibility | **HIGH** (coste bajo, claridad conceptual, integración directa con I-02) |

## 7. CONCLUSIÓN DE I-03 PARA POLARIS12

La reproyección solo-cámara con jitter es la operación **más barata** que este hardware puede ejecutar para evaluar
cambio temporal: un depth read + 2×matmul + comparación, O(1) por píxel, casi cero fill (necesita un único compute
dispatch por pantalla). Es la **base mínima** de la señal de cambio que I-02 necesita.

La limitación es clara y documentada: en cuanto los objetos se mueven, la señal solo-cámara falla → los tiles que
se marque como "locked" en ese momento generarán ghosting/artefactos. Eso se mide en la FASE G/K como falsabilidad.

Estado: **C** — medible con bajo costo, y alimenta directamente a I-02.