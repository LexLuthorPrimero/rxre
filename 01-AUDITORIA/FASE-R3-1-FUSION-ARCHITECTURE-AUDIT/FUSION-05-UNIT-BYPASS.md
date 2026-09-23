# FUSION 05 — "BYPASS DE LA UNIDAD SATURADA" (ROP → compute) — AUDITORÍA PRIORITARIA

> **Archivo:** `FUSION-05-UNIT-BYPASS.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** ROP-offload + Async auxiliary renderer + TBDR.

---

## 1. AUDITAR PRIMERO: ¿tiene sentido comparar A vs B?

**A) Graphics pipeline → color attachment** vs **B) Graphics/compute → SSBO/image → reconstrucción/blit/present**

El modelo mental "ROPs saturados + CUs libres" es **CONTRADICTED por mecanismo** en este chip:
- En GCN, el pixel shader se ejecuta en el **mismo array de CUs** ANTES de que el RBE vea bytes: si el RBE
  (ROP) está saturado, los CUs YA entregaron los fragmentos. ROP-busy alto NO implica CU idle.
- Las CUs pueden estar ociosas en **fetch-bound** (ES-01/ES-03: latencia de memoria) — pero ahí el
  bottleneck es memoria, no ROP.
- Balance del chip: **32 SP/ROP** (512 shaders / 16 ROPs) — extremo equivocado frente a GPUs donde el
  software raster gana (100+ SP/ROP).

**Prior art que ya cuantifica:** Laine & Karras 2011 (CUDARaster): pipeline software completo a 2–8× más
lento que HW en GTX 580 (2011). LucidRaster: OIT exacta en compute, ~3× más lenta que alpha HW. CuRast 2026:
gana SOLO para primitivas pixel-sized o instanciadas (no nuestro caso típico). Ninguno de los tres probó GCN.

## 2. Inventario de funciones ROP no trivialmente reemplazables

| Función fixed-function | Reemplazo por compute | Veredicto (evidencia) |
|---|---|---|
| **Blending** (todos los modos; dual-source, advanced) | atomics/UAV por píxel | FUNCIONALMENTE posible; pérdida de DCC; contendría atomics (bandwidth). **FEASIBLE / LOSSY** |
| **MSAA resolve** | resolve en shader (blit de muestras) | práctica común; coste alto por muestras. **FEASIBLE** |
| **Depth/stencil** | atomicMin/write per pixel + propio HTILE | pierde HTILE (que comprime/ordena en RB); depth shader-visible deja de comprimir bien (GPUOpen). **NO "sin pérdida"** |
| **Format conversion** | shader conversion | FEASIBLE (coste ALU) |
| **DCC/color compression** | UAV writes **deshabilitan DCC** | **CONTRADICTED "sin pérdida"** (GPUOpen: "UAV writable disallows compression entirely") |
| **Ordering / RMW** | atomics + fence | coste y semántica de orden → requiere sync (porRegion/UAV barrier) |
| **Rasterización (setup/interpol)** | vertex/geometry fuera → scan en shader | FEASIBLE pero ese NO es "trabajo de ROP" (es Geometry/CU) |

**Conclusión de función:** nada del comportamiento *funcional* es imposible en compute (CUDARaster lo
demostró); pero en GFX8 la **compresión de color/depth y el bypass-L2 del RB** se pierden en el camino
compute → el coste total (bandwidth + atomics + sync) sube. No hay medición GCN publicada del swap → las
cantidades son UNKNOWN por medición, los mecanismos están VERIFICADOS.

## 3. Hipótesis falsable (la única que justifica la fusión)

La arquitectura solo tiene sentido si existe un workload donde:
1. fixed-function path es limitante (ROP-busy ~100% medible, NO asumido);
2. compute tiene capacidad disponible (CU occupancy/occio medibles);
3. compute replacement cuesta MENOS total (bandwidth+atomics+sync);
4. sincronización no elimina la ventaja;
5. memoria adicional no elimina la ventaja.

**"ROP busy alto" NO es prueba suficiente.** Ver EXP-F5-A en EXPERIMENT-ROADMAP (diseño mínimo).

## 4. Relación con otros componentes

- **Async auxiliary renderer (I-10):** la pieza útil de esta fusión es mover trabajo ligero compute (shake-
  independent) a la cola async — no "ROPs por compute". KNOWN VARIANT (DOOM, Division 2).
- **TBDR:** irrelevante aquí — el bypass se plantea por celda saturada, no por tiling.

## 5. Veredicto de fusión

- **F1 (fusión ROP-offload completa):** **REJECTED/FALSIFIED** como mejora esperada; la premisa central
  (CUs libres + caminos equivalentes) contradice la topología GFX8 y las constantes publicadas. Valor
  residual: experimento mínimo de falsación documental (EXP-F5-A) y el co-scheduling async (con BERRETA).
- **Novedad:** KNOWN VARIANT (componentes); KNOWN VARIANT como combinación (CUDARaster precedent era ya de
  hace 15 años); aplicación GFX8 específica sin medición = NOVELTY UNKNOWN por datos.