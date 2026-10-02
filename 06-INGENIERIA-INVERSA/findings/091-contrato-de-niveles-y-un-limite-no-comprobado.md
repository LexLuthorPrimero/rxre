# 091 · El contrato de "cuantos niveles son validos" y un limite que no se comprueba

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El contrato del contador de niveles

La tabla DPM tiene hueco para 8 niveles de graficos, pero el host puede querer menos.
El contrato es que **el contador es el marcador de validez y la copia es
incondicional**.

`polaris10_smumgr.c:1097-1098` y `:1146-1148`:

```c
smu_data->smc_state_table.GraphicsDpmLevelCount = (uint8_t)dpm_table->sclk_table.count;
...
/* level count will send to smc once at init smc table and never change */
result = smu7_copy_bytes_to_smc(hwmgr, array, (uint8_t *)levels, (uint32_t)array_size, SMC_RAM_END);
```

con `array_size = sizeof(SMU74_Discrete_GraphicsLevel) * SMU74_MAX_LEVELS_GRAPHICS`, es
decir los 8 huecos, **pase lo que pase con el contador**.

O sea: el host sube siempre 448 bytes y le dice aparte cuantos son buenos. Los niveles
no poblados viajan con lo que tuvieran y el firmware no los debe mirar. El comentario
del propio driver lo dice: el contador se manda una vez al inicializar y no cambia.

Un driver propio tiene que hacer exactamente eso. Poner el contador a 3 y subir solo
tres niveles deja los otros cinco con basura, y con basura el firmware puede elegir un
nivel que no existe.

`EnabledForActivity` es el bit `i` de la mascara de niveles habilitados, indexado por
el mismo `i` (`polaris10_smumgr.c:1102-1104`):

```c
for (i = 0; i < GraphicsDpmLevelCount; i++)
        GraphicsLevel[i].EnabledForActivity =
                (sclk_dpm_enable_mask & (1 << i)) >> i;
```

Y `pcieDpmLevel` mapea cada nivel de graficos a su nivel de PCIe. Con tabla de PCIe
presente, `levels[i].pcieDpmLevel = i < max_entry ? i : max_entry`, o sea el ultimo
nivel se repite para todos los que no tienen. Sin tabla, se calculan el mas alto, el mas
bajo y uno intermedio para los niveles 0, 1 y el resto.

## Donde no se comprueba el limite

Los 8 niveles no son un limite arbitrario: `MAX_REGULAR_DPM_NUMBER` es 8
(`smu7_hwmgr.h:95`) y `SMU74_MAX_LEVELS_GRAPHICS` es 8 (`smu74.h:134`, que resuelve a
`SMU__NUM_SCLK_DPM_STATE` = 8). Coinciden.

Lo que no coincide nunca se comprueba. La tabla de niveles se **deriva** de la tabla de
dependencia de voltaje de la PowerPlay Table, y el bucle no tiene guarda contra el
limite. Este es el camino **v1**, que es el que se ejecuta en Polaris12
(`smu7_hwmgr.c:869-912`):

```c
dep_sclk_table = table_info->vdd_dep_on_sclk;
...
PP_ASSERT_WITH_CODE(dep_sclk_table->count >= 1,
                "SCLK dependency table count is 0.", return -EINVAL);

data->dpm_table.sclk_table.count = 0;

for (i = 0; i < dep_sclk_table->count; i++) {
        if (i == 0 || dpm_levels[count - 1].value != dep_sclk_table->entries[i].clk) {
                dpm_levels[count].value = ...;
                dpm_levels[count].enabled = ...;
                data->dpm_table.sclk_table.count++;
        }
}
```

No hay `if (count >= MAX_REGULAR_DPM_NUMBER) break;`. El bucle esta acotado por
`dep_sclk_table->count`, que viene de la PPT (`process_pptables_v1_0.c:422`, desde
`ucNumEntries`), es decir de datos externos. La unica comprobacion es `count >= 1`.

La deduplicacion solo puede hacer que `count` crezca mas despacio que `i`, nunca mas:
en el peor caso hay un nivel por entrada de la tabla de dependencia.

### Una correccion de atribucion

Una version anterior de este documento atribua el fallo a
`smu7_setup_dpm_tables_v0` (`smu7_hwmgr.c:781`), que tiene el mismo bucle. La
atribucion era **equivocada** y por poco se publica:

- `smu7_setup_default_dpm_tables` (`smu7_hwmgr.c:1061-1072`) despacha segun
  `hwmgr->pp_table_version`.
- El defecto es `PP_TABLE_V1` (`hwmgr.c:86`).
- `PP_TABLE_V0` se asigna **solo** en dos sitios: el bloque de `ci_smu_funcs`
  (`hwmgr.c:105`) y el de `iceland_smu_funcs` (`hwmgr.c:140`). Es decir, Carrizo y
  Topaz/Iceland. En ningun caso Polaris12.

