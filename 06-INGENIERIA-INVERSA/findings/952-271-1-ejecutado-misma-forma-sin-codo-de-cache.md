# 952 — `271-1` ejecutado: la misma forma con otro kernel, ningún codo de caché, y un escalón al revés a 8 MiB

Estado: `271-1` → `NOT_DETERMINED` con la causa nombrada. El discriminante propuesto no puede cerrarlo.
Instrumentos: banco con magnitudes emparejadas, control de contenido activo en los ocho puntos.

## El frente, tal como estaba

```
PENDIENTE=271-1 | ESTADO=REOPENED
           | MOTIVO=la meseta de 271 era artefacto; rehacer el barrido de tamaño de
           |         conjunto de trabajo con occ.comp y no con cache.comp
```

Lo llevaba tres notas citando como «el más antiguo y el único reabierto a propósito sin constancia
de cierre», sin leerlo. Es el mismo error que `282-2`: el estado de un frente leído de una fuente
secundaria. Leyéndolo, el discriminante es concreto y ejecutable.

## Por qué el discriminante era el correcto, y por qué no basta

Los dos kernels se diferencian justo en lo que `271` veía mal:

```
cache.comp:  idx = (i + k * STRIDE) % total
             el índice sale del CONTADOR DEL BUCLE, no del dato. Un prefetcher lo
             anticipa entero. El tiempo por acceso es TASA DE EMISIÓN.

occ.comp:    idx = hash(valor leído) % WSIZE
             el índice sale del DATO. Cadena dependiente. El tiempo por acceso es
             LATENCIA.
```

Ese era el discriminante de `271-1`, y está bien puesto: si la meseta de `cache.comp` era un
artefacto de emisión, `occ.comp` no debería mesetar igual.

## El confound que hubo que arreglar antes de medir

La primera pasada dio una curva con la forma correcta y **no significaba nada**: con
`items × ITERS` fijo en 65 536 accesos, la huella no crece con `W`. Cada acceso de `occ.comp` toca una
línea de 64 B porque el índice sale de un hash, luego 65 536 accesos tocan como mucho **4 MiB**, y
subir `W` de 32 MiB a 64 MiB ya no crece la huella: solo la dispersa.

Para que `W` SEA el conjunto de trabajo, los accesos tienen que crecer con `W`: `accesos = W / 64`, y
`ITERS = accesos / items`. Es lo que significa «barrer el conjunto de trabajo», y la primera versión no
lo hacía.

**Es la clase de fallo de siempre:** el parámetro nominal no es la magnitud física. Igual que en `282`
el conjunto de trabajo de 4 KiB, y que en `940` donde los despachos repetidos no se ven.

## El resultado

Ocho puntos, `items = 256`, control de contenido activo en todos, 11 repeticiones con mediana:

| W | accesos | host | ns/acceso | **marginal** ns/acceso |
|---|---|---|---|---|
| 64 KiB | 1 024 | 53 µs | 51,76 | — |
| 256 KiB | 4 096 | 77 µs | 18,80 | 7,81 |
| 1 MiB | 16 384 | 167 µs | 10,19 | 7,32 |
| 4 MiB | 65 536 | 539 µs | 8,22 | 7,57 |
| 8 MiB | 131 072 | 714 µs | 5,45 | **2,67** |
| 16 MiB | 262 144 | 1 234 µs | 4,71 | 3,97 |
| 32 MiB | 524 288 | 1 757 µs | 3,35 | 2,00 |
| 64 MiB | 1 048 576 | 3 429 µs | 3,27 | 3,19 |

**La curva se aplana, y se aplana hacia abajo.** El tiempo por acceso no sube nunca. Un codo de caché
sube: al dejar de caber el conjunto, cada acceso se va a memoria y cuesta más.

## El escalón, que es lo que no sé explicar

El marginal tiene **dos regímenes**, con un escalón en 8 MiB:

```
W <= 4 MiB    marginal ≈ 7,3 – 7,8 ns por acceso
W >= 8 MiB    marginal ≈ 2,0 – 4,0 ns por acceso
```

