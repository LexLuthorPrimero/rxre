# 118 · la medida de higiene de herramientas no puede ver el fallo de la herramienta que mide

```
CLASSIFICATION=DOCUMENTATION · TRACK=TOOLING
CORPUS=NO APLICA · HARDWARE_SCOPE=NO APLICA
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`117` encontró que `doclint` por defecto revisa 38 de 192 hallazgos. Pregunté si
eso era un caso o una plaga, medí las 29 herramientas con contrato, y salió que
**es un caso único.** Esta nota dice algo más incómodo que eso.

## Primero: es un caso único

Cinco herramientas recorren `findings/`. Cuatro lo recorren entero:

```
causal_map.py:129     glob.glob(f"{FIND}/*.md")
next_work.py:73       os.listdir(FIND)
num_collision.py:106  os.listdir(FIND)  filtrado por .md
stale_gap.py:407      os.listdir(FIND)
doclint.py:325        glob.glob(f".../findings/0[23]*.md")     <- EL ÚNICO FILTRO NUMÉRICO
```

Comprobado que ninguno de los cuatro tiene un filtro numérico adicional:

```
grep -nE 'FINDINGS|0\[0-9\]\*|\[0-9\]\{3\}|startswith\("0'  sobre los cuatro
-> 0 coincidencias
```

**El árbol tiene una convención consistente — "recorre `findings/` entero" — y
`doclint` es el que la rompe.** Eso cambia el diagnóstico de `117`: no es un
patrón sistémico, es un valor congelado en un sitio.

## Pero el problema real no es el alcance

Es que **nada revela que el alcance está incompleto.** Tres mecanismos, medidos:

**1 · El titular usa el denominador filtrado, y no dice el total.**

```
doclint.py:352   print(f"documentos: {len(args)}   errores: {tot_e}   avisos: {tot_w}")
```

Ejecutado sin argumentos:

```
documentos: 38   errores: 0   avisos: 37
```

**Eso se lee como un visto bueno.** La suposición del lector es "38 hallazgos, 0
errores". Es 38 de 192, y el 0Errors sólo es cierto sobre ese 38.

**2 · `doclint` no dice en ningún sitio cuántos hallazgos hay.**

```
grep -cE 'len\(glob|total_ficheros|hay [0-9]|de [0-9]+ hallazgos'  ->  0
```

**No hay forma de que quien lo lee se entere.** El titular tiene forma de Dictamen
limpio, y la forma no lleva la información que lo haría falso.

**3 · El alcance no está en el contrato.**

29 herramientas declaran `CONTRACT:`. Los campos que existen, en todo el árbol:

```
     33 CONTRACT: READONLY
     30 CONTRACT: WRITES_FILES
     30 CONTRACT: WRITES_SYSFS
     30 CONTRACT: WRITES_GPU
     30 CONTRACT: MUTATES_CORPUS
```

**Ninguno declara a qué cubre.** El contrato dice quéSide-effects tiene una
herramienta; no dice **sobre cuántas cosas.opina**.

## Y aquí está la parte incómoda

`toolaudit.py` mide F11, y F11 pregunta literalmente si una herramienta **publica
un titular** y si **alguien lo cita**. Las dos cosas las hace `doclint`, y bien:

```
toolaudit.py:74   Una herramienta "tiene titular" si su salida imprime un CONTEO como titular.
```

**Así que `toolaudit` calificaría a `doclint` como buena: tiene titular, y la
gente lo cita.** Lo que `toolaudit` no puede ver es que **el denominador de ese
titular es un subconjunto sin declarar.**

**La medida de higiene de herramientas tiene un punto ciego que es exactamente el
modo de fallo de las herramientas que mide.** Es la tercera vez que sale esta
forma en la tanda — con `citecheck`, con `doclint` y con `toolaudit` — y ya tiene
nombre en este proyecto:

| herramienta | comprueba | no puede comprobar |
|---|---|---|
| `citecheck` | que el fichero y la línea existan | que el contenido sea el que se cita |
| `doclint` | que la línea exista | que su existencia sea la noticia |
| `toolaudit` | que haya titular y se cite | que el titular esté completo |

**Las tres comprueban sintaxis. Ninguna comprueba que le hayan pedido la
comprobación correcta.**

## La regla, que es una línea

> **El denominador de un titular tiene que ser parte del titular.**

`documentos: 38 de 192` en vez de `documentos: 38`. Con eso, el fallo de `doclint`
se ve en la línea 1 de la salida, sin leer el código.

### Y NO ES MI REGLA: YA EXISTE EN ESTE ÁRBOL

La propuse como propuesta y era convención establecida. Seis sitios en cinco
herramientas, todos con la misma forma `N de M`:

```
next_work.py:140        f"{len(sin)} de {len(tocados)} registros sin mencion documental"
num_collision.py:240    f"numeros SIN colision: {len(unicos)} de {len(por_num)}"
smumsg.py:298           f"DEFINIDOS PERO NO ENVIADOS POR EL HOST: {len(un)} de {len(s7)}"
contradict.py:374       cab += f" de {len(vals)}" if ocultos else ""
pm4_reachable.py:391    print(...)
pm4_reachable.py:521    print(...)
```

**`doclint` no incumple una regla que le falte: incumple una convención que cinco
de sus vecinas ya cumplen.** No hay que inventar nada ni convencer a nadie: sólo
escribir el denominador.

### El alcance congelado sigue siendo único: 1 línea de 29

Medido sobre las 29 herramientas con contrato, separando filtro de *identidad*
(prefijo numérico, lista escrita a mano, corte) de filtro de *tipo* (`.md`, `.c`),
y cruzado por una segunda vía:

```
doclint.py   L325   args = sorted(glob.glob(f".../findings/0[23]*.md"))
total: 1 linea en 1 herramienta
```

**Y una hipótesis mía que era falsa, comprobada en vez de afirmada.** Vi
`next_work.py:139` con `registros=sin[:40]` y sospeché saturación a 40. No:
`[:40]` trunca **lo que se muestra**, y los dos conteos usan `len(sin)` completo.

```
next_work.py:129   sin = sorted(tocados - set(mencionados))
next_work.py:139   registros=sin[:40],                       <- solo la lista mostrada
next_work.py:140   detalle=f"{len(sin)} de {len(tocados)} ..."  <- cuenta todo
```

**`next_work` es el ejemplo correcto de la convención: trunca la presentación y no
el conteo, y hasta imprime el denominador.** Lo comprobé porque me parecía
demasiado bonito para ser cierto.

## Y por qué lo anterior no sirve

`117` propuso "una comprobación de contrato: que ninguna herramienta tenga un
alcance escrito a mano, y que se falle si el número de ficheros que cubre no
coincide con el de los que existen". **Antes de construirla comprobé si existía.**

```
toolkit.py:69    FLAGS = ["READONLY", "WRITES_FILES", "WRITES_SYSFS",
                          "MUTATES_CORPUS", ...]
