# R1-8 — CAPA TRANSVERSAL KERNEL/DRIVER — ARCHIVO DE AUDITORÍA (READ-ONLY)

> **Tarea R-1.8** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Consolida la investigación documental de la Capa Transversal (KERNEL/DRIVER COMPATIBILITY & EDGE-CASE LAYER,
> sección final de MASTER-PLAN). No se ejecuta nada; solo se audita el estado del conocimiento y cómo/qué
> experimentar en el futuro.

---

## 1. L.0 — Capability Audit de ppfeaturemask (READ-ONLY)

**Cuestión:** qué capacidades/overclock/UVD/UVC/PP_OD del controlador SMU7 están hoy disponibles en la RX 550.

Estado: `ppfeaturemask` actual = `0xfff7bfff` (leído vía sysfs, sin modificarse). PP_OVERDRIVE_MASK = `0x4000`.
Bit de OD (0x4000) **APARENTEMENTE no activo** con la máscara actual → overdriving no disponible hasta FASE L.
**NO MODIFICAR** (congelado). Paso 0 = lectura y estudio del campo; NO es «establecer 0x4000».

Registro: MASTER-PLAN §FASE L; congela `ppfeaturemask` en MASTER-RESEARCH-STATUS.

## 2. pp_od_clk_voltage (objeto de investigación independiente)

Escrituras a `pp_od_clk_voltage` son **writes → no autorizadas en R-1**. Documento base es genérico; para la RX 550
la disponibilidad exacta de las extensiones OD no está verificada. Requiere verificación de capacidad real antes de
diseñar experimento (FASE L).

## 3. pp_dpm_sclk / pp_dpm_mclk — edge cases

- `WRITE SUCCESS ≠ STATE CHANGE VERIFIED`: escribir OK no implica que el DPM cambió de estado.
- Escritura de frecuencias con espaciado/acople inesperados (SCLK con dependencia de cap: GAP-01).
- Leyenda de verificación propuesta: readback del estado + telemetría (SCLK real) antes/después.
- Estas escrituras son **writes → NO autorizadas en R-1**.

## 4. pp_table / SPPT / VBIOS

Documentación de bajo riesgo es válida; **extracción/modificación de VBIOS = HIGH-RISK, solo investigación
futura** y con autorización explícita adicional. No hay nada ejecutado.

## 5. Telemetría — clasificación A/B/C/D

| Clase | Descripción | Uso |
|---|---|---|
| A | Lectura directa sysfs/amdgpu (power1_input, gpu_busy, mem_busy…) | siempre disponible, cross-check |
| B | Herramientas externas con logging propia (radeontop…) | complementaria, declarar método |
| C | Contadores HW programados (PERF_SEL) | futura, requiere autorización + mapa |
| D = NO VERIFICADO | datos declarados no comprobados | no usar en diseño |

## 6. Herramientas de orquestación como objetos de evaluación

LACT / CoreCtrl / amdgpu-clocks: evaluar capacidades vs `rx550-torneo`, aplicar Protocolo GPU Ownership
(detectar→verificar→adquirir→experimentar→restaurar→liberar→verificar). No reemplazar rx550-torneo sin comparar.
Sin ejecución en R-1.

## 7. Observability Perturbation

Toda herramienta de observación puede perturbar lo observado (contadores requieren PKT3_EVENT_WRITE; shows logs;
polling). Documentar la perturbación esperada de cada futura técnica antes de medir.

## 8. Hardware Identity

Identificación robusta de la RX 550: por vendor+device+PCI BDF, resolviendo el nodo sysfs dinámicamente (no
depender exclusivamente de `/sys/class/drm/card1`). Se consolida aquí la estrategia definida en MASTER-PLAN §B.

## 9. Capability Matrix (estado)

| Capacidad | Estado verificado | Fuente |
|---|---|---|
| Overdrive (PP_OD) | NO DISPONIBLE (mask sin 0x4000) | sysfs ppfeaturemask |
| Perfiles DPM | verificado R-07 / MCLK smu7 | R0-2 + local |
| Contadores GFX8 mapa | VERIFICADO (R0-1) | GPUPerfAPI v3.11.1 |
| Semántica MC | UNRESOLVED | R1-1 |
| Workarounds Mesa GFX8 | VERIFICADO (R0-3) | código Mesa |
| MSAA sample loc bug en POLARIS12 | VERIFICADO presente | R0-3 |

## 10. Clasificación de afirmaciones externas

Regla (MASTER-PLAN): toda afirmación externa se registra en `UNVERIFIED-CLAIMS.md` con estado antes de usarla.
Las de este archivo provienen de fuentes primarias y se marcan [VERIFICADO]/[DOCUMENTADO].

---

**Confirmación read-only:** no se escribió ningún sysfs, ni ppfeaturemask, ni pp_od_clk_voltage, ni VBIOS, ni
pp_table; solo lectura de documentación.