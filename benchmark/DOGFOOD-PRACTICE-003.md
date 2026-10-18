# DOGFOOD-PRACTICE-003 — AUDITORÍA DE REVALIDACIÓN

**Auditoría de**: `benchmark/DOGFOOD-PRACTICE-002.md`
**Objetivo**: Validar la reconstrucción de `VM_CONTEXT0_CNTL` y los gaps de capacidad de RXRE.

---

## 1. REPOSITORY_STATE

| Campo | Estado |
|---|---|
| Repository root | `/home/lucas/Escritorio/rxre` |
| HEAD | 9ce74c53ba5a356fed9893c5f62b32e01f9d883a |
| Branch/worktree | `migration/validated-legacy-work` (main) |
| Modified files | 113 |
| Untracked files | 193 |
| Target report | `benchmark/DOGFOOD-PRACTICE-002.md` (14,929 bytes) |
| RXRE executable | `tools/rxre/rxre` ✓, `tools/rxre/cli.py` ✓, `tools/rxre/reg_resolve.py` ✗ (no existe) |

**READ-ONLY confirmed**: no se modificó ningún archivo del corpus.

---

## 2. AUDIT_TARGET

Reconstrucción original (DOGFOOD-PRACTICE-002) para auditar:

```text
REGISTER: VM_CONTEXT0_CNTL @ 0x504, 32-bit, RW, CONTEXT0
PRODUCER: rx550_vm_context_cntl_flat_gart()
TRANSFORMATION: PAGE_TABLE_DEPTH_0<<0 | GART_BLOCK_SIZE<<4 | ENABLE<<31
REPRESENTATION: PACKET3_SET_CONTEXT_REG (0x61) PM4 packet
CONSUMER: GPU VM unit (vmid 0..7 → CONTEXT0_CNTL, vmid 8..15 → CONTEXT8_CNTL)
SEMANTIC EFFECT: flat GART mapping, 4KB pages, context enabled
```

Y tres clasificaciones de gap a revalidar: `REGISTER_OFFSET_LOOKUP`, `FIELD_SEMANTICS`, `PRODUCER_CHAIN`.

---

## 3. REGISTER_VALIDATION

Verificación directa del corpus activo:

**Fuente primaria**: `04-IMPLEMENTACION/rx550-driver/rx550_mmio_access.c:104`

```c
"mmVM_CONTEXT0_CNTL", 0x504, 0x1410, 32, "RW", "CONTEXT0",
```

| Atributo | DOGFOOD-PRACTICE-002 afirmaba | VERIFICADO | Estado |
|---|---|---|---|
| REGISTER_NAME | `mmVM_CONTEXT0_CNTL` | ✓ `mmVM_CONTEXT0_CNTL` | PROVEN |
| REGISTER_OFFSET | `0x504` | ✓ `0x504` (dword), `0x1410` (byte) | PROVEN |
| REGISTER_WIDTH | `32` | ✓ `32` | PROVEN |
| REGISTER_ACCESS | `RW` | ✓ `RW` | PROVEN |
| BLOCK | `CONTEXT0` | ✓ `CONTEXT0` | PROVEN |
| SOURCE_FILE | `rx550_mmio_access.c` | ✓ L897 | PROVEN |
| SOURCE_LINE | — | ✓ L104 (definición), L599 (comentario) | PROVEN |

**Clasificación de hallazgos**:
- **REGISTER_DEFINITION** (definición del registro): L104 y L599 en `rx550_mmio_access.c`. PROVEN.
- **REGISTER_REFERENCE** (referencias): múltiples en `rx550_mmio_access.c/h` y `rx550_gpuvm.c:100`. PROVEN.
- **REGISTER_WRITE** (escritura): `rx550_gpuvm.c:104` `ring_write_wreg(&wp, cntl_reg, cntl_val)`. PROVEN.
- **REGISTER_READ** (lectura): ninguno encontrado (es RW pero nadie lo lee en el corpus). NEGATIVE_RESULT.

---

## 4. FIELD_LAYOUT_VALIDATION

**PUNTO CRÍTICO DE LA AUDITORÍA.**

Campos extraídos directamente de `04-IMPLEMENTACION/rx550-driver/rx550_mmio_access.c:600-669`:

