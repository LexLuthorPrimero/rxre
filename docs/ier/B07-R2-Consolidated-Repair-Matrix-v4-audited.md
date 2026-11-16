# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 4 (POST-AUDITORÍA DE v3)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** `docs/ier/B07-R2-Repair-Specification.md` v2.r2 — SHA-256 `9c8a0aba5cf6770b12561b7734e0630c41ae44b268ce5f9ecdcf216f9c57c39e` — **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1 (`e165aced…`), v2 (`103feeb2…`), v3 (`e1c046eb…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. **r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.**

## Registro de revisiones

| Versión | SHA-256 | Disposición |
|---|---|---|
| v1 | `e165aced…` | NO RATIFICABLE |
| v2 | `103feeb2…` | NO RATIFICABLE |
| v3 | `e1c046eb…` | NO RATIFICABLE; dictamen independiente sobre 104 filas (ninguna ratificada nueva); CR-01…CR-10 |
| v4 (este documento) | hash fuera del archivo (`state/multiproject/log.md`) | Aplica **P0** (C-01, C-04, C-02, C-08/C-18, C-03/C-13) y **P1/P2** (C-09, C-15, C-05, C-07, C-12, propagación, N-01…N-10 incorporados). **Todas las 104 filas permanecen REPAIR_REQUIRED o BLOCKED**; ninguna se declara aceptada por construcción. |

---

## 0. Leyenda

`Definición → Persistencia → Transición → Invariante → Contraejemplo → Prueba`.
Estados: `REPAIRED-DOCUMENTAL` (diseño correcto; no ejecutado; falta perito) · `REPAIRED-CONDICIONADO` (depende de límite/decisión abierta) · `BLOCKED` · `NOT_APPLICABLE`.
**Regla absoluta**: nada sale de este documento marcado `REPAIRED-DOCUMENTAL` sin revisión independiente del propietario.

---

## 1. Inventario (104 unidades — aritmética verificada)

`27+19+9+10 = 65`; `65+10 = 75` (heredadas de v1) · `75+19 = 94` (v2) · `94+10 = 104` (v3, porta C-01…C-19 + N-01…N-10).

---

## 2. Especificaciones P0 (criterios de aceptación del dictamen v3)

### §P0-1 — Estados de operación e insurrección del claim (C-01)

```
Estados de operación (columna od):
  NOT_EVALUATED  := op nacida; head puede o no publicarse; ninguna solicitud nueva despacha efectos.
  ADMITTED       := T-ADM admitió; head publicado necesariamente.
  BLOCKED        := T-ADM rechazó; head publicado necesariamente.
  NOT_DETERMINED := evidencia insuficiente; head publicado necesariamente.

Reglas:
  R-CREATE: INSERT sólo con od='NOT_EVALUATED' ∧ current_attempt_id=NULL (head ausente).
  R-CLAIM : INSERT de attempt; en la MISMA tx SET_HEAD: current_attempt_id := new_attempt_id, current_attempt_generation := 1 (u actual+1).
  R-ADM   : T-ADM resuelve sólo con head publicado; escribe od ∈ {ADMITTED, BLOCKED, NOT_DETERMINED} (misma tx).
  CHECK   := (od = 'NOT_EVALUATED') OR (current_attempt_id IS NOT NULL)
             ≡ od ≠ NOT_EVALUATED ⇒ head publicado.
  No se exige NOT_EVALUATED ⇒ head NULL (el head lo publica el claim con od aún NOT_EVALUATED):
explicito INVARIANT_CREATE: NOT_EVALUATED ∧ head NULL  → es el estado inicial válido;
                          NOT_EVALUATED ∧ head PUBLISHED → válido (post-claim pre-ADM);
                          od ≠ NOT_EVALUATED ∧ head NULL → rechazado;
                          od ≠ NOT_EVALUATED ⇒ head publicado.
  Prueba discriminante: (i) INSERT op nacida ⇒ NOT_EVALUATED/NULL aceptado; (ii) INSERT op od≠NOT_EVALUATED head NULL ⇒ rechazado por CHECK; (iii) claim concurrente 1 publica, otro aborta; (iv) T-ADM sobre head publicado admite transición NOT_EVALUATED→ADMITTED/BLOCKED/NOT_DETERMINED.
```

### §P0-2 — Codificación binaria canónica y firma de decisión (C-04/C-02 criptográfico)

