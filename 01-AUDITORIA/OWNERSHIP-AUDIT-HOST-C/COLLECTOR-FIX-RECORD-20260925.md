# R1 COLLECTOR — FIX RECORD (HIGH-1, HIGH-2, HIGH-3, MED-1)

```
COLLECTOR_CHANGE=FIXED_FOUR_FINDINGS
COLLECTOR_HASH_BEFORE=41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9
COLLECTOR_HASH_PREVIOUS=a2cf80c7cc28f27e48fc637df999a27a1d3ee2bbce1339d84f0cbf295f57f2f0
COLLECTOR_PROVENANCE=GIT_INDEX_STAGED_NOT_IN_HEAD
COLLECTOR_RUNTIME_EXECUTED=NO
PRIVILEGED_EXECUTION=NO
SUDO_INVOKED=0
R1_SAFE_TO_AUTHORIZE=YES
```

**Fecha:** 2026-09-25 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Único fichero de código modificado:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Fichero de test creado:** `test_collector_failure_modes.py` (35 tests, T01–T16)
**Test existente ampliado:** `test_privileged_read_collector.py` (allowlist, 2 entradas)
**Sin otra refactorización.** R1 no ejecutada. Ningún `sudo`.

---

## 1. HIGH-1 · El BDF ya no se prueba con el texto de la ruta

**Causa.** `os.path.realpath()` resuelve la cadena de enlaces hasta donde llega y **devuelve una
cadena**. Como `class/drm/<nodo>` es un enlace dentro de un directorio nombrado con el BDF, un
nodo cuyo enlace `device` falta o está roto producía igual una ruta cuyo texto contiene el BDF.

**Corrección.** Nueva función `resolve_node_device(node_dir)`, que exige **en orden**:

| # | Comprobación | Si falla |
|---:|---|---|
| 1 | `<nodo>/device` es symlink | `DEVICE_LINK_ABSENT` / `DEVICE_NOT_A_SYMLINK` |
| 2 | el destino existe (`os.path.exists` sobre el realpath, estricto) | `DEVICE_TARGET_ABSENT` |
| 3 | el destino es un directorio | `DEVICE_TARGET_NOT_A_DIRECTORY` |
| 4 | el BDF es derivable **de ese destino existente** | `BDF_NOT_RESOLVABLE_FROM_EXISTING_TARGET` |
| 5 | `vendor=0x1002` **leído en el destino resuelto** | `PCI_IDENTITY_MISMATCH_AT_NODE` |
| 6 | `device=0x699f` ídem | ídem |
| 7 | `class=0x030000` y `driver=amdgpu` ídem | ídem |

Un nodo con `BDF_LINK_STATUS != PROVEN` **nunca** es candidato: va a `excluded` con su motivo, y
como el barrido forward sigue viéndolo, las dos direcciones discrepan →
`DIRECTION_DISAGREEMENT` → `IDENTITY_NOT_PROVEN` → aborto.

**Punto clave:** la identidad se re-verifica **en el destino resuelto**, no en la ruta de la
que se leyó el texto del BDF. Un `device` apuntando a la Intel falla por
`PCI_IDENTITY_MISMATCH_AT_NODE` (0x8086), no por una simple diferencia de BDF.

**Verificado:** T01, T02, T02b, T03, T04, T05, T05b, T01b, T01c.

## 2. HIGH-2 · Un solo recorrido, un solo registro por PID

**Causa.** El primer bucle recorría todos los PIDs llamando a `classify()`; el segundo volvía a
llamar a `classify()` para los `service_pids` que no estaban en `interesting` — PIDs ya
contabilizados. Producía contadores inflados, `root_fd_errors` duplicados y **filas de cliente
duplicadas**.

**Corrección, estructural.** Se eliminó el segundo escaneo:

- Un único `for pid in proc_pids(): pid_records[str(pid)] = observe(pid)`.
- `observe()` es el **único** lugar que lee `proc_meta`/`scan_fds`/`scan_maps` y el único que
  incrementa contadores, inserta en `gpu_clients`/`storage_clients` y añade a `root_fd_errors`.
- `interesting` es una **vista** de `pid_records`, construida por comprehension.
- El bucle de servicios **consulta** `pid_records`; solo observa si el PID no está, lo que
  significa que no existía en el barrido y por tanto no podía estar contado. Esos casos se
  registran en `late_observed_pids` y **no** entran en `total_pids`.
- Fuera de `observe()` solo se incrementan `total_pids` y `late_observed_pids`, que son
  contabilidad del recorrido, no evidencia por PID.

No hay `set` posterior que tape el problema: la deduplicación es por construcción, porque no
existe una segunda lectura que pueda duplicar.

**Verificado:** T06 (`scan_fds`/`scan_maps`/`proc_meta` solo dentro de `observe()`; bucle de
servicios con `if key in pid_records:`), T07 (las seis fuentes de verdad presentes en un solo
sitio), T07b (contadores de evidencia todos dentro de `observe()`).

## 3. HIGH-3 · Poblaciones de namespace independientes

