# LÍNEA D — Minimal driver dependency map: qué tendría que existir para Polaris12

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 13
**Tipo**: `READ_ONLY/EVIDENCE` — lectura de código fuente. Cero escrituras a hardware, cero
  compilación, cero ejecución.
**Árbol de referencia**: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
**Estado de Q-5**: no tocado. `COORDINACION.md`: no tocado. Cerrojo de IA-2: no tocado.

---

## 0. Alcance y lo que NO es

Esto responde a la pregunta de la Línea D: *si mañana hubiera que escribir un módulo DRM mínimo
para Polaris12, ¿qué entidades reales del kernel habría que reproducir y cuáles no?*

**No** es un plan de implementación. **No** asume que el driver futuro deba copiar AMDGPU. Aplico
`IMPLEMENTATION_IS_NOT_AUTHORITY`: cada entrada dice qué hace el driver **actual**, y eso es
evidencia de **una** solución, no un requisito. Lo que el driver futuro necesitaría de verdad está
en la columna `REQUIRED` y se deriva de la naturaleza del hardware, no de lo que AMDGPU hace.

**No** cierro los huecos G-1/G-3/G-5: esos son líneas B y C (medición y ASM), de IA-2.

## 1. Hallazgo principal: Polaris12 **no tiene rama propia** en la selección de IP

Esto es lo contrario de lo que asumía el plan, y reduce el trabajo más de lo esperado.

```
amdgpu_drv.c:1827   static const struct pci_device_id pciidlist[] = {
amdgpu_drv.c:2041     {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
```

Y a partir de ahí, `CHIP_POLARIS12` **cae en la misma rama que Polaris10, Polaris11 y VegaM**:

```
amdgpu_device.c:1975  case CHIP_POLARIS12:
amdgpu_device.c:1987      adev->family = AMDGPU_FAMILY_VI;
amdgpu_device.c:1989      r = vi_set_ip_blocks(adev);
```

```
vi.c:2105  case CHIP_POLARIS10:
vi.c:2106  case CHIP_POLARIS11:
vi.c:2107  case CHIP_POLARIS12:
vi.c:2108  case CHIP_VEGAM:
vi.c:2109      amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
vi.c:2110      amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block);
vi.c:2111      amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);
vi.c:2112      amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
vi.c:2113      amdgpu_device_ip_block_add(adev, &sdma_v3_1_ip_block);
vi.c:2114      amdgpu_device_ip_block_add(adev, &pp_smu_ip_block);
...
vi.c:2121      amdgpu_device_ip_block_add(adev, &uvd_v6_3_ip_block);
vi.c:2122      amdgpu_device_ip_block_add(adev, &vce_v3_4_ip_block);
```

**Verificado y falso** el supuesto de que haría falta conocer la revisión exacta de Polaris12 para
elegir IP: **no hace falta**. La lista es la de la familia VI completa.

## 2. Segundo hallazgo: GMC v8.1 y SDMA v3.1 son *revisiones*, no implementaciones nuevas

Esto **colapsa dos incógnitas** y contradice una lectura natural de los nombres.

```
gmc_v8_0.c:1768   const struct amdgpu_ip_block_version gmc_v8_1_ip_block = {
gmc_v8_0.c:1769       .type = AMD_IP_BLOCK_TYPE_GMC,
gmc_v8_0.c:1770       .major = 8,  .minor = 1,  .rev = 0,
gmc_v8_0.c:1773       .funcs = &gmc_v8_0_ip_funcs,     <-- MISMA implementacion
```

```
sdma_v3_0.c:1693  const struct amdgpu_ip_block_version sdma_v3_1_ip_block = {
sdma_v3_0.c:1695      .type = AMD_IP_BLOCK_TYPE_SDMA,
sdma_v3_0.c:1696      .major = 3,  .minor = 1,  .rev = 0,
sdma_v3_0.c:1699      .funcs = &sdma_v3_0_ip_funcs,    <-- MISMA implementacion
```

`gfx_v8_0_ip_block` (`gfx_v8_0.c:7128-7134`) sí es `8.0.0` con `gfx_v8_0_ip_funcs`.

**Consecuencia para el driver futuro**: el conjunto de IP de la RX 550 es

