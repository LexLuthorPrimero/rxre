# FASE-R1-FINAL-REPORT.md — Informe Final de FASE R-1

> **FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION — 2026-09-22**
> Modo: SOLO DOCUMENTAL (read-only). Ninguna escritura de sistema durante toda la fase.
> Directorio: `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/`

---

## A. Resumen ejecutivo

FASE R-1 cerró la deuda documental acumulada entre FASE A y FASE R-0: se reconciliaron las discrepancias de
conteos de event IDs GFX8 (CB/SQ/MC), se actualizó la auditoría de IDs (Resultado B) con la adenda post-R-0, se
corrigieron los errores objetivos del informe de Etapa 2 (tabla radeontop y conteo SPI), se reconoció y preservó
el historial de MASTER-RESEARCH-STATUS v2.5 con adendas (no borrado), se construyó el mapa documental, el modelo
de estados de evidencia, los gaps críticos, la auditoría de la Capa Transversal, la readiness de E–J y el marco
de acciones no autorizadas. Se integró FASE R-1 en MASTER-PLAN (sección R) sin tocar las fases ni el sistema.

## B. Tareas realizadas (tabla resumen)

| ID | Entregable | Archivo | Estado |
|---|---|---|---|
| R-1.1 | Reconciliación Event IDs GFX8 CB/SQ/MC | `R1-1-GFX8-EVENT-RECONCILIATION.md` | COMPLETADA |
| R-1.2 | Resultado B — Revisión post FASE R-0 (adenda) | `FASE-D-GFX8-EVENT-ID-AUDIT.md` §14 | COMPLETADA |
| R-1.3 | Correcciones al informe Etapa 2 | `FASE-D-ETAPA-2-RESULTADOS.md` §12 | COMPLETADA |
| R-1.4 | MASTER-RESEARCH-STATUS reconciliado | `MASTER-RESEARCH-STATUS.md` v2.5 | COMPLETADA |
| R-1.5 | Mapa documental A–R-1 | `R1-5-DOCUMENTATION-STATUS.md` | COMPLETADA |
| R-1.6 | Modelo de estados de evidencia | `R1-6-EVIDENCE-STATE-MODEL.md` | COMPLETADA |
| R-1.7 | Gaps críticos | `R1-7-CRITICAL-GAPS.md` | COMPLETADA |
| R-1.8 | Capa transversal (auditoría read-only) | `R1-8-CROSS-CUTTING-AUDIT.md` | COMPLETADA |
| R-1.9 | Readiness E–J | `R1-9-E-J-READINESS.md` | COMPLETADA |
| R-1.10 | Acciones no autorizadas | `R1-10-NON-AUTHORIZED-ACTIONS.md` | COMPLETADA |
| R-1.13 | MASTER-PLAN + sección R | `MASTER-PLAN.md` §R | COMPLETADA |
| R-1.15 | Informe final (este) | `FASE-R1-FINAL-REPORT.md` | COMPLETADA |

## C. Reconciliaciones logradas

**R-1.1 — Event IDs GFX8 (CB/SQ/MC):**

| Bloque | GPUPerfAPI v3.11.1 | Mesa groups_VI | Estado |
|---|---|---|---|
| CB | 396 (índice 0..395) | 405 selectors (máx. clase VI) | PARTIALLY_RECONCILED |
| SQ | 299 (0..298) | 273 selectors (máx. clase VI) | PARTIALLY_RECONCILED |
| MC | 33 (0..32) | 22 selectors | PARTIALLY_RECONCILED (conteo); semántica MC UNRESOLVED |

Evidencia de alineación: 20/22 bloques con **coincidencia exacta** entre ambas fuentes primarias (GRBM 34, DB 257,
SPI 197, VGT 147, TCC 192, PA_SC 397, SX 34, etc.). PA_SU 153 vs 154 (diferencia menor descrita en R1-1 §4.4).
Regla operativa: usar la intersección de rangos (CB 0..395, SQ 0..272, MC 0..21) para diseño seguro futuro.

**R-1.4 — MASTER-RESEARCH-STATUS:** Conclusión B antigua (fuente local) preservada como historial + adenda de
cross-ref a FASE R-0/R-1; nota «GRBM BLOQUEADO» en sección K/Q y FASE M corregida a «VERIFICADO documental, escritura
NO autorizada». Versión → 2.5.

**R-1.3 — Etapa 2:** tabla radeontop reconstruida con método declarado (filtrada gpu≥95); conteo SPI_CSQ
corregido 3306→8408; conclusiones centrales intactas (potencia A 22.25 vs B 15.78 W, ratio 1.41).

## D. Contradicciones restantes (declaradas, no encubiertas)

- **Semántica/unidad de eventos del bloque MC [UNRESOLVED]**: sin catálogo AMD con nombres/unidad → no diseñar
  normalización de banda de memoria. (No es contradicción; gap declarado.)
- Coincidencia exacta de los selectores extra (los +9 de CB, +26 de SQ, +11 de MC y +1 de PA_SU) no verificada
  1:1 (sin catálogo nombrado para esas entradas) → estado PARTIALLY_RECONCILED, límite inferior usado.
