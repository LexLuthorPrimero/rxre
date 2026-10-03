# 130 · La clase `count - N` barrida: 196 accesos, y mi grep a mano solo veia 35

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## CERRADO POR `131` — ninguno de los 26 produce un indice negativo en mi placa
>
> Este fichero dejo abierto el `NOT_DETERMINED`: si algun `count` puede valer cero. **Cerrado
> con medicion, no con deduccion.** Los 26 accesos usan 13 expresiones que se reducen a **tres
> origenes**:
>
> | familia | sitios | count >= 1 por |
> |---|---|---|
> | A · tablas dep del PPT | 6 | el getter **rechaza el cero antes de `kzalloc_flex`**, y **comprobe que la rama de Polaris tambien**, que es la mia (`:443`) |
> | B · tablas DPM | 10 | la rama `i == 0` del filtro siempre pasa, y el bucle corre si Familia A dio tabla (`:900-912`) |
> | C · `performance_level_count` | 7 | **medido**: `request_ps = kzalloc` y solo se llena copiando un estado con flag `Boot`. Mi VBIOS **tiene uno** (`usClassification = 0x0008`) |
>
> ```
> ATOM_Tonga_State_Array en 0x9C57:  ucRevId=1  ucNumEntries=2
>   idx 0  usClass 0x0008  -> BOOT, UI_NONE
>   idx 1  usClass 0x0005  -> UI_PERFORMANCE, NO boot
> ```
>
> **Mi placa declara exactamente dos estados: BOOT y PERFORMANCE, y hay un BOOT.** Luego
> `performance_level_count >= 1` y los 7 sitios de la Familia C no son un indice negativo aqui.
>
> **Ademas, el estado 1 referencia SCLK 0..7 y MCLK 0..2: corroboracion independiente de `121`
> desde una tabla distinta, y por indices.** Y sirve de autovalidacion: un offset equivocado
> daria bytes arbitrarios, no un rango que casa con lo ya medido.
>
> **Lo que NO queda cerrado:** la garantia existe, pero **no esta escrita junto al acceso**.
> `smu7_set_sclk_od` comprueba `ps == NULL` y nada mas. **Un VBIOS perfectamente legal sin ningun
> estado `Boot` deja `request_ps` en el `kzalloc` y convierte los 7 sitios en
> `performance_levels[-1]`.** Eso no es un fallo de mi placa: es un defecto de contrato.

**Barrido sistematico del patron que `227` (antes `125`), `228` (antes `126`) y `230` (antes `129`) habian encontrado a mano.** El
alcance es mucho mayor de lo que parecia, y mi busqueda manual se estaba comiendo un tercio.

## La herramienta

`tools/count_guard.py` v1.0.0. **33 pruebas, 0 fallos, `TOOL_VALIDATED`.**

Clase de defecto nueva, que ninguna de mis siete herramientas cubria: un indice
`tabla->entradas[tabla->count - 1]` sin que nada compruebe que `count` vale al menos uno. Con
`count == 0` el indice es `-1`.

- Busca **todos** los accesos con la forma `X[ ... count - N ]`.
- Para cada uno: la funcion que lo contiene, el campo `count` implicado, si hay una
  **comparacion de orden sobre ESE MISMO campo antes**, y el tipo del array.
- El tipo importa porque decide la gravedad: si el array es de tamano **flexible**, `[-1]` es
  memoria anterior a la **reserva**; si es **fijo**, es memoria anterior **dentro de la struct
  que lo contiene**, y no hay fallo de pagina.

**LIMITE DECLARADO**: la herramienta no declara ningun sitio defectuoso. **SIN_GUARDIA no es un
fallo**: es un sitio cuya garantia hay que ir a buscar al getter que rellena el count. Este
fichero no la busca.

## El mapa

```
                          ARBOL        MI RUTA
                          (196)     (smu7_hwmgr.c + polaris10 + hardwaremanager.c)
  GUARDADO_ANTES             40                        18
  SIN_GUARDIA               146                        26   en 15 funciones
  CORTOCIRCUITO_POR_OR        9                         4
  GUARDIA_DESPUES             1                         0
  SIN_FUNCION                 0                         0
```

**En mi ruta: 48 accesos.** Dos de cada tres no tienen guarda previa sobre su propio campo.

### Los 26 SIN_GUARDIA, por funcion

