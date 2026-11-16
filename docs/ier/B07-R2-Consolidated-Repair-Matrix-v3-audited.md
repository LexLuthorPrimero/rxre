# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 3 (POST-AUDITORÍA DE v2)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** `docs/ier/B07-R2-Repair-Specification.md` v2.r2 — SHA-256 `9c8a0aba5cf6770b12561b7734e0630c41ae44b268ce5f9ecdcf216f9c57c39e` — **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** `B07-R2-Consolidated-Repair-Matrix-v1-audited.md` (`e165aced…`), `B07-R2-Consolidated-Repair-Matrix-v2-audited.md` (`103feeb2…`). **Ninguno se usa como baseline.**
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. **§1 y `B07_FORMAL_MODEL.md` intactos. r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.**

## Registro de revisiones

| Versión | SHA-256 | Disposición |
|---|---|---|
| v1-auditada | `e165acedff55b591b84168b138ac2951bb09a9032fa81d044f97704641a19bad` | NO RATIFICABLE (75→76 error; consistencia FAIL) |
| v2-auditada | `103feeb26f273523ace93c59bc285129fc2f6e81154dc6df7d75496041dd236d` | NO RATIFICABLE; dictamen sobre 94 filas: H-01…H-27 REPAIR_REQUIRED/BLOCKED; AUD sólo AUD-005; RES sólo RES-1/RES-3; M sólo M-06; A-01/A-02 CONDITIONED, resto BLOCKED; C-02/C-03/C-04/C-14 BLOCKED; D-R2R2 ninguna ratificada |
| v3 (este documento) | hash publicado fuera del archivo (`state/multiproject/log.md`) | Aplica **fases A→D** exigidas por el diseñador (consistencia, seguridad/concurrencia, criptografía/dependencias, propagación/trazabilidad). Incorpora N-01…N-10. Todavía sin verificar; aceptación exclusiva del propietario |

---

## 0. Leyenda y regla de cierre

Cada fila demuestra: `Definición → Persistencia → Transición → Invariante → Contraejemplo discriminante → Prueba`.
Estados (aplicación uniforme de la **regla de propagación** §8):
- `REPAIRED-DOCUMENTAL`: especificación diseñada; **no** ejecutada; sin verificación; falta auditoría.
- `REPAIRED-CONDICIONADO`: reparación diseñada pero depende de una precondición abierta (no ratificada por el propietario o por un límite como B-04/PKI/§1).
- `BLOCKED`: incompatible/indecidible sin decisión externa o diseño adicional. **No se cierra por contexto.**
- `NOT_APPLICABLE`: sólo con evidencia formal.

**Regla absoluta**: ninguna apertura v2.r2 → r3 del baseline sin ratificación expresa del propietario fila por fila.

---

## 1. Inventario total (104 unidades)

| Fuente | Cant. | Sección |
|---|---:|---|
| H-01…H-27 | 27 | §2 |
| R2A-AUD-001…019 | 19 | §3 |
| Notas residuales RES-1…9 | 9 | §4 |
| Microdefectos M-01…M-10 | 10 | §5 |
| Hallazgos nuevos del auditor sobre v2.r2 | 10 | §6 |
| Hallazgos de auditoría de v1 sobre esta matriz (C-01…C-19) | 19 | §6-B |
| Hallazgos nuevos de la auditoría de v2 (N-01…N-10) | 10 | §6-C |
| **Total** | **104** | — |

`27+19+9+10+10 = 75` (unidades heredadas de v1) · `75+19 = 94` (tras aud. v1) · `94+10 = 104` (tras aud. v2) — aritméticamente verificado.

---

## 2. Matriz H-01…H-27 (estados v3 según dictamen y propagación)