```
Atomic ASCII(s) SIN NUL adicional; cada tag literal INCLUYE el byte NUL explícito.
Leyenda de literales utilizados:
  'IER-effect-cap-v1\0'   → 18 bytes (17 ASCII + NUL)
  'IER-consume-v2\0'     → 15 bytes (14 ASCII + NUL)
  'IER-key-v1\0'         → 12 bytes (11 ASCII + NUL)
  'IER-effect-idem-v2\0'  → 19 bytes (18 ASCII + NUL)

ENC(b)  := NU64(len(b)) ‖ b           // NU64 = UINT64 little-endian; len en BYTES
NU8(x)  := 1 octeto exacto (0..255)
NU16(x) := 2 octetos LE
NU64(x) := 8 octetos LE

DECISION_PAYLOAD (kind ∈ {1=REOPEN, 2=T13, 3=T-CLOSE}; reason ∈ {1=ROLLBACK_RESOLVED, 2=RECONCILE_RESOLVED, 3=HUMAN-CLOSURE}):

  Tag('IER-consume-v2\0')              // 15 B
  ‖ NU8(kind)                          // 1
  ‖ ENC(scope_id)                      // 40  (8+32)
  ‖ NU64(scope_epoch)                  // 8
  ‖ NU64(opened_epoch)                 // 8
  ‖ NU8(reason)                         // 1
  ‖ ENC(evidence_hash)                  // 40
  ‖ ENC(decision_id)                    // 40
  ‖ ENC(key_id)                         // 40
                                        // = 193 bytes (verificado bit a bit en §11)

signature := Ed25519(bytes(DECISION_PAYLOAD))
key_id    := SHA-256(TAG('IER-key-v1\0') ‖ ENC(pk_raw))
decision_id := 32 B ALEATORIOS generados por W (CSPRNG); UNIQUE en consumed_decision.

Matriz kind↔reason (bit exactas; cualquier otra combinación ⇒ RECHAZO):
  kind=1 REOPEN → reason ∈ {1, 2}      (motivo de degradación almacenado)
  kind=2 T13    → reason = 3           (HUMAN-CLOSURE)
  kind=3 T-CLOSE→ reason = 3           (HUMAN-CLOSURE)

Reglas de verificación (bit exactas):
  1. decodificar payload rechaza desviaciones de longitud y tipo;
  2. key_id reconstruido de pk_raw == key_id declarado;
  3. kind y reason según matriz;
  4. kind=1 ⇒ opened_epoch = scope_epoch+1;
  5. reason correlaciona 1↔{rollback}, 2↔{reconcile} con el scope_event invocado;
  6. evidence_hash == scope_event.evidence_hash;
  7. decision_id no consumido (INSERT UNIQUE);
  8. mensaje contrario al payload codificado ⇒ rechazo íntegro.

VECTOR DE PRUEBA (clave determinista de prueba; NO USAR EN PRODUCCIÓN):
  secret_raw   = 000102…1f   (bytes(range(32)) fijos)
  pk_raw       = 03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8
  kid          = 030c0c8ca67886ad73c59776afa6c9ee85468f6b6db518965701b88b0f737a3b
  payload      = 4945522d636f6e73756d652d7632000120000000000000001111111111111111111111111111111111111111111111111111111111111111070000000000000008000000000000000120000000000000002222222222222222222222222222222222222222222222222222222222222222200000000000000033333333333333333333333333333333333333333333333333333333333333332000000000000000030c0c8ca67886ad73c59776afa6c9ee85468f6b6db518965701b88b0f737a3b
  payload_sha  = 43359a0c2d387cf02d9bd820642cfb398d6b9db2a20d527a3891723b519bd20e
  length       = 193 bytes (== 15+1+40+8+8+1+40+40+40)
  signature    = e9263e0e595ab934855578afb875cb99fd06027eea382f47b093eafdcb351b86d857f86f1e8901435d1ce1c7bb491f7949b16c74b7bb22c344defd7c53681609
Vector negativo: alterar 1 byte del payload ⇒ verificación falla (signature no válida).
```

### §P0-3 — Frontera de ejecución y fencing con revocación linealizable (C-02/C-08/C-18)

