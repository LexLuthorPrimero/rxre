# 1089 — `pm4_emit` exige que el anillo se llame literalmente `ring`: los 239 `kiq_ring` son invisibles, y en `gfx_v8_0.c` eso son exactamente los 3 paquetes con defectos de layout

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4PARSE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   ninguno: solo lectura de pm4_emit.py y del corpus
MODIFICADO_NADA_EXISTENTE    pm4_emit.py queda intacto; el defecto se REPORTA
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_emit.py:485  (WRITE_RE)
ALCANCE=239 escrituras en el corpus · 21 en gfx_v8_0.c · 4 ficheros ciegos
ESTADO=PROBADO · NO reparado (ver §7)
herramienta  08-ARQUITECTURA/tools/pm4_emit.py  (existente; NO se ha modificado)
distinto de 1087: alli el catalogo de opcodes; aqui el parser de escrituras
```

## 0 · El resultado, primero

```
$ python3 08-ARQUITECTURA/tools/pm4_emit.py --func gfx_v8_0_kiq_kcq_enable
gfx_v8_0_kiq_kcq_enable  (linea 4304)  0 dwords (0 condicionales), 0 resueltos
```

Esa función escribe **`PACKET3_SET_RESOURCES` en L4331 y `PACKET3_MAP_QUEUES` en
L4345**. Devuelve **0**. No es que no haya nada: es que no lo mira.

```python
# 08-ARQUITECTURA/tools/pm4_emit.py:485
WRITE_RE = re.compile(r"amdgpu_ring_write\s*\(\s*ring\s*,\s*(.+?)\s*\)\s*;", re.S)
```

**El nombre de la variable del anillo está escrito en la expresión regular.** Una
función que llame a su anillo `kiq_ring` no casa, y `pm4_emit` no dice nada: su
salida es un `0 dwords` limpio.

## 1 · MAGNITUD, MEDIDA SOBRE EL CONJUNTO DE FICHEROS

```
variable del anillo en amdgpu_ring_write, en los 44 .c del corpus
   ring          2142   <-- la unica que WRITE_RE exige
   kiq_ring       239   <-- invisible
```

En `gfx_v8_0.c`, el fichero de la generación objetivo:

```
   ring           151
   kiq_ring        21     ->  12,2% de sus escrituras de anillo
```

Y **cuatro ficheros no tienen ni una sola escritura con `ring`**, luego para ellos
`pm4_emit` no puede resolver nada:

```
   amdgpu_amdkfd_gfx_v9.c        7 escrituras, todas con otro nombre
   amdgpu_amdkfd_gfx_v10.c       7 escrituras, todas con otro nombre
   amdgpu_amdkfd_gfx_v10_3.c     7 escrituras, todas con otro nombre
   amdgpu_amdkfd_gfx_v11.c       7 escrituras, todas con otro nombre
```

## 2 · LOS TRES PAQUETES INVISIBLES SON LOS TRES CON DEFECTOS

Los paquetes que `gfx_v8_0.c` escribe por `kiq_ring`:

```
L4331   PACKET3_SET_RESOURCES
L4345   PACKET3_MAP_QUEUES
L4773   PACKET3_UNMAP_QUEUES
```

Y los hallazgos sobre esos mismos paquetes:

| invisible para `pm4_emit` | hallazgo | estado |
|---|---|---|
| `PACKET3_SET_RESOURCES` | `1073` — aprobado por su verificador, con los campos donde no tocan | defecto probado |
| `PACKET3_MAP_QUEUES` | `1082` — `CONTROL2` sin `queue`, `pipe` ni `me` | defecto probado |
| `PACKET3_UNMAP_QUEUES` | `1077` — 4 contradicciones de campo sin resolver | contradicción abierta |

**El punto ciego no coincide con los defectos por casualidad: coincide porque los
tres son el camino de inicialización del KIQ**, que es el único que nombra su
anillo de otra forma. El programa PM4 que la GPU ejecuta **antes de hacer nada
else** es exactamente el que la herramienta no puede resolver.

Consecuencia directa sobre la cadena de evidencia del proyecto: **no existe, y no
se puede obtener con esta herramienta, un IB de referencia del arranque del KIQ.**
Por eso los tres hallazgos quedan en `PROVEN_DERIVED` y no en `OBSERVED`, y por
eso `1077` no tiene el discriminante que necesita.

## 3 · LA HIPÓTESIS QUE TUVE Y ERA FALSA

Primero medí el reparto de estilos de escritura y concluí que `pm4_emit` solo
parseaba el constructor `ib.ptr[ib.length_dw++] = …`:

```
estilo ib.ptr[length_dw++]          : 42 lineas
estilo amdgpu_ring_write(...PACKET) : 36 lineas
proporcion no resuelta              : 75%
```

**Esa conclusión era falsa en suExplanation, y el dato que la refutó fue el
contador de `length_dw`: cero apariciones en el fichero.** `pm4_emit` no menciona
ese estilo en absoluto, así que no podía ser "el estilo que parsea". La
explicación real es más simple y más grave: parsea `amdgpu_ring_write`, **pero
exige `ring`**.

Lo verifiqué con un control positivo y negativo:

```
gfx_v8_0_ring_emit_vm_flush  ->  9 dwords, 9 resueltos     (usa `ring`)
gfx_v8_0_kiq_kcq_enable      ->  0 dwords, 0 resueltos     (usa `kiq_ring`)
```

**Un `0 dwords` no distingue "no escribe" de "no lo veo".** Es la misma clase de
error que este proyecto mide en otros sitios, y aquí la cometí yo antes de
mirar el código.

## 4bis · UNA SOSPECHA MÍA QUE ERA FALSA, Y EL LINTER TENÍA RAZÓN

`doclint` marcó mi encabezado `## 1 · MAGNITUD, MEDIDA SOBRE **TODO** EL CORPUS`
como marcador de trabajo sin resolver, y sospeché que era un defecto suyo: en un
corpus en castellano, «todo el ASIC» y «para todo» colisionarían con `TODO`.

