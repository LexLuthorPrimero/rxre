# INVENTARIO-ESTRUCTURAL-7.2.8.md — Inventario estructural de `drivers/gpu/drm/amd`

**FASE:** primera de la secuencia del brief. **Alcance:** estructural, no
semántico. **No** clasifica `KEEP`/`REMOVE`/`REWRITE`. No se ha escrito ni
modificado una línea de driver.

## Provenance

| Campo | Valor |
|---|---|
| `TARBALL` | `linux-7.2.8.tar.xz` |
| `SHA256` | `12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941` |
| `SHA256_VERIFICADO_CONTRA` | `cdn.kernel.org/pub/linux/kernel/v7.x/sha256sums.asc` (coincide) |
| `PGP` | **NO VERIFICADO** — no se validó la firma sobre `sha256sums.asc`. `NOT_AVAILABLE` |
| `ORIGEN` | `https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.2.8.tar.xz` · HTTP 200 · `application/x-xz` · 160 371 176 B · magic `fd377a585a00` = XZ |
| `FECHA` | 2026-09-28 |
| `REFERENCIA_INMUTABLE` | `RX550-INVESTIGACION/rx550-upstream-7.2.8/` — 2 842 ficheros, 691 MB, `mtime` 2026-09-28 02:53:07, **no modificada** |
| `ARBOL_ANALISIS` | `/home/lucas/rx550-analysis-7.2.8/linux-7.2.8/` — **fuera del repositorio**, para no poder tocar el índice de git |
| `EXTRACCION` | 12 subárboles, 14 574 ficheros, 690 MB |
| `WORK_CLASS` | `READ_ONLY/EVIDENCE` + `DOCUMENTATION` |

### BASELINES — tres, mezclados nunca

| id | qué es | dónde |
|---|---|---|
| `BASELINE-A` | kernel **en ejecución** 7.1.3-200.nobara.fc44 | host vivo |
| `BASELINE-B` | **fuente de estudio** 7.2.8 | `rx550-analysis-7.2.8/` |
| `BASELINE-C` | **amdgpu upstream 7.2.8 sin modificar** | `RESEARCH/baseline/linux-7.1.3/` (7.1.3, manifest `EXIT=0`, 2 787/2 787) y el tarball de 7.2.8 |

## Layout — hallazgo de estructura que condiciona todo

`drivers/gpu/drm/amd/` **no tiene ficheros en su raíz**: ni `Makefile`, ni
`Kconfig`, ni `.c`. Verificado contra el tarball (0 miembros en
`amd/[^/]+$`) y contra el baseline 7.1.3 sellado (misma estructura, y su
manifest confirma que esos ficheros no existen).

```
drivers/gpu/drm/Kconfig:303   source "drivers/gpu/drm/amd/amdgpu/Kconfig"
drivers/gpu/drm/Makefile:177  obj-$(CONFIG_DRM_AMDGPU)+= amd/amdgpu/
drivers/gpu/drm/Makefile:178  obj-$(CONFIG_DRM_AMDGPU)+= amd/amdxcp/
```

`amd/` no construye nada: agrupa. La unidad construible es `amd/amdgpu/`, y
sus hermanos se referencian con rutas relativas (`Makefile:314` `AMDACPPATH :=
../acp`, `Makefile:346` `AMD_GPU_RAS_PATH := ../ras`).

**TTM tampoco tiene Kconfig propio:** `CONFIG_DRM_TTM` vive en
`drivers/gpu/drm/Kconfig:198` y `CONFIG_DRM_TTM_HELPER` en `:250`.

## 1. Inventario por directorio

Unidad `LINES` = líneas de `.c` + `.h` + `.S`. Unidad `CHIPS` = tokens
`CHIP_*` **distintos**.

