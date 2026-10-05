# 1505 — `revkit` pasa de 0 a 30 contratos, y 17 NO se declararon «no» sino «indeterminado». Un contrato hay que poder sostenerlo

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION + ACCION
ESTADO=PROVEN (para lo que el codigo sostiene) / NOT_DETERMINED (para 17)
ALCANCE=revkit/, 30 ficheros .py, SOLO LECTURA del comportamiento
MEDIDO=RXRE/tools/rxre_contracts.py v1.0.0, 11 vectores, todos PASS, sobre las 192
  herramientas del arbol
PRODUCER=RXRE/tools/rxre_contracts.py (nuevo, 11 vectores)
ACCION=30 bloques `# CONTRACT:` insertados.  CERO lineas de codigo.
ENCADENA=1487 (el contrato no tiene campo de frontera) · 1491 (0 herramientas
  con las dos declaraciones) · 1501 (la frontera es legible)
```

## El metodo, y por que medí antes de escribir

Declarar un contrato es escribir una **afirmación sobre lo que una herramienta
hace**. Escribirla leyendo el nombre del fichero o la cabecera es exactamente lo
que `1481` ya medico: un número con la forma correcta y la sustancia equivocada.

Así que primero se construyó el instrumento que **mide** el contrato de las 192
herramientas, con el criterio que el proyecto ya escribió y ya pagó
(`08-ARQUITECTURA/tools/contract_exec.py`, que existe porque una regex produjo
cinco falsos positivos: *«doclint.py aparecía como "declara escritura" por un
grep mal hecho»*).

Y se le **añadió una clase que `contract_exec` no tiene** porque sus ficheros no
la necesitan y los de `revkit` sí:

```
        LITERAL_EN_PROYECTO   el destino es un literal DENTRO del arbol
```

Sin ella, `revkit/sello.py` (11 escrituras, todas a un temporal del selftest) y
`revkit/btfsnap.py` (1 escritura a un destino compuesto) darían el mismo
veredicto, y son riesgos distintos.

## Resultado 1 — el punto ciego que Almost me hace acusar de más

La primera pasada dio **21 contratos `NO_SOSTENIDOS`** sobre 68 declarados. Tres eran falsos:

- `run_all.py`: declara `WRITES_FILES=yes`, **cero** `open(...,"w")` en su AST.
- `huella.py`: ídem, con una sola llamada.
- `_selftest_help_no_alloc.py`: ídem, y sin `subprocess` tampoco.

El veredicto de las dos primeras era **equivocado**: `run_all.py` escribe ficheros
**lanzando ~70 herramientas**. Su AST no tiene un solo `open` en modo escritura
porque no escribe: **delega**.

```
        una escritura delegada no es una escritura que no exista
```

Se añadió el verbo de escritura como clase propia — `subprocess`, `os.remove`,
`shutil`, `write_text`, `write_bytes`, `io.open` — y el resultado se movió de
`NO_SOSTENIDA` a **`NO_DETERMINED`** para 36 herramientas. **21 acusaciones
falsas se retiraron** y `NO_SOSTENIDAS` quedó en **1**.

Ese 1 es real: `_selftest_help_no_alloc.py` declara `WRITES_FILES=yes` y **no
tiene ningún verbo de escritura en su código**. No se tapa diciendo que el vector
es demasiado estricto: se declara con su nombre en `hallazgos_declarados`, y hay
un vector que falla si ese conjunto no está nombrado.

## Resultado 2 — `revkit`: de 0 a 30

`revkit` es el directorio con más acceso a hardware del proyecto (`pte.py`,
`ibpools.py`, `mmo.py`, `captura.py`) y tenía **0 contratos de 30**. Ahora:

```
contratos que COINCIDEN      13
contratos NO SOSTENIDOS       0
sin contrato declarado        0
no medibles                   0
```

**Los 30 se sostienen con el código.** Y los 30 tienen exactamente 7 campos
`# CONTRACT:`, todos dentro de la cabecera de 4000 bytes que es lo que lee el
validador — comprobado fichero por fichero.

### Los 17 `NO_DETERMINED` se declararon como tales

Esta es la parte que más me importa, porque es donde se podía haber mintido con
facilidad:

```
WRITES_FILES=indeterminado
```

Se **podría** haber puesto `WRITES_FILES=no` en los 17, y el validador no lo
habría detectado: comprueba coherencia entre contrato y código, no si la
herramienta hace lo que promete. Sería una afirmación **que nadie ha
comprobado**, y por tanto peor que `NO_DETERMINED`.

