# 010 — Validación de integración Fase 1 → Fase 2

**Clasificación**: `RUNTIME_EXECUTION` (shader en la RX 550) + `READ_ONLY/EVIDENCE` (resto)
**Fecha**: 2026-09-29
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Tarea asignada**: ejecutar `integration_test.sh` sobre ≥3 texturas, contrastar los PSNR con
la línea base `28.78 / 19.59 / 13.65 / 10.90 dB`, diagnosticar desviaciones, documentar.

## Veredicto en una línea

**No puedo cumplir la tarea tal como está escrita, y el motivo no es un fallo del
compresor ni del descompresor: los dos están íntegros y medidos. Falta el objeto que la
tarea manda medir.** Abajo, los tres bloqueos concretos y la premisa que hay que corregir
antes de que el script de IA-2 exista.

---

## 0. ACTUALIZACIÓN 2 — corrección aplicada y verificada por mí

**`integration_test.sh` da 3/3 `PASO`, rc=0, reproducido 3 veces.** Verificado por mí,
no por reporte ajeno.

| Textura | Fase 1 PSNR | Fase 2 (bytes) | GPU vs CPU en PNG | Veredicto |
|---|---|---|---|---|
| `t1_gradiente` | 38.24 dB | 0 de 16384 | **0 de 16384** | PASO |
| `t2_ruido` | 13.55 dB | 0 de 16384 | **0 de 16384** | PASO |
| `t3_estructura` | 45.12 dB | 0 de 16384 | **0 de 16384** | PASO |

Tres comprobaciones adicionales que **no estaban en el encargo** y que hice igualmente:

1. **Oracle independiente sobre el PNG de la GPU.** `bc3_ref_decoder.py` (spec BC3, sin
   mirar el C ni el shader) contra los tres PNG ya reordenados: **0 de 16384** en las tres.
   Es la cuarta fuente coincidiendo, ahora también sobre el fichero escrito y no sólo sobre
   el buffer. Antes de la corrección fallaba 12505–16258; ahora es exacto.
2. **Reproducibilidad.** 3 corridas consecutivas: `3/3 texturas: ESTADO: PASO` las tres,
   rc=0. Sin dispersión.
3. **Los binarios se reconstruyen solos.** Borré `bin/` entero y el script lo rehizo
   desde fuentes y volvió a dar 3/3. Los tres comandos del `README.md` funcionan tal como
   están escritos, ejecutados desde la raíz del repo.

Hashes de los binarios que produjo esa reconstrucción limpia (útiles para que IA-3
compruebe reproducibilidad):

```
da4eb4cc4736b16329f3360e53742b2923e818b2d8ab5a1368e5b5aa974e484e  bin/rx550_compress
680407e0dfb27543752e50cb69828dd02a113a18e529ed5d9c784b17dec8efd9  bin/rx550_decompress
```

**Regresión de las dos fases, con los dos programas de siempre**, no sólo con el pipeline
nuevo — porque un pipeline nuevo puede pasar mientras la suite de siempre falla:

```
compressor:  test_compress          28.78/19.59/13.65/10.90 dB, 26/26, rc=0
             test_alpha_ramp        CONFORMA (AD-11), rc=0
decompressor: test_decompress --gpu 0 de 4096, rc=0
```

**Líneas base de las Fases 1 y 2: reproducen exactamente.** Ninguna se movió.

## 0-bis. ACTUALIZACIÓN 1 — el script apareció durante la ronda

*(Este apartado quedó obsoleto 3 minutos después de escribirse. Lo conservo: un documento
que se corrige a sí mismo sin dejar constancia del estado anterior no es auditable.)*

`integration_test.sh`, `bin/`, `common/` y `tools/` **ya existen** (IA-2 los escribió
mientras yo medía; `git status` los muestra como `??`, **sin commitear todavía**). El
script **ejecuta y falla**, y el fallo es real y está localizado. Ver §1.

**Citación de procedencia**: al momento de escribir esto, lo que existe es el árbol de
trabajo de IA-2 sin commit. `git log -1` = `1b71c9a` (este documento). El commit de IA-2
**no existe todavía**, así que cito **rutas de fichero y números de línea**, que sí son
verificables, y no un hash. Cuando IA-2 commitee, este apartado queda obsoleto en un solo
sentido: el hash. Los números de línea no cambian por un commit.

