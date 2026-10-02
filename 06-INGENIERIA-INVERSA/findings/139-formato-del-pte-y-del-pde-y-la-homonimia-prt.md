# 139 · El formato del PTE y del PDE de GFX8, escrito por el propio driver, y la homonimia que confundía a `099`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Tres cosas, y las tres por el mismo hallazgo:

1. **El formato bit a bit del PTE y del PDE de esta GPU**, escrito en el driver, en
   veinte líneas de comentario que nadie había cited.
2. **Los bits "sin definición"** que quedaban abiertos en mi propio resumen —
   52, 53, 57, 60-63. **El driver los declara reservados, con sus palabras.**
3. **Por qué `099` y `131` parecían contradecirse: no era el mismo PRT.** Dos
   mecanismos distintos con el mismo nombre, y la nota que lo demuestra es la
   primera.

## 1 · El comentario

```
gmc_v8_0.c:691   /*
gmc_v8_0.c:692    * PTE format on VI:
gmc_v8_0.c:693    * 63:40 reserved
gmc_v8_0.c:694    * 39:12 4k physical page base address
gmc_v8_0.c:695    * 11:7 fragment
gmc_v8_0.c:696    * 6 write
gmc_v8_0.c:697    * 5 read
gmc_v8_0.c:698    * 4 exe
gmc_v8_0.c:699    * 3 reserved
gmc_v8_0.c:700    * 2 snooped
gmc_v8_0.c:701    * 1 system
gmc_v8_0.c:702    * 0 valid
gmc_v8_0.c:703    *
gmc_v8_0.c:704    * PDE format on VI:
gmc_v8_0.c:705    * 63:59 block fragment size
gmc_v8_0.c:706    * 58:40 reserved
gmc_v8_0.c:707    * 39:1 physical base address of PTE
gmc_v8_0.c:708    * bits 5:1 must be 0.
gmc_v8_0.c:709    * 0 valid
gmc_v8_0.c:710    */
```

**"VI" es el nombre del ASIC en la nomenclatura de esta generación.** Es el mismo
"VI" de `gmc_v8_0_get_vm_pde` (`L712`) y de `gmc_v8_0_vm_decode_fault` (`L1001`).

**Esto responde a los bits abiertos, con las palabras del driver:**

| bit | estado en el comentario | estado en mi resumen anterior |
|---|---|---|
| 0 valid | definido | definido |
| 1 system | definido | definido |
| 2 snooped | definido | definido |
| 3 | **`reserved`** | faltaba |
| 4 exe | definido | definido |
| 5 read | definido | definido |
| 6 write | definido | definido |
| 7-11 | **`fragment`** | "definidos, sin significado" |
| 12-39 | **base física, 4 KiB** | correcto |
| **40-63** | **`reserved`** | **52, 53, 57, 60-63 sin definición** |

**Los 24 bits altos del PTE no tienen definición en ninguna generación de este
corpus.** No es que falte buscarlos: es que el driver los reserva. `PROVEN`.

## 2 · Los bits 7-11, por dos fuentes independientes

```
gmc_v8_0.c:695        11:7 fragment
amdgpu_vm.h:70        #define AMDGPU_PTE_FRAG(x)  ((x & 0x1fULL) << 7)
```

**Cinco bits, máscara `0x1f`, desplazamiento 7, y el nombre es `FRAG`.** El
comentario dice "fragment" y el macro se llama `FRAG`, y los dos son de cinco bits
en la misma posición.

**Y ese es el campo que `130` necesita:** `amdgpu_vm_pt.c:900` escribe el `FRAG` en
el PTE, y `gmc_v8_0.c:695` dice que el hardware lo lee. **El L1 guarda un PTE por
fragmento (`130`) porque el PTE lleva su número de fragmento en cinco bits, y el
hardware lo compara para no invalidar un TLB entero.** La capacidad de `130` y el
campo del PTE son la misma cosa vista desde los dos lados. `PROVEN`.

**Y se escribe en esta GPU:** `AMDGPU_PTE_FRAG` aparece en `amdgpu_vm_pt.c` y en
`amdgpu_gmc.c`, no en ningún `gmc_v9_0.c` ni posterior. `PROVEN` por fichero.

