# I-06 — PREDICTIVE GHOST CACHE — Documentary Novelty Audit

> **Proyecto:** RX550/Polaris12 iterative rendering research
> **Fase:** FASE R-3 — Documentary novelty audit (SOLO DOCUMENTAL; no code, no system changes, no benchmarks, no installs)
> **Fecha:** 2026-09-22
> **Modo:** DOCUMENTAL ONLY
> **Archivo principal:** `04-IMPLEMENTACION/projects/GHOST-PREDICTIVE-CACHE/`
> **Archivos:** `README.md`, `PRIOR-ART.md`, `POLARIS12-FEASIBILITY.md`, `EXPERIMENT-DESIGN.md`

---

## 1. IDEA EN UNA LÍNEA

A GPU-side **cache predictor** ("ghost cache") that predicts which textures/tiles/mips
the renderer will need in future frames (using camera motion + access patterns) and
prefetches/warms them in L2/VRAM *before* they are requested, to cut fetch latency on a
sparse-IO-bound IMR like Polaris12.

## 2. ESTADO

| Atributo | Valor |
|---|---|
| **IDEA** | I-06 — Predictive Ghost Cache |
| **NOVELTY STATUS** | **PARTIALLY NOVEL** (scope-resolved; ver desglose por sub-claim abajo y `PRIOR-ART.md` §6) |
| **Sub-claims** | 1) **Ghost cache genérico** (prefetch por patrones de acceso + anti-pollution) → **KNOWN**<br>2) **Prefetch predictivo por cámara** (predecir mips/tiles de textura y calentarlos "una vuelta antes") → **KNOWN VARIANT** en engines (UE/Unity/id); el nivel cache-GPU específico no apareció en fuentes primarias → **POTENTIALLY NOVEL** como política, pero **CONTRADICTED*/NO-FEASIBLE a nivel HW en GCN4** (sin API de control de cache)<br>3) **Servicio predictivo software (userland/driver API) en Polaris12** → **PARTIALLY NOVEL**; se solapa con el proyecto in-repo `GHOST` (localidad/prefetch) |
| **DOCUMENTAL depth** | ~30 fuentes primarias/comunitarias citadas en `PRIOR-ART.md` |
| **Patentes** | NOT AUDITED en este pase (ver §6) |
| **RECOMMENDED STATUS** | **C** — refinar el sub-claim a "servicio de prefetch predictivo software/residencia" y documentar explícitamente que el ghost cache a nivel HW cache no es realizable en Polaris12 |

> **Relación con proyectos in-repo:** se solapa con `GHOST/GHOST-CACHE-DESIGN.md` (hipótesis GHOST-CACHE = custodiar asignación/orden de accesos para maximizar hit). I-06 es la versión *predictiva/temporal* (predecir el working set futuro); evita duplicar la vía de localidad/asignación que ya es de GHOST.

## 3. NOVELTY STATUS — RESUMEN POR SUB-CLAIM

