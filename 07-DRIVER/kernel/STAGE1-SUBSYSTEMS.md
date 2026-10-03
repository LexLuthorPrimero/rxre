# STAGE1-SUBSYSTEMS — análisis por subsistema, driver RX 550

`DOCUMENTATION` · etapa 1 · host `7.1.3-200.nobara.fc44.x86_64` · GPU identificada por
identidad PCI `1002:699f`, nunca por nombre de nodo `cardN` · fecha de captura 2026-09-29.

Referenciado por `rx550_drv.c` y por `Makefile:check-drivers`. Si este fichero se mueve,
esas dos referencias quedan rotas.

## 0. Por qué existe este documento

La directiva que abre la etapa 1 fija `IMPLEMENTATION_IS_NOT_AUTHORITY`: que `amdgpu`
tenga una abstracción no la convierte en requisito de la RX 550. Este fichero es el
requisito de cada subsistema, separado de la elección de implementación, para que una
subsistema existente no sobreviva por tradición.

Regla de decisión aplicada en cada fila: **un subsistema entra si el hardware lo exige,
el core del kernel lo impone como contrato, o userspace no puede hacer su trabajo sin él.
Si no es ninguno de los tres, no entra.**

## 1. Diagrama de la etapa implementada

```
PCI
│
▼
probe()                                    rx550_drv.c:250
│
├── identify device                        rx550_probe() lee pdev->*
│   vendor 0x1002 device 0x699f           OBSERVED, 3 fuentes concordantes
│   subsistema 0x1002:0x0b04 revision 0xc7  OBSERVED
│   clase 0x030000                         OBSERVED (sysfs + lspci)
│
├── discover resources                     rx550_bar_describe()
│   lee pdev->resource[0..5], NO el config space crudo
│   4 de 6 BARs implementados              OBSERVED
│   tamaños vía res->end - res->start + 1  OBSERVED
│
├── map MMIO                               *** NO EN ETAPA 1 ***
│   ver §4. Bloqueado, no implementado.
│
├── initialize DRM                         devm_drm_dev_alloc + drm_dev_register(0)
│   sin GEM, sin KMS, sin master
│
└── cleanup                                remove() en orden inverso a probe()
│
▼
unload                                     module_pci_driver() autogenera exit
```

## 2. Subsistemas: qué entra y qué no

Estado de la columna "en etapa 1": `IMPLEMENTED` / `DEFERRED` / `EXCLUDED` / `BLOCKED`.

| Subsistema | Qué necesita la RX 550 | Qué impone el contrato | Qué da el hardware | ¿Se puede eliminar? | Etapa 1 |
|---|---|---|---|---|---|
| `pci_driver` | despertar el dispositivo, recibir el nodo | `pci_register_driver` es la única vía de entrada | PCIE | no | `IMPLEMENTED` |
| `pci_enable_device` | `MEM_SPACE` + `BUS_MASTER` para que un BAR sea accesible | `pci_enable_device` mantiene `enable_cnt`; sin él el core no da el BAR al driver | PCIE config space | no | `IMPLEMENTED` |
| `pci_request_regions` | reservar los BARs para que nadie más los reclame | claim de `struct resource`; sin él otro driver puede tomar el mismo BAR | — | no | `IMPLEMENTED` |
| Mapeo de MMIO | leer ASIC id, luego rings y VRAM | `pci_iomap_range` / `devm_ioremap` | BAR0, BAR2 (64 bit, prefetchable) | no, pero **no verificable aquí** | `BLOCKED` §4 |
| `drm_device` | dar a userspace un nodo `/dev` y un major/minor | `drm_dev_register` es lo que asigna major y crea el nodo | — | no, si se quiere `/dev/dri` | `IMPLEMENTED` |
| GEM / VRAM | los buffers BC3 y la textura descomprimida tienen que residir en VRAM accesible por la GPU | `drm_dev_register()` funciona sin GEM; sin él no hay `mmap` de buffers, ni `PRIME` | VRAM física | sí en la etapa 1; **no** en la etapa 2 | `DEFERRED` |
| KMS / modoset | la RX 550 tiene salidas físicas, pero la etapa 1 no las toca | `DRM_MINOR_PRIMARY` sin KMS no expone conectores |DisplayPipe | sí, en esta etapa | `EXCLUDED` |
| DRM master | sin KMS no hay nodo de control | — | — | sí, en esta etapa | `EXCLUDED` |
| Ring / command submission | es el objetivo final del driver | — | GFX8: GPR, sh, SEM | no, pero pertenece a una etapa posterior | `DEFERRED` |
| IRQ / MSI-X | cada ring necesita su vector | — | PCIe MSI-X | no, más adelante | `DEFERRED` |
| Firmware | GFX8 carga PSP/NBX blobs en el momento del init | — | on-die PSP | no, pero no en la etapa 1 | `DEFERRED` |
| PM / clocks | — | — | — | sí | `EXCLUDED` |
| `char device` | — | — | — | **sí: eliminado como camino principal** | `EXCLUDED` §3 |

