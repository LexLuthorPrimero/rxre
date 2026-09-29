# PATCH-RECOVERY-REPORT — Recuperación de parches tras restauración

**Fecha:** 2026-09-25T22:22Z
**Fase:** L1 — *localizar, reconstruir y registrar* los parches que quedaron fuera de la restauración.
**Alcance real ejecutado:** investigación de solo lectura + creación de documentación.
**No ejecutado:** modificación de kernel, Mesa, firmware, amdgpu, power cap, DPM, runtime PM,
systemd, GRUB, udev. Sin C1. Sin commit. Sin push. Sin remote. Sin reescritura de historial.
Sin borrar evidencia. Sin aplicar cambios al sistema.

Documentos de esta fase:
- `PATCH-REGISTRY-RECOVERED.md` — registro por parche (28 entradas).
- `PATCH-SOURCES.md` — procedencia, búsquedas negative y discrepancia de host.

---

## STATE

```
PATCH_RECOVERY=COMPLETO_CON_GAPS_DOCUMENTADOS
PROJECT_RESTORED=YES
PATCHES_RECOVERED=24
PATCHES_EXACT=24
PATCHES_PARTIAL=3
PATCHES_UNKNOWN=4
SYSTEM_PATCHES=13
STATIC_PATCHES=12
```

| Definicion | Valor |
|---|---|
| `PATCHES_RECOVERED` | 24 con contenido íntegro disponible (12 de proyecto + 12 de sistema/Mesa) |
| `PATCHES_EXACT` | 24 con `RECOVERED_EXACT=YES` |
| `PATCHES_PARTIAL` | 3 (`RX550-SD-02/03/04`): unidad exacta, payload ausente |
| `PATCHES_UNKNOWN` | 4 (`RX550-UNK-01` + 3 slots de categoría `NOT_AVAILABLE`) |
| `STATIC_PATCHES` | 12 (grupo A, código del proyecto) |
| `SYSTEM_PATCHES` | 13 (grupo B, artefactos de sistema; 1 `NOT_AVAILABLE`, 3 parciales) |
| Slots de categoría sin fuente | 3 (`KERNEL_PATCH`, `AMDGPU_PATCH`, `GRUB_PATCH`) |
| `NEW_DISK_APPLIED=YES` | 12 (solo grupo A, presentes en el árbol) |
| `NEW_DISK_APPLIED=NO` | 16 (todo grupo B) |
| Commits / tags / remotes creados | **0** |
| Cherry-picks intentados | **0** |
| Cambios de sistema ejecutados | **0** |

**Verificación de no-efecto:** el host vivo no tiene unidades `kalm*` (0), ni `system-autopilot*`
(0), ni `/usr/local/bin/kalm*`, ni `/opt/kalm`, ni `/opt/mesa-26.2.2-rx550-haswell`. Nada de lo
documentado en el grupo B se instaló ni se tocó.

---

## RECOVERED

### A) Proyecto (12) — presentes en el árbol, con diff exacto contra `c6146788`

