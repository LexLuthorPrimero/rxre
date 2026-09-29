# AUDITORÍA DE ACTUALIZACIONES AUTOMÁTICAS

> **Sistema**: Nobara Linux 44 (KDE Plasma Desktop Edition) — `ID=nobara`, `VERSION_ID=44`, `PLATFORM_ID=platform:f44`
> **Hostname**: `lex-luthor`
> **Fecha de auditoría**: 2026-09-23
> **Modo**: **READ-ONLY ESTRICTO** — no se desactivó, detuvo, enmascaró ni modificó ningún servicio, timer, archivo de configuración, repositorio, PackageKit, DNF/DNF5, KDE Discover ni mecanismo de Nobara. Tampoco se ejecutó `sudo`, `dnf install/update`, ni ninguna transacción de paquete.
> **Único archivo creado**: este informe. Necesario para la evidencia: snapshots read-only en `/tmp/opencode/` (fuera del proyecto).

---

## 1. Metodología

1. **Evidencia local primero** (estado de unidades systemd, timers, configuración, código fuente de paquetes, journal, historial dnf5).
2. Si un punto no era determinable localmente → documentación oficial/primaria. No se asumió ni inventó nada.
3. Clasificación explícita por mecanismo:
   - **A)** actualiza metadatos/caché de repositorios;
   - **B)** descarga paquetes;
   - **C)** comprueba actualizaciones / notifica;
   - **D)** instala actualizaciones automáticamente (sin confirmación del usuario).
4. Verificación final de integridad: snapshots comparativos (timers, unidad-files, hash de configs) tomados **antes** y **después** de redactar este informe + `git status`.

**Comandos de consulta utilizados (todos read-only)**: `cat /etc/os-release`, `systemctl list-timers --all`, `systemctl list-unit-files`, `systemctl is-enabled/is-active`, `systemctl cat <unidad>`, `journalctl -u <unidad>`, `rpm -qa | grep`, `rpm -ql <paquete>`, `cat /etc/dnf/dnf.conf`, `cat /etc/PackageKit/PackageKit.conf`, `cat /etc/fwupd/remotes.d/lvfs.conf`, `dnf5 history list`, `ps -eo pid,user,args`, lectura de código fuente Python instalado (`/usr/lib/python3.14/site-packages/appcenter/`), `crontab -l`, `ls /etc/cron.*`, `file /usr/bin/nobara-*`.

---

## 2. Resumen ejecutivo

| Mecanismo | Unidad / disparador | Estado | Clase | ¿Instala sin confirmación? |
|---|---|---|---|---|
| dnf5 makecache | `dnf-makecache.timer` → `dnf-makecache.service` (`dnf5 makecache`) | **ACTIVO** (enabled+active) | **A** (metadatos) | NO (nunca instala) |
| PackageKit daemon | `packagekit.service` (activación D-Bus) | Pasivo bajo demanda | A/C (si un cliente lo pide), D solo con petición+polkit | NO |
| DNF App Center Updater (bandeja) | autostart de sesión `org.dnf.AppCenter.Updater.desktop` → `dnf-app-center-updater` | Proceso activo (PID 6634) pero **desactivado por config de usuario** (`enabled: false`) | C (notificación) + A (refresco al comprobar) — hoy **inerte** | NO (instalar exige abrir la GUI y confirmar) |
| KDE Discover | Aplicación; sin daemon/timer | No se auto-ejecuta; solo al abrirlo | C (comprobación al abrir) | NO |
| Nobara `nobara-updater` / `nobara-sync` | Manual (sin unit, timer ni cron) | Herramienta manual GUI/TUI | D solo por invocación del usuario | NO |
| fwupd (firmware) | `fwupd.service` (D-Bus bajo demanda); `fwupd-refresh.timer` | **Timer DISABLED**; daemon parado | A/C solo bajo demanda manual; D nunca automático | NO |
| dnf-automatic / dnf5-automatic | — | **NO INSTALADO** | — | — |
| systemd-sysupdate | `systemd-sysupdate.timer/.service` | **DISABLED** (sin configs) | — | — |
| podman-auto-update | `.timer/.service` | **DISABLED** | — | — |
| dnf-system-upgrade / dnf5-offline-transaction | `.service` | **DISABLED** | — | — |
| flatpak auto-update | `flatpak-update.*` | **NO INSTALADO** (sin timers system ni user) | — | — |

