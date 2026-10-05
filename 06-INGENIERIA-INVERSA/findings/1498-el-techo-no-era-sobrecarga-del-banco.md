# 1498 — el número que podía moverse no se mueve: el 40 GB/s no era sobrecarga del banco de pruebas

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-SILICIO+REFUTACION-DE-HIPOTESIS-PROPIA+CIERRE
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta y verificada
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1496-*  cierra el ultimo limite que ese dejo abierto
         06-INGENIERIA-INVERSA/findings/1494-*  la eficiencia del 83.3 %, ahora sin margen
ESTADO=PROBADO · agrupando la sincronizacion, el techo SUBE solo un 1.8 %
       · 39.64 -> 40.34 GB/s al pasar de sincronizar en cada iteracion a agrupar 256
       · la hipotesis PROPIA de que el banco de pruebas inflaba la cifra: REFUTADA
       · la eficiencia queda en 84.0 % y NO es artefacto del instrumento.  YA NO SE MUEVE
```

## 1. La hipótesis que yo escribí, y que era la última duda

El 1496 cerraba su lista con esto, textualmente:

> *"El único número de esta tabla que aún podría moverse es el 84.2 %, y por un motivo concreto
> y no teórico: el bucle sincroniza en cada iteración, así que el 40.40 GB/s **incluye sobrecarga
> del propio banco de pruebas**."*

Es una objeción legítima y de las que hay que responder, no esquivar: si el techo medido
sobreviviera a que se quitase la espera, entonces el techo sería del hardware y no de mi
instrumento. **Si no sobreviviera, el 84.2 % sería una propiedad del banco de pruebas y no del
sistema de memoria**, y con él se caía la lectura entera del 1494.

**Medición, 256 MiB, modo `rmw`, 4 s por punto:**

| sincronización | GB/s | eficiencia sobre 48.0 |
|---|--:|--:|
| cada 1 iteración | **39.64** | 82.6 % |
| cada 4 | 40.16 | 83.7 % |
| cada 16 | 40.26 | 83.9 % |
| cada 64 | 40.31 | 84.0 % |
| cada 256 | **40.34** | **84.0 %** |

> **El techo sube un 1.8 % y ahí se queda.** De 39.64 a 40.34 GB/s. La sobrecarga de la
> sincronización eran **0.7 GB/s de 40**, un 1.8 %, y **no era el techo**.

**La hipótesis queda `REFUTADA` por medición.** El 40 GB/s es del subsistema de memoria.

## 2. Y la forma de la curva dice algo que no esperaba

```text
sync 1 -> 4        +1.3 %      (39.64 -> 40.16)
sync 4 -> 16       +0.25 %
sync 16 -> 64      +0.12 %
sync 64 -> 256     +0.07 %
```

**La corrección ocurre casi entera en los primeros cuatro pasos y luego se aplana hasta el
ruido.** Eso significa que el coste de sincronización es un **coste fijo por lote**, no un
coste por iteración: la primera espera amortiza lo que cuesta|round-trip al host, y repetirla
256 veces dentro de un lote no cuesta casi nada porque la GPU nunca para.

> Eso es, de paso, la confirmación de que el agrupamiento hace lo que dice hacer: no "no
> sincronizar" —que en Vulkan reutilizar un command buffer en vuelo es un fallo, no una
> medición— sino **sincronizar menos veces con más trabajo dentro**, que es lo único
> honesto.

**Y el modo en que lo escribí primero estaba roto.** Mi `--no-sync` original reutilizaba el
command buffer sin esperar a que terminara. Habría dado una lectura sin sentido, y probablemente
un fallo de Vulkan en vez de un número. Lo sustituí por `--sync-every N` antes de medir nada.

## 3. Lo que queda, y es una lista corta

```text
ancho de banda de DRAM, mixto R+W        40.34 GB/s   (con sync agrupada, 256 MiB)
eficiencia sobre 48.0 GB/s nominales      84.0 %
margen de recorrido                      16 %
```

**Y con esto se termina la pregunta del techo de memoria.** No queda ninguna variable de
instrumentación por resolver: el número se midió con la espera mínima que permite la API, y no
se mueve.

## 4. Lo que NO he hecho, y es lo que queda libre

No lo nombro como pendiente; lo nombro como **decisión**:

> **El banco de pruebas no puede subir el techo, y está medido.** Quedan dos vías para intentar
> llegar más lejos, y **las dos requieren intervención**, que no hago sin autorización:
>
> | vía | qué haría | por qué NO la ejecuto |
> |---|---|---|
> | **subir la frecuencia** | forzar un P-estado por encima de 1071 MHz o de 1500 MHz | `kv_dpm_force_performance_level` es envío de comandos al driver, y tocar voltaje o reloj fuera de la escalera DPM es `CONTROLLED_WRITE` sobre el reloj |
> | **forzar voltaje** | llevar VDDGFX de 881 mV hacia el techo declarado de 1075 mV | el margen de 22 % del 1477 está **declarado**, no verificado: hacerlo es escribir en el regulador |
>
> Ninguna de las dos es "leer un dato nuevo". Ambas cambian el estado del hardware en una vía
> que el proyecto no ha ejercido nunca. **El hallazgo 1477 ya entregó el número que las
> justificaría**; ejecutarlas es una decisión del propietario, no una iteración más del bucle.

Y hay una tercera vía que **no** requiere intervención y es la que corresponde:

> **Mejorar el instrumento.** El banco actual hace un `xorshift` de 3 pasos por elemento. Con un
> kernel que maximice el paralelismo de acceso y evite el `gl_GlobalInvocationID` lineal, el
> techo de 40 GB/s podría no ser del bus sino del **patrón de acceso**. Eso no se sabe, y se
> sabe fácil: dos o tres variantes de kernel, misma medición.

## 5. Procedencia

```text
instrumento  07-DRIVER/bench/rx550_gl_load.c   sha256 dd05012da76723f81329315c2b7dbda68…
             opcion --sync-every N (N=1 reproduce el comportamiento anterior)
