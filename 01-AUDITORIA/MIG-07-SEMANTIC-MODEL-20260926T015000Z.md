# MIG-07 — MODELO SEMÁNTICO PROVISIONAL

> **Artefacto nuevo de auditoría.** No modifica ningún documento previo.
> **No es revisión independiente.** Es análisis técnico, propuesta y autocrítica.
> **Ninguna migración aplicada. Ningún término renombrado, eliminado ni convertido.**

```
DOCUMENT_ID=MIG-07-SEMANTIC-MODEL
CREATED_UTC=2026-09-26T01:50:00Z
TYPE=SEMANTIC_ANALYSIS_AND_PROPOSAL
MIG-07_STATE=VERIFYING
MIGRATIONS_APPLIED=0
TERMS_RENAMED=0
TERMS_REMOVED=0
RECORDS_MODIFIED=0
FILES_MODIFIED_OUTSIDE_01_AUDITORIA=0
INDEPENDENT_REVIEW=NOT_PERFORMED
IMPLEMENTATION=NOT_EXECUTED
```

**Clasificación usada en este documento** (obligatoria, y sin `VERIFIED` como categoría):
`OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `CONFLICT`

---

## 1. RESUMEN EJECUTIVO

El enunciado de MIG-07 habla de **tres** vocabularios. El corpus contiene **siete fuentes
normativas declaradas**. El conteo estaba mal desde el origen y ese error es la razón de que
la primera propuesta de normalización fallara.

| # | Hallazgo | Clasificación |
|---|---|---|
| H-1 | Existen **7 vocabularios** declarados, no 3 | `OBSERVED` |
| H-2 | **Existe una autoridad declarada**: `09-ESTADOS-CIENTIFICOS.md` declara `SOURCE_OF_TRUTH: 00-INDICE/ESTADOS-ES-EN.md` | `OBSERVED` |
| H-3 | V6 (`ESTADOS-ES-EN.md`, 26 términos con *reglas de uso*) es la autoridad; V3 (`R1-6`) es **fuente de** V6, no par | `OBSERVED` |
| H-4 | La autoridad declarada es ella misma `DRAFT/CONFLICT` y se autodescribe como *provisional* | `OBSERVED` |
| H-5 | De las 12 dimensiones del encargo, **2 no existen**: `C` investigación, `J` verificación independiente. **`E` sí existe** — refutación de mi propia afirmación inicial, ver §4-bis | `SUPPORTED` |
| H-6 | Hay **4 dimensiones reales** que el encargo no listó: elegibilidad de evidencia, estimación, validez temporal, composición | `SUPPORTED` |
| H-7 | `VERIFIED` tiene **8 familias** de uso, no 5 | `OBSERVED` |
| H-8 | `DOCUMENTED` pertenece a una **escalera de madurez de 8 etapas**, no al eje de evidencia | `OBSERVED` |
| H-9 | Existe un **operador de composición `/`** con **513 patrones únicos**, no 9, y con 5 funciones distintas, no declarado | `OBSERVED` |
| H-10 | Mi revisión anterior Odyssey tuvo **un error de lectura** sobre `VERIFIED` (§21) | `OBSERVED` |
| H-11 | `REPRODUCIBLE` y `VERIFICADO` **no son excluyentes mutuos** en V3: ambos significan repetición | `SUPPORTED` |
| H-12 | La única traducción segura de `REPRODUCIBLE → REPRODUCIBLE` choca con 21 ficheros de uso no declarado | `OBSERVED` |

**Veredicto:** el modelo no puede cerrarse. Hay decisiones editoriales que ninguna cantidad de
análisis automático puede resolver, y además **dos dimensiones que el encargo pedía no
existen**, lo que invalida la premisa de partida de la lista A–L.

---

## 2. CORPUS ANALIZADO

| Ítem | Valor |
|---|---|
| Ficheros versionados escaneados | 1128 (`.md .json .tsv .py .jsonl .txt .csv`) |
| Método | extracción de contexto literal + agrupación por patrón |
| Árboles externos | `RX550-INVESTIGACION-NOTEBOOKLM/` (V3) — **fuera del repo**, no versionado |
| Ficheros de autoridad leídos íntegros | `AGENTS.md`, `PROBLEM-STATUS-FINAL.md`, `ESTADOS-ES-EN.md`, `09-ESTADOS-CIENTIFICOS.md`, `RX550_BUILD_SPECIFICATION.txt` |
| Modificaciones al corpus | **0** |

---

## 3. LOS 7 VOCABULARIOS IDENTIFICADOS

### V1 — Vocabulario del encargo (aplicado en documentos R1) — 10 términos
`OBSERVED` `SUPPORTED` `DERIVED` `PLAUSIBLE` `HYPOTHESIS` `UNKNOWN` `NOT_AVAILABLE`
`NOT_PROVEN` `REJECTED` `CONFLICT`
Sin fichero de definición. Origen: instrucción textual. `DERIVED`, `NOT_PROVEN`, `REJECTED`
**no declarados** en ninguna fuente del proyecto (0 ocurrencias en `AGENTS.md`).

### V2 — `AGENTS.md` §Evidence vocabulary — 8 términos
`OBSERVED` `SUPPORTED` `PLAUSIBLE` `UNKNOWN` `NOT_AVAILABLE` `CONFLICT` `FAIL` `DEFERRED`
Único con definiciones en inglés. Pero `FAIL` y `DEFERRED` **no son evidencia** (§11).

### V3 — `NOTEBOOKLM/02-R1-6-EVIDENCE-STATE-MODEL.md` — 10 términos
`VERIFICADO` `REPRODUCIBLE` `OBSERVADO` `HIPÓTESIS` `DOCUMENTADO` `PARTIALLY_RECONCILED`
`UNRESOLVED` `CONTRADICTED` `NO REPRODUCIBLE` `NO VERIFICADO`
En español, en árbol externo, **declarado fuente de V6** (H-3).

### V4 — `PROBLEM-STATUS-FINAL.md` §Estado — 8 términos
`RESOLVED` `PARTIALLY_RESOLVED` `UNRESOLVED` `OBSOLETE` `ALREADY_FIXED_UPSTREAM`
`NOT_REPRODUCED` `UNKNOWN` `NOT_AVAILABLE`
Único vocabulario que **declara su fuente de observación**: `FINAL-VALIDATION-20260925T135831Z.json`
— una captura concreta, HOST-B (§10).

### V5 — Clasificador de fase experimental — 12 términos
`VERIFIED` `DERIVED` `ESTIMATED` `UNKNOWN` `REQUIRES FUTURE EXPERIMENT` (declarado literal en
`PRIOR-ART.md`) + `DOCUMENTED` `OBSERVED` `REPRODUCED` `INFERRED` `HYPOTHESIS` `UNVERIFIED`
`CONTRADICTED` (`MASTER-PLAN.md:749`)
Único con **definiciones explícitas** (`FASE-R4A`): `VERIFIED` (leída) / `DERIVED` (aritmética
sobre VERIFIED) / `ESTIMATED` (modelo con supuesto no medible localmente).
Introduce `ESTIMATED`, `REPRODUCED`, `INFERRED` — **inexistentes en V1/V2/V3/V4**.

### V6 — `00-INDICE/ESTADOS-ES-EN.md` — 26 términos ⭐
`EXISTE` `IDEA` `DISEÑADO` `PLANIFICADO` `AUTORIZADO` `EJECUTADO` `INCONCLUSO` `PARADA D`
`DESCONOCIDO` `NO VERIFICABLE` `HISTÓRICO` `SNAPSHOT` `PERDIDO` `NO AUTORIZADO`
`REQUIRES CAPABILITY AUDIT` `REQUIRES EXPERIMENT` `PARTIALLY VERIFIED` `THERMALLY CONFOUNDED`
`DIAGNOSTIC ONLY` `NOT FOR VERDICT` `CONGELADO` `NO IMPLEMENTADO` `DRAFT` `CONFLICT` `LIVE`
`REQUIRES AUTHORIZATION`

**El más normativo del proyecto**: cada término tiene columna «Significado» **y** «Regla de uso».
Ejemplos de reglas que ningún otro vocabulario enuncia: «`EJECUTADO` no significa `VALIDADO`»,
«`VALIDADO` no significa `SUPPORTED` si el protocolo no lo permite», «`UNKNOWN` no se convierte
en resultado negativo por reiteración documental», «No promover a `SUPPORTED`».

### V7 — `00-INDICE/DIAGRAMAS/09-ESTADOS-CIENTIFICOS.md` — máquina de estados
`IDEA` `DESIGNED` `AUTHORIZED` `EXECUTED` `VALIDATED` `INCONCLUSIVE` `NEW_HYPOTHESIS`
`PARADA_D` `PRESERVE_EVIDENCE` `THERMALLY_CONFOUNDED` `DIAGNOSTIC_ONLY` `NOT_FOR_VERDICT`
+ `SNAPSHOT` `CONFLICT` `INCONCLUSIVE` `AUTHORIZATION`
Declara `STATUS: DRAFT/CONFLICT`, `SOURCE_OF_TRUTH: V6, V3, +3`, y **3 conflictos propios**.

---

## 4. DIMENSIONES SEMÁNTICAS REALES ENCONTRADAS

Se evaluaron las 12 dimensiones del encargo. Resultado:

### Dimensiones CONFIRMADAS en el corpus (9)

| Dim | Nombre | Términos propios observados | Fuente que la gobierna |
|---|---|---|---|
| A | `EVIDENCE_CLASSIFICATION` | V1(10) + `VERIFICADO` `OBSERVADO` `HIPÓTESIS` `VERIFIED` `DERIVED` `ESTIMATED` `INFERRED` `REPRODUCED` `UNVERIFIED` `DOCUMENTED` | V2, V3, V5 |
| B | `FINDING_STATE` | `OPEN` `INVESTIGATING` `NOT_CLOSED` `CORRECTED` `VERIFYING` | ⚠ **sin fuente declarada** |
| D | `PHASE_STATE` | `DEFERRED` `NOT_EXECUTED` `PREPARED_FOR_REVIEW` `CONTAMINATED_REQUIRES_ISOLATION` `DEFERRED_NOT_ACCEPTABLE_AS_FULL` | V2 + composición |
| F | `EXPERIMENTAL_RESULT` | `INCONCLUSIVE` `PARADA D` `PASS` `FAIL` `VERDICT` | V6, V7 |
| H | `REPRODUCIBILITY` | `REPRODUCIBLE` `NO REPRODUCIBLE` `REPRODUCED` + «evidencia reproducible» como *condición de transición* en V7 | V3, V5, V7 |
| I | `DOCUMENTATION_LIFECYCLE` | los 26 de V6 + escalera CAPABILITY de 8 etapas | **V6** |
| K | `RECONCILIATION_STATE` | `PARTIALLY_RECONCILED` `CONFLICT` `CONGELADO` `CONTRADICTED` `PARTIALLY_RESOLVED` | V3, V4, V6 |
| L | `PROVENANCE` | `HOST_SCOPE` `RUN_ID` `SHA256` `SOURCE_OF_TRUTH` `DIAGRAM_ID` — **campos**, no vocabulario | transversal |
| G | `CONFIDENCE` | `ALTA`/`MEDIA`/`BAJA` campo libre | ⚠ **sin enumeración canónica** |

### Dimensiones del encargo que NO EXISTEN en el corpus (2) — `SUPPORTED`

| Dim | Encargo pedía | Hallazgo |
|---|---|---|
| **C** | estado de investigación | **No existe.** La investigación se modela como ciclo de vida (`IDEA → DESIGNED → AUTHORIZED → EXECUTED → VALIDATED`) y como retorno a `NEW_HYPOTHESIS`. No hay término de «en curso de investigar». Búsqueda de `IN_PROGRESS`, `IN_INVESTIGATION`, `EN_CURSO`, `INVESTIGATING`, `RESEARCHING`: **0 usos, 0 ficheros.** |
| **J** | estado de verificación independiente | **No existe.** Búsqueda de `INDEPENDENTLY_VERIFIED`, `VERIFIED_BY_*`, `CROSS_CHECKED`, `SECOND_REVIEWER`, `REVIEWED_BY`, `peer_review`: **0 usos, 0 ficheros.** Ningún término codifica «verificado por alguien distinto del autor». Esto es exactamente por lo que RC-4 pudo operar sin ser detectado por el vocabulario. |

### 4-bis. REFUTACIÓN PROPIA: la dimensión **E sí existe** — `OBSERVED`

Escribí primero que `E = estado de gate` no existía. **Es falso**, y la búsqueda lo refutó:
`ALLOW`/`NO_GO`/`GO` dan **19 usos en 5 ficheros**. El gate sí está modelado:

| Término | Evidencia literal | Dimensión |
|---|---|---|
| `GO` / `NO_GO` / `ABORT` | triple declarado en `C1-ISOLATION-DESIGN-v1.0.md` | E |
| `NO_GO` **con regla de uso** | «`NO_GO` nunca significa "intentarlo de nuevo". `ABORT` nunca autoriza una acción» | E |
| `NO_GO_PRE` | ~12 filas de precondición en `C1-ISOLATION-DESIGN-v1.0.md` | E (variante) |
| `GO_C1` **como campo** | `GO_C1=NOT_AVAILABLE` en 20+ ficheros | E |
| `ALLOW/BLOCK` | patrón compuesto | E |

**Dos hallazgos que yo no había visto:**
1. **La dimensión E tiene reglas de uso declaradas** (fail-closed, sin reintento implicado) — al
   nivel de detalle de V6. Es el vocabulario **más operacional** del proyecto: es el que gobierna
   R1, C1, R2 y R3.
2. **El campo de decisión de gate toma un valor del eje de evidencia**: `GO_C1=NOT_AVAILABLE`.
   El gate no es un eje independiente — **cruza A y E**. `SUPPORTED`.

**Consecuencia para MIG-01/MIG-02:** cuando se gatee R1, el vocabulario correcto y ya existente
es `GO`/`NO_GO`/`ABORT`/`NO_GO_PRE`, **no** el `ALLOW`/`BLOCK` que inventé en el informe de
migración. `OBSERVED`.

### Dimensiones REALES que el encargo NO listó (4) — `SUPPORTED`

| Dim | Nombre | Términos | Evidencia |
|---|---|---|---|
| **M** | `EVIDENCE_ELIGIBILITY` | `DIAGNOSTIC ONLY` `THERMALLY CONFOUNDED` `NOT FOR VERDICT` | V6+V7. Regla V6: «No contarla como PASS/FAIL». Eje **ortogonal** al eje de fuerza: una evidencia puede ser `VERIFIED` y a la vez no contar para veredicto. |
| **N** | `ESTIMATION_CLASS` | `ESTIMATED` | V5, definido: «modelo con supuesto no medible localmente». Se mezcla hoy con el eje de evidencia. |
| **O** | `TEMPORAL_VALIDITY` | `HISTÓRICO` `SNAPSHOT` `OBSOLETE` `LOST` `CONGELADO` | V6+V4. Regla V6: «Un `HISTÓRICO` o `SNAPSHOT` no prueba capacidad actual». |
| **P** | `COMPOSITION` | el operador `/` (§12) | 9 patrones reales, ninguna fuente lo declara. |

**Total real: 16 dimensiones**, no 12. El modelo solicitado estaba mal en 3 (sobran) y
subdimensionado en 4 (faltan).

---

## 5. DICCIONARIO SEMÁNTICO PROVISIONAL

Solo para los términos con **≥2 dimensiones en colisión**. Los restantes están en §5 del
`MIG-07-VOCABULARY-MAPPING-20260926T011531Z.md`, que se conserva.

| Término | Dim. primaria | Dim. secundarias | ¿Definido formalmente? |
|---|---|---|---|
| `VERIFIED` | A (evidencia) | B (booleano), I (etapa), P (compuesto), M | ⚠ **NO** — definido en V5 informalmente («leída»), ausente de V6 |
| `REPRODUCIBLE` | H | A (como clase), P (compuesto) | V3 sí |
| `DOCUMENTED` | I (etapa CAPABILITY) | A (V5), I (V6 regla), P | V6 sí, pero como *documentación*; no como *evidencia* |
| `PASS` | F (resultado) | D (paso de procedimiento), P (**label de arista**), M | ⚠ **NO** en ninguna fuente |
| `FAIL` | F | P (label de arista), D, E (implícito) | V2 sí, pero como gate |
| `DEFERRED` | D | B (por hallazgo), campo-scoped | V2 sí |
| `UNKNOWN` | A | F (V4), B | V2, V6, V4 |
| `NOT_AVAILABLE` | A | F (V4), B | V2, V4 |
| `CONFLICT` | K | A (V2) | V2, V6 |
| `PARTIALLY VERIFIED` | B (grado) | P | V6 sí |
| `PARTIALLY_RECONCILED` | K | — | V3 sí |
| `PARTIALLY_RESOLVED` | F | — | ⚠ **NO** (V4 no lo define) |
| `UNRESOLVED` | A (V3) | F (V4) | V3 sí / V4 no |
| `VERIFICADO` | A | H (solapa con REPRODUCIBLE) | V3 sí |
| `REPRODUCED` | A | H | ⚠ **NO** |

---

## 6. ANÁLISIS DETALLADO DE `VERIFIED` — 56 ficheros, 173 usos

`OBSERVED`. Ocho familias, no cinco. La revisión previa yerra en dos (§21).

| # | Familia | Usos | Dimensión | Ejemplo literal |
|---|---|---:|---|---|
| **VF-1** | Clase de evidencia, eje junto a `DERIVED`/`ESTIMATED` | ~60 | A | `VERIFIED (leída) / DERIVED (aritmética sobre VERIFIED) / ESTIMATED (modelo con supuesto no medible localmente)` |
| **VF-2** | **Grado/gradiente parcial** | ~35 | B | `PARTIALLY VERIFIED — Evidencia parcial, sin causalidad completa` |
| **VF-3** | **Regla metodológica** (compuesto «state-change verified») | ~25 | regla | `WRITE SUCCESS ≠ STATE CHANGE VERIFIED` — 8+ ficheros |
| **VF-4** | **Escalera de capacidad**, etapa de madurez | ~12 | I | `CAPABILITY → DOCUMENTED → PRESENT → READABLE → WRITABLE → EFFECTIVE → REVERSIBLE → BENCHMARK` |
| **VF-5** | **Campo booleano** en esquemas de datos | ~15 | B | `RECOVERY_VERIFIED=0/NO` · `RESTORE_VERIFIED: False` |
| **VF-6** | **Leyenda de diagrama** | ~10 | I | `HW["[VERIFIED/DOC] Hardware"]` · `morado VERIFIED` |
| **VF-7** | **Conclusión negativa explícita** | ~8 | A | `Resultado: NO. VERIFIED.` (= «queda descartado») |
| **VF-8** | **Uso coloquial** | ~8 | — | `VERIFIED verde` |

### Hallazgos sobre `VERIFIED`

1. **VF-2 lo hace jerárquico y compuesto, no excluyente.** `PARTIALLY VERIFIED` está
   **declarado en V6** con regla «Indicar siempre el alcance probado». No es un término libre.
2. **VF-7 invierte el signo respecto a V1/V2.** En V5/V6 `VERIFIED` significa «afirmación
   verificada». En `PRIOR-ART.md`, `Resultado: NO. VERIFIED.` significa «se comprobó que NO es
   posible». **Mismo token, semántica opuesta según el eje que se recorre.** Esto es una
   colisión de polarity, no de dimensión. `UNKNOWN`.
3. **VF-3 es una regla, no un estado**, y es la máscitada (8+ ficheros). `OBSERVED`.
4. **`VERIFIED` no está declarado en V6**, que es la autoridad. El término más usado del
   proyecto vive fuera de la fuente de verdad. `OBSERVED`.
5. **Los 4 términos que propuse como canónicos** (`VERIFIED`, `REPRODUCIBLE`, `DOCUMENTED`,
   `PASS`) están **los 4 fuera de V6**. `SUPPORTED`.

### No decidido
Cuál de las 8 familias debe sobrevivir. **No es determinable técnicamente.** Requiere decisión
editorial (§17).

---

## 7. ANÁLISIS DETALLADO DE `REPRODUCIBLE` — 21 ficheros, 79 usos

`OBSERVED`.

| # | Familia | Usos | Dimensión | Ejemplo literal |
|---|---|---:|---|---|
| **RF-1** | **Propiedad** de comportamiento actual | ~35 | H | `[REPRODUCIBLE] comportamiento actual que se reproduce de forma estable` |
| **RF-2** | **Compuesto negativo** `NO REPRODUCIBLE` | ~30 | H + O | `[NO REPRODUCIBLE] resultado histórico no reproducible hoy; NO tratar como hecho operacional` |
| **RF-3** | **Clase de evidencia** en notación de corchetes | ~10 | A | `verificación documental, cruce de fuentes, clasificación por evidencia (VERIFICADO/REPRODUCIBLE/OBSERVADO/…)` |
| **RF-4** | **Propiedad de familia de experimento/dataset** | ~4 | H | `Esta familia es REPRODUCIBLE (workload Vulkan autónomo)` |
| **RF-5** | **Condición de transición** en la máquina de estados | 1 | E(implicita) | `VALIDATED: gate completo y evidencia reproducible` |

### Hallazgos sobre `REPRODUCIBLE`

1. **No es el opuesto de `NO REPRODUCIBLE`.** `REPRODUCIBLE` es una propiedad del
   *comportamiento actual*; `NO REPRODUCIBLE` es un estado de un *resultado histórico*. Se
   relacionan por negación **de escala**, no de estado. Tratarlos como un par sería incorrecto
   — la instrucción de no hacerlo automáticamente queda **confirmada por la evidencia**.
   `SUPPORTED`.
2. **`VERIFICADO` y `REPRODUCIBLE` se solapan semánticamente** (H-11). Definiciones literales
   de `RX550_BUILD_SPECIFICATION.txt`:
   - `VERIFICADO` = «medido y confirmado de forma repetible hoy»
   - `REPRODUCIBLE` = «comportamiento actual que se reproduce de forma estable»
   Ambos implican repetición. **No son excluyentes ni jerárquicos: son redundantes.**
   `SUPPORTED`.
3. `REPRODUCED` (V5, `MASTER-PLAN:749`) **no es `REPRODUCIBLE`** y no está definido. Término
   no declarado, 1+ usos. `OBSERVED`.
4. `REPRODUCIBLE` se usa en 21 ficheros **sin estar declarado en V2 ni en V6**. `OBSERVED`.
5. La fila de la propuesta anterior `REPRODUCIBLE → REPRODUCIBLE` pasa de
   `REQUIRES_MANUAL_REVIEW` a **`REJECTED_PENDING_RENAMING`**: el destino es un término con
   21 ficheros de uso no declarado. `OBSERVED`.

---

## 8. ANÁLISIS DETALLADO DE `DOCUMENTED` — 5 ficheros, 11 usos

`OBSERVED`. **No es un término de evidencia.** La instrucción de no mapearlo a `SUPPORTED`
queda **confirmada por la evidencia**, no solo por prudencia.

| # | Familia | Dimensión | Evidencia literal |
|---|---|---|---|
| **DF-1** | **Etapa de escalera de madurez de interfaz** (1 de 8) | I | `CAPABILITY → DOCUMENTED → PRESENT → READABLE → WRITABLE → EFFECTIVE → REVERSIBLE → BENCHMARK` |
| **DF-2** | **Etapa de ciclo de vida de artefacto** | I | `DOCUMENTED, DESIGNED, AUTHORIZED, EXECUTED, VALIDATED` y la regla `DOCUMENTED != EXECUTED` |
| **DF-3** | **Valor de evidencia/gate en tabla** | A/E | `DOCUMENTED` / `DOCUMENTED/REQUIRES_REVIEW` en `P0-GATE` |
| **DF-4** | **Clase de evidencia** | A | `FASE-G`: `DOCUMENTED: lo descrito por fuentes primarias (kernel amdgpu, …)` |
| **DF-5** | **Composición** | P | `DOCUMENTED/OBSERVED` (1 uso) |

### Veredicto sobre `DOCUMENTED`

Las familias **DF-1, DF-2 y DF-5 son documentación/ ciclo de vida**. **DF-3 y DF-4 son
evidencia.** El término está partido entre dos dimensiones.

- `DOCUMENTED → SUPPORTED`: **incorrecto.** `SUPPORTED` = «respaldado por la evidencia y gates
  definidos» (V2). Un artefacto puede estar documentado y no estar supported. Además V6 dice
  que `EXISTE` «no implica ejecución ni validez», misma familia semántica que `DOCUMENTED`.
  `SUPPORTED` como pérdida confirmada.
- **DF-1 es el hallazgo mayor de esta fase para `DOCUMENTED`.** La escalera de 8 etapas
  (`DOCUMENTED … REVERSIBLE … BENCHMARK`) es un eje de **madurez de interfaz** que no existe
  en V1/V2/V3/V4 y que el encargo tampoco listeó. Está implícita en `MEG-1`.
  `SUPPORTED`.

---

## 9. ANÁLISIS DETALLADO DE `PASS` — 45 ficheros, 173+ usos

`OBSERVED`. **Seis roles distintos.** `PASS` no declarado en V2, ni en V3, ni en V4, ni en V5,
ni en V6 — la única fuente que lo menciona es **indirectamente**: V6 declara `NOT FOR VERDICT`
con la regla «No contarla como PASS/FAIL», lo que confirma que `PASS` es una noción central
**y no normada**.

| # | Rol | Dimensión | Evidencia literal | ¿Contable? |
|---|---|---|---|---|
| **PF-1** | **Resultado de test** | F | `print(f"[{'PASS' if ok else 'FAIL'}] {name}")` · `TESTS=PASS` | sí |
| **PF-2** | **Resultado de criterio de validación** en tabla | F | `\| P99(s) no creciente en s \| **PASS** \| sí (curva p1) \|` | sí |
| **PF-3** | **Resultado de paso de procedimiento** | D | `DRY_RUN=PASS` · `CLEANUP_STATUS=PASS` | sí |
| **PF-4** | **Salida de gate** | E(implicita) | `GATE -->\|PASS\| EXP["authorized experiment"]` | sí |
| **PF-5** | **Label de arista en diagrama de estados** | **P** | `T_PRE -->\|PASS\| T_POST` · `IS -->\|FAIL\| RS["RESTORE"]` | **no es estado** |
| **PF-6** | **Negación explícita / metadiscurso** | — | `No se dibuja un PASS/FAIL global.` · `Las vistas no eligen un PASS limpio` | n/a |

### Hallazgos sobre `PASS`

1. **PF-5 es un rol semántico distinto**: label de transición. Un `FAIL` en `T_PRE -->|FAIL| R1["RESTORE"]`
   **no describe el estado de nada**: describe la arista. `OBSERVED`.
2. **PF-4 revela la dimensión E ausente**: el gate tiene resultado (`PASS`/`FAIL`) pero **no
   tiene decisión**. No existe término para «se permite avanzar» o «se bloquea». `SUPPORTED`.
3. **`PASS` es un término de conteo, no de fuerza.** Contradice directamente la Regla de
   evidencia de V6: «`NOT FOR VERDICT` … No contarla como PASS/FAIL». `SUPPORTED`.
4. **Regla de coexistencia descubierta en el corpus** (`P0-GATE`): «`NOT_AVAILABLE` de una
   capability no se convierte en `PASS` ni en `REFUTED`». `PASS` es explícitamente **no
   alcanzable** desde la ausencia de evidencia. `OBSERVED`.

---

## 10. ANÁLISIS DE V4 (`PROBLEM-STATUS-FINAL.md`)

`OBSERVED` en los hechos; `PLAUSIBLE` en la clasificación.

### 10.1 Qué contiene
8 términos en la columna `Estado`: `RESOLVED` `PARTIALLY_RESOLVED` `UNRESOLVED` `OBSOLETE`
`ALREADY_FIXED_UPSTREAM` `NOT_REPRODUCED` `UNKNOWN` `NOT_AVAILABLE`.
Los usa en 5-6 ficheros, casi todos dentro de sí mismo.

### 10.2 Qué dimensión controla
`F = EXPERIMENTAL_RESULT`, con dos fugas hacia otras dimensiones:
- `OBSOLETE` → O `TEMPORAL_VALIDITY`
- `ALREADY_FIXED_UPSTREAM` → **atribución de causa**, dimensión que no está modelada en ninguna parte

### 10.3 Qué otros vocabularios consume
| Consume | Términos | Hallazgo |
|---|---|---|
| V1/V2 | `UNKNOWN` (806), `NOT_AVAILABLE` (286) | **Colisión**: usa 2 términos de evidencia como resultado de problema |
| V3 | `UNRESOLVED` (57) | **Colisión**: mismo string en dos dimensiones |
| V4 propios | — | `PARTIALLY_RESOLVED` y `ALREADY_FIXED_UPSTREAM` **no están definidos** en ninguna parte |

### 10.4 ¿Independiente o vista derivada? → **Vista derivada** — `SUPPORTED`

**Evidencia decisiva** (esta es la evidencia que permite clasificarlo):

```
**Fuente de observación:** `01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json`
```

V4 declara su fuente: **una única captura concreta**. Su autoridad deriva de ese
artefacto, no normativa. Además:
- V4 **no declara** `SOURCE_OF_TRUTH` (V7 sí lo hace)
- V4 **no aparece** en la lista `SOURCE_OF_TRUTH` de V7
- V4 **no está** en V6, que es la autoridad
- V4 **define su alcance con una frase de límite**: «`NOT_REPRODUCED` significa que el síntoma no
  apareció en la comprobación actual; no significa que su causa histórica esté resuelta»
- V4 está anclado a esa captura HOST-B (`kernel 6.18.2-fc43`) mientras el host vivo es HOST-C
  → esto es MIG-03, no un problema de vocabulario

**Conclusión:** V4 es una **vista derivada sobre una captura**, con vocabulario propio **no
normativo** y **parcialmente colisionado** con V1/V2/V3. Su valor está en que declara su
provenance; su debilidad, en que sus 2 términos más usados son, en realidad, de otras dimensiones.

### 10.5 Evidencia que habría permitido clasificarlo antes
La línea `Fuente de observación` estaba presente. **No fue leída en la auditoría anterior**,
que la analizó como vocabulario canónico. `OBSERVED` — omisión propia.

---

## 11. COLISIONES SEMÁNTICAS

| # | Colisión | Términos | Dimensiones | Gravedad | Clasificación |
|---|---|---|---|---|---|
| **SC-1** | Polaridad invertida | `VERIFIED` (VF-1 «afirmación verificada») vs `NO. VERIFIED.` (VF-7 «se descartó») | A consigo misma | **CRÍTICA** | `OBSERVED` |
| **SC-2** | Redundancia | `VERIFICADO` y `REPRODUCIBLE` implican ambos repetición | H | ALTA | `SUPPORTED` |
| **SC-3** | Mismo string, dos ejes | `UNKNOWN` (A) / `UNKNOWN` (F, V4) | A + F | ALTA | `OBSERVED` |
| **SC-4** | Mismo string, dos ejes | `NOT_AVAILABLE` (A) / (F, V4) | A + F | ALTA | `OBSERVED` |
| **SC-5** | Mismo string, dos ejes | `UNRESOLVED` (A, V3) / (F, V4) | A + F | ALTA | `OBSERVED` |
| **SC-6** | 6 roles | `PASS` / `FAIL` | F, D, E, **P** | **CRÍTICA** | `OBSERVED` |
| **SC-7** | Eje partido | `DOCUMENTED` en I (etapa) y en A (evidencia) | I + A | **CRÍTICA** | `OBSERVED` |
| **SC-8** | resultado/estado | `PARTIALLY_RECONCILED` (A, V3) vs `PARTIALLY_RESOLVED` (F, V4) | A + F | ALTA | `OBSERVED` (0 co-ocurrencia) |
| **SC-9** | Sin definición | `PASS` en 45 ficheros, 0 declaraciones | F | **CRÍTICA** | `OBSERVED` |
| **SC-10** | 5 sentidos | `VERIFIED` fuera de la autoridad V6 | 8 familias | **CRÍTICA** | `OBSERVED` |
| **SC-11** | Compuesto no declarado | `REPRODUCIBLE` dentro de `NO REPRODUCIBLE` | H | ALTA | `OBSERVED` |
| **SC-12** | Cuantificador de grado | `PARTIALLY VERIFIED` (B) vs `PARTIALLY RESOLVED` (F) | B + F | ALTA | `OBSERVED` |
| **SC-13** | Gate implícito | `FAIL` declarado como gate en V2, usado como resultado y como arista en 42 ficheros | E + F + P | ALTA | `OBSERVED` |
| **SC-14** | Escala de negación | `REPRODUCIBLE` (propiedad) vs `NO REPRODUCIBLE` (estado histórico) | H | MEDIA | `SUPPORTED` |

---

## 12. TÉRMINOS COMPUESTOS

| Compuesto | Forma | Ocurrencias | ¿Declarado? | Observación |
|---|---|---:|---|---|
| `PARTIALLY VERIFIED` | espacio | ~35 | **V6 sí** | con regla de uso |
| `PARTIALLY_VERIFIED` | **guion bajo** | ≥1 | no | **mismo término, dos grafías** |
| `NO REPRODUCIBLE` | prefijo | ~30 | V3 sí | negación por prefijo, no término |
| `WRITE SUCCESS ≠ STATE CHANGE VERIFIED` | frase | ~25 | no | **regla**, no estado |
| `VERIFIED/DERIVED` | barra | 5+4 | no | composición de clases |
| `VERIFIED / UNKNOWN`, `VERIFIED/DOC`, `VERIFIED / CONTRADICTED` | barra | 3 | no | composición |
| `ESTIMATED/UNKNOWN` | barra | 4+2 | no | composición |
| `INFERRED/HYPOTHESIS` | barra | 1 | no | composición |
| `DOCUMENTED/OBSERVED` | barra | 1 | no | composición |
| `VALIDADO / VALID` | barra | V6 | **V6 sí** | equivalencia de idioma |
| `HISTÓRICO / NO VERIFICABLE`, `PERDIDO / NO VERIFICABLE` | barra | V6 | **V6 sí** | composición de O + I |
| `S1 = EXECUTED / COMPLETADA` | barra+igual | V6 | **V6 sí** | estado + nota |
| `DEFERRED_NOT_ACCEPTABLE_AS_FULL` | guion bajo | V6 | no | **calificador de gate** |
| `DIAGNOSTIC ONLY`, `NOT FOR VERDICT`, `THERMALLY CONFOUNDED` | espacio | V6+V7 | **V6 sí** | elegibilidad, no fuerza |
| `DRAFT/CONFLICT` | barra | V7 | no | dos dimensiones en un token |

**REFUTADO (K-8):** conté **9 patrones** contando solo los términos que ya había inventariado.
Un escaneo global da **513 patrones únicos** de `TOKEN_A / TOKEN_B`. Y la barra tiene
**5 funciones distintas**, no una:

| # | Función de `/` | Ejemplo | ¿es composición de estados? |
|---|---|---|---|
| 1 | composición ordenada de clases | `VERIFIED/DERIVED` | **sí** |
| 2 | composición de conjunción | `HISTÓRICO / NO VERIFICABLE` | **sí** |
| 3 | equivalencia de idioma | `VALIDADO / VALID` | **sí** |
| 4 | par actor/acción o ruta | `ACTION/POST` · `AUDITORIA/DECISIONES` | no |
| 5 | par de nombres de hardware | `AHCI/SATA` · `APERF/MPERF` | no |

**Consecuencia:** la dimensión P no es «composición de estados», es «barra como operador
multiforme». Sin embargo **solo las funciones 1–3 afectan a la semántica de estado**; las
funciones 4–5 son separadores sintácticos que no deben entrar en el modelo. Distinguir ambas
es trabajo pendiente. `SUPPORTED`.

---

## 13. TÉRMINOS QUE PUEDEN COEXISTIR

Regla no declarada en el corpus, **deducida de la evidencia** — `PLAUSIBLE`:

| Coexisten | Evidencia | Dimensión |
|---|---|---|
| `VERIFIED` + `DERIVED` | `VERIFIED/DERIVED` como par ordenado (9 usos) | A, jerárquico |
| `VERIFIED` + `ESTIMATED` | `VERIFIED (leída) / DERIVED (aritmética) / ESTIMATED (modelo)` | A, jerárquico |
| `VERIFICADO` + `REPRODUCIBLE` | definiciones solapadas | H (**y esto es un defecto**) |
| `VERIFIED` + `NOT FOR VERDICT` | evidencia válida no contable | A + M |
| `EXECUTED` + `INCONCLUSIVE` | `EXECUTED --> INCONCLUSIVE` en V7 | I + F |
| `EXECUTED` + `THERMALLY_CONFOUNDED` | V7 | I + M |
| `DESCONOCIDO` + `HISTÓRICO` | V6, eje O ortogonal a A | A + O |
| `DRAFT` + `CONFLICT` | `STATUS: DRAFT/CONFLICT` en V7 | I + K |
| `PARTIALLY VERIFIED` + `CONTRADICTED` | `PARTIALLY VERIFIED / CONTRADICTED según fase` | B + K |

## 14. TÉRMINOS MUTUAMENTE EXCLUYENTES

| Excluyentes | Evidencia | Dimensión |
|---|---|---|
| `VALIDADO` / `NO IMPLEMENTADO` | V6: «No confundir con existente» | I |
| `EJECUTADO` / `DISEÑADO` | V6: «`EJECUTADO` no significa `VALIDADO`» | I |
| `LIVE` / `DRAFT` | V6: «No es `LIVE` ni resultado» | I |
| `VALIDADO` / `INCONCLUSO` | V7: `EXECUTED --> INCONCLUSIVE`, sin camino a `VALIDATED` | I + F |
| `PASS` / `FAIL` (en PF-1..PF-4) | resultado de una misma prueba | F |
| `SNAPSHOT` / capacidad actual | V6: «no prueba capacidad actual» | O |
| `PERDIDO` / recuperable | V6: «No reconstruir sin decisión nueva» | O |
| `NOT FOR VERDICT` / cualquier veredicto | V6: «No contarla como PASS/FAIL» | M |

**Consecuencia arquitectónica:** los 9 pares de §13 que coexisten y los 8 de §14 que se excluyen
**no pueden compartir un enumeración plana.** Un modelo de una sola lista
`EVIDENCE_CLASSIFICATION = {…}` es **insuficiente por construcción**.

---

## 15. INFORMACIÓN QUE SE PERDERÍA CON CADA NORMALIZACIÓN

| Normalización | Pérdida | Tipo de pérdida | Clasificación |
|---|---|---|---|
| `VERIFICADO → OBSERVED` | 329 usos degradados: se pierde «verificado por alguien» | **fuerza** | `SUPPORTED` |
| `REPRODUCIBLE → (eliminar)` | 79 usos: se pierde la propiedad de repetición | **fuerza + escala** | `SUPPORTED` |
| `DOCUMENTED → SUPPORTED` | 11 usos: se pierde toda la escalera de madurez | **eje completo** | `SUPPORTED` |
| `NO VERIFICADO → NOT_AVAILABLE` | 47 usos: «no comprobable» ≠ «ausente» | **semántica** | `SUPPORTED` |
| `UNRESOLVED (V3) → UNRESOLVED (F)` | colapsa un eje en otro | **eje** | `OBSERVED` |
| `PARTIALLY_RECONCILED → CONFLICT` | se pierde «mecano explicado» | **resolución** | `SUPPORTED` |
| `PASS → ALLOW` | se pierde que fue un resultado, no una decisión | **rol** | `SUPPORTED` |
| `FAIL → BLOCK` | igual, y además pierde el uso como arista | **rol + dimensión** | `SUPPORTED` |
| `VERIFIED → UNO` | colapsa 8 familias | **8 ejes** | `OBSERVED` |
| `PARTIALLY_VERIFIED` → unificar grafía | renombramiento prohibido en esta fase | — | — |
| Eliminar `/` (composición) | se pierden 9 patrones, incluido `VERIFIED/DERIVED` que codifica procedencia aritmética | **procedencia** | `SUPPORTED` |
| Eliminar `ESTIMATED` | se pierde la distinción entre número medido y número modelado | **fuerza** | `SUPPORTED` |
| Eliminar `NOT FOR VERDICT` | se pierde que hay evidencia excluida del conteo | **elegibilidad** | `SUPPORTED` |
| Colapsar `HISTÓRICO`/`SNAPSHOT` en `OBSERVED` | se pierde que no prueba capacidad actual | **validez temporal** | `SUPPORTED` |
| `DEFERRED → fase` | se pierde el uso por hallazgo y por campo | **ámbito** | `SUPPORTED` |

**15 pérdidas confirmadas. Ninguna conversión es silenciosamente segura.**

---

## 16. TÉRMINOS QUE NO DEBEN NORMALIZARSE TODAVÍA

| Término / conjunto | Motivo |
|---|---|
| `VERIFIED` (173 usos, 8 familias) | sin decisión editorial; fuera de la autoridad |
| `PASS` / `FAIL` (45/42 ficheros, 6 roles) | sin definición; rol de arista no modelado |
| `DOCUMENTED` (11 usos) | partido entre eje I y eje A |
| `REPRODUCIBLE` / `NO REPRODUCIBLE` (79 usos) | escalas distintas; solapa con `VERIFICADO` |
| `VERIFICADO` (329 usos) | término más usado; sin destino en V1 |
| Los 26 de V6 | son la autoridad; normalizarlos sería autorreferencial |
| El operador `/` (9 patrones) | dimensión P completa sin modelar |
| `ESTIMATED`, `INFERRED`, `REPRODUCED`, `UNVERIFIED` | V5, sin equivalencia fuera |
| `PARTIALLY VERIFIED` vs `PARTIALLY_VERIFIED` | normalización = renombramiento, prohibido |
| `UNKNOWN`, `NOT_AVAILABLE`, `UNRESOLVED` | colisiones SC-3/4/5 sin resolver |
| `ALREADY_FIXED_UPSTREAM` | única atribución de causa del proyecto; sin dimensión |

---

## 17. PREGUNTAS EDITORIALES REALMENTE ABIERTAS

Estas **no** se pueden responder con evidencia. Ninguna depende de más análisis.

| # | Pregunta | Por qué no es técnica | Impacto |
|---|---|---|---|
| **E-1** | ¿Cuál de las 7 fuentes es canónica? V6 se autodescribe provisional; V7 la declara `SOURCE_OF_TRUTH` pero es `DRAFT/CONFLICT`. | Es política documental | **Bloqueante total** |
| **E-2** | ¿`VERIFIED` en VF-7 («NO. VERIFIED») significa lo mismo que en VF-1? | Hoy significa lo contrario | ALTA |
| **E-3** | ¿`VERIFICADO` y `REPRODUCIBLE` son dos términos o uno con dos etiquetas? | Redundancia editorial | ALTA |
| **E-4** | ¿`DOCUMENTED` es etapa de madurez o clase de evidencia? | El corpus dice las dos | ALTA |
| **E-5** | ~~¿Existe una dimensión de gate?~~ **RESUELTA: sí** (`GO`/`NO_GO`/`ABORT`/`NO_GO_PRE`, reglas declaradas). Queda abierto: ¿`PASS`/`FAIL` se Consideran resultado o se eliminan del eje E? | El gate está modelado pero en otro vocabulario | MEDIA |
| **E-6** | ¿Se crea `VERIFY_INDEPENDENT` para cerrar el hueco J? | Requisito de RC-4. **Búsqueda: 0 usos. El término no existe.** | **ALTA** |
| **E-7** | ¿Se acepta la barra como dimensión (P), y con cuál de sus 5 funciones? | 513 patrones, 5 funciones | MEDIA |
| **E-8** | ¿`ESTADOS-ES-EN.md` se promueve de provisional a canónico? | Declarado `SOURCE_OF_TRUTH` por un `DRAFT` | MEDIA |
| **E-9** | ¿V3 (árbol externo) se incorpora al repo o se marca como fuente histórica? | MIG-08 | MEDIA |
| **E-10** | ¿`OBSOLETE` y `ALREADY_FIXED_UPSTREAM` se mueven a O y a una dimensión de causa? | Hoy son fugas de F | BAJA |

---

## 18. PROPUESTA DE MODELO NORMALIZADO PROVISIONAL

**No es un vocabulario. Es una declaración de ejes**, porque §13/§14 prueban que una lista
plana es insuficiente.

```yaml
# PROVISIONAL — NO APLICADO. Ejes, no términos.
axes:
  A_evidence_classification:      # fuente y fuerza
    declared_by: [V2, V3, V5]
    undeclared_terms_in_use: [VERIFIED, DERIVED(ok), ESTIMATED, INFERRED, REPRODUCED, UNVERIFIED]
  B_finding_state:                # ciclo de vida de un hallazgo
    declared_by: []
    note: SIN FUENTE DECLARADA
  C_investigation_state:
    exists: false                 # H-5 — 0 usos de 5 sinónimos buscados
  D_phase_state:  {terms: [DEFERRED, NOT_EXECUTED, PREPARED_FOR_REVIEW, CONTAMINATED_REQUIRES_ISOLATION]}
  E_gate_decision:               # REFUTADO: SÍ existe (§4-bis)
    exists: true
    terms: [GO, NO_GO, ABORT, NO_GO_PRE, ALLOW, BLOCK]
    declared_by: ["04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md"]
    field_instance: GO_C1
    rules: ["NO_GO nunca significa intentarlo de nuevo", "ABORT nunca autoriza una acción"]
    cross_dimension: "el valor del campo puede ser del eje A (GO_C1=NOT_AVAILABLE) -> E cruza A"
    note: "NO usar ALLOW/BLOCK inventados: el proyecto ya tiene GO/NO_GO/ABORT"
  F_experimental_result: {terms: [INCONCLUSIVE, PARADA_D, PASS, FAIL, RESOLVED, PARTIALLY_RESOLVED, NOT_REPRODUCED]}
  G_confidence:      {declared_by: [], note: "campo libre ALTA/MEDIA/BAJA, sin enumeración"}
  H_reproducibility: {terms: [REPRODUCIBLE, REPRODUCED, NO_REPRODUCIBLE], note: "escala, NO par de opuestos"}
  I_documentation_lifecycle:      # la autoridad
    declared_by: [V6]
    capability_ladder: [CAPABILITY, DOCUMENTED, PRESENT, READABLE, WRITABLE, EFFECTIVE, REVERSIBLE, BENCHMARK]
  J_independent_verification:
    exists: false                 # H-5 — origen de que RC-4 fuera invisible al vocabulario
  K_reconciliation_state: {terms: [PARTIALLY_RECONCILED, CONFLICT, CONGELADO, CONTRADICTED]}
  L_provenance:      {fields: [HOST_SCOPE, RUN_ID, SHA256, SOURCE_OF_TRUTH], note: "campos, no vocabulario"}
  M_evidence_eligibility: {terms: [DIAGNOSTIC_ONLY, THERMALLY_CONFOUNDED, NOT_FOR_VERDICT], orthogonal_to: A}
  N_estimation_class: {terms: [ESTIMATED]}
  O_temporal_validity: {terms: [HISTORICO, SNAPSHOT, OBSOLETE, LOST, CONGELADO]}
  P_composition:      {operator: "/", patterns_found: 513, declared: false, functions: 5}

