# R1-ACTORS-INVENTORY-20260926

`DOCUMENT_KIND` = `ACTOR_INVENTORY` · **READ_ONLY + DOCUMENTACIÓN**
`TECHNICAL_MODEL_STATUS` = `CLOSED` (no modificado) · `PROJECT_MAPPING` = `NOT_ATTEMPTED`
`REQUIREMENT_INTENT_RECONSTRUCTION` = `NOT_ATTEMPTED`
Regla: `APLICACIÓN ≠ PROCESO ≠ FD ≠ struct drm_file ≠ drm-client-id ≠ PASID ≠ nodo DRM ≠
dispositivo PCI ≠ GEM ≠ VM ≠ engine`. NINGUNA definición P-1…P-16 fue alterada por este
documento. NINGÚN requisito, `PASS`/`FAIL`, `any()`/`all()` ni criterio de ownership fue creado
o modificado. Cero cambios de código, tests, `AGENTS.md`, `README.md`, collector o runner.

## 0 · CAPTURAS (TEMPORALITY · HOST_SCOPE)

Ninguna captura es intercambiable. PIDs y nombres `cardN` **no** son comparables entre capturas.

| | Artefacto | Timestamp | `HOST_SCOPE` | Privilegio | Modo |
|---|---|---|---|---|---|
| **CAP-1** | `OWNERSHIP-AUDIT-HOST-C/OWNERSHIP-AUDIT-HOST-C-20260925T231635Z.{json,md}` | `2026-09-25T23:16:35Z` | **`HOST-C` DECLARADO** | uid 1000, **sin sudo** | `READ_ONLY_EVIDENCE` |
| **CAP-2** | `FASE-C1-RUNTIME-PREFLIGHT/R1-20260926T030435Z.json` | `2026-09-26T03:05:07.847Z`→`03:07:09.660Z` | host `kalm`, kernel `7.1.3-200.nobora.fc44.x86_64` | **`EUID 0`** | `PRIVILEGED_READ_ONLY` |
| **CAP-3** | `FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-INTERACTIVE-LOGIN-TEST-20260925T080020Z-POST.json` | `2026-09-25T08:01:06Z` | **`NOT_AVAILABLE`** (sin `metadata.host`) | `NOT_AVAILABLE` | `CONTROLLED_TTY3_INTERACTIVE_LOGIN_TEST` |
| **CAP-4** | fichero debugfs `dri/129/clients`, citado en `R1-C1-CORRECTION-CLOSURE-20260926.md:350-360` | `NOT_AVAILABLE` (no fechado en la cita) | `NOT_AVAILABLE` | `EUID 0` declarado en el texto | `NOT_AVAILABLE` |
| **CAP-5** | contadores `12/12/12` citados en `R1-ATTRIBUTABLE-DEFINITION-RESEARCH:158`, `R1-REPAIRED-TECHNICAL-REQUIREMENTS:161,198,215` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |

**CAP-1 y CAP-2 comparten PIDs** (1825, 1910, 1923, 2003, 2191) → **mismo arranque**. CAP-3 tiene
PIDs distintos (3237, 3246, 3447…) y un timestamp **anterior** con PIDs **mayores** que CAP-1/CAP-2
→ **`INFERENCE`**: hubo un reinicio entre `2026-09-25T23:16` y `2026-09-26T03:05`. No verificado.

**Discrepancia de cobertura, no de estado** (atribución de cambio, `AGENTS.md` §Investigación):
`kwin_wayland` PID 1825 tiene **0 FDs visibles** en CAP-1 (uid 1000, `/proc/1825/maps` ilegible) y
**7 FDs DRM visibles** en CAP-2 (`EUID 0`, `ROOT_FD_COVERAGE = 283/283`,
`root_visibility_complete_for_snapshot = true`, `0` permission-denied, `0` unreadable). Es el
**mismo proceso**. La diferencia es `COVERAGE`, atribuible al privilegio, **no** a un cambio del
proceso. `SUPPORTED`.

**Identidad del dispositivo** (CAP-2, `identity.GPU`): `GPU_IDENTITY_STATUS = PROVEN`,
BDF `0000:01:00.0`, vendor `0x1002`, device `0x699f`, driver `amdgpu`, `card1` (minor 1),
`renderD129` (minor 129), `drm_discovery.agreement = true`. `card0`/`renderD128` = **otra** GPU
(`kworker/u33:3+i915_flip` en `window.blocked_tasks_union`). `PRIMARY_KERNEL_SOURCE` no aplica;
`RUNTIME_OBSERVATION` + `PROJECT_IMPLEMENTATION`.

---

## 1 · APLICACIONES DEL HOST

Campos omitidos = `NOT_AVAILABLE` o `NOT_OBSERVED`; ninguno se rellena por suposición.
**`drm-client-id`, `drm-pdev` y `PASID` observados: `NOT_AVAILABLE` en todas las entradas** — ver §5.

### 1.1 · Con FDs DRM legibles sobre nodos de la RX550

