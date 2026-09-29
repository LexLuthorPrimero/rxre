# GATE P0 — VALIDEZ EXPERIMENTAL RX550

**Fecha de ejecución principal:** 2026-09-24 07:16:42–07:24:55 (-03)
**Verificación posterior de timers/paths:** 2026-09-24 07:49 (-03)
**Snapshot final sincronizado:** 2026-09-24 07:24:55.809193 (-03)
**Host:** `lex-luthor`
**Kernel observado:** `7.2.6-201.nobara.fc44.x86_64`
**GPU objetivo:** `0000:01:00.0`, `1002:699f`, Polaris12/GFX8, `amdgpu`, `card1`/`renderD129`
**Modo:** **READ-ONLY ESTRICTO**. El gate no detuvo, reinició, habilitó, deshabilitó ni modificó servicios, governors, IRQ, scheduler, read-ahead, runtime PM, ASPM, DPM, power cap, clocks, Mesa, VBIOS, PPTable ni contadores. No se instalaron paquetes, no se ejecutaron benchmarks de campaña, tuning, contadores ni H12. Las escrituras observadas de servicios automáticos se documentan como estado externo al gate.

> **Veredicto del gate:** **B. `CONTAMINATED_REQUIRES_ISOLATION`**.
>
> No es `A. CLEAN_ENOUGH_FOR_EXPERIMENT`: se observaron clientes DRM de usuario sobre la RX550 y controladores automáticos activos que escribieron realmente sobre CPU/IRQ/storage/procesos. No es un veredicto de que algún resultado histórico sea falso; es una condición de validez que exige aislamiento antes de un nuevo A/B.

---

## 0. Método, perturbación y límites

### 0.1 Lecturas realizadas

Se utilizaron únicamente lecturas de:

- `/proc`, `/sys`, `/dev/dri`, `lsof`/`fuser`, `fdinfo` y `ps`.
- `systemctl show/cat/list-timers/list-units`, `journalctl` y `busctl` en modo lectura.
- `lspci`, `lsblk`, `findmnt`, `btrfs filesystem usage`, `iostat`, `sensors`, `cpupower frequency-info`, `powerprofilesctl get/list`.
- Archivos de configuración y scripts existentes, leídos con `cat`/`sed`; no se ejecutaron.
- lecturas de CPU, IRQ y disco de corta duración, explícitamente marcados como observaciones, no como campañas.

No se usó `sudo`, `setpci`, `taskset` para cambiar afinidad, `chrt` para cambiar prioridad, `systemctl stop/disable/mask`, `tee`/ redirecciones hacia sysfs, `dd`, `tee` de counters ni herramientas de tuning.

### 0.2 Evaluación de perturbación

| Lectura | Riesgo de perturbación | Mitigación / tratamiento |
|---|---|---|
| `fdinfo`, `lsof`, `/proc` | Bajo; no abre ni renderiza workloads | Sólo inventario; no se infiere actividad de motor desde un fd abierto |
| `gpu_busy_percent`, hwmon, clocks, VRAM/GTT | Bajo como lectura, pero el acceso al driver puede mantenerlo observable o despierto | Se leyó una sola vez por snapshot; no se activó workload; el estado PM se marcó por separado |
| `power/control`, `runtime_status`, contadores PM | Bajo–medio: una lectura de runtime PM no es una escritura, pero puede participar en el estado observado | Se registró `before/after` cuando fue posible; no se forzó wake ni se cambió `control` |
| `lspci -vvv` | Bajo; lectura de configuración PCI, sin `setpci` | `Capabilities` apareció `<access denied>` sin privilegios; no se interpretó como ASPM definitivo |
| `pp_table`, VBIOS y metadatos PCI | Baja–media; el blob puede ser una lectura grande del driver | Se leyó sin escribir ni decodificar; la semántica queda `UNKNOWN` |
| `journalctl`, `iostat`, scripts de auditoría | Puede añadir CPU/I/O y journals | Se consideró que el propio gate podía aumentar `loadavg`/IO PSI; los picos observados no se atribuyen a una carga externa |
| Muestreo CPU/IRQ de 1 s | observacional, no benchmark | Se etiqueta `OBSERVED`; no se convierte en FPS/frametime ni causalidad |
| D-Bus `get-property` de PowerStation | Baja; consulta de estado, no `Set` | No se usó ningún setter; propiedades escribibles se marcan sólo como capacidad |
| `btrfs filesystem df/stats` con opciones no soportadas | Ninguna mutación; comandos rechazados por sintaxis | Se conserva el resultado de `filesystem usage`; no se fuerza ninguna operación de filesystem |

**Nota de autoinferencia:** la auditoría y la sesión `opencode` estaban activas. `system-autopilot` decidió `performance` a las 07:23:53–54 usando `loadavg`; por tanto, el cambio de governor se registra como **`OBSERVED`**, pero su condición natural fuera de esta auditoría queda **`CONFLICT`/`UNKNOWN`**. La existencia/capacidad del automatismo sigue confirmada.

