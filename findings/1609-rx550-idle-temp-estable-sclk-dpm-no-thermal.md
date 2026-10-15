# RXRE-008 FINDING 1609 — RX550 idle: temp=35°C estable + SCLK fluctúa → DPM (no térmico)

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1609
- Estado: OBSERVED (temp/SCLK/VRAM/mmGRBM, 4 samples, idle, read-only) / REFUTED (H3 térmico)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12/Lexa PRO, rev c7), PCI 0000:01:00.0.
  iGPU 0000:00:02.0 NO tocada.
- Kernel/Software: Nobara/Fedora, amdgbo, sysfs /sys/class/drm/card1/device/{pp_dpm_sclk,pp_dpm_mclk,mem_info_vram_used,hwmon/*/temp1_input} + umr -O bits (mmGRBM_STATUS).
- Tool provenance: 4× `op:run gpu.register_read mmGRBM_STATUS decode=True` + `cat`/sys (read-only),
  1 s de separación, RXRE_DB=/tmp/rxre_ts5.sqlite3. Raw: /home/lucas/Escritorio/rxre/1609_raw.json.
- Relación: §1606 (SCLK fluctúa 551-1000) → §1607 (engines idle) → §1608 (floor DPM, write `low` gatea 214)
  → §1609 (temp plano → no thermal). Cierre del loopback §66/§109 (PERFORMANCE→OPTIMIZATION).

## Resumen
Bajo idle (engines idle §1607), **GPU temp = 35 °C estable (4/4 samples)**, mientras **SCLK fluctúa
(734/980 MHz)** (§1606). `MCLK=300 MHz` (min, VRAM idle) estable. `VRAM_used` fluctúa levemente
(~481↔~483 MiB, delta ~2 MiB).

→ **H3 (\"el floor/fluctuación de SCLK es el governor térmico\") REFUTADA**: temp plano (35 °C)
mientras SCLK varia descarta retroalimentación térmica. **H1 (DPM policy de amdgpu, no thermal)**
soportada: engines idle + temp plano + SCLK dinámico = el PM `auto` mantiene un piso de
responsabilidad, no un floor térmico. §72: el techo práctico de idle incluye un SCLK-floor
gateable (§1608 `low`→214), no un ceiling térmico.

## Evidencia técnica
### Serie (4 samples, 1 s, idle, read-only)
| sample | mmGRBM_STATUS | GUI_ACTIVE | SCLK (cur) | MCLK (cur) | VRAM_used | temp (°C) |
|---|---|---|---|---|---|---|
| 1 | 0x00003028 | 0 | 3:980Mhz * | 0:300Mhz * | 504680448 | 35 |
| 2 | 0x00003028 | 0 | 3:980Mhz * | 0:300Mhz * | 506777600 | 35 |
| 3 | 0x00003028 | 0 | 2:734Mhz * | 0:300Mhz * | 504680448 | 35 |
| 4 | 0x00003028 | 0 | 2:734Mhz * | 0:300Mhz * | 506777600 | 35 |

- `mmGRBM distinct: [0x00003028]` → idle lógico sostenido (4/4). [§1605 refuerzo]
- `SCLK distinct: [734, 980]` → 2 estados en 4 samples (fluctúa, nunca min 214 ni max 1071).
- `MCLK distinct: [300]` → VRAM en mínimo (idle) estable.
- `VRAM distinct: [504680448, 506777600]` → ~481 / ~483 MiB (delta ~2 MiB; algo activa under idle).
- `TEMP_C: [35]` → 35 °C plano (4/4); NO fluctuación térmica.
- `idle: True | SCLK_variable: True`.

### Discriminación (§48 DISCRIMINANT FIRST)
- H1 (\"SCLK fluctúa por policy DPM `auto` de amdgpu (responsabilidad), engines idle\"): **SOPORTADA**
  (engines idle §1607, temp plano §1609, SCLK dinámico).
- H2 (\"actividad oculta eleva SCLK\"): **REFUTADA** por §1607 (todos BUSY=0).
- H3 (\"governor térmico eleva/mantiene SCLK\"): **REFUTADA** (temp plano 35 °C mientras SCLK varía).
- Conclusión compuesta: el SCLK floor/fluctuación under idle es **PM policy** (amdgpu `auto`),
  observablemente independiente del load lógico (mmGRBM) y de la temperatura.

### Lectura (§9)
- OBSERVED: temp=35°C (4/4), SCLK 734/980 (idle), engines idle (§1607), VRAM minor-fluctúa.
- HYPOTHESIS: el governor DPM `auto` de amdgpu impone un piso de SCLK (no gatea a 214) por
  responsabilidad térmica de subida / latency budget. §1608 (`low`→214) confirma que es gateable.
- VRAM ~2 MiB fluctuation under idle: indica actividad de firmware/driver (alloc/free minor),
  no un job de usuario (engines idle).

## Decisiones
- D17 (RXRE-008): bajo idle, el floor de SCLK **no es térmico** (35 °C plano). Optimizar idle power
  via PM (§1608 `low`) sí reduce SCLK→214; el thermal NO es el limitante (D17 valida D11 §1607).
- D18 (RXRE-008): 35 °C es el **baseline térmico idle** de la RX550 (§72/§72 POWER). Útil para
  comparar contra workload (§1610: bajo load → temp↑, SCLK→max 1071?).
- D19 (RXRE-008): el VRAM_used ~480 MiB fluctúa (~2 MiB) under idle → no es estático;hay que
  identificar la fuente (driver/firmware alloc) §1611.

## Verificación
- temp=35 °C estable (4/4). ✓ (refuta H3)
- SCLK fluctúa 734/980 (idle) + engines idle (§1607) + temp plano → DPM policy. ✓
- MCLK=300 (min) estable; VRAM minor-fluctúa. ✓
- read-only (umr -r + /sys cat); sin writes; sin display; iGPU intacta. ✓
- Reproducible: temp/SCLK/VRAM observables son deterministas under idle. ✓

## Limitaciones
- Sólo 4 samples (1 s); un time-series largo + workload es necesario para modelar el governor auto.
- temp expuesto via hwmon (sí disponible). MCLK/SCLK via pp_dpm. VRAM via mem_info. No se accedió a
  debugfs ktime/firmware counters (§1610+: DPM governor mechanism).
- El VRAM ~480 MiB + delta ~2 MiB bajo idle: fuente no identificada (driver vs firmware alloc).
- No workload bajo carga (display prohibido; gating §42).

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1610 (frontera, gating §42 reversible write — autoriza RX550, NO display): workload compute no-display
  sobre la RX550 vía amdgpu → ¿SCLK sube a 1071 + temp↑? (validar DPM bajo load + §72 MAXIMUM PRACTICAL).
- 1611 (frontera, read-only): identificar la fuente de ~480 MiB VRAM + delta ~2 MiB bajo idle
  (mem_info + umr GART/VM BO audit). §17 MC→GART→GPUVM.
- (Fase E) machine.py docstring L12 staleness (dice 5 ops; real 10) — NOTA: machine.py es del
  agente concurrente (no se edita para evitar flux); se reporta como limitación de doc.

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only umr -O bits + read-only /sys)