| IP | versión declarada | implementación |
|---|---|---|
| GFX | 8.0.0 | `gfx_v8_0_ip_funcs` |
| GMC | 8.1.0 | `gmc_v8_0_ip_funcs` |
| SDMA | 3.1.0 | `sdma_v3_0_ip_funcs` |
| IH | `tonga_ih` | Tonga |
| SMU/PP | `pp_smu` | — |
| UVD | 6.3 | — |
| VCE | 3.4 | — |

**`.funcs` reusa el bloque de funciones mayor**: no hay un «SDMA v3.1» que estudiar. Hay «SDMA
v3.0», con la etiqueta 3.1 aplicada. Los ficheros `gmc_v8_1.c` y `sdma_v3_1.c` **no existen** —
verificado.

## 3. Mapa ASCII con evidencia en cada flecha

```
PCI device 1002:699f
│
│  amdgpu_drv.c:2041   {0x1002, 0x699F, ..., CHIP_POLARIS12}
▼
asic_type = CHIP_POLARIS12
│
│  amdgpu_device.c:1980   case CHIP_POLARIS12:   (agrupado con POLARIS10/11/VEGAM)
│  amdgpu_device.c:1987   adev->family = AMDGPU_FAMILY_VI;
│  amdgpu_device.c:1989   vi_set_ip_blocks(adev);
▼
vi_set_ip_blocks()                          [vi.c:2049]
│
│  vi.c:2109-2122   amdgpu_device_ip_block_add(...) x8
▼
ip_blocks[]  (lista ordenada de IP)
├── vi_common   --- registros y clocks y clocks de la familia VI
├── gmc_v8_1    ──> gmc_v8_0_ip_funcs        [gmc_v8_0.c:1768-1774]
├── tonga_ih    ──> interrupciones
├── gfx_v8_0    ──> gfx_v8_0_ip_funcs        [gfx_v8_0.c:7128-7134]
├── sdma_v3_1   ──> sdma_v3_0_ip_funcs       [sdma_v3_0.c:1693-1700]
├── pp_smu      ──> power management
├── uvd_v6_3 / vce_v3_4  (vidéo; irrelevante para compute)
│
│  amdgpu_discovery.c:634  amdgpu_discovery_init()   (sobrevive: valida IPs contra la tabla)
▼
per-IP: early_init / late_init
│
│  soc15.c:958   soc15_common_early_init()
│  soc15.c:1229  soc15_common_late_init()
│
│  NOTA: soc15.c NO contiene la cadena POLARIS12 (verificado: 0 ocurrencias).
│        El despacho es genérico soc15; Polaris12 se distingue por rev leido
│        del IP discovery, no por un case por chip.
▼
─────────────────── superficie de usuario ───────────────────
DRM device
│
│  amdgpu_drv.c:2364  amdgpu_pci_probe()
│  amdgpu_drv.c:2435  drm_dev_register(ddev, flags)
▼
├─► GEM (objetos de buffer)
│     amdgpu_gem.c:166  amdgpu_gem_object_create()
│     amdgpu_gem.c:191  amdgpu_bo_create_user()
│     amdgpu_gem.c:1285 amdgpu_gem_object_create() desde el ioctl de userspace
│
├─► TTM (gestor de memoria)
│     amdgpu_ttm.c:2066  amdgpu_ttm_init()
│     amdgpu_ttm.c:2073  ttm_device_init(&adev->mman.bdev, &amdgpu_bo_driver, ...)
│
├─► VM (espacio de direcciones GPU)
│     amdgpu_vm.c:2608   amdgpu_vm_init()
│     amdgpu_vm.c:2629   amdgpu_vm_init_entities()
│     amdgpu_vm.c:539    amdgpu_vm_init_entities()  (definicion)
│
└─► Ring (submission)
      amdgpu_ring.c:226  amdgpu_ring_init(adev, ring, ...)
```

## 4. Clasificación REQUIRED / OPTIONAL / GENERIC / POLARIS12-SPECIFIC / NOT_DETERMINED