| | A-1 `kwin_wayland` | A-2 `Xwayland` |
|---|---|---|
| `TIPO` | `APPLICATION`+`PROCESS` (compositor) | `APPLICATION`+`PROCESS` (servidor X) |
| `EJECUTABLE` | `/usr/bin/kwin_wayland` | `/usr/bin/Xwayland` |
| `ROL` | compositor Wayland de Plasma | servidor X para clientes X11 |
| `PID` observado | **1825** (CAP-1, CAP-2) · **3246** (CAP-3) | **1923** (CAP-1, CAP-2) · **3447** (CAP-3) |
| `PPID` / `UID` | 1817 / **1000** | — / **1000** |
| `NAMESPACE` | cgroup `0::/…/session.slice/plasma-kwin_wayland.service`; `pid:[4026531836]`, `mnt:[4026531832]`, `cgroup:[4026531835]`, `user:[4026531837]`, `ipc:[4026531839]`, `net:[4026531833]`, `uts:[4026531838]` | mismos valores de namespace que A-1 (CAP-2) |
| `NODO DRM` | `/dev/dri/renderD129` y `/dev/dri/card1` (**RX550**) | `/dev/dri/card1` (**RX550**) |
| `FD DRM` | **7**: `14,15,16,17`→`renderD129`; `51,52,53,54,55`→`card1` (CAP-2, root) | **1**: `13`→`card1` (CAP-1 y CAP-2) |
| `drm-client-id` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `drm-pdev` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `PASID` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| OTRAS RELACIONES | cmdline: `--wayland-fd 7 --socket wayland-0 --xwayland-fd 8 --xwayland-fd 9 --xwayland-display :0`; `KWIN_GPU_RELATION = OBSERVED`, base «`/proc/<pid>/fd` symlink on a BDF-proven DRM node»; `other_drm_targets` = `card0`,`renderD128` | `KWIN_GPU_RELATION = OBSERVED`; en CAP-3 `--rootless` |
| `FUENTE` | CAP-2 `ownership.gpu_clients`, `ownership.compositor_gpu_relations`; CAP-1 md | íd. + CAP-3 `post.processes` |
| `ESTADO` | `OBSERVED` (proceso, FDs, nodos) | `OBSERVED` |
| `LIMITACIONES` | A-1 con 7 FDs solo en CAP-2 (root). En CAP-1 el mismo PID tenía **0**: cobertura, no ausencia. `fdinfo` **vacío** en CAP-2 (`fdinfo: ""`), por lo que ninguna clave fdinfo fue leída en ese artefacto | un solo FD; sin `drm_file` ni `client_id` identificables |

### 1.2 · Con FDs DRM legibles sobre nodos **de otra GPU** (no RX550)