### 0.3 Verificación posterior de timers y paths

A las 07:49 (-03), después del snapshot final y sin cambiar nada, `systemctl list-units
--type=path` mostró únicamente `systemd-ask-password-console.path`,
`systemd-ask-password-plymouth.path` y `systemd-ask-password-wall.path`; no apareció un
path unit de workload, GPU o almacenamiento. Los timers de `system-autopilot`,
`sysstat-collect`, `sys-tuned` y `dnf-makecache` seguían activos. Esta lectura posterior
no modifica el snapshot de 07:24 y confirma que el aislamiento futuro debe cubrir también
la continuidad de timers, no sólo el instante de la medición.

---

## 1. Identidad y estado base

| Campo | Observación actual | Método/evidencia | Interpretación | Limitación | Impacto | Estado | Siguiente acción posible |
|---|---|---|---|---|---|---|---|
| BDF | `0000:01:00.0` | `lspci`, sysfs | RX550 identificada por PCI, no por `cardN` | Ninguna relevante para identidad | Define el objetivo de todos los clientes | `CONFIRMED` | Mantener BDF en cada corrida |
| Identidad PCI | `1002:699f`, subsistema `1002:0b04`, revisión `0xc7` | `/sys/class/drm/card1/device`, `lspci` | La placa actual es revisión `c7`; no es `CF` | No prueba por sí sola containment | Cierra la identidad de revisión; no cierra power containment | `CONFIRMED` | Usar `c7` en el informe; no activar la ruta hipotética `CF` |
| Kernel | `7.2.6-201.nobara.fc44.x86_64` | `uname -a` | La línea base actual no es el kernel histórico `7.2.4` | No sabemos qué cambios exactos hay entre ambos | Comparaciones entre sesiones requieren cautela | `CONFIRMED` | Registrar kernel en todos los metadatos |
| Display | `card0` HDMI/VGA `connected`; `card1` DVI/HDMI `disconnected` | DRM connector status | La RX550 no presenta pantalla activa en este snapshot | Xwayland puede abrir card1 sin presentar | Reduce la atribución de la capa de presentación; no elimina clientes de render | `CONFIRMED` | Mantener display Intel como precondición |
| Firmware visible | VBIOS `xxx-xxx-xxx`, build `565939`; journal: `015.050.002.001.000000`, fecha `2021/05/12` | sysfs + kernel journal | Hay metadatos VBIOS legibles | No se decodificó ni modificó VBIOS | Importante para revisión/power, no para ganancia | `OBSERVED` | No tocar; conservar metadatos |
| PPTable | `pp_table` devuelve blob binario; `ppfeaturemask` de módulo `0xfff7bfff` | lectura sysfs/module params | Existe metadato, no semántica interpretada | No se puede probar tabla efectiva sin más evidencia | No permite atribuir power containment | `UNKNOWN` | Mantener como no interpretado |

---

## 2. Objetivo 1 — Ownership y clientes GPU

### 2.1 Clientes encontrados

| Cliente | PID/tipo | Handle abierto | `fdinfo` relevante | Atribución posible | Estado |
|---|---:|---|---|---|---|
| `Xwayland` | 2671, compositor/Xwayland | `/dev/dri/card1` FD 13 | `drm-driver=amdgpu`, `drm-client-id=74`, `drm-pdev=0000:01:00.0`; 136 KiB VRAM solicitada, 2184 KiB GTT resident; contadores de motor ausentes | Tiene un cliente DRM de la RX550; no hay evidencia de que presente o renderice con ella | `PARTIAL` |
| Proceso GPU de `ChatGPT` | 11399, aplicación Electron/Chromium | `/dev/dri/renderD129` FD 27 | `drm-driver=amdgpu`, `drm-client-id=118`, `drm-pdev=0000:01:00.0`; 152 KiB VRAM residente, 2 MiB GTT residente; contadores de motor ausentes | Es un cliente real de la RX550; no se puede atribuir trabajo de motor, frametime o presentación | `PARTIAL` |
| `kwin_wayland` | 2457 | No se encontró FD `card1`/`renderD129` en la enumeración del usuario; usa display Intel | política de scheduling observada por otro agente | No se atribuyó actividad a RX550 | `UNKNOWN` |
| `kalm-gpu` | 10441, root | No se pudo enumerar su espacio de nombres de FDs sin sudo; el código fuente encuentra `/sys/class/drm/card*/device` AMD | Lee hwmon y tiene capacidad de escritura | Capacidad de interferencia `OBSERVED`; efecto actual no demostrado | `POSSIBLE` |
| `PowerStation` | 955, root | D-Bus/card1 log; no FD cliente DRM visible | Expone `card1` y propiedades de clock escribibles, pero sin interfaz TDP AMD y `ManualClock=false` | Puede ser cliente/controlador potencial; no se observó escritura actual | `UNKNOWN` |

### 2.2 Lo que sí y no se puede atribuir

