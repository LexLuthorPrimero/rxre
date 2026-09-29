# MIG-07 — VOCABULARY MAPPING

> Registro de auditoría. **NO modifica los 1577 registros del censo ni del routing.**
> Propuesta de normalización. Ninguna traducción se ha aplicado.

```
DOCUMENT_ID=MIG-07-VOCABULARY-MAPPING
CREATED_UTC=2026-09-26T01:15:31Z
TYPE=MAPPING_PROPOSAL
RECORDS_MIGRATED=0
CENSUS_MODIFIED=NO
ROUTING_MODIFIED=NO
MIG-07_STATE=VERIFYING
```

Método: **conteos reales por grep sobre 1128 ficheros versionados**, no suposiciones. Donde el
significado no es unívoco, el término queda marcado `REQUIRES_MANUAL_REVIEW`.

---

## 1. INVENTARIO LITERAL

### V1 — Vocabulario del encargo (aplicado en los documentos R1)

| Término | Definición | Occ | Ficheros | Dimensión |
|---|---|---:|---:|---|
| `OBSERVED` | dato leído directamente de una fuente | 147 | 24 | evidencia |
| `SUPPORTED` | respaldado por evidencia y gates definidos | 145 | 35 | evidencia |
| `DERIVED` | derivado por razonamiento de otra evidencia | 33 | 14 | evidencia |
| `PLAUSIBLE` | plausible pero no establecido | 20 | 12 | evidencia |
| `HYPOTHESIS` | conjetura no confirmada | 29 | 16 | evidencia |
| `UNKNOWN` | evidencia insuficiente | 806 | 149 | evidencia + estado ⚠ |
| `NOT_AVAILABLE` | fuente o artefacto requerido no disponible | 286 | 57 | evidencia + resultado ⚠ |
| `NOT_PROVEN` | afirmada pero no demostrada | 49 | 18 | evidencia |
| `REJECTED` | evidencia rechazada por no admisible | 22 | 13 | evidencia |
| `CONFLICT` | las fuentes discrepan | 183 | 41 | evidencia + estado ⚠ |

⚠ = el mismo término se usa también en otra dimensión.

### V2 — Vocabulario declarado en `AGENTS.md` §Evidence vocabulary

| Término | Definición literal | Occ | Ficheros | Dimensión |
|---|---|---:|---:|---|
| `OBSERVED` | directly read or recorded from a source | 147 | 24 | evidencia |
| `SUPPORTED` | supported by the defined evidence and gates | 145 | 35 | evidencia |
| `PLAUSIBLE` | plausible but not established | 20 | 12 | evidencia |
| `UNKNOWN` | evidence is insufficient | 806 | 149 | evidencia |
| `NOT_AVAILABLE` | the required source or artifact is unavailable | 286 | 57 | evidencia |
| `CONFLICT` | sources disagree | 183 | 41 | evidencia |
| `FAIL` | an explicit gate failed | 173 | 42 | **gate** |
| `DEFERRED` | intentionally not performed or requires later authorization | 78 | 33 | **hallazgo/fase** |

**Hallazgo:** V1 ⊃ V2 en 6 términos. V2 añade `FAIL` y `DEFERRED`, que son de **otras
dimensiones**. `DERIVED` y `REJECTED` (33 y 22 usos) **no están declarados** en `AGENTS.md`
(0 ocurrencias): existen en la práctica pero sin definición canónica.

### V3 — `NOTEBOOKLM/02-R1-6-EVIDENCE-STATE-MODEL.md`

| Término | Significado | Occ | Ficheros | Dimensión |
|---|---|---:|---:|---|
| `VERIFICADO` | fuente primaria + cross-check independiente | **329** | **47** | evidencia |
| `REPRODUCIBLE` | repetido ≥2 veces idéntico con el mismo método | 62 | 20 | evidencia (fuerza) |
| `OBSERVADO` | sensor directo, evento único | 45 | 19 | evidencia |
| `HIPÓTESIS` | conjetura no confirmada | 117 | 37 | evidencia |
| `DOCUMENTADO` | textual de una fuente, no medida aquí | 84 | 14 | evidencia (tipo de fuente) |
| `PARTIALLY_RECONCILED` | dos fuentes difieren pero el mecanismo está explicado | 42 | 15 | evidencia |
| `UNRESOLVED` | fuente insuficiente, no decidible | 57 | 25 | evidencia + resultado ⚠ |
| `CONTRADICTED` | dos fuentes incompatibles, no resoluble | 93 | 31 | evidencia |
| `NO REPRODUCIBLE` | resultado histórico no reconstruible | 41 | 18 | resultado |
| `NO VERIFICADO` | sin evidencia en ninguna fuente | 47 | 14 | evidencia |

### V4 — `PROBLEM-STATUS-FINAL.md` §Estado (NO estaba en el enunciado de MIG-07)

