# C1 ISOLATION DESIGN v1.0 — ESPECIFICACIÓN DOCUMENTAL

**Tipo:** especificación de aislamiento previo a C1; no es ejecución
**Estado:** `ISOLATION_DESIGN=PREPARED_FOR_REVIEW`
**Modo:** `SPECIFICATION_ONLY`
**Ejecución:** `NONE`
**C1:** `DEFERRED`
**C1_RUNTIME_VALIDATED:** `NO`
**RUNTIME_MATERIALIZED:** `NO`
**RUNTIME_VALIDATED:** `NO`
**RESTORE_EXECUTED:** `NO`
**RESTORE_VALIDATED:** `NO`

## 0. Invariantes globales

Estos estados no se modifican por esta revisión documental:

```text
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
C1=DEFERRED
C1_RUNTIME_VALIDATED=NO
C1_READY=NO
BTRFS=CONFLICT
BTRFS_CAUSE=UNKNOWN
HDD_FAILURE=NOT_PROVEN
GO_C1=NOT_AVAILABLE
```

Esta especificación no autoriza `C1 --run`, tests, runtime v2, sudo, `systemctl`,
detención de procesos, aislamiento real, cambios GPU/PM/governor/IRQ/scheduler/read-ahead,
tocar `/dev/sda`, benchmarks, A/B, SMART/Btrfs/scrub, GFX8, cambios de código o commit.

Las acciones narradas como futuras son requisitos de diseño, no acciones realizadas.

## 1. Taxonomía de resultados

| Token | Significado | Acción permitida |
|---|---|---|
| `NO_GO_PRE` | Falla antes de cualquier aislamiento; no se inicia C1 | Registrar evidencia; no mutar sistema |
| `ABORT_PRE` | Preflight aborta antes de mutación | Registrar causa; no iniciar C1 |
| `ABORT_GUARD` | Falla durante guard después de posible aislamiento | No continuar a C1; restaurar `touched[]` |
| `ABORT_C1` | C1 falla, se interrumpe o no valida | No retry automático; restaurar y verificar |
| `ABORT_RESTORE` | Restore parcial/fallido o readback no concluyente | No continuar; preservar evidencia y manual review |
| `ABORT_RUNTIME` | Runtime requerido ausente/inválido después de iniciar la fase | No continuar; preservar estado y evidencia |
| `NO_GO_RUNTIME` | Runtime ausente antes de una inicialización autorizada | No crear silenciosamente |
| `NO_GO_AUTH` | TTY, `RUN-C1` o sudo no satisfacen el gate | No solicitar bypass ni detener unidades |
| `RESTORE_PENDING` | Restore requerido después de aislamiento | Esperar readback; no lanzar C1 |
| `RESTORE_UNRESOLVED` | Restore no concluyente o fallido | Preservar evidencia; no continuar |
| `UNKNOWN` | Falta evidencia suficiente | Fallar cerrado para `OWNERSHIP=FULL` y `GO_C1` |
| `SOURCE=UNKNOWN` | No existe fuente para una decisión/requisito | No inventar valor ni causalidad |

`NO_GO` nunca significa “intentarlo de nuevo”. `ABORT` nunca autoriza una acción
adicional. Un proceso detenido es somente una evidencia parcial y nunca prueba por sí
solo ownership completo.

## 2. Ownership

### 2.1 Predicado `OWNERSHIP=FULL`

```text
OWNERSHIP=FULL sólo si:
  identity_fixed
  AND drm_client_inventory_complete
  AND no_unapproved_gpu_clients
  AND writer_scope_complete
  AND systemic_gates_pass
  AND btrfs_identity_matched_same_window
  AND guard_stability_proven
  AND restore_plan_complete_for_declared_scope
```

No se declara `FULL` por gpu libre, una FD cerrada, una unidad detenida, una pantalla
desconectada, un snapshot parcial o una frase como “parece libre”.

### 2.2 Evidencia que permite `FULL`

`OWNERSHIP=FULL` requiere evidencia trazable y simultánea para:

1. identidad de `card1`, `renderD129`, BDF, vendor/device/driver y mappings;
2. inventario completo de clientes en los namespaces relevantes, incluyendo procesos root
   y usuario, FDs y clientes DRM;
3. lista completa de procesos/unidades con capacidad de escribir CPU, IRQ, scheduler,
   read-ahead, storage, GPU, PM o display, con estado y readback;
4. ausencia de clientes o writers no aprobados durante la ventana;
5. readbacks estables de PM, governor, IRQ, scheduler y read-ahead;
6. identidad Btrfs de `/dev/sda2` coincidente dentro de la misma ventana;
7. guard estable con métricas y samples registrados;
8. restore definido para cada mutación permitida.

Si cualquiera de estos elementos es parcial, invisible, contradictorio o `UNKNOWN`,
el máximo estado es `OWNERSHIP=PARTIAL`.

### 2.3 Predicate de inventario completo

Un inventario de clientes se considera completo sólo si cada registro contiene:

```text
namespace_id
pid
uid
comm/cmdline_hash
fd_target
fd_flags
drm_client_id
card/render_node_mapping
observation_timestamp
visibility_status
source_evidence_id
```

La FUTURA fase autorizada deberá obtener vistas root y usuario, reconciliar sus namespaces
y declarar `visibility_status=COMPLETE` para cada proceso/FD relevante. `permission
denied`, overlay no visible, namespace no reconciliado o un campo `UNKNOWN` hace que
`drm_client_inventory_complete=FAIL`. La lista de writers se completa con la misma regla:
unit/process ID, scope, capability, PRE/guard/POST state, writer/readback y source; una
capacidad no accounting mantiene `writer_scope_complete=FAIL`.

### 2.4 Matriz de ownership

