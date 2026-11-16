# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 2 (POST-AUDITORÍA)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** `docs/ier/B07-R2-Repair-Specification.md` v2.r2 — SHA-256 `9c8a0aba5cf6770b12561b7734e0630c41ae44b268ce5f9ecdcf216f9c57c39e` — **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedente:** `docs/ier/B07-R2-Consolidated-Repair-Matrix-v1-audited.md` (sha256 `e165acedff55b591b84168b138ac2951bb09a9032fa81d044f97704641a19bad`) — versión auditada, conservada íntegra; **no** se usa como baseline; este documento la corrige y reemplaza.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`
**§1 y `B07_FORMAL_MODEL.md` intactos. Ninguna r3 autorizada. R3 BLOCKED. Promoción NOT_READY.**

## Registro de revisiones

| Versión | SHA-256 | Disposición |
|---|---|---|
| v1-auditada | `e165acedff55b591b84168b138ac2951bb09a9032fa81d044f97704641a19bad` | Auditoría del diseñador 2026-11-15: NO RATIFICABLE; consistencia técnica FAIL; 18 correcciones estructurales exigidas |
| v2 (este documento) | hash publicado fuera del archivo (`state/multiproject/log.md`) | Incorpora **todas** las reparaciones exigidas por la auditoría (C-01…C-19, §R2-A.r2) + reclasificación de estados según dictamen; todavía sin verificar; aceptación exclusiva del propietario |

---

## 0. Leyenda y regla de cierre

Cada fila demuestra: `Definición → Persistencia → Transición → Invariante → Contraejemplo discriminante → Prueba`.
Estados:
- `REPAIRED-DOCUMENTAL`: especificación diseñada; **no** ejecutada; sin verificación; falta auditoría.
- `REPAIRED-DOCUMENTAL DE LIMITE` / `CONDICIONADO`: reparación diseñada pero depende de una decisión pendiente o un límite explícito (B-04, PKI, §1, tercero).
- `BLOCKED`: incompatible o indecidible sin decisión externa o diseño adicional; **no** se cierra por contexto.
- `NOT_APPLICABLE`: justificado con evidencia.

**Regla absoluta**: ninguna re-apertura v2.r2 → r3 sin ratificación expresa del propietario fila por fila.

---

## 1. Inventario (75 unidades — corregido)

El error de v1 es corregido explícitamente: los hallazgos nuevos del auditor sobre v2.r2 son **10** (A-01…A-04, B, C, D, E, F, G), no 11. Total = 27+19+9+10+10 = **75**, no 76.

| Fuente | Cant. | Sección |
|---|---:|---|
| H-01…H-27 | 27 | §2 |
| R2A-AUD-001…019 | 19 | §3 |
| Notas residuales | 9 | §4 |
| Microdefectos (M-01…M-10) | 10 | §5 |
| Hallazgos nuevos del auditor sobre v2.r2 | 10 | §6 |
| Hallazgos de la auditoría de esta matriz (C-01…C-19) | 19 | §6-B |
| **Total** | **94** | — |

> Nota honesta: el inventario de v1 decía 75 pero los §6-B (19) son hallazgos nuevos de esta revisión; el conjunto a auditar es **94** filas, no 75. La auditoría v1 concluyó sobre los 75 contenidos en v1; las 19 filas nuevas derivan directamente de sus C-01…C-19 y re-clasificaciones. Ningún hallazgo se agrega silenciosamente.

---

## 2. Matriz H-01…H-27 (10 campos; estados v2 tras dictamen)

