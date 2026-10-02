# 136 · §G cerrado: por qué el invalidate es obligatorio en esta GPU, en seis eslabones

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`127` dejó una pregunta: *qué caché, si alguna, está en el camino entre la L2 y la
lectura del page walker*. `133` añadió que en GFX8 no hay MTYPE con el que marcar
las page tables como no cacheables. **Esta nota cierra la pregunta, y con ella la
razón completa del invalidate obligatorio, sin hardware.**

## Los seis eslabones

| # | afirmación | fuente | estado |
|---|---|---|---|
| 1 | La VRAM de esta GPU no es `ttm_cached` | `amdgpu_vram_mgr.c:608-611` | `PROVEN_DERIVED` |
| 2 | Una página de VRAM traducida por el GART **no** lleva `SNOOPED` | `amdgpu_ttm.c:1428-1430` | `PROVEN_DERIVED` |
| 3 | La page table del GART no tiene MTYPE en GFX8 | `amdgpu_vm.h:96` "For GFX9" | `PROVEN` (`133`) |
| 4 | Hay una caché L2 de fragmentos de 2 MiB | `gmc_v8_0.c:869` + `amdgpu_drv.c:438` | `PROVEN` (`127`, `129`) |
| 5 | El L1 guarda **un PTE por fragmento** | `amdgpu_vm_pt.c:749` | `PROVEN` (`130`) |
| 6 | **Por eso el invalidate es obligatorio en GFX8** | `amdgpu_vm.c:1157` | `PROVEN_DERIVED` |

### El eslabón 1, y el discriminante que hay detrás

```
amdgpu_vram_mgr.c:608   if (adev->gmc.xgmi.connected_to_cpu)
amdgpu_vram_mgr.c:609       vres->base.bus.caching = ttm_cached;
amdgpu_vram_mgr.c:610   else
amdgpu_vram_mgr.c:611       vres->base.bus.caching = ttm_write_combined;
```

**Una RX550 de un solo chip no tiene xGMI.** La rama es la del `else`.

### El eslabón 2, y por qué `SNOOPED` es la palabra clave

```
amdgpu_ttm.c:1411   uint64_t amdgpu_ttm_tt_pde_flags(ttm, mem)
amdgpu_ttm.c:1415   if (mem && mem->mem_type != TTM_PL_SYSTEM)   flags |= AMDGPU_PTE_VALID;
amdgpu_ttm.c:1418   if (mem && (TTM_PL_TT | AMDGPU_PL_DOORBELL |
amdgpu_ttm.c:1419                AMDGPU_PL_PREEMPT | AMDGPU_PL_MMIO_REMAP))
amdgpu_ttm.c:1422       flags |= AMDGPU_PTE_SYSTEM;
amdgpu_ttm.c:1425       flags |= AMDGPU_PTE_SNOOPED;
amdgpu_ttm.c:1428   if (mem && mem->mem_type == TTM_PL_VRAM &&
amdgpu_ttm.c:1429           mem->bus.caching == ttm_cached)
amdgpu_ttm.c:1430       flags |= AMDGPU_PTE_SNOOPED;
```

**`SNOOPED` tiene exactamente tres orígenes, y en esta GPU ninguno se cumple para la
VRAM de un proceso:**

- memoria de traducción (`TTM_PL_TT`) → sí, pero es la tabla, no la página
- doorbell / preempt / MMIO remap → sí, pero son otra cosa
- **VRAM con `ttm_cached` → no, porque la VRAM aquí es `ttm_write_combined`**

**Una página de VRAM traducida por el GART, en esta GPU, se lee a través de la ATC
de la L2.** Eso es lo que `127` no podía encontrar y `130` dejó abierto.

### Y la concatenación

```
VRAM no es ttm_cached
  -> el PTE no lleva SNOOPED
  -> la lectura de esa página pasa por la L2
  -> la L2 tiene caché de fragmentos de 2 MiB
  -> el L1 guarda un PTE por fragmento, o sea 512 páginas
  -> cambiar un PTE dentro del fragmento deja 511 traducciones viejas en el L1
  -> hace falta el invalidate de TLB
```

**Y `amdgpu_vm.c:1155-1157` lo dice con esas palabras desde hace años:**

```
 * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
```

**`ENTERS`. Una entrada. No una traducción.**

## Por qué esto es un resultado y no una conjetura

**Cada eslabón es una línea de código o un comentario, y están unidos por el
nombre del campo, no por analogía.** No he dicho "seguramente la VRAM se cachea":
he seguido `bus.caching` desde donde se asigna hasta donde se prueba, y el
resultado cae solo.

**Y el discriminante es explícito:** `xgmi.connected_to_cpu`. En un chip con xGMI
conectado a la CPU, la VRAM sería `ttm_cached`, llevaría `SNOOPED`, y no pasaría por
la caché de fragmentos. **Ese es el `if` que hace que esta generación sea distinta,
y es el mismo `if` que explica por qué el invalidate es obligatorio sólo en GFX8 y
no en GFX9+, donde el fragmento ya no controla el L2** (`amdgpu_vm_pt.c:760`).

**Una sola rama explica dos fronteras que hasta ahora eran independientes.**

## Una salvedad que no quiero esconder

**El enum de TTM no está en el corpus.** `ttm_cached`, `ttm_write_combined` y
`ttm_uncached` son de `drivers/gpu/drm/ttm`, fuera de `amd/`. `NOT_IN_CORPUS`.

