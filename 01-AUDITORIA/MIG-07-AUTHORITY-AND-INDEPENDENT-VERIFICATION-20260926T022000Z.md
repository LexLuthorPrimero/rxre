# MIG-07 — AUDITORÍA DE AUTORIDAD Y VERIFICACIÓN INDEPENDIENTE

> Artefacto nuevo de auditoría. No modifica ningún documento previo.
> **No implementa E-6. No modifica V6. No migra ni renombra ningún término.**

```
DOCUMENT_ID=MIG-07-AUTHORITY-AND-INDEPENDENT-VERIFICATION
CREATED_UTC=2026-09-26T02:20:00Z
TYPE=AUTHORITY_AUDIT
E1_RESULT=AUTHORITY_CONFLICT
E6_RESULT=DIMENSION_REQUIRED_NOT_IMPLEMENTED
MIG-07_STATE=VERIFYING
MIGRATIONS_APPLIED=0  TERMS_RENAMED=0  TERMS_REMOVED=0  TERMS_ADDED=0
INDEPENDENT_REVIEW=NOT_PERFORMED
IMPLEMENTATION=NOT_EXECUTED
```

**Clasificación usada:** `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `CONFLICT`
`VERIFIED` no se usa como categoría. `PASS` no se usa como categoría. `CONFIRMED` solo en los cuatro resultados formales de E-1.

---

## 1. ESTADO

| Eje | Estado | Clasificación |
|---|---|---|
| E-1 (autoridad) | **`AUTHORITY_CONFLICT`** | `CONFLICT` |
| E-6 (verificación independiente) | **`DIMENSION_REQUIRED_NOT_IMPLEMENTED`** | `SUPPORTED` |
| MIG-07 | `VERIFYING` | — |

E-1 **no** resulta `AUTHORITY_CONFIRMED`. Falla 4 de las 5 condiciones exigidas (§9).
E-6 **no** se implementa. Este documento solo determina si la dimensión es necesaria.

---

## 2. OBJETIVO

Determinar si `00-INDICE/ESTADOS-ES-EN.md` (V6) es la autoridad normativa del vocabulario de
estados, y si la dimensión J (verificación independiente) necesita representación propia.
Sin modificar nada.

---

## 3. CORPUS

| Ítem | Valor |
|---|---|
| Ficheros versionados (`.md .json .tsv .txt` + no versionados de `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/`) | 1128+ |
| Diagramas de `00-INDICE/DIAGRAMAS/` inspeccionados | 16 |
| Documentos normativos leídos íntegros | `AGENTS.md`, `ESTADOS-ES-EN.md`, `09-ESTADOS-CIENTIFICOS.md`, `DIAGRAMAS/README.md`, `DECISIONES-D1-D10.md`, `DOCUMENTARY-RECONCILIATION-2026-09-25.md`, `DOCUMENTATION-ROUTER.md`, `DOCUMENTATION-CENSUS.md`, `REPARATION-PLAN.md`, `PROJECT-DOCUMENTATION-STATUS.md` |
| Muestra estratificada de V6 | 26 términos, 5 estratos |
| Modificaciones al corpus | **0** |

**Métodos de descubrimiento (3, independientes, porrequirement):**

| # | Método | Resultado bruto |
|---|---|---|
| 1 | Búsqueda literal de 16 patrones de autoridad (EN+ES) | 19 `SOURCE_OF_TRUTH` / 17 ficheros; 19 `CANONICAL`; 18 `AUTORIDAD/AUTHORITY`; 1 `VOCAB_CANONICO`; 0 `DEFINICION_OFICIAL` |
| 2 | Inspección de normativos y referencias cruzadas | 3 declaraciones de autoridad ordenadas + 1 taxonomía `SOURCE_OF_TRUTH` propia |
| 3 | Muestreo directo del corpus contra los 26 términos de V6 | 25/26 en uso; 1 con 0 usos; 3 usados y no definidos |

**Los tres métodos producen conteos brutos distintos. No es `CONFLICT`: es una diferencia de
unidad.** Método 1 cuenta *ocurrencias de la cadena* (19); método 2 cuenta *declaraciones
estructuradas* (14 bloques de diagrama); método 3 cuenta *términos*. Reconciliación:
`14` bloques de diagrama + `1` plantilla (`DIAGRAMAS/README.md:147`) + `3` variantes
(`DOCUMENTARY-RECONCILIATION:192-194`) + `1` comentario de código (`collector.py:1891`) = **19**.
**Los tres métodos reconcilian exactamente.** `OBSERVED`.

---

## 4. INVENTARIO DE AUTORIDADES

### 4.1 Declaraciones explícitas

| # | Artefacto | Ubicación | Declara | Aplica a | Invoca autoridad superior | Vigencia | Evidencia que la respalda |
|---|---|---|---|---|---|---|---|
| **A1** | `AGENTS.md` | `:9-19` | `Canonical navigation and state:` + lista de 7 documentos | navegación y estado del proyecto | ninguna | vigente, V2 | — |
| **A2** | `AGENTS.md` | `:21-24` | `MASTER-RESEARCH-STATUS.md` es **navegación histórica**, «does not hold the current state» | estado actual | contradice A3 | vigente | — |
| **A3** | `00-INDICE/DIAGRAMAS/README.md` | `:21-27` | «La autoridad documental es, en este orden»: 1) `MASTER-RESEARCH-STATUS.md` + addendas vigentes, 2) resultados canónicos, 3) `MASTER-PLAN`/roadmap/seguridad, 4) auditorías y readiness **para clasificaciones**, 5) staging/hipótesis, 6) snapshots | autoridad documental general | ninguna | **`DRAFT/CONFLICT`** | — |
| **A4** | `DIAGRAMAS/README.md` | `:29` | «Un diagrama es una **vista derivada**… el texto canónico prevalece» | prevalencia | — | `DRAFT/CONFLICT` | — |
| **A5** | `09-ESTADOS-CIENTIFICOS.md` | `:5-10` | `SOURCE_OF_TRUTH: 00-INDICE/ESTADOS-ES-EN.md` (+4) | contenido de **ese diagrama** | V6 | **`DRAFT/CONFLICT`** | — |
| **A6** | `13-REGLA-FUNDAMENTAL.md` | `:6` | `SOURCE_OF_TRUTH: DIAGRAMAS/README.md` + `ESTADOS-ES-EN.md` + 3 | contenido de ese diagrama | V6, A3 | **`DRAFT`** | — |
| **A7** | `01-AUDITORIA/REPARATION-PLAN.md` | `:183` (N8) | «Vocabulario canónico» para la tabla ES/EN que iría en `00-INDICE/` | vocabulario de estados | — | plan, condición: «Los 8 requieren **autorización explícita de creación**» (`:185`) | — |
| **A8** | `DOCUMENTATION-ROUTER.md` | `:267` | `VOCABULARY` → `PRIMARY: AGENTS.md §Evidence vocabulary` · `SECONDARY: 00-INDICE/ESTADOS-ES-EN.md` · `ESCALATION: REVIEW_REQUIRED (dos vocabularios)` | **vocabulario** | A1 | vigente, y `AGENTS.md` lo designa «START HERE for any documentation question» | — |
| **A9** | `DOCUMENTATION-CENSUS.md` | `:92` | clasifica `ESTADOS-ES-EN.md` como **`REFERENCE`** (junto a `AGENTS.md` e `IMPLEMENTATION-SAFETY-RULES.md`) | taxonomía del censo | — | vigente, congelado | — |
| **A10** | `PROBLEM-STATUS-FINAL.md` | `:6` | `Fuente de observación: FINAL-VALIDATION-20260925T135831Z.json` | su columna `Estado` | ninguna | vigente | — |
| **A11** | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `:192-194` | `SOURCE_OF_TRUTH_CURRENT` / `_HISTORICAL` / `_DERIVED` (3 valores) | taxonomía propia | — | vigente | — |
| **A12** | `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | `§0` | «Convenciones de ESTADO» de 12 términos + «La taxonomía completa está en `ESTADOS-ES-EN.md`» | convenciones de estado | **V6** | vigente | — |
| **A13** | `DECISIONES-D1-D10.md` | `:32` (D6) | `Estado canónico R-4B` = `INCONCLUSO/INCONCLUSIVE`; «**no elevar a SUPPORTED**» | estado de R-4B | — | `✅ ADOPTADA` | — |

