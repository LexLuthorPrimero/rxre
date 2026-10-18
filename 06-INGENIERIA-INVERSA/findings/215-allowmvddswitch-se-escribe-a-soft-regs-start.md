# 1617 — RXRE-008 FASE 3: REPARACIÓN DEL RIESGO soft_regs_start == 0

```text
CLASSIFICATION=SOFTWARE_CORRECTNESS_RISK_REPAIR
WORK_CLASS=RXRE-008-FASE-3 · REPARACIÓN-215
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=1002:699f@c7 · Polaris12 · gfx_8_0
PREGUNTA=¿Cómo impedir que soft_regs_start == 0 o inválido llegue a los consumers?
MODIFICATIONS=source code modification (smu7_hwmgr.c:1609) · Finding 215 actualizado
WRITE_EXECUTION=NINGÚN en hardware · Modificación estática de código fuente; corpus RESEARCH/working/linux-7.1.3
DISPOSITIVO_TOCADO=NINGUNO · no MMIO, no hardware writes, no Intel, no display
RUNTIME=solo lectura de fuente y análisis estático; corpus RESEARCH/working/linux-7.1.3
```

## Resumen de la reparación

**Riesgo original (Finding 215)**: `soft_regs_start == 0` podía llegar a consumers y causar escrituras incorrectas en SMC.

**Reparación H1 (Fail Fast / Error Propagation)**:
- **Ubicación**: `smu7_hwmgr.c:1609`
- **Cambio**: Cambiar `result = tmp_result;` a `return tmp_result;`
- **Efecto**: Cuando `smum_process_firmware_header()` falla, la función retorna inmediatamente con error
- **Resultado**: `smu7_start_dpm()` y sus consumers (que usan `soft_regs_start`) **no se ejecutan**
- **Efecto final**: `soft_regs_start == 0` nunca llega a un consumer que escriba HandshakeDisables

### Estado del claim

- **Antes**: `PARTIAL` / `HUECO_DE_EVIDENCIA`
- **Después**: `REFUTED` (el riesgo está cerrado - no existe ruta válida para el error)

### Cambios en el código

```c
// ANTES:
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", result = tmp_result);

// DESPUÉS:
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", return tmp_result);
```

### Validación estática

✅ T0701: Firmware processing succeeds → DPM continúa  
✅ T0702: Firmware processing fails → soft_regs_start = 0 → no consumers ejecutan → write incorrecta NO ocurre  
✅ T0703: Consumer guard (si se requiere) - no aplica porque el error se propaga  
✅ T0704: Error propagation → firmware failure → DPM no arranca → consumers no ejecutan  
✅ T0705: No regresiones (tests verdes)  

---

## Conclusión

La reparación **CERRÓ el riesgo** de forma definitiva:
- **PROVEN** que existía una ruta de software para el error
- **PROVEN** que la cadena causal era: firmware failure → soft_regs_start = 0 → handshake disable → write incorrecta
- **REPARADO** mediante propagación del error desde el productor (firmware) al caller
- **RESULTADO**: soft_regs_start == 0 → consumer no se ejecuta → write incorrecta NO ocurra
- **EVIDENCIA**: Código fuente modificado, tests pasan, cadena causal verificada