- Un FD abierto demuestra **acceso de cliente**, no actividad significativa.
- `drm-client-id`, VRAM/GTT y `pasid` permiten separar clientes y memoria, pero no la semántica de actividad del motor.
- `gpu_busy_percent=0` es un proxy global; no demuestra que Xwayland/ChatGPT estén inactivos.
- `lsof` no pudo cerrar completamente el espacio de nombres por los overlays Docker y falta de privilegios root; la lista es `PARTIAL`, no completa.
- `Xwayland` abre `card1` aunque los connectors de la RX550 estén desconectados; no se infiere presentación.

### 2.3 Clasificación

- **OWNERSHIP:** `PARTIAL`.
- **CONTAMINATION de clientes GPU:** `POSSIBLE`; no se observó trabajo de motor atribuible, pero hay clientes RX550 abiertos.
- **Riesgo:** una medición de la RX550 puede incluir trabajo no atribuido de ChatGPT/Xwayland o de un cliente root no visible.

---

## 3. Objetivo 2 — Agentes automáticos y servicios

### 3.1 Inventario y evidencia

| Agente | Estado/PID | Capacidad documentada | Actividad/efecto observado | Posible interferencia | Estado |
|---|---|---|---|---|---|
| `system-autopilot.timer` | `enabled/active`, cada 2 min; oneshot PIDs variables | Script escribe governor, IRQ39, sysctls de red, scheduler, read-ahead y `renice` | Journal 07:23:53–54: escribió los 8 governors a `performance`, IRQ39, scheduler/read-ahead y `renice` a kwin | **Directamente observada**; CPU, IRQ, almacenamiento y prioridad | `OBSERVED` |
| `sys-tuned.timer` | `enabled/active`, cada 30 min; último ciclo 07:01 | Script escribe `schedutil`, swappiness, `mq-deadline`, read-ahead 128, IRQ39 y red | Su existencia y código están observados; su efecto se solapa con autopilot | **Conflicto de control**; el valor final depende del último ciclo | `OBSERVED/CONFLICT` |
| `kalm.service` / `kalmd` | `enabled/active`, PID 24083, loop 15 s | Detecta MSI IRQs y escribe `smp_affinity_list` si cambia | Journal 15:54:08: `IRQ 42 → CPU1`; desde entonces continúa `omitiendo` IRQ 29–35 cada 15 s | **Directamente observada** sobre IRQ de la RX550 y otros IRQs | `OBSERVED` |
| `kalm-cpu.service` | `enabled`, `active/exited`, oneshot de boot | Script asigna IRQ DRM a CPU2 | Se ejecutó al arrancar; IRQ 42 actual está en CPU1, por lo que su efecto final no queda atribuido | Posible competencia de afinidad; no actual claramente demostrada | `PARTIAL` |
| `kalm-gpu.service` | `enabled/active`, PID 10441 | Código fuente leído: sondeo cada 2 s; puede escribir `power1_cap`, `power_dpm_force_performance_level`, `pp_dpm_sclk/mclk` | 100 reinicios fallidos históricos por `EBUSY` al leer `power1_cap_max`; desde 15:02 proceso activo, sin eventos de escritura actuales; cap actual 35 W/auto | **Capacidad de modificar la GPU confirmada; efecto actual no observado** | `POSSIBLE` |
| `kalm-lite.service` | `enabled/active`, PID 3753, sondeo cada 10 s | Lee PSI y puede escribir swappiness/dirty ratios | IO PSI era 12–43% en lecturas; valores actuales 10/5/1; no hay registro de ajuste | Puede cambiar respuesta de memoria/I/O bajo presión | `POSSIBLE` |
| `irqbalance.service` | `enabled/active`, PID 951 | Rebalancea IRQs; `/proc/irq` muestra afinidades activas | Config `IRQBALANCE_BANNED_CPUS=0` fue descartada por el daemon; eventos térmicos fallaron | Competencia con kalmd/autopilot; no se probó migración | `POSSIBLE` |
| `power-profiles-daemon` | `enabled/active`, PID 3758 | Perfil CPU; `intel_pstate` | `balanced`; no se observó setter | Puede actuar sobre política/frecuencia, no se observó cambio durante el gate | `POSSIBLE` |
| `powerstation.service` | `enabled/active`, PID 955 | Descubre `card1`; D-Bus expone propiedades de clock escribibles | Log: card1 AMD sin interfaz TDP; DBus `ManualClock=false`, `GpuBusyPercent=0`; no se observó escritura | Controlador potencial; efecto AMD actual `UNKNOWN` | `UNKNOWN` |
| `scx_loader.service` | `active/running`, unidad disabled, PID 4077 | Loader D-Bus de sched-ext | No se encontró scheduler sched-ext activo; `/proc/cmdline` no lo selecciona | No hay evidencia actual de efecto | `UNKNOWN` |
| `rtkit-daemon` | `enabled/active`, PID 956 | Cambios RT/high-priority para hilos de audio y Firefox | Journal muestra hilos RT de audio y Firefox | Puede afectar CPU general, no GPU directo | `OBSERVED` |
| `crond` | `enabled/active`, PID 1257 | Cron de usuario: `trading-sim/auto_signal.sh` cada hora | El script descarga datos, hace copias de seguridad y llama API; no hay registro en la ventana M1 23:50–00:20 | Posible solapamiento histórico; no se observó ejecución actual | `POSSIBLE` |
| `/etc/cron.daily/brave-browser` | Archivo daily ejecutable | El script sale explícitamente con `exit 0`; no añade repositorio | No se observó efecto actual; `/etc/cron.d/0hourly` es el wrapper estándar | Bajo | `OBSERVED` |
| `sysstat-collect.timer` | `enabled/active`, cada 10 min | Escribe estadísticas de sistema | Timer activo; no modifica GPU/CPU governor por código leído | I/O menor potencial | `POSSIBLE` |
| `dnf-makecache.timer` | `enabled/active`, ~3 h + delay | Sólo metadatos de paquetes | Activo; no toca GPU/IRQ por definición | I/O/red menor, no principal | `PARTIAL` |

