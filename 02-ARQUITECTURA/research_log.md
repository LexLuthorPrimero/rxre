# Research Log — CIERRE 2026-09-19
Bitácora consolidada final.

## 2026-09-17 — Sesión histórica (origen de datos NO reproducibles)
- E1 `mesa-e1-20260917-170430`, E3 `mesa-e3-20260917-213646` (+E4, E5 dentro). Régimen: power1 plano == cap
  25 W, SCLK 330-390, MCLK ~1250-1500, 74-92 °C, FPS altos (phong 1285, desktop 443@1080). Mesa CUSTOM
  `/opt/mesa-26.2.2-rx550-haswell`. kalm sin eventos ese día. **Este régimen NO se ha reproducido después.**
- Backup: `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`.

## 2026-09-18 — Kalm crash y sweep
- 14:05 `rx550-power-sweep-20260918-140527`: cap 25/35, régimen libre (1071/9-10 W) con kalm real activo.
- 08:17 kalm-gpu.service (systemd) muere (`Errno 16` busy al leer power1_cap_max); el kalm real (kalmd.py/
  kalm-lite.py) sigue vivo. Resultados: cap no liga; results.csv tiene columnas desalineadas (solo raw válido).

## 2026-09-19 — Sesión de reproducción y cierre
- **Fase A** (`fase-a-discriminacion-20260919-114241/`): read-only. 3 GL + 3 VK phong + 3 VK default válidas.
  Invalidadas corriidas 04-09 (cataron iGPU Intel - `INVALIDACION-corridas-04-09.md`). Base: 1071/10.5 W/
  42-48 °C. GL jelly 640p 1169-1237; VK phong 396-400; VK default 403.
- **Fase B** (`fase-b-cap-probe-20260919-122038/`, autorizada writes de cap): 28 runs, curva plana
  (25-35 W → 1071/10.5-11.6 W). **El régimen E1/E3 no reaparece ni con cap 25 W.**
- **EP-08**: E1/E3 muestrearon la RX 550 real (header vram/gtt = amdgpu). Runner E1 ausente en backup.
- **EP-06** (`ep06-soak-cap-20260919-205645/`, autorizada cap writes con condición display): soak 7 min y
  pesado → max 13.6 W/67 °C. Réplica E1 a 70-71 °C cap 25 W → SCLK 1071/10-11.5 W, sin pinzado. kalm
  descartado (journal). Máximo draw real: 13.6 W.
- **EP-05** (`ep05-mesa-custom-20260919-212249/`, read-only): A/B CUSTOM vs STOCK a 1080p, N=2, desde frío.
  CUSTOM==STOCK (FPS 73-203; 1071/625/9-12.2 W/48-58 °C). Libs verificadas por /proc maps. CUSTOM no
  reproduce el régimen de E5. VK sin selector → iGPU (registrado).
- **CIERRE**: especificación `RX550_BUILD_SPECIFICATION.txt`, `README.md`, `FINAL-RESEARCH-STATUS.md`
  y este conjunto de 8 archivos. No se ejecutaron más experimentos (instrucción).

## Estado final del sistema tras EP-05/cierre [VERIFICADO]
- power1_cap = 35 000 000; DPM=auto; temp ~45-47 °C; kalm real intacto (no tocado); display en Intel
  (card0, i915); sin writes sysfs pendientes; Mesa del sistema sin cambios.

## 2026-09-20 — M1 (cap sostenido 35/30 W) [COMPLETADO]
- Runner `rx550-torneo m1-schedule` (congelado durante el run). `experiments/M1-cap-35-30/runs/20260919-235939`.
- **10/10 corridas OK**, 5×35 W + 5×30 W; SET/readback y RESTORE/readback final correctos; aux sin cambios;
  sin ERROR/CRITICAL/reset/hang; `workload_rc=0`; temp máx 52 °C (< 90 °C).
- `media(power1_input @35 W)` = **12.27 W** < 27 W → compuerta activada → **NO DISCRIMINATIVO**
  (el cap no liga con `vkmark shading:phong` 1080p). ΔFPS = [0,0,0,0,0]; ΔSCLK = [0,0,0,0,0].
- Anomalía: bloque 5 FPS 74→71 en ambos brazos (simétrico, no diferencial del cap).
- HOME/XDG corregido: `stderr` vacío en las 10 corridas (sin error de Mesa shader cache).
- Resultado detallado y hashes: `experiments/M1-cap-35-30/RESULTADOS-M1.md`.
- "NO DISCRIMINATIVO" ≠ "30 W = 35 W para cualquier workload": este workload no alcanzó demanda
  suficiente para que el cap pudiera ligar. No se ejecutan más experimentos.