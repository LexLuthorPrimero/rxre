# BERRETA — Documento de Diseño del Proyecto

> **Archivo:** `04-IMPLEMENTACION/projects/BERRETA/BERRETA-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.14)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑO/IDEA]. **PROVISIONAL** — no es tecnología consolidada.
> **Estado global:** **IDEA/DISEÑO**. No se ejecutó ni se escribió ningún código.

---

## 1. OBJETIVO
Estudiar si **programar trabajo computacional en colas async (ACE/compute) mientras la cola gráfica
pasa bytes** aumenta la utilización de SIMDs en Polaris12 sin empeorar la presentación. BERRETA
= una investigación de **overlap de colas**, no de performance absoluta.

## 2. HIPÓTESIS (todas sin validar)
- H-B1: existe **capacidad ociosa** de SIMD durante los stalls de memoria que detectamos en ES-01/F2
  (auto-pacing) y puede rellenarse con compute.
- H-B2: el overlap (graphics+compute, ASY-01) **no degrada la framerate** del flujo gráfico (a igual
  presupuesto de SIMD).
- H-B3 (débil): el trabajo compute compartido reduce la latencia percibida de tareas post-proceso.

## 3. RELACIÓN CON LA EVIDENCIA
- **Evidencia a favor de relevancia (direccional):** ES-01/F2: la GPU está **no-saturada en compute**
  durante fetch-stall (busy 100% pero fetch-bound; SIMDs ociosas) → existe fuel posible para H-B1.
  ASY-01 ya propuesto en POLARIS12-MAP (§Categoría 4).
- **Evidencia en contra / desconocida:** el sistema es power-limited (E3/E5): añadir trabajo puede
  simplemente **aumentar SCLK/power**, no el rendimiento. Y es M2 gate (FASE J) para no afirmar
  beneficio sin experimento.

## 4. MECANISMO TARGET (diseñado)
- **Vulkan**: crear un pipeline con `VK_QUEUE_GRAPHICS_BIT` + `VK_QUEUE_COMPUTE_BIT` (si la familia de
  cola computacional existe en RADV para GFX8) y timeline semaphores; el compute shader hace trabajo
  **memory-bound** (para rellenar el hueco de fetch), no ALU (que ya sabemos no es límite).
- **Métrico clave:** frametime de la cola gráfica; throughput de la cola compute; `shader_busy`
  (ocupación total) y power.

## 5. QUEUE MODEL / SCHEDULING / SINCRONIZACIÓN
- Diseño: el compute ejecuta intercalado con renders (¡NUNTA por mandato de fase!) — diseño de colas
  separadas, semáforos binarios por frame, sin dependencia de puntero de presentación.
- Riesgo de sincronización: fence de presentación tocando ambos streams; usar timeline semaphores para
  evitar deadlock.

## 6. POSIBLES BENEFICIOS (si se validan)
- Mayor ocupación de SIMD durante stalls → mejor frametime p99 (menos picos).
- Aprovechamiento de la "capacidad ociosa" documentada en fetch-bound sin aumentar la potencia de forma
  proporcional (pendiente de medir).

## 7. RIESGOS / CONFOUNDERS
- **Confounder #1:** el trabajo extra puede simplemente subir el SCLK/power (power-limited) → el beneficio
  neto se anula.
- **Confounder #2:** la cola compute del RADV en GFX8 puede no existir/estar detrás de la gráfica
  (colas VK computacionales usan la misma familia que el gráfico); verificar capacidad en Capability
  Matrix (K9) antes de diseñar.
- **Riesgo HW:** ninguno (read-only si solo observa); riesgo de diseño: afirmar overlap sin contadores.

## 8. MÉTRICAS / WORKLOADS
- Workload: sintético GEOMETRY+FETCH con cola compute de relleno (modo ASY de R-2.9), repetido N≥5
  pareadas; telemetría del Lab K; potencia/celda.
- Comparación con E-03 como **baseline NOT DIRECTLY COMPARABLE** cuando defina el texto.

## 9. EXPERIMENTOS FUTUROS (secuencia propuesta)
1. Verificar existencia de queue family compute (read-only, capability).
2. Microbenchmark de overlap: frametime graphics vs compute added → probar H-B2.
3. Barrido de "cuánto compute cabe sin empeorar frametime" (0/25/50/75/100% SIMD).
4. Medir el efecto en power/SCLK → discriminar H-B1 vs poder.

## 10. CRITERIO DE ÉXITO / ABANDONO
- **Éxito:** frametime p99 mejora ≥ IC95% sin bajar la mediación gráfica (p50 no peor) Y power no
  aumenta ≥ notch margin → H-B1+H-B2 sustentadas.
- **Abandono:** el compute degrada la cola gráfica a cualquier nivel, o la familia de cola no existe, o
  el sistema es ya power/térmico limitado de forma que todo trabajo extra degrada.

## 11. CONCLUSIÓN DEL DISEÑO
BERRETA es **IDEA/DISEÑO, PROVISIONAL** y **dependiente** de: verificación de queue family (read-only),
FASE K (runner), y del resultado del trabajo de memoria (G-M1/G-M5) para saber si el "hueco" existe de
verdad y si es de SIMD o de memoria. **No se ha ejecutado nada ni se ha afirmado ningún beneficio.**