| PATCH_ID | Nombre | TIPO | Recuperado |
|---|---|---|---|
| `RX550-PP-01` | Selector de GPU por `vendor:device`/BDF (elimina `DRI_PRIME=1`) | `STATIC_PROJECT_PATCH` | EXACTO |
| `RX550-PP-02` | Aislamiento RADV por ICD + higiene de selectores heredados | `STATIC_PROJECT_PATCH` | EXACTO |
| `RX550-PP-03` | Modo test M1 con estado AUX sintético (sin lectura PM en vivo) | `STATIC_PROJECT_PATCH` | EXACTO |
| `RX550-PP-04` | Tests sin topología fija + asserts de selector + skip de `strace` | `TEST_PATCH` | EXACTO |
| `RX550-PP-05` | Instrumentación de frame/present del workload (marcadores, p50/p95/p99) | `STATIC_PROJECT_PATCH` | EXACTO (binario no preservado → rebuild) |
| `RX550-PP-06` | Ruta del runner M1 tras reorganización | `STATIC_PROJECT_PATCH` | EXACTO |
| `RX550-PP-07` | Sonda H12-1 (Wayland + present timing) | `STATIC_PROJECT_PATCH` | EXACTO (revisión de build pendiente) |
| `RX550-TP-01` | Validador read-only del host | `TOOL_PATCH` | EXACTO |
| `RX550-C1-01` | Automator C1 estático + tests + colector privilegiado | `C1_PATCH` | EXACTO (nunca ejecutado) |
| `RX550-C1-02` | Observador C1 en el workload | `C1_PATCH` | EXACTO (nunca ejecutado) |
| `RX550-DP-01` | Anotación de no reproducibilidad en 4 runners históricos | `DOCUMENTATION_PATCH` | EXACTO |
| `RX550-DP-02` | Paquete documental final de release | `DOCUMENTATION_PATCH` | EXACTO |

Detalle campo por campo en `PATCH-REGISTRY-RECOVERED.md`.

### B) Sistema (13) — recuperado del backup del disco anterior, **no aplicado aquí**

| PATCH_ID | Nombre | TIPO | Recuperado |
|---|---|---|---|
| `RX550-SD-01` | `kalm-gpu.service` | `SYSTEMD_PATCH` | EXACTO |
| `RX550-SD-02` | `kalm.service` (kalmd) | `SYSTEMD_PATCH` | PARCIAL (falta `/opt/kalm/kalmd.py`) |
| `RX550-SD-03` | `kalm-cpu.service` | `SYSTEMD_PATCH` | PARCIAL (falta `kalm-cpu-apply.sh`) |
| `RX550-SD-04` | `kalm-lite.service` | `SYSTEMD_PATCH` | PARCIAL (falta `kalm-lite.py`) |
| `RX550-PM-01` | `/usr/local/bin/kalm-gpu` (cap + DPM) | `POWER_MANAGEMENT_PATCH` | EXACTO |
| `RX550-PM-02` | `rx550-power-sweep.sh` | `POWER_MANAGEMENT_PATCH` | EXACTO |
| `RX550-UD-01` | `60-kalm-bbr.rules` | `UDEV_PATCH` | EXACTO |
| `RX550-UD-02` | `60-kalm-io.rules` | `UDEV_PATCH` | EXACTO |
| `RX550-SCP-01` | `99-kalm-network.conf` | `SYSTEM_CONFIGURATION_PATCH` | EXACTO |
| `RX550-SCP-02` | `99-kalm-storage.conf` | `SYSTEM_CONFIGURATION_PATCH` | EXACTO |
| `RX550-SCP-03` | `kalm-despliegue-total.sh` (instalador) | `SYSTEM_CONFIGURATION_PATCH` | EXACTO |
| `RX550-MP-01` | Mesa `583c5d2f` — `radv: simplify address binding report logging` | `MESA_PATCH` | EXACTO (commit + `.patch` + diff hasheado) |
| `RX550-UNK-01` | `system-autopilot.{service,timer}` + `system-autopilot.sh` | `UNKNOWN` | **NO** (`NOT_AVAILABLE`) |

### Parche de Mesa recuperado con identidad completa

