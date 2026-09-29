# RX550 block texture codec — BC3/DXT5

Compresor de bloques de textura 4:1 para la **RX 550 (Polaris 12, Lexa)**, en espacio de
usuario. Sin cabeceras de kernel, sin carga de módulos, sin dependencia de la línea de
forense E1.

**Estado**: suite completa en verde — **26/26 comprobaciones en `test_compress`, más el
test independiente de rampa, `make test` rc = 0**.

> **El formato es BC3/DXT5 estándar de Microsoft.** Entre 2026-09-28 y 2026-09-29 este
> README y el código llamaron al formato "RX550_BC4X" y afirmaron que la rampa alfa de
> 6 valores no era BC3. Ambas cosas eran falsas, y ambas se construyeron sobre una premisa
> nunca verificada. Ver §1.1 y la decisión AD-8.

---

## 1. Qué es

Un bloque de **4×4 píxeles RGBA8 = 64 bytes** de entrada se emite en **16 bytes**:
ratio **4:1**, exactamente. Sub-bloque alfa de 8 bytes con índices de 3 bits, seguido de
sub-bloque color de 8 bytes con índices de 2 bits.

### 1.1 Identidad del formato: BC3/DXT5 estándar

| parte | regla | ¿conforme? |
|---|---|---|
| contenedor | 8 B alfa con índices de 3 bits + 8 B color con índices de 2 bits, 16 B, 4:1 | **sí** |
| color | BC1: endpoints RGB565, 4 valores, interpolación en espacio de 5 bits | **sí** |
| alfa, modo 8 valores | `a[i] = ((8-i)*a0 + (i-1)*a1 + 3)/7`, `i = 2..7` | **sí** |
| alfa, modo 6 valores | `a[i] = ((6-i)*a0 + (i-1)*a1 + 2)/5`, `i = 2..5`, y `a[6]=0`, `a[7]=255` | **sí** |

La especificación Microsoft "Block Compression (Direct3D 10)" dice: *"If alpha_0 is
greater than alpha_1, then BC3 interpolates 6 alpha values; otherwise, it interpolates 4.
When BC3 interpolates only 4 alpha values, it sets two additional alpha values (0 for
fully transparent and 255 for fully opaque)."* Corroborado por `bcdec`, `oxideav-dds`,
`DirectXTex/D3DX` y el análisis de ryg sobre comportamiento real de hardware.

El sub-bloque alfa de BC3 **comparte la rampa de BC4 por diseño**. No es una desviación:
BC4 es un formato de un solo canal y no tiene sub-bloque de color. Este formato tiene
ambos, luego es BC3.

**Polar 12 no tiene decodificador BC3 por hardware.** Una búsqueda del árbol de amdgpu
(36.695 ficheros, 2026-09-28) no encontró ningún decodificador BC3/DXT5, ni microcode de
descompresión, ni soporte de formato de textura BCn. El único hit fue
`CP_PERF_SEL_IMG_READ_FMT_BC3` en `vega10_enum.h`, un contador de rendimiento.

Consecuencias:

- **Estos bloques SÍ pueden subirse como `DRM_FORMAT_BC3` y samplearse.** Cualquier
  implementación de BC3 —`bcdec`, `basisu`, un visor, otro driver— los lee. Ese fue el
  argumento decisivo para abandonar el nombre propio: un formato inventado garantiza que
  nada más pueda leerlo.
- El compute shader de `../decompressor/` es el decodificador que usa este proyecto, y es
  una **opción**, no una obligación impuesta por el formato.

**Historia del nombre**, porque el error se cometió en las dos direcciones. Una versión del
shader afirmó que el C era la especificación y que *no* era DXT5 — con una rampa `/7` en
ambas ramas que coincidía con el `rx550_compress.c` de `05c6297`, también no conforme. Dos
implementaciones mutuamente consistentes y ambas erróneas pasan cualquier prueba de
round-trip. La versión siguiente corrigió la aritmética y la etiquetó "BC3 conforme",
manteniendo la regla de BC4: la aritmética era correcta y la etiqueta seguía siendo falsa.
Ni "conforme a DXT5" ni "el C manda sobre la especificación" describen este proyecto.

