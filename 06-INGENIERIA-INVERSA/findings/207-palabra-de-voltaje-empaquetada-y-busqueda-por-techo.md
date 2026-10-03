# 207  El voltaje es una palabra empaquetada de tres rails, y la busqueda tiene un indice sin verificar

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## Antes de nada: este camino se ejecuta en Polaris12

Por lo que enseño `206`, se comprueba antes de afirmar nada.

`polaris10_get_dependency_volt_by_clk` esta definida en `polaris10_smumgr.c:353` y se
llama desde las tres funciones de relleno de nivel de la ruta Polaris10:

```
polaris10_smumgr.c:975   nivel de graficos   -> &level->MinVoltage
polaris10_smumgr.c:1170  nivel de memoria    -> &mem_level->MinVoltage
polaris10_smumgr.c:1293  nivel ACPI          -> &table->ACPILevel.MinVoltage
```

Y `polaris10_smumgr.c` es la ruta de Polaris12: `hwmgr.c:157` selecciona
`polaris10_smu_funcs` para este ASIC, y la rama de `CHIP_POLARIS12` no cambia de
`smumgr_funcs`. Es el camino vivo, no un camino alternativo.

## Parte 1 · que es realmente `MinVoltage`

`MinVoltage` es de tipo `SMU_VoltageLevel`, que en `smu74.h:342` es un `uint32_t` pelado,
no una estructura. Y no es un milivoltio: es una **palabra de 32 bits con tres campos
empaquetados**.

Las constantes, `smu74.h:336-340`:

```c
#define VDDC_SHIFT   0
#define VDDCI_SHIFT  15
#define PHASES_SHIFT 30
```

| bits | ancho | contenido |
|---:|---:|---|
| 0..14 | 15 | VDDC |
| 15..29 | 15 | VDDCI |
| 30..31 | 2 | PHASES |

Y cada valor va multiplicado por `VOLTAGE_SCALE` = 4 (`hwmgr.h:38`):

```c
*voltage |= (entries[i].vddc  * VOLTAGE_SCALE) << VDDC_SHIFT;
*voltage |= (entries[i].vddci * VOLTAGE_SCALE) << VDDCI_SHIFT;
*voltage |= 1 << PHASES_SHIFT;        /* PHASES no es un voltaje: son las fases */
```

Lo confirma el rango: 2500 mV × 4 = 10000, y el campo admite hasta 32767. Con
resolucion de 0.25 mV.

**VDDC, VDDCI y MVDD van en la misma palabra.** Un driver propio que escriba ahi un
milivoltio a pelo no esta dando un voltaje erroneo: esta **partiendo la palabra en tres**,
y las tres partes significan cosas distintas.

`VOLTAGE_SCALE` aparece en el host **solo como multiplicador**. No hay ninguna division
en ningun sitio del subarbol: el `÷4` lo hace el firmware. `FW_SMU_INTERPRETATION`
sigue siendo `NOT_IN_CORPUS` en lo que respecta a quien deshace la escala.

La unidad se fija por comparacion con un valor fisico: `VDDC_VDDCI_DELTA` = 200 en
polaris10 (`polaris10_smumgr.c:57`), y en Fiji 300. Es la diferencia entre el rail de
graficos y el de memoria en la misma tabla de dependencia. Una diferencia de 200 unidades
entre voltajes que difieren en unos cientos de milivoltios solo tiene sentido si la
unidad es el milivoltio. Los valores de la PowerPlay Table estan en **mV**.

## La regla del busqueda: techo, con desempate a la izquierda

`polaris10_smumgr.c:367-369`:

```c
for (i = 0; i < dep_table->count; i++) {
        /* find first sclk bigger than request */
        if (dep_table->entries[i].clk >= clock) {
```

Para un reloj pedido se toma la **primera entrada cuyo reloj es mayor o igual**. O sea un
escalon con techo, no una interpolacion y no un redondeo al mas proximo.

Si ninguna entrada cumple, se usa la ultima (`polaris10_smumgr.c:398`):

```c
/* sclk is bigger than max sclk in the dependence table */
*voltage |= (dep_table->entries[i - 1].vddc * VOLTAGE_SCALE) << VDDC_SHIFT;
```

O sea: por encima del tope de la tabla se clava el valor del tope. La curva de
voltaje es plana a partir de ahi.

La misma regla esta en `phm_find_closest_vddci` (`smu_helper.c:429`), con un `pr_debug`
cuando se cae al ultimo valor.

**Las dos busquedas presuponen que la tabla esta ordenada ascendente y nada lo
comprueba.** La tabla viene de la PowerPlay Table, que es externa. Una tabla desordenada
no da un voltaje raro: da el primer techo que aparezca, que es un valor de la tabla y
por tanto completamente plausible.

## Parte 2 · un indice que no se ha verificado

`phm_find_closest_vddci`, `smu_helper.c:429-440`:

