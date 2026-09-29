# R1 COLLECTOR — INDEPENDENT DIFF REVIEW

```
REVIEW_STATUS=COMPLETE
REVIEW_MODE=READ_ONLY_NO_EXECUTION_NO_SUDO
CRITICAL_FINDINGS=0
HIGH_FINDINGS=3
MEDIUM_FINDINGS=4
LOW_FINDINGS=4
R1_SAFE_TO_AUTHORIZE=NO
```

**Fecha:** 2026-09-25 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Objeto:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Nada se corrigió.** `COLLECTOR_HASH_AFTER` sigue siendo `a2cf80c7…`.

| | |
|---|---|
| `COLLECTOR_HASH_BEFORE` | `41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9` |
| `COLLECTOR_HASH_AFTER` | `a2cf80c7cc28f27e48fc637df999a27a1d3ee2bbce1339d84f0cbf295f57f2f0` |
| delta | `+1218 −108`, 1158 → 2268 líneas |

**El resultado que importa: 43/43 tests verdes y tres defectos ALTOS.** El suite mapea los
GAP del encargo, no los modos de fallo del código nuevo, y por eso no los detectó. Eso es un
hallazgo sobre el suite, no solo sobre el collector.

---

## 1. Hallazgos ALTOS

### HIGH-1 · El BDF puede quedar "resuelto" a partir del texto de un enlace que no existe

`discover_drm_nodes()` obtiene el BDF aplicando `BDF_RE` sobre `os.path.realpath(class/drm/<nodo>/device)`.
`os.path.realpath` **no es estricto**: resuelve la cadena de enlaces hasta donde existe y
devuelve la cadena. Si `<nodo>/device` falta, la cadena devuelta **igual contiene el BDF**,
porque `class/drm/<nodo>` es a su vez un enlace que apunta dentro de
`…/0000:01:00.0/drm/<nodo>`.

Sondeo con árbol sintético en el que se eliminó el enlace `device` del nodo:

```
reverse card candidate bdf    : ['0000:01:00.0']
reverse card candidate driver : [None]
GPU_IDENTITY_STATUS           : PROVEN
GPU_CARD_NODE                 : card1
```

Es decir: `PROVEN` con el driver por nodo a `None`. La prueba que el código llama «bidireccional»
degrada a «el enlace de class apunta dentro de un directorio cuyo nombre contiene un BDF».

**Impacto.** En un host sano la respuesta sigue siendo correcta, así que **no hay atribución
falsa hoy**. Pero la afirmación de `COLLECTOR-CHANGE-RECORD` §3 («reverse: realpath → BDF») y la
docstring de `discover_drm_nodes` sobrestimen la evidencia. Un `device` ausente — degradación de
udev, sysfs recreado, bioshide — pasaría sin señal. Exactly el modo de fallo que el encargo
prohíbe: un binding nodo→BDF no demostrado tratado como demostrado.

**Corrección requerida (no aplicada).** Antes de aceptar un nodo como candidato, exigir
`(class_dir / name / "device").is_dir()` y exigir que la lectura del driver por nodo tenga éxito;
si no, excluirlo con `exclusion_reason` y tratarlo como `BDF_UNPROVEN`.

### HIGH-2 · `classify()` se ejecuta dos veces y duplica clientes y contadores

`main()` recorre **todos** los PIDs en el primer bucle y llama a `classify()` en cada uno
(incluye todos los incrementos de `coverage`, `root_fd_errors`, `gpu_clients` y
`storage_clients`). El segundo bucle, sobre `service_pids`, vuelve a llamar `classify()` para
cualquier PID que no esté ya en `interesting` — y ese PID **ya fue contado** en el primer bucle.

Consecuencias:

- `coverage[fd_complete_pids | maps_* | namespace_ok | root_pids]` inflados.
- `root_fd_errors` recibe entradas duplicadas.
- **`gpu_clients` y `storage_clients` reciben filas de cliente duplicadas** para el mismo
  `(pid, fd, target)`. `current_keys` es un `set` y deduplica, pero `gpu_clients` (la lista
  emitida) y `new_gpu_clients` no: `active_gpu_clients` y
  `additional_gpu_fd_count_vs_parent` pueden sobrecontar.

