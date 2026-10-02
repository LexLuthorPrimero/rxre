# 054 · Las dos máscaras de dirección MC y PTE, y la reproducción exacta de los cuatro números de colocación

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CUBRE=AGENTS.md §F MEMORY SYSTEM ("separar GPUVM translation de MC address decoding")`

## CUDA principal

Hay **dos** máscaras de dirección física, no una, y ambas se comentan como
"40 bit" aunque sólo una cubre los 40 bits. La distinción es exactamente la que
§F pide separar: una es el tope del espacio MC, la otra es el campo de dirección
que hay que escribir dentro de un PTE.

Y con ellas se reproducen **exactamente** los cuatro números de VRAM y GART que el
host imprime al arrancar. No se aproximan: coinciden bit a bit, incluido el
alineamiento final a 4 GiB.

Control de duplicación **antes** de derivar: `mc_mask` · `MC address` ·
`MC_VM_FB` · `MAX_MC` · `vram_base` · `address decoding` → **0 hallazgos** cada uno.

## 1 · Las dos máscaras, y por qué distinguirlas importa

`gmc_v8_0.c:1129-1134`:

```c
/* Set the internal MC address mask
 * This is the max address of the GPU's internal address space.
 */
adev->gmc.mc_mask        = 0xffffffffffULL;        /* 40 bit MC */
adev->gmc.pte_addr_mask  = 0x000000FFFFFFF000ULL;  /* 40 bit PA */
```

| máscara | valor | bits útiles | qué es |
|---|---|---|---|
| `mc_mask` | `0x0000_00FF_FFFF_FFFF` | **40** | tope del espacio de direcciones MC |
| `pte_addr_mask` | `0x0000_00FF_FFFF_F000` | **28** | base de página alineada: 40 bits + los 12 de offset a cero |

Los dos comentarios dicen "40 bit". Sólo uno tiene 40 bits de rango. La diferencia
son los **12 bits bajos**, que `pte_addr_mask` fuerza a cero porque es la dirección
de una página de 4 KiB (`AMDGPU_GPU_PAGE_SIZE = 4096`, `amdgpu_gart.h:35`).

**Para un driver propio esto no es cosmético.** Un PTE mal alineado no falla con
un error: `gmc_v8_0_get_vm_pde` lo detecta, pero sólo en la ruta de PDE
(`BUG_ON(*addr & 0xFFFFFF0000000FFFULL)`, `gmc_v8_0.c:715`), y no en la de PTE.

## 2 · `mc_mask` por generación: 40 bits hasta GFX8, 48 después

| ASIC | `mc_mask` | bits |
|---|---|---|
| `gmc_v6_0.c:838` | `0xffffffffff` | 40 |
| `gmc_v7_0.c:1018` | `0xffffffffff` | 40 |
| **`gmc_v8_0.c:1133`** | **`0xffffffffff`** | **40** ← esta GPU |
| `gmc_v9_0.c:1996` | `0xffffffffffff` | 48 |
| `gmc_v10_0.c:849` | `0xffffffffffff` | 48 |
| `gmc_v11_0.c:823` | `0xffffffffffff` | 48 |
| `gmc_v12_0.c:920` | `AMDGPU_GMC_HOLE_MASK` | 64 |

GFX12 cambia de modelo: usa un *hole mask*, no un tope. El corte está entre GFX8 y
GFX9.

El mismo límite de 40 bits aparece tres veces en GFX8 y por tres caminos
distintos: `mc_mask` (L1133), `pte_addr_mask` (L1134),
`dma_set_mask_and_coherent(DMA_BIT_MASK(40))` (L1136). Y
`drm_need_swiotlb(40)` (L1141) deriva de ahí.

## 3 · El "hueco GMC" no aplica a esta GPU

`amdgpu_gmc.c:298-299`:

```c
/*To avoid the hole, limit the max mc address to AMDGPU_GMC_HOLE_START*/
u64 max_mc_address = min(adev->gmc.mc_mask, AMDGPU_GMC_HOLE_START - 1);
```

Con `AMDGPU_GMC_HOLE_START = 0x0000800000000000` (`amdgpu_gmc.h:37`, para
`max_level != 4`):

```
min(0x0000_00FF_FFFF_FFFF,  0x0000_7FFF_FFFF_FFFF)
  = 0x0000_00FF_FFFF_FFFF        ← gana mc_mask
