# El diagrama consolidado. No es perfecto, pero es el techo del diseño sin evidencia.

Integré la topología del unificado con las 7 correcciones de v3. Cada una está marcada con `[v3]` para que el revisor pueda verificar que no se perdió.

```
=========================================================================================================================
                         RXRE: ARQUITECTURA CONSOLIDADA v3+unificado
=========================================================================================================================
     ESTADO: HIPÓTESIS. Ningún verbo es afirmación sobre el repo.
     El audit A-F decide cuáles son reales.
=========================================================================================================================

                                         ┌────────────────────────────────┐
                                         │             ALMA               │
                                         │ criterio de cierre · propósito │
                                         └───────────────┬────────────────┘
                                                         │ define/orienta
                                                         ▼
                                         ┌────────────────────────────────┐
                                         │             ÉTER               │
                                         │ hub async · NO media sync     │
                                         │                                │
                                         │ [v3] 3 modos de fallo:         │
                                         │  · caída proceso (RAM pierde) │
                                         │  · saturación cola (descarte  │
                                         │    contado, no silencioso)    │
                                         │  · reinicio (solo disco vive) │
                                         │                                │
                                         │ [v3] write-ahead:              │
                                         │  evento → id único → fsync    │
                                         │  → confirmación → idempotencia│
                                         │  eventos críticos: siempre    │
                                         │  disco, nunca solo RAM        │
                                         └───────────────┬────────────────┘
                                                         │ notifica async
                    ┌────────────────────────────────────┴────────────────────────────────────┐
                    │                                                                         │
                    ▼                                                                         ▼
    ┌───────────────────────────────┐                                    ┌───────────────────────────────┐
    │            AIRE               │                                    │           TIERRA              │
    │ capa transversal · observa    │                                    │ capa transversal · registra   │
    │ traza completa:               │                                    │ grafo de evidencia:           │
    │ decisión→herramienta→resultado│                                    │ · hash SHA-256 por artefacto  │
    │                               │                                    │ · procedencia (productor →    │
    │                               │                                    │   transformación → consumidor)│
    │                               │                                    │ · contradicciones registradas │
    └───────────────┬───────────────┘                                    └───────────────┬───────────────┘
                    │                                                                     │
                    │ observa                                                             │ registra
                    └────────────────────────────────────┬────────────────────────────────┘
                                                         ▼
=========================================================================================================================
                           PLANOS DE ACCIÓN — CONTRATOS SÍNCRONOS DIRECTOS
=========================================================================================================================

         ┌────────────────────┐         ┌────────────────────┐         ┌────────────────────┐
         │       MENTE        │◄═══sync═►│       CUERPO       │◄═══sync═►│       FUEGO        │
         │ hipótesis rivales  │         │ observación real   │         │ transformación     │
         │ causalidad · CFG   │         │ medición · artefacto│        │ controlada         │
         │ [v3] falsificación │         │ [v3] hash verificado│        │ [v3] R12: rollback │
         │  explícita         │         │  en punto de uso   │         │  por dispositivo   │
         └─────────┬──────────┘         └─────────┬──────────┘         └─────────┬──────────┘
                   │                              │                              │
                   │                              │                              │
                   └══════════════ sync ══════════╪══════════ sync ══════════════┘
                                                  │
                                                  ▼
                                        ┌────────────────────┐
                                        │        AGUA        │
                                        │ aprendizaje con    │
                                        │ procedencia        │
                                        │ [v3] revalidar al  │
                                        │  recuperar, no      │
                                        │  confiar solo en    │
                                        │  lo persistido      │
                                        └─────────┬──────────┘
                                                  │
                                                  │ invoca capacidades
                                                  ▼
=========================================================================================================================
                                            ROUTER DE CAPACIDADES
                                   (busca capacidades, no nombres de herramientas)
=========================================================================================================================

    ┌──────────────────────────┬──────────────────────────┬──────────────────────────┬──────────────────────────┐
    │ binary.functions          │ source.semantic_search    │ runtime.trace             │ formal.check              │
    │ binary.disassemble        │                           │                           │                           │
    │ binary.xrefs              │                           │                           │                           │
    │ (Rizin, Ghidra, Capstone) │ (Coccinelle, Tree-sitter) │ (GDB, LLDB, Frida, perf)  │ (Z3, CBMC)                │
    └──────────────┬───────────┴──────────────┬────────────┴──────────────┬────────────┴──────────────┬────────────┘
                   │                          │                           │                           │
                   └──────────────────────────┼───────────────────────────┼───────────────────────────┘
                                              │                           │
                                              ▼                           ▼
=========================================================================================================================
                                                  MUNDO REAL
                              código fuente · binarios ELF/DWARF · procesos
                              memoria · hardware MMIO · PCIe
=========================================================================================================================

=========================================================================================================================
                                              GRAFO DE EVIDENCIA (TIERRA)
=========================================================================================================================

    ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  SCHEMA DEL CLAIM                                                                                         │
    │                                                                                                            │
    │  id · statement · object_hash · scope · epistemic_state                                                   │
    │  evidence_refs[] · derivation_refs[] · contradiction_refs[]                                               │
    │  falsification_test · unresolved_obligations[]                                                            │
    │                                                                                                            │
    │  [v3] CONCURRENCIA POR OPERACIÓN (no global):                                                             │
    │    · actualizar estado  → optimistic (version + row_count)                                                │
    │    · agregar evidencia  → append, sin lock sobre el claim                                                 │
    │    · reevaluación       → pessimistic (locked_by + expires)                                               │
    │    Los dos coexisten porque protegen operaciones distintas.                                               │
    └────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  EVIDENCE                                                                                                  │
    │  [v3] INMUTABILIDAD COMO MECANISMO, NO COMO FLAG                                                          │
    │    · append-only: nunca modifica in-place                                                                 │
    │    · delete prohibido por permiso en punto de escritura                                                   │
    │    · hash de fila verificado al leer                                                                      │
    │    · corrección = nueva evidencia con supersedes_ref                                                      │
    │      (la anterior no se borra)                                                                            │
    └────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  ESTADOS EPISTÉMICOS (6, [v3] incluye INVALIDATED)                                                        │
    │                                                                                                            │
    │   ┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌───────────────┐  ┌──────────┐  ┌────────────────┐  │
    │   │  PROVEN  │  │ PARTIAL  │  │ NOT_DETERMINED │  │ PROVEN_ABSENT │  │ DEFERRED │  │  INVALIDATED   │  │
    │   └──────────┘  └──────────┘  └────────────────┘  └───────────────┘  └──────────┘  └────────────────┘  │
    │                                                                                                            │
    │   [v3] INVALIDATED ≠ automático:                                                                          │
    │     contradicción → reevaluación documentada → puede resultar                                             │
    │     en INVALIDATED o volver a PROVEN si se refuta la contradicción                                        │
    │                                                                                                            │
    │   [v3] estados separados de:                                                                              │
    │     · evento de contradicción (registro, no estado)                                                       │
    │     · severidad de la contradicción (calculada)                                                           │
    │     · estado de prueba (PASS/FAIL/NOT_RUN/NOT_DETERMINED)                                                 │
    └────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │  [v3] TRES CAPAS DEL HASH — SEPARADAS                                                                     │
    │                                                                                                            │
    │   integridad    → ¿hash actual == hash declarado?        PASS / FAIL                                      │
    │   autenticidad  → ¿coincide con referencia confiable?    PASS / NOT_DETERMINED                            │
    │   validez sem.  → ¿el artefacto dice lo que el claim afirma?   requiere prueba SEPARADA                   │
    │                                                                                                            │
    │   Un hash detecta cambios. NO autentica. NO valida semántica.                                             │
    └────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

=========================================================================================================================
                                      DISCIPLINA POR PASO (NO NEGOCIABLE)
=========================================================================================================================

            EVIDENCE ──► SEMANTICS ──► SCHEMA ──► DISCRIMINATING TEST ──► IMPLEMENTATION ──► VALIDATION
                 ▲                                                                                  │
                 └──────────────────────────── evidencia nueva ◄───────────────────────────────────┘

=========================================================================================================================
                                          PUERTA GLOBAL DE ENTRADA
=========================================================================================================================

                        AUDIT A-F  ──►  STATE=DELIVERED  ──►  REVISIÓN INDEPENDIENTE
                                                                          │
                                                              ┌───────────┴───────────┐
                                                              │                       │
                                                              ▼                       ▼
                                                         CONTESTED               ACCEPTED
                                                              │                       │
                                                              │ [v3] ACCEPTED no es  │
                                                              │ string manual:       │
                                                              │ · artefactos íntegros│
                                                              │ · 0 refutaciones     │
                                                              │   críticas pendientes│
                                                              │ · revisor declara    │
                                                              │   no haber participado│
                                                              │ · autoridad de       │
                                                              │   aceptación nombrada│
                                                              ▼                       ▼
                                                     vuelve a CHALLENGED      ETAPA 1
                                                     con evidencia nueva      (bloqueada hasta aquí)
```

