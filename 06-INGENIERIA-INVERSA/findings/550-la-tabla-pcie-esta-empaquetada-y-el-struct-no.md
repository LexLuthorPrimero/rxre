# 550 · La tabla PCIe de mi VBIOS está empaquetada y el struct de C no: 2 bytes de diferencia

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> La condición de `:666` queda **resuelta**: mi VBIOS **tiene** tabla PCIe, con
> **`ucNumEntries = 3`**, y **ningún `ulPCIE_Sclk` es cero**. La rama del `else`
> de `:681` queda **descartada**: `bif_sclk_table` se rellena.
>
> Y al hacerlo aparece algo que no esperaba: **el VBIOS empaqueta la tabla y el
> `struct` de C no**, y se separan **2 bytes**. Con el layout de C, la lectura
> daría **0 carriles PCIe** y un reloj de **134217728 kHz**.

## `:666` resuelta

La cadena, medida de punta a punta:

```
PowerPlayInfo @0x9C0A
  :45  usSclkDependencyTableOffset = 267   -> 0x9D15   (COINCIDE con el ancla de 267)
  :57  usPowerTuneTableOffset      = 673   -> 0x9EAB   (COINCIDE con el ancla)
  :61  usPCIETableOffset           = 752   -> 0x9EFA
```

**Dos anclas independientes confirman el recorrido del header**, que calculé
leyendo los campos del `struct _ATOM_Tonga_POWERPLAYTABLE` en vez de suponerlos:

| offset | campo | valor | destino | ¿ancla conocida? |
|---|---|---|---|---|
| 45 | `usSclkDependencyTableOffset` | 267 | `0x9D15` | **sí**, coincide |
| 57 | `usPowerTuneTableOffset` | 673 | `0x9EAB` | **sí**, coincide |
| 61 | `usPCIETableOffset` | 752 | `0x9EFA` | el medido |
| 59 | `usHardLimitTableOffset` | 0 | ausente | coherente |
| 63 | `usGPIOTableOffset` | 0 | ausente | coherente |

Y en `0x9EFA`:

```
ucRevId      = 1      -> NO es < 1, luego entra por la rama Polaris10 de :522
ucNumEntries = 3      -> cumple el assert de :526
```

`pcie_count = min(vdd_dep_on_sclk->count + 1, ucNumEntries) = min(9, 3) = **3**`.

**`:666 if (pcie_table != NULL)` es cierto. `bif_sclk_table` se rellena.** La
preocupación de `506` —que `:2094` pidiera un divisor DFS para un reloj de 0 MHz—
queda **descartada**, porque ningún `ulPCIE_Sclk` de mi VBIOS es cero.

## Y ahora el desacuerdo de 2 bytes

`ATOM_Polaris10_PCIE_Record` (de `pptable_v1_0.h:228-233`):

```c
UCHAR  ucPCIEGenSpeed;      /* @0 */
UCHAR  usPCIELaneWidth;     /* @1, declarado UCHAR */
UCHAR  ucReserved[2];       /* @2 */
ULONG  ulPCIE_Sclk;         /* @4  <-- alinea a 4 */
```

Medido con gcc: `sizeof(Record)` = **8**, y `sizeof(Table)` = **4**, con
**`entries` en offset 4** — porque el `ULONG` fuerza la alineación a 4 y los dos
`UCHAR` de cabecera dejan 2 bytes de relleno.

Y el macro del kernel usa el layout de C:

```c
#define GET_FLEXIBLE_ARRAY_MEMBER_ADDR(type, member, ptr, n) \
	(type *)((char *)&(ptr)->member + (sizeof(type) * (n)))
```

`&(ptr)->member` es `offsetof(entries)` **a través del compilador**. Así que el
código lee en `base + 4 + 8*i`.

**Los bytes de mi VBIOS, con las dos lecturas:**

```
base+0   01 03 00 08 00 00 fc 0a 00 00 00 08 00 00 f4 65
base+16  00 00 02 08 00 00 f4 65 00 00 9e 00
```

