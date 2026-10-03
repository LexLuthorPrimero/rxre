# 222  `usTjMax=93` se convierte en `usOperatingTempMaxLimit=43`, y `usEDCLimit` está disponible en el VBIOS pero el driver no lo copia

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

COMPLETA `220` · USA EL VBIOS REAL DE `revkit/capturas/` · corrige un error mio de esta misma
tanda

## La cadena, de punta a punta

Con los offsets ya medidos en `220` (`usTjMax` @ 17, `usEDCLimit` @ 21), leo el VBIOS real:

```
ATOM_Polaris_PowerTune_Table @ 0x9EAB   (pack(1), sizeof = 53)
   usTjMax                  @ 17  = 93
   usEDCLimit               @ 21  = 0
   usSoftwareShutdownTemp   @ 23  = 97
   usTemperatureLimitHotspot@ 29  = 80
```

Y el driver, `process_pptables_v1_0.c:669-670` (rama Polaris, la que corresponde):

```c
tdp_table->usDefaultTargetOperatingTemp = le16_to_cpu(polaristable->usTjMax);   /* = 93 */
tdp_table->usTargetOperatingTemp        = le16_to_cpu(polaristable->usTjMax);   /* = 93 */
```

Despues `smu7_hwmgr.c:2589-2593`, en `smu7_thermal_parameter_init`:

```c
table_info->cac_dtp_table->usDefaultTargetOperatingTemp =
        (table_info->cac_dtp_table->usDefaultTargetOperatingTemp >= 50) ?
                (table_info->cac_dtp_table->usDefaultTargetOperatingTemp - 50) : 0;

table_info->cac_dtp_table->usOperatingTempMaxLimit = table_info->cac_dtp_table->usDefaultTargetOperatingTemp;
table_info->cac_dtp_table->usOperatingTempStep    = 1;
table_info->cac_dtp_table->usOperatingTempHyst    = 1;
```

**La cuenta, con el valor real:**

```
93 >= 50   ->  TRUE
usDefaultTargetOperatingTemp = 93 - 50 = 43
usOperatingTempMaxLimit      = 43
usOperatingTempStep          = 1
usOperatingTempHyst          = 1
```

**Y esto corrige una afirmacion mia de hace una hora.** Escribi que la rama `>= 50` no se
toma porque el valor es 0. **Es falso**: `usDefaultTargetOperatingTemp` **si** se asigna,
desde `usTjMax`, y vale 93. Mi script automatico habia listado 5 campos no asignados y yo
**confundí "sobrescrito después" con "nunca establecido"**. El script tenía razón y yo lo
malinterpreté.

Que el valor fuera 0 habria sido otra historia, y por eso **hice bien en comprobar en vez de
publicar**. Un `43` aqui es comportamiento real; un `0` habria sido un fallo de recorte de
temperatura operativa.

## El patron que hay debajo, y es mas interesante que el valor

La conversion es **"-50 si es >= 50"**. O sea: el driver espera que `usTjMax` venga en
**grados Fahrenheit** y lo pasa a Celsius restando 32... **no, restando 50**.

Es decir: el VBIOS declara `usTjMax = 93`, y el driver lo trata como Fahrenheit-obscuro
para obtener 43 " Celsius". **Pero 93 °C y 43 °C no estan relacionados por una conversion
de temperatura.** Fahrenheit a Celsius es `(F-32)*5/9`; `93 -> 43` seria `(93-50)`, que es
lo que hace, pero **93 °F son 33.9 °C, no 43**.

Asi que el `-50` **no es una conversion fisica**. Es un **cambio de unidades arbitrario**, o
- mas probable - **el VBIOS almacena el limite en Celsius y el driver espera Fahrenheit**, y
el `-50` es un parche para un campo cuyo convenio cambio entre generaciones.

Lo que **si** se puede afirmar sin especular: **la magnitud de `usOperatingTempMaxLimit` es
exactamente `usTjMax - 50`, y el resultado (43) se usa como "limite maximo de temperatura
operativa"** sin ninguna comprobacion de que 43 sea una temperatura coherente con 93.

Y hay una comprobacion que **si** es coherente: `220` leyo del mismo VBIOS
`usTemperatureLimitHotspot = 80` y `usSoftwareShutdownTemp = 97`. Con
`usDefaultTargetOperatingTemp = 93` y su derivado 43, **los cuatro limites quedan**:
hotspot 80 < TjMax 93, shutdown 97, target 93, max-operativo 43. **El 43 es el unico que
se sale del rango de los demas.**

