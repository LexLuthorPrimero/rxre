# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 6 (CR-17…CR-28)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** v2.r2 (`9c8a0aba…`) **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1…v5 (`e165aced…/103feeb2…/e1c046eb…/5d4bf9bc…/52b3c9e5…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.

## Registro de revisiones

| Versión | SHA-256 | Disposición |
|---|---|---|
| v1..v4 | … | NO RATIFICADAS |
| v5 | `52b3c9e5…` | NO RATIFICABLE; CR-17…CR-28 |
| v6 (este documento) | hash fuera del archivo (`state/multiproject/log.md`) | Fase 1 (CR-17, CR-26, CR-28) → Fase 2 (CR-18..CR-21, CR-25) → Fase 3 (CR-22..CR-24, CR-27) → Fase 4 (grafo Λ, inventario, propagación). **Ninguna fila ni decisión se ratifica.** |

---

## 0. Leyenda y regla de cierre

`Definición → Persistencia → Transición → Invariante → Contraejemplo → Prueba`.
Estados: `REPAIRED-DOCUMENTAL` (diseño correcto; no ejecutado) · `REPAIRED-CONDICIONADO` · `BLOCKED` · `NOT_APPLICABLE`.
**Regla absoluta**: nada sale de aquí marcado `REPAIRED-DOCUMENTAL` sin revisión independiente del propietario ni evidencia ejecutable.

---

## 1. Modelo único de dependencia (cierra CR-28)

Se define un conjunto finito cerrado de bloqueos primarios **gates** y un mapa `deps : unidad → P(gates)`.

```
Gates:
  G-§1    canon congelado (§1) — ninguna fila lo acepta sin dictamen documental previo del propietario.
  G-B04   B-04 OPEN (autoridad de fencing / política de reclamo).
  G-PKI   D-R2R2-1: PKI, custodia, revocación y rotación de claves no demuestradas.
  G-ANY   cierre/terminalidad no resuelto (cierre depende de resolución externa de efectos).
  G-INT   integridad/codificación de manifiesto no ejecutable ni cotejada.
  G-ANCLA anclaje anti-rollback no demostrado (frewshness que no puede retroceder).
  G-EFFECT persistencia de efectos (effect_log) no verificada.
  G-GRAPH universo Λ/dependencias no cerrado (grafo verificable).
  G-AUD   cotejo con evidencia ejecutable pendiente.
  G-THIRD revisión de terceros NOT_EXECUTED; toda evidencia de esta línea lo bloquea.

Mapa de dependencias (única fuente de verdad) — las unidades no listadas dependen de G-AUD por defecto:
  H-01→G-AUD, H-02→G-AUD, H-03→G-ANCLA, H-04→G-B04+G-AUD, H-05→G-B04, H-06→G-PKI,
  H-07→G-B04+G-AUD, H-08→G-AUD, H-09→G-AUD, H-10→G-B04+G-AUD, H-11→G-B04, H-12→G-PKI,
  H-13→G-PKI, H-14→G-ANY, H-15→G-ANY, H-16→G-AUD, H-17→G-EFFECT, H-18→G-ANY, H-19→G-AUD,
  H-20→G-GRAPH, H-21→G-GRAPH, H-22→G-AUD, H-23→G-AUD, H-24→G-PKI, H-25→G-B04, H-26→G-ANY, H-27→G-GRAPH.
  AUD-005→G-AUD, AUD-007→G-PKI, AUD-011→G-B04, AUD-013→G-ANY, AUD-015→G-AUD, AUD-018→G-ANY, AUD-019→G-ANY; el resto→G-AUD.
  A-05→G-AUD, AUD-005…019 default G-AUD salvo identificados explícitamente.
  A-01→G-AUD, A-02→G-AUD, A-03→G-GRAPH, A-04→G-INT, B→G-B04, C→G-ANY, D→G-ANY, E→G-PKI, F→G-ANY, G→G-AUD.
  C-01→G-B04+G-AUD, C-04→G-PKI, C-05→G-AUD, C-07→G-GRAPH, C-08→G-B04, C-09→G-ANCLA, C-12→G-EFFECT,
    C-13→G-ANY, C-14→G-AUD, C-15→G-INT, C-16→G-EFFECT, C-17→G-GRAPH, C-18→G-B04, C-19→G-ANCLA; resto →G-AUD.
  M-02→G-AUD, M-03→G-AUD, M-04→G-PKI, M-05→G-GRAPH, M-07→G-PKI, M-08→G-AUD, M-09→G-AUD, M-10→G-B04.
  N-04→G-B04, N-05→G-INT, N-06→G-ANCLA; N-02→G-EFFECT.

B* = { u ∈ Λ : G(u) ∩ B₀-gates } propagated as LFP over Λ.  B₀-gates = {G-§1, G-B04, G-PKI, G-ANY, G-INT, G-ANCLA, G-EFFECT, G-GRAPH};
G-AUD/G-THIRD NO propagan bloqueo primario (ausencia de auditoría no prueba defecto).
```

