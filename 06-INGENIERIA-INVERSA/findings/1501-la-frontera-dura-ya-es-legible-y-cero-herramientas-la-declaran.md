# 1501 — La frontera dura ya es legible: 19 herramientas hablan de `/sys`, 0 escriben, 0 declaran la frontera. Y el instrumento falló cuatro veces en verde

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION
ESTADO=PROVEN (para lo que el codigo leido declara) / NOT_DETERMINED (para
  lo que hace en runtime)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=19 herramientas del registro nombran un nodo de /sys literal.  Cero
  escriben a /sys segun su AST.  Cero declaran TOUCHES_INTEGRATED.
PRODUCER=RXRE/tools/rxre_frontier.py v1.0.0, 21 vectores, todos PASS
COMANDO=python3 RXRE/tools/rxre_frontier.py --selftest
IDENTIDAD=leida de sysfs con rxre.limites_de_la_maquina(): integrada
  0x8086:0x0412, discreta 0x1002:0x699f, indice de la integrada card0
ENCADENA=1487 (el campo no existe) · 1491 (0 herramientas con las dos
  declaraciones) · 1481 (el catalogo solo cubre 4 de 220)
```

## Qué se añadió y por qué no es un septimo validador

`1487`/la medición posterior encontró que la frontera dura de AGENTS.md
**no es representable** en el contrato de seguridad: sus 9 claves no incluyen
ninguna para la integrada, y se buscó una explícitamente (`touch`, `integ`,
`i915`, `frontier`, `vga`, `consola`) sin encontrar ninguna.

Eso dejaba la frontera garantizada en un sitio —`rxre.PUERTA_FRONTERA`, con
vector— e **invisible en el otro**, y sin forma de saber qué herramientas la
nombran siquiera.

`rxre_frontier.py` **no valida**. Hace una interseccion, como
`toolkit_cross.py` hizo con las seis herramientas de validacion: **no se
comprueba nada nuevo, se cruza lo que ya se sabe** — qué nodo de `/sys` nombra
cada herramienta, con qué clase de acceso, y por qué vía llega a la integrada.

## Resultado 1 — la frontera, medida, no supuesta

```
integrada (de sysfs) : 0x8086:0x0412
discreta  (de sysfs) : 0x1002:0x699f
indice de la integrada: card0

19 herramientas nombran un nodo de /sys literal
12 de esas tocan, de un modo u otro, el dominio de la integrada
  POR_INDICE    4   usan en CÓDIGO el cardN de la integrada, por POSICIÓN
  POR_PADRE     8   nombran /sys/class/drm sin concretar el nodo
  POR_IDENTIDAD 0   nombran 8086:0412 literal

ESCRIBEN en /sys según su AST: 0
declaran TOUCHES_INTEGRATED: 0
tienen contrato, de las 12 que la nombran: 4
```

**El resultado que importa no es ninguno de los cinco.** Es que **cero
herramientas escriben a `/sys`** — y ese cero es `NOT_FOUND` sobre el código
leído, **no** `PROVEN_ABSENT`. No se ha ejecutado nada; una escritura podría
venir de un módulo, de un `ioctl`, o de otro proceso. El informe lo dice con esas
palabras en su propia declaración de estado, y hay un vector que falla si esa
declaración deja de nombrar los tres estados.

## Resultado 2 — las 4 que usan `card0` en código, y por qué son legítimas

Aquí está lo interesante, y es una corrección a mi propio cruce.

La primera versión contaba `card0` con un `findall` sobre el **texto** y salían
**9 herramientas**. Mirando las nueve, la mayoría eran **comentarios que
explican precisamente que `card0` es la Intel** — el texto *documentando* la
frontera, no cruzándola.

```
        el nombre del nodo en un comentario no es un acceso al nodo
