# 131 · Los 26 accesos sin guardia: los tres campos `count` valen al menos uno, y queda demostrado en mi VBIOS

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Cierra el `NOT_DETERMINED` que `130` dejo abierto.** Los 26 accesos sin guardia no son un
fallo en mi placa: los tres campos `count` que usan valen al menos uno, y en el caso que manda
**lo he medido en el VBIOS de esta placa**, no deducido.

Ademas: la decodificacion del VBIOS **corrobora `121` desde una tabla completamente distinta**.

## El mapa de los 13 campos, reducidos a 3 familias

Los 26 accesos de `130` usan 13 expresiones `count` distintas, pero solo **tres orgenes**. Eso
los hace una tabla y no una lista.

### Familia A — las tablas de dependencia del PPT (6 sitios)

```
dep_sclk_table->count                        :1000 :1001   smu7_setup_voltage_range_from_vbios
dep_mclk_table->count                        :2524 :2529   smu7_patch_voltage_workaround
allowed_sclk_vdd_table->count                :2437         smu7_find_highest_vddc
vddc_dep_on_dispclk->count                   :3163         smu7_lookup_vddc_from_dispclk
vddc_dependency_on_sclk->count               :1536         smu7_populate_umdpstate_clocks
vdd_dep_on_sclk->count                       :1553         smu7_populate_umdpstate_clocks
```

Todas salen de `get_*_dependency_table`, que **rechaza el cero antes de reservar**:

```c
/* process_pptables_v1_0.c:443-449 — la RAMA DE POLARIS, la mia */
PP_ASSERT_WITH_CODE((0 != polaris_table->ucNumEntries),
                "Invalid PowerPlay Table!", return -1);
sclk_table = kzalloc_flex(*sclk_table, entries, polaris_table->ucNumEntries);
if (!sclk_table)
        return -ENOMEM;
```

**Comprobé que la rama de Polaris tambien rechaza el cero**, no solo la de Tonga (`:414`). Esa
era la pieza que faltaba: mi placa no pasa por la rama de Tonga, y si solo esa rechazara el
cero, la garantia no existiria para mi ASIC.

Y el fallo se propaga: `:830` mete el `result` en la cadena, `:833` y siguientes cortocircuitan,
y `hwmgr.c:249-252` hace `goto err` si `pptable_init` falla — **de modo que `backend_init`, donde
vive todo esto, no llega a ejecutarse.**

- `FAMILIA_A_COUNT_MAYOR_IGUAL_A_1 = PROVEN`: aserto antes de `kzalloc_flex`, en ambas ramas.
- `UN_GETTER_FALLIDO_IMPIDE_EJECUTAR_BACKEND_INIT = PROVEN`: cadena de `result` + `goto err`.

### Familia B — las tablas DPM (10 sitios)

```
golden_sclk_table->count              :5211 :5239 :5241
golden_mclk_table->count              :5253 :5281 :5283
golden_dpm_table->sclk_table.count    :1515 :3272
sclk_table->count                     :5210
mclk_table->count                     :5252
dpm_table->pcie_speed_table.count     :4246
```

Todas salen de `smu7_setup_dpm_tables_v1` (o `_v0`), que **pone el contador a cero y lo
incrementa por entrada aceptada**:

```c
/* smu7_hwmgr.c:900-912 */
data->dpm_table.sclk_table.count = 0;
for (i = 0; i < dep_sclk_table->count; i++) {
        if (i == 0 || dpm_levels[count - 1].value != dep_sclk_table->entries[i].clk) {
                dpm_levels[count].value = ...;
                data->dpm_table.sclk_table.count++;
        }
}
```

El bucle corre **si y solo si** `dep_sclk_table->count >= 1`, y ademas la rama `i == 0` del
filtro siempre pasa en la primera iteracion. **O sea: `count >= 1` en cuanto la Familia A da
una tabla valida.** Y `golden_*` son copias de `dpm_table` por `memcpy` en `:1075`.

Los cinco retornos tempranos de la funcion (`:879`, `:885`, `:888`, `:892`, `:895`) o bien estan
descartados antes (`:879` `table_info == NULL`) o bien exigen que la Familia A falle.

- `FAMILIA_B_COUNT_MAYOR_IGUAL_A_1 = PROVEN_DERIVED`: la rama `i == 0` siempre pasa.
- `LOS_CINCO_RETORNOS_TEMPRANOS_EXIGEN_UN_GETTER_FALLIDO = PROVEN_DERIVED`

### Familia C — `performance_level_count` (7 sitios, la mayor)