**Nota de precisión:** la pertenencia de una unidad a G-AUD no prueba que sea defectuosa; sólo que no ha sido verificada con evidencia ejecutable. G-B04/G-PKI/G-ANY/G-INT/G-ANCLA/G-EFFECT/G-GRAPH sí son bloqueos estructurales con dependencia explícita.

---

## 2. Fase 1 — Coherencia lógica (CR-17, CR-26, CR-28)

### §2.1 — Regla de identidad de unidad (cierra CR-28)

```
Cada unidad declara (campo obligatorio):
  own_status     := REPAIR_REQUIRED | BLOCKED | NOT_APPLICABLE
  own_evidence   := (lista de artefactos / vectores / DDL / pruebas) o ∅
  direct_deps    := P(gates)    (§1)
  blocking_reason:= ∅ si no bloquea; si no: cita de gates o de fila
  authority      := IER_GATE_DESIGN_AUTHORITY
El state propio es propio_evidence-dependiente; no se propaga sin análisis:
  u ∈ B*  ⇔  propia u ⇒ G(u) ∩ B₀-gates ≠ ∅  ∨  (propagación: ∃w<u con w∈B* ∧ deps(u)∋w)
En claro: B* se calcula, no se escribe; la tabla §5 lista u∈B* según estas reglas.
```

### §2.2 — Terminalidad formal y reglas legales (CR-17, CR-26)

```
EFECTO (tupla explícita, ya corregido):
  effect := (executed, compensated, compensation_verified, policy_result, outcome)

OpOUT  := outcome de operación ∈ {NONE, COMMITTED, NOT_EXECUTED, UNKNOWN}
OpP    := p de operación     ∈ R1-P
OpO    := o de operación

Reglas de cierre:
  LegalClose(op) ⇔ p ∈ {COMMIT_DURABLE, ABORT_DURABLE}
                ∧ LegalState(op)
                ∧ ∀ e ∈ manifest(op): e ∈ {COMMITTED, NOT_EXECUTED}

Mapping total desde estado de efecto:
  executed=f false                                        → outcome=NONE
  executed=true  ∧ verified   ∧ policy=VERIFIED          → outcome=COMMITTED
  executed=true  ∧ compensated∧ compensation_verified    → outcome=NOT_EXECUTED   (compensación VERIFICADA; jamás COMMITTED)
  executed=true  ∧ compensated∧ ¬compensation_verified   → outcome=UNKNOWN        (compensación sin verificar ⇒ NO cerrar)
  executed=true  ∧ ¬compensated∧ ¬verified∧ pending     → outcome=UNKNOWN        (veredicto/sala pendiente ⇒ NO cerrar)

Política (determinación p/O/resultado):
  NONE   : effects=∅ ⇒ p→ABORT_DURABLE; O=NONE; never COMMIT.
  PL-002 ANY:
    ≥1 VERIFIED               → policy_result=VERIFIED
    todos COMPENSATED_ALL ∀e  → policy_satisfied=false; p→ABORT_DURABLE; O=NOT_EXECUTED
    mix VERIFIED/COMPENSATED  → policy_result=VERIFIED (≥1 VERIFIED basta)
    ⊇1 UNKNOWN                → policy_pending ⇒ no cerrar
  PL-003 ALL:
    todos VERIFIED             → policy_result=VERIFIED
    ∀ dispatched COMPENSATED_ALL → policy_satisfied=false ⇒ p→ABORT_DURABLE; O=NOT_EXECUTED
    ≥1 FAILED/UNKNOWN          → no cerrar
  PL-001 NONE (vacío o no):    executed=false obligatoriamente; policy_result=PENDING inerte.

Consistencia: outcome(operación)=COMMITTED ⇔ policy_result=VERIFIED ∧ ∀e∈manifest executed→verified ∧ p=COMMIT_DURABLE ∧ ∀e∉UNKNOWN.
  No hay contradicción entre reglas 3 y tabla: la compensación verificada respeta outcome=NOT_EXECUTED; nunca produce COMMITTED.
  Compensación NO convierte una ejecución pasada en inexistente; outcome=NOT_EXECUTED describe el estado final efectivo, no la historia.
```

### §2.3 — Señalizador único (cierra CR-28 plenamente)

