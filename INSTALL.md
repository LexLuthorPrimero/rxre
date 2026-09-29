# Instalación y preparación reproducible — RX 550

**Versión del documento:** 2026-09-25
**Modo de esta entrega:** `DOCUMENTATION` + `STATIC_IMPLEMENTATION`
**No es un instalador de cambios persistentes.**

## 1. Requisitos

- Host con la GPU objetivo `1002:699f` (Radeon RX 550/Polaris12, BDF
  `0000:01:00.0` en la instalación validada).
- Driver de kernel `amdgpu`; no usar `radeon` como sustituto automático.
- Nobara/Fedora compatible con paquetes Mesa, Vulkan loader, libdrm, LLVM y
  `linux-firmware`.
- Una sesión gráfica y un usuario normal. No usar `sudo` para las comprobaciones
  de diagnóstico.
- Para aislamiento/VFIO: hardware y recovery independientes; la instalación
  actual no cumple esos requisitos.

Comprobación de identidad, sin escrituras:

```bash
python3 tools/validate_rx550_final.py
```

El comando debe encontrar `1002:699f`, BDF `0000:01:00.0`, driver `amdgpu` y
un render node. Si no coincide, detener la preparación.

## 2. Paquetes y versiones

La instalación validada tenía:

| Paquete | Versión |
|---|---|
| `mesa-dri-drivers` | `25.3.2-2.fc43.x86_64` |
| `mesa-vulkan-drivers` | `25.3.2-2.fc43.x86_64` |
| `libdrm` | `2.4.128-3.fc43.x86_64` |
| `llvm-libs` | `21.1.7-1.fc43.x86_64` |
| `vulkan-loader` | `1.4.328.1-1.fc43.x86_64` |
| `vulkan-tools` | `1.4.328.1-1.fc43.x86_64` |
| `linux-firmware` | `20251125-1.fc43.noarch` |

Comprobar sin instalar:

```bash
rpm -q mesa-dri-drivers mesa-vulkan-drivers libdrm llvm-libs \
  vulkan-loader vulkan-tools linux-firmware
```

No instalar ni copiar el Mesa CUSTOM histórico de `/opt` como primer paso. La
build experimental no es la ruta de producción y no se ha demostrado necesaria.

## 3. Detección de hardware

La tarjeta Intel y la RX 550 pueden cambiar de `cardN` entre arranques. Resolver
siempre por vendor/device y BDF:

```bash
lspci -nnk -s 01:00.0
readlink -f /sys/class/drm/card*/device
cat /sys/bus/pci/devices/0000:01:00.0/vendor
cat /sys/bus/pci/devices/0000:01:00.0/device
```

En el host validado la Intel es `8086:0412`, `card1`, y la RX 550 es
`1002:699f`, `card2`. Esos números son sólo una observación de esta máquina.

## 4. OpenGL, Mesa y DRI_PRIME

Para un proceso que deba usar la RX 550:

```bash
DRI_PRIME=1002:699f glxinfo -B
```

También se puede usar el BDF como selector Mesa:

```bash
DRI_PRIME=pci-0000_01_00_0 glxinfo -B
```

No usar `DRI_PRIME=1` como atajo “AMD”: en la instalación actual `1` devuelve
Intel. No exportar una variable global sin probar KWin, Xwayland y la
permanencia de la sesión.

## 5. Vulkan/RADV

No depender de `MESA_VK_DEVICE_SELECT` para proof de renderer. Fijar el ICD
RADV x86_64 en el proceso que se desea medir:

```bash
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
  vulkaninfo --summary
```

El resultado esperado en el host validado es `deviceID=0x699f` y
`AMD Radeon RX 550 / 550 Series (RADV POLARIS12)`. Si se heredan variables de
otro ICD, se deben limpiar en el entorno del proceso antes de comparar.

`VK_EXT_image_drm_format_modifier` no aparece en el dispositivo GFX8 validado;
no se debe crear una expectativa de capacidad basada en la extensión ausente.

## 6. Kernel, amdgpu y firmware

No añadir parámetros de kernel, `vfio-pci`, `iommu=off`, `nomodeset`, GRUB,
initramfs o reglas udev como parte de esta preparación. La captura validó
`amdgpu` con firmware/ROM presentes, pero no valida VBIOS, reset, BACO o
runtime PM.

## 7. Configuración persistente

Archivos que se deben inspeccionar, sin modificarlos automáticamente:

- `/etc/modprobe.d/`
- `/etc/dracut.conf.d/`
- `/etc/udev/rules.d/`
- `/etc/default/grub`
- `/etc/systemd/system/`

La instalación validada no tenía una configuración específica de RX 550 en esos
sitios. Si aparece una, compararla con el hash/manifest y con
`ROLLBACK.md` antes de actuar.

## 8. Variables de entorno

Variables aceptables para un proceso aislado:

```text
DRI_PRIME=1002:699f
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
```

Variables que no deben heredarse sin revisión:

```text
MESA_CUSTOM
LD_LIBRARY_PATH
LIBGL_DRIVERS_PATH
MESA_VK_DEVICE_SELECT
VK_DRIVER_FILES
```

`MESA_VK_DEVICE_SELECT` se conserva como evidencia histórica, no como
mecanismo de producción. El runner M1 limpia esas variables en el entorno del
workload.

## 9. Procedimiento de preparación

1. Ejecutar el validador read-only y guardar el JSON con un nombre fechado.
2. Confirmar GPU, BDF, driver, render node, Mesa, RADV y firmware.
3. Ejecutar los tests estáticos de `TESTING.md`.
4. Para una sesión gráfica concreta, usar sólo selectores por proceso.
5. Revisar journal del mismo intervalo y registrar `W_SMU`, clocks, cap,
   temperatura y clientes; no interpretar un campo aislado.
6. No lanzar `rx550-torneo m1-run`, C1, benchmarks ni A/B sin autorización
   específica para runtime.
7. No declarar una corrección como `RESOLVED` si sólo se verificó que el
   comando arranca.

## 10. Pruebas de aceptación

La aceptación mínima de esta entrega es:

- identidad RX550 detectada por PCI;
- renderer GL explícito RX550;
- RADV aislado devuelve `0x699f`;
- ninguna escritura a `/sys` en las pruebas estáticas;
- journal sin reset/ring timeout no-PRT en la ventana leída;
- tests estáticos con resultados reproducibles;
- problemas no demostrados conservados como `UNRESOLVED`, `UNKNOWN` o
  `NOT_REPRODUCED`.

## 11. Rollback

Esta entrega no instala configuración persistente. El rollback de una sesión
con variables por proceso consiste en cerrar el proceso o sesión y limpiar las
variables exportadas. No existe un cambio de kernel, Mesa, firmware, servicio,
udev o GRUB que deshacer.

## 12. Seguridad y publicación

- No copiar logs con rutas personales, cookies, tokens, claves o volcados.
- No publicar el instalador de 193 MB ni el descarga parcial de 34 MB.
- Mantener el historial local; si se prepara un árbol público, excluir
  artefactos generados y documentar la exclusión.
- Revisar `git diff --check`, hashes, estado Git y remoto antes de publicar.
- `READY_FOR_GITHUB` sólo puede ser `YES` si no hay resoluciones falsas y la
  revisión de seguridad está cerrada.
