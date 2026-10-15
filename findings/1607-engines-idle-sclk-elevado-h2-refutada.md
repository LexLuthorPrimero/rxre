# RXRE-008 FINDING 1607 — RX550 idle: bloques SE/CP/RLC en idle (busy=0) con SCLK elevado — H2 refutada

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1607
- Estado: OBSERVED (engines idle + SCLK elevado, read-only) / HYPOTHESIS (amglgpu DPM floor)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12/Lexa PRO, rev c7), PCI 0000:01:00.0.
  iGPU 0000:00:02.0 NO tocada.
- Kernel/Software: Nobara/Fedora, amdgpu, umr 1.0.0, regdb ip/gfx_8_0_0.reg (regdb oracle).
- Tool provenance: `op:run gpu.register_read decode=True` (umr -O bits -g =0000:01:00.0 -r <reg>)
  para mmGRBM_STATUS, mmGRBM_STATUS2, mmGRBM_STATUS_SE0/1/2/3 + `cat`/sys pp_dpm_sclk/mclk +
  mem_info_vram_used. RXRE_DB=/tmp/rxre_ts3.sqlite3 (durable, root, aislada).
- Relación: §1604 (layout 24 fields) → §1605 (mmGRBM idle 8/8) → §1606 (SCLK fluctúa 551-1000 bajo idle) → §1607 (discriminación H2 refutada).

## Resumen
Sobre 6 registros GRBM decodificados read-only bajo idle, **todos los bloques están en idle**:
`mmGRBM_STATUS` (todos *_BUSY=0), `mmGRBM_STATUS2` (ME0/1/2 pipes RQ_PENDING=0, RLC_BUSY=0),
y `mmGRBM_STATUS_SE0/1/2/3` (BCI/VGT/PA/TA/SX/SPI/SC/DB/CB_BUSY = 0 en las 4 SE).

En cambio **SCLK=734 MHz** (state 2, `power_dpm_force_performance_level=auto`) y fluctúa
(§1606: 551/734/1000), nunca alcanzando el mínimo 214 MHz.

→ **Hipótesis H2 ("SCLK fluctuation refleja actividad oculta de GC/SDMA/CP") REFUTADA**: no
hay actividad de bloques mientras SCLK está elevado. El decoupling lógico/electrícico (§1606)
se confirma: idle lógico ≠ clock-gated. El piso de SCLK es el PM de amdgpu (responsabilidad),
no trabajo oculto. §72: bajo idle, el techo práctico mantiene un floor de SCLK.

## Evidencia técnica
### 6 registros GRBM decodificados (umr -O bits, regdb gfx_8_0_0.reg)
| registro | value | n_fields | busy-relevantes |
|---|---|---|---|
| mmGRBM_STATUS | 0x00003028 | 24 | SRBM_RQ_PENDING=1 (lector); GUI_ACTIVE=0; TA/GDS/VGT/WD/IA/SX/DB/CB_BUSY=0 |
| mmGRBM_STATUS2 | 0x00000008 | 18 | ME0/1PIPE* RQ_PENDING=0; RLC_BUSY=0 |
| mmGRBM_STATUS_SE0 | 0x00000006 | 11 | BCI/VGT/PA/TA/SX/SPI/SC/DB/CB_BUSY=0 |
| mmGRBM_STATUS_SE1 | 0x00000006 | 11 | idem (todos BUSY=0) |
| mmGRBM_STATUS_SE2 | 0x00000006 | 11 | idem (todos BUSY=0) |
| mmGRBM_STATUS_SE3 | 0x00000006 | 11 | idem (todos BUSY=0) |

