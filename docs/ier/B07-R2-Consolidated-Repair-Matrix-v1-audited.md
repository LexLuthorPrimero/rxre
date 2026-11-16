# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** `docs/ier/B07-R2-Repair-Specification.md` v2.r2 — SHA-256 `9c8a0aba5cf6770b12561b7734e0630c41ae44b268ce5f9ecdcf216f9c57c39e` — **INMUTABLE**. Esta matriz NO lo modifica.
**Objetivo:** consolidar en una sola trazabilidad los hallazgos H-01…H-27, R2A-AUD-001…019, las 9 notas residuales, los 10 microdefectos (M-01…M-10) y los hallazgos nuevos del auditor (A-01…A-04, B, C, D, E, F, G).
**Alcance:** diseño documental. Ningún código, DB, protocolo, crash injection, R3, publicación ni promoción. §1 intacta. `B07_FORMAL_MODEL.md` intacto.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED` — 76 filas; estados `REPAIRED-DOCUMENTAL` (propuesta, pendiente ratificación), `BLOCKED` o `NOT_APPLICABLE`; ningún estado implica cierre.

## 0. Leyenda de columnas y regla de cierre

Cada fila demuestra: `Definición → Persistencia → Transición → Invariante → Contraejemplo discriminante → Prueba`.

- `REPAIRED-DOCUMENTAL`: reparación diseñada y especificada en el documento r2; **no** ejecutada; sin verificación independiente; falta auditoría y ratificación del propietario.
- `BLOCKED`: incompatible o indecidible sin decisión externa (ver §7/§8).
- `NOT_APPLICABLE`: justificado con evidencia; prohibido usarlo para cerrar preguntas abiertas sin argumento.

Regla: **ni una re-apertura de v2.r2 → r3 ocurre sin ratificación expresa de cada fila por parte del propietario.**

---

## 1. Inventario total (76 filas)

| Fuente | Cantidad | Ver |
|---|---:|---|
| H-01…H-27 (auditoría del diseñador a v2) | 27 | §2 |
| R2A-AUD-001…019 (auditoría del diseñador a v1/v2) | 19 | §3 |
| Notas residuales de entrega v2.r2 | 9 | §4 |
| Microdefectos (M-01…M-10) | 10 | §5 |
| Hallazgos nuevos sobre v2.r2 (A-01…A-04, B, C, D, E, F, G) | 11 | §6 |
| **Total** | **76** | — |

---

## 2. Matriz H-01…H-27 (diez campos por fila)

| H | Defecto | Causa | Definición (→) | Persistencia | Transición | Invariante | Contraejemplo discriminante | Prueba | Estado |
|---|---|---|---|---|---|---|---|---|---|
| H-01 | Hash ambiguo, sin algoritmo ni vectores | concatenación `H(tag)‖campos` | SHA-256 tabular; tags NUL; layout fijo; vectores §R2.r2.1.6 | `manifest`, tablas hash-selladas | creación manifiesto; `T-SUSPEND`/`T-REOPEN` | ninguna nueva; tags pinning CHECK / census | confusión de cortes `a‖bc` vs `ab‖c` eliminada por longitudes explícitas y tags NUL | A-05/A-26 | REPAIRED-DOCUMENTAL |
| H-02 | `effect_ordinal` ambigüedad | ordinal local por `effect_kind` | ordinal global denso 0..n−1; orden de encode = ordinal | `manifest.effects_canon` | escritura/lectura manifiesto | INV-12 | dos efectos con mismo (kind, ordinal) permutados → permutación de `effect_ordinal` produce manifiesto distinto; unicidad integra la firma | A-05/A-26 | REPAIRED-DOCUMENTAL |
| H-03 | Manifiesto sin fuente de verdad | ausencia de almacén | tablas selladas append-only; manifiesto inmutable con `effects_canon` | completa §R2.r2.2 | sellado manifiesto tx | INV-01/12; INV-18 | sink recalculando sobre manifiesto falsificado sin almacenamiento ⇒ rechazo por recompute | A-02/A-05/A-21 | REPAIRED-DOCUMENTAL |
| H-04 | Head pointer sin CAS | último escritor gana | `SET_HEAD_ATTEMPT` CAS por `expected_generation` | única tx `operation+attempt` | claim | INV-17 | dos claims concurrentes → exactamente uno publica cabeza; otro aborta | A-02/A-15 | REPAIRED-DOCUMENTAL |
| H-05 | Fencing no linealizable vs suspensión | lectura consistente insuficiente | exclusión mutua sink↔T-SUSPEND por fila `scope` FOR UPDATE; LP=adquisición de lock | `scope` row lock; ES-001/002 inmediatos | dispatch; T-SUSPEND | INV-04/11/16 | escenario HP-2 del diseñador: fence elevado tras T-SUSPEND ⇒ sink rechaza siempre | A-12/A-15/A-21 | REPAIRED-DOCUMENTAL (sujeto a N-B) |
| H-06 | `REOPEN_EVIDENCE` sin esquema cerrado | referencia sin definición | esquema completo §R2.r2.4.2; Ed25519; payload determinista (D-R2R2-9) | `reopen_evidence` append-only | `T-REOPEN` | INV-15 | evidencia con `opened_epoch ≠ scope_epoch+1` o `verifier_id==issuer` ⇒ rechazo | A-04/A-22/A-24 | REPAIRED-DOCUMENTAL (sujeto a N-E) |
| H-07 | `RECONCILE_REQUIRED`; `scope_event` sin esquema | inconsistencia dominio | token `RECONCILIATION_REQUIRED`; evento y transición en la **misma** tx | `scope_event` | `T-SUSPEND` | INV-15 | evento huérfano sin su transición ⇒ jamás persiste por tx única | A-12/A-15 | REPAIRED-DOCUMENTAL |
| H-08 | FK compuesta ausente | scope_id sin referencia útil | FK `attempt(scope_id, operation_id) → operation(scope_id, operation_id)`; `UNIQUE(scope_id, operation_id)` | índices DDL | claim; re-lectura sink | INV-01/17 | intento con scope ajeno a la operación ⇒ RESTRICT rechaza | A-02 | REPAIRED-DOCUMENTAL |
| H-09 | Binding incoherente op↔intento | `operation.binding_hash` duplicada | binding **por intento**; cabeza componencial; `operation.binding_hash` eliminada | `attempt.binding_hash` NOT NULL | cabeza CAS | INV-17 | reintento con cabeza antigua inyectado ⇒ head-pointer hash concurrente rechaza por CAS | A-02/A-18/A-03 | REPAIRED-DOCUMENTAL |
| H-10 | Idempotencia entre epochs | regla omite epoch | clave idempotencia `(scope_id, scope_epoch, operation_kind, request_id)` única | índice compuesto | creación operación | INV-02/15 | tras REOPEN, misma request ⇒ nueva op; antes del REOPEN ⇒ devuelve existente | A-18/A-26 | REPAIRED-DOCUMENTAL |
| H-11 | Fencing sin protocolo | sólo monótona declaración | W co-locado; asignación atómica `scope.next_fence` claim tx; overflow→FENCING_EXHAUSTION | `scope.next_fence`; `attempt.fencing_token` UNIQUE | claim; dispatch; sink | INV-12/17 | sink acepta grant con fence previo a suspensión ⇒ protocolo rechaza por mínimos | A-12/A-15/A-25 | REPAIRED-DOCUMENTAL |
| H-12 | `decision_id` sin consumo atómico | T13 sin UNIQUE declarado | `consumed_decision` PK; todo cierre consume | DDL + tx | T-SUSPEND/T-REOPEN/T13/T-CLOSE | INV-19 | doble reapertura con mismo evidence ⇒ exactamente una transición gana | A-13/A-24/A-04 | REPAIRED-DOCUMENTAL |
| H-13 | `T-REOPEN` incompleto | crash mid-tx sin ancla | consume→row lock→verificaciones→epoch+1→fence→reopen_evidence→COMMIT | tx; `reopen_evidence` | `T-REOPEN` | INV-15/19 | crash entre bump y reopen_evidence ⇒ rollback completo | A-04/A-13 | REPAIRED-DOCUMENTAL (sujeto a N-E) |
| H-14 | `V=CLOSED` sin transición formal | absorbente sin ruta | `T-CLOSE` completo; cierra **todas** ops; fence explícito (§6 C) | `consumed_decision`; tx | `T-CLOSE` | INV-03/16/19 | scope sano con op OPEN+COMMIT_DURABLE + T-CLOSE ⇒ op queda CLOSED (violación previa de INV-16 eliminada) | A-14/A-08 | REPAIRED-DOCUMENTAL (sujeto a N-C) |
| H-15 | Máquinas incompletas | invariantes ≠ máquinas | tablas completas SI/TRs/ESs/OD/P/V/O/T/ESo/ES | máquinas §R2.r2.4.5…13 | todas | INV-01..19 | crash RECOVERABLE ⇒ SC-002 obligatorio o FAILED_CONSUMED | A-06/A-07/A-17 | REPAIRED-DOCUMENTAL (sujeto a N-D) |
| H-16 | INV-13 sin derivación | apelación a INV-09 | INV-13 = contrapositiva demostrada (dominio finito) | — | — | INV-13 | claim «consecuencia directa» es argumento; r2 lo resuelve por prueba | A-06 | REPAIRED-DOCUMENTAL |
| H-17 | Reconciliación incompleta/ES ilegal | `NOT_VERIFIED` ∉ ES; sin replay | dominio VERIFIED/REJECTED/CONTRADICTION; replay protected; orden total | `reconciliation_record` | ReconciliationProtocol | INV-05 | doble veredicto silencioso ⇒ r2 exige scope CONTRADICTION | A-07/A-23 | REPAIRED-DOCUMENTAL |
| H-18 | `ESo=REJECTED` sin terminal | camino muerto | (a) evidencia nueva → RECEIVED; (b) compensación durable + `T-CLOSE`; nunca `REJECTED→TESTIFIED` | `reconciliation_record`; tx | ESo machine | INV-07a/b/c; INV-14 | REJECTED oscilante eterno sin salida; r2 lo cierra por dos vías | A-07/A-17 | REPAIRED-DOCUMENTAL |
| H-19 | Tipos generación divergentes | UINT8 vs smallint/bigint | generation ≡ smallint 1..255; claim_generation ≡ UINT64 `numeric(20,0)` §7 D-R2R2-7; divergencia declarada | DDL alineado | claim | INV-08 | 255 vs 255, interpretación ambigua con epoch ⇒ exactamente 1..255 sin cast | A-02 | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-7) |
| H-20 | Barrera A6 permisiva | ELSE ALLOWED | default-deny; unknown ⇒ BLOCKED | `blocked_symbols` | todas | INV-19; censo | símbolo inocente colando dependencia §1 ⇒ denegado | A-09 | REPAIRED-DOCUMENTAL |
| H-21 | Censo incompleto, sin regla rechazo | no exhaustivo | census bidireccional completo §0+r2.5; regla rechazo; A-01 ambas direcciones | tabla §0 | todas | INV-01..19; A-01 | token no clasificado aceptado silenciosamente; r2 lo rechaza por regla | A-01 | REPAIRED-DOCUMENTAL (sujeto a N-G) |
| H-22 | Cardinalidad sin fundamentación | aritmética sin dominios | dominios justificados desde R1; 60/8640/518400 =; LEGAL/REACHABLE desconocidos | — | — | D-315 PENDING | 518400 presentado como legal: r2 declara cartesiano, no legal | A-06/A-10/A-26 | REPAIRED-DOCUMENTAL |
| H-23 | A-03 no demuestra cobertura sinks | construcción-no-evidencia | A-03-v2 reproducible; whitelist única; A-19 build-fail; A-20 ACL | sink ACL | dispatch gate | INV-12/19 | sink clandestino sin registro; r2 lo detecta y bloquea | A-03-v2/A-19..A-21 | REPAIRED-DOCUMENTAL |
| H-24 | Frontera confianza indefinida | A-11 asumía | TCB explícito; Ed25519; A-19/A-20; accesos restringidos | ACL/PKI | dispatch gate | INV-12/19 | llamar al adaptador externo sin sink ⇒ build/runtime error | A-11/A-19/A-20 | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-1/6) |
| H-25 | LP solicitud vs suspensión | orden lock indefinido | HP-1..6 con orden de lock explícito según vencedor | `scope` row lock | sink vs T-SUSPEND | INV-12/15 | mensaje válido en t ejecutado post-suspensión; r2 lo rechaza por lock | A-15/A-21 | REPAIRED-DOCUMENTAL (sujeto a N-B) |
| H-26 | Políticas sin puerta terminación | semántica sin transición | PL-002/PL-003 gates; PL-001 obligatorio ABORT; INV-18 | `manifest.policy` CHECK | máquina P | INV-18 | ALL con un COMPENSATED testificado COMMITTED; r2 lo prohíbe | A-17/A-27 | REPAIRED-DOCUMENTAL (sujeto a N-F) |
| H-27 | A6 sin propagación transitiva | solo símbolo directo | cierre transitivo finito por altura del grafo; unknown ⇒ dependiente BLOCKED | `blocked_symbols` | todas | INV-19; A-09 | símbolo permitido pese a depender de token §1; r2 lo bloquea | A-09 | REPAIRED-DOCUMENTAL (sujeto a N-E/M-05) |


## 3. Matriz R2A-AUD-001…019 (cobertura individual — cierra N-G)

| AUD | Descripción del hallazgo | Cobertura en r2 | Estado |
|---|---|---|---|
| AUD-001 | `SinkAccept` campos inexistentes | §R2.r2.3.2/3: EF-002 tipa mensaje; `SinkAcceptance` redefinida sobre campos declarados | REPAIRED-DOCUMENTAL |
| AUD-002 | Binding duplicado y preimagen inconsistente | **Una única definición** `BindingHash` (§R2.r2.1.3); demais secciones referencian | REPAIRED-DOCUMENTAL |
| AUD-003 | INV-06 redundante y ambigua | Eliminada → `INV-09` (autoridad única) | REPAIRED-DOCUMENTAL |
| AUD-004 | INV-07 con elipsis | Subdividida `INV-07a/b/c` cerradas | REPAIRED-DOCUMENTAL |
| AUD-005 | `≈ 8640` notación débil | `= 8640` (producto exacto) | REPAIRED-DOCUMENTAL |
| AUD-006 | §2.L contradice §2.A | `§A5.1` = texto unificado (OD-002 necesaria no suficiente; histórica post-COMMIT) | REPAIRED-DOCUMENTAL |
| AUD-007 | Epoch sin transición completa | `T-REOPEN` atómica con `scope_epoch+1` y `minimum_valid_fence:=GREATEST+1` | REPAIRED-DOCUMENTAL (sujeto a N-E) |
| AUD-008 | DDL sin `binding_hash` | `operation` sin `binding_hash`; `attempt.binding_hash` NOT NULL + CAS head | REPAIRED-DOCUMENTAL |
| AUD-009 | Dependencia FG-001→ES-007 injustificada | `REOPEN_EVIDENCE → scope_event (SC-001) + verificación independiente` (ninguna dependencia de efecto) | REPAIRED-DOCUMENTAL |
| AUD-010 | Índice impide reintentos legítimos | Unicidad en `attempt`; idempotencia compuesta con epoch en `operation` | REPAIRED-DOCUMENTAL |
| AUD-011 | Fencing no linealizable vs suspensión | Exclusión mutua por fila `scope` (§R2.r2.3.2); fence aplicado origen+sink | REPAIRED-DOCUMENTAL (sujeto a N-B) |
| AUD-012 | Origen vs sink no demostrados equivalentes | Separación explícita `DispatchAuthorization` (prevalidación) / `SinkAcceptance` (autoridad) | REPAIRED-DOCUMENTAL |
| AUD-013 | T13 no atómica | `T-CLOSE` atómica como transacción única (incluye suspend masivo + consume) | REPAIRED-DOCUMENTAL (sujeto a N-C, N-D) |
| AUD-014 | UNKNOWN/compensación informal | `ReconciliationProtocol` completa con dominio ES cerrado + replay protection | REPAIRED-DOCUMENTAL |
| AUD-015 | R1.3 vocabulario incompleto | Censo §0 + R1.3 completo (19 registros, diez campos) | REPAIRED-DOCUMENTAL |
| AUD-016 | INV-02 contradice epochs | `INV-02` reescrita (epoch vigente; histórico fijo; ops antiguas sin despacho) | REPAIRED-DOCUMENTAL |
| AUD-017 | Intentos sin persistencia | `attempt` tabla con claves/UNIQUE/INV-17 + head CAS | REPAIRED-DOCUMENTAL |
| AUD-018 | Política NONE/ANY/ALL sin semántica | §R2.r2.5.6 + INV-18 + tabla veredicto→estado del efecto | REPAIRED-DOCUMENTAL (sujeto a N-F) |
| AUD-019 | Relación P/T/ESo/O incompleta | INV-10/13/14/16/18 + §A5.1 obligaciones de consistencia | REPAIRED-DOCUMENTAL |

## 4. Notas residuales (9) — correspondencia

| RES | Nota (entrega v2.r2) | Correspondencia |
|---|---|---|
| RES-1 | `SinkAccept` campos inexistentes | = AUD-001 / H-05 / H-06; cierre verificado en EF-002 |
| RES-2 | Binding definido dos veces | = AUD-002 / H-09 |
| RES-3 | INV-06 e INV-07 | = AUD-003/004 / H-16 |
| RES-4 | `≈ 8640` | = AUD-005 / H-22 |
| RES-5 | §2.L semántica OD | = AUD-006 / D-R2A-3/4 |
| RES-6 | Incremento de epoch | = AUD-007 / H-13; §R2.r2.4.3 |
| RES-7 | DDL sin binding_hash | = AUD-008 / H-03/A-04 |
| RES-8 | Dependencia FG-001→ES-007 | = AUD-009 / §R2.r2.4.2 |
| RES-9 | INV-13 apelación | = H-16 (contrapositiva demostrada) |

## 5. Microdefectos (M-01…M-10) — correspondencia y disposición

| M | Defecto | Correspondencia | Disposición (propuesta) |
|---|---|---|---|
| M-01 | `ESo=REJECTED` «no leyérese T» ininteligible | AUD-004/018; H-18 | reescritura: «`ESo=REJECTED` ⇒ `T=NONE`; no habilita testificación; sólo cierre por compensación durable o nueva evidencia positiva» |
| M-02 | `decided_at` UINT64 en type table vs timestamptz DDL | H-17 | un único tipo: `timestamptz NOT NULL` en DDL y `UINT64` ABI de cable eliminado o ligado a timestampl; decisión D-R2R2-7 |
| M-03 | claim_generation «1…255» + ref §R2.r2.2.8 | H-19/AUD-017 | corregir ref → §R2.r2.2.5 y texto → UINT64 canónico (representación DDL según D-R2R2-7: numeric(20,0)) |
| M-04 | `IER-reopen-v1` en censo sin uso | AUD-007/009 | **eliminar** el tag del census o, preferiblemente, usarlo firmando el payload de reapertura como cierra N-E (decisión D-R2R2-9) |
| M-05 | `BND` sin regla de propagación demostrada | AUD-011/H-27 | añadir lema de punto fijo finito (dominios finitos; aristas monótonas al recorrer dependencias; terminación por rank altura del grafo) y demostración en §R2.r2.5.1 |
| M-06 | §7.5 (trazabilidad) inexistente | AUD-015 | reubicar referencia → §R2.r2.6 §6.2 |
| M-07 | `salt` en comentario sin campo | AUD-001/N-E | eliminar `salt` de toda fórmula y comentario (decisión D-R2R2-9: payload determinista) |
| M-08 | «`io` tags de política» espurio | AUD-018/H-26 | eliminar palabra «io»; policy siempre UINT8 (tabla type row) |
| M-09 | `A-03` y `A-03-v2` sin identificador canónico | AUD-015/H-23 | unificar a **A-03/A-03-v2** everywhere; ningún símbolo alternativo |
| M-10 | «fence-window» indefinido en HP-6 | H-25 | definir: `fence-window := intervalo de validez de un fencing_token entre minimum_valid_fence−1+1 y la revocación por T-SUSPEND/T13; fuera del intervalo ⇒ mensaje inválido en sink por revalidación» |

