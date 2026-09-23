# R1-7 — GAPS CRÍTICOS (brechas de conocimiento bloqueantes + prioridad de resolución)

> **Tarea R-1.7** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Mapa de brechas que impiden/retrasan experimentos futuros. Plantilla por gap: definición, porqué es crítico,
> impacto, dónde se registraría, qué falta, prioridad, y estado.

---

## Plantilla de gap (modelo estándar)

```
Identificador: GAP-XX
Título:
Definición: <qué no sabemos>
Por qué es crítico: <qué bloquea si no se resuelve>
Impacto: <fases afectadas (E..Q), riesgos>
Dónde se registraría: <documento/directorio destino>
Qué falta para resolverlo: <fuente/experimento/medición>
Fuentes consultadas ya:
Estado: [NO RESUELTO] / [PARCIAL] / [RESUELTO]
Prioridad: ALTA/MEDIA/BAJA
```

---

## Lista de gaps (extraída de MASTER-PLAN y deudas pendientes)

- **GAP-01 — Régimen 25 W / SCLK no ligado a cap [NO RESUELTO] — ALTA.** No se sabe qué controla SCLK en cap.
  Impacto: FASE I (PowerPlay), FASE L. Fuentes: EP06 (resultado), smu7 drivers. Falta: investigación DPM/SCLK
  con telemetría controlada.
- **GAP-02 — MCLK sostenido bajo carga no elevada (Polaris12) [NO RESUELTO] — MEDIA.** MCLK 1500 en steady de
  260 s; política de lifear a 1500 no entendida. Afecta FASE G (memoria) e I. Fuente: smu7 hwmgr (15/20 gates).
  Falta: medir actividad de memoria real vs MCLK.
- **GAP-03 — Draw call máximo / límites de acceso L2 [NO RESUELTO] — MEDIA.** Para FASE E/G. Falta benchmark
  controlado.
- **GAP-04 — Memoria: `mem_busy` no captura activity real (VSYNC / present stalls) [PARCIAL] — ALTA.**
  Afecta FASE G. Falta comprender la métrica sysfs bajo carga vs contadores reales de MC (con semántica aún
  UNRESOLVED, R1-1).
- **GAP-05 — DCC compression state y sus implicaciones [NO RESUELTO] — BAJA/MEDIA.** Afecta FASE H (RADV). Falta
  verificación en superficie real.
- **GAP-06 — «phong 1285 fps» del exploratorio no verificado/atribuible [NO RESUELTO] — MEDIA.**
  Requiere atribución correcta (comment/repro mode de vkmark) antes de usar como comparativa.
- **GAP-07 — PCIe x8 vs x4 operativo DUDOSO (etapa F2, 8 fetches) [NO RESUELTO] — ALTA.** Modalidad real del
  enlace PCIe no confirmada; afecta a todos los benchmarks dependientes de VRAM/GTT. Falta: `lspci -vv` /
  `pcie_speed` verificado.
- **GAP-08 — Número real de CUs/fuses/BIOS lock (8 CUs de 10) sin confirmación de la variante [NO RESUELTO] —
  ALTA.** Afecta toda la caracterización. Falta verificación documental (Rx550-2017 = 8 CU completo).
- **GAP-09 — Semántica/unidad de eventos del bloque MC [NO RESUELTO] — ALTA (solo documental).** R1-1 la dejó
  UNRESOLVED: sin catálogo con nombres+unidad → no diseñar normalización MC. Falta una fuente AMD de nombres de
  PERF_SEL MC (GPUPerfAPI v3.11.1 no expone nombres MC).
- **GAP-10 — Impacto de DPM intermedio / perfiles (PowerPlay) [NO RESUELTO] — MEDIA.** FASE I.
- **GAP-11 — mortalidad de la atenuación por MSAA sample location bug en POLARIS12 [NO RESUELTO] — MEDIA.**
  R-0.3 confirma has_msaa_sample_loc_bug; falta medir el efecto real.

---

## Prioridad global (sugerida para FASE J)

| Prioridad | Gaps |
|---|---|
| ALTA | GAP-01, GAP-04, GAP-07, GAP-08, GAP-09 |
| MEDIA | GAP-02, GAP-03, GAP-06, GAP-10, GAP-11 |
| BAJA | GAP-05 |

---

## Confirmación read-only

Gap list construida por lectura documental; sin ejecutar experimentos ni escribir en el sistema.