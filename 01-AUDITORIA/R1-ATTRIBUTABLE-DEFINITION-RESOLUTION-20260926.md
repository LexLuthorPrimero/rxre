# R1-ATTRIBUTABLE-DEFINITION-RESOLUTION-20260926

`DOCUMENT_KIND = RESEARCH` · `NORMATIVE_STATUS = RESEARCH_ONLY`
No es requisito. No sustituye ni sobrescribe V1, V2, el Bridge ni documento histórico alguno.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO` · `AGENTS.md = UNCHANGED`
`HOST_MEASUREMENT = NONE` · `COMMIT = NO` · **`IMPLEMENTATION_ALLOWED = NO`**

---

## 1 · EXECUTIVE_RESULT

La unidad formal de "cliente" en DRM quedó **establecida con fuente primaria**: es el
**`struct drm_file`**, y `drm-client-id` lo identifica **1:1**. Eso resuelve la pregunta de la
unidad. Lo que **no** queda resuelto es cuál de las relaciones documentadas debe contener una fila
de nodo, porque el requisito humano no la nombra.

**El hallazgo analítico central**: los tres campos de `DRM_ATTRIBUTION_FIELDS` **no pertenecen a la
misma relación**, y por eso `any()` y `all()` están ambos mal construidos — no porque uno u otro
umbral sea correcto, sino porque el predicado mezcla tres relaciones distintas.

| Campo | Qué relación establece realmente | ¿Aporta a "cliente atribuible"? |
|---|---|---|
| `drm-client-id` | `drm_file` ↔ identidad de cliente | **ÚNICO** que la establece |
| `drm-pdev` | `drm_file.minor` → `drm_device` → PCI | **No**: el collector ya la tiene por sysfs+BDF, sin leer fdinfo |
| `pasid` | `vmid` ↔ system PID, **durante un page fault** | **No**: no pertenece a la relación del cliente |

**Consecuencia verificable**: con `any()`, los mundos C, D y G producen nodo `PASS` **sin que exista
identidad de cliente alguno**. Con `all()`, el mundo B —donde el cliente **sí** está identificado—
fallaría por ausencia de `pasid`, que no pertenece a esa relación.

## 2 · CURRENT_DEFINITION

**Requisito humano vigente** (`AGENTS.md:176`, no modificado):
> `FULL` requires complete **attributable** evidence for the RX550's card and render nodes,
> **identified by PCI identity rather than by node name**, plus user/root namespaces, **DRM FDs**, …

**Ejemplo del mismo documento** (`AGENTS.md:103-104`):
> "Requirement: **attribute DRM clients per process**. Formalisation: the row `clients_pasid_attributable`."

**Implementación actual**: `card_complete = root_visibility_complete and any(fdinfo_attribution(...))`
sobre `("drm-client-id","drm-pdev","pasid")`.

**Estado**: el texto humano **no fija la unidad**. Fija el *dispositivo* (PCI) y usa "attributable"
como adjetivo de *evidence*, sin descenderla. El ejemplo `:103` usa "clients per process", pero es
**ejemplo de disciplina de procedencia**, no el requisito de esta fila.

## 3 · ESTABLISHED_RELATIONS

Todas con fuente primaria (`drm_file.c` = K1, `drm_gem.c` = K2, `drm-internals` = S3,
`drm-usage-stats` = S1, `amdgpu/debugging` = S4, `amdgpu/debugfs` = S5).

| # | Relación | Evidencia | Unidad | DIRECT/INFERRED |
|---|---|---|---|---|
| E-1 | `drm_device.filelist` = "**List of userspace clients**, linked through `drm_file.lhead`" | S3 | `drm_file` | DIRECT |
| E-2 | `drm_file` = "tracks DRM state **per open file descriptor**" | S3 | `drm_file` | DIRECT |
| E-3 | `drm_file.client_id = atomic64_inc_return(&ident)`, `static atomic64_t` | K1 | `drm_file` | DIRECT |
| E-4 | `drm-client-id` "should map 1:1 to … `struct drm_file`" | S1 | `drm_file` | DIRECT |
| E-5 | `drm_file.pid = get_pid(task_tgid(current))` → **TGID** | K1 | proceso | DIRECT |
| E-6 | `drm_file.pid` **reasignable** (`drm_file_update_pid`, `rcu_replace_pointer`) | K1 | proceso | DIRECT |
| E-7 | `drm_file.minor` → `drm_device` → `struct device` → PCI | K1, S3 | minor | DIRECT |
| E-8 | `drm-pdev` emitido **ssi** `dev_is_pci(dev->dev)` | K1 | `drm_file` | DIRECT |
| E-9 | `drm-driver` y `drm-client-id` **siempre** emitidos por el core | K1 | `drm_file` | DIRECT |
| E-10 | claves de driver anexadas por `dev->driver->show_fdinfo` **después** del core | K1 | `drm_file` | DIRECT |
| E-11 | `drm_file → object_idr → GEM` **muchos-a-muchos** (import dma-buf/flink) | K2 | GEM handle | DIRECT |
| E-12 | shared/private es **derivado** (`drm_gem_object_is_shared_for_memory_stats`) | K1 | `drm_file` | DIRECT |
| E-13 | `drm-engine-*` **por cliente**, tiempo **acumulado**, **no monotónico** | S1 | cliente | DIRECT |
| E-14 | `drm-total/-shared/-resident/-active` **por cliente**; `active ⊆ resident` | S1 | cliente | DIRECT |
| E-15 | `PASID` = "used to **link a vmid to a system process id**", **en un page fault**, condicional | S4 | vmid | DIRECT |
| E-16 | un `drm_file` pertenece a **exactamente un** `minor` (`drm_is_primary_client`/`render` comparan `drm_file.minor`) | S3 | `drm_file` | DIRECT |
| E-17 | render nodes **no tienen** `drm_master` | S2 | — | DIRECT |
| E-18 | `drm_debugfs_clients_add(file)` = directorio debugfs **por `drm_file`** | K1 | `drm_file` | DIRECT |
| E-19 | `dev->driver->open(dev, file)` invocado **una vez** en `drm_file_alloc()` | K1 | `drm_file` | DIRECT |

### 3.1 Respuestas a la sección A

| Pregunta | Respuesta |
|---|---|
| ¿Unidad formal de "client"? | **`struct drm_file`** (E-1, E-2) |
| ¿Unidad de `drm-client-id`? | **`struct drm_file`**, 1:1, contador **global por boot** (E-3, E-4) |
| ¿Varios FDs → un `drm_file`? | **Sí**: `dup`/`fork` clonan el `struct file`; `client_id` se asigna por `drm_file`, no por FD |
| ¿Varios `drm_file` → un proceso? | **Sí**: `client_id` distinto, `pid` igual |
| ¿Un `drm_file` puede cambiar de proceso? | **Sí** (E-6) |
| `/proc/<pid>/fd/<n>` ↔ `drm_file` | Relación **demostrable**: el symlink da el nodo; el `fdinfo` de ese FD da el `client_id` de ese `drm_file`; el path da el proceso. **No** hay campo que exponga el puntero `drm_file` |

## 4 · PARTIALLY_ESTABLISHED_RELATIONS

| Relación | Qué falta |
|---|---|
| `drm_file → memoria` | E-14 la establece **por cliente**; la atribución a **proceso** requiere además el path `/proc`, y eso es `INFERENCE` |
| `drm_file → engine` | E-13 por cliente; a proceso, `INFERENCE` |
| `PID ↔ amdgpu_gem_info/vm_info` | S5 lista "PIDs using the GPU" sin definir el término; sin puente documentado a `drm_file` |

## 5 · NOT_ESTABLISHED_RELATIONS

`driver_priv → amdgpu_fpriv` · `fpriv → VM` · `VM → PASID` · `PASID → task_info` ·
`PASID ↔ drm_file` · uso de `client_id` dentro de amdgpu · "PIDs using the GPU" ·
relación `job → process` · `dmem` cgroup.

**Causa: `SOURCE_INCOMPLETE`.** El subárbol `drivers/gpu/drm/amdgpu/` fue **404 en 4 hosts**
(raw.githubusercontent, jsdelivr, github.com/raw, sources.debian.org) y **bot-wall en 2**
(git.kernel.org, elixir.bootlin). `drm_file.c` y `drm_gem.c` **sí** se obtuvieron del mismo host,
lo que acota el bloqueo al subárbol y descarta un fallo transitorio.

## 6 · CONFLICTS

| ID | Conflicto | Estado |
|---|---|---|
| **C-1** | `drm-client-id` (cliente DRM) vs "**client ID**" de un page fault amdgpu = **GPU block** (`CB/DB, CPF, CPC, CPG, TCP, SDMA, VCN, JPEG`) | **`CONFLICT_UNRESOLVED`** |
| **C-2** | Tres sentidos de "client" en la misma pila: `drm_file`, `client_id`, `drm_master` (y render nodes no tienen master) | **`CONFLICT_UNRESOLVED`** |
| **C-3** | `drm_file.pid` reasignable vs la lectura de que `pid` identifica al dueño original | **RESOLVED**: el doc dice *"using"*, y el código re-apunta al que usa |
| **C-4** | `drm-pdev` `optional` en spec vs incondicional en PCI | **RESOLVED**: `optional` = el driver puede omitirlo; el core lo emite ssi PCI |
| **C-5** | `client_id` global-por-boot (código) vs spec "global **or** per-device" | **RESOLVED**: cumple el caso fuerte, pero **no estable entre boots** |

## 7 · REFUTED_PREVIOUS_CLAIMS

| Claim previo | Dónde | Estado | Sustituto |
|---|---|---|---|
| "Un mismo cliente puede aparecer en `card1` y en `renderD129`" | **mío**, ronda 1, mundo sintético | **REFUTADO** | E-16: un `drm_file` tiene **un** `minor`. Dos nodos ⇒ dos `drm_file` ⇒ dos `client-id`. **Ese mundo no es representable** |
| "`pasid` es un campo de atribución de cliente DRM" | `R1-DRM-FDS-ENUMERATED-FIX-RECORD:72-84` | **REFUTADO** | E-15: pertenece a `vmid ↔ PID` en un fault |
| "La unidad de atribución es el FD" | `OWNERSHIP_CRITERION_ROWS` | **REFUTADO** | E-1/E-4: la unidad del `client_id` es el `drm_file` |
| "No hay definición de attribution en el kernel" | V1/V2 | **CONFIRMADO** | 0 ocurrencias pertinentes en >10 000 líneas |
| "`pasid` no aparece en la documentación del kernel" | V1/V2 | **CONFIRMADO** y ampliado: tampoco en el código del core leído |

## 8 · REQUIREMENT_GAPS

| # | Hueco | Por qué no lo cierra la evidencia |
|---|---|---|
| G-1 | La **unidad** de la fila de nodo (¿`drm_file`? ¿proceso? ¿ambos?) | `AGENTS.md:176` no la nombra; `:103` es ejemplo |
| G-2 | Si "attributable" exige la relación **cliente**, o solo **proceso**, o ambas | Sin texto que lo diga |
| G-3 | Si `drm-pdev` debe exigirse como **corroboración** de que *este* `drm_file` pertenece a la RX550, o basta la identidad de nodo ya probada | `AGENTS.md:32` exige identidad PCI **del nodo**, no del FD |
| G-4 | Qué hacer si `drm-client-id` falta siendo `optional` en la spec | §17: no hay definición de "attributable" que diga si su ausencia es violación |
| G-5 | Si `drm_file.pid` reasignado invalida una atribución previa | No hay semántica de "ventana" definida |

## 9 · FALSIFICATION_CONDITIONS

| Conclusión | Falsificador |
|---|---|
| La unidad de "client" es `drm_file` | S3/K1 dejaran de llamar "clients" a las entradas de `filelist` |
| `client_id` es 1:1 con `drm_file` | S1 lo negara, o K1 lo asignara por FD |
| `drm-pdev` es redundante para el collector | el collector no pudiera probar el nodo por sysfs |
| `pasid` no pertenece a la relación de cliente | `amdgpu_vm.c` mostrara un campo que enlace `drm_file` a `vm`/`pasid` |
| Un `drm_file` pertenece a un solo nodo | `drm_file.minor` pudiera ser NULL o múltiple |
| `any()` admite mundos sin identidad de cliente | un campo distinto de `client_id` estableciera la identidad de cliente |

## 10 · MATRIZ SEMÁNTICA — MUNDOS (sección H)

`cid`=`drm-client-id` · `pdev`=`drm-pdev` · `pasid`. Las tres **relaciones** son distintas.

| Mundo | cid | pdev | pasid | ¿cliente identificado? | ¿PCI identificado? | ¿proceso atribuido? | ¿VM? | ¿pasid aporta a la fila? | ¿`any()` acepta? | ¿`all()` acepta? |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Y | Y | Y | **sí** | sí (ya sin fdinfo) | sí (vía `/proc`) | no | **nada** | sí | sí |
| B | Y | Y | N | **sí** | sí | sí | no | — | sí | **no** ← cliente sí, pasid no |
| C | Y | N | Y | **sí** | **sí igual** (sysfs) | sí | no | **nada** | sí | no |
| D | N | Y | Y | **NO** | sí | sí | no | **nada** | **sí ← falso positivo** | no |
| E | Y | N | N | **sí** | sí igual | sí | no | — | sí | no |
| F | N | Y | N | **NO** | sí | sí | no | — | **sí ← falso positivo** | no |
| G | N | N | Y | **NO** | sí igual | sí | no | **nada** | **sí ← falso positivo** | no |
| H | N | N | N | **NO** | sí igual | sí | no | — | no | no |

**Lectura**: `any()` acepta **3 de 8 mundos** en los que **no hay identidad de cliente**.
`all()` rechaza el mundo B, donde la relación de cliente **sí** está completamente establecida.
**Ninguno de los dos umbrales es correcto**, porque el predicado mezcla tres relaciones.

**Requisito adicional que cada mundo exigiría**: la identidad de cliente requiere `drm-client-id`
(E-3/E-4) y nada más. `drm-pdev` solo aportaría corroboración de que *ese* `drm_file` está en la
RX550 (G-3). `pasid` no aporta nada a esta fila (E-15).

## 11 · CONTRA-EJEMPLOS (sección J)

| # | Caso | Falso PASS bajo |
|---|---|---|
| 1 | 1 proc + 1 `drm_file` + 1 FD | ninguno |
| 2 | 1 proc + 1 `drm_file` + 5 FDs | contar FDs como clients (F-02) |
| 3 | 1 proc + 2 `drm_file` + 2 cid | ninguno, si la unidad es `drm_file` |
| 4 | 2 procs + GEM compartido | atribuir **memoria** a un solo cliente como exclusiva (E-12) |
| 5 | cid presente, pasid ausente | `all()` → **falso FAIL** (rechaza un cliente válido) |
| 6 | pasid presente, cid ausente | `any()` → **falso PASS** (mundo G) |
| 7 | pdev presente, cid ausente | `any()` → **falso PASS** (mundo F) |
| 8 | task_info apunta a otro TGID | imposible de observar: `task_info` no es visible en fdinfo |
| 9 | VM válida sin PASID | `SOURCE_INCOMPLETE` |
| 10 | PASID eliminado en teardown | `SOURCE_INCOMPLETE` |
| 11 | proceso desaparece durante la lectura | coberturas: `AGENTS.md` V3, regla de carrera |
| 12 | fdinfo legible, campo no expuesto por el driver | `optional` ausente **no** viola la spec (S1) |

## 12 · EVIDENCIA DE HOST (sección L) — qué demuestra cada observación

| Observación | Qué demuestra | Qué **no** |
|---|---|---|
| 12 DRM FDs, 4 procesos | 4 procesos con ≥1 FD | nº de clientes |
| kwin_wayland: 9 FDs, **3** `id` debugfs | `dup`/compartidos existen en la práctica; F02 confirmable | cuáles FDs comparten id (ventanas distintas) |
| `12/12/12` | los tres campos **se emiten** en este host | que sean **necesarios**; que pasid sea persistente |
| `drm_fds_enumerated = PARTIAL` con 1/12 fdinfo ilegible | cobertura de fdinfo parcial | que el nodo no sea atribuible |
| Xwayland: `pasid` presente, `drm-total-cpu=0` | **presencia de pasid ≠ actividad** (S4/E-15) | que use la GPU |
| `card_node_complete = PASS` con `render` también PASS | el acoplamiento original | — |
| agregado `PARTIAL`, `FULL` inalcanzable | 9 filas más bloquean `FULL` | — |

**Ninguna de estas observaciones se usa para decidir la definición.**

## 13 · CLASIFICACIÓN FINAL

### `REQUIREMENT_UNRESOLVED`

No `DEFINITION_PARTIALLY_ESTABLISHED` porque la **unidad** sí quedó establecida (E-1…E-4) pero la
**exigencia** —qué relación debe contener una fila de nodo— no puede derivarse de ninguna fuente:
`AGENTS.md:176` no nombra la unidad, y `:103` es un ejemplo cuya autoridad es `UNKNOWN`.

No `SOURCE_INCOMPLETE` como clasificación principal, aunque el hueco AMDGPU sea real: la pregunta
normativa **no se resuelve** aun con el código de amdgpu disponible, porque el requisito humano no
dice cuál de las relaciones documentadas debe contener la fila. El hueco de fuente **empeora** la
capacidad de recomendar, no cambia la naturaleza de la pregunta.

No `CONFLICT_UNRESOLVED` como principal: C-1 y C-2 son colisiones de **término**, no de
requerimiento, y no bloquean la decisión — la registran.

**Decisión humana que falta, exactamente una**: *¿"attributable evidence for the RX550's card and
render nodes" exige identificar el **cliente DRM** (`drm-client-id`), identificar el **proceso**
(`/proc` path), o ambos?* Todo lo demás —qué campos, qué umbrales, qué estado— se deriva de esa
respuesta y de la evidencia ya reunida.

## 14 · RECOMMENDED_NEXT_STEP

**Una sola acción**: elevar al requisito humano (`AGENTS.md` §Ownership) **una sola pregunta**,
sin proponer respuesta: *¿la atribución exigida es la del cliente DRM, la del proceso, o ambas?*,
y registrar que la unidad de "cliente" ya está establecida como `struct drm_file` con
`drm-client-id` 1:1, y que `drm-pdev` y `pasid` pertenecen a otras relaciones.

**No**propylongo la búsqueda de código AMDGPU: aunque se obtenga, no respondería la pregunta
normativa, y el análisis de la matriz (§10) ya muestra que el predicado actual mezcla relaciones.

## 15 · IMPLEMENTATION_ALLOWED

**NO.** No se propone cambio, no se corrige collector ni tests, no se declara PASS/FAIL de ninguna
implementación, y no se decide `any()` vs `all()`.