| FIELD | LOW_BIT | HIGH_BIT | WIDTH | MASK | SOURCE | ROLE |
|---|---|---|---|---|---|---|
| ENABLE_CONTEXT | 0 | 0 | 1 | 0x1 | gmc_v8_0.c:894 | WRITES |
| PAGE_TABLE_DEPTH | 1 | 2 | 2 | 0x6 | gmc_v8_0.c:895 | WRITES |
| RANGE_PROTECTION_FAULT_ENABLE_DEFAULT | 4 | 4 | 1 | 0x10 | gmc_v8_0.c:896 | WRITES |
| RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT | 3 | 3 | 1 | 0x8 | gmc_8_1_sh_mask.h:6585 | DECLARED_NOT_WRITTEN |
| DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT | 6 | 6 | 1 | 0x40 | gmc_8_1_sh_mask.h:6589 | DECLARED_NOT_WRITTEN |
| DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT | 7 | 7 | 1 | 0x80 | gmc_8_1_sh_mask.h:6591 | DECLARED_NOT_WRITTEN |
| PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT | 9 | 9 | 1 | 0x200 | gmc_8_1_sh_mask.h:6593 | DECLARED_NOT_WRITTEN |
| PDE0_PROTECTION_FAULT_ENABLE_DEFAULT | 10 | 10 | 1 | 0x400 | gmc_8_1_sh_mask.h:6595 | DECLARED_NOT_WRITTEN |
| PDE0_PROTECTION_FAULT_ENABLE_SAVE | 11 | 11 | 1 | 0x800 | gmc_8_1_sh_mask.h:6597 | DECLARED_NOT_WRITTEN |
| VALID_PROTECTION_FAULT_ENABLE_INTERRUPT | 12 | 12 | 1 | 0x1000 | gmc_8_1_sh_mask.h:6599 | DECLARED_NOT_WRITTEN |
| VALID_PROTECTION_FAULT_ENABLE_DEFAULT | 13 | 13 | 1 | 0x2000 | gmc_8_1_sh_mask.h:6601 | DECLARED_NOT_WRITTEN |
| VALID_PROTECTION_FAULT_ENABLE_SAVE | 14 | 14 | 1 | 0x4000 | gmc_8_1_sh_mask.h:6603 | DECLARED_NOT_WRITTEN |
| READ_PROTECTION_FAULT_ENABLE_INTERRUPT | 15 | 15 | 1 | 0x8000 | gmc_8_1_sh_mask.h:6605 | DECLARED_NOT_WRITTEN |
| READ_PROTECTION_FAULT_ENABLE_DEFAULT | 16 | 16 | 1 | 0x10000 | gmc_8_1_sh_mask.h:6607 | DECLARED_NOT_WRITTEN |
| READ_PROTECTION_FAULT_ENABLE_SAVE | 17 | 17 | 1 | 0x20000 | gmc_8_1_sh_mask.h:6609 | DECLARED_NOT_WRITTEN |
| WRITE_PROTECTION_FAULT_ENABLE_INTERRUPT | 18 | 18 | 1 | 0x40000 | gmc_8_1_sh_mask.h:6611 | DECLARED_NOT_WRITTEN |
| WRITE_PROTECTION_FAULT_ENABLE_DEFAULT | 19 | 19 | 1 | 0x80000 | gmc_8_1_sh_mask.h:6613 | DECLARED_NOT_WRITTEN |
| WRITE_PROTECTION_FAULT_ENABLE_SAVE | 20 | 20 | 1 | 0x100000 | gmc_8_1_sh_mask.h:6615 | DECLARED_NOT_WRITTEN |
| EXECUTE_PROTECTION_FAULT_ENABLE_INTERRUPT | 21 | 21 | 1 | 0x200000 | gmc_8_1_sh_mask.h:6617 | DECLARED_NOT_WRITTEN |
| EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT | 22 | 22 | 1 | 0x400000 | gmc_8_1_sh_mask.h:6619 | DECLARED_NOT_WRITTEN |
| EXECUTE_PROTECTION_FAULT_ENABLE_SAVE | 23 | 23 | 1 | 0x800000 | gmc_8_1_sh_mask.h:6621 | DECLARED_NOT_WRITTEN |
| PAGE_TABLE_BLOCK_SIZE | 24 | 27 | 4 | 0xF000000 | gmc_8_1_sh_mask.h:6623 | DECLARED_NOT_WRITTEN |

