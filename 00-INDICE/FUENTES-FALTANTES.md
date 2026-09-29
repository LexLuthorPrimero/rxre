# FUENTES-FALTANTES.md — Inventario de UNKNOWN y fuentes pendientes

**Fecha de creación:** 2026-09-24
**Modo:** documental e inventario; no autoriza experimentos ni escrituras.

Este documento reúne las preguntas y brechas que siguen sin una fuente o una medición
verificable. No convierte una hipótesis en resultado y no sustituye los documentos
canónicos `02-ARQUITECTURA/open_questions.md` ni
`01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-7-CRITICAL-GAPS.md`.

| ID | UNKNOWN / brecha | Fuente o evidencia buscada | Estado | Siguiente fuente/acción | Autorización |
|---|---|---|---|---|---|
| O-ROOT | Causa del régimen histórico E1/E3/E5 | Evidencia de cap, calor, Kalm, Mesa CUSTOM y GPU; ninguna explica el régimen completo | **ABIERTO / NO RESUELTO** | Reconstruir solo con fuente primaria o autorización expresa; no inferir del nombre de los runs | Nueva autorización |
| O-MCLK | Disparador local del MCLK alto sostenido | Política smu7 y telemetría actual; no identifica el trigger ni equivale a `mem_busy` | **ABIERTO** | Capability audit/read-only de actividad y clocks; no escribir MCLK aquí | Solo lectura |
| O-PHY | `W_SMU` máxima sostenida y límite térmico | EP-06 y Superposition; solo hay máximos observados, no un techo general ni vatímetro | **PARCIAL** | Medición posterior autorizada y telemetría sincronizada | Medición: explícita |
| O-BOT | Cuello exacto de GL 640p | Métricas de presentación, CPU, VRAM/GTT y counters HW | **ABIERTO** | Perf/EP-03 o contador programado bajo su propio protocolo | counters: explícita |
| O-Mesa | Beneficio de Mesa CUSTOM en workload real | EP-05: CUSTOM=STOCK en escenas probadas | **PARCIAL / NO DEMOSTRADO** | A/B con juego/carga real; no modificar Mesa system | experiments: explícita |
| O-FPS | Atribución del «phong 1285 fps» | EP-08 no localizó el runner; el script no está en el backup | **ABIERTO / NO VERIFICABLE** | Localizar fuente original o medir una configuración equivalente, sin inventar una equivalencia | Medición: explícita |
| GAP-01 | Relación cap/SCLK y control de DPM | EP-06, smu7 y telemetría; queda sin explicación de fondo | **NO RESUELTO** | FASE I/L con protocolo de ownership y rollback | Escrituras: explícita |
| GAP-02 | MCLK sostenido bajo carga | Política upstream 5/16/20 documentada; R-4A mostró readout local 3/16/20; falta reconciliación de campos y trigger real | **NO RESUELTO** | G-M1/G-M5 read-only; capability audit | Solo lectura inicialmente |
| GAP-03 | `W_SMU` máxima y límites L2 | No hay benchmark controlado que cierre el rango | **NO RESUELTO** | FASE E/G con carga autorizada | Explícita |
| GAP-04 | Significado operativo de `mem_busy` | Métrica sysfs y semántica MC aún no reconciliada | **PARCIAL** | Relación con contadores HW y ventana temporal | Contadores: explícita |
| GAP-05 | Estado/impacto de DCC en superficies reales | Documentación Mesa; sin medición de esta RX 550 | **NO RESUELTO** | A/B software por proceso, sin tocar Mesa system | Experimento: explícita |
| GAP-06 | Atribución del workload phong histórico | No hay runner ni script de generación preservado | **NO RESUELTO** | Recuperar fuente primaria; si no, dejar UNKNOWN | Explícita |
| GAP-07 | PCIe x8 frente a x4 operativo | R-4A verificó Gen2 ×4 en esta plataforma; capacidad Gen3 ×8 es otro eje | **RESUELTO PARA ESTA PLATAFORMA** | Mantener la distinción capacidad/negociación/verificación | Ninguna |
| GAP-08 | Variante y fuses/CU de la RX 550 | 8 CU observados; confirmación documental de variante pendiente | **PARCIAL** | Fuente de identificación de la variante y snapshot read-only | Solo lectura |
| GAP-09 | Semántica/unidad de eventos MC | GPUPerfAPI no expone nombres MC suficientes | **NO RESUELTO** | Fuente AMD adicional; no diseñar una normalización | Solo documental |
| GAP-10 | Impacto de DPM intermedio/perfiles | Falta experimentación específica de PowerPlay | **NO RESUELTO** | FASE I; writes solo con autorización y restore | Explícita |
| GAP-11 | Mortalidad del bug de sample location MSAA | Workaround documentado; efecto real no medido | **NO RESUELTO** | A/B de aplicación/proceso, no cambio permanente | Explícita |

## H12 — Capability audit READ-ONLY pendiente

**Estado:** `REQUIRES CAPABILITY AUDIT`; no diseñar ni ejecutar H12 todavía.

La auditoría local debe documentar, sin escrituras ni benchmarks, al menos:

1. **WSI/entorno:** Wayland/X11/Xwayland, compositor, surface/window, monitor y
   output de la RX550; confirmar si existe una superficie onscreen real.
2. **Vulkan:** versión, RADV, ICD, `VK_KHR_present_wait2`,
   `VK_EXT_present_timing` (o equivalente realmente expuesto), familias y número de
   queues, priorities, barriers y capacidad de presentación.
3. **Timing:** timestamps de submit/completion/present, first-pixel o equivalente,
   target vblank y distinción entre offscreen y onscreen.
4. **Telemetría observable:** `fdinfo`, debugfs, gpu_metrics, PMU, `gpu_busy`,
   `mem_busy`, MCLK/SCLK y correlación con WSI; no convertir proxies en causalidad.
5. **Entorno:** ownership de queues/clientes, Xwayland/compositor, runtime PM/ASPM,
   PCIe LnkSta/LnkCap/replay y DisplayLink; todos `UNKNOWN` hasta confirmación.
6. **Salida:** una matriz de capacidades con `PRESENT/ABSENT/UNKNOWN` y fuentes; no
   crear workload H12 ni convertir M1 en VSync-limited/GPU-limited.

## Reglas de cierre

- Una fuente solo se marca **RESUELTO** si se conserva su localizador y su evidencia.
- Una medición ausente se marca **NO VERIFICABLE**; no se sustituye por una ruta inventada.
- Este inventario no autoriza scripts, benchmarks, counters, sysfs, Mesa, Kalm ni cambios
  de servicio. La frontera vigente está en
  `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md`.
