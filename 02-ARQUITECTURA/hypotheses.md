# Hypotheses — CIERRE 2026-09-19

## Confirmadas / Soportadas (evidencia actual)
- H3 — `power1_input` = estimador SMU: [SOPORTADA]. Hoy reporta valores reales < cap; el "clavado==cap"
  solo apareció en el régimen histórico (descartado como hecho operacional).
- H6 — GL jellyfish 640p NO es SCLK-bound: [VERIFICADO] (FPS ~1035-1250 en SCLK 340-1071); causa exacta
  es HIPÓTESIS (CPU/submissions/present/VRAM-GTT).
- En las escenas actuales el cap (25-35 W) no liga y el draw real es 9.4-13.6 W: [REPRODUCIBLE].

## Descartadas (refutadas)
- H1 — "el cap 25 W liga el SCLK en cargas ligeras (640p)" → REFUTADA (Fase A/B: curva plana, 1071 siempre).
- H2/H5 — "régimen E1/E3 = power-target throttling por 25 W cap (+ soak)" → REFUTADA (Fase B frío y EP-06
  caliente hasta 71 °C: SCLK 1071, P 10-11.5 W, sin pinzado).
- H7 — "kalm/gobernador térmico causó el régimen histórico" → REFUTADA (journal: kalm real ACTIVO 18-19/09
  con régimen libre; 0 eventos el 17/09).
- H8 — "Mesa CUSTOM /opt/mesa-26.2.2-rx550-haswell reproduce el consumo alto de E5" → REFUTADA para arranque
  frío (EP-05: CUSTOM==STOCK, 1071/625/9-12 W).
- O1-b — "E1/E3 muestrearon otra GPU" → REFUTADA (EP-08: header vram/gtt solo existe en amdgpu = RX550 real).

## No reproducibles (históricas; no tratar como hipótesis de trabajo)
- El régimen E1/E3/E5 completo (25 W pin / SCLK 350-390 / MCLK ~1250-1500 / 74-92 °C; phong 1285 fps,
  desktop 443 a 1080) fue OBSERVADO el 17/09 pero NO REPRODUCIDO hoy bajo ningún parámetro autorizado
  (cap, calor hasta 71 °C, escenas, kalm, Mesa stock o CUSTOM). No hay hipótesis viva nueva para él;
  clasificar como [NO REPRODUCIBLE]/causa [DESCONOCIDA] hasta nueva autorización.

## Activas (hipótesis de siguiente fase, solo si se autoriza)
- Bottleneck de GL 640p = lado CPU (submissions/present): perf stat pendiente (EP-03).
- MCLK alto sostenido (1500) como disparador del consumo real alto: fuerza pp_dpm experimental (EP-09 futuro
  con permiso explícito).
- Estabilidad/mérito de forcing DPM vs AUTO: sin evidencia aún; no se recomienda en el camino normal.