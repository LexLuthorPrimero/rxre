# R1 EXECUTION RECORD — ABORTED AT IDENTITY RESOLUTION

```
R1_EXECUTED=YES_ATTEMPTED_ABORTED
RUN_ID=R1-20260926T000649Z
R1_RESULT=ABORTED_IDENTITY_NOT_PROVEN
R1_EVIDENCE_COLLECTED=NO
OWNERSHIP=PARTIAL
BLK_01=NOT_CLOSED
G1=OPEN
```

**Fecha:** 2026-09-26 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Autorización:**Execution de R1 privilegiada read-only, expresamente concedida.

| | |
|---|---|
| `RUN_ID` | `R1-20260926T000649Z` |
| `START` | `2026-09-26T00:06:49.442Z` |
| `END` | `2026-09-26T00:07:00.312Z` |
| `PRIVILEGED_EXECUTION` | `YES` (euid=0 verificado en pre-flight) |
| `SUDO_INVOKED` | `YES` — `SUDO_ASKPASS=/usr/bin/ksshaskpass` |
| `COLLECTOR_HASH` | `f0a2ac0b6b465486ccacff6e7ea4278683dd7aa3dbd5b0fad92ff9e783cb58e5` |
| `COLLECTOR_PROVENANCE` | `GIT_INDEX_STAGED_NOT_IN_HEAD` |
| Artefacto R1 | `R1-20260926T000649Z.json` — `fe2847b9fdac4ba27cd4366a253f3b25cc05d17f97fc9abf53d4fd1edb858384` |
| Bundle padre | `C1-PREFLIGHT-20260925T060029Z.json` — `f8664c0ab61e5697b80ddb6df43d1cd8…` |

Duración real: **10,9 s**. El collectorvkçalanza aborta en la etapa 3 de 11, antes de
cualquier recolección. La ventana de 120 s nunca comenzó.

---

## 1. Lo que el collector decidió

```json
"COLLECTOR_STATUS": "ABORTED",
"ABORT_REASON":    "IDENTITY_NOT_PROVEN",
"ABORT_STAGE":     "IDENTITY_STAGE_DRM",
"ABORT_DETAIL":    "DIRECTION_DISAGREEMENT",
"ownership_evidence_collected": false
```

El abort payload **no contiene clave `ownership`**, por diseño: un documento de ownership
vacío sería indistinguible de una observación de «cero clientes».

## 2. Causa raíz — defecto del collector, `DEFECT-01`

`GPU_BDF` mal extraído por ambiligüedad de texto de ruta.

```
/sys/class/drm/card1 -> ../../devices/pci0000:00/0000:00:01.0/0000:01:00.0/drm/card1
/sys/class/drm/card1/device -> /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0
```

En HOST-C la RX550 está **detrás de un puente PCI**, así que el realpath contiene **dos**
BDF: `0000:00:01.0` (el puente) y `0000:01:00.0` (el endpoint).

`_bdf_from_realpath()` usa `BDF_RE.search()`, que devuelve la **primera** coincidencia. Tomó
el puente:

| Nodo | BDF extraído | BDF real | Enlace `device` | Driver |
|---|---|---|---|---|
| `card1` | `0000:00:01.0` | `0000:01:00.0` | `PROVEN` | `amdgpu` |
| `renderD129` | `0000:00:01.0` | `0000:01:00.0` | `PROVEN` | `amdgpu` |
| `card0` | `0000:00:02.0` | `0000:00:02.0` | `PCI_IDENTITY_MISMATCH_AT_NODE` | `i915` |
| `renderD128` | `0000:00:02.0` | `0000:00:02.0` | `PCI_IDENTITY_MISMATCH_AT_NODE` | `i915` |

El destino del enlace era **correcto** — la re-verificación de identidad en el destino pasó
(`vendor=0x1002`, `device=0x699f`, `class=0x030000`, `driver=amdgpu`). El fallo está solo en
la **extracción textual del BDF** para la comparación.

Consecuencia: `card1` y `renderD129` se clasificaron `DIFFERENT_BDF`, las listas inversas
quedaron vacías, y las dos direcciones discrepan → `DIRECTION_DISAGREEMENT`.

