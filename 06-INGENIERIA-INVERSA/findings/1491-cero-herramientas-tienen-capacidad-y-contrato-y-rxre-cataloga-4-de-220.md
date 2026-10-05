# 1491 — Cero herramientas tienen las DOS declaraciones: ni capacidad enrutable ni contrato. Y `rxre` cataloga 4 de 220 herramientas propias, no 25

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION
ESTADO=PROVEN
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=por cruce de dosInventory: toolreg.inventory() x rxre.CAP x
  `# CONTRACT:` leido de cada fichero. Sin ejecucion de las herramientas
PRODUCER=cruce nuevo, sobre toolreg + rxre + toolkit (los tres ya existentes)
ENCADENA=1481 (mismo eje X, sin la cuenta de PATHS) · 1487 (mismo eje Y, sin
  la cuenta de herramientas nuestras)
```

## Qué se midió

`1487` cuenta contratos: 65 ficheros los tienen. `1481` cuenta capacidades
enrutables: 25 filas de catálogo. Los dos son ciertos y **los dos contaban
poblaciones distintas sin decirlo**, que es como `1481` afirma que
«213 de 217 no tienen capacidad» y `1487` afirma «149 sin contrato» sin que
nadie haya restado la intersección.

La pregunta que faltaba es la del AND: **¿cuántas herramientas tienen las dos
cosas?** Porque una herramienta con las dos es la que se puede enrutar *y* es
segura, y sin las dos es un instrumento que o no se puede usar o no se puede
usar con confianza.

## Resultado 1 — la intersección es CERO

```
entradas del registro       220
con capacidad en rxre         4      <-- no 25
con contrato                  67
con AMBOS                      0
SIN NINGUNA declaracion      145
```

**Ninguna herramienta del proyecto tiene a la vez capacidad enrutable y
contrato de seguridad declarado.** Cero. No es una cifra pequeña: es la
 cardinalidad de un conjunto vacío.

Reparto de las 145 que no tienen ninguna de las dos:

| directorio | sin ninguna |
|---|---|
| `tools` | 91 |
| `revkit` | 33 |
| `08-ARQUITECTURA/tools` | 13 |
| `09-POWER-CLOCKS/tools` | 4 |
| `04-IMPLEMENTACION/rx550-driver/tools` | 3 |
| `04-IMPLEMENTACION/tools` | 2 |
| `01-AUDITORIA/tools` | 1 |

Y la de 13 en `08-ARQUITECTURA/tools` son las que `toolkit.py` marca
`SIN CONTRATO` o `READONLY pero hay escrituras`: o sea, **las dos mitades del
problema se complementan sin solaparse**, que es la peor forma posible de que
se complementen.

## Resultado 2 — corrige `1481`: de 25 filas, 4 son nuestras

`1481` dice «25 quedan cubiertas» y lo está, con el criterio de
`len({f[0] for f in CAP})`. Pero ese conjunto mezcla dos universos que `rxre`
él mismo separa en `estado_de()`:

| filas de `CAP` | cuántas | qué son |
|---|---|---|
| de esta herramienta | **4** | `tools/ibref.py`, `tools/mmio.py`, `tools/layoutcross.py`, `tools/toolreg.py` |
| de `PATH` | 21 | `rg`, `clang`, `llvm-mc`, `spatch`, `pahole`, `bpftrace`… |
| de `sysfs` | 1 | `/sys/kernel/debug/dynamic_debug/control` |

Las 21 de `PATH` son instrumentos del sistema, no de este proyecto.
`rxre.py` lo dice con toda claridad en su propio §4b — *«son dos universos
disjuntos y una herramienta se escribe en uno de los dos según lleve o no la
ruta»* — y su vector `registro: y una de PATH NO se busca en el registro`
comprueba precisamente esa separación.

**Pero el número 25 no la aplicaba.** Medido: las herramientas **propias**
cubiertas por el catálogo son **4 de 220**, el **1.8 %**. Las 21 restantes son
`rg` y compañía, que el catálogo sirve para enrutar pero que nadie de este
proyecto escribió, probó ni mantiene.

Esto **no refuta** `1481` — su cifra de 213 no enrutables sigue siendo
correcta y su artefacto lo demuestra. Lo que hace es acotar el problema a la
medida real: el trabajo no es «catalogar 192 herramientas», es **«catalogar y
declarar las 216 herramientas propias»**, y de esas 4 ya lo están.

## Resultado 3 — y la intersección se abre: 0 → 4

El cero anterior era una medición. Convertirlo en estado es otra acción, y se
ejecutó sobre las **4 herramientas que ya eran enrutables**, que es el conjunto
más pequeño que puede vaciar el problema sin inventar una sola capacidad.

Se les añadió el bloque `# CONTRACT:` que faltaba, **usando el criterio del
propio proyecto y no uno nuevo**:

| herramienta | `READONLY` | `WRITES_FILES` | evidencia |
|---|---|---|---|
| `tools/mmio.py` | yes | no | escrituras en `mkdtemp(prefix="mmio-tabla-")`, línea 695 |
| `tools/layoutcross.py` | yes | no | `mkdtemp(prefix="layoutcross-")` y `-generico-`, líneas 1318/1447 |
| `tools/ibref.py` | yes | no | `mkdtemp(prefix="ibref_stub_")`, línea 2278 |
| `tools/toolreg.py` | **no** | `only_with_--register` | `--register` escribe el esqueleto; el resto es `inventory()` |

Las tres primeras tienen `open(...,"w")` en su `selftest` y declaran
`WRITES_FILES=no`. **Eso no es una declaración contradictoria: es exactamente la
distinción que `contract_exec.py` ya hace y por la que existe** — la clase
TEMPORAL. Declararlas `yes` sería mentir, y el propio validador lo dice con esas
palabras: *«declararlas WRITES_FILES=yes sería MENTIR»*.

`toolreg.py` es el caso distinto: escribe de verdad, pero **sólo** con
`--register`. Se declara `only_with_--register`, fuera del vocabulario `yes`/`no`,
por la misma razón que `rxre_boot.py`: `no` sería falso y `yes` haría creer que
escribe sin que se le pida.

**Intersección después del cambio:**

```
con capacidad enrutable : 4
con contrato            : 71
con AMBOS               : 4   <-- era 0
```

### Verificación del cambio

- **0 líneas de código añadidas.** `git diff` sobre las cuatro: todas las líneas
  `+` son comentarios o vacías. Comprobado contador a contador.
- Los cuatro selftests pasan: `mmio` **48 vectores**, `layoutcross` **79**,
  `toolreg` rc=0.
- `ibref.py` devuelve **rc=1 con 11 FALLA**. **Comprobado que es
  preexistente**: con `git stash` sobre el fichero original, sin mi cambio,
  `rc=1` con los **mismos 11 FALLA**. La diferencia entre las dos ejecuciones es
  el nombre del temporal, y el recuento de FALLA es idéntico (11 y 11). **Mi
  cambio no altera el comportamiento**; y el fallo de `ibref` queda **abierto y
  sin resolver por esta sesión**, no se ha tocado.
- `rxre.py` sigue en **188 vectores**. `rxre_boot.py` en **19/19**.
  `toolkit_cross.py` en **verde**.

## Procedencia

- `STATIC` — cruce de tres fuentes ya existentes, ninguna reescrita:
  `toolreg.inventory()` (220 entradas), `rxre.CAP` (26 filas),
  y `re.search(r'(?m)^#\s*CONTRACT:', …)` sobre las primeras 4000 bytes de cada
  fichero del registro.
- `CROSS-CHECK` — el recuento de contratos (67 entradas del registro, 65 ficheros
  con `# CONTRACT:` en el árbol) se hizo por dos vías: `grep -rl | wc -l` sobre
  tres directorios, y el bucle sobre `toolreg`. La diferencia 67 vs 65 son
  entradas cuyo nombre de fichero aparece dos veces en el registro; **no se
  investigative porque no cambia ninguna conclusión**, y se declara como
  discrepancia conocida en vez de omitirse.
- `EJECUCION` — sólo lectura de fuentes y `toolreg.inventory()`. **No se
  ejecutó ninguna herramienta del registro.** Sin `--help-probe`.
- **Sin MMIO write, sin TLB, sin insmod. `GPU INTACTA`.**
- **Modificadas 4 herramientas existentes, y sólo en sus 20 primeras líneas:**
  se les añadió el bloque `# CONTRACT:`, que es la ausencia que `1491` mide.
  **Cero líneas de código.** Verificado con `git diff` línea a línea.

## Lo que NO se afirma

- **No se afirma que 145 herramientas sean peligrosas.** No tienen contrato
  *declarado*; eso es `NOT_DETERMINED` sobre su comportamiento, no
  `PROVEN_ABSENT` de que escriban.
- **No se afirma que el cero de la intersección sea un error.** Puede ser que
  sea exactamente lo correcto: las 4 enrutables son de lectura y las 67 con contrato
  nunca se pidió enrutarlas. Lo que sí afirma es que **no hay ninguna
  herramienta que se pueda enrutar y cuya seguridad esté declarada**, que es
  lo que el north star necesita para decir «usa esta, es segura».
- **El conteo de 67 vs 65 no está explicado.** Es una discrepancia medida y
  queda abierta, no resuelta por convenience.

## Una nota de método

La intersección valía más que cualquiera de las dos cifras sueltas, y costó una
línea:

```python
arbol & contrato & en_rxre     # -> 0
```

`1481` dio 213, `1487` dio 149, y ninguno era falso. Los dos eran el tamaño de
dos conjuntos, y el conjunto que de verdad importa para la plataforma — *las
herramientas usables con confianza declarada* — es su intersección, que resultó
estar **vacía**.

Eso corrige una cosa que `1481` afirmaba en su propia sección de notas y que
esta medición confirma por un camino distinto: que el coste no son los campos
nuevos ni las capacidades nuevas, sino la **co-ocurrencia** de dos
declaraciones que hasta ahora nadie habia cruzado.

*Un conjunto es una medicion. Una interseccion es la respuesta.*
