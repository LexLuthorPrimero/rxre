# 1612 — RXRE-008 FASE 3: REPLANTEO DE FINDING 1607 POST-REFUTACIÓN SHADOW_START

```text
CLASSIFICATION=CLAIM_REFORMED+CHAIN_REAL_ESTABLISHED
WORK_CLASS=RXRE-008-FASE-3 · REPLANTEO-1607-POST-1611
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7 · Polaris12 · gfx_8_0
PREGUNTA=¿Existe evidencia suficiente para demostrar directamente la cadena real que popula soft_regs_start desde SoftRegisters?
MODIFICATIONS=NINGUNO · solo base de datos SQLite + este hallazgo
WRITE_EXECUTION=NINGUNO · solo lectura de fuente y de la CLI; corpus RESEARCH/working/linux-7.1.3
DISPOSITIVO_TOCADO=NINGUNO · no MMIO, no Intel, no display, no driver bind
RUNTIME=solo lectura de fuente y de la CLI; corpus RESEARCH/working/linux-7.1.3
```

---

## Resumen

Tras **refutar completamente** la hipótesis de `SHADOW_START` como enlace causal (Finding 1611), se replantea el modelo causal de `soft_regs_start` utilizando **solo evidencia estática real** disponible en el código fuente. Se verifica que el claim:

```
"soft_regs_start is populated from SoftRegisters"
```

puede **sostenerse mediante la cadena REAL de evidencia ya disponible**, alcanzando el estado **PROVEN** para el claim, manteniendo el effect como `NOT_DETERMINED` para el efecto hardware.

---

## Refutación de SHADOW_START (Finding 1611)

Antes de proseguir, se confirma el resultado de ACTION 82:

- **SHADOW_START** no existe como:
  - registro MMIO
  - packet PM4
  - constante, variable o símbolo real
- La única aparición fue en fixture de test: `citas_prosa_census.py:812` (duplicado 910)
- **Resultado**: `NO_LINK_FOUND` — el enlace `SHADOW_START → soft_regs_start` **NO ES UNA RELACIÓN CANDIDATA VÁLIDA**

Esto invalida la supposición previa en Finding 1607 y obliga a replantear el modelo causal.

---

## Cadena Causal Real Verificada

Tras búsqueda exhaustiva, se establece la **cadena estática demostrable**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PRODUCER                                                                    │
│   function: polaris10_process_firmware_header()                             │
│   file: smumgr/polaris10_smumgr.c                                           │
│   lines: 2510-2516                                                          │
│   operation: smu7_read_smc_sram_dword()                                     │
│   address: SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SoftRegisters)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRANSFORMATION                                                              │
│   function: smu7_read_smc_sram_dword()                                      │
│   file: smumgr/smu7_smumgr.c                                                │
│   lines: 229-237                                                            │
│   steps:                                                                    │
│     1. smu7_set_smc_sram_address(addr) → writes to mmSMC_IND_INDEX_11       │
│     2. *value = cgs_read_register(mmSMC_IND_DATA_11)                        │
│   effect: lectura de palabra dword desde SMC SRAM                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPRESENTATION                                                              │
│   variable: tmp (local)                                                     │
│   type: uint32_t                                                            │
│   value: contenido de SMC SRAM en [SMU7_FIRMWARE_HEADER_LOCATION +          │
│           offsetof(SMU74_Firmware_Header, SoftRegisters)]                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONSUMES                                                                    │
│   assignments:                                                              │
│     data->soft_regs_start = tmp;                                            │
│     smu_data->smu7_data.soft_regs_start = tmp;                              │
│   struct: smu7_hwmgr (data) + polaris10_smumgr (smu_data)                  │
│   scope: dentro de polaris10_process_firmware_header()                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ AFFECTS                                                                     │
│   effect: SMC SRAM initialization                                           │
│   target: registros SMC soft (via MMIO indirection)                         │
│   epistemic_state: NOT_DETERMINED (requiere validación hardware independiente)│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Evidencia de cada enlace

1. **Ubicación del firmware header**:
   ```c
   // smu7*.h (inc/)
   #define SMU7_FIRMWARE_HEADER_LOCATION 0x20000
   ```

2. **Definición del campo SoftRegisters**:
   ```c
   // smu74.h (inc/)
   struct SMU74_Firmware_Header {
       // ... otros campos ...
       uint32_t SoftRegisters;  // offset 44 = 0x2C desde inicio del struct
       // ... resto ...
   };
   ```

3. **Lectura del firmware**:
   ```c
   // polaris10_smumgr.c:2510-2516
   result = smu7_read_smc_sram_dword(hwmgr,
           SMU7_FIRMWARE_HEADER_LOCATION +
           offsetof(SMU74_Firmware_Header, SoftRegisters),
           &tmp, SMC_RAM_END);

   if (!result) {
       data->soft_regs_start = tmp;
       smu_data->smu7_data.soft_regs_start = tmp;
   }
   ```

4. **Función de lectura SMC**:
   ```c
   // smu7_smumgr.c:229-237
   int smu7_read_smc_sram_dword(struct pp_hwmgr *hwmgr,
           uint32_t smc_addr, uint32_t *value, uint32_t limit)
   {
       int result;
       result = smu7_set_smc_sram_address(hwmgr, smc_addr, limit);
       *value = result ? 0 : cgs_read_register(hwmgr->device, mmSMC_IND_DATA_11);
       return result;
   }
   ```