### 4.2 Patrón de `SOURCE_OF_TRUTH` en los 14 diagramas (aristas del grafo)

| Destino | nº diagramas |
|---|---:|
| `00-INDICE/MASTER-RESEARCH-STATUS.md` | **8** |
| `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md` | **8** |
| `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` | **8** |
| `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` | 6 |
| `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | 6 |
| `IMPLEMENTATION-READINESS-AUDIT.md` | 5 |
| `MASTER-PLAN.md` / `IMPLEMENTATION-ROADMAP.md` | 3 / 3 |
| **`00-INDICE/ESTADOS-ES-EN.md`** | **2** |
| `R1-6-EVIDENCE-STATE-MODEL.md` | 2 |
| otros (21 destinos únicos más) | 1–2 |

**V6 es la `SOURCE_OF_TRUTH` de 2 de 14 diagramas.** `MASTER-RESEARCH-STATUS.md` lo es de 8. `OBSERVED`.

---

## 5. GRAFO DE AUTORIDAD

Cada arista está respaldada por una referencia literal.

```
AGENTS.md ──── A1/A2 ──► PROBLEM-STATUS-FINAL.md (V4)
    │                        └──► FINAL-VALIDATION-20260925T135831Z.json  [A10]
    │                        └──► HOST-B. Sin SOURCE_OF_TRUTH propio.
    ├── A2: "MASTER-RESEARCH-STATUS does not hold current state"
    │                    ✗✗ CONTRADICE A3
    │
DIAGRAMAS/README.md ── A3 ──► (1) MASTER-RESEARCH-STATUS.md
    │  [DRAFT/CONFLICT]        (2) resultados canónicos
    │  A4: "diagrama = vista derivada"  (3) MASTER-PLAN / roadmap / seguridad
    │                                  (4) auditorías/readiness PARA CLASIFICACIONES
    │                                  (5) staging/hipótesis   (6) snapshots
    │
13-REGLA-FUNDAMENTAL ──A6──► DIAGRAMAS/README.md + ESTADOS-ES-EN.md      [DRAFT]
09-ESTADOS-CIENTIFICOS ─A5─► ESTADOS-ES-EN.md + R1-6 + READINESS + MRS + R4B  [DRAFT/CONFLICT]
                                                        │
PROJECT-DOCUMENTATION-STATUS ─A12──────────────────────┘  [declara a V6 autoridad]
                                                        │
                                        ESTADOS-ES-EN.md (V6)
                                        · sin STATUS / DIAGRAM_ID / SOURCE_OF_TRUTH
                                        · sin SHA256
                                        · no declarado en ninguna lista de AGENTS.md
REPARATION-PLAN N8 ──A7──► "Vocabulario canónico" (propuesto, requería autorización)
DOCUMENTATION-ROUTER ─A8──► VOCABULARY: PRIMARY=AGENTS.md, SECONDARY=V6,
                              ESCALATION=REVIEW_REQUIRED (dos vocabularios)   ✗ CONFLICT
