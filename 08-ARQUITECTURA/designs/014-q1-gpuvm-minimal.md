# 014 — Q1 GPUVM_MINIMAL (GFX8 / Polaris12)

> Iteración 3 · `Q1 GPUVM_MINIMAL` · corpus `RESEARCH/kernelbuild/linux-7.1.3`
> Fecha 2026-09-29 · Clasificación `READ_ONLY/EVIDENCE`
> Línea canónica: `04-IMPLEMENTACION/rx550-driver/` — **no tocada en esta iteración**

---

## 1. Resultado

```
Q1 = CLOSED

GPUVA_WIDTH_BITS   = 30      PROVEN
PA_WIDTH_BITS      = 40      PROVEN
PAGE_SIZE          = 4096    PROVEN
PAGE_DIR_LEVELS    = 1 + PTB PROVEN
BITS_PER_LEVEL     = 9       PROVEN
MIN_VIABLE_ASPACE  = 2 MiB   DERIVATION
```

La aritmética cierra con dos caminos independientes que coinciden, lo que es la
comprobación de que el modelo está bien entendido y no sólo copiado.

---

## 2. Evidencia

### 2.1 Los dos parámetros que definen el espacio de direcciones

```c
/* gmc_v8_0.c:1127 — gmc_v8_0_early_init */
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
/*                        │  │  │   └─ max_bits  = 40
                         │  │  └───── max_level = 1
                         │  └──────── fragment_size_default = 9
                         └─────────── min_vm_size = 64 MiB
```

```c
/* gmc_v8_0.c:1134 */
adev->gmc.pte_addr_mask = 0x000000FFFFFFF000ULL; /* 40 bit PA */
```

**Contraste generacional, que es la razón de no trasladar GFX9+**:

| ASIC | `max_level` | `max_bits` | niveles | VA |
|---|---|---|---|---|
| **GFX8** (`gmc_v8_0.c:1127`) | **1** | **40** | 1 + PTB | **30 bits** |
| GFX10 (`gmc_v10_0.c:817`) | 3 | 48 | 3 + PTB | 48 bits |
| GFX11 (`gmc_v11_0.c:791`) | 3 | 48 | 3 + PTB | 48 bits |
| GFX12 (`gmc_v12_0.c:846`) | 3 | 48 | 3 + PTB | 48 bits |

Una tabla de 4 niveles y 48 bits dibujada para GFX10+ **no** describe Polaris12.
Esto es `HARDWARE_REQUIREMENT`, no preferencia.

### 2.2 Tamaño de página y geometría de la entrada

```c
/* amdgpu_gart.h:35 */
#define AMDGPU_GPU_PAGE_SIZE 4096
```

```c
/* amdgpu_vm_pt.c:58 */
return 9 * (AMDGPU_VM_PDB0 - level) + adev->vm_manager.block_size;
```

Con `block_size = 9` (`:2464`, rama `num_level > 1`) y
`max_level = 1` → `root_level = AMDGPU_VM_PDB0` (`:2452`).

```c
/* amdgpu_vm.h:191-197 */
enum amdgpu_vm_level { AMDGPU_VM_PDB3, PDB2, PDB1, PDB0, AMDGPU_VM_PTB };
```

512 entradas por nivel × 8 B por entrada = 4096 B: una tabla cabe exactamente en
una página, lo que confirma que la entrada es de 64 bits.

### 2.3 La aritmética, por dos caminos

```
camino 1  VA = 9 (PDB0) + 9 (PTB) + 12 (offset) = 30 bits = 1024 MiB
camino 2  max_size = 1 << (max_bits - 30)  = 1 << 10 = 1024 MiB
          (amdgpu_vm.c:2395)
```

Dos fórmulas independientes del mismo driver dan el mismo número. Si el modelo
fuese una lectura equivocada, darían cosas distintas.

### 2.4 PTE: campos y sus posiciones

