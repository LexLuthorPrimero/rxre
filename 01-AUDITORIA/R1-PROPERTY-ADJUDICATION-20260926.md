# R1-PROPERTY-ADJUDICATION-20260926

`DOCUMENT_KIND` = `PROPERTY_ADJUDICATION` · **READ_ONLY** · sin cambios de código ni semántica normativa
`TECHNICAL_MODEL_STATUS` = `CLOSED` (sin modificar) · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`HUMAN_REQUIREMENT_STATUS` = `MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION`
`HUMAN_MIXED_TERM` = `RETIRED_AS_SINGLE_PROPERTY` · `PASS_FAIL` = `NOT_DEFINED` · `ANY_ALL` = `NOT_DECIDED`

## 0 · ERROR QUE ESTA RONDA CORRIGE

Las 11 propiedades fueron presentadas como «la descomposición normativa» del requisito. Eso
**reimportaba la formalización del agente como si fuera el requisito humano**, que es exactamente
el defecto que la descomposición debía eliminar. Aquí cada propiedad se **adjudica** contra el único
texto humano verificado, y el resultado es que **la superficie normativa humana es mucho menor que
11**.

**Único texto humano disponible**: `AGENTS.md:170-183` (criterio de `OWNERSHIP`). No se infiere
intención adicional. Nada de «presumiblemente quería decir».

## 1 · ADJUDICACIÓN

`HUMAN_BASIS`: `EXPLICIT` (cita literal) · `WEAK` (inferible del texto, no citado) ·
`VIA_AMBIGUOUS_TOKEN` (única base es «client», palabra retirada) · `NONE` (el texto no lo nombra).

