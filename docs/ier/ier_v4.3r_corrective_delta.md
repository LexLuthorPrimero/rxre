# IER-GATE — Corrección documental de v4.2R
## Borrador correctivo controlado (no es una promoción ni una implementación)

**Documento de origen:** `IER-GATE — Plan Técnico Canónico`, v4.2R  
**Fuente:** https://brewpage.app/jury/ApHR8xEreG  
**Fecha de revisión:** 2026-11-15  
**Estado propuesto:** `CORRECTIVE_DRAFT · DESIGN_UNVERIFIED · NOT_EXECUTED`  
**Estado global:** `PARTIAL`  
**Implementación:** `NOT_EXECUTED`  
**Crash injection:** `NOT_EXECUTED`  
**Revisión externa:** `NOT_EXECUTED / REQUIRED`  
**Promoción:** `NOT_READY`

---

## 0. Alcance y reglas de aplicación

Este documento contiene correcciones normativas concretas para v4.2R. No afirma que el archivo local haya sido modificado ni sustituye automáticamente al original.

### 0.1 Protección de §1

§1 del plan canónico está congelada. Por tanto:

- No se cambia ningún dominio, invariante, conteo, transición ni predicado de §1.
- Las contradicciones detectadas dentro de §1 se conservan como bloqueos normativos.
- Ninguna sección posterior puede inventar un valor nuevo para hacer compatible §1.
- Ningún conteo (2784, 2340 u otro) se considera verificado por aparecer en el documento.
- Los cambios de este delta no autorizan implementación, OP-NEXT-1, D-13, D-14, crash injection, revisión externa ni promoción.

### 0.2 Convención epistemológica

Se distinguen cuatro estados que no deben confundirse:

| Dimensión | Valores |
|---|---|
| Especificación | `OPEN`, `DESIGN_UNVERIFIED`, `DESIGN_CLOSED` |
| Ejecución | `NOT_EXECUTED`, `EXECUTED` |
| Verificación | `NOT_VERIFIED`, `PARTIALLY_VERIFIED`, `INDEPENDENTLY_VERIFIED` |
| Promoción | `NOT_READY`, `ELIGIBLE_FOR_OWNER_DECISION`, `PROMOTED` |

`DESIGN_CLOSED` no implica `EXECUTED`. `EXECUTED` no implica `INDEPENDENTLY_VERIFIED`. Ningún estado se infiere de otro.

---

# 1. Registro de defectos de esta revisión

Los defectos siguientes son añadidos al registro para trazabilidad. No se declaran cerrados por este documento.

