# R1-TECHNICAL-SEPARATION-TABLE-20260926

`DOCUMENT_KIND` = `TRANSITION_CLOSURE` · **READ_ONLY + DOCUMENTACIÓN**
`TECHNICAL_MODEL_STATUS` = `CLOSED` · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`HUMAN_MIXED_TERM` = `RETIRED` · `REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`
`NORMATIVE_REQUIREMENT_REWRITE` = `OPEN` (humano; **no** se aborda en esta etapa)
Cero cambios en código, tests, collector, runner, `AGENTS.md` ni requisitos normativos.
Cero runtime, sudo, systemctl, C1 ni capturas privilegiadas.

Documento **de transición**, no de investigación. No introduce evidencia nueva: consolida
`R1-TECHNICAL-MODEL-CLOSURE-20260926.md` (`ee86a3a7…`), `R1-SEMANTIC-DECOMPOSITION-20260926.md`
(`a04c090c…`) y `R1-ACTORS-INVENTORY-20260926.md`. Kernel de referencia: **linux v6.12**.

---

## 1 · `ORIGINAL_HUMAN_PHRASE` → `RETIRED`

```
término humano ambiguo  ("attributable", "complete", "client", "PCI identity")
        |
        v
RETIRED / NO INTERPRETAR          <-- no se reconstruye la intención; no se investiga más
        |
        v
propiedades técnicas independientes   (P-1..P-17 / S-1..S-7)
        |
        v
modelo técnico cerrado
```

`attributable` **no** es una propiedad. Es un sintagma que mezclaba ocho conceptos con cuatro
fuentes distintas. Retirarlo **no** elimina requisito humano: deja el requisito sin
formalización válida, y eso se registra como `REQUIREMENT_UNRESOLVED`, no como Permission.

**No existe** ninguna propiedad técnica llamada `ATTRIBUTABLE`, `DRM_ATTRIBUTION_FIELDS`,
`card_attributable`, `render_attributable`, `node_attributable` o `clients_pasid_attributable`.
`attributable` aparece en este documento únicamente como término retirado.

## 2 · `SEPARATION_TABLE`

Nombres técnicos candidatos. **`AGENT_FORMALIZATION`**: no son requisitos del proyecto, no tienen
obligación asociada, y no eligen `any()` ni `all()`.

