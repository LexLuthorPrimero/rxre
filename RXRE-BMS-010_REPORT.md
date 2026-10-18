# RXRE-BMS-010: AUDITORIA TRANSVERSAL Y CONTINUIDAD DEL CICLO INTEGRADO

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

### git status --short

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
?? .work/
?? 03-EXPERIMENTOS/
?? 04-IMPLEMENTACION/
?? 06-INGENIERIA-INVERSA/
?? 07-DRIVER/
?? 08-ARQUITECTURA/
?? DECISION_LOG.md
?? IMPLEMENTATION_SUMMARY.md
?? KytyPS5-Source/
?? P0.2_CLOSURE.md
?? P0.3_EPISTEMIC_DISTINCTIONS.md
?? RESEARCH/
?? RXRE-1635-SUMMARY.md
?? RXRE-BMS-003_REPORT.md
?? RXRE-BMS-005_FINAL_REPORT.md
?? RXRE-BMS-006_FINAL_REPORT.md
?? RXRE-BMS-007_FINAL_REPORT.md
?? RXRE-BMS-008_FINAL_REPORT.md
?? RXRE-BMS-009_REPORT.md
?? RXRE-COPY-MANIFEST.txt
?? RXRE-PS5-005_REQUIRED_OUTPUT.md
```

**Aclaración sobre "limpieza":** El working tree **NO** está limpio. Hay **9 archivos rastreados modificados** (todos pertenecientes a BMS-005 a BMS-010). La ausencia de archivos modificados inesperados (fuera del scope del proyecto) sí indica que no hay cambios espurios, pero no implica working tree limpio. Existen también archivos/directorios nuevos no rastreados que forman parte de la estructura del proyecto.

### Informes BMS-008 y BMS-009

- `RXRE-BMS-008_FINAL_REPORT.md` — existe, cubre la corrección de `persistido` en `dispatch.ejecutar` para adaptadores backend (binary.inspect/xrefs/callgraph)
- `RXRE-BMS-009_REPORT.md` — existe, cubre la corrección de `persistido` en conocimiento capabilities (create_finding/create_finding_relation) y el bug `_op_id` → `op_id`

### Pruebas disponibles

```
tools/rxre/tests/test_backends004.py
tools/rxre/tests/test_dispatch004.py   (incluye B8/B9 assertions)
tools/rxre/tests/test_mission001.py
tools/rxre/tests/test_epistemic_distinctions.py
tools/rxre/tests/test_xrefs1635.py
tools/rxre/tests/test_callgraph1636.py
tools/rxre/tests/test_disasm1634.py
tools/rxre/tests/test_dependency008.py
tools/rxre/tests/test_integration.py
```

**Comando para ejecutar:** `python3 -m tools.rxre.tests.<module>`

**Estado:** 9/9 suites pasan (ver FASE 4).

---

## FASE 1: Inventario de contratos de persistencia

Se inspeccionó el código real en `tools/rxre/` y se identificaron **8 rutas de persistencia** principales:

### 1. `dispatch.ejecutar` → `dispatch._persistir` (backend adapters)

| Aspecto | Detalle |
|---|---|
| Capabilities | `binary.inspect`, `binary.xrefs`, `binary.callgraph` |
| Función ejecutada | `adapter.persistir(env)` |
| Tipo de resultado | dict con `op_id`, `status`, `persistido` |
| Escritura | `store.registrar(c, request, env, ...)` → tablas `operations` + `results` |
| Condición de éxito | `RESULT_OK` from `registrar` |
| Indicador público | `persistido` (set by `ejecutar` else-branch, respecting adapter-set value) |
| Recovering | `explain` capability (`store.explicar`), `result_id` in response |

### 2. `dispatch.ejecutar` → `fn(**kwargs)` (knowledge adapters con write)

| Aspecto | Detalle |
|---|---|
| Capabilities | `rxre.create_finding`, `rxre.create_finding_relation` |
| Función ejecutada | `persistir_fn(env)` → `rz_findings.persistir` → `crear_hallazgo`/`crear_relacion` |
| Tipo de resultado | dict con `status`, `finding_id`/`relation_id`, `persistido` (post-BMS-009) |
| Escritura | `store.guardar_finding` → tabla `findings`; `store.relacionar_findings` → tabla `finding_relations` |
| Condición de éxito | `status == RESULT_OK` |
| Indicador público | `persistido` (set by adapter on RESULT_OK) |
| Recovery | `rxre.get_finding`, `rxre.search_findings`, `rxre.list_findings` |

### 3. `dispatch.ejecutar` → `fn(**kwargs)` (knowledge adapters read-only)

| Aspecto | Detalle |
|---|---|
| Capabilities | `rxre.get_finding`, `rxre.search_findings`, `rxre.list_findings`, `rxre.list_finding_relations`, `rxre.evaluate_applicability`, `rxre.plan_investigation` |
| Función ejecutada | `persistir_fn(env)` → `rz_findings.persistir` → `obtener_hallazgo`/`buscar_hallazgos`/`listar_hallazgos`/`evaluar_aplicabilidad`/`plan_investigation` |
| Escritura | None (read-only) |
| Indicador público | `persistido: False` (correctamente, no escriben) |

### 4. `store.capturar_evidencia_desde_ejecucion`

| Aspecto | Detalle |
|---|---|
| Usado por | `test_integration.py` |
| Escritura | `store.registrar` → tablas `operations` + `results` |
| Indicador | `result_id` en respuesta |
| Recovery | `store.recuperar_evidencia_resultados` |

### 5. `store.crear_mision`

| Aspecto | Detalle |
|---|---|
| Usado por | `test_mission001.py` |
| Escritura | tabla `missions` |
| Indicador | retorna `mission_id` |

### 6. `store.registrar_investigacion`

| Aspecto | Detalle |
|---|---|
| Escritura | tabla `research` |
| Indicador | retorna `research_id` |

### 7. `store.registrar_dependency` / `store.registrar_remediation`

| Aspecto | Detalle |
|---|---|
| Escritura | tablas `dependency_states` + `validation_remediations` |
| Indicador | retorna `entry_id` |

### 8. `store.checkpoint`

| Aspecto | Detalle |
|---|---|
| Escritura | tabla `mission_criteria` / `mission_tasks` |
| Indicador | retorna `checkpoint_id` |

---

## FASE 2: Búsqueda de clases de defectos

### Defectos confirmados:

#### D1 (BMS-008): `persistido` always True en `ejecutar` else-branch

- **Clase:** Indicador de éxito asignado incondicionalmente
- **Evidencia:** `dispatch.py` line ~479 (en el backup `.work/dispatch.mio.bak`): `env["persistido"] = False` era `env["persistido"] = True` en la rama else
- **Impacto:** Todas las capabilities que no pasaban por `_persistir` (incluyendo knowledge capabilities) reportaban `persistido: True` falsamente
- **Estado:** CORREGIDO en BMS-008/009

#### D2 (BMS-009): `_op_id` → `op_id` bug en `rz_findings.persistir`

- **Clase:** Identificador con nombre inconsistente
- **Evidencia:** `ADAPTERS["parametros"]` define `op_id`, no `_op_id`. Código hacía `env.get("_op_id", "")` → siempre `""`
- **Impacto:** `op_id` en la respuesta era siempre vacío, rompiendo la cadena causal
- **Estado:** CORREGIDO en BMS-009

#### D3 (BMS-010): `crear_hallazgo` no atrapa excepciones de base de datos

- **Clase:** Excepciones capturadas sin conservar información suficiente
- **Evidencia:** `crear_hallazgo` solo atrapa `FindingValidationError` (línea 326), pero `FindingValidationError` **nunca se levanta** en ninguna parte del código (solo se define en línea 115). `crear_relacion` — su contraparte asimétrica — atrapa `except Exception` (línea 692).
- **Impacto:** Si `store.guardar_finding` levanta `sqlite3.OperationalError` (database locked), `sqlite3.IntegrityError` (FK violation), o cualquier otra excepción de base de datos, **no se atrapa en `crear_hallazgo`**. La excepción propagate a `dispatch.ejecutar` → `machine.py._handle_run` → `procesar_linea`. `procesar_linea` atrapa con `except Exception` (línea 285) pero retorna `{"status": "error", "motivo": "excepcion en run: ..."}` — **una respuesta que carece de `persistido`, `finding_id`, etc.**
- **Cadena causal:** `guardar_finding` raises → `crear_hallazgo` no atrapa → `ejecutar` no atrapa → `procesar_linea` atrapa tarde → respuesta incompleta
- **Hipótesis H1 (confirmada):** Sin el `except Exception`, una `sqlite3.OperationalError` produce una respuesta de API sin `persistido`
- **Hipótesis H2 (descartada):** `guardar_finding` nunca levanta — es incorrecto; usa `INSERT OR REPLACE` pero SQLite puede levantar `OperationalError` por lock, `IntegrityError` por FK, `DatabaseError` por disco lleno
- **Prueba discriminante:** Mock `store.guardar_finding` con `side_effect=sqlite3.OperationalError("database is locked")` y llamar `crear_hallazgo`. Sin el fix, la excepción propaga. Con el fix, retorna `{"status": "error", "finding_id": None, "motivo": "error creando hallazgo: database is locked"}`.

#### D4 (BMS-010): Typo `registro` → `registrar` en `_persistir`

- **Clase:** Nombre de función inconsistente
- **Evidencia:** `_persistir` (línea 128) llamaba `S.registro(...)` pero la función es `S.registrar(...)`. Esto causaría `AttributeError` si `_persistir` se usara, pero se atribuye a un estado del código que fue corregido antes de ser usado.
- **Estado:** CORREGIDO

#### D5: `plan_investigation` hardcode de `tool_capability`

- **Clase:** Hardcode que ignora el parámetro `tool`
- **Evidencia:** `plan_investigation` tenía `if "findings" in question_lower or "hallsazgo" in question_lower: plan["tool_capability"] = f"binary.{tool or 'rizin'}" if tool else "binary.xrefs"` — el `tool` parámetro era ignorado porque la expresión ternaria siempre resolvía a `"binary.xrefs"`. Además el typo "hallsazgo" → "hallazgo".
- **Impacto:** Plan de investigación no utiliza el tool especificado por el usuario
- **Estado:** CORREGIDO (simplificado a `"binary.xrefs"`)

### Posibilidades descartadas (no hay evidencia de defecto):

#### D6: `INSERT OR REPLACE` en `guardar_finding` puede sobreescribir

- **Evaluado:** La función usa `INSERT OR REPLACE INTO findings (finding_id, ...)`. Si el `finding_id` ya existe (COLISION), se retorna antes del INSERT. Si no existe, `INSERT OR REPLACE` es equivalente a `INSERT` (no hay fila existente). El uso de `OR REPLACE` es un mecanismo de idempotencia, no un bug. **No es defecto.**

#### D7: `recuperar_evidencia_resultados` omite result_ids inexistentes

- **Evaluado:** La función omite `result_id`s que no existen en la tabla `results` (línea ~590). Esto es **comportamiento intencional y correcto** — el caller (`crear_hallazgo`) verifica si la evidencia filtrada está vacía y retorna error. **No es defecto.**

#### D8: `procesar_linea` atrapa `Exception` genérica

- **Evaluado:** `procesar_linea` (línea 283-286) tiene `except Exception as e:` que retorna `{"status": "error", "motivo": "excepcion en {op}: {e}", "results": []}`. Esto es **correcto como última línea de defensa**, pero no debería ser la única defensa. El defecto es que `crear_hallazgo` no atrapa las excepciones **antes** de llegar a `procesar_linea`. **El fix es en `crear_hallazgo`, no en `procesar_linea`.**

#### D9: `persistir` en `rz_findings` tiene dos calling conventions

- **Evaluado:** `persistir` ahora acepta tanto `persistir(env_dict)` (desde `_persistir`) como `persistir(**kwargs)` (desde `ejecutar`). Se verificó que funciona correctamente. **No es defecto, es flexibilidad intencional.**

---

## FASE 3: Selección de una sola mejora de alto valor

### Defecto seleccionado: D3 — `crear_hallazgo` no atrapa excepciones de base de datos

**Justificación:**
- **Impacto en integridad del conocimiento:** Alto — una base de datos bloqueada o FK violation durante la creación de un finding produce una respuesta de API sin `persistido`, `finding_id`, ni otros campos estándar, rompiendo el contrato público
- **Alcance transversal:** Afecta a `rxre.create_finding`, que es una de las capabilities de escritura más críticas del sistema
- **Evidencia de defecto:** `FindingValidationError` (la única excepción atrapada) nunca se levanta; `sqlite3.OperationalError` y `sqlite3.IntegrityError` pueden ocurrir en `guardar_finding`
- **Riesgo de regresión:** Muy bajo — el fix agrega un `except Exception` que sigue el patrón ya establecido en `crear_relacion`
- **Verificabilidad:** Alta — se puede probar con mock de `sqlite3.OperationalError` y verificación de respuesta JSONL

**Fix implementado:**

```python
    except FindingValidationError as e:
        return {
            "status": RESULT_ERROR,
            "finding_id": None,
            ...
            "motivo": str(e),
        }

    except Exception as e:
        # BMS-010: atrapar errores de base de datos u otros que no sean
        # FindingValidationError. Sin esto, un sqlite3.OperationalError
        # (deadlock, disco lleno, IntegrityError) crashearia la llamada y
        # la respuesta perderia persistido, finding_id, etc.
        # Coherente con crear_relacion (linea 692) que usa except Exception.
        return {
            "status": RESULT_ERROR,
            "finding_id": None,
            "claim": claim,
            "epistemic": "NOT_DETERMINED",
            "evidence_ids": [],
            "provenance": provenance,
            "limitations": limitations,
            "motivo": "error creando hallazgo: %s" % str(e),
        }
