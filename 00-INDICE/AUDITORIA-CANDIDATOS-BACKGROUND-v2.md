# AUDITORÍA DE CANDIDATOS EN SEGUNDO PLANO — v2 (FASE 2, investigación profunda READ-ONLY)

- **Fecha**: mié 2026-09-23, 10:05–10:50 (-03)
- **Sistema**: Nobara Linux 44 (KDE Plasma 6, Wayland), `lex-luthor` — i7-4790 / 12 GB / HDD SAMSUNG HM500JI / Intel HD 4600 + RX 550
- **Regla**: fase 100 % lectura. **No se ejecutó** ningún `stop`/`disable`/`mask`/`kill`/cambio de config/desinstalación. Los comandos de §9 son **documentación únicamente**.
- **Objetivo**: reducir despertares de CPU, CPU inútil, I/O del HDD, escritura de journal, conflictos entre servicios, RAM y actividad periódica inútil — **no** “tener menos procesos”.
- **Aclaración previa importante**: `nobara-sync` (P2, sospechoso) ha quedado **resuelto**: era una actualización real y legítima del sistema (§4). Y `kalm-gpu` queda **solo documentado, sin propuesta de desactivación** (§8), separando explícitamente el riesgo para la RX550.

---

## 0. Resumen de clasificaciones

| Candidato | Prioridad | Clasificación | Evidencia clave |
|---|---|---|---|
| `system-autopilot.timer` | P1 | **CANDIDATO FUERTE A DESACTIVACIÓN** | 54 ciclos/hoy; ~10 subprocesos sudo por ciclo; IRQ 39 fijada a `cc` por él; governor oscilante; redundante con `sys-tuned` |
| `kalm.service` (kalmd) | P1 | **CANDIDATO FUERTE A DESACTIVACIÓN** | 840 líneas journal/30 min; 0 detecciones de irqbalance; 3311 “omitiendo”/día; sin escrituras nuevas desde el arranque |
| `kalm-lite.service` | P2 | OPCIONAL / CANDIDATO LEVE | poll 10 s en memoria; escribe sysctl solo bajo PSI; sin journal |
| `nobara-sync` (proceso) | P2 | **NECESARIO/RECOMENDADO MANTENER** (resuelto: legítimo) | 3 transacciones `nobara-updater grouped update` hoy; salió solo |
| `mako.service` | P3 | CANDIDATO (medio) | dueño actual de `org.freedesktop.Notifications`; sin config de usuario; no-KDE en Plasma |
| `app-geoclue-demo-agent` | P3 | OPCIONAL / CANDIDATO LEVE | binario demo de geoclue2; 9,3 MB idle; daemon geoclue inactivo |
| `drkonqi-sentry-postman.timer` | P3 | OPCIONAL (inercia confirmada) | condición `sentry-envelopes/*` nunca se cumple; “skipped” en journal |
| `kalm-gpu.service` | — | **NO TOCAR / solo documentar** | gobernador térmico custom de la RX550 |

Criterio de clasificación: basado en **evidencia local medida** (journal, `/proc`, `systemctl`, `ss`, `busctl`); sin asumir por nombre.

---

## 1. `system-autopilot.timer` — CANDIDATO FUERTE A DESACTIVACIÓN

### A. Identidad exacta
- Unidad timer: `/etc/systemd/system/system-autopilot.timer` (root:root, 135 B, creado **2026-05-07 11:58**).
- Unidad service: `/etc/systemd/system/system-autopilot.service` (root:root, 115 B) — `Type=oneshot`, `ExecStart=/usr/local/bin/system-autopilot.sh`.
- Script: `/usr/local/bin/system-autopilot.sh` (root:root, 1.537 B, **2026-05-07 11:56**, ejecutable).
- Propietario: root; **sin paquete RPM** (creación manual): `rpm -qf` → nada.
- Timer: `OnBootSec=2min` + `OnUnitActiveSec=2min` → **cada 2 min**; `WantedBy=timers.target`; `is-enabled=enabled`.

