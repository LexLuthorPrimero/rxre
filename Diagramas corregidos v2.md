# Diagramas corregidos v2 — 7 diagramas, todas las correcciones aplicadas

Aplico las correcciones de los últimos tres mensajes. **Siguen siendo hipótesis.** Pero ahora distinguen lo que antes mezclaban.

---

## 1. ÉTER — tres fallos, tres mecanismos distintos

```
┌──────────────────────────────────────────────────────────────┐
│                         ÉTER                                 │
│                                                              │
│   ┌────────────┐    ┌────────────┐    ┌──────────────┐      │
│   │   cola     │───►│  buffer    │───►│ persistencia │      │
│   │  volátil   │    │emergencia  │    │  en disco    │      │
│   │            │    │ (ring, mem)│    │  (archivo)   │      │
│   └─────┬──────┘    └─────┬──────┘    └──────┬───────┘      │
│         │                 │                   │              │
│    saturación        caída proceso      reinicio             │
│         │                 │                   │              │
│         ▼                 ▼                   ▼              │
│   ┌──────────┐      ┌──────────┐      ┌──────────────┐     │
│   │ descarte │      │ buffer   │      │ TIERRA lee   │     │
│   │ contado  │      │ sobrevive│      │ archivo al   │     │
│   │ + alerta │      │ en RAM   │      │ reiniciar    │     │
│   └──────────┘      └──────────┘      └──────────────┘     │
└──────────────────────────────────────────────────────────────┘

DISTINCIÓN OBLIGATORIA:
  1. Caída de ÉTER (proceso muere)    → buffer en RAM pierde
  2. Saturación de cola (llena)       → descarte contado
  3. Reinicio del proceso             → solo disco sobrevive

RING BUFFER NO ES PERSISTENCIA.
Si el evento debe sobrevivir un reinicio → escribir a disco
ANTES de aceptar el evento (write-ahead).

Eventos críticos (kernel panic, fallo hardware):
  → persistencia SÍ o SÍ
  → buffer en RAM NO ES SUFICIENTE
  → declarar "pérdida admisible" por tipo de evento

Contador de descartes:
  - si vive en RAM → se pierde en reinicio
  - debe persistirse separado o en el mismo archivo
  - TIERRA verifica al recuperar: ¿coincide contador
    persistido con eventos recuperados? Si no → alerta
```

---

## 2. CLAIM — INVALIDATED no es automático

```
                    ┌──────────────────┐
                    │      DRAFT       │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Evaluar evidencia    │
                  └──────────┬───────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  ┌──────────┐        ┌──────────┐        ┌──────────────┐
  │  PROVEN  │        │ PARTIAL  │        │NOT_DETERMINED│
  └────┬─────┘        └────┬─────┘        └──────┬───────┘
       │                   │                     │
       │  nueva evidencia contradictoria         │
       │                   │                     │
       ▼                   │                     │
  ┌──────────────────────────────────┐          │
  │  CONTRADICCIÓN REGISTRADA        │          │
  │  (NO cambia estado automáticam.) │          │
  │                                  │          │
  │  Campos de la contradicción:     │          │
  │  - evidencia que la dispara      │          │
  │  - alcance de la evidencia       │          │
  │  - procedencia                   │          │
  │  - fiabilidad                    │          │
  │  - relación con el claim original│          │
  │  - severidad (calculada, no      │          │
  │    asumida)                      │          │
  └──────────────┬───────────────────┘          │
                 │                              │
                 ▼                              │
     ┌───────────────────────────┐              │
     │  REEVALUACIÓN DOCUMENTADA │              │
     │  (proceso, no transición) │              │
     │                           │              │
     │  Decide:                  │              │
     │  - mantener PROVEN        │              │
     │  - degradar a PARTIAL     │              │
     │  - pasar a INVALIDATED    │              │
     │  - pasar a NOT_DETERMINED │              │
     └───────────┬───────────────┘              │
                 │                              │
     ┌───────────┼───────────┬──────────┐       │
     │           │           │          │       │
     ▼           ▼           ▼          ▼       │
  PROVEN     PARTIAL    INVALIDATED  NOT_DET.   │
  (sigue)    (degrad.)  (refutado)   (reabre)◄──┘

ESTADOS SEPARADOS:
  - estado epistémico (PROVEN, PARTIAL, ...)
  - evento de contradicción (registrado, no es estado)
  - severidad de la contradicción (calculada)

INVALIDATED ≠ automático por contradicción.
Es el resultado de una reevaluación explícita.

Recuperación de INVALIDATED:
  - nueva evidencia que refuta la contradicción
  - → vuelve a reevaluación
  - → puede recuperar PROVEN o quedar PARTIAL
```

