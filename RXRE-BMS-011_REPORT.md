# RXRE-BMS-011: INTEGRIDAD REFERENCIAL Y RECUPERACION DE FALLOS

**Fecha:** 2026-10-13
**Estado:** COMPLETE
**HEAD:** `d754f2c` en `main`

---

## FASE 0: Estado inicial del repositorio

### HEAD y rama
```
commit d754f2c (RXRE-1644: Add investigation planner capability)
rama: main
```

### git status --short (9 archivos modificados)
```
 M tools/rxre/backends/adapters/rz_callgraph.py
 M tools/rxre/backends/adapters/rz_findings.py
 M tools/rxre/backends/adapters/rz_xrefs.py
 M tools/rxre/backends/decision.json
 M tools/rxre/backends/dispatch.py
 M tools/rxre/backends/registry.py
 M tools/rxre/tests/test_backends004.py
 M tools/rxre/tests/test_dispatch004.py
 M tools/rxre/tests/test_xrefs1635.py
```

Working tree NO esta limpio — 9 archivos rastreados modificados (BMS-005 a BMS-011).
`RXRE-BMS-010_REPORT.md` existe (25135 bytes). `RXRE-BMS-011_REPORT.md` no existia.

### Confirmacion de correccion BMS-010
Verificado en diff: `except Exception as e:` presente en `crear_hallazgo` (linea 338).
`S.registro` -> `S.registrar` corregido. `_op_id` -> `op_id` corregido.

### Tests
Todas las 9 suites pasan (ver FASE 4).

---

## FASE 1: Reconstruir el contrato de integridad

### Flujo real mapeado
```
operacion origen (binary.inspect)
  -> store.registrar() -> operations.operation_id (op_id)
  -> store.registrar() -> results.result_id (con FK a operations.operation_id)
  -> recuperar_evidencia_resultados(result_ids) -> evidence dict {result, operation, op_id, ...}
  -> crear_hallazgo(claim, evidence_ids, op_id, ...)
  -> validacion: op_id en evidence? target match?
  -> _reclamar_estado_epistemico(evidencia, estado_reclamado)
  -> store.guardar_finding(finding_dict) -> findings.finding_id (con FK op_id -> operations)
  -> env["persistido"] = True (set by rz_findings.persistir)
  -> machine._handle_run -> response JSONL
  -> store.explicar(result_id) / recuperar_finding(finding_id) <- recovery
```

### Contrato de op_id
| Aspecto | Valor |
|---|---|
| Mandatory? | No — Optional[str] = None |
| Nullable en schema? | Si — findings.op_id TEXT REFERENCES operations(operation_id) (no NOT NULL) |
| Validado antes del INSERT? | Parcialmente — evidence cross-check |
| Validado por FK? | Si — PRAGMA foreign_keys=ON en conectar() |

### Contrato de FK
| Tabla | Columna | FK | NOT NULL? |
|---|---|---|---|
| results | operation_id | -> operations.operation_id | No |
| findings | op_id | -> operations.operation_id | No |
| finding_relations | source_id | -> findings.finding_id | Si |
| finding_relations | target_id | -> findings.finding_id | Si |

### Transacciones y WAL
- conectar(): PRAGMA journal_mode=WAL + PRAGMA foreign_keys=ON
- guardar_finding: single INSERT OR REPLACE + commit() — atomico
- relacionar_findings: single INSERT OR REPLACE + commit() — atomico
- registrar: INSERT operations -> INSERT results -> commit() — atomico
- Si INSERT falla: rollback implicito (commit no alcanzado)

### Analisis de las 8 preguntas
1. op_id optional/nullable — Sí
2. Rechazar invalid op_id antes del INSERT — Parcialmente (evidence cross-check), no explicito
3. FK habilitado — Sí
4. crear_hallazgo vs crear_relacion equivalentes — Parcialmente. crear_relacion valida source/target antes del INSERT (lineas 626-648). crear_hallazgo NO valida op_id — depende de FK.
5. IntegrityError puede representar otras restricciones — Sí (FK, NOT NULL, PRIMARY KEY, etc.)
6. Manejo distingue IntegrityError de OperationalError — No (ambos en except Exception)
7. Escritura fallida deja cambios parciales — No (transaccion atomica)
8. Respuesta mantiene contrato — Si, post-BMS-010

