# B-07 — FORMAL MODEL (DESIGN, NOT EXECUTED) — Repair of R1 only: v1.22-R1.1

Estado global: **SPECIFICATION_ONLY · NOT_EXECUTED · DESIGN_UNVERIFIED · OPEN**.
Autoridad de diseño: `IER_GATE_DESIGN_AUTHORITY` · Diseño: `ChatGPT` ·
Ejecutor: `IA ejecutora autorizada` · `TARGET = docs/ier/B07_FORMAL_MODEL.md` · `VERSION = v1.22-R1.1` · `BASE = v1.22`.
§1 de `IER_GATE_PLAN.md` permanece **congelada**. No se reinterpreta ni se usa como fuente de corrección. Sus valores declarados (`2784`, etc.) continúan etiquetados **CANONICAL_DEPENDENCY_BLOCKED** cuando sea necesario.

Etiquetas y estados de `verification_status` declarados formalmente:

```
DECLARED              = declarado documentalmente; sin evidencia adicional. No implica independencia, corrección ni alcanzabilidad.
PARTIALLY_SUPPORTED   = respaldado parcialmente por evidencia interna listada con referencias concretas.
VERIFIED              = verificado mediante evidencia reproducible con referencia explícita (nunca usado aquí sin garantía).
BLOCKED               = bloqueado por dependencia normativa pendiente (siempre a CAN-xxx o a §1 congelada cuando aplica).
```

`DECLARED` nunca es prueba de corrección. `IsVerificado` requiere, como mínimo, un revisor independiente o un experimento replicable, ninguno de los dos habilitado ahora.

Numerales históricos previos (2340/1058/1282/2448/960/1488/138240/20/30/2880/304/9612) son **VOID**; no se citan ni se presentan como correctos ni como verificados.

`MODEL_VERIFIED: NO` · `INDEPENDENT_REPRODUCED: NO` · `IMPLEMENTATION_READY: NO` · `A/B: NO` · `CRASH_INJECTION: NO` · `OP-NEXT-1: NO` · `THIRD_PARTY_REVIEW: REQUIRED` · `PROMOTION: NOT_READY`.

---

## R1 — CANONICAL SYMBOL REGISTRY (reparado; contrato completo)

Reglas aplicadas por construcción:

1. Cada símbolo tiene exactamente los diez campos: `symbol_id`, `canonical_name`, `symbol_kind`, `domain`, `owner_entity`, `definition`, `lifecycle`, `dependencies`, `canonical_source`, `verification_status`.
2. `symbol_id` único dentro del registro completo; `canonical_name` único dentro del mismo `domain`.
3. Ninguna referencia externa apunta a un ID inexistente; ver §R1.TEST-4 y §R1.TEST-5.
4. Todo cambio de semántica requiere entrada R1 nueva; no se edita ni se anula un símbolo para ocultar conflictos.
5. Ningún símbolo se crea para ocultar una contradicción. Los conflictos con §1 ⇒ `CANONICAL_DEPENDENCY_BLOCKED` explícito.
6. Notación de referencias: ID plano (`SI-002`); ninguna abreviación, rango, slash ni grupo en posición normativa.
7. El owner_entity es el productor semánticamente principal, no el lugar de escritura física.
8. `lifecycle` indica creación, transición(es), y estado terminal o absorbente cuando aplica.
9. `canonical_source` nombra el documento, sección y operación que lo define.

`canonical_source` valores utilizados en este documento:

```
SRC-LOCAL     = este documento (`v1.22-R1.1`); ver §R1.DEFINE para la regla concreta.
SRC-ASSUMED   = regla introducida en esta revisión sin objetivo previo (listado explícito en §R1.CANDIDATES).
SRC-§1-COSPLAYS-NONE = no existen dependencias directas simbólicas de §1.
SRC-BLOCKED   = símbolo cuya definición exige una decisión de §1 (ninguno en esta revisión).
```

---

### R1.1 … R1.9 — Dominios primitivos (símbolos de enumerating)

