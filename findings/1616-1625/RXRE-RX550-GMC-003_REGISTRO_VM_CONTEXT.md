# RXRE-RX550-GMC-003 — Registro VM_CONTEXTn_PAGE_TABLE_BASE_ADDR (análisis estático)

## Evidencia primaria
- Artefacto: /usr/share/umr/database/ip/gmc_8_1_0.reg (214713 bytes, sha256: 02ed31da840858b44c3516a0327a497544a37e441e93d0adbaaa853c157199a)
- Referencia: polaris12.asic -> gmc810 null 2 8 2 0 ip/gmc_8_1_0.reg
- Registros observados (grep real, líneas 9247-9338):
  - mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0 0x54f 1 0 4294967295 (línea 9247)
  - mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR 0 0x550 1 0 4294967295 (línea 9306)
  - mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR 0 0x551 1 0 4294967295 (línea 9324)
  - mmVM_CONTEXT3_PAGE_TABLE_BASE_ADDR 0 0x552 ...
  - mmVM_CONTEXT4_PAGE_TABLE_BASE_ADDR 0 0x553 ...
  - mmVM_CONTEXT5_PAGE_TABLE_BASE_ADDR 0 0x554 ...
  - mmVM_CONTEXT6_PAGE_TABLE_BASE_ADDR 0 0x555 ...
  - mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR 0 0x556 ...
  - mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0 0x50e ...
  - mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR 0 0x50f ...
  - mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR 0 0x510 ...
  - mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR 0 0x511 ...
  - ... hasta mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR 0 0x515 ...

## Patrón observado (no inferido; basado en datos reales)
- CONTEXTO 0: 0x54f
- CONTEXTOS 1-7: 0x550 → 0x556 (incremento +1 hex por contexto, 8 registros consecutivos en rango)
- CONTEXTOS 8-15: 0x50e → 0x515 (incremento +1 hex por contexto, 8 registros consecutivos en rango)
- No hay registros definidos para CONTEXTOS 16-... en este archivo
- Registro no es contiguo de 0x54f a 0x550 sin interrupción (hay un salto de contexto/estructura entre 0 y 1-7; 8-15 están en rango separado)

## Hipótesis evaluadas
- H1 (patrón contiguo simple): REFUTADO — no todo es 0x54f, 0x550, 0x551 lineal global; hay agrupaciones.
- H2 (grupos por rango de contexto): RESPALDADO — 1-7 (0x55x) y 8-15 (0x50x) forman grupos; 0 (0x54f) es independiente.
- H3 (registro aislado por contexto): OBSERVED — cada contexto tiene su base; no hay superposición de registros.
- H4 (código del driver configura): CORROBORADO por referencia en xref.py:285 (WREG32 escribe registro) y polaris12.asic; uso dinámico OPEN (requeriría UMR con root).

## Relación con código / contrato
- `polaris12.asic` referencia `gmc_8_1_0.reg` → contrato de registro verificado.
- `WREG32` mecanismo de escritura documentado (`xref.py:285`) → correlacion posible entre definición estática y mecanismo de configuración.
- `gmc_7_1_d.h` referencia documentada previamente (RXRE-001/002/003/035); conexión entre definición de header y regdb confirmada.

## Limitaciones
- No se puede afirmar valor en ejecución sin observación dinámica (MMIO / UMR con privilegios).
- El archivo `.reg` no indica qué contexto está activo ni qué valores se escriben durante ejecución.
- No se confirma interacción entre VM_CONTEXT y otros registros (ej. PAGE_TABLE_START/END) sin análisis más amplio.

## Estado epistemológico
- REFERENCIA: PROVEN (archivo real, hash verificado)
- PRESENCIA REGISTRO: PROVEN (grep exacto, líneas citadas)
- PATRÓN DE OFFSETS: OBSERVED (patrón de grupos identificado, no simplificado como secuencia única)
- USO EN EJECUCIÓN: OPEN (requiere observación dinámica)
- EXCLUSIVIDAD / Cualquier causalidad universal: REFUTADA por diseño del contrato

## Resultado
No se requiere cambio de producción (machine.py, correlate.py, rxre) para este hallazgo estático. El conocimiento debe persistirse en el informe consolidado existente sin duplicar hallazgos previos.
