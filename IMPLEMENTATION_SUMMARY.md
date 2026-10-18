# IMPLEMENTATION SUMMARY: RXRE-008 Dependency-Aware Validation

## Capacidad implementada:

### 1. **Schemas** (store.py, DDL)

#### dependency_states
- `dep_id`: TEXT PRIMARY KEY (IDENTIFIER CITABLE)
- `target`: TEXT NOT NULL (VALIDATION_GOAL / TEST_TARGET)
- `name`: TEXT NOT NULL (DEPENDENCY_NAME, ej. SDL3, libX11)
- `state`: TEXT NOT NULL (MISSING | SATISFIED | OPTIONAL | NOT_DETERMINED)
- `required`: INTEGER DEFAULT 1 (1=obligatorio, 0=opcional)
- `diagnostic`: TEXT (error OBSERVADO del CMake, rpm, dnf, etc.)
- `source`: TEXT (ubicación del diagnóstico, ej. archivo/ruta del log)
- `context`: TEXT (JSON con revision, compiler, cmake flags, entorno de hw/sw)
- `validated_by`: TEXT (operation_id o result_id que lo verificó)
- `recorded_at`: TEXT NOT NULL (momento del registro)

**Restricciones CHECK**:
- `CHECK (state IN ('MISSING', 'SATISFIED', 'OPTIONAL', 'NOT_DETERMINED'))`
- `CHECK (required IN (0, 1))`

#### validation_remediations
- `rem_id`: TEXT PRIMARY KEY (IDENTIFIER CITABLE)
- `target`: TEXT NOT NULL (misma validacion)
- `dep_id`: TEXT REFERENCES dependency_states(dep_id)
- `remediation`: TEXT NOT NULL (acción, ej. "dnf install -y SDL3-devel")
- `remediation_type`: TEXT (INSTALL | CONFIGURE | UPDATE | SKIP | DONT_APPLY)
- `attempted`: INTEGER DEFAULT 0 (0=propuesta, 1=ejecutada)
- `attempted_at`: TEXT (momento de la ejecución)
- `verified`: INTEGER DEFAULT 0 (0=no verificado, 1=verificado)
- `verification_result`: TEXT (RESOLVED | FAILED | PENDING)
- `verification_at`: TEXT (momento de la verificación)
- `verification_evidence`: TEXT (result_id que verificó la remediación)
- `recorded_at`: TEXT NOT NULL

### 2. **Funciones públicas** (store.py)

#### registrar_dependency
`def registrar_dependency(c, target, name, state, required=True, diagnostic=None, source=None, context=None, validated_by=None)`
- REGISTRA UNA DEPENDENCIA CONDICIONADA.
- Conserva el DIAGNOSTICO OBSERVADO completo y el CONTEXTO irrepetible.
- Permite estados MISSING, SATISFIED, OPTIONAL, NOT_DETERMINED.
- Actualiza el estado cuando verified_by + verification_result se registran.

#### registrar_remediation
`def registrar_remediation(c, dep_id, remediation, remediation_type='INSTALL', target=None)`
- PROPONE o REGISTRA una acción de REMEDIACIÓN.
- Attempted=False inicialmente.
- Vincula la remediación al dep_id y target.

#### marcar_remediation_completada
`def marcar_remediation_completada(c, rem_id, verification_result, verification_evidence=None)`
- MARCA una remediation como intentada/verificada con un RESULTADO y EVIDENCIA independientes.
- Si verification_result == 'RESOLVED' AND verification_evidence != None, actualiza el estado de la dependency a SATISFIED y valida_by.
- Rechaza estados sin evidencia: una remediación RESOLVED sin verification_evidence NO cambia la dependencia a SATISFIED.

#### query_validation_chain
`def query_validation_chain(c, target=None, dep_name=None, state=None)`
- RECUPERA la cadena: dependency -> remediation -> verification_result.
- Permite filtros por target, nombre de dependency, estado.
- Devuelve un Dict con limitations y una lista de dependencias, cada una con:
  - dep_id, name, state, required, diagnostic, source, recorded_at
  - remediation (rem_id, remediation, remediation_type, attempted, verification_result, evidence, rem_recorded_at)
  - verified, verification_result, evidence

### 3. **Notas de diseño**