```
Teorema de la frontera: no existe un punto de linealización común entre PostgreSQL y un proveedor externo
si el proveedor no participa como autoridad de fence. Se declara honestamente:

PROVEEDOR CLASE-S (fence-capable): el proveedor mantiene por scope un contador `provider.min_fence`
  monótono. Atómicamente, para cada mensaje recibido:
    (verify sig ∧ verify expiry ∧ verify payload_hash ∧ verify idempotency_key)
    ∧ CAS provider.min_fence := max(provider.min_fence, cap.fence)
    y compara cap.fence ≥ provider.min_fence ⇒ acepta; < ⇒ rechaza.
  La revocación (T-SUSPEND/T13/T-CLOSE) ordena al proveedor aplicar el bump de scope
  antes de confirmar la suspensión (atómica en la frontera del proveedor).
  ⇒ Todo efecto externo ejecuta en orden o se rechaza: Linearizable respecto al bump.

PROVEEDOR CLASE-T (non-fence): no puede revocarse en sí; el sink es la frontera; el efecto materializado
  tras suspensión ⇒ outcome UNKNOWN; cierre prohibido; compensación obligatoria; jamás se declara
  inexistente por el solo hecho de suspender la operación.

Serialización interna (necesaria, no suficiente):
  T-SUSPEND:      SELECT … FOR UPDATE (scope); UPDATE scope+fencing bump; UPDATE operation v=SUSPENDED; COMMIT.
  Sink:           SELECT … FOR UPDATE (scope); verify(op/epoch/attempt/fence); dispatch/COMMIT.
  Despacho tras suspensión: revalidación obligatoria tras adquirir el lock: si v≠OPEN o fence cambio ⇒ rechazo.

Call in flight en el instante del bump:
  Clase-S ⇒ provider rechaza o retrasa (cap.fence < provider.min_fence) ⇒ no efecto.
  Clase-T ⇒ efecto posible con UNKNOWN; nunca cierre; reconciliación SC-002; compensación saga.

Exhaustión de fence: next_fence == 2^64-1 ⇒ no se emite capability alguna; T-SUSPEND global + escalación.
El fence-bump ocurre siempre en la misma tx que T-SUSPEND/T13/T-CLOSE ⇒ ninguna capability emitida antes permanece vigente después.
```


### §P0-4 — Terminalidad de efectos y cierre (C-03/C-13)

```
Tabla verdad ES × ResultadoConocido × Terminal(aceptable):

  state                        | ResultadoConocido (SÍ/NO) | Terminal (aceptable p/ cierre) | Estado terminal según O
  INTENT_DURABLE               | NO                          | NO                            | — (no despachado)
  DISPATCHED                   | UNKNOWN                     | NO                            | —
  ACKNOWLEDGED                 | UNKNOWN                     | NO                            | —
  OBSERVED                     | NO                          | NO (necesita veredicto SC-002)| —
  VERIFIED (ES-005)            | SÍ                          | SÍ                            | COMMITTED
  COMPENSATED (ES-006)         | SÍ                          | SÍ                            | NOT_EXECUTED (efecto anulado)
  UNKNOWN (ES-007)             | NO                          | NO, bloquea todo cierre       | UNKNOWN

Reglas de cierre (T-CLOSE/T13):
  ∀ e ∈ manifest: e ∈ {ES-005 VERIFIED, ES-006 COMPENSATED} ∨ e nunca fue despachado;
  ningún efecto puede quedar en ES-007;
  un efecto despachado sólo cierra tras veredicto SC-002 (saga → ES-006 o verificación → ES-005);
  UNA operación SIN efectos dispatchables puede cerrar si y sólo si p ∈ {ABORT_DURABLE} ∧ todos los efectos no despachados.

Compensación aplicable a cualquier despacho: la política ANY acepta ≥1 VERIFIED;
  ALL requiere todos VERIFIED; NONE prohíbe despacho y exige ABORT_DURABLE.
Verificación final: LegalState(op) ∧ política ⇒ p permite T ⇒ ESo TESTIFICATION.
```


## 3. Especificaciones P1 (persistencia, criptografía de escalado, censo)

### §P1-1 — Anclaje externo de la cadena (C-09)

