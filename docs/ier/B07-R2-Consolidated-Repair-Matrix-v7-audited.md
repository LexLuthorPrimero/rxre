# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 7 (CORRECTIVA)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** v2.r2 (`9c8a0aba…`) **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1…v6 (`e1…/10…/e1…/5d…/52…/34…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.

## Registro de revisiones

| Versión | Disposición |
|---|---|
| v6 | Auditoría: NO RATIFICABLE; CR-17…CR-28 abiertos; falta contenido individual de 104 unidades; coherencia documental insuficiente |
| **v7** | **Correctiva**: R7-A cierre semántico ↑, R7-B modelo de dependencias r1/r2 ↑, R7-C DDL coherente, R7-D R-CLAIM y suspensión máquinas, R7-E claves y ancla, R7-F matriz normalizada y 104 unidades con contenido |

---

## 0. Leyenda única y cierre

`Definición → Persistencia → Transición → Invariante → Contraejemplo → Prueba`.
Vocabulario de estado (**único, sin sinónimos**):
`REPAIR_REQUIRED` · `BLOCKED` · `NOT_APPLICABLE`
Definiciones:
- REPAIR_REQUIRED: unidad con defecto detectado cuya reparación está diseñada y pendiente de verificación ejecutable; nada se acepta sin cotejo.
- BLOCKED: unidad cuyo cierre depende de un bloqueo estructural (gate); no se cierra.
- NOT_APPLICABLE: unidad no aplicable salvo que cambie el alcance; exige justificación formal.
Ninguna decisión ni fila se acepta con base en este documento; la aceptación es exclusivamente del propietario tras auditoría independiente.

---

## 1. R7-A — Máquina de efectos y cierre (corrige CR-17 / CR-26)

### 1.1 — Tres ejes ortogonales, una única existencia por efecto

Un efecto del manifiesto no es un valor escalar: es el producto de tres ejes **independientes**:

```
ExecutionAxis      ∈ {NEVER_EXECUTED, EXECUTED, DISCHARGED}
CompensationAxis   ∈ {NOT_REQUIRED, PENDING, VERIFIED, FAILED}
OutcomeAxis        ∈ {NOT_EXECUTED, COMMITTED, UNKNOWN}
```

Ninguna transición borra `ExecutionAxis=EXECUTED`: la historia es inmutable (`effect` row append-only para ese eje).

### 1.2 — Reglas de asignación de ejes

```
NEVER_EXECUTED := effect inserto en estado inicial (ningun intento dispuso despacho o ninguno fue aceptado por el provider).
EXECUTED       := el provider confirmó recepción/operación del efecto (ExecutionReceipt durable registrado en effect_log).
DISCHARGED     := equivalente a `DISPATCHED` del modelo R1 — sustituye al `INTENT_DURABLE` del manifiesto; nunca transición reversa.

CompensationAxis:
  NOT_REQUIRED  := ExecutionAxis ≠ EXECUTED, o política/estado no exige compensación y ésta se decidó innecesaria.
  PENDING       := ExecutionAxis = EXECUTED y la compensación es requerida pero aún sin verificar.
  VERIFIED      := ExecutionAxis = EXECUTED ∧ CompensationAxis = VERIFIED (compensation_verified=TRUE) ∧ CompensationSig validada por verificador independiente.
  FAILED        := compensación requerida no satisfecha según verificador; nunca es terminal limpia.

OutcomeAxis (resultado jurídico/contractual del efecto):
  NOT_EXECUTED  := ExecutionAxis = NEVER_EXECUTED (sin efecto confirmado) ∨ (ExecutionAxis = EXECUTED ∧ CompensationAxis = VERIFIED)
                — es decir: o jamás se despachó, o el efecto ejecutado fue anulado-y-verificado.
  COMMITTED     := ExecutionAxis = EXECUTED ∧ CompensationAxis ∈ {NOT_REQUIRED, PENDING} ∧ policy_result(op) = VERIFIED (todos los efectos de la política verificados).
  UNKNOWN       := cualquier efecto con ExecutionAxis indeterminado o resultado no verificado.
```

