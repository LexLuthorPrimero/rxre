# Pruebas y validación — RX 550

**Fecha:** 2026-09-25
**Modo permitido:** `READ_ONLY/EVIDENCE` y pruebas estáticas con temporales.

## 1. Matriz

| ID | Prueba | Comando | Resultado válido | Significado |
|---|---|---|---|---|
| T-01 | Identidad PCI | `python3 tools/validate_rx550_final.py` | devuelve 0 y encuentra `1002:699f` | Detecta host objetivo |
| T-02 | Renderer GL explícito | `DRI_PRIME=1002:699f glxinfo -B` | RX550/Polaris12 | Verifica el renderer; no demuestra estabilidad |
| T-03 | RADV aislado | `VK_ICD_FILENAMES=...radeon_icd.x86_64.json vulkaninfo --summary` | `0x699f`, RADV | Verifica ICD, no compatibilidad VK_EXT |
| T-04 | Tests rx550-torneo | `PYTHONDONTWRITEBYTECODE=1 python3 tests/run_tests.py` | `64/64` | Detección dinámica y guards |
| T-05 | Tests M1 | `PYTHONDONTWRITEBYTECODE=1 python3 tests/run_tests_m1.py` | `110/110` | Nodo temporal, restore y firmas de journal |
| T-06 | Tests C1 | `python3 -m unittest discover -s 04-IMPLEMENTACION/tests -p 'test_*.py'` | 54 OK, 1 skip | Tests estáticos; no C1 runtime |
| T-07 | Sintaxis | `python3 -m py_compile ...` | exit 0 | Compila Python |
| T-08 | Higiene Git | `git diff --check` | exit 0 | Whitespace |
| T-09 | Commits/secretos | revisión de `git status`, hashes y búsqueda de secretos | sin secreto; remoto declarado | No hacer push sin autorización |

`strace` no está instalado en el host validado. Los tests que lo requieren se
marcan `NOT_AVAILABLE`; no se cuentan como PASS y no se instala durante esta
fase.

## 2. Pruebas negativas y guardas

- El test de PRT no debe clasificarse como reset.
- Un VM fault aislado no debe clasificarse como ring timeout.
- Un ring timeout o reset explícito sí debe activar `CRITICAL` en el detector.
- Un target PCI incorrecto debe abortar antes de escribir.
- Un nodo temporal M1 debe restaurar el cap original tras salida normal y
  `SIGKILL`.
- Un selector numérico `DRI_PRIME=1` no debe usarse como prueba de RX550.

Estas pruebas son estáticas o usan `/tmp`; no usan `/sys` como destino.

## 3. Prueba de forbidden de runtime

No ejecutar como parte de esta entrega:

```text
sudo
systemctl stop/start/restart
C1 --run / run_c1()
vkmark/glmark/FurMark/GravityMark/Superposition
A/B de power cap
SMART/scrub/Btrfs write
modprobe, GRUB, initramfs, udev, VFIO binding
```

La tabla anterior no autoriza esos comandos. Si una de estas acciones es
necesaria, requiere una autorización runtime separada, evidencia de aislamiento
y recovery validado.

## 4. Ventana de evidencia

Para cualquier repetición autorizada, guardar en la misma ventana:

```text
fecha/hora UTC y local
hostname/boot id o equivalente
PCI BDF, vendor/device, card, render node, driver
renderer GL y RADV
DPM/SCLK/MCLK, cap, W_SMU, temperatura, runtime_status
journal de kernel y compositor
identidad del workload y código de salida
```

Un código de salida cero sin journal limpio no es un PASS de estabilidad.

## 5. Criterio de cierre

Un problema puede pasar de `PARTIALLY_RESOLVED` a `RESOLVED` sólo si existe
una prueba reproducible, identidad de GPU, configuración exacta, resultado
positivo y negativo explícito cuando aplique, y rollback documentado. La
ausencia de un error en una instantánea se registra como `NOT_REPRODUCED`,
no como `RESOLVED`.
