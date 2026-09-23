# FASE-R0 — INFORME FINAL — EXTERNAL KNOWLEDGE RECOVERY / POLARIS12 KNOWLEDGE GAP AUDIT

> **Fecha:** 2026-09-22
> **Modo:** SOLO DOCUMENTAL / READ-ONLY. No se instaló ni eliminó software, no se escribió
> sysfs/MMIO, no se programaron contadores, no se modificó GPU/PowerPlay/Mesa/Kalm/rx550-torneo.
> Descargas de referencia a `/tmp/opencode/`; documentación creada en este directorio
> (`experiments/FASE-R0-EXTERNAL-KNOWLEDGE/`).
> **Estado:** FASE COMPLETADA.

---

## 1. Resumen ejecutivo

La FASE R-0 cierra el [GAP #1 de mayor prioridad] del proyecto: **los IDs de eventos (PERF_SEL)
de contadores HW de GFX8 / Polaris12** ahora están **documentados y verificados** desde fuente
primaria AMD (GPUPerfAPI v3.11.1), lo que **actualiza el Resultado B de FASE D** y **desbloquea el
diseño documental de FASE M**. Se validó además PowerPlay/MCLK (smu7), workarounds de Mesa
(Polaris12), arquitectura (Lexa), benchmarks externos y catálogo de herramientas históricas. Todo
sin ejecutar ningún experimento y sin tocar el sistema.

---

## 2. Matriz de Gaps / Preguntas R-0 → Resultado

| ID | Pregunta (gap) | Antes (local) | Ahora (externo) | Veredicto | Fuente principal | Confianza |
|---|---|---|---|---|---|---|
| **R-0.1** | Event IDs de performance counters GFX8/Polaris12 | **BLOQUEADO** (Resultado B: "no verificables con fuentes locales") | **RESUELTO** — catálogo GFX8 completo con nombres+valores (GRBM_GUI_ACTIVE=2, SQ_WAVES=4, etc.) en GPUPerfAPI v3.11.1 | **BLOQUEO ELIMINADO (documentalmente)** | GPUPerfAPI v3.11.1 (AMD), archivos autogenerados | **ALTA** |
| R-0.2 | Política DPM de MCLK en Polaris (smu7) | R-07 local (5/16/20) | Confirmado por código kernel (`smu7_hwmgr.c`): 128-bit → 5/16/20; gate `chip_id >= POLARIS10` | **[VERIFICADO]** (coincide con R-07) | kernel Linux smu7_hwmgr.c + commits | ALTA |
| R-0.3 | Workarounds Mesa aplicables a Polaris12 | sospechas de flags | `has_msaa_sample_loc_bug` incluye POLARIS12; `LINE_FILTER_DISABLE(family<=POLARIS12)`; `clear_db_cache_before_clear` | **[VERIFICADO]** | listas mesa-dev / código radeonsi | ALTA |
| R-0.4 | Arquitectura Lexa/Polaris12 (SP/TMU/ROP/bus/SE) | parcial | 512 SP/32 TMU/16 ROP/128-bit/50 W TDP/14 nm/2.2B transistores/101 mm²; RX550 8 CUs | **[VERIFICADO]** | TH, videocardz, TechPowerUp | ALTA |
| R-0.5 | Benchmarks externos RX 550 (referencia) | parcial | Rangos de rendimiento y potencia (gaming ~47 W; boost ~1141–1164 MHz; power virus ~820 MHz) | **[VERIFICADO]** (referencia, no medición) | TH 2017, Igor'sLAB | ALTA |
| R-0.6 | Herramientas históricas con tablas GFX8 | — | GPUPerfAPI v3.11.1 = única fuente abierta verificada; v4.0+ la eliminó; CodeXL/RGP no aportan tablas simples hoy; UMR solo registros | **[VERIFICADO]** | repos/README/release notes | ALTA |
| R-0.7 | Gaps abiertos restantes (véase §4) | — | No ampliables sin experimentos (no autorizados) | **ABIERTO** | — | — |

---

## 3. Actualización del Resultado B (FASE D)

- **Resultado B original (FASE-D-GFX8-EVENT-ID-AUDIT.md):**
  «Los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles.»
- **Resultado B actualizado (2026-09-22):**
  «Los IDs de eventos GFX8 **no están en fuentes locales**, pero **existen en fuente externa
  oficial verificable** (GPUPerfAPI v3.11.1). Ahora son **recuperables sin instalar ni escribir
  hardware**; se documentan en `R0-1-GFX8-EVENT-IDS.md` y `R0-1-GFX8-EVENT-ID-REFERENCE.txt`.
  Los valores concretos validados: GRBM PERF_SEL=2 (GUI_ACTIVE) y SQ PERF_SEL=4 (WAVES).»

  → La **FASE M (GFX8 Counter Research)** pasa de "recuperar IDs desde fuentes históricas" a
  "IDs **ya recuperados y verificados documentalmente**".

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
| Correlación de contadores programados con potencia real | ABIERTO | FASE D etapa 3 (requiere autorización) |
| Causa raíz régimen 17/09 | ABIERTO | Experimentos (NO autorizados) |
| DCC/HTILE behavior real de nuestra unidad | ABIERTO | Experimentos / SPM (NO autorizados) |

---

## 5. Archivos creados en `FASE-R0-EXTERNAL-KNOWLEDGE/`

| Archivo | Contenido |
|---|---|
| `R0-1-GFX8-EVENT-IDS.md` | Documento principal: event IDs GFX8 validados + rangos por bloque |
| `R0-1-GFX8-EVENT-ID-REFERENCE.txt` | **2304 filas** (event_id, grupo, nombre) extraídas de GPUPerfAPI v3.11.1 |
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
2. Decisión del operador sobre autorización explícita para FASE D etapa 3 (programación de
   contadores) — imprescindible para avanzar experimentalmente.
3. Reconciliación de conteos (CB/SQ/MC) y enumeración de instancias P12 reales cuando se retome
   la parte de instrumentación.