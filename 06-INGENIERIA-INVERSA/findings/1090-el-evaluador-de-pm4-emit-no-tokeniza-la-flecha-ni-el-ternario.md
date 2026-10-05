# 1090 — El evaluador de `pm4_emit` no tokeniza `->` ni `?:`: el 14% de las escrituras del corpus son insintetizables, y en el arranque del KIQ las dos que fallan son **las dos que deciden el layout**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4EVAL
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py (nuevo) + este hallazgo
MODIFICADO_NADA_EXISTENTE    pm4_emit.py queda intacto
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_emit.py:205-230  (tokenize / parse_or / parse_shift)
ALCANCE=305 expresiones con `->` (13%) · 29 con `?:` (1%) · 2381 escrituras
ESTADO=PROBADO · NO reparado (ver §6)
```

## 0 · El resultado, primero

`pm4_emit.eval_call` no puede evaluar **ninguna** expresión con acceso a miembro:

```
$ eval_call("ring->queue")            -> Unresolved('token:>')
$ eval_call("ring->queue + 1")        -> Unresolved('token:>')
$ eval_call("1 ? 2 : 3")              -> Unresolved('token:?')
```

Frontera medida con 13 formas:

```
  queue                             NO  'queue'
  5 << 2                            OK  0x00000014
  (5 << 2) | 3                      OK  0x00000017
  5 & 0xff                          OK  0x00000005
  PACKET3_MAP_QUEUES_QUEUE(3)       OK  0x0C000000
  PACKET3_MAP_QUEUES_QUEUE(queue)   NO  'queue'
  lower_32_bits(0x11223344)         NO  'lower_32_bits'
  PACKET3(PACKET3_MAP_QUEUES, 5)    OK  0xC005A200
  ring->queue                       NO  'token:>'
  ring->queue + 1                   NO  'token:>'
  1 ? 2 : 3                         NO  'token:?'
  (1 << 31) | 1                     OK  0x80000001

resuelve 6 de 13
```

**Las dos limitaciones de gramática son `->` y `?:`.** Las otras tres filas que
fallan no son limitaciones: son identificadores que no existen, y el
`Unresolved` con el nombre correcto es exactamente lo que deben hacer.

## 1 · MAGNITUD SOBRE EL CORPUS

De las **2381** expresiones que el driver escribe con `amdgpu_ring_write`:

```
con `->`   acceso a miembro, no tokenizable   : 305   (13%)
con `?:`   ternario, no tokenizable           :  29   ( 1%)
con ambos                                    :   4
sintetizables tal cual                        : 2051  (86%)
```

El 86% se queda fuera del problema. **El problema está concentrado, y donde
duele.**

## 2 · LA CONCENTRACIÓN ES LO IMPORTANTE

```
bloque SET_RESOURCES + MAP_QUEUES   15 escrituras, 14 sintetizables, 1 con `->`, 1 con `?:`
bloque UNMAP_QUEUES                  6 escrituras,  5 sintetizables, 1 con `->`, 0 con `:`
```

**Las dos escrituras que no se sintetizan en el arranque del KIQ son las dos
payloads que deciden qué campo va en qué bit:**

```c
amdgpu_ring_write(kiq_ring,
                  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index) |   <- `->`
                  PACKET3_MAP_QUEUES_QUEUE(ring->queue) |
                  PACKET3_MAP_QUEUES_PIPE(ring->pipe) |
                  PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1));             <- `?:` y `->`
