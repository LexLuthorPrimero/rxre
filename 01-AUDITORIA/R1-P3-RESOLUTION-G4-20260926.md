# R1-P3-RESOLUTION-G4-20260926

`DOCUMENT_KIND = RESEARCH` + `DEFINITION_RESOLUTION` · `NORMATIVE_STATUS = RESEARCH_ONLY`
Resuelve **G-4** y el hallazgo **S-1**. Complementa —no sustituye ni reescribe—
`R1-ATTRIBUTION-DECOMPOSITION-MODEL-20260926.md` (§1, §2, §6, §7, §8 quedan ampliados por este).
`CODE_CHANGE_ALLOWED = NO` · `MODEL_DESIGN_ALLOWED = YES` · collector/tests/AGENTS/README sin tocar.

---

## 1 · P3_DEFINITION

**P3 se divide.** La pregunta original ("¿se puede atribuir la evidencia al cliente?") mezclaba
**conformidad del texto** con **capacidad del analizador**. Son propiedades distintas, con
distintos Producers, distinta unidad y distinto falsificador.

| | `P3A · DRM_CLIENT_FDINFO_COMPLIANCE` | `P3B · DRM_CLIENT_IDENTITY` |
|---|---|---|
| `DEFINITION` | El fdinfo observado cumple las claves que el driver decidió exportar | El analizador dispone de `drm-client-id` suficiente para **identificar** y **discriminar** clientes DRM según la semántica documentada |
| `UNIT` | **fdinfo** (un texto por FD) | **`drm_file`** (el cliente DRM) |
| `SOURCE` | `drm-usage-stats`: *"Mandatory fully standardised keys: `drm-driver`"*. `drm_file.c:drm_show_fdinfo()` imprime `drm-driver` y `drm-client-id` **sin condición**; `drm-pdev` **ssi** `dev_is_pci()` | `drm-usage-stats`: `drm-client-id` *"maps 1:1 to … `struct drm_file`"*; `drm_file.c`: `file->client_id = atomic64_inc_return(&ident)` en `drm_file_alloc()` |
| `PRODUCER` | presencia/ausencia de `drm-driver` (y del prefijo estándar) en el texto leído | extracción del **valor** de `drm-client-id` por FD, y conjunto de valores **distintos** por nodo |
| `CONSUMER` | ninguno hoy — P3A no alimenta ninguna decisión | `card_clients`/`render_clients` (`:2869-2870`) y, semánticamente, las dos filas de nodo |
| `OBSERVABILITY` | `HIGH` — es lectura directa del texto | `MEDIUM` — observado 12/12 en el barrido, **sin texto crudo preservado** en ningún bundle |
| `PROVENANCE` | `EXTERNAL_SPEC` + `KERNEL_IMPLEMENTATION` | `EXTERNAL_SPEC` + `KERNEL_IMPLEMENTATION` |
| `STATUS` | `ESTABLISHED` | `ESTABLISHED` la relación · el **umbral** sigue `REQUIREMENT_UNRESOLVED` (G-1) |

### 1.1 Hallazgo que refina la premisa de G-4

`drm-client-id` está clasificado `Optional fully standardised` en la spec, y eso es correcto **a
nivel de driver** (un driver puede no implementar `.show_fdinfo` en absoluto). Pero **dentro de la
implementación estándar**, `drm_show_fdinfo()` lo imprime **incondicionalmente** para todo fichero
DRM. Por tanto:

> **`drm-client-id` ausente, con `fdinfo` legible y no vacío ⇒ el driver NO usó
> `drm_show_fdinfo()`** — es decir, expone un fdinfo no estándar, o ninguno.

Esto es compatible con la resolución de G-4: **la ausencia no es `FAIL` de conformidad por la
clave opcional**, pero sí es **diagnóstica** de que el prefijo estándar del core no está. P3A
registra ese hecho; P3B registra su consecuencia. Ninguna de las dos lo convierte en veredicto.

### 1.2 P3B se subdivide a su vez: `PRESENCE` ≠ `DISCRIMINATION`

El enunciado de G-4 juntaba "identificar/deduplicar". Son dos capacidades distintas, y **el
código actual solo tiene una**:

| | `P3B-1 PRESENCE` | `P3B-2 DISCRIMINATION` |
|---|---|---|
| Pregunta | ¿hay al menos un `drm-client-id` en este FD? | ¿cuáles clientes **distintos** hay, y cuántos? |
| Insumo necesario | **presencia** de la clave | **el valor** de la clave |
| Estado actual | **IMPLMENTADO** (`any()`, `:2783`) | **NO IMPLEMENTADO** |
| Razón | `fdinfo_attribution` devuelve `{name: bool}` — *"Presence only, never a value"* (`:1041-1051`) | el valor se descarta; hacer el recuento de distintos exige un extractor de valor |
| Implicación F-02 | `card_clients` hoy cuenta **FDs con la clave presente** | "nº de clientes" **no es computable hoy** |

**El valor es recuperable de la evidencia ya recolectada**: cada entrada de `gpu_clients` guarda el
texto completo (`"fdinfo": match.get("fdinfo")`, `:2467`). No hace falta un campo nuevo, sí un
**helper que devuelva el valor**. Es una nota de implementación; **no se implementa aquí**.

---

## 2 · P3_UNIT

`drm_file` — un `struct drm_file`, no un FD, no un proceso, no un `drm_master`.
El FD es **la vía de observación**; `drm-client-id` es **el valor observado**; la unidad es
`drm_file`.

`OBSERVED` vs `INFERENCE`: que la clave esté presente es `OBSERVED`; que ese valor *identifique un
`drm_file`* es `INFERENCE` de la spec, no lectura directa del host.

---

## 3 · Estados de P3B

Cada estado nombra **qué se midió**, no qué Conclusion se↓
extrae.

| Estado | Condición exacta | Qué NO significa | Falsificador |
|---|---|---|---|
| `PRESENT` | fdinfo legible ∧ `drm-client-id:` presente ∧ **valor distinto** por cliente | que el host esté "limpio"; que el proceso sea correcto | que dos `drm_file` distintos compartieran el mismo `client_id` |
| `ABSENT` | fdinfo legible ∧ `drm-client-id:` **no presente** | **no** es `FAIL` de conformidad (G-4); **no** significa "el driver es inválido" | que el driver estándar pudiera omitirlo |
| `READ_ERROR` | fdinfo **no** legible / lectura falló / FD desapareció | **no** es `ABSENT`: aquí se **desconoce**; reportarlo como ausencia es el error que `AGENTS.md` prohíbe | que una lectura fallida pudiera observarse como ausencia |
| `EMPTY_UNIVERSE` | **0 FDs** observados en el nodo | **no** es `PASS` de identidad (S-1); **no** es evidencia positiva de nada | — |
| `NO_DRM_FD` | el proceso/proceso-barrido no tiene ningún FD DRM en absoluto | ≠ `EMPTY_UNIVERSE`: es un hecho sobre el **universo barrido**, no sobre el nodo | — |
| `UNKNOWN` | no se pudo determinar (p. ej. `gpu_proven` falso: no sabemos que el nodo sea la RX550) | no es `ABSENT` | que `gpu_proven` fuera innecesario para decidir P3B |

`EMPTY_UNIVERSE` y `NO_DRM_FD` están separados a propósito: un proceso con FDs **solo** en `card1`
tiene `EMPTY_UNIVERSE` en `renderD129` y **no** `NO_DRM_FD`.

### 3.1 P3_PASS

> **P3B PASS = ∀fd ∈ nodo : fdinfo(fd) legible ∧ `drm-client-id` presente, ∧ el nº de
> `client-id` distintos es computable.**

Es una afirmación sobre **la cobertura de nuestra evidencia**, no sobre la Virtud del host.
**No certifica que la RX550 esté en paz.** Nombrarlo `IDENTITY` invita a leerlo como hecho del
host; el nombre correcto sería `IDENTITY_EVIDENCE_SUFFICIENT`. Registrado como defecto S-6.

### 3.2 P3_EMPTY

`EMPTY_UNIVERSE` = 0 FDs en el nodo. **Distinto de PASS y de FAIL.**

Razón: `∀fd: P(fd)` sobre conjunto vacío es vacuamente cierto, y esa verdad dice algo del
**universo**, no de la **propiedad**. Convertirlo en `PASS` es *evidence-of-availability leído de
ausencia de evidencia* — exactamente el vicio que `AGENTS.md` §Measurement discipline prohíbe.