| RESOURCE | CURRENT_OWNER | EXPECTED_OWNER | PROOF | FAIL | ABORT | RESTORE_IMPACT | SOURCE |
|---|---|---|---|---|---|---|---|
| `card1` | `MULTIPLE/UNKNOWN`; Xwayland observado en snapshot P0 | `C1_EXPERIMENT_ONLY`; sin cliente no aprobado | BDF/path/node identity + inventario DRM root/user completo + cero cliente no aprobado en la ventana | identity mismatch, inventario incompleto o cualquier cliente no aprobado | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Ninguna acción de proceso en esta fase; si una implementación futura lo modifica, necesita restore explícito | `P0`, `C1-CODE:collect_precheck` |
| `renderD129` | `MULTIPLE/UNKNOWN`; ChatGPT observado en snapshot P0 | `C1_EXPERIMENT_ONLY`; sin cliente no aprobado | Path/BDF identity + FD/client inventory completo | mapping incorrecto, cliente no aprobado o namespace invisible | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No matar/cerrar procesos; cualquier cambio futuro queda bloqueado sin restore | `P0`, `C1-CODE:collect_precheck` |
| `Xwayland` | `OBSERVED_ACCESS_P0` | Sin handle no aprobado durante `FULL` | PID/FD/client ID + namespace/user coverage + recheck de ventana | handle presente, proceso no identificado o cobertura incompleta | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No detener Xwayland aquí; restore de sesión/proceso=`NOT_DEFINED` si se propusiera | `P0:L72-96` |
| Aplicaciones | `PARTIAL/UNKNOWN` | Sólo C1 e instrumentación permitida | Inventario de procesos, FDs, namespaces y actividad atribuible | cualquier aplicación no aprobada o inventario parcial | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No stop/kill; `PROCESS_RESTORE` debe definirse antes de cualquier aislamiento | `P0`, `C1-CODE:process_scan_for_existing_c1` |
| `Mesa/RADV` | Target check existente; provenance en conflicto | Target RX550 `1002:699f`, ICD/driver verificados por corrida | ICD/maps/driver/argv/provenance y hash de fuentes | mismatch, renderer no verificable o provenance conflict | `NO_GO_PRE` | No modificar Mesa; no hay restore que ejecutar | `C1-DOC §GPU`, `DOC-REC` |
| `system-autopilot` | `OBSERVED_WRITER`; timer activo | Sin escritura durante la ventana | Unit state/PID/config/hash y readback de efectos sobre governor/IRQ/scheduler/read-ahead | activo, reaparición o writer no excluido | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No detener en esta fase; si futuro stop, restaurar PRE state | `P0`, `C1-CODE:UNIT_SPECS` |
| `kalm` | `OBSERVED_WRITER`; IRQ42 observado | Sin escritura IRQ/control durante la ventana | Unit/PID/config y readback IRQ/control | activo, polling/escritura o cobertura incompleta | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No detener aquí; restore de unidad requerida si se autorizara | `P0`, `C1-DOC` |
| `kalm-gpu` | `POSSIBLE_WRITER`; capability cap/DPM | Sin escritura GPU/PM durante la ventana | Unit/PID/capability y readback de controles | capability no resuelta, write o unidad unsafe | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No modificar GPU/PM; restore amplio `NOT_DEFINED` | `P0`, `C1-CODE:UNIT_SPECS` |
| `irqbalance` | `POSSIBLE_WRITER`; activo | Sin rebalanceo no atribuido durante la ventana | Unit/PID/config y readback IRQ | activo, migración no explicada o autor desconocido | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No cambiar IRQ/affinity; restore no aplica sin autorización | `P0` |
| Runtime PM | `PARTIALLY_CHARACTERIZED`; `auto/active/autosuspend=5000` | Readback estable; sin wake/control no autorizado | `power/control`, `runtime_status`, autosuspend, wake events y transiciones | missing, drift, wake/client no explicado | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No cambiar PM; si se autorizara, requiere inversa/readback | `P0`, `C1-OBS` |
| Governor | `CONFLICT`; `schedutil`/`performance` observado | Políticas legibles y estables; sin writer externo | Snapshot de todas las políticas y accounting de writers | política ausente, drift, oscilación o writer no resuelto | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No tuning; restore no definido para governor | `P0`, `OBS` |
| IRQ | `CONFLICT`; IRQ42 observado | Sin cambio no atribuido durante la ventana | Readback IRQ/affinity y evidencia de autor para cada cambio | cambio, fuente `UNKNOWN` o migración no explicada | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No cambiar IRQ; restore amplio no definido | `P0` |
| Scheduler | `OBSERVED_WRITER`; autopilot observado | Sin writer externo ni cambio no atribuido | Scheduler/priority/renice readback y accounting | drift, `renice` no atribuido o writer activo | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No cambiar scheduler; restore amplio no definido | `P0` |
| Read-ahead | `CONFLICT`; 256 frente a 128 documentados | Readback estable; sin writer no atribuido | Valor PRE/guard/POST y autor de cada cambio | drift, conflicto o autor `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No cambiar read-ahead; restore amplio no definido | `P0` |
| `/dev/sda` | `OBSERVED_STORAGE`; `/dev/sda2` en Btrfs | Sin actividad/atribución no aprobada; identidad reconciliada | `diskstats`, PSI, proceso/dispositivo y Btrfs tuple de la misma ventana | actividad no atribuida, source ausente o threshold `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No tocar `/dev/sda`; no hay restore de datos/FS autorizado | `P0`, `OBS`, `DOC-REC` |
| Btrfs | `CONFLICT` | `matched_identity_same_window` | Tuple completa de identidad en una ventana identificable | campos distintos, ausentes o de ventanas distintas | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | No ejecutar probe ni repair; `BTRFS_CAUSE=UNKNOWN` | `DOC-REC`, `P0` |

### 2.5 Estados `FULL` y `PARTIAL`

```text
FULL:
  todos los recursos anteriores PASS
  y no existe SOURCE=UNKNOWN
  y no existe cliente/writer no aprobado
  y el guard es PASS
  y el restore del scope declarado está definido

PARTIAL:
  identity-only, FD-only, una unidad quieta, un snapshot parcial,
  root namespace invisible, writer no resuelto, Btrfs conflict,
  o cualquier UNKNOWN
```

`PARTIAL` es el estado actual y no se promueve por diseño.

## 3. Gates sistémicos

Los gates sistémicos son read-only. `UNKNOWN` no se convierte en PASS.

