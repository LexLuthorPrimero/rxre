# FASE G — MEMORY / VRAM / GTT — Documento de Diseño

> **Archivo:** `FASE-G-MEMORY-VRAM-GTT-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.5)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO] — modelo conceptual + experimentos diseñados; nada ejecutado.
> **Línea relacionada:** proyecto `GHOST` (`projects/GHOST/GHOST-CACHE-DESIGN.md`) se deriva de esta fase
> como investigación de prefetch/localidad; "Ghost/Ghost Cache" NO es tecnología validada (ver R-2.15).

---

## 1. Objetivo

Diseñar la investigación del **camino de memoria** entre la GPU y los sistemas de almacenamiento
(VRAM/GTT — host memory y PCIe) para distinguir qué componente limita en los workloads de Polaris12.

## 2. Modelo conceptual: flujo de una request de memoria

```
 [WORKLOAD]──> request de memoria (load/store/vertex/texture/buffer)
        │
        ▼
 [GPU CACHES] (L0/L1 per-CU → L2 shared → vGPRs/TCI)   ← hit = sin tráfico externo
        │ miss
        ▼
 [VRAM (GDDR5 128-bit)] local a la GPU   ← MEMORY LOCAL, alta BW, 4 GB (2 GB efectivos)
        │ si status ≠ DEVICE_LOCAL o si eviction
        ▼
 [GTT (tak a host RAM via PCIe)]   ← "stolen"/mapped; latencia y BW limitadas por PCIe
        │ miss GTT
        ▼
 [SYSTEM RAM (host)] ← reservar/migrar vía TTM/amdgpu (page tables, io-mmu)
        │
        ▼
 [LATENCY / BANDWIDTH] → [GPU STALL] (espera por datos) → ocio de SIMDs
