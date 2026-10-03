# 964 — La puerta de reloj, para las seis suites: y dos fallos que solo aparecieron al correrlas

Estado: `PASS`. `bench.py` 33 de 33; 6 suites, todas con la puerta puesta y todas sin reventar.
Alcance: `08-ARQUITECTURA/tools/bench.py`, `escribir()`, `main()`, `veredicto()`.
AUTORIA=AGENTE-SMU

## Lo que había

`959` puso una puerta de reloj **dentro de la suite `jerarquia`**: si el reloj de la GPU varió más de
un 25 % a lo largo del barrido, el dato no vale. Funcionó, y por eso existe. Pero las otras cinco
suites miden tiempos con el mismo defecto y no la tenían.

Eso es un fallo de clase: no es que una suite esté mal, es que **cinco están igual de mal y solo una
lo sabía**.

## Por qué la puerta vive en `main()` y no en cada suite

La tentación era copiar el bloque a las seis. Habría sido un error por dos razones que se vieron:

1. **Las cinco primeras no habrían aparecido.** Solo la sexta dio el fallo, así que cinco copias
   idénticas habrían conviven con cinco que nunca se ejecutan nunca.
2. **Las seis suites no devuelven la misma cosa.** Dos devuelven una **lista** y cuatro un **dict**, y
   eso no lo supe hasta que las corrí.

Con un solo punto de inyección, `main()`, añadir una suite nueva la trae con la puerta puesta sin que
nadie tenga que acordarse. Y una comprobación que hay que acordarse de poner no se pone.

## Fallo 1 · la puerta asumía una forma de retorno que nunca comprobé

La primera versión escribía el corte **dentro del resultado** de la suite:

```python
resultado["puerta_de_reloj"] = bloque
resultado["veredicto"] = "INVALID"
```

Con `regresion` y `rejilla` eso no da un error de lógica: da

```
regresion   ValueError: dictionary update sequence element #0 has length 5; 2 is required
rejilla     TypeError: list indices must be integers or slices, not str
```

**Y el self-test no lo vio**, porque sus cuatro casos usaban dicts. Un self-test que construye el
caso con la misma forma que el código que quiere comprobar está probando su propia suposición, no el
código.

Eso dijo ademas algo más importante que el fallo: **la puerta estaba en la capa equivocada**. El reloj
no cambió porque la suite lo decidiera; cambió mientras la suite corría. La puerta es una condición de
la **corrida**, no de la suite.

Puesta en su sitio, desaparece la necesidad de hacer trampas. Ya no hay que `clear()` y reordenar
claves para que el corte no se pierda al final del dict: el bloque se devuelve, `escribir()` lo guarda
como **clave de primer nivel** del artefacto, y `main()` lo cuenta como un fallo más.

```python
v, malos = veredicto(resultado)
if puerta and puerta.get("estado") == "INVALIDA_POR_RELOJ":
    v = "INVALID"
    malos = malos + ["puerta_de_reloj=INVALIDA_POR_RELOJ"]
```

La suite no se entera y su forma de retorno deja de importar. Dos suites devuelven lista, cuatro
devuelven dict, y la puerta funciona igual en las seis.

## Fallo 2 · la puerta podía pisarse desde dentro

Con el corte dentro del resultado hubo que hacer `clear()`, `update()` y reordenar claves, porque el
`update()` del contenido de la suite **pisaba** el `veredicto=INVALID` de la puerta. El orden lo
arreglaba, pero que el arreglo sea el orden significa que cualquier cambio posterior lo rompe sin
avisar.

Eso ya no existe con la puerta en la capa de arriba. Aun así, en el camino nuevo me dejé un comentario
que afirmaba algo que el código no hacía:

> «El corte va al principio del resultado»

Asignar una clave nueva a un dict la deja **al final**. El comentario afirmaba un efecto que el código
no tenía, y abrir el artefacto para ver si el corte venía de ahí obligaba a llegar hasta el fondo.

Hay dos formas de arreglar eso: decirlo bien, o que sea verdad. Preferí que sea verdad:

```python
resultado["puerta_de_reloj"] = bloque   # la puerta, la PRIMERA clave
resultado.update(resultado_guardado)    # el contenido de la suite, detrás
resultado["veredicto"] = "INVALID"      # y el veredicto al final, GANANDO
```

## La puerta dispara, y eso es lo que la valida

En la primera corrida de las seis, `jerarquia` dio:

```
RELOJ VARIABLE en la corrida: 2.39x (448..1068 MHz) en 8 lecturas -> dato INVALIDO
```

