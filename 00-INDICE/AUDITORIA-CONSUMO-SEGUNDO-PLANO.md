# AUDITORÍA DE CONSUMO EN SEGUNDO PLANO (READ-ONLY)

- **Fecha**: mié 2026-09-23, 09:35–10:05 (-03)
- **Sistema auditado**: Nobara Linux 44 (KDE Plasma 6, Wayland), hostname `lex-luthor`
- **Hardware**: Intel Core i7-4790 (4C/8T), 11.817 MB RAM, **HDD SAMSUNG HM500JI 465,8 GB** (`sda`), GPU Intel HD 4600 (`card0`, i915) + AMD RX 550 (`card1`, amdgpu), red `enp3s0`
- **Método**: 100 % lectura (`ps`, `systemctl`, `journalctl`, `ss`, `iostat`, `/proc`, `/sys`); **cero escrituras al sistema**; única salida a `/tmp/opencode/` (baselines y muestreador); **ningún** `stop` / `disable` / `mask` / `kill` / cambio de config / desinstalación / `sudo` de escritura.
- **Regla de investigación aplicada**: si una unidad/proceso no se pudo identificar con evidencia local, se marcó `DESCONOCIDO — requiere investigación` y se citó la fuente usada.

---

## 0. Resumen ejecutivo

1. **El HDD mecánico es el cuello de botella activo**: el `iostat` mostró `sda` al **35–93 % de utilización** en muestras de 1 s, con latencias de **118 ms (lectura) y 273 ms (escritura)**; en una ventana de 60 s el disco escribió **≈161 MB** (95,7 k sectores leídos, 315 k escritos) y generó **+5.009 IRQ ahci (≈83/s)**.
2. **`system-autopilot.timer` es el generador periódico número uno**: unidad personalizada (24-05-07) que **cada 2 minutos** ejecuta `/usr/local/bin/system-autopilot.sh` (spawns múltiples `sudo`/`sysctl`/`renice`/`pgrep` → cada ciclo genera entradas de PAM/logind/audit/journal y despierta la CPU y el HDD). **24 ejecuciones en la última hora**, con evidencia en journal.
3. **`kalmd` (kalm.service) despierta cada 15 s solo para loguear**: emite **1.680 líneas/hora** de `[Kalm] IRQ N: no smp_affinity_list, omitiendo` (~28 líneas/minuto) y es redundante con `irqbalance` (co-activo).
4. **Tres pollers custom adicionales**: `kalm-lite` (PSI cada 10 s), `kalm-gpu` (hwmon de la RX550 cada 2 s), más tira y afloja de governor: `system-autopilot` fija `performance` (carga>2,5) cada 2 min mientras `sys-tuned` fija `schedutil` cada 30 min → **los 8 núcleos viven en 3,5–3,9 GHz** (frecuencias leídas de `/sys`).
5. **RAM**: familia **ChatGPT ≈ 2.474 MB** (12 procesos, incl. 269 MB de `codex`), cgroup de sesión `user@1000` ≈ **5,2 GB**. Otros residentes grandes: `openclaw-gateway` 574 MB, `nobara-sync` (root EUID) 452 MB **corriendo >1 h** (sospechoso de colgado; `DESCONOCIDO`), `open-webui` (docker) 420 MB, `plasmashell` 396 MB, `dnf-app-center-updater` 290 MB (ya desactivado por config), `packagekitd` 215 MB, `kwin` 234 MB.
6. **GPU**: la **Intel HD 4600 trabaja constantemente** (composición KDE; +3.674 IRQ i915/60 s). La **RX 550 está ociosa** (sin IRQ amdgpu en la ventana, 34 °C), con `renderD129` abierta **solamente** por Xwayland y el proceso GPU del ChatGPT. `kalm-gpu` la vigila cada 2 s.
7. **Red**: 12 conexiones TCP persistentes (FCM 5228 ×3 del ChatGPT, Cloudflare/GCP de opencode+ChatGPT, ollama local); **dos listeners en `0.0.0.0`** (open-webui :8080 y ollama :11434); KDE Connect broadcast UDP; LLMNR 5355. Sin tráfico generado por esta auditoría.
8. **Journal**: 185,3 MB; tras el ruido de arranque, los escritores repetitivos son `kalmd` (28 líneas/min) y el `system-autopilot` (sesiones sudo/PAM cada 2 min).

**Candidatos principales a desactivación (solo documentación, ver §13.3)**: `system-autopilot.timer`, `kalm.service`, `kalm-lite.service` (leve), `mako.service` (redundante con Plasma), `app-geoclue-demo-agent` (autostart), `drkonqi-sentry-postman.timer` (telemetría de crash) y revisar `kalm-gpu.service` (gobernador térmico de la RX550 — **no tocar amdgpu**).

---

## 1. Metodología y limitaciones

### 1.1 Comandos de evidencia (todos read-only)
`ps`, `pstree`, `systemd-cgtop`‑no, `systemctl list-units/list-timers/{status,cat,show,is-active,is-enabled}`, `journalctl`, `ss`, `iostat -x`, `lsblk/lspci/stat/du`, `/proc/*` (`status`, `io`, `diskstats`, `interrupts`, `fdinfo`, `loadavg`), `/sys/*` (frecuencias, governors, hwmon, sched_ext), `/usr/bin/… --help`, `rpm -qi/-qf`. Nada de ello escribe en el sistema.

### 1.2 Limitaciones documentadas
- **`/proc/<pid>/io` solo legible para procesos de `lucas` (UID 1000)** → los escritores root (journald, docker/open-webui, `nobara-sync`, `system-autopilot` vía sudo) se atribuyen a **nivel de dispositivo** (`/proc/diskstats`, `iostat`, IRQ), no por proceso.
- **La ventana de observación (60 s) no fue de reposo estricto**: el `loadavg 1m` osciló 7–15 (la propia auditoría + ChatGPT/opencode activos). Los deltas son indicativos de *peor caso*, no de reposo.
- **`fdinfo` de GPU no exporta contadores** de motor en esta HW (`i915` solo publica metadatos; RX 550 Polaris no publica contadores DRM) → la atribución GPU se apoya en **handles de `/dev/dri` + deltas de `/proc/interrupts`**.
- **`%CPU` de `ps`** = media desde el arranque del proceso (no instantánea).
- No se pudo leer `smartctl`/`powertop`/`turbostat` (requieren root). Irrelevante para las conclusiones centrales.

---

## 2. Inventario de procesos del usuario `lucas`

Fotografía base (`ps -eo pid,ppid,user,pcpu,pmem,rss,stat,etime,time,nlwp,comm,args -U lucas`). 75 procesos de `lucas` muestreados; 346 procesos totales en el sistema.

### 2.1 Procesos realmente activos (CPU sostenida, medido 09:39–09:44)

