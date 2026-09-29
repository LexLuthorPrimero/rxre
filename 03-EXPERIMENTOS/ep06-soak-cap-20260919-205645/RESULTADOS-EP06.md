# EP-06 — Soak térmico y réplica del régimen E1/E3 (cap 25 W, caliente)

> **SNAPSHOT HISTÓRICO (reconciliación 2026-09-24):** las cifras de `power1_input`
> se expresan como `W_SMU`/potencia estimada por sensor SMU, no como vatímetro. Este
> informe conserva la corrida y su write histórico; no autoriza repetirlo.

Fecha: 2026-09-19 · GPU: RX 550 Polaris12 (card1, amdgpu) · Display: Intel HD 4600 (card0) — condición de seguridad registrada en `seguridad-display.txt` y respetada.

## Pregunta
¿El régimen E1/E3 (SCLK ~330-390 MHz, power1≈cap 25 W, 75-79 °C) se reproduce con cap 25 W **desde caliente** y con **escenas pesadas**, es decir sin depender del arranque en frío que usó Fase B?

## Método
1. Verificación de seguridad antes de arrancar (card0=i915+HDMI-A-1 connected+fb0, kwin_wayland, GL default=Intel), guardada en `seguridad-display.txt`.
2. **Soak 1 (scenas ligeras, 1080p, cap 35 W)**: suite completa ×7 min → plateau 64 °C, max 12.3 W, SCLK 1071 (datos: `soak-probe-telemetry.csv`).
3. **Soak 2 (escenas pesadas, 2560x1440 texturizado, cap 35 W)**: max 13.6 W, 67 °C (datos: `soak-heavy-telemetry.csv`).
4. **Réplica E1 final (`soak-final.sh`)**: cap 25 W, calentamiento con 1080p pesado hasta T≥72 °C (alcanzado 71 °C), y sin cooldown, 4 corridas a cap 25 W caliente: J/P/D a 640p + J a 1080p.

## Resultados

### Réplica E1 (cap 25 W, T inicial 71 °C, sin cooldown) — medias de ventana
| Corrida | busy % | SCLK (med) | SCLK (min-max) | MCLK med | P wk med (min-max) | T | FPS |
|---|---:|---:|---:|---:|---:|---:|---:|
| E1REP-J-640 | 96 | 1071 | 1009-1071 | 625 | 10.5 (9.3-11.7) | 70 | 1209 |
| E1REP-P-640 | 99 | 1071 | 496-1071 | 300 | 11.5 (4.7-11.6) | 70 | 407 |
| E1REP-D-640 | 99 | 1071 | 604-1071 | 300 | 11.5 (5.4-11.5) | 70 | 395 |
| E1REP-J-1080 | 100 | 1071 | 992-1071 | 625 | 9.6 (8.7-10.0) | 70 | 204 |

**A 25 W de cap y a 70-71 °C la tarjeta sigue en SCLK 1071 MHz y ~10-11.5 W: NO pinza el cap, NO baja los relojes.** El régimen E1/E3 (350-390 MHz / power1≈cap / 74-79 °C) **no se reproduce** ni frío (Fase B), ni caliente, ni con escenas ligeras, ni con escenas pesadas, ni a 640p, ni a 1080p.

### Máximo consumo observable hoy
13.6 W `W_SMU` (2560x1440 texturizado, cap 35 W). **Ninguna escena disponible hace demandar >13.6 W** a la tarjeta. Para llegar a 25 W de `W_SMU` se necesitaría un workload ~2× más pesado (como el que produjo E5: 28-31 W a 1080p con la Mesa CUSTOM + MCLK ~1300).

## Auditoría de diferenciales de estado (kalm / servicio)
- `kalm-gpu.service` (systemd): **enabled, inactive**, murió TERM el 18/09 14:34; ese servicio NUNCA corrió el 17/09 (0 eventos en journal) — día de E1/E3/E5.
- **kalm real: `kalmd.py` (PID 4087) y `kalm-lite.py` (PID 4086), vivos desde el 18/09 y activos HOY** (evento [Kalm] en journal a las 21:19 de hoy). No se tocan.
- Con kalm real activo (18-19/09): régimen **libre** 1071 MHz / ~10 W (sweep, Fase A, B, EP-06).
- Sin ningún kalm (17/09): régimen **regulatorio** E1/E3/E5-baseline (25 W pin / 360 MHz).
- ⇒ **kalm NO es la causa de la diferencia**; de hecho apunta en la dirección opuesta.

## Conclusiones
1. EP-06 cierra el intento de reproducción por **estado térmico/cap**: el régimen E1/E3 no es reproducible bajo las condiciones autorizadas (cap 25 W + escenas actuales + stock Mesa + DPM auto), ni siquiera entrando a 70-71 °C.
2. El "power1≈25 W" de E1/E3 era un **estimado SMU en estado de regulación** (power_target), no una medición física independiente: hoy la `W_SMU` máxima observada es 13.6 W.
3. Los FPS de E1 siguen sin ser coherentes con su propia telemetría (phong 1285 @ 365 MHz vs 407 hoy @ 1071 MHz). **El linaje de datos de E1 es no fiable** (runner sin script, FPS de ventana/superficie ajena).
4. **Diferenciador restante del E5 (única fuente de 25-31 W reales)**: Mesa CUSTOM `/opt/mesa-26.2.2-rx550-haswell` + 1080p, que sostiene MCLK ~1250-1500 y 74-92 °C sostenidos. Está sin testear hoy (nuestros runs usaron Mesa stock). → EP-05 propone replicar la línea E5 a 1080p con esa Mesa para cerrar O5 y explicar el consumo alto.

## Estado final del sistema
- `power1_cap` = **35 000 000** (restaurado; ÚNICO write autorizado, trap de restauración).
- `power_dpm_force_performance_level` = auto; kalm real intacto; display en Intel HD 4600 (card0); sin cambios de DRM/KMS/Mesa/GRUB. Config/backups de kalm en `/etc/kalm/` no modificados.
