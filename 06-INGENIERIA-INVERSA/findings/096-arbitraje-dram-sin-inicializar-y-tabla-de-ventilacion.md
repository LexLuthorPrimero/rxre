# 096 · La tabla de arbitraje DRAM se copia sin inicializar, y la de ventilacion si

> El defecto **no es de Polaris10**: el barrido con `uninit_copy` lo encuentra tambien
> en `fiji_smumgr.c:1528` (SMU 7.3), con la misma forma. Nace en Fiji y se hereda.
> Ver "La clase de defecto" al final.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El hallazgo

`polaris10_smumgr.c:1490-1517`, en `polaris10_program_memory_timing_parameters`:

```c
struct SMU74_Discrete_MCArbDramTimingTable arb_regs;          /* 1494  sin inicializador */
uint32_t i, j;
int result = 0;

for (i = 0; i < hw_data->dpm_table.sclk_table.count; i++) {   /* 1498 */
        for (j = 0; j < hw_data->dpm_table.mclk_table.count; j++) {
                result = polaris10_populate_memory_timing_parameters(hwmgr,
                        hw_data->dpm_table.sclk_table.dpm_levels[i].value,
                        hw_data->dpm_table.mclk_table.dpm_levels[j].value,
                        &arb_regs.entries[i][j]);            /* 1500-1503 */
                if (result == 0 && i == 0)
                        result = atomctrl_set_ac_timing_ai(hwmgr, ..., j);
                if (result != 0)
                        return result;
        }
}

result = smu7_copy_bytes_to_smc(
                hwmgr,
                smu_data->smu7_data.arb_table_start,
                (uint8_t *)&arb_regs,
                sizeof(SMU74_Discrete_MCArbDramTimingTable),   /* 1515  SIEMPRE 384 */
                SMC_RAM_END);
```

`arb_regs` es una variable **de pila**, sin inicializador de agregado y sin `memset`
en ningun sitio. Los unicos `memset` del fichero son el de la tabla de registros MC
(`polaris10_smumgr.c:2574`) y el `kzalloc_obj` del backend (`:339`), que no latocan.

La copia, en cambio, es **incondicional en cantidad**: los 384 bytes completos, siempre.

O sea: **las entradas que el bucle no visita se copian a la SRAM del SMC con el
contenido residual de la pila.**

## Cuanto, exactamente

Tabla `entries[8][4]`, entrada de 12 bytes (4+4+1+3, con `#pragma pack(1)` en
`smu74_discrete.h:29`): 8 x 4 x 12 = **384 bytes**. El bucle escribe solo
`sclk_count * mclk_count * 12`.

| `sclk_count` | `mclk_count` | barridos | **basura a la SRAM** |
|---:|---:|---:|---:|
| 1 | 1 | 12 | **372 B (96.9 %)** |
| 1 | 2 | 24 | 360 B (93.8 %) |
| 2 | 2 | 48 | 336 B (87.5 %) |
| 4 | 4 | 192 | 192 B (50.0 %) |
| 8 | 4 | 384 | 0 B |

El caso de un solo nivel de graficos y uno de memoria deja **372 de los 384 bytes**
con lo que hubiera en la pila. Y con la cantidad de niveles que lleva una RX 5500
(que no he medido: `RUNTIME_MISSING`) el caso de un solo nivel es el esperable, no la
excepcion.

Los 3 bytes de `padding` de cada entrada (`smu74_discrete.h:173`) **no los escribe
nadie ni siquiera en las entradas validas**: el escritor pone tres campos
(`polaris10_smumgr.c:1483-1485`) y los tres de relleno se copian a la SRAM tal cual,
con el residuo de la pila.

## La misma operacion, escrita bien, en la ruta heredada

No es que nobody supiera hacerlo. La ruta legacy SI:

`pm/legacy-dpm/si_dpm.c:4840`:

```c
SMC_SIslands_MCArbDramTimingRegisterSet arb_regs = { 0 };      /* inicializado */
```

y calcula el tamano en vez de usar el de la struct completa, `si_dpm.c:4850`:

```c
sizeof(SMC_SIslands_MCArbDramTimingRegisterSet) * (first_arb_set + i),
```

