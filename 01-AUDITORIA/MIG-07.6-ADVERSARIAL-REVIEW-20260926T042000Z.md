# MIG-07.6 — REVISIÓN ADVERSARIAL INDEPENDIENTE DE MIG-07.5

> Artefacto nuevo de auditoría. No modifica MIG-07.5 ni ningún artefacto previo.
> **No es una revisión independiente en autoría.** Ver §1.2 — esa limitación no se oculta.

```
DOCUMENT_ID=MIG-07.6-ADVERSARIAL-REVIEW-OF-MIG-07.5
CREATED_UTC=2026-09-26T04:20:00Z
TYPE=ADVERSARIAL_REVIEW
AUTHOR_INDEPENDENCE=NO          # ver §1.2
TARGET=MIG-07.5-SELF-METHODOLOGY-GAP-20260926T034000Z.md
MIG-07=VERIFYING
MIG-07.5=VERIFYING
MIG-07.6=VERIFYING
IMPLEMENTATION=NOT_EXECUTED
```

Clasificación: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `NOT_PROVEN` · `CONFLICT`

---

## 1. FASE 1 — IDENTIDAD Y CONTAMINACIÓN

### 1.1 Quién produjo qué

| Elemento | Autor | ¿Verificable sin reutilizar sus conclusiones? |
|---|---|---|
| Los 19 casos y su tabla de 8 columnas | mismo | **No.** Las respuestas son juicio del autor sobre evidencia |
| Las 18 señales y su estado `EXISTENTE/PARCIAL/AD_HOC/NO_IMPLEMENTADA` | mismo | **No.** El estado es juicio |
| Los 14 triggers y sus 5 atributos | mismo | **Parcialmente**: la *existencia* de la condición es verificable; `TRIGGER_REQUIRED` y `PROMOTION_BLOCK_REQUIRED` son juicio |
| El modelo L0–L5 y las asignaciones por clase | mismo | **No.** Juicio puro |
| RQ1–RQ7 | mismo | **Parcialmente**: que la capacidad falte es verificable; que el requisito sea *necesario* es juicio |
| §11.2 (13 `REQUIRED`, 2 `USEFUL`, 2 `OPTIONAL`, 3 `NOT_JUSTIFIED`) | mismo | **No.** Juicio |
| Los 10 falsos positivos | mismo | **Sí**, en parte: FP-5, FP-6, FP-8 son reconstructibles desde artefactos |
| **O-01** | mismo | **SÍ — y reproducido en §3** |
| Los conteos (154 tests, 7 campos a 0, 14 diagramas, 27 filas) | mismo | **SÍ — reverificados en §4** |
| Capacidades OpenCode V2 | tercero (doc oficial) | **SÍ — reverificadas en §14** |

### 1.2 La limitación estructural, declarada antes que nada

**Soy el mismo agente que produjo MIG-07.5.** No puedo ser independiente en autoría.

Lo que sí es posible y es lo que este documento hace: **re-derivar cada conclusión desde
artefactos y mediciones, sin aceptar las conclusiones del autor como entrada.** Cuando eso es
posible, la verificación es genuina aunque el revisor sea el mismo. Cuando no, se marca
`AUTHOR_REASONING_ONLY=YES` y **no cuenta como evidencia**.

Por eso el resultado de §15 es `PARTIALLY_CONFIRMED` y no `CONFIRMED`: **no puedo demostrar
independientemente la afirmación más fuerte de MIG-07.5, y he encontrado evidencia que la
acota.** `SUPPORTED`

### 1.3 Clasificación de afirmaciones

| Clase | Nº | Qué incluye |
|---|---:|---|
| `INDEPENDENTLY_VERIFIABLE` | **11** | conteos, O-01, capacidades V2, las 3 contrapruebas, FP-5/6/8 |
| `PARTIALLY_INDEPENDENT` | **6** | triggers (existencia sí, severidad no), RQ (falta sí, necesidad no) |
| `AUTHOR_REASONING_ONLY` | **9** | L0–L5, §11.2, FP-1/2/3/4/9/10, la clasificación de las 11 clases |
| `NOT_VERIFIABLE` | **2** | si MIG-07.5 *razonó* bien; qué habría ocurrido sin esta revisión |

---

## 2. FASE 2 — BÚSQUEDA DE CONTRAEVIDENCIA

```
COUNTEREVIDENCE_FOUND=YES
```

**Encontré 6 documentos normativos de la raíz que MIG-07.5 nunca examinó.** Cero citas de cada uno:

| Documento | Citas en MIG-07.5 | Qué contiene |
|---|---:|---|
| `TESTING.md` | **0** | `§5 Criterio de cierre`: gate de promoción con 6 precondiciones |
| `ROLLBACK.md` | **0** | `§4`: procedimiento ejecutable de verificación post-acción |
| `PATCH-REGISTRY-FINAL.md` | **0** | 16+ correcciones, cada una con prueba de validación y hash de script |
| `CHANGELOG.md` | **0** | registro de cambios por dominio |
| `RELEASE-EXCLUSIONS.md` | **0** | — |
| `INSTALL.md` | **0** | — |

**Esto ya es un hallazgo en sí mismo: MIG-07.5/XP documentó `COVERAGE_GAP` como uno de sus gaps, y lo cometió contra sí mismo en el mismo documento.** `OBSERVED`

### CE-1 — Refutación parcial de trigger 6 (`SELF_CORRECTION_NOT_VERIFIED = DETECTION_METHOD:ninguno`)

