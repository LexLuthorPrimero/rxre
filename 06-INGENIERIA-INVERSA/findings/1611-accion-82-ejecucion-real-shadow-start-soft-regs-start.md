# 1611 — RXRE-008 FASE 3: ACCIÓN 82 EJECUCIÓN REAL — SHADOW_START → soft_regs_start

```text
CLASSIFICATION=NO_LINK_FOUND+HUECO_DE_EVIDENCIA_PERSISTE
WORK_CLASS=RXRE-008-FASE-3 · ACCION-82-EJECUCION-REAL
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7 · Polaris12 · gfx_8_0
PREGUNTA=¿Existe evidencia estática independiente que demuestre el enlace SHADOW_START → soft_regs_start?
MODIFICATIONS=NINGUNO · solo base de datos SQLite + este hallazgo
WRITE_EXECUTION=NINGUNO · solo lectura de fuente y de la CLI; corpus RESEARCH/working/linux-7.1.3
DISPOSITIVO_TOCADO=NINGUNO · no MMIO, no Intel, no display, no driver bind
RUNTIME=solo lectura de fuente y de la CLI; corpus RESEARCH/working/linux-7.1.3
```

---

## Resumen

Se ejecutó **realmente** la ACTION 82 registrada en Finding 1607:

```
ACTION 82: resolver el enlace: SHADOW_START → soft_regs_start
```

Tras **exhaustiva búsqueda estática** en el corpus disponible (kernel source, SMU source, headers, findings existentes), **no se encontró evidencia suficiente** para demostrar el enlace causal:

```
SHADOW_START
     ↓
...
     ↓
soft_regs_start
```

El estado actual persiste:

```
soft_regs_start = PARTIAL
gap_kind = HUECO_DE_EVIDENCIA
```

---

## Contexto de la Acción

El vertical slice de Finding 1607 estableció:

- **QUESTION**: ¿Qué inicializa soft_regs_start en Polaris12/gfx_8_0?
- **EVIDENCE**: Registro 0xA21 (kernel definition), PM4 SHADOW_START (mencionado en evidencia)
- **RELATION**: PRODUCER → TRANSFORMS → REPRESENTS → CONSUMES → AFFECTS
- **CLAIM**: "soft_regs_start is populated from SoftRegisters" (PARTIAL, HUECO_DE_EVIDENCIA)
- **NEXT_ACTION (ID 82)**: Resolver la siguiente relación faltante (SHADOW_START → soft_regs_start)

La distinción epistemológica OBSERVED vs MODELED (Finding 1603) se aplica:
- `results`: lectura de 0xA21 → `status='observed'` (medición directa)
- `relation_chains`: enlace PM4 SHADOW_START → soft_regs_start → `epistemic_state='PARTIAL'` (interpretación sin certeza)

---

## Búsqueda Estática Ejecutada

### 1. Búsqueda de `SHADOW_START` en el corpus

**Resultado**: **NO ENCONTRADO** en:
- `/home/lucas/Escritorio/rxre/RESEARCH/working/linux-7.1.3/` (kernel 7.1.3)
- `/home/lucas/Escritorio/rxre/rx550-upstream-7.2.8/linux-7.2.8/` (kernel 7.2.8 upstream)
- `/home/lucas/Escritorio/rxre/06-INGENIERIA-INVERSA/` (findings y herramientas RXRE)

**Coincidencias encontradas** (irrellevantes para el enlace):
- `SHADOW` en contextos de display (DPHY_FEC_READY_SHADOW)
- `SHADOW` en powerplay (Shadow Pstate capability)
- `SHADOW` en RLC (WREG32_SOC15_RLC_SHADOW)
- `SHADOW` en memoria del kernel (kmsan, kasan)
- **Ninguna** corresponde a un PM4 packet o registro que inicialice `soft_regs_start`

### 2. Búsqueda de `soft_regs_start` (consumidor conocido)

**Resultado**: **ENCONTRADO** en:
- **Ubicación**: `drivers/gpu/drm/amd/pm/powerplay/smumgr/smu7_smumgr.c` y archivos específicos por ASIC (polaris10_smumgr.c, iceland_smumgr.c, etc.)
- **Función**: `smu7_set_smc_sram_address()` (línea 43) y bucles de copia de bytes
- **Uso**: Registro MMIO `mmSMC_IND_INDEX_11` (SMC_IND_INDEX_11 = 0x1AC) para direccionar espacio SMC
- **Estructura**: Campo `soft_regs_start` en `smu7_hwmgr` o `smu_data->smu7_data`

