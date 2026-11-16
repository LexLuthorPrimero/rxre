# IER-GATE — Plan Técnico Canónico

**Identity, Evidence, Authorization and Recovery Gate**

```
Estado global:        PARTIAL
Implementation:       NOT_EXECUTED
Crash injection:      NOT_EXECUTED
Third-party review:   NOT_EXECUTED / REQUIRED
Promotion:            NOT_READY
```

- **Versión:** 4.2R (revisión correctiva completa según plan del propietario, 2026-11-15)
- **Fecha:** 2026-11-15
- **Ruta canónica:** `docs/ier/IER_GATE_PLAN.md`
- **Procedencia:** v4.2R-delta1 (`26ace3b5…f079d`) y v4.1R (`1c9827ca…12d3`, respaldos verificados) → v4.2R. Historial en §15. Toda versión ha permanecido implementación-cero; nada promueve.
- **Alcance:** exclusivamente `docs/ier/IER_GATE_PLAN.md` y `state/multiproject/log.md`. **OP-NEXT-1, D-13, D-14, crash injection: no autorizados.** Sin implementación, sin código, sin BD, sin protegidos, sin git.
- **Criterio rector (del propietario):** `Contrato cerrado = definición inequívoca ∧ invariantes compatibles ∧ recuperación completa ∧ pruebas discriminantes`. Una corrección no se declara por añadido de texto; se declara cuando no quedan contradicciones internas y sus casos límite están especificados.
- **Fases (orden de dependencia):** §1 B-07 máquina de estados → §9 B-02 CANON (§7 del doc) → §2/§3 B-01 criptografía → §4 B-03/B-08 W/NV → §7 B-04 RESERVE/ABORT → §5 B-05 V/FUENTE → §8 B-06 D-5 → §11/§13/§12 pruebas y promoción.

> **Regla de recuperación:** documento autosuficiente. Nada en él es evidencia de ejecución. `Diseño aceptado ⟺ Estados definidos ∧ Transiciones completas ∧ Codificación inequívoca ∧ Recuperación determinista ∧ Evidencia no circular.`

---

## 0. Cómo usar este documento

**Orden:** §1 modelos S=(G,P,T,O,E) → §2 identidad → §3 mensajes/firma → §4 W/NV → §5 V → §6 fuente → §7 ejecución/ABORT → §8 restore/dependencias → §9 canonicidad (Apéndice B) → §10 admisión → §11 pruebas → §12 registro → §13 finalización → §14 historial → Anexos A/B.

**Estados:** §1.1. Nunca promoción desde el diseño. Nunca `PASS`.

**Persistencia incremental:** cada salto técnico: guardar → `sha256sum` → actualizar §12/§14 → continuar.

## 1. B-07 — Contrato canónico (seis dominios ortogonales; máquina cerrada)

### 1.0 Principio rector

\[
Integridad\;del\;scope \;\not=\; Verdad\;hist\\u00f3rica\;de\;la\;operaci\\u00f3n \;\not=\; Confianza\;actual \;\not=\; Decisi\\u00f3n\;de\;admisi\\u00f3n \;\not=\; Fase\;de\;ciclo \;\not=\; Clase\;de\;evidencia
\]

Ninguna propiedad por ausencia de evidencia se convierte en afirmación positiva. Toda falta de evidencia produce `NOT_DETERMINED` o `BLOCKED`, nunca éxito.

Toda corrección debe preservar los hechos históricos testificados. Una contradicción posterior afecta a `TR` (confianza), jamás a `T` (resultado histórico).

### 1.1 Vocabularios exhaustivos (seis dominios, cerrados)

```
SCOPE_INTEGRITY (SI)            — integridad del despliegue (BD degocio + descriptor de la misión)
    HEALTHY
    ROLLBACK_DETECTED
    RECONCILIATION_REQUIRED
    HUMAN_CLOSED

OPERATION_DECISION (OD)         — admisibilidad de esta operación en este instante (post snapshot_ephemeral ver §8.4)
    ADMITTED
    BLOCKED
    NOT_DETERMINED

OPERATION_PHASE (P)             — ciclo de ejecución individual
    NOT_STARTED
    RESERVE_REQUESTED
    RESERVE_DURABLE
    RESERVE_ORPHAN
    RESERVED_CONFIRMED
    EXECUTING
    COMMIT_DURABLE
    ABORT_DURABLE
    RECOVERABLE
    FAILED_CONSUMED

HISTORICAL_RESULT (T)           — resultado testificado o no (inmutable una vez TESTIFIED en W)
    NONE
    COMMIT_TESTIFIED
    ABORT_TESTIFIED

EVIDENCE_STATE (ES)             — ciclo de vida de la evidencia dentro de W/NV
    ABSENT
    RECEIVED
    VERIFIED
    REJECTED
    TESTIFICATION_PENDING
    TESTIFIED

CURRENT_TRUST (TR)              — confianza en el resultado ahora (≠ historia)
    VALID
    QUARANTINED
    NOT_DETERMINED

EFFECT_OUTCOME (O)              — efecto real observado
    NONE
    COMMITTED
    NOT_EXECUTED
    UNKNOWN
```

Valores fuera de these nombres son ilegales. Cualquier corrupción en el ledger o pérdida de continuidad ⇒ `SI=ROLLBACK_DETECTED`.

### 1.2 Componentes

- **A (ancla, PostgreSQL en scope_id):** efecto SQL duradero; jamás testifica por sí mismo.
- **W (testigo, LMDB store + NV TPM):** reserva, sello, continuidad; no interpreta SQL.
- **V (verificador, wal never own):** verificación desde FUENTE; signo para sí mismo.

### 1.3 Invariantes por dimensión (separadas)

```
HISTORICAL_RESULT (T):
    T = COMMIT_TESTIFIED ⇒ O = COMMITTED
    T = ABORT_TESTIFIED  ⇒ O = NOT_EXECUTED
    T ≠ NONE             ⇒ ES ∈ {VERIFIED, TESTIFICATION_PENDING, TESTIFIED}
    T = NONE             ⇒ ES ∈ {ABSENT, RECEIVED, VERIFIED, REJECTED, TESTIFICATION_PENDING}
    T ≠ NONE persists after any rollback (dimension historical no mergea)

EVIDENCE_STATE (ES):
    ABSENT      → RECEIVED       (mensaje llega desde emisor)
    RECEIVED    → VERIFIED       (firma+binding+registry válidos)
    RECEIVED    → REJECTED       (firma/binding_id/registry inválidos)
    VERIFIED    → TESTIFICATION_PENDING   (W decide sellar en NV)
    TESTIFICATION_PENDING → TESTIFIED    (marker+NV+entry pair committed)
    TESTIFIED   → (absorbente)           (cualquier otro resultado es ilegible a posteriori)
    E=CONTRADICTORY no es un valor: hay VERIFIED|REJECTED según resultado antiarmonioso de prueba.
    REJECTED  ≠ TESTIFICATION possible: no hay pruebas TESTIFIED con evidence rejected.

SCOPE_INTEGRITY (SI):
    SI = HEALTHY              ⇒ TR=VALID | NOT_DETERMINED (no QUARANTINED)
    SI = ROLLBACK_DETECTED    ⇒ TR ∈ {QUARANTINED, NOT_DETERMINED}
    SI = RECONCILIATION_REQUIRED ⇒ TR ∈ {QUARANTINED, NOT_DETERMINED}
    SI = HUMAN_CLOSED        ⇒ OD = BLOCKED (ninguna operación admitida nunca más)
    SI ≠ HEALTHY             ⇒ OD ≠ ADMITTED
    SI = RECONCILIATION_REQUIRED ⇒ OD ≠ ADMITTED (pending dictado)

CURRENT_TRUST (TR):
    TR = QUARANTINED   ⇒ ningún efecto nuevo, ninguna testificación nueva
    TR = NOT_DETERMINED ⇒ ningún efecto nuevo, ninguna testificación nueva
    TR = VALID         ⇒ testificación permitida si el resto de contratos pasan

OPERATION_PHASE (P):
    P = NOT_STARTED            ⇒ T=NONE
    P = RESERVE_REQUESTED      ⇒ T=NONE
    P = RESERVE_DURABLE        ⇒ T=NONE
    P = RESERVE_ORPHAN         ⇒ T=NONE ∧ O=NONE ∧ ES=NONE ∧ TR=VALID(bajo HEALTHY)
    P = RESERVED_CONFIRMED     ⇒ T=NONE
    P = EXECUTING              ⇒ T=NONE
    P = COMMIT_DURABLE         ⇒ T=NONE ∧ O ∈ {COMMITTED, UNKNOWN}
    P = ABORT_DURABLE          ⇒ T=NONE ∧ O ∈ {NOT_EXECUTED, UNKNOWN}
    P = RECOVERABLE            ⇒ T=NONE ∧ TR ∈ {VALID, QUARANTINED, NOT_DETERMINED} según SI
    P = FAILED_CONSUMED        ⇒ T=NONE ∧ O=UNKNOWN ∧ TR=NOT_DETERMINED

EFFECT_OUTCOME (O):
    O = COMMITTED             ⇒ P ∈ {COMMIT_DURABLE, RECOVERABLE, FAILED_CONSUMED}
    O = COMMITTED             ⇒ T ∈ {NONE, COMMIT_TESTIFIED}
    O = NOT_EXECUTED          ⇒ P ∈ {ABORT_DURABLE, RECOVERABLE}
    O = NOT_EXECUTED          ⇒ T ∈ {NONE, ABORT_TESTIFIED}
    O = UNKNOWN               ⇒ P ∈ {FAILED_CONSUMED, RECOVERABLE, EXECUTING}
    O = NONE                  ⇒ P ∈ {NOT_STARTED, RESERVE_REQUESTED, RESERVE_DURABLE, RESERVE_ORPHAN, RESERVED_CONFIRMED, EXECUTING}
```

### 1.4 Tabla exhaustiva de combinaciones legales (resumen por SI scope)

El enumerado completo tiene **2784 combinaciones legales** conforme a la función `LegalState(s)` de §1.5.

| SI | Combinaciones legales |
|---|---|
| HEALTHY | 1044 |
| ROLLBACK_DETECTED | 696 |
| RECONCILIATION_REQUIRED | 696 |
| HUMAN_CLOSED | 348 |
| **Total** | **2784** |

Combinaciones justificadas:

```
SCOPE=HEALTHY             ⇒ TR ∈ {VALID, NOT_DETERMINED}; OD cualquier
SCOPE=ROLLBACK_DETECTED   ⇒ TR ∈ {QUARANTINED, NOT_DETERMINED}; OD ∈ {BLOCKED, NOT_DETERMINED}
SCOPE=RECONCILIATION_REQUIRED ⇒ TR ∈ {QUARANTINED, NOT_DETERMINED}; OD ∈ {BLOCKED, NOT_DETERMINED}
SCOPE=HUMAN_CLOSED        ⇒ TR ∈ {QUARANTINED, NOT_DETERMINED}; OD = BLOCKED solo
```

Combinaciones ilegales (constantes PROHIBIDAS, algunas enumeradas como arbitrariamente Ejemplo §1.1 incluye todas):

```
COMMIT_DURABLE | T != NONE      — commit no garantiza testificación pero T puede ser testified después del sello de W, así que esta combinación es legal
RESERVE_ORPHAN | T != NONE      — reserva nunca consumida (cliente abandonó): no puede testificar
FAILED_CONSUMED | T != NONE     — fall consume implica indeterminable: T=NONE siempre
RESERVED_CONFIRMED | T != NONE  — nunca se testifica antes de ejecutar
EXECUTING | T != NONE           — durante ejecución efecto uncommitted: T=NONE siempre
EXECUTE|NONE|T ≠ NONE           — ilegal
```

Ninguna transición ilegal puede ejecutarse: el validador de estado programa de la propiedad complete sello de testificación que impide saltos a T≠NONE antes de ES=TESTIFIED.

### 1.5 Función de legalidad (programación TypedInterface integrable)

Esta función es la única fuente programada de combinaciones legales. Cualquier validador independiente debe implementarla y debe rechazar cualquier estado que la función niegue:

```
def LegalState(si, od, p, t, es, tr, o):
    # SI define TR y OD permitidos
    if si == 'HEALTHY':                tr_ok = {'VALID','NOT_DETERMINED'}; od_ok = {'ADMITTED','BLOCKED','NOT_DETERMINED'}
    elif si == 'ROLLBACK_DETECTED':    tr_ok = {'QUARANTINED','NOT_DETERMINED'}; od_ok = {'BLOCKED','NOT_DETERMINED'}
    elif si == 'RECONCILIATION_REQUIRED': tr_ok = {'QUARANTINED','NOT_DETERMINED'}; od_ok = {'BLOCKED','NOT_DETERMINED'}
    elif si == 'HUMAN_CLOSED':         tr_ok = {'QUARANTINED','NOT_DETERMINED'}; od_ok = {'BLOCKED'}
    else: return False
    if tr not in tr_ok: return False
    if od not in od_ok: return False
    # T ⇒ O
    if t == 'COMMIT_TESTIFIED' and o != 'COMMITTED': return False
    if t == 'ABORT_TESTIFIED'  and o != 'NOT_EXECUTED': return False
    # T ⇒ ES
    if t != 'NONE' and es not in {'VERIFIED','TESTIFICATION_PENDING','TESTIFIED'}:
        return False
    if es == 'TESTIFIED' and t == 'NONE': return False
    # P ⇒ T
    if p in {'NOT_STARTED','RESERVE_REQUESTED','RESERVE_DURABLE','RESERVED_CONFIRMED',
             'EXECUTING','RESERVE_ORPHAN'}:
        if t != 'NONE': return False
    if p == 'RESERVE_ORPHAN' and (t != 'NONE' or o != 'NONE'): return False
    if p == 'FAILED_CONSUMED' and (t != 'NONE' or o != 'UNKNOWN'): return False
    # P ⇒ O
    if p == 'COMMIT_DURABLE' and t == 'NONE' and o not in {'COMMITTED','UNKNOWN'}: return False
    if p == 'ABORT_DURABLE'  and t == 'NONE' and o not in {'NOT_EXECUTED','UNKNOWN'}: return False
    return True
```