### 2.1 GEM — corrección de una línea mal redactada

La primera versión de esta tabla tenía la fila GEM con una celda corrupta y un texto
ajeno, escritos por error al componerla. Queda registrado por `AGENTS.md`, que exige
preservar las contradicciones. La fila está corregida arriba; el sentido no cambió: `GEM`
es `DEFERRED`, eliminable en la etapa 1 e indispensable en la etapa 2.

### 2.2 Por qué DRM entra y el char device sale

`FACT`, verificado sobre el `.ko` con `nm`, no sobre el fuente:

- `rx550.ko`: **0** símbolos que contengan `pci_driver` o `pci_register_driver`.
  No es un driver PCI. No se registra en el bus. Es un char device con un ioctl.
- `rx550_drv.ko`: `U __pci_register_driver`, `U pci_unregister_driver`,
  `d rx550_pci_driver`, y el alias `pci:v00001002d0000699Fsv*sd*bc*sc*i*`.

Motivo de la sustitución, no preferencia de estilo: **un char device no puede dar a
userspace un BAR mapeado**, y el mapeo de BAR es la función que un driver de GPU existe
para ejercer. Conseguirlo sobre `char device` exigiría reimplementar a mano la
`mmap` que el core de DRM ya resuelve. El char device se conserva compilando y sus
pruebas siguen siendo válidas, pero deja de ser el camino principal.

## 3. Lo que el `.ko` demuestra y lo que no

`TEST` — todo por `make check-drivers`, reproducible, sin cargar nada:

| Comprobación | Tipo | Resultado |
|---|---|---|
| los 4 símbolos de PCI importables presentes | positiva | `OK` ×4 |
| `struct pci_driver` presente | positiva | `OK` |
| `rx550.ko` sin símbolos PCI | **negativa** | `OK` (0) |
| cero llamadas de mapeo en ambos `.ko` | **negativa** | `OK` (0 y 0) |
| alias de udev = `1002:699f` | positiva | `OK` |
| `depends` vacío | positiva | `OK` (`CONFIG_DRM=y`, DRM es built-in) |
| `vermagic` == `uname -r` | positiva | `OK` |

`rx550_drv.ko` 410544 B, `srcversion 7D43D72102CF6946F4C45D1`.
`rx550.ko` 372968 B, `srcversion 4EDF8A86EE8D7CB27714D7D`.

**Lo que ninguna de estas comprobaciones prueba:** que `probe()` se ejecute, que
`pci_request_regions()` tenga éxito, que los 4 BARs tengan el tamaño que el core
dice, o que `drm_dev_register()` cree el nodo. Todo eso es `NOT_TESTED` por
construcción: probarlo exige cargar el módulo, y en esta host amdgpu tiene el
dispositivo vinculado. Cargar exigiría unbind, que la directiva prohíbe sin
autorización.

## 4. Mapeo de MMIO — `BLOCKED`, con el bloqueo nombrado

