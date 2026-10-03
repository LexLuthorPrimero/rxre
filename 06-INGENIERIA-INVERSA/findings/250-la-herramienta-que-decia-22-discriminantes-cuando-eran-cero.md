# 250 · La herramienta que decía 22 discriminantes pendientes cuando eran cero

```
CLASSIFICATION=ERROR+MEASUREMENT+CONTRADICTION+CORRECTION · TRACK=VERIFICATION
CORPUS=RESEARCH/working/RX550-INVESTIGACION · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`routeaudit.py` es la herramienta que decide qué discriminantes dependen de una
ruta que no se puede leer. Es decir: la que decide qué trabajo está **bloqueado**
y qué trabajo está **pendiente de investigar**. Su salida principal era:

```
journalctl -k    22 menciones pendientes, pero la ruta SI es alcanzable
```

Se iba a construir una iteración entera sobre ese 22. **El número correcto es 0.**

```
de las 22 que marcaba, lineas que empiezan por PENDIENTE=    0
de las 22, lineas de prosa que YA habian resuelto algo       22
```

## 1 · Qué son esas 22 líneas

Ninguna es un discriminante abierto. Todas son prosa que registra una
observación ya hecha:

```
086:157  - `HOST_OBSERVATION` -- sysfs (`mem_info_*`, ...), `journalctl`.
163:234  - `OBSERVED` -- `journalctl -k -b` de la sesión en curso, sin root...
236:155  - `OBSERVED` -- `journalctl -k -b`, las nueve líneas
```

Es decir: **el trabajo ya se hizo**. `233` se titula precisamente
*log observado polaris12 y cero crtc*, y su línea 234 dice `OBSERVED`.

## 2 · La causa: una ventana de 500 caracteres

`routeaudit.py` tiene dos caminos, y son de calidades distintas:

```
PEND_RX     el ESTRUCTURADO: una linea PENDIENTE=...|NECESITA=...|ALCANZABLE=
            una linea, un discriminante, cero ambiguedad

PENDIENTE   el LEXICO: busca la palabra "discriminante", "falta", "requiere",
            "no medido"... en una ventana de +-500 caracteres alrededor de la
            mencion de la ruta
```

El léxico guarda `VENTANA = 500`. Medido sobre las 22: **0 de 22 tienen un
marcador en su propia línea**. Las 22 entran porque hay un «pendiente» escrito
en la frase de al lado.

El fallo es de clasificación, no de ventana: la herramienta trata
**mencionar una ruta** y **tener un discriminante abierto sobre ella** como la
misma cosa, y son cosas distintas.

## 3 · Y lo grave: la ruta no se podía ni nombrar

El camino estructurado existe y es el bueno, pero no podía nombrar `journalctl`:

```
NEC_A_RUTA   5 claves para 9 rutas medidas
             faltaban journalctl, dmesg, proc_modules, sysfs_pci
```

Es decir: la ruta que la herramienta decía tener 22 discriminantes **no se
podía escribir** en un `PENDIENTE=`. El único camino fiable no la conocía.

Corregido: `NEC_A_RUTA` pasa a 9 de 9.

## 4 · Los tres estados de la verdad, medidos

```
lineas PENDIENTE= estructuradas en el corpus            14
  de las que el regex estricto PEND_RX reconoce         3
  de las que les falta NECESITA=                       11
de las 3 reconocidas, cuántas nombran una ruta realizable   0
    NECESITA=CORPUS x2, INYECCION_PM4_EN_ANILLO x1  ->  las tres a None