### 3. Búsqueda de relación PM4 → SMC

**Hallazgos relevantes**:
- `mmSMC_IND_INDEX_11` (0x1AC) y `mmSMC_IND_DATA_11` (0x1AD) son los registros usados para acceder a SMC
- Función `smu7_set_smc_sram_address()` escribe `smc_addr` en `mmSMC_IND_INDEX_11`
- Pero **no se encontró** ningún productor que llame a esta función desde un contexto PM4 genérico

### 4. Análisis de findings existentes

**Finding 1602** (byte offset vs índice dword):
- Confirma que `mmSMC_IND_INDEX_11 = 0x1AC` es un **índice dword**
- El byte offset correspondiente es `0x1AC * 4 = 0x6B0`
- El mecanismo de acceso SMC usa este registro como índice, no como byte offset directo

**Finding 1603** (OBSERVED vs MODELED):
- La mención de "PM4 SHADOW_START" en Finding 1607 fue clasificada como **MODELED interpretation**
- No había evidencia directa que la respaldara, solo una cita en herramientas de prosificación

---

## Análisis Causal Detallado

### Estado actual de la cadena (verificado en DB):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PRODUCER                                                                    │
│   operation_id: op_softregs_prod_*                                          │
│   operacion: register_read                                                  │
│   capability: register.definition                                           │
│   question: "What initializes soft_regs_start?"                             │
│   target: 1002:699f@c7 (Polaris12, gfx_8_0)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVIDENCE (OBSERVED)                                                         │
│   result_id: res_softregs_val_*                                             │
│   type: register                                                            │
│   value: "0xA21_val" (normalizado desde header kernel)                      │
│   source: reg_resolve.py → drivers/gpu/drm/amd/include/asic_reg/gfx8/...   │
│   status: "ok"                                                              │
│   raw_json: {} (preservado por transparencia)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRANSFORMATION                                                              │
│   transformation: "bits_extract_dword_index"                                │
│   → Extrae índice dword del registro MMIO (no byte offset)                  │
│   → Unidad semántica: NOT_DETERMINED para 0xA21/0xA32 (hallazgo 1602)       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPRESENTS                                                                  │
│   representation: "soft_regs_start_dword"                                   │
│   → Representación semántica del registro como índice dword                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONSUMES                                                                    │
│   consumer: res_softregs_val_* (el resultado observado)                     │
│   → El hardware consume el valor para habilitar escrituras de registro      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ AFFECTS                                                                     │
│   effect: "register_write_enabled"                                          │
│   → Efecto en hardware: habilita escritura en registros SMC soft           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ❌ ENLACE FALTANTE (ACTION 82)                                              │
│   ¿SHADOW_START → ... → soft_regs_start?                                   │
│   **NO ENCONTRADO** en corpus estático disponible                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Desglose de la búsqueda fallida

