# 941 · usTjMax = 93: la rama de límites de ventilador sí corre en mi placa

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Estado de `939`
>
> ```
> CLAIM-939 v1  punto 8: usDefaultTargetOperatingTemp != 0 -> NOT_DETERMINED
> CLAIM-939 v2  PROVEN. Valor medido: 93. La condicion se cumple.
> ```
>
> **Las dos condiciones de `smu7_hwmgr.c:2572-2573` se cumplen en mi placa, y la
> rama que fija los límites de ventilador se ejecuta.** Con eso queda medido, no
> supuesto, qué límites aplica el driver a mi tarjeta.

## 1. El error eran cinco guiones bajos

`939` dejo `usTjMax` como `NOT_DETERMINED` con el motivo «no aparece en el BTF».
**El motivo era incorrecto: sí aparece.** El tipo se lee de la declaración local,
no se adivina:

```
process_pptables_v1_0.c:587   dentro de get_cac_tdp_table (cuerpo 564..709)
    const ATOM_Tonga_PowerTune_Table *tonga_table = ...
```

**`ATOM_Tonga_PowerTune_Table`, con guion bajo delante de `Table`.** Los cinco
nombres que probé en `939` eran sin guion, y por eso los cinco dieron cero:

```
ATOM_PowerTuneTable          sin guion   0 coincidencias
ATOM_Tonga_PowerTuneTable    sin guion   0
ATOM_Polaris_PowerTuneTable  sin guion   0
ATOM_Fiji_PowerTuneTable     sin guion   0
ATOM_Common_PowerTuneTable   sin guion   0
ATOM_Tonga_PowerTune_Table   CON GUION   15 miembros
```

**Y el fallo adyacente:** el `grep` de `tonga_table` me habia devuelto el de
`get_sclk_voltage_dependency_table`, **otra variable con el mismo nombre en otra
funcion**. Por eso lo lei dentro del cuerpo de `get_cac_tdp_table`, línea a
línea, en vez de buscarla por nombre.

Un `0` de `grep` es la ausencia de **mi patron**, y cinco ceros consecutivos con
el mismo guion de diferencia son una pista, no cinco evidencias independientes.

## 2. El layout, y un control que lo confirma solo

```
ATOM_Tonga_PowerTune_Table   31 B   15 miembros, empaquetado
    usTjMax                bitoff 136 -> byte 17
    usSoftwareShutdownTemp bitoff 184 -> byte 23
    usClockStretchAmount   bitoff 200 -> byte 25
```

**`usClockStretchAmount` cae en el byte 25, que es exactamente donde `502` lo midio
por otra via.** Un layout correcto se autocomprueba contra un dato medido antes
por otro camino. Si hubiera salido en 24 o en 26, el layout estaba mal y yo no
me habría enterado por el valor, sino por el fallo de `502`.

## 3. La tabla PowerTune entera, medida

```
@0  ucRevId                          4
@1  usTDP                           35
@3  usConfigurableTDP                0
@5  usTDC                           36
@7  usBatteryPowerLimit             35
@9  usSmallPowerLimit               35
@11 usLowCACLeakage                  0
@13 usHighCACLeakage                 0
@15 usMaximumPowerDeliveryLimit     35
@17 usTjMax                         93     <-- el discriminante
@19 usPowerTuneDataSetID             0
@21 usEDCLimit                       0
@23 usSoftwareShutdownTemp           97
@25 usClockStretchAmount             2     <-- control cruzado, COINCIDE
```

**Coherencia de dominio que pasa:** `usSoftwareShutdownTemp = 97 > usTjMax = 93`.
El apagado por software esta por encima del limite de junction, que es lo
esperable. Y `usTDP`, `usBatteryPowerLimit`, `usSmallPowerLimit` y
`usMaximumPowerDeliveryLimit` comparten el valor 35, lo que es propio de un
limite de potencia unico replicado en cuatro campos.

