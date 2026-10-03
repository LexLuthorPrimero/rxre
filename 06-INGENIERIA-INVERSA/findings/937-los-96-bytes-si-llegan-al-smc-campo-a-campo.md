# 937 · Los 96 bytes sí llegan al SMC, campo a campo, y valen 4096

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Estado de `935`
>
> ```
> CLAIM-935 v1  punto 3: "no hay ningun campo de 96 bytes en esta ruta"
>               PROVEN_ABSENT
> CLAIM-935 v2  REFUTED por este hallazgo
> Razón:        no se copia en bloque, pero usFanGainEdge y usFanGainHotspot
>               SI llegan al SMC, escalados por 4096/100. La cadena entera
>               esta medida y no tiene ninguna puerta de runtime.
> ```

**La cadena del struct de 96 bytes, de punta a punta:**

```
VBIOS 0x9E7B   usFanGainEdge = 100   usFanGainHotspot = 100
   -> process_pptables_v1_0.c:1045   rama ucRevId >= 9  ->  ATOM_Polaris_Fan_Table
   -> :1069-1074   advanceFanControlParameters.usFanGainEdge = 100
   -> polaris10_smumgr.c:453-456
        scale_fan_gain_settings(100) = 100 * 4096 / 100 = 4096
        table->FanGainEdge    = PP_HOST_TO_SMC_US(4096)
        table->FanGainHotspot = PP_HOST_TO_SMC_US(4096)
   -> polaris10_smumgr.c:2118-2123
        bloque de 1776 bytes desde SystemFlags (byte 108), o sea 108..1884
        FanGainEdge    esta en 1688   -> DENTRO
        FanGainHotspot esta en 1690   -> DENTRO
   -> SMC
```

**PROVEN, estatico, de extremo a extremo.** Y el valor es **4096 = la unidad**.

## 1. Lo que `935` afirmo de mas

`935` concluyo `PROVEN_ABSENT`: que el struct de 96 bytes no aparecia en la ruta.
**Es demasiado fuerte, y lo era por una confusion mia entre dos preguntas
distintas:**

```
PREGUNTA 1  ¿se copia el struct de 96 bytes en bloque al SMC?     NO.  bien.
PREGUNTA 2  ¿alguno de sus campos llega al SMC?                    SI.  mal.
```

Son preguntas distintas y las dos importan. `907` se equivocó en la 1; yo me
equivocé en la 2 al llevar la respuesta de la 1 a la 2. **Un `PROVEN_ABSENT`
debe decirlo para el objeto exacto que se pregunta, nunca para el tipo entero del
que se deriva.**

## 2. Donde se leen los dos campos

`polaris10_smumgr.c:436-437` —la declaración que confundí— es un **alias de solo
lectura**, y su unico uso es escalar dos campos:

```c
:420-425  static uint16_t scale_fan_gain_settings(uint16_t raw_setting)
              { tmp = raw_setting * 4096 / 100; return (uint16_t)tmp; }

:453-456  table->FanGainEdge    = PP_HOST_TO_SMC_US(
               scale_fan_gain_settings(fan_table->usFanGainEdge));
          table->FanGainHotspot = PP_HOST_TO_SMC_US(
               scale_fan_gain_settings(fan_table->usFanGainHotspot));
```

Y `table` es `&(smu_data->smc_state_table)` (`:432`). **No se copia el struct: se
escalan dos campos y se depositan en la tabla DPM.** Por eso ninguna lectura de
`sizeof` da 96, y por eso `907` se topó en 8.

`scale_fan_gain_settings` es **porcentaje a fraccion de 12 bits**: 100 → 4096,
50 → 2048, 0 → 0. Los tres verificados como vectores en el self-test.

## 3. Por qué el destino es Polaris, y no Tonga

`init_thermal_controller` tiene **tres** ramos y mi revisión **no es la primera**:

```c
:960   if (fan_table->ucRevId < 8)          -> ATOM_Tonga_Fan_Table
:995   else if (fan_table->ucRevId == 8)    -> ATOM_Fiji_Fan_Table
:1045  else if (fan_table->ucRevId >= 9)    -> ATOM_Polaris_Fan_Table
```

Mi tabla tiene `ucRevId = 9` → **el tercer ramo, el Polaris**. Y el layout del
BTF lo confirma como propio:

```
ATOM_Tonga_Fan_Table      size_declarado=31   8 campos visibles
ATOM_Polaris_Fan_Table    size_declarado=48   27 campos
```

