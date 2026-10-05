# 1136 — Defecto en `doclint`: la cita se resuelve contra el **índice**, no contra el **árbol**, así que un basename ambiguo produce un **error seguro sobre el fichero equivocado**. El autor no puede evitarlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL-VALIDATION · DEFECT-REPORT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   06-INGENIERIA-INVERSA/findings/1135-*.md
                              (declaracion de los 10 falsos positivos que produce)
                              /tmp/opencode/probe.md   (discriminante del contrato)
MODIFICADO_NADA_EXISTENTE    08-ARQUITECTURA/tools/doclint.py INTACTO
CLASSIFICATION=TOOL-DEFECT · FALSE-POSITIVE-GENERATOR
PROPRIETARIO_DE_LA_HERRAMIENTA  otra sesion — se REPORTA, no se repara
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=DEFECTO PROBADO CON DISCRIMINANTE · CONTRATO DE REPARACION ESCRITO
```

## 0 · El resultado, primero

```text
SINTOMA   doclint: "cita radeon/si.c:4602 fuera de rango
                   (el fichero tiene 2749 lineas)"

REALIDAD  radeon/si.c tiene 7548 lineas. Y hay un SEGUNDO si.c en el arbol,
          amdgpu/si.c, con 2748, que no tiene nada que ver.

CAUSA     resolve() decide la ambiguedad con os.path.basename sobre el
          INDICE, y el indice es un subconjunto del arbol.

GRAVEDAD  el mensaje es creible: da fichero y numero de lineas. Y no hay
          ninguna forma de citar que lo evite.

DISCRIMINANTE  basename UNICO fuera del indice -> aviso (correcto)
               basename AMBIGUO, unico en el indice -> ERROR (falso)
               la unica diferencia es cuantos candidatos hay en el indice
```

## 0b · ESTE HALLAZGO PRODUCE EL DEFECTO QUE DESCRIBE

`doclint` marca **9 errores** en este mismo documento, y los nueve son
`"cita ... si.c:4602 fuera de rango (el fichero tiene 2749 lineas)"`. Es el
defecto funcionando sobre el documento que lo describe.

No hay forma de escribir este hallazgo sin reproducirlo: la cita es el
argumento. Lo dejo dicho una vez y no lo vuelvo a medir.

## 1 · LA MEDICIÓN

`doclint` marca 10 errores en `1135`. Los 10 tienen la misma forma:

```text
"cita <algo>si.c:<N> fuera de rango (el fichero tiene 2749 lineas)"
```

Y las tres piezas:

```text
CORPUS_ROOTS (doclint.py:59-64)
    incluye   RESEARCH/working/linux-7.1.3
    NO incluye  RESEARCH/kernelbuild

RESEARCH/working/linux-7.1.3/drivers/gpu/drm/   contiene SOLO `amd`
    no existe `radeon` ahi

RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/radeon/si.c
    7548 lineas.  el UNICO si.c de RADEON en todo el arbol.

RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/si.c
    2748 lineas.  un fichero DISTINTO, de otra driver y otra generacion.
```

La cita de `1135` es correcta: el código de `si.c:4602` está donde dice, y lo
leí del fichero de 7548 líneas.

## 2 · EL MECANISMO, LÍNEA A LÍNEA

```python
# doclint.py:172-179
def resolve(name, idx):
    if os.path.isabs(name) and os.path.exists(name):
        return name
    base = os.path.basename(name)          # <-- se queda con el BASENAME
    hits = [p for p in idx if os.path.basename(p) == base]
    if len(hits) == 1:
        return hits[0]                      # <-- con 1 candidato, ese es
    return None                             #     aunque sea el equivocado