| # | `NAME` | `TARGET` | `UNIT` | `MEANING` | `SOURCE` | `HUMAN_BASIS` | `AGENT_FORMALIZATION` | `EVIDENCE_BASIS` | `STATUS` |
|---|---|---|---|---|---|---|---|---|---|
| | **13 filas** | | | | | `EXPLICIT` 3 · `WEAK` 2 · `VIA_AMBIGUOUS_TOKEN` 2 · `NONE` 6 = **13** | | | `HUMAN_BASIS_EXPLICIT` 2 · `REQUIREMENT_DEFECTIVE` 1 · `PROPOSED_NOT_ACTIVE` 9 · `RETIRED` 1 = **13** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `FD_UNIVERSE_COVERAGE` | procesos × nodo DRM | `process × DRM node` | la población relevante de procesos fue examinada respecto de los nodos, con la cobertura exigida | `/proc/<pid>/fd`, `/proc` | **`EXPLICIT`**: «complete», «FD visibility is incomplete», «root namespaces are not covered», «a permission is denied» | el nombre; los 4 términos de visibilidad | `ESTABLISHED`; observado `283/283`, 0 denegados | **`HUMAN_BASIS_EXPLICIT`** |
| 2 | `DRM_NODE_PCI_IDENTITY` | nodo ↔ dispositivo PCI | dispositivo (`drm-pdev` = BDF) | el nodo observado corresponde al dispositivo PCI esperado | `drm-pdev` (`drm_file.c:948-950`), sysfs, spec `:59-62` | **`EXPLICIT`**: «identified by PCI identity rather than by node name» | el nombre | `ESTABLISHED`; `PROVEN` en captura (`0000:01:00.0`) | **`HUMAN_BASIS_EXPLICIT`** |
| 3 | `OWNERSHIP_VERDICT` — **NO es propiedad técnica**: `CLASS = PROJECT_VERDICT` | consumidor del proyecto | veredicto | que `OWNERSHIP` alcance un valor concreto | `AGENTS.md:170-183` | **`EXPLICIT`**: el veredicto existe | la noción de «fila» | el criterio que lo define usa un término **retirado** | **`REQUIREMENT_DEFECTIVE`** — requiere criterio nuevo escrito por el humano |
| 4 | `DRM_NODE_EXISTENCE` | nodo DRM | nodo | el nodo `/dev/dri/…` existe y es resoluble | sysfs `class/drm/` | **`WEAK`**: el texto nombra «the RX550's card and render nodes», pero no pide su existencia | el nombre y la separación de 1 | `ESTABLISHED` | **`PROPOSED_NOT_ACTIVE`** |
| 5 | `DRM_CLIENT_IDENTITY` | `struct drm_file` | `drm_file` / `drm-client-id` | identidad de la apertura DRM; 1:1 conceptual con `struct drm_file` | `drm_file.c:142,942-943`; spec `:64-72` | **`VIA_AMBIGUOUS_TOKEN`**: la única base es «a client is active», con «client» **retirado** | el nombre, la unidad, la separación del resto | `ESTABLISHED` (semántica); `VALUE` `NOT_AVAILABLE` | **`PROPOSED_NOT_ACTIVE`** |
| 6 | `DRM_CLIENT_PROCESS_ASSOCIATION` | relación `drm_file` ↔ proceso | relación | el proceso que **usa** esa apertura | `drm_file.c:143`; `drm_file.h:271-278`; `drm_debugfs.c:98-103` | **`VIA_AMBIGUOUS_TOKEN`**: ídem que 5 | el nombre | `ESTABLISHED`; `NOT_IMPLEMENTED` | **`PROPOSED_NOT_ACTIVE`** |
| 7 | `DRM_CLIENT_TO_DEVICE_ASSOCIATION` | relación `drm_file` → minor → device → PCI | relación | a qué dispositivo pertenece una apertura concreta | `drm-pdev`; `drm_file.minor` | **`WEAK`**: «identified by PCI identity» habla del nodo, no de la relación por fichero | el nombre y la separación de 2 | `ESTABLISHED` (semántica); solo contador `pooled` | **`PROPOSED_NOT_ACTIVE`** |
| 8 | `AMDGPU_VM_PROCESS_CONTEXT` | VM / PASID / proceso | vmid | PASID = vmid; relación con proceso | — | **`NONE`**: el texto no menciona PASID ni VM | el nombre | **`SOURCE_INCOMPLETE`** + `PROVISIONAL` | **`PROPOSED_NOT_ACTIVE`** — y **no** se pide decisión humana sobre ella |
| 9 | `DRM_CLIENT_MEMORY_ACCOUNTING` | `drm_file` | agregado por file y región | consumo agregado de ese cliente | `drm_file.c:828-840`; spec `:140-175` | **`NONE`** | el nombre | `ESTABLISHED`; `NOT_OBSERVED` | **`PROPOSED_NOT_ACTIVE`** |
| 10 | `DRM_CLIENT_ENGINE_ACTIVITY` | `drm_file` × engine | ns acumuladas | tiempo del engine ejecutando trabajo de ese cliente | spec `:79-137` | **`NONE`** | el nombre | `ESTABLISHED`; `NOT_OBSERVED` | **`PROPOSED_NOT_ACTIVE`** |
| 11 | `DRM_MASTER_RELATION` | `drm_master` | un master | qué `drm_file` posee el master del nodo primario | `drm_lease.h`; `drm_auth.c:81` | **`NONE`** | el nombre | `ESTABLISHED`; `NOT_OBSERVED` | **`PROPOSED_NOT_ACTIVE`** |
| 12 | `GEM_OBJECT_RELATION` | `drm_gem_object` | un objeto | qué objetos alcanza una apertura vía `object_idr` | `drm_file.h:299-304`; `drm_gem.h` | **`NONE`** | el nombre | `PARTIALLY_ESTABLISHED`; no observable | **`PROPOSED_NOT_ACTIVE`** |
| 13 | `DRM_CLIENT_DEDUPLICATION` | conjunto de aperturas | `distinct drm-client-id` | contar aperturas distintas sin confundir FDs | clave derivada de `client-id` | **`NONE`** — y es **consecuencia de la interpretación retirada** («12 clientes») | el nombre | **`NOT_ESTABLISHED`**: requiere `VALUE` y resolver `C-4` | **`RETIRED`/`UNSUPPORTED` como propiedad normativa.** Retenida solo técnicamente. **No** se pide decisión humana sobre ella |

### 1.1 · Dos cláusulas del texto humano que **no** tienen propiedad

El texto nombra «**a writer is unresolved**». No hay ficha para ella: `writers` (y el guard/restauración)
existen como **filas** del criterio en el collector (`writers_resolved`, `guard_and_restore`), pero
nunca se les dio definición técnica independiente.

| | `NAME` | `HUMAN_BASIS` | `STATUS` |
|---|---|---|---|
| 14 | `WRITER_RESOLUTION` — `CLASS = CRITERION_ROW_WITHOUT_PROPERTY` | **`EXPLICIT`**: «a writer is unresolved» | **`PROPOSED_NOT_ACTIVE`** — sin ficha técnica; el modelo **no** la cubre |
| 15 | `GUARD_RESTORE_CONDITION` — `CLASS = CRITERION_ROW_WITHOUT_PROPERTY` | implícita en la exigencia de reversión del propio proyecto | **`PROPOSED_NOT_ACTIVE`** — fuera del modelo DRM |

