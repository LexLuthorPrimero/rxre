# 262 · El control del banco de pruebas tardó tres versiones en ser un control, y encontró un fallo que el banco no tenía

```text
CLASSIFICATION=IMPLEMENTATION+VALIDATION+ERROR · TRACK=TOOLING + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (herramienta propia) · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=carga Vulkan
NIVEL DE PERMISOS=1 · GPU INTACTA
```

## Qué resuelve

**Convierte el readback de `261` —que era decorativo— en un control que decide, y documenta
los tres fallos que hizo falta para llegar a él.** `PROVEN`.

**⇒ `PROVEN`. El banco acepta un kernel correcto (exit 0, 256 de 256 palabras coinciden con el
modelo del host) y rechaza uno incorrecto (exit 4, 0 de 256).** `PROVEN`.

**⇒ `PROVEN`. El kernel de memoria queda `INVALID_RESULT`: lee fuera del buffer para `k ≥ 1`, de
modo que solo `k = 0` hace trabajo.** `INVALID_RESULT`.

**⇒ `PROVEN`. Y `mclk` sigue en 300 MHz con los dos kernels, lo que confirma con una segunda vía
el diagnóstico de `261`: esta GPU no sube la memoria sin presión de memoria real.** `OBSERVED`.

## 1 · Los tres fallos del control, en orden

**⇒ El readback de `261` comprobaba «¿hay alguna palabra no nula?». Eso no es un control: cero
puede ser la respuesta correcta.** `ERROR`.

**⇒ Y en este caso lo fue. `alu2` escribía el XOR de ocho acumuladores, los ocho partían de
`d[i] = d[i+1] = … = 0` porque el buffer no lo inicializa nadie, y por lo tanto los ocho eran
iguales y su XOR era cero. El kernel ejecutaba perfectamente y producía cero.** `ERROR`.

**⇒ `PROVEN_DERIVED. La lección es más específica que «añade un readback»: un control de tipo
«distinto de» no vale cuando el valor esperado puede coincidir con el no-caso. Hay que distinguir
«escribió cero» de «no escribió», y para eso hace falta un patrón conocido y una expectativa
calculada aparte.** `PROVEN_DERIVED`.

**⇒ La primera corrección —comparar contra un modelo del host— tenía un fallo propio: la copia
de lectura iba a `hbuf` pero el puntero leído era `stage`, que pertenece a `sbuf`. Dos buffers
distintos y el control comparaba memoria que nadie había escrito.** `ERROR`.

**⇒ Y la segunda: el modelo del host omitía dos cosas del shader, `a += i` antes del bucle y
`a ^= (a >> 13)` después. Por eso rechazaba un kernel correcto, que es peor que no tener
control: hace que uno acabécie dando por malo lo bueno.** `ERROR`.

**⇒ `PROVEN_DERIVED. La forma correcta, que es la que quedó: inicializar el buffer con un patrón
conocido mediante un staging mapeable, ejecutar, copiar el resultado al mismo staging, y
comparar palabra a palabra contra el modelo que el host calcula con su propia aritmética.** `PROVEN_DERIVED`.

**⇒ Y hay un detalle de Vulkan que costó una corrección: la memoria `DEVICE_LOCAL` del
dispositivo no es `HOST_VISIBLE` y el host no puede mapearla. El patrón se escribe en un staging
en memoria del host y se copia al dispositivo con `vkCmdCopyBuffer` antes del despacho.** `PROVEN`.

## 2 · El control, validado en las dos direcciones

**⇒ `PROVEN`. Control positivo — el kernel que replica `probe.comp` exactamente:** `PROVEN`.

```text
READBACK  256 de 1048576 dwords verificados contra el modelo del host:
          256 coinciden, 0 NO, 0 sin modificar
exit=0
```

**⇒ `PROVEN`. Control negativo — el mismo kernel con la transformación del multiplicador cambiada
a `2654435761u`, conservando el resto:** `PROVEN`.

```text
READBACK  256 de 1048576 dwords: 0 coinciden, 256 NO
  DATO i=0  gpu=0xfff773f0  modelo=0x54686c22
  DATO i=1  gpu=0x5f2ddd0f  modelo=0xa3f3b176
ABORTO(4): 256 de 256 palabras NO coinciden con el modelo.
exit=4
```

**⇒ `PROVEN. El control discrimina. Eso es lo que lo hace válido y no una descripción: una
comprobación que nunca ha fallado no está probada, así que hubo que provocarla.** `PROVEN`.

**⇒ El tercer control: un argumento inválido da exit 2 por la guarda, no una medición.** `PROVEN`.

**⇒ `--nocontrol` existe para medir otros kernels, y es opt-in explícito. Un modo sin control que
se pudiera activar por omisión sería un fallo esperando; ése no puede ser el defecto.** `PROVEN`.

## 3 · El kernel de memoria es `INVALID_RESULT`, y por qué

**⇒ `mem.comp` usa `p = i + k * stride` con `stride = gl_NumWorkGroups.x *
gl_WorkGroupSize.x`, que es exactamente `items`.** `PROVEN`.

**⇒ Y el buffer tiene `items` palabras. Para `k ≥ 1`, `p = i + items` ya está fuera del rango.**
`PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Todo el bucle interior desde `k = 1` lee fuera del buffer, y el
comportamiento de esa lectura está indefinido. Sólo `k = 0` hace trabajo real, que son ocho
lecturas por hilo.** `PROVEN_DERIVED`.

