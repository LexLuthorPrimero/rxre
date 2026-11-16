# B-07 — R2 REPAIR SPECIFICATION

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Objetivo:** especificación de reparación de R2 (contratos, invariantes, pruebas de aceptación).
**Alcance:** diseño documental. **No** modifica `IER_GATE_PLAN.md` (§1 FROZEN), ni `B07_FORMAL_MODEL.md`, ni código, DB, contratos ni archivos protegidos. **No** ejecuta protocolos. **No** inicia R3, crash injection ni promoción.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`

**Registro de revisión**
| Versión | SHA-256 | Contenido |
|---|---|---|
| v1 | `d749977f…` | DRAFT inicial; 19 hallazgos (R2A-AUD-001…019) |
| v2 | `d0fb27962832317b5ea0a2bbca68259401e3ffba682c454596c1a9d8b161536f` | Revisión R2-A.r1; re-auditoría → NOT_ACCEPTED; 27 hallazgos (H-01…H-27) comunicados por el diseñador |
| r2 (este documento) | hash publicado fuera del archivo (`state/multiproject/log.md` e informe) | Revisión R2-A.r2: integra H-01…H-27 según orden de reparación del propietario (1 cripto → 2 persistencia → 3 concurrencia/fencing/sink → 4 máquinas/recuperación → 5 barrera/censo/pruebas). Matriz de cobertura H/AUD/residuales incluida. Nada se declara cerrado sin auditoría independiente del propietario. |

Los 27 hallazgos H-01…H-27 y los 19 R2A-AUD-001…019 se consideran **atendidos documentalmente** en esta revisión. Ninguno se declara cerrado. La aceptación corresponde exclusivamente al propietario tras auditoría independiente.

---

## 0. Estado de los componentes y clasificación normativa (censo bidireccional, actualizado R2-A.r2)

| Componente | Estado |
|---|---|
| §1 `IER_GATE_PLAN.md` | `FROZEN` (`74a19ba2…`); intacta. |
| R1 — Canonical Symbol Registry | `ACCEPTED (structural)`. |
| B-03 / B-04 / B-08 | `OPEN`; autoridad final de `fencing_token` = W (propuesta de este documento, D-R2R2-2); si B-04 decide distinto, §3 se adapta sin alterar invariantes. |
| D-315 | `PENDING`. |

**Censo bidireccional — todo token normativo usado por esta especificación tiene definición y propietario:**

| Clase | Tokens | Definición | Propietario |
|---|---|---|---|
| R1 (símbolos) | OD, V, P, O, T, SI, TRs, ESs, ESo (+49 derivados) | `B07_FORMAL_MODEL.md` §R1 — semántica íntegra | Registro R1 `ACCEPTED (structural)` |
| R1.3 (nuevos) | ES-001…007, FG-001…004, PL-001…003, SC-001…003, EF-001…002 | §R2.r2.7 de este documento | Registro R1.3 (aditivo; ninguna ELEVACIÓN) |
| Funciones normativas | `EffectAdmissible`, `DispatchAuthorization`, `SinkAcceptance`, `AttemptCurrent`, `ManifestHash`, `BindingHash`, `Encode*`, `ReconciliationProtocol` | §R2.r2.1 / §R2.r2.3 / §R2.r2.4 | Este documento |
| Registros normativos | `scope_event` (SC-001), `REOPEN_EVIDENCE` (FG-001), `reconciliation_record` (SC-002), `BLOCKED_SYMBOLS` (FG-003), `consumed_decision`, `manifest` | §R2.r2.2 | Este documento |
| Tipos normativos | `Manifest`, `EffectDescriptor`, `EffectMessage` | §R2.r2.1 | Este documento |
| Campos del modelo persistente | `scope.next_fence`, `scope.minimum_valid_fence`, `operation.current_attempt_*`, `attempt.*`, `manifest.effects_canon` | §R2.r2.2; cada columna participa en ≥1 regla y ≥1 test | Este documento |
| Identificadores de protocolo/prueba | `T-SUSPEND`, `T-REOPEN`, `T13`, `T-CLOSE`, `A-*`, `INV-*`, `H-*`, `BND` | documentación, no símbolos de estado | Este documento |
| Tag de dominio criptográfico | `IER-effect-manifest-v1\0`, `IER-binding-v1\0`, `IER-attempt-v1\0`, `IER-reopen-v1\0` | §R2.r2.1; espera verificación de colisión de tags por censo | Este documento |

Regla: ningún token normativo puede entrar sin clasificar aquí o en R1/R1.3. El verificador A-01 lo comprueba en las dos direcciones (usado ⇒ registrado; registrado ⇒ usado o marcado de uso futuro).

---

## 1. Matriz de hallazgos → reparación propuesta (H-01…H-27)

| Hallazgo | Bloque | Sección |
|---|---|---|
| H-01 | 1 Criptografía | §R2.r2.1.1–§R2.r2.1.2, §R2.r2.1.6 (vectores) |
| H-02 | 1 Criptografía | §R2.r2.1.2, §R2.r2.1.3 |
| H-09 | 1 Criptografía | §R2.r2.1.4, §R2.r2.2, §R2.r2.3 |
| H-10 | 1 Criptografía | §R2.r2.1.5, §R2.r2.2, §R2.r2.3 |
| H-11 | 1 Criptografía | §R2.r2.1.7 |
| H-03 | 2 Persistencia | §R2.r2.2.2–§R2.r2.2.5 |
| H-04 | 2 Persistencia | §R2.r2.2.6 |
| H-07 | 2 Persistencia | §R2.r2.2.3, §R2.r2.2.4 |
| H-08 | 2 Persistencia | §R2.r2.2.4 |
| H-12 | 2 Persistencia | §R2.r2.2.7 |
| H-19 | 2 Persistencia | §R2.r2.2.8 |
| H-05 | 3 Concurrencia/sink | §R2.r2.3.1–§R2.r2.3.2 |
| H-20 | 5 Barrera | §R2.r2.5.1 |
| H-24 | 3 Concurrencia/sink | §R2.r2.3.4 |
| H-25 | 3 Concurrencia/sink | §R2.r2.3.3 |
| H-06 | 4 Máquinas | §R2.r2.4.2 |
| H-13 | 4 Máquinas | §R2.r2.4.2–§R2.r2.4.3 |
| H-14 | 4 Máquinas | §R2.r2.4.4 |
| H-15 | 4 Máquinas | §R2.r2.4.5–§R2.r2.4.14 |
| H-17 | 4 Máquinas | §R2.r2.4.10 |
| H-18 | 4 Máquinas | §R2.r2.4.9 |
| H-16 | 5 Invariantes | §R2.r2.5.3 |
| H-21 | 5 Censo | §R2.r2.5.2 |
| H-22 | 5 Cardinalidad | §R2.r2.5.4 |
| H-23 | 5 Pruebas | §R2.r2.5.5 (A-03) |
| H-26 | 5 Políticas | §R2.r2.5.6 |
| H-27 | 5 Barrera | §R2.r2.5.1 |

Correspondencia con H-01…H-27 y con los 19 hallazgos R2A-AUD-001…019 y las 9 notas residuales: ver matriz completa en §7.5 (trazabilidad tripartita).

---

# R2.r2.1 — Contratos criptográficos y codificación canónica (H-01, H-02, H-09, H-10, H-11)

## R2.r2.1.1 Algoritmo, tags y versionado

```
H := SHA-256 (256 bits). Salida: 32 octetos crudos.
Tag(tag_name) := ASCII(tag_name) ‖ 0x00   // terminado en NUL; longitud fija por variante; sin alias.
Domain separators (exactas):
  'IER-attempt-v1\0'        — preimagen de attempt_id
  'IER-effect-manifest-v1\0'— preimagen de manifest_hash
  'IER-binding-v1\0'        — preimagen de binding_hash
  'IER-reopen-v1\0'         — firma de verificación de evidencia de reapertura
Formato inmutable: cualquier cambio semántico ⇒ tag nuevo (v2...), nunca edición retroactiva.
```

Regla de no-ambigüedad: toda preimagen es una secuencia de campos codificados con longitudes explícitas o anchuras fijas declaradas. **Ninguna concatenación admite ambigüedad de corte.**

## R2.r2.1.2 Encoders y tipos (normativa cerrada)

| Tipo | Codificación | Rango |
|---|---|---|
| UINT8 | 1 octeto | 0…255 (generation 1…255) |
| UINT16 | 2 octetos LE | 0…65535 (`effect_kind`, `effect_ordinal`, `manifest_version`, `io` tags de política) |
| UINT64 | 8 octetos LE | 0…2^64−1 (`scope_epoch`, `policy_version`, `minimum_valid_fence`, `next_fence`, `claim_generation`, `decided_at` opcional) |
| BOOL | 1 octeto (`0x00`/`0x01`) | — |
| BYTES[n] | n octetos crudos | n declarado (`scope_id`, `operation_id`, `request_id`, `attempt_id`, `effect_binding`, `manifest_hash` de 32 octetos) |
| VBYTES | `uint64_le(len)` ‖ bytes | longitud explícita |

`encode(x)` = codificación del tipo declarado con ancho fijo. `encode_bytes(b)` = `uint64_le(len(b)) ‖ b`.
Lista canónica de efectos (`encode_effects_canonical`): orden total por `effect_ordinal` ascendente (único, denso, 0…n−1). `effect_kind` **no** participa en el orden; es una etiqueta de clasificación. Duplicado de `effect_ordinal` ⇒ manifiesto rechazado. Identidad de un efecto: `(operation_id, effect_ordinal)`.

```
ManifestHash := SHA-256(
    Tag('IER-effect-manifest-v1')
  ‖ encode(UINT16 manifest_version)
  ‖ encode(UINT8  policy_tag(policy))        // UNSPECIFIED=255 inválido; NONE=0, ANY=1, ALL=2
  ‖ encode_bytes(scope_id)                   // 32 B
  ‖ encode(UINT64 scope_epoch)
  ‖ encode_bytes(operation_id)               // 32 B
  ‖ encode(UINT64 policy_version)
  ‖ uint64_le(len(effects))
  ‖ concat(e ∈ effects ordenados por effect_ordinal :
             encode(UINT16 e.effect_kind) ‖ encode(UINT16 e.effect_ordinal) ‖ encode_bytes(e.effect_binding)))

AttemptId := SHA-256(
    Tag('IER-attempt-v1')
  ‖ encode_bytes(scope_id)
  ‖ encode_bytes(operation_id)
  ‖ encode_bytes(request_id)
  ‖ encode(UINT8 attempt_generation))        // 1…255

BindingHash := SHA-256(
    Tag('IER-binding-v1')
  ‖ encode_bytes(ManifestHash)               // SHA-256(ManifestHash).raw, 32 octetos
  ‖ encode_bytes(attempt_id)
  ‖ encode_bytes(request_id))
```

`request_id` aparece en `attempt_id` (y por tanto en `binding_hash` y `manifest binding` vía attempt). La identidad de petición es inmutable y única por `(scope_id, scope_epoch, operation_kind, request_id)` (operación) y por `attempt_id` (intento).

## R2.r2.1.3 Identidad y orden de efectos (H-02)

- `effect_ordinal`: índice **global al manifiesto**, denso 0…n−1, no local por `effect_kind`.
- Orden de serialización (`encode_effects_canonical`) = orden de `effect_ordinal`. 
- Identidad de efecto = (`operation_id`, `effect_ordinal`); el `binding_hash` de intento cubre el conjunto ordenado; alterar cualquier efecto, su orden o su ordinales ⇒ `ManifestHash` distinto ⇒ `BindingHash` distinto ⇒ sink rechaza.
- Prueba A-05/A-19: mismo manifiesto con ordinales permutados ⇒ hashes distintos.

## R2.r2.1.4 Binding por intento: inmutabilidad e historia (H-09)

- **No** existe `operation.binding_hash`. Se elimina. El binding es propiedad del **intento**, construido desde `manifest_hash` + `attempt_id` + `request_id`.
- `attempt.binding_hash` es inmutable una vez insertado (ningún UPDATE toca esa fila; sello por transacción del claim).
- Relación operación↔binding vigente = puntero `operation.current_attempt_id` → fila de intento → su `binding_hash`. El binding histórico de cada intento permanece (auditabilidad).
- Reintento legítimo = nuevo `attempt` bajo misma operación: su `attempt_id` cambia ⇒ su `BindingHash` cambia ⇒ mensajes preparados bajo el intento anterior son inválidos por fallo de `AttemptCurrent`.
- Sink: `envelope.binding_hash == head_attempt.binding_hash` verifica la vinculación completa (ver §R2.r2.3); el intento histórico no puede inyectarse por el head-pointer CAS (§R2.r2.2.6).

## R2.r2.1.5 Idempotencia antes y después de REOPEN (H-10)

| Situación | Comportamiento de la petición repetida |
|---|---|
| Epoch idéntico, request repetida, operación no terminal | Devuelve la operación existente (idempotente por índice `operation_scope_epoch_kind_request` §R2.r2.2); ningún efecto duplicado. |
| Epoch nuevo (tras `T-REOPEN`), misma request | Crea operación **nueva** (nueva fila, nuevo `scope_epoch`, nuevo intento); no toca la antigua (suspendida). |
| Epoch idéntico tras crash | Reintento idempotente: o reanuda el intento cabeza o crea `attempt_generation` siguiente bajo la misma operación, nunca duplica efecto externo (bind/orden verificados). |
| Mismo request dentro del mismo epoch con `operation_kind` distinto | Nueva operación (el kind forma parte del índice); documentado: un request puede dar lugar a obligaciones de efecto distintas con semánticas distintas. |

Correspondencia con identidad de efecto: tras REOPEN, efectos de la solicitud re-emitida son **distintos** de los antiguos; `effect_ordinal` se reutiliza en el manifiesto nuevo, no en los mensajes del epoch viejo.

## R2.r2.1.6 Vectores de prueba reproducibles (contrato normativo; no ejecutan implementación)

Determinados aplicando este contrato a las entradas siguientes (constantes publicables; re-verificables con cualquier SHA-256):

```
Constantes: scope_id=0x11*32, operation_id=0x22*32, request_id=0x44*32,
            effect_binding=0x33*32 (vector 1), kind=3 kind-ord-0 / kind=1 ord-1 (vector 2)
