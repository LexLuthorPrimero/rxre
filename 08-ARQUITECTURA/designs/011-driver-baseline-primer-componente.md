# 011 — Driver baseline y primer componente construible

> **Fase**: investigación → **construcción** (transición formal)
> **Fecha**: 2026-09-29
> **No abre** ningún frente de investigación. Cierra ninguno; los declara.

---

## 1. Frontera que se declara cerrada

Estos resultados dejan de ser trabajo en curso y pasan a ser baseline del proyecto.
Cada uno con su evidencia y su clasificación, sin upgraded de estado:

| propiedad | estado | evidencia |
|---|---|---|
| `WB_DOMAIN` | `PROVEN` | `amdgpu_object.c:156-161` (GTT → `TTM_PL_TT`), `amdgpu_object.h:161`, `amdgpu_object.c:559-560` |
| `GTT_PTE` | `PROVEN` | `amdgpu_vm.c:1356,1394-1396` → `amdgpu_ttm.c:1444-1456` → `gmc_v8_0.c:961,718-729` |
| `GPU_WRITE_VISIBILITY` | `STATICALLY_SUPPORTED` | PTE `READABLE\|WRITEABLE` sobre `TTM_PL_TT` (RAM de sistema) |
| `EMIT_MEM_SYNC` | `PROVEN` | `amdgpu_ib.c:235-236` → `gfx_v8_0.c:6761,6774,6913,6947,6986` |
| `RELEASE_MEM` | `PROVEN` | `gfx_v8_0.c:6239-6244` |
| `FENCE_DESTINATION` | `PROVEN` | `amdgpu_fence.c:117,175` → `ring->fence_drv.gpu_addr` (GTT) |
| `RMMIO_SIZE` | `PROVEN` | `0x40000` — identidad entre `pci-sysfs.c:1248` y `amdgpu_device.c:3814` |
| `MINIMAL_DISPATCH` | `READY` | `gfx_v9_4_2.c:385-409` |
| `COHERENCE` | `NOT_DETERMINED` | ver §5 |
| `POLARIS12 → GFX8` | `NOT_DETERMINED` | ver §6 |

### 1.1 Correcciones de esta ronda que se heredan

Dos afirmaciones previas resultaron ser inferencias y quedaron **refutadas** por el corpus.
No se arrastran:

```
"resource5 es la vía para cerrar coherencia"      → REFUTADO (fs/sysfs/file.c:100-101;
                                                    el EIO es estructural, no del dispositivo)
"el WB buffer depende del aperture de BAR5"       → REFUTADO (amdgpu_ib.c:358-360 → AMDGPU_GEM_DOMAIN_GTT)
```

Y una afirmación previa que **queda confirmada** y con la parte positiva añadida:

```
amdgpu_bo_sync            = reserva de fence        (CONFIRMADO)
invalidate_hdp            = host/MMIO, no VRAM     (CONFIRMADO)
ninguno de los dos toca RAM de sistema tras GTT    (CONFIRMADO por ausencia en la ruta)
```

---

## 2. Principio de diseño

```
AMDGPU = EVIDENCIA
AMDGPU ≠ ESPECIFICACIÓN
```

`amdgpu` es la mejor documentación disponible del hardware y de la API del kernel
para esta GPU. Es un **testigo**, no un plano. Un componente nuestro existe si
`amdgpu` lo hace, no porque `amdgpu` lo haga.

```
REFERENCE ≠ PRESERVATION
```

Copiar `struct amdgpu_device` porque existe no es diseño: es trasplantar la
arquitectura interna de otro proyecto, con su historia y sus workarounds
heredados, sin los requisitos que los justificaban.

### 2.1 Test de justificación de cada decisión

Una decisión de diseño se admite sólo si cae en al menos una de estas:

| clase | ejemplo | verificable por |
|---|---|---|
| `HARDWARE_REQUIREMENT` | el hardware obliga | corpus o ISA publicada |
| `KERNEL_REQUIREMENT` | el kernel lo exige | `Documentation/` del kernel en uso |
| `ABI_REQUIREMENT` | hay ABI documentado que hay que cumplir | uapi headers |
| `DEMONSTRATED_REQUIREMENT` | el experimento previo lo mostró | discriminante ejecutado |

Si no cae en ninguna: `DESIGN_FREEDOM = AVAILABLE`, y se elige libremente, dejando
constancia de que fue una elección y no una herencia.

