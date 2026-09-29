# R1 PREFLIGHT — Algoritmo de identidad DRM dinámica y auditoría de comandos

```
R1_STATUS=DESIGNED_NOT_EXECUTED
R1_AUTHORIZATION=REQUIRED
R1_EXECUTABLE_WITH_CURRENT_COLLECTOR=NO
COLLECTOR_CHANGE_REQUIRED=YES
CHANGE_REASON=STATIC_DRM_NODE_MAPPING
COLLECTOR_OWNERSHIP_BOOLEAN=NON_AUTHORITATIVE
DRM_IDENTITY_METHOD=PCI_VENDOR_DEVICE_BDF_THEN_DYNAMIC_SYSFS_RESOLUTION
DRM_IDENTITY_CONFIDENCE=PROVABLE_BEFORE_USE
DRM_ABORT_CONDITION=IDENTITY_NOT_PROVEN
R1_MUTATION_RISK=NONE_IN_PLANNED_COMMAND_SET
R1_MISSING_EVIDENCE=debugfs_client_attribution · proc_pid_maps · dynamic_drm_node_discovery · gpu_pci_identity_verification · dynamic_storage_identity · kwin_fd_visibility
R1_COMMAND_COUNT=15
R1_CAPABILITY_COVERAGE=5_OF_11_WITHOUT_CHANGE
R1_SYSTEM_CHANGES=0   R1_GPU_CHANGES=0   R1_SERVICE_CHANGES=0
R1_SYSFS_WRITES=0     R1_PROCESS_TERMINATED=0  R1_PROCESS_SUSPENDED=0
R1_SUDO_INVOKED=0
```

**Fecha:** 2026-09-25T23:40Z · `HOST_SCOPE=HOST-C` (`DECLARED`) · kernel `7.1.3-200.nobara.fc44.x86_64`
· `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`

**Nada ejecutado.** Cero `sudo`. `privileged_read_collector.py` leído, **byte-idéntico**
(`41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9`), **no modificado**.

---

# PARTE 1 — Algoritmo de identidad DRM dinámica

## 1. Principio

`cardN` y `renderDN` son **propiedad dinámica del host**, no identidad de GPU. R1 resuelve
**BDF → nodos** en cada ejecución y **aborta** si la cadena no es inequívoca. No elige por
posición, orden, menor número ni coincidencia histórica.

## 2. Los ocho pasos

| # | Paso | Fuente | Resultado esperado | Falla ⇒ |
|---:|---|---|---|---|
| 1 | Leer identidad PCI estable | `cat /sys/bus/pci/devices/0000:01:00.0/{vendor,device}` | `0x1002` / `0x699f` | `R1_ABORT=PCI_IDENTITY_MISMATCH` |
| 2 | Confirmar que ese BDF **es** la RX550 objetivo | `readlink -f …/driver` → `amdgpu`; `…/class` = `0x030000` | `amdgpu`, clase display | `R1_ABORT=PCI_IDENTITY_MISMATCH` |
| 3 | Enumerar **todos** los nodos DRM candidatos | `ls /sys/class/drm/{card*,renderD*}` | lista completa | `R1_ABORT=NO_DRM_NODES` |
| 4 | Resolver cada nodo a su BDF | `readlink -f /sys/class/drm/<nodo>/device` → normalizar a BDF | BDF por nodo | nodo no resoluble = excluido y **reportado** |
| 5 | **Vincular** por igualdad de BDF | `bdf(nodo) == "0000:01:00.0"` | subconjunto exacto | ver §4 |
| 6 | Exigir **ambos** roles presentes | ¿hay un `card*`? ¿y un `renderD*`? | 1 card + 1 render** como mínimo** | `R1_ABORT=ROLE_MISSING` |
| 7 | Exigir unicidad | ¿>1 `card*` con ese BDF? ¿>1 `renderD*`? | exactamente 1 de cada uno | `R1_ABORT=AMBIGUOUS_CANDIDATE` |
| 8 | Derivar hijos relacionados | `hwmon` desde `…/device/hwmon/hwmon*`; debugfs desde `…/device/dri/` | `hwmonN`, `dri/<minor>` | hijo ausente = `NOT_AVAILABLE`, **no** aborta |