8 MiB es exactamente el tamaño de la L3 de esta i7-4790. Y el coste **cae** 2,3 veces al cruzarla.

**Una caché no puede explicar que al dejar de caber el acceso sea más barato.** Es lo contrario de lo
esperado, y no lo tengo explicado. Queda `NOT_DETERMINED`, con candidatos y sin elegir:

- La cadena, al ser una iteración determinista de `hash(prev) % W`, **colapsa sobre un ciclo**. Con W
  pequeño el mapa se parece a una permutación y recorre casi todo; con W grande es una función
  aleatoria sobre muchos puntos y su atractor se alcanza antes. Eso cambiaría el número de líneas
  distintas tocadas, y por tanto el coste, **sin que nada en la jerarquía de memoria cambie**.
- El trabajo de GPU reportado cae en el mismo punto (de 480 ms a 312 ms entre 8 y 16 MiB), lo que
  apunta a menos líneas tocadas y no a una caché más rápida.
- Una variación de la ocupación: con `items = 256` hay 4 workgroups y el reparto entre CUs cambia con
  el tamaño del buffer.

El primero es comprobable y barato: **contar las direcciones distintas que toca la cadena**. El shader
puede hacerlo con un bitmap, y dice si la huella se satura. Es la acción siguiente.

## Lo que esto hace con `271-1`

**El discriminante propuesto no puede cerrarlo.** Cambiar de kernel  si el artefacto era de
`cache.comp`; y la respuesta es que la forma se reproduce igual con un kernel cuya latencia no se puede
anticipar. O sea: **la forma no es un artefacto de `cache.comp`**, que era media de la hipótesis, pero
tampoco es un codo de caché, que era la otra mitad.

Lo que el barrido mide es la dinámica de la cadena, no la jerarquía de memoria, porque en una cadena
dependiente **la huella la fijan los datos y no `W`**. Y esa es la razón por la que `271-1` no se
cierra cambiando de kernel: hay que cambiar qué se barre.

**Efecto lateral útil:** `270` explicó el aplanamiento como amortización del coste de lanzamiento, y
`938` midió ese coste directamente por otra vía —38,06 µs fijos por envío—. Aquí aparece el mismo
efecto con un tercer kernel. Tres caminos independientes al mismo mecanismo.

## Error propio

Dividí microsegundos por accesos y **etiqueté la columna «ns por acceso»**. Los valores salieron mil
veces más pequeños: 0,0033 ns por acceso, que a 1 071 MHz son 0,0036 ciclos, físicamente imposible
para una cadena dependiente. Lo detectó la física, no la mirada.

Es la tercera vez hoy que un número viola una restricción conocida y eso es lo que lo delata —las dos
anteriores, `gpu/host = 2,5` y `0,0036 ciclos`—. **Un invariante conocido es un detector de errores
gratis**, y no lo he declarado como control en ningún sitio. Es lo que compra esta nota.

## Instrumentos

Banco con magnitudes emparejadas y control de contenido activo. La suite que hace este barrido **no
existe todavía**: esto fue un script de un solo uso, y por lo tanto no es reproducible por el runner.
Sin suite, esto es un hallazgo de una sesión y no un dato del proyecto.

## Lo que queda abierto

- **Contar las direcciones distintas que toca la cadena.** Es lo que separa «la huella se satura» de
  «la caché cambia». Barato: un bitmap en el shader, y el control de contenido lo puede replicar.
- **Meter el barrido en `bench.py` como suite**, con su control y su artefacto. Sin eso, repetirlo es
  reescribir el script.
- **El escalón de 8 MiB**, `NOT_DETERMINED` hasta que se sepa si es la huella o la ocupación.
- **La ruta de `942`**: que `fronteras.py` distinga «reservada y no escrita» de «nunca reservada».
- **`277-1` y `281-1`**, los otros dos frentes `OPEN` más antiguos. Ninguno leído en esta sesión.