**Estado actual.** Latente para la lista actual de 15 unidades: cada nombre de unidad casa con
una palabra de `KEYWORDS` (`irqbalance`, `systemd`, `kalm`, `tuned`, `udisks`, `baloo`,
`sysstat`, `autopilot`, `power-profiles`), así que todas caen en `interesting` en el primer
bucle y el segundo no clasifica ninguna. **Es un accidente de la lista de palabras, no una
guarda.** Basta renombrar una unidad o añadir una sin palabra clave para que la duplicación
aparezca sin aviso.

**Corrección requerida (no aplicada).** Eliminar el segundo `classify()` y reutilizar el
elemento ya calculado, o mover los contadores fuera de `classify()` y contarlos una sola vez
por PID.

### HIGH-3 · Las condiciones de namespace no son independientes y una usa el denominador equivocado

```python
"root_namespace_ok":            coverage["namespace_ok"],
"user_namespace_ok":            coverage["namespace_ok"],
"root_namespace_complete":      coverage["namespace_ok"] == coverage["total_pids"],
"user_namespace_complete":      coverage["namespace_ok"] == user_pids,
```

Un único contador global alimenta las dos filas que `AGENTS.md` §Ownership exige
independientes. Dos consecuencias:

**(a) No hay entrada posible donde root esté cubierto y user no, ni al revés.** Las dos filas
son de hecho la misma condición duplicada. El criterio del proyecto pide evidencia separada para
namespaces de usuario y de root; aquí no puede separarse.

**(b) Error de categoría en el denominador.** `namespace_ok` cuenta **todos** los PIDs, y se
compara contra `user_pids`, que es un tamaño de subconjunto. En HOST-C hay ~199 PIDs root de
~283: si la ejecución privilegiada lee los 283, `namespace_ok = 283` y `user_pids = 84`, luego
`user_namespace_complete = (283 == 84) = False` → la fila se marca **FAIL aunque todas las
namespaces de usuario se hayan leído**. Es un **FAIL incorrecto**: evidencia correcta
reportada como incompleta.

No es fail-open, pero corrompe la matriz que es el propósito de R1.

**Corrección requerida (no aplicada).** Contar namespaces_OK y namespaces_DENIED por separado
para PIDs root y no-root, dentro del propio bucle, y comparar cada población consigo misma.

---

## 2. Hallazgos MEDIOS

**MED-1 · Identidad de almacenamiento no demostrada → `active_storage = 0`, indistinguible de
«sin clientes».** Con `STORAGE_IDENTITY_STATUS != PROVEN`, `disk_names=[]` y `ROOT_SOURCE=None`,
luego `storage_devices=set()`, luego `storage_clients=[]`, luego `active_storage=0`. Ese 0
satisface `ownership_full` y `g02`. Es la misma forma fail-open que el problema de `card1` que
justifica este trabajo: **ausencia de evidencia leída como evidencia de ausencia.** Con storage
no probado, `active_storage` debe ser `None`/`UNKNOWN` y el booleano debe ser `False`.

**MED-2 · Los namespaces colapsan todos los modos de fallo en el string `"UNAVAILABLE"`.**
`read_link` sí distingue `PermissionError` de `FileNotFoundError` en su campo `error`, pero
`proc_meta` lo descarta y guarda solo `"UNAVAILABLE"`. Para `maps` existe `MAPS_PERMISSION_DENIED`;
para namespaces no hay equivalente. **Aplicación inconsistente de la regla que el propio GAP 6
creó.**