| | A-3 `firefox-bin` | A-4 `plasmashell` | A-5 `plasma-keyboard` | A-6 `xwaylandvideobr` | A-7 `nobara-welcome` |
|---|---|---|---|---|---|
| `TIPO` | `APPLICATION`+`PROCESS` | `PROCESS` (escritorio) | `PROCESS` (servicio) | `PROCESS` (bridge) | `APPLICATION`+`PROCESS` |
| `EJECUTABLE` | `NOT_AVAILABLE` en CAP-1 | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `/usr/bin/xwaylandvideobridge` (CAP-3) | `NOT_AVAILABLE` |
| `ROL` | navegador | shell de Plasma | teclado en pantalla | puente de vídeo Xwayland | asistente de bienvenida |
| `PID` | **3424** (CAP-1) | **2003** | **1910** | **2191** (CAP-1) · 3753 (CAP-3) | **2218** |
| `UID` | 1000 | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `NAMESPACE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `NODO DRM` | **`renderD128` (Intel HD 4600)** | `renderD128` | `renderD128` | `renderD128` | `renderD128` |
| `FD DRM` | `NOT_AVAILABLE` (conteo, no descriptor) | íd. | íd. | íd. | íd. |
| `drm-client-id` / `drm-pdev` / `PASID` | `NOT_AVAILABLE` ×3 | `NOT_AVAILABLE` ×3 | `NOT_AVAILABLE` ×3 | `NOT_AVAILABLE` ×3 | `NOT_AVAILABLE` ×3 |
| OTRAS RELACIONES | `KWIN_GPU_RELATION = UNKNOWN`, base «no DRM FD observed; absence of evidence is not evidence of absence» | íd. | — | `KWIN_GPU_RELATION = UNKNOWN` | — |
| `FUENTE` | CAP-1 md tabla «PIDs con FDs legibles sobre el nodo Intel» | íd. | íd. | íd. + CAP-3 | CAP-1 md |
| `ESTADO` | `NOT_OBSERVED` en nodos RX550; `OBSERVED` sobre Intel | íd. | íd. | íd. | íd. |
| `LIMITACIONES` | **el documento afirma `Xwayland` como «la única RX550 client-visible»; A-3 no figura en ningún nodo de la RX550**. Ninguna afirmación de que Firefox usara o no usara la RX550 puede derivarse de CAP-1: `renderD128` no es la RX550 | sin PID en CAP-2 | sin PID en CAP-2 | sin PID en CAP-2 | sin PID en CAP-2 |

**`Xwayland` figura en las dos columnas**: aparece con un FD legible en `card1` (RX550) **y** con FD
legible en `renderD128` (Intel). Un proceso puede tener FDs en ambos dispositivos. No hay
contradicción; sí una advertencia contra cualquier Inferencia «Xwayland → la RX550» sin calificar el
nodo.

### 1.3 · Observados como proceso, **sin** dato de FD DRM

| | A-8 `kwin_wayland_wrapper` | A-9 `systemd` | A-10 `systemd-logind` | A-11 `irqbalance.service` |
|---|---|---|---|---|
| `TIPO` | `PROCESS` (wrapper) | `PROCESS` (init) | `PROCESS` (servicio) | `PROCESS` (servicio) |
| `EJECUTABLE` | `/usr/bin/kwin_wayland_wrapper` | `/usr/lib/systemd/systemd` | `/usr/lib/systemd/systemd-logind` | `NOT_AVAILABLE` |
| `ROL` | lanza el compositor con `--xwayland` | init del sistema | gestión de sesiones | balanceo de IRQ |
| `PID` | **3237** (CAP-3) · **1817** (CAP-1/2) | **1** | **993** | `ExecMainPID 973` (CAP-2) |
| `UID` | `NOT_AVAILABLE` | **0** | **0** | `NOT_AVAILABLE` |
| `NAMESPACE` | `NOT_AVAILABLE` | `pid:[4026531836]`, `mnt:[4026531832]`, cgroup `0::/init.scope` | mismo `pid`/`mnt`; cgroup `0::/system.slice/systemd-logind.service` | cgroup `/system.slice/irqbalance.service` |
| `NODO DRM` | `NOT_OBSERVED` (`KWIN_GPU_RELATION = UNKNOWN`) | `card1` y `card0` | `card1` | `NOT_AVAILABLE` |
| `FD DRM` | `NOT_OBSERVED` | **208**→`card1`; **230**→`card0` | **29**→`card1` | `NOT_AVAILABLE` |
| `drm-client-id` / `drm-pdev` / `PASID` | `NOT_OBSERVED` ×3 | `NOT_AVAILABLE` ×3 (fdinfo vacío) | `NOT_AVAILABLE` ×3 | `NOT_AVAILABLE` ×3 |
| OTRAS RELACIONES | cmdline `--xwayland` | `ROOT_FD_COVERAGE 283/283`; `state S`; `wchan ep_poll` | `state S`; `wchan ep_poll` | `ActiveState active` |
| `FUENTE` | CAP-3; CAP-1/2 `compositor_gpu_relations["1817"]` | CAP-2 `gpu_clients`, `relevant_processes` | CAP-2 `gpu_clients` | CAP-2 `active_service_rows` |
| `ESTADO` | `OBSERVED` como proceso; `NOT_OBSERVED` en DRM | `OBSERVED` | `OBSERVED` | `OBSERVED` |
| `LIMITACIONES` | `UNKNOWN` **no** significa ausente: el bundle lo declara explícitamente | `fdinfo: ""` → ninguna clave leída | íd. | sin datos de FD |

### 1.4 · Aplicación de escritorio observada en CAP-3 (Electron)

| | A-12 `ChatGPT` (escritorio) |
|---|---|
| `TIPO` | `APPLICATION` + familia de `PROCESS` |
| `EJECUTABLE` | `/usr/lib/chatgpt/ChatGPT` |
| `ROL` | aplicación de escritorio Electron |
| `PID` | **4190** (principal) · 4494, 4495, 4497 (zygotes) · **4535** (`--type=gpu-process`, `--ozone-platform=x11`) · 4538, 4579 (utilities) · 4890, 4982, 5798, 5943, 5973 (renderers) |
| `UID` | `NOT_AVAILABLE` |
| `NAMESPACE` | `NOT_AVAILABLE` |
| `NODO DRM` | `NOT_AVAILABLE` |
| `FD DRM` | `NOT_AVAILABLE` — **CAP-3 no capturó datos de FD** |
| `drm-client-id` / `drm-pdev` / `PASID` | `NOT_AVAILABLE` ×3 |
| OTRAS RELACIONES | `--user-data-dir=/home/lucas/.config/C…`; `impact.kwin_xwayland_chatgpt_present = true` |
| `FUENTE` | CAP-3 `post.processes`, `impact` |
| `ESTADO` | `OBSERVED` como proceso en CAP-3; `UNKNOWN` en relación con DRM |
| `LIMITACIONES` | **`--type=gpu-process` no demuestra ningún FD DRM.** Es la existencia de un subproceso etiquetado «gpu», no una observación de `/dev/dri`. `NOT_RUN` cualquier verificación |

### 1.5 · Firefox: tres estados distintos, ninguno es «el cliente de la GPU»

| Afirmación | Fuente | `CLASS` |
|---|---|---|
| `firefox-bin` PID 3424, uid 1000, FD legible sobre `renderD128` (**Intel**) | CAP-1 md | `RUNTIME_OBSERVATION` |
| «Firefox y su relación con la GPU» como **tema** | `DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md:655-657` (`KEYWORDS: firefox`) | `PROJECT_DOCUMENT` — **no** es observación |
| «`renice +5 firefox` / `renice -10 kwin_wayland`» | `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md:197` | `PROJECT_DOCUMENT` — **comando previsto**, no ejecución; además usa un nombre de **aplicación** donde el proceso observado se llama `firefox-bin` |

**`firefox` = aplicación · `firefox-bin` = proceso · ninguno de los dos es un `drm_file`.**

---

## 2 · PROCESOS DEL PROYECTO

| | P-1 collector | P-2 runner/automator | P-3 shell de captura | P-4 librería `rx550-torneo` | P-5 validador | P-6 `codex` |
|---|---|---|---|---|---|---|
| `TIPO` | `PROJECT_COMPONENT` (`IMPLEMENTATION`) | `PROJECT_COMPONENT` | `PROJECT_COMPONENT` | `PROJECT_COMPONENT` | `PROJECT_COMPONENT` | `AGENT_COMPONENT` (harness, no del proyecto) |
| `ORIGEN` | `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`, sha256 `bf77c33255a3a65f6cb62387a6181020c7b96a1e1e009bbd49c8cde040558681` | `04-IMPLEMENTACION/c1_isolation_automator.py` | `/bin/bash` | `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/` (11 módulos: `util`, `state_manager`, `cli`, `cap_test`, `gpu_finder`, `cap_run`, `failsafe`, `write_test`, …) | `tools/validate_rx550_final.py` | `/usr/lib/chatgpt/resources/codex` |
| `ROL` | lector read-only; productor + consumidor de la matriz | automatización de aislamiento C1 | envoltorio de captura | librería de experimentos de tornEO | validación final | `app-server` con `features.code_mode_host=true` |
| `PID` observado | **`NOT_AVAILABLE`** en CAP-1/2/3 | `NOT_AVAILABLE` | **8783** (CAP-3), `comm=bash`, cmdline `set -euo pipefail ROOT='/home/lucas/Escritorio/RX550-INVESTIGACION' E="$ROOT/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT" ID='C1-TTY3-INTERACT…` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | **4911** (CAP-3) |
| `UID` | `NOT_AVAILABLE` como proceso | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `NAMESPACE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `NODO DRM` | ninguno — **es un lector, no un cliente** | `NOT_AVAILABLE` | ninguno observado | ninguno observado | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `FD DRM` | `NOT_APPLICABLE` (no se observó ejecutándose con FDs DRM) | `NOT_AVAILABLE` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| `drm-client-id`/`drm-pdev`/`PASID` | `NOT_APPLICABLE` | `NOT_AVAILABLE` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_AVAILABLE` | `NOT_AVAILABLE` |
| OTRAS RELACIONES | produjo `CAP-2`; `mutating_commands: []`; `c1_invoked: false`; `privileges_used: privileged_reads: true` con `EUID_OBSERVED 0` | `AGENTS.md` prohíbe `C1`/`--run` sin autorización | es el proceso que produjo `CAP-3` | `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py` | — | `plugins.codex-app-tools@openai-bundled.mcp_…` |
| `FUENTE` | sha256 local; `CAP-2.metadata` | árbol del repo | `CAP-3.post.processes[19]` | árbol del repo | árbol del repo | `CAP-3.post.processes[14]` |
| `ESTADO` | `OBSERVED` (existe) · `NOT_OBSERVED` (proceso en ejecución) | `OBSERVED` (existe) | `OBSERVED` (proceso + cmdline) | `OBSERVED` (existe) | `OBSERVED` (existe) | `OBSERVED` (proceso) |
| `LIMITACIONES` | el artefacto no registra el PID del propio collector: `Captured is not consumed` invertido — el productor **no** se registra a sí mismo en `gpu_clients` | nunca ejecutado en esta sesión | `HOST_SCOPE = NOT_AVAILABLE` | nunca ejecutado en esta sesión | — | **no es un componente del proyecto** |