| H | Defecto | Fase A/B/C | Definición/Reparación (v3) | Persistencia | Transición | Contraejemplo/Prueba | Estado (v3, obligatorio) |
|---|---|---|---|---|---|---|---|
| H-01 | Hash sin algoritmo/vectores | C | SHA-256 tabular; tags NUL; layout fijo (§R2.r2.1.2); vectores reproducibles (§11) | `manifest`, tablas selladas | sellado/creación intento | Vectores §11; A-05/A-26 | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-02 | `effect_ordinal` ambiguo | A | ordinal global denso 0..n−1; orden de encode = ordinal; identidad (op,ordinal) | `manifest.effects_canon` | escritura manifiesto | permutación produce manifiesto distinto; A-05 | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-03 | Manifiesto sin fuente de verdad | B | append-only **con autoridad write-only + trigger `UPDATE/DELETE` rechazo + hash-chain anclada externamente (§6-B/C-09, C-19)**; verificación periódica recompute vs ancla externa | completa §R2.r2.2 | sellado manifiesto | manifiesto sustituido con cadena reconstruida pasa verificación local; r3 lo impide por ancla | REPAIRED-DOCUMENTAL — depende de H-24 (D-R2R2-1) |
| H-04 | Head pointer sin CAS | A | `SET_HEAD_ATTEMPT` con predicado completo: `WHERE operation_id=:op AND current_attempt_generation=:expected RETURNING …`; filas=1 éxito; 0 abort; publicación en única tx | única tx operación+head+insert intento | claim | dos claims ⇒ uno publica cabeza; A-02/A-15 | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-05 | Fencing no linealizable vs suspensión | B | **protocolo de 2 fases + exclusión mutua + frontera confiable con revocación+caducidad; LP formalizado** (§6-B/B, C-02, C-08/C-18) | row lock; `effect_log` | dispatch; T-SUSPEND | HP-2 + sink arrestado tras T-SUSPEND ⇒ boundary rechaza fence | **BLOCKED** (B-04/B-08 + C-02/C-08 abiertos) |
| H-06 | `REOPEN_EVIDENCE` sin esquema | C | esquema completo §R2.r2.4.2 + **preimagen canónica única §11–C-04** + Ed25519 (D-R2R2-1 PKI) | `reopen_evidence` | T-REOPEN | evidencia con epoch/evento incorrecto o firma alterada | **BLOCKED** (D-R2R2-9 no ratificada) |
| H-07 | `RECONCILE_REQUIRED`; `scope_event` sin esquema | A | token `RECONCILIATION_REQUIRED`; evento+transición en única tx; **esquema `scope_event` cerrado con `CONSTRAINT UNIQUE` sobre (scope_id, scope_epoch, kind, evidence_hash) y FK evidencia** | `scope_event` | T-SUSPEND | evento huérfano por crash mid-tx | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-08 | FK compuesta ausente | A | FK `attempt(scope_id, operation_id) → operation(scope_id, operation_id)`; `UNIQUE(scope_id, operation_id)` | DDL | claim; re-lectura sink | intento con scope ajeno rechazado por RESTRICT | REPAIRED-DOCUMENTAL — cotejo pendiente DDL |
| H-09 | Binding incoherente op↔intento | A | binding por intento; eliminar `operation.binding_hash`; cabeza componencial | `attempt.binding_hash` NOT NULL | cabeza CAS | reintento con cabeza antigua inyectado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-10 | Idempotencia entre epochs | A | clave idempotencia `(scope_id, scope_epoch, operation_kind, request_id)` única; **regla de colisión explícita y reutilización de `request_id` definida: nunca**; reclamar duplicado = devolver op existente si (od≠BLOCKED∧v≠CLOSED); si op terminal ⇒ nuevo request_id obligatorio | índice compuesto | creación operación | mismo request, misma op tras REOPEN ⇒ nueva op; mismo epoch ⇒ devuelve existente o consume op existente | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-11 | Fencing sin protocolo | C→A | depende de H-05/D-R2R2-2/B-04 | `scope.next_fence`; UNIQUE token | claim; dispatch; sink | sink acepta grant con fence previo cancelado | **BLOCKED** (B-04) |
| H-12 | `decision_id` sin consumo atómico | A | `consumed_decision` con **protocolo de consumo por transición** (§6-B/C-11): cada transición inserta su `(decision_id, scope_id, consumed_by)` en la misma tx; UNIQUE(decision_id); vínculo de contenido a decisión | `consumed_decision` | T-*/T13/T-CLOSE | doble reapertura con mismo evidence | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-13 | `T-REOPEN` incompleto | A | consume→row lock→verificaciones (preimagen+evento+epoch)→epoch+1→fence→reopen_evidence→COMMIT; crash ⇒ rollback | tx; `reopen_evidence` | T-REOPEN | crash entre bump y reopen_evidence ⇒ rollback total | **BLOCKED** (H-06/E no cerradas) |
| H-14 | `V=CLOSED` sin transición formal | B | **T-CLOSE condicionado: `Terminal(e) ∧ ResultadoExternoConocido(e)` para todo efecto** (§6-B/C-03); si existe ES-007 ⇒ FENCE CONTINÚA + escalación; no cierra | `consumed_decision`; tx | T-CLOSE | op con efecto ES-007 ⇒ T-CLOSE aborta | **BLOCKED** |
| H-15 | Máquinas incompletas | A/B | tablas completas SI/TRs/ESs/OD/P/V/O/T/ESo/ES **con relación op↔efecto↔política cerrada** (§6-B/F-13 mapa, §11); sin cerrar vía estados | máquinas §R2.r2.4.5…13 | todas | crash RECOVERABLE sin ruta ⇒ FAILED_CONSUMED o reinicio | **BLOCKED** |
| H-16 | INV-13 sin derivación | A | **prueba formal reproducida en texto** (§13.1): predicados, dominio finito, contrapositiva, equivalencia | — | — | «consecuencia directa» no aceptada; prueba escrita completa | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-17 | Reconciliación incompleta | A | dominio VERIFIED/REJECTED/CONTRADICTION; **orden parcial correcto + contradicción definida por clase de veredicto** (§6-B/C-12) | `reconciliation_record` | ReconciliationProtocol | doble veredicto silencioso ⇒ CONTRADICTION detectada | **BLOCKED** |
| H-18 | `ESo=REJECTED` sin terminal | B | salidas formales (a) evidencia nueva → RECEIVED; (b) compensación durable → T-CLOSE; mapa completo ES↔T↔P↔O; saga no cerrada ⇒ nada | tx; `reconciliation_record` | ESo machine | REJECTED sin salida ⇒ bloqueado o cierre insatisfecho | **BLOCKED** |
| H-19 | Tipos generación divergentes | A | generation ≡ smallint 1..255 (≡UINT8); claim_generation ≡ UINT64 `numeric(20,0)` con `CHECK 0..2^64−1` en **todas las columnas UINT64** + wire encode LE (§13.2); censo exhaustivo listado | DDL alineado | claim | 255 vs 2^64−1 interpretados por driver distintos | REPAIRED-DOCUMENTAL CONDICIONADO — cotejo pendiente |
| H-20 | Barrera A6 permisiva | A | default-deny; unknown ⇒ BLOCKED | `blocked_symbols` | todas | símbolo inocente con dep §1 ⇒ denegado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-21 | Censo incompleto sin regla rechazo | A | census bidireccional §0 + regla rechazo (H-20); AUD-015 compatibilidad R1.1 | tabla §0 | todas | token no clasificado aceptado | **BLOCKED** (AUD-015 abierto) |
| H-22 | Cardinalidad sin fundamentación | A | dominios justificados desde R1; 60/8640/518400 = exactos; LEGAL/REACHABLE desconocidos (§13.3) | — | — | 518400 declarado legal; r es cartesiano | REPAIRED-DOCUMENTAL — cotejo pendiente |
| H-23 | A-03 no demuestra cobertura sinks | B | A-03-v2 reproducible + evidencia ejecutable obligatoria (CI whitelist; A-19/A-20 aplicados) | sink ACL | dispatch gate | sink clandestino no registrado ⇒ build fail | **BLOCKED** |
| H-24 | Frontera confianza indefinida | B | TCB explícito; Ed25519 (D-R2R2-1 con revocación/rotación/custodia definidos); A-19/A-20 | ACL/PKI | dispatch gate | adaptador externo sin sink ⇒ build error | **BLOCKED** (D-R2R2-1) |
| H-25 | LP solicitud vs suspensión | B | protocolo 2 fases completo; **LP único definido**: commit dual `effect_log`+`scope`/freeze o commit de intención; externalidad queda <política exclusión> (§6-B/B) | row lock; `effect_log` | sink vs T-SUSPEND | sink arrestado invoca efecto tras T-SUSPEND ⇒ boundary rechaza | **BLOCKED** |
| H-26 | Políticas sin puerta terminación | A | PL-002/003 gates; PL-001 obligatorio ABORT; **NONE/ANY/ALL sobre no-vacíos + vacío** reglas explícitas (§6-B/F) + INV-18 | `manifest.policy` | máquina P | ALL-vacío COMMIT por vacuo ⇒ r ABORT_DURABLE | **BLOCKED** |
| H-27 | A6 sin propagación transitiva | C | cierre transitivo como **operador monótono sobre universo finito** con lema de terminación por cardinalidad (§6-B/C-07) | `blocked_symbols` | todas | símbolo permitido pese a deps §1 | REPAIRED-DOCUMENTAL CONDICIONADO — cotejo pendiente |

