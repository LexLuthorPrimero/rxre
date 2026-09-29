# Estado final de problemas — RX 550

**Fecha:** 2026-09-25
**Instalación validada:** Nobara Linux 43, kernel `6.18.2-200.nobara.fc43.x86_64`
**GPU objetivo:** `1002:699f`, BDF `0000:01:00.0`, Polaris12/GFX8, `amdgpu`
**Fuente de observación:** `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json`

## Regla de lectura

La columna **Estado** usa exclusivamente:
`RESOLVED`, `PARTIALLY_RESOLVED`, `UNRESOLVED`, `OBSOLETE`,
`ALREADY_FIXED_UPSTREAM`, `NOT_REPRODUCED`, `UNKNOWN` y
`NOT_AVAILABLE`.

Un hecho observado no se convierte en causalidad. `NOT_REPRODUCED` significa
que el síntoma no apareció en la comprobación actual; no significa que su causa
histórica esté resuelta.

## Matriz de problemas

| ID | Problema histórico o vigente | Síntoma observado | Evidencia y alcance | Corrección o decisión | Validación actual | Estado |
|---|---|---|---|---|---|---|
| RX550-01 | Identidad por `cardN` | La numeración histórica no coincide con la actual | PCI `1002:699f`, BDF, `card2`, `renderD129`, `hwmon1` | Resolver por `vendor:device`; no usar `cardN` como identidad | `tools/validate_rx550_final.py`; `run_tests.py` | `PARTIALLY_RESOLVED` |
| RX550-02 | Régimen E1/E3/E5: 25 W, SCLK 350–390, MCLK alto, 74–92 °C | No se reproduce en el host actual | Auditoría histórica; la instantánea actual no ejecutó campaña | No forzar clocks/cap; conservar línea base y exigir journal | Validación read-only | `NOT_REPRODUCED` |
| RX550-03 | Kalm como causa del régimen | La atribución histórica no se sostiene | Kalm estaba inactivo durante el hecho; unidades actuales `not-found` | Errata; no instalar Kalm para explicar el régimen | Estado de servicios | `OBSOLETE` |
| RX550-04 | `power1_input` como vatímetro | Se debe etiquetar como estimación SMU | Nodo `hwmon1`; lectura actual ~5.1 W | Usar `W_SMU`; no presentarlo como potencia de red | `power1_input_uw=5108000` | `RESOLVED` |
| RX550-05 | Mesa CUSTOM como causa | Build experimental no reproduce E5 | Backup; A/B histórico; no hay `/opt/mesa-*` actual | No migrar la build; usar paquetes de distribución | `rpm -qf` y renderer | `OBSOLETE` |
| RX550-06 | Workarounds RADV/RadeonSI GFX8 | MSAA/DCC/line-filter/VM-map pueden ser sospechosos | Workarounds documentados en Mesa upstream y distro | No duplicar workaround local | RADV arranca; efecto no medido | `ALREADY_FIXED_UPSTREAM` |
| RX550-07 | `VK_EXT_image_drm_format_modifier` | La app puede esperar la extensión | RADV GFX8 no la expone con ICD aislado | Reportar capacidad real; no parchear una extensión ausente | `vulkaninfo` | `NOT_AVAILABLE` |
| RX550-08 | RA24/little-endian | Se buscó un error de formato/endianess | No hay `RA24` en repo ni journal del boot | No aplicar parche little-endian; separar el error de permisos | `RA24=0` | `NOT_REPRODUCED` |
| RX550-09 | KWin/Wayland usa RX550 mientras la salida es Intel | Compositor y display no están separados | `wl_drm`/KWin apuntan a RX550; `card1` Intel; 14 permission-denied | Separar render/display sólo tras prueba de sesión y recovery | `wayland-info`, DBus, sysfs | `UNRESOLVED` |
| RX550-10 | `DRI_PRIME=1` como selector AMD | `DRI_PRIME=1` devuelve Intel | `DRI_PRIME=1002:699f` devuelve RX550 | Selector por proceso y validación de renderer | `glxinfo`; `64/64` | `PARTIALLY_RESOLVED` |
| RX550-11 | `MESA_VK_DEVICE_SELECT` no confiable | El loader puede enumerar Intel/llvmpipe | ICD RADV x86_64 sí devuelve sólo `0x699f` | Fijar ICD y limpiar selectores heredados | `vulkaninfo`; `110/110` | `PARTIALLY_RESOLVED` |
| RX550-12 | R-11 storage-image VM faults | El generador compute histórico provoked faults | Upload host corregido; corrida histórica limpia | Mantener workaround en workload; no global driconf | No repetido en instalación actual | `PARTIALLY_RESOLVED` |
| RX550-13 | Ring timeout/reset/hang | Detector podía mezclar PRT/VM fault con reset | Tests separan PRT, VM fault aislado, ring timeout y reset | Regex conservadora y journal `checked=false` si no es fiable | `110/110`; no prueba de carga | `PARTIALLY_RESOLVED` |
| RX550-14 | BACO/runtime PM | Se mezcló con resultados DPM | `power/control=auto`, `runtime_status=active`, BACO observado | Leer estado; no forzar PM/ASPM | Snapshot | `UNKNOWN` |
| RX550-15 | DPM/SCLK/MCLK/power cap | No hay causalidad aislada del control loop | Estados actuales y datos históricos no se pueden comparar directamente | Registrar por ventana; no cambiar cap | Snapshot | `UNKNOWN` |
| RX550-16 | Firmware/VBIOS/PP table | Posible hipótese de firmware | Firmware/ROM presentes; no se hizo flash | Reportar presencia; nunca flashear | Paquete y sysfs | `NOT_REPRODUCED` |
| RX550-17 | Migración Mesa/LLVM/libdrm | Stack custom 26.2.2/LLVM22 no es el actual | Actual Mesa 25.3.2/LLVM21.1.7/libdrm 2.4.128 | No copiar `/opt` ni `/usr`; fijar versiones | RADV/radeonsi stock | `PARTIALLY_RESOLVED` |
| RX550-18 | Kalm GPU/system-autopilot como agente | Se buscó en el P0 histórico | No hay unidades actuales; no se copiaron | No restaurar unidades históricas | `systemctl` read-only | `OBSOLETE` |
| RX550-19 | VFIO/RX550 dedicada | H81 sin VT-d utilizable; no hay grupos; compositor depende de RX550 | Auditoría VFIO read-only | No modificar cmdline, modules, GRUB o binding | Evidencia VFIO | `UNRESOLVED` |
| RX550-20 | C1/ownership/recovery | P0 contaminado; recovery no validado | Gates y preflight históricos; no runtime C1 | No ejecutar C1 ni declarar restore | 54 unit tests | `UNRESOLVED` |
| RX550-21 | HDD/Btrfs histórico | La raíz actual no usa el Btrfs histórico | `/` en `/dev/sdb3 ext4`; sin SMART | No trasladar causalidad; investigar identidad primero | `findmnt` | `NOT_REPRODUCED` |
| RX550-22 | H12/xdg-shell/WSI | No hay repetición actual del protocolo H12 | Evidencia H12 histórica y Wayland actual | No atribuir una corrección RADV/KWin al informe | `wayland-info` | `NOT_REPRODUCED` |

