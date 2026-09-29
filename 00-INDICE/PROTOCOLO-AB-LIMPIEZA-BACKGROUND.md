# PROTOCOLO A/B — LIMPIEZA DE BACKGROUND (autopilot → kalmd)

- **Fecha de creación**: mié 2026-09-23 ~10:35 (-03)
- **Sistema**: Nobara 44 KDE Plasma 6 (Wayland) — `lex-luthor` · i7-4790 (4C/8T) · 12 GB RAM · HDD SAMSUNG HM500JI · Intel HD 4600 + RX 550
- **Estado**: PROTOCOLO SOLO + **PRECHECK READ-ONLY realizada el 2026-09-23 (~10:44)** — resultado en §1.4. **No se ha ejecutado ninguna desactivación, no se ha modificado el sistema.**
- **Objetivo**: medir el efecto real de eliminar la actividad de `system-autopilot.timer` (FASE A) y de `kalm.service`/kalmd (FASE B) en **reposo**, de forma **reversible**, probando **una sola unidad por fase** (nunca ambas simultáneamente en esta primera etapa).
- **Pendiente de decisión del usuario**: ejecutar el protocolo (este documento se audita y se aprueba antes de tocar nada).

---

## 1. Alcance y reglas de seguridad

### 1.1 Alcance (lo único que se podrá tocar en ejecución)
| # | Unidad / proceso | Fase | Acción permitida |
|---|---|---|---|
| 1 | `system-autopilot.timer` | A | `systemctl stop` / `systemctl start` (restauración) |
| 2 | `kalm.service` (kalmd, PID 4055) | B | `systemctl stop` / `systemctl start` (restauración) |

### 1.2 Fuera de alcance — NO TOCAR en ningún caso
- `kalm-gpu.service` (gobernador térmico RX550), `kalm-lite.service`, `mako.service`, `app-geoclue-demo-agent@autostart`, `drkonqi-sentry-postman.timer`.
- `nobara-sync` / `nobara-updater` (resuelto como legítimo; no es servicio).
- `kalm-cpu.service`: oneshot de arranque (`kalm-cpu-apply.sh`), **no periódico** — activo solo como estado `exited` (aplicado 08:21:27 en el boot). **NO se desactiva ni se reinicia en esta prueba**; solo se documenta (§4.3) porque sus pines de IRQ persisten y coinciden con los de kalmd.
- `sys-tuned.timer` y `irqbalance.service`: **se dejan funcionando** (son los "gestores residuales" cuyo comportamiento se observa durante la prueba).

### 1.3 Reglas
1. Una sola unidad desactivada por fase. Antes de FASE B, **verificar que autopilot volvió a funcionar** (≥2 ciclos OK).
2. Cualquier lectura es con herramientas ya instaladas (§2.1). No se instala nada.
3. Nunca se edita el contenido de las unidades ni de los scripts (integridad por `sha256sum`, §7).
4. `stop` manual es la intervención mínima y reversible. `disable` **solo como alternativa documentada** (§6.1 nota) porque toca symlinks — no es la vía primaria.
5. Ante cualquier criterio de abort (§9) → restauración inmediata con los comandos de §7.2.

### 1.4 Resultado de la PRECHECK READ-ONLY (2026-09-23 ~10:44) — relación timer → service

**1) Qué unidad dispara `system-autopilot.timer`**: `system-autopilot.service`. Evidencia: `systemctl status system-autopilot.timer` → `Triggers: ● system-autopilot.service`; `systemctl show -p Unit` → `system-autopilot.service` (mapeo implícito por mismo basename; el archivo del timer no tiene `Unit=` explícito). El timer NO tiene `Requires`/`PartOf` sobre el service → **unidades independientes**: parar una no afecta a la otra.

**2) ¿Existe `system-autopilot.service`?** Sí — `/etc/systemd/system/system-autopilot.service`, `Type=oneshot`, `ExecStart=/usr/local/bin/system-autopilot.sh`. **Sin sección [Install]** (por tanto `systemctl enable/disable` sobre él **falla**), pero **sí existe symlink manual** `/etc/systemd/system/multi-user.target.wants/system-autopilot.service` (creado 2026-05-07 11:50). → El service se ejecuta **1 vez al boot vía multi-user.target** además de cada 2 min vía timer.

**3) Estados actuales (PRECHECK)**:

| Unidad | is-enabled | is-active | Detalle |
|---|---|---|---|
| `system-autopilot.timer` | enabled | active (waiting) | cadencia `OnBootSec=2min` + `OnUnitActiveSec=2min`; symlink en `timers.target.wants/` |
| `system-autopilot.service` | enabled (symlink manual) | inactive | oneshot ~1 s/ciclo; `Result=success` siempre |

**4) ¿Instancia corriendo durante la PRECHECK?** **Sí se observó una**: PID 108389 con `[AUTO-PILOT] cycle complete` a las 10:41:45 (ciclo 10:41:44→10:41:45, <1 s). Terminó sola. Prueba directa de que **parar el timer NO detiene una ejecución ya iniciada** (la instancia en curso sigue hasta acabar).

**5) ¿`stop` del timer garantiza “sin nuevas ejecuciones”?** Sí **para este boot**: `systemctl stop system-autopilot.timer` cancela todos los futuros triggers del timer; una instancia ya iniciada la deja terminar. El único otro disparador del service es `multi-user.target` (boot) — irrelevante salvo que un reboot ocurriera a mitad de la prueba (no previsto).

**6) ¿Hay que detener también el service en FASE A?** **Sí, por rigor.** Se detienen **ambas** unidades: `systemctl stop system-autopilot.timer` (cancela triggers) + `systemctl stop system-autopilot.service` (no-op si está inactivo —lo normal entre ciclos—; SIGTERM a un run de ~1 s si hubiera uno en curso). Así se garantiza **cero ejecuciones** durante la ventana de medición.

**7) Restauración exacta de ambos (respuesta a la pregunta “cómo restaurar”)**: `systemctl start system-autopilot.timer` devuelve el timer a `active (waiting)` con cadencia (NEXT ≈ +2 min). El service **no requiere `start` manual**: el próximo trigger del timer lo relanza; su estado estable entre ciclos es `inactive`. Los symlinks de enable de ambos (timers.target.wants y multi-user.target.wants) **no se tocan con `stop`** → no hace falta ninguna acción de enable. Si (solo si) el symlink manual del service se removiera, se recrea con `ln -s /etc/systemd/system/system-autopilot.service /etc/systemd/system/multi-user.target.wants/` + `systemctl daemon-reload` (no se puede usar `systemctl enable` porque el unit carece de `[Install]`).

**Confirmación `kalm.service` → kalmd**: `Type=simple`, MainPID=4055, **cgroup `/system.slice/kalm.service` con exactamente 1 task** (único proceso; `ps | grep kalmd.py` = solo 4055), `KillMode=control-group`, `SendSIGKILL=yes`, `TimeoutStopUSec=45s`. → **`systemctl stop kalm.service` elimina de verdad el proceso periódico de kalmd** (SIGTERM a la cgroup; SIGKILL a los 45 s si no saliera; `Restart=always` no reactiva tras un stop manual). Symlink estándar: `multi-user.target.wants/kalm.service` (sí tiene `[Install]`).

---

## 2. Estado de referencia (capturado 2026-09-23, 10:31–10:32, PRE-prueba)

| Item | Valor verificado |
|---|---|
| `system-autopilot.timer` | `is-enabled=enabled` · `is-active=active` · `NEXT` → cada 2 min (próx. 10:32) · schedule `OnBootSec=2min` + `OnUnitActiveSec=2min` |
| `system-autopilot.service` | `Type=oneshot` → `/usr/local/bin/system-autopilot.sh` |
| `kalm.service` | `is-enabled=enabled` · `is-active=active` · MainPID=4055 · `ExecStart=python3 /opt/kalm/kalmd.py` · `Restart=always`/5s · `After=multi-user.target` |
| governor (8 núcleos) | `schedutil` en todos · `intel_cpufreq` · frec. instantáneas 3,59–3,86 GHz (alta tras la actualización dnf de la mañana) |
| IRQ affinities | 27(ahci)=3 · 28(xhci)=0 · 39(enp3s0)=`2-3,6-7` (0xcc, de autopilot) · 40(i915)=1 · 42(amdgpu)=1 |
| `irqbalance` | `active`, MainPID=979 (sin PIDFile → kalmd nunca lo detecta) |
| Temperaturas | CPU Package 38 °C / Core0 38 °C · RX550 (amdgpu edge) **35 °C** |
| Load / proc | loadavg 1,78/1,96/2,47 · 352 procesos · uptime 2 h 20 min |
| Journal | 193,3 MB · **3.891 líneas/30 min** → autopilot 676 (~23/min) + kalm “omitiendo” 840 (~28/min) + sesiones sudo 364 (~12/min) |
| Disco | `/dev/sda2` 83% usado (79 G libres) |