`TESTING.md §5` — texto literal:

> Un problema puede pasar de `PARTIALLY_RESOLVED` a `RESOLVED` **sólo si existe una prueba
> reproducible, identidad de GPU, configuración exacta, resultado positivo y negativo explícito
> cuando aplique, y rollback documentado**. La ausencia de un error en una instantánea se registra
> como `NOT_REPRODUCED`, **no como `RESOLVED`**.

Seis precondiciones obligatorias. Y la última frase **prohíbe literalmente el modo de fallo que
produjo O-01**: tomar ausencia de error por resolución.

**Veredicto: `DETECTION_METHOD=ninguno` es FALSO.** Existe una regla escrita, es obligatoria, y
prohíbe exactamente el error observado. **MIG-07.5 queda refutado en este punto.** `OBSERVED`

### CE-2 — Refutación parcial adicional: `PATCH-REGISTRY-FINAL.md`

- `:16` — `RESOLVED`: «implementada **y verificada en el alcance indicado**»
- `:79` — campo obligatorio «**Prueba de validación:** `run_tests.py` `64/64`»
- `:71`, `:258`, `:278` — hash del script de prueba por entrada (`fa4c4885…`, `4e0fb097…`)

Es decir: **cada corrección está ligada por hash a su artefacto de prueba.** Es un mecanismo de
verificación de correcciones, escrito y aplicado 16+ veces. `OBSERVED`

### CE-3 — Refutación parcial adicional: `ROLLBACK.md §4`

Procedimiento ejecutable (3 comandos) + la regla: *«Un estado `UNKNOWN`, `NOT_AVAILABLE` o
`UNRESOLVED` **no se convierte en éxito por el mero hecho de que el sistema arranque**»*.

Otra prohibición directa de la clase de error de O-01. `OBSERVED`

### CE-4 — El límite que salva la conclusión de MIG-07.5

Los tres mecanismos son de **ámbito de sistema/runtime**. Términos de `TESTING.md §5`:
`prueba reproducible`, `identidad de GPU`, `configuración exacta`, `rollback`.
Cero menciones de: `artefacto`, `.md`, `texto`, `redacción`.

Y: **el único fichero de todo el repo que menciona escaneo de caracteres es el propio
MIG-07.5.** `OBSERVED`

**Conclusión de FASE 2, y es el resultado central de esta revisión:**

> El gap **existe**, pero está **acotado al dominio de artefactos y prosa**, y MIG-07.5 lo
> presentó como **global** sin haber examinado los 6 documentos que lo delimitan. La afirmación
> correcta es más estrecha y más defendible que la original.

---

## 3. FASE 3 — REPRODUCCIÓN INDEPENDIENTE DE O-01

Sin usar la descripción de MIG-07.5. Búsqueda directa.

| # | Paso | Resultado | Evidencia |
|---:|---|---|---|
| 1 | Buscar la referencia | `MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md` contiene `dePersistir` | `grep -n` |
| 2 | **Verificar la línea real** | **línea 23** | `Esta corrección se incorpora **antes** dePersistir, y fue verificada…` |
| 3 | Verificar el defecto | texto latino `de` + `Persistir` fundidos | inspección directa |
| 4 | Verificar que **permanece** | sí, en el fichero actual | `sha256 = 575c7957…` sin cambio |
| 5 | ¿Hay alguna regla que obligue a corregirlo? | **NO** para `.md`; **SÍ** para correcciones de sistema (`TESTING.md §5`, `PATCH-REGISTRY`) | búsqueda literal |
| 6 | ¿Hay revalidación posterior? | **NO** para prosa | CE-4 |
| 7 | ¿Podía sobrevivir al procedimiento? | **SÍ**: el gate de `TESTING.md §5` no cubre `.md` | CE-1e |
| 8 | ¿Coincide con la descripción de MIG-07.5? | **NO**: MIG-07.5 decía línea 43; la real es 23. Ya corregido en MIG-07.5 §6.4 | esta revisión |

```
O01_RESULT=CONFIRMED_AND_REPRODUCED
O01_LINE_CORRECTION=43 -> 23
O01_RULE_EXISTS_FOR_THIS_DOMAIN=NO
O01_BLOCKED_BY_EXISTING_GATE=NO
```

**O-01 se reproduce íntegramente, con una corrección factual.** Y su valor probatorio es **menor**
de lo que MIG-07.5 afirmó: no demuestra que el sistema no pueda detectar el defecto —demuestra que
**el gate que existe no cubre este dominio**. `SUPPORTED`

---

## 4. FASE 4 — REVISIÓN DE LOS 19 CASOS

Evidencia independiente consultada por caso. `RULE` = ¿existe regla? `AUTO` = ¿chequeo
automatizado? `MAND` = ¿acción obligatoria? `CORR` = ¿verificación de corrección? `IND` =
¿independencia?

