# 1525 — Segunda instancia de la misma clase, en el mismo fichero: `bar0_mib` y `bar0_mib_log` son el mismo hecho por dos vías y nunca se compararon

```text
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 10:11 -03
TIPO=FACT + NEGATIVE_RESULT (las puertas NO tienen el defecto) + ERROR PROPIO
ESTADO=PROVEN la omisión / PROVEN la reparación / REFUTADO un rc que escribí
ALCANCE=08-ARQUITECTURA/tools/fingerprint.py.  SOLO LECTURA sobre hardware.
DEPENDE_DE=1524 (el eje kernel añadido; alli se construyo _inconsistencias)
ENCADENA=1524 dejo abierta su propia pregunta -> aqui se mide con AST
  -> se encuentra la segunda instancia -> se distingue por que NO es igual
  -> y se corrige un rc mal medido en 1524
```

## La pregunta que `1524` dejó abierta

`1524` añadió el eje `kernel` porque el campo se leía y no se comparaba, y
construyó `_inconsistencias()` para el par `kernel` / `kernel_release`.

Eso dejó una pregunta sin responder, y era la obvia:

> `Collected()` produce **29** campos. `TARGET` compara **11**.
> **¿Qué otros se leen, se imprimen, y no se comparan nunca?**

Antes de contestarla, una comprobación de disciplina: si la respuesta fuera
«diecisiete campos más y ningún verificador más», entonces el hallazgo sería una
anécdota y no merecía un número. Así que primero se miró si el defecto existía
en otra parte.

## Primero, lo que NO es el problema: las puertas del proyecto

La instancia más peligrosa de esta clase es una **puerta**: si un gate imprime
veredicto sin comparar nada, la automatización lo confía. Hay tres.

Un grep rápido sugería que `reenvio_gate.py` tenía **cero** vectores que
afirmaran fallo. **Era falso**, y por la razón de siempre:

```text
    res("G1 sha declarado que no cuadra -> 1 y marca G1", ...)
    res("G2 fila de 4 campos -> 1 y marca G2", ...)
    res("G0 mapa inexistente -> 2", cod == EXIT_FALLA, ...)
```

El segundo argumento de `res()` es `cod == EXIT_FALLA`, no el literal `False`.
Buscando literales `ok = False` no hay ninguno, y `0` vectores negativos era un
artefacto del patrón de búsqueda. Leídos los vectores: **~24, y casi todos
afirman fallo.** Los tres gates tienen controles negativos reales.

**Esta frontera no existe.** Se registra como `NEGATIVE_RESULT` y se pasa.

> un grep que no encuentra nada no dice que no haya nada: dice que el patrón no
> busca lo que hay

## La medición con AST, y el control positivo

```text
campos que el PRODUCTOR construye : 29
etiquetas que el CONTRATO compara  : 11
campos que se IMPRIMEN            : 25
PRODUCIDOS Y NO COMPARADOS        : 18
```

El control positivo importa: `kernel_release` **ya está** en el contrato, porque
`1524` lo añadió. Si el método no lo hubiera encontrado, el resultado entero
sería dudoso.

De los 18, casi todos están justificadamente fuera del contrato —
`thread_siblings`, `ram_kib`, `gpu_slot_sysfs` son internos o derivados, y
`gpu_slot` está excluido **a propósito** y por escrito en el docstring del
fichero («el índice 01:00.0 es una convención de esta máquina, no una propiedad
del hardware»).

Pero uno no es un campo suelto: es **el mismo hecho por dos vías**.

## La segunda instancia

```text
fingerprint.py:293   campos["bar0_mib_log"] = ...  "Detected VRAM RAM=(\d+)M, BAR=(\d+)M"
fingerprint.py:317   campos["bar0_mib"]     = ...  /sys/bus/pci/devices/<slot>/resource
fingerprint.py:606   ambos se IMPRIMEN
fingerprint.py:149   SOLO bar0_mib está en TARGET
```

Dos fuentes **independientes** del mismo hecho:

| campo | fuente | qué es |
|---|---|---|
| `bar0_mib_log` | journalctl, `Detected VRAM RAM=…, BAR=…M` | lo que **amdgpu vio** |
| `bar0_mib` | `resource` de PCI config | lo que el **hardware tiene** |

Se imprimen los dos, se compara uno, y hoy coinciden:

```text
$ python3 08-ARQUITECTURA/tools/fingerprint.py --campo bar0_mib      -> 256
$ python3 08-ARQUITECTURA/tools/fingerprint.py --campo bar0_mib_log  -> 256
```

Así que la omisión **no produce un error hoy**. Es una comprobación que nunca
se ha hecho. Y si algún día difieren —un firmware que redimensiona BAR0, un
driver que leyera otra cosa, una línea de log que cambiara de formato— el
fingerprint lo imprimiría **sin señalar nada**, con dos números a la vista que
el lector tiene que saber comparar por su cuenta.

## Y aquí está la parte que NO es igual que `1524`

El reflejo sería meter el par en `_inconsistencias()` y que la discrepancia dé
`rc=3`. **Eso habría sido un error**, y conviene decir por qué.

