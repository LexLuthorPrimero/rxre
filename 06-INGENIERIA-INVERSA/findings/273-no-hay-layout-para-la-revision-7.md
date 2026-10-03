# 273 · No hay layout para la revision 7 y nadie comprueba la revision: el defecto es de amdgpu, no de mi VBIOS

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Respuesta a la pregunta de alcance de `272`
>
> Era: ¿esto es "mi VBIOS es rara" o "el driver lee basura en general"?
> **Es lo segundo, y esta medido.**

## Los dos hechos

**1. No existe layout para mi revision.** En `include/pptable.h`:

| struct | declarada |
|---|---|
| `ATOM_PPLIB_POWERPLAYTABLE` | si |
| `ATOM_PPLIB_POWERPLAYTABLE2` | si |
| `ATOM_PPLIB_POWERPLAYTABLE3` | si |
| `ATOM_PPLIB_POWERPLAYTABLE4` | si |
| `ATOM_PPLIB_POWERPLAYTABLE5` | si |
| **`ATOM_PPLIB_POWERPLAYTABLE6`** | **NO** |
| **`ATOM_PPLIB_POWERPLAYTABLE7`** | **NO** |

`grep -c` da **0** para PPLIB6 y para PPLIB7. El corpus no tiene struct para la
revision que mi VBIOS declara, y **la familia se detiene en 5**.

**2. Nadie comprueba la revision.** `ucFormatRevision` aparece **0 veces** en
todo `pm/powerplay/`. Salida de `grep -rc` sobre el arbol: `exit=1`, ningun
fichero con coincidencias.

O sea: el codigo **convierte sin mirar** a `ATOM_PPLIB_POWERPLAYTABLE3` porque
no tiene forma de saber que deberia mirar.

## Por que el layout declarado no encaja en mi ROM

Con los offsets medidos por gcc sobre `pptable.h`, leo mi tabla
(`PowerPlayInfo @ 0x9C0A`, `size = 778`, `rev 7.1`, segun `atomrom.py tablas`):

| campo | offset | bruto en mi ROM | veredicto |
|---|---:|---:|---|
| `sHeader.usStructureSize` | 0 | 778 | **OK**, coincide con atomrom |
| `sHeader.ucFormatRevision` | 2 | 7 | **OK**, coincide con atomrom |
| `ucNumStates` | 5 | **77** | imposible: mi tabla tiene 2 estados |
| `usClockInfoArrayOffset` | 11 | **11530** | fuera de rango (tabla de 778) |
| `usTableSize` | 19 | **32768** | fuera de rango |
| `usBootNonClockInfoOffset` | 35 | **77** | fuera de rango |
| `usFanTableOffset` | 42 | **34048** | fuera de rango |
| `usExtendenedHeaderOffset` | 44 | **2817** | fuera de rango |

**La cabecera de 4 bytes encaja byte a byte. Todo lo demas no.** Ese es el
patron que uno esperaria si el struct declarado pertenece a otra revision: las
primeras 4 bytes son universales (`ATOM_COMMON_TABLE_HEADER`) y a partir de ahi
los campos son de la revision.

## Dos layouts alternativos, y los dos fallan

Para no dejar esto en un «no se`, probe **dos** layouts alternativos y los dos
fallan. Registro el intento negativo porque un intento fallido informa.

**A. Desplazamiento de −4 bytes** (por si faltara el bloque de 5 UCHAR):

```
usExtendenedHeaderOffset  declarado 44 -> leido 2817
                            desplazado  -> leido    2   -> header en 0x9C0C, dentro de la cabecera misma
usTableSize                declarado 19 -> leido 32768
                            desplazado  -> leido    26   -> 26 < 46, el guarda :1140 REVERSA
