# C1 Recovery and GPU-Client Treatment Design v1.0

**Tipo:** diseño y análisis documental; no es ejecución
**Estado:** `RECOVERY_TREATMENT_DESIGN=PREPARED_FOR_REVIEW`
**Modo:** `DESIGN_ONLY`
**C1:** `DEFERRED`
**GO_C1:** `NOT_AVAILABLE`
**Fuente de estado:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json`
**Registro por holding:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-RECOVERY-TREATMENT-ANALYSIS-20260925T062806Z.json`

Este documento diseña qué debe verificarse o tratamiento debería documentarse en el
futuro. No ejecuta C1, no aisla clientes, no detiene procesos, no cambia servicios,
no modifica PM/governor/IRQ/scheduler/read-ahead, no escribe GPU/storage, no crea
runtime v2 y no hace commit. Ninguna alternativa de tratamiento queda seleccionada.

## 1. Invariantes

```text
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
RECOVERY=FAIL
C1=DEFERRED
GO_C1=NOT_AVAILABLE
C1_RUNTIME_VALIDATED=NO
RUNTIME_MATERIALIZED=NO
RUNTIME_VALIDATED=NO
RESTORE_EXECUTED=NO
RESTORE_VALIDATED=NO
```

La documentación de C1 ya define que `OWNERSHIP=FULL` requiere identidad fija,
inventario root/user completo, ausencia de clientes no aprobados, writer scope
completo, gates sistémicos, Btrfs de la misma ventana, guard estable y restore para
el scope declarado. Este documento no relajó ninguno de esos predicates.

## 2. Base de evidencia y límites

La captura privilegiada reciente observó `13` holdings GPU:

- `card1`: `8` holdings;
- `renderD129`: `5` holdings;
- `/dev/sda`: `0` holders en la captura;
- PIDs holders: `1`, `975`, `2457`, `2671`, `11399`.

Los holdings prueban acceso_open observado; no prueban por sí solos causalidad,
consumo de GPU, escritura, ni autorização para detener el proceso. La clasificación
de cada FD y la fuente exacta están en el JSON de análisis.

`PermissionError` previos: `362`. `FileNotFoundError` previo: `1`. El inventario
root posterior resolvió `224` PIDs previos; `15` ya no existían y quedaron `2`
carreras `FileNotFoundError` al leer FDs. No se reprodujeron `PermissionError`, pero
la cobertura no se convierte en `COMPLETE` mientras el escaneo tenga errores o
procesos no reconciliados.

## 3. Recovery independiente

Un mecanismo sólo es `RECOVERY=PASS` si existe, fue verificado en una fase posterior,
es independiente de la sesión gráfica que se pretende tratar, tiene una vía de
interacción probada y puede recuperar o dejar un estado seguro. La presencia de un
binario, nodo de dispositivo, archivo de configuración o entrada de boot no es
suficiente.