| ID | Defecto | Estado |
|---|---|---|
| C-201 | §1 declara seis dominios, pero enumera SI, OD, P, T, ES, TR y O: siete dominios. | BLOCKED_BY_FROZEN_§1 |
| C-202 | §1.3 usa `ES=NONE` en RESERVE_ORPHAN, aunque NONE no pertenece al dominio ES. | BLOCKED_BY_FROZEN_§1 |
| C-203 | §1.3 permite `T != NONE` con `ES=TESTIFICATION_PENDING`, aunque el hecho histórico testificado debe corresponder a `ES=TESTIFIED`. | BLOCKED_BY_FROZEN_§1 |
| C-204 | §1.3 contiene incompatibilidad entre `P=FAILED_CONSUMED ⇒ O=UNKNOWN` y `O=COMMITTED ⇒ P` incluyendo FAILED_CONSUMED. | BLOCKED_BY_FROZEN_§1 |
| C-205 | §1.4 incluye `COMMIT_DURABLE | T != NONE` en “ilegales” y simultáneamente explica que puede ser legal. | BLOCKED_BY_FROZEN_§1 |
| C-206 | §1.5 no valida exhaustivamente los siete dominios ni todas las invariantes de §1.3. | BLOCKED_BY_FROZEN_§1 |
| C-207 | §1.6 T03 llama `durable_write` a `SELECT ... FOR UPDATE`/adquisición de lock, que no persiste un claim durable. | OPEN |
| C-208 | §1.6 T06 permite que el horizonte temporal produzca RESERVE_ORPHAN sin reconciliación demostrada de A/PG. | OPEN |
| C-209 | §1.6 T09 mezcla contradicción de evidencia, pérdida de integridad y actualización de OD/TR sin separar la dimensión afectada. | OPEN; su correspondencia con §1 queda bloqueada |
| C-210 | §4.5 atribuye `FAILED_CONSUMED` a una operación a partir de un GAP que §4.6 define como opaco y sin operation_id. | OPEN |
| C-211 | §4.4 permite reintentar NV_Increment cuando `NV < expected` sin contrato completo para demostrar que el incremento anterior no está en vuelo ni puede completarse tardíamente. | OPEN |
| C-212 | §5.5 tiene una condición de completitud mal expresada: `completeness_status` demostrado parece compararse con `NOT_DETERMINED`. | OPEN |
| C-213 | §7.2 duplica pasos R1/R2 entre W y A y no define de manera única el punto de confirmación de ambas partes. | OPEN |
| C-214 | §7.4 usa el lock de fila como exclusión, pero no especifica exhaustivamente rutas de escritura, aislamiento, fencing y punto de linealización. | OPEN |
| C-215 | §8.2 incluye `pg_class.relhasoids`, incompatible con PostgreSQL 12+ donde OID de tabla fue eliminado. | OPEN |
| C-216 | §8.4 atribuye al event trigger capacidad de impedir toda modificación del despliegue; el alcance real depende de privilegios, propietario/superusuario y rutas fuera del modelo. | OPEN |
| C-217 | §9.3 define STRUCT con `UB(1 B)`, mientras §9.4 define `n_field_bytes`; no hay una gramática única. | OPEN |
| C-218 | §9.6 `typed_value` no coincide con `value`: omite STRUCT y duplica reglas de ARRAY/MAP. | OPEN |
| C-219 | §9.8 mezcla restricciones de bytes UTF-8 con rangos de puntos de código Unicode y no define de forma coherente C0/C1/DEL. | OPEN |
| C-220 | §9.9 exige fail-fast en orden de lectura, pero no especifica preflight de longitudes y presupuestos antes de asignaciones o lecturas grandes. | OPEN |
| C-221 | §10 usa `S=(G,P,T,O,E)` y `G` con vocabulario diferente de SI/OD/TR/ES de §1. La reconciliación requiere decisión sobre §1. | BLOCKED_BY_FROZEN_§1 |
| C-222 | §11 contiene oráculos contradictorios en T-I3-1 y T-I3-4 para la carrera EXECUTE/ABORT. | OPEN |
| C-223 | §11 T-AB-3 clasifica como NOT_DETERMINED todo ABORT durable sin sello W, sin separar resultado PG conocido de testificación W pendiente. | OPEN |
| C-224 | §12 mezcla cierre de diseño, implementación y verificación externa en una sola enumeración. | OPEN |
| C-225 | §13 ordena D-13/D-14/OP-NEXT-1/crash injection como siguiente secuencia sin convertir cada paso en una autorización independiente del propietario. | OPEN |

---

# 2. Reemplazo propuesto para §1.9 (solo registro; no modifica §1)

Sustituir la afirmación “B-07 corregido” por:

> **B-07: OPEN · DESIGN_UNVERIFIED.** §1 contiene un modelo candidato y un predicado de referencia, pero no se declara cerrado. Se han identificado inconsistencias internas C-201…C-206 y una dependencia congelada que impide resolverlas en esta revisión. Los conteos publicados son referencias no verificadas. Ninguna transición, función LegalState ni matriz de combinaciones se considera certificada.
>
> B-01…B-08 permanecen OPEN. Los estados `NOT_EXECUTED` se mantienen. No hay evidencia de implementación, crash injection, revisión independiente ni promoción.

No modificar las definiciones normativas de §1 mediante este reemplazo.

---

# 3. Reemplazo propuesto para §1.6 T03/T06/T09: bloqueo explícito