| Elemento buscado | Resultado | Conclusión |
|------------------|-----------|------------|
| **PM4 packet SHADOW_START** | No encontrado en headers/registers | No existe como definición de packet PM4 |
| **Registro SHADOW_START** | No encontrado en asic_reg/* | No es un registro MMIO directo |
| **Función que use SHADOW_START** | No encontrado en driver source | No hay código que lo procese |
| **Referencia en findings** | Solo en citas_prosa_census.py (fixture de test) | Era parte de un fixture duplicado, no evidencia real |
| **Ruta alternativa vía SMC** | smu7_set_smc_sram_address() existe pero no conectada a PM4 | Falta el enlace producer → esta función |

---

## Estados Epistemológicos Resultado

| Elemento | Campo | Valor | Justificación |
|----------|-------|-------|---------------|
| **Result** (0xA21) | `status` | `observed` | Lectura directa de header kernel |
| **Relation Chain** | `epistemic_state` | `PARTIAL` | Transformación probada; **enlace PM4 no encontrado** |
| **Claim** | `status` | `PARTIAL` | Persiste gap de evidencia |
| **Claim** | `gap_kind` | `HUECO_DE_EVIDENCIA` | Tipo de gap confirmado (§12 CLAIM REGISTRY) |
| **Next Action** (ID 82) | `status` | `OPEN` | Acción ejecutada pero no resuelta |

**Conflictos preservados** (hallazgo 1602):
- `CONFLICT` entre linajes `mmMC_CG_DATAPORT`: `gmc_8_1_d.h` 0xA21 vs `gmc_8_2_d.h` 0xA32
- `CANDIDATES` con ambos headers
- `CHOSEN=null` sin regla de selección automática

**UNIT_SEMANTICS preservada** (hallazgo 1602):
- `0xA21` y `0xA32`: `UNIT_SEMANTICS=NOT_DETERMINED` — el `#define` declara índice dword, pero la codificación PM4 y el efecto hardware requieren validación independiente

---

## Comparación: Estado Inicial vs Estado Final

| Aspecto | Antes de ACTION 82 | Después de ACTION 82 |
|---------|-------------------|----------------------|
| **Estado del claim** | PARTIAL (HUECO_DE_EVIDENCIA) | PARTIAL (HUECO_DE_EVIDENCIA) |
| **Evidencia de enlace** | Afirmada en Finding 1607 como evidencia | **Refutada** - no existe en corpus |
| **Provenance del claim** | basada en supuesta evidencia SHADOW_START | basada solo en transformación probada |
| **Necesidad de next_action** | resolver SHADOW_START → soft_regs_start | **mismo next_action** - enlace aún faltante |
| **Grado de certeza** | basado en suposición no verificada | basado en evidencia verificable únicamente |

---

## Próximos Pasos Accionables

Dado que la búsqueda estática **agotó el corpus disponible** sin encontrar el enlace:

### OPCIÓN 1: Declarar HARDWARE_OBSERVABILITY_GAP
```
Si el único discriminante restante requiere hardware:
  declarar: HARDWARE_OBSERVABILITY_GAP
  cerrar la acción como NOT_DETERMINED
```
**Aplicación**: El enlace SHADOW_START → soft_regs_start podría requerir:
- Análisis de PM4 queue en tiempo de ejecución
- Captura de IB (Indirect Buffer) durante inicialización
- Decodificación de comandos PM4 enviados al bloque SMC

### OPCIÓN 2: Busque discriminantes alternativos
Re-examinar si existen otras rutas de inicialización:
- **Otra vía PM4**: SET_CONTEXT, WRITE_DATA, etc.
- **Inicialización por firmware**: SMU firmware que escriba directamente
- **Ruta de arranque**: secuencia de boot que establezca el valor

### OPCIÓN 3: Mejorar la precisión del claim
Cambiar el claim de:
```
"soft_regs_start is populated from SoftRegisters"
```
a algo más específico y verificable:
```
"soft_regs_start register (mmSMC_IND_INDEX_11) is written via SMC indirection"
```

---

## Convergencia con el Principio Fundamental

El resultado mantiene la integridad epistemológica:

```
RXRE result (tras acción 82)
    ↓
evidence (res_softregs_val_* con status=observed)
    ↓
interpretation (relation_chains con epistemic_state=PARTIAL)
    ↓
claim (gap_kind=HUECO_DE_EVIDENCIA explícito, no falso)
    ↓
next_action (ID 82 ejecutado, resultado documentado)
    ↓
validación independiente (pending - requiere evidencia nueva)
```

No:
```
RXRE result
    ↓
interpretación oculta ("SHADOW_START inicializa soft_regs_start")
    ↓
truth asumida
```

---

## Próximos Pasos Sugeridos (Global Work Scan)

Tras ejecutar ACTION 82 y documentar su resultado:

1. **GLOBAL WORK SCAN** (§58 AGENTS.md):
   - [06] OBSERVABILITY gaps → **HARDWARE_OBSERVABILITY_GAP** identificado
   - [11] AUTOMATION gaps → posible script para decodificar PM4 buffers
   - [13] BOTTLENECKS medidos → enlace PM4-SMC como cuello de botella epistemológico

2. **Selección de próxima acción** (§59 AGENTS.md):
   Prioridad a:
   - mayor poder discriminante (evidencia hardware cerraría el gap)
   - mayor desbloqueo (permitiría pasar claim a PROVEN)
   - coste razonable (análisis de PM4 buffer es factible estáticamente)

3. **Próxima acción candidata**:
   - Analizar comandos PM4 durante secuencia de inicialización
   - Buscar escrituras a `mmSMC_IND_INDEX_11` en IBs capturados
   - Validar que el valor escrito corresponda a direcciones SMC válidas

---

<signed>
Sistema Autónomo RXRE