Otros componentes del proyecto **existentes en el árbol, nunca observados en ejecución**:
10 ficheros de test en `FASE-C1-RUNTIME-PREFLIGHT/`, `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py`,
`03-EXPERIMENTOS/**` (harness CMake/Vulkan, p. ej. `VkLayer_iterativero_jitter_observer.json`),
`03-EXPERIMENTOS/FASE-R4B-GOVERNOR/**`, `03-EXPERIMENTOS/M1-cap-35-30/**`.
`ESTADO = OBSERVED` (existen como ficheros) · `NOT_OBSERVED` como procesos.

**Nota de nomenclatura**: «el collector» es un **proceso** cuando se ejecuta y un **fichero**
cuando se nombra. `privileged_read_collector.py` no es un `drm_file`; no holds ni puede hold un
`drm-client-id`.

---

## 3 · AGENTES / COMPONENTES DE OPENCODE

| | O-1 agente primario | O-2 subagentes | O-3 instrucciones | O-4 configuración |
|---|---|---|---|---|
| `TIPO` | `AGENT` (sesión) | `AGENT` (subagentes de sesión) | `PROJECT_DOCUMENT` | `OPENCODE_CONFIG` |
| `NOMBRE` | sesión OpenCode actual, cwd `/home/lucas/Escritorio/RX550-INVESTIGACION`, `ses_f23f97e69ffeeiBopdfS0ZaYJB` | **`explore`**, **`general`** | **`AGENTS.md`** en la raíz del proyecto, 17 488 B | **no existe configuración de proyecto** |
| `ORIGEN` | harness | catálogo de la sesión | raíz del repo | — |
| `ROL` | conductors de esta investigación | explorar y trabajo paralelo | reglas durables del proyecto | — |
| ¿existe? | `OBSERVED` | `OBSERVED` **en el catálogo de la sesión** | `OBSERVED` en disco | **`NOT_AVAILABLE`**: no existe `.opencode/` ni `opencode.json` en el proyecto |
| `PROJECT_CONFIGURED` | n/a | **`NO`** — no hay fichero de configuración que los declare | n/a | `NOT_AVAILABLE` |
| `FUENTE` | id de sesión | catálogo de herramientas de la sesión | `ls -la AGENTS.md` | `ls .opencode opencode.json` → *No existe* |
| `ESTADO` | `OBSERVED` | `OBSERVED` (capacidad) / `NOT_AVAILABLE` (configuración del proyecto) | `OBSERVED` | `NOT_AVAILABLE` |
| `LIMITACIONES` | — | **su existencia como capacidad no prueba que se hayan usado ni que estén configurados para este proyecto** | `AGENTS.md` **no es un agente**; es un fichero de instrucciones | única config de usuario: `~/.config/opencode/service.json`, claves `['password']` (valor **no inspeccionado**, no impreso) |

