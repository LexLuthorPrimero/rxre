# rx550-torneo — Fase 3: preparación del test CONTROLADO de `power1_cap`

> **PREPARACIÓN del mecanismo. NO es una función de optimización ni un sweep.**
> No implementa perfiles, forcing de SCLK/MCLK, DPM, voltajes ni benchmarks.
> No toca `power/control`.
>
> **Estado: fase de ESCRITURA COMPLETADA.** La prueba real fue ejecutada por el
> usuario con resultado `OK` (ver «Cierre de la fase de escritura»). NO se ha
> ejecutado ningún benchmark. La comparación 35 W vs 30 W es una microfase
> posterior, pendiente de autorización.

Valida de extremo a extremo, sobre una única variable:

```
CAPTURA -> WRITE ÚNICO -> READBACK -> ROLLBACK -> READBACK FINAL
```

Única variable autorizada a escribir:

```
<hwmon dinámico de la RX 550>/power1_cap      (µW)
```

`power/control`, DPM, SCLK/MCLK, `pp_power_profile_mode`, voltajes y clocks
permanecen intactos y se verifican antes/después.

## Objetivo

Establecer un mecanismo reproducible para un **experimento controlado** donde
`power1_cap` es la única variable de rendimiento, con garantía de restauración.
No se miden FPS todavía. No hay sweep 25/28/32/35 W.

## Cierre de la fase de escritura

Prueba real ejecutada por el usuario (**root**), resultado **OK**:

| Campo | Valor |
|---|---|
| original `power1_cap` | `35000000` µW |
| temporal | `30000000` µW |
| readback temporal | `30000000` µW |
| restaurado | `35000000` µW |
| readback_final | `35000000` µW |
| `rollback_attempts` | `1` |
| `aux_diff` | `[]` |
| `aux_unchanged` | `true` |
| `power/control` | `on` sin cambios |
| DPM | `auto` sin cambios |
| SCLK/MCLK/power profile | sin cambios |
| `runtime_status` | `active` |
| resultado | `OK` |

Verificado post-prueba (read-only): `power1_cap=35000000`, `power/control=on`
(mtime `2026-09-19 22:46:12`), DPM `auto`, `runtime_status=active`.
El JSON de auditoría de esta corrida quedó bajo el `XDG_STATE_HOME` de root
(no legible sin privilegios); el contenido coincide con la tabla anterior.

**Fase de escritura CERRADA.** Próximo paso: diseño de la microfase de medición
35 W vs 30 W (sin ejecutar todavía).

## Valor temporal propuesto

- Original real: `35000000` µW (35 W) = `power1_cap_max`.
- Temporal por defecto: `30000000` µW (30 W), vía `DEFAULT_DELTA_UW = 5_000_000`.
- Solo se puede bajar (min `0`, max `35000000`); el valor no pertenece al sweep
  futuro {25,28,32,35} y sirve para validar el ciclo sin confundirse con una
  medición de rendimiento.

## Garantías y alcance

- Máximo **2 escrituras** al nodo: temporal + restauración. Nada más.
- `SysfsNode.verify_authorized()` exige que el path real sea exactamente el
  `power1_cap` del hwmon de la RX 550 (`1002:699f`) antes de cada escritura.
- `hwmon` se resuelve dinámicamente desde el PCI `1002:699f`; nunca asume
  `hwmon2` (se valida con `util.path_belongs_to_prefix`).
- `FileNode` (solo test-mode) se niega a apuntar a `/sys`.
- El resto del programa sigue protegido por `util.guard_no_sys_write`.
- No toca `power/control`, DPM, `pp_dpm_sclk/mclk`, `pp_power_profile_mode`,
  voltajes, clocks, GRUB, kernel, Mesa, Kalm, DRM/KMS ni la configuración de
  display. La GPU de display (Intel HD 4600) no se modifica.

## Precondiciones (dinámicas)

1. GPU objetivo PCI `1002:699f` (nunca asume `cardN`).
2. DRM card y hwmon resueltos por topología; hwmon pertenece al device.
3. Intel `8086:0412` con conector `connected` = GPU de display; la RX 550 sin
   display (`gpu_finder.discover()` ya lo exige).
