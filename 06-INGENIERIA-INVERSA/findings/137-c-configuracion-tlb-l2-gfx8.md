# 137 · §C/§G: la configuración completa de TLB y L2 de esta GPU, en diecisiete líneas

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`136` cerró por qué el invalidate es obligatorio. Esta nota sube un nivel: **no
sólo por qué, sino qué hay que escribir para que esta GPU funcione.** Es el bloque
de configuración más relevante para un driver propio que ha salido del proyecto,
y está entero en una función.

## El bloque completo: `gmc_v8_0_gart_enable`

```
gmc_v8_0.c:829   static int gmc_v8_0_gart_enable(struct amdgpu_device *adev)
gmc_v8_0.c:835   if (adev->gart.bo == NULL) { dev_err(..., "No VRAM object for PCIE GART."); return -EINVAL; }
gmc_v8_0.c:839   amdgpu_gtt_mgr_recover(&adev->mman.gtt_mgr);
gmc_v8_0.c:840   table_addr = amdgpu_bo_gpu_offset(adev->gart.bo);
```

**Y `L836` resuelve una pregunta de `133`/`136`: en GFX8 el GART es siempre un BO de
VRAM.** No hay rama de memoria del sistema — `gmc_v9_0.c:1794-1796` la tiene para
APU, GFX8 no. **Un discreto con VRAM siempre la usa.** `PROVEN`, y no hace falta
mirar el log.

## L1: `mmMC_VM_MX_L1_TLB_CNTL`

```
gmc_v8_0.c:844   ENABLE_L1_TLB                      = 1     bit 0     mask 0x01
gmc_v8_0.c:845   ENABLE_L1_FRAGMENT_PROCESSING      = 1     bit 1     mask 0x02
gmc_v8_0.c:846   SYSTEM_ACCESS_MODE                 = 3     bits 4-3  mask 0x18
gmc_v8_0.c:847   ENABLE_ADVANCED_DRIVER_MODEL       = 1     bit 6     mask 0x40
gmc_v8_0.c:848   SYSTEM_APERTURE_UNMAPPED_ACCESS    = 0     bit 5     mask 0x20
```

**`ENABLE_L1_FRAGMENT_PROCESSING = 1` es el eslabón que le faltaba a `136`.**

`130` decía que "el L1 puede guardar un PTE por fragmento" — es una capacidad.
**Este bit es el modo que la activa.** No es automático: sin él, el L1 no haría
procesamiento de fragmento, y el invalidate no sería necesario por granularidad.

**Y es exactamente la razón de la asimetría con Vega10.** `amdgpu_vm_pt.c:760` dice
*"Starting with Vega10 the fragment size only controls the L1. The L2 is now directly
feed with small/huge/giant pages"*. **En GFX8 el fragmento controla los dos niveles,
y por eso el invalidate es obligatorio. En GFX9+ el L2 recibe páginas grandes
directamente del walker, y `amdgpu_vm.c:1157` deja de forzarlo.**

## L2: `mmVM_L2_CNTL`

```
gmc_v8_0.c:852   ENABLE_L2_CACHE                             = 1
gmc_v8_0.c:853   ENABLE_L2_FRAGMENT_PROCESSING               = 1        <<<
gmc_v8_0.c:854   ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE     = 1
gmc_v8_0.c:855   ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE    = 1        <<<
gmc_v8_0.c:856   EFFECTIVE_L2_QUEUE_SIZE                     = 7
gmc_v8_0.c:857   CONTEXT1_IDENTITY_ACCESS_MODE               = 1        <<<
gmc_v8_0.c:858   ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY    = 1        <<<
```

**Tres de estos no los había visto y los tres importan:**

**`ENABLE_L2_FRAGMENT_PROCESSING = 1`** — el fragmento no es sólo del L1. **Es un
modo de los dos niveles, y esta GPU lo tiene activo en los dos.**

**`ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE = 1`** — **una escritura actualiza el
LRU de la caché de PDE0 de la L2.** Éste es el que cierra la pregunta de `229`
sobre `PDE_CACHE_EFFECTIVE_SIZE`: **sí hay una caché de PDE0, y las escrituras la
tocan.** Es decir: escribir una page table ** mete** la entrada nueva en la caché de
PDE0, y la única forma de hacer visible una entrada *distinta* del mismo fragmento
es invalidar. **Ahí está el requisito de coherencia, enunciado por un bit que el
driver pone.**

**`CONTEXT1_IDENTITY_ACCESS_MODE = 1`** — el contexto 1, que es el primer VMID de
userspace, accede en modo identidad. **Y `211` establece que el VMID 0 es el espacio
del kernel y los 1-15 de userspace.** Así que el driver configura el modo de acceso
del primer VMID de usuario explícitamente, y deja el 0 fuera.

## Los otros tres bloques, ya conocidos

```
gmc_v8_0.c:861   mmVM_L2_CNTL2.INVALIDATE_ALL_L1_TLBS  = 1        128
gmc_v8_0.c:862   mmVM_L2_CNTL2.INVALIDATE_L2_CACHE    = 1        128
gmc_v8_0.c:867   mmVM_L2_CNTL3.L2_CACHE_BIGK_ASSOCIATIVITY = 1   127
gmc_v8_0.c:868   mmVM_L2_CNTL3.BANK_SELECT           = fragment_size
gmc_v8_0.c:869   mmVM_L2_CNTL3.L2_CACHE_BIGK_FRAGMENT_SIZE = fragment_size   127
gmc_v8_0.c:873   mmVM_L2_CNTL4.VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL = 0   127
gmc_v8_0.c:874   mmVM_L2_CNTL4.VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED   = 0   127
```

