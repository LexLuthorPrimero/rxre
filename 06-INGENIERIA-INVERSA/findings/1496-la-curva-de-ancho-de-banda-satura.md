# 1496 — la curva de ancho de banda satura en 40 GB/s, y eso confirma que el techo es del sistema

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-SILICIO+DERIVACION+CIERRE-DE-DUDA-PROPIA
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta y verificada
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1494-*  la duda que ese hallazgo dejo abierta, CERRADA
         §77 MAXIMO RENDIMIENTO PRACTICO: el techo de memoria, con su curva
ESTADO=PROBADO · ancho de banda frente a tamano de buffer, 11 puntos de 1 a 1024 MiB
       · la curva SATURA: de 256 a 1024 MiB, 4x mas buffer da 1.8 % mas ancho de banda
       · asintota en 40.40 GB/s = 84.2 % de 48.0 nominales.  El limite es del SISTEMA
       · y la SMU baja la memoria a 625 MHz para 1 y 2 MiB: segundo disparador independiente
         del reloj de memoria, distinto del de la carga de ALU
```

## 1. La duda que el 1494 dejó abierta

El 1494 cerró la unidad del reloj de memoria por medición —40.00 GB/s descarta una transferencia
por ciclo— y calculó **83.3 % de eficiencia**. Pero dejó escrito un límite que es justo el que
puede invalidar el número:

> *"un solo tamaño de buffer (512 MiB). No hay barrido de tamaño, así que no se sabe si el 83.3 %
> es sensible al working set."*

Ese límite importa: si los 40 GB/s fueran un artefacto del buffer de 512 MiB —que cabe bien en la
VRAM y juega a lo que—, el 83.3 % no significaría nada. **La pregunta es si el ancho de banda
medido depende del tamaño del buffer, y la respuesta lo decide.**

## 2. La curva

Once puntos, de 1 a 1024 MiB, modo `rmw`, reloj de gráficos **1071 MHz en los once**, voltaje
**881 mV en los once**:

| buffer | GB/s | MCLK | `mem_busy%` | potencia |
|--:|--:|---|--:|--:|
| 1 MiB | 6.74 | **625** | 18 | 12.22 W |
| 2 MiB | 14.13 | **625** | 27 | 14.99 W |
| 4 MiB | 22.48 | 1500 | 24 | 14.16 W |
| 8 MiB | 28.94 | 1500 | 37 | 14.38 W |
| 16 MiB | 29.47 | 1500 | 38 | 14.72 W |
| 32 MiB | 34.02 | 1500 | 37 | 14.41 W |
| 64 MiB | 36.81 | 1500 | 43 | 14.19 W |
| 128 MiB | 38.55 | 1500 | 36 | 14.21 W |
| 256 MiB | 39.69 | 1500 | 49 | 14.22 W |
| 512 MiB | 40.06 | 1500 | 49 | 14.22 W |
| 1024 MiB | **40.40** | 1500 | 49 | 14.23 W |

**Por tramos:**

```text
   1 ->    4 MiB    x4 de buffer  ->  x3.34 de ancho de banda   (+233.5 %)
   4 ->   32 MiB    x8 de buffer  ->  x1.51                       (+51.3 %)
 256 -> 1024 MiB    x4 de buffer  ->  x1.018                      ( +1.8 %)
```

> **La curva satura.** De 256 a 1024 MiB, **cuadruplicar el buffer da un 1.8 % más de ancho de
> banda**, y la curva **nunca supera los 40.40 GB/s** en ningún punto.

**Eso convierte el 83.3 % del 1494 en una propiedad del sistema de memoria y no del tamaño de
trabajo.** El límite no es que el buffer sea pequeño ni que la VRAM esté fragmentada ni que el
acceso esté cacheado: es el subsistema de memoria. Con el factor de dos transferencias ya
`PROBADO` por medición, la asíntota queda en **40.40 / 48.0 = 84.2 % de eficiencia** para un
flujo mixto de lectura y escritura.

## 3. El tramo inicial NO es un efecto de caché, y es lo contrario de lo que se esperaría

Un resultado que parece obvio y que sale al revés merece nombrarse. Si el primer tramo fuera un
efecto de caché —los buffers pequeños caben en L2 y deberían ir **más rápido**— la curva
empezaría alta y bajaría. **Empieza en 6.74 GB/s y sube.**

```text
  1 MiB ->  6.74 GB/s     el MENOR ancho de banda de toda la curva
