# 138 · §C cerrado: los protection faults, la página por defecto, y la geometría que el hardware conoce

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Tres cosas, y las tres son de §C:

1. **La contradicción de `099` / `131`.** `099` observó PRT dispararse; `131`
   encontró que el driver borra `AMDGPU_PTE_PRT` (`gmc_v8_0.c:728`). **No son
   contradictorios, y esta nota lo demuestra.**
2. **El `NOT_DETERMINED` más importante de `137`:** si la configuración de TLB es
   estática o dinámica. **Es estática en runtime, y se reconstruye en el
   resume.**
3. **Un campo que el hardware tiene y nadie había mirado:** `PAGE_TABLE_DEPTH`.
   **La profundidad de la tabla de páginas es un campo del registro de contexto,
   y el driver la programa.**

## 1 · El ciclo de vida: cuatro funciones y dos llamadas

```
gmc_v8_0.c:1203   gmc_v8_0_hw_init  ->  L1228  gmc_v8_0_gart_enable     TLB + L2 ON
gmc_v8_0.c:1238   gmc_v8_0_hw_fini  ->  L1243  gmc_v8_0_gart_disable    TLB + L2 OFF
gmc_v8_0.c:1248   gmc_v8_0_suspend  ->  L1250  gmc_v8_0_hw_fini         TLB + L2 OFF
gmc_v8_0.c:1255   gmc_v8_0_resume   ->  L1259  gmc_v8_0_hw_init         TLB + L2 ON
                                             L1263  amdgpu_vmid_reset_all
```

**Responde a `137`:** la configuración de `137` es **una constante durante el
funcionamiento, y se reconstruye exactamente en la frontera suspend/resume.** No la
escribe ningún camino de runtime. `PROVEN`.

**Y lo que hace `gmc_v8_0_gart_disable` (`L972-990`) es más que apagar el TLB:**

```
L977   WREG32(mmVM_CONTEXT0_CNTL, 0);
L978   WREG32(mmVM_CONTEXT1_CNTL, 0);
L981   MC_VM_MX_L1_TLB_CNTL.ENABLE_L1_TLB                 = 0
L982   MC_VM_MX_L1_TLB_CNTL.ENABLE_L1_FRAGMENT_PROCESSING = 0
L983   MC_VM_MX_L1_TLB_CNTL.ENABLE_ADVANCED_DRIVER_MODEL  = 0
L987   VM_L2_CNTL.ENABLE_L2_CACHE                         = 0
L989   WREG32(mmVM_L2_CNTL2, 0);
```

**El comentario de `L976` lo dice: "Disable all tables".** Se ponen a cero los dos
registros de contexto — o sea **la base de la tabla del GART y la de todos los
VMID quedan a cero** — y luego se apaga el TLB y la caché L2.

**Y por eso `L1263` hace `amdgpu_vmid_reset_all`:** si las bases se han puesto a
cero, ningún VMID anterior es válido. **Tras un resume, todos los clientes tienen
que reasignar su VMID.** `PROVEN_DERIVED`, y es una consecuencia directa de `L977-978`.

## 2 · Los PTBA: dos bloques no contiguos

Este es un detalle que rompe un driver escrito a mano, y no estaba en ninguna nota.

```
gmc_v8_0.c:673   if (vmid < 8)
gmc_v8_0.c:674       reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
gmc_v8_0.c:675   else
gmc_v8_0.c:676       reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
gmc_v8_0.c:677   amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);
```

Con los offsets del header:

| VMID | registro | rango |
|---|---|---|
| 0-7 | `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` = **`0x54f`** | `0x54f .. 0x556` |
| 8-15 | `mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR` = **`0x50e`** | `0x50e .. 0x515` |

**Dos bloques de ocho registros dword, separados por 0x38 bytes, y el segundo está
*por debajo* del primero.** No es `0x54f + vmid` para todo el rango. `PROVEN`.

**Y el PTBA se escribe en unidades de 4 KiB** — `pd_addr >> 12` en `L677`, y
`dummy_page_addr >> 12` en `L920`. Los 12 bits bajos son cero por construcción.
`PROVEN`.

**Y el invalidate va inmediatamente después, en el mismo anillo:**