**Conclusión principal**: **no existe en este sistema ningún mecanismo activo capaz de instalar paquetes ni actualizaciones sin intervención explícita del usuario (clase D).** Lo único periódico y activo es el refresco de **metadatos** (`dnf-makecache.timer`). El único comprobador/notificador de actualizaciones (App Center Updater) está corriendo pero fue **desactivado por el propio usuario** en `~/.config/dnf-app-center/updater.json` (`enabled: false`, `notifications: false`).

---

## 3. Inventario detallado por mecanismo

Para cada mecanismo: nombre, unidad, estado, enabled/disabled, quién lo inicia, qué hace realmente, descarga solo, actualiza metadatos, puede instalar paquetes, instala sin confirmación, config, dependencias, evidencia exacta, nivel de certeza.

---

### 3.1 dnf5 makecache — `dnf-makecache.timer` → `dnf-makecache.service`

- **Nombre**: dnf5 makecache (refresco de caché de metadatos de repositorios).
- **Unidades**: `dnf-makecache.service` (static) y `dnf-makecache.timer` (**enabled, active**). `dnf5-makecache.service` y `dnf5-makecache.timer` son **alias** (misma unidad).
- **Estado actual**: timer `active`; la service es `oneshot` (inactiva entre ejecuciones).
- **Quién lo inicia**: systemd (`timers.target`). Reglas del timer: `OnBootSec=10min`, `OnUnitInactiveSec=3h`, `RandomizedDelaySec=60m`; condiciones `ConditionPathExists=!/run/ostree-booted` y `ConditionACPower=true` (solo con alimentación).
- **Qué hace realmente**: `ExecStart=/usr/bin/dnf5 makecache` → descarga/actualiza **solamente los metadatos** de los repos y genera la caché local. No descarga binarios de paquetes.
- **¿Solo descarga?**: NO — no descarga paquetes; solo metadatos.
- **¿Actualiza metadatos?**: **SÍ** (clase A).
- **¿Puede instalar paquetes?**: **NO**.
- **¿Instala sin confirmación?**: NO (no instala nunca).
- **Config**: `/etc/dnf/dnf.conf` (solo `[main]` sin opciones → defaults); repos en `/etc/yum.repos.d/` (`nobara.repo`, `terra.repo`, etc.).
- **Dependencias**: `dnf5`, `network-online.target`.
- **Evidencia exacta**:
  - `systemctl cat dnf-makecache.service` → `ExecStart=/usr/bin/dnf5 makecache`; `ConditionACPower=true`.
  - `systemctl cat dnf-makecache.timer` → `OnBootSec=10min`, `OnUnitInactiveSec=3h`, `RandomizedDelaySec=60m`.
  - `journalctl -u dnf-makecache` (boot 2026-09-23): `Starting dnf-makecache.service - dnf5 makecache...` → `Metadata cache created` → `Finished`. Sin descargas de paquetes.
  - `systemctl list-timers --all`: `dnf-makecache.timer` activo (última ejecución 08:22, próxima 11:54).
- **Nivel de certeza**: **Alta** (evidencia directa de unidad + journal).

---

### 3.2 PackageKit daemon — `packagekit.service`