```
PATCH_ID:   RX550-MP-01
REPO:       /home/lucas/mesa   (fuera del repositorio del proyecto)
RAMA/BASE:  kimi-rx550-optimization  ·  mesa-26.2.2 = 3281a69a8bf
— **resuelto 2026-09-28: `RESOLVED_WRONG_OBJECT`; el valor documentado es el correcto (tipo `commit`); el otro SHA es el objeto de tag. Ver `PATCH-SOURCES.md` F12-bis / F12-ter.**
COMMIT:     583c5d2f44152ed70d6f9aff58fbca5abcf7376d
AUTOR:      Lucas <tu_email@gmail.com>
FECHA:      2026-05-19 03:48:25 -0300
FICHERO:    src/amd/vulkan/radv_debug.c   (+34 / -4)
DIFF SHA256: c10c558b35d92cc0875a176a7c3b1da9be0c275f57445946169167dc9e87d7b4
.PATCH:      src/amd/vulkan/0001-radv-simplify-address-binding-report-logging.patch
            SHA256 26fdb443cc9cdc71453e956ff605f4a5dd1fc3d8109fc92f15091cbaa66d5399 (61 lineas, untracked)
ORIGINAL_APPLIED=UNKNOWN   NEW_DISK_APPLIED=NO   SYSTEM_CHANGE_REQUIRED=SI
```

Su contenido es un **cambio de logging**, no una corrección funcional de GFX8. EP05 con Mesa
CUSTOM ya dio `NOT_REPRODUCED` para E5 y ese resultado negativo se conserva sin reinterpretar.

---

## NOT_RECOVERED

| Elemento | Estado | Qué se conserva |
|---|---|---|
| `system-autopilot.service` (contenido) | `NOT_AVAILABLE` | ruta, tamaño (115 B), prefijo `07dc247f…932d6`, `Type=oneshot`, ausencia de `[Install]`, symlink manual en `multi-user.target.wants/` |
| `system-autopilot.timer` (contenido) | `NOT_AVAILABLE` | ruta, tamaño (135 B), prefijo `16d21f1c…00e72a`, cadencia `OnBootSec=2min` + `OnUnitActiveSec=2min` |
| `/usr/local/bin/system-autopilot.sh` (contenido) | `NOT_AVAILABLE` | ruta, tamaño (1.537 B), fecha de creación `2026-05-07 11:56`, prefijo `61519cfe…0fee3ea`, efecto observado (54 ciclos/día, IRQ 39 fijada a `cc`) |
| `/opt/kalm/kalmd.py` | `NOT_AVAILABLE` | solo la línea `ExecStart` que lo invoca |
| `/usr/local/bin/kalm-cpu-apply.sh` | `NOT_AVAILABLE` | idem |
| `/usr/local/bin/kalm-lite.py` | `NOT_AVAILABLE` | idem + `Documentation=https://github.com/example/kalm` (URL de relleno) |
| Parche de kernel | `NOT_AVAILABLE` | 0 `.patch`/`.diff` de kernel/amdgpu en proyecto, backup y `/home/lucas/linux-opt` |
| Parche de amdgpu | `NOT_AVAILABLE` | `amdgpu_pm.c` sin diff ni marcador custom; el `CUSTOM` encontrado es el perfil PP estándar |
| Parche de GRUB | `NOT_AVAILABLE` | sin copia de `/etc/default/grub` ni evidencia de cmdline editada |
| Parche de firmware | `NOT_AVAILABLE` / no aplica | solo paquetes `linux-firmware` del sistema |
| Parche de VFIO | `NOT_AVAILABLE` | sin unidades ni configuración VFIO en backup ni en el host |
| Parche C1 en runtime | `NOT_AVAILABLE` por prohibición | `C1_RUNTIME_VALIDATED=NO`; existe automate estático pero nunca se ejecutó |
| Binario del workload con `RX550-PP-05` | `NOT_AVAILABLE` | excluido del índice; requiere rebuild |
| Artefactos volátiles de runners | `NOT_AVAILABLE` | `/tmp/opencode/ep05_base.txt`, `/tmp/opencode/fase_b_base.txt` — destruidos por diseño |
| Commit de parche en Git | `NO EXISTE` | 8 commits son de reorganización; reflog sin `reset`/`amend`/`cherry-pick`; 0 commits inalcanzables |

**Ningún hueco se rellenó con contenido inventado.** Los prefijos de hash de 12 hex no permiten
reconstruir y no se usan como si fueran suficiente.

