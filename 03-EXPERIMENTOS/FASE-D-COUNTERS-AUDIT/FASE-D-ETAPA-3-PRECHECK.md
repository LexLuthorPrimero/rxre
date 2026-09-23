# FASE-D-ETAPA-3-PRECHECK.md — Auditoría read-only de instrumentabilidad (contadores programados)

**Fecha:** 2026-09-21
**Autorización:** SOLO LECTURA. Sin `umr -w`, sin escrituras MMIO, sin modificar GPU/sysfs/PowerPlay/Mesa/Kalm/rx550-torneo, sin SPM, sin ejecutar las corridas de Etapa 3.
**Objeto:** Verificar, contra la base de registros UMR local y documentación Mesa (sin tocar hardware), que la instrumentación de la Etapa 3 del plan `FASE-D-ETAPA-3-PLAN.md` es aplicable a la RX 550 Polaris12 (`1002:699f`, Lexa, rev c7), y documentar QUÉ se escribirá y QUÉ se restaurará en una futura fase autorizada.
**Alcance de este PRECHECK:** decide la *instrumentabilidad estática* del hardware, no ejecuta ni programa nada.

> Convención de verificación: **VERIFICADO** = confirmado estáticamente contra `/usr/share/umr/database/ip/…` (fuente autoritativa de offsets UMR) y/o documentación Mesa (`ac_perfcounter.c`, clase cik/GFX8, obtenida por websearch, ver §5 k). **[VERIFICAR]** = no confirmable sin operar la tarjeta (requiere escritura) o sin fuente adicional — se mantiene pendiente, NO se asume.

---

## 1. Estado PRE (solo lectura)

| Parámetro | Valor leído (martes 2026-09-21, session) | Fuente |
|---|---|---|
| Kernel | `7.2.4-201.nobara.fc44.x86_64` | `uname -r` |
| PCI | `0000:01:00.0`, clase VGA, `1002:699f` (Lexa PRO / Polaris12), rev `c7` | `lspci -v -s 01:00.0` |
| Subsystem | `1002:0b04` | lspci |
| Driver | `amdgpu` (no module conflict, no amdgpu=) | lspci |
| Card DRM | card1 (display en Intel HD 4600, card0) | /sys/class/drm |
| Runtime PM | `runtime_status = active`, `control = on` | sysfs |
| DPM | `pp_dpm_sclk: 0..7` (214…1071 MHz), `pp_dpm_mclk: 0..2` (300/625/1500 MHz), estado `auto` | sysfs |
| Clock idle (sanity) | sclk **nivel 0 (214 MHz)**, mclk **nivel 0 (300 MHz)**, `gpu_busy_percent`/`mem_busy_percent` = **0** | sysfs + radeontop |
| Potencia idle | `power1_input` ≈ **3,367,000 µW (3.37 W)**, `power1_cap` = 35,000,000 µW (35 W, no escrito en sesión) | hwmon |
| Temperatura idle | `temp1_input` ≈ 37 000 m°C (37°C) | hwmon |
| PCIe link | `current_link_width = 4`, `current_link_speed = 5.0 GT/s`, max `x8` | sysfs |
| Memoria VRAM | total 2147483648 B (2 GiB), vis 268435456 B (256 MiB) | sysfs |
| VBIOS | `xxx-xxx-xxx` (enmascarado por el firmware) | sysfs |
| Falts y resets | `dmesg_restrict = 1`; **journal accessible** (grupo `systemd-journal`): 0 resets en 24 h; 26 líneas de **VM fault** agrupadas en 06:40–06:41 (sep 20), leídas desde TC1/TC2/TC3, vmid 7, pasid 3624/3626; ninguna en las últimas horas | `journalctl -k` |
| Debugfs DRM | `/sys/kernel/debug/dri/` → Permission denied (sin root en sesión) | `ls` |
| UMR en vivo | **NO posible en esta sesión**: UMR exige root (`[ERROR]: UMR was not invoked as root.`); `sudo` pide contraseña (sin NOPASSWD). Lecturas en vivo delegadas al operador (§Apéndice A). | `umr -i 0 -r …` |
| radeontop sudo-net | **Funciona sin root**: idle = gpu/ee/vgt/ta/sx/sh/spi/sc/pa/db/cb **0.00 %**, VRAM 5.32 MB, mclk 0.300 GHz, sclk 0.214 GHz → dump `/tmp/opencode/rt_idle.csv` | radeontop live |

**Baseline de errores GPU para Etapa 3 (a comparar DURANTE):** únicamente el burst de VM fault del 20 sep 06:40–06:41 (26 líneas kernel, 0 RLC/ring timeouts, 0 resets, sin recovery). Un exceso de faults nuevos sobre este baseline durante una futura corrida debe disparar aborto (§7).