## 3 · Lo que el propio header declara reservado para GFX8

El enum de `amdgpu_vm.h` es **compartido entre GFX8 y GFX9+**, y lo dice en el
comentario de cada campo:

```
amdgpu_vm.h:72   /* TILED for VEGA10, reserved for older ASICs  */
amdgpu_vm.h:73   #define AMDGPU_PTE_PRT      (1ULL << 51)
amdgpu_vm.h:80   /* PTE is handled as PDE for VEGA10 (Translate Further) */
amdgpu_vm.h:81   #define AMDGPU_PTE_TF       (1ULL << 56)
amdgpu_vm.h:83   /* MALL noalloc for sienna_cichlid, reserved for older ASICs  */
amdgpu_vm.h:84   #define AMDGPU_PTE_NOALLOC  (1ULL << 58)
amdgpu_vm.h:86   /* PDE Block Fragment Size for VEGA10 */
amdgpu_vm.h:87   #define AMDGPU_PDE_BFS(a)   ((uint64_t)a << 59)
```

**"reserved for older ASICs" significa exactamente GFX8.** El header lo dice.

**Y ahora, la prueba por fichero, que no depende de ningún comentario:**

| flag | ¿lo escribe algún `.c` de GFX8? | ficheros que sí |
|---|---|---|
| `AMDGPU_PTE_FRAG` | **sí** | `amdgpu_vm_pt.c`, `amdgpu_gmc.c` |
| `AMDGPU_PDE_BFS` | **no** | `gmc_v9_0/v10_0/v11_0/v12_0/v12_1`, `amdgpu_gmc.c` |
| `AMDGPU_PTE_LOG` | **no** | `gmc_v10_0.c`, `gmc_v11_0.c` |
| `AMDGPU_PTE_NOALLOC` | **no** | `gmc_v10_0.c`, `gmc_v11_0.c`, `gmc_v12_0.c` |

**`gmc_v8_0.c` no aparece en ninguna de las tres últimas filas.** `PROVEN_ABSENT`,
y por presencia/ausencia de fichero, que es más fuerte que por comentario.

**Y hay una asimetría que sólo se ve al juntar las dos mitades:** el comentario de
`gmc_v8_0.c:705` dice que **el hardware tiene** el campo "block fragment size" en
los bits 63:59 del PDE, y el header de `amdgpu_vm.h:86` dice que el macro que lo
escribe es "for VEGA10". **El campo existe en GFX8; el driver no lo usa.** No es
una contradicción: uno describe el hardware y el otro, a qué le afecta al driver.

## 4 · La homonimia: `099` y `131` no hablaban del mismo PRT

Esto es lo que faltaba, y son **dos mecanismos con el mismo nombre**:

| | `AMDGPU_PTE_PRT` | `VM_PRT_CNTL` (`0x534`) |
|---|---|---|
| qué es | un **bit del PTE**, el 51 | un **registro global** con 7 campos |
| nombre en el hardware | TILED | Page Request Trigger |
| para qué | GFX9: indicating tile | desactivar faults en un rango |
| en GFX8 | **`reserved for older ASICs`** | existe, y `131` lo documentó |
| qué hace el driver | **lo borra** (`gmc_v8_0.c:728`) | lo programa, por rango de direcciones |

**Y el texto del aviso lo dice sin ninguna ambigüedad** (`gmc_v8_0.c:770-773`):

```c
if (enable && !adev->gmc.prt_warning) {
        dev_warn(adev->dev, "Disabling VM faults because of PRT request!\n");
        adev->gmc.prt_warning = true;
}
```

**"Disabling VM faults because of PRT request"** — el PRT del registro **desactiva
los faults de VM**, y el driver lo avisa con esas palabras. `gmc_v8_0.c:728` lo que
hace es borrar un bit **reservado en esta GPU**. **No se contradicen: uno es un bit
que no existe, el otro es una política global de diagnóstico.**

**Con `131` y `099`, las tres piezas encajan y la contradicción se disuelve:
`099` observó el mecanismo global; `131` encontró el registro; `gmc_v8_0.c:728`
limpia un campo que el propio header marca como reservado para esta generación.**