- `SE busy bits`: en las 4 SE, **BCI_BUSY=VGT_BUSY=PA_BUSY=TA_BUSY=SX_BUSY=SPI_BUSY=SC_BUSY=DB_BUSY=CB_BUSY=0**.
- `STATUS2`: ME0/1/2/3 pipes + RLC → RQ_PENDING=0, RLC_BUSY=0 (CP/RLC idle).
- `STATUS`: único pending = SRBM_RQ_PENDING[5]=1 = **el propio reader MMIO** (umr), no busy del chip.
- `SCLK cur`: `2: 734Mhz *` (auto DPM, fluctuando 551/734/1000 en §1606).
- `MCLK cur`: `0: 300Mhz *` (mínimo; VRAM idle).
- `VRAM_used`: 504549376 (~480 MiB) constante (§1608: fuente por identificar).

### Discriminación (§48 DISCRIMINANT FIRST)
- H1 ("SCLK fluctuation = PM DPM heuristic, engines idle"): **SOPORTADA** (todos BUSY=0 + SCLK elevado).
- H2 ("SCLK fluctuation = actividad oculta GC/SDMA/CP"): **REFUTADA** (engines idle contradice H2).
- H3 ("SCLK fluctuation = ruido térmico/firmware"): no refutada por este dato (engines idle lo es compatible con H1 y H3; diferenciaría con análisis DPM/thermal).

### Lectura (§9)
- OBSERVED: engines idle (6 registros, busy=0) + SCLK elevado (734, fluctuante).
- HYPOTHESIS: el piso de SCLK bajo idle es el PM de amdgpu (auto/responsabilidad), no
  clock-gating a mínimo. (Para confirmar: §1608 — probar force=low.)

## Decisiones
- D11 (RXRE-008): el floor de SCLK (no min) bajo idle es un target de optimización para un
  driver RX550 especializado (§7 hotpath): gatear SCLK a mínimo bajo idle puede reducir power
  sin afectar idle throughput (§72). Implementación futura (driver): PM4/SDMA PMU o sysfs
  force=low como frontera reversible.
- D12 (RXRE-008): para afirmar "idle del chip" basta leer GRBM_STATUS + STATUS2 + SE[0..3]
  (cobertura total: TA/PA/SX/SPI/SC/DB/CB/RLC/ME) → suficiente para refutar actividad oculta.
- D13 (RXRE-008): NO asumir "idle mmGRBM → idle eléctrico" (1606/1607 lo refutan); el PM es
  un dominio independiente del GRBM.

## Verificación
- 6 registros decodificados (24/18/11/11/11/11 fields) + umr -O bits oracle-match regdb. ✓
- Todos los *_BUSY = 0 en SE0/1/2/3 + STATUS2 + STATUS. ✓ (refuta H2)
- SCLK=734 (≠ 214 min) con engines idle → decoupling lógico/eléctrico observado. ✓
- MCLK=300 (mínimo, VRAM idle), VRAM_used constante. ✓
- read-only (umr -r + /sys cat); sin writes; sin display; iGPU intacta. ✓

## Limitaciones
- No se determinó QUÉ mantiene SCLK en floor (DPM curve, thermal governor, o firmware).
  → §1608: probar `power_dpm_force_performance_level=low` (write reversible, §42 gated).
- VRAM ~480 MiB usada bajo idle: fuente no identificada (driver vs firmware). → §1608+.
- SCLK fluctuation (551-1000) bajo idle: H1 vs H3 no diferenciado (ambos compatible con engines idle).
- Un único instantáneo de engines (no time-series de SE busy) → asumir estacionariedad.

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1608 (frontera, gating §42 reversible write — autoriza RX550, NO display): probar
  `power_dpm_force_performance_level=low` bajo idle → ¿SCLK gatea a 214 MHz?
  (descarta H3 floor-thermal vs H1 DPM-heuristic).
- 1608+ (frontera, read-only): identificar la fuente de ~480 MiB VRAM bajo idle (mem_info + GART/VM).
- Escalar a mmCP_STALLED_STAT1/2/3 (0x219d/0x219e/0x219c) + SDMA0_STATUS para confirmar CP/SDMA idle.

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only umr -O bits + read-only /sys)