---

## 3. Schema — locks y optimistic locking son mecanismos distintos

```
┌────────────────────────────────────┐
│             CLAIM                  │
├────────────────────────────────────┤
│ id                                 │
│ statement                          │
│ object_hash                        │
│ scope                              │
│ epistemic_state                    │
│ evidence_refs[]                    │
│ derivation_refs[]                  │
│ contradiction_refs[]               │
│ falsification_test                 │
│ unresolved_obligations[]           │
├────────────────────────────────────┤
│ CONCURRENCIA (elegir UNO):         │
│                                    │
│ A) OPTIMISTIC LOCKING              │
│    version INT                     │
│    updated_at TS                   │
│    → UPDATE ... WHERE version = ?  │
│    → verificar row_count = 1       │
│    → si 0 → conflicto → reintentar │
│                                    │
│ B) LOCK PESIMISTA                  │
│    locked_by TEXT                  │
│    lock_expires_at TS              │
│    → adquirir lock antes de write  │
│    → lock huérfano si expira       │
│                                    │
│ NO MEZCLAR A y B. Son mecanismos   │
│ distintos para problemas distintos.│
│ Optimistic: alta concurrencia,     │
│             conflictos raros       │
│ Pessimistic: baja concurrencia,    │
│              conflictos frecuentes │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│           EVIDENCE                 │
├────────────────────────────────────┤
│ id                                 │
│ claim_ref                          │
│ type                               │
│ source_hash                        │
│ tool_version                       │
│ command                            │
│ output_hash                        │
│ provenance                         │
├────────────────────────────────────┤
│ INMUTABILIDAD:                     │
│                                    │
│ immutable = true NO ES GARANTÍA.   │
│                                    │
│ Garantías reales:                  │
│ a) APPEND-ONLY: evidence nunca se  │
│    modifica, se agrega nueva       │
│    (con id distinto)               │
│ b) DELETE prohibido por permiso    │
│    (verificado en el punto de      │
│     escritura, no por flag)        │
│ c) Hash del contenido de la fila   │
│    verificado al leer              │
│                                    │
│ Corrección de evidencia:           │
│   nueva evidencia con              │
│   supersedes_ref = id_anterior     │
│   (no se borra, se referencia)     │
└────────────────────────────────────┘
```

---

## 4. Rollback — contrato por dispositivo, no regla genérica