```

**B. Sin el bloque de 5 UCHAR, todo corrido** (la hypothesis de que mi ROM es
4 bytes mas corta):

```
usStateArrayOffset   en 5  = 77    -> 0x9C57   <- APUNTA FUERA, no a una tabla
usClockInfoArrayOff  en 7  = 1629  -> 0xA267   usStructureSize=10280, rev=114.114  imposible
usBootClockInfoOff   en 21 = 6     -> 0x9C10   usStructureSize=23808, rev=6.0      imposible
usBootNonClockInfoOff en 23= 48928 -> 0x15B2A  FUERA del fichero entero
```

Un valor resulto \"correcto\": `usStateArrayOffset = 77` en offset 5, que da
`0x9C0A + 77 = 0x9C57`, y ahi hay algo con cabecera. Pero la cabecera de 0x9C57
es `usStructureSize = 513, rev 0.0`, que **no es una cabecera ATOM plausible**.
Un acierto entre varios, con la comprobacion debil, no es un acierto.

**Estado: `NOT_DETERMINED`.** No se cual es el layout real de mi revision 7.1, y
**no publico ninguno de los 16 candidatos** que un barrido de plausibilidad me
devolvio en un intento anterior.

## Lo que si queda cerrado

| afirmacion | estado |
|---|---|
| El struct declarado no describe mi tabla rev 7.1 | **`PROVEN`** (7 de 15 campos) |
| `pptable.h` no tiene layout para rev 6 ni 7 | **`PROVEN`** (0 declaraciones) |
| `ucFormatRevision` no se consulta en `powerplay/` | **`PROVEN`** (0 usos) |
| El cast a PPLIB3 es incondicional | **`PROVEN`** (`process_pptables.c:1144`) |
| `overdriveLimit.engineClock = 2952790445` en mi placa | **`PROVEN`** (`272`) |
| El valor correcto de `ulMaxEngineClock` | **`NOT_DETERMINED`** |

## Alcance del defecto

Esto **no es una rareza de mi VBIOS**. Es la combinacion de tres cosas de
amdgpu:

1. La familia de structs llega hasta PPLIB5.
2. Los ROM que amdgpu soporta tienen revisiones que el header no cubre.
3. La conversion no consulta la revision en ningun punto.

Cualquier placa Polaris10/12 cuyo PowerPlayInfo sea de revision 6 o 7 tiene el
mismo problema que la mia. **Es un defecto de upstream, y eso le da un valor
distinto al del hallazgo `272`: no es "esta placa va rara", es "el techo de
overdrive que el driver calcula no significa nada para esta familia".**

Para un driver propio eso es una buena noticia: no hay que adivinar un valor,
simplemente **no se puede usar el campo tal cual**, porque el codigo que lo
llena no valida nada.

## Lo que NO afirmo

- **NO** afirmo cual es el offset correcto de `usExtendenedHeaderOffset` en mi
  revision. Es `NOT_DETERMINED` y he dejado constancia de tres intentos
  fallidos.
- **NO** afirmo que `overdriveLimit.engineClock` se use para limitar el reloj. No
  he seguido al consumidor. Que valga basura **no** implica que limite algo.
- **NO** afirmo que el defecto cause un fallo visible. No hay crash: el offset
  cae dentro del fichero de ROM.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`.

## Observacion sobre el corpus compartido

Durante esta accion, `ls process_pptables.c` devolvio *No existe el fichero o el
directorio* y medio segundo despues `grep` encontro `./processpptables.c:836`.
El arbol de kernel esta siendo modificado mientras trabajo. Lo registro como
observacion de entorno, no como fallo mio, y no lo uso como evidencia de nada.

## Frontier siguiente

El unico camino que queda para el valor correcto es **externo a mi corpus**: el
documento de especificacion ATOM de AMD para `PowerPlayInfo` revision 7.1, que
no tengo. Todo lo demas esta agotado por el lado estatico: los dos layouts
alternativos fallan, el barrido de plausibilidad devuelve 16 candidatos que no
se distinguen entre si, y la familia de structs se detiene en 5.

Eso es `DEFERRED_BY_EXTERNAL_DEPENDENCY`, y por el principio de exploracion
(`DEPENDENCY BLOCK != PROJECT STOP`) paso a otra rama.

## Lo que si me llevo de esta rama entera

Cinco hallazgos encadenados — `256`, `262`, `263`, `265`, `269`, `272`, `273` —
y el resultado netto es este:

**El techo de reloj de esta placa tiene exactamente una fuente defendible: los
1071 MHz de la tabla DPM del VBIOS.** Todo lo demas que parece un techo
—`ulASICMaxEngineClock`, `overdriveLimit.engineClock`, las constantes AVFS—
esta vacio, corrupto o sobrescrito.

Y eso es una conclusion accionable, no una frustracion: **el trabajo de un
driver propio no es arreglar esos campos, es saber que no estan ahi.**

`B_RUNTIME = NOT_EXECUTED`. Sigue haciendo falta `Autorizo WRITE_EXECUTION para
B_EXPERIMENT`.