| CONCEPTO | NOMBRE TÉCNICO | UNIDAD | QUÉ IDENTIFICA | QUÉ NO IDENTIFICA | FUENTE | ESTADO |
|---|---|---|---|---|---|---|
| Apertura DRM | `DRM_FILE_IDENTITY` (S-1/P-8) | **una apertura DRM** (`struct drm_file`) | el `struct drm_file`; su `drm-client-id` 1:1. **Una sola escritura en todo el core** (`drm_file.c:142`), contador `static atomic64_t ident` **de ámbito de módulo** (`drm_file.c:132`) → unicidad **dentro de la vida del módulo `drm` cargado**, no persistente | **no** PID · **no** FD · **no** proceso · **no** `drm_master` · **no** PASID · **no** page-fault `client-id` | `drm_file.c:132,142`; `drm_file.h:281-282`; spec `:64-72` | `SUPPORTED` (identidad) · `VALUE` **no implementada** |
| Clave fdinfo de identidad | `drm-client-id` (propiedad de S-1) | un `drm_file` | identificador asociado al `drm_file`, para fdinfo; 1:1 conceptual con `struct drm_file` | unicidad **global o por dispositivo** (spec `:70-71`) → `C-4` abierto; **no** nº de clientes | `drm_file.c:943`; spec `:64-72` | `SUPPORTED`; unicidad `CONFLICT_UNRESOLVED` |
| Identidad del dispositivo | `DRM_DEVICE_IDENTITY` (S-3/P-4) | **un dispositivo** (nodo) | el `drm_device`/PCI por BDF; `drm-pdev` cuando corresponde. `drm_minor.type` tiene **cuatro** valores ABI: `PRIMARY=0`, `CONTROL=1`, `RENDER=2`, **`ACCEL=32`** (`drm_file.h:58-66`, `:80`) | **no** identidad de cliente; `drm-pdev` **no** transporta vendor/device/class; un minor `ACCEL` es un **cuarto** tipo de nodo que la enumeración de nodos del proyecto (card/render) no cubre | `drm_file.c:948-950`; spec `:59-62`; `dev_is_pci`; `drm_file.h:58-80` | `OBSERVED` en este host (`PROVEN`); tipo `ACCEL` `NOT_OBSERVED` |
| Descriptor | `DRM_FD_ENUMERATION` (P-1) | **FD** | un descriptor de proceso resuelto a un nodo DRM | **no** un `drm_file`: **N:1** por `dup()`/`fork()` | `/proc/<pid>/fd/<n>`; R-01/R-03 | `OBSERVED` (12 FDs) |
| Asociación de proceso (uso) | `PROCESS_ASSOCIATION` / `DRM_FILE_PROCESS_ASSOCIATION` (S-2/P-9) | un `drm_file` | el proceso que **está usando** ese file (`task_tgid`) | **no** la identidad histórica del opener (`drm_auth.c:236-238` lo compara con `task_tgid(current)`); **no** `drm-client-id` | `drm_file.c:143`; `drm_file.h:271-278`; `drm_debugfs.c:92,98-103` | `SUPPORTED` · **mutable**, documentado en `:275-277` |
| Asociación de proceso (tenencia) | `DRM_FD_PROCESS_ASSOCIATION` (P-10) | **FD** | qué proceso **posee** ese descriptor | **no** el campo del núcleo; **no** distingue dos FDs de un `drm_file` | `/proc/<pid>/fd/<n>` | `OBSERVED` |
| Legibilidad | `DRM_FDINFO_READABILITY` (P-2) | **FD** | que el fdinfo se pudo leer no vacío | **no** que contenga clave alguna | `/proc/<pid>/fdinfo/<n>` | `OBSERVED` (con `fdinfo: ""`) |
| Cobertura | `DRM_NODE_COMPLETENESS` (P-3) | descriptor / proceso | cobertura del universo de FDs de un nodo | **no** depende del contenido de fdinfo; **no** es un atributo global | los 4 términos de visibilidad | `OBSERVED` |
||vMID | `PASID_ASSOCIATION` / `VM_PASID_PROCESS_RELATION` (S-6/P-14) | **vmid** | un VM address space; se relaciona con un proceso **solo durante un page fault y con el proceso activo** | **no** `drm-client-id` · **no** PID · **no** FD · **no** identidad permanente de proceso | docs de amdgpu | `SOURCE_INCOMPLETE`: **0** en la spec, **0** en el core v6.12; convención de driver |
| Ownership de nodo | `DRM_MASTER_RELATION` (P-13) | un `drm_master` | qué `drm_file` posee el master de un nodo primario; **transferible** por leasing | **no** identidad de cliente · **no** identidad de proceso | `drm_lease.h`; `drm_lease.c`; `drm_auth.c:81` | `SUPPORTED` · `NOT_OBSERVED` aquí |
| Memoria | `MEMORY_ASSOCIATION` / `DRM_MEMORY_ACCOUNTING` (P-11) | agregado por `drm_file` | consumo agregado de ese `drm_file` por región | **no** inventario de objetos; **no** del PID; `=0` **no** prueba no-uso | `drm_file.c:828-840`; spec `:140-175` | `NOT_OBSERVED` en este host |
| Objetos | `DRM_GEM_OBJECT` (GEM) | un `drm_gem_object` | un objeto GEM; handles vía `object_idr` | **no** identidad de proceso | `drm_gem.h` | `NOT_OBSERVED` · exposición `SOURCE_INCOMPLETE` |
| Engine | `ENGINE_ACTIVITY` / `DRM_ENGINE_ACCOUNTING` (P-12) | `drm_file` × engine | tiempo que el engine pasó ocupado ejecutando trabajo **de ese cliente**; **no monótona** | **no** identidad de proceso · **no** actividad instantánea; `=0` **no** prueba no-uso | spec `:79-137` | `NOT_OBSERVED` aquí |
| Fila debugfs | `DRM_FILE_DEBUGFS_CLIENT_ENTRY` (S-4/P-16) | **`drm_file`** — 1 fila por elemento de `dev->filelist` | una fila con `command tgid dev master a uid magic` | **NO contiene `drm-client-id`** (`magic` es `drm_magic_t`, `dev` es índice de minor); **no** sustituye a S-1 | `drm_debugfs.c:73-113, 143` | `SUPPORTED` · creada **incondicionalmente** (`:354-370`) |
| Facilidad de driver | `DRM_CLIENT_DEBUGFS_FACILITY` (S-5/P-17) | `drm_file` (presumido) | nada establecido todavía | **no** se asume igual al fichero `clients` del core; **no** lo sustituye | `drm_debugfs.c:311-313`; `drm_client_debugfs.c` **NO LEÍDO** | `SOURCE_INCOMPLETE` |
| Page-fault | `GPU_PAGE_FAULT_CLIENT_ID` (S-7/P-15) | bloque del motor | un bloque del motor, en el informe de page fault | **no** `drm-client-id`; la palabra «client» **no** es evidencia de equivalencia | `SOURCE_INCOMPLETE` | `NOT_AVAILABLE` |
| Opaque | `drm_file.driver_priv` | puntero | contenido **definido por el driver** | **no** expuesto por el core | `drm_file.h` | `NOT_EXPOSED` · amdgpu `SOURCE_INCOMPLETE` |

