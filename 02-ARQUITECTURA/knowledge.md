# Knowledge (RX 550) — CIERRE 2026-09-19
Conocimiento válido que queda como base de la especificación. Solo afirmaciones reforzadas por lo
reproducible. Los históricos no reproducibles viven en `rejected/RESULTADOS` y se marcan [NO REPRODUCIBLE].

## Identidad y sistema [VERIFICADO]
- RX 550 = Polaris12/GFX8, PCI `1002:699f`, driver amdgpu; SCLK 214-1071 (8 DPM), MCLK 300-1500 (3 DPM),
  power1_cap default=max=35 W. Kernel 7.2.4-201.nobara.fc44, DRM 3.64.
- Display = Intel HD 4600 (card0, i915, HDMI-A-1 connected, fb0). RX 550 (card1) sin conectores activos.
  Decisión de seguridad: la RX 550 NUNCA debe ser la GPU de pantalla durante experimentación.
- GL por defecto del sistema = Intel; para la RX 550 usar `DRI_PRIME=1` (GL) y forzar ICD RADV (VK).
- Vulkan SIN selector → iGPU Intel 0x412 [VERIFICADO]; `MESA_VK_DEVICE_SELECT=1002:699f` roto (elige 0x412).
  Forzar con `VK_ICD_FILENAMES` (=radeon ICD stock o custom) y verificar device 0x699F.
- kalm real = `kalmd.py` (PID 4087) + `kalm-lite.py` (PID 4086), activos desde 18/09 y logueando a journal.
  `kalm-gpu.service` (systemd) dead desde 18/09 14:34. NO tocar kalm. kalm no explica la diferencia 17/09 vs 19/09.

## Comportamiento reproducible hoy [REPRODUCIBLE]
- En las escenas actuales el draw real es 9.4-13.6 W y el cap (25-35 W) NO liga. Máximo medido: 13.6 W
  (2560×1440 texturizado, EP-06).
- DPM auto en carga: SCLK 1071 MHz, MCLK 625 MHz (picos transitorios 1500), temp 42-58 °C en runs cortos,
  plateau soak 64 °C, máx hoy 67 °C.
- FPS base (Mesa stock/CUSTOM indistinguibles, DPM auto, cap 35 W): GL jelly 640p 1228-1250; VK phong 640p
  396-413; VK shading(640) 403-413; jelly 1080p 202-204; desktop 1080p 199-202; shading 1080p 73.
- GL jellyfish 640p es ~insensible al SCLK (340-1071 MHz → 1035-1250 fps): bottleneck no-SCLK [VERIFICADO,
  causa exacta = HIPÓTESIS CPU-side].
- power1_input es un ESTIMADOR SMU; hoy reporta valores reales < cap (no plano).

## Mesa [VERIFICADO]
- STOCK: Mesa 26.2.2, libs `/usr/lib64/libgallium-26.2.2.so`, `/usr/lib64/libvulkan_radeon.so`.
- CUSTOM: `/opt/mesa-26.2.2-rx550-haswell` (git-3281a69a8b), libs en su `lib64/`.
- Distinción fiable: path de `libgallium`/`libvulkan_radeon` en `/proc/<pid>/maps` del proceso benchmark
  (+ renderer string de glxinfo). EP-05: CUSTOM y STOCK idénticos en las condiciones controladas.

## Operacional (hygiene de experimentos)
- `power1_cap` se escribe solo con sudo, siempre con snapshot+readback+trap de restauración (35 W).
- Precondición de experimentos con writes: verificación previa de display Intel, proceso único (flock),
  cooldown, y restauración verificada al final. Ver FINAL-RESEARCH-STATUS y BUILD_SPEC.

## Histórico (NO reproducido; NO usar como especificación)
- E1/E3/E5 (17/09): 25 W pin / SCLK ~350-390 / MCLK ~1250-1500 / 74-92 °C / FPS altos (phong 1285).
  Nada de esto se ha reproducido bajo las condiciones actuales autorizadas (Fase B, EP-06, EP-05).
  Causa raíz [DESCONOCIDA]. Tratar como estado de otra sesión. Detalle en `rejected_ideas.md`, otros docs
  y reportes de experimentos.