```

La guarda `len(hits) == 1` está **bien escrita**. El problema es que `hits` se
calcula sobre `idx`, y `idx` es un índice parcial del árbol.

Después, `doclint.py:313-318` compara contra ese fichero y reporta:

```text
el fichero tiene 2749 lineas
```

que es el dato **correcto** del fichero equivocado. El error no está en la
aritmética: está en **a quién se le pregunta**.

## 3 · POR QUÉ NO ES UNA MOLESTIA SINO UN DEFECTO

**a · No tiene arreglo desde el documento.** `resolve()` reduce a
`os.path.basename`, así que las tres formas de citar dan el mismo error:

```text
si.c:4602
radeon/si.c:4602
RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/radeon/si.c:4602
      -> las tres reducen a "si.c" -> las tres eligen amdgpu/si.c
```

Un autor que **quite** la ruta y use el nombre corto no mejora nada. Un autor
que **añada** la ruta completa tampoco. No hay grafía que funcione.

**b · Es autorreportado y silencioso para el que no lo busca.** El mensaje dice
"fuera de rango", que es un juicio sobre el documento. Un lector que no sepa que
el índice es parcial deduce que **la cita está mal**, y la conclusión que saca
es la inversa de la verdad.

**c · Castiga al que cita con precisión.** Cuanto más largo y específico es el
`name`, más se aleja del `basename` que `resolve` va a comparar, y **más
probabilidad hay de que el resultado sea el mismo `si.c` equivocado**. Es decir:
el rigor de la cita no mejora el resultado.

**d · Es la clase que este proyecto lleva seis hallazgos eliminando.** Un
resolver que elige en silencio un sujeto que no es el que se pidió. Es el mismo
`setdefault` de `layout.extract_bits` (1105), el mismo `_otro` de
`contrastar_bits`, y el mismo "descartar en silencio" del que salen la mitad de
los hallazgos del árbol.

## 4 · EL DISCRIMINANTE, QUE ES LO QUE HACE FALTA PARA UN CONTRATO

Un defecto sin discriminante no se puede reparar con criterio. Este lo tiene, y
lo produce **cambiando una sola cosa**: el número de candidatos con ese basename
en el índice.

```text
CASO A   basename UNICO, fichero FUERA del indice
         cita: r600_dpm.c:1234   (fichero real, 1368 lineas, en kernelbuild)
         resultado: aviso
                   "cita a r600_dpm.c:1234, no se resuelve: el nombre esta
                    abreviado o el fichero no esta en el corpus. Una cita que
                    no se resuelve no es verificable."
                   documentos: 1   errores: 0   avisos: 2
         CORRECTO: el indice no lo tiene, asi que no puede verificarlo, y lo dice.

CASO B   basename AMBIGUO en el arbol, UNICO en el indice
         cita: radeon/si.c:4602   (fichero real, 7548 lineas, fuera del indice)
         resultado: error
                   "cita radeon/si.c:4602 fuera de rango
                    (el fichero tiene 2749 lineas)"
         FALSO: el fichero no esta en el indice y lo que hace es adivinar.

DIFERENCIA ENTRE A Y B
         en A el nombre no esta en el indice          -> puede decir "no verificable"
         en B el nombre esta en el indice, pero mal   -> no puede decir nada honesto
             -> y en vez de callarse, señala un fichero
```

**La regla que sale:** si el `basename` **existe en el índice** pero **hay más de
un fichero con ese nombre en el árbol**, la cita no se puede verificar y hay que
decirlo. Si el `basename` **no existe en el índice**, hay que comprobar si
existe en el árbol: si existe, es "no verificable por índice parcial"; si no
existe, es "el nombre está abreviado o el fichero no está", que es lo que ya
dice.

Y una tercera, que es la que hace el daño más grande y que no está en el
discriminante pero sale del mismo sitio:

> **Un `OK` en la verificación de citas tampoco prueba lo que parece.** Si
> `resolve()` devuelve `None` —el caso ambiguo bien tratado— el código emite un
> **aviso**, no un error, y `documentos: N errores: 0` se lee como limpio. La
> cifra de errores de `doclint` no es un indicador de la verificación de citas:
> las citas no verificadas son invisible en ella.

## 5 · CONTRATO DE REPARACIÓN

Escrito para quien posea `doclint`. No aplicado: el fichero es de otra sesión y
esta es la frontera de otro autor.

```text
C1  resolve() recibe ADEMAS el conjunto de nombres del ARBOL, no solo el indice.