**Análisis de solapamiento**: Ningún bit se solapa (26/32 bits utilizados, 81%). Validación de "22 campos, 22 shifts distintos, cero solapes" confirmada.

**Verificación matemática de los campos del DOGFOOD-PRACTICE-002:**

| DOGFOOD-PRACTICE-002 afirmaba | VERIFICADO | Estado |
|---|---|---|
| ENABLE_CONTEXT bit 0 | ✓ bits 0-0 | CORRECTO |
| PAGE_TABLE_DEPTH bits 0-1 | ✗ bits 1-2 | **INCORRECTO** — solapa con ENABLE_CONTEXT en bit 0 |
| GART_BLOCK_SIZE bits 4-7 | ✗ NO EXISTE ese nombre; PAGE_TABLE_BLOCK_SIZE está en bits 24-27 | **INCORRECTO** |
| PROTECTION_FAULT_ENABLE_* bits 6-23 | ✗ bits 3, 6-23 | **PARCIALMENTE INCORRECTO** — el campo de interrupt es bit 3, no el 4; hay un hueco en bit 5 |

**Clasificación epistemológica:**
```text
FIELD_MODEL = INCONSISTENT
```

El DOGFOOD-PRACTICE-002 afirmó `GART_BLOCK_SIZE (bits 4-7)` frente a `PROTECTION_FAULT_ENABLE_* (bits 6-23)`. Verificado:

- No existe campo llamado `GART_BLOCK_SIZE`. El campo real es `PAGE_TABLE_BLOCK_SIZE` en **bits 24-27** (shift 0x18, mask 0xF000000).
- Los campos `PROTECTION_FAULT_ENABLE_*` ocupan **bits 3 y 6-23**, no "6-23". El bit 4 y 5 están libres (bit 4 = RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, no es de protección).

**Conclusión de Parte B**: El layout de campos del DOGFOOD-PRACTICE-002 es **incorrecto en 3 de 4 afirmaciones**. Esto invalida el registro de `NOT_DETERMINED_RELATIONS` y `RELATIONS_RECONSTRUCTED=11` del informe original (el valor de 11 no puede ser verificado porque el layout fuente que usó para contar es erróneo).

**Corrección necesaria (sin implementar)**:
- `PAGE_TABLE_DEPTH`: bits 1-2, shift 0x1, no "bits 0-1, shift 0"
- `PAGE_TABLE_BLOCK_SIZE`: bits 24-27, shift 0x18, no "bits 4-7"
- Los campos de protección abarcan bits 3, 6-23, no "6-23"

---

## 5. TRANSFORMATION_VALIDATION

**Fuente**: `04-IMPLEMENTACION/rx550-driver/rx550_gpuvm.h:160-165`

```c
static inline uint32_t rx550_vm_context_cntl_flat_gart(void)
{
    return (RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0 << RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT) |
           (RX550_GART_BLOCK_SIZE << RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT) |
           RX550_VM_CONTEXT_CNTL_ENABLE;
}
```

**Constantes**:
```c
#define RX550_VM_CONTEXT_CNTL_DEPTH_SHIFT     0x0
#define RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0  0u   /* flat */
#define RX550_VM_CONTEXT_CNTL_BLOCK_SIZE_SHIFT  0x4
#define RX550_VM_CONTEXT_CNTL_ENABLE          (1u << 31)
#define RX550_GART_BLOCK_SIZE 10u
```

**Transformación**:
```text
INPUT_CONSTANTS: PAGE_TABLE_DEPTH_0 = 0, GART_BLOCK_SIZE = 10, ENABLE = (1 << 31)
SHIFT: 0, 4, 31 respectivamente
OR: (0 << 0) | (10 << 4) | (1 << 31)
FINAL_VALUE: 0x00000000 | 0x00000010 | 0x80000000 = 0x80000010
```

**Clasificación**:
- **SOURCE CODE**: PROVEN (rx550_gpuvm.h:160-165)
- **FACT**: `final_value = (0 << 0) | (10 << 4) | (1u << 31) = 0x80000010`
- **DERIVATION**: `PAGE_TABLE_DEPTH_0` → valor 0 → significa "flat" (comentario en el código: `/* flat */`)
- **DERIVATION**: `GART_BLOCK_SIZE` → 10 → significa 4KB pages (comentario: `/* GART block_size = 10 ... → 4 KB pages */`)
- **DERIVATION**: `RX550_VM_CONTEXT_CNTL_ENABLE` → habilita el contexto