---

## CLASSIFICATION

### A) PATCH DEL PROYECTO — 12 entradas

Código, scripts, runners, tests, validador y documentación del proyecto. Contenido íntegro en el
árbol. `SYSTEM_CHANGE_REQUIRED=NO` en los 12. No tocan kernel, Mesa, firmware, amdgpu, power cap,
DPM, runtime PM, systemd, GRUB ni udev.

### B) PATCH DEL SISTEMA — 13 entradas (y 3 slots vacíos)

Unidades systemd, daemon de potencia, reglas udev, sysctl, instalador y un parche de Mesa. Todos
proceden del backup del disco anterior. Todos con `NEW_DISK_APPLIED=NO` y
`SYSTEM_CHANGE_REQUIRED=SI`. **Ninguno es aplicable sin una decisión explícita de la siguiente
fase**, y la mayoría cae en dominios explícitamente prohibidos en esta fase.

### C) EVIDENCIA — NO son parches

| Artefacto | Qué demuestra | Qué **no** es |
|---|---|---|
| `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | Diseño de A/B reversible + precheck read-only | No es un parche. El propio doc dice "no se ha ejecutado ninguna desactivación" |
| `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | Estado, rutas y hashes de `system-autopilot`/`kalm` en el host viejo | No reconstruye el contenido ausente |
| `FASE-R0-3-MESA-WORKAROUNDS-POLARIS12.md` | Workarounds Mesa ya upstream | No es parche local pendiente |
| `04-IMPLEMENTACION/H12-1/README.md`, `C1-ISOLATION-DESIGN-v1.0.md` | Diseño | No es implementación validada |
| `audit-history/shell-history-rx550-kalm.txt` | Que `kalm-gpu` estuvo activo en el disco anterior | No es el parche en sí (sustenta `ORIGINAL_APPLIED`) |
| `manifest/SHA256SUMS-critical` | Integridad del backup | No es un parche |
| `ESTADO-HISTORICO-NO-UTILIZABLE.md` (2 power-sweeps) | Que esas series no son utilizables | Resultado negativo que se preserva |
| EP05 (scripts + resultados) | Que Mesa CUSTOM **no** reprodujo E5 | No es un arreglo pendiente |
| `01-AUDITORIA/FINAL-VALIDATION/*` | Estado del host a las 13:58Z | **Obsoleto respecto del host vivo** (ver BLOCK-1) |
| `PATCH-REGISTRY-FINAL.md` y resto del paquete `DP-02` | Correcciones y estado de release | Es documentación, no cambio aplicado |

### D) HIPÓTESIS — propuestas nunca aplicadas ni validadas

| Hipótesis | Estado conservado |
|---|---|
| Desactivar `system-autopilot.timer` (FASE A) | Propuesta. No ejecutada. Irrelevante aquí: la unidad no existe en el host vivo |
| Desactivar `kalm.service` (FASE B) | Propuesta. No ejecutada. Mismo caso |
| Kalm/autopilot como causa del régimen E1/E3/E5 | **No.** Conclusión histórica que se conserva: Kalm **no** explica el régimen |
| Mesa CUSTOM como arreglo de E5 | **No.** EP05 `NOT_REPRODUCED` |
| Workarounds Mesa GFX8 pendientes | **No.** `ALREADY_FIXED_UPSTREAM` |
| `power1_input` como medidor independiente | **No.** Es `W_SMU`; el etiquetado quedó `RESOLVED` |
| R-11 como corrección de host-upload | Pendiente de validación; `RX550-PP-05` aporta instrumentación, **no** prueba la corrección |
| VFIO passthrough | Bloqueado (auditoría de viabilidad) |
| Baja de clocks / RA24 | `NOT_REPRODUCED` |

---

## OPEN

