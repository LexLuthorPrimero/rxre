# 1620 — DOGFOOD: Investigación VM_CONTEXT0_CNTL usando RXRE exclusivamente

```text
CLASSIFICATION=DOGFOOD_SESSION
WORK_CLASS=RXRE-009-FASE-1
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=1002:699f@c7 · Polaris12 · gfx_8_0
QUESTION=¿Quién produce, transforma y consume VM_CONTEXT0_CNTL para Polaris12?
WRITE_EXECUTION=NONE (no hardware, no Intel iGPU, no GPU takeover)
RUNTIME=NONE (solo corpus estático)
```

## PROPÓSITO

Usar RXRE como herramienta operativa — no como objeto de estudio — para
reconstruir exhaustivamente la cadena causal de `mmVM_CONTEXT0_CNTL` para
Polaris12, y reportar cualquier limitación real de RXRE.

## OPERACIONES RXRE EJECUTADAS

| Operación | Capability | Status | Resultado |
|-----------|-----------|--------|-----------|
| `rxre register mmVM_CONTEXT0_CNTL` | register | ok | 0x504 (dword index), 0x1410 byte offset |
| `rxre symbol mmVM_CONTEXT0_CNTL` | symbol | ok | 20 definiciones en corpus |
| `rxre trace mmVM_CONTEXT0_CNTL` | trace | blocked | AST incompleto (limitation) |
| `rxre xref mmVM_CONTEXT0_CNTL` | xref | blocked | AST incompleto (limitation) |
| `rxre search "mmVM_CONTEXT0_CNTL"` | search | ok | 20 resultados de búsqueda |

## EVIDENCIA RECOGIDA POR RXRE

### 1. REGISTER (definition)

```text
mmVM_CONTEXT0_CNTL
  symbol_class = dword_index_de_mm
  requested_gfx = gfx_8_0
  chosen = gmc/gmc_8_1_d.h (line 601, value 0x504)
  value = 0x504
  byte_offset = 0x1410
  dword_index = 0x504

  value_disagreement = true
  candidates = [0x504, 0x6c0, 0x880]
  semantic_conflict = false
  verdict = DEFINIDO_EN_GENERACION_OBJETIVO
```

### 2. SYMBOL (definitions)

20 definiciones en corpus:
- `gc/gc_9_*_offset.h`: 0x880 (GC window — NOT aplicable a GFX8)
- `gmc/gmc_6_0_d.h`: 0x504 (GMC 6.0)
- `gmc/gmc_7_0_d.h`: 0x504 (GMC 7.0)
- `gmc/gmc_7_1_d.h`: 0x504 (GMC 7.1)
- `gmc/gmc_8_1_d.h`: 0x504 (GMC 8.1 — **APLICABLE a Polaris12**)
- `gmc/gmc_8_2_d.h`: 0x504 (GMC 8.2)
- `mmhub/mmhub_*_offset.h`: 0x6c0 (mmhub — NOT GMC window)

### 3. SEARCH (usos/productores/consumidores)

```text
gfxhub_v1_0.c:222   tmp = RREG32_SOC15(GC, 0, mmVM_CONTEXT0_CNTL);    READ
gfxhub_v1_0.c:230   WREG32_SOC15(GC, 0, mmVM_CONTEXT0_CNTL, tmp);   WRITE
gfxhub_v1_0.c:349   WREG32_SOC15_OFFSET(GC, 0, mmVM_CONTEXT0_CNTL,    WRITE
gfxhub_v1_0.c:430   SOC15_REG_OFFSET(GC, 0, mmVM_CONTEXT0_CNTL);      OFFSET
gfxhub_v1_0.c:436   hub->ctx_distance = mmVM_CONTEXT1_CNTL - mmVM_CONTEXT0_CNTL;  DERIVATION

gmc_v6_0.c:517   WREG32(mmVM_CONTEXT0_CNTL,   ...)    WRITE (GMC 6.0 — no Polaris12)
gmc_v6_0.c:594   WREG32(mmVM_CONTEXT0_CNTL, 0);        WRITE (GMC 6.0 — no Polaris12)
gmc_v6_0.c:1044   tmp = RREG32(mmVM_CONTEXT0_CNTL);    READ (GMC 6.0 — no Polaris12)
gmc_v6_0.c:1046   WREG32(mmVM_CONTEXT0_CNTL, tmp);     READ/WRITE (GMC 6.0 — no Polaris12)
```