```

Separado con AST, el criterio que `contract_exec.py` ya usa y por el que este
proyecto escribió en `toolkit.py`:

> «doclint.py aparecía como "declara escritura" por un grep mal hecho. Ese es el
> fallo de fondo: **un contrato en prosa no se puede comprobar con una
> máquina**.»

Baja de 9 a **4**, y las cuatro son legítimas:

| herramienta | líneas de código | qué hace |
|---|---|---|
| `tools/rxre.py` | 292, 303 | `limites_de_la_maquina()` **resuelve card0/card1 leyendo sysfs** |
| `tools/fingerprint.py` | 338, 348, 352 | `_id_pci("card0")` — **mide la identidad de la iGPU**, que es su trabajo |
| `tools/snapshot.py` | 224, 225, 574, 767 | fotografía del reparto de GPU |
| `08-ARQUITECTURA/tools/_selftest_runtime_obs.py` | 243, 251, 270, 284 | **control negativo del selftest** |

Las cuatro **leen el nodo de la integrada a propósito**, y tres de ellas existen
justo para **documentar o medir la frontera**. Ninguna la cruza.

Y `revkit/obs.py` — el directorio con cero contratos — es la que mejor lo tiene,
en su propio docstring:

> «NUNCA por número de card. En este host card0 es la Intel iGPU
> (8086:0412) y card1 es la RX550. **Suponer el orden por el índice es lo que
> produjo un dato atribuido al ASIC equivocado.**»

O sea: **la regla correcta está escrita en el proyecto, en prosa, en un fichero
sin contrato, y no es comprobable por ninguna máquina.** Eso no es un defecto de
`obs.py`: es el hueco de `1487`, visto desde el lado bueno.

## Resultado 3 — el instrumento falló cuatro veces, y en verde

Es la parte que más enseña de este hallazgo, y va antes que cualquier cifra.

**1. `RAIZ` con un `dirname` de menos.** Viviendo en `RXRE/tools/`, `dirname`
dos veces da `/…/RX550-INVESTIGACION/RXRE`, donde no existe `tools/rxre.py`. La
carga fallaba, `limites_de_la_maquina()` no se llamaba, y el informe decía
**«integrada: None»**. El vector en verde comprobaba que la identidad «se resuelve
**o** se declara no resuelta» — y con un `RAIZ` equivocado no se resolvía y se
declaraba, y las dos ramas pasan.

> **un vector con dos salidas aceptables no mide nada**

**2. `RE_SYS_NODO` exigía comillas a ambos lados.** Los nodos se escriben de
tres formas: literal (`"/sys/kernel/debug/dri/0000:01:00.0"`), prefijo
(`base = "/sys/class/drm"`) y con formato (`"{bdf}"`). El patrón sólo encontraba
la primera y el informe decía **«0 herramientas nombran /sys»** — con 21
vectores en verde, en un árbol donde hay cientos de nodos citados.

**3. El parser de identidad, dos veces.** `ident.split(":")` quita el `0x` de
cada mitad: correcto para `"8086:0412"`, **incorrecto para `"0x8086:0x0412"`**,
que es lo que devuelve sysfs aquí. Y en la versión siguiente normalicé la
identidad pero comparé lo leído de sysfs **en crudo**. Dos veces: la función
devolvió `None` y `POR_INDICE` salió 0 en una máquina donde `card0` **es** la
Intel, leída de sysfs.

> **normalizar sólo un lado de una comparación no es normalizar**
>
> **un parser que casi casa devuelve "no hay", que es peor que fallar**

**4. `construidos` se recogía dentro del bucle y se leía fuera.** `NameError`, no
un cero.

> **un nombre fuera de alcance no da 0, da ruido**

Cada fallo tuvo el mismo patrón: **el instrumento dijo "no hay nada" con todos
los vectores en verde.** No es un defecto de este fichero: es la clase de fallo
que `1481` ya medía con el `FileNotFoundError` que hacía que 28 capacidades se
leyeran como cero.

**La diferencia es que aquí los cuatro tienen vector ahora, y tres de ellos
comprobaban algo que antes no se comprobaba** (que el índice se lee; que hay
alguien por índice; que la identidad es coherente). El vector que cazó el
`RAIZ` no se relajó: se añadió el que faltaba.

## Procedencia

- `STATIC` — AST sobre los 220 ficheros del registro; `rxre.limites_de_la_maquina()`
  para las identidades, **no reimplementado** (dos números para el mismo hecho
  es lo que `1473` midió); `/sys/class/drm/cardN/device/{vendor,device}` leído
  directamente para el índice.
- `CROSS-CHECK` — el índice `card0` leído **por `rxre_frontier.py`** y por un
  script aparte, y comparado. Coinciden.
- `EJECUCION` — sólo lectura de fuentes. **No se ejecutó ninguna herramienta del
  registro.** Sin `--help-probe`, sin MMIO, sin TLB, sin insmod. **`GPU INTACTA`.**
- **Ninguna herramienta existente modificada en esta iteración.**

## Lo que NO se afirma

- **No se afirma que el cero de escrituras a `/sys` sea `PROVEN_ABSENT`.** Es
  `NOT_FOUND` sobre el código leído. Hay un vector que falla si el informe deja
  de decir `PROVEN_ABSENT` explícitamente.
- **No se afirma que las 12 herramientas sean seguras.** Han nombrado un nodo y
  eso es todo lo medido.
- **No se afirma que `TOUCHES_INTEGRATED` deba añadirse al vocabulario de
  `toolkit.py`.** Eso obligaría a revisar sus 71 contratos. Es una acción
  propuesta, medida en su coste, no ejecutada.
- **`POR_PADRE` es `NOT_DETERMINED`, no riesgo.** Nombrar `/sys/class/drm` sin
  concretar no es tocar la integrada; puede o no entrar en ella, y el informe no
  elige.

## La nota que queda

Las cuatro herramientas que usan `card0` en código lo hacen **bien**: leen la
integrada para identificarla, medirla, o comprobarla. El proyecto sabe qué es
la integrada, lo tiene escrito en varios sitios, y en un caso tiene el docstring que explica por qué no hay que asumir el orden por el índice.

Lo que no tiene es **una forma de que una máquina lo compruebe**. El campo
existe en cinco ficheros que esta sesion declaro y en ningún validador; el
resto de 19 lo nombran en prosa o en comentarios.

La frontera dura de AGENTS.md lleva 40 rondas declarada en prosa. Este
instrumento no la hace cumplir: **hace que se pueda ver quién la menciona**, que
es la condición previa, y es un `NOT_DETERMINED` honesto donde antes no había
nada.