### 2.2 Donde hay libertad, hoy

| elemento | estado | nota |
|---|---|---|
| nombre del módulo y de los símbolos | `DESIGN_FREEDOM = AVAILABLE` | elegido para no colisionar con `rx550` / `rx550_drv` |
| nombre de los campos de la `private_data` | `DESIGN_FREEDOM = AVAILABLE` | nada externo los referencia todavía |
| número de ficheros y su reparto | `DESIGN_FREEDOM = AVAILABLE` | una unidad, mientras el contrato lo permita |
| texto de `MODULE_DESCRIPTION` | `DESIGN_FREEDOM = AVAILABLE` | |
| política de logging | `DESIGN_FREEDOM = AVAILABLE` | se decide con el primer componente que lo necesite |
| contenido de la `private_data` | `DESIGN_FREEDOM = AVAILABLE` | en esta ronda: sólo identidad |
| mapa MMIO, orden de campos, unités | **no** es libertad todavía | `HARDWARE_REQUIREMENT` (BAR5) |
| tupla PCI a Recognize | **no** es libertad | `DEMONSTRATED_REQUIREMENT` (`amdgpu_drv.c:2041`) |
| API de probe/remove del kernel | **no** es libertad | `KERNEL_REQUIREMENT` |

---

## 3. ¿Qué se puede implementar AHORA?

La pregunta operativa, reformulada para que sea contestable:

> Un componente es construible ahora si se puede escribir su contrato, compilarlo
> contra el kernel exacto, y verificarlo **estáticamente** — sin hardware.

Con esa definición, casi todo el driver es construible. Lo que no es construible
es una clase distinta de componente: aquel cuyo **contrato sólo se puede
verificar con hardware**. Esos no se construyen todavía, pero su ausencia no
bloquea a los demás.

```
COMPONENTE                  CONSTRUIBLE AHORA     VERIFICABLE ESTATICAMENTE
─────────────────────────────────────────────────────────────────────────────
skeleton de módulo              sí                   sí
identidad PCI                   sí                   sí  (modinfo alias)
identificación CHIP_POLARIS12   sí                   sí  (modinfo alias, sub-device)
device object propio            sí                   sí  (nm, layout)
acceso MMIO encapsulado         sí                   sí  (nm: pci_iomap/ioremap presentes)
lifecycle init/teardown         sí                   sí  (nm: probe/remove)
logging / error handling        sí                   sí
─────────────────────────────────────────────────────────────────────────────────
VM completa                     no requiere COHERENCE, sí requiere PAGING
scheduler / ring submit         no requiere COHERENCE, sí requiere doorbell+shader
IB execution                    no  → requiere COHERENCE
shader execution / PM4          no  → requiere COHERENCE + hardware
userspace ABI                  no  → requiere submit
```

**Conclusión**: la única propiedad abierta (`COHERENCE`) no pertenece a ninguno de
los siete primeros componentes. No bloquea ninguno. Y no se investigará más hasta
que un componente la declare como requisito.

---

## 4. Matriz de componentes

`BLOQUEA` = el componente **no puede** escribirse. `RETRASA` = se puede escribir,
pero su contrato sólo se cierra con hardware.

| # | componente | requisitos demostrados | evidencia | UNKNOWN que bloquea | test estático |
|---|---|---|---|---|---|
| 1 | skeleton de módulo | kernel 7.1.3 con `CONFIG_MODULES=y` | `/usr/src/kernels/7.1.3-200.../.config` | — | `vermagic`, `modinfo` |
| 2 | identidad PCI | `0x1002:0x699F` es `CHIP_POLARIS12` | `amdgpu_drv.c:2041` | — | alias exacto en `modinfo` |
| 3 | id. `CHIP_POLARIS12` | la tupla identifica esa pieza, no la familia | `amdgpu_drv.c:2033-2041` (bloque `/* Polaris12 */`) | — | prefijo de alias |
| 4 | device object propio | contrato de `probe`/`remove` | `KERNEL_REQUIREMENT` | — | `nm`, tamaño de struct |
| 5 | MMIO encapsulado | BAR5 es la ruta MMIO post-Bonaire | `amdgpu_device.c:3812-3823` | **retrasa** el contenido | símbolos `pci_iomap` presentes |
| 6 | lifecycle init/teardown | `KERNEL_REQUIREMENT` | — | — | `nm`: `init`/`exit` |
| 7 | logging / errores | `DESIGN_FREEDOM` | — | — | `nm`: `pr_*` |

