# 032 · "Entrada inválida" en GFX8 no es `VALID=0`: es un PTE válido que apunta a 0

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=rx550-upstream-7.2.8/linux-7.2.8`
`RUNTIME=NOT_RUN` · `GPU INTACTA` · `CIERRA=030 §"Lo que queda abierto"`

## CUDA principal

El último hueco estático de la frontera de page tables era: *el bit 3 del PTE está reservado
y nada explica qué hace el hardware con una entrada inválida a media traducción*.

La respuesta es que **ese caso no se da**. El driver no marca entradas como inválidas
poniendo `VALID=0` en GFX8. Las tres estrategias que usa para "no translation" son todas
**PTE válidos apuntando a algún sitio**:

```c
/* amdgpu_vm.c:3043-3062, dentro de amdgpu_vm_handle_fault */
addr /= AMDGPU_GPU_PAGE_SIZE;
flags = AMDGPU_PTE_VALID | AMDGPU_PTE_SNOOPED | AMDGPU_PTE_SYSTEM;

if (is_compute_context) {
        /* Intentionally setting invalid PTE flag
         * combination to force a no-retry-fault */
        flags = AMDGPU_VM_NORETRY_FLAGS;
        value = 0;
} else if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_NEVER) {
        /* Redirect the access to the dummy page */
        value = adev->dummy_page_addr;
        flags |= AMDGPU_PTE_EXECUTABLE | AMDGPU_PTE_READABLE |
                 AMDGPU_PTE_WRITEABLE;
} else {
        /* Let the hw retry silently on the PTE */
        value = 0;
}
```

El bit 0 (`VALID`) está a 1 en las tres ramas. **El hardware nunca ve una traducción
"invalida" en este camino.**

## Las tres estrategias

| rama | condición | `value` (PA) | flags notables | efecto |
|---|---|---|---|---|
| KVM/compute | `is_compute_context` | `0` | `AMDGPU_VM_NORETRY_FLAGS` = `EXECUTABLE｜PDE_PTE｜TF` | **falla sin reintentar** |
| por defecto | `FAULT_STOP_NEVER` (parám 0) | `dummy_page_addr` | `+EXECUTABLE｜READABLE｜WRITEABLE` | **redirige a la página dummy** |
| debugger | `FAULT_STOP_PRINT/ALWAYS` | `0` | `VALID｜SNOOPED｜SYSTEM` | **reintenta en silencio para siempre** |

`amdgpu_vm_fault_stop` vale `0` por defecto (`amdgpu_drv.c:173`), luego **la rama efectiva
en metal desnudo es la del dummy page**.

## El dummy page

```c
/* amdgpu_gart.c:75-90 */
struct page *dummy_page = ttm_glob.dummy_read_page;
adev->dummy_page_addr = dma_map_page_attrs(&adev->pdev->dev, dummy_page, 0,
                                          PAGE_SIZE, DMA_BIDIRECTIONAL,
                                          DMA_ATTR_SKIP_CPU_SYNC);
