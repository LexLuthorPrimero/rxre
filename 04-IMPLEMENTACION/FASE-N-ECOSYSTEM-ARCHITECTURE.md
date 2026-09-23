# FASE N — ECOSYSTEM ARCHITECTURE — Nomenclatura y Arquitectura del Ecosistema

> **Archivo:** `FASE-N-ECOSYSTEM-ARCHITECTURE.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.13)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑADO]. Nombre/modulo provisionales ↔ consolidados se distinguen explícitamente.
> **Estado global:** **PLANIFICADA (DOCUMENTAL)**.

---

## 1. Objetivo

Definir la **nomenclatura oficial** del ecosistema y su arquitectura (qué componente existe, qué es
provisional, qué está implementado, dependencias) para que cualquier referencia futura no mezcle
nombres. **Las fases E–Q siguen intactas.** No se implementa nada aquí.

## 2. Regla de oro en nomenclatura
- Un nombre **provisional** (diseño/concepto) NO se convierte en tecnología consolidada por existir en
  este documento. Uso explícito de la etiqueta **PROVISIONAL** en la columna.
- Solo `rx550-torneo` y el workload sintético existen como **CÓDIGO implementado** hoy.
- Cualquier proyecto futuro debe declarar PROPÓSITO/TIPO/DEPENDENCIAS/ESTADO antes de nombrarse.

## 3. Inventario del ecosistema (14 nombres oficiales)

| Nombre | Propósito | Tipo | Dependencias | Estado | Relación | ¿Provisional? | ¿Implementado? |
|---|---|---|---|---|---|---|---|
| **Polaris Performance Laboratory** (o "el Lab" / FASE K) | Marco reproducible de experimentación/benchmark | Framework transversal | K, workload sintético, METRICS-DEFINITIONS | PLANIFICADA (diseño R-2.10) | es el arnés de ejecución de E–J | NO (nombre estable) | NO |
| **PolarisBench** | Colección estandarizada de benchmarks A/B del Lab | Suite de carga | FASE K | CONCEPTO (no diseñada en detalle) | workload del Lab | PROVISIONAL | NO |
| **PolarisTelemetry** | Esquema y collectors de telemetría (schema K1) | Componente de telemetría | FASE K | DISEÑADA (K1) | interpreta los datos; escanea METRICS-DEFINITIONS | NO | NO (hoy usa los arnés de FASE D/M1) |
| **PolarisScope** | Herramienta de estadística de resultados (IC95%, outlier, ranking) | Herramienta de análisis | K1/K6 | CONCEPTO | consuma result.json | PROVISIONAL | NO |
| **PolarisDiagnose** | Clasificador de estado del sistema (DPM, cap, estado Kalm/ownership) | Diagnóstico | sysfs, estado | CONCEPTO | pre/post-flight y validación (K6) | PROVISIONAL | NO |
| **PolarisLens** | Visor/explorador de eventos de contadores GFX8 (catálogo de FASE M) | Herramienta de contadores | R-0.1/R-1 (REFERENCE), FASE M | DISEÑADA (FASE M, M-E) | presenta el catálogo; NO programa (sin autorización) | PROVISIONAL | NO |
| **RX550-Tuner** (FASE L) | Búsqueda experimental de perfiles PowerPlay/DPM | Motor de tuning | FASE K, FASE I, sysfs | PLANIFICADA (diseño R-2.11) | evalua socrades a rx550-torneo; NO lo reemplaza | NO | NO (diseño) |
| **GFX8 Counter Research** (FASE M) | Conocimiento y catálogo de contadores GFX8 | Línea de investigación | R-0/R-1, GPUPerfAPI v3.11.1 | DOCUMENTADA + DISEÑADA | abastece a PolarisLens y D-3 | NO | parcial (catálogo sí; tool no) |
| **Polaris Knowledge Base** | Base de conocimiento (knowledge.md y docs consolidados) | Capa de conocimiento | raíz + R-0/R-1 + mapa R-2.2 | EXISTE (documental) | es la capa base de todas | NO | SÍ (documentación) |
| **Ghost** | Investigación de prefetch/localidad de memoria (hipótesis de los costes de fetch) | Proyecto de investigación | FASE G, memory model | IDEA→HIPÓTESIS (diseño R-2.15) | depende de que G-M1/G-M5 prueben el costo | PROVISIONAL | NO |
| **Ghost Cache** | Mecanismo (HYPOTÉTICO) de cache de accesos de memoria | Sub-proyecto | Ghost, driver? | HIPÓTESIS sin validar | es el "si Ghost tiene evidencia" | PROVISIONAL (junto a Ghost) | NO |
| **BERRETA** | Capa para acelerar/sincronizar trabajo async/ACE GPU | Proyecto de investigación | Vulkan, ASY-01, FASE P potencial | IDEA/DISEÑO (R-2.14) | depende de evidencia de overlap | PROVISIONAL | NO |
| **RX Compression Engine** | Estudio (HYPOTÉTICO) de comprimir datos de memoria para aumentar BW efectivo | Motor de investigación | FASE G (memory model), mem model | IDEA (R-2.16) | depende de costes de VRAM/GTT medidos | PROVISIONAL | NO |
| **Orquestador Final** | Orquestador de experimentos del ecosistema (runner, telemetría, validación, decisión) | Orquestador (Software) | K, L(control), M, FASE O(gestores), N | DISEÑADO (R-2.17) | es la capa de control/pipeline; respeta SAFETY BOUNDARY | NO (nombre operativo) | NO |

## 4. Principio fundamental del ecosistema (heredado de MASTER-PLAN §K)
- **Separación de responsabilidades:** Observación (telemetría) ≠ Experimentación (runner/autorización) ≠
  Usuarios de hardware (tuner) ≠ Análisis (scope/diagnose). Ningún componente escribe sysfs a menos que
  sea el tuner autorizado con lock.
- **SAFETY BOUNDARY:** la capa que puede tocar el sistema es solo FASE L (con autorización); todos los
  demás son observadores read-only.
- **Ciclo de vida de tecnologías:** cada nombre debe pasar las etapas IDEA→DISEÑO→EVALUACIÓN→ADOPCIÓN y
  solo la ADOPCIÓN la aprueba la gobernanza (no el documento).

## 5. Dependencias agregadas (resumen)

```
Polaris Knowledge Base ◄── R-0/R-1/R-2 / msestro
        │
        ▼
