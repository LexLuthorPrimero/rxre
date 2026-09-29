# FASE-R0 — INFORME FINAL — EXTERNAL KNOWLEDGE RECOVERY / POLARIS12 KNOWLEDGE GAP AUDIT

> **Fecha:** 2026-09-22
> **Modo:** SOLO DOCUMENTAL / READ-ONLY. No se instaló ni eliminó software, no se escribió
> sysfs/MMIO, no se programaron contadores, no se modificó GPU/PowerPlay/Mesa/Kalm/rx550-torneo.
> Descargas de referencia a `/tmp/opencode/`; documentación creada en este directorio
> (`05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/`).
> **Estado:** FASE COMPLETADA.

---

## 1. Resumen ejecutivo

La FASE R-0 **acota** el GAP #1: GPUPerfAPI v3.17 aporta un catálogo GFX8
externo y v3.11.1 conserva la extracción histórica. La presencia de filas no
verifica el ASIC `1002:699f`, la semántica ni la seguridad de programación; por
tanto FASE M queda `PARTIALLY_RECONCILED`, no desbloqueada. PowerPlay/MCLK es
source-level, y los workarounds/arquitectura son referencias que no sustituyen una
auditoría runtime. Todo sin ejecutar experimentos ni tocar el sistema.

---

## 2. Matriz de Gaps / Preguntas R-0 → Resultado

| ID | Pregunta (gap) | Antes (local) | Ahora (externo) | Veredicto | Fuente principal | Confianza |
|---|---|---|---|---|---|---|
| **R-0.1** | Event IDs de performance counters GFX8/Polaris12 | **BLOQUEADO** (Resultado B: no verificables localmente) | **PARCIALMENTE RECONCILIADO** — catálogo GFX8 genérico; `v3.11.1` histórico, `v3.17` referencia; 2304 filas no son eventos validados | **BLOQUEO LOCAL NO RESUELTO; CATÁLOGO EXTERNO DOCUMENTADO** | GPUPerfAPI upstream | **MEDIA** |
| R-0.2 | Política DPM de MCLK en Polaris (smu7) | R-07 local (5/16/20); R-4A readout 3/16/20 | Código kernel documenta 128-bit → 5/16/20 upstream; efecto local, campos/perfil y relación con `mem_busy` no cerrados | **[VERIFICADO source-level; local UNKNOWN]** | kernel Linux smu7_hwmgr.c + commits + R-4A | ALTA para fuente; baja para trigger local |
| R-0.3 | Workarounds Mesa aplicables a Polaris12 | sospechas de flags | `has_msaa_sample_loc_bug` incluye POLARIS12; `LINE_FILTER_DISABLE(family<=POLARIS12)`; `clear_db_cache_before_clear` | **[VERIFICADO]** | listas mesa-dev / código radeonsi | ALTA |
| R-0.4 | Arquitectura Lexa/Polaris12 (SP/TMU/ROP/bus/SE) | parcial | 512 SP/32 TMU/16 ROP/128-bit/50 W TDP/14 nm/2.2B transistores/101 mm²; RX550 8 CUs | **[VERIFICADO]** | TH, videocardz, TechPowerUp | ALTA |
| R-0.5 | Benchmarks externos RX 550 (referencia) | parcial | Rangos de rendimiento y potencia (gaming ~47 W; boost ~1141–1164 MHz; power virus ~820 MHz) | **[VERIFICADO]** (referencia, no medición) | TH 2017, Igor'sLAB | ALTA |
| R-0.6 | Herramientas históricas con tablas GFX8 | — | GPUPerfAPI v3.17 referencia / v3.11.1 histórico; v4.0+ eliminó GCN; RGP actual no GFX8 confirmado; UMR solo registros | **[PARTIALLY RECONCILED]** | repos/README/release notes | MEDIA |
| R-0.7 | Gaps abiertos restantes (véase §4) | — | No ampliables sin experimentos (no autorizados) | **ABIERTO** | — | — |

---

## 3. Actualización del Resultado B (FASE D)

- **Resultado B original (FASE-D-GFX8-EVENT-ID-AUDIT.md):**
  «Los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles.»
- **Resultado B actualizado (reconciliación 2026-09-24):**
  «Los IDs de eventos GFX8 no están en fuentes locales. GPUPerfAPI v3.17 aporta un
  catálogo externo genérico y v3.11.1 conserva una extracción histórica; 2304 filas no
  equivalen a eventos únicos o validados para `1002:699f`. GRBM=2 y SQ=4 quedan como
  entradas de catálogo, no como validación ASIC.»

  → La **FASE M (GFX8 Counter Research)** queda en reconciliación estructural parcial:
  el catálogo se puede citar, pero la aplicación al ASIC, la semántica y la seguridad de
  programación siguen `UNKNOWN`.