**Dos cosas distintas en dos rutas vivas que hacen lo mismo.** La de SI inicializa y
calcula el tamano; la de Polaris10 no inicializa y copia el tamano entero.

Ojo con la atribucion, porque aqui se equivoca la intuicion: el defecto **no nace en
Polaris10**. El barrido automatico lo encuentra tambien en `fiji_smumgr.c:1528`, con
la misma forma y el mismo nombre de variable. Ver "La clase de defecto" al final. Lo
que la ruta legacy demuestra no es que Polaris10 escribiera mal, sino que la forma
correcta existia y no se copio al cambiar de generacion.

Un detalle de nombre, porque buscar mal produce ceros que no son ausencias: el tipo
`MCArbDramTimingRegisterSet` **no existe** en la ruta Polaris12. Busqueda literal en
todo `drivers/gpu/drm/amd`: una sola aparicion, en
`legacy-dpm/sislands_smc.h:319-327`, usada por `si_dpm.c`. El nombre correcto en la
ruta SMU74 es **`SMU74_Discrete_MCArbDramTimingTableEntry`** (`smu74_discrete.h:169`).

## Un segundo defecto, latente: el indice de memoria puede pasar de 4

La segunda dimension de la tabla es `SMU__NUM_MCLK_DPM_LEVELS = 4` (`smu74.h:33`). Pero
el bucle recorre `hw_data->dpm_table.mclk_table.count`, y ese array es
`smu7_dpm_level dpm_levels[MAX_REGULAR_DPM_NUMBER]` con
`MAX_REGULAR_DPM_NUMBER = 8` (`smu7_hwmgr.h:95`, `:100`).

No hay ninguna comprobacion en el bucle. Como el elemento `(i,j)` vive en el byte
`(i*4 + j) * 12`:

| `i` | `j=4` | `j=5` | `j=6` | `j=7` |
|---:|---:|---:|---:|---:|
| 6 | 336 | 348 | 360 | 372 |
| 7 | **384** | **396** | **408** | **420** |

El objeto acaba en el byte 384. Aqui hay que separar dos cosas, porque una version
anterior de este documento las mezclaba y ademas se equivocaba en la cifra:

**Para `j` entre 4 y `count-1` con `i < 7` hay ALIASING, no salida.** Como la segunda
dimension es 4, `entries[i][4]` no es un elemento: es, en la memoria contigua,
`&entries[i+1][0]`. La escritura pisa una fila que ya pertenece al par de frecuencia
siguiente.

**Para `i == 7` con `j >= 4` si hay salida del objeto.** El ultimo elemento alcanzable es
`entries[7][7]`, que cae en el byte `(7*4+7)*12 = 420`, o sea **36 bytes mas alla** del
final. **36, no 48**: una version anterior de este documento decia 48 y era una resta
mal hecha.

| elemento | byte | situacion |
|---|---:|---|
| `entries[6][4]` | 336 | dentro, alias de `entries[7][0]` |
| `entries[7][3]` | 372 | dentro, el ultimo legitimo |
| `entries[7][4]` | **384** | **fuera**, primer byte fuera del objeto |
| `entries[7][7]` | **420** | **fuera, 36 bytes de mas** |

Y lo importante: **con `mclk_count <= 4` no ocurre ninguna de las dos cosas.** `j` nunca
pasa de 3 y las 32 entradas caen dentro y sin alias. El SMC solo admite 4 niveles de
memoria (`SMU__NUM_MCLK_DPM_LEVELS = 4`), asi que el caso realista esta limpio.

Por tanto: la comprobacion ausente es `PROVEN`, y el defecto solo se manifiesta si
`mclk_table.count > 4`. Ese valor viene del PPT del VBIOS: `RUNTIME_MISSING`. **No lo
puedo afirmar desde el corpus**, y la version anterior de este documento lo trataba como
si fuera un hecho.

## Y el contraste con la tabla de ventilacion, que si esta inicializada

`polaris10_smumgr.c:2170`, en `polaris10_thermal_setup_fan_table`:

```c
SMU74_Discrete_FanTable fan_table = { FDO_MODE_HARDWARE };
```