Polaris Performance Laboratory (K) ◄── PolariskTelemetry (K1) ─► PolarisScope (análisis)
        │                                             ▲
        ▼                                             │
   workloads (sintetico/superposition/game-E)  PolarisDiagnose (validación K6)
        │
        ├──► GHOST/Ghost-Cache (MEM; depende G-M1/G-M5)
        ├──► RX Compression Engine (MEM; depende G-M2/G-M4)
        ├──► BERRETA (async; depende ASY-01/evidencias)
        ├──► RX550-Tuner (control; depende K/I/autorización)
        ├──► GFX8 Counter Research / PolarisLens (contadores; R-0/R-1)
        └──► Orquestador Final (orquesta todo; usa SAFETY BOUNDARY)
```

Todo **PROVISIONAL** queda marcado y requiere evidencia para ascender en el ciclo de vida (nunca en este
mismo documento).

## 6. Conclusión del diseño
FASE N queda **DISEÑADA** (14 nombres, tabla de campos, principio fundamental, ciclo de vida,
dependencias). Conserva **exactamente** la intención de la "FASE N — Technology Naming & Architecture"
ya planificada: **no implementar tecnologías**; solo nombrar y ordenar. Ningún nombre provisional se
declara tecnología consolidada (Ghost Cache, RX Compression Engine, BERRETA = PROVISIONAL/IDEA).