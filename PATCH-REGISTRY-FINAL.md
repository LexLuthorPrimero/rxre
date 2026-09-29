# Registro final de correcciones y procedimientos — RX 550

**Fecha de consolidación:** 2026-09-25
**Ámbito:** migración documental y procedimientos read-only a la instalación
actual Nobara 43.
**Host de referencia:** `1002:699f`, BDF `0000:01:00.0`, `amdgpu`, Polaris12/GFX8.

Este registro separa una corrección de código de una hipótesis, una corrección
upstream, una configuración por proceso y un simple diagnóstico. No se aplicó
ningún cambio persistente al sistema. La única modificación de ejecución local
fue la creación de esta documentación, de la herramienta de validación y de
pruebas estáticas con archivos temporales.

## Convenciones

- `RESOLVED`: la corrección concreta está implementada y verificada en el
  alcance indicado.
- `PARTIALLY_RESOLVED`: una parte está verificada, pero queda una condición o
  una migración que no pudo cerrarse.
- `UNRESOLVED`: no existe evidencia suficiente para cerrar el problema.
- `OBSOLETE`: la hipótesis o configuración histórica quedó invalidada o ya no
  pertenece a la instalación actual.
- `ALREADY_FIXED_UPSTREAM`: el workaround está incorporado en Mesa upstream;
  no se debe mantener un parche local equivalente.
- `NOT_REPRODUCED`: el síntoma histórico no se reprodujo en la instalación
  actual; no es una declaración de causa.
- `NOT_AVAILABLE`: la capacidad o fuente necesaria no está disponible.

## Resumen

| ID | Problema | Tipo | Estado final |
|---|---|---|---|
| P-001 | Identidad por PCI frente a `cardN` | `CONFIGURATION_CHANGE` | `PARTIALLY_RESOLVED` |
| P-002 | Régimen E1/E3/E5 de 25 W y clocks bajos | `DIAGNOSTIC_ONLY` | `NOT_REPRODUCED` |
| P-003 | Atribución del régimen a Kalm | `DIAGNOSTIC_ONLY` | `OBSOLETE` |
| P-004 | `power1_input` tratado como vatímetro | `DIAGNOSTIC_ONLY` | `RESOLVED` |
| P-005 | Mesa CUSTOM como causa del problema | `PATCH_REAL` | `OBSOLETE` |
| P-006 | Workarounds RADV/RadeonSI para GFX8 | `UPSTREAM_FIX` | `ALREADY_FIXED_UPSTREAM` |
| P-007 | `VK_EXT_image_drm_format_modifier` en GFX8 | `DIAGNOSTIC_ONLY` | `NOT_AVAILABLE` |
| P-008 | RA24/little-endian en KWin/DRM | `DIAGNOSTIC_ONLY` | `NOT_REPRODUCED` |
| P-009 | Separación de render KWin/Wayland e Intel host | `CONFIGURATION_CHANGE` | `UNRESOLVED` |
| P-010 | `DRI_PRIME` numérico en Xwayland/GL | `CONFIGURATION_CHANGE` | `PARTIALLY_RESOLVED` |
| P-011 | Selección RADV por ICD | `CONFIGURATION_CHANGE` | `PARTIALLY_RESOLVED` |
| P-012 | VM faults de storage images R-11 | `WORKAROUND` | `PARTIALLY_RESOLVED` |
| P-013 | Detector de ring timeout/reset/hang | `PATCH_REAL` | `PARTIALLY_RESOLVED` |
| P-014 | BACO y runtime PM | `DIAGNOSTIC_ONLY` | `UNKNOWN` |
| P-015 | DPM/SCLK/MCLK/power cap | `DIAGNOSTIC_ONLY` | `UNKNOWN` |
| P-016 | Firmware/VBIOS y tabla de estados | `DIAGNOSTIC_ONLY` | `NOT_REPRODUCED` |
| P-017 | Migración Mesa/LLVM/libdrm | `UPSTREAM_FIX` | `PARTIALLY_RESOLVED` |
| P-018 | Kalm GPU/system-autopilot como agente actual | `DIAGNOSTIC_ONLY` | `OBSOLETE` |
| P-019 | VFIO y RX 550 dedicada al host | `DIAGNOSTIC_ONLY` | `UNRESOLVED` |
| P-020 | C1, ownership, recovery y aislamiento | `DIAGNOSTIC_ONLY` | `UNRESOLVED` |
| P-021 | HDD/Btrfs histórico frente a la nueva raíz | `DIAGNOSTIC_ONLY` | `NOT_REPRODUCED` |
| P-022 | H12 Wayland/xdg-shell/WSI | `DIAGNOSTIC_ONLY` | `NOT_REPRODUCED` |

