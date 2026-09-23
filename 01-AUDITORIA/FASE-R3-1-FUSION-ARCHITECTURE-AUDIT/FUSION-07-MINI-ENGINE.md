# FUSION 07 — "MINI-ENGINE" (arquitectura de largo plazo)

> **Archivo:** `FUSION-07-MINI-ENGINE.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** Fusión 2 + Fusión 3 + Fusión 6 (sistema completo).
> **Clasificación inicial: ARQUITECTURA CONCEPTUAL DE LARGO PLAZO. NO implementar.**

---

## 1. Auditar como sistema: grafos de flujo

**Dependency graph (resumido):**
```
MINI-ENGINE
├─► Fusión 2 (tile lógico) ──► binning/partial-redraw ──► FP2 (bloqueado por residencia L2)
├─► Fusión 3 (memoria invertida) ──► hot set GTT/VIS ──► FP3 (necesita mediciones BW)
└─► Fusión 6 (reconstrucción) ──► OF+FG async ──► FP6 (rechazada en 1080p; calibración 540p)
```
**Data flow:** RAM → (compresión delta app) → GTT/VIS → shader (L2 read) → tiles lógicos → present →
(reconstrucción compute). El "hot set" no puede ser L2; el destino controlable es VIS/GTT.

**Memory flow:** el camino CB/DB **omite L2** → attachments fuera de la jerarquía deseada; solo el tráfico
de texturas/compute la usa.

**Synchronization flow:** en un IMR con software-tiling + FG, los fences crecen (bin→shade→resolve→flow→
blit→present); el overlap async reduce pero no elimina sincronización.

**Compute/graphics flow:** ACE concurrentes comparten CUs; en fetch-bound el overlap "gratis" es improbable
de mantener; en saturación hay contención.

**Failure modes:** (1) sync cubre la ganancia; (2) banda de VRAM saturada por doble buffer; (3) presentación
al costo de latencia; (4) calidad percibida peor que calidad fija; (5) DCC perdido en todos los pasos
compute; (6) colapso por presupuesto de 35 W.

## 2. Clasificación de componentes

| Componente | Independently useful | Mutually dependent | Optional | Mutuamente excluyente |
|---|---|---|---|---|
| Partial-redraw (I-02) | + (estático) | ~ | zombies w/ post-procesado | — |
| Hot set GTT/VIS (I-03) | + (fetch-bound) | necesita L1/L2 hits | — | — |
| Binning app-side (I-02/F2) | + | — | — | excluye TBDR SW pure |
| Reconstrucción (I-06/F) | — en 1080p | depende de concurrency | require calibración | excluye "render real = show" |
| Governor (I-08) | + | — | — | — |

## 3. Prior art del mini-engine (búsqueda obligatoria)

- **Software tile renderers / hybrid / compute:** CuRast (TUW 2026) — rasterizador computacional (RTX),
  motor sin ROPs; vk_lod_clusters (NV) — SW raster en compute para detail; CUDARaster (2011).
- **Tile-based emulation sobre IMR:** freedreno binning (HW-fused), DOOM Eternal 256×256 coarse tiles
  (culling, no tiling de render), Vega DSBR.
- **Low-end/APU renderers:** EmberGL (tile-based software GPU para small embedded) — rescate del diseño,
  distinto resource profile; llvmpipe/SwiftShader = CPU-side.
- **Voxel/compute-style engines:** Atomontage (lineage: Outcast'99, Delta Force'98) — render sin raster
  convencional.

**Componentes: KNOWN. Combinación completa (TBDR SW + compute FG + memoria invertida en GCN4 low-end):
no encontrada en fuentes públicas → POTENTIALLY NOVEL (combinación), nunca "PROVEN NOVEL"; requiere chequeo
de patentes/DB antes de afirmar más.**

## 4. Restricciones que configuran el sistema (no preferencias)

- Un IMR GFX8 no tiene tile store de HW: toda residencia útil es shader-path (L2) o VRAM(VIS).
- Cualquier escritura compute pierde DCC/HTILE y bypass-L2.
- Presupuesto 35 W y 8 CUs: la reconstrucción compite con el render.
- El único "motor" realista a largo plazo sería un **renderer GPU-driven + partial-redraw + governor**,
  NO una TBDR software-computacional.

## 5. Falencia final

- **Estado del sistema completo:** **BLOCKED / RESEARCH ONLY** — depende de F5 y F6 que ya están
  REJECTED/FALSIFIED en su versión fuerte; queda sólo la agregación a largo plazo de piezas independientes.
- **Veredicto de fusión:** conceptualmente interesante, **técnicamente de largo plazo, sin evidencia de que
  la combinación gane**; cada pieza se valida por separado (I-02, I-08, BERRETA) antes de pensar en el motor.