### 1.3 — Contenido exacto del `effect` (persistencia real)

```
effect := (
  operation_id    bytea REFERENCES operation(operation_id),
  attempt_id      bytea REFERENCES attempt(attempt_id),
  effect_ordinal  smallint,
  effect_kind     smallint,
  execution_axis  text CHECK (execution_axis IN ('NEVER_EXECUTED','EXECUTED','DISCHARGED')),
  compensation_axis text CHECK (compensation_axis IN ('NOT_REQUIRED','PENDING','VERIFIED','FAILED')),
  outcome_axis    text CHECK (outcome_axis IN ('NOT_EXECUTED','COMMITTED','UNKNOWN')),
  policy_result   text CHECK (policy_result IN ('PENDING','VERIFIED','FAILED','COMPENSATED_ALL','UNKNOWN')),
  executed_at     timestamptz,
  verified_at     timestamptz,
  compensated_at  timestamptz,
  evidence_hash   bytea
)
```

### 1.4 — Reglas de coherencia entre ejes (restricción declarativa, verificable por construcción)

```sql
-- Sólo tras verificación independiente; ningún cierre de op es válido con outcome UNKNOWN
CHECK ( (outcome_axis='UNKNOWN' AND policy_result='UNKNOWN')
        OR (outcome_axis='COMMITTED' AND execution_axis='EXECUTED'
            AND evidence_hash IS NOT NULL)
        OR (outcome_axis='NOT_EXECUTED') )
CHECK ( compensation_axis='VERIFIED' ⇒ executed_at IS NOT NULL )
CHECK ( compensation_axis='FAILED'  ⇒ evidence_hash IS NOT NULL )

-- Coherencia agregada de op:
ClosedOK(op) ⇔
  ∀ e ∈ effects(op): e.outcome_axis ∈ {'NOT_EXECUTED','COMMITTED'}
  ∧ ∃ compensación durable-verified para todos los efectos historicamente ejecutados y cuya respuesta política era obligatoria
  ∧ p ∈ P_TERMINAL(op)
  ∧ eso ∈ ESO_KNOWN_OUTCOME(op)
  ∧ o  ∈ TESTIFIED(op)
```

### 1.5 — LegalClose y semántica de políticas

```
PL-001 NONE : ningún efecto despachable; effects nunca pueden salir de NEVER_EXECUTED; policy_result=FAILED si se intenta.
PL-002 ANY  : success ⇔ ≥1 effect con outcome_axis='COMMITTED'. El resto pueden estar en cualquier estado coherente (compensación).
PL-003 ALL  : success ⇔ ∀ e ∈ effects(op): outcome_axis='COMMITTED'. Si alguno no, abort-durable.
LegalClose ⇔
    executed(all) → compensated → verified… 
    resultado verificado-durable Y decisión registrada Y reserva vacía.
    Ninguna op {COMMITTED,NOT_EXECUTED} si alguno outcome_axis=UNKNOWN.
    compensation_axis='FAILED' cierra como FAILED_CONSUMED; jamás COMMITTED.
```

### 1.6 — LegalState (agrega ejes al nivel op)

```
LegalState(op) :=
  ∀e: outcome(e) ≠ UNKNOWN
  ∧ ∀e: outcome(e) = NOT_EXECUTED ⇒ compensation(e) ∈ {NOT_REQUIRED, VERIFIED}
  ∧ p(op) ∉ {P_NONTERMINAL ∩ Aborted(op)}           -- abort no produce la transición a COMMIT
  ∧ (eso ∈ ESO_KNOWN_OUTCOME ∨ e.runtime_observed)   -- evidencias suficientes
```

### 1.7 — Histórico inmutable de compensación

`CompensationAxis` sólo avanza en el orden `NOT_REQUIRED → PENDING → VERIFIED | FAILED` y no retrocede jamás; registro append-only con índice único en `(operation_id, effect_ordinal)` para mantener la integridad del histórico sin desvanecer el rastro de ejecución.