| Término | Occ | Ficheros | Dimensión |
|---|---:|---:|---|
| `RESOLVED` | 10 | 5 | resultado de problema |
| `PARTIALLY_RESOLVED` | 31 | 6 | resultado de problema |
| `UNRESOLVED` | 57 | 25 | resultado de problema ⚠ |
| `OBSOLETE` | 14 | 2 | validez temporal |
| `ALREADY_FIXED_UPSTREAM` | 7 | 2 | atribución de causa |
| `NOT_REPRODUCED` | 23 | 4 | resultado |
| `UNKNOWN` | 806 | 149 | evidencia + resultado ⚠ |
| `NOT_AVAILABLE` | 286 | 57 | evidencia + resultado ⚠ |

**V4 es un cuarto vocabulario de RESULTADO, y el enunciado de MIG-07 lo omitía.** Sus 8 términos
gobiernan la columna `Estado` del documento de estado canónico del proyecto.

## 2. DIMENSIONES SEPARADAS (PASO 3)

| Dim | Nombre | Términos propios | NO debe mezclarse con |
|---|---|---|---|
| A | `EVIDENCE_CLASSIFICATION` | V1 (10) + VERIFICADO, REPRODUCIBLE, DOCUMENTADO, CONTRADICTED, PARTIALLY_RECONCILED | B, C, D, E, F |
| B | `FINDING_STATE` | `OPEN` `INVESTIGATING` `ROOT_CAUSE_IDENTIFIED` `CORRECTED` `VERIFYING` `CLOSED` `LIMITATION_CONFIRMED` `NOT_A_PROBLEM` `BLOCKED_BY_EXTERNAL_LIMITATION` | A, D |
| C | `ROOT_CAUSE_STATE` | `HYPOTHESIS` `CONFIRMED` `UNRESOLVABLE` | A, B |
| D | `PHASE_STATE` | `DEFERRED` `PREPARED_FOR_REVIEW` `NOT_EXECUTED` `CONTAMINATED_REQUIRES_ISOLATION` | A, B, E |
| E | `GATE_STATE` | `BLOCK` `ALLOW` `FAIL` `PASS` `NOT_EVALUATED` | A, B, D |
| F | `EXPERIMENTAL_RESULT` | `RESOLVED` `PARTIALLY_RESOLVED` `UNRESOLVED` `NOT_REPRODUCED` `ALREADY_FIXED_UPSTREAM` `OBSOLETE` | A, B |
| G | `CONFIDENCE` | (V3 lo implye dentro de VERIFICADO/REPRODUCIBLE; hoy no es dimensión propia) | A |
| H | `PROVENANCE` | `HOST_SCOPE` `HOST_SCOPE_BASIS` `RUN_ID` `SHA256` — ortogonal, no es un estado | A–G |

**G y H quedan sin vocabulario propio.** H ya existe como metadata (`HOST_SCOPE`,
`HOST_SCOPE_BASIS`, `RUN_ID`, hashes) y es ortogonal: no debe mezclarse con ninguna dimensión de
estado. G es la única Carencia real: `CONFIDENCE` se declara como campo `ALTA/MEDIA/BAJA` en la
plantilla R1-6 pero **no tiene enumeración canónica**.

## 3. CONFLICTOS SEMÁNTICOS (PASO 7)

| # | Conflicto | Evidencia | Gravedad |
|---|---|---|---|
| **SC-1** | **`UNRESOLVED` significa DOS cosas**: en V3 es estado de *evidencia*; en V4 es estado de *problema*. Mismos 57 usos, mismos 25 ficheros → es el mismo token en dos dimensiones | recuento idéntico | **ALTA** |
| **SC-2** | **`UNKNOWN` en 3 dimensiones**: evidencia (V1/V2), resultado (V4), y usado como valor por defecto en varios documentos de estado. 806 usos, 149 ficheros | 806/149 | **ALTA** |
| **SC-3** | **`NOT_AVAILABLE` en 2**: evidencia (V1/V2) y resultado de problema (V4). 286 usos | 286/57 | **ALTA** |
| **SC-4** | **`PARTIALLY_RECONCILED` (V3, evidencia) vs `PARTIALLY_RESOLVED` (V4, resultado)**: casi sinónimos en dimensiones distintas. Convertirlos sería una traducción no silenciosa | 42 vs 31 | ALTA |
| **SC-5** | **Dos idiomas para el mismo concepto**: `OBSERVADO`/`OBSERVED`, `HIPÓTESIS`/`HYPOTHESIS`, `CONTRADICTED`/`CONFLICT`, `NO REPRODUCIBLE`/`NOT_REPRODUCED`, `NO VERIFICADO`/`NOT_AVAILABLE` | V3 completa | MEDIA |
| **SC-6** | **`PASS` (45 ficheros) y `FAIL` (42) nunca se declararon**: `FAIL` está en AGENTS.md como gate, `PASS` no aparece en ningún vocabulario | grep | MEDIA |
| **SC-7** | **`DERIVED` y `REJECTED` se usan (33 y 22) pero no están declarados** en ningún vocabulario canónico | 0 en AGENTS.md | MEDIA |
| **SC-8** | **`DEFERRED` es estado en V2 pero se usa como clasificación de evidencia** en documentos R1 | 78/33 | MEDIA |
| **SC-9** | **`REPRODUCIBLE` (62 usos) no tiene equivalente** en V1/V2/V4: es una dimensión de *fuerza* que se perdería | 62/20 | **ALTA** |