**Los ocho primeros campos tienen los mismos offsets en ambas** —`ucRevId@0`,
`ucTHyst@1`, `usTMin@2`, `usTMed@4`, `usTHigh@6`, `usPWMMin@8`, `usPWMMed@10`,
`usPWMHigh@12`—, asi que las lecturas de `935` §3 **se sostienen** y no hubo que
corregirlas. Lo verifique antes de darlo por bueno: un cambio de layout habria
podido invalidarlas.

## 4. La politica de ventilacion completa de mi placa

Con el layout Polaris correcto, la tabla entera de `0x9E7B`:

```
@0  ucRevId                       9      -> rama Polaris
@1  ucTHyst                       3      histeresis de curva
@2  usTMin                    4000      40.00 C
@4  usTMed                    6500      65.00 C
@6  usTHigh                   8500      85.00 C
@8  usPWMMin                 2000      20.00 %
@10 usPWMMed                 4000      40.00 %
@12 usPWMHigh                6000      60.00 %
@14 usTMax                  10900      109.0 C   techo
@16 ucFanControlMode             1
@17 usFanPWMMax                 100      100 %
@19 usFanOutputSensitivity    4836
@21 usFanRPMMax                4000      4000 RPM
@23 ulMinFanSCLKAcousticLimit 85000      /100 = 850, SCLK del limite acustico
@27 ucTargetTemperature          70      70 C objetivo
@28 ucMinimumPWMLimit            30      30 % minimo
@29 usFanGainEdge              100      -> 4096
@31 usFanGainHotspot           100      -> 4096
@33 usFanGainLiquid            100      -> 4096
@35 usFanGainVrVddc            100      -> 4096
@37 usFanGainVrMvdd            100      -> 4096
@39 usFanGainPlx               100      -> 4096
@41 usFanGainHbm               100      -> 4096
@43 ucEnableZeroRPM               0      RPM cero NO habilitado
@44 ucFanStopTemperature         50      50 C, para
@45 ucFanStartTemperature        60      60 C, arranca
@46 usReserved                   0
```

**Coherente de punta a punta:** curva monotona en temperatura y en PWM, siete
ganancias en rango 0-100, techo de 4000 RPM, banda de arranque/parada de 10
grados, objetivo a 70 C con tope de 109 C.

**Lo relevante para el rendimiento sostenido:** `usFanGainEdge` y
`usFanGainHotspot` estan **los dos en 100**, luego el valor escalado es
**exactamente 4096**, la unidad. **El VBIOS de esta placa no potencia el
ventilador ni por temperatura de borde ni por hotspot.** Los dos factores que en
una tarjeta de consumo se suben para gobernar el ventilador bajo carga termica
estan aqui en su valor neutro.

Es un dato de diseño, no un defecto: una RX 550 de bajo consumo con ventilador de
40 mm no lo necesita a 75 W. Pero **es el valor de partida documentado** para
cualquier politica propia, y es uno de los dos campos que el driver escribe en la
tabla DPM que el firmware lee.

## 5. El bloque que se sube, y por que los offsets cierran

```c
polaris10_smumgr.c:2118-2123
    smu7_copy_bytes_to_smc(hwmgr,
        dpm_table_start + offsetof(SMU74_Discrete_DpmTable, SystemFlags),
        &(table->SystemFlags),
        sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
        SMC_RAM_END);
```

Los tres numeros del BTF:

```
sizeof(SMU74_Discrete_DpmTable) = 1884     sizeof(SMU74_PIDController) = 36
SystemFlags @ bitoff 864  -> byte 108     longitud = 1884 - 3*36 = 1776
```

**El bloque va de 108 a 1884**, o sea el struct entero a partir de `SystemFlags`
—los 108 primeros bytes no se suben. Y los dos campos de ventilador estan en
1688 y 1690: **`1688 - 108 = 1580 < 1776`**, dentro por 196 bytes de margen.

Ese 1776 coincide con la cifra que venia arrastrando desde `920`, y **ahora
sabe de donde sale**, que es lo que faltaba antes: no era un numero de la
nada, era `1884 - 3*36`.

## 6. La herramienta, ampliada

`tools/atom_chain.py` **v1.2.0**, `VALIDATED`, ahora con:

```
dec_polaris_fan_table()   los 27 campos del layout Polaris, con los 8 primeros
                           verificados contra la lectura compartida con Tonga
escala_fan_gain()          x * 4096 / 100, con vectores 0, 50 y 100
dpm_copy_range()           (108, 1776) derivado de los dos sizeof del BTF
dpm_llega_al_smc(byte,w)   decide si un campo cae dentro del bloque subido
```