| PATH | FILES | LINES | % del total | HARDWARE GENERATION | STATUS |
|---|---:|---:|---:|---|---|
| `amd/amdgpu` | 631 | 386 857 | 6,1 % | ALDEBARAN, ARCTURUS, CYAN_SKILLFISH, NAVI10, NAVI12, NAVI14, POLARIS10/11/12, SIENNA, VEGA10/12/20 | inventariado |
| `amd/display` | 1 166 | 592 729 | 9,3 % | NAVI12, POLARIS10/11/12, VEGA10/12/20 | inventariado |
| **`amd/include`** | 564 | **5 116 394** | **80,6 %** | 178 tokens `CHIP_*` | inventariado |
| `amd/pm` | 273 | 185 443 | 2,9 % | POLARIS10/11/12, VEGA10/12/20 | inventariado |
| `amd/ras` | 56 | 14 381 | 0,2 % | ninguna referencia | inventariado |
| `amd/acp` | 2 | 83 | 0,0 % | ninguna | inventariado |
| `amd/amdkfd` | 62 | 48 185 | 0,8 % | ALDEBARAN, ARCTURUS, GC_9, GC_12, NAVI10, POLARIS10/11/12, SIENNA | inventariado |
| `amd/amdxcp` | 2 | 187 | 0,0 % | ninguna | inventariado |
| **`amd/` TOTAL | **2 756** | **6 344 259** | 100 % | — | — |

**El dato estructural más importante de esta fase:** `amd/include` es el
**80,6 %** de todas las líneas, y son definiciones de registros ASIC
generadas — 178 chips distintos, desde Polaris hasta RDNA4. Para un driver
exclusivo de RX 550, ese es el coste de generalidad más grande y el más
fácil de acotar. **No implica que deba borrarse**; implica que su natalidad
está medida.

### Dependencias de configuración

`amd/amdgpu/Kconfig:3`

```
config DRM_AMDGPU
	tristate "AMD GPU"
	depends on DRM && PCI
	select FW_LOADER, DRM_CLIENT, DRM_CLIENT_SELECTION,
	select DRM_DISPLAY_{DP,DSC,HDMI,HDCP}_HELPER, DRM_DISPLAY_HELPER,
	select DRM_KMS_HELPER, DRM_SCHED, DRM_TTM, DRM_TTM_HELPER,
	select POWER_SUPPLY, HWMON, I2C, I2C_ALGOBIT, CRC16,
	select BACKLIGHT_CLASS_DEVICE, INTERVAL_TREE, DRM_BUDDY,
	select DRM_SUBALLOC_HELPER, DRM_EXEC, DRM_PANEL_BACKLIGHT_QUIRKS,
	select INPUT if ACPI, ACPI_VIDEO if ACPI,
	select X86_PLATFORM_DEVICES if ACPI && X86, ACPI_WMI if ACPI && X86
```

Dos `depends on` y **23 `select`**. Un `select` es una dependencia dura: el
driver no compila sin ellas.

Sub-opciones: `DRM_AMDGPU_SI` (:41), `DRM_AMDGPU_CIK` (:56),
`DRM_AMDGPU_USERPTR` (:75).

### Entry points — `amd/amdgpu/amdgpu_drv.c`

| línea | símbolo | papel |
|---:|---|---|
| 2 217 | `static const struct drm_driver amdgpu_kms_driver;` | declaración adelantada |
| 3 097 | `static const struct drm_driver amdgpu_kms_driver = {` | **operación DRM** |
| 3 125 | `const struct drm_driver amdgpu_partition_driver = {` | driver de partición |
| 3 162 | `static struct pci_driver amdgpu_kms_pci_driver = {` | **operación PCI** |
| 3 168 | `.driver.pm = pm_ptr(&amdgpu_pm_ops),` | enganche a `drivers/base/power` |
| 3 199 | `pci_register_driver(&amdgpu_kms_pci_driver)` | **punto de entrada del módulo** |
| 3 209 | `pci_unregister_driver(&amdgpu_kms_pci_driver)` | salida |