| CASE | Evidencia independiente | RULE | AUTO | MAND | CORR | IND | RESULT |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| MIG-01 | artefacto del run 2 con traceback | no | no | no | no | no | `CONFIRMED` |
| MIG-02 | 154 tests / 2 `assertRaises` / 12 `main()` | no | **sí** | no | no | no | `CONFIRMED` |
| MIG-03 | `PROBLEM-STATUS-FINAL.md:6` vs host vivo | **sí** (`No se funden`) | no | no | no | no | `CONFIRMED` |
| MIG-04 | gate HOST-A referenciado | no | no | no | no | no | `CONFIRMED` |
| **MIG-07/E1** | 5 reglas de precedencia, 0 aplicables | **sí** (`No elegir`) | no | **sí** (escalar) | no | no | `CONFIRMED` |
| MIG-07/E6 | 7 campos de identidad a 0 ocurrencias | no | no | no | no | **no** | `CONFIRMED` |
| K-7 | `NO_GO` en 5 ficheros, 19 usos | no | **sí** | no | no | no | `CONFIRMED` |
| K-8 | 513 patrones únicos | no | **sí** | no | no | no | `CONFIRMED` |
| MIG-09 | lectura del fichero | no | no | **no** | no | no | `CONFIRMED` |
| MIG-12 | `git log` = 0 commits | no | **sí** | no | no | no | `CONFIRMED` |
| MIG-13 | 2 runs, 0 evidencia | no | **sí** | no | no | no | `CONFIRMED` |
| MIG-14 | sin causa | no | no | no | no | no | `PARTIALLY_CONFIRMED` (el gap sí; la causa sigue `UNKNOWN`) |
| MIG-15 | conteo de referencias | no | **sí** | no | no | no | `CONFIRMED` |
| **O-01** | **reproducido §3** | no | **sí** | no | **sí, y no se usó** | no | `CONFIRMED` |
| **O-02** | transcript + corrección posterior | no | **sí** | no | no | no | `PARTIALLY_CONFIRMED` (el incidente es `TX`, no artefacto) |
| P-01 | conteo directo de 7 campos | no | **sí** | no | no | no | `CONFIRMED` |
| X-01 | `ROUTER:267` | **sí** | no | **sí** | no | no | `CONFIRMED` |
| X-02 | MRS vs AGENTS | no | no | no | no | no | `PARTIALLY_CONFIRMED` (la degradación es juicio) |
| **D-01** | 226 vs 360: regex defectuosa | no | **sí** | no | **sí, y se rehízo** | no | `CONFIRMED` |

**Resultado: 15 `CONFIRMED`, 4 `PARTIALLY_CONFIRMED`, 0 `REFUTED`, 0 `NOT_REPRODUCED`.**

**Pero un dato que corrige a MIG-07.5:** la columna `MAND` (acción obligatoria) **no está a cero**:
MIG-07/E1 y X-01 tienen regla que obliga a escalar. MIG-07.5 los clasificó `AD_HOC` en §4. **Es
una clasificación demasiado pesimista en 2 de 19.** `CONFLICT`

---

## 5. FASE 5 — REVISIÓN DE LOS 14 TRIGGERS

| # | Trigger | ¿Condición existe? | ¿Gap metodológico o del proyecto? | ¿Regla existente? | Falso positivo | Falso negativo |
|---:|---|---|---|---|---|---|
| 1 | `PRECEDENCE_RULE=NOT_AVAILABLE` | **SÍ** (medido) | **Metodológico**: es del sistema documental | no | no | no |
| 2 | `REQUIRED_DIMENSION_NOT_IMPLEMENTED` | **SÍ** (0 usos) | Metodológico | no | no | no |
| 3 | `REQUIRED_PROVENANCE_NOT_AVAILABLE` | **SÍ** (7 campos a 0) | **Parcialmente del proyecto**: `TESTING.md §4` *sí* exige identidad de GPU y config | parcial | **posible**: esos campos no son "requeridos" por ninguna regla | no |
| 4 | `INDEPENDENT_VERIFICATION_NOT_AVAILABLE` | **SÍ** (0 campos) | Metodológico | no | no | no |
| 5 | `COVERAGE_NOT_DEMONSTRATED` | **SÍ** (3 casos) | Metodológico | no | no | **MIG-07.5 se detecta a sí mismo: 6 documentos no examinados** |
| 6 | `SELF_CORRECTION_NOT_VERIFIED` | **SÍ, pero `DETECTION_METHOD` FALSO** | **Mitad proyecto, mitad metodología** | **SÍ** — `TESTING.md §5`, `PATCH-REGISTRY`, `ROLLBACK.md §4` | **confirmado como error de MIG-07.5** | **el defecto de cobertura documental** |
| 7 | `RECURRING_DEFECT` | **SÍ** | Metodológico | no | no | no |
| 8 | `SAME_DEFECT_AFTER_CORRECTION` | **SÍ** | Metodológico | no | no | no |
| 9 | `PRODUCER_EQUALS_VERIFIER` | **SÍ** (19/19) | Metodológico | no | no | no |
| 10 | `REQUIRED_GATE_NOT_IMPLEMENTED` | **SÍ** para prosa | Mitad | **SÍ** para sistema | **parcial**: hay gate, no cubre el dominio | no |
| 11 | `AUTHORITY_CONFLICT_WITHOUT_PRECEDENCE` | **SÍ** | Metodológico | `CONFLICT` + `ESCALATION` | no | no |
| 12 | `STATE_CONFLICT_WITHOUT_RECONCILIATION` | **SÍ** (14) | Metodológico | `CONFLICT` declarado | no | no |
| 13 | `SOURCE_IDENTITY_UNRESOLVED` | **SÍ** | Metodológico | `HOST_SCOPE` (parcial, falló 2×) | no | no |
| 14 | `HISTORICAL_EVIDENCE_USED_AS_CURRENT` | **SÍ** | Mitad | `STALE` en router y censo §7 (16 docs) | no | no |