```

**En 40 bits el hueco no existe dentro del rango alcanzable.** El `min` está ahí
para las generaciones de 48 bits, donde `0x800000000000` sí cae dentro de
`mc_mask`. `AGENTS.md:121` dice que "GMC hole participa mediante max_mc_address":
para esta GPU es cierto que participa en el `min`, y es **falso** que tenga efecto
sobre el resultado. Verificado por aritmética, no por lectura.

## 4 · Reproducción exacta de los cuatro números observados

Entradas: `mc_mask` de §2, y del log de arranque de hoy:

```
VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF
GART: 256M  0x000000FF00000000 - 0x000000FF0FFFFFFF
```

Función: `amdgpu_gmc_gart_location`, `amdgpu_gmc.c:294-335`, política
`AMDGPU_GART_PLACEMENT_BEST_FIT` (`AGENTS.md:120`).

```
L299  max_mc_address = min(mc_mask, HOLE_START-1) = 0xffffffffff
L304  size_bf        = fb_start                     = 0xf400000000   (976 GiB)
L305  size_af        = max_mc + 1 - ALIGN(fb_end+1, 4G)
                                                = 0xb00000000     ( 44 GiB)
L307  gart_size(256 MiB) > max(size_bf, size_af)?  no → sin recorte
L324  BEST_FIT: size_bf >= gart && size_bf < size_af
               976 GiB >= 0.25 GiB  = TRUE
               976 GiB <  44 GiB    = FALSE
               → condición FALSE   → rama else, L328
L328  gart_start = max_mc_address - gart_size + 1
               = 0xffffffffff - 0x10000000 + 1 = 0xfff0000000
L332  gart_start &= ~(4GiB - 1)                   = 0x0ff00000000
L333  gart_end   = gart_start + gart_size - 1    = 0x0ff0fffffff
```

| | derivado | observado | coincide |
|---|---|---|---|
| `gart_start` | `0x000000FF00000000` | `0x000000FF00000000` | **sí** |
| `gart_end` | `0x000000FF0FFFFFFF` | `0x000000FF0FFFFFFF` | **sí** |

**Los cuatro números de VRAM y GART del log reproducen bit a bit desde la
fórmula.** No es una aproximación: el `BEST_FIT` cae en la rama `else` precisamente
porque `size_bf` (976 GiB) es mayor que `size_af` (44 GiB), así que el hueco grande
es el de *antes* de la VRAM, y aun así el GART se coloca arriba. La condición de la
línea 324 no es "elige el hueco más grande" sino "elige 0 si el hueco de abajo es
mayor que el de arriba"; aquí es al revés y cae arriba.

## 5 · Lo que NO se explica aquí, y no se afirma

- Por qué `size_bf` es 976 GiB: depende de `fb_start`, que viene de
  `MC_VM_FB_LOCATION` (`AGENTS.md:118`) y de la disposición de VRAM detectada del
  panel. No he rastreado su producer.
- `amdgpu_gmc_agp_location` (`amdgpu_gmc.c:349-362`) recoloca el AGP **después**
  del GART, y usa una granularidad de **16 GiB** (`sixteen_gb = 1ULL << 34`, L351),
  no de 4. No he reproducido sus números.

## 6 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| hay dos máscaras, `mc_mask` y `pte_addr_mask` | FACT | **PROVEN** |
| sólo `mc_mask` tiene 40 bits; `pte_addr_mask` 28 | DERIVATION | **PROVEN_DERIVED** |
| `mc_mask` pasa de 40 a 48 bits entre GFX8 y GFX9 | FACT | **PROVEN** (4+3 ficheros) |
| el hole GMC no tiene efecto en 40 bits | DERIVATION | **PROVEN_DERIVED** |
| los 4 números de VRAM/GART reproducen bit a bit | DERIVATION | **PROVEN_DERIVED** |
| `BEST_FIT` no significa "el hueco más grande" | DERIVATION | **PROVEN_DERIVED** |
| producer de `fb_start` | — | **NOT_DETERMINED**, no rastreado |
| números de `agp_location` | — | **NOT_DETERMINED**, granularidad 16 GiB |

## Lo que este hallazgo NO cierra

No cierra §F. Lo que hace es separar sus dos mitades con números: la
**dirección MC** (`mc_mask`, 40 bits, corte generational en GFX9) y el **campo de
dirección del PTE** (`pte_addr_mask`, 40−12 bits), y reproducir la colocación de
VRAM y GART desde la fórmula. Sigue faltando la traducción de dirección *GPU a
dirección física*, que es donde el PTE entra.

## Nota de proceso

El primer cálculo numérico dio `gart_start = 0xfff0000000` y **no coincidió** con
el observado. La causa: apliqué la fórmula de L328 pero no el `&= ~(four_gb - 1)`
de L332, que está tres líneas más abajo y es fácil no ver porque no está en el
`switch`. Aplicado, coincide exacto. Los cuatro números del log llevan ahí desde
las 05:49 de hoy y ninguno de los 33 hallazgos del proyecto los había reproducido.