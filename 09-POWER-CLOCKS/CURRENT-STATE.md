# AGENT-22 — RX550 POWER / CLOCKS — CURRENT STATE

**Target**: `1002:699f` rev c7 (Lexa PRO — RX 550/550X), PCI `01:00.0`
**Host**: Nobara 7.1.3-200.nobara.fc44.x86_64, driver `amdgpu`
**Scope**: SCLK, MCLK, DPM, V/F, power cap, thermal thresholds, throttling, perf states
**Date of capture**: 2026-10-03

---

## 0. HEADLINE

The idle-state telemetry surface of this GPU is **entirely unreadable** (`EBUSY`), and that
is a *policy*, not a fault. Root cause traced to source. Resolved **without root** by holding
the render node open. Full DPM + hwmon surface then became measurable.

---

## 1. THE OBSERVABILITY BLOCKER (category [01])

### E-PWR-001 — OBSERVED
With no GPU activity, `power/runtime_status = suspended` and **every** power/clock/thermal
sysfs read returns `EBUSY` ("Dispositivo o recurso ocupado"):

- `pp_dpm_sclk`, `pp_dpm_mclk`, `pp_dpm_pcie`, `pp_cur_state`, `power_dpm_state`,
  `power_dpm_force_performance_level`
- all of `hwmon1`: `freq1_input`, `freq2_input`, `in0_input`, `power1_input`,
  `power1_cap*`, `temp1_input`, `pwm1`

### E-PWR-002 — PROVEN_DERIVED (static provenance, source of record: linux-7.2.8 tree)

Read path for DPM clocks:

```
cat pp_dpm_sclk
  -> amdgpu_get_pp_dpm_sclk()            pm/amdgpu_pm.c:1093
  -> amdgpu_get_pp_dpm_clock()           pm/amdgpu_pm.c:994
  -> amdgpu_pm_get_access_if_active()    pm/amdgpu_pm.c:~1120
       -> amdgpu_pm_dev_state_check(adev, runpm=false)   pm/amdgpu_pm.c:109
            if (amdgpu_in_reset(adev) || !full_init) return -EBUSY;   // :115
            if (adev->in_suspend && !runpm_check)      return -EBUSY;   // :118
       -> pm_runtime_get_if_active(adev->dev)
            if (!ret) return -EPERM;
  -> amdgpu_dpm_emit_clock_levels()
```

`amdgpu_hwmon_show_power_cap_generic()` uses the **same** `amdgpu_pm_get_access_if_active()`
gate, so DPM and hwmon fail for one coherent reason, not per-sensor quirks.

**Key semantic** (`amdgpu_pm_get_access_if_active`, doc comment verbatim): *"Allow only if
device is active."* It uses `pm_runtime_get_if_active()`, which **never resumes** the device.
By contrast `amdgpu_pm_get_access()` uses `pm_runtime_resume_and_get()` and *does* resume.

> So reading a DPM/hwmon attribute is a **passive** operation. It cannot bring the GPU back.
> Consequence for our own driver: telemetry must be sampled while the device is genuinely
> active, or the driver must hold a runtime-PM reference itself.

**Which `-EBUSY` sub-condition fired**: `adev->in_suspend` is the consistent explanation
(runtime_status=suspended). NOT excluded: `!full_init` or `in_reset`. So the precise branch is
`CORROBORATED`, not `PROVEN`.

---

## 2. RESOLUTION OF THE BLOCKER — NO ROOT REQUIRED

### E-PWR-003 — OBSERVED
Opening `/dev/dri/renderD128|D129` and holding the fd keeps amdgpu runtime-PM **resumed**:

| phase | `power/runtime_status` | `cat pp_dpm_sclk` |
|---|---|---|
| idle | `suspended` | `EBUSY` |
| holding render node | `active` | `0: 214Mhz *` |

Instrument: `rx550_hold.c` (research instrument, open + sleep N s, submits nothing).
`/dev/dri/renderD129` is mode `0666`; user is **not** in group `video` — 0666 suffices.

`power/autosuspend_delay_ms = 5000`, `power/control = auto`, `wakeup = disabled`.
The RX550 is **not** the console device (`boot_vga = 0`; Intel iGPU is console), so nothing
keeps it awake and it drops to D3hot within 5 s of inactivity.

---

## 3. MEASURED DPM TABLES (device held active)

Source: `evidence/dpm-active.txt` sha256 `05b5a0f4…deddc`

### E-PWR-004 — OBSERVED

**SCLK — 8 DPM levels** (`pp_dpm_sclk`):
`214, 551, 734, 980, 1000, 1020, 1046, 1071 MHz` — current `*` on **level 0 (214 MHz)**