**No se mapea `EMPTY_UNIVERSE` a ningún estado de la matriz todavía.** El mapeo **es** la semántica
de la fila, y la semántica de la fila es **G-1**. Registrar el token y withholding del mapeo.

### 3.3 P3_ABSENT

`ABSENT` es un hecho de **observación**: la clave no estaba. Se propaga como `ABSENT`, no como
`FAIL`. `P3A` es quien juzga si eso es o no conformidad.

### 3.4 P3_READ_ERROR

`READ_ERROR` es **evidencia incompleta**, y debe viaja como tal: nunca colapsado a `ABSENT` ni a
vacío. Es el estado que un error tragado convertiría en `ABSENT` — el segundo vicio de
`AGENTS.md`. El collector ya lo hace bien: `"fdinfo": match.get("fdinfo")` conserva el texto
vacío y `:2782` distingue explícitamente el valor vacío de un campo ausente.

### 3.5 P3_UNKNOWN

`UNKNOWN` = no se pudo determinar la propiedad. Se alcanza cuando `gpu_proven` es falso
(`ownership_matrix:1702` ya devuelve `NOT_EVALUATED` en ese caso — correcto, y es el precedente
que P3B debe seguir). **Nunca se convierte en `PASS`.**

---

## 4 · F02_UNIT_ANALYSIS

### 4.1 Las dos relaciones, con fuente primaria

| Relación | Mecanismo kernel | Valor observado | Consecuencia |
|---|---|---|---|
| **2 FDs → 1 `drm_file` → 1 `client-id`** | `dup()`, `fork()`: el `struct file` se comparte → `file->private_data` (el `drm_file`) es el **mismo objeto** | **el mismo** `drm-client-id` en ambos FDs | contar FDs **sobrecuenta** clientes |
| **2 `drm_file` → mismo PID → 2 `client-id`** | dos `open()` → dos `drm_file_alloc()` → dos `atomic64_inc_return(&ident)` | **dos** `drm-client-id` distintos, un solo PID | contar PIDs **subcuenta** clientes |

Ambas son `ESTABLISHED` (`KERNEL_IMPLEMENTATION`, `drm_file.c`).

### 4.2 Conteo por unidad — la tabla que faltaba

| Unidad que se contara | 2 FDs → 1 `drm_file` | 2 `drm_file` → mismo PID | Veredicto |
|---|---|---|---|
| **FD** (lo que hace hoy) | 2 | 2 | ✗ **incorrecto** en la primera columna |
| **PID** | 1 | 1 | ✗ **incorrecto** en la segunda columna |
| **`drm_file` / `client-id`** | 1 | 2 | ✓ correcto en ambas |

**Ninguna unidad basada en el path `/proc/<pid>/fd/<n>` puede ser correcta**: ese path no
distingue un `drm_file` de otro.

### 4.3 Estado actual, verificado

`card_clients` (`:2869`) = `node_attributable[card]` = nº de **FDs** que pasan `any()`.
Se consume en `:1721` como `f"{context['card_clients']} attributable client(s)"`.
→ **La etiqueta dice "clients", la unidad es FDs.** `F-02` confirmado, y el nombre sigue
sospechoso, como se pidió.

### 4.4 Modelo semántico correcto para `card_clients` / `render_clients`

```
card_clients  :=  |{ drm-client-id(fd)  :  fd ∈ FDs(card1),  legible ∧ clave presente }|
render_clients := |{ drm-client-id(fd)  :  fd ∈ FDs(renderD129), legible ∧ clave presente }|
```

- **Unidad**: `drm_file`, por su `client-id`.
- **Conjuntos disjuntos**: un `drm_file` tiene **un** `minor` (`drm_is_primary_client()` compara
  `file->minor` contra el primary) ⇒ ningún cliente aparece en ambos nodos.
- **Requiere el VALOR**, no la presencia ⇒ `P3B-2`, hoy no implementado.
- **Vacío**: el conjunto vacío significa "0 clientes observados", y **no** "atribución completa".

### 4.5 Nota de implementación (NO ejecutada)

