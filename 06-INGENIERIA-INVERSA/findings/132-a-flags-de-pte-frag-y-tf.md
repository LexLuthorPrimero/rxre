# 132 · §A: los flags de PTE, y por qué el GART y un VMID de userspace tienen el mismo fragmento

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

AGENTS.md §A pide `encoding → bits → address → flags → fragment → valid`. `130`
cerró el concepto de fragmento y dejó los bits sin mirar. Esta nota cierra los
flags, y de paso la geometría de la page table del GART, que mi estado da por
estructuralmente cerrada pero sin el tamaño de fragmento.

## El layout completo, y qué de él existe en GFX8

```
amdgpu_vm.h:57   VALID            (1ULL << 0)
amdgpu_vm.h:58   SYSTEM           (1ULL << 1)
amdgpu_vm.h:59   SNOOPED          (1ULL << 2)
amdgpu_vm.h:62   TMZ              (1ULL << 3)     /* RV+ */
amdgpu_vm.h:65   EXECUTABLE       (1ULL << 4)     /* VI only */
amdgpu_vm.h:67   READABLE         (1ULL << 5)
amdgpu_vm.h:68   WRITEABLE        (1ULL << 6)
amdgpu_vm.h:70   FRAG(x)          ((x & 0x1f) << 7)      bits 7-11, 5 bits
amdgpu_vm.h:73   PRT              (1ULL << 51)    /* TILED VEGA10, reservado antes */
amdgpu_vm.h:76   PDE_PTE          (1ULL << 54)
amdgpu_vm.h:78   LOG              (1ULL << 55)
amdgpu_vm.h:81   TF               (1ULL << 56)    /* Translate Further */
amdgpu_vm.h:84   NOALLOC          (1ULL << 58)
amdgpu_vm.h:87   PDE_BFS(a)       ((uint64_t)a << 59)
```

**Tres cosas de esa tabla que no son lo que su nombre sugiere, y que son
importantes para esta GPU:**

## 1 · El tamaño del fragmento viaja en el PTE

```
amdgpu_vm_pt.c:900   uint64_t upd_flags = flags | AMDGPU_PTE_FRAG(frag);
```

**El exponente del fragmento está en los bits 7-11 de la propia entrada**, no sólo
en un registro de control. Y `frag` es lo que calcula `amdgpu_vm_pt_get_frag`,
que en GFX8 queda limitado:

```
amdgpu_vm_pt.c:765   if (params->adev->asic_type < CHIP_VEGA10)
amdgpu_vm_pt.c:766       max_frag = params->adev->vm_manager.fragment_size;   -> 9
amdgpu_vm_pt.c:768       max_frag = 31;
amdgpu_vm_pt.c:778   *frag = min_t(unsigned int, ffs(start) - 1, fls64(end - start) - 1);
amdgpu_vm_pt.c:779   if (*frag >= max_frag) { *frag = max_frag; ... }
```

**En GFX8 el exponente del fragmento está entre 0 y 9, y el hardware lo acepta
hasta 9.** El valor exacto depende de la alineación del rango mapeado: el driver
usa el mayor fragmento que la contigüidad permita, recortado a 9.

**Para un driver propio: el fragmento no es una constante de diseño, es el
resultado de un cálculo sobre la dirección y el tamaño de cada asignación.** El
usuario puede obtener fragmentos grandes alineando, como dice `amdgpu_vm_pt.c:757`.

## 2 · `AMDGPU_PTE_TF` no existe en esta GPU

```
gmc_v9_0.c:1040    *flags |= AMDGPU_PTE_TF;
gmc_v10_0.c:473    *flags |= AMDGPU_PTE_TF;
gmc_v11_0.c:464    *flags |= AMDGPU_PTE_TF;
gmc_v8_0.c         NUNCA
```

**`PROVEN_ABSENT` en GFX8.** El PTE nunca se marca como "manejado como PDE".

**Y eso confirma `129` por una vía independiente.** `129` dedujo que
`translate_further` sólo se asigna en `gmc_v9_0.c` y que por tanto vale 0 en
Polaris12. **Ahora: el bit que lo representa en el PTE tampoco lo escribe nadie en
GFX8.** Dos hechos independientes que convergen en cero.

**Para un driver propio, una consecuencia práctica:** no hay que escribir el bit
56. Un driver que lo escriba en GFX8 escribiría un bit reservado.

## 3 · El GART y un VMID de userspace tienen el mismo fragmento, y es 2 MiB

```
amdgpu_gmc.c:62     pde0_page_shift = vmid0_page_table_block_size + 21;
amdgpu_gmc.c:63     npdes = (vram_size + (1 << pde0_page_shift) - 1) >> pde0_page_shift;
amdgpu_gmc.c:1136   /* Each PDE0 (used as PTE) covers (2^vmid0_page_table_block_size)*2M */
amdgpu_gmc.c:1139   pde0_page_size = (1ULL<<vmid0_page_table_block_size)<<21;
amdgpu_gmc.c:1150   flags |= AMDGPU_PTE_FRAG((vmid0_page_table_block_size + 9*1));
amdgpu_gmc.c:1151   flags |= AMDGPU_PTE_PDE_FLAG(adev);
```