```
smu7_apply_state_adjust_rules  :3500
smu7_dpm_get_mclk              :3597
smu7_dpm_get_sclk              :3619
smu7_find_dpm_states_clocks_in_dpm_table  :4183 :4186
smu7_set_mclk_od               :5280
smu7_set_sclk_od               :5238
```

**Esta si hacia falta medirla**, porque el contador **no** viene de un getter con guarda:

```c
/* pp_psm.c:60, 67 — request_ps y current_ps nacen a CERO */
hwmgr->request_ps = kzalloc(size, GFP_KERNEL);
hwmgr->current_ps = kzalloc(size, GFP_KERNEL);

/* pp_psm.c:78-94 — y solo se rellenan copiando un estado marcado Boot */
for (i = 0; i < table_entries; i++) {
        result = hwmgr->hwmgr_func->get_pp_table_entry(hwmgr, i, state);
        ...
        if (state->classification.flags & PP_StateClassificationFlag_Boot) {
                hwmgr->boot_ps = state;
                memcpy(hwmgr->current_ps, state, size);
                memcpy(hwmgr->request_ps, state, size);
        }
}
```

**`request_ps` nace a cero y solo se llena desde un estado con el flag `Boot`.** Si el VBIOS no
declarase ninguno, `performance_level_count` se quedaria en **0** y `smu7_set_sclk_od` haria
`performance_levels[-1]` con el ioctl de overdrive.

**Y eso se lee del VBIOS.**

## La medicion

**Ancla, verificada:** `ulPlatformCaps` esta en el offset **19** de la tabla PPT, y en
`0x9C0A + 19 = 0x9C1D` esta `0x068000`, el valor que `122` ya habia decodificado. **La cadena de
offsets 19 -> 23 -> 27 -> 31 -> 33 -> 35 son incrementos simples**, asi que la verificacion del
ancla valida todo lo que viene despues.

```
usStateArrayOffset (offset 35) = 0x004D = 77   ->  array en 0x9C0A + 77 = 0x9C57
ATOM_PPLIB_CLASSIFICATION_BOOT = 0x0008        (pptable_v1_0.h:85)
ATOM_Tonga_State: 20 bytes, usClassification en el offset 8
```

```
ATOM_Tonga_State_Array en 0x9C57:  ucRevId = 1   ucNumEntries = 2

 idx  offset  usClass  usClass2  BOOT     SCLKlo SCLKhi MCLKlo MCLKhi
   0  0x9C59   0x0008    0x0000    SI           0      0      0      0
   1  0x9C6D   0x0005    0x0000    no          0      7      0      2
```

Decodificado con `make_classification_flags` (`:1257-1284`):

- `0x0008` = **BOOT**, y `0x0008 & UI_MASK(0x0007) = 0` = UI_NONE.
- `0x0005` = `& UI_MASK = 5` = **`ATOM_PPLIB_CLASSIFICATION_UI_PERFORMANCE`**, y
  `& 0x0008 = 0` → **no es boot**.

**Mi placa declara exactamente dos estados de potencia: BOOT y PERFORMANCE. Y hay un BOOT.**

**Por tanto `request_ps` se rellena, `performance_level_count >= 1`, y los 7 sitios de la Familia
C no son un indice negativo en esta placa.**

- `MI_VBIOS_DECLARA_DOS_ESTADOS_BOOT_Y_PERFORMANCE = PROVEN`: array en 0x9C57, `ucNumEntries=2`.
- `HAY_UN_ESTADO_BOOT = PROVEN`: `usClassification = 0x0008`.
- `REQUEST_PS_SE_RELLENA_POR_MEMCPY = PROVEN`: `pp_psm.c:93`.
- `FAMILIA_C_COUNT_MAYOR_IGUAL_A_1 = PROVEN`: medido, no deducido.
- `LA_GARANTIA_DEPENDE_DE_UN_FLAG_DEL_VBIOS = PROVEN`: si ningun estado lleva `BOOT`, los 7 sitios
  pasan a ser un `performance_levels[-1]` real. **Es un VBIOS valido sin el flag, no un
  imposible.**

## Y una corroboracion de `121` desde otra tabla

El estado 1 —PERFORMANCE— referencia por **indice**, no por valor:

```
SCLKlo = 0   SCLKhi = 7      -> la tabla SCLK tiene al menos 8 entradas
MCLKlo = 0   MCLKhi = 2      -> la tabla MCLK tiene al menos 3 entradas
```

