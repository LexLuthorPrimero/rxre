# DOCUMENTATION-TOPICS — Vocabulario de temas y rutas de búsqueda

**Fecha:** 2026-09-25T22:40Z
**Estado:** FASE 0. Este fichero **no es** el router. Solo registra qué fuente respondería a cada
pregunta, para que el router se diseñe después sobre datos reales.

## Cómo leer este fichero

Cada bloque de tema declara:

- `PRIMARY_SOURCE` — lo que se debería abrir primero.
- `SECONDARY_SOURCES` — solo si el primario no alcanza.
- `RAW_EVIDENCE` — el artefacto original, con su ruta de contexto.
- `KNOWN_CONFLICTS` — discrepancias que el lector debe conocer antes de concluir.
- `STATUS` — `CURRENT` / `HISTORICAL` / `MIXED` / `CONFLICT` / `NO_PRIMARY`.

Regla de escalada aplicada en todo el documento:

```
UNKNOWN  -> no hay fuente; registrar NOT_AVAILABLE y parar
CONFLICT -> hay dos fuentes que discrepan; devolver AMBAS, no elegir
NOT_AVAILABLE -> la fuente deberia existir y no esta
```

---

## 0. Vocabulario

57 temas exigidos, más los 11 descubiertos. `n` = número de documentos redactados que mencionan
el tema.

| Tema solicitado | n | Primario |
|---|---:|---|
| RX550 | 191 | Sí |
| GPU | 188 | Sí |
| POLARIS12 | 143 | Sí |
| GFX8 | 115 | Sí |
| AMDGPU | 98 | Sí |
| PCI | 88 | Sí |
| VRAM | 98 | Sí |
| DPM | 128 | Sí |
| SCLK | 100 | Sí |
| MCLK | 103 | Sí |
| POWER_CAP | 80 | Sí |
| RUNTIME_PM | 43 | Sí |
| BACO | 8 | **NO** |
| MESA | 149 | Sí (en conflicto) |
| RADV | 99 | Sí |
| VULKAN | 116 | Sí |
| OPENGL | 53 | Sí |
| WAYLAND | 54 | Sí |
| KWIN | 26 | Sí |
| XWAYLAND | 32 | Sí |
| INTEL_GPU | 68 | Sí |
| DRM | 61 | Sí |
| IOMMU | 4 | Sí |
| VFIO | 14 | Sí |
| C1 | 68 | Sí |
| OWNERSHIP | 60 | Sí |
| RECOVERY | 88 | Sí |
| TTY | 21 | Sí |
| SYSTEMD | 112 | Solo histórica |
| GRUB | 34 | **NO** (solo prohibición) |
| UDEV | 11 | **NO** (solo prohibición) |
| HDD | 20 | Sí (histórica) |
| STORAGE | 56 | Sí (histórica) |
| BTRFS | 25 | En conflicto |
| SMART | 15 | Sí (histórica) |
| IO | 37 | Sí (histórica) |
| PSI | 17 | Sí (histórica) |
| D_STATE | 16 | Sí (histórica) |
| KERNEL | 137 | Solo histórica |
| FIRMWARE | 41 | Sí |
| FIREFOX | 5 | **NO** |
| EXPERIMENTS | 169 | Sí |
| BENCHMARKS | 115 | Sí |
| SUPERPOSITION | 56 | Sí |
| GLMARK2 | 6 | Sí |
| M1 | 70 | Sí |
| R4B | 42 | Sí |
| R4C | 26 | Sí |
| PATCHES | 68 | Sí |
| RELEASE | 17 | Sí |
| GITHUB | 27 | Sí |
| SECURITY | 60 | Sí |
| REPRODUCIBILITY | 99 | Sí |

**Descubiertos durante el censo:**

| Tema descubierto | n | Primario | Nota |
|---|---:|---|---|
| KALM | 95 | No | Daemon que existió en el disco viejo. El host actual no lo tiene. |
| AUTOPILOT | 31 | No | `system-autopilot.timer`, idem. Contenido `NOT_AVAILABLE`. |
| GOVERNOR | 74 | Sí | Governor de CPU, no de GPU. |
| IRQ | 31 | Sí | Afinidad IRQ, disk viejo. |
| TELEMETRY | 124 | Sí | Esquemas y clasificación A/B/C/D. |
| COUNTERS | 97 | Sí | Performance counters GFX8. |
| SMU | 51 | Sí | `W_SMU` vs medidor independiente. |
| FRAME | 104 | Sí | Frametime, jitter, stutter. |
| WSI | 26 | Sí | Wayland/xdg-shell/Vulkan WSI, H12. |
| HOST_IDENTITY | 31 | Sí | SO/kernel/Mesa/Pci de la máquina. |
| RESET | 34 | Sí | Ring timeout, GPU reset, RA24. |
| OPENCODE | 34 | Sí | Instrucciones de agente. |
| BACKGROUND | — | Sí | Procesos en segundo plano. |
| PROJECT_STATUS | — | Sí | Estado global. |
| DOCUMENTATION_MAP | — | En conflicto | Los mapas se marcan no vivos. |

---

## 1. Estado del proyecto y publication

### TOPIC=PROJECT_STATUS
- **DESCRIPTION:** ¿En qué punto está el proyecto y qué es verdad hoy?
- **PRIMARY_SOURCE:** `README.md` (3.9 KB, 89 líneas, 12 enlaces salientes, 1 entrante)
- **SECONDARY_SOURCES:** `PROBLEM-STATUS-FINAL.md` · `RELEASE-CANDIDATE.md` ·
  `FINAL-RELEASE-REPORT.md` · `CHANGELOG.md`
- **RAW_EVIDENCE:** —
- **KEYWORDS:** estado actual, consolidacion, ready_for_github, consolidation, release
- **KNOWN_CONFLICTS:** `MASTER-RESEARCH-STATUS.md` se autocallifica "punto único de entrada" pero
  su overlay delega el estado en los 4 documentos de la raíz. Tiene 30 referencias entrantes
  frente a 15+14+11+11 de los cuatro. Empezar por él entrega estado histórico.
- **STATUS:** `CURRENT`
- **ESCALATION_CONDITION:** si la pregunta es "¿por qué el maestro y la raíz discrepan?", leer
  `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md`.