En C, un inicializador de agregado con un solo valor **pone a cero el resto**. Asi que
esta tabla **no tiene basura de pila**. Mismo fichero, mismo estilo de funcion, mismo
automatismo: uno inicializa y el otro no.

`sizeof(SMU74_Discrete_FanTable) == 36` bytes, contado campo a campo sobre
`smu74_discrete.h:377-394`: 14 campos de 2 bytes = 28, `RefreshPeriod` de 4 = 32,
`FdoMax` de 2 = 34, `TempSrc` de 1 = 35, `Padding` de 1 = 36. El codigo lo confirma
usando `sizeof(fan_table)` en la copia (`:2255`).

**Tres campos quedan a cero** por el inicializador y no los escribe nadie:
`TempCurr`, `SlopeCurr` y `PwmCurr` (`smu74_discrete.h:388-390`). Son los registros de
realimentacion que el microcodigo usa en su lazo de control. Que esten a cero sea lo
correcto es `SEMANTIC_MISSING`: el firmware no esta en el corpus.

## Lo que contiene la tabla de ventilacion

Cuatro constantes cocidas, sin justificacion en el codigo:
`HystUp = 1` (`:2236`), `HystSlope = 1` (`:2238`), `TempRespLim = 5` (`:2240`).

Las temperaturas se convierten de **centesimas de grado** a **decimas**: el
desplazamiento es `(50 + usTMin) / 100` (`:2221-2226`), o sea una correccion de medio
grado Celsius mas la division por 100. La unidad de entrada viene del comentario de
`hwmgr.h:669`, no del nombre del campo.

`FdoMax` se lee de la SRAM del SMC, del campo `FMAX_DUTY100` de `CG_FDO_CTRL1`
(`:2190-2191`, escrito en `:2248`), y `TempSrc` del campo `TEMP_SEL` de
`CG_MULT_THERMAL_CTRL` (`:2250-2252`).

`fdo_min` es el unico calculo de la funcion que se hace con cuidado de ancho: se
interpreta en `uint64_t` con `do_div` (`:2203-2206`) para que el producto con
`duty100` no desborde.

## Un nombre que engana

`PHM_PlatformCaps_FanSpeedInTableIsRPM` se activa **sin condicion de chip** en
`hwmgr/hwmgr.c:451-452`, dentro de las capacidades comunes de SMU7, y se consulta en
`smu7_thermal.c:154` para elegir entre fijar la salida maxima en RPM o en ciclo de
trabajo.

Es decir: **en esta familia lo que gobierna la tabla son revoluciones por minuto, no
ciclo de trabajo.** El `FdoMax` y el `duty100` de la firma son los dos nombres
equivocados. Un driver propio que lea esos campos creyendo que son porcentaje de
ventilador estara equivocado por un factor de las revoluciones.

## La guarda fan_table_start == 0

`polaris10_smumgr.c:2184-2188`. El valor viene de la cabecera del firmware:
`smu7_read_smc_sram_dword` de `SMU7_FIRMWARE_HEADER_LOCATION + offsetof(FanTable)`
(`:2530-2536`), que esta en offset 56 desde `0x20000` (`smu74.h:571`), o sea direccion
absoluta `0x20038`. Inicialmente vale 0 por el `kzalloc` de `:339`.

Cuando salta la guarda, lo que hace **no** es un fallo de copia: quita
`PHM_PlatformCaps_MicrocodeFanControl` y retorna. Como el arranque del control por
microcodigo esta detrás de ese mismo distintivo (`smu7_thermal.c:431-434`), el
microcodigo **nunca recibe `PPSMC_StartFanControl`** y el ventilador pasa a manos del
software.

Lo relevante es que **la guarda tambien absorbe un fallo de lectura**: si
`smu7_read_smc_sram_dword` devuelve error, `fan_table_start` conserva el 0 y la guarda
salta igual. Un fallo de lectura de la cabecera se manifiesta como "el firmware no
tiene tabla de ventilacion". Dos causas distintas, una sola respuesta, ninguna
distingue.

## Y la funcion devuelve 0 aunque todo falle

`polaris10_smumgr.c:2274-2278`:

```c
if (res)
        phm_cap_unset(hwmgr->platform_descriptor.platformCaps,
                PHM_PlatformCaps_MicrocodeFanControl);

return 0;
```

Tres pasos pueden fallar: la copia (`:2254`), `PPSMC_MSG_SetFanMinPwm` (`:2258`) y
`PPSMC_MSG_SetFanSclkTarget` (`:2266`). El unico efecto del fallo es quitar un
distintivo de capacidad. El retorno es **0 literal**. Y el unico llamador,
`smu7_start_thermal_controller`, **ignora** el valor:
`smum_thermal_setup_fan_table(hwmgr);` a secas (`smu7_thermal.c:461`).

Es el mismo patron que `094` (`polaris10_populate_smc_boot_level`, que tampoco puede
devolver fallo) y que `207` (validacion de VBIOS). Tres sitios, mismo modo de fallo:
convertir una ausencia de informacion en exito.

## Lo que el host nunca escribe

`McArbIndex` existe en dos sitios de la ruta SMU74 (`smu74_discrete.h:215` y `:434`).
Busqueda literal de `McArbIndex`, `McRegIndex` y `SeqIndex` en todo `pm/`: **solo
declaraciones de cabeceras, ninguna asignacion en ningun `.c`**.

O sea: el host rellena la tabla de 384 entradas pero **no rellena el indice que dice
cual usar**. El mecanismo de seleccion vive en el firmware. `CONNECTION_MISSING`.

Igual con los campos de mascara `MCARB_DRAM_TIMING_TABLE_*`: existen en
`include/asic_reg/smu/smu_7_0_1_sh_mask.h` como Definiciones generadas, y no los
escribe ningun `.c` de `pm/`. `PROVEN_ABSENT`.

## Un efecto secundario sobre hardware vivo

El bucle, para rellenar cada entrada, ejecuta
`atomctrl_set_engine_dram_timings_rv770` (`polaris10_smumgr.c:1473-1474`), que es la
tabla ATOM `DynamicMemorySettings` (`ppatomctrl.c:217-238`). **Eso programa el
hardware real.** Tras el bucle, la MC queda en la combinacion
`(sclk_count-1, mclk_count-1)` y no hay ninguna restauracion posterior: lo unico que
viene despues es la copia a SRAM (`:1511-1517`).

Ademas `atomctrl_set_ac_timing_ai` solo se invoca cuando `i == 0` (`:1504-1505`).

Y `McArbBurstTime` se lee **de MMIO** (`mmMC_ARB_BURST_TIME`, via
`PHM_READ_FIELD` definido en `smu_helper.h:149-150` como
`PHM_GET_FIELD(cgs_read_register(...), reg, field)`), despues de que el VBIOS haya
programado. Solo se copia el campo `STATE0` (bits 0-4, mascara `0x1f`,
`gmc_8_1_sh_mask.h:1243-1244`); los otros campos que ese registro define en GFX8
(`STATE1`, `TRRDS0/1`, `TRRDL0/1`) **no llegan a la tabla por esta ruta**.

## Clasificacion

- `SMC_ARB_UNINITIALIZED_STACK = PROVEN`: `arb_regs` sin inicializador ni `memset`
  (`:1494`).
- `SMC_ARB_COPY_ALWAYS_FULL = PROVEN`: 384 bytes siempre (`:1515`), frente a
  `sclk_count * mclk_count * 12` escritos.
- `SMC_ARB_GARBAGE_AMOUNT = PROVEN_DERIVED`, magnitud `RUNTIME_MISSING` (los contadores
  vienen del PPT). Con 1 nivel de graficos y 1 de memoria: 372 de 384 bytes.
- `SMC_ARB_PADDING_NEVER_WRITTEN = PROVEN_ABSENT`: los 3 bytes de relleno de cada
  entrada, ni en las validas.
- `SMC_ARB_LEGACY_PATH_IS_SAFE = PROVEN`: `si_dpm.c:4840` inicializa a cero y `:4850`
  calcula el tamano. La forma correcta existia antes de SMU 7.x y no se copio.
- `SMC_ARB_DEFECT_ORIGINATES_IN_SMU73 = PROVEN`: el mismo defecto en
  `fiji_smumgr.c:1528`, mismo nombre de variable, misma forma. No es de Polaris10.
  Localizado con `uninit_copy`, no a ojo.