### B. Función (qué hace cada ciclo — leído el script completo)
1. **Governor CPU**: si `loadavg(1m) > 2.5` → `performance`; si no → `schedutil`; escribe en los 8 `cpu*/cpufreq/scaling_governor` vía `sudo tee`.
2. **Afinidad IRQ de red**: busca la IRQ de `enp3s0` y escribe `smp_affinity = cc` (CPUs 2,3,6,7) vía `sudo`.
3. **Sysctls de red**: `default_qdisc=fq`, `tcp_congestion_control=bbr`, `tcp_fastopen=3`, `tcp_mtu_probing=1`, `netdev_max_backlog=5000`.
4. **Disco**: scheduler `mq-deadline` en todos los `sd*` vía `sudo`, y `read_ahead_kb=256` en `sda`.
5. **Prioridades**: `renice +5` a firefox, `renice -10` a kwin_wayland (vía `sudo`).

Por qué existe: **creación manual del usuario** (mayo 2026). **No hay mandato en la documentación del proyecto** (grep en MASTER-PLAN/decisions/FASE-R3 sin coincidencias de “autopilot”). Origen concreto (guía/script propio) `DESCONOCIDO — requiere confirmación del usuario`. No hay documentación oficial (no es de Nobara/Fedora/KDE).

### C. Actividad (medida)
- **Frecuencia**: 24 ciclos/hora (`journalctl -u system-autopilot.service | grep -c 'cycle complete'` → **54 hoy** desde el arranque 08:12).
- **Procesos por ciclo**: ~7 `sudo` (`tee` a governors×8 y scheduler, read_ahead, smp_affinity, `renice`×2) + 5 `sysctl` + `awk`/`bc`/`grep`/`pgrep`/`renice` → **~15 subprocesos efímeros cada 2 min**.
- **CPU**: picos periódicos (spawns cada 2 min); governor real oscilante: ciclos de 10:13–10:17 fijaron `schedutil` (carga 1m≤2,5); con carga>2,5 fija `performance` → **8 núcleos en turbo (3,5–3,9 GHz)** durante la actividad (§8 de la auditoría previa).
- **RAM**: efímera (oneshot); 0 residente.
- **I/O / HDD**: cada ciclo genera escrituras de journal + eventos PAM/audit (`sudo … session open/close`) → **despertares del HDD cada 2 min**.
- **Journal**: ~12–16 líneas por ciclo (líneas `[AUTO-PILOT]` + `sudo[NNN]: … session opened/closed` + `audit`).
- **Red**: no genera tráfico; reafirma sysctls (si se desactiva, los sysctls persisten hasta reboot y luego vuelven a valores por defecto de Fedora: `tcp_fastopen=1`, `mtu_probing=0`, `netdev_max_backlog=1000`, `qdisc` default de Nobara, `cubic`).
- **IRQ**: **se comprobó que la IRQ 39 (enp3s0) está actualmente en `cc` (2,3,6,7)** — `cat /proc/irq/39/smp_affinity` = `cc` — es decir, la pinza de autopilot está **en efecto ahora mismo**.

### D. Dependencias / qué pasaría si se desactiva
- Nada depende de él; es un launcher independiente y **redundante en su mayor parte** con `sys-tuned` (cada 30 min: schedutil, swappiness, scheduler, IRQ, sysctls net) y con `irqbalance` (afinidades).
- Conflictos verificados con `irqbalance`: la máquina tiene **3 gestores de afinidad coexistiendo** — autopilot (IRQ 39 = cc), kalmd (IRQ 27→3, 28→0, 40→1, 42→1) e irqbalance (IRQs 16/18/23–26 repartidas en pares 0,4/1,5/2,6/3,7). Ese solapamiento es la razón de “conflictos entre servicios” que el objetivo quiere reducir.
- No toca GPU (ni Intel ni RX550), no toca memoria (solo renice), no toca power capping.

**Clasificación: CANDIDATO FUERTE A DESACTIVACIÓN** — actividad periódica inútil + conflicto con irqbalance + generador de journal/PAM cada 2 min, con beneficios marginales en parte ya cubiertos por `sys-tuned`.

---

## 2. `kalm.service` (kalmd) — CANDIDATO FUERTE A DESACTIVACIÓN

### A. Identidad exacta
- Unidad: `/etc/systemd/system/kalm.service` (custom, root) — `ExecStart=/usr/bin/python3 /opt/kalm/kalmd.py`.
- Script: `/opt/kalm/kalmd.py` (root) — **v3, “Topology-aware IRQ affinity”**, 13 KB; **sin paquete RPM** (custom).
- Proceso actual: PID **4055**, `stat=S`, RSS **13,3 MB**, `is-enabled=enabled`, `is-active=active`.

