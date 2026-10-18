# 1526 — Doce de los vectores de `run_all.py` no pueden fallar, y hay dos autoridades para TARGET_MATCH que se contradicen

```text
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 10:21 -03
TIPO=FACT + ERROR (del proyecto, no mio) + CONTRADICTION
ESTADO=PROVEN los dos hechos, por ejecucion, no por lectura
ALCANCE=08-ARQUITECTURA/tools/run_all.py, tools/fingerprint.py.
  SOLO LECTURA. La unica escritura fue una mutacion deliberada y revertida.
PRECEDE_A=1524 y 1525 (que arreglaron un verificador; este dice que el
  ARRIQUE que lo ejecuta no podria notarlo)
```

## Por qué este hallazgo importa más que los dos anteriores

`1524` añadió un eje que rompía el verificador de target y lo probó con seis
mutaciones. `1525` añadió una comparación que faltaba y la probó con tres.

Los dos eran correctos. Y los dos eran, a la vez, **irrelevantes en la
práctica**, por una razón que no se había mirado: nadie mira el veredicto de
`fingerprint.py` salvo una persona, y `run_all.py` — el corredor del proyecto —
acepta sus self-tests rotos como correctos.

> arreglar un comprobador que nadie consulta no es dejar el sistema mejor

La pregunta que lo abrió fue de integración, no de semántica: **¿quién consume
el veredicto?** La respuesta fue `run_all.py`, y ahí aparecieron las dos cosas.

## Hecho 1 — los vectores de self-test de `run_all.py` no pueden fallar

La tupla de cada vector es `(label, args, want_lines, rc_tol)`, y se consume así:

```python
clase = t[4] if len(t) > 4 else "objetivo"
...
rc, ok = run(label, ["python3", os.path.join(HERE, a[0])] + a[1:],
             want_lines=n,
             rc_ok=[0, rc_tol] if rc_tol is not None else None)
```

Y dentro de `run()`:

```python
validos = [0] if rc_ok is None else list(rc_ok)
return r.returncode, r.returncode in validos
```

Con eso, los **12 vectores `--self-test`** del fichero:

```text
vectores con rc_tol en la tupla: 27
de los cuales son --self-test:    12
distribucion de rc_tol:           Counter({'1': 12})
```

**Los doce usan `rc_tol=1`**, o sea `rc_ok=[0, 1]`. Un self-test devuelve **0 al
pasar** y **1 al fallar**. Aceptar ambos es aceptar que pase y que falle.

Y `want_lines` no salva nada: es puramente de presentación.

```python
if want_lines and len(lines) > want_lines:
    print(f"... ({len(lines) - want_lines} lineas antes omitidas)")
```

No participa del veredicto. La tupla parece discriminating —tiene un número de
líneas esperado— y no lo es.

### Demostración, con la función de ellos y no una reimplementación

Se invocó `run_all.run()` directamente, con los mismos argumentos que el
vector, y se inyectó una mutación que hace fallar el self-test:

```text
=== A) self-test SANO ===
self-test OK (1 de unidades, 4 de parser con 3 controles negativos, ...)
[0.0s  rc=0]
   -> rc=0  ok=True

=== B) self-test ROTO (mutacion deliberada) ===
   MUTACION: vector inyectado que no existe
[0.0s  rc=1]
   -> rc=1  ok=True   <<< ESTO ES EL HALLAZGO
```

**El self-test falla con `rc=1` y el vector lo marca `ok=True`.**

Esto no es un análisis del código: es la ejecución del corredor con una
herramienta deliberadamente rota. La mutación se revirtió y el fichero quedó
verificado (`self-test rc=0`, verificador `rc=1`, compila).

> un vector cuyo criterio acepta el valor y su negación no es un vector

**Por qué `rc_tol` existe y por qué aquí no sirve.** El docstring de `run()`
explica que se creó porque `num_collision` devuelve 3 y eso es un hecho del
proyecto, no un fallo de la herramienta. Es una razón buena y está bien
resuelta. El problema es que **el mismo mecanismo se aplicó después a 12
self-tests**, donde `rc=1` significa exactamente lo contrario: *el self-test
falló*. La excepción razonable se convirtió en regla general, y una excepción
generalizada deja de ser excepción.

## Hecho 2 — hay dos autoridades para TARGET_MATCH, y se contradicen

Dos ficheros, mismo nombre, misma función declarada:

```text
35040  08-ARQUITECTURA/tools/fingerprint.py
22926  tools/fingerprint.py
```

En la **misma máquina**, en el **mismo minuto**:

```text
=== rc AISLADOS (sin pipe) ===
  tools/fingerprint.py            rc=0
  08-ARQ/tools/fingerprint.py     rc=1
```

Y lo que dicen:

```text
08-ARQ/tools/fingerprint.py:
  igpu          True    False   MISMATCH
  kernel_release 7.1.3  7.2.9…  MISMATCH
  TARGET_MISMATCH en: igpu, kernel_release

tools/fingerprint.py:
  igpu_id       sysfs card0/device   NO_OBSERVADO   None
  VEREDICTO: TARGET_PARCIAL
  Hay campos sin observar. No es MATCH, y no se rellenan con el
  valor declarado para que salga bien.
```

**Cada uno lo consume uno distinto:**

| | `08-ARQUITECTURA/tools/` | `tools/` |
|---|---|---|
| lo invoca | `run_all.py:346-349` | `mutscore.py:180,823` |
| eje `kernel` | **sí** (añadido en `1524`) | **no** |
| flag de self-test | `--self-test` | `--selftest` |
| rc cuando no es MATCH | `1` | **`0`** |