| H | Defecto | Causa | Definición | Persistencia | Transición | Invariante | Contraejemplo discriminante | Prueba | Estado (v1→v2) |
|---|---|---|---|---|---|---|---|---|---|
| H-01 | Hash ambiguo | concatenación `H(tag)‖campos` | SHA-256 tabular; tags NUL; layout fijo; vectores §R2.r2.1.6 | `manifest`, tablas selladas | sellado; creación intento | tags pinning CHECK + census | corte a `a‖bc` vs `ab‖c` | A-05/A-26 | REPAIRED-DOC → REPAIRED-DOC |
| H-02 | `effect_ordinal` ambiguo | local por tipo | ordinal global denso 0..n−1; orden de encode = ordinal | `manifest.effects_canon` | escritura manifiesto | INV-12 | permutación de ordinales ⇒ manifiesto distinto | A-05/A-26 | REPAIRED-DOC → REPAIRED-DOC |
| H-03 | Manifiesto sin fuente de verdad | ausencia de almacén | tablas selladas; **append-only con autoridad de escritura restringida y verificación por lectura** (§6-B/C-09, C-19) | completa §R2.r2.2 | sellado manifiesto | INV-01/12 | manifiesto falsificado por autoridad de escritura sin control; r2 lo impide por ACL y sellos | A-02/A-05/A-21 | REPAIRED-DOC → REPAIRED-DOC DE LÍMITE |
| H-04 | Head pointer sin CAS | último escritor gana | `SET_HEAD_ATTEMPT` con predicado completo: `WHERE operation_id=:op AND current_attempt_generation=:expected`; UPDATE+RETURNING; filas=1 éxito; 0 abort | única tx operación+head+insert intento | claim | INV-17 | dos claims simultáneos ⇒ exactamente uno publica cabeza | A-02/A-15 | REPAIRED-DOC → REPAIRED-DOC |
| H-05 | Fencing no linealizable vs suspensión | lectura consistente insuficiente | **protocolo de 2 fases + exclusión mutua por fila `scope` FOR UPDATE** (§6-B/B, C-02, C-08, C-18); LP entre validación y commit; sink re-verifica antes y después de lock | `scope` row lock; `effect_log` | dispatch; T-SUSPEND | INV-04/11/16 | escenario HP-2/HP-4-revisado + sink obsleto §6-B/C-08 | A-12/A-15/A-21 | REPAIRED-DOC → **BLOCKED** |
| H-06 | `REOPEN_EVIDENCE` sin esquema cerrado | referencia sin definición | esquema completo §R2.r2.4.2 + **preimagen criptográfica unificada y cerrada** (§6-B/E) | `reopen_evidence` append-only | T-REOPEN | INV-15 | evidencia con epoch/evento evasión o firma con preimagen ambigua | A-04/A-22/A-24 | REPAIRED-DOC → **BLOCKED** |
| H-07 | `RECONCILE_REQUIRED`; `scope_event` sin esquema | inconsistencia dominio | token `RECONCILIATION_REQUIRED`; evento+transición en misma tx | `scope_event` | T-SUSPEND | INV-15 | evento huérfano por fallo mitad tx | A-12/A-15 | REPAIRED-DOC → REPAIRED-DOC |
| H-08 | FK compuesta ausente | scope_id sin referencia | FK compuesta `attempt(scope_id, operation_id) → operation(scope_id, operation_id)`; `UNIQUE(scope_id, operation_id)` | DDL | claim; re-lectura sink | INV-01/17 | intento con scope ajeno a la operación ⇒ RESTRICT | A-02 | REPAIRED-DOC → REPAIRED-DOC |
| H-09 | Binding incoherente op↔intento | duplicación | binding por intento; cabeza componencial; eliminar `operation.binding_hash` | `attempt.binding_hash` NOT NULL | cabeza CAS | INV-17 | reintento con cabeza antigua inyectado | A-02/A-18 | REPAIRED-DOC → REPAIRED-DOC |
| H-10 | Idempotencia entre epochs | regla sin epoch | clave idempotencia `(scope_id, scope_epoch, operation_kind, request_id)` compuesta | índice | creación operación | INV-02/15 | REOPEN + misma request ⇒ nueva op; mismo epoch ⇒ devuelve existente | A-18/A-26 | REPAIRED-DOC → REPAIRED-DOC |
| H-11 | Fencing sin protocolo | sólo monótona | W co-locado; asignación atómica vía `scope.next_fence`; overflow→FENCING_EXHAUSTION | `scope.next_fence`; UNIQUE token TG | claim; dispatch; sink | INV-12/17 | sink acepte mensaje con fence previo computador | A-12/A-15/A-25 | REPAIRED-DOC → REPAIRED-DOC LIB-condicionado (B-04) |
| H-12 | `decision_id` sin consumo atómico | T13 sin UNIQUE | `consumed_decision` + **protocolo de consumo por tipo de transición** (§2-B/C-11) | `consumed_decision` | T-*/T13/T-CLOSE | INV-19 | doble reapertura con mismo evidence | A-13 | REPAIRED-DOC → REPAIRED-DOC |
| H-13 | `T-REOPEN` incompleto | crash mid-tx sin ancla | consume→row lock→verificaciones **cierre evidencia↔evento**→epoch+1→fence→reopen_evidence→COMMIT | tx; `reopen_evidence` | T-REOPEN | INV-15/19 | crash entre bump y reopen_evidence ⇒ rollback completo | A-04/A-13 | REPAIRED-DOC → **BLOCKED** |
| H-14 | `V=CLOSED` sin transición formal | absorbente sin ruta | `T-CLOSE` con precondición de **efectos resueltos** (§6-B/C-03): ningún efecto en INTENT/ES-002/ES-003/ES-004/ES-007 pendiente | `consumed_decision`; tx | T-CLOSE | INV-03/16/19 | op con efecto pendiente cierre ⇒ T-CLOSE aborta | A-14/A-08 | REPAIRED-DOC → **BLOCKED** |
| H-15 | Máquinas incompletas | invariantes≠máquinas | tablas completas SI/TRs/ESs/OD/P/V/O/T/ESo/ES **con relación estado-operación↔estado-efecto cerrada** | máquinas §R2.r2.4.5…13 | todas | INV-01..19 | crash RECOVERABLE ⇒ SC-002 o FAILED_CONSUMED | A-06/A-07/A-17 | REPAIRED-DOC → **BLOCKED** |
| H-16 | INV-13 sin derivación (sin prueba en texto) | apelación no demostrada | INV-13 = contrapositiva demostrada; **prueba escrita en texto del artefacto** (§2-B/C-18) | — | — | INV-13 derivada | claim «consecuencia directa» no aceptado | A-06 | REPAIRED-DOC → REPAIRED-DOC |
| H-17 | Reconciliación incompleta/ES ilegal | `NOT_VERIFIED` ∉ ES | dominio VERIFIED/REJECTED/CONTRADICTION; replay protection; **orden definido y contradicción explícita** (§2-B/C-12) | `reconciliation_record` | ReconciliationProtocol | INV-05 | doble veredicto silencioso ⇒ scope CONTRADICTION | A-07/A-23 | REPAIRED-DOC → **BLOCKED** |
| H-18 | `ESo=REJECTED` sin terminal | camino muerto | salidas formales (a) evidencia nueva → RECEIVED; (b) compensación durable → T-CLOSE; **relación ES↔T↔P↔O especificada y cerrada** (§2-B/C-13) | tx; `reconciliation_record` | ESo machine | INV-07a/b/c, INV-14 | REJECTED sin salida; r2 por compensación explícita | A-07/A-17 | REPAIRED-DOC → **BLOCKED** |
| H-19 | Tipos generación divergentes | UINT8 vs bigint | generation ≡ smallint 1..255; claim_generation ≡ UINT64 con dominio completo y `CHECK 0..2^64−1` (§2-B/C-05, §7 D-R2R2-7) | DDL alineado | claim | INV-08 | 255 vs 2^64-1, interpretación ambigua | A-02 | REPAIRED-DOC → REPAIRED-DOC CONDICIONADO |
| H-20 | Barrera A6 permisiva | ELSE ALLOWED | default-deny; unknown ⇒ BLOCKED | `blocked_symbols` | todas | INV-19; census | símbolo inocente con dep §1 ⇒ denegado | A-09 | REPAIRED-DOC → REPAIRED-DOC |
| H-21 | Censo incompleto, sin regla rechazo | no exhaustivo | census bidireccional §0 + regla rechazo; AUD-015 hasta aclarar canon → **BLOCKED** (§4-B/4.2) | tabla §0 | todas | INV-01..19 | token no clasificado aceptado | A-01 | REPAIRED-DOC → REPAIRED-DOC pero AUD-015 BLOCKED |
| H-22 | Cardinalidad sin fundamentación | aritmética sin dominios | dominios justificados; 60/8640/518400=; REACHABLE desconocido | — | — | D-315 PENDING | 518400 legal: r2 cartesiano | A-06/A-10/A-26 | REPAIRED-DOC → REPAIRED-DOC |
| H-23 | A-03 no demuestra cobertura sinks | construcción-no-evidencia | procedimiento A-03-v2 reproducible + evidencia ejecutable obligatoria; **no prohibido, no demostrada** | sink ACL | dispatch gate | INV-12/19 | sink clandestino no registrado | A-03-v2/A-19..A-21 | REPAIRED-DOC → **BLOCKED** |
| H-24 | Frontera confianza indefinida | A-11 asumía | TCB explícito; Ed25519; A-19/A-20; matiz PKI (D-R2R2-1) | ACL/PKI | dispatch gate | INV-12/19 | adaptador externo sin sink ⇒ build error | A-11/A-19/A-20 | REPAIRED-DOC → **BLOCKED** |
| H-25 | LP solicitud vs suspensión | LP ≠ commit; externalidad | **protocolo de 2 fases completo** con fencing en boundary confiable y revocación (§6-B/B) | row lock; `effect_log` | sink vs T-SUSPEND | INV-12/15 | sink arrestado invoca efecto tras suspensión confirmada; r2 lo impide en boundary | A-15/A-21 | REPAIRED-DOC → **BLOCKED** |
| H-26 | Políticas sin puerta terminación | sin transición | PL-002/003 gates; PL-001 obligatorio ABORT; INV-18; **empty-manifest rules** | `manifest.policy` | máquina P | INV-18 | ALL vacío ⇒ COMMIT por vacuo; r2 ABORT_DURABLE | A-17/A-27 | REPAIRED-DOC (sujeto a §6-B/F) → REPAIRED-DOC CONDICIONADO |
| H-27 | A6 sin propagación transitiva | solo símbolo directo | cierre transitivo formulado con **operador monótono sobre universo finito** + prueba de punto fijo por cardinalidad (§2-B/C-17) | `blocked_symbols` | todas | INV-19; A-09 | símbolo permitido pese a depender de token §1; r2 lo bloquea | A-09 | REPAIRED-DOC → **REPAIRED-DOC CONDICIONADO** |