| Entidad | Clase | Evidencia | Nota |
|---|---|---|---|
| Reconocer `1002:699f` | `POLARIS12-SPECIFIC` | `amdgpu_drv.c:2041` | única aparición de `0x699F` en el driver, junto a `amdgpu_atpx_handler.c:571` que es un quirk de plataforma, no de enumeración |
| Asignar IP blocks | `GENERIC` | `amdgpu_device.c:1989` → `vi.c:2105-2123` | Polaris12 comparte rama con P10/P11/VEGAM |
| `gfx_v8_0` | `POLARIS12-SPECIFIC` (por versión) | `gfx_v8_0.c:7128` | GFX8 es el hecho de la arquitectura Polaris12/GFX8 |
| `gmc_v8_1` → `gmc_v8_0_ip_funcs` | `GENERIC` | `gmc_v8_0.c:1773` | reutiliza implementación |
| `sdma_v3_1` → `sdma_v3_0_ip_funcs` | `GENERIC` | `sdma_v3_0.c:1699` | reutiliza implementación |
| `drm_dev_register` | `REQUIRED` para un módulo DRM | `amdgpu_drv.c:2435` | el núcleo de la API de userspace |
| GEM / `drm_gem_object_init` | `REQUIRED` si hay objetos de buffer | `amdgpu_gem.c:166` | el driver futuro necesita un tipo de objeto con backing |
| TTM | **`OPTIONAL`** | `amdgpu_ttm.c:2073` | TTM es el gestor de memoria *de upstream*; un driver propio podría usar VRAM directo. **Es evidencia de cómo AMDGPU resuelve, no requisito** |
| VM / direcciones GPU | `REQUIRED` para compute | `amdgpu_vm.c:2608` | sin traducción de direcciones no hay buffer visible |
| Ring / entity de submission | `REQUIRED` para compute | `amdgpu_ring.c:226` | `amdgpu_ring_init` es la función de nivel superior; el scheduler (`drm_sched`) **no verificado en esta ronda** |
| IH (interrupciones) | `NOT_DETERMINED` | `tonga_ih_ip_block` añadido, no analizado | no investigué si un submit sin IRQ es viable |
| Firmware (PSP/SMU) | `NOT_DETERMINED` | — | `F4-AD-6` sigue `BLOQUEADO` y depende de IA-1; no lo toqué |
| MMIO / BAR | `NOT_DETERMINED` | `vi.c:297-340` muestra accesos indirectos a PCIE/SMC vía `mmPCIE_INDEX` | **no** es el MMIO directo de un BAR; es un proxy de registers. No investigué el mapa BAR |
| `struct amdgpu_bo` | `NOT_DETERMINED` | el grep de la definición en `amdgpu.h` **no devolvió nada** con mi patrón | pendiente, no lo afirmo |
| UVD / VCE | `OPTIONAL` para este proyecto | `vi.c:2121-2122` | el objetivo es compute |
| DC / DCE | `OPTIONAL` | `vi.c:2117-2120` bajo `CONFIG_DRM_AMD_DC` | |

### `POLARIS12-SPECIFIC` — el recuento completo

De todo lo que investigué, **lo único que depende de Polaris12 por nombre** es la entrada de la
tabla PCI. El resto es familia VI, o versión de IP, o genérico. Esto **no** significa que el
hardware no difiera: significa que **el código de upstream no lo distingue**, y por tanto no
sabemos todavía en qué se diferencia realmente. Eso es `NOT_DETERMINED`, no «son iguales».

## 5. Gaps que se cierran y gaps que quedan

### Cerrados en esta ronda

| Gap | Antes | Ahora |
|---|---|---|
| Qué IP tiene la RX 550 | desconocido / supuesto por nombre de ASIC | **lista exacta** con `archivo:línea` para los 8 bloques |
| Si «v8_1» y «v3_1» son código nuevo | `NOT_DETERMINED` | **NO**: reutilizan `gmc_v8_0_ip_funcs` y `sdma_v3_0_ip_funcs` |
| Si Polaris12 tiene init propia | supuesto implícito | **NO**: comparte rama con P10/P11/VEGAM |
| Dónde se decide la lista de IP | `NOT_DETERMINED` | `amdgpu_device.c:1989` → `vi.c:2049` |
| Dónde se registra el DRM device | `NOT_DETERMINED` | `amdgpu_drv.c:2364` (probe) → `:2435` (`drm_dev_register`) |
| Dónde se crea un BO | `NOT_DETERMINED` | `amdgpu_gem.c:166` `amdgpu_gem_object_create()` |

### Abiertos

| Gap | Estado |
|---|---|
| Mapa BAR y qué registers son accesibles por MMIO directo | `NOT_DETERMINED` |
| `struct amdgpu_bo`: definición y ciclo de vida | `NOT_DETERMINED` (mi grep falló; no lo afirmo) |
| Scheduler: `drm_sched_entity_init` y su relación con el ring | `NOT_DETERMINED` |
| Si un submit sin IRQ es viable (pregunta `P-8`) | `NOT_DETERMINED` |
| PSP/SMU: qué secuencia de arranque es imprescindible | `BLOQUEADO` en `F4-AD-6`, depende de IA-1 |
| VRAM vs GTT: dónde se decide | `NOT_DETERMINED` |