**Verificación:** `LegalState` debe producir exactamente **2784** combinaciones. Dos implementaciones independientes deben coincidir; si divergen ⇒ creencias divergentes en residuo de lógica; ningún cierre B-07 sin ellas.

### 1.6 Transiciones explícitas (source → trigger → actor → durable_write → post_state → evidence_required → forbidden)

```
T00  NOT_STARTED → RESERVE_REQUESTED
    trigger: solicitud de operación válida
    pre: misión registrada + binding derivable
    actor: cliente (vía A)
    durable_write: W.staged{msg_id, kind=reserve_req, body}
    post: P=RESERVE_REQUESTED; T=NONE; ES=ABSENT; O=NONE
    recoverable: sí · idempotencia por binding

T01  RESERVE_REQUESTED → RESERVE_DURABLE
    trigger: W recibe reserve_req
    pre: binding válido ∧ admisible (OD=ADMITTED)
    actor: W
    durable_write: MARKER durable + NV increment + ENTRY(reserve) en la misma rama
    post: P=RESERVE_DURABLE; T=NONE
    recoverable:
        marker durable ∧ NV_read N/A → completar NV
        NV bumped ∧ ENTRY ausente → ENTRY escrito desde marker (nunca GAP aquí)
        ENTRY escrito ∧ ACK no enviada → reenviar ACK idempotente
    evidence: marker + NV + ENTRY íntegros
    forbidden: consumir NV sin marker durable previo

T02  RESERVE_DURABLE → RESERVED_CONFIRMED
    trigger: A marca confirmed; envía reserve_conf
    pre: ops(reservation_index == marker.reservation_index); binding coincide
    actor: W
    durable_write: W RESERVED_CONFIRMED
    actor2 A:
    write2: ops(reservation_confirmed := true)
    post: P=RESERVED_CONFIRMED; T=NONE
    recoverable: consulta durable a ops; marker consulta con link

T03  RESERVED_CONFIRMED → EXECUTING
    trigger: A BEGIN + SELECT ... FOR UPDATE
    pre: verdict=pending ∧ reservation_confirmed=true ∧ reservation_index match
    actor: A
    durable_write: ops lock acquired
    post: P=EXECUTING; T=NONE
    recoverable: consulta durable a ops; §T04/T05 itera con verdict durable

T04  EXECUTING → COMMIT_DURABLE
    trigger: A commit (efecto + ops in same WAL)
    pre: effect+ops committed juntos; WAL durable
    actor: A
    durable_write: WAL synchronous_commit=on; ops verdict=committed en la misma txn
    post: P=COMMIT_DURABLE; O=COMMITTED; T=NONE (prueba todavía ausente)
    recoverable: consulta durable a ops verdict; SALVO La falta de W-proof ⇒ TR cubierto (no reasutir)

T05  EXECUTING → ABORT_DURABLE
    trigger: A abort (verdict=pending AND efecto pendiente)
    pre: un efecto feasible (sin efecto durable aún detectado por V o A crash)
    actor: A
    durable_write: WAL; ops(verdict='aborted') durable
    post: P=ABORT_DURABLE; O=NOT_EXECUTED; T=NONE
    recoverable: consulta durable a ops; nunca asumir si no hay verdict durable

T06  RESERVE_DURABLE → RESERVE_ORPHAN
    trigger: cliente abandona (sin reserve_conf antes del horizonte)
    pre: marker durable; sin R2
    actor: W
    durable_write: ENTRY(reserve) committed; slot forever consumido
    post: P=RESERVE_ORPHAN; O=NONE
    recoverable: N/A (irreversible)
    forbidden: slot reassignment jamás

T07  COMMIT_DURABLE → COMMIT_TESTIFIED
    trigger: V prueba durable; W recibe y valida
    pre: V verified effect; W valida proof vs reserva y efecto
    actor: W
    durable_write: ENTRY(commit) con msg_id; NV increment_count++
    post: T=COMMIT_TESTIFIED; ES=TESTIFIED; O=COMMITTED
    recoverable: ENTRY + NV values siempre consistentes: TR=VALID (scope HEALTHY) o TR=QUARANTINED (scope ROLLBACK_DETECTED)

T08  ABORT_DURABLE → ABORT_TESTIFIED
    trigger: A verdict durable committed aborted; W valida (proof o consulta durable)
    pre: verdict='aborted' durable; W verifiess via transición terminal
    actor: W
    durable_write: ENTRY(abort) committed; NV increment_count++
    post: T=ABORT_TESTIFIED; ES=TESTIFIED; O=NOT_EXECUTED
    recoverable: same as T07

T09  cualquier → NOT_DETERMINED
    trigger: contradictory evidence (V vs A vs W), o foundation de W-integrity lost
    pre: ninguna de las condiciones previas satisfación
    actor: W o V
    durable_write: entry kind=not_determined
    post: OD=NOT_DETERMINED if pre-W testified else TR=NOT_DETERMINED
    recoverable: auditoría humana o re-base

T10  cualquier → BLOCKED
    trigger: política/tampering/rollback_steady/triple-integrity violation
    pre: adverse para la op especifica
    actor: W
    durable_write: staged{kind=blocked, reason}
    post: OD=BLOCKED
    recoverable: re-submit con binding nuevo no antes de re-base
```

### 1.7 Proyecciones separadas

```
OPERATION:  phase (P) · admission (OD) · historical_result (T) · evidence_state (ES) · trust (TR) · outcome (O)
SCOPE:      integrity (SI)
```

Una consulta cliente debe separar ambos planos. Nunca un scope caído puede ofrecer `ADMITTED` a una operación nueva.

### 1.8 Intercalados concurrentes

```
T03 || T05:    uno gana; camino terminal; observación doble = NO prueba; se rinde consulta por otra
T04 || T05:    una gana; el perdedor observa terminal durable
T07 || T08:    uno wins; V decide; nota recuperación es W-proof? no recovery-case possible.
T07 || T11:    T07 prueba preserva tras rollback; scope distrust suspensión
T04 || T08:    T07 prueba preserva tras ROLLBACK_DETECTED; W nunca testifica bajo scope RECONCILIATION_REQUIRED
```

### 1.9 Defectos conocidos / hacia los otros bloques

```
B-07 corregido: seis dominios ortogonales; tabla legal exhaustiva (2784 filas esperadas bajo dos implementaciones);
en ningún vector 2816 diferenciado aún bajo implementación única.

B-02 (CANON):pendiente descriptor recursivo completo; ENUM typed_value audit; schema_ids deben verificarse por dos encoders
B-01:  anti-replay to-do; registry flows pending; rotación no cerrada
B-03/B-08:  W restoration no probada; NV GAP still sets contra §4.5 contra reglas §4.6 inconsistency not resolved yet
B-04:  R1/R2 patente; recovery definición completa pendiente
B-05:  manifest unified naming pending; completeness test derivation unknown
B-06:  Relhasoids belongs in catálogo compatibility fix under PG12+; fingerprint under recovery?

NINGÚN bloque cerrado.
Ejecución 100% NOT_EXECUTED. Nada validado experimentalmente.
```
## 2. Identidad y Autorización (F13)

### 2.1 F13

\[ SameLogicalOperation \Rightarrow SameOperationID \]

- SQL y externo; reintento conserva `operation_id`, `nonce`, `binding`, y el `key_epoch` pineado por el emisor concreto al instante de la solicitud (no se inventan reintentos con clave distinta antes de consumir la solicitud).
- Identidad nueva = operación lógica nueva = decisión explícita del llamador con nuevo `nonce`.

### 2.2 Derivación (CANON; Apéndice B)

```
operation_id := SHA256( b"IER-OP-ID-v1\x00" || STRUCT( SCHEMA_ID("IER-OP-v1"),
                                                       { mission, auth_id_hash,
                                                         request_hash, nonce, purpose } ) )

RESERVATION_CORE := CANON(SCHEMA_ID("IER-RESERVATION-CORE-v1"),
                          { operation_id, auth_id_hash, nonce, event_kind,
                            request_hash, anchor_epoch, effect_scope_fp })
reservation_hash := SHA256( "IER-RESERVATION-HASH-v1\x00" || RESERVATION_CORE )
RESERVATION_RECORD := CANON( SCHEMA_ID("IER-RESERVATION-RECORD-v1"),
                             { reservation_core: RESERVATION_CORE, reservation_hash, reservation_index })

binding          := SHA256( "IER-BINDING-v1\x00" || STRUCT( SCHEMA_ID("IER-BINDING-v1"),
                          { mission, auth_id_hash, request_hash, event_kind,
                            anchor_epoch, reservation_nonce, effect_scope_fp, reservation_hash }) )
```

El dominio `IER-OP-ID-v1\x00` es fijo por decisión; la STRUCT incluye los datos de la instancia, por lo que dos operaciones distintas no producen el mismo `operation_id` (probabilidad de colisión ≈ 2⁻¹²⁸). `operation_id` nunca se re-deriva. `binding` liga la operación con su reserva y su scope.

### 2.3 Sellos normales

`RESERVE` y sellos terminales incluyen `{operation_id, reservation_hash, reservation_index, binding, anchor_epoch, effect_scope_fp}`.

### 2.4 ID_KEY

- PK `{operation_id}`; sección serializable única; binding idéntico ⇒ devolver sello exacto; distinto ⇒ `BLOCKED`.

### 2.5 Autorización

```
POLICY(gate):
  misión/auth/solicitud inválidos → BLOCKED
  clase EXTERNAL_UNPROVABLE       → BLOCKED
  falta scope verificable         → BLOCKED
  binding replay                  → BLOCKED
  otherwise                       → ADMITTED
```

### 2.6 Anti-replay

`{mission, request_hash, anchor_epoch, reservation_index, key_epoch}` incluidos; desafío fresco cuando aplique; duplicado ⇒ `NOT_DETERMINED`.

## 3. MENSAJES Y CRIPTOGRAFÍA (B-01 OPEN)

### 3.1 Estructuras

```
MSG_BODY := STRUCT(SCHEMA_ID("IER-MSG-BODY-v1"),
                  { kind, from, to, operation_id, anchor_epoch,
                    payload,                     -- PROOF viajará aquí como bytes; sin firma interna
                    issued_at,                   -- TIMESTAMP; informativo
                    protocol_version,            -- "IER-MSG-v1"
                    key_id, alg, key_epoch })    -- alg := "Ed25519"; key_epoch INT(8) BE

signature_input := b"IER-AUTH-SIG-v1\x00" || CANON(SCHEMA_ID("IER-MSG-BODY-v1"), ... MSG_BODY bytes ...)
signature       := ed25519_sign(sk, signature_input)                  -- dominio = bytes literales canónicos, no concatenación ad-hoc

msg_id          := SHA256( b"IER-MSG-ID-v1\x00" || MSG_BODY_BYTES )   -- todos los bytes autenticados; envelope no participa

MSG_ENVELOPE := STRUCT(SCHEMA_ID("IER-MSG-ENV-v1"),
                      { msg_id, body: <bytes MSG_BODY>, signature })
```

**Reglas:** una sola firma por mensaje; `payload` transporta `EFFECT-PROOF` y `ABORT-PROOF` (no existe un segundo contrato de firma); `msg_id` cubre **todo** lo firmado; ningún hash contiene la firma ni el msg_id.

### 3.2 Key registry pineado

```
(from, key_id, alg, key_epoch) → { pk_bytes (32 B), status: ACTIVE|REVOKED|RETIRED, not_before, not_after, curve: "Ed25519" }
- from desconocido ⇒ MSG_REJECTED
- key REVOKED/RETIRED/fuera de ventana ⇒ MSG_REJECTED
- key_epoch monotónico por componente (no reutilización)
- rotación: nuevo key_id, nuevo key_epoch; viejo pasa a RETIRED
- congelación en W (pineada) y en A
```

### 3.3 Kinds

`reserve_req | reserve_res | reserve_conf | abort_req | abort_res | effect_proof | abort_proof | status_req | status_res | ack | challenge_req | challenge_res`

### 3.4 Entrega

- at-least-once + dedupe por `msg_id`; acks idempotentes; `status_req/res` desde almacenamiento; pendiente ⇒ `RECOVERABLE|NOT_DETERMINED` según §4.2.
- Cada transición debe estar cubierta por `S0..S13` (§1.4) o produce `NOT_DETERMINED`.

## 4. B-03/B-08 — W y NV como protocolo recuperable

**Principio:** W (LMDB/WAL durable) y NV (hardware TPM) son medios distintos; **ninguna transacción abarca ambos**. La recuperación se apoya en un protocolo de intención durable + reconciliación. No se promete atomicidad.

### 4.1 Medios durables

```
W_store := { staged_msg, verified_msg, markers, ledger, acks }
W_marker := { operation_id, msg_id, event_kind, expected_counter,
              previous_counter, previous_header, binding, proof_hash, anchor_epoch,
              state: MARKER_DURABLE }
```

**exclusión (una sola NV call en vuelo):** W procesa una operación a la vez entre `VERIFIED → ENTRY_DURABLE`. Dos operaciones concurrentes rechazadas con `RETRY` (la misma op_id) o son serializadas.

