# 1513 — El acoplamiento real no está en `subprocess`: está en las tablas. 72 invocaciones que ningún grafo de imports ve, y el campo de la frontera ya tenía el precedente escrito

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION + ACCION + REPARACION
ESTADO=PROVEN (las 72 invocaciones) / NOT_DETERMINED (el nivel 4, declarado)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA salvo un
  fichero de validacion modificado
MEDIDO=176 llamadas a subprocess; 70 con programa literal; 0 invocan a una
  herramienta hermana; 72 invocaciones HERRAMIENTA_NUESTRA, todas en TABLAS
PRODUCER=RXRE/tools/rxre_deleg.py v1.0.0, 10 vectores, todos PASS
ENCADENA=1510 · 1507 · 1505 · 1501 · 1487 (la accion propuesta, ahora medida)
```

## Resultado 1 — el límite de `rxre_boot` era real y queda cerrado

`1481` dejó escrito, y con razón, que el grafo de dependencias tiene **172
llamadas a `subprocess` que no son aristas** y que por tanto es una **cota
inferior** del acoplamiento real. Ese límite estaba medido y sin cerrar.

Ahora está cerrado, y el resultado **contradecía** la preocupación que lo motivó:

```
llamadas a subprocess en el arbol      176
  con programa literal                   70
  SIN programa identificable            106
  invocan HERRAMIENTAS NUESTRAS          72     <-- todas en NIVEL 3 (TABLA)
  invocan binarios EXTERNOS              57