## 3. Cómo se demuestra que card y render son la misma GPU

**Ambos deben resolver al mismo BDF `0000:01:00.0`.** Es la misma prueba que el link simbólico
del kernel, no una inferencia. Contraste cruzado obligatorio: el `fdinfo` de cualquier cliente
debe mostrar `drm-pdev: 0000:01:00.0`. Si un nodo resuelve a `0000:00:02.0` (Intel), queda
**excluido** aunque su número sea menor.

## 4. Respuestas a las preguntas planteadas

**Q1 ¿Cómo se identifica por PCI vendor/device+BDF?**
Literal de `vendor` y `device` en el sysfs del BDF. Se exige `0x1002`/`0x699f` exacto.

**Q2 ¿Cómo se obtiene el card node?**
Paso 3 → 4 → 5. Un `card*` cuyo `device` resuelve a `0000:01:00.0`.

**Q3 ¿Cómo se obtiene el render node?**
Igual, con `renderD*`. El `minor` del render node debe coincidir con el que el kernel asigna al
BDF en `/sys/bus/pci/devices/0000:01:00.0/` (`drm/renderD*`).

**Q4 ¿Cómo se demuestra que ambos pertenecen a la misma GPU?**
Por igualdad de BDF resuelto en ambos symlinks, más `drm-pdev` en el `fdinfo` de cada cliente.

**Q5 ¿Cómo se evita confundir Intel HD 4600 con RX550?**
El Intel es `0000:00:02.0` / `8086:0412` / `i915`. Resuelve a un BDF distinto, así que el paso 5
lo excluye. **Protección adicional:** R1 registra el BDF de *cada* nodo descartado con su
motivo, para que una exclusión sea auditable y no silenciosa.

**Q6 ¿Varios candidatos?**
Por diseño del kernel hay exactamente un `card*` y un `renderD*` por dispositivo. Si apareciera
más de uno con el mismo BDF, es un estado inesperado: `R1_ABORT=AMBIGUOUS_CANDIDATE`. No se
desempata.

**Q7 ¿Sin correspondencia inequívoca?**
`R1_ABORT=IDENTITY_NOT_PROVEN`. R1 **no recolecta ownership**. Escribir un JSON de "no
encontrado" sería peor que abortar sin escribir: parecería evidencia.

**Q8 ¿Qué evidencia obliga a abortar?**
§6, tabla completa.

## 5. Identidad dinámica de las otras dos rutas del collector

El audit anterior solo subió `card1`. Verificando el código, hay **más hardcodes** y uno es
peligoso por silencioso:

| Hardcode | Ubicación | ¿Coincide en HOST-C? | Riesgo |
|---|---|---|---|
| `DEVICES = {"/dev/dri/card1","/dev/dri/renderD129"}` | L23 | **sí, por casualidad** | ALTO — atribución cruzada |
| `/sys/class/drm/card1/device` | L428 | sí, por casualidad | ALTO |
| `lsof/fuser` sobre card1/renderD129 | L584, L588 | sí, por casualidad | ALTO |
| **`SDA_PREFIX = "/dev/sda"`** | L24, L323, L467 | **`/dev/sda` existe pero NO es el disco raíz** | **SILENCIOSO** |
| `/run/user/1000/c1-isolation-automator*` | L753-754 | sí (uid 1000) | bajo |

**`/dev/sda` es el hallazgo más delicado:** en HOST-A el root estaba en `sda2`; en HOST-C está en
`/dev/sdb3`. `/dev/sda` **existe** en HOST-C pero es otro disco. El collector leería
`/sys/block/sda/queue` y `diskstats` de un dispositivo que no participa en la medición, y
**no fallaría** — produciría números plausibles y equivocados. Eso es peor que un error.

`R1_STORAGE_IDENTITY` debe resolverse desde `findmnt -n -o SOURCE /` → `/dev/sdb3` → su
partición → su disco padre, igual que la GPU.

## 6. Criterio de aborto de identidad

