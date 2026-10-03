# 287 · La lectura sí costaba su latencia: 443 ciclos. El error era mío — llevaba cuatro notas reportando el ritmo agregado como si fuera latencia

```text
CLASSIFICATION=MEASUREMENT+ERROR_CORRECTION+REFUTED · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con cuarta constant (MODE) y modelo 3 | ESTADO=VALIDATED (regresion 4/4)
```

> **`RESUELTA` por `602`. La `CONTRADICTION` de §4 no era una discrepancia entre `hwmon` y la
> memoria: era que el kernel que produjo los 17,829 GB/s tiene una cadena de direcciones que
> **colapsa**, y que el techo contra el que los comparé estaba calculado con la mitad del
> ancho de bus.**
>
> ```text
> CAUSA_1  la cadena de div.comp colapsa. El estado del sistema es idx = acc mod WSIZE, luego
>         la recurrencia es lineal y su imagen se reduce cada vuelta: con 4096 hilos de
>         partida, 186 direcciones distintas con 4 iteraciones y **UNA sola con 16**. Un
>         ITERS = 1024 entero mide un acceso a una direccion, leido por 65536 hilos.
> CAUSA_2  el techo de 24,0 GB/s de 258 usa un bus de 64 bits sin fuente. 602 mide 43,2 GB/s
>         utiles con reparto contiguo y entropia verificada: 64 bits son imposibles.
> ```
>
> **Ninguna de las dos hipótesis de §4 sobrevive.** No era que `hwmon1/freq2_input` no
> reflejara el reloj con el que la memoria atiende —se comprobó que sí, y que sube a 1500 MHz
> bajo demanda— ni que una caché explicara el exceso: no había DRAM de la que hablar.
>
> **Y el error de encuadre se repitió dos veces.** §4 de esta nota leyó `mclk` antes y después
> de la corrida, que es en reposo. La medición de `602` por modo tuvo el mismo fallo: el
> despacho contiguo dura 31 ms y el proceso vive 400 ms, así que el 90% de las muestras era
> la fase de inicialización en reposo. Rehecha con despachos largos en los dos modos.
>
> **Lo que sí sobrevive de esta nota:** la forma de la curva de la §3 —ancho de banda que sube
> con la latencia constante, y luego ancho saturado con latencia explotando— y la latencia de
> 443 ciclos a 1.024 hilos. Los **números** no son utilizables.
>
> **El defecto de instrumento que lo Enableó todo:** un control de contenido no puede detectar
> que el kernel hace el trabajo equivocado, porque el modelo del host hace la misma cuenta
> equivocada y los dos coinciden. Hace falta un control **sobre el trabajo**. `602` lo añade.

## Qué resuelve

**⇒ Ejecuta el discriminante que `282-1` y `286` dejaron abiertos, y el resultado invalida la
interpretación de cuatro notas. La lectura de memoria **sí** costaba su latencia: **443 ciclos
de reloj**, constante con 64, 256 y 1024 hilos.** `PROVEN`.

**⇒ `REFUTED`. El módulo entero —hipótesis H2, `idx = acc % WSIZE`, que en GFX8 se emula—
cuesta 0,03 ciclos, el 3,6% del total. No es el coste.** `REFUTED`.

**⇒ `PROVEN_DERIVED`. El error era aritmético y mío, y llevaba desde `277`: he estado
reportando `t / (items × iters)` como «ns por acceso». Eso es el **ritmo agregado** con todos
los hilos en paralelo. La latencia que sufre un hilo es `t / iters`, que es **219 veces mayor**
que el número que he estado publicando.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Consecuencia en cadena: el «1,49× el techo del enlace» de `282` era una
coincidencia aritmética entre un número mal formado y un techo que no era el recurso implicado.
El buffer del kernel es `DEVICE_LOCAL` —VRAM— y su techo es 24,0 GB/s, contra el cual 2,970 GB/s
son un 12,4% perfectamente plausible. El argumento estaba mal encuadrado.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y la curva tiene dos regímenes separados, que son dos magnitudes distintas: hasta
1024 hilos el límite es de **latencia** (443 ciclos, el ancho de banda sube linealmente); desde
4096 el límite es de **ancho de banda** (se satura en 17,83 GB/s y la latencia explota).** `PROVEN`.