**Divergencia de estado** (`CONFLICT` de estado, no de contenido): `CAP-2`'s padre
`C1-PREFLIGHT-20260925T060029Z-SUPPLEMENT.json:587` registra como inspeccionada la ruta
**`/home/lucas/.config/opencode/AGENTS.md`**. En el estado actual ese **fichero no existe**
(`~/.config/opencode/` contiene únicamente `service.json`). El artefacto preserva evidencia de una
configuración global de OpenCode que **ya no está**. No se repara ni se explica: `UNKNOWN` la causa.

**Ningún proceso `opencode` aparece en ninguna captura runtime** (`CAP-1`, `CAP-2`, `CAP-3`).
Que OpenCode se estuviera ejecutando en el host es `NOT_OBSERVED`; no se afirma en ningún sentido.

---

## 4 · ENTIDADES TÉCNICAS — **NO SON APLICACIONES**

| Entidad | Naturaleza | Dónde se define | `CLASS` de su existencia aquí |
|---|---|---|---|
| `struct drm_file` | objeto del núcleo, en memoria | `drm_file.h:164-391` (v6.12) | `PRIMARY_KERNEL_SOURCE`; en este host: `UNKNOWN` (contado, nunca identificado) |
| `drm-client-id` | `u64`, clave fdinfo | `drm_file.c:942-943`; spec `:64-72` | `PRIMARY_KERNEL_SOURCE`; **valor en este host `NOT_AVAILABLE`** |
| `drm-pdev` | clave fdinfo = **BDF** | `drm_file.c:948-950`; spec `:59-62` | `PRIMARY_KERNEL_SOURCE`; valor `NOT_AVAILABLE` |
| `drm_minor` | índice de nodo | `drm_file.h:77-86` | `PRIMARY_KERNEL_SOURCE`; observado como `card1`(1)/`renderD129`(129) |
| `drm_device` | driver + dispositivo | `drm_drv.h` | `PRIMARY_KERNEL_SOURCE` |
| PID / TGID | entero del núcleo | `drm_file.c:143` = `task_tgid(current)` | `OBSERVED` como PID de proceso; **el campo `drm_file.pid` no se publica** |
| FD | descriptor VFS | `/proc/<pid>/fd/<n>` | `OBSERVED` (12 en CAP-2) |
| PASID | vmid | docs de amdgpu | `SOURCE_INCOMPLETE`; **0 ocurrencias en la spec** |
| VM | — | — | `SOURCE_INCOMPLETE` |
| GEM object | objeto del núcleo | `drm_gem.h` | `SOURCE_INCOMPLETE` para exposición; `NOT_OBSERVED` en este host |
| engine | unidad de ejecución | spec `:79-137` | `NOT_OBSERVED` en este host |
| nodo DRM | entrada de `/dev` | sysfs + `minor->dev` | `OBSERVED` (`GPU_IDENTITY_STATUS = PROVEN`) |
| `driver_priv` | puntero opaco | `drm_file.h` | `NOT_EXPOSED` |
| GEM/object_idr | `idr` por `drm_file` | `drm_gem.h` | `PRIMARY_KERNEL_SOURCE`; `NOT_OBSERVED` |
| `drm_master` | ownership de nodos primarios | `drm_lease.h` | `PRIMARY_KERNEL_SOURCE`; `NOT_OBSERVED` |
| fila del fichero debugfs `clients` | **una fila = un `struct drm_file`** | `drm_debugfs.c:73-113`, `:143` | `SOURCE_LOCATED`; filas contadas: 4 (CAP-4) |

**Ninguna de estas 15 filas es una aplicación, un proceso ni un agente.**

---

## 5 · RELACIONES: `OBSERVED` vs `INFERENCE` vs `NOT_ESTABLE`

### 5.1 · `OBSERVED`

| # | Relación | Evidencia |
|---|---|---|
| R-OBS-1 | proceso `kwin_wayland` PID 1825 **poseía** los FDs `14-17`,`51-55` resueltos a `renderD129`/`card1` | CAP-2 `gpu_clients[].source = /proc/1825/fd/<n>` + `resource` |
| R-OBS-2 | proceso `Xwayland` PID 1923 poseía el FD `13` resuelto a `card1` | CAP-1 y CAP-2 |
| R-OBS-3 | esos nodos pertenecen al dispositivo `0000:01:00.0` / `amdgpu` | `identity.GPU.GPU_IDENTITY_STATUS = PROVEN` |
| R-OBS-4 | `kwin_wayland` y `Xwayland` estaban en el mismo namespace root de mnt/pid/user | CAP-2 `namespaces` idénticos |
| R-OBS-5 | el proceso `codex` 4911 y el shell del proyecto 8783 existían en CAP-3 | CAP-3 `post.processes` |
| R-OBS-6 | el fichero debugfs de `minor 129` contenía **4 filas de 715 bytes** | CAP-4 (cita textual; artefacto bruto `NOT_AVAILABLE`) |