> **Anotación posterior (2026-09-26). El texto anterior no se modifica ni se retira.**
> Identificación de este hallazgo, para que no se confunda con otro: documento
> `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md`, fecha 20260925, sección "MED-2", línea 127 —
> *"los namespaces colapsan todos los modos de fallo"*. **No** es el `MED-2` de
> `R1-COLLECTOR-INDEPENDENT-REVIEW-2-20260926.md:144`, que es un hallazgo distinto
> (*"Ningún test cubre el caso realista de MED-1"*) y que ese review numera desde `MED-1` otra vez.
> Ninguno de los dos identificadores se renombra.
> Veredicto histórico atribuido a este hallazgo, en
> `R1-DEFECT-FIX-RECORD-20260926.md:209`: `NON_BLOCKING_LIMITATION`. Sigue vigente y no se
> reclasifica. Con posterioridad, `AGENTS.md` V3 (`6fe40b2`) añadió la regla de *swallowed error*
> (`:76`) y *"a name is not a measurement"* (`:40`), ausentes del texto pre-V3 (`54b3ea8`, 0
> ocurrencias). Bajo ellas, el colapso pasó a incumplir una regla vigente: un contador llamado
> `user_namespace_denied` afirmaba una causa de permiso no demostrada. Ese gap posterior, su
> corrección y su verificación están en
> `01-AUDITORIA/R1-NAMESPACE-ERROR-ATTRIBUTION-20260926.md`. Dicha corrección **no** cambió
> `*_namespace_complete`, **no** convierte una desaparición en `PASS` ni en `RACE`, y **no** cierra
> R1. No se ha ejecutado ningún re-barrido privilegiado posterior.

**MED-3 · `card_node_complete` y `render_node_complete` son el mismo valor.** Ambos son
`root_visibility_complete`, una bandera global de «cero errores de lectura de FD en todo el
sistema». Ninguna es específica del nodo, y ninguna puede diferir de la otra. Además
`root_visibility_complete` depende de `unresolved_prior`, que viene del **bundle padre**: parte
del veredicto es función de un artefacto previo.

**MED-4 · `scan_maps` lee hasta 4 MiB por PID para todos los PIDs.** 283+ PIDs × 4 MiB de
lectura transitoria, sin `RLIMIT`. Es read-only y la salida retenida es pequeña, pero es un
coste de recursos nuevo y una superficie de fallo nueva. Además el corte a 4 MiB es **silencioso**:
solo la lista filtrada tiene `truncated`; la lectura cruda no tiene indicador.

---

## 3. Hallazgos BAJOS

- **LOW-1** `"sda"` permanece en `KEYWORDS` (línea 68). Solo es pista de búsqueda; todos los PIDs
  se escanean igual, así que no puede producir un falso negativo. Puede atraer al registro
  `interesting` un proceso cuyo cmdline contenga «sda».
- **LOW-2** El renombrado de esquema es asimétrico: `sda_identity` disappeared pero
  `queue.initial` ganó un sobre `{"STORAGE_METRICS", "block_sysfs", "queue"}` y
  `window.samples[i].queue` cambió de forma **sin documentar** en la tabla de esquema de
  `COLLECTOR-CHANGE-RECORD` §6. Un consumidor que lea `queue.initial.scheduler` obtiene nada.
- **LOW-3** `debugfs …/clients` se corta a 64 KiB sin marca de truncado, igual que el corte de
  4 MiB de `maps`. En un GPU con muchos clientes la lista se trunca en silencio dentro de un
  campo de evidencia.
- **LOW-4** 9 ramas de aborto alcanzables no tienen test: `PCI_DRM_ENUMERATION_ABSENT`,
  `PCI_DRM_ENUMERATION_UNREADABLE`, `DRM_CLASS_ABSENT`, `DRM_CLASS_UNREADABLE`, `ROLE_MISSING`,
  `RENDER_MINOR_NOT_DERIVED`, `DEBUGFS_AMBIGUOUS_MULTIPLE_AMDGPU`, `ROOT_MOUNTPOINT_NOT_FOUND`,
  `STORAGE_BLOCK_NOT_RESOLVABLE` (+ `BLOCK_DEVICE_ABSENT_IN_SYSFS`,
  `BLOCK_SYSFS_REALPATH_UNRECOGNISED`, `BLOCK_ENUMERATION_FAILED`).

---

## 4. Verificaciones que SÍ pasan

