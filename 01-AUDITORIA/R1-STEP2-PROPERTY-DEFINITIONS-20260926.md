# R1-STEP2-PROPERTY-DEFINITIONS-20260926

`DOCUMENT_KIND` = `PROPERTY_DEFINITION` · `STEP` = 2 · `CODE_CHANGE` = **no aplicado** (ver §4)
Define las dos propiedades del Paso 2 **antes** de codificar, como el paso exige.
`PROJECT_MAPPING` = `NOT_ATTEMPTED` · `CODE_CHANGE_ALLOWED` = `NO` en esta entrega.

Fuente semántica: `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` (`RT-1`, `RT-3`) sobre
`R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` (`CLOSED`).

---

## `P-COVERAGE` · `*_coverage_complete` (implementable ahora)

| | |
|---|---|
| Entidad | la tabla de descriptores de un nodo DRM, tal como se observa en un barrido completo |
| Unidad | **descriptor** (individual) · **proceso** (agregado) |
| Fuente | `/proc/<pid>/fd` y `readlink`. **Ninguna clave de fdinfo** |
| Observa | si el universo de procesos pudo enumerarse y cada descriptor quedó resuelto |
| **NO demuestra** | nada sobre `drm_file`, `drm-client-id`, `drm-pdev`, `pasid`, memoria, engine, ni identidad de cliente |
| Estados | `PASS` / `FAIL` / `NOT_EVALUATED` (si `gpu_proven` es falso) |
| PASS | `root_visibility_complete`: 0 fd denegados, 0 otros errores de fd, 0 permisos de la corrida, 0 previos sin resolver |
| Falsificador | un descriptor sin resolver que no degradara la propiedad; o que `PTRACE_MODE_READ_FSCREDS` no gobernara esa lectura |
| Límite de observabilidad | **no existe contador de descriptor-no-resuelto por nodo**: `root_fd_error_count` es global. La parte de nodo es **`NOT_INDEPENDENTLY_MEASURED`** y **no se inventa** |
| Provenance | `PRIMARY_KERNEL_SOURCE` (semántica) + `HUMAN_REQUIREMENT` (*"complete"*) + `AGENT_FORMALIZATION` (el flag) |

**Comparación entre nodos — justificada, no fabricada**: coverage comparte `root_visibility_complete`
entre card y render **legítimamente**, porque es propiedad **del barrido y del dispositivo**, no de
qué nodo se mira. No se fabrica un término de nodo para simular independencia. La independencia real
está en que coverage **no comparte campo alguno** con `P-CLIENT-ID`, y en que cada una se reporta y
consumible por separado.

## `P-CLIENT-ID-PRESENCE` · `*_client_id_presence` (implementable ahora)

| | |
|---|---|
| Entidad | los descriptores DRM resueltos a un nodo |
| Unidad | **FD**. **Cuenta DESCRIPTORES, no clientes**: un `drm_file` puede alcanzarse por varios FDs |
| Fuente | clave `drm-client-id:` en `/proc/<pid>/fdinfo/<n>`, buscada por **presencia**. **No se lee el valor** |
| Observa | si **todos** los descriptores del nodo llevan la clave |
| **NO demuestra** | identidad de cliente · discriminación entre `drm_file` · cantidad de clientes · asociación a proceso · `drm-pdev` · `pasid` · memoria · engine |
| Estados | `PASS` (todos, y ≥1 FD) · `PARTIAL` (algunos) · `FAIL` (ninguno, con fdinfo legible) · **`UNKNOWN` con 0 FDs** · `NOT_EVALUATED` |
| PASS | `present == fd_count` y `fd_count > 0` |
| Falsificador | un `drm-client-id:` presente que la búsqueda no encuentre; o un nodo con todos sus FDs legible y uno sin resolver |
| Límite de observabilidad | la clave la emite el core **incondicionalmente** dentro de `drm_show_fdinfo`; su ausencia en un fdinfo legible es un hecho **del texto**, no un recuento de clientes |
| Provenance | `PRIMARY_KERNEL_SOURCE` (`drm_file.c:142`, `drm_show_fdinfo`) + `AGENT_FORMALIZATION` (el roll-up por nodo) |