**Es la primera vez que la puerta captura una corrida real.** No un caso sintético del self-test: una
corrida de verdad en la que la GPU bajó a 448 MHz a mitad del barrido. Las seis:

```
regresion     PASS    reloj estable  1.00x (1068..1071 MHz)   3 lecturas
curva         PASS    reloj estable  1.00x (1071..1071 MHz)   2 lecturas
coalescencia  PASS    reloj estable  1.02x (1051..1071 MHz)   3 lecturas
rejilla       INVALID  reloj estable  1.00x (1068..1071 MHz)  11 lecturas
textura       INVALID  reloj estable  1.01x (1050..1062 MHz)   2 lecturas
jerarquia     PASS    reloj estable  1.02x (1052..1071 MHz)   8 lecturas
```

`jerarquia` da `PASS` en esta corrida y `INVALID` en la anterior, con la misma suite y el mismo reloj
casi siempre estable. **La diferencia entre las dos corridas es el reloj, y ahora eso se dice en el
artefacto en vez de quedar en un `print` que nadie guarda.**

## Un caso del self-test que no comprobaba nada

Uno de los seis casos nuevos tenía un `or True` al final y el comentario confessando que no
comprobaba nada. Lo encontré porque el resultado del `print` era sospechoso: un caso que siempre pasa
no es un caso, es decorado.

El arreglo fue hacer que el código guarde el bloque **también cuando el reloj está estable**, porque
decir «el reloj estuvo estable» es un dato y un dato que solo se imprimía en consola se pierde en
cuanto alguien mira el artefacto. Ahora:

```python
casos.append(("puerta: con reloj estable NO toca la suite", ...))
casos.append(("puerta: el estado del reloj se guarda aun sin cortar", ...))
casos.append(("puerta: el bloque guardado no inventa veredicto", ...))
```

Tres casos donde antes había uno decorado, y los tres miran algo distinto.

## Y dos expectativas mías que el código corrigió

- **`razon == 1.0` para un reloj «estable».** No: mi lista estable era 1071/1058/1066 MHz, y la razón
  es 1,0123. «Estable» quiere decir *bajo el umbral*, no *constante*. El que estaba equivocado era el
  caso, y ahora comprueba `1.0 < razon < 1.05` **y** que está bajo el umbral.
- **`PLANA` en el veredicto de curva**, ya en `959`. Con dispersión del 26 % una secante de 1,00 está
  por definición dentro del ruido y la respuesta honesta es `NO_RESUELTA`.

Las dos veces la respuesta del código fue la correcta y mi expectativa la que no. Un self-test que se
escribe con la respuesta que unoWXactly espera no está probando el código: está probando la memoria de
quien lo escribio.

## Qué NO hace esta puerta

- **No mide magnitudes, las invalida.** Una corrida a 448 MHz mide bien lo que la GPU hizo a 448 MHz. Lo
  que no vale es mezclarla con la de 1071 MHz, y de eso se ocupa `comparar_con_previo()`, que es un hueco
  distinto.
- **No corrige el reloj.** No hay forma de fijarlo sin `root`; lo que hay es negarse a afirmar una
  magnitud con la condición cambiante. Es el mismo limite que ya sabe `938`.
- **El umbral del 25 % sigue sin justificarse.** Con las razones observadas (1,00 a 2,39 dentro de
  corridas, 0,29 a 3,41 entre corridas) cualquier umbral entre el 5 % y el 20 % daría la misma
  respuesta. Puesto como constante con nombre, y visible en el bloque, pero sigue siendo un número mío.

## Instrumentos

- `bench.py`: `mirar_reloj()`, `cerrar_puerta_de_reloj()`, `PUERTA_RELOJ_RAZON`, `RELOJES`; seis puntos
  de medición con lectura; bloque de puerta en el artefacto; 7 casos de self-test. **33 de 33.**
- Las seis suites, sin cambios de comportamiento: la puerta solo invalida, nunca mide.

## Lo que queda abierto

- **La puerta solo mide el reloj, no la potencia ni la temperatura.** Un barrido que pasa de 40 °C a
  75 °C tiene el reloj estable y una magnitud que no es comparable consigo misma. Es el mismo patrón de
  fallo con otra variable, y la respuesta es la misma: leerla por punto y aplicar el mismo umbral.
  **No está hecho**, y es el siguiente hueco del mismo tipo.
- **El asíntota de 5 a 7 ns por acceso dependiente.** Magnitud ya estable, forma ya resuelta; la causa,
  no.
- **`277-1` y `281-1`**, los dos `OPEN` más antiguos. Ninguno leído.