| CHECK | SOURCE | REQUIRED_STATE | FAIL_CONDITION | ABORT_CONDITION | EVIDENCE | RESTORE_IMPACT |
|---|---|---|---|---|---|---|
| `PM` | `P0`, `C1-OBS`, `C1-CODE` | `power/control`, `runtime_status`, autosuspend y wake events legibles; sin transición no atribuida; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` para estabilidad | missing, drift, wake/client no explicado o writer no resuelto | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de cualquier mutación | Readback PRE/guard/POST con timestamps, fuente y hash de provenance | `NO_CHANGE_PLANNED`; si se muta PM, requiere inversa/readback antes de GO |
| `GOVERNOR` | `P0`, `OBS` | Todas las políticas legibles y estables; sin writer externo; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` | política ausente, cambio, oscilación o autor `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Snapshot de cada política, PRE/guard/POST y accounting de writers | `NO_CHANGE_PLANNED`; no tuning; cualquier cambio futuro bloquea GO |
| `IRQ` | `P0`, `OBS` | Readback IRQ/affinity estable y sin cambio no atribuido; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` | IRQ/affinity cambia, source missing o migración no explicada | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | PRE/guard/POST IRQ, afinidad, timestamp y autor | `NO_CHANGE_PLANNED`; no cambiar IRQ |
| `SCHEDULER` | `P0` | Scheduler/priority/renice sin writer externo; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` | cambio no atribuido, `renice` externo o writer no resuelto | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Readback de scheduler/priority/PID y accounting | `NO_CHANGE_PLANNED`; no cambiar scheduler |
| `READ_AHEAD` | `P0` | Valor PRE/guard/POST igual y autor conocido; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` para tolerancia | valor cambia, conflicto o autor `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Readback de read-ahead y evidencia de escritura | `NO_CHANGE_PLANNED`; no tocar read-ahead |
| `SDA_ACTIVITY` | `P0`, `OBS` | `diskstats` y PSI disponibles; actividad atribuible; `VALUE=UNKNOWN`, `THRESHOLD_SOURCE=NOT_AVAILABLE` | actividad no atribuida, source missing o criterio no validado | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` durante guard | `diskstats` PRE/guard/POST, PSI, `/dev/sda` source y proceso responsable | `NO_CHANGE_PLANNED`; no tocar `/dev/sda` |

### 3.1 Determinación futura de umbrales

Para cada `VALUE=UNKNOWN`:

```text
THRESHOLD=UNKNOWN
THRESHOLD_SOURCE=NOT_AVAILABLE
FUTURE_MEASUREMENT=read-only repeated snapshots in an explicitly authorized window
PASS_RULE=to be defined only after source, field, sampling rule and attribution rule are documented
NO_INVENTION=true
```

La medición futura deberá fijar antes del uso: métrica, unidades, path, frecuencia,
ventana, missing-data rule, attribution rule y criterio de abort. Hasta entonces el
gate es `DEFINED_PENDING_EXECUTION` y `GO_C1=NOT_AVAILABLE`.

## 4. Guard window

### 4.1 Parámetros documentados

```text
T_GUARD=120s
T_PRE=30s
T_POST=30s
SAMPLE_INTERVAL=5s
C1_MAX_SECONDS=180
D_STATE_REQUIRED=0
PROCS_BLOCKED_REQUIRED=0
IO_PSI_AVG10_MAX=10.0
SAMPLE_COUNT=RECORDED_EVIDENCE
```

No se inventa un conteo exacto: se registra el conteo real, y el resultado es PASS sólo
si cada sample tiene timestamp monotónico, índice, schema y log durable. `SAMPLE_COUNT`
no faltante, duplicado ni invalido.

### 4.2 Métricas obligatorias

- D-state y `procs_blocked`;
- PSI I/O `some/full avg10`;
- unidades y reapariciones;
- identidad/accesibilidad RX550 y controles GPU;
- inventario de clientes/ownership;
- PM, governor, IRQ, scheduler, read-ahead;
- `diskstats`/`/dev/sda` attribution;
- Btrfs identity tuple de la misma ventana.

La implementación C1 actual cubre solamente un subconjunto; las filas no implementadas
son `DEFINED_PENDING_EXECUTION`, no PASS.

### 4.3 Estabilidad y abort

```text
STABLE =
  all mandatory samples PASS
  AND no missing/invalid sample
  AND no UNKNOWN mandatory evidence
  AND no unaccounted client/writer
  AND no unaccounted PRE→GUARD→POST transition
  AND no unexplained PM/GPU/agent/storage drift

ABORT_GUARD =
  any FAIL, UNKNOWN, missing sample, signal, identity drift,
  reappearing unit, readback mismatch, collision, Btrfs conflict,
  or provenance loss
```

### 4.4 D-state, PSI, I/O y latencia

| Medida | Significado | Efecto de gate | Afirmación causal |
|---|---|---|---|
| D-state | Procesos en estado D observado | `ABORT_GUARD` si no es cero en guard | No demuestra latencia ni causa |
| `procs_blocked` | Campo de `/proc/stat` | `ABORT_GUARD` si no es cero | No demuestra I/O ni causa |
| PSI I/O | Presión agregada del kernel | `ABORT_GUARD` si `some/full avg10>10.0` o no comparable | No es porcentaje de disco, latencia ni causalidad |
| `SDA_ACTIVITY` | Actividad/atribución de `/dev/sda` | `NO_GO_PRE`/`ABORT_GUARD` según fase | No demuestra que el HDD cause frametime |

Una métrica dentro del gate y sin transición es evidencia de estabilidad, no prueba de
causalidad ni de que el ruido esté en el disco, PM, IRQ o scheduler.

## 5. Btrfs

```text
BTRFS=CONFLICT
BTRFS_CAUSE=UNKNOWN
REQUIRED=matched_identity_same_window
```

### 5.1 Significado exacto

`matched_identity_same_window` significa que un único registro futuro de evidencia contiene
la misma tupla, sin mezclar snapshots de diferentes momentos:

```text
IDENTITY_TUPLE =
  source_path
  filesystem_type
  device_or_mount_identity
  filesystem_UUID_or_serial_IF_AVAILABLE
  observation_window_id
  observation_start
  observation_end
  source_command_and_hash
```

Valores conocidos que no deben alterarse:

```text
source_path=/dev/sda2
filesystem_type=Btrfs
filesystem_UUID_or_serial=VALUE=UNKNOWN
observation_window_id=VALUE=UNKNOWN hasta una fase autorizada
WINDOW_ID=must be an immutable run/evidence-bundle identifier, never a free-text label
WINDOW_DURATION=VALUE=UNKNOWN
WINDOW_COVERAGE=PRE_to_T_GUARD_to_T_POST; exact wall-clock duration must be recorded
```

`filesystem_UUID_or_serial` sólo se exige si está disponible en la evidencia; no se
inventará un UUID. La coincidencia debe exigir que las fuentes A y B usen la misma
`observation_window_id` y registrar la misma topología de fuente/mount.

### 5.2 Evidencia y resultado

- Evidencia necesaria: fuente, comando/lectura, timestamp, path, tipo, identidad de
  dispositivo/mount, UUID/serial si existe, hash y `WINDOW_ID`.
- Resultado que cerraría el conflicto: todas las fuentes de la misma ventana coinciden
  en la tupla; entonces sólo una fase posterior podría cambiar
  `BTRFS=CONFLICT` a `BTRFS=MATCHED`.
- Resultado que mantiene `CONFLICT`: cualquier campo difiere, falta, es `UNKNOWN`,
  o las fuentes pertenecen a ventanas distintas.
- `BTRFS_CAUSE` permanece `UNKNOWN` aunque se resuelva la identidad; no se atribuye
  causalidad a Btrfs.
- No se ejecuta comprobación, probe, scrub ni repair en esta especificación.

## 6. Restore

Estados obligatorios y separados:

```text
RESTORE_PLANNED=DEFINED_FOR_DECLARED_SCOPE
RESTORE_EXECUTED=NO
RESTORE_VALIDATED=NO
```

`RESTORE_EXECUTED=YES` sólo puede aparecer después de una acción real autorizada.
`RESTORE_VALIDATED=YES` exige readback posterior; ninguna definición previa lo prueba.

### 6.1 Matriz de restore

| RESOURCE | BEFORE | MODIFICATION | AFTER | RESTORE_ACTION | RESTORE_EXECUTED | RESTORE_VALIDATED | FAIL_CONDITION |
|---|---|---|---|---|---|---|---|
| Servicios C1 allowlist | PRE `ActiveState/SubState/UnitFileState/MainPID` | Sólo stop autorizado de PRE-active | Estado PRE o discrepancia explicada | Start sólo de unidad tocada y PRE-active; no iniciar PRE-inactive | `NO` | `NO` | Start/readback falla, PRE/POST difiere o restore parcial |
| Runtime namespace | Paths propios y preexistentes separados | Creación/eliminación sólo de artefactos v2 propios | Sin entradas preexistentes alteradas | Cleanup sólo de paths rastreados por la corrida | `NO` | `NO` | Path no rastreado, layout inválido o cleanup parcial |
| Runtime root | Root tmpfs y permisos esperados | No crear en esta fase | Root no materializado o intacto | Ninguna; no borrar nada | `NO` | `NO` | Root inesperado, permisos inseguros o materialización no autorizada |
| `CURRENT` | Ausente o puntero regular preexistente | No crear/modificar en esta fase | Igual al BEFORE | Ninguna | `NO` | `NO` | Puntero cambia, no es regular o ownership/permisos no coinciden |
| `state/events/JSONL` | No existen en PRE o están allowlisted | No crear en esta fase | Evidencia histórica intacta | Ninguna | `NO` | `NO` | Archivo nuevo no permitido, schema inválido o colisión |
| Runtime PM | `power/control`, status, autosuspend | `NO_CHANGE_PLANNED` | Readback igual a BEFORE | Ninguna | `NO` | `NO` | Drift, wake o writer no explicado |
| Governor | Políticas PRE | `NO_CHANGE_PLANNED` | Políticas iguales | Ninguna | `NO` | `NO` | Drift o writer no explicado |
| GPU cap/DPM/PM | Valores PRE | `NO_CHANGE_PLANNED` | Valores iguales | Ninguna | `NO` | `NO` | Drift, unavailable o control no attributed |
| IRQ | IRQ/affinity PRE | `NO_CHANGE_PLANNED` | Readback igual | Ninguna | `NO` | `NO` |Cambio o autor `UNKNOWN` |
| Scheduler | Scheduler/priority PRE | `NO_CHANGE_PLANNED` | Readback igual | Ninguna | `NO` | `NO` | `renice` o cambio no atribuido |
| Read-ahead | Valor PRE | `NO_CHANGE_PLANNED` | Readback igual | Ninguna | `NO` | `NO` | Conflicto o cambio no atribuido |
| Xwayland/aplicaciones | PID/FD/session PRE | `NO_KILL_STOP_PLANNED` | Sin cambio o sesión restaurada por mecanismo future | No actuar en esta fase | `NO` | `NO` | Proceso/FD cambia sin mecanismo de restore |
| Mesa/RADV | ICD/maps/driver PRE | `NO_CHANGE_PLANNED` | Target y provenance iguales | Ninguna | `NO` | `NO` | Target/provenance mismatch |
| `/dev/sda`/Btrfs | Source/identity/activity PRE | `NO_TOUCH_PLANNED` | Source/identity sin cambio y evidencia intacta | Ninguna | `NO` | `NO` | Drift, conflict, probe no autorizada o repair |

Cualquier modificación no listada como `NO_CHANGE_PLANNED` requiere una fila nueva,
mecanismo inverso y readback antes de `GO_C1`.

### 6.2 Fallo de restore

```text
RESTORE_FAILURE
→ ABORT_RESTORE
→ detener la progresión de C1
→ determinar SAFE_STATE o SAFE_STATE=UNKNOWN
→ registrar BEFORE/AFTER/readback/error
→ no continuar automáticamente
→ no retry automático
```

Si el estado seguro es `UNKNOWN`, el resultado sigue siendo `ABORT_RESTORE` y
`RESTORE_VALIDATED=NO`. No se afirma que el sistema quedó restaurado.

## 7. Runtime, TTY, RUN-C1 y sudo

Estados separados:

```text
RUNTIME_DESIGNED=YES
RUNTIME_MATERIALIZED=NO
RUNTIME_VALIDATED=NO
C1_EXECUTED=NO
C1_RUNTIME_VALIDATED=NO
```

| ITEM | REQUIRED | CURRENT | PROOF | FAIL | ABORT | SOURCE |
|---|---|---|---|---|---|---|
| Namespace | Namespace v2 diseñado, aislado y con layout conocido | `DESIGNED=YES; MATERIALIZED=NO` | Path/version/layout/provenance/allowlist | Namespace inesperado, version inválida o layout desconocido | `ABORT_RUNTIME` | `C1-DOC §Runtime files`, `C1-SIDE` |
| Runtime root | `/run/user/1000/c1-isolation-automator-v2` con permisos/tmpfs requeridos | `ABSENT/NOT_MATERIALIZED` | Read-only root inspection de path, filesystem, uid y mode | Missing durante una fase que lo requiere, permisos inseguros o path inesperado | `ABORT_RUNTIME` | `C1-CODE:validate_runtime_dir`, `C1-DOC` |
| `CURRENT` | Ausente antes de nueva corrida o puntero regular allowlisted | `NOT_MATERIALIZED` | Tipo, uid, mode, target y hash de provenance | Symlink, puntero irregular, colisión o estado no trazable | `ABORT_RUNTIME` | `C1-CODE`, `C1-SIDE` |
| `state` | Ausente antes de init; luego schema2 inicial/final durable | `NO_RUNTIME_STATE` | JSON schema, hashes, phase, terminal y provenance | JSON incompleto, phase inválida, schema incorrecta o write failure | `ABORT_RUNTIME` | `C1-CODE:RuntimeArtifacts`, `C1-DOC §State machine` |
| `JSONL` | Ausente antes de C1; luego path exacto, parseable y durable | `ABSENT` | Path, hash, records, parser result y sample completeness | Colisión, path incorrecto, JSON inválido o sample faltante | `ABORT_RUNTIME` | `C1-CODE:observer_check`, `C1-DOC §Runtime files` |
| TTY | TTY real interactiva | `NOT_VERIFIED` | `isatty`/stream evidence en futura ejecución | No TTY, stream no interactivo o evidencia ausente | `NO_GO_PRE` | `C1-DOC §--run` |
| `RUN-C1` | Confirmación literal `RUN-C1` después de TTY | `ABSENT` | Prompt/response evidence, sin persistencia de credenciales | Confirmación ausente, incorrecta o no verificable | `NO_GO_PRE` | `C1-DOC §--run` |
| Sudo interactivo | `sudo -v` normal, TTY y sin bypass | `NOT_VERIFIED` | Resultado de autenticación/readback, nunca contraseña | Auth fail, `-n`, bypass o evidencia ausente | `NO_GO_PRE`; ninguna unidad se detiene | `C1-DOC §Sudo y privilegios` |

Si el runtime no existe, no se crea silenciosamente. Antes de una fase autorizada puede
ser el estado esperado (`NO_GO_PRE` si no hay autorización); después de que una fase
requiere materializarlo, su ausencia es `ABORT_RUNTIME`.

## 8. Prechecks

Cada fila es independiente y contiene las siete columnas requeridas.

