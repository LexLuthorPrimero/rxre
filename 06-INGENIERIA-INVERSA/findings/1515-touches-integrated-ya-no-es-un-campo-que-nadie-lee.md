# 1515 — `TOUCHES_INTEGRATED` ya no es un campo que se declara y nadie lee: 0 infracciones, 61 limpias y **13 sin respaldo**

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=VERIFICACION + CORRECCION DE INSTRUMENTO
ESTADO=PROVEN (0 infracciones sobre codigo leido) / NOT_FOUND (por herramienta)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=74 herramientas declaran TOUCHES_INTEGRATED; 0 infracciones; 61 limpias;
  13 declaran `no` sin respaldo; 118 no declaran el campo
PRODUCER=RXRE/tools/rxre_touch.py v1.0.0, 14 vectores, todos PASS
CROSS-CHECK=el recuento de subprocess por AST contra el de una regex que exige
  el prefijo `subprocess.` -- dos caminos independientes
ENCADENA=1513 (el campo se reconoce pero no se comprueba) · 1507 (el mismo
  defecto en el otro instrumento) · 1510 · 1501 · 1487
```

## Por qué este fichero existe

`1513` añadió `TOUCHES_INTEGRATED` al vocabulario de `toolkit.py` porque nueve
herramientas ya lo declaraban y el validador lo rechazaba. Y el propio
`toolkit.py` decía, en el párrafo añadido:

> reconocer un campo no es comprobarlo

Eso era una deuda con nombre. Este fichero la paga.

Y había una pregunta de diseño que había que responder **antes** de escribir
nada: **¿el campo significa *escribir* o *mencionar*?**

AGENTS.md prohíbe, sobre `0000:00:02.0`: escribir, descargar o modificar `i915`,
tocar `fb0`, alterar su runtime PM, cambiar la salida de consola. **Y el
proyecto además lee la iGPU a propósito**: `tools/fingerprint.py` mide
`_id_pci("card0")` porque ése es su trabajo, y lo hace con
`TOUCHES_INTEGRATED=no`.

> un verificador que confunde lectura con infracción no verifica: acusa

Confundir las dos cosas habría marcado como infracción a las herramientas que
cumplen la prohibición.

## Resultado 1 — las tres clases, y por qué no hay una cuarta

```
74 herramientas declaran TOUCHES_INTEGRATED
  VERIFICABLE_LIMPIO        61
  NO_DETERMINED             13
  INFRACCION                 0
118 NO declaran el campo
```

**Cero infracciones.** Ninguna herramienta del árbol escribe en `/sys`, escribe
en `/dev/dri`, llama a `ioctl`, ni borra un nodo de la GPU. `borra_frontera` sale
**0**; los 48 `os.remove`/`unlink` del árbol borran temporales, que no es tocar
la GPU.

**Lo que se afirma es `NOT_FOUND` sobre el código leído, y no
`PROVEN_ABSENT`.** No se ha ejecutado nada: una escritura podría venir de un
módulo, de un `ioctl` indirecto o de otro proceso. El informe lo dice y hay un
vector que falla si la declaración deja de nombrarlo.

**La cuarta clase que no existe es «está bien».** Una herramienta no está bien:
o su código lo sostiene, o no, o no se puede saber. Y la que no se puede saber
tiene nombre — las 13 `NO_DETERMINED`, que declaran `no` **sin respaldo** porque
delegan por `subprocess`.

## Resultado 2 — dos defectos reales del verificador, y el tercero estaba en el diseño

**El primero: daba veredicto a 118 herramientas que no declararon el campo.**

La primera versión llenaba `veredicto` para las 192 filas, incluidas las 118 que
no dicen nada. Y un veredicto sobre una herramienta que no ha dicho nada no es
una verificación: **es un dato sobre una fila que no existe**.

> verificar lo que nadie declaró es medir el instrumento, no el sujeto

Ahora el veredicto es exclusivo de las 74 que declaran, y las demás reciben
`NO_DECLARA` — un estado con nombre, no una ausencia de fila. Y hay dos vectores:
uno que exige `NO_DECLARA` exacto, y otro que exige que `NO_DECLARA` **no** entre
en el recuento de veredictos de comportamiento.

**El segundo: declaré `remove` como verbo de frontera y nunca lo usé.**

Estaba en `VERBOS_FRONTERA`, pero la comprobación de `INFRACCION` miraba
`escribe_sys`, `escribe_dri` e `ioctl`. `dupenum.py` hace `os.remove` cinco
veces sobre temporales y salía `VERIFICABLE_LIMPIO` — que es lo correcto, **pero
por un motivo que el código no decía**.

Declarar un verbo y no comprobarlo es **exactamente el mismo defecto** que
declarar un campo y no verificarlo: las dos cosas salen verdes.

Ahora el verbo depende de la **ruta**: borrar un nodo de `/sys` es escribir;
borrar un temporal de `/tmp` no es tocar la GPU. Y se cuentan los dos por
separado — `borra_frontera` 0, `borra_otro` 48 — para que se vea.

**El tercero, y el más caro: `delega` contaba por nombre de método.**

```python
if nom in ("run", "Popen", "call", ...):   # nom = f.attr
    c["delega"] += 1
