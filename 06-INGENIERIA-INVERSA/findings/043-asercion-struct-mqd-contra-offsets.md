# 043 · El driver tiene una aserción sobre el hardware que nunca se comprobó, y se cumple

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/mqd_layout.py` (`TOOL_VALIDATED`)
`CONTINUES=042` · `CORRIGE=el "64 registros sin mirar" de 042, que era un`
`artefacto de la extraccion y no una frontera real`

## Cuestión principal

¿Existe en el driver alguna afirmación sobre el **mapa de registros** que se
pueda verificar mecánicamente contra el header de offsets, y no solo leer?

## Criterio de terminación

O bien se localiza tal aserción y se verifica campo a campo, o bien se
documenta que no existe. Alcance: `struct vi_mqd` × `gfx_8_0_d.h` ×
`gfx_v8_0.c:4559-4579`. **Cumplido: la aserción existe y se cumple en 52 de 53
posiciones.**

## Resultado

Existe. `gfx_v8_0.c` programa la cola así:

```c
mqd_data = &mqd->cp_mqd_base_addr_lo;
for (mqd_reg = mmCP_HQD_VMID; mqd_reg <= mmCP_HQD_EOP_CONTROL; mqd_reg++)
        WREG32(mqd_reg, mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]);
```

`mqd_data` es un puntero a un campo `uint32_t` **dentro de una struct**, y se
indexa con `offset_de_registro − offset_base`. Eso **afirma**, sin decirlo y
sin comprobarlo nunca en runtime, cuatro cosas sobre el hardware:

```
A. el bloque HQD es CONTIGUO, sin huecos entre offsets
B. cada registro del bloque ocupa exactamente UN dword
C. el orden de los campos del struct replica el orden de los offsets
D. no hay campos de otro ancho (uint64_t, arrays) en medio
```

Si **D** fuera falso, `mqd_data[i]` leería memoria equivocada y el driver
programaría cada registro con el valor del campo de al lado. El compilador no
avisa: los índices son válidos, solo wrong. Es un fallo **latente**, sin error
de compilación y sin crash.

## Verificación

`mqd_layout.py` cruza las tres fuentes y evalúa las cuatro afirmaciones:

```
indices programados               : 53
cuadran (MATCH)                   : 49
cuadran con ALIAS en el header    : 3
nombre DIVERGENTE (posición ok)   : 1
MISMATCH (posición ambigua)       : 0
offsets SIN registro definido     : 0
campos array                      : 0
campos de otro tipo que no uint32 : 0
bloque verificado                 : 0x3245..0x3279  (53 dwords)
```

**PROVEN por verificación mecánica, sobre las 53 posiciones que el driver
escribe.** A, B, C y D se cumplen.

Y el bloque verificado `0x3245..0x3279` coincide **exactamente** con el
comentario del propio driver:

```c
/* HQD registers extend from mmCP_MQD_BASE_ADDR to mmCP_HQD_ERROR */   /* :4552 */
```

Es decir: una frase que el driver **declaraba** desde hace años queda
**confirmada** contra el header de offsets. Con una diferencia: el driver
programa un registro más allá de `CP_HQD_ERROR`, el `EOP_WPTR_MEM` de
`0x3279`, porque lo escribe suelto por la errata de Tonga. El comentario se
queda corto por un registro.

## Lo que esto cambia sobre 042

`042` decisiva: de "64 registros que el camino alcanza y ningún hallazgo
menciona" a una lista cerrada de 53 con su offset y su campo. Ese número era
**un artefacto de la extracción**, no una frontera
de conocimiento: `causal_chain.py` no expande los bucles de registro, así que
de `0x3245..0x3279` solo veía los escritos con nombre literal (6 de 53) y
contaba el resto como "no mirados".

Ahora están los 53, con su offset, su campo de struct, su registro y su
procedencia. El `causal_chain` señaló el sitio sin entenderlo; una herramienta
de la categoría "verificar" lo resolvió. Ese es el reparto correcto del trabajo
entre herramientas: una descubre, otra decide si lo descubierto es un problema.

## Tres alias de hardware

Tres offsets tienen **dos nombres** en el header:

| offset | nombres | el struct usa |
|---|---|---|
| `0x325e` | `CP_HQD_DMA_OFFLOAD` / `CP_HQD_OFFLOAD` | `cp_hqd_dma_offload` |
| `0x3265` | `CP_HQD_HQ_SCHEDULER0` / `CP_HQD_HQ_STATUS0` | `cp_hqd_hq_status0` |
| `0x3266` | `CP_HQD_HQ_CONTROL0` / `CP_HQD_HQ_SCHEDULER1` | `cp_hqd_hq_control0` |

Es **aliasing de hardware**, no un error del header: el mismo dword tiene dos
nombres según la generación de IP que lo describiera. La tabla del proyecto
debe llevar los dos, porque un nombre sin su gemelo induce a error al buscar
en otro ASIC. `065` ya había encontrado 7 casos equivalentes en GMC; aquí hay
3 más, y son de otro bloque.

Lo que **no** se puede afirmar es si los dos nombres significan lo mismo: que
el header los declare juntos prueba que AMD los considera la misma
dirección, no que la semántica sea idéntica en ambas generaciones.

## Una divergencia de nombre, no de posición

```
i=42  0x326f:  el struct lo llama cp_hqd_eop_done_events
                el header llama     mmCP_HQD_EOP_EVENTS