### TOPIC=RELEASE
- **DESCRIPTION:** ¿Se puede publicar? ¿Qué gates faltan? ¿Qué no se debe subir?
- **PRIMARY_SOURCE:** `RELEASE-CANDIDATE.md`
- **SECONDARY_SOURCES:** `FINAL-RELEASE-REPORT.md` · `RELEASE-EXCLUSIONS.md` · `README.md`
- **KEYWORDS:** release, publicacion, github, gates, ready_for_github, exclusiones, secrets
- **KNOWN_CONFLICTS:** `READY_FOR_GITHUB=NO` en `RELEASE-CANDIDATE.md`. Sin remote configurado.
- **STATUS:** `CURRENT`

### TOPIC=GITHUB
- **DESCRIPTION:** Estado de publicación en GitHub.
- **PRIMARY_SOURCE:** `RELEASE-CANDIDATE.md` (7 refs) · `FINAL-RELEASE-REPORT.md` (7)
- **SECONDARY_SOURCES:** `INSTALL.md` (5) · `RELEASE-EXCLUSIONS.md` (2)
- **KNOWN_CONFLICTS:** No hay remote. No se inventó URL. `SECURITY_REVIEW=NOT_READY` (66 ficheros
  con rutas personales).
- **STATUS:** `CURRENT`

### TOPIC=SECURITY
- **DESCRIPTION:** Qué está prohibido, qué no se publica, revisión de secretos.
- **PRIMARY_SOURCE:** `AGENTS.md` (reglas del agente) + `RELEASE-EXCLUSIONS.md` (política de publicación)
- **SECONDARY_SOURCES:** `README.md` §Reglas de seguridad · `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md`
- **KEYWORDS:** seguridad, secretos, prohibiciones, no tocar, authorization
- **STATUS:** `CURRENT` (política) + `HISTORICAL` (evidencia de auditoría)

---

## 2. Parches y correcciones

### TOPIC=PATCHES
- **DESCRIPTION:** ¿Qué correcciones existen, de dónde vinieron, son recuperables?
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` (29 KB, 14 entrantes) — registro de correcciones con hashes
- **SECONDARY_SOURCES:** `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` — 28 entradas con
  `RECOVERED_EXACT`, riesgo, aplicabilidad
- **THIRD:** `01-AUDITORIA/PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md` (informe L1) ·
  `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` (procedencia y discrepancia de host)
- **RAW_EVIDENCE:** hashes SHA-256 de los artefactos; repo externo `/home/lucas/mesa` commit
  `583c5d2f44152ed70d6f9aff58fbca5abcf7376d`
- **KEYWORDS:** patch, correccion, fix, workaround, hotfix, migracion, recuperacion, rollback
- **KNOWN_CONFLICTS:** Dos registros con alcances distintos — `PATCH-REGISTRY-FINAL` = estado de
  las correcciones; `PATCH-REGISTRY-RECOVERED` = procedencia y recuperabilidad. No son duplicados.
- **STATUS:** `CURRENT`

### TOPIC=ROLLBACK
- **DESCRIPTION:** Cómo revertir sin cambios persistentes.
- **PRIMARY_SOURCE:** `ROLLBACK.md`
- **SECONDARY_SOURCES:** `PATCH-REGISTRY-FINAL.md` (rollback por corrección) · `C1-ISOLATION-DESIGN-v1.0.md`
- **KEYWORDS:** rollback, revertir, restaurar, undo, seguro
- **KNOWN_CONFLICTS:** `ROLLBACK.md` avisa explícitamente de **no** restaurar el backup histórico
  sobre la instalación actual: contiene Nobara 44 / kernel 7.2.x / Mesa 26.2.2.
- **STATUS:** `CURRENT`

### TOPIC=INSTALLATION
- **DESCRIPTION:** Requisitos, paquetes, selectores de dispositivo.
- **PRIMARY_SOURCE:** `INSTALL.md`
- **SECONDARY_SOURCES:** `TESTING.md` · `ROLLBACK.md` · `README.md`
- **KEYWORDS:** instalacion, paquetes, dri_prime, selector, requisitos, versiones
- **KNOWN_CONFLICTS:** `INSTALL.md` describe Nobara 43 / Mesa 25.3.2; el host vivo es
  Nobara 44 / Mesa 26.2.3. `SECURITY_REVIEW=NOT_READY`.
- **STATUS:** `CURRENT` con host obsoleto

---

## 3. Host, kernel, GPU

### TOPIC=HOST_IDENTITY
- **DESCRIPTION:** ¿Qué SO, kernel, Mesa, paquetes y GPU tiene la máquina ahora?
- **PRIMARY_SOURCE:** **`tools/validate_rx550_final.py`** ejecutado (read-only) — es la única forma
  de obtener un dato vigente. Documentado en `README.md` §Reproducir la validación.
- **SECONDARY_SOURCES:** `01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md` §3 (tabla comparativa
  de las tres identidades de host) · `PATCH-REGISTRY-FINAL.md` §versiones
- **RAW_EVIDENCE:** `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json`
  (SHA-256 `0fea12f9…e7e1cb`) — **captura obsoleta**, describe Nobara 43 / kernel 6.18.2 /
  Mesa 25.3.2 / RX550 en `card2`; el host vivo es Nobara 44 / kernel 7.1.3 / Mesa 26.2.3 /
  RX550 en `card1`.
- **KEYWORDS:** host identity, so, kernel, uname, mesa, llvm, libdrm, firmware, os_release
- **KNOWN_CONFLICTS:** **Tres identidades de host distintas** conviven en la documentación. Ver
  `DOCUMENTATION-CENSUS.md` §5 y `DOCUMENTATION-GAPS.md` §1.
- **STATUS:** `CONFLICT`

### TOPIC=RX550 / GPU / POLARIS12 / GFX8
- **DESCRIPTION:** Identidad, arquitectura y capacidades de la GPU objetivo.
- **PRIMARY_SOURCE:** `02-ARQUITECTURA/knowledge.md` (identidad, energía, Mesa, ASIC/counters)
- **SECONDARY_SOURCES:** `02-ARQUITECTURA/POLARIS12-MAP/POLARIS12-MAP.md` ·
  `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-4-ARCHITECTURE-LEXA-POLARIS12.md`
- **THIRD:** `02-ARQUITECTURA/POLARIS12-MAP/UNVERIFIED-CLAIMS.md` (claims no verificados)
- **KEYWORDS:** polaris12, gfx8, lexa, 8 CU, navi, identity, 1002:699f, 0000:01:00.0
- **KNOWN_CONFLICTS:** `knowledge.md` declara kernel `7.2.4`; el host vivo es `7.1.3`.
- **STATUS:** `MIXED` (arquitectura estable, valores de host obsoletos)

### TOPIC=AMDGPU / DRM / KERNEL / FIRMWARE
- **DESCRIPTION:** Driver, subsistema DRM, versiones.
- **PRIMARY_SOURCE:** `02-ARQUITECTURA/knowledge.md`
- **SECONDARY_SOURCES:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` ·
  `02-ARQUITECTURA/POLARIS12-MAP/SOFTWARE-CAPABILITIES.md`