### 5.2 · `INFERENCE` (con base y con falsificador)

| # | `INFERENCE` | Base | Falsificador |
|---|---|---|---|
| R-INF-1 | cada fila del fichero debugfs `clients` es un `struct drm_file` del RX550 | `drm_debugfs.c:92` itera `dev->filelist` de `struct drm_file`; `minor 129` → RX550 | fila que no corresponda a un `drm_file` de `dev->filelist` |
| R-INF-2 | hubo un reinicio del host entre `2026-09-25T23:16` y `2026-09-26T03:05` | PIDs 3424→1825 con tiempo creciente | PIDs monótonos entre ambas capturas |
| R-INF-3 | las **12 filas** de CAP-4 equivalen a los **12 FDs** de CAP-2 en la misma cuenta | 12 filas y 12 FDs, misma clase de GPU | recuento de filas ≠ recuento de FDs en una misma captura |
| R-INF-4 | los 4 procesos de CAP-2 son los «4 procesos» de `12 FDs en 4 procesos` | PIDs 1, 993, 1825, 1925 de CAP-2 | lista de procesos distinta en la fuente de los 12/12 |
| R-INF-5 | `Xwayland` como proceso de la RX550 es un cliente X11 *dentro* de la sesión Wayland | cmdline `--xwayland` de `kwin_wayland` | `Xwayland` arrancado fuera de la sesión de `kwin_wayland` |

**R-INF-3 y R-INF-4 están `UNVERIFIED`**: la fuente de los contadores `12/12/12` (CAP-5) es una
**cita en documentos**, y su artefacto bruto no fue localizado en esta sesión. `NOT_AVAILABLE`.

### 5.3 · Prohibiciones activas (de `R1-SEMANTIC-DECOMPOSITION-20260926.md` §7)

`FD count → client count` · `drm-client-id → proceso` · `drm-client-id → actividad` · `PASID → cliente
DRM` · `drm-pdev → identidad de cliente` · `engine activity → proceso` · `GEM object → proceso` ·
`drm-master → drm-client-id` · `drm_client_dev → propiedad del core` · `**client is active** → nada`.

### 5.4 · Ningún valor fdinfo preservado

`grep` de `drm-client-id:<valor>`, `drm-pdev:<valor>`, `pasid:<valor>` sobre todo el repositorio:
**0 coincidencias con valor**. En CAP-2 los 12 registros tienen `fdinfo: ""`. Por tanto:

- `PRESENCE` de claves: `PROJECT_DOCUMENT` (`12/12/12`), artefacto `NOT_AVAILABLE`.
- `VALUE` de `drm-client-id` / `drm-pdev` / `PASID`: **`NOT_AVAILABLE`** en todo el proyecto.
- `DISCRIMINATION` (distinguir dos `drm_file`): **`NOT_ESTABLE`** — coherente con `C-4`
  `CONFLICT_UNRESOLVED` y con el conflicto `X-1`/`X-2` ya abierto en §17 de la descomposición.
- `ATTRIBUTION` (unir `drm_file` con proceso): por vía debugfs **hay camino de núcleo**
  (`drm_debugfs.c:98-103` publica el TGID), pero **ninguna captura del proyecto lo preservó**.

---

## 6 · DIAGRAMA ASCII

Relaciones en trazo continuo = `PRIMARY_KERNEL_SOURCE` (v6.12).
`( )` = relación no establecida / `SOURCE_INCOMPLETE` / `NOT_OBSERVED` en este host.
`==>` = camino del **core** verificado en `drm_debugfs.c`.
Las tres capas superiores se mantienen **separadas**: no hay flecha entre ellas porque ninguna fuente
las une.

