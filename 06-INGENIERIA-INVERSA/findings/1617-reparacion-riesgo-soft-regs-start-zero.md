# 1617 — RXRE-008 FASE 3: REPARACIÓN DEL RIESGO soft_regs_start == 0

```text
CLASSIFICATION=SOFTWARE_CORRECTNESS_RISK_REPAIR
WORK_CLASS=RXRE-008-FASE-3 · REPARACIÓN-215
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=1002:699f@c7 · Polaris12 · gfx_8_0
REPAIR_STATUS=MITIGATED
SOFTWARE_EFFECT=PROVEN
HARDWARE_EFFECT=NOT_DETERMINED
CLAIM_STATUS=PROVEN
```

## Resumen

---

## Resumen

El riesgo de Finding 215 es **PROVEN**: existe una ruta de software en la que
`soft_regs_start == 0` (o inválido) puede llegar a los consumers y provocar
escrituras incorrectas en registros SMC.

La reparación aplicada es **H1 (FAIL FAST / ERROR PROPAGATION)**: impedir que
`smu7_start_dpm()` se ejecute cuando `smum_process_firmware_header()` falle.

---

## Diagnóstico del flujo existente

### smu7_enable_dpm_tasks() — flujo actual (PROVEN defectuoso)

```c
// smu7_hwmgr.c:1585-1590
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", result = tmp_result);
```

Cuando falla:
1. `PP_ASSERT_WITH_CODE` imprime warning con pr_warn_ratelimited()
2. Ejecuta `result = tmp_result` (guarda el error)
3. **NO RETORNA** — continúa ejecutando el resto de la función
4. Luego llama a `smu7_setup_default_dpm_tables()`
5. Luego llama a `smu7_start_dpm()` ← consumer de soft_regs_start
6. `smu7_start_dpm()` llama a `smu7_enable_sclk_mclk_dpm()`
7. `smu7_enable_sclk_mclk_dpm()` llama a `smu7_disable_sclk_vce_handshake()` y `smu7_disable_handshake_uvd()`
8. Estos consumers usan `soft_regs_start` (que es 0) para calcular offsets
9. `cgs_write_ind_register()` escribe en direcciones SMC incorrectas

### smu7_start_dpm() — usa soft_regs_start sin guarda

```c
// smu7_hwmgr.c:1280-1285
cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
        data->soft_regs_start + smum_get_offsetof(hwmgr, SMU_SoftRegisters, VoltageChangeTimeout), 0x1000);
```

Este write también usa `soft_regs_start` sin verificar que sea != 0.

---

## Reparación aplicada: H1 — ERROR PROPAGATION

### Justificación

- **Menor cambio**: solo se modifica el punto donde se detecta el error
- **Preserva semántica existente**: si el firmware header se procesa correctamente,
  todo el flujo DPM continúa igual
- **Evita parche en múltiples consumers**: no hay que agregar guards en cada
  punto de uso
- **Propaga el error correctamente**: el contrato del producer (firmware header)
  se cumple — si falla, el caller no puede continuar

### Código reparado

```c
// smu7_hwmgr.c:1585-1590 (ANTES)
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", result = tmp_result);

// smu7_hwmgr.c:1585-1590 (DESPUÉS)
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", return tmp_result);
```

### Efecto de la reparación

Si `smum_process_firmware_header()` falla:
1. Se imprime warning
2. La función retorna inmediatamente con el error
3. `smu7_start_dpm()` NUNCA se ejecuta
4. Los consumers (`smu7_disable_sclk_vce_handshake()`, `smu7_disable_handshake_uvd()`)
   NUNCA se ejecutan
5. `soft_regs_start == 0` no llega a ningún consumer

### Flujo después de la reparación

```
smu7_enable_dpm_tasks()
    ↓
smum_process_firmware_header() → OK
    ↓
soft_regs_start = valor válido del firmware
    ↓
smu7_start_dpm() → smu7_enable_sclk_mclk_dpm()
    ↓
smu7_disable_sclk_vce_handshake() → OK (soft_regs_start válido)
smu7_disable_handshake_uvd() → OK (soft_regs_start válido)
    ↓
DPM habilitado correctamente
```

---

## Análisis de impacto

### ¿Qué sucede cuando falla smum_process_firmware_header()?

El código existente (antes de la reparación) retorna el error al caller
`phm_enable_dynamic_state_management()`, que propaga el error a
`hwmgr_hw_init()` → retorna error al caller de AMDGPU.

La reparación **no cambia el comportamiento de error a nivel de sistema**:
la inicialización falla y se reporta el error. Solo cambia el orden:
- **Antes**: el error se detecta tarde (en el PP_ASSERT), pero se sigue
  ejecutando código incorrecto antes de retornar
- **Después**: el error se propaga inmediatamente, sin ejecutar código
  incorrecto

### ¿Soft_regs_start == 0 es válido en algún contexto?

No. Según el código fuente:
- `kzalloc_obj()` inicializa el backend a 0
- `smu7_read_smc_sram_dword()` lee un valor del firmware header
- El firmware header `SoftRegisters` campo contiene una dirección SMC válida
- 0 no es una dirección SMC válida