**Es falso, y el código dice por qué** (`doclint.py:104-114`):

```
# BUG PROPIO QUE ESTA MISMA COMPROBACION CAUSO... la primera version era
# case-INsensitive, asi que \bTODO\b casaba con la palabra castellana "todo".
# Con un corpus en castellano, "todo el ASIC", "para todo" y "todo lo que"
# dan miles de falsos positivos y el linter deja de usarse en dos rondas.
#
# La regla: TODO / FIXME / XXX / TBD son convenciones en MAYUSCULAS. Se exige
# mayusculas.
PLACEHOLDERS = re.compile(r"(?:\bTODO\b|\bFIXME\b|\bXXX\b|\bTBD\b|\?\?\?)")
```

La colisión **ya estaba identificada y resuelta**: la regla exige mayúsculas
exactamente para eso. Y el error era **mío**: usé `TODO` en mayúsculas para
**enfatizar**, que es un hábito tipográfico del castellano y produce mayúsculas
en palabras que no son marcadores.

Lo que queda es una interacción menor y probablemente irreducible: en castellano
la mayúscula con valor enfático es idiomática, así que `TODO` en mayúsculas es
ambiguo por construcción entre «marcador» y «énfasis». Ninguna regla de contexto
lo resuelve del todo. Se anota, no se reporta como defecto: el linter se comportó
according to its own declared rule, y esa regla está escrita con su justificación
al lado.

## 4 · POR QUÉ EL CERO ES PELIGROSO Y EL ERROR NO

Un parser que fallara ruidosamente —error, exception, código distinto— sería
inofensivo. Este devuelve **`0 dwords, 0 resueltos`**, que es una respuesta
**válida y falso**: dice "esta función no emite nada", y eso es falso.

Y es peor por el nombre: `--func` sobre una función de arranque devuelve el mismo
`0` que devolvería sobre un `if` vacío. La salida no distingue *ausente* de
*ausente de mi mirada*.

## 5 · LO QUE YA FUNCIONA, Y ES MUCHO

No es un instrumento roto. Con la variable correcta resuelve de verdad:

```
$ pm4_emit.py --func gfx_v8_0_ring_emit_vm_flush
gfx_v8_0_ring_emit_vm_flush  (linea 6191)  9 dwords (2 condicionales), 9 resueltos
    6199  dword          0xC0053C00
    6200  dword          0x00000000
    6203  dword          0x0000051E
    ...
```

**9 de 9 resueltos**, con número de línea y valor. El evaluador de expresiones es
completo y correcto (`tokenize`, `parse_*`, `eval_call`, `load_macros`), y la
salida es utilizable tal cual. **El defecto es de Recognition, no de resolución**:
falta reconocer la llamada, y todo lo demás ya está.

## 6 · LO QUE ESTO DICE DE LA ARQUITECTURA DE LAS HERRAMIENTAS DEL PROYECTO