```
Ancla := actor independiente con identidad propia (Ed25519 propia) que firma un compromiso diario:
  anchor := { root_hash_bind: H(chain_head), seq: N, timestamp: T, anchor_sig }
  firmando chain head.
Cadena local: INSERT-only en tablas selladas con hash-chain per row:
  row_hash = H(row_prev_hash ‖ row_fields)
  ancla firma periódicamente chain_head.
Lectura con verificación: antes de toda consulta crítica (sink, dispatch, cierre), la cadena se
verifica hasta el último ancla conocido; si chain_head ≢ anchor.root ⇒ fail-closed; operación prohibida.
Rotación/suspensión del ancla ⇒ congelar escrituras críticas hasta nuevo ancla verificado.
Coste: 1 anclaje por N filas o T tiempo; escritura crítica completa por tx no cambia.
Garantía: sustitución completa de la cadena es detectable desde el ancla; clave duplicado en un
  sólo punto de anclaje no permite reencadenar.
```

### §P1-2 — Manifiesto embebido en operación (C-15)

```
Decisión de diseño: eliminar la tabla `manifest` independiente. El manifiesto vive como columna
se sellada `payload` en `operation`: operation.manifest_bytea / operation.manifest_hash.
Cero FKs cruzadas; cero casos de orden de creación; verificación local trivial:
  TRIGGER operation_manifest_check (BEFORE INSERT OR UPDATE OF manifest_* ON operation):
    NEW.manifest_hash == compute(ManifestHash, decode(NEW.manifest_bytea))  — recompute self-consistency
  Si no cumple ⇒ RAISE EXCEPTION ⇒ rollback.
Efectos: ninguna escritura de manifiesto fuera; manifiesto inmutable por fila (append-only por autorización: nadie UPDATE
manifest_* salvo flujo de cierre auditado).
```

### §P1-3 — Censo UINT64 completo con cotas (C-05)

| Columna | Tipo | CHECK |
|---|---|---|
| scope.scope_epoch | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| scope.minimum_valid_fence | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| scope.next_fence | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| operation.scope_epoch | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| operation.policy_version | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| operation.operation_kind | smallint | `0..255` |
| operation.current_attempt_generation | smallint | `1..255` |
| attempt.attempt_generation | smallint | `1..255` |
| attempt.claim_generation | numeric(20,0) | `1 ≤ v ≤ 18446744073709551615` |
| attempt.fencing_token | numeric(20,0) | `0 ≤ v ≤ 18446744073709551615` |
| operation.manifest_bytea hash | smallint | `1..2` (policy tag) |
Wire uint64: cualquier valor fuera del dominio ⇒ driver/serialización rechaza, no trunca. Use bigint sólo con migración de dominio explícita.

### §P1-4 — Propagación formal de bloqueos (C-07)

```
G=(V,E) con V = universo canónico finito; E = {(u,v): v depende de u}.
B₀ = bloqueados primarios (AUD-xxx REPAIRED no ratificado …): conjunto canónico de la §8.
D(v) = deps directas de v.
B* = LFP(Φ) con Φ(X)=X ∪ {v | D(v) ∩ X ≠ ∅}.
Teorema: |B₀|≤|V| finito; Φ monotónica; Xᵢ⊆Xᵢ₊₁; ⊇ detiene; Terminación en ≤|V| iteraciones.
Algoritmo en pseudocódigo:
  B := B0; changed := true
  while changed:
    changed := false
    for v in V:
      if v ∉ B and D(v) ∩ B != ∅:
        B := B ∪ {v}; changed := true
Precisión: v independiente mantiene estado propio; ningún propagado adicional.
Final: B* contiene exactamente los dependientes transitivos de B₀.
```

### §P1-5 — Orden determinista de verificación (C-12)

```
Orden total por (decided_at, decision_id) ((nota: el orden no decide contradicciones — lo decide el predicado).
Contradiction detection NO usa orden: se declara por evaluación semántica:
  CONFLICT(e) := ∃ r₁,r₂ veredictos distintos con clase incompatible (VERIFIED vs REJECTED) o cualquiera CONTRADICTION.
RR preservado append-only; hechos históricos nunca se reescriben; sólo se acumulan.
```

## 4. Propagación total (regla única) y estados por fila — sin cierre sin ratificación

La regla de §P1-4 es universal: cualquier fila dependiente de fila `BLOCKED` se propaga explícitamente en el conjunto §8. Ninguna fila «reparada» en esta revisión escapa a su dependencia; no se abre ninguna fila nueva hacia `REPAIRED-DOCUMENTAL` salvo que el documento la liste como demostrable con evidencia reproducible.

