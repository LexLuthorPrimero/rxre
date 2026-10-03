# 127 · Dos rutas paralelas para el mismo calculo, y la de caida tiene un desplazamiento mal puesto y dos lecturas fuera de limites

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## ALCANCE CERRADO POR `229` (antes `128`) — Ruta B **si** es alcanzable, con overdrive
>
> Este fichero dejo el alcance como `NOT_IN_CORPUS`. **`229` (antes `128`) lo cierra con un numero medido en
> mi VBIOS:**
>
> ```
> ulMaxODEngineClock = 180000  = 1800 MHz   (unidad 10 kHz; el propio driver imprime /100)
> maximo de la tabla dep SCLK  = 1071 MHz   (121)
> ```
>
> **1800 > 1071.** `smu7_check_clk_voltage_valid:5584-5585` acepta el reloj hasta
> `overdriveLimit.engineClock`, y `:4354-4358` mete el reloj del usuario en
> `dpm_table.sclk_table.dpm_levels[].value`. Luego un usuario puede fijar un reloj por encima
> del maximo de la tabla donde se busca, `:369` no encuentra entrada, y **Ruta B se ejecuta**.
>
> **Y la direccion del desbordamiento queda medida**, que era lo que faltaba:
>
> ```
> vdd_dependency_on_sclk = 224   (228 bytes)  -> fin en 452 = vdd_dependency_on_mclk
> vdd_dependency_on_mclk = 452   (228 bytes)  -> fin en 680 = odn_mclk_min_limit
> sizeof(smu7_odn_dpm_table) = 692
>
> entries[8].clk   = 680   <- odn_mclk_min_limit
> entries[8].vddc  = 689   <- byte 1 de max_vddc
> entries[8].mvdd  = 695   <- 3 bytes MAS ALLÁ del fin de la struct
> ```
>
> Con overdrive la tabla **no** es una reserva exacta sino un **array fijo de 8**
> (`MAX_REGULAR_DPM_NUMBER`, `smu7_hwmgr.h:179`), y la copia que lo llena
> (`smu_helper.c:604`) **no comprueba la capacidad**. `:408` lee 689 y `:414` lee **695**.
>
> **Con esto, las dos lecturas fuera de limite de este hallazgo tienen direccion concreta, y la
> afirmacion «28 bytes pasado del final» se precisa: 3 bytes fuera de `smu7_odn_dpm_table`, sin
> fallo de pagina porque la struct esta embebida en `smu7_hwmgr`.**

**Comparacion linea a linea de las dos rutas de `polaris10_get_dependency_volt_by_clk`
(`polaris10_smumgr.c:353`). Una esta bien. La otra, no. El codigo es mio para reescribir, asi
que la comparacion es util: es exactamente el tipo de codigo que yo no quiero escribir.**

## La funcion

```c
/* polaris10_smumgr.c:353 */
static int polaris10_get_dependency_volt_by_clk(struct pp_hwmgr *hwmgr,
                struct phm_ppt_v1_clock_voltage_dependency_table *dep_table,
                uint32_t clock, SMU_VoltageLevel *voltage, uint32_t *mvdd)
```

Su trabajo: dado un reloj, devolver el voltaje de la entrada de la tabla de dependencia mas
cercana. Empaqueta tres campos en una palabra (`092`; los desplazamientos son identicos en
`smu73.h`, `smu74.h` y `smu75.h`):

```c
#define VDDC_SHIFT   0
#define VDDCI_SHIFT  15
#define PHASES_SHIFT 30
#define VOLTAGE_SCALE 4        (hwmgr.h:38)
```

## Ruta A: se encuentra una entrada (`:367-394`) — CORRECTA

```c
for (i = 0; i < dep_table->count; i++) {
        if (dep_table->entries[i].clk >= clock) {
                *voltage |= (dep_table->entries[i].vddc  * VOLTAGE_SCALE) << VDDC_SHIFT;   /* 370 */
                if (NONE == data->vddci_control)
                        *voltage |= (...vddci_bootup_value... * VOLTAGE_SCALE) << VDDCI_SHIFT; /* 373 */
                else if (dep_table->entries[i].vddci)
                        *voltage |= (...vddci... * VOLTAGE_SCALE) << VDDCI_SHIFT;          /* 377 */
                else
                        *voltage |= (vddci * VOLTAGE_SCALE) << VDDCI_SHIFT;                /* 382 */
                if (NONE == data->mvdd_control)  *mvdd = ...;                              /* 385 */
                else if (entries[i].mvdd)        *mvdd = entries[i].mvdd * VOLTAGE_SCALE;  /* 389 */
                *voltage |= 1 << PHASES_SHIFT;                                             /* 392 */
                return 0;
        }
}
```

