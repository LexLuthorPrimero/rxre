# FASE M — GFX8 COUNTER RESEARCH — Documento de Diseño

> **Archivo:** `FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.12)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]. Documentado/reconciliado en R-0/R-1; **programación de contadores sigue
> NO AUTORIZADA.**
> **Estado global:** **PLANIFICADA** / parcialmente avanzada por R-0.1 y R1-1 (documental).

---

## 1. OBJETIVO

Diseñar la investigación de **performance counters HW GFX8 (Polaris12)** para respond a qué se puede
medir, con qué herramienta, con qué límite, y **qué falta autorizar** para hacerlo. A diferencia de la
FASE D etapa 3 (que instrumenta en vivo), FASE M es la **capa de conocimiento** del catálogo de eventos.

## 2. Estado actual documentado [desde R-0/R-1]

| Fuente | Qué aporta | Estado |
|---|---|---|
| **GPUPerfAPI v3.11.1** (AMD GPUOpen, tag) | Catálogo GFX8 completo (2304 eventos extraídos): GRBM GUI_ACTIVE=2, SQ WAVES=4 y demás por bloque (CB/SQ/PA/SPI/TA/TCP/TCC/VGT/SX/MC…) | **[VERIFICADO]** R0-1 |
| **Mesa `groups_VI` / `ac_perfcounter`** | Tablas por clase VI (selectors); máxima sobre clase (limit); rangos seguros CB 0..395, SQ 0..272, MC 0..21 | **[VERIFICADO]** / R1-1 (reconciliación) |
| **`gfx_8_0_enum.h`** (amdgfxregs) | Constantes de registros; sin enums PERF_SEL completos | NO contiene enums de evento |
| **UMR** | 2633 registros, ZERO enums de evento GFX8 | Sin eventos |
| **radeontop** | Solo mediciones por heurística (busy%, mem_busy) | NO contadores |
| **amdgpu kernel (local)** | Solo Kconfig/Makefile (sin python hw counters) | NO hay PMU amdgpu en perf |
| **RGP / Radeon GPU Profiler** | Moderno, SIN tablas GFX8 (GCN 8/9 eliminado); solo si se construye histórico | NO aplica hoy |
| **CodeXL** | EOL/archivado (semihistórico; requiere instalación, NO autorizada) | Referencia |

## 3. Qué sabemos / qué NO sabemos

**Sabemos (documental, verificado):**
- El índice de evento CONCIDECE con el PERF_SEL escribido en `*_PERFCOUNTERn_SELECT` (p.ej. GRBM=2,
  SQ=4) — convalidado por R-0.1 (estructura del catálogo) y R1-1 (reconciliación con Mesa).
- Rangos seguros y discrepancy 396 vs 405 (CB), 299 vs 273 (SQ), 33 vs 22 (MC) → PARTIALLY_RECONCILED;
  semántica de MC **UNRESOLVED** → **no diseñar normalización de MC**.
- Qué se puede medir read-only hoy (metadatos) está en K9 (Capability Matrix) y METRICS-DEFINITIONS.

**No sabemos (gaps):**
- comportamiento real en vivo (SAMPLE/START/STOP del CP) sin autorización para programar.
- la semántica exacta del bloque MC.
- el parseo de paquetes CP para SPM (futuro: FASE D et.3).

## 4. Rutas de investigación (diseñadas; todas read-only hasta autorización)

| Ruta | Qué haría | Autorización necesaria |
|---|---|---|
| **M-A: lectura del código local (Mesa/kernel)** | verificar en la FUENTE local (26.2.2) el estado de los workaround/switches (H5/H6/H7) y confirmar grupos_VI | NINGUNA (lectura) |
| **M-B: reconstrucción de catálogo por bloque vs Mesa** | script/csv cruzando R0-1 REFERENCE con `groups_VI` local (lectura) para cierre de la reconcil. MC | NINGUNA (compute) |
| **M-C: estudio RGP/CodeXL histórico** | descargar/instalar herramienta histórica validada (autorización); evaluar en offline | INSTALACIÓN (no autorizada aún) |
| **M-D: diseño de sesión de contadores (con permiso)** | plan exacto de qué bloques/eventos programar (D-3/et.3) y qué medir — volverá a gobernanza | PLANEO interno |
| **M-E: integración de evento IDs a herramienta propia** | tarea de código futuro (no en R-2): tool que use PERF_SEL con las tablas de R-1 | Programación de códigos del proyecto (futura) |

## 5. Event IDs documentados ≠ autorización

- El catálogo (R-0.1) prueba que **existen** los IDs y su semántica de PERF_SEL. NO prueba que
  programarlos esté permitido ni que la herramienta esté presente. La **DE MANDATO** de
  `GRBM_PERFCOUNTER0_SELECT=0x2` pasa de "no válido científicamente" a "valido documentalmente, pero
  **ejecución sigue NO AUTORIZADA**" (adenda R-1 en MASTER-RESEARCH-STATUS §R-0).
- La **FASE D etapa 3** (instrumentación en vivo, SPM) es una vía de EJECUCIÓN separada de la que FASE M
  solo provee el conocimiento; ambas se activan solo con autorización explícita.

## 6. Perturbación y dependencias
- Programar contadores puede perturbar la carga (K8) y requiere root; por eso M no ejecuta nada sola.
- Dependencias: FASE K (runner) para correr con contadores; R-0/R-1 (catálogo) para la herramienta;
  la herramienta de cnt++ (M-E) depende de la arquitectura del proyecto.

## 7. Conclusión del diseño
FASE M queda **DISEÑADA** (estado, rutas M-A..M-E, límites, autorización). El conocimiento documental ya
está resuelto (R-0.1, R1-1). Lo ejecutable (M-C/M-D/M-E) requiere autorización o instalación — **nada se
ejecutó**. La **programación de contadores permanece NO autorizada** y cualquier evento del catálogo
sigue siendo un selector documentado, no un hecho ejecutado.