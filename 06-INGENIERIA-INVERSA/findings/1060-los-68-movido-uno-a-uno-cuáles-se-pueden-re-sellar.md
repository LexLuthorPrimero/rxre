# 1060 — los 68 `MOVIDO`, uno a uno: 33 se pueden re-sellar, 30 no se deben, 3 no son míos y 2 son build output sellado como evidencia

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=ADJUDICACION · TRACK=STATIC+GIT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=docs/EVIDENCE-MANIFEST.sha256 (generado 09:59:09) · 68 de 245 entradas
         revkit/sello.py:133 custodia (ya separo las dos preguntas, commit b3314b6)
ORIGEN=1059 §6 (el contrato decia "decision fichero a fichero"; esto es esa decision)
ESTADO=PROBADO · 68/68 clasificados · NO he re-sellado nada
artefacto   /tmp/opencode/adjud68.json   (68 filas con las 5 respuestas)
```

## 0 · Lo que este documento decide y lo que no

`sello.py` se niega a re-sellar, y con razón: *"volver a sellar un fichero que cambió
sin mirarlo convierte un detector de derivas en un detector de cambios"*. Lo que
faltaba era **mirar**. Esto es mirar, fichero a fichero.

**Y el reparto sale menos uniforme de lo que el recuento sugería.** Los 68 `MOVIDO`
no son 68 casos del mismo tipo, y la acción que corresponde a cada uno es distinta.

| clase | n | ¿se puede re-sellar? | por qué |
|---|---|---|---|
| **A** `EDIT_COMMITTEADA` | **33** | **SÍ, con decisión** | el contenido actual **está commiteado**: el sello nuevo tiene un respaldo en git, que es lo que el sello protege |
| **B** `EDIT_SIN_COMMIT` | **3** | **NO** | son trabajo **sin commitear de otra sesión activa**. No es asunto mío |
| **C** `SELLADO_PERDIDO` | **30** | **NO, y es peor no hacerlo** | el estado sellado no está en ningún objeto. Re-sellar **destruye el único registro** de que ese estado existió |
| **D** `SIN_RECUPERAR` | **2** | **NO, y el problema es otro** | son **build output** sellado como evidencia (§4) |

## 1 · Las cinco preguntas, y por qué cinco

Por fichero, del manifiesto y del árbol:

| # | pregunta | método |
|---|---|---|
| Q1 | ¿el contenido **sellado** es recuperable? | sha256 de los 7614 blobs de `--batch-all-objects`, sueltos e inalcanzables |
| Q2 | ¿el contenido **actual** está commiteado? | `sha256(git cat-file blob HEAD:<p>)` == `sha256(working)` |
| Q3 | ¿hay cambios sin commitear? | `git diff --quiet` → **código de salida**, no stdout |
| Q4 | ¿el último commit encogió el fichero? | `git show --numstat` |
| Q5 | ¿hay un `.mod.cmd` hermano? | si lo hay, kbuild genera ese fichero |

Q5 es la que separa la clase D, y es la que no existía antes de este documento.

**El método tiene sus propios controles positivos**: 36 sellados recuperados y 32 no.
Un método que no encontrara nada daría 68 negativos. Y la enumeración es completa:
`count-objects` dice 760 sueltos + 10093 en pack; el recorrido ve 10847 entradas, 5
de ellas `missing` — los 5 objetos vacíos del hallazgo `1058`.

## 2 · CLASE A — 33 ficheros, re-sellables, y por qué esta clase SÍ se puede cerrar

Las cuatro respuestas: Q1 sí, Q2 sí, Q3 no, y el contenido sellado está a salvo.

```text
06-.../010-pgm-rsrc1-decoded.md            9535   dir=IGUAL
06-.../013-real-submit-path-polaris12.md  11966   dir=IGUAL
06-.../033-pm4-spec-gfx8-no-existe…      24616   dir=CRECIO
06-.../046-auto-referencia-y-la-jer…     10981   dir=IGUAL
06-.../047-el-handler-si-lee-src-data.md  11303   dir=IGUAL
06-.../057-vias-de-lectura-gpuvm…         7118   dir=IGUAL
06-.../058-tabla-iv-gfx8-112-nombres…     5132   dir=IGUAL
06-.../059-srcdata-no-es-payload…         5702   dir=IGUAL
06-.../060-srcdata-es-el-subtipo…         5969   dir=IGUAL
08-ARQUITECTURA/tools/_selftest_stale_gap.py  30804  dir=CRECIO
08-ARQUITECTURA/tools/causal_map.py      20697   dir=IGUAL
08-ARQUITECTURA/tools/doclint.py         20164   dir=CRECIO
08-ARQUITECTURA/tools/gmmio_inventory.py 14226   dir=IGUAL
08-ARQUITECTURA/tools/mqd_layout.py      34521   dir=IGUAL
08-ARQUITECTURA/tools/num_collision.py    9279   dir=ENCOGIO
08-ARQUITECTURA/tools/runtime_obs.py     17258   dir=CRECIO
08-ARQUITECTURA/tools/stale_gap.py       53805   dir=CRECIO
08-ARQUITECTURA/tools/toolkit.py         40492   dir=CRECIO
revkit/HALLAZGOS-2026-10-02.md            39435   dir=CRECIO
revkit/PTEPDE-GFX8.md                     5936   dir=CRECIO
revkit/WAIT-REG-MEM-REAL.md              12830   dir=CRECIO
revkit/check.sh                          31016   dir=CRECIO
revkit/cn7.py                            54295   dir=CRECIO
revkit/ibtrace.py                        23468   dir=CRECIO
revkit/pm4dec.py                         55047   dir=CRECIO
revkit/pte.py                            10819   dir=CRECIO
revkit/selfcheck.py                      29066   dir=CRECIO
tools/citegen.py                         20888   dir=CRECIO
tools/constmap.py                        31224   dir=CRECIO
tools/hwip.py                            49604   dir=CRECIO
tools/pm4census.py                       26775   dir=CRECIO
tools/rx550pm4val.c                      35368   dir=CRECIO
tools/toolreg.py                         55585   dir=CRECIO
```

**Por qué esta clase sí admite decisión automática, y las otras no.** El sello cumple
una función: *detectar que la evidencia cambió*. Esa función la puede cumplir git sin
ayuda del sello cuando **el contenido está commiteado** — que es Q2. Re-sellar un
fichero de esta clase cambia el hash del manifiesto y **no baja la capacidad de
detectar**: el estado anterior sigue en git, y por tanto sigue siendo alcanzable con
Q1.

**Un `ENCOGIO` que hay que mirar antes de cerrar nada:** `08-ARQUITECTURA/tools/
num_collision.py` (−). Todos los demás crecieron o quedaron iguales. Un fichero que
encoge es el único de esta clase que puede haber perdido contenido, y sin línea base
(`NOT_DETERMINED`, §5 del `1059`) no se puede saber qué. **Es el único fichero de las
68 que requiere una decisión humana antes de re-sellar.**

**No he re-sellado.** El contrato de `drift.py --actualizar` exige que no haya ni un
`MOVIDO` ni un `ROTO`, y los hay. Levantar eso para que pase una de las clases es
justo el atajo que el propio `sello.py` dice que no hay que hacer.

## 3 · CLASE B — 3 ficheros que no son asunto mío

```text
revkit/dires.py        17763   dir=CRECIO
tools/cap_census.py    24929   dir=CRECIO
tools/trace_path.py    42191   dir=CRECIO
```

Son el trabajo **sin commitear de otra sesión** que está escribiendo en este árbol. Q1
dice que su contenido sellado está a salvo, así que no hay pérdida. Pero **no se
pueden re-sellar**: re-sellar un fichero sin commitear cambia el manifiesto y no deja
ningún sitio al que volver. Reclamarlos sería además meter en un commit mío trabajo
ajeno, que es exactamente la violación de §88 que ya se ha pagado. **Dejar como están.**

## 4 · CLASE D — 2 ficheros que no son evidencia, y el filtro que no lo puede ver

```text
07-DRIVER/kernel/rx550.mod.c        426 B
07-DRIVER/kernel/rx550_drv.mod.c    480 B
```

MEDIDO, Q5: existen sus hermanos `.rx550.mod.cmd` y `.rx550_drv.mod.cmd`. Esos dos
`.cmd` son los ficheros de traza de órdenes que kbuild deja al compilar un módulo, y
**existen precisamente para estos dos `.c`**. Los dos ficheros sellados son
**generados por la construcción**, y se reescriben en cada `make`.

Su contenido empieza por `#include <linux/module.h>` / `<linux/compiler.h>`, que es
lo que emite kbuild, y su tamaño —426 y 480 bytes— es el de un stub de metadatos de
módulo, no el de un módulo.

