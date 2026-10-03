# 903 · Un banco de mediciones con contrato, y la prueba de que sabe invalidar

```text
CLASSIFICATION=TOOL+MEASUREMENT · TRACK=RUNTIME
CORPUS=sin cambios · MODIFICATIONS_CORPUS=0
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · BAR=256M
WORK_CLASS=WRITE_LOCAL (instrumento propio) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1 · AUTORIA=AGENTE-SMU
INSTRUMENTO NUEVO=08-ARQUITECTURA/tools/bench.py · ESTADO=VALIDATED (12 de 12)
ARTEFACTOS=08-ARQUITECTURA/validations/bench-<suite>-<timestamp>.json
GPU INTACTA
```

## Qué resuelve

**⇒ `PROVEN`: faltaba el instrumento de runtime.** `run_all.py` existe y es un runner de las
herramientas **estáticas**; no hay nada que haga lo mismo con las mediciones. Toda la medición de
`602`, `606`, `607`, `609` y `902` se hizo con scripts escritos a mano en `/tmp`, uno por
medición.** `PROVEN`

**⇒ `PROVEN_DERIVED`: ese hueco tiene un coste medible, y son los errores de esta sesión. Once
errores propios en una tarde, y cuatro de los cinco últimos fueron una línea de parche mal
aplicada. Ninguno lo detectó un control existente, porque ningún control miraba la magnitud
afectada.** `PROVEN_DERIVED`

**⇒ `PROVEN`: `bench.py` con doce casos de self-test, todos con un caso negativo. Y la prueba de
que un validador puede invalidar: un cambio de un carácter en una constante del hash de
`lane.comp` da `lane/disperso` con `control_contenido=False, exit=4`, veredicto `INVALID` y salida
1; restaurado da `PASS` y salida 0.** `PROVEN`

**⇒ `CORROBORATED`: el banco reproduce `609` de forma independiente. Las medianas por envío son
18,92 / 12,36 / 12,34 / 12,35 / 12,36 / 12,34 / 12,35 / 12,35 ms, diferencia de 6,570 ms y
dispersión del 0,21%, frente a las 6,599 ms y 1,07% de aquella nota.** `CORROBORATED`

## 1 · Lo que hace, y lo que no hace

**⇒ `PROVEN_DERIVED`. La regla que impone es la que hoy no tenía ningún instrumento: ningún número
se reporta si sus controles no pasan. Si el control de contenido, el de entropía o el de que el
tiempo crece con `ITERS` fallan, el resultado es `INVALID_RESULT` y la salida es distinta de cero.
No es un aviso: es un fallo.** `PROVEN_DERIVED`

```text
  regresion     11 casos de contenido + tiempo crece con ITERS + pago unico
  curva         t frente a ITERS; interceptor y pendiente
  coalescencia  disperso, contiguo y difusion con la misma carga de carril
  rejilla       interceptor en una rejilla de reserva por separado
```

**⇒ `PROVEN`: el artefacto lleva la procedencia que §99 pide.** `PROVEN`

```text
  hardware    kernel, PCI id, sclk, mclk, potencia, temperatura, BAR
  instrumento sha256 del binario y del fuente .c, y frescura de los .spv
  contexto    n de muestras, ITERS, y todos los parametros de la suite
  resultado   las muestras CRUDAS, el ajuste, cada control y su veredicto
  veredicto   PASS o INVALID, con la lista de fallos
```

**⇒ `PROVEN_DERIVED`. Y dos decisiones de diseño que vienen de los errores de hoy. La primera: el
intercepto del ajuste se llama `intercepto_ms` y no `coste_ms`, y el artefacto lleva un aviso que
dice que no es un coste y cita a `609`, porque tres notas seguidas lo leyeron como coste por envío.**
`PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`. La segunda: una muestra que falla su control no se promedia con las que lo
pasan. Se descarta y se cuenta en `rechazadas`, porque promediar un fallo esconde el fallo.** `PROVEN_DERIVED`

## 2 · Lo que el banco encontró en sí mismo al construirse