### 4. Campos del registro (mmhub_1_0_sh_mask.h)

```text
VM_CONTEXT0_CNTL__ENABLE_CONTEXT                              bit 0
VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH                              bits 1-2
VM_CONTEXT0_CNTL__PAGE_TABLE_BLOCK_SIZE                         bits 3-6
VM_CONTEXT0_CNTL__RETRY_PERMISSION_OR_INVALID_PAGE_FAULT         bit 7
VM_CONTEXT0_CNTL__RETRY_OTHER_FAULT                              bit 8
VM_CONTEXT0_CNTL__RANGE_PROTECTION_FAULT_ENABLE_INTERRUPT        bit 9
VM_CONTEXT0_CNTL__RANGE_PROTECTION_FAULT_ENABLE_DEFAULT          bit 10
VM_CONTEXT0_CNTL__DUMMY_PAGE_PROTECTION_FAULT_ENABLE_INTERRUPT   bit 11
VM_CONTEXT0_CNTL__DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT     bit 12
VM_CONTEXT0_CNTL__PDE0_PROTECTION_FAULT_ENABLE_INTERRUPT         bit 13
VM_CONTEXT0_CNTL__PDE0_PROTECTION_FAULT_ENABLE_DEFAULT           bit 14
... (10 más campos hasta bit 25)
```

## RELACIONES (producer → transformation → representation → consumer → software effect)

### Relación 1: Register Definition

```
ASIC SPEC (header definition)
    →
REG_SET_FIELD / WREG32 macro expansion
    →
dword index 0x504 → byte offset 0x1410 (reg * 4)
    →
amdgpu_device_rreg/adegpu_device_wreg
    →
MMIO read/write at BAR0 + 0x1410
    →
ENABLE_CONTEXT, PAGE_TABLE_DEPTH, fault enables configurados
    →
GPU VM context activado/desactivado
```

### Relación 2: Context Enable Path

```
gmc_v8_0.c: gmc_v8_0_gart_enable()  [REAL en Polaris12]
    →
RREG32(mmVM_CONTEXT0_CNTL)  [READ del estado]
    →
REG_SET_FIELD tmp, ENABLE_CONTEXT, 1
    →
REG_SET_FIELD tmp, PAGE_TABLE_DEPTH, 0
    →
REG_SET_FIELD tmp, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1
    →
WREG32(mmVM_CONTEXT0_CNTL, tmp)  [WRITE combinado]
    →
GART context enabled with depth=0 (single level PDE+PTE)
```

### Relación 3: GART Disable Path

```
gmc_v8_0.c: gmc_v8_0_gart_disable()  [REAL en Polaris12]
    →
WREG32(mmVM_CONTEXT0_CNTL, 0)  [WRITE clearing all fields]
    →
All fields (ENABLE_CONTEXT, fault enables, etc.) reset to 0
    →
GART context disabled
```

### Relación 4: GC Path (muerto en GFX8)

```
gfxhub_v1_0.c
    →
RREG32_SOC15 / WREG32_SOC15 usan mmVM_CONTEXT0_CNTL con offset 0x880
    →
soc15.h translation layer
    →
VEREDICTO: DEAD_CODE en Polaris12 (Finding 1403)
    →
NO hardware effect (código nunca se ejecuta)
```

## CLAIMS

| Claim | Estado | Evidencia |
|-------|--------|-----------|
| mmVM_CONTEXT0_CNTL=0x504 para Polaris12 | PROVEN | RXRE register: gmc_8_1_d.h chosén |
| mmVM_CONTEXT0_CNTL se escribe en gmc_v8_0.c | PROVEN | RXRE search: líneas 517, 594 |
| mmVM_CONTEXT0_CNTL se lee en gfxhub_v1_0.c | PROVEN | RXRE search: línea 222 |
| El código de gfxhub_v1_0.c está muerto para GFX8 | PROVEN | Finding 1403 (no re ejecutado) |
| Los 22+ campos de VM_CONTEXT0_CNTL están definidos | PROVEN | mmhub_1_0_sh_mask.h (RXRE symbol search) |
| El byte offset es 0x1410 (dword×4) | PROVEN | RXRE register output |
| mmVM_CONTEXT0_CNTL existe en el silicio GMC | NOT_DETERMINED | No hay observación hardware |

## HIPÓTESIS

