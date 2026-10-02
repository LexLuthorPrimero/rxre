# 023 · El productor de PTE en GFX8: SDMA_OP_GEN_PTEPDE, 9 dwords, y la puerta CPU cerrada por diseño

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `GPU INTACTA`
`CONTINUES=017, 018, 019, 021`
`CORRECTED_BY=035` **RETRACTADO POR 043 — el `count` de este documento era el correcto, y
la corrección de 035 estaba equivocada.** 035 leyó `sdma_v4_0.c` —la ruta de
`amdgpu_discovery.c`, que no corre en Polaris12— en vez de `sdma_v3_0.c`, que sí corre
(`vi.c:2107` añade `sdma_v3_1_ip_block`, definido en `sdma_v3_0.c:1693`). El nombre correcto
del opcode en este ASIC es `SDMA_OP_GEN_PTEPDE`, que es justo el que este documento cita.
Ver `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md`. El resto de este documento —el
writer CPU, PRT como apertura, `block_size`, la inexistencia de un tercer productor— no
cambia.

## CUDA principal

El writer de page tables de GFX8 está cerrado de extremo a extremo. Es un paquete SDMA de
**9 dwords, opcode 12 (`SDMA_OP_GEN_PTEPDE`)**, no una función de CPU. La función de CPU
existe, es correcta, y está deliberadamente cerrada por dos condiciones independientes en
`amdgpu_vm_init_entities` / `amdgpu_vm_make_compute`.

Consecuencia para el driver propio: **no hace falta escribir un PTE a mano. Hace falta
emitir un paquete.** La codificación de flags es la de `amdgpu_vm.h:57-88`, y el hardware
la aplica — `GEN_PTEPDE` significa literalmente "genera el PTE/PDE desde estos operandos".

## Alcance exacto

1. Localizar todo productor de entradas de tabla alcanzable en Polaris12.
2. Resolver su encoding completo hasta el campo.
3. Determinar por qué el writer CPU es inalcanzable y si es una decisión o una limitación.
4. Clasificar PRT en GFX8.

## Criterio de terminación (cumplido)

Dos productores localizados (`amdgpu_gmc_set_pte_pde` CPU, `sdma_v3_0_vm_*` SDMA) y todas
sus rutas de llamada. `PROVEN` que no existe un tercer productor.

---

## 1 · Los dos productores, y cuál gana

```
amdgpu_gmc_set_pte_pde()  amdgpu_gmc.c:163     CPU, writeq() directo
sdma_v3_0_vm_set_pte_pde  sdma_v3_0.c:982      SDMA_OP_GEN_PTEPDE
sdma_v3_0_vm_write_pte    sdma_v3_0.c:952      SDMA_OP_WRITE / SUBOP_WRITE_LINEAR
sdma_v3_0_vm_copy_pte     sdma_v3_0.c:925      SDMA_OP_COPY  / SUBOP_COPY_LINEAR
```

El CPU writer es `amdgpu_gmc.c:163-178`, cinco líneas:

```c
value = addr & adev->gmc.pte_addr_mask;   /* 0x000000FFFFFFF000ULL, gmc_v8_0.c:1128 */
value |= flags;
writeq(value, ptr + (gpu_page_idx * 8));  /* 8 bytes por entrada */
```

`ptr` es `void __iomem *` y el índice se multiplica por 8. Es la codificación del PTE
completa en una instrucción.

## 2 · El writer efectivo: `SDMA_OP_GEN_PTEPDE`, 9 dwords

`sdma_v3_0.c:982-997`, verbatim:

```c
ib->ptr[ib->length_dw++] = SDMA_PKT_HEADER_OP(SDMA_OP_GEN_PTEPDE);   /* opcode */
ib->ptr[ib->length_dw++] = lower_32_bits(pe);      /* dst addr  */
ib->ptr[ib->length_dw++] = upper_32_bits(pe);
ib->ptr[ib->length_dw++] = lower_32_bits(flags);   /* mask      */
ib->ptr[ib->length_dw++] = upper_32_bits(flags);
ib->ptr[ib->length_dw++] = lower_32_bits(addr);    /* value     */
ib->ptr[ib->length_dw++] = upper_32_bits(addr);
ib->ptr[ib->length_dw++] = incr;                    /* increment size */
ib->ptr[ib->length_dw++] = 0;                       /* dw5 = 0 */
ib->ptr[ib->length_dw++] = count;                   /* number of entries */
```

`SDMA_OP_GEN_PTEPDE = 12` (`tonga_sdma_pkt_open.h:37`, header que incluye `sdma_v3_0.c:48`).

**Esto refuta la lectura de `AGENTS.md:127` — "CPU page-table writer inalcanzable" — por la
razón equivocada.** El writer CPU es inalcanzable por dos condiciones, y la segunda es
geométrica, no de política:

```
amdgpu_vm.c:2595   vm->use_cpu_for_update = !!(vm_update_mode & AMDGPU_VM_USE_CPU_FOR_GFX);
amdgpu_vm.c:2600   WARN_ONCE(vm->use_cpu_for_update && !amdgpu_gmc_vram_full_visible(&adev->gmc),
                             "CPU update of VM recommended only for large BAR system\n");
```

`amdgpu_gmc_vram_full_visible` (`amdgpu_gmc.h:396-401`) devuelve
`real_vram_size == visible_vram_size`. Para una RX550 de 2 GiB con BAR de 256 MiB eso es
falso, así que aunque `vm_update_mode` dijera CPU, saldría el warning y el propio driver avisa
de que es una mala idea. La condición es `POLICY` (el parámetro) sobre `HARDWARE` (el BAR),
y el hardware no cede.

**Corrijo el `REQUIREMENT` que de aquí sale**: el driver propio no necesita un writer de PTE
por CPU si su BAR expone toda la VRAM, y no lo tiene. La pregunta real es si necesita un
*writer por CPU para la GART*, que es un camino distinto: `amdgpu_gart_map`
(`amdgpu_gart.c:354`) escribe la tabla GART con `amdgpu_gmc_set_pte_pde` sobre
`adev->gart.ptr`, y esa tabla **no depende de `vm_update_mode` ni de `vram_full_visible`**.
`gmc_v8_0_flush_gpu_tlb_pasid` lee `ATC_VMID0_PASID_MAPPING` (`gmc_v8_0.c:627`) y escribe
`mmVM_INVALIDATE_REQUEST` con máscara CPU. El path GART sí tiene writer CPU.

| Tabla | Productor CPU | ¿Depende de `vm_update_mode`? | ¿Depende de BAR completo? |
|---|---|---|---|
| GPUVM PT (VMID 1-15) | sí | **sí** | **sí** → inalcanzable |
| GART (VMID 0) | sí | no | no |

## 3 · PRT en GFX8: no es un tipo de entrada, es un mecanismo de aperture

`AMDGPU_PTE_PRT` = bit 51 (`amdgpu_vm.h:73`), comentado *"TILED for VEGA10, reserved for older
ASICs"*. En el PTE de GFX8 los bits 40-63 están reservados (`gmc_v8_0.c:686`), así que el bit
51 no tiene dónde vivir.

Consumidores del bit, por ASIC:

| ASIC | `gmc_v*_0.c` | acción |
|---|---|---|
| GFX6 | `:385` | `*flags &= ~AMDGPU_PTE_PRT` |
| GFX7 | `:507` | `*flags &= ~AMDGPU_PTE_PRT` |
| **GFX8** | **`:722`** | **`*flags &= ~AMDGPU_PTE_PRT`** |
| GFX9 | `:1193-1194` | `|= AMDGPU_PTE_PRT` **y** `&= ~AMDGPU_PTE_VALID` |
| GFX10 | `:511` | `|= AMDGPU_PTE_PRT` |

