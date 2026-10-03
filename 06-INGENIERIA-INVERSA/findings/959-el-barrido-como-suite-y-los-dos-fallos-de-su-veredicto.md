# 959 — El barrido de jerarquía, como suite: y los dos fallos que encontró en su propio veredicto
AUTORIA=AGENTE-SMU

Estado: `PASS`. La forma de la curva es `BAIDA`, sobre un artefacto reproducible.
Instrumentos: `bench.py` con la suite `jerarquia`, 15 de 15 en el resto; `huella.py` 7 de 7.

## Por qué esto era una suite y no un script

`952` y `958` son dos notas escritas a mano sobre el mismo barrido. Un hallazgo que no está en un
artefacto con procedencia no se puede repetir, y repetirlo es lo que haría falta para confirmar el
asíntota que sigue sin explicar. La suite lleva las tres piezas en un mismo fichero, porque por
separado no dicen nada:

- **host y gpu**, emparejadas por línea desde `938`;
- **ns por acceso**, que es ritmo agregado e incluye el lanzamiento;
- **huella**, que es aritmética sobre la réplica de la cadena y dice si el barrido barre de verdad.

## El primer veredicto de la suite afirmaba un codo de caché

Salió `SUBIDA`, con lectura «es la firma de un codo de cache: al dejar de caber, cada acceso se va a
memoria». El dato del marginal era:

```
2,93   6,18   8,18   7,89   2,36   5,17   7,83
```

Eso **no es una serie, es ruido**: los dos últimos difieren un 50% siendo el mismo trabajo, y en el
régimen asíntotico el coste por acceso tiene que ser el mismo.

Y la prueba de que era ruido salió sin querer: **dos corridas de la misma regla dieron `SUBIDA` y
luego `BAIDA`.** Una regla que cambia de respuesta con los mismos datos no está midiendo una forma.

## Fallo 1 · el marginal es un estimador mal condicionado

`Δhost / Δaccesos` entre puntos cercanos resta dos números parecidos y divide por un número pequeño, de
modo que amplifica el error de cada punto. **Muestrear más no lo arregla, y se comprobó:**

| muestras | dispersión del marginal | efecto |
|---|---|---|
| n = 5 | 46 % | 22 % |
| n = 11 | 34 % | 9 % |

El efecto **bajaba** al muestrear más. Eso no es ruido de muestreo: es un estimador que no converge.

El estimador bien condicionado es la **secante de los dos extremos**:

```
secante = (host_final / host_inicial) / (accesos_final / accesos_inicial)
```

Usa todo el rango, así que los errores relativos no se amplifican, y no depende de cuántos puntos
intermedios haya: cambiar el rango de `W` no cambia la magnitud. Con estos datos da **0,129**, o sea
que el coste por acceso cae al 12,9 % de su valor inicial sobre un factor 1024 en `W`. Un efecto del
87 %, con una dispersión del 26 %.

## Fallo 2 · la forma se decidía con la magnitud equivocada

Con la secante ya calculada, la etiqueta de la forma seguía saliendo de las medianas de los margenes.
Resultado: **decía `SUBIDA` con una secante de 0,089**, es decir, un factor siete en la dirección
contraria.

Entre las dos versiones el dato no había cambiado. Lo que cambió fue que se leía bien. Y eso es
precisamente el riesgo de automatizar un juicio: **la suite publica con su artefacto, su
procedencia y su reloj, y un veredicto equivocado publicado así pesa más que un veredicto equivocado
dicho en una nota.**

## Fallo 3 · el reloj, que era el que de verdad invalidaba la magnitud

Una corrida reporta `sclk = 313620000 Hz` mientras las demás reportan `1071000000`. **Un barrido que
recorre el reloj de la GPU a lo largo del tiempo no puede distinguir «el conjunto de trabajo creció»
de «la GPU bajó de frecuencia».** La secante mezclaba las dos cosas sin avisar.

`bench.py` ya medía el reloj en `fingerprint()`; lo que faltaba era **usarlo como condición de
validez** y no solo como dato de contexto. La puerta compara el reloj de todos los puntos y corta si
varió más de un 25 %. Probada con los relojes de una corrida real: 1071, 1071, 1065, 313, 1071 →
razón 3,41 → dispararía.