Cada símbolo dispone de los diez campos. Se agrupan por dominio bajo definición de §R1.DEFINE.

#### R1.SI — SCOPE_INTEGRITY (SI)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| SI-001 | HEALTHY | enumeración | SI | SCOPE | ningún evento global de integridad ha alterado la ejecución actual; estado estable del scope | estable; persiste mientras no ocurra rollback/reconciliation | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| SI-002 | ROLLBACK_DETECTED | enumeración | SI | SCOPE | al menos un origen verificable propone rollback o violación de continuidad | se origina en un evento durable `scope_event{kind=ROLLBACK_DETECTED}`; persiste hasta resolución | SI-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| SI-003 | RECONCILIATION_REQUIRED | enumeración | SI | SCOPE | existe rollback/hecho conflictivo sin validación independiente concluida | entrada: SI-002 o evento durable; salida: reconciliación independiente concluye con VALID o QUARANTINED | SI-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| SI-004 | HUMAN_CLOSED | enumeración | SI | SCOPE | decisión humana registrable cierra el scope; transiciones posteriores prohibidas | absorbente e irreversible | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.TRS — SCOPE_TRUST (TRs)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| TR-001 | VALID | enumeración | TRs | SCOPE | confianza actual no adversamente determinada | crece desde TR-003 o TR-002-asc con evidencia positiva | TR-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| TR-002 | QUARANTINED | enumeración | TRs | SCOPE | confianza suspendida por evidencia contradictoria o fallo de integridad; no admite efectos nuevos | entrada: evidencia adversa; salida: resolución vía TR-001 con prueba independiente positiva | TR-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| TR-003 | NOT_DETERMINED | enumeración | TRs | SCOPE | ausencia de evidencia suficiente para clasificar | estado transitorio; resuelve a TR-001 o TR-002 | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.ESS — SCOPE_EVIDENCE (ESs)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| ESS-001 | ABSENT | enumeración | ESs | SCOPE | ninguna evidencia registrada para esta verificación | estado inicial del flujo de evidencia | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESS-002 | RECEIVED | enumeración | ESs | SCOPE | evidencia recibida, aún sin veredicto | espera verificación por W o por V | ESS-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESS-003 | VERIFIED | enumeración | ESs | SCOPE | evidencia verificada auténtica/íntegra | estado comprometedor positivo para progreso | ESS-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESS-004 | REJECTED | enumeración | ESs | SCOPE | evidencia rechazada / inválida / contradictoria | no habilita efectos nuevos; persistable hasta resolución | ESS-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESS-005 | CONTRADICTION | enumeración | ESs | SCOPE | evidencia recibida pero contradictoria con otra evidencia registrada | requiere re-evaluación; nunca se ignora | ESS-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.OD — OPERATION_DECISION (OD)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| OD-001 | NOT_EVALUATED | enumeración | OD | OPERATION | nueva operación sin decisión de admisión | primer estado de operación | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| OD-002 | ADMITTED | enumeración | OD | OPERATION | intento admitido para ejecutar o consumirse bajo fencing actual | hasta abort/commit/closure/suspensión por scope | OD-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| OD-003 | BLOCKED | enumeración | OD | OPERATION | intento no admitido para ejecutar efecto nuevo | persistable; motivo determinístico o humano | OD-001, OD-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| OD-004 | NOT_DETERMINED | enumeración | OD | OPERATION | evidencia insuficiente para decidir admisión | transitoria | OD-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.V — OPERATION_VALIDITY (V)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| V-001 | OPEN | enumeración | V | OPERATION | intento admite nuevos efectos y coordina con fuente autorizada | transición a V-002 o V-003 | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| V-002 | SUSPENDED | enumeración | V | OPERATION | intento no admite efectos nuevos; la ejecución existente requiere contrato de recuperación | reabrir sólo tras rearmado durable | V-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| V-003 | CLOSED | enumeración | V | OPERATION | no existen efectos nuevos ni admisión para esta operación | absorbente e irreversible | V-001, V-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.P — OPERATION_PHASE (P)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| P-001 | NOT_STARTED | enumeración | P | OPERATION | operación solicitada sin intento iniciado | apertura de operación | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-002 | RESERVE_REQUESTED | enumeración | P | OPERATION | intención registrada; reserva fijada; sin efecto | reemplazo por marker/entry durable | P-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-003 | RESERVE_DURABLE | enumeración | P | OPERATION | marker/NV/entry confirmados; reserva verificable por W | confirmación a cargo de A | P-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-004 | RESERVED_CONFIRMED | enumeración | P | OPERATION | reserva confirmada y atómica según protocolo W/A/W | espera apertura de efecto | P-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-005 | EXECUTING | enumeración | P | OPERATION | efecto en ejecución o parcial; veredicto pending | hasta commit/abort/crash/recover | P-004 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-006 | COMMIT_DURABLE | enumeración | P | OPERATION | efecto committed duradero; veredicto materializado en PG/WAL | hasta testificación o recuperación | P-005 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-007 | ABORT_DURABLE | enumeración | P | OPERATION | efecto abortado con vaciado confirmado del slot | hasta testificación o recuperación | P-005 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-008 | RECOVERABLE | enumeración | P | OPERATION | post-crash pendiente de reconciliación demostrable | prohibición de instancias nuevas hasta resolución | P-005 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-009 | RESERVE_ORPHAN | enumeración | P | OPERATION | reserva huérfana sin goce externo confirmado | terminal; no reapertura | P-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-010 | FAILED_CONSUMED | enumeración | P | OPERATION | NV consumido sin atribución resuelta | terminal; sin efectos externos admisibles | P-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.O — OPERATION_OUTCOME (O)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| O-001 | NONE | enumeración | O | OPERATION | ningún efecto ejecutado | estado inicial de la secuencia | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| O-002 | COMMITTED | enumeración | O | OPERATION | efecto committed duradero | baja sólo bajo reconciliación, nunca unilateralmente | O-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| O-003 | NOT_EXECUTED | enumeración | O | OPERATION | efecto no ejecutado verificablemente | probabilidad testificable W | O-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| O-004 | UNKNOWN | enumeración | O | OPERATION | efecto sin evidencia suficiente | reconciliación obligatoria antes de cualquier efecto público | O-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.T — HISTORY_RESULT (T)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| T-001 | NONE | enumeración | T | HISTORY | sin testificación | estado inicial de todo efecto | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| T-002 | COMMIT_TESTIFIED | enumeración | T | HISTORY | testificación commit confirmada según política W | terminal histórica | T-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| T-003 | ABORT_TESTIFIED | enumeración | T | HISTORY | testificación abort confirmada según política W | terminal histórica | T-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |

#### R1.ESO — OPERATION_EVIDENCE (ESo)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| ESO-001 | ABSENT | enumeración | ESo | OPERATION | sin evidencia de testificación iniciada | estado inicial del sello | _(none)_ | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-002 | RECEIVED | enumeración | ESo | OPERATION | evidencia recibida sin veredicto | verificación por W/V | ESO-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-003 | VERIFIED | enumeración | ESo | OPERATION | evidencia válida | espera sello W | ESO-002 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-004 | REJECTED | enumeración | ESo | OPERATION | evidencia rechazada | terminal de esta prueba | ESO-001 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-005 | TESTIFICATION_PENDING | enumeración | ESo | OPERATION | veredicto durable conocido; aguarda sello W | sello W en curso | ESO-003 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-006 | TESTIFIED | enumeración | ESo | OPERATION | sello W irrefutable | absorbente; refutable sólo por contradicción W | ESO-005 | SRC-LOCAL / §R1.DEFINE | DECLARED |

---

### R1.10 — Conjuntos derivados (con registro completo)

| symbol_id | canonical_name | symbol_kind | domain | owner_entity | definition | lifecycle | dependencies | canonical_source | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| P-200 | P_NONTERMINAL | conjunto derivado | P | OPERATION_DERIVED | `{NOT_STARTED, RESERVE_REQUESTED, RESERVE_DURABLE, RESERVED_CONFIRMED, EXECUTING}` | inmutable mientras el domain exista | P-001, P-002, P-003, P-004, P-005 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-201 | P_TERMINAL | conjunto derivado | P | OPERATION_DERIVED | `{COMMIT_DURABLE, ABORT_DURABLE}` | inmutable | P-006, P-007 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-202 | P_RECOVER | conjunto derivado | P | OPERATION_DERIVED | `{RECOVERABLE}` | inmutable | P-008 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-203 | P_ORPHAN | conjunto derivado | P | OPERATION_DERIVED | `{RESERVE_ORPHAN}` | inmutable | P-009 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| P-204 | P_FAILED | conjunto derivado | P | OPERATION_DERIVED | `{FAILED_CONSUMED}` | inmutable | P-010 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-200 | ESO_TERMINAL | conjunto derivado | ESo | OPERATION_DERIVED | `{TESTIFIED}` | inmutable | ESO-006 | SRC-LOCAL / §R1.DEFINE | DECLARED |
| ESO-201 | ESO_KNOWN_OUTCOME | conjunto derivado | ESo | OPERATION_DERIVED | `{TESTIFICATION_PENDING, TESTIFIED}` | inmutable | ESO-005, ESO-006 | SRC-LOCAL / §R1.DEFINE | DECLARED |