### 4.2 W_STAGE (explícito y durable)

```
RECEIVED → VERIFIED → MARKER_DURABLE → NV_CALL_IN_FLIGHT → NV_CONFIRMED
                                          → ENTRY_DURABLE → ACK_PENDING → ACKED
```

Estados terminales de error: `GAP_REQUIRED`, `FAILED_CONSUMED`, `NOT_DETERMINED`.
Cada transición persiste el estado anterior en `W_store.markers`/`ledger`; ninguna transición salta del orden normativo.

### 4.3 Secuencia obligatoria

```
1. RECEIVED: verificar mensaje (firma/registry/binding/scope); staged_msg durable
2. VERIFIED: verificación pura superada
3. MARKER_DURABLE: marker persistido en W (expected_counter=prev+1, proof_hash, prev_header)
4. NV_CALL_IN_FLIGHT: W invoca TPM2_NV_Increment(counterNV) — único escritor autorizado
5. NV_CONFIRMED: NV muestra expected_counter (nv_read autenticado con AK pineada)
6. ENTRY_DURABLE: ENTRY(kind, index=next, counter_value=expected_counter, msg_id, binding, reservation_index, prev_header) escrita y encadenada
7. ACK_PENDING → ACKED
```

### 4.4 Recuperación por rama (exhaustiva)

| Observado tras crash | Interpretación | Acción |
|---|---|---|
| `RECEIVED` (sin marker durable) | nada durable | re-procesar mensaje; NV no consumido |
| `VERIFIED` (sin marker) | verificación ok, sin NV | escribir marker; pasar a `MARKER_DURABLE` |
| `MARKER_DURABLE` ∧ `NV < expected` | incremento no aplicado | loguear; re-intentar NV_Increment (una vez por rama; ambigüedad ⇒ abstención) |
| `MARKER_DURABLE` ∧ `NV == expected` | incremento consumido, ENTRY no escrita | escribir ENTRY; aplicar GAP si falta o aplicar ENTRY y otros contadores posteriores según §4.5 |
| `MARKER_DURABLE` ∧ `NV > expected` | estado inesperado | investigar TODOS los counter consumidos sin ENTRY (§4.5); si alguno irreconciliable ⇒ `NOT_DETERMINED`; nunca auto-asumir uno solo |
| `NV_CONFIRMED` ∧ `ENTRY_DURABLE` ausente | ENTRY perdida | reconstruir ENTRY mínima con marker (`kind`, `index`, `counter_value`); verificar idempotencia con operación idéntica (msg_id); si existe ENTRY id ⇒ sólo ACK |
| `ENTRY_DURABLE` ∧ `ACK_PENDING` | nada de confianza perdida | reenviar ACK (idempotente) |

### 4.5 Resolución NV > esperado (exhaustiva sobre counters consumidos)

```
para c in (last_persisted_counter+1 .. NV_read):
    si ENTRY(c) válida encadenada: continuar
    si marker(c) durable: validar contra marker y escribir ENTRY
    else: escribir GAP(c) INIGUO (opaco) y marcar operation at c :: FAILED_CONSUMED
consenso final: toda c consumida tiene ENTRY o GAP; si alguna c irreconciliable se aborta con NOT_DETERMINED global
```

Un counter consumido sin marcador ni ENTRY ⇒ imposible ⇒ `NOT_DETERMINED` (nunca se asume el contenido).

### 4.6 `index` vs `counter_value` (elección formal)

```
index         = posición ordinal de la entrada en el ledger W
counter_value = valor del contador NV consumido
header_i      = SHA256("IER-HEADER-v1\x00" || STRUCT(SCHEMA_ID("IER-HEADER-v1"), { prev_header, entry: ENTRY_i } ))

E_i.index         = E_{i-1}.index + 1
E_i.counter_value = E_{i-1}.counter_value + 1

GAP(n)            = ENTRY{ kind:"gap", index:n, counter_value:n } — opaco; nunca lleva operation_id
checkpoint        = ENTRY{ kind:"checkpoint", index, counter_value } — sellado autenticado
```

`index` y `counter_value` son independientes en ML (`counter_value ∈ NV`, `index ∈ ledger`) pero alineados 1:1 en W por construcción; checkpoints autentican ambos.

### 4.7 Atestación TPM (verificación completa)

```
nv_read-certification (TPM2_NV_Certify):
  qualifyingData   = STRUCT(SCHEMA_ID("IER-TPMNV-QUALIFY-v1"),
                           { challenge_random, witness_id, prev_header,
                             slots: ARRAY(INT(8) BE), anchor_epoch })
  verificación:
    - TPMS_ATTEST magic == TPM_GENERATED_VALUE
    - type == TPM_ST_ATTEST_NV
    - qualifiedSigner == AK pineada; AK chain valida a root pineada
    - extraData == qualifyingData (byte equality)
    - attested NV name == name pineado del índice contador (TPMA_NV_COUNTER, name=H(publicArea))
    - value de certificación == expected_counter
    - signature válida bajo AK
    - nonce freshness (válido para challenge de la sesión actual)
    - cualquier fallo ⇒ NOT_DETERMINED
replay: challenge_random único por misión; reutilizado ⇒ rechazo
```

### 4.8 Exclusividad y corrupción

- Sólo W puede incrementar el índice NV (policyWrite pineada por AK).
- Un incremento desde fuera ⇒ invariante roto ⇒ `NOT_DETERMINED` global.
- W perdido (base restaurada antigua) ⇒ verificación de continuidad obligatoria vía NV/chain/checkpoints; si no verifica ⇒ `NOT_DETERMINED`; nunca se continúa con estado parcial.

## 5. B-05 — V: completitud y dominio certificable

**Principio:** la ausencia de modificación en una fuente incompleta no demuestra ausencia de efecto. La prueba exige demostrablemente que el rango observado está completo y que el dominio está acotado y declarado.

### 5.1 Doble reconstrucción y dominio certifiable

```
FUENTE ├─ WAL real: tuple changes reconstructed (INSERTs/UPDATEs/DELETEs, scope+allits effect tables)
       └─ runtime_log declarado: lo que A escribió en la misma transacción
```

```
CERTIFICABLE:
  INSERT/UPDATE/DELETE sobre tablas enroladas; cambios completamente observables y
  correspondencia 1:1 con WAL y con runtime_log; claim==real.

NO CERTIFICABLE (default → NOT_DETERMINED, nunca prueba):
  DDL; secuencias nextval/setval; funciones con efectos externos; tablas fuera del scope;
  efectos mediados por extensiones/funciones no observables; captura incompleta;
  efectos por RLS/triggers fuera del scope; subtransacciones abortadas que consumen
  filas implicadas pero no persisten; TOAST divergente (§5.3).
```

### 5.2 Captura completa (precondición demostrable)

- `wal_level=logical`; **publicación sin filtros**, todas las tablas del scope enroladas (sin row/column filters); `REPLICA IDENTITY FULL` o pineado equivalente.
- **plugin y versión pineados** (`pgoutput` versión o compatible con decode siempre exacto); `source_id` pineado (hash serie + timeline + slot).
- **slot lógico pineado por identidad**; `restart_lsn ≤ commit_lsn` campo inicio; retención garantizada por el dominio FUENTE (sin `pg_replication_slot_advance` externo sin dictado).
- Timeline pineada; segmentos continuos con `checkpoint`-verificados; cualquier hueco ⇒ fuente no disponible ⇒ abstención.
- TOAST: la reconstrucción considera sólo las columnas modificadas observables; cualquier columna supuestamente involucrado pero no reconstruible ⇒ prueba denegada.
- Transacciones: `commit` y subtransacciones abortadas manejadas; una fila borrada por subtxn abortada NO cuenta como efecto persistido aunque esté en WAL.
- **Manifest de reconstrucción D.V obligatorio:** `source_id, anchor_epoch, timeline_id, slot_id, plugin_version, publication_id, start_lsn, end_lsn, transaction_id, commit_lsn, tables_observed, columns_observed, rows_reconstructed, missing_ranges, excluded_effects, completeness_status`.
  Si `missing_ranges` no vacío en rango observado ⇒ **prohibido emitir proof**; `NOT_DETERMINED`.
- Evidencia de captura limpia: confirmación autenticada de slot y timeline contra `confirmed_flush_lsn ≥ commit_lsn` de la transacción a verificar; divergencia ⇒ prueba denegada.

### 5.3 Runtime_log (claim de A)

`{op_id, schema_version, table, pk, before_row(CANON|NULL-CREATE), after_row(CANON), effect_scope_fp}`; si falta ⇒ proof denegado.

### 5.4 Prueba emitida por V

```
EFFECT_PROOF := payload effect_proof (sin firma propia; su firma es la del MSG que la transporta — V firma el MSG_BODY):
  { operation_id, mission, request_hash, binding, reservation_hash,
    effect_hash: SHA256( b"IER-EFFECT-DELTA-v1\x00" || STRUCT(SCHEMA_ID("IER-EFFECT-DELTA-v1"), { delta }) ),
    effect_delta, transaction_id, commit_lsn, timeline_id,
    anchor_epoch, reservation_index, source_id, effect_scope, effect_scope_fp,
    observed_at, manifest_dvr }
```

### 5.5 W verifica (conjunción)

Firma de V válida (§3) sobre MSG_BODY · `binding/reservation_hash` == sellos · `operation_id/mission/request_hash/anchor_epoch/reservation_index` de reserva · `effect_scope_fp` == sello · `source_id` pineado · timeline coherente · `completeness_status` demostrado == NOT_DETERMINED de otro modo.

### 5.6 Divergencia → rechazo

Fila/columna/tabla extra ó ausente; timeline distinta; LSN fuera de rango; slot ≠ pineado; publicación con filtro ⇒ proof denegado.

### 5.7 Abstención V

Sin poder demostrar rango completo o domain limits — `NOT_DETERMINED`, jamás prueba; no se infieren efectos silencios sin commit visible.

## 6. FUENTE WAL — contrato operativo (D-13)

### 6.1 Constitución

- Otro dominio de confianza distinto de A; identidad propia pineada en V y W (`source_id` propio).
- Publicación y tablas del scope; ninguna con filtro; retención controlada sin avance externo; partes secretas del sistema.

### 6.2 Timeline/epoch

- Timeline pineada por época; cambio ⇒ dictado humano + re-base + nueva timeline; segmentos faltantes ⇒ fuente no disponible.

### 6.3 Retención

- V no avanza el slot; retención sólo la maneja el dominio FUENTE bajo contrato; V puede leer el rango [commit_lsn-r_min, commit_lsn] completo o no emite proof.

### 6.4 Fuente comprometida/no usable

- I2 = `PARTIAL` operativo ⇒ `NOT_DETERMINED` para todo SQL_WRITE; jamás promoción; sellos W válidos pero V abstiene.
- Restore/fuente ausente ⇒ `ROLLBACK_DETECTED` o `NOT_DETERMINED` según W íntegro/no.

### 6.5 Externo — recordatorio

Sin recibo terminal durable del proveedor ⇒ `ABORT` no testificable.

## 7. B-04 — RESERVE R1/R2 y ABORT

### 7.1 Prequisito SQL

```
ops := { operation_id PK, reservation_index INT(8) BE NOT NULL,
         binding BYTES(32) NOT NULL, reservation_hash BYTES(32) NOT NULL,
         effect_scope_fp BYTES(32) NOT NULL,
         verdict TEXT NOT NULL CHECK (verdict IN ('pending','committed','aborted','unknown')),
         reservation_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
         ... }
```

`EXECUTE` exige `verdict='pending' ∧ reservation_confirmed=true ∧ binding match`.

### 7.2 Protocolo R1/R2 (RESERVE_CONFIRMED) con recuperación

```
R1 (A → W RPC reserve_req):
    W: RESERVE_REQUESTED local durable → sección crítica única:
        1. read NV current → expected_counter := current + 1
        2. persist marker{expected_counter, op_id, msg_id, bindings..., proof_hash=NULL, prev_header}
        3. TPM NV_Increment
        4. ENTRY(kind=reserve, index=expected_counter, counter_value=expected_counter,
                 msg_id, binding, reservation_index := expected_counter, prev_header)
        5. ops persistido W-state=RESERVE_DURABLE
        6. ACK a A con reservation_index
    A: INSERT INTO ops(operation_id, reservation_index := n, binding, reservation_hash,
                        effect_scope_fp, verdict='pending', reservation_confirmed := false)

R2 (A → W RPC reserve_conf):
    W: verificar {operation_id, reservation_index, binding} contra R1;
       OPREC{state=RESERVED_CONFIRMED}
    A → W: reserve_conf; W persist RESERVED_CONFIRMED; envía ACK; A marca reservation_confirmed := true
```

**Asignación del índice:** dentro de la sección crítica W (1–6 pasos); dos operaciones no pueden asignar el mismo índice; `expected_counter` se calcula desde una lectura NV fresca pineada, no estimada.
**RESERVE_DURABLE no implica ejecución.** Ops.reservation_confirmed=false bloquea EXECUTE siempre.

### 7.3 Recuperación según caídas

| Caída | Resultado |
|---|---|
| W antes de marker | no existe reserva durable; reintento limpio |
| W post-marker pre-NV_Increment | recovery §4 → MARKER_DURABLE→ learn NV; reintentar increment una vez; ambigüedad ⇒ GAP_REQUIRED |
| W post-NV, pre-ENTRY | recovery §4 → ENTRY o GAP en función de marker vs NV |
| W post-ENTRY, pre-ACK | W reenvía ACK idempotente |
| A antes de INSERT ops | RESERVED_ORPHAN |
| A post-INSERT pre-conf | retry INSERT idempotente; reserve_conf repetido |
| W confirmacion duplicada | W devuelve estado actual; sello sobreseído |
| Binding distinto para op_id | BLOCKED |
| `reservation_index` distinto del sello W o del ops | rechazo obligatorio | BLOCKED |
| W pierde base | re-verificación §4.8; si no pasa ⇒ NOT_DETERMINED |

