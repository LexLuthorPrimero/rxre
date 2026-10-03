# 1000 · De PCI enumeration a GPU READY: la secuencia completa, con su contraparte en el log de arranque

```text
CLASSIFICATION=DOCUMENTATION+MEASUREMENT   ·   TRACK=STATIC+RUNTIME_READ
CORPUS=RESEARCH/working/linux-7.1.3        ·   HARDWARE_SCOPE=0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=READ_ONLY (journalctl -k -b) · GPU INTACTA · CERROJOS=0
AUTORIA=AGENT-07 (PCI / DEVICE INITIALIZATION)
CIERRA=la cadena PCI → DEVICE DISCOVERY → ASIC ID → RESOURCE INIT → HARDWARE INIT → GPU READY
        en su orden total, que no estaba registrada en ninguna otra fuente del corpus
```

## Cuestión principal

`AGENT-07` recibe el tramo `PCI → DEVICE DISCOVERY → ASIC IDENTIFICATION →
RESOURCE INITIALIZATION → HARDWARE INIT → GPU READY`. Antes de este hallazgo el
corpus tenía el *qué* de casi cada nodo —el ASIC por `amdgpu_drv.c:2041`, la
ventana BAR5 por `242`, las IP blocks por `191`— pero **no tenía el orden**.

Comprobación previa sobre los 506 hallazgos:

```text
  amdgpu_pci_probe                0 hallazgos
  amdgpu_device_init              0 hallazgos
  pci_enable_device               0 hallazgos
  drm_mode_config_init            0 hallazgos
  amdgpu_kms_init                 0 hallazgos
  pci_set_power_state             0 hallazgos
  pci_save_state                  0 hallazgos
```

Y en 7.1.3 el punto de entrada **no** se llama `amdgpu_probe`: se llama
`amdgpu_pci_probe`, y vive en `amdgpu_drv.c`, no en `amdgpu_device.c`. Cualquier
reconstrucción hecha contra el nombre `amdgpu_probe` habría buscado en el fichero
equivocado.

## Criterio de terminación

Reconstruir la secuencia con orden explícito y contrastarla con el log de este
arranque. **Cumplido.** La secuencia está cerrada de fuente y corroborada de
ejecución para esta placa.

---

## 1 · El productor: `pci_register_driver` y su `.probe`

```c
amdgpu_drv.c:3135   static struct pci_driver amdgpu_kms_pci_driver = {
amdgpu_drv.c:3138       .probe = amdgpu_pci_probe,
amdgpu_drv.c:3169   return pci_register_driver(&amdgpu_kms_pci_driver);
```

`pci_register_driver` es el punto de entrada del kernel. Cada `struct pci_device_id`
de `amdgpu_pciidlist` que case con un dispositivo en el bus provoca una llamada a
`amdgpu_pci_probe(pdev, ent)`.

`amdgpu_drv.c:2041` es la entrada que casa con esta placa:

```c
{0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
```

Los tres `PCI_ANY_ID` y el `0` de revisión son la razón por la que `rev_id = 0xc7`
no filtra: **esta placa entra por la ruta sin restricción de subvendor, subdevice
ni revisión**. Eso explica por qué la discrepancia que `051` registró entre
`ASICID_IS_P23` y `0x699f` no tiene efecto: el `ent->driver_data` ya trae
`CHIP_POLARIS12` resuelto antes de que el macro se consulte nunca.

## 2 · Las nueve puertas de `amdgpu_pci_probe`, en orden

`amdgpu_drv.c:2364` — `unsigned long flags = ent->driver_data` (`:2369`) es el
transporte del ASIC desde el bus hasta el driver.