```
  [APLICACION DEL HOST]            [COMPONENTE DEL PROYECTO]        [AGENTE DE OPENCODE]
  kwin_wayland   (OBSERVED)        collector           (fichero)     agente primario  (OBSERVED)
  Xwayland       (OBSERVED)        runner/automator    (fichero)     explore          (OBSERVED)
  firefox-bin    (OBSERVED/Intel)  shell de captura    (PID 8783)    general          (OBSERVED)
  plasmashell    (OBSERVED/Intel)  rx550-torneo lib    (fichero)    (sin config de proyecto)
  plasma-keyboard(OBSERVED/Intel)  validador           (fichero)     ~/.config/opencode/
  xwaylandvideobr(OBSERVED/Intel)                      service.json
  nobara-welcome (OBSERVED/Intel)  codex  (PID 4911, harness, NO del proyecto)
  ChatGPT        (OBSERVED)        ---- sin datos de FD DRM en ninguna captura ---->
  systemd, systemd-logind (OBSERVED)
        |                                    |                                    |
        |  NO HAY FLECHA: ninguna fuente     |  NO HAY FLECHA: el collector     |
        |  une una aplicacion con un          |  no se registra a si mismo;      |
        |  proceso.                            |  no es cliente.                   |
        v                                    v                                    v
  [PROCESO  PID/TGID]  <---- /proc/<pid> ----    (NOT_APPLICABLE)                (NOT_OBSERVED)
   1825 kwin_wayland
   1923 Xwayland  3246 kwin_wayland  3447 Xwayland
   3424 firefox-bin (Intel)   2003 plasmashell   1910 plasma-keyboard
   2191 xwaylandvideobridge   2218 nobara-welcome  4190 ChatGPT
   1 systemd   993 systemd-logind   8783 bash(proyecto)   4911 codex
        |  OBSERVED: /proc/<pid>/fd/<n> resuelve al nodo
        v
  [FD]  14 15 16 17 -> renderD129   51 52 53 54 55 -> card1   13 -> card1   208 -> card1
       (12 FDs DRM en CAP-2, distributed en 4 procesos)
        |  INFERENCE N:1  (dup/fork)          |  NO HAY VALOR PRESERVADO
        |                                     +--> fdinfo = ""  en CAP-2
        v
  [struct file]  <- 1 descriptor [FD] referencia 1 struct file  (R-01: FD -> struct file, N:1)
        |  dup()/fork(): VARIOS [FD] -> el MISMO struct file
        |  ==> varios [FD] pueden referenciar la MISMA apertura DRM  (R-03: N:1, NO 1:1)
        v
  [struct drm_file]  1:1 con el struct file via private_data  (R-02)  --  unidad: una apertura DRM
        |                                   |   NO Observable como valor en este host
        +--> [drm-client-id]   u64, 1:1 con el drm_file   (drm_file.c:942-943; spec :64-72)
        |        unicidad: global O por dispositivo+drm-pdev   (spec :70-71)  ->  C-4 ABIERTO
        |        VALOR EN ESTE HOST: NOT_AVAILABLE
        |
        +--> [drm-pdev]   BDF del dispositivo, "solo si dev_is_pci"   (drm_file.c:948-950)
        |        NO es identidad de cliente.   VALOR: NOT_AVAILABLE
        |
        +--> [pid]    struct pid __rcu*, = task_tgid(current)   (drm_file.c:143)
        |        NO se publica en fdinfo.  PERO el core lo publica por debugfs:
        |        ==> [debugfs/dri/<minor>/clients]  una FILA por drm_file, con tgid
        |            (drm_debugfs.c:92,98-103,143)   <-- CONFIRMA que el recurso es del CORE
        |            VALOR PRESERVADO POR EL PROYECTO: NOT_AVAILABLE (solo el conteo: 4 filas)
        |        CONFLICTO ABIERTO: P-9 declara NOT_EXPOSED  ->  §17 X-1, NO aplicado
        |
        +--> [minor]  drm_minor  ->  nodo /dev/dri/{card1,renderD129}
        |        OBSERVED: minor 1 (card1), minor 129 (renderD129)
        |
        +--> [drm_device]  ->  [dispositivo PCI 0000:01:00.0, vendor 0x1002, device 0x699f, amdgpu]
        |        GPU_IDENTITY_STATUS = PROVEN   (CAP-2)
        |        ATENCION: card0 / renderD128 = OTRA GPU (i915). No la misma.
        |
        +--> [driver_priv]  puntero opaco, NO EXPUESTO
        |        contenido de amdgpu: SOURCE_INCOMPLETE
        |
        +--> [object_idr]  handles -> objetos GEM
        |        NO convierte al GEM en identidad de proceso.  NOT_OBSERVED aqui.
        |
        +--> [drm_master]  ownership de nodos primarios, TRANSFERIBLE por leasing
        |        NOT_OBSERVED aqui.
        |
        +--> (VM / PASID)   <-- SOLO SI LA RELACION ESTA ESTABLECIDA
        |        NO ESTABLECIDA.  VM: SOURCE_INCOMPLETE.
        |        PASID: 0 ocurrencias en la spec; 0 en el core v6.12; convencion de driver.
        |        Un PASID identifica un VM durante un page fault con el proceso activo.
        |        NO es drm-client-id. NO es PID. NO es identidad permanente de proceso.
        |
        +--> (GEM / MEMORIA)  <-- SOLO RELACIONES DEMOSTRADAS
        |        drm-memory-<region> (spec :143) existe; el core imprime drm-<stat>-<region>
        |        (drm_file.c:840).  ESTADO: NOT_OBSERVED en este host.
        |
        +--> (ENGINE)  <-- SOLO RELACIONES DEMOSTRADAS
                 drm-engine-<keystr>: tiempo del engine ejecutando trabajo de ESE cliente,
                 NO monotono (spec :79-89).  NO es el proceso.  NO es instantaneo.
                 ESTADO: NOT_OBSERVED / UNKNOWN.  "engine=0" NO prueba no-uso.
```

**Separación exigida, verificada**: `[APLICACION DEL HOST]`, `[COMPONENTE DEL PROYECTO]`,
`[AGENTE DE OPENCODE]` y `[ENTIDAD KERNEL/DRM]` no comparten ninguna arista. No existe en este
diagrama ninguna ruta que convierta una aplicación en un `drm_file`, ni un proceso en un
`drm-client-id`.

---

## 7 · REVISIÓN DE ERRORES DE NOMENCLATURA