**Causa.** Un único `namespace_ok` global alimentaba las dos filas, y se comparaba contra
`user_pids`, que es un tamaño de subconjunto. En HOST-C (199 root de 283) una lectura completa
daba `namespace_ok=283` frente a `user_pids=84` → `FAIL` espurio. Y no existía entrada posible
para que root estuviera cubierto y user no.

**Corrección.** Contadores separados, poblados en el mismo `observe()`:

```
root_pids · root_namespace_ok · root_namespace_denied · root_namespace_total
user_pids · user_namespace_ok · user_namespace_denied · user_namespace_total
uid_unknown_pids
```

Cada condición se evalúa **solo** contra su denominador:

```python
root_namespace_complete = root_namespace_total > 0 and root_namespace_ok == root_namespace_total
user_namespace_complete = user_namespace_total > 0 and user_namespace_ok == user_namespace_total
```

`> 0` evita que una población vacía se reporte como completa: no observada no es completa.
Un PID con `uid` ilegible va a `uid_unknown_pids` y **no** entra en ninguna población, en vez de
ser clasificado como user por defecto.

**Verificado:** T08, T09, T10, T11, más T11b y T11c, que fijan la propiedad clave: la misma
densidad de datos root con poblaciones user de 84, 80, 0 y 500 debe dar **siempre** el mismo
veredicto root.

## 4. MED-1 · `NOT_PROVEN` de storage ya no es «cero clientes»

**Causa.** Con storage no identificado, `storage_devices` quedaba vacío, luego
`storage_clients=[]`, luego `active_storage=0`, y ese 0 satisfacía `ownership_full` y `g02`.
Es exactamente la conversión «ausencia de evidencia → evidencia de ausencia» que el GAP 5 vino
a impedir, reintroducida por un camino nuevo.

**Corrección.**

```python
storage_proven           = storage_identity["STORAGE_IDENTITY_STATUS"] == "PROVEN"
active_storage           = len(storage_clients) if storage_proven else None
storage_client_evidence  = "EVALUATED" if storage_proven else "NOT_EVALUATED"
storage_no_clients       = storage_proven and active_storage == 0
```

`ownership_full`, `g02` y `NO_UNAUTHORIZED_CLIENTS` usan `storage_no_clients`, que es `False`
cuando la identidad no está probada. El booleano legacy queda **forzado a falso** en vez de
satisfacerse por falta de datos. En el payload, `active_storage_clients` se emite como
`"NOT_EVALUATED"`, nunca como `0`, y se añade `storage_client_evidence` y
`storage_identity_status`.

**Verificado:** T12, T13, T14, T14b, T15, T15b.

## 5. Booleano legacy: sin regresión

`COLLECTOR_OWNERSHIP_BOOLEAN=NON_AUTHORITATIVE` conservado. `ownership_full` sigue siendo la
misma conjunción de cuatro condiciones, con `storage_no_clients` en lugar de `active_storage == 0`.
`final.OWNERSHIP` sigue viniendo de `AGENTS_OWNERSHIP_MATRIX.OWNERSHIP_CRITERION_STATE`.

`writers_resolved` (R2) y `guard_and_restore` (R3) continúan en `OWNERSHIP_EXTERNAL_ROWS`, que
se consulta **antes** del diccionario `observed`, de modo que no existe entrada desde la que
convertirse. El agregado no puede alcanzar `FULL`.

**Verificado:** T16, T16b, T16c. T16b comprueba por AST que las dos filas **no aparecen** en el
bloque `observed = {…}` de `ownership_matrix`.

## 6. Resultados

| Suite | Resultado |
|---|---|
| `test_privileged_read_collector.py` (existente, allowlist ampliada) | **43 OK** |
| `test_collector_failure_modes.py` (nuevo, T01–T16) | **35 OK** |
| `test_c1_isolation_automator.py` (existente) | **54 OK**, skipped=1 |
| **Total** | **132 OK, 0 fallos** |

**Un test antiguo falló al principio y mereció la pena.** El allowlist de
`test_privileged_read_collector.py` está diseñado para fallar ante cualquier método no
clasificado, y detectó `os.path.isdir` y `.is_symlink()` introducidos por HIGH-1. Era el
comportamiento correcto del test; se clasificaron como pruebas de existencia. Un allowlist
permisivo habría pasado en silencio.

**Defectos míos durante esta fase, todos en los tests:** un `]` residual, indentedado roto por un
replace global (5 puntos), un `cleandoc` inválido, un helper de disco sin el enlace de la
partición, y dos aserciones que afirmaban menos de lo que el collector garantiza — T03 espere
`DIFFERENT_BDF` cuando el collector lo rechaza correctamente por
`PCI_IDENTITY_MISMATCH_AT_NODE`, y T06/T07b contaban llamadas dentro de `observe()` como si
estuvieran fuera. Ninguno era defecto del collector. Todos corregidos y verificados.

## 7. Revisión AST final

Escaneo independiente sobre el fichero corregido, sin allowlist:

```
mutating-capable calls : NONE   (3 × str.replace: NUL de cmdline, prefijo /dev/dri)
shell=True              : 0
os.environ             : 0
subprocess.run          : 1  (solo el wrapper auditado)
'with' blocks           : 2,  ambos con open("rb")
'sudo'                  : 1  occurrence, y es la clave JSON "sudo": {...} del payload,
                          no un argumento de ejecución
```