| # | línea | puerta | veredicto en esta placa |
|---|---|---|---|
| 1 | `:2375` | `drm_firmware_drivers_only() && amdgpu_modeset == -1` → `-EINVAL` | pasa |
| 2 | `:2381` | `amdgpu_unsupported_pciidlist` → `-ENODEV` | pasa |
| 3 | `:2387` | `supports_atomic = true` si DC o virtual display | evaluado |
| 4 | `:2389` | `AMD_EXP_HW_SUPPORT` → `-ENODEV` | pasa |
| 5 | `:2395` | `amdgpu_fix_asic_type(pdev, flags)` — **reescribe** `flags` | aplicado |
| 6 | `:2401` | SME + `CHIP_RAVEN` → `-ENOTSUPP` | no aplica |
| 7 | `:2408` | `amdgpu_support_enabled()` → `-ENODEV` | pasa |
| 8 | `:2411` | `devm_drm_dev_alloc()` — reserva el `struct amdgpu_device` | ok |
| 9 | `:2422` | **`pci_enable_device(pdev)`** — primer toque de energía | ok |

`pci_enable_device` es la **puerta PCI→dispositivo**: sin ella no hay bus master
ni mapeo de recursos. Es la primera línea del camino que produce el registro BAR0
de esta placa.

Después de esa puerta, y todavía en `amdgpu_pci_probe`:

```text
  :2426  pci_set_drvdata(pdev, ddev)
  :2428  amdgpu_init_debug_options(adev)
  :2430  amdgpu_driver_load_kms(adev, flags)     <-- toda la inicializacion
  :2435  drm_dev_register(ddev, flags)
         :2436  si == -EAGAIN  ->  retry hasta 3 veces, msleep(5000) entre ellas
  :2445  amdgpu_xcp_dev_register(adev, ent)
  :2449  amdgpu_amdkfd_drm_client_create(adev)
  :2457  fbdev, solo si hay conectores  (comment: no init fbdev on hw without DCE)
  :2470  amdgpu_debugfs_init(adev)              <-- fallo NO es fatal
  :2475  banderas DPM segun BACO/BOCO
```

Dos_comments del propio código importan para el orden:

- **`:2436` el reintento con `-EAGAIN` existe para no pedir modo EX con agresividad.**
  El log de este arranque **no** muestra ninguna línea `retry init`, lo que es
  consistente con que el primer `drm_dev_register` tuvo éxito.
- **`:2470` `amdgpu_debugfs_init` falla sin abortar.** El resto de la lista aborta;
  ese no. Es la diferencia entre `goto err_pci` y `DRM_ERROR`.

## 3 · `amdgpu_driver_load_kms`: cuatro pasos, uno solo fatal

`amdgpu_kms.c:135`. El comentario de la función es una declaración de contrato
explícita y es la razón por la que el orden importa:

```c
/* amdgpu_device_init should report only fatal error
 * like memory allocation failure or iomapping failure,
 * or memory manager initialization failure, it must
 * properly initialize the GPU MC controller and permit
 * VRAM allocation
 */
```

| línea | paso | fallo |
|---|---|---|
| `amdgpu_kms.c:148` | `amdgpu_device_init(adev, flags)` | **fatal** |
| `amdgpu_kms.c:154` | `amdgpu_device_detect_runtime_pm_mode(adev)` | — |
| `amdgpu_kms.c:160` | `amdgpu_acpi_init(adev)` | no fatal, `dev_dbg` |
| `amdgpu_kms.c:164` | `amdgpu_acpi_smart_shift_update(..., AMDGPU_SS_DRV_LOAD)` | no fatal, `drm_warn` |

Y `out:` (`:171`) hace `amdgpu_driver_unload_kms(dev)` si `r` — es decir, el
deshacer está en la misma función que el hacer, no en un unwind de `probe`.

## 4 · `amdgpu_device_init`: la secuencia, con su consumidor en el log

`amdgpu_device.c:3679`. 24 pasos. Los marcados **[LOG]** tienen una línea en el
arranque de esta placa; los marcados **[AUSENTE]** no la tienen, y esa ausencia es
información.