**No se corrigió ninguno.** Se documenta ubicación, significado local y si contradice el modelo.

| # | Ubicación | Texto | Significado real en ese contexto | ¿Contradice el modelo? |
|---|---|---|---|---|
| N-1 | `R1-20260926T030435Z.json` → `AGENTS_OWNERSHIP_MATRIX.conditions[0].EVIDENCE` | `"card1 / 8 attributable client(s)"` | 8 **Fds**; `attributable` es el término **RETIRED** | **SÍ, dos veces**: (a) término retirado; (b) FDs contados como clientes. Artefacto histórico → `HISTORICAL_NOMENCLATURE_DEFECT`, no reescrito |
| N-2 | `OWNERSHIP-AUDIT-HOST-C-20260925T231635Z.md:74-88` | «clientes *reales*: el compositor… tiene `/proc` ilegible»; «La unica RX550 client-visible es `Xwayland`» | «cliente» = **proceso** que posee un FD | **SÍ**: un proceso no es un `drm_file`; el documento no lo distingue. Además afirma «Cero observado != cero actual», lo cual es correcto |
| N-3 | `VFIO-FEASIBILITY-AUDIT-20260925T132242Z.md:188` | «Observed clients included Xwayland, KWin-related desktop services, `ksmserver`» | «clients» = **procesos**; «KWin-related desktop services» es una **categoría**, no una identidad | **SÍ**: mezcla dos tipos (proceso individual y categoría) bajo un mismo término que el modelo técnico reserva para `struct drm_file` |
| N-4 | `R1-C1-CORRECTION-CLOSURE-20260926.md:350` | «DRM clients in debugfs … 4 client entries» | aquí «client» = una **fila del fichero = un `struct drm_file`** (por `drm_debugfs.c:92`) | **AMBIGUO, no falso**: la unidad correcta, pero la palabra evoca proceso. Debe decir «4 `drm_file`» |
| N-5 | `privileged_read_collector.py:2345, 2439, 2907` | etiquetas de veredicto `"no DRM client"` frente a `"client without a readable fdinfo"` | «client» = **proceso/tenedor** de un FD | **SÍ, internamente inconsistente con §16**: el mismo proyecto usa «client» para el tenedor del FD, mientras el core lo usa para la fila `drm_file`. Dos significados en el mismo código |
| N-6 | `privileged_read_collector.py:1094, 1128, 1602, 2846, 2907` | comentarios que separan «no DRM client» de «cliente sin fdinfo legible», y «DRM client, un PCI device y un PASID en una propiedad» | uso **correcto**: enumera confusiones a evitar | **NO** — es el modelo funcionando |
| N-7 | `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md:197` | «`renice +5 firefox` / `renice -10 kwin_wayland`» | nombre de **aplicación** usado como nombre de **proceso** | **SÍ**: el proceso observado se llama `firefox-bin`; `firefox` no fue observado como proceso. Además es un comando **previsto**, no ejecutado |
| N-8 | `DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md:655-657` | «Firefox y su relación con la GPU», `KEYWORDS: firefox` | **tema** de documentación | **NO** — no afirma observación. Correcto si se lee como índice |
| N-9 | `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md:371-372` | «"1 DRM client" (pasada A) — `REFUTED`»; «"12 clientes" — `REFUTED` como enunciado: son 12 FDs en 4 procesos» | corrección explícita FDs→clientes | **NO** — es el modelo funcionando: el error está named y refutado |
| N-10 | `R1-DRM-FDS-ENUMERATED-FIX-RECORD-20260926.md:146` | «a host with no DRM client at all» | hipótesis sobre un **proceso** | **AMBIGUO**: contradice N-4/N-5 si «client» = `drm_file` |
| N-11 | `R1-REPAIRED-...:371` y `R1-ATTRIBUTABLE-DEFINITION-RESOLUTION:189` | «12 DRM FDs, 4 procesos \| 4 procesos con ≥1 FD \| nº de clientes» | tabla que **rechaza** la conversión | **NO** |

**Síntesis**: 4 usos **contradictorios** (N-1, N-2, N-3, N-7), 3 **ambiguos** (N-4, N-5, N-10) y 4
correctos. El conflicto de mayor gravedad no es de vocabulario sino de **unidad**: N-1 y N-7 están en
la ruta que alimenta `OWNERSHIP`; N-5 está en el propio collector. **Ninguno se corrigió**: el
criterio de corrección requiere decidir la unidad normativa, y eso es
`NORMATIVE_REQUIREMENT_REWRITE = OPEN` (humano).

---

## 8 · `DECISION`

```
ACTOR_INVENTORY                = CLOSED (con CONFLICTS y LIMITACIONES declarados)
TECHNICAL_MODEL                = CLOSED   (sin cambios; P-1..P-16 intactas)
PROJECT_MAPPING                = NOT_ATTEMPTED
REQUIREMENT_INTENT_RECONSTRUCTION = NOT_ATTEMPTED
HUMAN_MIXED_TERM               = RETIRED   (no reintroducido)
NOMENCLATURE_ERRORS            = DOCUMENTED_NOT_CORRECTED  (11 hallazgos: 4 contradictorios,
                                3 ambiguos, 4 correctos)
CODE_OR_CONFIG_CHANGES         = NONE
```