### B. Función y causa de los “omitiendo” (leído el código completo)
- Bucle `while True` cada **15 s** (“work”): (1) detecta `irqbalance.pid` → si existe pausa 30 s; (2) lee topología de CPU; (3) descubre IRQ desde `/sys/bus/pci/devices/*/msi_irqs` clasificándolas (GPU/INPUT/NET/STORAGE); (4) escribe `smp_affinity_list = CPU` según política (INPUT→core0, GPU→core1, NET→core2, STORAGE→core3) **solo si cambió**; (5) verifica la escritura.
- **Por qué produce “omitiendo”**: enumera **todos** los números MSI (incl. los 29–35 solicitados por la RX550) que **no tienen entrada en `/proc/irq`** → `Path.exists()` devuelve False → `log.warning("no smp_affinity_list, omitiendo")`. Evidencia: en `/proc/irq` **no existen los directorios 29–35** (`ls /proc/irq/[0-9]*` muestra 0–28, 36–42).
- **Por qué no se entera de irqbalance**: `is_irqbalance_active()` solo mira `/run/irqbalance.pid` (o `/var/run`), y **ese fichero no existe** (`irqbalance.service` no usa PIDFile; `systemctl show irqbalance -p PIDFile` = vacío). Consecuencia: **0 líneas “irqbalance activo” en todo el día** → kalmd siempre entra a la rama de trabajo aunque irqbalance esté activo.
- **Por qué no tiene efecto real hoy**: tras el arranque (08:21:27) **escribió con éxito una sola vez** (journal: `IRQ 39 → CPU2`, `IRQ 27 → CPU3`, `IRQ 42 → CPU1`, `IRQ 40 → CPU1`, `IRQ 28 → CPU0`). Después `last[irq]==cpu` → ya no reescribe; las afinidades quedan fijadas tal cual están en `/proc/irq` (27=3, 28=0, 40=1, 42=1) y `irqbalance` gestiona el resto. **El daemon ya no aporta nada nuevo: solo loguea.**

### C. Actividad (medida)
- **Journal**: **3.311 líneas “omitiendo”/día** (desde 08:12) y **840 en los últimos 30 min** (≈28/min ≈ 7 por ciclo × 4 ciclos/min). Es el 2.º generador de journal del sistema tras el autopilot.
- **CPU**: poll 15 s con iteración sobre sysfs (bajo %, pero constante).
- **RAM**: 13,3 MB residente; **I/O**: solo journal; **red**: ninguna; **IRQ**: no dispara IRQ (solo lee sysfs).

### D. Dependencias / efecto de desactivar
- Nada depende de kalmd. Al desactivarlo: `irqbalance` queda como único gestor (esperado); las afinidades ya fijadas (27/28/40/42) **persisten hasta reboot** (o hasta que irqbalance las reubique); se eliminan ~1.680 líneas journal/hora.

**Clasificación: CANDIDATO FUERTE A DESACTIVACIÓN** — daemon redundante con `irqbalance`, con detección rota y generador de journal puro.

---

## 3. `kalm-lite.service` — OPCIONAL / CANDIDATO LEVE

### A. Identidad
- Unidad: `/etc/systemd/system/kalm-lite.service` (custom, root). `ExecStart=/usr/bin/python3 /usr/local/bin/kalm-lite.py`.
- Script: `/usr/local/bin/kalm-lite.py` (root, custom). PID **4054**, RSS **8,7 MB**, enabled/active.

### B/C. Función y actividad
- Bucle cada **10 s** leyendo `/proc/pressure/{memory,io}` (en memoria, sin I/O de disco). Ajusta: `vm.swappiness` ±10 (piso 1) si `mem_psi>15` o `<5`; `vm.dirty_ratio/dirty_background_ratio` −2/−1 (piso 5/1) si `io_psi>10`; **cooldown 60 s**. Imprime solo en los cambios.
- No genera journal en reposo (solo `print` al ajustar). Valores actuales: `swappiness=10`, `dirty_ratio=5`, `dirty_background_ratio=1`.
- Conflicto conceptual: `sys-tuned` (30 min) re-fija `swappiness=10` — pugna de valores baja frecuencia vs bajo estrés; menor.

### D. Efecto de desactivar
Nada depende; los sysctls vuelven a defaults de Fedora tras reboot; entre reinicios persisten. La pérdida es la protección adaptativa de memoria bajo presión PSI.