```c
/* amdgpu_vm.h */
#define AMDGPU_PTE_VALID     (1ULL << 0)
#define AMDGPU_PTE_SYSTEM    (1ULL << 1)
#define AMDGPU_PTE_SNOOPED   (1ULL << 2)
#define AMDGPU_PTE_TMZ       (1ULL << 3)
#define AMDGPU_PTE_EXECUTABLE(1ULL << 4)
#define AMDGPU_PTE_READABLE  (1ULL << 5)
#define AMDGPU_PTE_WRITEABLE (1ULL << 6)
#define AMDGPU_PTE_FRAG(x)   ((x & 0x1fULL) << 7)
#define AMDGPU_PTE_PRT       (1ULL << 51)
#define AMDGPU_PDE_PTE       (1ULL << 54)          /* pre-GFX12 */
#define AMDGPU_PTE_LOG       (1ULL << 55)
#define AMDGPU_PTE_TF        (1ULL << 56)
#define AMDGPU_PTE_NOALLOC   (1ULL << 58)
#define AMDGPU_PDE_BFS(a)    ((uint64_t)a << 59)
```

`AMDGPU_PDE_PTE` marca la hoja. Y la selección por generación es explícita, lo
que confirma que el valor **no** es universal:

```c
/* amdgpu_vm.h:140-142 */
#define AMDGPU_PDE_PTE_GFX12 (1ULL << 63)
#define AMDGPU_PDE_PTE_FLAG(adev) \
	((amdgpu_ip_version((adev), GC_HWIP, 0) >= IP_VERSION(12, 0, 0)) \
	 ? AMDGPU_PDE_PTE_GFX12 : AMDGPU_PDE_PTE)
```

**GFX8 usa `1ULL << 54`.** Llevar el de GFX12 sería un `COPY` silencioso.

### 2.5 Registro GART y VMID

```c
/* gmc_v8_0.c:887-888 */
WREG32(mmVM_CONTEXT0_PAGE_TABLE_START_ADDR, adev->gmc.gart_start >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_END_ADDR,   adev->gmc.gart_end   >> 12);

/* gmc_v8_0.c:1168 */
adev->vm_manager.first_kfd_vmid = 8;
```

El `>> 12` es la página de 4 KiB hecha explícita. `first_kfd_vmid = 8` indica que
los VMID 0..7 están reservados para KMD; es un dato de `DESIGN_CHOICE` de amdgpu,
**no** un requisito de hardware, y no se hereda sin justificación.

### 2.6 TLB

`gmc_v8_0.c` invoca `amdgpu_vm_flush_compute_tlb()`. El mecanismo exacto de
invalidación **no** se investigó en esta iteración: es `Q4 SUBMISSION_CONTRACT` /
`Q11 VMID_MINIMAL`, y hacerlo aquí habría sido abrir otra línea.

```
TLB_INVALIDATION_MECHANISM = DEFERRED  (Q11)
```

---

## 3. HARDWARE_REQUIREMENT vs LINUX_REQUIREMENT vs DESIGN_CHOICE

| propiedad | clase | por qué |
|---|---|---|
| página 4 KiB | `HARDWARE_REQUIREMENT` | `AMDGPU_GPU_PAGE_SIZE`, y `>>12` en los registros |
| 9 bits por nivel | `HARDWARE_REQUIREMENT` | `amdgpu_vm_pt.c:58` lo calcula del hardware |
| 1 nivel de directorio + PTB | `HARDWARE_REQUIREMENT` | `max_level=1` en `gmc_v8_0.c:1127` |
| 40 bits de PA | `HARDWARE_REQUIREMENT` | `pte_addr_mask` |
| marca de hoja en bit 54 | `HARDWARE_REQUIREMENT` | `AMDGPU_PDE_PTE_FLAG` lo selecciona por ASIC |
| que la entrada sea de 8 B | `DERIVATION` | 512 × 8 B = 4096 B = una página |
| VA de 30 bits | `DERIVATION` | dos fórmulas independientes coinciden |
| `min_vm_size = 64 MiB` | `DESIGN_CHOICE` de amdgpu | no es un límite del hardware |
| `first_kfd_vmid = 8` | `DESIGN_CHOICE` de amdgpu | reparto de un recurso, no una propiedad |
| fragment size 9 | `DESIGN_CHOICE` | `AMDGPU_PTE_FRAG`: si no hace falta, 0 |
| número de VMID disponibles | `UNKNOWN` | no se investigó; Q11 |