### Hipotesis causales
- **H1:** KeyError en `e["operation"]["op_id"]` cuando operacion es borrada (evidencia huérfana). `recuperar_evidencia_resultados` retorna `"operation": {}` — `e["operation"]["op_id"]` -> KeyError.
- **H2:** FK enabled impide borrado de operacion con resultados — escena imposible en operacion normal.
- **Discriminante:** `PRAGMA foreign_keys = OFF` + DELETE operacion -> observa KeyError. Con FK ON -> imposible.

---

## FASE 2: Experimentos discriminantes

### Experimento 1: Evidencia huérfana con op_id (confirma H1)
Setup: `binary.inspect` crea `op_abc` + `res_xxx`. Luego `PRAGMA foreign_keys=OFF` -> DELETE operacion. Luego `create_finding` con `op_id="op_abc"` + `evidence_ids=["res_xxx"]`.

**Antes del fix:**
```
status=error, persistido=False, finding_id=None
motivo: error creando hallazgo: 'op_id'
```
KeyError confirmado. H1 confirmada, H2 refutada.

**Después del fix:**
```
status=error, persistido=False, finding_id=None
motivo: la evidencia no pertenece a la operacion indicada (op_id mismatch)
```

### Experimento 2: Evidencia huérfana sin op_id (ejerce _reclamar_estado_epistemico)
**Antes del fix:**
```
status=error, motivo: error creando hallazgo: sequence item 0: expected str instance, NoneType found
```
TypeError en sorted(estados_evidencia) porque contiene None.

**Después del fix:**
```
status=ok, finding_id=finding_46f0c6052515b320
motivo: PROVEN requiere al menos un resultado de estado ok; su evidencia tiene:
epistemic: PARTIAL (downgradado de PROVEN)
```

### Experimento 3: op_id válido (baseline)
```
status=ok, persistido=True, finding_id=finding_xxx
```

### Experimento 4: op_id inexistente con evidence válida
```
status=error, motivo: la evidencia no pertenece a la operacion indicida (op_id mismatch)
```

### Experimento 5: Evidence inexistente
```
status=error, motivo: ninguno de los result_id de evidencia existe
```

### Experimento 6: sqlite3.OperationalError / IntegrityError (mock)
```
PASS: OperationalError caught: error creando hallazgo: database is locked
PASS: IntegrityError caught: error creando hallazgo: FOREIGN KEY violation
```

### Experimento 7: Recuperación entre procesos
JSONL usa subprocess.run — proceso nuevo por request. DB persiste (WAL). ✅

### Experimento 8: Regresión
```
  test_backends004: OK
  test_dispatch004: OK
  test_mission001: OK
  test_epistemic_distinctions: OK
  test_xrefs1635: OK
  test_callgraph1636: OK
  test_disasm1634: OK
  test_dependency008: OK
  test_integration: OK
=== 9/9 OK ===
```

---

## FASE 3: Decision sobre correccion

### Deficiencia demostrable
SÍ — KeyError `'op_id'` en `crear_hallazgo` (y TypeError derivado en `_reclamar_estado_epistemico`). La evidencia huérfana (operación borrada) produce:
1. Crash con mensaje confuso: "error creando hallazgo: 'op_id'"
2. TypeError: "sequence item 0: expected str instance, NoneType found"

### Fix aplicado (cambio minimo)
1. `e["operation"]["op_id"]` -> `e["op_id"]` (top-level field, siempre presente)
2. `e["operation"]["target"]` -> `e["operation"].get("target", "")`
3. `e["operation"]["status"]` -> `e["operation"].get("status")` + filtrado de None
4. Aplicado en: `crear_hallazgo` (lineas 214, 221, 242->257, 319-323), `_reclamar_estado_epistemico` (389, 405, 414), `listar_hallazgos` (496-499)

### No cambiado y por qué
- Validacion explicita de op_id antes del INSERT: No necesaria. Evidence cross-check + FK son suficientes. Mensaje "op_id mismatch" ya es preciso.
- Tabla audit_log: No hay evidencia de valor inmediato.
- Separacion IntegrityError vs OperationalError: No es critico para correctness actual.

---

## FASE 4: Validacion

### 4.1 Reproduccion antes del fix
```
motivo: error creando hallazgo: 'op_id'
>>> BUG CONFIRMED: KeyError 'op_id'
```