---

## 2. Sanity idle (solo lectura)

- **En vivo esta sesión:** radeontop (sin root) reporta todos los bloques 0 % con sclk/mclk al nivel más bajo; `power1_input` 3.37 W. ✅
- **En vivo histórico en ESTA tarjeta (Etapa 1, root):** `runs/umr-counters-muestras.txt` (leo como síntoma de legibilidad y de estado por defecto):
  - `gfx800.mmGRBM_PERFCOUNTER0_LO/HI` y `_SELECT` = 0x0, de fábrica **sin selección** (PERF_SEL 0).
  - `gfx800.mmGRBM_SE0_PERFCOUNTER_LO/SELECT` = 0x0.
  - `gfx800.mmCPG/CPF/CPC_PERFCOUNTER0_LO` = 0; `CPC_PERFCOUNTER0_SELECT`/`SELECT1` = **0x000fffff** (default poblado).
  - `gmc810.mmGMCON_PERF_MON_*` = 0; `ATC_PERFCOUNTER0_CFG` = 0; `ATC_PERFCOUNTER_LO/HI` = 0; **`ATC_PERFCOUNTER_RSLT_CNTL` = 0x04000000** (estado RESET por defecto → contadores de memoria deshabilitados en reposo).
  - Clocks contadores libres: `RLC_GPU_CLOCK_COUNT_LSB/MSB` avanzando entre muestras (1 Hz) → lectura MMR viva funcional.
- **Interpretación:** la familia de registros objetivo es *legible* con UMR (root) en esta tarjeta; en reposo los contadores están parados/des-seleccionados. El sanity idle read-only de Etapa 3 queda cubierto por: sysfs busy=0 + radeontop 0 % + baseline archival.

---

## 3. Tabla de registros candidatos (existencia/offsets/lectura/selección)

Fuente de offsets: `/usr/share/umr/database/ip/gfx_8_0_0.reg` (gfx800/Gfx8, usado por `polaris12.asic`) y `ip/gmc_8_1_0.reg` (memoria). Formato UMR: `<offset UMR>` = offset de dword MMIO usado por `umr -r/-w "polaris12.gfx800.mmNOMBRE"`. Columna Mesa: equivalencia en notación `R_0xxxxx` (byte = dword ×4) usada por el plan §4.4/etapas previas — **no es un segundo offset físico, es la misma dirección en byte**, ambos son válidos.
Columna "lectura": D = lectura directa del valor (tras selección), W = requiere escritura de control para producir valor, (—) = registro de control.

### 3.1 gfx800 — contadores de bloques (bloques del pipeline GFX)