**El mecanismo del defecto, y es transferible.** `sello.py` filtra la evidencia por
**extensión**:

```python
NO_EVIDENCIA_EXT = {".o", ".ko", ".so", ".pyc", ".png", ".jpg", ".rgba", ".bin", ".spv", ...}
```

Un `.mod.c` **pasa**, porque es `.c`. **El filtro ve la extensión y no ve la
generación**, y un fichero generado con extensión de fuente es indistinguible de una
fuente escrita usando solo la extensión. Por eso son la **única clase que no puede
recuperar su sello nunca**: no es que se haya perdido, es que **no hay estado sellado
al que volver porque el fichero se reescribe**.

La detección no cuesta nada una vez que se sabe que hay que mirar: el hermano
`.cmd` delata la generación. `07-DRIVER/kernel/` tiene además `.o`, `.ko`,
`.mod.o`, `Module.symvers`, `modules.order` y sus `.cmd`, y **ninguno** está en el
manifiesto — así que el filtro funciona para casi todo y falla justo en el formato
que no sabía que existía.

## 5 · CLASE C — 30 sellados perdidos, y por qué NO se re-sellan

Los 30, con su dirección, en `adjud68.json`. Reparto por directorio:

```text
06-INGENIERIA-INVERSA/findings/   14
07-DRIVER/kernel/                  4      <-- fuentes del driver
08-ARQUITECTURA/tools/             5
revkit/                            1
tools/                             6
```

