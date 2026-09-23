# IDEA I-09 — L2-RESIDENT INTERNAL RESOLUTION (RX 550 / Polaris12)

> **Archivo:** `projects/L2-RESIDENT-RENDERING/README.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (sin código, sin benchmarks, sin instalaciones)
> **Clasificación:** [DISEÑO/IDEA]. **PROVISIONAL** — no es tecnología consolidada.
> **Estado global:** **IDEA/DOCUMENTAL**. No se ejecutó ni se escribió ningún código.

---

## 1. OBJETIVO
Auditar documentalmente la idea de **mantener un target de renderizado "residente en L2"** en la RX 550
(Polaris12/GFX8), con foco en la variante "resolución interna reducida = tamaño del framebuffer <
L2 = permanece en caché a través de múltiples passes". Pregunta clave: dado que en GFX8 CB/DB
**bypassean el L2**, ¿qué rutas de escritura sí pasan por L2? ¿Es factible que una resolución
reducida se mantenga en L2 con 512 KB de capacidad? ¿Qué papel juega DCC?

## 2. AUDITORÍA CENTRAL (hardware target)
**La premisa "framebuffer < L2 = residente" se rompe de entrada en la ruta CB/DB** (ver
`POLARIS12-FEASIBILITY.md`):
- En GFX6–8 el L2 **solo es usado por shaders**. Render Backend, Copy Engine y CP bypass L2 y
  escriben directo al controlador de memoria.
- ⇒ La ruta fija de color/depth (la de los render-pass attachments) **nunca toca el L2**; el target
  de color/depth **no puede ser L2-residente** por diseño de hardware.
- ⇒ Solo la ruta **shader/compute** (texturas, SSBOs, image load/store) pasa por V$→L2→DRAM.
  Un target escrito por compute sí puede vivir temporalmente en L2.
- 512 KB L2 / 1080p RGBA8 (8.3 MB) = **6% del frame**. Una resolución interna de 320×180 RGBA8
  (230 KB) = ~45% del L2 → posible en teoría, si el resto de working set (texturas, geom) no lo evict.
- DCC/HTILE existen solo en la ruta RBE (y comprimen antes del DRAM); una ruta compute pierde DCC
  y gana compresión manual. No hay compresión de image store en GCN4 por hardware.

## 3. HIPÓTESIS (todas SIN VALIDAR — documental)
- H-I09-A: la variante "render-pass attachment residente en L2" es **inviable en GFX8** por bypass
  de L2 en CB/DB.
- H-I09-B: la variante **"compute-written + re-leído múltiples veces"** sí puede beneficiarse de L2
  para targets pequeños, pero el techo es ~230 KB (0.45× L2) y depende del working set del shader.
- H-I09-C: DCC/HTILE en la ruta RBE es ya el mejor "compresor de bandwidth" para la mayoría de los
  frames; una ruta compute lossy no supera a DCC+HTILE en writes.
- H-I09-D: la única métrica utilizable para medir esto es la diferencia de latencia de relectura
  de la misma imagen a través de passes; sin contadores L2 expuestos en radeontop/GFX8 esta
  verificación queda como un "unknown empirico".

## 4. ESTADO DE NOVEDAD (resumen; detalle en PRIOR-ART.md)
- Headline: **CONTRADICTED BY PRIOR ART** (residents-in-L2 de framebuffer =硬件 imposible en CB/RB
  GFX8; academic prior art sobre cache-residency aplica a LLC moderno o HW con L2 expuesto;
  Polaris12 no expone control de L2 residency).
- Sub-claim "compute image store + L2 re-use across passes": **RELATED PRIOR ART** (NVIDIA L2
  persistence, AutoScratch, GSPC LLC management) — pero todo sobre HW con L2 ≥2 MB y control de
  residencia expuesto; Polaris12 no lo tiene. NOVELTY UNKNOWN para "compute L2 residency on GCN4"
  (no se encontró implementación).
- Absencia tras búsqueda amplia = NOVELTY UNKNOWN (nunca "nadie lo hace").

## 5. FICHEROS DEL PROYECTO
| Archivo | Contenido |
|---|---|
| `README.md` | este índice |
| `PRIOR-ART.md` | encuesta de estado del arte (académico, vendor, hardware, driver) |
| `POLARIS12-FEASIBILITY.md` | viabilidad específica GFX8 (topología L2, CB bypass, DCC) |
| `EXPERIMENT-DESIGN.md` | diseño de experimentos de medición (sin ejecutar) |

## 6. CONCLUSIÓN DEL DISEÑO
I-09 es **IDEA/DISEÑO, PROVISIONAL**. El headline "maintain internal resolution in L2" es
**inviable en Polaris12** en la ruta CB/DB (bypass L2, sin control de residencia). La variante
compute (escritura por image store + relectura L2) es técnicamente posible pero **marginal**
(512 KB L2 ≈ una fracción de 1080p; DCC en RBE ya gana en la mayoría de escenarios; sin
contadores L2 la verificación es imposible sin instrumentación nueva). Recomendación:
**E (DISCARD)** para el headline; el sub-claim de reutilización compute-L2 se conserva como
**D (MORE RESEARCH)** condicionado a obtener contadores L2 en futuro (RCP/AMD_perfmon, SPM).