**Nombres candidatos genéricos** (`AGENT_FORMALIZATION`, sin valor normativo):
`NODE_IDENTITY` · `CLIENT_IDENTITY` · `PROCESS_ASSOCIATION` · `PCI_DEVICE_IDENTITY` ·
`PASID_ASSOCIATION` · `MEMORY_ASSOCIATION` · `ENGINE_ACTIVITY`. **No son requisitos del proyecto.**
La tabla anterior los ata a una entidad, una unidad y una fuente concretas; esos siete, no.

## 3 · `FD` — corrección de formulación

Formulación **retirada** (imprecisa: fusiona dos cosas distintas):

```
FD 1:1 con drm_file                      <-- FORMULACION RETIRADA: FALSA / imprecisa
```

Formulación vigente, basada en **apertura DRM / `struct file` / `struct drm_file`**:

```
FD  --(descriptor de proceso)-->  struct file  --(private_data, 1:1)-->  struct drm_file
 |                                    |                                        |
 N:1                                 1:1 por apertura                     1:1 con el struct file
 dup()/fork(): VARIOS FD             lifetime: open() -> close()          unidad = UNA apertura DRM
 pueden referenciar                  dup()/fork() NO crean un
 la MISMA apertura                   struct file nuevo
```

`FD` **no** es sinónimo de `drm_file`. La equivalencia sería 1:1 **solo si** no hubiera
`dup()`/`fork()`; con ellos, la relación es **N:1** (`R-03`). `drm_file` se identifica por su
`drm-client-id`, no por el número de FD. Corregido en `R1-ACTORS-INVENTORY-20260926.md` (única
ocurrencia del repo). `R1-TECHNICAL-MODEL-CLOSURE` §3 ya distinguía `R-01`/`R-02`/`R-03`
correctamente: **no** requería cambio.

## 4 · `CLIENT` — qualified usage

«Cliente DRM» **no** se usa sin calificar. Según la entidad concreta:

| Si se quiere decir… | escribir | **nunca** |
|---|---|---|
| una apertura del kernel | `drm_file` / `apertura DRM` | «cliente» a secas |
| el identificador fdinfo | `drm-client-id` | «cliente» = su número |
| el nodo por el que se abrió | **no hay nombre de entidad kernel establecido para esto**: `drm_client_dev` **no existe** como símbolo en el conjunto primario. `PROVENANCE = HUMAN_REQUIREMENT` (token), **no** `PRIMARY_KERNEL_SOURCE`. Único símbolo real: `drm_client_dev_restore(dev)` en `drm_file.c:391`, llamado desde `drm_lastclose()`; su **definición no está en el conjunto leído** → `SOURCE_NOT_LOCATED`. La propiedad equivalente es S-5 (`DRM_CLIENT_DEBUGFS_FACILITY`, `SOURCE_INCOMPLETE`) | «cliente» = nodo |
| la fila del fichero debugfs del core | `fila de debugfs clients` = un `drm_file` | «cliente» = fila |
| el master de un nodo primario | `drm_master` | «cliente» = master |
| el identificador de page fault | GPU page-fault `client-id` | «cliente» = `drm-client-id` |
| un proceso con FDs DRM | **proceso que posee FDs DRM** | «cliente» = proceso |

`DRM_CLIENT_DEBUGFS_FACILITY` conserva el token `CLIENT` **heredado del símbolo del kernel**
(`drm_client_debugfs_init`); el nombre **no afirma** equivalencia semántica. Se registra así para que el nombre
no se lea como una identidad de cliente.

## 5 · `NOMENCLATURE_CLASSIFICATION` de los 11 usos (N-1…N-11)

**No se corrige ninguno.** Clasificación pedida: cuál es nomenclatura histórica incorrecta/ambigua y
cuál ya expresa la entidad técnica. Refs completas en `R1-ACTORS-INVENTORY-20260926.md` §7.