- `SMC_ARB_DIMENSION_MISMATCH = PROVEN`: `entries[][4]` frente a `dpm_levels[8]`, sin
  comprobacion. Con `mclk_count > 4`: aliasing para `i < 7`, y **36 bytes fuera** del
  objeto para `i == 7`. Aprovechabilidad `RUNTIME_MISSING` (depende de
  `mclk_table.count`). **Una version anterior de este documento decia 48 bytes: cifra
  erroneous.**
- `SMC_ARB_CLEAN_IF_MCLK_LE_4 = PROVEN_DERIVED`: con `mclk_count <= 4`, `j` nunca pasa
  de 3 y las 32 entradas caen dentro y sin alias. Cero bytes fuera, cero aliasing.
- `SMC_FAN_TABLE_INITIALIZED = PROVEN_DERIVED`: `= { FDO_MODE_HARDWARE }` (`:2170`)
  pone a cero el resto. Sin basura de pila.
- `SMC_FAN_TABLE_SIZE = PROVEN_DERIVED`: 36 bytes, contado campo a campo y coherente con
  el `sizeof` que usa el codigo.
- `SMC_FAN_FEEDBACK_FIELDS_ZERO = PROVEN_DERIVED`: `TempCurr`, `SlopeCurr`, `PwmCurr`.
  Si es lo correcto, `SEMANTIC_MISSING`.
- `SMC_FAN_UNITS_CENTI_TO_DECI = PROVEN_DERIVED`: `(50 + usTMin)/100`; entrada en
  centesimas segun `hwmgr.h:669`.
- `SMC_FAN_THREE_HARDCODED_CONSTANTS = PROVEN`: `HystUp = 1`, `HystSlope = 1`,
  `TempRespLim = 5`.
- `SMC_FAN_TABLE_IS_RPM = PROVEN`: `FanSpeedInTableIsRPM` sin condicion de chip
  (`hwmgr.c:451-452`), consultado en `smu7_thermal.c:154`.
- `SMC_FAN_GUARD_ABSORBS_READ_FAILURE = PROVEN_DERIVED`: el 0 inicial y el fallo de
  lectura producen la misma respuesta.
- `SMC_FAN_SETUP_ALWAYS_RETURNS_ZERO = PROVEN`: `return 0` literal (`:2278`) con tres
  pasos que pueden fallar, y el unico llamador ignora el retorno (`smu7_thermal.c:461`).
- `SMC_MC_ARB_INDEX_NEVER_WRITTEN = PROVEN_ABSENT`: `McArbIndex` solo aparece en
  cabeceras. `CONNECTION_MISSING` sobre el mecanismo de seleccion.
- `SMC_MC_PROGRAMMED_AND_NOT_RESTORED = PROVEN_DERIVED`: el bucle programa la MC y no
  hay restauracion posterior.

## Lo que esto NO dice

No dice cuantos niveles hay en esta placa. Es un dato del PPT, que no esta en el
corpus. Todo lo anterior es analisis estatico de la ruta.

No dice que el firmware lea una entrada invalida: si el microcodigo selecciona por el
indice de nivel y solo hay 1x1 niveles validos, las 372 entradas basura podrian no
llegarse a leer. Que las lea o no es `NOT_IN_CORPUS`.

No dice que el aliasing ni el desbordamiento sean alcanzables. Requieren
`mclk_table.count > 4`, y "los PPT de Polaris no suelen llegar ahi" es una expectativa,
no una medida: `RUNTIME_MISSING`. Una version anterior de este documento lo daba por
hecho y ademas citaba 48 bytes en vez de 36.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.

## La clase de defecto, no solo este caso: herramienta `uninit_copy`

Un solo hallazgo no es accionable; una **clase** de defecto si. Este no es un descuido
aislado: es "agregado de pila sin inicializar, copiado a `sizeof()` del tipo completo",
y se detecta automaticamente. Escribi `tools/uninit_copy.py` para eso y lobarre las
cuatro rutas de gestion de energia del arbol (39 ficheros, `smumgr/` y `legacy-dpm/`).

