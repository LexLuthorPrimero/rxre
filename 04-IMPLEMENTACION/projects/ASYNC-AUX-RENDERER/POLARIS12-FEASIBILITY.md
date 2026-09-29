# IDEA I-10 — ASYNC AUXILIARY RENDERER: POLARIS12 FEASIBILITY
# ANÁLISIS DE VIABILIDAD EN POLARIS12 (RX 550 / GCN4)

Target: RX 550, Polaris 12 / Lexa.

> **RECONCILIACIÓN 2026-09-24:** una `VK_QUEUE_COMPUTE_BIT` describe una cola lógica;
> no prueba reserva física de CUs, número de ACEs ni overlap real. Esos puntos requieren
> capability audit y medición local. La conclusión de viabilidad es `UNKNOWN`, no un beneficio
> confirmado.
**Confirmed specs (primary/aggregate: AMD RX 550 page, TechPowerUp, AIDA/aggregates):**
- 8 CUs × 64 shaders = **512 stream processors**; 32 TMUs; **16 ROPs**; L2 **512 KB**; L1 V$ 16 KB/CU
- El número de ACEs de Polaris12 es **UNKNOWN**; la familia GCN4 documenta ACEs/HWS, pero no
  hay una fuente local que cierre el recuento de esta unidad.
- 128-bit GDDR5; bandwidth nominal/estimado 96–112 GB/s según módulo/VBIOS; real `UNKNOWN`.
  Boost ~1183 MHz.
- Vulkan 1.4 via RADV (GFX8); soporte de cola compute/async + timeline semáforos
- Sources: https://www.amd.com/en/products/graphics/radeon-rx-550 ; https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2947 ; https://docs.mesa3d.org/drivers/radv.html

---

## 1. EL PARADIGMA DE POLARIS12: 8 CUs COMPARTIDOS + FETCH-BOUND

- Todos los motores (GFX queue, ACE compute queue, DMA) despachan a **la misma shader array de 8 CUs**.
  ACE/HWS solo *reordenan y solapan trabajo pendiente*; **no añaden CUs** (Polaris whitepaper §ACE/HWS).
- **ES-01 verify (in-repo):** el sintético es **fetch-bound**: frametime ∝ fetch, p50 flat, power
  cap auto-paced. El hueco real NO es CUs ociosas (como DOOM en GPU grandes) sino **latencia de
  memoria**. Un "renderer auxiliar" async que compita por **la misma memoria/L2 compartida (512 KB)**
  (Division 2 GDC19: "async stalling the gfx pipe") puede *empeorar* el p99 del flujo GFX.
- **Chip de 8 CUs + renderer auxiliar:** la CU array está *saturada por diseño* para el flujo GFX en
  pantalla; el auxiliar async solo "cabe" en el hueco de **latencia/espera de fetch**, no como pass
  compute masivo.

## 2. SOPORTE MECÁNICO (lo que NO es bloqueante)
- Vulkan/RADV describe colas compute y GFX en el mismo device a nivel API; la existencia de
  una cola no confirma scheduling overlap, número de ACEs ni comportamiento efectivo en esta
  placa. El patrón fork-join queda `REQUIRES CAPABILITY AUDIT`.
- Coste de sync: crear 2 colas + semáforos en cada frame tiene coste real en un chip pequeño
  (menos trabajo absoluto → el overhead de fences pesa más). Division2/Frostbite ya miden el costo
  del "sync at end". En un IMR de 8 CUs esto es **proporcionalmente caro**.

## 3. A DÓNDE VA LA GANANCIA (cuello real = memoria, no shader)

| Trabajo auxiliar candidato | Tipo de cuello que ataca | Encaja en Polaris12 fetch-bound? |
|---|---|---|
| SSAO/Hi-Z (lee depth previo) | CUs ociosas durante shadowmaps | Solo si el GFX está *raster-bound*; aquí el sintético es fetch-bound → bajo |
| SSR async (R*, Cyberpunk) | BW/compute en hueco | Necesita depth/color viejos; consume **BW** (la misma memoria que el fetch) → riesgo |
| Sombras de luces estáticas | CUs ociosas, sin dep. del frame | Puede anticiparse **en CPU/cola async en frames anteriores** (fork antes de join) → el caso más prometedor |
| Pre-pass de post (bloom/bokeh) | CUs/ALU | Si el GFX fetch-stallea, estos pasos independientes pueden usar huecos de **latencia**, no de BW extra |
| Simulación/IA visual | trabajo computacional extra | No reduce frametime del flujo gráfico; contamina el diagnóstico ES-01 |

Ley de la casa (in-repo): **power cap aplastará el overlap** (E3/E5: la GPU ya auto-pacing;
añadir trabajo async solo redistribuye el mismo power/tile budget). El resultado esperado NO es
"frametime menor" sino "misma frametime con más trabajo útil" (o p99 peor por BW compartida).

## 4. CONCLUSIÓN DE FACTIBILIDAD
1. **Feasible (API)** — RADV/Vulkan soporta la cola async en Polaris12; el patrón está probado en
   la industria (DOOM, Cyberpunk, R*, Frostbite).
2. **Beneficio esperado en Polaris12: BAJO-MEDIO** — por (a) 8 CUs compartidos saturados por el
   flujo GFX, (b) cuello real del sintético = memoria compartida → un auxiliar *compute+BW* compite,
   no solapa, (c) power cap (E3/E5) que distribuye el mismo budget.
3. **La única variante con sentido de "renderer auxiliar":** es una hipótesis de diseño:
   trabajo sin dependencia del frame actual y sin BW adicional, en una cola compute de
   frames anteriores con fork-join. La cola y su beneficio deben auditarse; no se presupone
   una cola ACE física ni reserva de CUs.
4. **Contradicción vs I-04:** NO es compute-renderer sustituyendo a la GFX (eso ya es
   CONTRADICTED). Es **co-programación**.

**Verdict:** la API sugiere un camino de diseño, pero la capacidad real y la ganancia
cuantificable son `UNKNOWN` hasta capability audit/medición. Como concepto, **KNOWN
VARIANT**; como medición local, gap documental. → **RECOMMENDED STATUS: C**.