| # | Ubicación | Expresa la entidad técnica… | `CLASS` | Dónde pesa |
|---|---|---|---|---|
| N-1 | `AGENTS_OWNERSHIP_MATRIX…EVIDENCE` = `"card1 / 8 attributable client(s)"` | **no**: cuenta **FDs** y usa el término **RETIRED** | `HISTORICAL_NOMENCLATURE_INCORRECT` (×2 defectos) | ruta que alimenta `OWNERSHIP`. Artefacto preservado → no reescribible |
| N-2 | `OWNERSHIP-AUDIT-HOST-C…:74-88` «clientes *reales*», «la única RX550 client-visible es `Xwayland`» | **no**: «cliente» = **proceso** | `HISTORICAL_NOMENCLATURE_INCORRECT` | captura preservada |
| N-3 | `VFIO-FEASIBILITY-AUDIT…:188` «Observed clients included Xwayland, KWin-related desktop services, `ksmserver`» | **no**: mezcla **procesos** y una **categoría** | `NOMENCLATURE_INCORRECT` | auditoría preservada |
| N-4 | `R1-C1-CORRECTION-CLOSURE…:350` «DRM clients in debugfs … 4 client entries» | **sí**: la unidad correcta (4 `drm_file`; `drm_debugfs.c:92`) | `NOMENCLATURE_AMBIGUOUS` | evoca proceso; debería decir «4 `drm_file`» |
| N-5 | `collector:2345, 2439, 2907` etiqueta `"no DRM client"` | **no**: «cliente» = **proceso/tenedor** | `NOMENCLATURE_INCORRECT` (contradicción interna con N-4 y con el core) | **código**; no autorizado |
| N-6 | `collector:1094, 1128, 1602, 2846, 2907` | **sí**: enumera confusiones a evitar | `NOMENCLATURE_CORRECT` | layk del modelo |
| N-7 | `PROTOCOLO-AB-LIMPIEZA-BACKGROUND:197` «`renice +5 firefox`» | **no**: nombre de **aplicación** como **proceso**; el proceso observado es `firefox-bin`; y es comando **previsto**, no ejecutado | `NOMENCLATURE_INCORRECT` | documento de protocolo vivo |
| N-8 | `DOCUMENTATION-TOPICS.md:655-657` | **sí**: es un **tema**, no una afirmación | `NOMENCLATURE_CORRECT` | ninguna |
| N-9 | `R1-REPAIRED-…:371-372` «"12 clientes" — `REFUTED`: son 12 FDs en 4 procesos» | **sí**: rechaza explícitamente la conversión | `NOMENCLATURE_CORRECT` | modelo funcionando |
| N-10 | `R1-DRM-FDS-ENUMERATED-FIX-RECORD…:146` «a host with no DRM client at all» | **no**: hipótesis sobre **proceso** | `NOMENCLATURE_AMBIGUOUS` | contradice N-4/N-5 |
| N-11 | `R1-REPAIRED-…:371`, `R1-ATTRIBUTABLE-DEFINITION-RESOLUTION:189` | **sí**: tabla que rechaza FDs→clientes | `NOMENCLATURE_CORRECT` | modelo funcionando |

**Recuento**: 4 `HISTORICAL_NOMENCLATURE_INCORRECT` (N-1, N-2, N-3, N-7) · 1
`NOMENCLATURE_INCORRECT` (N-5) · 2 `NOMENCLATURE_AMBIGUOUS` (N-4, N-10) · 4
`NOMENCLATURE_CORRECT` (N-6, N-8, N-9, N-11). Ninguno corregido: la corrección exige fijar la unidad
normativa, y eso es `NORMATIVE_REQUIREMENT_REWRITE`, fuera de esta etapa.

## 6 · `DECISION`

```
TECHNICAL_MODEL                   = CLOSED
DOCUMENTATION_DEFECT              = CLOSED   (P09 corregido; 6 excepciones registradas)
PROJECT_MAPPING                   = NOT_ATTEMPTED
HUMAN_MIXED_TERM                  = RETIRED   (NO_INTERPRETAR)
REQUIREMENT_INTENT_RECONSTRUCTION = NOT_ATTEMPTED
NORMATIVE_REQUIREMENT_REWRITE     = OPEN  (humano; fuera de esta etapa)
ATTRIBUTABLE_AS_PROPERTY          = DOES_NOT_EXIST
SEPARATION_TABLE                  = 18 conceptos, 17 propiedades (P-1..P-17 / S-1..S-7)
FD_EQ_DRM_FILE                    = REFUTED  (N:1 por dup/fork)
CLIENT_UNQUALIFIED                = PROHIBITED (tabla §4)
NOMENCLATURE_FIXED                = NONE  (11 clasificados, 0 corregidos)
CODE_OR_TEST_OR_AGENTS_CHANGES    = NONE
```

```
término humano ambiguo  ->  RETIRED / NO INTERPRETAR  ->  propiedades independientes  ->  modelo cerrado
```