## Detalle de entradas

### P-001 — Identidad por PCI frente a `cardN`

- **Tipo de parche:** `CONFIGURATION_CHANGE`.
- **Síntoma:** la numeración histórica `card0`/`card1` no coincide con la
  instalación actual; una prueba podía apuntar a la Intel o a un `hwmon` que
  ya no existe.
- **Causa:** `cardN` y `hwmonN` son asignaciones dinámicas, no identificadores
  de hardware.
- **Corrección propuesta:** resolver siempre por `vendor:device=1002:699f`,
  derivar BDF, card, render node y hwmon; usar el BDF sólo como confirmación.
- **Archivos/hash:** `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo/gpu_finder.py`
  (`b794407ed58a744995730acdeef9842db8aba6b46f2e4d94872c79e3a3423f24`),
  `state_manager.py` (`ef387e92db437cf2d1a84dccf921c9e927f1e55ab74502c344ec51488eb3f44a`),
  `tests/run_tests.py` (`fa4c488515967e6ed1379bb5891c6235dccca5d77fd077d0ff97fac8add338a6`),
  `tools/validate_rx550_final.py` (`2d7c4c9c8e3e03879f0a5a4c17ab31b618c019781c9cb459d5d38a8d88c435c3`).
- **Versiones:**Nobara 43; kernel `6.18.2-200.nobara.fc43.x86_64`; Mesa
  `25.3.2-2.fc43`; Python 3.14.
- **Estado anterior:** `PARTIALLY_RESOLVED` — el detector ya era dinámico, pero
  varias pruebas y documentación seguían nombrando nodos fijos.
- **Estado posterior:** `PARTIALLY_RESOLVED` — las pruebas se actualizaron y
  pasan en la instalación actual; las referencias históricas no se reescriben.
- **Prueba de validación:** `run_tests.py` `64/64`; el validador encontró
  `0000:01:00.0`, `card2`, `renderD129`, `hwmon1`.
- **Reversibilidad/riesgo:** cambio de código y pruebas; riesgo bajo; no
  modifica el host.

### P-002 — Régimen E1/E3/E5 de 25 W y clocks bajos

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** se registraron históricamente `power1_input≈25 W`, SCLK
  350–390 MHz, MCLK 1250–1500 MHz y 74–92 °C.
- **Causa:** `UNKNOWN`; la asociación con Kalm, Mesa CUSTOM o la iGPU fue
  refutada o no demostrada.
- **Corrección propuesta:** no aplicar un parche de clocks/power; conservar el
  hecho como baseline histórico y exigir identidad, journal y telemetría por
  ventana en cualquier repetición.
- **Archivos/hash:** `01-AUDITORIA/AUDIT-001/AUDIT-001.md`,
  `01-AUDITORIA/AUDIT-001/EVIDENCE-MATRIX.md`,
  `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json`
  (`0fea12f9da09a30456e1ab06c6b8fa40a27af94fcc64e2ae8b8fe9ac22e7e1cb`).
- **Versiones:** histórico Nobara 44/kernel 7.2.x frente a actual Nobara
  43/kernel 6.18.2; no son el mismo entorno.
- **Estado anterior:** `NOT_REPRODUCED`.
- **Estado posterior:** `NOT_REPRODUCED` — no se reprodujo en la nueva
  instalación; la causa continúa `UNKNOWN`.
- **Prueba de validación:** sólo instantánea read-only; no se ejecutó una campaña
  DPM.
- **Reversibilidad/riesgo:** no hay cambio que revertir; existe riesgo de
  sobreajuste si se fuerza un cap sin aislar clientes.

### P-003 — Atribución del régimen a Kalm

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** el relato histórico trataba Kalm como causa de 25 W y clocks
  bajos.
- **Causa:** atribución sin evidencia; el régimen se había observado con Kalm
  inactivo y con Kalm activo se melihaton otros estados.