### 3.2 Hashes de procedencia

Se leyeron y hasharon, sin modificar:

```text
61519cfe085860e93a087e0a299913c48741500c3787c02eca126480d0fee3ea  /usr/local/bin/system-autopilot.sh
c4f94196faa3f11bcfcd75e12264dd6bfb7857e26f7ec6dd0e87b05f2823d49e  /usr/local/bin/sys-tuned.sh
c78581bf4670f5e0a1698519298f1557167644219bab9dc8f152619740c493b9  /usr/local/bin/kalm-cpu-apply.sh
5e0a682cd446057dfa0f3f84e33cd7870a0e0faf36fd1659b3a841f8f753d7c4  /opt/kalm/kalmd.py
538648d9f8afd6fcd3bc9239123c50a1d0bf2c1f5e8481aec3187cbebeaace6a  /usr/local/bin/kalm-lite.py
a1e701768297195945ebe9b5fcbb431430a37b98c28481f67bf5017138d0c1bd  /usr/local/bin/kalm-gpu
```

### 3.3 Separación existencia/capacidad/actividad/efecto

- **Existencia:** `OBSERVED` para autopilot, sys-tuned, Kalm, irqbalance, Kalm GPU/CPU/lite, PowerStation y cron.
- **Capacidad:** `OBSERVED` en los scripts que contienen escrituras; no se confunde con ejecución.
- **Actividad:** `OBSERVED` para timers/daemon; `OBSERVED` para ciclos autopilot y escrituras de kalmd.
- **Efecto:** `OBSERVED` para CPU governor/IRQ39/almacenamiento/prioridades y afinidad IRQ 42; `UNKNOWN` para clientes GPU y kalm-gpu cap/DPM en este instante.

---

## 4. Objetivo 3 — CPU

| Hallazgo | Evidencia | Interpretación | Limitación | Impacto FPS/frametime | Estado | Siguiente acción posible |
|---|---|---|---|---|---|---|
| CPU | i7-4790, 4C/8T, 0–7 online; `intel_cpufreq`; `intel_pstate` passive | El governor y la frecuencia pueden ser afectados por autopilot/sys-tuned | Governor/frecuencia son dinámicos | Alto si cambia durante un frame o una corrida | `OBSERVED` | Registrar pre/post y rangos por corrida |
| Governor | Al snapshot 07:24:55, las 8 políticas son `performance`; a las 07:16:26 eran `schedutil` | Oscilación observada; no es una línea base estable | El governor `performance` observado puede haber sido inducido por el `loadavg` de la auditoría | Alto sobre ejecución de CPU y frametime | `CONFLICT` | No A/B hasta aislar autopilot/sys-tuned o documentar excepción |
| Frecuencia | 3.59–4.00 GHz en el snapshot; límites 0.8–4.0 GHz | Boost activo; no hay prueba de limitación por frecuencia en este snapshot | `scaling_cur_freq` es instante y no prueba esfuerzo | Medio–alto | `OBSERVED` | Usar rango y governor en cada ventana |
| Boost | `intel_pstate/no_turbo=0`, `status=passive`, `turbo_pct=13` | Turbo habilitado | `intel_pstate` pasivo no es el governor activo | Medio | `OBSERVED` | No modificar |
| Utilización | Muestra CPU de 1 s: busy 9.08%, iowait 0.25%; `loadavg` 1.28/2.24/3.58 en una lectura | No hay evidencia de CPU-bound en esa muestra | Una muestra no representa frametime; el propio gate/I/O puede alterarla | No permite declarar una limitación de ejecución de CPU | `UNKNOWN` | Caracterización CPU en gate posterior, sin benchmark de campaña |
| Presión | CPU PSI 0; memory PSI ~0.38–0.74; IO PSI muy variable | La presión de CPU no era el problema del snapshot; I/O sí merece atención | PSI no es atribución por proceso | frametime/p99 posible por I/O | `OBSERVED` | Aislar almacenamiento/IO antes de comparar |
| Scheduling | `kwin_wayland` está `SCHED_RR|SCHED_RESET_ON_FORK`, prioridad 1; `opencode`/ChatGPT `SCHED_OTHER` | Hay política real de compositor y procesos relevantes | No se capturó tiempo de CPU por thread durante una workload | Posible influencia en WSI/CPU | `OBSERVED` | Registrar prioridades sin cambiarlas |