### 2.1 Herramientas de medición verificadas (instaladas, sin instalar nada)
`turbostat` ✓ · `mpstat` ✓ · `iostat` ✓ · `pidstat` ✓ · `sensors` ✓ · `sar` ✓ · `vmstat` ✓ · `powertop` ✓ · `smartctl` ✓ · `hddtemp` ✓
Todas las lecturas del protocolo corren sin root, salvo `turbostat`/`powertop` (opcionales, requieren `sudo -n`; verificar con `sudo -n true` en la fase de ejecución; si no, usar el fallback de §3.5).

### 2.2 Hashes de integridad (línea base reversibilidad)
```
sha256sum /etc/systemd/system/system-autopilot.service = 07dc247f…932d6
sha256sum /etc/systemd/system/system-autopilot.timer  = 16d21f1c…00e72a
sha256sum /etc/systemd/system/kalm.service            = 69cc9644…b18443
sha256sum /usr/local/bin/system-autopilot.sh          = 61519cfe…0fee3ea
sha256sum /opt/kalm/kalmd.py                          = 5e0a682c…753d7c4
```
Regla: mismo hash antes y después de cada fase, o se **aborta**.

---

## 3. FASE BASE — medición en reposo (20 min)

Condición: sesión de escritorio normal, sin uso manual, sin ventanas activas de trabajo. No iniciar downloads ni reproducción.

Duración total fija **T = 20 min**, muestreada con los comandos siguientes (todos en paralelo, en terminales/ficheros de `/tmp/opencode/ab_logs/`, ver §8.1). Anotar `T1=fecha inicio`, `T2=T1+20 min`.

### 3.1 CPU / frecuencias / governor / RAM / load
```bash
# CPU total y por núcleo (2 muestras/seg, ventana completa)
mpstat -P ALL 5 240      > /tmp/opencode/ab_logs/base_mpstat.txt

# governor + frecuencia por núcleo cada 30 s (ver FRECUENCIA DE CAMBIOS de governor)
for i in $(seq 1 40); do
  for c in /sys/devices/system/cpu/cpu[0-7]/cpufreq; do
    n=$(basename $(dirname "$c"))
    echo "$(date +%H:%M:%S) $n gov=$(cat $c/scaling_governor) freq=$(cat $c/scaling_cur_freq)"
  done
  sleep 30
done > /tmp/opencode/ab_logs/base_govfreq.txt

# RAM y load
free -m                                                  > /tmp/opencode/ab_logs/base_ram.txt
cat /proc/loadavg                                        >> /tmp/opencode/ab_logs/base_ram.txt
uptime                                                   >> /tmp/opencode/ab_logs/base_ram.txt
```

### 3.2 IRQ / wakeups (sin instalar herramientas)
```bash
# Interrumpciones por segundo + context switches (toda la ventana)
vmstat 5 240             > /tmp/opencode/ab_logs/base_vmstat.txt

# Deltas de /proc/interrupts por IRQ relevante (T1 vs T2)
cp /proc/interrupts                                     /tmp/opencode/ab_logs/base_irq_T1.txt
# ...al final: cp /proc/interrupts                     /tmp/opencode/ab_logs/base_irq_T2.txt
# Cálculo de deltas (ejecutar al cierre de fase):
awk 'NR==FNR{a[$1]=$0;next}{n=$1; sub(/:/,"",n);
  for(i=2;i<=NF-7;i++)cnt[i]+=$i-a[n]  }' base_irq_T1.txt base_irq_T2.txt > /tmp/null
# (script plano: para cada IRQ, Δ = T2-T1; prestar atención a: ahci[27], enp3s0[39], i915[40], amdgpu[42], xhci[28])
```
Opción root (si `sudo -n true` funciona; fallback = vmstat+interrupts):
```bash
sudo -n turbostat --quiet --show IRQ,POLL,CPU%c1,CPU%c6,CPU%c7,CoreTmp,PkgTmp sleep 120
```

### 3.3 HDD `/dev/sda` (util%, IOPS, latencia, lecturas/escrituras)
```bash
# util%, tps, r/s, w/s, await — 4 muestras de 5 s
iostat -x /dev/sda 5 4    > /tmp/opencode/ab_logs/base_iostat.txt

# Deltas de contadores reales de la ventana (comparables entre fases)
cat /proc/diskstats | grep ' sda '    > /tmp/opencode/ab_logs/base_disk_T1.txt
# ...al cierre de fase: cat /proc/diskstats | grep ' sda ' > base_disk_T2.txt
# → anotar Δ de: lecturas completadas (f1), sectores leídos (f3),
#   escrituras completadas (f5), sectores escritos (f7), tiempo en I/O (f10)
```
Referencia fase previa: ventana 60 s en reposo ≈ 161 MB escritos/60 s atribuibles a servicios root (journald/docker/btrfs).