```
  3  smu7_populate_umdpstate_clocks          (el de 125)
  3  smu7_set_mclk_od                        (129)
  3  smu7_set_sclk_od                        (129)
  2  smu7_get_mclk_od
  2  smu7_get_sclk_od
  2  smu7_find_dpm_states_clocks_in_dpm_table
  2  smu7_patch_voltage_workaround
  2  smu7_setup_voltage_range_from_vbios
  1  smu7_apply_state_adjust_rules
  1  smu7_dpm_get_mclk
  1  smu7_dpm_get_sclk
  1  smu7_find_highest_vddc
  1  smu7_get_maximum_link_speed
  1  smu7_get_profiling_clk                  (el de 125)
  1  smu7_lookup_vddc_from_dispclk
```

**Y sale una agrupacion que `230` (antes `129`) no habia visto: los indices `count - 1` sin guarda estan
concentrados en la ruta de overdrive.** Cuatro funciones, diez sitios:

```
  smu7_get_sclk_od   2      smu7_set_sclk_od  3
  smu7_get_mclk_od   2      smu7_set_mclk_od  3
```

Las cuatro van por `.set_sclk_od` / `.set_mclk_od` / los hooks de OD, o sea **codigo de
overdrive, que dispara el usuario**. `230` (antes `129`) habia encontrado dos de las cuatro; **el patron son
cuatro funciones y diez accesos.**

### Los 4 CORTOCIRCUITO_POR_OR son los filtros de duplicados de `224` (antes `120`)

```
:809  if (i == 0 || dpm_table.sclk_table.dpm_levels[count - 1].value != ...)
:823  if (i == 0 || dpm_table.mclk_table.dpm_levels[count - 1].value != ...)
:902  if (i == 0 || dpm_table.sclk_table.dpm_levels[count - 1].value != ...)
:918  if (i == 0 || dpm_table.mclk_table.dpm_levels[count - 1].value != ...)
```

**Con `i == 0` el `||` cortocircuita, `count` sigue en 0 y `dpm_levels[-1]` NO se evalua.** Los
cuatro del filtro que `230` (antes `129`) describio son correctos.

Sin modelar el cortocircuito, la herramienta se autoporraba como SIN_GUARDIA y habria
inflado el recuento en 4. **Y hay que decir que MARCA, no RESUELVE**: solo detecta que hay un
`||` delante en la misma linea, que no implica que el acceso sea inalcanzable.

### La gravedad, aqui, es menor que en `229` (antes `128`)

En mi ruta **ninguno de los 48 indexa un array flexible con capacidad propia**. Los 48 caen en
arrays fijos (`dpm_levels[8]`, `performance_levels[2]`, `entries` de la tabla PPT), asi que un
`count == 0` daria indice `-1` **dentro de la struct que lo contiene**, no antes de una reserva.

**Eso baja la gravedad respecto a `229` (antes `128`)**, donde si se salia 28 bytes de una reserva de
`count * 28`. Aqui no hay fallo de pagina: hay lectura de basura en el campo anterior del mismo
struct.

- `NINGUNO_DE_LOS_48_ES_UN_ARRAY_FLEXIBLE = PROVEN_DERIVED`
- `UN_COUNT_CERO_DAINDICE_MENOS_UNO_DENTRO_DE_LA_STRUCT = PROVEN_DERIVED`
- `LA_GRAVEDAD_ES_MENOR_QUE_EN_128 = PROVEN_DERIVED`

## Mi busqueda manual se comia un tercio

Tres ficheros, mi grep:

```
grep -nE "\[[a-z_0-9>-]*count[[:space:]]*-[[:space:]]*[0-9]+\]" smu7_hwmgr.c polaris10_smumgr.c hardwaremanager.c
   ->  35 lineas
```

La herramienta, sobre **los mismos tres ficheros**: **48**.

**Mi patron no aceptaba notacion con punto** (`sclk_table.count - 1`), que es justamente la que
usa la mitad de los accesos.

> **Cuarta vez en dos dias que un filtro mal escrito me da un numero plausible y pequeno.**
> Un filtro que devuelve menos de lo que hay no avisa: devuelve un numero, y el numero parece
> un resultado. **La contrastacion es la unica forma de cazarlo**, y en este caso fue la
> herramienta la que dijo 48 donde yo decia 35.

## Mis nueve errores de esta tanda, y quien los caza

1. **`RE_SITIO` exigia un `count` de mas.** La cadena `t->count` se comia el `count` y el patron
   pedia un segundo. **`t->count - 1` no casaba nunca.**
2. **`_ULTIMO` exigia un caracter antes de `count`**, asi que el campo **desnudo** `count` —el
   mas frecuente del arbol— **no casaba nunca**.
