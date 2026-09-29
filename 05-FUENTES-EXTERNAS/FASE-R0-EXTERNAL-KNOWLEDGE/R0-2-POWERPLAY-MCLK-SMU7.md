# R0-2 — Política DPM de MCLK en SMU7/PowerPlay para Polaris (128-bit)

> **Archivo:** `R0-2-POWERPLAY-MCLK-SMU7.md`
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY / POLARIS12 KNOWLEDGE GAP AUDIT
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (read-only, validación cruzada de fuentes externas)
> **Clasificación:** [VERIFICADO source-level] (código fuente kernel Linux; no demuestra
> el trigger effective de esta unidad ni equivalencia con `mem_busy_percent`).
>
> **RECONCILIACIÓN 2026-09-24:** 5/16/20 se conserva como parámetro upstream para el
> caso de bus 128-bit. La activación local, el firmware/BIOS y la relación con MCLK
> reportada o `mem_busy_percent` siguen `UNKNOWN`; no es un gate operativo.

---

## 1. Resumen

La política optimizada de transición DPM de MCLK (histeresis y actividad objetivo) en el
controlador `smu7` (kernel Linux, `drivers/gpu/drm/amd/pm/powerplay/`) depende del **grosor de
bus VRAM (`adev->gmc.vram_width`)** y está **condicionada a la familia Polaris** (`chip_id >= CHIP_POLARIS10`).

Para **Polaris12 / RX 550 (bus 128-bit)**, los valores son:

| Parámetro | Significado | Valor |
|---|---|---|
| `mclk_up_hyst` | Histeresis de subida de MCLK | **5** |
| `mclk_down_hyst` | Histeresis de bajada de MCLK | **16** |
| `mclk_activity` | Actividad objetivo (%) para transición | **20** |

El parámetro upstream coincide con la investigación local `R-07` como **referencia
source-level**; no valida el comportamiento efectivo de la unidad ni la equivalencia
con `mem_busy_percent`.

---

## 2. Fuente primaria (código del kernel)

### 2.1 `smu7_init_dpm_defaults()` en `smu7_hwmgr.c`

Bloque que fija los valores por grosor de bus:

```c
data->current_profile_setting.bupdate_mclk = 1;

data->current_profile_setting.mclk_up_hyst = 0;        // caso NO-Polaris (default legacy)
data->current_profile_setting.mclk_down_hyst = 100;
data->current_profile_setting.mclk_activity = SMU7_MCLK_TARGETACTIVITY_DFLT;

if (adev->gmc.vram_width == 256) {
    mclk_up_hyst = 10;  mclk_down_hyst = 60;  mclk_activity = 25;
} else if (adev->gmc.vram_width == 128) {
    mclk_up_hyst = 5;   mclk_down_hyst = 16;  mclk_activity = 20;   // <-- Polaris12
} else if (adev->gmc.vram_width == 64) {
    mclk_up_hyst = 3;   mclk_down_hyst = 16;  mclk_activity = 20;
}
```

### 2.2 Commit que condiciona la política a Polaris

- Commit: `8d89b96fe79713fc5fc2b8d9c9b9f93842b55695` (mirror b0tt0m/Zx2c4, kernel).
- Modificación posterior que **restringe la política optimizada a `chip_id >= CHIP_POLARIS10`**:
  - Antes: los valores 256/128/64-bit se aplicaban a **todos** los chips SMU7 (incluyendo
    Tonga/Fiji/Carrizo) → no deseado.
  - Después: `if (hwmgr->chip_id >= CHIP_POLARIS10) { ramas por vram_width } else { 0/100/DFLT }`.
  - Confirma lógica del parche "Only apply optimized mclk dpm policy on polaris".

### 2.3 `struct profile_mode_setting` (smu7_hwmgr.h)

```c
struct profile_mode_setting {
    uint8_t  bupdate_sclk;
    uint8_t  sclk_up_hyst;
    uint8_t  sclk_down_hyst;
    uint16_t sclk_activity;
    uint8_t  bupdate_mclk;
    uint8_t  mclk_up_hyst;      // <-- 5 para Polaris12
    uint8_t  mclk_down_hyst;    // <-- 16 para Polaris12
    uint16_t mclk_activity;     // <-- 20 para Polaris12
};
```

También existe `apply_optimized_settings` y `update_up_hyst`/`update_down_hyst` (override por
`pp_dpm_*` / programas de gestión de potencia).

### 2.4 MCLK DPM lógica general (polaris10_smumgr.c)

- `MemoryDpmLevelCount` = nº de niveles de MCLK (máx. DPM).
- Los niveles MCLK se rellenan desde `vdd_dep_on_mclk` (tabla de dependencia voltaje/reloj del
  VBIOS/pptable).
- Nivel más alto: `DisplayWatermark = HIGH`, `EnabledForActivity = 1` (el 1500 MHz puede activarse
  por actividad).
- `levels[0].ActivityLevel = 0x1f` (protección contra stutter/up-threshold).
- `mclk_stutter_mode_threshold = 40000` (stutter enable por debajo de 40 MHz si aplica).

---

## 3. Implicación para Polaris12 / RX 550

- El código upstream documenta `mclk_activity=20`, `up_hyst=5` y `down_hyst=16` para
  el bus de 128 bits. **No demuestra** que MCLK 1500 en esta unidad requiera
  `mem_busy_percent >20`; el trigger local, firmware/BIOS y perfil efectivo son `UNKNOWN`.
- `mem_busy ~36 %` (sintéticos) vs `~25 %` (Superposition) son observaciones de proxy;
  no se convierten en un umbral causal del SMU.
- La correlación observada MCLK 300–625/1500 con presión de memoria es **direccional**,
  no una demostración del mecanismo local.

---

## 4. Fuentes y enlaces

1. `smu7_hwmgr.c` / `smu7_hwmgr.h` — kernel Linux (`drivers/gpu/drm/amd/pm/powerplay/hwmgr/`):
   - https://codebrowser.dev/linux/linux/drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_hwmgr.c.html
   - https://codebrowser.dev/linux/linux/drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_hwmgr.h.html
2. Commits/diffs (postas del bloque vram_width y del gate `chip_id >= CHIP_POLARIS10`):
   - `8d89b96fe79713fc5fc2b8d9c9b9f93842b55695` (smu7_init_dpm_defaults 256/128/64)
   - `7d892ca6a588bedd71a95cecd87512d9b24b2141` (gate `hwmgr->chip_id >= CHIP_POLARIS10`,
     FreeBSD drm-kmod mirror: `git.etawen.dev`)
3. `polaris10_smumgr.c` — niveles MCLK, `MemoryDpmLevelCount`, stutter, watermark (Cregit Linux 5.4:
   https://cregit.linuxsources.org/code/5.4/drivers/gpu/drm/amd/powerplay/smumgr/polaris10_smumgr.c.html).
4. Cross-reference local: `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` → **R-07** (registraba
   5/16/20 como policy source-level). R-4A además observó un readout local `3/16/20`;
   la equivalencia de campos/perfil no está reconciliada y no se usa como gate local.

---

## 5. Confianza y límites

- [VERIFICADO source-level] para la existencia de la política upstream.
- La medición real del comportamiento de transición en la unidad concreta depende de
  VBIOS/pptable, firmware y estado térmico; el código no demuestra el trigger local.
- RX 550 (1002:699f, Polaris12) → bus 128-bit → **5/16/20 upstream**; el readout local
  `3/16/20` de R-4A queda **UNRESOLVED** hasta reconciliar campo/perfil. No se usa como
  gate local.