- **KEYWORDS:** amdgpu, drm, kernel, firmware, amdgpu-firmware, vbios, ppfeaturemask
- **KNOWN_CONFLICTS:** `P0-EXPERIMENTAL-VALIDITY-GATE` (fc44 `7.2.6`) vs `knowledge.md`
  (fc44 `7.2.4`) vs host vivo (fc44 `7.1.3`). Registrado como CONFLICT en el propio gate.
- **STATUS:** `MIXED`

### TOPIC=PCI / VRAM
- **DESCRIPTION:** Enlace PCIe, anchura de VRAM, GTT.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`
  (enlace Gen2x4 VERIFIED, PCIe teórico DERIVED, VRAM ESTIMATED, real `UNKNOWN`)
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/FASE-G-MEMORY-VRAM-GTT-DESIGN.md` (diseño) ·
  `02-ARQUITECTURA/POLARIS12-MAP/HARDWARE-ROUTES.md`
- **RAW_EVIDENCE:** ese mismo directorio solo tiene el `.md`; no hay CSV de F-3A conservado.
- **KEYWORDS:** pcie, gen2, bandwidth, vram, gtt, root port, 00:01.0
- **STATUS:** `HISTORICAL`

---

## 4. Energía, clocks y gestión de potencia

### TOPIC=POWER_CAP
- **DESCRIPTION:** Efecto del límite de potencia sobre el rendimiento.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md` (35 W vs 30 W, 10 corridas,
  11 entrantes — el experimento canónico)
- **SECONDARY_SOURCES:** `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/RESULTADOS-FASE-B.md`
  (25/28/32/35 W) · `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md`
- **RAW_EVIDENCE:** `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939/` — `telemetry.csv`,
  `audit.json` por corrida, `m1-schedule.json`. Esquema en `M1-cap-35-30/TELEMETRY-SCHEMA.md`.
- **KEYWORDS:** power1_cap, power cap, 25w, 28w, 32w, 35w, watts, cap, energia
- **KNOWN_CONFLICTS:** `PATCH-REGISTRY-FINAL.md` P-002 marca el régimen E1/E3/E5 como
  `NOT_REPRODUCED`. Los `power-sweep-20260918-*` están marcados
  `ESTADO-HISTORICO-NO-UTILIZABLE` — **consultar esa marca antes de usar sus datos**.
- **STATUS:** `HISTORICAL` (resultado sólido sobre un host que ya no es este)

### TOPIC=DPM / SCLK / MCLK
- **DESCRIPTION:** Estados de energía, frecuencias de shader y memoria.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md`
  (tabla de regímenes)
- **SECONDARY_SOURCES:** `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md`
  (política DPM de MCLK en SMU7, fuente primaria del kernel) ·
  `04-IMPLEMENTACION/FASE-I-POWERPLAY-DPM-DESIGN.md` (diseño)
- **RAW_EVIDENCE:** `fase-a-discriminacion-20260919-114241/` (81 ficheros);
  `fase-b-cap-probe-20260919-122038/` (150 ficheros)
- **KEYWORDS:** dpm, pp_dpm_sclk, pp_dpm_mclk, sclk, mclk, pstate, powerplay, smu7
- **STATUS:** `HISTORICAL`

### TOPIC=RUNTIME_PM
- **DESCRIPTION:** `power/control`, `runtime_status`, autosuspend.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`
  (sección PM)
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/rx550-torneo/README-FASE1.md` (estado persistente) ·
  `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` (lectura de estado)
- **KEYWORDS:** runtime pm, power/control, runtime_status, autosuspend, pm_state
- **KNOWN_CONFLICTS:** `PROBLEM-STATUS-FINAL.md` deja la causalidad DPM/PM en `UNRESOLVED`.
  `PATCH-REGISTRY-FINAL.md` no la resuelve. `PM_EFFECT=UNKNOWN` en el addenda de reconciliación.
- **STATUS:** `HISTORICAL` + `UNRESOLVED`

### TOPIC=GOVERNOR
- **DESCRIPTION:** Governor de CPU, histéresis, ramp térmico. **No confundir con el de GPU.**
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/TEST-TERMICO-READONLY.md`
  (ramp 0.31 °C/s, recuperación ≤50 °C en 255–270 s, Kalm no intervino)
- **SECONDARY_SOURCES:** `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/RESULTADOS-TEST-TERMICO.md` ·
  `…/RESULTADOS-MINITEST-7.3-B.md` (N=2)
- **KEYWORDS:** governor, ramp, histeresis, termico, cooldowns, sclk 551, 92 grados
- **STATUS:** `HISTORICAL`

### TOPIC=BACO
- **DESCRIPTION:** Estado de ahorro BACO.
- **PRIMARY_SOURCE:** **NINGUNA.** 8 menciones, siempre de paso.
- **SECONDARY_SOURCES:** `PROBLEM-STATUS-FINAL.md` · `PATCH-REGISTRY-FINAL.md` · `FINAL-RELEASE-REPORT.md`
- **KEYWORDS:** baco
- **ESCALATION_CONDITION:** `NOT_AVAILABLE` como respuesta por defecto. No hay documento que
  defina qué se midió de BACO ni con qué resultado.
- **STATUS:** `NO_PRIMARY`

---

## 5. Mesa, Vulkan, RADV

### TOPIC=MESA
- **DESCRIPTION:** Versión, workarounds, parches custom.
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` §Mesa (registro de correcciones y versiones)
- **SECONDARY_SOURCES:** `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md`
  (workarounds aplicables, mayoría ya upstream) · `04-IMPLEMENTACION/FASE-H-RADV-WORKAROUNDS-DESIGN.md`