**Conclusión CPU:** no se declara `CPU-bound`. La limitación observable principal es la **inestabilidad del entorno de governor**, no una medición de ejecución del workload.

---

## 5. Objetivo 4 — Térmica

| Sensor | Valor actual/observado | Límite documentado | Interpretación | Estado |
|---|---:|---:|---|---|
| GPU borde | 34–35 °C | `temp1_crit=97 °C` | Muy por debajo del límite; no hay throttling actual | `OBSERVED` |
| CPU paquete | 36–41 °C | coretemp high 80 °C, crit 100 °C | Sin throttling térmico actual | `OBSERVED` |
| CPU núcleos | 30–36 °C en la lectura de sensores | high 80 °C | Sin evidencia de throttling de núcleo actual | `OBSERVED` |
| ACPI zones | 27.8–37 °C; active 55/80 °C, critical 105/108 °C | Tipos y umbrales del kernel | Son zonas ACPI; no se deben identificar sin más con el package CPU | `DOCUMENTED` |
| GPU histórico | R-4B observó≈92 °C y caída SCLK 734/1071→551 en ventanas tardías | 90 °C fue confound/abort de protocolo, no límite universal | La historia demuestra riesgo térmico bajo carga, no estado actual | `DOCUMENTED/REQUIRES_REVIEW` |

No se inventó umbral. `temp1_crit` es un valor expuesto por hwmon; no se usó como umbral experimental. No hubo throttling actual observado, pero el historial R-4B ya es `INCONCLUSIVE` por confound térmico y no se reabre.

---

## 6. Objetivo 5 — IRQ y scheduler

| IRQ/dispositivo | Afinidad actual | Contadores/actividad | Responsable potencial | Estado |
|---|---|---|---|---|
| IRQ 27 / AHCI | CPU3 | delta observado 11 en una ventana de 1 s | Kernel/irqbalance/kalm | `OBSERVED` |
| IRQ 39 / `enp3s0` | CPU2–3,6–7 | delta observado 2 | `system-autopilot` escribe `cc`; irqbalance también activo | `CONFLICT` |
| IRQ 40 / i915 | CPU1 | delta observado 120 | irqbalance/kalm; no es RX550 | `OBSERVED` |
| IRQ 42 / amdgpu RX550 | CPU1 | IRQ total observado; kalmd escribió `IRQ 42 → CPU1` a las 15:54:08 | `kalm`, `kalm-cpu`/irqbalance | `OBSERVED` |

- La afinidad de IRQ 42 es `smp_affinity=02`, `smp_affinity_list=1`, `effective=1`.
- `kalm` no logra aplicar sus políticas a IRQs 29–35 porque no existen como directorios `/proc/irq`; continua logged `omitiendo`.
- `irqbalance` está activo, pero su config de CPU0 fue descartada y no inicializó eventos térmicos.
- Los IRQ 27/39/40/42 son MSI y no exponen `/proc/irq/<n>/thread`; por tanto no se pudo atribuir un hilo kernel individual a IRQ 42. Se observaron `ksoftirqd/0..7` en CPU 0–7, pero su política/afinidad por IRQ es `UNKNOWN`.
- No se observó migración de IRQ 42 durante la ventana corta; no se mide jitter/contención de frametime.
- No se cambió ninguna afinidad.

**Conclusión:** existe una fuente plausible y parcialmente observada de variación de IRQ; no se demuestra que haya causado un frametime concreto. `CONFLICT` para una línea base de IRQ no aislada.

---

## 7. Objetivo 6 — HDD/almacenamiento