| PID | PPID | %CPU* | RSS MB | STAT | Hilos | Tiempo CPU | Comando | Padre / lanzado por |
|---|---|---:|---:|---|---|---:|---|---|
| 37933 | 23291 | 6,3 | 240 | Rl+ | 21 | 0:52 | opencode (sesión actual) | terminal konsole del usuario |
| 7487 | 7157 | 5,7 | 232 | Rl+ | 20 | 3:43 | opencode | konsole del usuario |
| 38014 | 37933 | 3,7 | 322 | Rsl | 29 | 0:31 | opencode serve | opencode de la sesión |
| 7073 | 1277 | 5,8 | 115 | Ssl | 5 | 3:50 | konsole | Plasma (aplicación en uso) |
| 8092 | 7600 | 5,4–6,3 | 590–646 | Sl | 16 | 3:31 | ChatGPT renderer | GPU/red de la app ChatGPT |
| 7585 | 1277 | 1,1–5,7 | 502 | Rsl | 51 | — | ChatGPT (main) | App "ChatGPT - AI assistant" (autostart KDE) |
| 7673 | 7597 | 1,6 | 188 | Dl | 15 | — | ChatGPT (gpu) | main ChatGPT |
| 6307 | 6296 | 4,5 | 234 | S<l | 24 | 3:01 | kwin_wayland | startplasma-way (compositor) |
| 12594 | 1277 | 2,1 | 452 | Rl | 2 | — | **nobara-sync cli** (EUID root) | sesión de usuario lucas (ver §6 y §13.5) |
| 6634 | 1277 | 0,1 | 290 | Ssl | 6 | — | dnf-app-center-updater | autostart KDE (config `enabled:false`) |

*`ps` = media desde inicio del proceso. Estos valores incluyen el consumo de la propia sesión de auditoría.

### 2.2 Residentes pero prácticamente inactivos (RSS significativo, CPU ≈ 0)

| PID | RSS MB | Comando | Función observada |
|---|---|---:|---|---|
| 1564 | 574 | `` MainThread `` (openclaw-gateway, node) | gateway local :18789/:18791 + mDNS |
| 3005 | 420 | python3 uvicorn (open-webui, con docker) | Web UI AI en `0.0.0.0:8080` |
| 6430 | 396 | plasmashell | shell de Plasma (56 hilos) |
| 6634 | 290 | dnf-app-center-updater | updater ya desactivado; además **zombie** `[dnf-app-center] <defunct>` hijo |
| 8112 | 269 | codex | helper de terminal/fondo del ChatGPT |
| 6456 | 158 | polkit-kde-auth | agente de autenticación KDE |
| 6359 | 166 | plasma-keyboard | teclado virtual (4× `renderD128` abiertas) |
| 6644 | 104 | xwaylandvideobridge | puente video X11→Wayland (autostart) |
| 6425 | 99 | kded6 | daemon de servicios KDE |
| 6366 | 84 | Xwayland | servidor X (necesario: opencode/ChatGPT son X11) |
| 6753 | 70 | ksecretd | almacén de secretos (crypto) |
| 6457 | 63 | org_kde_powerdevil | gestión de energía KDE |
| 6636 | 66 | kdeconnectd | KDE Connect (autostart) |
| 6707 | ~40 | xdg-desktop-portal | portales |
| 7560 | 54 | baloorunner | proveedor de búsqueda de baloo en KRunner |
| 6639 | ~30 | baloo_file | indexador (estado: **inactivo**, no indexando) |
| 6717 | 23 | mako | daemon de notificaciones Wayland (redundante con Plasma) |
| 3113 | 5 | ssh-agent | agente SSH (activo/sesion) |

### 2.3 Procesos que despiertan periódicamente
- **A nivel de usuario, ninguno tiene un timer propio** (los timers user del apartado §4.2 son de limpieza/crash). Los despertadores periódicos reales son **servicios de sistema/root**: `system-autopilot` (2 min), `kalmd` (15 s), `kalm-lite` (10 s), `kalm-gpu` (2 s), `sysstat-collect` (10 min) — ver §3/§4/§8.
- `ChatGPT` (PID 7699, network-service) mantiene sockets persistentes (FCM/Cloudflare) — ver §11.

---

## 3. Servicios systemd activos (clasificación A–F)

**40 servicios activos.** Memoria y CPU medida (MemoryCurrent, ps) con actividad observada (journal/interrupts). Clases: **A** imprescindible básico · **B** necesario KDE · **C** red/audio/gráficos · **D** útil pero opcional · **E** prescindible · **F** sospechoso de actividad periódica.

### 3.1 Tabla de servicios activos

| Servicio | RAM* | CPU | Actividad | Frec. activación | Clase | Función |
|---|---:|---|---|---|---|---|
| user@1000 (sesión KDE) | 5.208 MB | variable | todo lo del usuario | continua | B | sesión de Plasma, Wayland, apps |
| containerd.service | 85 MB | ~0 | daemon contenedores | continua | D | runtime de docker (open-webui) |
| docker.service | 67 MB | ~0 | daemon | continua | D | motor de contenedores (open-webui 4 meses) |
| ollama.service | 54 MB | ~0 | escucha :11434 | continua | D | server LLM (0.0.0.0) |
| systemd-udevd | 39 MB | ~0 | gestión HW | eventos | A | necesario |
| plasmalogin | 36 MB | ~0 | session greeter | continua | B | login de Plasma |
| systemd-journald | 28 MB | variable | 185 MB log | continua | A | logging (ver §12) |
| polkit | 9 MB | ~0 | authz | a demanda | A | autorización |
| user@0 (root session) | 8 MB | ~0 | sesión root | continua | C/D | session manager de root |
| ds-inhibit | 7,8 MB | ~0 | inhibitor de mouse DualShock | continua | D | gaming (Nobara) |
| **kalm.service** | 7,6 MB | ~0 (picos cada 15 s) | **loguea 28 lín/min** | **cada 15 s** | **F** | kalmd, afinidad IRQ — ver §3.2 |
| udisks2 | 6,3 MB | ~0 | mounts | eventos | A | discos |
| NetworkManager | 5,5 MB | ~0 | red | continua | C | red |
| dbus-broker | 5,4 MB | ~0 | bus de mensajes | continua | A | D-Bus system |
| **kalm-lite** | 5,4 MB | ~0 (picos cada 10 s) | lee PSI 10 s, sysctl cooldown 60 s | **cada 10 s** | **F** | tuner memoria/IO — ver §3.2 |
| systemd-userdbd | 4,3 MB | ~0 | user DB | a demanda | A | resolución de usuarios |
| chronyd | 3,8 MB | ~0 | NTP (red :123) | continua | C | reloj (Fuente: KoD RATE vista en journal) |
| smartd | 3,5 MB | ~0 | **vigila el HDD** | continua | C/D | **SMART — vital para HDD mecánico** |
| **kalm-gpu** | 3,5 MB | ~0 (picos cada 2 s) | lee hwmon RX550 cada 2 s | **cada 2 s** | **F** | gobernador térmico GPU — ver §3.2 |
| upower | 2,9 MB | ~0 | energía | eventos | C | energía |
| falcond | 2,8 MB | ~0 | daemon gaming (idle, `scx_sched=none`) | a demanda | E/D | optimizador gaming (PikaOS) |
| systemd-resolved | 2,4 MB | ~0 | DNS/LLMNR :5355 | continua | C | resolución |
| accounts-daemon | 2,3 MB | ~0 | cuentas | a demanda | D | AccountsService |
| systemd-logind | 1,9 MB | baja | **1.590 líneas/2 h** (sesiones sudo) | eventos | A | login/seat |
| pcscd | 1,8 MB | ~0 | smartcard | a demanda | D | PC/SC |
| powerstation | 1,5 MB | ~0 | gestiona núcleos/SMT | continua | D/F | "PowerStation Service" — ver §13.5 |
| uresourced | 1,3 MB | ~0 | recursos sesión | a demanda | A | QoS de sesión |
| power-profiles-daemon | 1,3 MB | ~0 | perfiles energía | eventos | C/D | PPD (solapa con powerdevil) |
| gssproxy | 1,3 MB | ~0 | GSSAPI | a demanda | D | kerberos |
| irqbalance | 1,1 MB | ~0 | balance IRQ | continua | D | balance IRQ (co-activo con kalmd → conflicto) |
| switcheroo-control | 1,0 MB | ~0 | modo dual GPU | eventos | C/D | switcheroo |
| scx_loader | 1,0 MB | ~0 | carga sched-ext vía D-Bus | a demanda | D | schedulers ext (Nobara/Fedora) |
| rtkit-daemon | 0,9 MB | ~0 | prioridad de audio realtime | a demanda | C | PipeWire rt |
| auditd | 0,9 MB | baja | **1.393 líneas/2 h** | eventos | A/D | auditoría (log alto por autopilot) |
| crond/atd | ~0,8 MB | ~0 | cron/at | a demanda | D/E | colas (sin cronjobs vistos) |
| systemd-machined | 0,8 MB | ~0 | VMs/ctn | a demanda | A | registro |
| alsa-state | 0,4 MB | ~0 | guarda estado audio | boot | C | audio |
| getty@tty2 | 0,3 MB | ~0 | consola TTY | — | A | login local |
| (packagekitd) | 215 MB | ~2 % (puntual) | activo desde 09:37 | a demanda | D | gestión paquetes (ver nota §6) |

