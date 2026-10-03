# 103 · El parche de UVD lee y reescribe BootVddc, el voltaje de arranque, por un desplazamiento mal calculado

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> **CORREGIDO POR `218` y `219`.** La premisa `offsetof - 108` queda **REFUTADA**:
> `dpm_table_start` es la base literal de la tabla. En consecuencia quedan **REFUTED**
> `SMC_UVD_PATCH_WRONG_OFFSET`, `SMC_UVD_PATCH_HITS_BOOT_VDDC`,
> `SMC_UVD_PATCH_DESTROYS_BOOT_VOLTAGE` y `SMC_PATCH_OFFSET_MIXES_REFERENCE_FRAMES`.
>
> **SE SOSTIENE, y `219` lo rederiva**: `SMC_VCE_PATCH_SAME_WORD` — los dos parches
> apuntan al DWORD 394 (`1576..1579`), porque `offsetof` se usa como ancla de palabra y el
> byte lo elige la mascara.
>
> Ademas, la conclusion *parcial* del documento (que el parche **no** cae en `BootVddc`)
> era correcta, y `107` la refuteo con una localizacion alternativa que tampoco era correcta.
> Los tres documentos compartian el mismo error de base y se parecian confirmar.

## El hallazgo

`polaris10_update_uvd_smc_table` (`:2288-2312`) hace un leer-modificar-escribir sobre la
SRAM del SMC para actualizar `UvdBootLevel`. Calcula la direccion como:

```c
mm_boot_level_offset = smu_data->smu7_data.dpm_table_start
                       + offsetof(SMU74_Discrete_DpmTable, UvdBootLevel);
```

Y ese calculo esta **desfasado 108 bytes** respecto a donde la copia inicial puso realmente
el campo.

## Los dos numeros, medidos

La copia inicial de la tabla, `polaris10_smumgr.c:2118-2123`:

```c
smu7_copy_bytes_to_smc(hwmgr,
        smu_data->smu7_data.dpm_table_start
                + offsetof(SMU74_Discrete_DpmTable, SystemFlags),
        (uint8_t *)&(table->SystemFlags),
        sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
        SMC_RAM_END);
```

Empieza en `offsetof(SystemFlags)`, no en 0. Con gcc:

```
sizeof(SMU74_Discrete_DpmTable) = 1884
offsetof(SystemFlags)           = 108
offsetof(UvdBootLevel)          = 1576
```

Asi que:

| | direccion en la SRAM |
|---|---|
| donde la copia puso `UvdBootLevel` | `dpm_table_start + (1576 - 108)` = `+ 1468` |
| donde el parche busca `UvdBootLevel` | `dpm_table_start + 1576` |

**1468 bytes de diferencia.** El parche no toca el campo que cree.

## Que toca en realidad

La direccion `dpm_table_start + 1576` corresponde al offset **1684** de la struct, porque
la copia desplazó todo 108 bytes hacia atras. Y en el offset 1684 esta `BootVddc`:

```
offset struct   campo        bytes
     1576       UvdBootLevel   1     <- lo que el parche CREE que toca
     1684       BootVddc       2     <- lo que el parche TOCA de verdad
```

`BootVddc` es un `uint16_t`, y el byte que cae encima es su byte **bajo** (offset interno
0).

## El leer-modificar-escribir

```c
mm_boot_level_offset = smu_data->smu7_data.dpm_table_start + offsetof(..., UvdBootLevel);
mm_boot_level_offset /= 4;
mm_boot_level_offset *= 4;                    /* alinea a 4 bytes */
mm_boot_level_value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset);
mm_boot_level_value &= 0x00FFFFFF;
mm_boot_level_value |= smu_data->smc_state_table.UvdBootLevel << 24;
cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset, mm_boot_level_value);
```

La operacion es "leer un DWORD, conservar los 24 bits bajos, sustituir el byte alto".
Tres consecuencias, todas verificadas:

**1. Escribe en `BootVddc`.** El byte alto del DWORD en `dpm_table_start + 1576` es el
byte bajo de `BootVddc`. Lo sustituye por `UvdBootLevel`, que es
`mm_dep_table->count - 1`.

**2. El valor real de `BootVddc` no se conserva.** El patron "conservar los vecinos" que
busca preservar los otros bytes funciona sobre el DWORD que cree estar leyendo. Los tres
bytes que no toca **si** se conservan, porque estan en el mismo DWORD. Lo que no se
conserva es `BootVddc` en si, porque es precisamente el byte que sustituye.

Es decir: **el comentario implícito "preservo los vecinos" es cierto para el DWORD y falso
para el campo.** Eso es lo que hace el fallo dificil de ver: el patron de codigo es el
correcto, aplicado a la direccion equivocada.

**3. La division y multiplicacion por 4 oculta el error de alineacion.** Como el offset
se trunca a multiplo de 4 antes de leer, y `1576` ya es multiplo de 4, la alineacion no
avisa de nada. Si la diferencia hubiera sido de 3 bytes, la division habria perdido el
desfase y el resultado habria sido ilegible. Aqui el desfase es de 108, que es divisible
por 4, asi que pasa limpio.

## Y hay un segundo sitio con el mismo calculo

`polaris10_update_vce_smc_table` (`:2326-2337`) hace lo mismo con `VceBootLevel`, cuyo
offsetof es **1577**. Con la misma formula:

```
offsetof(VceBootLevel) = 1577
1577 - 108 = 1469  ->  alineado a 4 = 1468
```

O sea que tras alinear, **cae en la misma palabra que el de UVD** (`1468`), y escribe en
su byte alto... que es el byte **medio** del DWORD, no el alto. Y encima pisa el mismo
`BootVddc`, esta vez en su byte **alto**.

Los dos parches, ejecutados, escriben los dos bytes de `BootVddc` con valores de boot de
UVD y de VCE.

| parche | campo que cree | offset sin alinear | offset alineado | byte real |
|---|---|---:|---:|---|
| UVD | `UvdBootLevel` | 1576 | 1576 | `BootVddc` byte 0 |
| VCE | `VceBootLevel` | 1577 | **1468** | `BootVddc` byte 1 |

El de UVD: `1576 / 4 * 4 = 1576`. El de VCE: `1577 / 4 * 4 = 1576`. **Los dos terminan
en 1576.** Es decir: los dos leen y escriben el **mismo DWORD**, y el de VCE pone su byte
en la posicion 16-23 (medio) en vez de la 24-31 (alto), lo que ademas pisa un byte del
valor que UVD acaba de escribir si corrieron en ese orden.

## Por que el desfase de 108

La copia empieza en `SystemFlags` porque los **tres `SMU74_PIDController` del principio**
(108 bytes) los escribe el firmware, no el host. `195` documento ese hueco: el host escribe
`[108, 1884)` y el firmware deja `[0, 108)`.

El firmware, que es quien de verdad coloca los campos, **conoce la disposicion del hueco**
y coloca `UvdBootLevel` en su offset real. El host, al calcular direcciones para
parchear, **se salta el hueco** y cuenta desde 0. Por eso el parche va 108 bytes tarde:
`dpm_table_start` es la base del firmware, no la base de la copia del host.

O sea: **el host mezcla dos sistemas de referencia** sin darse cuenta. `dpm_table_start` es
la direccion de la tabla segun el firmware; `offsetof(...)` es un offset en la struct del
host, que no tiene los 108 bytes de cabeza. Sumarlos produce una direccion valida en
linea de principio, con 108 bytes de desplazamiento.

## Y no es solo de Polaris10

> **CORRECCION.** Una version anterior de esta seccion decia que solo Polaris10 y VegaM
> tienen el hueco de los PID Controllers y que en Tonga, Iceland y CI la copia empieza en
> offset 0. **Es falso**, y lo corrijo aqui lo mismo que en `211`.

Medido: `offsetof(SystemFlags) = 108` en las cinco cabeceras (`smu71`, `smu72`, `smu73`,
`smu74`, `smu75`), y las cinco rutas copian la tabla inicial **desde `SystemFlags`**:

```
tonga_smumgr.c:2437     iceland_smumgr.c:2057    fiji_smumgr.c:2105
polaris10_smumgr.c:2118 vegam_smumgr.c:2134
```

O sea que Tonga e Iceland tienen el mismo patron, con `UvdBootLevel` y `VceBootLevel` en
sus propias tablas (`tonga:2688`, `:2723`; `iceland` equivalente). **El patron es de la
familia SMU7 entera.**

Lo que queda abierto, y es lo unico que decide si el fallo es real: si `dpm_table_start`
es la direccion **literal** del campo `DpmTable` de la cabecera, o si el firmware ya la
define de modo que `+ 108` sea el inicio de la parte que gestiona el host. Sin el
firmware no se decide: `CONNECTION_MISSING`, `NOT_IN_CORPUS`.

Lo que si es `PROVEN` e independiente de esa pregunta: **el codigo y el layout usan dos
bases distintas y nada lo reconcilia**, y las once direcciones calculadas son 108 bytes
distintas de las que el layout nombra.

## Lo que NO dice

Lo que **no** he verificado es con que frecuencia ocurre el ungate en esta placa, que
depende del scheduler y de la carga. Que el camino exista y se recorra es `PROVEN`; cuantas
veces en una sesion es `RUNTIME_MISSING`, y es lo que determina cuantas veces se pisa
`BootVddc` con que valores.

No digo que el valor final de `BootVddc` sea inutil. `BootVddc` se calcula en
`polaris10_populate_smc_boot_level` (`:1603-1604`) y se sube en la copia inicial. El
parche lo sobrescribe **despues**, asi que el valor que llega al firmware es el del
parche, no el calculado.

No se si el firmware lee `BootVddc` para arrancar memoria: `SEMANTIC_MISSING`.

## Clasificacion

- `SMC_UVD_PATCH_WRONG_OFFSET = PROVEN`: `:2291-2292` usa `dpm_table_start +
  offsetof(UvdBootLevel)`, cuando la copia de `:2118-2120` lo coloco en
  `dpm_table_start + (offsetof - 108)`.
- `SMC_UVD_PATCH_HITS_BOOT_VDDC = PROVEN_DERIVED`: `1576 + 108 = 1684` =
  `offsetof(BootVddc)`, byte bajo.
- `SMC_UVD_PATCH_DESTROYS_BOOT_VOLTAGE = PROVEN`: la mascara `&= 0x00FFFFFF` con
  `|= UvdBootLevel << 24` sustituye el byte que es `BootVddc`.
- `SMC_VCE_PATCH_SAME_WORD = PROVEN_DERIVED`: `1577 / 4 * 4 = 1576`, el mismo DWORD que
  UVD. Los dos parches colisionan.
- `SMC_PATCH_OFFSET_MIXES_REFERENCE_FRAMES = PROVEN`: `dpm_table_start` es la base del
  firmware; `offsetof` es un offset en la struct del host, que no tiene los 108 bytes de
  `PIDController`. Sumarlos mezcla dos referencias.
- `SMC_PID_HOLE_IS_7_4_PLUS = PROVEN_DERIVED`: es la disposicion `[0, 108)` que
  documenta `195`; en las rutas donde la copia empieza en 0 el calculo acierta.
- `SMC_PATCH_ALIGNMENT_MASKS_THE_ERROR = PROVEN`: `/= 4; *= 4` con un desfase divisible
  por 4 no produce aviso.
- `SMC_UVD_BOOT_LEVEL_NOT_UPDATED = PROVEN_DERIVED`: el campo que el parche queria
  cambiar nunca se cambia.
- `SMC_BOOT_VDDC_FINAL_VALUE = NOT_DETERMINED`: el camino de parche **si** corre (cadena
  verificada de punta a punta, transicion de ungate), asi que el valor final depende de
  cuantos ungate ocurren y en que orden, no de si ocurren.