| Bloque | Registro (UMR) | dword | Mesa (byte) | Campos/bit (VERIFICADOS en .reg) | Lectura | ¿Selección? | ¿Escritura para medir? | Existencia P12 | UMR lee (root) |
|---|---|---|---|---|---|---|---|---|---|
| — | `GRBM_GFX_INDEX` | 0xc200 | R_030800 | INSTANCE_INDEX[0:7], SH_INDEX[8:15], SE_INDEX[16:23], SH/INSTANCE/SE_BROADCAST_WRITES[29-31] | D | control | (índice de instancia/SE) | ✅ | ✅ |
| GRBM | `GRBM_PERFCOUNTER0_LO/HI` | 0xd040/0xd041 | R_034100 | conteo | D | `GRBM_PERFCOUNTER0_SELECT` 0xd840 | SELECT | ✅ | ✅ (archival: LO=0, SEL=0) |
| GRBM | `GRBM_PERFCOUNTER1_LO/HI` | 0xd043/0xd044 | R_03410C | conteo | D | SELECT 0xd841 | SELECT | ✅ | ✅ |
| GRBM | `GRBM_PERFCOUNTER0_SELECT` | 0xd840 | R_036100 | PERF_SEL[0:5] + *BUSY_USER_DEFINED_MASK (DB_CLEAN 10, CB_CLEAN 11, VGT 12, TA 13, SX 14, SPI 16, SC 17, PA 18, GRBM 19, DB 20, CB 21, CP 22, IA 23) | (—) | — | — | ✅ | ✅ |
| GRBM_SE | `GRBM_SE0_PERFCOUNTER_LO/HI` | 0xd045/0xd046 | R_034114 | conteo | D | `_SELECT` 0xd842 | SELECT | ✅ (P12=1 SE) | ✅ |
| GRBM_SE | `GRBM_SE1_PERFCOUNTER_LO/HI` | 0xd047/0xd048 | R_034118 | conteo | D | `_SELECT` 0xd843 | SELECT | ✅ (SE1 inactiva) | ✅ |
| GRBM_SE | `GRBM_SE2_PERFCOUNTER_LO/HI` | 0xd049/0xd04a | R_03411C | conteo | D | `_SELECT` 0xd844 | SELECT | ✅ | ✅ |
| GRBM_SE | `GRBM_SE3_PERFCOUNTER_LO/HI` | 0xd04b/0xd04c | R_034120 | conteo | D | `_SELECT` 0xd845 | SELECT | ✅ | ✅ |
| GRBM_SE | `GRBM_SEn_PERFCOUNTER_SELECT` | 0xd842…0xd845 | R_036108..14 | PERF_SEL[0:5] + user-defined mask (DB_CLEAN 10, CB_CLEAN 11, TA 12, SX 13, SPI 15, SC 16, DB 17, CB 18, VGT 19) | (—) | — | — | ✅ | ✅ |
| SX | `SX_PERFCOUNTER0..3_LO/HI` | 0xd240+2×k / +1 | R_034900+… | conteo | D | `SX_PERFCOUNTER0..3_SELECT` 0xda40…0xda43 | SELECT (+SELECT1 para ctr0/1) | ✅ | ✅ |
| SX | `SX_PERFCOUNTER0_SELECT` | 0xda40 | R_036900 | PERFCOUNTER_SELECT[0:9], PERFCOUNTER_SELECT1[10:19], CNTR_MODE[20:23] | (—) | — | — | ✅ | ✅ |
| SX | `SX_PERFCOUNTER1_SELECT`/`SELECT1` | 0xda41 / 0xda45 | R_036904/8 | PERFCOUNTER_SELECT / +PERF_SEL1 | (—) | — | — | ✅ | ✅ |
| TCC | `TCC_PERFCOUNTER0..3_LO/HI` | 0xd380+2×k / +1 | R_034E00+… | conteo | D (por instancia/slice) | `TCC_PERFCOUNTER0..3_SELECT` 0xdb80…0xdb85 (+SELECT1 en ctr0/1) | SELECT (+instancia) | ✅ | ✅ |
| TCC | `TCC_PERFCOUNTER0_SELECT` | 0xdb80 | R_036E00 | PERF_SEL[0:9], PERF_SEL1[10:19], CNTR_MODE[20:23], PERF_MODE1[24:27], PERF_MODE[28:31] | (—) | — | — | ✅ | ✅ |
| TCC | `TCC_PERFCOUNTER1_SELECT1` | 0xdb83 | R_036E06 | PERF_SEL2, PERF_SEL3, PERF_MODE3, PERF_MODE2 | (—) | — | — | ✅ | ✅ |
| TCA | `TCA_PERFCOUNTER0..3_LO/HI` | 0xd390+2×k / +1 | R_034E40+… | conteo | D (por instancia/slice) | `TCA_PERFCOUNTER0..3_SELECT` 0xdb90…0xdb95 (SELECT1 0xdb91) | SELECT (+instancia) | ✅ | ✅ |
| CB | `CB_PERFCOUNTER0..3_LO/HI` | 0xd406+2×k / +1 | R_034800+… | conteo | D | `CB_PERFCOUNTER0..3_SELECT` 0xdc01…0xdc05 (+SELECT1 0xdc02 en ctr0) | SELECT | ✅ | ✅ |
| CB | `CB_PERFCOUNTER_FILTER` | 0xdc00 | R_037000 | filtro por formato (solo ctr0) | (—) | — | — | ✅ | ✅ |
| DB | `DB_PERFCOUNTER0..3_LO/HI` | 0xd440+2×k / +1 | R_034700+… | conteo | D | `DB_PERFCOUNTER0..3_SELECT` 0xdc40…0xdc46 (+SELECT1 0xdc41/0xdc43 en ctr0/1) | SELECT | ✅ | ✅ |
| SQ | `SQ_PERFCOUNTER0..15_LO/HI` | 0xd1c0+2×k / +1 | R_034400+… | conteo | D | `SQ_PERFCOUNTER0..15_SELECT` 0xd9c0…0xd9cf | SELECT + window-control (§4) | ✅ | ✅ |
| SQ | `SQ_PERFCOUNTER_CTRL` | 0xd9e0 | R_036780 | PS_EN 0, VS_EN 1, GS_EN 2, ES_EN 3, HS_EN 4, LS_EN 5, CS_EN 6, CNTR_RATE 8:12, DISABLE_FLUSH 13 | (—) | — | control de ventana | ✅ | ✅ |
| SQ | `SQ_PERFCOUNTER_CTRL2` | 0xd9e2 | R_036788 | FORCE_EN 0 | (—) | — | control | ✅ | ✅ |
| SQ | `SQ_PERFCOUNTER_MASK` | 0xd9e1 | R_036784 | SH0_MASK 0:15, SH1_MASK 16:31 | (—) | — | control | ✅ | ✅ |
| SPI | `SPI_PERFCOUNTER0..5_LO/HI` | 0xd181+2×k / 0xd180+… | R_034600+… | conteo | D | `SPI_PERFCOUNTER0..5_SELECT` 0xd980…0xd989 (+SELECT1 0xd984…0xd987 en ctr0..3), BINS 0xd98a | SELECT | ✅ | ✅ |
| TA | `TA_PERFCOUNTER0_LO/HI`, `TA_PERFCOUNTER1_LO/HI` | 0xd2c0/0xd2c1, 0xd2c2/0xd2c3 | R_034B00+… | conteo | D (solo con ventana) | `TA_PERFCOUNTER0/1_SELECT` 0xdac0/0xdac2 (+SELECT1 0xdac1 en ctr0) | SELECT + WINDOW (evento CP) | ✅ | ✅ |
| TD | `TD_PERFCOUNTER0..1_LO/HI` | 0xd300+… | R_034C00+… | conteo | D (solo con ventana) | `TD_PERFCOUNTER0/1_SELECT` 0xdb00/0xdb02 (+SELECT1 0xdb01) | SELECT + WINDOW | ✅ | ✅ |
| TCP | `TCP_PERFCOUNTER0..3_LO/HI` | 0xd340+… | R_034D00+… | conteo | D (solo con ventana) | `TCP_PERFCOUNTER0..3_SELECT` 0xdb40…0xdb45 (+SELECT1 0xdb41/0xdb43 en ctr0/1) | SELECT + WINDOW | ✅ | ✅ |
| CP | `CP_PERFMON_CNTL` | 0xd808 | R_036020 | PERFMON_STATE[0:3], SPM_PERFMON_STATE[4:7], PERFMON_ENABLE_MODE[8:9], PERFMON_SAMPLE_ENABLE[10] | (—) | — | arranque de conteo global | ✅ | ✅ |
| CP | `CP_PERFMON_CNTX_CNTL` | 0xa0d8 | — | PERFMON_ENABLE[31] | (—) | — | enable | ✅ | ✅ |
| RLC | `RLC_PERFMON_CNTL` / `RLC_SPM_PERFMON_CNTL` / `RLC_PERFMON_CLK_CNTL` | 0xdcc0/0xdc80/0xdcbf | — | control SPM/clock (SPM NO usado en Etapa 3) | (—) | — | solo si SPM (excluido) | ✅ | ✅ |