**0 FDs → `UNKNOWN`, nunca `PASS`**: `0 == 0` es cierto sobre el **universo**, no sobre la propiedad.
El token dedicado (`EMPTY_UNIVERSE`) es una decisión de nivel de proyecto y **no se introduce aquí**.

## `*_client_identity` · `TECHNICAL_DEFINITION_REQUIRED` — NO implementada

**No se inventa.** Dos motivos, ambos técnicos:

1. Requiere el **valor**. `fdinfo_attribution` (`:1041-1051`) está escrita *"Presence only, never a
   value"*; sin valor no hay `DISCRIMINATION`, y la unidad de la propiedad es el `drm_file`.
2. El **alcance de la unicidad** está `CONFLICT_UNRESOLVED` (`C-4`): la spec admite unicidad **global**
   o **por dispositivo**, y en el segundo caso la identidad correcta es el **par
   `(drm-pdev, drm-client-id)`**. Decidir cuál aplica es una pregunta sobre el comportamiento del
   kernel, no una decisión de proyecto, y la spec no la resuelve.

Por eso la propiedad se llama `*_client_id_presence` y no `*_client_identity`: el nombre no puede
exceder la evidencia (`AGENTS.md:40-48`).

## 4 · Por qué el código no se aplicó

El cambio se implementó y se midió: **60 fallos** (8 `FAIL`, 52 `ERROR`), casi todos `KeyError`
porque **14 sitios de fixture** en 6 archivos construyen `root_coverage` y  supplying them las claves
nuevas:

`test_collector_failure_modes.py:485` · `test_medium_fixes.py:459` ·
`test_med_review_classifications.py:361,432,550,727,993,1025,1053` ·
`test_privileged_read_collector.py:143` · `test_r1_defects.py:406` ·
`test_drm_fds_enumerated_behavioral.py:76` · `test_defect04_behavioral.py:248` (`matrix_context`)

El collector se revirtió a `73720e714b29613f1f82cbfbda776627a352d80faf519a51f8b4b5d30d5333c2`,
**byte-idéntico** al estado post-Paso-1, y la suite volvió a `OK`. Dejar 60 tests en rojo es peor que
una parada documentada, y **no** se cambió el diseño para que los tests pasaran.

**No se usa `.get()` con valor por defecto**: `DEFECT-04` estableció que una clave faltante debe ser
un fallo ruidoso, y un default la convertiría en `"across 0 PIDs"`.

## 5 · Clasificación de problemas

| Problema | Clase |
|---|---|
| `*_client_identity` no implementable con la evidencia actual | **`TECHNICAL_DEFINITION_REQUIRED`** |
| 14 fixtures × 6 archivos requieren las claves nuevas | **`LIMITATION`** de alcance, no defecto |
| `card_clients`/`render_clients` siguen contando FDs con etiqueta "clients" | **`NOT_A_DEFECT`** aquí: es el paso 4, ya planificado |
| Ausencia de contador de descriptor-no-resuelto por nodo | **`LIMITATION`** — declarado, no inventado |
| 0 FDs no puede ser `PASS` | **`NOT_A_DEFECT`** — corregido en el diseño antes de codificar |

## 6 · Medición de la migración (verificada, 2.º intento)

**12 sitios de fixture** necesitan **10 claves nuevas** cada uno. Ninguno requiere inventar un mundo
de test: **toda clave nueva es derivable de contadores que el fixture ya declara.**

| Sitio | Claves heredadas que debe retirar |
|---|---|
| `test_collector_failure_modes.py:485` | `card_complete`, `render_complete`, `card_clients`, `render_clients` |
| `test_medium_fixes.py:459` | ídem |
| `test_privileged_read_collector.py:143` | ídem |
| `test_r1_defects.py:406` | ídem |
| `test_med_review_classifications.py:432, 550, 727, 993, 1007, 1025` | ídem |
| `test_med_review_classifications.py:886` | `card_complete` |
| `test_defect04_behavioral.py:248` (`matrix_context`) | `card_clients`, `render_clients` |
| `test_privileged_read_collector.py:136` (base) | `card_complete`, `render_complete` |

