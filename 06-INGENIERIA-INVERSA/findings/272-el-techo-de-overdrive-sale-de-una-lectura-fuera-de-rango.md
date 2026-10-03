# 272 · El techo de overdrive de mi placa sale de una lectura fuera de rango: 2952790445

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## El hallazgo
>
> `init_overdrive_limits_V2_1` lee `overdriveLimit.engineClock` a traves de un
> offset **no validado**, y en mi VBIOS ese offset cae **fuera de la tabla**.
> El valor que el driver computa es **2952790445**, que no es un techo de reloj.
> No hay crash, porque el offset cae dentro del fichero de ROM: hay un
> numero, y el numero es basura.

## La cadena, medida paso a paso

**1. Que version de FirmwareInfo corre en mi placa.** Con gcc sobre `atombios.h`:

```
sizeof(ATOM_FIRMWARE_INFO_V1_4) = 89
sizeof(ATOM_FIRMWARE_INFO_V2_1) = 92
mi usStructureSize              = 108
```

`processpptables.c:1194` exige `ucTableFormatRevision == 2 &&
usStructureSize >= sizeof(V2_1)`. Mi tabla es rev 2.2 con 108: **corre
`init_overdrive_limits_V2_1`, y NO la V1_4.**

Esto **descarta dos alarmed que yo mismo me habia hecho**: el bug de
`:1123-1127` (`maxOverdriveVDDC` sobrescrito con el mismo valor que el minimo)
**no me afecta**, porque esa funcion no corre. Y `ulASICMaxEngineClock = 0` es
**inerte** en mi placa, porque la V2_1 no lee ese campo.

**2. Lo que hace la V2_1** (`processpptables.c:1133-1161`):

```c
1140  if (le16_to_cpu(powerplay_table->usTableSize) < sizeof(ATOM_PPLIB_POWERPLAYTABLE3))
1142      return 0;
1146  if (0 == powerplay_table3->usExtendenedHeaderOffset)
1147      return 0;
1149  header = (ATOM_PPLIB_EXTENDEDHEADER *)(((unsigned long)powerplay_table) +
1150          le16_to_cpu(powerplay_table3->usExtendendedHeaderOffset));
1152  overdriveLimit.engineClock = le32_to_cpu(header->ulMaxEngineClock);
1153  overdriveLimit.memoryClock = le32_to_cpu(header->ulMaxMemoryClock);
1156  minOverdriveVDDC = 0;
1157  maxOverdriveVDDC = 0;
```

**Los dos guardas pasan y no protege el tercero.** Comprueba que `usTableSize`
sea suficiente y que el offset no sea cero, pero **no comprueba que el offset
esté dentro de la tabla**.

**3. Los offsets, con gcc sobre `pptable.h`:**

| simbolo | offset |
|---|---:|
| `offsetof(ATOM_PPLIB_POWERPLAYTABLE, usTableSize)` | 19 |
| `offsetof(ATOM_PPLIB_POWERPLAYTABLE3, usExtendendedHeaderOffset)` | 44 |
| `offsetof(ATOM_PPLIB_EXTENDEDHEADER, ulMaxEngineClock)` | 2 |
| `offsetof(ATOM_PPLIB_EXTENDEDHEADER, ulMaxMemoryClock)` | 6 |
| `sizeof(ATOM_PPLIB_POWERPLAYTABLE3)` | 46 |
| `sizeof(ATOM_PPLIB_EXTENDEDHEADER)` | 26 |

**4. La tabla de mi VBIOS.** `atomrom.py tablas` la da con nombre y tamano:
`PowerPlayInfo 0x9c0a size=778 rev=7.1`. Y la cabecera **cuadra byte a byte**:

```
sHeader.usStructureSize  = 778    OK   (coincide con atomrom)
sHeader.ucFormatRevision = 7
sHeader.ucContentRevision= 1
```

**5. Los campos posteriores NO cuadran**, y ahi esta el fallo:

```
usTableSize             (offset 19) = 32768     guarda :1140 (>=46) PASA
usExtendendedHeaderOffset(offset 44) = 2817     guarda :1146 (!=0)  PASA
```

`2817` es un offset **dentro de una tabla de 778**. La cabecera extendida
caeria en `0x9C0A + 2817 = 0xA70B`, **7841 bytes mas alla** del final de la
tabla (`0x9F14`).

Lo que el driver lee ahi:

```
:1152  overdriveLimit.engineClock = 2952790445
:1153  overdriveLimit.memoryClock = 429
```

Y como `0xA70B < 0xE600` (tamano del fichero), **la lectura es legal en RAM**:
no hay segfault, no hay assert, no hay aviso. Solo un numero imposible.

## Por que los offsets no cuadran

`usTableSize` a offset 19 vale 32768, y el campo esta declarado en
`pptable.h:197` con el comentario *"the size of this structure, or the extended
structure"*. Un valor de 32768 en una tabla de 778 no es un tamano.

La explicacion mas economica: **el cast a `ATOM_PPLIB_POWERPLAYTABLE3` asume
un layout que mi revision de tabla (7.1) no tiene.** El codigo nunca lee
`ucFormatRevision` de esta tabla para decidir el layout; lo que usa es
`usStructureSize`, y ese campo esta en una posicion que mi ROM no comparte.

**Estado: `PROVEN_DERIVED`.** Que el offset este equivocado, es `PROVEN`. Que la
causa sea un desajuste de revision, es la explicacion que encaja pero no la unica
posible.

## Que significa para el proyecto

**El techo de overdrive de reloj de mi placa no es un numero.** El campo vale
`2952790445`, o sea unos 2,95 GHz si se dividiera por 100, o 2,95 GHz si se
tomara como 10 kHz. Ninguna de las dos lecturas es defendible, y el codigo no
tiene forma de saberlo.

Consecuencias concretas:

- **La ruta B de overdrive de `127` tiene el techo corrupto.** No es que no
  exista: es que vale basura. Un driver propio **no puede confiar en
  `overdriveLimit.engineClock`** tal como lo deja el codigo actual, porque no
  distingue "sin limite" de "limite leido de basura".
- **`overdriveLimit.memoryClock = 429`** esta en la misma situacion.
- **`minOverdriveVDDC = maxOverdriveVDDC = 0`** (`:1156-1157`) es **deliberado y
  correcto para esta version**: el overdrive de voltaje esta apagado por
  construccion, no por un fallo de mi VBIOS. Eso si es un dato firme.
- El techo de reloj que **si** es real sigue siendo el de la tabla DPM:
  **1071 MHz**, con las reservas de `134`, `267` y `269`.

## Lo que NO afirmo

- **NO** afirmo que `overdriveLimit.engineClock` se use tal cual para limitar
  el reloj. Habria que seguir a quien lo consume; no lo he hecho.
- **NO** afirmo que la lectura sea fuera de rango de memoria: es legal en el
  fichero, asi que el efecto es un numero basura, no una caida.
- **NO** he medido nada en la GPU. `B_RUNTIME = NOT_EXECUTED`.
- **NO** he tocado el VBIOS ni el firmware.
- No afirmo que el valor correcto de `ulMaxEngineClock` sea 1071 MHz. Esa es la
  tabla DPM, que es otra tabla.

## Correccion de alcance

`269` decia que "`ulASICMaxEngineClock = 0` no lo respalda nadie". **Eso era
parcialmente falso y lo corrijo aqui**: si lo lee `init_overdrive_limits_V1_4`,
que **no corre en mi placa**, porque `sizeof(V2_1) = 92` y mi
`usStructureSize = 108` con `ucTableFormatRevision = 2` mandan a la V2_1. En mi
placa el campo no lo lee nadie. En placas con FirmwareInfo rev 1 si se leeria, y
alli un 0 **si** significaria techo cero.

## Estado epistemico que cambia