### 3.4 Journal (volumen y desglose de escritores)
```bash
journalctl --disk-usage                                 > /tmp/opencode/ab_logs/base_journal_mb.txt
journalctl --since "$T1" --until "$T2" --no-pager | wc -l            >> base_journal_mb.txt
journalctl -u system-autopilot.service --since "$T1" --until "$T2" --no-pager | wc -l
journalctl -u system-autopilot.service --since "$T1" --until "$T2" --no-pager | grep -c 'cycle complete'
journalctl --since "$T1" --until "$T2" --no-pager | grep -c 'omitiendo'
journalctl --since "$T1" --until "$T2" --no-pager | grep -c 'sudo.*COMMAND'
```

### 3.5 Temperatura CPU y estado RX550
```bash
sensors | grep -E 'Package id 0|Core 0'          > /tmp/opencode/ab_logs/base_temp_cpu.txt
sensors amdgpu-pci-0100                          > /tmp/opencode/ab_logs/base_temp_rx550.txt
# RX550: + IRQ 42 deltas (§3.2) + runtime PM:
cat /sys/bus/pci/devices/0000:01:00.0/power/runtime_status      # esperado: "suspended" | "active"
cat /sys/bus/pci/devices/0000:01:00.0/power/control             # esperado: auto
# (verificar BDF con: lspci -nn | grep -i 1002)
```

### 3.6 irqbalance, afinidades, actividad de los dos servicios
```bash
systemctl is-active irqbalance; systemctl show irqbalance -p MainPID
for i in 27 28 39 40 42; do printf 'IRQ %s: ' $i; cat /proc/irq/$i/smp_affinity_list; done
pidstat -p 4055 10 120   > /tmp/opencode/ab_logs/base_kalmd_cpu.txt     # %CPU, RSS de kalmd
systemctl list-timers --all --no-pager | grep -E 'autopilot|sys-tuned'  # frecuencia autopilot
```

### 3.7 Resumen FASE BASE (plantilla de registro)
| Métrica | Valor T1 | Valor T2 | Δ (ventana 20 min) |
|---|---|---|---|
| líneas journal totales / ventana | | | |
| líneas “omitiendo” (kalmd) | | | |
| ciclos autopilot completos | | | |
| sesiones sudo | | | |
| IRQ Δ (27/39/40/42/28) | | | |
| sda util% · tps · await | | | |
| sda escrituras ventana (sectores) | | | |
| cambios de governor (núcleos) | | | |
| mem · loadavg | | | |
| temp CPU Cpk · RX550 edge | | | |
| afinidad IRQ 39 | | | |

---

## 4. Qué se desactiva y qué queda vigente (para interpretar los resultados)

### 4.1 FASE A — `system-autopilot` deja de hacer (por cada ciclo de 2 min que ya no ocurre)
1. **Governor CPU**: ya no oscila entre `schedutil` (load≤2,5) y `performance` (load>2,5) en los 8 núcleos.
2. **IRQ affinity**: ya no escribe la máscara `0xcc` (CPUs 2,3,6,7) en la IRQ 39 (enp3s0).
3. **Sysctls de red**: ya no re-afirma `default_qdisc=fq`, `tcp_congestion_control=bbr`, `tcp_fastopen=3`, `tcp_mtu_probing=1`, `netdev_max_backlog=5000`.
4. **Disco**: ya no re-escribe scheduler `mq-deadline` (sd*) ni `read_ahead_kb=256` en sda.
5. **Prioridades**: ya no hace `renice +5 firefox` / `renice -10 kwin_wayland`.

**Qué PERMANECE aplicado tras `stop` (el kernel no revierte escrituras runtime):**
- IRQ 39 → `2-3,6-7` sigue tal cual (hasta que `irqbalance` la reubique o se reinicie).
- Sysctls de red vigentes (vuelven a defaults de Fedora **solo tras reboot**: `fastopen=1`, `mtu_probing=0`, `backlog=1000`, `cubic`).
- `mq-deadline` + `read_ahead 256` (persisten hasta reboot o `sys-tuned`).
- `renice` aplicado a los pids vivos.