Sobre #5, precisado: **encapsular** el MMIO no está bloqueado. Escribirlo sí,
porque el contenido del registro que se leería y con qué máscara no está
decidido, y equivocarse ahí es escribir en hardware del mapping equivocado.

---

## 5. `COHERENCE` — clasificación explícita

```
COHERENCE = NOT_DETERMINED
```

Salto abierto, uno solo:

> Por qué un load cacheable de CPU (`PAGE_KERNEL`, `ttm_tt.c:526`;
> `pgtable_types.h:225` → `PTE_PCD=0, PTE_PWT=0`) observa una escritura de la GPU
> a la misma RAM, sin invalidación de caché de CPU en el path.

```
BLOCKS:
    validación de completitud GPU→CPU del write-back buffer
    IB execution
    shader execution con lectura de resultado en CPU

DOES_NOT_BLOCK:
    skeleton de módulo
    identidad PCI
    device object
    lifecycle
    MMIO encapsulation
    logging
```

```
MINIMAL_DISCRIMINANT (futuro, NO ejecutado)
    dma_fence_wait()  →  load de WB  →  observar valor
```

**Riesgo registrado de ese discriminante**: `gfx_v9_4_2.c:513` hace
`memset(wb_ib.ptr, 0, …)` antes de despachar. Con mapping write-back eso deja
líneas sucias en caché de CPU sobre exactamente las direcciones que el shader
escribirá. Si la capa de coherencia no se sostiene, el discriminante lee ceros y
eso **no** es evidencia de no-ejecución. Ese caso debe distinguirse
explícitamente de una lectura correcta.

Todo componente que necesite la propiedad declarará:

```
REQUIRED_EVIDENCE = COHERENCE
```

y sólo entonces se reabre el discriminante. No se adelanta ese trabajo.

---

## 6. `POLARIS12 → GFX8` — dos cosas distintas

```
CODE_FOR_POLARIS12_IN_GFX_V8   = STATICALLY_SUPPORTED
EXACT_DISPATCH_COMPOSITION    = NOT_DETERMINED
```

La primera: hay código escrito explícitamente para `CHIP_POLARIS12` dentro de los
drivers v8_0.

```
gmc_v8_0.c:140-141   case CHIP_POLARIS11: case CHIP_POLARIS12:
gfx_v8_0.c:783-784   case CHIP_POLARIS11: case CHIP_POLARIS12:
gmc_v8_0.c:590-592   /* all engines support GPUVM */
gfx_v8_0.c:983       adev->asic_type >= CHIP_POLARIS10 && <= CHIP_POLARIS12
```

La segunda: la composición exacta de la tabla de dispatch no está indexada por
`CHIP_POLARIS12`, sino por revisión de hardware leída de MMIO.

```
amdgpu_device.c:1994         amdgpu_discovery_set_ip_blocks(adev)
amdgpu_discovery.c:2786        switch (adev->asic_type) {
  case CHIP_VEGA10 … case CHIP_CYAN_SKILLFISH:   IP_VERSION(9,0,1) … (10,1,3)
  :3023  default:                                ← aquí cae POLARIS12
  :3037      amdgpu_discovery_init_soc_config(adev);
```

`soc15_hw_ip.h` **existe** (`drivers/gpu/drm/amd/include/soc15_hw_ip.h`, 106
líneas) pero sólo contiene los `*_HWID`. No contiene tabla de ASIC. El
`kernel-devel` del kernel en ejecución lo tiene podado a `Kconfig` + `Makefile`.

Esto **no es un bloqueo global**. Se investigará el día que un componente la
necesite como requisito real, no antes.

---

## 7. Identidad exacta de la tarjeta objetivo

Resuelta antes de escribir el componente. Sin hardware de la GPU: espacio de
configuración y metadatos del core de PCI, que es donde el dispositivo
**declara** su identidad. No es MMIO, no es un BAR, no cambia estado.

### 7.1 Lectura

```
/sys/bus/pci/devices/0000:01:00.0/config   (64 B, offsets del header tipo 0)
offset  valor        campo
0x00    0x1002       vendor_id
0x02    0x699F       device_id
0x08    0xC7         revision_id
0x0A    0x00         subclass
0x0B    0x03         class            -> 0x030000, VGA-compatible controller
0x2C    0x1002       subsystem_vendor
0x2E    0x0B04       subsystem_device
```

