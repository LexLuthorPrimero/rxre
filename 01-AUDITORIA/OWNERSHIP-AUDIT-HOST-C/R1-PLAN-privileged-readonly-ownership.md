# R1 — PLAN/PREFLIGHT — Recolección privilegiada read-only de ownership

```
R1_STATUS=DESIGNED_NOT_EXECUTED
R1_AUTHORIZATION=REQUIRED
R1_PRIVILEGE=ROOT_READ_ONLY
R1_SYSTEM_CHANGES=0
R1_GPU_CHANGES=0
R1_SERVICE_CHANGES=0
R1_SYSFS_WRITES=0
R1_PROCESS_TERMINATED=0
R1_PROCESS_SUSPENDED=0
```

**Fecha de diseño:** 2026-09-25T23:30Z
**Estado base:** `OWNERSHIP=PARTIAL` · `BLK_01=NOT_CLOSED` · `G1=OPEN` ·
`OWNERSHIP_BLOCKER=DOCUMENTED_ACCESS_LIMITATION`
**Host:** `HOST-C` · `HOST_SCOPE_BASIS=DECLARED` · kernel `7.1.3-200.nobara.fc44.x86_64` ·
`HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`

**R1 NO se ejecutó. NO se pidió sudo. Ningún comando privilegiado se emitió en esta etapa.**

## 1. Qué información requiere privilegio, y por qué

Las tres barreras de la 2ª iteración read-only se reducen a un solo hecho: el kernel protege
`/proc/<pid>/fd`, `/proc/<pid>/maps` y los enlaces de namespace según el modo y las capacidades
del proceso observador, no según quién lo observa. Un `cat` no lo cambia.

| Barrera | Evidencia que la cerró en read-only | Evidencia que solo el privilegio da |
|---|---|---|
| `card1` incompleto | Xwayland (client-id 71) | tabla de FD de kwin_wayland y de los 199 PIDs root |
| `renderD129` sin datos | 0 clientes observables | igual:FDM de todos, incluidos los invisibles |
| Root namespaces | ninguno | `/proc/<pid>/fd` de uid 0, que sigue requiriendo privilegio |
| User namespaces | parcial | `/proc/1825/fd` + `/proc/1825/ns/*` de kwin |
| `kwin_wayland` | `UNKNOWN` | su tabla de FD real, o `NOT_AVAILABLE` si no abre nodos DRM |
| Clientes DRM/PASID | 1 atribuido | `fdinfo` `drm-client-id` / `drm-pdev` / `pasid` de cada cliente |

## 2. Auditoría del collector existente — **no se asume completo**

Fichero: `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py` (1158 líneas).
**Auditado leyendo el código. NO ejecutado.** Su docstring declara read-only y no invoca C1.

### 2.1 Cubre (verificado en el código)

| Capacidad | Ubicación | Veredicto |
|---|---|---|
| `/proc/*/fd` completo | `scan_fds()` L159 | **Sí**, con symlink por FD |
| `/proc/*/fdinfo` **contenido íntegro** | `scan_fds()` → `read_text(fdinfo)` 16384 B | **Sí** — incluye `drm-client-id`, `drm-pdev`, `pasid` |
| PID / UID / GID / PPID / comm | `proc_meta()` L115 | **Sí** |
| cmdline, exe, wchan, cgroup | `proc_meta()` | **Sí** |
| **Namespaces** (mnt, pid, user, net, cgroup, uts, ipc) | `proc_meta()` L152 | **Sí**, 7 de 7 |
| Root processes | itera `proc_pids()` sin filtro de uid | **Sí** |
| `kwin_wayland` | cubierto por ser un PID más; `KEYWORDS` incluye `xwayland` pero **no** `kwin` | **Indirecto** |
| `/usr/bin/lsof`, `/usr/bin/fuser` | L584, L588 | **Sí** — ambos existen en HOST-C |

### 2.2 NO cubre (huecos reales)

| Falta | Consecuencia |classification |
|---|---|---|
| **`/sys/kernel/debug/dri/1/clients`** | No hay attribution de kernel-level (PASID→PID) | `NOT_AVAILABLE` |
| **`/proc/<pid>/maps`** | No se puede confirmar qué binario mapeó una GPU | `NOT_AVAILABLE` |
| **Descubrimiento dinámico del nodo** | `DEVICES = {"/dev/dri/card1", "/dev/dri/renderD129"}` **hardcodeado** | `CONFLICT` latente |
| `/proc/<pid>/root`, `/proc/<pid>/cwd` | — | `NOT_AVAILABLE` |

### 2.3 El hardcode es el riesgo principal

