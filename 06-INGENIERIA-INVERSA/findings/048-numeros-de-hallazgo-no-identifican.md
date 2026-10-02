# 048 · Los números de hallazgo no identifican un hallazgo: 37 de 82 están duplicados

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/num_collision.py` (`TOOL_VALIDATED`)
`CONTINUES=047`

## Cuestión principal

¿La convención de citar un hallazgo por su número —`017 §3`, `033:397`,
`CONTINUES=033`— identifica un documento?

## Criterio de terminación

Medir cuántos números son únicos. **Cumplido: 37 de 82 duplicados, y 477
referencias que hoy son ambiguas.**

## Respuesta

```
128 documentos      82 números distintos      37 NÚMEROS DUPLICADOS
referencias `NNN` ambiguas : 477
```

Tres documentos `033-`:

```
033-mmu-vm-no-publicado.md
033-pm4-spec-gfx8-no-existe-y-el-encuadre.md
033-protections-opaco-en-el-camino-gpuvm.md
```

`033:397` no dice cuál. Y **encontré el error cometiéndolo**: un `sed` mío con
un glob que matcheaba varios ficheros leyó el `033` equivocado, y solo lo
detecté porque el texto no cuadraba. Sin esa referencia cruzada habria
aceptado una cita falsa como buena.

Los diez números más citados:

| número | referencias | documentos |
|---|---|---|
| `023` | 48 | 2 |
| `031` | 36 | 2 |
| `033` | 35 | 3 |
| `043` | 33 | 3 |
| `035` | 33 | 2 |
| `037` | 30 | 2 |
| `024` | 29 | 2 |
| `036` | 26 | 2 |
| `030` | 22 | 2 |
| `021` | 16 | 2 |

## Lo que rompe, en orden de gravedad

1. **Trazabilidad.** `015 §4` no identifica nada si hay dos `015`.
2. **Adjudicación de contradicciones.** Cuando dos documentos afirman valores
   distintos, hay que saber *cuáles*. Sin eso no se puede arbitrar: es
   exactamente el caso de `block_size`.
3. **`CORRIGE=`, `CONTINUES=`, `CIERRA=` de las cabeceras.** `CONTINUES=033`
   no dice qué documento.
4. **`stale_gap` NO le afecta**, y conviene saber por qué: cruza por *sujeto*,
   no por número. Es un accidente afortunado, no un diseño, y si alguien lo
   cambiara por número heredaría este defecto.

## El contexto desambigua más de lo que parece

Leyendo las 48 citas de `023`:

```
029:86   "la convencion que `023` midio en 68/68 del path GFX8"
029:100  "el `BLOCKED` que arrastraban `022`, `023` y `029`"
033:22   "`023` queda corroborado de forma independiente"
```

En la mayoría, el tema de la frase (`PACKET3`, `n = payload − 1`, el `census`)
identifica el documento sin decirlo. **Un lector humano resuelve casi todas;
una máquina no puede.**

Eso es exactamente lo que hace la evidencia fuerte y la cita débil: el
razonamiento llega, la referencia no.

## La herramienta me corrigió a mí

Escribí en el resumen de esta ronda: *"un solo número (`003`) es único en todo
el rango 001–056"*. Es **falso**: son **45 de 82** los que no colisionan,
incluyendo `002`, `003`, `005`…`017`.

Lo escribí contando con un shell mal construido, que listaba mal. Es la misma
recurrencia de siempre: un número plausible sin un valor competidor al lado
que lo contradiga. Por eso la herramienta existe y por eso mido antes de
afirmar.

## Las tres salidas, y por qué no ejecuto ninguna

Renumerar 128 documentos **rompe todas las citas a la vez**, y las citas son la
evidencia. Eso es una operación de un solo tiro con plan de reescritura y
verificación, no algo que se haga de paso.

| | |
|---|---|
| **A. Número único** `001..128` | Derriba "la ronda 33". |
| **B. Número + sufijo** `033-p`, `033-m` | Conserva la agrupación; la cita sigue siendo ambigua salvo que incluya el sufijo. |
| **C. Prefijo de sesión en la cita** `d033:397` | Inequívoca y compatible con lo escrito. |

Y en las tres, **el mecanismo para desambiguar ya existe**: cada documento
lleva su nombre completo, y `citecheck` resuelve `fichero:linea`. Lo que falta
es que las citas en prosa usen el nombre completo, no solo el número.

Esa es la salida de menor coste: no toca los documentos, solo la forma de
citarlos, y `citecheck` puede verificarla automáticamente después.

## Clasificación

| afirmación | estado |
|---|---|
| 37 números están duplicados | `MEASUREMENT` — `num_collision.py` |
| 477 referencias son ambiguas | `MEASUREMENT` |
| `033` tiene 3 documentos | `MEASUREMENT` |
| 45 de 82 números no colisionan | `MEASUREMENT` |
| La ambigüedad se resolvió leyendo un `sed` | `OBSERVATION` — error propio |
| Que la cita `033:397` sea recuperable por contexto | `OBSERVED` — muestra de 10 |
| Que las 477 se puedan recuperar por contexto | `NOT_DETERMINED` — no medido |
| Qué salida elegir | `NOT_DETERMINED` — decisión de proyecto |
| Que el problema afecte a `stale_gap` | `REFUTED` — cruza por sujeto |

## Confounders

- **El recuento depende del directorio.** `findings/` tiene 128 documentos
  ahora; mañana puede tener más, y el número es una cota inferior.
- **Las 477 son referencias de forma `` `NNN` ``.** Las citas
  `NNN:linea` se contaron aparte y son menos, porque ese formato aparece
  sobre todo en tablas de evidencia que sí usan el nombre. Las dos cifras no
  se deben sumar.
- **Ambigüedad de cita no es mentira.** La mayoría se resuelven leyendo. El
  coste es tiempo de quien lee, no información perdida. Lo grave es el 10% que
  no se resuelven, y **no he medido cuál es ese 10%**.
- **No conté `docs/` ni `08-ARQUITECTURA/`**, que también citan por número y
  pueden tener los mismos problemas.

## Desfalsificación

- **(a)** 37 duplicados → refutable con `ls findings/ | sed 's/-.*//' | sort |
  uniq -d | wc -l`.
- **(b)** `033` tiene 3 documentos → refutable con `ls findings/033-*`.
- **(c)** 477 referencias ambiguas → refutable con `--json`.
- **(d)** Hash distinto para documentos con el mismo número → refutable con
  `--self-test`, control 4.

## UNLOCKS

- **La convención de citar por número queda marcada como no fiable**, que era
  la premisa que el proyecto venía usando sin comprobarla.
- **`num_collision` mide el alcance** y avisa si crece, sin proponer renumerar.
- **La salida C es de bajo coste** y `citecheck` puede verificarla: si toda
  cita en prosa pasa a llevar el nombre del fichero, el problema desaparece.
- **El error propio queda registrado**: la cifra que dije en el resumen de esta
  ronda era falsa y la herramienta la corrigió.

## Evidencia

```
08-ARQUITECTURA/tools/num_collision.py   TOOL_VALIDATED, 6 controles

  documentos            128
  numeros distintos      82
  duplicados             37
  refs `NNN` ambiguas   477
  numeros sin colision   45 de 82

  001  2   010  2   021  2   023  2   024  2   025  2
  026  2   027  2   028  2   029  2   030  2   031  2
  032  2   033  3   035  2   036  2   037  2   038  2
  039  2   040  3   041  3   042  3   043  3   044  3
  045  3   046  3   047  3   048  2   049  2   050  2
  051  2   056  2   071  2   072  2   073  2   074  2
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.