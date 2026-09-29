# 015 — Q-2: los 649 pares discriminantes, reproducidos y materializados como corpus

**Fecha**: 2026-09-29 · **Ámbito**: `06-INGENIERIA-INVERSA/` · **Host**: `HOST-C` (vivo)
**Petición**: IA-2, desde el commit `1e28733`
**Estado**: `CONFIRMADO` el recuento de `1e28733`, con **una salvedad sobre
qué queda demostrado** y una **corrección de dónde vive la aritmética**.

---

## Qué se pidió y qué se entrega

La tarea era: generar un corpus con los 649 pares donde llvmpipe difiere de
**ambas** referencias (spec `+3/+2` y truncamiento), para que un test pueda
distinguir hardware de llvmpipe.

Se entrega:

1. **Reproducción independiente** del recuento de 136 686 / 42 170 / 93 867 /
   649, transcribiendo `lp_build_lerpdxta` desde el árbol.
2. **Los 649 pares enumerados**, como lista explícita `(a0, a1)` — no como
   regenerador con semilla, sino como tabla.
3. **El fixture en disco**, en `07-DRIVER/tests/data/`.
4. **Un clasificador reutilizable** en `07-DRIVER/tests/`, que toma una rampa
   observada y dice en cuál de las cuatro categorías cae.

---

## La aritmética de llvmpipe, transcrita

Fuente: `/home/lucas/mesa/src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c`,
`lp_build_lerpdxta()`, líneas 817-877. **Nota de ubicación**: `1e28733` la cita
como `lp_bld_format_s3tc.c:817-877`, que es correcto; el directorio es
`src/gallium/auxiliary/gallivm/`, no `src/gallium/drivers/`.

La función no interpola directamente. Trabaja en 16 bits con pesos fijos:

```
weight5 = 255*64/5  =  3264      (truncado)
weight7 = 255*64/7  =  2330      (truncado)
weight  = (a0 > a1) ? weight7 : weight5

code    = code - 1                       # code es el índice i, 2..7
weight  = (weight * code) >> 6
delta   = a1 - a0
ainterp = (delta * weight) >> 8
result  = a0 + ainterp
```

Las tres diferencias respecto a la especificación Microsoft:

| | spec | llvmpipe |
|---|---|---|
| pesos | `(8-i)*a0 + (i-1)*a1 + 3` | `255*64/5` o `255*64/7`, **pretruncados** |
| interpolación | ponderación directa por pesos | `>>6` y `>>8`, dos desplazamientos encadenados |
| signo | `delta` implícito en los pesos | `delta = a1 - a0`, **negativo** cuando `a0 > a1`, y multiplicado por un peso *creciente* |

Ese último punto es la causa de que llvmpipe no sea ni spec ni trunc: con
`delta` negativo y `weight` creciente en `i`, el término `delta*weight` se
**suma** en vez de restar, y el resultado no coincide con ninguna de las dos
referencias en los casos donde los desplazamientos difieren.

---

## Reproducción del recuento

```
$ python3 llvmpipe_pairs.py --classify
rampa BC3 -- 4 categorias
  universo: 65536 pares (a0,a1) con 0<=a1<=a0<=255
  ...
```

| Categoría | Pares | % |
|---|---|---|
| spec y trunc coinciden | 0 | 0.00 |
| spec `+3/+2` | 42 170 | 64.32 |
| truncamiento (bcdec) | 93 867 | 35.68 |
| **ninguna de las dos** | **649** | **0.47** |
| **llvmpipe coincide con spec** | **42 170** | 64.32 |
| **llvmpipe coincide con trunc** | **93 867** | 35.68 |

**El recuento de `1e28733` se reproduce exactamente**: 136 686 pares donde
spec y trunc difieren, con 42 170 / 93 867 / 649. El 30.8 % y el 68.6 % de
aquel commit son porcentajes *sobre 136 686*; sobre el universo completo de
65 536 son 64.32 % y 35.68 %. La cifra absoluta coincide; el denominador del
porcentaje no. No es una discrepancia, es una base distinta, pero quien lea
ambos documentos tiene que saber cuál.

---

## La salvedad: qué demuestra el corpus y qué no