**Veredicto de triggers: 12 de 14 se sostienen. 2 requieren corrección (3 y 6).**

- **Trigger 6: `DETECTION_METHOD` es `SUPPORTED`, no `ninguno`.** Refutado.
- **Trigger 3: «required» no está justificado.** `REQUIRED_PROVENANCE_NOT_AVAILABLE` presupone
  que esos campos son requeridos; ninguna regla lo dice. Es un juicio, no un gap demostrado.
  **MIG-07.5 lo presentó con la misma autoridad que los demás.** `CONFLICT`
- **Trigger 5: hay un falso negativo encubierto.** MIG-07.5 detectó el `COVERAGE_GAP` en otros y lo
  incurrió en sí mismo. `OBSERVED`

---

## 6. FASE 6 — VERIFICACIÓN DE FALSOS POSITIVOS

| FP | Declarado por MIG-07.5 | Verificación independiente | Veredicto |
|---|---|---|---|
| **FP-5** | «O-01 prueba que la detección funciona» → REFUTADO, prueba lo contrario | Reproducido: detección funcionó, remediación no | **`CONFIRMED` como corrección válida** |
| **FP-6** | K-7 y K-8 son un mismo defecto → REFUTADO, son dos | K-7: dimensión omitida (encontrada por búsqueda dirigida). K-8: conteo subestimado (encontrado por barrido global). Mecanismos y causas distintas | **`CONFIRMED` como corrección válida** |
| **FP-8** | MRS no es conflicto sino diferencia de dimensión | `AGENTS:21-24` (no tiene estado actual) vs `DIAGRAMS/README:24` (autoridad documental + addendas). Ambas ciertas a la vez | **`CONFIRMED`, pero `PLAUSIBLE`**: la separación es del revisor, no del proyecto |
| **FP-4** | «`CONFLICT` no es mecanismo: es un valor que escribe el autor» | **REFUTADO PARCIALMENTE**: el router tiene columna `ESCALATION`, `REVIEW_REQUIRED → "Escalar a revisión editorial"`, y documenta un caso de escalada fallida (`RT-0003`). **Sí hay mecanismo de escalado** | **`PARTIALLY_WRONG` — error de MIG-07.5** |
| **FP-1** | el escaneo CJK no es mecanismo | Correcto: no versionado, cobertura parcial, salida no registrada | `CONFIRMED` |
| **FP-2** | V6 es la autoridad | Correcto: `AUTHORITY_CONFLICT` se sostiene | `CONFIRMED` |
| **FP-3** | 4 triggers `NO` no son capacidad faltante | Parcialmente correcto; pero la distinción «no lo detecto» / «no existe» sigue sin operacionalizarse | `CONFIRMED` con reserva |
| **FP-9** | `CONFLICT` de AGENTS/V6 es misma dimensión | `AGENTS:98` (hecho) vs `V6:35` (hecho + regla). Mismo token, distinta definición | `CONFIRMED` |
| **FP-10** | un detector no puede ver lo no anticipado | Correcto y estructural | `CONFIRMED` |

**`FALSE_POSITIVES_CONFIRMED=7` (de 9 verificados), `1 PARCIALLY_WRONG` (FP-4), `0 refutados`.**

**Resultado neto para MIG-07.5: 7 de sus 9 autocorrecciones son válidas. 1 contiene un error.
Y el error (FP-4) es del mismo tipo que los que FP-5 y FP-8que identifican: subestimación
del mecanismo existente.** `SUPPORTED`

---

## 7. FASE 7 — FALSOS NEGATIVOS

```
FALSE_NEGATIVES_FOUND=5
```

### FN-1 — Los 6 documentos normativos de la raíz nunca examinados

- **EVIDENCIA**: 0 citas de `TESTING.md`, `ROLLBACK.md`, `PATCH-REGISTRY-FINAL.md`,
  `CHANGELOG.md`, `RELEASE-EXCLUSIONS.md`, `INSTALL.md` en MIG-07.5
- **WHY MISSED**: el análisis se concentró en `01-AUDITORIA/` y en el subárbol `00-INDICE/`,
  que es donde estaban los conflictos. **Nuncalooked en la raíz.**
- **WHICH TRIGGER**: ninguno. Ninguno de los 14 triggers obliga a revisar documentos normativos
  de la raíz. **`WHETHER_TRIGGER_EXISTS=NO`**
- **DETECTION POSSIBLE**: **SÍ** — un barrido de `ls *.md` en la raíz, que es lo primero que
  hice en esta revisión

**Este es el falso negativo más grave y es una confirmación directa del gap: el trigger que
debería haberlo detectado no existe.** `OBSERVED`

### FN-2 — El collector se autodeclara `NON_AUTHORITATIVE`

- **EVIDENCIA**: `privileged_read_collector.py` — `"COLLECTOR_OWNERSHIP_BOOLEAN":
  "NON_AUTHORITATIVE"` y `"AUTHORITY": "AGENTS_MD_OWNERSHIP_CRITERION"`. 5 ocurrencias.
- **WHY MISSED**: MIG-07.5 menciona `AUTHORITY` en §8.3 y dice «no registra quién verificó» —
  lo cual es cierto — pero no registrar que **la herramienta limita su propio estatuto epistémico**
- **WHICH TRIGGER**: 3 (`REQUIRED_PROVENANCE`) parcialmente
- **DETECTION POSSIBLE**: **SÍ**, un `grep` del campo