| Área | Resultado |
|---|---|
| **Identidad PCI** | `pci_identity()` exige `0x1002`/`0x699f`/`0x030000`/`amdgpu` antes de tocar nodos. `resolve_gpu_identity` retorna `devices=set()` si falla y `main()` aborta antes de cualquier uso. **No hay camino alternativo**: `grep` de `GPU_CARD_NODE`/`devices` no muestra ningún consumidor previo al abort. `PCI_IDENTITY=PROVEN` |
| **Mapeo BDF→DRM** | Sin dependencia de `card1`, `renderD129`, menor número ni orden de enumeración. Ambas direcciones deben coincidir; si no, `DIRECTION_DISAGREEMENT`. Exige exactamente 1 card + 1 render. Todo nodo descartado se registra con BDF y driver. Aborta ante ambigüedad. Salvedad: HIGH-1 |
| **Debugfs** | Minor derivado del render node discoveries. `dri/1` aparece **solo** en una docstring. Requiere marcadores `amdgpu_*` **y** exactamente un dispositivo amdgpu. `NOT_AVAILABLE` en 5 modos distintos. `DEBUGFS_REVIEW=PASS` |
| **Storage** | Ninguna ruta usa `/dev/sda`. Flujo `mountinfo → mount point → source → /sys/class/block → disco padre`. `NOT_PROVEN` en montura apilada, source no-`/dev`, bloque ausente, realpath no reconocido. Un `sda` existente no puede convertirse en fuente: `STORAGE_DISKSTATS_NAMES` se deriva del padre probado. Salvedad: MED-1 |
| **Read-only** | Escaneo AST independiente, **sin allowlist**: 0 llamadas mutantes. Los 3 `replace` son `str.replace` (L755, L1515) o `read_text` (L1057). Los 2 `with` abren `"rb"`. `subprocess.run` aparece **1 sola vez** (el wrapper). Sin `shell=True`, sin `os.environ`, sin `eval`/`exec`/`compile`, sin `ioctl`/`fcntl`/`mount`/`kill`. `READ_ONLY_REVIEW=PASS` |
| **Subprocess** | 5 cabezas: `systemctl show` (verbos solo de lectura), `lsof -nP --`, `fuser -v`, `ps -e`, `tty`. Los nombres de nodo están cerrados por `^card(\d+)$` y `^renderD(\d+)$`, así que el argv solo puede ser `/dev/dri/card<dígitos>` o `/dev/dri/renderD<dígitos>`: **no hay inyección de argumento**. `lsof` usa el terminador `--`. `fuser` no recibe `-k`/`-SIG`. Sin shell. `SUBPROCESS_REVIEW=PASS` |
| **PROC** | `maps`: `MAPS_READABLE` / `MAPS_PERMISSION_DENIED` / `ABSENT` / `ERROR` con la excepción preservada; un `PermissionError` nunca se convierte en `ABSENT`. `scan_fds`: un fallo de `listdir` da `status=ERROR` con el texto de la excepción en `errors`, no una lista vacía. `fdinfo` se lee íntegro (16384 B), donde viven `drm-client-id`, `drm-pdev` y `pasid`. `PROC_REVIEW=PASS` |
| **Namespaces** | Leídos de `/proc/<pid>/ns/*` del **propio** PID, nunca del padre; 7 namespaces; cobertura no se infiere de la del padre. Salvedad: MED-2 (motivo de fallo colapsado) y HIGH-3 (poblaciones) |
| **Namespaces (anotación 2026-09-26)** | La salvedad MED-2 de la fila anterior sigue siendo la registrada entonces; la causa del fallo ahora **se conserva** y se discrimina con `root_namespace_disappeared` / `user_namespace_disappeared`. La fila no cambia de veredicto. Ver `01-AUDITORIA/R1-NAMESPACE-ERROR-ATTRIBUTION-20260926.md`. |
| **kwin** | `compositor_gpu_relation()` solo devuelve `OBSERVED` (FD sobre nodo con BDF probado) o `UNKNOWN`. No existe ruta `kwin → RX550`. Con FD en la otra GPU devuelve `UNKNOWN` con el contraste registrado. `KWIN_REVIEW=PASS` |
| **Boolean** | `ownership_full` con expresión **inalterada**; emitido como `NON_AUTHORITATIVE`; `final.OWNERSHIP` sale de la matriz. `writers_resolved` y `guard_and_restore` vienen de `OWNERSHIP_EXTERNAL_ROWS` y **excluyen el diccionario `observed`**, así que no hay ruta de código que los convierta desde ningún valor. `OWNERSHIP_BOOLEAN_REVIEW=PASS`, con la salvedad MED-1 que hace que el booleano sea fail-open ante storage no probado |
| **Matriz 11** | Las 11 filas existen, cada una con `STATE`/`EVIDENCE`/`SOURCE`/`LIMITATION`/`ROUTE`. `NOT_EVALUATED` no se convierte (bypass explícito). `UNKNOWN` no se convierte. `clients_pasid_attributable` mapea `NOT_AVAILABLE → UNKNOWN`, nunca a `PASS`. El agregado no puede ser `FULL` con filas externas `NOT_EVALUATED`. `MATRIX_11_REVIEW=PASS_CON_CAVEATS` (HIGH-3, MED-3) |
| **Fail-closed** | Verificados por sondeo: PCI vendor/device incorrecto, BDF ausente, GPU ausente con iGPU presente, candidatos múltiples, desacuerdo de dirección, debugfs ausente, montura apilada, source no-`/dev`. Sin fallback en ningún caso. `FAIL_CLOSED_REVIEW=PASS` salvo LOW-4 |
| **Regresiones** | Sin pérdida de capacidad. Preservados: `fdinfo` íntegro, los 7 namespaces, `lsof`/`fuser`, IRQ+afinidad, PM completo (`mem_info_vram_used`, `mem_info_gtt_used`, `pp_dpm_sclk`, `pp_dpm_mclk`, `current_link_speed/width`, `gpu_busy_percent`, `amdgpu_parameters`), `diskstats`, `d_state_count`, `governor_history_unique`, `systemctl_rows` (15 unidades), TTY/recovery, btrfs, gap_records. Payload: 20 → 24 claves, **1 eliminada** (`sda_identity`, renombrada), 5 añadidas. `REGRESSION_REVIEW=PASS_CON_CAVEATS` (LOW-2) |