DOCUMENTATION-CENSUS ─A9─► ESTADOS-ES-EN.md clasificado REFERENCE             ✗ CONFLICT
```

**No hay arista que Apunte *hacia* V6 desde un documento vigente y no-DRAFT.** Las dos únicas
aristas entrantes (A5, A6) vienen de diagramas `DRAFT`/`DRAFT/CONFLICT`, y A4 —la regla del
propio directorio de diagramas— dice que un diagrama es vista derivada y el texto canónico
prevalece. `OBSERVED`.

---

## 6. AUDITORÍA DE V6 (`00-INDICE/ESTADOS-ES-EN.md`)

Hash `c858b5ae7aaa7086…` · mtime `2026-09-25 11:16` · 42 términos (26 filas ES+EN) · sin bloque de gobernanza.

### 6.1 Fortalezas — `OBSERVED`

1. Único vocabulario con columna **«Regla de uso»** por término. Ninguno de los otros 6 lo tiene.
2. Reglas normativas que no existen en ningún otro sitio: «`EJECUTADO` no significa `VALIDADO`»,
   «`VALIDADO` no significa `SUPPORTED` si el protocolo no lo permite», «`UNKNOWN` no se
   convierte en resultado negativo por reiteración documental», «No promover a `SUPPORTED`».
3. Introduce el eje M (elegibilidad): `DIAGNOSTIC ONLY`, `THERMALLY CONFOUNDED`, `NOT FOR VERDICT`.
4. 25 de 26 términos tienen uso real en el corpus.

### 6.2 Defectos materiales — `OBSERVED`

| # | Defecto | Evidencia | Gravedad |
|---|---|---|---|
| **V6-D1** | **No es autocontenido.** Su §«Regla de evidencia» usa `SUPPORTED`, que **V6 no define**. Su autoridad depende de una definición externa (V1/V2, `AGENTS.md`) | el término aparece en 2 reglas; 0 filas definiéndolo | **ALTA** |
| **V6-D2** | **`DIAGNOSTIC ONLY` tiene 0 usos en todo el corpus.** La forma realmente usada es `DIAGNOSTIC` (21 usos / 7 ficheros), que V6 **no define** | barrido exacto | **ALTA** |
| **V6-D3** | **V6 no declara su propio estado.** 0 ocurrencias de `STATUS:`, `DIAGRAM_ID:`, `SOURCE_OF_TRUTH`, `LAST AUDITED`. No puede ser `DRAFT` ni `LIVE`: no tiene ciclo de vida | recuento | ALTA |
| **V6-D4** | **V6 no tiene hash.** Un documento propuesto como autoridad de vocabulario sin hash de integridad | `SHA256` = 0 ocurrencias | ALTA |
| **V6-D5** | **V7 la declara provisional; V6 no se declara tal.** Asimetría: la caracterización de vigencia es externa | V7`:14` «sigue siendo provisional» vs V6, que solo usa «provisional» al definir `DRAFT` | MEDIA |
| **V6-D6** | **3 términos en uso que V6 no define:** `DOCUMENTED`, `SUPPORTED`, `INCONCLUSIVE` aparecen en `00-MAESTRO-PROYECTO.md` junto a 6 términos de V6. La tabla está **re-renderizada de forma parcial y divergente** en un diagrama `DRAFT/CONFLICT` | solape 6/27; 3 solo-en-diagrama | ALTA |
| **V6-D7** | **No está en la lista de autoridad ordenada** de `DIAGRAMAS/README.md` (A3), ni en la de `AGENTS.md` (A1) | conteo: 0 menciones en `AGENTS.md` | ALTA |
| **V6-D8** | **Su creación requería autorización explícita** (N8) y no hay registro de que se autorizara | `REPARATION-PLAN.md:185` | MEDIA |

### 6.3 Muestreo estratificado de conformidad

| Estrato | Término | Usos | Fich. | Conformidad con la regla V6 | Clasificación |
|---|---|---:|---:|---|---|
| gate crítico | `EJECUTADO` | 22 | 10 | conforme — usado junto a `DOCUMENTADO ≠ EJECUTADO` | `OBSERVED` |
| gate crítico | `AUTORIZADO` | 20 | 13 | conforme — `DISEÑADO ≠ AUTORIZADO ≠ VALIDADO` | `OBSERVED` |
| gate crítico | `CONFLICT` | 172 | 38 | **contradice su propia regla**: V6 dice «el texto canónico prevalece», pero 172 usos incluyen `STATUS: DRAFT/CONFLICT` de 14 diagramas que **no** son texto canónico | `CONFLICT` |
| gate crítico | `REQUIRES AUTHORIZATION` | 13 | 10 | conforme | `OBSERVED` |
| frecuente | `DRAFT` | 81 | 23 | conforme | `OBSERVED` |
| frecuente | `LIVE` | 16 | 5 | **parcial**: la conversión a `LIVE` está bloqueada en 3 documentos; el término se usa como objetivo, no como estado | `PLAUSIBLE` |
| ambiguo | `PARTIALLY VERIFIED` | 22 | 11 | conforme a la regla («indicar siempre el alcance probado») | `OBSERVED` |
| ambiguo | `HISTÓRICO` | 42 | 22 | conforme | `OBSERVED` |
| ambiguo | `CONGELADO` | 29 | 13 | conforme | `OBSERVED` |
| ambiguo | `PERDIDO` | 77 | 11 | conforme | `OBSERVED` |
| ambiguo | `SNAPSHOT` | 26 | 15 | conforme | `OBSERVED` |
| colisionado | `EXISTE` | 44 | 5 | conforme | `OBSERVED` |
| colisionado | `IDEA` | 104 | 51 | conforme | `OBSERVED` |
| colisionado | `DESCONOCIDO` | 29 | 15 | conforme | `OBSERVED` |
| colisionado | `PLANIFICADO` | 7 | 5 | conforme | `OBSERVED` |
| raro | `REQUIRES CAPABILITY AUDIT` | 31 | 15 | conforme | `OBSERVED` |
| raro | `THERMALLY CONFOUNDED` | 22 | 7 | conforme | `OBSERVED` |
| raro | `NOT FOR VERDICT` | 24 | 9 | conforme | `OBSERVED` |
| raro | `NO IMPLEMENTADO` | 1 | 1 | conforme | `OBSERVED` |
| raro | **`DIAGNOSTIC ONLY`** | **0** | **0** | **NO CONFORME — término nunca usado; la regla apunta a un string inexistente** | `CONFLICT` |
| **def. V6-D1** | **`SUPPORTED`** | — | — | **NO CONFORME — usado en las reglas de V6, no definido por V6** | `CONFLICT` |
| **def. V6-D6** | **`DOCUMENTED`** | — | — | **NO CONFORME — usado junto a términos V6, no definido por V6** | `CONFLICT` |

**Resultado: 19/22 conformes, 3 no conformes.** 2 de esas 3Conformidades no son de uso sino de
autorreferencia: **V6 viola su propia existencia como vocabulario cerrado**. `OBSERVED`.

---

## 7. ANÁLISIS DE V4 (`PROBLEM-STATUS-FINAL.md`)

| Pregunta | Respuesta | Evidencia | Clasificación |
|---|---|---|---|
| ¿Declara autoridad propia? | **No** | no contiene `SOURCE_OF_TRUTH`, `AUTORIDAD` ni `canónico` en sentido normativo | `OBSERVED` |
| ¿Declara su fuente? | **Sí** | `Fuente de observación: FINAL-VALIDATION-20260925T135831Z.json` (`:6`) | `OBSERVED` |
| ¿Es independiente o derivada? | **Derivada** | una sola captura; sin `SOURCE_OF_TRUTH`; ausente de la lista de V7; ausente de V6 | `SUPPORTED` |
| ¿Autoridad sobre su columna `Estado`? | **Limitada a esa captura** | su alcance está delimitado por su frase de límite: «`NOT_REPRODUCED` significa que el síntoma no apareció en la comprobación actual; no significa que su causa histórica esté resuelta» | `SUPPORTED` |
| ¿Y el JSON? | **Autoridad sólo sobre su captura** | `FINAL-VALIDATION-20260925T135831Z.json` es un artefacto de medición HOST-B. No declara autoridad semántica | `OBSERVED` |
| ¿Y el `JSON` histórico como `SOURCE_OF_TRUTH_CURRENT`? | **Taxonomía distinta** | `DOCUMENTARY-RECONCILIATION:192` usa `CURRENT`/`HISTORICAL`/`DERIVED`, eje de **vigencia**, no de **semántica** | `OBSERVED` |

**V4 es un conflicto menor adicional**: es el documento que `AGENTS.md` (A1) nombra
«current problem matrix» — el único mecanismo operativo de agente — y está anclado a HOST-B
(MIG-03), mientras el host vivo es HOST-C. `CONFLICT`.

---

## 8. ANÁLISIS DEL DOCUMENTO `DRAFT/CONFLICT` (V7)

| Pregunta | Respuesta | Evidencia | Clasificación |
|---|---|---|---|
| ¿Qué autoridad declara? | `SOURCE_OF_TRUTH`: V6, R1-6, READINESS-AUDIT, MASTER-RESEARCH-STATUS, EXP-F4-A-v2.3 — **en ese orden**, V6 primero | `:5-10` | `OBSERVED` |
| ¿Por qué `DRAFT`? | «esta state machine es provisional. No autoriza una ejecución ni convierte un estado diagnóstico en `VALIDATED`» | `:20` | `OBSERVED` |
| ¿Por qué `CONFLICT`? | Declara **3 conflictos propios**: (1) la taxonomía «sigue siendo provisional y no cubre necesariamente cada etiqueta histórica»; (2) «aún no ha sido reauditado contra todos los documentos heredados»; (3) «la conversión a `LIVE` queda bloqueada hasta resolver H12/capabilities» | `:11-19` | `OBSERVED` |
| ¿Contradice a V6? | **No por contenido, sí por estatus.** V7 añade estados que V6 no contiene (`NEW_HYPOTHESIS`, `PRESERVE_EVIDENCE`, `NO_AUTHORIZED`, `FROZEN`) y V6 no los contiene | comparación de tablas | `SUPPORTED` |
| ¿Es versión histórica? | **No.** Es la única máquina de estados con transiciones; V6 es una tabla de equivalencias, no un grafo. Son **complementarios**, no_versions | análisis estructural | `SUPPORTED` |
| ¿Contiene información que V6 no contiene? | **Sí**: el grafo de transiciones, las 4 salidas de `EXECUTED` (`INCONCLUSIVE`, `PARADA_D`, `THERMALLY_CONFOUNDED`, `NOT_FOR_VERDICT`) y `NEW_HYPOTHESIS` | `:22+` | `OBSERVED` |

**Punto decisivo:** V7 es `DRAFT/CONFLICT` **y su propio conflicto #1 dice que V6 es
provisional**. Es decir: **la declaración que pretendeu fundar la autoridad de V6 está ella
misma en estado de conflicto y describe a V6 como provisional.** `CONFLICT`.

Por A4, un diagrama es vista derivada. **Una vista derivada `DRAFT/CONFLICT` no puede ser la
base de una autoridad normativa.** `SUPPORTED`.

---

## 9. RESULTADO E-1

# `AUTHORITY_CONFLICT`

### 9.1 Contraste con las condiciones de `AUTHORITY_CONFIRMED`

| # | Condición exigida | Estado | Motivo |
|---:|---|---|---|
| 1 | declaración explícita | **PARCIAL** | 2 de 14 diagramas; ausente de A1 y de A3; 0 menciones en `AGENTS.md` |
| 2 | ausencia de autoridad contradictoria vigente | **FALLA** | A8 `REVIEW_REQUIRED (dos vocabularios)`; A9 clasifica V6 como `REFERENCE`; A1 designa `AGENTS.md §Evidence vocabulary` como `PRIMARY`; A2 contradice A3 |
| 3 | cadena de referencia demostrable | **FALLA** | aristas entrantes solo desde `DRAFT`/`DRAFT/CONFLICT`; V6 sin hash, sin `DIAGRAM_ID`, sin `SOURCE_OF_TRUTH` (V6-D3, V6-D4) |
| 4 | coherencia con los documentos normativos | **FALLA** | V6-D1 usa `SUPPORTED` sin definirlo; V6-D2 `DIAGNOSTIC ONLY` con 0 usos; V6-D6 3 términos usados y no definidos |
| 5 | ausencia de contradicción material no resuelta | **FALLA** | A7 (N8) exigía autorización explícita y no hay registro; V6-D5 V7 la llama provisional y V6 no |

**4 de 5 condiciones fallan. `AUTHORITY_CONFIRMED` queda descartado.**

### 9.2 Por qué no `AUTHORITY_HISTORICAL_ONLY`

V6 está en uso activo: `PROJECT-DOCUMENTATION-STATUS §0` remite a él, 25 de sus 26 términos se
usan, 2 diagramas lo nombran. No es histórico. `OBSERVED`.

### 9.3 Por qué no `AUTHORITY_NOT_DEMONSTRATED`

Porque **existen** dos designaciones de autoridad, ambas explícitas y ambas vigentes
(A7 «Vocabulario canónico»; A12 «La taxonomía completa está en `ESTADOS-ES-EN.md»`). No falta
demostración: **hay dos autoridades que se contradicen y el router ya lo registró como
`REVIEW_REQUIRED`**. Eso es exactamente `CONFLICT`, no `NOT_DEMONSTRATED`. `SUPPORTED`.

### 9.4 Evidencia a favor de V6

1. Único con columna «Regla de uso». `OBSERVED`
2. Reglas normativas ausentes en los otros 6 vocabularios. `OBSERVED`
3. Designado por A7 (N8), A12, A5, A6 — 4 referencias. `OBSERVED`
4. Único que introduce el eje M (elegibilidad de evidencia). `OBSERVED`
5. 25/26 términos en uso real. `OBSERVED`
6. Complementa a V7 con la columna ES/EN que V7 no tiene. `SUPPORTED`

### 9.5 Evidencia en contra

1. A8: el router lo marca `REVIEW_REQUIRED (dos vocabularios)`. `OBSERVED`
2. A9: el censo lo clasifica `REFERENCE`, no normativo. `OBSERVED`
3. 0 menciones en `AGENTS.md`, el único mecanismo operativo. `OBSERVED`
4. Ausente del orden de autoridad A3. `OBSERVED`
5. 2 de 14 diagramas, ambos `DRAFT`/`DRAFT/CONFLICT`. `OBSERVED`
6. Sin `STATUS`, sin hash, sin `DIAGRAM_ID`. `OBSERVED`
7. V7 la llama provisional; V6 no. `CONFLICT`
8. Se contradice a sí misma: usa `SUPPORTED` sin definirlo; `DIAGNOSTIC ONLY` nunca usado. `CONFLICT`
9. Su tabla está re-renderizada parcialmente en un diagrama `DRAFT/CONFLICT` con 3 términos que V6 no define. `CONFLICT`
10. A2 contradice a A3 sobre `MASTER-RESEARCH-STATUS.md`, y ese documento es `SOURCE_OF_TRUTH` de 8 diagramas. `CONFLICT`

### 9.6 Contraejemplos

| # | Contraejemplo | Refuta |
|---|---|---|
| **CE-1** | El router —designado por `AGENTS.md` como «START HERE for any documentation question»— marca `VOCABULARY` como `REVIEW_REQUIRED (dos vocabularios)`. **La contradicción no la descubrí yo: está registrada** | «hay una autoridad clara» |
| **CE-2** | `AGENTS.md` declara `MASTER-RESEARCH-STATUS.md` no autoritativo; `DIAGRAMAS/README.md` lo pone #1 en autoridad; 8 diagramas lo nombran. **A2 contradice a A3** | «la cadena de autoridad es coherente» |
| **CE-3** | V6 usa `SUPPORTED` en sus propias reglas sin definirlo. **No es autocontenido** | «V6 es un vocabulario cerrado y normativo» |
| **CE-4** | `DIAGNOSTIC ONLY`: 0 usos. `DIAGNOSTIC`: 21 usos, no definido. **La regla de V6 apunta a un string inexistente** | «V6 refleja el uso real» |
| **CE-5** | `REPAIR-PLAN` N8: «requieren autorización explícita de creación». No hay registro de autorización de N8 | «V6 se creó legítimamente» |
| **CE-6** | El censo (§133, ya antes de esta fase) detectó que «`AGENTS.md` declara 7 documentos "canonical"; **el estado real está en otros 4 de la raíz**» | «las declaraciones canónicas del proyecto son fiables» |
| **CE-7** | 138 de 360 entradas del staging están en `D`/`M` y 2 son `AM`: hay trabajo no consolidado. `MASTER-RESEARCH-STATUS.md` es la `SOURCE_OF_TRUTH` más citada (8) y `AGENTS.md` la degrada | «la autoridad más citada es vigente» |

---

## 10-11. SÍNTESIS DE EVIDENCIA

E-1 se resuelve en `AUTHORITY_CONFLICT` con 7 observaciones a favor y 10 en contra
(§9.4, §9.5), 7 contraejemplos (§9.6) y 4 de 5 condiciones de `AUTHORITY_CONFIRMED` falladas.

**La observación decisiva no es mía: es la fila `VOCABULARY` del router del proyecto**, que ya
registraba el conflicto antes de que MIG-07 existiera. `CONFLICT`.

---

## 12. DIMENSIÓN J — VERIFICACIÓN INDEPENDIENTE

### 12.1 Descubrimiento (6 variantes + mecanismos)

| Patrón | Ocurrencias | Ficheros |
|---|---:|---:|
| `independent review/verification/validation` (EN) | **1** | 1 — y es **negativa**: `LIMITATIONS=[derived analysis, no independent validation, no canonical provenance]` |
| `second reviewer` / `reviewed by another` (EN) | **0** | 0 |
| `revisión independiente` / `revisor independiente` (ES) | **0** | 0 |
| `verificación independiente` (ES) | **0** | 0 |
| `cross-check` (EN) | **13** | 12 |
| `otro agente` / `independent agent` | **5** | 3 |
| `permisos independientes` / `independent permissions` | **0** | 0 |
| `muestreo` (como revisión) | 66, **casi todos falsos positivos** — `muestreo` = muestra de mediciones, no muestreo de revisión | 38 |
| `NON_AUTHORITATIVE_REASON` | **8** | 1 |

> Nota de alcance: el barrido se hizo sobre ficheros versionados, por lo que **excluye los
> documentos MIG-07 que yo escribí** (untracked). 0 en español refleja el estado del proyecto
> antes de esta fase. `OBSERVED`.

### 12.2 ¿El proyecto diferencia A–F? (los seis niveles que pide el encargo)

| Nivel | ¿Existe? | Evidencia | Clasificación |
|---|---|---|---|
| **A** afirmación comprobada por el propio autor | **Sí** | implícito en todo el proyecto | `OBSERVED` |
| **B** afirmación reproducida | **Sí** | `REPRODUCIBLE` / `NO REPRODUCIBLE` (V3), eje H | `OBSERVED` |
| **C** revisada por **otro proceso** | **Parcial** | `cross-check` (13 usos), `otro agente` (4). `RX550_BUILD_SPECIFICATION.txt`: «base para que **otro agente** implemente sin repetir» — es *relevo de autoría*, no revisión | `SUPPORTED` |
| **D** revisada por **otro agente** | **No como estado** | 0 términos. La noción existe atribuida a *implementación*, no a *verificación* | `OBSERVED` |
| **E** revisada por otro agente con **permisos independientes** | **No** | 0 usos de `independent permissions` / `permisos independientes` | `OBSERVED` |
| **F** revisada por **muestreo humano** | **No** | `muestreo` = telemetría | `OBSERVED` |

### 12.3 La información J sí existe, en 3 codificaciones parciales

| # | Codificación | Dónde | Qué codifica | Qué NO codifica |
|---|---|---|---|---|
| **J-a** | `VERIFICADO` | V3 `R1-6`: «fuente primaria/medible **y fue confirmada por cross-check independiente**» | que hubo contraste | **quién contrastó** — la definición la satisface el autor contrastándose a sí mismo |
| **J-b** | `NON_AUTHORITATIVE_REASON` | `DOCUMENTARY-RECONCILIATION` (8 usos), incl. `no independent validation` | que el artefacto no es autoritativo **por no tener validación independiente** | no es un término; es un valor de campo; no es consultable como estado |
| **J-c** | `otro agente` | `RX550_BUILD_SPECIFICATION`, `P0-GATE` | autoría distinta | no es verificación; es atribución o relevo |

**Y un cuarto, inverso:** el router tiene `REVIEW_REQUIRED` («Escalar a revisión editorial») y
`CONFLICT_ID` con `Precedencia declarada`. Existe el **mecanismo** de escalar a revisión
editorial; no existe el **término** del resultado. `OBSERVED`.

---

## 13. ALTERNATIVAS A J

| # | Alternativa | ¿Expresa J? | Qué usa |
|---|---|---|---|
| **ALT-1** | J como sub-condición de `VERIFICADO` (eje A) | **Parcial** | A |
| **ALT-2** | J en provenance (eje L) | **Parcial** | L |
| **ALT-3** | J en `FINDING_STATE` (`VERIFYING`/`CLOSED`) | **No** | B |
| **ALT-4** | J como condición de entrada de un gate (`NO_GO` si no hay revisión) | **Parcial** | E |
| **ALT-5** | J por composición (`X_BY_INDEPENDENT`) | **Parcial** | P (operador `/` no declarado) |
| **ALT-6** | J = dimensión propia | **Sí** | J |

---

## 14. INFORMACIÓN PERDIDA POR CADA ALTERNATIVA

El único hecho no representable es **la independencia de la parte que verifica**.

| Alt | Información perdida | Tipo | Clasificación |
|---|---|---|---|
| **ALT-1** | **Quién verificó.** La definición de V3 la satisface el auto-contraste. Un autor que se contrasta a sí mismo y un revisor independiente producen el **mismo `VERIFICADO`** | identidad del verificador | `SUPPORTED` |
| **ALT-2** | **La independencia en sí.** Provenance registra quién, cuándo, con qué hash — un revisor y un autor generan registros de forma idéntica. `AUTHORITY: AGENTS_MD_OWNERSHIP_CRITERION` del collector es un ejemplo: declara fuente, no independencia | propiedad relacional | `SUPPORTED` |
| **ALT-3** | **El verificador y su independencia.** `VERIFYING` (10 ficheros) significa *verificación pendiente*, no *verificada por otro*. `CLOSED` no exige revisor | identidad + independencia | `SUPPORTED` |
| **ALT-4** | **Granularidad.** El gate registra «revisado» en la rama, no por afirmación. Y el gate no se ejecutó: `GO_C1=NOT_AVAILABLE` en 20+ ficheros | granularidad | `SUPPORTED` |
| **ALT-5** | **Todo.** Al no haber dimensión P declarada ni autorizar composición (§12 del modelo semántico), el término se crea ad hoc por artefacto | previsibilidad | `SUPPORTED` |

**Intento de refutar la necesidad de J (como exige el encargo):** las cinco alternativas pueden
expresan J parcialmente. **Ninguna lo expresa por completo, y la pérdida no es cosmética:**
es exactamente la propiedad que habría detectado RC-4 — un autor que verifica su propio
trabajo. `SUPPORTED`.

**Pero la dimensión debe ser estrecha.** El análisis NO justifica una máquina de estados de
revisión completa. Lo único no representable es la independencia del verificador. Cualquier
propuesta mayor sería Conveniencia, no necesidad. `SUPPORTED`.

---

## 15. RESULTADO PROVISIONAL E-6

# `DIMENSION_REQUIRED_NOT_IMPLEMENTED`

- **¿J existe como concepto?** **Sí, parcialmente**, en 3 codificaciones (J-a, J-b, J-c).
  `SUPPORTED`
- **¿Existe como dimensión?** **No.** 0 términos en ES, 1 uso negativo en EN. `OBSERVED`
- **¿Necesita dimensión propia?** **Sí, para el hecho único**: la independencia del verificador.
  Ninguna de las 5 alternativas lo representa. `SUPPORTED`
- **¿Se implementa?** **NO.** Requisitos previos: resolver E-1 y cerrar la revisión independiente
  del modelo semántico.

**Definición propuesta** (no canónica, no implementada):

> **J · INDEPENDENT_VERIFICATION** — propiedad de una afirmación que registra **quién la
> verificó y con qué independencia respecto de quien la produjo**.

- **NO significa**: calidad de la evidencia, ni fuerza de la clasificación, ni que el resultado
  sea correcto, ni autorización, ni `ALLOW`/`BLOCK` de un gate.
- **Qué evidencia la activa**: la existencia de un artefacto de revisión producido por una
  entidad distinta de la autora de la afirmación, con identificador de esa entidad.
- **Qué evidencia NO basta**: el auto-contraste del autor; una segunda ejecución idéntica
  (eso es H, reproducibilidad); un `cross-check` sin entidad identificable; la mera existencia
  de un segundo fichero.
- **Estados posibles** (ninguno implementado): `NOT_REQUESTED` · `REQUESTED` · `SELF_CHECKED`
  · `INDEPENDENTLY_REVIEWED` · `DISPUTED` · `NOT_AVAILABLE`.
- **Relación con A**: ortogonal. Una afirmación puede ser `OBSERVED` y no revisada, o
  `PARTIALLY VERIFIED` y revisada — ninguna combinación se deriva de la otra.
- **Relación con H**: ortogonal. `REPRODUCIBLE` dice que se repite; J dice quién lo revisó.
- **Relación con C (investigación)**: `C` no existe (§4 del modelo semántico). J **no crea** C.
- **Relación con gates**: E usa `GO`/`NO_GO`/`ABORT`. J sería una **condición de entrada** de
  `GO`, no un estado de gate. Un `NO_GO` por falta de revisión no sería un hallazgo: sería una
  precondición. `PLAUSIBLE`
- **Relación con provenance (L)**: J se apoya en L (quién), y añade la relación
  `verificador ≠ autor` que L no expresa. `SUPPORTED`

**Nota sobre la nomenclatura:** `VERIFY_INDEPENDENT` **no** es término canónico. Se usa aquí
solo como identificador provisional de la dimensión analizada, según lo indicado.

---

## 16. DECISIONES QUE SIGUEN ABIERTAS

| # | Decisión | Precedida por | Impacto |
|---|---|---|---|
| **E-1** | **Qué vocabulario es canónico** — 2 autoridades que se contradicen, ya marcadas `REVIEW_REQUIRED` por el propio router | esta fase | **BLOQUEANTE** |
| **E-2** | `VERIFIED` VF-7 (`NO. VERIFIED` = descartado) vs VF-1 (afirmación verificada): polaridad invertida | modelo semántico | ALTA |
| **E-3** | `VERIFICADO` y `REPRODUCIBLE` son uno o dos términos | modelo semántico | ALTA |
| **E-4** | `DOCUMENTED` es etapa de madurez o clase de evidencia | modelo semántico | ALTA |
| **E-6** | Crear J, y con qué alcance | esta fase | ALTA |
| **E-7** | La barra `/`: 513 patrones, 5 funciones | modelo semántico | MEDIA |
| **E-8** | Si V6 se promueve, ¿puede pasar a canónico, o se marca `LIVE`? | E-1 | MEDIA |
| **E-9** | V3 (árbol externo) ¿se incorpora al repo? | E-1 | MEDIA |
| **E-10** | `OBSOLETE` y `ALREADY_FIXED_UPSTREAM` a qué eje | modelo semántico | BAJA |
| **E-11** | **NUEVA**: ¿quién resuelve `REVIEW_REQUIRED` del router, y con qué precedencia sobre V6? | CE-1 | **ALTA** |
| **E-12** | **NUEVA**: si V6 no es la autoridad, ¿cuál es? Ninguna de las 6 candidatas cumple las 5 condiciones | §9 | **ALTA** |

---

## 17. CONDICIONES EXACTAS PARA CERRAR MIG-07

| # | Condición | Estado | Objetivo verificable |
|---:|---|---|---|
| 1 | Vocabularios inventariados | **CUMPLE** | 7 fuentes |
| 2 | Dimensiones separadas | **CUMPLE** | 16 (2 inexistentes, 4 no listadas) |
| 3 | Mapping completo | **CUMPLE** | 26 filas + 15 pérdidas |
| 4 | Ambigüedades identificadas | **CUMPLE** | 14 colisiones, 15 compuestos |
| 5 | Sin pérdida silenciosa | **CUMPLE** | 0 migraciones |
| 6 | Revisión independiente | **FALLA** | requiere otro autor |
| 7 | Contradicciones explícitas | **CUMPLE** | SC-1..SC-14 |
| 8 | Autoridad declarada resuelta | **FALLA** | `AUTHORITY_CONFLICT`; E-1, E-11, E-12 abiertas |
| 9 | Dimensiones del encargo validadas | **CUMPLE** | 2 inexistentes confirmadas por 0 usos |
| 10 | Candidatos no colisionan | **FALLA** | 4 de 4 colisionan |
| 11 | **NUEVA**: V6 autocontenido | **FALLA** | V6-D1, V6-D2 |
| 12 | **NUEVA**: V6 con provenance | **FALLA** | V6-D3, V6-D4 |
| 13 | **NUEVA**: conflicto del router resuelto | **FALLA** | E-11 |

**4 de 13.** MIG-07 no puede cerrarse.

---

## 18. NECESIDAD DE REVISIÓN INDEPENDIENTE

**Obligatoria, y no por formalidad.** Esta fase provee tres refutaciones propias (K-7, K-8 y ahora
las de E-1) y las dos últimas fallaron por cobertura, no de razonamiento.

Afirmaciones de este documento que un revisor debe refutar prioritariamente:

1. **`AUTHORITY_CONFLICT`** — y en particular si `AUTHORITY_NOT_DEMONSTRATED` sería más honesto.
2. **Que el router de A8 sea vinculante** — puede ser un artefacto de diseño, no una declaración.
3. **V6-D1/V6-D2** — que V6 no sea autocontenido.
4. **Que 2 de 14 diagramas no baste** para una autoridad.
5. **Que J necesite dimensión** — el argumento es estrecho y puede ser rechazado como
   sobre-ingeniería. La contra-argumentación más fuerte es ALT-4: el gate ya puede exigir
   revisión como precondición, sin vocabulario.
6. **Los 3 estados de V7 que contradicen la provisionalidad de V6** (§8).

**Esta ejecución NO es revisión independiente.** Es análisis, propuesta y autocrítica. La
revisión independiente definitiva la debe realizar otro agente o proceso, y según la
conclusión de la fase anterior debe ser **por muestreo humano sobre los usos**, no por otro
`grep`.

---

## 19. LIMITACIONES DEL ANÁLISIS

1. **El barrido de E-6 excluye mis propios documentos** (untracked). Los 0 usos en español
   reflejan el estado previo a esta fase, no el actual. `OBSERVED`
2. **Los conteos de V6 se hicieron sobre ficheros versionados.** Hay 17 entradas untracked en
   `01-AUDITORIA/` no cubiertas. `OBSERVED`
3. **No se leyó el contenido de las 1321 filas `RAW_EVIDENCE`** del censo: solo se muestrearon
   documentos normativos. Un uso conforme podría existir ahí. `UNKNOWN`
4. **El grafo de autoridad se construyó solo de aristas `SOURCE_OF_TRUTH` explícitas.** Un
   documento podría tener autoridad de facto sin declararla; eso no es detectable por este
   método. `UNKNOWN`
5. **No se pudo determinar si N8 fue autorizado** (V6-D8): no hay registro. `NOT_AVAILABLE`
6. **La clasificación de V6 como `REFERENCE` (A9) proviene del censo**, que es un artefacto
   congelado y no una autoridad normativa. Es evidencia de clasificación, no de autoridad. `PLAUSIBLE`
7. **E-6 no se implementó ni se probó.** La definición propuesta de J no tiene contraejemplo
  -invalidado, pero tampoco instancia que la valide. `UNKNOWN`
8. **El mtime de V6 y V7 es idéntico al segundo** (`11:16:13`), lo que sugiere escritura por
   lote. No se investigó. `UNKNOWN`
9. **Autoría de esta revisión:** la misma que escribió el modelo semántico y encontró K-7/K-8.
   Sesgo conocido, no mitigado. `SUPPORTED`

---

## 20. ESTADO FINAL

```
MIG-07=VERIFYING
E1_RESULT=AUTHORITY_CONFLICT
E6_RESULT=DIMENSION_REQUIRED_NOT_IMPLEMENTED
E6_IMPLEMENTED=0
V6_MODIFIED=NO
VOCABULARY_MIGRATED=0
TERMS_ADDED=0  TERMS_RENAMED=0  TERMS_REMOVED=0
DISCOVERY_METHODS=3  RECONCILED=YES  METHOD_CONFLICTS=0
SELF_REFUTATIONS=3   (K-7, K-8, y las de E-1)
OPEN_EDITORIAL_DECISIONS=12
CLOSURE_CRITERIA_MET=4/13
INDEPENDENT_REVIEW=NOT_PERFORMED
IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