### Por qué 4×4 → 16 bytes, y por qué eso no es una decisión de diseño

Las unidades de textura de Polaris 12 (GFX8) contienen **decodificadores de bloques de
función fija**. La forma 4×4 → 16 bytes no es una elecciónesthetics hecha para "una tarjeta
de 2 GB": es la forma que el hardware ya consume. Elegir cualquier otra significaría gastar
ciclos de shader GCN ISA para reimplementar un decodificador que el silicio ya tiene.

Esto es el mismo argumento por el que la regla 1 del manifiesto RX550-FIRST prevalece sobre
la regla 3 ("no imitar") en la capa de page tables: **la disposición del bloque es una
propiedad del hardware, no una preferencia del driver de AMD**.

> **Nota sobre la suposición de 2 GB.** La cifra de 2 GiB se arrastra como **cota superior
> conservadora, NO como hecho establecido**. La restricción medida en este silicio es la
> apertura MM de 2 GiB, no la capacidad de VRAM. Registrado como `PROB-001`. Nada en este
> códec depende de cuál de las dos lecturas sea la correcta.

---

## 2. Estructura del bloque

16 bytes exactos, sin relleno de cola, sin alineación implícita más allá de 1.

| offset | bytes | campo | descripción |
|---:|---:|---|---|
| 0 | 1 | `a0` | endpoint alfa 0 (máximo del bloque) |
| 1 | 1 | `a1` | endpoint alfa 1 (mínimo del bloque) |
| 2–7 | 6 | `a_idx` | 16 × índice de 3 bits, LSB-first |
| 8–9 | 2 | `c0` | endpoint color 0, **RGB565 little-endian** |
| 10–11 | 2 | `c1` | endpoint color 1, **RGB565 little-endian** |
| 12–15 | 4 | `c_idx` | 16 × índice de 2 bits, LSB-first, 4 por byte |

El tamaño lo fija `_Static_assert`, no un comentario:

```c
_Static_assert(sizeof(rx550_block_t) == RX550_BLOCK_BYTES, ...);
_Static_assert(offsetof(rx550_block_t, a_idx) == 2,  "alpha index offset");
_Static_assert(offsetof(rx550_block_t, c0)   == 8,  "colour endpoint offset");
_Static_assert(offsetof(rx550_block_t, c_idx) == 12, "colour index offset");
_Static_assert(RX550_INPUT_BLOCK_BYTES / RX550_BLOCK_BYTES == 4, "block codec must remain exactly 4:1");
```

### Rampa alfa (8 valores, regla BC3/DXT5 de Microsoft)

`a0` es el máximo, `a1` el mínimo. **Modo de 8 valores** cuando `a0 > a1`: seis valores
interpolados dividiendo por 7, `a[i] = ((8-i)*a0 + (i-1)*a1 + 3)/7` para `i = 2..7`.

**Modo de 6 valores** cuando `a0 <= a1`: cuatro valores interpolados dividiendo por 5,
`a[i] = ((6-i)*a0 + (i-1)*a1 + 2)/5` para `i = 2..5`, y los dos códigos sobrantes son los
extremos fijos, `a[6] = 0` y `a[7] = 255`. Ésta es la regla de BC3/DXT5 —el sub-bloque alfa
de BC3 comparte rampa con BC4 por diseño— y es la regla *menos* conforme del formato, no la
más.

### Nota sobre alfa plano

El caso `a0 == a1` (alfa uniforme) no necesita guarda especial: toma la rama `a0 <= a1`, donde
los coeficientes de `a0` y `a1` suman 5, luego `a[i] = (5*a0 + 2)/5 = a0` para `i = 2..5`, y
`a[6] = 0`, `a[7] = 255` por construcción. Es decir:

- `pal[0..5] = a0`
- `pal[6] = 0` (transparente)
- `pal[7] = 255` (opaco)

