# R1-ATTRIBUTABLE-NODE-ROWS-REQUIREMENT-20260926

`NORMATIVE_STATUS = PROPOSED_NOT_ACTIVE`
`DOCUMENT_KIND = REQUIREMENT_PROPOSAL`
`TEMPORALITY = CURRENT` (el estado del requisito que este documento intenta resolver, no del host)
`HOST_SCOPE = NO APLICA` — un requisito no observa un host. La evidencia de host citada abajo
procede de `HOST-C` y de los bundles R1, y es `HISTORICAL` respecto del collector vigente.
`CODE_CHANGED = NO` · `COLLECTOR_CHANGED = NO` · `TESTS_CHANGED = NO`
`AGENTS.md = UNCHANGED` · `README.md = UNCHANGED`

> **Este documento no sustituye a `AGENTS.md:176-179`.** La fuente normativa del proyecto para
> requisitos es `AGENTS.md` (categoría `PROJECT_NORM` según
> `01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-CENSUS.md:92`, y `MIG-07.9` §legitimidad).
> `AGENTS.md` no fue modificado en esta ronda y no puede serlo bajo la autorización vigente.
> Este texto es un **addendum propuesto**, no norma vigente, hasta que alguien con autoridad sobre
> `AGENTS.md` decida incorporarlo.

---

## 0 · Qué falta en el requisito vigente

`AGENTS.md:176-179` dice, literal:

> `FULL` requires complete attributable evidence for the RX550's card and render nodes,
> identified by PCI identity rather than by node name, plus user/root namespaces, DRM FDs,
> writers, agents, PM, governor, IRQ, scheduler, read-ahead, storage, Btrfs, guard and restore.

El texto **no desciende** la palabra *attributable* hasta una información observable por
descriptor. De ahí el vacío que esta propuesta intenta cerrar, y de ahí también el hecho de que
dos filas del mismo criterio hayan podido usar dos definiciones incompatibles de la misma palabra
sin que ninguna fuente las contradijera.

`AGENTS.md:184-186`, inmediatamente después del requisito, ya establece el marco:

> This is a requirement, not a description of any implementation. An implementation satisfies it
> by being executed against the requirement, never by naming it.

Este addendum se redacta para ser ejecutado contra el requisito, no para ser nombrado por él.

---

## 1 · PROCEDENCIA

Las cuatro capas se mantienen separadas. Ninguna inferencia se presenta como requisito humano.

### 1.1 `HUMAN_REQUIREMENT`

| # | Elemento | Fuente | Qué exige literalmente |
|---|---|---|---|
| H-1 | Los dos nodos nombrados | `AGENTS.md:176` | card **y** render, ambos |
| H-2 | "identified by PCI identity rather than by node name" | `AGENTS.md:176` | identificar el dispositivo por PCI, no por `cardN` |
| H-3 | "card and render nodes … plus … **DRM FDs**" | `AGENTS.md:176-178` | la atribución a nivel de FD es un ítem **distinto** de la cobertura de los nodos |
| H-4 | "attributable" como adjetivo de *evidence* | `AGENTS.md:176` | la evidencia es atribuible; el texto **no** dice de qué |
| H-5 | Ausencia ≠ disponibilidad | `AGENTS.md` §Evidence | la ausencia de un dato no es disponibilidad |
| H-6 | PCI identity por BDF, no por nombre | `AGENTS.md:32` | identificador de dispositivo |

**Lo que el requisito humano NO contiene** (relevante para la validación §4):

- no enumera ninguna clave de `fdinfo`;
- no nombra `drm-client-id`, `drm-pdev`, `pasid` ni `drm-driver`;
- no afirma que *attributable* sea una propiedad por descriptor, por cliente o por proceso;
- no dice qué hacer cuando un campo falta.

`drm-client-id` y `pasid` aparecen en `AGENTS.md:104` **únicamente** como ejemplo de disciplina de
procedencia, citando `clients_pasid_attributable`, que es un **nombre de fila creado por el
agente**. No es antecedente del requisito.

### 1.2 `AGENT_FORMALIZATION`

