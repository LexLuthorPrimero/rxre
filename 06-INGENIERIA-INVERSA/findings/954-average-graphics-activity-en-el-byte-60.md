# 954 · AverageGraphicsActivity está en el byte 60, y se mide compilando

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Estado de `953`
>
> ```
> CLAIM-953 v1  el offset de AverageGraphicsActivity -> NOT_DETERMINED
>               ("struct ausente del BTF")
> CLAIM-954     PROVEN por compilacion. Byte 60. sizeof = 120.
> ```
>
> Y el hallazgo de método es más útil que el número:
>
> **Mi primer cálculo del offset daba 52. El real es 60.** Me equivoqué por
> confiar en un comentario del propio código fuente que el propio código fuente
> contradice doce líneas después.

## 1. El nombre real, y por qué cuatro búsquedas fallaron

```
inc/smumgr.h:36          SMU_SoftRegisters = 0        <- una ENUM de bloques, no un struct
polaris10_smumgr.c:2418 static uint32_t polaris10_get_offsetof(uint32_t type, uint32_t member)
:2421       case SMU_SoftRegisters:
:2427       case AverageGraphicsActivity:
                return offsetof(SMU74_SoftRegisters, AverageGraphicsActivity);
```

**El struct se llama `SMU74_SoftRegisters`**, y solo aparece en la declaración de
ese `switch`, en `polaris10_smumgr.c:2428`. No lo busqué primero: lo deduje tras
ver que `SMU_SoftRegisters` era una enum.

**Es la cuarta vez hoy que un nombre con guiones bajos y sufijo numérico me hace
fallar.** Las cuatro:

```
ATOM_PowerTuneTable        -> real: ATOM_Tonga_PowerTune_Table
ATOM_VoltageLookupTable     -> real: ATOM_Tonga_Voltage_Lookup_Table
ATOM_Voltage_Lookup_Record  -> real: ATOM_Tonga_Voltage_Lookup_Record
SMU_SoftRegisters          -> real: SMU74_SoftRegisters
```

**El patron es inequivoco y ya no es una casualidad: en este codebase los structs
de ATOM y de SMU llevan el nombre de la generacion con guion bajo antes del
sufijo.** Decir «buscar el nombre» es una instruccion que produce ceros en este
repositorio. La instruccion correcta es **leer la declaracion**.

## 2. Y `SMU74_SoftRegisters` no esta en el BTF

```
btfq.py struct SMU74_SoftRegisters   -> (ninguna struct coincide)
```

**Y eso es informacion, no un fallo de busqueda**, porque `SMU74_Firmware_Header` y
`SMU74_Discrete_DpmTable` **si** estan en el BTF del modulo cargado. O sea que el
BTF tiene los tipos `SMU74_*` que se usan en la cabecera de firmware y en la
tabla DPM, y **no tiene este**, que se usa en una funcion de calculo de offsets.

**Mi regla central dice que ningun offset de struct va contra la cabecera de
fuentes.** Este no tiene BTF, asi que el offset **no sale de la cabecera**: sale de
**compilarla y medir `offsetof`**. Que es mejor que ninguna de las dos cosas, y es
distinto de las dos.

## 3. La medicion, y el error que casi se publica

Mi primer intento conto los campos:

```
campos uint32_t declarados: 25  ->  tamaño = 100 bytes
AverageGraphicsActivity  indice 14  ->  byte 52      <-- MAL
```

**Falso, y por un motivo que estaba a la vista.** El script filtraba solo las
lineas que empiezan por `uint32_t` y asignaba offsets por ese indice. Pero el
struct **tiene ocho `uint8_t` intercalados**, justo entre `HandshakeDisables` y
`AverageGraphicsActivity`:

```
smu74.h:518   uint32_t  HandshakeDisables;        -> 48
smu74.h:520-528   uint8_t  DisplayPhy1Config ... DisplayPhy8Config;   -> 52..59
smu74.h:530   uint32_t  AverageGraphicsActivity;  -> 60
```

Y lo que me engaño fue el comentario **de la linea anterior al struct**:

```
smu74.h:501   /* All 'soft registers' should be uint32_t. */
smu74.h:502   struct SMU74_SoftRegisters {
```

**«should be» es una intencion, no un hecho, y el struct la incumple.** Aplicar un
comentario sobre un codigo que tengo delante y que lo contradice es el error mas
basico posible, y lo cometi con un script que ademas **no lo mire**... y aun asi me
salio un numero plausible, un multiplo de 4, con forma de offset.

La medicion de verdad, compilando el struct tal cual esta declarado:

```c
gcc -O0 && ./m
    sizeof(SMU74_SoftRegisters)          = 120
    offsetof HandshakeDisables           = 48
    offsetof AverageGraphicsActivity     = 60      <== el que buscamos
    offsetof AverageMemoryActivity       = 64
    offsetof AverageGioActivity          = 68
    offsetof Activity_Weight             = 116
```

**Y el control aritmetico cuadra solo:** 13 `uint32_t` ocupan 0..51, los ocho
`uint8_t` ocupan 52..59, y el siguiente `uint32_t` cae en 60, que ya es multiplo
de 4. **Dos metodos independientes dan 60.**