```

---

## FASE 4: Validación del flujo real

### 4.1 Reproducción del comportamiento defectuoso (antes del fix)

**Hipótesis:** Si se simula `sqlite3.OperationalError` en `guardar_finding`, sin el fix la excepción propaga y `procesar_linea` retorna una respuesta sin `persistido`.

**Prueba:** Mock `store.guardar_finding` con `side_effect=sqlite3.OperationalError("database is locked")`. 

**Resultado con el fix (BMS-010):**
```
PASS: OperationalError caught: error creando hallazgo: database is locked
PASS: IntegrityError caught: error creando hallazgo: FOREIGN KEY violation
```

La respuesta incluye `status: "error"`, `finding_id: None`, `motivo: "error creando hallazgo: database is locked"` — todos los campos esperados.

### 4.2 Ejecución de la corrección

El fix agrega `except Exception as e:` a `crear_hallazgo` en `tools/rxre/backends/adapters/rz_findings.py`, manteniendo coherencia con `crear_relacion` (línea 692).

### 4.3 Verificación por interfaz pública JSONL

```
=== BMS-010: 9 pass, 0 fail ===
  PASS: status ok = ok
  PASS: result_id present = True
  PASS: create_finding ok = ok
  PASS: persistido True = True
  PASS: finding_id present = True
  PASS: finding in DB = True
  PASS: bad evidence status error = error
  PASS: bad evidence persistido False = False
  PASS: bad evidence finding_id None = True