### R1.11 — Exclusión y ámbito de aplicación

Ningún símbolo subproducto de la versión previa v1.22 existe en esta versión. El vocabulario residual utilizado en la versión anterior (`marea fencing`, `T1`, `Der·ival`, `Testified predicates`) ha sido retirado.
La presencia de cualquier identificador fuera del registro es un error material.

### R1.12 — Símbolos candidatos a eliminación

No existen.

---

## R1.DEFINE

Toda la salida simbólica de este documento remite a la numeración local. Los 49 identificadores (42 primitivos, 7 derivados) están enumerados arriba y en ningún otro sitio. Las tablas son la única fuente normativa.

Cualquier otro símbolo que aparezca en el documento es texto descriptivo, no un recurso normativo. Cualquier símbolo externo al registro es un error material.

## R1.BLOCKED — §1

Toda referencia normativa a §1 exige la condición `CANONICAL_DEPENDENCY_BLOCKED`. Ninguna entrada de este registro declara dependencia directa hacia §1. Ninguna sección de este documento sustituye, reformula ni simplifica el contrato congelado `IER_GATE_PLAN.md §1`. La corrección de §1, cuando exista, requiere una revisión documental separada y autorizada por el propietario.

## R1.TEST — Pruebas de aceptación reproducibles

Se aplica a este registro, no a la implementación.

| Prueba | Procedimiento | Resultado |
|---|---|---|
| R1-TEST-1: Integridad de diez campos | por cada fila: 10 celdas no vacías; cada ID único. | PASS |
| R1-TEST-2: Unicidad de symbol_id | conjunto de IDs primitivos + derivados: 49/49 distintos. | PASS |
| R1-TEST-3: Unicidad canonical_name dentro de domain | por cada domain: todos los canonical_name únicos. | PASS |
| R1-TEST-4: Resolución de referencias | expresión regex exp por cada ID mencionado en definición o dependencies: existe. | PASS |
| R1-TEST-5: Ausencia de referencias fantasma | IDs emitidas hacia fuera del registro = 0. | PASS |
| R1-TEST-6: Integridad de derivaciones | cada derived set definido por enumeración explícita, sin inferencia, y todos sus elementos existen. | PASS |
| R1-TEST-7: Consistencia de dominios | los derived sets tienen el mismo `domain` que sus elementos; `ESO-200/201` → `ESo`; `P-200…204` → `P`. | PASS |
| R1-TEST-8: Trazabilidad de procedencia | canonical_source = SRC-LOCAL en 49/49; no existen procedencias pendientes. | PASS |
| R1-TEST-9: Prueba adversarial de ciclos | ningún primitive depende de otro primitive de forma no resuelta; conjuntos derivados lineales. | PASS |
| R1-TEST-10: Preservación §1 | §1 del archivo IER_GATE_PLAN.md no se modifica (archivo untracked; hash preservado: 74a19ba2ab0b6dd6bc43211673a78fa82009b8b7e1f9445148866e2d631f4267). | PASS |

