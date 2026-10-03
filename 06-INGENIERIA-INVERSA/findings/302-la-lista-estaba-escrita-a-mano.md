# 302 · La lista estaba escrita a mano, y al derivarla el número bajó de 472 a 329

```text
CLASSIFICATION=ERROR+MEASUREMENT+TOOL · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `301` era que `mutscore --cobertura` dejase de mantener a mano
la lista de banderas, porque esa lista es lo que dio dos hallazgos
seguidos de error (`298` y `300`).

Hecho. Y al derivarla el número **no se quedó igual**: bajó de 472 a 329. Eso
obliga a explicar de dónde sale cada cifra, y la explicación son **dos causas
independientes**, y solo una tiene que ver con el descubrimiento.

## 1 · Lo que hay ahora en vez de la lista

```python
  def descubrir_casos(raiz):
      #  la bandera de self-test  -> flags_inventory.candidatos_self, que es
      #                             HEURISTICA, y por eso no se acepta sola
      #  las rutas de informe    -> flags_inventory.flags_de_ruta_del_selftest,
      #                             que lee el `for _flag in (...)` que el
      #                             propio self-test tiene escrito
```

Y el resultado, sin que nadie le diga nada:

```
  DESCUBIERTO del fuente, no escrito a mano:
    toolkit.py        --selftest-ajenas   ['--strict', '--sin-fallar', '--table']
    fingerprint.py    --selftest          ['--json']
    lint.py           --selftest          ['--censo', '--solo ANGLICISMO']
    nextnum.py        --selftest          ['--json', '--check 291']

  FUERA, con el motivo (0):
```

Esos cuatro argv son **exactamente** los que estaban escritos a mano. La
derivación acierta, y eso es lo que hace que el número tenga que explicarse.

### Y hay dos estados que se rechazan, y son distintos

```text
  0 candidatos a self-test, y hay rutas   -> FUERA, no se elige
  2 o mas candidatos                      -> FUERA, no se elige
  no parsea                               -> FUERA, con el error
  1 candidato y N listas de ruta          -> CASO
```

Elegir un candidato entre varios sería repetir el error de `298` con más
automatismo. El vector lo comprueba con una herramienta sintética de dos
candidatos: **queda fuera, no se elige**, y el motivo sale impreso.

## 2 · Por qué bajó el número: la mitad no es culpa del descubrimiento

```text
                              300          302        diferencia
  govcheck  self-test          347          347              0
  govcheck  + banderas         392          254            -138
  govcheck  NUEVAS             143            5            -138
  govcheck  total              490          352            -138
```

**El self-test de `govcheck` sigue en 347 líneas.** Lo que cambió es su ruta de
informe, que **hoy mide 254 y antes medía 392**: 138 líneas menos.

Y eso tiene una causa concreta: `govcheck` se ha editado durante esta sesión
(`terminos()`, `sello()`, `citas_de_codigo()`), y las líneas que su informe
ejecutaba antes ya no están. La cifra de `300` estaba **caducada por una razón que
no tiene nada que ver con el descubrimiento**.

```text
  UNA CIFRA DE COBERTURA CADUCA CUANDO EDITAS LA HERRAMIENTA QUE MIDE
  Y NADIE AVISA, PORQUE EL SELF-TEST SIGUE PASANDO
```

Eso es una OBSERVACIÓN general que aplica a todo el proyecto, no solo a esta tabla.

## 3 · Y la otra mitad: 143 líneas que solo existían porque el auditor las tenía escritas

```text
  472  =  5 herramientas, con 5 banderas escritas a mano en el auditor
  334  =  las mismas 5, con las banderas que CADA self-test declara ejercitar
  329  =  las 4 que hoy tienen la lista `for _flag in` en su self-test
```

```text
  472 - 143 (govcheck ya no aporta) + 5 (lo que aportaria hoy)  =  334
  334 - 5  (govcheck no tiene lista de ruta, luego no se descubre)  =  329
```

Las 143 líneas de `govcheck` eran **reales para la invocación que hacía
`mutscore`**, pero nunca fueron una propiedad del self-test de `govcheck`: esa
herramienta **nunca ha recibido vectores de ruta**, que es un pendiente que se
abrió en `297`, se anotó en `298` y se cerró a medias en `300` para `fingerprint`
y `toolkit`.

Lo que había era cobertura que existía únicamente porque el auditor la tenía
escrita. Eso no es cobertura del self-test. Es cobertura del auditor.

```text
  COBERTURA QUE SOLO EXISTE PORQUE EL AUDITOR LA ESCRIBIO A MANO
  NO ES COBERTURA DE LA HERRAMIENTA. ES COBERTURA DEL AUDITOR.
```

Y la herramienta nueva no puede distinguirlo sin mirar, porque no hay lista de
rutas que leer. Por eso `govcheck` se queda fuera, y por eso **no es un
incidente**: es el estado real de `govcheck`.

## 4 · Y el coste de cerrarlo, medido y con la cautela de `299`

```text
  govcheck --selftest     7 516 ms   y 12 739 ms   en dos medidas seguidas
  govcheck --json         5 396 ms
  govcheck --limite 2     4 339 ms   sin --json
  govcheck --json --limite 2   4 295 ms