La deduplicación no necesita campo nuevo — `gpu_clients` ya guarda el texto por FD (`:2467`).
Sí necesita un helper que devuelva el **valor**, porque `fdinfo_attribution` está escrita
explícitamente como *"Presence only, never a value"* (`:1041`). `CODE_CHANGE_ALLOWED = NO`:
registrado, no ejecutado.

---

## 5 · G1_STATUS · G2_STATUS

| | `STATUS` | Nota |
|---|---|---|
| **`G-1`** ¿la fila exige evidencia de **cliente**? | **`REQUIREMENT_UNRESOLVED`** | G-4 no lo respondió. G-4 respondió *cómo se mide* P3B, no *si la fila lo exige*. P3B queda definido y medible, **sin verdict en la fila**. `AGENTS.md:176-179` no lo dice. |
| **`G-2`** ¿la fila exige evidencia de **proceso**? | **`REQUIREMENT_UNRESOLVED`** | **No colapsada con G-1.** P4 sigue siendo una propiedad separada, con Producer distinto (el path `/proc/<pid>/fd/<n>`, no fdinfo). Que P3B se defina no implica nada sobre P4. |

Ambos siguen siendo **la misma pregunta abierta**, con la diferencia de que ahora **la capacidad
de medirlos existe y está descrita**, y lo que falta es solo la decisión humana de exigirlos.

---

## 6 · UPDATED_MODEL — cambios respecto de `R1-ATTRIBUTION-DECOMPOSITION-MODEL`

| antes | ahora |
|---|---|
| `P3 DRM_CLIENT_IDENTITY` (única) | `P3A DRM_CLIENT_FDINFO_COMPLIANCE` + `P3B DRM_CLIENT_IDENTITY` |
| `PASS` = "todo FD tiene ≥1 de 3 campos" | **retirado**: no es una propiedad, es un híbrido de cuantificadores |
| `PASS` = "todo FD tiene `drm-client-id`" | `P3B-1 PRESENCE` (implementado) + `P3B-2 DISCRIMINATION` (no implementado) |
| 0 FDs → `PASS` (vacuoso) | **`EMPTY_UNIVERSE`**, token propio, **mapeo a la matriz diferido a G-1** |
| "ausencia = FAIL" | `ABSENT` ≠ `FAIL`; la conformidad la juzga P3A |
| `card_clients` = nº de clientes | nº de **FDs** — **etiqueta engañosa, confirmada** |
| `S-1` abierto | **cerrado**: el vicio está identificado, corregido en el modelo, y **no implementado** en el código |
| `P5` | `SOURCE_INCOMPLETE` **sin cambio** |

---

## 7 · UPDATED_TEST_MODEL

Se **conservan** los 16 mundos de la versión previa y se **sustituyen** los que G-4cambia:

| # | Mundo | Prueba | Cambio |
|---|---|---|---|
| 4′ | `client-id` ausente, `drm-driver` presente | **P3B = `ABSENT`**, P3A = conforme, **fila no FAIL** | era "P3 FAIL" |
| 9′ | `pasid` ausente + `client-id` presente | P3B-1 `PRESENT`; `pasid` no participa | — |
| 10′ | `pasid` presente **sin** `client-id` | P3B-1 `ABSENT`, P3A conforme | — |
| **17** | **`drm-driver` ausente, resto presente** | **P3A = no conforme**; P3B = `ABSENT` | **nuevo** |
| **18** | **`drm-client-id` ausente con `drm-pdev` presente** | P3B `ABSENT`; **`drm-pdev` no salva** la identidad | **nuevo** |
| **19** | **fdinfo ilegible** | `READ_ERROR`, **no** `ABSENT`, **no** vacío | **nuevo** |
| **20** | **0 FDs en el nodo** | `EMPTY_UNIVERSE` ≠ `PASS` | **nuevo** |
| **21** | **0 FDs DRM en todo el barrido** | `NO_DRM_FD` ≠ `EMPTY_UNIVERSE` del nodo | **nuevo** |
| 7 | 2 FDs → 1 `client-id` | P3B-2 → 1 cliente; **`card_clients` hoy daría 2** | fija F-02 |
| 8 | 2 `drm_file` → mismo PID | P3B-2 → 2 clientes | fija F-02 |

Los mundos 1-3, 5-6, 11-16 se conservan sin cambio. Total **21**.