**⇒ `CONTRADICTION`, y es la que queda viva: los 17,83 GB/s medidos son el 371% del techo que
permite `mclk` = 300 MHz, el valor que `hwmon` reporta antes y después. Algo de esos dos números
no es correcto.** `CONTRADICTION`.

## 1 · El discriminante, y lo que descartó

**⇒ `PROVEN. `div.comp` es `occ.comp` con una sola diferencia: el índice siguiente se calcula
con `% WSIZE` o con `& (WSIZE − 1)`. La cadena sigue siendo dependiente en los dos modos —
`idx` depende de `acc`, `acc` depende de la lectura— así que lo único que cambia es la
operación.** `PROVEN`.

| modo | t (s) | ns por acceso | ciclos | control |
|---|---|---|---|---|
| `acc % WSIZE` | 0,000878 | 0,8373 | 0,89 | 11/11 |
| `acc & (WSIZE−1)` | 0,000846 | 0,8068 | 0,86 | 11/11 |

**⇒ `REFUTED`. La diferencia es 0,0305 ns por iteración, 0,03 ciclos, el 3,6% del total. Una
división emulada de GFX8 cuesta decenas de ciclos, no 0,03. O el compilador la ha sustituido
porque `WSIZE` es una specialization constant conocida en compilacion, o el coste estaba en otro sitio
y este no lo es.** `REFUTED`.

**⇒ `PROVEN. El control discrimina en los cuatro casos: `div.comp` valida 256 de 256 en los dos
modos, y falla 0 de 256 en modo máscara con `WSIZE` = 1000, que no es potencia de dos. Y la
regresión de los tres kernels anteriores sigue dando 0 `NO`.** `PROVEN`.

## 2 · El error aritmético, y por qué nadie lo vio

**⇒ `PROVEN_DERIVED. El número que he publicado desde `277` como «ns por acceso» es
`t / (items × iters)`.** `PROVEN_DERIVED`.

```text
con items = 256, iters = 4096, t = 0,001412 s:

  lo que publicaba     t / (items x iters) = 1,3466 ns   <- ritmo AGREGADO
  lo que sufre un hilo      t / iters      = 344,7 ns    <- LATENCIA
  a sclk 1063,02 MHz                           = 366 ciclos
```

**⇒ `PROVEN_DERIVED. La diferencia es un factor `items` = 256. Con 256 cadenas en paralelo, el
tiempo total se reparte entre ellas, y al dividir por el número de cadenas se obtiene el ritmo
conjunto, que no es lo que sufre ninguna de ellas.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y por eso la comprobación que hice en `277` no podía detectarlo. En `277`
medí cómo bajaba el «ns por acceso» al subir los hilos, y leí esa bajada como paralelismo
correcto. Era correcto y era la prueba del error: **el número bajaba porque lo dividía por más
hilos, no porque la memoria fuese más rápida.** Con la latencia correcta el efecto es el
contrario y es el que hace falta.** `PROVEN_DERIVED`.

## 3 · La curva correcta, que separa las dos magnitudes

