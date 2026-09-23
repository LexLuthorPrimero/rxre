# RESULTADO — Superposition 1.1 exploratorio (workload M2)

Fecha: 2026-09-20 · RX 550 (card1, 0000:01:00.0, 0x699f), cap=35 W (verificado).

## Decisión (criterios del usuario)
La ejecución terminó **correctamente (score 804, sin crash/device lost/reset)** pero la
potencia quedó **por debajo de 27 W** (máx 23.7 W; media de fase activa ~18.8–20.8 W).
Según el criterio **D**: la primera configuración no supera 27 W pero funciona OK →
**reportar y esperar autorización; NO aumento automático a configuras extremas.**

Nota de configuración: por la limitación del CLI (ver abajo), la carga efectiva fue la
configuración por defecto del motor: **1600x900 windowed, calidad Medium**, OpenGL.
No se alcanzó "1080p high" automáticamente.

## Comando exacto (motor `superposition` — correr desde `bin/`)
```
DRI_PRIME=1002:699f DISPLAY=:0 \
./superposition -project_name "Superposition" -video_mode=-1 \
  -console_command "world_load superposition/superposition" -extern_plugin "GPUMonitor" \
  -video_app opengl -quality high -mode default -iterations 1 -sound 0 -fullscreen 0 \
  -resolution 1920x1080 -log_csv <r>.csv -log_txt <r>.txt
```
- Los flags `-quality`/`-resolution` del CLI **NO** se aplican al motor directo (el binario
  `superposition_cli` los traduce vía XML/launcher.cfg, pero requiere `~/.Superposition/license`
  y sale rc=0 sin ejecutar — la edición estándar gratuita no lo concede aislado).
- El motor cargó el mundo `superposition/superposition` y ejecutó el benchmark del sistema
  con su preset por defecto (1600x900, Medium, OpenGL, windowed).

## Ejecución
- 1er-CLI intento: `superposition_cli -quality high …` → rc=0 en ~10 ms, sin ejecutar (busca license).
- Correcciones: motor directo con `-console_command world_load …`. El primer intento (bare) se
  cortó a 30 s durante carga del mundo (solo carga de core). Relanzamientos (bare2, bare3) con
  world_load: carga completa + benchmark.
- **bare3 (válido):** `timeout 400` → el motor imprimió "Benchmark running / Benchmark stopped /
  Benchmark results: 804" y luego fue terminado por SIGTERM del timeout (RC=124) tras completar;
  CSV/TXT no generados porque esos flags solo los interpreta el CLI. Score observable 804.
- stdout/stderr: `runs/Superposition/stdout_bare3.log`.

## Telemetría (10 Hz) — `runs/Superposition/telemetria_bare3.csv` (2939 muestras)
Resolución/render realmente usada (decodificado del paquete de resultados): **OpenGL · 1600x900 ·
Medium · SSRT/SSAO/Parallax/Refraction/Motion blur/DOF enabled**.
- Potencia: **media 13.8 W** (incluye carga del mundo ~5 min); **fase activa (busy>0): media 18.8 W,
  máx 23.7 W**; ventana >15 W: media 20.8 W, máx 23.7 W (~174 s).
- SCLK: 1071 MHz (3170 muestras), también 734/980/551 MHz. MCLK en niveles 300–1500 MHz.
- Temp: no registrada en resumen (max en cola ≈ bajo; idle actual 54 °C tras la prueba).
- VRAM: máx **1.63 GiB** (sin presión; GTT 0.15 GiB).
- GPU busy: 100 % en fase activa.
- Score: **804 puntos** (config por defecto).

## Journal/kernel
Sin `amdgpu.*error|reset|timeout|device lost|hang`, `drm reset`, `ring` en la ventana 04:55–05:02 ni en los últimos 10 min. **Sin reset/hang.**

## Estado final (verificado)
- power1_cap = 35000000 · control = on · DPM = auto · runtime = active · GPU idle (0 %, 3.06 W, 54 °C)
- cap nunca escrito; no se tocaron Mesa/amdgpu/Kalm/DPM/SCLK/MCLK/runtime-PM.

## Clasificación
- Ejecución correcta (score 804, sin incidentes) → [VERIFICADO] en cuanto a "ejecutable sin crash".
- Potencia **< 27 W** (máx 23.7 W) → de momento **NO supera el umbral de M2**.
- Configuración efectiva (1600x900/Medium) inferior a la intencionada (1080p/high) por la
  limitación de licencia del CLI → **pendiente de decisión** si se desea probar presets mayores
  (requiere autorización; no se auto-incrementa).

## Próximo paso propuesto (espera autorización)
- Opción 1: XML routine con `-quality high` + resolución 1080p vía `superposition_cli`, si se
  puede generar `~/.Superposition/license` (el launcher GUI la crea al activar la edición; no se
  ha ejecutado el GUI).
- Opción 2: usar `superposition` motor + flags de ventana del engine (`-video_app opengl`) para
  forzar 1080p/OpenGL y preset mayor (Medium→High/Extreme) si lo permite el system_script.
Ninguna se ejecuta sin autorización.