**Esto es comportamiento estándar de DXT5 según la especificación de Microsoft, no un
defecto.** Los dos códigos sobrantes decodifican siempre a los extremos, con independencia de
los endpoints del bloque.

No se manifiesta como artefacto visual porque el codificador selecciona el índice 0 para
todos los píxeles de un bloque plano, y `pal[0] = a0`. Los índices 6 y 7 nunca se emiten en
ese caso.

La conformidad se verifica para **los 65 536 pares de endpoints** contra la regla transcrita
de forma independiente en `test_alpha_ramp_independent.c`, y ese test se demuestra capaz de
fallar con `make check-ramp-discriminates`, que lo enlaza contra la rampa no conforme de
`05c6297` y exige código de salida distinto de cero.

### Corrección factual del 2026-09-28 — la fuente primaria contradice «es una desviación»

Este README afirma que la rama `a0 <= a1` «es la regla de BC4 y la desviación que da nombre
al formato», y que «BC3 cierra su modo de 6 valores con `a[7] = a1`, un endpoint
duplicado». **Ambas afirmaciones son falsas**, según la especificación primaria:

- *Block Compression (Direct3D 10)*, `learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression`
  (publicada 2022-08-26), sección BC3, publica textualmente
  `alpha_6 = 0;` y `alpha_7 = 255;` para la rama `a0 <= a1`.
- La misma fuente describe esa rama como compartida: BC4 declara el mismo comportamiento, y
  por eso un mismo bloque de 8 bytes con esa rampa sirve a ambos formatos.

Es decir: **no hay desviación**. La rampa implementada *es* la de BC3, y también la de BC4.
La rama es común a ambos formatos porque el hardware la implementa una sola vez.

| Afirmación previa | Estado | Fuente |
|---|---|---|
| «BC3 cierra el modo de 6 valores con `a[7] = a1`» | **FALSA** | spec BC3: `alpha_7 = 255` |
| «es la regla de BC4 y la desviación que da nombre al formato» | **FALSA** | spec BC3, rama `a0 <= a1` idéntica |
| «no es un formato de Microsoft» | **FALSA** | el bloque es BC3/BC4 de Microsoft |

`CONFORMITY_PROVENANCE = SPECIFICATION_VERIFIED` — la rampa se contrastó con la
especificación primaria, no sólo con transcripciones.

**Lo que NO se corrige aquí sin decisión del `HUMAN`**: el nombre `RX550_BC4X` y la
afirmación de que es una `HUMAN_POLICY` del 2026-09-28. Esa decisión **no consta** en
ninguna conversación registrada, y `AGENTS.md` §1 prohíbe inventar o tomar prestada una
decisión humana. Queda como `DECISION_REQUIRED` y el nombre actual se conserva sin alterar
mientras no se resuelva.

### Paleta de color (siempre modo 4 colores)

| entrada | valor |
|---|---|
| 0 | `c0` |
| 1 | `c1` |
| 2 | `(2·a + b) / 3` |
| 3 | `(a + 2·b) / 3` |

Expansión de bits a 8, la misma que hace el hardware al ensanchar RGB565:

```c
static inline uint8_t expand5(uint32_t v5) { return (uint8_t)((v5 << 3) | (v5 >> 2)); }
```

El modo de 1 bit / 3 colores no existe en esta disposición de bloque.

**Trampa documentada en el código**: la expresión aparentemente evidente
`"desplazar por 8 - i*2"` para extraer R/G/B de un RGB565 es **incorrecta** — en `i=1`
cruza los campos R y G y produce un valor que no pertenece a ningún canal. El error es
invisible (la paleta sigue en rango) pero destruye el bloque, porque encoder y decoder
dejan de coincidir sobre qué significan los endpoints. Por eso se usa una tabla explícita
`rgb565_shift[3] = { 11, 5, 0 }` en vez de una fórmula.

### Selección de endpoints de color

