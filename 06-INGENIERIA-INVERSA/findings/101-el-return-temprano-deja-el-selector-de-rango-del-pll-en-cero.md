# 101 · El `return` temprano deja el selector de rango del PLL permanentemente en cero

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La cadena

Tres funciones, un `return` mal puesto en la primera, y un efecto que llega hasta el
calculo del reloj de graficos.

### 1. `polaris10_get_sclk_range_table` tiene dos ramas y solo una rellena el array

`polaris10_smumgr.c:853-880`:

```c
struct pp_atom_ctrl_sclk_range_table range_table_from_vbios = { { {0} } };   /* 853 */
ref_clk = amdgpu_asic_get_xclk((struct amdgpu_device *)hwmgr->adev);

if (0 == atomctrl_get_smc_sclk_range_table(hwmgr, &range_table_from_vbios)) {  /* 857 */
        for (i = 0; i < NUM_SCLK_RANGE; i++) {
                table->SclkFcwRangeTable[i].vco_setting = ...;                /* 859-868 */
                ...
        }
        return;                                                              /* 870 */
}

/* la otra rama, la de caimiento */
for (i = 0; i < NUM_SCLK_RANGE; i++) {
        smu_data->range_table[i].trans_lower_frequency =
                (ref_clk * Range_Table[i].fcw_trans_lower) >> Range_Table[i].postdiv;  /* 874 */
        smu_data->range_table[i].trans_upper_frequency =
                (ref_clk * Range_Table[i].fcw_trans_upper) >> Range_Table[i].postdiv;  /* 875 */
        ...
}
```

**El `return` de `:870` se ejecuta cuando el VBIOS APORTA la tabla**, o sea en el camino
que funciona. Y se lleva por delante el bucle de `:874-875`, que es el **unico** que
escribe `smu_data->range_table[i].trans_lower_frequency` y `trans_upper_frequency`.

O sea: **en el camino normal, ese array se queda con los ceros del `kzalloc`.** En el
unico camino donde se rellena, es el de caimiento, que no se llega si el VBIOS funciona.

Lo irónico del caso es que el array que se rellena es `range_table_from_vbios`, que
**si** esta inicializado a cero (`:853`), mientras que el que se deja a cero
(`smu_data->range_table`) no depende de esa inicializacion: depende de no escribirse.

### 2. El consumidor compara contra un rango vacio

`polaris10_calculate_sclk_params`, rama de caimiento, `:922-928`:

```c
for (i = 0; i < NUM_SCLK_RANGE; i++) {
        if (clock > smu_data->range_table[i].trans_lower_frequency
        && clock <= smu_data->range_table[i].trans_upper_frequency) {
                sclk_setting->PllRange = i;
                break;
        }
}
```

Con el array a cero, la condicion es `clock > 0 && clock <= 0`. **Siempre falsa**, para
cualquier reloj positivo. Asi que el bucle corre entero sin ejecutar el `break`, y
`PllRange` conserva su valor inicial.

### 3. Y `Fcw_int` se calcula con el postdiv del rango equivocado

`:930-934`:

```c
sclk_setting->Fcw_int = (uint16_t)((clock << table->SclkFcwRangeTable[sclk_setting->PllRange].postdiv) / ref_clock);
temp = clock << table->SclkFcwRangeTable[sclk_setting->PllRange].postdiv;
temp <<= 0x10;
do_div(temp, ref_clock);
sclk_setting->Fcw_frac = temp & 0xffff;
```

`PllRange` vale lo que valia antes. En el camino de los niveles graficos, eso es 0 del
`SMU_SclkSetting curr_sclk_setting = { 0 };` de `:964`. O sea: **`Fcw_int` y `Fcw_frac`
se calculan con el `postdiv` del rango 0**, que es un rango de PLL, pero no
necesariamente el que corresponde a la frecuencia pedida.

Un `postdiv` mayor produce un `Fcw_int` mayor para la misma frecuencia; uno menor, menor.
Como el `postdiv` va en el desplazamiento, un factor de 2 o de 4 en el divisor cambia el
resultado de forma proporcional y el reloj resultante tambien.

## El caso ACPI es peor: valor rancio en vez de cero

`:1302` escribe `PllRange` (y el resto del `SclkSetting`) **directamente sobre
`table->ACPILevel.SclkSetting`**, sin struct local intermediaria. Ahi no hay un
`= { 0 }` que proteja: `PllRange` conserva lo que hubiera, que en la primera pasada es
cero del `kzalloc`, y en **cualquier pasada posterior** es un valor de la llamada
anterior.

