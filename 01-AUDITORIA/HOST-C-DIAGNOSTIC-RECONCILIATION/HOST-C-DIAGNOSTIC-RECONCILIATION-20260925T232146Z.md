# HOST-C DIAGNOSTIC RECONCILIATION — 20260925T232146Z

> Read-only. Sin sudo, sin instalaciones, sin escrituras. Ningun documento previo
> editado ni borrado. Este registro **suplementa** evidencia, no la sustituye.

```text
HOST_SCOPE=HOST-C   HOST_SCOPE_BASIS=DECLARED
KERNEL_RUNNING=7.1.3-200.nobara.fc44.x86_64
```

## A — Procedencia real de RADV

**`NEW_CLASSIFICATION`:** DRIVER_PROVENANCE=OBSERVED ; PACKAGE_PRESENT

### Cadena de evidencia (7 pasos, todos de lectura)

| # | Consulta | Resultado |
|---|---|---|
| 1 | `ls /usr/share/vulkan/icd.d/` | 24 ICD manifests incl. radeon_icd.x86_64.json (mtime 2026-09-16 21:00) |
| 2 | `cat radeon_icd.x86_64.json` | library_path=/usr/lib64/libvulkan_radeon.so, api_version=1.4.354, library_arch=64 |
| 3 | `ls -l /usr/lib64/libvulkan_radeon.so` | EXISTS, 19378152 bytes, mtime 2026-09-16 21:00 (same install event as the manifest) |
| 4 | `rpm -qf /usr/share/vulkan/icd.d/radeon_icd.x86_64.json` | mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64 |
| 5 | `rpm -ql mesa-vulkan-drivers-freeworld | grep radeon` | ships BOTH /usr/lib64/libvulkan_radeon.so AND /usr/share/vulkan/icd.d/radeon_icd.x86_64.json |
| 6 | `rpm -q mesa-vulkan-drivers` | NOT installed (confirmed) |
| 7 | `rpm -qa | grep -iE 'vulkan|mesa'` | mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.{x86_64,i686} present; no other vulkan driver package |

### Resolucion

```text
PROVENANCE_OF_RADV=`mesa-vulkan-drivers-freeworld`
RADV_PACKAGE=`mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64 (+ .i686)`
RADV_ICD=`/usr/share/vulkan/icd.d/radeon_icd.x86_64.json`
RADV_LIBRARY=`/usr/lib64/libvulkan_radeon.so`
RADV_VERSION=`Mesa 26.2.3 (icd api_version 1.4.354)`
RADV_RUNTIME=`OBSERVED`
PACKAGE_PRESENT=`OBSERVED`
DRIVER_PRESENT=`OBSERVED`
DRIVER_OPERATIONAL=`OBSERVED`
DRIVER_PROVENANCE=`OBSERVED`
```

### No habia contradiccion: era un fallo de nombre

There was no contradiction. mesa-vulkan-drivers (the name queried) and mesa-vulkan-drivers-freeworld (the package that actually ships RADV) are different packages. Nobara ships the freeworld variant. The validator's package list simply did not include the freeworld name, so the field read None while the driver was installed and working.

### Defecto del validador (A)

| Campo | Valor |
|---|---|
| `packages['mesa-vulkan-drivers']` | `None` |
| Realidad | `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64` |
| Clasificacion | **`DOCUMENTED_TOOL_DEFECT`** |
| Causa | hardcoded package list omits mesa-vulkan-drivers-freeworld; rpm -q is unprefixed, so unknown names are never enumerated |
| Modificado | `tools/validate_rx550_final.py was NOT modified in this stage` |

**No se derivo un token de otro:** DRIVER_OPERATIONAL was NOT inferred from PACKAGE_PRESENT. It is OBSERVED from BLK-02 vulkan_radv_icd device_id=0x699f, and independently corroborated here by the ICD->library->rpm chain being intact on disk.

## B — Identificacion de kernel

**`NEW_CLASSIFICATION`:** `KERNEL_QUERY_BEHAVIOUR=UNAMBIGUOUSLY_EXPLAINED`

```text
KERNEL_RUNNING=`7.1.3-200.nobara.fc44.x86_64`
KERNEL_INSTALLED=
  - `kernel-core-6.18.2-200.nobara.fc43.x86_64`
  - `kernel-core-7.1.3-200.nobara.fc44.x86_64`
VALIDATOR_FIELD=`packages['kernel-core'] = 6.18.2-200.nobara.fc43.x86_64`   <- enganoso
CLASSIFICATION=`DOCUMENTED_TOOL_DEFECT`
```

### `KERNEL_QUERY_BEHAVIOUR`

rpm -q kernel-core returns ALL installed kernel-core packages. With two kernels installed there is no correlation between the first returned line and the running kernel. rpm returns them in its own order; the validator then keeps the first '.x86_64' match, which was the fc43 one.

### Evidencia