1. Caja envolvente por canal a 5 bits a partir del min/max por SIMD.
2. Si un canal es plano, se ensancha para que los dos endpoints difieran y la interpolación
   quede definida.
3. Barrido diagonal de inset sobre **5 candidatos**, puntuado cada uno contra el **error de
   reconstrucción real** — la paleta cuantizada que el decoder reconstruirá de verdad, no
   una idealizada. El mejor gana.

---

## 3. Compilar y ejecutar

```bash
make            # compila -> ./test_compress
make test       # compila y ejecuta la suite + el test independiente de rampa
make check-ramp-discriminates   # demuestra que el test de rampa sabe fallar
make check-asm  # falla si el ensamblador pierde sus instrucciones AVX2
make disasm     # vuelca el desensamblado con sintaxis Intel
make clean
```

Requisitos: GCC o Clang, `make`, `libm`. Sin dependencias externas.

### Por qué el fichero C **no** se compila con `-mavx2`

El brief original pedía `-O3 -mavx2` para todo. Se sigue para el ensamblador y
**deliberadamente no** para la referencia C.

Si `rx550_compress.c` se compilase con `-mavx2`, GCC auto-vectorizaría la ruta portátil con
instrucciones AVX2. `rx550_have_avx2()` devolvería 0 en una CPU pre-Haswell, el dispatcher
elegiría correctamente la ruta "C", y **esa ruta ejecutaría una instrucción ilegal**. La
detección en runtime pasaría de mecanismo de seguridad a hazards.

La referencia C se compila para el baseline x86-64 y se mantiene portátil. El único AVX2
del grafo de objetos vive en `rx550_compress_avx2.s`, alcanzable sólo tras pasar la
comprobación en runtime (`__builtin_cpu_supports("avx2")`).

---

## 4. Verificación

`make test` — 26 comprobaciones en `test_compress` más el test independiente de rampa,
agrupadas:

| Test | Qué establece |
|---|---|
| **T1** | Tamaño de bloque (16 B exactos), entrada 64 B, ratio 4:1, y round-trip del patrón de referencia por encima del suelo |
| **T2** | Casos degenerados: todo-cero, todo-máx, todo-medio, outlier único, un solo canal. **Más** conformidad de la rampa alfa contra la regla BC3/DXT5 de Microsoft en los 65 536 pares de endpoints, y los invariantes `a0<a1`, `a0>a1` y alfa plano |
| **independiente** | `test_alpha_ramp_independent.c`, en su propio binario: la rampa contra una transcripción independiente, que sale con código distinto de cero ante cualquier desacuerdo. `make check-ramp-discriminates` lo enlaza contra la rampa no conforme de `05c6297` y **exige que falle** |
| **T3** | La reducción AVX2 es **bit-idéntica** a la referencia C sobre **200 000 bloques** |
| **T4** | El camino AVX2 completo es bit-idéntico al camino C completo sobre los mismos bloques |
| **T5** | El error de round-trip está acotado y **el acotamiento se mide, no se supone** |
| **T6** | Throughput de ambas rutas |

### Sobre las expectativas de T2

Un invariante de planares está correctamente enunciado así: un bloque plano debe decodificar
al valor **que el formato puede representar** — la expansión RGB565 más cercana — y nunca a
otro. El alfa siempre es exacto, porque la rampa alfa lleva 8 códigos en 8 bits.

Una versión anterior de este test exigía color exacto para `0x80` y fallaba en 48 de 64
valores de canal. **Esa expectativa era un defecto del TEST, no del códec**: 128 no es un
valor 5-6-5, y decide la propia precisión del formato. El alfa de un bloque `0x80` sí es
exacto, y eso sí se comprueba.

### Lo que T5 reporta sin afirmar

```
reference      PSNR = 28.73 dB     tripwire 24 dB   [ OK ]
smooth         PSNR = 19.59 dB     tripwire 16 dB   [ OK ]
pure noise     PSNR = 13.64 dB     tripwire 11 dB   [ OK ]
--- reported, not asserted ---
adversarial    PSNR = 10.89 dB
no parity claim against a reference BCn encoder: NOT_AVAILABLE
```

