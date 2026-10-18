# 1635 — `status: ok` NO ES UNA OPERACIÓN CERRADA — LOS OCHO PRINCIPIOS EJECUTABLES

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-ECO-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Qué impide que un `status: ok` se lea como «trabajo hecho»?
STATE=PROVEN
```

## EL HUECO

§105 termina en `UPDATE KNOWLEDGE`. Entre `BENCHMARK` y ese punto hay un
tramo que nadie cubre: **si la operación fue correcta**.

`status: ok` dice que el producer respondió. No dice que el resultado sea
*atribrible*. Una operación puede responder `ok` y ser irrecuperable: sin
`input_hash` nadie puede repetirla sobre la misma entrada. Con el mismo
`status`.

Los ocho principios estaban en un `.MD` de 8 párrafos. El encargo los pedía
«en operaciones reales, no en documentación». Documentados son ocho párrafos
que nadie ejecuta.

## LO QUE SE HIZO

`backends/adapters/ocho_principios.py`: ocho funciones con **entrada, salida y
fallo**, y un `gate()`. Cada una devuelve `ok`, `violation` o `not_proven`, con
su `porque` — porque un veredicto sin razón no es revisable.

Se expone como `./rxre audit --desde-fichero <env.json>`, **separado** de
`run` por una razón operativa: auditar sin ejecutar es barato, y cuando es
barato deja de usarse. Separado, obliga a invocarlo **después** de una
operación real.

## LAS TRES PROPIEDADES QUE LO HACEN UN MECANISMO Y NO UN TEXTO

### 1. Sin evidencia, no hay aprobación

```python
if viol:      estado = "violation"
elif no_prov: estado = "not_proven"     # NO "ok"
else:         estado = "ok"
```

La asimetría es el mecanismo. Si un principio ausente devolviera `ok`, el
sistema se autoabsuelve por omisión — el fallo de forma más común en un
sistema de principios. Hay un test que lo comprueba explícitamente
(`ocho.asimetria.no_absuelve`).

### 2. No promedia

7/8 con 1 en violación **no** es 7/8 con 1 sin probar. Un promedio borra la
diferencia que importa, así que el resumen son tres conjuntos disjuntos
(`cumplen` / `en_violacion` / `sin_probar`) cuya suma es 8.

### 3. Cada principio puede fallar de verdad

No basta con que existan: hay que verlos ponerse rojos. Cada test toma una
operación **real** y la degrada de una forma concreta.

| Principio | Degradación | Detecta |
|---|---|---|
| CUERPO | `precheck.ok = False` con resultados presentes | `violation` |
| MENTE | `limitations = []` | `violation` |
| ALMA | valor `{}`: ni patrón ni sujeto | `violation` |
| TIERRA | `provenance.input_hash = ""` | `violation` |
| FUEGO | `normalizador = ""` | `violation` |
| AIRE | total 4000, lista 3, sin flag de truncado | `violation` |
| AGUA | `persistido = False` | `violation` |
| ETER | sin coincidencias: dato aislado | `not_proven` |

Y el otro extremo, que es el que importa igual: **AIRE acepta un truncado
declarado**. `not_proven` no es `violation`; exigir que todo esté probado
haría el sistema inútil.

## MEDIDO END-TO-END

Sobre la operación real de `source.ast_parse` sobre `amdgpu.h`:

```text
status: ok  |  operacion_cerrada: True   |  los ocho principios pasan

  degradada   status: ok  |  operacion_cerrada: False  |  TIERRA
  (sin hash)                                        provenance sin input_hash:
                                                     no se puede repetir

  degradada   status: ok  |  rc=2                      |  AIRE
  (truncada)                      4000 declaradas, 3 publicadas, sin flag
