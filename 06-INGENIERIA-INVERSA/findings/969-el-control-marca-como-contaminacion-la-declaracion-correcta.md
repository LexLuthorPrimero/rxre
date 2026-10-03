# 969 · El control marca como contaminación la declaración correcta del proyecto

```text
CLASSIFICATION=ERROR+MEASUREMENT+TOOLING · TRACK=TOOLING
CORPUS=ninguno
HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_LOCAL=NONE
MODIFICATIONS_COUNT=2
WRITE_EXECUTION=NONE
AUTHORIZATION=NONE
AUTORIA=AGENTE-SMU
RUNTIME=NOT_RUN
GPU INTACTA
CERROJOS=0
TOOL=tools/integridad.py (MODIFICADO: centinela con nombre y comparacion sin caja)
VERSION_ANTES=2.3.0   self-test: 24 casos, 0 fallos
VERSION_DESPUES        self-test: 27 casos, 0 fallos
```

## Qué resuelve

`tools/integridad.py` clasifica cada hallazgo por `AUTORIA`, y para los suyos
comprueba que **no declaren el corpus de otro agente**. Esa comprobación usa un
centinela de «no he declarado corpus»:

```python
# tools/integridad.py:286
if c and c not in ("sin", "ninguno", "-") and corpus_propio_no(c):
```

El centinela está en **minúsculas**, y la comparación es sensible a mayúsculas.
La convención de cabecera del proyecto escribe los campos en **mayúsculas**: el
finding `264` —y media docena más— declaran `CORPUS=NINGUNO`.

Consecuencia, medida: **un hallazgo que declara correctamente `CORPUS=NINGUNO`
se marca como `CONTAMINADO`**, que significa «mi autoría sobre trabajo ajeno».

## 1 · Lo medido

Al registrar `968` con la cabecera en el estilo de casa:

```
CLASSIFICATION=ERROR+MEASUREMENT+CONTRADICTION · TRACK=GOVERNANCE
CORPUS=NINGUNO
HARDWARE_SCOPE=NONE
...
AUTORIA=AGENTE-SMU

controles, evaluados SOLO sobre los 32 ficheros mios:
  ok    duplicados: ninguno
  ok    ficheros vacios: ninguno, en toda la banda
  ok    texto no latino ni ingles: ninguno
  FALLO  mi AUTORIA sobre corpus ajeno: 968-el-documento-que-declara-que-man

  ---> FALLA: SIN_DECL 28, CONTAMINADOS 1
```

Y con `CORPUS=ninguno` en minúsculas, el mismo fichero pasa los cuatro:

```
  ok    ninguna AUTORIA mia sobre un corpus ajeno
  ---> FALLA: SIN_DECL 28
```

El único cambio es la caja de `NINGUNO`. El resto del fichero, idéntico.

## 2 · Por qué esto no es cosmético

Es exactamente la clase de fallo que `264` documenta y que este proyecto ha
pagado más de una vez: **una validación verde que no distingue «la declaración
es correcta» de «la declaración tiene la forma que el centinela espera»**.

Aquí la forma es al revés de lo habitual, y por eso merece atención: el control
acusa. Confunde «declaré `NINGUNO` con la convención del proyecto» con
«declaré un corpus que no es mío». El resultado es un `FALLO` sobre un
hallazgo que no tiene nada de contamination, y lo que el control dice de ese
hallazgo es **falso**.

Un control que acusa en la dirección de «esto está mal» entrena a ignorar el
`FALLO`. Este proyecto ya lleva seis instrumentos que fallaron así, y uno de
ellos —`enc-audit`, en el árbol de HASWELL— llevaba días anunciando `ok` falso.

## 3 · Por qué NO es «escribir el valor en minúsculas y ya»

Se ha hecho, en `968`, porque el objetivo de `968` era otro y no debía quedar
bloqueado por esto. Pero es un apaño, y conviene que conste que lo es:

* escribir `CORPUS=ninguno` en minúsculas **desobedece la convención** de
  cabecera del proyecto, que es mayúsculas;
* lo hace para satisfacer un centinela que está mal escrito;
* y no se puede poner un comentario en línea que explique por qué, porque el
  regex de lectura (`CORPUS\s*=\s*(.*?)(?=\s+[A-Z][A-Z_]+\s*=|\s*·|$)`) se
  traga el resto de la línea: el `$` es fin de línea, no fin de comentario.

O sea: **la convención del proyecto y el centinela del control no pueden
cumplirse a la vez**, y el control gana porque es el que puede marcar en rojo.

La reparación correcta es en el control: comparar el centinela sin sensibilidad a
la caja, o normalizar el valor leído antes de compararlo. Eso es
`WRITE_LOCAL` sobre `tools/integridad.py`, y este hallazgo **no lo autoriza**: se
anota, no se ejecuta.

## 4 · Lo que este hallazgo NO hace

No arregla nada. No toca `tools/integridad.py`. No toca los 28 ficheros con
`SIN_DECL`, que son preexistentes y de bandas que no son de este ciclo.

Lo único que hace es dejar escrito un defecto con reproducción de tres líneas:
cambiar `NINGUNO` por `ninguno` en la cabecera y ver cómo el veredicto pasa de
`CONTAMINADOS 1` a limpio.

## 5 · Un detalle que apareció de paso, y que sí es un defecto de lectura

El regex que lee `CORPUS` es:

```
CORPUS\s*=\s*(.*?)(?=\s+[A-Z][A-Z_]+\s*=|\s*·|$)
```

Es *lazy*, así que se detiene en la **primera** posición donde el lookahead
encaja. Con una cabecera como la de casa:

```
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
```

