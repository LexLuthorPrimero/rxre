# OWNERSHIP CLOSURE ATTEMPT (HOST-C) — 20260925T232522Z

> Read-only. Sin sudo, sin C1, sin aislamiento, sin tocar procesos ni sistema.
> Objetivo: determinar si `OWNERSHIP=FULL` es demostrable con acceso no privilegiado.

**Resultado: `NOT_REACHABLE_WITHOUT_PRIVILEGE`.** No se modifico el criterio para
alcanzarlo. No se redujo ninguna de las tres barreras.

## A — Visibilidad DRM: todos los oraculos no privilegiados

| Oraculo | Resultado | Clase |
|---|---|---|
| `/proc/<pid>/fd symlinks` | **PARTIAL** | `OBSERVED` |
| `/proc/<pid>/fdinfo drm-* fields` | **PARTIAL** | `OBSERVED` |
| `/sys/class/drm/{card0,card1,renderD128,renderD129}/device/*` | **NONE** | `NOT_AVAILABLE` |
| `/sys/bus/pci/devices/0000:01:00.0/resourceN/clients` | **BLOCKED** | `NOT_AVAILABLE` |
| `/sys/kernel/debug/dri/1/` | **BLOCKED** | `NOT_AVAILABLE` |
| `/sys/bus/pci/devices/0000:01:00.0/{gpu_busy_percent,mem_busy_percent}` | **EMPTY** | `NOT_AVAILABLE` |
| `systemctl show --property MainPID kwin_wayland.service` | **NOT_FOUND** | `NOT_AVAILABLE` |

Every DRM client-enumeration path outside /proc requires root. No unprivileged substitute exists on this host.

### Evidencia agregada: hay asignacion sin atribuir

| Metrica | Valor |
|---|---|
| `mem_info_vram_used` | `5439488` |
| `mem_info_vis_vram_used` | `5439488` |
| `mem_info_vram_total` | `2147483648` |
| `mem_info_gtt_used` | `12226560` |

Cliente observado y contabilizado: `Xwayland PID 1923 fd13` — `2184 KiB` GTT, `136 KiB` VRAM.

- **`SUPPORTED`:** SUPPORTED — memory is allocated on the RX550 beyond what the single observed client accounts for.
- **`UNKNOWN`:** UNKNOWN — aggregate counters carry no per-client attribution. The unattributed remainder is consistent with a privileged or unreadable client (kwin_wayland is the obvious candidate) but does NOT demonstrate one. Absence of per-client counters means this evidence can neither confirm nor exclude.

**`The unattributed VRAM/GTT is NOT attributed to kwin_wayland. Attributing it would be exactly the inference the task forbids.`**

## B — kwin_wayland (PID 1825)

### Observable sin privilegio

| Campo | Valor |
|---|---|
| `comm` | `kwin_wayland` |
| `cmdline` | `/usr/bin/kwin_wayland --wayland-fd 7 --socket wayland-0 --xwayland-fd 8 --xwayland-fd 9 --xwayland-display :0 --xwayland-xauthority /run/user/1000/xau` |
| `status_readable` | `True` |
| `stat_readable` | `True` |
| `threads` | `28` |
| `uid` | `1000` |
| `ppid` | `1817` |
| `CapEff` | `0000000000800000` |
| `NoNewPrivs` | `0` |
| `Seccomp` | `0` |

### Bloqueado sin privilegio

```text
/proc/1825/fd
/proc/1825/maps
/proc/1825/io
/proc/1825/cwd
/proc/1825/root
/proc/1825/ns/{mnt,pid,net,user,uts,ipc,cgroup}
```

### Decode de capabilities

`CapEff=`0x800000`` → bit 23 = `CAP_SYS_NICE`.

- Proves a privileged origin: the process is uid 1000 but retains a capability a normal user process cannot hold. It is NOT a DRM capability.
- `NO explica el deniego: `CAP_SYS_NICE does not itself gate /proc/<pid>/fd. The denial mechanism is not identified. Yama ptrace_scope=0 is NOT the cause.

### El padre 1817 si es legible — y no ayuda

`kwin_wayland_wr` (1817), fd legible: `DRM fds: NONE`, `DRM fdinfo: NONE`.