Reserva huérfana consume slot; no reasignada jamás; pide dictado humano ⇒ `HUMAN_CLOSED`.

### 7.4 Rutas de efecto y propiedad ABORT (condicional)

**Enrolled(R)** ⟺ todas las rutas capaces de modificar tablas de efecto pasan por las reglas del guard; **Inventario D-5 fresh** (§8.2/8.7) verificado en admisión. De no poderse auditar frescamente: **no testifica ABORT**.

EXECUTE y ABORT compiten por `ops[operation_id]`:
```
EXECUTE: BEGIN; SELECT .. FOR UPDATE WHERE operation_id=:op AND reservation_confirmed=true; verdict==pending?→ aplicar efecto; UPDATE ops SET verdict='committed' WHERE operation_id=:op AND verdict='pending' RETURNING 1; COMMIT;
ABORT:   BEGIN; SELECT .. FOR UPDATE ...; verdict==pending? → UPDATE ops SET verdict='aborted' WHERE operation_id=:op AND verdict='pending' RETURNING operation_id; COMMIT; else rollback)
```
La transición nula es la exclusión misma; D-5 garantiza ausencia de rutas alternativas (funciones, triggers, security definer, FK cascade, event triggers DDL).

### 7.5 ABORT terminal — prueba y condición

Prueba ABORT completa:

```
{ operation_id, binding, reservation_hash, reservation_index,
  transaction_id, commit_lsn, timeline_id,
  catalog_fingerprint (deploy_fp de §8.4), terminal_verdict:"aborted",
  source_id, anchor_epoch }
```

Producción de campos:
- V / A: transaction_id, commit_lsn, timeline_id, catalog_fingerprint (verificable con deploy_fp válido al momento de la transición);
- W: binding/reservation_hash/reservation_index/anchor_epoch verificados;
- `terminal_verdict` durable transaccional (SELECT verdict post-commit).

### 7.6 Externo

Sin recibo terminal durable del proveedor ⇒ ABORT no testificable.

## 8. B-06 — D-5: inventario + fingerprint + guarda del despliegue

### 8.1 Detección de restore

W sellado + revalidación incompatible ⇒ `ROLLBACK_DETECTED`.

### 8.2 Inventario completo de objetos capaces de mutar comportamiento

Aut ite, tabla de elementos obligatoria (checked on D-5 fresh):

| Categoría | Catálogo |
|---|---|
| Esquemas | pg_namespace |
| Tablas | pg_class (relkind, relam, relhasoids), pg_attribute (typid, typmod, attnotnull, atthasdef), pg_attrdef |
| Restricciones | pg_constraint (contype FK/PK/UNIQUE/NOT NULL/check/exclusion) |
| Índices | pg_index |
| Dependencias | pg_depend, pg_rewrite |
| Funciones | pg_proc (proname, prosrc, pronamespace, prosecdef, provolatile, prolang) |
| Triggers | pg_trigger (tgrelid, tgfoid, tgtype, tgenabled, tgconstraint) |
| Eventos DDL | pg_event_trigger |
| Extensiones | pg_extension (extname, extversion) |
| Publicaciones | pg_publication, pg_publication_rel, pg_publication_tables |
| RLS | pg_policy (polrelid, polname, polqual, polwithcheck, polcmd, polroles) |
| Secuencias | pg_sequence |
| Roles | pg_roles, pg_auth_members (rolname, rolsuper, rolcreaterole, rolbypassrls, effective chains) |
| Particiones | parent/child relations |
| Vistas | pg_views, pg_matviews |
| FDW | pg_foreign_table/pg_foreign_server/pg_foreign_data_wrapper |
| Reglas/rules | pg_rewrite |

Indice en cada catálogo la columna clave usada para ordenar SERIALIZADO; todo objeto descubierto no incluido en catálogo ⇒ deployment NO fingerprintable; D-5 no confiable esta vez.

### 8.3 Serialización CANON_CATALOG

```
catalog_snapshot := STRUCT(SCHEMA_ID("IER-CATALOG-SNAPSHOT-v1"),
                  { deployment_id, database_identity, objects:[...sorted by OID...], dependencies:[...],
                    effective_privileges:[...], extensions:[...], planner_flags (preset config relevant) ,
                    relrowsecurity_per_table } )
catalog_fp  := SHA256( b"IER-CATALOG-FP-v1\x00" || catalog_snapshot )
policy_fp   := SHA256( b"IER-POLICY-FP-v1\x00" || catalog_fp || policy_hash )
```

- Objetos y aristas ordenados determinísticamente; cada objeto serializa name y atributos significativos; objetos no reconocidos ⇒ hash falla ⇒ bloqueo total.
- `policy_hash` = hash de la política declarada (REGLAS de deployment: roles, writer-role, tables enrolled, op-classes).

### 8.4 Protectores del fingerprint durante la operación (deployment guard)

El guard debe descansar sobre **mecanismos, no sobre adjetivos**. En IER-GATE el despliegue protegido exige, antes de admitir cualquier operación, demostrar que estas condiciones están impuestas fuera del gate:

**Capa 1 — Separación de privilegios para DDL**

- Sólo el rol `ier_guard`, creado por el operador del despliegue y ajeno a la aplicación, tiene privilegios `CREATE|ALTER|DROP|TRUNCATE|REFERENCES|TRIGGER|RULE` sobre los objetos protegidos.
- `public`, `IER_GATE_APP_WRITER`, `IER_RUNTIME`, `ops_writer` **no** tienen ninguno de esos privilegios sobre los objetos protegidos.
- Los roles de auditoría no heredan privilegios DDL vía `ier_guard`: el guard **no delega**.

**Capa 2 — Guard durante la transición completa**

```
ADMISSION:
    A adquiere estado `deployment_guard = ACTIVE` en W (estado durable, ligado a la época en curso).
    Se registra catalog_fp_before (pre-snapshot de §8.2) y se tranca el estado.
    Mientras `ACTIVE`, cualquier DDL proveniente de fuera de `ier_guard` es rechazada por el motor mediante `ier_guard_audit_trigger`.

EXECUTION:
    Las rutas enroladas (§7) son las únicas que mantienen escritura.
    Cualquier DDL-capaz de otras conexiones incontra evento denegado.

VERIFICATION:
    catalog_fp_after := nuevo snapshot idéntico (§8.2).
    catalog_fp_after == catalog_fp_before  →  liberar guard; marcar `deployment_guard = INACTIVE`; emitir resultado.
    catalog_fp_after != catalog_fp_before  →  ninguna operación en el scope se sello;
                                               `ROLLBACK_DETECTED`; prueba denegada; reconciliación humana (§8.5).
```

**Capa 3 — Hooks permanentes durante el guard**

- `pg_event_trigger` `ier_guard_audit_trigger` permanece instalado y activo mientras `ACTIVE`. Si el trigger falta en cualquier momento de la operación: nada puede marcarse como `ACTIVE`; cualquier operación entra `NOT_DETERMINED`.
- `ier_guard_audit_trigger` registra en `deployment_guard_audit_log` todos los intentos denegados; se conserva hasta dictado de revisión del operador.

**Capa 4 — Fuera del modelo**

- Compromiso del hipervisor, del disco, del TPM o del sistema operativo del host.
- Un superusuario con credenciales fuera de control del operador: es el riesgo residual; no está bajo contrato del gate.
- Undefine/redefine de índice NV (p. ej., tras un reboot malicioso): tratado como pérdida de continuidad (`NOT_DETERMINED`).

Toda unidad que no cumpla Capas 1–3 no puede ser admitida; antes de cada operación protegida, el despliegue exige admitir otra vez esas precondiciones.

### 8.5 Grafo de dependencias

Nodos `db.schema.table[.col]`; aristas `READ|WRITE|CALL|TRIGGER|CASCADE|REFERENTIAL`; `unknown ⇒ dependent`. Disjunción exigida = demostrabilidad bajo fingerprint; si no ⇒ bloqueo o `NOT_DETERMINED`.

### 8.6 Bloqueo obligatorio en ROLLBACK_DETECTED

Como §8.4 (dependiente bloqueado; desconocido bloqueado; reejecución bloqueada), con fingerprints de §8.3.

### 8.7 Reconciliación

Humana; sin automatismo: `G = HUMAN_CLOSED`; sello histórico intacto; dictado por humano (nadie más abre el bloqueo).

### 8.8 ABORT tras restore

ABORT_TESTIFIED previo + restore ⇒ `ROLLBACK_DETECTED`; re-ejecución válida sólo por dictado humano con nueva operación/nuevo op_id.

## 9. ESPECIFICACIÓN CANON — BOOTSTRAP INDEPENDIENTE Y BIN-B

### 9.0 Criterio de aceptación

\[ B02_{\text{CLOSED}} \iff B \land T \land R \land I \]

- \(B\) bootstrap completamente especificado, no circular.
- \(T\) gramática inequívoca: tipos, tags, dominios, límites.
- \(R\) registro y evolución de esquemas definidos.
- \(I\) vectores positivos, negativos y de frontera reproducibles.

**B-02 permanece OPEN hasta verificar.** No se congelará nada antes de dos codificadores independientes coincidiendo en bytes (OP-NEXT-1 todavía no autorizada).

### 9.1 Bootstrap: gramática normativa (independiente de BIN-B)

```
SCHEMA_DEF_BYTES := MAGIC || name || version || count || field_1 || ... || field_n
MAGIC            := b"IER-SCHEMA-BOOTSTRAP-v1\x00"           (24 bytes exactos)
name             := UINT32 len || len OCTETS UTF-8-NFC
version          := UINT32 len || len OCTETS UTF-8-NFC        (publicado: "1"; versionado: un campo literal en el descriptor)
count            := UINT32 BE                                  (≤ 512; número de campos)
```

```
FIELD            := fname || type_id || required || min_len || max_len || type_meta
fname            := UINT32 len || len OCTETS UTF-8-NFC        (nombre único por schema)
type_id          := UINT8                                      (registro §9.2)
required         := 0x00 | 0x01                                (otros valores ⇒ invalid)
min_len          := UINT32 BE                                  (0x00000000 = sin límite inferior)
max_len          := UINT32 BE                                  (0xFFFFFFFF = sin límite superior)
type_meta        := depende de ARRAY|MAP|ENUM|STRUCT; véase TYPE_DESCRIPTOR
```

Restricciones para los tipos escalares con tamaño:
- `STRING`, `ENUM`, `BYTES`: `min_len ≤ max_len`; si `min_len == max_len` el tipo exige longitud fija (p. ej., `BYTES(32)` ⇒ `min_len == max_len == 32`).
- `DECIMAL`: se reutiliza `min_len`/`max_len` como `scale_min/scale_max` (ambos ≤ 38; el desborde de IEEE 128 bit de magnitud del campo invalida el valor).
- `TIMESTAMP`: sin restricción adicional (`min_len == 0`, `max_len == 0xFFFFFFFF`).
- `INT64`, `UINT64`, `UINT32`, `UINT16`, `UINT8`: idem sin restricción.
- `ARRAY`/`MAP`: `min_len`/`max_len` aplican al `count` de elementos.

`type_meta` requerido para ARRAY, MAP, ENUM y STRUCT. Terminación automática en primitivo antes de satisfacer ningún nivel recursivo. Tipos compuestos permitidos hasta profundidad 32.

```
TYPE_DESCRIPTOR := type_id (1 B) || type_meta(type_id)

type_meta(type_id) :=
      (ausencia total)                                                                               para NULL|BOOL|UINT64|UINT32|UINT16|UINT8|INT64|STRING|BYTES|DECIMAL|TIMESTAMP
    | TYPE_DESCRIPTOR                                                                               para ARRAY (tipo de cada elemento; el descriptor es recursivo, recortado por profundidades)
    | TYPE_DESCRIPTOR || TYPE_DESCRIPTOR                                                            para MAP (key_type y value_type en orden)
    | UINT32 len || len OCTETS UTF-8-NFC (nombre del dominio ENUM)                                  para ENUM (nombre resuelto contra el registro de dominios)
    | UINT32 len || len OCTETS UTF-8-NFC (nombre del schema destino)                                para STRUCT (nombre resuelto contra el registro de schemas; su instancia lleva schema_id)
```

LAYOUT DE INSTANCIA (BIN-B, valor concreto de ese campo presente, STRUCT como 0x0F):

```
STRUCT := 0x0F || schema_id (32 B) || n_field_bytes (1 B) || field_mask || valores presentes en orden de declaración del descriptor
n_fields      := len(descriptor.fields)         (≥ 1 y ≤ 512; cantidad TOTAL declarada)
required(i)   := descriptor.fields[i].required ∈ {TRUE, FALSE}
field_mask    := little-endian bits, bit i = 1 iff campo i presente en la instancia
n_field_bytes := ceil(n_fields / 8)             (1..64; n_fields ≥ 1 obligatorio)
bits > n_fields en el último byte ⇒ CANON_ERROR (reject)
required(i) == TRUE y bit i == 0 ⇒ CANON_ERROR
```

Reglas de rechazo:

- Valor de STRUCT instancia con `schema_id` no presente en el registro ⇒ `NOT_DETERMINED` (nunca adivinar).
- Nombre de schema destino (en descriptor) no registrado ⇒ `CANON_ERROR` (descripción malformada).
- Campo STRUCT instancia con `schema_id` incompatible con el nombre declarado en el descriptor del campo contenedor ⇒ `CANON_ERROR`.
- Campo instancia STRUCT cuyo field_mask activa bits fuera del rango descrito por n_fields ⇒ `CANON_ERROR`.
- Requerido declarado en descriptor pero presente=0 en instancia ⇒ `CANON_ERROR`.

Terminación automática en primitivo antes de satisfacer ningún nivel recursivo. Tipos compuestos permitidos hasta profundidad 32.

Por ejemplo, `ARRAY<MAP<STRING, ARRAY<INT64>>>` se serializa como:

```
0D 0E 08 0D 07                    -- ARRAY(0x0D) MAP(0x0E) STRING(0x08) ARRAY(0x0D) INT64(0x07)
```

Por ejemplo, `STRUCT<"IER-OP-v1">` como descriptor de un campo `child`:

```
0F 0000000A 49 45 52 2D 4F 50 2D 76 31                    -- tag 0x0F + UINT32 len(0x0A) + bytes "IER-OP-v1"
```

Por ejemplo, una instancia de ese campo con `mission, auth_id_hash, request_hash, nonce, purpose` completos:

```
0F <schema_id de IER-OP-v1 (32 B)> 01 1F 08 00000001 6D 09 00000020 00 01 02 ... 09 00000020 20 ... 3F 09 00000010 10 ... 1F 0A 00000004 74 65 73 74
```

\[ schema\_id = SHA256( D_{\text{SCHEMA-ID-v1}} \parallel SCHEMA\_DEF\_BYTES ) \]
\[ D_{\text{SCHEMA-ID-v1}} = b"IER-SCHEMA-ID-v1\x00" \]

### 9.2 Tabla cerrada de `type_id` (sin colisiones)

| `type_id` | Tipo | Payload binario | Validación |
|---|---|---|---|
| 0x01 | NULL | 0 bytes | ausencia ≠ NULL; ambos distinguibles |
| 0x02 | BOOL | 1 byte (`0x00`/`0x01`) | otros valores ⇒ invalid |
| 0x03 | UINT64 | 8 B BE unsigned | n ∈ [0, 2⁶⁴−1] |
| 0x04 | UINT32 | 4 B BE unsigned | n ∈ [0, 2³²−1] |
| 0x05 | UINT16 | 2 B BE unsigned | n ∈ [0, 65535] |
| 0x06 | UINT8 | 1 byte unsigned | n ∈ [0, 255] |
| 0x07 | INT64 | 8 B BE two's complement | n ∈ [−2⁶³, 2⁶³−1] |
| 0x08 | STRING | UINT32 len + UTF-8 NFC | NFC, UTF-8 estricto, sin BOM, control <0x20 prohibido |
| 0x09 | BYTES | UINT32 len + raw | sin interpretación de encoding |
| 0x0A | ENUM | UINT32 len + UTF-8 NFC | dominio declarado contra registro; dominio no registrado ⇒ NOT_DETERMINED; valor no permitido ⇒ CANON_ERROR |
| 0x0B | DECIMAL | UINT8 scale + INT128 BE two's comp | scale ∈ [0,38]; minimal: si s>0 ⇒ \|v\| mod 10 ≠ 0; cero único con scale=0 |
| 0x0C | TIMESTAMP | INT64 BE µs UTC | n ∈ [0, 2⁶³−1]; negativos ⇒ invalid |
| 0x0D | ARRAY | UINT32 count + items en orden | count ≤ 2²⁴; items del `element_type_id` declarado |
| 0x0E | MAP | UINT32 count + entries ordenadas | count ≤ 2²⁴; claves únicas; orden por bytes CANON(key) |
| 0x0F | STRUCT | `schema_id` (32 B) + `n_field_bytes` (1 B) + `field_mask` + campos presentes en orden del descriptor | n_fields ≤ 512 |

Ningún otro `type_id` es válido. Todo valor fuera de rango ⇒ `CANON_ERROR`.

### 9.3 BIN-B — gramática de valores

```
value := 0x01                                      (NULL)
      |  0x02 || 0x00 | 0x01                       (BOOL)
      |  0x03 || UINT64 BE                          (UINT64)
      |  0x04 || UINT32 BE                          (UINT32)
      |  0x05 || UINT16 BE                          (UINT16)
      |  0x06 || UINT8                              (UINT8)
      |  0x07 || INT64 BE two's complement          (INT64)
      |  0x08 || UINT32 len || len OCTETS UTF-8 NFC (STRING)
      |  0x09 || UINT32 len || len OCTETS raw       (BYTES)
      |  0x0A || UINT32 len || len OCTETS UTF-8 NFC (ENUM)
      |  0x0B || UINT8 scale || INT128 BE two's comp(DECIMAL)
      |  0x0C || INT64 BE µs UTC                    (TIMESTAMP)
      |  0x0D || UINT32 count || items              (ARRAY)
      |  0x0E || UINT32 count || entries            (MAP)
      |  0x0F || schema_id (32) || UB(1 B) || mask || present (STRUCT)
```

### 9.4 STRUCT — reglas

`STRUCT` normativa (una única regla raíz, descriptor e instancia):

```
STRUCT instance := 0x0F || schema_id (32 B) || n_field_bytes (1 B) || field_mask
                   || valores presentes en el orden de declaración del descriptor
n_field_bytes := ceil(n_fields / 8)         (1..64, para 1 ≤ n_fields ≤ 512; jamás 0)
n_fields    := len(descriptor.fields)        (≥ 1)
field_mask  := little-endian bit i = 1 iff campo i declarado en el descriptor presente en la instancia
present(i) := (mask[⌊i/8⌋] >> (i mod 8)) & 1
required   := (required_mask & field_mask) == required_mask
```

- **STRUCT descriptor**: un campo cuyo `type_id == 0x0F` en el `SCHEMA_DEF` declara únicamente `schema_name` del schema destino (nombre NFC registrado; ver §9.1). No transporta `schema_id` binario en el descriptor.
- **STRUCT instance**: lleva el `schema_id` binario (32 B) del schema destino y el `field_mask` de la instancia; el descriptor del campo no transporta `schema_id`, por lo que no hay ciclo `schema_id → CANON(STRUCT) → schema_id`.
- **Referencias cíclicas** entre schemas son legales: la resolución es por nombre, no por `schema_id`. La profundidad de descenso instanciado queda acotada por §9.8 (≤ 32).

### 9.5 MAP — orden y unicidad

```
MAP := 0x0E || UINT32 count || entries sorted por bytes CANON(key)
entries := canon(k)|canon(v) * count; count declarado ≠ real ⇒ invalid; duplicados ⇒ invalid
```


### 9.6 Tipos con restricción de tamaño y `typed_value`

Restricciones admitidas por el descriptor (§9.1):

```
BYTES(N) := type_id=0x09, min_len = max_len = N       -- longitud fija obligatoria
BYTES(M..N) := type_id=0x09, min_len = M, max_len = N -- rango declarado
STRING(N) := type_id=0x08, min_len = max_len = N      -- longitud fija obligatoria
STRING(M..N) := type_id=0x08, min_len = M, max_len = N
BYTES(any) := type_id=0x09, min_len = 0, max_len = 0xFFFFFFFF
STRING(any) := type_id=0x08, min_len = 0, max_len = 0xFFFFFFFF
```

`typed_value` es una unión discriminada — definida aquí y utilizada por el campo `pk` de `IER-EFFECT-DELTA-v1` (§9.13) y por el campo `payload` de cualquier prueba:

```
typed_value := 0x01 (NULL) | 0x02 | 0x03 | 0x04 | 0x05 | 0x06   -- primitivos
            | 0x07 (INT64)      -- INT64
            | 0x08 || len || bytes                     -- STRING
            | 0x09 || len || bytes                     -- BYTES
            | 0x0A || len || bytes                     -- ENUM
            | 0x0B || scale || magnitude(16 bytes)     -- DECIMAL
            | 0x0C || epoch microseconds               -- TIMESTAMP
            | 0x0D || count || item(typed_value)*      -- ARRAY(homogeneous)
            | 0x0E || count || (key,value)*            -- MAP (orden canónico)
```

Reglas adicionales:
- `typed_value` para ARRAY exige homogeneidad: todos los elementos deben tener el mismo `type_id` declarado en el descriptor.
- `typed_value` para MAP exige `key_type == STRING`.
- Desbordamiento de `typed_value` compuesto (deriva de tamaño) ⇒ `CANON_ERROR`.
- Sin `type_id` coincidente con la declaración prescrita en el descriptor ⇒ `CANON_ERROR`.

### 9.7 ENUM — dominios cerrados (normativos)

```
kind_entry  := reserve|commit|abort|gap|checkpoint                              (IER-ENTRY-v1)
kind_msg    := reserve_req|reserve_res|reserve_conf|abort_req|abort_res|
               effect_proof|abort_proof|status_req|status_res|ack|challenge_req|challenge_res
from_to     := A|V|W|CLIENTE|PROVEEDOR
op_class    := EFFECT_SQL_WRITE|EFFECT_EXTERNAL_IDEMPOTENT|EFFECT_EXTERNAL_UNPROVABLE
operation   := CREATE|UPDATE                                          (IER-EFFECT-DELTA-v1)
dep_kind    := DEPENDENCY|RESTRICT|EXCLUDE                             (IER-DEP-POLICY-v1)
dep_type    := CALL|READ|WRITE|TRIGGER|CASCADE|REFERENTIAL             (policy model)
```

```
Tres condiciones con tres resultados distintos (no se mezclan):

  Codificación binaria malformada (por ejemplo, len imposible)   ⇒ CANON_ERROR
  Dominio no registrado en el registro activo                      ⇒ NOT_DETERMINED   (jamás se inventa semántica)
  Dominio conocido pero valor no pertenece al conjunto admitido    ⇒ CANON_ERROR
```

### 9.8 Normalización

- STRING: UTF-8 estricto, NFC; sin BOM; control bytes <0x20 prohibido; bytes 0x7F-0x9F permitido Unicode pero no C0/C1; un valor no aceptado ⇒ `NOT_DETERMINED` para el mensaje entero.
- MAP: unicidad y orden CANON.
- DECIMAL: minimalidad obligatoria con |v| y s<0 prohibido.
- BOOL: sólo 0x00/0x01.
- TIMESTAMP: µs UTC ≥ 0.
- ENUM: dominio resuelto exactamente contra el registry; dominio desconocido ⇒ `NOT_DETERMINED`; valor fuera del dominio conocido ⇒ `CANON_ERROR`.

### 9.9 Límites y validación

```
profundidad ≤ 32 · tamaño total ≤ 4 MiB · nodos ≤ 2²¹ · MAP/ARRAY count ≤ 2²⁴ · n_fields ≤ 512
orden de validación: rechazo fail-fast en orden de lectura; un solo error descarta el mensaje entero;
ningún sub-objeto se procesa después del primer error.
```

### 9.10 Tipos compuestos — gramática y terminación

```
nested := PRIMITIVE                                   -- NULL | BOOL | UINT* | INT64 | STRING | BYTES | DECIMAL | TIMESTAMP
       | ARRAY(nested)                                -- 0x0D + UINT32 count + items del nested
       | MAP(nested, nested)                          -- 0x0E + UINT32 count + pairs key/value de nested
       | STRUCT(schema_name)                          -- schema reference, name; la instancia lleva schema_id
```


terminación: cada nivel reduce el presupuesto de profundidad; agotamiento ⇒ `CANON_ERROR`. Referencias entre esquemas permitidas como ciclos; progreso acotado por §9.8. La referencia por **nombre** evita ciclo `schema_id → CANON → schema_id`; la semántica de un STRUCT procede siempre del registro, no del propio valor.

### 9.11 Política ante esquemas desconocidos

```
schema_id no registrado                ⇒ NOT_DETERMINED
schema_id conocido con descriptor fijado pero bytes incompatibles ⇒ CANON_ERROR
campo STRUCT cuyo schema_id difiere del esperado por el descriptor contenedor ⇒ CANON_ERROR
field_mask inválido (bits fuera de rango, required ausente)                    ⇒ CANON_ERROR
versión de schema_def inesperada para un id                                  ⇒ NOT_DETERMINED
```

### 9.12 Vectores positivos (bytes y sha256 verificables)