## 5 · `gmc_v8_0_set_prt` completo: los siete campos y el rango

```
gmc_v8_0.c:776   VM_PRT_CNTL.CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS     = enable
gmc_v8_0.c:778   VM_PRT_CNTL.CB_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS    = enable
gmc_v8_0.c:780   VM_PRT_CNTL.TC_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS     = enable
gmc_v8_0.c:782   VM_PRT_CNTL.TC_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS    = enable
gmc_v8_0.c:784   VM_PRT_CNTL.L2_CACHE_STORE_INVALID_ENTRIES               = enable
gmc_v8_0.c:786   VM_PRT_CNTL.L1_TLB_STORE_INVALID_ENTRIES                 = enable
gmc_v8_0.c:788   VM_PRT_CNTL.MASK_PDE0_FAULT                              = enable
```

**Son siete, y todos toman el mismo valor.** Los cuatro primeros son por cliente de
memoria — `CB` = command buffer, `TC` = texture cache — y reads y writes.

**Y los dos siguientes invalidan: `L2_CACHE_STORE_INVALID_ENTRIES` y
`L1_TLB_STORE_INVALID_ENTRIES`.** Es el mismo par de invalidación que `137` documentó en
`VM_L2_CNTL2`, pero **junto al PRT**: el PRT se lleva por delante la invalidación de
la L2 y del L1 al mismo tiempo. `PROVEN`, y es la primera vez que estos dos campos
aparecen con nombre.

**Y el rango de direcciones (`L792-815`):**

```
enable  ->  PRT_APERTURE{0,1,2,3}_LOW_ADDR  = AMDGPU_VA_RESERVED_BOTTOM >> 12
            PRT_APERTURE{0,1,2,3}_HIGH_ADDR = max_pfn - (AMDGPU_VA_RESERVED_TOP >> 12)
disable ->  LOW = 0xfffffff   (o sea, -1, un rango vacío)
            HIGH = 0x0
```

**Ocho registros, cuatro aperturas, y disable es literalmente un rango vacío.** Y
el rango que se silencia va de `AMDGPU_VA_RESERVED_BOTTOM` a `max_pfn` menos
`AMDGPU_VA_RESERVED_TOP`: **las dos franjas que el driver se reserva para sí mismo.**

**Para un driver propio, esto es una advertencia de diseño, no un detalle:** si
activas el PRT, tus propias franjas reservadas dejan de generar faults. Es un
intercambio explícito, y el texto del `dev_warn` lo reconoce.

## 6 · `get_vm_pde` no hace nada

```
gmc_v8_0.c:712   static void gmc_v8_0_get_vm_pde(struct amdgpu_device *adev, int level,
gmc_v8_0.c:713                                   uint64_t *addr, uint64_t *flags)
gmc_v8_0.c:714   {
gmc_v8_0.c:715           BUG_ON(*addr & 0xFFFFFF0000000FFFULL);
gmc_v8_0.c:716   }
```

**El callback de PDE por chip, en GFX8, no añade ni quita un solo flag.** Sólo
comprueba que la dirección no tenga bits set en `0xFFFFFF0000000FFF`, es decir, en
los **bits 0-11** (alineación de 4 KiB) ni en los **bits 44-59**.

**Es decir: en esta generación el hardware no tiene flags de PDE que el driver
gestione, y el propio driver lo afirma con un cuerpo vacío.** Los flags que sí
importan — `VALID` — los pone `amdgpu_vm_pt.c`, no el callback por chip.
`PROVEN`.

**Y es coherente con el comentario de `L708`: *"bits 5:1 must be 0"*.** Un PDE de
GFX8 no tiene flags. `PROVEN_DERIVED`.

## 7 · Catorce bits de fault, no siete

`138` documentó los siete `..._ENABLE_DEFAULT`. **Hay otros siete** con el mismo
sufijo de nombre y otro sufijo, y viven en la misma máscara:

```
gmc_v8_0.c:1391   u32 bits = (RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK   |
gmc_v8_0.c:1392            DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK  |
gmc_v8_0.c:1393            PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK       |
gmc_v8_0.c:1394            VALID_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK      |
gmc_v8_0.c:1395            READ_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK       |
gmc_v8_0.c:1396            WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK      |
gmc_v8_0.c:1397            EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT_MASK);
```

**Catorce, en dos familias: `..._ENABLE_DEFAULT` (qué se sirve) y
`..._ENABLE_INTERRUPT` (si se avisa).** Y `gmc_v8_0_vm_fault_interrupt_state`
(`L1385-1425`) pone y quita **los catorce a la vez** (`tmp |= bits`,
`tmp &= ~bits`), sobre **`VM_CONTEXT0_CNTL` y `VM_CONTEXT1_CNTL` los dos**.

**Esto es la pieza que le faltaba a `138` para que la historia de `099` fuera
completa:** `gmc_v8_0_late_init` (`L1068`) pide el IRQ de fault **si y sólo si
`vm_fault_stop != ALWAYS`**, y al pedirlo se encienden los siete bits
`_ENABLE_INTERRUPT`. **Con el valor por defecto de esta máquina, los catorce están
activos: se avisa y se sirve la página.** `PROVEN_DERIVED`.

**Y `138` queda corregido en un punto:** no son siete bits dispersos, son **dos
familias de siete**, y cada familia tiene su máscara propia. La tabla de `138`
debía llevar las dos columnas.

## 8 · Las anchuras, cruzadas por tres fuentes

```
gmc_v8_0.c:1127   amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
gmc_v8_0.c:1133   adev->gmc.mc_mask       = 0xffffffffffULL;         /* 40 bit MC */
gmc_v8_0.c:1134   adev->gmc.pte_addr_mask = 0x000000FFFFFFF000ULL;   /* 40 bit PA */
gmc_v8_0.c:1136   dma_set_mask_and_coherent(adev->dev, DMA_BIT_MASK(40));
gmc_v8_0.c:1141   adev->need_swiotlb = drm_need_swiotlb(40);
```

**La llamada de `L1127` es la geometría completa en un sitio: 64 bits de VA, 9 de
fragmento, 1 de nivel, y 40 de tamaño de VM.** Y las otras cuatro líneas dicen 40
una y otra vez, por cuatro caminos distintos: máscara del MC, máscara del PTE, DMA
del kernel, y SWIOTLB.

**Y el comentario del PTE lo corrobora por quinta vez:** `39:12 physical page base`
son 28 bits de página más 12 de desplazamiento, o sea **40 bits de dirección
física**. `PROVEN`, y cinco fuentes coinciden.

**El `0x000000FFFFFFF000` de `L1134` es la máscara del PTE entero, y es
`0xFFF` en el bajo y 40 bits en el alto — exactamente lo que espera el hardware,
menos los bits de flags.** Un driver propio puede derivar de ahí qué se preserva al
escribir un PTE: los flags de `L691-702`, nada más.

## 9 · Los VMID, y por qué el registro se parte en dos bloques

```
gmc_v8_0.c:1162   /*
gmc_v8_0.c:1163    * number of VMs
gmc_v8_0.c:1164    * VMID 0 is reserved for System
gmc_v8_0.c:1165    * amdgpu graphics/compute will use VMIDs 1-7
gmc_v8_0.c:1166    * amdkfd will use VMIDs 8-15
gmc_v8_0.c:1167    */
gmc_v8_0.c:1168   adev->vm_manager.first_kfd_vmid = 8;
```

**Y el reparto de registros de `gmc_v8_0.c:673-676` parte exactamente en 8.** No es
un accidento de direccionamiento: **el mapa de registros refleja el mapa de
usuarios.** Los siete VMID de un cliente gráfico van en el bloque `0x54f-0x556`, y
los ocho de KFD en `0x50e-0x515`. `PROVEN_DERIVED`, y es una razón que un
documento de registro no daría.

**Lo que el registro del GART recibe, y lo que no** (`L886-897`, que es el bloque
que `138` nombra sólo en su parte del contexto 1):