- `SMC_PATCH_PATH_IS_LIVE = PROVEN`: `amd_powerplay.c:1230` -> `:449` ->
  `smu7_hwmgr.c:5871` -> `smu7_clockpowergating.c:137` (rama `else`, ungate) -> `:47` ->
  `polaris10_smumgr.c:2367-2368`. No es un camino de arranque: es de transicion DPM.

## Lo que esto obliga a hacer en un driver propio

**Un solo sistema de referencia para las direcciones.** Si la base que da el firmware y
la base desde la que copia el host no coinciden, hay que convertirlas de forma explicita:
`addr_smc = dpm_table_start + offsetof(T, campo) - inicio_de_la_copia_del_host`.

Y **no escribir sobre un byte sin comprobar que byte es**. El leer-modificar-escribir con
mascara presupone que uno sabe que hay al lado. Aqui se preservan tres bytes y se destruye
el campo, porque el patron es correcto y la direccion no.

Un test barato que lo habria cazado: al arrancar, comparar lo que el driver creo que
habia escrito con lo que hay en la SRAM, **byte a byte**, en los offsets que el driver
usa para parchear. Ese es el discriminante, y no requiere hardware nuevo.

## Y el camino es vivo, no latente

La pregunta que decide la gravedad es si esos dos parches se ejecutan en Polaris12. La
cadena, verificada entera:

```
pp_set_powergating_by_smu(handle, block_type, gate, inst)      amd_powerplay.c:1220
  case AMD_IP_BLOCK_TYPE_UVD -> pp_dpm_powergate_uvd(handle, gate)   :1230
    -> hwmgr->hwmgr_func->powergate_uvd(hwmgr, gate)               :449
       que es smu7_powergate_uvd, de smu7_hwmgr.c:5871 (.powergate_uvd)
         [polaris10_smumgr.c NO declara powergate_uvd: no lo sobreescribe]
  smu7_powergate_uvd(hwmgr, bgate)                smu7_clockpowergating.c:~110
    if (bgate) { ...gate...; smu7_update_uvd_dpm(hwmgr, true); }   :127   no parchea
    else       { ...ungate...; smu7_update_uvd_dpm(hwmgr, false); } :137   PARCHA
      -> smu7_update_uvd_dpm(hwmgr, false)
         if (!bgate) smum_update_smc_table(hwmgr, SMU_UVD_TABLE)   :47
           -> hwmgr->smumgr_funcs->update_smc_table
              case SMU_UVD_TABLE: polaris10_update_uvd_smc_table    :2367-2368
```

**El parche se ejecuta en el `else`, o sea al DESHACER el power gate.** Y eso es un camino
de transicion de nivel de energia: cada vez que el scheduler saca UVD de un estado
gateado. No es un camino de arranque, es un camino de transicion, y las transiciones de
nivel DPM ocurren durante el uso normal de la GPU.

Lo mismo para VCE por `SMU_VCE_TABLE` (`:54` y `:2370-2372`), y el patron
`gate`/`ungate` es identico (`:155` y `:165`).

Un detalle que confirma que no es un camino muerto: **`polaris10_smumgr.c` no declara
`powergate_uvd` ni `powergate_vce`**, asi que se usa el de smu7 (`smu7_hwmgr.c:5871`), que
es el que lleva la cadena. Es el mismo criterio de liveness que apliqué al principio de
sesion, con el resultado contrario: aqui si corre.

### Y los dos parches se pisan entre si

Orden real: UVD primero (`:1230`), luego VCE (`:1233`), en la misma llamada. Y los dos
terminan en el **mismo DWORD** (`dpm_table_start + 1576`), como muestra la tabla de arriba.
O sea que en una transicion que ungatee ambos bloques, se ejecutan dos lecturas y dos
escrituras sobre la misma palabra, y la segunda ve lo que puso la primera.

