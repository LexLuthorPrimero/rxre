# ARCHIVE — F02-P0-2026-11-15 (RXRE)

POC histórico del caso F-02 (esquema SQLite persistido incompatible con `store.registrar()`: faltaban 8 columnas M281 — `declared_scope/authorized_scope/auth_decision/auth_actor/auth_timestamp` en `operations`; `verified_scope/scope_decision/limitations_json` en `results`). Construido 2026-11-15 17:35–17:38. Rescatado 2026-11-16 según dictamen del propietario.

## Estatus

**HISTÓRICO. NO OPERATIVO. NO RE-EJECUTAR COMO RUTA DE TRABAJO.**

- El POC demostró: el defecto F-02 es reproducible sobre copia sellada; la migración ALTERed 8 columnas resuelve sobre copia; el POC nunca tocó la DB protegida (`195f68fb25db674b41408ee8283df952b158528c9ccb58cdb1dc42b0810f8ef2`).
- La capacidad correspondiente está **integrada** en el canónico RXRE: reparación F-02 como `IER repair flow`, `core/store.py::_asegurar_columnas_m281()` ejecutado dentro de `conectar()`, cobertura en `ier/repair_flow.py`, `ier/investigate_f02.py`, `ier/lesson_f02.py` y `tools/rxre/tests/test_f02_repair_flow.py` / `test_f02_lesson.py`.

## Notas sobre el inventario

- `expected.json` es **snapshot histórico** pre-integración. Su campo `origin.sha256` (`195f68fb…`) coincide con la DB protegida (verificado al archivar). Su campo `contract_ddl.sha256` (`e9c0cc5f…`) **NO** coincide con `tools/rxre/core/store.py` vigente (`6d38ea1e…`); `store.py` tras la integración M281 necesariamente cambió. **No utilizar `expected.json` como oráculo** para ninguna operación futura.
- `reports/F02-20261115T173842.json` es el informe **citado por el ledger canónico** (`state/multiproject/log.md`, entrada 2026-11-15 F-02/P0): `sha256_manifest=fd58dccb…` y `sha256_verify_db=103a7aa1…`. Ambos valores coinciden EXACTAMENTE con este archivo al archivar (2026-11-16). Es la evidencia del run 2026-11-15T17:38.
- `reports/F02-20261115T173753.json` fue un run previo (superseded), no citado en el ledger; se preserva igualmente.
- `verifier/p0_verify.py`: verificador **independiente** del POC (no importa `p0` ni `core.store`; consulta DDL/queries leídas solamente). **No portar a `ier/` sin la auditoría de independencia y contrato que indicó el propietario** (2026-11-16). **No introduce segunda vía de reparación ni mutación** (auditado al archivar: ninguna operación de escritura sobre la DB; única conexión vía `sqlite3.connect(path)` lectura de PRAGMA/SELECTs).
- `rxre_evolve`: CLI histórico (subcomandos `investigate|repair|verify|report|all`). Ruta de trabajo obsoleta: duplicaba `ier/` y `api/machine.py`. Conservado solo por procedencia.
- `tests/test_p0.py`: 12 pruebas T01–T12 del POC; superadas en cobertura por `test_f02_repair_flow.py` y `test_f02_lesson.py` en el canónico. Se copian para procedencia, no como suite operativa.
- `MANIFEST.json`: sha256 por archivo y comparación byte a byte antes/después del rescate (14/14 idénticos).
- `p0/__pycache__/` NO archivado (desechable).

## Integridad verificada

- Comparación byte a byte origen (`B`) → archivo (`A/state/artifacts/…`): **14/14 idénticos**.
- `MANIFEST.json` y este anexo: generados durante la operación de rescate.
- Origen `B` (`/home/lucas/Escritorio/RXRE-EVOLUTION-ENGINE — P0/`) permanece **intacto y sin modificar** (hash de archivo preservado en copia). Eliminarlo requiere autorización explícita posterior; **no está autorizado todavía**.

*Autorización de rescate: bloque explícito del propietario (dictamen M10/F-02; "el siguiente texto puede utilizarse como autorización explícita para ejecutar únicamente el rescate"); ejecución 2026-11-16; límites respetados: sin borrado, sin mover/modificar B, sin portar verificador, sin tocar DB/protegidos/contratos/fixtures, sin commits ni publicación.*