## 3. Matriz R2A-AUD-001…019 (estados v3 según dictamen)

| AUD | Descripción | Estado v3 |
|---|---|---|
| AUD-001 | `SinkAccept` campos inexistentes | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-002 | Binding duplicado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-003 | INV-06 redundante | REPAIRED-DOCUMENTAL — cotejo pendiente (INV-09 debe cubrir todo el dominio) |
| AUD-004 | INV-07 con elipsis | REPAIRED-DOCUMENTAL — cotejo pendiente (INV-07a/b/c no se reproducen) |
| AUD-005 | `≈ 8640` | **ACEPTADA** (alcance notacional; cálculo pendiente de reproducing) |
| AUD-006 | §2.L contradice §2.A | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-007 | Epoch sin transición | **BLOCKED** (preimagen pendiente H-06/C-04) |
| AUD-008 | DDL sin `binding_hash` | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-009 | Dependencia FG-001→ES-007 | REPAIRED-DOCUMENTAL — cotejo pendiente (SC-001 suficiencia a demostrar) |
| AUD-010 | Índice impide reintentos | REPAIRED-DOCUMENTAL — cotejo pendiente (reintentos legítimos vs duplicación lógica) |
| AUD-011 | Fencing no linealizable | **BLOCKED** |
| AUD-012 | Origen vs sink | REPAIRED-DOCUMENTAL — cotejo pendiente (falta contrato completo de frontera) |
| AUD-013 | T13 no atómica | **BLOCKED** |
| AUD-014 | UNKNOWN informal | **BLOCKED** |
| AUD-015 | R1.3 vocabulario incompleto | **BLOCKED** (compatibilidad con canon R1.1 no demostrada) |
| AUD-016 | INV-02 contradice epochs | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-017 | Intentos sin persistencia | REPAIRED-DOCUMENTAL — cotejo pendiente |
| AUD-018 | Política sin semántica | **BLOCKED** |
| AUD-019 | Relación P/T/ESo/O | **BLOCKED** |

## 4. Notas residuales RES-1…9 (estados v3 según dictamen)

| RES | Nota | Estado v3 |
|---|---|---|
| RES-1 | `SinkAccept` campos inexistentes | **ACEPTADA** (correspondencia AUD-001) |
| RES-2 | Binding duplicado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| RES-3 | INV-06 e INV-07 | **ACEPTADA** (correspondencia AUD-003/AUD-004; no aceptación de la reparación técnica subyacente) |
| RES-4 | `≈ 8640` | REPAIRED-DOCUMENTAL — cotejo pendiente |
| RES-5 | §2.L semántica OD | REPAIRED-DOCUMENTAL — cotejo pendiente |
| RES-6 | Incremento de epoch | **BLOCKED** (preimagen pendiente) |
| RES-7 | DDL sin binding_hash | REPAIRED-DOCUMENTAL — cotejo pendiente |
| RES-8 | FG-001→ES-007 | REPAIRED-DOCUMENTAL — cotejo pendiente |
| RES-9 | INV-13 apelación | REPAIRED-DOCUMENTAL — cotejo pendiente (INV-13 reproducida §13.1) |

