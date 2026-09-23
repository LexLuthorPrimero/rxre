# R0-3 — Workarounds / Erratas de Mesa (radeonsi+RADV) aplicables a Polaris12

> **Archivo:** `R0-3-MESA-WORKAROUNDS-POLARIS12.md`
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [VERIFICADO] (postas de código en lista mesa-dev/fossies/kernel git)

---

## 1. Resumen

Polaris12 (`gfx803`, familia `CHIP_POLARIS12`) está afectado por un subconjunto concreto de los
workarounds/erratas que el driver radeonsi de Mesa activa por familia de chip. Ninguno de estos
workarounds requiere modificación por parte del proyecto (Mesa ya los aplica), pero **explican
comportamiento observado y candidaturas de FASE H/Q**. Se listan los verificados:

| Workaround (flag interna) | Aplicable a Polaris12 | Reg/atom | Efecto |
|---|---|---|---|
| `has_msaa_sample_loc_bug` | **SÍ** (`POLARIS10..POLARIS12` ∪ VEGA10 ∪ RAVEN) | `PA_SU_SMALL_PRIM_FILTER_CNTL` (R_028830), sample locations | Pequeño filtro primitivo usa sample locations aunque MSAA esté off; línea discontinua |
| `LINE_FILTER_DISABLE` | **SÍ** (`family <= CHIP_POLARIS12`) | `S_028830_LINE_FILTER_DISABLE` | Bug de filtro de línea en GFX8 (Polaris y anteriores) |
| `clear_db_cache_before_clear` (driconf `radeonsi_clear_db_cache_before_clear`) | Sí (opción) | DB cache flush | Workaround para corrupción con ARK (cache DB/Z antes de clear) |
| `assume_no_z_fights`, `commutative_blend_add` | Opciones driconf | — | Optimizaciones (no erratas HW) |
| MSAA regression 2016 (bug #96908) | Histórica, ya corregida en Mesa | DB flush + disable small prim filter | Polaris: DB no procesa cambio de sample locations sin flush → Z incorrectos |

### No aplicables a Polaris12 (pero presentes en el mismo driver)

- `has_ls_vgpr_init_bug` → SOLO VEGA10/RAVEN (NO Polaris12).
- `dpbb_allowed` (primitive binning) → SOLO RAVEN/RAVEN2.

---

## 2. Evidencia (postas de código)

### 2.1 `has_msaa_sample_loc_bug` — `src/gallium/drivers/radeonsi/si_pipe.c`

```c
sscreen->has_msaa_sample_loc_bug = (sscreen->b.family >= CHIP_POLARIS10 &&
                                    sscreen->b.family <= CHIP_POLARIS12) ||
                                   sscreen->b.family == CHIP_VEGA10 ||
                                   sscreen->b.family == CHIP_RAVEN;
```

- Posta: lista mesa-dev, PATCH `[PATCH 01/10] radeonsi: adjust checking for SC bug workarounds`
  (2017-03) y su evolución (RAVEN añadido en `[PATCH 3/3] radeonsi: add support for Raven2`,
  2018-10; VS prolog en `[PATCH 4/4] ... has_ls_vgpr_init_bug`, 2017-11).

### 2.2 Emisión del filtro — `si_emit_msaa_sample_locs` (si_state.c)

```c
small_prim_filter_cntl =
    S_028830_SMALL_PRIM_FILTER_ENABLE(1) |
    S_028830_LINE_FILTER_DISABLE(sctx->b.family <= CHIP_POLARIS12); /* line bug */
if (has_msaa_sample_loc_bug &&
    sctx->framebuffer.nr_samples > 1 &&
    rs && !rs->multisample_enable)
    small_prim_filter_cntl &= C_028830_SMALL_PRIM_FILTER_ENABLE;
radeon_set_context_reg(cs, R_028830_PA_SU_SMALL_PRIM_FILTER_CNTL, small_prim_filter_cntl);
```

### 2.3 Origen del bug MSAA Polaris (2016, bug #96908)

- `[PATCH 1/2] radeonsi: fix Polaris MSAA regression` (2016-07): la regresión se introdujo con
  commit `d938b8c`. Para usar el small primitive filter hay que poner sample locations a 0 de
  forma explícita, pero la DB no procesa el cambio de sample locations sin flush → Z incorrectos.
  Solución: **deshabilitar el small primitive filter cuando MSAA está desactivado** (en lugar de
  hacer flush).
- `[PATCH 4/4] … emit sample locations also when nr_samples == 1` (2016-11): el state tracker
  habilita MSAA en HW también para nr_samples==1.

---

## 3. Relevancia para el proyecto

- **FASE H (RADV/Workarounds)/FASE Q (Mesa Polaris12 Optimization)**: `msaa_sample_loc_bug` y
  `line filter` son erratas HW reales de Polaris que Mesa ya compensa; cualquier A/B con
  MSAA/prim small debe tenerlas presentes (por ej. Superposition/Heaven usan MSAA; si A/B muestra
  diferencias, no se debe atribuir al "modo MSAA" sin controlar el filtro).
- **Aclaración del panel "DCC behavior" y "HTILE"**: consultar R0-1 y el registro previo
  (TC_COMPATIBLE_HTILE en GFX8). No se modifica el funcionamiento del sistema; es conocimiento
  documental para interpretar resultados existentes.

---

## 4. Fuentes y enlaces

1. Mesa-dev 2017-03 — `si_pipe.c` / `si_pipe.h` / `si_state.c` — postas `has_msaa_sample_loc_bug` y
   `LINE_FILTER_DISABLE`:
   - https://lists.freedesktop.org/archives/mesa-dev/2017-March/150360.html
2. Mesa-dev 2016-07 — fix Polaris MSAA regression (bug #96908):
   - https://lists.freedesktop.org/archives/mesa-dev/2016-July/123414.html
3. Mesa-dev 2016-11 — sample positions nr_samples==1:
   - https://lists.freedesktop.org/archives/mesa-dev/2016-November/135501.html
4. Mesa-dev 2017-11 — `has_ls_vgpr_init_bug` (SOLO VEGA10/RAVEN; contraste de no-aplicabilidad):
   - https://lists.freedesktop.org/archives/mesa-dev/2017-November/175846.html
5. Mesa-dev 2018-10 — Raven2 / msaa_sample_loc_bug (evolución del flag):
   - https://lists.freedesktop.org/archives/mesa-dev/2018-October/208028.html
6. Fossies — `si_state_msaa.c` (posiciones MSAA y R_028BF0.., si aplica):
   - https://fossies.org/linux/mesa/src/gallium/drivers/radeonsi/si_state_msaa.c

---

## 5. Confianza y límites

- [VERIFICADO] propagación de flags por familia de chip en radeonsi (fuentes primarias de listas
  de desarrollo de Mesa).
- Los nombres/hashes de commit citados corresponden a lo que las postas de las listas muestran;
  la versión local de Mesa (26.2.2) es muy posterior y puede haber refactorizado (los flags se
  siguen aplicando de forma equivalente para GFX8/`gfx_level` moderno). No se afirma el estado
  exacto del código local sin leerlo (lectura local no realizada ahora; puede contrastarse en
  sessions futuras).