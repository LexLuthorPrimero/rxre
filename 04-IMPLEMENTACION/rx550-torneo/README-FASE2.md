# rx550-torneo — Fase 2: prueba CONTROLADA de write + rollback

> **TEST CONTROLADO del mecanismo. NO es una función de optimización.**
> No implementa perfiles, forcing de SCLK/MCLK, DPM, power cap, runtime-PM
> automation ni benchmarks.

Valida de extremo a extremo:

```
CAPTURA -> WRITE ÚNICO -> READBACK -> ROLLBACK -> READBACK FINAL
```

Única variable autorizada a escribir:

```
<device RX 550>/power/control      (valores válidos: on | auto)
```

No asume `on`: lee el valor original y lo restaura exactamente, sea `on` o `auto`.

## Garantías y alcance

- Máximo **2 escrituras** al nodo: temporal + restauración. Nada más.
- `SysfsNode.verify_authorized()` exige que el path real sea exactamente el
  `power/control` del device de la RX 550 (`1002:699f`) antes de cada escritura.
- `FileNode` (usado solo en test-mode) se niega a apuntar a `/sys`.
- El resto del programa sigue protegido por `util.guard_no_sys_write`.
- No toca `power1_cap`, DPM, `pp_dpm_sclk/mclk`, `pp_power_profile_mode`,
  voltajes, clocks, GRUB, kernel, Mesa, Kalm, DRM/KMS ni la configuración de
  display. La GPU de display (Intel HD 4600) no se modifica.

## Precondiciones (dinámicas)

1. GPU objetivo PCI `1002:699f` (nunca asume `cardN`).
2. DRM card y path real de `power/control` resueltos por topología.
3. Intel `8086:0412` con conector `connected` = GPU de display; la RX 550 sin
   display (`gpu_finder.discover()` ya lo exige).
4. Captura del estado completo existente (`state_manager.capture`) antes.
5. Lectura del valor original exacto; si no es `on`/`auto`, **no se escribe**.

## Failsafe

Maneja: `SIGINT`, `SIGTERM`, excepción inesperada, fallo de readback, fallo de
write, GPU desaparecida, ruta sysfs inválida y pérdida de acceso al nodo.

- Ante cualquier error **después** del write se intenta restaurar el valor
  original **una sola vez** y se registra el resultado.
- Si la restauración no puede verificarse: resultado `CRITICAL`, se detiene y se
  informa qué quedó modificado. No se intentan cambios adicionales.
- Un write rechazado (permiso/error) no dispara rollback: no llegó a escribirse.

## Comparación de nodos no autorizados

- **Estricta** (byte a byte): `power1_cap`,
  `power_dpm_force_performance_level`, `pp_power_profile_mode`.
- **Normalizada** (`pp_dpm_sclk`, `pp_dpm_mclk`): se ignora el marcador `*` de
  nivel activo, que es telemetría en vivo y cambia solo; se compara la tabla.
- `runtime_status` se registra; puede cambiar como consecuencia directa de
  `power/control` y no es una escritura nuestra.

## CLI

```bash
# Dry-run (por defecto): preflight, NO escribe nada
./rx550-torneo state-write-test
./rx550-torneo state-write-test --json

# Prueba real controlada (requiere root para escribir sysfs)
sudo ./rx550-torneo state-write-test --confirm --json
```

Salida: original, temporal, readback, restaurado, readback final, intentos de
rollback, diff auxiliar y resultado. El registro de auditoría se persiste en
`$XDG_STATE_HOME/rx550-torneo/write-test-<timestamp>.json` (atómico).

Campos de auditoría: `timestamp`, `pci_id`, `drm_card`, `bdf`, `path`,
`original`, `temporary`, `readback`, `restored`, `readback_final`, `result`,
`rollback_attempts`, `aux_before/after/diff`, `events`, `capture_before`.

## Runbook de la prueba real (root)

```bash
cd ~/Escritorio/RX550-INVESTIGACION/04-IMPLEMENTACION/rx550-torneo
sudo ./rx550-torneo state-write-test --confirm --json
```

Antes / después, verificar (read-only):

```bash
./rx550-torneo status --json      # GPU detectada + Intel display
./rx550-torneo verify             # validaciones integrales (rc=0)
cat /sys/class/drm/card1/device/power/control
```

## Tests

```bash
python3 tests/run_tests_fase2.py
```

Cobertura A–J + failsafes: original `on`→rollback; original `auto`→rollback;
readback incorrecto; write rechazado; GPU incorrecta; path incorrecto;
`SIGINT`/`SIGTERM`; excepción tras el write; pérdida de acceso; `strace`
(≤2 writes al nodo, cero a `/sys`); dry-run sin escritura; y verificación de que
los nodos reales quedan intactos (contenido + mtime).

**Resultado: 55/55 checks OK.** La suite nunca escribe sysfs: usa `FakeNode` en
memoria y `FileNode` con archivo plano fuera de `/sys` (`RX550_TORNEO_TEST_MODE`).