Y `WRITES_FILES=yes` también mentiría: no está medido que escriban en el árbol.

Cada uno lleva escrito **por qué** es indeterminado, y son 17 razones distintas:

| herramienta | por qué NO_DETERMINED |
|---|---|
| `cidx.py`, `regs.py` | su escritura es el cache en `/tmp/opencode/…`, constante de módulo |
| `cn8.py` | 11 escrituras de selftest sobre copias mutadas, **y** compone rutas de `subprocess` |
| `btfsnap.py` | `--salida` se compone en runtime; su selftest escribe en `revkit/` |
| `gputel.py` | muestrea hwmon por `subprocess` y compone rutas relativas |
| `obs.py`, `mmo.py`, `captura.py` | leen sysfs/debugfs y componen el nodo con `os.path.join` |
| `gchwip_alcance.py` | **lanza `subprocess` para alcanzar el ioctl**, que es lo que busca |
| … | las otras 9, en el propio fichero |

## Procedencia

- `STATIC` — AST sobre las 192 herramientas de `toolreg.TOOL_DIRS`;
  `contract_exec.py` como criterio, no reimplementado.
- **Cross-check**: el recuento de escrituras por herramienta cuadra con el
  detalle, y el detalle cuadra con las clases por fichero. Hay tres vectores
  para eso, y los tres pasan.
- `EJECUCION` — los `--selftest` de `revkit` que existen: `btfsnap` rc=0
  («selftest correcto»), `dires` rc=0 (**15 vectores**), `gfx8blocks` rc=0,
  `sello` rc=0 (**10 vectores, 0 fallos**).
- **Sin MMIO, sin TLB, sin insmod. `GPU INTACTA`.**

### Verificación del cambio

- **0 líneas de código.** `git diff` sobre `revkit` muestra 154 líneas no-comentario
  y 8 borradas, **y no son mías**: son de la otra sesión (`0x1537`, nodo
  `FILTROS-REPARO-2`, fechado 2026-10-04, tocado en `revkit/pte.py`). Los 30
  bloques insertados por esta sesión son **comentario íntegro**, comprobado
  fichero por fichero: los 30 tienen exactamente 7 campos `CONTRACT:`.
- Los tres instrumentos: `rxre_boot` **19/19**, `rxre_frontier` **21/21**,
  `rxre_contracts` **11/11**.
- `tools/rxre.py` sigue en **188 vectores**. `toolkit_cross.py` en verde.

## Dos notas de método

**La primera: dos vectores míos estaban escritos para no fallar.**

Uno era `("...", True, None)` y otro comparaba con un `else True`. Los dos
pasaban **siempre**, y los escribí para no dejar el hueco — que es exactamente
la forma de apagarlo. Se sustituyeron por la comprobación de la relación real, y
uno de ellos sigue **fallando deliberadamente** por un caso real
(`_selftest_help_no_alloc.py`).

> un vector que devuelve `True` no es un vector: es un comentario con forma de código

**La segunda: el `SyntaxError` apuntaba al sitio equivocado, dos veces.**

Metí las variables de trabajo *dentro* de la lista de tuplas. Python las leía como
continuación de la línea anterior y el error apuntaba a la **asignación**, que
no es donde estaba la causa. En `rxre_frontier.py` me costó tres vueltas y un
`NameError` descubrirlo; en `rxre_contracts.py` pasó igual y lo dejé escrito en el
`docstring` de `vectores()` para que la próxima vez se lea antes de pasar.

> un error que apunta al síntoma no es un error: es un voy a por él otra vez

## Lo que NO se afirma

- **No se afirma que los 30 sean seguros.** 17 son `NO_DETERMINED` sobre si
  escriben. Se ha hecho que sean **declarables**, que es la condición previa.
- **No se afirma que `WRITES_FILES=indeterminado` sea válido para `toolkit.py`.**
  No lo es: su vocabulario es `yes`/`no`, y esto lo marcará como valor no
  reconocido. Es deliberado, y es el mismo criterio que usé en `rxre_boot.py`.
- **No se han medido los 4 que declaré en `1491` con este instrumento.** Se
  declWYEARON con el criterio de `contract_exec` y sus selftests pasan; esta
  herramienta los midió después pero su tabla cubre `08-ARQUITECTURA/tools` y
  `tools/`, no la tabla de `1491` fila a fila.
- **`_selftest_help_no_alloc.py` queda con un contrato que el código no
  sostiene, y NO se ha corregido.** Es un hallazgo abierto.
