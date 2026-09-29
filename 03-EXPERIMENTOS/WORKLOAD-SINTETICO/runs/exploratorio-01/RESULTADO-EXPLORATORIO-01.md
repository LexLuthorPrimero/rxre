# Resultado — Corrida exploratoria 01 (workload sintético Vulkan Compute)

Fecha: 2026-09-20 · Autorizado: primera corrida exploratoria (solo esta; sin M2).

## Configuración ejecutada (conservadora, defaults del prototipo)

- Workload: `03-EXPERIMENTOS/WORKLOAD-SINTETICO/` (`src/main.cpp` + `src/compute.comp`, build OK).
- Comando:
  `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json MESA_VK_DEVICE_SELECT=1002:699f ./main --duration 20 --vram 268435456 --iterations 512 --stride 16 --seed 42`
- `--duration 20` s · `--vram 256 MiB` (2 GB no se llenan) · `--iterations 512` · `--stride 16` · `--seed 42`.

## Pre-flight (verificado antes)

power1_cap=35000000 · power/control=on · runtime_status=active · DPM=auto ·
vendor=0x1002 device=0x699f · idle 3.45 W / 36 °C / busy 0 %.

## Salida del workload

- device seleccionado: `AMD Radeon RX 550 / 550 Series (RADV POLARIS12) vendor=0x1002 device=0x699F`
- duración real: **20.047 s**
- dispatches: **162** · fps: **8.08**
- workgroups=4096 iterations=512 stride=16 seed=42 vram=268435456 bytes
- código de salida: **0**
- stderr: vacío
- stdout/stderr guardados en `runs/exploratorio-01/stdout.txt` / `stderr.txt`.

## Resultados (telemetría 10 Hz, 185 muestras)

| Métrica | Valor |
|---|---|
| Potencia media (toda la corrida) | 11.12 W |
| Potencia media (fase activa, gpu_busy>0) | 13.23 W |
| Potencia máxima | 13.35 W |
| SCLK (fase activa) | 1071 MHz (dominante; 141/185 muestras) |
| MCLK | 300 MHz (todo el tiempo) |
| Temp media / máxima | 40.3 / 44.0 °C |
| GPU busy (pico, fase activa) | 100 % |
| mem_busy (pico) | 18 % |
| VRAM usada máx | 274 821 120 B (0.26 GB) |
| GTT usada máx | 11 567 104 B (0.01 GB) |

## Journal / kernel

Sin mensajes de amdgpu/drm/reset/hung/intento de reset en el journal
(pre y post). Sin device lost, sin OOM, sin core dumps.

## Post-flight (verificado después)

power1_cap=35000000 · power/control=on · runtime_status=active · DPM=auto ·
vendor=0x1002 device=0x699f · idle tras corrida 3.38 W / 39 °C.

## Clasificación

- **Ejecución: [VERIFICADO]**, reproducible en esta configuración (RC=0, sin reset).
- **Gate de potencia: NO superado.** Fase activa ~13.2 W media / 13.35 W máx,
  muy por debajo del umbral ~27 W. En esta primera configuración el workload
  compute deja la GPU busy 100% con SCLK 1071 MHz pero apenas ~13 W, con MCLK
  en piso 300 MHz (carga de cómputo pura, sin banda de memoria).
- Conclusión preliminar (hipótesis §J, un solo dato): la carga pura de cómputo/
  ALU con 256 MiB de VRAM **no rampa la potencia**. Siguiente hipótesis a
  evaluar (solo con autorización): aumentar intensidad (iterations/workgroups),
  aumentar VRAM/working set, o mezclar presión de memoria/banda para elevar el
  consumo. NO se aumentó intensidad automáticamente (regla del dueño).

## Archivos del experimento

- `runs/exploratorio-01/telemetria.csv` · `stdout.txt` · `stderr.txt` ·
  `journal_pres.txt`. Ningún otro archivo se modificó después de la corrida.