```

**Ninguna de las 70 llamadas con programa literal invoca a una herramienta de
este proyecto.** Los 9 programas distintos que aparecen son todos externos:
`git` (29), `gcc` (5), `objdump` (3), `bash`, `nm`, `grep`, `sha256sum`,
`readelf`, `python3`.

Y las **72 invocaciones entre herramientas del proyecto no están en ninguna
llamada a subprocess**. Están en `run_all.py`, que las nombra en una **tabla**:

```python
tools = [
    ("cierre de includes de gfx_v8_0.c",
     ["include_closure.py", "gfx_v8_0.c", "--opcodes"], 0),
    ...
```

y luego itera: `run(label, ["python3", os.path.join(HERE, a[0])] + a[1:], ...)`.

El nombre está en un literal — **visible** — pero el `argv` que se ejecuta se
construye con `a[0]`. **Ningún `ast.walk` lo ve, y ningún patrón de texto
tampoco**: la lista y el uso están a treinta líneas de distancia.

> una lista de herramientas es un grafo escrito como tabla

**Y hay un oráculo para comprobar que la tabla no miente:** las 72 invocadas
**existen en disco**. Las 72. Una tabla que invoca una herramienta inexistente
sería un error de la tabla, y eso se puede comprobar sin ejecutar nada.

## Resultado 2 — y el dato que corrige una conclusión de `1505`

`1505` dejó 45 herramientas clasificadas como «puede escribir delegando» por
tener llamadas a `subprocess`, y la preocupación implícita era que delegaran en
hermanas que escriben en el árbol.

**La medición dice que no.** De las 70 llamadas con programa literal, **cero**
apuntan a una herramienta de este proyecto: todas van a binarios externos. Las
72 invocaciones entre hermanas están en tablas, y ahí el dato es otro.

Eso **no cierra** la preocupación —delegar puede ser por tabla, por flujo de
datos o por un módulo que no se lee— pero la acota a lo que se puede mirar, y
dice dónde mirar.

### La clase que queda sin medir, y se declara

**NIVEL 4: destino que llega por flujo de datos a través de variables sin `with`
ni lista resoluble.** No se mide, y se declara `NOT_DETERMINED` en el informe.
No es un cero: es un `NOT_DETERMINED`.

## Resultado 3 — el campo de la frontera tenía el precedente escrito, y lo usé

Al declarar las 4 herramientas de las 47 que `run_all` invoca y que estaban sin
contrato (`causal.py`, `citecheck.py`, `scopeguard.py`, `xref.py` — las mismas
cuatro que `toolkit.py` reportaba como `SIN CONTRATO`), incluí
`TOUCHES_INTEGRATED`, como ya lo hacen las 30 de `revkit` y las 36 de `tools/`.

**Y `toolkit.py` rechazó su propio autotest entero:**

```
AUTOTEST FALLA:
   causal.py declara TOUCHES_INTEGRATED y el validador no lo conoce
   citecheck.py declara TOUCHES_INTEGRATED y el validador no lo conoce
   scopeguard.py declara TOUCHES_INTEGRATED y el validador no lo conoce
   xref.py declara TOUCHES_INTEGRATED y el validador no lo conoce
No se valida: el validador no supera su autotest.
```

Eso es una **regresión mía**, y la forma de resolverla importa más que el
número: `toolkit.py` ya tenía `CONTRATO_FLAGS` **exactamente para este caso**, con
el precedente escrito dos veces en su propio cuerpo — `EXIT_ON_SUCCESS` el
2026-10-03 y `WRITES_GPU` en el hallazgo 197, con el mismo texto sobre un campo
que el código leía y el validador no nombraba.

```
CONTRATO_FLAGS = CONTRATO_FLAGS + ["TOUCHES_INTEGRATED"]
```

Cuatro líneas. Reparado y medido por las dos vías:

| | sin el arreglo | con el arreglo |
|---|---|---|
| autotest | `AUTOTEST FALLA` | **`autotest OK`** |
| flags conocidos | — | **9** (antes 8) |
| contrato válido | — | **54/68** |

El cambio está en `08-ARQUITECTURA/tools/toolkit.py`, **31 líneas, todas
comentario más una** de código. Es el primer fichero de validación que modifica
esta sesión, y sólo porque medirlo lo volvió necesario: `1487` propuso esta
acción y la dejó **sin ejecutar** diciendo que su coste era «revisar los
contratos existentes». **El coste medido son cuatro líneas y un autotest que se
negaba a correr.**

### Y lo que el arreglo NO hace, dicho en el propio fichero

> reconocer un campo no es comprobarlo

El validador **reconoce** `TOUCHES_INTEGRATED` y **no lo comprueba**. Que
`TOUCHES_INTEGRATED=no` sea verdad es `NOT_DETERMINED` con un verificador que
todavía no existe: `rxre_frontier.py` mide el acceso a sysfs pero no lee ese
campo para juzgarlo. Declarar un campo sin verificador sería el mismo defecto
que el proyecto ya pagó dos veces.

## Procedencia

- `STATIC` — AST sobre 176 ficheros de `tools/`, `revkit/` y
  `08-ARQUITECTURA/tools/`. Sin ejecutar nada.
- `CROSS-CHECK` — las 72 invocadas se comprobaron una por una contra el disco:
  **72 existen, 0 no existen**. La lista `tools` de `run_all.py` se leyó dos
  veces, con un script propio y con el instrumento, y coincide.
- **El filtro de tablas necesitó tres versiones** y las tres están en el
  código, porque cada una enseñó algo:
  1. aceptaba cualquier tabla 2D → capturaba `[("0 == f(x, y)", "cond")]`
  2. exigía que *pareciera* un programa → seguían entrando `cond`,
     `pci_register_driver` y una ruta a un `.md`
  3. exigía que **resolviera** contra el árbol o contra los externos
- **Un vector exigía que toda fila de nivel 3 fuera del árbol** y falló con
  `rg`, `llvm-objdump`, `addr2line` y `pahole`. El fallo era del vector: una
  tabla que invoca un binario externo es una tabla de invocaciones tan legítima
  como otra.
- `EJECUCION` — sólo `toolkit.py`, que se ejecutó tres veces (con el fichero de
  `HEAD`, sin los 4 contratos, y con el arreglo). **Sin MMIO, sin TLB, sin
  insmod.** `GPU INTACTA`.
- Los 4 ficheros declarados **parsean**; `causal.py`, `citecheck.py`, `xref.py`
  y `scopeguard.py` **no tienen `--selftest` ni `--self-test`**, así que no hay
  vector propio que ejercitar: `rc=2` de argparse, que es «opción desconocida»,
  no un fallo.

## Dos notas de método

**La primera: el límite se cerró, y el resultado quitó la preocupación.**

`rxre_boot` declaraba 172 acoplamientos invisibles. Al medirlos, la mitad
resultan ser binarios del sistema y **cero** son entre herramientas. La
preocupación que motivó el límite era real en forma y **falsa en sustancia**, y
sólo se supo al medir. Un límite declarado y no medido es una invitación a
adivinar lo que hay detrás.

> un límite declarado y no medido invita a adivinar lo que hay detrás

**La segunda: rompí un validador y lo reparé siguiendo su propio precedente.**

Lo más rápido habría sido quitar `TOUCHES_INTEGRATED` de los 4 ficheros y
dejar el validador como estaba — tres líneas, ningún fallo. Eso habría dejado la
frontera **sin declarar justo en las cuatro herramientas que `run_all` ejecuta**,
que es donde más importa.

La alternativa correcta era la que el propio validador llevaba dos veces escrita
en su cuerpo: un campo que el código declara y el validador no nombra no es un
campo inválido, es un campo **pendiente**. Y el coste, que `1487` dejó sin
medir, resultó ser una línea de código.

*Medir el coste de una acción propuesta es lo que la convierte de propuesta en
acción.*
