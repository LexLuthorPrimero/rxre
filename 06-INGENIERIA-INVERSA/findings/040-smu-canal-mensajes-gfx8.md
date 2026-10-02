# 040 · El canal de mensajes al SMU en GFX8: quién calcula el reloj y quién lo aplica

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`

> Territorio virgen: `SMU/DPM/clocks/power/thermal` tenía 0 findings y 0 herramientas.
> Verificado antes de empezar: `findings/` cubría PM4, PTE/PDE, VM flush, fences.
> No solapa con los scopes `pm4dw`, `pteflags`, `findings`, `docs`.

---

## CUDA principal

**El driver NO escribe los registros de reloj de GFX8.** Calcula un *payload* de
nivel de rendimiento, lo serializa, lo sube a la SRAM del SMC, y **es el firmware
del SMU quien aplica el cambio de frecuencia**.

Esto no es una inferencia: `si_convert_power_level_to_smc()` —el producer del
payload— no contiene ni una sola escritura de registro.

---

## 1. El canal host ↔ SMU

```
amdgpu_si_send_msg_to_smc(adev, msg)      pm/legacy-dpm/si_smc.c:170
  :191   if (!amdgpu_si_is_smc_running(adev)) return PPSMC_Result_Failed;
  :194   WREG32(mmSMC_MESSAGE_0, msg);                    host → SMU
  :196   for (i = 0; i < usec_timeout; i++) {
  :197       tmp = RREG32(mmSMC_RESP_0);                  SMU → host
  :198       if (tmp != 0) break;                        0x00 = pendiente
  :200       udelay(1);                                  busy-wait 1 µs
         }
  :203   tmp = RREG32(mmSMC_RESP_0);
  :204   if (tmp == 0) drm_warn("timeout on message: %x (SMC_SCRATCH0: %x)", ...)
  :210   return (PPSMC_Result)tmp;
```

### Registros

`asic_reg/smu/smu_7_1_1_d.h` — el que `vi.c:50` incluye:

| registro | offset | dirección |
|---|---|---|
| `mmSMC_MESSAGE_0` | `0x94` | escritura host→SMU |
| `mmSMC_RESP_0`    | `0x95` | lectura SMU→host |

**Adyacentes**, igual que `VM_INVALIDATE_REQUEST` / `VM_INVALIDATE_RESPONSE` en
el dominio de invalidación. Patrón estructural repetido en el mismo ASIC.

> **NOTA DE ALCANCE:** GFX8 **no** usa `smu_8_0_d.h`. `vi.c:50-51` incluye
> `smu/smu_7_1_1_d.h` y `smu/smu_7_1_1_sh_mask.h`; el comentario `/* smu_8_0_d.h */`
> en `vi.c:344` es residual. GFX8 reutiliza el mapa de registros SI/7.x.

### Protocolo de 3 estados en un solo registro

```
ppsmc.h:67   #define PPSMC_Result_OK     ((uint8_t)0x01)
ppsmc.h:68   #define PPSMC_Result_Failed ((uint8_t)0xFF)
ppsmc.h:70   typedef uint8_t PPSMC_Result;
```

| valor | significado | quien lo pone |
|---|---|---|
| `0x00` | **pendiente** — el SMC todavía no terminó | valor inicial |
| `0x01` | OK | firmware |
| `0xFF` | fallido | firmware |

### Tiempos de espera

```
si_smc.c:178-189   1 s : NoForcedLevel, SetEnabledLevels, SetForcedLevels,
                       DisableULV, SwitchToSwState
                 200 ms : resto