| CHECK | SOURCE | REQUIRED_STATE | FAIL_CONDITION | ABORT_CONDITION | EVIDENCE | RESTORE_IMPACT |
|---|---|---|---|---|---|---|
| `SCOPE` | `DESIGN`, `P0` | Revisión documental completa; ejecución no autorizada | Se solicita ejecutar o mutar sin autorización separada | `NO_GO_PRE` | Estado de autorización y versión del diseño | `NONE` |
| `HOST_KERNEL` | `C1-CODE`, `P0` | Host/kernel exactos y legibles | Mismatch o lectura ausente | `NO_GO_PRE` | Host, kernel, timestamp | `NONE` |
| `GPU_IDENTITY` | `C1-CODE`, `C1-DOC` | BDF/vendor/device/driver/card1/renderD129/hwmon2 exactos | Cualquier mismatch o mapping ausente | `NO_GO_PRE` | Identity snapshot y mappings | `NONE` |
| `DISPLAY_TOPOLOGY` | `P0` | Intel `card0` conectado; RX550 `card1` sin presentación | Topología cambia o aparece display RX550 | `NO_GO_PRE` | DRM/card/display readback | `NONE` |
| `PROVENANCE` | `C1-CODE`, `C1-SIDE` | Hashes, build ID, git HEAD y fuentes trazables | Hash mismatch, source missing o provenance no reproducible | `NO_GO_PRE` | Manifest/hash ledger | `NONE` |
| `RUNTIME_NAMESPACE` | `C1-CODE`, `C1-SIDE` | Design correcto; materialized ausente o completo/válido; legacy allowlisted | Runtime incompleto, desconocido, JSONL inesperado o colisión | `ABORT_RUNTIME` | Layout/path/permissions/schema/hashes | `NONE`; no crear runtime |
| `C1_COLLISION` | `C1-CODE` | No C1/observer activo ni JSONL previo | Cualquier colisión | `ABORT_PRE` | Process scan, path y timestamp | `NONE` |
| `D_STATE` | `C1-DOC`, `C1-CODE` | `D_STATE_COUNT=0` en PRE y cada muestra | `>0`, missing o lectura interrompida | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después | Snapshot PRE/guard/POST | `NONE` antes; restore de unidades si ya hubo aislamiento |
| `PROCS_BLOCKED` | `C1-CODE` | `procs_blocked=0` en PRE y cada muestra | `>0` o missing | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | `/proc/stat` snapshot y sample log | `NONE`/restore de `touched[]` si aplica |
| `PSI_IO` | `C1-CODE`, `C1-SIDE` | `some avg10<=10.0` y `full avg10<=10.0` | `>10.0`, NaN, missing o no comparable | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | PSI PRE/guard/POST y parser output | `NONE`/restore de `touched[]` si aplica |
| `SDA_ACTIVITY` | `P0`, `OBS` | `diskstats`/PSI available; attribution rule definida; threshold `UNKNOWN` hasta fase autorizada | Actividad no atribuida, source missing o threshold no establecido | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | `diskstats`, PSI, source `/dev/sda` y actor | `NONE`; no tocar `/dev/sda` |
| `BTRFS_IDENTITY` | `DOC-REC`, `P0` | `matched_identity_same_window` | `BTRFS=CONFLICT`, mismatch o missing | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Tuple, window ID, timestamps y source hashes | `NONE`; no probe/repair |
| `GPU_CLIENTS` | `P0`, `C1-CODE` | Inventario root/user completo; sólo clientes permitidos | Xwayland, ChatGPT, otro cliente o namespace `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | PID, FD, namespace, client ID y timestamp | `PROCESS_RESTORE` no definido; bloquea `GO` |
| `OWNERSHIP` | `P0`, `C1-CODE`, `DESIGN` | Predicado FULL completo | `PARTIAL`, `UNKNOWN`, sólo FD cerrado o writer no resuelto | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Matriz de ownership y evidence IDs | `NONE` sin mutación; restore requerido si se propone |
| `SERVICE_AGENTS` | `P0`, `C1-CODE` | Todos los writers relevantes quietos/excluidos/autorizados; sin `UNKNOWN` | Reaparición, unsafe state o writer no inventariado | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Unit/PID/config/readback por agente | No detener aquí; futuro stop exige restore |
| `PM` | `P0`, `OBS` | Readback estable; `VALUE=UNKNOWN` para threshold | Drift, wake/client no explicado o writer | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | PM PRE/guard/POST | `NO_CHANGE_PLANNED` |
| `GOVERNOR` | `P0`, `OBS` | Políticas estables; `VALUE=UNKNOWN` para tolerancia | Drift, oscilación o writer | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Governor snapshots | `NO_CHANGE_PLANNED` |
| `IRQ` | `P0`, `OBS` | Readback estable; `VALUE=UNKNOWN` para tolerancia | Drift o autor `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | IRQ/affinity snapshots | `NO_CHANGE_PLANNED` |
| `SCHEDULER` | `P0` | Scheduler/priority/renice sin writer; `VALUE=UNKNOWN` | Cambio o `renice` no atribuido | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Scheduler/priority snapshots | `NO_CHANGE_PLANNED` |
| `READ_AHEAD` | `P0` | Readback igual; `VALUE=UNKNOWN` para tolerancia | Valor cambia o autor `UNKNOWN` | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Read-ahead snapshots | `NO_CHANGE_PLANNED` |
| `GPU_CONTROLS` | `C1-CODE` | cap/DPM/PM/status legibles y sin drift | Missing, mismatch o readback unsafe | `ABORT_GUARD` | GPU control snapshot | `NO_CHANGE_PLANNED` |
| `TTY_CONFIRMATION` | `C1-DOC` | TTY real + literal `RUN-C1` | TTY o confirmación ausente | `NO_GO_PRE` | TTY/prompt/response metadata | `NONE` |
| `SUDO` | `C1-DOC` | `sudo -v` interactivo normal | Auth fail, bypass, `-n` o evidencia ausente | `NO_GO_PRE` | Resultado de auth/readback | `NONE`; no stop |
| `SNAPSHOT_READBACK` | `C1-DOC`, `C1-CODE` | PRE/plan/evidence durable y readback completo | Campo obligatorio faltante o mismatch | `NO_GO_PRE` antes de aislamiento; `ABORT_GUARD` después de aislamiento | Snapshot index, hashes y logs | `NONE` si no hubo mutación |
| `RESTORE_PLAN` | `DESIGN`, `C1-DOC` | Cada mutación autorizada tiene BEFORE/AFTER/inversa/readback | Falta inversa, responsable o readback | `NO_GO_PRE` | Restore matrix y decision IDs | `RESTORE_EXECUTED=NO` hasta autorización |
| `C1_STATE` | `C1-SIDE`, `DESIGN` | No C1/observer active; runtime v2 no materialized en esta fase | Runtime incomplete/collision o estado no trazable | `ABORT_PRE` | Sidecar/state/readback | `NONE`; no crear runtime |

## 9. Fallback y abort

Cada fila declara una única clasificación y un único siguiente estado. No se permite
continuar silenciosamente.