- **THIRD:** `PATCH-REGISTRY-RECOVERED.md` `RX550-MP-01` (commit Mesa `583c5d2f`, diff hasheado)
- **KEYWORDS:** mesa, radeonsi, radv, workarounds, erratas, has_msaa_sample_loc_bug, driconf
- **KNOWN_CONFLICTS — TRIPLE:**
  1. `MESA_EXTERNAL=26.2.3` vs `MESA_CANONICAL=26.2.2`, `MESA_PROVENANCE=CONFLICT`
     (`DOCUMENTARY-RECONCILIATION-2026-09-25.md`).
  2. Los documentos de la raíz dicen Mesa **25.3.2**; el host vivo tiene **26.2.3**.
  3. La investigación se hizo con Mesa **26.2.2** en el disco viejo.
  EP05 con Mesa CUSTOM **no reprodujo** E5 — resultado negativo que se conserva.
- **STATUS:** `CONFLICT`

### TOPIC=RADV
- **DESCRIPTION:** Driver Vulkan de AMD, selección de dispositivo.
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` (correcciones de selector: ICD AMD aislada,
  `DRI_PRIME` por `vendor:device`, `deviceID=0x699f`)
- **SECONDARY_SOURCES:** `04-IMPLEMENTATION/FASE-H-RADV-WORKAROUNDS-DESIGN.md` ·
  `02-ARQUITECTURA/knowledge.md`
- **KEYWORDS:** radv, icd, radeon_icd, vk_driver_files, dri_prime, device_select
- **KNOWN_CONFLICTS:** `mesa-vulkan-drivers` **no está instalado** en el host vivo, sí lo estaba
  en las capturas. Cualquier afirmación sobre RADV necesita re-verificación.
  `VK_EXT_image_drm_format_modifier` = `NOT_AVAILABLE` en el dispositivo GFX8 validado.
- **STATUS:** `CONFLICT` (host) / `CURRENT` (correcciones de selector)

### TOPIC=VULKAN
- **DESCRIPTION:** API, extensiones, WSI.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/H12-1/README.md` · `02-ARQUITECTURA/knowledge.md`
- **KEYWORDS:** vulkan, extension, wsi, present, xdg_shell, swapchain, surface
- **STATUS:** `HISTORICAL`

### TOPIC=OPENGL
- **DESCRIPTION:** Renderer OpenGL, `glxinfo`, selección por `DRI_PRIME`.
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` (identidad de selector; `cardN` no portable)
- **SECONDARY_SOURCES:** `INSTALL.md` §selectores · `02-ARQUITECTURA/knowledge.md`
- **KEYWORDS:** opengl, glxinfo, dri_prime, renderer, radeonsi, gl
- **KNOWN_CONFLICTS:** la numeración `cardN` de la RX550 cambió (`card2` → `card1`).
- **STATUS:** `CURRENT` (regla de selection) / `CONFLICT` (numeración)

---

## 6. Escritorio, compositors y otras GPUs

### TOPIC=KWIN / WAYLAND / XWAYLAND
- **DESCRIPTION:** Compositor, sesión gráfica, clientes de la GPU.
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` (14 mensajes de permission-denied de KWin;
  KWin/Wayland usan la RX550 como renderer)
- **SECONDARY_SOURCES:** `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` ·
  `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md` (sección renderers)
- **KEYWORDS:** kwin, wayland, xwayland, compositor, permission denied, plasma, session
- **KNOWN_CONFLICTS:** separación KWin/Intel = `UNRESOLVED`.
- **STATUS:** `MIXED`

### TOPIC=INTEL_GPU
- **DESCRIPTION:** GPU de display, su rol, por qué importa.
- **PRIMARY_SOURCE:** `02-ARQUITECTURA/knowledge.md` (Intel HD 4600, `0000:00:02.0`, i915)
- **SECONDARY_SOURCES:** `PATCH-REGISTRY-FINAL.md` (selector) · `RESULTADOS-FASE-A.md`
- **KEYWORDS:** intel, i915, hd 4600, 8086:0412, display, dri_prime
- **KNOWN_CONFLICTS:** el host vivo enumera Intel como `card0` y RX550 como `card1`;
  la captura de la raíz dice RX550 = `card2`.
- **STATUS:** `MIXED`

---

## 7. C1, aislamiento y propiedad

### TOPIC=C1
- **DESCRIPTION:** Experimento de aislamiento, su diseño, su estado, sus gates.
- **PRIMARY_SOURCE:** `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md` (41 KB — especificación
  con invariantes, taxonomía, GO/NO-GO/ABORT, restore)
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` (implementación y
  `restore_units()`) · `C1-RECOVERY-GPU-TREATMENT-DESIGN-v1.0.md`
- **THIRD:** `01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md` (53 KB,
  registro técnico con historial)
- **RAW_EVIDENCE:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/*.json` (14 ficheros, hasta 780 KB);
  `04-IMPLEMENTACION/c1_isolation_automator.py`; `03-EXPERIMENTOS/WORKLOAD-SINTETICO/c1_observer.py`
- **KEYWORDS:** c1, aislamiento, isolation, guard, restore, abort_restore, go/no-go, dry-run
- **KNOWN_CONFLICTS — CUATRO, sobre el mismo hecho:**
  1. **Tests C1**: `24/24` (R5, `HISTORICAL`) vs `37/37` (diagramas, `DERIVED/STALE`) vs
     `44/44` (sidecar vigente). `C1_TESTS=CONFLICT` en `DOCUMENTARY-RECONCILIATION-2026-09-25.md`.
  2. **Kernel**: `7.2.6` (C1/Gate) vs `7.2.4` (knowledge). No se funden.
  3. **Restore**: existe `restore_units()` pero `PROCESS_RESTORE_NOT_DEFINED` para clientes de sesión.
  4. **Estado**: `C1=DEFERRED`, `C1_RUNTIME_VALIDATED=NO`, `C1_READY=NO`. La existencia de la
     implementación y de tests estáticos **no** significa que C1 esté listo.
- **STATUS:** `CONFLICT`

### TOPIC=OWNERSHIP
- **DESCRIPTION:** Quién tiene la GPU abierta y si está probadamente libre.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`
  (fuente primaria declarada del gate P0)
- **SECONDARY_SOURCES:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.md`
  (lecturas privilegiadas) · `AGENTS.md` §Ownership
