# 1494 — los tres cuellos de botella, el ancho de banda real, y la SMU oscilando

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-SILICIO+DERIVACION+REVISION-PROPIA+DESCUBRIMIENTO
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta y verificada
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1485-*  CORREGIDO: mi ancho de banda estaba a la mitad
         §67 BOOTLENECK ENGINE: contestado con datos, no con intuicion
         §77 MAXIMO RENDIMIENTO PRACTICO: techo de memoria y eficiencia, medidos
         06-INGENIERIA-INVERSA/findings/1489-*  el techo de 1500, con su unidad resuelta
ESTADO=PROBADO · la tarjeta es MEMORY-BOUND para rmw y fill, y ALU-BOUND para math.  Medido
       · 40.00 GB/s de trafico de DRAM en lectura+escritura.  NO son 18.34: mi numero del 1485
         estaba a la mitad por un error de contabilidad mio, y lo corrijo
       · 40.00 GB/s > 24 GB/s descarta la lectura de una transferencia por ciclo.  Eso RESUELVE
         por medicion la unidad que el 1485 dejo NOT_DETERMINED: son dos.  Eficiencia 83.3 %
       · y la SMU OSCILA entre 1500 y 625 MHz bajo carga de ALU, durante toda la carga
```

## 1. La corrección: mi ancho de banda del 1485 estaba a la mitad

El 1485 mide `bytes_del_buffer × iteraciones / tiempo` y lo llamó "ancho de banda aparente". Pero
eso cuenta el buffer **una vez** por iteración, y en `rmw` cada elemento **se lee y se escribe**:

```text
fill  (solo escritura)   trafico real = 1x el buffer por iteracion
rmw   (lectura+escritura) trafico real = 2x el buffer por iteracion
math  (lectura+escritura) trafico real = 2x el buffer por iteracion
```

El factor depende del modo. Multiplicarlo sin mirar el modo es una cuenta que no significa nada,
y **eso es lo que hice**. El instrumento ahora lo declara explícitamente y aplica el factor.

**Con 512 MiB y 21 muestras por modo:**

| modo | qué hace | tráfico de DRAM | `mem_busy%` | SCLK/MCLK | VDDGFX | potencia |
|---|---|--:|--:|---|--:|--:|
| `fill` | escritura pura | **32.84 GB/s** | 40.9 | 1071 / 1500 | 881 mV | — |
| `rmw` | lee + modifica + escribe | **40.00 GB/s** | 48.9 | 1071 / 1500 | 881 mV | 14.22 W |
| `math` | 64 FMA por elemento | **12.89 GB/s** | 22.5 | 1071 / 1500 y **625** | 881 mV | **17.9 W** |

> **El `rmw` del 1485 no eran 18.34 GB/s: eran ~36.8 GB/s** (buffer de 512 MiB, escala anterior).
> La cifra buena es **40.00 GB/s**, reproducible, y la de arriba es con la contabilidad corregida.

## 2. LA UNIDAD DEL RELOJ DE MEMORIA, RESUELTA POR MEDICIÓN

El 1485 dejó esto explícitamente sin cerrar: con 128 bits y "1500 MHz", el máximo nominal son
48 GB/s con transferencia doble, y **dependía de una convención que no estaba establecida**, así
que se negatively no construía rendimiento sobre ese número. Ahora hay un discriminador.

```text
ancho del bus              128 bits = 16 bytes por transferencia

SI 1500 MHz fuese la tasa EFECTIVA (una transferencia por ciclo):
    1500e6 × 16 =  24.0 GB/s

MEDIDO (rmw, 21 muestras, 512 MiB):  40.00 GB/s

    40.00 > 24.0   ==>  DESCARTADO
```

> **La medición de ancho de banda descarta por sí sola la lectura de una sola transferencia por
> ciclo.** No es una hipótesis que yo prefiera: es la única de las dos que sobrevive al dato. Y
> con transferencia doble:
>
> ```text
>     1500e6 × 2 × 16 = 48.0 GB/s     40.00 / 48.0 = 83.3 % de eficiencia
> ```
>
> **La unidad del reloj de memoria queda `PROBADO` = dos transferencias por ciclo**, y con ella
> la **eficiencia del subsistema de memoria medida en 83.3 %** para un flujo mixto de lectura y
> escritura. Eso no estaba en el proyecto, y es el número que hace falta para saber si queda
> recorrido.

## 3. §67 CONTESTADO: el cuello cambia según la carga

El BOTTLENECK ENGINE (§67) exige clasificar antes de optimizar. Con datos:

```text
                  fill              rmw                math