*RAM = `MemoryCurrent`. **Nota**: `packagekitd` arrancó a las 09:37 durante la auditoría (refresco a demanda, probablemente del AppCenter); no es un proceso periódico.

### 3.2 Trío Kalm — detalle (personalizados, mayo 2026, fuera de RPM)

Unidades en `/etc/systemd/system/`, scripts en `/opt/kalm/kalmd.py`, `/usr/local/bin/kalm-lite.py`, `/usr/local/bin/kalm-gpu`:
- **kalmd.py**: bucle `while True` de descubrimiento de IRQ (PCI msi_irqs) + intento de escribir `smp_affinity_list`. **Evidencia de periodo 15 s**: journal `09:43:43` y `09:43:58` repiten `[Kalm] IRQ 35/33/31/34/32/30/29: no smp_affinity_list, omitiendo` (7 líneas × ~4 ciclos/min ≈ **28 líneas/min = 1.680/hora**). Detecta `irqbalance.pid` pero sigue ciclando y logueando. **Redundante con irqbalance** (ambos gestionan afinidad).
- **kalm-lite.py**: monitorea `/proc/pressure/*` cada **10 s**; escribe `swappiness`/`dirty_ratio` con cooldown de 60 s. Valores actuales: `swappiness=10`, `dirty_ratio=5`, `dirty_background_ratio=1` (más bajos que Fedora 20/10).
- **kalm-gpu**: `POLL_SEC=2.0`, lee hwmon de la RX550 (`temp1_input=34000` → **34 °C**); escribe power cap cuando hace falta. Poll en memoria (sin I/O de disco), pero despierta la CPU cada 2 s.

---

## 4. Timers

### 4.1 Timers de sistema (12) — evidencia `systemctl list-timers --all`

| Timer | Frecuencia | Última / próxima | Dispara | Qué hace | Disco | CPU | Red | Procesos |
|---|---|---|---|---|---|---|---|---|
| **system-autopilot** | **cada 2 min** (`OnUnitActiveSec=2min`) | 09:56 / 09:58 | system-autopilot.service | script custom auto-tune (governor, IRQ affinity, sysctls net, scheduler, renice) | **sí** (journal/PAM/audit: 24 ciclos/h) | **sí** (~10 subprocesos `sudo`/`sysctl`/`bc`/`pgrep`/`renice` por ciclo) | no (solo reafirma sysctls) | sí, muchos efímeros |
| **sys-tuned** | cada 30 min | 09:45 / 10:15 | sys-tuned.service | tune estable (schedutil, swappiness, scheduler, IRQ, net) | menor | menor | no | sí, pocos |
| **sys-optimize** | al boot (Persistent) | 07:53 / — | sys-optimize.service | tune de arranque | una vez | menor | no | una vez |
| dnf-makecache | ≈cada 3,5 h (aleatorio) | 08:22 / 11:54 | dnf5 makecache | solo **metadatos** (clase A de la auditoría previa; `ConditionACPower=true`) | leve | menor | **sí** | sí |
| sysstat-collect | **cada 10 min** | 09:50 / 10:00 | sysstat-collect | recoge stat → escribe `/var/log/sa/saDD` | **sí (cada 10 min)** | menor | no | sí |
| sysstat-summary | 1×/día 00:07 | — | sysstat-summary | resumen diario | sí | menor | no | sí |
| sysstat-rotate | 1×/día 00:00 | — | sysstat-rotate | rota datos sysstat | sí | menor | no | sí |
| logrotate | 1×/día 00:46 | 00:11 / 00:46+1d | logrotate | rota logs/paketes | sí | menor | no | sí |
| unbound-anchor | 1×/día 00:00 | 00:00 | unbound-anchor | refresca ancla DNSSEC raíz | leve | menor | **sí** | sí |
| systemd-tmpfiles-clean | 1×/día | 08:27 / +1d | tmpfiles-clean | limpia /tmp etc. | leve | menor | no | sí |
| fstrim | semanal (lun 00:25) | 21-09 / 28-09 | fstrim | TRIM **no aplica a HDD mecánico** → no-op | (no-op) | — | — | — |
| raid-check | semanal (dom 01:00) | 20-09 / 27-09 | raid-check | sin RAID → no-op | (no-op) | — | — | — |

**Especial atención a timers de pocos minutos**: el único es **`system-autopilot` (2 min)** — principal fuente de despertares periódicos (ver §13.3.1).

### 4.2 Timers de usuario (4) — evidencia `systemctl --user list-timers`

