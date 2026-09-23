# IDEA I-10 — ASYNC AUXILIARY RENDERER: POLARIS12 FEASIBILITY
# ANÁLISIS DE VIABILIDAD EN POLARIS12 (RX 550 / GCN4)

Target: RX 550, Polaris 12 / Lexa.
**Confirmed specs (primary/aggregate: AMD RX 550 page, TechPowerUp, AIDA/aggregates):**
- 8 CUs × 64 shaders = **512 stream processors**; 32 TMUs; **16 ROPs**; L2 **512 KB**; L1 V$ 16 KB/CU
- **2 ACE** en arquitectura GCN4 low-end (Polaris10 tenía 4; los modelos pequeños implementan ~2 ACE +
  1 HWS — **sin ficha oficial pública de Lexa**: asumimos 2 ACE como rangos inferiores Google, se
  declara como supuesto, no dato oficial)
- 128-bit GDDR5 @ 112 GB/s; boost ~1183 MHz
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
- Vulkan 1.4 (RADV) en GFX8: cola compute + GFX en el mismo device; fork-join con semáforos binarios
  o timeline. El patrón async hardware está **disponible** (al contrario de I-06, aquí la API sí
  existe).
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
3. **La única variante con sentido de "renderer auxiliar":** pasos async *sin dependencia del frame
   actual y sin BW adicional* (luces estáticas anticipadas, pre-passes de post que trabajan en
   huecos de *latencia*), ejecutados en cola ACE de frames anteriores y **fork-join** al final.
4. **Contradicción vs I-04:** NO es compute-renderer sustituyendo a la GFX (eso ya es
   CONTRADICTED). Es **co-programación**.

**Verdict:** TÉCNICamente plausible y API-soportado, **pero la ganancia cuantificable dependerá de
medir el hueco real de ocupación** — exactamente el trabajo que ASY-01/BERRETA ya diseñó. Como
concepto, **KNOWN VARIANT**; como medición local, gap documental. → **RECOMMENDED STATUS: C**.