```text
R1_ABORT=PCI_IDENTITY_MISMATCH      vendor/device != 0x1002/0x699f
R1_ABORT=PCI_IDENTITY_MISMATCH      driver != amdgpu, o clase != display
R1_ABORT=NO_DRM_NODES               /sys/class/drm sin card*/renderD*
R1_ABORT=IDENTITY_NOT_PROVEN        ningún nodo resuelve a 0000:01:00.0
R1_ABORT=ROLE_MISSING               no hay card* o no hay renderD* para ese BDF
R1_ABORT=AMBIGUOUS_CANDIDATE        >1 nodo del mismo rol con el mismo BDF
R1_ABORT=STATIC_NODE_ASSUMPTION     el collector intenta usar card1/renderD129 literales
R1_ABORT=MUTATION_REQUIRED          algún comando previsto no es demostrablemente read-only
R1_ABORT=INFERENCE_ONLY             algún resultado crítico solo se obtiene por inferencia
R1_ABORT=STORAGE_IDENTITY_NOT_PROVEN la identidad del disco no es derivable de findmnt
R1_ABORT=IDENTITY_NOT_PROVEN        (canónico) cualquier fallo de la cadena BDF→nodo
```

**En cualquiera de estos casos R1 escribe un marcador de aborto y no recolecta ownership.**

---

# PARTE 2 — Auditoría de los 15 comandos

| ID | Comando | Privilegio | READ_ONLY | Propósito | Entrada | Salida | `MUTATION_RISK` | Aborta si |
|---|---|---|---|---|---|---|---|---|
| C01 | `uname -r` | no | **YES** | kernel en ejecución | — | string | NONE | — |
| C02 | `cat /etc/os-release` | no | **YES** | SO | — | texto | NONE | — |
| C03 | `readlink -f /sys/class/drm/card*/device` | no | **YES** | BDF por nodo | symlinks | tabla BDF↔nodo | NONE | >1 por rol |
| C04 | `cat …/device/{vendor,device,class,driver}` | no | **YES** | identidad PCI | sysfs | valores | NONE | ≠`0x1002`/`0x699f` |
| C05 | `ls /sys/class/drm/` | no | **YES** | inventario de nodos | — | lista | NONE | vacío |
| C06 | `readlink -f /sys/bus/pci/devices/0000:01:00.0/drm/*` | no | **YES** | render node del BDF | symlinks | nodo | NONE | sin render |
| C07 | `findmnt -n -o SOURCE,FSTYPE /` | no | **YES** | identidad del disco raíz (reemplaza `/dev/sda`) | — | device | NONE | — |
| C08 | `ls -l /proc/<pid>/fd/` | **root** | **YES** | tabla de FD completa | procfs | symlinks | NONE | fd ilegible → se registra el error |
| C09 | `cat /proc/<pid>/fdinfo/<n>` | **root** | **YES** | `drm-client-id`, `drm-pdev`, `pasid` | procfs | 16 KB/fd | NONE | — |
| C10 | `readlink /proc/<pid>/ns/{mnt,pid,user,net,cgroup,uts,ipc}` | **root** | **YES** | 7 namespaces | procfs | inodes | NONE | — |
| C11 | `cat /proc/<pid>/maps` | **root** | **YES** | binario que mapeó la GPU | procfs | texto | NONE | — |
| C12 | `cat /proc/<pid>/{status,comm,cmdline,cgroup}` | no | **YES** | metadatos | procfs | texto | NONE | — |
| C13 | `cat /sys/kernel/debug/dri/<minor>/clients` | **root** | **YES** | atribución kernel-level | debugfs | texto | NONE | ausente → `NOT_AVAILABLE`, **no** aborta |
| C14 | `lsof -nP -- <card> <render>` | parcial | **YES** | contraste de clientes | nodos | texto | NONE | — |
| C15 | `fuser -v <card> <render>` | parcial | **YES** | contraste alterno | nodos | texto | NONE | — |

**`READ_ONLY=YES` demostrado por construcción:** los 15 son `cat`, `ls`, `readlink` o `findmnt`.
Ninguno abre un descriptor en modo escritura; ninguno acepta redirección; ninguno invoca
`tee`/`sh -c`. `lsof` y `fuser` abren el nodo **en modo lectura** para consultarlo.

