# 1095 — **Ninguna herramienta del proyecto extrae un valor de campo PM4 de un dword.** `pm4_codec` rotula sin calcular, `field_masks()` está muerta *y* rota con masks a cero, y `vid.h` no declara anchuras: por eso los cuatro defectos de layout se acumularon sin que ninguno se viera

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4FIELDS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   ninguno en esta iteracion
MODIFICADO_NADA_EXISTENTE    pm4_codec.py intacto
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_codec.py:150-172  (field_masks, muerta y rota)
         08-ARQUITECTURA/tools/pm4_codec.py:186      (pkt["campos"] = {}, nunca relleno)
ALCANCE=las 7 herramientas PM4 del proyecto · 0 extracciones de campo en todas
ESTADO=PROBADO · NO reparado
```

## 0 · El resultado, primero

`pm4_codec` **imprime el texto del layout junto a cada dword y no calcula ningún
valor**. Ejecutado sobre el IB de referencia de `1094`:

```
$ pm4_codec.decode([0xC004A300, 0x20000001, 0x0000001C, 0, 0, 0])
opcode PACKET3_UNMAP_QUEUES (0xA3)  F=4  datos=5
   dw1  0x20000001  ACTION[1] | QUEUE_SEL[2:0] | ENGINE_SEL[6:5] | NUM_QUEUES[10]
   dw2  0x0000001c  DOORBELL_OFFSET0[25:2]
   dw3  0x00000000  dword[2]
```

Correcto en el opcode, correcto en el `F`, correcto en el número de payload. Y
**los rangos `[1]`, `[2:0]`, `[6:5]`, `[10]` no se usan para nada**: son texto al
lado de un número, no una extracción.

La función que debería hacer esa extracción existe:

```
08-ARQUITECTURA/tools/pm4_codec.py:150
def field_masks(opname):
```

**No la llama nadie.** Y está rota:

```
$ pm4_codec.field_masks("PACKET3_UNMAP_QUEUES")
   ACTION             mask=0x00000000 shift=0
   QUEUE_SEL          mask=0x00000000 shift=4
   ENGINE_SEL         mask=0x00000000 shift=26
   NUM_QUEUES         mask=0x00000000 shift=29
   DOORBELL_OFFSET0   mask=0x00000000 shift=2
   ... 10 campos, todos con mask 0

   extrayendo del dword observado 0x20000001:
   ACTION = 0 · QUEUE_SEL = 0 · ENGINE_SEL = 0 · NUM_QUEUES = 0
```

**Todos los masks son cero.** Si esa función se cableara tal cual, devolvería
**0 para todos los campos sin avisar**, que es peor que no tenerla.

## 1 · POR QUÉ LOS MASKS SON CERO, Y ES LA RAZÓN DE FONDO

El propio código lo dice, y es honesto:

```python
out[m.group(1)] = (0, int(m.group(2)))     # solo el shift
```

**`vid.h` no declara anchuras.** El kernel escribe
`PACKET3_UNMAP_QUEUES_ACTION(x) ((x) << 0)`, y de ahí sale la posición del bit
menos significativo. **No sale cuántos bits ocupa el campo.** La segunda regex
que intenta calcular un mask:

```python
re.finditer(r"define\s+" + opname + r"_(\w+)\s+\(1\s*<<\s*(\d+)\)", ...)
```

existe para deducir la anchura de la forma `(1 << N)` **declarada al lado**, y
`setdefault` garantiza que nunca pise el shift ya capturado. Encuentra la forma
cuando está — y en `vid.h` **no está**, porque el kernel no la escribe para estos
paquetes.

> **La imposibilidad no es un fallo de la herramienta: es una carencia de la
> fuente.** `layoutcross` choca con el mismo muro y por eso declara
> `ANCHURA_NO_DETERMINABLE` = *«el kernel da el desplazamiento, no la anchura»*.

Lo que **no** es inevitable es seguir como está, porque hay tres salidas y
ninguna se ha tomado:

```
1  el documento de hardware, que si declara los rangos
2  derivar la anchura de la complementariedad, como hace layoutcross con
   VMID_MASK<<0 / UNMAP_LATENTY<<16 -> vmid_mask ocupa [15:0]
3  declarar que NO se extraen valores, y que los rangos de DOC_LAYOUTS son
   documentacion, no calculo   <- lo que el codigo hace de hecho, sin decirlo