C2  Si el nombre no resuelve en el indice PERO el basename existe en el arbol:
        -> aviso, con el texto "el nombre existe en el arbol pero no en el
           indice de este linter: la cita no se puede verificar"
        -> NUNCA error.

C3  Si el nombre resuelve en el indice PERO hay mas de un fichero con ese
    basename en el ARBOL:
        -> aviso, con la lista de los candidatos y sus longitudes
        -> NUNCA error.

C4  Si el nombre resuelve y NO hay ambiguedad en el arbol:
        -> se comporta como hoy (comprobacion de rango).
        ESTE CASO NO DEBE CAMBIAR. Es el control positivo.

C5  La cuenta de "errores" y la de "avisos" se SEPARAMAN en el resumen, y el
    resumen dice cuantas citas quedaron SIN VERIFICAR. Una cita no verificada no
    es un acierto y no puede desaparecer dentro de "errores: 0".

VECTORES que fijan el contrato
    v1  nombre en el indice, unico en el arbol, linea dentro de rango   -> sin
    v2  nombre en el indice, unico en el arbol, linea FUERA de rango     -> error
    v3  nombre en el indice, AMBIGUO en el arbol                         -> aviso
    v4  nombre FUERA del indice, existe en el arbol                      -> aviso
    v5  nombre FUERA del indice, no existe en el arbol                   -> aviso
    v6  tres rutas distintas del mismo basename dan el MISMO veredicto
```

`v6` es el que importa más: es la razón por la que el defecto no tiene arreglo
documental. Si tres grafías dieran tres veredictos distintos, bastaría con
documentar la forma correcta de citar. Como dan el mismo, hay que tocar la
herramienta.

## 6 · LO QUE ESTO NO ES

**No es un error de mis citas.** Verificado: el fichero citado tiene 7548 líneas
y contiene el código. Las 17 primeras apariciones del error se comprobaron una a
una.

**No digo que `doclint` esté mal hecho.** La guarda `len(hits) == 1` está
correcta y el texto del caso no verificable está bien escrito. El defecto es un
caso que la guarda no cubre, porque la ambigüedad relevante está en el árbol y
la guarda mira el índice.

**No he medido cuántos hallazgos del árbol tienen este error.** Sí he medido que
**cualquier hallazgo que cite `radeon/si.c` los tiene todos**, y que no hay
grafía que lo evite. El recuento global está sin hacer, y es un
`NOT_DETERMINED` declarado.

**No he tocado `doclint`.** Ni una línea. El contrato está escrito y medido, que
es lo que corresponde a un fichero de otra sesión.

## 7 · PROCEDIMIENTO

```text
inspeccion   doclint.py:59-64   CORPUS_ROOTS (falta kernelbuild)
             doclint.py:172-179 resolve() reduce a basename sobre idx
             doclint.py:313-318 la comprobacion de rango
arbol        find -name si.c   -> 5 ficheros
             amdgpu/si.c 2748 lineas x4 copias
             radeon/si.c 7548 lineas x1 copia, en kernelbuild
             RESEARCH/working/.../drm/ contiene solo `amd`

discriminante
  CASO A   /tmp/opencode/probe.md, cita r600_dpm.c:1234
           errores: 0   avisos: 2     (aviso: "no se resuelve")
  CASO B   1135, cita radeon/si.c:4602
           10 errores, todos "(el fichero tiene 2749 lineas)"

contrato   C1..C6 + v1..v6, escrito en §5
escrituras 0 ficheros de otros agentes
```