Clasificación del bloqueo: `BLOCKER` para la etapa 2. No bloquea la etapa 1, que no lo
usa.

Por qué no se escribe el código de mapeo aunque el diagrama lo pida: el requisito de la
directiva es que **cada etapa tenga un discriminante verificable**, y una función de
mapeo que no se puede ejecutar no tiene ninguno. Escribirla sería escribir código
especulativo. Se documenta el diseño y se deja fuera.

Diseño previsto, para cuando se autorice:

- `pci_iomap_range(pdev, RX550_MMIO_INDEX, 0, len, "rx550-mmio")` con una lista blanca
  explícita, no un bucle sobre los 6 BARs. Mapear un BAR de I/O como si fuera memoria
  no falla de forma evidente.
- Prefetch y caché coherentes **no se pueden fijar sin conocer el hardware**: el
  `IORESOURCE_PREFETCH` que da el core describe la BAR, no la semántica de
  `readl`/`writel` sobre ella. Fijarlos a ciegas es exactamente el tipo de
  invención que la directiva prohíbe. `UNKNOWN` hasta que haya lectura directa de
  amdgpu para este ASIC, y eso es una lectura de fuente, no un supuesto.
- `devm_ioremap` o `devm_ioremap_resource` para que el unmape sea automático en
  `remove()`, por el mismo motivo que `devm_drm_dev_alloc`.

Autorización que lo resolvería: `RUNTIME_EXECUTION` para `insmod`, lo que a su vez exige
desvincular `amdgpu` del dispositivo. Son dos permisos distintos y el segundo sigue
prohibido.

## 5. Fuentes y su clase

Toda la evidencia de esta etapa es de lectura directa, sin privilegio y sin escritura.

| Dato | Fuente | Clase |
|---|---|---|
| `1002:699f`, `1002:0b04`, rev `0xc7` | `/sys/bus/pci/devices/0000:01:00.0/{vendor,device,subsystem_*,revision}` | `OBSERVED` |
| clase `0x030000` | atributo `class` de sysfs | `OBSERVED` |
| clase `0x0300`, nombre Lexa PRO | `lspci -nn -s 01:00.0` | `OBSERVED` |
| los mismos bytes de config space | `lspci -x` y el nodo `config` de sysfs, **idénticos byte a byte** | `OBSERVED` |
| bases y tipos de BAR | `lspci -x` (config space) **y** `/proc/bus/pci/devices`, **concordantes** | `OBSERVED` |
| `COMMAND = 0x0407` | config space | `OBSERVED` |
| `amdgpu` vinculado | `readlink /sys/bus/pci/devices/0000:01:00.0/driver` | `OBSERVED` |
| `CONFIG_DRM=y`, `CONFIG_PCI=y`, `CONFIG_DRM_AMDGPU=m` | `include/config/auto.conf` del árbol de build | `OBSERVED` |
| `PCI_STD_NUM_BARS=6` | `include/uapi/linux/pci_regs.h:37` | `OBSERVED` |
| campos de `drm_driver` (`.name` `.desc` `.major` `.minor` `.patchlevel`; **no** `.date` ni `.description`) | `include/drm/drm_drv.h:396-412` | `OBSERVED` |
| `.load`/`.unload` deprecados para drivers nuevos | `include/drm/drm_drv.h:189-192`, `:235-243` | `OBSERVED` |
| `DRM_MINOR_PRIMARY` en `drm_file.h` | `include/drm/drm_file.h:63` | `OBSERVED` |
| `devm_drm_dev_alloc(parent, driver, type, member)` devuelve el **tipo contenedor** | `include/drm/drm_drv.h:470-472` | `OBSERVED` |
| `pci_driver` usa `.remove`, no `.remove_new` | `include/linux/pci.h`, `struct pci_driver` | `OBSERVED` |
| número de bus = `pdev->bus->number`; `pci_bus_nr()` **no existe** en este árbol | `struct pci_bus` en `include/linux/pci.h` | `OBSERVED` |
| gcc del kernel 16.1.1, local 16.2.1 | aviso del propio build | `OBSERVED` |

