# 922 · AVFS: lo que de verdad se sube al SMC, y que no es lo que yo suponía

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## CORREGIDO POR `926` — una de mis conclusiones era falsa
>
> `922`CONCLUSION FALSA, lo digo claro porque es una conclusion mia y no
> una limitacion de la medicion.
>
> | afirmacion de `922` | estado real |
> |---|---|
> | «mi placa no aplica AVFS con clock stretching off» | **`REFUTED`**: `polaris10_smumgr.c:1803` **fuerza** `ucEnableApplyAVFS_CKS_OFF_Voltage = 1` sin consultar el VBIOS |
> | `a0..a2` son coeficientes o offsets, sin decidir | **`RESOLVED`** en `926`: son parametros opacos, y el driver los sobrescribe con los mismos valores que ya trae mi VBIOS |
> | `Platform_sigma = 0`, `Platform_mean = 500 mV` | **`PROVEN`**, el driver no los toca |
>
> El error fue leer el valor del VBIOS como si fuera el valor que llega al SMC. En
> esa rama el driver lo sobreescribe, y para mi ASIC lo sobreescribe **con lo
> mismo**.


> ## Resultado
>
> Los **parámetros de AVFS de mi placa son medibles enteros, estáticamente**, y
> el resultado **no es la curva media/sigma que yo iba buscando**.
>
> El VBIOS deja `Platform_sigma = 0` y desactiva la aplicación de AVFS con
> clock-stretching. **Mi tarjeta no usa media/sigma: usa las tablas cuadráticas
> VDROOP con clock stretching activo**, con `usClockStretchAmount = 2`.

## 1. Por qué reenfocué la pregunta

`920` proponía leer `AvfsMeanNSigma` y `AvfsSclkOffsetTable` en el ROM. Al
mirarlo, esas son **direcciones de RAM del SMC**, no del ROM:

```
smu7_hwmgr / smu7.h / smu74.h / smu75.h
   #define SMU7_FIRMWARE_HEADER_LOCATION 0x20000
```

Y el struct no está en el BTF, porque el compilador lo poda si solo se usa con
`offsetof`. **La dirección no es legible, y no es lo que importa.**

Lo que **sí** importa es el contenido, y es íntegramente estático: el driver
construye `AVFS_meanNsigma` (28 B) y `AVFS_Sclk_Offset` (16 B) campo a campo, y
los valores vienen del **VBIOS**. Los bytes que se suben se pueden calcular sin
saber a dónde se suben.

## 2. La cadena, entera y medida

```
mdt[31]                                  ASIC_ProfilingInfo, indice 31 de 35
   @ROM + data_table + 4 + 31*2 = 0x9834 -> 0xA6E4
atomctrl_get_avfs_information()           ppatomctrl.c:1042
   lee (ATOM_ASIC_PROFILING_INFO_V3_6 *) del dato anterior
polaris10_init_smc_table()                polaris10_smumgr.c:1855-1865
   AVFS_meanNsigma.Aconstant[i] = PP_HOST_TO_SMC_UL(avfs_params.ulAVFS_meanNsigma_Acontant[i])
   ... y los cinco campos mas
smu7_copy_bytes_to_smc()                  :1872   28 bytes a la direccion que dio el firmware
```

## 3. La base, confirmada por dos vías independientes

```
@0xA6E4:  usStructureSize           = 268
           ucTableFormatRevision     = 3
           ucTableContentRevision    = 6
```

**268 es exactamente el tamaño que da el BTF** para el struct compilado, y
**3.6 es literalmente el nombre del struct**, `_ATOM_ASIC_PROFILING_INFO_V3_6`.

Lo segundo importa porque **no es único**: hay otras tres posiciones en
`0x9800..0xA800` cuyo `usStructureSize` vale 268. Lo único que separa `0xA6E4` es
que su revisión es 3.6. Si me hubiera quedado con el tamaño, habría tenido cuatro
candidatas y habría elegido por coherencia de valores, que es el criterio blando.

## 4. Los valores

```
campo del driver                  valor    en unidades de 0.25 mV o 1/100
------------------------------------------------------------------------------
Aconstant[0]                          279
Aconstant[1]                         1186
Aconstant[2]                          446
DC_tol_sigma                           27
Platform_mean                        2000    -> 500 mV
Platform_sigma                          0
usMaxVoltage_0_25mv                  4300    -> 1075 mV
```