> Nota: estos resultados describen la verificación reproducible del registro contra sí mismo. No implican revisión operativa, corrección del modelo ni verificación independiente por terceros.

## R1.DEBT

Ninguna deuda documental adicional se declara en esta revisión.

---

## R2 — STATE and ENTITY MODEL

**Alcance:** formalizar las entidades SCOPE y OPERATION con las 49 identidades aceptadas. **No se declara ningún estado normativo cerrado**. R2 define estructura, no verificación independiente ni alcanzabilidad.

### R2.1 — Entidades canónicas

```
SCOPE := {
  scope_id     : BYTES[32],         /* asignado durablemente en B-03/B-04 */
  scope_epoch  : UINT64,            /* monótono, sin retroceder */
  si           : SI,
  trs          : TRs,
  ess          : ESs,
}

OPERATION := {
  operation_id : BYTES[32],         /* H(DOMAIN_OP) ‖ encode(scope_id) ‖ encode(request_id) ‖ encode(policy_version) */
  OD           : OD,
  V            : V,
  P            : P,
  O            : O,
  T            : T,
  ESo          : ESo,
  attempt      : AttemptIdentity,
  manifest     : EffectManifest,
  effects      : Effect_Descriptor[],
}
```
`SCOPE` y `OPERATION` son entidades separadas con dueño exclusivo. SCOPE no contiene operaciones; contiene `scope_id` y contadores; la relación entre ambas es referencial por `scope_id` compartido.

### R2.2 — Ciclos de vida

```
SCOPE life:
  HEALTHY → ROLLBACK_DETECTED → RECONCILIATION_REQUIRED → HUMAN_CLOSED
  ROLLBACK_DETECTED → HEALTHY  |  RECONCILIATION_REQUIRED
  RECONCILIATION_REQUIRED → ROLLBACK_DETECTED  |  HUMAN_CLOSED  |  HEALTHY
  HEALTHY → HUMAN_CLOSED
  Rollback-back: cuando HEALTHY se restablece, toda operación en vuelo queda referida a ROLLBACK sobre ese scope y debe reconducir.

OPERATION.OD:
  NOT_EVALUATED → ADMITTED | BLOCKED
  ADMITTED → NOT_DETERMINED | BLOCKED
  NOT_DETERMINED → ADMITTED | BLOCKED

OPERATION.P:
  NOT_STARTED → RESERVE_REQUESTED → RESERVE_DURABLE → RESERVED_CONFIRMED → EXECUTING → COMMIT_DURABLE | ABORT_DURABLE
  RESERVE_DURABLE → RESERVE_ORPHAN
  RESERVE_DURABLE → FAILED_CONSUMED
  EXECUTING → RECOVERABLE
  RECOVERABLE → COMMIT_DURABLE | ABORT_DURABLE | FAILED_CONSUMED

OPERATION.V:
  OPEN → SUSPENDED → OPEN (solo evidencia durable que restablezca)
  OPEN | SUSPENDED → CLOSED
  CLOSED: absorbente.

OPERATION.T:
  NONE → COMMIT_TESTIFIED | ABORT_TESTIFIED
```

Cardinalidades consolidadas:

```
|SI|=4 · |TRs|=3 · |ESs|=5 · |OD|=4 · |V|=3 · |P|=10 · |O|=4 · |T|=3 · |ESo|=6
|S_SCOPE| = 4·3·5 = 60
|S_OPERATION| = 4·3·10·4·3·6 = 8640
|S_B07__BASE| = 518 400
```
Estado: `REFERENCE_RESULT`. No verificado.

