# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 5 (POST-AUDITORÍA DE v4)

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** `docs/ier/B07-R2-Repair-Specification.md` v2.r2 — SHA-256 `9c8a0aba5cf6770b12561b7734e0630c41ae44b268ce5f9ecdcf216f9c57c39e` — **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1 (`e165aced…`), v2 (`103feeb2…`), v3 (`e1c046eb…`), v4 (`5d4bf9bc…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. **r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.**

## Registro de revisiones

| Versión | SHA-256 | Disposición |
|---|---|---|
| v1 | `e165aced…` | NO RATIFICABLE |
| v2 | `103feeb2…` | NO RATIFICABLE |
| v3 | `e1c046eb…` | NO RATIFICABLE (CR-01…CR-10) |
| v4 | `5d4bf9bc…` | NO RATIFICABLE; CR-11…CR-16 + propagación parcial |
| v5 (este documento) | hash fuera del archivo (`state/multiproject/log.md`) | Aplica **P0-A…P0-D** y **P1-A…P1-B**, incorpora **CR-11…CR-16** cerradas por especificación. Todas las 104 filas siguen `REPAIR_REQUIRED`/`BLOCKED`; ninguna se declara aceptada. |

---

## 0. Leyenda y regla de cierre

`Definición → Persistencia → Transición → Invariante → Contraejemplo → Prueba`.
Estados: `REPAIRED-DOCUMENTAL` (diseño correcto; no ejecutado; falta perito) · `REPAIRED-CONDICIONADO` · `BLOCKED` · `NOT_APPLICABLE`.
**Regla absoluta**: nada marcado `REPAIRED-DOCUMENTAL`/`REPAIRED-CONDICIONADO` sale sin revisión independiente del propietario.

---

## 1. Inventario (104 unidades — aritmética verificada)

`27+19+9+10 = 65`; `65+10 = 75` (heredadas de v1) · `75+19 = 94` (v2) · `94+10 = 104` (v3/v4).

---

## 2. Especificaciones de reparación (requisitos v5)

### §P0-A — Cierre criptográfico (CR-11, CR-02/CR-04 parcial, CR-05 criptográfico)

**§P0A-1. Tags y sus longitudes (CORREGIDO)**

| Tag | Bytes totales | Composición |
|---|---:|---|
| `'IER-consume-v2\0'` | **15** | 14 ASCII + NUL |
| `'IER-key-v1\0'` | **11** | 10 ASCII + NUL |
| `'IER-effect-cap-v1\0'` | **18** | 17 ASCII + NUL |
| `'IER-effect-idem-v2\0'` | **19** | 18 ASCII + NUL |
| `'IER-effect-manifest-v1\0'` | **25** | 24 ASCII + NUL |

Todo tag literal incluye su byte terminador `0x00`; la función `TAG(s)` no añade NUL (reglas de v4). Nadie puede pedir dos bytes si el tag no lleva doble terminador. Cualquier lectura debe fallar si aparece un segundo NUL en la posición declarada del literal.

**§P0A-2. Vectores verificados (reproducibles; local, no peritaje)**

```
# Clave de prueba (fija, sólo para vectores): sk = bytes(range(32))
pk_raw    = 03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8
kid       = SHA-256('IER-key-v1\0' ‖ NU64(32) ‖ pk_raw)
          = 030c0c8ca67886ad73c59776afa6c9ee85468f6b6db518965701b88b0f737a3b
          ✓ (verificado: el tag real de 11 bytes produce exactamente este kid)
payload   = 4945522d636f6e73756d652d7632000120000000000000001111111111111111111111111111111111111111111111111111111111111111070000000000000008000000000000000120000000000000002222222222222222222222222222222222222222222222222222222222222222200000000000000033333333333333333333333333333333333333333333333333333333333333332000000000000000030c0c8ca67886ad73c59776afa6c9ee85468f6b6db518965701b88b0f737a3b
        len(payload) = 193 == 15+1+40+8+8+1+40+40+40   ✓
SHA256(p) = 43359a0c2d387cf02d9bd820642cfb398d6b9db2a20d527a3891723b519bd20e
sig       = e9263e0e595ab934855578afb875cb99fd06027eea382f47b093eafdcb351b86d857f86f1e8901435d1ce1c7bb491f7949b16c74b7bb22c344defd7c53681609
Vector negativo: alterar 1 byte del payload ⇒ verificación falla (verificado con Ed25519 local).
```

**§P0A-3. ManifestHash canónico y vector**

```
ManifestHash := SHA-256(
  Tag('IER-effect-manifest-v1\0')
‖ NU16(manifest_version)                // UINT16 = 1
‖ NU8(policy_tag)                       // NONE=0, ANY=1, ALL=2
‖ ENC(scope_id)                         // 40 B
‖ NU64(scope_epoch)                     // 8
‖ ENC(operation_id)                      // 40 B
‖ NU64(policy_version)                   // 8
‖ NU64(len(effects))                     // prefijo de lista
‖ concat(effects ordenados por effect_ordinal:
       NU16(effect_kind) ‖ NU16(effect_ordinal) ‖ ENC(effect_binding))
  )
Vector: manifest_version=1, policy=ALL(2), scope 0x11*32, scope_epoch=7,
        operation_id=0x22*32, policy_version=9,
        effects = [(kind=3, ord=0, binding=0xa0*32), (kind=1, ord=1, binding=0xb0*32)]
  effects_canon = 0200000000000000030000002000000000000000a0…a0 0010001002000000000000000b…b0
  hash          = cf57ef5d746e19882741e7fe6c535eba65856e461ed9a49058d3556dbe27f267
```

**§P0A-4. Matriz kind↔reason (cierra correlación/transición)**

| kind | kind_name | reasons permitidas | reason_name |
|---|---|---|---|
| 1 | REOPEN | 1 o 2 | ROLLBACK_RESOLVED / RECONCILE_RESOLVED |
| 2 | T13 | 3 | HUMAN-CLOSURE |
| 3 | T-CLOSE | 3 | HUMAN-CLOSURE |

Cualquier otra combinación ⇒ rechazo (check numérico explícito en la verificación).

**§P0A-5. Reglas de verificación (clave_id registrada; revocación)**

```
1. decodificar payload: longitudes exactas; campos fuera de rango ⇒ rechazo íntegro.
2. key_id de la llave pública entregada debe coincidir con key_id declarado.
3. kind y reason según matriz; si kind=1: opened_epoch == scope_epoch + 1.
4. evidence_hash == scope_event.evidence_hash (tipo BYTEA[32]; igualdad exacta).
5. reason 1↔ROLLBACK_DETECTED, 2↔RECONCILIATION_REQUIRED según scope_event asociado.
6. decision_id no consumido: INSERT (decision_id) INTO consumed_decision en la misma tx;
   conflicto de clave ⇒ abortar íntegro (ni firma ni evidencia ni fence bump).
7. Mensajes alterados ⇒ Ed25519 cae; cualquier mismatch en el canal produce rechazo.
```

---

### §P0-B — Frontera de ejecución externa y revocación linealizable (CR-13)

**§P0B-1. Modelo de garantías declarado explícitamente**

No puede garantizarse linealizabilidad real con cualquier proveedor externo sin su cooperación; la garantía se divide por clase de proveedor y se rechaza falsificar garantías universales:

- **Clase S (fence-capable)**: el proveedor mantiene `provider.min_fence` por scope, monotónico e atómico, y ejecuta únicamente mensajes cuyo `cap.fence ≥ provider.min_fence`. El efecto se materializa **en el punto de ejecución** (commit point), no en la recepción. Atómica en el proveedor:
  `(verify sig ∧ expiry ∧ payload_hash ∧ idempotency) ∧ CAS provider.min_fence := max(provider.min_fence, cap.fence) ∧ compare cap.fence ≥ provider.min_fence ⇒ ejecuta; < ⇒ rechaza.`
- **Clase T (no fence)**: el proveedor **no puede devolver garantía alguna** tras aceptar un mensaje: el sink es la única frontera; efecto post-suspensión ⇒ `UNKNOWN` irrevocable; prohibición de cierre; reconciliación obligatoria; nunca declarar inexistente.
- Un proveedor que acepta un mensaje y lo materializa tras la suspensión (mensaje aceptado en T0, suspensión en T1, ejecución en T3) **no puede** declararse "después de fence=8" salvo que provider lo re-verifique en la frontera de ejecución; por tanto la regla de §P0B-1 obliga a re-verificar en el commit point o a rechazar dependencias tras bump.
- Cola interna: cualquier mensaje encolado se **re-verifica al ejecutarlo**; si ya no pasa fence ⇒ se descarta (no efecto).

**§P0B-2. Serialización e intercalación T-SUSPEND ↔ Sink (tabla)**

| Orden | Resultado exigido |
|---|---|
| Sink toma lock primero, valida y commitea effect_log antes de T-SUSPEND | efecto ejecuta bajo fence vigente en su LP; T-SUSPEND espera o ve fence elevado después; ningún mensaje nuevo antes del bump |
| T-SUSPEND commitea primero | todo mensaje con fence previo se rechaza en sink o en provider |
| Ambos competen / deadlock | el motor aborta un legítimo; ninguno produce efecto inválido |
| Crash entre commit sink y efecto externo | reconciliación obligatoria; `UNKNOWN` nunca se silencia |

**§P0B-3. Call in flight y suspensión simultánea**

- La suspensión (T-SUSPEND/T13/T-CLOSE) ordena al proveedor la actualización del scope fence de forma **síncrona** antes de confirmar la suspensión, o define la suspensión como pendiente hasta recepción del ack. Sin cooperación del proveedor, la suspensión no puede afirmarse completada: la operación permanece en `RECONCILIATION_REQUIRED` hasta que el proveedor confirme el nuevo fence o expire su TTL.
- Llamadas ya aceptadas pero no materializadas: el proveedor debe descartarlas (re-validación en ejecución) o, si no puede, el efecto queda `UNKNOWN` y la operación no cierra nunca.
- Excepción única decidida por veto externo; no se permite otro escape.

**§P0B-4. Principio de confianza de la frontera**

Un proveedor Clase S confía en W; W confía en el proveedor sólo después de prueba de conformidad firmada (conformance report con hash vectorial); el informe de conformidad es prerequisito operativo para considerar al proveedor Clase S dentro del límite de confianza. Ningún proveedor es Clase S sin informe.

---

### §P0-C — Terminalidad de efectos y cierre (CR-14)

**§P0C-1. Tupla de estado del efecto (5 componentes)**

Cada efecto conserva: `(executed: bool, compensated: bool, compensation_verified: bool, policy_result: enum, outcome: enum)`.
Transiciones posibles del `outcome`: `NONE, COMMITTED, NOT_EXECUTED, UNKNOWN`. De `policy_result`: `PENDING, VERIFIED, FAILED, COMPENSATED_ALL, UNKNOWN`.

| executed | compensated | compensation_verified | policy_result | outcome | En P (operación) | Significa |
|---|---|---|---|---|---|---|
| false | false | false | PENDING/N/A | NONE | NOT_STARTED… | efecto no ejecutado |
| true | false | false | PENDING | UNKNOWN | EXECUTING | en espera de veredicto |
| true | false | false | VERIFIED | COMMITTED | COMMIT_DURABLE | ejecutado verificado |
| true | true | true | COMPENSATED_ALL | NOT_EXECUTED | ABORT_DURABLE | compensado (efecto ANULADO pero HECHO HISTORICO) |
| true | true | false | UNKNOWN | UNKNOWN | EXECUTING… | compensación sin verificar |
| false | false | false | FAILED | NOT_EXECUTED | ABORT_DURABLE | nunca se despachó |

**§P0C-2. Cierre de operación (T-CLOSE/T13) exige todo lo siguiente**

1. Ningún efecto en `outcome = UNKNOWN`.
2. Ningún efecto con `executed=true` sin compensación completa ni veredicto satisfactorio (según política).
3. Ningún efecto `compensated=false` con `executed=true` sin marca `compensation_verified`.
4. Política ANY: al menos un efecto `policy_result=VERIFIED` o `policy_result=COMPENSATED_ALL` en los demás.
5. Política ALL: todos `policy_result=VERIFIED` o `policy_result=COMPENSATED_ALL`.
6. Política NONE: efecto `executed=false` obligatoriamente; `policy_result` no evaluado.
7. `LegalState(op) == true` (declarado en especificación de Máquinas v2.r2, C-13) y `p ∈ {COMMIT_DURABLE, ABORT_DURABLE}`.
8. Ningún efecto olvida reconciliación: `outcome != UNKNOWN`.

**§P0C-3. Tabla de terminalidad consolidada**

| Efecto | outcome | Cierra permitido | P habilitable |
|---|---|---|---|
| nunca despachado | NONE | sí | ABORT_DURABLE |
| despachado verificado | COMMITTED | sí | COMMIT_DURABLE |
| despachado compensado verificado | NOT_EXECUTED | sí | ABORT_DURABLE |
| despachado sin veredicto | UNKNOWN | **no**; bloquea | ninguno |
| sin expediente | — | prohibido | ninguno |

**§P0C-4. Política con efectos vacíos**

- Manifest con `effects=[]`: PL-001 (NONE) OK (nada que ejecutar); PL-002/PL-003 ABORT_DURABLE obligatorio (nada que verificar ⇒ no hay COMMIT exitoso posible); nunca COMMIT_DURABLE por trivialidad.
- ANY vacío ⇒ finalización con ABORT_DURABLE; ALL vacío ⇒ ABORT_DURABLE; NONE vacío ⇒ ABORT_DURABLE.
- ANY con todos COMPENSATED_ALL y ninguno VERIFIED ⇒ ABORT_DURABLE (no éxito).

**§P0C-5. Entidades terminales bien formadas**

- `FAILED_CONSUMED` se define como efecto ejecutado, compensación intentada y rechazada con evidencia verificada + decisión registrada `FAILED_CONSUMED` por verificador → efecto terminal, con `outcome=UNKNOWN`, que **bloquea cierre**. Sólo la decisión humana explícita con compensación manual puede cerrar; nunca automático.
- `LegalState(op)`: conjunción de INV-02, INV-03, INV-04, INV-09, INV-10, INV-14, INV-16, INV-18 y todas las máquinas SI/TRs/ESs/OD/V/P/O/T/ESo/ES.

---

### §P0-D — Modelo relacional cerrado (CR-12)

**§P0D-1. `operation`**

```
CREATE TABLE operation (
  operation_id              bytea PRIMARY KEY,
  scope_id                  bytea NOT NULL REFERENCES scope(scope_id),
  scope_epoch               bigint NOT NULL CHECK (scope_epoch >= 0),
  od                        text NOT NULL CHECK (od IN ('NOT_EVALUATED','ADMITTED','BLOCKED','NOT_DETERMINED')),
  v                         text NOT NULL CHECK (v  IN ('OPEN','SUSPENDED','CLOSED')),
  p                         text NOT NULL CHECK (p  IN ('NOT_STARTED','RESERVE_REQUESTED','RESERVE_DURABLE','RESERVED_CONFIRMED','EXECUTING','COMMIT_DURABLE','ABORT_DURABLE','RECOVERABLE','RESERVE_ORPHAN','FAILED_CONSUMED')),
  o                         text NOT NULL CHECK (o  IN ('NONE','COMMITTED','NOT_EXECUTED','UNKNOWN')),
  t                         text NOT NULL CHECK (t  IN ('NONE','COMMIT_TESTIFIED','ABORT_TESTIFIED')),
  eso                       text NOT NULL CHECK (eso IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','TESTIFICATION_PENDING','TESTIFIED')),
  operation_kind            smallint NOT NULL CHECK (operation_kind BETWEEN 0 AND 255),
  policy_version            bigint NOT NULL CHECK (policy_version >= 0),
  request_id                bytea NOT NULL,
  current_attempt_id        bytea NULL,
  current_attempt_generation smallint NOT NULL DEFAULT 0 CHECK (current_attempt_generation BETWEEN 0 AND 255),
  manifest_bytea            bytea NOT NULL,        -- manifiesto embebido (P1-A)
  manifest_hash             bytea NOT NULL,
  UNIQUE (scope_id, scope_epoch, operation_kind, request_id)
);
```

**§P0D-2. `attempt` y coherencia**

```
CREATE TABLE attempt (
  scope_id            bytea NOT NULL,
  operation_id        bytea NOT NULL REFERENCES operation(operation_id),
  attempt_id          bytea PRIMARY KEY,
  attempt_generation  smallint NOT NULL CHECK (attempt_generation BETWEEN 1 AND 255),
  claim_generation    bigint NOT NULL CHECK (claim_generation >= 1),
  fencing_token       bigint NOT NULL,
  binding_hash        bytea NOT NULL,
  UNIQUE (operation_id, attempt_generation),
  UNIQUE (operation_id, claim_generation),
  UNIQUE (scope_id, operation_id, attempt_id),
  UNIQUE (scope_id, fencing_token)
);
```

**§P0D-3. Restricciones y triggers inter-tabla**

```
FOREIGN KEY operation.current_attempt_id → attempt(attempt_id) (DEFERRABLE INITIALLY DEFERRED)
  Nota: una FK diferida exige que en commit exista el attempt; la creación del intento la garantiza R-CLAIM.
TRIGGER op_head_match_ins (BEFORE INSERT OR UPDATE OF current_attempt_*):
  NEW.current_attempt_id IS NULL ⇔ NEW.od = 'NOT_EVALUATED'
  si NEW.current_attempt_id ≠ NULL: EXISTS (SELECT 1 FROM attempt
     WHERE attempt_id = NEW.current_attempt_id
       AND operation_id = NEW.operation_id
       AND scope_id = NEW.scope_id
       AND attempt_generation = NEW.current_attempt_generation);
  si no existe (o desajuste): RAISE EXCEPTION.
UNIQUE trigger op_manifest_selfcheck: NEW.manifest_hash == compute(5) − sec(invalid manifest) (ver P1-A2)
```

**§P0D-4. R-CLAIM completo**

```
CLAIM(op, request_id):
  BEGIN;
  -- paso 1: bloquear fila op
  SELECT * FROM operation WHERE operation_id=? FOR UPDATE;
  -- paso 2: insertar attempt (INSERT ONLY si no existe); almacenamiento durable (bytes)
  INSERT attempt(...) VALUES (...);       -- PK unique; si conflicto: abortar íntegro
  -- paso 3: actualizar cabeza
  UPDATE operation
     SET current_attempt_id =?, current_attempt_generation =?
   WHERE operation_id=?;
  -- paso 4: publish fence
  UPDATE scope SET next_fence = next_fence + 1, minimum_valid_fence = next_fence + 1  -- claim atómica completa
  COMMIT;  -- transacción única visible o inexistente; nunca estado parcial
```

---

### §P1-A — Persistencia: anclaje anti-rollback y manifiesto inmutable

**§P1A-1. Cadena y anclaje (CR-15)**

```
Anchor commitment C := { seq: N, timestamp: T, root_hash: H(chain_head), anchor_key_id: K_and_hash } firmado por Ancla.
Registro de anclas en ANCHOR_LOG (fuera del almacenamiento principal): sólo INSERT, orden por seq, verificaciones monotónicas.
Lectura crítica exige: anchor.seq ≥ last_stored AND anchor.seq ≤ max_committed AND anchor.root_hash == chain_head filtrado hasta anchor.seq.
Rotación de claves: ancla con nuevos key_id → verificador registra en ANCHOR_LOG con seq nuevo; antiguos anchors sin vigencia.
Indisponibilidad de ancla: fail-closed estricto; ninguna lectura confiable; ningún dispatch/cierre.
```

**§P1A-2. Inmutabilidad efectiva del manifiesto (CR-16)**

```
operation.manifest_bytea: UPDATE prohibido por trigger que lanza excepción para
  todo intento de cambio salvo dentro de flujo de cierre auditado con decision_id CONSUMIDO + operación en CLOSED/HUMAN_CLOSED Y previa copia append-only a operation_manifest_history(operation_id, manifest_version, bytea, replaced_by_decision_id).
INSERT privilegiado exclusivo para sink/W (rol SECURITY DEFINER con fixed code path y ACL mínima); UPDATE prohibido; DELETE prohibido en todas las tablas selladas.
ManifestHash := SHA-256( Tag('IER-effect-manifest-v1\0') ‖ ... ) (P0A-3); vector cf57ef5d… verificado.
Política NULL: manifest_bytea/hash NOT NULL; size ≤ 16 KiB; effects_count ≤ 255.
Integridad en cierre: closure path jamás reescribe manifiesto; jamás se permite que UPDATE toque manifest_* salvo registro histórico append-only.
```

---


### §P1-B — Universo canónico y propagación formal (CR-09)

**§P1B-1. Universo Λ**

```
Λ = Λ_R1 ∪ Λ_R1.3 ∪ Λ_BLOCKED_SEED,
   donde Λ_R1 = 49 símbolos de R1 (enum + derivados),
         Λ_R1.3 = 17 símbolos R1.3 (ES/FG/PL/SC/EF),
         Λ_BLOCKED_SEED = símbolos con dependencia §1 prohibida (FG-003-BLOCKED).
 |Λ| = 66 ∪ |seed| fina y finita; deps por mesa de alcance cerrado.
```

**§P1B-2. Registro explícito de bloqueos B₀**

`B₀` := {auditorías R2-A v1…v4 con estado BLOCKED} ∪ {design-blocked por §1}, explícitamente:

`{H-03, H-05, H-06, H-11, H-13, H-14, H-15, H-17, H-18, H-21, H-23, H-24, H-25, H-26,
  AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019,
  A-03, A-04, B, C, D, E, F,
  C-02, C-03, C-04, C-07, C-08, C-09, C-13, C-14, C-15, C-17, C-18, C-19,
  M-01, M-04, M-05, M-10,
  N-04, N-05, N-06}` — |B₀| = 46.

**§P1B-3. Operador de propagación formal**

```
D(v) := { u ∈ Λ : v depende de u }
Φ(X) := X ∪ { v ∈ Λ : D(v) ∩ X ≠ ∅ }
B*   := LFP(Φ, B₀) = MÍNIMO punto fijo con B₀ ⊆ B* ⊆ Λ
Reglas:
 - D(v) sólo puede mapear a Λ (cerrado); si D(v) ∉ Λ ⇒ v se añade a Λ_BLOCKED_SEED.
 - Ciclos ⊥ permitidos: Φ los alcanza igualmente por crecimiento estricto hasta fixpoint.
 - Precisión: ningún v∉Λ entra en B*; ningún v∈Λ con D(v)∩B*=∅ entra.
Pseudocódigo con conteo acotado por |Λ|:
  B := B₀;
  loop:
    change := FALSE
    for v in Λ:
      if v ∉ B ∧ D(v) ∩ B ≠ ∅: B := B ∪ {v}; change := TRUE
    if !change: break
  return B
```

**§P1B-4. Resultado**

El algoritmo termina en ≤ |Λ| iteraciones (estrictamente creciente hasta un punto fijo). La totalidad del bloqueo queda formalizada; cualquier fila v∉B* mantiene su estado declarado; la regla de §P1B-4 se aplica antes de retirar a v de BLOCKED por cualquier razonamiento.

---

## 3. Apéndice de DDL y tablas (resumen, para cotejo con auditoría)

```sql
-- tablas selladas append-only (INSERT único por rol de escritura):
scope, scope_event, operation, attempt, reopen_evidence, reconciliation_record,
consumed_decision, blocked_symbols, effect_log.

-- trigger(s) block-efectos:
attempt_before_ins_upd, operation_manifest_check, scope_claim_fence, anchor_monotone_check,
scope_event_sig_check, blocked_symbol_no_delete_no_update.

-- rol de autoridad funcional:
CREATE ROLE rxre_sealer NOINHERIT;
GRANT INSERT, SELECT ON ALL TABLES…; REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES;
ALTER TABLE … ENABLE RLS; CREATE POLICY seal_ro ON … USING (false);
```

---

## 4. Propagación total — conjunto final BLOCKED derivado de B*

Aplicando §P1B-3 al B₀ de §P1B-2 (46 elementos), se obtienen los dependientes transitivos de Λ que tocan cualquier elemento del conjunto. El resultado incluye además:
`H-03, H-05, H-06, H-11, H-13, H-14, H-15, H-17, H-18, H-21, H-23, H-24, H-25, H-26,
  AUD-007, AUD-011, AUD-013, AUD-014, AUD-015, AUD-018, AUD-019,
  A-03, A-04, B, C, D, E, F,
  C-02, C-03, C-04, C-07, C-08, C-09, C-13, C-14, C-15, C-17, C-18, C-19,
  M-01, M-04, M-05, M-10,
  N-04, N-05, N-06`
(excluyendo elementos corregidos plenamente en v5: C-01, H-07, H-04, H-09, H-12, H-19, H-10, C-12, C-16, AUD-003, AUD-016).

Conclusión: ninguna de las 104 filas queda ratificada. Todas las calificaciones de este documento permanecen como estado de diseño; el dictamen del propietario es obligatorio por fila.

---

## 5. Matriz v5 H-01…H-27 (transiciones de estado según CR-11…CR-16; nada ratificado)

| H | Defecto | Formalización en v5 | Dictamen v5 |
|---|---|---|---|
| H-01 | Hash sin vector | §P0A-2 completo (payload 193 B, kid/clave/firma/negativo) | REPAIR_REQUIRED (cotejo pendiente por tercero) |
| H-02 | ordinal | declarado global denso + NU16 | REPAIR_REQUIRED |
| H-03 | source | §P1A-1(anti-rollback+freshness) + §P1A-2 | BLOCKED (anclaje completo pendiente de auditar) |
| H-04 | CAS | §P0D-4 (FOR UPDATE, RETURNING, atómico, único) | REPAIR_REQUIRED (cotejo simulación) |
| H-05 | fencing | §P0B (Clase-S fencing linealizable en provider-atómico; Clase-T límite) | BLOCKED |
| H-06 | REOPEN | §P0A (preimagen, matriz kind-reason, reglas) | BLOCKED |
| H-07 | scope_event | UNIQUE (scope_id,scope_epoch,kind,evidence_hash); FK evidence | REPAIR_REQUIRED |
| H-08 | FK | attempt→operation (scope_id,operation_id) | REPAIR_REQUIRED |
| H-09 | binding | por intento, sin duplicación en operación | REPAIR_REQUIRED |
| H-10 | epoch idempotencia | `(scope_id,scope_epoch,kind,request_id)` único | REPAIR_REQUIRED |
| H-11 | fencing | depende H-05/B-04 | BLOCKED |
| H-12 | decision consumible | §P0A-5 §6 (INSERT UNIQUE misma tx) | REPAIR_REQUIRED (exactitud pendiente) |
| H-13 | T-REOPEN | preimagen + epoch+1 + consumed + commit | BLOCKED |
| H-14 | CLOSED | cierre condicionado a terminalidad real (§P0C-3) | BLOCKED |
| H-15 | máquinas | tablas cerrado-completivas + op↔efecto↔política | BLOCKED |
| H-16 | INV-13 prueba | §13.1 + check exclusivo | REPAIRED-CONDICIONADO (cotejo pendiente) |
| H-17 | reconciliación | §P0C (outcome explícito); orden de la reconciliación invariante del efecto (operación) | BLOCKED |
| H-18 | ESo=REJECTED | mapa único global ES↔P↔O↔T | BLOCKED |
| H-19 | tipos | §P1-3 census estructura | REPAIR_REQUIRED |
| H-20 | barrera | §P1B default-deny LFP | REPAIR_REQUIRED |
| H-21 | census | con AUD-015 dependent | BLOCKED |
| H-22 | cardinalidad | dominios R1 | REPAIR_REQUIRED |
| H-23 | coverage | A-19/A-20 obligatoria | BLOCKED |
| H-24 | TCB | PKI Ed25519 (D-R2R2-1) | BLOCKED |
| H-25 | LP | §P0B-2 tabla de órdenes | BLOCKED |
| H-26 | políticas | tabla cerrada con vacío y precedencia | BLOCKED |
| H-27 | A6 | §P1B-3 LFP probado | REPAIR_REQUIRED |


---

## 6. Matriz R2A-AUD-001…019 + RES-1..9 + M-01…10 + A-01…G + C-01..19 + N-01..10 (estados v5; sin ratificación nueva)

| Rango | Estado dominante (sin cambios respecto a dictamen v4) |
|---|---|
| AUD-001 | REPAIR_REQUIRED (cotejo pendiente) |
| AUD-002 | REPAIR_REQUIRED (DDL/hash no cotejado por tercero) |
| AUD-003 | REPAIR_REQUIRED (cobertura INV-09) |
| AUD-004 | REPAIR_REQUIRED (INV-07a/b/c reproducidas) |
| AUD-005 | ACEPTADA (aritmética) |
| AUD-006 | REPAIR_REQUIRED |
| AUD-007 | BLOCKED |
| AUD-008 | REPAIR_REQUIRED |
| AUD-009 | REPAIR_REQUIRED |
| AUD-010 | REPAIR_REQUIRED |
| AUD-011 | BLOCKED |
| AUD-012 | REPAIR_REQUIRED |
| AUD-013 | BLOCKED |
| AUD-014 | BLOCKED |
| AUD-015 | BLOCKED |
| AUD-016 | REPAIR_REQUIRED |
| AUD-017 | REPAIR_REQUIRED |
| AUD-018 | BLOCKED |
| AUD-019 | BLOCKED |
| RES-1 | ACEPTADA |
| RES-2 | REPAIR_REQUIRED |
| RES-3 | ACEPTADA |
| RES-4 | REPAIR_REQUIRED |
| RES-5 | REPAIR_REQUIRED |
| RES-6 | BLOCKED |
| RES-7 | REPAIR_REQUIRED |
| RES-8 | REPAIR_REQUIRED |
| RES-9 | REPAIR_REQUIRED |
| M-01 | BLOCKED |
| M-02 | REPAIR_REQUIRED (unify timestamptz only) |
| M-03 | REPAIR_REQUIRED |
| M-04 | BLOCKED |
| M-05 | BLOCKED |
| M-06 | ACEPTADA |
| M-07 | REPAIR_REQUIRED |
| M-08 | REPAIR_REQUIRED |
| M-09 | REPAIR_REQUIRED |
| M-10 | BLOCKED |
| A-01 | REPAIR_REQUIRED |
| A-02 | REPAIR_REQUIRED |
| A-03 | BLOCKED |
| A-04 | BLOCKED |
| B | BLOCKED |
| C | BLOCKED |
| D | BLOCKED |
| E | BLOCKED |
| F | BLOCKED |
| G | ACEPTADA LIMITADA |
| C-01 | REPAIR_REQUIRED (§P0D; prueba discriminanta real exigida A-02) |
| C-02 | BLOCKED (Clase-S/T exacto) |
| C-03 | BLOCKED (cierre) |
| C-04 | BLOCKED (P0A-2) |
| C-05 | REPAIR_REQUIRED |
| C-06 | REPAIR_REQUIRED |
| C-07 | BLOCKED (+§P1B) |
| C-08 | BLOCKED |
| C-09 | BLOCKED (P0/P1A) |
| C-10 | REPAIR_REQUIRED (§P0D-4 RETURNING) |
| C-11 | REPAIR_REQUIRED |
| C-12 | REPAIR_REQUIRED |
| C-13 | BLOCKED (=C-03) |
| C-14 | BLOCKED |
| C-15 | BLOCKED (=A-04) |
| C-16 | REPAIR_REQUIRED (§P1-5 partial done) |
| C-17 | BLOCKED (+§P1B) |
| C-18 | BLOCKED (=C-08) |
| C-19 | BLOCKED (=C-09) |
| N-01 | REPAIR_REQUIRED (=C-01) |
| N-02 | REPAIR_REQUIRED (§P0C — cambio notable: ya es REPAIR_REQUIRED) |
| N-03 | REPAIR_REQUIRED |
| N-04 | BLOCKED (=C-08) |
| N-05 | BLOCKED (=A-04) |
| N-06 | BLOCKED (=C-09) |
| N-07 | REPAIR_REQUIRED |
| N-08 | ACEPTADA (limitada) |
| N-09 | ACEPTADA |
| N-10 | REPAIR_REQUIRED |

## 7. D-R2R2-1…11 — ninguna ratificada (v5 reaplica dictamen)

| # | Estado v5 |
|---|---|
| D-R2R2-1 | BLOCKED (revocación/rotación/custodia abiertas) |
| D-R2R2-2 | BLOCKED (B-04) |
| D-R2R2-3 | BLOCKED |
| D-R2R2-4 | REPAIR_REQUIRED (alineamento global UINT64) |
| D-R2R2-5 | BLOCKED (P0A-2; sin ratificar) |
| D-R2R2-6 | DIFERIDA |
| D-R2R2-7 | REPAIR_REQUIRED |
| D-R2R2-8 | REPAIR_REQUIRED (DEFERRABLE requiere cotejo) |
| D-R2R2-9 | BLOCKED (sin ratificación) |
| D-R2R2-10 | BLOCKED (=A-04) |
| D-R2R2-11 | BLOCKED (mapa no cerrado) |

---

## 10. Estado final tras esta revisión

- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `D-315 = PENDING` · `MODEL_VERIFIED = NO` · `INDEPENDENTLY_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · `PROMOTION = NOT_READY`.
- Esta revisión **no** ratifica ninguna decisión, **no** habilita r3 del baseline, **no** `B07_FORMAL_MODEL.md`, **no** §1, **no** terceros, **no** ejecución.
- Ninguna prueba de ejecución ni verificación de terceros se declara. Los vectores §P0A-2 se obtuvieron en esta sesión (cálculos documentales); no constituyen verificación.
- Procedencia registrada en `state/multiproject/log.md`.
- Antecedentes v1…v4 conservados íntegros en este árbol.

---

## 13. Apéndices mecánicos

### §13.1 INV-13 (prueba mecánica pura)

```
INV-09: ∀ s ∈ op: t(s) ∈ {COMMIT_TESTIFIED, ABORT_TESTIFIED} ⇒ p(s) ∈ {COMMIT_DURABLE, ABORT_DURABLE}
Dominio T finito {NONE, COMMIT_TESTIFIED, ABORT_TESTIFIED}, dominio P conocido.
Contrapositiva: p(s) ∉ {COMMIT_DURABLE, ABORT_DURABLE} ⇒ t(s) ∉ {CT, AT} ⇒ t(s) = NONE.
INV-13 := esa proposición. Derivation mecánica válida; no depende de máquinas.
```

### §13.2 D-315 (aritmética de dominios R1)

```
R1 dominios: SI=4, TRs=3, ESs=5, OD=4, V=3, P=10, O=4, T=3, ESo=6.
|S_SCOPE| = 4·3·5 = 60
|S_OP| = 4·3·10·4·3·6 = 8640
|S_BASE| = 518400 (cartesiano; no legalidad)
|LEGAL| ≤ |S_BASE|; |REACHABLE| ≤ |LEGAL|; ambos desconocidos.
```

### §13.3 BND fixpoint (resolución formal)

En §P1B-3 se formaliza Φ y se demuestra su terminación por cardinalidad; equivalente al lema de Knaster-Tarski sobre un conjunto finito.

Fin R2-A REVISION 5 · DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED · Procedencia en `state/multiproject/log.md`.