## 4. La direccion completa, y lo que queda

```
AverageGraphicsActivity = soft_regs_start + 60

soft_regs_start = CU32( SMU7_FIRMWARE_HEADER_LOCATION
                      + offsetof(SMU74_Firmware_Header, SoftRegisters) )
                  = polaris10_smumgr.c:2510-2517
                  = RUNTIME_MISSING  (contenido de la RAM del SMC)

sizeof(SMU74_SoftRegisters) = 120 bytes, 41 campos
```

**El ultimo paso que falta es una lectura de la RAM del SMC**, que es
`RUNTIME_MISSING` por la via conocida, y que **el metodo de `946` ya determina
como distinta del volcado masivo de registros**: una lectura dirigida de una
direccion que el driver acaba de usar para imprimir un numero en pantalla.

**Asi que el punto 8 de `951` —«¿el registro de actividad se actualiza?»— tiene
ahora su direccion exacta**, que antes no tenia:

```
leer soft_regs_start de la cabecera de firmware
leer soft_regs_start + 60 dos veces, separadas en el tiempo
si cambia, el firmware actualiza el registro y el 0 % de 950 es real
si no cambia, el sensor miente en esta placa
```

**Y ese es el discriminante limpio que `951` necesitaba.** Dos lecturas del mismo
registro separadas en el tiempo separan las dos lecturas del punto 2 de `953` sin
necesitar saber cuanto dura la ventana de promediado.

## 5. Por que compilar es mejor que contar, y cuando no lo es

Esto es una mejora de metodo general, no un detalle de esta finding:

```
CONTAR sobre la cabecera        rapido, y falla en cuanto hay padido o
                                campos de tamaño mixto
BTF                              la autoridad, y no esta para todos los tipos
COMPILAR y medir offsetof        funciona siempre que el tipo sea compilable,
                                y no depende de que el BTF lo tenga
```

**Y el BTF tiene prioridad, no el compilador.** Aqui no habia BTF, asi que
compilar es la mejor opcion disponible. **Si hubiera habido BTF, el BTF habria
ganado**, porque refleja el binario que se esta ejecutando y no el fuente que se
lee.

**El orden correcto es: BTF si esta; si no, compilacion; contar a mano solo si no
hay ninguna de las dos, y entonces marcando el resultado como derivado y no como
medido.**

## 6. Errores de esta iteracion

**1.** Di `NOT_DETERMINED` sobre el offset en `953` tras una sola consulta de BTF,
y lo resolvi en los treinta segundos siguientes. **Un `NOT_DETERMINED` decidido
por una consulta es un `NOT_DETERMINED` sin investigar**, que es peor que
`UNKNOWN` porque aparenta cierre.

**2.** Filtre el struct por `uint32_t` porque el comentario de la linea anterior
decia que todos los soft registers son `uint32_t`. **El comentario era una
intencion y el struct no la cumple.** Y el numero que salio —52— era un multiplo
de 4, con forma de offset, y por eso casi lo publico sin mirarlo.

**3.** Busque el struct por `SMU_SoftRegisters`, que es una enum. **Un enum y un
struct con el mismo nombre se diferencian por el uso, no por el nombre**, y el uso
se ve leyendo la llamada: `offsetof(SMU74_SoftRegisters, AverageGraphicsActivity)`.

## 7. Frontier siguiente

```
1.  el struct real es SMU74_SoftRegisters, con sufijo de generacion   PROVEN
2.  offsetof AverageGraphicsActivity == 60, medido compilando        PROVEN
3.  sizeof == 120, 41 campos                                         PROVEN
4.  el BTF del modulo NO tiene este tipo                             PROVEN
5.  soft_regs_start desde la cabecera de firmware                   RUNTIME_MISSING
6.  direccion completa = soft_regs_start + 60                        PROVEN_DERIVED
7.  la ventana de promediado sigue siendo del firmware               SEMANTIC_MISSING
8.  el techo termico                                                SEMANTIC_MISSING
```

**El frente util es el punto 5, y es el primer `RUNTIME_MISSING` de la linea que
tiene una direccion exacta y un metodo de lectura distinguible del volcado masivo
que reinicia la maquina.**

**Una lectura dirigida de un dword en la cabecera de firmware, con el SMC ya
funcionando, es la operacion de menor riesgo que puede deshacer el punto 6 de
`951`**, y es de solo lectura, sin escritura al hardware, sin registros de
diagnostico. **Es, de todos los `RUNTIME_MISSING` que he enumerado, el que tiene
mejor relacion entre lo que desbloquea y lo que cuesta.**

Criterio de cierre: el valor de `soft_regs_start` leido de la cabecera de firmware,
con el procedimiento y su exit, o `NOT_EXECUTED` con la razon por la que la
politica no lo concede. **Y si se ejecuta, la segunda lectura de
`soft_regs_start + 60` separada en el tiempo, que es la que separa las dos lecturas
de `953` y convierte el `0 %` de `950` en un dato con significado o en un sensor
que no dice nada.**
