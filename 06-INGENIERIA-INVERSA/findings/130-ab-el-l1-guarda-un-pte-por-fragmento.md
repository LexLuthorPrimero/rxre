# 130 · §A/§B/§C: el L1 guarda **un PTE por fragmento**, y por eso el flush es obligatorio

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

AGENTS.md pide en §A `encoding → bits → address → flags → fragment → valid`, en §B
`VA → root → PDE → PTE → physical address` con `levels, root_level, num_level,
page size, fragmentation`, y en §C el invalidate.

**Las tres están en un bloque de 18 líneas de comentario que estaba en el
fichero desde el principio.** Nadie lo había leído. `127` cerró el invalidate
obligatorio por una vía indirecta y con una conclusión incompleta; esta nota lo
cierra por la vía directa y le da el requisito implementable.

## La descripción del hardware, textual

```
amdgpu_vm_pt.c:745  * granularity is increased from 4KB to (1 << (12 + frag)). The PTE
amdgpu_vm_pt.c:746  * flags are considered valid for all PTEs within the fragment range
amdgpu_vm_pt.c:747  * and corresponding mappings are assumed to be physically contiguous.
amdgpu_vm_pt.c:749  * The L1 TLB can store a single PTE for the whole fragment,
amdgpu_vm_pt.c:750  * significantly increasing the space available for translation
amdgpu_vm_pt.c:751  * caching. This leads to large improvements in throughput when the
amdgpu_vm_pt.c:752  * TLB is under pressure.
amdgpu_vm_pt.c:754  * The L2 TLB distributes small and large fragments into two
amdgpu_vm_pt.c:755  * asymmetric partitions. The large fragment cache is significantly
amdgpu_vm_pt.c:756  * larger. Thus, we try to use large fragments wherever possible.
amdgpu_vm_pt.c:757  * Userspace can support this by aligning virtual base address and
amdgpu_vm_pt.c:758  * allocation size to the fragment size.
amdgpu_vm_pt.c:760  * Starting with Vega10 the fragment size only controls the L1. The L2
amdgpu_vm_pt.c:761  * is now directly feed with small/huge/giant pages from the walker.
```

**Cinco hechos, y los cinco son hardware:**

1. Un fragmento de tamaño `frag` cubre `2^(12+frag)` bytes. Con `frag = 9`: **2 MiB**.
2. **Las flags del PTE valen para todo el fragmento.** No por PTE.
3. **Y los mapeos se asumen físicamente contiguos** dentro del fragmento.
4. **El L1 TLB guarda un solo PTE para el fragmento entero.**
5. **El L2 tiene dos particiones asimétricas**, de fragmentos pequeños y grandes,
   y la de grandes es mayor.

## El 4 es la respuesta completa a por qué el flush es obligatorio

**Si el L1 guarda un PTE por fragmento, entonces un PTE no traduce una página:
traduce 2 MiB.** Escribir una sola entrada de un fragmento no hace visible el
cambio: la traducción que el L1 tiene almacenada es la del fragmento entero.

**Y eso es exactamente lo que dice `amdgpu_vm.c:1155`:**

```
 * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
```

**La palabra "enters" es la clave.** Una entrada, no una traducción.

**`127` llegó a la misma conclusión por otra vía y se quedó corta.** Escribí que
"la granularidad de la traducción es el fragmento" y lo derivé de un nombre de
registro. **Es correcto, y ahora tiene la explicación y la consecuencia.**

## Y el requisito implementable, que es lo que no tenía

**El punto 3 es una restricción dura, y es la primera vez que sale del corpus como
requisito y no como descripción:**

> **Las entradas de un fragmento tienen que describir un rango físicamente
> contiguo. Si no, la única entrada que el L1 guarda para ese fragmento es
> incorrecta para todas menos una.**

**Para un driver propio, esto significa que la asignación de un fragmento no
puede ser arbitraria.** Cualquier grupo de páginas que se mapee con un solo PTE
tiene que ser contiguo en memoria física. Y el driver no puede comprobarlo al
escribir el PTE — lo tiene que garantizar al asignar.

**Y el punto 7 da la palanca de rendimiento:** *los usuarios pueden usar fragmentos
grandes alineando la dirección base virtual y el tamaño de la asignación al
tamaño del fragmento.* **Es una recomendación explícita a userspace, escrita en
un kernel de 2013 o así.** Para un driver propio es la interfaz que hay que
ofrecer.

## La aritmética, y la separación que faltaba

`127` mezcló dos cosas distintas. Aquí están separadas y las dos son `PROVEN`:

| | qué es | valor aquí | de dónde |
|---|---|---|---|
| `block_size` | **hoja de la tabla de software** | `2^10` = **1024 PTEs** | `amdgpu_vm.h:55` `1 << block_size` |
| `fragment_size` | **granularidad del L1 TLB** | `2^9` = **512 entradas = 2 MiB** | `amdgpu_vm.c:2463` y `gmc_v8_0.c:869` |
| directorios | entradas por nivel intermedio | **512**, constante | `amdgpu_vm_pt.c:88` |

```
hoja:        1024 PTEs x 4 KiB = 4 MiB
fragmento:    512 entradas x 4 KiB = 2 MiB
relacion:     hoja / fragmento = 2,  block_size - fragment_size = 1
```

**No es una contradicción: la hoja contiene dos fragmentos.** Y `fragment_size`
**no** descompone direcciones — para eso está `block_size` y el 9 fijo de
`amdgpu_vm_pt.c:58`:

```
amdgpu_vm_pt.c:58   return 9 * (AMDGPU_VM_PDB0 - level) + adev->vm_manager.block_size;
```