Notas sobre la tabla:
- **GRBM_SE: 1 contador POR SE (SE0…SE3)**, no «2 por SE» como sugería una lectura previa del plan §4. Con 1 SE activo en Polaris12, SE1–SE3 están presentes pero sin hardware detrás (selección devuelve 0/inactiva).
- **Contadores de bloques directos (sin shader-window):** GRBM, GRBM_SE, SX, TCC, TCA, CB, DB → el plan §4.4 los clasifica «directos»; VERIFICADO por clasificación Mesa (flags sin SHADER_WINDOWED).
- **Contadores windowed: SQ/SPI (vía `SQ_PERFCOUNTER_CTRL`) y TA/TD/TCP (ventana de shader por evento).** VERIFICADO por clasificación Mesa (flags `SHADER_WINDOWED`) y por presencia del control `SQ_PERFCOUNTER_CTRL`.
- Los LO/HI de SPI figuran invertidos en cierta documentación (HI en dirección par 0xd180…d188, LO en impar 0xd181…d18b): la lectura se hace via UMR por nombre; no es un problema.

### 3.2 gmc810 — contadores de memoria (MECANISMO SNAPSHOT/TRIGGER, no acumuladores simples)

Los contadores de memoria NO son 4 acumuladores por bloque sino: **4 selectores `*_CFG` + un par LO/HI compartido + `*_RSLT_CNTL`** (selección de canal + trigger START/STOP + CLEAR_ALL/ENABLE_ANY/STOP_ON_SATURATE). Para medir k canales hay que (a) escribir CFG0..3 con PERF_SEL y ENABLE, (b) escribir RSLT_CNTL con PERF_COUNTER_SELECT=c y triggers, (c) leer LO/HI por canal.