Corroborado por el core de PCI, que es la misma lectura por otra vía:

```
uevent:  PCI_ID=1002:699F
         PCI_SUBSYS_ID=1002:0B04
         PCI_CLASS=30000
MODALIAS pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00
```

### 7.2 Qué campo identifica la tarjeta

| campo | valor objetivo | ¿necesario para el match? | por qué |
|---|---|---|---|
| vendor | `0x1002` | **sí** | específico junto con device; solo, no discrimina nada |
| device | `0x699F` | **sí** | el campo más fino disponible que es específico de esta pieza |
| subsystem vendor | `0x1002` | **no** | idéntico al vendor: no añade un bit de información |
| subsystem device | `0x0B04` | **no — y usarla sería un ERROR** | ver abajo |
| revision | `0xC7` | **no** | `amdgpu_drv.c:2034-2041` pone `revision = 0` en las ocho filas; la revisión selecciona comportamiento, no identidad |
| class | `0x030000` | **no** | `0x03` es toda la clase VGA; no distingue |
| `asic_type` | `CHIP_POLARIS12` | **no para el match** | es una *consecuencia* del device ID, no un identificador |

### 7.3 El subsystem device no sirve, y es actively misleading

```
$ grep "0b04" /usr/share/hwdata/pci.ids
	1028 0b04  Radeon R9 360 OEM
	1002 0b04  Radeon RX 560
```

`0x0B04` con subsystem vendor `0x1002` es el **Radeon RX 560**. No es un
identificador de placa: es un código de modelo que el fabricante reutiliza entre
varias tarjetas de la misma familia.

Consecuencia: incluir `subsystem_device` en la condición de aceptación
**endurecería la condición con un valor que no identifica**. Daría la impresión
de un match más estricto cuando en realidad es semánticamente vacío — y peor,
ataría el driver a un código que el fabricante recicla.

Corroboración independiente: `amdgpu` tampoco lo usa. Sus ocho filas Polaris12
declaran `PCI_ANY_ID` en subvendor y subdevice (`amdgpu_drv.c:2034-2041`), y
`modinfo amdgpu` publica el alias con comodines:

```
alias: pci:v00001002d0000699Fsv*sd*bc*sc*i*
```

### 7.4 Contrato de matching

```
TARGET_MATCH =
	vendor == 0x1002
	&&
	device == 0x699F

REJECTED_DEVICE_BEHAVIOR =
	el kernel no llama a probe();
	el dispositivo queda served por otro driver o sin driver.

ALCANCE DE LA EXCLUSIVIDAD:
	PROVEN    a granularidad de PCI device ID: 0x699F es distinto de los
	          otros siete Polaris12 de amdgpu_drv.c:2034-2041
	          (0x6980 0x6981 0x6985 0x6986 0x6987 0x6995 0x6997)
	NOT_DETERMINED  a granularidad de placa fisica: que ningun otro board
	          del mundo reporte 1002:699F con otro subsystem
```

Esa última línea es un límite real y no se rellena por derivación:

- `0x699F` **no tiene entrada** en `pci.ids`, así que ninguna base de datos local
  enumera sus variantes de placa.
- Un device ID de SKU puede repartirse entre tarjetas de distintos fabricantes
  con subsystem IDs distintos. Nada en la evidencia local lo resuelve.

**Distinción que no debe colapsarse:**

```
"ningun otro board responde a esta tupla"   = hecho de hardware, NO PROBADO
"este driver soporta una sola tarjeta"       = decision de diseno, PROBADA
```

La segunda es la que el proyecto necesita, y se sostiene por construcción: el
driver matchea a granularidad de device ID, y su alcance declarado es una única
tarjeta. No afirma ser un driver para `CHIP_POLARIS12` ni para GFX8.

### 7.5 La cadena, sin invertirla

```
PCI DEVICE  1002:699F          PROVEN        config space + uevent
     ↓
TARGET GPU  la tarjeta 0000:01:00.0          por definición del proyecto
     ↓
ASIC ID     CHIP_POLARIS12     PROVEN        amdgpu_drv.c:2041
     ↓
POLARIS12                         cadena, no generalización
     ↓
GFX8         NOT_DETERMINED / STATICALLY_SUPPORTED
```