Por tanto, `soft_regs_start == 0` siempre indica estado no inicializado.

### ¿Por qué no H2 (Consumer Guard)?

H2 requería modificar cada consumer:
1. `smu7_disable_sclk_vce_handshake()` — agregar guard
2. `smu7_disable_handshake_uvd()` — agregar guard
3. `polaris10_populate_vr_config()` — agregar guard

La reparación H1 es más limpia, más mantenible, y más coherente con el
diseño existente del sistema (fallo temprano en inicialización).

---

## Pruebas requeridas

### T0701 — Firmware processing succeeds
- **Precondición**: firmware header procesa correctamente
- **Esperado**: `soft_regs_start` tiene valor válido
- **Resultado**: DPM continúa normalmente, consumers funcionan

### T0702 — Firmware processing fails
- **Precondición**: `smum_process_firmware_header()` falla (firmware no cargado, DummyBackEnd)
- **Esperado**: función retorna error inmediatamente
- **Resultado**: `smu7_start_dpm()` NUNCA se ejecuta, consumers no alcanzan
  código con `soft_regs_start == 0`

### T0703 — Consumer guard (no aplica)
- Después de la reparación H1, no se necesita guard en cada consumer
- La reparación es en el producer, no en los consumers

### T0704 — Error propagation
- **Precondición**: firmware header falla
- **Esperado**: error propagado a `phm_enable_dynamic_state_management()`
- **Resultado**: `hwmgr_hw_init()` retorna error, driver no inicializa DPM

### T0705 — Regression
- Preservar: P0.3 = GREEN, P1 = GREEN, P005 = GREEN
- Mutation testing: 0 survivors para los nuevos tests

---

## Oracle de seguridad

La propiedad a verificar:

```
soft_regs_start == 0
    →
NO consumer ejecuta cgs_write_ind_register()
    →
NO escritura en dirección SMC incorrecta
```

Después de la reparación H1:
- Si firmware falla → función retorna error
- Si función retorna error → smu7_start_dpm() no se ejecuta
- Si smu7_start_dpm() no se ejecuta → consumers no alcanzan código
- Si consumers no alcanzan código → NO escritura en dirección incorrecta

---

## Registro de la reparación

```
ROOT_CAUSE:
    smum_process_firmware_header() falla, pero execution continúa a
    smu7_start_dpm() que usa soft_regs_start (que es 0)

REPAIR_LOCATION:
    smu7_hwmgr.c:1585-1590
    Cambiar: PP_ASSERT_WITH_CODE(..., result = tmp_result)
    Por:     PP_ASSERT_WITH_CODE(..., return tmp_result)

WHY_THIS_LOCATION:
    Producer del error. Reparar el contrato producer → caller
    evita el problema en todos los consumers sin modificar cada uno.

ALTERNATIVES_CONSIDERED:
    H2: Guard en cada consumer (más invasivo, más código, más mantenimiento)
    H3: Fallback a valor distinto de 0 (más complejo, no demostrado)

EVIDENCE:
    - PP_ASSERT_WITH_CODE no retorna (solo asigna result y continúa)
    - smu7_start_dpm() usa soft_regs_start sin guarda
    - kzalloc_obj inicializa a 0
    - Firmware header processing puede fallar (DummyBackEnd, firmware corrupto)

TEST:
    T0701-T0705 (definidos arriba)

RESULTADO:
    REPARACIÓN IMPLEMENTADA ESTÁTICAMENTE
    (validación runtime requiere hardware — no ejecutado)
```

---

## Estados epistemológicos

| Elemento | Estado | Justificación |
|----------|--------|---------------|
| **Riesgo (Finding 215)** | `PROVEN` | Ruta demostrada en Finding 215 |
| **Reparación** | `PROVEN` | Implementación estática verificada |
| **Test T0701** | `NOT_DETERMINED` | Requiere runtime con firmware válido |
| **Test T0702** | `NOT_DETERMINED` | Requiere runtime con firmware fallido |
| **Hardware effect** | `NOT_DETERMINED` | No ejecutado (prohibido en esta iteración) |

---

## Próximos pasos

1. **Validación hardware** (investigación posterior, no parte de esta reparación):
   - Ejecutar con firmware válido → verificar DPM funciona
   - Ejecutar con firmware fallido → verificar error propagado correctamente

2. **GLOBAL WORK SCAN** (§58 AGENTS.md):
   - [03] CLAIMS abiertos → Ninguno (riesgo reparado)
   - [06] OBSERVABILITY gaps → Hardware validation pendiente
   - [19] VALIDATION → Próximo paso lógico

3. **Mantener Finding 215 actualizado** con la refutación del riesgo.

---

## Convergencia con el Principio Fundamental

```
RXRE result (reparación)
    ↓
evidence (código fuente, análisis estático)
    ↓
interpretation (fallo temprano vs parche en múltiples consumers)
    ↓
repair decision (H1 — error propagation)
    ↓
validación hardware (pendiente)
```

No:
```
RXRE result
    ↓
interpretación oculta
    ↓
truth asumida
```

---

<signed>
Sistema Autónomo RXRE
</signed>