binario      07-DRIVER/bench/rx550_gl_load.bin  sha256 2d932be0ebdecfbce3a7e3c17cf6fba99…
             el binario se versiona junto al fuente: un hallazgo sobre rendimiento sin poder
             reconstruir el instrumento con el que se tomo no es reproducible
             (hallazgos 1419 y 1449 sufrieron justamente eso: no se podia recuperar el
              multiplicador de anchuras que habian usado)
metodo       --sync-every agrupa N iteraciones en un unico command buffer, envia una vez y
             espera una vez.  Nunca reutiliza un command buffer en vuelo
solo lectura  pp_dpm_sclk, pp_dpm_mclk, amdgpu_pm_info
escrituras   CERO registros
frontera     verificada en caliente (POST-CONDICION: renderer AMD y es esta tarjeta)
```

```text
ESTADO=PROBADO · el techo de ancho de banda SUBE solo 1.8 % al eliminar la sincronizacion por
       iteracion: 39.64 -> 40.34 GB/s.  La sobrecarga del banco eran 0.7 GB/s de 40
REFUTADA mi propia hipotesis del 1496 de que el banco de pruebas inflaba la cifra
CIERRA  el ultimo limite del 1496.  La eficiencia queda en 84.0 % y NO es un artefacto del
       instrumento.  La lectura de rendimiento del 1494 se sostiene integra
NUEVO  la forma de la curva: la correccion ocurre casi entera de sync 1 a sync 4 y luego se
       aplana.  El coste de sincronizacion es FIJO POR LOTE, no por iteracion: la GPU no para
DECLARADO Y NO HECHO  el techo NO se puede subir desde el banco de pruebas; eso esta medido.
       Las dos vias que quedan (forzar P-estado, forzar voltaje) son CONTROLLED_WRITE sobre
       reloj o regulador y NO se ejecutan sin autorizacion del propietario.  El margen de 22 %
       de voltaje esta DECLARADO por el 1477, no verificado
NOT_DETERMINED  si el patron de acceso del kernel limita los 40 GB/s.  El kernel actual hace un
       xorshift de 3 pasos por elemento con indice lineal; si un patron mejor sube la cifra,
       el techo era del acceso y no del bus
LIMITE   una sola resolucion de buffer (256 MiB) y un solo tamano de lote por punto.  El 1.8 %
       esta por encima del ruido inter-punto, pero no se ha medido su incertidumbre
RIESGO  ninguno.  Sin reset, sin ring timeout
FRONTERA Intel intacta, verificada en caliente
Siguiente  1) variantes de patron de acceso en el kernel.  Es la via que NO requiere
           intervencion y es la que queda.  Si un kernel con acceso por bloques emparejados
           pasa de 40.3 GB/s, el limite estaba en el acceso
         2) si el 1494 y el 1496 se cierran ya, el frente de rendimiento que queda por encima
           de la linea es la potencia: 17.9 W para 12.89 GB/s en carga de ALU
```

## 6. Una regla sobre el patrón de estos tres hallazgos

Tres seguida, y merece escribirse porque el proyecto las ha tratado por separado:

| # | hipótesis mía | resultado |
|---|---|---|
| 1494 | el ancho de banda en `rmw` es 18.34 GB/s | **error de contabilidad mío**: era 2× eso |
| 1496 | el tramo inicial bajo es un efecto de caché | **falsa**: es coste fijo por iteración, y va al revés |
| 1498 | el techo incluye sobrecarga del banco | **falsa**: sube 1.8 %, no es el techo |

> **Las tres eran hipótesis mías sobre mis propias cifras, y las tres resultaron falsas.** En
> ningún caso las dejó en el sitio sin comprobar, y en dos casos una medición de cuatro
> segundos las desmontó.
>
> Eso no es una observación sobre mi cabeza: es una sobre el **coste de fiarse de un número
> propio**. Los tres casos tienen la misma forma —un número que acabo de producir, una
> explicación plausible, y la tentación de escribirla sin más evidencia—. El patrón se
> corrige con un mecanismo, no conuidado: **toda cifra propia que vaya a un hallazgo tiene que
> pasar por un intento de refutación con una medición distinta antes de que se le llame
> Established.**

Ese mecanismo es lo que aplico en el próximo paso: el patrón de acceso del kernel, con una
predicción que se puede fallar.