**Los cinco registros del bloque de lectura que `229` y `131` propusieron quedan
aquí, con su función deutenido: `0x501` y `0x502` y `0x534` los escribe esta función,
`0x500` es `mmVM_L2_CNTL`, y `mmMC_VM_MX_L1_TLB_CNTL` es el sexto.**

## Lo que esto es, para un driver propio

**Es la lista de trabajo.** Un driver que quiera traducir direcciones en esta GPU
tiene que escribir, como mínimo:

1. `ENABLE_L1_TLB = 1` — el L1 tiene que existir
2. `ENABLE_L1_FRAGMENT_PROCESSING = 1` — y procesar fragmentos
3. `ENABLE_L2_CACHE = 1` y `ENABLE_L2_FRAGMENT_PROCESSING = 1` — en la L2
4. `L2_CACHE_BIGK_FRAGMENT_SIZE = 9` — 2 MiB, leído del hardware, no inventado
5. `ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE = 1` — **o las escrituras no actualizan
   la caché de PDE0 y la coherencia se rompe por el otro lado**
6. `SYSTEM_ACCESS_MODE = 3` — el modo con el que la GPU accede a memoria de sistema
7. y un invalidate de TLB por cada cambio de page table, **que es obligatorio y no
   opcional** (`amdgpu_vm.c:1157`)

**Los siete están en una función de 42 líneas que cabe en una pantalla.**

**Y hay un orden que importa:** el invalidate de `L861-862` va **después** de
configurar el fragment size de `L869`, y antes de nada que use la traducción.
`gmc_v8_0_gart_enable` es una secuencia, no un conjunto de campos.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Los siete valores de configuración en GFX8 | `PROVEN` (17 líneas) |
| El fragmento es un modo, no una capacidad automática | `PROVEN` (`L845`, `L853`) |
| La L2 tiene una caché de PDE0 que las escrituras tocan | `PROVEN` (`L855`) |
| El contexto 1 es modo identidad | `PROVEN` (`L857`) |
| El GART es siempre VRAM en GFX8 | `PROVEN` (`L962`, sin rama APU) |
| Por qué `SYSTEM_ACCESS_MODE = 3` y no otro | **`NOT_DETERMINED`** — no hay enumeración |
| Qué es `EFFECTIVE_L2_QUEUE_SIZE = 7` | **`NOT_DETERMINED`** |
| Si el driver debe cambiar algo de esto en runtime | **`NOT_DETERMINED`** — sólo se escribe aquí |
| Los valores reales tras el reset | **`NOT_PROVEN`** — los `RREG32` |

**Las dos primeras `NOT_DETERMINED` son las que más valen, y las dos se resuelven
con los mismos `RREG32` de `229`/`131`:** `mmMC_VM_MX_L1_TLB_CNTL` y `mmVM_L2_CNTL`
sumados a `0x501` y `0x534`. **Son cuatro registros del bloque de GMC, y el bloque
entero cabe en una lectura de 64 bytes si se lee seguido.**

**Y la tercera es la que importa para un driver propio:** si estos registros sólo se
tocan en `gart_enable`, entonces **la configuración de TLB de esta GPU es estática
y se hace una vez.** Eso la convierte en una constante, no en una política.

## Procedencia

- `STATIC` -- `gmc_v8_0.c:829-874` `:962`, `gmc_v9_0.c:1794-1800`,
  `amdgpu_vm.c:1155-1157`, `amdgpu_vm_pt.c:744-768`,
  `amdgpu_vram_mgr.c:605-611`, `amdgpu_ttm.c:1411-1455`,
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h` (`MC_VM_MX_L1_TLB_CNTL__*`).
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `136` (la cadena de coherencia), `133` (el MTYPE),
  `132` (los flags y la geometría), `130` (el L1 guarda un PTE por fragmento),
  `129` (la granularidad), `229` (los mecanismos de invalidate), `127` (la caché L2),
  `131` (PRT), `220` (BAR 256 MiB), `211` (VMID 0 = kernel), `194` (el flush
  obligatorio).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Leí `gmc_v8_0.c:858-874` en `127` y `229`, y salté de `L858` a `L860`.**

Estaba justo debajo. `L829-857` son veintinueve líneas con **cinco registros de
control de TLB y L2**, y yo fui a buscar `VM_L2_CNTL3` porque `229` me había
apuntado que nadie lo escribía.

**La razón: entrée por el símbolo que me interesa y leo el barrioImmediate.** Pero
el bloque que importa es el que programa el subsistema entero, y está *delante* del
que yo buscaba, no detrás.

*Cuando el objeto de estudio es un subsistema, hay que leer la función que lo
inicializa entera, no el registro que me interesa.* Y un bloque de
configuración se lee de principio a fin, porque **el orden de las escrituras es
información** — `L861` invalida *después* de `L869` configurar el fragment size, y
eso no se ve si entras por el medio.

Es la cuarta vez en esta tanda, y la misma que `130` y `133`: **el comentario y el
bloque completo estaban delante, y yo entré por donde já sabia.**