| Consulta | Resultado |
|---|---|
| `uname -r` | 7.1.3-200.nobara.fc44.x86_64 |
| `cat /proc/version` | Linux version 7.1.3-200.nobara.fc44.x86_64 (mockbuild@559670082b9946b78305ee85a5345150) |
| `cat /proc/sys/kernel/osrelease` | 7.1.3-200.nobara.fc44.x86_64 |
| `rpm -q kernel-core` | TWO lines: fc43 then fc44 |
| `rpm -qf /boot/vmlinuz-7.1.3-200.nobara.fc44.x86_64` | kernel-core-7.1.3-200.nobara.fc44.x86_64  <- unambiguous |
| `ls -l /boot/vmlinuz*` | 3 images: 6.18.2 fc43 (dic 2025), 7.1.3 fc44 (jul 3), 0-rescue |

### Fuente recomendada para una correccion futura

| Uso | Fuente | Motivo |
|---|---|---|
| Primaria | **`uname -r  (or /proc/sys/kernel/osrelease)`** | authoritative for the RUNNING kernel; no package query needed |
| Corroboracion | `rpm -qf /boot/vmlinuz-7.1.3-200.nobara.fc44.x86_64  -> package owning the running image` | — |
| Antipatron | `rpm -q kernel-core  -> ambiguous when >1 kernel installed; must never be presented as the running kernel` | — |

## Reconciliacion de evidencia previa

### RT-0016 (ROUTING-LOG.jsonl, PRESERVED)

| Campo | Valor |
|---|---|
| `OLD_CLASSIFICATION` | DRIVER_OPERATIONAL=NOT_AVAILABLE for RADV on HOST-C |
| `NEW_CLASSIFICATION` | **DRIVER_OPERATIONAL=OBSERVED** |
| `NEW_EVIDENCE` | BLK-02 FINAL-VALIDATION-20260925T231128Z renderers.vulkan_radv_icd device_id=0x699f; plus this stage's ICD->library->rpm chain |
| `REASON` | RT-0016 correctly recorded that mesa-vulkan-drivers was absent and that this prevented asserting DRIVER_OPERATIONAL. The missing inference was that the RADV driver ships in mesa-vulkan-drivers-freeworld instead. Once provenance is established, PACKAGE_PRESENT and DRIVER_OPERATIONAL are both OBSERVED. RT-0016 is NOT deleted or rewritten. |

### OWNERSHIP-AUDIT-HOST-C-20260925T231635Z (PRESERVED)

| Campo | Valor |
|---|---|
| `OLD_CLASSIFICATION` | OWNERSHIP=PARTIAL ; OWNERSHIP_CARD1=NOT_AVAILABLE ; OWNERSHIP_RENDERD129=NOT_AVAILABLE |
| `NEW_CLASSIFICATION` | **UNCHANGED** |
| `NEW_EVIDENCE` | none in this stage |
| `REASON` | This stage did not re-run ownership and gathered no new FD evidence. PARTIAL is preserved. Absence of Kalm/autopilot is not ownership FULL. |

### PATCH-SOURCES.md section 3 (PRESERVED, HISTORICAL note retained)

| Campo | Valor |
|---|---|
| `OLD_CLASSIFICATION` | mesa-vulkan-drivers: no instalado |
| `NEW_CLASSIFICATION` | **PARTIALLY SUPERSEDED: the fact stays true, its implication was wrong** |
| `NEW_EVIDENCE` | rpm -qf radeon_icd.x86_64.json -> mesa-vulkan-drivers-freeworld |
| `REASON` | The literal statement 'mesa-vulkan-drivers is not installed' remains OBSERVED and correct. What changes is that it was read as 'Vulkan drivers absent'. They are present under a different package name. The historical text is not edited; this reconciliation supersedes its interpretation only. |

## Ownership — conservado sin cambios

```text
OWNERSHIP=`PARTIAL`
OWNERSHIP_CARD1=`NOT_AVAILABLE`
OWNERSHIP_RENDERD129=`NOT_AVAILABLE`
BLK_01=`NOT_CLOSED`
G1=`OPEN`
criterion_evaluation_root_namespaces=`FAIL (199 root-owned PIDs with unreadable /proc/PID/fd)`
```

Esta etapa **no** re-ejecuto la auditoria de ownership y **no** aporto evidencia de FDs.
La ausencia de Kalm y `system-autopilot` no se convierte en ownership FULL.

## Lo que NO se hizo

- No package installed, removed or updated
- tools/validate_rx550_final.py NOT modified
- ROUTING-LOG.jsonl NOT modified (no new query required documentation lookups)
- No prior capture, audit or historical document edited or deleted
- No sudo, no service change, no sysfs write, no process touched
- No C1, no benchmark, no patch applied

## Garantias

```text
WRITES_TO_SYSTEM=False
PACKAGE_INSTALLS=0
SERVICE_CHANGES=0
SYSFS_WRITES=0
PROCESSES_TERMINATED=0
PROCESSES_SUSPENDED=0
PATCHES_APPLIED=0
BENCHMARKS_EXECUTED=False
C1_EXECUTED=FALSE
```