Nunca al revés. `GFX8 → Polaris12 → todas las RX 550` sería una
generalización no autorizada, y este diseño no la hace en ninguna dirección.

---

## 8. Área limpia de implementación

```
DRIVER_WIP_EXISTING  = 07-DRIVER/kernel/
                         rx550_drv.c, rx550_drv.h   (untracked, otra sesión)
                         STAGE1-SUBSYSTEMS.md        (untracked, otra sesión)
                         Makefile                    (modified, otra sesión)
                         rx550_drv.ko, rx550.ko      (build products)

DRIVER_CLEAN_WORKSPACE = 07-DRIVER/driver/          ← nuevo, sin colisión
```

Justificación de por qué `07-DRIVER/driver/` y no otro:

| candidato | por qué no |
|---|---|
| `07-DRIVER/kernel/` | **prohibido**: WIP de otra sesión, 2 ficheros untracked + 1 modificado |
| `07-DRIVER/build/` | vacío pero ignorado por git (`.gitignore:8 = **/build/`); es salida de build, no fuente |
| `07-DRIVER/firmware/` | vacío; su propósito es firmware, no fuente |
| `07-DRIVER/tests/` | contiene tests del driver existente (`test_pm4.c`, `test_firmware_*.c`): acoplar el driver nuevo ahí ata los dos proyectos |
| `07-DRIVER/userspace/` | contiene `librx550.c` del driver existente |
| `07-DRIVER/outgoing-reviews/` | correo saliente |

Nombre de módulo elegido: `rx550_pciid`. Los `.ko` en el repo son `rx550`,
`rx550_drv`, `amdgpu`, `nhwa`. No colisiona con ninguno, y **no** puede
reemplazar ni ser confundido con el módulo de la otra sesión.

---

## 9. Primer componente

### 9.1 Elección

```
FIRST_COMPONENT = identidad PCI
```

Un solo componente. No cinco.

**Por qué éste y no otro.** Los siete candidatos de la lista se ordenan por
cuánta evidencia ajena necesitan. El esqueleto de módulo es el que menos
necesita, pero no es verificable: un `.ko` que compila no demuestra nada sobre
el hardware. La identidad PCI es el punto más bajo de la escala que **sí** tiene
una tupla demostrada y **sí** produce una comprobación mecánica.

Concretamente: la tupla PCI es `PROVEN` en el corpus, y `modinfo` imprime el
alias que el kernel derivó de la `id_table`. Ese alias es el contrato, escrito a
mano en el `.ko` y legible desde fuera. No hace falta hardware para comprobarlo.

**Por qué no identidad `CHIP_POLARIS12` como componente separado.** No es
separado: el kernel ya codifica esa identificación en el alias, porque
`PCI_DEVICE(0x1002, 0x699F)` genera
`pci:v00001002d0000699Fsv*sd*bc*sc*i*`. Declarar la tupla es declarar la pieza.
Un componente que re-implemente la tabla de `amdgpu_drv.c` dentro de un `probe`
sería copiar una referencia sin requisito (`REFERENCE ≠ PRESERVATION`).

### 9.2 Contrato del componente

> El módulo declara una `id_table` de **exactamente una** entrada, igual a la
> tupla `0x1002:0x699F`. Su `probe` no accede al hardware: registra identidad
> vendor/device/subdevice/revision y almacena una `private_data` que contiene
> sólo esos cuatro valores. Su `remove` libera esa estructura y nada más.

Lo que el contrato **excluye**, y por tanto la lista de lo que el test debe
detectar si aparece:

```
pci_iomap / ioremap / ioread32 / iowrite32 / readl / writel
request_irq / dma_alloc_coherent
pci_enable_device / pci_set_master
WDOORBELL / doorbell_index
cgas_read / cgas_write
mmio reads de cualquier tipo
```

### 9.3 Lo que este componente NO es

No es un driver funcional. No hace `pci_enable_device`, no mapea BARs, no
reserva IRQ, no registra char device, no expone ioctl. `pci_register_driver()`
está presente en `module_init` — es la forma canónica de un módulo de kernel y
sin él no habría `probe` — pero **no se ejecuta**, porque el módulo no se carga.
Cargar el módulo ataría un driver al `0000:01:00.0` mientras `amdgpu` ya está
enlazado, y eso es exactamente lo prohibido en esta fase.

---

## 10. Restricción permanente de alcance