Vector 1: manifest_version=1, policy=NONE(0), scope_epoch=7, policy_version=1,
          effects=[kind=1, ordinal=0, binding=0x33*32]
  attempt_id    = 2343e895d1d413916d14a61339c59e23508e0f50d41978ed02fc3153beda913d
  manifest_hash = 3cdf3a0a091bced7c43282c21f3abd1a9d787784d347ed0be5b732fd52f03a1e
  binding_hash  = 387c9aa4c47bd6b5f5c2045c1e6518f610a1db0aa891e8995c240c9057ff0ab5
Vector 2: manifest_version=1, policy=ALL(2), scope_epoch=7, policy_version=9,
          effects=[A(kind=3, ordinal=0, binding=0xa0*32), B(kind=1, ordinal=1, binding=0xb0*32)]
  manifest_hash = cf57ef5d746e19882741e7fe6c535eba65856e461ed9a49058d3556dbe27f267
```

Nota de procedencia: estos vectores se obtuvieron aplicando este contrato con `hashlib.sha256` (cálculo documental; ninguna implementación del sistema se ejecutó). Cualquier revisor independiente debe reproducirlos.

## R2.r2.1.7 Protocolo completo de `fencing_token` (H-11)

```
Autoridad: W (policy/claim engine) co-locado con el almacén del scope. Un pod W actúa de único emisor por scope mediante ROW LOCK del scope (SELECT … FOR UPDATE) durante el claim.
Asignación atómica: el claim de intento incrementa `scope.next_fence` y asigna `fencing_token := old_next_fence` dentro de la misma transacción que inserta el intento y actualiza el head-pointer (CAS §R2.r2.2.6).
Monotonía: next_fence nunca retrocede ni se recicla; tokens emitidos viven en `attempt` y son únicos por fila.
Overflow: si next_fence == 2^64−1, el claim aborta y emite `scope_event{kind=FENCING_EXHAUSTION}`; no se emiten tokens agotados; el scope requiere T13 (cierre humano) o T-REOPEN (epoch nuevo con next_fence reiniciado a 0 SOLO con decisión durable y registro de agotamiento).
Relación con claim_generation: claim_generation (por operación, 1…255… ver §R2.r2.2.8) es el índice de intento de la OPERACIÓN; fencing_token es el índice GLOBAL del SCOPE; nunca coinciden obligatoriamente ni se derivan uno de otro.
Validación independiente en el sink: fencing_token del mensaje ≥ scope.minimum_valid_fence leído EN la ventana de decisión del sink (§R2.r2.3); el sink rechaza mensajes con token menor o igual a mínimo−1; tokens no correlacionados con ninguna fila attempt válida y vigente también se rechazan.
Consumo: el sink no «consume» tokens (son identidades inmutables); rechaza/acepta; la validez temporal depende del fence vigente.
```

## R2.r2.1.8 Tipo `decision_id` (uso criptográfico)

`decision_id := SHA-256(Tag('IER-consume-v1') ‖ encode_bytes(source_kind) ‖ encode_bytes(scope_id) ‖ encode(UINT64 decided_at) ‖ encode(BYTES salt16))` — único y no reutilizable; su persistencia y consumo atómico se definen en §R2.r2.2.7; índice UNIQUE; tampering ⇒ firma inválida en la verificación del payload de decisión correspondiente.

---

# R2.r2.2 — Modelo persistente e integridad referencial (H-03, H-04, H-07, H-08, H-12, H-19)

## R2.r2.2.1 Convenciones del almacén

- Una única escritura sincrónica; lectura consistente cuando el sink decide (§R2.r2.3).
- Ningún `UPDATE`/`DELETE` permitido sobre tablas de sello/evidencia (`manifest`, `scope_event`, `reopen_evidence`, `blocked_symbols`, `reconciliation_record`, `consumed_decision`): sólo `INSERT`. Las filas jamás cambian de contenido. La auditoría histórica es por consulta, nunca por mutación.
- Toda transición que cambia `scope.si`, `scope.minimum_valid_fence`, `scope.next_fence`, `scope.scope_epoch`, head-pointer o estado de operación ocurre en **una sola** transacción SQL; sin pasos fuera de ella (§R2.r2.3, §R2.r2.4).
- Nombres de tokens: dominio canónico `RECONCILIATION_REQUIRED` (H-07 corrige el typo `RECONCILE_REQUIRED`).

## R2.r2.2.2 `scope`

```sql
CREATE TABLE scope (
  scope_id              bytea PRIMARY KEY CHECK (octet_length(scope_id) = 32),
  scope_epoch           bigint NOT NULL CHECK (scope_epoch >= 0),
  si                    text NOT NULL CHECK (si IN ('HEALTHY','ROLLBACK_DETECTED','RECONCILIATION_REQUIRED','HUMAN_CLOSED')),
  trs                   text NOT NULL CHECK (trs IN ('VALID','QUARANTINED','NOT_DETERMINED')),
  ess                   text NOT NULL CHECK (ess IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','CONTRADICTION')),
  minimum_valid_fence   bigint NOT NULL DEFAULT 0 CHECK (minimum_valid_fence >= 0),
  next_fence            bigint NOT NULL DEFAULT 0 CHECK (next_fence >= 0)  -- H-11
);
```
`next_fence` es el contador emisor de `fencing_token`; `minimum_valid_fence` es el piso aceptado. Ambos monotónicos por contrato; jamás retroceden.

## R2.r2.2.3 `scope_event` (esquema y relación transaccional, H-07)

```sql
CREATE TABLE scope_event (
  event_id        bytea PRIMARY KEY CHECK (octet_length(event_id) = 32),
  scope_id        bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT,
  scope_epoch     bigint NOT NULL,
  kind            text NOT NULL CHECK (kind IN ('ROLLBACK_DETECTED','RECONCILIATION_REQUIRED','HUMAN_CLOSED','FENCING_EXHAUSTION','CONTRADICTION_ARBITRATION')),
  evidence_hash   bytea NOT NULL CHECK (octet_length(evidence_hash) = 32),
  emitter         text NOT NULL,          -- autoridad emisora (p.ej. 'W', 'A')
  created_at      timestamptz NOT NULL DEFAULT now(),
  -- Relación con la transición: el evento y la transición se confirman en la misma tx.
  CONSTRAINT scope_event_integral CHECK (octet_length(scope_id) = 32)
);
```

Transacción `T-SUSPEND`: el evento `scope_event` se inserta **en la misma transacción** que el `UPDATE scope` y la suspensión masiva de operaciones; si el evento existe pero la transición falla, todo aborta (no hay eventos huérfanos sin su efecto, ni suspensiones sin evento que las explique).

## R2.r2.2.4 `operation`

```sql
CREATE TABLE operation (
  operation_id               bytea PRIMARY KEY CHECK (octet_length(operation_id) = 32),
  scope_id                   bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT,
  scope_epoch                bigint NOT NULL,                 -- fijo de creación; ver INV-02
  od                         text NOT NULL CHECK (od IN ('NOT_EVALUATED','ADMITTED','BLOCKED','NOT_DETERMINED')),
  v                          text NOT NULL CHECK (v  IN ('OPEN','SUSPENDED','CLOSED')),
  p                          text NOT NULL CHECK (p  IN ('NOT_STARTED','RESERVE_REQUESTED','RESERVE_DURABLE','RESERVED_CONFIRMED','EXECUTING','COMMIT_DURABLE','ABORT_DURABLE','RECOVERABLE','RESERVE_ORPHAN','FAILED_CONSUMED')),
  o                          text NOT NULL CHECK (o  IN ('NONE','COMMITTED','NOT_EXECUTED','UNKNOWN')),
  t                          text NOT NULL CHECK (t  IN ('NONE','COMMIT_TESTIFIED','ABORT_TESTIFIED')),
  eso                        text NOT NULL CHECK (eso IN ('ABSENT','RECEIVED','VERIFIED','REJECTED','TESTIFICATION_PENDING','TESTIFIED')),
  operation_kind             text NOT NULL,
  current_attempt_id         bytea NOT NULL,
  current_attempt_generation smallint NOT NULL CHECK (current_attempt_generation BETWEEN 1 AND 255),
  manifest_hash              bytea NOT NULL CHECK (octet_length(manifest_hash) = 32),
  policy_version             bigint NOT NULL CHECK (policy_version >= 0),
  request_id                 bytea NOT NULL CHECK (octet_length(request_id) = 32),
  UNIQUE (scope_id, operation_id),       -- permite FK compuesta desde attempt (H-08)
  UNIQUE (scope_id, scope_epoch, operation_kind, request_id)  -- idempotencia de petición (H-10)
);
```

Notas de integridad:
- `operation` no almacena `binding_hash` (H-09). Su integridad de binding es composicional vía `current_attempt_id` → `attempt`.
- FK `operation.scope_id → scope.scope_id` (NOT NULL, `ON DELETE RESTRICT`). La `UNIQUE(scope_id, operation_id)` existe para la FK compuesta de `attempt` (H-08); no es redundante con la PK (la PK no incluye `scope_id`).

## R2.r2.2.5 `attempt` (persistencia de intentos, H-08, H-19)

```sql
CREATE TABLE attempt (
  scope_id            bytea NOT NULL,
  operation_id        bytea NOT NULL,
  attempt_id          bytea PRIMARY KEY CHECK (octet_length(attempt_id) = 32),
  attempt_generation  smallint NOT NULL CHECK (attempt_generation BETWEEN 1 AND 255),  -- ≡ UINT8 canónico
  claim_generation    bigint NOT NULL CHECK (claim_generation >= 1 AND claim_generation < 2^64),  -- ≡ UINT64 canónico
  fencing_token       bigint NOT NULL CHECK (fencing_token >= 0 AND fencing_token < 2^64),
  binding_hash        bytea NOT NULL CHECK (octet_length(binding_hash) = 32),
  -- Integridad referencial compuesta (H-08): el intento solo existe bajo su propia operación y scope:
  FOREIGN KEY (scope_id, operation_id) REFERENCES operation(scope_id, operation_id) ON DELETE RESTRICT,
  UNIQUE (operation_id, attempt_generation),
  UNIQUE (operation_id, claim_generation),
  UNIQUE (scope_id, operation_id, attempt_id),
  UNIQUE (scope_id, fencing_token)   -- cada token emitido por el scope es único (H-11)
);
```

Tipos (H-19):
- `attempt_generation` — el canon dice UINT8; SQL `smallint CHECK BETWEEN 1 AND 255` es representación cerrada exacta; sin truncamiento.
- `claim_generation` — el canon v2-4.2R dice UINT8, v2 de este documento dijo bigint. Se resuelve: **UINT64 canónico** (`claim_generation_abi := bigint CHECK < 2^64`). El canon artefacto `B07_FORMAL_MODEL.md` §R2.3 habla de UINT8; esa sección permanece `REPAIR_REQUIRED` y se alinea al emitirse la revisión de ese artefacto; este documento declara explícitamente la divergencia y su resolución (UINT64), sin tocar el artefacto ni §1.
- `fencing_token` — UINT64 canónico; `bigint CHECK < 2^64`.

## R2.r2.2.6 Puntero cabeza con CAS (H-04)

```
SET_HEAD_ATTEMPT(op, expected_generation, new_attempt):
  Una sola transacción que inserta el nuevo intento (§R2.r2.2.5) y ejecuta:
    UPDATE operation
       SET current_attempt_id = :new_attempt_id,
           current_attempt_generation = :expected_generation + 1
     WHERE operation_id = :op
       AND current_attempt_generation = :expected_generation;
  Filas afectadas = 1 ⇒ éxito (nueva cabeza publicada).
  Filas afectadas = 0 ⇒ abort(controlado): otro claim concurrente ganó; nadie pisa la cabeza.
  El efecto del claim (insertar intento + link) es atómico; jamás hay dos intentos cabeza para la misma operación; jamás head-pointer se mueve sin generar el intento.
  Reintento legítimo tras crash del originador: recomienza por expected_generation consultando head; idempotente vía UNIQUE del intento (request_id único).
```

Head-pointer íntegro: `operation.current_attempt_*` SIEMPRE apunta a una fila `attempt` existente del mismo scope y operación; INV-17 (§R2.r2.5.7). FK verificable en A-02.

## R2.r2.2.7 Consumo único atómico de `decision_id` (H-12)

```sql
CREATE TABLE consumed_decision (
  decision_id   bytea PRIMARY KEY CHECK (octet_length(decision_id) = 32),
  scope_id      bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT,
  consumed_by   text NOT NULL CHECK (consumed_by IN ('T-SUSPEND','T-REOPEN','T13','RECONCILE')),
  consumed_at   timestamptz NOT NULL DEFAULT now()
);
```
T13, T-REOPEN y cierre de reconciliación: `INSERT consumed_decision` en la **misma** transacción; un `decision_id` ya consumido ⇒ INSERT falla (la transacción entera aborta) ⇒ ningún cierre parcial. Doble reapertura/cierre concurrentes con el mismo `decision_id`: exactamente una transición ocurre; la otra falla limpiamente por conflicto de PK.

## R2.r2.2.8 `manifest` durable e inmutable (H-03)

```sql
CREATE TABLE manifest (
  operation_id     bytea PRIMARY KEY REFERENCES operation(operation_id) ON DELETE RESTRICT,
  manifest_version smallint NOT NULL CHECK (manifest_version = 1),
  policy           smallint NOT NULL CHECK (policy IN (0,1,2)),  -- NONE,ANY,ALL
  scope_epoch      bigint NOT NULL,
  policy_version   bigint NOT NULL,
  effects_canon    bytea NOT NULL,     -- contenido EXACTO de encode_effects_canonical(effects)
  effects_count    bigint NOT NULL CHECK (effects_count >= 0),
  manifest_hash    bytea NOT NULL UNIQUE CHECK (octet_length(manifest_hash) = 32),
  sealed_at        timestamptz NOT NULL DEFAULT now()
  -- Inmutabilidad: 0 UPDATE/DELETE por diseño del almacén y por contrato W/A (Append-Only).
);
```

`effects_canon` es la fuente de verdad de los efectos: el sink re-lee `effects_canon`, recalcula `ManifestHash` y verifica contra `operation.manifest_hash` (que vive solo en `operation.manifest_hash`) (§R2.r2.1.2/§R2.r2.1.3). Cualquier discrepancia ⇒ rechazo. Verificación de integridad en línea: recalcular y comparar no cuesta I/O adicional significativo y cierra la ventana de aceptación de manifiestos falsificados.

## R2.r2.2.9 `reopen_evidence` y `reconciliation_record`

```sql
CREATE TABLE reopen_evidence (
  decision_id    bytea PRIMARY KEY CHECK (octet_length(decision_id) = 32),   -- ver §R2.r2.4.2
  scope_id       bytea NOT NULL REFERENCES scope(scope_id) ON DELETE RESTRICT,
  scope_epoch    bigint NOT NULL,
  opened_epoch   bigint NOT NULL CHECK (opened_epoch = scope_epoch + 1),
  verifier_id    bytea NOT NULL CHECK (octet_length(verifier_id) = 32),
  issuer         bytea NOT NULL CHECK (octet_length(issuer) = 32),
  reason         text NOT NULL CHECK (reason IN ('ROLLBACK_RESOLVED','RECONCILE_RESOLVED')),
  evidence_hash  bytea NOT NULL CHECK (octet_length(evidence_hash) = 32),
  signature      bytea NOT NULL CHECK (octet_length(signature) = 64),
  schema_version smallint NOT NULL CHECK (schema_version = 1),
  sealed_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reconciliation_record (
  reconciliation_id bytea PRIMARY KEY CHECK (octet_length(reconciliation_id) = 32),
  operation_id      bytea NOT NULL,
  attempt_id        bytea NOT NULL,
  effect_ordinal    smallint NOT NULL CHECK (effect_ordinal >= 0),
  effect_binding    bytea NOT NULL CHECK (octet_length(effect_binding) = 32),
  verdict           text NOT NULL CHECK (verdict IN ('VERIFIED','REJECTED','CONTRADICTION')),   -- dominio ES (H-17)
  verifier_id       bytea NOT NULL CHECK (octet_length(verifier_id) = 32),
  evidence_hash     bytea NOT NULL CHECK (octet_length(evidence_hash) = 32),
  decision_id       bytea NOT NULL UNIQUE,           -- replay ⇒ rechazo (H-17)
  decided_at        timestamptz NOT NULL,            -- orden total sobre reconciliación del efecto
  FOREIGN KEY (scope_id, operation_id, attempt_id) REFERENCES attempt(scope_id, operation_id, attempt_id) ON DELETE RESTRICT
);
```

`reconciliation_record` vincula veredicto con su efecto exacto `(operation_id, attempt_id, effect_ordinal, effect_binding)` (H-17). `decided_at` obligatorio con orden total; `decision_id` UNIQUE ⇒ replay rechazado; dos veredictos para el mismo efecto permitidos (ambos se conservan) y si alguno es `CONTRADICTION` ⇒ scope `ess := CONTRADICTION` (§R2.r2.4.10).

## R2.r2.2.10 `blocked_symbols` (FG-003)

```sql
CREATE TABLE blocked_symbols (
  symbol       text PRIMARY KEY,
  source_doc   text NOT NULL,
  reason       text NOT NULL,
  decided_by   text NOT NULL,
  decided_at   timestamptz NOT NULL DEFAULT now()
);
```

Append-only (INSERT). Fuente del verificador A-09 (§R2.r2.5.1). Prohibido UPDATE/DELETE.

---

# R2.r2.3 — Autorización, concurrencia, fencing y linealización del sink (H-05, H-20, H-24, H-25)

## R2.r2.3.1 Protocolo de encolado del origen

```
DispatchAuthorization(effect, scope, operation, attempt) :=
    EffectAdmissible(effect, scope, operation, attempt)   // §R2.r2.3.5
  ∧ attempt.fencing_token ≥ scope.minimum_valid_fence
```

El origen evalúa esta guarda **antes** de encolar el `EffectMessage` (EF-002). Es una condición necesaria; **nunca** sustituye la decisión del sink.

## R2.r2.3.2 Sink autoritativo con exclusión mutua respecto a T-SUSPEND (H-05)

El defecto crítico encontrado por el diseñador: una lectura consistente NO impide que un efecto se ejecute después de que T-SUSPEND haya confirmado `fence+1` — check-then-act es insuficiente. Solución: **sección crítica mutua sink ↔ T-SUSPEND sobre la fila `scope`**.

```
SinkAcceptance(envelope, input):
  Transacción del sink (almacén del sink co-locado con el scope):
    1. WITH row := SELECT * FROM scope WHERE scope_id = envelope.scope_id FOR UPDATE;   -- toma el mismo lock que T-SUSPEND
    2. Leer operation (FOR SHARE o FOR UPDATE dentro de la misma tx), attempt (head), manifest (recompute);
    3. Verificación autoritativa (§R2.r2.3.5): todas las condiciones simultáneamente;
    4. Si falla alguna ⇒ ROLLBACK; el mensaje se rechaza; el sink devuelve sin ejecutar el efecto.
    5. Si pasan ⇒ ejecutar el efecto externo. El efecto es parte de la decisión del sink o está bajo su contrato de confirmación (durable o queda UNKNOWN/PENDIENTE).
    6. INSERT/UPDATE del estado de efecto (ES-002 DISPATCHED) en la MISMA transacción si el efecto es confirmado durable dentro de ella; si la comprobación del efecto requiere interacción externa que no cabe en la tx, el sink registra ES-007 UNKNOWN y ejecuta la reconciliación obligatoria; jamás emite el efecto y luego «olvida» registrarlo.
    7. COMMIT. El lock se libera al final.
  T-SUSPEND: toma LA MISMA fila con FOR UPDATE; espera a que la tx del sink cierre (o aborta); su progreso implica que el sink terminó su decisión con fence antiguo o la rechazó.
```

**Linealización real, no lectura consistente**: el punto de linealización del sink es la **adquisición del lock de fila `scope`** (§R2.r2.3.3). El punto de linealización de T-SUSPEND es el mismo. No hay mensaje aceptado «a caballo» entre ambas:
- Ocurre sink antes ⇒ el efecto se ejecuta bajo el fence antiguo válido en su LP; T-SUSPEND espera y confirma después (efecto ya producido: admitido por el contrato, recuperable por ES-*/ReconciliationProtocol).
- Ocurre T-SUSPEND antes ⇒ el sink lo observa: `si≠HEALTHY` o `fence` elevado ⇒ rechazo; ningún efecto.
- No existe tercer resultado.

Se asume co-ubicación lógica sink↔scope (mismo motor, o columnas de recencia vía protocolo declarado; si fueran sistemas separados, la garantía debe reforzarse con un comparador CAS sobre (scope_id, scope_epoch, minimum_valid_fence) post-ejecución y un retract idempotente — está por fuera del alcance de R2-A y se declara en §8 incompatibilidades/decisiones).

## R2.r2.3.3 Casos adversariales y resultados exigidos (H-25)

| # | Escenario | Orden de adquisición del lock | Resultado exigido |
|---|---|---|---|
| HP-1 | Sink valida con fence=10; T-SUSPEND pone fence=11 después | sink primero, T-SUSPEND después | Mensaje válido: efecto ejecuta bajo fence=10 (era válido en su LP); T-SUSPEND espera; fence pedido/emitido después es 11. Sin efecto NO autorizado en ningún instante. |
| HP-2 | T-SUSPEND confirma fence=11; sink recibe mensaje preparado con fence=10 después | T-SUSPEND primero, sink después | Sink rechaza (`si≠HEALTHY` o fence insuficiente); el efecto **no** se produce. |
| HP-3 | Sink inició tx, T-SUSPEND concurrente; deadlock del almacén | cualquiera | El motor aborta una de las dos; la abortada reintenta; nunca ambas progresan sin orden. |
| HP-4 | Crash del sink tras aceptar el mensaje pero antes del efecto | no aplica (post-commit del sink) | No posible: el registro ES-002 se hace en la misma tx (paso 6). Crash intermedio ⇒ la tx completa o nada; la decisión del sink no queda a medias. |
| HP-5 | Crash del efecto externo confirmado pero no registrado | post-ejecución | Reconciliación obligatoria vía SC-002; nunca silencio (INV-05). |
| HP-6 | Reentrega del mensaje (replay) | sink como cualquiera | El binding/hash del envelope sigue verificándose contra la cabeza de intento vigente y fence vigente; un replay de un mensaje antes válido puede seguir siendo válido si el head-pointer no cambió — pero el efecto duplicado lo impide la unicidad `effect_ordinal`/idempotencia de ejecución interna del sink (registro durable único por (operation_id, effect_ordinal, fence-window) o confirmación idempotente del efecto externo). |

HP-6 sub-regla normativa para efectos externos no idempotentes: la unicidad definitiva del efecto depende de que el efecto externo soporte idempotencia (idempotency-key derivada de `(operation_id, effect_ordinal)`) o de que el protocolo de saga lo compense; sin ninguna de las dos propiedades el efecto queda en ES-007 y se reconcilia (nunca se re-ejecuta a ciegas). El sink no reejecuta efectos ya en estado `DISPATCHED`, `ACKNOWLEDGED`, `OBSERVED`, `VERIFIED` o con ES-007 pendiente de veredicto.

## R2.r2.3.4 Frontera de confianza y ausencia de bypass (H-24)

```
Confiables (trusted computing base):
  - W (policy/claim) — único emisor de intentos, head-pointers, evidence.
  - Sink executor — único autorizado a ejecutar efectos externos (H-05).
  - Almacén durable — única fuente de verdad de scope, operación, intento, manifiesto, evidencias.
No confiables:
  - Cliente/productor de peticiones; observadores externos; cualquier actor sin credencial del sink.
Credenciales y autoridad:
  - Cada componente tiene identidad criptográfica (Ed25519, propuesta D-R2R2-1); las autorizaciones viajan firmadas o en canal autenticado; ninguna decisión se toma sobre bytes no autenticados.
Interfaces permitidas:
  - Cliente → W (petición). W → origen (prevalidación). Origen → Sink (EffectMessage autenticado). Sink → almacén (único camino de efectos). Sink → cliente (resultado opaco; no se expone información de alcance).
  - Cualquier otra vía de ejecución de efectos (llamadas directas, tools alternativos, jobs basados en lectura de scope) está prohibida por construcción y por A-11/A-19.
Demostración de ausencia de bypass (obligación de verificación, no afirmación):
  - A-11: intento de despacho sin sink ⇒ imposible por arquitectura; test de integración lo verifica.
  - A-19: programa de análisis estático sobre el módulo de efectos: resolución de llamadas a adaptadores de efecto externos sólo desde Sink executor; fuera ⇒ build falla.
  - A-20: auditoría de permisos: ACL del almacén sólo permite INSERT/UPDATE de entidades de dispatch al sink.
  - Esta especificación no afirma que bypass sea imposible; afirma el mecanismo y el test que debe demostrarlo.
```

## R2.r2.3.5 `EffectAdmissible` (origen/sink — guarda completa, normativa)

```
EffectAdmissible(effect, scope, operation, attempt) :=
    operation.od == ADMITTED                         // R1 OD-002 (D-R2A-3/4)
  ∧ operation.v  == OPEN                             // R1 V-001
  ∧ scope.si     == HEALTHY                          // R1 SI-001
  ∧ scope.trs    == VALID                            // R1 TR-001 (D-R2A-1)
  ∧ scope.ess    ∈ {ABSENT, RECEIVED, VERIFIED}      // R1 ESS-001/002/003 (D-R2A-2)
  ∧ operation.scope_epoch == scope.scope_epoch        // INV-02
  ∧ effect       ∈ manifest.effects                   // manifiesto persistido + hash verificado (R2.r2.2.8)
  ∧ AttemptCurrent(attempt, operation)                 // puntero cabeza
  ∧ attempt.attempt_generation == operation.current_attempt_generation
  ∧ operation.current_attempt_id == attempt.attempt_id
  ∧ attempt.fencing_token ≥ scope.minimum_valid_fence
  ∧ recompute(ManifestHash, manifest) == operation.manifest_hash   // sólo en verificar/insertar; ver A2-reglas
```

`SinkAcceptance` = evaluación de `EffectAdmissible` sobre filas re-leídas en la propia tx del sink + chequeos de manifiesto y fence (§R2.r2.3.2). Origen (`DispatchAuthorization`) es prevalidación, nunca autoridad.

Invariantes relacionadas: INV-02/03/04/05/11/12/17 (§R2.r2.5.7).

## R2.r2.3.6 Reconciliación ante horizonte (integración con §R2.r2.4.10)

Todo efecto con outcome no demostrable queda ES-007; la operación no cierra mientras exista ES-007; el cierre requiere veredicto SC-002 por efecto; sin que el sink «olvide» ningún efecto encolado (re-suma vía reconciliation loop sobre `operation.p=EXECUTING` con fence envejecido — detalles §R2.r2.4.10).

---

# R2.r2.4 — Máquinas de estados y recuperación (H-06, H-13, H-14, H-15, H-17, H-18)

## R2.r2.4.1 Convención de las tablas

Cada tabla declara: **estado origen → evento/verbo → guarda → persistencia atómica → postcondición → autoridad → ante fallo**. «Ante fallo» indica resultado tras crash/intermitencia: `SIN TRANSICION` (nada persiste) o `ROLLBACK total`.

Persistencia atómica significa **una sola transacción** del almacén; ninguna tabla enumera transiciones sin persistencia asociada.

## R2.r2.4.2 `REOPEN_EVIDENCE` — esquema cerrado y verificación (H-06)

```
REOPEN_EVIDENCE := {
  schema_version : UINT16 (= 1),
  decision_id    : BYTES[32],     // SHA-256(Tag('IER-consume-v1') ‖ encode_bytes('REOPEN') ‖ encode_bytes(scope_id) ‖ encode(UINT64 decided_at) ‖ encode(BYTES salt16))
  scope_id       : BYTES[32],
  scope_epoch    : UINT64,        // epoch que se cierra por esta evidencia
  opened_epoch   : UINT64,        // epoch que se abre: DEBE ser scope_epoch + 1 (comprobación criptográfica)
  issuer         : BYTES[32],     // identidad W (Schnorr/Ed25519)
  verifier_id    : BYTES[32],     // identidad del verificador independiente (DISTINTO de issuer)
  reason         : {ROLLBACK_RESOLVED, RECONCILE_RESOLVED},
  evidence_hash  : BYTES[32],     // hash del expediente de reconciliación externo
  signature      : BYTES[64],     // firma Ed25519(skew ok) sobre encode(concat(…todos los campos previos excepto signature/ salt…)),
}
Verificación:
  1. schema_version == 1;
  2. opened_epoch == scope_epoch + 1;
  3. decision_id coincide con el hash recomputable (tag CHECK);
  4. firma válida bajo la clave pública de issuer;
  5. verifier_id ≠ issuer; ambos registrados (PKI/BC abierto; verificación contra almacén de identidades del ámbito);
  6. evidence_hash coincide con el `evidence_hash` del expediente de reconciliación del scope (SC-002-RECONCILE) o el scope_event que lo originó;
  7. decision_id aún no consumido (§R2.r2.2.7).
```

Firma: Ed25519 (propuesta; D-R2R2-1). La verificación de `decision_id` es determinista y reproducible por cualquier verificador independiente.

## R2.r2.4.3 `T-REOPEN` — protocolo completo (H-06, H-13)

```
T-REOPEN(scope_id, evidence):
  Precondición: scope_event durable correlativo existe (kind ∈ {ROLLBACK_DETECTED, RECONCILIATION_REQUIRED}).
  Una sola transacción durable:
    1. INSERT consume decision_id en consumed_decision (falla si ya consumido → abort);
    2. row := SELECT * FROM scope WHERE scope_id = :id FOR UPDATE;
    3. si row.si ∉ {ROLLBACK_DETECTED, RECONCILIATION_REQUIRED} ⇒ ROLLBACK de todo (incl. consumed_decision);
    4. verificar evidence (§R2.r2.4.2);
    5. new_epoch := row.scope_epoch + 1;
    6. UPDATE scope SET si='HEALTHY', scope_epoch=new_epoch,
         minimum_valid_fence = GREATEST(row.minimum_valid_fence, (SELECT MAX(fencing_token) FROM attempt WHERE scope_id=:id)) + 1,
         next_fence = GREATEST(row.next_fence, GREATEST(row.minimum_valid_fence, (SELECT MAX(fencing_token) FROM attempt WHERE scope_id=:id)) + 1);
    7. INSERT reopen_evidence (sello; immutable);
    8. COMMIT.

Concurrencia:
  - Dos T-REOPEN concurrentes con el mismo decision_id: exactamente uno gana (paso 1).
  - T-SUSPEND vs T-REOPEN: lock de fila scope; serializan; el segundo ve el estado final del primero.
  - T13 vs T-REOPEN: readiness de precondition falla ⇒ la perdedora aborta sin efectos.
  - Crash pasos 1-7: la tx aborta por completo (no hay decision_id consumido a medias, no hay scope a medias reapertura).
  - Crash post-COMMIT: reapertura confirmada; decision_id ya consumido; no re-reaplica.

Efectos colaterales: operaciones antiguas permanecen SUSPENDED (nunca re-abiertas); trabajo nuevo bajo nuevo epoch = nuevas operaciones.
```

## R2.r2.4.4 `V=CLOSED` — transición formal y completa (H-14)

```
T-CLOSE(scope_id, decision_id):
  Precondición (todas):
    - scope.si ∈ {HEALTHY, ROLLBACK_DETECTED, RECONCILIATION_REQUIRED, HUMAN_CLOSED};
    - ∀ op ∈ scope: op.v ∈ {SUSPENDED} o op.p ∈ {COMMIT_DURABLE, ABORT_DURABLE, RECOVERABLE,
       RESERVE_ORPHAN, FAILED_CONSUMED};
    - NINGÚN efecto ES-007 sin veredicto SC-002; NINGÚN efecto no terminal (ES-001..004 pendientes).
    - decision_id válido y no consumido (consumed_decision);
  Una sola transacción:
    1. INSERT consumed_decision;
    2. row := SELECT scope FOR UPDATE;
    3. validar precondición;
    4. UPDATE operation SET v = 'CLOSED' WHERE scope_id = :id AND v = 'SUSPENDED';
    5. UPDATE scope SET si = 'HUMAN_CLOSED' (si vino de degradación) — fence se incrementa; scope queda absorbido;
    6. COMMIT.
Derivados:
    - CLOSED absorbente e irreversible (V-003): ninguna reapertura ni reemisión de admisión; ningún intento nuevo;
      TRI-STATE cerrado para la operación completa del scope (op.v ∈ CLOSED).
    - T permanece inmutable post-CLOSED (INV-13/14).
    - Efectos en recuperación siguen su máquina (ALL/ANY policies); ninguna testificación nueva.
  Ante fallo: ROLLBACK completo o confirmación completa de T-CLOSE.
```

## R2.r2.4.5 `SI` (SCOPE_INTEGRITY) — máquina completa

| Estado | Evento | Guarda | Postcondición | Autoridad | Ante fallo |
|---|---|---|---|---|---|
| HEALTHY | degradación detectada (detector) | evidencia durable disponible | `ROLLBACK_DETECTED` o `RECONCILIATION_REQUIRED`; scope_event INSERT (misma tx, §R2.r2.2.3); fence+1 | W | abort total |
| ROLLBACK_DETECTED | T-REOPEN confirma | §R2.r2.4.3 | `HEALTHY`; epoch+1 | W+ver | abort total |
| RECONCILIATION_REQUIRED | T-REOPEN confirma | §R2.r2.4.3 | `HEALTHY`; epoch+1 | W+ver | abort total |
| ROLLBACK_DETECTED | T13/T-CLOSE | §R2.r2.4.4 | `HUMAN_CLOSED` | W humano+verificador | abort total |
| RECONCILIATION_REQUIRED | T13/T-CLOSE | §R2.r2.4.4 | `HUMAN_CLOSED` | W humano | abort total |
| HUMAN_CLOSED | — | ABSORBENTE (V-003 análogo): ningún evento reabre | — | — | — |

Absorción de estados: HEALTHY→ROLLBACK_DETECTED→(HEALTHY vía REOPEN | HUMAN_CLOSED vía T-CLOSE); HEALTHY→HUMAN_CLOSED directo sólo por T13 (decisión humana sin degradación previa) — el armado del evento procede igualmente.

## R2.r2.4.6 `TRs` (SCOPE_TRUST) — máquina completa

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| VALID | evidencia adversa | durable | `QUARANTINED`; scope_event registro | W |
| QUARANTINED | resolución | independiente, positiva | `VALID`; scope_event registro | W+verificador |
| NOT_DETERMINED | — | transitorio; siempre resuelve | `VALID` o `QUARANTINED` | W+verificador |
| cualquier | T-REOPEN/T13 | coherencia con SI | absorbe/sextuplica coherencia | W |

## R2.r2.4.7 `ESs` (SCOPE_EVIDENCE) — máquina completa

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| ABSENT | llega evidencia | recepción durable | `RECEIVED` | W |
| RECEIVED | verifica W | muestreo/constatación | `VERIFIED` o `REJECTED` | W |
| VERIFIED | — | comprometedor positivo | persiste | — |
| REJECTED | resolvedor | evidencia final dudosa | persiste; efecto: ningún dispatch nuevo (§R2.r2.3.5 lo bloquea) | W |
| ABSENT/RECEIVED | contradicción | dos evidencias registradas en conflicto | `CONTRADICTION`; scope no despacha; arbitraje externo | W |
| CONTRADICTION | resolución humana | evidencia externa documentada | `VERIFIED` o `REJECTED`; si persiste ⇒ scope cerrado (T13) | W humano |

## R2.r2.4.8 `OD` (OPERATION_DECISION) — máquina completa

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| NOT_EVALUATED | T-ADM admite | `EffectAdmissible` (§R2.r2.3.5) evaluado | `ADMITTED` (histórica) | W |
| NOT_EVALUATED | T-ADM rechaza | guarda no satisfecha | `BLOCKED` | W |
| NOT_EVALUATED | evidencia insuficiente | — | `NOT_DETERMINED` | W |
| ADMITTED | suspensión por scope | T-SUSPEND | permanece `ADMITTED` (histórico; sin fuerza operativa, D-R2A-3) | sistema |
| ADMITTED | abort confirmado | `p=ABORT_DURABLE` | mantiene `ADMITTED` (hecho histórico) | W |
| BLOCKED | — | persiste | persiste | — |
| NOT_DETERMINED | sentencia | evidencia suficiente | `ADMITTED` o `BLOCKED` | W |

OD nunca se usa como guarda por sí solo; su valor operativo vive en `V` + `P` (D-R2A-4).

## R2.r2.4.9 `V` y `O` (OPERATION_VALIDITY, OPERATION_OUTCOME) — máquinas completas

V:

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| OPEN | T-SUSPEND / T13 | §R2.r2.3.2/§R2.r2.4.4 | `SUSPENDED` | sistema |
| SUSPENDED | T-REOPEN | **NUNCA** reabre operaciones antiguas | persiste `SUSPENDED` | sistema |
| SUSPENDED | T-CLOSE | §R2.r2.4.4 | `CLOSED` | humano+verificador |
| OPEN | T-CLOSE | condición de efectos terminales | `CLOSED` | humano+verificador |
| CLOSED | — | ABSORBENTE; ninguna transición | — | — |
| OPEN/SUSPENDED | cierre por agotamiento fencing | `FENCING_EXHAUSTION` event | `CLOSED` (o `SUSPENDED`+T13) | sistema |

O:

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| NONE | efecto committed verificado | duradera | `COMMITTED` | W |
| NONE | efecto abortado verificado | duradera | `NOT_EXECUTED` | W |
| NONE | sin evidencia suficiente | — | `UNKNOWN` | W |
| COMMITTED | reconciliación | independiente | persiste; baja bajo reconciliación nunca unilateral | W+verificador |
| NOT_EXECUTED | reconciliación | independiente | persiste | W+verificador |
| UNKNOWN | veredicto SC-002 | alcance del efecto | `COMMITTED` o `NOT_EXECUTED` (REJECTED→saga→NOT_EXECUTED) o `UNKNOWN` permanente (scope close) | W+verificador |

## R2.r2.4.10 `ES` (EFFECT_DOMAIN) — máquina completa y reconciliación (H-17, H-15)

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| (sin efecto, manifiesto intenta despacho) | T-ADM agotada | efecto VÁLIDO | `ES-001 INTENT_DURABLE` | W |
| ES-001 | sink ejecuta | §R2.r2.3.2 OK | `ES-002 DISPATCHED` | sink |
| ES-002 | ACK recibido | efecto aceptado por externo | `ES-003 ACKNOWLEDGED` | sink/A |
| ES-003 | verificador observa | veredicto medible | `ES-004 OBSERVED` | verificador |
| ES-004 | veredicto concluyente | verificado auténtico | `ES-005 VERIFIED` | verificador |
| ES-004 | compensación aplicada | saga confirmada durable | `ES-006 COMPENSATED` | W/A |
| ES-002..ES-004 | sin evidencia concluyente | — | `ES-007 UNKNOWN` | sink/A |
| ES-007 | veredicto SC-002 | efecto exacto vinculado | `ES-005 VERIFIED` o `ES-006 COMPENSATED` o rechazado (saga) o `ES-007` permanente | verificador |

**ReconciliationProtocol (cerrada, H-17):**
```
ReconciliationProtocol :=
  1. Registro obligatorio SC-002 por cada efecto ES-007, con:
     reconciliation_id (UNIQUE), operation_id, attempt_id, effect_ordinal, effect_binding,
     verdict ∈ {VERIFIED, REJECTED, CONTRADICTION},  // dominio ES; NOT_VERIFIED ∉ ES (H-17 exige dominio cerrado)
     verifier_id≠producer, evidence_hash, decided_at (timestamptz NOT NULL), decision_id UNIQUE.
  2. Unicidad y replay: decision_id UNIQUE; el mismo decision_id reentregado ⇒ rechazo íntegro (consumido_decision).
  3. Orden: decided_at monótono por efecto (consultado MAX(decided_at) al registrar); empate ⇒ rechazo o arbitraje W+verificador.
  4. Doble veredicto para el mismo efecto: ambos registros se conservan;
       ambos VERIFIED ⇒ ambos VERIFIED se admiten (idempotencia de observación, no contradice);
       VERIFIED+REJECTED ⇒ scope.ess := CONTRADICTION (sin dispatch nuevo; arbitraje) (H-17);
       CONTRADICTION en cualquier combinación ⇒ scope.ess := CONTRADICTION.
  5. Post-veredicto:
       VERIFIED → efecto ES-005 terminal;
       REJECTED → efecto NO verificado: prohibido re-intento del mismo effect_binding para esta operación;
                   se compensa (saga) o FAILED_CONSUMED; testificación sólo por camino ABORT/FAILED; nunca COMMITTED;
       CONTRADICTION → scope ess:=CONTRADICTION; arbitraje; ninguna testificación bajo contradicción.
  6. Todo cierre de operación (cierre destino T13/T-CLOSE) con efectos ES-007 o veredictos pendientes queda INVÁLIDO y falla la transición de cierre; cierre post-cosecha exige cero pendientes.
```

## R2.r2.4.11 `T` (HISTORY_RESULT) — máquina completa

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| NONE | COMMIT_DURABLE verificado | durable | `COMMIT_TESTIFIED` | W |
| NONE | ABORT_DURABLE verificado | durable | `ABORT_TESTIFIED` | W |
| COMMIT_TESTIFIED | — | terminal histórica; absorbente | — | — |
| ABORT_TESTIFIED | — | terminal histórica; absorbente | — | — |

Guardas de autorización: `COMMIT_TESTIFIED ⇒ p = COMMIT_DURABLE`; `ABORT_TESTIFIED ⇒ p = ABORT_DURABLE` (INV-09).

## R2.r2.4.12 `ESo` (OPERATION_EVIDENCE) — máquina completa + escape `REJECTED` (H-18)

| Estado | Evento | Guarda | Postcondición | Autoridad |
|---|---|---|---|---|
| ABSENT | sello W solicitado | p∈{CD,AD} | `RECEIVED` | W |
| RECEIVED | W verifica | constatación | `VERIFIED` o `REJECTED` | W |
| VERIFIED | sello emitido | — | `TESTIFICATION_PENDING` | W |
| REJECTED | resolución | decisión externa o corrección durable | `RECEIVED` (con evidencia nueva) o migración: ver escape abajo | W |
| REJECTED | ninguna evidencia llega | voluntariamente REJECTED permanente | persiste `REJECTED`; no leyérese `T` | — |
| TESTIFICATION_PENDING | sello W final | irrefutable | `TESTIFIED` | W |
| TESTIFIED | — | terminal; absorbente | — | — |

**Salida formal desde `ESo=REJECTED` (H-18):**
```
ESo=REJECTED persiste mientras no exista nueva evidencia verificable.
Únicas dos salidas:
  (a) Nueva evidencia verificada positiva por W ⇒ REJECTED → RECEIVED → VERIFIED (nueva cadena; decision_id nuevo; append-only);
  (b) Compensación durable (saga) de TODOS los efectos de la operación y cierre vía ABORT_DURABLE ⇒
      el intento queda FAILED_CONSUMED; ESo permanece REJECTED (no hay testificación posible);
      la operación termina con v=CLOSED vía T-CLOSE exigiendo: ningún efeito UNKNOWN/pendiente;
      compensación durable y auditada; decisión humana explícita (T13).
No existe transición REJECTED → TESTIFIED. No existe transición REJECTED → VERIFIED sin nueva evidencia positiva registrada con decision_id nuevo.
```

## R2.r2.4.13 Cambios de `P` y reconciliación cruzada

| Estado p | Evento | Guarda | Postcondición | Autoridad | Ante fallo |
|---|---|---|---|---|---|
| NOT_STARTED | T-ADM | guarda | `RESERVE_REQUESTED` | W | ninguno |
| RESERVE_REQUESTED | marker persistido | verify A | `RESERVE_DURABLE` | W | ninguno |
| RESERVE_DURABLE | W confirma | coordinado | `RESERVED_CONFIRMED` o `RESERVE_ORPHAN` | W/A | confirmación incompleta ⇒ RESERVE_ORPHAN |
| RESERVED_CONFIRMED | sink ejecuta | §R2.r2.3.2 | `EXECUTING` | sink | crash ⇒ recovery |
| EXECUTING | efecto resuelto | durable | `COMMIT_DURABLE` o `ABORT_DURABLE` o `RECOVERABLE` | sink | crash ⇒ recovery |
| EXECUTING | crash sin efecto durable | post-crash | `RECOVERABLE` | reconciler | — |
| RECOVERABLE | reconciliación concluye | SC-002 completo | `COMMIT_DURABLE` o `ABORT_DURABLE` o `FAILED_CONSUMED` | verificador | silencio prohibido |
| RESERVE_ORPHAN | — | terminal | absorbente | — | — |
| FAILED_CONSUMED | — | terminal | absorbente | — | — |

Crash-based determinism: cualquier crash antes del COMMIT deja la operación en el estado previo (durable); cualquier crash después deja el efecto del evento; jamás estado intermedio visible al sink.

## R2.r2.4.14 Mapa estados ↔ invariantes

Toda invariante de §R2.r2.5.7 referencia una máquina de este apartado; ninguna máquina existe sin al menos una invariante. Revisión cruzada obligatoria antes de aceptar esta revisión.

---

# R2.r2.5 — Barrera normativa, censo y pruebas de aceptación (H-16, H-20, H-21, H-22, H-23, H-26, H-27)

## R2.r2.5.1 Barrera normativa fail-closed con cierre transitivo (H-20, H-27)

```
BND(symbol):
  seed := symbols with canonical_source = IER_GATE_PLAN_S1 (design freeze §1)
  trusted := symbols with canonical_source ∈ {SRC-LOCAL (este documento), SRC-LOCAL/R1, registro R1, registro R1.3}
  for each symbol S used anywhere in scope:
    if S ∉ trusted ∪ registered-by-census ⇒ BLOCKED(S, 'UNCLASSIFIED_TOKEN')
    if any dep D ∈ closure(deps(S)) is BLOCKED ⇒ BLOCKED(S, 'DEPENDS_ON_BLOCKED')   // cierre transitivo
  unknown/missing source_doc ⇒ BLOCKED (default-deny).

closure(deps) := menor conjunto S tal que:
  S ⊇ deps(S0); D∈deps(S) ∧ D∈registered ⇒ S ⊇ deps(D); punto fijo finito (los dominios son finitos).

BLOCKED_SYMBOLS (FG-003, §R2.r2.2.10) es la fuente única del verificador; BND se ejecuta en cada cierre de fase.
```

- **Fail-closed por defecto**: todo elemento no clasificado, no registrado o con origen desconocido queda bloqueado; nada «pasa por ser inocente».
- **Transitividad**: el bloqueo de una dependencia bloquea a todo dependiente; la no clasificación de una dependencia bloquea al símbolo. No existen excepciones por conveniencia.
- Regla de cierre: ninguna fase aguas-abajo consume símbolos bloqueados; A-09 verifica.

## R2.r2.5.2 Censo normativo exhaustivo y verificación bidireccional (H-21)

El censo de §0 lista todas las clases usadas en este documento:

| Clase | Elementos | Regla |
|---|---|---|
| R1 | 49 símbolos | semántica íntegra; cualquier alteración prohibida (R1.4) |
| R1.3 | ES-001…007, FG-001…004, PL-001…003, SC-001…003, EF-001…002 | registrar o prohibir |
| Funciones | EffectAdmissible, DispatchAuthorization, SinkAcceptance, AttemptCurrent, ManifestHash, BindingHash, encode*, ReconciliationProtocol | definición normativa única por función |
| Registros | manifest, scope_event, reopen_evidence, reconciliation_record, consumed_decision, blocked_symbols (SC-001, SC-002, FG-001, FG-003…) | DDL cerrado §R2.r2.2 |
| Tipos | Manifest, EffectDescriptor, EffectMessage | §R2.r2.1 |
| Campos persistentes | scope.*, operation.*, attempt.*, manifest.* | cada columna en ≥1 regla y ≥1 test |
| Tags cripto | IER-*-v1\0 | censo anti-colisión |

Regla de rechazo: **cualquier token normativo no incluido en la tabla de §0 ⇒ R2-A.r2 no puede aceptarse hasta su clasificación o su eliminación.** A-01 verifica en ambas direcciones.

## R2.r2.5.3 INV-13 demostrada formalmente (H-16)

```
INV-09: ∀s: t(s) ∈ {COMMIT_TESTIFIED, ABORT_TESTIFIED} ⇒ p(s) ∈ {COMMIT_DURABLE, ABORT_DURABLE}.
Contrapositiva válida: ∀s: p(s) ∉ {COMMIT_DURABLE, ABORT_DURABLE} ⇒ t(s) ∉ {COMMIT_TESTIFIED, ABORT_TESTIFIED}.
Dominio de t: {NONE, COMMIT_TESTIFIED, ABORT_TESTIFIED} (finito).
Por tanto: p(s) ∉ {COMMIT_DURABLE, ABORT_DURABLE} ⇒ t(s) = NONE.
INV-13 := esa proposición. No es «consecuencia directa de INV-09» por apelación; es su contrapositiva demostrada.
Estado: DERIVED-VALID. No es un axioma independiente; no se mantiene como invariante primaria.
```

## R2.r2.5.4 Cardinalidad justificada (H-22)

```
Dominios (justificación):
  SI = 4 (§R1): estados observables estables del scope; no derivables unos de otros;
  TRs = 3, ESs = 5, OD = 4, V = 3, P = 10, O = 4, T = 3, ESo = 6  (§R1).
  |S_SCOPE|    = 4 · 3 · 5            =   60     (producto exacto)
  |S_OPERATION| = 4 · 3 · 10 · 4 · 3 · 6 = 8640  (producto exacto)
  |S_BASE|      = 60 · 8640           = 518400  (proyección cartesiana, nada más)
Independientes: cada dominio se enumera por separado sobre el mismo ámbito (operación única ligada a manifest, intento cabeza); no hay solapamiento entre dominios.
A alcanzables: |REACHABLE| ≤ |LEGAL| ≤ |S_BASE|; ambos desconocidos; pendientes de enumerador independiente.
D-315 sigue PENDING; este documento no reporta ningún número alcanzable/efectivo.
INV operansobre estados parciales: |LEGAL| < |S_BASE| en al menos un punto (p.ej. INV-04 elimina combinaciones V≠OPEN con efectos; INV-09 elimina t-post-terminal con p no terminal). El número exacto de estados eliminados no está demostrado; exige enumeración.
```

## R2.r2.5.5 Censo reproducible de sinks de efecto (H-23)

```
Procedimiento A-03-v2 (reproducible; se ejecuta cuando la implementación exista):
  1. Estático: análisis de call-graph sobre el módulo de efectos (p.ej. tree-sitter/import-graph);
     todo símbolo de adaptador de efecto externo registrado en una whitelist de sinks.
  2. Whitelist única: SinkExecutor (único autorizado). Ningún otro módulo importa un adaptador de efecto.
  3. Dinámico: A-11 (bypass imposible), A-19 (scan en CI: import fuera de whitelist ⇒ build falla), A-20 (ACL almacén), A-21 (crash bajo fence).
  4. Artefacto de la auditoría: listado de sinks encontrados + hash + resultado A-11/A-19/A-20/A-21; se archiva en evidence/.
  5. Cualquier sink nuevo no registrado ⇒ la auditoría A-03 falla hasta nuevo registro/census.
```

## R2.r2.5.6 Políticas y terminación de operación (H-26)

```
ANY (PL-002):
  Semántica: la operación se considera aceptablemente completa si existe AL MENOS UN efecto en estado terminal satisfactorio (ES-005 VERIFIED), y todos los no-satisfactorios están COMPENSATED o reconciliados a no-éxito (ES-005/ES-007 con veredicto REJECTED registrado).
  Terminación: p alcanza COMMIT_DURABLE SOLO cuando hay evidencia durable del conjunto terminal; testificación posible; sino p queda EXECUTING o ABORT path.
  Cancelación: con ningún efecto despachado ⇒ cancelación del manifiesto y O=NOT_EXECUTED obligatorio; con al menos un efecto despachado ⇒ compensación de todos los despachados (saga) hasta que no quede ningún efecto pendiente o desconocido;
  Recuperación: post-crash ⇒ RECOVERABLE → ReconciliationProtocol.
  Observable: outcome (O) plausible COMMITTED sólo si ≥1 efecto VERIFIED (O=COMMITTED) o ninguno VERIFIED (pero al menos uno COMPENSATED y ninguno UNKNOWN-pendiente) ⇒ igualmente COMMITTED como camino ANY? — NO: ANY requiere al menos uno VERIFIED; sin ninguno ⇒ la operación debe ir a ABORT_DURABLE (no testificación de COMMITTED).
ALL (PL-003):
  Semántica: todos los efectos deben alcanzar VERIFIED.
  Terminación: p llega a COMMIT_DURABLE sólo si TODOS los efectos están VERIFIED (o es camino ABORT_DURABLE completo); cualquier COMPENSATED/REJECTED pendiente de resolución ⇒ la operación NO puede testificar éxito; testificación ABORT_TESTIFIED
  Cancelación: mientras ningún efecto esté dispatchado, cancelación total legal; con cualquier efecto dispatchado, debe aplicarse compensación.
  Observable: O=COMMITTED sólo si todos VERIFIED.
NONE (PL-001):
  Semántica: manifiesto declarativo; efectos prohibidos.
  Terminación: O=NOT_EXECUTED obligatorio; única vía testificación: ABORT_TESTIFIED tras confirmar durablemente ausencia de efecto (es decir, ningún EffectMessage fue aceptado por ningún sink o el efecto nunca se ejecutó).
  Cualquier efecto externo detectado ⇒ scope pasa a CONTRADICTION; nunca testificación COMMITTED.

Conexión con terminación (P):
  PL-002 gate: p→COMMIT_DURABLE sólo si ∃i: effect[i]=VERIFIED ∧ ∀j: effect[j]∈{VERIFIED,COMPENSATED,REJECTED-with-record};
  PL-003 gate: p→COMMIT_DURABLE sólo si ∀i: effect[i]=VERIFIED;
  PL-001 gate: p→ABORT_DURABLE obligatorio; p→COMMIT_DURABLE prohibido.
Estas puertas pertenecen a la máquina P y se integran al R3 solo con revisión independiente.
```

## R2.r2.5.7 Registro único de invariantes (ACTUALIZADO R2-A.r2: INV-17…19 añadidas; INV-13 reclasificada derivada)

| ID | Predicado (cerrado) |
|---|---|
| INV-01 | ∀ op: `op.scope_id` existe en `scope` (FK `operation.scope_id → scope.scope_id`) |
| INV-02 | ∀ op despachable: `op.scope_epoch == scope.scope_epoch` (vigente). Fija de creación immut. |
| INV-03 | ∀ op: `v(op) = CLOSED ⇒` ninguna transición posterior despacha efecto |
| INV-04 | ∀ op: `v(op) ∈ {SUSPENDED, CLOSED} ⇒ EffectAdmissible(op)=FALSE` |
| INV-05 | ∀ e ∈ ES-007(UNKNOWN): ninguna repetición ni compensación hasta SC-002 registrado |
| INV-07a/b/c | ESO↔T cerradas (§R2.r2.4.12) |
| INV-08 | ∀ attempt: unicidad `(scope_id, operation_id, attempt_id)` y `(operation_id, attempt_generation)` y `(operation_id, claim_generation)` |
| INV-09 | ∀ op: `t ∈ {CT, AT} ⇒ p ∈ {COMMIT_DURABLE, ABORT_DURABLE}` |
| INV-10 | `p=CD ⇒ o∈{COMMITTED,UNKNOWN}` · `p=AD ⇒ o∈{NOT_EXECUTED,UNKNOWN}` |
| INV-11 | ∀ scope: `si=HUMAN_CLOSED ⇒` ningún despacho nuevo |
| INV-12 | ∀ e despachable: `effect_binding` y `binding_hash` verificados in situ (§R2.r2.3) |
| INV-13 | ∀ op: `p∉{CD, AD} ⇒ t = NONE` (contrapositiva demostrada de INV-09, §R2.r2.5.3) |
| INV-14 | `t=CT ⇒ o=COMMITTED` · `t=AT ⇒ o=NOT_EXECUTED` |
| INV-15 | tras REOPEN: ops del epoch anterior tienen `v=SUSPENDED` permanente y nunca despachan |
| INV-16 | `si=HUMAN_CLOSED ⇒ ∀ op∈scope: v≠OPEN` |
| INV-17 | ∀ op: el head `(current_attempt_id, current_attempt_generation)` apunta a una fila `attempt` con `scope_id`+`operation_id` coincidentes y generación igual (`current_attempt_generation`) |
| INV-18 | ∀ op PL-002: `p→COMMIT_DURABLE` sólo si ∃i VERIFIED ∧ ∀j terminal satisfactorio; ∀ op PL-003: sólo si todos VERIFIED; ∀ op PL-001: `p→ABORT_DURABLE` obligatorio |
| INV-19 | ∀ op y scope: CLOSED (op) / HUMAN_CLOSED (scope) son absorbentes; ninguna transición los revierte |

## R2.r2.5.8 Pruebas ampliadas (A-serie; cuando la ejecución sea autorizada)

| # | Criterio (evidencia mínima) |
|---|---|
| A-01 | Censo bidireccional §0 ≡ artefacto; rechazo de desconocidos |
| A-02 | Reconstrucción SCOPE↔OPERATION por scope_id en cualquier estado; head-pointer vs attempt consistente (INV-17) |
| A-03 / A-03-v2 | Censo de sinks §R2.r2.5.5 + prevalidación origen / revalidación sink (A3.3) |
| A-03-neg-1..9 | Cada cláusula de EffectAdmissible falseada ⇒ FALSE (9 negativos + POSITIVO) |
| A-04 | T-REOPEN rechaza evidencia inválida, epoch reciclado, decision_id consumido, si incorrecto |
| A-05 | Vectores §R2.r2.1.6 reproducibles; positivo/negativo hash |
| A-06 | Enumerador LegalState (INV-01…19) con hash cerrado |
| A-07 | UNKNOWN ⇒ sin repetición; doble veredicto ⇒ CONTRADICTION |
| A-08 | HUMAN_CLOSED: cero dispatch post-cierre; ops no OPEN (INV-16) |
| A-09 | BND closure: consumidor de BLOCKED ⇒ fase falla cerrada |
| A-10 | LEGAL/REACHABLE reportados aparte de S_BASE |
| A-11 | Bypass imposible; integración demuestra |
| A-12 | Crash sink entre validación y efecto ⇒ efecto no producido (sink lock §R2.r2.3.2) |
| A-13 | Reapertura concurrente con misma evidencia ⇒ UNA transición gana |
| A-14 | T-CLOSE atomicidad bajo crash forzado |
| A-15 | Sink vs suspensión: HP-1…HP-6; ambos órdenes producen el resultado exigido |
| A-16 | Política NONE: rechazo permanente de cualquier despacho |
| A-17 | ANY: éxito con ≥1 VERIFIED y 0 UNKNOWN pendientes; ALL: falla ante no-VERIFIED |
| A-18 | Tras REOPEN, op antigua rechazada (INV-02/INV-15); nueva op sí puede ejecutar (nuevo intento cabeza) |
| A-19 | static scan: import de adaptadores de efecto fuera de sink ⇒ build falla |
| A-20 | ACL almacén: sólo sink puede escribir entidades de despacho |
| A-21 | Sink mantiene lock durante ejecución; T-SUSPEND espera; nunca efecto post-suspensión |
| A-22 | Reapertura con firma válida de W pero verifier_id==issuer ⇒ rechazo |
| A-23 | Reconciliación con decision_id replay ⇒ rechazo independientemente de veredicto |
| A-24 | REOPEN_EVIDENCE con opened_epoch ≠ scope_epoch+1 ⇒ rechazo |
| A-25 | Mensaje con fencing_token = minimum_valid_fence−1 ⇒ rechazo permanente |
| A-26 | Enumeración completa ejecución INV-01…19 (incluye INV-18) con hash de salida cerrado |
| A-27 | Política ANY con 0 VERIFIED y todos COMPENSATED ⇒ operación no testable COMMITTED |

---

# R2.r2.6 — Matriz tripartita de trazabilidad (H-01…H-27 × R2A-AUD-001…019 × notas residuales)

Leyenda de estado: **ATENDIDO-DOCUMENTAL** = reparado en esta revisión; **BLOCKED** = incompatibilidad no resoluble por diseño (ver §7); **NOT_APPLICABLE** = no aplica con justificación explícita. Ningún estado implica cierre; la aceptación es del propietario.

## 6.1 Matriz H-01…H-27 (columnas exigidas por el diseñador)

| H | Defecto | Causa (v2 por qué falla) | Definición (reparación) | Persistencia | Transición afectada | Invariante | Contraejemplo que v2 permitía y r2 impide | Prueba | Estado |
|---|---|---|---|---|---|---|---|---|---|
| H-01 | Hash sin algoritmo, versionado, tags ni vectores | v2 concatenaba `H(tag)` con campos; omisiones fatales | SHA-256; tags NUL-terminados; encoder tabular; layout fijo; vectores §R2.r2.1.6 publicables | `manifest`, `scope_event`, `blocking_list` tablas con `manifest_hash` único | creación de intento/manifiesto; `T-SUSPEND`/`T-REOPEN` preimages | ninguna nueva; tag pinning CHECK | es concatenar admite corte ambiguo: `A‖BC` vs `AB‖C` resolvían igual; r2 lo rechaza por construcción | A-05; A-26; censo tags | ATENDIDO-DOCUMENTAL |
| H-02 | `effect_ordinal` sin semántica global | encoder lo permitía local-por-tipo; identidad no demostrable | ordinal global denso 0..n-1; orden de encode = ordinal; `(op,ordinal)` identidad | `manifest.effects_canon` bytea sellado | escritura/lectura manifiesto | INV-12 (binding por efecto) | con ordinales locales múltiples 0s: permutación de efectos colapsaba identidad; r2 exige unicidad y orden | A-05; A-26 | ATENDIDO-DOCUMENTAL |
| H-09 | `BindingHash` incoherente entre operación e intento | `operation.binding_hash` duplicado; reintento rompía unicidad | binding es por **intento**; `operation.binding_hash` eliminada; cabeza componencial | `attempt.binding_hash` NOT NULL; `current_attempt_*` pointer | creación de intento; sink revalidación | INV-17 | reintento con operación igual, envelope con binding antiguo: v2 aceptaba si head no cambió la columna; r2 verifica contra fila cabeza viva | A-02; A-18; A-03 | ATENDIDO-DOCUMENTAL |
| H-10 | Idempotencia entre epochs incoherente | regla textual omitía epoch en la clave de idempotencia | clave idempotencia `(scope_id, scope_epoch, operation_kind, request_id)` única en almacén y regla | índice único `operation_scope_epoch_kind_request` | creación operación/cada re-try | INV-02/15 | REOPEN + mismo request: v2 producía segunda op sin aviso; r2 la permite (epoch distinto) pero NUNCA bajo el mismo epoch — comportamiento definido y testeado | A-18; A-26 | ATENDIDO-DOCUMENTAL |
| H-11 | `fencing_token` sin protocolo | sólo declaración de monotonía | autoridad W co-locada; asignación atómica con `scope.next_fence`; UNIQUE por `(scope_id, fencing_token)`; overflow → FENCING_EXHAUSTION | columna `scope.next_fence`; `attempt.fencing_token` UNIQUE | claim de intento; sink | INV-12/17 | sink acepta mensaje con fence antiguo tras suspender con `fence+1` CONCURRENTE: v2 sin asignación atómica lo permitía; r2 vincula asignación a claim tx+lock SKIP | A-12; A-15; A-25 | ATENDIDO-DOCUMENTAL |
| H-03 | Manifest sin persistencia durable | sink necesitaba releer manifiesto inexistente | tablas `manifest`, `scope_event`, `reopen_evidence`, `reconciliation_record`, `blocked_symbols`, `consumed_decision`; append-only; FK y CHECK | §2 completo | todas las transiciones de manifest/cierre/evidencia | INV-01..12, 18 | sink intenta verificar manifiesto falsificado por ausencia de almacenamiento: v2 carecía de fuente de verdad; r2 recomputa y confronta | A-02; A-05; A-21 | ATENDIDO-DOCUMENTAL |
| H-04 | Head pointer sin CAS | último-escritor-ganaba; sin predicado de éxito | `SET_HEAD_ATTEMPT` CAS con `WHERE current_attempt_generation=expected`; abort=0 filas | misma tx de inserción de intento | claim de intento | INV-17 | dos claim concurrentes misma operación: v2 tomaba cualquiera; r2 exactamente uno gana, el otro aborta sin efecto | A-02; A-15 | ATENDIDO-DOCUMENTAL |
| H-07 | `RECONCILE_REQUIRED` typo; `scope_event` sin esquema ni relación tx | inconsistencia de dominio con R1 (`RECONCILIATION_REQUIRED`) | token canónico `RECONCILIATION_REQUIRED`; esquema `scope_event` cerrado; evento y transición confirman en UNA tx | `scope_event` (§R2.r2.2.3) | T-SUSPEND | INV-15 | evento huérfano sin suspensión correspondiente: v2 admitía; r2 escribe ambos en la misma tx | A-12; A-15 | ATENDIDO-DOCUMENTAL |
| H-08 | FK compuesta ausente | `attempt.scope_id` sin referencia útil; head sin FK | `Foreign key (scope_id, operation_id) REFERENCES operation(scope_id, operation_id)`; `UNIQUE(scope_id, operation_id)`; `scope_id→scope` en operation | índices y FKs cerrados §R2.r2.2 | claim/re-lectura sink | INV-01; INV-17 | intento con scope ajeno operación: v2 lo admitía; r2 lo rechaza por RESTRICT | A-02 | ATENDIDO-DOCUMENTAL |
| H-12 | `decision_id` sin consumo atómico | T13 se apoyaba en UNIQUE no declarado | tabla `consumed_decision` (PK consumed_by); pasos 1-7 de T-SUSPEND/REOPEN/T-CLOSE la incluyen; doble consumo ⇒ abort total | DDL §R2.r2.2.7 | T-SUSPEND/REOPEN/T-CLOSE | INV-19 | doble reapertura concurrente con mismo evidence: v2 la admitía; r2 una gana y la otra aborta sin side effects | A-13; A-24 | ATENDIDO-DOCUMENTAL |
| H-19 | Divergencia de tipos de generación (UINT8 vs smallint; UINT8 vs bigint) | artefacto R2.3 habla UINT8; v2 SQL smallint/bigint sin decisión | canon alinea a `smallint CHECK BETWEEN 1 AND 255` para generation (≡UINT8); `claim_generation` ≡ **UINT64** `bigint CHECK <2^64`; artefacto §R2.3 permanece REPAIR_REQUIRED (no tocado); divergencia declarada | DDL + regla formal | claim de intento | INV-08 | 255 vs 255 interpretación con cast ambiguo al epoch siguiente: v2 admitía truncamiento; r2 define rango exacto | A-02 | ATENDIDO-DOCUMENTAL |
| H-05 | Fencing no linealizable frente a suspensión concurrente | lectura consistente insuficiente | exclusión mutua sink↔T-SUSPEND sobre fila scope (FOR UPDATE); ejecución de efecto dentro de esa ventana | `scope` row lock; sink tx | T-SUSPEND; sink decision | INV-04; INV-11; INV-16 | escenario HP-2/HP-5 del diseñador: v2 permitía efecto post-suspensión; r2 lo impide por lock o fence | A-12; A-15; A-21 | ATENDIDO-DOCUMENTAL |
| H-20 | Barrera A6 permisiva por defecto | `ELSE ALLOWED(symbol)` | default-deny: origen desconocido ⇒ BLOCKED; closed deps evaluadas también | `blocked_symbols` | todas las fases aguas | INV-19; censo A-01 | símbolo «inocente» sin clasificar colando una dependencia de §1: v2 lo admitía; r2 lo bloquea | A-09 | ATENDIDO-DOCUMENTAL |
| H-24 | Frontera de confianza y bypass no definidos | A-11 asumía sin firmar/modelo | TCB explícito (W, sink, almacén); credenciales Ed25519 propuestas; interfaces enumeradas; prohibidos caminos alternativos; verificación A-19/A-20/A-11 | credenciales fuera del modelo; almacén ACL | todas las que ejecutan efecto | — | «llamar al adaptador directamente no pasa por el sink»: v2 no lo prohibió como regla; r2 lo prohíbe como regla y test falla | A-11; A-19; A-20 | ATENDIDO-DOCUMENTAL |
| H-25 | Orden suspensión vs LP indefinido | A-15 no distinguía solicitud vs LP | casos HP-1..HP-6 con orden de lock explícito y resultados exigidos | `scope` row lock | sink vs T-SUSPEND | INV-12; INV-15 | sink decide válidamente en instante t y ejecuta después de suspensión ya confirmada: v2 lo permitía; r2 lo rechaza (HP-2) | A-15; A-21 | ATENDIDO-DOCUMENTAL |
| H-06 | `REOPEN_EVIDENCE` sin esquema cerrado | v2 lo referenciaba sin definición normativa | esquema completo §R2.r2.4.2 + firma Ed25519 sobre encoding cerrado; verificación determinista | `reopen_evidence` tabla append-only | T-REOPEN | INV-15 | evidencia con opened_epoch ≠+1, assinatura no migrable: v2 no tenía con qué rechazar; r2 rechaza | A-04; A-22; A-24 | ATENDIDO-DOCUMENTAL |
| H-13 | T-REOPEN incompleto | crash mid-tx tolerado raso | algoritmo completo: consumed_decision→row lock→validaciones→epoch+1→fence→reopen_evidence→COMMIT | `reopen_evidence`, `consumed_decision`, `scope` | T-REOPEN | INV-15; INV-19 | crash entre bump de epoch y registro: v2 no lo ató; r2 rollbackea completo o confirma completo | A-04; A-13; A-24 | ATENDIDO-DOCUMENTAL |
| H-14 | `V=CLOSED` sin transición formal | absorbente sin ruta normativa | `T-CLOSE` completa: precondición terminal+sin pendientes; una tx con consumed_decision; absorción INV-19 | `consumed_decision` | T-CLOSE | INV-03; INV-16; INV-19 | operaciones en SUSPENDED eternamente con efectos terminados: v2 sin camino formal; r2 T-CLOSE lo satisface | A-14 | ATENDIDO-DOCUMENTAL |
| H-15 | Máquinas sin transiciones completas | invariantes ≠ máquinas | tablas completas SI/TRs/ESs/OD/P/V/O/T/ESo/ES con precondición, postcondición, persistencia, autoridad, fallo | máquinas §R2.r2.4.5…13 | todas | INV-01..19 | crash intermedio en RECOVERABLE sin ruta: v2 no determinaba; r2 fuerza SC-002 o FAILED_CONSUMED | A-06; A-07; A-17 | ATENDIDO-DOCUMENTAL |
| H-17 | Reconciliación incompleta y dominio ES ilegal | `NOT_VERIFIED` ∉ ES; sin replay protection | dominio VERIFIED/REJECTED/CONTRADICTION; SC-002 con decision_id UNIQUE; orden total por decided_at | `reconciliation_record` | ReconciliationProtocol | INV-05; INV-07a/b/c; INV-12 | doble veredicto sin contradicción detectada: v2 lo admitía silenciosamente; r2 exige scope CONTRADICTION | A-07; A-23 | ATENDIDO-DOCUMENTAL |
| H-18 | `ESo=REJECTED` sin terminal | camino muerto | salidas formales: (a) nueva evidencia verificada positiva; (b) compensación durable + T13; nunca REJECTED→TESTIFIED | `reconciliation_record` | ESo machine | INV-07a/b/c; INV-14 | REJECTED se quedaría sin camino; v2 lo permitía oscilar; r2 lo cierra | A-07; A-17 | ATENDIDO-DOCUMENTAL |
| H-16 | INV-13 sin derivación demostrada | apelación a «consecuencia directa» | INV-13 := contrapositiva de INV-09 probada (dominio finito) | ninguna | invariantes | INV-13 | claim derivación implícita: puerto para un fallo lógico; r2 evidentemente por contraposición | A-06 | ATENDIDO-DOCUMENTAL |
| H-21 | Censo incompleto | tabla de censo no exhaustiva ni con regla de rechazo | §R2.r2.5.2: census bidireccional exhaustivo + regla de rechazo | tabla §0 | todas las fases | INV-01..19; A-01 | token «inocente» sin clasificación: v2 podría aceptar documento inconsistente; r2 exige A-01 ambas direcciones | A-01 | ATENDIDO-DOCUMENTAL |
| H-22 | Cardinalidad sin fundamentación | aritmética sin justificación de dominios | 60/8640/518400 exactos con derivación por R1; LEGAL/REACHABLE desconocidos; PENDING | none new | D-315 | ninguna de estados legales | 518400 presentado como alcanzable: v2 lo admite como cota no legal; r2 lo declara cartesiano, no legal | A-06; A-10; A-26 | ATENDIDO-DOCUMENTAL |
| H-23 | A-03 no demuestra censo de sinks | «proof by construction» insuficiente | procedimiento A-03-v2 (§R2.r2.5.5): estático whitelist + dinámico A-11/A-19/A-20 + artefacto de evidencia | sink ACL | A-03 fases | INV-24? (no nuevo ID) — ref INV-12/19 | sink clandestino no detectado: v2 no admitía test que lo detecte; r2 lo exige | A-03-v2; A-19..A-21 | ATENDIDO-DOCUMENTAL |
| H-26 | Políticas ANY/ALL sin conexión con terminación | semántica sin puerta de transición | PL-002/003 gates a P→COMMIT_DURABLE; PL-001 obligatorio ABORT; terminación vía testificación | `manifest.policy` (CHECK 0,1,2) | máquina P | INV-18 | operación ALL con un efecto COMPENSATED testificada como COMMITTED: v2 no lo prohibía por máquina; r2 lo prohíbe en INV-18 | A-17; A-27 | ATENDIDO-DOCUMENTAL |
| H-27 | A6 no propaga bloqueos transitivamente | BND bloqueaba sólo el símbolo directo | cierre transitivo finito; unknown/defective dep ⇒ dependiente BLOCKED; registrado ⇒ cerrado | `blocked_symbols` | todas | INV-01..19; A-09 | símbolo permitido pese a depender de un token §1: v2 no garantizaba cierre | A-09 | ATENDIDO-DOCUMENTAL |

## 6.2 Correspondencia H-01…H-27 ↔ R2A-AUD-001…019 ↔ notas residuales

Solapamientos (misma raíz, distinta etiqueta):
- H-03 ⊃ AUD-008 (persistence DDL) + residual 2.
- H-06 ≈ AUD-007 (reopen evidence/protocol).
- H-13 ≈ AUD-007 ampliado.
- H-05 ≈ AUD-011/012 (fencing vs suspension; origen vs sink).
- H-25 ≈ AUD-011 ampliado.
- H-09 ≈ AUD-002 (binding único pero por intento).
- H-01 ≈ AUD-002/005 (encoding).
- H-12 ≈ AUD-013 (T13/atomicidad extendida a decision consumption).
- H-19 ≈ AUD-017 (attempt identity types/persistencia).
- H-04 ≈ AUD-017 (head) — reforzado como CAS.
- H-16 ≈ AUD-003/004 (invariantes INV-13/09/06/07 derivadas).
- H-15 ≈ AUD-019 (máquinas faltantes obligatorias).
- H-02 ≈ AUD-018 (política descriptiva incompleta, solapada).
- H-18 ≈ residual 6 (ESo=REJECTED).
- H-17 ≈ AUD-014 (reconciliación).
- H-07 ≈ residual 4 + AUD-007 (sync `RECONCILE_REQUIRED` typo / scope_event relation).
- H-08 ≈ residual 5.
- H-10 ≈ AUD-010/016 (epoch/idempotencia + §A2 índice compuesto).
- H-11 ≈ AUD-017 (autoridad/protocolo completo).
- H-14 ≈ AUD-013 (T13 no alcanza absorción).
- H-20 ≈ AUD-011 (barrera default-permit).
- H-23 ≈ AUD-012 (sink autoritativo / census del sink completo).
- H-26 ≈ AUD-018.
- H-21 ≈ AUD-015.
- H-24 ≈ AUD-012 (frontera de confianza).
- H-27 ≈ AUD-011 (barrera default-permit).
- H-22 ≈ AUD-005, AUD-019 (cardinalidad/legalidad).

AUD y residuales sin correspondencia directa: ninguna; todos mapean a H-* o a obligaciones A-/INV- completas. Los 19 AUD y las 9 notas residuales mapean a H-* o a obligaciones A-/INV- completas.

## 6.3 Prueba de completitud del censo

Cada celda de la matriz menciona como mínimo un identificador normativo (`§R2.r2.x.y`, `INV-xx`, `A-xx`, tabla o DDL específico) verificado al momento de entrega. Cualquier celda vacía debe rellenarse antes de aceptar esta revisión.


---

# R2.r2.7 — Registro aditivo R1.3 (completo; diez campos por entrada)

Reglas: aditivo; ninguna semántica R1 se altera; todas las entradas `DECLARED`; `canonical_source` definitivo al cierre de R1.3 como documento propio (hoy: `LOCAL-DESIGN / R2-REPAIR-SPEC`, sin artefacto sellado); §1 intacta; toda dependencia §1 permanece `BLOCKED` (§R2.r2.5.1).

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| ES-001 | INTENT_DURABLE | enumeración | ES | OPERATION | voluntad de efecto durablemente registrada; no despachado | admisión confirmada → ES-002 | ES-002 | LOCAL-DESIGN | DECLARED |
| ES-002 | DISPATCHED | enumeración | ES | OPERATION | efecto despachado; espera confirmación | espera ACK | ES-001 | LOCAL-DESIGN | DECLARED |
| ES-003 | ACKNOWLEDGED | enumeración | ES | OPERATION | ACK recibido; outcome no verificable | espera verificación | ES-002 | LOCAL-DESIGN | DECLARED |
| ES-004 | OBSERVED | enumeración | ES | OPERATION | verificador ha observado el efecto | espera veredicto | ES-003 | LOCAL-DESIGN | DECLARED |
| ES-005 | VERIFIED | enumeración | ES | OPERATION | efecto verificado externamente | terminal | ES-004 | LOCAL-DESIGN | DECLARED |
| ES-006 | COMPENSATED | enumeración | ES | OPERATION | efecto compensado vía saga | terminal dentro de ámbito saga | ES-004 | LOCAL-DESIGN | DECLARED |
| ES-007 | UNKNOWN | enumeración | ES | OPERATION | outcome indeterminado; reconciliación obligatoria | espera SC-002 | ES-002 | LOCAL-DESIGN | DECLARED |
| FG-001 | REOPEN_EVIDENCE | registro | FG | SCOPE | evidencia de reapertura verificada por W + verificador independiente | §R2.r2.4.2/3 | SC-001, FG-004 | LOCAL-DESIGN | DECLARED |
| FG-002 | minimum_valid_fence | contador | FG | SCOPE | fence piso monotónico; incremento en suspensión/cierre/reapertura | §R2.r2.2.2 | — | LOCAL-DESIGN | DECLARED |
| FG-003 | BLOCKED_SYMBOLS | registro | FG | GOVERNANCE | registro append-only de símbolos bloqueados (default-deny) | §R2.r2.5.1 | — | LOCAL-DESIGN | DECLARED |
| FG-004 | consumed_decision | registro | FG | GOVERNANCE | consume único y atómico de decision_id (T-SUSPEND/T-REOPEN/T13/T-CLOSE) | §R2.r2.2.7 | FG-003 | LOCAL-DESIGN | DECLARED |
| PL-001 | NONE | enumeración | PL | OPERATION | manifiesto declarativo; efectos prohibidos | gate P→ABORT_DURABLE obligatorio | — | LOCAL-DESIGN | DECLARED |
| PL-002 | ANY | enumeración | PL | OPERATION | éxito con ≥1 VERIFIED y 0 UNKNOWN pendientes | §R2.r2.5.6 | ES-005 | LOCAL-DESIGN | DECLARED |
| PL-003 | ALL | enumeración | PL | OPERATION | éxito exige todos VERIFIED | §R2.r2.5.6 | ES-005 | LOCAL-DESIGN | DECLARED |
| SC-001 | scope_event | registro | SC | SCOPE | evento durable de degradación/cierre; única fuente normativa de suspensión | §R2.r2.2.3 | FG-003 | LOCAL-DESIGN | DECLARED |
| SC-002 | reconciliation_record | registro | SC | OPERATION | veredicto vinculado a (operation, attempt, effect, binding) | §R2.r2.4.10 | ES-007, FG-004 | LOCAL-DESIGN | DECLARED |
| SC-003 | manifest | registro | SC | OPERATION | manifiesto inmutable sellado (effects_canon + hash) | §R2.r2.1.2/§R2.r2.2.8 | FG-002 | LOCAL-DESIGN | DECLARED |
| EF-001 | EffectDescriptor | tipo normativo | EF | MANIFEST | {effect_kind, effect_ordinal, effect_binding} en ManifestHash | §R2.r2.1.3 | — | LOCAL-DESIGN | DECLARED |
| EF-002 | EffectMessage | tipo normativo | EF | OPERATION | sobre origen→sink con binding_hash + fencing_token | §R2.r2.3.1 | EF-001, FG-002 | LOCAL-DESIGN | DECLARED |

Censo: este documento no usa ningún token normativo fuera de R1, R1.3 y las funciones/registros clasificados en §0 y §R2.r2.1–§R2.r2.7. A-01 lo comprueba en ambas direcciones.


# R2.r2.8 — Estado, incompatibilidades y decisiones pendientes

## 8.1 Incompatibilidades no resolubles por diseño (documentadas, no eludidas)

1. **Contradicción §1 (FROZEN)**: «`COMMIT_DURABLE ⇒ T=NONE`» frente a la máquina T. No se resuelve, no se interpreta, no se simplifica. Marcada `CANONICAL_DEPENDENCY_BLOCKED` (FG-003); toda dependencia normativa de este bloque permanece bloqueada hasta que §1 reciba un dictamen documental expreso del propietario (§1 no se modifica por esta entrega ni ninguna entrega de esta línea).
2. **Verifier independence**: ninguna reconciliación de este modelo puede darse por veraz por auto-verificación. Toda reclamación de conclusión de `UNKNOWN` requiere un verificador independiente ajeno al productor; este documento define el *protocolo*, no fabrica independencia. Terceros: `NOT_EXECUTED`.
3. **B-03 / B-04 / B-08 (`OPEN`)**: todo lo que dependa de la identidad y autoridad de W/A/V está parametrizado, no implementado. Si B-04 decide una representación de fencing incompatible, §R2.r2.3/§3 deben adaptarse sin alterar las invariantes (la dependencia se anota aquí como bloqueante estructural, no como detalle).
4. **Saga choreography**: este documento declara el punto de contacto (ES-006 COMPENSATED bajo compensación durable), no la coreografía externa; fuera de alcance hasta un dictamen explícito.

## 8.2 Decisiones pendientes para el propietario

| # | Decisión | Propuesta |
|---|---|---|
| D-R2R2-1 | Esquema y PKI de firmas (issuer/verifier) | Ed25519 con almacén de identidades independiente del productor |
| D-R2R2-2 | Autoridad de `fencing_token` | W co-locado con almacén del scope, vía `scope.next_fence` (§R2.r2.3); alternativa: secuencia de base de datos bajo contrato B-04 |
| D-R2R2-3 | `T-CLOSE` sobre scope sano legítimo (no degradado) | Permitido sólo con decisión humana durable; suspende masivamente y cierra absorbido; requiere cero efectos pendientes |
| D-R2R2-4 | `claim_generation` canónico | UINT64 (`bigint CHECK < 2^64`); `B07_FORMAL_MODEL.md §R2.3` permanece REPAIR_REQUIRED; la alineación del artefacto exige autorización posterior |
| D-R2R2-5 | Tag de dominio para `decision_id` | `'IER-consume-v1\0'` |
| D-R2R2-6 | Cadena de herramientas para A-19 (static scan de sinks) | árbol sintáctico (tree-sitter u equivalente); se decide al abrir R3 |

## 8.3 Fuera de alcance declarado (no se toca en esta entrega)

- `B07_FORMAL_MODEL.md` (R1/R2) — sin modificaciones; su sincronización con este contrato exigirá la autorización separada ya comprometida en su revisión.
- `IER_GATE_PLAN.md` (§1) — congelada; intacta.
- Cualquier archivo protegido, DB, fixtures, pruebas ejecutables, publicación o commit.
- `R3`, `OP-NEXT-1`, `D-315`, crash injection, A/B, promoción.

## 8.4 Estado final tras esta entrega

- `R2 = REPAIR_REQUIRED`. Esta especificación **no** lo repara.
- H-01…H-27: **ATENDIDOS documentalmente**; ninguno CERRADO.
- R2A-AUD-001…019: correspondencia establecida (§R2.r2.6 §6.2); ninguno CERRADO.
- `R3 = BLOCKED` · `D-315 = PENDING` · `IMPLEMENTATION_READY = NO` · `PROMOTION = NOT_READY` · `MODEL_VERIFIED = NO`
- En ningún punto de este documento se declara evidencia ejecutable de ningún protocolo, ningún test ejecutado, ninguna validación externa.

## 8.5 Procedencia

- Baseline auditado: `d0fb27962832317b5ea0a2bbca68259401e3ffba682c454596c1a9d8b161536f` (R2-A.r1).
- Hashes del artefacto antes/después: ver registro de revisión.
- Los vectores de prueba de §R2.r2.1.6 fueron calculados aplicando el contrato con `hashlib.sha256` dentro de esta sesión (cálculo documental; ninguna implementación del sistema se ejecutó).
- ` state/multiproject/log.md` registra esta revisión al cerrar el archivo.
- Ningún tercero revisó este documento. Ninguna auto-revisión lo certifica.

Fin R2-REPAIR_SPEC v2.r2 · No modifica §1 · No modifica `B07_FORMAL_MODEL.md` · DRAFT / NOT_ACCEPTED · Procedencia en `state/multiproject/log.md`.
