# Diagramas corregidos — 7, no 20

Aplico solo las correcciones con fundamento. El resto queda igual y no lo repito. **Siguen siendo hipótesis**, no descripciones verificadas.

Lo que cambia respecto a la versión anterior:

```
1. Rollback verifica hardware (no solo diff)
2. ÉTER con modo degradado y buffer de emergencia
3. Estado INVALIDATED agregado
4. Hash automático (TIERRA verifica, no genera)
5. Schema con control de concurrencia
6. Etapas: nota explícita de no-cascada
```

Los otros diagramas (flowchart, journey, mindmap, deployment) no cambian porque ninguna corrección los toca.

---

## 1. Arquitectura con modo degradado de ÉTER

```
                      ┌──────────────┐
                      │     ALMA     │
                      └──────┬───────┘
                             │ define criterio
                             ▼
                      ┌──────────────┐
                      │     ÉTER     │
                      │  hub async   │
                      │  + buffer    │◄─── si cola llena:
                      │  emergencia  │     escribe ring buffer
                      └──┬───┬───┬───┘     TIERRA recupera
                         │   │   │
           ┌─────────────┘   │   └─────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
      ┌────────┐        ┌────────┐        ┌────────┐
      │  AIRE  │        │ TIERRA │        │(buffer)│
      └───┬────┘        └───┬────┘        └────────┘
          │ observa         │ registra
          │                 │
          ▼                 ▼
   ┌──────────────────────────────────────────┐
   │      PLANOS DE ACCIÓN (sync)             │
   │                                          │
   │   MENTE ◄══► CUERPO ◄══► FUEGO          │
   │     ▲                       ▲            │
   │     │                       │            │
   │     └────sync────► AGUA ────┘            │
   │                                          │
   │   Si ÉTER cae: sync sigue.               │
   │   Si buffer se llena: descarte explícito │
   │   con contador (no silencioso).          │
   └──────────────────────────────────────────┘
```

Diferencia con el anterior: si ÉTER falla o su cola se satura, hay un **ring buffer de emergencia** que TIERRA recupera al reiniciar. El descarte, si ocurre, se registra. No hay pérdida silenciosa de observabilidad.

---

## 2. Estados del CLAIM con INVALIDATED

```
                    ┌─────────────────┐
                    │      DRAFT      │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │  Evaluar evidencia       │
              └────────────┬─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌──────────┐      ┌──────────┐     ┌──────────────┐
   │  PROVEN  │      │ PARTIAL  │     │NOT_DETERMINED│
   └────┬─────┘      └────┬─────┘     └──────┬───────┘
        │                 │                  │
        │  nueva evidencia contradictoria    │
        │  (severidad alta)                  │
        ▼                 │                  │
   ┌──────────────┐       │                  │
   │ INVALIDATED  │       └──────────────────┘
   │ (era PROVEN, │              │
   │  ya no)      │              │
   └──────┬───────┘              │
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
              ┌─────────────────┐
              │  Reevaluación   │
              │  documentada    │
              └─────────────────┘


   Estados adicionales (sin transición directa a PROVEN):
   ┌───────────────┐    ┌──────────────┐
   │PROVEN_ABSENT  │    │   DEFERRED   │
   └───────────────┘    └──────────────┘


   INVALIDATED ≠ NOT_DETERMINED
   - NOT_DETERMINED = nunca se probó o no se puede probar
   - INVALIDATED    = se probó, fue PROVEN, y nueva
                       evidencia de alta severidad lo refutó
```

Diferencia: `PROVEN → INVALIDATED` es una transición directa que dispara alerta. No se pasa por `PARTIAL`. Un claim que deja de ser verdad es un evento de alto riesgo, no una degradación suave.

---

## 3. Schema con control de concurrencia