comentario :177   "SMC seems to process some messages exceptionally slowly."
```

---

## 2. El producer del nivel de reloj — NO escribe registros

```
si_convert_power_level_to_smc()      si_dpm.c:5520   (declaración en :1857)
  :5532  level->gen2PCIE      = pl->pcie_gen
  :5536  si_populate_sclk_value(adev, pl->sclk, &level->sclk)   ← CALCULA
  :5538  level->mcFlags = 0
  :5545  lee mmDPG_PIPE_STUTTER_CONTROL          ← única lectura, no escritura
  :5551  if (gmc.vram_type == AMDGPU_VRAM_TYPE_GDDR5) {
  :5552      mclk > mclk_edc_enable_threshold      → MC_EDC_RD_FLAG
  :5555      mclk > mclk_edc_wr_enable_threshold    → MC_EDC_WR_FLAG
  :5558      strobeMode = si_get_strobe_mode_settings(adev, pl->mclk)
```

Destino: `SISLANDS_SMC_HW_PERFORMANCE_LEVEL *level` — **estructura de payload**.

```
SI_DPM_WITES_CLOCK_REGISTERS = PROVEN_ABSENT
  en la ruta producer no hay ninguna escritura de registro de reloj
 el unico acceso es RREG32 de stutter control
```

## 3. El chain completo hacia el reloj

```
pl (sclk, mclk, pcie_gen)
  │
  ├─ si_convert_power_level_to_smc()          si_dpm.c:5763
  │     rellena smc_state->levels[i]
  │     .arbRefreshState = SISLANDS_DRIVER_STATE_ARB_INDEX + i      :5766
  │     .displayWatermark = LOW|HIGH                               :5772-5777
  │     .ACIndex = SISLANDS_MCREGISTERTABLE_FIRST_DRIVERSTATE_SLOT+i :5778
  ├─ si_write_smc_soft_register(SI_SMC_SOFT_REGISTER_watermark_threshold,
  │                            threshold / 512)   ◄ UNIT: dividido por 512   :5782
  ├─ si_populate_smc_sp()      serializa el bloque SP     :5791
  ├─ si_populate_smc_t()       termina en copy_bytes_to_smc
  └─ amdgpu_si_copy_bytes_to_smc(adev, address, (u8 *)smc_state, ...)
        └─► SRAM del SMC
              └─► mensaje PPSMC_* por mmSMC_MESSAGE_0 / mmSMC_RESP_0
                    └─► FIRMWARE aplica el reloj
```

**Protocolo de dos fases:** primero subida masiva de tablas a SRAM del SMC,
después el mensaje que ordena actuar. No es un único write.

## 4. Tablas que el driver sube a la SRAM del SMC

```
si_dpm.c:2297,2316   papm_cfg_table_start
si_dpm.c:2628        dte_table_start            ← DTE = Dynamic Voltage Eduction
si_dpm.c:2821        cac_table_start            ← CAC = Current Activity Controller
si_dpm.c:3009        spll_table_start           ← SPLL = reloj
si_dpm.c:4847,5218   (estados de power)
```

`spll_table_start` es la pieza que confirma el punto central: el driver sube una
**tabla de PLL** al SMC en lugar de escribir el divisor.

## 5. Volumen del canal

```
27 llamadas a amdgpu_si_send_msg_to_smc() desde si_dpm.c
```

incluidas:

```
PPSMC_MSG_EnableThermalInterrupt        si_dpm.c:3876
PPSMC_MSG_RunningOnAC                   si_dpm.c:3895
PPSMC_MSG_NoForcedLevel                 si_dpm.c:3911
PPSMC_MSG_EnableDTE / DisableDTE        si_dpm.c:2931 / :2938
PPSMC_MSG_EnableCac / DisableCac        si_dpm.c:2922 / :2940
PPSMC_CACLongTermAvgEnable / Disable    si_dpm.c:2917 / :2945
PPSMC_TDPClampingActive / Inactive      si_dpm.c:2556 / :2561
```

## 6. Interfaz SMC completa (si_smc.c, 301 líneas)

```
:39   si_set_smc_sram_address        dirección de la SRAM del SMC
:53   amdgpu_si_copy_bytes_to_smc    subida masiva
:117  amdgpu_si_start_smc
:126  amdgpu_si_reset_smc
:140  amdgpu_si_program_jump_on_start
:147  amdgpu_si_smc_clock            enable/disable del reloj del propio SMC
:159  amdgpu_si_is_smc_running       precondition de send_msg
:170  amdgpu_si_send_msg_to_smc      ◄ EL MENSAJE
:213  amdgpu_si_wait_for_smc_inactive
:231  amdgpu_si_load_smc_ucode       carga del firmware
:273  amdgpu_si_read_smc_sram_dword
:288  amdgpu_si_write_smc_sram_dword
```

---

## CONEXIÓN CRUZADA con el dominio de invalidación

Es el resultado más útil del turno, y no estaba buscado.

| | SMU | VMID |
|---|---|---|
| registro | `mmSMC_RESP_0` | `mmVM_INVALIDATE_REQUEST` |
| completion | `0x00` = pendiente, `0x01`/`0xFF` = resultado | sin valor de completion documentado |
| primitiva | poll con predicto explícito `!= 0` | `WAIT_REG_MEM FUNCTION=always` (sin comparación) |
| razón | el hardware **da** centinela | el hardware **no da** completion comparable |

```
REGLA_REUTILIZABLE = PROVEN por comparación de dos subsistemas del mismo ASIC
  cuando el hardware expone un valor centinela de "pendiente"  → poll con predicto
  cuando no lo expone                                          → primitiva sin comparación
```

Es la misma forma de problema que `FUNCTION=always` + `mask=0`, y la respuesta
observada en el otro extremo del chip indica qué esperar de cada caso.

---

## Estructuras de datos

```
sislands_smc.h   SISLANDS_MAX_SMC_PERFORMANCE_LEVELS_PER_SWSTATE = 16
                 struct PP_SIslands_Dpm2PerfLevel { MaxPS, TgtAct, MaxPS_StepInc,
                                                    MaxPS_StepDec, PSSamplingTime,
                                                    NearTDPDec, AboveSafeInc,
                                                    BelowSafeInc }
                 (410 líneas; es header de estructuras, NO de offsets de registro)
```

---

## Lo que queda abierto

```
SMC firmware content      NOT_IN_CORPUS   el binario no está en el árbol de kernel
apply-clock-in-firmware   NOT_DETERMINED  la semántica del firmware no es código aquí
voting en CAC / DTE       NOT_READ
limitación de 1 s y 200 ms  CORROBORATED  por comentario del driver, no por medición
```

---

## Fallos nominales que ocurrieron en este turno

| # | Busqué | Realidad | clase |
|---|---|---|---|
| 15º | `asic_smu_funcs` | no existe; el código está en `pm/` | SUBDIRECTORY |
| 16º | `amdgpu_smu_init` | no existe | NAME |
| 17º | `smu_c2p_msg` | es `amdgpu_si_send_msg_to_smc` | NAME |
| 18º | `smu_8_0_d.h` como mapa de GFX8 | `vi.c` usa `smu_7_1_1_d.h` | NAME |
| 19º | `struct amdgpu_vm_manager` / `root_dir` | `vm->root.bo` | NAME |

Todos del mismo tipo: **suponer el subdirectorio o el nombre antes de localizar
por contenido**. Quinta vez que un subdirectorio no inventariado produce un
falso negativo.

```
SUBDIRECTORY_INVENTORY_GATE
  amdgpu/  pm/  pm/legacy-dpm/  pm/powerplay/  pm/swsmu/
  include/asic_reg/{gca,gmc,smu,mmhub}/
  → enumerarlos TODOS antes de concluir NAME_NOT_FOUND
```

---

## Qué desbloquea

```
clock application        PROVEN que lo hace el firmware, no el driver
SMU message channel      PROVEN canal, registros, protocolo de 3 estados
tablas SMC               PROVEN incl. spll (PLL de reloj), dte, cac
sentinel-vs-comparison   PROVEN regla reutilizable de diseño
```

Sigue abierto y es la siguiente pieza: **qué hace el firmware con el payload**,
es decir, el lado que no es código del driver. La ruta estática siguiente es
`si_populate_smc_sp` / `si_populate_smc_t` y el formato SMC packet, que es donde
el payload se serializa.