Tres campos en su sitio, `PHASES` activado, y `entries[i]` con `i < count`.

## Ruta B: el reloj supera el maximo de la tabla (`:396-417`) — DEFECTUOSA

```c
/* sclk is bigger than max sclk in the dependence table */
*voltage |= (dep_table->entries[i - 1].vddc * VOLTAGE_SCALE) << VDDC_SHIFT;   /* 398  bien */
if (NONE == data->vddci_control)
        *voltage |= (...vddci_bootup_value... * VOLTAGE_SCALE) << VDDCI_SHIFT; /* 401  bien */
else if (dep_table->entries[i-1].vddci) {
        *voltage |= (entries[i-1].vddci * VOLTAGE_SCALE) << VDDC_SHIFT;       /* 404  MAL */
} else {
        vddci = phm_find_closest_vddci(&(data->vddci_voltage_table),
                        (dep_table->entries[i].vddc - VDDC_VDDCI_DELTA));       /* 408  FUERA */
        *voltage |= (vddci * VOLTAGE_SCALE) << VDDCI_SHIFT;                     /* 409  bien */
}
if (NONE == data->mvdd_control)
        *mvdd = ...vddci_bootup...;
else if (dep_table->entries[i].mvdd)                                            /* 414  FUERA */
        *mvdd = dep_table->entries[i - 1].mvdd * VOLTAGE_SCALE;                  /* 415 */
return 0;                                                                        /* 417 */
```

Y **falta** el `*voltage |= 1 << PHASES_SHIFT;` que Ruta A tiene en `:392`.

**Tras el bucle, `i == dep_table->count`.** Eso convierte las tres referencias a
`entries[i]` en **lecturas un registro pasado del final**.

## Los cuatro defectos, uno por uno

### 1. `:404` escribe VDDCI en el campo de VDDC

```c
:377   *voltage |= (dep_table->entries[i].vddci * VOLTAGE_SCALE) << VDDCI_SHIFT;   /* Ruta A */
:404   *voltage |= (dep_table->entries[i-1].vddci * VOLTAGE_SCALE) << VDDC_SHIFT;  /* Ruta B */
```

**Misma operacion, una linea de distancia, constante distinta.** `092` ya habia measured
`VDDC_SHIFT=0` y `VDDCI_SHIFT=15`.

Lo que produce, con `count` = 8 entradas de mi placa:

- bits 0-14 = `(vddc_max * 4)` **OR** `(vddci * 4)` — **los dos voltajes mezclados y
  contaminados**, porque `|=` no es `=`
- bits 15-29 = **0** — el campo VDDCI queda **vacio**
- bits 30-31 = **0** — `PHASES` sin activar, frente al `1` de Ruta A

**Un campo de voltaje a cero se le entrega al SMC, con otro voltaje OR'eado encima.**

- `SHIFT_MAL_PUESTO_EN_404 = PROVEN`: `VDDC_SHIFT` donde la ruta paralela usa `VDDCI_SHIFT`.
- `SE_ADJUNTAN_DOS_VOLTAJES_EN_LOS_MISMOS_15_BITS = PROVEN_DERIVED`: `|=` sobre el mismo
  campo.
- `EL_CAMPO_VDDCI_QUEDA_A_CERO = PROVEN_DERIVED`: nada escribe en los bits 15-29.
- `PHASES_NO_SE_ACTIVA_EN_RUTA_B = PROVEN`: `:392` existe, en Ruta B no.

### 2. y 3. Dos lecturas fuera de limites, a 28 bytes del final

```c
:408   dep_table->entries[i].vddc     /* i == count */
:414   dep_table->entries[i].mvdd     /* i == count */
```

La tabla se reserva **exactamente** `count` registros:

```c
/* process_pptables_v1_0.c:417 */
sclk_table = kzalloc_flex(*sclk_table, entries, tonga_table->ucNumEntries);
```

y `entries[]` es un **miembro de tamaño flexible** (`hwmgr_ppt.h:51`), no un array de tamano
fijo. O sea: `entries[count]` es un registro entero mas alla del final de la reserva.

Medido con gcc, porque el tamano importa y no quiero estimarlo:

```
registro empaquetado: 24 bytes
registro SIN empacar : 28 bytes   <-- el que vale
```

