# EP-08 — Auditoría de la fuente de telemetría E1/E3 (read-only)

## Método
- Buscar runner E1/E3 en backup: NO presente (no hay .sh con 'tele-' en el backup; críticos borrados).
  Se auditó por evidencia indirecta del sistema y de los archivos.

## Evidencia
1. header E1: `ts,busy,freq_hz,power_uw,temp_mc,vram_used,gtt_used`.
2. `mem_info_vram_used` y `mem_info_gtt_used` (y `mem_info_preempt_used`) existen SOLO en amdgpu card1
   (/sys/class/drm/card1/device/mem_info_*). En card0 (i915) NO hay mem_info_* ni hwmon.
3. Por lo tanto las lecturas E1/E3 (freq 298-1029MHz, power ~25W, temp 75-79C, vram/gtt) provienen de la
   RX 550 (amdgpu), NO de la iGPU.

## Conclusión
- O1-b ("E1/E3 muestrearon la tarjeta equivocada") = **REFUTADA**. Los datos E1/E3 son de la RX 550 real.
- El régimen E1/E3 es un ESTADO REAL de la tarjeta: cada run entra YA caliente (temp 76C en la primera
  muestra), el SCLK NUNCA boostea (523 -> ~365 MHz estable), power clavada en 25W (cap) todo el run.
- Ejemplo (vk-phong r1, 64 muestras / 15s): busy 87-100%, freq 362-384MHz (pico inicial 523), power 25.0W
  constante, temp 76C constante. NO hay fase de boost dentro del run.

## Estatus
- Mantiene viva la vía "SOAK térmico + cap 25W" (H2-via-soak) como explicación del régimen, PORQUE hoy con
  entrada en frío (Fase B) el cap 25W NO produce throttling (1071MHz/10W).
- Deja una anomalía de linaje pendiente (O3): vk-phong E1 FPS 1285 @ ~365MHz vs hoy 400fps @ 1071MHz (misma
  surface 640x480, mismo benchmark). Imposible físicamente -> sospecha de FPS no originado en la ventana
  muestreada o superficie distinta. Re-medir (EP-07).