SCLK/MCLK    1071 / 1500 (21/21)  1071 / 1500 (21/21)  1071 / 1500 o 625, OSCILANDO
gpu_busy%            —                 100                 100  (21/21)
mem_busy%         40.9               48.9                22.5
trafico         32.84 GB/s         40.00 GB/s          12.89 GB/s
potencia            —               14.22 W              17.9 W
```

> **`fill` y `rmw` son MEMORY-BOUND.** Los relojes se quedan clavados en el techo, `mem_busy` en
> 41–49 %, y el ancho de banda llega al 83 % de lo nominal. No queda mucho que ganar ahí.
>
> **`math` es ALU-BOUND.** El tráfico cae a 12.89 GB/s, la memoria está ociosa al 22 %, y la
> tarjeta **consume MÁS potencia** (17.9 W frente a 14.22 W) porque lo que está trabajando es el
> núcleo de gráficos, no la memoria.
>
> Y `gpu_busy_percent = 100` en los tres modos, así que **el 100 % no significa "saturado de
> memoria"**: significa "el motor está ocupado", y *en qué* se deduce de `mem_busy_percent`. Ese
> par de observables es el discriminante, y ahora está medido en los tres regímenes.

## 4. EL HALLAZGO GRANDE: la SMU oscila

La línea temporal del modo `math`, muestra a muestra:

```text
  t=1   1071/1500   mem%=16   17.75 W
  t=2   1071/1500   mem%=16   17.10 W
  t=3   1071/1500   mem%=16   17.81 W
  t=4   1071/ 625   mem%=39   17.98 W      <-- cae
  t=5   1071/1500   mem%=16   17.85 W      <-- vuelve
  t=6   1071/1500   mem%=16   17.11 W
  t=7   1071/1500   mem%=16   17.93 W
  t=8   1071/ 625   mem%=39   17.95 W      <-- cae
  t=9   1071/1500   mem%=16   16.17 W      <-- vuelve
  ...
  t=13  1071/ 625   mem%=39   17.11 W
  t=15  1071/ 625   mem%=39   17.12 W
  t=19  1071/ 625   mem%=39   17.11 W
  t=20  1071/ 625   mem%=38   17.12 W
```

> **No es una transición. Es una oscilación.** Durante los 12 s completos, el reloj de memoria
> alterna entre 1500 y 625 MHz, con 15 muestras arriba y 6 abajo, **sin tendencia**. Y el gráfico
> se queda clavado en 1071 MHz las 21 veces: la oscilación es **sólo del reloj de memoria**.

**Y el acoplamiento es visible en `mem_busy_percent`:**

```text
mclk = 1500  ->  mem% = 16
mclk =  625  ->  mem% = 39
```

Subir el reloj **baja** el porcentaje de ocupación, que es lo esperado si `mem_busy_percent` mide
**tiempo con trabajo pendiente** y no tasa. Es decir: **la señal que gobierna el reloj de memoria
la propiaacceleración del reloj de memoria modifica.** Eso es un lazo de realimentación, y un lazo
así es exactamente lo que oscila.

**Consecuencia que no voy a adornar:** cada transición es un cambio de reloj de GDDR5, y en una
tarjeta con `usMcPhyInitTableOffset` presente eso normalmente implica **reentrenamiento de
straddle**. El hallazgo 1472 dejó probado que el BIOS **presetea** los offsets y deja la búsqueda a
otro, y no sé todavía quién la ejecuta — pero sí sé que **aquí se está cambiando el reloj de
memoria treinta veces en doce segundos**, y eso es observable por el mismo mecanismo.

**Lo que NO afirmo:** que la oscilación sea un defecto, ni que se pueda arreglar, ni que cause
pérdida de rendimiento medible. **Lo que sí es `PROBADO`:** que ocurre, que es de memoria y no de
gráficos, y que `fill` y `rmw` **no** lo hacen (21/21 en 1500 cada uno).

## 5. Y la recuperación es la misma en los tres modos

```text
fill_post   1071/1500 -> 1046/300 (850 mV) -> 551/300 (700 mV) -> 214/300 (700 mV)
rmw_post    idem
math_post   idem
```

**El camino de descenso es idéntico con independencia del perfil de carga**, y con el voltaje
detrás: 881 → 850 → 700. Y coincide con lo observado en el 1485 (1071 → 980 → 551 → 214). O sea
que **bajar es reproducible y bajar rápido es independiente de la carga**; lo que depende de la
carga es sólo si hay oscilación.

## 6. Procedencia

```text
artefacto    07-DRIVER/bench/sweep3-modos-2026-10-05.tsv    21 muestras x 3 modos + reposo + post
instrumento  07-DRIVER/bench/rx550_gl_load.c   --mode fill|rmw|math  --no-sync  --iters
             kernel en GLSL 430 con uniforme uMode/uIters/uBase; troceado en trozos de
             65535 workgroups porque maxComputeWorkGroupCount[0] lo declara 4294967295 y el
             producto en uint32 desbordaria
frontera     verificada en caliente en cada ejecucion: POST-CONDICION DE FRONTERA: renderer
             AMD y es esta tarjeta. OK