Dado que §1 está congelada, las siguientes son notas de incompatibilidad y no sustituciones normativas.

### T03 — Lock volátil frente a claim durable

`SELECT ... FOR UPDATE` es un mecanismo de serialización transaccional. No constituye por sí solo un registro durable de que una ejecución fue reclamada.

Hasta que se autorice y defina el contrato correspondiente:

- No describir la adquisición del lock como `durable_write`.
- No inferir `EXECUTING` durable a partir de un lock que desaparece con el fin de la transacción.
- Mantener separado el estado de claim durable del lock volátil.
- La recuperación de un claim abandonado no puede inferir que el efecto no ocurrió.
- Un claim de generación antigua debe ser rechazado por fencing en el punto efectivo de escritura.

**Estado:** `BLOCKED_BY_FROZEN_§1`; no se cambia la transición canónica.

### T06 — Reserva huérfana

El horizonte temporal solo habilita una reconciliación:

`elapsed(horizon) ⇒ reconciliation_due`

No habilita por sí mismo:

`elapsed(horizon) ⇒ no_execution`

La observación de `ENTRY(reserve)` sin R2 demuestra una reserva W no confirmada, no la ausencia de ejecución SQL. La clasificación de reserva W y el resultado de A/PG deben permanecer separados.

No se permite `ORPHAN_TERMINAL` sin una comprobación serializada de:

1. ausencia de efecto confirmado;
2. ausencia de claim activo;
3. ausencia de ejecución en vuelo;
4. generación vigente;
5. binding inequívoco entre operación y reserva.

Si una condición es desconocida, la decisión es `NOT_DETERMINED`.

**Estado:** `OPEN`; correspondencia final con §1 bloqueada.

### T09 — Incertidumbre y contradicción

No utilizar un único evento `not_determined` para colapsar:

- evidencia contradictoria;
- pérdida de continuidad de W;
- fuente WAL no disponible;
- binding ambiguo;
- scope en rollback;
- ausencia de evidencia suficiente.

Cada caso debe conservar las observaciones originales, su identidad, el dominio afectado y las invariantes potencialmente violadas. No se inventan valores dentro de SI, OD, P, T, ES, TR u O.

**Estado:** `OPEN`; proyección canónica bloqueada.

---

# 4. Reemplazo de §4.4 — Recuperación NV con fencing de intentos

La recuperación debe distinguir el estado durable del marker, el resultado observado del contador y la posibilidad de que una llamada anterior siga en vuelo.

Definiciones:

- `expected_counter`: contador que la operación intenta consumir.
- `observed_counter`: lectura autenticada del NV.
- `attempt_id`: identidad inmutable de un intento NV.
- `attempt_state`: `NOT_STARTED | IN_FLIGHT | CONFIRMED | UNKNOWN`.
- `marker_state`: `MARKER_DURABLE | ENTRY_DURABLE | RECONCILIATION_REQUIRED`.

Reglas:

| Observación | Acción permitida |
|---|---|
| Marker durable, intento nunca iniciado y exclusión de escritor demostrada | iniciar un intento NV |
| Intento en vuelo | esperar/reconciliar; no emitir segundo incremento |
| Resultado de intento desconocido | no reintentar hasta demostrar el estado del primer intento |
| NV = expected y atestación válida | reconstruir ENTRY desde marker, idempotentemente |
| NV < expected y el intento anterior está demostrado como no aplicado y cerrado | puede iniciarse un único nuevo intento bajo el mismo attempt_id lógico y fencing |
| NV > expected | enumerar todos los contadores consumidos; no atribuir operaciones sin binding |
| Lectura/atestación inválida | `NOT_DETERMINED`; no sellar |

La recuperación debe ser idempotente por `(witness_id, attempt_id, operation_id, msg_id)`. Un proceso reiniciado no puede crear una segunda llamada mientras el resultado de la primera sea desconocido.

---

# 5. Reemplazo de §4.5 — GAP opaco y atribución separada

