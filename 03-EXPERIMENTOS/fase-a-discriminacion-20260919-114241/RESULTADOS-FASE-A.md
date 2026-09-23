# FASE A — Discriminación del régimen SCLK/potencia de la RX 550 (read-only)
Fecha: 2026-09-19 · GPU: 1002:699f (RX 550 Polaris12) · Mesa STOCK distro (MESA_CUSTOM unset)
Resolución: 640x480 · telemetría 10 Hz (amdgpu card1 hwmon) · power1_cap = SISTEMA (35 W), NO modificado
Confinamiento: sin writes (sin cap/DPM/grub/kalm); solo DRI_PRIME=1 (GL) y seleccion VK default=AMD.

## Período/cualidad de las corridas
- run-01..03: glmark2 -s 640x480 jellyfish:duration=15 (GL, AMD). VALIDAS.
- run-04..09: vkmark shading phong/default: INVALIDAS -> corrieron en iGPU Intel HD 4600
  (MESA_VK_DEVICE_SELECT=1002:699f selecciona 0x412 3/3 hoy). telemetria card1 = idle. EXCLUIDAS.
- run-10..15: vkmark sucrose phong dur15 (10-12) y shading default (13-15), 640x480, device=AMD (0x699F). VALIDAS.

## Tabla de regimenes (ventana de estado cuasi-estable, busy>=30%)
tag                     workload         FPS     busy%  SCLK_med  SCLK_min-max     P_med    T_med
E1 (17/09, cap25W)      GL jellyfish    1121-1187  97  342MHz   298-976        25.0W    76-79C
E1 (17/09, cap25W)      VK phong        1285-1361  98  374MHz   325-1029       25.1W    75-76C
sweep (18/09, cap25W)   GL jellyfish    1035-1062  ~67-79  1071MHz  1052-1071  9.5W     65-77C
sweep (18/09, cap35W)   GL jellyfish    1043-1100  ~79-81  1071MHz  995-1071    9.3W     44-70C
sweep (18/09, cap25W)   VK shading def  347       ~77     1071MHz  1059-1071   9.7W     68-69C
sweep (18/09, cap35W)   VK shading def  351       ~90     1071MHz  1055-1071   9.7W     51C
FASE A (19/09, cap35W)  GL jellyfish   1169-1237  91-96  1071MHz   720-1071    10.4-10.6W  42-48C
FASE A (19/09, cap35W)  VK phong        396-400   100     1071MHz   562-1071     11.2-11.3W  42-47C
FASE A (19/09, cap35W)  VK shading def  403      99-100  1071MHz   564-1071     11.2W     48-50C

(Nota sweep: power de su CSV = watts; E1 = uw/1e6; promedias de results.csv de sweep contaminados por bug de columnas -> solo raws.)

## Hallazgos
- C1. El "regimen sweep" (1071 MHz / ~9-12 W / frio) es REAL y reproducible: coincide con lo que la RX 550
  hace HOY en estado frio, cap por defecto 35 W, sin ningun tunco. El cap de 25 W NO liga a 640x480:
  potencia medida 9-10 W queda muy por debajo del cap.
- C2. El "regimen E1/E3" (aprox 340-400 MHz / potencia clavada 25 W / 75-79 C / busy ~97%) NO se reproduce
  en estado frio/uncapped. Su firma (P==cap, SCLK bajo, T alta) es la de un GPU REGULADO por power-target
  termico: el SMU mantiene la potencia estimada ~ cap bajando el clock. Indica que en E1/E3 la tarjeta quedo
  CALIENTE y sostenida bajo cap 25 W.
- C3. A 640x480 el GL jellyfish NO es limitado por SCLK: al variar SCLK 340->1071 MHz el FPS solo varia
  ~+/-6% (banda 1035-1237). Por eso E1 puede dar 1121 fps con SCLK 340 MHz: el cuello NO es shader clock
  (candidatos: commits CPU, VRAM/GTT, CES). Las corridas VK phong/default si parecen mas sensibles (396 vs 403).
- C4. El cap SI liga en 1080p fullscreen: E5 (17/09) cap25W->SCLK ~390, cap35W->600-750, FPS x2-4d.
  => la RESOLUCION decide si el cap liga o no, no solo la carga.
- C5. Contradiccion E1 vs sweep = MAYORMENTE APARENTE:
  (a) los VK de E1 (phong) vs sweep (default) eran workloads distintos -> FPS no comparables 1:1, y la
  superficie de E1-vk quedó sin confirmar (1285fps@340MHz vs hoy 396@1071MHz = imposible al mismo tamano;
  O sea: O bien E1-vk corrió en otra superficie/device, O su telemetria de SCLK no era la de ese dispositivo);
  (b) el regimen E1 era card caliente+capped (throttle real), no el estado nominal;
  (c) los promedios del results.csv de sweep estaban contaminados (bug columnas).
  La unica tension irresuelta: por que E1 quedo clavado en 25W/340MHz SIENDO el mismo HW que hoy da
  1071/10W -> explicado por throttling power-target termico; verificacion definitiva = prueba cap 25W HOY (Fase B).
- C6. Seleccion VK rota HOY: MESA_VK_DEVICE_SELECT=1002:699f -> Intel 0x412 (3/3 deterministico); sin
  selector o por nombre -> AMD 0x699F. UNKNOWN por que cambio vs 17/09 (capas o mesa 26.2.2).

## Conclusiones de hipotesis (serie A/B/C)
- H1 'cap liga en 640p'   -> REFUTADA en estado tipico/frio (sweep + fase A: cap no liga, P<<cap).
                               Vigente solo como mecanismo del regimen de card caliente (E1/E3).
- H2 'thermal/power'       -> SOPORTADA (parcial): explica el regimen E1/E3; no discrimina hoy por si sola.
- H3 'P1 = estimador SMU'  -> SOPORTADA para la CONSTANCIA de 25W dentro de una corrida E1 (P fisicamente
                               constante es imposible con SCLK 298-868); el valor absoluto (P==cap) apunta a
                               throttle real por power-target, no a sensor colgado.
- H4 'resolucion'          -> SOPORTADA: 1080p expone el cap (E5); 640p no.

## Siguiente paso minimo (requiere writes -> FASE B, BLOQUEADA)
Probe controlado de cap en 4 estados (25/28/32/35W) HOY, desde frio, con cooldown entre estados,
sampler 10Hz y GL+vk phong/default:
- Si a 25W HOY se reproduce P==25W/SCLK~340-400/75C  -> confirma throttling power-target termico y cierra C5.
- Si a 25W HOY NO se reproduce (queda 1071Hz/10W)    -> E1/E3 fueron anomalia de muestreo/estado y hay que
  re-medir E1 vk phong (superficie/device) para reconciliar el FPS.