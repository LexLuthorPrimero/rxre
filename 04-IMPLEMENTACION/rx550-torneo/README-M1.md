# rx550-torneo — M1: runner sostenido de `power1_cap` (35 W vs 30 W)

> **MECANISMO de medición controlada. NO es optimización.**
> El runner sostiene un cap durante UNA corrida y SIEMPRE lo restaura.
> La ejecución real de M1 **no está autorizada todavía**.

Implementación: `src/rx550_torneo/cap_run.py` + subcomandos `m1-run` y
`m1-schedule` en el CLI. Tests: `tests/run_tests_m1.py` (62/62).

## Flujo exacto de escritura / rollback

```
preflight (read-only: GPU, power/control=on, DPM=auto, sin forcing, original=35M, límites)
  -> SET power1_cap=target        (escritura 1)  -> readback obligatorio
  -> workload (vkmark) + sampler 10 Hz (SOLO LECTURA)
  -> RESTORE power1_cap=35000000  (escritura 2)  -> readback final obligatorio
  -> verificación de auxiliares (power/control, DPM, SCLK/MCLK, profile)
```

- Escrituras privilegiadas totales: **exactamente 2**, siempre sobre `power1_cap`.
- El sampler no escribe. No hay `sudo` ni privilegios por muestra.
- El runner se lanza **una vez** con `sudo`; el workload corre como el usuario
  de escritorio (`SUDO_UID`/`SUDO_GID`). El guard (fork) restaura ante SIGKILL.

## Abortos (restauran SIEMPRE)
`temp1_input >= 90 °C` · timeout de workload · **`workload rc != 0` (→ ERROR)** ·
**reset/hang de GPU detectado (ventana `journalctl`, → CRITICAL)** · `SIGINT`/`SIGTERM`/`SIGHUP` ·
error de write/readback · excepción inesperada · nodo inaccesible.
Si el restore no verifica readback: `CRITICAL`, se detiene y no reintenta.
`run_schedule` aborta ante **cualquier** resultado distinto de `OK` y no inicia otro bloque.

## Identidad del workload (root)
Si el runner corre como root pero no hay `SUDO_UID` válido (p.ej. `sudo -i`), se
**rechaza antes de tocar sysfs**: el workload nunca corre como root. El caso normal
`sudo ./rx550-torneo ...` hereda `SUDO_UID`/`SUDO_GID` y arranca el workload como el usuario.
Además el workload recibe `HOME=<home real del uid>` (nunca `/root`) y
`XDG_RUNTIME_DIR=/run/user/<uid>`; las variables gráficas (`DISPLAY`,
`WAYLAND_DISPLAY`, `XAUTHORITY`, `DBUS_SESSION_BUS_ADDRESS`) se conservan si están
y, si faltan, se derivan de la sesión del uid. Así Mesa no cae en
`/root/.cache/... Permission denied`.

## Detección de reset/hang (7d)
Se consulta `journalctl -k` **solo-lectura** con una **ventana temporal exacta**
alrededor del workload (`--since`/`--until` capturados antes/después de lanzarlo),
en **un único formato** (`--output=short-iso`). No se hace diff posicional del
ring buffer. Solo cuentan firmas inequívocas con prefijo `amdgpu|drm` (`ring ...
timeout`, `GPU reset`, `reset begin/success`, `asic/ring reset`, `job timeout`,
`hang`, `failed to reset`). Se **excluye** explícitamente el mensaje benigno
`Disabling VM faults because of PRT request!` y **no** se trata `VM fault`/`page
fault` como reset. Coincidencia → `CRITICAL` + restore + aborto del schedule.
El audit guarda `gpu_reset_check = {checked, error, format, expected_format,
since, until, matches}`. Si la fuente no está disponible o el formato no coincide,
`checked: false` y el run **no** se aborta (límite documentado; sin heurística
agresiva).

## CLI

```bash
# Dry-run (read-only, no escribe): verifica precondiciones
./rx550-torneo m1-run
./rx550-torneo m1-run --json

# Una corrida real (requiere root)
sudo ./rx550-torneo m1-run --confirm --target 30000000 --duration 25 --out DIR

# M1 completo: 5 bloques pareados 35/30, orden alternado, cooldown <=45 C
sudo ./rx550-torneo m1-schedule --confirm --blocks 5 \
     --arms 35000000 30000000 --duration 25 --out DIR
```

Test-mode (nunca toca `/sys`): `RX550_TORNEO_TEST_MODE=1`,
`RX550_TORNEO_TEST_WRITE_PATH=<archivo fuera de /sys>`,
`RX550_TORNEO_TEST_WORKLOAD="<comando>"`.

## Tests y strace
`python3 tests/run_tests_m1.py` (112/112) cubre: happy path (2 writes, workload tras
readback), original != 35M, precondiciones, forcing, out-of-range, set/restore
readback malo (workload no corre / CRITICAL y stop), abort por temperatura,
timeout, orden antes del workload, SIGTERM, aux cambiado, alternancia y parada
del schedule, **workload rc!=0 (ERROR + restore + abort)**, **root sin SUDO_UID
(rechazo sin escrituras)**, **excepción tras SET aplicado (restore)**, **reset/hang
simulado (CRITICAL + restore + abort)**, **journal no disponible (documentado)**,
**7d: PRT histórico benigno no dispara (A)**, **VM fault aislado no dispara (B)**,
**ring timeout nuevo → CRITICAL (C)**, **GPU reset nuevo → CRITICAL (D)**,
**formato incompatible → checked=false sin CRITICAL (E)**, **ventana vacía →
checked=true, 0 matches (F)**, **HOME del workload = usuario no-root (G)**,
**cero writes a nodos sysfs distintos de `power1_cap` (H)**, **strace (cero
escrituras a `/sys`, exactamente 2 a `power1_cap`, set antes del workload)** y
**guard que restaura tras `SIGKILL`**.

## Riesgos / UNKNOWN
- **Compuerta de ligadura**: los workloads reproducibles actuales demandan
  <= 13.6 W; un cap de 30 W probablemente NO ligue → resultado
  `NO DISCRIMINATIVO` (ver `CONDICIONES.txt`). No se declara "sin efecto".
- Granularidad/redondeo real del driver para `power1_cap` (se detecta por readback).
- `power1_input` es estimador SMU, no medición eléctrica directa.
- El workload corre como el usuario; requiere sesión gráfica activa para vkmark.