```
V1  INT64 1                      bytes 070000000000000001
                                 sha256 cb46e87cf21bf247a88eba01e68fef30198cf07743192f233d75b74e0137d46c
V2  STRING "a"                   bytes 080000000161
                                 sha256 8c14a1d208c12ee58d4af154f49552c79311840b492653213a88bc2db1378963
V3  NULL                         bytes 01
                                 sha256 4bf5122f344554c53bde2ebb8cd2b7e3d1600ad631c385a5d7cce23c7785459a
V4  MAP{"s":7}                   bytes 0e00000001080000000173070000000000000007
                                 sha256 75cc9ae44a335eaf55409b0df1829352d3f22d0241ed57eabe567d02dbb4babb
V5  BOOL 1                       bytes 0201
                                 sha256 25dfd29c09617dcc9852281c030e5b3037a338a4712a42a21c907f259c6412a0
V6  IER-OP-v1 completo (mission="m" auth=00..1F req=20..3F nonce=10..1F purpose=test)
                                 schema_id a710e4256e283db21b5f9a25c3d08d50935ba2ee47681c5bdec70526bb1f9802
                                 bytes 0fa710e4256e283db21b5f9a25c3d08d50935ba2ee47681c5bdec70526bb1f9802011f
                                        08000000016d0900000020000102030405060708090a0b0c0d0e0f1011121314151617
                                        18191a1b1c1d1e1f0900000020202122232425262728292a2b2c2d2e2f303132333435
                                        363738393a3b3c3d3e3f0900000010101112131415161718191a1b1c1d1e1f0a000000
                                        0474657374
                                 sha256 b58a51ca082ec5e91b49fb7b6f05315894bf0dcb51d3dd747a058b0480c5c17f
V7  DECIMAL 123.45               bytes 0b0200000000000000000000000000003039
                                 sha256 850a9429a98feeda164e13327d02878e2258df57506004409a4de0f9dc06692f
V8  INT64 max (2^63−1)           bytes 077fffffffffffffff
                                 sha256 5ac85332e98af5ba465bd22693723ebac5e0e5f8126a47c074ea3bf67e61ea8b
V9  INT64 min (−2^63)            bytes 078000000000000000
                                 sha256 7d92c4d577eab67d6898f53d6a65db7c8bc885cc698cdd8bd32536e92c480acb
V10 ARRAY vacío                  bytes 0d00000000
                                 sha256 3c8f1b104592e3ebb2b2602b3979a27e77f586fb4c655369fa4eccb6d545a0f8
V11 DECIMAL cero scale=0        bytes 0b0000000000000000000000000000000000
                                 sha256 403aad34495f625943e5df2b1a29750817c7c214b0153a29b1613a0515e9e574
V12 STRING vacío                 bytes 0800000000
                                 sha256 18b1b592a44f7fbe33dab6a3d22857eea5118da14d6fabbc59b0681dbf1286f1
```

### 9.13 Vectores negativos (bytes concretos y SHA esperado)

```
N1  STRUCT falta obligado             bytes 0fac346adbb109199ad5e329ae779873f1ce9be27fb2eaa956ce5114b988ea7ae20100
                                      required_mask != field_mask ⇒ CANON_ERROR
                                      sha256 ef251ef3eb9e288ced7117e0730bde0e4536a2ef81c5528ab01ac8e9600d4d83
N2  STRING válida UTF-8 NFC pero no normalizada   bytes 080000000361cc81 (a + U+0301 COMBINING ACUTE; forma NFD)
                                      ⇒ CANON_ERROR (violación de la regla NFC del §9.8)
                                      sha256 9c8827dc1ba746be49192e147f04be3f9ce42be8c97d4cef3a82b37ad7b5cb5a
N3  schema_id no registrado           bytes 0fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff011f08000000016d
                                      ⇒ NOT_DETERMINED (schema id desconocido; nunca adivinar)
                                      sha256 dfde4b557c8ac41fe0022977392a8e6af19f47f6ca67b3da0c8e42c87928eedc
N4  MAP duplicado                     bytes 0e0000000208000000017301070000000000000008000000017301070000000000000007
                                      ⇒ CANON_ERROR (claves duplicadas)
                                      sha256 97323a84b38a3cacd57d24440c002414a0b7fbb58016bd71097c5c346d028f53
N5  MAP fuera de orden                bytes 0e00000002080000000162070000000000000002080000000161070000000000000001
                                      ⇒ CANON_ERROR (orden incorrecto: b ≤ a violado)
                                      sha256 9e4b181d6dcef19d1e2099fac898d4ecd2e3d559d7bfd8ac4c4cf45537d6f5ee
N6  BOOL 0x02                         bytes 0202
                                      ⇒ CANON_ERROR (rango fuera)
                                      sha256 50cff72c8e550546d661ec235431888fb2f9f7bada40c17020d47f6ccc117aae
N7  TIMESTAMP < 0                    bytes 0cffffffffffffffff
                                      ⇒ CANON_ERROR (µs negativos)
                                      sha256 f9f565a6e160373d89dea25b81c0cd02e3c4fc7994ec47c62d1f769a0a613902
N8  ARRAY count > 2²⁴                 bytes 0d01000001070000000000000001070000000000000001070000000000000001
                                      ⇒ CANON_ERROR (count 16777217 > 2²⁴)
                                      sha256 59cc8594514a482fc503b37bdd08e1994f4f4242d9c3dbb8e87bf06cdbc627a5
N9a ENUM dominio desconocido        bytes 0a0000000378797a (dominio 'xyz' no registrado)
                                      ⇒ NOT_DETERMINED (dominio no disponible; nunca adivinar)
                                      sha256 3e5f319d8676b1ec69e7f3f6f4a9a0a6a9de2022443f4c4f358848f65a82de21
N9b ENUM valor inválido (dominio conocido) bytes 0a0000000767617262616765 ('garbage', no en op_class)
                                    ⇒ CANON_ERROR (valor fuera de dominio registrado)
                                    sha256 4f0230bea0340acbc13267ab86ae21414f8639344e18f3ff2b7ec5997395f81f
N10 STRUCT esperados no coinciden    bytes 0fac346adbb109199ad5e329ae779873f1ce9be27fb2eaa956ce5114b988ea7ae20180
                                      ⇒ CANON_ERROR (bit ≥ n_fields gesetzt)
                                      sha256 50e4622a597c0522c319e8c20e6ac1c978ccdd5d5c7f4136579a052008600eeb

```
### 9.14 Registro y evolución

- Un schema publicado nunca se altera; cualquier cambio produce un schema_id nuevo.
- Extender ENUM requiere nuevo schema_id.
- Esquema de publicación en Apéndice B.

### 9.15 Estado epistémico de §9

`OPEN`. Los contenidos de esta sección son sus alphas realmente calculados bajo un encoder de referencia interna; ningún byte ha sido verificado por una segunda implementación independiente aún. B-02 no es cerrado. OP-NEXT-1 no ejecutada.
## 10. ADMISIÓN (compuesta; S=(G,P,T,O,E))

### 10.1 Evaluación (orden obligatorio)

```
1. CONTINUIDAD — W íntegro + fuente usable + checkpoints verificados?  no ⇒ G=NOT_DETERMINED
2. NEGATIVOS   — ROLLBACK_DETECTED vigente sobre scope?                 sí ⇒ G=ROLLBACK_DETECTED
3. EVIDENCIA   — proof aplicable válida + sello W ⇒ T sellado, O: EFFECT_COMMITTED|EFFECT_NOT_EXECUTED
                 ninguna ⇒ G=NOT_DETERMINED (T=NONE)
4. TERMINAL    — si T sellado, gate informa (G,T,O,E).
```

**Promoción (NUNCA habilitada por cierre documental):** §11 en verde + D-13/D-14 funcionales + W verificado por ≥2 implementaciones + tercero + **dictado explícito del propietario**. `NOT_EXECUTED` nunca habilita promoción.

Niveles separados: **Diseño aceptable** (§0 regla de recuperación) · **Implementación verificada** (§11 completo) · **Promoción** (tercero + dictado). Diseño no es promoción.

### 10.2 Estados operativos

`TERMINAL_RESULT := COMMIT_TESTIFIED | ABORT_TESTIFIED`. `G ∈ { NOT_DEFINED, ADMITTED, BLOCKED, NOT_DETERMINED, ROLLBACK_DETECTED, HUMAN_CLOSED }`. Ésta es exactamente la enumeración de §1; nunca existe `PASS`.

### 10.3 Revocación

D-7 pendiente; ausente mecanismo ⇒ promoción prohibida.

## 11. PRUEBAS DISCRIMINANTES (formato canónico)

Cada caso declara: `precondiciones — input — pasos — punto de inyección — recuperación — oráculo — negaciones — criterio de aceptación`. Todas `NOT_EXECUTED`. Ningún "ok" por convención.

### 11.0 Formato obligatorio

```
TEST_ID
PRECONDITIONS:  estado inicial de A/W/NV/ledger; claves; misión; contexto;
INPUT:          mensaje/operación/scope;
STEPS:          secuencia exacta de operaciones (actor explícito);
INJECTION:      instante exacto de interrupción (estado persistido en ese instante);
RECOVERY:       procedimiento de reinicio y verificación;
ORACLE:         estado de A, W, NV, cadena, prueba y bytes esperados;
NEGATIVE:       qué se PROHIBE (sin duplicidad; sin sello incorrecto; sin reuso);
ACCEPTANCE:     condiciones exactas para "prueba APROBADA";
EVIDENCE:       artefactos requeridos (hash de registro, manifest, sello).
```

### 11.1 T-G-* (composición global, tabla completa)

| ID | Estado | Pasos | Inyección | Oráculo | Acceptance |
|---|---|---|---|---|---|
| T-G-1 | op válida, sin ops | R1 → W RESERVE → A crash pre-R2 → retry → A confirma → EXECUTE solo tras CONFIRMED | A cae antes de INSERT ops | Retry devuelve misma reserva; ops íntegra; no ejecuta sin Confirm; reservation_confirmed=true | prueba ver reservation_index==reserved slot |
| T-G-2 | R1 reservada; A confirma; ops ok | EXECUTE SQL durable; W cae post-pre-proof; reinicio W; status_req | W crash post-COMMIT durable A | status_req: RECOVERABLE; A durable committed; no efecto reejecutado; W testifica una vez | sello único |
| T-G-3 | sello otorgado; restore del ancla | AI snapshot restaurado antes de seal | restore completo | W+V: ROLLBACK_DETECTED; bloqueo scope | seal prior exists; bloqueo activo |
| T-G-4 | externo_idempotent op aceptada; A cae separadamente pre-ops | reintento mismo op_id | A crash entre dispatch y ops insert | proveedor idempotente cuya clave sobrevive con durabilidad garantizada por el proveedor: la misma clave nunca se ejecuta dos veces en un mismo dominio; si la durabilidad o el alcance temporal de la clave no son verificables, NOT_DETERMINED; el recibo debe ser firmado y durable | op_count_effect=1
# REQUIRE recibo firmado del proveedor identificando operation_id + response; sin recibo firmado: NOT_DETERMINED
| T-G-5 | W destruida y recreada | cliente status o op cualquiera | W catastrophic loss | NOT_DETERMINED todo; nunca promo | never PASS |
| T-G-6 | V certifica; FUENTE desmiente | proof invalidada; W revalida | tamper fuente | W rechaza; sin sello; NDET | no seal |
| T-G-7 | durable commit sin V prueba; V disponible | V emite diferida; W sella | red V→W only | W sella una vez; efecto no reejecutado | sello exacto no.; efecto=1 |

### 11.2 T-I2-*

| ID | Precondiciones | Pasos | Inyección | Oráculo | Acceptance |
|---|---|---|---|---|---|
| T-I2-1 | ops_opF02: reservation_confirmed=true, verdict=pending; cuentas[42].saldo=1000; TPM NV=0x10 | EXECUTE: BEGIN; SELECT ... FOR UPDATE WHERE id=42; UPDATE cuentas; UPDATE ops SET verdict='committed'; COMMIT | crash antes del COMMIT; apenas después | rollback; cuentas.saldo=1000; ops.verdict=pending; cualquier efecto: 0 | COMMIT no ocurrió; retry viable; nunca acreditado |
| T-I2-2 | opF02: ops pending; reservas confirmadas; cuentas[42].saldo=1000 | EXECUTE SQL: effect+ops committed por misma txn; W cae antes de testificar; reinicio W | crash post-COMMIT, pre-proof | estado durable: cuentas.saldo=900; ops (opF02).verdict=committed; W sin sello; status_req=>RECOVERABLE | cualquier reejecución: prohibida |
| T-I2-3 | WAL committed durable disponible en FUENTE | reinicio FUENTE+V; V re-lee WAL de tras-resto; rebuild delta; V firma prueba | crash FUENTE | V reconstruye delta.declarado delta.WAL iguales o no | sin prueba o NOT_DETERMINED |
| T-I2-4 | runtime_log: before=100, after=200; tabla real after=150 | V reconstruye WAL real; compara con log | — | delta diff ⇒ proof denegado; cualquier testificación: NONE_DETERMINED | sin sello o NOT_DETERMINED |
| T-I2-5 | DDL disponible: email TEXT NOT NULL en tabla de efecto | reinicio FUENTE | crash A | V proof denegados; efectos excluidos de dominio | NOT_DETERMINED |
| T-I2-6 | LSN declarado (A) ≠ LSN observado (V) | reinicio FUENTE+C API | — | LSM no verificada => proof denegada | NOT_DETERMINED |
| T-I2-7 | synchronous_commit=off en A | commit durable fuera de A | crash de la máquina | prueba no viable (sig_commit=nodurable) | NOT_DETERMINED |

### 11.3 T-I3-*

| ID | Precondiciones | Pasos | Inyección | Oráculo | Acceptance |
|---|---|---|---|---|---|
| T-I3-1 | ops_opF01: pending, confirmed; sesión EXECUTE + sesión ABORT presionan misma fila | concurrencia entre Tx EXECUTE y Tx ABORT; ambas SELECT ... FOR UPDATE | cualquier intercalado | exactamente un terminal; otro observa terminal y aborta; efecto=0|1 | exactamente uno gana |
| T-I3-2 | opF03: ops pending, ambas sesiones envían EXECUTE con mismo op_id | reintentos simultáneos por el mismo op_id | concurrencia | effect aplicado exactamente una vez; op reusada | cualquier duplicado |
| T-I3-3 | ABORT Tx y EXECUTE Tx deadlocking en la fila | ciclo de locks; deadlock detection | deadlock | consulta post-crash durable decide ganador; jamás suposición | ambos completados |
| T-I3-4 | ops pendiente; A arranca Tx y SELECT ... FOR UPDATE; crash entre BEGIN y aplicar el efecto | crash pre-efecto vs crash post-efecto según estado durable | crash entre etapas | (a) nada aplicó ⇒ pending, retry viable; (b) aplicó ⇒ verdict committed/aborted durable, V al-validate; NEVER reejecutar; verificar verdict sin suponer | efecto 0 vs efecto aplicado con sello único |
| T-I3-5 | opF02 committed en A; crash W antes de sello | client restart; W status_req | cualquier | committed es durable; jamás reejecutar; W testifica una vez | cualquier reejecución |
| T-I3-6 | trigger en tabla de efecto AFTER INSERT | ruta no enrolada | cualquier | efecto no con otro camino; NOT_DETERMINED | cualquier efecto adicional |
| T-I3-7 | op pending tras crash | retry | any | op reusable sin efectos duplicados | efectos |
| T-I3-8 | proveedor forgets credential | reuso mismo idempotency key | restore | exactly-once; provider resends same receipt | duplicado |

