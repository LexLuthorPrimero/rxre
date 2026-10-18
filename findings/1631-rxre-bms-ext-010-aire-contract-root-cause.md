# Finding 1631 — RXRE-BMS-EXT-010: AIRE contract integration in root_cause (MENTE)

**Fecha:** 2026-10-15  
**Categoría:** tooling / AIRE / MENTE / contract  
**Estado:** ✅ completada

## Resumen

`_handle_run` ahora inyecta el resultado de `_verificar_integridad_artefacto`
(PRE_EXECUTION_CONTRACT_CHECK) en el envelope `precheck.contrato`. Cuando la
operación falla, `_analyze_run_failure` incluye una hipótesis de tipo
`contract_violation` con la limitación del contrato y la verificación correspondiente.

## Principio

**AIRE** — Verificar contratos y el recorrido completo. La integridad se
verifica **antes** de ejecutar, no después. Pero una verificación que no
influye en la causa raíz no sirve de nada.

## Evidencia

```json
{
  "op": "run",
  "capability": "binary.inspect",
  "artefacto": "/nonexistent/path/to/binary"
}
→ status: invalid_input
→ root_cause.hipotesis: [
    {tipo: "artefacto_not_found", nodo: "dispatch.precheck.input_existe"},
    {tipo: "contract_violation", nodo: "aire._verificar_integridad_artefacto",
     hipotesis: "El contrato PRE_EXECUTION fallo: artefacto no existe: /nonex..."}
]
```

## Cambios

`tools/rxre/api/machine.py`:
- `_verificar_integridad_artefacto` ahora siempre se ejecuta (antes solo cuando
  fallaba) y se inyecta en `precheck.contrato` del envelope
- `_analyze_run_failure` incluye `contract_violation` como nueva categoría de
  hipótesis, clasificada bajo `aire._verificar_integridad_artefacto`