| Bloque | Registro (UMR) | dword | Campos (VERIFICADOS) | Lectura | ¿Selección? | ¿Escritura? | Existencia P12 | UMR lee |
|---|---|---|---|---|---|---|---|---|
| MC_ARB | `MC_ARB_PERFCOUNTER0..3_CFG` | 0x7bc…0x7bf | PERF_SEL[0:7], PERF_SEL_END[8:15], PERF_MODE[24:27], ENABLE[28], CLEAR[29] | (cfg) | — | CFG | ✅ | ✅ |
| MC_ARB | `MC_ARB_PERFCOUNTER_LO/HI` | 0x7a6 / 0x7ae | conteo del canal seleccionado | D (por canal) | `RSLT_CNTL` | RSLT_CNTL | ✅ | ✅ |
| MC_ARB | `MC_ARB_PERFCOUNTER_RSLT_CNTL` | 0x7d4 | PERF_COUNTER_SELECT[0:3], START_TRIGGER[8:15], STOP_TRIGGER[16:23], ENABLE_ANY 24, CLEAR_ALL 25, STOP_ALL_ON_SATURATE 26 | (—) | — | RSLT_CNTL | ✅ | ✅ |
| MC_ARB | `MC_ARB_PERF_CID` / `MC_ARB_PM_CNTL` | 0x9c6 / 0x9ed | CH0/CH1 + EN, PM_CNTL 21 bits | (—) | — | control | ✅ | ✅ |
| MC_CITF | `MC_CITF_PERFCOUNTER0..3_CFG` | 0x7b0…0x7b3 | PERF_SEL/END/MODE/ENABLE/CLEAR | (cfg) | — | CFG | ✅ | ✅ |
| MC_CITF | `MC_CITF_PERFCOUNTER_LO/HI`, `_RSLT_CNTL` | 0x7a0/0x7a8, 0x7ce | igual estructura que MC_ARB | D (por canal) | RSLT_CNTL | RSLT_CNTL | ✅ | ✅ |
| MC_CITF | `MC_CITF_PERF_MON_CNTL2` / `PERF_MON_RSLT2` | 0x98e / 0x991 | CID[0:7] | (—) | — | control | ✅ | ✅ |
| ATC | `ATC_PERFCOUNTER0..3_CFG` / `_LO` 0x7a7 / `_HI` 0x7af / `_RSLT_CNTL` 0x7d5 | 0x7c8…0x7cb | igual estructura | D | RSLT_CNTL | CFG+RSLT | ✅ | ✅ |
| CHUB_ATC | `CHUB_ATC_PERFCOUNTER0/1_CFG`, `_LO` 0x7d6, `_HI` 0x7d7, `_RSLT_CNTL` 0x7da | 0x7d8/0x7d9 | igual estructura | D | RSLT_CNTL | CFG+RSLT | ✅ | ✅ |
| GMCON | `GMCON_PERF_MON_CNTL0/1`, `_RSLT0/1` | 0xd4a/0xd4b, 0xd4c/0xd4d | contador global GMC | D | CNTL | CNTL | ✅ | ✅ |

Además existen bloques MC_HUB, MC_RPB, MC_VM_L2 y MC_MCBVM/MCDVM; bastan los tres de arriba (ARB/CITF/ATC) para el plan §4.4. Ojo del mecanismo: el artefacto de Etapa 1 leyó `ATC_RSLT_CNTL = 0x04000000` (estado RESET) → por defecto parados, como se espera.

---

## 4. Shader-window para TA/TD/TCP (+ SQ/SPI)

**Mecanismo (VERIFICADO estructural; semántica [VERIFICAR]):**
1. Los contadores TA/TD/TCP (y SQ/SPI con su `SQ_PERFCOUNTER_CTRL`) están clasificados `SHADER_WINDOWED` en la tablas de Mesa (`class_gfx8` del CHIP: cik_TA/cik_TD/cik_TCP flags `SE|INSTANCE_GROUPS|SHADER_WINDOWED`).
2. **Registro de control de la ventana:** `SQ_PERFCOUNTER_CTRL` (0xd9e0, Mesa R_036780) — requisito documentado: escribir `SQ_PERFCOUNTER_CTRL` con `PS_EN..CS_EN` (bits 0–6) para los stages a medir y `CNTR_RATE` (bits 8–12). Complementos: `SQ_PERFCOUNTER_CTRL2.FORCE_EN` (0xd9e2) y `SQ_PERFCOUNTER_MASK` (0xd9e1, SH0/SH1_MASK).
3. **Arranque/parada global del perfmon:** `CP_PERFMON_CNTL.PERFMON_STATE` (0xd808) con valor `V_..._START_COUNTING`; bit `PERFMON_ENABLE_MODE`, `SPM_PERFMON_STATE` (SPM excluido), `PERFMON_SAMPLE_ENABLE`.
4. **Eventos de ventana vía CP:** la apertura/cierre real de la ventana en los windowed se hace con el evento **`PERFCOUNTER_START` / `PERFCOUNTER_STOP`** (tipo `EVENT_TYPE`, index `0`), inyectado como `PKT3_EVENT_WRITE` en la command queue (Ver `si_pc_emit_start` de `ac_perfcounter.c`: escribe CP_PERFMON_CNTL → vole a emitir el evento, `EVENT_TYPE(V_028A90_PERFCOUNTER_START) | EVENT_INDEX(0)`).