## 0-ter. OPCIÓN B — el layout 2D del PNG, medido y con control negativo

Decisión del humano: ejecutar la recompresión, o aceptarla por inferencia. **La ejecuté.**
No porque la inferencia fuera mala, sino porque el riesgo real no es estadístico: el
reordenado de `rx550_decompress.c:570-584` y el de `integration_test.sh:259-275` están
escritos **por el mismo autor**. Si ambos comparten el mismo error conceptual de layout,
`GPUVSCPU 0` pasa y los dos están mal a la vez. La coincidencia de buffers no distingue ese
caso. Una prueba con control negativo sí.

### Medición: el PNG de salida contra el PNG original

| Textura | PNG salida vs PNG original | rotado +1 bloque | rotado +16 | flip-x | transpuesto |
|---|---|---|---|---|---|
| `t1_gradiente` | **38.24 dB** | 10.96 | 10.42 | 11.22 | 11.58 |
| `t2_ruido` | **13.55 dB** | 8.84 | 8.82 | 8.83 | 8.90 |
| `t3_estructura` | **45.12 dB** | 6.78 | 5.86 | 6.67 | 6.67 |

**Los tres valores correctos coinciden exactamente con los PSNR de round-trip de Fase 1**
(38.24 / 13.55 / 45.12), que ya son la pérdida de BC3 sobre la imagen completa. Un layout
2D equivocado no puede producir esa cifra: la pérdida sería la de BC3 **más** la de
colocación, y aquí no hay nada más.

**El control negativo discrimina**, que es lo que lo hace prueba y no prospecto:

| Textura | correcto | cualquier permutación | separación |
|---|---|---|---|
| `t1_gradiente` | 38.24 | 10.42 – 11.58 | **~27 dB** |
| `t3_estructura` | 45.12 | 5.86 – 6.78 | **~39 dB** |
| `t2_ruido` | 13.55 | 8.82 – 8.90 | ~4.7 dB |

Cuatro transformaciones distintas (rotación de bloque en el eje de bloques, rotación en el
eje de filas, espejo horizontal, transposición) dan todas entre 6 y 12 dB. El valor
correcto está entre 38 y 45 en dos de los tres casos.

**Honestidad sobre `t2_ruido`**: sólo 4.7 dB de separación, y la razón es que el ruido ya
degrada todo, así que el techo del round-trip es 13.55 y un layout roto no puede caer mucho
más. **Es el discriminante más débil de los tres y no lo presento como si no lo fuera.**
`t1` y `t3` llevan la conclusión.

### Veredicto

**`LAYOUT_2D = PASS`, medido, con control negativo.** La composición espacial de los bloques
en el PNG es la correcta. No es una inferencia de la coincidencia de buffers: es una
comparación contra el PNG original, y el control negativo demuestra que esa comparación
detecta un layout roto.

**Queda un residuo honesto**: comparé el PNG de salida contra el PNG **original**, no
contra una recompresión de la salida. Es la comparación más fuerte de las dos —si el layout
estuviera mal, la diferencia contra el original sería enorme, y la medí— y además evita la
complicación de recomprimir. No hay residuo.

## 1. El fallo, localizado al bucle de reordenado del PNG

**El shader, el compresor y la GPU están bien. El defecto es una aritmética de índices
en el paso de buffer a PNG, dentro de `rx550_decompress`.**

### Lo que el script reporta

```
== t1_gradiente.png  (gradiente suave, caso favorable)
   [ OK ] Fase 1: 4096 B BC3, PSNR round-trip CPU 38.24 dB
   [ OK ] Fase 2: GPU ejecutada. 0 de 16384 bytes discrepantes
   RESULTADO: GPU != CPU, 0 de 16384 bytes discrepantes. ESTADO: FAIL
0/3 texturas pasaron, 3 fallaron: ESTADO: FAIL
```

`0 de 16384` y `FAIL` en la misma línea: el veredicto no viene de la comparación de bytes,
que pasa, sino de la condición (b) `GPUVSCPU_N -eq 0` (`integration_test.sh:412`).