**MCLK — 3 DPM levels** (`pp_dpm_mclk`):
`300, 625, 1500 MHz` — current `*` on **level 0 (300 MHz)**

**PCIe — 2 levels** (`pp_dpm_pcie`): `0: 2.5GT/s, x8`, `1: 5.0GT/s, x16` (current `*` = level 1)

### ⚠ DISAMBIGUATION (prevents a real category error)

- `pp_num_states` = `states: 2` / `0 boot` / `1 performance` is the **PCIe/D3PCIP power-state
  list**, NOT the number of SCLK levels (there are 8).
- `pp_cur_state` = `1` therefore reports the **PCIe power state index** (= performance), NOT
  the current SCLK level. The `*` marker on `pp_dpm_sclk` index 0 is the current clock.
- Conflating these would make the GPU look like it is running at the *second-highest* state
  when it is in fact at the **lowest SCLK** while the PCIe link is at the top PCIe state.

---

## 4. POWER, VOLTAGE, THERMAL (device held active)

Source: `evidence/hwmon-active.txt` sha256 `ae826831…bc3`

### E-PWR-005 — OBSERVED (idle/boot state, SCLK 214 MHz, MCLK 300 MHz)

| hwmon attr | label | value | unit |
|---|---|---|---|
| `freq1_input` | sclk | 214 000 000 | Hz |
| `freq2_input` | mclk | 300 000 000 | Hz |
| `in0_input` | **vddgfx** | **687** | mV |
| `power1_input` | **PPT** | **3 227 000** | µW = **3.23 W** |
| `power1_cap` | — | 35 000 000 | µW = **35 W** |
| `power1_cap_default` | — | 35 000 000 | µW = **35 W** |
| `power1_cap_max` | — | 35 000 000 | µW = **35 W** |
| `power1_cap_min` | — | 0 | µW |
| `temp1_input` | **edge** | 28 000 | m°C = **28 °C** |
| `temp1_crit` | — | 97 000 | m°C = **97 °C** |
| `temp1_crit_hyst` | — | −273 150 | **invalid / unprogrammed** |
| `pwm1` | — | 75 (of 0–255) | — |
| `pwm1_enable` | — | 2 = manual | — |

### E-PWR-006 — OBSERVED (sensor census / absences)

- `temp2_input` (junction) — **DOES NOT EXIST**
- `temp3_input` (memory) — **DOES NOT EXIST**
- `temp1_emergency` / `temp2_emergency` — **DO NOT EXIST**
- `fan1_input` → `EINVAL` — fan RPM not reported by SMU (fan exists, `pwm1` is writable)

**Scope gate (§16)**: these are `PROVEN_ABSENT` *as sysfs nodes in hwmon1 on this running
system*. This is **not** a claim that the ASIC lacks junction/memory sensors — only that this
driver+firmware exposes no such node.

### E-PWR-007 — DERIVED (first V/F point)
**214 MHz @ 687 mV, 3.23 W, 28 °C** at the lowest DPM state. Single point — a V/F *curve*
requires the loaded sweep (not yet performed).

---

## 5. DPM GOVERNING POLICY — `pp_power_profile_mode`

### E-PWR-008 — OBSERVED

Current profile: **1 = `3D_FULL_SCREEN`** (marked `*`).

| # | profile | SCLK_UP_HYST | SCLK_DOWN_HYST | SCLK_ACTIVE_LEVEL | MCLK_UP_HYST | MCLK_DOWN_HYST | MCLK_ACTIVE_LEVEL |
|---|---|---|---|---|---|---|---|
| 0 | BOOTUP_DEFAULT | – | – | – | – | – | – |
| 1 | **3D_FULL_SCREEN** * | 0 | **100** | 30 | 3 | 16 | 20 |
| 2 | POWER_SAVING | 10 | 0 | 30 | – | – | – |
| 3 | VIDEO | – | – | – | 10 | 16 | 31 |
| 4 | VR | 0 | 11 | 50 | 0 | 100 | 10 |
| 5 | **COMPUTE** | 0 | **5** | 30 | – | – | – |
| 6 | CUSTOM | – | – | – | – | – | – |

`-` = not parameterised for this profile (field is unused).

**This is the clock-transition policy** — the `WORKLOAD → CLOCK` edge of the causal model.
Notable: `COMPUTE` has a far *tighter* SCLK down-hysteresis (5) than `3D_FULL_SCREEN` (100),
i.e. the default 3D profile is far more reluctant to drop clocks than the compute profile.
Units/semantics of the hysteresis fields are **not yet** established (open item).

Also: `pp_sclk_od = 0`, `pp_mclk_od = 0` (overdrive off).
`power_dpm_state = performance`, `power_dpm_force_performance_level = auto`.

