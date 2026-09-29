# FASE M — GFX8 COUNTER RESEARCH — Documento de Diseño

> **Archivo:** `FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.12)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]. Documentado/reconciliado en R-0/R-1; **programación de contadores sigue
> NO AUTORIZADA.**
> **Estado global:** **PLANIFICADA** / parcialmente avanzada por R-0.1 y R1-1 (documental).
>
> **RECONCILIACIÓN 2026-09-24:** el catálogo GFX8 documenta filas y nombres, pero no
> valida eventos para `1002:699f`. `v3.11.1` es extracción histórica; `v3.17` es la
> referencia operativa de tablas. Los rangos `0..N-1` no son rangos semánticamente
> seguros. La programación de counters permanece NO AUTORIZADA.

---

## 1. OBJETIVO

Diseñar la investigación de **performance counters HW GFX8 (Polaris12)** para respond a qué se puede
medir, con qué herramienta, con qué límite, y **qué falta autorizar** para hacerlo. A diferencia de la
FASE D etapa 3 (que instrumenta en vivo), FASE M es la **capa de conocimiento** del catálogo de eventos.

## 2. Estado actual documentado [desde R-0/R-1]

| Fuente | Qué aporta | Estado |
|---|---|---|
| **GPUPerfAPI v3.17** (referencia actual; `v3.11.1` histórico) | Filas y nombres genéricos GFX8; 2304 filas expuestas, no eventos únicos/validados para Polaris12 | **PARTIALLY RECONCILED / CATALOG ONLY** |
| **Mesa `groups_VI` / `ac_perfcounter`** | Tablas por clase VI; el máximo de clase no es el ASIC concreto ni una garantía semántica | **PARTIALLY RECONCILED** |
| **`gfx_8_0_enum.h`** (amdgfxregs) | Constantes de registros; sin enums PERF_SEL completos | NO contiene enums de evento |
| **UMR** | 2633 registros, ZERO enums de evento GFX8 | Sin eventos |
| **radeontop** | Solo mediciones por heurística (busy%, mem_busy) | NO contadores |
| **amdgpu kernel (local)** | Solo Kconfig/Makefile (sin python hw counters) | NO hay PMU amdgpu en perf |
| **RGP / Radeon GPU Profiler** | Moderno, SIN tablas GFX8 (GCN 8/9 eliminado); solo si se construye histórico | NO aplica hoy |
| **CodeXL** | EOL/archivado (semihistórico; requiere instalación, NO autorizada) | Referencia |

## 3. Qué sabemos / qué NO sabemos

**Sabemos (documental, verificado):**
- El catálogo contiene una asociación source-level índice↔PERF_SEL; no prueba que cada
  entrada exista en el ASIC, tenga semántica conocida o sea programable.
- La comparación de conteos es `PARTIALLY_RECONCILED` (19/23); la semántica de MC es
  `UNRESOLVED` y no se diseña normalización de bandwidth.
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

- El catálogo (R-0/R-1) permite documentar nombres y valores como **entradas de catálogo**.
  NO prueba que el evento exista en el ASIC concreto, que su semántica sea conocida ni que
  programarlo esté permitido. La autorización de ejecución es una condición separada.
- La **FASE D etapa 3** (instrumentación en vivo, SPM) es una vía de EJECUCIÓN separada de la que FASE M
  solo provee el conocimiento; ambas se activan solo con autorización explícita.

## 6. Perturbación y dependencias
- Programar contadores puede perturbar la carga (K8) y requiere root; por eso M no ejecuta nada sola.
- Dependencias: FASE K (runner) para correr con contadores; R-0/R-1 (catálogo) para la herramienta;
  la herramienta de cnt++ (M-E) depende de la arquitectura del proyecto.

## 7. Conclusión del diseño
FASE M queda **DISEÑADA** (estado, rutas M-A..M-E, límites, autorización). El conocimiento documental está **parcialmente reconciliado** (R-0/R-1); la aplicabilidad al ASIC y la semántica de eventos individualmente siguen `UNKNOWN`. Lo ejecutable (M-C/M-D/M-E) requiere autorización o instalación — **nada se
ejecutó**. La **programación de contadores permanece NO autorizada** y cualquier evento del catálogo
sigue siendo un selector documentado, no un hecho ejecutado.