- **Corrección propuesta:** errata explícita; no instalar ni activar Kalm para
  explicar el régimen; separar correlación de causalidad.
- **Archivos/hash:** `01-AUDITORIA/AUDIT-001/ERRATA.md` y la validación final
  (`0fea12f9da09a30456e1ab06c6b8fa40a27af94fcc64e2ae8b8fe9ac22e7e1cb`).
- **Versiones:** backup histórico frente a Nobara 43 actual.
- **Estado anterior:** `OBSOLETE` como hipótesis de causa.
- **Estado posterior:** `OBSOLETE` — la atribución no se conserva; el servicio
  tampoco está instalado en la instalación actual.
- **Prueba de validación:** `kalm-gpu.service` y `kalm.service` =
  `inactive/not-found`; no se cambió su estado.
- **Reversibilidad/riesgo:** sólo documentación; riesgo bajo.

### P-004 — `power1_input` tratado como vatímetro

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** cifras de `power1_input` presentadas como vatios independientes.
- **Causa:** el nodo es una estimación del sensor SMU, no un vatímetro externo.
- **Corrección propuesta:** escribir `W_SMU`; no comparar con potencia de red
  sin instrumentación independiente.
- **Archivos/hash:** `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md`
  (`104ececa92ab75926d2f1e589e14db9c435d96a0469e05e15955c0ed2f70677b`),
  validación final (`0fea12f9da09a30456e1ab06c6b8fa40a27af94fcc64e2ae8b8fe9ac22e7e1cb`).
- **Versiones:** nodo `hwmon1` de la instalación actual; lectura ~5.1 W.
- **Estado anterior:** `UNKNOWN` para la interpretación del sensor.
- **Estado posterior:** `RESOLVED` para la etiqueta/metadato; no se afirma vatímetro.
- **Prueba de validación:** `power1_input_uw=5108000`, cap/default/max de 35 W;
  no se leyó ni modificó.
- **Reversibilidad/riesgo:** no aplica al sistema; riesgo de interpretación
  eliminado parcialmente.

### P-005 — Mesa CUSTOM como causa del problema

- **Tipo de parche:** `PATCH_REAL` (parche histórico local, no instalado).
- **Síntoma:** una build experimental en `/opt/mesa-26.2.2-rx550-haswell` se
  registraba como posible causa del régimen o de diferencias de rendimiento.
- **Causa:** el A/B controlado no reprodujo E5 y la build no es necesaria para el
  renderer de distribución actual.
- **Corrección propuesta:** conservar el parche y el manifiesto como evidencia,
  pero no migrarlo al árbol del sistema; usar paquetes de distribución.
- **Archivos/hash:** commit Mesa `583c5d2f44152ed70d6f9aff58fbca5abcf7376d`,
  parche `0001-radv-simplify-address-binding-report-logging.patch`
  (`26fdb443cc9cdc71453e956ff605f4a5dd1fc3d8109fc92f15091cbaa66d5399`),
  backup `RX550_Modo_Torneo_Backup_2026-09-19_0836/`.
- **Versiones:** build custom 26.2.2 histórica; actual 25.3.2 de Nobara 43.
- **Estado anterior:** `OBSOLETE` como hipótesis de causa.
- **Estado posterior:** `OBSOLETE` — no se aplica; no existe `/opt/mesa-*` en
  la instalación actual.
- **Prueba de validación:** `rpm -qf` identifica el renderer de distribución y
  no hay ruta custom; no se comparó rendimiento.
- **Reversibilidad/riesgo:** no hay cambio activo; existe riesgo de introducir
  una ABI incompatible si se copia la build.

### P-006 — Workarounds RADV/RadeonSI para GFX8

- **Tipo de parche:** `UPSTREAM_FIX`.
- **Síntoma:** posibles diferencias de MSAA sample-location, line filtering,
  DCC/HTILE y wait-for-VM-map en GFX8.
- **Causa:** bugs y límites de la generación GFX8; varios workarounds ya están
  integrados en Mesa upstream y en reglas de distribución.
- **Corrección propuesta:** no mantener un parche local equivalente; usar Mesa
  de distribución y revisar la versión antes de ajustar `driconf`.
- **Archivos/hash:** `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md`
  y `/usr/share/drirc.d/00-radv-defaults.conf` de la instalación actual.
