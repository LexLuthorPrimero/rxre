# 966 — El control que la suite declara no tener: contraste del emisor PTEPDE contra el ASIC que corre

Estado: `VALIDADO`. `emisor.py` 16 de 16; los dos controles negativos verificados sobre el fichero real.
Instrumentos: `emisor.py` (nuevo), `07-DRIVER/tests/Makefile` (`run`, `emisor`, `verify`).
Alcance: `08-ARQUITECTURA/tools/emisor.py`, `07-DRIVER/kernel/rx550_pm4.h:266`.

## Lo que había, y por qué esto no era escribir código nuevo

Leí la documentación antes de tocar nada, y `docs/IMPLEMENTATION-STATUS.md` cierra su sección 8 con
una frase que cambia el encargo:

```
ESCRITO    mucho, y bien estructurado
COMPILA    sí, los cuatro .ko y las tres suites
VALIDADO   el análisis estático, con contrapruebas
LA GPU     INTACTA

Lo que falta para que el driver propio toque hardware son dos cosas, y ninguna es
técnica: una ruta de recuperación independiente demostrada (hoy PARTIAL) y una
autorización explícita. Todo lo demás ya está escrito.
```

Verificado antes decreerlo: los dos `.ko` compilan, `check-drivers` pasa sus comprobaciones por `nm`,
`test_pm4` da **208 checks, 0 fallos**. No hay un subsistema que escribir. Lo que hay son **huecos de
verificación**, y el más grande lo declara la propia suite en su salida.

## El hueco, textual

`test_pm4.c` cierra en verde y dice exactamente qué no cubre:

```
NOT covered, and not claimed:
- the provenance of the PTEPDE expectations is weaker than the PACKET3 ones. Those
  five headers were counted inside amdgpu.ko; PTEPDE cannot be, because a PTEPDE packet
  contains no PACKET3 header to count. Its expected values are transcribed from
  sdma_v4_0.c. A matching misreading in the encoder and in this test would pass.
```

**Una circularidad declarada.** El codificador se escribió leyendo amdgpu y las expectativas del test
se transcribieron del **mismo** amdgpu, así que un error de lectura replicado en los dos sitios pasa
las comprobaciones.

Y no es teórico: el dword 9 estuvo mal dos veces, en la dirección peligrosa.

| hallazgo | qué leyó | qué escribió | |
|---|---|---|---|
| `023` | `sdma_v3_0.c` | `count` | correcto |
| `036` | `sdma_v4_0.c` | `count - 1` | **incorrecto** |
| `038` | volvió a `sdma_v3_0.c` | `count` | correcto |

El «cross-check» que justificó el cambio decía que *los otros dos productores de este ASIC
coinciden*, y estaba leyendo `sdma_v4_0.c`. **Una comprobación hecha sobre una sola fuente no es una
comprobación cruzada**, y citar dos líneas del mismo fichero como si fueran dos fuentes es
exactamente la forma que me engañó.

## Lo construido: `emisor.py`

Compara nuestro emisor contra el del driver de referencia **dword a dword y por rol, no por texto**,
porque las dos fuentes escriben lo mismo con sintaxis distinta:

```
referencia   ib->ptr[ib->length_dw++] = lower_32_bits(pe);
nuestro      ib->buf[ib->length_dw++] = (__u32)(pe & 0xFFFFFFFFu);
```

Esas dos son la misma operación, y compararlas por texto daría un falso positivo. Y estas dos no lo son:

```
count        -> el campo es un número de entradas
count - 1    -> el campo es un número de entradas menos uno
```

Un rol no reconocido no se da por bueno: sale `DESCONOCIDO` y la herramienta sale distinta. Un
validador que solo sabe decir «iguales» no es un validador.

Resultado sobre el árbol real:

```
dw0  OK  HEADER:GEN_PTEPDE     dw5  OK  LO32(addr)
dw1  OK  LO32(pe)              dw6  OK  HI32(addr)
dw2  OK  HI32(pe)              dw7  OK  INCR
dw3  OK  LO32(flags)           dw8  OK  CERO
dw4  OK  HI32(flags)          dw9  OK  COUNT        <-- el que estuvo mal dos veces

RX550_SDMA_PTEPDE_DW = 10   el emisor de referencia emite 10   OK
RESULT: IDENTICOS
```

## Tres cosas que solo se ven haciendo el control

**1 · Elegir la fuente cambia el veredicto, y eso es lo que lo hace falsable.** El mismo código
nuestro es `IDENTICOS` contra `sdma_v3_0.c` y `DIVERGEN` contra `sdma_v4_0.c`, y solo en el dword 9.
Un comentario podía afirmar cualquiera de las dos cosas; una herramienta que puede correr contra las
dos no.

**2 · La cita de la constante apuntaba al ASIC equivocado.** `RX550_SDMA_PTEPDE_DW` valía 10 y se
justificaba con `sdma_v4_0.c:1649-1658`. El valor 10 es el mismo en los dos emisores, así que **el
número no falla; falla la fuente que lo justifica** — que es justo lo que hizo que el dword 9 fuera
del ASIC equivocado. Corregida a `sdma_v3_0.c:986-996`, y la herramienta ahora avisa si vuelve a
apuntar al que no corre.

**3 · El recuento de dwords no detecta un intercambio de campos.** Los dos emisores emiten 10, así que
el conteo pasa. Pero cambiar `LO32(flags)` por `LO32(addr)` conserva el tipo, el tamaño y el orden
longitudinal, y produce una page table silenciosamente mal. Mutado, el veredicto es `DIVERGEN` en el
dword 3.

## El fallo que casi se queda dentro