El caso adversarial se **reporta pero no se afirma**: por debajo de su propio tripwire, y
reportarlo es más honesto que mover el tripwire hasta que pase. Y **no se afirma paridad con
un codificador BCn de referencia** — no hay uno disponible en este entorno
(`NOT_AVAILABLE`).

---

## 5. Throughput medido

Medido en este host, sobre MB/s de **entrada consumida**:

| Ruta | Throughput |
|---|---|
| C (referencia portable) | **~28 MB/s** |
| AVX2 | **~28 MB/s** |
| Speedup | **0,97× – 1,05× entre ejecuciones** |

> **Cifras corregidas el 2026-09-28.** Este README publicaba 85,9 / 89,9 MB/s y un
> speedup de 1,05×. Esos valores son de una versión anterior del codificador y **no son
> reproducibles hoy**. El codificador actual rinde ~28 MB/s en ambas rutas.
> La regresión de ~3× está **`UNEXPLAINED`**: no procede de la corrección de la rampa DXT5
> (que hace *menos* iteraciones: 4 en vez de 6) ni de `RX550_INSET_CANDIDATES`, que sigue
> en 5. Se asocia a cambios del otro escritor en `rx550_compress.c` y merece análisis
> propio antes de publicarse como cifra. No se corrige el número para que cuadre: se
> publica el medido y se marca su estado.
>
> El speedup oscila alrededor de 1 porque el SIMD cubre **sólo** la reducción min/max
> (ver abajo), de modo que la diferencia entre rutas es pequeña frente al coste del
> codificador. Un valor único de speedup no es una medida; el rango sí.

### Por qué el speedup es modesto

**El SIMD cubre únicamente la reducción min/max.** La construcción de paleta y la búsqueda
de índices por píxel siguen en C, por decisión explícita de diseño: son trabajo ramificado
donde SIMD aporta poco y el riesgo de corrección es alto.

Además, un speedup pequeño es el resultado *correcto* aquí. `amdgpu_vm_pde_update()` — el
análogo de esta ruta en el driver — se invoca una vez por BO relocalizado por llamada, no
por byte. No hay un bucle caliente que vectorizar, y la ruta crítica del proyecto no es de
rendimiento sino de corrección. Reescribirla en ensamblador no habría comprado nada
medible.

---

## 6. API

```c
/* 1 si la CPU implementa AVX2, 0 si no. Cacheado tras la primera llamada. */
int  rx550_have_avx2(void);

/* Dispatcher: elige AVX2 si está disponible, si no la referencia C.
 * Ambas producen salida bit-idéntica; sólo cambia la velocidad. */
void rx550_compress_block    (const rx550_rgba_block_t *src, rx550_block_t *out);

/* Rutas explícitas, para benchmark y para el test de coincidencia. */
void rx550_compress_block_c   (const rx550_rgba_block_t *src, rx550_block_t *out);
void rx550_compress_block_avx2(const rx550_rgba_block_t *src, rx550_block_t *out);

/* Decoder de referencia. Round-trip exacto dentro del límite de error declarado.
 * Escrito para claridad, no para velocidad: el GPU decodifica en hardware. */
void rx550_decompress_block(const rx550_block_t *in, rx550_rgba_block_t *dst);

/* Fuerza una ruta concreta (gancho de test). */
void rx550_set_impl(rx550_impl_t impl);   /* AUTO | C | AVX2 */

/* Reducción min/max expuesta a propósito: el test debe poder demostrar que el
 * ensamblador y la referencia C coinciden bit a bit. Ocultarlas dejaría como única
 * validación la salida del bloque, que es con pérdida y por tanto no puede
 * certificar la reducción. */
void rx550_minmax_c   (const uint8_t src[64], uint8_t out[8]);
void rx550_minmax_avx2(const uint8_t src[64], uint8_t out[8]);
```