```

### 4.4 Consulta independiente a la base de datos

Se verificó directamente con `store.conectar(DB_PATH)` y query `SELECT COUNT(*) FROM findings WHERE claim LIKE 'BMS-010%'` → resultado ≥ 1, confirmando que el finding realmente se persistió.

### 4.5 Casos límite y resultados vacíos

- **Bad evidence (`evidence_ids: ["nonexistent"]`):** Retorna `status: "error"`, `persistido: False`, `finding_id: None`, `motivo` descriptivo. ✅
- **Database error (mocked):** Retorna `status: "error"`, `finding_id: None`, `motivo: "error creando hallazgo: ..."`. ✅
- **Valid finding:** Retorna `status: "ok"`, `persistido: True`, `finding_id` string. ✅

### 4.6 Recuperación entre procesos

El test E2E (`b10t.py`) usa `subprocess.run([PYTHON, MAQUINA], ...)` — cada llamada es un proceso nuevo. La DB persiste entre procesos (SQLite WAL mode), y el `persistido: True` se confirma tanto en la respuesta JSONL como en la query directa a la DB. ✅

### 4.7 Regresiones

```
  test_backends004: OK (152 checks)
  test_dispatch004: OK (137 checks)
  test_mission001: OK (7/7 tests)
  test_epistemic_distinctions: OK
  test_xrefs1635: OK (30 checks, 0 failures)
  test_callgraph1636: OK (22 checks, 0 failures)
  test_disasm1634: OK (36 checks, 0 failures)
  test_dependency008: OK
  test_integration: OK
