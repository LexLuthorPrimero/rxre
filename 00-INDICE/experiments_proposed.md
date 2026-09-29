# Experiments Proposed — CIERRE 2026-09-19

Estado de los experimentos candidatos tras el cierre de la investigación de reproducción.

## Ejecutados y cerrados
- **FASE A** (read-only) — completado. Base reproducible.
- **FASE B** (cap probe 25/28/32/35 W, autorizado) — completado. Régimen E1/E3 no reproduce por cap.
- **EP-08** (auditoría telemetría E1/E3) — completado. Telemetría es de la RX 550 real; runner E1 no
  está en backup.
- **EP-06** (soak + réplica E1 caliente) — completado. No reproduce el régimen; draw máx real 13.6 W.
- **EP-05** (A/B Mesa CUSTOM vs STOCK, 1080p) — completado. CUSTOM == STOCK; H8 refutada frío.
- **M1** (cap sostenido 35 W vs 30 W, `vkmark shading:phong` 1080p, 5 bloques pareados, autorizado)
  — **COMPLETADO (2026-09-20)**. 10/10 OK, 5×35 W + 5×30 W; `power1_input @35 W` = 12.27 W;
  compuerta `<27 W` activada → **NO DISCRIMINATIVO** (el cap no liga con este workload).
  ΔFPS = [0,0,0,0,0], ΔSCLK = [0,0,0,0,0]. Ver `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`.

## BLOQUEADO (no ejecutar sin nueva autorización explícita)
- **FASE C / EP-09 — Exp perfil experimental (forcing SCLK/MCLK)**: El único camino restante para explorar
  O-MCLK y O-PHY. Requiere writes a `pp_dpm_sclk`/`pp_dpm_mclk` (fuera de lo autorizado) + condition display.
  Conservar como experimento futuro: diseñado en BUILD_SPEC §28, §44.
- **EP-07** (re-medir phong para O-FPS): read-only en sí, pero el usuario instruyó NO ejecutar más
  experimentos después de EP-05. Conservar como futuro.
- **EP-03** (perf stat CPU-side sobre GL 640p): read-only; pausado hasta nueva autorización.
- Cualquier write adicional a `power1_cap` idem.
- **E1 + E2** (L1 REPRESENTACIÓN: instancing vs geometría duplicada; granularidad de
  command buffer y de submission) — **BLOQUEADO por `B-09`**, precheck 2026-09-28 sobre
  `HOST-C`. El discriminante es de herramienta, no de método ni de dispositivo:
  no hay compilador C++ (`g++`/`c++`/`clang++` ausentes), no hay
  `/usr/include/vulkan/vulkan.h` (`pkg-config vulkan` → `NO`), no hay compilador de
  shaders (`glslangValidator`/`glslc`/`spirv-as` ausentes) y no hay capas de validación.
  `c1_observer.py:555-558` sólo admite `main-graphics` (`C1_BINARY_OUTSIDE_ALLOWLIST`),
  y `main-graphics` no expone draws, instancing, command buffers ni submissions
  (`src/graphics.cpp`: 1 `vkCmdDraw`, 0 `vkCmdDrawInstanced`, `instanceCount` 0 veces).
  El dispositivo **sí** es alcanzable: `main-graphics` inicializa Vulkan y emite
  `run_start`. `NOISE = NOT_DETERMINED`, luego ningún tamaño de efecto sería
  interpretable. Diseño de controles y discriminadores ya registrados en
  `02-ARQUITECTURA/RESEARCH-LINES.md` §10.1 para que la ronda que levante `B-09` no los
  reinvente. `NOT_RUN` — estado, nunca resultado negativo.

## Traspaso a la especificación de rx550-torneo
- Las preguntas de O-BOT/O-MCLK/O-PHY quedan modeladas como casos de uso del perfil `experimental`
  (`--danger`) en `RX550_BUILD_SPECIFICATION.txt` (§28, §44): perf stat, forcing MCLK con readback,
  re-medición de phong con runner reconstruido. No como requisitos de v1.

## Recomendación
Construir primero `rx550-torneo` en modo seguro/balanced (§40-43) y, solo si se autoriza la fase
experimental, ejecutar los experimentos futuros con la instrumentación del programa.