```
THE DRIVER IS EXCLUSIVE TO THE TARGET RX 550.
```

Esto es un **requisito del proyecto**, no una preferencia de estilo. No se
convierte en un driver genérico por reutilización, limpieza, "arquitectura
extensible" ni buenas prácticas, sin una decisión explícita y respaldada por
evidencia.

```
DRIVER_SCOPE               = SINGLE_TARGET_GPU
GENERIC_GPU_SUPPORT        = NO
POLARIS12_GENERAL_SUPPORT  = NO
GFX8_GENERAL_SUPPORT       = NO
```

La libertad de diseño de la sección 2.1 está **dentro** de este límite:

```
IMPLEMENTATION FREEDOM  →  TARGET = RX 550 OBJETIVO  →  NO GENERALIZATION
```

Dos consecuencias concretas para el código:

**No se crean abstracciones de familia.** Nada del tipo `amd_gpu_device`,
`gfx8_device`, `polaris_device`, `amd_ring`, `amd_gpu_ops` si su única razón de
ser es admitir más GPUs. La arquitectura representa las necesidades demostradas
de una tarjeta. Si aparece una segunda, es una decisión de diseño nueva.

**Si una implementación futura contradice esta restricción, se detiene el
trabajo y se reporta la contradicción** antes de seguir.

## 11. Estado de partida

```
runtime                = NOT_RUN
MODULE_LOADED          = NO
GPU_TOUCHED            = NO
staging                = EMPTY
commit                 = NO
COHERENCE              = NOT_DETERMINED
COHERENCE_BLOCKS_1st   = NO
POLARIS12→GFX8         = NOT_DETERMINED
POLARIS12→GFX8_BLOCKS_1st = NO
TARGET_GPU_IDENTITY    = PROVEN   (ver seccion 7)
TARGET_MATCH           = PROVEN   (seccion 7.4, granularidad device ID)
BOARD_UNIQUENESS       = NOT_DETERMINED  (seccion 7.4)
DRIVER_SCOPE           = SINGLE_TARGET_GPU
```

## 12. Componente 2 — lifecycle explícito


Cerrado sobre el mismo módulo, sin renombrarlo: la identidad del componente 1
queda intacta y su test sigue pasando.

### 12.1 Firma, verificada en los headers exactos

```
/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/linux/pci.h
  :1025   int  (*probe)(struct pci_dev *dev, const struct pci_device_id *id);
  :1026   void (*remove)(struct pci_dev *dev);
```

Es el segundo componente donde el build aporta evidencia y no Confirmación.
La firma clásica de `probe` — un solo argumento — no compila contra este
kernel. Se había escrito de memoria y el Makefile del árbol lo rechazó.

### 12.2 Lo que el lifecycle hace, y nada más

```
module_init
  └─ pci_register_driver
       └─ probe(pdev, id)
            ├─ TARGET_MATCH explícito  →  -ENODEV si no cuadra
            ├─ kmalloc                 →  -ENOMEM si falla
            ├─ inicializar todos los campos
            ├─ pci_set_drvdata         ← attach
            └─ return 0
       └─ remove(pdev)          [solo si probe devolvió 0]
            ├─ guard: sin estado → return
            ├─ pci_set_drvdata(pdev, NULL)   ← detach
            └─ kfree                         ← destroy + free
  └─ pci_unregister_driver        (module_exit)
```

`module_pci_driver()` se sustituyó por `module_init`/`module_exit` explícitos: el
ciclo de vida **es** el objeto del componente, y con una macro tendría que
deducirse de ella.

### 12.3 Ownership

Una sola política, declarada en la cabecera:

```
pci_dev
  └─ drvdata  (pci_set_drvdata / pci_get_drvdata)
       └─ struct rx550_target   kmalloc del driver
```

El `target` pertenece al driver desde el `return 0` de `probe` hasta el
`kfree` de `remove`. Antes no existe; después ya no existe. `remove` no asume
estado válido — tiene guard — aunque el kernel sólo llame tras un `probe`
exitoso.

### 12.4 Lo que NO se añadió, deliberadamente

El estado de software es un `struct rx550_target` con **dos** campos: el
back-pointer a `pci_dev` y la identidad del componente 1. No es el device
object del componente 3.