---

## 6. `pp_table` — RAW BLOB, NOT A TABLE

### E-PWR-009 — PROVEN (provenance) + OBSERVED (payload)

`cat pp_table` returned **778 bytes of binary** (sha256 `ff65c3f5…a83210`), *not* a text table.
This is **not** an error and **not** a valid DPM table — it is the expected format for this path:

```
amdgpu_get_pp_table()            pm/amdgpu_pm.c:~555
  -> amdgpu_pm_get_access_if_active()      (same EBUSY gate)
  -> amdgpu_dpm_get_pp_table()            pm/amdgpu_dpm.c:1195
       memcpy(table, pp_funcs->get_pp_table(...), size)   // RAW BYTES
  -> smu_sys_get_pp_table()               pm/swsmu/amdgpu_smu.c:644
       *table = smu_table->power_play_table   // == SMU_TABLE_DPMCLKPOWRESET
       returns power_play_table_size           // == 778
```

To use it, the blob must be decoded against the Arcturus `DPMCLKPOWRESET` struct from the
source tree. **Status: NOT YET DECODED.** Currently `UNUSED_EVIDENCE` (correctly refused).

---

## 7. PCIe LINK ANOMALY (unresolved confounder)

### E-PWR-010 — OBSERVED, CONTRAADICTSORY

| source | width | speed |
|---|---|---|
| `max_link_width` / `max_link_speed` (PCIe core) | **8** | 8.0 GT/s |
| `current_link_width` / `current_link_speed` (read while **active**) | **4** | 5.0 GT/s |
| `pp_dpm_pcie` level 1 (current) | **x16** | 5.0 GT/s |

**Conflict**: DPM advertises x16 but the card's maximum is x8, and the *current* negotiated
width reads x4. Three candidate explanations, not yet discriminated:
1. D3hot/downtrain reduces LNKSTA-reported width → `4` is a suspension artifact, not steady state.
2. The board slot is mechanically x8 and an intermediate x4 is a real downtraining.
3. DPM table x16 is simply unreachable and must be clamped by the link layer.

`current_link_width`/`max_link_width` have **zero** occurrences in `drivers/gpu/drm/amd/` →
they are generic **PCIe-core** sysfs attributes derived from config-space LNKSTA/LNKCTL, not
amdgpu software state. That rules out an amdgpu misreport but not a real downtrain.

**Status: OPEN CONTRADICTION.** Must be resolved *before* any bandwidth-bound conclusion.

---

## 8. CAPABILITY CENSUS (what we can and cannot drive)

### E-PWR-011 — OBSERVED

| capability | state | consequence |
|---|---|---|
| `radeonsi_dri.so` | **present** in `/usr/lib64/dri` | OpenGL on RX550 **is** available |
| AMD Vulkan ICD (`amd_icd`/`radeonsi_icd`) | **absent** | no Vulkan on RX550 |
| `libdrum` legacy `radeon_icd` | present | useless — legacy radeon does not support Polaris12 |
| `libdrm.so.1.134.0` + **dev headers** | present (2.4.134) | DRM render API usable |
| EGL 1.5 + GLES3 + GL headers | present | **headless EGL surfaceless load possible** |
| `glmark2` | absent | – |
| `glxgears` | present but needs an X display bound to the **iGPU** | wrong device for our purpose |
| root / sudo | **unavailable** (password required) | all observations must be unprivileged |

Since `boot_vga=0`, the RX550 drives no display: **all GPU load must be headless**
(EGL surfaceless + GLES3, selecting the AMD EGL device), which is feasible with the
toolchain present.

---

## 9. CAUSAL MODEL — CURRENT STATE (honest)

```
WORKLOAD ──?──> GPU_BUSY ──?──> DPM_LEVEL ──?──> SCLK/MCLK
                                                      │
                                                      v
                                          vddgfx (V/F) ──> PPT ──> edge TEMP
                                                                    │
                                                                    v
                                                        throttle @ 97 °C / 35 W ?
```

| edge | status | evidence |
|---|---|---|
| WORKLOAD → GPU_BUSY | **NOT MEASURED** | no load generated yet |
| GPU_BUSY → DPM_LEVEL | **NOT MEASURED** | needs busy% under load |
| DPM_LEVEL → SCLK/MCLK | **PARTIAL** | `*` markers + table exist; transition not observed |
| SCLK → vddgfx | **ONE POINT ONLY** (214 MHz @ 687 mV) | curve needs sweep |
| → PPT | **ONE POINT ONLY** (3.23 W idle) | |
| PPT → edge TEMP | **NOT MEASURED** | thermal response untested |
| throttle behaviour | **NOT MEASURED** | caps known (35 W, 97 °C) but never approached |
| DPM policy → transitions | **MECHANISM KNOWN, EFFECT UNVERIFIED** | E-PWR-008 |

