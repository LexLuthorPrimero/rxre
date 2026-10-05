# 1065 — un verificador de contratos que no puede fallar: `ast.walk` contaba el docstring como código

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/prosa.py 1.0.0 (instrumento de este hallazgo)
ESTADO=PROVEN-MI-DEFECTO · CORREGIDO · con vector de regresion que lo fija
herramienta   tools/prosa.py 1.0.0
sha256        b28dcf07ed83cc7818d36838245d478c6274254ed0e07691a999c722adc4a3b2
```

## 0 · EL HECHO

Un verificador de contratos tiene que comparar **lo que la prosa declara** contra
**lo que el código hace**. La tentación es escanear el fichero: es lo que hace
`tools/toolcheck.py` con `add_argument`, y lo que hace la interlusa de
`tools/riesgo.py` con dos regex sobre el **texto**.

La primera versión de `prosa.py` casi caía en eso. Lo avoided, y el motivo
concreto está en el diseño: se extrae la prosa con `ast` y las referencias del
código también con `ast`, y **los nodos `Constant` que son docstrings se
excluyen** (`_nodos_docstring()`, que los recoge de `Module`, `FunctionDef`,
`AsyncFunctionDef` y `ClassDef`, no solo del módulo).

## 1 · POR QUÉ ESO NO ES UN DETALLE DE ESTILO

`ast.walk` ve el docstring del módulo **igual que ve cualquier otra cadena**. Es
un `Expr(Constant(str))`, y el caso más común del árbol.

Si se contara, el resultado sería: **toda** declaración de entrada de **todas**
las herramientas saldría `SUSTENTADA`. No porque sean ciertas, sino porque la
palabra que la prosa afirma está en la misma frase que la afirma.

MEDIDO: son 205 herramientas con contrato y ~1000 afirmaciones de entrada. El
instrumento habría produced **238 filas en verde**, que es exactamente la forma
que tiene un control que no puede fallar: un número limpio, plausible, y vacío
de información.

## 2 · LO QUE LO CAZÓ

Dos vectores, y uno de ellos existe por esto:

```
REGRESION__docstring_NO_es_codigo
    el docstring dice "fuente de datos de zz9x.h" y el codigo no lo menciona
    => zz9x.h tiene que salir SIN_RESOLVER, no SUSTENTADA

REGRESION__qq4w.h_SIN_RESOLVER
    qq4w.h solo aparece en la prosa, en ninguna parte del codigo
    => SIN_RESOLVER
```

El primero está escrito **a propósito para fallar** si alguien vuelve a escanear
texto: su único trabajo es sujetar esa decisión de diseño.

Y hay un segundo mecanismo, más sutil, que también depende de esto: la
diferencia entre `EN_APLICACION` y `SOLO_EN_LISTA` (hallazgo `1066`) **no
existe** si los literales de la prosa entran como literales del código, porque
entonces la lista de candidatos de `HEADERS_OPCODE` parecería "usada".

## 3 · LA LECCIÓN, Y POR QUÉ LA ESCRIBO SIENDO YO EL QUE LA COMETIÓ

> **Un instrumento que no puede fallar no informa de nada.** Y la forma más
> barata de construir uno es empezar por lo que ya se hace en el proyecto:
> `grep`.

Este árbol tiene al menos tres controles que interrogan el **texto** de un
fichero para decidir qué hace: la interlusa de `toolreg.run_selftests()`, el
`declares_read_only()` de `riesgo.py`, y el `if "--selftest" in txt` que produces
los 22 falsos positivos que el propio hallazgo `R1` documenta. **Los tres son
textuales, y los tres tienen el mismo techo**: no pueden distinguir
`escribe("x")` de `# escribe "x"`.

La lección no es "usa `ast`". Es: **un control sobre qué hace un programa, hecho
sobre el texto del programa, tiene un techo que no se ve desde el control** — y
ese techo se descubre cuando el control se calibra contra un caso que no
importa, como estos vectores.

## 4 · LO QUE ESTO NO DICE

No dice que `ast` resuelva el problema entero. `ast` tampoco ve los
**comentarios**, y hay contratos enteros escritos en comentarios: los 32
ficheros `.c`/`.sh` quedan `NO_CLASIFICABLE` por eso, y
`08-ARQUITECTURA/tools/reenvio_freeze.py` documenta en un comentario que
`--forzar` ya no existe, cosa que el instrumento no ve.

Es decir: **`ast` sube el techo, no lo quita.** Y el techo que queda está
declarado en la cabecera de `prosa.py`, que es lo único que hace que un
instrumento con techo sea usable.