```
L887   VM_CONTEXT0_PAGE_TABLE_START_ADDR = gart_start >> 12
L888   VM_CONTEXT0_PAGE_TABLE_END_ADDR   = gart_end   >> 12
L889   VM_CONTEXT0_PAGE_TABLE_BASE_ADDR  = table_addr >> 12
L890   VM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR = dummy_page_addr >> 12
L892   VM_CONTEXT0_CNTL2 = 0
L894   VM_CONTEXT0_CNTL.ENABLE_CONTEXT      = 1
L895   VM_CONTEXT0_CNTL.PAGE_TABLE_DEPTH    = 0
L896   VM_CONTEXT0_CNTL.RANGE_PROTECTION_FAULT_ENABLE_DEFAULT = <value>
```

**Esto cierra el `NOT_DETERMINED` que `138` dejó abierto.** El contexto 0 **sí**
recibe `PAGE_TABLE_DEPTH`, y vale **0** (`L895`). **El GART es un nivel de página
— 1024 entradas, 8 KiB — y los clientes son dos niveles, valor 1 (`L925`).** Y
`L908-909` da a los contextos 1-15 la ventana completa: `START = 0`,
`END = max_pfn - 1`.

**Y el `VM_CONTEXT1_CNTL2 = 4` de `L922` sí tiene nombre:**

```
VM_CONTEXT1_CNTL2__CLEAR_PROTECTION_FAULT_STATUS_ADDR_MASK  0x1
VM_CONTEXT1_CNTL2__ENABLE_CLEAR_..._WHEN_INVALIDATE_CONTEXT 0x2
VM_CONTEXT1_CNTL2__ENABLE_INTERRUPT_PROCESSING_FOR_SUBSEQUENT_FAULTS_PER_CONTEXT 0x4
VM_CONTEXT1_CNTL2__ALLOW_SUBSEQUENT_PROTECTION_FAULT_STATUS_ADDR_UPDATES 0x8
VM_CONTEXT1_CNTL2__WAIT_FOR_IDLE_WHEN_INVALIDATE 0x10
```

**`4` = `ENABLE_INTERRUPT_PROCESSING_FOR_SUBSEQUENT_FAULTS_PER_CONTEXT`.** Es decir:
tras un fault, el hardware sigue informando de los siguientes. **Y es coherente con
`L1450`, `WREG32_P(mmVM_CONTEXT1_CNTL2, 1, ~1)`, que limpia el bit 0
(`CLEAR_PROTECTION_FAULT_STATUS_ADDR`).** El driver escribe un 4 sin nombrar porque
el campo existe pero no tiene un `REG_SET_FIELD` que lo cubra; se puede nombrar
igualmente. `PROVEN`.

**Mientras que el contexto 0 recibe `0` en `L892`, es decir, ni el bit 0 ni el 2: el
GART no informa de faults de forma reiterada.** La asimetría es deliberada: el
contexto 0 es del kernel y sus faults no se reportan.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El formato bit a bit del PTE de GFX8 | `PROVEN` (`gmc_v8_0.c:691-702`) |
| Los bits 40-63 del PTE están reservados | `PROVEN` (el comentario lo dice) |
| El bit 3 está reservado | `PROVEN` |
| Los bits 7-11 son el fragmento | `PROVEN` (dos fuentes) |
| `AMDGPU_PDE_BFS` no se escribe en GFX8 | `PROVEN_ABSENT` (por fichero) |
| `AMDGPU_PTE_LOG` y `NOALLOC` no se escriben en GFX8 | `PROVEN_ABSENT` |
| El campo existe en el hardware pero el driver no lo usa | `PROVEN_DERIVED` |
| `AMDGPU_PTE_PRT` y `VM_PRT_CNTL` son distintos | `PROVEN` |
| `099` resuelto | `PROVEN_DERIVED` |
| Los siete campos de `VM_PRT_CNTL`, con nombre | `PROVEN` |
| El PRT silencia las franjas reservadas del driver | `PROVEN` |
| `get_vm_pde` no modifica flags en GFX8 | `PROVEN` (cuerpo vacío) |
| Un PDE de GFX8 no tiene flags | `PROVEN_DERIVED` |
| Hay catorce bits de fault, en dos familias | `PROVEN` |
| `PAGE_TABLE_DEPTH` = 0 para el GART, 1 para clientes | `PROVEN` (`L895`, `L925`) |
| `VM_CONTEXT1_CNTL2 = 4` = interrumpir faults subsecuentes | `PROVEN` |
| Las anchuras de 40 bits, por cinco fuentes | `PROVEN` |
| El registro de PTBA se parte en la frontera KFD | `PROVEN_DERIVED` |
| Qué hace el hardware con los 24 bits reservados | **`NOT_DETERMINED`** — reservado es reservado |
| `L2_CACHE_STORE_INVALID_ENTRIES` y su hermano, qué vacían | **`NOT_DETERMINED`** — el nombre no lo dice |
| Por qué el contexto 0 no habilita faults subsecuentes | **`NOT_DETERMINED`** |
| Los valores reales de estos registros tras el reset | **`NOT_PROVEN`** — los `RREG32` |