- **Versiones:** Mesa 25.3.2; LLVM 21.1.7;RADV GFX8.
- **Estado anterior:** `ALREADY_FIXED_UPSTREAM` para los workarounds
  documentados.
- **Estado posterior:** `ALREADY_FIXED_UPSTREAM` — el efecto de cada workaround
  en una aplicación concreta no se revalidó.
- **Prueba de validación:** RADV arranca y enumera `0x699f`; no se ejecutó una
  prueba de imagen DCC/HTILE.
- **Reversibilidad/riesgo:** usar stock evita parches locales; una regla global
  nueva requiere A/B y rollback, por lo que no se añadió.

### P-007 — `VK_EXT_image_drm_format_modifier` en GFX8

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** una aplicación o informe histórico puede buscar la extensión
  para import/export de modifiers DRM.
- **Causa:** el dispositivo RADV GFX8 de esta instalación no expone la
  extensión; no hay evidencia de que deba exponerse.
- **Corrección propuesta:** informar la capacidad real; no fabricar un parche
  que prometa una extensión ausente.
- **Archivos/hash:** validación final JSON/MD, sección Vulkan.
- **Versiones:** loader Vulkan 1.4.328.1; RADV Mesa 25.3.2.
- **Estado anterior:** `UNKNOWN` para la expectativa de la aplicación.
- **Estado posterior:** `NOT_AVAILABLE` — la extensión no aparece con el ICD
  AMD aislado; la disponibilidad para otras GPU no se afirma.
- **Prueba de validación:** `vulkaninfo --summary` con ICD RADV; no se forzó
  una negociación de swapchain.
- **Reversibilidad/riesgo:** sólo diagnóstico; riesgo bajo.

### P-008 — RA24/little-endian en KWin/DRM

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** búsqueda de `RA24`, `Unsupported screen format` o un problema de
  endianess/formato en KWin.
- **Causa:** no se encontró un rastro de RA24 en el repositorio ni en la
  instantánea actual; el issue upstream consultado para RA24 corresponde a
  otra combinación hardware/KWin y no prueba causalidad para Polaris12.
- **Corrección propuesta:** no aplicar un parche little-endian; conservar el
  término como consulta y separar el error de permisos de card1 observado.
- **Archivos/hash:** validación final (`0fea12f9...e1cb`); búsqueda histórica
  en `AUDIT-001` y journal del boot.
- **Versiones:** KWin 6.5.4; Mesa 25.3.2; kernel 6.18.2.
- **Estado anterior:** `UNKNOWN`.
- **Estado posterior:** `NOT_REPRODUCED` — `RA24=0` en el journal del boot; no
  se ejecutó una prueba de conmutación de formatos.
- **Prueba de validación:** `journalctl -b -k`; 14 errores de permiso KWin
  permanecen un asunto separado.
- **Reversibilidad/riesgo:** no hay cambio; riesgo de atribuir erróneamente el
  error de permisos a RA24.

### P-009 — Separación de render KWin/Wayland e Intel del host

- **Tipo de parche:** `CONFIGURATION_CHANGE` (procedimiento propuesto, no aplicado).
- **Síntoma:** la salida física está en Intel, pero KWin/Wayland usa la RX 550
  como renderer; el objetivo VFIO/host independiente no está cumplido.
- **Causa:** dos GPUs activas y una configuración de compositor/permisos que
  no separa de forma demostrable render y display.
- **Corrección propuesta:** primero demostrar una sesión KWin estable con
  render Intel y salida Intel; después evaluar la RX 550 dedicada. No cambiar
  `/dev/dri`, udev, GRUB o servicios en esta fase.
- **Archivos/hash:** validación final MD/JSON; auditoría VFIO bajo
  `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/`.
- **Versiones:** KWin 6.5.4; Mesa 25.3.2; kernel 6.18.2.
- **Estado anterior:** `UNRESOLVED`.
- **Estado posterior:** `UNRESOLVED` — el host depende observablemente de la
  RX 550 para el compositor.
- **Prueba de validación:** `wayland-info`, `qdbus ... supportInformation`,
  `/sys/class/drm` y journal; sólo lectura.
- **Reversibilidad/riesgo:** no se aplicó; cualquier cambio futuro necesita una
  prueba de recovery y de restauración.

