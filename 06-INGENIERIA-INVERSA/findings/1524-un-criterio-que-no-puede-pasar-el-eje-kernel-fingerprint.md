# 1524 — Un criterio que no puede pasar: el eje `kernel` añadido a `fingerprint.py` daba MISMATCH con el kernel correcto, y su self-test pasaba igual

```text
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 05:23 -03
TIPO=FACT + ERROR (propio) + CONTRADICTION_RESUELTA
ESTADO=REFUTADO el criterio inicial / PROVEN el defecto / PROVEN la correccion
ALCANCE=08-ARQUITECTURA/tools/fingerprint.py.  SOLO LECTURA sobre hardware.
DEPENDE_DE=1521 (el TARGET_MISMATCH de kernel_release)
ENCADENA=1521 dio el mismatch -> aqui se decidio COMO se comprueba -> aqui se
 Rompio el comprobador al construirlo -> aqui se midio y se reparo
```

## Qué se iba a hacer, y por qué era correcto

`1521` dejó el segundo eje del `TARGET_MISMATCH` sin comprobación automática:
el `.ko` del proyecto es para 7.1.3 y el kernel que corre es 7.2.9, y esa
discrepancia rompe `insmod` con `Invalid module format`.

Al medir dónde vivía eso, salió el hueco real: **`fingerprint.py` leía el
kernel y no lo comparaba.**

```text
fingerprint.py:136    campos["kernel"] = un.strip() if un else None    <- se LEE
fingerprint.py:311    "os", "kernel", "arch", ...                     <- se IMPRIME
fingerprint.py:52-63  TARGET = [ ... ]                                 <- NO se compara
```

Es la sexta aparición en este proyecto de la misma clase de defecto, y es la
que el propio proyecto ya nombró: **un valor calculado y nunca comparado no es
un criterio, es un dato.**

Y hay un segundo dato en la misma línea que importa más: **el validador ya
existía.** `fingerprint.py` ya hacía exactamente lo que §4 pide — fingerprint
reproducible con veredicto `TARGET_MATCH`, y `NOT_AVAILABLE ≠ MATCH` — y ya
detectaba el otro eje:

```text
$ python3 08-ARQUITECTURA/tools/fingerprint.py | tail -3
  igpu          True                                   False                  MISMATCH
TARGET_MISMATCH en: igpu
rc=1
```

Dos iteraciones resolviendo a mano lo que una herramienta presente respondía.
Eso no es un hallazgo nuevo: es la métrica del proyecto saliendo a la superficie.

## El defecto, y es uno serio

Añadir `("kernel", "7.1.3", None)` al contrato parece correcto. No lo era.

La regla general de `veredicto()` para cadenas es:

```python
elif isinstance(esperado, str):
    estado = "MATCH" if esperado in str(real) else "MISMATCH"
```

Y el campo `kernel` no es una versión: es **la salida entera de `uname -srmo`**.

```text
$ uname -srmo
Linux 7.2.9-200.nobara.fc44.x86_64 x86_64 GNU/Linux
```

Empieza por `Linux ` y acaba en `GNU/Linux`. Entonces `"7.1.3" in real` es
`False` **siempre**, y el criterio queda así:

```text
$ python3 -c "... _es_misma_serie(real, '7.1.3') ..."
  real (7.2.9, INCORRECTO) -> False   <- correcto
  real (7.1.3, CORRECTO)   -> False   <- INCORRECTO
```

**El criterio no distinguía el kernel bueno del malo.** Da la misma respuesta en
los dos casos.

Esto es peor que no comprobar el eje. Un criterio que no puede fallar **falla en
silencio y con apariencia de haber functioned**: si el proyecto hubiera
migrado a 7.2.9 correctamente, esta herramienta habría seguido gritando
`TARGET_MISMATCH`, y el diagnóstico equivoco habría apuntado al hardware en vez
de al verificador.

> un criterio que no puede pasar no es un criterio débil: es uno que reporta
> sobre el hardware lo que en realidad es un defecto suyo

Y el self-test **pasaba**. Lo comprobé antes de tocar nada, porque la secuencia correcta aqui era sospechar del propio criterio y no escribir el hallazgo como si
fuera una mejora:

```text
self-test OK (... 2 de veredicto)
```

Siete vectores nuevos y el número de fallos era cero, porque los vectores
probaban la función con cadenas que el productor **nunca emite**.

## Las tres capas, y por qué hizo falta la tercera