| Timer | Frecuencia | Dispara | Qué hace | Disco/CPU/Red |
|---|---|---|---|---|
| systemd-tmpfiles-clean | diario | tmpfiles-clean | limpia temporales del usuario | leve / no / no |
| drkonqi-coredump-cleanup | semanal | DrKonqi cleanup | limpia datos de crash | leve / no / no |
| **drkonqi-sentry-postman** | **horaria** | sentry-postman | **envía crash pendientes a Sentry** (telemetría; nunca ha disparado: `LAST —`) | leve / no / **sí (si hay crash)** |
| grub-boot-success | one-shot (+2 min de sesión) | grub-boot-success | marca boot OK (corrió 08:16) | leve / no / no |

---

## 5. KDE (Plasma 6) — componente por componente

| Componente | PID/RSS | Activo | Veredicto |
|---|---|---|---|
| plasmashell | 6430 / 396 MB | sí | **Necesario** (shell; 56 hilos) |
| kwin_wayland | 6307 / 234 MB | sí | **Necesario** (compositor; conflictos en IRQ i915 = su trabajo) |
| startplasma-way / ksmserver | 5960 / — | sí | necesario (gestor de sesión) |
| Xwayland | 6366 / 84 MB | sí | necesario (opencode/ChatGPT son X11; tiene card0+card1+renderD128) |
| kded6 | 6425 / 99 MB | sí | necesario (daemon de servicios KDE; I/O 2,5 MB/60 s) |
| kactivitymanagerd | — / 50 MB | sí | actividad de sesión (meh, útil) → RECOMENDADO |
| org_kde_powerdevil | 6457 / 63 MB | sí | energía/brillo → **Necesario** (PPD duplica parte) |
| polkit-kde-auth | 6456 / 158 MB | sí | prompts de auth → **Necesario** (no desactivar) |
| ksecretd + kwalletd6 | 6753 / 70 MB | sí | almacén de claves → **Necesario** |
| **Baloo** (baloo_file + baloorunner) | ~30 MB + 54 MB | **idle** | indexador terminado: **2.372 archivos, índice 48,17 MiB, estado "Inactivo"** (`balooctl6 status`). No indexa ahora; despierta con cambios de archivos → **RECOMENDADO MANTENER** (búsquedas); pequeño coste en HDD solo durante reindexado |
| KRunner | — | a demanda | no residente |
| **KDE Connect** (kdeconnectd) | 6636 / 66 MB | autostart | red: TCP :1716 + UDP broadcast :34388 + mDNS → **OPCIONAL** (si no se usa con el móvil, es tráfico LAN periódico) |
| xdg-desktop-portal-kde + -gtk | ~35 MB | sí | portales; el **GTK es redundante** con KDE (pequeño) → OPCIONAL el GTK |
| xdg-document-portal / permission-store | pequeño | sí | flatpak → necesario si se usan flatpaks |
| **plasma-keyboard** | 6359 / 166 MB | sí | **teclado virtual residente con 4× renderD128** → OPCIONAL (en escritorio con teclado físico; se desactiva desde KDE, no con systemd) |
| **xwaylandvideobridge** | 6644 / 104 MB | autostart | puente X11→Wayland para compartir pantalla (OBS/Discord) → **OPCIONAL** |
| kaccess / gmenudbusproxy / xembedsniproxy | pequeño | sí | accesibilidad/menús GTK/iconos tray → mantener (ligeros) |
| **mako** | 6717 / 23 MB | **activo** | **daemon de notificaciones Wayland redundante**: hoy es el dueño de `org.freedesktop.Notifications` (unit `Type=dbus`, activado por nombre de bus, `is-enabled=disabled` pero activo). Plasma tiene su propio sistema → ver §13.3.5 |
| at-spi (a11y) | 2× registry | sí | accesibilidad; doble registry (D-Bus :1.21 y :1.95) — nota menor |
| gvfs + gvfs-metadata | pequeño | sí | necesario (montajes/GUI) |
| dconf | pequeño | sí | preferencias |
| uresourced | 1,3 MB | sí | QoS de sesión → mantener |
| Discover | — | no residente | solo abre su tray/updater; AppCenter Updater ya deshabilitado (§6) |
| geoclue-demo-agent | autostart | **activo** | **agente de demostración de ubicación** (geoclue system está `inactive`) → OPCIONAL/CANDIDATO (§13.3.6) |

---

## 6. Aplicaciones en segundo plano (residentes sin uso activo)

| App/proceso | RSS | Evidencia de actividad | Clasificación de consumo |
|---|---:|---|---|
| **ChatGPT familia** (12 procs: main, renderers, gpu, network, codex) | **2.474 MB** | sockets FCM/Cloudflare; renderer 5–6 % CPU | App del usuario en uso (Codex/chatgpt). **NO TOCAR**, pero es el mayor bloque de RAM |
| **openclaw-gateway** (node) | 574 MB | listener localhost :18789/:18791 + mDNS | Infra del usuario (OpenClaw v2026.4.29, autostart systemd-user). OPCIONAL según uso |
| opencode (3 procs de la sesión actual) | 762 MB | activo | **es la sesión en curso** (no fondo) |
| **nobara-sync cli** (EUID root, PPID 1277) | 452 MB | **1 h 15 min ejecutándose**, 2,1 % CPU sostenido | **DESCONOCIDO — requiere investigación** (§13.5). No es timer: parece un lanzamiento manual/AppCenter que no terminó. No se debe matar sin decisión del usuario |
| **open-webui** (docker, uvicorn) | 420 MB | `0.0.0.0:8080`; contenedor `open-webui:main` hace 4 meses | Infra AI del usuario. OPCIONAL (revisar exposición 0.0.0.0) |
| docker + containerd + shim | ~167 MB | runtime | igual que arriba |
| ollama | 54 MB | `0.0.0.0:11434` (solo local en uso: opencode/open-webui) | igual |
| dnf-app-center-updater | 290 MB | en `~/.config/dnf-app-center/updater.json` → `enabled:false`, `notifications:false`, intervalo 999 semanas; hijo zombie | **ya desactivado por el usuario**; queda residente por autostart. OPCIONAL purgar autostart (ver auditoría previa) |
| packagekitd | 215 MB | arrancó 09:37, termina solo | a demanda (Discover/AppCenter/dnf5). Mantener |
| konsole | 115 MB | terminal con la auditoría | en uso |
| falcond | 2,8 MB | gaming daemon, `enable_performance_mode=true`, `scx_sched=none` → idle | OPCIONAL (decisión de juego) |
| powerstation | 1,5 MB | gestiona núcleos/SMT | DESCONOCIDO parcial — ver §13.5 |
| ds-inhibit | 7,8 MB | inhibitor DualShock/DualSense | pequeño, gaming |
| obexd | 8 MB | servicio OBEX; **bluetooth.service inactive** → sin pareja BT activa | OPCIONAL |
| ssh-agent | 5,3 MB | agente | mantener (si se usan claves) |
| geoclue-demo | ~5 MB | demo de ubicación | OPCIONAL (§13.3.6) |
| mako | 23 MB | §5 | CANDIDATO (§13.3.5) |

---

## 7. Disco / HDD mecánico (SAMSUNG HM500JI)