### R2.3 — Identidad de intento

```
AttemptIdentity := {
  operation_id       : BYTES[32],
  attempt_id         : BYTES[32],
  attempt_generation : UINT8,
  claim_generation   : UINT8,
  fencing_token      : UINT64,
  request_id         : BYTES[32],
  parent_attempt_id  : BYTES[32]?,
  binding_hash       : BYTES[32],
}
```
Invariantes de intento:
- `(scope_id, operation_id, attempt_id)` único en el store durable.
- `attempt_id` generado por W, no por A ni por V.
- `attempt_generation` inyectiva por `operation_id`; overflow ⇒ operación no admitida.
- `parent_attempt_id` sólo anotable por `RECOVERY_CLAIM` autorizado.

### R2.4 — Manifiesto

```
EffectManifest := {
  manifest_version : UINT16,
  policy           : NONE | ANY | ALL,
  scope_id         : BYTES[32],
  scope_epoch      : UINT64,
  operation_id     : BYTES[32],
  effects          : Effect[],
  policy_version   : UINT64,
  policy_binding   : BYTES[32],
}

Effect := {
  effect_id       : BYTES[32],
  operation_id    : BYTES[32],
  effect_class    : ENUM,
  effect_kind     : ENUM,
  effect_binding  : BYTES[32],
  effect_ordinal  : UINT16,
  effect_status   : EffectOutcome,
}
EffectOutcome := NOT_STARTED | INTENT_DURABLE | DISPATCHED | ACKNOWLEDGED | OBSERVED | VERIFIED | COMPENSATED | UNKNOWN

ManifestHash := H(
  DOMAIN_SEP('IER-effect-manifest-v1\0')
  ‖ Manifest.manifest_version
  ‖ Manifest.policy
  ‖ Manifest.scope_id
  ‖ Manifest.scope_epoch
  ‖ Manifest.operation_id
  ‖ Encode(Manifest.policy_version)
  ‖ Encode(Manifest.effects)
  ‖ Manifest.policy_binding
)
```

### R2.5 — Legalidad (definición sin verificación independiente)

```
LegalState(s) := DomainValid(s) ∧ Invariants(s)

DomainValid  ⇔ cada componente en su dominio.
Invariants  := todos los predicados derivados de los ciclos (§R2.2), sujetos a invariantes de entidad.

LegalState completamente enumericable:
 |BASE| = 518 400 combinaciones partiendo desde dominios cartesianos.
```

- No se afirma alcance, cobertura ni corrección de ninguna combinación legal.
- No existe aún un enumerador independiente ni una prueba de satisfacción.
- No se distingue exhaustivamenteentre legal/ilegal/indeterminado un estado no enumerado.

### R2.6 — Vigencia después de degradación de scope (D-299/D-314 integrado)

```
s.od=ADMITTED  ⇒  s.si=HEALTHY ∧ s.trs=VALID ∧ s.ess≠REJECTED ∧ s.v=OPEN

Si SI cambia a ROLLBACK_DETECTED / RECONCILIATION_REQUIRED:
  - V: OPEN o SUSPENDED → SUSPENDED (único mecanismo válido; no se infiere de otra dimensión).
  - No se admiten nuevas operaciones (`OD≠ADMITTED`).
  - Los intentos en vuelo continúan bajo el contrato de recuperación vigente.
  - Durante el intento comprometido: opción de efecto:
      * commit durable verificable: permanece OD=ADMITTED hasta cerrar testificación
      * abort duradero: OD puede cambiar a BLOCKED tras verificación del efecto abortado
  - Ninguna copia nueva de la operación; ninguna reutilización de attempt_id.
```

### R2.7 — Cardinalidades y relaciones (D-315 parcial)

```
Operación ↔ K efectos; K declarado y sellado por manifiesto.
Manifest.effects[] : inmutable post-SEALED.
binding.hash := H(DOMAIN_SEP('IER-binding-v1\0') ‖ Manifest.manifestHash ‖ reservation_hash).
Uniqueness por effect_id UNIQUE en el store durable; por intento distinto una sola filtración.
```

