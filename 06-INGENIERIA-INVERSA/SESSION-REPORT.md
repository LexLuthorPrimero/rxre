# Informe de sesión — IA-1

**Fecha**: 2026-09-29 · **Ámbito**: `06-INGENIERIA-INVERSA/`, con extensible
a `04-IMPLEMENTACION/`

---

## Resumen

Cerrado el trabajo de **integración F1→F2** (pipeline ejecutable y
reproducible) y la **verificación de Q-2/Q-3**. Durante la sesión aparecieron
**tres errores propios** que hubo que corregir, y dos de ellos se habían
propagado a decisiones de otras sesiones.

`Q-5` sigue `NOT_DETERMINED`. No es un bloqueo con.dataset: es la medición que
todavía nadie ha ejecutado.

---

## Commits

| Hash | Contenido |
|---|---|
| `0b95f90` | Ficheros del pipeline F1→F2 — **recogidos del índice por otra sesión** |
| `d94460d` | `PROVENANCE.md`: qué contiene `0b95f90` y por qué |
| `75e6b85` | `llvmpipe_pairs.py` sin `EXPECTED`, sin jerarquía falsa |
| `7c7a384` | `015` describe lo que existe; retira la división 271/378 |
| `3234853` | `015` separa DISEÑADO / IMPLEMENTADO / EJECUTADO / VALIDADO |
| `4ffb53f`, `00f9051`, `5c02833`, `1e28733` | Otras sesiones |

---

## Trabajo entregado

### 1. Pipeline de integración F1→F2 — `04-IMPLEMENTACION/`

`PNG → BC3 (CPU) → decodificación BC3 (RX 550, Vulkan compute) → PNG`, con
comparación pixel a pixel.

**Medido, dos corridas consecutivas idénticas, `rc=0`:**

| Textura | Discrepancias GPU vs CPU | PSNR | Suelo | Estado |
|---|---|---|---|---|
| `t1_gradiente.png` | 0 / 16384 | 38.24 dB | 25 dB | PASO |
| `t2_ruido.png` | 0 / 16384 | 13.55 dB | 10 dB | PASO |
| `t3_estructura.png` | 0 / 16384 | 45.12 dB | 20 dB | PASO |

**Reproducibilidad verificada en clon limpio** (`/tmp/rx550-clean`, sin `.o`,
sin binarios, sin `.spv`): mismas cifras, binarios **bit a bit** idénticos
(`da4eb4cc…`, `680407e0…`).

Las tres cifras **no son la misma cifra**: `0/16384` mide la fidelidad del
decodificador, el PSNR la calidad del codificador con pérdida, y `GPUVSCPU 0`
que el PNG conserve el orden de bloques.

### 2. Tres defectos que el pipeline encontró

Los tres son el mismo patrón — dos números correctos comparados entre cosas
distintas — y ninguno lo habría visto un test sobre el corpus sintético de 64
bloques, donde las dos ordenaciones coinciden:

1. **Orden de bloque frente a orden de imagen.** La GPU escribe el bloque `b`
   en `b*64 + p*4`; la imagen lo quiere en `(by*4+py)*stride + (bx*4+px)*4`.
   Para el primer bloque coinciden. Daba ~13 000 discrepancias falsas.
2. **`dst` sin el factor 4.** Multiplicaba por 4 el término de columna pero no
   el de fila: escribía bien la primera fila y el resto en otro sitio.
3. **`awk -v p=` en vez de `$1`.** El PSNR llegaba por `stdin` y la comparación
   se hacía en `BEGIN`, que no lee `stdin`. Toda textura comparaba `0 >= suelo`.

Más dos `SIGSEGV` por structs `Vk*CreateInfo` sin inicializar y un fallo de
orden de destrucción (`vkFreeCommandBuffers` después de
`vkDestroyCommandPool`), que fallaban **después** de una comparación correcta
y parecían un fallo del shader.

### 3. Q-3: no hay descompresor BC3 en CPU en Mesa — `CONFIRMADO`

Con **una corrección que invalidaba el comando asignado**:
`/usr/lib64/dri/radeon_dri.so` **no existe**; el nombre real es
`radeonsi_dri.so`, symlink a `libdril_dri.so`. `grep -c` sobre un fichero
inexistente da 0, igual que sobre uno sin el símbolo: el comando "confirmaba"
cualquier cosa.

Sobre los binarios reales: **0 símbolos** `dxt5`/`s3tc`. Las 4 cadenas que
quedan son nombres en una tabla de formatos, y el símbolo
`util_format_dxt5_rgba_fetch` que las genera **no existe en el binario
compilado**. radeonsi y RADV no referencian el descompresor.

### 4. Q-2: los 649 discriminantes — `CONFIRMADO`, con la aritmética aclarada

```
spec != trunc  (divergentes)   136686
  llvmpipe == spec  (+3/+2)      42170   30.85 %
  llvmpipe == trunc (bcdec)      93867   68.67 %
  llvmpipe == NINGUNA              649    0.47 %
```

