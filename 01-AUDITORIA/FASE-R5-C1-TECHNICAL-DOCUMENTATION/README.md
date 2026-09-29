# FASE R5 — Documentación técnica consolidada C1/RX550

**Tipo:** documentación/auditoría, READ-ONLY
**Fecha de consolidate:** 2026-09-24
**Ámbito:** proyecto `RX550-INVESTIGACION`; no es una autorización operativa.

## Propósito

Consolidar en un único registro la arquitectura, la línea temporal, la evidencia experimental, la definición de C1, el automatizador v1.1.0, los fallos, el estado actual, la provenance y la matriz de conocimiento. El documento conserva las contradicciones y los `UNKNOWN/NOT_AVAILABLE/CONFLICT`; no reemplaza las fuentes canónicas.

## Fuentes y precedencia

1. `00-INDICE/MASTER-RESEARCH-STATUS.md` — estado vigente y addendas.
2. `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` — validez del entorno actual.
3. `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` y `C1-ISOLATION-AUTOMATOR.sha256` — automatizador y validación registrada.
4. `02-ARQUITECTURA/knowledge.md`, `evidence.md`, `hypotheses.md`, `open_questions.md` — conocimiento base, con Addenda ASIC/WSI y Gate P0.
5. `03-EXPERIMENTOS/` — datos, manifiestos, telemetría y resultados; las rutas históricas conservan contexto.
6. `01-AUDITORIA/FASE-R1-*`, `FASE-R2-*`, `FASE-R3-*` — reconciliación, diseño y auditorías documentales.

Si una fuente histórica contradice una Addenda o el Gate P0, se conserva la frase histórica y se aplica la precedencia indicada arriba. No se sobrescribe evidencia.

## Archivos de este paquete

- `C1-TECHNICAL-RECORD.md` — registro técnico principal.
- `README.md` — este índice, alcance y fronteras.
- `DOCUMENT-HASHES.txt` — hashes de los documentos nuevos, calculado después de la redacción.

## Fronteras de esta actualización

No se ejecutó C1, `--run`, benchmark, observer real, test runner, `sudo`, `systemctl`, UMR, RGP, radeontop, modificación de RX550/Mesa/PM/DPM/sysfs/servicios, ni modificación de código funcional, tests, manifiestos o hashes existentes. Sólo se leyeron estructura, código fuente, evidencia y provenance.

## Estado exigido por el proyecto

```text
CODE_MODIFIED=YES
TESTS=PASS
PREPARE=PASS
DRY_RUN=PASS
NO_SYSTEM_CHANGES=YES
C1_EXECUTED=NO
C1_RUNTIME_VALIDATED=NO
READY_FOR_EXECUTION=NO
C1_STATUS=DEFERRED
PERSISTENT_SYSTEM_CHANGES=NONE
UNITS_STOPPED=NONE
AUTOMATIC_RETRY=DISABLED
```

`NO_SYSTEM_CHANGES=YES` y `UNITS_STOPPED=NONE` se refieren a la validación v1.1.0 y al estado C1 actual; no niegan las escrituras históricas autorizadas de cap documentadas en otros experimentos ni el hecho de que el run legacy registrado haya autenticado sudo antes de fallar.