```
┌──────────────────────────────────────────────────────────────┐
│                    R12: NO HAY ROLLBACK GENÉRICO             │
│                                                              │
│  Cada tipo de dispositivo declara:                           │
│                                                              │
│  ┌─────────────────────┬─────────────────────────────────┐  │
│  │ CATEGORÍA           │ REGLA                           │  │
│  ├─────────────────────┼─────────────────────────────────┤  │
│  │ read-only           │ observar OK, NUNCA escribir     │  │
│  │ write-safe          │ restaurar a baseline si difiere │  │
│  │ write-side-effects  │ NUNCA restaurar a ciegas;       │  │
│  │                     │ requiere procedimiento específico│  │
│  │ volatile            │ no restaurable; documentar      │  │
│  │ latched             │ requiere reset explícito;       │  │
│  │                     │ no basta escribir valor         │  │
│  │ bus state (PCIe)    │ renegociación explícita,        │  │
│  │                     │ no "rollback"                   │  │
│  └─────────────────────┴─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│  ESTADO PRE-CAMBIO      │
│  - hash código          │
│  - hash binario         │
│  - snapshot selectivo   │◄── solo registros categorizados
│    de registros:        │    como "write-safe" u "observable"
│    - write-safe         │
│    - observables        │
│  - estado bus (baseline)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  APLICAR CAMBIO         │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │             │
   PASA         FALLA
     │             │
     ▼             ▼
┌──────────┐  ┌─────────────────────────────┐
│Regresión │  │  ROLLBACK                   │
│OK        │  │  1. revertir código         │
└──────────┘  │  2. revertir binario        │
              │  3. restaurar SOLO          │
              │     write-safe registros    │
              │  4. verificar bus           │
              │  5. NO tocar:               │
              │     - read-only             │
              │     - side-effects          │
              │     - volatile              │
              │     - latched               │
              └──────────┬──────────────────┘
                         │
                         ▼
              ┌──────────────────────────────┐
              │  EVALUAR RESULTADO           │
              │                              │
              │  Comparar:                   │
              │  - diff código = 0           │
              │  - diff binario = 0          │
              │  - write-safe = baseline     │
              │  - bus = baseline            │
              │                              │
              │  INVARIANTE FUNCIONAL:       │
              │  ¿el driver sigue funcionando│
              │  como antes? (test, no hash) │
              └──────────┬───────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────────┐  ┌──────────────┐
   │ROLLBACK │    │ROLLBACK      │  │ESTADO        │
   │COMPLETO │    │PARCIAL       │  │DESCONOCIDO   │
   │(todo    │    │(algo difiere)│  │(no se puede  │
   │ coincide)│    │→ alerta     │  │ demostrar)   │
   └─────────┘    └──────────────┘  └──────────────┘

CHECKSUM VRAM:
  - no garantiza estado original
  - detecta cambios respecto a baseline
  - no prueba que la GPU esté "bien"
  - usar como indicador, no como prueba
  - validación funcional (test real) > checksum
```

---

## 5. Hash — verificación en punto de consumo

```
GENERACIÓN (en CI/CD o pre-commit):
  ┌──────────────────────────────────────┐
  │ hook genera hash                     │
  │ → escribe: algoritmo, objeto,        │
  │   procedencia, contexto, timestamp   │
  └──────────────┬───────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  ¿hook omitido? │◄── posible
        │  → hash ausente │
        └────────┬────────┘
                 │
                 ▼
VERIFICACIÓN (en punto de consumo):
  ┌──────────────────────────────────────┐
  │ TIERRA verifica:                     │
  │ 1. ¿existe hash?                     │
  │ 2. ¿algoritmo declarado?             │
  │ 3. ¿coincide con contenido actual?   │
  │ 4. ¿procedencia verificable?         │
  │ 5. ¿referencia confiable disponible? │
  │    - si SÍ → comparar con referencia │
  │    - si NO → autenticidad =          │
  │      NOT_DETERMINED                  │
  └──────────────┬───────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌──────┐ ┌──────┐ ┌─────────────┐
    │VÁLIDO│ │FALLA │ │NO VERIFICABLE│
    │      │ │      │ │(sin ref.)    │
    └──────┘ └──────┘ └─────────────┘

HASH EXISTENTE ≠ HASH VERIFICADO.
Hook local no es garantía (puede omitirse).
Verificación debe ocurrir donde el artefacto se USA,
no solo donde se GENERA.
```

---

## 6. Etapas — registro inmutable, claims reevaluables

```
┌──────────────────────────────────────────────────────────────┐
│                     ETAPA 0: AUDIT A-F                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  INFORME HISTÓRICO: INMUTABLE                          │  │
│  │  - report.md congelado                                 │  │
│  │  - claims.csv congelado                                │  │
│  │  - commands.log congelado                              │  │
│  │  - hashes de artefactos congelados                     │  │
│  │                                                        │  │
│  │  No se reescribe. No se corrige. No se actualiza.      │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  CLAIMS: REEVALUABLES                                  │  │
│  │  - nueva evidencia puede agregarse                     │  │
│  │  - contradicción nueva puede registrarse               │  │
│  │  - reevaluación documentada puede cambiar estado       │  │
│  │  - el informe histórico NO se toca                     │  │
│  │  - se agrega: claims.updated.csv (nueva versión)       │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
                     ETAPA 1
                           │
                           │  Si Etapa 1 descubre que un claim
                           │  del audit era incorrecto:
                           │
                           ▼
              ┌──────────────────────────────┐
              │  NO se invalida el audit.    │
              │  SÍ se documenta:            │
              │  - qué claim                  │
              │  - qué evidencia nueva        │
              │  - qué reevaluación se hizo   │
              │  - nuevo estado del claim     │
              │                              │
              │  El audit histórico sigue    │
              │  describiendo lo que existía │
              │  cuando corrió.              │
              └──────────────────────────────┘

INMUTABILIDAD DEL REGISTRO
  ≠
VALIDEZ ETERNA DE LAS CONCLUSIONES.
```