**Valores (hardcodeds, no verificables por registro):** la ventana hace que el contador **sume desde el evento START hasta el evento STOP**. `CNTR_RATE` selecciona la cadencia; encodings concretos de `CNTR_RATE` y de `PERF_SEL`/PERFCOUNTER_SELECT (IDs de evento) **NO están en los .reg** → **[VERIFICAR]** contra `ac_perfcounter.c` clase GFX8/VI (ver §5).

**Disponibilidad en P12:** registros y campos existen (VERIFICADO en .reg). El mecanismo es funcional del silicio.

**Qué exige escrituras (y milita contra UMR puro):**
- SELECT/SELECT1 de cada bloque (wxMMIO) → programable.
- `SQ_PERFCOUNTER_CTRL`/CTRL2/MASK (wxMMIO) → programable.
- `CP_PERFMON_CNTL.PERFMON_STATE` (wxMMIO) → programable.
- **Eventos PERFCOUNTER_START/STOP — NO son MMIO: requieren inyecerte en el IB/ring del CP** (PKT3_EVENT_WRITE). Con UMR-`-w` puro NO se puede abrir/cerrar ventana determinísticamente → para TA/TD/TCP el camino medible es: (a) un ejecutor de comandos que emita WRITE_DATA/PKT3_EVENT_WRITE, o (b) la vía Mesa (queries AMD_performance_monitor), o (c) dejar la ventana «abierta por defecto» (todas las stages enabled sin eventos) y medir acumulado desde un arranque de clock — semántica **[VERIFICAR]**.

**Conclusión §4:** los bloques windowed existen y su control MMIO es escribible, pero medirlos correctamente en Etapa 3 requiere la emisión de eventos CP → **BLOQUEADO para UMR-only; viable con un inyector mínimo de paquetes o vía Mesa** (plan §4.3/§5 ya lo anticipaba).

---

## 5. Semántica (confirmada vs documentada)

| Elemento | Estado | Fuente / nota |
|---|---|---|
| Existencias, offsets dword, campos/bit de todos los registros de §3 | **VERIFICADO** | `.reg` locales (fuente UMR) |
| Equivalencia „Mesa R_0xxxxx = dword×4" (§3) | **VERIFICADO** | cruce R_034100↔0xd040, R_036100↔0xd840, R_036B00↔0xdac0, R_034B00↔0xd2c0, R_036780↔0xd9e0, R_034E00↔0xd380, R_036E00↔0xdb80… |
| Clasificación windowed vs directa (flags `SHADER_WINDOWED`) | **VERIFICADO** | tablas cik_* de `ac_perfcounter.c` (websearch/fossies) |
| Mecanismo triggers/snapshot de memoria | **VERIFICADO** | `.reg` gmc810: CFG + LO/HI + RSLT_CNTL (START/STOP/CLEAR/ENABLE_ANY) |
| Contador por instancia/slice (TCC/TCA/TA/TCP) y su selección por `GRBM_GFX_INDEX.INSTANCE_INDEX` | **VERIFICADO** | flag `INSTANCE_GROUPS` + campos de GFX_INDEX; procedimiento exacto de suma global **[VERIFICAR]** |
| IDs de evento numéricos (`PERF_SEL`, `PERFCOUNTER_SELECT`, `CNTR_RATE`, V_028A90_*) | **[VERIFICAR]** | no están en `.reg`; segunda fuente (ac_perfcounter classe hexa del gfx8/VI) pendiente en red (bloqueos fetch) |
| Semántica «contador acumula sin evento START» para bloques no-windowed | **[VERIFICAR]** | requiere experimento (escritura) EN autorización futura |
| Si `CP_PERFMON_CNTL.PERFMON_STATE` basta para que GRBM/SE/SX/CB/DB acumulen | **[VERIFICAR]** | en experimento autorizado |
| Velocidad/validez del snapshot de memoria (debe volcarse con triggers antes de overwrite) | **[VERIFICAR]** | en experimento autorizado |
| Comportamiento de LO/HI en saturación (`STOP_ALL_ON_SATURATE` presente) | **VERIFICADO (campo)** / semántico [VERIFICAR] | .reg gmc810 |