### 4.2 Correccion aplicada
Cambios en `tools/rxre/backends/adapters/rz_findings.py` — 4 patrones de acceso defensivo.

### 4.3 Verificacion JSONL
```
Test1 (orphan, no op_id): status=ok, finding_id=finding_46f0c6052515b320, epistemic=PARTIAL
Test2 (orphan, with op_id): status=error, motivo=op_id mismatch
```

### 4.4 Consulta independiente a DB
```
DB: 1 findings matching BMS-011 — finding persistido verificado por query directa
```

### 4.5 Casos limite
| Caso | Resultado |
|---|---|
| op_id valido + evidence valida | status=ok, persistido=True |
| op_id invalido + evidence valida | status=error, motivo=op_id mismatch |
| op_id nulo | status=ok, finding creado |
| evidence inexistente | status=error, motivo=ninguno de los result_id existe |
| evidence huérfana + op_id | status=error, motivo=op_id mismatch |
| evidence huérfana sin op_id | status=ok, epistemic=PARTIAL |
| sqlite3.OperationalError | status=error, motivo capturado |
| sqlite3.IntegrityError | status=error, motivo capturado |

### 4.6 Recuperacion entre procesos
JSONL usa subprocess — DB persiste (WAL). persistido verificado en respuesta + DB. ✅

### 4.7 Regresiones
9/9 suites OK. ✅

---

## FASE 5: Auditoria transversal

### CUERPO
Operacion real: `binary.inspect /bin/ls` -> `create_finding`. Finding escrito a DB, verificado por query. ✅

### MENTE
H1 (KeyError), H2 (FK imposibilita escena), H3 (TypeError) — todas validadas con experimentos discriminantes. ✅

### ALMA
Estado recuperable: DB persiste entre procesos (WAL). Finding con evidencia huérfana → epistemic downgrade. ✅

### TIERRA
op_id: Optional, nullable, FK a operations. Response contract: status, finding_id, persistido, motivo, epistemic — todos presentes. ✅

### FUEGO
Falla: KeyError TypeError. Fix: acceso defensivo. Revalidacion: 8 experimentos + 9 suites. ✅

### AIRE
```
PRODUCTOR: recuperar_evidencia_resultados (op deleted -> e["operation"]={})
TRANSFORMACION: crear_hallazgo (e["operation"]["op_id"] -> KeyError -> except Exception)
CONSUMIDOR: machine._handle_run -> procesar_linea
EFECTO: respuesta JSONL con motivo confuso

DESPUES: e["op_id"] -> None -> evidence filtered -> "op_id mismatch"
```

### AGUA
Procedencia: `e["op_id"]` seteado por `recuperar_evidencia_resultados` (linea 593). Integrity FK preserve. ✅

### ETER
Ciclo completo: EVIDENCIA -> SEMANTICA -> CLAIM -> MODELO -> IMPLEMENTACION -> VALIDACION -> RENDIMIENTO ✅
Siguiente accion: validar op_id explicitamente en operations antes del INSERT.

---

## FASE 6: GLOBAL WORK SCAN

| Frontera | Estado | Prioridad |
|---|---|---|
| KeyError en evidencia huérfana | VERIFIED -> FIXED | Alta |
| TypeError en _reclamar_estado_epistemico | VERIFIED -> FIXED | Alta |
| op_id FK validation explicita | Abierta | Media-Alta |
| Separacion IntegrityError vs OperationalError | Abierta | Baja |
| Tabla audit_log | Abierta | Baja |
| plan_investigation tool_capability dinámico | Abierta | Media |

### Siguiente accion priorizada
**Agregar validacion explicita de op_id en operations antes del INSERT en crear_hallazgo.**

Razon: Consistencia con crear_relacion (valida source/target), diagnostico preciso ("op_id no existe" vs "op_id mismatch"), defense-in-depth.

---

## Diferencias del repositorio (BMS-011)

Cambios en `tools/rxre/backends/adapters/rz_findings.py`:
- `e["operation"]["op_id"]` -> `e["op_id"]` (3 sites)
- `e["operation"]["target"]` -> `e["operation"].get("target", "")` (1 site)
- `e["operation"]["status"]` -> `e["operation"].get("status")` + filter None (4 sites)

---

*BMS-011 complete. 9/9 test suites pass. KeyError/TypeError en crear_hallazgo corregidos — evidencia huérfana ahora produce respuestas estructuradas con mensajes de error precisos.*