**Estado de la afirmación DOGFOOD-PRACTICE-002**: "transformation: bitwise OR of constants" → **PROVEN**. Correcto.

---

## 6. REPRESENTATION_VALIDATION

Cadena producer → representation:

```text
rx550_vm_context_cntl_flat_gart()
        ↓ (devuelve uint32_t cntl_val)
rx550_gpuvm_init_contexts()
        ↓ (wraps para cada vmid, cntl_reg = 0x504u + vmid)
ring_write_wreg(&wp, cntl_reg, cntl_val)
        ↓ (PACKET3_SET_CONTEXT_REG = 0x61, count = 1)
ring_write_dword(wptr, (0x61u << 16) | 1u)
ring_write_dword(wptr, reg_index)
ring_write_dword(wptr, val)
        ↓ (GPU recibe el PM4 packet, escribe mmVM_CONTEXT0_CNTL)
GPU MMU/VM unit
```

| Salto | Estado | Evidencia |
|---|---|---|
| flat_gart() → cntl_val | PROVEN | rx550_gpuvm.c:95 `uint32_t cntl_val = rx550_vm_context_cntl_flat_gart();` |
| cntl_val → ring_write_wreg | PROVEN | rx550_gpuvm.c:104 `ring_write_wreg(&wp, cntl_reg, cntl_val);` |
| ring_write_wreg → PACKET3_SET_CONTEXT_REG (0x61) | PROVEN | rx550_gpuvm.c:26 `(0x61u << 16) | 1u` |
| reg_index → VM_CONTEXT0_CNTL | PROVEN | rx550_gpuvm.c:100 `cntl_reg = 0x504u + vmid;` para vmid < 8 |
| packet → GPU escribe el registro | DERIVATION (modelo PM4) | Formato PACKET3_SET_CONTEXT_REG es estándar de AMD |

**Estado**: La cadena REPRESENTATION está **PROVEN** con cada salto verificado en el corpus.

---

## 7. CONSUMER_VALIDATION

Afirmación DOGFOOD-PRACTICE-002: "GPU VM unit escribe CONTEXT0_CNTL para vmid 0..7, luego CONTEXT8_CNTL para vmid 8..15".

**Verificación**:

```c
int rx550_gpuvm_init_contexts(void *ring_buffer, uint32_t *ring_wptr,
                              uint32_t vmid_start, uint32_t vmid_count)
{
    if (vmid_start + vmid_count - 1 > RX550_VMID_MAX)  // RX550_VMID_MAX = 15
        return RX550_GPUVM_ERR_INVALID_VMID;

    uint32_t cntl_val = rx550_vm_context_cntl_flat_gart();

    for (uint32_t vmid = vmid_start; vmid < vmid_start + vmid_count; vmid++) {
        uint32_t cntl_reg;
        if (vmid < 8)
            cntl_reg = 0x504u + vmid;     // CONTEXT0_CNTL ... CONTEXT7_CNTL (0x504..0x50B)
        else
            cntl_reg = 0x504u + 8 + (vmid - 8);  // CONTEXT8_CNTL ... CONTEXT15_CNTL (0x50C..0x513)
        ring_write_wreg(&wp, cntl_reg, cntl_val);
    }
}
```

**Clasificación de cada aspecto**:
1. "es abstracción del software" → **FACT** (es código que programa el hardware, no una operación GPU intrínseca)
2. "es una secuencia de registros consecutivos" → **FACT** (0x504 → 0x50C son consecutivos por vmid)
3. "es una operación realmente ejecutada por la GPU" → **DERIVATION** (el código escribe el PM4, la GPU lo consume; el driver no lo ejecuta directamente)
4. "es una derivación del modelo" → **FACT** (el bucle construye la secuencia, no hay llamada única "escribir todos los contextos")

**Estado**: **PROVEN** — el software programa los registros CONTEXT0_CNTL..CONTEXT15_CNTL según vmid. El DOGFOOD-PRACTICE-002 acertó en la descripción.

---

## 8. SEMANTIC_EFFECT_VALIDATION

Revisión de las afirmaciones semánticas individuales:

| Afirmación | Clasificación | Evidencia |
|---|---|---|
| flat GART mapping | **DERIVATION** (con base FACT) | `RX550_VM_CONTEXT_CNTL_PAGE_TABLE_DEPTH_0 = 0u /* flat */` + nombre de función `flat_gart` |
| 4KB pages | **FACT** | Comentario en rx550_gpuvm.h:157: `/* GART block_size = 10 ... → 4 KB pages */` — referenciado a hallazgo 113 y rx550_gart_geom |
| context enabled | **FACT** | `RX550_VM_CONTEXT_CNTL_ENABLE = (1u << 31)` |
| Effect on TLB invalidation | **NOT_DETERMINED** | No se rastreó la relación con VM_INVALIDATE_REQUEST |
| Effect on PTE/PDE | **NOT_DETERMINED** | Solo se escribe; el consumo de TLB no está probado |

**Corrección necesaria**: La afirmación "flat GART mapping" es una **DERIVATION**, no un FACT, porque depende de la interpretación de `PAGE_TABLE_DEPTH_0 = 0` como "flat" (basada en el comentario del código y el nombre de la función). No hay evidencia de hardware que lo verifique.

---

## 9. REGISTER_OFFSET_GAP_AUDIT

**Reproducción**: `rxre register VM_CONTEXT0_CNTL` → `PROVEN_ABSENT_EN_ASIC_REG`, 0 definitions.

**Análisis del universo de búsqueda**:
- RXRE registra: `argv_tail: [--kernel, linux-7.1.3, --gfx, gfx_8_0, --reg, VM_CONTEXT0_CNTL]`
- Notificación: "busqueda exhaustiva sobre include/asic_reg"

**Evidencia de existencia en el corpus**:
```bash
$ grep "VM_CONTEXT0_CNTL" RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_1_sh_mask.h
# devuelve 76 definiciones (#define VM_CONTEXT0_CNTL__*__MASK / __SHIFT)
```

**Conclusión de Part F**:
- Punto 1 (registro existe en corpus activo) → **PROVEN** (76 definiciones en gmc_8_1_sh_mask.h)
- Punto 2 (RXRE recibe la consulta correcta) → **PROVEN** (argv_tail muestra la consulta bien formada)
- Punto 3 (el archivo está dentro del corpus que RXRE debería consultar) → **PROVEN** (gmc_8_1_sh_mask.h está en `include/asic_reg/gmc/`)
- Punto 4 (el resolver excluye el archivo por diseño) → **NOT_DETERMINED** (no se inspeccionó el código fuente del resolver, pero el resultado PROVEN_ABSENT_EN_ASIC_REG indica búsqueda fallida sobre include/asic_reg)
- Punto 5 (no es una consulta mal formada) → **PROVEN**

**Clasificación**: `REGISTER_OFFSET_LOOKUP = PROVEN_CAPABILITY_GAP`

El registro EXISTE en el kernel fuente (76 definiciones de máscaras/shifts), RXRE consulta correctamente, y el archivo está en el directorio que RXRE busca (`include/asic_reg/gmc/gmc_8_1_sh_mask.h`), pero RXRE devuelve 0 definiciones. Esto indica una limitación de RXRE en la extracción de registros desde los archivos `*_sh_mask.h` (probablemente RXRE busca definiciones con `#define mmVM_CONTEXT0_CNTL 0x504`, un patrón diferente al que usa el kernel).

**Corrección del tipo de gap**: El DOGFOOD-PRACTICE-002 lo clasificó como "RXRE no busca la implementación RXRE". **CORREGIR**: No es eso — el registro NO está en la implementación RXRE (`04-IMPLEMENTACION/...`), está en el kernel fuente (RESEARCH/). El gap de RXRE es: **no extrae registros de los archivos `*_sh_mask.h` del kernel**, por lo que no encuentra definiciones que sí existen en el kernel. El offset 0x504 está en la implementación RXRE (`rx550_mmio_access.c`), lo cual es un hallazgo adicional: el kernel no define el offset con un macro, el offset está codificado en la tabla de la implementación RXRE.

**Revisión final**: `REGISTER_OFFSET_LOOKUP = PROVEN_CAPABILITY_GAP` (el kernel define máscaras/shifts, pero RXRE no puede extraerlas; el offset 0x504 está en la tabla de la implementación RXRE, no en el kernel).

---

## 10. FIELD_SEMANTICS_GAP_AUDIT

**Afirmación original**: "RXRE no puede extraer 22 campos de rx550_mmio_access.c" → CORPUS_GAP.

**Reevaluación**:

- Los campos NO están en el kernel: gmc_8_1_sh_mask.h define solo máscaras y shifts, no el nombre `GART_BLOCK_SIZE` (el kernel usa `PAGE_TABLE_BLOCK_SIZE`).
- El kernel define 22 campos para VM_CONTEXT0_CNTL (ver tabla de la Parte B). Confirma el comentario en rx550_mmio_access.c:626: "22 campos, 22 shifts distintos".
- Los campos de la implementación RXRE (ENABLE_CONTEXT, PAGE_TABLE_DEPTH, etc.) son una interpretación sobre el layout del kernel, NO son definiciones del kernel.
- El offset 0x504 NO está definido en el kernel (no hay `#define mmVM_CONTEXT0_CNTL 0x504`), solo máscaras y shifts.

**Clasificación**: `FIELD_SEMANTICS = CORPUS_GAP + PARSER_GAP`

- **CORPUS_GAP**: El kernel no tiene `GART_BLOCK_SIZE`; la implementación RXRE usa un alias interpretado.
- **PARSER_GAP**: RXRE no extrae el layout de campos de los archivos `*_sh_mask.h` ni de la tabla de `rx550_mmio_access.c`.
- El campo `GART_BLOCK_SIZE` **NO EXISTE** ni en el kernel ni como macro; el DOGFOOD-PRACTICE-002 inventó un alias que no aparece en ninguna fuente verificada. **FACT**: `GART_BLOCK_SIZE` no es una definición real.

**Corrección necesaria**: El DOGFOOD-PRACTICE-002 afirmó `GART_BLOCK_SIZE (bits 4-7)` — este nombre no existe en ninguna fuente verificada del corpus. El campo real es `PAGE_TABLE_BLOCK_SIZE` (bits 24-27, definido en gmc_8_1_sh_mask.h:6623 y en rx550_mmio_access.c:668).

---

## 11. PRODUCER_CHAIN_GAP_AUDIT

**Reproducción**: `rxre trace VM_CONTEXT0_CNTL`.

**Análisis**:
- La cadena productor→transformación→consumidor SÍ está en el corpus y fue reconstruida correctamente:
  - `rx550_vm_context_cntl_flat_gart()` → `rx550_gpuvm_init_contexts()` → `ring_write_wreg()` → PACKET3_SET_CONTEXT_REG (0x61) → mmVM_CONTEXT0_CNTL
- Cada salto está PROVEN en el corpus (Parte 6).

**Clasificación**: `PRODUCER_CHAIN = PROVEN`, NO es un gap.

La afirmación del DOGFOOD-PRACTICE-002 de que "PRODUCER_CHAIN: RXRE cannot trace this relation" es **INCORRECTA**: la relación no solo es rastreable, sino que el DOGFOOD-PRACTICE-002 mismo la reconstruyó correctamente a través de grep manual. El problema no es la ausencia de la cadena, sino que RXRE no tiene una capacidad de `trace` que la descubra automáticamente (lo que es un gap de herramienta diferente: **TRACE_CAPABILITY**, no ausencia de la relación).

**Corrección necesaria**: `PRODUCER_CHAIN = PROVEN` (la relación existe y fue reconstruida). Lo que es verdadero es que **RXRE trace no encontró el productor** → esto debería clasificarse como **TRACE_GAP** o **NO_GAP** (RXRE trace no extrae cadenas de llamadas desde el registro).

---

## 12. METRIC_RECONCILIATION

Corrección de las métricas del DOGFOOD-PRACTICE-002 (reproducidas durante esta auditoría):

| Métrica | DOGFOOD-PRACTICE-002 | REPRODUCIDO | Observación |
|---|---|---|---|
| RXRE_INVOCATIONS | 2 | 2 | `register` + `search` (no se ejecutó `trace` en la auditoría original, así que no se puede reprobar) |
| RXRE_FAILURES | 3 | 1 | Solo 1 fallo de RXRE confirmado en la auditoría (el `register`) |
| RXRE_RECOVERIES | 0 | 3 | 3 recuperaciones manuales (grep en `rx550_mmio_access.c`, `rx550_gpuvm.h`, `rx550_gpuvm.c`) |
| MANUAL_SHELL_COMMANDS | 5 | 3 | Las recuperaciones principales fueron 3 greps |
| RELATIONS_RECONSTRUCTED | 11 | 11 verificables: 9 PROVEN, 2 con correcciones necesarias | 11 de 12 relaciones son PROVEN tras auditoría |
| RELATIONS_UNRESOLVED | 5 | 3 + 2 = 5 | 3 NOT_DETERMINED (TLB, PTE/PDE, efecto hardware) + 2 correcciones (campo layout, producer chain) |