## 3. Matriz R2A-AUD-001…019 (individual; estados v2 tras dictamen)

| AUD | Descripción | Cobertura en r2 | Estado (v2) |
|---|---|---|---|
| AUD-001 | `SinkAccept` campos inexistentes | §R2.r2.3.2/3: EF-002 tipa mensaje; `SinkAcceptance` redefinida sobre campos declarados; HP-2 conforme | REPAIRED-DOC |
| AUD-002 | Binding duplicado | Una única definición `BindingHash` (§R2.r2.1.3) | REPAIRED-DOC |
| AUD-003 | INV-06 redundante | Eliminada; INV-09 única autoridad | REPAIRED-DOC |
| AUD-004 | INV-07 con elipsis | INV-07a/b/c cerradas | REPAIRED-DOC |
| AUD-005 | `≈ 8640` | `= 8640` | REPAIRED-DOC |
| AUD-006 | §2.L contradice §2.A | OD-002 necesaria no suficiente; histórica post-COMMIT | REPAIRED-DOC |
| AUD-007 | Epoch sin transición completa | T-REOPEN atómica; `scope_epoch+1`; `minimum_valid_fence:=GREATEST+1`; **preimagen cerrada §6-B/E** | REPAIRED-DOC (sujeto a N-E) → **BLOCKED** |
| AUD-008 | DDL sin `binding_hash` | `operation` sin `binding_hash`; `attempt.binding_hash` NOT NULL | REPAIRED-DOC |
| AUD-009 | Dependencia FG-001→ES-007 | `REOPEN_EVIDENCE → SC-001 + verificación independiente` | REPAIRED-DOC |
| AUD-010 | Índice impide reintentos | Unicidad en `attempt`; idempotencia compuesta con epoch | REPAIRED-DOC |
| AUD-011 | Fencing no linealizable vs suspensión | Exclusión mutua sink↔T-SUSPEND; fencing en boundary | REPAIRED-DOC → **BLOCKED** |
| AUD-012 | Origen vs sink | `DispatchAuthorization` (prevalidación) / `SinkAcceptance` (autoridad); sink re-verifica tras lock | REPAIRED-DOC |
| AUD-013 | T13 no atómica | `T-CLOSE` atómica: transacción única con fence bump explícito y suspend masivo | REPAIRED-DOC → **BLOCKED** |
| AUD-014 | UNKNOWN informal | `ReconciliationProtocol` + dominio ES + replay protection + **closure-states (§2-B/C-13)** | REPAIRED-DOC → **BLOCKED** |
| AUD-015 | R1.3 vocabulario incompleto | Censo + R1.3; **compatibilidad con canon R1.1 sin demostrar** | REPAIRED-DOC → **BLOCKED** |
| AUD-016 | INV-02 contradice epochs | INV-02 reescrita (epoch vigente; histórico fijo) | REPAIRED-DOC |
| AUD-017 | Intentos sin persistencia | `attempt` con claves/UNIQUE/INV-17 + head CAS | REPAIRED-DOC |
| AUD-018 | Política sin semántica | §R2.r2.5.6 + INV-18 + mapa veredicto→estado | REPAIRED-DOC → **BLOCKED** |
| AUD-019 | Relación P/T/ESo/O | INV-10/13/14/16/18; **mapping estados op↔effect (§2-B/C-13)** | REPAIRED-DOC → **BLOCKED** |