`DEVICES` está fijado a `card1`/`renderD129` (L23). En HOST-B la RX550 era `card2`; en HOST-C
es `card1`. **Que coincida hoy es accidental.** Además L584/L588 y L428 apuntan también a
`/dev/dri/card1` de forma literal. Ejecutar el collector sin verificar el nodo puede atribuir
clients de otra GPU o perder los de la RX550.

**R1 resuelve esto con identidad dinámica por `pci_id`+`bdf`, no por `cardN`** — que es
justamente `RX550-PP-01` del router, y por eso no es opcional.

### 2.4 El collector **no** debe declarar `OWNERSHIP=FULL`

El collector calcula `ownership_full = root_visibility_complete and active_gpu==0 and
active_sda==0 and active_agents==0` (L773-779). Eso es el gate P0, **no** el criterio de
`AGENTS.md` §Ownership, que tiene 11 condiciones y exige *cero handles no aprobados*, no solo
cero handles. **R1 no reutiliza ese booleano.** R1 entrega una matriz de 11 filas; el veredicto
se reevalúa contra `AGENTS.md`, nunca contra `ownership_full`.

## 3. Definición de la ejecución R1

**Una sola ventana temporal.** Un único `PREFLIGHT_ID`, un `START_ISO`, un `END_ISO`. Ninguna
recolección en dos pasadas: la atribución de FD es instantánea y no debe cruzarse con otra.

| # | Artefacto | Contenido | Formato |
|---:|---|---|---|
| 1 | Identidad de host | `uname -r`, `os_release`, `HEAD` | JSON |
| 2 | Identidad de GPU | `pci_id`, `bdf`, `driver` **por pci_id+bdf, no cardN** | JSON |
| 3 | Nodos resueltos | `cardN`→BDF, `renderDNN`→BDF, para la RX550 | JSON |
| 4 | PID snapshot | todos los PIDs, uid, comm, ppid, cgroup | JSON |
| 5 | FD snapshot | por PID: fd, target, `fdinfo` íntegro (drm-client-id, drm-pdev, pasid) | JSON |
| 6 | DRM client snapshot | cliente ↔ `drm-client-id` ↔ `pasid` ↔ `drm-pdev` | JSON |
| 7 | Namespace snapshot | 7 namespaces por PID | JSON |
| 8 | kwin snapshot | PID 1825: FD, fdinfo, maps, ns, cmdline | JSON |
| 9 | Root coverage | PIDs uid 0 con lectura completa o con el error exacto | JSON |
| 10 | debugfs clients | `/sys/kernel/debug/dri/1/clients` si es legible | JSON o `NOT_AVAILABLE` |
| 11 | `lsof`/`fuser` | salida cruda con su exit code | texto |
| 12 | Hashes | SHA-256 de cada artefacto | manifiesto |

## 4. Comandos previstos — todos READ-ONLY por construcción

Ninguno escribe. Los marcados `(nuevo)` son los que el collector no cubre.

| # | Comando | Propósito | Privilegio | Modifica |
|---:|---|---|---|---|
| 1 | `uname -r`, `cat /etc/os-release` | identidad de host | no | no |
| 2 | `readlink -f /sys/class/drm/card*/device`, `cat …/vendor`,`…/device` | **nodos por pci_id+bdf (nuevo)** | no | no |
| 3 | `cat /proc/<pid>/fd/*` (symlink) | tabla de FD completa | **root** | no |
| 4 | `cat /proc/<pid>/fdinfo/*` | client-id, pdev, pasid | **root** | no |
| 5 | `cat /proc/<pid>/ns/{mnt,pid,user,net,cgroup,uts,ipc}` | namespaces | **root** | no |
| 6 | `cat /proc/<pid>/maps` | binario que mapeó la GPU (nuevo) | **root** | no |
| 7 | `cat /proc/<pid>/status`,`comm`,`cmdline`,`cgroup`,`exe` | metadatos | no (parcial) | no |
| 8 | `cat /sys/kernel/debug/dri/1/clients` | atribución kernel-level | **root** | no |
| 9 | `lsof -nP -- /dev/dri/card1 /dev/dri/renderD129` | clientes por nodo | parcial | no |
| 10 | `fuser -v /dev/dri/card1 /dev/dri/renderD129` | idem, contraste | parcial | no |
| 11 | `cat /sys/bus/pci/devices/0000:01:00.0/mem_info_*` | asignación agregada (control) | no | no |
| 12 | `sha256sum <artefactos>` | integridad | no | no |

**Comandos prohibidos, por diseño:** `kill`, `pkill`, `systemctl stop/start/restart/reload`,
`tee`/`echo`/`printf` sobre sysfs, `modprobe`, `rmmod`, `unbind`, `bind`, escrituras a
`power/control`, `power1_cap*`, `pp_dpm_*`, `power_dpm_*`, montajes nuevos, `nsenter`,
`unshare`, cualquier manipulación de namespace. **Ninguno figura en la tabla.**

