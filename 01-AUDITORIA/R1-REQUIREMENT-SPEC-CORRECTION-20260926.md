# R1-REQUIREMENT-SPEC-CORRECTION-20260926

`DOCUMENT_KIND` = `SPEC_CORRECTION` · **READ_ONLY / DOCUMENTATION-ONLY**
`HUMAN_REQUIREMENT_STATUS` = `MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION`
`HUMAN_MIXED_TERM` = `RETIRED_AS_SINGLE_PROPERTY` · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`PASS_FAIL` = `NOT_DEFINED` · `ANY_ALL` = `NOT_DECIDED` · `TECHNICAL_MODEL` = `CLOSED` (sin modificar)
Sin cambios en collector, tests, `AGENTS.md`, `README.md`, código, C1, runtime, sysfs, GPU/PM,
storage, systemd ni configuración. Sin sudo, systemctl, commits.
Semántica completa ya established en `R1-TECHNICAL-SEMANTIC-MODEL-V2-20260926.md` (`6286b680`) y
`R1-TECHNICAL-TAXONOMY-20260926.md` (`d36deb11`); este documento **corrige la especificación**, no
re-deriva el modelo.

## A · `REQUISITORIGINAL`

> `AGENTS.md:176-177` — `FULL` requires **complete attributable evidence** for the RX550's card and
> render nodes, **identified by PCI identity rather than by node name**
> `AGENTS.md:180-181` — If **FD visibility is incomplete**, **a permission is denied**, **root
> namespaces are not covered**, **a client is active** or **a writer is unresolved**, then
> `OWNERSHIP != FULL`

`PROVENANCE: HUMAN_REQUIREMENT`. Verbatim. No parafraseado.

## B · `DEFECTO_DE_FORMULACIÓN`

«attributable» no puede tratarse como una propiedad coherente porque **no tiene unidad**. Un
predicado necesita una unidad; la frase mezcla, bajo un solo sustantivo:

| # | Mezcla | Unidad mezclada | Fuente |
|---|---|---|---|
| 1 | existencia/visibilidad del nodo | nodo | sysfs, `/proc` |
| 2 | identidad PCI del dispositivo | dispositivo | `drm-pdev` |
| 3 | visibilidad de DRM FDs | FD | `/proc/<pid>/fd` |
| 4 | identidad del `drm_file` | apertura DRM | fdinfo, debugfs |
| 5 | `drm-client-id` | `drm_file` | fdinfo |
| 6 | asociación `drm_file` ↔ PID/TGID | relación | `drm_file.pid` |
| 7 | `drm-pdev` | BDF | fdinfo |
| 8 | PASID/VM | vmid | **sin fuente obtenida** |
| 9 | memoria por cliente | agregado | fdinfo |
| 10 | actividad de engine | ns | fdinfo |

Y «client» nombra **cinco** entidades distintas en el propio kernel. Un predicado sobre esta
formulación tendría que decidir **cuál** de las diez unidades falló, y ninguna definición lo permite.
Reconstruir la intención no es una vía verificable: no hay evidencia que distinga las alternativas.

## C–E · PROPIEDADES SEPARADAS, NOMBRES Y SEMÁNTICA

`OBSERVABILITY` = las 5 capas, en orden, sin saltar: **E**=expuesto · **R**=leído por el analizador ·
**O**=observado en la muestra · **P**=demuestra la propiedad · **S**=satisface el requisito
(**nunca answered aquí**).

### P-1 · `FD_UNIVERSE_COVERAGE`
`PURPOSE`: determinar que la población relevante de procesos fue examinada respecto de los nodos con
la cobertura exigida. `ENTITY/UNIT`: `process × DRM node`. `SOURCE`: los cuatro términos de
visibilidad de `/proc`. `RELATIONSHIP`: ninguna con DRM. `OBSERVABILITY`: E sí · R sí · O sí
(`283/283`) · P parcial · S `NOT_ATTEMPTED`. `SEMANTICS`: **significa** cobertura de un universo;
**no significa** identidad de cliente, asociación con proceso, ni actividad. `MUTABILITY/LIFETIME`:
re-evaluable / la del barrido. `LIMITATIONS`: cobertura parcial ≠ completa; no cubre el minor `ACCEL`.
`FALSIFIER`: mismo universo y privilegio con los 4 términos satisfechos y una fila de FDs ausente.
`PROVENANCE`: **`HUMAN_REQUIREMENT`** («complete», «FD visibility», «root namespaces»).
`ZERO_OBJECTS`: `EMPTY_UNIVERSE` — barrido completo con 0 FDs es una observación real **solo** si
ningún PID desapareció sin ausencia demostrada; con desaparecimientos, `UNKNOWN`.