### P-010 — `DRI_PRIME` numérico en Xwayland/GL

- **Tipo de parche:** `CONFIGURATION_CHANGE`.
- **Síntoma:** `DRI_PRIME=1` selecciona Intel en la instalación actual aunque
  el operador lo interpretaba como “AMD”.
- **Causa:** el valor es un índice de dispositivo, no un alias por vendor.
- **Corrección propuesta:** usar `DRI_PRIME=1002:699f` o el BDF sólo para el
  proceso objetivo y comprobar renderer/render node; no definirlo globalmente
  sin validar compositor.
- **Archivos/hash:** `state_manager.py` (`ef387e92db437cf2d1a84dccf921c9e927f1e55ab74502c344ec51488eb3f44a`),
  `run_tests.py` (`fa4c488515967e6ed1379bb5891c6235dccca5d77fd077d0ff97fac8add338a6`).
- **Versiones:** Mesa 25.3.2; Xwayland/KWin actuales.
- **Estado anterior:** `PARTIALLY_RESOLVED` — el detector era dinámico, pero
  había fallback a `DRI_PRIME=1`.
- **Estado posterior:** `PARTIALLY_RESOLVED` — se eliminó el fallback numérico;
  la selección por proceso está verificada, la sesión global no.
- **Prueba de validación:** `64/64` checks; `glxinfo` explícito devuelve RX
  550 y `DRI_PRIME=1` devuelve Intel.
- **Reversibilidad/riesgo:** sólo entorno de proceso; riesgo bajo, pero no
  sustituye una prueba del compositor.

### P-011 — Selección RADV por ICD

- **Tipo de parche:** `CONFIGURATION_CHANGE`.
- **Síntoma:** el selector histórico `MESA_VK_DEVICE_SELECT` no fue una
  garantía suficiente; el loader puede enumerar Intel/llvmpipe.
- **Causa:** la selección por entorno depende de la versión y de la ICD activa.
- **Corrección propuesta:** fijar el ICD RADV x86_64 en el proceso y eliminar
  `MESA_VK_DEVICE_SELECT`/`VK_DRIVER_FILES` heredados del entorno.
- **Archivos/hash:** `cap_run.py` (`6919cfd9467b776fccc75abebe629ac22f671020d2295a777ae87c91a92b1469`),
  `tests/run_tests_m1.py` (`4e0fb09700d336bbc680a1ca201d3fe2bc5c6f25bc82a1b6ea45121891d66142`).
- **Versiones:** Vulkan loader 1.4.328.1; Mesa 25.3.2.
- **Estado anterior:** `PARTIALLY_RESOLVED`.
- **Estado posterior:** `PARTIALLY_RESOLVED` — el ICD aislado RADV fue
  observado; no se afirma compatibilidad universal del workaround.
- **Prueba de validación:** `vulkaninfo --summary` con
  `radeon_icd.x86_64.json` devuelve sólo `0x699f`; test M1 `110/110`.
- **Reversibilidad/riesgo:** limpiar variables por proceso; riesgo bajo.

### P-012 — VM faults de storage images R-11

- **Tipo de parche:** `WORKAROUND`.
- **Síntoma:** el generador compute con cuatro storage images provocaba VM
  faults deterministas en la campaña histórica.
- **Causa:** interacción del upload/host y del mapa VM en GFX8; no se atribuyó
  una causa única de kernel/RADV.
- **Corrección propuesta:** evitar el patrón mediante upload host/corrección
  del generador; no añadir un driconf global.
- **Archivos/hash:** `03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp`
  (`7f1bf813d577a456d485a55ae01bd684bd746e9a3e03a084db2edcab57943615`),
  `src/gen.comp` (`d6ab1d1228fd5291c5bd8213df532b6303f9f4cac8e4fc71accb2fbd410dee35`),
  `RESEARCH.md` (`104ececa92ab75926d2f1e589e14db9c435d96a0469e05e15955c0ed2f70677b`).
- **Versiones:** RADV/Mesa 26.2.2 histórico; no revalidado en Mesa 25.3.2.
- **Estado anterior:** `PARTIALLY_RESOLVED` — la corrección histórica tuvo una
  corrida limpia, no una garantía universal.
- **Estado posterior:** `PARTIALLY_RESOLVED` — el código está disponible, pero
  no se volvió a ejecutar en esta instalación.
