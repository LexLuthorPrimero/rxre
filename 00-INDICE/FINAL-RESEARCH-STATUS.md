# FINAL-RESEARCH-STATUS.md — Estado final de la investigación
Fecha: 2026-09-19 · Colección del cierre documental de la sesión RX 550.

## Qué sabemos (reproducible y verificado hoy)
- RX 550 = Polaris12/GFX8, PCI `1002:699f`, amdgpu. Display en Intel HD 4600 (card0); RX 550 es GPU
  secundaria sin salida de video (decisión deliberada de seguridad).
- En las escenas actuales la RX 550 demanda **9.4-13.6 W** y el cap (25-35 W) **no liga**. Máximo draw
  real medido: **13.6 W** (2560×1440 texturizado, EP-06). En carga: SCLK 1071, MCLK 625 (pico transitorio
  1500), temp 42-58 °C en runs cortos; plateau soak 64 °C.
- **M1 (2026-09-20, `vkmark shading:phong` 1080p, cap sostenido 35/30 W, 10 corridas pareadas):**
  `power1_input @35 W` = **12.27 W** → compuerta `<27 W` activada → **NO DISCRIMINATIVO** (el cap no liga
  con este workload). ΔFPS y ΔSCLK pareados = 0. Ver `experiments/M1-cap-35-30/RESULTADOS-M1.md`.
- FPS base (Mesa stock o CUSTOM indistinguibles, DPM auto, cap 35 W): GL jelly 640p 1228-1250; VK phong
  640p 396-413; VK shading 640p 403-413; jelly 1080p 202-204; desktop 1080p 199-202; shading 1080p 73.
- GL jellyfish 640p NO es SCLK-bound (FPS ~igual en 340-1071 MHz) — bottleneck fuera del shader.
- power1_input es estimador SMU; hoy reporta valores reales (no plano).
- Mesa CUSTOM (`/opt/mesa-26.2.2-rx550-haswell`) se carga real (maps: `/opt/.../libgallium-26.2.2.so`,
  renderer `git-3281a69a8b`) y se distingue de STOCK (`/usr/lib64/...`).
- Vulkan sin selector cae en la iGPU (0x412); hay que forzar ICD RADV y verificar 0x699F.
- kalm real (`kalmd.py`/`kalm-lite.py`) está activo; `kalm-gpu.service` de systemd está muerto.

## Qué NO sabemos (pendiente, ver open_questions.md y BUILD_SPEC §45)
- **Causa raíz del régimen histórico** (25-31 W / SCLK ~350-390 / MCLK ~1250-1500 / 74-92 °C).
- Qué dispara/desdibuja el MCLK sostenido alto (hoy solo 625 con picos; nunca 1250-1500 sostenido).
- Draw real máximo sostenido y límite térmico efectivo extremo.
- Bottleneck exacto del GL 640p (CPU/submissions/present/VRAM-GTT).
- Qué es el "phong 1285 fps" (origen del dato).

## Qué quedó DESCARTADO (con evidencia)
- Cap 25 W liga SCLK en cargas ligeras → Fase B (curva plana).
- Régimen E1/E3 por cap simple o por soak+cap hasta 70-71 °C → Fase B + EP-06 (sin pinzado).
- kalm/gobernador como causa del régimen histórico → journal (17/09 sin kalm; 18-19/09 kalm activo con libre).
- Mesa CUSTOM como causa del consumo de E5 → EP-05 (CUSTOM == STOCK; libs verificadas).
- E1/E3 muestrearon otra GPU → EP-08 (telemetría es de la RX 550 real).

## Qué quedó sin reproducir ([NO REPRODUCIBLE], no tratar como hecho)
- Todo el régimen E1/E3/E5 del 17/09: power1==cap 25 W, SCLK 350-390, MCLK ~1250-1500, 74-92 °C,
  phong 1285 fps, desktop 443@1080@35 W, jelly 691@35 W. Ningún parámetro autorizado (cap, calor, kalm,
  Mesa stock o CUSTOM) lo reprodujo. **No es una especificación de rendimiento esperado.**

## Qué arquitectura se recomienda implementar
`rx550-torneo` totalmente seguro y reversible, con la separación display/RX550 como pilar:
- gpu_finder por PCI `1002:699f` (nunca asumir card index ni salida de video),
- state_manager + failsafe (snapshot, readback, rollback, restauración post-crash),
- telemetry CSV con campos definidos y detección STOCK/CUSTOM por /proc maps,
- perfiles balanced / locked / 25W / experimental (forcing solo con `--danger` y readback),
- DPM auto en el camino normal; pp_table/SPPT/VBIOS prohibidos; kalm y display intocables.
Detalle completo: **RX550_BUILD_SPECIFICATION.txt** (§19-43).

## Siguiente paso de implementación
1. Implementar `rx550-torneo` v0 en modo balanced (gpu_finder + telemetry + state_manager + failsafe)
   sin writes reales, validando contra las referencias de §15 (jelly 640p ≈ 1228-1250, shading 1080p ≈ 73).
2. Usar el test suite de §43 (SIGTERM/muerte simulada, restauración, readback) como criterio de cierre.
3. Solo después, y con autorización explícita nueva, abordar Fase C (perfil experimental, EP-09).

## Estado del sistema al cierre (verificado)
power1_cap = 35 000 000 · DPM auto · temp ~45-47 °C · kalm real intacto · display Intel card0 · sin writes
sysfs pendientes · Mesa del sistema sin cambios; no se ejecutan más experimentos por ahora.