4. Captura del estado completo existente (`state_manager.capture`) antes.
5. Límites reales leídos de sysfs (`power1_cap_min/max/default`).
6. `original` debe estar dentro de `[min, max]`, si no **no se escribe**.
7. El valor temporal debe estar dentro de `[min, max]` y ser distinto del
   original, si no **no se escribe**.

## Failsafe

Maneja: `SIGINT`, `SIGTERM`, excepción inesperada, fallo de readback, fallo de
write, GPU desaparecida, hwmon inválido, ruta sysfs inválida y pérdida de acceso
al nodo.

- Ante cualquier error **después** del write se intenta restaurar el valor
  original **una sola vez** y se registra el resultado.
- Si la restauración no puede verificarse: resultado `CRITICAL`, se detiene y se
  informa qué quedó modificado. No se intentan cambios adicionales.
- Un write rechazado (permiso/error) no dispara rollback: no llegó a escribirse.

## Riesgos / UNKNOWN

- **Granularidad**: sysfs expone `min=0`, pero se desconoce el mínimo práctico y
  el redondeo real que acepta el driver. Se detectará por readback mismatch
  (dispara rollback). No asumir que un valor escrito se acepta tal cual.
- Solo hay margen hacia abajo (`original == max`).
- Cualquier cambio inesperado en nodos no autorizados aborta con `AUX_CHANGED`.

## Comparación de nodos no autorizados

- **Estricta** (byte a byte): `power/control`,
  `power_dpm_force_performance_level`, `pp_power_profile_mode`.
- **Normalizada** (`pp_dpm_sclk`, `pp_dpm_mclk`): se ignora el marcador `*` de
  nivel activo, que es telemetría en vivo y cambia solo; se compara la tabla.
- `runtime_status` se registra; puede cambiar solo y no es una escritura nuestra.

## CLI

```bash
# Dry-run (por defecto): preflight + límites + valor propuesto, NO escribe nada
./rx550-torneo cap-write-test
./rx550-torneo cap-write-test --json
./rx550-torneo cap-write-test --value 30000000

# Prueba real controlada (requiere root para escribir sysfs)
sudo ./rx550-torneo cap-write-test --confirm --json
```

Salida: ruta, límites, original, temporal, readback, restaurado, readback final,
intentos de rollback, diff auxiliar y resultado. La auditoría se persiste en
`$XDG_STATE_HOME/rx550-torneo/write-test-<timestamp>.json` (atómico).

Campos de auditoría: los de Fase 2 más `field`, `limits`, `original_int`,
`temporary_int`, `delta_int`.

## Runbook propuesto (NO ejecutar todavía)

```bash
cd ~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo
./rx550-torneo cap-write-test                 # ver valor propuesto (read-only)
sudo ./rx550-torneo cap-write-test --confirm --json
```

Antes / después, verificar (read-only):

```bash
./rx550-torneo status --json
./rx550-torneo verify
cat /sys/class/drm/card1/device/hwmon/hwmon2/power1_cap
cat /sys/class/drm/card1/device/power/control
cat /sys/class/drm/card1/device/power_dpm_force_performance_level
```

## Tests

```bash
python3 tests/run_tests_fase3.py
```

Cobertura A–J + failsafes: original→temporal→rollback; fuera de rango y valor
igual al original (rechazo antes de escribir); readback incorrecto; write
rechazado; GPU incorrecta; hwmon incorrecto / nodo no autorizado; `SIGINT`/
`SIGTERM`; excepción tras el write; pérdida de acceso (antes y después);
`strace` (exactamente 2 writes al nodo, cero a `/sys`); dry-run sin escritura ni
auditoría; y verificación de que `power/control`, DPM, SCLK/MCLK y profile reales
quedan intactos (contenido + mtime).

**Resultado: 56/56 checks OK.** La suite nunca escribe sysfs: usa `FakeNode` en
memoria y `FileNode` con archivo plano fuera de `/sys` (`RX550_TORNEO_TEST_MODE`).