```

Tres cosas de ahí:

- **`--limite` no abarata nada.** 4,3 s con y sin `--json`. La bandera recorta la
  salida, no el trabajo, que es el mismo error de coste que el de `297`.
- **El self-test de `govcheck` se mide entre 7,5 y 12,7 s**, un factor 1,7 en el
  mismo minuto. Es el ruido de cronómetro de `299`, y por eso aquí no se escribe
  «costará X»: se escribe que no se ha medido con la máquina descargada.
- Con un vector de ruta, su self-test pasaría de ~7,5 s a ~13 s. Es asequible y
  no es gratis, y el trabajo de `govcheck` es de los que grow.

## 5 · Cuarto vector mío mal, y el patrón ya es una regla

`flags_de_ruta_del_selftest` tuvo tres expectativas mías equivocadas y las tres
las contestó la herramienta:

```text
  1  espere duplicados      la funcion duplicaba de verdad  -> la leia bien
  2  espere una lista plana di una lista plana, SIN el valor
                          `ANGLICISMO`, porque no es bandera  -> la herramienta
                                                                    tenia razon
  3  espere un nivel de
     anidamiento de menos   se me olvido la lista de bucles  -> error mio
```

La segunda es la que enseña algo, y no sobre la herramienta:

```text
  ANCLAR        ["--solo", "ANGLICISMO"]
  APLANA        ["--solo"]
  INVOCAR APLANA  ->  rc=2, por falta de argumento
                  ->  y ejecuta la RUTA DE ERROR de argparse, no la de --solo
```

Es decir: **aplanar los argv mide otra cosa sin decirlo.** Por eso el dato es un
argv por elemento de la tupla, y no una lista de banderas.

La regla que sale de cuatro casos ya:

```text
  UN VECTOR ESCRITO A MANO DICE LO QUE EL CODIGO DEBERIA HACER
  LA HERRAMIENTA DICE LO QUE EL CODIGO HACE
  Y CUANDO DISCREPAN, LA HERRAMIENTA TIENE RAZON EN 4 DE 4
  PORQUE YO ESCRIBO LA EXPECTATIVA DE INTUICION Y NO LA DE MEDIDA
```

Y el corolario que ya no es opcional: **el self-test tiene que construirse
mirando la salida real de la herramienta, no el código que se acaba de escribir.**

## 6 · Lo que NO se establece

```text
  si el descubrimiento cubre mas herramientas cuando mas tengan listas de ruta
    SI, por construccion: basta con que escriban el `for _flag in`. Y ahora se
    PUEDE saber, porque `descubrir_casos` imprime las que quedan fuera y el
    motivo. Antes habia que mantener una lista; ahora hay que hacer que una
    herramienta declare lo que ya hace
  si 143 era el numero correcto para `govcheck` en su momento
    SI, en aquel momento. `govcheck --json` ejecutaba 392 lineas. Hoy ejecuta 254.
    No se ha ido por el descubrimiento: se ha ido porque la herramienta cambio
  cuanto de las 254 lineas actuales de `govcheck` son utiles
    NO_DETERMINADO. Se sabe que son pocas nuevas (5). No se ha leido ninguna, y
    5 lineas nuevas es un numero que NO significa «la ruta esta probada»
  las 6 vias de lectura de banderas de `301` mas `for _flag in`, que es la septima
    La septima no es una via de LECTURA de banderas por parte del usuario, es una
    via de DECLARACION por parte del self-test. Y es la que no admite heuristica,
    que es justo por la que `mutscore` puede fiarse
  el numero de candidatos ambiguos en el arbol real
    MEDIDO: `mutscore` mismo tiene 3 (`--self`, `--selftest`, y `--se...`). No se ha
    mirado por que, y no importa para cobertura porque no tiene listas de ruta,
    pero importa para cualquier herramienta que quiera auto-descubrirse
```

## 7 · Trazabilidad

```text
  tools/flags_inventory.py            candidatos_self() y
                                      flags_de_ruta_del_selftest(), 28 vectores
  tools/mutscore.py                   descubrir_casos(), 29 comprobaciones
  findings/300 §2                     el error de `--self` que motiva todo esto
  findings/301 §5                     el metodo, y las seis vias
  findings/299 §4                     el ruido de cronometro de estos numeros
```

## 8 · Corrección de cifra

```text
  este fichero se escribio como 302, reservado con --reservar antes de escribir

  CORRIGE A findings/300 §3bis
    la tabla de cobertura y la cifra de 472 lineas
    motivo: una de las cinco filas usaba banderas escritas a mano en el auditor, y
    una de ellas (`govcheck`) no era una propiedad del self-test de `govcheck`.
    Ademas la cifra de esa fila habia caducado porque `govcheck` se edito hoy
    300 NO SE EDITA. Esta seccion es la correccion
    y el numero vigente es 329, con la composicion del §3
```