## 6. Hallazgos nuevos del auditor sobre v2.r2 (A-01…A-04, B, C, D, E, F, G)

| ID | Defecto (preciso) | Reparación propuesta | Persistencia | Transición | Invariante | Contraejemplo que r2 debe impedir | Prueba | Estado |
|---|---|---|---|---|---|---|---|---|
| A-01 | `reconciliation_record` declara FK sobre columna `scope_id` inexistente | añadir `scope_id bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT` en `reconciliation_record`; FK compuesta a attempt confirmada | DDL completo | registro evento | INV-01 | intento de inserción sin scope? el DDL lo rechaza | A-02; A-01 census | REPAIRED-DOCUMENTAL |
| A-02 | `bigint` PG no contiene UINT64 (`<2^64`) | campos UINT64 canónicos ⇒ `numeric(20,0)` (íntegro, exacto; orden total; sin redondeo) — **decisión D-R2R2-7**; `decided_at` fuera de este tipo (timestamptz); wire encode UINT64 LE directo | DDL alineado | wire↔almacén | INV-08/12 | fencing_token grande truncado por bigint ⇒ sink aceptaría mensaje con token parcializado; r2 define almacenamiento completo | A-26; tests integración | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-7) |
| A-03 | head pointer sin FK real | `current_attempt_id` **NULL hasta primer claim**; FK `operation.current_attempt_id → attempt(attempt_id) DEFERRABLE INITIALLY DEFERRED`; INV-17 exige NOT NULL para operación con cualquier attempt | DDL + CHECK `v<>'OPEN' OR current_attempt_id IS NOT NULL` (emitido tras claim) | claim; SET_HEAD_ATTEMPT | INV-17; INV-03 | dos intentos cabeza o head huérfano post-claim | A-02; A-21 | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-8) |
| A-04 | manifest no ligado forzosamente a `operation.manifest_hash`; orden de creación indefinido | creación atómica de `(operation, manifest)` en **una tx**; `operation.current_…`/`manifest_hash` se escribe con el manifest de cálculo previo y cross-check `manifest.manifest_hash == computed`; FK `manifest.operation_id → operation` `DEFERRABLE`; no existe operación sin manifest ni viceversa (**sin excepciones**) | DDL + tx rules | creación operación | INV-12 | operación con manifest_hash ≠ manifest sellado; ya no persiste | A-02; A-05 | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-8) |
| B | externalidad del sink no atómica (HP-4 falso: efecto puede ocurrir con rollback posterior) | **Protocolo de dos fases con idempotencia**: (F1) sink FOR UPDATE + revalidación + registro durable de **intención** `ES-001 INTENT_DURABLE` (antes de cualquier llamada); (F2) llamada externa con **idempotency-key derivada de `(operation_id, effect_ordinal)`**; (F3) registro del resultado (ES-002/ES-005/ES-007); crash F1–F3 ⇒ `reconciler` resuelve por consulta provider-side con la misma idempotency-key; resultado incierto ⇒ ES-007 + SC-002; **HP-4 corregido**: ya no se afirma atomicidad externa; la unicidad deja de depender del «mismo tx» y pasa a depender de idempotency-key + reconciliación | `manifest`, `effect_log` (propuesta nueva fila) / `attempt` binding | dispatch; commit; recuperación | INV-05; INV-10 | efecto externo ocurre, PG rollback, sink/suspend reintentan ⇒ doble efecto; r2 lo impide por provider-side idempotency-key + reconciliación | A-12; A-15; A-21; HP-4 corregido | REPAIRED-DOCUMENTAL (sujeto a diseño N-B ratificado) |
| C | `T-CLOSE` sólo cierra SUSPENDED; INV-16 roto; fence bump sin SQL concreta | `T-CLOSE` v cierra **todas** ops del scope: `UPDATE operation SET v='CLOSED' WHERE scope_id=:id AND v IN ('OPEN','SUSPENDED')`; bump explícito `scope.minimum_valid_fence := GREATEST(minimum_valid_fence, next_fence) + 1; scope.next_fence := scope.minimum_valid_fence;` **misma tx**; absorción `CLOSED`(v3) | DDL; tx T-CLOSE | T-CLOSE | INV-16; INV-03; INV-19 | scope sano con op en COMMIT_DURABLE+OPEN + T-CLOSE ⇒ v queda OPEN; r2 la cierra | A-14; A-08 | REPAIRED-DOCUMENTAL |
| D | `T13` sin protocolo normativo completo | definir protocolo T13: precondición (decisión humana durable, decision_id UNIQUE, scope no HUMAN_CLOSED ya), una tx: insert consumed; row lock; fence bump; suspend masivo (v: OPEN→SUSPENDED; SUSPENDED ya queda), `si:=HUMAN_CLOSED`; insert `scope_event{kind=HUMAN_CLOSED}`; COMMIT; crash ⇒ rollback total; HP rows; tests A-14 | `consumed_decision`, `scope_event`, tx única | T13 | INV-16; INV-19 | crash a mitad de cierre ⇒ scope HUMAN_CLOSED con operaciones OPEN o sin suspensión masiva; r2 lo impide | A-14 | REPAIRED-DOCUMENTAL |
| E | Firma de reapertura sin preimagen cerrada: `IER-consume-v1` fuera del censo; `salt16` no persistido; §1.8≠§4.2; binding scope incompleto | unificar §R2.r2.1.8 y §R2.r2.4.2: preimagen exacta `SHA-256(Tag('IER-consume-v1\0') ‖ encode_bytes(payload))` donde `payload := kind('REOPEN'|'T13'|'CLOSE') ‖ encode_bytes(scope_id) ‖ encode(UINT64 scope_epoch) ‖ encode_bytes(decision_id)`; **persistir** `salt` eliminado; payload determinista ⇒ salt innecesario; añadir `IER-consume-v1\0` al censo §0; firma = Ed25519(payload_final); verifier registrado PKI independiente; `reason` en payload; **verificar vinculación scope_epoch↔evento** | `reopen_evidence` + `consumed_decision` | T-REOPEN/T13/T-CLOSE | INV-15 | evidencia que no correla con el evento de degradación exacto, aceptada como «nueva»; r2 lo impide por payload | A-04; A-22; A-24 | REPAIRED-DOCUMENTAL (sujeto a D-R2R2-9) |
| F | Políticas incompletas: `REJECTED-with-record` ∉ ES; ALL verdad vacua en manifiesto vacío; codificación inconsistente (UINT8/smallint/UINT16) | mapa completo `veredicto→estado ES`: `VERIFIED→ES-005`, `REJECTED→saga→ES-006 o FAILED_CONSUMED (terminales)`, `CONTRADICTION→scope CONTRADICTION`; empty-manifest rules: `PL-002 y PL-003 requieren ≥1 efecto; vacío ⇒ ABORT_DURABLE obligatorio`; todos los valores de política ≡ UINT8 wire (smallint 0..2 DB); type table fila policy unificada; tests A-17/A-27 extendidos (caso vacío, ALL-fail-one-COMPENSATED) | `manifest.policy` CHECK 0/1/2 | gate máquinas P/ANY/ALL | INV-18 | ALL aplicado a manifiesto vacío acepta éxtito por vacuo; r2 lo prohíbe | A-17; A-27 | REPAIRED-DOCUMENTAL |
| G | Matriz §6.2 no demuestra cobertura AUD-001/006/009 | este documento §3 asigna correspondencia **individual** a los 19 AUD; AUD-001→§R2.r2.3.2/3.3; AUD-006→D-R2A-3/4 → §A5.1/OD; AUD-009→FG-001 dep=SC-001 | — | matrix | — | — | auditoría misma | REPAIRED-DOCUMENTAL |