Eso **no es una temperatura**. Los otros tres estan en 80-97 °C. Un "limite maximo
operativo" de 43 °C cuando el die termico esta en 93 °C significa que **el recorte a 43
nunca sera alcanzado**: el control termico nuncaLimitara por `usOperatingTempMaxLimit`.

**Eso es `PROVEN_DERIVED` y es el hallazgo de este documento**: el recorte a temperatura
operativa esta inactivo, porque su umbral (43) queda muy por debajo del umbral termico real
(80, el hotspot).

Y `usOperatingTempStep = 1` y `usOperatingTempHyst = 1` son **constantes**, no vienen del
VBIOS. `PROVEN`.

## El hueco real: `usEDCLimit`

Comparacion mecanica, campo por campo, entre la struct `phm_cac_tdp_table` y lo que
asigna `get_cac_tdp_table` (rama Polaris):

```
campos de phm_cac_tdp_table        : 34
asignados por get_cac_tdp_table     : 29
NO asignados                        : 5
    usEDCLimit
    usOperatingTempMinLimit
    usOperatingTempMaxLimit     (se asigna en smu7_hwmgr.c:2592, no aqui)
    usOperatingTempStep         (idem :2593)
    usOperatingTempHyst         (idem :2594)
```

Los cuatro `usOperatingTemp*` se asignan en `smu7_thermal_parameter_init`, asi que
**no son un hueco del consumidor**: son constantes o derivados. Correcto.

**`usEDCLimit` si es un hueco.** Esta **presente** en
`ATOM_Polaris_PowerTune_Table` (offset 21, valor 0 en este VBIOS), **el driver lo lee del
VBIOS en otras ramas** (Tonga y Fiji lo tienen), pero **la rama Polaris NO lo copia** a
`phm_cac_tdp_table`. Como la tabla se `kzalloc`ea, `usEDCLimit` queda en **0**.

Que el VBIOS de esta placa lo declare 0 significa que **no se puede distinguir** si el campo
esta realmente a cero o si el driver lo pierde. **Es `SEMANTIC_MISSING`**: no se si el
firmware depende de el.

## Y el error mio, que es la parte que mas valor tiene

Escribi, hace poco:

> "Los cuatro `usOperatingTemp*` se asignan en `smu7_hwmgr.c:2592-2594`, no en
> `get_cac_tdp_table`." — correcto.
> Y despues: "`usDefaultTargetOperatingTemp` nunca se asigna, asi que vale 0" — **falso**.

Mi script automatico habia dicho correctamente que `usDefaultTargetOperatingTemp` **si** se
asigna. **Lo que fallo fue mi lectura del script**, no el script. Interprete "no aparece en
la lista de 5" como "esta en la lista de 5".

Y si lo hubiera publicado sin comprobar, el hallazgo habria sido **un recorte de
temperatura operativa a 0 °C**, que suena grave y **es imposible**: `usTjMax=93` garantiza
que la rama `>=50` se toma.

**La leccion**: un script que dice "5 elementos" y una lista de 5 elementos se leen con
cuidado, porque la ausencia en la lista es un dato y la **interpretacion** de la lista es
otro. Un `0` ahi no era un hecho, era una inferencia mia, y la inferencia era lo que tenia
que verificar.

## Clasificacion

- `US_TJMAX_IS_93_AND_IT_CONVERTS = PROVEN_DERIVED`: `usDefaultTargetOperatingTemp = 93`
  (`:669-670`), `93 >= 50` es cierto, y por tanto
  `usDefaultTargetOperatingTemp = 43` y `usOperatingTempMaxLimit = 43` (`:2589-2593`).
- `OPERATING_TEMP_LIMIT_IS_INACTIVE = PROVEN_DERIVED`: con `usOperatingTempMaxLimit = 43`
  y `usTemperatureLimitHotspot = 80`, el umbral de recorte queda **37 °C por debajo** del
  limite termico. El recorte no se alcanza. **Efecto: el recorte de temperatura operativa no
  actua en esta placa.**