| RECOVERY_ID | MECHANISM | EXISTS | VERIFIED | INDEPENDENT_FROM_GRAPHICAL_SESSION | REQUIRES_REBOOT | REQUIRES_NETWORK | REQUIRES_USER_INTERACTION | CAN_RESTORE_GPU_SESSION | RISK | STATUS | SOURCE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `REC-TTY-01` | TTY/VT real y controlable | `PARTIAL`: hay nodos y `tty0` enabled | `NO`: `tty`=no, stdin=`/dev/null` | `UNKNOWN` | `NO` | `NO` | `YES` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `tty`, `/proc/consoles`, `/sys/class/tty/console/active`, `TTY_COMMAND` |
| `REC-SSH-01` | SSH | `NO`: binario presente, `sshd.service/socket=inactive`, sin listener `:22` | `NO` | `PLAUSIBLE` sólo si se verificara | `NO` | `YES` | `YES` | `UNKNOWN` | `UNKNOWN` | `NOT_AVAILABLE` | `systemctl show`, `ss -ltn`, `command -v sshd` |
| `REC-CONSOLE-01` | Consola de emergencia | `PARTIAL`: `/dev/console` existe | `NO`: no hay TTY interactiva | `PLAUSIBLE` | `UNKNOWN` | `NO` | `YES` | `UNKNOWN` | `HIGH` | `UNKNOWN` | `/dev/console`, `/proc/consoles`, `TTY_COMMAND` |
| `REC-GRUB-01` | Entrada rescue/GRUB | `PARTIAL`: entrada `...-rescue.conf` observada en captura previa | `NO`: no se puede seleccionar ni probar sin reiniciar | `PLAUSIBLE` | `YES` | `NO` | `YES` | `UNKNOWN` | `HIGH` | `UNKNOWN` | `C1-PREFLIGHT...json:tty_recovery.recovery_candidates` |
| `REC-SESSION-01` | Segundo usuario/sesión independiente | `NO`: dos sesiones, ambas UID 1000; no segundo usuario | `NO` | `NO` demostrada | `NO` | `NO` | `YES` | `UNKNOWN` | `HIGH` | `NOT_AVAILABLE` | `loginctl list-sessions/list-users` |
| `REC-OTHER-01` | Entorno headless/VM/host alterno | `NOT_AVAILABLE`: no hay evidencia de un entorno independiente configurado | `NO` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NOT_AVAILABLE` | `SOURCE=UNKNOWN` |

### Resultado recovery

```text
RECOVERY_CANDIDATES=6
RECOVERY_VERIFIED=0
RECOVERY=FAIL
RECOVERY_PATH_USABLE=UNKNOWN
TTY_AVAILABLE=NO
```

Para convertir `RECOVERY=FAIL` en `RECOVERY=PASS` se necesitaría, como mínimo, una
fuente de recovery real y una validación posterior que demostraría, sin ejecutar C1:

1. mecanismo disponible y accesible desde una sesión que no sea la sesión gráfica
   que se quiere tratar;
2. `VERIFIED=YES` con timestamp, source y comando de verificación;
3. `INDEPENDENT_FROM_GRAPHICAL_SESSION=YES` demostrado, no supuesto;
4. `CAN_RESTORE_GPU_SESSION=YES` o un `SAFE_STATE` documentado;
5. usuarios, permisos y ruta de interacción conocidos;
6. plan de abort y de recuperación manual si la vía falla;
7. evidencia posterior de que el mecanismo puede recuperar el estado o dejar el
   sistema seguro.

La existencia de `/boot/loader/entries/*rescue.conf` no cambia el resultado mientras
no se pueda verificar su selección y su retorno sin reiniciar.

## 4. Clasificación de clientes GPU

La siguiente clasificación es de diseño; no es una autorización de tratamiento.

| PID | PROCESO | CARD | RENDER NODE | FDs | ROLE | CAN_BE_TREATED | TREATMENT_REQUIRED | TREATMENT_METHOD | RECOVERY_IMPACT | RISK | STATUS |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `systemd` | `/dev/dri/card1` | — | 402 | `system_agent` | `NO` sin criterio de excepción | `UNKNOWN` | `T1/T2` sólo si el criterio lo permite; no stop | ninguno directo; quitarlo puede afectar control del host | `HIGH` | `DEFERRED` |
| 975 | `systemd-logind` | `/dev/dri/card1` | — | 28 | `system_agent` | `NO` sin criterio de excepción | `UNKNOWN` | `T1/T2` sólo si el criterio lo permite; no stop | puede afectar sesiones y login | `HIGH` | `DEFERRED` |
| 2457 | `kwin_wayland` | `/dev/dri/card1` | `/dev/dri/renderD129` | 51–55 / 14–17 | `graphical_client_essential` | `CONDITIONAL` sólo por cambio de sesión autorizado voluntariamente | `YES` si `FULL` exige cero handles no aprobados | `T6/T7`; no `T4/T5` en esta fase | perder compositor/display; la recuperación requiere otra sesión | `HIGH` | `DEFERRED` |
| 2671 | `Xwayland` | `/dev/dri/card1` | — | 13 | `session_client` | `CONDITIONAL` sólo con cierre voluntario o sesión alternativa | `YES` si `FULL` exige cero handles no aprobados | `T6/T7`; no kill | pérdida de compatibilidad X11; puede requerir relanzar sesión | `HIGH` | `DEFERRED` |
| 11399 | `ChatGPT` | — | `/dev/dri/renderD129` | 27 | `graphical_client_essential` | `CONDITIONAL`: cierre voluntario, nunca kill implícito | `YES` si `FULL` exige cero handles no aprobados | `T3` como máximo; no `T4/T5` | cierre de aplicación; ventana/UX/sesión pueden cambiar | `MEDIUM/HIGH` | `DEFERRED` |

Campos por holding (`PID`, `UID`, `PARENT/PPID`, `PROCESS`, `EXE`, `CARD`,
`RENDER_NODE`, `FD`, `FD_TARGET`, `FDINFO`, `WCHAN`, `CGROUP`, `NAMESPACES`,
`ROLE`, `CAN_BE_TREATED`, `TREATMENT_REQUIRED`, `TREATMENT_METHOD`,
`RECOVERY_IMPACT`, `RISK`, `STATUS` y `SOURCE`) están en el JSON de análisis.
No se registra aquí un comando de parada o aislamiento.

Distribución de los 13 holdings:

```text
system_agent=2
graphical_client_essential=6
session_client=1
auxiliary_client=0
experiment_process=0
unknown_process=0
```

La ausencia de `auxiliary_client`, `experiment_process` o `unknown_process` en esta
captura no autoriza a eliminarlos: sólo describe los holdings presentes.

## 5. Alternativas de tratamiento

No se elige una alternativa final. Las siguientes son funciones de diseño.

| ID | PRECONDITION | ACTION | REVERSIBILITY | RECOVERY_REQUIRED | RISK | IMPACT_ON_DISPLAY | IMPACT_ON_CHATGPT | IMPACT_ON_SYSTEM | IMPACT_ON_REPRODUCIBILITY | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|
| `T1` | Aceptar que la contaminación permanece | No tratar | N/A | `NO` | `HIGH` para validez C1 | Ninguno | Ninguno | Ninguno | `FAIL` para `OWNERSHIP=FULL` | `DEFERRED_NOT_ACCEPTABLE_AS_FULL` |
| `T2` | Excepción formal de allowlist y prueba de que el recurso no participa | Excluir del alcance | Alta si sólo cambia bookkeeping | `NO` para el experimento | `MEDIUM` | Puede seguir ocupando el GPU | Puede seguir ocupando el GPU | Bajo si no se toca unidad | Sólo vale si `CRITERION` está documentado | `DEFERRED; CRITERION_NOT_DEFINED` |
| `T3` | Usuario cierra voluntariamente la aplicación; no kill | Cierre normal de app | Alta; relanzamiento manual | `NO` si no cambia el display; `YES` si la app es la sesión | `MEDIUM` | Depende de la app | ChatGPT puede cerrar | Bajo | Mejora sólo si desaparecen todos los handles no aprobados | `DEFERRED` |
| `T4` | Autorización por unidad, PRE state y restore verificable | `stop` de servicio/agente | Condicional; depende de restore | `YES` | `HIGH` | Puede afectar el display o la energía | Puede afectar procesos de usuario | Alto: IRQ/PM/display/servicios | Sólo válida con readback completo | `DEFERRED_NOT_AUTHORIZED` |
| `T5` | Diseño de aislamiento reversible y probado | Namespace/cgroup/proceso aislado | `UNKNOWN` sin prueba | `YES` | `HIGH` | Puede cortar display | Puede cortar app | Alto | No equivalente si cambia hardware/sesión | `DEFERRED_NOT_AUTHORIZED` |
| `T6` | Recovery TTY/SSH/sesión independiente verificado | Ejecutar desde otra sesión | Alta para el experimento | `YES` | `MEDIUM` | Puede dejar display intacto | Puede permanecer o cerrarse | Bajo si no se tocan servicios | No basta por sí solo: aún requiere ownership | `DEFERRED` |
| `T7` | Entorno independiente real, mismo RX550 o justificación de equivalencia | Ejecutar en entorno separado | Alta para el host original | `YES` | `HIGH` | Depende del entorno | Separado si hay host independiente | Puede ser muy diferente | No prueba equivalencia sin provenance | `PLAUSIBLE_NOT_VALIDATED` |

`T3` no es permiso para cerrar ChatGPT en esta fase. `T4` no es permiso para
parar `kalm-gpu`, `irqbalance` o `power-profiles-daemon`. `T5` no es permiso para
aislar systemd, KWin, Xwayland o ChatGPT.

## 6. Criterio operacional de `OWNERSHIP=FULL`

El criterio normativo existente es fail-closed. Para una futura declaración FULL
deben cumplirse simultáneamente:

1. `card1` y `renderD129` tienen identidad fija, mappings correctos al mismo BDF y
   evidencia de acceso.root y user completa.
2. El inventario contiene cada proceso/FD relevante con PID, UID, PPID, namespace,
   command/exe, FD target, flags, mapping, timestamp, source y visibility status.
3. No hay `PermissionError`, `FileNotFoundError` no explicado, proceso que desapareció del inventario sin reconciliación, ni writer sin accounting.
4. Existe una allowlist explícita de clientes permitidos y todos los holders están
   clasificados; no se puede añadir una excepción por conveniencia.
5. No existe ningún cliente o writer no aprobado durante la ventana. La lista de
   clientes permitidos y su justificación deben estar documentadas antes del gate.
6. Los agentes que puedan afectar PM, GPU, IRQ, scheduler, read-ahead, storage,
   display o runtime están ausentes, excluidos de forma verificable o autorizados
   explícitamente con restore.
7. Los readbacks PRE/guard/POST tienen timestamps, source, hashes y reglas de
   attribution. `UNKNOWN` en PM, governor, IRQ, scheduler, read-ahead o I/O no se
   convierte en PASS.
8. Btrfs tiene `matched_identity_same_window`, o el gate permanece fallido.
9. El guard es estable según una regla documentada; no se inventa threshold.
10. Existe restore para cada mutación realmente permitida y un camino de recovery
    independiente verificado.

### Respuestas operacionales

- **¿Todos los DRM clients tienen que desaparecer?** No necesariamente todos si una
  allowlist formal los declara permitidos y demuestra que no interfieren; para el
  estado actual no existe esa allowlist, por lo que el default fail-closed es cero
  clientes no aprobados.
- **¿Hay clientes permitibles?** `CRITERION=NOT_DEFINED`. No se puede asumir que
  systemd, KWin, Xwayland o ChatGPT estén permitidos sólo por tener un FD.
- **¿systemd puede permanecer?** `UNKNOWN` como excepción; el criterio actual no
  define una excepción. Su FD en `card1` debe ser reconciliado o rechazado.
- **¿kwin_wayland puede permanecer?** `NO` bajo el criterio actual de owner
  esperado; requiere una sesión/allowlist explícita y restore, no una excepción
  implícita.
- **¿Xwayland puede permanecer?** `NO` bajo el handle no aprobado; necesita cierre
  voluntario o sesión alternativa documentada.
- **¿ChatGPT puede permanecer?** `NO` bajo el handle no aprobado; sólo T3
  voluntario sería una alternativa futura, no una acción permitida aquí.
- **¿kalm-gpu/irqbalance/power-profiles-daemon deben tratarse?** `UNKNOWN` como
  writer/agent hasta que su capability y restore estén documentados; si el criterio
  exige cero writers, requieren tratamiento o allowlist formal. No se detienen aquí.
- **¿Qué significa ownership para `card1` versus `renderD129`?** Son gates de nodo
  separados. Cada uno requiere identity, mapping, inventario completo y readbacks. Un
  handle en `renderD129` no sustituye la prueba de `card1`, ni viceversa. El
  owner esperado actual es `C1_EXPERIMENT_ONLY` para ambos.
- **¿Qué evidencia se conserva antes y después?** Para cada hold: PID, UID, PPID,
  namespace/cgroup, command/exe, FD target/flags, WCHAN, source, timestamp y
  visibilidad. Para cada tratamiento: PRE state, autorización, comando exacto,
  resultado, POST state, readback, error y responsable. También hashes de código,
  runtime, PM, governor, IRQ, scheduler, read-ahead, I/O y Btrfs cuando apliquen.

`CRITERION=NOT_DEFINED` donde no existe una regla objetiva. `THRESHOLD=UNKNOWN`
para PM/governor/IRQ/scheduler/read-ahead/I/O hasta que una fuente Objective
defina métrica, unidades, sampling, attribution y abort.

## 7. Restore

### Estado actual

```text
RESTORE_EXECUTABLE=PARTIAL_FOR_DECLARED_C1_UNIT_ALLOWLIST_ONLY
RESTORE_VERIFIABLE=STATIC_CONTRACT_ONLY; RUNTIME_VALIDATION=NO
RESTORE_FAILURE_HANDLING=DEFINED_FOR_UNITS; ABORT_RESTORE; NO_AUTOMATIC_RETRY
RESTORE_RECOVERY_PATH=NOT_VERIFIED; CURRENT_STATE=FAIL
```

La implementación contiene `restore_units()` y tracking de `touched[]`: registra
PRE state, intenta start sólo de unidades tocadas y readback de `ActiveState`
(`c1_isolation_automator.py:L2323-L2442`). `settle_restore_contract()` marca
`ABORT_RESTORE` si el restore o POST no son satisfactorios
(`L2445-L2453`). Esto es diseño/contrato estático; no se ejecutó y no demuestra
restore runtime.

| Recurso | Restore actual | Verificación required | Estado |
|---|---|---|---|
| Unidades C1 allowlist | start/stop y readback para unidades PRE-active | PRE/POST state, `MainPID`, `UnitFileState`, error | `PARTIAL_STATIC_ONLY` |
| PM | `NO_CHANGE_PLANNED`; no mutación | PRE/guard/POST readback; si se mutara, inversa/readback | `NOT_EXECUTED` |
| Governor | `NO_CHANGE_PLANNED` | políticas PRE/guard/POST y writer accounting | `NOT_EXECUTED` |
| IRQ/affinity | `NO_CHANGE_PLANNED` | IRQ y afinidad PRE/guard/POST | `NOT_EXECUTED` |
| Scheduler | `NO_CHANGE_PLANNED` | scheduler/priority/renice PRE/guard/POST | `NOT_EXECUTED` |
| Read-ahead | `NO_CHANGE_PLANNED` | valor PRE/guard/POST y autor | `NOT_EXECUTED` |
| GPU cap/DPM/PM | `NO_CHANGE_PLANNED` | identity y controles; cualquier cambio futuro requiere nueva fila | `NOT_EXECUTED` |
| Runtime namespace | `RuntimeArtifacts` tiene cleanup de paths propios y validación de layout | ausencia de runs huérfanos | `DESIGNED_NOT_MATERIALIZED` |
| systemd/KWin/Xwayland/ChatGPT | no hay stop/close/isolate en esta ruta | mechanism de sesión/proceso y POST readback | `PROCESS_RESTORE_NOT_DEFINED` |
| DRM ownership | no se modifica | recheck completo de ambos nodos | `NOT_AVAILABLE` |
| `/dev/sda`/Btrfs | `NO_TOUCH_PLANNED` | identity/activity POST; no probe/repair | `NOT_EXECUTED` |

Por tanto, un futuro tratamiento de clientes no puede declarar restore verificable
sólo porque el automator tenga una función de restore de unidades. El restore de
sesión/procesos gráficos es `NOT_DEFINED`, y recovery independiente sigue `FAIL`.

## 8. Runtime v2: artefactos que faltan

`RUNTIME_V2_PRESENT=NO`; no se creó el path. Antes de una fase runtime autorizada
deben existir y estar validados, sin colisiones:

```text
/run/user/1000/c1-isolation-automator-v2/        real directory, UID 1000, mode private
  .lock                                           regular private lock, no symlink
  CURRENT                                         regular private pointer or documented absent pre-run
  c1-observer-v1.jsonl                            exact path, parseable, durable; absent before C1
  runs/<run-id>/                                  private directory
    state.json                                    schema_version=2, required state fields, hashes
    events.jsonl                                  durable JSONL matching state
    tmp/                                          private
    cache/                                        private
```

Además deben cumplirse:

- `/run/user/1000` debe ser tmpfs y tener layout/UID/mode esperados;
- v2 y legacy deben ser siblings separados; el legacy no se borra ni se carga como
  estado activo;
- `CURRENT` debe ser regular, privado, trazable y apuntar sólo a un run ID válido;
- `state.json` debe pasar el schema completo, incluyendo `runtime_contract`,
  `restore_contract`, `contract_manifest`, PRE/guard/C1/restore/POST e iniciales/final;
- `events.jsonl` debe coincidir con state y tener hashes;
- el observer debe ser el path/hash esperado y no existir antes de la corrida;
- TTY interactiva, `RUN-C1` y autenticación normal deben estar verificados en la
  fase autorizada;
- no debe haber C1/observer collision, run orphan o estado v2 incompleto;
- todo artefacto creado debe quedar registrado en `RuntimeArtifacts` para cleanup
  limitado; cleanup no está autorizado en esta fase.

La existencia del diseño v2 y los tests estáticos no equivale a
`RUNTIME_MATERIALIZED=YES` o `RUNTIME_VALIDATED=YES`.

## 9. Decisión

```text
DESIGN_DOCUMENT=PREPARED_FOR_REVIEW
RECOVERY_DESIGN=DEFINED
GPU_CLIENT_TREATMENT_DESIGN=DEFINED
OWNERSHIP_CRITERION=DEFINED_EXCEPTIONS_NOT_DEFINED
RESTORE_STATIC_REVIEW=PARTIAL
RUNTIME_V2=NOT_AVAILABLE
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

No se elige T1–T7. No se autoriza C1. La decisión runtime requerirá una fase posterior
separada con autorización específica para las acciones necesarias.

## 10. Provenance

- Parent evidence: `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json`.
- Parent JSON SHA256: `1b1f8e27cdc53a9a3d1f2353bd819ceb15008dbd96ee99f534cda1db81246e0f`.
- C1 code SHA256: `006149849f4b0ba1a3dcb7f29b19501d9cccf04e54248215bc6471272be3e06d`.
- Design SHA256: `8401208ea84a406c7eb24e68c2f47693a38f7e0f5ac95acd24130e190fee9ef0`.
- AGENTS SHA256: `20201819c693311ce3c1c40af0db3c36af0b7f861e334cf3abb471e74017488b`.
- Recovery system reads: 2026-09-25, `tty`, `/proc/consoles`,
  `/sys/class/tty/console/active`, `systemctl show`, `ss -ltn`, `loginctl`,
  `/boot/loader/entries` metadata y hashes de boot documents.
- No se consultó documentación externa de OpenCode sobre recovery porque la normativa de recovery
  y C1 ya estaba definida en los documentos del proyecto; no se introdujo una regla
  externa.
- `C1_EXECUTED=0`, `RUNTIME_MATERIALIZED=0`, `GPU_WRITES=0`, `STORAGE_WRITES=0`,
  `SYSTEMD_CHANGES=0`, `SYSTEM_CHANGES=0`, `COMMIT=0`.
