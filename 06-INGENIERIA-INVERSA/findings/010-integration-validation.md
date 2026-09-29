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

## 1. Bloqueo 1 — `integration_test.sh` no existe

`ls 04-IMPLEMENTACION/integration_test.sh` → *No existe*. Tampoco `04-IMPLEMENTACION/bin/`,
ni `04-IMPLEMENTACION/README.md`. Los tres son tareas de IA-2.

**No hay commit que citar.** La directiva pide "citar el commit del script de IA-2" en
este documento: ese commit **no existe en el momento de escribir**. Citar un hash inventado
sería exactamente el fallo que `AGENTS.md` §Falsificación prohíbe. Se cita lo que sí
existe: `git log -1` = `cc03e33` (IA-2, codificador PM4, 03:19), que **no** contiene el
script.

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
| 1 | `integration_test.sh`, `bin/`, `README.md` | `NOT_DETERMINED` — no existen | IA-2 |
| 2 | Modo de corpus externo para la Fase B | `DEFERRED` — decisión de diseño (A o B) | IA-2 |
| 3 | Cargador PNG → RGBA8 | `NOT_DETERMINED` — no existe | IA-2 |
| 4 | Agreement test GPU sobre los 768 bloques nuevos | `NOT_DETERMINED` — bloqueado por 2 | IA-2, luego IA-1 |
| 5 | Línea base del PSNR de imagen completa | `NOT_AVAILABLE` — no existe; el criterio correcto es A1+A2+A3 | IA-3 |
| 6 | `AD-12` (truncamiento o redondeo del sampler) | `NOT_DETERMINED` | Fase 3, **fuera del alcance actual por directiva** |
| 7 | `mesa-vulkan-drivers` presente, RADV operativo | `OBSERVED` 2026-09-29 | corregir el router |

**Recomendación al cierre**: si IA-3 quiere criterios binarios verificables hoy, los que
**sí** se pueden comprobar sin escribir una línea nueva son A1 (línea base del encoder, ya
medida: 28.78 / 19.59 / 13.65 / 10.90) y A2 (agreement GPU, ya medido: 0/4096). A3 y el
resto dependen de los bloqueos 2 y 3, que son código que aún no existe.

**Criterio que propongo rechazar**: "el pipeline pasa". Un pipeline que no existe no puede
pasar, y un criterio de cierre que se cumple por ausencia es peor que uno que no se
cumple.

## Reproducir esta validación

```bash
cd 04-IMPLEMENTACION/compressor && ./test_compress && ./test_alpha_ramp
cd ../decompressor && ./test_decompress --gpu
cd ../../06-INGENIERIA-INVERSA/corpus && python3 make_corpus.py . && cat MANIFEST.sha256
```

La sonda `cpu_probe.c` **no está en el repositorio a propósito**: usa rutas absolutas y
vive en `/tmp/opencode/`. Si IA-2 quiere un medidor reutilizable, lo correcto es un
`rx550_probe` en `04-IMPLEMENTACION/bin/`, que es su ámbito. No lo he creado ahí para no
invadirlo.