La reparación no fue un ajuste de una línea. Fueron tres defectos
superpuestos, cada uno detectado por una mutación distinta.

### Capa 1 — el substring sobre versiones

La regla general es `esperado in str(real)`: un **substring**, y sobre números
de versión tiene falsos positivos reales.

```text
"7.1.3" in "17.1.30"     -> True   (otra serie)
"7.1.3" in "7.1.30-rc1"  -> True   (otro patchlevel)
```

Se añadió `_es_misma_serie()`: prefijo de serie, y el carácter siguiente — si lo
hay — no puede ser dígito ni punto. El sufijo de distro empieza por guion y
pasa; un patchlevel más alto sigue con dígito y no.

**Mutación M2** — reducir el predicado a `return s in r`:

```text
self-test FALLA (2)
   patchlevel mas alto NO es la misma serie: True != False
   serie precedida de otra no es la misma serie: True != False
rc=1
```

Falla. Capa 1 cubierta.

### Capa 2 — la lógica del productor, probada como el lenguaje

El release se extraía en línea dentro de `Collected()`:

```python
_un_tok = un.split() if un else []
campos["kernel_release"] = _un_tok[1] if len(_un_tok) > 1 else None
```

Y el self-test **reimplementaba** esa línea con su propio `un.split()[1]`.

**Mutación M1** — cambiar el *call site* para que devolviera la cadena con
sobre:

```text
self-test OK (...)      rc=0      <- NO LA DETECTO
```

Dos veces seguidas. Porque el vector probaba `str.split` — el lenguaje — y no
el código:

> un self-test que reimplementa la lógica que dice probar no prueba la lógica

Se extrajo `_release_de()`, y ahora `Collected()` y el self-test llaman a **la
misma** función.

**Mutación M3** — tomar el token `[0]` en vez del `[1]`:

```text
self-test FALLA (3)
   el productor extrae el release de 'uname -srmo' (7.2.9): 'Linux' != '7.2.9-...'
   el productor extrae el release de 'uname -srmo' (7.1.3): 'Linux' != '7.1.3-...'
   uname de un solo token no da release: 'Linux' != None
rc=1
```

Falla. Capa 2 cubierta.

### Capa 3 — el armado, que no lo cubría nada

Sigue faltando: **M1 no la detectaba**, y ahora fallaba por otra razón — el
*call site* de `Collected()` no lo ejercita ningún vector, porque los vectores
usan campos sintéticos y `Collected()` lee hardware.

Hay un invariante propio que sí es comprobable sin máquina: **el release es un
token de la cadena `kernel` que produjo el mismo `uname`.** Si los dos no
concuerdan, el fingerprint se contradice a sí mismo.

Se añadió `_inconsistencias()` y un **rc=3 distinto** del 1 (`MISMATCH`) y del
2 (`INDETERMINATE`), porque *un verificador que se contradice a sí mismo no ha
medido un target distinto: ha fallado como verificador*. Es otra cosa que un
`MISMATCH`, y con el mismo número sería invisible.

Se extrajo `_informe(campos)`, que ahora usan **tanto** `main()` como el
self-test: una sola implementación, llamada por los dos lados. Eso además da
algo que no tenía: **el verificador de target del proyecto entero tiene ahora
vectores que no necesitan que la máquina sea la correcta** — que es justo cuando
más se necesitan.

**Mutación M4** — desconectar la alarma (`malas_internas = []`):

```text
self-test FALLA (4)      rc=1
```

**Mutación M5** — degradar el rc=3 a rc=1, que es exactamente el fallo silencioso
que se quería cazar:

```text
self-test FALLA (2)      rc=1
```

Ambas fallan. Capa 3 cubierta.

## Un vector falló por la razón equivocada, y eso también es dato

Al añadir la comprobación de texto, un vector falló contra **mi propio código**:

```text
self-test FALLA (1)
   un fingerprint inconsistente no debe imprimir TARGET_MISMATCH
```

La causa: el mensaje que escribí para explicar el caso dice

```text
FINGERPRINT_INCONSISTENTE (2).  Esto NO es un TARGET_MISMATCH:
```

— que **contiene** el substring que el vector buscaba. El oráculo era demasiado
grueso: no distinguía «emite el veredicto MISMATCH» de «dice que no es MISMATCH».