- **Nombre**: PackageKit (daemon de gestión de paquetes del sistema).
- **Unidades**: `packagekit.service` (estado **static** = no se auto-arranca al boot; se lanza por **activación D-Bus** bajo demanda). No hay timer asociado.
- **Estado actual**: pasivo; `is-active` alterna según haya clientes conectados (se observó `inactive` y luego `active` durante la auditoría, a demanda).
- **Quién lo inicia**: un cliente D-Bus (p. ej. KDE Discover, App Center, utilidades `pkcon`) que invoca el servicio `org.freedesktop.PackageKit`. `ExecStart=/usr/libexec/packagekitd`.
- **Qué hace realmente**: daemon que, **a petición de un cliente**, puede refrescar metadatos, comprobar actualizaciones, descargar o instalar paquetes. No ejecuta nada por sí solo; no hay ninguna unidad periódica que lo despierte.
- **¿Solo descarga?**: solo si un cliente lo pide explícitamente.
- **¿Actualiza metadatos?**: a petición de cliente (p. ej. App Center/Discover al comprobar). No hay refresco automático propio configurado.
- **¿Puede instalar paquetes?**: sí, como API — pero **solo** si un cliente lo solicita y el flujo de autorización (polkit) lo permite. En este sistema **ningún agente lo hace periódicamente**.
- **¿Instala sin confirmación?**: **NO** — requeriría una petición explícita de un cliente con privilegios; no existe tal cliente/agente.
- **Config**: `/etc/PackageKit/PackageKit.conf` — no contiene ninguna opción de instalación automática (todas comentadas; sin `UpdateMetadata` modificado, sin políticas).
- **Dependencias**: `packagekit`, libdnf5 backend.
- **Evidencia exacta**:
  - `systemctl is-enabled packagekit` → `static`; `systemctl cat packagekit.service` → `ExecStart=/usr/libexec/packagekitd`.
  - `journalctl -u packagekit` (2026-09-23): `Starting packagekit.service...` → `daemon start` → `Deactivated successfully` (arranque bajo demanda, apagado al dejar de usarse).
  - `cat /etc/PackageKit/PackageKit.conf` → sin directivas de auto-instalación.
- **Nivel de certeza**: **Alta** para la afirmación de que no instala nada por sí mismo (no hay disparador periódico ni agente solicitante); el resto es comportamiento estándar del daemon.

---

### 3.3 DNF App Center Updater (bandeja del sistema) — `org.dnf.AppCenter.Updater`

- **Nombre**: "Actualizador del Centro de Aplicaciones DNF" (`dnf-app-center-updater`, paquete `dnf-app-center-0.1.7`).
- **Unidad / disparador**: autostart de sesión gráfica vía `/etc/xdg/autostart/org.dnf.AppCenter.Updater.desktop` (comentario oficial: “Checks for package updates and shows a tray icon when updates are available”). En el ámbito de usuario se genera `app-org.dnf.AppCenter.Updater@autostart.service` (state `generated`).
- **Estado actual**: **proceso activo** (`/usr/bin/dnf-app-center-updater`, PID 6634, usuario `lucas`) **pero desactivado por configuración del usuario**.
- **Config de usuario** (`~/.config/dnf-app-center/updater.json`, modificado hoy 2026-09-23 09:03):
  ```json
  {
    "enabled": false,
    "interval_unit": "weeks",
    "interval_value": 999,
    "notifications": false,
    "update_feed_url": "https://updates.nobaraproject.org/updates.txt",
    "update_flatpaks": false
  }
  ```
  - `enabled: false` → según el código (`schedule()` en `updater_service.py`), la bandeja **no comprueba actualizaciones en intervalo** (muestra 0 actualizaciones y queda inerte).
  - `notifications: false` → no emite notificaciones.
  - `interval_value: 999` semanas → intervalo efectivamente nunca.
- **Qué hace realmente (por diseño)**: icono de bandeja; si estuviera activado, comprobaría actualizaciones cada 12 h (default; código `updater_config.py`) usando `dnfdaemon` (`get_upgradable_packages()`), refrescaría metadatos al comprobar y notificaría. El ítem de menú **"Update System"** solo **abre la GUI de App Center** (`_spawn_app("--update")`); **la instalación siempre la confirma el usuario en la GUI**.
- **¿Solo descarga / instala?**: NO — nunca descarga ni instala nada por sí mismo. Instalación = acción del usuario en App Center.
- **¿Actualiza metadatos?**: sí, cuando comprueba (clase A); hoy desactivado.
- **¿Notifica?**: por diseño sí (clase C); hoy `notifications: false`.
- **Dependencias**: `dnf-app-center`, `dnfdaemon` (libdnf5), GTK/Ayatana (indicador).
- **Evidencia exacta**:
  - `ps -eo pid,user,args | grep dnf-app-center-updater` → PID 6634 activo.
  - `cat ~/.config/dnf-app-center/updater.json` → `enabled: false` (ver arriba).
  - Código fuente instalado: `updater_service.py` (línea 181: `if not settings.get("enabled", True): ... return True`; menú `_spawn_app("--update")`).
  - Desktop file `/etc/xdg/autostart/...` con `Exec=dnf-app-center-updater`.