**Quién REVIERTE o cubre su papel (se deja funcionando a propósito):**
- `sys-tuned.timer` (cada 30 min): re-fija governor→`schedutil`, `read_ahead 128`, IRQ 39→`0x84` (CPUs 2,7), `swappiness=10`, fq/bbr. → **Durante FASE A el governor quedará estabilizado por sys-tuned**; los cambios de governor deberían caer a ~0 entre ejecuciones de sys-tuned.
- `irqbalance` (daemon, PID 979): seguirá balanceando afinidades del resto de IRQs. → La IRQ 39 podría moverse sola durante la prueba; anotarlo.

**Diferencia medible esperada en FASE A (objetiva)**: líneas journal de autopilot (≈676/30 min → 0), sesiones sudo (≈364/30 min → ~0), intentos de escritura en `/proc/irq/39` y `/sys/.../scaling_governor` (0), y wakeups asociados a esos spawns.

### 4.2 FASE B — `kalm.service` (kalmd) detenido
- **SIGTERM a kalmd (PID 4055)**. `Restart=always` **no** reactiva tras un `stop` manual (semántica de systemd: Restart no aplica a paradas ordenadas).
- **Qué queda vigente**: las afinidades ya escritas al boot — IRQ 27→3, 28→0, 40→1, 42→1 — permanecen fijadas en el kernel (`smp_affinity_list` no se revierte al detener el servicio).
- **`irqbalance` sigue funcionando normalmente** (activo, PID 979, sin PIDFile — como siempre) y mantiene su reparto en IRQ 16/18/23–26; no se interrumpe su gestión por detener kalmd.
- **Qué se elimina**: las ~840 líneas “omitiendo”/30 min (~28/min) y el poll de 15 s sobre sysfs. **Cero** otras consecuencias funcionales (kalmd no ajustaba nada efectivo fuera del boot since las escrituras ya estaban hechas).
- **Después de `start`**: kalmd vuelve a poll; solo re-escribe si la afinidad difiere del objetivo (si `irqbalance` movió algo mientras estuvo detenido, se verá un “IRQ → CPU” en el journal — señal útil de conflicto).

### 4.3 `kalm-cpu.service` (NO se toca — documentación)
Oneshot de boot `RemainAfterExit=true` → `/usr/local/bin/kalm-cpu-apply.sh`: fija `smp_affinity=1` (CPU0) a IRQ de i8042/xhci/usb/mouse/kbd y `smp_affinity=2` (CPU1) a IRQ drm/amdgpu/radeon. Se aplicó a las 08:21:27 (mismo instante que las escrituras iniciales de kalmd). Es responsable de los pines actuales 28→0, 40→1, 42→1. No es periódico ni daemon: **ninguna acción en esta prueba**.

---

## 5. FASE A — `system-autopilot.timer` (20–30 min de prueba)

### 5.1 Pre-check (estado antes)
```bash
systemctl is-enabled system-autopilot.timer    # esperado: enabled
systemctl is-active  system-autopilot.timer    # esperado: active
systemctl list-timers --all --no-pager | grep autopilot   # NEXT ≈ +2 min
sha256sum /etc/systemd/system/system-autopilot.{service,timer}   # = tabla §2.2
```

### 5.2 Desactivación (comando primario — mínima huella, no toca symlinks ni archivos)
```bash
systemctl stop system-autopilot.timer    # cancela futuros triggers (PRECHECK §1.4-5)
systemctl stop system-autopilot.service  # no-op si inactivo; corta un run en curso (<1 s) — PRECHECK §1.4-6
```
> **Corrección derivada de la PRECHECK (§1.4)**: el service es oneshot e independiente del timer (sin `Requires/PartOf`), y durante la pre-check se observó una instancia activa (PID 108389). Parar **únicamente el timer** no detendría un run ya iniciado ni garantizaría cero ejecuciones en la ventana. Por eso en FASE A se detienen **ambas unidades**. Ninguna recibe `disable`: los symlinks de enable no se tocan.
>
> **Alternativa documentada (NO primaria, toca symlinks, solo aplica al timer)**: `systemctl disable --now system-autopilot.timer` — restauración `systemctl enable --now system-autopilot.timer`. **El service no admite `enable`/`disable` vía systemctl** (no tiene `[Install]`; su symlink en `multi-user.target.wants/` es manual — ver §1.4-7). Para la A/B se recomienda `stop`.