### Clasificación de literales residuales

| Ocurrencia | Línea | Clasificación |
|---|---|---|
| `"sda"` en `KEYWORDS` | 68 | `SAFE_DYNAMIC` — pista de búsqueda; ningún PID se excluye del escaneo. LOW-1 |
| `{/dev/dri/card1, /dev/dri/renderD129}.` | 374 | `DOCUMENTATION_ONLY` — docstring que describe lo que se eliminó |
| ``dri/1`` | 440 | `DOCUMENTATION_ONLY` — docstring que declara que no se asume |
| `/sys/kernel/debug/dri/1/clients` en el test | test | `TEST_ONLY` — comprueba precisamente que el minor se deriva |
| `card1`/`renderD129` en builders de test | test | `TEST_ONLY` |
| `card1`/`renderD129` como destino de `lsof`/`fuser` | — | **ausente** — 0 ocurrencias funcionales |

---

## 5. Calidad de los tests

**43 tests. No se re-ejecutaron** (registrados en `COLLECTOR-CHANGE-RECORD` §7). Inspección:

- **Comportamiento, no implementación:** la mayoría. 12 tests de resolución construyen un árbol
  sysfs/procfs/debugfs sintético y afirman sobre valores de salida. El árbol **sí** incluye el
  enlace `device` real por nodo y las particiones son hijas de su disco padre — corregido durante
  la fase de implementación. `card0`/`renderD128` y `card2`/`renderD137` cubren los casos de
  renumeración. `/dev/sda` presente pero no root, root en `nvme0n1p3`, candidatos múltiples,
  identidad PCI incorrecta, ausencia de identidad, minor debugfs dinámico, `PermissionError` en
  maps, y el booleano legacy `True` alimentando la matriz.