1. **Verificar 12 parches de proyecto en el host vivo.** Ya no se puede asumir que los resultados
  Previos (64/64, 110/110, 54+1) describan el host actual: cambió SO, kernel, Mesa, LLVM, libdrm,
   firmware y la numeración `cardN`. Re-ejecutar en la siguiente fase.
2. **Decidir, uno por uno, los 13 parches de sistema.** Ninguno puede aplicarse sin
   autorización explícita, y `RX550-PM-01`, `RX550-PM-02`, `RX550-SCP-03` caen en territorio
   prohibido (power cap, DPM).
3. **`RX550-PP-05` y `RX550-PP-07` requieren rebuild** y revisión. El primero no tiene binario;
   el segundo son ~4692 líneas de origen no documentado en esta fase.
4. **`RX550-C1-01/02` siguen sin validación runtime.** `PROCESS_RESTORE_NOT_DEFINED` no está
   resuelto para clientes de sesión; la restauración de unidades no equivale a restauración
   verificable.
5. **Payloads faltantes de Kalm** (`kalmd.py`, `kalm-cpu-apply.sh`, `kalm-lite.py`): decidir si se
   reconstruyen o se declaran definitivamente `NOT_AVAILABLE`.
6. **`RX550-UNK-01`**: decidir si `system-autopilot` se reconstruye desde el comportamiento
   documentado o se abandona como `NOT_AVAILABLE`. Reconstrucirlo sería escribir código nuevo
   presentándolo como recuperación: no es admisible.
7. **RADV sin `mesa-vulkan-drivers` instalado** en el host vivo: re-verificar antes de cualquier
   afirmación sobre Vulkan/RADV.
8. **R-11 sobre Mesa 25.3.2** ya no aplica tal cual: el host vivo está en 26.2.3. La conclusión
   pendiente debe reformularse contra la versión real.
9. **Higiene de publicación:** 66 ficheros de texto preparados siguen conteniendo rutas personales
   absolutas (`/home/lucas`, `/root`); `SECURITY_REVIEW` sigue en `NOT_READY`.
10. **Política de historia pública:** el historial base conserva binarios, logs, dumps y rutas
    personales que se excluyeron del índice. Sin decisión.

---

## BLOCK

**BLOCK-1 — La evidencia de validación final no describe el host actual.**
`FINAL-VALIDATION-20260925T135831Z.json` dice Nobara 43 / kernel 6.18.2 / Mesa 25.3.2 / RX550 en
`card2`. El host vivo es Nobara **44** / kernel **7.1.3** / Mesa **26.2.3** / LLVM 22.1.8 /
libdrm 2.4.134 / firmware 20260810 y la RX550 está en **`card1`**. No se investigó por qué y no
se afirma ninguna causa. Consecuencia: `PATCH-REGISTRY-FINAL.md`, `PROBLEM-STATUS-FINAL.md`,
`RELEASE-CANDIDATE.md` y `FINAL-RELEASE-REPORT.md` deben tratarse como **evidencia de un estado
anterior** hasta re-ejecutar el validador. Detalle comparativo en `PATCH-SOURCES.md` §3.

**BLOCK-2 — Git no puede publicar.** No hay remote configurado. Sin `READY_FOR_GITHUB=YES`
(actualmente `NO` en `RELEASE-CANDIDATE.md`) no hay commit, tag, push ni release. Nada de esto
se ha alterado.

**BLOCK-3 — `SECURITY_REVIEW=NOT_READY`.** 66 ficheros de texto preparados contienen rutas
personales absolutas. Decisión pendiente: sanitizar o excluir.

**BLOCK-4 — Grupos B sin autorización.** Todo el grupo B requiere cambios de sistema. Las reglas
de esta fase lo prohíben. Ninguno puede marcarse "aplicable" sin una fase de decisión posterior.