Con la puerta activa y el reloj estable en la corrida final:

| W | sclk | host | ns/acceso | marginal |
|---|---|---|---|---|
| 64 KiB | 1063 MHz | 55 µs | 53,71 | — |
| 1 MiB | 1062 MHz | 161 µs | 9,83 | 7,00 |
| 8 MiB | 1071 MHz | 1 074 µs | 8,19 | 8,18 |
| 64 MiB | 1031 MHz | 7 279 µs | 6,94 | 8,82 |

```
secante = 0,129        el coste por acceso baja al 12,9 % en un factor 1024 en W
dispersión = 26 %       el efecto la supera con holgura
forma = BAIDA
cobertura de la huella = 0,637 constante
```

## Lo que el veredicto dice, y lo que no

**`BAIDA`, y eso descarta el codo de caché.** Un codo sube: al dejar de caber el conjunto, cada acceso
se va a memoria y cuesta más. Una caída del 87 % no es un codo, y `958` ya había dejado sin fuerza la
explicación alternativa —la huella no se satura, la cobertura es 0,637 constante—.

**Y la caída tiene un nombre medido por otra vía.** `938` medió 38,06 µs de coste fijo por envío, sin
usar esta suite. Los puntos pequeños están dominados por arranque en frío y por ese lanzamiento
amortizado sobre pocos accesos; el asíntota es el coste de un acceso compulsory. Dos instrumentos, dos
rutas, el mismo mecanismo.

Lo que **no** dice: el valor del asíntota, 5 a 7 ns por acceso dependiente, sigue sin explicar más
allá de «compulsory miss». Un asíntota del que se sabe la magnitud y no la causa no es un hallazgo
cerrado.

## Un rasgo del diseño que me salió bien

El veredicto tiene **tres salidas alcanzables**, y la tercera es la que importa: `NO_RESUELTA`,
cuando el efecto no supera la dispersión del propio estimador. No es un fallo del dato: es una
afirmación sobre el dato.

Y hay una más, `INVALIDA_POR_RELOJ`, que no es «no se puede saber la forma» sino «el dato no vale».
No son lo mismo entre sí, ni son lo mismo que el caso de `952`. Una es «el dato no resuelve la
pregunta»; la otra es «el dato no vale»; y lo de `952` era «el dato resuelve otra cosa». Se
distinguen por la acción que implican, y por eso necesitan nombres distintos.

**Hay una cuarta rama, `PLANA`, y es prácticamente inalcanzable.** Con la puerta de resolución
puesta, una secante lo bastante cerca de 1 para llamarla plana está *por definición* dentro de la
dispersión, y entonces cae en `NO_RESUELTA`. Se conserva por si con muchas muestras y un estimador
bien condicionado la dispersión llegara a cero, pero no cuenta como una salida real.

Eso lo comprobé ejercitando la lógica con cinco casos sintéticos, y **el quinto me dio la razón a
mí y no al código**: esperaba `PLANA` para una secante de 1,00 con dispersión del 26 %, y la
respuesta correcta es `NO_RESUELTA`. Mi expectativa estaba mal, y por eso el caso del self-test lleva
la respuesta que el código da y no la que yo suponía. Los cinco están ahora en el self-test.

## Instrumentos

- `bench.py`: suite `jerarquia`, con reloj por punto, secante, dispersión del estimador y puerta de
  reloj. 15 de 15 en el resto.
- `huella.py`: 7 de 7, réplica verificada contra el modelo del banco.

## Lo que queda abierto

- **El asíntota de 5 a 7 ns por acceso dependiente.** Con la magnitud estable y la forma resuelta, la
  pregunta es qué hace el hardware con una distancia de reutilización del orden del buffer. No lo sé.
- **Un kernel que reutilice dentro de la línea y a la vez no sea anticipable.** Las dos condiciones
  tiran en direcciones opuestas y ningún kernel del banco las tiene a la vez. Ese es el problema de
  diseño de verdad, y sigue sin resolver.
- **`277-1` y `281-1`**, los otros dos `OPEN` más antiguos. Ninguno leído en esta sesión.
- **Que `bench.py` use la puerta de reloj en las otras cinco suites.** Ahora solo `jerarquia` la tiene,
  y las demás miden magnitudes que dependen del reloj igual que ésta.
