# Rejected / Refuted ideas — CIERRE 2026-09-19

> **Reconciliación terminológica 2026-09-24:** `W_SMU` histórico se etiqueta como
> `W_SMU`/potencia estimada SMU, no como vatímetro independiente.
Ideas evaluadas y el peso de cada refutación.

1. "El cap 25 W liga el SCLK en cargas ligeras (640p)" → REFUTADO. Fase B: curva plana 25→35 W,
   SCLK 1071, P 10.5-11.6 W; jelly 640 1228-1250. El cap no liga; hoy W_SMU ≤13.6 W.
2. "El régimen E1/E3 es efecto del cap por sí solo" → REFUTADO. Fase B cap 25 W desde frío no lo reproduce.
3. "Régimen E1/E3 por soak térmico (75-80 °C) + cap 25 W" → REFUTADO. EP-06: réplica a 70-71 °C caliente:
   SCLK 1071, P 10-11.5 W, sin pinzado.
4. "El SCLK bajo de E1 causó FPS bajos en GL" → REFUTADO. GL 640p insensible al SCLK (1035-1250 en
   340..1071 MHz).
5. "power1_input <= cap siempre plana/estimada igual al cap" → REFUTADO para el estado actual: sin régimen
   de throttle reporta valores reales 9-13.6 W. (En el régimen histórico SÍ se vio plano, artefacto.)
6. "E1 y sweep corrieron el mismo VK" → falso. E1 usó otro runner/estado (FPS incomparable; runner ausente).
7. "kalm/gobernador térmico (kalmd) causó el régimen histórico" → REFUTADO. El día 17/09 (dato histórico)
   había 0 eventos [Kalm]; los días 18-19/09 kalm real activo mostró régimen libre.
8. "La Mesa CUSTOM /opt/mesa-26.2.2-rx550-haswell reproduce el consumo alto / MCLK ~1300 de E5"
   → REFUTADO para arranque frío. EP-05 A/B: CUSTOM==STOCK (1071/625/9-12 W; FPS 73-203). Libs verificadas
   por maps. El régimen de E5 NO se reprodujo ni con CUSTOM ni con STOCK.
9. "E1/E3 midió otra GPU (no la RX 550)" → REFUTADO (EP-08): columna vram/gtt del header solo existe en
   amdgpu (RX 550 real); i915 hoy sin hwmon/mem_info.

NO existe a día de hoy ninguna explicación con evidencia para el régimen del 17/09; se archiva como
[NO REPRODUCIBLE] con causa [DESCONOCIDA].
