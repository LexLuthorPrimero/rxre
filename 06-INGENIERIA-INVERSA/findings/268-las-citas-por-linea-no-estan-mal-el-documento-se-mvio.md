# 268 · Las citas por línea no están malas: el documento se movió debajo de ellas

```
CLASSIFICATION=MEASUREMENT+ERROR+TOOLING · TRACK=VERIFICATION
CORPUS=NINGUNO (el proyecto y su git) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`264` medió que hay 28 citas del tipo `AGENTS.md:118` en los hallazgos, y
`govcheck` las declaraba **`INCOMPARABLE`**: el número existe y no significa lo
que significaba.

Eso era una conclusión prematura. **git conserva seis versiones del documento
rector**, y una cita por línea se puede contrastar contra las seis. Lo que no se
puede es saber cuál era la vigente, y eso es `AMBIGUO`, no `INCOMPARABLE`.

Al medirlas sale algo que cambia el diagnóstico por completo.

## 1 · El inventario, lado a lado

```
  28 citas por linea, en 17 lineas distintas

  COMPARTE_TERMINO     2
  DISPARADOR          25
  SIN_TEXTO            1
```

Cada fila pone al lado qué afirma el hallazgo y qué dice la línea citada. Las
primeras:

```
  017  afirma:  Esto es la frontera abierta de AGENTS.md:140-143
       cita  :  ## Falsification and verification

  018  afirma:  Clasificar `hardware execution ordering` (AGENTS.md:141)
       cita  :  - check the object by name, not a relative of it — `which X`
```

Eso, a primera vista, son citas malas. **Y son casi lo contrario.**

## 2 · El contenido existe, en otra línea

```
  version de AGENTS.md    lineas   "hardware execution ordering"   JERARQUÍA
  6fb9113                    1060                     176              46
  daec702                     984                     173              46
  ..................................................................
  lo que citan los hallazgos              141                  46-88
```

```
  46 RESUELVE en las dos versiones commiteadas
  141 NO:  el contenido estaba en 173 y 176
```

**Las líneas se desplazaron al editar el documento**, y los hallazgos se escribieron
contra la versión en la que el contenido estaba donde ellos dicen.

## 3 · Y esa versión no está en git

```
  6fb9113  1060 lineas   CITA=0   <- la mayor commiteada
  daec702   984 lineas   CITA=0
  1bb4115   332 lineas
  4a437ac   301 lineas
  6fe40b2   276 lineas
  54b3ea8   255 lineas
  ...............................................
  la que rigio durante la sesion   1101 lineas   CITA=1
  V6, la que hay ahora              3736 lineas   CITA=0
```

**Ninguna versión commiteada tuvo `LA CITA QUE SE SOSTIENE`.** La de 1101 líneas
estaba solo en el árbol de trabajo, y el pegado de V6 la sobrescribió.

Así que la secuencia completa es:

```
  las citas eran CORRECTAS al escribirse
  el documento fue editandose y las lineas se movieron
  la version contra la que eran correctas no se commiteo
  y se perdio
```

## 4 · Por qué eso importa más que "las citas están rotas"

Una cita colgante **se ve**: `grep` no la encuentra y salta. Una cita que resuelve
a texto ajeno **se lee como si estuviera bien**, y nadie la va a revisar.

Y aquí hay un agravante concreto: el mecanismo de reparación del proyecto reescribe
la referencia para que resuelva. `REF-EXCEPTIONS.txt` documenta un caso donde se
**decidió NO corregir** una referencia rota, y el motivo era exactamente éste:

> Corregirla a `023-` haría que 021 contara una colisión con dos ficheros 022
> cuando uno jamás existió con ese nombre: se arreglaría la referencia rompiéndola.

La misma lógica, más grande: **corregir estas 28 citas a la baja sería reescribir
el hallazgo para que encaje con una versión del documento que no existe.** El
número correcto no se conoce, porque el documento que lo fijaba no se guardó.

## 5 · Lo que `govcheck` hace con eso, y lo que no

```
  ESTABLE        las N versiones dicen lo mismo en esa linea
  DIVERGE        las versiones dicen cosas distintas
  PARCIAL        solo algunas versiones tienen esa linea
  FUERA_DE_RANGO ninguna la tiene

  y en el inventario, sobre la afirmacion y el texto citado:
  COMPARTE_TERMINO    comparten al menos un termino
  DISPARADOR         no comparten ninguno
  SIN_TEXTO          no hay linea que citar