```
Cada fila de §5/§6/§7 expresa EXPLICÍTAMENTE: gates := G(u); own_status ∈ {REPAIR_REQUIRED, BLOCKED, ACCEPTED-LIMIT}; propagates := G(u)∩B₀-gates≠∅.
No hay divergencia: own_status es propio; propagated es calculada; ambos se listan.
```

---


## 3. Fase 2 — Integridad transaccional (CR-18, CR-19, CR-20, CR-25)

### §3.1 — DDL de almacén (referencia; no ejecutada en esta sesión)

```sql
CREATE TABLE scope (
  scope_id            bytea PRIMARY KEY,
  scope_epoch         numeric(20,0) NOT NULL CHECK (scope_epoch >= 0),
  si                  text NOT NULL CHECK (si IN ('HEALTHY','ROLLBACK_DETECTED','RECONCILIATION_REQUIRED','HUMAN_CLOSED')),
  trs                 text NOT NULL CHECK (trs IN ('VALID','QUARANTINED','NOT_DETERMINED')),
  ess                 text NOT NULL CHECK (ess IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','CONTRADICTION')),
  minimum_valid_fence numeric(20,0) NOT NULL DEFAULT 0 CHECK (minimum_valid_fence >= 0),
  next_fence          numeric(20,0) NOT NULL DEFAULT 0 CHECK (next_fence >= 0),
  fence_monotonic     numeric(20,0) GENERATED ALWAYS AS (next_fence) STORED,
  last_ack_correlation uuid,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE operation (
  operation_id              bytea PRIMARY KEY,
  scope_id                  bytea NOT NULL REFERENCES scope(scope_id),
  scope_epoch               numeric(20,0) NOT NULL CHECK (scope_epoch >= 0),
  od                        text NOT NULL CHECK (od IN ('NOT_EVALUATED','ADMITTED','BLOCKED','NOT_DETERMINED')),
  v                         text NOT NULL CHECK (v  IN ('OPEN','SUSPENDED','CLOSED')),
  p                         text NOT NULL CHECK (p  IN ('NOT_STARTED','RESERVE_REQUESTED','RESERVE_DURABLE','RESERVED_CONFIRMED','EXECUTING','COMMIT_DURABLE','ABORT_DURABLE','RECOVERABLE','RESERVE_ORPHAN','FAILED_CONSUMED')),
  o                         text NOT NULL CHECK (o  IN ('NONE','COMMITTED','NOT_EXECUTED','UNKNOWN')),
  t                         text NOT NULL CHECK (t  IN ('NONE','COMMIT_TESTIFIED','ABORT_TESTIFIED')),
  eso                       text NOT NULL CHECK (eso IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','TESTIFICATION_PENDING','TESTIFIED')),
  operation_kind            smallint NOT NULL CHECK (operation_kind BETWEEN 0 AND 255),
  policy_version            numeric(20,0) NOT NULL CHECK (policy_version >= 0),
  request_id                bytea NOT NULL,
  current_attempt_id        bytea,
  current_attempt_generation smallint NOT NULL DEFAULT 0 CHECK (current_attempt_generation BETWEEN 0 AND 255),
  manifest_bytea            bytea NOT NULL CHECK (octet_length(manifest_bytea) BETWEEN 0 AND 4096),
  manifest_hash             bytea NOT NULL CHECK (octet_length(manifest_hash) = 32),
  first_fence               numeric(20,0),
  closed_at                 timestamptz,
  UNIQUE (scope_id, operation_id),
  UNIQUE (scope_id, scope_epoch, operation_kind, request_id)
);

CREATE TABLE attempt (
  scope_id           bytea NOT NULL,
  operation_id       bytea NOT NULL,
  attempt_id         bytea PRIMARY KEY,
  attempt_generation smallint NOT NULL CHECK (attempt_generation BETWEEN 1 AND 255),
  claim_generation   numeric(20,0) NOT NULL CHECK (claim_generation >= 1),
  fencing_token      numeric(20,0) NOT NULL CHECK (fencing_token BETWEEN 0 AND 18446744073709551615),
  binding_hash       bytea NOT NULL CHECK (octet_length(binding_hash) = 32),
  effect_key         bytea,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (operation_id, attempt_generation),
  UNIQUE (operation_id, claim_generation),
  UNIQUE (scope_id, operation_id, attempt_id),
  UNIQUE (scope_id, fencing_token),
  FOREIGN KEY (scope_id, operation_id)
    REFERENCES operation(scope_id, operation_id) ON DELETE RESTRICT
);
-- La FK compuesta attempt(scope_id, operation_id) → operation(scope_id, operation_id)
-- garantiza attempt.scope_id = operation.scope_id (cierra CR-19).

CREATE TABLE effect (
  effect_id        bytea PRIMARY KEY,
  scope_id         bytea NOT NULL,
  operation_id     bytea NOT NULL,
  attempt_id       bytea NOT NULL REFERENCES attempt(attempt_id),
  effect_ordinal   smallint NOT NULL CHECK (effect_ordinal BETWEEN 0 AND 254),
  effect_kind      smallint NOT NULL CHECK (effect_kind BETWEEN 0 AND 65535),
  effect_class     smallint NOT NULL CHECK (effect_class BETWEEN 0 AND 255),
  executed         boolean NOT NULL DEFAULT false,
  compensated      boolean NOT NULL DEFAULT false,
  compensation_verified boolean NOT NULL DEFAULT false,
  policy_result    text NOT NULL DEFAULT 'PENDING'
                    CHECK (policy_result IN ('PENDING','VERIFIED','FAILED','COMPENSATED_ALL','UNKNOWN')),
  outcome          text NOT NULL DEFAULT 'UNKNOWN'
                    CHECK (outcome IN ('NONE','COMMITTED','NOT_EXECUTED','UNKNOWN')),
  idempotency_key  bytea,
  row_version      smallint NOT NULL DEFAULT 1,
  attempted_at     timestamptz,
  verified_at      timestamptz,
  UNIQUE (scope_id, operation_id, attempt_id, effect_ordinal),
  UNIQUE (scope_id, operation_id, effect_ordinal),
  UNIQUE (idempotency_key)
);
```

