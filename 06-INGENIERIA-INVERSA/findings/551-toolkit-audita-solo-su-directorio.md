# 551 · El auditor de contratos solo mira su propio directorio, y la excepción `AJENA` no tiene plazo

`CLASSIFICATION=TOOLING` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`

## Cuestión principal

`run_all` tiene un `FALLA` permanente: *contrato de las herramientas*. La
pregunta es qué significa `AJENA` y por qué una herramienta con contrato completo
cuenta y otra sin contrato no. Y de ahí sale otra: **¿quién audita a quién?**

## La regla, y está bien razonada

De `toolkit.py`:

> **LA REGLA: una herramienta que no está en git se REPORTA como ajena y NO cuenta
> para el código de salida.** En cuanto se commitea, pasa a contar normalmente. Se
> sigue **VERIFICANDO** igual.

Y el motivo está escrito, que es lo que la hace aceptable:

> Este directorio lo comparten varias sesiones, y una herramienta que otra sesión
> acaba de crear AUN NO ESTA COMMITEADA. Contarla como fallo haría que `run_all`
> se pusiera rojo por un fichero que nadie ha publicado todavía, y eso es
> exactamente como se aprende a ignorar el runner.

**Además tiene registrado un intento anterior fallido**, y esto es lo mejor del
fichero:

> EL PRIMER INTENTO USO LA EDAD DEL FICHERO (modificado hace más de dos minutos =
> estable) y fue un error. Una herramienta que otra sesión escribe, abre, corrige
> y abandona sin commitear pasa de "estable" en dos minutos. La edad no distingue
> "terminado" de "abandonado a medias".

Y tiene **autotest de la distinción** (`--selftest-ajenas`) con tres casos: un
fichero versionado cuenta como propio, uno no versionado como ajeno, y con
`--strict` el ajeno vuelve a reprobar. Con el motivo del control escrito:

> Sin el, la regla "lo que no está en git no cuenta" es una excepción que nadie
> puede comprobar: si `_en_git` devolviera False para TODO, el control devolvería
> 0 y no detectaría ni una herramienta sin contrato.

**Es una excepción deliberada, con control y con intento fallido documentado.**
No la llamo defecto. Lo que sigue es su alcance real, que es otra cosa.

## 1 · La excepción esconde 6 defectos ahora mismo

```
AJENA(1)  causal.py  citecheck.py  contradict.py    ninguna capacidad declarada
AJENA(1)  hdrmap.py  inst_closure.py  xref.py        declaran, pero 1 problema
FALLA(1)  aperture.py  doclint.py  findings_index.py  ipver_zero.py
          pm4_emit.py  scopeguard.py  struct_rw.py    -> SI cuentan