**La iGPU no se vio afectada** porque `0000:00:02.0` cuelga directamente de `0000:00` sin
segmento de puente, así que la primera coincidencia daba por casualidad el BDF correcto. El
defecto solo se manifiesta con un puente en el caminho.

### 2.1 La propiedad de seguridad se mantuvo

El collector **no adoptó una GPU equivocada**. Se negó a identifiers. `card1` no llegó a
`GPU_CARD_NODE`, `devices` quedó `set()`, y no se recolectó nada. El fallo es
**sobre-estricto, nunca permisivo**. No hay atribución falsa que corregir; hay evidencia que
no pudoogradarse.

### 2.2 Por qué mis propios tests no lo cazaron

HIGH-1 corrigió la prueba de *existencia* del enlace `device`, pero la **comparación** de BDF
siguió usando extracción de texto. Todos mis árboles sintéticos colocaban el dispositivo
directamente sobre `pci0000:00/0000:01:00.0`, **sin segmento de puente**, porque ese es el
camino que la iGPU sí tiene. El hueco estaba en el fixture, no en el criterio.

Es la misma clase de problema que HIGH-1 —texto de ruta como evidencia— en su segunda forma.
HIGH-1 probó que el enlace *existe*; nadie probó que el BDF *extraído* sea el del dispositivo.

### 2.3 Corrección necesaria (NO aplicada)

El BDF exacto es el **nombre del directorio destino**: sysfs nombra los directorios de
dispositivo PCI por su BDF. `os.path.basename(os.path.realpath(link))` da `0000:01:00.0` sin
ambigüedad, o equivalentemente la última coincidencia del regex. Reemplazar la extracción por
primera-coincidencia en `resolve_node_device()` y añadir un test con puente PCI.

**No parcheado**, por instrucción expresa. R1 queda detenido hasta autorización de corrección.

## 3. Segundo defecto, independiente — `DEFECT-02`

El bundle padre pertenece a **otro host**:

| | Bundle padre | Host R1 |
|---|---|---|
| host | `lex-luthor` | `kalm` |
| kernel | `7.2.6-201.nobara.fc44.x86_64` | `7.1.3-200.nobara.fc44.x86_64` |
| identidad | HOST-A (disco viejo) | HOST-C (vivo) |

El collector usa `ownership.fd_visibility_errors` (363 PIDs) y `ownership.clients` (2) del
padre para construir `prior_pids` y `unresolved_prior`, y **nunca compara la identidad del host
del padre con la del host actual**. Aun con DEFECT-01 corregido, esos 363 PIDs de HOST-A no
existirían aquí → `unresolved_prior` no vacío → `root_visibility_complete = False` →
`card_node_complete` y `render_node_complete` en `FAIL`.

Es decir: **hubo un segundo defecto que habría producido un FAIL espurio** por entrada
heredada de otro host..fail-closed, pero por la razón equivocada. Clasificación:
`PRIOR_BUNDLE_HOST_IDENTITY_NOT_COMPARED`.

## 4. Campos solicitados — todos NO recolectados

Ninguno de estos se ha observado. **Ninguno se reporta como 0 ni como vacío.**

| Campo | Estado | Motivo |
|---|---|---|
| `GPU_IDENTITY` | `PCI=PROVEN` / `DRM=NOT_PROVEN` | `DIRECTION_DISAGREEMENT` (DEFECT-01) |
| `CARD1_CLIENTS` | `NOT_COLLECTED` | aborto en etapa 3 de 11 |
| `RENDERD129_CLIENTS` | `NOT_COLLECTED` | ídem |
| `UNKNOWN_PROCESSES` | `NOT_COLLECTED` | el barrido de `/proc` nunca se ejecutó |
| `ROOT_COVERAGE` | `NOT_COLLECTED` | ídem |
| `NAMESPACE_COVERAGE` | `NOT_COLLECTED` | ídem |
| `KWIN_COVERAGE` | `NOT_COLLECTED` | ídem |
| `STORAGE_IDENTITY` | `NOT_COLLECTED` | se resuelve en etapa 4, posterior al aborto |
| `STORAGE_CLIENTS` | `NOT_COLLECTED` | ídem |
| `systemd service state` | `NOT_COLLECTED` | `systemctl_rows()` es posterior al aborto |
| `GPU runtime PM` | `NOT_COLLECTED` | etapa 9 |
| `GPU DPM` | `NOT_COLLECTED` | etapa 9 |
| `power cap` | `NOT_COLLECTED` | etapa 9 |
| `debugfs DRM minor` | `NOT_COLLECTED` | etapa 8 |
| `hwmon` | `NOT_COLLECTED` | requiere identidad probada |
| `proc maps` | `NOT_COLLECTED` | etapa 7 |
| `FD visibility` | `NOT_COLLECTED` | etapa 6 |

