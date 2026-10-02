# 097 · El memset que falta en dos de cinco: el defecto es intermitente, no una progresion

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## La pregunta

`096` encontro que en `polaris10_smumgr.c:1494` la tabla de arbitraje DRAM se declara
sin inicializar y se copia a tamano completo. Barri el patron con `uninit_copy` y salio
tambien en `fiji_smumgr.c:1528`.

La pregunta que importa para un driver propio no es "donde falla", sino **si es una
tendencia o un accidente**. Si es una tendencia, el modelo mental correcto es "las
generaciones nuevas lo hacen mal". Si es un accidente, el modelo correcto es "esta
copia concreta esta mal y hay que comprobar cada una".

## La respuesta: accidente

Las cinco rutas de la familia SMU7 hacen **exactamente la misma operacion** con la
misma forma de codigo. Y tres de las cinco se defienden:

| fichero | SMU | declaracion | `memset` | linea del `memset` |
|---|---|---|---:|---:|
| `tonga_smumgr.c` | 7.2 | `SMU72_... arb_regs;` | **si** | `1495` |
| `iceland_smumgr.c` | 7.1 | `SMU71_... arb_regs;` | **si** | `1619` |
| `vegam_smumgr.c` | 7.5 | `SMU75_... arb_regs;` | **si** | `1285` |
| `fiji_smumgr.c` | 7.3 | `struct SMU73_... arb_regs;` | **NO** | — |
| `polaris10_smumgr.c` | 7.4 | `struct SMU74_... arb_regs;` | **NO** | — |

El `memset` va **siempre antes** del bucle doble, en las tres que lo tienen:

```c
/* tonga_smumgr.c:1492-1497 */
SMU72_Discrete_MCArbDramTimingTable  arb_regs;
uint32_t i, j;

memset(&arb_regs, 0x00, sizeof(SMU72_Discrete_MCArbDramTimingTable));

for (i = 0; i < data->dpm_table.sclk_table.count; i++) {
```

Idéntico en `iceland_smumgr.c:1616-1621` y en `vegam_smumgr.c:1285-1287`.

**La secuencia por generacion es: presente (7.2), presente (7.1), ausente (7.3),
ausente (7.4), presente (7.5).** No es una degradacion: se pierde en Fiji, se pierde
en Polaris, y VegaM lo recupera. Un defecto que aparece y se corrige solo en la
generacion siguiente no es una tendencia del lenguaje ni del equipo: es un descuido
puntual en dos ficheros concretos, corregido sin que nadie lo documentara.

## Por que el `memset` importa mas aqui que en otros sitios

Porque con `memset` la copia a tamano completo es **correcta por construccion**. Las
entradas no barridas quedan en cero, que es un valor definido y que el firmware puede
leer como "este par de frecuencias no tiene temporizacion especial". Sin `memset`, esas
mismas entradas llevan **contenido residual de pila**, que es un valor indefinido que no
distingue "cero" de "basura" en ninguna parte del sistema.

Asi que la unica diferencia entre las cinco implementaciones es si la parte no escrita
de la tabla es **cero** o es **basura**. Y las dos se copian de 384 bytes (640 en
VegaM).

## Los cuatro tamaños, cruzados con gcc

No.sumados de memoria. Compilados:

```
SMU71_Discrete_MCArbDramTimingTable   gcc = 384   modelo = 384   COINCIDE   (iceland)
SMU72_Discrete_MCArbDramTimingTable   gcc = 384   modelo = 384   COINCIDE   (tonga)
SMU73_Discrete_MCArbDramTimingTable   gcc = 384   modelo = 384   COINCIDE   (fiji)
SMU74_Discrete_MCArbDramTimingTable   gcc = 384   modelo = 384   COINCIDE   (polaris10)
SMU75_Discrete_MCArbDramTimingTable   gcc = 640   modelo = 640   COINCIDE   (vegam)
```

**VegaM son 640, no 384, y la causa no es la matriz.** La matriz es la misma: `entries
[SMU__NUM_SCLK_DPM_STATE][SMU__NUM_MCLK_DPM_LEVELS]` con 8 y 4 tambien en
`smu75_discrete.h:192`, y `SMU__NUM_SCLK_DPM_STATE` sigue valiendo 8 en `smu75.h:40`.

Lo que cambia es **la entrada**: en SMU 7.5 `McArbBurstTime` es `uint32_t` y hay dos
campos mas, `McArbRfshRate` y `McArbMisc3` (`smu75_discrete.h:181-187`):

```
SMU74: uint32 McArbDramTiming; uint32 McArbDramTiming2;
       uint8  McArbBurstTime;   uint8  padding[3];        = 12 B

SMU75: uint32 McArbDramTiming; uint32 McArbDramTiming2;
       uint32 McArbBurstTime;   uint32 McArbRfshRate;
       uint32 McArbMisc3;                                 = 20 B
```