Los cuatro de `07-DRIVER/kernel/` son `rx550_drv.c`, `rx550_drv.h`, `rx550_pm4.c` y
`rx550_pm4.h`, y **no tienen copia en ninguna parte**: no existen en
`04-IMPLEMENTACION/rx550-driver/`, que es el otro árbol de driver del proyecto. Sus
contenidos actuales sí están commiteados (Q2 sí), de modo que **el código está a
salvo**; lo que no está a salvo es **el estado que el manifiesto certificaba**.

**Por qué re-sellar empeora las cosas, y no las arregla.** Q1 responde *"¿existe el
estado sellado?"*. Re-sellar cambia la respuesta a sí y **hace la pérdida
permanente e invisible**: dentro de un mes el manifiesto dirá que ese estado existe,
porque alguien lo re-selló, y ya no habrá nada en el árbol, ni en el reflog, ni en el
historial que diga que hubo un momento en que se certificaba otro contenido.

Es la razón por la que `sello.py` escribe *"un sello que se sobrescribe a sí mismo no
recuerda nada"*, y por la que el coste de esta clase no se paga re-sellando: **se paga
dejando constancia.**

## 6 · El coste de la alternativa, que también es un coste

Los 33 de la clase A **se pueden** re-sellar y siguen sin sellarse. Eso tiene un
nombre: el manifiesto está viejo y **no vuelve a detectar deriva** sobre ellos. No es
gratis, y decir *"no re-sello porque no es seguro"* es sólo la mitad de la verdad.

**Lo que hace falta para cerrarlo sin perder nada:** los 32 re-sellables en un
manifiesto **nuevo** (`--actualizar` escribe a fichero nuevo y no toca el anterior, que
es exactamente para esto), los 3 de B y los 30 de C **dejados fuera con su motivo
escrito**, y los 2 de D **declarados no-evidencia** con la regla del `.cmd` hermano.
Eso es un trabajo de edición y una decisión por clase, no un script, y por eso no está
hecho.

## 7 · PROCEDENCIA

```text
manifiesto   docs/EVIDENCE-MANIFEST.sha256, 245 entradas, generado 2026-10-04 09:59:09
sello        OK 177 · MOVIDO 68 · ROTO 0 · rc=1
custodia     las dos preguntas, ya separadas (b3314b6): 213 recuperables / 32 perdidos
artefacto    /tmp/opencode/adjud68.json · 68 filas × (clase, Q1..Q5)
controles    36 positivos / 32 negativos;  enumeración completa (5 missing = 1058)
escrituras   0 en el árbol.  Nada re-sellado.  Nada commiteado de la otra sesión.
```

**Lo que este documento NO prueba.** No prueba que los 68 sean la lista completa de lo
que ha cambiado desde las 09:59: **el árbol se está escribiendo mientras mido**, y una
entrada puede moverse entre que la leo y la clasifico. No prueba que los 30 de la
clase C no hayan perdido contenido (`NOT_DETERMINED`, y sin línea base no hay diff). No
afirma que re-sellar la clase A sea *innecesario*: §6 dice que tiene un coste, y es
este. Y no toca la GPU.