## 5. Matriz de 11 condiciones — no evaluable

Ninguna condición se evaluó. **No se infiere `FULL` por ausencia de datos.**

```
CARD1_CLIENTS=NOT_COLLECTED          ROOT_COVERAGE=NOT_COLLECTED
RENDERD129_CLIENTS=NOT_COLLECTED     NAMESPACE_COVERAGE=NOT_COLLECTED
UNKNOWN_PROCESSES=NOT_COLLECTED      KWIN_COVERAGE=NOT_COLLECTED
STORAGE_IDENTITY=NOT_COLLECTED       OWNERSHIP=PARTIAL
BLK_01=NOT_CLOSED                     G1=OPEN
```

`OWNERSHIP` sigue `PARTIAL` porque nunca se evaluó, **no** porque se evaluara y fallara. El
valor por defecto de un agregado no evaluado es el conservador.

## 6. Garantías verificadas

```
SYSTEM_CHANGES=0    GPU_CHANGES=0    SERVICE_CHANGES=0    SYSFS_WRITES=0
PROCESS_TERMINATED=0  PROCESS_SUSPENDED=0  PACKAGE_INSTALLS=0  PATCHES_APPLIED=0
C1_EXECUTED=NO      R2_EXECUTED=NO     R3_EXECUTED=NO      BENCHMARKS_EXECUTED=NO
R1_LEFT_UNMODIFIED=YES  (hash f0a2ac0b… idéntico antes y después)
```

Verificado tras la ejecución: `HEAD` sin cambios, 360 rutas staged sin commit, 0 directorios
runtime C1, los 9 hashes protegidos intactos, `ROUTING-LOG` con 24 eventos.

**Variación normal de PIDs** (281 → 285, y dos `kwin_wayland` hijos con PIDs distintos) es
actividad propia de la sesión de escritorio durante los 11 s de la ejecución, no efecto del
collector: el collector no creo, termino ni envio senales a procesos. `Xwayland` 1923 estable.

## 7. Lo que R1 ha planteado

`OWNERSHIP=FULL` requería demostrar las 11 condiciones. R1 no produjo ninguna. Lo que sí ha
producido es una **identidad PCI verificada** (`0x1002`/`0x699f`/`0x030000`/`amdgpu` en
`0000:01:00.0`) y la demostración de que el enfoque de descubrimiento funciona salvo por la
extracción textual del BDF. `BLK_01` sigue abierto, y ahora con dos defectos concretos y
acotados en lugar de una barrera de acceso.

## 8. Nota sobre el hostname

El host se llama `kalm`. El agente contaminante de HOST-A era `kalm-gpu.service`, que en HOST-C
está `not-found` según la evidencia BLK-02. El nombre del host **no** es evidencia del estado
del servicio y no se usa como tal aquí. `SERVICE_CHANGES=0` y ninguna unidad fue tocada.

---

```
R1_EXECUTED=YES_ATTEMPTED_ABORTED
R1_EVIDENCE_COLLECTED=NO
DEFECT_01=BDF_TEXT_EXTRACTION_AMBIGUOUS_WITH_PCI_BRIDGE
DEFECT_02=PRIOR_BUNDLE_HOST_IDENTITY_NOT_COMPARED
OWNERSHIP=PARTIAL   BLK_01=NOT_CLOSED   G1=OPEN
```