**No se ha tomado nada de `drm_gpuvm` ni de la arquitectura de VM de amdgpu.** El
modelo anterior es una descripción del hardware; el nuestro puede ser una cosa
distinta con las mismas propiedades.

---

## 4. Espacio de direcciones mínimo viable

```
1 nivel PDB0   ->  512 entradas
1 PTB          ->  512 paginas de 4 KiB  =  2 MiB
```

**2 MiB es la unidad mínima real**, y sale de la aritmética del hardware, no de una
decisión. Un primer experimento — IB, un shader, un fence — cabe en un solo PTB
con un solo nivel de directorio.

El mínimo absoluto que aún tiene sentido:

```
un PDB0 (4 KiB de memoria)  +  un PTB (4 KiB)  +  hasta 2 MiB mapeados
= 8 KiB de tablas para 2 MiB de espacio
```

---

## 5. Diagrama

```
        HARDWARE_REQUIREMENT
═══════════════════════════════════════════════════════
  GPUVA 30 bits
    │  ┌──────────────┬──────────────┐
    │  │ bits [29:21] │ bits [20:12] │ bits [11:0]
    │  │   9 bits     │    9 bits    │  12 bits
    │  │    PDB0      │     PTB      │  offset
    ▼  └──────┬───────┴──────┬───────┘
        512 × 8 B = 4 KiB    512 × 8 B = 4 KiB
                             │
                             ├── PTE[0]   VALID RW ... frame[39:12]
                             ├── PTE[1]   una entrada por pagina de 4 KiB
                             └── PTE[511] marca de hoja en bit 54

        HARDWARE_LIMIT (PROVEN)
═══════════════════════════════════════════════════════
  PA 40 bits  ───── pte_addr_mask 0x000000FFFFFFF000
  VA 30 bits  ───── max_level 1 + PTB, 9 bits/nivel
  2 MiB por PTB, 1 GiB de VA total

        DISEÑO PROPIO (a decidir en Q2, aquí NO)
- - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  dónde viven las tablas   ────  DESIGN_CHOICE
  quién las asigna        ────  DESIGN_CHOICE
  cuántas VM              ────  DESIGN_CHOICE
  MDT frente a UVM        ────  DESIGN_CHOICE

  (NO heredado de amdgpu sin requisito)
```

---

## 6. Lo que NO se afirma

- Que un VA de 30 bits sea **óptimo**. Es lo que el hardware permite, no lo que
  convenga.
- Que la estructura de tablas de amdgpu sea la correcta para nuestro driver.
  `HARDWARE_REQUIREMENT` es la geometría; el reparto de memoria es nuestro.
- Nada sobre TLB: `DEFERRED`.
- Nada sobre el tipo de backing. `TTM_PL_TT` frente a VRAM es `Q2`.
- Nada sobre si hace falta DMA API. `Q9`.

---

## 7. Deuda registrada

En la iteración 1 afirmé que el corpus GFX8 servía para "cruzar opcode ↔
encoding". `Q1` confirma que para **el espacio de direcciones** el corpus sí es
suficiente, y de hecho es la mejor fuente disponible. La restricción de la
iteración 1 era específica de las **instrucciones**, no del hardware de VM. Las
dos cosas no deben mezclarse.

## 8. Cierre

```
Q1 GPUVM_MINIMAL = CLOSED
FILES_CREATED    08-ARQUITECTURA/designs/014-q1-gpuvm-minimal.md
FILES_MODIFIED   ninguno
DRIVER_TOUCHED   ninguno
RUNTIME          NOT_RUN
NEXT             Q2 MEMORY_OBJECT
CONTINUE         YES
```