Y en vez de entrada de tabla, GFX8 tiene aperture de rango:
`mmVM_PRT_APERTURE{0..3}_{LOW,HIGH}_ADDR` programados con
`AMDGPU_VA_RESERVED_BOTTOM >> 12` y `max_pfn` (`gmc_v8_0.c:792-808`), más
`VM_PRT_CNTL` con `L1_TLB_STORE_INVALID_ENTRIES`, `L2_CACHE_STORE_INVALID_ENTRIES` y
`MASK_PDE0_FAULT`. El mensaje del driver es explícito: *"Disabling VM faults because of PRT
request!"*.

**El driver propio de Polaris12 necesita los dos mecanismos o ninguno.** No hace falta una
tercera forma de entrada. `PROVEN` por lectura del consumidor y del formateo del PTE.

`LIMITACIÓN`: no he verificado que el hardware GFX8 interprete el bit 3 del PTE como reservado
— que es lo que haría que `&= ~PRT` sea seguro y no una corrupción silenciosa. Requiere
RUNTIME, y es la razón por la que el driver lo borra en vez de no hacer nada.

## 4 · Corrección de provenance: `gmc_8_1_d.h`, no `gmc_8_2_d.h`

Error mío, en `017`, `018` y `019`. `gmc_v8_0.c:35` incluye `gmc/gmc_8_1_d.h`;
`gfx_v8_0.c:41` incluye `gmc/gmc_8_2_d.h`. Yo cité la segunda para todo el path GMC.

Verificado si cambia algo — 15 registros, offsets comparados:

```
mmVM_INVALIDATE_REQUEST  8_1=0x51e  8_2=0x51e  SI
mmVM_INVALIDATE_RESPONSE 8_1=0x51f  8_2=0x51f  SI
mmATC_L1RD_DEBUG_TLB     8_1=0xcde  8_2=0xcde  SI
mmATC_L2_DEBUG2          8_1=0xcd8  8_2=0xcd8  SI
mmATC_VMID_PASID_MAPPING_UPDATE_STATUS 8_1=0xce6  8_2=0xce6  SI
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR     8_1=0x54f  8_2=0x54f  SI
...  (15/15 coinciden)
```

**Ninguna conclusión cambia.** Los offsets de los registros citados son idénticos en ambas
cabeceras. Diferencia global entre las dos: `gmc_8_1_d.h` tiene 1156 registros, `gmc_8_2_d.h`
882; 315 sólo en 8_1, 41 sólo en 8_2, **1 offset distinto** (`mmMC_CG_DATAPORT` `0xa21` →
`0xa32`, y no es un registro que yo cite). Todos los que usé coinciden.

`8_1` es la ASIC-correcta para el bloque GMC de GFX8 (`gmc_v8_0.c` la incluye). `8_2` es la
que incluye `gfx_v8_0.c` para el mismo fin. Los offsets son los mismos porque son el mismo
ASIC documentado dos veces. Anotado como `CORRECTION_OF_PROVENANCE`, no de resultado.

## 5 · `PAGE_TABLE_BLOCK_SIZE` depende de la RAM del host

De la iteración anterior, ahora con el productor identificado. `gmc_v8_0.c:927-928`:

```c
REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
              adev->vm_manager.block_size - 9);
```

`block_size` sale de `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)` (`gmc_v8_0.c:1121`) →
`amdgpu_vm.c:2427-2430`. Con `num_level == 1` cae en
`amdgpu_vm_get_block_size(max_pfn)` (`amdgpu_vm.c:2332-2343`), que depende de `vm_size`, que
depende de `si.totalram` (`amdgpu_vm.c:2390-2394`).

| RAM del host | vm_size | block_size | PDE |
|---|---|---|---|
| ≤ 21 GB | 64 GB | 13 | 16 KiB |
| 22-42 GB | 128 GB | 14 | 32 KiB |
| 43-85 GB | 256 GB | 14 | 32 KiB |
| ≥ 86 GB | 512 GB | 15 | 64 KiB |