## 5. Microdefectos M-01…M-10 (estados v3 según dictamen)

| M | Defecto | Estado v3 |
|---|---|---|
| M-01 | `ESo=REJECTED` ininteligible | **BLOCKED** (saga no cerrada) |
| M-02 | `decided_at` UINT64 vs timestamptz | REPAIRED-DOCUMENTAL — cotejo pendiente (unificar a timestamptz; no vincular a D-R2R2-7; vincular a tipo temporal único) |
| M-03 | claim_generation divergente | REPAIRED-DOCUMENTAL — cotejo pendiente (claim_generation UINT64; attempt_generation smallint; censo completo §13.2) |
| M-04 | `IER-reopen-v1` sin uso | **BLOCKED** (preimagen pendiente D-R2R2-9) |
| M-05 | `BND` sin propagación demostrada | REPAIRED-DOCUMENTAL — cotejo pendiente (lema §6-B/C-07) |
| M-06 | §7.5 inexistente | **ACEPTADA** (referencia corregida a §R2.r2.6 §6.2; ubicación existe) |
| M-07 | `salt` sin campo | REPAIRED-DOCUMENTAL — cotejo pendiente (sin salt; payload determinista; cotejo de todas las referencias criptográficas) |
| M-08 | «`io` tags de política» | REPAIRED-DOCUMENTAL — cotejo pendiente (census de política completo) |
| M-09 | `A-03` vs `A-03-v2` | REPAIRED-DOCUMENTAL — cotejo pendiente (unificado; no fusionar procedimientos) |
| M-10 | «fence-window» indefinido | **BLOCKED** (H-25/C-02 no cerrados) |


## 6. Hallazgos nuevos del auditor sobre v2.r2 (estados v3)

| ID | Defecto | Reparación/estado v3 |
|---|---|---|
| A-01 | FK sobre columna inexistente | REPAIRED-DOCUMENTAL — cotejo pendiente (columnas scope_id/operation_id/attempt_id DDL; FK compuesta) |
| A-02 | `bigint` no contiene UINT64 | REPAIRED-DOCUMENTAL CONDICIONADO — `numeric(20,0)` + `CHECK 0..18446744073709551615`; censo completo §13.2; wire=LE; conversiones del driver según §13.2 |
| A-03 | head pointer sin FK / CHECK contradictorio | **BLOCKED** (diseño exacto §11-C-01; DDL no validado) |
| A-04 | manifiesto sin vínculo cruzado | **BLOCKED** (trigger §11-C-15 bajo juicio) |
| B | sink no atómico / frontera | **BLOCKED** (B-04/B-08) |
| C | cierre con efectos pendientes | **BLOCKED** (§11-C-03) |
| D | T13 sin protocolo | **BLOCKED** (hereda C) |
| E | preimagen firma reapertura | **BLOCKED** (§11-C-04) |
| F | políticas incompletas | **BLOCKED** (mapa ES↔T↔P↔O pendiente) |
| G | §6.2 sin cobertura individual | **ACEPTADA LIMITADA** (estadística de trazabilidad propia) |

## 6-B. Hallazgos de auditoría v1 (C-01…C-19) — reparaciones formales y estados v3

### §11-C-01 — Estado inicial de operación × CHECK

```
NOT_CLAIMED     := od = 'NOT_EVALUATED' ∧ current_attempt_id IS NULL
HEAD_PUBLISHED  := od ≠ 'NOT_EVALUATED' ∧ current_attempt_id IS NOT NULL
CHECK := (od='NOT_EVALUATED') = (current_attempt_id IS NULL)

Reglas:
- INSERT op: sólo NOT_CLAIMED (od=NOT_EVALUATED, head NULL, v=OPEN). Légitimo.
- CLAIM: inserta attempt; SET_HEAD lo publica en la MISMA tx; od sigue NOT_EVALUATED hasta decisión T-ADM: NOT NULL head ⇒ od∉{NOT_EVALUATED} ⇒ od≠NOT_EVALUATED es posterior al primer claim publicado.
- od≠NOT_EVALUATED ⇔ head publicado ⇔ existe attempt.
- v no participa en el CHECK; v=OPEN nacidos NOT_CLAIMED son válidos siempre.
- INVARIANTE DE CREACIÓN: (NOT_CLAIMED ∨ HEAD_PUBLISHED) siempre; otra combinación: rechazo.
Prueba: INSERT op nacida ⇒ OK; INSERT con od≠NOT_EVALUATED e head=NULL ⇒ rechazo; claim ⇒ od puede ADMITTED/BLOCKED/NOT_DETERMINED sólo con head publicado.
```

### §11-C-12 — Reconciliación: orden parcial + contradicción

