# RXRE: ARQUITECTURA CONSOLIDADA v3+unificado

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

| # | Corrección v3 | Dónde está | En el andamiaje | **En RXRE** |
|---|---|---|---|---|
| 1 | ÉTER: 3 modos de fallo + write-ahead | Bloque ÉTER | `arquitectura/ETER.py` | ❌ PROVEN_ABSENT |
| 2 | INVALIDATED con reevaluación | Bloque estados (6) | `arquitectura/TIERRA.py` | ❌ PROVEN_ABSENT — `store.py:210` declara 5 estados |
| 3 | Concurrencia por operación | Bloque schema | `TIERRA.py` | ❌ PROVEN_ABSENT — no hay `version`/`row_count` |
| 4 | Rollback por dispositivo (R12) | Bloque FUEGO | `arquitectura/planos.py` | ❌ PROVEN_ABSENT — homonimia con el rollback de SQLite |
| 5 | Inmutabilidad como mecanismo | Bloque EVIDENCE | triggers en `TIERRA.py` | ❌ PROVEN_ABSENT — 0 triggers; `INSERT OR REPLACE` |
| 6 | Hash: integridad ≠ autenticidad ≠ validez | Bloque hash | `TIERRA.verificar_hash` | ❌ PROVEN_ABSENT — una sola función |
| 7 | ACCEPTED con autoridad declarada | Bloque puerta | `arquitectura/PUERTA.py` | ❌ PROVEN_ABSENT — sin evaluación de condiciones |

Las 7 están **en el andamiaje**. Ninguna está **en RXRE**. La diferencia entre
las dos columnas es el trabajo que queda, y `AUDIT.md` lo enumera.

---

## Dónde vive cada bloque

| Bloque | Módulo | Qué hace |
|---|---|---|
| ALMA | `arquitectura/ALMA.py` | 7 criterios de cierre, evaluables |
| ÉTER | `arquitectura/ETER.py` | write-ahead, idempotencia, 3 modos de fallo, descarte contado |
| AIRE | `arquitectura/AIRE.py` | traza decisión→herramienta→resultado, `tool_hash` obligatorio |
| TIERRA | `arquitectura/TIERRA.py` | claim, evidencia, contradicciones, concurrencia, 3 capas de hash |
| MENTE | `arquitectura/planos.py::Libro` | hipótesis rivales con falsificación obligatoria |
| CUERPO | `arquitectura/planos.py::CUERPO` | medición con hash verificado en punto de uso |
| FUEGO | `arquitectura/planos.py::FUEGO` | transformación controlada, R12 por dispositivo |
| AGUA | `arquitectura/AGUA.py` | aprendizaje con procedencia, revalidación al recuperar |
| ROUTER | `arquitectura/ROUTER.py` | resolución por capacidad, no por nombre de herramienta |
| PUERTA | `arquitectura/PUERTA.py` | las 4 condiciones, sin forma de declararlas a mano |
| schemas | `arquitectura/schemas.py` | los 19 checks del diagrama, todos en HIPÓTESIS |

---

## Lo que este diagrama **no** resuelve

```
✗ ¿ÉTER existe?                → audit: PROVEN_ABSENT
✗ ¿El schema tiene INVALIDATED? → audit: PROVEN_ABSENT
✗ ¿El rollback es por device?   → audit: PROVEN_ABSENT
✗ ¿ACCEPTED tiene autoridad?    → audit: PROVEN_ABSENT
✗ ¿El hash distingue las 3?     → audit: PROVEN_ABSENT
```

Las cinco preguntas siguen abiertas. El diagrama consolida **qué debería
ser**. El audit dice **qué es**. Ninguno reemplaza al otro.

---

## Por qué no es "perfecto"

Un diagrama perfecto requeriría:

```
1. Que el audit confirme cada casilla        → HECHO: 0 de 19 VERIFICADO
2. Que el revisor independiente lo valide    → PENDIENTE: nadie nombrado
3. Que Etapa 1 pase su puerta                 → BLOQUEADA
4. Que Etapa 2-4 midan A vs B                → NO LLEGADA
5. Que el resultado sea positivo              → DESCONOCIDO
```

Las cinco siguen sin cumplirse. El diagrama es el mapa. El territorio está
sin explorar, y ahora está medido.

---

## Lo que este diagrama sí es

```
El techo del diseño sin evidencia.
Todo lo que se puede dibujar sin mentir.
Todo lo que se puede consolidar sin inventar.
```

Y ahora, además: un **andamiaje ejecutable** para las 7 correcciones v3, con
88 aserciones discriminantes que pasan, y un `AUDIT.md` que dice exactamente
qué parte de ese techo ya tiene cimientos.

---

## Estado

```
AUDIT A-F:       ENTREGADO (AUDIT.md, 19 casillas medidas)
INICIO:          NO CONFIRMADO
ETAPA 1:         BLOQUEADA (falta autoridad de aceptación)
IMPLEMENTACION:  PARCIAL — andamiaje construido, NO integrado
DIAGRAMAS:       v3+unificado (consolidado, 7/7 correcciones)
                 HIPÓTESIS — auditadas: 0 VERIFICADO / 7 PARTIAL
                                    / 9 PROVEN_ABSENT / 3 NOT_DETERMINED

PENDIENTE DE DECISIÓN (no de diseño):
  Integrar el andamiaje en store.py y dispatch.py, o dejarlo aparte.
  Es una decisión de migración, no una corrección de documento.
```

**Este diagrama está consolidado.** Si llega otro documento pidiendo
correcciones al diagrama, la respuesta es esta misma: el diagrama está
completo, las casillas están medidas, y lo que falta no es diseño sino
**migración**. La siguiente decisión es de alguien con autoridad sobre qué
se toca primero — y `PUERTA.aceptar()` no deja que esa persona la tome sin
nombrarse.