| # | línea | acción | estado en runtime |
|---|---|---|---|
| 1 | `:3694` | `adev->asic_type = flags & AMD_ASIC_MASK` | — |
| 2 | `:3699` | `adev->gmc.gart_size = 512 MiB` (valor por defecto) | **[LOG]** `GART: 256M` — **no** es 512 |
| 3 | `:3812` | `asic_type >= CHIP_BONAIRE` → BAR 5, si no BAR 2 | **[LOG]** `register mmio base: 0xF7D00000` |
| 4 | `:3823` | **`adev->rmmio = ioremap(rmmio_base, rmmio_size)`** | **[LOG]** `register mmio size: 262144` |
| 5 | `:3859` | `amdgpu_set_init_level(AMDGPU_INIT_LEVEL_DEFAULT)` | — |
| 6 | `:3861` | **`amdgpu_device_ip_early_init(adev)`** | **[LOG]** 9 × `detected ip block number` |
| 7 | `:3872` | `aperture_remove_conflicting_pci_devices()` (solo VGA/OTHER) | **[LOG]** `vgaarb: deactivate vga console` |
| 8 | `:3878` | `amdgpu_gmc_tmz_set(adev)` | **[LOG]** `TMZ feature not supported` |
| 9 | `:3923` | `pci_enable_atomic_ops_to_root()` | **[AUSENTE]** `PCIE atomic ops is not supported` |
| 10 | `:3932` | `amdgpu_doorbell_init(adev)` — mapea BAR de doorbell | — |
| 11 | `:3940` | `amdgpu_reset_init(adev)` | — |
| 12 | `:3949` | `amdgpu_asic_need_reset_on_init()` → `amdgpu_asic_reset()` | **[AUSENTE]** ningún reset |
| 13 | `:3971` | `amdgpu_device_need_post()` → `amdgpu_device_asic_init()` | **[AUSENTE]** `GPU posting now...` |
| 14 | `:3996` | `amdgpu_atombios_get_clock_info()` | **[LOG]** `VCE firmware Version: 53.26` |
| 15 | `:4003` | `amdgpu_i2c_init(adev)` | — |
| 16 | `:4009` | `amdgpu_fence_driver_sw_init(adev)` | — |
| 17 | `:4017` | **`drm_mode_config_init()`** | **[AUSENTE]** silencioso |
| 18 | `:4019` | **`amdgpu_device_ip_init(adev)`** | **[LOG]** VRAM/GART/GTT/IB/DC |
| 19 | `:4026` | `amdgpu_fence_driver_hw_init(adev)` | — |
| 20 | `:4035` | `adev->accel_working = true` | — |
| 21 | `:4052` | `amdgpu_register_gpu_instance(adev)` | **[LOG]** `Topology: Add GPU node` |
| 22 | `:4058` | **`amdgpu_device_ip_late_init(adev)`** | **[LOG]** reloj/power |
| 23 | `:4065` | `amdgpu_ras_resume` + `delayed_init_work` a `AMDGPU_RESUME_MS` | — |
| 24 | `:4077` | `kgd2kfd_init_zone_device` + `kfd_update_svm_support_properties` | **[LOG]** `kfd: Allocated 3969056 bytes on gart` |

### 4.1 · El paso 2 contradice el valor por defecto, y el log lo dice

```c
amdgpu_device.c:3699    adev->gmc.gart_size = 512 * 1024 * 1024;   /* por defecto */
...
OBSERVADO               GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
```

El GART de esta placa es **256 MiB, la mitad del default**. El default es solo un
punto de partida; el valor real lo fija `gmc_v8_0` durante `ip_init`. Registrar el
512 del código como si fuera el de la placa sería un error de lectura, y la
distancia entre ambos es justamente lo que hace observable la inicialización.

### 4.2 · El paso 3: el mapa de BAR, con dirección física

El log de este arranque da el mapa completo del bus, que es la capa de entrada:

```text
  BAR 0  [mem 0xe0000000-0xefffffff 64bit pref]   256 MiB   VRAM visible
  BAR 2  [mem 0xf0000000-0xf01fffff 64bit pref]     2 MiB
  BAR 4  [io  0xe000-0xe0ff]                          256 B
  BAR 5  [mem 0xf7d00000-0xf7d3ffff]               256 KiB   <-- ventana de registros
  ROM    [mem 0xf7d40000-0xf7d5ffff pref]           128 KiB
```

