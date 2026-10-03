# 935 · 907 queda refutada: la tabla de ventilador se entrega entera

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Estado de `907`
>
> ```
> CLAIM-907 v1   el driver copia 8 bytes de un puntero donde el firmware espera 96
>                VALIDATED
> CLAIM-907 v2   REFUTED     <- este hallazgo
> Razón:         sizeof(fan_table) es 36, no 8. Y no hay copia masiva de 96 bytes
>                en esta ruta.
>
> POSTERIOR: este hallazgo **v3**, en `937`. El punto 3 de la seccion 8 de este
> fichero era **demasiado fuerte** y queda corregido: los 96 bytes de
> `pp_advance_fan_control_parameters` no se copian en bloque, pero **dos de sus
> campos si llegan al SMC**, campo a campo y escalados. Ver `937`.
> El defecto medido no existia.
> ```
>
> **El tamanho real es 36 bytes y coincide exactamente con `SMU74_Discrete_FanTable`,
> un struct declarado en el BTF del `amdgpu.ko` cargado.** La copia es completa.
>
> Lo que si queda es mucho mas util: **la tabla de ventilador de mi VBIOS, leida
> entera, y todas las guardas de la ruta, comprobadas una a una contra mi placa.**

## 1. De donde salio el 8

`polaris10_smumgr.c:2170` declara la variable:

```c
SMU74_Discrete_FanTable fan_table = { FDO_MODE_HARDWARE };
```

**Es un struct en la pila, no un puntero.** Y el BTF del modulo cargado da su
tamano:

```
SMU74_Discrete_FanTable   size_declarado=36   18 miembros   FdoMode .. Padding
```

18 campos, del `FdoMode` en el byte 0 al `Padding` en el 34, 36 bytes. Los que
escribe `:2240-2252` —`TempRespLim`, `RefreshPeriod`, `FdoMax`, `TempSrc`— estan
todos dentro. **Nada se sale.**

De donde salio el 8, con alta probabilidad: `hwmgr->thermal_controller.
advanceFanControlParameters` **si** es un puntero de 8 bytes, y `sizeof()` sobre
el una struct de ese nombre da exactamente 8. Un barrido que empareje `sizeof`
con el nombre de struct equivocado produce 8 con toda la apariencia de una
medida. **Un numero plausible no es un numero verificado.**

## 2. El destino, y por que los 96 no aparecen por ningun lado

```c
polaris10_smumgr.c:2254
    res = smu7_copy_bytes_to_smc(hwmgr, smu_data->smu7_data.fan_table_start,
                                 (uint8_t *)&fan_table, (uint32_t)sizeof(fan_table),
                                 SMC_RAM_END);
polaris10_smumgr.c:2530-2536
    smu7_read_smc_sram_dword(hwmgr, SMU7_FIRMWARE_HEADER_LOCATION +
                             offsetof(SMU74_Firmware_Header, FanTable), &tmp, SMC_RAM_END);
    smu_data->smu7_data.fan_table_start = tmp;
```

El destino es el campo `FanTable` de la cabecera de firmware **en RAM del SMC**,
no una zona de 96 bytes. La estructura que el firmware espera ahi se llama
`SMU74_Discrete_FanTable` y mide 36. **Los 96 bytes de
`pp_advance_fan_control_parameters` no aparecen en esta ruta en absoluto**: ese
struct vive en la cabecera PP del host y sus campos viajan **por mensajes
PPSMC individuales**, en `:2258-2272`:

```
PPSMC_MSG_SetFanMinPwm      -> advanceFanControlParameters.ucMinimumPWMLimit
PPSMC_MSG_SetFanSclkTarget  -> advanceFanControlParameters.ulMinFanSCLKAcousticLimit
```

**Hay dos rutas de ventilacion, y las dos existen.** Una copia de 36 bytes a la
tabla de microcodigo, y una serie de mensajes sueltos. El hallazgo anterior las
confundio en una sola y declaro un defecto donde habia dos caminos.

## 3. La tabla de ventilador de mi placa

`usFanTableOffset` esta en el byte 37 de `ATOM_Tonga_POWERPLAYTABLE`
(bitoff 296, BTF). Con la cadena del driver:

```
PPI + usFanTableOffset = 0x9C0A + 625 = 0x9E7B
```

Y ahi, con el layout del BTF:

```
campo          valor    lectura
ucRevId           9     > 0, y NO < 8  -> rama Polaris, no la Tonga de :960
ucTHyst           3     histeresis 3 grados
usTMin         4000     40.00 C
usTMed         6500     65.00 C
usTHigh        8500     85.00 C
usPWMMin       2000     20.00 %
usPWMMed       4000     40.00 %
usPWMHigh      6000     60.00 %
```

**40/65/85 grados con 20/40/60 por ciento de PWM, histeresis de 3 grados.** Es la
curva de ventilacion de una tarjeta de este tamaño, con los valores que
corresponden. No hay ambiguedad.

**Una trampa que dejo documentada:** hay una `PPTable_Generic_SubTable_Header` de
4 bytes antes de la tabla, y si se decodifica en `+4` salen `usPWMMed = 10900` y
`usPWMHigh = 25601`, imposibles. Pero el driver **tipa el puntero como esa
cabecera generica y lee `ucRevId` en el byte 0** (`:946-952`), asi que la lectura
correcta es sin `+4`. **El dominio y el codigo coinciden en cual es la buena**, y
la herramienta guarda el `+4` como control explicito para que si someday cambia
el layout se vea en vez de pasar desapercibido.

## 4. Todas las guardas, una a una, contra mi placa

La pregunta era si esta ruta **se ejecuta en mi ASIC**. No basta con que el codigo
exista: hay cinco guardas y las cinco son datos de mi VBIOS.

```
guarda                                              fuente          veredicto
:941  usFanTableOffset != 0                        mi VBIOS  625    PASA
:952  fan_table->ucRevId > 0                       mi VBIOS  9      PASA
:960  ucRevId < 8  ->  rama Tonga                  mi VBIOS  9      NO, va a Polaris
:935  ucType != ATOM_PP_THERMALCONTROLLER_NONE     mi VBIOS  23     PASA
:924  ucFanParameters & 0x80  ->  bNoFan           mi VBIOS  2      PASA, bNoFan = FALSE
```

La quinta necesita `ATOM_Tonga_Thermal_Controller` en `PPI + usThermalControllerOffset`,
que es el byte **39** (bitoff 312):

```
ucRevId              1
ucType              23     != 0  -> PHM_PlatformCaps_ThermalController ACTIVA
ucI2cLine            0
ucI2cAddress         0
ucFanParameters      2      & 0x80 = 0  -> bNoFan = FALSE
                              & 0x1F = 2     2 pulsos de tacometro por vuelta
ucFanMinRPM          0
ucFanMaxRPM         40      -> ulMaxRPM = 40 * 100 = 4000 RPM
ucReserved           0
ucFlags              0
```

**4000 RPM como techo, 2 pulsos por vuelta, hay ventilador, y la microcodigo tiene
el control.** Y `use_hw_fan_control` —que solo se activa si `usFanTableOffset`
fuera 0— **se queda en 0**, o sea que la ruta del microcodigo es la que manda.

**Conclusion: `PHM_PlatformCaps_MicrocodeFanControl` queda ACTIVADA en mi placa,
y por una razon que puedo enunciar.** El ventilador si esta bajo control del
driver.

## 5. Lo que queda runtime

Una sola cosa, y es de otra naturaleza:

```
fan_table_start = valor de SMU74_Firmware_Header.FanTable en RAM del SMC
                 :2530, leido con smu7_read_smc_sram_dword
                 = RUNTIME_MISSING (contenido de la RAM del SMC)
```

Y si saliera **0**, `:2184-2188` desactivaria `MicrocodeFanControl` y devolveria
0 sin escribir nada. Es la unica condicion que puede tumbar la ruta, **y es
precisamente la que solo se puede observar en ejecucion**. No es un hueco que
cerrar con mas analisis estatico: es `B_RUNTIME`.

## 6. La herramienta que hacia falta

He fallado **tres veces** la cadena ATOM en tres iteraciones: una direccion
anotada en vez de recalcular, y dos veces confundiendo *la direccion del campo que
contiene `data_table`* con *el valor de `data_table`*. La segunda vez me dio
`PPI = 0x4D4F`, que es la cadena ASCII `MO`, y todos los offsets derivados parecian
validos hasta que los mire.

Un error repetido tres veces no es un descuido: es una operacion que necesita
herramienta. **`tools/atom_chain.py` v1.1.0**, `VALIDATED`:

```
BUILD              py_compile OK
BASIC TEST         informe exit=0, stderr 0 bytes, 14 lineas
KNOWN INPUT        12 vectores de direccion, todos verificados por dominio
EXPECTED OUTPUT    PPI=0x9C0A, usStructureSize=778, fan=0x9E7B, thermal=0x9E72,
                   sclk=0x9D15, powertune=0x9EAB, pcie=0x9EFA
EDGE CASE          truncado a 100 B -> AtomError
                   58880 B de ceros -> AtomError (firma ATOM ausente)
                   directorio como argumento -> AtomError
                   fichero inexistente -> AtomError
FAILURE CHECK      paso 16 rechazado con el motivo, no en silencio
                   campo desconocido -> AtomError
                   lectura en el borde final -> AtomError
OUTPUT VALIDATION  dos ejecuciones byte a byte IDENTICAS
SELF_TEST          38 casos, 0 fallos, exit=0   (minimo declarado 20)
```

**El caso que mas importa es este:**

```
ok  confundir direccion con valor -> detectable   u16 leeria 0x4D4F
```

**La herramienta reproduce mi error exacto y lo reporta.** Eso la convierte en un
test de regresion de verdad, no en una convenience que reimplementa lo que ya
hacia yo. Sin ese vector, el mismo error volveria a pasar sin que nada lo notara.

Ademas guarda el paso de 15 bytes de la tabla SCLK como **exigido por el
dominio, no asumido**: `dec_sclk_dependency(..., stride=16)` lanza error con el
motivo, porque con 16 no sale ni un valor plausible y con 15 si.

## 7. Errores de esta iteracion

**1. **`907` estaba mal y lo daba por bueno.** Reverti un hallazgo marcado
`VALIDATED`. El mecanismo del error fue emparejar un `sizeof` con la struct
equivocada: `sizeof` de un puntero da 8 con toda la apariencia de una medida, y
8 contra 96 es exactamente el tipo de contraste que hace que un defecto parezca
encontrado. **Un contraste valioso solo lo es si las dos cifras estan medidas.**

**2.** Volvi a fallar la cadena ATOM por segunda vez, y la herramienta que
existia para evitarlo no existia porque no la habia construido tras el primer
fallo. **Un solo fallo no justifica una herramienta; tres si.** Conte los fallos
y ahi construi.

**3.** Casi dejo pasar el `+4` de la cabecera generica. Lo que me detuvo fue que
los valores salian absurdos: 25601 por ciento de PWM. **El test de dominio es lo
que separa el layout bueno del malo**, y ya me habia salvado en `929`.

## 8. Frontier siguiente

**La linea del ventilador queda cerrada en su parte estatica, y con una
correccion substantial respecto a lo que creia saber:**

```
1.  sizeof(SMU74_Discrete_FanTable) == 36, copia COMPLETA        PROVEN
2.  destino = SMU74_Firmware_Header.FanTable en RAM del SMC     PROVEN
3.  no hay COPIA MASIVA de 96 bytes en esta ruta            PROVEN_ABSENT
    >> CORREGIDO en 937: no se copia en bloque, pero usFanGainEdge y
       usFanGainHotspot SI llegan al SMC por :453-456 y :2118.
4.  curva de mi VBIOS: 40/65/85 C -> 20/40/60 %, hyst 3, 4000 RPM PROVEN
5.  ucRevId 9 -> rama Polaris, no Tonga                          PROVEN
6.  las 5 guardas de la ruta pasan con datos de mi VBIOS         PROVEN
7.  MicrocodeFanControl queda ACTIVADA; use_hw_fan_control = 0    PROVEN
8.  fan_table_start != 0                                          RUNTIME_MISSING
```

**Lo que cambia para el objetivo del driver propio:** la idea de que el
ventilador «no lo gobierna el driver» era **falsa**, y con ella se cae la
conexion que `931` construyo con la linea de tension. El ventilador **si** lo
gobierna el driver, con una curva de tres puntos que esta en el VBIOS, y el
`fan_table_start` es la unica condicion que puede desactivarlo.

**Eso devuelve el peso al frente que si queda abierto:** el rendimiento sostenido
de mi placa depende de si el fan table llega al SMC, y eso es `B_RUNTIME`.

Y hay una consecuencia practica inmediata: **la curva 40/65/85 con 20/40/60 % es
el punto de partida documentado para cualquier politica de ventilacion propia.**
Con 4000 RPM de techo y 3 grados de histeresis, los margenes termicos de mi placa
estan fijados por esa tabla, y son conocidos.

## 9. Correccion registrada

`907` queda **REFUTADA** y su texto **se conserva integro** en su fichero, sin
reescribir. La version v2 vive aqui y cita la v1. **Un hallazgo corregido no se
borra: se conserva el recorrido, porque el mecanismo del error es evidencia.**