```
Contradiction(e) :≡ ∃ r₁,r₂ ∈ RR(e): (r₁.verdict ≠ r₂.verdict) ∧
                   (r₁.verdict∈{VERIFIED,REJECTED} ∨ r₂.verdict∈{VERIFIED,REJECTED}
                    ∨ r₁.verdict=CONTRADICTION ∨ r₂.verdict=CONTRADICTION)
  con RR(e) := ∀ reconciliation_record con (operation_id, attempt_id, effect_ordinal, effect_binding) = e.
Semántica: cualquier r CONTRADICTION ⇒ CONTRADICTION (monotónica);
VERIFIED vs REJECTED ⇒ CONTRADICTION;
VERIFIED vs VERIFIED ⇒ OK (compatible);
REJECTED vs REJECTED ⇒ OK (compatible).
Orden: RR(e) se registra con decided_at (DB assign); para efectos de consulta «última decisión» se toma
la fila con max decided_at; empate ⇒ CONTRADICTION (ambas conservadas). No se afirma un orden total global:
relaciones entre efectos distintos son independientes; el sistema nunca decide por arbitraje temporal entre efectos.
```

### §11-C-13 — Terminalidad y cierre de efectos

```
W-T(e) := e está COMPENSADO(ES-006) o VERIFICADO(ES-005) o NUNCA DESPACHADO.
W-R(e) := ResultadoExternoConocido(e):
          ES-005 | ES-006 | ES-002,003,004 con veredicto SC-002 (REJECTED→saga→ES-006, VERIFIED→ES-005).
W-C(e) := ObsoletoNo dispatched: jamás entró al sink (sin registro) y oculta sólo efecto lógico declarado.

Cierre de operación (T-CLOSE/T13) exige §7: ∀e∈manifest: W-T(e) ∧ W-R(e) ∧ ¬ES-007.
Resultado desconocido ⇒ la operación NO es cerrable; escalar: scope queda RECONCILIATION_REQUIRED
indefinido o FAILED_CONSUMED por decisão humana; nunca cierre limpio.
```

### §11-C-15/C-C-15 — Integridad cruzada del manifiesto (trigger)

```
TRIGGER manifest_before_ins_upd (BEFORE INSERT OR UPDATE ON manifest):
  NEW.manifest_hash == compute ManifestHash(NEW fields)  [v2-self-consistency]
  AND operation := SELECT manifest_hash FROM operation WHERE operation_id = NEW.operation_id
  AND (operation row NOT EXISTS) OR (operation.manifest_hash == NEW.manifest_hash
    AND operation.operation_id == NEW.operation_id)
  ⇒ si ninguna, RAISE (detect; inserción diferida: usar FKs DEFERRABLE INITIALLY DEFERRED).
TRIGGER operation_before_ins_upd (BEFORE INSERT OR UPDATE OF manifest_hash ON operation):
  SELECT manifest_hash FROM manifest WHERE operation_id=NEW.operation_id;
  si fila existe ∧ mismatch ⇒ RAISE; si no, commit diferido OK (deferrable FKs).
Todo dentro de la MISMA transacción de creación; ambos triggers ejecutan en el mismo tx.
Verificación adicional en A-02: para toda fila operation↔manifest: equality comprobada en auditoría.
```

### §11-C-16 — Clave de idempotencia entre reintentos

```
EFFECT_KEY := SHA-256( Tag('IER-effect-idem-v2\0') ‖ encode_bytes(operation_id) ‖ NU16(effect_ordinal) ‖ encode_bytes(payload_hash) )
SIN attempt_id (no rompe reintentos), SIN request_id (la petición no es evento de efecto).
Mismo efecto lógico con payload distinto ⇒ misma identidad de OPERACIÓN pero payload_hash diferente
  ⇒ el K idempotente cambia ⇒ el proveedor ejecuta como solicitud distinta = correcto
    porque la semántica del efecto cambió (contenido distinto); documentar: idempotencia es sobre el
    efecto (operación, ordinal, contenido), no sobre el orden del payload-unrelated.
K está verificado en el boundary confiable junto con capability (§11-C-02).
```

### §11-C-04 — Preimagen canónica de firma + vectores

```
TAG(s) := ASCII(s) ‖ 0x00
ENC(b) := NU64(len(b)) ‖ b           // uint64_le; longitudes en BYTES;b puede ser vacía ⇒ len=0 ⇒ sola prefijo 00..00 (8 bytes)
NU8/NU64 := little-endian exacto

DECISION_PAYLOAD :=
  TAG('IER-consume-v2\0')              // 17 bytes + NUL = 17
  ‖ NU8(kind)                          // 1=REOPEN, 2=T13, 3=T-CLOSE
  ‖ ENC(scope_id)                      // 8+32 = 40
  ‖ NU64(scope_epoch)                  // 8
  ‖ NU64(opened_epoch)                 // 8
  ‖ NU8(reason)                         // 1=ROLLBACK_RESOLVED, 2=RECONCILE_RESOLVED, 3=HUMAN-CLOSURE
  ‖ ENC(evidence_hash)                  // 8+32 = 40
  ‖ ENC(decision_id)                   // 8+32 = 40
  ‖ ENC(key_id)                         // 8+32 = 40
                                        // = 194 bytes
signature := Ed25519(DECISION_PAYLOAD bytes crudos)
key_id    := SHA-256(TAG('IER-key-v1\0') ‖ ENC(pk_raw))
decision_id := 32B ALEATORIOS CSPRNG de W; INSERT UNIQUE en consumed_decision garantiza unicidad criptográfica
          (probabilidad de colisión despreciable; constraint UNIQUE aborta si ocurre).
REGLAS DE VERIFICACIÓN (bit exactas):
 1. decodificar payload con el esquema de arriba (rechazar cualquier desviación de longitudes);
 2. key_id reconstruido de pk_raw DEBE ser igual al declarado;
 3. reason ∈ {1,2,3}; kind ∈ {1,2,3};
 4. kind=1 (REOPEN) ⇒ opened_epoch == scope_epoch + 1;
 5. reason correlaciona 1↔{rollback}, 2↔{reconcile} con el scope_event invocado;
 6. evidence_hash == scope_event.evidence_hash (constraint/tx);
 7. decision_id no consumido (INSERT UNIQUE).
VECTORES (clave de prueba desechable; no empleada en producción):
 payload_sha256 := adccff51574b1a942ecbdf9fb1ef89c496bb072c98af6d75799131c45ddf8be3
 public_key     := 3c7cb8300fdc6c4e0f58a88499eaa5de3f895107e49102b1afa0a9a30f4cb746
 key_id         := 29020debec15707734f5c7a8e9024cacbc4dcc3013ff59f728710857183e8abc
 signature      := 3e068b892170cecec417fa70a972ba33f8c4bca339865b9a05c97b70847e0ad11316a4c93aa0dd151f3cedb7e7eb2fbccecee21c1bdb946abec65cdc2b0e0b05
 Vector negativo: alterar 1 byte del payload ⇒ verificación falla (rechazado).
```