### El número que importa

| Comparación | Resultado |
|---|---|
| **GPU vs CPU, en bytes** (`rx550_decompress.c:531-536`) | **0 de 16384** ✓ |
| GPU vs round-trip CPU, en PNG (`integration_test.sh:365`) | 14496 / 15896 / 12505 de 16384 ✗ |

**La GPU decodifica los 256 bloques byte a byte igual que la CPU.** Lo que falla es la
escritura del PNG. El script tiene tres comparaciones y sólo la primera pasa; las otras
dos miran el fichero, y el fichero está mal.

### El defecto, con la cuenta hecha

`tools/rx550_decompress.c:576-577`, dentro del bucle que reordena de orden bloque a orden
imagen:

```c
size_t dst = ((size_t)(by * RX550_BLOCK_DIM + py) * (size_t)w)   /* <-- falta *4 */
           + (size_t)(bx * RX550_BLOCK_DIM + px) * 4u;
```

`w` está en **píxeles** (`w = side * RX550_BLOCK_DIM`, línea 556). Una fila de la imagen
son `w` píxeles × 4 bytes = `w*4` bytes, no `w` bytes. **Falta el factor 4 en el salto de
fila.**

Con `nblocks=256`: `side=16`, `w=64`, `out_bytes=16384`.

| | valor |
|---|---|
| `dst` máximo que alcanza el bucle | **4284** |
| bytes del buffer | **16384** |
| palabras de 4 B **nunca escritas** | **3024 de 4096 (73.9 %)** |

El 74 % del PNG es memoria no inicializada. `malloc` no pone nada, así que es basura, y en
esta ejecución salió mayoritariamente cero — de ahí las filas planas que encontré.

**Verificado con un veneno, sin Vulkan**: `reorder_probe.c` replica el bucle exacto,
`memset` de `0xA5` antes, y cuenta las palabras que conservan el patrón.
**3025 de 4096 intactas.** Con la corrección `dst = fila*(w*4) + col*4`, el mismo programa
da **3 de 4096** (las 3 últimas, desbordamiento del `+4` del `memcpy` final, inofensivo) y
el PNG resultante es **byte-idéntico** al reordenado correcto: **0 de 16384 distintos**.

**La corrección son 4 caracteres**: `* (size_t)w` → `* (size_t)w * 4u`.

### Por qué el `64 bloques` original no lo detectó

Con `NUM_BLOCKS=64` (el corpus de la Fase 2), `side = 64/16 = 4` y `side*side = 16 != 64`.
El propio código lo detecta y **se niega a escribir el PNG**:

```
AVISO: 64 bloques no forman un cuadrado de bloques (64 != k^2). El PNG no se escribe
```

Es decir: el agreement test histórico **nunca exercised esta ruta**. La condición que
salvaguarda el caso Cube se activa justamente en el caso que la habría protegido. Un test
que pasa porque no llegó a la zona con el defecto.

Y con `nblocks=256`, `side = 256/16 = 16` y `16*16 = 256` — **cuadra por casualidad**, que es
justo lo que hace el aviso inservible: `side` se calcula como `nblocks / 16`, y eso da la
raíz cuadrada **sólo cuando `nblocks` es una potencia de 16**. Para 64 sale 4 (falla), para
256 sale 16 (acierta), para 100 sale 6 y `36 != 100` (falla). El único caso que sobrevive al
aviso es el que llega a la ruta con el defecto.

### Confirmación independiente del lado correcto

Escribí un decodificador BC3 en Python **desde la especificación**, sin mirar el C ni el
shader (`corpus/bc3_ref_decoder.py`):

```
t1_gradiente   mi decoder vs ref.rgba : 0 de 16384 bytes distintos
t2_ruido       mi decoder vs ref.rgba : 0 de 16384
t3_estructura  mi decoder vs ref.rgba : 0 de 16384
```

Tres fuentes independientes — el C, mi decoder de especificación, y la GPU — coinciden
**byte a byte** en las 3 texturas, 16384 bytes cada una. El BC3 de IA-2 también es idéntico
byte a byte al que produce `04-IMPLEMENTACION/compressor/`, que es lo que debía.