### 7.1 Configuración observada
- `sda`: 465,8 GB; `/boot` ext4 (sda1) + `/` y `/home` btrfs **subvolúmenes @ y @home de sda2** + swap sda3 (sin uso; 357 MB en **zram0**). Todo el sistema y la sesión viven en el mismo HDD → **cualquier I/O de cualquier servicio lo despierta**.
- Scheduler `mq-deadline`, `read_ahead_kb=256` (fijados por los scripts custom). `swappiness=10`, `dirty_ratio=5`, `dirty_background_ratio=1` (tuners custom; flushes más frecuentes/menores — en HDD mecánico puede aumentar seeks; caveat documentado).
- `journald` ocupa **185,3 MB** (186 MB en `/var/log/journal`), `/var/log/audit` 0 bytes (va al journal).

### 7.2 Evidencia de actividad (iostat, 3 muestras de 1 s)
```
sda   r/s=28  rkB/s=1599  r_await=118 ms   w/s=27  wkB/s=1213  w_await=273 ms   %util=53 %
sda   r/s=106 rkB/s=3592  r_await= 24 ms                       %util=93 %   (muestra pico)
sda   r/s=13  rkB/s=236   r_await= 16 ms   w/s=16  %util=36 %
```
→ El HDD trabaja de forma sostenida incluso sin interacción del usuario.

### 7.3 Ventana de 60 s (muestreador `/tmp/opencode/idle_sample2.py`, deltas)
```
sda:  2005 lecturas · 95.728 sectores leídos (~48,9 MB)
      2989 escrituras · 315.176 sectores escritos (~161 MB)
      io_ms = 1.777.733 (~29,6 min de I/O acumulado en 60 s)
IRQ:  ahci 27  +5.009 (≈83/s) · i915 40 +3.674 · xhci 28 +922 · enp3s0 39 +72
I/O por proceso lucas (solo UID 1000): plasmashell rd 8,2 MB · opencode rd ~6 MB ·
      kded6 rd 2,5 MB + wr 1 MB · ChatGPT wr ~0,6 MB  (75 procesos muestreados)
```
→ **Los ≈161 MB/60 s escritos provienen de servicios root** (journald con sus volcados, docker/open-webui, btrfs), no de procesos de `lucas` (atribución exacta requiere root — limitación). El HDD está activo incluso con poca carga del usuario.

### 7.4 Despertar periódico del HDD
- `system-autopilot` (cada 2 min): writes de journal/PAM/audit durante cada ciclo.
- `kalmd` (cada 15 s): ~28 líneas/min al journal → journald escribe periódicamente.
- `sysstat-collect` (cada 10 min): escribe en `/var/log/sa/`.
- `logrotate` (1×/día) y `dnf-makecache` (metadatos, leve): I/O puntual ya documentada.

---

## 8. CPU (i7-4790)

- **Governor**: `performance` fijado por `system-autopilot` (carga>2,5). Frecuencias leídas: **3,83/3,59/3,59/3,59/3,59/3,83/3,79/3,85 GHz** (los 8 núcleos en turbo, sin idle profundo). `sys-tuned` (schedutil, 30 min) se pelea con autopilot → oscilación gobernador continua. Efecto colateral: más calor/consumo en un equipo usado a media carga.
- **Despertadores frecuentes** (ordenados): `kalm-gpu` (2 s), `kalm-lite` (10 s), `kalmd` (15 s), `system-autopilot` (2 min), `sysstat-collect` (10 min).
- **Picos periódicos**: autopilot (multi-spawn con `sudo` — picos de 1-2 s cada 2 min) y sysstat.
- **IRQ por CPU**: i915 **+3.674/60 s** (trabajo real de composición Intel) y ahci **+5.009/60 s** (disco) dominan; xhci (USB) +922 (posible entrada periférica/`ds-inhibit`).
- Sin `turbostat`/`powertop` (root) no se midió residencia de C-states; la evidencia (frecuencias en turbo + carga 1m>2,5) indica **sin reposo profundo sostenido**.

---

## 9. RAM

- `free -m`: total **11.817** · used 5.841 · free 761 · buff/cache 5.954 · **available 5.975**. `zram0` 357 MB usados; swap `sda3` 0. **La page cache (buff/cache) NO es RAM desperdiciada** (se libera bajo presión); se reporta `available`.
- Consumidores RSS (evidencia ps, 09:44):

| Familia/proceso | RSS | Recuperable al cerrar/desactivar |
|---|---:|---|
| ChatGPT (12 procs) + codex | 2.474 MB | NO (en uso) |
| opencode (3 procs — sesión actual) | 762 MB | NO (en uso) |
| openclaw-gateway | 574 MB | sí, si no se usa (decisión del usuario) |
| nobara-sync (EUID root) | 452 MB | **sí, si está colgado** (proceso manual; no matar sin decisión) |
| open-webui (docker) | 420 MB | sí, si no se usa la web AI |
| plasmashell | 396 MB | NO (compositor) |
| dnf-app-center-updater | 290 MB | sí, si se purga el autostart (ya desactivado) |
| kwin_wayland | 234 MB | NO |
| packagekitd | 215 MB | termina solo |
| plasma-keyboard | 166 MB | sí (OPCIONAL) |
| polkit-kde-auth | 158 MB | NO (auth GUI) |
| xwaylandvideobridge | 104 MB | sí (OPCIONAL) |
| Xwayland | 84 MB | NO (necesario) |
| kded6 | 99 MB | NO |
| kdeconnectd | 66 MB | sí (OPCIONAL si sin móvil) |
| ollama | 54 MB | sí (si sin uso) |
| baloorunner/baloo | 84 MB | parcial (búsquedas perdidas) |
| mako | 23 MB | sí (redundante) |
| trío kalm | ~16 MB | marginal |

~ Memoria recuperable razonable sin afectar KDE: **unos 650–1.100 MB** (mako + plasma-keyboard + xwaylandvideobridge + geoclue + kdeconnect si no se usa + nobara-sync si está colgado). El resto de la sesión (5,2 GB) es el escritorio + apps del usuario.

---

## 10. GPU

**Mapa de handles `/dev/dri`** (evidencia `ls -l /proc/<pid>/fd | grep dri`):

| Proceso | i915 card0/renderD128 | amdgpu card1/renderD129 |
|---|---|---|
| plasmashell | renderD128 (×1) | — |
| plasma-keyboard | renderD128 (×4) | — |
| Xwayland | card0 + renderD128 (×6) | **card1** (contexto) |
| xwaylandvideobridge | renderD128 (×3) | — |
| ChatGPT (gpu-proc 7673) | renderD128 (×7) | **renderD129** |

- **Intel HD 4600 = GPU de composición activa**: +3.674 IRQ i915/60 s. Sin contadores fdinfo (i915 no los publica).
- **RX 550 (amdgpu) = ociosa**: **cero IRQ amdgpu** en la ventana; temp1_input **34 °C**; `renderD129` solo la mantienen Xwayland y el proceso GPU del ChatGPT (contexto DRM, sin actividad). `kalm-gpu` la vigila cada 2 s (hwmon, en memoria).
- **Limitación**: fdinfo no exporta contadores de motor (Polaris/i915) → la atribución GPU se basa en handles + IRQ, que es suficiente para concluir *RX550 inactiva / Intel activa*.
- **NO TOCAR nada de amdgpu/RX550** (regla del proyecto). `kalm-gpu` es la única pieza que escribe sobre ella (power cap), y es custom del usuario — ver §13.3.4.

