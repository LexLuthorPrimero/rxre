# 226  Barrido de la frontera VBIOS→host: el patrón de 120/123 aparece en 1 de 5, y `224` (antes `224`) no estaba donde yo creía

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**CORRIGE el alcance de `224` (antes `224`)** · generaliza `225` (antes `225`) · herramienta propia `tools/ppt_validate.py`
con `--selftest` de 29 pruebas

## Lo que hice

`225` (antes `225`) termino con una frase que era un encargo: *«las validaciones faltan en el hueco entre
el VBIOS declara y el driver lo usa»*. tenia **cuatro** casos de ese hueco. Un patron de cuatro
pide barrido sistemático, y el alcance es medible: **9 subtablas del PPT con contador y 15
offsets** en el PowerPlayInfo.

Así que construí `tools/ppt_validate.py`, que para cada getter de subtabla del PPT responde:

1. de donde sale la **cuenta** (el VBIOS)
2. con que **capacidad** se reserva el destino (el host)
3. si esa capacidad se **compara** con la cuenta en algun punto
4. y, si no se compara, si la reserva **es** la cuenta (desajuste imposible por construccion)

## El resultado, y corrige mi propia afirmacion

```
  funcion                           capacidad                       cuenta        estado
  ----------------------------------------------------------------------------------
  get_vddc_lookup_table             max_levels                      ucNumEntries  *** SIN COMPARAR ***
  get_mclk_voltage_dependency_table  mclk_dep_table->ucNumEntries   ucNumEntries  segura
  get_sclk_voltage_dependency_table  tonga_table->ucNumEntries      ucNumEntries  segura
  get_pcie_table                    atom_pcie_table->ucNumEntries  pcie_count    comparada
  get_mm_clock_voltage_table        mm_dependency_table->ucNum...  ucNumEntries  segura

  reserva == cuenta (desajuste imposible) : 3
  comparadas explicitamente               : 1
  SIN COMPARAR (patron de 120 y 123)      : 1
```

**Solo 1 de 5.** Y eso **degrada mi patron**, que lo tinha extendiendo con entusiasmo:

- **Tres getters son seguros por construccion**: reservan con `kzalloc_flex(..., ucNumEntries)`
  y escriben `ucNumEntries`. El desajuste es **imposible**, no por una validacion, sino porque
  no hay dos cantidades.
- **Uno recorta a proposito**, y el codigo lo dice:
  ```c
  /* Since first PCIE entry is for ULV, #pcie has to be <= SclkLevel + 1 */
  pcie_count = vdd_dep_on_sclk->count + 1;
  if ((uint32_t)atom_pcie_table->ucNumEntries <= pcie_count)
          pcie_count = (uint32_t)atom_pcie_table->ucNumEntries;
  ```
  **Con el motivo escrito en el comentario.** Eso es lo que deberia ser el patron, y es el
  unico sitio donde se cumple.
- **Solo `get_vddc_lookup_table` tiene el problema**: capacidad constante `16`, cuenta del
  VBIOS hasta 255, sin comparar. Es exactamente lo que publique en `225` (antes `225`), y sigue siendo
  cierto.

**Y hay una correccion de alcance que importa mas**: **`224` (antes `224`) no esta en este fichero.**
`224` (antes `224`) era `smu7_hwmgr.c:smu7_setup_dpm_tables_v1`, donde el lazo copia desde la tabla del PPT
— ya correcta, con la reserva exacta— a un **array fijo** `dpm_levels[8]`. **Son dos fronteras
distintas**:

| frontera | fichero | capacidad | cuenta | estado |
|---|---|---|---|---|
| VBIOS -> tabla del host | `process_pptables_v1_0.c` | `ucNumEntries` (4 de 5) | VBIOS | **segura** |
| tabla del host -> tabla del SMC | `smu7_hwmgr.c` | **8** (`MAX_REGULAR_DPM_NUMBER`) | **la misma** | **`224` (antes `224`), margen CERO** |

La primera frontera esta bien. **La segunda es la que falla, y falla con margen cero.** La
herramienta solo cubre la primera, asi que **`224` (antes `224`) sigue en pie y fuera de su alcance**: no lo
ha refutado, no lo ha confirmado, y no lo pretendia.

## Que aporta la herramienta, mas alla del numero

**El resultado que no esperaba: la mayoria de la frontera esta bien.**

Eso cambia la lectura del conjunto. Durante cuatro documentos he tratado «el VBIOS declara y
el host no comprueba» como una property del formato. **Es una property de UN getter**, y los
otros cuatro hacen las cosas bien: tres alocando a medida, uno recortando a proposito con el
motivo escrito.

La leccion general, y es de las que mas me han servido:

> **Un patron encontrado a mano puede ser un patron del CODIGO o un patron del AUTOR.**
> Cuatro casos me hacian esperar que la frontera entera fuera laxa. **El barrido dice que
> la frontera es correcta en 4 de 5.** Cuatro hallazgos a mano no autorizan una regla general,
> y un barrido de N elementos si.