Es un mecanismo de **auto-limitación epistémica** realmente implementado. Debilitó la afirmación
de que `OUTPUT_INTEGRITY` no tiene ninguna salvaguarda. `OBSERVED`

### FN-3 — Técnica de verificación independiente por AST sin allowlist

- **EVIDENCIA**: `R1-COLLECTOR-INDEPENDENT-REVIEW-20260925.md:174` — «**Escaneo AST
  independiente, sin allowlist**: 0 llamadas mutantes»
- **WHY MISSED**: MIG-07.5Ctó `AUTOMATED_CHECK` solo por el escaneo de caracteres, no por el
  escaneo AST del collector
- **DETECTION POSSIBLE**: **SÍ**, leyendo los artefactos de revisión previos

Es un método de verificación **más fuerte** que el escaneo de caracteres: analiza el código, no el
texto. MIG-07.5 no lo mencionó. `OBSERVED`

### FN-4 — Correcciones ligadas por hash a su artefacto de prueba

- **EVIDENCIA**: `PATCH-REGISTRY-FINAL.md:71,258,278` — hashes `fa4c4885…`, `4e0fb097…`
- **WHY MISSED**: MIG-07.5 afirmó (§11.1) que el proyecto «tiene provenance sobre *qué* y
  ninguno sobre *quién*». Correcto. Pero omitió que **cada corrección está atada a su prueba por
  hash**, que es provenance de *verificación*, no de *persona*.
- **DETECTION POSSIBLE**: **SÍ**

### FN-5 — 360 rutas staged / 0 commits, nunca clasificado

- **EVIDENCIA**: `staged=360`, `HEAD=c614678`, 0 commits que toquen el collector
- **WHY MISSED**: MIG-07.5 no menciona `staged` en ningún punto (0 coincidencias)
- **WHICH TRIGGER**: 3 (`REQUIRED_PROVENANCE_NOT_AVAILABLE`)
- **DETECTION POSSIBLE**: **SÍ**, `git status`

Es el gap de provenance **más grande del proyecto** y MIG-07.5 no lo menciona, mientras sí
analiza campos de identidad con 0 ocurrencias. `OBSERVED`

---

## 8. FASE 8 — VERIFICACIÓN DE L0–L5

| Nivel | ¿Se puede demostrar con un ejemplo real? | Contrajemplo | Veredicto |
|---|---|---|---|
| **L0** `NO_DETECTION` | **SÍ**: C y J con 0 usos de término; `VERIFIED_BY`=0 | — | **`PROVEN`** |
| **L1** `MODEL_DETECTION` | **SÍ**: 17/19 casos de §4 detectados sin regla | — | **`PROVEN`** |
| **L2** `PROCEDURAL_DETECTION` | **SÍ**: `AGENTS.md:106` «Never convert `UNKNOWN`… into `PASS`» | se cumple en prosa, no impone registro | **`PROVEN`, débil** |
| **L3** `AUTOMATED_DETECTION` | **SÍ**: `tools/validate_rx550_final.py` (302 líneas, AST válido) + 154 tests | O-01: el chequeo corrió y su salida no se procesó | **`PROVEN` por existencia; `NOT_PROVEN` como garantía metodológica** |
| **L4** `INDEPENDENT_DETECTION` | **NO.** `REVIEWER` en 1 fichero; `VERIFIED_BY`/`AUTHORED_BY`/`REVIEWED_BY`/`Autor:` = **0**. Las 2 revisiones «independientes» no tienen campo de autor y las escribió el mismo agente | — | **`NOT_PROVEN`** |
| **L5** `STRUCTURAL_ENFORCEMENT` | **NO.** `TESTING.md §5` es L2-L3 (escrito, no automático). `ROUTER:ESCALATION` no se ejecutó para VOCABULARY. Ningún `deny` activo | — | **`NOT_PROVEN`** |

**Consecuencia: `L4` y `L5` no son `PROVEN`, son `NOT_PROVEN`.** MIG-07.5 los trata la ausencia
como nivel 0. **Son estados epistémicos distintos**: `L0` afirma que no existe detección;
`NOT_PROVEN` afirma que **no se pudo determinar**. La distinción importa y el modelo de MIG-07.5
no la tiene para estos niveles. `SUPPORTED`

---

## 9. FASE 9 — REVISIÓN DE `L3_MAX`

MIG-07.5 afirmó `CURRENT_DETECTION_LEVEL=L3_MAX`.

**Separación exigida por el encargo:**

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Existe una herramienta que puede detectar? | **SÍ** | `validate_rx550_final.py`, 154 tests, escaneo AST |
| ¿La metodología **garantiza** que el detector se ejecute? | **NO** | O-01: el escaneo corrió y el defecto quedó |
| ¿Garantiza **cobertura**? | **NO** | FN-1: 6 documentos no examinados |
| ¿Garantiza que el resultado **se procese**? | **NO** | O-01, y §5 de MIG-07.5 |

**Veredicto: `L3_MAX` es correcto sólo por existencia de herramienta, y `EXAGERADO` como
afirmación metodológica.** El nivel correcto depende del dominio:

| Dominio | Nivel por existencia | Nivel por garantía metodológica |
|---|---|---|
| Estado del sistema RX550 | L3 | L2 |
| Collector (código) | L3 | L2 (tests existen pero no cubren orquestación: MIG-02) |
| **Artefactos y prosa** | L3 (ad hoc) | **L1** |
| **Cobertura de investigación** | L0 | L0 |
| **Autocorrección** | L1 | L0 |
| **Independencia** | L0 | L0 |