### Regla de derivación — ninguna clave exige un valor inventado

| Clave nueva | Se deriva de |
|---|---|
| `*_coverage_complete` | los 4 términos que el fixture **ya** declara: `root_fd_permission_denied == 0`, `root_fd_other_errors == 0`, `current_run_permission_denied` falso, `unresolved_prior` vacío |
| `*_client_id_presence` (+`_reason`) | `node_client_id_presence_state(drm_fds_found, drm_client_id_seen, node, True)` — la función de producción, con los dos contadores que el fixture ya declara |
| `*_drm_fds` | `drm_fds_found` |
| `*_client_id_fds` | `drm_client_id_seen` |

**Consecuencia**: la migración es mecánica y no cambia ningún mundo de test. El coste es de
redacción, no de semántica. La forma correcta es que **cada fixture exponga la derivación de forma
visible** —no un `.get()` con default en producción, que `DEFECT-04` prohíbe, ni un valor fijo que
ocultaría el mundo—.

### Punto 6 — la corrección de nombres no puede hacerse aislada

`card_clients` / `render_clients` deben renombrarse (unidad **FD**), pero su valor aparece en la
cadena de evidencia de `ownership_matrix:1723-1724` como `"... attributable client(s)"`, y esa cadena
la pinnan tests de `test_med_review_classifications.py`. Renombrar el contador sin tocar la cadena
deja la etiqueta mintiendo; tocar la cadena sin los fixtures rompe la suite. **El rename va en el
mismo commit lógico que el consumer y los fixtures.**

---

# 7 · REVISIÓN SEMÁNTICA CORREGIDA (2.º intento)

`READ_ONLY` salvo este documento. No se reabrió la intención humana, el modelo técnico ni ninguna
decisión de proyecto. No se añade capa: dos de las propiedades de §7 **consumen contadores que ya
existen** y que el Paso 1 dejó sin leer.

## 7.1 Tabla de corrección de nombres

| `NOMBRE_ACTUAL` | → `NOMBRE_CORREGIDO` | Qué representa | Unidad | Fuente | `ESTADO_SEMÁNTICO` | ¿CAMBIO DE CÓDIGO? | Motivo |
|---|---|---|---|---|---|---|---|
| `card_complete` / `render_complete` | `*_coverage_complete` | cobertura del universo de FDs | descriptor / proceso | `/proc/*/fd` | `ESTABLECIDO` | **sí** | el nombre promete una conjunción que no es suya |
| `node_attributable` | *(eliminar)* | — | — | — | `NO_APLICA` | **sí** | alimentaba `any()` sobre 3 dominios; no es una propiedad |
| `any(fdinfo_attribution(...).values())` | *(eliminar)* | — | — | — | `NO_APLICA` | **sí** | predicado de atribución compuesta |
| `card_attributable` / `render_attributable` | *(eliminar)* | — | — | — | `NO_APLICA` | **sí** |ributors: era el término de atribución de la fila |
| `drm_fds_found` (pooled) | `*_drm_fd_presence` | FDs DRM resueltos al nodo | **FD** | symlink `/proc/*/fd` | `ESTABLECIDO` | **sí** | el nombre no decía la unidad |
| `drm_fdinfo_read` (pooled) | `*_drm_fd_readability` | de esos, cuántos tienen su fdinfo se leyó | **FD** | fdinfo no vacío | `ESTABLECIDO` | **sí** | separado de presencia: son dos cosas |
| `drm_client_id_seen` (pooled) | `*_drm_client_id_presence` | de esos, cuántos llevan la clave `drm-client-id:` | **FD** | fdinfo | `PROPIEDAD_SEPARADA` | **sí** | presencia **no** es identidad |
| `drm_pdev_seen` (pooled) | `*_drm_pdev_presence` | cuántos llevan `drm-pdev:` | **FD** | fdinfo | `PROPIEDAD_SEPARADA` | **sí** | es del **dispositivo**, no del cliente; hoy nadie lo lee |
| `drm_pasid_seen` (pooled) | `*_pasid_presence` | cuántos llevan `pasid:` | **FD** | fdinfo | `OBSERVABILIDAD_LIMITADA` | **sí** | relación **episódica** (solo en fault); hoy nadie lo lee |
| `card_clients` / `render_clients` | `*_drm_fds` | **FD**, no clientes | **FD** | conteo | `ESTABLECIDO` | **sí** | el nombre dice clientes y el valor son FDs |
| *(nuevo)* | `*_drm_client_id_count` | nº de `drm-client-id` **distintos** | `drm_file` | **valor** | `REQUIERE_DEFINICIÓN` | **no** | nada extrae el valor; `fdinfo_attribution` es presencia-only |
| *(nuevo)* | `*_drm_file_process_association` | proceso ↔ `drm_file` | `drm_file` | `drm_file.pid` | `OBSERVABILIDAD_LIMITADA` | **no** | el campo **no se expone**; la ruta `/proc` es otra relación (RT-9) |
| `card_node_complete` / `render_node_complete` | `*_coverage_complete` (estado) | solo cobertura | descriptor | `/proc` | `ESTABLECIDO` | **sí** | ver §7.3: sin requisito explícito, **no se conjuga** |
| `clients_pasid_attributable` | *(retirar, paso 7)* | — | — | — | `NO_APLICA` | no | nominaba 3 dominios |