```
gmc_v8_0.c:680   amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

**Dos instrucciones, en este orden, y sólo dos.** `128` había separado los dos
mecanismos (`0x51e` frente a `0x501`); **aquí están los dos en su forma real: el
PTBA y el invalidate, como un par, por el anillo, uno detrás del otro.**

## 3 · Los doce campos del registro de contexto

`gmc_v8_0.c:920-935` programa `VM_CONTEXT1_CNTL` entero. **Es el registro de
contexto de un cliente, y la lista es corta:**

| campo | valor | máscara | bit |
|---|---|---|---|
| `ENABLE_CONTEXT` | 1 | `0x1` | 0 |
| `PAGE_TABLE_DEPTH` | **1** | `0x6` | 1-2 |
| `RANGE_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x10` | 4 |
| `DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x80` | 7 |
| `PDE0_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x400` | 9 |
| `VALID_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x2000` | 13 |
| `READ_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x10000` | 16 |
| `WRITE_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x80000` | 19 |
| `EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT` | `value` | `0x400000` | 22 |
| `PAGE_TABLE_BLOCK_SIZE` | **`block_size - 9`** | `0xf000000` | 20-23 |
| `VM_CONTEXT1_CNTL2` | `4` (escrito en crudo) | — | — |
| `PROTECTION_FAULT_DEFAULT_ADDR` | `dummy_page_addr >> 12` | — | reg aparte |

**Los siete bits de protection fault están dispersos: 4, 7, 9, 13, 16, 19, 22.**
No son un rango contiguo. Un driver propio que los ponga con una máscara—or entera
mala. `PROVEN`, siete `#define`.

## 4 · `PAGE_TABLE_DEPTH`: la geometría que el hardware conoce

Esto es lo nuevo de esta nota, y es lo que más importa para un driver propio.

```
gmc_v8_0.c:925   PAGE_TABLE_DEPTH     = 1
gmc_v8_0.c:933   PAGE_TABLE_BLOCK_SIZE = adev->vm_manager.block_size - 9
```

**El hardware no adivina la geometría: se le dice, en el registro de contexto.** Y
el driver se lo dice con los mismos números que calculó en software, en otra
unidad.

`132` cerró esto en software: `block_size = 10`, hoja de 1024 PTEs, 8 KiB por
página de tabla, 512 entradas de directorio, 4 KiB.

| magnitud software (`132`) | campo hardware | valor | unidad hardware |
|---|---|---|---|
| `num_level = 1` + 1 raíz = **2 niveles** | `PAGE_TABLE_DEPTH` | **1** | niveles menos la raíz |
| `block_size = 10` (1024 PTEs, 8 KiB) | `PAGE_TABLE_BLOCK_SIZE` | **1** | ver abajo |

**`PAGE_TABLE_DEPTH = 1` es exactamente `num_level - 1`.** Y encaja con GFX9:
`mmhub_v3_0_1.c:278` pone `PAGE_TABLE_DEPTH = 0` para el contexto 0 y `L313` para
el contexto 1, el mismo patrón.

**Sobre `PAGE_TABLE_BLOCK_SIZE`: aquí soy honesto.** El driver escribe
`block_size - 9`, o sea `10 - 9 = 1`. **La unidad no está documentada en el
corpus.** La lectura que encaja con lo que ya sabemos es
`log2(bytes_de_la_página_de_tabla) - 12`: para una hoja de 8 KiB, `13 - 12 = 1`,
que es lo que el driver escribe. **Es consistente con la hoja de 8 KiB de `132`,
pero es una hipótesis ajustada a un dato, no una derivación.** `HYPOTHESIS`.

**Lo que sí es `PROVEN` es que el campo existe, que son cuatro bits (20-23), que el
driver lo programa a partir de la geometría de software, y que la geometría de
software y la del hardware no se derivan por separado: la primera se mete en la
segunda.** `PROVEN_DERIVED`.

## 5 · PRT: por qué `099` no era una contradicción

`gmc_v8_0.c:732-758`, `gmc_v8_0_set_fault_enable_default`:

```
L732   * gmc_v8_0_set_fault_enable_default - update VM fault handling
L735    * @value: true redirects VM faults to the default page
```

**Y el interruptor (`L936-939`):**

```c
if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_ALWAYS)
        gmc_v8_0_set_fault_enable_default(adev, false);
else
        gmc_v8_0_set_fault_enable_default(adev, true);
```