## 4. Notas residuales (RES-1…9) — correspondencia corregida según dictamen

| RES | Nota | Correspondencia corregida | Estado |
|---|---|---|---|
| RES-1 | `SinkAccept` campos inexistentes | **RES-1 → AUD-001 (campos declarados en EF-002/ SinkAcceptance)**; NO H-05/H-06 (los modos de fallo son distintos) | REPAIRED-DOC |
| RES-2 | Binding duplicado | = AUD-002 / H-09 | REPAIRED-DOC |
| RES-3 | INV-06 e INV-07 | **RES-3 → AUD-003 (INV-06 eliminada) + AUD-004 (INV-07a/b/c)**; NO H-16 | REPAIRED-DOC |
| RES-4 | `≈ 8640` | = AUD-005 / H-22 | REPAIRED-DOC |
| RES-5 | §2.L semántica OD | = AUD-006 / D-R2A-3/4 | REPAIRED-DOC |
| RES-6 | Incremento de epoch | = AUD-007 / H-13; §R2.r2.4.3 | REPAIRED-DOC (sujeto a N-E) |
| RES-7 | DDL sin binding_hash | = AUD-008 / H-03/A-04 | REPAIRED-DOC |
| RES-8 | FG-001→ES-007 | = AUD-009 / §R2.r2.4.2 | REPAIRED-DOC |
| RES-9 | INV-13 apelación | = H-16 (contrapositiva escrita en texto) | REPAIRED-DOC |

## 5. Microdefectos (M-01…M-10) — estados v2 tras dictamen

| M | Defecto | Correspondencia | Estado (v2) |
|---|---|---|---|
| M-01 | `ESo=REJECTED` ininteligible | AUD-004/018; H-18; **resolver en §6-B/F** | REPAIRED-DOC |
| M-02 | `decided_at` UINT64 vs timestamptz | H-17; **un único tipo decidido (§2-B/C-05)** | → **BLOCKED** (decisión D-R2R2-7 obligatoria) |
| M-03 | claim_generation «1…255» + ref | H-19/AUD-017 | → **BLOCKED** (requiere alineación UINT64 global) |
| M-04 | `IER-reopen-v1` sin uso | AUD-007/009 | → **BLOCKED** (requiere D-R2R2-9) |
| M-05 | `BND` sin propagación demostrada | AUD-011/H-27 | → **CONDICIONADO** (requiere C-17 cerrado) |
| M-06 | §7.5 inexistente | AUD-015; reubicado → §R2.r2.6 §6.2 | REPAIRED-DOC |
| M-07 | `salt` sin campo | AUD-001/N-E | → **CONDICIONADO** (requiere D-R2R2-9) |
| M-08 | «`io` tags de política» | AUD-018/H-26 | REPAIRED-DOC |
| M-09 | `A-03` vs `A-03-v2` | AUD-015/H-23; unificado a **A-03/A-03-v2** | REPAIRED-DOC |
| M-10 | «fence-window» indefinido | H-25 | → **REPAIR REQUIRED** (redefinición operacional §6-B/C-06) |


## 6. Hallazgos nuevos del auditor sobre v2.r2 (A-01…A-04, B, C, D, E, F, G) — estados v2 tras dictamen