**`hwmgr_ppt.h` no tiene ningun `#pragma pack`** (0 coincidencias de `pack`). El lado VBIOS si
lo tiene (`pptable_v1_0.h:30`), por eso `121` mide un paso de 15 bytes alli y el struct interno
ocupa **28**.

**La lectura se sale 28 bytes de una reserva de `count * 28`.**

- `ENTRIES_ES_TAMANO_FLEXIBLE = PROVEN`: `hwmgr_ppt.h:51`.
- `LA_RESERVA_ES_EXACTAMENTE_COUNT_REGISTROS = PROVEN`: `kzalloc_flex(..., ucNumEntries)` (`:417`).
- `I_ES_IGUAL_A_COUNT_TRAS_EL_BUCLE = PROVEN`: `for (i = 0; i < dep_table->count; i++)`.
- `SE_LEEN_28_BYTES_PASTA_EL_FINAL = PROVEN`: registro de 28 bytes, sin `pack`.
- `LA_LECTURA_EN_408_SOLO_OCURRE_SI_VDDCI_CONTROL_NO_ES_NONE_Y_LA_ENTRADA_ANTERIOR_TIENE_VDDCI_CERO
  = PROVEN_DERIVED`
- `LA_LECTURA_EN_414_SOLO_OCURRE_SI_MVDD_CONTROL_NO_ES_NONE = PROVEN_DERIVED`

**Y hay un detalle que explica por que nadie lo ha visto:** el struct del VBIOS **si**
lleva la anotacion de limite, y el interno **no**.

```c
/* pptable_v1_0.h:197 — struct del VBIOS */
ATOM_Tonga_SCLK_Dependency_Record entries[] __counted_by(ucNumEntries);

/* hwmgr_ppt.h:51 — struct interno, el que usa el codigo */
phm_ppt_v1_clock_voltage_dependency_record entries[];      /* sin __counted_by */
```

**El compilador solo puede avisar de lo que tiene anotado.** El codigo que se pasa de rango
opera sobre la copia interna, que no lleva `__counted_by`, asi que la lectura es legal para el
analizador estatico.

> **`__counted_by` es la anotacion que convierte una lectura fuera de limites en un aviso de
> compilacion.** El struct de entrada la tiene; el de trabajo, no. Es el mismo patron de `226` (antes `124`)
> — una frontera segura por construccion en un lado y sin nada en el otro.

### El patron que lo causo todo

Ruta A usa `entries[i]` en **condicion y cuerpo**. Ruta B, al cambiar el contexto a
`i == count`, **cambio el operando del `if` a `i` pero dejo el del cuerpo en `i - 1`**:

```c
:414   else if (dep_table->entries[i].mvdd)          /* condicion: i   */
:415       *mvdd = dep_table->entries[i - 1].mvdd    /* cuerpo:    i-1 */
```

Dos indices distintos en la misma sentencia. Uno de los dos tiene que estar mal, y en este
caso los dos.

## Alcanzabilidad: cuando corre esto en mi ASIC

Ruta B exige `clock > entries[count-1].clk`, es decir **un reloj por encima del maximo de la
tabla**.

**Con overdrive desactivado (por defecto), NO corre, y se demuestra por construccion:**

```c
/* polaris10_smumgr.c:1067-1071 */
for (i = 0; i < dpm_table->sclk_table.count; i++) {
        result = polaris10_populate_single_graphic_level(hwmgr,
                dpm_table->sclk_table.dpm_levels[i].value,   /* el reloj es un nivel DPM */
                &(smu_data->smc_state_table.GraphicsLevel[i]));
```

Y dentro, la tabla contra la que se busca es `table_info->vdd_dep_on_sclk`. Pero
`smu7_setup_dpm_tables_v1` **copia cada entrada aceptada de esa misma tabla a
`dpm_levels[count]`**. O sea que **el valor de cada nivel DPM proviene de una entrada de la
tabla donde se busca**, y `entries[i].clk >= clock` se cumple en la primera coincidencia.
**Ruta A siempre gana.**

- `RUTA_B_NO_SE_ALCANZA_SIN_OVERDRIVE = PROVEN_DERIVED`: por construccion, no por dato.
- `CON_OVERDRIVE_LA_BUSQUEDA_CAMBIA_DE_TABLA = PROVEN`: `:969-972` y `:1164-1167` eligen
  `data->odn_dpm_table` cuando `hwmgr->od_enabled`.