**Conclusión.** La autoridad normativa del vocabulario **no está establecida**, y el conflicto
**no es una inferencia mía**: la fila `VOCABULARY` del `DOCUMENTATION-ROUTER` —el documento que
`AGENTS.md` designa como punto de entrada para toda pregunta documental— ya lo marcaba
`REVIEW_REQUIRED (dos vocabularios)` antes de que MIG-07 existiera. Lo que esta fase añade es
el *porqué*: no es que falte un documento, es que **las dos candidatas fallan condiciones
distintas**. V6 es el mejor redactado y el más usado, pero no es autocontenido, no tiene
provenance, no está en ninguna lista de autoridad vigente, y su único declaration de autoridad
proviene de un diagrama `DRAFT/CONFLICT` que él mismo la describe como provisional.

E-6 queda **determinado y no implementado**. La dimensión J es necesaria, pero su contenido
legítimo es **un solo hecho**: quién verificó y con qué independencia respecto de quién produjo.
Las tres codificaciones parciales que ya existen (`VERIFICADO` con cross-check,
`NON_AUTHORITATIVE_REASON`, `otro agente`) demuestran que el proyecto **ya practice** la
distinción sin nombrarla. Nombrarla es la única acción pendiente; crearla sin resolver antes
E-1 sería construir sobre arena.