| ID | Defecto (preciso) | Reparación diseñada (v2, tras auditoría) | Persistencia | Transición | Invariante | Contraejemplo discriminante | Prueba | Estado |
|---|---|---|---|---|---|---|---|---|
| A-01 | `reconciliation_record` declara FK sobre columna inexistente | **v2**: añadir `scope_id bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT` y FK compuesta; columnas `operation_id`, `attempt_id` ya existen | DDL completo | registro reconciliación | INV-01 | inserción bajo scope ajeno rechazada; intento sin scope inexistente | A-02 | REPAIRED-DOC; cotejo pendiente |
| A-02 | `bigint` PG no contiene UINT64 | **v2**: `numeric(20,0)` **con CHECK 0 ≤ v ≤ 18446744073709551615** en todas las columnas UINT64; `decided_at` timestamptz; wire = UINT64 LE limitado al dominio | DDL completo alineado | wire↔almacén | INV-08/12 | token 2^64−1 truncado a 2^63−1 ⇒ sink deriva mensaje obsoleto; r2 almacena entero exacto | A-26 | REPAIRED-DOC CONDICIONADO (D-R2R2-7) |
| A-03 | head pointer sin FK y CHECK contradictorio | **v2**: `current_attempt_id` **NULL solo antes del primer claim**; estados separados: `NOT_CLAIMED`(od=NOT_EVALUATED, head NULL) y `HEAD_PUBLISHED`(od≠NOT_EVALUATED, head NOT NULL); CHECK `od='NOT_EVALUATED' ↔ current_attempt_id IS NULL`; FK `operation.current_attempt_id → attempt(attempt_id) DEFERRABLE INITIALLY DEFERRED` | DDL corregido | creación; claim | INV-17; INV-03 | operación nacida v=OPEN con head NULL rechazada por CHECK | A-02/A-21 | **BLOCKED** (contradicción aún no validada en DDL real) |
| A-04 | manifiesto sin vínculo ni orden de creación | **v2**: creación `(operation, manifest)` **en una tx** con cross-check `manifest.manifest_hash == computed(ManifestHash)`; FK `manifest.operation_id → operation DEFERRABLE INITIALLY DEFERRED`; trigger BEFORE INSERT en `manifest` que verifica `computed == NEW.manifest_hash`; INV-12 derivada | DDL + tx rules | creación operación | INV-12 | operation con manifest_hash ≠ manifest sellado ⇒ tx aborta | A-02/A-05 | **BLOCKED** (mecanismo trigger sin especificar en v2) |
| B | sink no atómico vs externo (HP-4 falso) | **v2 protocolo de 2 fases con frontera confiable**: (F1) sink FOR UPDATE + revalidación + `INSERT ES-001 INTENT_DURABLE` durable; (F2) llamada externa con **capability firmada por W**, idempotency-key derivada de `(operation_id, effect_ordinal, attempt_id)` **vinculada al payload_hash**; proveedor confiable rechaza fencing obsoleto por `min_valid_fence` por scope; (F3) registro del resultado; crash F1–F3 ⇒ reconciliador resuelve por consulta provider-side; proveedor no confiable o no consultable ⇒ ES-007 + SC-002; **key sin reuso de payload** (mismatch ⇒ rechazo); suspend mientras hay intent ⇒ revocación: no se llama; intent queda ES-007 final; **proveedores sin idempotency**: frontera = sink; reconciliación obligatoria | `effect_log` (propuesta); `attempt`; `manifest` | dispatch; commit; recovery | INV-05; INV-10 | sink arrestado invoca efecto tras T-SUSPEND ⇒ proveedor confiable rechaza por fence; caso proveedor tonto ⇒ ES-007 + SC-002 prohíbe reintento | A-12/A-15/A-21; HP-4 corregido | **BLOCKED** (diseño de boundary sin validar con B-04/B-08) |
| C | `T-CLOSE` cierra ops con efectos pendientes | **v2**: precondición explícita de cierre: **ningún efecto en `{ES-001, ES-002, ES-003, ES-004, ES-007-pendiente}`**; cierre implica estados terminales o reconciliados; `v` se cierra en ops previamente suspendidas Y ops OPEN en contexto confirmado de efectos terminados; fence bump `minimum_valid_fence := GREATEST(minimum_valid_fence, next_fence) + 1` en misma tx; **T13 comparte precondición** (§2-B/D) | DDL + tx | T-CLOSE; T13 | INV-16; INV-03; INV-19 | op con `INTENT_DURABLE` + T-CLOSE ⇒ abortado | A-14/A-08 | **BLOCKED** (efectos pendientes no resueltos) |
| D | `T13` sin protocolo completo | **v2**: protocolo normativo completo: precondición (decisión humana durable, decision_id UNIQUE, scope no HUMAN_CLOSED); una tx; insert consumed_decision; row lock; fence bump explícito; suspend masivo `v: OPEN→SUSPENDED`; `si:=HUMAN_CLOSED`; insert `scope_event{HUMAN_CLOSED}`; COMMIT; crash ⇒ rollback total; HP rows; tests A-14 | DDL; tx | T13 | INV-16; INV-19 | crash entre fence bump y suspend ⇒ rollback total; ningún cierre parcial | A-14 | **BLOCKED** (misma precondición C) |
| E | firma reapertura incompleta (preimagen ambigua; salt) | **v2**: unificar §R2.r2.1.8/§R2.r2.4.2; **preimagen única exacta**: `payload := Tag('IER-consume-v1\0') ‖ encode(UINT8 kind ∈ {REOPEN, T13, CLOSE}) ‖ encode_bytes(scope_id) ‖ encode(UINT64 scope_epoch) ‖ encode(UINT64 opened_epoch) ‖ encode(UINT8 reason) ‖ encode_bytes(evidence_hash) ‖ encode_bytes(decision_id)`; firma Ed25519 sobre `payload` exactamente como bytes; **sin salt**; añadir `IER-consume-v1\0` al censo §0; correlación `reason`↔`scope_event.kind` y `evidence_hash`↔`scope_event.evidence_hash` garantizada por CHECK/TX; vectores de prueba positivos/negativos obligatorios (§5) | `reopen_evidence`; `consumed_decision` | T-REOPEN;T13;T-CLOSE | INV-15 | evidencia con `scope_epoch` correcto pero evento incorrecto (otro degradado) ⇒ rechazo | A-04/A-22/A-24 | **BLOCKED** (pendiente ratificación D-R2R2-9) |
| F | políticas incompletas (REJECTED ∉ ES; ALL vacío) | **v2 mapa veredicto→estado ES**: `VERIFIED→ES-005`; `REJECTED→(saga)→ES-006 o FAILED_CONSUMED`; `CONTRADICTION→scope CONTRADICTION`; **empty-manifest**: PL-002 y PL-003 con 0 efectos ⇒ `ABORT_DURABLE` obligatorio; PL-001: ninguna despacho jamás; encoding políticas siempre UINT8 wire ↔ smallint 0..2 DDL; fila policy type-table unificada; tests A-17/A-27 extendidos (caso vacío+ALL-fail) | `manifest.policy` | gates máquinas P | INV-18 | ALL-vacío acepta éxito vacuo; r2 ABORT_DURABLE | A-17/A-27 | REPAIRED-DOC CONDICIONADO |
| G | matriz §6.2 sin cobertura individual | **v2**: §3 de este documento asigna correspondencia **individual** a los 19 AUD (esta misma matriz); cada celda liga AUD→sección del baseline con predicado observable | — | trazabilidad | — | — | auditoría misma | **REPAIRED-DOCUMENTAL LIMITADO** (no demuestra reparación del baseline) |