- `CON_OVERDRIVE_EL_ALCANCE_NO_LO_PUEDO_DECIDIR = NOT_IN_CORPUS`: hace falta saber si un nivel
  DPM de overdrive puede superar el maximo de la tabla de dependencia de overdrive. No tengo
  datos de OD.

Los otros dos llamadores usan relojes de arranque, no parametros: `:1293` con
`sclk_bootup_value` y `:1328` con `mclk_bootup_value`. **No he medido esos dos valores en el
VBIOS**, asi que **no afirmo nada sobre ellos**: quedan abiertos.

## Y una correccion a mi propio razonamiento

En `228` (antes `126`) observe que el cap `ControlVDDCI` **si** esta activo en mi placa, porque el bit 15
(`ATOM_TONGA_PP_PLATFORM_CAP_VDDCI_CONTROL = 0x8000`) esta en `ulPlatformCaps = 0x068000` y
`set_platform_caps:94-96` lo traduce.

**Eso elimina la unica via por la que yo creia bloqueado el defecto de `:404`.** Si
`vddci_control != NONE`, la rama de `:403` es alcanzable, y con ella el desplazamiento mal
puesto y la lectura fuera de limites de `:408`.

Lo que **no** cambia: la condicion de entrada es `clock > maximo de la tabla`, y sin
overdrive eso no ocurre. **El defecto sigue sin ejecutarse en mi placa, pero por una razon mas
debil de la que yo suponia**: no porque el voltaje este bloqueado, sino porque el reloj nunca
supera la tabla.

## Clasificacion

- `SHIFT_MAL_PUESTO_EN_404 = PROVEN`
- `EL_CAMPO_VDDCI_QUEDA_A_CERO_Y_PHASES_TAMBIEN = PROVEN_DERIVED`
- `DOS_LECTURAS_FUERA_DE_LIMITAS_EN_408_Y_414 = PROVEN`
- `LA_RESERVA_ES_DE_COUNT_REGISTROS_EXACTAMENTE = PROVEN`: `kzalloc_flex` (`:417`)
- `SE_LEEN_28_BYTES_PASTA_EL_FINAL = PROVEN`: registro de 28 bytes, `hwmgr_ppt.h` sin `pack`
- `EL_STRUCT_VBIOS_TIENE_COUNTED_BY_Y_EL_INTERNO_NO = PROVEN`: `pptable_v1_0.h:197` frente a
  `hwmgr_ppt.h:51`
- `CONDICION_Y_CUERPO_USAN_INDICES_DISTINTOS = PROVEN`: `:414` con `i`, `:415` con `i-1`
- `RUTA_B_NO_SE_ALCANZA_SIN_OVERDRIVE = PROVEN_DERIVED`: por construccion
- `EL_ALCANCE_CON_OVERDRIVE_ES_NOT_IN_CORPUS`: no tengo datos de OD
- `LOS_RELOJES_DE_ARRANQUE_NO_ESTAN_MEDIDOS = EVIDENCE_MISSING`: `:1293` y `:1328`
- `MI_BLOQUEO_POR_VDDCI_CONTROL_ERA_FALSO = CORRECTED`: `228` (antes `126`) lo refuta

## Lo que esto obliga a hacer en un driver propio

1. **Dos rutas para el mismo calculo se comparan, o no existen.** Ruta A y Ruta B differen en
   cuatro puntos y **solo una estaba bien**. Es el coste de mantener el caso borde separado del
   caso normal.
2. **El caso borde se prueba con el MISMO contrato que el caso normal.** Aqui el contrato es
   «los tres campos en su sitio y `PHASES` activado», y Ruta B no lo cumple.
3. **`__counted_by` en todas las estructuras de tamano flexible.** Sin la anotacion, un
   `entries[count]` es indistinguible de un acceso legitimo. Es gratis y avisa en compilacion.
4. **Un indice derivado de un bucle no sobrevive a la salida del bucle.** Tras
   `for (i = 0; i < count; i++)`, `i == count`, y cualquier `entries[i]` se sale. Si hace
   falta el ultimo elemento, **hay que guardarlo dentro del bucle**.
5. **Y condicion y cuerpo tienen que usar el mismo indice.** `:414` y `:415` usan `i` e
   `i-1`; uno de los dos esta mal y aqui los dos lo estan. Es la forma mas barata de tener un
   error y la mas dificil de ver.

## Estado

Hallazgo **127** con su alcance medido: **el defecto existe en el codigo y no se ejecuta en mi
placa sin overdrive**, por construccion y no por casualidad.