# IDEA I-01 — TBDR EMULATION ON IMR (RX 550 / Polaris12)

> **Archivo:** `04-IMPLEMENTACION/projects/TBDR-IMR/README.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (sin código, sin benchmarks, sin instalaciones)
> **Clasificación:** [DISEÑO/IDEA]. **PROVISIONAL** — no es tecnología consolidada.
> **Estado global:** **IDEA/DOCUMENTAL**. No se ejecutó ni se escribió ningún código.

---

## 1. OBJETIVO
Auditar documentalmente la idea de **emular renderizado tile-based deferred (TBDR) sobre un motor
inmediato de renderizado (IMR)** en la placa objetivo RX 550 (Polaris12/GFX8): es decir, ¿puede un
algoritmo *software* de tiling (binning + render por tile, con el framebuffer residente en caché) dar
un beneficio real de ancho de banda/residencia frente a la ruta IMR de fábrica, y qué mecanismos
reducirían memoria de verdad en esta GPU concreta?

## 2. AUDITORÍA CENTRAL (hardware target)
La premisa de "tile cabe en caché => framebuffer residente" **se evalúa contra la topología GFX8** (ver
`POLARIS12-FEASIBILITY.md`):
- L2 = 512 KB (2 slices de 256 KB), 16-way, 64 B/line, write-back/write-allocate. V$ = 16 KB/CU.
- **En GFX6–GFX8 el L2 **solo** lo usan los shaders.** Render Backend, Copy Engine y Command Processor
  **bypassean el L2** y escriben directo al controlador de memoria ("GFX6-8: L2 used by shaders only.
  GFX9-10: used by everything" — Mesa-dev 2019; GCN whitepaper; GPUOpen RDNA slides).
- Los caches de tile del render backend (color ~16 KB, depth ~4 KB) y la compresión DCC/HTILE del RBE
  absorben la escritura de color/depth **sin pasar por L2**.
- Conclusión estructural: en la ruta RB/CB fija el framebuffer de color/depth **nunca es residente en L2**,
  por diseño. Solo las lecturas/escrituras de shader (texturas, SSBO, image load/store) pasan por L2.

## 3. HIPÓTESIS (todas SIN VALIDAR — documental)
- H-I01-A: un renderer software por tiles/particiones de pantalla **no puede reducir** ancho de banda de
  color/depth en Polaris12 porque la ruta CB/RB ya escribe comprimida (DCC/HTILE) y bypasea L2.
- H-I01-B: el único beneficio direccional residiría en **localidad de la ruta shader** (texturas/imagenes:
  V$→L2): un binning + scissor por tile mejora la localidad de lectura, no la escritura de frame.
- H-I01-C: la variante "deferred por tiles vía compute" equivale de facto a rasterización software en
  compute (idea I-04, ya auditada y **CONTRADICTA POR PRIOR ART** en Polaris12).

## 4. ESTADO DE NOVEDAD (resumen; detalle en PRIOR-ART.md)
**KNOWN VARIANT** — re-combinación de técnicas todas documentadas (binning/scissor, tiled lighting
Forward+, decoupled/dsort shading, bin-buffers en drivers móviles y VectorFabrics/freedreno) sobre el
suelo HW Polaris12. El sub-claim "framebuffer L2-residente" es **CONTRADICTO POR PRIOR ART** (CB/RB
bypasean L2 en GFX8). No se encontró ninguna implementación ("TBDR emulated on IMR desktop GPU") como
producto; la ausencia tras búsqueda amplia se registra como **NOVELTY UNKNOWN**, no como "nadie lo hace".

## 5. FICHEROS DEL PROYECTO
| Archivo | Contenido |
|---|---|
| `README.md` | este índice |
| `PRIOR-ART.md` | encuesta de estado del arte (académico, open source, comercial, drivers) |
| `POLARIS12-FEASIBILITY.md` | viabilidad específica GFX8 (topología L2/CB/RBE, bandas) |
| `EXPERIMENT-DESIGN.md` | diseño de experimentos de medición (sin ejecutar) |

## 6. CONCLUSIÓN DEL DISEÑO
I-01 es **IDEA/DISEÑO, PROVISIONAL**. La variante plena (tiling software delegado al framebuffer,
residente en L2) es **no viable estructuralmente** en GFX8 por bypass de L2 en la ruta RB/CB; la
variante útil de la intuición (binning/scissor + localidad de la ruta shader, y deferred por tiles de
iluminación vía compute) es tecnología **ya conocida** (a6xx binning, Forward+, DCC/HTILE del RBE).
Recomendación de estado: **D→E** (documentar y no perseguir como feature de performance; conservar el
sub-estudio de localidad de ruta shader como medición opcional).