3. **`_ULTIMO` solo aceptaba tres literales** y se le escapaban los sitios de
   `performance_level_count`.
4. **Comparaba la guarda con la cadena incompleta.** Recortaba el sufijo en el sitio pero no en
   la comparacion, y **las dos partes jamas coincidieron: toda guarda salia SIN_GUARDIA.**
5. **Y despues, al revés:** pasaba el indice entero `t->count-1` contra el `t->count` de la
   guarda. **Sigue sin poder coincidir.** Cuatro correcciones encadenadas en la misma funcion.
6. **`tipo_de_array` devolvia la PRIMERA declaracion con ese nombre.** El arbol tiene
   `entries[8]` fijos y `entries[]` flexibles, y la de la tabla del PPT salia como **fija**.
   **Un tipo equivocado es peor que un tipo desconocido.**
7. **Un VARIABLE LOCAL llamado `levels` heredaba la capacidad de un miembro homonimo de otro
   struct** (`fiji:1038` tomaba `SMU10_MAX_HARDWARE_POWERLEVELS`). **Mi propia regla
   `NAME_MATCH != SEMANTIC_MATCH`, commitida por mi propia herramienta.**
8. **No modelaba el cortocircuito**, y se autoporraba en los 4 filtros de `224` (antes `120`).
9. **Y al arreglarlo, marco como cortocircuito una continuacion de linea**, que si se evalua.
   En el fixture sintetico, ademas, la extraccion numerica solo recognocia `FIJO:MACRO=8` y no
   `FIJO:8`, produciendo `FIJO{}` — peor que no decir nada.

**Los 9 los cazaron el self-test o la contrastacion con el recuento de mano. Ninguno lo habria
cazado leyendo el codigo con calma.**

## Clasificacion

- `LA_CLASE_COUNT_MENOS_N_ESTA_BARRIDA = PROVEN`: 196 en el arbol, 48 en mi ruta
- `26_DE_48_NO_TIENEN_GUARDIA_PREVIA = PROVEN`: en 15 funciones
- `LOS_10_SIN_GUARDIA_DE_LA_RUTA_DE_OVERDRIVE_ESTAN_EN_4_FUNCIONES = PROVEN`
- `LOS_4_CORTOCIRCUITOS_SON_LOS_FILTROS_DE_120 = PROVEN`: `:809`, `:823`, `:902`, `:918`
- `NINGUNO_DE_MI_RUTA_ES_UN_ARRAY_FLEXIBLE = PROVEN_DERIVED`
- `MI_GREP_DA_35_Y_LA_HERRAMIENTA_DA_48 = PROVEN`: el patron no aceptaba notacion con punto
- `UN_TIPO_EQUIVOCADO_ES_PEOR_QUE_UN_TIPO_DESCONOCIDO = CORRECTED`
- `LOCAL_HOMONIMO_Y_MIEMBRO_NO_ES_EL_MISMO_TIPO = CORRECTED`
- `NUEVE_ERRORES_DE_LA_HERRAMIENTA = CORRECTED`

## Lo que esto obliga a hacer en un driver propio

1. **`count - 1` se escribe con el `count` ya comprobado, no despues.** En 48 sitios de amdgpu,
   26 no lo comprueban. **Es la forma mas barata de un indice negativo** y la mas facil de
   cazar en revision.
2. **Un helper de "ultimo elemento" con el guarda dentro.** No `tabla->entradas[tabla->count-1]`
   esparcido por el codigo, sino `ultimo(entradas, count)` que devuelve error con `count == 0`.
   **Elimina la clase entera de un plumazo**, que es lo que un revisor no puede hacer a ojo.
3. **Y si la excepcion es legitima (el `||` de `224` (antes `120`)), que sea explicita con un comentario.**
   Aqui el cortocircuito es correcto pero invisible: se lee como un `dpm_levels[-1]`.
4. **Un filtro de busqueda se contrasta con una herramienta antes de creerse su numero.**
   35 y 48 son ambos plausibles. **Solo uno es el bueno, y nada en el filtro lo dice.**
5. **Un tipo que no se puede determinar se declara incognita.** `AMBIGUO FIJO{8,16}` dice menos
   que un 8 inventado, y mucho mas que nada.

## Estado

Hallazgo **130**: la clase `count - N` queda barrida y acotada, con la concentracion en la
ruta de overdrive como dato principal. **Y queda un `NOT_DETERMINED` sin cerrar:** si algum
`count` puede valer cero en mi placa, que es lo que decide si alguno de estos 26 es un indice
negativo real.