```
NO PCI_ENABLE_DEVICE      NO en esta fase: toca el dispositivo
NO PCI_REQUEST_REGIONS    NO en esta fase: reserva espacio de BAR
NO PCI_IOMAP / IOREMAP    NO en esta fase: no hay mapa
NO DMA / IRQ / DOORBELL   NO en esta fase: no hay ejecucion
NO PM / FIRMWARE          NO en esta fase
```

Ninguna de estas se añadió "por si acaso". La regla del proyecto: un componente
que no la necesita, no la lleva; si aparece una, se reporta antes de seguir.

### 12.5 Estado

```
DRIVER_LIFECYCLE        = PROVEN_STATICALLY
PROBE_SIGNATURE         = PROVEN   (pci.h:1025)
ERROR_UNWIND            = VERIFIED
REMOVE_SYMMETRY         = VERIFIED
MODULE_INIT_EXIT        = VERIFIED
TARGET_MATCH_UNCHANGED  = VERIFIED

BUILD        = PASS   (0 warnings del módulo)
STATIC_TESTS = PASS   (16/16)

COHERENCE_BLOCKS_LIFECYCLE        = NO
POLARIS12→GFX8_BLOCKS_LIFECYCLE   = NO
runtime = NOT_RUN   module_loaded = NO   GPU_TOUCHED = NO
```

Los tests declaran **sobre qué** comprueban (`HEADER`, `SOURCE`, `BINARY`), y
uno de ellos falló en la primera pasada: contaba `return -ENOMEM` como fuga
cuando es justamente el fallo de la asignación. El defecto estaba en el test.

### 12.6 Secuencia de construcción

```
[1] PCI TARGET IDENTITY        CLOSED
[2] DRIVER LIFECYCLE           CLOSED  ← este componente
[3] DEVICE OBJECT / OWNERSHIP   siguiente
[4] PCI RESOURCE ABSTRACTION
[5] MMIO ACCESS
[6] GPU INITIALIZATION
[7] COMMAND SUBMISSION
[8] GPU EXECUTION
```

Ninguno de los siguientes se adelanta porque exista código de referencia en
AMDGPU. AMDGPU sigue siendo evidencia técnica, no arquitectura.



---

## 13. Componente 3 — device object y modelo de propiedad de recursos

### 13.1 Hallazgo: un campo del componente 2 estaba injustificado

El componente 2 dejó el objeto así:

```c
struct rx550_target {
	struct pci_dev	*pdev;
	struct rx550_pciid	 id;	/* vendor, device, subsys_vendor,
					   subsys_device, revision — 5 campos */
};
```

La copia de identidad **se quitó**. No por gusto, sino por tres razones
verificables:

1. Esos valores son propiedades de `struct pci_dev`, que el core de PCI rellenó
   al enumerar, y son legibles en cualquier momento a través de `pdev`.
2. El core es dueño de `pdev` y lo mantiene vivo mientras el driver esté
   enlazado. Copiarlos al objeto no los protege de nada: crea una segunda fuente
   de verdad que puede divergir de la primera.
3. En esta fase el driver no los consulta después de `probe()`. La única lectura
   es la línea de log de probe, que puede leerlos de `pdev` en ese momento.

```
TARGET IDENTITY  ≠  DEVICE RUNTIME STATE

la identidad la posee el CORE
el objeto solo guarda la RELACION con el core
```

Objeto final: **un campo**.

```c
struct rx550_target {
	struct pci_dev		*pdev;	/* del core, no del driver */
};
```

Es exactamente el mínimo que el `FIELD/PURPOSE/OWNER/…` del encargo exige, y
cada campo tiene su justificación escrita. No hay MMIO, DMA, IRQ, rings,
doorbells, locks, workqueues, timers, fences, PM, firmware, VRAM, GTT ni TTM:
la ausencia es intencional y está anotada como tal.

### 13.2 Invariante añadido

`remove()` comprueba que el back-pointer sea el mismo dispositivo antes de
liberar:

```c
	if (target->pdev != pdev) {
		pci_err(pdev, "drvdata does not belong to this device\n");
		return;
	}
```

Sin esto, un `drvdata` que no fuera el esperado significaría liberar el estado
de otro dispositivo.

### 13.3 Lo que el driver NO da por supuesto

```
BEFORE_PROBE   el driver no publica nada
PROBE == 0     objeto asignado, inicializado, publicado; el driver es dueño
TRAS PROBE     drvdata solo se lee en remove()
REMOVE         recuperar, despublicar, destruir, liberar
TRAS REMOVE    no hay objeto
```