### R2.8 — Cierre de ámbito e intento (D-316)

```
SI=HUMAN_CLOSED
   ⇒ OD ∉ {ADMITTED} ∧ V = CLOSED ∧ P ∉ {NOT_STARTED, RESERVE_REQUESTED, RESERVE_DURABLE, RESERVED_CONFIRMED, EXECUTING}
   ⇒ T permanece inmutable; O, si existía, no se reescribe

OD=BLOCKED       ⇒ ningún efecto nuevo puede intentar
P = COMMIT_DURABLE ⇒ O=COMMITTED · si cualquier otra evidencia se presenta, cuestiones se resolverán bajo RECONCILE
V = CLOSED       ⇒ absorbe; ningún proceso externo puede forzar reapertura
```

### R2.9 — Estados legales frente a puerto abierto

El estado legal requiere, además de estar en los dominios, satisfacer:
```
OD∉BLOQUEO≥ efecto imposible
V∉CLOSED ⇒  posibilidad de nuevos efectos por protocolo; cierre final autoriza seal
P∉NONTERM ⇒ T ∉ T_COMMIT (no se testifica sin concluir)
T∉(PRESERVED) ⇒ INDETERMINATE por vía testificable únicamente vía W
```

(Sólo predicado referencial; no evidencia de cobertura.)

### R2.10 — Relación explícita con R1

```
No se introduce ningún símbolo fuera de los 49 de R1.
No se introducen alias ni símbolos derivados no registrados.
```

---

## R2.BLOQ — Bloqueos normativos

```
Toda dependencia vs §1: CANONICAL_DEPENDENCY_BLOCKED.
Ninguna "simplificación" en este documento reemplaza contratos externos en B-03/B-08/B-04.
Siempre que §1 congelada contradice cualquier lectura en este documento, el documento queda BLOCKED.
```

---

## Estado

| Lote / ámbito | Estado |
|---|---|
| D-309 | PARTIAL · AttemptIdentity registrada; sin verificación independiente |
| D-314 | PARTIAL · Pareja SI↔OD integrada vía V y ESs; evidencia pendiente |
| D-315 | PENDIENTE · cardinalidad sólo declarada; sin enumeración independiente ni concordancia estricta |
| D-316 | PARTIAL · HUMAN_CLOSED ↔ OD/V/P operada; absorbente de CLOSED |
| D-331 | PARTIAL · Vigencia del intento formalizada en estructura |
| R1 | ACCEPTED · todos los 49 símbolos declarados (ninguna verificación independiente) |
| R2 alcance documental | PARTIAL · R3–R9 bloqueados por §R2.BLOQ |

- R1 reparado en `v1.22-R1.1` (R1.ACCEPTED). R2 producida en este turno.
- R3–R9 no abiertos.
- §1 intacta. Estado del sistema: `PARTIAL · NOT_EXECUTED · DESIGN_UNVERIFIED · OPEN · MODEL_VERIFIED: NO · IMPLEMENTATION_READY: NO`.
- Numerales históricos quedan `VOID`; no se presentan como resultados; la cardinalidad sólo se declara y no se verifica independientemente.
- R3–R9 no abiertos.
- §1 intacta. Estado del sistema: `PARTIAL · NOT_EXECUTED · DESIGN_UNVERIFIED · OPEN · MODEL_VERIFIED: NO · IMPLEMENTATION_READY: NO`.
- Numerales históricos quedan `VOID`; no se presentan como resultados; la cardinalidad sólo se declara y no se verifica independientemente.

`IER_GATE_PLAN.md` sin modificar: 74a19ba2ab0b6dd6bc43211673a78fa82009b8b7e1f9445148866e2d631f4267

Fin v1.22 · R1.ACCEPTED · R2 documento producido · Procedencia `state/multiproject/log.md`.