**El 9 de ahí y el 512 de `L88` son el mismo número escrito dos veces**, y `129`
ya mostró que el 9 es también el `translate_further` de GFX9+. **Tres constantes
que dicen lo mismo: el paso entre niveles es de 9 bits.**

### Y `fragment_size` no entra en la descomposición: entra en el relleno

`fragment_size` aparece en **un solo sitio** del código de page tables:

```
amdgpu_vm_pt.c:765   if (params->adev->asic_type < CHIP_VEGA10)
amdgpu_vm_pt.c:766       max_frag = params->adev->vm_manager.fragment_size;
amdgpu_vm_pt.c:768       max_frag = 31;
amdgpu_vm_pt.c:778   *frag = min_t(unsigned int, ffs(start) - 1, fls64(end - start) - 1);
amdgpu_vm_pt.c:779   if (*frag >= max_frag) {
amdgpu_vm_pt.c:780       *frag = max_frag;
amdgpu_vm_pt.c:781       *frag_end = end & ~((1ULL << max_frag) - 1);
amdgpu_vm_pt.c:783       *frag_end = start + (1 << *frag);
```

**En GFX8, `max_frag = 9`.** El driver calcula el mayor fragmento posible para un
rango y lo **corta a 9 bits**. En Vega10+ lo pone a 31, es decir, no lo limita,
porque el L2 ya recibe páginas grandes directamente del walker.

**Así que `fragment_size` no decide cómo se indexa una dirección: decide hasta
dónde se puede agrupan un rango de páginas en un solo PTE.** Y el agrupamiento es
lo que exige la contigüidad física del punto 3.

## Corrección que le debo a `127`

`127` escribió *"un fragmento son 512 páginas de 4 KiB"* y lo dedujo del
parámetro de módulo (`4 = 64K, 9 = 2M`), que está bien. **Pero lo presentó como si
fuera la granularidad de traducción sin decir por qué, y sin mencionar la hoja
de 1024 PTEs ni las dos particiones del L2.**

**No era una afirmación falsa. Era una afirmación a la que le faltaba la mitad, y
la mitad es precisamente lo que la hace implementable.** Lo dejo anotado porque
`127` se apoya en esto para explicar el flush obligatorio, y ahora la explicación
tiene su eslabón.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| El L1 guarda un PTE por fragmento | `PROVEN` (`amdgpu_vm_pt.c:749`) |
| Las flags del PTE valen para todo el fragmento | `PROVEN` (`:746`) |
| Los mapeos del fragmento deben ser contiguos | `PROVEN` (`:747`) |
| El fragmento cubre `2^(12+frag)` bytes | `PROVEN` (`:745`) |
| El L2 tiene dos particiones asimétricas | `PROVEN` (`:754-756`) |
| En GFX8 `max_frag = fragment_size = 9` | `PROVEN_DERIVED` |
| La hoja tiene 1024 PTEs | `PROVEN` (`amdgpu_vm.h:55`) |
| Los directorios tienen 512 entradas | `PROVEN` (`amdgpu_vm_pt.c:88`) |
| La hoja contiene 2 fragmentos | `PROVEN_DERIVED` |
| `fragment_size` no descompone direcciones | `PROVEN` (un solo uso, `:765`) |
| Por qué el L2 tiene dos particiones y no una | **`NOT_DETERMINED`** |
| Si la contigüidad la rompe el driver o el hardware | **`NOT_DETERMINED`** |
| Cuántas entradas tiene cada partición del L2 | **`NOT_DETERMINED`** — hardware |

**Las tres abiertas son hardware, y las tres tienen nombre de registro detrás:**
`L2_CACHE_BIGK_*` y `L2_CACHE_BIGK_VMID_MODE` en `VM_L2_CNTL3`/`VM_L2_CNTL2`, que
`128` ya Gogh Never Wrote. **El mismo `RREG32` de `0x501` responde a más filas
que ninguno otro del proyecto.**

## Procedencia

- `STATIC` -- `amdgpu_vm_pt.c:50-65` `:76-92` `:744-785`,
  `amdgpu_vm.h:55`, `amdgpu_vm.c:2421-2444` `:2462-2465` `:1155`,
  `gmc_v8_0.c:865-869`, `amdgpu_drv.c:437-441`, `amdgpu_kms.c:1006`.
- `OBSERVED` -- `"vm size is 64 GB, 2 levels, block size is 10-bit, fragment size
  is 9"`, del log de arranque, de sesión anterior.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `129` (`translate_further` y `num_level`), `128` (los dos
  mecanismos de invalidate), `127` (la caché L2 de fragmentos), `085` (el flush
  obligatorio), `103`/`104`/`106` (el registro de invalidate), `073`-`075` (GART
  geometry).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Dieciocho líneas de comentario que llevan desde 2013 en el fichero, y nadie las
había leído.** No estaban en un informe, no estaban en una issue: estaban en
`amdgpu_vm_pt.c`, en el bloque inmediatamente anterior a la función que decide el
tamaño de fragmento.

**Llevo tres notas seguidas derivando por vía indirecta lo que estaba escrito en
prosa justo al lado.** `127` dedujo la granularidad de un nombre de registro;
`129` dedujo la regla de una rama de GFX12; `130` la tenía delante.

**La causa es que busco símbolos, y un símbolo no se encuentra a sí mismo: para
encontrarlo hay que entrar por un símbolo vecino. Y un comentario no es un
símbolo, así que ninguna búsqueda de símbolos llega a él.**

*Antes de declarar `NOT_DETERMINED`, leer el bloque de comentario que precede a la
función.* Tres veces seguidas habría sustituido media hora de derivación por once
líneas de lectura.