Los tests 19-21 son los que **ejecutan el vicio S-1**: sin ellos, un `0 == 0` sigue leyéndose
como `PASS`.

---

## 8 · SELF_CRITIQUE

Defectos encontrados **en este mismo documento**, corregidos antes de entregarlo:

- **S-6** · Llamé `P3B` "IDENTITY" cuando su PASS afirma cobertura **de nuestra evidencia**, no
  un hecho del host. El nombre invitaba a leerlo como certificación. **Corregido**: el nombre
  correcto es `IDENTITY_EVIDENCE_SUFFICIENT`; el PASS queda enunciado como afirmación de cobertura.
- **S-7** · Acepté de entrada el enunciado de G-4 ("identificar/deduplicar") como una sola
  capacidad. No lo es: presencia y discriminación necesitan **insumos distintos** (bool vs string).
  **Corregido**: `P3B-1`/`P3B-2`, y F-02 se explica por esa misma razón.
- **S-8** · Casi colapsé `EMPTY_UNIVERSE` y `NO_DRM_FD` bajo "universo vacío". **Corregido**:
  son hechos sobre universos distintos (el nodo vs el barrido) y tienen falsificadores distintos.
- **S-9** · En §1.1 casi presenté "el core lo imprime sin condición" como si **invalidara** la
  resolución de G-4. No la invalida: la clave sigue siendo opcional **a nivel de driver**. Es un
  dato **diagnóstico**, y lo registré como tal, no como motivo de `FAIL`.
- **S-10** · `P3A` podría leerse como "¿el driver es válido?", que es una pregunta de juicio de
  terceros. **Corregido**: `P3A` pregunta solo si el **texto observado** cumple las claves
  declaradas; no emite juicio sobre el driver.
- **S-11** · Afirmé "conjuntos disjuntos" para `card_clients`/`render_clients` apoyándome en
  `drm_is_primary_client()`. Eso es `INFERENCE` sobre una regla de un minor, no una lectura
  medida en este host. Lo marqué como tal.

**No encontré** otra mezcla de propiedades, ni `pasid`/memoria/engine convertidos en atribución de
proceso, ni dependencia accidental card↔render. **G-1/G-2 no fueron tocados** — la resolución de
G-4 no los responde y no se absorben.

---

## 9 · OPEN

1. **G-1** — ¿la fila de nodo exige `P3B`? Define también el mapeo de `EMPTY_UNIVERSE`.
2. **G-2** — ¿la fila de nodo exige `P4`? Independiente de G-1.
3. **S-1/§3.2** — token `EMPTY_UNIVERSE` existe; su `STATE` en la matriz depende de G-1.
4. **`P3B-2` / F-02** — el recuento de clientes distintos **no es computable hoy**.
5. **C-1/C-2** — colisiones de "client", `CONFLICT_UNRESOLVED` en upstream.

## 10 · BLOCK

- **`P3B-2` y F-02** — requieren código (`CODE_CHANGE_ALLOWED = NO`).
- **`P5`** — `SOURCE_INCOMPLETE`. No se buscan más fuentes: la taxonomía ya es honesta sin ellas.
- **`P6/P7 → proceso`** — límite de la spec, no bloqueo.

## 11 · EVIDENCE

- `drm_file.c:drm_show_fdinfo()` — `drm-driver` y `drm-client-id` **incondicionales**; `drm-pdev`
  **ssi** `dev_is_pci()`. `drm_file_alloc()` — `client_id = atomic64_inc_return(&ident)`.
  Fuente: Torvalds/linux, `drivers/gpu/drm/drm_file.c`, leido en la fase anterior.
- `drm-usage-stats` — `drm-driver` *Mandatory*; `drm-client-id` *Optional*, *"maps 1:1 to …
  `struct drm_file`"*; `drm-engine-<key>` *"belonging to this client"*, *"not required to be
  constantly monotonic"*.
- `privileged_read_collector.py` `e1f732ea` — `:1033` tupla de 3 campos · `:1041-1051`
  *"Presence only, never a value"* · `:2467` texto fdinfo por FD · `:2783` `any()` ·
  `:2788-2789` igualdad por nodo · `:2869-2870` contadores · `:1721-1722` etiqueta "client(s)".
  **Sin modificar.**
- `AGENTS.md` `a8b8ae64…` — sin modificar en esta fase.