### P-2 · `DRM_NODE_PCI_IDENTITY`
`PURPOSE`: vincular el nodo observado al dispositivo PCI esperado. `ENTITY/UNIT`: nodo ↔
dispositivo. `SOURCE`: `drm-pdev` (`drm_file.c:948-950`), sysfs, spec `:59-62`. `RELATIONSHIP`:
`drm_minor → drm_device → PCI`. `OBSERVABILITY`: E sí · R sí · O sí (`PROVEN`) · P sí · S
`NOT_ATTEMPTED`. `SEMANTICS`: **significa** BDF del dispositivo; **no significa** identidad de
cliente — todos los clientes de ese dispositivo comparten el valor. `MUTABILITY/LIFETIME`:
inmutable / la del dispositivo. `LIMITATIONS`: ausente en dispositivos no-PCI; no transporta
vendor/device/class. `FALSIFIER`: `drm-pdev` emitiendo algo que no sea `domain:bus:slot.func`.
`PROVENANCE`: **`HUMAN_REQUIREMENT`** («identified by PCI identity rather than by node name»).
`ZERO_OBJECTS`: nodo ausente → `ABSENT`, no `UNKNOWN`; es un hecho de existencia.

### P-3 · `DRM_FD_VISIBILITY`
`PURPOSE`: enumerar y leer los DRM FDs del universo. `ENTITY/UNIT`: proceso + FD. `SOURCE`:
`/proc/<pid>/fd/<n>` + `fdinfo/<n>`, con `read_bytes`+`status`. `OBSERVABILITY`: E sí · R sí · O sí
(12 FDs / 4 procesos) · P sí · S `NOT_ATTEMPTED`. `SEMANTICS`: **significa** posesión del descriptor y
resolución del destino; **no significa** que el FD sea un `drm_file` ni que exista `client-id`.
`LIMITATIONS`: `NOT_OBSERVED` ≠ el proceso no tenía el FD. `FALSIFIER`: symlink a otro nodo; o
`read_text` en la ruta de fdinfo. `PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`.
`ZERO_OBJECTS`: 0 FDs con barrido completo = `EMPTY_UNIVERSE` (ver P-1).

### P-4 · `DRM_FILE_IDENTITY`
`PURPOSE`: relacionar un FD con su apertura DRM. `ENTITY/UNIT`: una apertura DRM (`struct drm_file`).
`SOURCE`: R-01/R-02 (`private_data`); core expone la fila en `debugfs/dri/<minor>/clients`
(`drm_debugfs.c:92,143`). `RELATIONSHIP`: `FD → struct file` **N:1**; `struct file → drm_file` **1:1**.
`OBSERVABILITY`: E sí · R **no preservado** · O no · P no · S `NOT_ATTEMPTED`. `SEMANTICS`:
**significa** que varios FDs pueden referenciar la misma apertura; **no significa** FD ≡ `drm_file`.
`MUTABILITY/LIFETIME`: `open()`→`close()`; `dup()`/`fork()` no crean apertura. `LIMITATIONS`: fdinfo
no publica la identidad. `FALSIFIER`: dos FDs del mismo `drm_file` con identificadores distintos.
`PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`. `ZERO_OBJECTS`: 0 aperturas = `NO_EVIDENCE` si el
barrido fue parcial; `EMPTY_UNIVERSE` si fue completo.

### P-5 · `DRM_CLIENT_IDENTITY`
`PURPOSE`: obtener el `drm-client-id` y establecer su unidad. `ENTITY/UNIT`: un `drm_file`.
`SOURCE`: `drm_file.c:142,942-943`; `drm_file.h:281-282`; spec `:64-72`. `RELATIONSHIP`:
`drm_file → client_id`, **1:1**. `OBSERVABILITY`: E sí · R presencia sí, **valor no** · O solo por cita
· P **no** · S `NOT_ATTEMPTED`. `SEMANTICS`: **significa** identidad de la apertura; **no significa**
PID · FD · proceso · `drm_master` · PASID · page-fault `client-id` · nº de clientes. `MUTABILITY`:
inmutable en el core; **alcance**: contador `static` de módulo (`:132`) → único dentro de la vida del
módulo `drm`. `LIMITATIONS`: unicidad **global o por dispositivo** (`C-4`); en el segundo caso
`drm-pdev` desambigua (spec `:70-71`). `FALSIFIER`: dos `drm_file` distintos con el mismo `client_id`
dentro del dominio de unicidad aplicable. `PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`.
`ZERO_OBJECTS`: ausencia de la clave tiene ≥7 causas y **dos** indistinguibles (clave opcional no
exportada; driver sin `drm_show_fdinfo`) → `UNKNOWN`, nunca ausencia.