```

Componentes y su nivel de certeza:

| Componente | Qué se sabe (nivel) | Fuente |
|---|---|---|
| VRAM física 2 GB (501 GB/s teórico GDDR5 128-bit) | [VERIFICADO] spec | R0-4 / BUILD_SPEC |
| GTT = asignación de host RAM por TTM/amdgpu, accesible por la GPU vía PCIe | [VERIFICADO conceptual] Open-code amdgpu TTM manual | kernel docs / local dev knowledge |
| `mem_busy` (sysfs) ≈ actividad SMU de memoria, NO es % de ancho de banda | [VERIFICADO] METRICS-DEFINITIONS y FASE D | radeontop/sysfs doc |
| MCLK sube a 1500 solo con presión real (superposition)  | [OBSERVADO/REPRODUCIBLE] MCLK policy smu7 (R0-2) | R0-2, R-15 |
| fetching granulosgado (ES-01/F2) → frametime ∝ fetches, power cte | [OBSERVADO/REPRODUCIBLE] | ES-01, F2 |
| `mem_busy` NO escala con power (B>A, A más potente) | [OBSERVADO] FASE D etapa 2 | FASE D |
| VBO/IBO streaming desde host (GTT) → BW PCIe/DRAM | [HIPÓTESIS] diseño candidato GEO-03 | este diseño |

Todo lo que no esté arriba se marca explícitamente como **[HIPÓTESIS]** en los experimentos.

## 3. Distinción rigurosa de estados

- **DOCUMENTED:** lo descrito por fuentes primarias (kernel amdgpu, Mesa, whitepaper) pero no re-medido.
- **OBSERVED:** medido en este sistema (read-only).
- **INFERRED:** deducido de mediciones sin contar con el mecanismo interno hardware (ej. "auto-pacing").
- **HYPOTHESIS:** propuesta de mecanismo a probar.
Nunca se promueve un INFERRED a OBSERVED por una única métrica; ver modelo de estados R1-6.

## 4. Preguntas de investigación (FASE G)

- G-1 ¿Qué fracción de las request de los workloads sintéticos caen en caché (L2) vs VRAM vs GTT?
- G-2 ¿Cuánta latencia/bandwidth agrega pasar por GTT vs VRAM en acceso GPU?
- G-3 ¿Condiciona el modelo de asignación (DEVICE_LOCAL vs HOST_VISIBLE) la elección del camino?
- G-4 ¿Bajo qué condiciones `mem_busy` realmente refleja BW (cómo se satura 128-bit)?
- G-5 ¿El fetch-latency (auto-pacing) se debe a MISS en L2 o a acceso GTT?

## 5. Experimentos diseñados (todos read-only o con escrito reversible autorizado)

### G-M1: Mapa de camino de los buffers actuales del workload sintético
- **Medir** (read-only): `mem_info_vram_used`, `mem_info_gtt_used`, y la diferencia de rendimiento con
  `RADV_...` que fuerce alojamiento (variables de control documentadas; NO modificar Mesa).
- **Resultado esperado (hipótesis):** los buffers de los sintéticos residen en GTT/heap host-visible →
  cada fetch cruza PCIe → cualquier "fetch-latency" observada es, al menos en parte, **camino GTT**.
- **Confounder:** el driver puede migrar dinámicamente; hay que fijar el alojamiento (via flags de
  creación, no sysfs) y verificar con `mem_info_*` que el mapa se mantiene.

### G-M2: Contraste DEVICE_LOCAL vs HOST_VISIBLE
- Reuse de MEM-02: misma carga, misma cantidad, tres alojamientos
  (DEVICE_LOCAL / HOST_VISIBLE|HOST_COHERENT / HOST_CACHED);
  medir FPS, frametime, `mem_busy`. **Pregunta G-3.**
- **Criterio de resultado:** si DEVICE_LOCAL > HOST_VISIBLE > HOST_CACHED → el camino GTT añade coste.

### G-M3: Pressure VRAM y eviction (MEM-01)
- Working set VRAM 50/75/100/125/150% de 2 GB → medir corte de FPS y page faults en `dmesg`.
- **RIESGO:** OOM/device lost → requiere autorización y ventana con reinicio posible; marcar cómo de
  complejo en Matriz J.

### G-M4: Relación `mem_busy` ↔ BW real (G-4)
- Cross-check `mem_busy` (SMU) con un patrón memorístico conocido (solo sintético read-heavy) y comparar
  vs teórico 128-bit/501 GB/s. **Sin contadores HW**, al menos equipara la escala, no la exactitud.

### G-M5: ¿fetch-latency = camino GTT? (G-5)
- Diseñado para interaccionar con ES-01/F2: variar el **alojamiento** de la textura (GTT vs VRAM) a igual
  patrón de fetch (fetch8 de F2) y observar si el ratio frametime/fetch cambia.
- Si el ratio es invariante → el cuello es la **latencia de memoria misma** (no el camino externo).

## 6. Interacción con GHOST y con el resto del ecosistema

- **GHOST** (proyecto separado, NO validado) estudiará prefetch/localidad de acceso para reducir
  "fetch-latency". GHOST queda **dependiente** de G-M1/G-M5: sin el mapa de caminos no se puede diseñar
  un mecanismo de prefetch (evidencia → hipótesis → validación).
- **RX-COMPRESSION-ENGINE** (proyecto separado, provisional) usa este modelo para saber DÓNDE ahorrar
  BW (VRAM vs GTT/PCIe) → depende de G-M2/G-M4.
- Con **FASE M** (contadores) se podrá verificar con eventos reales (TCC/TCP para L2/tex, MC para DRAM).
- Con **FASE D etapa 3** (diseñada) el byte-quota por path podría medirse directamente (no autorizado hoy).

## 7. Cierre
FASE G queda **DISEÑADA** (modelo + 5 experimentos, G-M1..G-M5), **PENDIENTE**. Ningún experimento de
esta fase se ejecutó ni se afirma ninguna relación no documentada. El peor caso para la interpretación es
medir CPUs-idle (auto-pacing) sin conocer el camino → los G-M1/G-M5 son los primeros ejecutables de la fase.