Esto es una **laguna de la descomposición, no un problema del humano**: el agente produjo 11 fichas y
el texto tiene al menos 3 propiedades con base explícita. La descomposición **no** es una partición
del texto humano, y no debe presentarse como tal.

## 2 · LO QUE ESTO CORRIGE

| Antes (incorrecto) | Ahora |
|---|---|
| «las 11 propiedades son la descomposición normativa» | **3** tienen base humana explícita: `FD_UNIVERSE_COVERAGE`, `DRM_NODE_PCI_IDENTITY`, `OWNERSHIP_VERDICT` |
| «el humano dijo 11 cosas» | el humano nombra **3** conceptos; el resto lo separó el agente |
| «decidir cuáles de las 11 son obligatorias» | la decisión humana es **escribir un criterio nuevo** para `OWNERSHIP` (3), y **opcionalmente** activar 4 propuestas con base débil o vía token ambiguo |
| 11 propiedades esperando decisión | **1 retirada**, **10 propuestas no activas**, **3 con base explícita** |

## 3 · LO QUE NO SE PIDE DECISIÓN HUMANA

`AMDGPU_VM_PROCESS_CONTEXT` · `DRM_CLIENT_MEMORY_ACCOUNTING` · `DRM_CLIENT_ENGINE_ACTIVITY` ·
`DRM_MASTER_RELATION` · `GEM_OBJECT_RELATION` · `DRM_CLIENT_DEDUPLICATION`.
Ninguna tiene base humana. Pedir que el humano decida sobre ellas reintroduciría la formalización
del agente como requisito: exactamente el defecto que se está corrigiendo.

## 4 · IMPLEMENTACIÓN QUE DEPENDE DE LA PROPIEDAD RETIRADA

Sin cambios en esta ronda. Registrado para después:

| Dónde | Qué depende | Qué debería pasar |
|---|---|---|
| `OWNERSHIP_CRITERION_ROWS` (`writers_resolved`, `guard_and_restore`) | filas que emitieren estados sin ficha técnica (14, 15) | definir o retirar las filas |
| `AGENTS_OWNERSHIP_MATRIX` | el criterio ensamblado que alimenta `OWNERSHIP` | depende del criterio nuevo que escriba el humano |
| `card_drm_client_id_fds` / `render_drm_client_id_fds` | nombre ya corregido; el valor es un **conteo de FDs** | no requiere acción: el nombre dice lo que mide |
| `PASID` (contador pooled) | propiedad 8, `PROPOSED_NOT_ACTIVE` | dejar de recolectar o justificar su uso, si el humano no la activa |

## 5 · ESTADO

```
HUMAN_REQUIREMENT_STATUS   = MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION
HUMAN_MIXED_TERM           = RETIRED_AS_SINGLE_PROPERTY
ROWS_TOTAL                        = 15   (13 en la tabla de adjudicación + 2 filas de criterio sin propiedad)
TECHNICAL_PROPERTIES              = 12   (filas 1,2,4-13)
PROJECT_VERDICT_NOT_A_PROPERTY    = 1    (fila 3: OWNERSHIP_VERDICT)
CRITERION_ROWS_WITHOUT_PROPERTY   = 2    (filas 14,15: writers_resolved, guard_and_restore)
HUMAN_BASIS_EXPLICIT_TECHNICAL    = 2    (FD_UNIVERSE_COVERAGE, DRM_NODE_PCI_IDENTITY)
HUMAN_BASIS_EXPLICIT_BUT_VERDICT  = 1    (OWNERSHIP_VERDICT: el veredicto es humano, su CRITERIO es defectuoso)
PROPOSED_NOT_ACTIVE               = 11   (2 WEAK + 2 VIA_AMBIGUOUS_TOKEN + 5 NONE en la tabla, + 2 filas de criterio)
RETIRED_UNSUPPORTED               = 1    (DRM_CLIENT_DEDUPLICATION)
CHECK                             = 2+1+2+2+5+1+2 = 15  OK
PROJECT_MAPPING            = NOT_ATTEMPTED
PASS_FAIL                  = NOT_DEFINED
ANY_ALL                    = NOT_DECIDED
TECHNICAL_MODEL            = CLOSED (sin modificar)
CODE_CHANGES               = NONE
```

La separación está definida. **Detenerse**: la decisión humana pendiente es **escribir un criterio
de `OWNERSHIP` en términos de las 3 propiedades con base explícita**, no elegir entre 11.