| tipo de par | si difieren | |
|---|---|---|
| `kernel` / `kernel_release` | **el verificador está roto** | `rc=3`, se aborta |
| `bar0_mib` / `bar0_mib_log` | **el hardware es raro** | se informa, `rc` no cambia |

La primera pareja sale del **mismo** `uname`: si no coinciden, la herramienta se
contradice a sí misma y su veredicto no vale. La segunda sale de **dos fuentes
distintas**: que difieran es un hecho sobre la máquina, no un defecto del
programa. Un firmware que recorta BAR0 es una respuesta documentada de la
placa, no un fallo.

Confundir los dos casos produce un `rc=3` que aparece por dos motivos distintos
y acaba sin significar nada. Y una herramienta cuyos avisos no se distinguen
enseña a ignorarlos.

Por eso van por caminos separados: `_inconsistencias()` → `rc=3`;
`_crosadas()` → una línea `COINCIDE` / `DIFIERE` en el informe, y el código de
salida **no se toca**.

```text
VIAS INDEPENDIENTES DEL MISMO HECHO
------------------------------------------------------------------------
  hecho          via_1          via_2          estado
  bar0_mib       256            256            COINCIDE
```

**Mutaciones de la parte nueva** — tres, todas fallan:

```text
M6  la comparación siempre dice COINCIDE     -> self-test FALLA (1)  rc=1
M7  DIFIERE se reporta como INCONSISTENTE   -> self-test FALLA (1)  rc=1
M8  una vía ausente se informa como si compara-> self-test FALLA (1)  rc=1
```

M7 es la importante: es exactamente la confusión entre «hardware raro» y
«herramienta rota», introducida a propósito y detectada.

Cuando una de las dos vías falta **no se dice nada**: es `INDETERMINATE`, que por
la regla que el propio fichero ya tiene no es ni `MATCH` ni `MISMATCH`.

## Y una corrección a `1524`: escribí un `rc` que no medí

Al registrar la regresión del cambio anterior puse:

```text
- `REGRESSION` — `toolkit.py` sigue en `rc=0`, `contrato valido 54/68`
```

**Es falso.** El rc de `toolkit.py` es **1**. Lo escribí porque puse `rc=$?`
después de un *pipeline*, de modo que leí el rc de `tail`, que es el último del
pipe:

```text
python3 toolkit.py | tail -12 ; echo "rc=$?"      <- rc de tail, no del toolkit
```

Medido bien, y comparando contra el árbol sin mis cambios:

```text
SIN mis cambios   rc=1   contrato valido 54/68
CON mis cambios   rc=1   contrato valido 54/68
diff de la salida completa:  IDENTICA
```

Dos cosas, y la segunda importa más que la primera:

1. **La conclusión era correcta aunque el número no.** Mi cambio no altera
   `toolkit.py`; la salida es byte-idéntica.
2. **El `rc=1` dice algo que el `rc=0` tapaba**: 14 de 68 herramientas sin
   contrato válido. Es un dato real sobre el estado del proyecto que este
   hallazgo estaba ocultando detrás de un cero inventado.

Se corrigió `1524` **añadiendo** la corrección, sin borrar el original, y
anotando que el error fue de medición y no de criterio.

> `exit 0` de un pipeline es el `exit` del último miembro.
> El error no fue creer el numero: fue medir el numero equivocado.

## Procedencia

- `CROSS-CHECK` — dos vías para la omisión: por **grep** (los campos y el
  contrato, y se verificó el control positivo `kernel_release`) y por **AST**
  (`ast.walk` sobre las asignaciones a `campos[...]`, la tupla `TARGET` y el
  bucle de impresión de `_informe`).
- `NEGATIVE_RESULT` — las puertas: leído el código, no el grep.
- `SELF_TESTED` — 25 vectores, 6 mutaciones nuevas (M6, M7, M8), las tres
  fallan.
- `REGRESSION` — `toolkit.py` con salida byte-idéntica, `rc=1` antes y después.
- Diff acumulado del fichero: +433 −32. **Cero escrituras en hardware.**

## Lo que queda abierto, sin adornos

- **17 campos más** se producen e imprimen sin compararse. La mayoría están
  justificadamente fuera (internos, derivados, o excluidos por escrito), pero
  **eso se ha comprobado uno a uno por lectura, no por criterio**. No hay
  verificador que decida si un campo debe estar o no en el contrato, y ese es un
  hueco real, no medido: `NOT_DETERMINED`.
- **`ram_gib` fuera del contrato** es discutible y en general lo es: el
  TARGET CONTRACT de AGENTS.md declara `12 GiB DDR3` como parte del target, y
  el verificador no lo comprueba. No se ha añadido porque «cuál es la RAM
  esperada» es una decisión de proyecto, no una reparación — igual que el
  `7.1.3` de `1521`. Se registra como pregunta abierta, no como defecto.
- **`1524` sigue `PARCIAL` en M1**: la defensa de producción funciona y está
  medida, pero ningún vector del self-test lo caza.