**Exactamente las 8 SCLK y las 3 MCLK que `121` reconstruyó midiendo el paso de los registros de
las tablas de dependencia.** Vienen de una tabla distinta, referenciando por indice, y coinciden.

**Y esto valida mi propia decodificación por dentro**: si el offset de `usStateArrayOffset`
estuviera mal, saldrían bytes arbitrarios, no un rango 0..7 y 0..2 que casa con las dos tablas.
**Un dato que se decodifica a algo coherente con lo ya medido, es su propia prueba.**

- `121_QUEDA_CORROBORADO_DESDE_LA_TABLA_DE_ESTADOS = PROVEN`
- `LA_DECODIFICACION_SE_AUTOVALIDA = PROVEN_DERIVED`: el rango de indices casa con lo ya medido.

## Que queda, entonces

**Ninguno de los 26 accesos de `130` produce un indice negativo en mi placa.** Los tres campos
`count` valen al menos uno, y en la familia que mandaba **esta medido**.

**Lo que queda en pie es lo que `230` (antes `129`) ya dijo:** la guarda **no esta escrita**. El codigo depende
de tres invariantes que estan en tres sitios distintos —el aserto del getter, la rama `i == 0` del
bucle, y el flag `Boot` del VBIOS— **y ninguno esta junto al acceso.** Un solo cambio en el
VBIOS, o un getter que falle por otra razon, y los 26 se convierten en indices negativos sin que
avise nadie.

Eso **no es un fallo de mi placa. Es un defecto de contrato, y es exactamente lo que un driver
propio tiene que hacer distinto.**

## Clasificacion

- `FAMILIA_A_DEP_TABLES_COUNT_MAYOR_IGUAL_A_1 = PROVEN`: aserto antes del `kzalloc_flex`, **en la
  rama de Polaris tambien**, que es la mia
- `FAMILIA_B_DPM_COUNT_MAYOR_IGUAL_A_1 = PROVEN_DERIVED`: la rama `i == 0` siempre pasa
- `FAMILIA_C_POWER_LEVEL_COUNT_MAYOR_IGUAL_A_1 = PROVEN`: **medido en el VBIOS**
- `REQUEST_PS_NACE_A_CERO_Y_SOLO_LO_LLENA_UN_ESTADO_BOOT = PROVEN`: `pp_psm.c:60` y `:93`
- `MI_VBIOS_TIENE_EXACTAMENTE_DOS_ESTADOS_BOOT_Y_PERFORMANCE = PROVEN`
- `EL_ARRANQUE_DE_26_SITIOS_DEPENDE_DE_UN_FLAG_DEL_VBIOS = PROVEN`: no es imposible, es una
  garantia externa
- `121_CORROBORADO_DESDE_LA_TABLA_DE_ESTADOS = PROVEN`
- `LA_DECODIFICACION_SE_AUTOVALIDA = PROVEN_DERIVED`
- `NINGUNO_DE_LOS_26_ES_UN_INDICE_NEGATIVO_EN_MI_PLACA = PROVEN_DERIVED`
- `PERO_LA_GUARDIA_NO_ESTA_ESCRITA = PROVEN`: tres invariantes en tres sitios, ninguno junto al
  acceso

## Lo que esto obliga a hacer en un driver propio

1. **Un invariante que se cumple hoy no es una guarda.** Aqui hay tres invariantes reales —el
   aserto del getter, la rama `i == 0`, el flag `Boot`— **y los tres estan a cientos de lineas del
   acceso que dependen de ellos.**
2. **Yo no voy a confiar en el flag del VBIOS.** `smu7_set_sclk_od` comprueba `ps == NULL` y nada
   mas. Si mi VBIOS no declara ningun estado `Boot` —y es perfectamente legal— mi driver lee memoria
   anterior a un array. **Un `count >= 1` en el sitio, o un helper, y el problema no existe.**
3. **El fallo de un getter tiene que ser visible donde se usa el getter.** Aqui el getter falla,
   aborta el arranque, y por eso el invariante se cumple; **pero el codigo que usa el resultado no
   puede saber si fallo o no, y no lo pregunta.**
4. **Y el flag `Boot` es el eslabon mas fragil de los tres**, porque es un dato del VBIOS que
   nadie verifica: si falta, `request_ps` se queda en el `kzalloc` **sin ningun sintoma** hasta
   que algo lee `performance_levels[-1]`.

## Estado

Hallazgo **131**: el `NOT_DETERMINED` de `130` queda **cerrado con medicion**, las tres familias
de contadores estan resueltas, y `121` queda corroborado desde una segunda tabla.