## 6. Correcciones sobre el propio trabajo de esta etapa

Se registran porque son el resultado más transferible de la sesión: cada una de las
siguientes afirmaciones la compilación refutó.

1. **No existe `pci_bus_nr()`** en `7.1.3`. Escribí la llamada por analogía con
   versiones anteriores. `struct pci_bus.number` es el campo. `REFUTED` por el
   compilador; el campo existe en `include/linux/pci.h`.
2. **`IORESOURCE_MEM_PREFETCH` no existe.** El nombre real es `IORESOURCE_PREFETCH`
   (`include/linux/ioport.h:47`). Lo confundí con el `PCI_BASE_ADDRESS_MEM_PREFETCH`
   del espacio de usuario, que sí existe pero significa otra cosa.
3. **`drm_dev_register()` no recibe `DRM_MODE_CONNECT_NONE`** en este árbol. Ese
   símbolo no existe. El segundo argumento lo recibía `.load()`, que aquí no se
   rellena porque está deprecado, así que el valor correcto es `0`.
4. **`devm_drm_dev_alloc()` no devuelve `struct drm_device *`.** Devuelve el **tipo
   contenedor**: el macro es `((type *) __devm_drm_dev_alloc(parent, driver,
   sizeof(type), offsetof(type, member)))`. Pasé `sizeof(...)` donde esperaba el tipo.
5. **`drm_device` no expone `major` ni `minor` en la cabecera pública.** `grep` sobre
   `drm_device.h` no devuelve ninguno de los dos. El primer borrador los imprimía en un
   `dev_info`. No habría fallado al compilar si el campo hubiera existido; como no
   existe, era una afirmación sobre un dato que el driver no tiene.
6. **Los campos inexistentes de un inicializador designado no dan error de
   compilación, se ignoran en silencio.** Escribí `.description` y `.date` en
   `struct drm_driver`; el compilador los habría aceptado y descartado. Sólo lo detecté
   al listar los campos reales de la estructura. De aquí la regla que sigo en este
   fichero: los nombres de campo se verifican contra la cabecera, no contra el
   compilador.
7. **Class code: conflicto sin resolver, y deliberadamente no lo uso.** El nodo
   `config` de sysfs entrega 64 bytes, y en `0x09..0x0B` hay `00 00 03`, mientras el
   atributo `class` del mismo core dice `0x030000` y `lspci` dice clase `03`. No
   logré reconciliar la disposition de los tres bytes con la especificación PCI a
   partir de estas fuentes. `CONFLICT`, no resuelto, **y sin efecto**: el driver
   consume `pdev->class`, que el core ya dejó combinado en 24 bits, y no descodifica
   config space a mano. La regla que sale de esto: donde el core ya parseó algo, no
   re-parsear.
8. **Los tamaños de BAR sí se conocen**, contra mi expectativa inicial de
   `NOT_DETERMINED`. `pdev->resource[].end` lo calculó el core mediante el truco de
   escribir todos-unos en el BAR **durante la enumeración del bus**, no en runtime. La
   consecuencia correcta es que `rx550_bar_describe()` da longitudes reales sin que este
   driver escriba nada. `pci_request_regions()` no las necesita: por eso su
   clasificación de "puede fallar con `-EBUSY` en esta host" no es "`-EINVAL` por
   tamaño desconocido".

## 7. Límite de cobertura declarado

`/sys/bus/pci/devices/0000:01:00.0/resource{0,2,4,5}` existen pero devuelven
`Permission denied` sin privilegio. Estado según la tabla de "ausencia" de `AGENTS.md`:
**evidence denied**, no "el recurso no existe". Los inodos están presentes, lo que se
comprobó por listado del directorio. Consecuencia: la dirección y el tamaño que el
driver usa vienen del core en memoria, no de una lectura de este usuario. Ambas cosas
deben coincidir, y que coincidan **no está verificado** en esta etapa.
