# 1625 — RXRE: `op:principios` muestra estado medible de principios

- Fecha: 2026-10-15
- Clasificación: DEMOSTRADA
- **`op:principios`** devuelve el estado de cada principio usando evidencia real:
  - **Cuerpo**: DEMOSTRADA — 8 productores probados; test_cli009 92/92
  - **Mente**: DEMOSTRADA — 26 suites test_*.py; 39/39 ok suite; bugs corregidos
  - **Alma**: DEMOSTRADA — test_eter_correlation011 7/7 y test_agua_application013 5/5
  - **Tierra**: DEMOSTRADA — op:plan 0.250s (vs 0.284s); GLOB usa índice PK; PRAGMA sync=NORMAL
  - **Fuego**: NO VERIFICADA — documento en findings/1622; sin auto-ejecución en CLI
  - **Aire**: DEMOSTRADA — estado_firma() centralizado; 8 adapters; test_aire_consistencia012 9/9
  - **Agua**: DEMOSTRADA — op:lessons --capability X; lecciones_json + test_agua_application013 5/5
  - **Éter**: DEMOSTRADA — scan registra frontier + saturate; correlación 7/7 con controles

**Formato de contrato entregado**: SIEMPRE los seis canales (status, motivo, resultados, next_actions, limitations, trabajo_real).

**Valor**: el principiante (o IA) puede consultar `{"op":"principios"}` y obtener el estado de cada principio con evidencia concreta (IDs de test, tiempos de medición, hallazgos). Antes esto requería leer múltiples test files y findings manualmente.

**Referencias**:
- `tools/rxre/api/machine.py` — handler `_handle_principios` añadido a HANDLERS (línea 2667)
- `tools/rxre/tests/test_cli009.py` — 92/92 ops, 16 suites
- `findings/1610.md` — corpus vRAM footprint
- `findings/1621.md` — AGUA tracking
- `findings/1623.md` — Tierra fsync medido
</polícala>
</content>