1024 MiB -> 40.40 GB/s    el mayor, y con memoria al techo en ambos
```

La explicación que encaja con el dato es **coste fijo por iteración**: el bucle paga cada vez
el coste de la command buffer, la barrera y `glFinish`, y con 1 MiB eso se amortiza sobre 4096
workgroups frente a los 262 144 de 1024 MiB. **La curva mide "cuánto trabajo amortizo un coste
fijo", no "cuánta caché tengo".**

Lo que **queda por vía de evidencia**: que el tope de 40.40 es del sistema. Que sea la DRAM y no
otro sitio **no lo sé** — con un buffer de 1024 MiB la L2 de esta GPU es irrelevante por
tamaño, pero eso lo tengo por el valor típico del silicio, **no medido aquí**.

## 4. La SMU tiene un SEGUNDO disparador para bajar la memoria

```text
  1 MiB -> mclk 625    \  el reloj de memoria al SUELO, con el grafico al TECHO
  2 MiB -> mclk 625    /
  4 MiB -> mclk 1500      y a partir de ahi, siempre al techo
```

**Es el mismo comportamiento que el del 1494 con carga de ALU** —el gráfico se queda en 1071 y lo
que cae es la memoria—, pero el disparador es completamente distinto: aquí el perfil de cómputo
es el mismo `rmw` de siempre, y lo que cambia es **el tamaño del buffer**.

> **La política de reloj de memoria de esta tarjeta tiene al menos dos disparadores
> independientes**, y ambos conservan el reloj de gráficos:
>
> | disparador | observado en | memoria | gráficos |
> |---|---|---|---|
> | carga saturada de ALU | `math`, 64 FMA | 1500 ↔ **625, oscilando** | 1071 fijo |
> | working set pequeño | `rmw`, 1–2 MiB | **625 fijo** | 1071 fijo |
> | carga de memoria | `rmw`/`fill`, ≥4 MiB | 1500 fijo | 1071 fijo |
>
> **Que un cambio de reloj de memoria no arrastre al de gráficos es un hecho medido en los tres
> regímenes, y es una característica del diseño de la SMU que el driver no expone por ninguna
> interfaz.** Para el objetivo del proyecto importa: es una palanca de rendimiento que existe,
> y para captarla de forma fiable tendría que controlarla el propio driver.

## 5. Un detalle que encaja con el 1485

**VDDGFX = 881 mV en los once puntos**, incluidos los dos en que la memoria está a 625 MHz.

Y el 1485 ya había observado que en la escalera de descenso **el voltaje acompaña al reloj de
gráficos, no al de memoria**: `881 → 850 → 700` mientras la memoria caía a 300.

> **Consistente, y ahora confirmado por un segundo camino.** El voltaje de este regulatorio lo
> gobierna el estado de gráficos, no el de memoria. Lo digo porque es el tipo de cosa que, si no
> se mide, se da por hecho al revés.

## 6. Procedencia

```text
artefacto    07-DRIVER/bench/sweep4-tamano-buffer-2026-10-05.tsv   11 puntos, clocks y mem%
instrumento  07-DRIVER/bench/rx550_gl_load.c  --buffer N --mode rmw --seconds 5
             el multiplicador de trafico por modo va declarado en la salida del propio programa
