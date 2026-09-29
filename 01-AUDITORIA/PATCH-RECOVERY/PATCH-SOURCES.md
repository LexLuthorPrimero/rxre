# PATCH-SOURCES — Procedencia de cada fuente examinada

**Fecha:** 2026-09-25T22:22Z
**Proposito:** dejar constancia de *que se busco*, *donde*, *que se encontro* y *que no se
encontro*, para que la recuperacion sea auditable y repetible.
**Todas las operaciones fueron de solo lectura.** No se ejecuto `git cherry-pick`, `git commit`,
`git gc`, `git stash`, ni ninguna escritura de sistema.

---

## 1. Fuentes consultadas

| # | Fuente | Ruta / identificador | Resultado |
|---|---|---|---|
| F1 | Arbol del proyecto | `~/Escritorio/RX550-INVESTIGACION` | Proyecto restaurado presente. Indice con 360 rutas preparadas (87 A, 139 M, 134 D), 0 commit nuevo. |
| F2 | Historial de ramas | `git log --all --graph` | 8 commits, todos `lucas <lucas@local>` del 2026-09-23, todos de reorganizacion/baseline (`Baseline:`, `Grupo 00..05`, `Registro de movimientos`). **Ninguno es un commit de parche.** |
| F3 | Reflog | `git reflog --all` | 8 entradas por ref (`main` + `HEAD`), exactamente los mismos 8 commits. **Sin** `reset`, `amend`, `checkout`, `cherry-pick`, `rebase`. → ningun commit perdido por reflog. |
| F4 | Refs y tags | `git for-each-ref`, `git tag --list` | Solo `refs/heads/main`. **0 tags. 0 remotes. 0 refs de stash.** |
| F5 | Estado pendiente | `git stash list`, `.git/{MERGE_HEAD,CHERRY_PICK_HEAD,REVERT_HEAD,ORIG_HEAD,BISECT_HEAD}` | Stash vacio. Ningun fichero de operacion en curso. |
| F6 | Objetos inalcanzables | `git fsck --full --no-reflogs --unreachable` | **197 objetos, todos `blob`. 0 commits, 0 trees.** |
| F7 | Forma de los blobs | clasificacion por contenido | **0 blobs con forma de parche** (`diff --git`, `From <sha>`, `---`/`+++`, `@@`). Perfil: 115 ficheros con lenguaje de script, 81 documentos, 1 binario. Todos corresponden a generaciones previas de ficheros ya presentes en el indice. → **no hay parche perdido en Git.** |
| F8 | Busqueda de parches en el proyecto | `git ls-files` + `grep` de `PATCH/PATCHES/FIX/FIXES/CORRECTION/CORRECCIONES/MIGRATION/MIGRACION/RESTORE/ROLLBACK/CHANGELOG/RELEASE/IMPLEMENTACION/HOTFIX/WORKAROUND/MITIGATION/PARCHE` | Coincidencias solo en: `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md`, `RELEASE-CANDIDATE.md`, `FINAL-RELEASE-REPORT.md`, `INSTALL.md`, `ROLLBACK.md`, `TESTING.md`, `CHANGELOG.md`, `RELEASE-EXCLUSIONS.md`, `FASE-H-RADV-WORKAROUNDS-DESIGN.md`, `R0-3-MESA-WORKAROUNDS-POLARIS12.md`, `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md`, `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, mas directorios de resultados `fixed1/2/3`. Ningun `.patch`/`.diff` versionado. |
| F9 | Backup del disco anterior | `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` | **Fuente principal de los parches de sistema (B).** Contiene `system/`, `etc/`, `code/`, `manifest/`, `audit-history/`. |
| F10 | Integridad del backup | `manifest/SHA256SUMS-critical` | Hashes de `system/kalm-gpu`, `system/kalm-gpu.service`, `code/rx550-power-sweep.sh` **coinciden** con los ficheros presentes → el backup es coherente consigo mismo. |
| F11 | Prueba de estado del host viejo | `audit-history/shell-history-rx550-kalm.txt` | `systemctl status kalm-gpu.service`, `sudo sed -n /usr/local/bin/kalm-gpu`, `systemctl stop kalm-gpu.service` → prueba que `kalm-gpu` **estaba instalado y activo** en el disco anterior. Es la base de `ORIGINAL_APPLIED=YES` en RX550-SD-01/PM-01. |
| F12 | Repo Mesa externo | `/home/lucas/mesa` | **Reinspeccionado 2026-09-28.** Rama activa `main` @ `c5e413533f4` (2026-05-16). La rama `kimi-rx550-optimization` **existe** y esta marcada `+` (activa en **otro worktree**). El commit `583c5d2f44152ed70d6f9aff58fbca5abcf7376d` existe en esa rama lateral: `radv: simplify address binding report logging`, `src/amd/vulkan/radv_debug.c`, +34/-4. `git merge-base --is-ancestor 583c5d2f… HEAD` → **NO**: no esta en `main`. `git diff HEAD -- src/amd/vulkan/radv_debug.c` → vacio: **el parche NO esta aplicado al arbol de trabajo**. Cambio identificado como **logging, no funcional**. Ver `RX550-MP-01`. **DISCREPANCIA ABIERTA**: ver F12-bis. |
| F12-bis | Resuelto: identificadores de `mesa-26.2.2` | `/home/lucas/mesa` | **2026-09-28. `RESOLVED_WRONG_OBJECT`. YA NO ES CONTRADICCION.** Metodo: `cat-file -t`, `cat-file -p`, `rev-parse ...^{commit}`, `tag -l --format`, `merge-base --is-ancestor`. `3281a69a8bf` = tipo **`commit`** (`VERSION: bump for 26.2.2`, Eric Engestrom, 2026-09-02 17:40:02 +0200, padre `77ec9a2a16d1`). `997191be71af` = tipo **`tag`** (tag anotado `mesa-26.2.2`, tagger Eric Engestrom, creator 2026-09-02 17:52:53 +0200) cuyo contenido es literalmente `object 3281a69a8bfd9f99...` / `type commit`. `rev-parse mesa-26.2.2^{commit}` -> **`3281a69a8bf`**. **El tag NO se movio** (creatordate 12 min posterior al commit). **Conclusion: no existia contradiccion**; son dos *tipos de objeto* distintos que nombran la misma release. **El valor documentado `3281a69a8bf` es CORRECTO.** El objeto erroneo fue el mio: `rev-parse` sin `^{commit}` devuelve el objeto tag, no el commit. Ver F12-ter. |
| F12-ter | Rama y base reales del parche RADV | `/home/lucas/mesa` `583c5d2f441` | **2026-09-28. Correccion de F12.** La rama `kimi-rx550-optimization` **NO contiene el parche**: `merge-base --is-ancestor 583c5d2f441 kimi-rx550-optimization` -> no. `for-each-ref --contains 583c5d2f441` -> **`refs/heads/lexluthor/radv-binding-report-cleanup`**. Base = padre `c5e413533f461cffb98150c9d91908ea1911c589`, que **es el HEAD de `main`** (2026-05-16). Ese commit **si** es ancestro de `3281a69a8bf` (26.2.2, 2026-09-02): `main` esta en la misma linea, ~4 meses antes. `rev-list --left-right --count main...kimi-rx550-optimization` -> `0  4128`. El parche **no esta aplicado** al arbol de trabajo. |
| F13 | Arbol de build Mesa | `/home/lucas/mesa-26.2.2-build` | Presente. **No** es `/opt/mesa-26.2.2-rx550-haswell` (verificado ausente en el host vivo). |
| F14 | Fuente de kernel | `/home/lucas/linux-opt` | **Reinspeccionado 2026-09-28**, y ahora **concluyente**. Arbol: Linux **7.1.0-rc1** (`VERSION=7 PATCHLEVEL=1 SUBLEVEL=0 EXTRAVERSION=-rc1`), rama `master`, HEAD `e75a43c7c` (2026-04-29). Metodo: acotar la consulta al subarbol que interesa en vez de repetir el `git status` completo que habia vencido por timeout. `git status --porcelain -- drivers/gpu/drm/amd` → **0 entradas**; `git diff -- drivers/gpu/drm/amd/pm/amdgpu_pm.c` → vacio; 0 ficheros `.patch`/`.diff` en `-maxdepth 3`. → **`RX550-AG-01` pasa de `NOT_AVAILABLE` a `CLOSED` (cerrado sin parche)**. **ALCANCE**: unicamente `drivers/gpu/drm/amd`. El resto de `/home/lucas/linux-opt` queda `UNKNOWN` / no inspeccionado. Ademas el arbol es 7.1.0-rc1, **no** el kernel en ejecucion (7.1.3-200.nobara.fc44) ni el arbol de estudio (7.2.8). |
| F15 | Ficheros `*.patch`/`*.diff` bajo `/home/lucas` | `find -maxdepth 4` | Solo 2, ambos de CI de Mesa y ajenos al proyecto: `/home/lucas/mesa/.gitlab-ci/piglit/disable-vs_in.diff` y su copia en el arbol de build. |
| F16 | Historial OpenCode y volcados de conversacion | `~/.local/share/opencode`, `~/Escritorio/{opencode2,chatgpt,kimi,documentos1}.txt` | Coincidencias de contexto RX550/Kalm/Mesa. **Ninguna contiene el texto de un parche de sistema ausente.** Las menciones a `system-autopilot` son auditorias, no el fuente. |
| F17 | Documentacion del proyecto (00-INDICE, 01-AUDITORIA) | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | Unica fuente de `system-autopilot` (rutas, tamaños, fechas, prefijos de hash). Marcadas explicitamente como *propuesta* y *precheck read-only sin ejecutar*. |
| F18 | Estado vivo del sistema (solo lectura) | `systemctl list-unit-files`, `ls`, `rpm -q`, `findmnt`, sysfs | Base de todos los campos `NEW_DISK_APPLIED=NO` del grupo B. Detalle en §3. |

## 2. Fuentes NO consultadas (y por que)

| Fuente | Motivo |
|---|---|
| `git fsck --lost-found` / `git gc` | Escriben objetos/refs. Prohibido por las reglas de la tarea. El inventario se hizo con `fsck --unreachable` + `cat-file`, sin escritura. |
| `git cherry-pick` / `git commit` | Prohibido explicitamente. Ningun parche fue materializado en historia. |
| Contenido de `/home/lucas/linux-opt` completo | Auditoria de kernel fuera de alcance; solo se comprobo la existencia de parches. |
| Re-ejecucion de tests o del validador | Fase siguiente. Esta fase es solo de registro. |
|Cualquier lectura de `/etc` de escritura, `/sys` de escritura, GRUB, udev | Sin autorizacion. No se toco nada. |

---

## 3. DISCREPANCIA CRITICA — La evidencia existente no describe el host vivo

**Este es el hallazgo mas relevante de la fase y no puede ignorarse.**

`01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json` (generado
`2026-09-25T13:58:50Z`) registra el host como Nobara **43** / kernel `6.18.2-200.nobara.fc43` /
Mesa **25.3.2** / LLVM `21.1.7` / libdrm `2.4.128` / firmware `20251125`, con la RX550 en
`card2`.

Lectura en vivo del host a las `2026-09-25T22:22:08Z`:

| Elemento | Evidencia registrada (13:58Z) | Host vivo (22:22Z) | ¿Coincide? |
|---|---|---|---|
| SO | Nobara **43** | Nobara **44** (KDE Plasma, `PLATFORM_ID=platform:f44`) | **NO** |
| Kernel | `6.18.2-200.nobara.fc43.x86_64` | `7.1.3-200.nobara.fc44.x86_64` | **NO** |
| Mesa (dri) | `25.3.2-2.fc43` | `26.2.3-1.fc44` | **NO** |
| LLVM | `21.1.7-1.fc43` | `22.1.8-4.fc44` | **NO** |
| libdrm | `2.4.128-3.fc43` | `2.4.134-1.fc44` | **NO** |
| linux-firmware | `20251125-1.fc43` | `20260810-1.fc44` | **NO** |
| RX550 `cardN` | `card2` | `card1` (Intel pasa a ser `card0`) | **NO** |
| RX550 render node | `/dev/dri/renderD129` | `/dev/dri/renderD129` | SI |
| RX550 PCI / BDF / driver | `1002:699f` / `0000:01:00.0` / `amdgpu` | identico | SI |
| RX550 hwmon | `hwmon1` | `hwmon1` | SI |
| `mesa-vulkan-drivers` | instalado | **no instalado** | **NO** |
| `/opt/mesa-26.2.2-rx550-haswell` | referenciado por codigo | **ausente** | **NO** |
| Unidades `kalm*` | n/a (nunca habia estado aqui) | **0** | — |
| Unidades `system-autopilot*` | n/a | **0** | — |
| Raiz | `/dev/sdb3 ext4` | `/dev/sdb3 ext4` | SI |

**Lectura correcta (sin inferir causa):** el host actual **no coincide** con el host que genero
la evidencia de validacion final. Las causas posibles (actualizacion de SO entre sesiones,
restauracion sobre un estado distinto, host distinto) **no se investigan ni se afirman aqui**.
Lo que si es verificable:

1. Cualquier afirmacion de la sesion previa que dependa de la version de SO, kernel, Mesa, LLVM,
   libdrm, firmware o de la numeracion `cardN` **queda sin verificar para el host actual**.
2. `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md`, `RELEASE-CANDIDATE.md` y
   `FINAL-RELEASE-REPORT.md` contienen el bloque de host de esa evidencia: deben marcarse como
   *evidencia de un estado anterior* antes de cualquier publicacion.
3. `RX550-MP-01` (parche de Mesa) queda aún más lejos de ser aplicable: el sistema usa ahora
   `26.2.3` mientras el parche está basado en `mesa-26.2.2`.
4. La numeración `cardN` cambió de `card2` a `card1`, lo que **confirma empíricamente** que los
   scripts y tests con `cardN`/`hwmonN` literales no son portables — y respalda
   `RX550-PP-01`/`RX550-PP-04` como dirección correcta (no como parche ya validado).
5. `mesa-vulkan-drivers` **no esta instalado** en el host vivo: cualquier conclusion previa que
   dependiera de RADV debe re-verificarse. El validador si habia reportado `deviceID=0x699f` con
   ICD AMD aislada; eso no se re-verifico en esta fase.

---

## 4. Trazabilidad de los parches de proyecto (base → estado actual)

Todos contra `c6146788e0d4fb12d9b0ec1209fa2840692de0c5`. Sin commit: el "cambio original" vive
únicamente en `git diff --cached` y en los blobs del indice citados en el registro.

| Fichero | Blob indice | mtime (UTC) | Parche |
|---|---|---|---|
| `.../rx550_torneo/state_manager.py` | `cea959980d5a21c3825654aa584f963f2fe268d1` | 2026-09-25T14:16:13Z | RX550-PP-01 |
| `.../rx550_torneo/cap_run.py` | `33f83077f4f1650503c822a50ee1b807676a2c8c` | 2026-09-25T13:56:16Z | RX550-PP-02, RX550-PP-03 |
| `.../rx550_torneo/cli.py` | `a651a7d2e5a6569ea4a48619ace06f7de1392741` | 2026-09-25T14:16:13Z | RX550-PP-03 |
| `.../tests/run_tests.py` | `e20e02dd098e56b0d9e384e71e1b4dc901b17896` | 2026-09-25T14:20:25Z | RX550-PP-04 |
| `.../tests/run_tests_m1.py` | `14e813ece2ab73d7793ca9070b0460a63d4078c7` | 2026-09-25T13:56:44Z | RX550-PP-04 |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp` | `0abc168d2c1239618c425288a3f42b71415d3e31` | 2026-09-24T11:16:47Z | RX550-PP-05 |
| `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh` | `0065b972e6ba7c79df75fa517e4bc7dda780c10b` | 2026-09-23T21:15:30Z | RX550-PP-06 |
| `04-IMPLEMENTACION/H12-1/src/h12_probe.c` | `6e72f615123a3364726897ab502fb7eed9e7ec7c` | 2026-09-24T09:24:16Z | RX550-PP-07 |
| `04-IMPLEMENTACION/H12-1/include/h12_probe.h` | `e00b437af5c547b0c22ad778970c0f611ecf954f` | 2026-09-24T09:24:16Z | RX550-PP-07 |
| `04-IMPLEMENTACION/c1_isolation_automator.py` | `203191e91f72b75c360d350a4def834dc2a405a8` | 2026-09-25T05:43:41Z | RX550-C1-01 |
| `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py` | `df0ccb9aa37ccce78b40d459bb85bd2b85461998` | 2026-09-25T13:56:16Z | RX550-C1-01 |
| `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py` | `5d8d5769d34daa9f134193fa3ba0f97f8d1095eb` | 2026-09-25T13:56:16Z | RX550-C1-01 |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/c1_observer.py` | `739406399fa749680fd6b995a083d7e6c5afd7eb` | 2026-09-24T11:29:05Z | RX550-C1-02 |
| `tools/validate_rx550_final.py` | `736b7f147e0dd5922c1288e336dec7ba258a6185` | 2026-09-25T13:58:47Z | RX550-TP-01 |
| `.../ep05.../scripts/ab-e5.sh` | `1531c1e8b9c7b3e5758488d2a39c8c3fd1dbb788` | — | RX550-DP-01 |
| `.../ep05.../scripts/ab-e5-vk.sh` | `13f2c0d09bca870018a9f48bb8dc20b1d2d35733` | — | RX550-DP-01 |
| `.../ep05.../scripts/env-check.sh` | `c509ca86f2c272f310dfbf62d6c1c07e7d2ae8ea` | — | RX550-DP-01 |
| `.../fase-b-cap-probe.../driver.sh` | `5bd9e0ea7fb4346bc63cc248eb9c7fe12c1c08e2` | — | RX550-DP-01 |

`mtime` es marca de sistema de ficheros de la sesion de trabajo. **No es fecha de autoria** y no
se usa como tal.

## 5. Trazabilidad de los parches de sistema (backup → hash)

Base: `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`

| Artefacto | SHA-256 | En `SHA256SUMS-critical` | Parche |
|---|---|---|---|
| `system/kalm-gpu` | `a1e701768297195945ebe9b5fcbb431430a37b98c28481f67bf5017138d0c1bd` | si | RX550-PM-01 |
| `system/kalm-gpu.service` | `beafc37afdb2cb30f7204cf45628b67da357463afaa17f1e68be7c6dd732cb9c` | si | RX550-SD-01 |
| `etc/kalm.service` | `69cc9644456807e04f2458e3f3f7545bb9e8efe3701b5f106127e2b5a2b18443` | no | RX550-SD-02 |
| `etc/kalm-cpu.service` | `0424fee09630143275f727965575b2d38af01b03c67f229c574b6ea07cc2e610` | no | RX550-SD-03 |
| `etc/kalm-lite.service` | `4713306df853c015ee64513d1a1703a2508d1fa5597b04985cbb75288ac52b36` | no | RX550-SD-04 |
| `etc/60-kalm-bbr.rules` | `4c254b053aed14139395ea3a016bbd860fc31cb0e4bf4f9eb59ccfeb1e7e4009` | no | RX550-UD-01 |
| `etc/60-kalm-io.rules` | `dc31580adb67b3d718d1dbc69639dce7a5b9359da41eae2fa36c48fef232fc6f` | no | RX550-UD-02 |
| `etc/99-kalm-network.conf` | `24100bc5324f558c633de79b2edfc4d776341546ed92be68f5ac63ff67d4e0bd` | no | RX550-SCP-01 |
| `etc/99-kalm-storage.conf` | `c280c95a66c5b5c761a6ab0a62c4a661c0768dc5bef9306d84ac606673c015ad` | no | RX550-SCP-02 |
| `code/kalm-despliegue-total.sh` | `73f9052cc4863ccf059a141bbaf5a6fa50c299c95f3a913c2a76edb1d72fae22` | no | RX550-SCP-03 |
| `code/rx550-power-sweep.sh` | `01f331bb9f311445ac905c054941d749d03f34013d092a9bb34436a85690051a` | si | RX550-PM-02 |

Mesa (fuera del backup): commit `583c5d2f44152ed70d6f9aff58fbca5abcf7376d`, diff
`c10c558b35d92cc0875a176a7c3b1da9be0c275f57445946169167dc9e87d7b4`, fichero `.patch`
`26fdb443cc9cdc71453e956ff605f4a5dd1fc3d8109fc92f15091cbaa66d5399`. → RX550-MP-01.

## 6. Objetos Git inalcanzables (inventario, sin escribir)

`git fsck --full --no-reflogs --unreachable` → 197 blobs, 0 commits, 0 trees. Ninguno con forma de
parche. Perfil de contenido: 115 con lenguaje de script (Python/Bash/MD con comandos), 81
documentos, 1 binario. Corresponden a generaciones previas de ficheros ya presentes en el
indice (p. ej. versiones anteriores de `state_manager.py`, `cap_run.py`, `cli.py`, los runners de
EP05, `h12_probe.c`, documentos de auditoria). **No se copiaron al proyecto**: no hay un parche
perdido que conservar, y copiar 197 blobs habria inflado el arbol sin valor probatorio. Se deja
constancia de los hashes aqui y en el reporte para que cualquier revisor pueda repetir la
clasificacion con `git cat-file`.

Recomendacion para la siguiente fase: antes de publicar, ejecutar `git gc` **solo** si se decide
que el indice no debe seguir generating blobs huerfanos; hoy no es necesario y no se hizo.

## 7. Reglas de recuperacion respetadas

1. No se reconstruyo contenido ausente: `RX550-UNK-01` queda `NOT_AVAILABLE` con solo prefijos de hash.
2. No sealed historia: 0 commits, 0 tags, 0 remotes, 0 rewrites. `HEAD` sigue en `c6146788...`.
3. No se sustituyo un fichero actual por uno historico: los scripts EP05/fase-B solo recibieron
   comentario (RX550-DP-01), su contenido sigue igual.
4. No se aplico ni se probo nada: todo `REPRODUCTION_REQUIRED=SI` sigue pendiente.
5. La discrepancia de host (§3) se documenta; no se "corrige" reescribiendo evidencia previa.

---

# 8. TRABAJO PREVIO DE MODIFICACION DEL DRIVER (2026-09-28)

## `DRIVER_MODIFICATION_PRIOR_WORK = NOT_FOUND`

**Alcance de la afirmacion.** No se encontro trabajo previo de modificacion del
driver. El futuro driver RX550 parte de **investigacion del codigo existente**,
no de una implementacion modificada previa que haya que reconciliar.

**Limitacion que se conserva explicitamente.** Esto **NO** demuestra que todo
`/home/lucas/linux-opt` este limpio: solo `drivers/gpu/drm/amd` fue
verificado contra su `HEAD`. El resto de ese arbol queda
`UNKNOWN`/no inspeccionado. Tampoco cubre ningun otro arbol de la maquina.

## Clasificacion de los artefactos existentes

| artefacto | ubicacion | que es | es modificacion del driver? |
|---|---|---|---|
| modulo educativo `polaris12xl` | `RESEARCH/polaris12xl/`, compilado en `RESEARCH/kernelbuild/` | 10 ficheros en `core/`, **inerte por construccion**: sin `pci_driver`, sin `drm_driver`, no puede enlazar ni tocar el dispositivo | **NO** |
| parche Mesa `RX550-MP-01` | commit `583c5d2f441…`, rama `kimi-rx550-optimization` | `radv_debug.c` +34/-4, **logging, no funcional**; **no aplicado** al arbol `main` | **NO** |
| daemons historicos | `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` | `kalm-gpu` y unidades `kalm*`/`system-autopilot*` del **host antiguo**; 0 unidades en el host vivo | **NO** (userspace, y ademas de otro host) |
| scripts de medicion | `04-IMPLEMENTACION/rx550-torneo/`, `RX550-PP-01..07`, `RX550-TP-01`, `RX550-DP-01/02` | arneses de recurrencia, validadores y comentados | **NO** |
| arbol de kernel | `/home/lucas/linux-opt` | Linux 7.1.0-rc1, `drivers/gpu/drm/amd` limpio | **NO** |

**Conclusion:** no existe una implementacion modificada previa del driver que
heredar. Si existe la investigacion que la precede.

## Nota de disponibilidad: debugfs

`/sys/kernel/debug` **existe** (`debugfs` montado, `rw,nosuid,nodev,noexec,relatime`).
Su contenido **no es observable en esta sesion**: `/sys/kernel/debug` tiene modo
`drwx------` y duenio `root`, y el acceso devuelve `Permiso denegado`.

Estado: **`NOT_AVAILABLE_BY_PERMISSION`**. **No** es `ABSENT`, **no** es
`EMPTY`, **no** es `NOT_SUPPORTED`. No se intenta sortear el bloqueo de `sudo`.

## Fichero excluido

`~/Descargas/github-recovery-codes.txt` — **no volver a intentar leerlo**. No es
relevante para el proyecto. La regla ya consta en `AGENTS.md` (§4.7, §4.8.1) y
**no se modifica `AGENTS.md`** en esta sesion: su edicion requiere
autorizacion explicita (LIII) y la regla ya es correcta.