## 5. Matriz de condiciones — R1 reevalúa las 11 de `AGENTS.md`

`PREVIOUS_STATE` viene de `OWNERSHIP-CLOSURE-ATTEMPT-20260925T232522Z`.
`NEW_STATE` **no se preasigna**: R1 no declara FULL. Es la casilla que la evidencia decidirá.

| # | Condición | PREVIOUS_STATE | R1_EVIDENCE esperada | NEW_STATE | SOURCE | LIMITATION |
|---:|---|---|---|---|---|---|
| 1 | `card1` completo | `FAIL` | FD+fdinfo de todos los PIDs | *a decidir* | cmds 3,4,9 | ninguno previsto |
| 2 | `renderD129` completo | `FAIL` | ídem | *a decidir* | cmds 3,4,9 | ninguno previsto |
| 3 | user namespaces | `FAIL` | kwin_wayland legible | *a decidir* | cmds 3,5 | si el kernel mantiene la denegación, seguirá `FAIL` |
| 4 | root namespaces | `FAIL` | 199 PIDs root legibles | *a decidir* | cmds 3,4,5 | si el modo de kwin es otro, puede no bastar root |
| 5 | DRM FDs enumerados | `PARTIAL` | conjunto completo | *a decidir* | cmds 3,4,11 | — |
| 6 | writers (gov/IRQ/sched/readahead/storage) | `NOT_EVALUATED` | **R1 no lo cubre** | `NOT_EVALUATED` | — | **R2, ruta separada** |
| 7 | agents ausentes | `PASS` | re-confirmar en la ventana | *a decidir* | cmds 2,11 | — |
| 8 | PM | `PASS` | lectura | *a decidir* | cmd 11 | — |
| 9 | guard + restore | `FAIL` | **R1 no lo cubre** | `FAIL` | — | **R3, ruta separada; C1 prohibido** |
| 10 | Btrfs identity | `NOT_APPLICABLE` | host es ext4 | `NOT_APPLICABLE` | cmd 1 | sigue sin aplicar en HOST-C |
| 11 | clients/PASID atribuibles | `UNKNOWN` | `drm-client-id`+`pasid` por cliente | *a decidir* | cmds 4,8 | debugfs puede no existir |

**Resultado esperado con alta probabilidad:** condiciones 1–5 pasan, 6 y 9 siguen sin cubrir.
**`OWNERSHIP=FULL` seguiría sin poder declararse** porque 6 y 9 no pertenecen a R1. Se_requires
R1+R2+R3, y R3 requiere runtime que está prohibido.

## 6. Qué NO se convierte en nada

| No se convierte | En |
|---|---|
| 0 clientes visibles | «dispositivo libre» |
| ausencia de Kalm | `OWNERSHIP=FULL` |
| proceso compositor | uso de la RX550 |
| VRAM/GTT agregado | dueño determinado |
| acceso privilegiado | autorización para modificar |

Y además: **R1 no declara `OWNERSHIP=FULL` automáticamente.** Si tras R1 quedan condiciones no
demostrables, se mantiene `OWNERSHIP=PARTIAL` · `BLK_01=NOT_CLOSED` · `G1=OPEN`.

## 7. Separación de rutas — no se mezclan

```
R1 = privileged read-only ownership evidence   ← ESTE PLAN. No ejecutado.
R2 = writer audit (governor/IRQ/sched/readahead/storage)  ← separate. No diseñado.
R3 = validated recovery + guard                 ← separate. NO autorizado (C1 prohibido).
```

`OWNERSHIP=FULL` requeriría las tres. R1 sola no basta, y este documento no lo insinúa.

## 8. Garantías de diseño

```text
R1_SYSTEM_CHANGES=0        R1_GPU_CHANGES=0        R1_SERVICE_CHANGES=0
R1_SYSFS_WRITES=0          R1_PROCESS_TERMINATED=0 R1_PROCESS_SUSPENDED=0
R1_PACKAGE_INSTALLS=0      R1_PATCHES_APPLIED=0    R1_C1_EXECUTED=NO
R1_BENCHMARKS_EXECUTED=NO  R1_MODIFIES_AGENTS_MD=NO R1_MODIFIES_ROUTER=NO
```

**Reversibilidad:** total. R1 solo lee; su único efecto es escribir su propio JSON de evidencia.
**Riesgo:** el riesgo no es la recolección, es la **confianza indebida**: leer
`ownership_full=True` del collector y tomarlo por veredicto. R1 lo evita por construcción
(§2.4).

**Nota deのお amplificación:** ningún privileged command issued. `sudo` no invocado.