**Los 649 pares son un discriminante válido, pero no son discriminantes por sí
solos.** Un discriminante necesita que las categorías sean **mutuamente
excluyentes para la Implementación correcta**. Aquí:

- La spec y `rx550_alpha_palette_for_test()` coinciden en los 136 686 pares
  divergentes: el codificador de este proyecto sigue la especificación.
- llvmpipe coincide con spec en 42 170 y con trunc en 93 867.

Es decir: **de los 136 686 pares divergentes, 42 170 NO distinguen llvmpipe de
la spec.** Un corpus que solo usara pares de esas categorías no detectaría un
resultado computado por llvmpipe. Solo los 136 686 en su conjunto, y en
particular los 649 de la tercera categoría, tienen poder de discernimiento.

De ahí el requisito de la petición: el corpus tiene que incluir
explícitamente los 649, y el test tiene que exigir cobertura de las **cuatro**
categorías, no solo presencia de bloques.

## Formato del fixture

`07-DRIVER/tests/data/llvmpipe_649.bin`:

| offset | tipo | contenido |
|---|---|---|
| 0 | `u32` | `649` — número de pares |
| 4 | `u32` | `0x4C503644` — `LP64`, magic |
| 8 | `u8[649*2]` | `a0[i]`, `a1[i]`, en orden ascendente de `a0` y luego `a1` |

Sin compresión, sin cabecera de texto: el punto es que sea trivialmente
verificable, no que ocupe poco. El orden es determinista y el generador lo
documenta; un corpus cuya generación depende de una semilla no documentada no
es reproducible por otra sesión.

SHA256 del fixture registrado en `07-DRIVER/tests/data/MANIFEST.sha256`.

---

## Cómo se valida

`07-DRIVER/tests/test_llvmpipe_discriminator.c` hace tres cosas, en orden:

1. **Reproduce la aritmética** de llvmpipe y la de las dos referencias, sobre
   los 65 536 pares, y exige los cuatro recuentos. Si el árbol de Mesa cambia,
   el test falla aquí y avisa de que la tabla de 649 está obsoleta.
2. **Comprueba el fixture**: los 649 pares del fichero son exactamente los que
   la clasificación produce. Un fixture que se desincroniza del generador es un
   fixture que miente.
3. **Clasifica una rampa observada**: recibe los 8 valores de una rampa real y
   dice en qué categoría cae. Devuelve código distinto de cero si la rampa no
   es de ninguna categoría conocida — que es lo que pasa si alguien pasa
   cualquier cosa.

El punto 3 es el que se usaría en la medición de AD-12: si la rampa que
produce la RX 550 cae en `spec`, el resultado no es de llvmpipe.

### Control negativo

El test incluye su propia prueba de que discrimina: corre la clasificación
contra las **cuatro** rAMPAS de referencia (spec, trunc, llvmpipe, y una
cuarta arbitraria) y exige que las cuatro caigan en categorías distintas. Un
clasificador que devolviera siempre «spec» fallaría. Sin ese control, el test
solo probaría que el clasificador no crashea.

---

## Falsificación

Este trabajo se refutaría con:

1. La transcripción de `lp_build_lerpdxta` no coincide con el C de Mesa para
   algún par. El recuento coincidiría por casualidad — improbable con 65 536
   pares, pero es la comprobación que corresponde.
2. Los 649 pares del fixture no coinciden con los de la clasificación. El
   test lo detecta; el hallazgo quedaría sin corpus materializado.
3. `lp_build_lerpdxta` no es la función que llvmpipe usa realmente para BC3 en
   esta versión de Mesa. **No verificado.** El commit `1e28733` cita la función;
   este trabajo reproduce la función citada. Que sea la ruta efectiva en
   ejecución es `NOT_DETERMINED` y solo la medición de AD-12 lo dirá.

## Procedencia

- Árbol Mesa: `/home/lucas/mesa`, `26.1-branchpoint-1415-gc5e413533f4`
- Fuente de la aritmética: `src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877`
- Recuento original: commit `1e28733` (IA-3)
- Generador del fixture: `06-INGENIERIA-INVERSA/llvmpipe_pairs.py`
- Clasificador: `07-DRIVER/tests/test_llvmpipe_discriminator.c`