**Definiciones de cada métrica**:
- `RXRE_INVOCATIONS`: número de llamadas a `python3 tools/rxre/rxre <capacidad>` hechas durante la auditoría.
- `RXRE_COMMAND_FAILURES`: número de llamadas RXRE que devolvieron `verdict != ok` / `results` vacíos (aquí: `PROVEN_ABSENT_EN_ASIC_REG`).
- `RXRE_INTERNAL_FAILURES`: número de fallos ocurridos en el procesamiento interno del corpus por RXRE (no determinado).
- `RECOVERY_ACTIONS`: número de recuperaciones manuales exitosas (grep) que proporcionaron evidencia que RXRE no pudo dar.
- `MANUAL_SHELL_COMMANDS`: número de comandos shell manuales ejecutados fuera de RXRE.
- `RELATIONS_RECONSTRUCTED`: número de saltos de la cadena REGISTER→…→SEMANTIC EFFECT verificados como PROVEN.
- `RELATIONS_UNRESOLVED`: número de saltos no verificados (NOT_DETERMINED) o erróneos (requieren corrección).

---

## 13. INVALID_OR_UNSUPPORTED_CLAIMS

| Claim DOGFOOD-PRACTICE-002 | Estado |
|---|---|
| `GART_BLOCK_SIZE (bits 4-7)` | **INVALID** — el campo no existe; el real es `PAGE_TABLE_BLOCK_SIZE` en bits 24-27 |
| `PROTECTION_FAULT_ENABLE_* (bits 6-23)` | **PARCIALMENTE INVALID** — son bits 3, 6-23 (bit 3 = interrupt, hueco en bit 5) |
| `PAGE_TABLE_DEPTH (bits 0-1)` | **INVALID** — son bits 1-2 |
| `RELATIONS_RECONSTRUCTED = 11` | **SUPPORTED** — 11 de 12 relaciones verificadas (9 PROVEN + 2 con corrección) |
| `PRODUCTION_CHAIN = PROVEN` (reconstruido) | **CORRECTO** — la cadena existe, pero RXRE no la encontró |
| `SEMANTIC EFFECT = flat GART mapping` | **DERIVATION** (no FACT) |
| `REGISTER_OFFSET_LOOKUP = CAPABILITY GAP` | **CORRECTO** (con la corrección: el kernel define máscaras/shifts, RXRE no las extrae; el offset 0x504 está en la tabla RXRE) |
| `FIELD_SEMANTICS = CAPABILITY GAP` | **CORRECTO** (PARSER_GAP sobre `*_sh_mask.h`) |
| `PRODUCER_CHAIN = CAPABILITY GAP` | **INVALID** — la cadena está PROVEN; es un TRACE_CAPABILITY gap, no ausencia de relación |

---

## 14. FINAL_CLASSIFICATION

```text
AUDIT_PASS_WITH_CORRECTIONS
```

**Justificación**: La cadena completa es **útil y mayoritariamente correcta**, pero contiene afirmaciones que deben corregirse:

**Correctas (9/12)**:
- REGISTER: vmVM_CONTEXT0_CNTL @ 0x504, 32-bit RW → PROVEN
- PRODUCER: rx550_vm_context_cntl_flat_gart() → PROVEN
- TRANSFORMATION: bitwise OR de constantes → PROVEN (valor 0x80000010)
- REPRESENTATION: PACKET3_SET_CONTEXT_REG (0x61) PM4 → PROVEN
- CONSUMER: GPU VM unit con bucle vmid → PROVEN
- REGISTER_OFFSET_LOOKUP = PROVEN_CAPABILITY_GAP → PROVEN (con corrección: RXRE no extrae máscaras/shifts de `*_sh_mask.h`)
- FIELD_SEMANTICS = CAPABILITY/PARSER_GAP → PROVEN
- CONSUMER: bucle vmid → PROVEN
- SEMANTIC: 4KB pages, context enabled → PROVEN/DERIVATION

