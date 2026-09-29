# R1 MEDIUM FIX RECORD — MED-1..MED-5

```
MED5_SUDO_CLAIM=FIXED
BUNDLE_IDENTITY=FIXED_HOST_AND_KERNEL_REQUIRED
INVALID_METADATA=FIXED_CLASSIFIED_NOT_FATAL
PID_DISAPPEARED=FIXED_DISTINGUISHED_FROM_DENIAL
BRIDGE_FIXTURE=REALISTIC_REPLACED_T22B
HASH_BEFORE=0985ad03afffa848301200c464b85e40e038964e6f3e9674f5a730bc3a6d5849
HASH_AFTER=ae115054a89a51944362d812412886c1901eabcd139e801495a979440cca19e7
COLLECTOR_PROVENANCE=GIT_INDEX_STAGED_NOT_IN_HEAD
R1_SAFE_TO_AUTHORIZE=YES
R1_EXECUTED=NO   PRIVILEGED_EXECUTION=NO   SUDO_INVOKED=0
```

**Fecha:** 2026-09-26 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Fichero modificado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Test creado:** `test_medium_fixes.py` (27 tests, P35–P47 + puente realista)
**Tests existentes modificados:** 3, por citar expresiones anteriores.

---

## 1. MED-5 — privilegio observado, no afirmado

`observe_privilege_state()` lee el **euid real** del proceso. El wrapper previsto ya no se
confunde con la elevación:

```python
PRIVILEGE_STATE   = PRIVILEGE_OBSERVED_ROOT | PRIVILEGE_NOT_ROOT | PRIVILEGE_UNKNOWN
EUID_OBSERVED     = <int> | None
EUID_OBSERVATION  = OK | ERROR
SUDO_COMMAND_EXPECTED = YES          # el wrapper documentado
SUDO_INVOKED      = NOT_OBSERVED     # nunca afirmado
```

`metadata.sudo_invoked: True` y `sudo.SUDO_INVOKED: "YES"` **eliminados**. El payload lleva
ahora `privilege` observado, y `privileged_reads` se deriva de
`PRIVILEGE_STATE == "PRIVILEGE_OBSERVED_ROOT"`. El camino de aborto también observa privilegio.
El collector no ejecuta ni detecta `sudo`; solo lee su propio euid.

Verificado en este host sin elevar: `EUID_OBSERVED=1000` → `PRIVILEGE_NOT_ROOT`, mientras
`SUDO_COMMAND_EXPECTED=YES`. Antes habría afirmado `SUDO_INVOKED=YES`.

## 2. MED-4 — política de identidad del bundle, explícita

```
host  ausente            -> NOT_AVAILABLE  / REJECTED_PARENT_IDENTITY_NOT_AVAILABLE
host  distinto           -> HOST_MISMATCH  / REJECTED_HOST_MISMATCH
host  coincide, sin kernel -> INCOMPLETE   / REJECTED_INCOMPLETE_IDENTITY
kernel distinto          -> KERNEL_MISMATCH / REJECTED_KERNEL_MISMATCH
ambos coinciden          -> MATCH          / ACCEPTED_SAME_HOST_AND_KERNEL
```

El caso `INCOMPLETE` es nuevo: antes un bundle con host y sin kernel se admitía en silencio
porque el chequeo se saltaba con `if observed_kernel and ...`. La política queda escrita en el
propio resultado: `policy = "host must match AND kernel must be present AND kernel must match"`.

`OWNERSHIP_EVIDENCE_FROM_PARENT` es `ADMITTED` o `NOT_AVAILABLE` — explícito, no implícito.
Además `btrfs_observation.parent_state` — la última lectura del padre que quedaba sin filtro —
ahora devuelve `"NOT_AVAILABLE_PARENT_BUNDLE_NOT_ADMITTED"` cuando el bundle no se admite.

## 3. MED-3 — metadata malformada, clasificada

`assess_parent_bundle` ya no lanza excepción ante `metadata` (o el bundle entero) de tipo
`str`, `list`, `int`, `bool` o `None`:

```
PARENT_BUNDLE_METADATA = INVALID
PARENT_BUNDLE_IDENTITY = INVALID
PRIOR_EVIDENCE_STATUS   = REJECTED_BUNDLE_MALFORMED
OWNERSHIP_EVIDENCE_FROM_PARENT = NOT_AVAILABLE
```

Nunca crash, y nunca `[]` ni cero clientes: `prior_errors`/`prior_clients` quedan vacíos solo
como consecuencia de `PRIOR_EVIDENCE_ADMISSIBLE == False`, y el diferencial se emite como
`"NOT_AVAILABLE"`.

## 4. LOW-2 — un PID desaparecido no es una denegación

`classify_proc_error()` nombra la causa, y `parse_proc_stat` / `scan_fds` la propagan en un
campo `reason` sin perder el `error` original.

| Causa | Clase | Efecto en coverage |
|---|---|---|
| `PermissionError` | `PERMISSION_DENIED` | **sí** degrada visibility |
| `FileNotFoundError` / `ProcessLookupError` | `PROCESS_DISAPPEARED` | no; `NOT_APPLICABLE_PER_OBSERVATION` |
| otro | `OTHER_ERROR` | **sí** degrada visibility |

```python
root_visibility_complete = (root_fd_permission_denied == 0
                            and root_fd_other_errors == 0
                            and not current_run_permission_denied
                            and len(unresolved_prior) == 0)
```

Un proceso efímero que muere durante el barrido ya no produce el mismo estado que una denegación
de aislamiento. La causa queda registrada en `current_run_disappeared_pids`,
`current_run_permission_denied_pids` y los contadores por clase.

## 5. MED-1 / MED-2 — reconciliación documental y fixture del puente

### Reconciliación

En `R1-DEFECT-FIX-RECORD-20260926.md` afirmé que el check de `vendor`/`device` «prueba que ese
directorio es un dispositivo y no un puente o un bus». **Es falso y queda corregido aquí.**

Verificado en este host, read-only:

```
0000:00:01.0  vendor=0x8086  device=0x0c01  class=0x060400   <- puente: TIENE vendor/device
0000:01:00.0  vendor=0x1002  device=0x699f  class=0x030000   <- endpoint RX550
```

Formulación correcta, y es la que el código implementa:

1. **La estructura PCI identifica el directorio endpoint** — el BDF es el *nombre* del
   directorio al que resuelve `<nodo>/device`, validado con `fullmatch` y con la presencia de
   atributos de dispositivo.
2. **La clase PCI distingue dispositivo gráfico de bridge** — `class=0x030000` frente a
   `0x060400`. **Esta es la barrera real contra un puente**, y vive en `resolve_node_device`,
   no en `resolve_pci_device_dir`.
3. **`vendor`/`device` identifican la RX550** — `0x1002`/`0x699f` leídos en el endpoint.
4. **`driver=amdgpu` y la re-verificación completa** cierran la identidad.

Ninguna lógica de seguridad se relajó. El registro anterior **no se sobrescribe**; esta
reconciliación lo corrige.

### Fixture del puente

`T22b` construye un directorio con forma de BDF **sin** `vendor`/`device` — imposible en sysfs
real, porque todo dispositivo PCI, puente incluido, tiene ambos. Se sustituyó por un fixture
realista con los valores reales de este host, y se añadió la aserción de que el motivo del
rechazo es **clase/identidad**, no un atributo ausente:

```python
self.assertNotEqual(node["BDF_LINK_ABORT"], "DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE")
self.assertTrue(any("class=" in m for m in node["mismatches"]))
self.assertTrue(any("vendor=" in m for m in node["mismatches"]))
```

`test_the_bridge_really_does_have_vendor_and_device` falla si el fixture deja de representar la
realidad, para que no vuelva a ser un test de fixture superficial.

## 6. La matriz de ownership NO cambió

Condición de parada explícita del encargo. `ownership_matrix` no fue editada por ninguna de las
cuatro correcciones. Verificado:

- 11 condiciones, nombres y descripciones idénticos a los documentados en la revisión.
- `writers_resolved` → `NOT_EVALUATED` / R2; `guard_and_restore` → `NOT_EVALUATED` / R3.
- El agregado exige `states ⊆ {PASS, NOT_APPLICABLE}`, luego **`FULL` sigue inalcanzable**.
- Las entradas del contexto que consume la matriz no cambiaron de nombre ni de significado.

## 7. Tests

| Suite | Resultado |
|---|---|
| `test_medium_fixes.py` (nuevo: P35–P47 + puente realista) | **27 OK** |
| `test_privileged_read_collector.py` | **43 OK** |
| `test_collector_failure_modes.py` | **35 OK** |
| `test_med_review_classifications.py` | **26 OK** |
| `test_r1_defects.py` | **23 OK** |
| **Total del lado collector** | **154 OK, 0 fallos** |

**`test_c1_isolation_automator.py` (54 tests) NO se pudo re-ejecutar.** Durante esta fase el
directorio `04-IMPLEMENTATION/tests/` dejó de ser resoluble — `find` localiza el fichero,
`ls` y `os.path.isdir` dicen que el directorio no existe, y el directorio padre sí resuelve.
Se intentó 5 veces. **No se afirma que pase.** No es una regresión: el automator C1
(`c1_isolation_automator.py` = `006149849f4b0ba1`) y su test no fueron editados en esta fase;
los únicos ficheros tocados están bajo `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`.

**Cuatro tests existentes fallaron** al endurecer las expresiones, y los cuatro merecían
fallar: el allowlist de read-only detectó `os.geteuid`/`os.getegid` sin clasificar, y tres tests
citaban la expresión anterior de `root_visibility_complete`. Actualizados, y `T31` ahora
comprueba además la **ausencia** del carve-out de PIDs desaparecidos.

**Cinco defectos míos en `test_medium_fixes.py`**, todos de mock: `scan_fds` lista la tabla con
`os.listdir`, no con `Path.open`; un FIFO da `EINVAL` en `readlink`, no `PermissionError`; y
`ast.unparse` recibía la función en vez del nodo AST. Ninguno era defecto del collector.

## 8. Auditoría AST

```
mutating calls (excl. str.replace) : NONE
str.replace                        : 3
shell=True                         : 0
os.environ                         : 0
sudo as an executed command        : NONE
subprocess.run                     : 1  (solo el wrapper)
'with' open modes                  : {'rb'}
imports                            : sin subsistemas mutantes
```

## 9. Procedencia e integridad

```
HASH_BEFORE = 0985ad03afffa848301200c464b85e40e038964e6f3e9674f5a730bc3a6d5849
HASH_AFTER  = ae115054a89a51944362d812412886c1901eabcd139e801495a979440cca19e7
lines       = 2597 -> 2764
HEAD        = c6146788e0d4fb12d9b0ec1209fa2840692de0c5   (sin commit)
STAGED      = 360 rutas                                    (índice, separado de HEAD)
PROVENANCE  = GIT_INDEX_STAGED_NOT_IN_HEAD
```

Históricos no modificados: `R1-PLAN` `5832a468…`, `R1-PREFLIGHT` `61f5d5f7…`, revisión
independiente #1 `79bede39…`, `R1-DEFECT-FIX-RECORD` `a02b56c0…`, revisión #2 `bceddac1…`,
JSON del R1 abortado `fe2847b9…`, `AGENTS.md` `d5fa85a4…`, router `9ef58048…`, censo
`a4ccacbc…`, `ROUTING-LOG` `ff9110e9…` (24 eventos).

```
SYSTEM_CHANGES=0  GPU_CHANGES=0  SERVICE_CHANGES=0  SYSFS_WRITES=0
PROCESS_TERMINATED=0  PROCESS_SUSPENDED=0  SUDO_INVOKED=0

OWNERSHIP=PARTIAL   BLK_01=NOT_CLOSED   G1=OPEN
```