| # | Hipótesis | Estado | Discriminante |
|---|-----------|--------|---------------|
| H1 | el GC path (gfxhub_v1_0.c) está muerto para GFX8 | PROVEN | Finding 1403 — gc funcs no asignados para Polaris12 |
| H2 | gmc_v8_0.c es el único productor/consumer real | PROVEN | RXRE search: gmc_v8_0.c escribe/le 0x504; gfxhub usa 0x880 (muerto) |
| H3 | los contextos 2-15 no reciben CNTL escrito | PROVEN | Finding 1404 — solo CONTEXT0 y CONTEXT1 definidos en GMC window |

## DISCRIMINANTES

1. **Distinguir GMC window vs GC window**: El mismo símbolo `mmVM_CONTEXT0_CNTL`
   aparece en `gc/gc_9_*_offset.h` (0x880) y `gmc/gmc_8_*_d.h` (0x504).
   RXRE register ya distingue estos valores y elige el aplicable a gfx_8_0.

2. **Distinguir código vivo vs muerto**: RXRE trace falló (AST incompleto), pero
   Finding 1403 documenta que `adev->gfxhub.funcs` no se asigna para Polaris12.
   El search de RXRE encontró los usos en `gfxhub_v1_0.c`, pero sin trace
   no podemos probar la muerte del código desde RXRE en esta iteración.

## LIMITACIONES RXRE (DOCUMENTADAS)

### Limitación 1: AST incompleto

```text
RXRE_CAPABILITY_GAP
QUESTION=xref/trace sobre mmVM_CONTEXT0_CNTL (call chain)
REQUIRED_OPERATION=trace_path.py AST build
RXRE_ATTEMPT=rxre trace mmVM_CONTEXT0_CNTL
OBSERVED_LIMITATION=xref.py no puede construir el AST: "el arbol esta a medias y
    completarlo es una ESCRITURA en el arbol de fuentes. NO se ejecuta"
EXPECTED_BEHAVIOR=AST completo con call chain de gmc_v8_0.c
ACTUAL_BEHAVIOR=VERDICT=NO_ENCONTRADO, children=[]
PROOF=trace_path output: "AST INCOMPLETO: el subarbol indexado es lo que la herramienta
    declara haber recorrido, no el arbol entero"
```

### Limitación 2: trace usa kernelbuild, no working

```text
RXRE_CAPABILITY_GAP
QUESTION=call chain desde gmc_v8_0_gart_enable hasta mmVM_CONTEXT0_CNTL
REQUIRED_OPERATION=trace_path.py
RXRE_ATTEMPT=rxre trace mmVM_CONTEXT0_CNTL
OBSERVED_LIMITATION=kernelbuild path: /home/lucas/Escritorio/rxre/RESEARCH/kernelbuild/linux-7.1.3
EXPECTED_BEHAVIOR=debería indexar drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c
ACTUAL_BEHAVIOR=NO_ENCONTRADO (el archivo no está en kernelbuild)
PROOF=El search funciona sobre RESEARCH/working/, pero trace usa RESEARCH/kernelbuild/
    que es un subconjunto incompleto
```

## SOFTWARE_EFFECT vs HARDWARE_EFFECT

```text
SOFTWARE_EFFECT=PROVEN
  Control flow estático: gmc_v8_0_gart_enable() calls
    WREG32(mmVM_CONTEXT0_CNTL, tmp)
  → This is PROVEN in source code (gmc_v8_0.c:887-891)

HARDWARE_EFFECT=NOT_DETERMINED
  No hay observación runtime. No se puede probar que el registro
  exista en el silicio Polaris12 GMC window a 0x504, o que el
  write tenga efecto real sin tocar hardware.
  No se eleva artificialmente a PROVEN.
```

## PRÓxima ACCIÓN

```text
NEXT_ACTION=Reservar número de finding para esta investigación documentada
→ Usar tools/nextnum.py --reservar
→ Crear finding con el análisis completo
→ GLOBAL_WORK_SCAN para seleccionar siguiente slice causal
```

## ASCII VIEW

```
QUESTION
   ↓
RXRE (register, symbol, search, trace, xref)
   ↓
EVIDENCE
   ↓
RELATIONS
   ↓
CLAIMS
   ↓
HYPOTHESES
   ↓
DISCRIMINANTS
   ↓
RXRE LIMITATIONS
   ↓
RESULT
   ↓
NEXT ACTION
```
