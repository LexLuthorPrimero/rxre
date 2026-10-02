# 046 · CORRECCIÓN: 040-045 describen una ruta que NO se compila para Polaris12

`CLASSIFICATION=CONTRADICTION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`SCOPE_CLAIM=.write-lock/smu`
`CORRECTS=040,041,042,043,044,045`

---

## Qué ocurrió

Al cerrar la cadena del reloj en 045 no comprobé **qué implementación de DPM
compila realmente** para Polaris12. Documenté `pm/legacy-dpm/si_dpm.c` y
`si_smc.c` asumiendo que eran la ruta activa. **No lo son.**

```
legacy-dpm/Makefile:4   LEGACYDPM_MGR-$(CONFIG_DRM_AMDGPU_SI)+= si_dpm.o si_smc.o
```

`si_dpm.c` y `si_smc.c` se compilan **exclusivamente** con `CONFIG_DRM_AMDGPU_SI`.

```
amdgpu/Kconfig:42-51   config DRM_AMDGPU_SI
                        "Enable amdgpu support for SI parts"
                        "SI (Southern Islands) are first generation GCN GPUs"
```

Polaris12 es **Volcanic Islands**, no Southern Islands. Los únicos configs ASIC
del Kconfig son `DRM_AMDGPU_SI` y `DRM_AMDGPU_CIK`; **no existe
`DRM_AMDGPU_VI`**, porque VI está siempre activo y no se compila por
`legacy-dpm`.

```
SI_DPM_COMPILED_FOR_POLARIS12 = PROVEN_ABSENT
  evidencia: Makefile:4  +  Kconfig:42-51
  no es un negativos por búsqueda: es el gate de compilación explícito
```

## La ruta real de Polaris12

```
pm/powerplay/hwmgr/hwmgr.c:131     case AMDGPU_FAMILY_VI:
pm/powerplay/hwmgr/hwmgr.c:154-158
    case CHIP_POLARIS11:
    case CHIP_POLARIS10:
    case CHIP_POLARIS12:
        hwmgr->smumgr_funcs = &polaris10_smu_funcs;
        polaris_set_asic_special_caps(hwmgr);
        hwmgr->feature_mask &= ~(PP_UVD_HANDSHAKE_MASK);
        break;
pm/powerplay/hwmgr/hwmgr.c:122     smu7_init_function_pointers(hwmgr);
pm/powerplay/smumgr/polaris10_smumgr.c:2681   polaris10_smu_funcs
pm/powerplay/hwmgr/smu7_hwmgr.c:5938           smu7_init_function_pointers
```

**PowerPlay con la familia smu7, no legacy-dpm.** Y `smu8_hwmgr.c` /
`smu8_smumgr.c` tampoco participan: el selector usa `polaris10_smu_funcs`.

## Qué sobrevive y qué no

| documento | contenido | estado para Polaris12 |
|---|---|---|
| 040 | canal `mmSMC_MESSAGE_0` / `mmSMC_RESP_0` | **CONCEPTO VIVO**, función distinta |
| 041 | curva `r600_calculate_at`, banda A-T | **NO EXISTE** en la ruta activa |
| 042 | formato de wire A-T, `CG_AT__CG_R`/`CG_L` | **NO EXISTE** |
| 043 | PLL `r600_calculate_u_and_p`, `bsp` | **NO EXISTE** |
| 044 | `xclk` con 5 caminos, `asi`/`pasi` | **NO EXISTE** como divisor PLL |
| 045 | "cadena completa del reloj" | **CADENA EQUIVOCADA** |

Comprobación directa sobre la ruta activa:

```
smu7_hwmgr.c   calculate_at          0 ocurrencias
               calculate_u_and_p     0 ocurrencias
               bsp                   0 ocurrencias
               ClockVoltageDependency 0 ocurrencias
               xclk                  1  ← pero para DISPLAY TIMING, no PLL