The wrapper holds no DRM node. The FDs it passes to kwin (--wayland-fd 7, --xwayland-fd 8/9) are Wayland/X11 sockets, not DRM nodes. The DRM fd, if any, is opened by kwin_wayland itself and is unobservable.

```text
KWIN_RELATION=`UNKNOWN`
CLASSIFICATION=`UNKNOWN`
```

**`kwin_wayland is the compositor of the active session, and the project's HOST-A evidence recorded it holding card1 and renderD129. NONE of that is transferred. Being the compositor does not demonstrate use of the RX550: the host has an Intel HD 4600 that owns the display connectors (card1-DVI-D-1, card1-HDMI-A-2 connector names are on card0). Its relationship to 0000:01:00.0 is not demonstrable without reading its fd table.`**

## C — Cobertura de root

| Oraculo | Resultado |
|---|---|
| `/proc/<pid>/fd (uid 0)` | BLOCKED |
| `fdinfo drm-* (uid 0)` | BLOCKED |
| `systemctl show MainPID per unit` | INCOMPLETE — resolves some units but not a client list, and returned 0 for kwin_wayland.service |
| `aggregate amdgpu counters` | NO_PER_CLIENT_ATTRIBUTION |

No unprivileged source enumerates DRM clients held by root-owned processes. The barrier is structural, not a matter of trying harder.

```text
ROOT_COVERAGE=`NOT_AVAILABLE`
```

## D — Namespaces / contexto

Of 283 PIDs, 215 have an unreadable /proc/<pid>/fd: 199 root-owned, 5 uid-1000 (sd-pam, kwin_wayland, polkit-kde-auth, ssh-agent, fusermount3), and 11 belonging to other uids.

**El caso uid-1000 restringido:** kwin_wayland (1825) is uid 1000 yet its fd, maps, io, cwd, root and all 7 namespace links are denied, while its parent (1817, same uid) is fully readable. The differentiator was not identified: not Yama (ptrace_scope=0), not seccomp (0), not NoNewPrivs (0). No bypass was attempted.

```text
NAMESPACE_COVERAGE=`PARTIAL`
namespaces_entered=0
namespaces_modified=0
```

## E — Evaluacion del criterio (sin modificarlo)

Fuente: `AGENTS.md section Ownership (unchanged; not modified to reach FULL)`

| Condicion | Resultado | Clase | Motivo |
|---|---|---|---|
| card1 complete evidence | **FAIL** | `OBSERVED` | kwin_wayland fd unreadable; 199 root PIDs uncovered |
| renderD129 complete evidence | **FAIL** | `OBSERVED` | 0 readable clients is not evidence of 0 actual clients; compositor unreadable |
| user namespaces covered | **FAIL** | `OBSERVED` | kwin_wayland is in the user session and is unreadable; Xwayland is a child of it (ppid 1825) |
| root namespaces covered | **FAIL** | `OBSERVED` | 199 root-owned PIDs, no unprivileged oracle |
| DRM FDs enumerated | **PARTIAL** | `OBSERVED` | 8 FDs / 6 PIDs readable; full set not enumerable |
| writers resolved (governor, IRQ, scheduler, read-ahead, storage) | **NOT_EVALUATED** | `NOT_AVAILABLE` | outside a client-FD audit; belongs to the storage/IRQ layer |
| agents absent | **PASS** | `OBSERVED` | kalm*, system-autopilot, sys-tuned all not-found (BLK-02); irqbalance present and enabled |
| PM state | **PASS** | `OBSERVED` | power/control=auto, runtime_status observed; BLK-02 |
| guard and restore validated | **FAIL** | `OBSERVED` | RESTORE_EXECUTED=NO, RESTORE_VALIDATED=NO (C1 design doc); no runtime allowed |
| Btrfs identity | **NOT_APPLICABLE** | `OBSERVED` | host root is /dev/sdb3 ext4, not Btrfs; HOST-A Btrfs claims do not transfer |

```text
CONDITIONS_TOTAL=11
CONDITIONS_PASS=3
CONDITIONS_FAIL=6
CONDITIONS_PARTIAL=1
CONDITIONS_NOT_EVALUATED=1
OWNERSHIP_CRITERION=`COMPLETE_AS_DEFINED`
```