- `OPERATING_TEMP_STEP_AND_HYST_ARE_CONSTANTS = PROVEN`: `= 1` y `= 1`, fijos en `:2593-2594`,
  no vienen del VBIOS.
- `THE_MINUS_50_IS_NOT_A_TEMPERATURE_CONVERSION = PROVEN_DERIVED`: `F->C` seria `(93-32)*5/9`;
  el driver hace `93-50`. **No es una conversion fisica.** Que el convenio del campo haya
  cambiado entre generaciones es `NOT_IN_CORPUS`.
- `US_EDCLIMIT_NOT_COPIED_ON_POLARIS = PROVEN`: la rama Polaris (`:658-698`) **no** asigna
  `usEDCLimit`, aunque el campo existe en `ATOM_Polaris_PowerTune_Table` @ 21 y las ramas
  Tonga/Fiji **si** lo hacen. Con `kzalloc`, queda en 0. Que el firmware lo use:
  `SEMANTIC_MISSING`.
- `US_EDCLIMIT_VALUE_IS_0_IN_THIS_VBIOS = PROVEN`: `0x9EAB + 21 = 0`. **Por eso no se puede
  distinguir "perdido" de "realmente cero" en esta placa.**
- `MY_MISREADING_OF_MY_OWN_SCRIPT = CORRECTED`: leí la lista de 5 campos no asignados como
  si incluyera `usDefaultTargetOperatingTemp`. **No la incluia.** El script era correcto.
  **Publicarlo sin verificar habria producido un fallo de recorte a 0 °C que es imposible
  dado `usTjMax=93`.**
- `POWERPLAY-STRUCT-SELECTION_CIERRA_PARCIALMENTE = PROVEN`: las tres ramas (Tonga, Fiji,
  Polaris) leen la misma forma de `usTjMax -> usDefaultTargetOperatingTemp`, y el VBIOS real
  cae en la de Polaris. El layout elegido es el correcto **para esta placa**, por el valor de
  `ucRevId`.

## Y una consecuencia de la que no se puede escapar

`usTjMax = 93` esta en el VBIOS de mi placa, y `usSoftwareShutdownTemp = 97` y
`usTemperatureLimitHotspot = 80` tambien. Los tres son **coherentes entre si como
temperaturas en °C**. **`usOperatingTempMaxLimit = 43` es el unico que no lo es.**

La lectura mas economica es que el campo `usTjMax` del VBIOS esta en **Celsius**, el
driver lo trata como si estuviera en Fahrenheit, y por eso produce 43 donde deberia
producir 93 (o 33.9). Con eso, el recorte operativo se desactivaria **y el target inicial
de temperatura seria 93 en vez de 43** (`usTargetOperatingTemp = usTjMax = 93`, `:671-672`).

**Ojo con esto, que es la trampa**: `usTargetOperatingTemp` **si** vale 93 (no pasa por el
`-50`), mientras que `usDefaultTargetOperatingTemp` **si** pasa por el `-50` y vale 43. **Dos
campos con el mismo nombre base y valores distintos, uno restado y otro no, en lineas
contiguas (`:671` y `:2589`).** Eso es exactamente el tipo de cosa que hace que un cambio de
un campo afecte al otro sin que nadie lo note.

## Lo que esto obliga a hacer en un driver propio

1. **Un `-50` sin comentario es un `-50` sin contrato.** La conversion Fahrenheit->Celsius es
   `(F-32)*5/9`. Un `-50` a secas significa que el campochanged de unidades en algun momento
   y nadie lo documento. Un driver propio tiene que **declarar la unidad de cada campo del
   PPT** y **convertir explicitamente**, no restar una constante magica.
2. **Verificar que un umbral derived es coherente con los limites del mismo bloque.** Un
   chequeo de una linea: `usOperatingTempMaxLimit` deberia caer entre
   `usTemperatureLimitHotspot` y `usTjMax`. Si cae fuera (43 < 80), **algo esta mal**, y un
   assert lo habria dicho. **Mi driver deberia validar el PPT al cargarlo.**
3. Y la generalizacion, que es la que mas veces ha salido esta sesion: **un campo con dos
   nombres parecidos y valores distintos, uno restado y otro no, en lineas contiguas, es
   una bomba de relojería.** Ambos se llaman `...OperatingTemp`, los dos se alimentan del
   mismo `usTjMax`, y solo uno pasa por la conversion.