**136 686 no puede ser un recuento de pares**: el universo de pares `(a0,a1)`
es 256×256 = 65 536. Son **triplas** `(a0, a1, code)`, `code ∈ 2..7`. Sin ese
dato, cualquiera que intente verificarlo obtiene un número que no cuadra.

---

## Tres errores propios, corregidos

### Error 1 — una afirmación falsa que se propagó

Proposé dividir las 649 en **271 discriminantes robustos** y **378 débiles**
(por ser estos últimos de la rama `a0<=a1`, donde la spec y el trunc fijan
constantes y llvmpipe interpola).

**Es falso.** Reparto real:

| rama | código | casos |
|---|---|---|
| `a0<=a1` | 5 | **378** |
| `a0>a1` | 5 | 50 |
| `a0>a1` | 7 | 221 |

Los 378 caen **todos en el código 5**, que las tres implementaciones
interpolan. Ninguna cae en código 6 o 7 de la rama `a0<=a1`. **Las 649 son
equivalentes.**

**La decisión de criterio de pase se construyó sobre mi cifra.** Se retiró.

### Error 2 — un `EXPECTED` que convertía el test en tautología

Escribí a mano `EXPECTED = {COMUN: (..., 271)}` con una fila inventada, y el
script no se quejaba porque la acumulación no comprobaba el universo. Un valor
esperado escrito al ver mi propia salida compara consigo mismo.

Ahora el único número que el proyecto no produce es el 649 de `1e28733`, una
derivación independiente sobre el mismo árbol. **Control negativo ejecutado**:
romper `>>8` por `>>7` da `136686 / 1269 / 1272 / 134145` y `rc=1`.

### Error 3 — un documento que describía entregables inexistentes

`015` prometía `test_llvmpipe_discriminator.c` y `llvmpipe_649.bin`. **Ninguno
existe.** No se construyen: el clasificador Python cubre la función que Q-5
necesita, y el corpus `5c02833` ya trae `block_hex` listo para la GPU.

`IMPLEMENTATION_IS_NOT_AUTHORITY`: que un documento prometiera un `.c` no lo
convierte en requisito.

---

## El fallo de coordinación que hay que registrar

**Dos veces** (la segunda ya documentada en `PROVENANCE.md`), mis ficheros
estaban en el índice de git y otra sesión ejecutó `git commit` a secas:
`0b95f90` y `75e6b85` los recogieron bajo mensajes que describían otra cosa.

- Contenido: **idéntico** en disco y en `HEAD` en ambos casos.
- Dañado: el mensaje no describe el contenido, y `git blame` atribuye el
  código a quien no lo escribió.

**El cerrojo de `COORDINACION.md` serializa el árbol, no el índice de git**,
y el índice es donde estos ficheros estaban esperando. Medidas propuestas,
ninguna en el protocolo: `git commit <ruta>` o `-o/--only`, y releer el
mensaje después de escribirlo — es la única parte del commit que no queda en
el árbol y no se puede verificar comparando ficheros.

---

## Estado del proyecto

### Cerrado

| | |
|---|---|
| **Pipeline F1→F2** | `VALIDADO`, reproducible en clon limpio |
| **Layout 2D del PNG** | `PROBADO` con control negativo (`0b95f90`) |
| **Fallback CPU en Mesa** | `REFUTADO`, verificado sobre binarios (`014`) |
| **Corpus de 649** | `REFINDO` y contrastado contra `1e28733` |
| **Fases 1 y 2 (software)** | Cerradas a nivel de lógica y algoritmo |

### Abierto

| | |
|---|---|
| **Q-5** | `NOT_DETERMINED`. Falta demostrar que `lp_build_lerpdxa` es la ruta efectiva de llvmpipe |
| **AD-12** | `NOT_DETERMINED`. Redondeo o truncamiento real del sampler de la RX 550 |
| **`07-DRIVER/`** | Trabajo de Fase 4 |

### Dos precisiones sobre el estado del códec

El códec **completo está implementado y validado**: el compresor en C + ASM
(`05c6297`) y el descompresor en GLSL compute (`F4-AD-12`). La asimetría entre
lenguas es deliberada: `clang` no acepta `-x spirv` ni `-x hlsl`, y solo
`-x cl` produce ISA.

Y una corrección al recuento de `1e28733`: los porcentajes 30.8 % y 68.6 % son
correctos **sobre 136 686**; sobre las 393 216 triples serían 10.7 % y 23.9 %.
La cifra absoluta coincide; el denominador no.

---

## Lo siguiente, en orden

1. **Q-5** — medir si la ruta estudiada es la efectiva en ejecución. Es lo que
   separa «la aritmética que el código declara» de «la que el software usa».
2. **AD-12** — con el oracle validado, medir la rampa en la RX 550.
3. **Fase 4** — el driver exclusivo, que sigue bloqueado por `F4-AD-5`
   (falta autorización de `unbind`).

Nada de esto requiere decisión mía. Los dos primeros son mediciones, y ambos
dependen de ejecución en hardware que necesita su autorización correspondiente.
