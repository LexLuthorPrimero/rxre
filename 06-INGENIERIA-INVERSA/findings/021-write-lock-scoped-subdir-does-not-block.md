# 021 · El cerrojo de ámbito no excluye al cerrojo raíz, y viceversa

`CLASSIFICATION=DOCUMENTATION` · `WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE`
`CONTINUES=COORDINACION.md §PREFLIGHT, §Ámbitos independientes`

## CUDA principal

`.write-lock` y `.write-lock/findings` **no se excluyen mutuamente**. El protocolo de
`COORDINACION.md:163-175` dice que el cerrojo raíz "es el único que excluye a las otras
sesiones de todo". Falso: `mkdir .write-lock/findings` tiene éxito con `.write-lock` ya
creado. Dos sesiones pueden escribir a la vez en el mismo árbol sin que ninguna lo detecte.

## Reproducción

```
$ mkdir /tmp/opencode/locktest && cd locktest
$ mkdir .write-lock                      # rc=0, cerrojo raíz adquirido
$ mkdir .write-lock/findings             # rc=0  <-- CON LA RAÍZ YA TOMADA
$ ls .write-lock/
findings
```

`mkdir` sobre un directorio existente falla; sobre un subdirectorio **nuevo** de un
directorio existente tiene éxito. La primitiva de exclusión del protocolo sólo protege
contra dos sesiones que compiten por el **mismo** nombre de lock, nunca contra un ancestro.

## Por qué importa aquí, y no es teórico

Durante esta sesión pasó. Dos sesiones corriendo a la vez:

| PID | Lock tomado | Ficheros escritos |
|---|---|---|
| 50141 | `.write-lock` (raíz) | `017` :09:52, `018` :10:04, `019` :10:11 |
| 50153 | `.write-lock/findings` | `020` :10:12 |

Ambas escribieron en `06-INGENIERIA-INVERSA/findings/` simultáneamente. `/proc/50153` no
existe al comprobarlo, y `/proc/50141` tampoco: ambos procesos ya habían terminado. Los
PID los escribió el shell que ejecutó el `mkdir`, no el proceso agente, así que **el PID
registrado no identifica al dueño** y el test de liveness de `COORDINACION.md:88-90` no
puede decidir nada. Eso ya lo registra `COORDINACION.md:208-220` y `:245-257` para el
protocolo del humano; aquí se repite con el canónico.

Los números no chocaron porque 017/018/19 y 020 elegieron nombres distintos. Eso fue
suerte del índice, no una garantía: `016-q5-static-preregistration.md` era el último
fichero y `020` era el siguiente libre por orden para las dos sesiones. Si las dos hubieran
elegido `020`, una habría sobrescrito a la otra. Es exactamente el daño que
`COORDINACION.md:9-12` describe ("una reescritura que ni compilaba") y que el protocolo
debería impedir.

`NEGATIVE_RESULT` verificado: **ningún rango de escritura de esta sesión se solapó con el
de la otra**. Comprobado por mtime de los cuatro ficheros, todos distintos y coherentes
(09:52, 10:04, 10:11, 10:12). `CONFLICT=none`. `NO_COLLISION_OBSERVED` no es
`COLLISION_IMPOSSIBLE`: es el resultado de una vez.

## Reglas que sí funcionan, y las que no

| Regla | Estado |
|---|---|
| `mkdir` como exclusión atómica, misma ruta | `PROVEN` funciona — dos sesiones, misma ruta, una gana |
| Cerrojo raíz excluye todas las demás sesiones | **`REFUTED`** por §Reproducción |
| Cerrojo de ámbito (`docs/`, `findings/`) excluye a quien tiene la raíz | **`REFUTED`** por la misma prueba |
| Test de liveness por `/proc/$pid` | `INCONCLUSIVE` — el PID del shell no es el del agente |
| `git status` como arbitro | `REFUTED`, ya lo decía `COORDINACION.md:15-19` |

El caso inverso —ámbito tomado, raíz después— sí falla como es debido: `mkdir
.write-lock` falla si `.write-lock` existe. O sea que la asimetría es en un solo sentido:
**la raíz gana al ámbito, el ámbito no puede desplazar a la raíz y tampoco es bloqueado
por ella**. La raíz sólo protege de otras raíces.

## Corrección mínima, con el coste medido

Un solo cambio al protocolo: antes de `mkdir .write-lock/<ámbito>`, comprobar que
`.write-lock` no existe **y** que `.write-lock/owner` no es nuestro. Si existe y no es
nuestro, `QUEUE_ENTRY_BLOCKED`. Eso convierte el ancestro en excluyente sin cambiar la
primitiva ni los nombres de ámbito, que es lo único que las sesiones actuales ya hacen
bien.

Coste: una comprobación extra. Beneficio: cierra la única vía por la que dos sesiones
escribieron en el mismo árbol hoy. No lo aplico — es un cambio a `COORDINACION.md`, que es
ley operativa, y eso requiere decisión humana.

Lo que **no** propongo: un fichero de "intención" dentro del lock, porque introduce una
ventana de carrera entre escribir la intención y tomar el lock, que es peor que el
problema que resuelve.

