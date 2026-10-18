# Los corrijo. Pero primero una cosa.

Este sería el **octavo documento** de correcciones. Cada uno generó una evaluación que generó más correcciones. El audit sigue sin correr. Si te doy otra versión, va a pasar lo mismo.

Así que hago dos cosas:

1. Te doy los 7 diagramas con **todas** las correcciones de las últimas 4 rondas consolidadas.
2. Cierro el loop: **esta es la última versión sin audit**. No voy a corregir otra.

---

## 1. ÉTER — cola, buffer y disco con protocolo

```
┌──────────────────────────────────────────────────────────────┐
│                         ÉTER                                 │
│                                                              │
│  evento                                                      │
│    │                                                         │
│    ▼                                                         │
│  ┌────────────┐                                              │
│  │ id único   │◄── obligatorio, generado al recibir          │
│  └─────┬──────┘                                              │
│        │                                                     │
│        ▼                                                     │
│  ┌─────────────────────────────────────────┐                │
│  │  ESCRITURA DURABLE (write-ahead)        │                │
│  │  → disco ANTES de confirmar             │                │
│  │  → fsync + verificación                 │                │
│  │  → si falla: rechazar evento            │                │
│  └─────────────────┬───────────────────────┘                │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────┐                │
│  │  CONFIRMACIÓN AL EMISOR                 │                │
│  │  solo después de durable                │                │
│  └─────────────────┬───────────────────────┘                │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────┐                │
│  │  PROCESAMIENTO (idempotente)            │                │
│  │  por id único → si ya procesado, skip   │                │
│  └─────────────────┬───────────────────────┘                │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────┐                │
│  │  RECUPERACIÓN (al reiniciar)            │                │
│  │  1. leer disco                          │                │
│  │  2. detectar registros incompletos      │                │
│  │     (checksum del registro, no solo     │                │
│  │      del contenido)                     │                │
│  │  3. descartar incompletos + registrar   │                │
│  │  4. deduplicar por id                   │                │
│  │  5. verificar contador de descartes     │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  RING BUFFER EN RAM:                                         │
│  → solo para eventos NO críticos                             │
│  → eventos críticos: siempre disco                           │
│  → si RAM se llena: descarte contado,                        │
│    NUNCA silencioso                                          │
│  → contador persistido separado                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. CLAIM — INVALIDATED con reevaluación

```
                    ┌──────────────┐
                    │    DRAFT     │
                    └──────┬───────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Evaluar evidencia    │
                └──────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────────┐
   │  PROVEN  │     │ PARTIAL  │     │NOT_DETERMINED│
   └────┬─────┘     └────┬─────┘     └──────┬───────┘
        │                │                  │
        │ nueva evidencia contradictoria    │
        ▼                │                  │
  ┌────────────────────────────────────┐    │
  │ CONTRADICCIÓN REGISTRADA           │    │
  │ (no cambia estado automáticamente) │    │
  │                                    │    │
  │ - qué evidencia la dispara         │    │
  │ - alcance de esa evidencia         │    │
  │ - procedencia verificable          │    │
  │ - fiabilidad calculada             │    │
  │ - relación con claim original      │    │
  │ - severidad (calculada, no asumida)│    │
  └────────────┬───────────────────────┘    │
               │                            │
               ▼                            │
     ┌───────────────────────┐              │
     │ REEVALUACIÓN          │              │
     │ DOCUMENTADA           │              │
     │ (proceso explícito)   │              │
     │                       │              │
     │ Decide:               │              │
     │  - mantener PROVEN    │              │
     │  - degradar a PARTIAL │              │
     │  - INVALIDATED        │              │
     │  - NOT_DETERMINED     │              │
     └──────────┬────────────┘              │
                │                           │
                ▼                           │
        ┌───────────────┐                   │
        │  INVALIDATED  │◄──────────────────┘
        │  (si reeval.  │
        │   lo decide)  │
        └───────┬───────┘
                │
                │ recuperación:
                │ nueva evidencia que
                │ refuta la contradicción
                ▼
        ┌───────────────┐
        │ NUEVA         │
        │ REEVALUACIÓN  │
        └───────────────┘

ESTADOS SEPARADOS:
  - estado epistémico del claim
  - evento de contradicción (registro, no estado)
  - severidad de la contradicción