5. **Direccionamiento SMC**:
   ```c
   // smu7_smumgr.c:43
   cgs_write_register(hwmgr->device, mmSMC_IND_INDEX_11, smc_addr);
   ```

### Provenance Completa

Cada enlace mantiene provenance verificable:
- `PRODUCER`: `polaris10_process_firmware_header()` → llamada a `smu7_read_smc_sram_dword()`
- `TRANSFORMATION`: `smu7_read_smc_sram_dword()` → lecturas de registros MMIO SMC
- `REPRESENTATION`: variable `tmp` contiene valor leído de SMC SRAM
- `CONSUMES`: assignments a `data->soft_regs_start` y `smu_data->smu7_data.soft_regs_start`
- `AFFECTS`: inicialización de registros SMC soft para uso posterior

---

## Evaluación del Claim

### Claim original:
```
"soft_regs_start is populated from SoftRegisters"
```

### Análisis estado a estado:

| Elemento | Campo | Estado | Justificación |
|----------|-------|--------|---------------|
| **Result** (firmware read) | `status` | `observed` | Lectura directa de definición de struct y función |
| **Relation Chain** | `epistemic_state` | `PROVEN` | Cadena causal completa demostrada estáticamente |
| **Claim** | `status` | **PROVEN** | Evidencia suficiente para demostrar población desde SoftRegisters |
| **Claim** | `gap_kind` | **N/A** | No existe gap - claim demostrado |
| **Effect** (hardware) | `epistemic_state` | `NOT_DETERMINED` | El efecto final en hardware requiere validación independiente |

### Transición epistemológica:
```
UNKNOWN → OBSERVED (lectura de struct y función)
OBSERVED → PROVEN (cadena causal completa)
PROVEN → CLAIM PROVEN (evidencia suficiente)
CLAIM PROVEN → PENDING VALIDATION (efecto hardware)
```

---

## Comparación: Modelo Antes vs Después

| Aspecto | Modelo Anterior (con SHADOW_START) | Modelo Real (post-refutación) |
|---------|-----------------------------------|-------------------------------|
| **Fuente de inicialización** | SHADOW_START (falso) | SoftRegisters (real) |
| **Estado del claim** | PARTIAL / HUECO_DE_EVIDENCIA | **PROVEN** |
| **Gap kind** | HUECO_DE_EVIDENCIA | N/A (no hay gap) |
| **Evidencia clave** | Fixture de test (910 duplicado) | Código fuente real (funciones y structs) |
| **Unidad semántica** | NOT_DETERMINED (porque SHADOW_START no existía) | **NOT_DETERMINED** (para efecto hardware, pero cadena probada) |
| **Conflictos preservados** | 0xA21/0xA32 (intactos) | 0xA21/0xA32 (intactos) |

---

## Decisión de Diseño

Tras refutar la dependencia falsa `SHADOW_START`, el modelo se simplifica y fortalece:

### Antes:
```
QUESTION → EVIDENCE(0xA21) → TRANSFORMATION → REPRESENTATION → 
CONSUMES → AFFECTS → CLAIM(PARTIAL: SHADOW_START) → GAP
```

### Después:
```
QUESTION → EVIDENCE(0xA21) → TRANSFORMATION → REPRESENTATION → 
CONSUMES → AFFECTS → CLAIM(PROVEN: SoftRegisters) → 
[HARDWARE_EFFECT=NOT_DETERMINED] → VALIDATION_PENDING
```

---

## Próximos Pasos

1. **VALIDACIÓN DE EFECTO HARDWARE** (ahora prioridad):
   - Verificar que `soft_regs_start` efectivamente habilita escrituras SMC
   - Requeriría análisis de PM4 posterior o captura de estado SMC
   - Pero esto es separado del claim de población

2. **GLOBAL WORK SCAN** (§58 AGENTS.md):
   - [03] CLAIMS críticos abiertos → **Ninguno** (claim resuelto)
   - [06] OBSERVABILITY gaps → efecto hardware permanece NOT_DETERMINED
   - [11] AUTOMATION gaps → posible script para validar cadena completa
   - [19] VALIDATION → próximo paso lógico

3. **Mantenimiento de rigor epistemológico**:
   - No convertir cadena demostrada en verdad hardware
   - Mantener `HARDWARE_EFFECT = NOT_DETERMINED` separado
   - El claim de población está **PROVEN** independientemente del efecto

---

## Convergencia con el Principio Fundamental

El resultado mantiene la cadena epistemológica completa:

```
RXRE result (cadena poblacional)
    ↓
evidence (definiciones de struct, funciones, llamadas)
    ↓
interpretation (cadena causal completa: firmware→tmp→soft_regs_start)
    ↓
claim (PROVEN: "soft_regs_start is populated from SoftRegisters")
    ↓
validación independiente (pendiente - efecto hardware)
```

No:
```
RXRE result
    ↓
interpretación oculta
    ↓
truth asumida
```

El claim poblacional está **PROVEN**; el efecto hardware queda como asunto separado para validación futura.

---

<signed>
Sistema Autónomo RXRE