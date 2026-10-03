# 940 — El control de contenido no puede ver que falten despachos: 1024 despachos idénticos cuestan 6,8× menos que el mismo trabajo en uno solo

Estado: `PROVEN` para el observable. `NOT_DETERMINED` para el mecanismo. Invalida `--batch` como
instrumento para su propósito declarado.
Alcance: la RX 550 de esta placa, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU

## Qué se iba a medir

`938` dejó abierto si agrupar despachos en un command buffer es una ganancia, y para eso se añadió
`--batch=M` al banco. La primera pasada dio 87,8% menos tiempo por despacho al agrupar 64, mezclado
con un aumento de ocupación. El experimento controlado es `items × M` constante.

## El experimento controlado, y por qué no cerró

Con `items × M = 262144` constante y `wsize = 262144` (1 MiB, dentro de la L3), el trabajo total por
envío es idéntico:

| M | items | host | gpu | host/despacho |
|---|---|---|---|---|
| 1 | 262 144 | 2 588 µs | 2 471 µs | 2 588 µs |
| 2 | 131 072 | 2 564 µs | 2 468 µs | 1 282 µs |
| 8 | 32 768 | 2 561 µs | 2 474 µs | 320 µs |
| 16 | 16 384 | 2 543 µs | 2 468 µs | 159 µs |
| 32 | 8 192 | 2 375 µs | 2 302 µs | 74 µs |
| 64 | 4 096 | 1 738 µs | 1 637 µs | 27 µs |
| 128 | 2 048 | 857 µs | 734 µs | 6,7 µs |

`host` y `gpu` son constantes de M=1 a M=32 y luego **colapsan**. Con trabajo constante, el colapso no
lo explica el reparto del trabajo entre invocaciones ni la ocupación, y hay una comprobación que lo
descarta del todo.

## La comprobación que descarta la explicación fácil

La explicación fácil es «con M despachos pequeños hay más paralelismo y por eso es más rápido». Es
falsa, y se descarta repartiendo **el mismo trabajo dentro de un solo despacho** en vez de en varios:

| reparto del mismo trabajo | gpu |
|---|---|
| 1 despacho de 262 144 items × 8 iteraciones | 2 470 µs |
| 1 despacho de 65 536 × 32 | 2 393 µs |
| 1 despacho de 16 384 × 128 | 2 380 µs |
| 1 despacho de 4 096 × 512 | 2 373 µs |
| 1 despacho de 1 024 × 2 048 | 2 419 µs |
| **1 024 despachos de 256 × 8** | **363 µs** |

Las cinco primeras filas **cambian el paralelismo en un factor 256** — de 262 144 invocaciones a
1 024 — y ninguna se acerca a la sexta. Todas cuestan lo mismo. La sexta hace exactamente el mismo
trabajo y cuesta **6,8 veces menos**.

No es paralelismo. No es ocupacion. Con el trabajo total fijo, la cantidad de trabajo que la GPU
ejecuta depende de **cuántos command buffers hay**, no de cuánto trabajo hay.

## Los dos relojes coinciden

No es un artefacto de las marcas:

```
1 despacho    de 262144 x 8 :  host 2475 us    gpu 2471 us
1024 despachos de    256 x 8 :  host  475 us    gpu  367 us
```

El reloj del host —independiente de la API de marcas— dice lo mismo. El trabajo se terminó en 475 µs
de pared, y no puede haberse hecho en 367 µs de GPU si fueran 2 097 152 iteraciones de lectura
encadenada.

## Lo que no se puede decir

**No se afirma que el driver pierda despachos.** Eso sería una afirmación fuerte y no está
respaldada. Los candidatos, con su estado:

- **Optimización legítima.** Cada despacho calcula lo mismo y escribe en las mismas direcciones
  con los mismos valores. Las escrituras son idempotentes, asi que eliminar los 1 023 restantes
  **no cambia el resultado**. Un conductor que analiza eso puede hacerlo sin violar la
  especificación, y no sería un error: sería una optimización válida de un caso degenerado.
- **Truncamiento del command buffer.** Posible, y sería un error.
- **Otro límite del conductor.**
- **Otra causa que no se ha buscado.** No hay enumeración de despachos en un command buffer
  desde la API de Vulkan, asi que esta lista está incompleta **por construcción** y no por
  descuido. Una lista de candidatos que no se puede cerrar no es una lista cerrada.

Lo que sí es `PROVEN` y no depende de cuál sea: **con N despachos byte-idénticos en un command
buffer, el tiempo de GPU escala con log(N) en vez de con N**, en el rango medido.

## El hallazgo de fondo: el control no puede ver esto

El control de contenido pasa **256 de 256 en las seis filas**. Y es que no puede hacer otra cosa:
todos los despachos escriben en `d[WSIZE + i]` con los mismos valores, así que el último escritor
deja el resultado esperado tanto si corro uno como si corro 1 024.

**Un control que verifica el resultado final no verifica que se ejecutó cada unidad de trabajo.**
Con escrituras solapadas e idénticas, el resultado final es el mismo para todos los números posibles
de repeticiones, y el control es ciego a la diferencia.

Eso no es un defecto de este experimento: es una limitación de la forma del experimento. Y es la
misma limitación que inutiliza `--batch` para lo que se construyó. Con el banco actual, cualquier
medición de coste por despacho con despachos repetidos **no es válida**, porque el instrumento no
puede decir si se ejecutaron todos.

## Lo que hace falta para poder medirlo

Que cada despacho escriba en una región **disjunta**, de modo que el resultado esperado dependa de
cuántos despachos corrieron. Con el banco actual eso no se puede expresar: el shader no sabe qué
despacho es, y el banco no tiene push constants ni varios pipelines. Con 256 push constants —o con
varios pipelines— sí.

Alternativa más barata y ya disponible: **hacer los despachos distintos** con `vkCmdDispatchBase`
cambiando `baseWorkgroup`. Entonces las escrituras caen en sitios distintos y el control vuelve a
distinguir. No se ha probado.

## Instrumentos

- `vulkan_compute_probe.c`: `--batch=M` existe y funciona como flag. **Lo que no funciona es lo que
  se puso para medir con él**, y el banco sigue admittinglo sin avisar.
- `bench.py` 15 de 15, sin cambios en esta vuelta.

## Lo que `938` deja en pie y lo que no

De `938` queda en pie: el techo de envío de ~38 µs, el punto de cruce de 61 µs, y la corrección de
la magnitud de GPU. **Lo que cae es la pregunta que `938` dejó abierta** — «por debajo de 60 µs, ¿se
gana algo agrupando?» — porque no se puede responder con este banco, y ahora se sabe por qué.

## Errores propios

1. **Escribí el veredicto del sweep antes que los datos.** El script decía «se paga POR COMMAND
   BUFFER» con un umbral `a < 15` inventado, y los números no lo sostenian: `host` no era constante
   en M. El rótulo iba puesto antes de mirar.
2. **Atribuí el colapso a más paralelismo** antes de hacer la comprobación que lo descartaba. La
   explicación fácil era buena, y por eso había que comprobarla en vez de adoptarla.
3. **`--batch` quedó en el banco sabiendo que no se podía medir con él.** Un flag que no puede
   cumplir su propósito declarado es un flag que va a usarse por su nombre.