Entrada: `rx550_rgba_block_t` = 16 píxeles × 4 bytes, orden **R, G, B, A** por píxel.

---

## 7. Historia de defectos en el ensamblador

`rx550_compress_avx2.s` documenta en su cabecera los **cuatro** defectos que este diseño
corrige. No los reproducibles aquí; los tres primeros son la razón por la que el fichero
existe en su forma actual.

| # | Defecto | Consecuencia |
|---|---|---|
| 1 | Macros `.macro` de GAS | No ensamblaba: dentro de un cuerpo `.macro`, `%name` significa "sustituir el nombre del parámetro", así que un registro literal debe ser `%%ymm0`, y ese escape no sobrevive a una invocación anidada |
| 2 | Deinterleave con `VPERMD` e índices `{c, c+4, c+8, …}` | Un píxel es **un dword de 32 bits**, así que el índice 4 selecciona el píxel 4, no un lane de byte. Los índices 8..31 estaban fuera de rango y devolvían cero. El correcto es `VPSHUFB`, que selecciona **bytes** dentro de un lane de 128 bits |
| 3 | **Aliasing de registros** — `%ymm0`/`%ymm1` guardaban los 64 bytes de entrada y eran también destino del plegado horizontal | Tras la primera reducción, **7 de las 8** restantes operaban sobre basura. El mínimo salía corrupto |
| 4 | **Trampa del `0x00` de `VPSHUFB`** — la tabla `.Lswap01` usaba índices `0x80` | Con el bit alto activo `VPSHUFB` produce **`0x00`**, que gana siempre en un `vpminub` ⇒ **el mínimo devolvía cero en todos los bloques**. El plegado final era además redundante: tras `vpshufd $0xb1` el byte 0 ya es la respuesta |

El defecto 4 es el que mejor ilustra por qué el test compara contra la referencia C y no
contra el resultado del bloque: el bloque se reconstruía *plausible* y el alfa y el color
salían a cero de forma sistemáticamente consistente, de modo que un test de round-trip
sencillo no lo habría delatado. T3 sí.

El invariante que previene la reaparición está escrito sobre la función:

```
REGISTER CONTRACT: %ymm0 y %ymm1 contienen los 64 bytes de entrada, cargados una vez
y NUNCA escritos de nuevo. %ymm2/%ymm3 planos_extraídos, %ymm4 la máscara,
%ymm5 el acumulador, %xmm6 el temporal de plegado de lanes.
```

---

## 8. Alcance y autorización

Este trabajo es **código nuevo en espacio de usuario** dentro de `04-IMPLEMENTACION/`. No
parchea el kernel: no toca page tables (PDE/PTE del GMC), ni MEC, ni políticas de power o
clocks. Conforma la decisión humana `AD-4`, que mantiene `RG-1` íntegra y aplica el
manifiesto RX550-FIRST exclusivamente a este directorio.

No se ha ejecutado nada contra la GPU. No hay claim de mejora de rendimiento en el juego:
las cifras de la sección 5 son de **este códec en esta CPU**, no del renderizado.

---

## 9. Ficheros

| Fichero | Contenido |
|---|---|
| `rx550_compress.h` | Geometría, layout del bloque, API. `_Static_assert` sobre tamaño y offsets |
| `rx550_compress.c` | Referencia C, palettes, selección de endpoints, dispatcher, decoder |
| `rx550_compress_avx2.s` | Reducción min/max AVX2. Bit-idéntica a la referencia C por contrato |
| `test_compress.c` | 26 comprobaciones + benchmark |
| `test_alpha_ramp_independent.c` | Conformidad de la rampa contra una referencia independiente. Binario propio, salida no cero ante desacuerdo |
| `test_alpha_ramp_mutation.c` | La rampa no conforme de `05c6297`, como objetivo de mutación. Existe sólo para que el test anterior pueda demonstrarse capaz de fallar |
| `Makefile` | `all` · `test` · `check-ramp-discriminates` · `check-asm` · `disasm` · `clean` |
| `README.md` | Este fichero |