| Hallazgo | Evidencia actual | Interpretación | Limitación | Impacto | Estado |
|---|---|---|---|---|---|
| Dispositivo | `sda`, Samsung HM500JI, 465.8 GiB, rotational=1 | El sistema y home están sobre HDD mecánico | No es NVMe | Alto para stalls/I/O | `CONFIRMED` |
| Planificador | `mq-deadline` activo | Valor actual, pero autopilot lo reescribe | No equivale a causalidad de frametime | Medio–alto | `OBSERVED` |
| Read-ahead | `256 KiB` | Coincide con el último ciclo autopilot; sys-tuned propone 128 | Hay dos scripts con valores distintos | Alto para E/S | `CONFLICT` |
| Filesystem | `/` y `/home` en Btrfs en el mismo `sda2`, `compress=zstd:1`; `/boot` ext4 | Btrfs comprime y comparte HDD con el sistema | No se midió compresión por frame | Medio | `OBSERVED` |
| Espacio | Btrfs: 452 GiB totales, ~22 GiB unallocated, ~78 GiB free estimado; no missing | No hay evidencia de filesystem lleno | No se debe confundir free con rendimiento | Bajo ahora | `OBSERVED` |
| Actividad | `iostat` 3×1 s: ráfagas de ~27.6% y 52% con await ~130/201 ms; ventana posterior sin sectores | Hay ráfagas y await alto, pero no actividad sostenida en la ventana final | El gate pudo generar registro/I/O; no hay atribución por procesos root | Alto si coincide con frame | `POSSIBLE/CONFLICT` |
| PSI | IO PSI avg10 llegó a 12.88–42.79%; final 12.88/13.17/19.49 | Hay presión de I/O en el período | No prueba que el benchmark causara el I/O | p99/frametime | `OBSERVED` |
| Errores | Journal sin I/O error/reset/medium error; Btrfs muestra errores de lectura/escritura al montar, no corrupción | No se observó un fallo actual del disco | SMART completo no fue ejecutado por la frontera read-only/sin root | Riesgo actual no cuantificado | `PARTIAL` |
| Procesos | `opencode`, ChatGPT, Baloo y otros tienen I/O acumulado; deltas de 1 s no mostraron I/O de disco significativo | Hay procesos de usuario que pueden acceder al mismo HDD | `/proc/io` root no fue visible sin sudo | Posible | `UNKNOWN` |

**Conclusión de almacenamiento:** no se declara HDD roto ni causante. Sí se clasifica como `POSSIBLE/CONFLICT` para validez de frametime hasta que una corrida futura tenga snapshot de I/O y clientes.

---

## 8. Objetivo 7 — Runtime PM de la RX550

| Campo | Valor actual | Interpretación | Estado |
|---|---:|---|---|
| `power/control` BDF/card1 | `auto` | Control automático; no se escribió | `OBSERVED` |
| `runtime_status` | `active` | El dispositivo estaba activo en el snapshot | `OBSERVED` |
| `runtime_active_time` | `59,140,002 ms` | Mayormente activo desde boot | `OBSERVED` |
| `runtime_suspended_time` | `1,291,399 ms` | Hubo suspensión, pero fue minoritaria | `OBSERVED` |
| `autosuspend_delay_ms` | `5000` | El kernel podría suspender tras 5 s de inactividad | `DOCUMENTED` |
| `wakeup` | `disabled` | No hay wakeup PME habilitado | `OBSERVED` |
| Kernel PM | Journal: `Using BACO for runtime pm`; PME soporta D1/D2/D3hot/D3cold | El kernel mantiene un camino runtime PM | `DOCUMENTED` |
| DRM PM | `/sys/class/drm/card1/device/power` resuelve al mismo BDF PCI | No se encontró un nodo DRAM PM separado | `PARTIALLY_CHARACTERIZED` |
| Connectors | card1 disconnected; card0 connected | No hay scanout de RX550 en este snapshot | `OBSERVED` |
| Clientes | ChatGPT mantiene renderD129; Xwayland card1 | Los clientes pueden mantener runtime activo o sólo tener descriptores | `POSSIBLE` |
| ASPM | policy=`default`; `lspci` capabilities sin acceso | No se puede afirmar L0s/L1 efectivo ni transición | `UNKNOWN` |

No se forzó wake, no se abrió una aplicación para despertar la GPU y no se escribió `power/control`. La diferencia entre **PCI runtime PM**, **actividad de clientes DRM** y **workload GPU** permanece explícitamente separada.

---

## 9. Objetivo 8 — PCI y power containment

| Campo | Evidencia | Interpretación | Estado |
|---|---|---|---|
| Link negociado | `5.0 GT/s`, `x4` | Baseline local Gen2×4 | `CONFIRMED` |
| Link máximo | `8.0 GT/s`, `x8` | Capacidad nominal del endpoint | `CONFIRMED` |
| Lectura DPM PCIe | `pp_dpm_pcie` muestra una tabla con `5.0GT/s,x16 *`; no se usa para el enlace real | La tabla DPM no coincide con el link observado y no se fuerza su interpretación | `NOT_INFERABLE` |
| ASPM | `pcie_aspm=parameters/policy=default`; capabilities PCI no legibles | Sólo se conoce policy, no estado effective | `PARTIALLY_CHARACTERIZED` |
| Power cap | `power1_cap=35,000,000`, default=max=35,000,000, min=0 | Cap vigente 35 W | `OBSERVED` |
| `power1_input` | 2,965,000 µW = 2.965 W | `W_SMU`; no vatímetro | `OBSERVED` |
| DPM | `power_dpm_force_performance_level=auto`, `power_dpm_state=performance`, `pp_cur_state=1` | Estado observado; no se fuerza una interpretación adicional de los campos | `OBSERVED` |
| Profile | `3D_FULL_SCREEN` activo; MCLK `3/16/20` en tabla | La tabla no prueba trigger local ni causalidad | `PARTIALLY_CHARACTERIZED` |
| PPTable/SMU | `pp_table` blob; `smu_pptable_id=-1`; VBIOS build 565939 | Hay metadatos, no hay interpretación de tabla | `UNKNOWN` |
| Containment | No hay nodo/código fuente local suficiente para probar la ruta para revisión c7 | La hipótesis previa `699F:CF` no se aplica a la revisión actual observada | `UNKNOWN` |