```

**Seis defectos de contrato verificados y visibles en la tabla, que no cuentan
para el código de salida.** Tres de ellos no declaran **ninguna** capacidad: sin
contrato no hay forma de comprobar ni qué escriben.

Y uno de los seis es **`citecheck.py`**, que es la herramienta que verifica las
citas. Su contrato no está declarado y su defecto no cuenta.

## 2 · La excepción no tiene plazo

Busqué un mecanismo de caducidad y **no existe**:

```
grep -niE "dias|antiguedad|plazo|deadline|expir" toolkit.py   -> nada
```

La edad del fichero se usó y se descartó a propósito. Correcto: la edad no
distingue terminado de abandonado. Pero si **no** hay edad y **no** hay plazo,
entonces **una herramienta puede nacer sin versionar y quedarse así para
siempre**, y sus defectos para siempre.

Eso no es un defecto del detector: es un **hueco de cierre**. El proyecto sabe
detectar; lo que no tiene es un mecanismo que obligue a cerrar.

## 3 · Y el auditor solo mira su propio directorio

Este es el dato que no esperaba:

```
08-ARQUITECTURA/tools:  46 de 49 rastreadas
tools/                   1 de 60 rastreadas
```

`toolkit.py` hace `os.listdir(HERE)`, y `HERE` es su propio directorio. Imprime:

```
herramientas en .../08-ARQUITECTURA/tools: 49
```

**No mira `tools/`, ni `RESEARCH/polaris12xl/tools`, ni `04-IMPLEMENTACION/tools`.**

De modo que la excepción `AJENA` **ni siquiera se aplica ahí**: esas herramientas
no están en la tabla, no son "ajenas toleradas", son **invisibles**. Y el
directorio con 60 herramientas tiene **59 sin versionar**.

El contraste con lo que ya existe: `cite_registry.py` cuenta **115** herramientas
en cuatro directorios. El que *cuenta* ve 115; el que *valida contratos* ve 49.

| | herramientas que ve |
|---|---|
| `cite_registry.py` | 115 en 4 directorios |
| `toolkit.py` | 49 en 1 directorio |

## Lo que esto NO dice

- **No dice que la regla `AJENA` esté mal.** Está razonada, tiene control y tiene
  documentado por qué se descartó la alternativa. Cambiarla sin más sería tirar
  un diseño pensado.
- **No son 59 herramientas rotas.** Son 59 herramientas **no auditadas**. La
  diferencia es la que separa `NOT_OBSERVED` de `PROVEN_ABSENT`, y aquí es
  exactamente la que importa: **no sé si sus contratos están bien porque no los
  he mirado**, y decirlo de otro modo sería inventar un resultado.
- No he ejecutado ninguna de esas 59 herramientas.

## Confounders

- **`_en_git` y `HERE`**: he leído el uso, no he auditado el validador línea por
  línea. `NOT_DETERMINED` si hay otro punto de entrada que sí las recorra.
- El recuento de `tools/` (1 de 60) es **mi medición**, no la del proyecto.
- `AJENA(1)` no distingue entre "sin contrato" y "contrato con 1 problema". En
  la tabla se ve por la columna de capacidades, pero el código no lo separa.
- No he mirado si `tools/` tiene su propio auditor de contratos.

## Clasificación

| afirmación | estado |
|---|---|
| la regla `AJENA` es deliberada, razonada y con control | `PROVEN` — el motivo está escrito |
| la edad del fichero se probó y se descartó a propósito | `PROVEN` |
| hay autotest de la distinción propia/ajena | `PROVEN` — `--selftest-ajenas`, 3 casos |
| 6 defectos de contrato no cuentan para el código de salida | `OBSERVED` |
| 3 de ellos no declaran ninguna capacidad | `OBSERVED` |
| la excepción no tiene mecanismo de plazo | `PROVEN` — nada en el fichero |
| `toolkit.py` solo recorre su propio directorio | `PROVEN` — `os.listdir(HERE)` |
| `tools/` tiene 59 herramientas sin versionar | `OBSERVED` — `git ls-files` |
| esas 59 no están auditadas | `OBSERVED` — no salen en la tabla |
| sus contratos están mal | **`NOT_OBSERVED`**, no `PROVEN_ABSENT` |
| `citecheck.py` es una de las no auditadas con defecto | `OBSERVED` |

## Desfalsificación

- **(a)** la regla es deliberada → refutable leyendo el comentario de `LA REGLA`.
  **Verificado.**
- **(b)** no hay plazo → refutable grepeando plazos/edades. **Verificado: nada.**
- **(c)** solo mira su directorio → refutable leyendo `HERE` y el `listdir`.
  **Verificado.**
- **(d)** 59 sin versionar → refutable con `git ls-files tools/`. **Verificado: 1.**

## UNLOCKS

- **La excepción está bien y aun así esconde seis defectos.** Una salvaguarda que
  no caduca no protege: solo difiere el problema. Detectar y cerrar son
  capacidades distintas, y el proyecto tiene la primera.
- **Una herramienta sin contrato no se puede auditar.** No es que falle el
  contrato: es que **no hay contrato contra el que fallar**. Tres de las seis
  ajenas están exactamente así, y una es `citecheck.py`, la que verifica citas.
- **El alcance del auditor es su propio directorio, y eso no se anuncia.** Un
  validador que solo se valida a sí mismo tiene el mismo punto ciego que
  cualquier otro.
- **Siguiente paso, y sale de aquí**: los dos recuentos —115 y 49— no pueden
  coexistir sin que uno diga qué le falta al otro. `cite_registry` ya cuenta los
  cuatro directorios y distingue CONFLICTO de COPIA; lo que falta es que
  `toolkit.py` pueda **declarar su alcance** y que el recuento diga
  "49 de 115, y estos 66 no los audita nadie". Un validador que dice qué no cubre
  es más útil que uno que parece cubrirlo todo.

## Evidencia

```
grep -n "os.listdir(HERE)" toolkit.py        -> 412, 426, 459
grep "herramientas en" toolkit.py            -> HERE = su propio directorio
git ls-files 08-ARQUITECTURA/tools | wc -l    -> 46 de 49
git ls-files tools/            | wc -l        -> 1 de 60
grep -niE "plazo|deadline|expir" toolkit.py  -> nada
grep "AJENA([1-9])" <salida>                  -> 6
grep "FALLA([1-9])" <salida>                  -> 7
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.---

# AÑADIDO A `551`: qué comprueba `toolkit.py` de verdad

Pregunta: ¿valida lo que la herramienta **declara**, o lo que **hace**?

