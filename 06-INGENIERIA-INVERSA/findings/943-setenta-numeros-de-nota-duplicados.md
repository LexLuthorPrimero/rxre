# 943 — 70 números de nota están duplicados: 3840 citas del corpus no se pueden resolver

Estado: `PROVEN`. Instrumento: `fronteras.py --citas`, 15 de 15.
Alcance: `06-INGENIERIA-INVERSA/findings/`, 447 notas.
AUTORIA=AGENTE-SMU

## Qué se encontró

`942` construyó `fronteras.py` para encontrar fronteras rancias, y al construirlo salió otra cosa.
El instrumento ordena las notas por número de fichero para establecer la cronología de cada frente.
Al ordenar, apareció que **el número no identifica una nota**.

```
70 numeros con mas de una nota, en 167 de las 447 notas del directorio.
```

No son sufijos de versión ni notas de revisión del mismo contenido. Son **notas distintas que
recibieron el mismo número**:

```
258-veinticuatro-gbs-de-vram-contra-dos-gbs-de-pcie.md
258-verificar-el-target-coincide-en-diez-campos-y-la-amd-no-es-card0.md
```

El techo de VRAM contra el techo de PCIe, y la verificación de que el target coincide en diez campos.
Nada que ver. Y `258` está citado **106 veces desde otras notas**.

## La magnitud

```
108   citada 413 veces      hay 2 notas
100   citada 264 veces      hay 3 notas
121   citada 110 veces      hay 3 notas
 99   citada 108 veces      hay 3 notas
258   citada 106 veces      hay 2 notas
130   citada 106 veces      hay 3 notas
 23   citada  99 veces      hay 2 notas
115   citada  98 veces      hay 2 notas
...
3 840 citas en total, en 70 numeros distintos.
```

Y un punto donde el daño es concreto: **`258` es el techo de PCIe de Gen2 x4**, el número contra el que
este proyecto ha medido durante meses. Yo lo he citado en notas de esta sesión como si fuera una sola
nota. La cita funciona por costumbre —el contexto desambigua— y no porque el número resuelva.

**Un número que no resuelve no es una cita, es una suposición con formato.**

## Dónde muerde de verdad

Siete de las dieciocho fronteras abiertas tienen su nota base en un número colisionado: `246-1`,
`258-1`, `258-2`, `258-4`, `261-1`, `262-1`, `262-2`. Para esas, la cronología que construye
`fronteras.py` **no sabe en qué orden ocurrieron dos notas con el mismo número**. El instrumento
ordena por número y, a igualdad, por orden de directorio, que es arbitrario.

Eso no ha producido un veredicto falso aquí —la única rancia que encontró era de `282-2`, cuyo número
no está colisionado— pero es un límite real del instrumento y está anotado como tal en su cabecera.

## Por qué ha pasado

Dos veces este directorio ha tenido que renumerar por colisión, y las dos se han arreglado en el acto.
Lo que no se ha hecho nunca es **auditar si quedan colisiones**, y con 447 notas ya las hay. La
numeración manual no escala: 447 notas escritas a lo largo del tiempo por varios frentes, con el
siguiente libre calculado a ojo cada vez.

Es la misma clase de fallo que las fronteras rancias de `942`: **un identificador que se mantiene a
mano y que nadie comprueba**. El identificador de las notas es el número; el de los frentes es el
string `NNN-M`; los dos se propagan y ninguno se audita.

## El arreglo

Para lo que está escrito: **cuando el número esté colisionado, citar el principio del nombre del
fichero en vez del número.**

```
mal     el techo de PCIe de `258`
bien    el techo de PCIe de `258-veinticuatro-gbs`
mal     corroborada por `100`
bien    corroborada por `100-el-limite-de-la-sram`
```

Un prefijo corto basta; no hace falta el nombre entero, y se puede leer igual de rápido.

Para lo que viene: el número tiene que dejar de asignarse a ojo. `fronteras.py --citas` ya devuelve
`1` cuando hay colisiones, así que puede meterse en un preflight como el control de frescura del
binario: es exactamente el mismo tipo de puerta.

## Lo que NO se ha hecho

- **Renumerar las 167 notas afectadas.** Renumerar en un árbol con 3840 citas entrantes rompe las
  citas, y arreglar eso exige tocar casi todo. Es un trabajo grande, y hacerlo sin un mapa de citas
  completo sería peor que la ambigüedad. No se ha empezado.
- **Decidir qué nota se queda con cada número.** No es una decisión que se pueda tomar por mayoría de
  citas: las dos notas con `258` son ambas legítimas.
- **Convertir `258` en algo no numérico.** Es la solución real —un identificador que no pueda colisionar
  se resuelve con un hash o con la fecha—, y es un cambio incompatible con 3840 citas. Deuda, no
  arreglo.

## Instrumentos

`08-ARQUITECTURA/tools/fronteras.py`, 15 de 15. Modo `--citas`: devuelve `1` si hay citas ambiguas,
así que sirve como preflight.

Tres vectores del self-test nuevos, y uno de ellos es el más importante: **`258` está colisionado**, y
el self-test lo Comprueba por número y por recuento. Un control sobre una propiedad que se acaba de
descubrir rotten tiene que estar en el self-test desde el primer día, o se olvida.

## Nota sobre la numeración de esta sesión

Al escribir `942` hubo una colisión en vivo: otra sesión escribió `941` mientras yo escribía la mía.
Renumeré a `942`, y al hacerlo encontré la de `941`. Es la tercera vez, y la primera que se detecta
sistemáticamente en lugar de por casualidad.

**Consecuencia práctica:** las notas 938 a 943 las escribí yo y las comprobé una a una; las de otros
frentes las he leído puntualmente. Si dos sesiones escriben a la vez, la numeración necesita un
lock, y no lo tiene.

## Lo que queda abierto

- **Un lock por número de nota**, como el que ya existe por scope de escritura. `.write-lock/nota-NNN`.
  Es el arreglo de la causa, no del síntoma, y es barato.
- **`fronteras.py` puede leer el bloque multilínea** y recuperar las 4 declaraciones con `ESTADO=` en la
  línea siguiente, que hoy quedan fuera del control.
- **Reauditar los siete frentes con base colisionada** cuando la cronología se pueda ordenar sin
  ambigüedad.
- **Las 18 fronteras abiertas** que quedan, de las que ninguna está mirada en esta vuelta salvo `282-1`.