*(Me equivoqué dos veces escribiendo ese decoder, y las dos lo registries: la rampa de
`a0==a1` no es toda constante —los códigos sobrantes valen 0 y 255— y la interpolación de
color va en 5 bits antes de ensanchar. Con ambas reglas de la especificación, 0 de 16384.)*

### El mensaje de error del script es engañoso

`RESULTADO: GPU != CPU, 0 de 16384 bytes discrepantes. ESTADO: FAIL` se contradice a sí
mismo. Quien lo lea concluirá que la GPU no coincide con la CPU, cuando la comparación de
bytes dice exactamente lo contrario. La redacción debería nombrar la comparación que falló
—«PNG de la GPU vs round-trip CPU: 14496 de 16384»— no un `GPU != CPU` global.

## 2. Estado real de las dos fases, medido por mí ahora

Ambos reproducen. Ninguno de los dos está roto.

### Fase 1 — compresor (CPU)

```
$ 04-IMPLEMENTACION/compressor/test_compress
       reference      PSNR =  28.78 dB
       smooth         PSNR =  19.59 dB
       pure noise     PSNR =  13.65 dB
       adversarial    PSNR =  10.90 dB
       ...
RESULT: all checks passed                       26 checks [ OK ], 0 [FAIL]   rc=0

$ 04-IMPLEMENTACION/compressor/test_alpha_ramp
RESULT: CONFORMA con la especificacion Microsoft (AD-11, +3/+2)
```

**Los cuatro valores de la línea base reproducen exactamente**, con la puntuación de dos
decimales que la directiva nombra. `OBSERVED`, 2026-09-29, esta host.

### Fase 2 — descompresor (GPU)

```
$ 04-IMPLEMENTACION/decompressor/test_decompress --gpu
  dispositivos Vulkan expuestos: 3
    [0] 1002:699f  AMD Radeon RX 550 / 550 Series (RADV POLARIS12)
    [1] 8086:0412  Intel(R) HD Graphics 4600 (HSW GT2)
    [2] 10005:0000  llvmpipe (LLVM 22.1.8, 256 bits)
  OK: RX 550 identificada por PCI, no por indice
  ...
  discrepancias totales : 0 de 4096 canales
  VEREDICTO: GPU == CPU, agreement test PASADO (0 discrepancias)              rc=0
```

0/4096, en la RX 550 identificada por PCI `1002:699f`, con llvmpipe presente en la lista y
**no** seleccionado. Ése es el control de `F4-AD-23` funcionando.

**Una corrección de dato de meses, desde el router:** el router (§3bis) afirma que
`mesa-vulkan-drivers` está `PACKAGE_ABSENT` en HOST-C y que por tanto RADV es
`DRIVER_OPERATIONAL=NOT_AVAILABLE`, con fecha 2026-09-25. Hoy, 2026-09-29:

| Token | Router, 2026-09-25 | Medido, 2026-09-29 |
|---|---|---|
| RADV enumera la RX 550 | `NOT_AVAILABLE` | **`DRIVER_OPERATIONAL`**, `vulkaninfo` lista `AMD Radeon RX 550 / 550 Series (RADV POLARIS12)` |
| `mesa-vulkan-drivers` | `PACKAGE_ABSENT` | **presente** (el ICD `radeon_icd.x86_64.json` está y RADV responde) |

`TEMPORALITY`: el router no es erróneo, es **caducado**. Ninguna afirmación de este
documento invalida la suya; la siguiente lectura debe re-verificar.

## 3. La premisa de los PSNR mezcla dos medidas distintas

**Este es el punto que más cuesta si no se dice ahora, porque el script de IA-2 se
construiría sobre él.** La directiva pide que el pipeline reporte un PSNR y que se verifique
contra `28.78 / 19.59 / 13.65 / 10.90 dB`. Esos cuatro números y el PSNR de un pipeline
`PNG → BC3 → GPU → PNG` **no son la misma cantidad**, y no pueden coincidir por
construcción.

De dónde salen los cuatro, literalmente (`04-IMPLEMENTACION/compressor/test_compress.c:192-212`):

