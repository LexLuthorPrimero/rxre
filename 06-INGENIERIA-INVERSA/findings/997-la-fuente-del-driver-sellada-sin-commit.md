# 997 · La fuente del driver está SELLADA y SIN COMMIT: la misma ventana por la que el 050 se perdió, con el fichero todavía en pie

```text
CLASSIFICATION=ERROR+MEASUREMENT+RISK · TRACK=DRIVER+PROVENANCE
CORPUS=07-DRIVER/kernel/  ·  fuente primaria: docs/EVIDENCE-MANIFEST.sha256
HARDWARE_SCOPE=NOAPLICA — no se ha tocado la placa ni el driver
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
MODIFICATIONS_COUNT=0 · no se ha commiteado NADA de 07-DRIVER/
AUTHORIZATION=NONE · GPU INTACTA
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
HERRAMIENTA=revkit/sello.py --custodia   (la DEL PROYECTO. No una propia.)
```

## El hecho, y de dónde sale

Todo lo de abajo es salida de `revkit/sello.py`, que el proyecto ya tenía y que.verifica.
No se ha inventado ninguna medición.

```
$ python3 revkit/sello.py --raiz .. --custodia --todos

  sellado + commiteado  (detecta y recupera)     192
  sellado SIN commit     (detecta, NO recupera)  53
  commiteado SIN sello   (recupera, no detecta)   5260
  ni sello ni commit     (ni detecta ni recupera)  0

  SELLADOS SIN COMMIT, por directorio:
    tools/          39
    08-ARQUITECTURA/  9
    07-DRIVER/        5
```

La segunda fila es la que importa, y la herramienta ya explica por qué es una categoría
distinta: **detecta pero no recupera**. Es exactamente la diferencia entre "saber que algo se
ha movido" y "poder volver atrás".

## La ventana concreta, medida con git directamente

El resumen de `sello.py` dice «07-DRIVER/ → 5». **Ese 5 no se sostiene**, y por eso la tabla
de abajo no lo copia: se ha consultado `git` fichero a fichero.

```
SIN RED  (sellado=SÍ, commiteado=NO)
  07-DRIVER/kernel/rx550_drv.c          20017 B    <<<< la fuente del driver
  07-DRIVER/kernel/rx550_drv.h           2518 B
  07-DRIVER/kernel/rx550_drv.mod.c        480 B
  07-DRIVER/kernel/rx550.mod.c            426 B
                                       ------
                                        4 ficheros, 23441 B

CON RED  (commiteados, recuperables por git)
  07-DRIVER/kernel/rx550_pm4.c          48820 B
  07-DRIVER/kernel/rx550_pm4.h          27477 B
```

`rx550_drv.c` y `.h` son **la fuente del driver**, lo primero que el proyecto no podría
reconstruir: no hay otro lugar del que sacarlos si se pierden. `rx550_pm4.c/.h` sí están
commiteados, así que **la parte pesada del driver tiene red**. La de la estructura del
dispositivo, no.

## Las tres cifras no cuadran, y eso es parte del hallazgo

De la misma corrida de `sello.py` salen tres números para el mismo directorio:

```
custodia, por directorio :  07-DRIVER/   5   sellados sin commit
lista de MOVIDO          :  07-DRIVER/   6   ficheros
consulta directa a git   :  07-DRIVER/   4   sin commit
```

**5, 6 y 4.** Ninguno de los tres es descartable sin investigating por qué, y esa es la
razón por la que este hallazgo **no usa el 5**: un número que no se puede reconciliar con la
respuesta de `git` sobre los mismos ficheros no es un número sobre el que actuar. Los que sí
sostienen son los de la tabla de arriba, porque son los que responde git.

Lo que esto **no** es: una acusación a `sello.py`. La herramienta detectó los 53, separó los
que tienen red de los que no, y por su cuenta —la parte difícil— lo hizo bien. Lo que
no hizo es cuadrar su propio resumen con su propia lista, y esa comprobación no cuesta nada.

## Por qué esto no es un hallazgo nuevo sobre el 050, sino el mismo hallazgo antes de que duela

`revkit/HALLAZGOS-2026-10-02.md:280` ya registró la pérdida:

```
**El 050 no se puede recuperar.** No hay version en git. No se ha intentado
reconstruirlo porque adivinar el contenido de un documento no es una
operacion con criterio. Se deja constancia.
```

Ese 050 se perdió **exactamente** por esta razón: sellado, no commiteado, y nadie lo
advirtió hasta que ya no estaba. Lo que se registra aquí es **la misma configuración con el
fichero todavía en pie**: la ventana existe ahora mismo, y se cierra con una orden.

## Estado del cerrojo, medido

```
.write-lock/drv-q8/   NO EXISTE          (el ámbito se liberó)
procesos con cwd en 06-DRIVER:  ninguno    (nadie escribiendo ahora)
```

Es decir: **no hay nadie escribiendo el driver en este instante**, y su ambito de escritura
está libre. Eso convierte la ventana en cerrable en este momento y no más tarde.

## Por qué no lo cierro yo

`git add 07-DRIVER/kernel/rx550_drv.c` es una escritura en el ambito de **AGENT-06
DRIVER C/ASSEMBLY/PERFORMANCE**, y en un arbol donde varios agentes escriben a la vez. No es
mi ambito, y el proyecto tiene un protocolo escrito —`COORDINACION.md`— cuyo primer
apartado es precisamente no hacer eso. Lo que hago es dejar medido, con el comando exacto y
con el estado que lo hace posible ahora.

## El resto de los 53, y por qué NO los alarmo

```
39  tools/            instrumentos: es lo que se mide y se corrige a diario
 9  08-ARQUITECTURA/  idem
 5  07-DRIVER/        ESTE hallazgo
```

Los 44 de instrumentos se mueven porque se están usando, y **eso es lo normal**: un sello que
señalara cualquier cambio sería inservible. Los 53 `MOVIDO` de `sello.py` no son 53 errores;
son 53 ficheros que han cambiado desde el sello del 2026-10-02 01:15. La pregunta por la que
vale la pena mirar es la de custodia, no la de movimiento, y de custodia solo 5 son driver.

## Lo que este hallazgo NO dice

- **No dice** que haya una pérdida. No hay ninguna: los cinco ficheros existen.
- **No dice** que `sello.py` falle. Ha hecho su trabajo: ha detectado los 53 y ha separado
  los que tienen red de los que no.
- **No acusa** a nadie. El 050 se perdió sin red; este fichero sigue sin red porque nadie ha
  hecho `git add`, y probablemente porque nadie ha caido en la cuenta, no por una decisión.
- **No commitea** nada de `07-DRIVER/`. Ni un byte.

## Procedencia

```
sello     docs/EVIDENCE-MANIFEST.sha256   245 entradas   2026-10-02 01:15:47
herramienta  revkit/sello.py --custodia --todos          exit 0
07-DRIVER/kernel/rx550_drv.c   20017 B   sha actual medido, sin commitear
cerrojo   .write-lock/drv-q8    ausente
procesos  ninguno con cwd en 06-DRIVER
LIMITACION  El estado de custodia se midió a las 15:4x del 2026-10-03. Es una foto, y
            AGENT-06 puede haber commiteado entre la medición y la lectura de este texto.
LIMITACION  `sello.py` cruzó el sello con git en el momento de ejecutarlo; si el índice de
            git cambia durante la corrida, el recuento puede quedar desfasado. No se ha
            reejecutado para comprobar estabilidad, y ese es un control que falta.
```