La cadena de techo de reloj, completa y con su parte rota a la vista:

| fuente | valor | estado |
|---|---|---|
| tabla DPM `ulSclk` max | 1071 MHz | `PROVEN` (`267`) |
| `MinVoltage` del nivel max | 0 | `PROVEN` (`267`) |
| VoltageObjectInfo | sin rellenar | `PROVEN_DERIVED` (`134`) |
| `ulASICMaxEngineClock` | 0 | `PROVEN`, pero **nadie lo lee en mi placa** |
| `overdriveLimit.engineClock` | **2952790445** | **`PROVEN`, y es basura** |
| `overdriveLimit.memoryClock` | **429** | **`PROVEN`, y es basura** |
| overdrive de voltaje | apagado (0..0) | `PROVEN`, correcto por diseno |

**El unico techo de reloj defendible en todo el sistema es 1071 MHz.** Y la unica
via para pasarlo es la de un driver propio, porque la ruta del driver actual
tiene el techo corrupto.

## El metodo, que es lo que mas me importa aqui

Tres cosas que hice mal y como las caught:

1. **`head -20` en un `grep` de consumidores**: casi publico "cero
   consumidores de `ulASICMaxEngineClock`". Truncar una lista es inventar una
   ausencia.
2. **`grep -rl` con timeout dio 0 ficheros**: un cero por tiempo agotado. Ese 0
   no era informacion.
3. **Ancla `0x9C0A` asumida como el tipo que yo queria**: me dio
   `ulMaxEngineClock = 2952790445` en la primera lectura, antes de tener el
   contexto. Lo sanee como basura en vez de publicarlo, y al sanearlo bien
   resulto ser **el hallazgo**.

Un numero absurdo es una senal. Un numero *plausible* en la posicion
equivocada habria sido el peligro real.

## Herramienta nueva: `atombios.h` compila

`gccverify` estaba bloqueado por cabeceras de kernel generadas. **`atombios.h`
si compila** con tres cosas:

```
-DATOM_BIG_ENDIAN=0      la puerta de endianness de atombios.h:39
typedefs UCHAR/USHORT/ULONG/CHAR/INT/BOOL
#define __counted_by(x)   vacio, gcc no lo conoce
```

Con eso gcc mide **cualquier struct ATOM del VBIOS**. En esta iteracion produjo:
`sizeof(FIRMWARE_INFO_V1_4)=89`, `sizeof(FIRMWARE_INFO_V2_1)=92`,
`offsetof(PPLIB3, usExtendenedHeaderOffset)=44`,
`offsetof(EXTENDEDHEADER, ulMaxEngineClock)=2`,
`sizeof(PPLIB3)=46`, `sizeof(ATOM_PPLIB_POWERPLAYTABLE)=37`.

Estado de la capacidad: **`VALIDATED`**, con la limitacion de que define los
tipos a mano y eso **no** cubre las cabeceras de kernel, que siguen bloqueadas.

## Frontier siguiente, y es la unica que importa

Determinar si el layout correcto de `ATOM_PPLIB_POWERPLAYTABLE3` para la
revision 7.1 existe en el corpus con otro nombre, o si la conversion sin
comprobacion es simplemente un bug de AMD que sobrevivio porque las placas que
lo ejecutan tienen otro layout.

Discriminante: `atombios.h` declara el campo como `USHORT
usExtendendedHeaderOffset` en `pptable.h:220`. Si hay una version versionada por
revision en `atomfirmware.h` o en `pptable.h`, ahi estara. Si **no** la hay, el
defecto es del driver y mi lectura es correcta.

Es lectura estatica pura, y decide si esto es "mi VBIOS es raro" o "el driver
lee basura en general". La diferencia importa: la primera es un dato de esta
placa, la segunda es un defecto de amdgpu que aplica a toda la familia.

`B_RUNTIME = NOT_EXECUTED`. Sigue haciendo falta `Autorizo WRITE_EXECUTION para
B_EXPERIMENT`.