Esta revisión **no declara ninguna fila ratificada**. Toda admisión de corrección por el diseñador exige evidencia de prueba (A-xx executed) o cotejo del DDL; nothing here is testimonial.


## 5. Matriz H-01…H-27 (estados v4; nada se declara reparado ni ratificado)

| H | Defecto | Definición/Diseño (v4) | Contraejemplo de v3 (rechazado) | Dictamen v4 |
|---|---|---|---|---|
| H-01 | Hash sin vectores | §P0-2 define encoding+payload byte exacto+vector reproducible | payload distinto por NUL duplicado | REPAIR_REQUIRED (cotejo pendiente de vector reproducible por tercero) |
| H-02 | ordinal ambiguo | global denso 0..n−1 (*) | ordinal local duplicado produce manifiestos distintos | REPAIR_REQUIRED (falta segundo cálculo reproducido) |
| H-03 | fuente de verdad | §P1-1 anclaje externo+write-only roles | sustitución completa de la cadena pasa verificación local | BLOCKED (depende de D-R2R2-1/PKI) |
| H-04 | head pointer sin CAS | §P0-1 predicado completo SET_HEAD_ATTEMPT | dos claims ⇒ uno publica, otro aborta | REPAIR_REQUIRED (cotejo DDL pendiente) |
| H-05 | fencing vs suspensión | §P0-3 frontera fence-capable/provider_domain; ordinales fence | general de las fases A/B/C | BLOCKED |
| H-06 | REOPEN_EVIDENCE | §P0-2 preimagen canónica completa+tag v2 | firma válida de reapertura falsa si epoch alterado | BLOCKED |
| H-07 | scope_event sin esquema | UNIQUE(scope_id, scope_epoch, kind, evidence_hash) + FK evidencia; evento+tx única | evento huérfano por crash mid-tx | REPAIR_REQUIRED (cotejo DDL pendiente) |
| H-08 | FK compuesta | attempt(scope_id, op_id)→operation(scope_id, operation_id) | intento con scope ajeno aceptado | REPAIR_REQUIRED |
| H-09 | binding op↔intento | binding por intento; eliminación binding op; cabeza componencial | reintento con cabeza antigua inyectado | REPAIR_REQUIRED |
| H-10 | idempotencia epochs | `(scope_id, scope_epoch, kind, request_id)` único | REOPEN+misma req ⇒ nueva op | REPAIR_REQUIRED |
| H-11 | fencing sin protocolo | depende de H-05/P0-3/B-04 | grant con fence previo rechazado | BLOCKED |
| H-12 | decision_id sin consumo | `consumed_decision` UNIQUE + protocolo por transición (§6-B/C-11-draft v3) | doble reapertura gana doble | REPAIR_REQUIRED (diseño exacto pendiente) |
| H-13 | T-REOPEN | §P0-2 verificación + epoch+1/fence completo | crash entre bump y evidencia ⇒ rollback | BLOCKED |
| H-14 | V=CLOSED sin transición | §P0-4 cierre con ES-007 bloqueo duro | op con ES-007 ⇒ cierre prohibido | BLOCKED |
| H-15 | máquinas incompletas | tablas SI/TRs/ESs/OD/P/V/O/T/ESo/ES con op↔efecto↔política (§P0-4 + referencia §6-B/C-13 v3) | crash RECOVERABLE sin ruta | BLOCKED |
| H-16 | INV-13 sin derivación | prueba formal escrita (texto del artefacto) | «consecuencia directa» no aceptada | REPAIRED-CONDICIONADO (prueba pendiente de cotejo por diseñador) |
| H-17 | reconciliación | §P1-5 total order (decided_at, decision_id); clase veredicto contradicción | doble veredicto silencioso ⇒ contradicción | BLOCKED |
| H-18 | ESo=REJECTED | §P0-4 saga=ES-006 ∨ FAILED_CONSUMED; sin empuje posible | REJECTED sin salida | BLOCKED |
| H-19 | tipos generación | §P1-3 census+range CHECK | 255 vs 2^64-1 drivers divergentes | REPAIR_REQUIRED |
| H-20 | barrera permisiva | default-deny completo (§P1-4 propagation LFP) | símbolo inocente con dep §1 | REPAIR_REQUIRED |
| H-21 | census+rechazo | idéntico con AUD-015 | token no clasificado aceptado | BLOCKED |
| H-22 | cardinalidad | dominios justificados R1 fila a fila; LEGAL/REACHABLE desconocidos | 518400 declarado legal | REPAIR_REQUIRED (evidencia pendiente) |
| H-23 | coverage sinks | A-03-v2 evidencia ejecutable requerida | sink clandestino | BLOCKED |
| H-24 | TCB | ACL/PKI+Ed25519 (D-R2R2-1) | adapter externo sin sink | BLOCKED |
| H-25 | LP solicitud vs suspensión | §P0-3 LP=commit dual+sincr límite clase | mensaje perdido tras suspensión | BLOCKED |
| H-26 | políticas | §P0-4 policy gates+empty rules+INV-18 | ANY-vacío test case obligatorio (reccur); ALL-empty ⇒ ABORT_DURABLE por defecto | BLOCKED |
| H-27 | A6 propagación | §P1-4 LFP pseudocode+terminación | símbolo permitido pese a deps §1 | REPAIR_REQUIRED (revisión pendiente) |