```

**El camino estructurado está vacío en la práctica.** No por falta de formato
sino porque lo que las 14 líneas piden no son rutas del host.

## 5 · Lo que la propia herramienta ya decía, y no se leía

El `docstring` de `routeaudit.py` lo tenía escrito desde antes:

> 1. **La deteccion de "pendiente" es LEXICA.** [...] un "N pendientes" sacado
> de una heuristica lexical es un numero con dos cifras

Y `[4] la LIMITAD: la heuristica no distingue 'falta' de 'no falta'` es un
selftest que **demonstra el falso positivo a propósito**.

O sea: la herramienta sabía. Lo que no sabía era que **su línea de salida
contraía esa salvedad**: `22 menciones pendientes` se lee como un recuento, y un
recuento no se lee «aproximadamente». La advertencia estaba en la letra
chica del módulo y el número estaba en la última línea de la pantalla.

Eso es lo que cambió: **la salida ahora dice qué cuenta y con qué precisión**.

```
  /sys/kernel/debug/*   32/32 candidatos sobre una ruta NO alcanzable
      0 PENDIENTE= PROPIAS que la nombran   <- estos si
      32 candidatos LEXICOS de ventana=500  <- estos no; cerca de un
                                                'pendiente' de otra frase
  journalctl -k         la ruta SI es alcanzable
      0 PENDIENTE= PROPIAS que la nombran   <- estos si
      22 candidatos LEXICOS de ventana=500  <- estos no
```

Y los 32 de `debugfs` y los 5 de `dmesg` también salen a **0 propias**: toda la
sección de candidatos descansaba sobre la misma señal falsa.

## 6 · Las cuatro correcciones, y la quinta que salió por el camino

```
  1  propia/ventana   dos campos nuevos en cada fila. `propia` = la línea es
                      una PENDIENTE=. `ventana` = solo hay un marcador cerca.
                      La salida los cuenta por separado y dice que la ventana
                      es de 500.
  2  NEC_A_RUTA       5 -> 9. Ninguna ruta medida queda sin nombrar.
  3  vector 3b        un discriminante nuevo que separa PROPIA de VENTANA
  4  el recuento      "11 vectores" era una CONSTANTE escrita a mano. Con 3b
                      ya no describia lo que hacia. Ahora lo cuenta el codigo,
                      en las DOS ramas: decir 12 comprobaciones y reportar 4
                      seria tan erroneo como escribir 11 a mano.
  5  formato          " · ".join(estado) con una rama string y otra tupla
                      unia los CARACTERES de la string, y la linea salia como
                      "3 · 2 · / · c · a · n · d · i · d · a · t · o · s".
                      No lanza, y parece texto: la forma mas cara de tener un
                      error de formato.
```

## 7 · Dientes

La distinción `propia`/`ventana` se puede invertir, y al hacerlo sale la
afirmación falsa original:

```
invertida    22 PENDIENTE= PROPIAS que la nombran
              0 candidatos LEXICOS

restaurada    0 PENDIENTE= PROPIAS que la nombran
             22 candidatos LEXICOS
```

Es el mismo mecanismo de siempre: **la afirmación sobre lo que hace una
herramienta tiene que poder fallar**, o es una descripción.

## 8 · Lo que este hallazgo NO dice

```
  NO dice que no haya trabajo pendiente en las rutas del host.
  NO dice que las 0 PENDIENTE= propias sean un fallo de quien las escribio:
      NECESITA= de esas tres son CORPUS e INYECCION_PM4, que no son rutas.
  NO cierra ningun discriminante. Solo deja de fingir que hay 22.
  NO arregla las 11 lineas PENDIENTE= sin NECESITA=: son de otros hallazgos y
    corregirlas es cambiar el texto de un hallazgo ya escrito.
```

Lo que sí deja, y es lo accionable: la tabla de rutas tiene **9 entradas
medidas** y ahora se pueden nombrar todas. El siguiente paso del proyecto puede
escribir `PENDIENTE=` con una ruta real, que es justo lo que no se podía.

## 8 bis · COMPLEMENTO, misma sesión: la taxonomía que NO es una partición

Lo anterior dice «las 22 son prosa que ya resolvió algo». Es cierto, pero es
poco: **no son una cosa, son varias**, y el saber cuál importa para lo que sigue.

`routeaudit.py` clasifica ahora cada línea que nombra una ruta por su firma:

```
SUELTA             18   NO CLASIFICADA: hay que leerla
INVENTARIO          6   - `X` -- enumera las rutas que el hallazgo USA
OBSERVACION         3
ALCANCE             1   ALCANCE:/TIPO:/NIVEL:
TRANSCRIPTO         1   $ journalctl -k   FUNCIONA
```

**Y la taxonomía no es una partición.** De 29 candidatas, 6 tienen clase y 23 no.
Las 18 `SUELTA` son al menos seis formas más:

```
  cabeceras RUNTIME=READ_ONLY (journalctl -k -b)   <- clase propia, 6 filas
  transcripciones con su resultado al lado
  filas de tabla de resultados
  prosa sobre lo que la ruta puede o no puede
  Y LA SALIDA DE ESTA MISMA HERRAMIENTA, citada dentro de un hallazgo
```

Esa última es la que cierra el círculo: `250` cita `journalctl -k   22
menciones pendientes`, o sea, la herramienta midiéndose a sí misma a través de
su propio hallazgo. Un clasificador de líneas no puede partitionar eso, y si
devolviera una clase para todo estaría **repartiendo**, no clasificando.

Por eso la salida declara, en la propia línea en que se puede leer:

```
  SUELTA no es una clase: es la ausencia de clase. Las
  firmas cubren 5 formas y el resto son otras seis, entre
  ellas la SALIDA DE ESTA MISMA HERRAMIENTA citada dentro
  de un hallazgo. El unico recuento automatico que se
  publica es el de PROPIAS.
```

### Lo que sí es exacto, y lo único

```
  "esta linea es una PENDIENTE="     respuesta automatica, falsable, exacta
  todo lo demas                      hay que leerlo
```

El recuento que se publica es el de **PROPIAS**, que es 0, y el resto se publica
como lo que es: candidatos que hay que leer. Publicar «0 de 23 tienen clase» es
información; publicar «23» habría sido el error de otra vez, con otro número.

## 9 · Trazabilidad


```
  tools/routeaudit.py:117   PEND_RX, el camino estructurado
  tools/routeaudit.py:105   PENDIENTE, el léxico, y sus 9 marcadores
  tools/routeaudit.py:111   VENTANA = 500
  tools/routeaudit.py:329   las dos ramas FAIL restauradas tras la surgery
  tools/routeaudit.py:196   ok() y fallo(): el recuento ya no es constante
  findings/086:157  findings/163:234  findings/236:155   las tres lineas reales
```