```
CURRENT_DETECTION_LEVEL=DOMAIN_DEPENDENT
CURRENT_DETECTION_LEVEL_MAX=L3_BY_EXISTENCE
CURRENT_DETECTION_LEVEL_MAX_BY_GUARANTEE=L2
```

**MIG-07.5 no hizo esta distinción y por eso `L3_MAX` sugiere más cobertura de la que existe.**
`SUPPORTED`

---

## 10. FASE 10 — `SELF_CORRECTION_MODEL`

MIG-07.5 afirmó `L0` y marcó `diff`, `rollback`, `post-check`, `comparación antes/después` como
`NOT_AVAILABLE`. **Eso es incorrecto a nivel de proyecto.**

| Mecanismo | ¿Existe? | Evidencia | Ámbito |
|---|---|---|---|
| `diff` | **SÍ** | 50 documentos lo mencionan | proyecto |
| rollback | **SÍ** | 44 documentos; `ROLLBACK.md` completo | sistema |
| hash de artefacto | **SÍ** | 94 documentos; censos congelados | proyecto |
| test | **SÍ** | 142 documentos; 154 tests | sistema/código |
| re-ejecución | **SÍ** | 21 documentos | sistema |
| verificación post-acción | **SÍ** | `ROLLBACK.md §4`, 3 comandos | sistema |
| cierre con 6 precondiciones | **SÍ** | `TESTING.md §5` | sistema |
| prueba de validación por corrección | **SÍ** | `PATCH-REGISTRY`, 16+ entradas | sistema |
| **verificación semántica de una corrección de prosa** | **NO** | ningún artefacto | — |
| **comparación antes/después de un artefacto `.md`** | **NO** | — | — |
| **regresión automática sobre prosa** | **NO** | — | — |

**Y la observación de MIG-07.5 era correcta en un punto que se mantiene:** un hash **no** prueba
corrección semántica. Ningún hash puede. Eso no es un gap de OpenCode, es una limitación de la
clase de prueba.

```
SELF_CORRECTION_LEVEL=L3_BY_EXISTENCE_SYSTEM_DOMAIN
SELF_CORRECTION_LEVEL=L1_DOCUMENT_DOMAIN
SELF_CORRECTION_LEVEL_BY_GUARANTEE=L2_SYSTEM / L0_DOCUMENT
```

**`SELF_CORRECTION_MODEL=L0` es `EXAGERADO`.** `SUPPORTED`

---

## 11. FASE 11 — `INDEPENDENCE_MODEL`

MIG-07.5 afirmó `L0`. Verificación:

| Campo | Ficheros que lo contienen |
|---|---:|
| `VERIFIED_BY` | **0** |
| `AUTHORED_BY` | **0** |
| `REVIEWED_BY` | **0** |
| `Autor:` | **0** |
| `Preparado por` | **0** |
| `REVIEWER` | **1** |

Y: `R1-COLLECTOR-INDEPENDENT-REVIEW-*.md` existen (2), uno con verificación por AST sin
allowlist. **La práctica de revisión independiente existe y está documentada. La independencia no
es acreditable, porque no hay campo que la acredite.**

**Distinción que MIG-07.5 no hizo y que es la correcta:**
*otra fase* ≠ *actor independiente*. Dos revisiones escritas por el mismo agente en sesiones
distintas son **dos artefactos, un actor**. `SUPPORTED`

```
INDEPENDENCE_LEVEL=L1_PRACTICE_WITHOUT_ATTESTATION
INDEPENDENCE_MINIMUM_DEMONSTRABLE=artifact from a distinct actor
INDEPENDENCE_CURRENTLY_DEMONSTRABLE=NO
```

**`L0` es correcto en sustancia** (no hay separación acreditada) **pero `NOT_PROVEN` es la etiqueta
epistémica correcta**, y además hay un nivel intermedio (`L1_PRACTICE_WITHOUT_ATTESTATION`) que
MIG-07.5 no contempló. `SUPPORTED`

---

## 12. FASE 12 — RQ-7 (verificar referencias `fichero:línea`)

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Realmente falta? | **SÍ** | Lo demostré: MIG-07.5 citaría `:43` cuando era `:23`, en 4 lugares, y ningún escaneo de caracteres lo detecta |
| ¿Existe parcialmente? | **SÍ** | `tools/validate_rx550_final.py` valida rutas y hashes del sistema; los censos congelados validan inventario. No validan citas |
| ¿Implementable con las herramientas existentes? | **SÍ** | Un script que resuelva cada `ruta:línea` y compare. `read` + `grep`. Además `ctx.tool.hook("execute.before")` (§14) |
| Falsos positivos | **ALTOS**: `fichero:línea` en citasIPs o en tablas generated; sed after editing |
| Falsos negativos | **ALTOS**: una cita correcta puede apuntar a la evidencia equivocada; el validador comprueba que la línea existe, no que respalde la afirmación |

**Veredicto: `RQ-7` es `USEFUL` pero no `REQUIRED` por sí solo.** Un validador de citas garantiza
que la referencia exista, **no** que la evidencia respalde la conclusión. Presentado como
requisito, sugiere una garantía que no da. `SUPPORTED`