## Y los tres errores que tuvo la herramienta

Porque son el argumento de por que el selftest existe:

1. **La regex del origen de la cuenta pedia `.count`**, y el codigo usa `->count`. Las cuatro
   cuentas salieron `(no detectada)`.
2. **Mi expectativa sobre `get_mm_clock_voltage_table` era falsa.** Escribi que debia salir
   "comparada"; la herramienta dijo que no, y **la herramienta tenia razon**: ese getter
   reserva `ucNumEntries` y escribe `ucNumEntries`. No hay nada que comparar. Eso obligo a anadir
   la categoria que faltaba, **reserva == cuenta**, que es la que mas casos cubre.
3. **La semantica del selftest estaba planteada al reves**: yo creia que `compara`
   distinguiria al arriesgado de los seguros. No: `compara` es `False` en los cuatro, y lo que
   los distingue es `capacidad_es_cuenta`.

Y el tercero es el que mas me importa, porque **el selftest estaba probando mi idea en vez de
la realidad**, y solo fallo cuando la realidad no coincidio.

## La validacion de la validacion

Igual que en `smc_copy_scope`: un control que nunca ha fallado no esta probado.

El selftest inyecta en el codigo real una comparacion que no existe
(`ucNumEntries > 16 || 0 != ucNumEntries`) y **comprueba que el veredicto cambie** de SIN
COMPARAR a COMPARADA. Si el control no decidiera, ese test pasaria siempre.

Ademas, los cuatro getters reales estan como **vectores positivos**: si la herramienta no los
marca con lo que corresponde, `TOOL_BROKEN`.

## Clasificacion

- `PPT_GETTERS_INVENTORY = PROVEN`: 9 subtablas con `ucNumEntries`, 15 offsets en el
  PowerPlayInfo. Alcance medido antes de construir la herramienta.
- `THREE_OF_FOUR_FLEX_GETTERS_ALLOCATE_TO_FIT = PROVEN`: `get_sclk/mclk/mm_voltage_dependency_table`
  reservan `kzalloc_flex(..., ucNumEntries)` y escriben `ucNumEntries`. **Desajuste imposible.**
- `GET_PCIE_TABLE_CLAMPS_EXPLICITLY = PROVEN`: `:502-504`, con el motivo en el comentario de
  `:500`. **El unico sitio donde hay recorte deliberado, y esta escrito por que.**
- `ONLY_GET_VDDC_LOOKUP_TABLE_HAS_THE_PATTERN = PROVEN`: capacidad `max_levels` (16
  hardcodeado en `:283` y `:292`), cuenta `ucNumEntries` hasta 255, unico check `!= 0`.
  **Es el hallazgo de `225` (antes `225`), y el unico de su clase.**
- `FINDING_120_IS_IN_A_DIFFERENT_BOUNDARY = PROVEN_DERIVED`: `224` (antes `224`) es la frontera
  **tabla del host -> tabla del SMC** (`smu7_hwmgr.c`, `dpm_levels[8]`), no la que barre esta
  herramienta. **`224` (antes `224`) no queda refutado ni confirmado aqui.**
- `MY_PATTERN_IS_ONE_GETTER_NOT_THE_WHOLE_BOUNDARY = CORRECTED`: dije en `225` (antes `225`) que las
  validaciones faltan «entre el VBIOS declara y el driver lo usa». **En 4 de 5 no faltan.**
- `MY_SELFTEST_WAS_TESTING_MY_IDEA_NOT_REALITY = CORRECTED`: la distincion por `compara` era
  mia y era falsa; la real es `capacidad == cuenta`.

## Lo que esto obliga a hacer en un driver propio

1. **Copiar el patron de `get_pcie_table`, no el de `get_vddc_lookup_table`.** La forma buena
   esta en el arbol y tiene el motivo escrito: recortar al minimo de las dos cantidades, con
   un comentario que explique por que. **Un recorte con motivo es un contrato; un recorte sin
   motivo es una sorpresa.**
2. **Reservar a medida siempre que se pueda.** Tres de cuatro getters lo hacen, y con eso el
   desajuste no puede existir. `kzalloc_flex` con la cuenta del VBIOS **es** la validacion
   cuando el destino es flexible.
3. **Cuando el destino sea fijo, ahi si hay que comparar**, y ahi es donde falla `224` (antes `224`), con
   margen cero. **Mi driver tiene que distinguir las dos fronteras**, porque en la primera la
   validacion es estructural y en la segunda tiene que ser explicita.
4. Y la regla de proceso, que es la de este documento: **cuatro hallazgos a mano no autorizan
   una regla general.** Este barrido es lo que dice si el patron es del codigo o del autor,
   y salio que **es de un getter**. Barrir antes de generalizar, que es lo mas barato que
   tengo y lo que mas me ha costado no hacer.