## 6. Trabajo redundante que debe evitarse

| Evitar | Por qué |
|---|---|
| Estudiar «SDMA v3.1» o «GMC v8.1» como código nuevo | `sdma_v3_0.c:1699` y `gmc_v8_0.c:1773` prueban que reutilizan `.funcs` de la versión mayor. Un estudio separado de v3.1 seria estudiar una etiqueta |
| Buscar una rama `CHIP_POLARIS12` en `amdgpu_discovery.c` | **0 ocurrencias** verificadas. La discovery es genérica soc15 |
| Planear TTM como requisito | `OPTIONAL`: es la solución de upstream, no una necesidad del hardware |
| Reestudiar la ruta de submit | Ya existe: findings `011-compute-submit-path.md` y `013-real-submit-path-polaris12.md` en `06-INGENIERIA-INVERSA/`. **No lo he releído**, así que no afirmo que cubran lo que yo encontré; lo señalo como candidato a extender en vez de duplicar |

## 7. IDEA — registrada, **no** implementada

```
IDEA
  el mapa de IP de Polaris12 es el de la familia VI, sin revisión propia
↓
PREGUNTA
  ¿qué distingue realmente a Polaris12 de Polaris10/11 a nivel de siliconio,
     si el driver no lo distingue?
↓
EVIDENCIA EXISTENTE
  vi.c:2105-2123  (rama compartida) · gmc_v8_0.c:241-244 (chip_name polaris12_k por ASICID_P23)
↓
FALTANTE
  revisión de siliconio por ASICID; el diff de registros no está medido
↓
DISCRIMINANTE
  amdgpu_i2c / lectura de registers de revision, o comparar el dump de
  GFX version register entre P10, P11 y P12
↓
FUTURO EXPERIMENTO
  lectura de ASICID/revision (NO requiere carga de GPU; sysfs ya lo expone)
```

**No lo implemento.** Requiere decidir si leer registros es autorizado, y no lo es sin
autorización expresa.

## 8. Procedencia — según `F4-AD-24`/`F4-AD-26`

| Dato | Grado | Cómo se obtuvo |
|---|---|---|
| `0x699F → CHIP_POLARIS12` | `MEASURED` | `grep -n` sobre `amdgpu_drv.c` |
| `CHIP_POLARIS12` sin rama de IP propia | `MEASURED` | lectura de `amdgpu_device.c:1975-1990` y `vi.c:2103-2123` |
| `.funcs` reusa v8.0/v3.0 | `MEASURED` | lectura de `gmc_v8_0.c:1768-1774`, `sdma_v3_0.c:1693-1700` |
| `gmc_v8_1.c` y `sdma_v3_1.c` no existen | `MEASURED` | `ls` → No existe |
| `POLARIS12` ausente de `soc15.c` y de `amdgpu_discovery.c` | `MEASURED` | `grep -c` → 0 en ambos |
| Cadena DRM register | `MEASURED` | `grep -n` sobre `amdgpu_drv.c` |
| Cadena GEM/BO | `MEASURED` | `grep -n` sobre `amdgpu_gem.c` |
| Cadena TTM | `MEASURED` | `grep -n` sobre `amdgpu_ttm.c:2066-2073` |
| Cadena VM | `MEASURED` | `grep -n` sobre `amdgpu_vm.c` |
| Cadena ring | `MEASURED` | `grep -n` sobre `amdgpu_ring.c:226` |
| Que el árbol es el del host vivo | **`NOT VERIFICADO`** | el router registra `HOST-C` con kernel `7.1.3-fc44` y el árbol es `linux-7.1.3`, pero no comprobé que sea el mismo commit. `DECLARED` por correspondencia de versión |
| Todo lo de MMIO/BAR, `amdgpu_bo`, scheduler, IRQ, PSP/SMU | `NOT_DETERMINED` | no investigado en esta ronda |
| Los findings `011`/`013` de IA-1 | **no leídos** | no los abrí; no afirmo su cobertura |

**Límite de esta ronda**: investigación estática. No se midió nada en hardware, no se compiló, no
se ejecutó. Un mapa estático de un driver **actual** no establece qué necesita un driver
**futuro**; establece qué existe hoy y, por tanto, qué habría que re-derivar.