- **Nivel de certeza**: **Alta** (config real + proceso + código fuente del paquete).

---

### 3.4 DNF5 / DNF (gestor de paquetes)

- **Paquetes**: `dnf5-5.4.3.0`, `dnf-plugins-core`, `dnfdaemon`, `libdnf5-plugin-appstream`.
- **Config**: `/etc/dnf/dnf.conf` = vacío de opciones (solo `[main]`); sin `/etc/dnf/automatic.conf`.
- **dnf-automatic / dnf5-automatic**: **NO instalados, no existen unidades** (`systemctl is-enabled dnf-automatic.timer` → `not-found`). Esto elimina el mecanismo canónico de instalación automática en serie Fedora.
- **Timers propios**: únicamente `dnf-makecache.timer` (metadatos, ver 3.1).
- **Servicios deshabilitados**: `dnf-system-upgrade.service`, `dnf5-offline-transaction.service` (ambos `disabled`) — no se prepara ningún "offline upgrade" automático.
- **Historial (`dnf5 history list`)**: todas las transacciones visibles son **comandos manuales del usuario**: `dnf install/remove/swap`, `dnf distro-sync --refresh` (16/9), y `nobara-updater grouped update: ...` (16/9 y 23/9 12:17). No aparece ninguna transacción iniciada por timer/servicio. **Evidencia directa de que ningún mecanismo automático ha instalado paquetes.**
- **Nivel de certeza**: **Alta**.

---

### 3.5 KDE Discover — `plasma-discover` 6.7.4

- **Unidades**: ninguna. No hay servicio, daemon ni timer de Discover; no se encontró servicio D-Bus `org.kde.discover.notifier` (`ls /usr/share/dbus-1/services/` → sin coincidencias).
- **Quién lo inicia**: el usuario (aplicación; `.desktop` de aplicaciones `org.kde.discover.desktop`, `kcm_updates.desktop` = módulo de configuración).
- **Qué hace realmente**: frontend de PackageKit/Flatpak/AppStream. Comprueba actualizaciones cuando se abre; toda instalación/actualización requiere confirmación del usuario.
- **¿Instala sin confirmación?**: **NO**.
- **Config**: `~/.config/discoverrc` → solo `[FlatpakSources] Sources=flathub-beta`. Sin opciones de instalación automática.
- **Dependencias**: PackageKit, flatpak.
- **Evidencia exacta**: `rpm -qa | grep discover` → `plasma-discover-6.7.4-...`; `rpm -ql plasma-discover` → solo `/usr/bin/plasma-discover` y `.desktop` (sin binario notificador propio en este paquete); `cat ~/.config/discoverrc`.
- **Nivel de certeza**: **Alta** (local) para ausencia de mecanismo automático; comportamiento "requiere confirmación" documentado (KDE Discover).

---

### 3.6 Nobara — `nobara-updater` / `nobara-sync`

