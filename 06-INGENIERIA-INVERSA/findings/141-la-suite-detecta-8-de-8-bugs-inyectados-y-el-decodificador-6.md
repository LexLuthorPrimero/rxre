# 141 · La suite de pruebas tenía 208 comprobaciones y no se sabía cuántas cumplían su trabajo

```
CLASSIFICATION=TOOLING · TRACK=VERIFICATION
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Una suite en verde no dice nada sobre si sirve para detectar fallos. Sólo dice
que hoy no hay ninguno. Las 208 comprobaciones de `test_pm4.c` podrían haber
sido 208 que sólo leen `buf[0]` yan `32` y `42` y seguirían en verde
mientras el encoder escribiera basura.

La única forma de saberlo es **meter un bug a propósito y mirar si algo se
queja**. Eso es `tools/mutate.py`, y su resultado es un número que antes no
tenía: **de 8 bugs inyectados en el encoder, los detecta 8; y de esos 8, el
decodificador —no las comprobaciones de cabecera— detecta 6.**

Los 2 que no detecta el decodificador son los dos que **ninguna herramienta
estructural puede ver**, y por eso tienen nombre y no son un agujero sin
explicar.

## 1 · Qué hace el arnés

`tools/mutate.py` copia el árbol del driver a `/tmp/opencode/mutate-scratch`,
cambia **una línea literal** del encoder, construye, ejecuta `test_pm4` y
registra si algo falló. El árbol se reconstruye en cada mutante: el driver del
repo y el corpus de Linux no se tocan nunca, porque una herramienta que puede
corromper el driver no sirve para auditar el driver.

Las mutaciones son literales exactos, no expresiones regulares, y **el anclaje
tiene que aparecer exactamente una vez**. Eso no es estilo: un anclaje ambiguo
muta el primer sitio que case y emite un veredicto sobre un cambio que nadie
pidió. El primer catálogo tenía uno (`dispatch_token_fuera`), y el selftest lo
cazó antes de que yo ejecutara nada.

```
  $ python3 tools/mutate.py --all
  wait_count_alto                  CONFIRMADO   4    DECODIF
  wait_count_bajo                  CONFIRMADO   4    DECODIF
  dispatch_count_alto              CONFIRMADO   5    DECODIF
  sync_count_bajo                  CONFIRMADO   5    DECODIF
  event_count_uno                  CONFIRMADO   4    DECODIF
  dispatch_token_fuera             CONFIRMADO   8    DECODIF
  dispatch_operandos_intercambiados CONFIRMADO   2    cabecera
  ptepde_count_menos_uno           CONFIRMADO   2    cabecera
  exit=0
```

La columna `DECODIF` la calcula la herramienta, no quien lee la salida.

**Cómo lo calculó primero, y por qué estaba mal.** El criterio inicial era que
los checks de decodificación llevan la palabra `decodifica` en el nombre.
Falso: son 13 llamadas al helper y sólo 12 checks la llevan. El que falta es el
de PTEPDE, cuyo nombre habla de la cabecera SDMA y no de decodificación. Con
ese criterio, `sync_count_bajo` se atribuía al header validator cuando lo cazan
**las dos** comprobaciones — un mutante que cae en dos sitios sólo nombra uno.

**El criterio ahora** es un prefijo declarado, `[IB] `, que todo check producido
por `check_ib()` o `check_ib_hasta_no_pm4()` lleva. Un prefijo y no una palabra:
una palabra aparece y desaparece con cada reescritura del texto, y un criterio
de atribución tiene que ser una convención verificada, no una coincidencia de
prosa. `mutate.py --selftest` comprueba el invariante contra el binario, no
contra el fuente:

```
  $ # quitando el marcador de un solo check
  FAIL todo check de decodificacion lleva el marcador [IB] -- marcados=13 llamadas=12
