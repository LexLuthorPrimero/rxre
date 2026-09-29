# PATCH-REGISTRY-RECOVERED — Registro de recuperación de parches

**Fecha de elaboracion:** 2026-09-25T22:22Z
**Alcance:** registro *de recuperacion y documentacion*. Ningun parche fue aplicado, modificado,
reconstruido en codigo ni instalado. Ningun cambio de sistema fue ejecutado.
**Relacion con `PATCH-REGISTRY-FINAL.md`:** ese documento registra el *estado final* de las
correcciones sobre el host; este documento registra *procedencia, recuperabilidad y riesgo*.
No son duplicados: Final = estado; Recovered = origen y trazabilidad.

## Esquema de identificadores

| Prefijo | TIPO | Naturaleza |
|---|---|---|
| `RX550-PP-*` | `STATIC_PROJECT_PATCH` | A — codigo/scripts del proyecto |
| `RX550-TP-*` | `TOOL_PATCH` | A — validador/metodologia |
| `RX550-C1-*` | `C1_PATCH` | A — instrumentacion C1 (solo estatica) |
| `RX550-DP-*` | `DOCUMENTATION_PATCH` | A/C — anotacion documental |
| `RX550-SD-*` | `SYSTEMD_PATCH` | B — unidad systemd |
| `RX550-PM-*` | `POWER_MANAGEMENT_PATCH` | B — power cap / DPM |
| `RX550-UD-*` | `UDEV_PATCH` | B — regla udev |
| `RX550-SCP-*` | `SYSTEM_CONFIGURATION_PATCH` | B — sysctl / instalador |
| `RX550-MP-*` | `MESA_PATCH` | B — parche de Mesa |
| `RX550-UNK-*` | `UNKNOWN` | sin fuente recuperable |
| `RX550-KP/AG/GR-*` | `KERNEL_PATCH` / `AMDGPU_PATCH` / `GRUB_PATCH` | slots sin fuente |

**Base de comparacion de los parches de proyecto:** commit base
`c6146788e0d4fb12d9b0ec1209fa2840692de0c5` (HEAD, rama `main`, unico commit con el estado
restaurado). Los parches de proyecto **no son commits**: son diferencias sin commitear en el
indice de trabajo (360 rutas preparadas, 0 commit nuevo). Por eso `AUTOR` y `FECHA_DE_COMMIT`
son `NO_REGISTRADO`; la unica marca temporal es el mtime del fichero, que se reporta aparte y
**no** se interpreta como fecha de autoria.

---

# A) PARCHES DEL PROYECTO (A)

## RX550-PP-01 — Selector de GPU por identidad (vendor:device / BDF)

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`
- **EVIDENCIA:** `git diff --cached -- 04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/state_manager.py`
- **ARCHIVOS_AFECTADOS:** `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/state_manager.py`
  (blob index `cea959980d5a21c3825654aa584f963f2fe268d1`, mtime `2026-09-25T14:16:13Z`)
- **CAMBIO_ORIGINAL:** `_mesa_status()` deja de usar el fallback `DRI_PRIME=1` y recibe
  `target_pci` / `target_bdf`; construye la lista de selectores `[vendor:device, pci-<BDF>]`;
  deja de tratar "el renderer por defecto ya es AMD" como invalidacion de la seleccion
  explicita; registra el selector efectivamente usado en `glxinfo_prime_selector`; `capture()`
  propaga el PCI/BDF detectado. Anade newline final.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (contenido integro en el arbol actual)
- **APLICABLE_AL_NUEVO_DISCO:** `YES_COMO_CODIGO` — verificado contra la topologia viva
  (2026-09-25T22:22Z): Intel `card0` / `0000:00:02.0` / `i915`, RX550 `card1` /
  `0000:01:00.0` / `amdgpu`. El codigo no depende de `cardN`.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO`. Solo lectura. Elimina una seleccion ambigua que podia apuntar a Intel.
- **VERIFICACION_REQUERIDA:** `rx550-torneo` suite (resultado registrado: 64/64). Re-ejecutar
  en la siguiente fase; no re-ejecutado en esta fase.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  (presente en el arbol del disco nuevo; validado solo por suite) · `SYSTEM_CHANGE_REQUIRED=NO`
  · `REPRODUCTION_REQUIRED=NO`

## RX550-PP-02 — Aislamiento RADV por ICD y higiene de selectores heredados

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`
- **EVIDENCIA:** `git diff --cached -- .../cap_run.py`
- **ARCHIVOS_AFECTADOS:** `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/cap_run.py`
  (blob index `33f83077f4f1650503c822a50ee1b807676a2c8c`, mtime `2026-09-25T13:56:16Z`)
- **CAMBIO_ORIGINAL:** el entorno del workload pasa de `MESA_VK_DEVICE_SELECT=1002:699f` a
  `DRI_PRIME=1002:699f` mas ICD RADV forzado; `MESA_VK_DEVICE_SELECT` y `VK_DRIVER_FILES` se
  anaden a `WORKLOAD_ENV_UNSET` para eliminar selectores heredados no fiables; comentario
  explicito de que el indice numerico no es estable.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `YES_COMO_CODIGO`. Observacion de entorno, sin conclusion de
  causalidad: el host vivo reporto `mesa-dri-drivers-26.2.3-1.fc44` y **no** tiene
  `mesa-vulkan-drivers` instalado; el mecanismo de ICD RADV debe re-verificarse antes de
  cualquier afirmacion sobre RADV.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO` (solo entorno de proceso hijo).
