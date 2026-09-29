# R1-G1-G2-DECISION-REQUEST-20260926

`DOCUMENT_KIND = DECISION_REQUEST` · `NORMATIVE_STATUS = RESEARCH_ONLY` · `NOT_NORMATIVE`
Para el **autor humano** del requisito. No propone solución técnica.
`CODE_CHANGE_ALLOWED = NO` · nada implementado, corregido ni modificado.
Cierra como `REQUIREMENT_UNRESOLVED` G-1 y G-2. La procedencia ya está trazada
(`R1-ATTRIBUTION-DECOMPOSITION-MODEL-20260926.md`, `R1-P3-RESOLUTION-G4-20260926.md`, y la
trazada de procedencia de la ronda previa). **No se infiere intención no escrita.**

`TEMPORALITY` = estado del working tree al cierre de esta etapa · `HOST_SCOPE` = ninguno (no hay
lectura de host en este documento).

---

## G-1 · OBJETO DE "ATTRIBUTABLE"

**Requisito humano actual**, textual, sin paráfrasis:

> `AGENTS.md:176-177` — "`FULL` requires complete attributable evidence for the RX550's **card and
> render nodes**, identified by PCI identity rather than by node name"

> `AGENTS.md` rev. `54b3ea8` — "`OWNERSHIP=FULL` requires complete, attributable evidence for
> `card1`, `renderD129`"

La adjetivación **"attributable" consta**. **Su objeto no consta.** Universo buscado:
`AGENTS.md` completo, sus 2 versiones en historia (`git log --follow` → `6fe40b2`, `54b3ea8`),
§Ownership completo. Sin frase que nombre cliente, proceso, ni dstinatario de la atribución.

### Alternativa A · `ATTRIBUTION_TO_DRM_CLIENT`

| Campo | Contenido |
|---|---|
| `HUMAN_REQUIREMENT` | **Ausente para esta alternativa.** El texto exige *atribuible*, no *atribuible a un cliente DRM*. No nombra `drm-client-id`, `drm_file` ni cliente. Búsqueda: `AGENTS.md` §Ownership, ambas versiones |
| `AGENT_FORMALIZATION` | **Sí, y trazada.** Plan `R1-PLAN-privileged-readonly-ownership.md` **fila 11** (`:144`) *"clients/PASID atribuibles"*, evidencia `drm-client-id`+`pasid`; artefacto #6 (`:36`,`:95`) *"cliente ↔ drm-client-id ↔ pasid ↔ drm-pdev"*; campos en `:36`,`:48`,`:94`. **Asignada a una fila y una ruta separadas, no a las filas 1-2** |
| `IMPLEMENTATION_STATUS` | `PARTIAL_IMPLEMENTED`. `P3B-1 PRESENCE` sí (`any()`, `:2783`); `P3B-2 DISCRIMINATION` **no** — `fdinfo_attribution` (`:1041-1051`) *"Presence only, never a value"* |
| `EVIDENCE` | `collector:1033`, `:2783`, `:2839-2840`, `:1041-1051`; plan `:36`,`:144`; `AGENTS.md:176-177` |
| `FALSIFIER` | (a) Una frase humana que nombre el cliente como objeto. (b) Que la fila 11 del plan se lea como la **única** ruta de atribución, en cuyo caso A pertenece a otra fila y no a las filas 1-2 |
| `STATUS` | `PROPOSED` · el requisito que la respalda es `REQUIREMENT_UNRESOLVED` |

### Alternativa B · `ATTRIBUTION_TO_PROCESS`

| Campo | Contenido |
|---|---|
| `HUMAN_REQUIREMENT` | **Ausente en la oración de las filas de nodo.** Sí existen dos rastros **en otra oración** (§Ownership, cláusula de fallo `:180-181`): *"If FD visibility is incomplete…"* y *"a **client is active**…"*. Y *"DRM FDs"* figura enumerado como **condición aparte**. Ninguno nombra proceso como objeto de *"attributable"* en las filas de nodo |
| `AGENT_FORMALIZATION` | **Sí, como método.** Plan `:134-135`, evidencia de las filas 1-2 = *"FD+fdinfo de **todos los PIDs**"*. Eso describe **cómo** se recorre, no **qué** debe probarse |
| `IMPLEMENTATION_STATUS` | `NOT_IMPLEMENTED_AS_SEPARATE_PROPERTY`. El path `/proc/<pid>/fd/<n>` se recorre para obtener la tabla (P1), pero **ninguna propiedad puntúa la asociación a proceso** ni emite por proceso |
| `EVIDENCE` | plan `:134`; `collector:2455-2472`, `:2772-2789`; `AGENTS.md:180-181` |
| `FALSIFIER` | (a) Frase humana que nombre proceso como objeto. (b) Que *"todos los PIDs"* se lea como método de completitud — en cuyo caso B es indistinguible de C |
| `STATUS` | `PROPOSED` · requisito `REQUIREMENT_UNRESOLVED` |

