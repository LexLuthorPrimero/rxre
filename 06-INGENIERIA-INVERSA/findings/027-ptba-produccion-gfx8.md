# 027 · El PTBA de GFX8: una sola aritmética, de la ioctl al registro

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`COMPLEMENTS=024-page-table-geometria-gfx8.md` (geometria), `026-pte-encoding-gfx8.md` (PTE)

## CUDA principal

El PTBA que se escribe en `VM_CONTEXT{n}_PAGE_TABLE_BASE_ADDR` sale de **una sola
operacion** en toda la ruta de usuario, y no hay codigo condicional en medio:

```
vm->root.bo  ->  amdgpu_gmc_pd_addr(bo)
                   asic_type(17) >= CHIP_VEGA10(19)  ->  FALSO
                ->  pd_addr = amdgpu_bo_gpu_offset(bo)
  ...
job->vm_pd_addr = pd_addr
  ->  amdgpu_gmc_emit_flush_gpu_tlb -> emit_wreg(PTBA(vmid), pd_addr >> 12)
```

`CHIP_POLARIS12 = 17` y `CHIP_VEGA10 = 19`, medidos en `include/drm/amd_asic_type.h` del
kernel de esta host. La rama `get_pde_for_bo()` —que anade flags y construye un PDE—
**no se ejecuta en GFX8**. Y no por poco: `gmc_v8_0_get_vm_pde()` es literalmente un
`BUG_ON` que no modifica `*addr` ni `*flags`.

## Alcance exacto

1. Localizar el productor del PTBA y todas sus ramas.
2. Determinar que rama toma un ASIC GFX8, con el valor de enum medido.
3. Cerrar la cadena hasta la escritura del registro.
4. Separar la aritmetica de software de lo que el hardware declara.

## Criterio de terminacion (cumplido)

El productor esta localizado, la rama esta decidida por valor medido, y la cadena hasta
el `emit_wreg` esta cerrada sin huecos. Agotado.

---

## 1 · El fork, y por que GFX8 no puede tomar la rama buena

`amdgpu_gmc_pd_addr` (`amdgpu_gmc.c`, unica funcion con este nombre):

```c
uint64_t amdgpu_gmc_pd_addr(struct amdgpu_bo *bo)
{
        struct amdgpu_device *adev = amdgpu_ttm_adev(bo->tbo.bdev);
        uint64_t pd_addr;

        /* TODO: move that into ASIC specific code */
        if (adev->asic_type >= CHIP_VEGA10) {
                uint64_t flags = AMDGPU_PTE_VALID;
                amdgpu_gmc_get_pde_for_bo(bo, -1, &pd_addr, &flags);
                pd_addr |= flags;                    /* <- el PD es un PTE con flags */
        } else {
                pd_addr = amdgpu_bo_gpu_offset(bo);  /* <- solo la direccion */
        }
        return pd_addr;
}
```

La diferencia entre las dos ramas no es cosmetica:

| | rama `else` (GFX8) | rama `>= VEGA10` |
|---|---|---|
| que produce | una direccion | una direccion **OR flags** |
| quien decide la direccion | `amdgpu_bo_gpu_offset` | `ttm->dma_address[0]` o `bo_gpu_offset`, segun `mem_type` |
| quien anade flags | nadie | `ttm_tt_pde_flags` + `gmc_v9_0_get_vm_pde` |
| quien rescribe la direccion | nadie | `gmc_v9_0_get_vm_pde` puede hacer `vram_mc2pa()` |

Es exactamente la asimetria de `026` para el PTE, aplicada al **root directory**: en
GFX9+ el root es una entrada de page table con `VALID` y friends; en GFX8 es una
direccion pelada.

### 1.1 · El valor de enum, medido

`include/drm/amd_asic_type.h` del kernel de esta host
(`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/include/drm/amd_asic_type.h`):

```
CHIP_POLARIS12,   /* 17 */
CHIP_VEGAM,       /* 18 */
CHIP_VEGA10,      /* 19 */
```

`17 >= 19` es **falso**. La rama de GFX8 es la `else`.