```

```
smu7_hwmgr.c:4683   ref_clock = amdgpu_asic_get_xclk(...);
smu7_hwmgr.c:4684   refresh_rate = hwmgr->display_config->vrefresh;
smu7_hwmgr.c:4689   frame_time_in_us = 1000000 / refresh_rate;
```

El único uso de `xclk` en la ruta activa es para **timing de display**, no para
el divisor del PLL.

## El modelo real es otro: tablas de voltaje

```
polaris10_smumgr.c:664   polaris10_populate_smc_mvdd_table()    memoria
polaris10_smumgr.c:691   polaris10_populate_smc_vddc_table()   nucleo
polaris10_smumgr.c:716   polaris10_populate_smc_vddci_table()   I/O
polaris10_smumgr.c:230   smu7_send_msg_to_smc_offset(hwmgr)
polaris10_smumgr.c:102   smum_send_msg_to_smc_with_parameter(hwmgr, PPSMC_MSG_PerformBtc, ...)
polaris10_smumgr.c:131   smu7_read_smc_sram_dword(hwmgr, ...)
```

La ruta Polaris organiza el control de energía alrededor de **tablas de voltaje**
por dominio, no de curvas de histéresis. El mecanismo de mensaje **es el mismo
concepto** —escritura en `0x94`, poll a `0x95`— pero con otra función y otro
formato de payload.

## Lo que sí es transferible

```
1. EL CANAL DE MENSAJES
   el concepto de 040 es correcto; hay que reubicarlo en la función real
   smu7_send_msg_to_smc_offset / smum_send_msg_to_smc_with_parameter

2. LA CONEXIÓN CON EL DOMINIO INVALIDATE
   la regla "centinela explícito → poll con predicto; sin centinela →
   primitiva sin comparación" sigue siendo válida como regla de diseño.
   No depende de qué fichero la contenga.

3. EL VBIOS MIENTE
   vi.c:546 "vbios says 48Mhz, but the actual freq is 100Mhz"
   aplica igual: clock.spll.reference_freq no es garantía

4. LAS REGLAS METODOLÓGICAS
   SUBDIRECTORY_INVENTORY_GATE, GREP_FILTER_FALSELY_NEGATIVE,
   GREP_TOO_SPECIFIC_AS_ABSENCE, OUT_PARAMETER_NOT_IN_ASSIGNMENT_SEARCH
   y ahora la nueva:
   
   COMPILE_GATE_BEFORE_TRACE_GATE
     verificar en el Makefile y el Kconfig que el fichero que se va a trazar
     se compila para el ASIC objetivo, ANTES de gastar N hallazgos en él
```

La quinta es la que faltó y es la causa directa de este error. Trazar un fichero
correcto, con toda la evidencia correcta, sobre un fichero que no entra en el
build produce documentos internally consistentes y operacionalmente inútiles.

## Corrección de proceso

El error no fue de lectura ni de búsqueda. Fue de **no verificar el gate de
compilación** antes de invertir esfuerzo. `legacy-dpm/Makefile:4` era una línea y
responde exactamente a la pregunta que hacía falta.

```
REGLA: antes de trazar, responder
  ¿este .c se compila para mi ASIC?
    → grep en el Makefile correspondiente
    → grep del CONFIG en el Kconfig
  Si no se compila: documentar como REFERENCIA_DE_GENERACION, no como ruta activa.
```

## Siguiente tarea correcta

Rehacer el scope `smu` sobre la ruta real:

```
1. smu7_send_msg_to_smc_offset / smum_send_msg_to_smc_with_parameter
   → confirmar que el canal 0x94/0x95 y el centinela 0x00 son los mismos
2. polaris10_populate_smc_{mvdd,vddc,vddci}_table
   → el modelo de energía real de Polaris12
3. smu7_hwmgr.c: donde se aplica el nivel de voltaje al hardware
4. la ruta de reloj real: ¿dónde está en smu7/polaris lo que en SI era si_dpm.c?
```

El punto 4 es el que realmente importa y es el que 043/044 intentaban responder
por el camino equivocado.

---

```
COSTO DE ESTE ERROR
  6 documentos, ~1250 líneas, sobre una ruta que no entra en el build
  TODO el contenido técnico es correcto para SI
  NADA de ello describe el comportamiento de Polaris12
  lo único que sobrevive intacto: el canal de mensajes como concepto,
  y las cinco reglas metodológicas

  Esto no invalida 040-045 como REFERENCIA DE GENERACIÓN:
  Tonga, Fiji, Carrizo y Stoney sí usan esa ruta, y el modelo es la misma
  familia GCN. Para un driver propio que quiera soportar también SI,
  esos documentos siguen siendo válidos y no duplicables.
```