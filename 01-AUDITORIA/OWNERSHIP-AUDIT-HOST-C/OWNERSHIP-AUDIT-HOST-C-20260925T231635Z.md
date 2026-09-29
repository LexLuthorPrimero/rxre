# OWNERSHIP AUDIT — HOST-C — 20260925T231635Z

> Auditoria **read-only**, sin sudo, sin privilegios elevados. Ningun proceso terminado,
> suspendido o pausado. Cero escrituras a sysfs. Cero cambios de servicio. C1 no ejecutado.

## Identidad

| Campo | Valor |
|---|---|
| `HOST_SCOPE` | **`HOST-C`** |
| `HOST_SCOPE_BASIS` | **`DECLARED`** |
| SO | Nobara Linux 44 (KDE Plasma Desktop Edition) |
| Kernel en ejecucion | `7.1.3-200.nobara.fc44.x86_64` |
| Sesion | `wayland` / `KDE` |
| Agente de captura | uid `1000` (lucas), sin sudo |
| Identidad derivada de | captura BLK-02 `FINAL-VALIDATION-20260925T231128Z` + `uname -r` + `os_release` |

## Metodo y oraculo

Oraculo: **`/proc/<pid>/fd` symlinks + campos `drm-*` de `/proc/<pid>/fdinfo`**.

Comandos usados (todos de lectura):

- `ls /proc | grep -E '^[0-9]+$'`
- `ls /proc/<pid>/fd`
- `readlink /proc/<pid>/fd/<n>`
- `cat /proc/<pid>/fdinfo/<n>`
- `cat /proc/<pid>/status ; cat /proc/<pid>/comm ; cat /proc/<pid>/cgroup`
- `uname -r ; cat /etc/os-release ; id -u ; id -un`
- `ls -l /dev/dri/`

No usados: `fuser (no write; but /proc scan is the project's declared oracle)``, ``lsof (absent on host; /proc scan used instead)``, ``sudo (forbidden by task)``, ``debugfs /sys/kernel/debug/dri/1/clients (requires root)`.

**Limitacion declarada:** only PIDs whose /proc/<pid>/fd is readable to UID 1000 can be enumerated; root-owned and ptrace-protected PIDs are NOT visible.

## Visibilidad — el dato que determina el resultado

| Metrica | Valor |
|---|---|
| PIDs totales | 283 |
| Con `/proc/<pid>/fd` legible | **68** |
| Con `/proc/<pid>/fd` **ilegible** | **215** |
| Ilegibles y propiedad de root | **199** |
| `ptrace_scope` | `0` |
| debugfs clients | `NOT_AVAILABLE (requires root)` |

Ilegibles dentro de la propia sesion de usuario (uid 1000):

- PID 1697 `(sd-pam)` — `FD_UNREADABLE_NO_PRIVILEGE`
- PID 1825 `kwin_wayland` — `FD_UNREADABLE_NO_PRIVILEGE`
- PID 2025 `polkit-kde-auth` — `FD_UNREADABLE_NO_PRIVILEGE`
- PID 2028 `ssh-agent` — `FD_UNREADABLE_NO_PRIVILEGE`
- PID 2259 `fusermount3` — `FD_UNREADABLE_NO_PRIVILEGE`

## Recurso A — `/dev/dri/card1` (RX550, amdgpu, 0000:01:00.0)

Clientes legibles: **1**

| PID | Proceso | UID | PPID | FD | client-id | pdev | pasid | VRAM | GTT |
|---|---|---|---|---|---|---|---|---|---|
| 1923 | `Xwayland` | 1000 | 1825 | 13 | 71 | `0000:01:00.0` | 43 | 0 KiB | 2184 KiB |

**`OWNERSHIP_CARD1=NOT_AVAILABLE`** — un cliente legible no prueba ausencia de otros.

## Recurso B — `/dev/dri/renderD129` (RX550)

Clientes legibles: **0**

**`OWNERSHIP_RENDERD129=NOT_AVAILABLE`** — cero clientes *observados* no equivale a cero
clientes *reales*: el compositor activo tiene `/proc` ilegible. Cero observado != cero actual.

## Contraste — `/dev/dri/renderD128` (Intel HD 4600, NO es la RX550)

PIDs con FDs legibles sobre el nodo Intel: **6**

| PID | Proceso |
|---|---|
| 1910 | `plasma-keyboard` |
| 1923 | `Xwayland` |
| 2003 | `plasmashell` |
| 2191 | `xwaylandvideobr` |
| 2218 | `nobara-welcome` |
| 3424 | `firefox-bin` |

**Hallazgo relevante:** el apilamiento de clientes graficos esta sobre el nodo **Intel**,
no sobre la RX550. La unica RX550 client-visible es `Xwayland` sobre card1. Esto es
un cambio real respecto de HOST-A y es consistente con el menor ruido de KWin, pero
**no demuestra ownership**.

## El compositor no es auditable

| Campo | Valor |
|---|---|
| PID | 1825 |
| comm | `kwin_wayland` |
| UID / PPID | 1000 / 1817 |
| cmdline | `/usr/bin/kwin_wayland --wayland-fd 7 --socket wayland-0 --xwayland-fd 8 --xwayland-fd 9 --xwayland-display :0` |
| cgroup | `0::/user.slice/user-1000.slice/user@1000.service/session.slice/plasma-kwin_wayland.service` |
| FDs visibles | **0** |
| `/proc/1825/maps` legible | **False** |
| Motivo | `FD_UNREADABLE_NO_PRIVILEGE` |
| Relevancia | COMPOSITOR_OF_THE_ACTIVE_SESSION; per fdinfo-level DRM client accounting it is the most likely holder of /dev/dri/card1 and /dev/dri/renderD129, but this CANNOT be observed without privilege |
| Clasificacion | **`UNKNOWN`** |

