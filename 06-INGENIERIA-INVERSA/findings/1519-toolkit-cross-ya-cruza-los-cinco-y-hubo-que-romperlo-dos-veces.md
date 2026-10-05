# 1519 — `toolkit_cross` ya cruza los cinco validadores de RXRE, y para demostrar que cruza **hubo que romper uno dos veces**

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=ACCION + PRUEBA DE MUTACION
ESTADO=PROVEN (que el cruce detecta; probado por mutacion, dos veces)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=5 validadores invocados por ruta; 5 de 5 con contrato, EXIT_ON_SUCCESS=0
  y selftest en verde
PRODUCER=08-ARQUITECTURA/tools/toolkit_cross.py -- seccion 4, NUEVA
MUTACIONES=2 sobre `rxre_deleg.py`.  La 1a no la detecto.  La 2a si.
ENCADENA=1517 (el cruce debe ser falsable) · 1515 · 1513 · toolkit_cross.py
```

## Qué se añadió, y por qué no se importan

`1517` dejó escrito que `rxre_touch` no estaba en ningún runner y que
`toolkit_cross.py` no lo cruzaba. Eso es lo que se ha hecho: **sección 4** de
`toolkit_cross.py`.

**Y la decisión que se tomó antes de escribir nada: NO se importan.**

Es la misma decisión que `1515` tomó para `toolkit.py`, pero aplicada a un
validador cuyo propósito es **cruzar**. La razón está en el docstring del propio
`toolkit_cross.py`:

> «No se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben.»

Un validador que se importa deja de ser independiente, y el cruce deja de ser un
cruce: **dos módulos que comparten memoria no sirven para mutar uno al otro**, que
es justo lo que un cruce sirve. Por eso se **invocan por ruta** con `subprocess` y
se lee su `rc` y su cabecera.

Costo de la alternativa, medido: importar exigiría añadir `RXRE/tools` a
`sys.path` desde `08-ARQUITECTURA/tools/` — **cuatro niveles hacia arriba**, y
acoplar dos árboles por una ruta que no es un módulo.

## Resultado 1 — el hueco que la sección 4 encontró

Al añadir la sección, la primera ejecución dio **3 de 5**, no 5 de 5:

```
rxre_deleg.py   7 campos  NO   SIN EXIT_ON_SUCCESS
rxre_touch.py   7 campos  NO   SIN EXIT_ON_SUCCESS
```

Y la causa era mía: había puesto el `EXIT_ON_SUCCESS=0` **en la prosa**, antes
del ancla `TOUCHES_INTEGRATED`, de modo que la línea `# CONTRACT:` quedaba **fuera
de la cabecera de 4000 bytes** — que es exactamente el recorte que leen tanto
`rxre_contracts.py` como el cruce.

> un campo escrito en prosa es un campo que no existe

Corregido y verificado **por el mismo cruce que lo detectó**, que es la única
comprobación que vale: `EXIT_ON_SUCCESS en cabecera de 4000B: True`.

Resultado: **5 de 5**.

## Resultado 2 — y el cruce NO detectaba una rotura: dos mutaciones

Escribir una sección de cruce y ver que dice «5 de 5» **no prueba que funcione**.
La única prueba es romper lo que cruza.

**Mutación 1 — rompí un vector de `rxre_deleg.py`.** El cruce siguió diciendo
«5 de 5 en verde» con `rc=0`.

Dos motivos, y los dos son culpa mía:

1. **La primera versión del cruce no usaba el `rc`.** Calculaba
   `rc = _rc_de(ruta, ["--selftest"])` y el veredicto salía **sólo del
   contrato**: si había contrato y `EXIT_ON_SUCCESS`, «ok». El `rc` estaba ahí,
   evaluado, y sin usar.

   > un cruce que no mira el rc de lo que cruza, cruza el contrato

2. **Mi mutación estaba mal hecha.** Cambié la condición del vector por `True`,
   lo que lo hace **pasar**. Un vector que pasa no es una rotura.

**Mutación 2 — la correcta:** forcé el vector a `False`.

```
rxre_deleg.py   8 campos  si   SELFTEST rc=1
      4 de 5 con contrato, EXIT_ON_SUCCESS y selftest en verde.
```