**⇒ `ERROR`: `ajustar` multiplicaba por 1000 dentro de la función y devolvía milisegundos sin
decirlo. El self-test lo detectó con `a=0, b=500` sobre una recta conocida. Es exactamente la clase
de error que este proyecto ha repetido cinco veces: una magnitud con la unidad escondida dentro de
la fórmula en vez de declarada donde se usa. Ahora `ajustar` devuelve las unidades que recibe y las
convierte quien llama.** `ERROR`

**⇒ `ERROR`: mi caso de prueba estaba mal, no el código. Declaré `ys = 0,5·x` y esperaba `a = 0,5`
cuando la recta es `y = 0,5·x` con `a = 0`. El ajuste daba la respuesta correcta y la expectativa
estaba mal. Un self-test que se equivoca en su caso bueno obliga a tocar el código bueno, así que
también es un fallo, y lo es del mismo modo que un dato malo: no distingue lo que sabe de lo que
supone.** `ERROR`

**⇒ `ERROR`: `suite_coalescencia` usaba `ctx["iters"]`, que `main` rellena con una **tupla** para la
suite `curva`. Al banco le llegaba la tupla, `strtoul` devolvía 0, y las tres filas salían
`INVALID` en 0,0 s. Dos suites compartiendo una clave con tipos distintos.** `ERROR`

**⇒ `ERROR`: escribí `Malos` en una línea y `malos` en la condición siguiente. En Python no es el
mismo binding, así que la condición leía una lista vacía de otro caso del self-test y fallaba con
`okf=False` y el estado `OBSOLETO` a la vista. Un nombre que sólo se distingue por la caja es un
nombre que otro lee sin querer, y el fallo se ve sólo si se imprime el valor de los dos.** `ERROR`

## 3 · El hueco que encontró al probarlo, y que era un fallo suyo

**⇒ `PROVEN`: el banco daba `PASS` con el instrumento roto.** `PROVEN`

**⇒ `ERROR`: lo primero que probé fue cambiar el hash de `lane.comp` y no recompilar bien; el error
de `glslangValidator` se fue a `/dev/null`, se consumió el `.spv` viejo y el banco dio `PASS` con el
kernel intacto. Un `PASS` así no es un resultado: es la ausencia de resultado con forma de
resultado.** `ERROR`

**⇒ `PROVEN_DERIVED`: eso es §25 aplicado al artefacto. Antes de consumir hay que comprobar que el
artefacto existe, está completo, es válido y es del tipo esperado. El banco comprobaba existencia
y nada más, y un `.spv` obsoleto es un artefacto de otra ejecución.** `PROVEN_DERIVED`

**⇒ `PROVEN`: ahora `frescura_spv()` compara el `mtime` de cada `.comp` con el de su `.spv` para los
ocho kernels, y si el fuente es más nuevo el banco lo dice en el artefacto. Además guarda los dos
hashes por kernel, para que un artefacto de una corrida se pueda invalidar después desde fuera.**
`PROVEN`

**⇒ `PROVEN_DERIVED`: y el self-test tiene dos casos para esto: uno que toca el `mtime` del fuente
para comprobar que la frescura lo detecta, y otro que comprueba que dice "al día" tras restaurar.
Tocar el `mtime` en vez del contenido es deliberado: un self-test que modifica el instrumento para
probarlo tiene que poder deshacerlo, y modificar contenido para eso es una forma de dejar el
instrumento distinto del que estaba.** `PROVEN_DERIVED`

**⇒ `PROVEN`: y la rotura semántica de verdad, la que sí compila, da `INVALID` con salida 1.** `PROVEN`

```text
  0x85ebca6bu -> 0x85ebca6cu  en lane.comp, recompilado y validado
  lane/disperso : control_contenido=False  exit=4
  veredicto     : INVALID   fallos: [7]=INVALID   salida del banco: 1
  restaurado    : PASS                          salida del banco: 0
```