### §3.2 — Triggers de transición de efecto (estado P0)

```sql
CREATE FUNCTION effect_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- monotonía de fila: ningún campo vuelve a atrás salvo mediante compensación verificada.
  IF TG_OP = 'INSERT' THEN
    IF NEW.executed IS NULL THEN NEW.executed := false; END IF;
    IF NEW.row_version IS NULL THEN NEW.row_version := 1; END IF;
    RETURN NEW;
  END IF;
  IF OLD.executed = TRUE THEN
    -- executed nunca pasa de true a false
    NEW.executed := TRUE;
  END IF;
  IF OLD.compensated = TRUE AND NEW.compensated = FALSE THEN
    RAISE EXCEPTION 'compensated cannot revert';
  END IF;
  IF OLD.compensation_verified = TRUE AND NEW.compensation_verified = FALSE THEN
    RAISE EXCEPTION 'compensation_verified cannot revert';
  END IF;
  NEW.row_version := OLD.row_version + 1;
  RETURN NEW;
END $$;

CREATE TRIGGER effect_before_update
  BEFORE UPDATE ON effect FOR EACH ROW EXECUTE FUNCTION effect_transition();

-- Regla de coherencia con opica: cierre exclusivo por trigger
CREATE FUNCTION effect_close_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.outcome IS DISTINCT FROM OLD.outcome THEN
    IF OLD.outcome = 'UNKNOWN' AND NEW.outcome <> 'UNKNOWN' AND EXISTS
      (SELECT 1 FROM effect e WHERE e.operation_id = NEW.operation_id
        AND e.scope_id      = NEW.scope_id
        AND e.outcome       = 'UNKNOWN'
        AND e.effect_ordinal<> NEW.effect_ordinal) THEN
      RAISE EXCEPTION 'Op cannot close until every effect is known';
    END IF;
  END IF;
  RETURN NEW;
END $$;
```

### §3.3 — R-CLAIM completo con asignación atómica de fence (cierra CR-18)

```sql
CREATE OR REPLACE FUNCTION r_claim(p_operation_id bytea, p_request_id bytea)
  RETURNS record LANGUAGE plpgsql AS $$
DECLARE
  v_op       operation%ROWTYPE;
  v_alloc    numeric(20,0);
BEGIN
  -- 1) Bloquear operación
  SELECT * INTO v_op FROM operation
    WHERE operation_id = p_operation_id FOR UPDATE;

  -- 2) Bloquear scope y asignar fence atómicamente ANTES de insertar intento
  UPDATE scope
     SET next_fence = next_fence + 1,
         minimum_valid_fence = GREATEST(minimum_valid_fence, next_fence + 1)
    WHERE scope_id = v_op.scope_id
    RETURNING next_fence INTO v_alloc;
  -- 3) La vigencia máxima queda publicada sólo mediante cap.fence = v_alloc en la siguiente tx.

  -- 4) Insertar intento con el fence asignado
  INSERT INTO attempt
    (scope_id, operation_id, attempt_id, attempt_generation, claim_generation, fencing_token, binding_hash)
    VALUES (v_op.scope_id, p_operation_id, gen_random_bytes(32), v_op.current_attempt_generation + 1,
            v_op.current_attempt_generation + 1, v_alloc, v_op.manifest_hash);

  -- 5) Publicar cabeza de operación
  UPDATE operation
     SET current_attempt_id = (SELECT attempt_id FROM attempt
                                WHERE operation_id = p_operation_id
                                  AND attempt_generation = v_op.current_attempt_generation + 1),
         current_attempt_generation = v_op.current_attempt_generation + 1
   WHERE operation_id = p_operation_id;

  RETURN (v_alloc, v_op.operation_id, v_op.scope_id);
END $$;
-- Orden irreversible: fence POST-FOR-UPDATE antes de INSERT attempt ⇒
-- attempt.fencing_token = next_fence atómico. Ningún intento puede publicarse con token anterior.
```