### P-6 · `DRM_CLIENT_PROCESS_ASSOCIATION`
`PURPOSE`: relacionar una apertura con el proceso que la usa. `ENTITY/UNIT`: relación.
`SOURCE`: `drm_file.c:143` (`task_tgid`); `drm_file.h:271-278`; `drm_debugfs.c:98-103`. `RELATIONSHIP`:
`drm_file → TGID`, 1:1 **instantáneo**; dirección **opuesta** a P-3. `OBSERVABILITY`: E sí (debugfs) ·
R no implementado · O no · P no · S `NOT_ATTEMPTED`. `SEMANTICS`: **significa** el proceso que **está
usando** el archivo; **no significa** identidad histórica del opener. `MUTABILITY`: **mutable**,
documentado en la fuente (`drm_file.h:275-277`); sitio de reasignación `SOURCE_NOT_LOCATED`.
`FALSIFIER`: `drm_clients_info` sin columna `tgid`; o `:272` describiendo al proceso original.
`PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`. `ZERO_OBJECTS`: sin fila debugfs → `NOT_OBSERVED`,
no «no hay proceso».

### P-7 · `DRM_PDEV_ASSOCIATION`
`PURPOSE`: asociar una apertura concreta con su dispositivo. `ENTITY/UNIT`: relación
`drm_file → minor → device → PCI`. `SOURCE`: `drm-pdev`; `drm_file.minor` (`drm_file.h:295-296`).
`OBSERVABILITY`: E sí condicional · R **solo contador pooled** · O presencia por nodo · P no · S
`NOT_ATTEMPTED`. `SEMANTICS`: **significa** a qué dispositivo pertenece una apertura; **no
significa** identidad de cliente. `LIMITATIONS`: hoy no existe relación por fichero, solo un agregado
pooled. `FALSIFIER`: dos `drm_file` del mismo dispositivo con `drm-pdev` distinto.
`PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`. `ZERO_OBJECTS`: `drm-pdev` ausente = dispositivo
no-PCI (`NOT_EXPOSED`), no «sin cliente».

### P-8 · `PASID_OBSERVABILITY` / `PASID_VM_PROCESS_RELATION`
`PURPOSE`: observar `pasid`; establecer la relación VM↔PASID↔proceso. `ENTITY/UNIT`: vmid.
`SOURCE`: **`SOURCE_INCOMPLETE`** — 0 en `drm-usage-stats.rst`, 0 en el core v6.12. `OBSERVABILITY`:
E **no** · R no · O no · P no · S `NOT_ATTEMPTED`. `SEMANTICS`: **no significa** identidad de cliente
DRM · PID · `drm_file` · «cliente». `LIMITATIONS`: sin fuente; sin falsador disponible → `PROVISIONAL`.
`FALSIFIER`: `pasid` junto a PID sin fault concurrente. `PROVENANCE`: `INFERENCE` (núcleo amdgpu
inaccesible). `ZERO_OBJECTS`: irrelevante: hoy no hay exposición que pueda estar vacía.

### P-9 · `CLIENT_MEMORY_ACCOUNTING`
`PURPOSE`: saber qué estadísticas de memoria pertenecen a un `drm_file`. `ENTITY/UNIT`: agregado por
`drm_file` y región. `SOURCE`: `drm_file.c:828-840`; spec `:140-175`. `OBSERVABILITY`: E por driver ·
R no implementado · O `NOT_OBSERVED` · P no · S `NOT_ATTEMPTED`. `SEMANTICS`: **significa** consumo
agregado del cliente; **no significa** memoria del proceso, ni inventario; `=0` **no** prueba no-uso.
`FALSIFIER`: clave de memoria indexada por proceso en la spec.
`PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`. `ZERO_OBJECTS`: `=0` es un **valor**, no un universo
vacío: no se distingue «no observable» de «cero».