## Y lo peor del segundo: dice que no es MATCH y sale con 0

```text
  VEREDICTO: TARGET_PARCIAL
  Hay campos sin observar. No es MATCH, y no se rellenan con el
  valor declarado para que salga bien.
rc=0
```

El texto es correcto y es exactamente la razón de existir de la otra
herramientia: *`NOT_AVAILABLE` no es `MATCH`*. Pero **el código de salida no lo
refleja**. Un llamante que compruebe solo el rc —que es lo que se hace en
automación— lee **éxito**.

Y el propio fichero declara la regla que incumple:

```text
REGLA QUE IMPONE EL PROPIO CONTRATO. `NOT_AVAILABLE` no es `MATCH`. Un campo que no
se pudo leer se reporta como tal y hace que el veredicto NO sea MATCH. Si no, el
fingerprint "pasa" mientras le falta la mitad, que es como un filtro que solo dice
"no".
```

El filtro dice «no». El `rc` dice «sí».

Que lo invoque `mutscore.py` —el puntúador de mutación del proyecto— es lo que
hace esto más incómodo: **el análisis de cobertura de mutación se está haciendo
contra la autoridad equivocada.**

## Detalle 3 — `--completo` está documentado y no existe

```text
Uso:
  fingerprint.py --completo     todos los campos + veredicto
```

`main()` solo reconoce `--self-test` y `--campo`. `--completo` cae al camino
normal, así que hace exactamente lo mismo que sin él. Y el vector de `run_all.py`
lo pide esperando `rc=0`:

```python
("fingerprint: TARGET_MATCH",
 ["fingerprint.py", "--completo"], 0, 0),
```

```text
$ python3 08-ARQUITECTURA/tools/fingerprint.py --completo ; echo $?
1
```

**Y esto es previo a `1524`**, medido con `git stash`: sin mis cambios también
daba `rc=1`. Lo anotaba porque «mis cambios rompieron el corredor» sería falso, y
también porque importa que el corredor ya estaba en rojo ahí antes.

## Detalle 4 — dos «256» que no son lo mismo

```text
bar0_mib       256         <- BAR0, en MiB, del recurso PCI
rmmio_size     262144      <- BAR de registros, en KiB
```

En `tools/fingerprint.py` el segundo aparece como `bar_registro 262144 bytes
(256 KiB)`. Los dos dicen «256» y miden cosas con **mil veces de diferencia**.
No es un error —son campos distintos con nombres distintos— pero es el mismo
número a la vista de un lector en dos herramientas distintas, y `1525` acababa de
añadir justo la clase de comprobación que lo distinguiría.

## Procedencia

- **Ejecución, no lectura**, para los dos hechos centrales. El primero
  inyectando una mutación y llamando a `run_all.run()` con los argumentos
  exactos del vector. El segundo ejecutando los dos ficheros y comparando rc en
  aislamiento, **sin pipes** — que es el error que corregí en `1525`.
- `CROSS-CHECK` del Hecho 1: por código (`ok = r.returncode in validos`) y por
  ejecución (mutación + `ok=True` con `rc=1`).
- `REGRESSION` — `--completo` en `rc=1` **antes y después** de mis cambios de
  `1524`/`1525`, medido con `git stash`. No lo causé.
- Reversión verificada: `self-test rc=0`, verificador `rc=1`, `py_compile` limpio,
  `grep` de la cadena de mutación → 0 apariciones.
- **Cero escrituras en hardware.** Sin MMIO, sin `insmod`, sin `/sys` escrito.

## Lo que NO se ha hecho, y por qué

- **No he corregido `run_all.py`.** Cambiar `rc_tol` de 1 a 0 en 12 vectores
  pone el corredor en rojo de golpe, y eso **no es una reparación**: es una
  decisión sobre qué se considera un fallo conocido. Corresponde al
  propietario, y el orden correcto es que el corredor sea rojo primero y que
  después se arregle lo que encuentre.
- **No he unificado los dos `fingerprint.py`.** Borrar uno es irreversible y el
  otro tiene 22 comprobaciones propias que no están en el primero. Y hay una
  fuente visible de verdad: el primero es el que ejecuta `run_all.py`.
- **No he tocado `tools/fingerprint.py`.** Su `rc=0` con `TARGET_PARCIAL` es un
  defecto real y **corregirlo lo declararía en rojo**, que es el orden correcto.
- **No he añadido el eje `kernel` al segundo.** Es una reparación de
  comportamiento y pertenece a la misma decisión de unificación.

## Lo que queda, en una frase por cosa

| | |
|---|---|
| 12 vectores de `run_all.py` | **PROVEN**, no pueden fallar. Corrección = decisión del propietario |
| 2 autoridades de TARGET_MATCH | **PROVEN**, se contradicen en la misma máquina |
| `tools/fingerprint.py` rc=0 con `TARGET_PARCIAL` | **PROVEN**, el rc contradice su propio texto |
| `mutscore.py` mide la autoridad equivocada | **PROVEN**, por ruta |
| `--completo` documentado e inexistente | **PROVEN**, previo a esta sesión |
| cuál de las dos es la buena | **NOT_DETERMINED**, no medido |
| por qué hay dos ficheros | **NOT_DETERMINED**, no medido |

La nota que cierra el hallazgo:

> Los dos hallazgos anteriores se diverted en la semántica del comprobador.
> Este dice que la comprobación **no se ejecutaba de una forma que pudiera
> notar la diferencia**. Un corredor que acepta la herramienta rota y la sana
> indistintamente no valida nada, y da igual cuántas mutaciones se hayan
> escrito abajo: por arriba todo sigue verde.