- **VERIFICACION_REQUERIDA:** `run_tests_m1` (resultado registrado: 110/110, `strace=NOT_AVAILABLE`).
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-PP-03 — Modo test M1 con estado AUX sintetico (sin lectura PM en vivo)

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`
- **EVIDENCIA:** `git diff --cached -- .../cap_run.py .../cli.py`
- **ARCHIVOS_AFECTADOS:**
  `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/cap_run.py` (`33f83077f4f1650503c822a50ee1b807676a2c8c`),
  `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/cli.py`
  (blob index `a651a7d2e5a6569ea4a48619ace06f7de1392741`, mtime `2026-09-25T14:16:13Z`)
- **CAMBIO_ORIGINAL:** se anaden `TEST_AUX`, `read_aux_test()` y `read_limits_test()`; las
  sesiones M1 en `test_mode` dejan de leer estado PM/DPM real de la GPU y usan estado sintetico;
  `_m1_test_session_kwargs()` propaga los readers a dry-run y a la sesion real de test.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `YES_COMO_CODIGO`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO`. Elimina dependencia de precondiciones PM en tests (origen del
  acoplamiento que hacia fallar la suite en maquinas sin el mismo estado DPM).
- **VERIFICACION_REQUERIDA:** `run_tests_m1` 110/110 registrado; re-ejecucion pendiente de fase siguiente.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-PP-04 — Tests independientes de topologia + asserts de selector + skip de strace

- **TIPO:** `TEST_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`
- **EVIDENCIA:** `git diff --cached -- .../run_tests.py .../run_tests_m1.py`
- **ARCHIVOS_AFECTADOS:**
  `04-IMPLEMENTACION/rx550-torneo/tests/run_tests.py` (blob index `e20e02dd098e56b0d9e384e71e1b4dc901b17896`, mtime `2026-09-25T14:20:25Z`),
  `04-IMPLEMENTACION/rx550-torneo/tests/run_tests_m1.py` (blob index `14e813ece2ab73d7793ca9070b0460a63d4078c7`, mtime `2026-09-25T13:56:44Z`)
- **CAMBIO_ORIGINAL:** `renderD129`/`card0`/`card1` literales pasan a regex dinamicos
  (`/renderD[0-9]+$/`, `card[0-9]+`); el driver Intel se resuelve por symlink sysfs y se exige
  `i915`; las rutas `card1/.../hwmon2/power1_cap` se reemplazan por resolucion dinamica; el test
  de `strace` pasa a `SKIP` cuando `strace` no esta instalado (no PASS, no FAIL); nuevo
  `t_workload_radv_icd_selector` con asserts G2..G6.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `YES_COMO_CODIGO` — **justificado por la topologia viva**: la
  RX550 es `card1` con `hwmon1`, mientras que los scripts historicos asumian `card1/hwmon2`
  (ver `RX550-DP-01`). La numeracion `cardN` no es estable entre estados de instalacion.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO`.
- **VERIFICACION_REQUERIDA:** 64/64 y 110/110 registrados.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-PP-05 — Instrumentacion de frame/present del workload sintetico (R-11)

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`; mtime `2026-09-24T11:16:47Z`
- **EVIDENCIA:** `git diff --cached -- 03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp`
- **ARCHIVOS_AFECTADOS:** `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp`
  (blob index `0abc168d2c1239618c425288a3f42b71415d3e31`)
- **CAMBIO_ORIGINAL (verificado en el diff):** marcadores monotónicos `emitMarker()` con
  `clock_gettime(CLOCK_MONOTONIC)`; `fatal()` y `check()` emiten marcador conservando los codigos
  de salida (`DEVICE_LOST`=2, `OOM`=4, `VULKAN_ERROR` generico); percentiles `p50/p95/p99` sobre
  frametimes ya ordenados sin interpolar (`percentileSorted`, p50 conserva el indice legacy);
  estructura `FrameRecord` con `submit`/`fence`/fin de frame; `shaderDir` vacio por defecto y
  resolucion de rutas de shader relativas a `/proc/self/exe`.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (codigo). El **binario compilado no esta
  preservado** (excluido del indice en la sesion previa): el cambio no es ejecutable tal cual.
- **APLICABLE_AL_NUEVO_DISCO:** `UNKNOWN_POR_REBUILD`. Requiere recompilar contra las cabeceras
  Vulkan/shaderc presentes en el host vivo. No se ha rebuilding ni ejecutado.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO` (build local, no sistema)
- **RIESGO:** `MEDIO` — cambia la instrumentacion de un workload historico; la semantica de
  `p50` se preserva deliberadamente, pero cualquier reinterpretacion de series antiguas con el
  nuevo codigo seria invalida.
- **VERIFICACION_REQUERIDA:** rebuild + `RESEARCH.md` del experimento debe declarar que las
  series previas fueron generadas con el binario antiguo.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` (el codigo esta
  aplicado en el arbol; si el binario llego a compilarse y ejecutarse no consta) ·
  `NEW_DISK_APPLIED=UNKNOWN` · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=YES`

## RX550-PP-06 — Correccion de ruta del runner M1 tras reorganizacion

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`; mtime `2026-09-23T21:15:30Z`
- **EVIDENCIA:** `git diff --cached -- 03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh`
- **ARCHIVOS_AFECTADOS:** `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh`
  (blob index `0065b972e6ba7c79df75fa517e4bc7dda780c10b`)
