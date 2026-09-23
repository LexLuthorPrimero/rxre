# EP-05 — Réplica de la línea E5 a 1080p con Mesa CUSTOM (A/B controlado)

Fecha: 2026-09-19 · GPU: RX 550 Polaris12 (card1, amdgpu), DPM=auto, power1_cap=35 000 000 (nunca escrito)
Display: Intel HD 4600 (card0) — condición autorizada respetada (sin writes sysfs, sin tocar kalm/DRM/Mesa del sistema).

## Objetivo
Determinar si `/opt/mesa-26.2.2-rx550-haswell` (Mesa CUSTOM, la usada el 17/09 en E5) reproduce el régimen de
E5 a 1080p (25-31 W / MCLK ~1250-1500 MHz / SCLK 600-750 / 88-92 °C), frente al régimen actual con Mesa
stock (~10-14 W / MCLK 300-625 / SCLK 1071).

## Метод
- A/B controlado intercalado CUSTOM vs STOCK bajo condiciones idénticas, desde frío (42 °C), N=2 por escena.
- Escenas (línea E5, 1920×1080): A GL desktop, B GL jellyfish, C VK shading. GL: `--fullscreen --reuse-context`
  `-s 1920x1080 -b <scene>:duration=15`; VK: `-p immediate -s 1920x1080 -b shading:duration=15`.
- Env GL CUSTOM: `MESA_CUSTOM LD_LIBRARY_PATH="$CUSTOM/lib64" LIBGL_DRIVERS_PATH="$CUSTOM/lib64/dri" DRI_PRIME=1`.
  Env GL STOCK: `-u` las anteriores + `DRI_PRIME=1`. Env VK CUSTOM: `VK_ICD_FILENAMES=$CUSTOM/share/.../radeon_icd.x86_64.json`;
  VK STOCK: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` (VK sin selector cae en Intel 0x412,
  patrón ya documentado → ambos brazos forzados a radeon).
- Sampler 10 Hz sysfs: gpu_busy_percent, mem_busy_percent, freq1_input, pp_dpm_mclk activo, power1_input,
  temp1_input, mem_info_vram/gtt. Captura de `/proc/$PID/maps` a los 1.5 s para registrar libs cargadas.

## Verificación de carga (registro exigido)
- GL CUSTOM (A-custom): maps → `/opt/mesa-26.2.2-rx550-haswell/lib64/libgallium-26.2.2.so`,
  `/opt/mesa-26.2.2-rx550-haswell/lib64/libGLX_mesa.so.0.0.0`; glxinfo renderer `Mesa 26.2.2 (git-3281a69a8b)`.
- GL STOCK (B-stock): maps → `/usr/lib64/libgallium-26.2.2.so`, `/usr/lib64/libGLX_mesa.so.0.0.0`.
- VK CUSTOM: maps → `/opt/mesa-26.2.2-rx550-haswell/lib64/libvulkan_radeon.so`; device `AMD ... (RADV POLARIS12)` 0x699F.
- VK STOCK: maps → `/usr/lib64/libvulkan_radeon.so`; device idem 0x699F.
⇒ Se ejecutó EXACTAMENTE la Mesa CUSTOM en el brazo CUSTOM y la stock en el brazo STOCK, ambas sobre la RX 550.

## Resultados (mediana ventana, N=2)
| esc | brazo | FPS(med) | busy% | SCLK med | MCLK med (min-max) | P med (min-max) W | T med °C |
|---|---|---:|---:|---:|---:|---:|---:|
| A desktop | CUSTOM | 201.5 | 100 | 1071 | 625 (625-625) | 10.4 (9.7-10.8) | 48-51 |
| A desktop | STOCK  | 199.5 | 100 | 1071 | 625 (625-1500*) | 10.4 (9.6-10.7) | 49-52 |
| B jelly   | CUSTOM | 202.5 | 100 | 1071 | 625 (625-1500*) | 9.4 (8.9-9.9) | 50-53 |
| B jelly   | STOCK  | 201.0 | 100 | 1071 | 625 (625-1500*) | 9.4 (8.8-10.0) | 51-54 |
| C shading | CUSTOM | 73.0  | 100 | 1071 | 625 (625-625) | 11.9 (11.9-12.1) | 52-56 |
| C shading | STOCK  | 73.0  | 100 | 1071 | 625 (625-1500*) | 12.1 (11.3-12.3) | 54-57 |

\* Pico transitorio único a 1500 MHz (sin duración sostenida); la mediana y el piso se mantienen en 625.

## Conclusiones
1. **La Mesa CUSTOM NO reproduce el régimen E5 en arranque frío**: en todos los brazos SCLK=1071, MCLK=625
   sostenido, potencia 9.4-12.2 W, temperaturas 44-58 °C. Nunca 25-31 W ni MCLK ≥1250 mantenido ni 88-92 °C.
2. CUSTOM vs STOCK son indistinguibles (ΔFPS ≤1 %, ΔP ≤0.3 W, mismo SCLK/MCLK). La Mesa CUSTOM no altera el
   régimen térmico/potencia con estos escenarios.
3. **H8 (Mesa CUSTOM = causa del consumo de E5): NO CONFIRMADA para arranque desde frío; se refuta como
   explicación por sí sola.** El estado de E5 (25-31 W / MCLK ~1300 / 74-92 °C) sigue requerir otro ingrediente
   (probablemente el estado térmico previo de aquella sesión y/o un empuje de MCLK que hoy no se dispara con
   escenas ligeras; la card hoy no pasa de 13.6 W — ver EP-06).
4. Se registró además que VK sin selector cae en la iGPU (0x412) incluso con vkmark puro; para VK en este
   sistema hay que forzar por ICD (o device select por nombre), y el A/B aquí forzó radeon en ambos brazos.

## Estado final
Sin writes sysfs (cap/DPM/kalm/DRM intactos). Systema: cap 35 W, DPM auto, kalm real intacto, display Intel.
Runs y telemetría raw en `runs/` (A/B/C × custom/stock × r1-r2).