| # | Elemento | Ubicación | Regla que introduce |
|---|---|---|---|
| F-1 | Las 11 filas de `OWNERSHIP_CRITERION_ROWS` | `privileged_read_collector.py:1556-1570` | La frase "card and render nodes" se divide en dos filas |
| F-2 | `"DRM card node FD table complete and attributable"` | `:1557-1558` | *attributable* pasa a ser un **conyuncto de la fila de nodo**, y por tanto una propiedad medida **por descriptor** |
| F-3 | `DRM_ATTRIBUTION_FIELDS = ("drm-client-id", "drm-pdev", "pasid")` | `:1033` | Esos tres son *the* campos de atribución |
| F-4 | Umbral `all()` en la fila agregada | `:1662-1667` | Los tres son requeridos. Razonado en `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md:72-84` para **`drm_fds_enumerated`**, otra fila |
| F-5 | Umbral `any()` en las filas de nodo | `:2783` | Basta uno. **Sin justificación escrita**: el comentario del código defiende el conyuncto de completitud, no la agregación |
| F-6 | `card_clients` como conteo de FDs | `:2866` | Ver §5, F-02 |

`fdinfo_attribution` **delega explícitamente** la agregación al caller (`:1045-1046`: *"the caller
decides what that means"*). Sus dos call sites eligieron `any()` y `all()`. **No hay definición a
nivel de proyecto que los arbitre** — ese es el vacío que este addendum vuelve explícito.

### 1.3 `EXTERNAL_SPEC`

`docs.kernel.org/gpu/drm-usage-stats`, kernel **7.3.0-rc4**, consultado **2026-09-26`.
`EXTERNAL` — no es evidencia sobre este host.

| Clave | Categoría en la spec | Identifica |
|---|---|---|
| `drm-driver` | **Mandatory** fully standardised | el driver |
| `drm-pdev` | **Optional** fully standardised | el dispositivo PCI |
| `drm-client-id` | **Optional** fully standardised | el cliente DRM (`struct drm_file`), "to distinguish duplicated and shared file descriptors" |
| `pasid` | **ausente de la spec** | `NOT_ESTABLISHED` |

Acoplamiento declarado por la spec: la unicidad de `drm-client-id` es "globally unique, **or
unique within the scope of each device, in which case `drm-pdev` shall be present as well**".

`pasid`: dos búsquedas sin resultado; `git.kernel.org` y `elixir.bootlin.com` inaccesibles
(bot-wall). **No se asserta nada sobre su semántica requerida.** No es clave estandarizada: la
spec reserva el prefijo `drm-` a las estandarizadas y `driver_name-` a las de driver, y `pasid` no
tiene ninguno de los dos.

### 1.4 `INFERENCE`

Marcado como inferencia, **no** como requisito:

| # | Inferencia | Base | Fuerza |
|---|---|---|---|
| I-1 | *attributable* es una propiedad **por descriptor** | F-2 lo dice, pero F-2 es formalización del agente | Débil |
| I-2 | El requisito exige distinguir **clientes** y no solo FDs | H-3 separa "DRM FDs" de los nodos, lo que sugiere que la atribución por FD es otra fila | Débil |
| I-3 | `drm-client-id` + `drm-pdev` es el par mínimo coherente con la spec | El acoplamiento de la spec | Media; es la lectura más ajustada, sigue siendo inferencia |
| I-4 | El dispositivo ya está identificado por sysfs + symlink, así que `drm-pdev` sería corroboración y no fuente | `GPU_PCI_TARGET` + resolución por BDF | Media |
| I-5 | `pasid` aportaría relación con un espacio de direcciones que el proyecto no consume | `R1-C1-CORRECTION-CLOSURE-20260926.md:345-384` registra proceso→engine como `NOT_AVAILABLE` | Débil |

---

## 2 · PROPUESTA DE REQUISITO

Texto propuesto. **No prescribe campos, ni umbrales, ni unidad de conteo.**

> ### Atribuible — filas de nodo
>
> Para cada nodo DRM de la RX550 cuya tabla de descriptores se declara completa, debe ser posible
> establecer, **por cada descriptor abierto sobre ese nodo**:
>
> **(1)** a qué proceso pertenece el descriptor;
>
> **(2)** que el descriptor está efectivamente asociado a ese nodo, corroborado por la identidad
> PCI del dispositivo y no por su nombre;
>
> **(3)** si dos descriptores del mismo nodo corresponden al mismo cliente DRM o a clientes
> distintos.
>
> La evidencia utilizada para establecer (1)–(3) se registra **por descriptor**.
>
> La fila no se declara satisfecha si algún descriptor del nodo no permite establecer las
> propiedades requeridas.
>
> La ausencia de cualquier dato utilizado como evidencia se trata como ausencia de evidencia,
> nunca como disponibilidad.
>
> Este requisito **no prescribe qué claves de `fdinfo` se deben utilizar ni cuáles son
> obligatorias**. La elección de instrumentación debe tener su propia procedencia y justificación,
> y no se deduce de este texto.
>
> **Pendiente de decisión humana:** si (3) significa "distinguir clientes" o "contar descriptores",
> porque la redacción de la fila emplea la palabra *client* y el conteo disponible es de
> descriptores. Ver §5.

### 2.1 Notas de revisión sobre el texto propuesto

| # | Observación | Tipo |
|---|---|---|
| N-1 | "cuya tabla de descriptores se declara completa" **presupone** la completitud en vez de definirla. Al añadirle requisitos de atribución, *complete* y *attributable* quedan en el mismo enunciado y pueden leerse como un concepto único. **Defecto real de la redacción propuesta.** | Corregir antes de adoptar |
| N-2 | "el collector debe poder establecer" nombra al implementador. Consistente con el estilo de `AGENTS.md` §Ownership, que también nombra `lsof` y `fuser`. Se conserva, pero conviene que sea deliberado. | Aceptable |
| N-3 | (1) y (3) son `INFERENCE` (I-1, I-2), no `HUMAN_REQUIREMENT`. Si se adoptan como requisito hay que aceptarlos como decisión, no como transcripción. | Declarar |
| N-4 | (2) sí está respaldado por texto humano (H-2, H-6). | Sólido |
| N-5 | El texto no dice qué hacer con un campo ausente. Correcto: la semántica de estado es otra decisión (§6). | Correcto |
| N-6 | El texto no nombra `pasid`, `drm-client-id`, `drm-pdev` ni `drm-driver`. Verificado. | Correcto |
| N-7 | El texto no menciona `any()` ni `all()`. Verificado. | Correcto |

**Propuesta de corrección de N-1**, si se adopta el texto: separar las dos propiedades en
enunciados distintos, de modo que la atribución se exija para un descriptor **cuya** completitud
ya fue establecida, y ninguna de las dos se defina por la otra.

> ### Completitud de la tabla de descriptores — filas de nodo
>
> Para cada nodo DRM de la RX550 cuya tabla de descriptores se declara completa, debe ser posible
> establecer, para cada proceso observado, que su tabla de descriptores pudo enumerarse completa y
> que ningún descriptor de esa tabla quedó sin resolver.
>
> ### Atribuible — filas de nodo
>
> Para cada nodo cuya tabla de descriptores se declara completa según el requisito anterior, y
> **por cada descriptor abierto sobre ese nodo**, debe ser posible establecer: [… (1)–(3) …]

Esto mantiene "completo" y "atribuible" como dos propiedades con dos enunciados y dos unidades
(universal sobre procesos, una sobre descriptores), y no fusionadas.

---

## 3 · DECISIONES DE IMPLEMENTACIÓN EXPRESAMENTE EXCLUIDAS DEL REQUISITO

Ninguna de estas puede quedar en el texto del requisito. Se registran aquí para que no se
introduzcan por derivación al implementar.

| # | Decisión | Estado |
|---|---|---|
| X-1 | `any()` — basta un campo | `EXCLUDED`. Sin antecedente humano; sin respaldo en la spec |
| X-2 | `all()` — los tres campos | `EXCLUDED`. Registrado en `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md:72-84` para **otra** fila; sin registro de extensión a las filas de nodo |
| X-3 | `drm-client-id` obligatorio | `EXCLUDED` |
| X-4 | `drm-pdev` obligatorio | `EXCLUDED`. Opcional en la spec, y el collector ya identifica el dispositivo por sysfs |
| X-5 | `pasid` obligatorio | `EXCLUDED`. `NOT_ESTABLISHED`; no figura en la spec |
| X-6 | `drm-driver` obligatorio | `EXCLUDED`. Es el único mandatory de la spec, pero el requisito humano nunca pide identidad de driver por descriptor. **No se derivó una cuarta definición por esto.** |
| X-7 | "conteo de FDs" como unidad de la fila | `EXCLUDED`. Ver §5 |
| X-8 | "conteo de clientes DRM" como unidad de la fila | `EXCLUDED`. Ver §5; y ningún dato del host autoriza ese conteo |

---

## 4 · VALIDACIÓN DEL REQUISITO PROPUESTO

| # | Comprobación | Resultado |
|---|---|---|
| V-1 | ¿Prescribe campos? | **NO.** Verificado sobre el texto de §2: no aparece `drm-client-id`, `drm-pdev`, `pasid` ni `drm-driver` |
| V-2 | ¿Prescribe `any()`/`all()`? | **NO.** No hay comparación ni conjunción de campos |
| V-3 | ¿Confunde FD con client? | **NO en el texto**, pero **SÍ en la premisa**: "tabla de descriptores" es correcto y §5 deja la unidad de conteo explícitamente pendiente. Riesgo residual en la redacción de la fila, no en el requisito |
| V-4 | ¿Depende de PASID? | **NO.** `pasid` no aparece |
| V-5 | ¿Convierte la spec externa en requisito humano? | **NO.** §1.3 está etiquetado `EXTERNAL` y §1.1 no cita campos. La spec sustenta (2) por vía de H-2/H-6, que es texto humano, no la spec |
| V-6 | ¿Es falsificable? | **SÍ.** Ver §6: un descriptor cuyo proceso, cuyo nodo, o cuya relación cliente/cliente no pueda establecerse vuelve la fila no satisfecha |
| V-7 | ¿La unidad de evidencia es explícita? | **SÍ**: "por cada descriptor abierto sobre ese nodo", y "se registra por descriptor". La unidad de **conteo** de la fila queda declarada pendiente, no oculta |
| V-8 | ¿"complete" y "attributable" quedan fusionados? | **NO tras la corrección de N-1.** En el texto original de §2: **SÍ, parcialmente** — por eso N-1 se corrige antes de adoptar |

---

## 5 · F-02 — `card_clients` no es un conteo de clientes

`OPEN` · problema **separado** de §2 · **no** se corrige el nombre en esta ronda.

### 5.1 Hecho

```
node_attributable[target] += 1        (una vez por entrada de gpu_clients)
```

`privileged_read_collector.py:2776-2784` y `:2866`. Cada entrada de `gpu_clients` es **un
descriptor**: lleva `"source": f"/proc/{pid}/fd/{fd}"`. **No existe deduplicación por
`drm-client-id` en ninguna parte del collector.**

| | |
|---|---|
| `card_clients` **es** | cantidad de **descriptores** del nodo que satisfacen el predicado de atribución vigente |
| `card_clients` **NO es** | cantidad de `drm-client-id` distintos, ni de clientes DRM, ni de procesos |
| Nombre actual | `card_clients` / `render_clients`, y el string `"{node} / N attributable client(s)"` |

### 5.2 Evidencia de la indistinguibilidad

- **Ejecución, worlds sintéticos**: 1 proceso con 2 descriptores al mismo nodo y **mismo**
  `drm-client-id` → `card_clients = 2`, clientes = **1**. Con descriptores compartidos entre 2
  procesos y el mismo `drm-client-id` → `card_clients = 2`, clientes = **1**.
- **Spec**: `drm-client-id` existe, textualmente, "to distinguish **duplicated and shared** file
  descriptors". FD y cliente son cosas distintas **por diseño del kernel**.
- **Host, histórico** (`R1-C1-CORRECTION-CLOSURE-20260926.md:321-368`): `kwin_wayland` (pid 1825)
  tiene **9 descriptores** (5 en `card1`, 4 en `renderD129`) y **3** `id` distintos en debugfs
  (`47`, `65`, `71`). Los tres conteos difieren dentro de la misma observación.
  Salvedad del propio documento: el barrido (~02:37) y la lectura de `clients` (~02:42) son
  **ventanas distintas**; no se afirma correspondencia entre ellas.

### 5.3 Consecuencia y alcance

`FD ≠ DRM client ≠ proceso ≠ nodo DRM`. El mismo cliente puede aparecer en `card1` y en
`renderD129`, o sea que la fila es **por nodo**, no por cliente: eso está correcto.

**No se corrige el nombre en esta ronda**: renombrar `card_clients` tocaría el collector y sus
tests, fuera de la autorización vigente. Se registra aquí como `OPEN` y se referencia desde §2
como la pregunta pendiente de unidad de conteo.

---

## 6 · FALSIFICACIÓN

Un requisito sin falsificador declarado no es un requisito. Estos tres lo falsifican.

**Falsificador 1 — proceso no establecible.**
Un descriptor del nodo cuyo proceso propietario no puede establecerse. El collector no puede
afirmar (1). La fila **no** puede declararse plenamente atribuible.

**Falsificador 2 — asociación con la RX550 no establecible.**
Un descriptor cuya asociación con el nodo no puede establecerse por identidad PCI, y solo por
nombre de nodo o por suposición. El collector no puede afirmar (2). Contradice `AGENTS.md:32` y
`AGENTS.md:176`. La fila **no** puede declararse plenamente atribuible.

**Falsificador 3 — identidad de cliente indeterminable.**
Dos descriptores del mismo nodo para los cuales no puede determinarse si representan el mismo
cliente DRM o clientes distintos. El collector no puede afirmar (3). La fila **no** puede declararse
plenamente atribuible.

**Sobre los falsificadores 1 y 2.** Son derivaciones directas de `HUMAN_REQUIREMENT` H-1/H-2 y de
`AGENTS.md:32`, y no dependen de ninguna decisión de campos. El falsificador 3 depende de (3), que
es `INFERENCE` (I-2): si se rechazara (3), este falsificador cae con ella, y la fila volvería a
medir solo (1) y (2). **Esa es la dependencia que hay que resolver al decidir (3).**

### 6.1 Lo que esta sección NO decide

Que la fila "no pueda declararse plenamente atribuible" **no fija el resultado operativo**. La
semántica de estado — `FAIL`, `PARTIAL`, `UNKNOWN`, o una combinación por propiedad — es una
decisión distinta, no tomada aquí, y no debe heredarse de la redacción de este documento.

`AGENTS.md:106` impide anyways promover `UNKNOWN`, `NOT_AVAILABLE` o `CONFLICT` a `PASS`. La
elección entre esas salidas y `FAIL` no se resuelve con este addendum.

---

## 7 · CONFLICTOS CON DOCUMENTACIÓN EXISTENTE

Ninguno se sobrescribe. Todos se citan con ubicación.

| # | Documento | Ubicación | Relación | Acción |
|---|---|---|---|---|
| C-1 | `AGENTS.md` §Ownership | `:176-179` | **Fuente normativa.** No desciende *attributable*. Este documento propone hacerlo y **no lo sustituye** | Pendiente de decisión humana sobre `AGENTS.md` |
| C-2 | `R1-COLLECTOR-INDEPENDENT-REVIEW-20250925.md` | `:151` | Hallazgo `MED-3`: las dos filas comparten una entrada. Veredicto histórico, no reescribir | Anotación aditiva pendiente |
| C-3 | `R1-DEFECT-FIX-RECORD-20260926.md` | `:224` | `MED-3 = NON_BLOCKING_LIMITATION`, "Sound por entelación… dependencia conceptual". **El veredicto histórico no se altera.** Este documento no lo confirma ni lo refuta: enumera las propiedades, no su código | Anotación aditiva pendiente |
| C-4 | `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md` | `:37-41`, `:47-64`, `:72-84` | Razonamiento de `all()` para `drm_fds_enumerated`. **No se extiende a las filas de nodo** sin decisión | Referenciado, no modificado |
| C-5 | `R1-C1-CORRECTION-CLOSURE-20260926.md` | `:321-384` | Evidencia de host: `12/12/12`, la distinción FD/client/proceso, y proceso→engine `NOT_AVAILABLE`. En `:322-327` la prosa ya confunde FD con client | Referenciado; la confusión de prosa se registra en §5 |
| C-6 | `DOCUMENTATION-CENSUS.md` | `:92` | `AGENTS.md` es `REFERENCE`/`PROJECT_NORM`. Un documento nuevo que se lea como requisito primario crearía **confusión de fuente con autoridad** | Mitigado por `NORMATIVE_STATUS` |
| C-7 | `DOCUMENTATION-ROUTER.md` | §3, dominio `D8 · OWNERSHIP` | El router **no conoce** este documento. `README.md` declara al router como punto de entrada, y el router §8 manda `ESCALATED` al censo §15 para topics no listados | **`REFERENCE_STATUS=UNREGISTERED`** — reportado, **no reparado** (fuera de la autorización de requisito) |

---

## 8 · ESTADO Y LO QUE ESTE DOCUMENTO NO HACE

`REQUIREMENT_STATUS = AMBIGUOUS` en `AGENTS.md`. Este documento **no cambia** ese estado: pasa
`AMBIGUOUS` a **`AMBIGUOUS_DEFINIDO_Y_PROPUESTO`** — el vacío quedó nombrado y hay un texto
propuesto, pero el texto no está adoptado.

No se hizo, y no se hizo deliberadamente:

- no se modificó `AGENTS.md`, `README.md`, el collector, los tests, ni ningún documento histórico;
- no se eligió `any()`, `all()`, ni ninguna definición de campo;
- no se renombró `card_clients` (F-02 queda `OPEN`);
- no se decidió la semántica de estado de §6.1;
- no se decidió la unidad de conteo de la fila;
- no se creó ningún topic en el router (C-7).

Todo lo que este documento afirma como hecho es `OBSERVED` o `SUPPORTED` y está citado. Lo que es
inferencia está marcado `INFERENCE` en §1.4 y no se usa como requisito.