- **CAMBIO_ORIGINAL:** `ROOT` pasa de `../../rx550-torneo` a
  `../../04-IMPLEMENTACION/rx550-torneo`.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `YES_COMO_CODIGO`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO` — pero el runner **requiere root y hace 2 escrituras privilegiadas por
  corrida** (`SET` + `RESTORE`); no debe invocarse sin autorizacion.
- **VERIFICACION_REQUERIDA:** `bash -n` (sintaxis) basta para este cambio de ruta.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-PP-07 — Sonda H12-1 (Wayland/XDG-shell + present timing)

- **TIPO:** `STATIC_PROJECT_PATCH`
- **FUENTE:** indice de trabajo (sin commit); mtime `2026-09-24T09:24:16Z`
- **EVIDENCIA:** `git diff --cached --diff-filter=A` (archivos nuevos)
- **ARCHIVOS_AFECTADOS:**
  `04-IMPLEMENTACION/H12-1/src/h12_probe.c` (blob index `6e72f615123a3364726897ab502fb7eed9e7ec7c`, ~4692 lineas),
  `04-IMPLEMENTACION/H12-1/include/h12_probe.h` (blob index `e00b437af5c547b0c22ad778970c0f611ecf954f`)
- **CAMBIO_ORIGINAL:** fichero nuevo. Sonda Vulkan + Wayland/XDG-shell con `VK_KHR_present_timing`
  (dominios de present calibrados), `H12_FRAMES_IN_FLIGHT=2`, timeouts de acquire/fence y
  diagnostico de `configure`. **No es una modificacion de un fichero previo**: es codigo nuevo
  que aun no ha pasado revision de construccion.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (contenido integro) / `REVIEW_PENDIENTE`
- **APLICABLE_AL_NUEVO_DISCO:** `UNKNOWN_POR_BUILD`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO` mientras no se compile; `MEDIO` si se ejecuta (abre surface Wayland y
 sondea present timing). 4692 lineas de origen desconocido para esta fase: **no se asume
  correcto por estar staged**; la revision de construccion es un requisito previo.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=PARTIAL` (contenido integro; origen/autor no
  documentados) · `ORIGINAL_APPLIED=YES` (en el arbol) · `NEW_DISK_APPLIED=YES` ·
  `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=YES`

## RX550-TP-01 — Validador read-only del host

- **TIPO:** `TOOL_PATCH`
- **FUENTE:** indice de trabajo (sin commit); mtime `2026-09-25T13:58:47Z`
- **EVIDENCIA:** `git diff --cached --diff-filter=A -- tools/validate_rx550_final.py`;
  salida registrada en `01-AUDITORIA/FINAL-VALIDATION/`
- **ARCHIVOS_AFECTADOS:** `tools/validate_rx550_final.py` (blob index `736b7f147e0dd5922c1288e336dec7ba258a6185`)
- **CAMBIO_ORIGINAL:** herramienta nueva de solo lectura que captura identidad de GPU, kernel,
  paquetes, renderers, PM/DPM, firmware y servicios en JSON+MD.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `PARCIALMENTE` — la herramienta es reutilizable, pero **su salida
  de 2026-09-25T13:58:50Z ya no describe el host vivo** (ver seccion `DISCREPANCIA` en
  `PATCH-SOURCES.md`). Debe re-ejecutarse antes de citar cualquier dato.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO` (solo lectura por diseño; verificar que no crece a escritura).
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-C1-01 — Automator de aislamiento C1 (estatico) + tests + colector privilegiado

- **TIPO:** `C1_PATCH`
- **FUENTE:** indice de trabajo (sin commit); mtime `2026-09-25T05:43:41Z`
- **EVIDENCIA:** `git diff --cached --diff-filter=A`; revision estatica registrada en
  `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` (`RESTORE_STATIC_REVIEW=PARTIAL`,
  `C1_RUNTIME_VALIDATED=NO`)
- **ARCHIVOS_AFECTADOS:**
  `04-IMPLEMENTACION/c1_isolation_automator.py` (blob index `203191e91f72b75c360d350a4def834dc2a405a8`),
  `04-IMPLEMENTACION/tests/test_c1_isolation_automator.py` (blob index `df0ccb9aa37ccce78b40d459bb85bd2b85461998`),
  `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py` (blob index `5d8d5769d34daa9f134193fa3ba0f97f8d1095eb`)