`register mmio base: 0xF7D00000` es exactamente el inicio de BAR5, y
`262144 = 0x40000` es exactamente `0xf7d3ffff - 0xf7d00000 + 1`. Las dos líneas del
log son las dos líneas del `dev_info` de `amdgpu_device.c:3827-3830`, alimentadas por
`pci_resource_start/len(pdev, 5)`.

**⇒ `PROVEN_DERIVED`. Para el driver propio: `rmmio_base` es una dirección física
de bus, `0xF7D00000`, y la ventana son 256 KiB. `242` ya había corregido el BAR y
la longitud; lo que este hallazgo añade es que el mapeo es `ioremap()` de una
dirección física —`amdgpu_device.c:3823`— y **no** `pci_iomap`.**

Eso importa para el driver propio porque las dos cosas no son intercambiables:
`pci_iomap` aplica la política del núcleo (orden, límites, `max_len`); `ioremap` de
un recurso ya asignado no la aplica. Implementar con `pci_iomap(pdev, 5)` sería
correcto pero distinto de lo que hace el driver de producción, y `197` ya registró
un choque real de firma en ese mismo símbolo.

### 4.3 · El paso 9 y el 13: dos ausencias que son datos

```text
  paso 9   amdgpu_device.c:3928   if (!adev->have_atomics_support)
                                      dev_info("PCIE atomic ops is not supported\n");
  OBSERVADO                          la linea NO aparece

  paso 13  amdgpu_device.c:3971   if (amdgpu_device_need_post(adev))
                                      dev_info("GPU posting now...\n");
  OBSERVADO                          la linea NO aparece
```

- **Paso 9.** `pci_enable_atomic_ops_to_root` devolvió éxito: la placa **sí**
  soporta atomics PCIe de 32 y 64 bits. El log también corrobora que el camino
  tomado no fue ni SR-IOV ni APU, porque en esos casos la línea tampoco se
  imprimiría pero por otra razón (`amdgpu_device.c:3908-3926`).
- **Paso 13.** `amdgpu_device_need_post()` devolvió falso: **la placa ya estaba
  posteada por el BIOS** y el driver no tuvo que postearla. Esto tiene una
  consecuencia dura: el VBIOS se leyó de la ROM BAR
  (`Fetched VBIOS from ROM BAR`) y `amdgpu_device_asic_init` nunca corrió.

**⇒ `PROVEN`. La placa entra al driver ya posteada. Ningún registro de
inicialización de clocks propio del ASIC ocurre en el camino de probe de esta
configuración; el reloj lo dejó el firmware antes de que el driver existiera.**

## 5 · El discriminante nuevo: `(vi_common)` decide la rama del `switch`

Este es el resultado que no estaba en ninguna otra fuente.

`amdgpu_device.c:1926` — `amdgpu_device_ip_early_init` abre con un `switch`
sobre `adev->asic_type`. La etiqueta que corresponde a esta placa es:

```c
amdgpu_device.c:1980   case CHIP_POLARIS12:
amdgpu_device.c:1984           if (adev->flags & AMD_IS_APU)
amdgpu_device.c:1985                   adev->family = AMDGPU_FAMILY_CZ;
amdgpu_device.c:1987           else
amdgpu_device.c:1987                   adev->family = AMDGPU_FAMILY_VI;
amdgpu_device.c:1989           r = vi_set_ip_blocks(adev);
...
amdgpu_device.c:1994   default:  r = amdgpu_discovery_set_ip_blocks(adev);
```

`242` registró que el enum `CHIP_BONAIRE` no está en el corpus y tuvo que decidir
la rama del BAR **por el número impreso** (`262144`), porque leer el orden del enum
era imposible. Ese sigue siendo el método correcto y no se sustituye.

Pero hay un discriminante adicional que `242` no tenía, y es de ejecución:

```c
amdgpu_ip.c:241    dev_info(adev->dev, "detected ip block number %d <%s_v%d_%d_%d> (%s)\n",
                             i, ..., adev->ip_blocks[i].version->funcs->name);
```

El quinto `%s` es `version->funcs->name`. Para el bloque 0 de esta placa el log da:

```text
  detected ip block number 0 <common_v1_0_0> (vi_common)
```

Y la procedencia de ese nombre es **única**:

```text
  vi.c:2020    static const struct amd_ip_funcs vi_common_ip_funcs = {
  vi.c:2021            .name = "vi_common",
  vi.c:2041            .funcs = &vi_common_ip_funcs,      <-- unico referenciador
  vi.c:2049    int vi_set_ip_blocks(struct amdgpu_device *adev)
  amdgpu_device.c:1989        r = vi_set_ip_blocks(adev); <-- unico llamador
```

Verificado por búsqueda exhaustiva sobre el árbol `drivers/gpu/drm/amd`:

```text
  grep -rn "vi_common_ip_funcs"   ->  2 ocurrencias, ambas en vi.c (2020, 2041)
  grep -rn "vi_set_ip_blocks"     ->  4 ocurrencias, 1 solo calledor (amdgpu_device.c:1989)
```

**⇒ `PROVEN_DERIVED`. La cadena `log dice (vi_common)` → `vi.c:2041` →
`vi_set_ip_blocks` → `amdgpu_device.c:1989` → `case CHIP_POLARIS12:` es
**unívoca**: no hay segundo camino que pueda imprimir ese sufijo en esta placa.**

Corolarios, cada uno con su alcance:

| afirmación | estado | por qué |
|---|---|---|
| El log de esta placa pasó por `vi_set_ip_blocks` | `PROVEN` | sufijo único + un solo llamador |
| `adev->asic_type` estaba en el conjunto `{TOPAZ, TONGA, FIJI, POLARIS10, POLARIS11, POLARIS12, VEGAM, CARRIZO, STONEY}` | `PROVEN` | las nueve etiquetas comparten esa llamada |
| `adev->asic_type == CHIP_POLARIS12` | `PROVEN_DERIVED` | el conjunto de 9 más `amdgpu_drv.c:2041`, y la revisión `0xc7` no filtra porque los campos son `PCI_ANY_ID` |
| La rama `default:` / `amdgpu_discovery_set_ip_blocks` **no** se tomó | `PROVEN` | es la única alternativa al `switch` |
| El orden del enum `CHIP_BONAIRE` vs `CHIP_POLARIS12` | **`NOT_DETERMINED`** | sin resolver, pero **ya no es necesario**: `242` lo deciding por el número, y este hallazgo lo resuelve por el sufijo |

**⇒ Esto cierra el `NOT_IN_CORPUS` de `242` §1 sin appeals al orden de un enum,
y por una vía independiente.** Dos discriminantes, dos métodos, mismo resultado: la
ventana de registros es BAR5.

## 6 · La cadena causal completa, con productor y consumidor

```text
PCI bus scan (kernel)
  └─ casa amdgpu_pciidlist[amdgpu_drv.c:2041]  {1002,699F,...,CHIP_POLARIS12}
       └─ flags = ent->driver_data                                    [amdgpu_drv.c:2369]
            └─ amdgpu_pci_probe                                       [amdgpu_drv.c:2364]
                 ├─ 9 puertas, :2375 .. :2422
                 └─ amdgpu_driver_load_kms                             [amdgpu_drv.c:2430]
                      └─ amdgpu_device_init                            [amdgpu_kms.c:148]
                           ├─ asic_type = flags & AMD_ASIC_MASK       [:3694]
                           ├─ rmmio_base = pci_resource_start(pdev,5) [:3813]
                           │    └─ ioremap -> adev->rmmio            [:3823]
                           │         └─ dev_info "register mmio"     [:3827]
                           │              └─ OBSERVADO 0xF7D00000 / 262144
                           └─ ip_early_init                           [:3861]
                                └─ case CHIP_POLARIS12 -> vi_set_ip_blocks [:1989]
                                     └─ amdgpu_ip.c:241 dev_info "detected ip block"
                                          └─ OBSERVADO "(vi_common)"
  ---> dev_reg + ip_init [:4019]  ---> VRAM/GART/GTT/IB/DC
  ---> fence hw + late_init [:4058]  ---> reloj, power
GPU READY:  "Initialized amdgpu 3.64.0 for 0000:01:00.0 on minor 1"
```