**Comandos que se(propsieron) por tener riesgo de mutación y quedaron fuera:**
`systemctl stop/start/restart` · `kill`/`pkill` · `modprobe`/`rmmod` · `unbind`/`bind` ·
`echo`/`printf`/`tee` sobre sysfs · escrituras a `power/control`, `power1_cap*`, `pp_dpm_*`,
`power_dpm_*` · `nsenter`/`unshare` · montajes nuevos.

**`R1_MUTATION_RISK=NONE_IN_PLANNED_COMMAND_SET`.**

## 2.1 Corrección aplicada al plan previo

El plan de la etapa anterior listaba `/sys/class/drm/{card,renderD*}/device/*` como un solo
comando. Se separó en **C03–C06** porque cada uno tiene su propia condición de aborto. También
se añadió **C07**: sin descubrimiento dinámico del disco, R1 leería `/dev/sda`, que en HOST-C
existe pero no es el disco raíz.

---

# PARTE 3 — R1 vs cambio de código

```text
R1_EXECUTABLE_WITH_CURRENT_COLLECTOR=NO
COLLECTOR_CHANGE_REQUIRED=YES
CHANGE_REASON=STATIC_DRM_NODE_MAPPING
```

**Por qué NO puede ejecutarse tal cual.** El collector fija `DEVICES={"/dev/dri/card1",
"/dev/dri/renderD129"}` (L23) y repite `card1` en L428, L584 y L588. Hoy coincide con HOST-C
**por casualidad**: en HOST-B la RX550 era `card2`. Y **no verifica `vendor`/`device` en ningún
punto** — las únicas lecturas de `vendor`/`device` (L469-470) pertenecen a `queue_identity()`, que
es del **disco**, no de la GPU. Ejecutarlo sin cambio podría atribuir a la RX550 clientes de la
Intel o, peor, omitir los suyos sin señalar error.

### Cambio mínimo necesario (NO implementado)

| # | Cambio | Ubicación | Tamaño |
|---:|---|---|---|
| 1 | `resolve_gpu_identity()`: BDF→card/render/hwmon/drm-minor por sysfs, con `R1_ABORT` en cada fallo | nuevo | ~40 líneas |
| 2 | Sustituir `DEVICES` por `set(resolve_gpu_identity()["nodes"])` | L23 | 1 línea |
| 3 | `lsof`/`fuser` sobre los nodos resueltos | L584, L588 | 2 líneas |
| 4 | `pm_snapshot()` sobre `…/device` del BDF resuelto | L428 | 1 línea |
| 5 | `debugfs` por `dri/<minor>` dinámico, con `NOT_AVAILABLE` si falta | nuevo | ~8 líneas |
| 6 | **`storage_identity()`** desde `findmnt` en vez de `SDA_PREFIX` estático | L24, L323, L467 | ~15 líneas |
| 7 | **`maps` por PID** (gap 2 de §5) | dentro de `scan_fds` | ~3 líneas |
| 8 | **`ownership_full` etiquetado `NON_AUTHORITATIVE`** en la salida | L773 | 1 línea + nota |
| 9 | Matriz de 11 condiciones `AGENTS.md` en la salida, sin booleano único | nuevo | ~25 líneas |

Los cambios 1–6 son **correcciones de corrección** (identidad dinámica). El 8–9 es
**interpretación**: neutralizar un booleano que el proyecto no reconoce como veredicto.

**Nada de esto se ha escrito.** El collector sigue byte-idéntico. Requiere autorización aparte.

---

# PARTE 4 — R1 no declara FULL; entrega evidencia para 11 condiciones

`PREVIOUS` viene de `OWNERSHIP-CLOSURE-ATTEMPT-20260925T232522Z`. `NEW_STATE` **no se
preasigna**: es lo que la evidencia decida. La tabla no implica resultado.