---

## 11. Red

**Sockets persistentes** (evidencia `ss -tunp`, 09:45):

| Proceso | Conexión | Tipo |
|---|---|---|
| ChatGPT (7699, network) | 64.233.190.188:**5228** ×3 | **Google FCM** (push persistente) |
| opencode + ChatGPT | 104.18.39.21 / 172.65.x / 172.64.x :443 | Cloudflare (gateway/API) |
| opencode + ChatGPT | 35.190.80.1 :443 | Google Cloud |
| opencode | 127.0.0.1:**49374** (serve local) y 127.0.0.1:**11434** (ollama) | local |
| openclaw-gateway | 127.0.0.1:18789/:18791 + mDNS 5353 | local + link-local |
| kdeconnectd | **:1716 TCP** + UDP :34388 + broadcast + mDNS | LAN |
| systemd-resolved | UDP :53 localhost + **LLMNR :5355** (v4/v6) | link-local |
| DHCP | UDP :68 → 192.168.100.1:67 | enlace |
| chronyd | UDP :123 NTP | saliente puntual (journal: "KoD RATE" de un servidor NTP) |

**Listeners de exposición**: `0.0.0.0:**8080**` (open-webui), `0.0.0.0:**11434**` (ollama), `*:1716` (kdeconnectd, LAN), LLMNR 5355. **Tráfico periódico pese a inactividad**: FCM push del ChatGPT, mDNS/broadcast de KDE Connect y openclaw, LLMNR. **Esta auditoría no generó tráfico externo** (solo lecturas `ss`).

---

## 12. Journal / logging

- Volumen: **185,3 MB** (`journalctl --disk-usage`); 41.426 líneas en las últimas 2 h (incluye boot y múltiples inicios de `dracut`).

**Top por unidad (2 h)** — evidencia:

| Unidad | Líneas / 2 h | Origen |
|---|---:|---|
| systemd[1] | 4.170 | en gran parte arranques/paradas de servicio del autopilot y boot |
| dracut (×4 procesos) | ≈16.000 | **solo boot** (08:12); no es periódico |
| **python3[4055] = kalmd** | **2.323** | **repetitivo 15 s: "IRQ N: no smp_affinity_list, omitiendo" ×7** |
| kernel | 1.904 | boot + eventos HW |
| systemd-logind (1008/1003) | 1.936 | **sesiones PAM del sudo de autopilot** (cada 2 min) |
| audit[1]+audit | 1.393 | eventos exec/sudo de autopilot-sysctl etc. |
| rpm | 713 | salidas de dnf5/packagekit (sesión previa del usuario) |
| chatgpt | 450 | app del usuario |
| systemd[1277] (user) | 330 | fondo de sesión |

**Servicio que despierta únicamente para registrar**: **kalmd** (28 líneas/min, sin efecto útil porque las afﬁnidades no se pueden escribir mientras `irqbalance` domina). **Mensajes repetitivos secundarios**: sesiones sudo del autopilot (x ~10 cada 2 min); `chronyd "KoD RATE"` puntual.

---

## 13. Resultado

### 13.1 Tabla final

| Proceso/servicio | CPU | RAM | I/O | Frecuencia | Función | Necesidad | Potencialmente desactivable |
|---|---:|---:|---:|---|---|---|---|
| systemd-journald | baja | 28 MB | alto (185 MB log) | continua | logging | NECESARIO | no |
| systemd-logind | baja | 2 MB | medio | eventos | login/sesiones | NECESARIO | no |
| dbus-broker (sys+user) | baja | 5+ MB | bajo | continua | bus de mensajes | NECESARIO | no |
| systemd-udevd | baja | 39 MB | bajo | eventos | hardware | NECESARIO | no |
| systemd-resolved | baja | 2 MB | bajo | continua | DNS/LLMNR | NECESARIO | no |
| NetworkManager | baja | 5,5 MB | bajo | continua | red | NECESARIO | no |
| polkit + polkit-kde-auth | baja | 9+158 MB | bajo | a demanda | autorización | NECESARIO | no |
| plasmashell | baja | 396 MB | 8 MB/60 s | continua | shell KDE | NECESARIO | no |
| kwin_wayland | 4–6 % | 234 MB | bajo | continua | compositor | NECESARIO | no |
| ksmserver/startplasma | baja | — | bajo | continua | sesión KDE | NECESARIO | no |
| Xwayland | baja | 84 MB | bajo | continua | apps X11 (opencode/ChatGPT) | NECESARIO | no |
| kded6 | baja | 99 MB | 2,5 MB/60 s | continua | daemon KDE | NECESARIO | no |
| pipewire/pulse/wireplumber + rtkit | baja | ~50 MB | bajo | continua | audio | NECESARIO (C) | no |
| xdg-desktop-portal(-kde) | baja | ~35 MB | bajo | a demanda | portales | NECESARIO | no |
| upower/powerdevil | baja | 66 MB | bajo | eventos | energía | NECESARIO | no |
| smartd | baja | 3,5 MB | bajo | continua | **SMART HDD** | RECOMENDADO | no |
| systemd-tmpfiles-clean (sys+user) | baja | — | leve | diario | limpieza | RECOMENDADO | no |
| gvfs + dconf + metadata | baja | ~20 MB | bajo | a demanda | GUI/archivos | RECOMENDADO | no |
| Baloo (+baloorunner) | baja | 84 MB | leve (idle) | a demanda | búsqueda local | RECOMENDADO | no |
| chronyd | baja | 3,8 MB | bajo | continua | NTP | RECOMENDADO | no |
| udisks2 | baja | 6 MB | bajo | eventos | discos | RECOMENDADO | no |
| uresourced | baja | 1,3 MB | bajo | a demanda | QoS sesión | RECOMENDADO | no |
| packagekitd | ~2 % puntual | 215 MB | medio | a demanda | paquetes (Discover) | RECOMENDADO | no |
| KDE Connect | baja | 66 MB | bajo | continua | móvil; **red UDP** | OPCIONAL | sí (si sin móvil) |
| xwaylandvideobridge | baja | 104 MB | bajo | continua | compartir pantalla X11 | OPCIONAL | sí |
| plasma-keyboard | baja | 166 MB | bajo | continua | teclado virtual | OPCIONAL | sí (por KDE, no systemd) |
| geoclue-demo-agent | baja | ~5 MB | bajo | continua | demo de ubicación | OPCIONAL | sí |
| xdg-desktop-portal-gtk | baja | ~8 MB | bajo | a demanda | portal GTK redundante | OPCIONAL | sí |
| obexd | baja | 8 MB | bajo | (BT inactivo) | OBEX | OPCIONAL | sí |
| ssh-agent | baja | 5 MB | bajo | continua | claves SSH | OPCIONAL | depende de uso |
| falcond | baja | 2,8 MB | bajo | a demanda | gaming optimizer (PikaOS) | OPCIONAL | sí (si sin gaming) |
| ds-inhibit | baja | 7,8 MB | bajo | continua | inhibitor mouse PS | OPCIONAL | sí (gaming) |
| docker+containerd | baja | ~167 MB | medio (logs) | continua | contenedores (open-webui) | OPCIONAL | sí (revisar AI) |
| ollama | baja | 54 MB | bajo | continua | LLM local | OPCIONAL | sí (revisar AI) |
| open-webui (docker) | baja | 420 MB | medio | continua | web AI | OPCIONAL | sí (revisar AI) |
| openclaw-gateway | baja | 574 MB | bajo | continua | agente del usuario | OPCIONAL | sí (si sin uso) |
| ChatGPT familia | 5–10 % | **2.474 MB** | bajo | continua | app del usuario | EN USO (no fondo) | no (uso activo) |
| opencode (sesión actual) | ~15 % | 762 MB | 6 MB/60 s | continua | sesión de auditoría | EN USO | no |
| dnf-app-center-updater | baja | 290 MB | bajo | **desactivado ya** | updater (config off) | OPCIONAL | sí (purga autostart) |
| `system-autopilot.timer` | picos | efímero | **alto (journal)** | **cada 2 min** | auto-tune custom | **CANDIDATO** | **sí** |
| kalmd (kalm.service) | baja | 7,6 MB | **medio (log 28/min)** | **cada 15 s** | IRQ affinity custom | **CANDIDATO** | **sí** |
| kalm-lite | baja | 5,4 MB | bajo | cada 10 s | memory/IO tuner | **CANDIDATO (leve)** | sí |
| kalm-gpu | baja | 3,5 MB | bajo | cada 2 s | thermal governor RX550 | OPCIONAL/CAVEAT | **decisión** (ver 13.3.4) |
| mako | baja | 23 MB | bajo | a demanda | notificaciones (redundante) | **CANDIDATO** | **sí** |
| drkonqi-sentry-postman.timer | baja | — | bajo | **horaria** | telemetría de crash | **CANDIDATO** (privacy) | sí |
| nobara-sync (EUID root) | 2,1 % | 452 MB | medio | raro (1 h+ ) | updater manual | **DESCONOCIDO** | **investigar** |
| powerstation | baja | 1,5 MB | bajo | continua | núcleos/SMT | DESCONOCIDO parcial | investigar |
| irqbalance | baja | 1,1 MB | bajo | continua | balance IRQ | RECOMENDADO | no (es el que no loguea) |
| auditd | baja | 0,9 MB | medio (eventos) | eventos | auditoría | RECOMENDADO | no |