INVALIDATED ≠ automático.
Es resultado de reevaluación explícita.
```

---

## 3. Schema — mecanismo por operación, no por sistema

```
┌────────────────────────────────────────────────────────────┐
│                    CLAIM                                   │
├────────────────────────────────────────────────────────────┤
│ id · statement · object_hash · scope                       │
│ epistemic_state · evidence_refs[] · derivation_refs[]      │
│ contradiction_refs[] · falsification_test                  │
│ unresolved_obligations[]                                   │
├────────────────────────────────────────────────────────────┤
│ CONTROL DE CONCURRENCIA — POR OPERACIÓN, NO GLOBAL         │
│                                                            │
│ Operación: actualizar estado epistémico                    │
│   → OPTIMISTIC: version INT                                │
│   → UPDATE WHERE id=? AND version=?                        │
│   → verificar row_count=1                                  │
│                                                            │
│ Operación: agregar evidencia                               │
│   → APPEND (no modifica claim)                             │
│   → nueva fila en EVIDENCE                                 │
│   → sin lock sobre CLAIM                                   │
│                                                            │
│ Operación: reevaluación completa                           │
│   → PESSIMISTIC: locked_by + lock_expires_at               │
│   → si expira → lock huérfano → reclamar                   │
│   → usar solo si la operación toca múltiples campos        │
│                                                            │
│ Los dos mecanismos pueden coexistir en el mismo sistema    │
│ porque protegen operaciones distintas.                     │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                    EVIDENCE                                │
├────────────────────────────────────────────────────────────┤
│ id · claim_ref · type · source_hash · tool_version         │
│ command · output_hash · provenance                         │
├────────────────────────────────────────────────────────────┤
│ INMUTABILIDAD — GARANTIZADA, NO DECLARADA                  │
│                                                            │
│ 1. APPEND-ONLY: nunca se modifica                          │
│ 2. DELETE prohibido por permiso en el punto de escritura   │
│ 3. Hash de fila verificado al leer                         │
│ 4. Corrección = nueva evidencia con supersedes_ref         │
│    → la anterior NO se borra                               │
│                                                            │
│ `immutable = true` como flag no es garantía.               │
│ La garantía está en el mecanismo, no en el campo.          │
└────────────────────────────────────────────────────────────┘
```

---

## 4. Rollback — contrato por dispositivo + validación funcional

```
┌──────────────────────────────────────────────────────────────┐
│             R12: NO HAY ROLLBACK GENÉRICO                    │
│                                                              │
│  Cada dispositivo declara por registro:                      │
│                                                              │
│  ┌──────────────┬─────────────────────────────────────────┐ │
│  │ CATEGORÍA    │ REGLA                                   │ │
│  ├──────────────┼─────────────────────────────────────────┤ │
│  │ read-only    │ observar OK, NUNCA escribir             │ │
│  │ write-safe   │ restaurar SOLO si el contrato del       │ │
│  │              │ dispositivo lo permite EN ESTE contexto │ │
│  │ side-effects │ NUNCA restaurar a ciegas                │ │
│  │ volatile     │ no restaurable; documentar              │ │
│  │ latched      │ reset explícito, no escritura de valor  │ │
│  │ bus (PCIe)   │ renegociación explícita, no "rollback"  │ │
│  └──────────────┴─────────────────────────────────────────┘ │
│                                                              │
│  write-safe NO es etiqueta estática.                         │
│  Depende de:                                                 │
│  - estado actual del dispositivo                             │
│  - dependencias entre registros                              │
│  - efectos de operaciones previas                            │
│  - orden de restauración                                     │
│                                                              │
│  Si write-safe no se puede demostrar en contexto →           │
│  no escribir; declarar estado desconocido                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────┐
│  BASELINE PRE-CAMBIO     │
│  - hash código           │
│  - hash binario          │
│  - snapshot de registros │
│    observables y         │
│    write-safe             │
│  - estado bus baseline   │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│  APLICAR CAMBIO          │
└───────────┬──────────────┘
            │
     ┌──────┴──────┐
     │             │
   PASA         FALLA
     │             │
     ▼             ▼