- **Paquetes**: `nobara-updater-2.0.1-44` (provee `/usr/bin/nobara-updater` y el symlink `/usr/bin/nobara-sync`; también `nobara-codec-wizard`). Otros: `nobara-kernel-manager`, `nobara-driver-manager`, `pbcli-nobara`, `nobara-login*`.
- **Unidades**: **ninguna**. `ls /usr/lib/systemd/system /etc/systemd/system | grep nobara` solo muestra `nobara-automount@.service` (**disabled**, para montar unidades al conectar — no relacionado con actualizaciones). `grep -ril 'nobara-updater|nobara-sync' /usr/lib/systemd/system /etc/systemd/system /etc/cron*` → **sin resultados**.
- **Quién lo inicia**: exclusivamente el usuario (GUI/TUI manual, o terminal).
- **Qué hace realmente**: guion Python/Gtk (código leído en `/usr/bin/nobara-updater`): ejecuta **"grouped updates"** de paquetes RPM (grupos Kernel/Desktop/Graphics/System) con validación de módulos de kernel, más actualización de Flatpaks (`install_system_flatpak_updates`, `run_as_user` para user flatpaks). Sincroniza repos Nobara. Solo actúa al ser invocado.
- **¿Instala sin confirmación?**: **NO** — por definición es una herramienta manual; no hay disparador periódico.
- **Config**: `/etc/nobara/` (trackers como `newinstall`), `/etc/yum.repos.d/nobara.repo`, `nobara-kernel-mainline.repo`.
- **Evidencia exacta**:
  - `file /usr/bin/nobara-updater` → Python script; `nobara-sync` → symlink.
  - Historial dnf5: `nobara-updater grouped update: Kernel...` (23/9 12:17), `Desktop/System/Graphics` (16/9) → invocaciones manuales.
  - Ausencia de units/cron (ver arriba).
- **Nivel de certeza**: **Alta**.

---

### 3.7 Firmware — `fwupd` / `fwupdmgr` 2.1.7

- **Unidades**: `fwupd.service` (static; **inactive**, activación D-Bus bajo demanda), `fwupd-refresh.service` (static), **`fwupd-refresh.timer` → DISABLED**.
- **Estado actual**: daemon parado (journal: "Stopping fwupd.service" 07:51 de hoy); timer de refresco deshabilitado → **no hay refresco automático de metadatos de firmware**.
- **Remote configurado**: `/etc/fwupd/remotes.d/lvfs.conf` → `Enabled=true` (LVFS estable), `AutomaticReports=false`, `AutomaticSecurityReports=false`, `ApprovalRequired=false`. El remote **existe pero no se refresca automáticamente** (timer off).
- **Qué hace realmente**: detecta dispositivos y prepara actualizaciones de firmware **solo cuando el usuario invoca** `fwupdmgr` o una GUI (p. ej. Discover). Instalación efectiva de firmware (incl. cápsulas UEFI) requiere acción y confirmación explícita del usuario (y para algunas, un reinicio interactivo y desbloqueo).
- **Distinción**: detección/preparación = bajo demanda manual; **instalación efectiva = siempre manual**. No hay mecanismo automático activo.
- **Config**: `/etc/fwupd/fwupd.conf` (51 bytes, `640 root:root`, sin opciones); `/etc/fwupd/remotes.d/`.
- **Evidencia exacta**:
  - `systemctl list-unit-files | grep fwupd` → `fwupd-refresh.timer disabled`; `fwupd.service static`.
  - `journalctl -u fwupd` → inicio/parada bajo demanda hoy (07:50–07:51).
  - `cat /etc/fwupd/remotes.d/lvfs.conf` → `Enabled=true`, reports automáticos en `false`.
  - `journalctl -u fwupd-refresh` → **"No entries"** (nunca se ha ejecutado).
- **Nivel de certeza**: **Alta**.

---

### 3.8 Otros mecanismos posibles (búsqueda exhaustiva)

