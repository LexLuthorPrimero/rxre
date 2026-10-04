# 1059 — `sello.py --custodia` pregunta si el **fichero** está en HEAD, cuando la pregunta que importa es si el contenido **sellado** está en algún objeto: se separan en 30 de 245

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=revkit/sello.py:133-239 (custodia) · docs/EVIDENCE-MANIFEST.sha256
         cableado en revkit/check.sh:504
ALCANCE=245 entradas del manifiesto · 7612 blobs leidos · 0 escrituras
ESTADO=PROBADO · el defecto NO esta reparado (ver §6)
herramienta   /tmp/opencode/adjudica.py
instrumento   RESEARCH_INSTRUMENT de una sola tirada, NO promovido a tools/.
              Su contrato (Q1..Q4) esta en §2; sin hash porque no se sella:
              vive fuera del arbol y un sello de algo que no esta en el arbol
              seria una cifra que nadie podria comprobar.
```

## 0 · El resultado, primero

`sello.py` está **en rojo ahora mismo**: `OK 177 · MOVIDO 68 · ROTO 0`. Y su modo
`--custodia` dice:

```
sellado + commiteado  (detecta y recupera)     243
```

**Para 30 de esas 243, "recupera" es falso.** El contenido que el manifiesto sella
**no está en ningún objeto del repositorio**: ni en un commit, ni en el reflog, ni
como objeto suelto. La ruta está en HEAD, que es lo que `custodia` comprueba. El
contenido sellado no.

## 1 · POR QUÉ ES UN DEFECTO Y NO UNA OBSERVACIÓN

El propio `sello.py` escribe, en su docstring, la distinción correcta:

> El sello DETECTA la corrupcion. El commit RECUPERA la perdida. Son preguntas
> distintas, y una no implica la otra.

Y en la salida de `custodia`, la etiqueta es literal:

```
sellado + commiteado  (detecta y recupera)
```

**La implementación hace `ls-tree -r HEAD --name-only` y compara conjuntos de rutas.**
Es decir: pregunta *"¿existe este path?"*, que es la versión débil de la segunda
pregunta, y la etiqueta lo llama "recupera". Para un fichero cuyo contenido cambió y
se commiteó, es cierto. Para uno cuyo contenido cambió y **nunca se commiteó**, es
falso, y no hay forma de que la herramienta lo note.

**Las dos preguntas se separan en 30 entradas, y esa separación es exactamente lo
que la puerta no ve.**

## 2 · EL MÉTODO, Y POR QUÉ SE PUEDE CREER

Para cada entrada que hashea distinto:

| # | pregunta | cómo se contesta | coste |
|---|---|---|---|
| Q1 | ¿el contenido **sellado** es recuperable? | se hashean los **7612 blobs** de `--batch-all-objects` (sueltos **e inalcanzables**, que `rev-list` no ve) y se busca el sha256 del manifiesto | 7612 hasheos |
| Q2 | ¿el contenido **actual** está commiteado? | `sha256(git cat-file blob HEAD:<path>) == sha256(working tree)` | 68 lecturas |
| Q3 | ¿hay cambios sin commitear? | `git diff --quiet HEAD -- <path>` → **rc**, no stdout | 68 llamadas |
| Q4 | ¿el último commit encogió el fichero? | `git show --numstat` | 68 lecturas |

**Se usa `--batch-all-objects` y no `rev-list --all` a propósito**: el contenido
sellado puede ser justo lo que ya no referencia ningún commit, que es el caso que
importa. Un recorrido por ramas habría dado "no lo encuentro" también en los 33
casos en los que sí está, y no habría podido distinguir.

### El método está validado por sus propios controles positivos

```
sellado_recuperable=True    36      (las clases A y B)
sellado_recuperable=False   32      (las clases C y D)
```

**Si la enumeración estuviera perdiendo objetos, los 36 positivos también fallarían.**
Un método que no encuentra nada daría 68 negativos, no 32. Y la enumeración es
completa: `git count-objects -v` dice 760 sueltos + 10093 en pack; el recorrido ve
10840 entradas, **5 de ellas `missing`, que son exactamente los 5 objetos sueltos de
tamaño cero** de `1058 §4`.

## 3 · LAS CUATRO CLASES, Y POR QUÉ NO SE COLAPSAN EN UNA

`ROTO 0` y `MOVIDO 68`. Los 68 se reparten así:

| clase | n | qué es | ¿contenido sellado a salvo? |
|---|---|---|---|
| **A** `EDIT_COMMITTEADA` | **33** | el fichero cambió y el cambio está commiteado | **sí** |
| **B** `EDIT_SIN_COMMIT` | **3** | cambió y **no** está commiteado | **sí** |
| **C** `SELLADO_PERDIDO` | **30** | el contenido sellado **no está en ningún objeto** | **NO** |
| **D** | **2** | `07-DRIVER/kernel/rx550.mod.c` y `rx550_drv.mod.c`: sin commitear y sello no recuperable | no |

A y B juntos son 36 y son el caso benigno: el manifiesto está viejo y el contenido
está a salvo. Los 3 de B son `tools/cap_census.py`, `tools/trace_path.py` y
`revkit/dires.py`, que son **trabajo sin commitear de otra sesión activa** en este
mismo árbol — no pérdida, pero sí otra razón por la que un `MOVIDO` no significa
"corrupción".

Los 2 de D son artefactos de build generados y nunca commiteados: no hay nada que
recuperar porque nunca hubo nada commiteado. Es exactamente lo que
`sello.py --custodia` ya declara aparte como los 2 *"SELLADOS SIN COMMIT"*.

**Y los 30 de C son la clase que no existe en la taxonomía actual.**

## 4 · DEMOSTRACIÓN, UN CASO COMPLETO

```
fichero   06-INGENIERIA-INVERSA/findings/018-execution-order-invalidacion-gfx8.md
sellado   fc119aaac65f050e6f4578056de9f7e6e1bcb6228c02484be20544b41cd96318
HEAD      blob c69d8fd9ffe5  ->  sha256 d2b50415eba79b26
ahora     sha256 d2b50415eba79b26        (= lo que sello.py llama "obtenido")
```

Los cuatro datos encajan y cierran la cadena: el fichero se commiteó, su contenido
**actual** es el de HEAD, y el contenido **sellado** no aparece en ninguno de los 7612
blobs.

**Y `sello.py --custodia` no lo nombra en ninguna de sus listas**, es decir: lo cuenta
dentro de los **243 "detecta y recupera"**.

## 5 · ¿SE PERDIÓ CONOCIMIENTO? `NOT_DETERMINED`, Y POR QUÉ NO PUEDO DECIR MÁS

Este es el punto donde es tentador cerrar el hallazgo y no se debe.

| lo que sé | lo que NO sé |
|---|---|
| el estado sellado de 30 entradas **no existe** en el repositorio | si esos 30 ficheros **perdieron** algo |
| ninguno de los 30 **encogió** en su último commit | si perdieron tanto como ganhar |

MEDIDO sobre el último commit de cada uno: **25 crecieron, 5 quedaron con el mismo
tamaño, 0 encogieron.** Pero un fichero puede perder 50 líneas y ganar 50, y **sin la
línea base no hay diff posible**. Que la dirección sea benigua **no es** lo mismo que
que no haya pérdida, y confundir las dos cosas es exactamente el error que este
proyecto mide.

```
PROVEN           30 de 245 entradas tienen su contenido sellado en ningún objeto
NOT_DETERMINED   si eso supone pérdida de conocimiento en alguna de ellas
```

**Lo que sí es `PROVEN` y es lo peor:** no hay ningún mecanismo en el árbol que
pudiera enterarse de esto. `sello.py` solo compara lo declarado con lo actual; si un
sellado desaparece, no hay ningún estado del sistema que lo refleje.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ NO LO HICE

**No he reparado `sello.py`.** El arreglo son unas líneas: en `custodia`, cambiar la
pregunta de *"¿la ruta está en `ls-tree HEAD`?"* por *"¿existe un objeto cuyo sha256
sea el declarado?"*. Es barato y es justo lo que convierte un rojo ambiguo en un rojo
informativo.

No lo he hecho porque **este hallazgo es una medición y la reparación es otra
acción**, y meterlas juntas es lo que produce mediciones que nadie puede
reproducir. El contrato de la reparación, para que no se pierda:

```
REPARACION = custodia() responde la pregunta Q1, no la Q2
  lee los sellados del manifiesto
  hashea los blobs de --batch-all-objects
  etiqueta "sellado + commiteado" SOLO si el contenido sellado esta
  anade una clase: SELLADO_PERDIDO (nunca lo hubo)
  NO baja el rc por ello: es un hecho que hay que mirar, no un fallo del sello