### P-10 · `CLIENT_ENGINE_ACTIVITY`
`PURPOSE`: saber qué actividad de engine pertenece a un cliente. `ENTITY/UNIT`: `drm_file`×engine,
ns **acumuladas**. `SOURCE`: spec `:79-137` (`:86` *«belonging to this client»*, `:88-89` no monótona).
`OBSERVABILITY`: E por driver · R no implementado · O `NOT_OBSERVED` · P no · S `NOT_ATTEMPTED`.
`SEMANTICS`: **significa** tiempo acumulado; **no significa** actividad instantánea ni «proceso
usando la GPU ahora»; `=0` **no** prueba no-uso. `FALSIFIER`: `drm-engine-*` por proceso, o declarada
monótona. `PROVENANCE`: `AGENT_DERIVED_TECHNICAL_PROPERTY`. `ZERO_OBJECTS`: ídem P-9.

## F · TRAZABILIDAD

| `PROVENANCE` | Propiedades |
|---|---|
| `HUMAN_REQUIREMENT` | **P-1**, **P-2** (cita literal) |
| `AGENT_DERIVED_TECHNICAL_PROPERTY` | P-3, P-4, P-5, P-6, P-7, P-9, P-10 |
| `INFERENCE` | P-8 |
| `KERNEL_SOURCE` (semántica, no nombre) | P-2…P-7, P-9, P-10 |
| `PROJECT_MAPPING` | **ninguna** — `NOT_ATTEMPTED` |

**Ninguna de las 10 es requisito humano salvo P-1 y P-2.** `OWNERSHIP_VERDICT` queda fuera de este
listado: es `CLASS = PROJECT_VERDICT`, no una propiedad del kernel.

### F.1 · Nombres con «client»: desambiguados

| Concepto | Nombre propio | Significado |
|---|---|---|
| apertura DRM | `struct drm_file` | el «cliente» del core |
| fila del fichero debugfs | `debugfs_client_entry` | 1 fila = 1 `drm_file` |
| owner de nodos primarios | `drm_master` | relación de ownership, **no** identidad |
| page-fault | `gpu_page_fault_client_id` | bloque del motor, **no** `drm-client-id` |
| minor de aceleración | `accel_minor_file` | `drm_is_accel_client` (`drm_file.h:432`) |
| nodo de apertura | `drm_client_dev` | **sin fuente primaria**: solo `drm_client_dev_restore(dev)` (`:391`), definición `SOURCE_NOT_LOCATED` |
| clave fdinfo | `drm_client_id` | 1:1 con `struct drm_file` |

## G · `IMPLEMENTATION_IMPACT = FOUND`

Sin corregir. Lo que **tendría** que cambiar después:

| # | Dónde | Qué depende de la formulación defectuosa | Tipo |
|---|---|---|---|
| 1 | `collector:1811,1817` | `EVIDENCE` de las filas de nodo presenta conteos `client-id`/`pdev`/`pasid` como si fueran **cantidades**, cuando son `PRESENCE` por FD | `SEMANTIC_CHANGE` |
| 2 | `collector:2350-2352` | `drm_client_id_seen`/`drm_pdev_seen`/`drm_pasid_seen` son un agregado **pooled** de tres dominios; no permiten atribución por nodo | `SEMANTIC_CHANGE` |
| 3 | `collector:3249` | `active_gpu_clients` nombra clientes sobre un conteo | `RENAME_ONLY` |
| 4 | `OWNERSHIP_CRITERION_ROWS` | `writers_resolved` y `guard_and_restore` emiten estado sin ficha técnica | `REQUIREMENT_CHANGE` (humano) |
| 5 | bundle `R1-20260926T030435Z.json` | `AGENTS_OWNERSHIP_MATRIX` con `EVIDENCE: "card1 / 8 attributable client(s)"` | artefacto **preservado**: no se reescribe |

## H · LO QUE REQUIERE DECISIÓN HUMANA

`HUMAN_DECISION_REQUIRED`: escribir el criterio de `OWNERSHIP` en términos de **P-1** y **P-2** (las
únicas con base textual), y decidir si P-4/P-5 se activan — su base es un token retirado. Nada más.

## I · ESTADO

