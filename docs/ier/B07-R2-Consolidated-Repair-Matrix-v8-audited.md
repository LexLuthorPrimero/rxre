# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 8 CORREGIDO

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** v2.r2 (`9c8a0aba…`) **INMUTABLE**; esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1…v7 (`e1…/10…/e1…/5d…/52…/34…/698d…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. r3 NO autorizada. R3 BLOCKED. promoción NOT_READY.

Registro: v7 published `61f33ca…` (NOT_RATIFIABLE) → **R8** correctiva de v7 con R8-B (grafo), R8-F (contenido individual), máquina de efectos reescrita y DDL coherente.

---

## 0. Leyenda

Estados únicos: `REPAIR_REQUIRED` · `BLOCKED` · `NOT_APPLICABLE`. El estado de una fila = estado de su **reparación** documental (eje de esta auditoría): una fila no comunica el estado de aceptación por terceros ni el propio modelo.

---

## 1. R8-C — Máquina de efectos exhaustiva y cierre único

### 1.1 — Ejes y valores

```
DispatchState  ∈ {NOT_DISPATCHED, DISPATCHED, ACCEPTED, REJECTED, UNKNOWN}
ExecutionState ∈ {NOT_CONFIRMED, EXECUTED, FAILED_CONFIRMED, UNKNOWN}
CompensationState ∈ {NOT_REQUIRED, PENDING, VERIFIED, FAILED}
Outcome ∈ {NOT_EXECUTED, COMMITTED, COMPENSATED, UNKNOWN}
```

### 1.2 — Tabla exhaustiva de combinaciones (axes ≡ effects)

| dispatch | execution | compensation | outcome | validez |
|---|---|---|---|---|
| NOT_DISPATCHED | * | NOT_REQUIRED | NOT_EXECUTED | válida (efectos no despachables, PL-001) |
| NOT_DISPATCHED | * | PENDING / VERIFIED / FAILED | * | INVÁLIDA (no despachado no exige compensación) |
| DISPATCHED | NOT_CONFIRMED | NOT_REQUIRED | UNKNOWN | válida en vuelo; implica verificación pendiente |
| DISPATCHED | NOT_CONFIRMED | PENDING | UNKNOWN | válida máxima |
| DISPATCHED | NOT_CONFIRMED | VERIFIED/FAILED | * | INVÁLIDA salvo sección de compensación confirmada |
| ACCEPTED | EXECUTED | NOT_REQUIRED | COMMITTED | válida éxito simple |
| ACCEPTED | EXECUTED | PENDING | UNKNOWN | válida (executing ya confirmed → outcome UNKNOWN) |
| ACCEPTED | EXECUTED | VERIFIED | COMPENSATED | válida (exec + compensated + verified ⇒ outcome COMPENSATED) |
| ACCEPTED | EXECUTED | FAILED | UNKNOWN | válida; policy no satisfecha |
| ACCEPTED | FAILED_CONFIRMED | NOT_REQUIRED | NOT_EXECUTED | válida (FAILED_CONFIRMED ⇒ never COMMITTED) |
| ACCEPTED | FAILED_CONFIRMED | PENDING | UNKNOWN | válida |
| ACCEPTED | FAILED_CONFIRMED | VERIFIED/FAILED | * | INVÁLIDA/INALCANZADA (FAILED+VERIFIED = failed commuted/transaction) |
| REJECTED | NOT_CONFIRMED | NOT_REQUIRED | NOT_EXECUTED | válida (provider rej computa no-op) |
| REJECTED | * | PENDING/VERIFIED/FAILED | * | INVÁLIDA (rechazado nunca entra a compensación) |
| UNKNOWN | * | * | UNKNOWN | válida; cierre prohibido |

Exclusión mutua: for all (dispatch, execution, compensation) ∈ grid, exactly one outcome is assigned; if a triple is not listed ⇒ REJECTED.

### 1.3 — Peor caso: transiciones procedentes de máquina R1

`P.EXECUTING → P.COMMIT_DURABLE | P.ABORT_DURABLE` requieren NOT_DESPATCHED ∈ effects ⇒ ningún efecto despachado permanece NOT_CONFIRMED; ejecución confirmada completa antes de `COMMIT_DURABLE`; `ABORT_DURABLE` exec/execution-history preservado. `O.COMMITTED` sólo si policy satisfied by allDispatchedEffects = VERIFIED ⇒ any referenced effect with policy_satisfied compatible.

### 1.4 — LegalClose (predicado único)

```
LegalClose(op) ⇔
    LegalState(op)                                     // máquinas R1 consistentes
  ∧ p(op) ∈ P_TERMINAL(op)                            // COMMIT_DURABLE | ABORT_DURABLE
  ∧ ∀ e ∈ effects(op): Terminal(e)                      // tabla §1.2 exhaustiva
  ∧ PolicySatisfied(op, effects(op))                     // reglas siguientes

Terminal(e) ⇔
    e.dispatch ∈ {ACCEPTED, REJECTED}
  ∧ e.execution ∉ UNKNOWN
  ∧ (e.compensation ∈ {NOT_REQUIRED, VERIFIED})
  ∧ e.outcome ≠ UNKNOWN

PolicySatisfied(op, effects):
  PL-002 ANY ⇔
      ∃ ! e: e.outcome = COMMITTED,
      ∀ e'≠e: e'.outcome ∈ {COMMITTED, NOT_EXECUTED, COMPENSATED},
      ∀ e': e'.dispatch ≠ UNKNOWN
  PL-003 ALL ⇔
      ∀ e: e.outcome = COMMITTED
  PL-001 NONE ⇔
      ∀ e: e.dispatch ∈ {NOT_DISPATCHED, REJECTED}

Payloads vacío (boundary):
  effects = [] ∧ PL-001 NONE ⇒ legal; O=NONE; p→ABORT_DURABLE.
  effects = [] ∧ ANY/ALL    ⇒ policy_unsatisfiable; cierre prohibido; decisión durable (abort + verificación del manifiesto) requerida.
```

### 1.5 — Closure único para ANY incluyendo efectos pendientes

Si ANY ya satisfecho (≥1 VERIFIED) but some e's remain DISPATCHED with NOT_CONFIRMED execution ⇒ cierre prohibido; effects must reach terminal classes before seal. PSEUDO: `policySatisfied = EXISTS e.outcome=COMMITTED ∧ ∀e': e'.outcome ∈ {COMMITTED, COMPENSATED, NOT_EXECUTED}`.

### 1.6 — Test vectors canonical & discriminantes

Vector de prueba documental (byte canónico, no ejecutable en esta entrega):
- arity-1 triple `(ACCEPTED, EXECUTED, NOT_REQUIRED) → COMMITTED` ✓
- arity-2 triple `(DISPATCHED, NOT_CONFIRMED, NOT_REQUIRED) → UNKNOWN` ✓
- triplet invalid `(REJECTED, EXECUTED, …)` ⇒ rejected check 
- arity-4: `(ACCEPTED, EXECUTED, PENDING, ANY) → ineligible cierre` ✓
- arity-5: vacío effects with PL-001 ⇒ legal; PL002/003 ⇒ ilegal ✓

---

## 2. R8-B — Grafo materializado (B₀, B*)

### 2.1 — Universo canónico Ξ

`Λ_canon :=` **R1, 49 símbolos** del artefacto sellado de fábrica (`B07_FORMAL_MODEL.md` §R1, hash a7273d58…).
`Λ_audit  :=` las 104 unidades de reparación documental listadas en §6.
`Λ        :=` Λ_canon ∪ Λ_audit.

### 2.2 — Gates canónicos

```
G-§1    §1 congelada (precondición permanente)
G-B04   fencing authority / B-04 OPEN   (autoridad de reclamo)
G-PKI   sistema de identidad y pública clave (D-R2R2-1)
G-ANY   cierre con resolución externa de efectos
G-INT   integridad/edificación de manifiesto
G-ANCLA anti-rollback externo (anchor proof)
G-EFFECT persistencia de efectos
G-GRAPH universo Λ / deps sin cerrar
G-AUD   evidencia ejecutable/cotejo pendiente (no bloquea estructuralmente)
```

### 2.3 — Mapa D_G (unidad→gates) y D_U (unidad→unidad)

D_G se publica como tabla siguiente (misma decisión que v6, conservada bajo revisión). D_U se publica sólo para unidades que dependen de otra unidad concreta; ausencia de declaración implica D_U(u)=∅ y, por tanto, B*(u) depende únicamente de B* de D_G(u).

```
H-01:{AUD} H-02:{AUD} H-03:{ANCLA} H-04:{B04,AUD} H-05:{B04} H-06:{PKI}
H-07:{B04,AUD} H-08:{AUD} H-09:{AUD} H-10:{B04,AUD} H-11:{B04} H-12:{PKI}
H-13:{PKI} H-14:{ANY} H-15:{ANY} H-16:{AUD} H-17:{EFFECT} H-18:{ANY}
H-19:{AUD} H-20:{GRAPH} H-21:{GRAPH} H-22:{AUD} H-23:{AUD} H-24:{PKI}
H-25:{B04} H-26:{ANY} H-27:{GRAPH}
AUD-001:{AUD} AUD-002:{AUD} AUD-003:{AUD} AUD-004:{AUD} AUD-005:{AUD} AUD-006:{AUD}
AUD-007:{PKI} AUD-008:{AUD} AUD-009:{AUD} AUD-010:{AUD} AUD-011:{B04}
AUD-012:{AUD} AUD-013:{ANY} AUD-014:{ANY} AUD-015:{AUD} AUD-016:{AUD}
AUD-017:{AUD} AUD-018:{ANY} AUD-019:{ANY}
RES-1:{AUD} RES-2:{AUD} RES-3:{AUD} RES-4:{AUD} RES-5:{AUD} RES-6:{PKI}
RES-7:{AUD} RES-8:{AUD} RES-9:{AUD}
M-01:{ANY} M-02:{AUD} M-03:{AUD} M-04:{PKI} M-05:{GRAPH} M-06:{AUD} M-07:{PKI} M-08:{AUD} M-09:{AUD} M-10:{GRAPH}
A-01:{AUD} A-02:{AUD} A-03:{GRAPH} A-04:{INT} B:{B04} C:{ANY} D:{ANY} E:{PKI} F:{ANY} G:{AUD}
C-01:{B04,AUD} C-02:{B04} C-03:{ANY} C-04:{PKI} C-05:{AUD} C-06:{AUD} C-07:{GRAPH} C-08:{B04}
C-09:{ANCLA} C-10:{B04,AUD} C-11:{B04,AUD} C-12:{EFFECT} C-13:{ANY} C-14:{AUD} C-15:{INT}
C-16:{EFFECT} C-17:{GRAPH} C-18:{B04} C-19:{ANCLA}
N-01:{B04,AUD} N-02:{EFFECT} N-03:{EFFECT} N-04:{B04} N-05:{INT} N-06:{ANCLA} N-07:{PKI} N-08:{AUD} N-09:{AUD} N-10:{AUD}
```

D_U (unidad→unidad) vacío en esta revisión (ningún requisito de reparación declara dep de otra reparación concreta); consecuencia: `B* = B₀`. G-AUD NO conduce a BLOCKED por sí sola; iba quedar «pendiente» sólo denotativo.

### 2.4 — Bloques

```
B₀ = { H-03, H-05, H-06, H-11, H-13, H-14, H-15, H-17, H-18, H-21, H-23, H-24, H-25, H-26,
       AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019,
       A-03, A-04, B, C, D, E, F,
       C-01, C-02, C-03, C-04, C-07, C-08, C-09, C-12, C-13, C-15, C-16, C-17, C-18, C-19,
       M-01, M-04, M-05, M-07, M-10,
       N-01, N-02, N-03, N-04, N-05, N-06 }
|B₀| = 46.
B* = B₀ (D_U = ∅).
```

Interpretación: 46 unidades bloqueadas por gates estructurales; 58 quedan REPAIR_REQUIRED (pendientes de reparación documental/verificación); cero NOT_APPLICABLE.

---


## 3. R8-C — DDL coherente (ejecutable diseñadamente; no se ejecuta aquí)

```sql
CREATE TABLE scope (
  scope_id             bytea PRIMARY KEY,
  scope_epoch          bigint NOT NULL CHECK (scope_epoch >= 0),
  si                   text NOT NULL CHECK (si IN ('HEALTHY','ROLLBACK_DETECTED','RECONCILIATION_REQUIRED','HUMAN_CLOSED')),
  trs                  text NOT NULL CHECK (trs IN ('VALID','QUARANTINED','NOT_DETERMINED')),
  ess                  text NOT NULL CHECK (ess IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','CONTRADICTION')),
  minimum_valid_fence  bigint NOT NULL DEFAULT 0 CHECK (minimum_valid_fence >= 0),
  next_fence           bigint NOT NULL DEFAULT 0 CHECK (next_fence >= 0),
  CHECK (next_fence >= minimum_valid_fence)
);

CREATE TABLE operation (
  operation_id              bytea PRIMARY KEY,
  scope_id                  bytea NOT NULL REFERENCES scope(scope_id),
  scope_epoch               bigint NOT NULL CHECK (scope_epoch >= 0),
  od                        text NOT NULL CHECK (od IN ('NOT_EVALUATED','ADMITTED','BLOCKED','NOT_DETERMINED')),
  v                         text NOT NULL CHECK (v IN ('OPEN','SUSPENDED','CLOSED')),
  p                         text NOT NULL CHECK (p IN ('NOT_STARTED','RESERVE_REQUESTED','RESERVE_DURABLE','RESERVED_CONFIRMED','EXECUTING','COMMIT_DURABLE','ABORT_DURABLE','RECOVERABLE','RESERVE_ORPHAN','FAILED_CONSUMED')),
  o                         text NOT NULL CHECK (o IN ('NONE','COMMITTED','NOT_EXECUTED','UNKNOWN')),
  t                         text NOT NULL CHECK (t IN ('NONE','COMMIT_TESTIFIED','ABORT_TESTIFIED')),
  eso                       text NOT NULL CHECK (eso IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','TESTIFICATION_PENDING','TESTIFIED')),
  operation_kind            smallint NOT NULL CHECK (operation_kind BETWEEN 0 AND 255),
  policy_version            bigint NOT NULL CHECK (policy_version >= 0),
  request_id                bytea NOT NULL,
  current_attempt_id        bytea NULL,
  current_attempt_generation smallint NOT NULL DEFAULT 0 CHECK (current_attempt_generation BETWEEN 0 AND 255),
  manifest_hash             bytea NOT NULL CHECK (octet_length(manifest_hash) = 32),
  first_fence               bigint NOT NULL,
  UNIQUE (scope_id, scope_epoch, operation_kind, request_id),
  UNIQUE (scope_id, operation_id)
);

CREATE TABLE attempt (
  scope_id           bytea NOT NULL REFERENCES scope(scope_id),
  operation_id       bytea NOT NULL REFERENCES operation(operation_id),
  attempt_id         bytea PRIMARY KEY,
  attempt_generation smallint NOT NULL CHECK (attempt_generation BETWEEN 1 AND 255),
  claim_generation   bigint NOT NULL CHECK (claim_generation BETWEEN 1 AND 18446744073709551615),
  fencing_token      bigint NOT NULL CHECK (fencing_token BETWEEN 0 AND 18446744073709551615),
  binding_hash       bytea NOT NULL CHECK (octet_length(binding_hash) = 32),
  UNIQUE (operation_id, attempt_generation),
  FOREIGN KEY (scope_id, operation_id)
    REFERENCES operation(scope_id, operation_id) ON DELETE RESTRICT
);

CREATE TABLE effect (
  scope_id         bytea NOT NULL REFERENCES scope(scope_id),
  operation_id     bytea NOT NULL REFERENCES operation(operation_id),
  effect_ordinal   smallint NOT NULL CHECK (effect_ordinal BETWEEN 0 AND 254),
  attempt_id       bytea NOT NULL,
  dispatch_state   text NOT NULL CHECK (dispatch_state IN ('NOT_DISPATCHED','DISPATCHED','ACCEPTED','REJECTED','UNKNOWN')),
  execution_state  text NOT NULL CHECK (execution_state IN ('NOT_CONFIRMED','EXECUTED','FAILED_CONFIRMED','UNKNOWN')),
  compensation     text NOT NULL CHECK (compensation IN ('NOT_REQUIRED','PENDING','VERIFIED','FAILED')),
  outcome          text NOT NULL CHECK (outcome IN ('NOT_EXECUTED','COMMITTED','COMPENSATED','UNKNOWN')),
  evidence_hash    bytea,
  row_version      integer NOT NULL DEFAULT 1,
  UNIQUE (scope_id, operation_id, effect_ordinal),
  FOREIGN KEY (operation_id, attempt_id)
    REFERENCES attempt(operation_id, attempt_id) ON DELETE RESTRICT
);

-- Trigger order documented explicitly:
--   effect_before_ins (BEFORE INSERT)
--   effect_before_upd (BEFORE UPDATE)
--   effect_before_del (BEFORE DELETE)  → forbid
--   operation_od_immutable (BEFORE UPDATE)
--   operation_head_check (BEFORE INSERT OR UPDATE)
```

## 4. R8-D — Fencing y suspensión formal

### 4.1 — Máquina de reclamo

```
 states: CREATED → FENCED → PUBLISHED → WRITTEN | ABANDONED | EXPIRED_RETRYABLE
flow:
  1. tx{ sel op FOR UPDATE; check od ∈ {NOT_EVALUATED};
        UPDATE scope SET next_fence = next_fence + 1
           WHERE scope_id = op.scope_id;
        INSERT attempt(scope_id, op, gen = op.current_attempt_generation + 1,
                       claim_generation = scope.next_fence,
                       fencing_token = scope.next_fence) RETURNING attempt_id;
        UPDATE operation SET current_attempt_id = attempt_id,
                            current_attempt_generation = op.current_attempt_generation + 1
         WHERE operation_id = op.operation_id; commit; }
  2. publish FENCE_COMMUNICATED durablemente (append-only scope_event; visible antes del uso del token).
  3. abort path: scope_event FENCE_ABANDONED durable; op queda RESERVE_ORPHAN; fence remains consumed/frozen (no reutiliza jamás).
INVARIANTES:
  * fencing_token >= MIN(next_fence) at mint; unique per scope.
  * never reuse; gen exhausted ⇒ op culminates in FAILED_CONSUMED (no new attempts).
```

### 4.2 Suspensión

```
 states: ACTIVE → SUSPEND_REQUESTED → SUSPENDED → REOPEN_EVIDENCE → RESUMED | TERMINAL_HUMAN
flow:
  1. tx{ FOR UPDATE on scope; scope_event RECONCILIATION_REQUIRED durable;
        UPDATE scope SET si = RECONCILIATION_REQUIRED, minimum_valid_fence = next_fence;
        commit; }
  2. W y verifier independiente confirman REOPEN_EVIDENCE (predicate canonical).
  3. tx{ FOR UPDATE; scope_epoch := scope_epoch + 1; scope_event RECONCILE_RESOLVED; commit; }
suspend no revoca efectos; efectos en vuelo se reconcilian bajo efecto contrato.
```

### 4.3 ACK tardío

`ACK` consumido ∈ (suspension_epoch, reopen_epoch) ⇒ se descarta; el dispatch locking exige fence >= current minimum_valid_fence (owner-locked heartbeat).

---


## 5. R8-E — PKI y ancla anti-rollback

### 5.1 KeyRegistry

```
 key_registry := append_only,
  key_id          bytea PRIMARY KEY,
  public_key      bytea NOT NULL CHECK (octet_length(public_key)=32),
  role            text NOT NULL CHECK (role IN ('SINK_W','W_CLAIM','SCOPE_AUTHORITY','REOPEN_VERIFIER')),
  scope_id        bytea,
  valid_from      timestamptz NOT NULL,
  valid_to        timestamptz,
  revocation_key_id bytea,        -- referencia a esta fila: revocation_event (evento posterior)
  sign_me         bytea NOT NULL,  --        ...
  issued_at_seq   bigint NOT NULL,
  supersedes      bytea           -- referencia a fila anterior de la misma key_id (superseded-by-key_id)
');
```

Roles según engine:
`SINK_W` ejecuta ejecuciones; `W_CLAIM` emite W penultimate; `SCOPE_AUTHORITY` firma events del scope; `REOPEN_VERIFIER` verifica REOPEN_EVIDENCE.

### 5.2 Ancla anti-rollback

```
 anchor := { seq, root_hash, ts, sig } anchor_seq strictly monotone cuerda;
evidence of anchors: anchor_log (seq, root_hash, ts) — seq UNIQUE.
 chain independent of primary storage: the anchor is externally signed by an indep. actor.
 restoration old <> fresh never: restored replica missing any seq ≥ last_anchor visible ⇒ freeze writes read-only.
recover => verify anchors seq 1..N chain_pattern outward; exact target anchor only decoded
```

---

## 6. R8-F — 104 unidades (defecto → defecto → reparación → estado v7)

Estados: REPAIR_REQUIRED | BLOCKED. Columnas: unidad · defecto (ID del audit) | reparación · estado.

H-01 · hash sin vectors → §3 §1 bounds → REPAIR_REQUIRED
H-02 · ordinal local → §1 vector global dense → REPAIR_REQUIRED
H-03 · manifiesto sin ancla → §3 manifest embebido + §5 → BLOCKED
H-04 · head CAS → §4.1 → REPAIR_REQUIRED
H-05 · fencing no linealizado → §3/§4 protocol → BLOCKED
H-06 · REOPEN sin esquema → §5.1 KeyRegistry → BLOCKED
H-07 · evento sin esquema → §3 scope_event tabla+UNIQUE → REPAIR_REQUIRED
H-08 · FK compuesta → §3 → REPAIR_REQUIRED
H-09 · binding duplicado → §1 → REPAIR_REQUIRED
H-10 · idempotencia ausente → §1 idempotency_key → REPAIR_REQUIRED
H-11 · B-04 frontera → §3/§4.1 → BLOCKED
H-12 · doble consume → §4.1 → REPAIR_REQUIRED
H-13 · T-REOPEN → §4.1/§5.1 → BLOCKED
H-14 · cierre sin transición → §1 LegalClose → BLOCKED
H-15 · máquinas → §1 S/TI → BLOCKED
H-16 · INV-13 derivación → §1.5 pruebas → REPAIR_REQUIRED
H-17 · reconciliación sin orden → §4.3 → REPAIR_REQUIRED
H-18 · ESo=REJECTED terminal → §1 ESo mapping → REPAIR_REQUIRED
H-19 · tipos divergentes → §3 → REPAIR_REQUIRED
H-20 · barrera default-allow → §2.2 default-deny → REPAIR_REQUIRED
H-21 · census incompleto → §2.2/§3 → BLOCKED
H-22 · cardinalidad sin fundar → §6 census → REPAIR_REQUIRED
H-23 · sinks sin cobertura → §4 → BLOCKED
H-24 · TCB indefinido → §5 → BLOCKED
H-25 · LP despacho/suspensión → §4.2 → BLOCKED
H-26 · políticas ambiguas → §1.4× round → BLOCKED
H-27 · A6 propagación → §2.2 default-deny → REPAIR_REQUIRED

AUD-001 · campos inexistentes → §1 tabla S→V → REPAIR_REQUIRED
AUD-002 · binding duplicado → §1 → REPAIR_REQUIRED
AUD-003 · INV-06 redundant → §1 LegalClose único → REPAIR_REQUIRED
AUD-004 · elipsis INV-07 → §1 ESo dominio cerrado → REPAIR_REQUIRED
AUD-005 · ≈8640 → §2 vigente → REPAIR_REQUIRED
AUD-006 · §2.L vs §2.A → §1 normas únicas → REPAIR_REQUIRED
AUD-007 · epoch sin transición → §4.1/§5.1 → BLOCKED
AUD-008 · DDL sin binding → §3 → REPAIR_REQUIRED
AUD-009 · dep FG-001→ES-007 → §5.1 → REPAIR_REQUIRED
AUD-010 · índice bloquea retry → §1 → REPAIR_REQUIRED
AUD-011 · fencing interferencia → §4.1 → BLOCKED
AUD-012 · origen/sink → §1 → REPAIR_REQUIRED
AUD-013 · T13 atómica → §4.1 → REPAIR_REQUIRED
AUD-014 · UNKNOWN → §1 → REPAIR_REQUIRED
AUD-015 · R1.3 vocab → §2.2/§6 → BLOCKED
AUD-016 · INV-02 epochs → §3 → REPAIR_REQUIRED
AUD-017 · attempts → §3 → REPAIR_REQUIRED
AUD-018 · políticas → §1 → REPAIR_REQUIRED
AUD-019 · P/ESo/T/O → §3/§6 → REPAIR_REQUIRED

RES-1 · SinkAccept campo → §1 → REPAIR_REQUIRED
RES-2 · binding duplicate → §1 → REPAIR_REQUIRED
RES-3 · INV-06/INV-07 → §1 → REPAIR_REQUIRED
RES-4 · ≈8640 → §2 → REPAIR_REQUIRED
RES-5 · §2.L OD → §1 → REPAIR_REQUIRED
RES-6 · epoch bump → §4.1/§5.1 → REPAIR_REQUIRED
RES-7 · DDL binding → §3 → REPAIR_REQUIRED
RES-8 · deps sc-001 → §5.1 → REPAIR_REQUIRED
RES-9 · INV-13 → §1 → REPAIR_REQUIRED

M-01 · ESo=REJECTED → §1 → BLOCKED
M-02 · decided_at → §3/§4 → REPAIR_REQUIRED
M-03 · claim_generation → §3 tipos → REPAIR_REQUIRED
M-04 · IER-reopen-v1 → §5.1 → BLOCKED
M-05 · BND termino → §4/§6 → BLOCKED
M-06 · §7.5 referencia → §6 → REPAIR_REQUIRED
M-07 · rely salt → §5 → BLOCKED
M-08 · io tag → §6 → REPAIR_REQUIRED
M-09 · A-03/v2 unificación → §6 → REPAIR_REQUIRED
M-10 · fence-window → §4 → BLOCKED

A-01 · columna FK → §3 → REPAIR_REQUIRED
A-02 · bigint UINT64 → §3 → REPAIR_REQUIRED
A-03 · head CAS → §4 → REPAIR_REQUIRED
A-04 · manifest linked → §3/§4 → REPAIR_REQUIRED
A~ · coverage sink → §4 → REPAIR_REQUIRED

B · 2phase atomic → §3/§4 → BLOCKED
C · T-CLOSE effects → §3/§4 → REPAIR_REQUIRED
D · T13 → §4 → BLOCKED
E · preimagen → §5 → BLOCKED
F · empty policy → §1.4 → BLOCKED
G · coverage universal → §2.2 → REPAIR_REQUIRED

C-01 · head NULL/V → §4 → REPAIR_REQUIRED
C-02 · nh atómica → §4 → BLOCKED
C-03 · epoch pairs → §3 → BLOCKED
C-04 · preimagen → §5 → BLOCKED
C-05 · numeric → §3 → REPAIR_REQUIRED
C-06 · window close → §4 → REPAIR_REQUIRED
C-07 · atomic resume → §4 → REPAIR_REQUIRED
C-08 · cap sieve → §4/§5 → BLOCKED
C-09 · anchor → §5 → BLOCKED
C-10 · CAS → §3/§4 → REPAIR_REQUIRED
C-11 · dupe consume → §2/§4 → REPAIR_REQUIRED
C-12 · dense order → §6 → REPAIR_REQUIRED
C-13 · terminal compensación → §1/§3 → BLOCKED
C-14 · enforced sinks → §4 → BLOCKED
C-15 · permisos trigger → §3 → REPAIR_REQUIRED
C-16 · effect_key → §3 → REPAIR_REQUIRED
C-17 · A6 → §2.2 → REPAIR_REQUIRED
C-18 · atomic line → §4 → REPAIR_REQUIRED
C-19 · anchor bi → §5 → BLOCKED

N-01 · CHECK both → §3 → REPAIR_REQUIRED
N-02 · attempt key → §3 → REPAIR_REQUIRED
N-03 · order → §6 → REPAIR_REQUIRED
N-04 · cap binding → §5 → REPAIR_REQUIRED
N-05 · trigger → §3 → REPAIR_REQUIRED
N-06 · anchor ext → §5 → BLOCKED
N-07 · encode → §3 → REPAIR_REQUIRED
N-08 · splitting → §6 → REPAIR_REQUIRED
N-09 · splitting → §6 → REPAIR_REQUIRED
N-10 · domains → §6 → REPAIR_REQUIRED

## 7. Propagación cerrada

| Estado | Unidades |
|---|---|
| BLOCKED | H-03, H-05, H-06, H-11, H-13, H-14, H-15, H-18, H-21, H-23, H-24, H-25, H-26; AUD-006, AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019; A-03, A-04, B, D, E, F; C-01, C-02, C-03, C-07, C-09, C-13, C-14, C-19; M-01, M-03, M-04, M-05, M-07, M-10; N-06, N-09, N-10; N-01, N-02, N-03 |
| REPAIR_REQUIRED | cualquier unidad no listada |

B₀ = conjunto anterior; B* = B₀ (D_U = ∅); ninguna unidad aceptada.

## 8. Estado

- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `MODEL_VERIFIED = NO` · promoción `NOT_READY`.
- Antecedentes v1…v7 preservados; baseline intacto; §1 intacta; `B07_FORMAL_MODEL.md` intacto.
- `state/multiproject/log.md` registra esta revisión.

Fin R2-A REVISION 8 · DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED · Procedencia en `state/multiproject/log.md`.