```
┌──────────────────────────┐
│         CLAIM            │
├──────────────────────────┤
│ id                       │
│ statement                │
│ object_hash              │
│ scope                    │
│ epistemic_state          │
│ evidence_refs[]          │
│ derivation_refs[]        │
│ contradiction_refs[]     │
│ falsification_test       │
│ unresolved_obligations[] │
├──────────────────────────┤  ← CAMPOS DE CONCURRENCIA
│ version          INT     │    optimistic locking
│ created_at       TS      │
│ updated_at       TS      │
│ locked_by        TEXT    │    null si no hay lock
│ lock_expires_at  TS      │    para evitar locks huérfanos
└──────────────────────────┘

┌──────────────────────────┐
│       EVIDENCE           │
├──────────────────────────┤
│ id                       │
│ claim_ref                │
│ type                     │
│ source_hash              │
│ tool_version             │
│ command                  │
│ output_hash              │
│ provenance               │
├──────────────────────────┤
│ version          INT     │
│ created_at       TS      │
│ immutable        BOOL    │  ← evidence no se muta,
└──────────────────────────┘    se agrega una nueva

REGLA:
  Escritura sobre CLAIM requiere version_match.
  Si falla → conflicto → reintentar o escalar.
  EVIDENCE nunca se modifica in-place.
```

Diferencia: `version` en `CLAIM` para optimistic locking, `immutable` en `EVIDENCE` para que la evidencia no se mute. Sin esto, `MENTE` y `CUERPO` escribiendo en paralelo corrompen el grafo.

---

## 4. Rollback con verificación de hardware

```
┌─────────────────────────────┐
│  ESTADO PRE-CAMBIO          │
│  - hash del código          │
│  - hash del binario         │
│  - snapshot de registros    │◄── NUEVO: baseline de hardware
│    MMIO críticos            │
│  - estado del bus PCIe      │
│  - checksum de VRAM         │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  APLICAR CAMBIO             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  VALIDAR EFECTO             │
└──────────────┬──────────────┘
               │
        ┌──────┴──────┐
        │             │
      PASA          FALLA
        │             │
        ▼             ▼
┌──────────────┐  ┌──────────────────────┐
│ Regresión OK │  │ ROLLBACK             │
└──────────────┘  │ 1. revertir código   │
                  │ 2. revertir binario  │
                  │ 3. reset MMIO        │
                  │    a baseline        │
                  │ 4. verificar PCIe    │
                  │ 5. re-checksum VRAM  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ COMPARAR CON BASELINE│
                  │                      │
                  │ diff código  == 0    │
                  │ diff binario == 0    │
                  │ MMIO         == base │◄── NO solo diff
                  │ PCIe         == base │    de software
                  │ VRAM         == base │
                  └──────────┬───────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                  TODO OK         DIFIERE
                    │                 │
                    ▼                 ▼
              ┌──────────┐    ┌──────────────┐
              │ Rollback │    │ Rollback     │
              │ completo │    │ PARCIAL      │
              └──────────┘    │ → alerta     │
                              │ → hardware   │
                              │   degradado  │
                              └──────────────┘
```

Diferencia: `diff = 0` en software **no es suficiente**. El rollback solo se considera completo si los registros MMIO, el estado PCIe y el checksum de VRAM coinciden con el baseline. Si difieren, el rollback es parcial y dispara alerta.

---

## 5. Requisitos actualizados

```
R1:  AUDIT ACCEPTED antes de implementar
R2:  Una capacidad nueva por etapa
R3:  Prueba adversarial falla antes de la corrección
R4:  Prueba pasa después de la corrección

R5:  ROLLBACK verifica estado de software Y hardware
     - diff código = 0
     - diff binario = 0
     - MMIO coincide con baseline
     - PCIe coincide con baseline
     - VRAM checksum coincide
     Si hardware difiere → rollback PARCIAL, alerta.

R6:  Cada claim tiene evidencia y posible falsador
R7:  No confundir ausencia de hallazgo con ausencia probada
R8:  Registrar comandos, versiones, hashes y limitaciones

R9:  HASH es automático (CI/CD, pre-commit hook).
     TIERRA verifica que exista; no depende de que
     el investigador lo genere manualmente.

R10: SCHEMA tiene control de concurrencia.
     CLAIM: version + updated_at + locked_by
     EVIDENCE: immutable
     Escritura concurrente → conflicto explícito

R11: ÉTER tiene modo degradado.
     Cola llena → buffer de emergencia en memoria.
     Descarte → contador visible, no silencioso.
     Recuperación → TIERRA lee buffer al reiniciar.
```