#### DISTINCIÓN EPSTEMICA
- MISSING ≠ SATISFIED ≠ OPTIONAL ≠ NOT_DETERMINED
- MISSING → SATISFIED SOLO por verification_result == 'RESOLVED' + verification_evidence
- RESOLVED sin verification_evidence deja a la dependency MISSING (cadena incompleta)

#### CONTEXTO EVIDENCIA
- El campo `context` (JSON) es esencial para reutilización.
- Una dependency sin contexto es basura reutilizable: la misma "libX11" puede ser MISSING en una máquina y SATISFIED en otra.
- La verificación de contexto es responsabilidad del consumidor.

#### DISTINCIÓN DE CADENA
- La cadena VALIDATION -> DEPENDENCY -> REMEDIATION -> EXECUTION_RESULT es recuperable por target.
- DISTINGUE:
  - BLOCKED: dependency MISSING, remediation pendiente (attempted=False / verification_result=PENDENT)
  - FALLADO: dependency SATISFIED pero verification_result == 'FAILED' (ej. intento de instalación falló)
  - NO-EJECUTADO: target no mencionado (no hay dependencia con este target)
  - RESUELTO: dependency SATISFIED + verification_result == 'RESOLVED' + verification_evidence presente

#### REDUNDANCIA EVIDENCE
- La verificación es independiente: result_id (ej. rc=0 de dnf, CMake.success) viaja con el verification_result y verification_evidence.
- Permite evidenciar "por qué se resolvió" con un productor diferente del que propuso la remediación.

### 4. **Prueba unitaria** (test_dependency008.py)

#### TESTS PRINCIPALES:
1. **Dependency MISSING**: registrada con target, diagnostic, context.
2. **Remediation propuesta**: attempted=False mantiene MISSING.
3. **Remediation completada con evidencia**: dependency pasa a SATISFIED.
4. **RESOLVED sin evidencia**: la dependency permanece MISSING (cadena incompleta).
5. **Cadena completa**: recupera todas las dependencies y remediaciones.
6. **Filtrado**: filtra por target, dep_name, state.

#### CUMPLIMIENTO:
- Todos los assertions PASS.
- El test demuestra la distinción crítica BLOCKED vs. no-ejecutado.
- El test valida que MISSING → SATISFIED SOLO con verification_evidence.

### 5. **Limitaciones**

#### ¿Qué no está actualmente implementado?
- `backend` y `capability` fields: estan en `operations` y `results` existentes, pero no están presentes en el schema de `dependency_states`.
- CLI `dep` y `rem` dedicado: el frontend/no hay una interfaz de línea de comandos dedicada para crear/mostrar dependencias y remediaciones.

#### ¿Qué está en la matriz RXRE-008?
- Desde RXRE-002: `register.writers`, `register.uses`, `pm4.opcodes`, `provenance.keys`, `project.capabilities`.
- Desde RXRE-004: `binary.inspect` (ejecutable), `binary.decompile` (disponible con limitación ET_REL).

### 6. **Justificación para el proyecto RX550-INVESTIGACION**

#### Caso de uso (KytyPS5 build fallado por SDL3/libX11/Wayland):
```
TARGET: S_ADD_U32_regression_test
BUILD_CONFIGURATION: Nobara Linux 44, GCC 16.2.1, CMake 4.3.0
DEPENDENCY_1:
  name: SDL3
  state: MISSING
  diagnostic: CMake Error: SDL could not find X11 or Wayland development libraries
  context: {"os": "Nobara Linux 44", "cmake_version": "4.3.0"}
  validated_by: op_kyty_cmake_1
  # ^Es un hecho: la configuración de CMake falló por eso.

DEPENDENCY_2:
  name: libX11
  state: MISSING
  diagnostic: CMake Error: Could NOT find X11
  context: {"cmake_version": "4.3.0"}

VALIDATION_GOAL:
  "ejecutar shader_recompiler_compute_tests que contiene S_ADD_U32 cases"

CADENA DE VALIDACIÓN:
  VALIDATION_GOAL -> S_ADD_U32_regression_test -> BUILD_CONFIGURATION ->
  DEPENDENCY_1 -> OBSERVED_BLOCKER(MISSING) ->
  REMEDIATION(propuesta: dnf install -y SDL3-devel libX11-devel wayland-devel) ->
  OBSERVED_BLOCKER(pendiente) ->
  REMEDIATION(ejecutada: dnf install -y ...) ->
  EXECUTION_RESULT(RESOLVED con verification_evidence res_dnf_success_001) ->
  DEPENDENCY_1.state = SATISFIED

DEPENDENCY_2 permanece MISSING porque no tiene remediation o verification.

¡IMPACTO!
  - RXRE puede COMPROBAR por qué S_ADD_U32_regression_test no se ejecuta.
  - ¿Falta SDL3 o libX11? ¿Cuál?
  - Si SDL3 se instala y se ejecuta el test, RXRE puede recuperar la prueba y evidencia.
  - Si el test aún falla, RXRE puede registrar la remediación fallada (FAILED + evidence).
  - Si el test nunca se ejecuta porque libX11 aún falta, RXRE lo sabe.
```