## 7.2 Qué es `drm-client-id`, y qué uncertainty NO le pertenece

- **Significado `ESTABLECIDO`**: identificador asociado al **`struct drm_file`**. `drm_file.c:142`
  lo asigna una vez en `drm_file_alloc`; `drm_show_fdinfo` lo emite **incondicionalmente**.
- **Presencia de la clave** = propiedad de **observabilidad**, no de identidad.
- **No** es FD, **no** es PID/TGID, **no** es PASID, **no** es el *client-id* de page fault,
  **no** es un GEM object.
- La spec permite unicidad **global** o **por dispositivo** (`C-4`). Esa incertidumbre afecta
  **solo a la clave de deduplicación** — es decir, a `*_drm_client_id_count` — y **no** al
  significado de `drm-client-id` ni a su presencia. Por eso el nombre `identity` **no** se usa:
  `drm_client_id_count` queda como `REQUIERE_DEFINICIÓN`, y la elección de clave
  (`client_id` vs par `(drm-pdev, client-id)`) queda `TECHNICAL_DEFINITION_REQUIRED` **independiente**.

`drm-pdev` es propiedad del **dispositivo PCI**, sirve para **calificar** al que pertenece el
`drm_file`, y no es una propiedad intrínseca de identidad del cliente. PASID es una relación
**episódica** (`vmid ↔ PID`, solo durante un page fault) y no completa artificialmente ninguna
identidad DRM.

## 7.3 La conjunción de la fila de nodo

`AGENTS.md:176-177` **no** nombra qué combina. `PROJECT_MAPPING = NOT_ATTEMPTED`. Por tanto la fila
`card_node_complete` **deja de conjugar** y pasa a reflejar **solo** `*_coverage_complete`, que es la
única de las dos con antecedente humano literal (*"complete"*). Las demás propiedades se **exponen y
son visibles** en la evidencia, sin afectar el veredicto. Conjunción solo cuando exista un requisito
explícito que la exija.

**Consecuencia declarada**: un nodo con cobertura completa y ningún `drm-client-id` presente pasará
la fila de cobertura y **no** la de identidad de cliente. Antes era un único veredicto compuesto. Es
un cambio de comportamiento **intencionado**, y es la consecuencia de no inventar la composición.

## 7.4 Clasificación

`ESTABLECIDO`: `*_coverage_complete`, `*_drm_fd_presence`, `*_drm_fd_readability`,
`drm_client_id_presence`, `*_drm_pdev_presence`, `*_drm_fds`.
`PROPIEDAD_SEPARADA`: las tres de presencia por nodo, antes fundidas en `any()`.
`OBSERVABILIDAD_LIMITADA`: `*_pasid_presence` (episódica), `*_drm_file_process_association` (campo no expuesto).
`REQUIERE_DEFINICIÓN`: `*_drm_client_id_count` (falta el valor), clave de deduplicación (`C-4`).
`NO_APLICA`: `node_attributable`, `any()`, `*_attributable`.