┌──────────┐  ┌─────────────────────────────────┐
│Regresión │  │  ROLLBACK                       │
│OK        │  │  1. revertir código             │
└──────────┘  │  2. revertir binario            │
              │  3. verificar contrato por      │
              │     registro ANTES de escribir  │
              │  4. restaurar solo si el        │
              │     contrato lo permite         │
              │  5. no tocar categorías         │
              │     no restaurables             │
              └──────────────┬──────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │  VALIDACIÓN FUNCIONAL           │
              │                                 │
              │  NO es diff = 0.                │
              │  NO es checksum.                │
              │  ES test del dispositivo:       │
              │  ¿sigue haciendo lo que hacía?  │
              │                                 │
              │  Si pasa + baseline coincide:   │
              │  → ROLLBACK COMPLETO            │
              │                                 │
              │  Si pasa + baseline difiere:    │
              │  → ROLLBACK PARCIAL (alerta)    │
              │                                 │
              │  Si no pasa:                    │
              │  → ESTADO DESCONOCIDO           │
              │    (no "rollback falló",        │
              │     sino "no sabemos qué es")   │
              └─────────────────────────────────┘
```

---

## 5. Hash — integridad, autenticidad, procedencia separadas

```
GENERACIÓN (CI/CD o pre-commit):
  ┌────────────────────────────────────────┐
  │ hash = algoritmo(objeto)               │
  │ + metadatos:                           │
  │   - algoritmo usado                    │
  │   - objeto (path, id)                  │
  │   - procedencia (quién, cuándo, cómo)  │
  │   - contexto de cálculo                │
  └──────────────┬─────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ ¿hook omitido? │◄── posible
        │  → sin hash    │
        └────────┬───────┘
                 │
                 ▼
VERIFICACIÓN (punto de consumo):
  ┌────────────────────────────────────────┐
  │ Capa 1 — INTEGRIDAD                    │
  │   ¿hash declarado coincide con         │
  │    contenido actual?                   │
  │   → SÍ: contenido no cambió desde      │
  │     que se calculó el hash             │
  │   → NO: cambió algo                    │
  │                                        │
  │ Capa 2 — AUTENTICIDAD                  │
  │   ¿hash coincide con referencia        │
  │    confiable externa?                  │
  │   → SÍ: quién produjo el artefacto     │
  │     es quien dice ser                  │
  │   → NO DISPONIBLE: autenticidad =      │
  │     NOT_DETERMINED                     │
  │                                        │
  │ Capa 3 — VALIDEZ SEMÁNTICA             │
  │   ¿el artefacto dice lo que el         │
  │    claim afirma?                       │
  │   → requiere prueba separada,          │
  │     NO se deriva del hash              │
  └──────────────┬─────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ Tres resultados SEPARADOS:     │
    │ integridad     = PASS/FAIL     │
    │ autenticidad   = PASS/NOT_DET  │
    │ validez semán. = requiere test │
    └────────────────────────────────┘

Un hash sin referencia confiable:
  → detecta cambios (integridad)
  → NO autentica (quién lo produjo)
  → NO valida semántica (qué significa)
```

---

## 6. Etapas — registro inmutable, claims reevaluables

```
┌──────────────────────────────────────────────────────────────┐
│                     ETAPA 0: AUDIT A-F                       │
│                                                              │
│  INFORME HISTÓRICO: INMUTABLE                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - report.md + hash                                     │ │
│  │ - claims.csv + hash                                    │ │
│  │ - commands.log + exit codes                            │ │
│  │ - hashes de artefactos de entrada                      │ │
│  │ - STATE inicial                                        │ │
│  │                                                        │ │
│  │ No se reescribe. Se versiona.                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  CLAIMS: REEVALUABLES                                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - nueva evidencia puede agregarse                      │ │
│  │ - contradicción puede registrarse                      │ │
│  │ - reevaluación puede cambiar estado                    │ │
│  │ - se escribe en claims.updated.csv (nueva versión)     │ │
│  │ - el informe histórico NO se toca                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ACEPTACIÓN:                                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ STATE = ACCEPTED NO es string manual.                  │ │
│  │                                                        │ │
│  │ Requiere:                                              │ │
│  │ 1. artefactos íntegros (hash verificado)               │ │
│  │ 2. obligaciones críticas resueltas                     │ │
│  │ 3. limitaciones documentadas                           │ │
│  │ 4. revisor independiente:                              │ │
│  │    - identidad declarada                               │ │
│  │    - no participó en diseño                            │ │
│  │    - no preparó las pruebas                            │ │
│  │    - no conocía conclusiones esperadas                 │ │
│  │ 5. autoridad de aceptación declarada:                  │ │
│  │    quién firma, con qué evidencia, cómo                 │ │
│  │                                                        │ │
│  │ Si falta cualquier condición → NO ACCEPTED              │ │
│  │ → máximo DELIVERED                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Checklist — obligaciones con autoridad