**The chain is documented at its endpoints and entirely unmeasured in its dynamics.**
No causal claim is licensed yet.

---

## 10. CONTROL POINTS FOR OUR OWN DRIVER (candidate list, unranked)

Derived strictly from what was observed — each still needs validation:

1. **Hold a runtime-PM reference** before sampling any telemetry — otherwise every power/clock
   read returns `EBUSY` (E-PWR-001/002). Non-obvious and easy to get wrong.
2. **Prefer the COMPUTE profile over the default 3D_FULL_SCREEN** for compute workloads —
   SCLK down-hysteresis 5 vs 100 (E-PWR-008). *Effect unverified.*
3. **`pp_power_profile_mode` is runtime-selectable** → per-workload clock policy.
4. **35 W PPT cap is settable** (`power1_cap`, writable; min 0, max/default 35 W) → a real
   power/thermal control knob. *Write semantics untested; do not write yet (§42/§43).*
5. **`temp1_crit` = 97 °C, `temp1_crit_hyst` unprogrammed (−273150)** → hysteresis is ours to
   set; a naive value could cause thermal oscillation.
6. **`pp_sclk_od` / `pp_mclk_od` = 0** → overdrive gate exists (currently off).
7. Only `edge` temp is observable → throttling decisions cannot use junction/memory temp.

---

## 11. OPEN FRONTIERS (ranked by discriminant)

| ID | frontier | discriminant | risk |
|---|---|---|---|
| **F-PWR-01** | Generate headless EGL/GLES3 load on RX550; sample busy%→SCLK→PPT→temp | `gpu_busy_percent` rises while SCLK climbs | LOW |
| **F-PWR-02** | Resolve PCIe x16-vs-x8-vs-x4 contradiction (E-PWR-010) | read LNKSTA while active + `lspci -vv` LnkSta | READ-ONLY |
| **F-PWR-03** | Decode 778 B `pp_table` → per-level V/F/power limits | struct size matches 778 | READ-ONLY |
| **F-PWR-04** | Determine hysteresis-field units/semantics | source of `SCLK_UP_HYST` consumers | READ-ONLY |
| **F-PWR-05** | Observe actual clock transitions under varying load | `*` marker moves across levels | LOW |
| **F-PWR-06** | Test PPT cap write semantics | **DEFERRED** — controlled write, needs intervention gate | MED-HIGH |

---

## 12. NEGATIVE / INVALID RESULTS (recorded, not silently dropped)

- `pp_table` binary output — **INVALID_AS_TABLE**, valid as raw blob. Not consumed as a table.
- `temp2_*` / `temp3_*` / `temp*_emergency` — **PROVEN_ABSENT as sysfs nodes** (scoped).
- `fan1_input` — `EINVAL`, fan RPM not exposed.
- `pp_cur_state` = 1 while SCLK at level 0 — **not** a contradiction once disambiguated (§3).
- Vulkan on RX550 — **NOT_AVAILABLE** (no AMD ICD), despite `radeonsi_dri.so` existing.

---

## 13. ARTIFACT LINEAGE

| artifact | producer | sha256 |
|---|---|---|
| `evidence/dpm-active.txt` | rx550_hold + `cat` sysfs | `05b5a0f4924cb89c548d679a782a5064e57bd1db5a42e860f675a52a721deddc` |
| `evidence/hwmon-active.txt` | rx550_hold + `cat` hwmon1 | `ae826831be2bc5325c2a5c56cd4b4b0def02262745505743c2fbdb26e5e97bc3` |
| `evidence/pp_table.txt` | `cat pp_table` (raw blob) | `ff65c3f52132b8dfb7b227a5448e4eb2b300ab272e594dd7a6893e9c52a83210` |
| instrument | `/tmp/opencode/rx550_hold.c` (gcc -O2, unprivileged) | not yet hashed |

**Tool validity**: `rx550_hold` is UNVALIDATED beyond "opening the node flips runtime_status to
active and DPM reads succeed" (single observation, no negative control yet).

---

## 14. STATE SUMMARY

Project branch **AGENT-22 POWER/CLOCKS**: **ACTIVE**.

- Observability blocker: **RESOLVED** (no root).
- DPM tables: **MEASURED**.
- Power cap + thermal thresholds: **MEASURED**.
- DPM transition policy: **MEASURED**.
- Causal dynamics: **NOT MEASURED** ← this is the open work, F-PWR-01.
- No clock/power write has been performed. No hardware state modified.