authority:
  declared: V6_ESTADOS_ES_EN
  declared_by: V7_09_ESTADOS_CIENTIFICOS
  self_declared_status: DRAFT/CONFLICT
  caveat: "la autoridad declarada es ella misma provisional"
```

**Términos que NO propongo renombrar**: ninguno. Los 4 que la propuesta anterior dio por
canónicos pasan a `REJECTED_PENDING_RENAMING`.

---

## 19. CRITERIOS OBJETIVOS PARA CERRAR MIG-07

| # | Criterio | Estado | Objetivo verificable |
|---:|---|---|---|
| 1 | Vocabularios inventariados | **CUMPLE** | 7 fuentes, con conteos reales |
| 2 | Dimensiones separadas | **CUMPLE** | 16 dimensiones (9 del encargo + 4 nuevas + 3 inexistentes) |
| 3 | Mapping completo | **CUMPLE** | 26 filas heredadas + 15 pérdidas de §15 |
| 4 | Ambigüedades identificadas | **CUMPLE** | 14 colisiones, 15 compuestos |
| 5 | Sin pérdida silenciosa | **CUMPLE** | 0 migraciones, 0 renombres |
| 6 | Revisión independiente | **FALLA** | requiere otro autor |
| 7 | Contradicciones explícitas | **CUMPLE** | SC-1..SC-14 |
| 8 | **Autoridad declarada resuelta** (nuevo) | **FALLA** | E-1 abierta |
| 9 | **Dimensiones del encargo validadas** (nuevo) | **FALLA** | C y J no existen (0 usos); E sí existe (K-7) |
| 10 | **Términos candidatos no colisionan** (nuevo) | **FALLA** | 4 de 4 colisionan |

**3 de 10. MIG-07 no puede cerrarse en esta ejecución** — y no solo por la falta de revisor
independiente: **E-1, la elección de autoridad, es anterior a cualquier revisión.**

---

## 20. ELEMENTOS QUE REQUIEREN REVISIÓN INDEPENDIENTE

1. **E-1 / autoridad** — decisión editorial, no revisable técnicamente.
2. **Las 8 familias de `VERIFIED`** — mi separación puede ser incorrecta; requiere muestreo
   humano de los 173 usos.
3. **H-5 (2 dimensiones inexistentes)** — afirmación fuerte: «no existe término de investigación ni
   de verificación independiente». Refutable: una búsqueda más amplia podría encontrarlos. Nota:
   mi primera versión de H-5.erró al declarar también inexistente la dimensión E (K-7).
4. **H-6 (4 dimensiones nuevas)** — pueden ser re-categorizaciones de existentes.
5. **§10.4 V4 como vista derivada** — la evidencia es la línea `Fuente de observación`; un
   revisor debe confirmar que no hay otra declaración de autoridad en V4.
6. **H-9 / operador `/`** — **513** patrones y 5 funciones, no 9 y 1. Requerirá muestreo para
   separar las funciones 1–3 (semánticas) de 4–5 (sintácticas).
7. **Las 15 pérdidas de §15** — pueden ser 20.
8. **La clasificación de V6 como autoridad** — se apoya en una línea de V7 que es `DRAFT`.

---

## 21. CORRECCIONES A TRABAJOS PROPIOS ANTERIORES

Registradas, no ocultadas:

| # | Documento | Afirmación anterior | Corrección | Clasificación |
|---|---|---|---|---|
| **K-1** | `MIG-07-INDEPENDENT-REVIEW-…md` | «`VERIFIED` ya significa 5 cosas», una de ellas «estado systemd» | **Error de lectura.** `WSI["xdg-shell/Wayland<br/>state=4 activated<br/>[VERIFIED]"]` es un **tag de leyenda de diagrama** (VF-6); `state=4 activated` es estado WSI de Wayland, no systemd. La familia no existe. **Son 8 familias, no 5.** | `OBSERVED` |
| **K-2** | `MIGRATION-METHODOLOGY-AUDIT-…md` | «hay 3 vocabularios», luego «4» | **7 fuentes normativas declaradas.** El conteo de 4 omitió V5, V6 y V7. | `OBSERVED` |
| **K-3** | `MIG-07-VOCABULARY-MAPPING-…md` | propuso `VERIFIED`, `REPRODUCIBLE`, `DOCUMENTED` como canónicos | Los 3 **no están en V6**, la autoridad. Y `VERIFIED` tiene 8 familias. `REJECTED_PENDING_RENAMING`. | `OBSERVED` |
| **K-4** | `MIG-07-VOCABULARY-MAPPING-…md` | `DOCUMENTED` → eje A (evidencia) | `DOCUMENTED` pertenece principalmente a **I** (ciclo de vida / escalera de 8 etapas). | `OBSERVED` |
| **K-5** | análisis de V4 | V4 tratado como vocabulario canónico | V4 **declara su fuente**: es **vista derivada** de una captura HOST-B. | `OBSERVED` |
| **K-6** | `MIG-07-VOCABULARY-MAPPING-…md` | `PASS` → resultado + gate `ALLOW` | `PASS` tiene un **rol de arista** (PF-5) que no es ni estado ni decisión. 6 roles, no 2. | `OBSERVED` |
| **K-7** | este documento, §4 (1ª redacción) | «la dimensión **E** (gate) no existe en el corpus» | **REFUTADO por el propio escaneo.** `GO`/`NO_GO`/`ABORT` existen, con reglas de uso declaradas en `C1-ISOLATION-DESIGN-v1.0.md` y campo `GO_C1` en 20+ ficheros. Solo **C** y **J** no existen. Afirmación revertida. | `OBSERVED` |
| **K-8** | este documento, §12 y H-9 | «el operador `/` tiene 9 patrones» | **REFUTADO por escaneo global:** 513 patrones únicos y **5 funciones** de la barra (composición de estados, conjunción, equivalencia de idioma, separador de ruta, par de hardware). El conteo de 9 sale de contar solo los términos ya inventariados. | `OBSERVED` |

**Patrón (K-1..K-8):** los ocho errores son **subestimaciones de alcance** — vi menos
vocabulario del que existe. Ninguno fue un error de invención. Es la firma de RC-4 operando en
la dirección contraria a la que supuse: no inventé términos, **dejé de ver los que ya estaban**.

Y una observación sobre la revisión adversarial: K-7 y K-8 los refuté **con un escaneo más
amplio, no con más reflexión**. Los dos casos en que fallé eran de cobertura de búsqueda, no de
razonamiento. Eso sugiere que el límite real de esta fase es el muestreo, no el análisis — y es
un argumento a favor de que la revisión independiente sea por muestreo humano, no por otro
pasada de grep.

---

## 22. ESTADO

```
MIG-07=VERIFYING
MIGRATIONS_APPLIED=0
TERMS_RENAMED=0
TERMS_REMOVED=0
VOCABULARIES_FOUND=7      (enunciado decía 3)
DECLARED_AUTHORITY_FOUND=1  (ESTADOS-ES-EN.md, autodeclarada provisional)
DIMENSIONS_REAL=16        (encargo listaba 12; 2 no existen, 4 no listadas)
NONEXISTENT_DIMENSIONS=2  (C investigacion, J verificacion independiente — 0 usos cada una)
COLLISIONS=14
COMPOUNDS=15
CONFIRMED_LOSSES=15
EDITORIAL_QUESTIONS=10    (E-5DOWNGRADED tras K-7)
CLOSURE_CRITERIA_MET=3/10
SELF_REFUTATIONS=2        (K-7, K-8)
INDEPENDENT_REVIEW=NOT_PERFORMED
IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

**Nota de método.** El encargo decía «No asumas que todas deben existir finalmente». La
evidencia fue más lejos: **dos de las doce dimensiones que el encargo daba por existentes
no existen**, y **hay cuatro que el encargo no=listó**. El modelo A–L de partida era incorrecto,
y esa corrección es probablemente el resultado más útil de esta fase: sin ella, cualquier
vocabulario que se construya encima heredaría dos dimensiones vacías y omitiría cuatro reales.

Y una limitación que declaro sobre mi propio trabajo: **los dos casos en que esta fase se
refutó a sí misma (K-7, K-8) fallaron por cobertura de búsqueda, no por razonamiento** — un
escaneo más amplio los refutó. Eso significa que el límite real aquí es el muestreo, y que una
revisión independiente feita con la misma técnica **heredaría el mismo sesgo**. La revisión
independiente tiene que ser por muestreo humano sobre los usos, no por otro `grep`.