```

## 2 · Los seis que detecta el decodificador

Todos son la misma clase de fallo: **la cabecera declara una longitud y lo
escrito no la cumple**. Con `count` en bits 21:16 y total = count + 2, el
decodificador ve el desfase; un `check_eq` sobre `buf[0]` no puede verlo,
porque la cabecera puede ser perfectamente válida mientras el cuerpo no lo es.

| mutante | qué rompe | checks que caen |
|---|---|---|
| `wait_count_alto` | declara 8 dwords, escribe 7 | 4 |
| `wait_count_bajo` | declara 6, escribe 7 | 4 |
| `dispatch_count_alto` | `DISPATCH_DIRECT` declara 4, escribe 5 | 5 |
| `sync_count_bajo` | `SURFACE_SYNC` declara 2, escribe 3 | 5 |
| `event_count_uno` | `EVENT_WRITE` declara 1 payload, escribe 0 | 4 |
| `dispatch_token_fuera` | se pierde el dword de token | 8 |

`dispatch_token_fuera` es el más instructivo: **8 comprobaciones caen** y es el
único que el header validator no habría visto, porque la cabecera del paquete
sigue siendo correcta. Falta un dword de payload y nada en el primer dword lo
dice.

## 3 · Los dos que no detecta, y por qué es el resultado correcto

```
  dispatch_operandos_intercambiados   CONFIRMADO   2    cabecera
  ptepde_count_menos_uno             CONFIRMADO   2    cabecera
