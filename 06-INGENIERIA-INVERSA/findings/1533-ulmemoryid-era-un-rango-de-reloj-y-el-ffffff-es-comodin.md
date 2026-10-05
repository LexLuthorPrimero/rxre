# 1533 — `ulMemoryID` era un rango de reloj de 24 bits, y el 0xFFFFFF de tres tablas es un comodín

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2
CLASSIFICATION=SEMANTICA-DERIVADA + CIERRE-DE-HUECO-NOMBRADO
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
CIERRA=el hueco "la semantica de ulMemoryID" que el 1530 dejo nombrado
ESTADO=PROBADO · ulMemoryID es ATOM_MEMORY_SETTING_ID_CONFIG: ucMemBlkId[31:24] + ulMemClockRange[23:0]
       · los cuatro bloques tienen ucMemBlkId = 0
       · el 0xFFFFFF de tres tablas es el rango COMODIN, no un valor de relleno que se ignores
       · el endianness NO cambia las posiciones de los campos, solo el orden de declaracion
       · y el driver no decodifica esto en ninguna parte: solo existe la definicion
```

## 1. El hueco que cierra esto

El 1532 y el 1530 dejaron esto escrito, textual:

> `0x00FFFFFF` es el mismo valor en los tres bloques que no son el de parcheo de reloj, y
> `0x00009C40` = 40 000 decimal. **No interpreto ninguno de los dos:** no hay fuente en el corpus que
> declare la unidad de `ulMemoryID`.

Es decir: cuatro numeros, sin significado, y sin fuente. Eso es exactamente el tipo de cosa que
produce hallucination si se sigue calculando. Se cierra leyendo la estructura, que es lo quetocaba.

## 2. La estructura existe, y es `ulMemoryID`

`ATOM_MEMORY_SETTING_DATA_BLOCK` empieza por un `ATOM_MEMORY_SETTING_ID_CONFIG_ACCESS`, y ese union
contiene un `ULONG` crudo. El `ulMemoryID` del 1530 **es** ese `ULONG`. Y el bitfield esta escrito
(`atombios.h:7449-7457`):

```c
  typedef struct _ATOM_MEMORY_SETTING_ID_CONFIG{
  #if ATOM_BIG_ENDIAN
          ULONG   ucMemBlkId:8;
          ULONG   ulMemClockRange:24;
  #else
          ULONG   ulMemClockRange:24;
          ULONG   ucMemBlkId:8;
  #endif
  }ATOM_MEMORY_SETTING_ID_CONFIG;
```

**Ojo con el `#if`, porque es una trampa de lectura rapida.** El endianness cambia el *orden de
declaracion* de los campos, pero **no sus posiciones**: en las dos ramas `ulMemClockRange` ocupa los
bits 23-0 y `ucMemBlkId` los bits 31-24. Si uno lee solo la rama `#else` y aplica "el primero que se
declara va arriba", intercambia los dos campos y decodifica el numero al reves.

Con las posiciones correctas:

| bloque | `ulMemoryID` | `ucMemBlkId` | `ulMemClockRange` |
|---|---|--:|---|
| `usMemClkPatchTbl` | `0x00009C40` | 0 | 40 000 |
| `usMemAdjustTbl` | `0x00FFFFFF` | 0 | 16 777 215 |
| `usMcAdjustPerTileTbl` | `0x00FFFFFF` | 0 | 16 777 215 |
| `usMcPhyInitTable` | `0x00FFFFFF` | 0 | 16 777 215 |

## 3. Lo que cambia: tres tablas son comodin, no relleno

`0xFFFFFF` en 24 bits es **todos los unos**. En un campo que se compara contra un rango de reloj, eso
es un **comodin**: la entrada aplica a cualquier reloj de memoria. No es un valor de relleno, no es
"sin definir", y no es un dato que se pueda ignorar.

Eso reordena lo que significan las tablas:

```text
  usMcPhyInitTable      25 registros   SIN RESTRICCION de reloj.  El PHY se programa igual a todos
                                         los relojes.  Coherente con ser una inicializacion de PHY.

  usMcAdjustPerTileTbl   1 registro    SIN RESTRICCION de reloj.  Un ajuste por tile, siempre.

  usMemAdjustTbl        vacio          SIN RESTRICCION de reloj, y sin entradas.  No hace nada.

  usMemClkPatchTbl      14 registros   SOLO para el rango 40 000.  Este es el unico que depende del
                                         reloj, y el nombre del campo lo confirma: "ClkPatch".
```

**El nombre del campo y el valor coinciden.** Una tabla llamada *parcheo de reloj* es la unica que
lleva un rango de reloj concreto, y las otras tres llevan el comodin. Eso es una corroboracion por
nombre, y es independiente del decode.