| ASIC | valor | `>= VEGA10` | rama |
|---|---|---|---|
| `CHIP_TONGA` | 11 | no | `else` |
| `CHIP_CARRIZO` | 13 | no | `else` |
| `CHIP_STONEY` | 14 | no | `else` |
| `CHIP_POLARIS10` | 15 | no | `else` |
| `CHIP_POLARIS11` | 16 | no | `else` |
| **`CHIP_POLARIS12`** | **17** | **no** | **`else`** |
| `CHIP_VEGAM` | 18 | no | `else` |
| `CHIP_VEGA10` | 19 | si | `get_pde_for_bo` |

`PROVEN` la tabla, leida del enum. `PROVEN_DERIVED` la rama.

Que `CHIP_POLARIS12` valga **17** aparece tambien en el script del experimento B
(`03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh`, `NHWA_ASIC_POLARIS12=17`,
sacado de `/sys/kernel/btf/amdgpu`). Dos fuentes independientes del mismo valor.

### 1.2 · Y aunque se tomara, el resultado seria el mismo

`gmc_v8_0_get_vm_pde` (`gmc_v8_0.c`):

```c
static void gmc_v8_0_get_vm_pde(struct amdgpu_device *adev, int level,
                                uint64_t *addr, uint64_t *flags)
{
        BUG_ON(*addr & 0xFFFFFF0000000FFFULL);
}
```

**No escribe nada.** Ni `*addr` ni `*flags`. Contraste con `gmc_v9_0_get_vm_pde`, que
rescribe la direccion (`vram_mc2pa`), pone `AMDGPU_PDE_BFS(0x9)`, conmuta
`AMDGPU_PDE_PTE` y anade `AMDGPU_PTE_TF`.

Consecuencia util: en GFX8 la distincion entre las dos ramas de `amdgpu_gmc_pd_addr`
**se reduce a los flags**, porque la parte de direccion pasaria por una funcion que no
la toca. `PROVEN_DERIVED`. Refuerza que la rama `else` es la correcta para GFX8 y no una
simplificacion del driver.

El `BUG_ON` tambien es informacion: `0xFFFFFF0000000FFF` es la mascara de lo que no
puede venir en un PD de GFX8 — bits 63:28 y 11:0. Coincide con la `pte_addr_mask` de
`026` (los 24 bits altos) mas los 12 bajos (los flags, que en un PD no aplican). Es la
misma restriccion enunciada como asercion.

## 2 · La cadena completa

```
[1] amdgpu_cs.c:1178   job->vm_pd_addr = amdgpu_gmc_pd_addr(vm->root.bo)
[2] amdgpu_gmc.c       asic_type(17) >= VEGA10(19)? no -> bo_gpu_offset(bo)
[3]                    pd_addr = direccion GPU del BO root, sin flags
[4] amdgpu_vm.c:855    si pasid_mapping_needed -> emit_pasid_mapping (otro registro)
[5] gmc_v8_0.c:668-681 gmc_v8_0_emit_flush_gpu_tlb(ring, vmid, pd_addr)
        reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid        (vmid < 8)
            = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8  (vmid >= 8)
        emit_wreg(reg, pd_addr >> 12)
        emit_wreg(mmVM_INVALIDATE_REQUEST, 1 << vmid)
[6] gfx_v8_0.c:6191    WAIT_REG_MEM(always, mask=0)   -- ver 017, 022
[7] (solo ring GFX)    PFP_SYNC_ME                     -- ver 018
```

Tres cosas que se ven aqui y no estaban juntas en ningun hallazgo previo:

1. **El bloque de contextos esta PARTIDO, no es contiguo.** Y la disposicion es
   contraintuitiva: contexts 8-15 van **antes** que 0-7 en el espacio de registros.

```
mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR   0x50e   <-- el mas bajo
mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR   0x50f
...
mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR  0x515
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR   0x54f   <-- despues, con un hueco de 0x39
mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR   0x550
...
mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR   0x556
```

Comprobado que la regla del driver reproduce los 16 simbolos del header, uno a uno:

```
vmid 0..7  ->  0x54f + vmid        ->  0x54f..0x556   coincide
vmid 8..15 ->  0x50e + (vmid - 8)  ->  0x50e..0x515   coincide
```