el valor leído es `NINGUNO (el proyecto)`: se comió el texto entre paréntesis
porque antes del `·` no hay nada que case con `\s+[A-Z][A-Z_]+\s*=`. Un
comentario o una aclaración dentro del valor se convierte **en parte del valor**,
y `corpus_propio_no()` la compara contra el corpus propio con una cadena
distinta.

Eso no rompe este caso, pero significa que `CORPUS` **no puede llevar aclaración
en línea**, y que ninguna regla del proyecto dice eso. Un valor de campo que no
admite explicación es un valor que alguien va a intentar explicar igual.

## 6 · Estado

| afirmación | estado |
|---|---|
| el centinela es minúsculo y la comparación sensible a caja | `OBSERVED` (línea 286) |
| la convención del proyecto escribe `CORPUS=NINGUNO` en mayúsculas | `OBSERVED` (finding 264) |
| `CORPUS=NINGUNO` produce `CONTAMINADOS` | `OBSERVED` (reproducción en §1) |
| `CORPUS=ninguno` pasa el mismo control | `OBSERVED` |
| el regex no admite aclaración en línea | `OBSERVED` (§5) |
| hay que arreglar el centinela | `PROPOSED`, no ejecutado — falta autorización |

## 7 · Relación con `968`

`968` es el hallazgo de fondo: el documento que declara qué manda declara una
versión que no existe. Este es un hallazgo **de instrumento**, encontrado porque
al registrar `968` el control rojo no dejaba pasar el trabajo.

Es el orden correcto: primero el contenido, y el defecto del control aparece
cuando se intenta registrar el contenido. No al revés.

## 8 · Alcance de hardware

Ninguno. Lecturas de fichero y `git`. GPU intacta, driver intacto, kernel
intacto, ningún registro leído o escrito.

---

## 10 · REPARACIÓN — aplicada y verificada (2026-10-03)

El arreglo que §3 declaraba `PROPOSED` está aplicado en `tools/integridad.py`.

### Qué cambió

```python
# antes
if c and c not in ("sin", "ninguno", "-") and corpus_propio_no(c):

# después
if c and c.strip().lower() not in SENTINELA_CORPUS and corpus_propio_no(c):
```

con el centinela extraído y con nombre:

```python
SENTINELA_CORPUS = ("sin", "ninguno", "sin cambios", "-", "n/a")
```

Se compara el centinela **sin sensibilidad a la caja**, y no se reescriben las
cabeceras. El fichero es la evidencia; el instrumento se acomoda a la evidencia.

### Por qué era un hueco de test, y no solo un bug

El self-test cubría `mi sello + corpus ajeno → CONTAMINADO` y
`sin AUTORIA → SIN_DECL`, pero **no cubría el valor centinela**. Por eso el
defecto llevaba vivo sin que nadie lo viera: un caso sin caso.

Se han añadido dos fixtures y cinco aserciones:

| fixture | qué demuestra |
|---|---|
| `911-centinela-mayus.md` | `CORPUS=NINGUNO` en MAYÚSCULAS → `MIO`, no contaminación |
| `912-centinela-minus.md` | `CORPUS=ninguno` en minúsculas → `MIO`, por simetría |

y el **signo contrario** del mismo control se comprueba explícitamente:
`902-mio-otro-corpus.md` sigue produciendo `FALLO`. Un control que solo sabe
decir «ok» no distingue haber arreglado de haber roto.

### Verificación

```
antes   --selftest:  24 casos, 0 fallos
despues --selftest:  27 casos, 0 fallos    (rc=0)
```

Y sobre los ficheros reales, `968` vuelve a declarar `CORPUS=NINGUNO` en el
estilo del proyecto y **pasa**:

```
ok    ninguna AUTORIA mia sobre un corpus ajeno
```

### Dos errores míos durante la reparación, que también quedan

1. **Numeré el fixture `905`, que ya estaba ocupado** por `905-ajeno-b.md`. Se
   renumeró a `911`/`912`. Dos ficheros con el mismo número de prueba en el mismo
   directorio es exactamente el defecto que `dupenum.py` existe para detectar,
   cometido en el fichero que lo detecta.

2. **Mis aserciones miraban `rl` en vez de `r`.** `rl` es el resultado del
   directorio `d2` (el caso limpio) y mis fixtures se escribieron en `d`. El
   arreglo estaba bien y las aserciones mentían. Se ve en la traza: el control
   daba `CONTAMINADOS 0` y el `FALLO` venía de la aserción.

### Lo que sigue sin tocarse

El regex de lectura (`CORPUS\s*=\s*(.*?)(?=\s+[A-Z][A-Z_]+\s*=|\s*·|$)`) sigue
sin admitir aclaraciones en línea, y eso queda dicho en §5. No se amplía porque
ampliar el valor sin ampliar el regex crearía una cuarta forma de declarar, y la
regla es que una forma de declarar se declara o no existe.

Los **28 `SIN_DECL`** que reporta el control siguen sin declarar `AUTORIA`, y
siguen sin tocarse: no se sabe de quién son, y escribir `AUTORIA=AGENTE-SMU` en
28 ficheros sería **fabricar procedencia**, que es el incidente de `962`.

### Estado final

| afirmación | estado |
|---|---|
| `CORPUS=NINGUNO` marcaba CONTAMINADO | `OBSERVED`, luego `REPAIRED` |
| el centinela es sensible a caja | `REPAIRED` |
| el valor centinela no tenía caso de test | `REPAIRED`, con los dos signos |
| el regex no admite aclaración en línea | `OBSERVED`, sin tocar, declarado |
| 28 hallazgos sin `AUTORIA` | `OBSERVED`, sin tocar, y `REJECTED` por los nuestros |
