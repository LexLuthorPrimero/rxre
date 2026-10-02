# 062 · La cita que arbitra `block_size` está desplazada 2 líneas, y la tabla de `030` invierte dos valores

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · CORPUS=RESEARCH/working/linux-7.1.3
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué NO es este hallazgo

Esto **no** cierra ninguna frontera y **no** corrige ninguna conclusión. La
conclusión `num_level = 1 → root_level = AMDGPU_VM_PDB0` ya está `PROVEN` por
tres vías independientes y `C-009` la registra. Lo que sigue es higiene de citas,
clasificado `ERROR`.

Lo digo primero porque el riesgo real de esta nota es que alguien la lea como
una corrección sustantiva y la use para reabrir `C-009`. No hay nada que reabrir.

## Control de duplicados, ejecutado antes de escribir

La primera hipótesis de este trabajo era que el mapa `num_level → root_level` no
estaba registrado. **Es duplicada**: `C-009` ya contiene el `switch` completo y
el `enum`, y su apartado `RESIDUO` ya marca `030` como refutado en este punto
(`CONTRADICTIONS.md:549-552`, `:577-580`). No se registra como `C-012` porque
sería novedad falsa.

Lo que sigue **no** aparece en `C-009` ni en ningún otro fichero: es la única parte
que sobrevive al control de duplicados.

## `ERROR` 1 · la línea que arbitra `C-009` no contiene lo que se le atribuye

`C-009` es el árbitro canónico de `block_size`. Su cadena de evidencia cita la
línea que decide el nivel raíz, y aquí el `:NNNN` es **el número de línea dentro
de `amdgpu_vm.c`**, no de `CONTRADICTIONS.md` (se escribe el nombre explícito
porque la notación en cadena es ambigua y aquí sería un error de lectura):

```
CONTRADICTIONS.md:512   :2438 switch case 1 -> root_level = AMDGPU_VM_PDB0
                         ^^^^^ este 2438 es de amdgpu_vm.c
```

La línea 2438 de `amdgpu_vm.c` **no** contiene eso:

```c
amdgpu_vm.c:2437        adev->vm_manager.root_level = AMDGPU_VM_PDB1;
amdgpu_vm.c:2438        break;
amdgpu_vm.c:2439        case 1:
amdgpu_vm.c:2440        adev->vm_manager.root_level = AMDGPU_VM_PDB0;
```

La afirmación está en **2440**, con `case 1:` en **2439**. `:2438` es el `break`
del `case 2:` anterior. Desplazamiento de 2 líneas.

**Por qué importa pese a no cambiar la conclusión.** `C-009` es ahora la fuente
canónica y todo el proyecto cita "C-009 dice `amdgpu_vm.c:2438`". El arbitraje es
correcto; su **ancla textual** no. Quien reutilice la cita para abrir el
`switch` aterriza en un `break;` y no ve el `case 1:` hasta dos líneas más abajo.
Es el mismo fallo que `C-011` describe para otro fichero, y por el mismo motivo:
la cita es un índice, y un índice desplazado no señala el sitio.

Corregir la cita de `C-009` sería reescribir trabajo ajeno
(`COORDINACION.md:184`), así que se informa en vez de arreglar.

## `ERROR` 2 · `030` invierte los valores de `PDB2` y `PDB1`

`030-page-walker-gfx8-2-niveles.md:83` afirma:

```
   Con block_size=22:  PDB2→31,  PDB1→40,  PDB0→22,  PTB→0
```

La fórmula está en `amdgpu_vm_pt.c:58-59` y es `9 * (AMDGPU_VM_PDB0 - level) +
block_size`. El `enum` (`amdgpu_vm.h:191-197`) numera `PDB3=0, PDB2=1, PDB1=2,
PDB0=3, PTB=4`, y la cabecera de `PDB3` es el **mayor**, que es lo que hace que
`PDB0 - level` no dé negativo. Sustituyendo:

```
   PDB3=0 -> 9*(3-0)+22 = 49
   PDB2=1 -> 9*(3-1)+22 = 40
   PDB1=2 -> 9*(3-2)+22 = 31
   PDB0=3 -> 9*(3-0...)  = 22
   PTB     -> 0            (return explicito, amdgpu_vm_pt.c:60-61)
```

`PDB2` da **40** y `PDB1` da **31**: están intercambiados en `030`. `PDB0` y `PTB`
sí coinciden. El error es de aritmética, independiente del valor de `block_size`:
con `block_size=10` los valores serían 28 y 19, y el orden sigue siendo el
contrario del que dice `030`.

`030` también omite `PDB3`, cuyo turno es 49 con `block_size=22`, o sea más allá
de `max_bits=40`. Es la razón de que `num_level` esté acotado por `max_level`
(`amdgpu_vm.c:2428`), y por tanto `PDB3` es inalcanzable en esta GPU.

**Alcance de este error.** La tabla entera de `030` se calcula con
`block_size=22`, que `C-009` ya refutó a favor de 10, así que sus cifras están
bajo un dato retirado. El intercambio `PDB2`/`PDB1` es un error real pero de
segundo orden: no cambia el título de `030` ("2 niveles"), que sigue siendo
correcto, porque `num_level = 1 → PDB0 → PTB` son dos niveles con cualquiera de
los dos `block_size`. Se registra porque el orden relativo de los niveles sí es
estructural, no una consecuencia del `22`.