Un GAP representa consumo de contador sin evidencia suficiente para reconstruir el evento original. Un GAP no lleva `operation_id`, `binding`, `reservation_index` ni payload semántico inferido.

Definir la clasificación separada:

```text
GapAttribution:
    GAP_UNATTRIBUTED
    GAP_ATTRIBUTED
    CONSUMPTION_UNCERTAIN
```

Reglas:

1. Si no existe binding único, registrar `GAP_UNATTRIBUTED`.
2. Si existe prueba independiente y única que vincula el contador con una operación, registrar la atribución en un registro separado, firmado y enlazado al GAP; no modificar el GAP original.
3. Si no se sabe si el contador fue consumido o si la lectura no es confiable, usar `CONSUMPTION_UNCERTAIN` y detener la reconciliación.
4. Nunca ejecutar `mark operation at c :: FAILED_CONSUMED` a partir de la mera posición del GAP.
5. `FAILED_CONSUMED` solo puede asignarse a una operación mediante binding único y contrato de transición válido.
6. Los slots consumidos nunca se reasignan.

Pseudocódigo:

```python
def classify_gap(counter, marker, entry, binding_proof):
    if not counter_read_is_authenticated():
        return "CONSUMPTION_UNCERTAIN"

    if entry_is_valid_and_chained(entry, counter):
        return "NOT_A_GAP"

    if marker_is_valid_and_matches(marker, counter):
        return "RECONSTRUCT_ENTRY_FROM_MARKER"

    if binding_proof is not None and verify_unique_binding(binding_proof, counter):
        append_immutable_gap_attribution(counter, binding_proof)
        return "GAP_ATTRIBUTED"

    append_opaque_gap(counter)
    return "GAP_UNATTRIBUTED"
```

El registro de atribución no puede transformar una inferencia en evidencia. La prueba debe incluir fuente, algoritmo, versión, identidad del verificador y resultado de validación.

---

# 6. Reemplazo de §5.5 — Verificación del proof por conjunción

La condición `completeness_status` debe expresarse sin ambigüedad:

```text
W_ACCEPTS_EFFECT_PROOF iff
    signature_valid
    AND registry_key_valid
    AND operation_binding_matches
    AND reservation_hash_matches
    AND reservation_index_matches
    AND anchor_epoch_matches
    AND effect_scope_fp_matches
    AND source_id_pinned
    AND timeline_matches
    AND wal_physical_continuity_verified
    AND transaction_completeness_verified
    AND relation_coverage_verified
    AND effect_attribution_verified
    AND runtime_log_equals_reconstructed_delta
```

Cada componente es trivalente: `TRUE | FALSE | UNKNOWN`.

- Si todos son TRUE: prueba candidata a `VERIFIED`.
- Si alguno es FALSE: rechazo por contradicción o invalidez, con razón tipada.
- Si ninguno es FALSE pero alguno es UNKNOWN: `NOT_DETERMINED`.
- Nunca interpretar `completeness_status=NOT_DETERMINED` como evidencia de completitud.

El certificado debe distinguir continuidad física de WAL, completitud de transacciones, cobertura de relaciones y atribución semántica del efecto. La completitud global es la conjunción de las cuatro.

---

# 7. Reemplazo de §7.4 — Exclusión EXECUTE/ABORT

El lock de fila es un mecanismo de serialización, no una prueba autónoma de exactly-once ni una garantía frente a rutas de escritura no enroladas.

Contrato requerido:

- Clave de serialización: `operation_id`.
- EXECUTE y ABORT bloquean la misma fila de operación.
- La actualización terminal y el efecto SQL protegido ocurren en una única transacción PostgreSQL.
- La transacción verifica `verdict='pending'`, `reservation_confirmed=true`, binding y generación vigente.
- La transacción que no obtiene el estado pendiente no produce efectos.
- Toda ruta alternativa de escritura debe estar excluida por privilegios, dependencias, funciones, triggers, cascades, extensiones y política de despliegue verificable.
- La confirmación durable se reconoce únicamente después de COMMIT y lectura posterior del estado durable.
- Un timeout o una conexión perdida durante COMMIT produce resultado desconocido hasta reconciliar con A/PG y WAL.