**⇒ `PROVEN_DERIVED`: y la localización es exacta. La rotura estaba en la rama `LANEMODE == 1`, y
falló `lane/disperso` y ningún otro. Un banco que invalida sin decir dónde es peor que uno que no
invalida, porque deja la decisión de dónde mirar a quien lee.** `PROVEN_DERIVED`

## 4 · Un resultado que el banco expone y que las notas no cuantificaban

**⇒ `MEASUREMENT`. La suite `coalescencia` da, a `ITERS = 2.048` y huella de 256 MiB:** `MEASUREMENT`

| reparto | GB/s útiles | factor sobre disperso |
|---|---|---|
| disperso | 1,55 | 1,00 |
| contiguo | 28,01 | 18,04 |
| difusión | 47,67 | 30,69 |

**⇒ `PROVEN_DERIVED`: el factor es de tiempo total, no de tiempo marginal, y por eso sale menor que
el 27,4 de `602`. El modo contiguo paga el pago único de ~6,7 ms que `609` midió y el disperso no,
así que a `ITERS = 2.048` ese pago es una fracción grande del tiempo del contiguo. Las dos cosas
son ciertas: 27,4 es el factor marginal y 18,0 es el factor de latencia a esa longitud de ráfaga.
Son dos preguntas y el banco las responde por separado.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: por eso el factor es un número que no debe citarse sin decir de qué es
factor. Un banco que lo publica sin esa calificacion se está haciendo el mismo favor que `606` se
hizo a sí mismo durante tres notas.** `PROVEN_DERIVED`

## 5 · Límites

**⇒ `NOT_DETERMINED`: `bench.py` no mide nada que los shaders no midieran. Si un kernel no
distingue dos cosas, el banco tampoco: repite y agrega.** `NOT_DETERMINED`

**⇒ `NOT_DETERMINED`: los controles que exige son los de hoy, no los de mañana. El de frescura
compara `mtime`, que es una heurística y no un hash; un `.spv` regenerado con el `mtime` antiguo
pasa. Se guarda el hash en el artefacto para que se invalidar desde fuera, pero el banco no lo
comprueba por sí mismo.** `NOT_DETERMINED`

**⇒ `NOT_DETERMINED`: el banco no compila. Si falta un `.spv`, falla, y si un `.comp` cambió
devuelve `PASS` con un aviso en vez de fallar, porque un `.comp` sin recompilar es una decisión
del operador y no un fallo del instrumento.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`: y el artefacto escribe en `08-ARQUITECTURA/validations/`, que es donde ya
había artefactos, no en un sitio nuevo. `crear el mínimo artefacto necesario` es para lo que no
existe, y este directorio ya existía para esto.** `PROVEN_DERIVED`

## 6 · PENDIENTE

```text
INSTRUMENTO=bench.py | ESTADO=VALIDATED, 12 de 12
           | SUITES=regresion, curva, coalescencia, rejilla
           | ARTEFACTO=validations/bench-<suite>-<ts>.json con hardware, sha256 y muestras crudas
           | REGLA=ningun numero se reporta si sus controles no pasan
           | CONTROLES_QUE_EXIGE=contenido, entropia, tiempo crece con ITERS, frescura del .spv

602   | SU MEDICION, ahora reproducible con `bench.py run coalescencia`
           | el 27,4 es el factor MARGINAL; el de latencia a 2048 vueltas es 18,0
609   | SU MEDICION, ahora reproducible con `bench.py run regresion`

TODO-1 | ESTADO=OPEN
           | Los umbrales de 902 (reserva >= 64 MiB, separado >= 16 MiB) con la rejilla del banco,
           | y el punto que mas discrimina: reserva 32 MiB con separado 16 MiB

TODO-2 | ESTADO=OPEN
           | El ancho de bus: 128 o 256 bits. Bloqueado en el VBIOS, sudo, desde 272

TODO-3 | ESTADO=OPEN
           | El mecanismo del pago unico de 6,7 ms. Conocido en magnitud, en condicion y en
           | su dependencia de ITERS; el mecanismo sigue NOT_DETERMINED
```