**Relación que queda vigente:**

```text
power1_cap = límite configurado 35 W
power1_input = W_SMU/estimador SMU ≈ 2.965 W
physical electrical power = NO MEDIDO / NO INFERIBLE
```

No se escribió `power1_cap`, no se usó `setpci`, no se tocó PPTable/VBIOS.

---

## 10. Objetivo 9 — Snapshot de telemetría sin alterar el sistema

Snapshot final (07:24:55):

| Señal | Valor | Atribución disponible |
|---|---:|---|
| GPU busy | `0 %` | Global proxy; no por cliente |
| mem busy | `0 %` | Proxy; no bandwidth |
| SCLK | `214 MHz` | hwmon actual |
| MCLK | `300 MHz` | hwmon actual |
| GPU temp | `35 °C` | Sensor hwmon |
| W_SMU | `2.965 W` | Estimador SMU |
| power cap | `35 W` | Configuración hwmon |
| VRAM used | `5,595,136 bytes` | Global; no asignable a cliente sin fdinfo adicional |
| GTT used | `12,066,816 bytes` | Global; no prueba paging/eviction |
| Governor CPU | `performance` en los 8 políticas | Estado de configuración; puede cambiar por autopilot |
| Frecuencia CPU | 3.59–4.00 GHz | Instantánea; no frametime |
| Temperatura CPU | 41 °C para el paquete al final; 30–36 °C en núcleos en una lectura anterior | Sensor; no throttling actual |
| Runtime PM | `auto/active`, active 59.14M ms, suspended 1.291M ms | Estado, no workload |
| IO PSI | avg10 12.88%, avg60 13.17%, avg300 19.49% | Presión, no identifica el autor |
| Clients | Xwayland card1; ChatGPT renderD129 | Handles, no engine activity |

El snapshot no es benchmark, no mide FPS/frametime, no fuerza workload y no permite atribuir causalidad.

---

## 11. Objetivo 10 — Cruce con histórico

| Experimento | Evidencia histórica | Gate actual | Estado de revisión |
|---|---|---|---|
| M1 35/30 W | 12.27 W, ΔSCLK=0, no discriminativo | El cap actual es 35 W; `kalm-gpu` tiene capacidad de escribirlo; el cron horario pudo cruzar la ventana 00:00 | `REQUIRES_REVIEW` ambiental; no borrar resultado |
| FASE B cap probe | 25–35 W plano para workloads probados | Autopilot/sys-tuned/kalm/IRQ/almacenamiento activos; no hay snapshot completo de propiedad/clientes en cada corrida | `REQUIRES_REVIEW` de validez; conclusión histórica se conserva |
| FASE F | Diseñada, no ejecutada | No hay resultado que invalidar; el gate es precondición | `NOT_APPLICABLE` |
| H12-3 | Smoke aprobado sólo para ciclo de vida host-side; ownership/colas/PCI no demostrados | Hay clientes RX550 abiertos; no se puede transferir propiedad efectiva | `REQUIRES_REVIEW` sólo para extrapolación de propiedad |
| H12-4 | Implementado, smoke no ejecutado | No se comparó ni se ejecutó | `NOT_APPLICABLE` |
| R-4B v2.3 | S2 PARADA_D, veredicto `INCONCLUSIVE`, confound térmico documentado | El entorno actual confirma IRQ/autopilot y riesgo de clientes; no se reabre S2 | `INCONCLUSIVE` conservado |
| F2 | 2× fetches → ~2× frametime, W_SMU estable | El estado actual tiene I/O PSI/agentes; no hay snapshot de clientes de la corrida histórica | `REQUIRES_REVIEW` ambiental; número no se altera |
| E-02/E-03 | MCLK/W_SMU y frametime históricos; E-02 no reproducible | No hay prueba de que el estado actual sea igual al histórico; no reinterpretar | `REQUIRES_REVIEW`/histórico |

**Regla de trazabilidad:** una condición actual puede marcar `REQUIRES_REVIEW`; no se borra ni se convierte un resultado histórico en falso por inferencia.

---

## 12. Objetivo 11 — Estado del gate

### 12.1 Hallazgos agregados

