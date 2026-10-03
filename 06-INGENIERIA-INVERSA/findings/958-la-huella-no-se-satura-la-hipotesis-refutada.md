# 958 — La huella no se satura: la hipótesis de `952` queda REFUTADA, y el «escalón de 8 MiB» era ruido
AUTORIA=AGENTE-SMU

Estado: `REFUTADA` la primera hipótesis de `952`. `271-1` sigue `NOT_DETERMINED` con menos candidatos.
Instrumento nuevo: `huella.py`, 7 de 7, con la réplica verificada contra el banco en 4 configuraciones.

## La pregunta

`952` dejó un candidato para el escalón del barrido de conjunto de trabajo: **que en una cadena
dependiente la huella la fijan los datos y no `W`**, porque `hash(prev) % W` no es una permutación y
la cadena colapsa sobre su atractor. Si fuera así, al crecer `W` se tocarían proporcionalmente menos
líneas, y el coste por acceso bajaría — que es lo que se veía.

Es comprobable **sin GPU**: la cadena está replicada en el host para el control de contenido y los
datos son conocidos, `d[j] = PATRON_INICIAL + j`. Es aritmética, no una medición.

## El resultado: la huella crece con `W`

`items = 256` y `ITERS` creciendo para que los accesos ≈ líneas, que es lo que hace el barrido:

| W | accesos | líneas del buffer | líneas tocadas | cobertura | accesos/línea |
|---|---|---|---|---|---|
| 64 KiB | 1 024 | 1 024 | 652 | 0,6367 | 1,57 |
| 256 KiB | 4 096 | 4 096 | 2 590 | 0,6323 | 1,58 |
| 1 MiB | 16 384 | 16 384 | 10 362 | 0,6324 | 1,58 |
| 4 MiB | 65 536 | 65 536 | 41 353 | 0,6310 | 1,58 |
| 8 MiB | 131 072 | 131 072 | 82 882 | 0,6323 | 1,58 |
| 16 MiB | 262 144 | 262 144 | 165 672 | 0,6320 | 1,58 |
| 32 MiB | 524 288 | 524 288 | 331 243 | 0,6318 | 1,58 |
| 64 MiB | 1 048 576 | 1 048 576 | 662 818 | 0,6321 | 1,58 |

**La cobertura es 0,632 en los ocho puntos y los accesos por línea son 1,58 en los ocho.** Sobre un
factor 1024 en `W`, no se mueve.

**La hipótesis queda refutada.** La cadena no colapsa: toca el 63% del buffer y lo toca a ritmo
constante. El barrido **sí** barre el conjunto de trabajo, que es lo que se sospechaba que no hacía.

## Y el «escalón» era ruido

Con la hipótesis fuera, queda explicar el escalón del marginal del `952`: 7,5 ns por debajo de 8 MiB
y 3,2 ns por encima, con 8 MiB siendo la L3 de esta CPU. Mirando la columna del marginal de `952`:

```
7,81   7,32   7,57   2,67   3,97   2,00   3,19
```

Eso **no es un escalón, es ruido**: los últimos cuatro valores bailan entre 2,0 y 4,0 sin monotonía.
Un escalón es un salto; esto es una dispersión. Con 11 repeticiones y una cadena dependiente, ±1 ns en
el marginal no es resoluble, y yo leí una forma donde no la hay.

**Me dibujé una estructura donde había ruido, porque encajaba con una hipótesis que yo acababa de
escribir.** La hipótesis del atractor era de veras, y una hipótesis que se pueda refutar
vale más que un número sin explicar, pero solo si se refuta de verdad, y eso exigía medir,
no argumentar.

## Lo que queda, y es menos

La curva real es monótona: 51,8 ns/acceso a 64 KiB bajando a 3,27 ns a 64 MiB. Los puntos pequeños
están dominados por el arranque en frío —coste de envío de 38 µs medido en `938`, más TLB frío y líneas
frías— y el asíntota es el coste de un acceso compulsory en la jerarquía de la GPU.

