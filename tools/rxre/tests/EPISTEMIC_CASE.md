# EPISTEMIC CASE — Finding 1618

## PROPÓSITO

Conversión de un caso real (Finding 1618) en una regresión epistemológica de RXRE
para impedir que una futura IA vuelva a confundir:

```
ACTION_EXECUTED ≠ RELATION_PROVEN
REPAIR_PROVEN   ≠ CLAIM_PROVEN
SOFTWARE_EFFECT ≠ HARDWARE_EFFECT
```

## ENTREGABLE

```
EPISTEMIC_CASE=Finding_1618
ACTION_EXECUTED=EXECUTED
ACTION_RESULT=LINK_NOT_FOUND
RELATION_STATUS=NOT_ESTABLISHED
REPAIR_STATUS=MITIGATED
SOFTWARE_EFFECT=PROVEN
HARDWARE_EFFECT=NOT_DETERMINED
STRUCTURAL_SUPPORT=HEADER_KEYS_AÑADIDAS_EN_FINDING_1618_Y_1617
MISSING_SUPPORT=NINGUNO (auditoría inicial confirmó huecos; cerrados en esta iteración)
REGRESSION_TESTS=tools/rxre/tests/test_epistemic_distinctions.py
MUTATION_SURVIVORS=0
```

## CADENA DE EVIDENCIA (PRODUCER → TRANSFORMATION → REPRESENTATION → CONSUMER → HARDWARE EFFECT)

| Dimensión | Producer | Transformation | Representation | Consumer | Hardware Effect |
|-----------|----------|----------------|----------------|----------|-----------------|
| ACTION | Finding 1611 | DB registro | ACTION_EXECUTED=EXECUTED | test_epistemic_distinctions | N/A |
| ACTION_RESULT | Búsqueda estática | grep corpus kernel | ACTION_RESULT=LINK_NOT_FOUND | test_epistemic_distinctions | N/A |
| RELATION | Finding 1611 | xref corpus | RELATION_STATUS=NOT_ESTABLISHED | test_epistemic_distinctions | N/A |
| REPAIR | Finding 215/1617 | code change smu7_hwmgr.c | REPAIR_STATUS=MITIGATED | test_epistemic_distinctions | NOT_DETERMINED |
| SOFTWARE_EFFECT | Control flow analysis | smum_process_firmware_header return | SOFTWARE_EFFECT=PROVEN | test_epistemic_distinctions | NOT_DETERMINED |
| HARDWARE_EFFECT | (pendiente) | (ninguno) | HARDWARE_EFFECT=NOT_DETERMINED | test_epistemic_distinctions | NOT_DETERMINED |

## PRUEBAS DE ESTRUCTURA (no dependientes de prosa)

1. `test_01`: ACTION_EXECUTED=EXECUTED ≠ RELATION_STATUS=NOT_ESTABLISHED
2. `test_02`: ACTION_RESULT=LINK_NOT_FOUND ≠ PROVEN
3. `test_03`: REPAIR_STATUS=MITIGATED ≠ CLAIM_STATUS=PROVEN
4. `test_04`: SOFTWARE_EFFECT=PROVEN ≠ HARDWARE_EFFECT=NOT_DETERMINED

## MUTATIONS (detectadas)

| Mutation | Tipo | Detectada |
|----------|------|-----------|
| ACTION_EXECUTED=EXECUTED → PROVEN | Conflación | SÍ |
| ACTION_RESULT=LINK_NOT_FOUND → PROVEN | Conflación | SÍ |
| REPAIR_STATUS=MITIGATED → PROVEN | Conflación | SÍ |
| HARDWARE_EFFECT=NOT_DETERMINED → PROVEN | Conflación | SÍ |
| CLAIM_STATUS=PROVEN → NOT_PROVEN | Borrado | SÍ |
| SOFTWARE_EFFECT=PROVEN → NOT_DETERMINED | Downgrade | SÍ |

## CONCLUSIÓN

RXRE ahora puede representar estructuralmente las cuatro dimensiones epistemológicas
descubiertas en Finding 1618. Las distinciones NO dependen de leer el texto humano del
finding — se recuperan mediante `header_field()` sobre las header keys declaradas.

Una futura IA que intente confundir ACTION_EXECUTED con RELATION_PROVEN (o cualesquiera
de las otras tres conflaciones) será detectada por los tests de regresión, que fallarán
si las distinciones se eliminan o corrompen.

**HARDWARE_EFFECT permanece NOT_DETERMINED** porque no hay observación runtime:
la validación hardware (T0701/T0702) está diferida por autorización del propietario.
No se ha elevado artificialmente a PROVEN.