### 7. **Declaración de cumplimiento para RXRE-008**

✅ **La IA puede registrar un REQUIREMENT observado para una validación específica**
   - `registrar_dependency()` registra `target`, `name`, `state`, `diagnostic`, `context`.
   - El estado es MEDIDO (no una opinión). MISSING, SATISFIED, OPTIONAL, NOT_DETERMINED.

✅ **El estado viaja con su DIAGNOSTICO y CONTEXTO irrepetibles**
   - diagnostic: la línea exacta del error de CMake.
   - source: ubicación del error.
   - context: JSON con revision, compiler, cmake flags, entorno.

✅ **La remediación es PROPOUE y REGISTRADA**
   - `registrar_remediation()` se usa para PROPOSE.
   - `attempted=False` inicialmente.
   - La remediación está vinculada al dep_id.

✅ **VERIFICACIÓN independiente vincula el RESULTADO a la EVIDENCIA**
   - `marcar_remediation_completada()` con verification_result + verification_evidence.
   - RESOLVED sin verification_evidence NO actualiza la dependency.

✅ **La cadena VALIDATION -> DEPENDENCY -> REMEDIATION -> EXECUTION_RESULT es recuperable**
   - `query_validation_chain()` permite filtros por target, nombre, estado.
   - Devuelve una lista completa de dependencies y sus remediaciones.

✅ **DISTINGUE BLOCKED vs. FALLADO vs. NO-EJECUTADO**
   - BLOCKED: dependency MISSING, remediation pendiente.
   - FALLADO: dependency SATISFIED pero verification_result == 'FAILED'.
   - NO-EJECUTADO: target no mencionado en ninguna dependency.

**Resultado:** RXRE ahora puede responder preguntas como:
- "¿Por qué no puedo ejecutar S_ADD_U32_regression_test?"
- "¿Qué dependency me falta y como lo remedio?"
- "Si ya intenté remediar, que resultado tuve?"

### 8. **Referencias cruzadas**

- **RXRE-002**: `register.writers`, `register.uses`
- **RXRE-004**: `binary.inspect`
- **RXRE-008**: este cambio

### 9. **Próximos pasos**

#### Lo que está más cerca de la "actualización Rxre.ps5-009" del usuario:
- **Añadir un API de CLI `dep` para `dep list` y `dep create/remedy`** (opcional).
- **Convertir el registro de testing expuesto en el frontend `api/request`** (si existe `ops`).

#### Para las capacidades de KytyPS5:
- **Resolver el error Vulkan-Headers Extent3D / Extent2D** (afuera, por ahora, por versión).
- **Corregir los errores de brace-inicialización en toda la fuente** (afuera).
- **Una vez resuelto, el build de shader_recompiler_compute_tests correrá y producirá un EXECUTION_RESULT para S_ADD_U32 cases**.RXRE podría registrar el resultado real.

### 10. **Archivos modificados**

- `tools/rxre/core/store.py`: DDL + funciones.
- `tools/rxre/tests/test_dependency008.py`: test unitario nuevo.

### 11. **Base de datos de almacenamiento** (si se reinicia)

- `tools/rxre/storage/rxre.sqlite3`
- Nuevas tablas: `dependency_states`, `validation_remediations`

### 12. **Función de hash SHA256** (nota para el usuario)

`def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]`

Maneja dep_ids y rem_ids como dep_<sha> / rem_<sha>.RXRE now supports dependency-aware validation tracking, allowing:

- Observable dependency states with full context
- Propose and execute remediations with independent verification
- Track blocked, failed, and not-started test states
- Reproducible evidence chains for validation failures