```

Las tres líneas tienen el **mismo `status: ok`**. Solo el gate las separa. Eso
es el hallazgo: el status del producer es insuficiente, y ahora hay algo que
complementarlo.

## LAS LECCIONES QUE INTERVIENEN EN OPERACIONES REALES

`backends/lessons.py`: siete lecciones, cada una con su regla, su **medida**,
su aplicación y su coste. Y `contraviene()` se **ejecuta** en
`ts_ast.parsear()`: si el adapter repite un patrón ya pagado, devuelve
`blocked` con el número de lección.

Un módulo de lecciones que solo se lee no evita nada.

### El guard动人的: un falso positivo que hubo que arreglar

Primera versión de `contraviene()` buscaba el texto `[:50]`. El guard se
disparó **sobre el propio adapter ya corregido**, que contiene
`coincidencias[:50]` justamente porque publica `n_coincidencias` al lado.

**30 tests en rojo** por un guard que confundía *mención* con *uso*.

El guard ahora distingue «esto recorta sin decir nada» de «esto recorta y lo
dice», exigiendo que el total esté presente:

```text
  recorte sin total       -> [5, ...]
  recorte CON total (ok)  -> [] sin violaciones
  filtro solo por forma   -> [4, ...]
  path con .. sin abspath -> [2, ...]
```

La lección 8 es esa, y se escribió porque un guard que no sabe cuándo callar
es peor que no tener guard: bloquea el trabajo legítimo.

## LAS SIETE LECCIONES, EN UNA LÍNEA CADA UNA

```text
L1  un upstream declarado puede no existir          (ls-remote, o es disculpa)
L2  un path mal resuelto parece un artefacto ausente (imprime la ruta ABSOLUTA)
L3  un producer tiene que poder rechazar lo que pide (umbral = hueco MEDIDO)
L4  'es una hoja' NO es 'es código' en tree-sitter   (filtra por TIPO)
L5  un total truncado sin declarar es error de magnitud
L6  una aserción de test puede ser FALSA, no un bug del código
L7  un `ok` del producer no es una operación cerrada
```

### L3 en detalle, porque el umbral tiene historia

El adapter devolvía `ok` parseando un `.py` con gramática de C. El umbral no
se inventó: se midió el hueco.

```text
  amdgpu.h (C real)    nodos=7066  ERROR=10  ratio=0.0014
  fichero .py          nodos=15    ERROR=1   ratio=0.0667
  fichero .md          nodos=29    ERROR=3   ratio=0.1034
```

`0.01` está en medio del hueco, con margen de ~7× a un lado y ~5× al otro.
Subirlo a 0.05 dejaría pasar el `.py`; bajarlo a 0.05 rechazaría C con macros
exóticas.

### L6 en detalle, porque una IA se engaña con ella

El test afirmaba que el AST daría **menos** que `grep` sobre `amdgpu.h`. Dio
**igual** (11 = 11), y parecía que el caso sintético mentía.

No mentía. **El adapter estaba mal** (L4). Y el orden de los filtros importó:
excluir solo comentarios hacía pasar el caso sintético mientras `amdgpu.h`
seguía dando 11, porque la línea 54 es un `preproc_include`, no un comentario.

*Arreglar* el código para satisfacer una expectativa equivocada deja el
defecto real intacto **y** añade una restricción falsa. La regla: antes de
«arreglar», comprobar que la expectativa era correcta.

## LO QUE ESTO NO ES

- **No es un score.** No hay número único, y añadirlo sería exactamente el
  defecto que este módulo evita.
- **No planifica.** No dice qué investigar. Audita lo que ya se ejecutó.
- **No sustituye al juicio.** `operacion_cerrada: true` significa «se cumplen
  las ocho condiciones que RXRE se exige», no «el resultado es correcto». Lo
  segundo sigue necesitando un discriminante.
- **No cubre el proyecto entero.** Se ejecutó sobre `source.ast_parse`. Las
  25 capacidades anteriores no están auditadas. `NOT_DETERMINED`.

## ESTADO

```text
CLAIM=status:ok implica operación cerrada
STATE=REFUTED (tres envelopes con status ok, veredictos distintos)

CLAIM=los ocho principios pueden intervenir en operaciones reales
STATE=PROVEN (39 checks; cada principio se pone rojo ante su degradación)

CLAIM=las lecciones mejoran decisiones futuras
STATE=PROVEN para L1-L7 (guard ejecutado en ts_ast.parsear)
STATE=NOT_DETERMINED para L8 (el falso positivo se corrigió, no se midió
       cuántas veces habría evitado)
```