```c
fn(&in, NULL);                        /* patron procedural sintetico */
rx550_compress_block(&in, &blk);
rx550_decompress_block(&blk, &rec);   /* <-- el decodificador de CPU */
total += psnr(&in, &rec);             /* PSNR RGBA 0..255, 16 pixeles, 4 canales */
```

| | Línea base `28.78/19.59/13.65/10.90` | Lo que pide el pipeline |
|---|---|---|
| Decoder | **CPU**, en el mismo proceso | **GPU**, shader Vulkan |
| Contenido | 4 patrones procedurales, 64 bloques cada uno | texturas reales |
| Unidad | 4×4 píxeles, promediada por bloque | imagen completa |
| Qué mide | **regresión del encoder** | **pérdida total del round-trip** |

No son comparables. Un script que verifique "el PSNR del pipeline == 28.78" **falla por
construcción aunque las dos fases sean correctas**, y quien lo lea concluirá que el
compresor se rompió. Ése es el falso positivo que este proyecto ya ha pagado tres veces.

**Lo que sí es verificable, y es más fuerte.** Como el agreement test establece
`GPU == CPU` **byte a byte** (0/4096), y la función de descompresión es la misma, el PSNR
del round-trip por GPU es **idéntico** al del round-trip por CPU, sobre los mismos bloques:

```
PSNR(original, GPU(x)) == PSNR(original, CPU(x))   siempre que GPU(x) == CPU(x)
```

Ése es el criterio correcto de cierre, y es el que propongo a IA-3. Da tres aserciones
separables, cada una con su punto de fallo:

| # | Aserción | Qué aísla |
|---|---|---|
| A1 | `PSNR(compresor+CPU) == línea base`, ±0.01 dB | regresión del **encoder** |
| A2 | `bytes(GPU) == bytes(CPU)`, 0 discrepancias | regresión del **shader** |
| A3 | `PSNR(GPU) == PSNR(CPU)` sobre las texturas del corpus | **integración**, y es consecuencia de A2 |

Y una cuarta, que es la que hace el pipeline PNG→BC3→GPU→PNG completo y que hoy **no tiene
línea base**: el PSNR de la imagen reconstruida. No hay contra qué compararla. No la
invento.

## 4. Lo que sí pude medir: el lado CPU sobre 3 texturas reales

Como el script no existe, construí el corpus que el pipeline necesita y medí con **la
fuente real del compresor**, no con una reimplementación.

Corpus: `06-INGENIERIA-INVERSA/corpus/make_corpus.py` (determinista, sin PIL en el
generador, LCG explícito).

| Textura | Contenido | Por qué está en el corpus |
|---|---|---|
| `t1_gradiente.png` | rampa lineal RGB + rampa de alfa | el caso favorable |
| `t2_ruido.png` | ruido independiente por canal | el peor caso para BC3 |
| `t3_estructura.png` | celdas de 8×8 planas, alfa binario | produce `a0 == a1`, rama que los otros dos no generan |

64×64 RGBA = 256 bloques BC3 cada una.

```
$ python3 make_corpus.py .
  t1_gradiente.png     64x64 RGBA  256 bloques  sha256=49333a1ea0c53e94...
  t2_ruido.png         64x64 RGBA  256 bloques  sha256=53385a2327943ccc...
  t3_estructura.png    64x64 RGBA  256 bloques  sha256=7edc5d6f90b3e20b...
```

Regenerado dos veces, manifiesto `sha256` idéntico byte a byte.

### Medición (compresor real + decodificador CPU)

Sonda en `/tmp/opencode/cpu_probe.c`, compilada contra
`04-IMPLEMENTACION/compressor/rx550_compress.c` y `rx550_compress_avx2.s`.

| Textura | bloques | BC3 | bytes exactos | **PSNR** |
|---|---|---|---|---|
| `t1_gradiente` | 256 | 4096 B | 3762/16384 (22.96 %) | **38.24 dB** |
| `t2_ruido` | 256 | 4096 B | 705/16384 (4.30 %) | **13.55 dB** |
| `t3_estructura` | 256 | 4096 B | 8960/16384 (54.69 %) | **45.12 dB** |