Regla transversal del proyecto respetada: los estados de hipótesis (Q1–Q8 del plan) solo se fijarán APOYADA/DEBILITADA/… al interpretar datos DURANTE una futura corrida autorizada; este PRECHECK no fija ninguna hipótesis.

---

## 6. Restauración (plan snapshot/restore — sin ejecutar)

- **Antes de cualquier escritura futura** se volcará el estado íntegro de los bloques tocados (snapshot read-only): `umr -lr gfx800` + `umr -lr gmc810` + lecturas individuales de los SELECT/CTRL/CFG/RSLT_CNTL/GFX_INDEX y `CP_PERFMON_CNTL` (listado en §3). Archivo de referencia previo ya existe: `runs/umr-counters-muestras.txt`.
- **Restauración** = escribir de vuelta cada valor volcado en orden inverso (SELECT→CTRL→CFG/RSLT_CNTL→GFX_INDEX). Última línea de defensa: reinicio en frío del sistema (restaura absoluta de fábrica del estado perfecto de los contadores, como se ve en el default del artefacto: SELECT=0, LO=0, RSLT_CNTL=0x04000000).
- **Regla reforzada post-auditoría (MASTER):** `power1_cap` nunca debe ser escrito salvo restore del valor leído (35000000 µW) — mantiene el invariante de la infraestructura rx550-torneo.
- **Aborto automático si:** aparece fault/reset inédito (sobre el baseline §1), el contador devuelve valores incoherentes (LOAD). En ese caso: restaurar snapshot, no improvisar, e informar.

---

## 7. Riesgos / criterio de bloqueo (BLOQUEADO, no improvisar)

| # | Bloqueo / riesgo | Tipo | Estado |
|---|---|---|---|
| L1 | Lectura MMIO en vivo con UMR | Prerrequisito ambiental: **exige root**; `sudo` sin NOPASSWD | **BLOQUEADO (ambiental, esta sesión)** — mitigación: evidencia archival + comandos para operador (§Apéndice A). NO falsable sin root. |
| L2 | IDs de evento numéricos (`PERF_SEL` etc.) | Semántica | **[VERIFICAR]** — pendiente de fuente Mesa classe VI |
| L3 | Ventana de shader TA/TD/TCP necesita `PKT3_EVENT_WRITE` en ring del CP | Capability | **BLOQUEADO para UMR -w puro** → extiende a inyector de paquetes o vía Mesa (no es «no implementable», es «no con UMR solo») |
| L4 | Lectura global de contadores por-instance (TCC/TCA) | Procedimiento | **[VERIFICAR]** — requiere manejo de `GRBM_GFX_INDEX.INSTANCE_INDEX` |
| L5 | Debugfs DRM / dmesg del kernel | Acceso | Parcial: journal del usuario OK (baseline faults §1); `dmesg_restrict=1`; debugfs root-only → DURANTE a cargo del operador con root |
| L6 | Arranque de conteo (`CP_PERFMON_CNTL`), semántica snapshot memoria | Semántica | **[VERIFICAR]** — solo falsable escribiendo (futura autorización) |
| L7 | SPM (RLC_SPM_*) | | **EXCLUIDO** por diseño (plan §4); registros solo listados para que NO se toquen |

Criterio transversal: si un punto marcado **[VERIFICAR] o BLOQUEADO** es imprescindible para un objetivo del plan y no se puede resolver, el diseño de Etapa 3 se aborta para ese objetivo en vez de improvisar.

---

## 8. Conclusiones del PRECHECK

1. **Instrumentabilidad estática confirmada:** todos los contadores del plan existen en gfx800/gmc810 de Polaris12, son legibles por UMR (root, evidencia archival) y sus offsets quedan fijados en §3 (dword UMR = bytes Mesa/4).
2. **Directos sin ventana (medibles con SELECT + CP_PERFMON_CNTL):** GRBM (2), GRBM_SE (1/SE; P12 usa SE0), SX (4), TCC (4 por-instance), TCA (4 por-instance), CB (4), DB (4), SQ (16, windowed-vía-CTRL), SPI (6).
3. **Windowed por evento (TA/TD/TCP):** mecanismo y registro de control confirmados; su medición correcta requiere emisión de eventos CP → **vía extendida** (inyector de paquetes o Mesa), no UMR puro. Se mantiene en diseño §4 como «vía Mesa».
4. **Memoria (MC_ARB/CITF/ATC/CHUB_ATC/GMCON):** mecanismo snapshot/trigger confirmado; requiere programación de CFG+RSLT_CNTL (canal a canal) → claramente una *fase de programación autorizada*, no una lectura pasiva.
5. **Correcciones al plan (para aplicar en la futura autorización):**
   - §4 GRBM_SE: «2 contadores/SE» → **1 contador por SE (SE0…SE3)**.
   - §4.4: los offsets en notación `R_03xxxx` del plan son válidos (bytes); **usar offsets dword UMR** de §3 para `umr -r/-w` (`polaris12.gfx800.mm…` / `gmc810.mm…`).
   - §4 MC_ARB: describir como **snapshot/CFG+RSLT_CNTL por canal**, no 4 LO independientes.
   - §4 TCC/TCA: son por-instancia; el total requiere superar/brodcast con `GRBM_GFX_INDEX.INSTANCE_INDEX` **[VERIFICAR]**.
   - §5: añadir lectura del baseline de faults (§1) de este PRECHECK como pre-corrrida para el criterio de aborto.
