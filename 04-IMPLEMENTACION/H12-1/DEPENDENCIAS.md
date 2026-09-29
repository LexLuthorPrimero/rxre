# H12-1 — Dependencias y límites de compilación

## Dependencias de build requeridas

| Dependencia | Uso | Comprobación |
|---|---|---|
| C11 compiler | Compilar el probe | `cc`/`gcc` |
| CMake >= 3.16 | Generar el binding xdg-shell y el target | `cmake` |
| Vulkan loader + headers | Instance, surface, queue, swapchain, queries | `find_package(Vulkan)` y `vulkan/vulkan.h` |
| Wayland client library + headers | Display, surface, `wl_surface.frame` | `pkg-config wayland-client` |
| Wayland protocol XML | xdg-shell | `pkg-config wayland-protocols` |
| `wayland-scanner` | Generar header y private code de xdg-shell | `find_program(wayland-scanner)` |

No se requiere `xkbcommon`, EGL, GLFW, shader compiler, kernel module, counter
tool ni paquete de benchmark para compilar H12-1.

## Dependencias de runtime

- Una sesión Wayland nativa con `xdg_wm_base` y `wl_compositor`.
- Un ICD Vulkan que exponga la RX 550 `1002:699f` y `VK_KHR_wayland_surface`.
- `VK_KHR_swapchain` en el dispositivo.
- La imagen/swapchain debe ser soportada por la queue graphics seleccionada.

El instrumento no fuerza `MESA_VK_DEVICE_SELECT` ni confía en el orden de
enumeración. Exige exactamente un dispositivo Vulkan con:

```text
vendorID = 0x1002
deviceID = 0x699f
```

El nombre, API y bus PCI (si `VK_EXT_pci_bus_info` está disponible) se escriben
en metadata. La correlación de ownership o output sigue siendo `UNKNOWN`
salvo que una fase posterior la demuestre.

## Extensions Vulkan tratadas como opcionales

| Extension | Política H12-1 |
|---|---|
| `VK_KHR_surface` | Requerida |
| `VK_KHR_wayland_surface` | Requerida |
| `VK_KHR_swapchain` | Requerida |
| `VK_EXT_pci_bus_info` | Si está disponible, se registra el bus PCI |
| `VK_KHR_get_surface_capabilities2` o Vulkan 1.1 core | Necesaria para la ruta de capabilities |
| `VK_KHR_get_physical_device_properties2` o Vulkan 1.1 core | Necesaria para features2/properties2 y calibrated timestamps |
| `VK_KHR_present_id2` | Se usa solo con feature y `presentId2Supported`; el swapchain lleva `VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR` |
| `VK_EXT_present_timing` | Se activa solo con extensión, feature, `VK_KHR_calibrated_timestamps`, surface, dominio y entry points reales |
| `VK_KHR_present_wait2` | Se consulta como soporte y depende de Present-ID2; no se usa para bloquear el loop ni se marca observado |
| `VK_EXT_calibrated_timestamps` / `VK_KHR_calibrated_timestamps` | Se registra la capability; no se deriva correlación |

Una extension anunciada pero no utilizable se marca `NOT_AVAILABLE` o
`CONFLICT`; no se convierte en un timestamp sintético.

## Inventario local observado durante H12-1

La comprobación de disponibilidad fue read-only y no instaló nada:

- Vulkan loader: `1.4.341`.
- Wayland client: `1.25.0`.
- Wayland protocols: `1.49`.
- CMake: `4.3.0`.
- Compiler GCC: `16.2.1`.
- `wayland-scanner`, `vulkan/vulkan.h` y `wayland-client.h`: presentes.

La compilación usada para verificar el código se realizó en:

```text
/tmp/opencode/h12-1-build
```

Ese directorio es externo al repositorio. La compilación no ejecuta el
instrumento ni campaigns H12.

## Si falta una dependencia

CMake debe fallar con el nombre de la dependencia y no debe intentar instalar
paquetes. En ese caso H12-1 queda `BUILD_BLOCKED`; no se sustituye una
dependencia por una ruta inventada ni se modifica el sistema para resolverla.

## Dependencias explícitamente no requeridas

- X11/Xlib/XCB: no son el backend de H12-1.
- EGL/GLX/GLFW: no se usan.
- `VK_EXT_calibrated_timestamps` no es condición para arrancar; su ausencia solo
  cambia la capability reportada.
- `VK_EXT_present_timing` no es condición para arrancar; su ausencia cambia el
  campo de timing a `NOT_AVAILABLE`.
- Ninguna dependencia de `radeontop`, `umr`, `perf`, PMU, GFX8 counters,
  sysfs, DPM, power cap, runtime-PM, ASPM, Mesa o firmware.
