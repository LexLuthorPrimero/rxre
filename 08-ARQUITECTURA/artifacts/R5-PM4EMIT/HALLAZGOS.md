# R5-PM4EMIT — un "nunca emitido" que en realidad es "no existe para esta generación"

<!-- MEDIDO con tools/pm4ops.py (alcance de includes) y con la propia
     08-ARQUITECTURA/tools/pm4_emit.py (fallo al evaluar el macro).
     Se cruzan dos mecanismos INDEPENDIENTES. -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin GPU · no se modifica pm4_emit.py
escritura=1 fichero NUEVO (este) + la medida nueva en pm4ops.py
herramienta   tools/pm4ops.py   (nombres_fuera_del_alcance)
sujeto        08-ARQUITECTURA/tools/pm4_emit.py   -- de otra sesion: NO tocado
```

## 0 · EL NÚMERO PUBLICADO

```
$ python3 08-ARQUITECTURA/tools/pm4_emit.py --control
PACKET3 definidos en sid.h : 83
emitidos por GFX8         : 21
nunca emitidos            : 62
```

Las tres cifras son de **universos distintos**. La primera viene de leer
`sid.h` por ruta fija. La segunda se evalúa con las macros que resuelve
`resolve_includes` desde `gfx_v8_0.c`. Y `sid.h` **no está** entre esas —medido
en R2—.

De los 62, **19 no son "nunca emitidos": no son evaluables.** El `except
Unresolved: pass` de `control()` los mete en el mismo saco, en silencio.

## 1 · LO QUE ES Y LO QUE NO ES

`control()` tiene el texto *"Paquetes definidos en sid.h que GFX8 nunca emite"*,
y esa frase mezcla dos afirmaciones:

| lo que dice | lo que es |
|---|---|
| "definidos en sid.h" | un header que GFX8 **no compila** |
| "nunca emitidos" | para 19 de ellos, **no evaluable** |

No es que GFX8 pueda emitirlos y no lo haga. Es que **para GFX8 no existen**.

Verificado sobre la fuente:

| nombre | `sid.h` | `vid.h` | ¿lo compila GFX8? |
|---|---|---|---|
| `PACKET3_ALLOC_GDS` | `0x1B` | — | no |
| `PACKET3_MEM_WRITE` | `0x3D` | — | no |
| `PACKET3_ME_WRITE` | `0x7A` | — | no |
| `PACKET3_COPY_DW` | `0x3B` | — | no |
| `PACKET3_CP_DMA` | `0x41` | — | no |

Y `gfx_v8_0.c` alcanza `vid.h` y **no** alcanza `sid.h` (R2, con 141 ficheros y
una sola rotura, en la cadena del DAL).

## 2 · CORROBORACIÓN POR DOS CAMINOS INDEPENDIENTES

No basta con que yo lo diga. Los dos mecanismos se calculan distinto:

| camino | método | resultado |
|---|---|---|
| `pm4ops --alcance` | cierre de `#include` desde `gfx_v8_0.c` | **67** nombres fuera de alcance |
| `pm4_emit --control` | `eval_call` falla con las macros de su contexto | **19** no evaluables |

Cruce: **18 de los 19** están en el conjunto fuera de alcance. El restante,
`SEM_WAIT_ON_SIGNAL`, es un **tercer estado**: en `sid.h` vale `(0x1 << 12)`, que
**no es un opcode de un byte**. No es "nunca emitido" ni "no existe": está
definido y no es un opcode.

Tres estados distintos que un solo número.

## 3 · LO QUE NO SE AFIRMA

- **No se modifica `pm4_emit.py`.** Es de otra sesión. Esto es un informe.
- **No se afirma que el resto de las cifras sean wrong.** Los 21 "emitidos" y los
  43 restantes sí son comparables; lo que no se sostiene es que los 62 sean
  homogéneos.
- **Los 18 cruzados son la prueba**, y la da el acuerdo de dos mecanismos que no
  comparten código. `pm4ops` razona sobre includes; `pm4_emit` evalúa macros.

## 4 · LA LECIÓN, Y POR QUÉ NO CONSTRUÍ LA HERRAMIENTA GENERAL

Antes busqué un detector general de *"un `except` silencioso convierte no-medido
en ausente"*. **MEDIDO: 94 de 182 herramientas tienen `except: pass`, y 77
además formulan afirmaciones de ausencia.** Al leer las 77, la mayoría son
**comentarios que defienden la disciplina** —`artifacts.py`, `lint.py`,
`revdict.py` argumentan por qué las afirmaciones de ausencia son peligrosas.

**El patrón estático no discrimina.** Una herramienta así daría 77 falsos
positivos: es el defecto que este trabajo denuncia, repetido por mí. No se
construyó.

El defecto se encontró **entendiendo el código y midiéndolo**, que es más lento
y es lo que funciona.

## 5 · LO QUE SÍ SE AÑADIÓ

`pm4ops` expone ahora `nombres_fuera_del_alcance`: los nombres definidos solo en
headers que la generación no compila. Es un hecho del corpus que cualquier
herramienta que hable de "PACKET3 definidos" necesita, y es lo que convierte el
número de `pm4_emit` de aparentemente sólido en visiblemente mixto.

Un detalle de implementación que salió del cruce y que es fácil de volver a
equivocar: **esa medida no puede usar `tabla_activa`**. `tabla_activa` conserva
deliberadamente los nombres cuyos headers son todos de otra generación —
decisión correcta para el *veredicto*, porque borrarlos sería inventar una
ausencia— y por eso misma da cero fuera de alcance. La procedencia por nombre la
da `consenso`, que es la autoritativa. Vectores `ALC_9` y `ALC_10`.

```
ESTADO
  ficheros escritos    1 nuevo; 1 existente modificado (pm4ops.py, mio)
  pm4_emit.py          NO TOCADO
  GPU                  INTACTA
  sudo                 NO usado
  commits              NINGUNO
```