Ninguna escritura, ningún mutador de procesos, ningún cambio de sistema, ningún `sudo`.

## 8. Reconciliación

Ningún histórico se sobrescribió. Lo que quedó obsoleto:

| Documento | Afirmación | Estado |
|---|---|---|
| `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md` (`79bede39…`) | `HIGH_FINDINGS=3`, `MED_FINDINGS=4`, `R1_SAFE_TO_AUTHORIZE=NO` | **SUPERADO** por este registro. Los 3 HIGH y MED-1 están corregidos. MED-2/3/4 y LOW-1..4 **permanecen abiertos** — no se pidieron |
| `COLLECTOR-CHANGE-RECORD-20260925.md` (`f04ae667…`) | «reverse: realpath → BDF» como prueba bidireccional | **OBSOLETE**: era exactamente el punto débil de HIGH-1. Sustituido por `resolve_node_device()` |
| `COLLECTOR-CHANGE-RECORD-20260925.md` | `43 tests OK` | **SUPERADO**: el suite mapeaba los GAP, no los modos de fallo — 3 HIGH convivían con 43/43 |
| `R1-PREFLIGHT-drm-identity-and-command-audit.md` (`61f5d5f7…`) | intacto | sin cambio |

**MED-3 sigue abierto:** `card_node_complete` y `render_node_complete` siguen siendo el mismo
`root_visibility_complete`. No estaba en los cuatro defects autorizados, así que **no se tocó**.

## 9. Procedencia

```
COLLECTOR_HASH_BEFORE     = 41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9
COLLECTOR_HASH_PREVIOUS   = a2cf80c7cc28f27e48fc637df999a27a1d3ee2bbce1339d84f0cbf295f57f2f0
COLLECTOR_PROVENANCE      = GIT_INDEX_STAGED_NOT_IN_HEAD
```

`41fee794` **no está en HEAD**: `git show HEAD:<path>` devuelve `e3b0c442…`, el SHA-256 de la
cadena vacía, porque el fichero fue *staged* en la fase de parches y nunca *commiteado*. Su
única procedencia es el índice de git, verificado byte a byte. `a2cf80c7` era el estado
revisado; este cambio parte de ahí. **No se hizo commit ni se modificó git.**

## 10. Garantías

```
COLLECTOR_RUNTIME_EXECUTED=NO   PRIVILEGED_EXECUTION=NO   SUDO_INVOKED=0
SYSTEM_CHANGES=0   GPU_CHANGES=0   SERVICE_CHANGES=0   SYSFS_WRITES=0
PROCESS_TERMINATED=0   PROCESS_SUSPENDED=0   PATCHES_APPLIED=0
C1_EXECUTED=NO     R1_EXECUTED=NO
MODIFIES_AGENTS_MD=NO  MODIFIES_ROUTER=NO  MODIFIES_CENSUS=NO
MODIFIES_ROUTING_LOG=NO  MODIFIES_HISTORICAL_CAPTURES=NO
MODIFIES_R1_PLAN=NO      MODIFIES_R1_PREFLIGHT=NO  MODIFIES_REVIEW=NO
```

Sin cambios: `AGENTS.md` `d5fa85a4…`, `README.md` `4524f6f6…`, censo `a4ccacbc…`, router
`9ef58048…`, `ROUTING-LOG.jsonl` `ff9110e9…` (24 eventos), BLK-02 `6c6e0353…`, ownership audit
`3bd1c05c…`, closure attempt `9f7f8378…`, reconciliación `06f337c7…`, R1-PLAN `5832a468…`,
R1-PREFLIGHT `61f5d5f7…`, revisión independiente `79bede39…`.

```
OWNERSHIP=PARTIAL   BLK_01=NOT_CLOSED   G1=OPEN
```

Que `R1_SAFE_TO_AUTHORIZE=YES` **no significa que R1 deba ejecutarse**: la autorización sigue
siendo tuya, y R2, R3, MED-2, MED-3, MED-4 y LOW-1..4 siguen abiertos.

> **Anotación posterior (2026-09-26) sobre el MED-2 de la lista anterior.** No se modifica la
> frase ni se cierra ninguno de los ítems: R2, R3, MED-3, MED-4 y LOW-1..4 siguen abiertos, y
> **R1 sigue abierto**. Lo único que se anota es que el MED-2 de esta lista
> (`R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:127`, "los namespaces colapsan todos los modos de
> fallo en `UNAVAILABLE`") recibió después una corrección documentada en
> `01-AUDITORIA/R1-NAMESPACE-ERROR-ATTRIBUTION-20260926.md`: la causa del fallo de namespace ahora
> se conserva y se discrimina. Su veredicto histórico `NON_BLOCKING_LIMITATION`
> (`R1-DEFECT-FIX-RECORD-20260926.md:209`) **no se reclasifica**, y no se ha ejecutado ningún
> re-barrido privilegiado posterior, por lo que `user_namespaces_covered` no puede declararse
> resuelta.