**BLOCK-5 — Parches ausentes e irreconstruibles.** `RX550-UNK-01` (3 ficheros), payloads de 3
unidades Kalm, y las 3 categorías de sistema sin fuente (kernel, amdgpu, GRUB). Sin fuente, sin
objeto Git, sin volcado: `NOT_AVAILABLE` es el estado correcto y final, no un hueco a rellenar.

---

## NEXT

Secuencia propuesta. **Nada de esto se ha ejecutado.**

1. **Resolver BLOCK-1 primero.** Re-ejecutar `tools/validate_rx550_final.py` en modo solo
   lectura sobre el host vivo y emitir un nuevo `FINAL-VALIDATION-<timestamp>.json|.md`. Marcar
   el JSON anterior como histórico. Sin esto, cualquier revisión de parches hereda evidencia
   obsoleta.
2. **Revisión de parches de proyecto, uno por uno** (12 entradas), en este orden:
   `PP-01` → `PP-02` → `PP-03` → `PP-04` (se verifican juntos, comparten topología) →
   `PP-06` → `PP-05` (requiere rebuild) → `TP-01` → `PP-07` (revisión de build) →
   `C1-01`/`C1-02` (sin ejecutar) → `DP-01`/`DP-02`. Para cada uno:
   `¿aplicable tal cual? / ¿requiere adaptación? / ¿debe quedar como evidencia?`
3. **Decidir el grupo B con una pregunta por entrada**, empezando por las de riesgo alto:
   `PM-01` (kalm-gpu), `PM-02` (power-sweep), `SCP-03` (instalador), `SD-01` (`kalm-gpu.service`).
   Respuesta esperada para casi todas: *no aplicar, conservar como evidencia del sistema viejo*.
4. **Cerrar `RX550-UNK-01` y los payloads faltantes** como `NOT_AVAILABLE` definitivo, o abrir una
   fase de reconstrucción **explícitamente marcada como código nuevo** (no como recuperación).
5. **Solo después**: re-ejecutar los tests, resolver BLOCK-3 (rutas personales), revisar
   BLOCK-2 (remote) y reconsiderar `READY_FOR_GITHUB`.
6. **Nunca**: aplicar un parche de sistema "para ver qué pasa". El protocolo A/B del propio
   proyecto exige stop/start reversible, una unidad por fase y aprobación previa.

---

## EVIDENCE

Ficheros creados en esta fase (documentación, sin staging ni commit):

```
01-AUDITORIA/PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md      (este documento)
01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md
01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md
```

Estado de Git tras la fase (sin cambios respecto al inicio de la fase más los 3 ficheros nuevos):

```
rama:     main
HEAD:     c6146788e0d4fb12d9b0ec1209fa2840692de0c5   (sin cambios)
remotes:  (ninguno)
tags:     (ninguno)
stash:    (ninguno)
commits nuevos: 0
indice:   360 rutas preparadas (87 A, 139 M, 134 D) — intacto
```

Fuentes de evidencia consultadas: árbol del proyecto · `git log/reflog/for-each-ref/stash/fsck` ·
`cat-file` sobre los 197 blobs inalcanzables · backup
`~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` con su `manifest/SHA256SUMS-critical` ·
`audit-history/shell-history-rx550-kalm.txt` · repo `/home/lucas/mesa` (commit
`583c5d2f44152ed70d6f9aff58fbca5abcf7376d`) · `/home/lucas/mesa-26.2.2-build` ·
`/home/lucas/linux-opt` (búsqueda acotada de parches) · `~/.local/share/opencode` y volcados de
conversación en `~/Escritorio/` · `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` ·
`00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` · lectura en vivo de solo lectura del host
(`systemctl list-unit-files`, `rpm -q`, `uname`, `findmnt`, sysfs de `/sys/class/drm`).

Hashes completos y trazabilidad archivo por archivo: `PATCH-SOURCES.md` §4, §5, §6.
Campos por parche: `PATCH-REGISTRY-RECOVERED.md`.

---

**Fin del reporte L1. En espera. No se aplicó ningún parche.**