## Rutas de cierre (documentadas, NO ejecutadas)

### `R1`

| Campo | Valor |
|---|---|
| `REQUIRED_EVIDENCE` | /proc/<pid>/fd + fdinfo for every process holding a RX550 DRM node, including uid 0 and including kwin_wayland |
| `WHY_CURRENT_ACCESS_CANNOT_OBTAIN_IT` | Kernel gates those paths on privilege; uid 1000 without CAP_SYS_PTRACE-equivalent cannot read them. ptrace_scope=0 does not help because the restriction is not Yama. |
| `MINIMAL_NEXT_ACTION` | A single privileged READ-ONLY collection run, equivalent to the project's own privileged_read_collector.py, as a separately authorized step |
| `RISK` | LOW for the collection itself (read-only); it does NOT authorise C1 or isolation |
| `REVERSIBILITY` | NOT_APPLICABLE — no state change |
| Resuelve | card1, renderD129, root namespaces, user namespaces, DRM FDs |
| **NO** resuelve | writers, guard/restore |

### `R2`

| Campo | Valor |
|---|---|
| `REQUIRED_EVIDENCE` | Writer attribution for governor, IRQ affinity, scheduler, read-ahead, storage on the RX550 and the root filesystem during a measurement window |
| `WHY_CURRENT_ACCESS_CANNOT_OBTAIN_IT` | Requires /proc/<pid>/fd of root agents and /sys/kernel/debug or per-CPU irq affinity reads; no unprivileged equivalent |
| `MINIMAL_NEXT_ACTION` | Documented as a separate read-only audit; NOT executed here |
| `RISK` | LOW if read-only |
| `REVERSIBILITY` | NOT_APPLICABLE |
| Resuelve | writers |
| **NO** resuelve | card1, renderD129, guard/restore |

### `R3`

| Campo | Valor |
|---|---|
| `REQUIRED_EVIDENCE` | A validated, independent recovery path (TTY/console/session) and a verified restore, before any isolation could ever be considered |
| `WHY_CURRENT_ACCESS_CANNOT_OBTAIN_IT` | Requires runtime execution; C1 execution is prohibited and PREVIOUS_RECOVERY=FAIL on HOST-A |
| `MINIMAL_NEXT_ACTION` | None within current authorization |
| `RISK` | HIGH |
| `REVERSIBILITY` | MANDATORY |
| Resuelve | guard/restore |
| **NO** resuelve | card1, renderD129, root namespaces, writers |

## Conclusion

```text
OWNERSHIP=`PARTIAL`
OWNERSHIP_BLOCKER=`DOCUMENTED_ACCESS_LIMITATION`
BLK_01=`NOT_CLOSED`
G1=`OPEN`
barriers_reduced_this_stage=NONE
```

**Barreras nuevas cuantificadas:** The kwin_wayland denial is NOT Yama, NOT seccomp, NOT NoNewPrivs; the mechanism was not identified. 5 uid-1000 processes are affected, not 1.

**`Condiciones satisfechas por la nueva evidencia: `NONE. This stage produced no condition change; it produced a documented proof that the remaining conditions are unreachable without privilege.**

**`Ausencia no convertida: `The absence of visible renderD129 clients and the absence of Kalm were NOT converted into evidence of absence or into ownership FULL.**

## Evidencia previa preservada

- `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/OWNERSHIP-AUDIT-HOST-C-20260925T231635Z.{json,md}`
- `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T231128Z.{json,md}`
- `01-AUDITORIA/HOST-C-DIAGNOSTIC-RECONCILIATION/HOST-C-DIAGNOSTIC-RECONCILIATION-20260925T232146Z.{json,md}`

## Garantias

```text
WRITES_TO_SYSTEM=False
PACKAGE_INSTALLS=0
SERVICE_CHANGES=0
SYSFS_WRITES=0
PROCESSES_TERMINATED=0
PROCESSES_SUSPENDED=0
PROCESSES_NAMESPACES_ENTERED=0
PATCHES_APPLIED=0
BENCHMARKS_EXECUTED=False
C1_EXECUTED=FALSE
privileges_used=`none (no sudo)`
```