El driver **no** depende de que el core deje `drvdata` a `NULL` antes de
`probe()`. Esa semántica no es verificable en este árbol — `drivers/pci/` del
`kernel-devel` está podado a directorios, no a fuentes (`pci-driver.c` ausente) —
y no se necesita: la corrección viene de publicar sólo tras una asignación
exitosa, y de leer sólo en `remove()`, para el que el core sólo invoca tras un
`probe` que devolvió 0.

`pci_set_drvdata` sí es verificable: `include/linux/pci.h:2314-2317` es
`dev_set_drvdata(&pdev->dev, data)`, o sea escribe `dev->driver_data`.

### 13.4 Modelo de recursos: declarado y vacío

```
RESOURCE        MODELLED   ACQUIRED   RELEASED   DUEÑO FUTURO
PCI DEVICE      SI         NO         NO         el core de PCI
PCI REGIONS     SI         NO         NO         el driver
MMIO            SI         NO         NO         el driver
IRQ             SI         NO         NO         el driver
DMA             SI         NO         NO         el driver
```

Existe para que ningún componente posterior adquiera un recurso sin decidir
antes quién lo posee y quién lo libera, en orden inverso. La ausencia de
llamadas es comprobada por test, no por convención.

La máquina de estados `ABSENT → ALLOCATED → INITIALIZED → ATTACHED →
RESOURCE_ACTIVE → …` se queda **documental**. `RESOURCE_ACTIVE` no existe en el
código porque no hay recursos adquiridos; inventar un estado o un enum para una
ausencia de runtime sería inútil.

### 13.5 Un fallo de build no reproducible

Una primera invocación devolvió `rc=2` con 0 warnings reportados, y la
siguiente `rc=0`. Tres builds limpios consecutivos dieron `rc=0`. Se registra
como transitorio no reproducido, no como cerrado: si reaparece, la causa sigue
sin explicar.

### 13.6 Estado

```
COMPONENT_3            = COMPLETE
DEVICE_OBJECT          = PROVEN_STATICALLY
OBJECT_OWNERSHIP       = PROVEN_STATICALLY
DRVDATA_LIFETIME       = PROVEN_STATICALLY
ERROR_UNWIND           = VERIFIED
REMOVE_SYMMETRY        = VERIFIED
RESOURCE_MODEL         = VERIFIED
RESOURCE_ACQUISITION   = NONE
HARDWARE_ACCESS        = NONE
BUILD = PASS   WARNINGS = 0   STATIC_TESTS = 24/24
```

### 13.7 Los tests discriminan

Un test que sólo comprueba que un nombre está presente no detecta un defecto de
comportamiento. Se comprobó con mutación: cada defecto inyectado rompe el test
que corresponde, y sólo ese.

| mutación inyectada | tests que la detectan |
|---|---|
| `pci_set_drvdata(NULL)` movido después de `kfree` | `T7`, `T11` |
| campo nuevo en la struct sin inicializar | `T3` |
| lectura de `target->` después de `kfree` | `T8` |
| doble `kfree` | `T9` |
| `pci_enable_device()` añadido | `T13` |
| segundo device ID en la `id_table` | `I1` |

Las mutaciones se aplicaron sobre una copia en `/tmp`, no sobre el árbol.

Dos defectos del arnés se encontraron y corrigieron por el camino, ambos en el
test y no en el código:

- `at()`/`cnt()` pasaba patrones como regex a `awk`, donde `\(` no casa: la
  búsqueda devolvía cero en silencio y T2/T5/T7/T8 fallaban por la razón
  equivocada. Ahora usan `index()`, que es lo que corresponde a un token literal.
- T3 contaba el `};` de cierre de la struct como un campo, y T6b contaba
  `pci_get_drvdata` sobre el `.c` cuando el accessor vive en la cabecera.

### 13.8 Secuencia

```
[1] PCI TARGET IDENTITY        CLOSED
[2] DRIVER LIFECYCLE           CLOSED
[3] DEVICE OBJECT / OWNERSHIP  CLOSED  ← este componente
[4] PCI RESOURCE OWNERSHIP     siguiente
[5] MMIO ABSTRACTION
[6] HARDWARE ACCESS
```

No se pasa a (4) sin autorización. (4) es el primero que adquiere un recurso
físico, y por lo tanto el primero donde `probe()` dejaría de ser pasivo.

