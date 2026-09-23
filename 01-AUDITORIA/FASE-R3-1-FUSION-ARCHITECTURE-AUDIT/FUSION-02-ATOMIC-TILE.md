# FUSION 02 — "EL TILE ES LA UNIDAD ATÓMICA"

> **Archivo:** `FUSION-02-ATOMIC-TILE.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** unificación de subsistemas alrededor de un "tile lógico" (TBDR emulado + tile
> delta reuse + L2-resident + Ghost Cache + ROP-offload)

---

## 1. Auditado: ¿qué es un "tile" en Polaris12?

| Componente HW | Unidad real (evidencia) | Fuente |
|---|---|---|
| Rasterizador GCN | **8×8** píxeles (quads/tiles de 4), wavefront 64 lanes | GCN execution patterns |
| RBE / Color Block | caches de color 16 KB, depth 4 KB; ROP unit por RB | GCN whitepaper |
| HTILE (depth) | bloque **8×8** (`ADDR_HTILE_BLOCKSIZE_8`) | mesa-dev 2017 |
| DCC | bloques descomprimidos **64/128/256 B**; mínimo comprimido **32 B** (dGPU); Polaris hasta 8:1@256B | mesa-dev 2017 / Polaris whitepaper |
| Microtiling GFX6-8 | microtiles **8×8** (o 8×8×4/8×8×8), macrotiles 2D | linux-amdgpu patching / Radeon docs |
| Vulkan tiling | OPTIMAL = swizzle no-lineal propietaria; LINEAR = row-major | Khronos |

**¿32×32 es unidad natural?** **NO en GCN como unidad física.** 32×32 es un *tamaño de tile común de la
industria* (PowerVR 32×32, Mali 16×16, Adreno 32/64×…), pero en Polaris12 las unidades físicas son 8×8
(raster/HTILE) y bloques de bytes (DCC). 32×32 (o 16×16/64×64) es una **decisión lógica**, no una constante
descubierta. La afirmación "32×32 RGBA = unidad natural del hardware" **queda CONTRADICTED como hecho HW**;
conserva valor como granularidad logística (binning app-side).

## 2. El problema fatal: "¿el tile permanece en L2?"

**CONTRADICTED.** En GFX8, el **Render Backend (CB/DB) BYPASSA L2**: los writes de color/depth van directo al
controlador de memoria ("final pixel colors are written to the memory controllers and bypass the L2 cache").
Consecuencia directa de I-01/I-09 (ya auditadas en R-3):
- `tile size < L2 size` NO implica residencia: los writes de attachments **jamás entran** a L2.
- 512 KB L2 no es un "pool gestionable": sin API de residencia/pinning userspace en amdgpu (CUDA L2-persist
  es Ampere+, inexistente en GCN4).
- La única vía de releycado barato es la **ruta shader** (texture reads / compute UAV reads), que SÍ pasa por
  L2 — relevante para compute-path, no para el CB-path.

## 3. "Render tile by tile" sobre una GPU IMR

Significado real (prior art): binning de geometría por tiles al estilo freedreno a6xx binning pass (HW +
scanout), Vega DSBR (grid de bins, geometría una vez, pixel-shading diferido), o bucket rendering clásico
(Cox & Bhandari 1997, 32×32 vs 128×128). Costes Vulkan en IMR para un software-tile:
- subpass merge / `loadOp`–`storeOp` DONT_CARE; `VK_KHR_dynamic_rendering_local_read`;
  `VK_EXT_subpass_merge_feedback`;
- dependencias byRegion (evitar barriers globales que flushing sincronizan tile caches);
- lecturas externas del framebuffer = el "enemigo" (invalidan la localidad).

**No existe medición publicada del coste de software-tiling en Polaris12** (NOVELTY UNKNOWN en lo cuantitativo).

## 4. Auditado: ¿granularidades compatibles?

Los subsistemas operan en granularidades **distintas e incompatibles**:
- TBDR emulado → tile de *render/pixel* (lógico, elige tú: 16/32/64).
- Tile delta reuse → tile de *comparación de contenido* (imagen previa);
- L2-resident → granulosidad de *bytes/caché* (bloques DCC 64-256 B, no píxeles);
- Ghost Cache → granulosidad de *textura/mip* (no píxeles);
- ROP-offload → granulosidad de *cuenta SSA hardware*.

**Resultado:** la "unidad atómica común" no es unívoca. Agruparlas alrededor de un mismo tile lógico es
**agrupación artificial** de mecanismos que operan en capas distintas (imagen / caché / textura / hardware-cop).
El único tile con significado físico es el 8×8 de raster/HTILE y los bloques de DCC.

## 5. Falsabilidad

Hipótesis falsable mínima: *"existe un tamaño de tile lógico (16/32/64) cuyo binning en escena controlada
reduce el tráfico real medible de fill/compute frente a fullscreen, sin pérdidas de sincronización"*.
Falsable con microbenchmark de frametime + telemetría read-only. La parte "tile = unidad atómica única de
todo el ecosistema" se **rechaza a priori** por heterogeneidad de granularidades.

## 6. Veredicto de fusión

- **Se rechaza la versión fuerte** (un tile único común). 
- **Se conserva** como "tile lógico a nivel aplicación" para binning/partial-redraw (I-02) — KNOWN VARIANT.
- **Blockers:** residencia L2 (HW-limited), control DCC/HTILE (driver-level), occupancy.
- **Estado:** **REJECTED/FALSIFIED** para la unificación-residencia; **RESEARCH ONLY** para tile-lógico app-side.