```

`DISPARADOR` **no es un error**, y el propio informe lo dice antes de listarlos,
con los números medidos a la vista. Se llama disparador y no error porque hay un
caso legítimo con solape cero: un hallazgo que se apoya en la **posición** de una
sección en vez de en su texto no tiene término que compartir y su cita sigue
valiendo.

Y el solape de términos es una **señal**, no un veredicto. La herramienta no
corrige ninguna cita y no podría: decidir si una cita sostiene una afirmación es
una lectura.

## 6 · Tres errores propios en esta ampliación

```
  1  dos vectores de govcheck AFFIRMANBA lo contrario de lo correcto:
     uno decia que "terminos" no debe incluir "clasificar", cuando es
     justamente una palabra significativa. El vector estaba mal, no la funcion.

  2  main() usaba una variable `raiz` que no existia alli. NameError en la
     primera ejecucion del informe, que es donde se nota.

  3  un test de dientes que NO FUNCIONABA: mute un campo que nadie lee
     (`estado_linea`) en vez del clasificador, y el self-test seguia pasando.
     Volver a mutar bien --el clasificador diciendo SIEMPRE ESTABLE-- deja
     17 lineas en ESTABLE y cae 2 vectores. Ese es el que prueba algo.

  4  y un ideograma colado otra vez en la palabra "terminos", el septimo de la
     mismo tipo de la sesion. Los siete han sido en texto largo, que es donde
     cae la atencion: eso es lo que 189 mide y lo que sigue siendo verdad.
```

El tercero es el que más dice: **una prueba de dientes que no muerde es peor que
ninguna**, porque se lee como si la propiedad estuviera vigilada.

## 6 bis · El ultimo tramo, y una clase que overestimate lo que se media

Quedaba una pregunta por cada `DISPARADOR`: ¿está su contenido en alguna de las
seis versiones commiteadas? Eso es una búsqueda, y se implementó.

El primer resultado fue `LOCALIZABLE: 13`, con estas coincidencias:

```
  017  cita AGENTS.md:140-143  ->  6fb9113:797   '- tiene nombre conocido;'
  018  cita AGENTS.md:141      ->  6fb9113:8     'AMDGPU, Linux DRM, Mesa, ...'
  019  cita AGENTS.md:666-678  ->  6fb9113:497   'No asumir coherencia por analogía.'
```

Y eso **no** es el contenido que las citas buscaban. La clase afirmaba mas de lo
que el metodo sostiene, y habia colado un texto sin formato.

### Lo que se midió para saberlo

La tasa de coincidencia dentro del documento, es decir cuántas de sus 1060
líneas comparten ≥2 términos con la afirmación:

```
  017   1 línea    0,1 %
  018   3 líneas   0,3 %
  023   4 líneas   0,4 %
  024   2 líneas   0,2 %
```

**El criterio discrimina dentro del documento**: entre 1 y 4 líneas de 1060. Eso
descarta el ruido.

### Y por qué aun así no bastaba

Porque el vocabulario de los hallazgos y el de `AGENTS.md` **se solapan por
construcción**: los dos hablan del mismo proyecto, con los mismos términos. Una
coincidencia de 1 en 1060 dentro de ese campo no es casual, pero tampoco es
prueba: es un **eco del tema**.

```
  017 cita una "frontera abierta" y encuentra "- tiene nombre conocido;"
  eso no es una coincidencia fuerte. Es una coincidencia POCO MAS FUERTE que
  el azar, en un documento donde las palabras coinciden por los dos lados.
```

### Cómo quedó la clase

`LOCALIZABLE` pasó a **`COINCIDE_UN_TERMINO`**, que es exactamente lo que el
método mide: hay una única línea del documento con esos términos.

Y el informe dice, antes de listarlas, que no son «el contenido está aquí», que
el vocabulario se solapa por construcción, y que **leer la línea es lo que
decide**. La herramienta las imprime para que la lectura sea de una pasada.

```
  la clase dice lo que el metodo sostiene
  la LECTURA dice si la clase sirve, y no la hace la herramienta
```

Es la frontera que este proyecto lleva toda la sesión: automatizar lo que se
puede medir, y no automatizar el juicio.

## 7 · Lo que NO se establece

```
  cual era la version vigente cuando se escribio cada cita
    AMBIGUO: hay seis commiteadas y la que valia no esta. Sin un sello de tiempo
    en la cita no se puede elegir, y adivinar seria inventar
  el texto exacto de la linea 141 de la version de 1101
    NO RECUPERABLE. No esta en git, ni en disco, ni en stash
  si las citas fallen en su mayoria
    NO SE AFIRMA. 2 de 28 comparten termino, lo que NO demuestra que esten bien:
    una cita correcta por POSICION tambien puede no compartir termino
  la convencion CITA=/TERMINO=/ROL=
    NO RECUPERABLE del repositorio, y no declarable en el documento rector por
    decision del usuario. Su unico registro escrito son las cabeceras de las tres
    herramientas y los hallazgos que las usan
```

## 8 · Trazabilidad

```
  tools/govcheck.py              la auditoria, 16 comprobaciones, --json
  git log -- AGENTS.md           las 6 versiones commiteadas
  git show <c>:AGENTS.md         el texto de cada linea citada, por version
  tools/REF-EXCEPTIONS.txt       el precedente de NO corregir una referencia
  findings/264                   la sustitucion del documento rector
  AGENTS.md                      NO MODIFICADO, por decision del usuario
```