### 11.4 T-I4-*

| ID | Precondiciones | Pasos | Inyección | Oráculo | Acceptance |
|---|---|---|---|---|---|
| T-I4-1 | marker persistido; NV incrementado | crash antes de ENTRY persistente | crash | tras reinicio: NV contradictorio; GAP para slot consumido; ops reservadas en ese slot=NOT_DETERMINED | cualquier entry inventada |
| T-I4-2 | snapshot restaurado con NV inferior | restore | — | NV detectado > ledger; ROLLBACK_DETECTED; bloqueo | cualquier sello automático |
| T-I4-3 | NV > last persisted; crash tras incrementar NV pero antes de escribir ENTRY | reinicio W | crash | GAP para slot consumido; ops reservadas=NOT_DETERMINED | cualquier entry inventada |
| T-I4-4 | checkpoint válido: NV==last_index+1 | cualquier cambio en NV coincidiendo con checkpoint | crash | match → CONTINUE | any flag mismatch → ROLLBACK |
| T-I4-5 | TPM2_NV_Certify con firma inválida | firma no verifica contra AK | any failure | rechazo estricto; sin sello | sello |
| T-I4-6 | challenge repetido | cliente reenvía desafío idéntico | replay | rechazo inmediato (no replay) | cualquier aceptación |
| T-I4-7 | 2 NV increments sin Entrys; ambos consumidos | análisis | — | 2 GAP entries; ops en esos slots=NOT_DETERMINED | cualquier entry inventada |
| T-I4-8 | W destruido totalmente | catastrophic restore | catastrophic | NOT_DETERMINED global; ningún sello posible | cualquier sello |

### 11.5 T-AB-*

| ID | Precondiciones | Pasos | Oráculo/Acceptance |
|---|---|---|---|
| T-AB-1 | ops pendiente; EXECUTE iniciada; luego ABORT solicitado | concurrencia: ABORT Tx ganador o EXECUTE Tx gana | uno gana; effects=0/1 según ganador |
| T-AB-2 | ABORT en curso | crash durante ABORT | durable verdict=aborted; sin efectos |
| T-AB-3 | ABORT durable en A; W sin sello | crash antes de testificar | NOT_DETERMINED sello W |
| T-AB-4 | efecto external, proveedor sin idempotencia durable | recibo NO terminal durable | NOT_DETERMINED forever; no sello |
| T-AB-5 | ABORT sellada antes de restore | snapshot restauración | ROLLBACK_DETECTED; scope bloqueado |

### 11.6 T-MSG-*

| ID | Precondiciones | Pasos | Inyección | Oráculo | Negative | Acceptance |
|---|---|---|---|---|---|---|
| T-MSG-1 | proof ready emit msg v1; W-no ack; V crash previo | V entrega a W-antes de commit; W entrega msg then V dies | crash entre envío W y ACK V | re-entrega: W procesa una vez aunque V haga re-delivery tras crash | efectos duplicados | exactamente 1 sello W |
| T-MSG-2 | W marker aún no NV; NV sigue subj in_house; crash W antes de bump | W recibe proof msg; crash entre recepción y NV_increment | crash en W | NV_desa math match con marker esperado; bump una vez; ENTRY una vez | consumo NV duplicado | entry escrita exactamente una vez |
| T-MSG-3 | marker con NV number 6 consumido; ENTRY aún no escrito; crash | W ejecuta NV; crash antes de escribir ENTRY | crash en W | NV value now 6; tras crash recovery: marker NV=6; chain matches; ENTRY escrita exactamente una vez | ENTRY escrita dos veces | entry exactamente una |
| T-MSG-4 | W sellado; cliente nunca recibió ack; client crash antes | cliente reconectando busca status_req | crash de cliente | cliente consulta W; W devuelve stored state (committed) exactamente igual a antes; nada cambia | efectos duplicados | cliente recibe mismo estado stored; no reejecuta |
| T-MSG-5 | mismo proof retransmitido (retry manual cliente) | msg_id replicado recibido por W | repeat delivery | W detecta msg_id duplicado con los mismos bytes; no reescrito; efecto consta una vez | cualquier efecto duplicate | entry escrita exactamente una vez |
| T-MSG-6 | V emite proof mientras W en NV_CALL_IN_FLIGHT; V entregable | entrega de V a W; crash V entre stages | crash de V | W recovers marker; V determinista re-deriva proof; W dedupe msg_id en la transición; modelo: at-least-once entrega + dedupe exactamente-once efectividad de sello; no hay atomicidad SQL↔NV, recovery abredos rutas por algoritmo recuperador | menos de exactamente-once | `exactly-once` efectivo por dedupe, nunca at-most-once por accidente |

### 11.7 T-GAP-*

| ID | Precondiciones | Pasos | Inyección | Oráculo | Negative | Acceptance |
|---|---|---|---|---|---|---|
| T-GAP-1 | marker_NV=4 consumed (entries 1..4, NV=4); op bloquea marker_5 NV_{5} consume pero sin ENTRY; crash | ejecución entre slots con aperiodic bump NV (4→6 quedando sin ENTRY 5) | crash entre marker y ENTRY | tras recovery: NV(6)>ledger(4) ⇒ slots 5,6 consumidos; §4 regla gap: 2 GAP entries (slot=5, slot=6), no payload | never un GAP entry con payload | 2 GAP entries exactly; NONE del tipo OPERATION |
| T-GAP-2 | ledger extendido tras gap recovery: entries 1..4, 5..6 gaps, 7 entry válida | auditoría de chain con gaps reconocidos | input resumido | cadena persiste CONTINUE; entries 7+ pointer a gap-entry 6; verification V se omite | silently reorder | chain sigue válida; gaps matizados |
| T-GAP-3 | ops opF07 tenía reservation_index=5 (antes del crash) | op llega RPC execute post crash con reservation_index=5 | después de T-GAP-1 | slot 5 suelto ⇒ reserva no encontrada ⇒ NOT_DETERMINED para opF07; ninguno puede usarlo como nuevo slot | reasignar slot 5 | reserva en slot gap ⇒ NOT_DETERMINED forever |
| T-GAP-4 | marker_saved durable; NV bump comprobado por NV_read immediate value; crash = resignación | tras crash 50 procesos  recover-loop | crash antes de ENTRY | marker_completos con NV value 6; NV match marker ⇒ ENTRY escrita única bajo msg_id marker; al menos 1 sello emitido | ENTRY escrita que borra ya otorgadas | ENTRY escrita exactamente una vez |
| T-GAP-5 | fuente WAL sin slot capaz durante restore (entries nunca confirmadas) | restore desde snapshot de fuente | forward restore | fuente indisponible: V no puede verificar nada ⇒ W NEVER testifica cualquier op nuevo; NOT_DETERMINED global | cualquier sellado | NO sello automático posible |

### 11.8 T-DEP-*

| ID | Precondiciones | Pasos | Oráculo | Negative | Acceptance |
|---|---|---|---|---|---|
| T-DEP-1 | scopeA={tablaA, tablaB}; scopeB={tablaC, tablaD} | ambas operaciones admitidas; sus writes aislados por scope; ninguna obsta a la otra | scopes disjuntos: no overlap (por ejemplo columnas, pks, tablas, noas); ambas admitidas; el fingerprint no cambia entre ellas | cualquier operación «admite solo una» | se admiten ambas |
| T-DEP-2 | scopeB sin evidencia suficiente para probar disjunción | intento | scope desconocido/desconocido ⇒ BLOCKED exactamente | cualquier admitida | ninguna admitida |
| T-DEP-3 | DDL ejecutada entre Admission y Verification: columna alterada en TablaA | cualquier intento posterior | ROLLBACK_DETECTED | admite algo | BLOCKED total en ese scope |

### 11.9 T-GATE-*

| ID | Precondiciones | Pasos | Oráculo | Negative | Acceptance |
|---|---|---|---|---|---|
| T-GATE-1 | ROLLBACK_DETECTED vigente por monitoring externo o audit log | cualquier nueva operación o efecto sobre el scope | BLOCKED_name_TARGET_PROPOSED | anything allowed | nothing allowed en el scope |
| T-GATE-2 | ABORT_TESTIFIED por op precedente | retenidas las transacciones con mismo op_id | ningún efecto puede producirse a partir de la abortada | effect continued | nothing continued |
| T-GATE-3 | W perdió capacidad de verificar continuidad (missing segments) | si cae any protect | NOT_DETERMINED permanente | anything tests | never PASS |

### 11.10 Criterio de promoción (tres niveles, sin contradicciones)

```
DISEÑO ACEPTABLE (documental):   contratos sin contradicciones (§§1–10); enlaces cruzados verificados;
               NOT_EXECUTED explicitado; nunca habilita promoción.
IMPLEMENTACIÓN VERIFICADA:        §11 completo en verde (sello + artefactos; verificación por 2 ejecutores distintos).
PROMOCIÓN:                        lo anterior + tercero + dictado explícito del propietario.
```

## 12. DEFECTOS Y REGISTRO (OPEN·DESIGN_CLOSED·IMPLEMENTED_UNVERIFIED·VERIFIED)

```
OPEN                      contrato abierto o dependencia abierta entre ellos
DESIGN_CLOSED             contrato especificado coherentemente; nada ejecutado
IMPLEMENTED_UNVERIFIED    codificado; sin tests independientes; a evitar
VERIFIED                  ejecutado + independencia pública + terceros
```

| ID | Ref | Estado | Condición de cierre |
|---|---|---|---|
| B-01 | cripto msg/firma replay | OPEN | §3.1+§9.3 normas cerradas (post-auditoría v4.2R) + §11 verde |
| B-02 | CANON identidad esquema | OPEN | §9 completa con bootstrap cerrado + Apéndice B self-contained + embedders independientes coincidiendo |
| B-03 | NV recovery | OPEN | §4.2 exact piecewise branches cerradas + T-GAP/T-MSG verde |
| B-04 | RESERVE huérfana | OPEN | §7.2 R1/R2 determinación completa por caso + T-G-1 verde |
| B-05 | completitud V | OPEN | §5.2 captura completa con prueba formal + §5.7 dominio definido + T-I2 verde |
| B-06 | fingerprint real | OPEN | §8.2 catalog completo + guard de drifteza T-DEP verde |
| B-07 | máquina compuesta | OPEN | §1 completa (incluir vocabularios gap/orphan/fail) + T-GATE verde |
| B-08 | W durabilidad | OPEN | §4 completa + protocolo reconfigurable + T-MSG verde |

**Estado global:** `PARTIAL`. Ningún B está `DESIGN_CLOSED`; nada superior a `OPEN`. Ninguna declaración aquí habilita promoción, D-13, D-14, OP-NEXT-1, crash tests ni publicación. El veredicto global sigue siendo PARTIAL.

## 13. FINALIZACIÓN v4.2R Y PRÓXIMA OPERACIÓN

**Qué demuestra v4.2R:** ninguna cosa ejecutada. La reconstrucción paso §9 y Apéndice B a una gramática no circular, corrigió §2.2 (operation_id ahora por instancia), unificó la notación STRUCT/CANON de §2/§3/§5/§8, cerró la contradición §13/§10 y eliminó la declaración falsa de §12. B-02 permanece `OPEN`; los ocho B-* permanecen `OPEN`. Lo único demostrado es que existe un documento con contratos descritos; nada de ellos está verificado. **Qué no:** ejecución, terceros, promoción, D-13, D-14, OP-NEXT-1.

**Secuencia (dictado entre pasos):**

```
1. Revisión v4.2R por el propietario (gate explícito)
2. D-13 FUENTE (§6 completo) + D-14 V (§5 completo)
3. OP-NEXT-1 sobre Apéndice B (codificador segundo root, sin código compartido)
      3.1 corpus C20 (fijar en Apéndice B en el mismo cambio)
4. Crash injection masivo § 11 completo
5. D-5 inventario fresh + terceros
6. D-7 revocación
7. Tercero (D-11) → decisión de promoción
```

**Verificación de este documento:** `sha256sum docs/ier/IER_GATE_PLAN.md && wc -l`

## Anexo A — Checklist día 0

- [ ] S=(G,P,T,O,E); nadie mezcla; nadie abre estados fuera de §1.1.
- [ ] RESERVE_DURABLE jamás ejecuta sin RESERVED_CONFIRMED (ops.reservation_confirmed=true).
- [ ] V nunca acepta runtime_log solo; captura completa exigida.
- [ ] Scope enrolado: nada fuera; rutas alternativas ⇒ I3 no cerrado.
- [ ] Toda composición CANON-v1; identificators binarios de 32 B (schema_id).
- [ ] W: marker→NV→ENTRY→ACK con exclusión sec; nunca sello sin cadena.
- [ ] GAPs consumidos irrevocablemente.
- [ ] ROLLBACK_DETECTED bloque consultable; fingerprint drift ⇒ bloqueo.
- [ ] Nada ejecutado; promoción jamás por cierre a diseño.
- [ ] log.md se actualiza en cada salto técnico.

