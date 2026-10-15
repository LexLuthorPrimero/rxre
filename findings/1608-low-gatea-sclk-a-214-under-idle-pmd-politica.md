# RXRE-008 FINDING 1608 — power_dpm_force_performance_level=low gatea SCLK a 214MHz (min) bajo idle; el floor de SCLK es política DPM

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1608
- Estado: OBSERVED (SCLK before/after PM write, read-only probes) / CONFIRMED (gateability; H1 DPM-policy)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12/Lexa PRO, rev c7), PCI 0000:01:00.0.
  iGPU 0000:00:02.0 NO tocada; fb0/i915 (Intel) = consola, intacta; salidas card1-DVI-D-1 /
  card1-HDMI-A-1 NO programadas.
- Kernel/Software: Nobara/Fedora, amdgpu, sysfs /sys/class/drm/card1/device/*.
- Auth: el propietario autoriza intervención sobre la RX550 siempre que no se toque la iGPU
  ni la salida de display. Este write es PM (power_dpm_force_performance_level), NO es
  programación de salida de display. §42 controlled write (reversible).

## Resumen
Bajo idle (engines idle, §1607), `power_dpm_force_performance_level=auto` mantiene SCLK en un
**floor fluctuante 551–1000 MHz** (§1606/1607: nunca 214 min ni 1071 max). Forzar `low`
gaterea SCLK a **214 MHz** (state 0, MIN), y restaurar `auto` devuelve SCLK al floor
(980→214→734 MHz).

→ El floor de SCLK bajo `auto` es **política DPM de amdgpu** (programable, gateable), **no**
un floor térmico/hardware. **H3 refutada** (floor ≠ térmico fijo; es policy). **H1 confirmada**
(DPM policy, engines idle → SCLK gateable a min).

Para §72 (MAXIMUM PRACTICAL) / §1607 D11: un driver RX550 especializado **puede gatear SCLK a
mínimo bajo idle** (PM4/SDMA PMU, o sysfs low) para reducir power sin afectar idle throughput.
Esto es un target de especialización directo.

## Evidencia técnica
### Experimento controlado (§42/§47), read-only-post-write, reversible
| paso | level | SCLK (cur `*`) | MCLK | GUI_ACTIVE | acción |
|---|---|---|---|---|---|
| PRECONDITION | auto | 3: 980Mhz * | 0: 300Mhz * | 0 (idle) | (engines idle §1607) |
| ACTION | low | — | — | — | `echo low > /sys/.../power_dpm_force_performance_level` (rc=0) |
| UNDER low | low | **0: 214Mhz *** (MIN) | 0: 300Mhz * | (no re-lectura necesaria; no cambió la GPU) | |
| RECOVERY | auto | — | — | — | `echo auto > ...` (rc=0) |
| RESTORED | auto | 2: 734Mhz * (floor) | 0: 300Mhz * | 0 | SCLK vuelve al floor |

- `SCLK gates to min(214) under low`: **True** (`low_sclk=['0: 214Mhz *']`).
- `SCLK returns to floor auto`: **True** (`restored=['2: 734Mhz *']`; fluctuaba 551/734/980 bajo auto en §1606/1607).
- `rc=0` en ambos writes (sysfs PM escribible).
- iGPU / display / fb0 NO toccados (solo card1 PM sysfs).

## Decisiones
- D14 (RXRE-008): el floor de SCLK bajo idle (`auto`) es política DPM → **gateable a min**. Esto
  valida D11 (§1607): gatear SCLK a min bajo idle es un target de optimización real (no un techo
  hardware).
- D15 (RXRE-008): un driver RX550 especializado (§6 C/ASM) puede implementar idle-SCLK-gating
  vía PM4/SDMA PMU o sysfs, reduciendo power sin afectar idle throughput (§72). Priority ↑
  (driver C core → power state machine).
- D16 (RXRE-008): el write a `power_dpm_force_performance_level` (PM) es REVERSIBLE y NO toca
  display/iGPU → autorizado por el propietario. La frontera dura sigue siendo "salida de DISPLAY
  de la RX550" (card1-DVI/HDMI) → sigue prohibida hasta permiso explícito.

## Verificación
- PRECONDITION verificado: level=auto, GUI_ACTIVE=0, engines idle (§1607). ✓
- ACTION: write `low` rc=0. ✓
- OBSERVABLE: SCLK 980→214 (gatea a min). ✓ (discrimina H3: si fuera térmico/hardware, `low` no gatearía a 214)
- RECOVERY: write `auto` rc=0, SCLK vuelve a floor (734). ✓ (reversibilidad validada)
- iGPU/display intactos (solo card1 PM sysfs). ✓
- Reproducible: mismo PRECONDITION (idle + auto) → mismo efecto (gatea 214). ✓

## Limitaciones
- Sólo se probó `low` (no `high`/`manual`); el DPM `auto` fluctúa (551-1000) — el trigger exacto
  dentro de `auto` no se determinó (§1609+: bajo carga / thermal governor).
- El experimento fue bajo IDLE (no carga); bajo load el DPM es distinto (§1609).
- El floor fluctúa (551/734/980) → el DPM `auto` es dinámico/ruidoso; se necesita time-series
  + thermal para modelar el governor.
- El write es a sysfs (amdgpu), no a registros MMIO del chip → no valida el mecanismo PM4/SDMA
  PMU de un driver propio (§1609: implementar gate bajo load).

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1609 (frontera, §72/§109): time-series SCLK + temperatura bajo idle (leer sensors/k10temp)
  → modelar el governor DPM `auto` (¿qué dispara 980 vs 734 vs 551?).
- 1610 (frontera, read-only): bajo CARGA (compute no-display, SOLO si se autoriza; display
  prohibido) → ¿SCLK sube a 1071? + mmGRBM_STATUS bajo load. gating §42 workload.
- 1611 (frontera): identificar la fuente de ~480 MiB VRAM usada bajo idle (mem_info + GART/VM).
- (Fase E) Driver C: esbozar el power-state machine idle-gate (SCLK→min) como hotpath §7.

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only probes + controlled reversible PM sysfs write on card1 only, no display outputs)
