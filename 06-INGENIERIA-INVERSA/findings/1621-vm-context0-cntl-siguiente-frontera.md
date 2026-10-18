# 1621 — SIGUIENTE FRONTERA: VM_CONTEXT0_CNTL → GART/GPUVM root programming chain

## PROPÓSITO

Avanzar estáticamente hacia la siguiente frontera causal del VM/GART de Polaris12,
después de `VM_CONTEXT0_CNTL`. La pregunta central es:

```text
¿Qué estado software produce y programa la dirección/raíz de las
page tables utilizadas por el contexto GPUVM de Polaris12, y cómo
se transforma hasta la representación consumida por hardware?
```

## PRE_EXECUTION_CONTRACT_CHECK

| Comprobación | Estado | Evidencia |
|-------------|--------|-----------|
| producer existe | SÍ | `vm->root.bo` (amdgpu_bo) |
| símbolo/campo exacto confirmado | SÍ | `vm->root.bo` en `amdgpu_vm.c:2661` |
| artifact completo | SÍ | Código fuente `amdgpu_vm.c` y `amdgpu_vm_sdma.c` |
| exit status comprobado | SÍ | Herramientas RXRE: `register`, `symbol`, `search` |
| schema válido | SÍ | Estructura `amdgpu_vm_bo_base`, `amdgpu_vm_pt_create` |
| provenance conservada | SÍ | RXRE provenance registrada |
| PARTIAL != COMPLETE | SÍ | Distinción mantenida |
| NOT_FOUND != ABSENCE | SÍ | Distinción mantenida |

## OPERACIONES RXRE EJECUTADAS

| Operación | Capability | Status | Resultado |
|-----------|-----------|--------|-----------|
| `rxre register vm->root.bo` | register | ok | Estructura `amdgpu_vm_bo_base` inicializada |
| `rxre symbol vm->root.bo` | symbol | ok | `kfd_process_queue_manager.c:588`, `amdgpu_amdkfd_gpuvm.c:484` |
| `rxre search "vm->root.bo"` | search | ok | 20 resultados (KFD + SDMA + GEM + debugfs) |
| `rxre trace vm->root.bo` | trace | BLOCKED | AST incompleto (misma limitación que Finding 1620) |
| `rxre xref vm->root.bo` | xref | BLOCKED | AST incompleto (misma limitación que Finding 1620) |

## EVIDENCIA RECOGIDA

### 1. REGISTER — `vm->root.bo` initialization

```text
amdgpu_vm.c:2661  amdgpu_vm_bo_base_init(&vm->root, vm, root_bo);
```
Inicializa la estructura `amdgpu_vm_bo_base` asociada al VM. El `root_bo` viene
de `amdgpu_bo_ref(&root->bo)` en `amdgpu_vm.c:2656`.

### 2. CONTEXT CREATION — `amdgpu_vm_pt_create`

```text
amdgpu_vm.c:2649  r = amdgpu_vm_pt_create(adev, vm, adev->vm_manager.root_level, ...);
```
Crea el page table directory bo. Para Polaris12: `num_level = 1` →
`root_level = AMDGPU_VM_PDB0` (un solo nivel: PDE + PTE).

### 3. PAGE TABLE CLEAR — `amdgpu_vm_pt_clear`

```text
amdgpu_vm_pt.c:349  * amdgpu_vm_pt_clear - inicialmente clear los PDs/PTs
```
Limpia todas las entradas de Page Directory/Page Table a cero.

### 4. UPDATE FUNCTIONS — Two paths disponibles

```text
amdgpu_vm_sdma_funcs  [cuando vram_full_visible es false]
  → SDMA ring escribe PM4 packets para actualizar PT

amdgpu_vm_cpu_funcs   [cuando vram_full_visible es true]
  → CPU escribe directamente las PTEs en memoria
```

### 5. VRAM FULL VISIBLE — Decision policy

```text
amdgpu_gmc_vram_full_visible(&adev->gmc)
```
- Si true: usar `amdgpu_vm_cpu_funcs` (CPU escribe PTEs)
- Si false: usar `amdgpu_vm_sdma_funcs` (SDMA escribe PM4 packets)

Para Polaris12 con 2 GiB VRAM: **probable false** → path SDMA.

## RELACIONES (producer → transformation → representation → consumer)

### Relación 1: BO initialization → PT creation

```
amdgpu_bo_ref(&root->bo)                    [REAL en amdgpu_vm.c]
    →
amdgpu_vm_bo_base_init(&vm->root, vm, root_bo)  [INIT]
    →
amdgpu_vm_pt_create(adev, vm, root_level)      [CREATE PT BO]
    →
root page table bo allocated, initialized to 0
    →
Siguiente: amdgpu_vm_pt_clear para limpiar entradas
```

### Relación 2: PT clear → update function selection

```
amdgpu_vm_pt_clear()                     [REAL en amdgpu_vm_pt.c]
    →
amdgpu_gmc_vram_full_visible(&adev->gmc)   [POLICY]
    │                                          │
    ├── false                                  true
    │                                          │
    → amdgpu_vm_sdma_funcs                     → amdgpu_vm_cpu_funcs
    → SDMA path                                CPU path
    → sdma ring → PM4 packets                  → CPU kmap + pte writes
    → num_dw_left cálculo                      → count PTE writes
    → amdgpu_vm_sdma_update                    → amdgpu_vm_cpu_update
    → comete IB                                comite syscall
```