## 14. Historial

| Versión | Hash sha256 | Estado |
|---|---|---|
| v3.7R | `2bb6e151…b7cf` | histórica |
| v3.8R | `85fc70a4…b9c5` | histórica |
| v3.9R | `74fceae6…9cc1` | histórica |
| v4.0R | `07f8399d…b7cf` | histórica |
| v4.1R | `1c9827ca…12d3` | histórica |
| v4.2R-delta1 | `26ace3b5…f079d` | sustituida por esta revisión en el mismo ciclo (nunca verificada por propietario) |
| **v4.2R** | en `state/multiproject/log.md` | **vigente** |

### Sustituciones de aquella revisión frente a v4.1R/v4.2R-delta1

| Antes | Sustituida por | Motivo |
|---|---|---|
| SCHEMA textual en flujo STRUCT | schema_id binario de 32 B en STRUCT (§9.0) | B-02 identidad normativa única |
| STRUCT schema_id como bytes declarados | SCHEMA_DEF canónico calculado (§9.0) | B-02 | 
| reservation_hash circular | reservation_core separado de record | B-01 |
| msg_id incompleto | msg_id = SHA256(domain + MSG_BODY_BYTES) | B-01 |
| P con vocabulario terminal | S=(G,P,T,O,E) con TERMINAL_RESULT separado | B-07 |
| W states inconsistentes | W_STAGE explícito con MARKER/CONFIRMED/... | B-03/B-08 |
| NV ambigua exclusiva del marker | expected_counter + exclusión + lectura por rama | B-03/B-08 |
| D-5 solo catálogo ampliado | guard del despliegue + catálogo completo ordenado | B-06 |
| pruebas agrupadas | casos completos reproducibles | B-08/S-09 |
| promoción con NOT_EXECUTED | tres niveles separados (§10/§11) | B/S |

Respaldos: `/tmp/IER_GATE_PLAN_v4.0R_backup.md`, `/tmp/IER_GATE_PLAN_v4.1R_backup.md`, `/tmp/IER_GATE_PLAN_v4.2R-delta1_backup.md`, `/tmp/Escritorio_v4.2R-delta1_backup.md`.

## Apéndice B — Registro v1 (bootstrap-hashed, RECONSTRUIDO)

### B.1 Carácter normativo

\[ schema\_id = SHA256( D_{\text{SCHEMA-ID-v1}} \parallel SCHEMA\_DEF\_BYTES ) \]
\[ D_{\text{SCHEMA-ID-v1}} = b"IER-SCHEMA-ID-v1\x00" \]

`SCHEMA_DEF_BYTES` se obtiene por `BOOTSTRAP_ENCODER` (§9.1). El registro incluye todos los schemas publicados; **cualquier discrepancia entre dos codificadores de este registro invalida el dominio, no se normaliza a posteriori**.

No existe esquema adicional a los listados. El registro no declara "vigentes 25"; son los aquí escritos y no más.

### B.2 Registro

| Schema | schema_id |
|---|---|
| IER-OP-v1 | `a710e4256e283db21b5f9a25c3d08d50935ba2ee47681c5bdec70526bb1f9802` |
| IER-BINDING-v1 | `8a31b7f143c25ddde71f3859ed8318e115562b5cb18a577aff1a75e6e0ec20af` |
| IER-RESERVATION-CORE-v1 | `7da9717de180fe1970e02817c95f762a16fd61cb81c908de8c9ef448f9bf840f` |
| IER-RESERVATION-RECORD-v1 | `eb5c3ffc7e4e0bf387d43531d471b05741e14256770a86e234fb88f1faf5c9cd` |
| IER-RESERVATION-HASH-v1 | `1c5ac85ff2213677f6e2c2594c9ac64b163449c833574932851987b4baca5b33` |
| IER-MSG-ID-v1 | `2758f6ed0be0e828179fec47fa2bf36b13d1fb95d5105036962aaa924ae29ab1` |
| IER-MSG-BODY-v1 | `4cb635e24d8f413ae7fe24b3675b30cecd9a4cae3f396c574b270ccb6404e973` |
| IER-MSG-ENV-v1 | `b829bb549380f4c080d5cf3ad99f4c7e7fc7a11e48b30679fe14693c6496f144` |
| IER-ENTRY-v1 | `e9baf9ff7de075570158cecd168e78dbd56de85c03df8dc9934cf57951bc6739` |
| IER-HEADER-v1 | `d1f32949b86b826a2e02b855b25ff8a45ac7e980f1d0999c85247093beb5ee0c` |
| IER-HEADER-v1-GENESIS | `231365e1b0f8ce531cbf94cc37421156ee430e778268684eca452e7279044ce2` |
| IER-TPMNV-QUALIFY-v1 | `35804862a4307c13aefc3e54fbf1a26be433ae402c11272129db2bf1d0e6adcd` |
| IER-AUTH-SIG-v1 | `3441dbbb329f1eb09b3710c33997f2d0b56df086746dacaaf5131accb552d388` |
| IER-DEP-POLICY-v1 | `f8a5c7088b1349d7df30e7c0d8dff3635fb1904319e13281e0d7c871ca4aa025` |
| IER-EFFECT-DELTA-v1 | `39878d1a9507dd06263866fe15d2917468d41d27e8aea68778889e5c6b345153` |
| IER-EFFECT-PROOF-v1 | `c8d0206d295a9306c31b27cf11e2a27874f428165df758c3adeb54ed356e1c52` |
| IER-DEPLOY-FP-v1 | `5064a7a1133a733471863751504f3b070702e8a464fc405f0d28fbf359ba729c` |
| IER-CATALOG-SNAPSHOT-v1 | `578c8682beeebebe78fb7f7fa9a7c55a268b0ab98eda9d62f947a94e9403680c` |

N = 18 esquemas registrados. Ninguno demás es válido en esta revisión.

### B.3 Descriptores completos

`schema_id` se deriva de `SCHEMA_DEF(schema)`; cada descriptor aquí está codificado según §9.1/§9.2/§9.3 y exige que el decodificar independiente reconstruya idénticamente cada uno antes de verificar cualquier hash. Ningún descriptor puede ser omitido ni normalizado a posteriori.

* **IER-OP-v1** — mission:STRING:req, auth_id_hash:BYTES(32):req, request_hash:BYTES(32):req, nonce:BYTES(16..32):req, purpose:ENUM op_class:req
* **IER-BINDING-v1** — mission:STRING:req, auth_id_hash:BYTES(32):req, request_hash:BYTES(32):req, event_kind:ENUM kind_entry:req, anchor_epoch:INT64:req, reservation_nonce:BYTES(32):req, effect_scope_fp:BYTES(32):req, reservation_hash:BYTES(32):req
* **IER-RESERVATION-CORE-v1** — operation_id:BYTES(32):req, auth_id_hash:BYTES(32):req, nonce:BYTES(16..32):req, event_kind:ENUM kind_entry:req, request_hash:BYTES(32):req, anchor_epoch:INT64:req, effect_scope_fp:BYTES(32):req
* **IER-RESERVATION-RECORD-v1** — reservation_core:STRUCT IER-RESERVATION-CORE-v1:req, reservation_hash:BYTES(32):req, reservation_index:INT64:req
* **IER-RESERVATION-HASH-v1** — reservation:BYTES:req
* **IER-MSG-BODY-v1** — kind:ENUM kind_msg:req, from:ENUM from_to:req, to:ENUM from_to:req, operation_id:BYTES(32):req, anchor_epoch:INT64:req, payload:BYTES:req, issued_at:TIMESTAMP:req, protocol_version:STRING:req, key_id:BYTES(32):req, alg:STRING:req, key_epoch:INT64:req
* **IER-MSG-ID-v1** — msg:BYTES:req
* **IER-MSG-ENV-v1** — msg_id:BYTES(32):req, body:BYTES:req, signature:BYTES(64):req
* **IER-ENTRY-v1** — kind:ENUM kind_entry:req, index:INT64:req, counter_value:INT64:req, event:ENUM kind_entry:req, binding:BYTES(32):req, operation_id:BYTES(32):req, reservation_index:INT64:optional, msg_id:BYTES(32):optional, prev_header:BYTES(32):req
* **IER-HEADER-v1** — prev_header:BYTES(32):req, entry:BYTES:req
* **IER-HEADER-v1-GENESIS** — anchor_epoch:INT64:req
* **IER-TPMNV-QUALIFY-v1** — challenge_random:BYTES(32):req, witness_id:BYTES(32):req, prev_header:BYTES(32):req, slots:ARRAY<INT64>:req, anchor_epoch:INT64:req
* **IER-AUTH-SIG-v1** — label:STRING:req
* **IER-DEP-POLICY-v1** — version:STRING:req, nodes:ARRAY<STRING>:req, edges:ARRAY<BYTES>:req, rules:BYTES:req
* **IER-EFFECT-DELTA-v1** — schema_version:STRING:req, operation:ENUM operation:req, pk:BYTES(CANON(MAP<STRING,typed_value>)):req, before_row:MAP<STRING,typed_value>|NULL:optional, after_row:MAP<STRING,typed_value>:req
* **IER-EFFECT-PROOF-v1** — operation_id:BYTES(32):req, mission:STRING:req, request_hash:BYTES(32):req, binding:BYTES(32):req, reservation_hash:BYTES(32):req, effect_hash:BYTES(32):req, effect_delta:BYTES:req, transaction_id:STRING:req, commit_lsn:INT64:req, timeline_id:INT64:req, anchor_epoch:INT64:req, reservation_index:INT64:req, source_id:BYTES(32):req, effect_scope:STRUCT IER-DEPLOY-FP-v1:req, effect_scope_fp:BYTES(32):req
* **IER-DEPLOY-FP-v1** — catalog_hash:BYTES(32):req, policy_hash:BYTES(32):req, deployment_id:STRING:req
* **IER-CATALOG-SNAPSHOT-v1** — deployment_id:STRING:req, database_identity:STRING:req, objects:ARRAY<BYTES>:req, dependencies:ARRAY<BYTES>:req, effective_privileges:ARRAY<BYTES>:req, extensions:ARRAY<BYTES>:req, relrowsecurity_per_table:BYTES:req

### B.4 Vectores de verificación con hashes calculados

```
V1  INT64 1                      bytes 070000000000000001
                                 sha256 cb46e87cf21bf247a88eba01e68fef30198cf07743192f233d75b74e0137d46c
V2  STRING "a"                   bytes 080000000161
                                 sha256 8c14a1d208c12ee58d4af154f49552c79311840b492653213a88bc2db1378963
V3  NULL                         bytes 01
                                 sha256 4bf5122f344554c53bde2ebb8cd2b7e3d1600ad631c385a5d7cce23c7785459a
V4  MAP{"s":7}                   bytes 0e00000001080000000173070000000000000007
                                 sha256 75cc9ae44a335eaf55409b0df1829352d3f22d0241ed57eabe567d02dbb4babb
V5  BOOL 1                       bytes 0201
                                 sha256 25dfd29c09617dcc9852281c030e5b3037a338a4712a42a21c907f259c6412a0
V6  IER-OP-v1  completo
                                 sha256 b58a51ca082ec5e91b49fb7b6f05315894bf0dcb51d3dd747a058b0480c5c17f
                                 bytes 0fa710e4256e283db21b5f9a25c3d08d50935ba2ee47681c5bdec70526bb1f9802011f08000000016d
                                        0900000020000102030405060708090a0b0c0d0e0f101112131415161718191a1b
                                        1c1d1e1f0900000020202122232425262728292a2b2c2d2e2f303132333435363738
                                        393a3b3c3d3e3f0900000010101112131415161718191a1b1c1d1e1f0a00000004
                                        74657374
V7  DECIMAL 123.45               bytes 0b0200000000000000000000000000003039
                                 sha256 850a9429a98feeda164e13327d02878e2258df57506004409a4de0f9dc06692f
V8  INT64 max                    bytes 077fffffffffffffff
                                 sha256 5ac85332e98af5ba465bd22693723ebac5e0e5f8126a47c074ea3bf67e61ea8b
V9  INT64 min                    bytes 078000000000000000
                                 sha256 7d92c4d577eab67d6898f53d6a65db7c8bc885cc698cdd8bd32536e92c480acb
V10 ARRAY vacío                bytes 0d00000000
                                 sha256 3c8f1b104592e3ebb2b2602b3979a27e77f586fb4c655369fa4eccb6d545a0f8
V11 DECIMAL cero scale=0      bytes 0b0000000000000000000000000000000000
                                 sha256 403aad34495f625943e5df2b1a29750817c7c214b0153a29b1613a0515e9e574
V12 STRING vacío               bytes 0800000000
                                 sha256 18b1b592a44f7fbe33dab6a3d22857eea5118da14d6fabbc59b0681dbf1286f1
```

### B.5 Estado epistémico

`NOT_EXECUTED`. Los 18 `schema_id` y V1..V12 fueron calculados por un único codificador de referencia interna (herramienta de esta sesión), cuyo alcance es demostración de coherencia interna, no verificación independiente. **Ningún `schema_id` ni vector ha sido verificado por una segunda raíz.** Ningún contenido de Apéndice B constituye afirmación de implementación, promoción, o validación.

---

```
Versión vigente:        4.2R
Ruta canónica:          docs/ier/IER_GATE_PLAN.md
Estado global:          PARTIAL
Implementation:         NOT_EXECUTED
Crash injection:        NOT_EXECUTED
Third party:            NOT_EXECUTED / REQUIRED
Promotion:              NOT_READY
```