Resultado, y es el hallazgo que compensa la herramienta:

```
uninit_copy 1.0.0 · 39 ficheros leidos · 2 candidatos · 2 en las clases pedidas
  FULL_SIZE_COPY fiji_smumgr.c:1528       struct SMU73_Discrete_MCArbDramTimingTable arb_regs
  FULL_SIZE_COPY polaris10_smumgr.c:1494  struct SMU74_Discrete_MCArbDramTimingTable arb_regs
```

**El mismo defecto existe en Fiji (SMU 7.3) y en Polaris (SMU 7.4), con el mismo
nombre de variable y la misma forma.** `fiji_smumgr.c:1528` es el caso de Polaris12
trasladado una generacion atras:

```c
struct SMU73_Discrete_MCArbDramTimingTable arb_regs;      /* 1528  sin inicializador */
for (i = 0; i < data->dpm_table.sclk_table.count; i++) {  /* 1532 */
        for (j = 0; j < data->dpm_table.mclk_table.count; j++) {
                ... &arb_regs.entries[i][j]);            /* 1537 */
        }
result = smu7_copy_bytes_to_smc(...,
                (uint8_t *)&arb_regs,
                sizeof(SMU73_Discrete_MCArbDramTimingTable),   /* 1548 */
                ...);
```

O sea: no es que upstream escribiera mal Polaris10. **El error viene de Fiji y se
hereda.** Eso cambia la atribucion: el defecto nace en SMU 7.3, donde la copia a
tamano completo era correcta porque ahi el bucle si recorria la tabla entera, y se
vuelve defectuoso cuando el bucle pasa a barrer solo `count x count` sin que la copia
acompanase el cambio.

La ruta legacy, como debe, **no sale**, y su no salida es lo que da valor a las dos
lineas de arriba.

### El self-test cazo cuatro fallos reales, incluido uno en mi propia fuente

Los documento porque es lo que hace que una herramienta sirva:

1. **Solo miraba el primer argumento de la llamada.** En el codigo real `&arb_regs` es
   el **tercero** (`hwmgr`, destino, `(uint8_t *)&arb_regs`, `sizeof`, `SMC_RAM_END`).
   Mi primera version devolvia cero: no "no hay caso", sino "no se ha mirado bien". El
   cero silencioso es el fallo que mas caro sale.
2. **No quitaba casts.** `(uint8_t *)&arb_regs` no es igual a `&arb_regs`, asi que
   tampoco casaba.
3. **Solo buscaba declaraciones con la palabra `struct`.** El codigo de Polaris
   declara `struct SMU74_... arb_regs;` y el de legacy
   `SMC_SIslands_... arb_regs;` por typedef. Con solo la primera forma se perdia la
   mitad de los casos. Ahora hay dos formas, y las de typedef salen como
   `TYPEDEF_CANDIDATE` hasta confirmar el tipo con `--structs-from`, para no tratar un
   tipo sin verificar como si fuera struct.
4. **Numeros de linea desplazados en uno** cuando la firma de la funcion se parte en dos
   lineas, que es justo como esta escrita la de Polaris. El self-test con fixtures de
   una sola linea **no lo cazaba**: todos los fixtures Caben en una linea. Anadi el
   caso 12 con la firma partida precisamente por eso. Lo detecte al comparar el 1493
   que daba la herramienta con el 1494 que da `grep -n`.

Y un quinto, que no era de la herramienta sino mio: **escribi dos caracteres CJK en el
propio fuente**, precisamente al citar los que estaba corrigiendo en los informes. El caso 9 comprueba el fuente contra rangos CJK y fallo
solo. Es exactamente el fallo que vengo corrigiendo en los informes, apareciendo en la
herramienta nueva.

Estado: `TOOL_VALIDATED`. 13 vectores de self-test, incluidos un par que se confirma
mutuamente (el mismo `sizeof` con y sin asterisco produce `FULL_SIZE_COPY` y
`COMPUTED_SIZE`), una trampa de comentarios y cadenas, escalares que no deben salir, y
un caso de numero de linea. La salida distingue un caso malo de un caso bueno, que es
la unica forma de que signifique algo.