Y el valor de ese parámetro:

```
gmc_v9_0.c:1780/1783    vmid0_page_table_block_size = 12  o  0
gmc_v12_0.c:787/790     vmid0_page_table_block_size = 12  o  0
gmc_v8_0.c              NUNCA LO ASIGNA
```

**En GFX8 vale 0** (estructura a cero, nadie lo escribe). Y con 0:

```
pde0_page_shift      = 0 + 21 = 21   ->  cada PDE0 cubre 2 MiB
AMDGPU_PTE_FRAG arg  = 0 + 9*1 = 9    ->  fragmento de 2 MiB
```

**El comentario de `L1136` y el código coinciden exactamente:** *"covers
(2^0)*2M" = 2 MiB.*

**Y ese 2 MiB es el mismo que el de los VMIDs de userspace** (`fragment_size = 9`,
`130`/`129`). **El GART y un proceso de userspace tienen la misma granularidad de
traducción en esta GPU.** No es un caso especial: es el mismo número por dos
rutas de código.

**El `+ 9*1` de `L1150` es el `9 * (PDB0 - level)` de `amdgpu_vm_pt.c:58`, con
`level = PDB1`.** O sea: **el PDE0 del GART se indexa un nivel más profundo que
el primer nivel de un VMID de userspace.** Coherente con `211`, que sitúa el
VMID 0 en el espacio del kernel.

## 4 · Y la geometría de la tabla, que sale de dos funciones que no había mirado

```
amdgpu_vm_pt.c:103   static uint32_t amdgpu_vm_pt_entries_mask(adev, level)
amdgpu_vm_pt.c:106       if (level <= adev->vm_manager.root_level)   return 0xffffffff;
amdgpu_vm_pt.c:108       else if (level != AMDGPU_VM_PTB)            return 0x1ff;
amdgpu_vm_pt.c:110       else                                       return AMDGPU_VM_PTE_COUNT(adev) - 1;

amdgpu_vm_pt.c:123   static unsigned int amdgpu_vm_pt_size(adev, level)
amdgpu_vm_pt.c:126       return AMDGPU_GPU_PAGE_ALIGN(amdgpu_vm_pt_num_entries(adev, level) * 8);
```

**Tres anchos y un tamaño de entrada, todos explícitos:**

| nivel | máscara | entradas | tamaño |
|---|---|---|---|
| raíz (`PDB0` aquí) | `0xffffffff` | `round_up(max_pfn, 1<<10) >> 10` | variable, alineado a página |
| intermedio | `0x1ff` | **512** | `512 × 8` = **4 KiB**, exactamente una página |
| hoja (`PTB`) | `0x3ff` = **10 bits** | **1024** | `1024 × 8` = **8 KiB** |

**Cada entrada son 8 bytes.** Es lo que hace que un directorio intermedio ocupe
exactamente una página de 4 KiB, y lo que hace que la hoja ocupe 8.

**Y con `num_level = 1` no hay niveles intermedios en absoluto:** los dos niveles
son la raíz y la hoja. El reparto de una dirección virtual es:

```
PFN  [ 10 .. 31+ ]  indice de la raiz,  sin mascara mas alla de 32 bits
     [  0 ..  9  ]  indice de la hoja,  & 0x3ff
     page offset    [  0 .. 11 ] del byte, 4 KiB
```

**Con `FRAG(x) = 9` en el PTE, cada PTE cubre hasta `2^9` páginas en vez de una**, y
por eso el índice de la raíz sólo tiene que distinguir regiones de 2 MiB. **Eso es
`130` aplicado a la aritmética del índice, y cierra la pregunta de §B: `VA → root
→ PTE → physical address` con los anchos concretos.**

**La Laguna que señalé arriba es real y la localizo:** el layout de `amdgpu_vm.h`
define los bits 0-6, 7-11, 51, 54, 55, 56, 58, 59-63. **Faltan 52-53, 57 y 60-63.**
Y `amdgpu_gmc.c:1147-1151` construye los flags del PTE del GART con una lista
explícita, no un cleaner:

```
amdgpu_gmc.c:1147   flags |= AMDGPU_PTE_VALID | AMDGPU_PTE_READABLE;
amdgpu_gmc.c:1148   flags |= AMDGPU_PTE_WRITEABLE;
amdgpu_gmc.c:1149   flags |= AMDGPU_PTE_SNOOPED;
amdgpu_gmc.c:1150   flags |= AMDGPU_PTE_FRAG(...);
amdgpu_gmc.c:1151   flags |= AMDGPU_PTE_PDE_FLAG(adev);
```