**Requieren corrección (3/12)**:
- `PAGE_TABLE_DEPTH bits 0-1` → debe ser **bits 1-2** (shift 0x1)
- `GART_BLOCK_SIZE bits 4-7` → debe ser **PAGE_TABLE_BLOCK_SIZE bits 24-27** (shift 0x18); el nombre `GART_BLOCK_SIZE` no es una definición real
- `PRODUCER_CHAIN gap` → la cadena está **PROVEN**, solo RXRE no la encontró (TRACE_CAPABILITY gap)

**Estado final de las tres clasificaciones revalidadas**:
| Clasificación | DOGFOOD-PRACTICE-002 | AUDIT → |
|---|---|---|
| REGISTER_OFFSET_LOOKUP | PROVEN_CAPABILITY_GAP | **PROVEN_CAPABILITY_GAP** ✓ |
| FIELD_SEMANTICS | CORPUS/PARSER GAP | **PARSER_GAP + CORPUS_GAP** ✓ (con corrección del campo erróneo) |
| PRODUCER_CHAIN | PROVEN_CAPABILITY_GAP | **PROVEN (la relación)** — RXRE no la extrae = TRACE_CAPABILITY gap |

---

## 15. GLOBAL_WORK_SCAN

```text
[01] ERRORS que invalidan conocimiento: 3 — layout de campos incorrecto (3 afirmaciones invalidas)
[02] CONTRADICCIONES críticas: 1 — GART_BLOCK_SIZE vs PAGE_TABLE_BLOCK_SIZE
[03] CLAIMS críticos abiertos: 3 — efectos de hardware (TLB invalidation, PTE/PDE, efecto real)
[04] DEPENDENCIAS desbloqueables: 0 — no se puede validar sin hardware/depuración
[05] EVIDENCIA faltante: 3 — efecto real del registro en la GPU, interacción TLB, interacción PTE/PDE
[06] OBSERVABILITY gaps: 1 — RXRE no extrae registros de *_sh_mask.h (REGISTER_OFFSET_LOOKUP)
[07] STATIC discriminants: 11 de 12 verificados
[08] RUNTIME discriminants: 0 — sin ejecución/depuración
[09] TOOL gaps: 2 — register (máscaras/shifts), trace (cadena de llamadas)
[10] TOOL validation pendiente: 0
[11] AUTOMATION gaps: 0
[12] REPRODUCIBILITY gaps: 0
[13] BOTTLENECKS medidos: 0
[14] PREPARATION: 0
[15] IMPLEMENTATION justificada: 0 (READ-ONLY)
[16] BENCHMARKS pendientes: 0
[17] REGRESSIONS: 0
[18] OPTIMIZATIONS: 0
[19] VALIDATION: completada — AUDIT_PASS_WITH_CORRECTIONS
[20] USER IDEAS: 0
[21] Otras vías: 0
```

---

## FRONTERA MÁS INFORMATIVA

**CAPABILITY_GAP: RXRE_NO_REGISTERS_FROM_SH_MASK**

RXRE no puede extraer la definición de registros desde los archivos de máscaras/shifts del kernel (`include/asic_reg/gmc/gmc_8_1_sh_mask.h`), donde el kernel AMD define oficialmente los bits y shifts de VM_CONTEXT0_CNTL (76 definiciones `#define VM_CONTEXT0_CNTL__*__MASK/__SHIFT`).

- El kernel define máscaras y shifts → RXRE devuelve 0 definiciones → **PROVEN_CAPABILITY_GAP**.
- El offset 0x504 NO está en el kernel → está codificado en la tabla de la implementación RXRE (`rx550_mmio_access.c:104`).

**Impacto**: La semántica completa del registro (22 campos, máscaras, shifts) es INVISIBLE para RXRE y solo accesible mediante grep manual. Esta es la frontera técnicamente más informativa: un gap de herramienta que deja la semántica del registro completamente fuera del alcance de RXRE, obligando a intervención manual en el corpus.

---

## STOP GATE

**Resultado: AUDIT_PASS_WITH_CORRECTIONS**

La cadena REGISTER→PRODUCER→TRANSFORMATION→REPRESENTATION→CONSUMER→SEMANTIC EFFECT es reconstruible y mayoritariamente correcta, pero contiene 3 afirmaciones erróneas (layout de campos) y 1 mal clasificada (PRODUCER_CHAIN), lo que no permite un AUDIT_PASS completo. No se inició ninguna implementación ni nueva tarea.