| # | Condición | PREVIOUS | R1_EVIDENCE | NEW_STATE | SOURCE | LIMITATION |
|---:|---|---|---|---|---|---|
| 1 | `card1` completo | `FAIL` | FD+fdinfo de todos los PIDs | *a decidir* | C08,C09,C14 | si el modo de kwin persiste, sigue `FAIL` |
| 2 | `renderD129` completo | `FAIL` | ídem | *a decidir* | C08,C09,C14 | ídem |
| 3 | user namespaces | `FAIL` | kwin_wayland legible | *a decidir* | C08,C10 | — |
| 4 | root namespaces | `FAIL` | 199 PIDs root | *a decidir* | C08,C09,C10 | — |
| 5 | DRM FDs enumerados | `PARTIAL` | conjunto completo | *a decidir* | C08,C09 | — |
| 6 | writers | `NOT_EVALUATED` | **R1 no lo cubre** | `NOT_EVALUATED` | — | **R2** |
| 7 | agents ausentes | `PASS` | re-confirmar en ventana | *a decidir* | C05,C07 | — |
| 8 | PM | `PASS` | lectura | *a decidir* | C04 | — |
| 9 | guard + restore | `FAIL` | **R1 no lo cubre** | `FAIL` | — | **R3**; C1 prohibido |
| 10 | Btrfs identity | `NOT_APPLICABLE` | host es ext4 | `NOT_APPLICABLE` | C07 | sigue ext4 |
| 11 | clients/PASID | `UNKNOWN` | `drm-client-id`+`pasid` | *a decidir* | C09,C13 | debugfs puede faltar |

**R1 cubre 1–5, 7, 8, 10, 11. NO cubre 6 ni 9.**

```text
R1 = privileged read-only ownership evidence
R2 = writer audit (governor/IRQ/scheduler/read-ahead/storage)
R3 = guard / restore / validated recovery
```

**`OWNERSHIP=FULL` requeriría las tres. R1 sola no puede declararlo**, porque 6 y 9 no le
pertenecen. Si tras R1 quedan condiciones sin demostrar: `OWNERSHIP=PARTIAL` ·
`BLK_01=NOT_CLOSED` · `G1=OPEN`.

## 4.1 `COLLECTOR_OWNERSHIP_BOOLEAN=NON_AUTHORITATIVE`

El booleano interno `ownership_full = root_visibility_complete and active_gpu==0 and
active_sda==0 and active_agents==0` (L773-779) es el **gate P0**, no el criterio de
`AGENTS.md` §Ownership, que tiene 11 condiciones y exige *cero handles no aprobados*, no cero
handles. Se clasifica `NON_AUTHORITATIVE` y **no se usa como veredicto**. No se modifica todavía.

---

# PARTE 5 — Las 10 capacidades, verificadas contra el código

La cifra «8/10» del audit previo se recounts aquí contra el código, con la **ruta exacta** de
cada capacidad. Las dos rutas de los gaps también se hacen dinámicas.

| # | CAPABILITY | CURRENT_SUPPORT | SOURCE_CODE_LOCATION | EXPECTED_EVIDENCE | KNOWN_GAP |
|---:|---|---|---|---|---|
| 1 | `/proc/*/fd` (symlink por FD) | **YES** | `scan_fds()` L159-200 | nodo abierto por PID/FD | requiere root |
| 2 | `/proc/*/fdinfo` íntegro | **YES** | `scan_fds()` L196 (`read_text` 16384) | `drm-client-id`, `drm-pdev`, `pasid` | requiere root |
| 3 | Metadatos de proceso | **YES** | `proc_meta()` L115-158 | uid/gid/ppid/comm/cmdline/exe/wchan/cgroup | `maps` **NO** incluido |
| 4 | Namespaces (7) | **YES** | `proc_meta()` L152-155 | mnt/pid/user/net/cgroup/uts/ipc | requiere root |
| 5 | Root processes | **YES** | `proc_pids()` L83, sin filtro uid | conjunto completo | — |
| 6 | `lsof` + `fuser` | **YES** | L584, L588 | contraste por nodo | **nodos hardcodeados** |
| 7 | `/sys/kernel/debug/dri/1/clients` | **NO** | ausente | atribución kernel-level | **GAP 1**; además `1` es estático → debe derivarse de `dri/<minor>` del BDF |
| 8 | `/proc/<pid>/maps` | **NO** | ausente | binario que mapeó la GPU | **GAP 2** |
| 9 | Identidad PCI de la GPU | **NO** | `queue_identity()` L466 lee vendor/device **del disco** | `1002:699f` verificado | **GAP 3 (nuevo)** |
| 10 | Descubrimiento BDF→nodo | **NO** | `DEVICES` L23 estático | card+render ligados al BDF | **GAP 4 (nuevo)** |
| 11 | Identidad del disco | **PARCIAL/ENGAÑOSA** | `SDA_PREFIX` L24 estático | disco raíz real | **GAP 5 (nuevo)**: `/dev/sda` ≠ `/dev/sdb3` en HOST-C |