| FAILURE | CLASSIFICATION | ACTION | ABORT? | RESTORE? | EVIDENCE | NEXT_STATE |
|---|---|---|---|---|---|---|
| Ownership `PARTIAL/UNKNOWN` | `NO_GO_PRE` | No aislar; preservar snapshot | `NO` | `NO` | Ownership matrix y evidence IDs | `NO_GO` |
| D-state falla antes de aislamiento | `NO_GO_PRE` | No iniciar aislamiento | `NO` | `NO` | PRE dstate | `NO_GO` |
| D-state falla durante guard | `ABORT_GUARD` | No lanzar C1; restore de `touched[]` | `YES` | `REQUIRED` | JSONL/state/readback | `RESTORE_PENDING` |
| PSI falla antes de aislamiento | `NO_GO_PRE` | No iniciar aislamiento | `NO` | `NO` | PSI snapshot | `NO_GO` |
| PSI falla durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | PSI samples y log | `RESTORE_PENDING` |
| I/O guard falla antes de aislamiento | `NO_GO_PRE` | No tocar `/dev/sda`; no lanzar C1 | `NO` | `NO` | PSI/diskstats/actor/source | `NO_GO` |
| SDA activity no atribuida antes de aislamiento | `NO_GO_PRE` | No tocar `/dev/sda`; no lanzar C1 | `NO` | `NO` | diskstats/PSI/actor/source | `NO_GO` |
| I/O guard falla durante guard | `ABORT_GUARD` | No lanzar C1; restore de `touched[]` | `YES` | `REQUIRED` | samples, readback y error | `RESTORE_PENDING` |
| SDA activity no atribuida durante guard | `ABORT_GUARD` | No lanzar C1; no tocar `/dev/sda`; restore | `YES` | `REQUIRED` | diskstats/PSI/readback | `RESTORE_PENDING` |
| Runtime ausente antes de init autorizada | `NO_GO_RUNTIME` | No crear silenciosamente | `NO` | `NO` | Path/layout/authorization | `NO_GO_RUNTIME` |
| Runtime ausente cuando ya era requerido | `ABORT_RUNTIME` | No continuar; preservar estado | `YES` | `REQUIRED` sólo para artefactos previos | Runtime readback/error | `ABORT_RUNTIME` |
| TTY ausente | `NO_GO_PRE` | No pedir ni forzar sudo | `NO` | `NO` | TTY evidence | `NO_GO` |
| `RUN-C1` ausente | `NO_GO_PRE` | No continuar | `NO` | `NO` | Prompt metadata | `NO_GO` |
| Sudo falla | `NO_GO_AUTH` | No detener unidades | `NO` | `NO` | Auth result/readback | `NO_GO_AUTH` |
| PM inconsistente antes de aislamiento | `NO_GO_PRE` | No cambiar PM | `NO` | `NO` | PM readback | `NO_GO` |
| PM inconsistente durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | PM readback/samples | `RESTORE_PENDING` |
| Governor inconsistente antes de aislamiento | `NO_GO_PRE` | No tuning | `NO` | `NO` | Governor snapshots | `NO_GO` |
| Governor inconsistente durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | Governor snapshots | `RESTORE_PENDING` |
| IRQ inconsistente antes de aislamiento | `NO_GO_PRE` | No cambiar IRQ | `NO` | `NO` | IRQ/affinity readback | `NO_GO` |
| IRQ inconsistente durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | IRQ/affinity readback | `RESTORE_PENDING` |
| Scheduler inconsistente antes de aislamiento | `NO_GO_PRE` | No cambiar scheduler | `NO` | `NO` | Scheduler/priority readback | `NO_GO` |
| Scheduler inconsistente durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | Scheduler/priority readback | `RESTORE_PENDING` |
| Read-ahead inconsistente antes de aislamiento | `NO_GO_PRE` | No tocar read-ahead | `NO` | `NO` | Read-ahead readback | `NO_GO` |
| Read-ahead inconsistente durante guard | `ABORT_GUARD` | No lanzar C1; restore | `YES` | `REQUIRED` | Read-ahead readback | `RESTORE_PENDING` |
| Btrfs conflict antes de aislamiento | `NO_GO_PRE` | No probe/repair | `NO` | `NO` | Btrfs tuple/window | `NO_GO` |
| Btrfs conflict durante guard | `ABORT_GUARD` | No probe/repair; no lanzar C1; restore | `YES` | `REQUIRED` | Btrfs tuple/window/readback | `RESTORE_PENDING` |
| Restore falla o readback no coincide | `ABORT_RESTORE` | Detener progresión; no retry; determinar safe state | `YES` | `ATTEMPTED` | Result por recurso + error + safe-state readback | `RESTORE_UNRESOLVED` |
| `POST_CONFLICT` | `ABORT_C1` | No corregir automáticamente; preservar evidencia | `YES` | `REQUIRED`/`ATTEMPTED` | POST discrepancies | `RESTORE_UNRESOLVED` |

`NO_GO` y `ABORT` son observables. `UNKNOWN` se clasifica como falla cerrada, no como
`PASS` ni como “best effort”.

## 10. Flujo documental

El flujo embebido de esta especificación usa exactamente los nodos requeridos:

```text
DOCUMENTARY DESIGN
NO EXECUTION EVIDENCE

BASELINE
  -> PRECHECK
  -> CONTAMINATION?
       -> YES/UNKNOWN: NO-GO / ISOLATION REQUIRED
       -> NO: OWNERSHIP
  -> VERIFY OWNERSHIP
  -> GUARD WINDOW
  -> VERIFY STABILITY
       -> NO/UNKNOWN: NO-GO / ABORT
       -> YES: C1 AUTHORIZATION
  -> C1
  -> RESTORE
  -> VERIFY RESTORE
```

`OWNERSHIP_REQUEST`, `ISOLATION` y `VERIFY` no sustituyen los nodos normativos
`OWNERSHIP` y `VERIFY OWNERSHIP`. El archivo separado
`00-INDICE/DIAGRAMAS/15-C1-ISOLATION-DESIGN.md` permanece una vista derivada; no se
modifica en esta operación de alcance único.

## 11. Comparación con C1 v1.1.1

| Requirement | C1 actual | Especificación requerida | Estado |
|---|---|---|---|
| Identidad/hash/build | Implementados en precheck | Gate completo | `DEFINED_PENDING_EXECUTION` |
| D-state/procs/PSI | Implementados | Gate por muestra | `DEFINED_PENDING_EXECUTION` |
| Ownership FULL | `PARTIAL` fijo | Predicato y prueba FULL | `DEFINED_PENDING_EXECUTION` |
| Client inventory | Sólo colisión C1/observer | Root/user completo | `DEFINED_PENDING_EXECUTION` |
| Agents | Allowlist limitado | Writer coverage completo | `DEFINED_PENDING_EXECUTION` |
| PM/governor/IRQ/scheduler/read-ahead | Lecturas parciales | Gates read-only y readback | `DEFINED_PENDING_EXECUTION` |
| SDA activity | Snapshot parcial | Threshold/atribución futura | `DEFINED_PENDING_EXECUTION` |
| Btrfs | Sin gate | `matched_identity_same_window` | `DEFINED_PENDING_EXECUTION` |
| TTY/RUN-C1/sudo | Contrato existe, no validado | Gate previo obligatorio | `DEFINED_PENDING_EXECUTION` |
| Namespace/schema2 | Sidecar/tests estáticos; no runtime | Diseño/materialización/validación separados | `DEFINED_PENDING_EXECUTION` |
| Restore | Units/runtime propios | Matriz completa y failure state | `CLOSED_AS_SPECIFICATION` |
| Precheck schema | Tabla anterior agrupaba campos | Siete columnas independientes | `CLOSED_AS_SPECIFICATION` |
| Fallback | Reglas dispersas | Matriz única `FAILURE→NEXT_STATE` | `CLOSED_AS_SPECIFICATION` |

## 12. Provenance de decisiones críticas

