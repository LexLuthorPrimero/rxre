# BENCHMARK-INVENTORY.md — Benchmarks GPU Linux para selección de workload M2

Fecha: 2026-09-20. Estado: **instalación autorizada para la prueba exploratoria M2 completada** (solo extracción en `~/Escritorio/berchmark/instalados/`, sin lanzar benchmarks ni cargar la GPU). La FECHA de estado instalado corresponde a la sesión 2026-09-20; se registró rutas, versiones y CLI de los 4 instaladores. NO se ejecutó ninguna carga sostenida ni comando de modificación de GPU/Mesa/amdgpu.

Contexto experimental de destino:

- **RX 550 Polaris12/GFX8, PCI `1002:699f`, amdgpu** como GPU de render secundaria; **Intel HD 4600 (card0) es la GPU de display**.
- Objetivo M2: encontrar una carga GPU-bound reproducible que lleve el draw real desde **~12.3 W (M1)** hacia **>27 W con cap=35 W**, para que la comparación 35 W vs 30 W sea discriminativa.
- Selección de GPU por proceso (no toca display):
  - OpenGL: `DRI_PRIME=1` (o `1002:699f` / `pci-0000_01_00_0` con guiones bajos) + verificar renderer `radeonsi polaris12`.
  - Vulkan: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` + `MESA_VK_DEVICE_SELECT=1002:699f` + verificar device `AMD Radeon RX 550` / `0x699f`. Sin selector, Vulkan cae en Intel.
- La métrica de éxito es FPS/frametime; potencia es variable explicativa.

**Convención de estado:** [VERIFICADO] disponible/confirmado hoy · [REPRODUCIBLE] comportamiento estable · [OBSERVADO] reportado por fuentes externas · [NO REPRODUCIBLE] histórico no confirmado · [HIPÓTESIS] · [DESCARTADO] · [DESCONOCIDO].

---

## 1. Objetivo del inventario

Seleccionar candidatos de workload reproducible que una fase posterior pueda **instalar con autorización**, ejecutar por terminal, fijar a la RX 550, y medir (FPS/frame time + telemetría del runner) para determinar si la demanda de potencia alcanza el régimen en que el power cap liga (>27 W). También documentar alternativas para caracterizar cuello de botella (BERRETA/Ghost Cache).

## 2. Estado del hardware relevante

- RX 550 `1002:699f` (card1, amdgpu, renderD129): 512 shaders / 8 CU, GDDR5 128-bit, SCLK 214–1071 MHz, MCLK 300/625/1500 MHz, power1_cap default=max=35 W.
- Intel HD 4600 `8086:0412` (card0, i915): display/compositor; NO tiene hwmon ni se usa para benchmark.
- Draw real medido hoy: 9.4–13.6 W; máx 13.6 W @2560×1440 texturizado (EP-06). **Ningún workload disponible ha alcanzado >27 W**.
- Mesa STOCK 26.2.2 (radeonsi/RADV, ACO); Mesa CUSTOM `/opt/mesa-26.2.2-rx550-haswell` presente (== STOCK en las pruebas EP-05).

## 3. M1 como contexto (completado)

- Workload M1: `vkmark -p immediate -s 1920x1080 -b shading:shading=phong:duration=25`.
- Resultado: `media(power1_input@35 W)` = **12.27 W** → compuerta `<27 W` → **NO DISCRIMINATIVO** (cap 30 W no liga). ΔFPS=ΔSCLK=0 pareados.
- Lección: un workload ligero no discrimina el cap; M2 necesita carga sostenida sensiblemente más costosa.

---

## 4. Categorías

- **A. Benchmarks GPU reales:** renderizan escenas 3D con contexto gráfico completo (escena/geometría/shaders). Más cercanos a uso real.
- **B. Stress tests térmicos/gráficos:** cargas extremas sostenidas orientadas a exigir la GPU al máximo (potencia/temperatura).
- **C. Benchmarks sintéticos:** micro-benchmarks de un recurso acotado (ALU, memoria, cómputo).
- **D. Herramientas de diagnóstico:** información/lectura del estado de la GPU (no cargan).
- **E. Suites de benchmarks:** agregan y orquestan múltiples tests (instalan binarios propios).

---

## 5. Candidatos documentados

Formato por candidato (orden fijo):
① Fuente oficial · ② API · ③ Ejecución por terminal · ④ Headless/offscreen · ⑤ Resolución · ⑥ Duración · ⑦ Reproducibilidad · ⑧ Selección de escena · ⑨ Métrica · ⑩ Carga sostenida · ⑪ Probabilidad de acercar RX 550 al límite · ⑫ Compatibilidad Polaris12/RADV/radeonsi · ⑬ Dependencias · ⑭ Disponibilidad Fedora/Nobara 44 · ⑮ Descarga externa · ⑯ Gratuito · ⑰ Riesgo crash/reset · ⑱ Adecuación M2 · ⑲ Comando instalación (referencia) · ⑳ Comando ejecución (referencia).

---

### A. Benchmarks GPU reales

#### A1. vkmark (Vulkan)
① github.com/vkmark (mingw/android/NOT,) → vkmark/vkmark · ② Vulkan (RADV). · ③ `vkmark -b <escena>:<opts>:duration=N -s <WxH> -p immediate` (patrón FPS en stdout). · ④ Soporta `--winsys` xcb/wayland/kms; el runner M1 lo usa con presentación inmediata en sesión gráfica. · ⑤ Cualquier WxH (se probó 640, 1080). · ⑥ Configurable por escena (`duration=`). · ⑦ [REPRODUCIBLE] escenas fijas; es el workload de M1 (CV intra-brazo 1.828 %). · ⑧ `-b shading:shading=phong`, desktop, etc.; `-l/--list-scenes`. · ⑨ FPS (stdout), selectable device. · ⑩ Moderada: `shading` 1080p llega a ~12.3 W; insuficiente para M2. · ⑪ BAJA (demuestra M1). · ⑫ Sí (RADV POLARIS12 OK). · ⑬ Vulkan loader + mesa-vulkan-drivers. · ⑭ **Sí (`vkmark` en repos Fedora/Nobara)**. · ⑮ No. · ⑯ Sí (LGPL). · ⑰ Bajo. · ⑱ PUNTO DE REFERENCIA, no candidato >27 W. · ⑲ `sudo dnf install vkmark` (REFERENCIA). · ⑳ `VK_ICD_FILENAMES=... MESA_VK_DEVICE_SELECT=1002:699f vkmark -p immediate -s 1920x1080 -b shading:shading=phong:duration=25` (REFERENCIA).

#### A2. glmark2 (GL)
① github.com/glmark2/glmark2. · ② OpenGL. · ③ `glmark2 -s <WxH> -b <escena>:duration=N`; patrón FPS en stdout. · ④ `--off-screen`, `--run-forever`, `-l/--list-scenes`, `-f/--benchmark-file`. · ⑤ Configurable. · ⑥ `:duration=` por escena. · ⑦ [REPRODUCIBLE] escenas fijas (jellyfish/desktop/conditionals…). · ⑧ `-b` por escena + `--validate`. · ⑨ FPS; `--results fps,cpu,shader`; `--results-file`. · ⑩ Ligera–moderada (jelly 640p 1228–1250 FPS a ~10.8 W; no SCLK-bound). · ⑪ BAJA. · ⑫ Sí (radeonsi). · ⑬ mesa GL + glx. · ⑭ **Sí (`glmark2`)**. · ⑮ No. · ⑯ Sí (GPLv3). · ⑰ Bajo. · ⑱ Bajo para M2 (bottleneck no shader). · ⑲ `sudo dnf install glmark2` (REFERENCIA). · ⑳ `DRI_PRIME=1002:699f glmark2 -s 1920x1080 -b jellyfish:duration=25 -b build:duration=25` (REFERENCIA).

#### A3. GravityMark (Vulkan/OpenGL) — INSTALADO `instalados/GravityMark_1.89`
① gravitymark.tellusim.com (autor). · ② Vulkan y OpenGL (escena delegada a la GPU, evita cuello CPU). · ③ **[VERIFICADO] CLI completa** en los `run_*.sh` (binario `bin/GravityMark.x64`; sin `--help`, `-h` imprime build). · ④ Ventana/manual automatizable; paraderos `-benchmark 0/1 -close 0/1 -count <N> -times <file>`. · ⑤ `-width W -height H -fullscreen 0/1 -fulldesktop 0/1 -mode <name>`. · ⑥ `-benchmark 1 -count <N>` (pasadas) y `-close 1` cierra al finalizar; frame times con `-times <file>`. · ⑦ [HIPÓTESIS] repetibilidad escena 100% GPU declarada; frame-time exportable. · ⑧ Presets/parámetros por línea de comando (asteroids/lod/raster/meshlet/raytracing). · ⑨ FPS (+`-fps 1 -sensors 1`) y frame time (`-times`). · ⑩ Potencialmente ALTA (delegación total a GPU). · ⑪ **ALTA**. · ⑫ Sí (RADV/radeonsi via `-vk`/`-opengl`). · ⑬ Vulkan/GL libs; instalador. · ⑭ **No** (no en repos). · ⑮ DESCARGADO (`~/Escritorio/berchmark/GravityMark_1.89.run`, sha256 `de090c7b…2e005`) e INSTALADO. · ⑯ Freeware (propietario), EULA Evaluation aceptada al instalar (click-through). · ⑰ Moderado. · ⑱ **CANDIDATO PRIORITARIO M2**. · ⑲ `sh GravityMark_1.89.run --nox11 --noexec --keep --target <instalados>/GravityMark_1.89` (ejecutado; aceptar EULA con `y`). · ⑳ `VK_ICD_FILENAMES=... MESA_VK_DEVICE_SELECT=1002:699f <instalados>/GravityMark_1.89/bin/GravityMark.x64 -vk -benchmark 1 -count N -close 1 -width 1920 -height 1080 -fullscreen 1 -device <idx> -times out.times` (CONFIRMAR device al ejecutar).

#### A4. UNIGINE Heaven 4.0 (GL) — INSTALADO `instalados/Unigine_Heaven-4.0`
① benchmark.unigine.com/heaven. · ② OpenGL (Motor UNIGINE 2.52; libs x64 en `bin/`). · ③ La automatización CLI/CSV corresponde a **ediciones extendidas (Advanced/Pro)**; la versión libre usa launcher `browser_x64`. · ④ Interactiva; CLI limitada en la edición gratis. · ⑤ 640–4K (vía launcher, presets gratis). · ⑥ Preset/clique manual. · ⑦ [HIPÓTESIS] repetible en edición extendida; la libre es interactiva. · ⑧ Presets gratis. · ⑨ FPS/score en pantalla + HTML. · ⑩ Media–alta. · ⑪ MEDIA. · ⑫ Sí (OpenGL sobre radeonsi). · ⑬ Instalador propietario. · ⑭ **No**. · ⑮ DESCARGADO (`Unigine_Heaven-4.0.run`) e INSTALADO. · ⑯ Freeware propietario. · ⑰ Moderado. · ⑱ Bajo–medio como CLI (ed. gratis interactiva); útil como carga exploratoria con launcher. · ⑲ `sh Unigine_Heaven-4.0.run --accept --nox11 --noexec --keep --target <instalados>/Unigine_Heaven-4.0` (ejecutado). · ⑳ `DRI_PRIME=1002:699f <instalados>/Unigine_Heaven-4.0/heaven` (launcher GUI; REFERENCIA).

#### A5. UNIGINE Valley 1.0 (GL) — INSTALADO `instalados/Unigine_Valley-1.0`
Igual estructura que Heaven (motor UNIGINE 2.52; `valley` → `browser_x64`), CLI/CSV solo edición Pro. DESCARGADO (`Unigine_Valley-1.0.run`) e INSTALADO en `instalados/Unigine_Valley-1.0`. Ejecución: `DRI_PRIME=1002:699f <instalados>/Unigine_Valley-1.0/valley` (REFERENCIA).

#### A6. UNIGINE Superposition (GL) — INSTALADO `instalados/Unigine_Superposition-1.1` (**CORRECCIÓN: NO DESCARTADO**)
① benchmark.unigine.com/superposition. · ② OpenGL (y DirectX 11 en Windows; en Linux `-api opengl`). · ③ **[VERIFICADO]** CLI robusta y documentada en el User Manual del instalador: `bin/superposition_cli` con `-api`, `-resolution [WxH]`, `-fullscreen [0/1/2]`, `-quality [low/medium/high/extreme/4K_Optimized/8K_Optimized]`, `-textures`, `-dof`, `-motion_blur`, `-sound`, `-mode [default/frame/scene]`, `-mode_duration [min]`, `-iterations [0..99999]`, `-log_csv "file.csv"`, `-log_csv_step [float]`, `-log_txt "file.txt"`, `-xml "routine.xml"`; también `-preset N -batch 1` en cadenas internas. → **La afirmación previa «edición gratis sin CLI reproducible» era INCORRECTA**. · ④ Sí (CLI; `-mode default` sin interacción final; `-log_csv/-log_txt` generan reportes). · ⑤ `-resolution WxH` explícito. · ⑥ `-iterations N` + `-mode_duration` (minutos) + `-log_csv_step`. · ⑦ [HIPÓTESIS] alta (pases e iteraciones deterministas; CSV por frame). · ⑧ Quality presets completos. · ⑨ FPS/score en `-log_txt` (stats generales) + CSV per-frame (`-log_csv`). · ⑩ MUY ALTA (SSRTGI, shader-heavy). · ⑪ **ALTA** (uno de los más exigentes). · ⑫ Sí (GL sobre radeonsi; verificar device con `DRI_PRIME`). · ⑬ Instalador 1.64 GB. · ⑭ **No**. · ⑮ DESCARGADO (`Unigine_Superposition-1.1.run`, sha256 `7494e1…0f8`) e INSTALADO (`version` file = `1.1`). · ⑯ Freeware propietario. · ⑰ Moderado. · ⑱ **CANDIDATO M2 con CLI totalmente reproducible** (reemplaza la clasificación previa). · ⑲ `sh Unigine_Superposition-1.1.run --accept --nox11 --noexec --keep --target <instalados>/Unigine_Superposition-1.1` (ejecutado). · ⑳ `DRI_PRIME=1002:699f <instalados>/Unigine_Superposition-1.1/bin/superposition_cli -api opengl -resolution 1920x1080 -quality high -mode default -iterations 3 -sound 0 -fullscreen 0 -log_csv <out>.csv -log_txt <out>.txt` (REFERENCIA; verificar device).

#### A7. GravityMark 1.89 — ver A3 (candidato prioritario).

#### A8. Juegos con modo benchmark/autostart (Workloads reales)
① fuentes oficiales de cada título. · ② GL/Vulkan según juego. · ③ Replay/autostart por CLI (SuperTuxKart `--benchmark`, 0 A.D. `--autostart`+mapas demo, Xonotic, vkQuake timedemo, OpenArena). · ④ Requieren sesión gráfica (compositor activo). · ⑤ Configurable. · ⑥ Per replay/demo fija. · ⑦ [HIPÓTESIS] alta si el replay es determinista; el framerate depende de la carga del mapa. · ⑧ Mapas/mods fijos. · ⑨ FPS/timedemo. · ⑩ MEDIA-ALTA según escena/población. · ⑪ MEDIA-ALTA (escenas densas de SuperTuxKart salto-through / 0 A.D. megafights). · ⑫ Sí (GL/VK sobre Mesa). · ⑬ Paquetes juego. · ⑭ **Sí** (`supertuxkart`, `0ad`, `xonotic`, `vkquake`, `openarena` en Fedora). · ⑮ No. · ⑯ Sí (GPL/FLOSS). · ⑰ Bajo-moderado. · ⑱ MEDIO (probar como backup a GravityMark). · ⑲ `sudo dnf install supertuxtkart 0ad` (REFERENCIA). · ⑳ e.g. `DRI_PRIME=1002:699f supertuxkart --benchmark --benchmark-file=<replay>` (REFERENCIA).

### B. Stress tests

#### B1. FurMark 2 (GL y Vulkan, Geeks3D) — sucesor del GpuTest/FurMark investigado
① geeks3d.com/furmark (oficial). · ② OpenGL y Vulkan (GeeXLab). · ③ CLI robusta y documentada: `furmark --p1080 --benchmark --duration-ms N --max-time S`, `--vsync`, `--gpu-index`, `--no-score-box`, `--log-gpu-data`. · ④ Ventana/presentación; útil interactivo. · ⑤ Presets 1080/1440/2160/3440. · ⑥ `--duration-ms`/`--max-time`/`--max-frames`. · ⑦ [HIPÓTESIS] alta (demos repetibles, benchmark con duration). · ⑧ Presets y demos (`--demo`, `--demolist`). · ⑨ FPS/score; `--print-render-speed`; log CSV de datos. · ⑩ MUY ALTA (es stress test). · ⑪ **MUY ALTA** (>27 W plausible; exige al máximo). · ⑫ Sí. · ⑬ Instalador. · ⑭ **No** (no en repos). · ⑮ Sí; v2.10.2 linux64 (16 MB, 7zip); [HIPÓTESIS] no se bajó en esta fase por ser instalador propietario a revisar. · ⑯ Freeware propietario. · ⑰ **ALTO** (stress): riesgo de reset térmico; reportes de crashes de kernel en GpuTest histórico; el runner aborta ≥90 °C. · ⑱ **CANDIDATO PRIORITARIO** para M2 (mayor poder de carga), con control de duración y cooldown. · ⑲ descarga manual geeks3d.com/furmark/downloads + extraer (REFERENCIA). · ⑳ `furmark --p1080 --benchmark --duration-ms 30000 --no-score-box` (REFERENCIA; probar selección RX550 con `--gpu-index`/env VK).

#### B2. stress-ng --gpu (GL/EGL)
① github.com/ColinIanKing/stress-ng. · ② EGL/GBM (GPU compute/texture). · ③ `stress-ng --gpu N --gpu-frag --gpu-tex-size --gpu-upload --gpu-xsize --gpu-ysize --gpu-ops N`; devnode con `--gpu-devnode`. · ④ OFFSCREEN nativo (sin display) → no molesta al compositor. · ⑤ Interna. · ⑥ `--timeout`. · ⑦ [HIPÓTESIS] determinista por ops/timeout. · ⑧ Opciones internas. · ⑨ Ops/s, exit rc. · ⑩ ALTA (tensor/textura continua). · ⑪ ALTA-MEDIA. · ⑫ Necesita verificación de selección de device via EGL/GBM (DRI_PRIME). · ⑬ Mesa EGL. · ⑭ **Sí (`stress-ng`)**. · ⑮ No. · ⑯ Sí (GPLv2). · ⑰ Moderado. · ⑱ MEDIO (offscreen puede simplificar pruebas; requiere validar device). · ⑲ `sudo dnf install stress-ng` (REFERENCIA). · ⑳ `DRI_PRIME=1002:699f stress-ng --gpu 1 --gpu-frag --gpu-tex-size 4096 --timeout 30s --metrics-brief` (REFERENCIA).

### C. Benchmarks sintéticos

#### C1. clpeak (OpenCL/Vulkan)
① github.com/krrishnarraj/clpeak. · ② OpenCL (+ Vulkan opcional). · ③ `clpeak --all-tests` / `--global-bandwidth`, `--compute-sp`, `--transfer-bandwidth`, `-p`, `-d`. · ④ Sí (sin ventana). · ⑤ N/A. · ⑥ Por test. · ⑦ Alta (mediciones repetibles). · ⑧ Flags. · ⑨ GFLOPS/GB/s. · ⑩ ALTA en compute/copias, acotada en tiempo. · ⑪ ALTA (cómputo sostenido); depende de ruta OpenCL en RX 550 (clover/rusticl en Mesa). · ⑫ Necesita verificación (`clinfo` + selection device). · ⑬ mesa OpenCL/Vulkan. · ⑭ **Sí (`clpeak`, `clinfo`)**. · ⑮ No. · ⑯ Sí (Apache-2.0). · ⑰ Bajo. · ⑱ MEDIO (buena para caracterizar cómputo BERRETA; menor para "juego"). · ⑲ `sudo dnf install clpeak clinfo` (REFERENCIA). · ⑳ `clpeak --all-tests --global-bandwidth` (REFERENCIA; verificar device = RX 550).

#### C2. vkpeak (Vulkan compute, nihui)
① github.com/nihui/vkpeak. · ② Vulkan compute. · ③ `vkpeak <device_id> [escenario]`; device 0 por defecto (requiere devolver el índice de la RX 550 tras el ICD forzado). · ④ Sí (headless). · ⑤ N/A. · ⑥ Por escenario. · ⑦ Alta. · ⑧ Escenarios fp32/fp16/int8/matrix/copy-d2d etc. · ⑨ GFLOPS/GIOPS. · ⑩ ALTA en cómputo. · ⑪ ALTA-MEDIA. · ⑫ Sí. · ⑬ Vulkan. · ⑭ **No** (build/desde fuente; no paquete). · ⑮ Sí (releases GitHub); NO descargado. · ⑯ Sí (BSD/MIT). · ⑰ Bajo. · ⑱ MEDIO (caracterizar cómputo; HEADLESS). · ⑲ build desde fuente (`cmake`…; REFERENCIA). · ⑳ `VK_ICD_FILENAMES=... MESA_VK_DEVICE_SELECT=1002:699f ./vkpeak 0 all` (REFERENCIA).

#### C3. glmark2 scenes pesadas — ver A2.
#### C4. SuperTuxKart — ver A8 (workload real con benchmark).

### D. Herramientas de diagnóstico (no cargan; útiles para verificar selección/estado)

- `clinfo`: lista devices OpenCL y plataformas de la RX 550. Numero de device que luego elegir clpeak.
- `vulkaninfo`/`vulkaninfo --summary`: verifica device Vulkan (debe aparecer `AMD Radeon RX 550 ... RADV POLARIS12` tras forzar ICD; NO asumir que sin selector elija la RX 550).
- `glxinfo -B` + `DRI_PRIME=1002:699f`: renderer GL real de la RX 550 (`radeonsi polaris12`).
- `radeontop` / `amdgpu_top`: bus% en vivo de gfx/compute/sdma/vcn (útil para BERRETA y Ghost Cache: separar Gfx vs ACE/SDMA utilización).
- `igt-gpu-tools` (`igt_gpu_tools`, tools AMD también) y `gpu-top`: complemento de monitoreo [HIPÓTESIS; no revisar en repos].
- Sysfs del runner (read-only): `gpu_busy_percent`, `mem_busy_percent`, `freq1_input/freq2_input`, `power1_input`, `mem_info_vram_used/gtt_used`.
- Todos disponible en Fedora/Nobara (`clinfo`, `vulkan-tools`, `glx-utils`, `radeontop`, `amdgpu_top`). NO son candidatos de carga M2.

### E. Suites

#### E1. Phoronix Test Suite (PTS)
① phoronix-test-suite.com. · ② Multi-API (GL/VK/OpenCL/compute). · ③ `phoronix-test-suite benchmark <test>`; tests gráficos: `glmark2`, `gputest` (GpuTest), `vkpeak`, `unigine-heaven/sanctuary/superposition/tropics/valley`, `IndigoBench`; suites `desktop-graphics`, `unigine`. · ④ No headless por diseño (abren ventanas). · ⑤ Configurable por test. · ⑥ Por test. · ⑦ Alta (instala y ejecuta múltiples veces). · ⑧ Tests/presets de PTS. · ⑨ Score/resultados en `~/.phoronix-test-suite`. · ⑩ Depende del test (superposition = muy alta). · ⑪ ALTA (puede orquestar superposition/vkpeak). · ⑫ Sí. · ⑬ python + php/mejoras; descarga binarios de tests al ejecutar. · ⑭ **Sí (`phoronix-test-suite`)**. · ⑮ Vía PTS al ejecutar (requiere instalación de paquetes de test con PTS). · ⑯ Libre/propietario según test. · ⑰ Moderado (instala jerarquía local). · ⑱ MEDIO (orquestador; no reemplaza el runner propio). · ⑲ `sudo dnf install phoronix-test-suite` (REFERENCIA). · ⑳ `phoronix-test-suite benchmark unigine-superposition` (REFERENCIA).

---

## 6. Disponibilidad global (síntesis de la investigación)

| Fuente | Benchmarks que los contienen |
|---|---|
| **Repos Fedora/Nobara 44** [VERIFICADO por repoquery] | `vkmark`, `glmark2`, `phoronix-test-suite`, `stress-ng`, `clpeak`, `clinfo`, `vulkan-tools`, `glx-utils`, `supertuxkart`, `0ad`, `xonotic`, `vkquake`, `openarena`, `blender`, `hashcat`, `radeontop`, `amdgpu_top`, `igt-gpu-tools`, `f3d`, `teeworlds` |
| **Descarga externa** (instalados 2026-09-20 en `~/Escritorio/berchmark/instalados/`) | **GravityMark 1.89** ✅, **UNIGINE Heaven 4.0** ✅, **UNIGINE Valley 1.0** ✅, **UNIGINE Superposition 1.1** ✅ (originales `.run` intactos en `~/Escritorio/berchmark/`); FurMark 2 (NO bajado; revisar), vkpeak (source) |
| **No en repos / no verificado** | `gputest`, `unigine-*` (ya instalado), `gravitymark` (ya instalado), `vkpeak`, `basemark`, `gpu-burn`, `nexuiz`, `warfork`, `amber` |
| **Descartado con evidencia** | — (Superposition REINSTAURADO por CLI verificada en `superposition_cli`) |

## 7. Requisitos/licencias

- **GravityMark**: freeware propietario; instalador `.run`; revisar licencia antes de ejecutar.
- **FurMark 2**: freeware propietario; revisar licencia; instalador.
- **UNIGINE**: freeware propietario (edición Benchmark gratuita); revisar licencia.
- **vkmark/glmark2/stress-ng/clpeak** etc.: libres (LGPL/GPL/BSD/Apache), instalables con `dnf`.
- **Phoronix Test Suite**: libre; descarga tests de terceros al ejecutar (atención a binarios descargados).

## 8. Riesgo asociado (alto → bajo)

FurMark 2 > SuperTuxKart/0 A.D. escenas densas > GravityMark > stress-ng --gpu > UNIGINE > vkmark/glmark2/clpeak/vkpeak (bajo). El runner aborta ≥90 °C y detecta reset/hang por `journalctl`; display siempre en Intel (red de seguridad).

## 9. Reproducibilidad estimada

- **Alta (determinista/cli):** vkmark (M1 real), glmark2, GravityMark (declarado), FurMark 2 (duration), clpeak/vkpeak, stress-ng.
- **Media:** PTS; juegos con replay/demo (dependen del mapa y de la CPU).
- **Baja:** ediciones UNIGINE gratuitas (interactivas).

## 10. Capacidad potencial de generar >27 W (estimación, [HIPÓTESIS])

| Candidato | API | Potencial de carga |
|---|---|---|
| FurMark 2 (`--p1080 --duration-ms`) | GL/VK | **Muy alto** (diseñado para stress) |
| UNIGINE Superposition (ed. extendida) | GL/VK | Muy alto (descartado por ed. gratis) |
| GravityMark preset alto | VK/GL | **Alto** (escena 100% GPU) |
| stress-ng --gpu pesado | EGL/GBM | Alto |
| clpeak / vkpeak cómputo | CL/VK | Alto (acotado) |
| Juegos densos (STK/0 A.D./Xonotic) | GL/VK | Medio-alto |
| vkmark/phong, glmark2 | VK/GL | Bajo (M1: 12.3 W) |

Ningún valor >27 W está [VERIFICADO] aún; requiere la prueba exploratoria.

## 11. Selección explícita de la RX 550 (resumen práctico)

- **GL (juegos/glmark2/SuperTuxKart/0 A.D.):** `DRI_PRIME=1002:699f` (o `DRI_PRIME=1`) antes del comando; verificar renderer con `glxinfo -B`.
- **Vulkan (GravityMark/FurMark VK/vkmark):** `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` + `MESA_VK_DEVICE_SELECT=1002:699f`; verificar con `vulkaninfo --summary` y, de ser posible, `--gpu-index`/device id.
- **EGL/GBM (stress-ng):** `DRI_PRIME=1` + `--gpu-devnode` apuntando al render node de la RX 550.
- **OpenCL (clpeak):** seleccionar el device de clpeak correspondiente a la RX 550 tras `clinfo`.

---

## 12. Tabla final

| Benchmark | API | Instalación | Terminal | Carga GPU potencial | Reproducibilidad | Duración configurable | Selección RX 550 | Riesgo | Utilidad M2 |
|---|---|---|---|---|---|---|---|---|---|
| FurMark 2 | GL/VK | externa (Geeks3D) | sí (CLI preset+duration) | Muy alta | Alta (duration) | sí (`--duration-ms`) | `--gpu-index`/env VK | Alto (stress) | **ALTA** |
| GravityMark 1.89 | VK/GL | externa (**descargado**) | sí (CLI declarada) | Alta | Alta (declarada) | preset/CLI | env VK + verificar | Moderado | **ALTA** |
| SuperTuxKart | GL | dnf | sí (`--benchmark`) | Media-alta | Media (replay) | replay fijo | DRI_PRIME | Bajo-mod. | Media |
| 0 A.D. | GL/VK | dnf | sí (`--autostart`+demo) | Media-alta | Media (mapa) | demo fijo | DRI_PRIME | Bajo-mod. | Media |
| stress-ng --gpu | EGL | dnf | sí (offheadless) | Alta | Alta (timeout) | sí (`--timeout`) | DRI_PRIME+devnode | Moderado | Media |
| clpeak | CL/VK | dnf | sí (headless) | Alta (acotada) | Alta | por test | device id (clinfo) | Bajo | Media |
| vkpeak | VK | source | sí (headless) | Alta (acotada) | Alta | por escenario | env VK+id | Bajo | Media |
| UNIGINE Heaven/Valley | GL | externa (**instalados 2026-09-20**) | limitada (ed. gratis) | Media-alta | Media | preset | DRI_PRIME | Moderado | Baja |
| UNIGINE Superposition | GL | externa (**instalado 1.1**) | **sí (CLI `superposition_cli` + XML/CSV)** | Muy alta | Alta (HIERRO) | `-iterations/-mode_duration` | DRI_PRIME | Moderado | **ALTA (reinstalado)** |
| vkmark (phong 1080p) | VK | dnf | sí | Baja (12.3 W) | Alta (M1) | sí | env VK IC | Bajo | **Referencia M1** |
| glmark2 | GL | dnf | sí | Baja-med | Alta | sí | DRI_PRIME | Bajo | Baja |
| PTS (suite) | multi | dnf | sí | Varía (≥ alta) | Media-alta | por test | por test | Moderado | Media |

---

## 12b. Registro de instalación autorizada (2026-09-20) — sin ejecutar cargas

Los 4 instaladores permanecen **intactos** en `~/Escritorio/berchmark/` (SHA256 re-verificados: `de090c…e005`, `52db2e…e397`, `2fb47a…f7ef`, `7494e…f80f`). Extracción con makeself `--nox11 --noexec --keep --target` (sin lanzar post-install y sin escribir fuera de `instalados/`). No se ejecutó ningún benchmark de carga; solo ayudas `-help/-h` y verificación binaria.

| Benchmark | Ruta instalada | Versión verif. | Binario principal | `--help`/ayuda | Método de ejecución (REFERENCIA aún, sin carga) |
|---|---|---|---|---|---|
| **GravityMark 1.89** | `~/Escritorio/berchmark/instalados/GravityMark_1.89/` | `Build Version: 1.89`, `version=20250429; linux; x64; release; vk=1; gl=45; gles=32; cu=1; fusion` | `bin/GravityMark.x64` (ELF) | Sin `--help`/`-h` (imprime build); CLI documentada en `run_*.sh` | `cd instalados/GravityMark_1.89/bin && VK_ICD_FILENAMES=... MESA_VK_DEVICE_SELECT=1002:699f ./GravityMark.x64 -vk -benchmark 1 -count N -close 1 -fullscreen 1 -width W -height H -device <idx> -times out.times` |
| **UNIGINE Superposition 1.1** | `~/Escritorio/berchmark/instalados/Unigine_Superposition-1.1/` | file `version` = `1.1` | `bin/superposition_cli` (CLI), `bin/superposition`, `bin/launcher` (GUI) | Documentada en `docs/Superposition_Benchmark_User_Manual.pdf` (sección Command Line Parameters) | `cd instalados/Unigine_Superposition-1.1/bin && DRI_PRIME=1002:699f ./superposition_cli -api opengl -resolution WxH -quality <low/medium/high/extreme/4K_Optimized/8K_Optimized> -mode default -iterations N -sound 0 -fullscreen 0 -log_csv out.csv -log_txt out.txt` (XML: `-xml routine.xml`) |
| **UNIGINE Heaven 4.0** | `~/Escritorio/berchmark/instalados/Unigine_Heaven-4.0/` | file `data/heaven-version` = `4.0` | `bin/heaven_x64` (engine core), `bin/browser_x64` (launcher) | Manual `documentation/User_Manual.pdf`; CLI/automatización solo ediciones extendidas | `cd instalados/Unigine_Heaven-4.0 && DRI_PRIME=1002:699f ./heaven` (launcher GUI; REFERENCIA) |
| **UNIGINE Valley 1.0** | `~/Escritorio/berchmark/instalados/Unigine_Valley-1.0/` | file `data/valley-version` = `1.0` | `bin/valley_x64`, `bin/browser_x64` | Manual `documentation/User_Manual.pdf`; automatización solo ediciones extendidas | `cd instalados/Unigine_Valley-1.0 && DRI_PRIME=1002:699f ./valley` (launcher GUI; REFERENCIA) |

**Resultado exploratorio Superposition 1.1 (2026-09-20): NO supera 27 W en config por defecto (ejecuta OK).** El motor `superposition` (con `-console_command world_load`) corre y da score 804, pero con preset por defecto **1600x900/Medium/OpenGL** (el `superposition_cli` traduce `-quality/-resolution` a XML pero requiere `~/.Superposition/license` y sale rc=0 sin ejecutar). Potencia fase activa: media 18.8 W, **máx 23.7 W < 27 W**; VRAM 1.63 GiB sin presión; sin reset/hang; estado final OK. Por criterio D: no se auto-incrementó la carga → **pendiente de autorización** para preset mayor (1080p/high) si se desea. Detalle: `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md`.

**Resultado de la prueba exploratoria GravityMark (2026-09-20): NO DISCRIMINATIVO para M2.** Intento 1: `-asteroids 4m` → device lost/OOM (2.86 GB > 2 GB), incidente de ejecución, sin medición (detalle abajo). Intento 2 (200k, 1080p Vulkan): carga válida (busy 100 %, temp máx 59 °C, sclk 1071 MHz) pero **potencia media 12.4 W / máx 14.8 W — claramente <27 W**; además **presión de VRAM 2.10 GB/2.00 GB** → por regla no se probó 1m. GravityMark descartado como candidato M2 (techo real ~15 W sobre RX 550 2 GB). Estado final OK: cap 35 W, sin reset/hang. Detalle en `experiments/EXPLORATORIO-GravityMark/runs/RESULTADO.md`.

Notas de la instalación:
- **Superposition: NO se ejecuta el postinstall** (`postinstall.sh` escribía `Superposition.desktop`, iconos y `~/.local/share/...`, y borraba archivos del target). El `--noexec` de makeself lo impidió, dejando todo el contenido en `instalados/`. `version`=1.1 (que el postinstall habría borrado) quedó intacto.
- **GravityMark: EULA Evaluation** se aceptó durante la instalación (respuesta `y`, equivalía al "I AGREE" del lanzador). Al ejecutar `--help` el binario compiló su diálogo GTK en `~/.tellusim/dialogs_*` (efecto colateral del binario, no del instalador; NO se modificó Mesa/amdgpu/kalm).
- **Selección RX 550 verificada por documento (no por benchmark corrido):** Vulkan → `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` + `MESA_VK_DEVICE_SELECT=1002:699f` + `-device <idx>` en GravityMark; OpenGL → `DRI_PRIME=1002:699f` (o `=1`). Confirmar el device/renderer en el reporte de cada herramienta antes de confiar.
- **Duración:** GravityMark `-count N` + `-close 1`; Superposition `-iterations N` y `-mode_duration N` (min); Heaven/Valley ed. gratis = duración/lazo manual (necesitarían timeout externo si se usaran).
- **FPS/resultados:** GravityMark `-times <file>` (frame times) y `-fps 1`; Superposition `-log_csv` (per-frame) y `-log_txt` (score); Heaven/Valley score en pantalla (+HTML en la ed. ext.).

---

## 13. CANDIDATOS PRIORITARIOS PARA M2

La prioridad responde únicamente a: **"¿Qué candidato tiene mayor utilidad experimental para producir una carga GPU reproducible que pueda llevar la RX 550 desde ~12.3 W hacia >27 W con cap=35 W, permitiendo luego comparar 35 W vs 30 W?"**. No es ranking de rendimiento.

### 1. FurMark 2 (Geeks3D, GL y Vulkan)
- **Por qué podría superar a M1:** es un stress test de propósito general con presets (1080p/1440p) y duración exacta (`--duration-ms`), pensado para llevar la GPU al límite térmico/potencia; mucho más costoso que `vkmark shading:phong` (12.3 W).
- **API:** Vulkan o OpenGL (GeeXLab); elegir Vulkan con ICD RADV para el camino ya validado del runner.
- **Cómo fijar RX 550:** Vulkan → `VK_ICD_FILENAMES=... + MESA_VK_DEVICE_SELECT=1002:699f`, y si `--gpu-index` lo soporta, fijar el índice; verificar device en reporte. OpenGL → `DRI_PRIME=1`.
- **Carga reproducible:** preset fijo + `--duration-ms 25000` + `--no-score-box`; benchmark termina al tiempo y devuelve el shell (CLI documentada por Geeks3D).
- **Métrica:** FPS/score del stderr/stdout de FurMark; el runner ya parsea `FPS:` y agrega telemetría sysfs.
- **Riesgos:** ALTO (stress) → usar cooldown ≤45 °C, duración acotada, aborto ≥90 °C del runner, detector 7d de reset/hang; revisar licencia antes de instalar; reportes históricos de inestabilidad del kernel con el FurMark/GpuTest legado → valorar más la variante Vulkan moderna.
- **Runner actual:** compatible sin cambios de código (el runner solo cambia el workload/duración; requiere sesión gráfica activa). Necesita instalar el binario.

### 2. GravityMark 1.89 (Tellusim)
- **Por qué podría superar a M1:** escena full-GPU (sin cuello de CPU), compleja y con presets; la doc oficial destaca CLI/automatización y es exactamente la carga "GPU-bound" que M1 no fue.
- **API:** Vulkan (recomendado) y OpenGL.
- **Cómo fijar RX 550:** Vulkan env VK (ICD+selector) + verificar con el informe del propio tool/`vulkaninfo`.
- **Carga reproducible:** preset alto + parámetros/presets de automatización (confirmar `--help` tras instalación), duración/presets deterministas.
- **Métrica:** FPS/score de salida; runner parsea y añade telemetría.
- **Riesgos:** moderados (instalador propietario .run, licencia; bajo riesgo de reset).
- **Runner actual:** compatible; **ya está descargado** (`official-downloads/gravitymark/`, sha256 registrado) → es el camino más corto a una prueba exploratoria (solo falta instalación autorizada + licencia).

### 3. UNIGINE Superposition 1.1 (GL; **REINSTALADO** tras corrección de la CLI)
- **Por qué:** su `bin/superposition_cli` tiene CLI robusta y documentada (User Manual del propio instalador): `-api opengl`, `-resolution WxH`, `-quality low/medium/high/extreme/4K_Optimized/8K_Optimized`, `-mode default/frame/scene`, `-mode_duration Nmin`, `-iterations N`, `-log_csv file.csv` (per-frame), `-log_txt file.txt` (score/stats), `-xml routine.xml` (pases). La afirmación previa «ed. gratis sin CLI reproducible» quedó **invalidada por verificación directa** (strings + pdf manual).
- **API:** OpenGL (`-api opengl`) en Linux. Para la RX 550: `DRI_PRIME=1002:699f`.
- **Cómo fijar RX 550:** `DRI_PRIME=1002:699f` (GL) + verificar device en el reporte.
- **Carga reproducible:** `superposition_cli -api opengl -resolution 1920x1080 -quality <pq> -mode default -iterations N -sound 0 -fullscreen 0 -log_csv <out>.csv -log_txt <out>.txt`; duración acotada por `-iterations`/`-mode_duration`.
- **Métrica:** CSV per-frame (FPS/frametime) + TXT con score → parselable por el runner sin cambios.
- **Riesgos:** moderados (instalador propietario, heavy shaders con SSRTGI); runner aborta ≥90 °C.
- **Runner actual:** compatible; el runner solo cambia el workload/duración.

### 4. Phoronix Test Suite (como salvaguarda de carga extrema)
- **Por qué:** puede orquestar `unigine-heaven/superposition` y `vkpeak` con fotografía de resultados; utilidad para comparación independiente.
- **API:** multi. **Riesgo:** instala repositorios/binarios de tests al correr; requiere revisión y es más "caja negra" que el runner propio.
- **Runner actual:** se ejecuta aparte; el runner mide igualmente por sysfs si el workload corre en la misma sesión.

### Candidatos secundarios (backup, sin prioridad)
- SuperTuxKart `--benchmark` (veneno extra MNITS): carga media-alta con replay determinista; requiere `DRI_PRIME`.
- stress-ng `--gpu` pesado: offscreen (no compite con el compositor), pero validar en el devnode correcto.
- clpeak/vkpeak: buena caracterización de cómputo para las capas BERRETA/Ghost Cache (cómputo sostenido), no del perfil "3D".

### No apto / descartado
- vkmark/glmark2 en configuraciones de referencia (ya demostrado <27 W).

> **No se selecciona todavía el workload definitivo de M2.** Queda como **candidato a prueba exploratoria posterior**: medir draw/FPS/temp/resets de cada prioritario con cap=35 W, y solo el que alcance ≥27 W repetible será la carga de M2.

## 14. Lo que debe verificarse antes de usar un candidato (prueba exploratoria)

1. Instalación autorizada + aceptación de licencia (GravityMark obligatorio; FurMark 2 obligatorio).
2. `./rx550-torneo status --json`: GPU correcta (`1002:699f`), display en Intel, cap=35 W, DPM auto.
3. Workload con la selección de RX 550 correcta (ver §11) y renderer/device verificado en el reporte.
4. Dry-run del runner (read-only) antes de cualquier corrida con writes.
5. Métrica de ventana estable (mismo esquema M1: [5 s, 25 s]); térmico dentro de rango; sin reset/hang en `journalctl`.
6. decidido tras los datos: si draw <27 W → descartar y pasar al siguiente candidato.

---

Fuentes: sitios oficiales consultados en la sesión (Geeks3D/FurMark 2, Tellusim/GravityMark, UNIGINE, Phoronix, stress-ng, vkmark, glmark2, clpeak, vkpeak, 0 A.D./SuperTuxKart) + `dnf5 repoquery --available` (Fedora/Nobara 44) + experiencia local (`rx550-torneo`, M1, EP-05/EP-06). Donde un dato no pudo confirmarse está marcado [HIPÓTESIS]/"confirmar al instalar".