**Clasificación: OPCIONAL / CANDIDATO LEVE.** Coste real mínimo (poll en memoria cada 10 s). Decisión del usuario: puede permanecer sin impacto visible.

---

## 4. `nobara-sync` — RESUELTO (legítimo; NECESARIO/RECOMENDADO MANTENER)

### A. Identidad
- `/usr/sbin/nobara-sync` → symlink → `/usr/bin/nobara-updater` (**script python3**, 71.619 B, GPL-3.0, paquete **`nobara-updater-2.0.1-44.fc44`**, instalado 16-sep-2026).
- **No es un servicio ni un timer**: no hay unidad systemd propia; es una herramienta **a demanda**.

### B. Qué es
- Actualizador oficial de **Nobara** (frente de línea de `nobara-sync cli`; ejecuta “grouped updates”: Kernel → Graphics → Global, con confirmación).

### C. Actividad durante la auditoría (evidencia que lo **exculpa**)
- Proceso observado: PID **12594**, EUID root (auid=1000), PPID 1277 (systemd --user), iniciado **09:04**, RSS 452 MB, 2,1 % CPU.
- `dnf5 history` muestra **3 transacciones esta mañana**: `nobara-updater grouped update: Kernel…` (8), `Graphics…` (28), `Global/Non-e…` (27) (12:17/12:37/12:48 UTC = 09:17/09:37/09:48 local).
- Eventos de auditoría kernel **`AUDIT1138 pid=12594 uid=0 auid=1000 comm="nobara-sync" exe="/usr/bin/python3.14"`** a las **10:00:39** con `op=update`/`install`… `res=success` para decenas de RPM (kernel-tools, mesa-vulkan-drivers, chatgpt, wine-staging, heroic-games-launcher, openrgb, goverlay, adw-gtk3-theme…).
- **El proceso ya no existe** (verificado `/proc/12594` ausente ≈10:12): **terminó solo, sin intervención nuestra, tras completar la sincronización**. No hubo OOM.
- A las 10:03:01 el tray `dnf-app-center-updater[6634]` registró `Checking for updates (refresh=True)` — refresco puntual post-update (intervalo configurado por el usuario en 999 semanas; ya desactivado).

### D. Conclusiones
- **No está bloqueado ni es sospechoso**: era una actualización legítima lanzada vía sesión (AppCenter/manual del usuario).
- No hay nada que “desactivar” (no es servicio). **Regla**: no matarlo; si reaparece y **no** fue el usuario quien lo lanzó, entonces sí requiere investigación en ese momento (con `wchan`, `fd`, `ss`).

**Clasificación: NECESARIO/RECOMENDADO MANTENER** (herramienta oficial; a demanda; sin mecanismo periódico).

---

## 5. `mako.service` — CANDIDATO (medio)

### A. Identidad
- Unidad: `/usr/lib/systemd/user/mako.service` (paquete **mako-1.11.0-1.fc44**, instalado 16-sep-2026 10:21 — mismo lote de instalación que las herramientas gaming/energía).
- Binario: `/usr/bin/mako`; **sin configuración del usuario** (`~/.config/mako/` no existe → ejecuta con defaults).
- `Type=dbus`, `BusName=org.freedesktop.Notifications`; `is-enabled=disabled` (activación por bus), `is-active=active`.

### B. Función
- Daemon de notificaciones Wayland (estilo Sway/wlroots). **En Plasma 6 es redundante**: el escritorio KDE gestiona notificaciones con su propio applet.
- Estado actual verificado: **mako es HOY el dueño activo del nombre `org.freedesktop.Notifications`** — `dbus-send GetServerInformation` → `mako / emersion / 0.0.0 / 1.2`; `busctl --user list` → nombre en PID **6717 (mako)**.
- `dbus-broker` lo avisa: “Service file ‘fr.emersion.mako.service’ is not named after the D-Bus name ‘org.freedesktop.Notifications’” (4 ocasiones registradas) — peculiaridad del empaquetado.

### C. Actividad
- RAM **23,4 MB**; CPU ~0; sin I/O de disco; red nula. Sin errores propios en journal.

### D. Efecto de desactivar
- Las notificaciones dejan de pasar por mako y vuelven a **Plasma** (que tomará el nombre al primer uso): popups/estilo/historial = los nativos de KDE. Sin config de mako no hay preferencias que perder. Certeza **media-alta** (el único matiz: comportamiento de apps Wayland que llamaran explícitamente a mako; sin evidencia de ello en este sistema).

