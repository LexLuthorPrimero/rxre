# Resultado — Corrida exploratoria 02 (workload sintético, presión memoria/bandwidth)

Fecha: 2026-09-20 · Autorizado: segunda corrida exploratoria (sin M2).

## Configuración (una sola; código/entorno idénticos, solo parámetros)

- Binario `main` sin cambios (md5 `a7e7ace54e2d1198729ec5e935421982`), shader `src/compute.comp` intacto.
- Comando:
  `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json MESA_VK_DEVICE_SELECT=1002:699f ./main --duration 20 --vram 536870912 --iterations 1024 --stride 256 --seed 42`
- `--duration 20` s · `--vram 512 MiB` (moderada, lejos de 2 GB) · `--iterations 1024` (doble de ALU+accesos vs. corrida 1) · `--stride 256` (mayor dispersión, presión bandwidth) · `--seed 42` (mismo).

## Pre-flight (verificado antes)

power1_cap=35000000 · power/control=on · runtime_status=active · DPM=auto · vendor=0x1002 device=0x699f · idle 3.37 W / 38 °C / busy 0 %.

## Salida del workload

- device: `AMD Radeon RX 550 / 550 Series (RADV POLARIS12) vendor=0x1002 device=0x699F`
- duración real: **20.146 s**
- dispatches: **51** · fps: **2.53**
- código de salida: **0** · stderr vacío.

## Resultados (telemetría 10 Hz, 188 muestras)

| Métrica | Valor |
|---|---|
| Potencia media (toda la corrida) | 11.85 W |
| Potencia media (fase activa, gpu_busy>0, 176 muestras) | **12.38 W** |
| Potencia máxima | 12.51 W |
| SCLK (fase activa) | 1071 MHz dominante (176/188) |
| MCLK | 300 MHz (todo el tiempo, piso) |
| Temp media / máxima | 43.0 / 46.0 °C |
| GPU busy (fase activa) | 100 % |
| mem_busy | 3–7 % (pico 7 %) |
| VRAM usada máx | 543 780 864 B (0.51 GB) |
| GTT usada máx | ~12 MB |

## Comparación con corrida 01 (ALU pura)

| Métrica | Corrida 01 (ALU, 256 MiB, iter 512, stride 16) | Corrida 02 (ALU+memoria, 512 MiB, iter 1024, stride 256) |
|---|---|---|
| Pot media activa | 13.23 W | 12.38 W |
| Pot máxima | 13.35 W | 12.51 W |
| mem_busy máx | 18 % | 7 % |
| MCLK | 300 MHz | 300 MHz |
| Dispatches / fps | 162 / 8.08 | 51 / 2.53 |

**Aumentar el working set y la dispersión NO aumentó el consumo: lo redujo ~0.85 W.**
El SSBO de 512 MiB ni siquiera generó presión DRAM real: MCLK permaneció en el
piso de 300 MHz y mem_busy solo 3–7 % (la carga siguió siendo limitada por el
shader, no por la banda de memoria). Con iteraciones el doble y stride 16×, el
rendimiento bajó (2.53 fps) pero la potencia no subió: el shader está saturado
de ALU/latencia en SCLK 1071 MHz sin activar banda de memoria.

## Journal / kernel

Sin mensajes amdgpu/drm/reset/hung/device lost/OOM (pre y post). Sin crashes,
sin core dumps, sin procesos residuales.

## Post-flight (verificado después)

power1_cap=35000000 · power/control=on · runtime_status=active · DPM=auto ·
vendor=0x1002 device=0x699f · idle 3.37 W / 39 °C / busy 0 %.

## Clasificación

- Ejecución: **[VERIFICADO]** (RC=0, sin reset).
- Gate de potencia: **NO superado** (~12.4 W << 27 W). La presión de
  memoria/bandwidth en esta configuración no aumenta el consumo; incluso lo
  reduce levemente respecto de la ALU pura de la corrida 01.
- Resultado concluyente para esta vía de parámetros: simplemente "más
  iteraciones + más dispersión" no rampa la potencia en Polaris12/RADV con este
  shader. Evidencia de que el límite es la ejecución del shader (SCLK pegado a
  1071 MHz y mem_busy bajo) y NO el acceso a memoria ni el tamaño del SSBO.
- No se aumentó intensidad automáticamente (regla del dueño).

## Archivos del experimento

- `runs/exploratorio-02/telemetria.csv` · `stdout.txt` · `stderr.txt` ·
  `journal_pres.txt`. Ningún otro archivo modificado tras la corrida.