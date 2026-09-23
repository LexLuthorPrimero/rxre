# R0-4 — Arquitectura Polaris12 / Lexa (RX 550) según fuentes externas

> **Archivo:** `R0-4-ARCHITECTURE-LEXA-POLARIS12.md`
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [VERIFICADO] (reviews técnicos y spec base confirmada por concurrencia de fuentes)

---

## 1. Identidad Silicon

- **Polaris12** = "Lexa" (codename interno AMD). ASIC GFX8/GCN 4.º gen.
- RX 550: **512 SP / 32 TMU / 16 ROP**, bus **128-bit**, memoria GDDR5, boost ~1183 MHz (SKU de
  referencia; filial puede variar).
- Transistores ~2.2B, die ~101 mm², fabricación 14nm (GF/Samsung 14LPP).
- Variantes: RX 550 existe con 640 SP en algunos AIB; Lexa también se vendió como RX 560D / Radeon
  550 en OEM. La referencia del proyecto es `1002:699f`.

## 2. Configuración fija de la unidad (según tabla Polaris/Tom's hardware/blog técnico)

| Componente | Polaris12 (Lexa) valor | Nota vs P11 (Lexa) |
|---|---|---|
| CUs activas | 10 (640 SP en chip completo; RX550 usa 8 CUs = 512 SP) | P11 = 14-16 CUs |
| Shader Engines | 2 SE × 1 CU/SPI… | 2 SE → **2 triángulos/clk de rasterización** |
| ROPs | 16 | igual a P11 |
| L2 | 512 KiB (reportado; distinto de P11? validar con SI_* ) | — |
| TMUs | 32 | — |
| Memoria | GDDR5 7 Gbps 128-bit → ~112 GB/s teórico | — |
| TDP | ~50 W (sin conector aux) | P11 ~50 W |

**Conclusión arquitectónica externa (coincide con R-01 local):** Polaris12 es un chip de
**bajo presupuesto con 2 SE** (a diferencia de mucho más común "1 SE" asumido antes localmente;
ver R-01 para discrepancia de 4 instancias vs registradas). Radio back-end de 16 ROPs hace que
fill-rate y ROP sean más balanceados y NO el cuello (coherente con FASE D etapa 2: sx ≈ 1.51–1.60
ratio entre A/B).

## 3. Implicaciones para observaciones del proyecto

- **2 SE** ⇒ posibilidad de 2 primitivos/clk; los contadores GRBMSE (4 instancias registro) pueden
  registrar actividad distribuida; la L2 compartida 512 KiB es la que condiciona el límite de
  w/s de 256 KiB (R-05).
- **16 ROPs + 128-bit**: el render back-end convencional (CB) es relativamente estrecho; DCC
  relevante (ver R0-1/R0-6); los números de exit/ROP de Superposition se alinean con la teoría
  de que la geometría/vertex/export (vgt/pa/sh) mueve la diferencia de potencia y no los ROPs.
- El dibujo "3 vértices bufferless" (R-08) en 2 SE funciona porque el rasterizer distribuye
  primitivos; nada de la arquitectura impide ese caso.

## 4. Referencias de potencia observadas externamente (para contraste)

- TDP nominal 50 W; mediciones gaming ~47 W peor caso en reviews (Tom's Hardware e Igor'sLab).
- En el proyecto la unidad funciona en régimen cap a 35 W con draw real actual ~13 W (época
  post-torneo); las mediciones externas se citan solo como referencia asintótica superior (no son
  comparables 1:1 por cap/VRAM/refrigeración).

## 5. Fuentes

1. Tom's Hardware — Radeon RX 550 2GB review (spec arquitectónica y mediciones de potencia):
   https://www.tomshardware.com/reviews/amd-radeon-rx-550-2gb,5034-... (review de 2017)
2. VideoCardz – Lexa PRO spec page: https://videocardz.net/amd-radeon-rx-550 (640/512 SP, 1183 MHz boost, 14nm, 2.2B tr, 101 mm²)
3. TechPowerUp GPU database — RX 550 entry (512 SP, 1183 MHz, 128-bit, GDDR5):
   https://www.techpowerup.com/gpu-specs/radeon-rx-550.c2905
4. Cross-ref local: `POLARIS12-MAP/` (R-01 en WORKLOAD-SINTETICO/RESEARCH.md) para la
   discrepancia de instancias de bloques.

## 6. Confianza y límites

- [VERIFICADO] datos de spec base (SP/TMU/ROP/bus/TDP) por concurrencia de al menos 3 fuentes web
  técnicas.
- Los detalles finos (L2 512 KiB, nº exacto de unidades de textura por CU, distribución de bloques
  por instancia) no quedan verificados por estas fuentes; marcar como [DESCONOCIDO] si se usan
  como supuesto de diseño experimental.