**La unidad de `usTDP` queda `SEMANTIC_MISSING` y no la estimo.** El driver lo
multiplica por 128 al escribirlo (`:442`, `table->DefaultTdp = usTDP * 128`), o
sea 4480 en la unidad de la struct DPM, y no sé qué unidad es esa. Afirmarla
sería inventar el cierre.

## 4. Las dos condiciones, una a una

```
:603-604   tdp_table->usDefaultTargetOperatingTemp = le16_to_cpu(tonga_table->usTjMax)
:827       get_cac_tdp_table(&pp_table_information->cac_dtp_table, pPowerTuneTable)
           -> la CAC/DTP vive DENTRO de la tabla PowerTune, no en subtabla propia

:2572      if (table_info->cac_dtp_table->usDefaultTargetOperatingTemp != 0 &&
:2573          advanceFanControlParameters.ucFanControlMode) {
```

```
condicion 1   usDefaultTargetOperatingTemp = usTjMax = 93  ->  93 != 0   CUMPLE
condicion 2   ucFanControlMode             = 1  (939)                  CUMPLE
```

**La rama se ejecuta.** Con los valores que produce, todos medidos:

```
@2574  usFanPWMMinLimit   = ucMinimumPWMLimit    = 30      (@28 del VBIOS)
@2577  usFanPWMMaxLimit   = usDefaultMaxFanPWM   = 100     (@17)
@2580  usFanPWMStep       = 1
@2582  usFanRPMMaxLimit   = 100
@2584  usFanRPMMinLimit   = ucMinimumPWMLimit    = 30
@2587  usFanRPMStep       = 1
@2596  usMaxFanPWM        = usDefaultMaxFanPWM   = 100
@2599  usMaxFanRPM        = usDefaultMaxFanRPM   = 4000
@2589  usDefaultTargetOperatingTemp = (93 >= 50) ? (93 - 50) : 0  ->  43
@2592  usOperatingTempMaxLimit = 43
@2593  usOperatingTempStep      = 1
@2594  usOperatingTempHyst      = 1
```

Y `usMaxFanPWM` y `usMaxFanRPM` **los lee la ruta termica de mi ASIC**:

```
smu7_thermal.c:161   advanceFanControlParameters.usMaxFanPWM    -> 100
smu7_thermal.c:157   advanceFanControlParameters.usMaxFanRPM    -> 4000
```

**PROVEN de punta a punta.**

## 5. El `-50`: una tercera convencion de temperatura, y distinta de las otras dos

La placa tiene **tres** codificaciones de temperatura coexistiendo, y conviene no
confundirlas:

```
tabla de ventilador      usTMin=4000  usTMax=10900      centesimas   (935)
                         40.00 C      109.00 C
PowerTune                usTjMax=93                          grados enteros
                         93 C
tras la resta           usOperatingTempMaxLimit=43           grados enteros
                         43 C
```

Las del ventilador están en centésimas; las de la PowerTune **en grados
enteros**, y eso lo fija el dominio: `93` en centésimas serían 0.93 °C, absurdo
para un límite de junction. **El `-50` es una conversión de unidades, no un
margen térmico.** Es lo unico que hace la resta.

Y la magnitud que queda, **43**, no la interpreto: qué significa un limite de
temperatura de operación 43 junto a un `ucTargetTemperature` de 70 y un
`usTMax` de 109 **depende de lo que el firmware del SMC haga con ella**, y eso no
está en el corpus. `SEMANTIC_MISSING`, no `NOT_DETERMINED`: está Located pero sin
semántica, que es un estado distinto.

## 6. La herramienta, y un fallo de test que valió la pena

`tools/atom_chain.py` **v1.3.0**:

```
dec_powertune_table()   los 14 campos de la tabla PowerTune
resta_50(x)             el ternario de :2589-2590, extraido a funcion
SELF_TEST               79 casos, 0 fallos, exit=0   (minimo subido a 70)
```

**El self-test fallo una vez, y el fallo era mio, no del codigo.** Escribi la
aserción del `-50` reescribiendo el ternario de C en Python, y lo escribi al reves:

```python
(0 if 49 >= 50 else 49 - 50) == 0      # mi test:    condition false -> 49-50 = -1
(x - 50) if x >= 50 else 0             # el codigo:  condition false -> 0
```

Un `ok` que reimprime la regla **puede estar mal y pasar igual**, porque prueba
mi copia y no la función. Lo arreglo extrayendo `resta_50()` y haciendo que los
tests la **llamen**, con vectores en los bordes: `0, 49, 50, 51, 93`, mas una
comprobacion de monotonia.

Es el mismo modo de fallo que `907`: **emparejar un nombre con un objeto sin
comprobar que es el mismo objeto.** Solo que aqui la copia la puse yo.

## 7. Errores de esta iteracion

**1.** `939` declaro `NOT_DETERMINED` con el motivo «no aparece en el BTF», y el
motivo era **falso**. Un `NOT_DETERMINED` cuyo motivo no he verificado es peor que
un `UNKNOWN`: parece una investigacion cerrada cuando no lo estaba. **El motivo de
un `NOT_DETERMINED` tiene la misma obligacion de prueba que la afirmacion que
sustituye**, porque es lo que impide que otro repita el intento cinco veces.

**2.** Cinco nombres de struct sin guion bajo. **Cinco ceros no son cinco
evidencias: son una.** Cuando N intentos seguidos fallan con el mismo error,
la pista esta en lo que tienen en comun los N, no en el numero de intentos.

**3.** `usTDP = 35` me quedaba sin unidad y casi escribo «35 W» por
aproximación al nombre del campo. **El nombre de un campo no es su unidad**, y lo
deje `SEMANTIC_MISSING` en vez de estimarlo.

## 8. Frontier siguiente

```
1.  usTjMax = 93 en el byte 17, layout del BTF                PROVEN
2.  usClockStretchAmount = 2 en el byte 25, control cruzado   CORROBORADO
3.  shutdown 97 > TjMax 93, coherencia de dominio             CORROBORATED
4.  las 2 condiciones de :2572-2573 se cumplen                 PROVEN
5.  la rama se ejecuta y fija PWM 30..100, RPM 30..4000        PROVEN
6.  usMaxFanPWM 100 y usMaxFanRPM 4000 los lee smu7_thermal    PROVEN
7.  93 >= 50 -> usOperatingTempMaxLimit = 43                   PROVEN
8.  la magnitud 43 no tiene semantica en el corpus             SEMANTIC_MISSING
9.  la unidad de usTDP = 35 no esta                            SEMANTIC_MISSING
10. fan_table_start != 0                                       RUNTIME_MISSING
```

**Lo que queda abierto es de dos indoles distintos y ambos son honestos:**

- **Punto 10, `RUNTIME_MISSING`.** Contenido de la RAM del SMC. Irrecuperable
  estaticamente por diseno, y `B_RUNTIME` sigue sin autorizacion.
- **Puntos 8 y 9, `SEMANTIC_MISSING`.** No faltan datos: **falta el significado**,
  y vive en el firmware del SMC, fuera del corpus. No se cierra con mas busqueda.

**Ningun otro punto abierto en la linea de ventilacion, clocks y tension de mi
placa.** Eso no es una linea terminada: es una linea **cerrada en todo lo
staticamente medible**, con dos limites con nombre, con su causa, y sin accion
estatica que las cierre.

El frente util que queda abierto, y que no es de esta linea, es el
contrapunto: **todo esto dice como el driver limita el ventilador, y nada dice
cual es el techo real de rendimiento de mi placa.** El techo lo fijan la
temperatura sostenida y el consumo, y para eso haria falta medir, que es `B_RUNTIME`.

## 9. Correccion registrada

`939` punto 8 pasa de `NOT_DETERMINED` a `PROVEN`, **con su texto original
conservado** y la correccion visible desde el propio `939`. El motivo que yo
di -«no aparece en el BTF»- era incorrecto y queda anotado como tal: un motivo
falso en un `NOT_DETERMINED` es la clase de error que hace que el proximo agente
nono se lo intente.