- **Prueba de validación:** registro histórico de E-03; journal actual no
  muestra VM faults no-PRT en el boot, lo que no sustituye la prueba de carga.
- **Reversibilidad/riesgo:** cambiar sólo el workload; no toca el sistema; el
  riesgo es generalizar demasiado el workaround de upload.

### P-013 — Detector de ring timeout/reset/hang

- **Tipo de parche:** `PATCH_REAL`.
- **Síntoma:** un detector podía contar un aviso PRT o un VM fault aislado como
  reset, mezclando evidencia con causalidad.
- **Causa:** firmas demasiado amplias y ventana de journal ambigua.
- **Corrección propuesta:** regex sólo para reset/hang inequívoco, excluir PRT
  y registrar `checked=false` si el formato/fuente no es fiable.
- **Archivos/hash:** `cap_run.py` (`6919cfd9467b776fccc75abebe629ac22f671020d2295a777ae87c91a92b1469`),
  `tests/run_tests_m1.py` (`4e0fb09700d336bbc680a1ca201d3fe2bc5c6f25bc82a1b6ea45121891d66142`).
- **Versiones:** Python 3.14; kernel 6.18.2.
- **Estado anterior:** `PARTIALLY_RESOLVED` — había tests, pero faltaba
  cobertura de la migración.
- **Estado posterior:** `PARTIALLY_RESOLVED` — tests pasan; no demuestra que el
  sistema no pueda hacer reset bajo carga.
- **Prueba de validación:** `110/110` checks; PRT, VM fault aislado, ring
  timeout y reset se prueban por separado.
- **Reversibilidad/riesgo:** sólo detector/test; riesgo bajo.

### P-014 — BACO y runtime PM

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** las expectativas históricas sobre `power/control`, BACO y
  runtime PM se mezclaban con resultados DPM.
- **Causa:** no hubo un experimento de PM aislado en la instalación actual.
- **Corrección propuesta:** leer `power/control`, `runtime_status` y los
  parámetros del módulo; no forzar BACO, PM, ASPM ni clocks.
- **Archivos/hash:** `cap_run.py`; final validation JSON.
- **Versiones:** módulo amdgpu del kernel 6.18.2; `runpm=-1`; BACO observado
  durante el arranque.
- **Estado anterior:** `UNKNOWN`.
- **Estado posterior:** `UNKNOWN` — `auto/active` es una observación, no una
  prueba de causalidad de rendimiento.
- **Prueba de validación:** snapshot read-only; no hubo escritura de PM.
- **Reversibilidad/riesgo:** sin cambio; forzar PM tendría riesgo alto y queda
  deliberadamente diferido.

### P-015 — DPM/SCLK/MCLK/power cap

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** el cap histórico de 25/35 W, SCLK 350–390/1071 MHz, MCLK
  300/625/1500 MHz y las lecturas de 25 W se interpretaron como un único
  control loop.
- **Causa:** no se aislaron workload, semántica del sensor, política del driver
  y estado térmico.
- **Corrección propuesta:** registrar DPM, cap, `W_SMU`, identidad del workload
  y journal por ventana; no cambiar el cap en esta fase.
- **Archivos/hash:** `cap_run.py`; `RESEARCH.md`; final validation JSON.
- **Versiones:** Mesa 25.3.2/kernel 6.18.2 actuales; histórico 7.2.x/Mesa
  26.2.2.
- **Estado anterior:** `UNKNOWN`.
- **Estado posterior:** `UNKNOWN` — se leyó el estado actual, pero no hubo A/B
  causal.
- **Prueba de validación:** `power1_cap=35 W`, DPM `auto`, SCLK `1046 MHz`
  activo, MCLK `300 MHz` activo; no hubo escritura.
- **Reversibilidad/riesgo:** sin cambio; las escrituras de cap están protegidas y
  requieren una autorización separada.

### P-016 — Firmware/VBIOS y tabla de estados

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** el firmware/VBIOS y la tabla PP aparecieron en el diagnóstico
  histórico.
- **Causa:** no hay prueba de una imagen corrupta o de firmware incompatible en
  el host actual.
- **Corrección propuesta:** registrar la presencia de ROM bar/firmware y sus
  versiones; nunca flashear ni sintetizar un VBIOS.