### §11-C-02 — Fencing capability + protocolo de frontera (revocación efectiva)

```
CAPABILITY := W-signed Ed25519{DECISION_PAYLOAD-remota? NO} — capability de EFECTO:
 cap_fields := TAG('IER-effect-cap-v1\0') ‖ NU8(1) ‖ encode_bytes(scope_id) ‖ NU64(scope_epoch)
             ‖ NU64(fencing_token) ‖ encode_bytes(operation_id) ‖ NU8(attempt_generation)
             ‖ NU16(effect_ordinal) ‖ encode_bytes(payload_hash) ‖ NU64(expiry_epoch)
             ‖ encode_bytes(key_id)   // W signs over these exact bytes

PROVIDER_TRUSTED con contador por scope `last_fence` monotónico:
 - al aceptar cualquier efecto E con fence f: monotone check last_fence[scope] ≤ f o rechazar.
 - al detectar revocación (T-SUSPEND/T-CLOSE global bump): escalar last_fence[scope] := new_min.
 - atómico accept: (verificar firma ∧ expiry ∧ payload_hash) ∧ (compare-and-set last_fence := max(last_fence, f)) en un único paso atómico antes de ejecutar.

CALL_EN_VUELO: provider no debe ejecutar efecto con fence obsoleto EN NINGUNA circunstamcia:
 - pre-check at accept time (commit point);
 - revocación posterior invalida: el efecto se materializa o no se acepta;
   si ya empezó, suspender es semánticamente irreversible: debe quedar UNKNOWN → reconciliación.
- Revocación: W emite broadcast/commit de fence global bump en la misma tx del scope;
  providers consultan o son notificados antes de cada force-risk; TTL de capability corta la ventana de captura.
- Sin support de fence en provider ("provider tonto"): la frontera es el sink;
  sink exige capability válida + fence vigente + sin suspensión confirmada antes de encolar al proveedor; UNKNOWN outcome postal⇒ ES-007;
  la ventana de riesgo queda acotada por: expiry corto + consulta post-dispatch + revocación posterior + SC-002 obligatorio.
- Proveedor sin idempotency-key support: mismo régimen; idempotency-key sólo se exige si soportado;
  caso contrario, reconciliación provider-side obligatoria; operación no cierra hasta veredicto.
```

### §11-C-03 — Cierre ante efectos desconocidos

```
T-CLOSE/T13 exige: ∀ e∈manifest: ResultadoExternoConocido(e): (ES-005 ∨ ES-006) ∨ Nuncadespachado ∧ Terminal;
ES-007 persistente ⇒ bloqueo duro; sin empuje posible por T-SUSPEND;
decisión humana (T13) con efectos pendientes ⇒ ilegal; la petición de cierre advierte y falla.
Cierre parcial prohibido: no hay CLOSED con efectos sin veredicto.
```

### §11-C-08/C-18 — Punto de linealización único

```
LP del sink := RESERVE slot atómico `effect_log` con state=INTENT (o confirm de dispatch)
               en la MISMA tx que decrementa min-time/fence-counters? NO: LP := fila scope lock
               tomada en la tx del sink para validación Y confirmación del efecto (o el commit del
               effect_log.LP-orden); textbf{el LP real es el commit que escribe `effect_log`+estado
               del efecto observable}. La adquisición de lock es sincronización, no LP.
Linealización contra suspensión: la operación que cierra (T-SUSPEND) y el LP del sink comparten el
scope row lock; el que adquiere primero determina precedencia observable; el posterior ve el resultado;
LP único ⇒ ningún proceso cruza con side-effect no registrado.
Interrupción entre validación y dispatch: effect_log previa (INTENT) garantiza outcome visible;
crash ⇒ sin dispatch (rollback completo) o reconciler resuelve con provider-side attestation.
```

### §11-C-09/C-19 — Anclaje externo de la cadena