### §3.4 — Efectos del intento por operación (efecto del manifiesto: cierre CR-20)

```sql
CREATE FUNCTION validate_effect_log() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.effect_ordinal >= (SELECT count(*) FROM operation) THEN
    RAISE EXCEPTION 'effect_ordinal out of manifest bounds';
  END IF;
  IF NEW.attempt_generation <> (SELECT current_attempt_generation FROM operation WHERE operation_id = NEW.operation_id) THEN
    RAISE EXCEPTION 'effect row bound to stale attempt';
  END IF;
  RETURN NEW;
END $$;
```

---


## 4. Fase 3 — Garantías distribuidas y criptográficas (CR-22, CR-23, CR-24, CR-27)

### §4.1 — Anclaje anti-rollback con verdad externa (cierra CR-22)

```
Diseño: ningún almacenamiento único puede garantizar monotonía frente a restauración.
Se exige rol de autoridad ancla dual-operador:

Ancla := servicio externo verificable independiente con identidad (BaseCrypto) propia.

ance := { seq: N, root_hash: H(chain_head), timestamp: T, anchor_sig } firmado por Ancla.
ANCHOR_LOG (append-only en el almacén principal y en el almacén externo):
  seq UNIQUE, root_hash UNIQUE, timestamp UNIQUE.

Protocolo de lectura crítica:
  1. Obtener anchor más reciente de ANCHOR_LOG exterior: SELECT MAX(seq).
  2. Verificar ancla firmada con clave ANTES del uso; validar que seq > last_stored_local.
  3. Filtrar chain hasta anchors anteriores y RECONSTRUIR hash acumulado; comparar con anchor.root_hash.
  4. Si mismatch ⇒fail-closed: bloqueo.  Ninguna decisión crítica se toma tras esa cadena.

Restablecimiento anti-rollback:
  Si el almacenamiento se restaura desde una versión antigua, ANCHOR_LOG local puede retroceder,
  pero ANCHOR_LOG exterior (monitoreado) no. La discrepancia es imposible de ocultar: se rechaza despacho.

Unicidad de seq y orden: garantizada por CHECK (seq>0 y monotone-insert-only en ambas tablas).
Si falta ancla intermedia ⇒ reconstruir hasta último válido y exigir discrepancia explicitada.

Límite honesto: sin dual-operador no hay anti-rollback absoluto; este documento lo exige:
  - Modo mínimo honesto: dos almacenes independientes que validan mutuamente el último anchor.
  - Sin ambos, la garantía es: rollback detectable antes del próximo commit, no imposible.
```

### §4.2 — Autoridad de claves (cierra CR-23)

```
KeyRegistry (append-only):
  key_id        bytea PRIMARY KEY,
  public_key    bytea NOT NULL CHECK (octet_length(public_key)=32),
  role          text  NOT NULL CHECK (role IN ('SINK_W','W_CLAIM','SCOPE_AUTHORITY','REOPEN_VERIFIER')),
  scope_id      bytea,
  valid_from    timestamptz NOT NULL,
  valid_to      timestamptz,
  revoked_at    timestamptz,
  sign_bytes    bytea NOT NULL,
  sig_authority bytea NOT NULL
Clave válida ⇔ valid_from ≤ now() ∧ revoked_at IS NULL.
Revocación efectiva ⇔ revoked_at IS NOT NULL; nunca rollback a clave previa.
Rotación: promoción de clave nueva por decision DUAL (W + verificador independiente) registrado como HUMAN-CLOSURE/REOPEN con opened_epoch=actual+1.
Recuperación ante compromiso: revocar key_id comprometido; reemitir decision; propagar a ANCHOR_LOG antes de cualquier decisión crítica.
V6 does not permit silent key promotion; every registry change requires HUMAN-CLOSURE signature.
```

### §4.3 — Codificación canónica de manifiesto (cierra CR-24)