## 6-B. Hallazgos de la auditoría de v1 (C-01…C-19) — causas, reparaciones diseñadas, pruebas discriminantes

| C | Defecto | Reparación diseñada (v2) | Porqué resuelve | Prueba discriminante | Estado |
|---|---|---|---|---|---|
| C-01 | CHECK A-03 contradice creación sin intento | Estados separados `NOT_CLAIMED`/`HEAD_PUBLISHED`; CHECK `od='NOT_EVALUATED' ↔ current_attempt_id IS NULL`; no se asume operación reclamada sin intento | Elimina contradicción operación-vacía vs CHECK | Inserción op NULL-od/NULL-head pasa; claim publica; head huérfano rechazado | REPAIRED-DOC → cotejo pendiente DDL |
| C-02 | Idempotency-key ≠ fencing | Protocolo 2 fases: intención durable + llamada con **capability W firmada** (payload + fence + epoch); proveedor confiable rechaza fence obsoleto (por scope) y idempotency-key con payload distinto; proveedor no confiable ⇒ frontera = sink + ES-007 + SC-002; casos: sin idempotency, key caducada, key+payload distinto, proveedor no consultable, crash post-efecto, suspensión con intent pendiente | Propaga rechazo de órdenes obsoletas al boundary efectivo; cubre todos los casos enumerados | A-21: proveedor confiable rechaza capability con fence < mínimo; A-12: crash entre intención y dispatch | **BLOCKED** (requiere B-04/B-08) |
| C-03 | Cierre masivo sin calificar efectos | Precondición de cierre explícita: **cero efectos en `{ES-001…004, ES-007}`**; cierre exige terminalidad o reconciliación; intent pendiente ⇒ no cierre | Elimina «v=CLOSED» cosmético con intención no ejecutada | op con `ES-001` + T-CLOSE ⇒ aborta con efecto pendiente | **BLOCKED** (pertenece a diseño de estados, requiere auditoría) |
| C-04 | Preimagen firma reapertura ambigua | §6-B/E: preimagen única `Tag ‖ kind ‖ scope_id ‖ scope_epoch ‖ opened_epoch ‖ reason ‖ evidence_hash ‖ decision_id`; firma Ed25519 sobre `payload` exacto; **cardinalidad exacta de encoding** (bytes LE declarados por campo); vectores pos/neg obligatorios; correlación `scope_event.evidence_hash == evidence_hash` obligatoria | Elimina ambigüedad de campos y correlación epoch/evento | Vector positivo reproduce firma; vector alterado falla; evidencia sin correlation ⇒ rechazo | **BLOCKED** (pendiente D-R2R2-9) |
| C-05 | `numeric(20,0)` no impone UINT64 | `CHECK (0 ≤ v ∧ v ≤ 18446744073709551615)` en todas las columnas UINT64; pruebas de límites (0, 2^63−1, 2^63, 2^64−1) | Representación cerrada con dominio exacto | Límites almacenados exactos; valores fuera ⇒ rechazo | REPAIRED-DOC (sujeto a D-R2R2-7) |
| C-06 | `fence-window` circular y sin eventos | Definición operacional: `min_valid_fence(scope)` evoluciona por `SETTLE` monótono; un mensaje con token `t` es válido en sink ⇔ `t ≥ min_valid_fence(scope, now)` leído en la tx del sink; `fence-window(scope, t)` no existe como sustituto; no es intervalo temporal; es fence entero; revocación es atómica por fila | Elimina nombre circular; la validez se decide en una operación atómica | Mensaje con token agotado tras T-SUSPEND ⇒ rechazo inequívoco | REPAIRED-DOC (sujeto a §2-B/H-25) |
| C-07 | `BND` terminación sin grafo comprobado | Lema finito: universo U finito; operador `Φ(S) = S ∪ deps(S)` monótono; iteración estrictamente creciente mientras S insatisfecho; pasa de 1 a lo sumo |U| pasos; ciclos sin límite (finito); desconocidos ⇒ BLOCKED | Terminación demostrable sin acíclicidad | Exhaustivo en grafo cíclico artificial | REPAIRED-DOC (sujeto a M-05) |
| C-08 | H-05 adquisición lock ≠ commit | LP formalizado: secuencia `lock → valid → fence-effect (verify) → commit`; abort tras lock ⇒ no efecto; precedencia observable viene de la fila de orden; abort tras confirmación externa ⇒ reconciliación | Distingue orden de serialización vs durable | Sink adquiere lock, aborta; T-SUSPEND procede; ningún efecto producido | A-12/A-15 | REPAIRED-DOC → cotejo pendiente (B) |
| C-09 | Append-only ≠ inmutabilidad | Append-only declarado con **rol de escritura única** (sink/W) + `INSERT`-only ACL + trigger UPDATE/DELETE reject + hash-chain por fila; verificación periódica de hash chain recompute | Inmutabilidad efectiva, no solo declarativa | UPDATE directo rechazado por trigger; hash chain fractura ⇒ verificación fallo | A-02; A-21 | REPAIRED-DOC → cotejo pendiente |
| C-10 | CAS H-04 sin predicado completo | Predicado completo: `UPDATE … SET current_attempt_id = new, current_attempt_generation = inc WHERE operation_id=:op AND current_attempt_generation=:expected RETURNING attempts;` Filas=1 ⇒ publica; 0 ⇒ abort | Materializa comparación efectiva | dos claims simultáneos ⇒ exactamente uno tiene RETURNING≠∅ | A-02/A-15 | REPAIRED-DOC |
| C-11 | `consumed_decision` protocolo incompleto | Tabla de consumo por transición: `{T-SUSPEND, T-REOPEN, T13, T-CLOSE, RECONCILE}`; cada una convoca INSERT con su `consumed_by`; doble consumo en la misma transacción ⇒ abort; scope vinculado en la fila; regla de consumo documentada por fila | Cierra ámbito de unicidad universal | T-SUSPEND y T-CLOSE concurrentes con mismo decision_id ⇒ uno gana, otro aborta | A-13 | REPAIRED-DOC |
| C-12 | Reconciliación sin orden | Orden parcial explícito por clave `(operation_id, effect_ordinal, attempt_id, decision_id)`; empate⇒CONTRADICTION; no se afirma orden total global; solo orden lexicográfico por decision decisiva por efecto | Evita afirmación falsa; contradicción detectada | Dos veredictos simultáneos mismo efecto ⇒ contradicción | A-07/A-23 | REPAIRED-DOC → cotejo pendiente H-17 |
| C-13 | REJECTED/FAILED_CONSUMED/ES-006 relación incompleta | Mapa Cerrado de políticas vs estados: `VERIFIED→ES-005`; `REJECTED + saga aplicada→ES-006`; `REJECTED + sin compensación→FAILED_CONSUMED`; `CONTRADICTION→scope CONTRADICTION`; terminalidad definida explícita para cada estado | Cierra transiciones terminales | compensation confirmada ⇒ ES-006 | saga incompleta ⇒ FAILED_CONSUMED | A-17 | REPAIRED-DOC → cotejo pendiente H-18 |
| C-14 | Cobertura de sinks no demostrada | Todo adapter de efecto externo en whitelist única (SinkExecutor); CI scan falla fuera; A-19/A-20; listado reproducible del censo | Cobertura verificable y no asumida | adapter nuevo no registrado ⇒ build falla | A-03-v2/A-19 | **BLOCKED** (sin implementación ejecutable aún) |
| C-15 | A-04 trigger sin especificar | Trigger `BEFORE INSERT/UPDATE ON manifest`: `PERFORM assert_manifest_hash_equal(NEW.manifest_hash, NEW.effects_canon, NEW.manifest_version, NEW.policy, NEW.scope_epoch, NEW.operation_id, NEW.policy_version)`; fn `assert_manifest_hash_equal` recomputación LS + comparación exacta; falla ⇒ excepción | Cierre real del `operation.manifest_hash ↔ manifest.manifest_hash` | operación insertada con hash distinto del manifest ⇒ excepción | A-02/A-05 | REPAIRED-DOC → cotejo pendiente DDL |
| C-16 | idempotency-key sin vínculo a payload | idempotency-key = `H(Tag('IER-effect-idem-v1\0') ‖ encode_bytes(operation_id) ‖ encode_bytes(attempt_id) ‖ encode(UINT16 effect_ordinal) ‖ encode_bytes(payload_hash))`; mismatch payload ⇒ provider rechaza | Vincula clave con contenido real | misma operación+ordinal, payload distinto ⇒ rechazo provider-side | A-12/A-15/A-21 | REPAIRED-DOC |
| C-17 | H-27 terminación por altura no probada | Lema finito por cardinalidad (C-07) | Terminacion sin exigir acíclicidad | grafo cíclico artificial converge | A-09 | REPAIRED-DOC (sujeto a §2-B/H-27) |
| C-18 | LP ≠ commit durable (H-05) | LP formalizado en C-08; adquisición lock no equivale a efecto durable; precedencia observable = commit de `effect_log` o commit del scope row | Comprobar LP con abort evidencia | sink lock+abort ⇒ T-SUSPEND gana | A-12/A-15 | REPAIRED-DOC |
| C-19 | Append-only autoridad efectiva | Rol de sólo-escritura única para tablas selladas; hash-chain verificada periódica; A-20 ACL; A-02 verificación | Inmutabilidad real, no declarada | escritura por autoridad no designada ⇒ denegación | A-02/A-20 | REPAIRED-DOC → cotejo pendiente DDL |