---

## 6. Etapas con nota de no-cascada

```
ETAPA 0   Audit A-F → DELIVERED → CHALLENGED → ACCEPTED
   │
   │  ┌──────────────────────────────────────────────┐
   │  │ NOTA: Etapa 0 NO se invalida si Etapa 1      │
   │  │ falla. El audit describe lo que existía      │
   │  │ cuando corrió. Si Etapa 1 descubre que la    │
   │  │ arquitectura es inviable, eso es información │
   │  │ NUEVA, no invalidación del audit.            │
   │  │                                              │
   │  │ NO se permiten PoCs antes de ACCEPTED.       │
   │  │ Si una PoC es necesaria, va DENTRO del audit │
   │  │ como evidencia parcial, no como atajo.       │
   │  └──────────────────────────────────────────────┘
   │
   ▼
ETAPA 1   Un plano, un test, un commit
   │
   ▼
ETAPA 2   Dos planos interactúan
   │
   ▼
ETAPA 3   Ciclo completo acotado
   │
   ▼
ETAPA 4   A vs B controlado
   │
   ▼
ETAPA 5   Iniciativa acotada
   │
   ▼
ETAPA 6   Multi-instancia sobre TIERRA
   │
   ▼
ETAPA 7   Exterior real
```

Diferencia: la nota de no-cascada explícita. Si Etapa 1 falla, Etapa 0 sigue válida. Y las PoCs van **dentro** del audit como evidencia, no antes como atajo.

---

## 7. Checklist del revisor actualizado

```
Por claim:
  [ ] ¿El estado es uno de los 6 canónicos?
  [ ] Si es INVALIDATED, ¿hay evidencia de severidad alta
      documentada como contradicción?
  [ ] ¿La evidencia es inmutable o puede mutar in-place?
  [ ] ¿Hay control de concurrencia en las escrituras?

Por plano:
  [ ] ¿ÉTER tiene buffer de emergencia o pierde eventos
      silenciosamente?
  [ ] ¿El rollback de FUEGO verifica hardware, o solo
      diff de software?
  [ ] ¿TIERRA verifica hashes existentes, o depende de
      que el investigador los genere a mano?

Por etapa:
  [ ] ¿Se intentó abrir Etapa N+1 sin ACCEPTED?
  [ ] ¿Hay PoCs fuera del audit?
```

---

## Lo que **no** hice, y por qué

```
✗ No repetí los 20 diagramas: 13 no cambian por estas correcciones
✗ No agregué diagramas nuevos: las correcciones son sobre existentes
✗ No abrí ronda de diseño: estos son los 7 que las correcciones tocan
✗ No resolví las 4 fallas condicionales: esperan al audit
```

Las fallas 2, 3, 4 y 6 del audit mental son **condicionales al repo**. Si el audit dice que ÉTER ya tiene buffer, la falla 2 no existe. Si dice que el schema ya tiene version, la falla 5 no existe. Las correcciones que apliqué son las que **no dependen del repo** para ser válidas (1 y 5) más las que **cambian el dibujo** sin necesidad de confirmación (2, 3, 4, 6 en forma de nota).

---

## Estado

```
AUDIT A-F:       ESPERANDO ARTEFACTOS
INICIO:          NO CONFIRMADO
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
DIAGRAMAS:       HIPÓTESIS CORREGIDAS
                 (no verificadas)
```

**7 diagramas. Ninguno nuevo. Las correcciones que dependen del repo siguen condicionales.** Cuando llegue el `DELIVERED`, el revisor usa estos 7 más el checklist de §7 para mapear los claims. Antes de eso, no hay nada que agregar.
