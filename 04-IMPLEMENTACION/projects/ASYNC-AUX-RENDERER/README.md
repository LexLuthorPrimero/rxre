# I-10 — ASYNC AUXILIARY RENDERER — Documentary Novelty Audit

> **Proyecto:** RX550/Polaris12 iterative rendering research
> **Fase:** FASE R-3 — Documentary novelty audit (SOLO DOCUMENTAL; no code, no system changes, no benchmarks, no installs)
> **Fecha:** 2026-09-22
> **Modo:** DOCUMENTAL ONLY
> **Archivo principal:** `projects/ASYNC-AUX-RENDERER/`
> **Archivos:** `README.md`, `PRIOR-ART.md`, `POLARIS12-FEASIBILITY.md`, `EXPERIMENT-DESIGN.md`

---

## 1. IDEA EN UNA LÍNEA

Run auxiliar render/especialista (≈"auxiliary renderer": sombras, depth/Hi-Z, AO, SSR, pre-pass de
post, simulación física/IA visual) en **cola compute async (ACE)**, en paralelo con la cola gráfica
(IMR), para rellenar los huecos de ocupación del chip y reducir el frametime total en Polaris12 — el
mismo patrón async-compute que hoy usan DOOM/Cyberpunk/Frostbite y que este laboratorio ya planteó
como ASY-01/BERRETA.

## 2. ESTADO

| Atributo | Valor |
|---|---|
| **IDEA** | I-10 — Async Auxiliary Renderer |
| **NOVELTY STATUS** | **KNOWN VARIANT** (async-compute es una técnica madura y documentada; ver sub-claims) |
| **Sub-claims** | 1) **Ejecutar pasos de render en cola compute async** → **KNOWN** (computación async GPU on GCN: AMD GDC17, Vulkan samples async_compute, DOOM, Cyberpunk 2077 GDC23, Frostbite FrameGraph GDC17)<br>2) **"Auxiliary renderer" completo paralelo (segunda apertura/reflexión/sombra en cola async)** → **KNOWN VARIANT** (SSR async en R*: Rockstar; Hi-Z+SSAO async durante shadowmaps: Cyberpunk; async AO en Frostbite): el sub-claim demo es re-ejecutar un *pipeline* auxiliar alejado del G-buffer principal |
| **DOCUMENTAL depth** | ~25 fuentes primarias citadas en `PRIOR-ART.md` |
| **Patentes** | NOT AUDITED en este pase (ver §6) |
| **RECOMMENDED STATUS** | **C** — refinar el sub-claim a *cuánta ganancia real de overlap hay con 2 ACE en un IMR de 8 CUs* y **coordinarlo con ASY-01/BERRETA** (ambos compiten por el mismo experimento). |

> **Relación in-repo crítica:** este proyecto colisiona de frente con `BERRETA` / `ASY-01` (overlap
> graphics+compute en la misma GPU). I-10 = el *concepto* de "renderer auxiliar async"; BERRETA = el
> *diseño de medición* del overlap. **No se debe duplicar el runner/experimento; I-10 debe actuar
> como variante de workload (qué es "auxiliar") sobre el diseño de medición de BERRETA.**

## 3. NOVELTY STATUS — RESUMEN POR SUB-CLAIM

| Sub-claim | Estado | Evidencia clave |
|---|---|---|
| Async compute en GCN (ACE, colas múltiples) | KNOWN | AMD Polaris whitepaper (ACE/HWS), GDC17 "Async Compute", RADV docs |
| Cargas async típicas (AO, SSR, Hi-Z, sombras) junto a la cola gráfica | KNOWN / Shipped | DOOM (idTech6), Cyberpunk 2077 (GDC23), Frostbite (GDC17), Division 2 (GDC19), Vulkan samples async_compute, Rockstar async SSR |
| **"Auxiliary renderer" completo** (segundo pipeline que renderiza su propia imagen en cola async) | KNOWN VARIANT | R* async SSR (compute sobre buffers en cola async); Cyberpunk async (SSR/Hi-Z/SSAO fuera de la cola GFX); en Vulkan el patrón "second pass computed separately" está documentado en samples/tutorial |
| **Cuantificar el overlap real en Polaris12 (8 CUs, 2 ACE, fetch-bound)** | **NO-FEASIBLE de afirmar sin medición; el overlap está por medida, no por literatura** | (mira `POLARIS12-FEASIBILITY.md` §3) |

## 4. ANÁLISIS RESUELTO POR COMPONENTE (I-10)

- **ACE/HW (Polaris whitepaper):** 4th-gen GCN tiene ACEs + HWS + motores de DMA capaces de
  despachar en paralelo. Polaris RX480-class ~4 ACE + 2 HWS; la clase Polaris12 (RX550) hereda el
  modelo de ACE single-pair con 2 motores (confirmado por arquitectura GCN4 de gama baja; no hay
  ficha oficial pública detallada de Lexa => ver `FEASIBILITY` §1). Se despacha a la **misma
  shader array de 8 CUs** (CU Reservation, QoS, Quick Response Queue). => *async NO añade CUs;
  reordena/solapa trabajo pendiente.*
- **Señal de ocupación (in-repo):** ES-01 → fetch-bound + power auto-paced. El hueco a rellenar es
  **memoria/caché**, no CU ociosas. A diferencia de los casos publicados (DOOM: CUs ociosas por
  raster-ROP-heavy; Cyberpunk: ocupan gap durante shadowmaps), aquí el cuello es **fetch**. Un
  renderer auxiliar *compute-heavy* dificilmente cabe "gratis" si el cuello es memoria compartida.