```
BUILD              py_compile OK
KNOWN INPUT        27 vectores de la tabla Polaris, todos por dominio
FAILURE CHECK      la comprobacion de rango tiene NEGATIVOS:
                     offset fuera del bloque detectado        True
                     offset en el borde final detectado       True
                   sin ellos, un positivo no significaria nada
SELF_TEST          62 casos, 0 fallos, exit=0    (minimo declarado 40)
```

Subi el suelo de `CASOS_SELFTEST_MINIMO` de 20 a 40, porque con 62 casos reales
un minimo de 20 era un suelo que no protegia nada.

## 7. Errores de esta iteracion

**1. Escribi un `PROVEN_ABSENT` que no se sostenia.** Lo escribi la iteracion
anterior, creyendo que responder la pregunta 1 con «no» respondia la pregunta 2.
**Un `PROVEN_ABSENT` es la afirmacion mas fuerte que se puede hacer sobre un
codigo, y la unica que no se puede deshacer con mas busqueda: hay que
justificar el scope exacto.** Escribi el marcador sin el scope.

Corregido en sitio, en `935`, sin borrar el texto: el punto 3 sigue visible con la
correccion debajo. **Un estado corregido se conserva, no se sustituye.**

**2.** Casi me fio del layout Tonga para el resto de la tabla. Los 8 primeros
campos coinciden, lo cual hace el error invisible: **la parte que leeria bien
es justamente la que ya habia publicado.** Verificar si lo que ya tengo cambia es
parte de la lectura, no un extra.

**3.** Un `subprocess` mio para pedir `sizeof(SMU74_PIDController)` fallo por
directorio y devolvio `None`. **Si no cierro la aritmetica, no la presento como
cerrada**: el script salio con `SystemExit` en vez de imprimir un resultado
parcial. Volví a pedirlo con la herramienta directa.

## 8. Frontier siguiente

**Con esto, la ventilacion de mi placa queda cerrada en su parte estatica, y
completa:**

```
1.  sizeof(SMU74_Discrete_FanTable) == 36, copia completa          PROVEN
2.  curva 40/65/85 C -> 20/40/60 %, histeresis 3, techo 4000 RPM    PROVEN
3.  objetivo 70 C, tope 109 C, banda de parada/arranque 50/60 C     PROVEN
4.  limite acustico a SCLK 850                                      PROVEN
5.  RPM cero NO habilitado                                          PROVEN
6.  las 7 ganancias de ventilador = 100, sin historial              PROVEN
7.  usFanGainEdge/Hotspot escalan a 4096, la unidad                  PROVEN
8.  esos 2 campos SI llegan al SMC por :453-456 y :2118             PROVEN
9.  el bloque DPM son 1776 B = 1884 - 3*36, cubre 108..1884        PROVEN
10. fan_table_start != 0, unica puerta runtime, sigue RUNTIME_MISSING
```

**Lo que queda abierto y es de otra naturaleza:** el punto 10. Todo lo demas es
estatico y esta cerrado; ese no lo es por diseno, es contenido de la RAM del SMC
y solo se ve en ejecucion (`B_RUNTIME`).

Y el frente nuevo que abre esto es concreto: **los seis gains que el driver lee
del VBIOS y NO escribe en la DPM** —`usFanGainLiquid`, `usFanGainVrVddc`,
`usFanGainVrMvdd`, `usFanGainPlx`, `usFanGainHbm`, y `ucFanControlMode`— estan
en 100 en mi VBIOS, pero **el kernel no los sube a ningun sitio que yo haya
encontrado**. Eso es un `NOT_FOUND` que vale la pena cerrar: si el firmware los
espera y el kernel no los manda, es el mismo tipo de desconexion que `907`
buscaba y en la direccion contraria.

**Cerrado en `939`:** los cinco no tienen consumidor en esta generacion de ASIC, y
la causa no es un descuido del driver sino que **la struct de destino del SMC no
tiene esos campos**: `SMU74_Discrete_FanTable` tiene 0 gains y la tabla DPM tiene
exactamente 2. Alli mismo se abre `ucFanControlMode`, que **si** esta vivo y
gobierna una rama de `smu7_hwmgr.c` que si se ejecuta.

## 9. Correcciones registradas

- `935` v2 → v3: el punto 3 era demasiado fuerte. Marcado **en el propio
  fichero**, con la razon en dos lineas.
- `935` §3 **se sostiene**: verificado que el layout Polaris comparte los
  offsets de los 8 primeros campos con el Tonga, con lo que las lecturas
  publicadas no cambian.
- `907` v2 **se sostiene**: su conclusion de que el ventilador no llega al SMC
  era falsa, y ahora hay una correccion mas fuerte que la que lui mismo di.