**Detectado, con nombre y con el `rc`.** Restaurado → 5 de 5.

Y en el camino salió el límite que hay que declarar: **`rc` sólo es comparable si
la herramienta terminó**. Un `TIMEOUT` no es un `rc`, así que `_rc_de` lo
devuelve como cadena y el cruce lo trata como fallo, no como un número raro.

## Procedencia

- `STATIC` — cabeceras leídas con el mismo recorte posicional de 4000 bytes que
  usa `rxre_contracts.py`. Recortar de más o de menos daría dos veredictos para el
  mismo fichero.
- `CROSS-CHECK` — **el cruce lo detecta, y está probado por mutación dos veces**,
  no declarado.
- `EJECUCION` — cinco instrumentos invocados por ruta (`--selftest`), más
  `toolkit_cross`, `rxre.py` y `toolkit.py`. **Sin MMIO, sin TLB, sin insmod.**
  `GPU INTACTA`.
- Los cinco: **19 + 22 + 17 + 10 + 18 = 86 vectores**, todos PASS.
  `rxre.py` **188 vectores** intacto. `toolkit.py` autotest OK con 9 flags.

## Lo que se cambió, exactamente

- `08-ARQUITECTURA/tools/toolkit_cross.py`: `VALIDADORES_RXRE`, `_rc_de()`, y la
  sección 4. **Ningún import nuevo** salvo `re` y `subprocess`, y ambos locales a
  la función que los usa — siguiendo el patrón que el fichero ya tenía.
- Los cinco instrumentos de `RXRE/tools/`: bloque `# CONTRACT:` propio.
  `rxre_boot` ya lo tenía; **`rxre_frontier`, `rxre_contracts` y `rxre_deleg`
  no lo tenían**, y eso es un hallazgo sobre mí: construí cinco validadores y
  cuatro no eran declarables. `rxre_touch` se declara
  `WRITES_FILES=indeterminado` porque delega.

## Lo que NO se afirma

- **No se afirma que los cinco sean correctos.** El cruce dice que su contrato, su
  `EXIT_ON_SUCCESS` y su selftest **no se contradicen**. Es menos de lo que
  haría falta para confiar en el runner, y el propio cruce lo dice ahora en su
  punto 5.
- **`rxre_touch.py` declara `NOT_FOUND` sobre código leído**, que no es
  `PROVEN_ABSENT`. Y `RXRE/tools/` sigue sin estar en ningún runner: `run_all.py`
  cruza los seis validadores de `toolkit_cross` desde sus tablas, y **ningún
  mecanismo del proyecto invoca a los cinco de RXRE salvo este cruce**.
- **No se ha tocado `toolkit.py`** en este hallazgo, ni ningún contrato de
  herramienta fuera de `RXRE/tools/`.

## Dos notas de método

**La primera: mi primera mutación no era una mutación.**

Cambié `x == "OK"` por `True`. Eso hace que el vector **pase**, y un vector que
pasa es exactamente el estado que ya estaba. Necesitaba `False`.

Y antes de eso había un fallo de verdad: el cruce **calculaba el `rc` y no lo
usaba**. Es el mismo patrón por quinta vez, y ya merece nombre propio:

| | |
|---|---|
| `1507` | la columna `declarado` traducía `indeterminado` a `no` |
| `1515` | se daba veredicto a quien no declaró |
| `1515` | `remove` estaba declarado y nunca comprobado |
| `1517` | un vector leía el resultado del cálculo que debía vigilar |
| `1519` | el cruce calculaba el `rc` y no lo comparaba |

Cinco, en cuatro instrumentos, y **ninguno falló**: todos salían verdes.
*Un valor calculado y no comparado no es una medición: es un trabajo sin
resultado.*

**La segunda: un cruce que no he roto no sé si es un cruce.**

«5 de 5 en verde» es un número que también produce un cruce que no mira nada.
Eso no lo distingue de uno que mira lo correcto, y por eso la sección 4 no se dio
por buena hasta que **el validador roto salió nombrado en la tabla**.

La prueba de que un cruce funciona no es que dé verde: es que **dé rojo cuando
debe**, con el nombre de quien lo tiene.