- **CAMBIO_ORIGINAL:** ficheros nuevos. Automator con `restore_units()` y contrato de restore
  (`ABORT_RESTORE` si restore/POST no satisfactorios), mas colector de lecturas privilegiadas.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `NO_EJECUTADO_POR_PROHIBICION_EXPRESA`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` (stop/start de unidades de sesion/proceso) — **no autorizado**
- **RIESGO:** `ALTO` si se ejecuta: contract de restore definido solo a nivel de unidades, sin
  `PROCESS_RESTORE_NOT_DEFINED` resuelto para clientes de sesion.
- **VERIFICACION_REQUERIDA:** tests unitarios (54 tests, 1 skip registrados) +
  `C1_RUNTIME_VALIDATED=YES` antes de cualquier afirmacion de validity.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` (codigo en arbol) ·
  `NEW_DISK_APPLIED=NO` (nunca ejecutado aqui) · `SYSTEM_CHANGE_REQUIRED=SI` ·
  `REPRODUCTION_REQUIRED=SI`

## RX550-C1-02 — Observador C1 en el workload

- **TIPO:** `C1_PATCH`
- **FUENTE:** indice de trabajo (sin commit); mtime `2026-09-24T11:29:05Z`
- **EVIDENCIA:** `git diff --cached --diff-filter=A`
- **ARCHIVOS_AFECTADOS:** `03-EXPERIMENTOS/WORKLOAD-SINTETICO/c1_observer.py`
  (blob index `739406399fa749680fd6b995a083d7e6c5afd7eb`, 701 lineas)
- **CAMBIO_ORIGINAL:** fichero nuevo; observador de estado durante la sesion C1.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `NO_EJECUTADO_POR_PROHIBICION_EXPRESA`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO` por si mismo; depende de `RX550-C1-01`.
- **RIESGO:** `BAJO` aislado / `ALTO` en combinacion con el automator.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=PARTIAL` · `ORIGINAL_APPLIED=YES` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=SI`

## RX550-DP-01 — Anotacion de no reproducibilidad en runners historicos

- **TIPO:** `DOCUMENTATION_PATCH`
- **FUENTE:** indice de trabajo (sin commit) sobre base `c6146788`
- **EVIDENCIA:** `git diff --cached` sobre los 4 scripts
- **ARCHIVOS_AFECTADOS:**
  `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/scripts/ab-e5.sh` (`1531c1e8b9c7b3e5758488d2a39c8c3fd1dbb788`),
  `.../ab-e5-vk.sh` (`13f2c0d09bca870018a9f48bb8dc20b1d2d35733`),
  `.../env-check.sh` (`c509ca86f2c272f310dfbf62d6c1c07e7d2ae8ea`),
  `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/driver.sh` (`5bd9e0ea7fb4346bc63cc248eb9c7fe12c1c08e2`)
- **CAMBIO_ORIGINAL:** cabecera `HISTORICO / NO VERIFICABLE` declarando que
  `/tmp/opencode/ep05_base.txt` y `/tmp/opencode/fase_b_base.txt` ya no existen (artefacto volatil
  no preservado, no reconstruido) y que el script no es re-ejecutable tal cual, con la prohibicion
  explicita de sustituir por una ruta inventada. Solo comentarios + newline final.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `SI_COMO_ANOTACION`. Sin el archivo base, la anotacion es la
  correccion honesta: el runner no puede ejecutarse.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO`. Nota relevante: `driver.sh` fija `card1/device/hwmon/hwmon2`; en el host vivo
  la RX550 es `card1` con `hwmon1` → la ruta es incorrecta incluso si el base existiera.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

## RX550-DP-02 — Paquete documental final de release

- **TIPO:** `DOCUMENTATION_PATCH`
- **FUENTE:** indice de trabajo (sin commit); sesion 2026-09-25
- **EVIDENCIA:** `git diff --cached --diff-filter=A` sobre la raiz del proyecto
- **ARCHIVOS_AFECTADOS:** `README.md` (mod.), `CHANGELOG.md`, `AGENTS.md`, `.gitignore`,
  `INSTALL.md`, `ROLLBACK.md`, `TESTING.md`, `RELEASE-EXCLUSIONS.md`,
  `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md`, `RELEASE-CANDIDATE.md`,
  `FINAL-RELEASE-REPORT.md` (y el par de `01-AUDITORIA/FINAL-VALIDATION/`)
- **CAMBIO_ORIGINAL:** documentacion de instalacion/rollback/test/publicacion, matriz de
  problemas, exclusiones de release y `.gitignore`. `RELEASE-CANDIDATE.md` fija
  `READY_FOR_GITHUB=NO`.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `SI_COMO_DOCUMENTACION` — con la salvedad de que su seccion de
  host (Nobara 43 / Mesa 25.3.2) esta desactualizada respecto del host vivo.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `NO`