```
RQ7_STATUS=USEFUL_BUT_INSUFFICIENT
RQ7_ADDITIONAL_REQUIREMENT=la cita debe ir acompañada del texto citado, no solo del puntero
```

---

## 13. FASE 13 — PROBLEMA DE CORRUPCIÓN TEXTUAL

| Métrica | MIG-07.5 | Verificado en esta revisión |
|---|---|---|
| Ocurrencias documentadas | ≥13 | **`NOT_VERIFIABLE` fuera de la transcripción.** 0 en artefactos |
| Estado actual | CJK=0 | **CJK=0, camelCase=1** (medido en los 7 artefactos) |
| Ese camelCase | `dePersistir` | **reproducido, línea 23** |
| Correcciones que generan defectos | 1 caso (O-02) | **2 casos**: O-02 y Q-1..Q-3 de MIG-07.5 §6.4 |
| Detector versionado | no | **no — confirmado** |
| Cobertura del detector | ninguna | **confirmada: 6 docs no examinados en MIG-07.5** |
| Regla que obligue a corregir | no | **no para `.md`; sí para sistema** |
| Métrica de recurrencia | no existe | **no existe — confirmado** |

**Confirmado en lo esencial, y se añade un dato: la segunda autocorrección generadora de defectos
ocurrió dentro del propio MIG-07.5.** El patrón es más estable de lo que se registró. `OBSERVED`

**Y una limitación que reaffirma el principio central del encargo:** el conteo de ≥13 **solo
existe en la transcripción de la sesión**. Ningún artefacto lo registra. **Por tanto «13
ocurrencias» es `AUTHOR_REASONING_ONLY` y no puede usarse como evidencia.** `SUPPORTED`

---

## 14. FASE 14 — VERIFICACIÓN DE OPENCODE V2

Documentación oficial, reverificada hoy.

| Capacidad | Estado | Verificación |
|---|---|---|
| `permissions` (`allow`/`deny`/`ask`) | `DOCUMENTED` | HTTP 200, array ordenado, última regla gana |
| `ctx.permission.hook("evaluate")` puede asignar `effect` | `DOCUMENTED` | texto literal: *«A hook may change `effect` to `allow`, `ask`, or `deny`»* |
| `ctx.tool.hook("execute.before")` inspecciona entrada | `DOCUMENTED` | *«Inspect or replace tool input before execution»* |
| `ctx.shell.hook("create.before")` | `DOCUMENTED` | puede modificar `command`/`cwd`/`timeout`/`env` |
| `policies` | `DOCUMENTED`, `experimental` | *«authored under `experimental.policies`»* |
| `steps` | `NOT_DOCUMENTED` | HTTP **404** confirmado |
| autodiagnóstico metodológico | `NOT_DOCUMENTED` | ninguna página lo describe |
| verificación del trabajo propio | `NOT_DOCUMENTED` | ninguna |
| `agents` / `subagent` | `DOCUMENTED` | HTTP 200 |

**Distinción exigida por el encargo — y aquí hay un matiz que MIG-07.5 no hizo:**
`DOCUMENTED` ≠ `OBSERVED_LOCALLY`. **El proyecto no usa ninguna de estas capacidades**: no hay
`.opencode/`, no hay `opencode.jsonc`, no hay plugins. Verificado. `OBSERVED`

Por tanto: **la capacidad de enforcement estructural (`permission hook → deny`) está documentada
pero no está presente en este proyecto.** `SUPPORTED`

---

## 15. FASE 15 — RESULTADO ADVERSARIAL