## 6. Matriz R2A-AUD-001…019 (dictamen v4)

| AUD | Descripción | Estado v4 |
|---|---|---|
| AUD-001 | SinkAccept fields | REPAIR_REQUIRED (cotejo pendiente) |
| AUD-002 | Binding duplicado | REPAIR_REQUIRED (cotejo DDL) |
| AUD-003 | INV-06 redundante | REPAIR_REQUIRED (cobertura INV-09 por demostrar) |
| AUD-004 | INV-07 elipsis | REPAIR_REQUIRED (INV-07a/b/c por reproducir) |
| AUD-005 | `≈ 8640` | ACEPTADA (aritmética) |
| AUD-006 | §2.L contradice §2.A | REPAIR_REQUIRED (cotejo ambos) |
| AUD-007 | epoch | BLOCKED |
| AUD-008 | DDL binding | REPAIR_REQUIRED (cotejo) |
| AUD-009 | FG-001→ES-007 | REPAIR_REQUIRED (SC-001 suficiencia) |
| AUD-010 | índice | REPAIR_REQUIRED |
| AUD-011 | fencing | BLOCKED |
| AUD-012 | origen/sink | REPAIR_REQUIRED (contrato completo de frontera) |
| AUD-013 | T13 | BLOCKED |
| AUD-014 | UNKNOWN | BLOCKED |
| AUD-015 | R1.3 vs canon | BLOCKED |
| AUD-016 | INV-02 epochs | REPAIR_REQUIRED (compatibilidad) |
| AUD-017 | attempts | REPAIR_REQUIRED |
| AUD-018 | políticas | BLOCKED |
| AUD-019 | P/T/ESo/O | BLOCKED |

## 7. Notas residuales RES-1…9

| RES | Estado |
|---|---|
| RES-1 | ACEPTADA |
| RES-2 | REPAIR_REQUIRED |
| RES-3 | ACEPTADA |
| RES-4 | REPAIR_REQUIRED |
| RES-5 | REPAIR_REQUIRED |
| RES-6 | BLOCKED |
| RES-7 | REPAIR_REQUIRED |
| RES-8 | REPAIR_REQUIRED |
| RES-9 | REPAIR_REQUIRED (INV-13 §2 H16 prueba pendiente de cotejo) |

## 8. Microdefectos M-01…M-10

| M | Estado |
|---|---|
| M-01 | BLOCKED |
| M-02 | REPAIR_REQUIRED (decided_at timestamptz; orden §P1-5) |
| M-03 | REPAIR_REQUIRED (census §P1-3; claim_generation UINT64) |
| M-04 | BLOCKED |
| M-05 | BLOCKED (BND universe por §P1-4) |
| M-06 | ACEPTADA |
| M-07 | REPAIR_REQUIRED (cotejo referencias cripto) |
| M-08 | REPAIR_REQUIRED (census políticas) |
| M-09 | REPAIR_REQUIRED (unificación exacta) |
| M-10 | BLOCKED |

## 9. Hallazgos nuevos del auditor (A-01…A-04, B, C, D, E, F, G)