- **RIESGO:** `BAJO`; riesgo de **desinformacion** si se cita sin corregir la identidad de host.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` · `NEW_DISK_APPLIED=YES`
  · `SYSTEM_CHANGE_REQUIRED=NO` · `REPRODUCTION_REQUIRED=NO`

---

# B) PARCHES DEL SISTEMA (B) — presentes solo en el backup del disco anterior

**Estado comun:** `NEW_DISK_APPLIED=NO` para todos. Verificado en el host vivo (2026-09-25T22:22Z):
`systemctl list-unit-files 'kalm*'` → 0 unidades; `'system-autopilot*'` → 0 unidades;
`/usr/local/bin/kalm*` inexistente; `/opt/kalm` inexistente. **Ninguno se ha instalado aqui.**

Fuente comun: `/home/lucas/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`
(`manifest/SHA256SUMS-critical` usado como prueba de integridad; los hashes de abajo coinciden).

## RX550-SD-01 — Unidad `kalm-gpu.service`

- **TIPO:** `SYSTEMD_PATCH`
- **FUENTE:** backup `system/kalm-gpu.service` (identico a `etc/kalm-gpu.service`)
- **EVIDENCIA:** SHA-256 `beafc37afdb2cb30f7204cf45628b67da357463afaa17f1e68be7c6dd732cb9c`
  (presente en `manifest/SHA256SUMS-critical`)
- **ARCHIVOS_AFECTADOS (historicos):** `/etc/systemd/system/kalm-gpu.service`,
  payload `/usr/local/bin/kalm-gpu`
- **CAMBIO_ORIGINAL:** `Type=simple`, `ExecStart=/usr/bin/python3 /usr/local/bin/kalm-gpu`,
  `Restart=always`, `RestartSec=10`, `Nice=-5`, `ProtectSystem=full`, `ProtectHome=true`,
  `ReadWritePaths=/sys/class/drm`, `LimitNOFILE=8192`, `WantedBy=multi-user.target`.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO`. El host vivo es otra version de SO
  (Nobara 44 vs 43) y no tiene `/opt/mesa-26.2.2-rx550-haswell`; el `Nice=-5` requiere
  privilegios y el `ReadWritePaths` asume la topologia sysfs del host viejo.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `ALTO`. `Nice=-5` en un servicio que escribe sysfs puede competir con KWin/Xwayland.
- **VERIFICACION_REQUERIDA:** `systemctl cat` + hash de la unidad desplegada + pruebas de
  comportamiento GPU. No autorizada.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` (disco anterior:
  `systemctl status/stop kalm-gpu.service` en `audit-history/shell-history-rx550-kalm.txt`) ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-PM-01 — `/usr/local/bin/kalm-gpu` (gobernador termico/potencia)

- **TIPO:** `POWER_MANAGEMENT_PATCH`
- **FUENTE:** backup `system/kalm-gpu`
- **EVIDENCIA:** SHA-256 `a1e701768297195945ebe9b5fcbb431430a37b98c28481f67bf5017138d0c1bd`
  (presente en `manifest/SHA256SUMS-critical`)
- **ARCHIVOS_AFECTADOS (historicos):** `/usr/local/bin/kalm-gpu`; escribe en
  `power1_cap`, `pp_dpm_sclk`, `pp_dpm_mclk`, `pp_power_profile_mode`,
  `power_dpm_force_performance_level`
- **CAMBIO_ORIGINAL:** daemon Python con `TEMP_LOW=58` / `HIGH=70` / `CRITICAL=78` /
  `EMERGENCY=82`, `POWER_TARGET=32`, `POWER_MIN=22`, `POWER_STEP_UP=1.5`, EMA/anticipacion;
  escribe el cap de potencia y los clocks DPM con validacion de `power1_cap_max`.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `NO_AUTORIZADO_Y_NO_COMPATIBLE_SIN_REVISION`. Es exactamente el
  dominio prohibido en esta tarea (power cap / DPM).
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `ALTO`. Conclusion historica que se conserva sin alteracion: **Kalm no explica el
  regimen E1/E3/E5**; por tanto este parche no puede presentarse como causa ni como correccion
  del regimen. Si se instaló, seria un actor mas del sistema, no una solucion probada.
- **VERIFICACION_REQUERIDA:** solo dentro de un protocolo A/B aprobado (stop/start reversible).
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-SD-02 — Unidad `kalm.service` (kalmd, demonio IRQ)

- **TIPO:** `SYSTEMD_PATCH`
- **FUENTE:** backup `etc/kalm.service`
- **EVIDENCIA:** SHA-256 `69cc9644456807e04f2458e3f3f7545bb9e8efe3701b5f106127e2b5a2b18443`
- **ARCHIVOS_AFECTADOS (historicos):** `/etc/systemd/system/kalm.service`,
  payload `/opt/kalm/kalmd.py` — **payload NO presente en el backup**
- **CAMBIO_ORIGINAL:** `ExecStart=/usr/bin/python3 /opt/kalm/kalmd.py`, `Restart=always`,
  `RestartSec=5`, `WantedBy=multi-user.target`.
- **ESTADO_DE_RECUPERACION:** `PARCIAL` — unidad exacta; **cuerpo del parche `NOT_AVAILABLE`**
- **APLICABLE_AL_NUEVO_DISCO:** `NO` (unidad sin payload no es funcional)
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `ALTO` (demonio que fija afinidad IRQ).
- `RECOVERED_EXACT=YES` (unidad) · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=YES` (PID 4055
  documentado en `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md`) · `NEW_DISK_APPLIED=NO` ·
  `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI` · `PAYLOAD=NOT_AVAILABLE`

## RX550-SD-03 — Unidad `kalm-cpu.service` (afinidad IRQ CPU, oneshot)

