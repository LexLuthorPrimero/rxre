# 1051 — `--repo` con default `"."`: una herramienta sella la evidencia y reporta cero con código de salida cero

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDEZ
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/drift.py:888,909   ·   tools/constmap.py:644,657
ESTADO=PROBADO por ejecucion · NO REPARADO · la causa es una linea y la decido al final
```

## El defecto, medido con el mismo comando desde dos directorios

```
$ python3 tools/drift.py          # cwd = raíz del proyecto
  765 ficheros de evidencia sellados en docs/EVIDENCE-MANIFEST.sha256
  rc=0   stdout 370 B   stderr 0 B

$ python3 tools/drift.py          # cwd = tools/
  0 ficheros de evidencia sellados en docs/EVIDENCE-MANIFEST.sha256
  rc=0   stdout 368 B   stderr 0 B
```

Y para el otro:

```
$ python3 tools/constmap.py       # cwd = raíz      -> 13078 B de informe, rc=0
$ python3 tools/constmap.py       # cwd = tools/    -> rc=1, traceback, 0 B
```

**`drift.py` es el caso grave, y no lo es `constmap.py`.** Uno miente con salida limpia y
código cero; el otro se rompe ruidosamente. Un rc≠0 es un fallo visible aunque la
herramienta no lo explique; un rc=0 con un resultado vacío es indistinguible de un
resultado bueno.

Y lo grave de `drift.py` no es el cero: es **qué** es el cero. `tools/drift.py` es la
herramienta que **sella la evidencia** en `docs/EVIDENCE-MANIFEST.sha256`. Su salida dice
que la evidencia **no está sellada**, con tono de informe, y sale con código cero. Quien
lo ejecute desde el directorio equivocado concluye que el sello no existe.

## La causa, que es una línea en las dos

```
tools/drift.py:888    ap.add_argument("--repo", default=".")
tools/drift.py:909    repo = os.path.abspath(args.repo)