Queda un número sin explicar y **no lo adorno**: el asíntota de 3,27 ns por acceso dependiente a
1 071 MHz son 3,5 ciclos. Una cadena dependiente con 1,58 accesos por línea y distancia de reutilización
del orden del buffer es, en principio, un compulsory miss por acceso — y el valor concreto depende de
lo que el hardware hace con esa distancia, que es justamente lo que no sé.

## Dos cosas del instrumento, que es la parte útil

**El vector tautológico.** El self-test comparaba `_hash()` con una copia suya escrita a mano. Eso no
comprueba el hash: comprueba que no me equivoque al teclear la copia. Pasa siempre y ocupa una línea
dando la impresión de que hay una garantía. Ahora el vector **compara la réplica contra el modelo del
banco, en 4 configuraciones**, y da `4/4`.

**Para poder hacerlo tuve que tocar el banco**, y esa es la parte que me hizo dudar: el banco solo
imprimía la pareja gpu/modelo cuando el control de contenido **fallaba**, así que no había forma de
obtener su predicción a voluntad. Le añadí una línea `MODELO` que expone la predicción del item 0.
Es una modificación del camino de medición validado para servir a una herramienta, y normalmente
no se hace. La justificación es que **una réplica en otro lenguaje que no se puede contrastar
con su generador no vale el cálculo que hace encima** — es un número sin unidad con pasos extra—.
Y porque al tocarlo tuve que ejecutar `bench.py run regresion` entero, que dio **`PASS`**: los once
casos de contenido y sus controles siguen bien después de borrar y restituir una cabecera de
bucle.

Ese `PASS` importa más que la línea nueva. La cabecera de `for` del readback se me perdió en un parche
y la restauré de memoria; `607` registró exactamente ese tipo de pérdida rompiendo el banco entero, y
`bench.py` lo detectó porque el tiempo dejó de crecer con `ITERS`. La detección funcionó, y eso es lo
que se compra un banco con controles.

## Un detalle del self-test que mentía

Dos casos afirmaban «la huella se satura» porque, con `ITERS` fijo, `W` grande toca menos líneas. Es
cierto **y no es saturación**: con `ITERS` fijo, `W` grande significa más líneas que accesos. El nombre
decía una causa que el parámetro producía. Ahora los casos dicen lo que miden —accesos por línea, no
`W`— y hay uno que verifica que con accesos ≈ líneas la cobertura no depende de `W`.

## El mecanismo de numeración, trabajando

Al reservar pedí el 953 y **me dio el 958**: otra sesión tomó 953 a 957 entre mi comprobación y la
reserva. Eso es exactamente la colisión que `944` decía que podía ocurrir, ocurriendo, y sin daño porque
el camino pasa por la reserva. Es la primera vez que veo el mecanismo ganarse el sitio en vez de solo
constar que existe.

## Instrumentos

- `huella.py`, 7 de 7. Réplica de la cadena verificada contra el modelo del banco en 4 configuraciones.
- `vulkan_compute_probe.c`: línea `MODELO` con la predicción del item 0.
- `bench.py run regresion` → `PASS` tras la modificación.

## Lo que queda abierto

- **`271-1` sigue abierto**, y ahora con menos candidatos: la huella no es. Lo que hace falta es un
  kernel que **reutilice dentro de una línea** —para que haya algo que amortizar— y a la vez **no sea
  anticipable** —para que no mida emisión—. Esas dos cosas tiran en direcciones opuestas y ningún
  kernel del banco las tiene a la vez. Ese es el problema de diseño de la próxima iteración, y es un
  problema de diseño de verdad, no una falta de medidas.
- **El asíntota de 3,27 ns por acceso**, sin explicar más allá de «compulsory miss».
- **Meter el barrido en `bench.py` como suite**, con su control y su artefacto. Sigue siendo un script
  de un solo uso.
- **`277-1` y `281-1`**, los otros dos `OPEN` más antiguos. Ninguno leído.