`CALLERS` y `CALLEES` por directorio: **`UNKNOWN`**. No se extrajeron con
ninguna herramienta. Método pendiente: `cscope`/`ctags` sobre el árbol
completo, o el mapa de símbolos del propio `.ko` ya compilado en
`RESEARCH/kernelbuild/`. **No se rellena a ojo.**

## 2. Fase 4 — generalidad removable, vía configuración

`amd/amdgpu/Makefile:81-85`

```make
amdgpu-$(CONFIG_DRM_AMDGPU_CIK)+= cik.o cik_ih.o \
	dce_v8_0.o gfx_v7_0.o cik_sdma.o uvd_v4_2.o vce_v2_0.o

amdgpu-$(CONFIG_DRM_AMDGPU_SI)+= si.o gmc_v6_0.o gfx_v6_0.o si_ih.o si_dma.o dce_v6_0.o \
	uvd_v3_1.o vce_v1_0.o
```

**15 objetos** (7 CIK + 8 SI) están detrás de dos flags. CIK = Sea Islands
(Carrizo), SI = Southern Islands (Tonga). **Ninguno es alcanzable para
Polaris 12**, y los cinco ficheros raíz existen en 7.2.8.

**Esto no es un `REMOVE`.** Es un hecho estructural con un mecanismo
concreto: **no habilitar los flags en `.config`**, sin tocar código. La
distinción importa: borrar ficheros y no compilar ficheros tienen
consecuencias de mantenimiento distintas.

## 3. Las nueve relaciones

`OBLIGATORIA` = la interfaz del kernel la exige. `OPCIONAL` = el driver puede
existir sin ella. `UNKNOWN` = no establecido en esta fase.

| # | relación | interfaz | estado |
|---|---|---|---|
| H | AMDGPU ↔ DRM | `struct drm_driver`; `depends on DRM` | **OBLIGATORIA.** Un driver de GPU usable por un compositor *es* un driver DRM. `Kconfig:5`, `amdgpu_drv.c:3097` |
| I | AMDGPU ↔ TTM | `select DRM_TTM`, `DRM_TTM_HELPER`; 30 ficheros, 11 277 líneas | **OBLIGATORIA en la configuración actual.** `ttm/Makefile`: `ttm_tt, ttm_bo, ttm_bo_util, ttm_bo_vm, ttm_module, ttm_execbuf_util, ttm_range_manager, ttm_resource, ttm_pool, ttm_device, ttm_sys_manager, ttm_backup` (+ `ttm_agp_backend` si `CONFIG_AGP`). Si TTM es sustituible, no es por *recorte*, sino por diseño alternativo: `UNKNOWN` |
| J | AMDGPU ↔ GEM | `select DRM_BUDDY`, `DRM_SUBALLOC_HELPER` | **`UNKNOWN`** — no se localizó el punto de integración |
| K | AMDGPU ↔ GPUVM | no extraído | **`UNKNOWN`** |
| L | AMDGPU ↔ scheduler | `select DRM_SCHED` (`Kconfig:15`) | **`UNKNOWN`** si es obligatorio para un driver solo de display |
| M | AMDGPU ↔ PCI | `depends on PCI`; `pci_driver` y `pci_register_driver` | **OBLIGATORIA** |
| N1 | AMDGPU ↔ runtime PM | `.driver.pm = pm_ptr(&amdgpu_pm_ops)`; `drivers/base/power` (15 ficheros) | **OBLIGATORIA** |
| N2 | AMDGPU ↔ política de energía de la GPU | `amd/pm/` — 273 ficheros, 185 443 líneas | **OBLIGATORIA para la RX 550**: es la pila PowerPlay `smu7` que la maneja. **No confundir N1 con N2**: runtime PM del subsistema ≠ DPM del siliconio |
| O | AMDGPU ↔ firmware | `select FW_LOADER`; `amdgpu_ucode.c`, `amdgpu_cgs.c`, tablas ATOM | **`UNKNOWN`** — no se comprobó qué firmware hay en `/lib/firmware/amdgpu/` ni cuál carga |
| P | AMDGPU ↔ display | `amd/display/` — 1 166 ficheros, 592 729 líneas; `select DRM_KMS_HELPER` + 5 helpers | **`HUMAN_POLICY` requerido** — ver §5 |