---

## 7. Decisiones D-R2R2 — tras dictamen (estado reflejado, no propuesto)

| # | Decisión | Estado (dictamen) | Estado tras esta revisión |
|---|---|---|---|
| D-R2R2-1 | PKI y autoridad Ed25519 | Pendiente; faltan revocación, rotación, custodia, validación del verificador | **BLOCKED** hasta especificación de confianza, revocación, rotación y custodia de claves |
| D-R2R2-2 | Autoridad de fencing | BLOCKED — B-04 | **BLOCKED** — no cerrable desde la matriz; requiere B-04 |
| D-R2R2-3 | `T-CLOSE` sobre scope sano | BLOCKED — efectos pendientes | **BLOCKED** — precondición nueva: cero efectos pendientes (§6-B/C-03/D) |
| D-R2R2-4 | `claim_generation` UINT64 | Pendiente | **REPAIRED-DOC CONDICIONADO** — ancestral de H-19; requiere coherencia global UINT64 (D-R2R2-7) |
| D-R2R2-5 | Tag de dominio `IER-consume-v1` | Pendiente | **REPAIRED-DOC CONDICIONADO** — preimagen cerrada §6-B/C-04 sellada |
| D-R2R2-6 | Toolchain A-19 | Diferida | **DIFERIDA** a apertura formal de R3 |
| D-R2R2-7 | Representación UINT64 | `numeric(20,0)` adecuada con `CHECK 0..2^64−1` | **REPAIRED-DOC CONDICIONADO** — `bigint` descartado como UInt64 |
| D-R2R2-8 | FKs circulares | `DEFERRABLE INITIALLY DEFERRED` posible; no resuelve A-03 | **BLOCKED** — A-03 requiere estados separados (§6-B/C-01); FK diferida unida al CREATE TABLE |
| D-R2R2-9 | Preimagen firma cierre | BLOCKED | **BLOCKED** — §6-B/C-04/E define preimagen exacta; ratificación pendiente |
| D-R2R2-10 | Vínculo manifiesto↔operation | Pendiente | **REPAIRED-DOC CONDICIONADO** — mecanismo trigger exacto §6-B/C-15 |
| D-R2R2-11 | REJECTED como veredicto ligado | Pendiente | **REPAIRED-DOC CONDICIONADO** — mapa completo de estados §6-B/C-13 |

