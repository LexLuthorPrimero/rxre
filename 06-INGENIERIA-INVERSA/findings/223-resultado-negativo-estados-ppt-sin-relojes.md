# 223  RESULTADO NEGATIVO: el VBIOS declara 2 estados de potencia sin datos de reloj, y eso es correcto, no un fallo

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**REFUTA una hipotesis mia** · separa dos nociones de "nivel" que yo estaba confundiendo ·
no cierra `099`, y **no pretende cerrarlo**

## Lo que me proponia hacer

`099` afirma que tras un fallo de `smu7_setup_dpm_tables_v1` los contadores quedan en
**8 y 4 con valores a cero**. Para poner a prueba esa cifra pensé: el VBIOS declara los
niveles DPM, asi que si el VBIOS dijera otra cosa, `099` cae.

## Y no dice otra cosa, porque son dos cosas distintas

El array de estados del VBIOS, `ATOM_Tonga_State_Array` en `0x9C57`:

```
ucRevId      = 1
ucNumEntries = 2
entrada 0:  engIdx=0  memIdx=0  pcieGen=0  pcieLn=0  usClassification=0x0008
entrada 1:  engIdx=0  memIdx=0  pcieGen=7  pcieLn=2  usClassification=0x0000
```

**Dos entradas.** Y el consumidor de la cifra es directo:

```c
/* process_pptables_v1_0.c:1251 */
return (uint32_t)(state_arrays->ucNumEntries);
```

con **un solo llamador**, `smu7_get_number_of_powerplay_table_entries` (`smu7_hwmgr.c:3677`),
que es el numero de **estados de potencia del PPT**.

**Y los 8 y 4 de `099` no vienen de ahi.** Son cotas de array de la **tabla DPM del SMC**:
`SMU74_MAX_LEVELS` = 8 y `SMU_MAX_MCLK_DPM_LEVELS` = 4. Los puebla el **firmware del SMC**,
no el PPT del VBIOS.

O sea: hay **dos nociones distintas de "nivel"**, y las estaba usando como si fueran una:

| nocion | quien la fija | valor en esta placa |
|---|---|---:|
| estados de potencia del PPT | `ucNumEntries` en el VBIOS | **2** |
| niveles DPM del SMC (graficos) | firmware, cota `SMU74_MAX_LEVELS` | hasta **8** |
| niveles DPM del SMC (memoria) | firmware, cota `SMU_MAX_MCLK_DPM_LEVELS` | hasta **4** |

**Mi prueba estaba mal dirigida, y lo digo en vez de forzar que encaje.** El VBIOS **no puede**
confirmar ni refutar `099`, porque `099` habla de la tabla del SMC y el VBIOS no la contiene.
`099` sigue exactamente como estaba: `PROVEN` en lo que dice del codigo, y sin dato nuevo.

## La hipotesis que si queda refutada

La que **si** era mia y **si** queda muerta: *"el array de estados tiene 2 entradas con
relojes a cero, eso esta mal, y por eso el conteo sale mal"*.

Es **falsa**, y el VBIOS lo demuestra al ser decodificable:

```
ATOM_PPLIB_CLASSIFICATION_UI_MASK = 0x0007
ATOM_PPLIB_CLASSIFICATION_BOOT    = 0x0008
ATOM_PPLIB_CLASSIFICATION_THERMAL = 0x0010
```

```
entrada 0:  0x0008  ->  UI = 0 (ATOM_PPLIB_CLASSIFICATION_UI_NONE),  BOOT = 1
entrada 1:  0x0000  ->  UI = 0,  sin BOOT, sin THERMAL
```

**Es un PPT moderno y minimo**: dos estados, uno marcado BOOT, sin etiqueta de interfaz, y
**sin datos de reloj porque en esta familia los relojes no salen del PPT**. Salen de la
tabla DPM que el firmware construye en la SRAM del SMC.

Que `smu7_get_pp_table_entry_callback_func_v1` (`smu7_hwmgr.c:3683`) construya estados de
potencia a partir de entradas sin reloj **no es un fallo**: en SMU7 el PPT aporta
clasificación y PCIe, y el SMC aporta los relojes.

## Y una validacion que es laxa, pero correcta aqui

`check_powerplay_tables` (`:1123-1131`) valida cuatro cosas:

```c
sHeader.ucTableFormatRevision >= ATOM_Tonga_TABLE_REVISION_TONGA   /* 7  >= 7  OK */
usStateArrayOffset != 0                                          /* 77 != 0  OK */
sHeader.usStructureSize > 0                                       /* 778     OK */
state_arrays->ucNumEntries > 0                                    /* 2       OK */
```

Y **nunca comprueba que `ucNumEntries` sea suficiente**, ni que las entradas traigan reloj.
Con dos entradas a cero pasa igual.

**Podria sonar a fallo y no lo es**: para esta GPU el check correcto es "que haya al menos un
estado", porque los estados no portan relojes. **Un check mas estricto habria rechazado un
VBIOS valido.** Lo anoto como **caracteristica del formato**, no como defecto, precisamente
porque la version "suspicaz" de la misma afirmacion es falsa.

**Pero si generaliza en una direccion**: si una subtabla del PPT **si** tiene que portar
datos, y la validacion solo mira `> 0`, el mismo patron se repetiria. Eso no se puede
afirmar sin revisar cada subtabla, y **no lo reviso aqui**: queda como
`NOT_DETERMINED`, no como sospecha.

## Lo que esto hace con `099`

Nada. `099` sigue siendo lo que es:

- `PROVEN`: el retorno de `smu7_setup_dpm_tables_v1` se ignora en `smu7_hwmgr.c:1068`.
- `PROVEN_DERIVED`: tras el fallo los contadores quedan con valores a cero.

Y **esta tanda no aporta ni una linea de evidencia nueva a `099`**. Lo digo porque
`NEGATIVE_RESULT PROPAGATION` empieza por eliminar la rama refutada, y aqui la rama
refutada es **mia y era mia sobre el VBIOS**, no sobre `099`.

## Clasificacion

- `MY_VBIOS_TEST_OF_099_WAS_MIS_AIMED = PROVEN`: `ucNumEntries` gobierna los estados del
  PPT; los 8 y 4 son cotas de la tabla del SMC. **Dos nociones distintas.**
- `VBIOS_DECLARES_2_POWDER_STATES = PROVEN`: `ucNumEntries = 2` en `0x9C58`, consumido por
  `get_number_of_powerplay_table_entries_v1_0` (`:1251`) con un solo llamador
  (`smu7_hwmgr.c:3677`).
- `VBIOS_STATE_ARRAY_IS_NOT_MALFORMED = PROVEN`: `usClassification` = `0x0008` (BOOT) y
  `0x0000`, decodificados contra `ATOM_PPLIB_CLASSIFICATION_*` de `pptable.h:249-258`.
  **REFUTA** mi hipotesis de "tabla malformada".
- `PPT_STATES_CARRY_NO_CLOCK_DATA_BY_DESIGN = PROVEN_DERIVED`: `engIdx=0, memIdx=0` en las
  dos entradas, y en SMU7 los relojes salen de la tabla DPM del SMC. Coherente con el resto.
- `CHECK_POWERPLAY_TABLES_ONLY_REQUIRES_NONZERO = PROVEN`: `:1123-1131` valida cuatro
  condiciones, todas satisfied por este VBIOS, y ninguna sobre la suficiencia de
  `ucNumEntries` ni sobre el contenido de las entradas.
- `SUFICIENCY_CHECKS_FOR_OTHER_SUBTABLES = NOT_DETERMINED`: no revisado. **No lo afirmo.**
- `FINDING_099_UNCHANGED = PROVEN_DERIVED`: esta tanda no aporta evidencia a `099`, ni a
  favor ni en contra.

## Lo que esto obligan a hacer en un driver propio

1. **Separar "estado de potencia" de "nivel DPM".** En este hardware son dos cosas con dos
   dueños: el VBIOS y el firmware. Un driver propio que los mezcle tendra un numero de
   niveles que no significa nada. **Cada uno tiene su contador, su fuente y su cota.**
2. **Un check `> 0` es un check de presencia, no de validez.** Aqui es correcto porque la
   subtabla no tiene que portar datos. En cualquier subtabla que **si** tenga que portarlos,
   `> 0` es insuficiente. **Mi driver tiene que validar lo que cada subtabla promete**, y
   para eso hay que saber que promete cada una: eso no esta escrito en ningun sitio del
   arbol, y es trabajo pendiente.
3. Y la regla de proceso, que hoy me ha servido: **una prueba mal dirigida se declara mal
   dirigida.** Es mas barato que forzar que el dato encaje con la hipotesis, y evita
   publicar un fallo que no existe.