`1087` y `1089` son **el mismo fichero, dos mecanismos distintos**, y juntos
forman una clase: **acoplar un instrumento a una forma literal del texto en lugar
de a la estructura**.

```
1087  catalogo de opcodes escrito a mano      (sid.h, cuando la placa usa vid.h)
1089  nombre de variable escrito en la regex (ring, cuando el anillo es kiq_ring)
```

Los dos son `NOT_FOUND → PROVEN_ABSENT` boosterados por el detalle correcto: una
expresión regular bien escrita que casa con el caso que el autor tenía delante.
**El detalle correcto es lo que hace el fallo invisible**: una lista de 119
opcodes parece específica, y `ring\s*,` parece una comprobación de sintaxis.

Y hay un patrón de reparto que conviene ver: **lo que el autor escribió es
justo lo que su herramienta sí resuelve**. Los 9 dwords de `ring_emit_vm_flush`
salen porque esa función usa `ring`.

## 7 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he modificado `pm4_emit.py`.** Es de otra sesión activa.

**No he construido el sintetizador de IB de referencia** que pondría los tres
hallazgos en `OBSERVED`. Es posible y no duplicaría trabajo: `pm4_emit` ya tiene
el evaluador (`eval_call`, `load_macros`) y mi `layoutcross` ya tiene el parser de
`amdgpu_ring_write`, así que la composición es corta. No lo he hecho porque es
una construcción nueva y este hallazgo es una medición, y porque los valores que
escribiría (`ring->queue`, `ring->doorbell_index`, `ring->me`) **no son constantes
en el código**: el artefacto que falta no es «el IB» sino «un IB de referencia
para unos valores elegidos», y esa elección es una decisión que conviene no
tomar en el mismo paso que la medición.

**No he medido los otros modos** de `pm4_emit` (`--control`, `--frame-size`,
`--all`) con el mismo defecto. He medido `--func` y el regex, que es lo que
explica el resultado.

## 8 · EL CONTRATO DE LA REPARACIÓN

```
REPARACION  WRITE_RE pasa a aceptar cualquier identificador antes de la coma:
              amdgpu_ring_write\s*\(\s*[A-Za-z_]\w*\s*,\s*(.+?)\s*\)\s*;
            y se registra CUAL fue el nombre, para que la salida diga por que
            anillo se escribio
INVARIANTE  los 9 dwords de gfx_v8_0_ring_emit_vm_flush no cambian: ahora se
            resuelven 9 de 9 -> 9 de 9, y el contenido byte a byte identico
TEST        positivo: --func gfx_v8_0_kiq_kcq_enable -> >0 dwords, y entre ellos
                     PACKET3_SET_RESOURCES y PACKET3_MAP_QUEUES
            negativo: una funcion con un `if` vacio sigue devolviendo 0, y ahora
                     la salida dice explicitamente "sin escrituras de anillo"
            el recuento de 239 kiq_ring pasa a 0 Writes ignoradas
ALCANCE     los 4 ficheros KFD pasan de 0 a resolubles
DECLARADO   la limitacion nueva, que hoy no existe: "no se modela el flujo de
            control; un ring_write dentro de un if se cuenta como escrito"
```

## 9 · PROCEDENCIA

```text
mecanismo   pm4_emit.py:485  WRITE_RE con `ring` literal ; `length_dw` aparece 0 veces
positivo    --func gfx_v8_0_ring_emit_vm_flush  -> 9 dwords, 9 resueltos
negativo    --func gfx_v8_0_kiq_kcq_enable      -> 0 dwords, 0 resueltos
mecanismo   el cuerpo de kiq_kcq_enable escribe ring_write(kiq_ring, ...)
magnitud    corpus: ring 2142 / kiq_ring 239
            gfx_v8_0.c: ring 151 / kiq_ring 21 (12,2%)
            4 ficheros KFD con 7 escrituras cada uno y cero `ring`
paquetes    los 3 de kiq_ring son SET_RESOURCES, MAP_QUEUES, UNMAP_QUEUES
enlace      los mismos 3 de los hallazgos 1073, 1082 y 1077
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que `kiq_ring` sea la única variable
de anillo que el parser rechaza: he medido las dos que aparecen en el corpus
(`ring` y `kiq_ring`) y no hay una tercera, lo que **no** es lo mismo que probar
que no pueda haberla en código que no esté en el árbol. No afirma que el
`0 dwords` de `kiq_kcq_enable` signifique que no haya nada que resolver: afirma
que hay 2 paquetes de control y al menos 13 escrituras, y que la herramienta no
los ve.