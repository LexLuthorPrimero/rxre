# R1 DEFECT FIX RECORD — DEFECT-01 and DEFECT-02

```
DEFECT01=FIXED
DEFECT02=FIXED
HASH_BEFORE=f0a2ac0b6b465486ccacff6e7ea4278683dd7aa3dbd5b0fad92ff9e783cb58e5
COLLECTOR_PROVENANCE=GIT_INDEX_STAGED_NOT_IN_HEAD
R1_SAFE_TO_AUTHORIZE=YES
R1_EXECUTED=NO   PRIVILEGED_EXECUTION=NO   SUDO_INVOKED=0
```

**Fecha:** 2026-09-26 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Origen:** R1 run `R1-20260926T000649Z` abortó con `IDENTITY_NOT_PROVEN / DIRECTION_DISAGREEMENT`.
**Fichero modificado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Test creado (único):** `test_r1_defects.py` (23 tests, T17–T34)
**Tests existentes modificados:** 3, todos por afirmar el diseño anterior.

---

## 1. DEFECT-01 — el BDF venía del puente PCI

### Antes

`_bdf_from_realpath()` aplicaba `BDF_RE.search()` al realpath y devolvía la **primera**
coincidencia. En HOST-C la RX550 está detrás de un puente:

```
/sys/class/drm/card1/device
  -> /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0
                      ^^^^^^^^^^^^ puente   ^^^^^^^^^^^ endpoint
```

`search()` devolvía `0000:00:01.0`. `card1` y `renderD129` se clasificaron `DIFFERENT_BDF`,
las listas inversas quedaron vacías y las dos direcciones discrepan.

### Ahora

`resolve_pci_device_dir()` sustituye al extractor por texto. Exige, en orden:

| # | Comprobación | Aborta con |
|---:|---|---|
| 1 | `<nodo>/device` es symlink | `DEVICE_LINK_ABSENT` / `DEVICE_NOT_A_SYMLINK` |
| 2 | el destino existe (`os.path.exists`, estricto) | `DEVICE_TARGET_ABSENT` |
| 3 | el destino es directorio | `DEVICE_TARGET_NOT_A_DIRECTORY` |
| 4 | el **nombre** del directorio es un BDF **completo** (`fullmatch`) | `DEVICE_DIR_NAME_IS_NOT_A_BDF` |
| 5 | el directorio expone `vendor` y `device` | `DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE` |

El BDF es el **nombre del directorio destino**, porque sysfs nombra los directorios de
dispositivo PCI por su BDF. No es «la última coincidencia»: es identificación **estructural**,
y el punto 5 prueba que ese directorio es un dispositivo y no un puente o un bus. Los
componentes BDF de la ruta se registran en `bdf_components_in_path` como evidencia y **nunca**
se usan como identidad.

### La verificación de identidad NO se relajó

`resolve_node_device()` sigue re-verificando en el directorio resuelto:

```
vendor=0x1002  device=0x699f  class=0x030000  driver=amdgpu
```

Cualquier fallo → `PCI_IDENTITY_MISMATCH_AT_NODE` → nodo excluido → `IDENTITY_NOT_PROVEN`. Con
el BDF ahora correcto, un desajuste aquí es un desajuste real.

### Verificado en el host real (read-only, sin sudo)

```
bdf_components_in_path : ['0000:00:01.0', '0000:01:00.0']
device_dir_bdf         : 0000:01:00.0
GPU_IDENTITY_STATUS    : PROVEN
GPU_BDF                : 0000:01:00.0
card1 (minor 1) / renderD129 (minor 129)
devices                : ['/dev/dri/card1', '/dev/dri/renderD129']
excluded (Intel)       : card0 y renderD128 -> 0000:00:02.0, PCI_IDENTITY_MISMATCH_AT_NODE
```

`T25b` deja constancia explícita de que la heurística antigua habría devuelto el puente.

### El hueco que dejó pasar el defecto

HIGH-1 probó que el enlace `device` **existe**. Nadie probó que el BDF **extraído** fuera el del
dispositivo. Los 43+35+26 tests anteriores no lo cazaron porque **todos mis árboles sintéticos
colocaban el dispositivo directo sobre `pci0000:00`, sin segmento de puente** — la forma que
la iGPU sí tiene y que por eso pasaba desapercibida. El fixture, no el criterio, era el
problema. `test_r1_defects.build()` ahora anida los directorios como sysfs real, y `T19`
reproduce la ruta exacta del aborto.

## 2. DEFECT-02 — evidencia heredada de otro host