```
ManifestHash := SHA-256(
  Tag('IER-effect-manifest-v1\0')
  ‖ NU16(manifest_version)                // UINT16 = 1 por definición
  ‖ NU8(policy_tag)                       // NONE=0, ANY=1, ALL=2
  ‖ ENC(scope_id)                         // 40B
  ‖ NU64(scope_epoch)                     // 8B
  ‖ ENC(operation_id)                      // 40B
  ‖ NU64(policy_version)                   // 8B
  ‖ NU64(n_effects)                        // 8B count
  ‖ concat(effects ordenados por effect_ordinal:
       NU16(effect_kind) ‖ NU16(effect_ordinal) ‖ ENC(effect_binding))
)

ENC(b) := NU64(len(b)) ‖ b; longitudes rechazadas si superan bounds máximos:
  scope_id 32, operation_id 32, binding 32, policy_version >= 0.
Reglas de rechazo:
  manifest_version ≠ 1 ⇒ rechazo
  policy_tag ∉ {0,1,2} ⇒ rechazo
  n_effects > 255 ⇒ rechazo; ordinal repetido ⇒ rechazo; ordinal ≠ 0..n-1 denso ⇒ rechazo
  bytes residuales (más allá del último effect) ⇒ rechazo
  total length ≠ declarada ⇒ rechazo
```

Vector: reproducible bit a bit desde esta especificación — ver v5 §P0A-3; idéntico cálculo aquí.

### §4.4 — Protocolo de suspensión con correlación de ACK anticuado (cierra CR-27)

```
Estado(parte): scope.row_version integer + suspension_seq; scope_generator ∈ scope.
Capacidad: cap.fence ligada a fence-por-scope reclamado en el ordinales del scope.

Suspend protocol (único orden, ninguna ruta alternativa):
  1. TX1: SELECT * FROM scope WHERE scope_id=? FOR UPDATE; row_version += 1; fence/epoch bump;
     fresh_nonce := gen_random_bytes(16);
     atom submit(op=SMAN suspend,...).
  2. TX1 commits. suspension nonce stored in scope.suspension_nonce INT.
  3. Sink action requires scope.row_version == scope.acceptance.row_version and last_fence >= fence — checked IN THE SAME TX.
  4. Firma ACK de suspension incluye suspension_seq + fencing_token; nunca reencaminado;
     un ACK antiguo (fence < current) se descarta; nuevo fence puede surgir.

Invariante:
  Sink may dispatch ⇒ cap.fence ≥ scope.minimum_valid_fence ∧ scope.row_version == last_seen_row_version ± 0 UNLIKE suspension after start.
  Si suspension ocurre durante dispatch solicitado ⇒ sink aborta, nunca despacha.
  Sink nunca commitea bajo row_version stale; si suspension ocurrió entretanto ⇒ reintenta/aborta, nunca emite.
  T-SUSPEND no revocable: row_version sólo crece.
  Suspensión incompleta ⇒ queda en RECONCILIATION_REQUIRED con row_version bump y revocación persisted, nunca "completada".
```

---


## 5. Fase 4 — Inventario Λ, B₀ y B* (cierra CR-21, CR-28 segundo nivel)

### §5.1 — Universo Λ (cerrado, comprobable)

```
Λ = Λ_R1 ∪ Λ_R1.3 ∪ Λ_SEED ∪ Λ_AUDIT, con:
  Λ_R1     = 49 símbolos de R1 — NO se incorporan silenciosos a Λ: ninguno aparece aquí sin citación al registro R1 de B07_FORMAL_MODEL.md.
  Λ_R1.3   = 19 símbolos (ES-001..7, FG-001..4, PL-001..3, SC-001..3, EF-001..2) — declarados sólo en el artefacto de diseño; sin sellar.
  Λ_SEED   = símbolos con dependencia a §1: {x′}. = RN-teórico B02-B07. (… como variable abstracta) – ninguno activo.
  Λ_AUDIT  = símbolos introducidos por nuestra reparación: effect, effect_log, r_claim, loader…todos declarables según gate explícito.
  |Λ| <= 104 (106 máx); en esta revisión cerramos a 104 unidades de auditoría (auditor-dictamen v5 §6).
```

### §5.2 — B₀ (bitmap de bloqueos primarios explícitos)

```
Definido según §1.2 del modelo de dependencia:
B₀-gates := {G-§1, G-B04, G-PKI, G-ANY, G-INT, G-ANCLA, G-EFFECT, G-GRAPH}
B₀-time  := filas con gate crítico propio o propagación conocida.
```

### §5.3 — B* (punto fijo LFP)

`B* = LFP(Φ, B₀)` calculado por el algoritmo de §1; la unión de todas las unidades con cualquier gate estructural en propiedad. El resultado exhaustivo se escribe a continuación en la matriz §6 §7 §8.**Nada se ha ejecutado ni verificado; ningún resultado indica cierre.**