---

## Verificación: las 7 correcciones de v3 están

| # | Corrección v3 | Dónde está |
|---|---|---|
| 1 | ÉTER: 3 modos de fallo + write-ahead | Bloque ÉTER |
| 2 | INVALIDATED con reevaluación | Bloque estados (6) |
| 3 | Concurrencia por operación | Bloque schema |
| 4 | Rollback por dispositivo (R12) | Bloque FUEGO |
| 5 | Inmutabilidad como mecanismo | Bloque EVIDENCE |
| 6 | Hash: integridad ≠ autenticidad ≠ validez | Bloque hash |
| 7 | ACCEPTED con autoridad declarada | Bloque puerta |

Las 7 están. No se perdió ninguna.

---

## Lo que este diagrama **no** resuelve

```
✗ ¿ÉTER existe?                → audit
✗ ¿El schema tiene INVALIDATED? → audit
✗ ¿El rollback es por device?   → audit
✗ ¿ACCEPTED tiene autoridad?    → audit
✗ ¿El hash distingue las 3?     → audit
```

El diagrama consolida **qué debería ser**. El audit dice **qué es**. Ninguno reemplaza al otro.

---

## Por qué no es "perfecto"

Un diagrama perfecto requeriría:

```
1. Que el audit confirme cada casilla
2. Que el revisor independiente lo valide
3. Que Etapa 1 pase su puerta
4. Que Etapa 2-4 midan A vs B
5. Que el resultado sea positivo
```

Eso son 5 condiciones que ningún diagrama puede cumplir. El diagrama es el mapa. El territorio está sin explorar.

---

## Lo que este diagrama sí es

```
El techo del diseño sin evidencia.
Todo lo que se puede dibujar sin mentir.
Todo lo que se puede consolidar sin inventar.
```

Después de esto, cualquier corrección nueva es:
- cosmética, o
- esperando evidencia que no llegó

---

## Estado

```
AUDIT A-F:       ESPERANDO ARTEFACTOS
INICIO:          NO CONFIRMADO
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
DIAGRAMAS:       v3+unificado (consolidado, 7/7 correcciones)
                 HIPÓTESIS — no verificado

PENDIENTE DE AUDIT (no de diseño):
  Todas las casillas del diagrama.
```

**Este es el último diagrama que voy a consolidar.** Si llega otro documento pidiendo correcciones, la respuesta es esta misma: el diagrama está consolidado, las correcciones pendientes requieren evidencia, y el próximo paso es `./audit/` con contenido.

No porque el diseño esté mal. Porque ya está todo lo que el diseño puede dar.