```

Los dos los detecta la suite — `CONFIRMADO` — pero **no el decodificador**:

- **x e y intercambiados**: la cabecera es válida, la longitud es correcta, y
  `dw1`/`dw2` llevan operandos que sólo tienen el significado correcto en
  contexto. El decodificador es estructural y no tiene por qué saber si un
  `DISPATCH_DIRECT` con x=1 y e y=8 es una carga válida. Lo cazan dos
  `check_eq` explícitos.
- **`ptepde` escribiendo `count - 1`**: el payload SDMA. Es el bug documentado
  entre `sdma_v3_0.c:986-996` (escribe `count`) y `sdma_v4_0.c:1649-1658`
  (escribe `count - 1`), y el ASIC ejecuta la ruta de v3.0 (`findings/043`,
  `findings/115`–`120`). Lo detecta `check_eq("dw9 plain count, per
  sdma_v3_0.c (043)")`, que existe y **cita el hallazgo**.

Éste lo declaré mal. En la primera versión del catálogo lo puse `VIVIR`, con el
razonamiento —correcto en su mitad— de que el decodificador no mira payload
SDMA. El resultado fue `DISCREPANCIA` porque **sí lo detectaba otro check**. La
expectativa equivocada no era "el decodificador no lo ve": era "nadie lo ve".
Corregido a `CAER` con la afirmación correcta, que es la que importa:

> El driver **no puede volver** al comportamiento de `sdma_v4_0` sin romper un
> test. Lo que sigue sin cubrirse es el payload SDMA en general, y eso sí es un
> agujero con nombre.

## 4 · Lo que el arnés encontró en sí mismo

**Seis** de sus **seis** vectores de selftest existen porque la primera versión
tenía el defecto que cada uno comprueba. Ninguno es hipotético:

1. **Un anclaje no único** (`dispatch_token_fuera`). Habría mutado el primer
   `= 1u;` que encontrara y emitido un veredicto sobre un cambio distinto del
   declarado. Ahora el catálogo se valida a sí mismo antes de correr.
2. **`printf` sin `<stdio.h>`** en el proyecto sintético. El compilador lo dijo;
   yo lo había escrito.
3. **El proyecto sintético tenía el bug del `count`**: mi `emit` escribía
   `cnt + 1` dwords y el `decode` del mismo fichero exigía `cnt + 2`. Los dos
   checks lo cazaron. Es la regla de PACKET3, reproducida por error.
4. **La copia del driver no conservaba la profundidad del árbol**, así que
   `../../tools/pm4decode.c` resolvía fuera del scratch. Los ocho mutantes
   reportado "no compilan" — **y el motivo era del arnés, no del encoder**,
   que es exactamente el caso en el que un arnés sin explicación parece un
   veredicto sobre el driver. Y peor: `/tmp/opencode/tools` existía, así que la
   copia manual anterior compilaba contra un decodificador **ajeno y viejo** y
   daba un verde falso. `preparar()` reconstruye ahora la forma del árbol en
   vez de reescribir rutas.
5. **Un fichero ausente reventaba con traceback** en vez de reportarse como
   error del catálogo. Un arnés que se rompe en vez de medir, no mide.

6. **El criterio de atribución era una coincidencia de prosa.** Decía que
   "todos los checks llevan `decodifica` en el nombre" y son 13 contra 12. Se
   detectó al contar, no al ejecutar: el arnés no falló, mi afirmación sí. Por
   eso el criterio es ahora un prefijo declarado y comprobable.

Los cinco primeros son bugs del arnés. El sexto es el másmolesto porque no
hacía fallar nada: hacía que un reparto correcto pareciera una atribución arbitraria. Se
escribe aquí para que no se repita: **un criterio de clasificación tiene que ser
una convención verificada contra el binario, porque una frase en un comentario
no sobrevive al primer check nuevo.**

Queda un defecto abierto, y está declarado:

```
PENDIENTE=el scratch resuelve ../../tools por ruta relativa y una vez dio
          verde falso porque existia un /tmp/opencode/tools ajeno
  | HALLAZGO=141-la-suite-detecta-8-de-8-bugs-inyectados-y-el-decodificador-6.md
  | ESTADO=NOT_DETERMINED
  | NECESITA=una comprobacion de que el scratch NO contiene un tools/ propio y
  |          de que el include resuelto cae DENTRO del scratch
  | ALCANZABLE_SIN_ROOT=si
```

## 5 · Por qué esto no cierra el gate

208 comprobaciones que detectan 8 de 8 bugs inyectados en el encoder es una
medida **del encoder**, no del hardware. Sigue sin establecerse que cualquiera
de esos paquetes haga algo en el RX 550: ningún paquete construido aquí se ha
ejecutado nunca en la GPU, y la única secuencia de dispatch disponible es el
workaround EDC de Carrizo, que retorna inmediatamente para `CHIP_POLARIS12`.

```
CLASE NO CUBIERTA POR NINGUNA HERRAMIENTA ESTRUCTURAL
  - semantica de payload: que operandos son validos para que opcode
  - payload SDMA en general (solo el count de PTEPDE esta fijado)
  - efecto sobre GC_HWIP: requiere insmod, NIVEL 4, AGENTS.md 76-82
```

## Procedencia

```
tools/mutate.py          arnés, 8 mutantes, selftest 6/6
tools/mutate.py --all    8/8 CONFIRMADO, exit 0
tools/pm4decode.c        selftest 25/25, 0 avisos con -Wall -Wextra
07-DRIVER/tests/test_pm4.c  208 checks, 0 failures, 13 de decodificación
                          (13 llamadas al helper, 13 checks con prefijo [IB])
sid.h:377, :397          PACKET3_WRITE_DATA 0x37, PACKET3_WAIT_REG_MEM 0x3c
tonga_sdma_pkt_open.h:55-56   SDMA_PKT_HEADER_op_mask 0xFF, op_shift 0
findings/043, 115-120    sdma_v3_0 es la ruta que corre; count sin restar
```

## CORRECCION POSTERIOR

**`CORRECTED_BY` este mismo hallazgo — el criterio de atribución, dos veces.**

La primera redacción de la sección 1 afirmaba:

> "todos los checks de decodificación llevan `decodifica` en el nombre y
> **ninguno** de cabecera lo lleva"

Es **falso**, y lo era de una forma que no rompía nada: hay 13 llamadas al
helper de decodificación y sólo 12 checks llevan esa palabra. El decimotercero,
el de PTEPDE, se llama así porque su contenido habla de la cabecera SDMA y no
de decodificación. La afirmación era plausible, estaba escrita como
verificable, y nadie la comprobó.

La consecuencia medida: con ese criterio, `sync_count_bajo` se atribuía al
header validator cuando **lo cazan las dos** comprobaciones — 5 checks fallan,
no 2. Un mutante que cae en dos sitios queda atribuido a uno.

La corrección es un **prefijo declarado** `[IB] `, que todo check producido por
`check_ib()` o `check_ib_hasta_no_pm4()` lleva, más un vector de `mutate.py
--selftest` que verifica el invariante **contra el binario** y no contra el
fuente: 13 checks marcados, 13 llamadas. Quitando el marcador de un solo check,
el vector falla con `marcados=13 llamadas=12`.

**Por qué no la borré y la reescribí como si nunca hubiera estado mal**: porque
el defecto no es una frase equivocada, es una clase de error — un criterio de
clasificación escrito como prosa en un comentario en vez de como convención
comprobable. Esa clase volverá en el próximo criterio que escriba. Queda
registrada por eso, y como regla permanente en `AGENTS.md` § VALIDACIÓN DE LA
VALIDACIÓN.

Nota aparte, sin efecto en este hallazgo: la tabla de nombres de `pm4_nombre`
en `tools/pm4decode.c` tuvo siete entradas equivocadas y se reconstruyó desde
`sid.h` antes de escribir nada aquí. Se registra para que no se lea como un
acierto del procedimiento.