## 4. PROPUESTA NORMALIZADA

### 4.1 `EVIDENCE_CLASSIFICATION` (dimensión A)

Se propone añadir a V1, no sustituirlo:

| Término | Origen | Nota |
|---|---|---|
| `VERIFIED` | V3 `VERIFICADO` | **renombrado**: cross-check independiente explícito |
| `OBSERVED` | V1/V2/V3 | unificado de las 3 grafías |
| `REPRODUCIBLE` | V3 | **nuevo en V1**, conserva la distinción de fuerza |
| `SUPPORTED` | V1/V2 | — |
| `DOCUMENTED` | V3 `DOCUMENTADO` | fuente textual, no medida |
| `DERIVED` | V1 |gana definición canónica |
| `PLAUSIBLE` | V1/V2 | — |
| `HYPOTHESIS` | V1/V3 | unificado |
| `PARTIALLY_RECONCILED` | V3 | estado de resolución de conflicto, **no** equivalente a `CONFLICT` |
| `CONFLICT` | V1/V2/V3 | — |
| `REJECTED` | V1 | gana definición canónica |
| `UNKNOWN` | V1/V2 | — |
| `NOT_AVAILABLE` | V1/V2 | — |
| `NOT_PROVEN` | V1 | — |
| `CONTRADICTED` | V3 | colapsa en `CONFLICT` (sin pérdida: ambos = fuentes incompatibles) |

### 4.2 `FINDING_STATE` (B) — nuevo, sin predecesor
`OPEN` · `INVESTIGATING` · `ROOT_CAUSE_IDENTIFIED` · `CORRECTED` · `VERIFYING` · `CLOSED` ·
`LIMITATION_CONFIRMED` · `NOT_A_PROBLEM` · `BLOCKED_BY_EXTERNAL_LIMITATION`

### 4.3 `ROOT_CAUSE_STATE` (C) — nuevo
`HYPOTHESIS` · `CONFIRMED` · `UNRESOLVABLE`

### 4.4 `GATE_STATE` (E)
`BLOCK` · `ALLOW` · `NOT_EVALUATED`. `PASS`/`FAIL` **dejan de ser gate state**: `PASS` es un
resultado favorable y `FAIL` un resultado desfavorable; la decisión de avanzar es `ALLOW`/`BLOCK`.

### 4.5 `EXPERIMENTAL_RESULT` (F) — desde V4
`RESOLVED` · `PARTIALLY_RESOLVED` · `UNRESOLVED` · `NOT_REPRODUCED` · `ALREADY_FIXED_UPSTREAM` · `OBSOLETE`

## 5. MATRIZ DE EQUIVALENCIAS

`LOSS_OF_INFORMATION=YES` marca las traducciones que **no** deben hacerse en silencio.