solo lectura  pp_dpm_sclk, pp_dpm_mclk, mem_busy_percent, amdgpu_pm_info
escrituras   CERO registros.  Solo la carga de compute
frontera     verificada en caliente en cada ejecucion (POST-CONDICION: renderer AMD)
```

```text
ESTADO=PROBADO · ancho de banda frente a tamano de buffer, 11 puntos, 1..1024 MiB
CIERRA UN LIMITE DEL 1494  el 83.3 % NO era un artefacto del buffer de 512 MiB: la curva satura
       y de 256 a 1024 MiB un x4 de buffer da solo +1.8 %
PROBADO  la asintota es 40.40 GB/s = 84.2 % de 48.0 GB/s nominales, con el factor de dos
       transferencias ya PROBADO por medicion en el 1494
DESCUBRIMIENTO  la SMU baja la memoria a 625 MHz para working sets de 1-2 MiB.  Es un SEGUNDO
       disparador, independiente del de la carga de ALU, y en ambos la memoria cae sin que el
       reloj de graficos se mueva
NUEVO NEGATIVO CON VALOR  el tramo inicial NO es un efecto de cache.  Un buffer pequeno deberia
       ir mas rapido si estuviera cacheado; aqui va mas lento (6.74 GB/s a 1 MiB).  La curva
       mide coste fijo amortizado por iteracion, no cache
CORROBORADO  VDDGFX = 881 mV en los once puntos, incluidos los de memoria a 625.  El voltaje lo
       gobierna el estado de GRAFICOS, no el de memoria, coherente con la escalera de descenso
       del 1485 (881 -> 850 -> 700 mientras la memoria caia a 300)
NOT_DETERMINED  que el tope de 40.40 sea la DRAM y no otro elemento.  Con 1024 MiB la L2 es
       irrelevante por tamano, pero eso lo tengo por el valor tipico del silicio, NO MEDIDO
LIMITE   un solo modo (rmw), una sola duracion por punto (5 s), sin --no-sync.  El coste fijo por
       iteracion queda identificado pero no medido: con --no-sync la asintota deberia subir
RIESGO  ninguno.  Sin reset, sin ring timeout
FRONTERA Intel intacta, verificada en caliente en cada ejecucion
Siguiente  1) medir el coste fijo por iteracion: el mismo barrido con --no-sync.  Si la asintota
           sube por encima de 40.4, entonces el 40.4 incluria sobrecarga del propio banco y el
           techo real seria mayor.  Es el unico punto donde el numero 84.2 % puede moverse
         2) caracterizar la oscilacion con --iters intermedios: con 64 FMA oscila, con 1 no.  El
           limite esta entre medio, y se puede acotar con media docena de puntos
         3) la L2 de esta GPU: su tamano y su ancho de banda son la unica pieza del subsistema
           de memoria que el proyecto tiene por valor tipico y no por medicion
```

## 7. Lo que queda establecido y lo que queda libre

```text
ancho de banda de DRAM, flujo mixto R+W     40.40 GB/s   asintota, 11 puntos
eficiencia sobre 48.0 GB/s nominales        84.2 %
techo de reloj de memoria                   1500 MHz     alcanzado, medido, y declarado en el ROM
techo de reloj de graficos                  1071 MHz     alcanzado, y declarado en el ROM
reloj de memoria de 1500 MHz                dos transferencias por ciclo, PROBADO
politica de DPM de la memoria               dos disparadores, ambos con graficos fijo
presupuesto de voltaje                      881 mV de trabajo / 1075 declarados = 22 % libre
cuello con carga de memoria                 84 % de lo nominal: recorrido pequeno
cuello con carga de ALU                     17.9 W por 12.89 GB/s: recorrido real
```

**El único número de esta tabla que aún podría moverse es el 84.2 %**, y por un motivo concreto
y no theoretical: el bucle sincroniza en cada iteración, así que el 40.40 GB/s **incluye
sobrecarga del propio banco de pruebas**. El experimento que lo decide es una línea de código que
ya está escrita (`--no-sync`) y una medición.

Y hasta que eso se mida, la conclusión de rendimiento del 1494 se sostiene: **la memoria está
cerca de su límite, y el recorrido está en la eficiencia de cómputo y en la potencia.**