**Recuento real: 5 de 11 cubiertos sin cambios; 6 requieren cambio.** Los gaps 3, 4 y 5 no
aparecían en el audit previo: aparecieron al leer el código completo esta vez. **`/dev/sda`
existe en HOST-C pero no es el disco raíz**, así que el fallo sería silencioso — devolvería
números plausibles del disco equivocado.

**Sobre los dos gaps conocidos, y su ruta dinámica:**
`/sys/kernel/debug/dri/<minor>/clients`, donde `<minor>` se deriva de
`/sys/bus/pci/devices/0000:01:00.0/dri/renderD*` (C06) — **nunca `dri/1` literal**;
`/proc/<pid>/maps`, por PID, en la misma pasada de FD (C11).

`CAPABILITY_COVERAGE=5_OF_11_WITHOUT_CHANGE`

---

# PARTE 6 — Criterio de aborto

R1 aborta **antes de recolectar ownership** si ocurre cualquiera:

| # | Condición | `R1_ABORT` |
|---:|---|---|
| 1 | `vendor`/`device` ≠ `0x1002`/`0x699f` | `PCI_IDENTITY_MISMATCH` |
| 2 | driver ≠ `amdgpu` o clase ≠ display | `PCI_IDENTITY_MISMATCH` |
| 3 | ningún nodo DRM resuelve a `0000:01:00.0` | `IDENTITY_NOT_PROVEN` |
| 4 | falta `card*` o falta `renderD*` para ese BDF | `ROLE_MISSING` |
| 5 | >1 candidato del mismo rol con el mismo BDF | `AMBIGUOUS_CANDIDATE` |
| 6 | el collector necesita `card1`/`renderD129` literales | `STATIC_NODE_ASSUMPTION` |
| 7 | algún comando no es demostrablemente read-only | `MUTATION_REQUIRED` |
| 8 | algún resultado crítico solo se obtiene por inferencia | `INFERENCE_ONLY` |
| 9 | identidad del disco no derivable de `findmnt` | `STORAGE_IDENTITY_NOT_PROVEN` |

**Ninguna ambigüedad se resuelve por conveniencia.** Un aborto escribe un marcador y nada más:
un JSON con `ownership` vacío se confundiría con evidencia.

---

# PARTE 7 — Conversiones prohibidas

| No se convierte | En |
|---|---|
| 0 clientes visibles | «dispositivo libre» |
| ausencia de Kalm | `OWNERSHIP=FULL` |
| proceso compositor | uso de la RX550 |
| VRAM/GTT agregado | dueño determinado |
| acceso privilegiado | autorización para modificar |
| `ownership_full=True` del collector | veredicto del proyecto |

---

# Garantías

```text
R1_STATUS=DESIGNED_NOT_EXECUTED     R1_AUTHORIZATION=REQUIRED
R1_SYSTEM_CHANGES=0                 R1_GPU_CHANGES=0
R1_SERVICE_CHANGES=0                R1_SYSFS_WRITES=0
R1_PROCESS_TERMINATED=0             R1_PROCESS_SUSPENDED=0
R1_PACKAGE_INSTALLS=0               R1_PATCHES_APPLIED=0
R1_C1_EXECUTED=NO                   R1_BENCHMARKS_EXECUTED=NO
R1_SUDO_INVOKED=0                   R1_MODIFIES_AGENTS_MD=NO
R1_MODIFIES_ROUTER=NO                R1_MODIFIES_CENSUS=NO
COLLECTOR_MODIFIED=NO               (byte-idéntico: 41fee794…)
```

**Reversibilidad:** total. R1 solo lee; su único efecto sería escribir su propio JSON.
**Riesgo principal:** no la recolección, sino la **confianza indebida** en
`ownership_full=True` del collector. R1 lo neutraliza por diseño (Parte 4.1).