---

## 2. R7-B — Modelo de dependencias y universo Λ cerrado (corrige CR-21 / CR-28)

### 2.1 — Dos relaciones, no una sola

```
D_G : Units → P(Gates)     — unidad depende estructuralmente de un gate;
D_U : Units → P(Units)     — unidad depende de otra unidad (precedencia lógica de la clásica).
```

Gates externos: `{G-§1, G-B04, G-PKI, G-ANY, G-INT, G-ANCLA, G-EFFECT, G-GRAPH, G-AUD, G-THIRD}` con sus significados ya definidos en v6.

Universo Λ cerrado (enumeración completa; sin semillas abstractas):

```
Λ := R1 ∪ R1.3 ∪ AUD
R1 := {SI-001..004, TR-001..003, ESS-001..005, OD-001..004, V-001..003, P-001..010,
       O-001..004, T-001..003, ESO-001..006, P-200..204, ESO-200, ESO-201}            (49)
R1.3 := {ES-001..007, FG-001..004, PL-001..003, SC-001..003, EF-001..002}              (19)
AUD := H-01..27 ∪ AUD-001..019 ∪ RES-1..9 ∪ M-01..10 ∪ 
        A-01..A-04 ∪ A-T(?! A-05 … ) ∪ B,C,D,E,F,G ∪ C-01..19 ∪ N-01..10             (104)

|Λ| = 49 + 19 + 104 = 172
```

### 2.2 — R1.3 se declara explícitamente como «sellado opcional, no normativo»

R1.3 no forma parte del canon hasta que el propietario cierre el artefacto; hasta entonces:
63 símbolos `DECLARED`, ninguno `VERIFIED`, ninguno `ACCEPTED`.

### 2.3 — B₀ es explícito, no abstracto

```
B₀-gates := {G-§1, G-B04, G-PKI, G-ANY, G-INT, G-ANCLA, G-EFFECT, G-GRAPH}
B₀-seed  := prefijos H/AUD/C × su gate crítico propio (tablas del §1 de v6, §Hereafter).

B₀ := { u ∈ Λ : ∃ g ∈ B₀-gates: g ∈ D_G(u) }.
```

### 2.4 — Propagación B₀ sobre D_U

```
B := B₀
repeat:
  for u in Λ:
    if u ∉ B and D_U(u) ∩ B ≠ ∅: B := B ∪ {u}
until no change
B* := B
```

### 2.5 — Precedencia

- u ∈ B*  ⇔  u depende (directa o transitivamente) de algún bloqueado primario.
- u ∉ B*  ⇔  u no tiene dependencias conflictivas directas ni transitivas.
- G-AUD/G-THIRD sólo marcan investigación pendiente; no son bloqueantes, pero tampoco dan luz verde.

### 2.6 — Referencia: por qué Λ_seed de v6 estaba vacío

v6 declaró Λ_SEED como variable abstracta. En v7 Λ queda concreto: Λ = R1 ∪ R1.3 ∪ AUD = 172. Se elimina Λ_SEED, Λ_AUDIT sin definición, y cualquier cardinalidad conjetural.

---

## 3. R7-C — DDL coherente y ejecutable-ish (corregir CR-25, CR-20, CR-18)

### 3.1 — Reglas de cobertura

- `attempt.attempt_generation` se invalida automáticamente por `operation.current_attempt_generation` (CHECK en la inserción mediante trigger lineal).
- `effect` referencia `attempt(attempt_id, operation_id, scope_id)` compuesto; jamás un intento ajeno.
- `effect` devuelve contadores vacíos y cierra ELetras de operación sin efectos confirmados; success leg sólo bajo PL-001 con manifiesto vacío.
- Ningún efecto puede ser creado sin vinculado a un `attempt` publicado y válido.
- `task_revision` es un compromiso exterior signado.

### 3.2 — `effect` coherente