```

## 2 · LO QUE ESTO EXPLICA: POR QUÉ LOS CUATRO DEFECTOS ANTERIORES SON INVISIBLES

| hallazgo | defecto | ¿por qué no se vio? |
|---|---|---|
| `1061` | `CP_DMA` con un dword de más | solo visible al contar |
| `1073` | `SET_RESOURCES` con campos donde no tocan | solo visible al comparar posiciones |
| `1082` | `MAP_QUEUES` `CONTROL2` sin `queue`/`pipe`/`me` | solo visible al comparar qué escribe el driver |
| `1094` | `UNMAP_QUEUES`: 3 de 4 etiquetas apuntan a bits que no son | **solo visible con un IB de referencia** |

Los cuatro se acumulan en `DOC_LAYOUTS`, y `DOC_LAYOUTS` **nunca produce un
número**. Una tabla de etiquetas que nadie convierte en valores no puede tener el
efecto que sus entradas describen.

**Y esto obliga a corregir la severidad de `1094`.** Allí escribí que
`pm4_codec` «decodifica 3 de los 4 campos con el valor equivocado». Es cierto si
alguien extrae a mano siguiendo las etiquetas, y es lo que hice yo. **La
herramienta no extrae nada**: el daño observable es *rotular mal*, no *calcular
mal*. `1094` queda con la parte del análisis intacta y con la parte del daño
reducida a «las etiquetas mienten», que es menos grave.

## 3 · MEDIDO SOBRE EL PROYECTO ENTERO

```
$ grep -rn "field_masks\|campos\[" --include=*.py tools/ 08-ARQUITECTURA/tools/ revkit/
(sin llamadas a field_masks)
```

Las herramientas PM4 del proyecto:

| herramienta | extrae el count | extrae campos con nombre |
|---|---|---|
| `pm4_codec.py` | sí | **no** — `pkt["campos"] = {}` se inicializa y nunca se rellena |
| `pm4_layout_audit.py` | sí (`F`) | **no** |
| `pm4census.py` | sí (`mascara_del_count`) | **no** |
| `revkit/pm4dec.py` | sí | **no** |
| `tools/pm4ops.py` (mío) | no extrae, contrasta opcodes | contrasta LSB, sin mask |
| `tools/layoutcross.py` (mío) | id. | contrasta LSB, declara la anchura no determinable |
| `tools/ibref.py` (mío) | id. | no extrae: sintetiza |

**Cero de siete extraen un valor de campo.** El `count` es el único campo que
alguien extrae, y es el único que las cabeceras sí describen completo.

## 4 · POR QUÉ ESTO ES MÁS BARATO DE ARREGLAR DE LO QUE PARECE

La tentación es decir «hay que implementar la extracción de campos». **No**, o
no primero: sin anchuras no se puede, y `field_masks()` devuelve ceros. Arreglar
eso sin resolver la anchura produce ceros con apariencia de datos.

El arreglo correcto, en orden de coste:

```
1  pm4_codec debe DECLARAR que DOC_LAYOUTS es documentacion y no calculo.
   Hoy lo usa como si fuera calculo: rotula cada dword con un rango que no
   aplica. Una linea que lo diga evita que el proximo que lea la tabla se
   lleve un numero que la herramienta nunca calculer.
2  los rangos que si se pueden verificar sin anchura, deben verificarse. Es
   exactamente el LSB, y layoutcross ya lo hace con 43 afirmaciones y 4 clases
   de veredicto. No hay que reimplementarlo.
3  la anchura, solo con el documento de hardware. Y declararla como
   NOT_DETERMINED mientras no exista, que es lo que hace layoutcross.
```

## 5 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he modificado `pm4_codec.py`.** No he cableado `field_masks()` y **no
debería**: con masks a cero devolvería ceros, y un campo que vale 0 por defecto
es indistinguible de un campo que vale 0. Sería un fallo silencioso nuevo, y
justo en la herramienta cuyo problema es la rótulos incorrectos.

**No he calculado ninguna anchura.** Se pueden derivar de la complementariedad
en algunos casos (`VMID_MASK<<0` y `UNMAP_LATENTY<<16` acotan `vmid_mask`), pero
derivar una ancho de un vecino no es lo mismo que declararla, y confundir las dos
cosas es como nacen las cifras que nadie puede comprobar. Queda
`NOT_DETERMINED`.

**No he reescrito la sección de severidad de `1094` como hallazgo aparte.** La
corrección está en §2 de este, referring al lugar donde se aplica, para que no
haya dos versiones de la misma afirmación circulando.

## 6 · PROCEDENCIA

```text
medida 1   python3 -c "pm4_codec.decode([...6 dwords...])"
          -> imprime las etiquetas al lado de cada dword; ningun valor
medida 2   grep -rn "field_masks" tools/ 08-ARQUITECTURA/tools/ revkit/
          -> 1 definicion, 0 llamadas
medida 3   python3 -c "pm4_codec.field_masks('PACKET3_UNMAP_QUEUES')"
          -> 10 campos, todos mask=0x00000000; extraccion da 0 en todos
medida 4   grep de las 7 herramientas PM4: 7/7 sin extraccion de campos con nombre
fuente     vid.h NO declara anchuras; solo el desplazamiento, confirmado en 5 headers
IB         08-ARQUITECTURA/artifacts/R8-IBREF/kcq_disable_unmap.ib.txt
escrituras 0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que `vid.h` no declare anchuras en
ningún paquete: se ha comprobado en los paquetes con layout numerado y en los
macros de `SET_RESOURCES`, `MAP_QUEUES` y `UNMAP_QUEUES`, no en los 119 de
`sid.h`. No prueba que no exista un documento de hardware en el árbol; afirma que
las cabeceras del corpus no lo llevan. Y no propone una anchura para ningún
campo.