### 5.3 Post-check (estado después)
```bash
systemctl is-active  system-autopilot.timer    # esperado: inactive
systemctl is-enabled system-autopilot.timer    # esperado: enabled (sin cambios)
systemctl list-timers --all --no-pager | grep autopilot   # esperado: sin fila
systemctl is-active system-autopilot.service   # esperado: inactive (sin instancia en curso)
pgrep -af system-autopilot.sh                  # esperado: vacío (cero runs activos)
sha256sum /etc/systemd/system/system-autopilot.{service,timer}   # idénticos
```

### 5.4 Medición DURANTE la prueba (misma batería que FASE BASE, misma duración 20 min)
Ejecutar §3.1–§3.6 con salidas `faseA_*.txt`. Registrar en §3.7 renovado. Señal clave: en 20 min no debe aparecer **ningún** `[AUTO-PILOT]` ni ciclo, y las sesiones sudo deben caer a ~0.

### 5.5 Restauración exacta
```bash
systemctl start system-autopilot.timer
systemctl is-active  system-autopilot.timer    # esperado: active
systemctl list-timers --all --no-pager | grep autopilot   # NEXT ≈ +2 min
# Verificar que el 1er ciclo vuelve a ejecutarse (≤ 2-4 min después):
journalctl -u system-autopilot.service --since -5min --no-pager | grep 'cycle complete'
# Verificar governor re-aseseverado y afinidad IRQ 39:
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /proc/irq/39/smp_affinity
sha256sum /etc/systemd/system/system-autopilot.{service,timer}
```
> **El service NO requiere `start` manual** para restaurar: el próximo trigger del timer lo relanza (su estado estable entre ciclos es `inactive`; el `stop` del service anterior no impide el próximo ciclo). Opcional (no recomendado en la prueba): `systemctl start system-autopilot.service` ejecuta de inmediato un ciclo tipo “boot” — añadiría una ejecución extra fuera de cadencia; prescindir.

---

## 6. FASE B — `kalm.service` (20–30 min de prueba)

### 6.1 Pre-check
```bash
systemctl is-enabled kalm.service     # esperado: enabled
systemctl is-active  kalm.service     # esperado: active
systemctl show kalm.service -p MainPID # esperado: 4055
ps -p 4055 -o pid,rss,stat,etime
sha256sum /etc/systemd/system/kalm.service /opt/kalm/kalmd.py
```

### 6.2 Desactivación
```bash
systemctl stop kalm.service
```
(equivale a SIGTERM a PID 4055; `Restart=always` no actúa tras stop manual)

### 6.3 Post-check
```bash
systemctl is-active kalm.service       # esperado: inactive
systemctl is-enabled kalm.service      # esperado: enabled
ps -p 4055 -o pid,stat                 # esperado: vacío (proceso terminado)
systemctl is-active irqbalance         # esperado: active (sigue funcionando)
journalctl --since -3min --no-pager | grep -c 'omitiendo'   # esperado: se congela
sha256sum /etc/systemd/system/kalm.service /opt/kalm/kalmd.py
```

### 6.4 Medición DURANTE la prueba (repetir FASE BASE, salidas `faseB_*.txt`; 20 min)
Señal clave: 0 líneas “omitiendo”; afinidades 27/28/40/42 intactas; sin impacto en irqbalance ni en IRQ 42 (amdgpu).

### 6.5 Restauración exacta
```bash
systemctl start kalm.service
systemctl is-active kalm.service        # esperado: active
systemctl show kalm.service -p MainPID  # nuevo PID
ps -p <nuevoPID> -o pid,rss,stat
# kalmd retoma el poll; a los 15 s vuelve el journal “omitiendo” (verificar conteo):
journalctl --since -1min --no-pager | grep -c 'omitiendo'
sha256sum /etc/systemd/system/kalm.service /opt/kalm/kalmd.py
```

---

## 7. Reversibilidad y registro previo a la ejecución

