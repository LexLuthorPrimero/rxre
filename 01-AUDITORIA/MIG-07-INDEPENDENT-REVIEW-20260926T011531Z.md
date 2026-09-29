# MIG-07 — INDEPENDENT REVIEW OF THE MAPPING

> Revisión independiente del documento `MIG-07-VOCABULARY-MAPPING-20260926T011531Z.md`.
> **No se modificó el mapeo.** Esta revisión lo evalúa y lo rechaza parcialmente.

```
DOCUMENT_ID=MIG-07-INDEPENDENT-REVIEW
CREATED_UTC=2026-09-26T01:15:31Z
TYPE=INDEPENDENT_REVIEW
REVIEWER=SELF-ADVERSARIAL (mismo agente, método adversarial explícito)
LIMITATION=REQUIRES_INDEPENDENT_HUMAN_OR_SEPARATE_AGENT
MAPPING_ACCEPTED=PARTIAL
MIG-07_STATE=VERIFYING
```

**Limitación de esta revisión, declarada antes de nada:** la hice yo, con el mismo sesgo que
produjo RC-4. Es una revisión *adversarial en método* (intenté romper el mapeo, no defenderlo),
pero **no es independiente en autoría**. Para cerrar MIG-07 según el criterio de cierre
—«una revisión independiente confirmó el mapping»— esto **no cuenta**. Se necesita otro
revisor. Marcado `REQUIRES_INDEPENDENT_REVIEWER`.

---

## Veredicto: el mapeo **NO es adoptable tal como está escrito**

Un hallazgo bloqueante y tres confirmaciones.

---

## B-1 (BLOQUEANTE) · La propuesta adopta vocabulario preexistente e incontrolado

El mapeo propone `VERIFIED`, `REPRODUCIBLE` y `DOCUMENTED` como si fueran **términos nuevos**.
No lo son:

| Término propuesto | Ya aparece en | Declarado en `AGENTS.md` |
|---|---:|---:|
| `VERIFIED` | **40 ficheros** | **0** |
| `REPRODUCIBLE` | **20 ficheros** | **0** |
| `DOCUMENTED` | 5 ficheros | **0** |

Adoptarlos como canónicos **no añade vocabulario: da autoridad a 65 ficheros de uso que
nunca la tuvieron**, y redefine su significado. Eso es exactamente el «vocabulario único falso»
que el encargo prohíbe aceptar.

### Y `VERIFIED` ya significa **cuatro cosas distintas**

Contexto real extraído del repo:

| Uso | Fichero/ejemplo | Sentido |
|---|---|---|
| Columna de estado del censo | `[VERIFIED]/DOC Hardware`, `[VERIFIED ] Drivers` | **clase de estado de ítem del censo** |
| Modificador de grado | `PARTIALLY VERIFIED` — «Evidencia parcial» | **grado**, no clase |
| Regla de escritura | `WRITE SUCCESS ≠ STATE CHANGE VERIFIED` | **confirmación de cambio de estado**, no evidencia |
| Token de máquina de estados | `[VERIFIED]` junto a `state=4 activated` | **salida de systemd** |
| Coloquial | `VERIFIED verde` | **uso informal** |

Ninguno de esos cinco es «verificado por cross-check independiente», que es lo que el mapeo
propone. **Colisión semántica de 5 sentidos en un término que el mapeo declararía único.**

### `REPRODUCIBLE` tampoco es libre

Se usa como parte de un compuesto con negación: `[NO REPRODUCIBLE]` en 8 ficheros. No es una
clase independiente sino un marcador compuesto. Declararlo término autónomo rompe la
notación.

**Consecuencia:** las filas del mapeo `VERIFICADO→VERIFIED`, `REPRODUCIBLE→REPRODUCIBLE` y
`DOCUMENTADO→DOCUMENTED` deben pasar de `LOSS=YES, REQUIRES_MANUAL_REVIEW` a
**`REJECTED_PENDING_RENAMING`**: requieren un nombre que no colisione con el uso preexistente
(por ejemplo un espacio de nombres explícito), no una traducción.

---

## Confirmación 1 · `PASS` es la ambigüedad más extendida de todo el proyecto

`PASS` aparece en **45 ficheros** y **no está declarado en ningún vocabulario canónico**.
Uso real: 25 contextos de gate + 18 de test + 1 de resultado. Es decir, la misma palabra
significa «el gate permite avanzar» y «el test pasó». Es un caso peor que los registrados
porque **no tiene definición de la que depender**.