```

Eso captura `self.run(...)`, `runner.run(...)`, cualquier cosa. Consecuencia
medida: **16 herramientas salían `NO_DETERMINED`, y tres de ellas
(`campos_pm4.py`, `revkit/pm4dec.py`, `revkit/sello.py`) tienen CERO llamadas a
`subprocess`** — verificado con `grep` por fuera.

> un nombre de método no dice quién lo define

Ahora se exige que el receptor sea el módulo `subprocess`, sobre el AST.

**Y el vector que faltaba.** Este fallo pasó porque **todos** los vectores
comprobaban el AST contra sí mismo. Un vector que compara el instrumento consigo
mismo no puede ver un fallo del instrumento. Se añadió el recuento por un **segundo
camino**: una regex que exige el prefijo `subprocess.`, que es lo que ya hacía
`rxre_contracts.py`. Ahora `delega` (AST) = **156** y `delega_por_regex` = **169**,
y los 28 `metodo_del_nombre` explican la diferencia en lugar de esconderla.

Es el mismo criterio que `rxre_boot.py` ya usa para el recuento independiente del
campo `rc`.

## Resultado 3 — la coherencia cruzada, que es lo que hace útil al verificador

Crucé `TOUCHES_INTEGRATED` con `WRITES_FILES`, que miden instrumentos distintos
sobre ficheros distintos:

| `WRITES_FILES` declarado | `TOUCHES_INTEGRATED` veredicto |
|---|---|
| `no` (61) | `VERIFICABLE_LIMPIO` |
| `indeterminado` (11) | `NO_DETERMINED` |
| `only_with_--register` (1) | `NO_DETERMINED` |

**Incoherencias: 0.** Las 13 que declaran la frontera sin respaldo son
**exactamente** las 13 que ya declaran `WRITES_FILES=indeterminado` por el mismo
motivo — delegan y no se puede saber.

Antes del arreglo del alcance de nombre eran **3** incoherentes: `campos_pm4.py`,
`pm4dec.py` y `sello.py` declaraban `WRITES_FILES=no` (no escriben nada) **y**
`TOUCHES_INTEGRATED=no` sin respaldo. El mismo defecto en dos campos distintos, y
sólo apareció al cruzarlos.

> un campo no se verifica solo: se verifica contra otro campo que mide otra cosa

## Procedencia

- `STATIC` — AST sobre 192 ficheros de los 7 directorios de `toolreg.TOOL_DIRS`.
  Sin ejecutar ninguna herramienta.
- `CROSS-CHECK` — el recuento de `subprocess` por **dos caminos**: AST con el
  receptor `subprocess`, y regex `subprocess\.(run|Popen|…)`. **156 y 169**, con
  los 28 métodos de nombre coincidente explicando la diferencia.
- **Las tres `NO_DETERMINED` falsas se detectaron cruzando instrumentos**, no
  leyendo el propio informe — que es donde se mire primero y donde peor se ve.
- `EJECUCION` — sólo los cinco instrumentos y `toolkit.py`. **Sin MMIO, sin TLB,
  sin insmod.** `GPU INTACTA`.
- Los cinco: `rxre_boot` **19**, `rxre_frontier` **22**, `rxre_contracts` **17**,
  `rxre_deleg` **10**, `rxre_touch` **14**. Preexistentes: `rxre.py` **188
  vectores**, `toolkit.py` autotest OK con 9 flags, `toolkit_cross` verde.

## Lo que NO se afirma

- **No se afirma que las 61 limpias sean seguras.** Se afirma `NOT_FOUND` sobre su
  código. Y 61 de 74 tienen el campo pero **118 del árbol no lo declaran**, así
  que la cobertura de la frontera sigue siendo parcial.
- **No se ha añadido este verificador a `toolkit.py`.** Sigue siendo un
  instrumento aparte que hay que ejecutar. Integrarlo es una acción propuesta, y
  su coste no esta medido — que es exactamente lo que `1513` dejó sin hacer.
- **`mmap` se cuenta y sale 0**, pero sigue declarado como hueco: mapear
  `/dev/dri` puede dar acceso a la BAR sin `open` en modo escritura. Con cero
  casos no hay discriminante, y un campo sin casos no se puede verificar.
- **La GPU integrada sigue ausente de `/sys`** (`1510`), así que este
  verificador trabaja por código y no por hardware. **No puede decir nada de lo
  que pase en runtime**, y no lo dice.

## Dos notas de método

**La primera: los tres defectos se encontraron escribiendo el vector, no el
código.**

El `NO_DECLARA` salió de un vector que pedía `veredicto is None`. El verbo
`remove` salió de un vector que enumeraba los verbos reales. Y el alcance de
`subprocess` **no** salió de un vector: salió de cruzar dos instrumentos y ver
que tres filas no cuadtaban, y de un `grep` de dos segundos que confirmó que
tenían cero llamadas.

Los dos primeros los escribió la disciplina; el tercero lo escribió **la
discrepancia entre dos medidas**. Un instrumento que se verifica a sí mismo sólo
detecta los fallos que alguien pensó mirar.

**La segunda: el mismo defecto, tres veces, en tres instrumentos.**

`1507`: la columna `declarado` traducía `indeterminado` a `no`.
`1513`/este: el veredicto se daba a quien no declaró.
Aquí: `remove` estaba declarado y nunca comprobado.

No son tres errores distintos: son **la misma forma**. *Declarar algo y no
comprobarlo sale verde siempre*, porque no hay nada que pueda ponerse rojo.

Y el patrón que los tres compartían es peor que el de un bug: en los tres, la
columna o el campo **parecía** hacer su trabajo. Por eso la defensa no es
«escribir más vectores», sino **cruzar dos instrumentos que miden cosas
distintas y exigir que cuadren** — que es lo que encontró el tercero.