- **Estructural, no de comportamiento (4):** `test_02_legacy_static_identifiers_are_gone`
  (busca cadenas), `test_capability_matrix_names_real_code` y
  `test_criterion_rows_are_exactly_eleven_and_two_are_external` (afirman constantes del propio
  collector contra números que el test también fija — tautológicos), y las 12 pruebas de
  read-only, que son inevitablemente de forma pero por AST, que es lo correcto para esa clase.
- **Lo que falta y importa:** ningún test cubre la doble contabilidad de HIGH-2, ni el
  storage-no-probado → 0 de MED-1, ni los denominadores de namespace de HIGH-3, ni la
  **exigencia** del enlace `device` de HIGH-1. HIGH-1 se habría detectado con un solo test que
  eliminara ese enlace y afirmara `NOT_PROVEN`; el árbol sintético lo creaba, así que la
suposición nunca se puso a prueba.

**Conclusión sobre el suite:** mapea los 10 GAP del encargo, que es lo que se pidió, y por eso
 puntúa 43/43 mientras el código nuevo tiene tres defectos ALTOS. Lalesson: un suite de
conformidad con una especificación no sustituye a un suite de modos de fallo.

---

## 6. Procedencia

| Comprobación | Resultado |
|---|---|
| `COLLECTOR_HASH_BEFORE` | `41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9` |
| Corresponde al collector previo | **Sí**, byte a byte contra el blob del índice de git (`git show :<path>`) y contra la copia de trabajo. Idénticos |
| `COLLECTOR_HASH_AFTER` | `a2cf80c7cc28f27e48fc637df999a27a1d3ee2bbce1339d84f0cbf295f57f2f0` |
| Modificado en esta revisión | **No**. `a2cf80c7…` antes y después |
| Hash histórico reescrito | **No**. `ROUTING-LOG` `ff9110e9…`, router `9ef58048…`, `AGENTS.md` `d5fa85a4…` sin cambios |
| `COLLECTOR_HASH_BEFORE` en un commit | **No.** `git show HEAD:<path>` devuelve `e3b0c442…`, que es el SHA-256 de la cadena vacía: el fichero fue *staged* (360 rutas), nunca *commiteado*. Su única procedencia es el índice. Conviene tenerlo presente antes de citar ese hash como referencia durable |

---

## 7. Veredicto

```
R1_SAFE_TO_AUTHORIZE=NO
```

No hay defectos CRÍTICOS: el collector es genuinamente read-only, no puede producir
`OWNERSHIP=FULL`, y falla cerrado ante identidad no demostrada. Los tres ALTOS caen
exactamente sobre la lista descalificadora:

- **HIGH-1** → *falsa identidad de GPU*: el binding nodo→BDF puede quedar demostrado por el
  texto de la ruta de un enlace inexistente, con `PROVEN` emitido y el driver por nodo a `None`.
- **HIGH-2** → *atribución incorrecta de clientes*: filas de cliente duplicadas y contadores
  inflados por doble clasificación.
- **HIGH-3** → integridad de la matriz de 11 condiciones: poblaciones de namespace no
  independientes, un denominador incorrecto, y un `FAIL` espurio con cobertura completa.

Los tres son corregibles sin rediseño y sin Privilegio — sonchanges lógicos en ~20 líneas. Pero
**no se corrigen aquí**, por instrucción expresa. Cuando se autorice, la secuencia recomendada es
HIGH-1 → HIGH-2 → HIGH-3 → MED-1, y después añadir los tests de modo de fallo que faltan, antes
de volver a pedir autorización de R1.

```
COLLECTOR_RUNTIME_EXECUTED=NO    PRIVILEGED_EXECUTION=NO    SUDO_INVOKED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  SERVICE_CHANGES=0  SYSFS_WRITES=0
PROCESS_TERMINATED=0  PROCESS_SUSPENDED=0

OWNERSHIP=PARTIAL
BLK_01=NOT_CLOSED
G1=OPEN
```