**`Platform_mean = 2000` en unidades de 0.25 mV son 500 mV**, que es la tensión
de operación de una RX 550, y **`usMaxVoltage = 4300` son 1075 mV**, coherente con
el límite de un Polaris. Cinco de seis en dominio a la primera: la base es la
buena.

## 5. Y lo que cambia la lectura: no hay curva media/sigma

```
Platform_sigma                     @212 bytes=00 00   -> 0
ucEnableApplyAVFS_CKS_OFF_Voltage  @266         = 0
ucEnableGB_VDROOP_TABLE_CKSOFF     @260         = 0
ucEnableGB_VDROOP_TABLE_CKSON      @261         = 1
```

El cero de `Platform_sigma` **es real y no relleno**: los bytes contiguos son
`D0 07` (que es `Platform_mean`) y `DD 24`. Una sigma de plataforma nula deja la
media/sigma degenerada.

Y los `enable` son tajantes: **la tabla VDROOP con clock stretching está
activada; la de clock stretching OFF, no.**

**Consecuencia para el objetivo del proyecto:** la regulación de tensión de esta
plata no la gobierna una curva media/sigma, sino **las tablas cuadráticas VDROOP
con CKS activo**, con `usClockStretchAmount = 2` — el mismo parámetro que `903`
midió en el PowerTune. **Clock stretching es la vía real**, no un caso particular
del driver.

Y el driver lo confirma por su cuenta: `polaris10_smumgr.c:1806-1808` busca una
firma mágica (`0xEA522DD3`, `0x5645A`, `0x33F9E`) que **mi VBIOS no tiene**, así
que ese camino especial no se activa.

## 6. Lo que queda abierto, y por qué no lo fuerzo

**Los valores de `ulGB_VDROOP_TABLE_CKSOFF_a0..a2` no los doy por buenos:**

```
a0 = 0xF6B024DD     a1 = 196702 (0x3005E)     a2 = 100959 (0x18A5F)
```

`a1` y `a2` son valores de un orden de magnitud razonable como coeficientes, pero
también **encajan como offsets dentro del ROM**, y ambos caben en 58880 bytes.
`a0` es demasiado grande para un coeficiente.

Con tres números y una hipótesis de unidad no se puede decidir, y la regla del
proyecto es explícita: **un número plausible no es un número verificado.** Quedan
como `NOT_DETERMINED`, y el discriminante está nombrado: probar las dos lecturas
contra el dominio de una curva de dropout, donde `a0 + a1*x + a2*x*x` tiene que
dar milivoltios para `x` en el rango de sigma.

`usPSM_Age_ComFactor` queda directamente `NOT_DETERMINED`: no localicé su offset
en el BTF y **no lo estimé**, aunque se usa en `:1860` y va al mismo struct.

## 7. Errores de esta iteración

Ninguno de medición. Los dos son de alcance:

**1.** Propuse una acción («leer las direcciones en el ROM») que **no se podía
hacer**, por la razón que saya mismo había medido antes: ese espacio es RAM del
SMC, no ROM. La rehice porque el objetivo —el objetivo de la acción, «leer en el
VBIOS»— parecía cumplible de otra forma, pero no comprobé si la acción literal lo
era.

**2.** Busqué `SMU74_Firmware_Header` en el BTF y no salió, y estuve a punto de
concluir `PROVEN_ABSENT`. Me acordé de la lección de `907` —buscar `#define`
cuando son valores de `enum`— y paré a mirar: **solo se usa con `offsetof`, y el
compilador poda ese tipo del BTF.** Es una ausencia esperada, no un fallo del
lector.

## 8. Frontier siguiente

**Decidir `ulGB_VDROOP_TABLE_CKSOFF_a0..a2`, que es la última incógnita de AVFS y
la que gobierna el clock stretching de verdad.**

La pregunta es binaria y tiene discriminante directo: **¿son tres coeficientes de
una curva, o un puntero más dos offsets?** Si fueran coeficientes, `a0` tendría
que ser del orden de los cientos como `Aconstant[]`. Si son offsets, `a0`
debería caer **dentro del ROM**.

Esa comprobación es de un minuto y separa las dos hipótesis sin depender de la
unidad.

Criterio de cierre: el veredicto sobre la forma de `a0..a2`, y con él la
confirmación de que la regulación de tensión de mi placa es la tabla cuadrática
VDROOP con CKS y `usClockStretchAmount = 2`. Con eso la cadena AVFS queda cerrada
de punta a punta y se puede escribir qué haría un driver propio distinto del de
AMD.