- **Puente con Vulkan:** `VK_KHR_timeline_semaphore`/binary semáforos para fork-join async;
  `queueFamily` compute en RADV (GFX8 en Vulkan 1.4) → el *mecanismo* de ejecutar una cola async
  adicional está soportado en Polaris12/RADV (ver `FEASIBILITY` §2).
- **Sync points:** todo auxiliar async que *lea* el frame GFX requiere esperar (dependency) →
  el patrón real documentado es **fork-join**: lanzar lo que no depende del frame (sombras de
  luces estáticas, Hi-Z del frame previo, SSAO del depth previo, SSR con buffers viejos) y hacer
  join antes del consumo. (Cyberpunk GDC23; Frostbite FrameGraph explícito: sync al pasar el
  "Antes" y Dependencia.)

## 5. VEREDICTO RC-* (RÁPIDO)

| Métrica | Leyenda |
|---|---|
| **FEASIBILITY VERDICT (Polaris12/IMR)** | FEASIBLE a nivel de API (RADV support, 2 colas), **PERO** la ganancia depende de un cuello de ocupación que ES-01 sugiere ausente (fetch-bound) → **low expected overlap**, medible |
| **TECHNICAL PLAUSIBILITY** | HIGH (técnica probada) / LOW-MEDIUM la **cuantificación** en este chip específico |
| **IMPLEMENTATION COST** | MEDIUM (workload sintético ya diseñado en ASY-01/BERRETA; adaptar el auxiliar como nueva variante) |
| **RISK** | Alto de **diagnóstico mal atribuido**: async-compute falla suele enmascararse (Division 2 GDC19 "async stalling the gfx pipe"); power cap (ES-06) puede aplastar el hipotético overlap; **colisión con BERRETA** (no duplicar runner) |
| **DEPENDENCIES** | BERRETA/ASY-01 (diseño de overlap), runner K, harness sintético, Vulkan; **NINGUNA instalación nueva** |
| **RECOMMENDED STATUS** | **C** (ver escala §7); integrarse como variante de BERRETA, no proyecto independiente |

## 6. LIMITACIONES DEL AUDIT (transparencia)

1. **Patentes: NO auditadas** (mismo criterio que I-02/I-06). Async-compute es área llena de patentes
   de vendors/engines; audit aparte si fuese a producción.
2. **Sin ficha pública oficial de Lexa** sobre número exacto de ACE/HWS → se usa el modelo de
   arquitectura GCN4 de Polaris + confirmación de RADV de soporte de cola compute en GFX8; marcado
   como supuesto razonable, no dato oficial (en `FEASIBILITY` §1).
3. **"No hay literatura sobre overlap en RX550"** ≠ "no existe": solo se declara lo no encontrado en
   las ~14 búsquedas registradas (`PRIOR-ART` §6).
4. **Colisión con BERRETA/ASY-01:** este audit reclama explícitamente que la *medición* del overlap
   ya fue diseñada in-repo (BERRETA). I-10 se limita a aportar el sub-claim "renderer auxiliar
   completo" como *variante de workload*; sin runner nuevo.

## 7. ESCALA DE ESTADO RECOMENDADO (A/B/C/D/E)
- **A** — CONTRADICTED BY PRIOR ART / abandonar el claim.
- **B** — KNOWN tal como está formulado; usar como referencia, no como hipótesis propia.
- **C** — PARTIALLY NOVEL: refinar el alcance a un sub-claim específico y documentarlo.
- **D** — suficientemente concreto para formalizar una hipótesis medible.
- **E** — pasar a diseño de experimento (FASE G/K) con el claim ya acotado.

---

## ANEXO — Formato ordenado (requerido por FASE R-3)
- **IDEA:** I-10 — Async Auxiliary Renderer.
- **NOVELTY STATUS:** KNOWN VARIANT (async-compute KNOWN; "renderer auxiliar completo async" es
  variante ya practicada en AO/SSR/shadows del mundo real: Cyberpunk, Rockstar, Frostbite).
- **KEY PRIOR ART (w/URLs):** en `PRIOR-ART.md`; highlights: AMD Polaris whitepaper (ACE/HWS),
  GDC17 "Async Compute", Vulkan-Samples async_compute, Cyberpunk 2077 GDC23, Frostbite FrameGraph
  GDC17, Division 2 GDC19, Rockstar async SSR, RADV docs.
- **OPEN SOURCE IMPLS:** Vulkan-Samples async_compute; RADV (Vulkan 1.4, soporte GFX8); DOOM
  Vulkan async ~7% (GDC16/GPUOpen); tuteo Khronos "Async compute". 
- **ACADEMIC:** (menos core académico, es ingeniería): Otterness & Anderson RTSS 2021 (scheduling ACE);
  GDC white papers arriba. 
- **COMMERCIAL:** Polaris whitepaper (ACE, CuReservation, Quick Response), Frostbite/DICE, CDPR
  Cyberpunk, Ubisoft Division 2, idTech6, Rockstar (async SSR), consoles.
- **POLARIS RELEVANCE:** ACE + 2 colas presentes; pero chip = 8 CUs + fetch-bound → overlap probable
  bajo; la oportunidad real es rellenar huecos **de memoria**, no de shader.
- **FEASIBILITY VERDICT:** FEASIBLE (API) / LOW-MEDIUM (ganancia esperada en Polaris12); medible.
- **TECHNICAL PLAUSIBILITY:** HIGH técnica; LOW-MEDIUM en la cuantificación local.
- **IMPLEMENTATION COST:** MEDIUM (como variante de BERRETA).
- **RISK:** Alto (diagnóstico engañoso; power cap; colisión BERRETA).
- **DEPENDENCIES:** BERRETA/ASY-01, runner K, Vulkan, harness.
- **RECOMMENDED STATUS:** **C**.