**La segunda fila del final es la que más importa para un driver propio: el PRT
invalida la caché L2 y el L1, y no hay nada en el corpus que diga qué entrada
 invalida ni de quién lo invalida.** Es exactamente el hueco que dejé anotado al principio de esta
tanda ("cuál caché pesa más en el flush obligatorio: `NOT_DETERMINED`"), y aquí
aparece un segundo invalidador que no es el de la cadena del PTE. **Son dos, no
uno.**

## Procedencia

- `STATIC` -- `gmc_v8_0.c:411-461`, `gmc_v8_0.c:661-666`, `gmc_v8_0.c:668-689`,
  `gmc_v8_0.c:691-710`, `gmc_v8_0.c:712-729`, `gmc_v8_0.c:766-816`,
  `gmc_v8_0.c:829-946`, `gmc_v8_0.c:992-1021`, `gmc_v8_0.c:1045-1072`,
  `gmc_v8_0.c:1123-1187`, `gmc_v8_0.c:1385-1425`, `gmc_v8_0.c:1440-1505`,
  `amdgpu_vm.h:57-100`, `amdgpu_vm_pt.c:900` (`FRAG`),
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h` (`VM_CONTEXT1_CNTL2__*`,
  `MC_HUB_MISC_HUB_CG__*`).
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `138` (los protection faults y la geometría — esta nota completa
  su `NOT_DETERMINED` del contexto 0 y corrige su cuenta de bits), `137` (la
  configuración de TLB), `136` (la cadena de coherencia), `133` (el MTYPE),
  `132` (la geometría), `131` (`VM_PRT_CNTL`), `130` (el L1 por fragmento),
  `099` (**resuelto aquí, por homonimia**), `104` (el mapa de VMID), `083`
  (`dst`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Busqué `gmc_v8_0_vm_decode_fault` y mi `awk` no tenía cota superior, así que
imprimió el fichero entero. Lo que buscaba eran cinco líneas; me salieron mil.**

**Y en las mil estaba el formato bit a bit del PTE, escrito por el driver, veinte
líneas por encima de donde yo miraba.** `gmc_v8_0.c:691-710`. Veinte líneas que
responden a la pregunta más antigua que tenía abierta en este proyecto — qué son
los bits altos del PTE — y que llevaba siete notas sin aparecer.

**La lección no es sobre `awk`. Es esta: he pasado esta tanda entera entrando por
el símbolo que ya sabía.** `gmc_v8_0_emit_flush_gpu_tlb` porque `128` me apuntó
`VM_L2_CNTL3`, `gmc_v8_0_process_interrupt` porque `138` me apuntó
`set_fault_enable_default`, `gmc_v8_0_vm_decode_fault` porque me había quedado
abierto el `NOT_DETERMINED` de sus bits.

**Las tres veces, el bloque que hacía falta estaba entre veinte y sesenta líneas
antes del que yo abría, en el mismo fichero.** Y dos de las tres veces, en la misma
función que ya tenía leída.

*Un fichero de 1800 líneas con veinte comentarios de formato no se recorre por
símbolo. Se recorre una vez entero.* Y el coste de recorrerlo entero son treinta
segundos. **El coste de no hacerlo ha sido siete notas, y un `awk` sin cota
superior me lo acaba de resolver por accidente.**