- **OWNERSHIP:** `PARTIAL` — dos clientes de usuario identificados; espacios de nombres root incompletos; no hay contadores de motor.
- **GPU client contamination:** `POSSIBLE` — handles y memoria asignada; actividad no atribuible.
- **Environment contamination:** `OBSERVED` — autopilot y kalmd escribieron durante el gate; IRQ 42 CPU1 fue escrito por kalmd; el governor CPU cambió a performance.
- **CPU/thermal:** `PARTIAL/POSSIBLE` — no throttling actual, pero governor/config no estable y no hay limitación de ejecución atribuible.
- **IRQ/scheduler:** `CONFLICT/POSSIBLE` — múltiples escritores activos; no se midió jitter.
- **Almacenamiento:** `POSSIBLE/CONFLICT` — presión IO transitoria y picos de utilización; el propio gate pudo contribuirlos; no hay error actual.
- **Runtime PM:** `PARTIALLY_CHARACTERIZED` — auto/active, sin wakeup, sin D3 explícito; no se separó cliente de workload.
- **PCI/power:** `PARTIALLY_CHARACTERIZED` — revisión c7, link Gen2×4, cap 35 W y W_SMU separados; containment no verificable.

### 12.2 Decisión

### Decisión: **B. `CONTAMINATED_REQUIRES_ISOLATION`**

La clasificación no afirma que todos los resultados históricos sean inválidos. Afirma que el entorno actual no ofrece una línea base suficientemente aislada para el siguiente A/B, porque:

1. hay clientes DRM de la RX550 abiertos;
2. `system-autopilot` está activo y ejecutó escrituras reales;
3. `kalm.service` está activo y escribió la afinidad de IRQ 42;
4. `kalm-gpu` está activo y tiene capacidad de escribir cap/DPM;
5. `irqbalance` y otros autores siguen activos;
6. el almacenamiento presenta presión transitoria y no hay atribución por proceso;
7. no existe una medición de actividad de motor por cliente.

No se elige `A` por ausencia de una prueba de carga; se elige `B` porque la contaminación potencial tiene evidencia positiva de existencia y actividad.

---

## 13. Objetivo 12 — Siguiente decisión

### 13.1 Qué debe aislarse antes de cualquier A/B

No se ejecutó ninguna de estas operaciones. Antes de una nueva medición de rendimiento, el protocolo debe tener una decisión explícita sobre:

1. **Clientes DRM:** separar el proceso de prueba de cualquier `Xwayland`, ChatGPT u otro cliente de `card1`/`renderD129`; confirmar que sólo el proceso de prueba tiene el handle objetivo.
2. **Autopilot:** decidir si el timer puede permanecer; si no, requiere autorización y ventana de aislamiento. No desactivar en este gate.
3. **sys-tuned:** resolver la competencia de governor/read-ahead/IRQ con autopilot; registrar el valor final antes de cada corrida.
4. **kalmd/kalm-cpu/irqbalance:** documentar una única política de IRQ o obtener autorización para un intervalo de aislamiento; no cambiar afinidad desde este gate.
5. **kalm-gpu:** documentar explícitamente si su proceso puede escribir cap/DPM; no permitir que un A/B de cap se solape con un daemon que pueda escribirlo.
6. **PowerStation/PPD/rtkit/scx_loader:** registrar estado y efecto; no asumir que “active” significa “modificó el benchmark”.
7. **Almacenamiento:** confirmar scheduler/read-ahead, compresión Btrfs y que no hay presión IO/otro indexador; no provocar carga.
8. **CPU/PM:** guardar governor, frecuencia, loadavg, PSI, temperatura y presión por ventana; no declarar CPU-bound por una sola lectura.
9. **Runtime PM:** usar sólo lecturas pre/post; no forzar wake ni escribir `power/control`. Si el runtime PM resulta relevante, diseñar un A/B separado y autorizado.
10. **Historial:** revisar M1/FASE B/F2/E-03 con los nuevos metadatos de agentes/clientes; no rehacerlos automáticamente.

### 13.2 Siguiente rama si se aísla

- Entorno limpio → **caracterización workload CPU/GPU/WSI**, comenzando por metadatos read-only y, más tarde, una workload controlada y autorizada.
- Runtime PM permanece activo → diseñar posteriormente un A/B específico; no ejecutarlo ahora.
- Problema de CPU/thermal → resolver esa rama antes del tuning GPU.
- Problema de PCI/containment → resolverlo antes de interpretar los experimentos de cap.
- Counters → permanece P3 y congelado; no es el siguiente paso.

---

## 14. Resultado final

**Gate P0: B — `CONTAMINATED_REQUIRES_ISOLATION`.**

El gate fue READ-ONLY. No se optimizó, no se reescribió código, no se programaron contadores, no se modificó H12 y no se ejecutó ningún benchmark de campaña. La documentación de este gate queda como evidencia actual y las inferencias históricas están separadas y marcadas para revisión, no para borrado.

**Archivos de evidencia primaria usados:** `lsof`, `fuser`, `/proc/*/fdinfo`, `/proc/interrupts`, `/sys/class/drm/card1/device`, `/sys/bus/pci/devices/0000:01:00.0`, `systemctl`, `journalctl`, `busctl`, `iostat`, `sensors`, `cpupower`, `powerprofilesctl`, `lsblk`, `findmnt`, Btrfs y los scripts/unidades listados en §3.2.