- **TIPO:** `SYSTEMD_PATCH`
- **FUENTE:** backup `etc/kalm-cpu.service`
- **EVIDENCIA:** SHA-256 `0424fee09630143275f727965575b2d38af01b03c67f229c574b6ea07cc2e610`
- **ARCHIVOS_AFECTADOS:** `/etc/systemd/system/kalm-cpu.service`,
  payload `/usr/local/bin/kalm-cpu-apply.sh` — **payload NO presente en el backup**
- **CAMBIO_ORIGINAL:** `Type=oneshot`, `ExecStart=/bin/bash /usr/local/bin/kalm-cpu-apply.sh`,
  `RemainAfterExit=true`.
- **ESTADO_DE_RECUPERACION:** `PARCIAL` (unidad exacta, payload `NOT_AVAILABLE`)
- **APLICABLE_AL_NUEVO_DISCO:** `NO`
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` · **RIESGO:** `ALTO` (afinidad IRQ en el hilo de CPU)
- `RECOVERED_EXACT=YES` (unidad) · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI` ·
  `PAYLOAD=NOT_AVAILABLE`

## RX550-SD-04 — Unidad `kalm-lite.service`

- **TIPO:** `SYSTEMD_PATCH`
- **FUENTE:** backup `etc/kalm-lite.service`
- **EVIDENCIA:** SHA-256 `4713306df853c015ee64513d1a1703a2508d1fa5597b04985cbb75288ac52b36`
- **ARCHIVOS_AFECTADOS:** `/etc/systemd/system/kalm-lite.service`,
  payload `/usr/local/bin/kalm-lite.py` — **payload NO presente**;
  contiene `Documentation=https://github.com/example/kalm` (URL de relleno)
- **CAMBIO_ORIGINAL:** `Type=simple`, `ExecStart=/usr/bin/python3 /usr/local/bin/kalm-lite.py`,
  `Restart=on-failure`, `RestartSec=10`.
- **ESTADO_DE_RECUPERACION:** `PARCIAL` (unidad exacta, payload `NOT_AVAILABLE`)
- **APLICABLE_AL_NUEVO_DISCO:** `NO` — la `Documentation=` de relleno es en si un indicador de
  artefacto no revisado.
- `RECOVERED_EXACT=YES` (unidad) · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI` ·
  `PAYLOAD=NOT_AVAILABLE`

## RX550-UD-01 — Regla udev `60-kalm-bbr.rules`

- **TIPO:** `UDEV_PATCH`
- **FUENTE:** backup `etc/60-kalm-bbr.rules`
- **EVIDENCIA:** SHA-256 `4c254b053aed14139395ea3a016bbd860fc31cb0e4bf4f9eb59ccfeb1e7e4009`
- **ARCHIVOS_AFECTADOS (historicos):** `/etc/udev/rules.d/60-kalm-bbr.rules`
- **CAMBIO_ORIGINAL:** regla BBR preservada en el backup. Aplicacion exacta sobre el host viejo
  no reconstruible: una copia no prueba que estuviera cargada.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (contenido) · aplicacion `UNKNOWN`
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO` (depende de esquema de dispositivos del host actual)
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` · **RIESGO:** `MEDIO` (udev puede alterar I/O de bloque)
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-UD-02 — Regla udev `60-kalm-io.rules`

- **TIPO:** `UDEV_PATCH` · **FUENTE:** backup `etc/60-kalm-io.rules`
- **EVIDENCIA:** SHA-256 `dc31580adb67b3d718d1dbc69639dce7a5b9359da41eae2fa36c48fef232fc6f`
- **CAMBIO_ORIGINAL:** regla de schedulers de I/O preservada en el backup.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (contenido) · aplicacion `UNKNOWN`
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO` · **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `MEDIO`
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-SCP-01 — `99-kalm-network.conf` (sysctl)

- **TIPO:** `SYSTEM_CONFIGURATION_PATCH` · **FUENTE:** backup `etc/99-kalm-network.conf`
- **EVIDENCIA:** SHA-256 `24100bc5324f558c633de79b2edfc4d776341546ed92be68f5ac63ff67d4e0bd`
- **CAMBIO_ORIGINAL:** parametros sysctl de red (backlog, syn, buffers) preservados en el backup.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` · aplicacion `UNKNOWN`
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO` · **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `BAJO` para GPU; `MEDIO` para red general.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-SCP-02 — `99-kalm-storage.conf` (sysctl)

- **TIPO:** `SYSTEM_CONFIGURATION_PATCH` · **FUENTE:** backup `etc/99-kalm-storage.conf`
- **EVIDENCIA:** SHA-256 `c280c95a66c5b5c761a6ab0a62c4a661c0768dc5bef9306d84ac606673c015ad`
- **CAMBIO_ORIGINAL:** parametros sysctl de almacenamiento/VM preservados en el backup.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` · aplicacion `UNKNOWN`
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO` · **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` · **RIESGO:** `BAJO`
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-SCP-03 — `kalm-despliegue-total.sh` (instalador del conjunto)

- **TIPO:** `SYSTEM_CONFIGURATION_PATCH`
- **FUENTE:** backup `code/kalm-despliegue-total.sh`
- **EVIDENCIA:** SHA-256 `73f9052cc4863ccf059a141bbaf5a6fa50c299c95f3a913c2a76edb1d72fae22`;
  lineas clave: 40-41 `systemctl disable --now`, 47-56 diez `sysctl -w`, 169-185
  `cat > /etc/systemd/system/kalm-gpu.service` + `daemon-reload` + `enable --now`
- **CAMBIO_ORIGINAL:** instalador que desactiva servicios existentes, aplica 10 ajustes sysctl
  volátiles, escribe `/etc/systemd/system/kalm-gpu.service` y lo habilita.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` · **si se ejecuto tal cual: `UNKNOWN`**