```
MIG-07.6=VERIFYING

SELF_METHODOLOGY_GAP_RESULT=PARTIALLY_CONFIRMED

O01_RESULT=CONFIRMED_AND_REPRODUCED
O01_LINE=23   (MIG-07.5 decía 43; error corregido en MIG-07.5 §6.4)
O01_RULE_EXISTS_FOR_THIS_DOMAIN=NO

FALSE_POSITIVES_CONFIRMED=7        (de 9 verificados)
FALSE_POSITIVES_PARTIALLY_WRONG=1  (FP-4)
FALSE_POSITIVES_REFUTED=0
FALSE_NEGATIVES_FOUND=5

AUTHOR_REASONING_ONLY=9
INDEPENDENTLY_VERIFIABLE=11
PARTIALLY_INDEPENDENT=6
NOT_VERIFIABLE=2

COUNTEREVIDENCE_FOUND=YES   (6 documentos normativos nunca examinados)
MIG-07.5_CLAIMS_REFUTED=3
MIG-07.5_CLAIMS_NARROWED=4
MIG-07.5_CLAIMS_UPHELD=6

CURRENT_DETECTION_LEVEL=DOMAIN_DEPENDENT
CURRENT_DETECTION_LEVEL_MAX_BY_EXISTENCE=L3
CURRENT_DETECTION_LEVEL_MAX_BY_GUARANTEE=L2
CURRENT_DETECTION_LEVEL_DOCUMENT_DOMAIN=L1
CURRENT_DETECTION_LEVEL_COVERAGE=L0

SELF_CORRECTION_LEVEL=L3_SYSTEM / L1_DOCUMENT   (MIG-07.5 decía L0 -> REFUTED)
SELF_CORRECTION_LEVEL_BY_GUARANTEE=L2_SYSTEM / L0_DOCUMENT

INDEPENDENCE_LEVEL=L1_PRACTICE_WITHOUT_ATTESTATION   (L0 correcto en sustancia, etiqueta distinta)
INDEPENDENCE_L4=NOT_PROVEN
INDEPENDENCE_L5=NOT_PROVEN

RQ7_STATUS=USEFUL_BUT_INSUFFICIENT

L0=PROVEN   L1=PROVEN   L2=PROVEN(debil)   L3=PROVEN(existencia)   L4=NOT_PROVEN   L5=NOT_PROVEN

KNOWN_DEFECT=CONFIRMED      # dePersistir, MIGRATION-…:23
CORRECTION=DEFERRED

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

### Las 3 refutaciones de MIG-07.5

| # | Afirmación de MIG-07.5 | Refutación | Evidencia |
|---|---|---|---|
| **R1** | trigger 6 `SELF_CORRECTION_NOT_VERIFIED` → `DETECTION_METHOD: ninguno` | **FALSA.** Hay regla escrita con 6 precondiciones que prohíbe literalmente el error de O-01 | `TESTING.md §5` |
| **R2** | `SELF_CORRECTION_MODEL=L0` | **EXAGERADO.** 7 mecanismos de verificación existen; 3 son ejecutables y vinculan corrección↔prueba por hash | `ROLLBACK.md §4`, `PATCH-REGISTRY`, 50–142 documentos |
| **R3** | `CURRENT_DETECTION_LEVEL=L3_MAX` | **ENGANOSO por garantía.** L3 por existencia; L2 por garantía metodológica. `L3_MAX` sin matriz sugiere cobertura inexistente | O-01, FN-1 |

### Las 4 acotaciones

| # | Afirmación | Acotación |
|---|---|---|
| **A1** | «0 de 18 señales `EXISTENTE`» | Hay ≥5 señales con soporte escrito: `TESTING.md §5`, `ROLLBACK.md §4`, convenciones del registry, `NON_AUTHORITATIVE` del collector, `ESCALATION` del router. **No son `EXISTENTE` (no son automáticas) pero sí son más que `AD_HOC`** |
| **A2** | «los 19 casos sin regla que obligue» | MIG-07/E1 y X-1 **sí** tienen regla que obliga a escalar. 2 de 19 mal clasificados |
| **A3** | `L4`/`L5` = nivel 0 | `NOT_PROVEN` ≠ `L0`. Distinción epistémica que el modelo no tiene para estos niveles |
| **A4** | `RQ-7` como requisito | `USEFUL_BUT_INSUFFICIENT`: verificar que la línea existe no prueba que la evidencia respalde la conclusión |

---

## 16. FASE 16 — REGLA DE HONESTIDAD

**No puedo determinar `CONFIRMED` ni `REFUTED`.**

- **No `REFUTED`**: el gap es real y reproducible (O-01, los 5 triggers sin método de detección,
  la ausencia total de campos de identidad). El hallazgo central de MIG-07.5 **se sostiene**.
- **No `CONFIRMED`**: la afirmación era **global** («no existe ningún mecanismo») y es
  **falsa en el ámbito de sistema**: hay tres mecanismos escritos, uno de ellos con 6
  precondiciones, que MIG-07.5 nunca examinó. Y **no puedo demostrar la parte que sí importa**
  —que el gap persiste en el dominio de artefactos— con independencia de autoría, porque soy el
  mismo agente.

```
SELF_METHODOLOGY_GAP_RESULT=PARTIALLY_CONFIRMED
```

**Y el resultado más honesto de esta revisión es sobre la revisión misma:**

> La revisión Noel puede ejecutarse mientras el revisor sea el autor. Cada vez que la intenté,
> produje una clasificación de confianza, no una clasificación de poder. Las 2 autocorrecciones
> que producí (FP-4 parcial, y el hallazgo de los 6 documentos) son ellas mismas actos de
> razonamiento no verificado, tal como RQ8 ya anticipaba.

**El instrumento de independencia no existe en el sistema. Es L4 y es `NOT_PROVEN`.**

---

## 17. FASE 17/18 — CAMBIOS Y DEFECTO CONOCIDO

```
KNOWN_DEFECT=CONFIRMED
  artefacto: 01-AUDITORIA/MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md
  linea: 23
  texto: "antes dePersistir,"  -> debe ser "antes de persistir,"
  sha256 del artefacto: 575c7957ed2a2faabd79073690e0d97113d32c3d4061b6398a4acf9405ee53aa
  detectado: 2026-09-26T01:16Z
  no corregido: 2026-09-26T04:20Z  (5 fases)

CORRECTION=DEFERRED
MOTIVO=no existe mecanismo de versionado de artefactos de auditoria
REQUISITO_PARA_CORREGIR=una nueva version/artefacto que preserve el original y su hash
```

**Cualquier corrección deberá producir un artefacto nuevo que:**
1. preserve el original `575c7957…` sin tocar
2. registre la corrección como entrada trazable con su propia fecha y hash
3. no edite el original en el sitio

**Ese mecanismo no existe y no se inventa aquí.** Es la decisión pendiente del usuario.

### Verificación de no-modificación

```
ARCHIVOS_MODIFICADOS=0
ARCHIVOS_CREADOS=1   (este informe)
STAGED=360  (sin cambio)
HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5  (sin cambio)
COMMITS=0  PUSHES=0
UNTRACKED_FUERA_01_AUDITORIA=0
.opencode/=NO   STATE/=NO
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
```

**Artefactos MIG-07/07.5 no modificados, incluido MIG-07.5 con sus defectos.** `OBSERVED`