`PAGE_TABLE_DEPTH` = 0 para VMID 0 (`gmc_v8_0.c:889`) y 1 para VMID 1-15 (`:919`). El campo
`PAGE_TABLE_DEPTH` es `MASK 0x6` `SHIFT 1` — 2 bits, 4 valores, y el driver GFX8 usa 2 de
ellos. GFX9+ usa `max_level=3, max_bits=48`.

**Implicación para el driver propio**: el tamaño de entrada de page table no es una
constante del hardware, es una decisión de diseño que el driver de referencia deriva del
host. Fijarlo es `MODEL_CHOICE`; lo que no es libre es que `mmVM_PRT_APERTURE*_HIGH_ADDR` se
programa con `max_pfn` (`gmc_v8_0.c:789`), así que **tamaño de tabla y rango de aperture
están acoplados por construcción**. Cambiar `block_size` cambia dónde termina la GART.

## 6 · UNLOCKS

- El encoder de PTE del driver propio es un emisor de `SDMA_OP_GEN_PTEPDE` de 9 dwords. No
  hace falta implementar `writeq` de page tables.
- Los otros dos paquetes (`SDMA_OP_WRITE` para `count < 3`, `SDMA_OP_COPY` para el bloque
  grande de system pages) son optimizaciones del driver de referencia, no requisitos.
- GART y GPUVM tienen reglas de inalcanzabilidad distintas. Documentar sólo la de GPUVM fue
  mi error de alcance.

## 7 · Falsación

Se refutaría si: (a) apareciera un tercer productor de entradas de tabla en el path GFX8 —
`PROVEN` no hay; (b) `vram_full_visible` fuera verdadero para una RX550 de 2 GiB, lo que
reabriría el writer CPU — el supuesto previo es un BAR de 256 MiB, que es `PROVEN` de la
configuración del host pero no de este corpus, así que aquí es `PROVISIONAL`; (c) el hardware
GFX8 usara el
bit 3 del PTE, lo que rompería el `&= ~PRT` — RUNTIME.

## 8 · Evidencia

```
sha256 tarball: 12e8d5a973d1ad7c5a5c69882e4022b131ed715db7003fdcd760ddf8c3e51941 (linux-7.2.8.tar.xz)

amdgpu_gmc.c:      163-178 (set_pte_pde), 1134-1190 (init_pdb0, XGMI only)
amdgpu_gmc.h:      396-401 (vram_full_visible)
amdgpu_vm.c:       2595-2607, 2695-2736 (init_entities / make_compute),
                   2330-2442 (adjust_size / get_block_size)
amdgpu_vm.h:       57-88 (PTE flags), 185-186 (USE_CPU_FOR_GFX/COMPUTE)
amdgpu_vm_cpu.c:   75-110 (amdgpu_vm_cpu_update)
amdgpu_vm_sdma.c:  187-296 (set_ptes / copy_ptes)
amdgpu_gart.c:     308-339 (unbind), 354-415 (map, map_vram_range)
amdgpu_gem.c:      832-841 (AMDGPU_VM_PAGE_PRT en ioctl)
gmc_v8_0.c:        685-703 (PTE/PDE format), 706-723 (get_vm_pde/pte),
                   880-935 (context setup), 1121 (adjust_size), 1127-1128 (maskes)
sdma_v3_0.c:       916-997 (los tres productores), 1084-1089 (pmf)
tonga_sdma_pkt_open.h: 37 (SDMA_OP_GEN_PTEPDE = 12)
include/asic_reg/gmc/gmc_8_1_d.h, gmc_8_2_d.h  (comparación de offsets)
```

Ningún registro leído de MMIO. Ninguna operación runtime. `MODIFICATIONS=0` en el corpus.