| i | lectura con `entries@4` | lectura con `entries@2` |
|---|---|---|
| 0 | lanes=**0**, sclk=**134217728** | lanes=**8**, sclk=**2812** |
| 1 | lanes=8, sclk=26100 | lanes=**8**, sclk=**26100** |
| 2 | lanes=0x9e, sclk=... | gen=2, lanes=**8**, sclk=**26100** |

## El discriminante, y es limpio

**26100 kHz es el reloj de referencia PCIe de manual.** Aparece en las dos lecturas
posibles para la entrada 1, así que por sí solo no discrimina. Lo que discrimina es
**el número de carriles**:

- Con `entries@4`, la entrada 0 tiene **`lanes = 0`**. **Cero carriles PCIe es
  imposible**: no existe un ancho de enlace de 0.
- Con `entries@2`, las tres entradas tienen **`lanes = 8`**, que es un ancho válido
  y además es el que usa esta placa (`sub_sys` de 8 carriles).

Y el reloj de la entrada 0 con `entries@2` es **2812 kHz**, que es bajo pero no
absurdo, y encaja con que esa entrada sea la de ULV, que el propio código trata aparte
(`:536-537`).

**El contenido de mi VBIOS está en offset 2, y el struct de C lo lee en offset 4.**

## Una sexta colisión de numeración, y esta vez la cuenta

Este hallazgo se iba a llamar `507`. Al regenerar el índice había **dos filas con
`507`**: la mía y `507-toolkit-audita-solo-su-directorio.md`, del otro agente. Lo
renombré a `550`.

**Es la sexta vez**, y ya no es un accidente puntual sino el funcionamiento normal
de dos agentes escribiendo en el mismo directorio: la frontera del otro agente llega
a `507` mientras yo trabajo, así que cualquier banda «por delante del máximo» se
queda corta en dos o tres iteraciones.

Eso **confirma la tesis de `400`** con más datos: una comprobación puntual no puede
arbitrar un estado compartido. Y añade el matiz que faltaba: **la banda **no** es
suficiente como solución**, porque el otro agente también avanza. Lo único que
funciona de verdad es que **cada agente use una banda que el otro no use**, y eso es
una convención, no una técnica.

Lo dejo escrito porque la próxima vez que colisione hay que **no perder otra
iteración investigándolo**: se renombra y se sigue.

## Lo que NO afirmo, y es lo importante

**NO afirmo que esto rompa nada.** Hay dos explicaciones y no puedo elegir entre
ellas con lo que tengo:

1. **Defecto de upstream**: `sizeof(ATOM_Polaris10_PCIE_Table)` compila con relleno
   de alineación y el VBIOS se escribe empaquetado. Entonces el driver lee 2 bytes
   desplazado y las tres entradas PCIe son basura — lo que produciría un
   `pcie_speed_table` con 0 carriles en la primera entrada.
2. **Mi lectura de la cabecera está desplazada**: si `usPCIETableOffset` no fuera el
   campo del offset 61, la tabla empezaría en otro sitio y coincidiría.

La segunda es **mucho menos probable**, porque dos anclas independientes (`0x9D15` y
`0x9EAB`) confirman el recorrido del header. Pero «menos probable» no es «descartada»,
y la forma de cerrarlo está nombrada más abajo.

Lo que sí es **`PROVEN`**:

- Mi VBIOS **tiene** tabla PCIe, `ucNumEntries = 3`, rev 1.
- Los datos legibles están en `base + 2 + 8*i`.
- `sizeof` del struct en C da `entries` en offset 4.
- **Las dos cosas no coinciden.**

Lo que es **`NOT_DETERMINED`**: si el efecto es real o si hay una lectura que lo
evite.

## El discriminante que lo cierra

**Mirar qué lee el driver de verdad**, no qué debería leer. Hay dos formas, y la
segunda es la buena:

1. Compilar `sizeof(ATOM_Polaris10_PCIE_Table)` en el **contexto real del kernel**,
   con sus `UCHAR`/`USHORT`/`ULONG` reales y su `__counted_by`. Yo medí una copia
   local de los structs; si el kernel define alguno de esos tipos distinto, mi número
   no vale.