Pseudocódigo conceptual:

```sql
BEGIN;

SELECT verdict, reservation_confirmed, binding, generation
FROM ops
WHERE operation_id = :operation_id
FOR UPDATE;

-- Verificar binding, reserva, generación y verdict=pending.
-- La rama EXECUTE aplica el efecto y marca committed
-- dentro de esta misma transacción.
-- La rama ABORT marca aborted sin aplicar el efecto.

UPDATE ops
SET verdict = :terminal_verdict
WHERE operation_id = :operation_id
  AND verdict = 'pending'
  AND generation = :expected_generation;

-- Debe afectar exactamente una fila.
COMMIT;
```

No usar este fragmento como SQL ejecutable sin completar las validaciones y las ramas. La propiedad exigida es:

`COMMIT(effect, verdict=committed)` o `COMMIT(verdict=aborted, no_effect)`, nunca ambos y nunca uno sin el otro para el dominio SQL enrolado.

Para efectos externos, PostgreSQL no proporciona atomicidad con el proveedor. Exigir idempotency key durable y recibo terminal firmado del proveedor; sin ello, abstenerse.

---

# 8. Reemplazo de §8.2 — Catálogo compatible con versiones

Eliminar `pg_class.relhasoids` como atributo universal. El inventario debe ser versionado por `server_version_num`.

Reglas:

- Consultar `server_version_num` antes de construir el snapshot.
- Incluir solo columnas existentes en esa versión.
- No usar un nombre de columna eliminado como requisito universal.
- Registrar versión del servidor, versión del esquema del inventario y consulta exacta.
- Si una versión no está soportada por el catálogo certificado, el resultado es `NOT_DETERMINED`, no un fingerprint parcial.
- El catálogo debe incluir objetos, propietarios, privilegios efectivos, dependencias, funciones, triggers, políticas RLS, secuencias, extensiones, publicaciones, particiones y rutas indirectas relevantes.
- Una lista de catálogos no demuestra exhaustividad: cada clase debe tener un procedimiento de enumeración y un test de omisión.

---

# 9. Reemplazos de §9 — BIN-B

## 9.1 Regla única de STRUCT

Sustituir en §9.3 `UB(1 B)` por `n_field_bytes (1 B)`.

Única gramática normativa:

```text
STRUCT :=
    0x0F
    || schema_id[32]
    || n_field_bytes[1]
    || field_mask[n_field_bytes]
    || values_of_present_fields_in_descriptor_order

1 <= n_fields <= 512
n_field_bytes = ceil(n_fields / 8)
1 <= n_field_bytes <= 64
field_mask uses little-endian bit numbering within each byte.
Unused high bits in the final byte MUST be zero.
Every required field MUST be present.
```

Cualquier aparición de `UB(1 B)` debe eliminarse como alias no normativo.

## 9.2 `typed_value` debe ser `value`

Eliminar la gramática paralela de §9.6. Sustituirla por:

```text
typed_value := value
```

El descriptor del schema determina el tipo permitido y sus restricciones. No se define una segunda codificación para pruebas.

Consecuencias:

- STRUCT está permitido cuando el descriptor lo declara.
- ARRAY y MAP conservan exactamente la gramática de §9.3.
- MAP no queda restringido globalmente a claves STRING; el descriptor determina `key_type`.
- Si un campo concreto necesita claves STRING, esa restricción se expresa en su descriptor.
- No se permiten excepciones de codificación en `IER-EFFECT-DELTA-v1` ni en payloads.

## 9.3 Normalización de STRING

Definir sobre puntos de código Unicode, no sobre bytes aislados:

1. Decodificar UTF-8 estrictamente.
2. Rechazar secuencias inválidas, sobrelongitudes, sustitutos y valores fuera de Unicode.
3. Exigir que el texto recibido ya esté en NFC; no normalizar silenciosamente antes de calcular hashes.
4. Rechazar U+0000..U+001F y U+007F..U+009F.
5. Re-encode UTF-8 y exigir igualdad byte a byte con la entrada.
6. Cualquier violación produce `CANON_ERROR`.