## Las dos cosas, y la parte que puede no servir

```
scan_writes(path)   "Que patrones de escritura hay, por analisis de texto"
```

Regex sobre el **texto**: `open(...,'w'|'a'|'x')`, `['"]>['"]`, etc. Y luego
cruza: `READONLY` no puede tener escrituras.

Eso detectó mi mentira (`READONLY=yes` con `--fijar` escribiendo), y **no pudo
detectarla leyendo comentarios**. Así que hace las dos cosas: lo declarado y una
aproximación textual de lo hecho.

**Y la propia herramienta dice cómo de débil es esa parte:**

> Expresiones que delatan escritura. **Debilis por construccion** — no distingue
> "w" de "r+" bien, y no ve escrituras via **subprocess** — pero es lo que hay.

## El bucle, que es lo que importa

```
WRITES_SYSFS    si escribe en /sys      (tabla + --write)
```

- `runtime_obs.py` es la **única** herramienta que declara `WRITES_SYSFS=yes`.
- Lo que se verifica es **una tabla de escrituras con justificación** más el
  conmutador `--write`.
- **No se ejecuta nada.** No hay ninguna comprobación de que la tabla sea
  cierta.

Es decir: **la única herramienta que escribe en el hardware de esta placa está
validada por su propio comentario y por su propia tabla.** El validador que
debería impedir que una herramienta escriba en el hardware se apoya en que esa
herramienta **diga** que escribe.

Y a eso se le añade que su detector de escrituras:
- **no distingue `"w"` de `"r+"`** — un `r+` evade la comprobación
- **no ve escrituras por `subprocess`** — `subprocess.run(["sh","-c","..."])`
  evade la comprobación entera

## Por qué esto no es "el validador es malo"

El resto del diseño de `toolkit.py` es **cuidado y está razonado**: la excepción
`AJENA` con su motivo, el intento fallido de la edad registrado, el autotest de la
distinción propia/ajena, y ejemplos concretos de herramientas que declaran mal. Esto es
trabajo pensado.

El hueco es de un tipo distinto y muy concreto: **la capacidad más peligrosa es
la única que se verifica por declaración**. Todo lo demás —`READONLY`,
`WRITES_FILES`, `MUTATES_CORPUS`— se puede contrastar contra el texto porque
escribir un fichero deja una marca en el código. Escribir en `/sys` no deja
marca: el comentario es lo único que hay.

## Lo que esto NO dice

- **No digo que `runtime_obs.py` escriba de más.** No lo he ejecutado ni auditado
  su tabla. Lo que digo es que **nada fuera de su comentario lo contradice**.
- **No es un defecto del texto de `toolkit.py`.** Es un límite de lo que es
  posible verificar estáticamente, y está escrito. El defecto sería **no decirlo**
  en ningún sitio, que es lo que pasa.
- `WRITES_GPU=yes` lo declara el propio `toolkit.py`; no he seguido ese camino.

## Clasificación

| afirmación | estado |
|---|---|
| `toolkit.py` valida lo declarado **y** lo textual | `PROVEN` — `scan_writes` |
| su autodescripción admite `r+` y `subprocess` como huecos | `PROVEN` — comentario |
| `runtime_obs.py` es la única con `WRITES_SYSFS=yes` | `PROVEN` |
| `WRITES_SYSFS` se verifica con tabla + conmutador, sin ejecutar | `PROVEN` |
| la tabla de escrituras es veraz | **`NOT_OBSERVED`** |
| `runtime_obs.py` escribe más de lo que declara | **`NOT_DETERMINED`** |
| la regex confunde `r+` con lectura | `PROVEN` — declarado por la propia herramienta |

## UNLOCK

- **Verificar por declaración y verificar por ejecución son capacidades
  distintas, y solo la segunda sirve para lo que no deja marca en el código.**
  Escribir un fichero se ve en el texto; escribir en `/sys`, no.
- **Una herramienta con capacidad de hardware debería exigir una evidencia de su
  ejecución, no una tabla que ella misma escribe.** Es la diferencia entre
  `NOT_OBSERVED` y `CORROBORATED` aplicada al contrato, no al hardware.
- **Siguiente paso**: el coste de verificar `runtime_obs.py` de verdad es alto
  —requiere ejecutarla— y por eso `NOT_DETERMINED` es la respuesta honesta y no
  una tarea urgente. Lo que **sí** es barato y útil: que `toolkit.py` **diga en
  su salida** que las capacidades de hardware se verifican por declaración, para
  que quien lea `run_all` no las tome por lo mismo que `READONLY`, que sí se
  verifica contra el texto.