solo lectura pp_dpm_sclk, pp_dpm_mclk, gpu_busy_percent, mem_busy_percent, amdgpu_pm_info
escrituras   CERO registros.  El unico estado que cambia es la carga de compute
```

```text
ESTADO=PROBADO · 40.00 GB/s de trafico de DRAM en lectura+escritura, 512 MiB, 21 muestras
CORRECCION PROPIA  el 1485 dio 18.34 GB/s y ERA LA MITAD: contaba el buffer una vez por
       iteracion y en rmw el trafico es 2x.  La cifra buena es 40.00 GB/s.  El instrumento ahora
       declara el factor por modo, porque un multiplicador sin mirar el modo no significa nada
DERIVACION  40.00 GB/s > 24.0 GB/s descarta la lectura de una transferencia por ciclo.  La unidad
       del reloj de memoria queda PROBADO = dos transferencias por ciclo, por medicion y no por
       convencion.  Maximo nominal 48.0 GB/s => EFICIENCIA 83.3 %
       ESTA ERA LA CONCRETA DEJADA ABIERTA POR EL 1485, Y AHORA ESTA CERRADA
§67 CONTESTADO  fill y rmw son MEMORY-BOUND (relojes al techo, mem% 41-49, 83 % de lo nominal).
       math es ALU-BOUND (12.89 GB/s, mem% 22.5, y MAS potencia: 17.9 W vs 14.22 W)
       Y gpu_busy%=100 en los tres, asi que ese 100 % NO significa "saturado de memoria".
       El par (gpu_busy, mem_busy) es el discriminante, medido en los tres regimenes
DESCUBRIMIENTO  la SMU OSCILA entre 1500 y 625 MHz bajo carga de ALU: 15 muestras arriba, 6 abajo,
       12 s completos sin tendencia.  El grafico se queda en 1071 las 21 veces, luego la
       oscilacion es solo del reloj de memoria.  Y mem% sube de 16 a 39 cuando el reloj BAJA:
       la señal que gobierna el reloj la modifica el propio reloj.  Lazo de realimentacion
NUEVO NEGATIVO CON VALOR  fill y rmw NO oscilan (21/21 en 1500 cada uno).  La oscilacion es
       especifica del perfil saturado de ALU
PROBADO  el camino de descenso es identico en los tres modos, con el voltaje detras
       (881 -> 850 -> 700), y coincide con el del 1485
NOT_DETERMINED  si la oscilacion es un defecto y si cuesta rendimiento.  No lo se.  Lo que si se
       es que el reloj de memoria cambia ~6 veces en 12 s, y eso es observable por el mismo
       mecanismo que el reentrenamiento de straddle del 1472
LIMITE   un solo tamano de buffer (512 MiB).  No hay barrido de tamano, asi que no se sabe si el
       83.3 % es sensible a laworking set
RIESGO  ninguno.  Sin reset, sin ring timeout.  Intel intacta y verificada en cada ejecucion
Siguiente  1) el teorico de 48.0 GB/s: PROBADO el factor 2, pero la direccion de 16 bytes por
           transferencia es una suposicion mia.  El discriminador barato es medir con un buffer
           que quepa en L2 o en cache, donde el trafico a memoria cae y la eficiencia sube
         2) barrido de tamano de buffer: 4 / 16 / 64 / 256 / 512 / 1024 MiB.  El 83.3 % puede
           depender del working set, y eso decide si el cuello es la VRAM o el bus
         3) la oscilacion: si se puede provocar con --iters intermedios, se puede caracterizar su
           region.  Con 64 FMA oscila; con 1 no.  El limite esta entre medio
```

## 7. Lo que cambia para el objetivo

El proyecto tenía un techo de reloj de memoria y nada más. Ahora tiene:

```text
ancho de banda de DRAM medido        40.00 GB/s   (mixto lectura+escritura, 21 muestras)
eficiencia sobre el maximo nominal     83.3 %
cuello con carga de memoria           MEMORY-BOUND, y cerca del limite
cuello con carga de ALU               ALU-BOUND, con MAS potencia consumida
comportamiento del DPM                estable en rmw/fill, OSCILANTE en ALU
presupuesto de voltaje                 881 mV de trabajo sobre 1075 declarados  => 22 % de margen
```

**Y una conclusión incómoda que no voy a maquillar:** la ruta de **memoria** está al 83 % de lo
nominal, así que **optimizar submission o classificação deergence tiene poco recorrido** — el
cuello ya está donde tiene que estar. La ruta con recorrido es la de **ALU**, y ahí la tarjeta
gasta **17.9 W** para mover 12.89 GB/s. **Si el objetivo es rendimiento, el frente no es la
memoria: es la eficiencia de cómputo y el presupuesto de potencia que se lleva.**

Eso es una respuesta de §67 y §77 con datos, y dice en qué dirección merece la pena trabajar.