| Mecanismo | Resultado |
|---|---|
| `systemd-sysupdate` | `.service` `indirect`, `.timer` **disabled**; sin directorios `/usr/lib/sysupdate.d` ni `/etc/sysupdate.d` → **inoperante** |
| `podman-auto-update` | `.timer`/`.service` **disabled** (sin contenedores) |
| `systemd-boot-update.service` | **disabled** |
| `flatpak` auto-update | Sin `flatpak-update.timer/service` (system ni `--user`); único servicio flatpak `flatpak-add-fedora-repos.service` = **oneshot del primer arranque** (añade flathub; no periódico, ya completado). Sin timers de usuario flatpak |
| `snap` / `snapd` | **NO instalado** |
| `unattended-upgrades` | **NO aplica** (no instalado; mecanismo Debian/Ubuntu) |
| Cron del sistema | `/etc/cron.d/0hourly`, `/etc/cron.hourly/0anacron` (anacron estándar), `/etc/cron.daily/brave-browser` (solo crea config del repo de Brave; actualizaciones del navegador Brave, no del sistema) |
| Cron de usuario `lucas` | Solo `trading-sim/auto_signal.sh` (simulación de trading, cada hora) — **sin relación con paquetes ni actualizaciones** |
| `at` | Sin trabajos pendientes |
| Autostart de sesión | `/etc/xdg/autostart/`: `nobara-firstrun.desktop`, `nobara-welcome-autostart.desktop` (primera configuración/bienvenida, no actualizaciones), `org.dnf.AppCenter.Updater.desktop` (ver 3.3). `~/.config/autostart/` usuario: **vacío** |

- **Nivel de certeza**: **Alta** (todas las comprobaciones locales del inventario).

---

## 4. Clasificación A / B / C / D por mecanismo

| Mecanismo | A metadatos | B descarga pkg | C comprueba/notifica | D instala autom. |
|---|---|---|---|---|
| `dnf-makecache.timer` (dnf5 makecache) | ✅ **activo** | ❌ | ❌ | ❌ |
| PackageKit daemon | ✅ (a demanda de cliente) | ✅ (solo a demanda de cliente) | ✅ (a demanda) | ❌ sin agente solicitante |
| DNF App Center Updater | ✅ (al comprobar; hoy **off** por config) | ❌ | ✅ (por diseño; hoy **off**) | ❌ |
| KDE Discover | ✅ (al abrirlo, vía PackageKit) | ✅ (tras confirmar) | ✅ | ❌ |
| `nobara-updater` / `nobara-sync` | ✅ | ✅ | ✅ | ❌ (manual) |
| fwupd / fwupd-refresh | ❌ (timer **disabled**) | ❌ | ✅ manual | ❌ |
| dnf-automatic, sysupdate, podman-auto-update, dnf-system-upgrade, offline-transaction | — | — | — | **no instalados/disabled** |

---

## 5. Secciones finales obligatorias

### 5.1 Mecanismos actualmente activos

1. **`dnf-makecache.timer`** → `dnf5 makecache` — refresca metadatos de repos cada ~3 h (activo; clase A). **No toca paquetes.**
2. **`packagekit.service`** — daemon bajo demanda D-Bus (pasivo; no hace nada sin un cliente).
3. **DNF App Center Updater (bandeja)** — proceso activo pero **desactivado por el usuario** (`enabled: false`, `notifications: false`) → inerte; sin comprobaciones ni notificaciones.
4. **`flatpak-add-fedora-repos.service`** — oneshot ya completado (añade flathub); no periódico.

Ninguno de los anteriores **instala** nada. **No existe ningún mecanismo de instalación automática activo (clase D).**

### 5.2 Mecanismos capaces de instalar actualizaciones automáticamente

**NINGUNO.** Verificaciones que lo sustentan:
- `dnf-automatic`/`dnf5-automatic`: no instalados.
- `systemd-sysupdate`, `podman-auto-update`, `dnf-system-upgrade`, `dnf5-offline-transaction`, `systemd-boot-update`: deshabilitados o sin configuración.
- `fwupd-refresh.timer`: deshabilitado.
- Ningún timer de usuario flatpak; sin services/timers Nobara de actualización.
- Historial dnf5: 100 % transacciones manuales.

### 5.3 Mecanismos que solo actualizan metadatos/caché

- `dnf-makecache.timer` → `dnf5 makecache` (**único activo**).
- `fwupd-refresh.service` (**deshabilitado**; refrescaría metadatos LVFS si el timer estuviera activo).
- PackageKit y App Center Updater: refrescan metadatos solo como parte de una comprobación solicitada por un cliente.

### 5.4 Mecanismos que solo notifican

