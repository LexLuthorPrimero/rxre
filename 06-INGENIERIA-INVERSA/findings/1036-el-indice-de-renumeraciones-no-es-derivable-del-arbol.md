# 1036 · El índice de renumeraciones NO es derivable del árbol, y regenerarlo lo destruye

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=N/A` · `HARDWARE_SCOPE=N/A` (ningún acceso a hardware)
`WORK_CLASS=READ_WRITE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`GPU INTACTA` · `MODIFIES_CODE=SI` (`08-ARQUITECTURA/tools/findings_index.py`)

---

## La pregunta

El nodo de la puerta de numeración dejó escrita una acción discriminante:
regenerar `FINDINGS-RENUMERACIONES.md` y comprobar que el código de la puerta
baja de 5 a 4. La ejecuté. **Bajó a 4** — y al comparar el índice antes y
después descubrí que la regeneración había **borrado el contenido más valioso
del documento**.

## MEDIDO

### Lo que se perdió

`FINDINGS-RENUMERACIONES.md`, regenerado por su propio generador:

| | índice en disco (2026-10-03T15:59:03) | tras regenerar |
|---|---|---|
| Ficheros en `findings/` | 509 | 540 |
| Numeros con colisión | 74 | 74 |
| **Renumeraciones detectadas** | **43** | **0** |
| **Referencias colgando** | **1033**, en 42 números | **0**, en 0 números |

Las dos últimas filas son el hallazgo. **Las 1033 referencias colgantes son
reales**: son citas `` `NNN` `` que apuntan a un número cuyo hallazgo ya no es
ese, por el renumerado anterior. Y son exactamente la clase de defecto que el
resto del proyecto mide.

### Por qué el generador no las ve

MEDIDO, sobre el generador y sobre git:

```
08-ARQUITECTURA/tools/findings_index.py   usa  reenvios_estable()
                                            = diferencia entre el ÁRBOL DE
                                              TRABAJO y HEAD
```

Eso **sólo ve las renumeraciones que no están commiteadas**. Y hay una razón de
fondo por la que las commiteadas no se van a ver nunca:

> **el renumerado reutiliza el número viejo para otro hallazgo.**

```
$ ls 06-INGENIERIA-INVERSA/findings/052-*
052-srcid-de-fault-gfx8-y-tabla-de-iv-no-catalogada.md

$ git log --diff-filter=R --name-status -- 06-INGENIERIA-INVERSA/findings/
(0 líneas)
$ git log --name-status -M1 -- 06-INGENIERIA-INVERSA/findings/ | grep -c ^R
1
```

El 52 se renumeró a 193, y **otro hallazgo ocupa hoy el 52**. Git ve
BORRADO + AÑADIDO, no un renombrado, porque el nombre se reutilizó. Con `-M1`
aparece **una sola** línea, de 43.

Corolario: **las 1033 referencias no son recuperables del árbol por ninguna vía de
renombrado**. No es que falte un comando; es que la información se
hacia donde git no la puede ver.

### Por qué el contenido actual se conserva solo por casualidad

Cuando generé el índice el 2026-10-03, las 43 renumeraciones **aún no estaban
commiteadas** — por eso las vio. Se commitearon después. En el momento en que se
commitearon, el índice se convirtió en el **único** sitio donde estaban, y el
generador pasó a producir ceros.

Por eso el índice no es un artefacto derivado: es un **registro accumulative**.

### La puerta lo detecta, pero el arreglo proposed la destruía

`tools/check_num_unico.py` da **5** hoy, y el 5 es un **positivo cierto**: el
índice dice 509 ficheros y hay 540. La acción que el nodo proponía para limpiar el
5 —regenerar— es exactamente la que borra el historial. Las dos cosas son
verdaderas a la vez, y por eso la puerta no bastaba: **detecta el síntoma y no la
consecuencia**.

## Lo que hice

`escribir_reenvio()` **se niega a escribir** si va a perder renumeraciones o
referencias colgando:

```
$ python3 08-ARQUITECTURA/tools/findings_index.py --escribir-reenvio
escribir_reenvio: NO SE ESCRIBE
  el indice de disco tiene 43 renumeraciones y esta ejecucion mide 0.
  Motivo medido:  el generador las ve comparando el arbol contra HEAD,  y las
  commiteadas no se ven  —porque el numero viejo se reutiliza para otro hallazgo
  y git lo registra como borrado + anadido,  no como renombrado.
  Regenerar aqui pondria 0 donde hay 43,  y las 1033 referencias colgando
  dejarian de estar registradas.
  Para regenerar hay que decidir antes donde vive ese historial:  el indice no
  es derivable del arbol.
findings_index: perdio 43 renumeraciones y 1033 referencias colgando
$ echo $?
2
```

La comprobación va **después** de calcular, porque lo que se compara es lo que se
va a escribir contra lo que hay; y va **antes** de abrir el fichero en `"w"`,
porque un 0 escrito sobre un 43 es irreversible en cuanto se cierra.

MEDIDO: el índice conserva su sha256 (`946219b4…`) después del intento. Y
`--self-test` sigue en verde.

## Lo que NO se ha hecho, y por qué

1. **No se ha regenerado el índice.** El 509 sigue diciendo 509 y la puerta sigue
   dando 5. Es correcto: el índice *está* viejo, y la manera de arreglarlo está
   bloqueada por una decisión que no es técnica.
2. **No se ha arreglado el 509.** Se podría escribir a mano `540` y la puerta
   bajaría a 4 — pero eso hace que el documento **parezca** regenerado cuando no
   lo está, y borra la señal de "esto es un registro de una época". Peor que
   estar viejo.
3. **No se han reparado las 1033 referencias.** Es reescritura de texto sobre 42
   números, y primero hay que saber cuál es el destino correcto de cada una.

## LA DECISIÓN QUE HACE FALTA, y es de política

El historial de renumeraciones vive hoy en un fichero generado que se puede
destruir con un comando. Tres destinos posibles, ninguno bueno:

| destino | qué gana | qué cuesta |
|---|---|---|
| **`findings/_reservas/*.res`** | ya es el sitio de "número reservado", y ya hay 5 stubs | MEDIDO hoy: los stubs tienen `numero`, `pid`, `agent` y timestamp, **pero no el renumerado**. Habría que cambiar su formato y no se puede recuperar lo que no está |
| **un fichero de historial explícito** | un registro por renumeración, append-only, con su sha256 | hay que escribir las 43 a mano desde el índice viejo, y el día que se vuelva a renumerar hay que acordarse de escribir |
| **la cabecera de cada hallazgo** (`RENUMERADO_DE=N` en el `.md`) | sobrevive al renumerado, porque viaja con el fichero | MEDIDO: no existe ese campo en ninguno de los 540 ficheros, y las 43 filas del índice viejo habría que volcarlas |

La tercera es la que sobrevive a `tar`, a `cp` y a un `checkout`, y es la coherente
con el resto del proyecto. Pero es una decisión de convención, no una medida, y
por eso no la tomo aquí.

## LO QUE ESTA ABIERTO

- `tools/check_num_unico.py` da **5** y seguirá dando 5 hasta que el índice se
  actualice. Con `--alcance propio` cuesta 1.54 s.
- El índice generated 2026-10-03 y no debe tocarse sin la decisión de arriba.
- Las 20 líneas del registro que dicen «no renumerar» (medidas en
  `08-ARQUITECTURA/decisions/2026-10-04-numeros-de-hallazgo-duplicados.md`)
  siguen ahí, y la clasificación que se hizo de ellas —afirmación sobre el
  método, no prohibición— está medida pero no reescrita.