```sql
CREATE TABLE effect (
  scope_id         bytea NOT NULL REFERENCES scope(scope_id),
  operation_id     bytea NOT NULL REFERENCES operation(operation_id),
  effect_ordinal   smallint NOT NULL CHECK (effect_ordinal BETWEEN 0 AND 254),
  effect_kind      smallint NOT NULL CHECK (effect_kind BETWEEN 0 AND 65535),
  attempt_id       bytea NOT NULL REFERENCES attempt(attempt_id),
  execution_axis   text NOT NULL DEFAULT 'NEVER_EXECUTED'
                   CHECK (execution_axis IN ('NEVER_EXECUTED','EXECUTED','DISCHARGED')),
  compensation_axis text NOT NULL DEFAULT 'NOT_REQUIRED'
                   CHECK (compensation_axis IN ('NOT_REQUIRED','PENDING','VERIFIED','FAILED')),
  outcome_axis     text NOT NULL DEFAULT 'NOT_EXECUTED'
                   CHECK (outcome_axis IN ('NOT_EXECUTED','COMMITTED','UNKNOWN')),
  policy_result    text NOT NULL DEFAULT 'PENDING'
                   CHECK (policy_result IN ('PENDING','VERIFIED','FAILED','COMPENSATED_ALL','UNKNOWN')),
  executed_at      timestamptz,
  verified_at      timestamptz,
  compensated_at   timestamptz,
  evidence_hash    bytea,
  row_version      smallint NOT NULL DEFAULT 1,
  UNIQUE (scope_id, operation_id, effect_ordinal),
  CONSTRAINT execution_before_compensation
    CHECK (compensation_axis <> 'VERIFIED' OR execution_axis IN ('EXECUTED','DISCHARGED')),
  CONSTRAINT outcome_not_unknown_required_success
    CHECK (outcome_axis <> 'COMMITTED' OR execution_axis IN ('EXECUTED','DISCHARGED')),
  CONSTRAINT no_compensation_without_execution
    CHECK (compensation_axis <> 'VERIFIED' OR execution_axis <> 'NEVER_EXECUTED')
);

CREATE TRIGGER effect_set_revision
  BEFORE INSERT OR UPDATE OF execution_axis, compensation_axis, outcome_axis, policy_result, evidence_hash
  ON effect FOR EACH ROW
  EXECUTE FUNCTION effect_revision_bump();

CREATE FUNCTION effect_revision_bump() RETURNS trigger AS $$
BEGIN
  NEW.row_version := OLD.row_version + 1;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
```

### 3.3 — `operation` head publish según R1 OD + head inmutabilidad

`od` no puede revertirse una vez confirmada admisión: trigger `operation_od_immutable` obliga: si OD-ENGINE abrió `ADMITTED`, el intento sólo avanza monotónicamente; `od=BLOCKED` o `NOT_DETERMINED` sólo pueden cerrar con consentimiento durable y se persisten por append.

### 3.4 — FK compuesta para effect

`effect` referencia `attempt(scope_id, operation_id, attempt_id)`; composición: `attempt.operation_id = effect.operation_id`, `attempt.scope_id = effect.scope_id` mediante FK compuesta.

### 3.5 — Closure OK cruzada de columnas

Trigger `effect_operation_closure_check` encierra:
- cerrar operation ⇒ todos los efectos outcome_axis NOT UNKNOWN
- cierre sólo si exécution final probada, compensación trazada si aplica.

---

## 4. R7-D — Máquina de reclamación/asignación (corrige CR-18)

### 4.1 — Estados explícitos de reclamo

```
ClaimStates: CREATED → FENCED → PUBLISHED → ACKED | FAILED | EXPIRED_RETRYABLE | ABORTED
CanPublishSelection := VALID | EXPIRED | STALE_SCOPE_EPOCH
PublishSelection := exact scope/fence match.
```

### 4.2 — Reglas