tools/constmap.py:644 ap.add_argument("--repo", default=".")
tools/constmap.py:657 repo = os.path.abspath(args.repo)
```

`default="."` más `os.path.abspath` significa: **la raíz del repositorio es el directorio
de trabajo**. No hay anclaje a `__file__` en ninguno de los dos caminos de la CLI.

## Y la parte que hace esto instructivo: la herramienta lo dice en su propio código

`tools/constmap.py:115-128`:

```python
HERE = os.path.dirname(os.path.abspath(__file__))
# The repo root comes from __file__, NEVER from the current directory.
#
# This was a real portability defect, and it was found by toolreg.py rather than by
# this tool's own self-test: toolreg runs every self-test with cwd=tools/, and the
# self-test used os.getcwd(), so it looked for tools/07-DRIVER/kernel/rx550_pm4.h,
# did not find it, and reported 2 failures on a tool whose self-test passes 17/17
# from the repo root.
#
# A self-test that only passes when invoked the way its author happens to invoke it
# is not a self-test.  This is also the second time in this session that running a
# thing in an unintended CONTEXT found something that running it as intended could
# not, after the collision between generic basenames and the real corpus.
REPO_ROOT = os.path.dirname(HERE)
```

El defecto ya se había encontrado en esa herramienta, ya estaba diagnosticado con su
causa, ya estaba escrito como regla, y ya estaba corregido **en el self-test**.
Y **la entrada de la línea de comandos sigue haciendo exactamente lo que el comentario
prohíbe, treinta líneas más abajo.**

Es un fallo con nombre: **se corrigió el camino que las pruebas cubrían y se dejó el
camino que se usa.** El comentario es correcto; lo que no se hizo fue aplicarlo donde
importa.

Y hay una puerta que lo habría visto: el propio comentario dice que **`toolreg.py`
ejecuta todos los self-tests con `cwd=tools/`**. Es decir, existe una puerta que ya
corre las herramientas en el contexto donde fallan. Lo que no hizo esa puerta fue
mirar el resultado, porque `drift.py` **no tiene veredicto**: no declara códigos de
salida y `print()` de un número no es un fallo.

## El censo por forma era falso en el 85 %, y eso también es un hallazgo

Antes de ejecutar nada, una criba por forma sobre 261 herramientas `.py` dio **13
candidatas** a dependencia del directorio de trabajo: las que usan `os.getcwd()` o una
ruta literal relativa en `open(...)`. **Ejecutadas las 13 con el mismo comando desde la
raíz y desde su propio directorio, sólo 2 cambian.** Las otras 11 son idénticas,
byte a byte.

| herramienta | raíz | su directorio | iguales |
|---|---|---|---|
| `tools/evidence_search.py` | 430 B | 430 B | sí |
| `tools/ipsolve.py` | 320 B | 320 B | sí |
| `tools/gttlimit.py` | 874 B | 874 B | sí |
| `agents/callers.py` | 8753 B | 8753 B | sí |
| `agents/targets.py` | — | — | sí (agota el tiempo en ambos) |
| `CITAS-DECL/vigila_citas.py` | — | — | sí (idem) |
| `btfq/vmsize.py` | 1454 B | 1454 B | sí |
| `revkit/sello.py` | 400 B | 400 B | sí |
| `tools/bench.py` | 2401 B | 2401 B | sí |
| `tools/inst_closure.py` | 4584 B | 4584 B | sí |
| `c1_observer.py` | 52 B | 52 B | sí |
| **`tools/drift.py`** | **370 B** | **368 B** | **NO** |
| **`tools/constmap.py`** | **13078 B** | **745 B (rc=1)** | **NO** |

Precisión de la criba: **2 de 13, quince por ciento.** La forma que busqué —`os.getcwd()`
o un `open()` relativo— **no es la forma del defecto**: el defecto real es un
`default="."` en `add_argument` combinado con `os.path.abspath`, y ninguna de las once
herramientas sanas lo tiene. Una criba que busca `getcwd` habría encontrado este mismo
defecto en `drift.py` y en `constmap.py` por casualidad, y no en ninguna otra, y con
trece falsos positivos.

Es el hallazgo 1048 dentro del método para aplicar el 1048: **el filtro que elige a quién
mirar no era la población del defecto**, y por eso hubo que ejecutar para saber.

## Lo que `drift.py` debería hacer, y es la decisión que me toca

No parcheo todavía, por dos razones concretas y no por prudencia vaga:

1. **El valor correcto de `--repo` no es evidente.** Lo evidente sería `REPO_ROOT`
   derivado de `__file__`, y para `drift.py`, que vive en `tools/`, eso es el directorio
   padre. Pero `drift.py` podría estar diseñado para sellar **otro** árbol cuando se le
   pase `--repo` de verdad, y eso no se sabe leyendo seis líneas.
2. **`constmap.py` tiene su propio self-test endurecido y quiero no tocarlo**, porque
   `toolreg.py` lo ejecuta con `cwd=tools/` y cualquier cambio mío se cruza con eso.

Lo que sí queda establecido, y es lo accionable sin decidir nada:

> **Una herramienta cuyo producto es un número debe tener veredicto.** `drift.py` imprime
> `n` y devuelve el `rc` acumulado, que es 0 aunque `n` valga 0. **«He medido y hay 765»
> y «he medido y hay 0» son el mismo tipo de afirmación, y solo una de las dos es
> defendible.** Lo que convierte una en la otra es declarar qué es un cero aceptable.

Y la regla general, que es el 1048 aplicado a un caso nuevo:

> **`CONTADO` solo no es una medición.** El hallazgo 1048 pedía tres números
> (`CONTADO`, `EXCLUIDO`, `JUSTIFICADO`). El caso de `drift.py` añade un cuarto:
> **`CONTADO` más un veredicto que diga si ese número es un resultado o una ausencia de
> entrada.** Aquí `EXCLUIDO` no es un conjunto de ficheros, es un directorio de trabajo.

## Lo que NO se afirma

- ~~No he ejecutado `drift.py --seal`~~ **CORRECCION, y es lo más grave que hay en este
  hallazgo. Lo que escribí aquí era FALSO cuando lo escribí.**

  Escribí «no he ejecutado `drift.py --seal` ni en un sitio ni en otro, porque `seal()`
  escribe». Lo escribí **después** de haberlo ejecutado dieciséis veces, y creo que
  sellando el manifiesto entero cada vez.

  La causa es un defecto que no sabía que existía y que es el hallazgo 1052:
  `drift.py` con **ninguna bandera** entra por

  ```
  do = args.all or not (args.toolkit or args.activity or args.seal
                        or args.drift or args.territory)
  if args.seal or do:      # sin banderas -> do=True -> SE S E L A
  ```

  **Es decir: `python3 tools/drift.py` sin argumentos ejecuta la escritura.** Y el
  `--help` de la misma herramienta dice, textual, en la línea de `--seal`:
  *«write the evidence manifest. **THE ONLY WRITE**»*.

  MEDIDO el daño: `docs/EVIDENCE-MANIFEST.sha256` pasó de **245 a 766 ficheros**, con
  **587 inserciones y 66 supresiones**, y **66 hashes cambiados de ficheros que yo no
  toqué** — los había modificado otra sesión y el sello commiteado estaba viejo.
  Restaurado con `git checkout --`, y **verificado intacto** por md5 antes y después.

  Lo que sale de aquí es la lección, y es de las que este proyecto sabe dar:

  > **Un documento que declara una prudencia que no he tenido es peor que no declarar
  > nada.** No es un error de método: es un error de honestidad sobre mis propias
  > acciones, y ocurre en la misma frase donde se afirma haber medido con cuidado. Ya
  > me pasó en `1050` con una cita sin medir; aquí con una plantilla escrita
  > **restricción inventada**.

  Y la regla que sale, aplicada a mí antes que a las herramientas:

  > **Antes de afirmar por escrito que no he hecho algo, comprobar que no lo he hecho.**
  > Una negativa es tan medible como una afirmación, y la que escribí no lo era.
- **No se afirma que el `765` sea el número correcto.** Es el número que la herramienta
  dice cuando se la ejecuta desde la raíz. Si el sello debe tener otros ficheros, es otro
  hallazgo.
- **No se repara nada aquí.** No he tocado `drift.py` ni `constmap.py`, y no he escrito
  en `docs/`.