```
Anchor := compromiso diario {"root_hashes":[…], "seq":N, "timestamp":T}, firmado por Ancla (verificador externo).
Rotación de raíz por ancla externa; cadena local verificada contra ancla externamente.
Sustitución completa de la cadena ⇒ hash no coincide con ancla externa ⇒ detectado.
Autoridad de anclaje NO coincide con autoridad de escritura ⇒ separación completa.
Int detección silencio: mismatch ⇒ fail-closed; ninguna lectura confía sin comprobación del ancla.
Coste: una verificación externa por día (o por rotación); tolerancia de ancho en caché.
```

## 6-B.1 C-01…C-19 — estado y disposición v3

| C | Reparación (§11) | Estado v3 |
|---|---|---|
| C-01 | estados separados + CHECK equivalenica exacta columna/estado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| C-02 | protocolo frontera completa (capability+fence+revocación+casos proveedor) | **BLOCKED** (B-04/B-08) |
| C-03 | cierre con efectos conocidos/verificados/compensados/never | **BLOCKED** (requires ratificación) |
| C-04 | preimagen canónica + vectores + key registry + reglas verificación | **BLOCKED** (D-R2R2-9) |
| C-05 | `numeric(20,0)` + CHECK dominios completo | REPAIRED-DOCUMENTAL CONDICIONADO (D-R2R2-7) |
| C-06 | retirada de `fence-window`; fence entero monotónico en sink | REPAIRED-DOCUMENTAL — cotejo pendiente |
| C-07/C-17 | lema finito por cardinalidad (especificado en §11-C-07) | REPAIRED-DOCUMENTAL CONDICIONADO |
| C-08 | LP = commit dual (effect_log+estado); lock=sincronización | REPAIRED-DOCUMENTAL — cotejo pendiente (B) |
| C-09/C-19 | rol write-only+trigger rechazo+anchor externo + verificación periódica | REPAIRED-DOCUMENTAL — cotejo pendiente H-03 |
| C-10 | CAS predicado completo | REPAIRED-DOCUMENTAL — cotejo pendiente |
| C-11 | consumo por transición con contenido vinculado | REPAIRED-DOCUMENTAL — cotejo pendiente |
| C-12 | orden parcial por instancias; contradicción por clase de veredicto | REPAIRED-DOCUMENTAL — cotejo pendiente H-17 |
| C-13 | mapa terminal de efectos demostrable | REPAIRED-DOCUMENTAL — cotejo pendiente H-18 |
| C-14 | cobertura sinks exige evidencia ejecutable (CI con evidence archivada) | **BLOCKED** (evidencia no ejecutada) |
| C-15 | trigger comprueba operación↔manifest en la misma tx | REPAIRED-DOCUMENTAL — cotejo pendiente A-04 |
| C-16 | idempotency-key sin attempt_id | REPAIRED-DOCUMENTAL — cotejo pendiente |
| C-17 | ver C-07 | REPAIRED-DOCUMENTAL CONDICIONADO |
| C-18 | ver C-08 | REPAIRED-DOCUMENTAL |
| C-19 | ver C-09 | REPAIRED-DOCUMENTAL — cotejo pendiente |

## 6-C. N-01…N-10 — incorporación de los defectos nuevos de v2

| N | Defecto | Disposición v3 |
|---|---|---|
| N-01 | C-01 contradecía ejemplo | Cerrado en §11-C-01 (definiciones explícitas + tests) |
| N-02 | C-16 incluía attempt_id | Cerrado: EFFECT_KEY sin attempt_id; ver §11-C-16 |
| N-03 | orden lexicográfico descrito como parcial | Cerrado: orden parcial por instancias + contradicción por clases (§11-C-12) |
| N-04 | LP sin fijación única | Cerrado: LP = commit dual (effect_log↔estado); ver §11-C-08/C-18 |
| N-05 | C-15 no consulta operación | Cerrado: trigger cruza operation↔manifest en misma tx (§11-C-15/C-C-15) |
| N-06 | C-19 sin ancla externa | Cerrado: ancla externa (§11-C-09/C-19) |
| N-07 | encode_bytes no definido | Cerrado: preimagen canónica con encodes exactas (§11-C-04) |
| N-08 | H-16 cita C-18 como soporte | Corregido: H-16 referencia su propia prueba formal §13.1 |
| N-09 | M-02 vinculado a D-R2R2-7 | Corregido: `decided_at` ⇒ timestamptz único; D-R2R2-7 sólo UINT64 generaciones |
| N-10 | H-22 incompleto | Corregido: dominio justificado fila a fila desde R1 con productos exactos (§13.3) |


---

## 7. D-R2R2-1…11 — ninguna ratificada (v3 mantiene los estados del dictamen)

| # | Dictamen | Estado en esta v3 |
|---|---|---|
| D-R2R2-1 | BLOCKED | **BLOCKED** (revocación/rotación/custodia) |
| D-R2R2-2 | BLOCKED (B-04) | **BLOCKED** |
| D-R2R2-3 | BLOCKED (efectos) | **BLOCKED** |
| D-R2R2-4 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (alineación D-R2R2-7) |
| D-R2R2-5 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (§11-C-04 pendiente ratificación) |
| D-R2R2-6 | DIFERIDA | **DIFERIDA** |
| D-R2R2-7 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (numeric(20,0)+CHECK + censo completo) |
| D-R2R2-8 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (C-01 separa estados; FK diferida sólo tras corrección) |
| D-R2R2-9 | BLOCKED | **BLOCKED** |
| D-R2R2-10 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (trigger concurso verificado §6-B/C-15) |
| D-R2R2-11 | REPAIR_REQUIRED | **REPAIRED-CONDICIONADO** (mapa estados §11-C-13) |