- Los valores GFX12/GFX11 contrarios a GFX8 (p. ej. SQ WAVES moderno) son como aviso de no-portabilidad cruzada,
  no contradicción dentro de GFX8.

## E. Gaps críticos registrados (prioridad)

1. GAP-01 — control SCLK bajo cap (ALTA)
2. GAP-04 — `mem_busy` no representa activity real (ALTA)
3. GAP-07 — PCIe x8 vs x4 sin verificar (ALTA)
4. GAP-08 — variante/CUs/fuses/BIOS lock sin confirmar (ALTA)
5. GAP-09 — semántica de eventos MC (ALTA, documental)
6. MEDIA/BAJA: GAP-02/03/05/06/10/11. Detalle en `R1-7-CRITICAL-GAPS.md`.

## F. Readiness de fases futuras

- **E–J (PENDIENTES):** diseñables documentalmente ya; ejecución bloqueada hasta (1) autorización explícita,
  (2) Laboratorio K/framework de telemetría, (3) resolución de gaps ALTA.
- **M:** propósito casi resuelto por R-0/R-1 (mapa recuperado); queda opcional/consolidación.
- **K/L/N–Q:** siguen PLANIFICADAS, sin cambios de autorización.

## G. Acciones NO autorizadas (mantenidas)

1. Programar contadores / MMIO counters.
2. Escribir sysfs (`power1_cap`, `pp_dpm_*`, `ppfeaturemask`, `pp_od_clk_voltage`).
3. Instalar/ejecutar benchmarks sin autorización.
4. Modificar congelados (WORKLOAD-SINTETICO, BIOS/VBIOS/SPPT/pp_table, Kalm, Mesa sistema, GRUB/kernel/DRM).
5. Implementar BERRETA/Ghost Cache/etc.
Marco completo en `R1-10-NON-AUTHORIZED-ACTIONS.md`.

## H. Trazabilidad (fuentes primarias usadas)

- GPUPerfAPI v3.11.1: `gpa_hw_counter_gfx8.cc`, `gpa_hw_exposed_counters_gfx8.cc`,
  `public_counter_names_vk_gfx8*.txt` (parsing de arrays, conteo y unicidad confirmados).
- Mesa local backup: `ac_perfcounter.c` (groups_CIK/VI/gfx9), `ac_perfcounter.h` (`selectors` campo).
- Referencia expuesta: `R0-1-GFX8-EVENT-ID-REFERENCE.txt` (2304 contadores).
- Documentos FASE D (RESULTADOS/EVENTS/AUDIT-ID/AUDIT-ETAPA2) y MASTER-PLAN / MASTER-RESEARCH-STATUS.

## I. Confirmación de READ-ONLY

Durante FASE R-1 **no se escribió ningún sysfs, MMIO, contador, PowerPlay, BIOS/VBIOS, ni se instaló o ejecutó
nada**. Todos los cambios se limitaron a archivos de documentación del repositorio.

## J. Archivos de la entrega (rutas)

```
experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/
 ├─ R1-1-GFX8-EVENT-RECONCILIATION.md
 ├─ R1-5-DOCUMENTATION-STATUS.md
 ├─ R1-6-EVIDENCE-STATE-MODEL.md
 ├─ R1-7-CRITICAL-GAPS.md
 ├─ R1-8-CROSS-CUTTING-AUDIT.md
 ├─ R1-9-E-J-READINESS.md
 ├─ R1-10-NON-AUTHORIZED-ACTIONS.md
 └─ FASE-R1-FINAL-REPORT.md
Modificados: FASE-D-GFX8-EVENT-ID-AUDIT.md (§14), FASE-D-ETAPA-2-RESULTADOS.md (§12),
MASTER-RESEARCH-STATUS.md (v2.5), MASTER-PLAN.md (sección R + FASE M + contradictions).
```

## K. Checklist de entrega (§14 del encargo R-1)

| Requisito | Cumplido |
|---|---|
| 1. Fase R-1 como su propia sección en MASTER-PLAN (R-1.13) | ✅ sección R |
| 2. MASTER-RESEARCH-STATUS v2.5 con changelog | ✅ adenda + versión |
| 3. Reconciliación R-1.1 (CB/SQ/MC) completa | ✅ PARTIALLY_RECONCILED declarado |
| 4. Auditoría IDs GFX8 con adenda post-R-0 | ✅ §14 |
| 5. Corrección informe Etapa 2 | ✅ §12 |
| 6. Mapa documental | ✅ R1-5 |
| 7. Modelo de estados | ✅ R1-6 |
| 8. Gaps | ✅ R1-7 |
| 9. Capa transversal | ✅ R1-8 |
| 10. Readiness E–J | ✅ R1-9 |
| 11. Acciones NO autorizadas | ✅ R1-10 |
| 12. Read-only confirmado | ✅ sección I |
| 13. Sin inventar datos / trazabilidad | ✅ sección H |

**FASE R-1 COMPLETADA.**