8 x 4 x 12 = 384 en SMU 7.4; 8 x 4 x 20 = **640** en SMU 7.5.

Esto importa mas de lo que parece. En SMU 7.4 el `padding[3]` **declarado** y los tres
bytes que el host no escribe coinciden en numero por casualidad: son 3 bytes sin
escribir y 3 bytes declarados. En SMU 7.5 **no hay `padding`**, porque los tres campos
que anadian son precisamente los que antes quedaban a cero. El contrato paso de
"rellena lo que puedas y el resto es relleno" a "rellena cinco campos obligatorios".

Una version anterior de este parrafo decia que la matriz de VegaM era de 10 x 4. Es
falso, y lo corrijo aqui porque el numero habria misleadado: una tabla mas grande no
sale de mas filas, sale de **mas campos por entrada**, que es un cambio de hardware, no
de configuracion.

Tambien note que **Fiji escribe un cuarto campo que Polaris12 no escribe**:
`fiji_smumgr.c:1518` pone `arb_regs->TRRDS`, y no existe equivalente en la struct de
Polaris12 (`smu74_discrete.h:169-174`, que solo tiene `McArbDramTiming`,
`McArbDramTiming2`, `McArbBurstTime` y `padding[3]`). El hardware cambio, y con el
hardware cambio el contrato. Eso es `PROVEN` y explica por que las dos rutas no son
intercambiables aunque la forma del codigo sea identica.

## Que NO sigue de aqui

No sigue que el resto de tablas de las cinco rutas tengan el mismo problema. El barrido
encontró **24 copias con `sizeof()` y contador de bucle en la misma funcion**, y solo
dos son de este tipo. Las otras 22 son de otra naturaleza: tablas cuyo productor
recorre un numero distinto de elementos que los que declara su array. Esa generalizacion
la dejo abierta y es trabajo de otro sitio, no una afirmacion de este documento.

No sigue que en esta placa el defecto se manifieste. Sigue necesitando el valor de
`sclk_table.count` y `mclk_table.count`, que es `RUNTIME_MISSING` (dato del PPT).

No sigue que el firmware lea las entradas no barridas. Si selecciona por indice de
nivel y solo hay combinaciones validas, las entradas sucias podrian no leerse nunca.
Eso es `NOT_IN_CORPUS`.

## Clasificacion

- `SMC_ARB_MEMSET_PRESENT_TONGA = PROVEN`: `tonga_smumgr.c:1495`, antes del bucle.
- `SMC_ARB_MEMSET_PRESENT_ICELAND = PROVEN`: `iceland_smumgr.c:1619`, antes del bucle.
- `SMC_ARB_MEMSET_PRESENT_VEGAM = PROVEN`: `vegam_smumgr.c:1285`, antes del bucle.
- `SMC_ARB_MEMSET_ABSENT_FIJI = PROVEN_ABSENT`: `fiji_smumgr.c:1528`, sin memset ni
  inicializador. Buscado por nombre exacto de `memset(&arb_regs`.
- `SMC_ARB_MEMSET_ABSENT_POLARIS12 = PROVEN_ABSENT`: `polaris10_smumgr.c:1494`, igual.
- `SMC_ARB_DEFECT_IS_INTERMITTENT = PROVEN`: presente en 7.1 y 7.2, ausente en 7.3 y
  7.4, presente en 7.5. **No es una progresion generacional.**
- `SMC_ARB_SIZES_MEASURED = PROVEN_DERIVED`: 384, 384, 384, 384, 640, los cinco por
  gcc, no por suma.
- `SMC75_ARB_ENTRY_IS_20_BYTES = PROVEN_DERIVED`: cinco `uint32_t` sin relleno
  (`smu75_discrete.h:181-187`), frente a los dos `uint32_t` mas `uint8_t`+`padding[3]`
  de SMU 7.4 (`smu74_discrete.h:169-174`). 8 x 4 x 20 = 640. **La matriz es la misma
  en las dos** (`smu75.h:40` sigue valiendo 8). Una version anterior de este documento
  decia matriz 10 x 4: falso.
- `SMC73_HAS_TRRDS_FIELD = PROVEN`: `fiji_smumgr.c:1518` escribe `TRRDS`, que no existe
  en `SMU74_Discrete_MCArbDramTimingTableEntry`.

## Lo que esto obliga a hacer en un driver propio

Una sola vez, en el sitio unico por donde pasan todas las tablas de la SMC: **poner a
cero el destino antes de escribir una fraccion de el**. Si la copia va a tamano
completo, el relleno a cero no es opcional; es la unica cosa que convierte "bytes no
escritos" en "bytes definidos".

Y no confiar en que el compilador o el ABI lo hagan por uno: esto es C, la variable es
de pila, y el estandar no garantiza nada sobre ella. El `memset` de Tonga e Iceland es
codigo escrito a mano, no algo que el lenguaje imponga.