Así se elimina la contradicción entre “control bytes” y los rangos C0/C1.

## 9.4 DECIMAL

Representar el valor como:

`x = v × 10^(-scale)`

Donde:

- `v` es INT128 con signo en complemento a dos, big-endian.
- `scale ∈ [0,38]`.
- Si `scale > 0`, `v mod 10 != 0`.
- Cero tiene representación única: `v=0, scale=0`.
- No hay NaN, infinito ni valores alternativos.
- El rango de `v` es `[-2^127, 2^127-1]`.

Dos valores matemáticamente iguales deben tener una única representación canónica. Los vectores deben cubrir extremos, escalas y equivalencia matemática.

## 9.5 Límites y orden de validación

Reemplazar “fail-fast en orden de lectura” por:

```text
1. Verificar longitud total del mensaje contra el límite global.
2. Verificar que cada longitud/count cabe en los bytes restantes.
3. Verificar límites declarados antes de reservar memoria.
4. Verificar presupuesto acumulado de nodos, profundidad y bytes.
5. Decodificar el valor.
6. Verificar canonicalidad y restricciones de descriptor.
7. Verificar hash/firma solo después de una decodificación estructural válida.
```

Nunca reservar `count × sizeof(element)` antes de comprobar overflow, presupuesto y bytes disponibles. Cualquier agotamiento de presupuesto produce rechazo determinista; no continuar procesando subobjetos.

---

# 10. Reemplazos de §11 — Oráculos discriminantes

## T-I3-1 — Carrera EXECUTE/ABORT

Oráculo correcto:

- Si ABORT gana la serialización: `verdict=aborted`, efecto SQL=0.
- Si EXECUTE gana y confirma: `verdict=committed`, efecto SQL=1.
- El perdedor observa el estado terminal durable y no produce efecto.
- Nunca existen dos terminales ni dos efectos para el mismo `operation_id`.

La aceptación no puede exigir `effect=0` para ambos resultados posibles.

## T-I3-4 — Crash durante EXECUTE

Como efecto SQL y `verdict=committed` pertenecen a la misma transacción:

- Crash antes del COMMIT: ambos rollback; `verdict=pending`, efecto=0.
- COMMIT confirmado: ambos durable; `verdict=committed`, efecto=1.
- Resultado del COMMIT desconocido para el cliente: no reejecutar; reconciliar consultando A/PG y WAL.
- No existe estado válido con efecto SQL confirmado y `verdict=aborted` para la misma transacción protegida.

## T-AB-3 — ABORT durable, W sin sello

Separar:

- `A/PG verdict=aborted` durable: hecho de ancla conocido.
- `W terminal seal absent`: testificación pendiente.
- Resultado de W: `RECOVERABLE` si continuidad e identidad pueden verificarse; `NOT_DETERMINED` si no pueden.
- No volver a ejecutar la operación.
- No declarar `ABORT_TESTIFIED` hasta que W valide y persista la evidencia terminal.

## T-GAP-1/3 — GAP y operación previamente asociada

Un GAP opaco no atribuye por sí solo una operación. Si una operación tenía `reservation_index` coincidente con el contador perdido, la operación queda `NOT_DETERMINED` hasta que una prueba de binding independiente resuelva la asociación. No asignar `FAILED_CONSUMED` solo por igualdad numérica de índices.

## T-GAP-4 — Recuperación concurrente

50 recuperadores concurrentes deben converger en una única ENTRY, protegida por una clave de idempotencia y un lock/fencing durable de recuperación. La aceptación exige:

- una única ENTRY por `(witness_id, counter_value)`;
- mismo contenido/hash en todos los observadores;
- ninguna segunda NV increment;
- ningún ACK emitido antes de ENTRY durable;
- ninguna ENTRY previa sobrescrita.

---

# 11. Reemplazo de §12 — Estados de defectos y evidencia

Usar estados ortogonales:

| Campo | Valores |
|---|---|
| `design_status` | `OPEN`, `DESIGN_UNVERIFIED`, `DESIGN_CLOSED` |
| `implementation_status` | `NOT_EXECUTED`, `IMPLEMENTED` |
| `verification_status` | `NOT_VERIFIED`, `PARTIALLY_VERIFIED`, `INDEPENDENTLY_VERIFIED` |
| `external_review_status` | `NOT_REQUESTED`, `PENDING`, `PASSED`, `FAILED` |
| `promotion_status` | `NOT_READY`, `ELIGIBLE_FOR_OWNER_DECISION`, `PROMOTED` |

Un defecto solo puede pasar a `DESIGN_CLOSED` si:
1. contrato inequívoco;
2. dominios completos;
3. invariantes compatibles;
4. transiciones completas;
5. recuperación para cada punto durable;
6. pruebas positivas, negativas y de frontera;
7. ausencia de contradicciones internas;
8. dependencias normativas resueltas.

No usar `VERIFIED` como sinónimo de revisión externa. La revisión externa es una dimensión independiente.

Estado de esta revisión:

```text
B-01 ... B-08:
    design_status = OPEN
    implementation_status = NOT_EXECUTED
    verification_status = NOT_VERIFIED
    external_review_status = NOT_REQUESTED
    promotion_status = NOT_READY

C-201 ... C-206:
    design_status = BLOCKED_BY_FROZEN_§1
```

---

# 12. Reemplazo de §13 — Secuencia y autorizaciones

La secuencia documental no concede autorización operativa. Cada paso requiere una decisión independiente del propietario.

Orden de dependencias propuesto:

1. Resolver formalmente los bloqueos de §1 mediante autorización específica; hasta entonces no modificar §1 ni declarar B-07 cerrado.
2. Cerrar contratos internos de BIN-B y Apéndice B sin ejecutar codificadores (diseño solamente).
3. Cerrar identidad, firmas, anti-replay y registry.
4. Cerrar protocolo W/NV y recuperación por cada crash point.
5. Cerrar contrato de captura WAL y dominio certificable.
6. Cerrar R1/R2, EXECUTE/ABORT y exclusión de rutas alternativas.
7. Cerrar catálogo/fingerprint y revocación.
8. Completar matrices de pruebas y auditoría independiente del diseño.
9. Solicitar autorización explícita para cada actividad de ejecución, prueba destructiva o revisión externa.

OP-NEXT-1, D-13, D-14, crash injection, revisión externa y promoción permanecen `NOT_AUTHORIZED` hasta autorización específica. No iniciar automáticamente el siguiente paso por haber terminado el anterior.

---

# 13. Criterios para aceptar una futura v4.3R

La futura versión no se acepta por incluir este delta. Debe demostrar:

- §1 resuelta por decisión autorizada o sus dependencias permanecen bloqueadas explícitamente.
- C-201…C-225 clasificados con evidencia de cierre o bloqueo.
- Todas las referencias cruzadas y nombres de estados validados automáticamente.
- Cada transición tiene precondiciones, actor, autorización, clave de serialización, punto de linealización, escrituras durables, postestado, evidencia, recuperación, prohibiciones e invariantes.
- Cada punto de persistencia tiene casos crash-before/during/after.
- Los oráculos de §11 son mutuamente compatibles.
- Los vectores BIN-B se verifican byte a byte; hashes recalculados por herramientas independientes.
- Los certificados de legalidad/alcanzabilidad tienen algoritmos reproducibles y testigos.
- Dos implementaciones independientes coinciden antes de declarar conformidad criptográfica.
- Revisión independiente de diseño superada antes de considerar `DESIGN_CLOSED`.

## Dictamen de este delta

`CORRECTIVE_DRAFT · DESIGN_UNVERIFIED · NOT_EXECUTED`

No es `IMPLEMENTATION_READY`. No modifica §1. No cierra B-01…B-08. No autoriza OP-NEXT-1, D-13, D-14, crash injection, revisión externa ni promoción.