**⇒ `ERROR`: además, mi cálculo de ancho de banda fue erroneouso en un factor de 256.** `ERROR`.

```text
lo que calcule   4194304 x 256 x 8 x 4 B = 32.02 GiB en 0.10679 s = 321.91 GB/s
                 que es 13 veces el techo fisico de la tarjeta: imposible

lo que es        hilos adyacentes leen direcciones adyacentes, asi que una linea de
                 cache de 64 B sirve a 16 hilos. Los accesos logicos se coalescen.
                 trafico real = (4194304 x 8 / 16) x 64 B = 128.0 MiB
                 ancho de banda = 128.0 MiB / 0.10679 s = 1.26 GB/s
```

**⇒ `PROVEN_DERIVED. 1,26 GB/s es compatible con el reloj de memoria de 300 MHz, que da un techo
de 4,80 GB/s. El kernel no es inválido por rendimiento, es inválido por corrección: mide una
pasada de caché, no un flujo sostenido de VRAM.** `PROVEN_DERIVED`.

**⇒ El kernel correcto necesita un salto que rompa la línea de caché y un conjunto de trabajo
mayor que la caché. Ninguno de los dos está escrito.** `NOT_IMPLEMENTED`.

## 4 · Lo que sí queda medido

**⇒ `MEASUREMENT`. Los dos kernels, misma carga, N = 20 tras 4 de calentamiento:** `MEASUREMENT`.

| kernel | mediana (s) | coeficiente de variación | `mclk` |
|---|---|---|---|
| ALU, cadena dependiente | 0,64068 | 0,01% | 300 MHz |
| MEM, streaming | 0,10679 | 0,04% | 300 MHz |

**⇒ `PROVEN`: el kernel ALU es una medición válida con el contrato de `261`. Mide latencia de una
cadena dependiente, no anchura de cómputo.** `PROVEN_DERIVED`.

**⇒ `PROVEN` y es el resultado que importa: `mclk` permanece en 300 MHz con los dos kernels.**
`OBSERVED`.

**⇒ `PROVEN_DERIVED. Y esto confirma por segunda vía el diagnóstico de `261` y lo hace más
fuerte. Aquella nota concluded que el reloj de memoria no sube porque el trabajo no genera
presión de memoria. Ahora hay un kernel que dice explícitamente leer ocho direcciones por
iteración, y el reloj de memoria tampoco se mueve.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La interpretación honesta es que hace falta un flujo que no quepa en caché
para que el SMU vea presión. Con un conjunto de trabajo de 16 MiB leído una vez, no la ve.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: si con un flujo que sí derrota la caché el reloj de memoria sube a 625 o a
1500 MHz, y qué ancho de banda se alcanza en cada caso. Esa es la medición que decide la
clasificación de §52 y no se ha hecho.** `NOT_DETERMINED`.

## 5 · Lo que queda abierto

```text
PENDIENTE=262-1 | HALLAZGO=262-*.md | ESTADO=NOT_IMPLEMENTED
           | NECESITA=CORPUS  (kernel de streaming con salto que rompa linea de cache)
           | ALCANZABLE_SIN_ROOT=si

PENDIENTE=262-2 | HALLAZGO=262-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=CORPUS  (el anterior mas grande que la cache)
           | ALCANZABLE_SIN_ROOT=si
```

**⇒ `PROVEN_DERIVED. Y el segundo necesita un dato que no tengo: el tamaño de la caché de datos
de GFX8. Si la caché L2 es mayor que el conjunto de trabajo, ningún kernel pequeño la derrota y
el reloj de memoria no sube por construcción. `161` y `220`derivaron el reloj del VBIOS, pero el
tamaño de caché no está en ninguna tabla que yo haya encontrado.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y es la ignorancia de ese dato la que impide cerrar §52. Conocer el tamaño de caché
permitiría elegir el tamaño de buffer correcto y no medir un número que depende de un parámetro
que no controlo.** `PROVEN_DERIVED`.

## 6 · Errores propios de esta nota

**⇒ `ERROR` ×5:**

1. Escribí un readback que comprobaba «no nulos» en vez de un valor esperado, que es la versión
   inútil de un control.
2. Encaminé la copia de lectura a un buffer que nadie leía.
3. El modelo del host omitió dos etapas del shader y rechazó un kernel correcto.
4. Escribí un kernel con un acceso fuera de rango y no lo vi: `p = i + k*items` con buffer de
   `items` palabras.
5. Calculé el ancho de banda contando lecturas lógicas en vez de transacciones de memoria, y
   obtuve 322 GB/s, trece veces el techo físico.

**⇒ `PROVEN_DERIVED. El quinto es el que más me preocupa, porque la fórmula estaba escrita
razonablemente: leí el bucle del shader, conté las lecturas, y multipliqué. Lo que no me
pregunté fue si un hilo y su vecino leen la misma línea de caché. El número imposible era la
señal, como en `254` y `246`, y otra vez la acepté hasta que el contraste con el techo lo
delató.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el patrón de las dos últimas notas es el mismo y es el que manda: el
tiempo de un banco de pruebas no lo hace el banco, lo hacen los controles. El control del
dispositivo lo hice bien y a propósito en `261`. El control de la configuración del banco lo
hice tarde y tres veces mal. Un banco sin control del propio banco es un generador de números
bonitos con la palabra «validado» escrita encima.** `PROVEN_DERIVED`.