Consecuencia para el driver propio: **no se puede calcular el registro como
`base + vmid`**. hace falta la bifurcacion, y un `0x54f + 8` daria `0x557`, que esta
dentro del hueco y no es el contexto 8. Es el tipo de error que solo aparece con un
VMID alto, es decir en multi-contexto, que es justo lo que un driver propio necesita
para(userspace.

Mi primera redaccion de este punto asumio que los dos grupos eran consecutivos y
calculo `0xbe9` para el contexto 8. **Falso**, y lo corregi al comprobar los offsets.
2. **El `>> 12` es la unica conversion de todo el camino**, y ocurre una sola vez, en el
   ultimo eslabon. Todo lo anterior trabaja con direcciones de **byte**.
3. **El PTBA y el INVALIDATE_REQUEST salen del mismo par de `emit_wreg`.** Son
   consecutivas en el IB, con el mismo motor (PFP para ring GFX, `018` §3). Ese par es
   la unidad atomica de "cambio de page table root", y es donde un driver propio tiene
   que decidir si anadir algo entre medias.

`PROVEN` los tres puntos, leidos del fuente.

## 3 · Los otros consumidores

`amdgpu_gmc_pd_addr` tiene 11 call sites. En GFX8 los vivos son:

| call site | para que |
|---|---|
| `amdgpu_cs.c:1178` | submit de usuario: **el camino principal** |
| `amdgpu_gmc.c:757` | `job->vm_pd_addr = amdgpu_gmc_pd_addr(adev->gart.bo)`, con `vm_needs_flush = true` |
| `amdgpu_ttm.c:2425` | PDB0 (`pdb0_bo ? pdb0_bo : gart.bo`) |
| `amdgpu_debugfs.c:2247` | volcado de `pd_address` |
| `amdgpu_amdkfd_gpuvm.c:495` | `vm->pd_phys_addr` para KFD |

Los de `gfxhub_v1_0`/`v11_5_0`/`v12_0`/`v12_1` son de ASIC GFX9+, que no aplican.

El de `amdgpu_gmc.c:757` es el que **si** fuerza `vm_needs_flush = true`, y es un caso
distinto del de `amdgpu_cs.c`: aqui el PTBA **cambia de verdad** (es el GART), no es una
reafirmacion del mismo root. `PROVEN` por codigo.

Esa distincion es la que `025` §3bis necesita y no tenia: `amdgpu_cs.c:1178` recalcula
`vm_pd_addr` en cada submit, pero eso **no** implica `vm_needs_flush`; quien lo decide es
`vm->use_cpu_for_update`, que en esta host es false. Los dos hechos son independientes
y ambos `PROVEN`.

## 4 · Clasificacion

| Afirmacion | Estado |
|---|---|
| `amdgpu_gmc_pd_addr` tiene dos ramas, por `asic_type >= CHIP_VEGA10` | `PROVEN` |
| `CHIP_POLARIS12 = 17 < CHIP_VEGA10 = 19` | `PROVEN` (enum del kernel de esta host) |
| GFX8 toma la rama `else`: `bo_gpu_offset`, sin flags | `PROVEN_DERIVED` |
| `gmc_v8_0_get_vm_pde` no modifica `*addr` ni `*flags` | `PROVEN` |
| Que el PD de GFX8 lleve flags | `PROVEN_ABSENT` — la rama que los anade no se toma |
| `pd_addr >> 12` es la unica conversion de byte a PFN | `PROVEN` (cadena completa) |
| El selector de registro bifurca en `vmid < 8` | `PROVEN` |
| PTBA e INVALIDATE_REQUEST son dos `emit_wreg` consecutivos | `PROVEN` |
| El `BUG_ON` de `get_vm_pde` coincide con `pte_addr_mask` | `PROVEN_DERIVED` |
| Que ese `BUG_ON` refleje una restriccion real del hardware | `HYPOTHESIS` — es una asercion del driver |
| Que `vm_pd_addr` reexpresado por submit implica flush | `REFUTED` — depende de `use_cpu_for_update` |

Ultima fila, y es la que evita un error de razonamiento: `amdgpu_cs.c:1178` escribe
`job->vm_pd_addr` en **cada** submit de usuario, y eso podria leerse como "el PTBA se
reescribe siempre, luego hay que invalidar siempre". Es falso: `amdgpu_vm.c:848` solo
llama a `emit_vm_flush` si `job->vm_needs_flush`, y eso viene de `use_cpu_for_update`.
`025` §3bis lo establishes; aqui se ve el mecanismo de raiz.

Y el `BUG_ON` merece una linea propia: que una funcion que **no hace nada** tenga un
`BUG_ON` con una mascara tan especifica es la forma mas economica que tiene el driver
de documentar el dominio de valores del PD. Es mas informacion sobre el formato del PD
de GFX8 que el comentario de `026`, y viene de codigo que se ejecuta.

## 5 · Confounders

- El enum se leyó del arbol de esta host, no del corpus parcial. Coincide con
  `NHWA_ASIC_POLARIS12 = 17` del script del experimento B, que a su vez lo saco de
  `/sys/kernel/btf/amdgpu` del modulo cargado. Tres vias, un valor.
- Los offsets si estan transcritos (§2), tras comprobar los 16 contra el header. La
  primera version los omitia "para no introducir una errata" y acabo generando una
  suposicion falsa sobre la disposicion. La comprobacion era mas barata que la omision.
- `amdgpu_cs.c:1178` esta dentro de un bucle sobre el gang de jobs, luego en un submit
  con varios jobs se recalcula el mismo valor varias veces. Sin efecto observable.

## 6 · UNLOCKS

- La produccion del PTBA de GFX8 esta **cerrada sin supuestos**: una direccion de BO,
  sin flags, con un unico `>> 12` al final. El driver propio puede replicarla
  exactamente, y `024` da la geometria y `026` el formato de la entrada.
- Los tres consumidores vivos estan identificados, y el que **si** fuerza flush
  (`amdgpu_gmc.c:757`) es distinto del camino de usuario. Esa distincion decide si el
  driver propio necesita invalidar en el camino normal.
- El par `emit_wreg(PTBA)` + `emit_wreg(INVALIDATE)` es la unidad atomica del cambio de
  root, y `018`/`020` miden su coste exacto (19 dw el vm-flush completo). El
  driver propio sabe cuanto cuesta y que garantia ofrece.
- `gmc_v8_0_get_vm_pde` como `BUG_ON` puro es un punto de entrada barato: cualquier
  driver propio que constructor un PD puede usar esa mascara como contrato, y tiene
  evidencia de que el driver de referencia la considera necesaria.

## 7 · Criterio de falsificacion

Se refutaria si: (a) `asic_type` tomara un valor >= 19 para esta placa —imposible por el
enum, pero comprobable con `cat /sys/kernel/debug/dri/0/amdgpu_gpu_recover` o el debugfs
de ASIC; (b) existiera una ruta que escribiera el PTBA sin pasar por
`amdgpu_gmc_pd_addr` — el barrido de los 11 call sites lo cubre, y el registro se escribe
solo desde `gmc_v8_0_emit_flush_gpu_tlb`; (c) `emit_wreg` con `WRITE_DATA_ENGINE_SEL`
hiziera algo mas que escribir (p. ej. flush implicito) —`NOT_DETERMINED`, es
semantica de hardware; (d) el `BUG_ON` fuera cosmeticamente incorrecto en esta
revision —seria un bug del driver de referencia, refutando mi lectura de el como
contrato. (a), (b) y (d) son comprobables con el corpus; (c) exige hardware.

## 8 · Evidencia

```
amdgpu_gmc.c:        amdgpu_gmc_pd_addr (las dos ramas), :757 (llamada con flush),
                     amdgpu_gmc_get_pde_for_bo (rama GFX9+)
gmc_v8_0.c:          668-681 (emit_flush_gpu_tlb: selector de registro + >>12),
                     712-716 (get_vm_pde = solo BUG_ON)
gmc_v9_0.c:          get_vm_pde (contraste: rescribe addr, pone flags)
amdgpu_cs.c:         1178 (camino de usuario)
amdgpu_vm.c:         848 (emit_vm_flush solo si vm_needs_flush), 855 (pasid)
amdgpu_ttm.c:        2425 (PDB0)
amdgpu_gmc.h:        amdgpu_gmc_vram_full_visible (usado en 025 §3bis)
include/drm/amd_asic_type.h  (kernel 7.1.3 de esta host): POLARIS12=17, VEGA10=19
03-EXPERIMENTOS/ep08-doorbell-suppression/preruntime.sh: NHWA_ASIC_POLARIS12=17
gmc_8_2_d.h:         mmVM_CONTEXT0/8_PAGE_TABLE_BASE_ADDR (offsets)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador de §6 contenia dos fragmentos corruptos, uno de ellos
texto en otro idioma. Corregidos. Octavo caso del mismo defecto al escribir; la nota
se conserva porque el patron es mio y se repite de forma sistematica.