- **APLICABLE_AL_NUEVO_DISCO:** `NO` — queda registrado como artefacto; su ejecucion esta
  prohibida explicitamente en esta tarea y en `ROLLBACK.md`.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` · **RIESGO:** `ALTO` — desactiva servicios del usuario y
  escribe configuracion global sin rollback atomico.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-PM-02 — `rx550-power-sweep.sh` (runner de barrido de power cap)

- **TIPO:** `POWER_MANAGEMENT_PATCH`
- **FUENTE:** backup `code/rx550-power-sweep.sh`
- **EVIDENCIA:** SHA-256 `01f331bb9f311445ac905c054941d749d03f34013d092a9bb34436a85690051a`
  (presente en `manifest/SHA256SUMS-critical`)
- **ARCHIVOS_AFECTADOS (historicos):** escribe `power1_cap` y clocks DPM; requiere root
- **CAMBIO_ORIGINAL:** recorre caps 25/28/32/35 W con restauracion por corrida. **No es una
  correccion**: es un instrumento de medicion con efectos sobre el sistema.
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES`
- **APLICABLE_AL_NUEVO_DISCO:** `NO` — proibido en esta tarea; ademas los resultados historicos
  de power-sweep estan marcados `ESTADO-HISTORICO-NO-UTILIZABLE`.
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` · **RIESGO:** `ALTO` (deja el cap alterado si se interrumpe)
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=SI` (ejecutado
  historicamente: artefactos `ESTADO-HISTORICO-NO-UTILIZABLE.md` lo corroboran) ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-MP-01 — Mesa: `radv: simplify address binding report logging`

- **TIPO:** `MESA_PATCH`
- **FUENTE (fuera del repositorio del proyecto):** repo Git `/home/lucas/mesa`,
  rama `kimi-rx550-optimization`, base `mesa-26.2.2` (`3281a69a8bf`)
- **EVIDENCIA:**
  - commit `583c5d2f44152ed70d6f9aff58fbca5abcf7376d`
  - autor `Lucas <tu_email@gmail.com>`, fecha `2026-05-19 03:48:25 -0300`
  - fichero afectado `src/amd/vulkan/radv_debug.c` (+34 / -4)
  - SHA-256 del diff (`git show --format=''`) `c10c558b35d92cc0875a176a7c3b1da9be0c275f57445946169167dc9e87d7b4`
  - fichero de parche en el arbol: `src/amd/vulkan/0001-radv-simplify-address-binding-report-logging.patch`,
    SHA-256 `26fdb443cc9cdc71453e956ff605f4a5dd1fc3d8109fc92f15091cbaa66d5399` (61 lineas), **untracked**
- **ARCHIVOS_AFECTADOS (historicos):** `src/amd/vulkan/radv_debug.c`
- **CAMBIO_ORIGINAL:** simplifica el registro de debugging de *address binding* en RADV.
  **No es una correccion funcional de GFX8**: es un cambio de logging. El experimento EP05 con
  Mesa CUSTOM no reprodujo E5 (resultado negativo que se conserva).