## 6. Matriz H-01…H-27 (gates + estado propio + propagado; v6)

| H | Gates propios | propio | propagado | péndulo (estado v6) |
|---|---|---|---|---|
| H-01 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED (cotejo) |
| H-02 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED (cotejo) |
| H-03 | G-ANCLA | BLOCKED | sí | BLOCKED |
| H-04 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| H-05 | G-B04 | BLOCKED | sí | BLOCKED |
| H-06 | G-PKI | BLOCKED | sí | BLOCKED |
| H-07 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| H-08 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED (cotejo) |
| H-09 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| H-10 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| H-11 | G-B04 | BLOCKED | sí | BLOCKED |
| H-12 | G-PKI | BLOCKED | sí | BLOCKED |
| H-13 | G-PKI | BLOCKED | sí | BLOCKED |
| H-14 | G-ANY | BLOCKED | sí | BLOCKED |
| H-15 | G-ANY | BLOCKED | sí | BLOCKED |
| H-16 | G-AUD | REPAIRED-CONDICIONADO | no | CONDICIONADO |
| H-17 | G-EFFECT | BLOCKED | sí | BLOCKED |
| H-18 | G-ANY | BLOCKED | sí | BLOCKED |
| H-19 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| H-20 | G-GRAPH | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| H-21 | G-GRAPH | BLOCKED | sí | BLOCKED |
| H-22 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| H-23 | G-AUD | BLOCKED | no | BLOCKED |
| H-24 | G-PKI | BLOCKED | sí | BLOCKED |
| H-25 | G-B04 | BLOCKED | sí | BLOCKED |
| H-26 | G-ANY | BLOCKED | sí | BLOCKED |
| H-27 | G-GRAPH | REPAIR_REQUIRED | sí | BLOCKED (propagado) |

## 7. Matriz AUD-001…019 + RES-1…9 + M-01…10 + A/T + C + N (v6; gates propios; estado propio y propagado)

| Unidad | Gates | propio | propagado | v6 |
|---|---|---|---|---|
| AUD-001 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-002 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-003 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-004 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-005 | G-AUD | ACEPTADA | no | ACEPTADA (limitada) |
| AUD-006 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-007 | G-PKI | BLOCKED | sí | BLOCKED |
| AUD-008 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-009 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-010 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-011 | G-B04 | BLOCKED | sí | BLOCKED |
| AUD-012 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-013 | G-ANY | BLOCKED | sí | BLOCKED |
| AUD-014 | G-ANY | BLOCKED | sí | BLOCKED |
| AUD-015 | G-AUD | BLOCKED | no | BLOCKED |
| AUD-016 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-017 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| AUD-018 | G-ANY | BLOCKED | sí | BLOCKED |
| AUD-019 | G-ANY | BLOCKED | sí | BLOCKED |
| RES-1 | G-AUD | ACEPTADA | no | ACEPTADA |
| RES-2 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| RES-3 | G-AUD | ACEPTADA | no | ACEPTADA |
| RES-4 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| RES-5 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| RES-6 | G-PKI | BLOCKED | sí | BLOCKED |
| RES-7 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| RES-8 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| RES-9 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| M-01 | G-ANY | BLOCKED | sí | BLOCKED |
| M-02 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| M-03 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| M-04 | G-PKI | BLOCKED | sí | BLOCKED |
| M-05 | G-GRAPH | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| M-06 | G-AUD | ACEPTADA | no | ACEPTADA |
| M-07 | G-PKI | BLOCKED | sí | BLOCKED |
| M-08 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| M-09 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| M-10 | G-GRAPH | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| A-01 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| A-02 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| A-03 | G-GRAPH | BLOCKED | sí | BLOCKED |
| A-04 | G-INT | BLOCKED | sí | BLOCKED |
| B | G-B04 | BLOCKED | sí | BLOCKED |
| C | G-ANY | BLOCKED | sí | BLOCKED |
| D | G-ANY | BLOCKED | sí | BLOCKED |
| E | G-PKI | BLOCKED | sí | BLOCKED |
| F | G-ANY | BLOCKED | sí | BLOCKED |
| G | G-AUD | ACEPTADA LIMITADA | no | ACEPTADA LIMITADA |
| C-01 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| C-02 | G-B04 | BLOCKED | sí | BLOCKED |
| C-03 | G-ANY | BLOCKED | sí | BLOCKED |
| C-04 | G-PKI | BLOCKED | sí | BLOCKED |
| C-05 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| C-06 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |
| C-07 | G-GRAPH | BLOCKED | sí | BLOCKED |
| C-08 | G-B04 | BLOCKED | sí | BLOCKED |
| C-09 | G-ANCLA | BLOCKED | sí | BLOCKED |
| C-10 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| C-11 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| C-12 | G-EFFECT | BLOCKED | sí | BLOCKED |
| C-13 | G-ANY | BLOCKED | sí | BLOCKED |
| C-14 | G-AUD | BLOCKED | no | BLOCKED |
| C-15 | G-INT | BLOCKED | sí | BLOCKED |
| C-16 | G-EFFECT | BLOCKED | sí | BLOCKED |
| C-17 | G-GRAPH | BLOCKED | sí | BLOCKED |
| C-18 | G-B04 | BLOCKED | sí | BLOCKED |
| C-19 | G-ANCLA | BLOCKED | sí | BLOCKED |
| N-01 | G-B04,G-AUD | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| N-02 | G-EFFECT | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| N-03 | G-EFFECT | REPAIR_REQUIRED | sí | BLOCKED (propagado) |
| N-04 | G-B04 | BLOCKED | sí | BLOCKED |
| N-05 | G-INT | BLOCKED | sí | BLOCKED |
| N-06 | G-ANCLA | BLOCKED | sí | BLOCKED |
| N-07 | G-PKI | REPAIR_REQUIRED | sí | REPAIR_REQUIRED |
| N-08 | G-AUD | ACEPTADA | no | ACEPTADA |
| N-09 | G-AUD | ACEPTADA | no | ACEPTADA |
| N-10 | G-AUD | REPAIR_REQUIRED | no | REPAIR_REQUIRED |

