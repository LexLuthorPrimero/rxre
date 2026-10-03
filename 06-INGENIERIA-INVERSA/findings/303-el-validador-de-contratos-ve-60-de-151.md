# 303 · El validador de contratos ve 60 herramientas de 151

```text
CLASSIFICATION=MEASUREMENT+ERROR+CONTRADICTION_CANDIDATE · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `302` era que `mutscore --cobertura` dejase de mantener a mano
la lista de banderas. Hecho, y está en `302`.

Lo que sale de aquí es más serio y no estaba en el plan: **la regla de seguridad
que sostiene la afirmación «GPU INTACTA» se comprueba sobre el 40 % de la caja.**

## 1 · De dónde salió

De reparar una cosa pequeña. `toolcheck` marcó `mutscore.py` como
`CONTRATO_INCOMPLETO` porque le faltan tres de las cuatro marcas que exige. Le
puse las tres, y para no hacerlo a ciegas conté cuántos ficheros del proyecto las
tienen.

```text
  %-22s %8s %8s %8s
  directorio         ficheros contrato      sin
  tools                    62        1       61
  08-ARQ                   60       55        5
  revkit                   29        0       29
  ....................................................................
  TOTAL                   151       56       95
```

El único contrato de `tools/` es el que he escrito yo hoy. Y `revkit/` no tiene
ninguno, en el formato que el resto del proyecto usa.

## 2 · Y el validador no los ve

```text
  toolkit.py:65         HERE = os.path.dirname(os.path.abspath(__file__))
  toolkit.py:497        files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))

  contract_exec.py:56   TOOLS = os.path.join(ROOT, "08-ARQUITECTURA/tools")
  contract_exec.py:228  for f in sorted(os.listdir(TOOLS)):
```

Los dos validadores de contrato son **una sola constante de directorio**, y los dos
apuntan al mismo.

```text
  lo que ven                       60 ficheros
  lo que hay                      151 ficheros
  lo que NO ven                    91 ficheros   60 %
```

Y lo que no ven no es una esquina inocua: son **las 62 herramientas de `tools/`**,
que es donde vive el control del proyecto —`govcheck`, `mutscore`, `lint`,
`fingerprint`, `toolcheck`, `nextnum`, `pipeline`— y **las 29 de `revkit/`**.

## 3 · Y hay dos formatos que no se leen entre sí

Al contar, un resultado mío salió mal y la herramienta tenía razón:

```text
  lo que yo medi    '# CONTRACT: name=' en las primeras 2000 lineas   -> 56
  lo que hay        29 ficheros de revkit declaran CONTRATO en comentario, SIN '#'
                    y DENTRO del docstring
```

```text
  08-ARQUITECTURA/tools/toolkit.py     # CONTRACT: name=toolkit
                                        # CONTRACT: WRITES_GPU=no
                                        r"""TOOLKIT ...

  revkit/bootcheck.py                   CONTRACT: name=bootcheck
                                        CONTRACT: WRITES_GPU=no
                                        """              <- dentro del docstring

  el primero se lee con un parser de comentarios
  el segundo necesita un parser que tambien mire dentro del docstring
  y `revkit/` esta en un directorio al que no llega ninguno de los dos
```

Es decir: **aunque un validador se arreglara para recorrer los tres directorios, con
el parser actual seguiría sin leer `revkit/`.** Son dos arreglos, no uno.

## 4 · Por qué importa, con las palabras del propio validador

`toolkit.py:18-24`, de su propio docstring:

```text
  El riesgo no es cosmetico. Una herramienta que escribe en el hardware sin
  declararlo es la peor clase de herramienta en un proyecto de ingenieria inversa:
  nadie sabe si al ejecutarla se toco la GPU. Este proyecto lleva 40 rondas
  declarando GPU INTACTA, y eso solo es creible si hay algo que lo compruebe y no
  una promesa.
```

Y la regla 1 que ese mismo fichero declara comprobar:

```text
  Una herramienta que diga WRITES_GPU no puede existir en la caja. Si aparece, el
  validador falla.
```

```text
  LA AFIRMACION "GPU INTACTA" SE SOSTIENE CON UN VALIDADOR
  Y ESE VALIDADOR MIRA EL 40 % DE LA CAJA
  Y EL 60 % QUE NO MIRA INCLUYE TODAS LAS HERRAMIENTAS DE REVKIT,
  DE LAS CUATLAS CUATRO QUE MENCIONAN WRITES_GPU
```

## 5 · Y lo que NO se establece, que es lo importante

```text
  si alguna de esas 91 herramientas ESCRIBE en la GPU
    NO HAY EVIDENCIA DE QUE SI. Se ha mirado una muestra:
      revkit/bootcheck.py    0 escrituras a /dev/mem, ni a /sys/bus/pci, ni a /proc/bus/pci
      revkit/gputel.py       0 escrituras crudas; solo lee /sys/class/drm/
      revkit/gfx8blocks.py   0 escrituras crudas
    Y las cuatro que declaran WRITES_GPU lo declaran como `no`.
    O sea que el riesgo NO ESTA DEMOSTRADO. Lo que no esta es la VERIFICACION
  si el validador fallaria si una de las 60 escribiera en la GPU
    NO COMPROBADO. Se cree que si, porque la regla esta escrita y `--strict`
    devuelve 2, pero no se ha provocado una herramienta con WRITES_GPU=yes para
    ver si el validador la rechaza. Es el mismo metodo que `294` y `300`: falta
    PROVOCAR el fallo
  las 91 sin contrato, una por una
    SIN LEER. Ni una. Lo que hay es un recuento, y un recuento no dice si una
    herramienta concreta es peligrosa
  si las 29 de revkit necesitan contrato
    NO DECIDIDO. Puede que `revkit` se considere material de investigacion y no
    caja. Pero entonces el criterio esta escrito en ninguna parte, y una
    herramienta que se pone ahi no tiene ninguna regla que la obeyed
```

## 6 · La regla

```text
  UN VALIDADOR CON UNA CONSTANTE DE DIRECTORIO NO ES UN VALIDADOR DEL PROYECTO
  ES UN VALIDADOR DE UN DIRECTORIO, Y SU ALCANCE HAY QUE DECIRLO EN SU SALIDA
```

`toolkit` imprime `herramientas en .../08-ARQUITECTURA/tools: 59` en su informe, y
eso es honesto: **sí dice dónde mira**. El problema no es que mienta. Es que el
número se ha estado leyendo como «las herramientas de la caja» cuando es «las de
este directorio».

Y el mecanismo por el que se ha encontrado no es un barrido: es que `toolcheck`
señaló **un** fichero, y al mirar el denominador salieron 91. Un validador que
señala un fichero es útil; el mismo validador con el recuento al lado es el que da
la respuesta.

## 7 · Trazabilidad

```text
  tools/toolcheck.py:57             REQUIRED_MARKS, el que señaló mutscore
  tools/mutscore.py                 las tres marcas, y el contrato que declara
  08-ARQUITECTURA/tools/toolkit.py:18-24   el riesgo, en su propio docstring
  08-ARQUITECTURA/tools/toolkit.py:65      HERE, el alcance real
  08-ARQUITECTURA/tools/contract_exec.py:56   TOOLS, el otro alcance
  revkit/bootcheck.py:40-46         el segundo formato de contrato
  findings/301                      la herramienta que dio el denominador
```

## 8 · Corrección de numeración

```text
  este fichero se escribio como 303, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 303  RESERVADO
```