```c
uint16_t phm_find_closest_vddci(struct pp_atomctrl_voltage_table *vddci_table, uint16_t vddci)
{
        uint32_t  i;

        for (i = 0; i < vddci_table->count; i++) {
                if (vddci_table->entries[i].value >= vddci)
                        return vddci_table->entries[i].value;
        }

        pr_debug("vddci is larger than max value in vddci_table\n");
        return vddci_table->entries[i-1].value;
}
```

Con `count == 0` el bucle no se ejecuta, `i` se queda en **0**, y `entries[i - 1]` es
`entries[0xFFFFFFFF]`: `i` es `uint32_t`, la resta da un desbordamiento y la lectura es
fuera del array.

Con `count >= 1` el `i-1` es la ultima entrada y esta bien. El problema es **solo**
`count == 0`.

### Se puede llegar?

La cadena entera, comprobada:

1. `amdgpu_atombios.c:1419`: `voltage_table->count = gpio->ucGpioEntryNum;`
2. `amdgpu_atombios.c:1407`: valida el **limite superior**, `ucGpioEntryNum >
   MAX_VOLTAGE_ENTRIES` devuelve `-EINVAL`. **No valida el inferior.**
3. Con `ucGpioEntryNum == 0` el almacenamiento termina con `return 0`, o sea **exito**.
4. En el subarbol de powerplay **no hay ningun assert de `count >= 1`** para
   `vddci_voltage_table`. Buscado: solo hay `count >= 1` para la tabla de dependencia
   SCLK y MCLK.

Las precondiciones para llegar a la lectura fuera de rango son tres, todas a la vez:

- el objeto de voltaje del VBIOS tiene cero entradas, y el driver lo acepta con exito
- `vddci_control` **no** es `SMU7_VOLTAGE_CONTROL_NONE`, que es lo unico que evita la
  llamada (si es NONE se usa `vbios_boot_state.vddci_bootup_value`)
- alguna entrada de la tabla de dependencia tiene `vddci == 0`, que es lo que hace caer
  en la rama de la busqueda

No he ejecutado nada contra el VBIOS de esta placa. **Es un hallazgo estatico:** el
codigo acepta un `count` de cero en la lectura y no lo comprueba antes de indexar con
`i - 1`.

### Lo que esto NO es

No es un fallo explotable tal cual. Requiere un VBIOS con un objeto de voltaje vacio, que
es un VBIOS raro pero no imposible, y dos condiciones mas. No lo he comprobado en esta
placa y no hay forma de comprobarlo sin tocar hardware.

Es un **fallo de robustez con una firma concreta**: un `count` que se acepta en cero y un
`-1` sobre un indice sin comprobar. Una correccion de una linea lo haria imposible:

```c
if (vddci_table->count == 0)
        return 0;
```

## Lo que un driver propio hace con esto

1. Escribir `MinVoltage` como palabra empaquetada de tres campos, no como un voltaje.
2. Cada valor multiplicado por 4.
3. Interpretar la tabla de dependencia como **escalon con techo**, con desempate a la
   izquierda, y plana por encima del tope.
4. Verificar `count != 0` antes de indexar con `i - 1`, aunque el host no lo haga.
5. Ordenar la tabla de dependencia si se genera en lugar de leerse.

## Clasificacion

- `SMC_VOLTAGE_WORD_LAYOUT = PROVEN`: VDDC bits 0-14, VDDCI 15-29, PHASES 30-31.
  `SMU_VoltageLevel` es un `uint32_t` en `smu74.h:342`.
- `SMC_VOLTAGE_SCALE = PROVEN`: 4, solo multiplicador en el host.
- `SMC_VOLTAGE_UNIT = PROVEN` en mV, por comparacion con `VDDC_VDDCI_DELTA` = 200.
- `SMC_VOLTAGE_LOOKUP_RULE = PROVEN`: techo, primera entrada con `clk >= pedido`,
  ultimo valor si ninguna cumple.
- `SMC_VOLTAGE_LOOKUP_ASSUMES_SORTED = PROVEN`: nada comprueba el orden.
- `SMC_FIND_VDDCI_UNDERFLOW = PROVEN`: con `count == 0`, `entries[i-1]` con
  `i == 0` sobre `uint32_t` lee fuera del array.
- `SMC_VBIOS_ZERO_ENTRIES_ACCEPTED = PROVEN`: la lectura valida el maximo y no el minimo,
  y devuelve exito con cero entradas.
- `SMC_FIND_VDDCI_PRECONDITIONS = NOT_VERIFIED`: tres condiciones a la vez, sin
  comprobar en esta placa.

## Lo que esto NO dice

No dice cual es el voltaje real de ningun nivel. Es una regla de codificacion y de
busqueda, no una medicion.

No dice que el firmware lea los tres campos, ni en que orden, ni si el `÷4` lo hace
sobre el valor entero o sobre el campo ya desempaquetado.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.