```

El offset es el mismo y es el único registro en esa posición, así que la
correspondencia por posición es correcta. Difieren dos palabras.

No es un descuido del driver: `cp_hqd_eop_done_events` aparece con ese nombre
en las **cinco** generaciones del struct (`vi`, `v9`, `v10`, `v11`, `v12`), y
el código de GFX8 lo rellena leyendo `mmCP_HQD_EOP_EVENTS`
(`gfx_v8_0.c:4528`). El struct es coherente consigo mismo; el header usa otra
palabra para lo mismo.

Clasificar esto como `MISMATCH` habría sido un falso positivo de gravedad
injusta. La herramienta lo separa como `NOMBRE_DIVERGENTE` y **no cuenta como
fallo**, porque el fallo de una aserción estructural es un desajuste de
posición, no de vocabulario.

## El bloque crece con la generación

```
gfx_7_0: registros CP_HQD_EOP = 0    (el bloque no tiene EOP)
gfx_8_0: registros CP_HQD_EOP = 8    mmCP_HQD_ERROR = 0x3278
gfx_8_1: registros CP_HQD_EOP = 8    mmCP_HQD_ERROR = 0x3278
```

GFX7 no tiene EOP; GFX8 sí, y añade 8 registros al final del bloque. Para
Polaris12 el bloque **sí** tiene EOP, y el driver lo usa. Esto es
`CORROBORATION` de que `EOP_*` es una extensión de GCN1→GCN3, no un concepto
que existiera siempre. La semántica sigue siendo `NOT_DETERMINED`.

## Dos falsos positivos que la herramienta dio, y por qué

Una herramienta que llora lobo entrena a su usuario a ignorar sus hallazgos,
que es peor que no tenerla. Los dos errores que cometí:

**1. Comparar nombres sin normalizar.** El struct llama
`cp_hqd_pq_base_lo` a un registro que el header llama `mmCP_HQD_PQ_BASE`
(registro de 64 bits partido en dos dwords de 32). Sin quitar el sufijo, la
primera versión reportó **26 MISMATCH**, todos falsos. Resultado: alarming
`"LA ASERCION DEL DRIVER NO SE CUMPLE"` sobre código que funciona.

Corregido con dos candidatos por campo: el nombre tal cual, y el nombre sin
`_lo`/`_hi`. Porque hay registros que **sí** se llaman `_HI` en el header
(`mmCP_MQD_BASE_ADDR_HI`), y esa corrección sola creataba 13 falsos positivos
más. La respuesta correcta es aceptar ambos.

**2. Comparar los 257 campos del struct contra los 2633 registros.** El
struct es mucho más grande que el bloque HQD: incluye el estado de dispatch de
compute y graphics, que se programan campo a campo, no por offset. Evaluar
todo daba `MISMATCH` en casi todo.

Corregido evaluando **solo los índices que el driver programa**, derivados de
los bucles del propio `.c`, no de un rango supuesto.

Ninguno de los dos lo detectó el self-test: los controles existen para detectar
errores de lógica, y estos eran de **especificación de la comparación**. Por
eso el self-test se escribe *después* de la herramienta y contra ella.

## El control negativo que falló, y por quéImporta más que los dos anteriores

El control 4 borraba `mmCP_HQD_EOP_CONTROL` del header esperando ver un
`SIN_REGISTRO`. No lo vio: **0 → 0**.

Causa: ese registro es la **cota superior** del primer bucle. Al desaparecer
del header, el bucle ya no se puede resolver, sus índices pasan a
`NO_PROGRAMADO`, y el total programados cae de 53 a 16.

Es comportamiento **correcto**: si la herramienta no sabe dónde acaba el
bloque, no debe inventar un hueco dentro de él. Un detector que dijera "aquí
falta un registro" cuando en realidad no sabe los límites del bloque sería un
generador de falsos positivos.

Pero el control no discriminaba. Dos arreglos:

1. El control 4 elige ahora una víctima que **está dentro** de un rango y no
   es ninguna cota. Detecta `0 → 1`.
2. El control 4b **exige** el comportamiento correcto: al borrar una cota,
   los programados bajan y `SIN_REGISTRO` sigue en 0.

Convertir un fallo del control en un requisito explícito es más útil que
relajar el control hasta que pase.

## Clasificación

| afirmación | estado |
|---|---|
| El driver indexa `struct vi_mqd` por offset de registro | `PROVEN` — `gfx_v8_0.c:4553,4560` |
| El bloque HQD es contiguo, sin huecos | `PROVEN` — 53/53, sin `SIN_REGISTRO` |
| Cada registro ocupa un dword | `PROVEN` — 0 arrays, 0 tipos distintos de 32 bits |
| El orden del struct replica el de los offsets | `PROVEN` — 52/53 por posición |
| El bloque va de `0x3245` a `0x3279` | `PROVEN` — derivado de los bucles |
| El comentario del driver describe el bloque | `PROVEN` — y se queda corto en 1 registro |
| 3 offsets tienen alias en el header | `PROVEN` — tabla de §3 |
| Que los alias signifiquen lo mismo | `NOT_DETERMINED` — el header los declara juntos |
| `0x326f` se llama de dos formas | `PROVEN` — divergencia de nombre, posición correcta |
| Que hace cada uno de los 53 registros | `NOT_DETERMINED` — 033: no hay spec de GCN3 |

## Confounders

- **El header no es el hardware.** Que `gfx_8_0_d.h` sea coherente demuestra
  coherencia del header, no la geometría física del bloque. El argumento es
  más fuerte que "el driver acierta" pero más débil que "el hardware es así".
- **Sólo `mqd_commit` de `gfx_v8_0.c`.** `gfx_v7_0.c` tiene el mismo patrón
  (`:2951`, `:2955`) y no se ha verificado. Es el siguiente paso obvious.
- **Sólo GFX8.** `gfx_8_1` da el mismo 49/1, así que la conclusión aguanta
  para la familia 8_0/8_1, que incluye Polaris12. GFX9 en adelante usa otras
  cabeceras y no se ha comprobado.
- **53 de 257 campos.** El resto del struct (dispatch de compute/graphics) se
  programa campo a campo. Si ese camino también indexa por offset en otro
  sitio, este mismo método se aplica. No comprobado.
- **Regex, no AST.** La extracción de bucles es textual. Una llamada
  repartida en varias líneas podría escaparse. El recuento de 3 bucles
  coincide con la lectura manual del fichero, pero no es una garantía de que
  no haya un cuarto.

## Desfalsificación

- **(a)** El struct no cuadra porque haya un hueco real → refutable con
  `--mismatches`; sale 0 huecos.
- **(b)** El parseo del struct inventa campos → refutable contando a mano los
  campos de `vi_structs.h:159-415`; son 257 y el ancla es el 128.
- **(c)** El índice `mqd_data` no es lo que creo → refutable leyendo
  `gfx_v8_0.c:4553`; `mqd_data = &mqd->cp_mqd_base_addr_lo`, sobre un
  `uint32_t *`, y `vi_structs.h:159` declara `struct vi_mqd` con todos sus
  campos `uint32_t`.
- **(d)** Los bucles no son los que creo → refutable con `--ranges`, que los
  extrae del `.c` y no de una lista a mano.
- **(e)** Los alias son un error de parseo → refutable con `grep` directo en
  `gfx_8_0_d.h:655-666`, donde los pares están en líneas contiguas.

## UNLOCKS

- **La geometría del bloque de cola de Polaris12 queda cerrada**: 53 dwords
  contiguos, `0x3245..0x3279`, cada uno mapeado a su campo de struct. Es lo
  que hay que replicar para arrancar una cola en un driver propio.
- **`042` queda cerrado**: los "64 registros sin mirar" no eran una frontera,
  eran un agujero de la extracción. Corregido.
- **El método es reutilizable tal cual**: cualquier struct indexada por offset
  de registro es una aserción verificable sobre el hardware. `vi_mqd`,
  `si_mqd` y `v9_mqd` de `amdgpu` tienen la misma forma.
- **La divergencia de nombre está explicada** en lugar de reportada como bug.

## Evidencia

```
HERRAMIENTA
  08-ARQUITECTURA/tools/mqd_layout.py   TOOL_VALIDATED (9 controles)
    cuadran 52/53   mismatch 0   huecos 0   arrays 0   tipos_malos 0
    bloque 0x3245..0x3279 = 53 dwords
    3 alias de hardware
    1 divergencia de nombre con posicion correcta
    gfx_8_1: mismo resultado (49 match + 1 divergencia)

CORPUS
  gfx_v8_0.c:4552         el comentario que declara el bloque
  gfx_v8_0.c:4553         mqd_data = &mqd->cp_mqd_base_addr_lo
  gfx_v8_0.c:4559,4573,4577  los tres bucles
  gfx_v8_0.c:4568-4570    EOP RPTR/WPTR/WPTR_MEM sueltos (errata Tonga)
  gfx_v8_0.c:4528         lee mmCP_HQD_EOP_EVENTS -> cp_hqd_eop_done_events
  vi_structs.h:159-415    struct vi_mqd, 257 campos uint32_t
  gfx_8_0_d.h:630-685     los 53 offsets
  gfx_8_0_d.h:655-666     los 3 alias
  gfx_7_0_d.h:567-570     el bloque en GFX7, sin EOP
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.