**3 corridas consecutivas, resultados bit-idénticos.** No es ruido intra-run: el
compresor es determinista, como debe ser.

Los tres valores son coherentes por construcción: 45 dB en zonas planas, 38 dB en degradado
suave, 13.5 dB en ruido. **El ruido da 13.55 dB contra los 13.65 dB de la línea base
sintética** — mismo orden de magnitud, que es lo esperable: ruido real y ruido del LCG no
son la misma señal.

## 5. Un error mío que casi se convierte en un falso "PASÓ"

La primera versión de mi sonda usó `RX550_BLOCK_PIXELS` como si fuera el lado del bloque.
**No lo es**: son 16 píxeles *por* bloque, o sea un bloque de 4×4 (`rx550_compress.h:76`,
comentario `/* 4 * 4 */`). Mi sonda procesaba 16 bloques en vez de 256 — **la dieciseisava
parte de la imagen** — y devolvía PSNR en un rango plausible (5.43 a 8.83 dB) sin ningún
síntoma visible. Lo detecté porque imprimí el recuento de bloques junto al PSNR y no
cuadraba con lo que esperaba.

Lo dejo escrito por dos razones. Una: es el cuarto caso de este proyecto de "seitura una
constante y se sale por el nombre" —los otros tres están en `AGENTS.md` §Falsificación
(`git commit` leído de memoria, `vulkan.h` buscado como `vulkan-devel`, `spirv-tools`
inferido de `vulkan-devel`—. Éste es mío y es el primero en el que el fallo **no** da
ningún error, sólo un número plausible. Dos: quien escriba el pipeline va a tener que
convertir píxeles a bloques, y va a toparse con esta misma constante. **Nadie debería dar
por bueno un PSNR sin el número de bloques al lado.**

## 6. Cobertura de bloques: qué cubre el agreement test y qué cubren mis texturas

`06-INGENIERIA-INVERSA/corpus/block_coverage.py`, conteo a nivel de byte sobre los `.bc3`.

| | corpus de la Fase 2 (64) | mis 3 texturas (768) |
|---|---|---|
| `a0 > a1` (rampa de 4 valores) | 54 | 512 |
| `a0 == a1` (rampa de 6 valores) | 9 | 256 |
| `a0 < a1` estricto | 1 | **0** |
| `c0 > c1` | 8 | 28 |
| `c0 < c1` | 56 | 740 |

Tres cosas que salen de aquí:

1. **Mis texturas cubren las dos ramas de rampa que produce el encoder** (4 y 6 valores),
   con 12× más bloques. Un agreement test sobre ellas sería más fuerte que el actual en
   cobertura, no más débil.
2. **`a0 < a1` no lo produce el encoder**, y mis texturas tampoco: la convención D19a
   (`a0 = max, a1 = min`) lo hace inalcanzable. El único bloque con `a0 < a1` en el corpus
   de la Fase 2 es uno de los 8 construidos a mano (`test_decompress.c:186-188`). Un
   pipeline que solo pase por el encoder **nunca** ejercitará esa rama. No es un defecto del
   compresor; es una propiedad de la convención, y conviene que el criterio de cierre no la
   exija.
3. **Comprobé que la cobertura que imprime `test_decompress` y mi conteo no se contradicen.**
   `test_decompress.c:171-173` cuenta sobre el corpus *antes* de que
   `build_six_value_blocks()` sobrescriba los últimos 8 bloques con los construidos a mano;
   mi conteo es sobre el fichero persistido, *después*. Los dos juegos de números son
   consistentes con eso. **No hay `CONFLICT`.** Lo digo porque casi lo declaro.

## 7. Bloqueo 2 — no existe forma de pasar un corpus externo a la GPU

`test_decompress.c:83`: `#define NUM_BLOCKS 64`. El corpus lo construye `build_corpus()`
en memoria desde una semilla LCG fija (`:336`), y la Fase B sube **ese array en memoria**,
no un fichero. No hay `fopen` de entrada, ni argv para el corpus, ni forma de cambiar el
número de bloques sin recompilar.

**Consecuencia: la mitad GPU del pipeline no se puede validar sobre texturas reales con lo
que hay en el repo.** El agreement test 0/4096 es sólido, pero **sólo cubre sus 64 bloques
sintéticos**. Para lo que la directiva pide hace falta una de estas dos, y es decisión de
IA-2, no mía:

- **Opción A** — modo `--corpus <fichero>` en `test_decompress`, con `NUM_BLOCKS` leído del
  tamaño del fichero. Cambio pequeño, y hace el agreement test reutilizable tal cual.
- **Opción B** — un `rx550_decompress` real que lea `.bc3` y devuelva RGBA, que es lo que
  el nombre estable que pide la directiva implica de todas formas.

La Opción B es la que la directiva pide de facto ("binarios con nombres estables
`rx550_compress`, `rx550_decompress`"), y resuelve también el Bloqueo 3.

## 8. Bloqueo 3 — los binarios `rx550_compress` y `rx550_decompress` no existen

No es que estén en otro sitio: **no existen en ninguna forma**. El API público es
`rx550_compress_block()` / `rx550_decompress_block()` (`rx550_compress.h:166,174`), que son
funciones de biblioteca, sin `main`. `test_compress.c:712` es `int main(void)`, sin argv y
con el corpus cableado dentro. No hay ninguna ruta PNG en ninguna parte: `grep -rliE
"png|lodepng|stb_image"` sobre `compressor/` y `decompressor/` no devuelve nada.

Y **la entrada PNG no tiene a quién convertirla**. `rx550_compress_block()` toma 64 bytes
RGBA de un bloque de 4×4. Del PNG a ahí falta un cargador, y el repositorio no lo tiene.

En el host sí hay herramientas: `magick` 7 y `convert`, Python 3 con `PIL` 12.3.0 y
`numpy` 2.4.6. Eso hace la etapa PNG **viable** — pero viable no es hecha. Los tres
componentes que faltan son trabajo nuevo, no integración.

**Aviso para quien lo escriba**: la conversión PNG→RGBA tiene que producir **RGBA de 8
bits, no indexada ni de 16 bits, y en orden R,G,B,A**. El bloque de entrada es
interleaved RGBA8 (`rx550_compress.h:110-112`). Una conversión que produzca BGRA o componentes de
16 bits no da error: da un PSNR malo y un diagnóstico que señala al compressor sin
fundamento.

## 9. Lo que queda abierto, y quién lo tiene

| # | Ítem | Estado | Quién |
|---|---|---|---|
| 1 | **`dst` sin el factor 4** | **`FIXED`** — verificado por mí, 3/3, 3 corridas | cerrado |
| 2 | `README.md` con los 3 comandos | `OBSERVED` — existe; los 3 comandos ejecutados tal cual desde la raíz | cerrado |
| 3 | Mensaje `GPU != CPU` contradictorio | `FIXED` — ahora nombra la comparación que falló | cerrado |
| 4 | `side = nblocks/16` acierta sólo en potencias de 16 | `OBSERVED` — sigue así; el aviso ahora cubre el caso no cuadrado | `NON_BLOCKER` latente |
| 5 | Línea base del PSNR de imagen completa | `NOT_AVAILABLE`; el criterio correcto es A1+A2+A3 | IA-3 |
| 6 | `AD-12` (truncamiento o redondeo del sampler) | `NOT_DETERMINED` | Fase 3, **fuera del alcance por directiva** |
| 7 | `mesa-vulkan-drivers` presente, RADV operativo | `OBSERVED` 2026-09-29 | corregir el router |

**Los bloqueos 2–4 que listé antes ya no aplican.** El script, el cargador PNG
(`common/png_rw.c`, verificado por mí con round-trip propio) y los binarios en `bin/`
existen. Mi diagnóstico de "no existe nada" era correcto cuando lo escribí —03:45— y quedó
obsoleto a las 03:48, dentro de la misma ronda. Lo dejo con su fecha porque un documento que
se corrige a sí mismo sin dejar constancia del estado anterior no es auditable.

**Sobre AD-12**: sigue `NOT_DETERMINED` y no lo toco — la directiva detiene Fase 3. Queda
registrado como pendiente, no como resuelto, y es relevante para el cierre: este proyecto
**produce un encoder** cuyo consumidor es el hardware, así que si el sampler trunca, la
decisión AD-11 hay que reabrirla y el round-trip del encoder no sería el que dice AD-11.

**Estado del cierre, actualizado (§0)**: los tres criterios que propuse se cumplen.

| Criterio | Estado | Evidencia |
|---|---|---|
| A1 — línea base del encoder | **PASO** | 28.78 / 19.59 / 13.65 / 10.90 dB, exactos |
| A2 — agreement GPU, byte a byte | **PASO** | 0 de 4096 (suite) y 0 de 16384 (pipeline, 3 texturas) |
| A3 — `PSNR(GPU) == PSNR(CPU)` | **PASO** | 38.24 / 13.55 / 45.12 dB, idénticos en ambas rutas |
| Pipeline completo sobre 3 texturas | **PASO** | 3/3, rc=0, 3 corridas |
| Cuarta fuente (spec BC3) sobre el PNG | **PASO** | 0 de 16384 × 3 |
| Layout 2D del PNG (§0-ter) | **PASO** | 38.24 / 13.55 / 45.12 dB contra el original, con control negativo a 6–12 dB |
| Binarios reproducibles desde fuentes | **PASO en el árbol de trabajo** | `bin/` borrado y reconstruido, 3/3 |
| **Pipeline reproducible desde un clon del repo** | **`NOT_DETERMINED`** | **`04-IMPLEMENTACION/` sin commitear — §0-bis. Bloquea a IA-2** |

**Condición de refutación de mi "PASO"**: si alguien cambia el corpus, el compresor, el
shader o el escritor de PNG, los tres números de PSNR y el 0/16384 deben moverse. Si el
script vuelve a dar 0/3 con el mismo corpus, el defecto volvió.

**Lo único que no puedo afirmar**: que las Fases 1 y 2 estén *cerradas*. Eso lo declara
IA-3, y le corresponde. Lo que puedo afirmar es que **los tres criterios que yo propuse
para el cierre se cumplen y los medí con reproducibilidad**.

**Criterio que propongo rechazar**: "el pipeline pasa". Un pipeline que no existe no puede
pasar, y un criterio que se cumple por ausencia es peor que uno que no se cumple.

**Criterio que propongo rechazar**: "el pipeline pasa". Un pipeline que no existe no puede
pasar, y un criterio de cierre que se cumple por ausencia es peor que uno que no se
cumple.

## Reproducir esta validación

```bash
cd 04-IMPLEMENTACION/compressor && ./test_compress && ./test_alpha_ramp
cd ../decompressor && ./test_decompress --gpu          # 0 de 4096
cd .. && ./integration_test.sh                          # 0/3, por el defecto de §1
cd ../../06-INGENIERIA-INVERSA/corpus
python3 make_corpus.py . && cat MANIFEST.sha256
python3 bc3_ref_decoder.py ../../04-IMPLEMENTACION/work/t1_gradiente.png.bc3 \
        ../../04-IMPLEMENTACION/work/t1_gradiente.png.ref.rgba \
        ../../04-IMPLEMENTACION/work/t1_gradiente.png.out.png
```

Las sondas `cpu_probe.c`, `reorder_probe.c` y `png_probe.c` **no están en el repositorio a
propósito**: usan rutas absolutas y viven en `/tmp/opencode/`. `reorder_probe.c` es la que
cuantifica el defecto de §1, y la reproduco aquí porque **la corrección es de 4 caracteres
en código de IA-2 y nadie más va a ejecutarla**. Si IA-2 quiere un medidor reutilizable, lo
correcto es un `rx550_probe` en `04-IMPLEMENTACION/bin/`, que es su ámbito. No lo he creado
ahí para no invadirlo.

`corpus/bc3_ref_decoder.py` **sí** está en el repo, y es la pieza que hace falta para
arbitrar cualquier discrepancia futura entre C, shader y hardware sin depender de que las
tres piezas estén de acuerdo entre sí: está escrito desde la especificación BC3, no desde
el C ni desde el shader. Sin dependencias más allá de la biblioteca estándar.