> **ACTUALIZACION.** Esta pregunta ya no esta abierta: `212` la resuelve con evidencia
> indirecta pero solida. La lectura de `PmFuses` en `:529` extrae cuatro bytes
> consecutivos con los shifts que el layout exige, lo que prueba que el layout del host y
> el del firmware coinciden byte a byte. De ahi se sigue la **lectura (A)**: los once
> usos estan **desviados 108 bytes**. Estado `PROVEN_DERIVED`.

## Su unicidad frente a la correccion de `211`

`211` documento el mismo patron de desfase en **once** sitios, y concluyo que eran un
fallo grave. Una version posterior de `211` lo corrige a **latente**, porque la copia
completa de la tabla (`:2118`) va la ultima y sobrescribe lo que las copias parciales
escribieron desviado.

**Ese argumento no aplica aqui, y por eso este hallazgo sigue vivo:**

| | los parches de UVD/VCE |
|---|---|
| quien los llama | `smum_update_smc_table(hwmgr, SMU_UVD_TABLE)` desde `smu7_clockpowergating.c:47` |
| cuando | transicion DPM, **fuera** de `init_smc_table` |
| hay copia completa despues | **no**: no vuelve a construirse la tabla |
| efecto | el byte de `BootVddc` queda pisado en la SRAM |

Es el unico punto de la lista de once donde el error de 108 bytes **llega a la SRAM sin
que nada lo tape**. El resto son escrituras redundantes con una correccion posterior; este
es un parche en caliente sin correccion posterior.

Estado: `PROVEN` el mecanismo, `PROVEN` que el camino se recorre
(`amd_powerplay.c:1230` -> `:449` -> `smu7_hwmgr.c:5871` -> `smu7_clockpowergating.c:137`,
rama ungate), `RUNTIME_MISSING` cuantas veces ocurre.


## ACTUALIZACION tras `107`: el campo es `Smio[5]`, no `BootVddc`

`107` rehace el calculo con el layout medido por gcc y corrige dos puntos de este
documento.

**El campo.** Mi cuenta fue `offsetof(UvdBootLevel) + 108 = 1684 = offsetof(BootVddc)`.
Ese es el **mismo error** que corregi a mano en `211`, por cuarta vez:

- "el offset `X` de la struct esta en la posicion `X + 108` de la tabla" — **cierto**.
- "la posicion `X` de la tabla contiene el offset `X` de la struct" — **falso**.

Para saber que hay en la posicion `X` de la tabla hay que mirar el offset `X - 108` de la
struct. En `1576 - 108 = 1468` esta **`Smio`**, y el byte que escriben las mascaras es el
**byte 0 de la celda 5**: `Smio[5]`.

Con gcc:

```
sizeof(SMU74_Discrete_DpmTable) = 1884
offsetof(BootVddc)              = 1684
offsetof(VceBootLevel)          = 1577
```

**El solape.** Decia que VCE escribia en el byte medio "y por eso pisaba lo que UVD acaba
de escribir". Falso: `0x00FFFFFF` conserva bytes 0-2 y escribe el 3; `0xFF00FFFF`
conserva 0, 2, 3 y escribe el 2. **Cada mascara preserva el byte de la otra.**

Lo que si es cierto, y es lo unico que sobrevive de este documento: **las dos escriben en
el mismo DWORD** (`1577 / 4 * 4 = 1576`), asi que en un ungate que pase por ambos
(`amd_powerplay.c:1230` y `:1233`) el DWORD queda con dos celdas de `Smio` tocadas por dos
niveles de arranque distintos.

Y un dato que `107` aporta y que atenua el dano: `SMU_MAX_SMIO_LEVELS = 4`, asi que
`Smio[5]` **no lo escribe ningun productor** y parte de cero.

Estado tras la correccion:

| afirmacion | estado |
|---|---|
| el parche calcula mal la direccion por 108 bytes | `PROVEN`, sobrevive |
| el camino es vivo y es de transicion DPM | `PROVEN`, sobrevive |
| es el unico punto sin copia posterior que lo tape | `PROVEN`, sobrevive |
| el campo es `BootVddc` | **REFUTED** por `107` |
| VCE pisa lo que escribio UVD | **REFUTED** por `107` |