TEST       control positivo con un sellado cuyo blob se sabe que existe
            control negativo con un sellado inventado
INVARIANTE no cambia lo que ya devolvia para las 214 entradas con Q1 = True
```

Y **tampoco he re-sellado el manifiesto.** `sello.py` lo dice y con razón: *"volver a
sellar un fichero que cambió sin mirarlo convierte un detector de derivas en un
detector de cambios"*. Los 68 requieren una decisión **fichero a fichero** — ¿cambio
legítimo o pérdida? — que un script no puede tomar, y que además tiene que tomar
alguien que mire. **Aquí no lo ha hecho nadie, y ese es el agujero de fondo.**

## 7 · MI PROPIA MEDICIÓN TENÍA UN BUG, Y LO DICE EL HALLAZGO

Antes de reportar nada comprobé el método contra el código, y encontré esto en **mi**
guion:

```python
sucio = bool(git('diff','--quiet','HEAD','--',p))     # MAL
```

`git diff --quiet` está **diseñado para no imprimir nada**: su veredicto está en el
código de salida. `bool(stdout)` es `False` **siempre**, así que `sucio` salía `False`
para los 68 ficheros.

**La clase C no depende de `sucio`** — su condición es `no recuperable Y actual
commiteado` — así que **la cifra de 30 se sostiene**. Pero A y B sí dependían, y la
primera medición era incorrecta. Corregido y repetida:

| | antes (mal) | después |
|---|---|---|
| A `EDIT_COMMITTEADA` | 33 | 33 |
| B `EDIT_SIN_COMMIT` | **0** | **3** |
| C `SELLADO_PERDIDO` | 30 | **30** |
| D | **5** | **2** |

Los 3 ficheros de B aparecieron al arreglarlo. **Si hubiera reportado la primera
tabla, el hallazgo principal habría sido el mismo y el detalle habría sido falso**,
que es como se cuela un error pequeño hasta que alguien depende de él.

## 8 · PROCEDENCIA

```text
artefacto    /tmp/opencode/adjudicacion.json   (68 filas, con las 4 respuestas)
metodo       7612 blobs leidos con git cat-file --batch (SOLO lectura)
manifiesto   docs/EVIDENCE-MANIFEST.sha256, generado 2026-10-04 09:59:09
sello        revkit/sello.py -> OK 177 · MOVIDO 68 · ROTO 0 · rc=1
custodia     revkit/sello.py --custodia --todos -> 243 / 2 / 6153 / 0
controles    36 positivos / 32 negativos; enumeracion completa (5 missing = los 5 de 1058)
scripts      /tmp/opencode/adjudica.py   NO promovido a tools/ -- ver §6
escrituras   0 en el arbol.  `git fsck` de 1058 §4 ya habia escrito; esta iteracion no
```

**Lo que este documento NO prueba.** No prueba pérdida de conocimiento (§5). No prueba
que los 30 sean la clase correcta: la clasificación depende de que `--batch-all-objects`
enumere todo, y eso lo valida el recuento de `count-objects`, no una prueba de que no
falte ningún objeto empaquetado. No toca la GPU, no ejecuta el driver y no mide
rendimiento. Y **no repara nada**: el manifiesto sigue con los mismos 68 `MOVIDO`.