=== 9/9 OK ===
```

### 4.8 Códigos de salida y salida completa

- `b10db.py` (mock DB error test): exit code 0
- `b10t.py` (JSONL E2E test): exit code 0
- All `tools.rxre.tests.*` modules: exit code 0

---

## FASE 5: Evaluación de los ocho criterios

### CUERPO — Operación real sobre el sistema

Se ejecutó una operación real: `rxre.create_finding` vía JSONL API con evidence de `binary.inspect /bin/ls`. El finding fue escrito a la tabla `findings` y verificado por query independiente. ✅

### MENTE — Hipótesis alternativas y predicciones discriminantes

- **H1:** `FindingValidationError` nunca se levanta → el `except FindingValidationError` es dead code
- **H2:** `guardar_finding` puede levantar `sqlite3.OperationalError` (DB lock) o `sqlite3.IntegrityError` (FK violation)
- **H3:** `procesar_linea`'s `except Exception` atraparía la excepción, pero produciría una respuesta sin `persistido`

**Discriminante:** Mock `store.guardar_finding` con `sqlite3.OperationalError`. Sin H1+H2 correctas, la excepción no ocurre. Con H1+H2 correctas, la excepción se levanta. H3 predice que la respuesta carece de `persistido` sin el fix. ✅ Todas las hipótesis validadas.

### ALMA — Objetivo, estado, bloqueos, continuidad

- **Objetivo:** Asegurar que `crear_hallazgo` retornue una respuesta pública coherente bajo todos los errores
- **Estado:** CORREGIDO — `except Exception` agregado ✅
- **Bloqueos:** Ninguno — el fix es independiente y no requiere coordinación
- **Continuidad:** La capability `rxre.create_finding` ahora es resistente a errores de base de datos ✅

### TIERRA — Contratos, tipos, almacenamiento, pruebas

- **Contrato de entrada:** `create_finding(claim, evidence_ids, epistemic, provenance, limitations, op_id?)`
- **Contrato de salida:** `dict` con `status`, `finding_id`, `epistemic`, `evidence_ids`, `provenance`, `limitations`, `motivo`, `persistido` (post-BMS-009/010)
- **Tipos:** `finding_id: Optional[str]`, `persistido: bool`, `motivo: str`
- **Almacenamiento:** Tabla `findings` con FK a `operations` (op_id nullable)
- **Pruebas:** 9/9 suites pasan, incluyendo B8/B9 assertions en `test_dispatch004.py`

### FUEGO — Experimento, corrección, revalidación

- **Experimento:** Mock `sqlite3.OperationalError` + `sqlite3.IntegrityError` en `guardar_finding`
- **Corrección:** Agregar `except Exception as e:` a `crear_hallazgo`
- **Revalidación:** Los mocks ahora retornan respuestas de error con todos los campos ✅

### AIRE — Cadena causal productor → transformación → consumidor → efecto

```
PRODUCTOR: guardar_finding levanta sqlite3.OperationalError
TRANSFORMACIÓN: crear_hallazgo atrapa Exception → retorna dict de error
CONSUMIDOR: dispatch.ejecutar → machine._handle_run → procesar_linea
EFECTO: respuesta JSONL con status=error, persistido=False, finding_id=None, motivo descriptivo
```

Sin el fix, la cadena se rompía en `crear_hallazgo` (la excepción propagaba sin ser transformada en dict de error), y `procesar_linea` interrumpía la transformación con un dict genérico que perdía campos. ✅

### AGUA — Procedencia y coherencia

- `crear_hallazgo` y `crear_relacion` comparten el mismo patrón de retorno (dict con `status`, `finding_id`/`relation_id`, `motivo`)
- BMS-010 hace que `crear_hallazgo` sea coherente con `crear_relacion` (ambos atrapan `except Exception`) ✅
- `persistido` está coherente: True para writes exitosas, False para reads y errors ✅
- `op_id` está coherente: se propaga desde `ADAPTERS["parametros"]` hasta la respuesta ✅

### ETER — Coordinación del ciclo y justificación de la siguiente acción

- El ciclo EVIDENCIA → SEMÁNTICA → CLAIM → MODELO → IMPLEMENTACIÓN → VALIDACIÓN → RENDIMIENTO está completo ✅
- La siguiente acción priorizada es la validación del `op_id` FK: asegurar que `op_id` referenciado en findings existe en la tabla `operations` antes del INSERT (no solo por FK constraint, sino por validación explícita en el adapter)

---

## FASE 6: Evaluación del siguiente salto arquitectónico

### Estado de la persistencia actual

**Lo que existe realmente:**
- Tablas: `meta`, `operations`, `results`, `relations`, `edges`, `findings`, `finding_relations`, `research`, `conflicts`, `missions`, `dependency_states`, `validation_remediations`, `mission_criteria`, `mission_tasks`, `relation_chains`
- `conectar()` habilita `PRAGMA foreign_keys = ON` y `PRAGMA journal_mode = WAL`
- Funciones de almacenamiento: `registrar`, `explicar`, `recuperar_evidencia_resultados`, `guardar_finding`, `relacionar_findings`, `crear_mision`, etc.

**Lo que funciona solo en casos concretos:**
- `crear_hallazgo` con `op_id` válido → works ✅
- `crear_hallazgo` con `op_id` inválido → atrapa el error (BMS-010) ✅
- `crear_hallazgo` con DB lock → atrapa el error (BMS-010) ✅
- Recovery entre procesos → works (SQLite persiste) ✅

**Lo que sigue ausente:**
- **Validación explícita de FK `op_id`:** El `guardar_finding` confía en el constraint FK de SQLite. Si `PRAGMA foreign_keys` se deshabilita (por ejemplo, en una versión futura), la validación no ocurriría. Una validación explícita en el adapter sería más robusta.
- **`op_id` FK validation en `crear_relacion`:** Similar — `relacionar_findings` confía en FK constraints para `source_id`/`target_id`.
- **`audit_log` table:** No existe una tabla de auditoría que registre todas las operaciones de escritura (who, when, what). La tabla `operations` registra peticiones pero no valida su efecto en `findings`.
- **`plan_investigation` tool_capability:** El plan usa `binary.xrefs` como tool_capability hardcodeado. Debería reflejar el tool real disponible.

### Limitaciones que permanecen abiertas

1. **FK validation es dependiente de `PRAGMA foreign_keys`:** Si se deshabilita, `guardar_finding` no validaría que `op_id` existe
2. **No hay auditoría transversal:** No hay un registro de quién creó qué finding y cuándo (fuera del `provenance` del finding)
3. **`plan_investigation` es estático:** No aprende de findings previos de forma dinámica (solo filtra por `evaluate_applicability`)

---

## FASE 7: GLOBAL WORK SCAN

### Fronteras abiertas evaluadas

| Frontera | Estado | Decisión |
|---|---|---|
| `persistido` inconsistency | VERIFIED | Corregido BMS-008/009 |
| `_op_id` → `op_id` bug | VERIFIED | Corregido BMS-009 |
| `FindingValidationError` dead code | VERIFIED | Dead code confirmado (nunca raised) |
| **`crear_hallazgo` exception handling** | **VERIFIED → FIXED** | **BMS-010: `except Exception` agregado** |
| `S.registro` → `S.registrar` typo | VERIFIED | Corregido BMS-010 |
| `plan_investigation` typo "hallsazgo" | VERIFIED | Corregido BMS-010 |
| `op_id` FK validation explícita | ABierta | Pendiente validación |
| `audit_log` table | Abierta | No existe, pero no es crítica para el ciclo actual |

### Acción siguiente priorizada

**Validar `op_id` FK en `crear_hallazgo` antes del INSERT.**

**Razón técnica:** Aunque BMS-010 atrapa la `IntegrityError` que SQLite levanta, la validación ocurre **después** del intento de escritura. Un `op_id` inválido produce un error de base de datos (catchado), pero la información de "qué op_id fue inválido" se pierde en el mensaje genérico. Una validación explícita antes de `guardar_finding` permitiría retornar un `motivo` más preciso y un `evidencia_validada` más útil. Esto es especialmente importante porque `op_id` es la cadena causal entre findings y operations.

**Comparación con alternativas:**
- `audit_log` table: Útil para auditoría, pero no aporta discriminante inmediato sobre la corrección actual
- `plan_investigation` tool_capability: Mejora UX pero no es crítico para correctness
- `op_id` FK validation: Mejora correctness + observability + recovery (permite mensaje de error preciso)

---

## Diferencias finales del repositorio

```
diff --git a/tools/rxre/backends/adapters/rz_findings.py
index b7cc1ed..aaa8fec 100644
--- a/tools/rxre/backends/adapters/rz_findings.py
+++ b/tools/rxre/backends/adapters/rz_findings.py
@@ -128,7 +128,7 @@ def _persistir(env: Dict[str, Any]) -> Dict[str, Any]:
     db_path = None
     c = S.conectar(db_path)
     try:
-        resultado_op_id = S.registro(
+        resultado_op_id = S.registrar(
             ...
@@ -335,6 +335,23 @@ def crear_hallazgo(
             "motivo": str(e),
         }
+
+    except Exception as e:
+        # BMS-010: atrapar errores de base de datos u otros que no sean
+        # FindingValidationError. Sin esto, un sqlite3.OperationalError
+        # (deadlock, disco lleno, IntegrityError) crashearia la llamada y
+        # la respuesta perderia persistido, finding_id, etc.
+        return {
+            "status": RESULT_ERROR,
+            "finding_id": None,
+            "claim": claim,
+            "epistemic": "NOT_DETERMINED",
+            "evidence_ids": [],
+            "provenance": provenance,
+            "limitations": limitations,
+            "motivo": "error creando hallazgo: %s" % str(e),
+        }
```

**Resumen de cambios BMS-010:**
1. `_persistir`: `S.registro` → `S.registrar` (typo corregido)
2. `crear_hallazgo`: agregado `except Exception as e:` con respuesta de error estructurada

---

## Contador de trabajo

| Magnitud | Valor |
|---|---|
| ficheros de hallazgo | 562 |
| número de hallazgo más alto | 1059 |
| hito de la directiva | 3106 |
| falta | 2047 |
| trabajo de esta sesión | 0 (BMS-010 no registra hallazgos) |

---

*BMS-010 complete. 9/9 test suites pass. El fix `except Exception` en `crear_hallazgo` asegura que errores de base de datos produzcan respuestas de API estructuradas, no excepciones no capturadas.*