- Fence asignado antes de cualquier INSERT de intento.
- Scope bloqueado en la misma TX que el UPDATE del fence.
- publication proof persistido (`scope_event` tipo `FENCE_PUBLISHED`).
- `cap.fence = allocated` en la persistencia persisted.
- ack-correlation con nonce único por scope: `(scope_id, fence)` UNIQUE.
- Fences POST-publication revocadas separadamente por decisión explícita.

### 4.3 — Invariante multi-scope

- Dos scopes se bloquean sin deadlock mediante orden jerárquico global `scope_id` bytes lexicographic.
- Saga mínima de verificación pair-wise tras aborto parcial.

### 4.4 — Expiración / retry

```
FENCED sin ACK en N segundos ⇒ expired-retryable ⇒ suena bell / sólo permite reclamo (nunca cierre).
PERSISTED-PAUSE sólo permite nuevos intentos marcados RETRY con fence efectivo.
FAILED ⇒ terminal-back-off SCOPE-WIDE human-only with explicit decision log.
```

---

## 5. R7-E — Registro de claves y ancla anti-rollback (corrige CR-22 / CR-23)

### 5.1 — Registro inmutable de eventos

```
KeyRegistry := append-only:
  event_id      bytea PRIMARY KEY,
  key_id        bytea REFERENCES key_index(key_id),     -- append-only también
  role          text CHECK ('SINK_W'|'W_CLAIM'|'SCOPE_AUTHORITY'|'REOPEN_VERIFIER'),
  op_decl       bytea,
  op_witness    bytea,
  scope_id      bytea,
  valid_from    timestamptz NOT NULL,
  valid_to      timestamptz,
  revoke        boolean,
  authority_sig bytea,
  body          jsonb                                   -- raw signed body
```

### 5.2 — Revocación por evento, no por mutación

```
key_index := registro append-only de identidades públicas y dependencias; never UPDATE, never DELETE, only INSERT.
revoke := index insert con op_decline timestamp; never DELETE, never UPDATE.
```

### 5.3 — Anclaje con huella externa

```
timestamper := servicio externo independiente con clave pública publicada.
anchor := { seq, root_hash, state, signature_by_timestamper }
anchor_seq is MONOTONICALLY INCREASING; last_anchor must not go backwards.
Los anclajes intermedios deben reconstruirse cargo-eco para ser verificables.
Si ambos almacenes divergen ⇒ fail-closed; no es posible commit de efectos.
```

### 5.4 — Autoridad

- Anchored records son visibles antes de cualquier decisión crítica.
- Respaldo vs rollback distinguen: crisp rollback vs soft stall.
- Resolución de conflicto: verificador asignado para AMBOS almacenes.

---


## 6. R7-F — Matriz normalizada de 104 unidades (vocabulario único)

Vocabulario: `REPAIR_REQUIRED` · `BLOCKED` · `NOT_APPLICABLE`. Ninguna otra etiqueta.
Cada unidad declara: gates, estado y motivo en una línea reproducida aquí; nada se ratifica.

Leyenda rápida: R=REPAIR_REQUIRED, B=BLOCKED, NA=NOT_APPLICABLE.