- **Archivos/hash:** `01-AUDITORIA/FINAL-VALIDATION/*`; package output.
- **Versiones:** `linux-firmware-20251125-1.fc43.noarch`; amdgpu module
  6.18.2.
- **Estado anterior:** `UNKNOWN`.
- **Estado posterior:** `NOT_REPRODUCED` — no se observó un fallo actual; la
  semántica de la imagen sigue sin probarse.
- **Prueba de validación:** presencia de firmware/ROM; no hubo flash ni lectura
  de VBIOS.
- **Reversibilidad/riesgo:** sin cambio; el flashing tendría riesgo alto y no
  forma parte de este repositorio.

### P-017 — Migración Mesa/LLVM/libdrm

- **Tipo de parche:** `UPSTREAM_FIX`.
- **Síntoma:** el stack histórico de Mesa CUSTOM 26.2.2/LLVM 22/libdrm 2.4.134
  difiere de la nueva instalación.
- **Causa:** migración de versión de la distribución, no un defecto específico
  de la RX 550.
- **Corrección propuesta:** usar paquetes stock de Nobara, registrar versiones
  exactas y no copiar la build antigua a `/usr` ni a `/opt`.
- **Archivos/hash:** `tools/validate_rx550_final.py` (`2d7c4c9c8e3e03879f0a5a4c17ab31b618c019781c9cb459d5d38a8d88c435c3`),
  final validation JSON, manifiesto del backup histórico.
- **Versiones:** Mesa 25.3.2, LLVM 21.1.7 y libdrm 2.4.128 actuales; histórico
  Mesa 26.2.2/LLVM 22/libdrm 2.4.134.
- **Estado anterior:** `PARTIALLY_RESOLVED` — la build custom tenía evidencia
  histórica, pero no era un destino de migración.
- **Estado posterior:** `PARTIALLY_RESOLVED` — RADV/radeonsi stock enumeró la
  RX 550; la paridad de rendimiento y cada workload histórico siguen sin
  probarse.
- **Prueba de validación:** procedencia de paquetes y comprobaciones de
  renderer/ICD.
- **Reversibilidad/riesgo:** sin cambios de paquetes; instalar un stack custom
  requeriría un plan separado de build/rollback.

### P-018 — Kalm GPU/system-autopilot como agente actual

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** se buscaron servicios y agentes automáticos como explicación de
  la estabilidad y la propiedad del entorno.
- **Causa:** el P0 histórico los observó; la nueva instalación no contiene las
  mismas unidades.
- **Corrección propuesta:** registrar el estado actual de los servicios y no
  restaurar la unidad histórica desde el backup.
- **Archivos/hash:** `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`,
  final validation JSON.
- **Versiones:** Nobara 43 actual; auditoría histórica 2026-09-24.
- **Estado anterior:** `UNRESOLVED` como agente histórico.
- **Estado posterior:** `OBSOLETE` para la instalación actual; no prueba
  sobre el sistema histórico.
- **Prueba de validación:** unidades `inactive/not-found`; no hubo cambio de
  servicios.
- **Reversibilidad/riesgo:** sin cambio; copiar la unidad antigua sería un
  cambio persistente y queda fuera de alcance.

### P-019 — VFIO y RX 550 dedicada al host

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** objetivo de separar la RX 550 del host Intel para render
  dedicado.
- **Causa:** la placa H81 no ofrece VT-d utilizable, no hay grupos IOMMU
  utilizables y el compositor del host depende observablemente de la RX 550.
- **Corrección propuesta:** no agregar VFIO/modprobe/GRUB hasta que exista
  hardware, aislamiento y recovery validados.
- **Archivos/hash:** `01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-20260925T132242Z.json`
  (`27fc2799b203c9c30f86d0125c59953f7784930fe6d6158dac4f65509517b62e`),
  MD (`7488c63b3579a30eeedd6388a8fef3ca9bec8f9c3a4cdf0bbe4a9c5c9565d5ba`).
- **Versiones:** kernel 6.18.2; evidencia H81/IOMMU de la auditoría read-only.
- **Estado anterior:** `UNRESOLVED`.
- **Estado posterior:** `UNRESOLVED` — la viabilidad sigue siendo negativa; no
  se hizo binding ni cambio de módulo.