Es el unico caso de la ruta donde el campo llega rancio. En todos los demas hay una
inicializacion que lo pone a cero. Es `EVIDENCE_MISSING` si `init_smc_table` puede
invocarse mas de una vez; el mecanismo esta `PROVEN`.

## Y un detalle que si es un defecto, pero NO es lo que decia el agente

El agente afirmo que en `polaris10_populate_clock_stretcher_data_table`, tras el
comentario `/* Populate CKS Lookup Table */` (`:1695`) **no hay ninguna instruccion**.

**Es falso, y lo he leido.** `:1695-1702`:

```c
/* Populate CKS Lookup Table */
if (stretch_amount == 0 || stretch_amount > 5) {
        phm_cap_unset(hwmgr->platform_descriptor.platformCaps,
                PHM_PlatformCaps_ClockStretcher);
        PP_ASSERT_WITH_CODE(false,
                "Stretch Amount in PPTable not supported",
                return -EINVAL);
}
```

Debajo del comentario hay codigo, y si el `stretch_amount` es invalido la funcion
**retorna `-EINVAL`** tras quitar la capability. Eso es una comprobacion real. El
comentario esta mal colocado, o alude a lo que hace la funcion en conjunto, pero la
afirmacion de "comentario sin codigo" no se sostiene.

Lo que si es cierto de esa funcion, y lo anoto aparte porque es de otro tipo:
`stretch_amount` se lee y se usa para la comprobacion, pero **no se guarda en
`table->ClockStretcherAmount`**. Ese campo queda a cero. Si el firmware espera leelo
ahi, lee 0. Que lo espere: `SEMANTIC_MISSING`.

## Lo que NO dice

No dice que el reloj que se programa este mal **en esta placa**. Depende de si el VBIOS
aporta la tabla de rangos, y de si la frecuencia pedida cae dentro de lo que el rango 0
puede cubrir. Si el VBIOS tiene una sola fila, el rango 0 es el correcto y no hay
diferencia. Eso es `RUNTIME_MISSING`.

No dice que `Fcw_int` sea invalido. Es un valor bien formado; lo que no se puede afirmar
sin el firmware es si corresponde al reloj pedido.

No hay lectura de hardware, no hay escritura, no hay `/sys`, no hay modulos.

## Clasificacion

- `SCLK_RANGE_TABLE_NEVER_FILLED_ON_VBIOS_PATH = PROVEN`: `polaris10_smumgr.c:870` es un
  `return` dentro de la rama de exito (`:857`), y el unico bucle que escribe
  `smu_data->range_table[i].trans_*_frequency` es `:874-875`, en la rama de fallo.
- `SCLK_RANGE_SELECTOR_ALWAYS_FALSE = PROVEN_DERIVED`: con el array a cero, la condicion de
  `:923-924` es `clock > 0 && clock <= 0`, falsa para cualquier reloj positivo.
- `SCLK_PLL_RANGE_STAYS_AT_ZERO = PROVEN`: no hay rama que asigne cuando el bucle no
  encuentra. El valor inicial viene del `= { 0 }` de `:964`.
- `SCLK_FCW_USES_WRONG_POSTDIV = PROVEN` el mecanismo, `SEMANTIC_MISSING` si el rango 0 no
  corresponde a la frecuencia pedida.
- `SCLK_ACPI_RANGE_IS_STALE = PROVEN` el mecanismo (`:1302` escribe sobre la tabla de heap
  sin struct local), `EVIDENCE_MISSING` si `init_smc_table` corre mas de una vez.
- `SCLK_CKS_STRETCH_AMOUNT_NOT_STORED = PROVEN`: se lee y valida (`:1696`), no se escribe en
  `table->ClockStretcherAmount`.
- `SCLK_CKS_STRETCH_HAS_REAL_CHECK = PROVEN`: **refuta** la afirmacion del agente de que
  detras del comentario no hay codigo. `:1696-1702` valida y retorna `-EINVAL`.

## Lo que esto obliga a hacer en un driver propio

Un `return` en medio de una funcion de relleno tiene que ser explicito sobre que deja sin
escribir. Aqui el `return` de exito deja sin escribir un array que **otra funcion lee para
decidir que divisor de PLL usar**. En un driver propio, las dos funciones estan separadas
y el contrato entre ellas no esta escrito en ningun sitio.

La regla que sale: **si una funcion escribe en un array que otra lee, y la primera tiene
mas de una rama, cada rama tiene que dejar el array completo o devolver un error.** El
`return` silencioso de exito es el peor caso, porque parece el camino bueno.