### 7.1 Registro previo obligatorio (a completar justo antes de CADA fase)
| Campo | FASE A (autopilot) | FASE B (kalm) |
|---|---|---|
| `is-enabled` antes | enabled (timer) | enabled |
| `is-active` antes | active (timer) | active (service) |
| Estado del service (A) | service `enabled` (symlink manual) / `inactive` entre ciclos — §1.4-3 | — |
| Timer schedule | OnBootSec=2min + OnUnitActiveSec=2min | — (daemon continuo) |
| PID (si aplica) | — (oneshot; verificar `pgrep system-autopilot.sh` vacío) | 4055 (cgroup 1 task) |
| Symlinks habilitadores | timers.target.wants/**timer** + multi-user.target.wants/**service** (manual; NO se tocan con `stop`) | multi-user.target.wants/`kalm.service` |
| Otro disparador del service (A) | **1 ejecución al boot vía multi-user.target** además del timer | — (daemon continuo) |
| Archivos/unidades | service+timer+script (§2.2) | service+script (§2.2) |
| Hashes (sha256) | idénticos a §2.2 | idénticos a §2.2 |
| Fecha/hora | TBD | TBD |

### 7.2 Comandos de restauración (exactos y en orden)
| Situación | Comando |
|---|---|
| Restaurar autopilot tras `stop` (FASE A) | `systemctl start system-autopilot.timer` — el service se relanza solo con el próximo trigger; **sin** `start` manual (§1.4-7, §5.5) |
| Restaurar autopilot si se usó `disable --now` (timer) | `systemctl enable --now system-autopilot.timer` — recrea `timers.target.wants/` |
| Recrear el symlink MANUAL del service si se removiera | `ln -s /etc/systemd/system/system-autopilot.service /etc/systemd/system/multi-user.target.wants/` + `systemctl daemon-reload` (el unit no tiene `[Install]`; `systemctl enable` falla) |
| Restaurar kalm tras `stop` | `systemctl start kalm.service` |
| Restaurar kalm si se usó `disable --now` | `systemctl enable kalm.service` (recrea multi-user.target.wants/kalm.service) |
| **Abortar y restaurar TODO (emergencia)** | `systemctl start system-autopilot.timer kalm.service` (el service autopilot se relanza con el próximo trigger del timer) |

Garantía de reversibilidad: `stop` no modifica ni el contenido de las unidades ni Symlinks de enable; `start` devuelve el mismo estado `active/enabled` y (autopilot) la cadencia de 2 min; kalmd vuelve a poll con las mismas afinidades ya aplicadas.

---

## 8. Métricas y registro de la prueba

### 8.1 Organización
- Carpeta de logs: `/tmp/opencode/ab_logs/` (volátil; al finalizar, copiar las tablas resumidas AL INFORME, §11).
- Nombrar: `base_*`, `faseA_*`, `faseB_*`, cada fase con su `T1`/`T2`.

### 8.2 Métricas comparadas entre fases (tabla maestra para el informe final)
| Métrica | BASE | FASE A (Δ vs base) | FASE B (Δ vs base) | Señal de mejora |
|---|---|---|---|---|
| IRQ/s + ctxt/s (vmstat) | | | | ↓ |
| Δ IRQ (27,39,40,42,28) | | | | ↓ |
| %CPU total (mpstat idle) | | | | ↑ idle |
| Cambios de governor (por núcleo) | | | | ↓ (A) |
| sda util% / tps / await | | | | ↓ |
| Escrituras sda en ventana (sectores) | | | | ↓ |
| líneas journal/ventana | | | | ↓ |
| sesiones sudo / “omitiendo” | | | | ↓ |
| temp CPU pkg / RX550 edge | | | | ≤ |
| RAM total | | | | ≤ |

### 8.3 Checklist “NO empeora” (verificar BASE vs FASE A/B)
| Dominio | Verificación |
|---|---|
| Red | `ip -s link show enp3s0` (errores/descartes sin +); ping 5× al gateway o 8.8.8.8 (latencia no degradada) |
| Audio | `pactl info >/dev/null && echo OK` (o `pipewire` activo); sin errores nuevos de pipewire/wireplumber en journal |
| Plasma | `systemctl --user is-active plasma-core.target` = active; sin errores nuevos de `plasmashell`/`kwin_wayland` en journal |
| Estabilidad gráfica | journal `drm`/`i915` sin errores nuevos; sin reinicios de compositor (kwin PID estable) |
| RX550 | temp edge sin subida; Δ IRQ 42 sin incremento anómalo; `runtime_status`/`control` idénticos |
| Runtime PM | estados `/sys/bus/pci/devices/*/power/runtime_status` sin regresión (documentar antes/después con `grep -r . /sys/bus/pci/devices/*/power/runtime_status`) |
| Escritorio normal | sesión usable; ventanas/KVI interactúan sin error; plasmashell PID 6430 y kwin PID 6307 estables |

---

## 9. Criterios de abort (restaurar inmediatamente — §7.2)
- Crash o reinicio de `kwin_wayland` (PID 6307) o `plasmashell` (PID 6430).
- Errores nuevos de kernel (drm, i915, amdgpu, ahci) en journal durante la fase.
- IRQ 42 (amdgpu) con deltas anómalos o temperatura RX550 > 45 °C en reposo.
- `sda` con util% > 95 % sostenido o errores de E/S (`iostat` con `r_await`/`w_await` >> 500 ms).
- Pérdida de conectividad de red o audio roto.
- Cualquier hash de unidad/script distinto del §2.2.
- El resto de pids de referencia muere por causas no explicadas.

---

## 10. Orden de ejecución propuesto (cuando el usuario lo autorice)
1. `FASE BASE` — 20 min de medición.
2. `FASE A` — stop autopilot → 20 min de medición → start → verificar 2 ciclos OK (~10 min).
3. `FASE B` — stop kalm → 20 min de medición → start → verificar kalmd activo (~5 min).
4. Verificación final: repo estados §7.1, hashes, `git status`, journal sin errores.
5. Redactar informe con las tablas §8.2/§8.3 (a definir si es este archivo u otro según instrucción).

Duración total estimada: **≈ 1 h 40 min**. Nunca se tocan kalm-gpu, kalm-lite, mako, geoclue-demo, drkonqi, nobara.

---

## 11. Auditoría de comandos (realizada, 2026-09-23)

| Comando propuesto | Verificación realizada | Resultado |
|---|---|---|
| `systemctl stop system-autopilot.timer` | unit existe, type timer con cadencia 2 min, service oneshot corto | ✅ válido (deja de disparar; no toca archivo de unidad) |
| `systemctl start system-autopilot.timer` | rearma schedule (OnUnitActiveSec) → NEXT ≈ +2 min | ✅ válido |
| `systemctl stop kalm.service` | Type simple (default), MainPID 4055, Restart=always → no reactiva tras stop manual | ✅ válido |
| `systemctl start kalm.service` | vuelve a running; kalmd re-aplica afinidades solo si difieren | ✅ válido |
| `disable --now` (alternativa) | %Nombres de unidades verificados (`systemctl list-units`/`is-enabled`) | ✅ documentada, no primaria |
| Mediciones §3 | Todas las herramientas verificadas instaladas; lecturas sin root salvo turbostat (fallback vmstat/interrupts) | ✅ |
| Deltas diskstat/journal | formato `/proc/diskstats` (`sda` línea) y `journalctl --since/--until` validados | ✅ |

**Resultado de la PRECHECK (sección nueva §1.4)**:
| Comprobación | Evidencia | Resultado |
|---|---|---|
| Relación timer → service | `Triggers: system-autopilot.service`; `Unit=` resuelto; sin `Requires/PartOf` (independientes) | ✅ mapeo implícito por basename |
| Service existe y su estado | oneshot, `inactive` entre ciclos; `Result=success` | ✅ |
| Disparador extra del service | symlink **manual** en `multi-user.target.wants/` (may 7 11:50) → 1 ejecución al boot | ✅ documentado |
| Instancia en curso durante PRECHECK | PID 108389 (ciclo 10:41:44→45) | ✅ confirma: `stop` del timer no corta un run ya iniciado |
| `stop` del timer suficiente para “sin nuevas ejecuciones” | sí en este boot; service se detiene también por rigor (ambas unidades) | ✅ corrección aplicada §5.2 |
| `stop kalm.service` mata a kalmd | Type=simple, cgroup con **1 task** (4055), KillMode=control-group, SendSIGKILL=yes | ✅ confirmado |
| `systemctl enable` del service autopilot | el unit **no tiene `[Install]`** → enable/disable via systemd **fallan**; symlink es manual (`ln -s` para recrear) | ✅ quirk documentado §1.4-7/§7.2 |
| Symlink kalm | `multi-user.target.wants/kalm.service` estándar (sí tiene `[Install]`) | ✅ |

**Nota de contexto para la interpretación (honestidad de la prueba)**: la mayor parte del beneficio esperado está en **journal + I/O del HDD + limpieza de conflictos**, no en CPU/RAM (los spawns de 2 min son baratos; los `omitiendo` de kalmd son lecturas de sysfs). Los números arriba lo medirán objetivamente; si la diferencia resulta pequeña, la conclusión válida es “bajo coste”, no “sin efecto”.

---

*FIN DEL PROTOCOLO — pendiente de aprobación del usuario para su ejecución. No se ejecutó ninguna desactivación; no se inició Set H; no se hizo commit.*