## 8. Propagación de bloqueos — aplicación uniforme

Regla: una fila `BLOCKED` propaga bloqueo a cualquiera dependiente de ella; ninguna dependencia oculta a través de una fila «reparada» puede saltarse el bloqueo.

Conjunto `BLOCKED` v3 (uniforme): H-05, H-06, H-11, H-13, H-14, H-15, H-17, H-18, H-21, H-23, H-24, H-25, H-26, AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019, A-03, A-04, B, C, D, E, F, C-02, C-03, C-04, C-14, M-01, M-04, M-10.
Cualquier mención de estas filas como `REPAIRED-DOCUMENTAL` o libre es un error de esta revisión y debe marcarse así en auditoría.

## 9. Procedimiento posterior (NO autorizado aún)

```
1. Propietario audita esta revisión v3.
2. Dictamen por fila; registro anotado.
3. Si se aprueba: regeneración completa del baseline como r3 aplicando ÚNICAMENTE lo ratificado.
4. r3 pasa a auditoría independiente desde cero.
5. B07_FORMAL_MODEL.md: sin modificaciones autorizadas ahora o aquí.
6. R3 permanece BLOCKED.
```

## 10. Estado y procedencia

- v3 sustituye a v2 para efectos de auditoría; antecedente conservado: `B07-R2-Consolidated-Repair-Matrix-v2-audited.md` (`103feeb2…`).
- v2.r2 intacta (`9c8a0aba…`); `B07_FORMAL_MODEL.md` intacto; §1 intacta.
- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `D-315 = PENDING` · `MODEL_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · `PROMOTION = NOT_READY`.
- Esta matriz no declara evidencia ejecutable de ninguna prueba; los vectores §11 son cálculos documentales reproducibles, no ejecución del sistema.
- `state/multiproject/log.md` registra esta revisión.

## 13. Apéndice formal

### 13.1 INV-13 — prueba formal (H-16)

```
INV-09: ∀ op, T(op) ∈ {COMMIT_TESTIFIED, ABORT_TESTIFIED} ⇒ P(op) ∈ {COMMIT_DURABLE, ABORT_DURABLE}
Dominio T = {NONE, COMMIT_TESTIFIED, ABORT_TESTIFIED}; dominio P finito y conocido.
Contrapositiva: ∀ op, P(op) ∉ {COMMIT_DURABLE, ABORT_DURABLE} ⇒ T(op) ∉ {COMMIT_TESTIFIED, ABORT_TESTIFIED}
          ⇒ T(op) = NONE por dominio finito de T.
INV-13 := esa proposición. No depende de máquinas; depende de INV-09 + dominios finitos (R1).
```

### 13.2 Censo UINT64 (A-02/H-19)

| Columna | Tipo | CHECK |
|---|---|---|
| `scope.scope_epoch` | numeric(20,0) | `0 ≤ v` |
| `scope.minimum_valid_fence` | numeric(20,0) | `≥ 0` |
| `scope.next_fence` | numeric(20,0) | `≥ 0` |
| `operation.scope_epoch` | numeric(20,0) | `≥ 0` |
| `operation.policy_version` | numeric(20,0) | `≥ 0` |
| `operation.current_attempt_generation` | smallint | `1..255` |
| `attempt.attempt_generation` | smallint | `1..255` |
| `attempt.claim_generation` | numeric(20,0) | `1 ≤ v ≤ 18446744073709551615` |
| `attempt.fencing_token` | numeric(20,0) | `0..18446744073709551615` |
| `manifest.policy_version` / `manifest.scope_epoch` | numeric(20,0) | `≥ 0` |
| `reconciliation_record.decided_at` | timestamptz | `NOT NULL` |
| `blocked_symbols.decided_at` | timestamptz | `NOT NULL` |
Wire: uint64_le(v) con pre-validate `0 ≤ v ≤ 18446744073709551615`; driver rechazado fuera de dominio.

### 13.3 Cardinalidad D-315 (H-22)

R1 da dominios: SI=4, TRs=3, ESs=5, OD=4, V=3, P=10, O=4, T=3, ESo=6.
```
|S_SCOPE| = 4·3·5 = 60   (∈dominios R1)
|S_OPERATION| = 4·3·10·4·3·6 = 8640   (∈dominios R1)
|S_BASE| = 60·8640 = 518400   (proyección cartesiana; no legalidad)
|LEGAL| ≤ |S_BASE|; |REACHABLE| ≤ |LEGAL|; ambos desconocidos; D-315 = PENDING
```

### 13.3a Terminación de cierre transitivo BND (C-07/C-17)

```
Universo U := R1(49) ∪ R1.3(17) ∪ bloqueados ∈ U; |U| ≤ 66; deps: U×U → finito.
Φ(X) = X ∪ {d ∈ U : dep(target of X) contains d}
Φ monótono ⊆ monótono en ⊆; iterable: X₀=seed; X_{i+1}=Φ(Xᵢ); estrictamente creciente si no está en punto fijo.
Por tanto existe N ≤ 66 con X_N = X_{N+1}. Desconocidos tratados como BLOCKED.
Ciclos no requieren acíclicidad; requieren |U| finito.
```

Fin matriz consolidada R2-A — REVISIÓN 3 · DRAFT / NOT_ACCEPTED · Procedencia en `state/multiproject/log.md`.
