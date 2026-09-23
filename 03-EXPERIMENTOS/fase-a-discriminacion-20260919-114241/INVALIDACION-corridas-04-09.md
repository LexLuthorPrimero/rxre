# INVALIDACION de corridas VK 04-09 (y nota sobre selector)

- Fecha: 2026-09-19. Mismas variantes/workloads, pero el selector `MESA_VK_DEVICE_SELECT=1002:699f`
  (usado en las series historicas per AUDIT + rx550-power-sweep.sh:126) HOY selecciona la iGPU Intel HD 4600
  (0x8086 / 0x0412) en 3/3 intentos, NO la RX 550.
- Por lo tanto run-04..09 ejecutaron vkmark sobre la iGPU: telemetria de card1 = idle (0%, 214 MHz, 3.4 W),
  FPS irrelevantes (2876-3395). Quedan EXCLUIDOS de comparacion con la serie RX 550.
- Diagnostico (deterministico, 3/3 cada uno):
    * `MESA_VK_DEVICE_SELECT=1002:699f` -> Intel (0x412)
    * MESA_VK_DEVICE_SELECT por nombre -> AMD 0x699F
    * sin selector (default del loader)  -> AMD 0x699F
- La forma por nombre y el default seleccionan AMD de forma deterministica.
- Re-ejecucion: run-10..15 (phong N=3, default N=3) SIN selector (default = AMD), DRI_PRIME=1, stock Mesa,
  mismas variantes/workload/resolucion que las series historicas.
- UNKNOWN registrado: por que `1002:699f` selecciona Intel hoy pero (segun stdout E1) seleccionaba AMD el 17/09.