La primera versión de la herramienta **no cazaba el error para el que existía**. Al mutar el fuente
real a `count - 1` y ejecutar, salió `RESULT: IDENTICOS` y `exit=0`.

Causa: `main()` imprimía en la cabecera la ruta que recibía por `--nuestro` pero **leía la ruta fija**.
El `replace` que la cambió no casaba y no se comprobó. La cabecera decía «estoy leyendo la copia
mutada» mientras leía el original.

Es la regla del proyecto escrita en su forma más incómoda: **nunca dejar un comentario, ni una
cabecera, afirmando un control que el código no hace.** Aquí no era un comentario, era la línea que
dice qué fichero se está leyendo.

Y no lo veía el self-test, porque los casos llamaban a la librería directamente y no a `main()`.
**Un self-test que ejercita la librería no prueba el programa: prueba las funciones que el programa
llama, y el cableado entre ellas es justo donde estaba el fallo.** Por eso el caso `CN-7` ejecuta
`main()` de verdad contra un fichero mutado de verdad, y comprueba las tres cosas: que diverge, que
sale con 1 y que señala el dword.

## Un comentario mío que era falso, y cómo lo supe

Escribí en el código que *el orden de las pruebas importa*: si `count` se probara antes, el `- 1`
casaría con `COUNT` y la herramienta pasaría el error que existe para cazar.

**Es falso, y por dos motivos.** El patrón de `COUNT` lleva ancla `$`, así que `count - 1` no casa
con `count$` con ningún orden; y aun sin ancla, `COUNT_MENOS_UNO` va primero.

Lo comprobé rompiéndolo, que es la única forma de saber si un control controla algo:

| mutación | resultado |
|---|---|
| invertir el orden `count` / `count - 1` | 16 de 16 — **no se entera** |
| quitar el ancla `$` de `COUNT` | 16 de 16 — **no se entera** |
| quitar **las dos** | **12 de 16**, y `CN-7` reporta `rc=0` |

Son dos defensas independientes y cada una basta sola. Se conservan las dos porque son baratas, y el
comentario va así porque afirmar que el orden importa cuando no importa es un control que no existe
escrito como si existiera.

## Dos huecos baratos que salieron de leer

**`make run` declaraba cinco tests y ejecutaba tres.** `test_mmio` y `test_mc` se compilaban en cada
`make all` y no los ejecutaba nadie nunca. Compilar un test no es correrlo, y un test que se compila
sin ejecutarse no puede fallar: es el peor sitio donde puede esconderse un fallo, porque no hay nadie
mirando. Los dos pasaban —27 y 23 checks— así que no había daño acumulado, pero lo había. El target
`run` ahora recorre `$(TESTS)` y **propaga el fallo**: comprobado con un test que sale con 9, da
`ALGO FALLO` y `make` sale distinto de cero.

**`emisor` no va dentro de `run`.** Lee el corpus, así que su respuesta depende de amdgpu y no solo de
nuestro código: mezclarlo haría que una mudanza del corpus pareciera un fallo del driver. Vive en su
propio target, y `verify` corre los dos.

```
$ make -C 07-DRIVER/tests verify
  los 5 tests ... han pasado
  RESULT: IDENTICOS
  verificado: 5 tests de userspace + contraste del emisor
```

## Lo que NO hace, y son las tres limitaciones

1. **No dice que el silicio lea el campo como el driver lo escribe.** Dice que nuestro emisor hace lo
   que el de referencia, y para esta pieza lo mejor disponible es eso. `PROVEN_DERIVED`, no `PROVEN`.
   El agreement test de la línea B es el que atrapa el otro lado, y necesita GPU.
2. **No compila ni ejecuta hardware.** Es estática. El CRC de la decompilación de `04-IMPLEMENTACION`
   ya no es reproducible hoy porque `/lib/modules/.../build` no tiene `scripts/`; queda pendiente.
3. **Solo conoce las formas que puede reducir a rol.** Un emisor nuevo con otra forma sale
   `DESCONOCIDO`, que es el fallo correcto.

## Instrumentos

- `emisor.py` — `--self` 16 de 16, con `CN-7` end-to-end. Cero intrusiones CJK.
- `07-DRIVER/tests/Makefile` — `run` sobre `$(TESTS)` con propagación de fallo, `emisor`, `verify`.
- `07-DRIVER/kernel/rx550_pm4.h:266` — cita corregida y con el porqué escrito al lado.
- Los dos `.ko` siguen compilando y `check-drivers` sigue en verde tras tocar el header.

## Lo que queda abierto, y es lo que sigue bloqueado

- **`docs/IMPLEMENTATION-STATUS.md` §2.1** describe el error `count - 1` como vivo, con un
  `CORRECTED 2026-10-02` que lo corrige en medio del párrafo. Ese documento se lee rápido y se lee
  mal: mezcla el estado viejo con la corrección. Y ese mismo fallo de estado ya está registrado como
  `LIMITACIÓN #3` en `docs/IMPLEMENTATION-STATUS.md:248` — el test de la línea B devuelve `rc=0`
  aunque imprima `[FAIL]` — y sigue `NO REVERIFICADO`.
- **Los binarios de la línea B sin versionar.** `COORDINACION.md:9-12` registra dos pérdidas
  reales por no haber mecanismo: la reversión completa de AD-12 y D13, y un fichero de 787 líneas
  sobrescrito por una reescritura que ni compilaba. El agreement test de 64 bloques sigue sin salida
  persistida, así que es el tercer candidato.
- **La ruta de recuperación sigue `PARTIAL`** (1 de 3 condiciones), y sin eso más autorización
  explícita, el resto del discriminante de runtime —N1, N2, N4, N6— no se abre.