`kwin_wayland` es el compositor de la sesion activa. No se mato, no se detuvo, no se
inspecciono con privilegio. Su conjunto de FDs — y por tanto si mantiene o no
`card1` / `renderD129` — es **UNKNOWN**.

## Aplicacion del criterio — `AGENTS.md` `§Ownership`

Criterio: **`COMPLETE_AS_DEFINED`**. Texto: OWNERSHIP=FULL requires complete attributable evidence for card1, renderD129, user/root namespaces, DRM FDs, writers, agents, PM, governor, IRQ, scheduler, read-ahead, storage, Btrfs, guard, and restore. If FD visibility is incomplete, PermissionError exists, root namespaces are not covered, a client is active, or a writer is unresolved, then OWNERSHIP != FULL.

| Sub-condicion | Resultado | Motivo |
|---|---|---|
| `card1_complete` | **FAIL** | kwin_wayland FD not readable; completeness not demonstrable |
| `renderD129_complete` | **FAIL** | 0 readable clients but compositor unreadable; zero-observed != zero-actual |
| `user_namespaces_covered` | **PARTIAL** | user@1000.session covered for readable PIDs; unreadable PIDs within the same session exist |
| `root_namespaces_covered` | **FAIL** | 199 root-owned PIDs have unreadable /proc/<pid>/fd; no root namespace covered |
| `drm_fds_enumerated` | **PARTIAL** | 8 FDs across 6 PIDs readable; full set not enumerable |
| `writers_resolved` | **FAIL** | governor, IRQ, scheduler, read-ahead, storage writers NOT enumerated in this audit |
| `agents` | **PASS** | kalm/autopilot absent; no automatic controller observed in this boot |
| `pm` | **OBSERVED** | runtime_status=active, power_control=auto (BLK-02) |
| `governor_irq_scheduler_readahead_storage_btrfs` | **NOT_EVALUATED** | out of scope for a client-FD ownership audit; BLK-05 territory |
| `guard_restore` | **NOT_EVALUATED** | belongs to C1 design (BLK-03); no runtime execution authorized |

## Resultado

```text
OWNERSHIP=PARTIAL
OWNERSHIP_CRITERION=COMPLETE_AS_DEFINED
OWNERSHIP_CARD1=NOT_AVAILABLE
OWNERSHIP_RENDERD129=NOT_AVAILABLE
OWNERSHIP_EFFECT=BLK-01_NOT_CLOSED
```

OWNERSHIP != FULL by criterion: FD visibility is incomplete (215/283 unreadable, 199 root-owned) and root namespaces are not covered. Per AGENTS.md, use PARTIAL or UNKNOWN, never 'parece libre'. Absence of Kalm does NOT imply FULL ownership; it only removes one contributor. FULL would additionally require root-namespace coverage that this task's no-sudo constraint makes impossible.

**La ausencia de Kalm y de `system-autopilot` no convierte esto en FULL.** Elimina un
contaminante de HOST-A, nada mas. El criterio exige ademas cobertura de namespaces de
root, y la restriccion de no-sudo de esta tarea la hace inalcanzable.

## UNKNOWN

- kwin_wayland (PID 1825): does it hold /dev/dri/card1 and/or /dev/dri/renderD129? UNKNOWN — requires privilege
- All 199 root-owned PIDs: whether any holds a DRM node. UNKNOWN
- drm-client-id space is only partially enumerated; the compositor's client-id (if any) is UNKNOWN

## NOT_AVAILABLE

- `debugfs /sys/kernel/debug/dri/1/clients (requires root)`
- `lsof binary not present on host (used /proc instead)`
- `kwin_wayland fdinfo (no privilege)`

## Conflictos

Ninguno observado en esta auditoria. Se conservan los 6 del router sin resolver.

## Relacion con BLK-02

- Kalm absent + autopilot absent: removes HOST-A contributors, but is NOT evidence of FULL ownership
- kwin permission-denied 0: compositor no longer blocked; does not imply it holds no DRM fd
- runtime PM active: consistent with a session in use; does not imply ownership
- card1/renderD129 identity confirmed by BLK-02 and not re-derived here

## RADV y kernel — hallazgos separados, no reconciliados aqui

```text
mesa-vulkan-drivers = NOT_PRESENT   (BLK-02 packages: None)
vulkan_radv_icd     = OBSERVED 0x699f (BLK-02 renderers)
RADV_OPERATIONAL    = OBSERVED
PROVENANCE_OF_RADV  = UNKNOWN      (no verificado de que paquete proviene)
RUNNING_KERNEL      = 7.1.3-200.nobara.fc44.x86_64
RPM_QUERY_KERNEL_CORE = 6.18.2-200.nobara.fc43
CAUSE               = multiple kernels installed / rpm query ordering
STATUS              = DOCUMENTED_TOOL_DEFECT
```

## Garantias de seguridad de esta auditoria

```text
writes_to_system=False
privileges_used=`none (no sudo)`
processes_terminated=0
processes_suspended=0
sysfs_writes=0
services_changed=0
C1_EXECUTED=NO
BENCHMARKS_EXECUTED=NO
PATCHES_APPLIED=0
```
