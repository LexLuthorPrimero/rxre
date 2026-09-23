# FASE R-4C — EXP-F1-A Jitter Observability (COMPLETADA)

**Estado (v2.10):** `EXP-F1-A = COMPLETADA — HARNESS EJECUTADO BAJO AUTORIZACIÓN (8/8 celdas PASS)`

## Qué es
Validación de que un harness Vulkan puede **generar** una secuencia de jitter TAA subpíxel conocida y que una
**capa Vulkan externa** (local, vía `VK_LAYER_PATH`) puede **observar/reconstruir** esos offsets con
`MAE < 0.01 px` (PROVISIONAL TARGET).

## Entregables
1. **`PRECHECK-REPORT.md`** — 11 ítemes (A–K) + checklist QA §19 (19/19). Conclusión: NIVEL A VERIFIED, NIVEL B DERIVED.
2. **`EXP-F1-A-JITTER-OBSERVABILITY.md`** — diseño completo (§1–§11): niveles A/B, secuencia, métricas, criterios, límites.
3. **`PRIOR-ART.md`** — fuentes primarias (FSR2/GPUOpen, Khronos LoaderLayerInterface, man page `vkCmdPushConstants`), análisis FP32, matriz de observabilidad.
4. **`EXP-F1-A-RESULTADOS.md`** — **informe final de resultados observados** (v2.10).
5. **`README.md`** — este archivo.

## Resultados observados (resumen)
- **NIVEL A** (push constants): `MAE = 0.0 px` (bit-idéntico), 320/320 frames, Pearson 1.0 — RADV real y lavapipe.
- **NIVEL B** (reconstrucción desde matriz en UBO host-visible): `MAE = 3.66×10⁻¹⁰ px`, máx `3×10⁻⁸ px`, 320/320, Pearson 1.0 — piso FP32 de la ruta matriz, muy por debajo de 0.01 px.
- 2 réplicas × 2 niveles × 2 drivers = **8 corridas, todas exitosas y deterministas**.
- ANV (opcional): sin devices físicos en este entorno → documentado como NO EJECUTADO.

## Uso
Leer primero `EXP-F1-A-RESULTADOS.md` (resultados observados), luego `PRECHECK-REPORT.md` (conclusión/checklist),
`EXP-F1-A-JITTER-OBSERVABILITY.md` (método), `PRIOR-ART.md` (evidencia). Reproducible con
`./harness/run_all.sh` (todo local; resultados en `results/`).

## Alcance de la ejecución autorizada
Cero modificaciones al sistema: capa cargada solo por `VK_LAYER_PATH`/`LD_LIBRARY_PATH` locales; drivers RADV
real + lavapipe; sin benchmarks de rendimiento; sin tocar registros/kernel/GPU; jitter ≠ motion vector
(conclusión NO formulada en ningún punto).