- **Prueba de validación:** `/proc/cmdline`, inventario de grupos IOMMU,
  topología PCI y observaciones del renderer del host.
- **Reversibilidad/riesgo:** sin cambio; una configuración incorrecta de VFIO
  podría inutilizar el host y por eso no se intenta.

### P-020 — C1, propiedad, recovery y aislamiento

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** P0 histórico `B__CONTAMINATED_REQUIRES_ISOLATION`, propiedad
  parcial y recovery no validado.
- **Causa:** clientes/agentes/visibilidad de FD y evidencia de almacenamiento
  de la misma ventana incompletos; no hay prueba completa de propiedad.
- **Corrección propuesta:** conservar los gates; no ejecutar C1, no materializar
  runtime v2 y no declarar restore validado.
- **Archivos/hash:** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`,
  `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md`,
  `04-IMPLEMENTACION/c1_isolation_automator.py`.
- **Versiones:** Python 3.14; 54 unit tests con 1 skip.
- **Estado anterior:** `UNRESOLVED`.
- **Estado posterior:** `UNRESOLVED` — la nueva captura no sustituye el gate
  histórico de propiedad/recovery.
- **Prueba de validación:** sólo `unittest`; no `run_c1`, no systemd, no sudo,
  no `/sys` writes.
- **Reversibilidad/riesgo:** sin materialización runtime; se evitó el riesgo
  operativo.

### P-021 — HDD/Btrfs histórico frente a la nueva raíz

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** conflictos y errores históricos de HDD/Btrfs.
- **Causa:** evidencia histórica y topología nueva no describen el mismo
  almacenamiento montado.
- **Corrección propuesta:** no trasladar la conclusión al host actual; exigir
  `findmnt`, identidad y SMART separado antes de investigar.
- **Archivos/hash:** `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`,
  validación final JSON/MD.
- **Versiones:** raíz actual `/dev/sdb3 ext4`; el Btrfs de `sda2` no está
  montado como raíz.
- **Estado anterior:** `UNRESOLVED` para la evidencia HDD/Btrfs.
- **Estado posterior:** `NOT_REPRODUCED` como síntoma actual; salud y causalidad
  `UNKNOWN`.
- **Prueba de validación:** `findmnt`; no hubo SMART, scrub ni escritura.
- **Reversibilidad/riesgo:** sin cambio; los comandos invasivos de
  almacenamiento siguen diferidos.

### P-022 — H12 Wayland/xdg-shell/WSI

- **Tipo de parche:** `DIAGNOSTIC_ONLY`.
- **Síntoma:** historial de H12/WSI y presentación xdg-shell como fuente de
  discrepancias Vulkan/Wayland.
- **Causa:** no se volvió a ejecutar H12 en la nueva instalación; la evidencia
  actual sólo prueba la negociación Wayland general.
- **Corrección propuesta:** conservar el informe H12 como evidencia histórica;
  no atribuirle una corrección de RADV o KWin.
- **Archivos/hash:**
  `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`.
- **Versiones:** evidencia H12 histórica; actual KWin 6.5.4/Wayland.
- **Estado anterior:** `NOT_REPRODUCED`/`UNKNOWN` según el protocolo H12.
- **Estado posterior:** `NOT_REPRODUCED` — no se ejecutó una repetición actual.
- **Prueba de validación:** `wayland-info` y el archivo de evidencia; no hubo
  ejecución H12.
- **Reversibilidad/riesgo:** sin cambio; una repetición debe ser read-only y
  tener un journal de la misma ventana.

## Reglas de instalación y rollback

No hay un instalador de sistema que deba ejecutarse para esta entrega. La
corrección de migración es documental y estática:

1. instalar/verificar paquetes de distribución, no el Mesa CUSTOM histórico;
2. usar los selectores por proceso descritos en `INSTALL.md`;
3. validar BDF, `glxinfo`, RADV y journal antes de cualquier carga;
4. mantener el workload R-11 como alternativa de upload, no como parche de
   kernel;
5. no habilitar BACO, DPM, VFIO, Kalm, modprobe, GRUB, udev o C1 sin una
   autorización distinta.

**Reversibilidad:** no se aplicaron cambios persistentes. Para una sesión con
variables por proceso basta con cerrar el proceso y eliminar las variables
exportadas. No existe un cambio de sistema que deshacer en esta fase.