La tentación era relajar el vector para que pasara. Eso es exactamente lo que
este proyecto prohíbe, y además habría sido ocultar un defecto real. Lo que se
hizo fue **afilarlo**: se comprueba la línea de veredicto, que empieza por
`TARGET_MISMATCH en:`, y no cualquier mención de la palabra.

```text
    un substring sobre prosa no es un oráculo
```

Es la misma razón por la que Capa 1 existe, aplicada a texto en vez de a
versiones. Dos veces en el mismo cambio.

## El estado final, y lo que M1 sigue sin tener

```text
self-test OK (1 de unidades, 4 de parser con 3 controles negativos,
2 de veredicto, 5 de serie de kernel con 3 controles negativos,
3 del productor real con 3 controles negativos, 1 de distincion,
2 de forma del contrato, 4 de consistencia interna con 3 controles
negativos, 5 de camino completo sin hardware)
rc=0

$ python3 08-ARQUITECTURA/tools/fingerprint.py | tail -3
  igpu            True        False                  MISMATCH
  kernel_release  7.1.3       7.2.9-200.nobara.fc44. MISMATCH
TARGET_MISMATCH en: igpu, kernel_release
rc=1
```

**Y M1, con la defensa puesta, en producción:**

```text
FINGERPRINT_INCONSISTENTE (2).  Esto NO es un TARGET_MISMATCH:
   kernel_release ('Linux 7.2.9-... GNU/Linux') no es el release de kernel (...)
   kernel_release ('Linux 7.2.9-... GNU/Linux') tiene mas de un token: no es
   un release, es una cadena con sobre
  El veredicto de arriba no es de fiar hasta arreglar esto.
rc=3
```

**Lo que NO se afirma, y es la parte honesta de este hallazgo:**

- **`M1` sigue sin ser detectado por un vector del self-test.** Lo detectan
  `_informe` y el camino de producción, y eso está medido arriba, pero el
  self-test por sí solo no lo caza. La causa es honesta y es un límite, no un
  olvido: `Collected()` lee hardware real y los vectores son sintéticos.
  Cubrirlo del todo exigiría inyectar la lectura, y eso es trabajo que no está
  hecho. Se declara **parcial**, no cerrado.
- **No se ha modificado el valor esperado del target.** `7.1.3` sigue siendo el
  esperado. Cuál de los dos kernels es el target sigue siendo decisión del
  propietario, igual que en `1521`. Lo que se añadió es que **la discrepancia
  ahora es detectable automáticamente**, sea cual sea el valor que se elija.
- **No se ha tocado hardware.** Sin MMIO, sin insmod, sin `/sys` escrito.
  `fingerprint.py` lee `/proc`, `/sys` y llama a `lspci` y `journalctl`.

## Procedencia

- `SELF_TESTED` → los 22 vectores nuevos, con 6 mutaciones deliberadas
  (M1 ×3, M2, M3, M4, M5), **tres de las cuales no dispararon nada** hasta que
  se reparó la capa que dejaban fuera.
- `CROSS-CHECK` — el veredicto por dos vías: el contractual
  (`TARGET_MISMATCH en: igpu, kernel_release`, rc=1) y el directo (`uname -r`
  contra `modinfo | grep vermagic` de `1521`).
- `REGRESSION` — `toolkit.py` sigue en `rc=0`, `contrato valido 54/68`, idéntico
  a antes del cambio.
- Diff: `08-ARQUITECTURA/tools/fingerprint.py`, +352 −31. **Cero escrituras en
  hardware, cero cambios en otros ficheros.**

## La nota que resume el hallazgo

Tres cosas que no se esperaban al empezar:

1. **El validador ya existía y ya detectaba uno de los dos ejes.** La pregunta
   «¿por qué no vi esto antes?» tiene una respuesta que no es Robinson Crusoe:
   no se había ejecutado la herramienta que el proyecto ya tenía para esto.
2. **El criterio nuevo estaba roto antes de ser escrito,** y su self-test pasó
   con siete vectores nuevos. Un test suite que pasa no es evidencia de nada si
   no se ha intentado romper deliberadamente lo que cubre.
3. **Hizo falta la tercera capa.** La primera corrigió el predicado; la segunda,
   que el vector probara el código y no el lenguaje; la tercera, que el *armado*
   estuviera probado. Ninguna se habría encontrado sola: cada una la dejó
   rota la anterior.

> el defecto no era el comparador, ni el extractor, ni el campo.
> Era que nadie comprobaba si el comprobador comprobaba algo.