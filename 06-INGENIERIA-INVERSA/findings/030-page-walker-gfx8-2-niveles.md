# 030 · El page walker GFX8 es de 2 niveles y sin huge pages, y corrijo un error mío de `block_size`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `CONTINUES=017–029`
`CORRECTS=019 §5 y el informe de la iteración 5`

## CUDA principal

Dos cosas, y la primera es una corrección de un número que yo publiqué mal.

**El page walker de GFX8 tiene un único modo de operación: 2 niveles, siempre hasta el
PTB.** El driver se niega a usar un nivel no-hoja como hoja antes de GMC v9, literalmente:

```c
/* amdgpu_vm_pt.c:825-832 */
} else if (adev->asic_type < CHIP_VEGA10 && (flags & AMDGPU_PTE_VALID)) {
        /* No huge page support before GMC v9 */
        if (cursor.level != AMDGPU_VM_PTB) { ... continue; }
}
```

No hay descriptores de bloque en operación normal. `PAGE_TABLE_BLOCK_SIZE` existe en el
registro pero el driver no lo usa como tamaño de bloque.

**Y me equivoqué en `block_size`.** Reporté 13/14/15. Es **22/23/24**.

## La corrección

En la iteración 5 calculé `block_size` pasando `vm_size` a `amdgpu_vm_get_block_size()`.
El código pasa **`tmp`**:

```c
/* amdgpu_vm.c:2400, 2430 */
tmp = roundup_pow_of_two(adev->vm_manager.max_pfn);
...
adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);
```

`tmp` es un número de páginas redondeado a potencia de dos, no un tamaño en GiB. Feeding
`vm_size=64` a una función cuyo parámetro se llama `vm_size` pero cuyo uso real es páginas
metió mi cálculo por la rama `vm_size <= 8`, que da `bits-9` en vez de `(bits+3)/2`.

| RAM del host | `block_size` correcto | el que publiqué | `PAGE_TABLE_BLOCK_SIZE` |
|---|---:|---:|---:|
| ≤ 21 GB | **22** | 13 ❌ | 13 |
| 22–42 GB | **23** | 14 ❌ | 14 |
| 43–85 GB | **23** | 14 ❌ | 14 |
| ≥ 86 GB | **24** | 15 ❌ | 15 |

Lo irónico: el número que publiqué como `PAGE_TABLE_BLOCK_SIZE` (13/14/15) es el correcto
para ese campo. Confundí el campo con su fuente. El error no se propagó a ningún veredicto
—`019` sólo lo usaba para mostrar que `block_size` depende del host, y esa conclusión sigue
siendo cierta—, pero el número estaba mal y `019 §5` lo publica.

## La geometría del walk, con el valor correcto

`block_size = 22` con 16 GB de RAM:

```
VA[39:31]  6 bits   índice de PDE   (max_bits - 12 - block_size)
VA[30:9]  22 bits   índice de PTE   (= block_size = AMDGPU_VM_PTE_COUNT)
VA[8:0]   12 bits   offset de página
```

`AMDGPU_VM_PTE_COUNT(adev) = 1 << block_size` (`amdgpu_vm.h:55`) es la definición directa
del ancho del índice de PTE. Un PTB con 2^22 entradas cubre 16 GiB; un PDB con 2^6 entradas
los indexa todos: 2^40 bytes = **1024 GiB**, que es exactamente `max_size` con `max_bits=40`.

Con 22 bits de índice de PTE el walk es una tabla plana de 4 Mi entradas por PTB. Eso tiene
una consecuencia práctica que `019` no vio: **`max_bits = 40` y `max_level = 1` fuerzan un
índice de PTE enorme**, porque el presupuesto de bits se reparte entre los dos niveles y el
driver reparte casi todo al inferior.

## Niveles

```
num_level = 1                       -> root_level = AMDGPU_VM_PDB2   (amdgpu_vm.c:2410-2411)
enum: PDB3=0, PDB2=1, PDB1=2, PDB0=3, PTB=4   (amdgpu_vm.h:194-196)
PAGE_TABLE_DEPTH = 1 para VMID 1-15, 0 para VMID 0   (gmc_v8_0.c:889, :919)
```

`amdgpu_vm_pt_level_shift()` da `9*(PDB0-level) + block_size` para los PDB y `0` para el
PTB. Con `block_size=22`: PDB2→31, PDB1→40, PDB0→22, PTB→0. Es una función de
fragmentación, no el ancho del índice; el ancho sale de los conteos.

## Lo que queda abierto

| Afirmación | Estado |
|---|---|
| El walk GFX8 es de 2 niveles y sin huge pages | `PROVEN` por el predicado de `amdgpu_vm_pt.c:825` |
| `block_size` = 22/23/24 según RAM | `PROVEN_DERIVED` — corregido aquí |
| Los índices VA[30:9] y VA[39:31] | `PROVEN_DERIVED` de los conteos y `max_bits` |
| Que el hardware extraiga el índice así | `NOT_DETERMINED` — es inferencia del layout, no del siliconio |
| Si un PTB puede existir sin PDE válido (walk recortado) | `NOT_OBSERVED` |

El último es el hueco real que queda: el formato del PTE de GFX8 tiene el bit 3 *reserved*
(`gmc_v8_0.c:685-695`) y nada en el corpus explica qué hace el hardware con una entrada
inválida a media translated. Requiere el documento de arquitectura de GFX8, no el código.

## UNLOCKS

- El driver propio necesita **una sola** estructura de datos: tabla plana de entradas de
  8 bytes indexada por `VA >> 9`, y una tabla de PDE de entradas de 8 bytes indexada por
  `VA >> 31`. Dos niveles, sin variantes.
- `PAGE_TABLE_BLOCK_SIZE` no controla el tamaño de bloque en GFX8. Es un campo que existe y
  que el driver no exploita; `DESIGN_FREEDOM` deja abierto si el driver propio debe
  escribirlo o dejarlo a cero.
- La corrección de `block_size` cambia el tamaño de la tabla GART de ~1 MB a ~64 MB
  (65536 entradas × 8 bytes es el número de `29⁄9⁄26.md`; con el PTE real, el número
  depende de `block_size`, no de `gart_size`).

## Corrección de `019 §5`

`019 §5` publicaba la tabla con `block_size` 13/14/15 y afirmaba que
`PAGE_TABLE_BLOCK_SIZE = block_size - 9` coupling con el rango de aperture. El coupling es
correcto (`gmc_v8_0.c:927-928`); los valores de `block_size` no. Corregido aquí, y el
finding original queda marcado como `CORRECTED_BY=030` en lugar de reescrito, porque
`AGENTS.md` §Documentación prohíbe sobrescribir evidencia histórica.

## Evidencia

```
amdgpu_vm.c:      2326-2343 (get_block_size), 2397-2430 (adjust_size),
                  2410-2411 (root_level), 2840-2843 (concurrent_flush)
amdgpu_vm.h:      55 (AMDGPU_VM_PTE_COUNT), 194-196 (enum de niveles)
amdgpu_vm_pt.c:   50-62 (level_shift), 825-832 ("No huge page support before GMC v9")
gmc_v8_0.c:       685-703 (formato PTE/PDE), 889 y 919 (PAGE_TABLE_DEPTH),
                  927-928 (PAGE_TABLE_BLOCK_SIZE = block_size - 9)
```

`TEMPORALITY`: `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`, `HOST_SCOPE=n/a`. Ningún registro
leído de MMIO. `RUNTIME=NOT_RUN`. `MODIFICATIONS=0`.