## Estado

| Afirmación | Estado | Contada como |
|---|---|---|
| `num_level = 1 → root_level = PDB0` | `PROVEN` (3 vías, desde `C-009`) | ya registrada, **no** nueva |
| `amdgpu_vm.c:2438` no contiene la afirmación que `C-009` le atribuye | `PROVEN` | `ERROR` nuevo |
| `PDB2→40` y `PDB1→31`, no al revés | `PROVEN_DERIVED` | `ERROR` nuevo |
| `PAGE_TABLE_DEPTH = 0/1` (sentido del campo MMIO de 2 bits) | `NOT_DETERMINED` | fuera de alcance |

Sobre `F3`: lo que se investigó aquí es la **profundidad** del page walker
(`num_level`, `root_level`), que es otra cosa. `F3` sigue `NOT_DETERMINED` y este
hallazgo **no la cierra**. Se comprobó el nombre antes de concluir: `PAGE_TABLE_DEPTH`
llegó a un nombre que existe, y su campo de 2 bits es un asunto distinto del
`switch` de niveles.

## Cómo se encontró, y por qué importa el método

Se rastreó `root_level` buscando quién **lo escribe**, no dónde se lo menciona.
El `grep` da 26 apariciones en 8 ficheros y no las ordena por uso. La herramienta
`xref.py` las clasifica en `WRITE`/`READ` y sale que hay **4 escrituras, todas en
el mismo `switch` de 16 líneas** (`amdgpu_vm.c:2429-2444`). Eso convierte "dónde
se mentiona" en "quién decide", que es la pregunta que `F3` necesitaba.

El mismo rastreo cometió un error propio que la herramienta detectó: se pidió el
símbolo `level_shift`, que no existe, porque el símbolo real es
`amdgpu_vm_pt_level_shift`. `\b` no corta dentro de un identificador. Eso es la
 clase de error **(a) `NAME_NOT_FOUND` tratado como ausencia**, y se ha repetido
cuatro veces
hoy. La herramienta ahora responde "NINGUN sitio con ese NOMBRE EXACTO, pero la
cadena aparece dentro de 2 símbolos" en vez de afirmar que no existe.

## `ERROR` 3 · la notación en cadena de `C-009` es ambigua (menor, pero es la causa del 1)

La cita de arriba se reproduce **verbatim**, incluida su ambigüedad: un `:2438`
que sigue a `CONTRADICTIONS.md:512` puede significar la línea 2438 de ese
documento, o la línea 2438 del fichero de código del que se está hablando. El
lector tiene que saber cuál, y el texto no lo dice.

Es un tercer defecto, de los tres el más pequeño, pero explica por qué el
anclaje está desplazado: quien escribió la cadena raisó `:2438` desde la
numeración de `amdgpu_vm.c` sin dejar constancia de a qué fichero pertenecía, y
el deslizamiento no tenía dónde detectarse.

**Aviso propio y deliberado.** Al verificar este documento con `citecheck.py`,
el `:2438` se marca `LINE_OUT_OF_RANGE` contra `CONTRADICTIONS.md` en **4 sitios**
(L38 en la cita textual, y L141, L146 y L157 al explicarla). **Esos 4 avisos se
esperan y no se corrigen**, porque la ambigüedad es el objeto del hallazgo: aquí
el `2438` es de `amdgpu_vm.c`, y la herramienta sólo puede heredar el último
fichero nombrado, que aquí es el `.md`. Se deja la cita textual con sus tres
líneas porque transcribirla sin la ambigüedad falsearía la evidencia.

Recuento verificado, no estimado: **25 citas comprobadas, 21 resueltas, 4
problemáticas, y las 4 son la misma ambigüedad**. Con `--skip-fences` son 18
citas y las 4errepermanecen, porque la mitad de ellas está en prosa y no en el
bloque de código. Ese flag no es la solución aquí; sólo lo es cuando lo que hay
dentro del fence es un ejemplo, y aquí es una transcripción.

## Herramientas usadas, y sus límites demostrados

`citecheck.py` verificó 25/25 citas de `CONTRADICTIONS.md` y reportó **0
problemáticas**. El `:2438` erróneo **pasa** ese filtro. No es un fallo: el filtro
comprueba que la línea exista, no que diga lo que la cita afirma. Lo demuestra en
vez de esconderlo, y por eso `--context` imprime la línea real: el defecto se ve
en un segundo.

Esa división se ve también en el caso inverso, con `030`: sus citas apuntan a
líneas que existen (`amdgpu_vm.c:2410-2411` es un comentario, no la asignación),
as que el filtro las acepta igual. Dos documentos, dos defectos, cero
detectados automáticamente, todos dos visibles con `--context`.

Sin la herramienta, estas dos citas se habrían reusado tal cual desde `C-009`.
Con ella, se corrigen sin abrir nada.

## Procedencia

- `CORPUS` — `amdgpu_vm.c`, `amdgpu_vm.h`, `amdgpu_vm_pt.c` (7.1.3).
- `SEMI_PRIMARY` — `CONTRADICTIONS.md`, `030`, `FINDINGS-INDEX.md`.
- Sin `RUNTIME`, sin lectura de la GPU, sin cambio en la máquina.
- No se editó `C-009` ni `030`: son de otras sesiones (`COORDINACION.md:184`).