- **RAW_EVIDENCE:** `C1-PREFLIGHT-20260925T061932Z-PRIV.json` (780 KB)
- **KEYWORDS:** ownership, fds, drm clients, lsof, fuser, procesos,PermissionError
- **KNOWN_CONFLICTS:** `OWNERSHIP=PARTIAL`; el gate P0 da `B__CONTAMINATED_REQUIRES_ISOLATION`.
- **STATUS:** `HISTORICAL` + `PARTIAL`

### TOPIC=RECOVERY / TTY
- **DESCRIPTION:** Vía de recuperación independiente, disponibilidad de TTY.
- **PRIMARY_SOURCE:** `ROLLBACK.md` (política vigente) + `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY-GETTY-AUDIT-20260925T074900Z.md`
- **SECONDARY_SOURCES:** `C1-RECOVERY-INDEPENDENCE-VALIDATION-20260925T063810Z.md` ·
  `C1-RECOVERY-RUNTIME-TEST-20260925T064051Z-{PRE,POST}.md` ·
  `C1-TTY3-*-20260925T0*.md` (4 documentos)
- **KEYWORDS:** recovery, restore, tty, getty, reboot, post_reboot, independence
- **KNOWN_CONFLICTS:** `RESTORE_EXECUTED=NO`, `RESTORE_VALIDATED=NO`. Los documentos `-PRE`
  solo tienen sentido junto a su `-POST`.
- **STATUS:** `HISTORICAL`

### TOPIC=GATES
- **DESCRIPTION:** Gates de validez experimental y de publicación.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`
  (33 KB, 13 entrantes)
- **SECONDARY_SOURCES:** `RELEASE-CANDIDATE.md` (gates de publicación) ·
  `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md`
- **KEYWORDS:** gate, p0, g-01, g-08, deffered, contaminated, isolation, publish gate
- **STATUS:** `MIXED` (P0 histórico; gates de publicación actuales)

---

## 8. Contadores y telemetría

### TOPIC=COUNTERS
- **DESCRIPTION:** Performance counters GFX8, cuáles existen y cuáles no.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md`
  (Resultado B: GRBM=2 / SQ=4 **no validan ASIC**)
- **SECONDARY_SOURCES:** `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-1-GFX8-EVENT-IDS.md` ·
  `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md` ·
  `FASE-D-COUNTERS-AUDIT.md` · `FASE-D-ETAPA-2-{AUDIT,RESULTADOS}.md`
- **THIRD:** `04-IMPLEMENTACION/FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md` · `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md`
- **RAW_EVIDENCE:** `FASE-D-COUNTERS-AUDIT/runs/etapa2/` (93 ficheros, `resultados_etapa2.json` **malformado**)
- **KEYWORDS:** counters, grbm, mmhub, sq, event ids, sqtt, gpuperfapi, perf
- **STATUS:** `HISTORICAL`

### TOPIC=TELEMETRY
- **DESCRIPTION:** Esquemas de datos, ventana de análisis, clasificación de calidad.
- **PRIMARY_SOURCE:** `02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md`
  (clasificación A/B/C/D) · `03-EXPERIMENTOS/M1-cap-35-30/TELEMETRY-SCHEMA.md` (esquema M1)
- **SECONDARY_SOURCES:** `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/EP08-auditoria-telemetria-E1E3.md`
- **KEYWORDS:** telemetria, telemetry.csv, window, samples, 10hz, clasificacion a/b/c/d
- **STATUS:** `HISTORICAL`

### TOPIC=SMU
- **DESCRIPTION:** Qué mide realmente `power1_input`.
- **PRIMARY_SOURCE:** `01-AUDITORIA/AUDIT-001/ERRATA.md` §ERRATUM-002 — `power1_input` es
  **`W_SMU`** (potencia estimada por el sensor), no un medidor independiente.
- **SECONDARY_SOURCES:** `01-AUDITORIA/AUDIT-001/METRICS-DEFINITIONS.md` (`power_avg_full`,
  `power_avg_steady`, `power_max`) · `PATCH-REGISTRY-FINAL.md`
- **KEYWORDS:** smu, w_smu, power1_input, power_avg_steady, power_avg_full
- **STATUS:** `RESOLVED` (etiquetado) — `HISTORICAL` (documento)

### TOPIC=RESET
- **DESCRIPTION:** Ring timeout, GPU reset, RA24.
- **PRIMARY_SOURCE:** `PATCH-REGISTRY-FINAL.md` (P-008: RA24 = `NOT_REPRODUCED`; `RA24=0` en el journal)
- **SECONDARY_SOURCES:** `PROBLEM-STATUS-FINAL.md` · `03-EXPERIMENTOS/M1-cap-35-30/` (`gpu_reset_check` en `audit.json`)
- **KEYWORDS:** reset, ring timeout, amdgpu_fence, ra24, little endian, journal
- **STATUS:** `CURRENT` (el veredicto `NOT_REPRODUCED` es actual) — pero la evidencia es del host viejo

---

## 9. Frame, jitter, WSI