- DNF App Center Updater (bandeja): por diseño notifica cuando hay actualizaciones; hoy **off** (`notifications: false`).
- KDE Discover: muestra actualizaciones solo al abrirlo.
- Nobara Welcome / `updates.nobaraproject.org`: feed informativo web (no instala).

### 5.5 Qué habría que desactivar para impedir instalaciones automáticas

**Nada.** No existe ningún mecanismo de instalación automática (clase D) que desactivar. Las únicas acciones "automáticas" son de **metadatos** (`dnf-makecache.timer`) y de **notificación** (App Center tray, ya desactivado por el usuario). Si se quisiera un sistema 100 % silencioso (ni metadatos ni tray):
- `dnf-makecache.timer` (metadatos; opcional e innecesario para seguridad).
- DNF App Center Updater en autostart (ya funcionalmente desactivado vía `updater.json`; opcional retirar del arranque).

Ninguna de las dos desactivaciones es necesaria para evitar instalaciones: **no hay instalaciones automáticas posibles en el estado actual.**

### 5.6 Qué NO habría que desactivar

- **`packagekit.service`** y **`dnfdaemon.service`** — los usan KDE Discover y App Center para funcionar; no instalan por sí solos. Enmascararlos rompería la gestión manual de software.
- **`flatpak-add-fedora-repos.service`** — oneshot ya hecho; irrelevante.
- **`fwupd.service`** — si se desea poder actualizar firmware manualmente; no actúa solo.
- **KDE Discover / App Center** — gestión manual normal.
- **`nobara-updater` / `nobara-sync`** — herramienta manual oficial de Nobara.

### 5.7 Efectos secundarios previsibles de cada desactivación

| Desactivación | Efectos secundarios |
|---|---|
| `dnf-makecache.timer` | Metadatos de repos quedarán obsoletos; `dnf5 update`/`dnf check-update` serán lentos o requerirán `--refresh`; sin impacto en instalación. Sin riesgo de seguridad relevante |
| App Center tray autostart (mv del `.desktop`) | Desaparece el icono de bandeja y las notificaciones de actualizaciones; la GUI de App Center sigue funcionando manualmente |
| (hipotético, NO recomendado) `mask packagekit.service` | Discover y App Center dejan de poder comprobar/instalar paquetes (errores de backend); se pierde la gestión gráfica |
| (hipotético) `mask fwupd.service` | `fwupdmgr` y las actualizaciones de firmware de la GUI fallan; sin detección de firmware |

### 5.8 Cómo revertir cada cambio

| Cambio | Reversión |
|---|---|
| `systemctl disable --now dnf-makecache.timer` | `systemctl enable --now dnf-makecache.timer` |
| Renombrar/mover `org.dnf.AppCenter.Updater.desktop` fuera de autostart | Recuperar el `.desktop` a `/etc/xdg/autostart/` (o eliminar el symlink/mask de `~/.config/autostart/`) |
| `enable=false` en `~/.config/dnf-app-center/updater.json` | poner `"enabled": true` (y `"notifications": true`) |
| (no recomendado) `mask packagekit.service` | `systemctl unmask packagekit.service` |
| (no recomendado) `mask fwupd.service` | `systemctl unmask fwupd.service` |

### 5.9 Comandos exactos (SOLO DOCUMENTACIÓN — **NO EJECUTADOS**)

> Esta sección es documentación. Durante esta auditoría **no se ejecutó ningún** `disable`, `stop`, `mask`, ni se modificó configuración alguna.