| DECISION_ID | SOURCE | EVIDENCE_ID | STATUS |
|---|---|---|---|
| `DEC-OWNERSHIP-FULL` | `P0`, `C1-CODE`, `DESIGN` | `P0-OWNERSHIP-CLIENTS`, `C1-PRECHECK-OWNERSHIP` | `DEFINED_PENDING_EXECUTION` |
| `DEC-CLIENT-INVENTORY` | `P0`, `C1-CODE` | `P0-FD-ROOT-UNKNOWN`, `C1-COLLISION-SCAN` | `DEFINED_PENDING_EXECUTION` |
| `DEC-AGENT-SCOPE` | `P0`, `C1-CODE` | `P0-AGENT-WRITERS`, `C1-UNIT-SPECS` | `DEFINED_PENDING_EXECUTION` |
| `DEC-SYSTEMIC-GATES` | `P0`, `OBS`, `C1-CODE` | `P0-PM-GOV-IRQ-SCHED-IO`, `OBS-SNAPSHOTS` | `DEFINED_PENDING_EXECUTION` |
| `DEC-SDA-THRESHOLD` | `P0`, `OBS` | `OBS-DISKSTATS`, `P0-SDA` | `DEFINED_PENDING_EXECUTION` |
| `DEC-BTRFS-WINDOW` | `DOC-REC`, `P0` | `DOC-REC-BTRFS-CONFLICT`, `P0-SDA2` | `DEFINED_PENDING_EXECUTION` |
| `DEC-RESTORE-CONTRACT` | `C1-DOC`, `DESIGN` | `C1-DOC-RESTORE`, `RESTORE-MATRIX` | `CLOSED_AS_SPECIFICATION` |
| `DEC-RUNTIME-STATES` | `C1-DOC`, `C1-CODE`, `C1-SIDE` | `C1-DOC-RUNTIME`, `C1-SIDE-SCHEMA2` | `DEFINED_PENDING_EXECUTION` |
| `DEC-PRECHECK-SCHEMA` | `DESIGN` | `PRECHECK-7-COLUMNS` | `CLOSED_AS_SPECIFICATION` |
| `DEC-FALLBACK-STATES` | `DESIGN`, `C1-DOC` | `FALLBACK-MATRIX`, `C1-DOC-STATE-MACHINE` | `CLOSED_AS_SPECIFICATION` |
| `DEC-GUARD-PARAMETERS` | `C1-DOC`, `C1-CODE`, `C1-SIDE` | `C1-DOC-GUARD`, `C1-CODE-guard_sample` | `CLOSED_AS_SPECIFICATION` |
| `DEC-DIAGRAM-NODES` | `DESIGN` | `FLOW-OWNERSHIP-VERIFY` | `CLOSED_AS_SPECIFICATION` |

Regla de provenance: cada decisión crítica debe tener un `DECISION_ID`; cada fuente
debe apuntar a evidencia, documentación, código o hipótesis. Si no existe fuente:

```text
DECISION_ID=<id>
SOURCE=UNKNOWN
EVIDENCE_ID=NONE
STATUS=DEFINED_PENDING_EXECUTION
```

Nunca `RESOLVED_BY_ASSUMPTION`.

## 13. Ledger de cierre de gaps

| GAP_ID | Tratamiento documental | STATUS |
|---|---|---|
| `G-01` | Predicado FULL y evidencia negativa positiva definidos | `DEFINED_PENDING_EXECUTION` |
| `G-02` | Inventario root/user/clients y fail/abort definidos | `DEFINED_PENDING_EXECUTION` |
| `G-03` | Scope de agentes y writers definido | `DEFINED_PENDING_EXECUTION` |
| `G-04` | Gate PM y método de determinación futura definidos | `DEFINED_PENDING_EXECUTION` |
| `G-05` | Gate governor y threshold unknown explícitos | `DEFINED_PENDING_EXECUTION` |
| `G-06` | Gates IRQ/scheduler/read-ahead definidos | `DEFINED_PENDING_EXECUTION` |
| `G-07` | Gate SDA activity y threshold unknown explícitos | `DEFINED_PENDING_EXECUTION` |
| `G-08` | `matched_identity_same_window` definido sin resolver conflict | `DEFINED_PENDING_EXECUTION` |
| `G-09` | Restore matrix y failure flow definidos | `CLOSED_AS_SPECIFICATION` |
| `R-01` | `RESTORE_PLANNED/EXECUTED/VALIDATED` separados | `CLOSED_AS_SPECIFICATION` |
| `G-10` | Runtime/TTY/RUN-C1/sudo separados con comportamiento de runtime ausente | `DEFINED_PENDING_EXECUTION` |
| `P-01` | Precheck table tiene siete columnas independientes | `CLOSED_AS_SPECIFICATION` |
| `F-01` | Fallback matrix cubre todos los casos solicitados | `CLOSED_AS_SPECIFICATION` |
| `D-01` | Flujo embebido usa OWNERSHIP y VERIFY OWNERSHIP | `CLOSED_AS_SPECIFICATION` |
| `V-01` | DECISION_ID/SOURCE/EVIDENCE_ID/STATUS agregados | `CLOSED_AS_SPECIFICATION` |

`STATUS=RESOLVED_BY_ASSUMPTION` no se usa. Un gap con evidencia faltante queda
`DEFINED_PENDING_EXECUTION`; no se presenta como PASS de ejecución.

## 14. Decisión final

```text
DESIGN_UPDATE=PASS
DESIGN_STATUS=PREPARED_FOR_REVIEW
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
C1=DEFERRED
C1_RUNTIME_VALIDATED=NO
C1_READY=NO
RUNTIME_DESIGNED=YES
RUNTIME_MATERIALIZED=NO
RUNTIME_VALIDATED=NO
RESTORE_PLANNED=DEFINED_FOR_DECLARED_SCOPE
RESTORE_EXECUTED=NO
RESTORE_VALIDATED=NO
BTRFS=CONFLICT
HDD_FAILURE=NOT_PROVEN
GO_C1=NOT_AVAILABLE
NEXT=AWAIT_SEPARATE_AUTHORIZATION_BEFORE_IMPLEMENTATION_OR_RUNTIME
```

La especificación queda cerrada como contrato documental. Los gaps que requieren
lectura, implementación o ejecución permanecen explícitamente pendientes y no se
resuelven por suposición.
