# 1066 — 35 de 35 filas acusadoras eran mentira: cuatro clases de falso positivo en un verificador de opciones

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/prosa.py 1.0.0 (instrumento de este hallazgo)
         revkit/pm4dec.py:29 (docstring, caso que motivo la herramienta)
ESTADO=PROVEN-MI-DEFECTO x4 · CORREGIDO · 35 -> 6 filas
herramienta   tools/prosa.py 1.0.0
sha256        b28dcf07ed83cc7818d36838245d478c6274254ed0e07691a999c722adc4a3b2
```

## 0 · EL HECHO Y SU COSTE

La primera medición real del eje de opciones dio **35** `FLAG_INEXISTENTE`.
Adjudiqué los 8 primeros **a mano, uno a uno, leyendo el código**. Cuatro eran
falsos.

Si hubiera publicado los 35, el acierto habría sido **31 de 35 ≈ 89 %**, y esa
cifra es la que hace que un instrumento con ruido se siga usando: parece
bueno, y cada fila es una afirmación concreta que alguien se va a creer.

> **Un eje que dice 35 y acierta 31 no es un eje: es ruido con formato de tabla.**
> Y el ruido aquí tiene un nombre propio: una fila que accuses es una afirmación
> que alguien va a investigar, y el coste de que sea falsa no es la fila.

**Resultado tras corregir: 35 → 6**, y los 6 se sostienen a mano.

## 1 · LAS CUATRO CLASES, QUE SON DISTINTAS Y HAY QUE NOMBRARLAS

| clase | ejemplo | por qué es FALSO |
|---|---|---|
| **A · guion parentético** | `artifacts.py --que`, `--el`, `--y`, `--aceptar` | la prosa del proyecto usa `--` como paréntesis, no como opción. No son flags |
| **B · flag de otro programa** | `round.py --contradictions` | la frase es `causal_map.py --contradictions`: es el flag de **`causal_map.py`**, nombrado de paso. La frase es verdadera |
| **C · abreviatura de argparse** | `struct_layout.py --fields` | `allow_abbrev=True` es **el defecto de CPython**: `--fields` **funciona** si existe `--fields-of` |
| **D · flag retirado** | `reenvio_freeze.py --forzar` | la prosa dice `**ELIMINADO.**`. Documenta la retirada, honestamente |

### La clase C es la que casi se me escapa, y la razón es técnica

Supuse que `--fields` no existía porque leí mal qué fichero registraba
`--fields-of`. **Era `reg_resolve.py`, no `struct_layout.py`.** Lo verifiqué
después y la herramienta tenía razón y yo me equivocaba. Se queda escrito porque
el modo de fallo —dar por bueno un falso positivo porque encaja con la
narrativa— es el que hace que estas puertas se crocodilen.

### La clase D no tiene arreglo limpio, y se dice por qué

Detectar que una línea *retira* un flag exige reconocer la negación en prosa.
Eso es detección de intención, y la detección de intención en prosa es un
oráculo débil. La regla que se implementó es **una lista corta y explícita**
(`ELIMINADO`, `RETIRADO`, `ya no existe`, `REMOVED`, `DEPRECATED`), y su
justificación está escrita en el código: *una lista corta es un oráculo, un
detector de negación general es adivinanza*.

## 2 · EL MECANISMO DE A Y B, QUE ES LO TRANSFERIBLE

Un flag solo se acepta como declaración sobre **esta** herramienta en dos formas:

```
(i)   la línea empieza por el flag  Y tiene una vecina que también empieza
      por un flag.     <- la firma de un bloque de opciones
(ii)  la línea invoca a ESTE programa y el flag va detrás.
```

El requisito de **la vecina** no es decorativo. Sin él, una frase partida en
dos líneas empieza igual que un bloque de opciones:

```
--coverage   which findings have no registered claim    <- bloque
--aceptar un "no".  No hay banderines aqui.             <- prosa partida
```

Las dos empiezan por `--` y solo la primera está acompañada. Eso lo cazó el
selftest, con dos vectores que fallaron.

## 3 · EL LÍMITE QUE SE DEJÓ A PROPÓSITO, Y QUE NO SE AFINÓ

Hay una cuarta rama que degrada a `NO_CLASIFICABLE`: si el código menciona
`sys.argv`, un flag que el código conoce por otra vía **no se cuenta como
inexistente**. Es correcta en el fondo —`flags_inventory.py` lee `sys.argv` a
mano y su docstring lo declara— pero **es demasiado ancha**, porque el modismo de
entrada `sys.exit(main(sys.argv[1:]))` también la activa, y lo usa
`claim.py:758`.

Se deja así a propósito, y está escrito en el código por qué:

> El error va hacia **"no se puede concluir"**, nunca hacia **"acuso"**. Un
> instrumento que acusa de más no sirve; uno que se calla de más solo pierde
> sensitivity, que se recupera leyendo el código.

La asimetría no es estética: es la diferencia entre un instrumento que la gente
ignora y uno que la gente consulta.

## 4 · EL CASO QUE MOTIVÓ LA HERRAMIENTA, Y POR QUÉ NO ES HALLAZGO

`revkit/pm4dec.py` declara en su docstring:

> *De `sid.h` del corpus, leído EN TIEMPO DE EJECUCIÓN.*

Y su código hace lo contrario: elige la tabla con el **grafo de includes** de
`gfx_v8_0.c`, que da `vid.h`. Su propio bloque de comentarios explica que
**`sid.h` es la cabecera disidente**: la única de seis que desplaza
`LOAD_SH`/`LOAD_CONFIG`/`LOAD_CONTEXT` una posición.

O sea: **el contrato en prosa declara el INPUT que el código existe para
rechazar.** Y es la afirmación más pesada del decodificador PM4 del proyecto.

**El instrumento la clasifica `SOLO_EN_LISTA` y la deja en la sección
informativa. Y ese es el veredicto correcto**, por esto:

- el literal `sid.h` **sí aparece** en el código —en `HEADERS_OPCODE`, en
  `SID_CANDIDATOS`, en `RENUMERADOS_SID`— porque lo nombra para **excluirlo**;
- por tanto un chequeo de prosa **no puede falsarlo**: no hay ausencia que medir;
- y la verdad de la cadena (`vid.h` es la que esta generación compila) **no la da
  un grep de prosa**: la da el **cierre de includes**, que es trabajo del nodo
  `R2`, no de un verificador de prosa.

> **Lo que esto deja escrito, y es un hallazgo sobre el instrumento:** la
> afirmación que carga con la mayor parte del peso del decodificador PM4 **no es
> falsable con análisis de prosa**, y hasta ahora no estaba escrito en ninguna
> parte. Un instrumento cuyo techo se conoce sigue siendo usable; uno cuyo techo
> se confunde con su alcance no lo es.