---

## 7. Decisiones pendientes del propietario (exigidas por esta matriz)

| # | Decisión | Propuesta |
|---|---|---|
| D-R2R2-1 | Esquema y PKI de firmas (issuer/verifier) | Ed25519, almacén de identidades independiente del productor |
| D-R2R2-2 | Autoridad de `fencing_token` | W co-locado con el almacén del scope vía `scope.next_fence` (§R2.r2.3); alternativa secuencia DB bajo B-04 |
| D-R2R2-3 | `T-CLOSE` sobre scope sano legítimo | Permitido con decisión humana durable; suspende/cierra masivamente |
| D-R2R2-4 | `claim_generation` canónico | UINT64; §R2.3 del artefacto permanece REPAIR_REQUIRED; alineación exige autorización |
| D-R2R2-5 | Tag de dominio para `decision_id` | `'IER-consume-v1\0'` (alineado con N-E) |
| D-R2R2-6 | Toolchain A-19 | árbol sintáctico (tree-sitter u equivalente); se decide al abrir R3 |
| D-R2R2-7 | Representación UINT64 en almacén | `numeric(20,0)` (recomendada) o `bigint` con decisión explícita de dominio ≤ 2^63−1 documentada |
| D-R2R2-8 | Estrategia de FK circulares | `DEFERRABLE INITIALLY DEFERRED` para `operation.current_attempt_id → attempt` y `manifest.operation_id → operation`; INV-17 de respaldo en commit |
| D-R2R2-9 | Preimagen/firma del cierre de decisión (`REOPEN`/`T13`/`T-CLOSE`) | payload determinista = `SHA-256(Tag('IER-consume-v1\0') ‖ encode_bytes(kind) ‖ encode_bytes(scope_id) ‖ encode(UINT64 scope_epoch) ‖ encode_bytes(decision_id))`; sin `salt`; sin entradas opacas |
| D-R2R2-10 | Integridad del manifiesto con vínculo cruzado | `operation.manifest_hash = manifest.manifest_hash` verificable por trigger de commit + A-02; alternativa: `manifest` como fila de `operation` con contención de archivo sellado |
| D-R2R2-11 | ¿Clasificación de `REJECTED` de reconciliación como estado ES de facto (`FAILED` marker) o sólo como veredicto ligado? | Propuesta: **veredicto ligado**; los estados ES permanecen cerrados; el efecto transita ES-002/004→(saga→)ES-006 o FAILED_CONSUMED |

