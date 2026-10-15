# RXRE-008 FINDING 1606 — RX550 idle: estado lógico vs PM eléctrico (SCLK no clock-gated)

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1606
- Estado: OBSERVED (8 samples, idle, read-only) / HYPOTHESIS (interpretación DPM)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12/Lexa PRO, rev c7), PCI 0000:01:00.0. iGPU 0000:00:02.0 NO tocada.
- Kernel/Software: Nobara/Fedora, amdgpu (DRIVER=amdgpu), sysfs /sys/class/drm/card1/device/{pp_dpm_sclk,pp_dpm_mclk,mem_info_vram_used} + umr 1.0.0 -O bits.
- Tool provenance: 8× `op:run gpu.register_read mmGRBM_STATUS decode=True` (umr -O bits) + `cat`/sys pp_dpm*/mem_info (read-only), 1 s de separación, RXRE_DB=/tmp/rxre_ts2.sqlite3 (durable, root, aislada).
- Relación: extiende §1604 (layout) → §1605 (idle sostenido mmGRBM) → 1606 (decoupling clock-power/lógico).

## Resumen
Durante 8 samples bajo idle, `mmGRBM_STATUS=0x00003028` (logico idle: `GUI_ACTIVE=0`,
todos BUSY=0) se mantiene 8/8, `MCLK=300MHz` (mínimo, VRAM idle) es constante y
`mem_info_vram_used=504549376` (~480 MiB) es constante. SIN EMBARGO **SCLK fluctúa entre
551, 734 y 1000 MHz** (DPM states 1/2/4), nunca alcanzando el mínimo (214 MHz) ni el máximo
(1071 MHz), con `power_dpm_force_performance_level=auto`.

→ La RX550 está **lógicamente idle pero no clock-gated**. El PM de amdgpu mantiene un
piso de SCLK (responsabilidad/responsiveness) bajo idle; el estado lógico (mmGRBM) y el
estado PM eléctrico (SCLK) están **acoplados débilmente**. Para §72 (MAXIMUM PRACTICAL):
bajo idle, el techo práctico incluye un floor de SCLK (no se gatea a mínimo).

## Evidencia técnica
### Serie temporal correlacionada (8 samples, 1 s, idle, read-only)
| sample | mmGRBM_STATUS | SRBM_RQ_PENDING | GUI_ACTIVE | SCLK (cur) | MCLK (cur) | VRAM_used |
|---|---|---|---|---|---|---|
| 1 | 0x00003028 | 1 | 0 | 4:1000MHz * | 0:300MHz * | 504549376 |
| 2 | 0x00003028 | 1 | 0 | 2:734MHz *  | 0:300MHz * | 504549376 |
| 3 | 0x00003028 | 1 | 0 | 2:734MHz *  | 0:300MHz * | 504549376 |
| 4 | 0x00003028 | 1 | 0 | 4:1000MHz * | 0:300MHz * | 504549376 |
| 5 | 0x00003028 | 1 | 0 | 2:734MHz *  | 0:300MHz * | 504549376 |
| 6 | 0x00003028 | 1 | 0 | 4:1000MHz * | 0:300MHz * | 504549376 |
| 7 | 0x00003028 | 1 | 0 | 2:734MHz *  | 0:300MHz * | 504549376 |
| 8 | 0x00003028 | 1 | 0 | 1:551MHz *  | 0:300MHz * | 504549376 |

- `mmGRBM distinct: ['0x00003028']` → idle lógico sostenido (8/8). [§1605 refuerzo]
- `SCLK distinct: [551, 734, 1000]` → 3 estados distintos en 8 samples; nunca 214 (min) ni 1071 (max).
- `MCLK distinct: [300]` → VRAM en mínimo (idle) estable.
- `VRAM_used: 504549376 (~480 MiB)` constante → algo lo reserva (ver §1607).

### Lectura (§9 EPISTEMIC KERNEL)
- OBSERVED: mmGRBM=0x3028 (idle), MCLK=300 (VRAM idle), SCLK fluctúa 551-1000 (no gate).
- HYPOTHESIS: amdgpu DPM `auto` impone un piso de SCLK bajo idle (responsabilidad térmica de
  subida); no se gatea a 214 MHz. (No se observó un job/submission que eleve SCLK.)
- La contradicción aparente (idle + SCLK activo) se RESOLVE como: los contadores de ocupación
  (mmGRBM) reportan idle lógico, pero el PM de bloque (SCLK) no se gatea → decouple.

## Decisiones
- D8 (RXRE-008): para caracterizar idle de la RX550, NO basta mmGRBM_STATUS; hay que leer
  SCLK/MCLK (sysfs pp_dpm_*) + VRAM. El idle "lógico" ≠ idle "eléctrico".
- D9 (RXRE-008): `power_dpm_force_performance_level=auto` (+SCLK fluctuate ≠ min) sugiere
  que un perfil `low`/manual o `battery` podría gatear SCLK a min bajo idle (cambio de PM
  → requiere write a sysfs `device/power_dpm_force_performance_level`; gating §42: controlled
  write, reversible; NO display; autoriza RX550). Frontera para validar.
- D10 (RXRE-008): el decoupling invalida asumir "GPU idle → SCLK mínimo" (§72 NO OVER-RESEARCH:
  no maximizar watts/clock a ciegas; medir).

## Verificación
- mmGRBM=0x3028 8/8 (idle lógico estable). ✓
- SCLK 3 estados distintos (551/734/1000) → no clock-gated a mínimo. ✓ (descarta
  H: "SCLK=constante en mínimo bajo idle").
- MCLK=300 8/8 (VRAM idle). ✓
- VRAM_used constante 504549376 (idle + algo mantiene ~480 MiB; ver §1607). ✓
- No se escribió a display (card1-DVI-D-1/HDMI-A-1) ni a iGPU. ✓ (read-only).

## Limitaciones
- No se determinó QUÉ mantiene SCLK activo (firmware DPM vs actividad oculta de GC/SDMA/CP).
  → §1607: sondear rings/SDMA/CP + contadores de jobs bajo idle.
- ~480 MiB VRAM usada bajo idle: fuente no identificada (driver vs proceso vs firmware).
  → §1607+: sondear BO/mem_info + /sys/device/mem_info o umr GART/VM.
- Un workload de carga (compute no-display) no se ejecutó (display prohibido; gating §42).

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1607 (frontera): leer rings/SDMA/CP + contadores de jobs (umr -O PM4/CP/SDMA) bajo idle →
  discriminar H1(DPM heuristic, SDMA/CP idle) vs H2(actividad oculta eleva SCLK). §17 PM4→CP→RINGS→SDMA.
- 1608 (frontera): identificar la fuente de 480 MiB VRAM bajo idle (MC/VRAM, §17).
- (Opcional, gating §42 reversible): probar `power_dpm_force_performance_level=low` bajo idle
  → ¿SCLK gatea a 214? (requiere write sysfs; display prohibido; iGPU intacta).
- (Fase E) README L139 staleness + machine.py docstring L12 (dice 5 ops, reales 10).

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only probes + read-only sysfs)