```
HUMAN_REQUIREMENT_STATUS = MIXED/AMBIGUOUS_REQUIREMENT_CORRECTED_BY_DECOMPOSITION
HUMAN_MIXED_TERM         = RETIRED_AS_SINGLE_PROPERTY
SEPARATED_PROPERTIES     = 10   (2 humanas + 8 agent-derived/INFERENCE)
PROJECT_VERDICT          = 1    (OWNERSHIP_VERDICT, no propiedad del kernel)
IMPLEMENTATION_IMPACT    = FOUND (5 puntos, ninguno corregido)
PROJECT_MAPPING          = NOT_ATTEMPTED
PASS_FAIL / ANY_ALL      = NOT_DEFINED / NOT_DECIDED
TECHNICAL_MODEL          = CLOSED (sin modificar)
```

## J · `GATES_RECONCILIATION` y estado de referencias retiradas

### J.1 · Gates `G-01…G-10` frente al collector real

| | | |
|---|---|---|
| Documentos que nombran gates `G-xx` | **25** | `grep -rlE 'G-0[0-9]' --include='*.md'` |
| Gates presentes en el collector | `G-01`…`G-08`, `G-10` | `grep -oE '"G-[0-9]{2}"'` |
| **`G-09` — CORRECCIÓN 2026-09-26** | **NO está ausente: está `CLOSED_AS_SPECIFICATION`.** `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md:540`: «`G-09` \| Restore matrix y failure flow definidos \| `CLOSED_AS_SPECIFICATION`» | búsqueda literal |
| `CLASS` | **`RESOLVED` — no era `DOCUMENTATION_DEFECT`** | `C1-ISOLATION-AUTOMATOR.md:652` lo confirma: «Los gaps **G-01–G-08 y G-10** siguen `DEFINED_PENDING_EXECUTION`», es decir la familia **excluye G-09 deliberadamente** |

**Por qué su ausencia del collector es correcta**: un gate `CLOSED_AS_SPECIFICATION` es una
especificación documental, no un predicado de runtime; por tanto **no tiene clave en la matriz** y su
presencia en el código no sería esperable. La clasificación anterior (`DOCUMENTATION_DEFECT`) fue
**mía y equivocada**: confundí «no está en el código» con «no existe». La evidencia lo refuta.

**Lo que sí queda**: `G-09` es `AGENT_FORMALIZATION` (documento de diseño de OpenCode,
`SPECIFICATION_ONLY`, `C1: DEFERRED`, sin ejecución) y su contenido —«restore matrix y failure flow
definidos»— tiene **contraparte parcial** en el collector: la fila `guard_and_restore` existe pero
permanece `NOT_EVALUATED` por diseño (`:1615`, `R3`). No es un requisito humano
`HUMAN_REQUIREMENT` y no se convierte en uno.

### J.2 · Referencias a conceptos retirados, por clase

| Concepto | En código `.py` | Estado documental |
|---|---|---|
| `DRM_ATTRIBUTION_FIELDS` | **0** | `HISTORICAL_ONLY` en 18 documentos; ninguno vigente lo afirma como actual |
| `card_attributable` / `render_attributable` | **0** | `HISTORICAL_ONLY`; los tests que los nombran los **prohíben** |
| `node_attributable` | **0** | ídem |
| `clients_pasid_attributable` | **1** = anotación de retiro (`collector:1606`) | retirado |
| `card_clients` / `render_clients` | **0** | renombrados la ronda anterior |

**Ningún bundle histórico se reescribe**: `R1-20260926T030435Z.json` conserva
`"card1 / 8 attributable client(s)"` como evidencia del estado del artefacto en su momento.

### J.3 · Correcciones de presentación aplicadas al collector

| | Cambio | sha |
|---|---|---|
| `EVIDENCE` de filas de nodo | añade el segmento `basis=key-presence-per-fd (NOT coverage, NOT client counts)` | `c2e582ee` |
| `active_gpu_clients` | → `active_gpu_drm_fds` (2 sitios) | ídem |

**Restricción descubierta**: el formato de las cláusulas de evidencia (`<clave>: N fd(s)`) está
**fijado por test** (`test_node_field_presence.clause()`). Cambiar la redacción de las cláusulas
rompe 5 tests de independencia del consumidor. Por eso la corrección **añade un segmento** en lugar de
reescribir las cláusulas. Los contadores `*_seen` siguen siendo `POOLED_ACROSS_NODES` con unidad FD:
expresarlo como campo legible requiere migrar los fixtures del acumulador, que es un cambio de
contrato propio (`IMPLEMENTATION_CHANGE_REQUIRED = YES`, no autorizado).