```
POR CADA ÍTEM:

  ┌─────────────────────────────────────────────────┐
  │ OBLIGACIÓN: [descripción]                       │
  │                                                 │
  │ VERIFICACIÓN (elegir una):                      │
  │   [ ] test reproducible (nombre + ubicación)    │
  │   [ ] evidencia citada (artefacto + hash)       │
  │   [ ] justificación de inaplicabilidad          │
  │                                                 │
  │ ESTADO: PASS | FAIL | NOT_RUN | NOT_DETERMINED  │
  │                                                 │
  │ SI FAIL → bloquea avance                        │
  │ SI NOT_RUN → se registra, se justifica          │
  │ SI NOT_DETERMINED → limitación explícita        │
  └─────────────────────────────────────────────────┘

CHECKLIST MÍNIMO:

AUDIT
  [ ] report.md + claims.csv + commands.log con hash
  [ ] STATE con firma de autoridad declarada
  [ ] revisor independiente:
      - identidad
      - no participó en diseño
      - no preparó pruebas
      - no conocía conclusiones esperadas
  [ ] refutaciones críticas: 0 pendientes

CLAIM
  [ ] estado ∈ {6 canónicos}
  [ ] INVALIDATED solo si reevaluación documentada
  [ ] falsification_test presente
  [ ] contradicciones con severidad calculada

EVIDENCE
  [ ] append-only verificado en escritura
  [ ] delete prohibido por permiso (verificado)
  [ ] hash de fila verificado al leer
  [ ] supersedes_ref en correcciones

CONCURRENCIA
  [ ] mecanismo declarado POR OPERACIÓN
  [ ] optimistic y pessimistic pueden coexistir
  [ ] row_count verificado tras UPDATE

ÉTER
  [ ] id único por evento
  [ ] eventos críticos: write-ahead durable
  [ ] recuperación idempotente verificada
  [ ] contador de descartes persistido

ROLLBACK
  [ ] contrato por dispositivo documentado
  [ ] write-safe demostrado en contexto
  [ ] validación funcional post-rollback
  [ ] estados: completo / parcial / desconocido

HASH
  [ ] integridad verificada
  [ ] autenticidad: referencia confiable o NOT_DETERMINED
  [ ] validez semántica por prueba separada
```

---

## Cierre

Esta es la **versión final sin audit**. Consolida 4 rondas de correcciones:

```
ÉTER:         protocolo completo (write-ahead, idempotencia,
              recuperación)
CLAIM:        INVALIDATED con reevaluación explícita
SCHEMA:       mecanismo por operación, inmutable por
              mecanismo no por flag
ROLLBACK:     contrato por dispositivo + validación funcional
HASH:         integridad ≠ autenticidad ≠ validez semántica
ETAPAS:       registro inmutable, claims reevaluables,
              ACCEPTED con autoridad declarada
CHECKLIST:    obligaciones verificables con autoridad
```

**No voy a corregir otra versión sin audit.** Cualquier mensaje que pida una v4 va a recibir esta misma respuesta: los diagramas están consolidados, las correcciones pendientes necesitan evidencia.

---

## Estado

```
AUDIT A-F:       ESPERANDO ARTEFACTOS
INICIO:          NO CONFIRMADO
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
DIAGRAMAS:       v3 CONSOLIDADO (no verificado)

PENDIENTE DE AUDIT (no de diseño):
  - ¿ÉTER existe? ¿tiene write-ahead?
  - ¿el schema existe? ¿tiene concurrencia?
  - ¿el rollback es por dispositivo?
  - ¿ACCEPTED tiene autoridad declarada?
```

**La próxima corrección es el audit.** No un diagrama.