**Clasificación: CANDIDATO (medio)** — redundante por origen (no-KDE), sin configuración y duplicado con el sistema de notificaciones de Plasma. Reversible en segundos.

---

## 6. `app-geoclue-demo-agent@autostart` — OPCIONAL / CANDIDATO LEVE

### A. Identidad
- Unidad **generada** por `systemd-xdg-autostart-generator` desde `/etc/xdg/autostart/geoclue-demo-agent.desktop` → `Exec=/usr/libexec/geoclue-2.0/demos/agent` (paquete **geoclue2-2.8.2-1.fc44**).
- Proceso: PID **6663**, `comm=agent`, RSS **9,3 MB**, PPID 1277 (systemd --user).

### B. Función
- Agente de **demostración** de geolocalización (ejemplo de cliente del API de Geoclue). El daemon `geoclue.service` (system) está **inactive** → el agente no tiene a quién hablar; queda residente e inerte.

### C. Actividad
- Residente sin CPU ni I/O; journal: solo start/stop de la unidad (reinició una vez a las 08:32 durante el arranque de sesión).

### D. Efecto de desactivar
- Ninguno práctico: KDE no usa el demo agent; no hay apps dependientes. Reversible al instante.

**Clasificación: OPCIONAL / CANDIDATO LEVE** (binario demo sin uso; coste 9,3 MB).

---

## 7. `drkonqi-sentry-postman.timer` — OPCIONAL (inercia confirmada)

### A. Identidad
- Unidades: `/usr/lib/systemd/user/drkonqi-sentry-postman.service` + `.timer` (paquete **plasma-drkonqi-6.7.4-1.fc44**).
- Service: `ExecStart=/usr/libexec/drkonqi-sentry-postman`, `RuntimeMaxSec=30 min`, `Restart=no`.
- Timer: `OnCalendar=hourly` + **`ConditionPathExistsGlob=%C/drkonqi/sentry-envelopes/*`**.

### B. Función
- Enviar “crash envelopes” (informes de fallo aceptados por el usuario) al servicio Sentry de KDE (telemetría). Solo corre si existen sobres pendientes.