## 8. Incompatibilidades no resolubles por diseño (documentadas; no se eluden)

1. **§1 (FROZEN)**: contradicción vigente; `CANONICAL_DEPENDENCY_BLOCKED` (FG-003). No se resuelve aquí.
2. **Independencia de terceros**: ninguna reconciliación de este modelo puede auto-verificarse; todo `UNKNOWN` exige verificador independiente. Terceros: `NOT_EXECUTED`.
3. **B-03 / B-04 / B-08 (`OPEN`)**: la autoridad final de fencing vive en B-04; este documento parametriza sin cerrar ese bloque.
4. **Atomicidad externa**: ningún diseño puede hacer «una transacción» con un sistema de terceros sin su cooperación; la garantía exigible es: intención durable + idempotency-key + reconciliación obligatoria. «Atomicidad externa» estricta no es alcanzable — se declara, no se simula.
5. **Entorno criptográfico**: la seguridad real depende de PKI y gestión de claves fuera de este modelo; `Ed25519` es propuesta, no evidencia.

## 9. Procedimiento posterior (NO autorizado todavía — bloqueado hasta ratificación)

```
1. Propietario audita esta matriz + las decisiones (D-R2R2-1…11).
   [artefacto: este documento]
2. Con dictamen: r3 de B07-R2-Repair-Specification.md regenerada
   como revisión completa (no parches) aplicando la matriz ratificada.
3. r3 pasa a auditoría independiente (nueva).
4. Nada se aplica a B07_FORMAL_MODEL.md salvo autorización separada.
5. R3 no se abre hasta cierre documental de R2 + autorización expresa.
```

## 10. Estado y procedencia

- `R2 = REPAIR_REQUIRED`. `AUD-001…019`, `H-01…27`, microdefectos y hallazgos nuevos: **ATENDIDOS EN ANÁLISIS, NO CERRADOS**.
- `R3 = BLOCKED` · `D-315 = PENDING` · `IMPLEMENTATION_READY = NO` · `MODEL_VERIFIED = NO` · `PROMOTION = NOT_READY`.
- Nada de este documento verifica, ejecuta ni promulga.
- Procedencia: `docs/ier/B07-R2-Repair-Specification.md` (9c8a0aba…) auditada por el propietario 2026-11-15; hallazgos verificados independientemente por el ejecutor (§1 de este documento); decisiones de diseño documentadas sin ratificar.
- `state/multiproject/log.md` registra esta entrada.

Fin matriz consolidada R2-A · DRAFT / NOT_ACCEPTED · Procedencia en `state/multiproject/log.md`.