## 8. Incompatibilidades, límites críticos y propagación

1. **§1 (FROZEN)** contradicción: `CANONICAL_DEPENDENCY_BLOCKED` (FG-003). Ninguna fila derivada puede declararse lista sin resolver §1 con dictamen documental.
2. **Independencia de terceros:** no simulable; todo `UNKNOWN` y toda reconciliación exige verificador independiente. Terceros `NOT_EXECUTED`.
3. **B-03 / B-04 / B-08 (`OPEN`)**: autoridad de fencing y rotación en B-04; no cerrable aquí.
4. **Atomicidad externa:** imposible sin cooperación provider-side; garantía mínima exigible = intención durable + capability W + idempotency-key + reconciliación obligatoria. Estricta no existe.
5. **PKI externa:** Ed25519 es propuesta; revocación, rotación y custodia pendientes.
6. **Regla de propagación (vinculante):** toda fila dependiente de un límite `OPEN`/`BLOCKED` hereda el bloqueo hasta el cierre del límite. En la práctica este documento declara `BLOCKED` a: H-05, H-06, H-13, H-14, H-15, H-17, H-18, H-23, H-24, H-25, AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019, A-03, A-04, B, C, D, E, F, M-02…M-05, M-07, M-10. No sustituyen ni se disfrazan de `REPAIRED-DOCUMENTAL`.

## 9. Procedimiento posterior (NO autorizado aún; bloqueado hasta ratificación)

```
1. Propietario audita esta revisión v2.
2. Dictamen por fila; anotación en registro.
3. Si se aprueba procedimiento: regeneración completa de B07-R2-Repair-Specification.md
   como r3 incorporando únicamente lo ratificado.
4. r3 pasa a auditoría independiente.
5. B07_FORMAL_MODEL.md no se modifica hasta autorización separada.
6. R3 no se abre.
```

## 10. Estado y procedencia

- Revisión v2 de la matriz consolidada. **Sustituye a v1 para efectos de auditoría**, cuya copia íntegra se conserva (`B07-R2-Consolidated-Repair-Matrix-v1-audited.md`, sha256 `e165aced…`).
- v2.r2 intacta: `9c8a0aba…` · `B07_FORMAL_MODEL.md` `a7273d58…` · §1 `74a19ba2…`.
- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `D-315 = PENDING` · `MODEL_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · `PROMOTION = NOT_READY`.
- Inventario corregido: **75** (27 H + 19 AUD + 9 RES + 10 M + 10 nuevos). Añadidos C-01…C-19 como hallazgos de auditoría de v1. Total de filas: 94.
- Ningún estado de esta matriz declara cierre. La aceptación es exclusivamente del propietario.
- Procedencia: `state/multiproject/log.md`; auditoría del diseñador 2026-11-15 con dictamen aplicado.

Fin matriz consolidada R2-A — REVISIÓN 2 · DRAFT / NOT_ACCEPTED · Procedencia en `state/multiproject/log.md`.
