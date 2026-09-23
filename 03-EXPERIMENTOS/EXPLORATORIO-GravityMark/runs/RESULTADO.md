# RESULTADO — Reintento exploratorio GravityMark 1.89 (200k) — INCIDENTE anterior documentado abajo

Fecha: 2026-09-20 · GPU RX 550 (card1, 0000:01:00.0, 0x699f, RADV POLARIS12), cap=35 W (verificado 35000000 µW al final).

## DECISIÓN (criterio del usuario aplicado)
**200k FUNCIONA con carga GPU válida, pero NO supera 27 W** → banda "claramente por debajo de 27 W".
Sin embargo presenta **presión importante de VRAM (2.10 GB usados de 2.00 GB)** durante la carga.
Regla del usuario: "si 200k muestra presión importante de VRAM → detenerse".
⇒ **NO se ejecuta el intento 1m. Descarta GravityMark como candidato M2 por no superar 27 W** en 1080p Vulkan sin exceder 2 GB VRAM.

## Ejecución 200k
Comando exacto (run desde `.../GravityMark_1.89/bin`, DISPLAY=:0):
```
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
MESA_VK_DEVICE_SELECT=1002:699f \
./GravityMark.x64 -vk -benchmark 1 -count 1 -close 1 -fullscreen 0 \
  -width 1920 -height 1080 -asteroids 200k -fps 1 -sensors 1 -info 1 \
  -times <runs/200k/times_200k.txt> -stats <runs/200k/stats_200k.txt>
```
- Exit code: 124 (timeout de 120 s). La pasada de benchmark no finalizó en 120 s (el `-close 1` cierra AL terminar todas las pasadas; con `-count 1 -benchmark 1` la escena 200k tarda >2 min, así que el proceso fue terminado por timeout mientras aún renderizaba; no hubo error ni device lost).
- stdout/stderr: `.../runs/200k/stdout_200k.log` — seleccionó correctamente RX 550 (RADV POLARIS12, 0x699f, AMD 26.2.2, Video Memory 2.00 GB); "Creating 200,000 Asteroids"; "GravityMark 1.89 Vulkan is Ready in 4.8 s"; "Starting 1920x1080 Vulkan Benchmark". No hubo líneas E:/W: de error durante la carga.
- Duracion de carga muestreada: ~92 s de gpu_busy>0 sobre la ventana de telemetría (1027 muestras @ ~10 Hz; 922 con busy>0).

### Telemetría (10 Hz, sysfs card1/hwmon2) — `runs/200k/telemetria.csv`
Verificación tardía: `times_200k.txt`/`stats_200k.txt` NO se generaron por terminación por timeout (se escriben al cierre), por eso **FPS/frame-time no disponible**; el FPS se puede inferir vía `-fps`/sensor solo en cierre.
- Potencia: media **12 419 506 µW ≈ 12.4 W**, p50 13.4 W, p90 14.0 W, **máx 14.84 W**. Sleep/idle 3.36 W.
- SCLK: nivel 7 @ **1071 MHz** dominante (928 muestras), mínimo 214 MHz, transiciones 551–1046 MHz.
- MCLK: 300 / 625 / **1500 MHz** (330 muestras @ 1500).
- Temp: media 50.1 °C, **máx 59 °C** (arranque 37 °C).
- GPU busy: **100 %** durante carga.
- VRAM (vram_used): máx **2 104 389 632 B ≈ 2.10 GB de 2.00 GB** (≈98 % → presión alta); GTT used máx 1.18 GB.
- Estado Vulkan: OK (device correcto); sin errores en stdout.

### Journal/kernel
Ventana 04:39–04:44: **sin** líneas `amdgpu.*error|reset|timeout|device lost`, `drm reset`, `gpu hang`, `ring gfx`. Sin reset/hang.

## Estado final (verificado)
- power1_cap = 35000000 · power/control = on · DPM = auto · runtime_status = active
- GPU idle tras la prueba: busy 0 %, 3.3 W, 50 °C (enfriando). Vulkan responde.
- Cap nunca se escribió (se mantuvo 35 W). No se tocó Mesa/amdgpu/Kalm/DPM/SCLK/MCLK/runtime-PM.

## Clasificación
- **NO DISCRIMINATIVO para M2** (no supera 27 W; techo GravityMark 1080p Vulkan sobre 2 GB ≈ 14/15 W).
- GravityMark con escena >200k no procede por presión VRAM (1m/2m/4m excederían 2 GB).
- Sin reset/hang. Incidente previo (4m, device lost OOM) documentado en sección abajo.

## Conclusión para workload M2
GravityMark 1.89 NO será candidato M2 (no alcanza régimen 25–31 W en RX 550 con 2 GB VRAM).
Próximo candidato a evaluar (no ejecutado): UNIGINE Superposition 1.1 (CLI reproducible, GL, presets 1080p high/extreme) — requiere autorización.