## Problemas que no deben marcarse como resueltos

1. No hay evidencia suficiente para afirmar una causa del régimen E1/E3/E5.
2. `power1_input` no resuelve la disponibilidad de un vatímetro independiente.
3. La extensión Vulkan ausente en GFX8 no se convierte en un bug corregido.
4. La ausencia de RA24 en este boot no valida todos los paths de KWin.
5. KWin todavía usa la RX550 como renderer y registra errores de permisos sobre
   `card1`; la separación de host no está lograda.
6. La corrección R-11 no se revalidó en Mesa 25.3.2 bajo una campaña actual.
7. No se ejecutó una prueba de estabilidad que cierre reset, ring timeout o VM
   fault bajo carga.
8. VFIO, C1, BACO, DPM y recovery permanecen abiertos o sin fuente suficiente.
9. El árbol histórico contiene artefactos y rutas que requieren una revisión
   de publicación; la nueva captura no elimina el historial previo.

## Correlaciones que deben permanecer explícitas

- Mayor `W_SMU` observado no demuestra mayor consumo de red.
- `power1_cap=35 W` no demuestra que el cap limite el SCLK.
- Un perfil DPM activo no demuestra que BACO o runtime PM sean la causa.
- Una línea PRT no es un reset.
- Que el renderer por defecto sea AMD no invalida que `DRI_PRIME=1` sea Intel.
- Que el host tenga una iGPU no prueba que pueda relinquishir el compositor a
  esa iGPU.
- Una build CUSTOM que arranca no prueba que sea necesaria o mejor.

## Resumen de estado

- Identidad y selectores por proceso: `PARTIALLY_RESOLVED`.
- Métrica `W_SMU` y etiquetas: `RESOLVED` como corrección documental.
- Workarounds Mesa conocidos: `ALREADY_FIXED_UPSTREAM`.
- Historial Kalm/Mesa CUSTOM: `OBSOLETE` como hipótesis de causa.
- Capacidades o síntomas no reproducidos: `NOT_REPRODUCED` o
  `NOT_AVAILABLE` según el caso.
- Estabilidad, DPM causal, VFIO, C1 y recovery: `UNRESOLVED` o `UNKNOWN`.