## 4. Hardware registrado como FACT

Con la separación exigida:

| capa | valor | clase |
|---|---|---|
| `GPU_CAPABILITY` | `1002:699f` rev **`0xc7`**, Polaris 12 / GFX8, VRAM 2 147 483 648 B (2 048 MiB), visible 268 435 456 B | FACT |
| `GTT` | 6 194 638 848 B (~5,9 GiB) | FACT |
| `PCI_LINK_CAPABILITY` | 8,0 GT/s ×8 (Gen3) — lo que anuncia el dispositivo | FACT |
| `CURRENT_LINK_STATE` | 5,0 GT/s ×4 (Gen2) | **OBSERVATION** |
| `MOTHERBOARD/CPU_LIMITATION` | controlador Haswell | **`INFERRED`** — no medido. Lo que lo establecería: la capacidad de enlace del puerto raíz PCIe |
| `DRIVER_CONFIGURATION` | parámetros `pcie_*` de amdgpu | **`NOT_DETERMINED`** — no leídos |
| `CPU` | Intel i7-4790, 4c/8t, 3,60 GHz nominal, 4 000 MHz máx | FACT |
| `RAM` | 12 098 908 kB ≈ **11,3 GiB** | FACT |
| `KERNEL` | 7.1.3-200.nobara.fc44 · Mesa 26.2.3 | FACT |
| `STORAGE` | 2 discos rotacionales; `/` = ext4 en `sdb3`; **btrfs de 452 GB sin montar en `sda2`** | FACT |

**No** se afirma en ningún sitio que PCIe sea el cuello de botella. H-PCIE
queda como hipótesis con su experimento `EXP-PCIE-BANDWIDTH-REAL` sin ejecutar.
GTT sigue siendo `OBSERVATION`: no se ha medido uso real, evictions ni
migraciones.

## 5. Una decisión de requisito que te corresponde a ti

Observación, no decisión: el panel activo está en la **Intel** (`card0-HDMI-A-1
connected`); la RX550 declara `DVI-D-1` y `HDMI-A-2` **ambos desconectados**, y
es `boot_vga=1`.

De ahí sale `P` — 1 166 ficheros y 592 729 líneas de display. Para un driver
exclusivo de esta máquina, la pregunta es:

> **¿Debe la RX 550 poderafiaPilotar un monitor alguna vez?**

- Si **sí** → KMS/display es obligatorio, y las 592 729 líneas se quedan.
- Si **no** → es peso muerto, y es el bloque más grande eliminable después de
  `amd/include`.

Eso no lo deduce el código: es una decisión de requisito, y por tanto tuya.
`boot_vga=1` significa además que la RX550 se inicializa al arrancar, así que
"no la vamos a usar para display" no elimina la ventana de riesgo en boot.

## 6. Estado

| | |
|---|---|
| Lo demostrado | layout real del árbol; 2 756 ficheros / 6 344 259 líneas por directorio; 23 `select` + 2 `depends on`; entry points; 15 objetos detrás de 2 flags de generación; `amd/include` = 80,6 % del total; separaciones de hardware |
| Lo que falta | `CALLERS`/`CALLEES`; relaciones J, K, L, O; firmware presente; `DRIVER_CONFIGURATION` de PCIe; `MOTHERBOARD_CPU_LIMITATION` medido; **cualquier medición** |
| Clasificaciones semánticas | **ninguna**, por diseño de esta fase |
| Código modificado | **0** |
| Experimentos ejecutados | **0** |