### 13.2 Categorías (criterio explícito)

- **NECESARIO**: sin él el sistema o el escritorio no funciona (todos los `A`/`B`/`C` de §3 y §5).
- **RECOMENDADO MANTENER**: funciona y aporta de forma real; el coste medido es bajo (p. ej. `smartd` protege un HDD, `baloo` ya está idle, `chronyd` estándar).
- **OPCIONAL**: coste bajo o medio y se pierde funcionalidad concreta si se quita (KDE Connect, teclado virtual, puente video, infra AI del usuario).
- **CANDIDATO A DESACTIVACIÓN**: coste desproporcionado para lo que aporta, o redundante, o generador de actividad periódica sin función efectiva (autopilot, kalmd, mako, sentry-postman, geoclue-demo).
- **NO TOCAR**: sesión en uso, compositor, amdgpu/RX550 y todo lo marcado NO en §13.1.
- **DESCONOCIDO — requiere investigación**: `nobara-sync` en ejecución prolongada; detalles finos de `powerstation`; comportamiento exacto de `falcond` en este sistema (fuentes: **README de falcond** leído; para powerstation se debería consultar la doc del paquete Fedora 0.8.4; para `scx_loader` la doc de sched-ext de Fedora).

### 13.3 Fichas de CANDIDATO A DESACTIVACIÓN (comandos = SOLO documentación, NO ejecutados)

#### 13.3.1 `system-autopilot.timer` (el más importante)
- **Evidencia**: 24 ejecuciones/h; log `[AUTO-PILOT] Starting optimization cycle` → `[PROC] tuned` → `cycle complete` cada 2 min; cada ciclo dispara ~10 `sudo` (journal: `sudo[94885]: COMMAND=/usr/sbin/renice -10 -p 6296` + PAM session open/close), 4 `sysctl`, `echo` a `/sys`.
- **Qué se gana**: −~10 subprocesos y −sesiones PAM/logind/audit cada 2 min → menos journal (crecimiento), menos despertares del HDD, menos picos de CPU; el governor deja de oscilar (queda el de `sys-tuned`, schedutil, o el del usuario).
- **Qué se pierde**: ajuste dinámico a `performance` cuando carga>2,5 (recuperable ejecutando el script a mano), afinidad IRQ de `enp3s0`, reafirmación de sysctls net y scheduler (ya los fija `sys-tuned` cada 30 min), `renice kwin/firefox`.
- **Impacto**: KDE → nulo (salvo perder el nice −10 de kwin, no crítico) · HDD → positivo (menos wakes) · RAM → nulo · CPU → positivo · red → nulo (solo reafirma sysctls).
- **Revertir**: `systemctl enable --now system-autopilot.timer`
- **Desactivar (doc)**: `systemctl disable --now system-autopilot.timer`

#### 13.3.2 `kalm.service` (kalmd)
- **Evidencia**: bucle 15 s; 1.680 líneas journal/h de “no smp_affinity_list, omitiendo”; `irqbalance` ya hace el trabajo (conflicto de afinidad detectado por el propio script).
- **Ganancia**: −28 líneas journal/min → journald escribe menos (HDD), menos wakeups.
- **Pérdida**: política de afinidad IRQ custom del usuario (topología GPU/INPUT/NET/STORAGE) — ya no efectiva mientras corre `irqbalance` (evidencia: omite todas las escrituras).
- **Impacto**: KDE nulo · HDD positivo · RAM insignificante · CPU positivo leve · red nulo.
- **Revertir**: `systemctl enable --now kalm.service`
- **Desactivar (doc)**: `systemctl disable --now kalm.service`

#### 13.3.3 `kalm-lite.service` (leve)
- Poll PSI cada 10 s; escribe sysctl con cooldown. Mantiene `swappiness=10`/`dirty 5/1`.
- **Ganancia** si se desactiva: menos polls (10 s) y menos flushes de dirty pagecache (puede reducir seeks del HDD). **Pérdida**: valores custom de swappiness/dirty se restablecen a Fedora por defecto (20/10) en el próximo arranque.
- **Revertir**: `systemctl enable --now kalm-lite.service` · **Desactivar (doc)**: `systemctl disable --now kalm-lite.service`