Y el `0x00009C40` = 40 000 sigue **sin unidad declarada**: el corpus usa "10kHz" para `ulClkRange` en
otros sitios, pero no para `ulMemClockRange`, y no los voy a igualar por parecido de nombre.
`NOT_DETERMINED`, con la razon.

> **ACTUALIZADO por el hallazgo `1542`: este punto quedo RESUELTO despues.** El mismo campo
> `ulMemClockRange` recorre once valores —40 000, 80 000, 90 000, 100 000, 112 500, 125 000,
> 137 500, 150 000, 162 500, 175 000, 200 000— y en unidades de **10 kHz** son exactamente la escalera
> de reloj de DRAM de 400 a 2000 MHz. **La unidad es 10 kHz, deducida de la estructura de la tabla, no
> de un comentario.** El `NOT_DETERMINED` de esta linea ya no aplica; se conserva la frase porque es el
> estado en el momento en que se escribio este hallazgo.

## 4. El detalle que reinforce todo: el driver tampoco lo decodifica

```text
  ulMemClockRange / ucMemBlkId / slAccess   aparecen en UN solo sitio:
                                             include/atombios.h:7449-7463, la definicion
```

Cero usos en `amdgpu/*.c`. Ni una vez.

Eso no es un detalle: es **la misma conclusion del 1530 vista desde otro campo**. El 1530 demostro
que el driver no escribe ningun registro de configuracion de memoria. Esto demuestra que tampoco
*lee* ninguna de las tablas que el ROM pone ahi para el. **El driver de Linux no consulta la
configuracion de memoria de esta placa en ninguna parte del arbol.**

Y el 1530 ya habia medido el otro lado: el bloque `usMemAdjustTbl` esta **vacio** (una sola entrada, el
centinela `0xFFFF`). Una tabla vacia que el driver tampoco consulta. Dos wasteful, por el mismo motivo.

## 5. Estado

```text
CERRADO    la semantica de ulMemoryID.  ucMemBlkId en [31:24], ulMemClockRange en [23:0].
           Los cuatro con ucMemBlkId = 0.
CERRADO    que son las tres tablas 0xFFFFFF.  Comodin de rango de reloj, no relleno.
CERRADO    por que solo una de las cuatro depende del reloj.  Por su nombre.
NUEVO      el driver no decodifica el campo en ninguna parte del arbol.
ABIERTO    la unidad de ulMemClockRange.  No declarada.  40 000 no se convierte en nada.
ABIERTO    el significado de ucMemBlkId = 0.  Cero puede ser "bloque 0" o "no aplica".
RIESGO     ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE     lectura de un volcado con estructuras del header de 7.1.3.  El #if de endianness lo
           he resuelto leyendo las dos ramas, no suponiendo.
```

## 6. Decision log (§103)

```text
DECISION    cerrar el hueco declarando la semantica del campo y dejar la unidad abierta
WHY         el campo tiene estructura, posiciones y un valor que se explica solo (todos los unos).
            Lo que no tiene es unidad, y la unidad no se inventa.
ALTERNATIVA  declarar "10kHz" por analogia con ulClkRange.  Descartada: son campos distintos en
            structs distintos, y 40 000 en 10kHz son 400 MHz, que no encaja con una placa cuyo
            techo esta medido en 1500 MHz.  Una unidad que da un numero absurdo no se publica
            aunque el nombre la sugiera.
DISCriminante  la unidad esta en el codigo de la BIOS, que no tenemos.  NO esta en el corpus.  Es
            una dependencia externa, no un hueco nuestro.
CONSECUENCIA  el 1530 pierde un NOT_DETERMINED y gana un hecho: tres de las cuatro tablas de
            memoria aplican a cualquier reloj.
REVERSIBLE  si el corpus tuviera una version de atombios.h con el bitfield en otro orden, la
            lectura de ucMemBlkId / ulMemClockRange se invierte.  He leido las dos ramas del #if.
```

## 7. Una reflexion sobre el metodo, porque es el segundo error de lectura de hoy

Este hueco estaba abierto porque en el 1530 vi un `0x00FFFFFF` y un `0x00009C40` y no me pareci
a nada. **Los use como respuesta, no como problema.** Un `ULONG` cuyo primer miembro es un
`ATOM_MEMORY_SETTING_ID_CONFIG_ACCESS` no es un numero: es una estructura con dos campos, y el
union existe precisamente para poder leerlo crudo.

Los dos errores de hoy —contear la tabla de comandos con el puntero de datos, y leer los remaps como
nibbles—*y este*, son la misma cosa: **tratar un campo con estructura como si fuera un entero.** Los
tres se cazaron con una comprobacion gratuita. Y los tres eran el mismo error conceptual.

> Regla que queda: antes de interpretar un valor, comprobar si el tipo que lo contiene es un
> entero. En C, un `union` con una struct y un `ULONG` es una invitation a leerlo mal.