| Sub-claim | Estado | Evidencia clave |
|---|---|---|
| Prefetch general / ghost lists / politicas anti-pollution (cache lineal) | KNOWN | ARC ghost lists (Megiddo & Modha 2003), bypass caches (IPDPS 2013), MLOP (2020), hardware prefetchers |
| Prefetch de *texturas* en GPU (demand/anticipado por localidad) | KNOWN | Igehy 1998 (texture prefetch a través de send/queues); Hakura & Gupta 1997; caches de texturas por bloque |
| **Prefetch predictivo por mov. de cámara** en engines | KNOWN VARIANT | UE texture streaming (preload por cámara), Unity (SetPreloading), idTech5 (análisis feedback + upsampling), Dumont 2003 (prediction camera), NeuralPVS 2025 (prefetch/streaming desde PVS aprendido) |
| **Elevar esa predicción a Nivel caché-GPU (L2/texture cache) en un IMR de escritorio (Polaris12)** | **POTENTIALLY NOVEL** (none found) — pero **NO-FEASIBLE por HW** | Sin instrucción u API de prefetch de texturas en RADV/Vulkan para GCN4; control L2 estilo CUDA es Ampere+ (cc≥8.0); PRT/sparse roto en Polaris (CachyOS #930, fix 2026-March) |
| Servicio predictivo **software** (predice Mip/Tile → pide residencia/sparse o copia SDMA/CPU antes del uso) | **PARTIALLY NOVEL** | No aparece en fuentes primarias para GCN4 desktop; el mecanismo de predicción está publicado (campos de visión + historial), la integración como servicio en Polaris12 no (NO CLAIMED de otro modo) |

## 4. ANÁLISIS RESUELTO POR COMPONENTE (I-06)

- **CÁMARA** — predictibilidad de visibilidad futuro: conocida y usada comercialmente
  (UE preloads mipmap levels según la cámara; Dumont 2003 usó "prediction camera" desplazada
  hacia adelante). No es nuevo.
- **WORKING SET futuro en un IMR** — no hay PVS comercial en IMR: el frame siguiente solo se
  conoce tras rasterizar el actual (los engines predicen con heurísticas de distancia/velocidad).
  La predición es estadística, nunca exacta.
- **MECANISMO CACHE** — Polaris12 CB/DB **evitan** L2 (escriben vía RBE/DCC) → el cuello de
  "fetch" es **textura→L1(V$ 16KB/CU)→L2(512KB)→VRAM/GTT**, no el depth buffer. Igehy 1998 ya
  demostró que prefetch *software* de texturas en HW de esa era ganaba hasta ~30% si la fila es
  previsible; la contrapartida moderna es el auto-pacing fetch-bound de ES-01 (p50 flat, p99 ∝
  fetch) → el prefetch ataca el α del p99.
- **HW DESKTOP GCN4** — no existe API de control de L2/cache de texturas para aplicaciones
  (RADV no expone ninguna; CUDA L2 residency/access-window es Ampere+); PRT/texture sparse está
  presente pero **inestable en Polaris** (issue público 2026). La única vía real es un servicio
  *software* de "prefetch userland" → resident VRAM, o alimentar `tile-cache` vía accesos previos
  con texturas pequeñas.

## 5. VEREDICTO RC-* (RÁPIDO)

| Métrica | Leyenda |
|---|---|
| **FEASIBILITY VERDICT (Polaris12/IMR)** | PARTIALLY FEASIBLE — como servicio software predictivo (userland, sin tocar kernel); NO-FEASIBLE como ghost cache a nivel de L2/texture-cache HW |
| **TECHNICAL PLAUSIBILITY** | HIGH (mecanismo de predicción publicado y comercial) / LOW en el nivel cache-HW (sin HW support en GCN4) |
| **IMPLEMENTATION COST** | MEDIUM-HIGH (servicio de residencia/prefetch + heurística de cámara + telemetría) en harness sintético; **sin tocar el kernel** |
| **RISK** | Alto de *pollution* (prefetch agresivo llena L2/VRAM y puede empeorar el p99 si compite con el frame actual); colisión con GHOST (no duplicar); PRT inestable en Polaris |
| **DEPENDENCIES** | Harness sintético existente (F2/FETCH + cámara sintética), runner K, Vulkan; lectura de `mem_busy`/`frametime`; **NINGUNA instalación nueva**; control de prioridad del "ghost" para no robar BW al frame actual |
| **RECOMMENDED STATUS** | **C** (escala en §7; detalle en `PRIOR-ART.md` §6) |

## 6. LIMITACIONES DEL AUDIT (transparencia)

1. **Patentes: NO auditadas** en este pase (igual que I-02). Si el sub-claim software
   avanzara, requiere audit de patentes separado (UE: "residency management para streaming";
   id: "feedback buffer for texture paging"; Nanite/Nvidia: prefetch por PVS aprendido).
2. **"No encontré en ~25 búsquedas" ≠ "no existe"**: se declara solo lo que la búsqueda
   realmente cubrió (rutas/cadena en `PRIOR-ART.md` §7).
3. **Corrección de cita**: "Ghost Cache" de la literatura de *seguridad* (CCS 2025,
   `THU-HAS/ghostcache`) NO debe confundirse con el concepto de cache predictivo: es un
   ataque de factor de conflicto cache (RISC-V/ARM). Se documenta para no contaminar las
   búsquedas.

## 7. ESCALA DE ESTADO RECOMENDADO (A/B/C/D/E)

- **A** — CONTRADICTED BY PRIOR ART / abandonar el claim.
- **B** — KNOWN tal como está formulado; usar como referencia, no como hipótesis propia.
- **C** — PARTIALLY NOVEL: refinar el alcance a un sub-claim específico y documentarlo.
- **D** — suficientemente concreto para formalizar una hipótesis medible.
- **E** — pasar a diseño de experimento (FASE G/K) con el claim ya acotado.

---

## ANEXO — Formato ordenado (requerido por FASE R-3)

- **IDEA:** I-06 — Predictive Ghost Cache.
- **NOVELTY STATUS:** PARTIALLY NOVEL (el sub-claim realizable —servicio predictivo software— no
  encontrado en fuentes primarias para GCN4 desktop; los mecanismos de predicción son KNOWN).
- **KEY PRIOR ART (w/URLs):** lista completa en `PRIOR-ART.md`; highlights: Igehy 1998 (texture
  prefetch), Dumont et al. 2003 (prediction camera), UE5 VT ("reactive by nature"), UE texture
  streaming, idTech5 van Waveren, NeuralPVS 2025, ARC/bypass/MLOP (ghost lists), NVIDIA L2 control.
- **OPEN SOURCE IMPLS:** Mesa/RADV (sin API de prefetch para GCN4), amdgpu PRT (roto en Polaris),
  arc-pre.loads en engines (UE: `r.Streaming.*`; Unity: `StreamingController.SetPreloading`),
  FidelityFX no relevante. Ver `PRIOR-ART.md` §7.
- **ACADEMIC:** Igehy 1998; Hakura & Gupta 1997; Dumont/Pellacini/Kautz 2003; Megiddo & Modha 2003
  (ARC ghost lists); bypass buffer (IPDPS 2013); MLOP (2020); NeuralPVS 2025.
- **COMMERCIAL:** UE5 VT/SVT (reactive), UE texture streaming (camera-based preload), Unity mipmap
  streaming (SetPreloading), id Tech 6 Neocodex/feedback, consolas (Kraken/BCpack + DirectStorage
  — decompresión por HW que habilita streaming reactivo), CUDA L2 access-policy (Ampere+, no GCN4).
- **POLARIS RELEVANCE:** alta a nivel de *fetch* (ES-01: p99 ∝ fetch; L1 16KB/CU, L2 512KB,
  CB/DB bypass); baja a nivel HW-cache (sin control). El cuello real de streaming es VRAM→L2,
  no L2→VRAM.
- **FEASIBILITY VERDICT:** PARTIALLY FEASIBLE (servicio software predictivo; sin tocar HW/kernel).
- **TECHNICAL PLAUSIBILITY:** HIGH (mecanismo de predicción probado) / LOW en nivel cache-GPU.
- **IMPLEMENTATION COST:** MEDIUM-HIGH (servicio + heurística + residencia, en harness sintético).
- **RISK:** HIGH (pollution de L2/VRAM; colisión con GHOST; PRT inestable en Polaris).
- **DEPENDENCIES:** harness F2 + runner K + Vulkan; sin instalaciones; requiere control de
  prioridad/errores de PRT.
- **RECOMMENDED STATUS:** **C**.