## Confirmación 2 · `PARTIALLY_RECONCILED` y `PARTIALLY_RESOLVED` no son sinónimos

Co-ocurrencia: **0 ficheros**. No aparecen nunca juntos → se usan en conjuntos documentales
**disjuntos**, lo que confirma que pertenecen a dimensiones distintas (SC-4 del mapeo).
**La revisión confirma SC-4.**

## Confirmación 3 · `NO REPRODUCIBLE` y `NOT_REPRODUCED` tampoco coexisten

Co-ocurrencia: **0 ficheros**. Mismo patrón: misma idea, dos vocabularios, conjuntos
disjuntos. Refuerza que el problema es la **fragmentación**, no la ambigüedad semántica dentro
de un mismo documento.

---

## Conflictos que el mapeo **subestimó**

| # | El mapeo dijo | La revisión encuentra |
|---|---|---|
| SC-6 | `PASS`/`FAIL` no declarados, media | `PASS` en 45 ficheros, 3 sentidos distintos → **ALTA** |
| SC-7 | `DERIVED`/`REJECTED` sin declarar | Correcto, pero se omite que `VERIFIED`/`REPRODUCIBLE`/`DOCUMENTED` están **igual o peor** |
| SC-9 | `REPRODUCIBLE` sin destino en V1 | Correcto, pero la propuesta de destino **colisiona** (B-1) |
| — | no detectado | **`VERIFIED` con 5 sentidos** → nuevo **SC-10, BLOQUEANTE** |
| — | no detectado | **`REPRODUCIBLE` es término compuesto con negación** → nuevo **SC-11** |

##against el criterio de cierre (PASO 10)

| # | Criterio | Estado |
|---:|---|---|
| 1 | vocabularios inventariados | **CUMPLE** — 4 fuentes, conteos reales |
| 2 | dimensiones separadas | **CUMPLE** — 8 dimensiones |
| 3 | mapping completo | **CUMPLE** — 26 filas |
| 4 | ambigüedades identificadas | **CUMPLE** — 9 (+2 nuevos) |
| 5 | sin pérdida silenciosa | **CUMPLE** — 0 migraciones aplicadas |
| 6 | revisión independiente confirmó | **FALLA** — esta revisión **rechaza** parte del mapeo, y no es independiente en autoría |
| 7 | contradicciones explícitas | **CUMPLE** — SC-1..SC-11 registradas |

**5 de 7. El criterio 6 falla por dos razones independientes:** la revisión no es de otro autor,
y su resultado es negativo sobre el mapeo.

---

## Qué hace falta para poder cerrar MIG-07

1. **Resolver el vocabulario preexistente de `VERIFIED` (40 ficheros).** Decisión editorial:
   ¿se adopta su significado actual, se renombra el uso de evidence-class, o se introduce un
   espacio de nombres (`EV.VERIFIED`) que no colisione?
2. **Lo mismo para `REPRODUCIBLE` (20) y `DOCUMENTED` (5).**
3. **Declarar `PASS`** o prohibitions, dado que 45 ficheros ya lo usan con 3 sentidos.
4. **Una revisión de verdad independiente** —otro agente o una persona— que no haya escrito el
   mapeo.
5. Decidir cuál de los 4 vocabularios es canónico. **El mapeo no lo decide, y está bien que no
   lo haga: es una decisión editorial, no técnica.**

```
MIG-07=VERIFYING
CRITERIA_MET=5/7
BLOCKING_FINDINGS=1
NEW_CONFLICTS=2   (SC-10 VERIFIED 5 sentidos; SC-11 REPRODUCIBLE compuesto)
MAPPING_ACCEPTED=PARTIAL
REVIEW_INDEPENDENT=NO  (mismo autor; requiere otro revisor)
RECOMMEND_NEXT=MIG-07 permanece; NO avanzar a MIG-14
```

## Nota sobre el patrón

Este es el **segundo** caso en esta migración donde mi propia propuesta no resistió una revisión
adversarial. El primero fue la terminología V1 reportada como V2. Los dos son la misma causa:
**RC-4, verificado de nuevo sobre mí mismo, ahora con artefacto escrito y no solo con una
respuesta de chat.** Un archivo en el repo es más fácil de refutar que una conclusión en
conversación, y por eso este tipo de revisión tiene que artefactarse.