```bash
# 1) Metadatos de repositorios (clase A; opcional, no impide instalación automática porque no la hay)
sudo systemctl disable --now dnf-makecache.timer
# Revertir:
sudo systemctl enable --now dnf-makecache.timer

# 2) Bandeja/notificador de App Center (autostart de sesión; ya desactivado funcionalmente por updater.json)
sudo mv /etc/xdg/autostart/org.dnf.AppCenter.Updater.desktop \
        /etc/xdg/autostart/org.dnf.AppCenter.Updater.desktop.disabled
# Revertir:
sudo mv /etc/xdg/autostart/org.dnf.AppCenter.Updater.desktop.disabled \
        /etc/xdg/autostart/org.dnf.AppCenter.Updater.desktop
# (Alternativa solo para el usuario, sin sudo:)
mkdir -p ~/.config/autostart && ln -s /dev/null ~/.config/autostart/org.dnf.AppCenter.Updater.desktop
rm ~/.config/autostart/org.dnf.AppCenter.Updater.desktop   # revertir

# 3) (NO recomendado — rompería Discover/App Center) PackageKit
# sudo systemctl mask packagekit.service
# sudo systemctl unmask packagekit.service               # revertir

# 4) (NO recomendado — quitaría firmware manual) fwupd — su timer de refresco ya está disabled:
sudo systemctl disable --now fwupd-refresh.timer          # ya está disabled; documentación
sudo systemctl enable --now fwupd-refresh.timer           # revertir
```

### 5.10 Mecanismos de actualización manual que seguirían funcionando

1. **Terminal (DNF5)** — `sudo dnf5 update` / `sudo dnf update`, `dnf5 check-update`, `dnf5 distro-sync`, `dnf5 remove/install`.
2. **App Center (GUI)** — `dnf-app-center` (incluso aunque se desactive la bandeja/notificador).
3. **Nobara Updater / nobara-sync** — `nobara-updater` (GUI/TUI oficial, grouped updates + flatpaks + validación de kernels).
4. **KDE Discover** — `plasma-discover` (comprobar/instalar con confirmación).
5. **Flatpak** — `flatpak update`, `flatpak update --user`.
6. **Firmware** — `fwupdmgr refresh` + `fwupdmgr update` (manual; el timer de refresco sigue deshabilitado).
7. **Upgrade de release mayor** — `dnf system-upgrade` (servicio auxiliar deshabilitado hasta que se invoque manualmente; tras la preparación, el usuario confirma el reinicio).

---

## 6. Verificación de integridad (sin cambios del sistema)

Comprobaciones realizadas por esta auditoría (todo read-only):

- **No se ejecutó** ningún `disable`, `stop`, `mask`, `daemon-reload`, ni se modificó ningún archivo de configuración, repo o servicio. No se usó `sudo` para escritura. Las únicas escrituras: los snapshots en `/tmp/opencode/` (fuera del proyecto) y este informe.
- **Snapshots comparativos** (`systemctl list-timers`, `systemctl list-unit-files` filtrado, hashes SHA256 de `/etc/dnf/dnf.conf`, `/etc/PackageKit/PackageKit.conf`, `/etc/fwupd/remotes.d/lvfs.conf`, `~/.config/discoverrc`): capturados **antes** de redactar el informe en `/tmp/opencode/baseline_*.txt|sha256`. Se re-comparan tras la redacción (paso siguiente de esta sesión).
- `fwupd.conf` no es legible por el usuario (`640 root:root`); su integridad se verifica por `stat` (tamaño/fecha) antes/después.
- **`git status` del proyecto**: sin nuevos cambios respecto a la fase anterior — se espera que el único archivo nuevo no rastreado (además de los 6 informes ya existentes) sea **este informe** (36 modificados + 7 untracked).

---

## 7. Niveles de certeza y limitaciones

- **Certeza Alta** en todos los mecanismos activos/inactivos (evidencia directa local: unidades, timers, configuración, código fuente del paquete, journal, historial dnf5).
- **No se pudo leer** `/etc/fwupd/fwupd.conf` (permisos `640 root:root`); se usó `stat` para su control de integridad. Es irrelevante para la conclusión: su timer de refresco está deshabilitado y el daemon solo actúa bajo demanda.
- El crontab de `lucas` contiene una tarea de simulación de trading (`auto_signal.sh`) verificada como **sin relación** con paquetes/actualizaciones.
- No se detectó ningún mecanismo de actualización de navegadores/distribuidos de terceros que opere a nivel de sistema salvo el daily de Brave (solo prepara el repo del navegador).
- Conclusión: **no hay vía automática de instalación de paquetes ni de firmware sin confirmación del usuario en el estado actual del sistema.**