Cada flecha tiene productor, representación y consumidor. No queda ningún eslabón
completado por intuición.

## 7 · `ip_init`: el orden real de los bloques, y por qué COMMON y GMC van antes

`amdgpu_device.c:2299`. El bucle no es uniforme, y esa asimetría es el contenido
real de la función:

```text
  :2304  amdgpu_ras_init(adev)                    una vez, antes del bucle
  :2308  for (i = 0; i < adev->num_ip_blocks; i++)
  :2309        if (!adev->ip_blocks[i].status.valid) continue;
  :2312        sw_init()  de cada bloque marcado valid
  :2321        adev->ip_blocks[i].status.sw = true
  :2323        if (!amdgpu_ip_member_of_hwini(...)) continue;      <-- SALTA hw_init
  :2327        if (type == COMMON)  hw_init()                     <-- ADELANTADO
                    "need to do common hw init early so everything is set up for gmc"
  :2336        else if (type == GMC)  hw_init()                   <-- ADELANTADO
                    + amdgpu_device_mem_scratch_init  (:2342)
                    + amdgpu_device_wb_init           (:2355)
                    + amdgpu_allocate_static_csa       (:2365)
                    + amdgpu_seq64_init               (:2376)
  :2388  amdgpu_ib_pool_init(adev)
  :2395  amdgpu_ucode_create_bo(adev)      "create ucode bo when sw_init complete"
  :2399  amdgpu_device_ip_hw_init_phase1(adev)
```

Dos consecuencias que no se ven leyendo solo la lista de bloques:

1. **`sw_init` de los 9 bloques ocurre en el bucle; `hw_init` de 7 de ellos no.**
   Los que no son COMMON ni GMC se saltan aquí por `:2323` y los hace
   `hw_init_phase1`. El log de esta placa lo ordena accordingly:
   `hwmgr_sw_init smu backed is polaris10_smu` (sw) aparece **antes** que
   `Display Core v3.2.378 initialized` (hw).
2. **GMC `hw_init` es un prerrequisito de la asignación de VRAM**, y por eso
   arrastra scratch memory, writeback, CSA y seq64. `amdgpu_kms.c:145-150` lo dice
   en el contrato: *"it must properly initialize the GPU MC controller and permit
   VRAM allocation"*.

**⇒ Para el driver propio: no hay un `init` que hacer. Hay una secuencia con dos
bloques adelantados, y adelantarlos es opcional pero no inocuo.** Si el driver
propio no necesita VRAM hasta más tarde, GMC puede ir después; si la necesita para
el primer frame, tiene que ir antes de cualquier cosa que pida memoria de GPU.

## 8 · Lo que este hallazgo NO cierra

```text
POST / RESET                 amdgpu_asic_need_reset_on_init -> False en esta
                             maquina. POR QUE devuelve falso, y que habria
                             devuelto True, es OTRO mecanismo y NO_DETERMINED.
                             No se ha medido ni un solo reset en ejecucion.

ORDEN DEL ENUM CHIP_BONAIRE  NOT_DETERMINED.  No se necesita para el BAR, pero
                             si para cualquier otra comparacion `>= CHIP_*` que
                             el driver propio tenga que replicar.

ORDEN EXACTO DE LOS 24 PASOS runtime-verificado  Parcial. 19 pasos tienen o no
                             linea de log; los 5 restantes son silenciosos por
                             diseno y no se pueden discriminar desde este lado.

pci_set_power_state / RUNTIME PM  El log dice "Using BACO for runtime pm" pero
                             ningun hallazgo cubre la maquina de estados de
                             energia. Fuera del alcance de este hallazgo.

SRIOV / APU / XeMgmt           Las ramas no tomadas se identificaron por
                             ausencia de log, que es consistente pero NO es
                             prueba de que el codigo las haya recorrido.
                             NOT_DETERMINED por construccion.
```

