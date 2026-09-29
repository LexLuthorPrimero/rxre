# RESULTADOS-M1 — Efecto de power1_cap 35 W vs 30 W

> **ESTADO: COMPLETADO** (2026-09-20). Cierre autorizado. Artefactos crudos intactos.
>
> **Nota de reconciliación 2026-09-24:** M1 es un snapshot histórico; su regla de
>abort a 90 °C no reemplaza la taxonomía vigente (90 °C = confound, 96 °C = abort
> configurado). `power1_input` es `W_SMU`, no vatímetro.

- Fecha de ejecución: 2026-09-20 00:00–00:13 (-03:00)
- Directorio: `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939`
- GPU: RX 550 Polaris12 (card1, amdgpu, `1002:699f`) · Display: Intel HD 4600 (card0, i915)
- Workload: `vkmark -p immediate -s 1920x1080 -b shading:shading=phong:duration=25`
- Mesa: STOCK · 5 bloques pareados (10 corridas) · ventana de análisis [5 s, 25 s] · telemetría 10 Hz
- Runner congelado durante el experimento (hashes registrados al inicio).

## 0. Integridad y seguridad de las 10 corridas

- **10/10 corridas completadas, todas `OK`** (`stopped_early=false`). **5× 35 000 000 µW + 5× 30 000 000 µW.**
- SET/readback: 30 W → `30000000`; 35 W → `35000000` (baseline, escritura no-op). Correctos.
- RESTORE/readback final: **`restored=35000000` y `readback_final=35000000` en las 10** (`rollback_attempts=1`).
- Auxiliares sin cambios: `power/control=on`, `power_dpm_force_performance_level=auto`,
  `pp_power_profile_mode` activo `3D_FULL_SCREEN *`; `aux_unchanged=true`, `aux_diff=[]` (10/10).
- Sin `ERROR`/`CRITICAL`, sin `fatal`, sin reset/hang (`gpu_reset_check.checked=true`,
  `format=short-iso`, `matches=[]` en las 10), sin `sampler_error`.
- `workload_rc=0` en las 10. Temperatura inicial 40–44 °C (cooldown ≤45 °C OK); máxima en ventana 52 °C
  (límite de aborto 90 °C, no alcanzado).
- Artefactos completos: 10× `{audit.json, stdout.txt, stderr.txt, telemetry.csv}` + `m1-schedule.json`.

## 0.1 Compuerta de ligadura (bloqueante)

- **`media(power1_input @35 W)` en ventana = 12.267 W (pooled) / 12.268 W (media de medias por corrida).**
- **12.267 W < 27 W → COMPUERTA ACTIVADA → clasificación `NO DISCRIMINATIVO`.**

## 1. FPS (ventana, 1 valor por corrida)

| bloque | orden | FPS 35 W | FPS 30 W | Δ (30−35) | FrameTime 35/30 (ms) |
|---|---|---:|---:|---:|---|
| 1 | 35→30 | 74 | 74 | **0** | 13.514 / 13.514 |
| 2 | 30→35 | 74 | 74 | **0** | 13.514 / 13.514 |
| 3 | 35→30 | 74 | 74 | **0** | 13.514 / 13.514 |
| 4 | 30→35 | 74 | 74 | **0** | 13.514 / 13.514 |
| 5 | 35→30 | 71 | 71 | **0** | 14.085 / 14.085 |
| **mediana** | | 74 | 74 | **0** | 13.514 / 13.514 |

**ΔFPS pareado = [0, 0, 0, 0, 0]** · media 0.0000 · IC95% (0.0000, 0.0000).

## 2. SCLK efectivo (mediana por corrida)

| bloque | 35 W | 30 W | Δ (MHz) |
|---|---:|---:|---:|
| 1 | 1071 | 1071 | **0** |
| 2 | 1071 | 1071 | **0** |
| 3 | 1071 | 1071 | **0** |
| 4 | 1071 | 1071 | **0** |
| 5 | 1071 | 1071 | **0** |
| **mediana** | 1071 | 1071 | **0** |

**ΔSCLK pareado = [0, 0, 0, 0, 0] MHz** · IC95% (0.0, 0.0); no cumple ≤ −50 MHz.

## 3. MCLK efectivo (mediana por corrida)

| bloque | 35 W | 30 W | Δ (MHz) |
|---|---:|---:|---:|
| 1..5 | 625 | 625 | **0** |

## 4. power1_input (media por corrida, W) — estimador SMU

| bloque | 35 W | 30 W | Δ (30−35) |
|---|---:|---:|---:|
| 1 | 12.291 | 12.328 | +0.037 |
| 2 | 12.328 | 12.325 | −0.003 |
| 3 | 12.342 | 12.338 | −0.004 |
| 4 | 12.330 | 12.326 | −0.003 |
| 5 | 12.052 | 11.917 | −0.134 |

ΔPwr: media **−0.0215 W**, IC95% **(−0.1029, +0.0598)** (contiene 0; signo negativo 4/5, indistinguible de ruido).

## 5. Otros (ventana)

- `gpu_busy` media: 98.94 % (35 W) / 99.13 % (30 W); mediana 100 % en ambos.
- `mem_busy` media: 9.09 % (35 W) / 6.94 % (30 W).
- `temp_mc`: media 49.04 °C (35 W) / 49.27 °C (30 W); máx 52 °C en ambos.
- `runtime_status`: `active` en las 10 corridas.
- Errores/reset/hang: **ninguno**.

## 6. Ruido y criterio (si el cap hubiese ligado)