### TOPIC=FRAME
- **DESCRIPTION:** Frametime, jitter, stutter,Percentiles.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md`
  (NIVEL A MAE=0.0 px, NIVEL B MAE=3.66e-10 px; 8/8 celdas PASS; ANV sin devices → `NO EJECUTADO`)
- **SECONDARY_SOURCES:** `PRECHECK-REPORT.md` · `EXP-F1-A-JITTER-OBSERVABILITY.md` · `PRIOR-ART.md` ·
  `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/README.md` (resumen)
- **RAW_EVIDENCE:** `FASE-R4C-JITTER-OBSERVABILITY/results/` (85 ficheros: `metrics/*.json`,
  `gt/*_gt.json`, capas Vulkan)
- **KEYWORDS:** frametime, jitter, stutter, p50, p95, p99, maes, percentiles, timeline
- **STATUS:** `HISTORICAL`

### TOPIC=WSI
- **DESCRIPTION:** Ciclo Wayland / xdg-shell / Vulkan WSI y present timing.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md` (37 KB)
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/H12-2/README.md` ·
  `04-IMPLEMENTACION/H12-1/README.md` (32 KB, incluye H12-3/H12-4)
- **KEYWORDS:** wsi, xdg_shell, present timing, wayland, surface, configure, h12
- **KNOWN_CONFLICTS:** `H12-4=EXTERNAL_COMPLETED_RECORD_VS_DOC_NOT_EXECUTED`;
  `H12-4_PROVENANCE=CONFLICT`. `PATCH-REGISTRY-FINAL.md` P-022 marca H12 como `NOT_REPRODUCED`
  **como síntoma actual**.
- **STATUS:** `CONFLICT`

---

## 10. Almacenamiento

### TOPIC=STORAGE / HDD / SMART / IO / D_STATE / PSI
- **DESCRIPTION:** Salud del disco, E/S, estados D, presión de I/O.
- **PRIMARY_SOURCE:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`
- **SECONDARY_SOURCES:** `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` (44 KB) ·
  `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` (25 KB)
- **THIRD:** `AGENTS.md` §HDD and Btrfs
- **KEYWORDS:** hdd, hm500ji, smart, scrub, iostat, iowait, d-state, psi, pressure stall, loadavg
- **KNOWN_CONFLICTS:** `HDD_FAILURE=NOT_PROVEN`, `HDD_HEALTHY=UNKNOWN`. El host viejo tenía
  HDD SAMSUNG HM500JI; **el host vivo usa `/dev/sdb3` ext4** — distinto.
- **STATUS:** `HISTORICAL`

### TOPIC=BTRFS
- **DESCRIPTION:** Sistema de ficheros, errores de VM fault, identidad de la ventana.
- **PRIMARY_SOURCE:** `PROBLEM-STATUS-FINAL.md` (P-012 R-11) + `PATCH-REGISTRY-FINAL.md` §P-012
- **SECONDARY_SOURCES:** `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md` §R-11 (VM faults
  deterministas de `imageStore` a storage IMAGE, corrección por upload host)
- **THIRD:** `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` (`BTRFS=CONFLICT`)
- **RAW_EVIDENCE:** `WORKLOAD-SINTETICO/src/graphics.cpp` (bloque de upload); `src/gen.comp`
- **KEYWORDS:** btrfs, vm fault, storage image, r-11, imageStore, ext4, sdb3
- **KNOWN_CONFLICTS:** `BTRFS=CONFLICT`, `BTRFS_CAUSE=UNKNOWN`, requiere
  `matched_identity_same_window`. El host vivo es **ext4**, no Btrfs.
- **STATUS:** `CONFLICT` (histórico) / `OBSOLETE` (sistema de ficheros del host actual)

---

## 11. Background, systemd y otros autores

### TOPIC=SYSTEMD / KALM / AUTOPILOT / BACKGROUND
- **DESCRIPTION:** Procesos y unidades que compiten por la GPU en el disco viejo.
- **PRIMARY_SOURCE:** `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` (25 KB) — auditoría
  detallada de `system-autopilot.timer` y `kalm.service`
- **SECONDARY_SOURCES:** `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` (30 KB, protocolo A/B
  **nunca ejecutado**) · `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` (44 KB)
- **THIRD:** `01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` (parches de sistema B:
  `RX550-SD-01..04`, `RX550-PM-01`, `RX550-UNK-01`)
- **KEYWORDS:** kalm, kalmd, autopilot, background, irq 39, smp_affinity, sys-tuned, 54 ciclos
- **KNOWN_CONFLICTS:** estas unidades **no existen en el host vivo** (verificado: 0 unidades
  `kalm*`, 0 `system-autopilot*`, sin `/opt/kalm`, sin `/usr/local/bin/kalm*`).
  El protocolo A/B está explícitamente marcado como no ejecutado.
  Conclusión histórica conservada: **Kalm no explica el régimen E1/E3/E5.**
- **STATUS:** `HISTORICAL` (obsoleto para el host actual)

### TOPIC=IRQ
- **DESCRIPTION:** Afinidad de IRQ, IRQ 39 fijada a `cc`.
- **PRIMARY_SOURCE:** `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` §IRQ
- **SECONDARY_SOURCES:** `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` · `C1-PREFLIGHT-20260925T061932Z-PRIV.md`
- **KEYWORDS:** irq, smp_affinity, cc, isolated, housekeeping
- **STATUS:** `HISTORICAL`

### TOPIC=GRUB / UDEV
- **DESCRIPTION:** Configuración de arranque y reglas de dispositivos.
- **PRIMARY_SOURCE:** **NINGUNA.** Existen como **prohibición** en `README.md` §Reglas de
  seguridad, `AGENTS.md`, `ROLLBACK.md`, `INSTALL.md` (UDEV: 11 menciones; GRUB: 34).
- **SECONDARY_SOURCES:** `PATCH-REGISTRY-RECOVERED.md` `RX550-UD-01/02` (reglas udev del
  backup, **no aplicadas**), `RX550-GR-01` = `NOT_AVAILABLE`
- **KEYWORDS:** grub, grubenv, cmdline, udev, rules.d, initramfs, dracut
- **ESCALATION_CONDITION:** la respuesta correcta es "no hay fuente y está prohibido".
- **STATUS:** `NO_PRIMARY` (solo prohibición)

---

## 12. Experimentos, benchmarks y carga

### TOPIC=EXPERIMENTS / R4B / R4C
- **DESCRIPTION:** Qué experimentos existen, cuál es el resultado canónico de cada uno.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`
  (12 entrantes — R-4B: S1 EJECUTADA, S2 **PARADA_D**, veredicto `INCONCLUSO`)
- **SECONDARY_SOURCES:** `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md` ·
  `00-INDICE/MASTER-RESEARCH-STATUS.md` §Precedencia de estado R-4B
- **THIRD:** protocolos y pre-runs de `FASE-R4B-GOVERNOR/` (7 ficheros, `SNAPSHOT`)
- **RAW_EVIDENCE:** `FASE-R4B-GOVERNOR/results/session1-v22/` y `results/v23/` (340 ficheros,
  `metrics.json` de 37-38 KB)
- **KEYWORDS:** exp-f4-a, r-4b, r-4c, s1, s2, parada_d, inconclusive, addenda d6, freeze
- **KNOWN_CONFLICTS:** las frases «NO EJECUTADA» / «S2 no iniciada» en secciones anteriores de
  `MASTER-RESEARCH-STATUS.md` son snapshots que **no** describen el estado post-addenda.
- **STATUS:** `HISTORICAL`

### TOPIC=M1
- **DESCRIPTION:** Experimento canónico de power cap.
- **PRIMARY_SOURCE:** `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/rx550-torneo/README-M1.md` (runner) ·
  `M1-cap-35-30/TELEMETRY-SCHEMA.md` (esquema) · `03-EXPERIMENTOS/M1-cap-35-30/run-m1.sh`
- **RAW_EVIDENCE:** `M1-cap-35-30/runs/20260919-235939/` (51 ficheros, 10 corridas,
  `m1-schedule.json` de 53 KB)
- **KEYWORDS:** m1, 35w, 30w, cap, block, arm, schedule, fps
- **STATUS:** `HISTORICAL`

### TOPIC=BENCHMARKS / SUPERPOSITION / GLMARK2
- **DESCRIPTION:** Benchmarks candidatos y ejecutados.
- **PRIMARY_SOURCE:** `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` (37 KB,
  "cuatro conceptos distintos")
- **SECONDARY_SOURCES:** `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-5-BENCHMARKS-EXTERNOS-RX550.md` ·
  `RX550_Benchmarks/README.md` · `RX550_Benchmarks/docs/SOURCES-AND-EXECUTION.md`
- **THIRD:** `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/` ·
  `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/`
- **KEYWORDS:** benchmark, vkmark, glmark2, superposition, unigine, gravitymark, m2, workload
- **KNOWN_CONFLICTS:** los ficheros de benchmark grandes están excluidos del árbol publicable
  (`RELEASE-EXCLUSIONS.md`): `Unigine_Superposition-1.1.run.partial` (123 753 líneas),
  `GravityMark_1.89.run` (683 686 líneas) — eliminados del índice Git en la fase de parches.
- **STATUS:** `MIXED` (inventario actual; datos históricos)

---

## 13. Hipótesis, decisiones y diseño

### TOPIC=HYPOTHESIS
- **DESCRIPTION:** Registro de hipótesis H1–H12 y su estado.
- **PRIMARY_SOURCE:** `00-INDICE/HYPOTHESIS-REGISTER.md` (16 KB) — **sin veredictos**, `DRAFT/CONFLICT`
- **SECONDARY_SOURCES:** `02-ARQUITECTURA/hypotheses.md` (confirmadas, descartadas, no reproducibles) ·
  `02-ARQUITECTURA/rejected_ideas.md`
- **THIRD:** `DESIGN-GRAPHICS.md` §taxonomía `[VERIFICADO]`/`[NO REPRODUCIBLE]`/`[HIPÓTESIS]`/
  `[DESCARTADO]`/`[DESCONOCIDO]` que `RESEARCH.md` reutiliza
- **KEYWORDS:** hipotesis, hypothesis, h1..h12, descartada, no reproducible, veredict
- **KNOWN_CONFLICTS:** el registro es **textual y provisional**; no es un veredicto.
- **STATUS:** `MIXED`

### TOPIC=DECISIONS
- **DESCRIPTION:** Decisiones de investigación y autorizaciones.
- **PRIMARY_SOURCE:** `01-AUDITORIA/DECISIONES-D1-D10.md` (67 KB) + reconciliación
- **SECONDARY_SOURCES:** `00-INDICE/decisions.md` (cierre 2026-09-19) ·
  `00-INDICE/experiments_proposed.md`
- **KEYWORDS:** decisiones, d1-d10, autorizacion, cierre, bloqueado, traspaso
- **STATUS:** `MIXED`

### TOPIC=DESIGN
- **DESCRIPTION:** Diseños de fases E–Q, de ideas I-01..I-10, del workload sintético.
- **PRIMARY_SOURCE:** `00-INDICE/MASTER-PLAN.md` (73 KB) — plan maestro
- **SECONDARY_SOURCES:** `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` ·
  `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md` (frontera de seguridad)
- **THIRD:** los 12 `FASE-*-DESIGN.md` y los 10 dossiers de `04-IMPLEMENTACION/projects/`
- **KEYWORDS:** diseno, design, fase e..q, idea i-01..i-10, roadmap, feasibility, prior art
- **KNOWN_CONFLICTS:** **ningún diseño es autorización.** `MASTER-PLAN.md` lo dice: "no es
  autorización". `IMPLEMENTATION-SAFETY-RULES.md` define la frontera.
- **STATUS:** `MIXED` (diseño) — `CURRENT` (las reglas de seguridad)

---

## 14. Documentación y navegación

### TOPIC=DOCUMENTATION_MAP / DIAGRAMS
- **DESCRIPTION:** Mapas e índices del propio repositorio.
- **PRIMARY_SOURCE:** `00-INDICE/README.md` (índice canónico) + `README.md` (raíz)
- **SECONDARY_SOURCES:** `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` ·
  `00-INDICE/DIAGRAMAS/README.md` (convención)
- **THIRD:** `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (**`DRAFT/CONFLICT`**) ·
  16 vistas en `00-INDICE/DIAGRAMAS/` (**`DRAFT/CONFLICT`**) ·
  `01-AUDITORIA/FASE-R1/R1-5-DOCUMENTATION-STATUS.md`
- **RAW_EVIDENCE:** `00-INDICE/REGISTRO-DE-MOVIMIENTOS.md` y
  `REGISTRO-DE-REPARACION-REFERENCIAS.md` (trazabilidad de la reorganización y de las reparaciones)
- **KEYWORDS:** indice, mapa, navegacion, documentacion, reorganizacion, referencias, hashes
- **KNOWN_CONFLICTS:** el mapa global y 16 de 17 diagramas se marcan a sí mismos
  `DRAFT/CONFLICT`. No son fuente de estado. Existen **cinco** mecanismos de navegación
  parcialmente solapados y ninguno se declara canónico salvo `README.md`.
- **STATUS:** `CONFLICT`

### TOPIC=VOCABULARY
- **DESCRIPTION:** Normalización de estados documentales.
- **PRIMARY_SOURCE:** `AGENTS.md` §Evidence vocabulary (`OBSERVED`, `SUPPORTED`, `PLAUSIBLE`,
  `UNKNOWN`, `NOT_AVAILABLE`, `CONFLICT`, `FAIL`, `DEFERRED`)
- **SECONDARY_SOURCES:** `00-INDICE/ESTADOS-ES-EN.md` (taxonomía ampliada, **provisional**) ·
  `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-6-EVIDENCE-STATE-MODEL.md`
- **KEYWORDS:** vocabulario, estados, evidence state model, taxonomia, normalizacion
- **KNOWN_CONFLICTS:** `ESTADOS-ES-EN.md` se autodescribe como taxonomía ampliada **provisional**.
  Hay **dos** vocabularios de estados: el de `AGENTS.md` (inglés) y el de `PATCH-REGISTRY-FINAL.md`
  (11 estados de problema). No están unificados.
- **STATUS:** `MIXED`

### TOPIC=FIREFOX
- **DESCRIPTION:** Firefox y su relación con la GPU.
- **PRIMARY_SOURCE:** **NINGUNA.** 5 menciones, siempre de paso o como cliente de GPU.
- **KEYWORDS:** firefox
- **ESCALATION_CONDITION:** `NOT_AVAILABLE`.
- **STATUS:** `NO_PRIMARY`

---

## 15. Resumen de rutas de búsqueda

| Tema | FIRST_DOCUMENT | SECOND_DOCUMENT | RAW_EVIDENCE | ESCALATION |
|---|---|---|---|---|
| PROJECT_STATUS | `README.md` | `PROBLEM-STATUS-FINAL.md` | — | `MASTER-RESEARCH-STATUS.md` (solo historial) |
| HOST_IDENTITY | ejecutar `tools/validate_rx550_final.py` | `PATCH-SOURCES.md` §3 | `FINAL-VALIDATION-*.json` (obsoleto) | `CONFLICT` → 3 identidades |
| PROBLEM_MATRIX | `PROBLEM-STATUS-FINAL.md` | `PATCH-REGISTRY-FINAL.md` | — | `CONFLICT` |
| PATCHES | `PATCH-REGISTRY-FINAL.md` | `PATCH-REGISTRY-RECOVERED.md` | hashes | `NOT_AVAILABLE` (system-autopilot) |
| RELEASE | `RELEASE-CANDIDATE.md` | `FINAL-RELEASE-REPORT.md` | — | `BLOCK` (sin remote) |
| SAFETY | `AGENTS.md` | `IMPLEMENTATION-SAFETY-RULES.md` | — | — |
| C1 | `C1-ISOLATION-DESIGN-v1.0.md` | `C1-ISOLATION-AUTOMATOR.md` | `C1-PREFLIGHT-*.json` | `CONFLICT` (4 flavour) |
| OWNERSHIP | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | `C1-PREFLIGHT-…-PRIV.md` | `.json` 780 KB | `PARTIAL` |
| GATES | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | `RELEASE-CANDIDATE.md` | — | `DEFERRED` |
| POWER_CAP | `RESULTADOS-M1.md` | `RESULTADOS-FASE-B.md` | `M1-cap-35-30/runs/` | `NOT_REPRODUCED` (E1/E3/E5) |
| SCLK/MCLK | `RESULTADOS-FASE-A.md` | `R0-2-POWERPLAY-MCLK-SMU7.md` | `fase-a-*/` | — |
| RUNTIME_PM | `P0-…GATE-2026-09-24.md` | `README-FASE1.md` | — | `UNRESOLVED` |
| MESA | `PATCH-REGISTRY-FINAL.md` | `R0-3-MESA-WORKAROUNDS-POLARIS12.md` | commit `583c5d2f` | `CONFLICT` (3 versiones) |
| RADV | `PATCH-REGISTRY-FINAL.md` | `knowledge.md` | — | `CONFLICT` (sin mesa-vulkan-drivers) |
| VULKAN/WSI | `H12-2-…WSI-EVIDENCE.md` | `H12-1/README.md` | `results/` | `CONFLICT` (H12-4) |
| FRAME | `EXP-F1-A-RESULTADOS.md` | `PRECHECK-REPORT.md` | `FASE-R4C-*/results/` | — |
| COUNTERS | `FASE-D-GFX8-EVENT-ID-AUDIT.md` | `R0-1-GFX8-EVENT-IDS.md` | `FASE-D-*/runs/` | — |
| SMU | `AUDIT-001/ERRATA.md` | `METRICS-DEFINITIONS.md` | — | `RESOLVED` |
| BTRFS/R-11 | `PROBLEM-STATUS-FINAL.md` P-012 | `WORKLOAD-SINTETICO/RESEARCH.md` §R-11 | `src/graphics.cpp` | `CONFLICT` / `OBSOLETE` |
| STORAGE/HDD | `P0-…GATE-2026-09-24.md` | `AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | — | `UNKNOWN` (host nuevo es ext4/sdb3) |
| BACKGROUND | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | `PATCH-REGISTRY-RECOVERED.md` grupo B | backup `shell-history` | `NOT_AVAILABLE` (no existe ya) |
| R4B | `EXP-F4-A-RESULTADOS-v2.3.md` | `MASTER-RESEARCH-STATUS.md` addenda D6 | `results/v23/` | `INCONCLUSIVE` |
| R4C | `EXP-F1-A-RESULTADOS.md` | `README.md` (FASE R-4C) | `results/` | — |
| M1 | `RESULTADOS-M1.md` | `README-M1.md` | `runs/20260919-235939/` | — |
| BENCHMARKS | `BENCHMARK-INVENTORY.md` | `R0-5-BENCHMARKS-EXTERNOS-RX550.md` | `RX550_Benchmarks/` | datos excluidos |
| GPU/POLARIS12 | `02-ARQUITECTURA/knowledge.md` | `POLARIS12-MAP.md` | — | `MIXED` |
| KERNEL/AMDGPU | `02-ARQUITECTURA/knowledge.md` | `SOFTWARE-CAPABILITIES.md` | — | `CONFLICT` (3 kernels) |
| EXPERIMENTS | `MASTER-RESEARCH-STATUS.md` (historia) | `RESEARCH.md` (workload) | por directorio de experimento | — |
| HYPOTHESIS | `HYPOTHESIS-REGISTER.md` | `02-ARQUITECTURA/hypotheses.md` | — | `DRAFT` |
| DECISIONS | `DECISIONES-D1-D10.md` | `00-INDICE/decisions.md` | — | — |
| DESIGN | `MASTER-PLAN.md` | `IMPLEMENTATION-ROADMAP.md` | — | no es autorización |
| DOC-INDEX | `README.md` | `00-INDICE/README.md` | — | `CONFLICT` (5 mecanismos) |
| **BACO** | — | menciones de paso | — | `NOT_AVAILABLE` |
| **FIREFOX** | — | menciones de paso | — | `NOT_AVAILABLE` |
| **GRUB** | — | solo prohibición | — | `NOT_AVAILABLE` |
| **UDEV** | — | solo prohibición | — | `NOT_AVAILABLE` |