### Antes

El collector consumía `ownership.fd_visibility_errors` (363 PIDs) y `ownership.clients` (2) del
bundle padre **sin comparar la identidad de host**. El padre era `lex-luthor` / kernel
`7.2.6-201` (HOST-A); la ejecución era `kalm` / `7.1.3-200` (HOST-C). Esos PIDs no existen
aquí, así que `unresolved_prior` habría sido no vacío y
`root_visibility_complete` habría sido `False` con un FAIL espurio.

### Ahora

`assess_parent_bundle(parent, current_host, current_kernel)` decide la admisibilidad:

| Situación | `PARENT_BUNDLE_IDENTITY` | `PRIOR_EVIDENCE_STATUS` |
|---|---|---|
| mismo host y kernel | `MATCH` | `ACCEPTED_SAME_HOST_AND_KERNEL` |
| host distinto | `HOST_MISMATCH` | `REJECTED_HOST_MISMATCH` |
| kernel distinto | `KERNEL_MISMATCH` | `REJECTED_KERNEL_MISMATCH` |
| sin identidad declarada | `NOT_AVAILABLE` | `REJECTED_PARENT_IDENTITY_NOT_AVAILABLE` |

Sobre rechazo, **ninguna** evidencia del bundle alcanza un contador: `prior_errors` y
`prior_clients` quedan vacíos y la elisión se lee explícitamente en el payload.

Además, `root_visibility_complete` pasa a construirse **solo desde la ejecución actual**:

```python
current_run_unreadable = [key for key, record in pid_records.items()
                          if record.get("stat", {}).get("status") != "OK"
                          or record.get("fd_scan", {}).get("status") != "OK"]
root_visibility_complete = (root_fd_error_count == 0
                            and not current_run_unreadable
                            and len(unresolved_prior) == 0)
```

La contaminación queda bloqueada en las dos direcciones: un bundle ajeno no puede **bajar** una
cobertura, y los errores de la ejecución actual **sí** la bajan (`T31`).

### Evidencia rechazada nunca es «cero clientes»

`new_gpu_clients` pasa a ser la cadena `"NOT_AVAILABLE"` cuando no hay padre admisible, en lugar
de una lista vacía que se leería como «cero clientes nuevos». El recuento en el payload sigue
siendo `"NOT_AVAILABLE"`, no `0`. Mismo tratamiento que MED-1 ya aplicaba al storage.

### Verificado contra el bundle real

```
parent_host='lex-luthor'  current_host='kalm'
PARENT_BUNDLE_IDENTITY    : HOST_MISMATCH
PRIOR_EVIDENCE_ADMISSIBLE : False
PRIOR_EVIDENCE_STATUS     : REJECTED_HOST_MISMATCH
```

## 3. Tests

| Suite | Resultado |
|---|---|
| `test_r1_defects.py` (nuevo, T17–T34) | **23 OK** |
| `test_privileged_read_collector.py` | **43 OK** |
| `test_collector_failure_modes.py` | **35 OK** |
| `test_med_review_classifications.py` | **26 OK** |
| `test_c1_isolation_automator.py` | **54 OK**, skipped=1 |
| **Total** | **181 OK, 0 fallos** |

**Tres tests existentes fallaron** al cambiar el diseño y los tres merecían fallar:

1. El allowlist de read-only detectó `re.finditer` como método no clasificado → clasificado.
2. `test_realpath_is_not_used_as_existence_proof` afirmaba que `_bdf_from_realpath` era un
   extractor puro llamado solo desde `resolve_node_device`. Ese diseño ya no existe → reescrito
   para `resolve_pci_device_dir`, y ahora **prohibe explícitamente** `BDF_RE.search()`.
3. `test_the_shared_input_is_defined_once_and_is_whole_system` citaba la expresión literal de
   `root_visibility_complete` → actualizada a la nueva.

**Cuatro defectos míos en `test_r1_defects.py`**, todos de fixture: los directorios PCI se
creaban como hermanos en vez de anidados; rutas que no incluían el puente; symlinks relativos
calculados contra el padre simbólico en vez del real (sysfs resuelve desde la ubicación real);
y `T23` que por eso producía `DIRECTION_DISAGREEMENT` en vez de ambigüedad real. Ninguno era
defecto del collector.

## 4. Revisión final obligatoria