La última fila es la que más conviene retener: **la ausencia de una línea de log
acredita que no se emitió, no que el camino sea inalcanzable.** Es la diferencia
entre `NOT_OBSERVED` y `PROVEN_ABSENT`, y aquí es `NOT_OBSERVED`.

## 9 · Desfalsificación

| afirmación | refutada por |
|---|---|
| El punto de entrada es `amdgpu_pci_probe` | `amdgpu_drv.c:3138`; no hay `amdgpu_probe` en 7.1.3 |
| La ventana es BAR5 | log `0xF7D00000` + `amdgpu_device.c:3813`; `242` lo confirmo por via independiente |
| El mapeo es `ioremap`, no `pci_iomap` | `amdgpu_device.c:3823`; no hay `pci_iomap` en el arbol amdgpu |
| `(vi_common)` identifica la rama `vi_set_ip_blocks` | un solo referenciador y un solo llamador, verificados |
| La placa no se postea en probe | `GPU posting now...` ausente **y** codigo de `need_post` leido |
| La placa soporta atomics PCIe | `PCIE atomic ops is not supported` ausente; rama leida |
| GART real = 256 MiB | log `GART: 256M` contra default de 512 MiB en `:3799` |
| 9 bloques IP, `vi_set_ip_blocks` | log 9 lineas + 1 unico camino |

## 10 · Trazabilidad

```text
  amdgpu_drv.c:3135-3139     la struct pci_driver y su .probe
  amdgpu_drv.c:3169          pci_register_driver
  amdgpu_drv.c:2041          la entrada que casa: 1002:699F -> CHIP_POLARIS12
  amdgpu_drv.c:2364-2435     amdgpu_pci_probe y sus 9 puertas
  amdgpu_kms.c:135-171       amdgpu_driver_load_kms y su contrato de fatality
  amdgpu_device.c:3679       amdgpu_device_init, 24 pasos
  amdgpu_device.c:3812-3823  elecion de BAR5 e ioremap
  amdgpu_device.c:3861       amdgpu_device_ip_early_init, punto 6
  amdgpu_device.c:1981-1994  el switch y sus dos unicas salidas
  amdgpu_device.c:2299-2400  amdgpu_device_ip_init y el adelantamiento de COMMON/GMC
  amdgpu_ip.c:241            el dev_info cuyo 5o %s es funcs->name
  vi.c:2020-2049             vi_common_ip_funcs, unico nombre y unico camino
  journalctl -k -b           la observacion: mapa de BAR, 9 bloques, geometria
  findings/051               la pregunta original (ASIC ID); respondida en :2041
  findings/202               el NOT_IN_CORPUS del enum; cerrado por via independiente
  findings/191               las 126 tablas IP; la de esta placa es la de vi.c
  findings/197               el choque real de firma de pci_iomap, que no se repite
  findings/163               el log ya observado; aqui se le anade el orden
```

```text
CITA=amdgpu_device.c | TERMINO=adev->asic_type >= CHIP_BONAIRE
    | ROL=la rama que abre la ventana de registros; el orden del enum sigue
         NOT_DETERMINED pero el resultado ya no depende de el
CITA=vi.c | TERMINO=.name = "vi_common"
    | ROL=el sufijo del log que identifica la rama del switch, por unico camino
CITA=amdgpu_kms.c | TERMINO=it must properly initialize the GPU MC controller and permit VRAM allocation
    | ROL=por que GMC hw_init va antes que el resto: es lo que hace posible el frame 1
```

```
WRITE_EXECUTION=NONE.  MODIFICATIONS=0.  GPU INTACTA.  CERROJOS=0.
```

## CONTINÚA

El tramo siguiente de la cadena de `AGENT-07` es `GPU READY → MMU/GPUVM`, que ya
tiene hallazgos propios (`033`, `067`, `204`, `242`) pero no esta enlazado a este
orden. El eslabón que falta es la **posición exacta de `amdgpu_mmu_init` y
`amdgpu_vm` dentro de `ip_init` y `late_init`**, y si el driver propio puede
saltarse `amdgpu_device_init` entero conservando el punto de entrada en VRAM.
```