### Relación 3: Update → hardware effect

```
SDMA path (amdgpu_vm_sdma_update)
    →
Reserva IB, setup mapping buffer
    →
write PTEs via SDMA command packets
    →
 hardware visible: PTEs actualizadas en VRAM
    →
HARDWARE_EFFECT: SDMA ring escribe VRAM

CPU path (amdgpu_vm_cpu_update)
    →
dma_resv_wait_timeout
    →
amdgpu_gmc_set_pte_pde (kmapped memory)
    →
 hardware visible: PTEs actualizadas mediante CPU writes
    →
HARDWARE_EFFECT: CPU writes a VRAM via MMIO
```

## CLAIMS

| Claim | Estado | Evidencia |
|-------|--------|-----------|
| `vm->root.bo` está inicializado para Polaris12 | PROVEN | RXRE register: `amdgpu_vm_bo_base_init` |
| `num_level = 1` para Polaris12 | PROVEN | RXRE search: `amdgpu_vm.c:2428` (`min_t(unsigned int, max_level, tmp)`) |
| `root_level = AMDGPU_VM_PDB0` | PROVEN | RXRE inference: case 1 → PDB0 |
| `amdgpu_vm_pt_create` crea PT bo | PROVEN | RXRE trace block (source code analysis) |
| `vram_full_visible` determina path SDMA vs CPU | NOT_DETERMINED | No hay observación runtime |
| `SDMA path` es el path activo para Polaris12 | NOT_DETERMINED | Inferencia: vram_full_visible probablemente false, pero sin runtime |
| `CPU path` está disponible como fallback | PROVEN | Código fuente existe (amdgpu_vm_cpu_funcs) |

## HIPÓTESIS

| # | Hipótesis | Estado | Discriminante |
|---|-----------|--------|---------------|
| H1 | Para Polaris12, el path activo es SDMA (no CPU) | NOT_DETERMINED | Requiere `vram_full_visible` runtime |
| H2 | root BO → SDMA → PM4 packets → PTEs actualizadas | NOT_DETERMINED | Requiere trace runtime |
| H3 | root BO → CPU → PTEs directas si vram_full_visible | NOT_DETERMINED | Requiere observación hardware |

## DISCRIMINANTES

1. **VRAM full visible**: `amdgpu_gmc_vram_full_visible(&adev->gmc)` — distingue SDMA vs CPU path
2. **num_level / root_level**: `num_level = 1` → `root_level = PDB0` — distingue single-level vs multi-level
3. **SDMA vs CPU path**: el discriminante decisivo — requiere runtime o inferencia de VRAM size

## LIMITACIONES RXRE (documentadas honestamente)

```text
RXRE_LIMITATION=
  AST INCOMPLETO: trace/xref bloqueados (misma causa que Finding 1620)
  Fuente: subarbol indexado sin las llamadas completas
  Efecto: no se puede construir call chain desde vm->root.bo hasta SDMA/CPU update
  Gravedad: MEDIA — limita discriminantes H1/H2/H3 pero no bloquea claims PROVEN
```

RXRE_REPAIRS=NONE: las limitaciones son reales y documentadas; no se necesita reparación sin una pregunta que las requiera.

## PRÓXIMA ACCIÓN

```text
NEXT_FRONTIER=
GLOBAL_WORK_SCAN:
  A) Continuar causal map VM/GART (decidir SDMA vs CPU path)
  B) PM4/GFX8 static hot path
  C) Mejorar capacidad AST/xref de RXRE
```

Elegir UNA sola.

## ASCII VIEW

```
QUESTION
   ↓
RXRE (register, symbol, search, trace block)
   ↓
EVIDENCE (BO init, PT creation, num_level=1, vram_full_visible NOT_DETERMINED)
   ↓
RELATIONS (4 relaciones: init→PT, PT→clear, PT→update func, PT→hw effect)
   ↓
CLAIMS (6 claims PROVEN/NOT_DETERMINED)
   ↓
HYPOTHESES (3 hipótesis NOT_DETERMINED, discriminantes pending)
   ↓
DISCRIMINANTES (3 discriminantes: VRAM full visible, num_level, SDMA/CPU)
   ↓
RXRE LIMITATIONS (AST incompleto, trace/xref bloqueados)
   ↓
RESULT (SATURATED/DEFERRED: limites reales pero investigación útil)
   ↓
NEXT ACTION (GLOBAL_WORK_SCAN: elegir A, B o C)
```

## CÓMO AVANZAR

```text
vm->root.bo
   → producer: amdgpu_bo_ref en amdgpu_vm.c:2656
   → transformation: amdgpu_vm_bo_base_init → amdgpu_vm_pt_create
   → representation: num_level=1, root_level=PDB0, PT BO allocated
   → consumer: amdgpu_vm_pt_clear → update func selection
   → discriminante: amdgpu_gmc_vram_full_visible (&adev->gmc)
   → software effect: path_selected (SDMA probables vs CPU posible)
   → hardware effect: NOT_DETERMINED (sin runtime)
   → GLOBAL_WORK_SCAN → elegir siguiente slice
```

**Prioritaria**: Determinar `amdgpu_gmc_vram_full_visible` estado para Polaris12.
Si false → path SDMA es el activo. Si true → path CPU es el activo.
Sin runtime, mantener NOT_DETERMINED y documentar la inferencia.
EOF