**⇒ `MEASUREMENT. `div.comp`, modo división, `ITERS` = 1024, `WSIZE` = 65536, 9 muestras con
calentamiento, control 9 de 9 en los seis puntos.** `MEASUREMENT`.

| hilos | ns por vuelta | ciclos | GB/s | % de 24,0 |
|---|---|---|---|---|
| 64 | 515,6 | 548 | 0,496 | 2,1% |
| 256 | 413,1 | 439 | 2,479 | 10,3% |
| 1.024 | **417,0** | **443** | 9,823 | 40,9% |
| 4.096 | 1.003,9 | 1.067 | 16,320 | 68,0% |
| 16.384 | 3.772,5 | 4.010 | 17,372 | 72,4% |
| 65.536 | 14.703,1 | 15.630 | **17,829** | 74,3% |

**⇒ `PROVEN`. Los dos regímenes son distinguibles y tienen la firma que les corresponde.** `PROVEN`.

```text
64 -> 256 -> 1024 hilos : ancho de banda x5,00 y x3,96   latencia x0,80 y x1,01
                           el ancho crece con los hilos, la latencia NO cambia
                           => limite de LATENCIA, 443 ciclos

4096 -> 16384 -> 65536   : ancho de banda x1,06 y x1,03   latencia x3,76 y x3,90
                           el ancho se SATURA, la latencia EXPLOTA
                           => limite de ANCHO DE BANDA, las peticiones se encolan
```

**⇒ `PROVEN_DERIVED. Que la latencia se mantenga constante mientras el ancho de banda sube
linealmente es la firma de un límite de latencia. Que el ancho se aplane mientras la latencia se
multiplique por cuatro es la firma de un límite de ancho de banda. Ninguna de las dos firmas
admite la lectura que hice en `277` y `282`.** `PROVEN_DERIVED`.

## 4 · La contradicción que queda abierta, y es la buena

**⇒ `PROVEN_DERIVED. Los 17,829 GB/s medidos son el 74,3% del techo de VRAM derivado en `258`,
pero ese techo asume `mclk` = 1500 MHz, y `hwmon` dice 300 MHz antes y después.** `PROVEN_DERIVED`.

```text
con mclk 1500 MHz : techo = 1500e6 x 2 x 8 = 24,0 GB/s  ->  17,829 es el 74,3%   coherente
con mclk  300 MHz : techo =  300e6 x 2 x 8 =  4,8 GB/s  ->  17,829 es el  371%   IMPOSIBLE
```

**⇒ `CONTRADICTION`. O `hwmon1/freq2_input` no refleja el reloj con el que la memoria está
atendiendo las peticiones, o la lectura no pasa por el controlador de memoria que ese reloj
gobierna. Las dos son verificables y las dos tienen consecuencias distintas.** `CONTRADICTION`.

**⇒ `PROVEN_DERIVED. Y la segunda tiene un nombre en el proyecto: la caché. Si una fracción
sustancial de los 17,829 GB/s la sirve una caché en el camino, el reloj de la DRAM no limita y
`mclk` puede quedarse en 300 MHz sin contradicción. `265` establecía que el tamaño de esa caché no
está en ninguna fuente, y `277` / `281` / `282` / `283` dejaron la medición en un punto donde
el instrumento no distinguía caché de memoria. Esta nota llega a un punto donde sí puede: el
ancho de banda agregado, con su latencia y su saturación.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: cuál de las dos salidas de la contradicción es la buena. Requiere
saber qué reloj gobierna realmente las peticiones de este ASIC, que es la pregunta que `253`
dejó abierta sobre el control térmico y que `247`/`253` apuntan al firmware.** `NOT_DETERMINED`.

## 5 · Estado de las notas que esta corrección afecta

**⇒ `CORROBORATED`. La linealidad del bucle que midió `281` no cambia: el bucle se ejecuta, eso
sigue siendo cierto, y el discriminante de `STEPS` sigue siendo válido.** `CORROBORATED`.

**⇒ `REFUTED`. La conclusión de `277` —«el kernel es issue-bound y no memory-bound»— es falsa.
Es memory-bound: 443 ciclos de latencia por acceso dependiente es exactamente eso.** `REFUTED`.

**⇒ `REFUTED`. El argumento de imposibilidad de `282` §3 es inválido por encuadre: comparó un
número de bytes por segundo con el techo del enlace cuando el recurso implicado es la VRAM, y
además el número estaba mal formado por el error de división.** `REFUTED`.