### C. Actividad (medida)
- Journal (3 eventos hoy): **“skipped, unmet condition check ConditionPathExistsGlob=…/sentry-envelopes/*”** (08:14, 08:17, 08:32) → **nunca ha disparado** porque `~/.cache/drkonqi/` **no contiene** `sentry-envelopes/` (sí hay `crashes/` — incl. el crash de firefox 09:24 — y `dsns.json`, pero sin sobres: el usuario no optó por enviar). RAM 0, red 0.

### D. Efecto de desactivar
- No enviar informes de fallo (privacidad). Los datos locales (`~/.cache/drkonqi/crashes`, limpia por `drkonqi-coredump-cleanup.timer`) siguen existiendo; la funcionalidad local de DrKonqi/Reporte de fallos no cambia. Certeza alta.

**Clasificación: OPCIONAL** — hoy no hace nada; es un recorte de telemetría/red preventivo si en el futuro se optara por el envío.

---

## 8. `kalm-gpu.service` — SOLO DOCUMENTACIÓN (NO se propone desactivación operativa)

- Unidad: `/etc/systemd/system/kalm-gpu.service` (custom, root) — `Nice=-5`, `ProtectSystem=full`, **`ReadWritePaths=/sys/class/drm`**, `Restart=always`/10 s. PID **6441**, RSS **8,9 MB**, enabled/active.
- Script: `/usr/local/bin/kalm-gpu` — control térmico de la **RX 550** con anticipación: bandas 58/70/78/82 °C, `POWER_TARGET=32 W`, escribe `power1_cap` **validando `power1_cap_max`**, `POLL_SEC=2.0`, usa `gpu_busy_percent`, fallback de sensor. Temp actual GPU: 34 °C.
- **Riesgo separado de la desactivación (para decisión explícita del usuario)**: desactivarlo **no toca amdgpu** (regla del proyecto), pero **quita el gobernador térmico custom** de la RX550: el kernel/amdgpu conserva sus límites de fábrica (no hay riesgo de daño por hardware), pero se pierde el ajuste fino térmico/power-cap en carga. **Por el objetivo del proyecto (RX550) y la regla NO TOCAR amdgpu, NO se propone desactivación operativa.** Si se considerara en el futuro: medir antes/después temp GPU en carga, `gpu_busy_percent`, `power1_cap` actual vs `power1_cap_max`, y comportamiento del ventilador. (Referencia: en reposo la RX550 está a 34 °C y sin IRQ — ver auditoría v1 §10.)

---

## 9. Comandos de documentación (SOLO p. ej.: NO ejecutar nada)

> Los comandos de `§9.1–9.3` se presentan **exclusivamente como documentación** para una decisión posterior del usuario. **No se ejecutó ni se ejecutará ninguno sin orden explícita.** Todos son coherentes con el estado actual (`enabled`/`active`).
>
> Nota de sintaxis: `unit-name` con `@` y escapes `\x2d` — usar el nombre tal cual muestra `systemctl --user list-units`.

### 9.1 `system-autopilot` (estado actual: timer enabled)
| Acción | Comando (documentación) |
|---|---|
| Desactivar | `systemctl disable --now system-autopilot.timer` |
| Detener (temporario, sin desactivar) | `systemctl stop system-autopilot.timer` |
| Reactivar | `systemctl enable --now system-autopilot.timer` |
| Re-armar/reiniciar cadencia | `systemctl restart system-autopilot.timer` |
| Restaurar estado original | `systemctl enable system-autopilot.timer ` y `systemctl start system-autopilot.timer` (era `enabled`) |

- **Efectos secundarios esperados**: deja de oscilar el governor entre `schedutil`/`performance` (queda `sys-tuned` cada 30 min y/o el default Nobara `schedutil`); la IRQ 39 queda gestionada solo por `irqbalance` (pierde la pinza `cc` al rebalancearse/reboot); los sysctls (bbr/fastopen/mtu/backlog) vuelven a defaults de Fedora tras reinicio; sin renice de firefox/kwin (marginal).
- **Métricas a medir antes/después**: `journalctl -u system-autopilot -S -1h | wc -l`; `journalctl | grep -c 'sudo\['`/h; `/proc/irq/39/smp_affinity`; `scaling_governor`; `iostat -x 1 3` sobre `sda`; `loadavg` en reposo; conteo de sesiones `systemd-logind`/h.

### 9.2 `kalm` (estado actual: enabled/active)
| Acción | Comando (documentación) |
|---|---|
| Desactivar | `systemctl disable --now kalm.service` |
| Detener (temporario) | `systemctl stop kalm.service` |
| Reactivar | `systemctl enable --now kalm.service` |
| Reiniciar | `systemctl restart kalm.service` |
| Restaurar estado original | `systemctl enable kalm.service` (era `enabled`) |

- **Efectos secundarios**: se eliminan ~1.680 líneas journal/h; irqbalance queda único gestor; los pins ya escritos (27→3, 28→0, 40→1, 42→1) persisten hasta reboot/rebalance.
- **Métricas antes/después**: `journalctl --since -30min | grep -c omitiendo`; `cat /proc/irq/{27,28,40,42}/smp_affinity_list`; líneas journal/hora.

### 9.3 `kalm-lite` (estado actual: enabled/active) — solo si el usuario decide “calma total”
| Acción | Comando (documentación) |
|---|---|
| Desactivar | `systemctl disable --now kalm-lite.service` |
| Detener (temporario) | `systemctl stop kalm-lite.service` |
| Reactivar | `systemctl enable --now kalm-lite.service` |
| Reiniciar | `systemctl restart kalm-lite.service` |
| Restaurar estado original | `systemctl enable kalm-lite.service` |

- **Efectos secundarios**: swappiness/dirty vuelven a defaults Fedora tras reboot; entre reinicios persisten valores actuales. Sin impacto funcional aparente.
- **Métricas**: `cat /proc/sys/vm/{swappiness,dirty_ratio,dirty_background_ratio}` antes/después; `journalctl | grep '\[Kalm\] swappiness'`/periodo.

### 9.4 `mako` (estado actual: user, active por bus, is-enabled=disabled)
| Acción | Comando (documentación) |
|---|---|
| Desactivar | `systemctl --user disable --now mako.service` |
| Detener (temporario) | `systemctl --user stop mako.service` |
| Reactivar | `systemctl --user enable --now mako.service` |
| Reiniciar | `systemctl --user restart mako.service` |
| Restaurar estado original | era `disabled`+activo por bus: basta `systemctl --user start mako.service` (o ningún enable) |

- **Efectos secundarios**: las notificaciones pasan a Plasma (dueño siguiente del nombre). Sin config de mako, sin pérdida de preferencias.
- **Métricas**: `busctl --user list | grep -i notification` (ver quién es dueño); test de notificación (KDE `notify-send` o applet) antes/después; `free` delta (−23 MB).

### 9.5 `geoclue-demo` (estado actual: user, active)
| Acción | Comando (documentación) |
|---|---|
| Desactivar | `systemctl --user disable --now app-geoclue\x2ddemo\x2dagent@autostart.service` |
| Detener (temporario) | `systemctl --user stop app-geoclue\x2ddemo\x2dagent@autostart.service` |
| Reactivar | `systemctl --user enable --now app-geoclue\x2ddemo\x2dagent@autostart.service` |
| Reiniciar | `systemctl --user restart app-geoclue\x2ddemo\x2dagent@autostart.service` |
| Restaurar estado original | era `active` por autostart (el generator la recrea): basta re-iniciar sesión o `start` |

- **Efectos secundarios**: ninguno práctico (geoclue-daemon inactive; KDE no lo usa). −9 MB.
- **Métricas**: `ps -C agent` antes/después; journal geoclue.

### 9.6 `drkonqi-sentry-postman` (estado actual: timer inbox, condición nunca cumplida)
| Acción | Comando (documentación) |
|---|---|
| Desactivar (timer) | `systemctl --user disable --now drkonqi-sentry-postman.timer` |
| Detener | `systemctl --user stop drkonqi-sentry-postman.timer` |
| Reactivar | `systemctl --user enable --now drkonqi-sentry-postman.timer` |
| Reiniciar | `systemctl --user restart drkonqi-sentry-postman.timer` |
| Restaurar estado original | era `enabled` (pero con condición de sobres): `systemctl --user enable drkonqi-sentry-postman.timer` |
| Alternativa KDE | Notificaciones → Fallos: “no enviar informes” (DesCRIPCIÓN: Plasma 6) |

- **Efectos secundarios**: no enviar telemetría de crash; sin impacto local (los dumps locales persisten y los limpia `drkonqi-coredump-cleanup.timer`).
- **Métricas**: `journalctl --user -u drkonqi-sentry-postman.timer -S -7d | grep -c skipped` antes/después; red saliente nula en ambos casos.

### 9.7 Kalm-GPU — **no incluido en desactivación** (ver §8). Comandos omitidos intencionalmente hasta decisión explícita del usuario con evaluación de riesgo RX550.

---

## 10. Verificación final (debe quedar sin cambios)

1. **Sin stops**: `journalctl -S -40min` sin eventos “Stopping … (kalm|mako|geoclue|autopilot)” ni fallos de parada. **`nobara-sync` terminó solo** (evidencia: AUDIT1138 + `dnf5 history`; `/proc/12594` ausente al final).
2. **Sin procesos terminados**: PIDs de los candidatos vivos al cierre: 4055 (kalmd), 4054 (kalm-lite), 6441 (kalm-gpu), 6717 (mako), 6663 (geoclue demo), 6634 (dnf-app-center-updater), más el resto de la sesión (kwin 6307, plasmashell 6430, ChatGPT 7585/8092, etc.).
3. **Sin disable/mask**: `is-enabled` idéntico — autopilot.timer, kalm, kalm-lite, kalm-gpu → `enabled`; `is-active` → `active` (kalm, kalm-lite, kalm-gpu, mako, geoclue); drkonqi-sentry-postman.timer → `inactive` (condición no cumplida, como al inicio).
4. **Sin cambios de configuración**: no se escribió en `/etc`, `/usr/local`, `/opt`, `/home/lucas/.config` ni sysfs. Única escritura: `/tmp/opencode/` (muestreadores y baselines de la fase anterior).
5. **`git status`**: 36 `M` + 8 `??` antes de esta fase; el único archivo nuevo es el presente (9.º `??`).
6. **Resumen de consumidores principales confirmados en esta fase**: autopilot (54 ciclos/día, ~15 subprocesos/ciclo), kalmd (840 líneas journal/30 min), ChatGPT + openclaw + open-webui + nobara-updater (transitorio) en RAM; sda y i915 dominan IRQ; RX550 ociosa (34 °C).

**DETENERSE** — no se inició Set H, no se hace commit, no se ejecutó ninguna desactivación. Los comandos de §9 quedan como documentación pendiente de decisión del usuario.