```
Scope

  H-01 R G-AUD
  H-02 R G-AUD
  H-03 B G-ANCLA
  H-04 R G-B04+G-AUD
  H-05 B G-B04
  H-06 B G-PKI
  H-07 R G-B04+G-AUD
  H-08 R G-AUD
  H-09 R G-AUD
  H-10 R G-B04+G-AUD
  H-11 B G-B04
  H-12 B G-PKI
  H-13 B G-PKI
  H-14 B G-ANY
  H-15 B G-ANY
  H-16 R G-AUD
  H-17 B G-EFFECT
  H-18 B G-ANY
  H-19 R G-AUD
  H-20 R G-GRAPH
  H-21 B G-GRAPH
  H-22 R G-AUD
  H-23 B G-AUD
  H-24 B G-PKI
  H-25 B G-B04
  H-26 B G-ANY
  H-27 R G-GRAPH

  AUD-001 R G-AUD · AUD-002 R G-AUD · AUD-003 R G-AUD · AUD-004 R G-AUD
  AUD-005 R G-AUD · AUD-006 R G-AUD · AUD-007 B G-PKI · AUD-008 R G-AUD
  AUD-009 R G-AUD · AUD-010 R G-AUD · AUD-011 B G-B04 · AUD-012 R G-AUD
  AUD-013 B G-ANY · AUD-014 B G-ANY · AUD-015 B G-AUD · AUD-016 R G-AUD
  AUD-017 R G-AUD · AUD-018 B G-ANY · AUD-019 B G-ANY

  RES-1 R G-AUD · RES-2 R G-AUD · RES-3 R G-AUD
  RES-4 R G-AUD · RES-5 R G-AUD · RES-6 B G-PKI
  RES-7 R G-AUD · RES-8 R G-AUD · RES-9 R G-AUD

  M-01 B G-ANY · M-02 R G-AUD · M-03 R G-AUD · M-04 B G-PKI
  M-05 R G-GRAPH · M-06 R G-AUD · M-07 B G-PKI · M-08 R G-AUD
  M-09 R G-AUD · M-10 R G-GRAPH

  A-01 R G-AUD · A-02 R G-AUD · A-03 B G-GRAPH · A-04 B G-INT
  F B G-ANY · G R G-AUD · E B G-PKI · B B G-B04
  C B G-ANY · D B G-ANY

  C-01 B G-B04+G-AUD · C-02 B G-B04 · C-03 B G-ANY · C-04 B G-PKI
  C-05 R G-AUD · C-06 R G-AUD · C-07 B G-GRAPH · C-08 B G-B04
  C-09 B G-ANCLA · C-10 B G-B04+G-AUD · C-11 B G-B04+G-AUD · C-12 B G-EFFECT
  C-13 B G-ANY · C-14 B G-AUD · C-15 B G-INT · C-16 B G-EFFECT
  C-17 B G-GRAPH · C-18 B G-B04 · C-19 B G-ANCLA

  N-01 B G-B04+G-AUD · N-02 B G-EFFECT · N-03 B G-EFFECT · N-04 B G-B04
  N-05 B G-INT · N-06 B G-ANCLA · N-07 R G-PKI · N-08 R G-AUD
  N-09 R G-AUD · N-10 R G-AUD
```

## 7. Recapitulación de estados (conteos verificados)

- NOT_APPLICABLE: 0
- REPAIR_REQUIRED: 48 (declarados; ningún cotejo ejecutado)
- BLOCKED: 56 (dependencia estructural de gates; ver §1)
- Ninguna fila declara validación ejecutable ni cierre.

## 8. Apéndice — LegalClose y PartialState independiente de cierre

```
AbsoluteClose := ∀e ∈ effects(op): outcome_axis ∈ {NOT_EXECUTED, COMMITTED}
             ∧  AllCompensationVerified or all compensation_axis NOT_REQUIRED
             ∧  p ∈ {COMMIT_DURABLE, ABORT_DURABLE}
             ∧  eso = TESTIFIED(op)
             ∧  t(op) ≠ UNKNOWN
             ∧  no e has outcome_axis UNKNOWN
```

## 9. Estado final tras esta revisión

- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `D-315 = PENDING` · `MODEL_VERIFIED=NO` · `IMPLEMENTATION_READY=NO` · `PROMOTION=NOT_READY` · `THIRD_PARTY_REVIEW=REQUIRED`.
- Nada ejecutado: **ninguna** prueba de compilación, concurrencia, CRL, despliegue o terceros se ha ejecutado.
- `R1` no se modifica. `R1.3` no se acepta.
- `B07_FORMAL_MODEL.md` intacto; §1 intacta.
- Antecedentes v1…v6 preservados; este documento no sustituye la auditoría.

Fin R2-A REVISION 7 · DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED · Procedencia `state/multiproject/log.md`.