**y `flags` nace de `adev->gart.gart_pte_flags` con un `//TODO it is UC. explore NC/RW?`
en `L1135`.** O sea: **ni siquiera el autor sabía qué MTYPE era el correcto, y lo
dejó sin tocar.** Los bits sin definir no se ponen porque nadie los pone.

## Una corrección mía, de unidades, que el comentario del driver cazó

Escribí un script que imprimía el resultado de `AMDGPU_PTE_FRAG(9)` como
*"2^9 = 512 bytes = 0 MiB"*.

**El argumento de `AMDGPU_PTE_FRAG` no es un tamaño en bytes: es un exponente.**
`amdgpu_vm_pt.c:745` dice `1 << (12 + frag)`, así que 9 → `2^21` = 2 MiB.

**Lo que me avisó fue que "0 MiB" es absurdo, y fui a leer el comentario de
`L1136`, que dice 2M.** Si no hubiera leído el comentario, habría publicado una
aritmética que se contradecía a sí misma.

**Es la cuarta vez que calculo mal y la segunda que el cuerpo del driver detecta el
error.** Las dos últimas veces por el mismo motivo: *una unidad que no he
confirmado.* Aquí `frag` es un exponente y yo lo traté como un tamaño.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| El layout de flags, con posiciones exactas | `PROVEN` (`amdgpu_vm.h:57-87`) |
| El fragmento viaja en los bits 7-11 del PTE | `PROVEN` (`amdgpu_vm_pt.c:900`) |
| En GFX8 el exponente está acotado a 9 | `PROVEN_DERIVED` |
| El valor depende de la alineación del rango | `PROVEN` (`amdgpu_vm_pt.c:778`) |
| `AMDGPU_PTE_TF` no se escribe en GFX8 | `PROVEN_ABSENT` |
| Confirma `translate_further = 0` por vía independiente | `CORROBORATED` |
| `vmid0_page_table_block_size = 0` en GFX8 | `PROVEN_ABSENT` (nunca asignado) |
| El PDE0 del GART cubre 2 MiB | `PROVEN` (código y comentario coinciden) |
| El fragmento del GART = el de userspace | `PROVEN_DERIVED` |
| El GART se indexa en PDB1 | `PROVEN_DERIVED` (`+ 9*1`) |
| El bit `LOG` y su semántica | **`NOT_DETERMINED`** — nadie lo escribe en GFX8 |
| Los bits 52-53, 57, 60-63 | **`NOT_DETERMINED`** — sin definición en el corpus |
| Si el hardware acepta fragmento 9 en GFX8 o lo satura | **`NOT_PROVEN`** |

**La anteúltima merece atención.** El layout que he dado no cubre los 64 bits:
faltan 52-53, 57 y 60-63. **Para un driver propio, escribir un PTE significa
 poner flags en bits que no sé qué son.** Lo honesto es que el driver limpia
`flags` a un valor conocido antes de escribir — y eso lo debería verificar, no
suponer.

**Y la última es hardware**, y es la pregunta que `130` dejó: si el fragmento se
satura por debajo de 9 o si 9 es lo que dice el registro. **El registro
`L2_CACHE_BIGK_FRAGMENT_SIZE` de `0x503` lo diría, y es el mismo bloque de lectura
de `0x501` y `0x534`.**

## Procedencia

- `STATIC` -- `amdgpu_vm.h:55-111`, `amdgpu_vm_pt.c:50-65` `:760-785` `:890-905`,
  `amdgpu_gmc.c:58-66` `:1132-1151`, `gmc_v9_0.c:1040` `:1780-1783`,
  `gmc_v10_0.c:473`, `gmc_v11_0.c:464`, `gmc_v12_0.c:787-790`,
  `gmc_v6_0.c:391`, `gmc_v7_0.c:513`, `gmc_v8_0.c:728`.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `130` (el L1 guarda un PTE por fragmento), `129`
  (`translate_further`), `229` (los mecanismos de invalidate), `131` (PRT),
  `211` (VMID 0 = kernel), `194` (el flush obligatorio).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Entré buscando dos bits y salí con el layout completo de 64 y una laguna en
medio.**

Lo que pedí fue el valor de `AMDGPU_PTE_FRAG` y si se escribía `AMDGPU_PTE_TF`.
Lo que encontré fue `amdgpu_vm.h:57-111` entero, leído de una vez, y con él la
observación de que **la definición cubre 12 bits de 64**.

*Un layout se lee entero o no se lee. Pedir dos campos de un registro es la forma
segura de tener una tabla a medias y no notarlo.* Ya me había pasado con
`soc15d.h` al principio de la sesión, leyendo `PACKET3_WAIT_REG_MEM__*` y no la
tabla de alias `WAIT_REG_MEM_*`. **Tercera vez con el mismo fichero de headers.**

Y lo útil no fue ninguno de los dos bits que busqué: fue la comparación entre
`amdgpu_gmc.c:1150` y `amdgpu_vm_pt.c:58`, que son la misma aritmética con un
nivel de diferencia, y que dice que el GART está un nivel más profundo. **Eso no
estaba en mi pregunta.**