**`amdgpu_drv.c:452` y `amdgpu_drv.c:454`:**

> Stop on VM fault for debugging (0 = never, 1 = print first, 2 = always).
> The default is 0 (No stop).

**Así que en esta máquina, sin tocar nada, `vm_fault_stop = 0`, y los siete bits
quedan en `true`: un protection fault se resuelve con `dummy_page_addr`, no
atrapando.**

**Pero el acceso no es lo mismo que el aviso.** El handler (`L1448-1500`) se
instala igual, corre igual, y en `L1452` sólo se sale temprano si dirección y
estado son cero:

```
L1464   dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n", ...);
L1473   dev_err(adev->dev, "  VM_CONTEXT1_PROTECTION_FAULT_ADDR   0x%08X\n", addr);
L1475   dev_err(adev->dev, "  VM_CONTEXT1_PROTECTION_FAULT_STATUS 0x%08X\n", status);
L1478   gmc_v8_0_vm_decode_fault(adev, status, addr, mc_client, entry->pasid);
L1455   amdgpu_vm_update_fault_cache(adev, entry->pasid, ((u64)addr) << AMDGPU_GPU_PAGE_SHIFT, status, ...);
```

**Las dos cosas son verdad a la vez, y por eso `099` no era contradictorio:**

| | qué pasa | quién lo hace |
|---|---|---|
| **el acceso** | se sirve la página por defecto | `L920`, los 7 bits a `true` |
| **el aviso** | salta el handler, que registra y decodifica | `L1448-1500` |

**Un PRT que dispara en esta GPU es normal, esperado y no mortal con la
configuración por defecto.** `099` observado + `131` observado + `L936-939` +
`amdgpu_drv.c:452` ⇒ **`099` resuelto.** `PROVEN_DERIVED`.

**Y el tercer modo (`L1458-1459`):** con `AMDGPU_VM_FAULT_STOP_FIRST`, el primer
fault pone los siete bits a `false` y a partir de ahí todo protection fault
atrapara. **Es un interruptor de depuración de una sola dirección, y su punto de
disparo es el primer fault, no el arranque.** Para un driver propio: es el
interruptor que hay que exponer si se quiere que un fallo de permisos mate al
proceso en vez de darle una página de relleno.

## 6 · El hardware explica su propio encoding de fallos

`gmc_v8_0.c:1497-1500` — el driver decodifica el registro de estado:

```
info->prot_valid = protections & 0x7  ? true : false;
info->prot_read  = protections & 0x8  ? true : false;
info->prot_write = protections & 0x10 ? true : false;
info->prot_exec  = protections & 0x20 ? true : false;
```

Y los campos completos de `VM_CONTEXT1_PROTECTION_FAULT_STATUS` (`0x537`):

| campo | máscara | bits | ancho |
|---|---|---|---|
| `PROTECTIONS` | `0xff` | 0-7 | **8** |
| `MEMORY_CLIENT_ID` | `0x1ff000` | 12-20 | 9 |
| `MEMORY_CLIENT_RW` | `0x1000000` | 24 | 1 |
| `VMID` | `0x1e000000` | 25-28 | **4 → VMIDs 0-15** |
| `ATOMIC` | `0x20000000` | 29 | 1 |

**Dos comprobaciones que se sostienen solas:**