```
BRIDGE_PATH_TEST=PASS                      (T19, reproduce la ruta exacta del aborto)
ENDPOINT_BDF_EXTRACTION=0000:01:00.0       (nunca 0000:00:01.0; T18, T20, T24, T25)
PARENT_HOST_CONTAMINATION=BLOCKED          (T27, T28, T28b, T29, T32)
CURRENT_RUN_EVIDENCE_ISOLATED=YES          (T30, T31, T34)
OLD_BUNDLE_CANNOT_AFFECT_CURRENT_OWNERSHIP=YES  (T29, T32)
FAIL_CLOSED=YES                            (T21, T22, T22b, T23; abort sin recolectar)
```

## 5. Auditoría AST

```
mutating calls (excl. str.replace) : NONE
str.replace                        : 3  (NUL de cmdline, prefijo /dev/dri)
shell=True                         : 0
os.environ                         : 0
sudo as an executed command        : NONE
'sudo' occurrences                 : 1  (clave JSON del payload, no un comando)
subprocess.run                     : 1  (solo el wrapper auditado)
'with' open modes                  : {'rb'}
imports                            : sin subsistemas mutantes
```

Sin escrituras, sin `sudo` ejecutable desde código, sin `os.environ`, sin cambios de sistema.

## 6. Procedencia

```
HASH_BEFORE  = f0a2ac0b6b465486ccacff6e7ea4278683dd7aa3dbd5b0fad92ff9e783cb58e5
HASH_AFTER   = <registrado en el L1 de esta fase>
HEAD         = c6146788e0d4fb12d9b0ec1209fa2840692de0c5   (sin commit)
STAGED       = 360 rutas                                    (índice, sin tocar)
PROVENANCE   = GIT_INDEX_STAGED_NOT_IN_HEAD
```

`41fee794` sigue siendo el hash del collector previo a la corrección HIGH/MED, y
`a2cf80c7` el previo a esta corrección DEFECT. Ningún hash histórico reescrito.

## 7. Lo que sigue abierto

- **MED-2** `NON_BLOCKING_LIMITATION` — el motivo de fallo de namespaces se colapsa a
  `UNAVAILABLE`; la dirección peligrosa (lectura denegada contada como cubierta) está cerrada.
  - **Anotación posterior (2026-09-26). No altera este veredicto.** El veredicto histórico
    sigue siendo `NON_BLOCKING_LIMITATION` y su rationale sigue siendo correcto:
    `*_namespace_complete` continúa siendo `ok == total` y una lectura denegada nunca cuenta
    como cubierta. Lo que ocurrió después es que `AGENTS.md` V3 (`6fe40b2`) introdujo dos
    reglas que el texto pre-V3 (`54b3ea8`, con 0 ocurrencias de ambas) no contiene: la regla de
    *swallowed error* (`AGENTS.md:76`) y *"a name is not a measurement"* (`:40`). Bajo esas
    reglas surge un gap metodológico distinto del veredicto histórico: `user_namespace_denied`
    afirmaba una causa de permiso que un PID desaparecido no demuestra.
    El gap posterior, la corrección implementada y la verificación actual (suite 296/296, 5/5
    mutaciones detectadas, `root_coverage` de 29 a 31 claves) están documentados en
    `01-AUDITORIA/R1-NAMESPACE-ERROR-ATTRIBUTION-20260926.md`. Ese registro **no** reclasifica
    MED-2, **no** cierra R1 y **no** afirma que `user_namespaces_covered` esté resuelto: no se
    ha ejecutado ningún re-barrido privilegiado tras la corrección.
- **MED-3** `NON_BLOCKING_LIMITATION` — `card_node_complete` y `render_node_complete` comparten
  `root_visibility_complete`. Sound por entelación, pero es una dependencia conceptual.
- **MED-4** `NON_BLOCKING_LIMITATION` — tope de 4 MiB sin marca de truncado; `maps` no entra en
  ninguna fila de la matriz.
- **LOW-1..4** de la revisión independiente, y 9 ramas de aborto sin test.
- `sudo_invoked: True` hardcodeado en el payload y `"sudo -A python3 …"` en la descripción del
  comando G-02: describen la invocación prevista, no una acción.

`R1_SAFE_TO_AUTHORIZE=YES` significa que los dos defectos que detuvieron R1 están corregidos y
probados. **No significa que R1 deba ejecutarse**: la autorización sigue siendo tuya, y la
próxima ejecución courtierá con un padre rechazado, lo que deja
`additional_gpu_clients` como `NOT_AVAILABLE` por diseño.

```
OWNERSHIP=PARTIAL   BLK_01=NOT_CLOSED   G1=OPEN
```