```

Un diseño en el que la mitad de un dword se resuelve y la otra no no es un
caso borde: es un dword partido en dos, una mitad con número y la otra con
`Unresolved`. Y esa mitad es la que `1082` necesita para demostrar que el
decodificador del proyecto **no rotula** `queue`, `pipe` y `me`.

## 3 · POR QUÉ NINGÚN LINTER NI CONTRATO LO DETECTÓ

`pm4_emit` tiene un `--self-test` y un autotest. **Su autotest pasa.** El motivo
es que la dependencia de la forma del texto es de la misma naturaleza que en
`1087` y `1089`, y en los tres casos el test se escribió sobre la forma que el
autor tenía delante.

```
el lexer acepta identificadores, numeros, parentesis y operadores
el corpus de test usa  PACKET3(...) y constantes
el fallo esta en una forma que no aparece en el corpus de test
```

**Un validador de sintaxis que valida la sintaxis que su autor escribió no puede
encontrar una forma sintáctica que nunca vio.** Para encontrarlo hacía falta
feedearle las expresiones **del corpus real**, que es lo que hice en §0.

## 4 · LOS TRES DEFECTOS DE `pm4_emit`, JUNTOS

`1087`, `1089` y este son **tres mecanismos distintos en el mismo fichero**, y
juntos tienen una forma común que merece nombre:

| | acoplamiento | Medido | Efecto |
|---|---|---|---|
| `1087` | catálogo de opcodes escrito a mano (`sid.h`) | 6 de 26 paquetes invisibles | recuento de alcance 20 en vez de 26 |
| `1089` | nombre de variable escrito en la regex (`ring`) | 239 escrituras invisibles | arranque del KIQ a 0 dwords |
| `1090` | gramática de expresiones más estrecha que el código | 13% + 1% insintetizables | las payloads decisivas sin resolver |

**Los tres son «la forma literal del código, escrita en el instrumento»**, y los
tres son invisibles porque **el instrumento funciona bien sobre la forma que su
autor tenía delante**. Un acierto parcial no se parece a un fallo, y por eso
estos tres no se ven leyendo el código: se ven alimentando el código real.

Y hay un cuarto que **no** es de `pm4_emit`: `layoutcross.py` mío tenía el
mismo defecto en `campos_escritos`, que buscaba `PACKET3_<OP>_<CAMPO>(` con el
opcode embebido en la expresión regular, y por eso no veía las emisiones de otro
fichero. Lo detecté porque fusionaba generaciones y salía con 17 filas
inventadas. Es el mismo patrón, y por eso `layoutcross` busca ahora con el opcode
como **dato**.

## 5 · LO QUE ESTO HACE CON LOS HALLAZGOS ANTERIORES

`1082` afirma, sobre el dword `CONTROL2` de `MAP_QUEUES` con `queue=3, pipe=1,
doorbell=5`:

```
CONTROL2 = (5 << 2) | (3 << 26) | (1 << 29) | 0 = 0x28000014
```

y lo marca como **`PROVEN_DERIVED`, no `OBSERVED`**, porque el valor es un cálculo
mío con los macros y no una lectura de una emisión. Es un límite honrado y
correcto.

**Ahora existe el camino para cerrarlo**, y es `tools/ibref.py`: liga el
evaluador de `pm4_emit` con un parser de escrituras que reconoce el anillo por
**identificador**, y **normaliza `->` y `?:` antes de evaluar**. Sin esa
normalización, la composición hereda el defecto de `pm4_emit`; con ella, el
`CONTROL2` sale leído de la expresión real del driver y el hallazgo pasa a
`OBSERVED`.

La normalización es de mi instrumento y **no exige tocar `pm4_emit`**: reescribir
`ring->queue` como `ring_queue` antes de llamar a `eval_call` es una
adaptación legítima de la frontera, no un parche.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he modificado `pm4_emit.py`.** Es de otra sesión activa. El contrato de la
reparación, para que no se pierda:

```
REPARACION  tokenize reconoce `->` como acceso a miembro y `? :` como ternario
INVARIANTE  las 6 formas que hoy resuelve devuelven el MISMO valor, byte a byte;
            en especial (1 << 31) | 1 = 0x80000001 y PACKET3(...) = 0xC005A200
TEST        positivo: eval_call("ring->queue", {}) -> Unresolved('queue'), no
                     Unresolved('token:>')   <- ESTA es la asercion clave: el
                     nombre del parametro, no un error de lexer
            positivo: eval_call("1 ? 2 : 3", {}) -> Unresolved(<la rama no
                     constante>), no 'token:?'
            alimentacion con las 2381 expresiones reales del corpus, como minimo
CONTROL     las 13 formas de la tabla de §0, con las 6 que ya funcionaban
```

**No he terminado `ibref.py`.** Su `--selftest` falla: el stub del evaluador no
reproduce el comportamiento de identificador que el diseño necesita, y esa
discrepancia es la que está destapando este defecto. Está en
`RESEARCH_INSTRUMENT`, sin promover, y su fallo está declarado en vez de
oculto.

**No he medido el modo `--control` ni `--frame-size`** de `pm4_emit`. He medido
`eval_call`, que es la función que los tres comparten.

## 7 · PROCEDENCIA

```text
frontera    13 formas contra pm4_emit.eval_call con load_macros() real -> 6 OK
mecanismo   Unresolved('token:>') y Unresolved('token:?'): el lexer parte `-` y
            `>` como operadores separados, y no conoce el acceso a miembro
magnitud    2381 expresiones de amdgpu_ring_write en el corpus
              305 con `->` (13%) · 29 con `?:` (1%) · 2051 (86%) sintetizables
concentr.   bloque SET_RESOURCES+MAP_QUEUES: 15 escrituras, 2 no sintetizables,
            y son las dos payloads con queue/pipe/me
autotest    pm4_emit --self-test pasa: el fallo esta en una forma que su corpus
            de test no contiene
encargos    tools/ibref.py (nuevo, RESEARCH_INSTRUMENT, selftest en rojo)
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que `tokenize` sea la única función
con el problema: he medido `eval_call` desde fuera y atribuyo el fallo al lexer
por el mensaje `token:>`, que lo indica, pero no he leído `parse_atom` para
confirmar que no hay un segundo punto de fallo en el camino. No afirma que las 305
expresiones con `->` sean todas sintetizables tras la normalización: afirma que hoy
no lo son. Y no es un juicio sobre `pm4_emit` en conjunto: el mismo fichero resuelve
el 86% de las expresiones del corpus.