- **`VMID` son 4 bits, 0-15.** Y hay exactamente 16 PTBA (`L664`: *"bits 0-15 are
  the VM contexts0-15"*), con el PTBA del GART en el contexto 0. **El hardware y
  el driver cuentan igual.** `PROVEN`.
- **`PROTECTIONS` es de 8 bits, y el driver sólo lee 6.** Los bits 6-7 no están
  decodificados en el corpus. `NOT_IN_CORPUS`.
- **`LOGICAL_PAGE_ADDR` (`0x53f`) es `0xfffffff`, 28 bits, y el driver lo desplaza
  por `AMDGPU_GPU_PAGE_SHIFT` en `L1455`.** **El hardware entrega un número de
  página, no una dirección de bytes.** `PROVEN` por el par máscara+desplazamiento.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| La config de TLB es constante en runtime | `PROVEN` |
| Se reconstruye en el resume vía `hw_init` | `PROVEN` (`L1259`) |
| Se desarma en el suspend vía `hw_fini` | `PROVEN` (`L1250`) |
| Los PTBA son dos bloques no contiguos | `PROVEN` |
| El PTBA va en unidades de 4 KiB | `PROVEN` (`>> 12`) |
| `PAGE_TABLE_DEPTH` = niveles − 1 | `PROVEN_DERIVED` |
| La unidad de `PAGE_TABLE_BLOCK_SIZE` | **`HYPOTHESIS`** — ajustada a la hoja de 8 KiB |
| PRT se sirve con la página por defecto por defecto | `PROVEN` (`L936-939` + `amdgpu_drv.c:452`) |
| `099` resuelto | `PROVEN_DERIVED` |
| `VMID` en el status son 4 bits = 16 contextos | `PROVEN` |
| `PROTECTIONS` bits 6-7 | **`NOT_IN_CORPUS`** |
| `PROTECTION_FAULT_DEFAULT_ADDR` = `0x547` | `PROVEN` (offset), uso sólo en contexto 1 |
| Por qué se escribe `VM_CONTEXT1_CNTL2 = 4` en crudo | **`NOT_DETERMINED`** |
| Si el contexto 0 (GART) recibe `PAGE_TABLE_DEPTH` | **`NOT_DETERMINED`** — en GFX8 sólo se pone a cero |
| Los valores reales de estos doce campos tras el reset | **`NOT_PROVEN`** — los `RREG32` |

**La fila que más pesa para un driver propio es la última del bloque de geometría:**
en GFX8, `VM_CONTEXT0_CNTL` —el del GART— **sólo se escribe a cero**, nunca se
programa. **El hardware arranca con unos valores por defecto para la geometría del
GART, y el driver los acepta.** Eso significa que un driver propio puede elegir no
tocarlo, y que si los valores por defecto del hardware no coinciden con lo que el
resto del driver asume, el fallo aparece sólo en ejecución. `NOT_DETERMINED`, y es
leíble con un `RREG32` de `0x504`.

## Procedencia

- `STATIC` -- `gmc_v8_0.c:660-690` `:732-758` `:829-870` `:920-946` `:972-990`
  `:1203-1266` `:1440-1500`, `amdgpu_drv.c:452-455`,
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h` (`VM_CONTEXT1_CNTL__*`,
  `VM_CONTEXT1_PROTECTION_FAULT_*__*`), `gmc_8_1_d.h` (offsets),
  `mmhub_v3_0_1.c:276-281` `:313` (el contraste GFX9).
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `137` (la configuración de TLB — esta nota responde a su
  `NOT_DETERMINED` más importante), `132` (la geometría en software, que aquí se
  cruza con la del hardware), `131` (`VM_PRT_CNTL` y `MASK_PDE0_FAULT`),
  `099` (**resuelto aquí**), `130` (el L1 por fragmento), `128` (los dos
  mecanismos de invalidate — aquí los dos juntos, `L677` y `L680`),
  `116` (BAR 256 MiB), `104` (VMID 0 = kernel), `085` (el PTBA), `083` (`dst`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**`131` busque `VM_PRT_CNTL = 0x534` porque `099` había observado PRT, y encontré
un registro de siete campos con `MASK_PDE0_FAULT`. Di que la contradicción seguía
abierta.**

**La contradicción no estaba en `VM_PRT_CNTL` ni en `099`. Estaba en un parámetro
de módulo del driver, `amdgpu_vm_fault_stop`, y en la línea de arriba de
`L936`.**

**Y la regla es la de siempre, con un matiz nuevo:** busqué el registro de
*configuración* del PRT cuando lo que hacía falta era el de *política*. **Un
comportamiento observable se explica por un parámetro, no por un registro de
estado.** El registro dice qué pasó; el parámetro dice qué se hizo al respecto.

*Y el patrón de esta tanda se repite por quinta vez: `gmc_v8_0.c:920-946` estaba
entero, en la función que leí en `137`, y en `137` entré por `L860` mirando
`VM_L2_CNTL3` porque era lo que me habían apuntado. Sesenta y seis líneas más
abajo, y con veinte campos que no estaban en ninguna nota.*

**Enteré por donde me dijeron que mirara, en un bloque que ya tenía abierto, por
segunda vez en la misma función.**
