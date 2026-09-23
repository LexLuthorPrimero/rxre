# M1 — Esquema de datos (telemetry.csv)

Muestreo 10 Hz por corrida. Una fila por muestra. El sampler es SOLO LECTURA y
no toca sysfs para escribir.

| columna | unidad | origen | notas |
|---|---|---|---|
| `ts` | s (epoch) | `time.time()` | reloj de pared del sampler |
| `t_rel` | s | monotónico | tiempo relativo desde el inicio del sampler |
| `gpu_busy_pct` | % | `device/gpu_busy_percent` | |
| `mem_busy_pct` | % | `device/mem_busy_percent` | |
| `sclk_hz` | Hz | `hwmon/freq1_input` | SCLK efectivo |
| `mclk_hz` | Hz | `hwmon/freq2_input` | MCLK efectivo |
| `power1_uw` | µW | `hwmon/power1_input` | **estimador SMU**, no eléctrico |
| `power1_cap` | µW | `hwmon/power1_cap` | cap vigente (read-only) |
| `temp_mc` | m°C | `hwmon/temp1_input` | |
| `runtime_status` | texto | `device/power/runtime_status` | |
| `event` | texto | derivado | p.ej. `EVENT_T>=90C` |
| `cap_target` | µW | runner | cap objetivo de esa corrida |

## Ventana de análisis
Se descartan las muestras con `t_rel < 5.0` (warm-up). Métricas sobre el resto.

## Artefactos por corrida (`runs/<blockNN>-armM-<target>/`)
- `telemetry.csv` — muestras crudas (nunca se edita).
- `stdout.txt`, `stderr.txt` — salida del workload (FPS).
- `audit.json` — resultado del runner (original, target, readbacks, aux, eventos,
  `workload_rc`, `gpu_reset_check`).
- `guard.log` — solo si el guard intervino (crash).

## `gpu_reset_check` (dentro de `audit.json`)
Ventana `journalctl -k` solo-lectura, un formato (`short-iso`), capturada entre el
inicio y el fin del workload.
- `checked` (bool): `true` solo si la fuente respondió y el formato coincide.
- `error`: motivo si `journalctl` no fue accesible (`null` si ok).
- `format` / `expected_format`: formato observado vs esperado (`short-iso`).
- `since` / `until` (epoch): ventana temporal consultada.
- `matches`: líneas con firmas inequívocas de reset/hang; si no está vacío el run
  es `CRITICAL` (`GPU_RESET_OR_HANG`). Se excluye el mensaje benigno
  `Disabling VM faults because of PRT request!` y no se cuenta `VM fault` aislado.

## Artefactos globales
- `m1-schedule.json` — resumen de los 5 bloques (`stopped_early`, resultados, runs).
- `RESULTADOS-M1.md` — análisis derivado (fuera de `runs/`).

## Derivados por corrida (calculados, no almacenados como crudo)
FPS (de stdout), median/media/min/max/p1/p99/IQR de `sclk_hz`, `mclk_hz`,
`power1_uw`, `temp_mc`; media de `gpu_busy_pct`/`mem_busy_pct`; valores distintos
de `runtime_status`; errores/reset de kernel en el intervalo.