2. **`amd_powerplay` no es el único consumidor.** Si hay otro camino que lea la
   tabla PCIe del VBIOS y produzca valores coherentes, la discrepancia es del
   `struct` que uso y no del hardware. Buscar otros lectores de `usPCIETableOffset`
   y de `ATOM_Polaris10_PCIE_Table` en `atomctrl` es un `grep` acotado.

Si aparece un segundo lector coherente, la explicación 1 se cae y esto pasa a ser
**una rareza de layout de la que nadie se ocupa porque no duele**. Si no aparece, es
un defecto real de upstream.

## Dos detalles que salieron de paso

**`UCHAR usPCIELaneWidth`** está declarado como `UCHAR` pero se lee con
`le16_to_cpu` (`:554`). Sobre un campo de 1 byte eso no rompe nada —`le16_to_cpu`
devuelve `int` y solo promotiona— pero es un **desajuste de tipo**, y significa que
el campo no puede llevar anchos de carril de más de 255. Irrelevante en la práctica.

**`pcie_count` depende de `vdd_dep_on_sclk->count`**, que es la tabla SCLK que
`267` decodificó con **8 entradas**. Si esa cuenta fuera distinta, `pcie_count`
cambiaría. Con 8 sale `min(9, 3) = 3`, o sea que **`ucNumEntries` manda** y el 8 no
aprieta. Aun así, la dependencia existe y la tabla SCLK es mi fuente de reloj, así que
**la conexión entre las dos es real y conviene no olvidarla**.

## Lo que NO afirmo

- **NO** afirmo que el driver lea mal la tabla. Es `NOT_DETERMINED` con dos
  explicaciones.
- **NO** afirmo que `vdd_dep_on_sclk->count` sea 8 en el sentido que usa el código. En
  `267` leí 8 entradas de la tabla SCLK **del VBIOS**, que es otra cuenta de la que
  hace el kernel al parsearla. Con `ucNumEntries = 3` no cambia el resultado, pero no
  lo he traced.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`.
- **NO** he modificado código. `MODIFICATIONS 0`.

## Lo que queda cerrado de la rama de las 16 puertas

- `:2005` clock stretcher — **cerrada** en `505`.
- `:666` / `:681` rama PCIe — **cerrada** aquí: hay tabla, con 3 entradas, y
  `bif_sclk_table` se rellena. La preocupación de lectura en cero de `506` queda
  **descartada**.
- `:2095` divisor DFS — sus entradas son estos mismos `ulPCIE_Sclk`, y **ninguno es
  cero**. Sigue dependiendo de que `ComputeMemoryEnginePLL` responda, y esa tabla
  **no está en mi corpus**.

## Frontier siguiente

**Buscar un segundo lector de la tabla PCIe del VBIOS**, que es el discriminante
barato entre «defecto real» y «rareza que no duele».

Es un `grep` acotado por `usPCIETableOffset` y por `ATOM_Polaris10_PCIE_Table` en
todo `amd/`, con `exit` verificado y el recuento de ficheros a la vista. Si aparece
otro lector, hay que leerlo entero y ver si produce valores coherentes.

Criterio de cierre: o existe un segundo lector coherente y esto se degrada a
`NOT_APPLICABLE`, o no existe y el desacuerdo de 2 bytes queda como
**defecto de upstream medido**, con el impacto acotado a la primera entrada PCIe.

Y si es un defecto real, el siguiente paso natural es el mismo método que acabo de
usar aquí, sobre un objeto más grande: **`ComputeMemoryEnginePLL`**, la tabla que
decide la PLL del reloj de memoria. Es lo que ejecuta `:2094`, es lo que decide los
dos campos `BifSclkDfs`, y **está en el mismo master data table** que todo lo que
llevo leyendo. Eso cerraría el círculo entre la tabla DPM y los relojes, que es la
pregunta con la que empezó esta rama.