```

Una página del propio TTM, mapeada por DMA. La dirección es un **IOMMU/PA real**, no un
sentinel. Se usa en tres sitios:

| uso | lugar |
|---|---|
| rellenar entradas GART liberadas | `amdgpu_gart.c:326` (`amdgpu_gart_unbind`) |
| destino de faults de VM | `amdgpu_vm.c:3055` |
| `VM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR` | `gmc_v8_0.c:884-885, 914-915` |

Y hay un cuarto, en el hardware de interrupciones: `cik_ih.c:116` escribe
`adev->dummy_page_addr >> 8` en `mmINTERRUPT_CNTL2`. La página dummy es también el destino
de las interrupts de página.

## Lo que significa para el driver propio

`REQUIREMENT` concreto, no suposición:

**GFX8 no tiene un marker de "inválido" en el PTE.** Las tres opciones son apuntar a 0,
apuntar al dummy, o una combinación de flags sin retry. Un driver propio que ponga
`VALID=0` está usando una codificación que el driver de referencia nunca exercise, y
`030 §"Lo que queda abierto"` no puede resolver por qué.

La elección de `value = 0` **con `VALID=1`** es la que más se le escapa a quien lee el
formato del PTE: parece un PTE normal apuntando a la dirección física 0, y en realidad es el
"retry forever". Un driver propio que mapee algo en PA 0 tendrá una traducción válida
silenciosa.

## Lo que sigue abierto

| Afirmación | Estado |
|---|---|
| El bit 3 no se usa como inválido | `PROVEN` por lectura del productor |
| Cuál es el efecto hardware de un PTE válido con PA=0 | `NOT_DETERMINED` — el comentario dice "retry silently", lo cual es interpretación |
| Si el hardware trata `VALID=0` distinto de "PA=0 con VALID=1" | `NOT_DETERMINED` — exige la spec de GFX8 |
| Qué es exactamente `PDE_PTE` (bit 54) en GFX8, donde los bits 40+ son reservados | `NOT_DETERMINED` — `AMDGPU_VM_NORETRY_FLAGS` lo incluye pero el PTE de GFX8 no lo documenta |

La última es la más incómoda: `AMDGPU_VM_NORETRY_FLAGS` incluye `AMDGPU_PDE_PTE` (bit 54),
que según el comentario de `amdgpu_vm.h:75-76` es *"PDE is handled as PTE for VEGA10"*. En
GFX8 los bits 40-63 están reservados, así que **el flag de no-retry para KVM escribe un bit
que el formato de GFX8 no define**. O el hardware GFX8 lo interpreta igualmente, o la rama
`is_compute_context` no funciona en GFX8. `NOT_DETERMINED`, y es el hueco que queda.

## UNLOCKS

- El driver propio tiene una respuesta concreta para "qué escribo en una entrada no
  mapeada": PTE válido con PA=0, y opcionalmente apuntando al dummy. No hay tercera vía.
- El dummy page es un concepto del driver, no del hardware: una página DMA cualquiera. El
  driver propio puede usar la suya.
- La rama `is_compute_context` es un camino KVM que usa un flag no documentado en GFX8. Para
  un driver propio metal desnudo es irrelevante, pero si alguien quiere hacer
  passthrough esa es la línea a verificar primero.

## Criterio de falsación

Se refutaría si apareciera un productor de PTE en el path GFX8 que escribiera
`VALID=0`. La búsqueda hecha es `grep -rn "set_invalid"` sobre `amdgpu/*.c`, que devuelve
**cero** referencias, y el único productor de entradas no mapeadas de este camino es
`amdgpu_vm_handle_fault`. Un productor en `amdgpu_gart_unbind` también escribe sin `VALID`:
`flags = 0` y `page_base = dummy_page_addr` (`amdgpu_gart.c:315, 326`). Ahí sí hay
`VALID=0`, con el dummy como PA. **Corrección**: el caso GART sí usa `VALID=0`, y lo usa
para rellenar. La diferencia con `amdgpu_vm_handle_fault` es que allí el propio PTE es el
que se invalida; en la GART se rellena con un PTE no-válido que apunta al dummy. La
afirmación del cuerpo de este documento debe leerse como referida a la traducción
de VM, no a la tabla GART.

## Evidencia

```
amdgpu_vm.c:        3043-3062 (las tres estrategias), 3070-3075 (update_range + update_pdes),
                    2593 (need_tlb_fence)
amdgpu_gart.c:      75-90 (dummy_page_init), 99-108 (fini), 308-339 (unbind, flags=0)
amdgpu_drv.c:       173 (fault_stop = 0 por defecto), 450-456 (documentación del parámetro)
amdgpu_vm.h:        88-95 (NORETRY_FLAGS, NORETRY_FLAGS_TF), 72-84 (PRT, PDE_PTE, TF, NOALLOC)
gmc_v8_0.c:         685-703 (formato PTE/PDE: bit 3 reservado, 40-63 reservados),
                    884-885 y 914-915 (PROTECTION_FAULT_DEFAULT_ADDR = dummy >> 12)
cik_ih.c:           116 (mmINTERRUPT_CNTL2 = dummy >> 8)
```

`grep -rn "set_invalid" amdgpu/*.c` → **0 resultados**: no existe un productor que marque
entradas inválidas en GFX8 por el camino de VM. `HOST_SCOPE=n/a` (statements sobre el driver
de referencia). `RUNTIME=NOT_RUN`. `MODIFICATIONS=0`.