| ID | Estado |
|---|---|
| A-01 | REPAIR_REQUIRED (DDL verificado por duplicado) |
| A-02 | REPAIR_REQUIRED (census completo §P1-3) |
| A-03 | BLOCKED (DDL validación pendiente C-01) |
| A-04 | BLOCKED (§P1-2 trigger a validar en DDL fluido) |
| B | BLOCKED (frontera provider) |
| C | BLOCKED (resultado desconocido) |
| D | BLOCKED (T13) |
| E | BLOCKED (CR-02 vector completo) |
| F | BLOCKED |
| G | ACEPTADA LIMITADA |

## 10. C-01…C-19

| C | Estado |
|---|---|
| C-01 | REPAIR_REQUIRED (§P0-1 por demostrar en DDL real) |
| C-02 | BLOCKED (frontera provider) |
| C-03 | BLOCKED (outcome desconocido) |
| C-04 | BLOCKED (CR-02 vectores+kind matrix) |
| C-05 | REPAIR_REQUIRED (census completo §P1-3) |
| C-06 | REPAIR_REQUIRED (fence entero) |
| C-07 | BLOCKED (universo no ratificado) |
| C-08 | BLOCKED (LP único común pre/post-efecto) |
| C-09 | BLOCKED (anclaje externo completo) |
| C-10 | REPAIR_REQUIRED (CAS predicado completo) |
| C-11 | REPAIR_REQUIRED (protocolo exhaustivo) |
| C-12 | REPAIR_REQUIRED (orden §P1-5; verificación) |
| C-13 | BLOCKED |
| C-14 | BLOCKED (evidencia ejecutable) |
| C-15 | BLOCKED (§P1-2 validación) |
| C-16 | REPAIR_REQUIRED (EFFECT_KEY sin attempt_id) |
| C-17 | BLOCKED |
| C-18 | BLOCKED |
| C-19 | BLOCKED |

## 11. N-01…N-10

| N | Estado |
|---|---|
| N-01 | REPAIR_REQUIRED (§P0-1) |
| N-02 | REPAIR_REQUIRED (§P0-4) |
| N-03 | REPAIR_REQUIRED (§P1-5/§6-B/C-12) |
| N-04 | BLOCKED |
| N-05 | BLOCKED (§P1-2) |
| N-06 | BLOCKED (§P1-1) |
| N-07 | REPAIR_REQUIRED (§P0-2 latido) |
| N-08 | ACEPTADA (referencia H-16 corregida) |
| N-09 | ACEPTADA |
| N-10 | REPAIR_REQUIRED |

## 12. D-R2R2-1…11 — ninguna ratificada

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

## 13. Propagación total (regla §P1-4 aplicada)

Conjunto BLOCKED v4 (cerrado por dependencia): H-03(ahora con reserva), H-05, H-06, H-11, H-13, H-14, H-15, H-17, H-18, H-23, H-24, H-25, H-26; AUD-007/011/013/014/015/018/019; A-03/A-04/B/C/D/E/F; C-02/C-03/C-04/C-07/C-08/C-09/C-13/C-14/C-15/C-17/C-18/C-19; M-01/M-04/M-05/M-10; N-04/N-05/N-06.
Regla: cualquier dependencia de estos elementos en otra fila obliga a esa fila a declararse BLOCKED en la siguiente revisión, salvo que se demuestre independencia formal.

## 14. Criterio de aceptación y plan de verificación

```
Aceptación total (cuantos pasos, no verificados aquí):
 1. DDL ejecutable completo de scope/operation/attempt/effect_log/reconciliation_record (pg sandbox).
 2. Vectores de hash verificados por dos ejecutores independientes.
 3. Tests de concurrencia deterministas HP-1..6 (suspendimiento/despacho).
 4. Censo bidireccional A-01 (árbol≡artefacto) ejecutado.
 5. Revisión independiente de 104 filas fila por fila.
 6. Cotejo DDL y vectores por dos ejecutores.

Este documento no declara ningún paso ejecutado.
```

## 15. Estado

- Baseline v2.r2 intacto (`9c8a0aba…`); §1 intacta (`74a19ba2…`); `B07_FORMAL_MODEL.md` intacto.
- Antecedentes v1/v2/v3 conservados.
- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `MODEL_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · `D-315 = PENDING` · `PROMOTION = NOT_READY`.
- `state/multiproject/log.md` registra esta revisión.

Fin matriz consolidada R2-A — REVISIÓN 4 · DRAFT / NOT_ACCEPTED · Procedencia en `state/multiproject/log.md`.