### Alternativa C · `ATTRIBUTION_TO_PCI_NODE`

| Campo | Contenido |
|---|---|
| `HUMAN_REQUIREMENT` | **Presente y literal, pero en rol de *qualifier*, no de objeto.** `AGENTS.md:177` *"identified by PCI identity rather than by node name"*; `:32` *"Identify a device by PCI identity, never by its `cardN` name"*. Único antecedente literal de las cuatro. **Ambigüedad real**: el texto admite leerlo como *regla de selección de dispositivo* y no como *destinatario de "attributable"* — la redacción no lo desambigua |
| `AGENT_FORMALIZATION` | `gpu_proven` + derivación de nodos desde sysfs (`collector:2772-2773`), gate de `:1703-1708`. `drm-pdev` dentro de `DRM_ATTRIBUTION_FIELDS` es un **segundo camino, más débil**, a la misma propiedad (plan `:36`) |
| `IMPLEMENTATION_STATUS` | `IMPLEMENTED`. Y es la **única de las cuatro implementada como gate independiente de fdinfo**: no requiere leer un solo byte de `/proc/*/fdinfo` |
| `EVIDENCE` | `AGENTS.md:32`, `:177`; `collector:2772-2773`, `:1703-1708`, `:1033` |
| `FALSIFIER` | (a) Frase humana que declare la identidad PCI como **solo** regla de alcance, no como objeto de atribución. (b) Demostrar que `drm-pdev` no liga un cliente al RX550 — es propiedad del *dispositivo del fd*, no del cliente |
| `STATUS` | `ESTABLISHED` que la **identidad PCI es exigida** · `UNKNOWN` si es **lo que "attributable" denota**. Las dos cosas no son la misma y no se colapsan |

### Alternativa D · `ATTRIBUTION_TO_OBSERVED_FD`

| Campo | Contenido |
|---|---|
| `HUMAN_REQUIREMENT` | **Compatible, no enunciada.** *"attributable"* + la cláusula de fallo *"If FD visibility is incomplete…"* son coherentes con D: bastaría con que la evidencia esté **ligada al nodo identificado** y completa. El texto no exige propiedad adicional |
| `AGENT_FORMALIZATION` | **Es la que implementaba el baseline.** `df2406a:2750-2751` → `"card_complete": root_visibility_complete` a secas. La **descripción** de la fila (`:1557-1558`) decía *"complete **and attributable**"* y la expresión **no** lo computaba |
| `IMPLEMENTATION_STATUS` | `MATCHES_COMMITTED_BASELINE_ONLY`. El working tree **ya no** la implementa: `:2839-2840` añade `card_attributable` |
| `EVIDENCE` | `git show df2406a:…:2750-2751` vs `collector:2839-2840`; `collector:1557-1558` |
| `FALSIFIER` | (a) Frase humana que exija identidad o discriminación más allá de la ligation al nodo. (b) Que la fila 11 del plan se lea como parte de las filas 1-2 |
| `STATUS` | `PROPOSED` |

**Consecuencia factual, no recomendación**: bajo D, el predicado `any(drm-client-id, drm-pdev,
pasid)` de las filas de nodo queda **sin motivo**; bajo D el fix de Opción A no impuesto en el working
tree sería una **divergencia respecto del requisito**, no una mejora.

---

## G-2 · UBICACIÓN DEL REQUISITO PROCESO↔FD

Lo que **queda establecido por la procedencia**, sin elegir:

| # | Alternativa | `HUMAN_REQUIREMENT` | `AGENT_FORMALIZATION` | `IMPLEMENTATION_STATUS` | `FALSIFIER` | `STATUS` |
|---|---|---|---|---|---|---|
| **A** | proceso↔FD es requisito de `card_node_complete`/`render_node_complete` | **Ausente** | Solo como método (plan `:134`) | `NOT_IMPLEMENTED_AS_SEPARATE_PROPERTY` | (a) Frase humana que lo exija en esas filas. (b) La lectura de método → lo reduce a C | `PROPOSED` |
| **B** | proceso↔FD es requisito **únicamente** de `drm_fds_enumerated` | **Parcial**: *"DRM FDs"* enumerado como condición propia (`AGENTS.md:178`) y *"FD visibility"* en la cláusula de fallo (`:180`) | Plan **fila 5** *"DRM FDs enumerados"*, evidencia *"conjunto completo"* | `IMPLEMENTED_AS_POOLED` — `drm_fd_enumeration_state` (`:1576`) evalúa card y render **conjuntos**, no por separado | Demostración de que la fila 5 no cubre la asociación | `PROPOSED` |
| **C** | proceso↔FD es **solo método** de observación, no requisito independiente | **Ausente** como requisito; presente como enumerable | Filas 1-2 = completitud del nodo; fila 5 = enumeración de FDs | Coherente con el estado actual | (a) Frase humana que lo exija. (b) Condición de fallo que lo haga indispensable | `PROPOSED` |
| **D** | `REQUIREMENT_UNRESOLVED` | — | — | — | — | **`RECOMENDADO PARA DECISIÓN`** |

**Precisión para quien decide**: A es excluyente con B y con C. **B y C son compatibles entre sí** —
difieren en si el requisito está escrito en algún sitio (fila 5) o si solo subyace al método. La
pregunta operatoria es una sola: **¿las filas de nodo deben exigir la asociación a proceso, sí o
no?**

---

## C-3 · `CONFLICT_UNRESOLVED`

| Lado | Contenido |
|---|---|
| `PLAN` | filas 1-2 = **completitud**; fila 11 = **clients/PASID atribuibles** |
| `IMPLEMENTATION` (working tree) | filas 1-2 = **completitud** + `any(drm-client-id, drm-pdev, pasid)` |
| `C3_STATUS` | **`CONFLICT_UNRESOLVED`** — no corregido |
| Nota adicional | El baseline `df2406a` implementaba el lado del **PLAN**; el working tree se aparta de él. `ESTABLISHED` |

---

## F-02

`F02_STATUS` = **`TECHNICALLY_ESTABLISHED_BUT_REQUIREMENT_DEPENDENT`**

Hecho técnico `ESTABLISHED`: `FD count ≠ distinct drm-client-id count` cuando varios FDs
corresponden al mismo `drm_file` (dup/fork → `struct file` compartido → mismo `client_id`).

**No se convierte en obligación normativa** hasta que G-1 defina si la fila requiere P3B.
`card_clients`/`render_clients` **no se renombran y no se corrigen**.

---

## EMPTY_UNIVERSE

`EMPTY_UNIVERSE_STATUS` = **`MAPPING_DEFERRED`**

Motivo: G-1 no define si la fila requiere P3B. Sin esa definición no puede decidirse si 0 FDs es un
estado distinguible, un PASS o un FAIL. El token existe; el mapeo no.

---

## ESTADO DE SALIDA

```
G1_DECISION_REQUIRED  = YES
G2_DECISION_REQUIRED  = YES
G1_ALTERNATIVES       = A ATTRIBUTION_TO_DRM_CLIENT | B ATTRIBUTION_TO_PROCESS
                        | C ATTRIBUTION_TO_PCI_NODE | D ATTRIBUTION_TO_OBSERVED_FD
G2_ALTERNATIVES       = A required-by-node-rows | B required-by-drm_fds_enumerated
                        | C method-only | D REQUIREMENT_UNRESOLVED
C3_STATUS             = CONFLICT_UNRESOLVED
F02_STATUS            = TECHNICALLY_ESTABLISHED_BUT_REQUIREMENT_DEPENDENT
EMPTY_UNIVERSE_STATUS = MAPPING_DEFERRED
CODE_CHANGE_ALLOWED   = NO
NEXT                  = "Human requirement decision required"
```

## LO QUE ESTA RONDA NO HIZO

No implementó P3B-2 · no corrigió F-02 · no tocó `card_node_complete`/`render_node_complete` ·
no modificó código, tests, `AGENTS.md`, `README`, documentación normativa, Git ni sistema ·
no ejecutó sudo, systemctl, C1, runtime ni benchmarks · no infirió intención humana no escrita.