Con lo que el camino v0 no se ejecuta en esta placa, y la version anterior iba a
declarar como fallo vivo de Polaris12 algo que solo ocurre en Carrizo. El fallo es real
y esta en el camino correcto: **v1**. Lo que fallo fue el recorrido, no el codigo.

Comprobado lo mismo para el camino v0: el bucle de `smu7_hwmgr.c:806` tampoco comprueba
el limite. Los dos caminos tienen el patron; solo uno se usa aqui.

## A donde cae el desbordamiento

Medido con la herramienta, no estimado:

```
smu7_dpm_level        = 12 bytes    (u8 enabled + 3 relleno + u32 value + u32 param1)
smu7_single_dpm_table = 100 bytes   (count 4 + 8 x 12 = 96)
smu7_dpm_table        = 600 bytes   (seis tablas de 100)
  sclk_table  @   0
  mclk_table  @ 100
  pcie_table  @ 200
  vddc_table  @ 300
  vddci_table @ 400
  mvdd_table  @ 500
```

`dpm_levels[8]` empieza en el offset `4 + 8*12 = 100`, que es **exactamente donde empieza
`mclk_table`**. Es decir: el noveno nivel de graficos no corrompe memoria arbitraria,
escribe justo sobre `mclk_table.count`. Y ese campo se usa despues para construir los
niveles de memoria, asi que la corrupcion no se queda en un sitio: se propaga al
contador de niveles de memoria.

La tabla de niveles de graficos va primera en `smu7_dpm_table` a proposito. Si fuera la
ultima, el desbordamiento caeria fuera de la estructura. Que caiga justo sobre el campo
de al lado es peor que si cayera al final, porque el valor corrupto es un `uint32_t` que
se usa como longitud de otro bucle.

## Lo que esto es y lo que no es

Es una **falta de comprobacion de limites** en el driver de upstream. No es un fallo
explotable tal cual, y conviene decirlo:

- El dato viene de la PowerPlay Table, que el driver valida como tabla firmada y
  coherente antes de usarla.
- La deduplicacion hace que en uso normal `count` no supere el numero de frecuencias
  distintas que hay.
- El hardware tiene 8 niveles de SCLK, asi que una PPT valida para esta placa tiene 8 o
  menos entradas.

Lo que si es cierto y accionable: **la seguridad del bucle depende de que
`MAX_REGULAR_DPM_NUMBER` y `SMU74_MAX_LEVELS_GRAPHICS` valgan lo mismo, y de que la PPT
tenga como mucho 8 frecuencias de SCLK distintas.** Ninguna de las dos cosas esta
comprobada en el codigo, y estan a dos ficheros de distancia: uno en `smu7_hwmgr.h` y el
otro en `smu74.h`. Son dos constantes que coinciden hoy, en dos headers distintos, sin
ninguna invariante que lo exija.

## Que hace un driver propio

Acotar, y no confiar en la coincidencia:

```
count = min(count, SMU74_MAX_LEVELS_GRAPHICS)
```

antes de escribir el noveno nivel, y volver a acotar despues de calcular
`GraphicsDpmLevelCount`. Es una linea y convierte una dependencia invisible entre dos
ficheros en una invariante explicita.

Aparte, lo del contrato de la seccion anterior: subir **siempre** el array entero y
poner el contador aparte. Es lo que hace el driver y no es negociable.

## Clasificacion

- `SMC_LEVEL_COUNT_CONTRACT = PROVEN`: el contador marca la validez y la copia sube
  siempre los 8 huecos. Comentario explicito en `polaris10_smumgr.c:1146`.
- `SMC_LEVEL_ARRAY_SIZE = PROVEN`: `MAX_REGULAR_DPM_NUMBER` = 8 y
  `SMU74_MAX_LEVELS_GRAPHICS` = 8.
- `SMC_LEVEL_COUNT_UNBOUNDED_LOOP = PROVEN`: el bucle de `smu7_setup_dpm_tables_v1`
  (`smu7_hwmgr.c:869`) no comprueba el limite y esta acotado por un dato externo. Es el
  camino vivo en Polaris12.
- `SMC_LEVEL_COUNT_LOOP_V0 = PROVEN`: el camino v0, `smu7_setup_dpm_tables_v0`
  (`smu7_hwmgr.c:781`), tiene el mismo patron sin cota, y **no se ejecuta en
  Polaris12**: `PP_TABLE_V0` solo se activa para Carrizo y Topaz/Iceland.
- `SMC_LEVEL_OVERFLOW_TARGET = PROVEN`: el noveno nivel escribe en offset 100, que es
  `mclk_table.count`.
- `SMC_LEVEL_TABLE_ORDERED_FIRST = PROVEN`: `sclk_table` es la primera de las seis
  tablas de `smu7_dpm_table`.

## Lo que esto NO dice

No dice que haya happenedo nunca. Requiere una PowerPlay Table con mas de ocho
frecuencias de SCLK distintas, que no es una PPT valida para este hardware.

No he ejecutado nada contra la PPT de esta placa. Es un hallazgo **estatico**: el
codigo no comprueba un limite que podria no cumplirse.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.