- **CV intra-brazo FPS = 1.828 %** (ambos brazos, sd 1.3416 sobre media 73.4). Umbral de magnitud: 2×CV = 3.66 %.
- `|ΔFPS|/FPS35 = 0 %` < 3.66 %; IC95% ΔFPS contiene 0 → sin efecto.
- ΔSCLK = 0 MHz (> −50 MHz) → sin efecto.
- ΔPwr con IC95% conteniendo 0 → sin efecto.

## 7. Anomalías / observaciones

- **Bloque 5: FPS 74→71 en AMBOS brazos** (FrameTime 13.514→14.085 ms), coincidente con las temperaturas
  de ventana más altas (50–52 °C) y con ser el tramo final de la sesión. La variación fue **simétrica y no
  diferencial del cap**.
- `gpu_busy_percent` mostró ceros aislados dentro de la ventana (≈1 muestra/corrida; 10 en b5-a1 y 6 en
  b5-a2) mientras `sclk_hz` permaneció fijo en 1071 MHz y el FPS no cambió → artefactos de lectura, no idle.
- `mclk_hz`: mediana estable en 625 MHz con excursiones raras a 300/1500 MHz.
- El marcador de `pp_dpm_sclk` pasa de nivel 0 (idle) a 7 (1071 MHz) por la carga; la comparación
  normalizada lo ignora correctamente.

## 8. HOME / XDG_RUNTIME_DIR

- Corregido. **Las 10 corridas tuvieron `stderr.txt` vacío**: desapareció el
  `Failed to create /root/.cache/mesa_shader_cache ... Permission denied` del primer intento.
- El workload corrió con `HOME` del usuario real (no `/root`) y `XDG_RUNTIME_DIR=/run/user/<uid>`.

## Conclusión

**M1 = NO DISCRIMINATIVO — el cap no liga con `vkmark shading:phong` a 1920×1080.**

> Aclaración obligatoria: **"NO DISCRIMINATIVO" NO significa "30 W = 35 W para cualquier workload".**
> Significa que **este workload no alcanzó una demanda suficiente para que el cap de potencia pudiera ligar**
> (W_SMU ≈12.27 W, muy por debajo del cap de 30 W). No se declara "sin efecto" sobre otros workloads.

## 9. Preservación de artefactos (sha256)

Artefactos originales **no modificados**. `stderr.txt` (vacío) idéntico en las 10: `e3b0c442…b855`.

```
3d2c7015105e635737657c2cb12acb12dab6318d0b4c21eaf2d10d0ace50ad29  block01-arm1-35000000/audit.json
a410383c1da363a9c1524857a3549f48259a568edf53c7b62c08931fdfb74e50  block01-arm1-35000000/telemetry.csv
bf4acf975a4d9b3a1bf6f328b1a5307c259012a0cf5ff3c6a40e91ac9fcc71a0  block01-arm2-30000000/audit.json
3d993b78eabcb702bca8b7e6f45288ba5e0122dba15e38a0e490529f8aca4c3b  block01-arm2-30000000/telemetry.csv
9fc113967b9a58bf2bb523b4a74a46376762ab7564cffe4008d8441ee6ed95f9  block02-arm1-30000000/audit.json
332279d88db9ed6469040f7d137cd376d1f83fed2cf28035763f3a1c8664387d  block02-arm1-30000000/telemetry.csv
a9a548a5a640785363b6897fba16361d470d26f906622f5c5a67a97107fca23b  block02-arm2-35000000/audit.json
342a5868cd75b3b19cd8cac36c0b490a3ef9ce87386babec620f655ee935b016  block02-arm2-35000000/telemetry.csv
a5e77e06825bf38ebbe7f28777abb66b8b10e701b6883f09a2c2737859987806  block03-arm1-35000000/audit.json
03144c1ef8a540033a59166b975f230378f3c9c7b43b2c0ec5aa1c836dad61ab  block03-arm1-35000000/telemetry.csv
3095eed0927aaf90f3f0c05c2425b297acca709e82679bbc98c7120c95d62e6c  block03-arm2-30000000/audit.json
358f53f0ff99e01bab829e0815b941b141c4f3e0a816b0340334cce48d941645  block03-arm2-30000000/telemetry.csv
fa00d1896f47988307d26f9567177cf3a40db99a994894c4468f6eac17de7e85  block04-arm1-30000000/audit.json
dfc72c6db90d12a6d7f99da145749a6a03b52b074d9d4fec5058accba66567a8  block04-arm1-30000000/telemetry.csv
30c57cd8db328be0080c98acadb324b9bbdd529059c3f412918f8b1257b6374c  block04-arm2-35000000/audit.json
02eba8e7adc549f07963385452b00c588065632e01615b3bbe2aca479928176a  block04-arm2-35000000/telemetry.csv
05eb53b16812c14c83c2bfe2844b357f29bdddd454eeb9e349871dfd1d4c2b68  block05-arm1-35000000/audit.json
412faab673e347a3550176fc0d4c61a07e88239eb79b716e54478ce9486c7549  block05-arm1-35000000/telemetry.csv
41c9ae98cc19c0963e2c7204fabbf0ef6e63810fc0af78e610e7a6b4caede815  block05-arm2-30000000/audit.json
4df5171089401ee4dd2cb38570db0be699b515e51dee58c621870e7e9f57537f  block05-arm2-30000000/telemetry.csv
4af5478fc53f34a84357c666f5beec9f82855f1d44ba2608d45eef8ae10477e5  m1-schedule.json
```

`stdout.txt`: idéntico en b01–b04 (`25e305fb…ad45`); b05 distinto (`ad2c756f…d9e5`).