- **ESTADO_DE_RECUPERACION:** `RECOVERED_EXACT=YES` (commit + parche + diff hasheado)
- **APLICABLE_AL_NUEVO_DISCO:** `DESCONOCIDO`. Hechos registrados sin conclusion: el host vivo
  usa `mesa-dri-drivers-26.2.3-1.fc44`; el parche esta basado en `mesa-26.2.2`; no existe
  `/opt/mesa-26.2.2-rx550-haswell`; el repo fuente `/home/lucas/mesa` **si** esta presente.
  Aplicarlo exigiria reconstruir e instalar Mesa = prohibicion explicita ("NO modificar Mesa").
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI`
- **RIESGO:** `ALTO` (sustitucion del stack grafico del sistema) y `INUTIL` como
  "arreglo": el cambio no apunta al sintoma.
- **VERIFICACION_REQUERIDA:** ninguna disponible; EP05 ya dio `NOT_REPRODUCED` para Mesa CUSTOM.
- `RECOVERED_EXACT=YES` · `SOURCE_VERIFIED=YES` · `ORIGINAL_APPLIED=UNKNOWN` (el commit existe
  en el repo fuente; no hay prueba de que estuviera en el build historico desplegado) ·
  `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` · `REPRODUCTION_REQUIRED=SI`

## RX550-UNK-01 — `system-autopilot.service` / `.timer` / `system-autopilot.sh`

- **TIPO:** `UNKNOWN`
- **FUENTE:** ninguno. **El contenido de los tres ficheros NO se recuperó.**
- **EVIDENCIA (indirecta, documental):**
  `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` y
  `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` registran ruta, propietario, tamaño y fecha de
  cada componente, mas prefijos de hash:
  `/etc/systemd/system/system-autopilot.service` (115 B) `07dc247f…932d6`,
  `/etc/systemd/system/system-autopilot.timer` (135 B) `16d21f1c…00e72a`,
  `/usr/local/bin/system-autopilot.sh` (1.537 B, 2026-05-07 11:56) `61519cfe…0fee3ea`;
  `system-autopilot.service` **sin seccion `[Install]`** con symlink manual en
  `multi-user.target.wants/`; cadencia cada 2 min; 54 ciclos/dia; fijaba IRQ 39 a `cc`;
  documentado como "creado a mano" (root:root).
- **Búsqueda realizada sin resultado:** backup del disco anterior (no esta), arbol del proyecto
  (no esta), objetos Git (0 commits/trees inalcanzables; 0 blobs con forma de parche), historial
  de OpenCode, `.patch`/`.diff` bajo `/home/lucas` (solo 2 diffs de CI de Mesa, ajenos).
- **ESTADO_DE_RECUPERACION:** `NOT_AVAILABLE`. Solo se conservan **prefijos** de hash
  (12 hex), insufficientes para reconstruir. **No se ha inventado contenido.**
- **APLICABLE_AL_NUEVO_DISCO:** `NO_APLICABLE` — ademas no esta instalado (verificado: 0 unidades).
- **REQUIERE_CAMBIO_DE_SISTEMA:** `SI` (si alguna vez se reconstruyera) · **RIESGO:** `ALTO`
- `RECOVERED_EXACT=NO` · `SOURCE_VERIFIED=NO` · `ORIGINAL_APPLIED=YES` (activo en el disco
  anterior segun la auditoria) · `NEW_DISK_APPLIED=NO` · `SYSTEM_CHANGE_REQUIRED=SI` ·
  `REPRODUCTION_REQUIRED=SI`

---

# CATEGORIAS SIN FUENTE RECUPERABLE (slots vacios, no son parches)

| PATCH_ID | TIPO | ESTADO | Busqueda | Conclusion |
|---|---|---|---|---|
| `RX550-KP-01` | `KERNEL_PATCH` | `NOT_AVAILABLE` | `*.patch`/`*.diff` en proyecto, backup y `/home/lucas/linux-opt`; 0 resultados para kernel/amdgpu | No hay parche de kernel recuperable. Los unicos `.patch` en el backup son `rustix` de Mesa (subproyecto, ajenos). |
| `RX550-AG-01` | `AMDGPU_PATCH` | `CLOSED` — **cerrado sin parche: la busqueda ahora es concluyente** (no "parche recuperado") | **2026-09-28.** `git -C /home/lucas/linux-opt status --porcelain -- drivers/gpu/drm/amd` → **0 entradas**; `git diff -- drivers/gpu/drm/amd/pm/amdgpu_pm.c` → vacio. Arbol: Linux **7.1.0-rc1**, rama `master`, HEAD `e75a43c7c`. | No existe modificacion de amdgpu en `/home/lucas/linux-opt`. **ALCANCE LIMITADO**: solo `drivers/gpu/drm/amd`. El resto del arbol sigue `UNKNOWN`/no inspeccionado (el `git status` completo vencio por timeout; se resolvio acotando la consulta al subarbol). Ademas 0 ficheros `.patch`/`.diff` en `-maxdepth 3`. Ver `PATCH-SOURCES.md` F14. |
| `RX550-GR-01` | `GRUB_PATCH` | `NOT_AVAILABLE` | Sin copia de `/etc/default/grub` ni `grubenv` en el backup; sin evidencia de cmdline editada para la RX550 | Sin parche de GRUB recuperable ni evidencia de que existiera. |

Igual treatment para: firmware (`linux-firmware` sin parche; solo paquetes del sistema),
VFIO (ninguna unidad/configuracion), C1 runtime (nunca ejecutado: `C1_RUNTIME_VALIDATED=NO`).

---

## Resumen del registro

| Magnitud | Valor |
|---|---|
| Entradas en el registro | 28 (12 proyecto + 13 sistema + 3 slots vacios) |
| A) Parches de proyecto | 12 |
| B) Parches de sistema | 13 (de los cuales 1 `NOT_AVAILABLE`, 3 con payload ausente) |
| Slots de categoria sin fuente | 3 |
| `RECOVERED_EXACT=YES` (contenido integro disponible) | 24 |
| Recuperacion parcial (unidad exacta, payload ausente) | 3 |
| `NOT_AVAILABLE` / `UNKNOWN` | 4 (1 + 3 slots) |
| Con `NEW_DISK_APPLIED=YES` | 12 (todos de proyecto) |
| Con `NEW_DISK_APPLIED=NO` | 16 (todo B) |
| Con `SYSTEM_CHANGE_REQUIRED=SI` | 16 |
| Cherries / commits / tags / remotes creados | 0 |
| Cambios de sistema ejecutados | 0 |