| ORIGINAL_TERM | SOURCE | ORIGINAL_MEANING | DIM | NORMALIZED_TERM | LOSS | AMBIG | REVISAR |
|---|---|---|---|---|---|---|---|
| `VERIFICADO` | V3 | primaria + cross-check | A | `VERIFIED` | **YES** — V1 no tiene «cross-check» | no | sí |
| `REPRODUCIBLE` | V3 | ≥2 repeticiones idénticas | A | `REPRODUCIBLE` | **YES** — no existe en V1 | no | sí |
| `DOCUMENTADO` | V3 | textual, no medida | A | `DOCUMENTED` | **YES** — `SUPPORTED` implicaría más | no | sí |
| `PARTIALLY_RECONCILED` | V3 | difieren, mecanismo explicado | A | `PARTIALLY_RECONCILED` | **YES** — `CONFLICT` implicaría irresoluble | **sí** | sí |
| `CONTRADICTED` | V3 | incompatibles, no resoluble | A | `CONFLICT` | no | no | no |
| `OBSERVADO` | V3 | sensor directo | A | `OBSERVED` | no | no | no |
| `HIPÓTESIS` | V3 | conjetura | A | `HYPOTHESIS` | no | no | no |
| `UNRESOLVED` | V3 | evidencia insuficiente | A | `UNKNOWN` | **YES** — colapsa con `UNKNOWN` | **sí** | sí |
| `UNRESOLVED` | V3 | evidencia insuficiente | A | `UNRESOLVED` (nuevo en A) | no | **sí** | sí |
| `NO REPRODUCIBLE` | V3 | histórico no reconstruible | F | `NOT_REPRODUCED` | no | no | no |
| `NO VERIFICADO` | V3 | sin evidencia | A | `NOT_AVAILABLE` | **YES** — «no verificable» ≠ «no disponible» | **sí** | sí |
| `RESOLVED` | V4 | problema resuelto | F | `RESOLVED` | no | no | no |
| `PARTIALLY_RESOLVED` | V4 | problema parcial | F | `PARTIALLY_RESOLVED` | no | **sí** | sí |
| `UNRESOLVED` | V4 | problema abierto | F | `UNRESOLVED` | no | **sí** | sí |
| `OBSOLETE` | V4 | validez temporal | F | `OBSOLETE` | no | no | no |
| `ALREADY_FIXED_UPSTREAM` | V4 | atribución de causa | F | `ALREADY_FIXED_UPSTREAM` | no | no | no |
| `NOT_REPRODUCED` | V4 | no reproducido | F | `NOT_REPRODUCED` | no | no | no |
| `UNKNOWN` | V1/V2 | evidencia insuficiente | A | `UNKNOWN` | no | **sí** | sí |
| `UNKNOWN` | V4 | resultado de problema | F | `UNRESOLVED` | **YES** | **sí** | sí |
| `NOT_AVAILABLE` | V1/V2 | fuente ausente | A | `NOT_AVAILABLE` | no | **sí** | sí |
| `NOT_AVAILABLE` | V4 | resultado de problema | F | `UNRESOLVED` | **YES** | **sí** | sí |
| `FAIL` | V2 | gate falló | E | `BLOCK` + resultado `FAIL` | **YES** — mezcla gate y resultado | **sí** | sí |
| `DEFERRED` | V2 | no hecho, requiere autorización | D | `DEFERRED` | no | **sí** | sí |
| `PASS` | (no declarado) | resultado favorable | — | resultado `PASS`; gate `ALLOW` | **YES** — sin dimensión de origen | **sí** | sí |
| `DERIVED` | V1 | derivado | A | `DERIVED` | no | no | no |
| `REJECTED` | V1 | no admisible | A | `REJECTED` | no | no | no |

**17 de 26 filas requieren revisión manual.** Ninguna se ha aplicado.

## 6. PÉRDIDA DE INFORMACIÓN (PASO 6)

Cinco pérdidas confirmadas. Ninguna conversión automática:

1. **`VERIFICADO` → V1: sin destino.** El término más usado del proyecto (329/47) no existe en
   V1. Convertirlo a `OBSERVED` **degradaría** 329 afirmaciones.requiere añadir `VERIFIED`.
2. **`REPRODUCIBLE` → sin destino.** 62 usos de «fuerza de repetición» no tienen término en V1.
3. **`DOCUMENTADO` → `SUPPORTED` sería una mejora falsa.** `SUPPORTED` implica evidencia que
   respalda; `DOCUMENTADO` es solo texto de fuente. **Prohibido** mapear así.
4. **`NO VERIFICADO` → `NOT_AVAILABLE` es incorrecto.** «No verificable» ≠ «no disponible»:
   una fuente puede existir y no ser verificable. 47 usos en riesgo.
5. **`UNRESOLVED` (V3) y `UNRESOLVED` (V4) son el mismo string en dos dimensiones.** Cualquier
   traducción automática colapsa una dimensión. **Requiere decisión editorial por instancia.**

## 7. LO QUE ESTO NO RESUELVE

- **No cierra MIG-05** («cinco» contradicciones que son seis): es un defecto de conteo, no de
  vocabulario.
- **No toca los 1577 registros.** Cero migrados.
- **No define `CONFIDENCE`** (dimensión G), que hoy solo existe como campo libre.
- **No reconcilia V3 (`NOTEBOOKLM`)** con el repo: sigue siendo un árbol externo (MIG-08).
- **No decide cuál vocabulario es el correcto.** Eso requiere tu decisión, no la derivo.

```
MIG-07=VERIFYING
RECORDS_MIGRATED=0
INVENTORY_COMPLETE=YES
DIMENSIONS_SEPARATED=YES
MAPPING_COMPLETE=YES (26 filas, 17 con REQUIRES_MANUAL_REVIEW)
SILENT_LOSS=0
CONFLICTS_REGISTERED=9
INDEPENDENT_REVIEW=PENDING
CLOSURE_CRITERIA_MET=5/7   -> falla 6 (revisión independiente) y 7 (contradicciones explícitas)
IMPLEMENTATION=NOT_EXECUTED
```