**⇒ `CORROBORATED`. La conclusión de `283` —que la lectura y la aritmética no cuestan lo mismo—
se sostiene y se precisa: la aritmética cuesta 0,89 ciclos y la lectura 443.** `CORROBORATED`.

**⇒ `CORROBORATED`. `286` no se ve afectado: su medición es de copias completas, no de cadenas
dependientes, y un acceso por copia no se solapa con otros.** `CORROBORATED`.

## 6 · Mis errores, y el patrón que completa la serie

**⇒ `ERROR`: reporté `t / (items × iters)` como «ns por acceso» desde `277`. La latencia de un
acceso dependiente es `t / iters`. El factor `items` estaba escondido en el denominador durante
cinco notas.** `ERROR`.

**⇒ `ERROR`: el argumento de `282` comparó contra el techo del enlace un buffer que es
`DEVICE_LOCAL`. El recurso implicado es la VRAM. Cuando dos números se parecen y uno de ellos es
erróneo por construcción, la semejanza es casualidad, no evidencia.** `ERROR`.

**⇒ `ERROR`: la comprobación que hice en `277` no podía detectar el error porque medí la
magnitud equivocada. La comprobación correcta —variar los hilos y ver si la latencia por vuelta
se mantiene constante— la tenía escrita en la misma nota y la interpreté al revés.** `ERROR`.

**⇒ `PROVEN_DERIVED. Y el patrón de toda la serie es el mismo en los tres casos: medí bien,
reporté mal. El instrumento llevaba un mes pasando sus controles y tres revisiones, y el fallo
era de la unidad con la que yo traducía el resultado a un número que significa algo. Ningún
control de readback detecta eso, porque el readback valida el contenido y no la unidad.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La regla que este caso añade, y que es la última que me faltaba sobre
medición: **una magnitud medida necesita una unidad cuyo significado esté justificado, no solo
una fórmula que la produzca.** `ns por acceso` sonaba a latencia y no lo era. Lo que la habría
detectado es una sola pregunta antes de escribir: ¿esto es el tiempo que sufre una unidad de
trabajo, o el tiempo repartido entre todas?** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
262-1 | ESTADO=REOPENED con instrumento apto
           | PREGUNTA=¿cual es el tamaño de la cache de GFX8?
           | POR_QUE_CAMBIA=el instrumento por fin separa las dos magnitudes: la latencia
           |   de 443 ciclos con conjunto pequeno, y el ancho de banda saturado con
           |   conjunto grande. El punto donde la latencia deja de crecer al aumentar el
           |   conjunto es el punto donde deja de caber en la cache.
           | ALCANZABLE_SIN_ROOT=si

287-1 | ESTADO=OPEN · CONTRADICTION
           | PREGUNTA=17,829 GB/s son el 74% del techo con mclk 1500 y el 371% del techo
           |          con mclk 300. ¿Cual reloj gobierna las peticiones de este ASIC?
           | CONSECUENCIA_SI_ES_LA_CACHE=los 17,829 no son DRAM, y el ancho de banda de
           |          la DRAM sigue sin medir
           | DISCAMINANTE=barrer el conjunto de trabajo con la MAGNITUDE CORRECTA, que es
           |          latencia por vuelta y ancho de banda por hilo, no ns por acceso
           | ALCANZABLE_SIN_ROOT=si

INSTRUMENT=vcp | ESTADO=VALIDATED
           | CONSTANTS=4 (ITERS, WSIZE, STEPS, MODE) — offsets 0, 4, 8, 12 en pData
           | MODELOS=4 (0=probe, 1=occ, 2=chain, 3=div)
           | REGRESION=probe, occ, chain, div — los cuatro validan con 0 NO
           | INVARIANTES_2=wsize >= items, WSIZE >= items (ambos exit 2)
```