#### 13.3.4 `kalm-gpu.service` — CAVEAT RX550
- **NO tocar amdgpu/RX550** (regla del proyecto). Este servicio es el **gobernador térmico de la RX550** (poll 2 s, temp actual 34 °C). Desactivarlo **no toca amdgpu** pero deja la GPU sin protección térmica activa del script custom (el límite de potencia del kernel sigue actuando).
- **Ganancia**: −1 wake cada 2 s. **Pérdida**: vigilancia térmica custom de la RX550. **Recomendación**: mantener si se usa la RX550 para carga real; es el único candidato que no recomiendo desactivar salvo decisión explícita del usuario.
- **Revertir**: `systemctl enable --now kalm-gpu.service` · **Desactivar (doc)**: `systemctl disable --now kalm-gpu.service`

#### 13.3.5 `mako.service` (usuario)
- **Evidencia**: activo vía D-Bus (`is-enabled=disabled`, `Type=dbus`, `BusName=org.freedesktop.Notifications`); en Plasma el propio escritorio gestiona notificaciones → **duplicado**. 23 MB.
- **Ganancia**: −23 MB y se elimina la ambigüedad de quién muestra notificaciones (Plasma). **Pérdida**: ningún comportamiento Plasma; solo apps Wayland que pidieran mako explícitamente (improbable). Certeza media-alta.
- **Revertir**: `systemctl --user enable --now mako.service` · **Desactivar (doc)**: `systemctl --user disable --now mako.service`

#### 13.3.6 `app-geoclue-demo-agent@autostart` (usuario)
- Agente de demostración de ubicación (`geoclue.service` system está *inactive*). Pequeño; opcional puro.
- **Revertir**: habilitar el autostart desde KDE (Autostart) · **Desactivar (doc)**: `systemctl --user disable --now app-geoclue\x2ddemo\x2dagent@autostart.service`

#### 13.3.7 `drkonqi-sentry-postman.timer` (usuario) — telemetría
- **Evidencia**: unit user con `OnCalendar=hourly`, descripción “Submitting pending crash events” (envía dumps de crash a Sentry); nunca disparó (LAST `—`).
- **Ganancia**: privacidad (no enviar dumps); cero impacto de rendimiento. **Pérdida**: no se reportan crashes de KDE (diagnóstico).
- **Revertir**: `systemctl --user enable --now drkonqi-sentry-postman.timer` · **Desactivar (doc)**: `systemctl --user disable --now drkonqi-sentry-postman.timer` (alternativa: KDE → Configuración → Fallos → no enviar informes)

### 13.4 Qué NO desactivar (recomendaciones explícitas)
`smartd` (HDD), `kwin/plasmashell/Xwayland`, `polkit*`, `pipewire*`/`rtkit`, `systemd-*` base, `NetworkManager`, `chronyd`, `ssh-agent`, `powerdevil`, `upower`, `packagekit` (Discover), `gvfs`, `xdg-desktop-portal-kde`, `baloo` (idle), `docker/ollama/open-webui` **hasta decidir sobre la infra AI**, y **todo lo relacionado con amdgpu/RX550**.

### 13.5 DESCONOCIDO — requiere investigación
- **`nobara-sync` (PID 12594, EUID root, PPID 1277)**: corriendo desde 09:04 (>1 h), 452 MB RSS, 2,1 % CPU sostenido. No hay timer/unit que lo lance (PPID = sesión de usuario). Parece un lanzamiento manual/AppCenter **sin terminar** → decisión del usuario (no matarlo sin su autorización). No es un mecanismo automático del sistema.
- **`powerstation`**: daemon de núcleos/SMT (1,5 MB); paquete Fedora 0.8.4. Función fina no confirmada en docs locales → consultar documentación del paquete antes de cualquier decisión.
- **`falcond`**: confirmado por README como optimizador gaming; con `scx_sched=none` está idle. Si no hay gaming, es OPCIONAL, pero se deja la decisión al proyecto (fuente: `/usr/share/doc/falcond/README.md`).
- **`scx_loader`**: `sched-ext` activo; `root/ops` vacío → scheduler concreto no confirmado (Nobara/Fedora cargan uno por defecto en boots modernos).

---

## 14. Verificación final (debe quedar sin cambios)

1. **Sin modificaciones del sistema**: solo se escribió en `/tmp/opencode/` (`res_before_pids.txt`, `idle_sample*.py`). No hubo `stop`/`disable`/`mask`/`kill`/`sudo`/cambios de config ni de repo.
2. **Timers**: `systemctl list-timers --all` al final = **12 timers, mismas unidades y cadencias** que al inicio (autopilot 2 min, sys-tuned 30 min, dnf-makecache 3 h, sysstat 10 min, logrotate/fstrim/raid-check/unbound/tmpfiles diarios/semanales; user: tmpfiles/grdkonqi-cleanup/sentry-postman/grub-boot-success). Timers que dispararon durante la auditoría = los esperados (autopilot ×4, sys-tuned).
3. **`is-enabled` clave idéntico**: dnf-makecache, system-autopilot, sys-tuned, sys-optimize, kalm, kalm-gpu, kalm-lite, falcond, powerstation, docker, ollama, irqbalance → `enabled`; mako user → `disabled`(activo por bus). **`is-active`**: kalm, kalm-gpu, kalm-lite, falcond, powerstation, docker → `active` (igual que al inicio).
4. **Ningún proceso muerto**: verificados vivos al final: 1277 (systemd user), 5960 (startplasma), 6307 (kwin), 6430 (plasmashell), 7585/8092 (ChatGPT), 4055/4054/6441 (kalm trio), 6634 (app-center updater), 12594 (nobara-sync).
5. **`git status`** (proyecto): **36 `M` + 7 `??`** — igual que al inicio; este informe es el único archivo nuevo (8.º `??`).
6. **Resumen de principales consumidores** (medido):
   - **CPU**: sesión de auditoría (opencode ~15 %), ChatGPT familia (~5–10 %), kwin (~4–6 %), konsole (~6 %), nobara-sync (2,1 % root EUID). Despertadores: kalm-gpu 2 s · kalm-lite 10 s · kalmd 15 s · autopilot 2 min · sysstat 10 min.
   - **RAM**: ChatGPT 2.474 MB · openclaw 574 MB · nobara-sync 452 MB · open-webui 420 MB · plasmashell 396 MB · kwin 234 MB · packagekitd 215 MB · dnf-app-center 290 MB (desactivado).
   - **I/O/HDD**: sda 35–93 % util; ~161 MB/60 s escritos (root services: journald/docker/btrfs); IRQ ahci ~83/s.
   - **GPU**: Intel HD 4600 activa (composición, 61 IRQ/s) · RX 550 ociosa (34 °C, sin IRQ).
   - **Red**: FCM/Cloudflare persistentes (ChatGPT/opencode) · listeners 0.0.0.0:8080/11434 · KDE Connect UDP · LLMNR 5355.

**DETENERSE** — no se inicia Set H, no se hace commit. Decisión de desactivación (si procede) queda exclusivamente en manos del usuario, con los comandos de §13.3 como documentación únicamente.
