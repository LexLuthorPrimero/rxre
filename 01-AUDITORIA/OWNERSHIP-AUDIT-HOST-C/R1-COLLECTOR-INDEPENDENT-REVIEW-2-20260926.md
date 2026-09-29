# R1 COLLECTOR — INDEPENDENT REVIEW #2 (post DEFECT-01 / DEFECT-02)

```
REVIEW_STATUS=COMPLETE
REVIEW_MODE=READ_ONLY_NO_MODIFICATION
COLLECTOR_REVIEWED=0985ad03afffa848301200c464b85e40e038964e6f3e9674f5a730bc3a6d5849
CRITICAL_FINDINGS=0
HIGH_FINDINGS=0
MEDIUM_FINDINGS=5
LOW_FINDINGS=3
R1_SAFE_TO_AUTHORIZE=YES
```

**Fecha:** 2026-09-26 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`

**Ningún archivo modificado.** El collector, los tests y el repo quedan byte-idénticos.
Las pruebas de esta revisión son sondas en `/tmp/opencode` sobre árboles sintéticos, no
ediciones. No se ejecutó R1, ni `sudo`, ni C1/R2/R3.

**Método:** no se aceptó ninguna propiedad por tener un test que la afirme. Cada una se
volvió a derivar del código o se sondeó con una entrada que mis tests no construyen.

---

## 1. Lo que se verificó con evidencia independiente

### DEFECT-01 — el endpoint se identifica estructuralmente

`BDF_RE.search(` aparece **0 veces** en el collector. La heurística de primera coincidencia
desapareció por completo. Quedan un `finditer` (solo diagnóstico, alimenta
`bdf_components_in_path`) y un `fullmatch` (identidad).

Verificado en el host real, read-only:

```
/sys/class/drm/card1/device -> /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0
bdf_components_in_path : ['0000:00:01.0', '0000:01:00.0']   <- el puente se ve y no se usa
device_dir_bdf         : 0000:01:00.0                        <- el endpoint
GPU_IDENTITY_STATUS    : PROVEN
```

Sondeos que mis 181 tests **no** construyen:

| Sonda | Resultado | Veredicto |
|---|---|---|
| symlink apunta a un **puente real** | `NOT_PROVEN`, `PCI_IDENTITY_MISMATCH_AT_NODE` | fail-closed |
| symlink **encadenado** (`device → hop → endpoint`) | `device_dir_bdf=0000:01:00.0`, `PROVEN` | correcto |
| symlink roto | `DEVICE_TARGET_ABSENT` | fail-closed |
| destino existe pero es **fichero** | `DEVICE_TARGET_NOT_A_DIRECTORY` | fail-closed |
| card y render a **endpoints distintos** | `DIRECTION_DISAGREEMENT`, `devices=set()` | fail-closed |
| **dos GPUs AMD** | `PROVEN` para la pedida, `amdgpu_device_bdfs` con 2 → debugfs `NOT_AVAILABLE` | correcto |
| endpoint con driver `radeonsi` | `PCI_IDENTITY_MISMATCH_AT_NODE`, mismatch nombrado | fail-closed |
| dominio PCI distinto (`0001:03:00.0`) | `BDF_RE` lo reconoce pero queda `DIFFERENT_BDF` | fail-closed |

**Ningún camino selecciona una GPU equivocada.** En todos los casos o resuelve el endpoint
correcto o se niega.

### DEFECT-02 — el bundle padre no puede crear ni eliminar clientes

`gpu_clients` se construye **solo** desde el barrido actual de `/proc`. `prior_keys` filtra
únicamente el *diferencial* `new_gpu_clients`. Un bundle puede, en el mejor de los casos,
alterar un diferencial — nunca la lista de clientes.

```
A same host+kernel        -> MATCH / ACCEPTED                    admissible=True
B otro host               -> HOST_MISMATCH / REJECTED_HOST       admissible=False
C mismo host, otro kernel -> KERNEL_MISMATCH / REJECTED_KERNEL   admissible=False
E ausente (None)          -> NOT_AVAILABLE / REJECTED            admissible=False
F vacío                   -> NOT_AVAILABLE / REJECTED            admissible=False
H metadata None           -> NOT_AVAILABLE / REJECTED            admissible=False
```

`root_visibility_complete` se construye solo de la ejecución actual:
`root_fd_error_count == 0 and not current_run_unreadable and not unresolved_prior`.

### Semántica NOT_AVAILABLE

Los tres sitios que cuentan clientes contra el padre están guardados:

```python
len(new_gpu_clients) if gpu_delta_status == "COMPUTED" else "NOT_AVAILABLE"
```

Verificado en los tres sitios (L2236, L2317, L2452). `storage_clients` sigue el patrón de
MED-1: `active_storage = None` cuando la identidad no está probada. Ningún `NOT_AVAILABLE` se
convierte en `[]`, `0` ni `False`.

### Matriz de 11 condiciones

| # | Condición | Fuente | PASS | FAIL | UNKNOWN/NE | ¿Puede dar FULL por error? |
|---:|---|---|---|---|---|---|
| 1 | `card_node_complete` | `gpu_proven and coverage[card_complete]` | identidad probada **y** `root_visibility_complete` | identidad probada, cobertura incompleta | `NOT_EVALUATED` si identidad no probada | No |
| 2 | `render_node_complete` | ídem con `render_complete` | ídem | ídem | ídem | No |
| 3 | `user_namespaces_covered` | `user_namespace_ok == user_namespace_total and total>0` | población user completa | alguna denegada | — | No |
| 4 | `root_namespaces_covered` | ídem sobre población root | ídem | ídem | — | No |
| 5 | `drm_fds_enumerated` | `gpu_proven and fd_error_count == 0` | cero errores de FD | ≥1 error | — | No |
| 6 | `writers_resolved` | `OWNERSHIP_EXTERNAL_ROWS` | **imposible** | — | `NOT_EVALUATED` R2 | No |
| 7 | `agents_absent` | `active_agents == 0` | cero servicios activos | ≥1 | — | No |
| 8 | `pm_observed` | `pm_status == "READ"` | leído | — | `UNKNOWN` si omitido | No |
| 9 | `btrfs_identity` | `btrfs_status` (mountinfo actual) | **nunca PASS** | — | `NOT_APPLICABLE` / `UNKNOWN` | No |
| 10 | `clients_pasid_attributable` | debugfs | `PROVEN`/`OBSERVED` | — | `NOT_AVAILABLE → UNKNOWN` | No |
| 11 | `guard_and_restore` | `OWNERSHIP_EXTERNAL_ROWS` | **imposible** | — | `NOT_EVALUATED` R3 | No |

Agregado: `FULL` exige `states ⊆ {PASS, NOT_APPLICABLE}`. Las filas 6 y 11 son
`NOT_EVALUATED` incondicionalmente, así que **`FULL` es inalcanzable** desde este collector.
Ningún `UNKNOWN`, `NOT_AVAILABLE` ni `NOT_EVALUATED` se convierte en `PASS` en ninguna fila.

### Autocontraminiación

Orden verificado: `resolve_gpu_identity()` (1714, solo `readlink`/`exists`/`isdir`, sin
aperturas) → barrido `/proc` (1879) → `lsof` (1903) → `fuser` (1904) → `pm_snapshot` (1970).
El snapshot de clientes precede cualquier operación que abra los nodos. Ninguna operación
previa puede crear una referencia DRM.

### Read-only

`mutating calls = NONE` · `shell=True = 0` · `os.environ = 0` · `sudo` como comando
ejecutable = ninguno · `subprocess.run = 1` (solo el wrapper) · `with` solo `open("rb")` ·
imports sin subsistemas mutantes. Sin escrituras, sin cambios de sistema.

---

## 2. MEDIUM

### MED-1 · Un puente PCI **sí** tiene `vendor`/`device`; mi check #5 no lo distingue

En este host:

```
0000:00:01.0  vendor=0x8086  device=0x0c01  class=0x060400   <- puente, tiene vendor/device
0000:01:00.0  vendor=0x1002  device=0x699f  class=0x030000   <- endpoint
```

En `R1-DEFECT-FIX-RECORD` afirmé que el check #5 «prueba que ese directorio es un dispositivo y
no un puente o un bus». **Esa afirmación es falsa**: los puentes son dispositivos PCI y
exponen ambos atributos. Lo que realmente excluye un puente es el check de `class`
(`0x030000` frente a `0x060400`), que vive en `resolve_node_device`, no en
`resolve_pci_device_dir`.

La protección es real —la sonda con un puente real devuelve `NOT_PROVEN`— pero la garantía
documentada era más fuerte que la implementada. `class` es la única barrera contra un puente,
y está en otra función.

### MED-2 · Ningún test cubre el caso realista de MED-1

`T22b` construye un directorio con forma de BDF **sin** `vendor`/`device` y espera
`DEVICE_DIR_LACKS_PCI_VENDOR_DEVICE`. Ese directorio **no puede existir** en sysfs real:
todo dispositivo PCI, puente incluido, tiene ambos atributos. El test prueba un escenario
imposible mientras el realista —symlink a un puente con atributos válidos pero `class=0x06xx`—
queda sin cubrir. Lo verifiqué por sonda: está cerrado, pero por accidente del fixture, no por
prueba.

### MED-3 · `assess_parent_bundle` lanza excepción ante metadata corrupta

`{"metadata": "not-a-dict"}` → `AttributeError: 'str' object has no attribute 'get'`. La
excepción sube por `main()`; el envoltorio `__main__` la captura y emite
`collector_error` con `OWNERSHIP=PARTIAL`. Es fail-closed en efecto, pero convierte un
**rechazo clasificable** en un crash. Lo pedido era clasificar como `UNKNOWN` o
`NOT_AVAILABLE`. Un bundle no vacío que no sea dict falla igual. Además el bundle G
(`ownership` no-dict) se **admite** como `MATCH` y luego revienta al leer `ownership`.

### MED-4 · Un bundle sin kernel declarado se admite solo por host

`{"metadata": {"host": "kalm"}}` → `MATCH / ACCEPTED_SAME_HOST_AND_KERNEL`. El chequeo de
kernel se salta con `if observed_kernel and ...`. Se admite evidencia cuyo contexto de boot
no puede verificarse. El impacto real es bajo porque `root_visibility_complete` ya no depende
del padre, pero el diferencial se calcularía contra evidencia no verificable.

### MED-5 · `SUDO_INVOKED` es una afirmación no observada

`metadata.sudo_invoked: True` y `sudo.SUDO_INVOKED: "YES"` están **hardcodeados**.
`os.geteuid()` no se lee en ningún punto. Una ejecución sin privilegio produciría un
artefacto que afirma haberse elevando a root. En un proyecto cuya disciplina central es no
afirmar lo no observado, esto es un defecto de integridad de la evidencia. No afecta a
ninguna condición de ownership.

---

## 3. LOW

- **LOW-1 · `PARENT.get("btrfs", {})` no está gated.** Es la única lectura del padre que
  sobrevive al filtro de admisibilidad, y coloca estado Btrfs de HOST-A en el payload bajo
  `btrfs_observation.parent_state`. Verificado que la matriz **no** lo lee (solo
  `btrfs_status`, derivado del mountinfo actual), así que es inerte. Pero la etiqueta
  `parent_state` no registra que fue rechazado.
- **LOW-2 · `current_run_unreadable` confunde PID desaparecido con visibilidad denegada.** Un
  proceso que muere entre `proc_pids()` y `proc_meta()` produce `stat.status != "OK"`, igual
  que un `PermissionError`. En un escritorio activo con procesos efímeros es probable que
  dispare, y degrada `card`/`render`/root coverage a `FAIL` por un motivo que no es de
  aislamiento. Fail-closed pero semánticamente incorrecto y no determinista. No puede
  producir `FULL`.
- **LOW-3 · 11 ramas de abort sin test:** `PCI_DRM_ENUMERATION_ABSENT`, `DRM_CLASS_ABSENT`,
  `DEVICE_LINK_UNREADABLE`, `DEVICE_TARGET_NOT_A_DIRECTORY`, `DEBUGFS_AMBIGUOUS_MULTIPLE_AMDGPU`,
  `DEBUGFS_UNREADABLE`, `RENDER_MINOR_NOT_DERIVED`, `ROOT_MOUNTPOINT_NOT_FOUND`,
  `BLOCK_DEVICE_ABSENT_IN_SYSFS`, `BLOCK_SYSFS_REALPATH_UNRECOGNISED`, y el motivo de exclusión
  `DIFFERENT_BDF`. Dos de ellas las verifiqué por sonda en esta revisión y están cerradas.

---

## 4. Veredicto

```
R1_SAFE_TO_AUTHORIZE=YES
```

**Ningún hallazgo puede producir `OWNERSHIP=FULL` falso, ni cobertura root/card/render falsa,
ni atribución incorrecta de clientes, ni ownership de storage falso, ni un `FULL` basado en
`UNKNOWN`/`NOT_PROVEN`/`NOT_EVALUATED`.**

Los cinco MEDIUM son: una afirmación de diseño que era más fuerte que el código (MED-1, con la
protección real intacta), un test que ejercita un escenario imposible en vez del real (MED-2),
robustez y clasificabilidad ante un bundle corrupto (MED-3, fail-closed), admisión de contexto
no verificable (MED-4, sin efecto en coverage) y una afirmación `SUDO_INVOKED` no observada
(MED-5, sin efecto en veredictos). Ninguno cambia un veredicto.

Los tres LOW son diagnostics y cobertura.

`OWNERSHIP=FULL` sigue siendo inalcanzable por construcción: las filas R2 y R3 son
`NOT_EVALUATED` incondicionalmente. Corregir MED-1..MED-5 es recomendable antes de la
próxima ejecución de R1, pero no bloquea la autorización.

```
R1_EXECUTED=NO   PRIVILEGED_EXECUTION=NO   SUDO_INVOKED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  SERVICE_CHANGES=0  SYSFS_WRITES=0
PROCESS_TERMINATED=0  PROCESS_SUSPENDED=0

OWNERSHIP=PARTIAL   BLK_01=NOT_CLOSED   G1=OPEN
```
