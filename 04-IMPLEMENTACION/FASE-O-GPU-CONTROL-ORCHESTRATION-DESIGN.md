# FASE O — GPU CONTROL & ORCHESTRATION RESEARCH — Documento de Diseño

> **Archivo:** `FASE-O-GPU-CONTROL-ORCHESTRATION-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.18)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO]. Herramientas externas = OBJETOS DE EVALUACIÓN, no soluciones adoptadas.
> **Estado global:** **PLANIFICADA**. No se instaló ninguna herramienta.

---

## 1. OBJETIVO

Evaluar **acercamientos de control de la GPU** existentes (LACT, CoreCtrl, amdgpu-clocks, y nuestra
propia rx550-torneo) para decidir si conviene adoptar, integrar o conservar los nuestros. La decisión se
basa en **capacidades comparadas**, no en intención de reemplazar rx550-torneo.

## 2. Criterios de comparación (marco de evaluación)

| Criterio | Qué pregunta responde |
|---|---|
| **Capabilities** | ¿qué puede tocar? (power cap, DPM niveles, perfil power, runtime PM, OD) |
| **Ownership** | ¿adquiere el control de sysfs? ¿hay lock? ¿detecta a otros gestores? |
| **Profiles** | ¿gestión de perfil (GUI/CLI/automático)? |
| **Telemetry** | ¿puede ser fuente de datos para el Lab K? ¿exporta CSV/JSON? |
| **Runtime PM** | ¿gestiona suspensiones headless? |
| **PowerPlay** | ¿soporta ppfeaturemask/pptable/OD (alto riesgo)? |
| **Rollback** | ¿protección del estado original? ¿snapshot? |
| **GUICLI/automation** | ¿existe interfaz conservable para el Orquestador? |
| **Risk** | ¿puede romper el sistema (writes sin verificación)? |
| **Polaris compatibility** | ¿soporta GFX8/Polaris12 / amdgpu? |

## 3. Evaluación inicial documental (sin instalar nada)

| Herramienta | Capacidades | Ownership | GUI/CLI | Risk | Polaris12 | Estado local |
|---|---|---|---|---|---|---|
| **LACT** (Linux AMD Control Tool) | power/RPM/DPM/OD, perflevel | puede competir por sysfs; requiere dæmon | GUI | medio (OD/pptable si se habilita) | se espera sí (amdgpu genérico); NO VERIFICADO localmente | NO instalada (no autorizado) |
| **CoreCtrl** | DPM/OD, perfiles por app | control de sysfs | GUI | medio | se espera sí; NO VERIFICADO | NO instalada |
| **amdgpu-clocks** | lectura/escritura de clocks simples | minimal | CLI | bajo (solo escribir pp_dpm) | sí (amdgpu) | NO instalado (evaluado en R0-6? documental) |
| **rx550-torneo** (nuestra) | cap, dpm, perfiles, runtime, rollback con verificación | lock + ownership | CLI | bajo (con --danger para experimental) | sí (1002:699f) | IMPLEMENTADA y validada (65/55/56/112 checks) |

**Conclusión direccional (no decisiva):** rx550-torneo ya cubre los casos que el proyecto tiene hoy
(regimen controlado con rollback verificado) y añade la verificación de cambio de estado y ownership que
LACT/CoreCtrl no garantizan explícitamente. Las externas valen como **objeto de evaluación de referencia**
y de futura comparación en el momento en que el Lab quiera más perfiles/OD — nada se adopta hoy.

## 4. Protocolo GPU Ownership (aplicable a cada externa)
- **detectar** qué gestor está activo (procesos, sysfs writable) → **verificar** (que no escriba en el
  mismo campo) → **adquirir** (ocupar el campo con nuestro write test en ventana autorizada) →
  **experimentar** → **restaurar** → **liberar** → **verificar** (R1-8 Capa Transversal).
- Kalm se evalúa SIEME igual (detectar activo en vivo; no asumir).

## 5. Integración con el Orquestador y K
- FASE O produce la **tabla de capacidad-habilidad** que el Orquestador (R-2.17) usara para decidir a qué
  herramienta delegar (o no) el control: si una externa no respeta ownership/verificación, queda como
  NO CANDIDATA para el pipeline automático.

## 6. Límites
- **NO instalar/añadir nada** en esta fase.
- **NO cambiar** rx550-torneo (herramienta oficial) ni sus perfiles.
- **NO adoptar** ninguna externa en la operativa sin una decisión documentada de gobernanza.

## 7. CONCLUSIÓN DEL DISEÑO
FASE O queda **DISEÑADA** (marco de comparación + evaluación documental inicial direcciónal). La decisión
de adopción integración **queda abierta a una evaluación futura con instalación autorizada** (fuera de
R-2). rx550-torneo sigue siendo la herramienta operativa; LACT/CoreCtrl/amdgpu-clocks = objetos de
evaluación, no soluciones adoptadas.