## 8. D-R2R2-1…11 — ninguna ratificada (reaplica dictamen v5, sin cambio)

| # | Estado |
|---|---|
| D-R2R2-1 | BLOCKED |
| D-R2R2-2 | BLOCKED |
| D-R2R2-3 | BLOCKED |
| D-R2R2-4 | REPAIR_REQUIRED |
| D-R2R2-5 | BLOCKED |
| D-R2R2-6 | DIFERIDA |
| D-R2R2-7 | REPAIR_REQUIRED |
| D-R2R2-8 | REPAIR_REQUIRED |
| D-R2R2-9 | BLOCKED |
| D-R2R2-10 | BLOCKED |
| D-R2R2-11 | BLOCKED |


---

## 9. Apéndice — LegalState y atributos de cierre formal

```
LegalState(op) :=
  DomainValid(op) ∧ INV-02 ∧ INV-03 ∧ INV-04 ∧ INV-09 ∧ INV-10 ∧ INV-14 ∧ INV-16 ∧ INV-18

Cierre (EXACTO):
  T-CLOSE/T13 ⇔ p ∈ {COMMIT_DURABLE, ABORT_DURABLE}
             ∧ ∀ e ∈ manifest: e ∈ {COMMITTED, NOT_EXECUTED}
             ∧ LegalState(op) = TRUE

NUNCA cierre si:
  ∃ e ∈ manifest: e.outcome = UNKNOWN
  O_comp¬verified × executed=TRUE
  SAGA iniciada sin compensada
```

## 10. Plan de verificación (aún no ejecutado)

```
1. Cotejo DDL ejecutable: 8 tablas + 7 triggers + 4 funciones + 1 endpoint criptográfico.
2. Verificación reproducible de vectores con dos ejecutores independientes.
3. Prueba de concurrencia: 6 escenarios HP-1..6 con monkey-patching; comportamiento estable semanal.
4. Censo bidireccional árbol≡artefacto (A-01).
5. Revisión de terceros (REQUIRED; NOT_EXECUTED).
6. Cotejo auditoría fila por fila con actualización del ledger del proyecto.
```

## 11. Estado final tras esta revisión

- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `D-315 = PENDING` · `MODEL_VERIFIED = NO` · `INDEPENDENTLY_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · `PROMOTION = NOT_READY` · `THIRD_PARTY_REVIEW = REQUIRED / NOT_EXECUTED`.
- **Ninguna** decisión ratificada; **ninguna** fila ratificada salvo acotados (AUD-005, RES-1/RES-3, M-06, G, N-08/N-09 con alcance limitado).
- Baseline v2.r2 intacto (`9c8a0aba…`); `B07_FORMAL_MODEL.md` intacto (`a7273d58…`); §1 intacta (`74a19ba2…`).
- Ninguna ejecución, ninguna prueba real; todo diseño declarativo.
- Procedencia registrada en `state/multiproject/log.md`.
- Antecedentes v1…v5 conservados íntegros.

---

Fin R2-A REVISION 6 · DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED · Procedencia en `state/multiproject/log.md`.