```

**Existe el validador de contratos, y el vocabulario, y las 29 herramientas ya
lo usan.** Lo que falta es **un campo**, no una herramienta.

| lo que hace falta | dónde | tamaño |
|---|---|---|
| campo `SCOPE=` en el vocabulario | `toolkit.py:69` `FLAGS` | 1 línea |
| que `doclint` lo declare, o cambie el glob | `doclint.py:325` | 1 línea |
| que el titular lleve el denominador | `doclint.py:352` | 1 línea |

**Tres líneas. Y no las aplico: `toolkit.py` y `doclint.py` están escritos en
primera persona por otra sesión, y no hay git para saber de quién son.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `doclint` es el único con filtro numérico de alcance | `PROVEN` (5 herramientas revisadas) |
| Los otros cuatro recorren `findings/` entero | `PROVEN` (`grep`, 0 filtros extra) |
| El denominador del titular es `len(args)` | `PROVEN` (`doclint.py:352`) |
| `doclint` no declara el total | `PROVEN` (`grep`, 0 coincidencias) |
| 5 campos de contrato, ninguno de alcance | `OBSERVED` (29 herramientas) |
| `toolaudit` mide titular y citación | `PROVEN` (`toolaudit.py:74`) |
| `toolaudit` no mide el denominador | `PROVEN_ABSENT` |
| Que F11 sea esta frontera | **`NOT_VERIFIED`** |
| Que 4 de las 5 herramientas con titular hagan lo mismo | **`NOT_DETERMINED`** |

**La penúltima no la comprobé.** `117` y yo damos por hecho que `F11` es la
frontera del titular en `docs/OPEN-FRONTIERS.md`, y no lo he abierto. Lo doy por
sabido y **es el cuarto "doy por sabido" de la tarde**, que es exactamente el
defecto que vengo documentando. Lo marco para no repetirlo: **nadie ha abierto ese
fichero en esta sesión.**

**La última es la que da miedo y la dejo abierta a propósito:** si `causal_map`,
`next_work`, `num_collision` o `stale_gap` tienen un titular con denominador
filtrado, el problema no es `doclint` sino el patrón. **No lo he medido**, y es
una sola línea por herramienta.

## Procedencia

- `TOOLING` -- `doclint.py:325` `:352`, `toolkit.py:69`, `toolaudit.py:9-10`
  `:74`. Lectura. No se modificó ningún fichero.
- `OBSERVED` -- `grep` sobre las 29 herramientas con `CONTRACT: name=`, y sobre
  las 5 que recorren `findings/`. Lectura.
- **No se editó `doclint.py` ni `toolkit.py` ni `toolaudit.py`** (`COORDINACION.md:184`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.
- Encadenada con `117` (el alcance congelado), `062`/`077` (citas sin verificar),
  `116` (no re-mirar un valor).

## Nota de método

**Esta nota nació de una propuesta que resulté no construir.** `117` terminó
proponiendo una comprobación de alcance, y el turno siguiente la iba a escribir.
Antes la busqué en el árbol y existed el validador y el vocabulario y las 29
herramientas usándolo.

**DUPLICATE CONTROL me salvó por segunda vez en dos turnos, y las dos por el
mismo motivo: nombré un trabajo y fui a hacerlo en vez de mirar qué había.**

**Lo que sí he cambiado, y es lo que quiero que quede: la propuesta ya no es una
herramienta, es un campo y una regla.** *"El denominador de un titular tiene que
ser parte del titular"* no necesita un programa que la imponga. Se lee. Y si en
seis meses alguien escribe un titular con un subconjunto, la línea lo delata.

**Tres líneas de parche, una regla de una línea, y ninguna aplicada porque no son
mías. Eso es todo lo que sale de aquí, y es menos de lo que tenía al empezar.**