---

## 7. Checklist — obligaciones verificables

```
Por cada ítem del checklist:

  ┌─────────────────────────────────────────────────┐
  │ OBLIGACIÓN:   [descripción]                     │
  │                                                 │
  │ VERIFICACIÓN:                                   │
  │   [ ] test reproducible (nombre y ubicación)    │
  │   [ ] evidencia citada (artefacto + hash)       │
  │   [ ] justificación de inaplicabilidad          │
  │       (si no se puede testear)                  │
  │                                                 │
  │ ESTADO: PASS | FAIL | NOT_RUN | NOT_DETERMINED  │
  │                                                 │
  │ Si FAIL → no se avanza                          │
  │ Si NOT_RUN → se registra y se justifica         │
  │ Si NOT_DETERMINED → limitación explícita        │
  └─────────────────────────────────────────────────┘

CHECKLIST COMPLETO (v2):

AUDIT/ETAPA 0
  [ ] audit/report.md existe y tiene hash
  [ ] audit/claims.csv existe y tiene hash
  [ ] audit/commands.log con exit codes
  [ ] STATE = ACCEPTED (no DELIVERED, no CHALLENGED)
  [ ] refutaciones críticas resueltas
  [ ] revisor independiente documentado
      (identidad, si conocía el modelo, si participó
       en el diseño)

CLAIM
  [ ] estado es uno de los 6 canónicos
  [ ] si INVALIDATED → contradicción documentada
      con severidad calculada y reevaluación
  [ ] falsification_test presente
  [ ] unresolved_obligations listadas

EVIDENCE
  [ ] append-only (no se modifica in-place)
  [ ] delete prohibido por permiso (verificado)
  [ ] hash del contenido verificado al leer
  [ ] procedencia con productor + transformación

CONCURRENCIA
  [ ] se eligió UN mecanismo (optimistic XOR lock)
  [ ] no se mezclan version + locked_by
  [ ] row_count verificado tras UPDATE

ÉTER
  [ ] distingue caída / saturación / reinicio
  [ ] eventos críticos tienen persistencia
  [ ] contador de descartes persiste
  [ ] recuperación al reiniciar es verificable

ROLLBACK
  [ ] existe contrato por tipo de dispositivo
  [ ] registros categorizados (read-only, write-safe,
      side-effects, volatile, latched)
  [ ] restauración solo de write-safe
  [ ] validación funcional post-rollback
  [ ] si no se puede demostrar → "parcial" o
      "desconocido"

HASH
  [ ] verificación en punto de consumo
  [ ] algoritmo declarado
  [ ] referencia confiable identificada o
      NOT_DETERMINED explícito
```

---

## Lo que NO cambió

```
✗ Los 8 planos siguen siendo hipótesis
✗ La arquitectura sigue sin verificarse
✗ Etapa 1 sigue bloqueada
✗ Sin audit ACCEPTED no hay implementación
```

---

## Estado

```
AUDIT A-F:       ESPERANDO ARTEFACTOS
INICIO:          NO CONFIRMADO
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
DIAGRAMAS:       HIPÓTESIS CORREGIDAS v2
                 (no verificadas)

R12 anotada:     rollback por dispositivo, no genérico
```

Estos 7 diagramas incorporan las correcciones de los últimos tres mensajes. Cuando llegue el audit, el revisor los usa como vocabulario. Antes, no hay donde ponerlos que no sea otro documento.