6. **Lectura en vivo diferida:** la validación de semántica (L2/L4/L6) y el sanity completo MMR requieren root → lista de comandos en Apéndice A para el operador. El PRECHECK queda concluido como **read-only en su totalidad**; **la programación de Etapa 3 sigue NO autorizada**.

Estado final: **Etapa 3 PRECHECK completado; programación NO autorizada.**

---

## Apéndice A — Comandos read-only para el operador (con root)

```bash
# Identificar instancia
sudo umr -i 1     # o `umr -a` para enumerar ASIC

# Lectura de bloques directos (ejemplos, TODOS read-only)
sudo umr -i 1 -r "polaris12.gfx800.mmGRBM_PERFCOUNTER0_LO"
sudo umr -i 1 -r "polaris12.gfx800.mmGRBM_PERFCOUNTER0_SELECT"
sudo umr -i 1 -r "polaris12.gfx800.mmGRBM_SE0_PERFCOUNTER_LO"
sudo umr -i 1 -r "polaris12.gfx800.mmSX_PERFCOUNTER0_LO"
sudo umr -i 1 -r "polaris12.gfx800.mmTCC_PERFCOUNTER0_LO"
sudo umr -i 1 -r "polaris12.gfx800.mmCB_PERFCOUNTER0_SELECT"
sudo umr -i 1 -r "polaris12.gfx800.mmDB_PERFCOUNTER0_LO"
sudo umr -i 1 -r "polaris12.gfx800.mmSQ_PERFCOUNTER_CTRL"
sudo umr -i 1 -r "polaris12.gfx800.mmCP_PERFMON_CNTL"
sudo umr -i 1 -r "polaris12.gfx800.mmGRBM_GFX_INDEX"

# Contadores de memoria (solo lista/lectura; cualquier ESCritura queda EXCLUIDA)
sudo umr -i 1 -lr gfx800    # catálogo completo gfx800
sudo umr -i 1 -lr gmc810    # catálogo completo de memoria
sudo umr -i 1 -r "gmc810.mmMC_ARB_PERFCOUNTER_LO"
sudo umr -i 1 -r "gmc810.mmMC_ARB_PERFCOUNTER_RSLT_CNTL"
sudo umr -i 1 -r "gmc810.mmMC_CITF_PERFCOUNTER0_CFG"

# Snapshot para restauración (§6)
sudo umr -i 1 -lr gfx800 > /home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-D-COUNTERS-AUDIT/runs/snapshot-gfx800-PRECHECK.txt
sudo umr -i 1 -lr gmc810 > /home/lucas/Escritorio/RX550_Iterative_Research/experiments/FASE-D-COUNTERS-AUDIT/runs/snapshot-gmc810-PRECHECK.txt
```

**NO ejecutar** `-w` con ninguno de estos registros; ningún registro requiere escritura para este PRECHECK.

## Apéndice B — Provenance

- Offsets/bitfields: `/usr/share/umr/database/ip/gfx_8_0_0.reg`, `/usr/share/umr/database/ip/gmc_8_1_0.reg` (incluidas por `polaris12.asic`, UMR 1.8.5 instalado en host).
- Clasificación windowed/por-instancia e intro de eventos: `src/amd/common/ac_perfcounter.c` (tablas `cik_*`) — fragmento obtenido por websearch (fossies.org/linux/mesa); fichero completo no recuperable en red esta sesión (gitlab Anubis, sources.debian.org, raw.githubusercontent.com 404) → pendiente para L2.
- Lecturas en vivo archival: `runs/umr-counters-muestras.txt` (Etapa 1) y `runs/etapa2/A1/umr_samples.csv` (Etapa 2).
- Idle en vivo esta sesión: radeontop (dump `/tmp/opencode/rt_idle.csv`), sysfs (`power1_input`, clocks, busy).