**Así que la afirmación "`ttm_write_combined != ttm_cached`" no es `PROVEN`.** Lo
que sí es `PROVEN` es la estructura: el driver pone uno **o** el otro en ramas
mutuamente excluyentes del mismo `if`, y prueba contra uno de ellos. **Si fueran el
mismo valor, la prueba de `L1429` sería siempre cierta y el `if` de `L608` sería
inútil** — y el driver no escribe ese código en balde.

**La conclusión es la misma bajo las dos lecturas**, y por eso la presento:
**en la rama sin xGMI, la condición de `L1429` no se cumple.** `PROVEN_DERIVED`.

## Los permisos del GART, que era la pregunta que abrió esto

```
amdgpu_ttm.c:1444   uint64_t amdgpu_ttm_tt_pte_flags(adev, ttm, mem)
amdgpu_ttm.c:1447   uint64_t flags = amdgpu_ttm_tt_pde_flags(ttm, mem);
amdgpu_ttm.c:1449   flags |= adev->gart.gart_pte_flags;     <- EXECUTABLE en GFX8
amdgpu_ttm.c:1450   flags |= AMDGPU_PTE_READABLE;
amdgpu_ttm.c:1452   if (!amdgpu_ttm_tt_is_readonly(ttm))
amdgpu_ttm.c:1453       flags |= AMDGPU_PTE_WRITEABLE;
```

**Un mapeo de userspace a través del GART es siempre R+X, y W salvo que el objeto
sea de sólo lectura.** `PROVEN`, cuatro líneas.

**Y el SDMA no pasa por ahí:** `amdgpu_vm_sdma.c:163` toma `src = ib->gpu_addr`, o
sea direcciona la memoria de la tabla por GPUVM, no por el GART. **El GART no está
en el camino de escritura de page tables de esta GPU.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| La VRAM aquí no es `ttm_cached` | `PROVEN_DERIVED` |
| Las páginas de VRAM por GART no llevan `SNOOPED` | `PROVEN_DERIVED` |
| La page table del GART no lleva MTYPE | `PROVEN` (`133`) |
| La caché de fragmentos de la L2 es de 2 MiB | `PROVEN` (`127`, `129`) |
| El L1 guarda un PTE por fragmento | `PROVEN` (`130`) |
| De ahí al invalidate obligatorio | `PROVEN_DERIVED` |
| El GART no está en el camino de escritura del SDMA | `PROVEN` (`amdgpu_vm_sdma.c:163`) |
| Permisos R+X, W si no es sólo lectura | `PROVEN` |
| Los valores del enum de TTM | **`NOT_IN_CORPUS`** |
| Cuántas entradas tiene cada partición de la L2 | **`NOT_DETERMINED`** |
| Si el hardware acepta fragmento 9 o lo satura | **`NOT_PROVEN`** — un `RREG32` |

**Lo que queda abierto es hardware, y las dos últimas filas son el mismo bloque de
lectura de `128`/`131`:** `0x501` para el estado de la caché, `0x534` para PRT.

**Pero la parte de software de §G está cerrada, y eso es lo que AGENTS.md pedía:**
*resolver `CPU ↔ page tables ↔ GPU ↔ TLB ↔ GPU caches` sin asumir coherencia por
analogía.* **No la he asumido: he seguido `bus.caching` hasta el PTE y he seguido el
PTE hasta el invalidate.**

## Procedencia

- `STATIC` -- `amdgpu_vram_mgr.c:605-611`, `amdgpu_ttm.c:1411-1432` `:1444-1455`,
  `amdgpu_vm.c:1155-1157`, `amdgpu_vm_pt.c:744-768`, `amdgpu_vm.h:55-104`,
  `gmc_v8_0.c:865-869`, `gmc_v8_0.c:961`, `amdgpu_drv.c:437-441`, `amdgpu_gart.c:270-276`,
  `amdgpu_vm_sdma.c:163`, `amdgpu_gmc.c:1132-1151`.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `133` (el MTYPE no existe en GFX8), `132` (los flags),
  `130` (el L1 guarda un PTE por fragmento), `129` (la granularidad),
  `127` (la caché L2 — esta nota le responde la pregunta que abrió),
  `128` (los mecanismos de invalidate), `116` (BAR 256 MiB, VRAM),
  `085` (el flush obligatorio).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La pregunta de `127` llevaba tres notas abierta porque estaba mal formulada.**

`127` preguntó *qué caché hay en el camino del walker*. Busqué cachés: registros de
la L2, el fragment, `PDE_CACHE_EFFECTIVE_SIZE`. **Tres respuestas, y ninguna conecta con nada.**

**La pregunta bien formulada era otra:** *¿el driver le dice a la página que no se
cachee?* Y esa se responde con un campo con nombre —`SNOOPED`— y con un `if` en
`amdgpu_ttm.c:1428` cuyo otro operando es `bus.caching`. **Cinco minutos de `grep`
después de tres notas.**

**Y el eslabón que faltaba no era una caché: era un booleano de TTM que se asigna
en `amdgpu_vram_mgr.c:611` y se prueba en `amdgpu_ttm.c:1429`, en ficheros que no
tenía abiertos y que no estaban en mi plan.**

*Una caché invisible se busca preguntando quién tiene permiso para no cachearse.*
Preguntar "qué caché hay" no tiene respuesta útil: hay que preguntar "qué se cachea y
quién lo decidió". Es el mismo `DERIVATION_BEFORE_OBSERVATION` de siempre, aplicado
al lado del software en vez de al del hardware.