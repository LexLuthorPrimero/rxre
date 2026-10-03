# 938 — El techo de envío son ~38 µs, y por debajo de 60 µs de trabajo el banco está enviado-limitado. Pero la magnitud de GPU tardó tres pasos en ser publicable

Estado: `PROVEN` para el techo de envío y el punto de cruce. Corrige la magnitud de GPU de `934`.
Alcance: la RX 550 de esta placa, Polaris12/GFX8.1, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU
Instrumentos: `bench.py` 15 de 15, banco con marcas de tiempo por medición.

## La pregunta

`934` dejó sobre la mesa un número: 72 µs de host contra 36,5 µs de GPU. Es decir, **la mitad del
tiempo que el banco llevaba meses reportando no era trabajo de la GPU**. Eso no es una precisión: es
una afirmación sobre dónde está el límite, y para `§H` y `§57` el límite es exactamente la pregunta.

Con el modelo `host = c + b · gpu` sobre once puntos y el control de contenido activo en cada uno:

```
host = 38,06 us  +  1,0479 * gpu        R2 = 0,99936
```

Un término fijo de **38 µs** y una pendiente de 1,05. La pendiente no es exactamente 1 porque el
corchete de marcas no cubre todo el lado GPU: deja fuera el vaciado de la cola.

## El punto de cruce

La fracción `gpu/host` sobre el tamaño del trabajo:

| items | bytes | host | gpu | gpu/host |
|---|---|---|---|---|
| 1 024 | 0,03 MiB | 60 µs | 17,3 µs | **0,288** |
| 4 096 | 0,13 MiB | 78 µs | 24,6 µs | 0,316 |
| 16 384 | 0,52 MiB | 88 µs | 52,0 µs | 0,591 |
| 65 536 | 2,10 MiB | 303 µs | 223,2 µs | 0,737 |
| 262 144 | 8,39 MiB | 2 581 µs | 2 469 µs | **0,957** |

Monótona, de 0,29 a 0,96. Y tiene la forma que debe tener: **la fracción sube porque el envío es un
coste fijo**, y un coste fijo se amortiza.

**El envío es la mitad del tiempo en torno a 61 µs de trabajo de GPU.** Por debajo de ahí el banco
está enviado-limitado; por encima, GPU-limitado. Ése es el discriminante que `§H` necesita y que
antes no existía: no era un número de tiempo, era una **pregunta** que el banco no podía responder.

Consecuencia práctica para un driver propio, y es la razón de haberlo medido. La pregunta que
abre es: **por debajo de ~60 µs de trabajo, el banco se gana algo agrupando despachos?**
En `bench.py` se añadió `--batch=M` para comprobarlo, y la primera pasada dio un 87,8% de menos
tiempo por despacho al agrupar 64. Pero la medición iba acompañada de un aumento de ocupación,
y no se puede separar así. Queda registrado como `NOT_DETERMINED` con la causa, no como
resultado.

## La magnitud de GPU: tres pasos hasta ser publicable

Esto es lo que ocupó la iteración, y es el caso de un instrumento que produce un número
plausible y falso tres veces seguidas antes de ser correcto.

### Paso 1: la línea `GPU` no describía las mediciones

`934` añadió un pool de marcas y lo leía **una vez, después de la calibración**. Pero el bucle de
medición reenvía el command buffer `--rep` veces, y el pool se resetea en cada reenvío. La línea
`GPU` era el intervalo de la calibración; las mediciones no tenían marca.

Peor: `bench.py` leía esa línea y la guardaba junto a **la mediana de host de las repeticiones**. Dos
números que no describen el mismo trabajo.

### Paso 2: el síntoma era físicamente imposible, y por eso se detectó

El resultado de esa mezcla era `gpu/host = 2,5`. La GPU no puede tardar más que la espera del host.
Un número imposible es un dato gratis: no hace falta saber qué pasa, solo que no puede pasar. Eso
detectó el fallo en un paso, cuando la discoloración de las cifras —que era lo que yo buscaba— no
decía nada.

### Paso 3: el arreglo, y un control para que no vuelva

La marca se lee ahora **dentro del bucle**, en la misma línea que el tiempo:

```
TIEMPO    0.002611 s  gpu=2.470880 ms
```

Y `bench.py` tiene un control de física antes de publicar la magnitud:

```python
ok_g = [x for x in gpus if x is not None and 0.0 < x < med * 1e3]
```

Si **ninguna** marca cumple `0 < gpu < host`, la magnitud **no se publica como número**: se publica
como incidente, y el veredicto de esa fila pasa a `INVALID`. Un instrumento que puede publicar un número que sabe imposible es un instrumento que tarde o
temprano lo publica.

## Instrumentos

- `vulkan_compute_probe.c`: la marca va en la línea de su propia medición. Sin ese cambio, todo lo
  demás de esta nota no es reproducible.
- `bench.py`: emparejamiento por línea, control de física, 15 de 15.
- `--batch=M` en el banco: existe, y su resultado está sin interpretar.

## Errores propios

Cuatro, y los cuatro son de la misma clase: **un indicador que no distingue lo que tiene que
distinguir, varias veces seguidas.**

1. **Leí la marca de la calibración como si fuera la de las mediciones.** No era un error de
   código sutil: era que el pool se resetaba en cada reenvío y yo no lo pensé.
2. **Comparé esa marca con la mediana de host de las repeticiones.** El mismo defecto de no mirar de
   qué trabajo habla cada número.
3. **Lo llamé «GPU/host = 2,5» sin mirar que es imposible.** Un número que viola la física es una
   alarma gratis, y yo la traté como un resultado raro.
4. **En el barrido anterior colgué un `exit=2` del banco como «control falla».** El banco había
   rechazado el invariante `wsize >= items` por stderr y mi expresión regular no lo vio. Clasificar
   un aborto como un fallo de control es como se confunde «no se pudo» con «dio mal».

## Lo que queda abierto

- **`--batch=M` sin responder.** El resultado bruto es 87,8% menos tiempo por despacho al agrupar
  64, pero el trabajo de GPU también sube, así que la ganancia es de envío y de ocupación mezcladas.
  El experimento controlado es `items × M` constante; la primera versión lo intentó y chocó con el
  invariante `wsize >= items`, que obliga a `items ≤ wsize` y por tanto acota `M` desde abajo. Con
  `wsize` de 1 MiB se resuelve, y no se ha hecho.
- **La magnitud de GPU como la buena para `§H`**: en la primera comparación de `934` las dos ramas
  estaban a 0,9% en GPU y a 26% en host, lo que sugería que GPU separa mejor. Ese 0,9% venía del
  emparejamiento roto de este nota, así que **esa afirmación queda anulada** y hay que rehacerla con
  la magnitud ya corregida.
- **`282-1`** y **`--mem=2`**: sin cambios, siguen como estaban.
- ~~**`282-2`**~~ **RANCIOSO**: cerrado en `283`. Lo detecté con `fronteras.py` en la misma
  vuelta en que lo escribí rancio, que es la mejor forma posible de que un linter exista.