## Falsación

Se refutaría si se mostrara una variante de la prueba en la que `mkdir
.write-lock/findings` falla con `.write-lock` presente. En POSIX, `mkdir` sólo falla con
`EEXIST`, y `.write-lock/findings` no existe aunque `.write-lock` sí. `PROVEN`.

## Evidencia

```
$ mkdir /tmp/opencode/locktest; mkdir .write-lock; mkdir .write-lock/findings; echo $?
0
$ ls .write-lock/
findings
```
Ejecutado en `/tmp/opencode/locktest`, fuera del repositorio, y borrado después. No se
toca el árbol del proyecto para demostrarlo.

Estado del cerrojo del proyecto, y aquí corrijo lo que escribí al redactar:

A las 10:11 el cerrojo estaba así: `.write-lock/findings/owner` =
`PID=50153 2026-10-01T10:05:24-03:00`, con `/proc/50153` inexistente →
`OWNER_NOT_RUNNING` → `QUEUE_ENTRY_BLOCKED` por `COORDINACION.md:97`. Escribí que lo
dejaba como estaba y que no lo borraba, porque un cerrojo abandonado no es permiso para
tomarlo (`COORDINACION.md:160`) y tomarlo exige autorización humana.

**Ya no está.** Comprobado al cerrar:

```
$ test -d .write-lock || echo "LOCK_ABSENT -> QUEUE_ENTRY_ALLOWED"
LOCK_ABSENT -> QUEUE_ENTRY_ALLOWED
```

La otra sesión lo liberó por su cuenta. No lo borré yo en ningún momento: mi `rm` de las
10:11 tocó sólo `.write-lock/owner` (mi propio fichero) y el `rmdir` falló por el
subdirectorio ajeno, como consta arriba. Un `NEGATIVE_RESULT` que dejo dicho porque
afecta a la fiabilidad de mi propio relato: **no sé cuándo ni quién lo liberó**, y no hay
registro en el árbol que lo diga. Sin ese registro, "no lo borré yo" es una afirmación
sobre mis propias llamadas — verificable en el transcript — y no sobre el estado del
disco.

Consecuencia práctica en ese momento: el repo pasó a `LOCK_ABSENT`. Duró poco — ver §9. Y la lección sigue siendo válida: la colisión ocurrió con dos
locks vivos a la vez, y liberarlos después no deshace el solapamiento de 10:11–10:12.

Ficheros de esta sesión, con mtime y sha256:

```
017-vm-invalidate-gfx8-function-always.md    09:52:11
018-execution-order-invalidacion-gfx8.md     10:04:07   fc119aaa…96318
019-atc-l2-invalidation-gfx8.md              10:11:36   b882b372…be16486
021-write-lock-scoped-subdir-does-not-block.md            (este)
```

`020-vmflush-dword-budget-gfx8.md` :10:12:15 — escrito por PID 50153, no es mío.

## 9 · Postdata: la colisión ocurrió otra vez, y el índice se solapó

Después de redactar esto, a las 10:38, hubo otra escritura concurrente. La tabla de la
§Estado del cerrojo queda desactualizada y la actualizo:

| PID | Lock | Fichero | mtime |
|---|---|---|---|
| esta sesión | `.write-lock` (raíz) | `023-pte-productor-sdma-gfx8.md` | 10:38:08 |
| otra sesión | `.write-lock/tools` | `022-cond-exec-inerte-en-gfx8.md` | 10:34:28 |
| otra sesión | — | `021-frame-budget-gfx8-peor-caso.md` | 10:28:21 |

Reproduce exactamente el fallo que este documento predice: dos sesiones con locks de
ámbito distintos escribiendo en `findings/` al mismo tiempo. Y esta vez **ttambién
colisionó el índice**: las dos sesiones eligieron `022` y escribieron
`022-cond-exec-inerte-en-gfx8.md` y `022-pte-productor-sdma-gfx8.md` en el mismo directorio.
Ya hay dos `021` en el directorio por el mismo motivo.

Resolución: renombré el mío a `023-pte-productor-sdma-gfx8.md` y corregí su título. El otro
`022` no lo toqué — no es mío, y `COORDINACION.md:184` dice informar, no arreglar. Queda un
`021` duplicado sin resolver: `021-frame-budget-gfx8-peor-caso.md` y
`021-write-lock-scoped-subdir-does-not-block.md` son de sesiones distintas y ambos existen.

**Esto convierte `NO_COLLISION_OBSERVED` de la §"Por qué importa" en `COLLISION_OBSERVED`.**
La primera vez no hubo solapamiento de nombres y lo registré como suerte del índice. La
segunda vez sí lo hubo. El índice numérico no es un mecanismo de exclusión y no lo es
tampoco entre sesiones que nunca se ven.

`NEGATIVE_RESULT` que sí se sostiene: ningún fichero existente fue sobrescrito. Los dos
`022` coexisten porque el sistema de ficheros creó nombres distintos; el de las 10:38 se
renombró. Eso es `mkdir`/`O_CREAT` FAIR, no coordinación — el resultado correcto por el
mecanismo equivocado, otra vez.