### Qué cambia y qué NO cambia
- **Desbloqueado:** la parte de *mapeo documental* de eventos VI (diseño de qué se escribiría).
- **NO desbloqueado:** la *escritura* de contadores (sigue NO autorizada; FASE D etapa 3 sigue
  requiriendo autorización explícita previa).
- **NO cambia:** congelados (KDE, BIOS/VBIOS), política de no-experimentos, cap 35 W, DPM auto.

---

## 4. Gaps abiertos (no resolubles documentalmente)

| Gap | Estado | Qué haría falta |
|---|---|---|
| Confirmación de comportamiento real de transición de MCLK en la unidad (no solo política del driver) | ABIERTO | Experimentos (NO autorizados) |
| Confirmar qué instancias concretas (de las catalogadas) están habilitadas por fuses en la unidad P12 | ABIERTO | Lectura de fuses/BIOS (alto riesgo; NO autorizado) |
| Correlación de contadores programados con `W_SMU` | ABIERTO | FASE D etapa 3 (requiere autorización) |
| Causa raíz régimen 17/09 | ABIERTO | Experimentos (NO autorizados) |
| DCC/HTILE behavior real de nuestra unidad | ABIERTO | Experimentos / SPM (NO autorizados) |

---

## 5. Archivos creados en `FASE-R0-EXTERNAL-KNOWLEDGE/`

| Archivo | Contenido |
|---|---|
| `R0-1-GFX8-EVENT-IDS.md` | Catálogo GFX8: entradas source-level; no validación ASIC ni de ejecución |
| `R0-1-GFX8-EVENT-ID-REFERENCE.txt` | **2304 filas** extraídas de GPUPerfAPI v3.11.1 (histórico); no eventos únicos/validados |
| `R0-2-POWERPLAY-MCLK-SMU7.md` | Política DPM MCLK smu7 (5/16/20), validación R-07 |
| `R0-3-MESA-WORKAROUNDS-POLARIS12.md` | Workarounds radeonsi aplicables (msaa_sample_loc_bug, line filter, etc.) |
| `R0-4-ARCHITECTURE-LEXA-POLARIS12.md` | Arquitectura Lexa/Polaris12, specs y relevancia |
| `R0-5-BENCHMARKS-EXTERNOS-RX550.md` | Benchmarks/potencia externos como referencia |
| `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md` | Catálogo de herramientas (GPUPerfAPI/CodeXL/RGP/UMR/radeontop/si_perfcounter) |
| `FASE-R0-EXTERNAL-KNOWLEDGE-FINAL-REPORT.md` | Este informe |

---

## 6. Anomalías / alertas detectadas

1. `public_counter_names_vk_gfx8_baffin.txt` = `_ellesmere.txt` (idénticos): confirmado que los
   nombres expuestos son genéricos GFX8; NO hay variante ASIC para eventos.
2. Discrepancias de conteo vs doc local (CB 396 vs 405; SQ 299 vs 273; MC 33 vs 22): se deben a
   métodos de conteo distintos (rango por unidad vs selectores usables del driver). Registrar en
   la matriz de reconciliación cuando se retome FASE D/FASE M.
3. En el repo GPUPerfAPI, la rama `main`/master modernos NO contiene GFX8 (solo v3.x y anteriores).
4. `gpa_hw_counter_gfx8.cc` incluye otros bloques no documentados en la referencia (SDMA, CP, RLC,
   WD, GDS, TCA, TD, GPIN, GPUTime, GpuTimestamp): los rangos leídos están en R0-1 §2.2 pero no
   todos tienen nombres expuestos.

---

## 7. Confirmación de cumplimiento (read-only)

- [x] No se ejecutó benchmark ni workload.
- [x] No se escribió sysfs/MMIO/registros de contador.
- [x] No se instaló ni eliminó software del sistema (descargas solo a /tmp/opencode).
- [x] No se modificó Mesa, PowerPlay, Kalm, kernel, BIOS ni rx550-torneo.
- [x] No se programaron contadores HW.
- [x] Documentación creada únicamente en `FASE-R0-EXTERNAL-KNOWLEDGE/`.

## 8. Próximos pasos sugeridos (para el operador/humanitario; NO ejecutados)

1. **FASE M** → tomar `R0-1-GFX8-EVENT-IDS.md` como base documental; los IDs recuperados ya permiten
   diseñar (no ejecutar) la programación.
2. Reconciliación de aplicabilidad del catálogo, tupla evento/ASIC/instancia y enumeración
   de capacidad local antes de cualquier diseño de programación.
3. Reconciliación de conteos (CB/SQ/MC) y enumeración de instancias P12 reales cuando se retome
   la parte de instrumentación.
