# MIG-07.9 — PROVENANCE Y LEGITIMIDAD DE REGLAS

> Artefacto nuevo de auditoría. No modifica ningún documento previo.
> No implementa nada. Ninguna regla descubrimiento se convierte en norma.
> `KNOWN_DEFECT` (`dePersistir`) permanece `CONFIRMED` / `CORRECTION=DEFERRED`.

```
DOCUMENT_ID=MIG-07.9-PROVENANCE-AND-RULE-LEGITIMACY
CREATED_UTC=2026-09-26T06:30:00Z
TYPE=RULE_PROVENANCE_AUDIT
SELF_PROVENANCE_DEFECT=FOUND        # ver §4 — método de rastreo con universo incompleto
MIG-07.9=VERIFYING
PROMOTION=BLOCKED
IMPLEMENTATION=NOT_EXECUTED
```

Clasificación: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `NOT_PROVEN` · `CONFLICT`
Naturaleza: `HECHO` · `INFERENCIA` · `HIPÓTESIS` · `REGLA` · `NORMA` · `CRITERIO_OPERATIVO`

---

## 1. RESUMEN

**El hallazgo central es un defecto de mi propio método, no del proyecto.**

Definí el «corpus previo» para rastrear la procedencia de reglas usando `git ls-files '*.md'`.
Eso **excluía 39 de 291 documentos (13%)** en el momento del rastreo, incluida toda la carpeta `OWNERSHIP-AUDIT-HOST-C/`,
el censo, el router y el registro de decisiones.

**Consecuencia medida:** el término `sin allowlist` aparecerá «0 veces en el corpus previo» y lo
habría clasificado como `INVENTED_RULE`. **Aparece 2 veces en documentos preexistentes.**
Reintroduje, como descubrimiento, una técnica que el proyecto ya usaba. `OBSERVED`

**Ironía que no es retórica:** el mismo error es la cuarta repetición del patrón FN-1 — *búsqueda
dirigida que no declaró su universo*. Y lo cometí en la fase cuyo objeto es **la procedencia**.

| # | Hallazgo | Clasificación |
|---|---|---|
| R-1 | 10 reglas inventadas en MIG-07.5–07.8, **0 en el corpus previo** | `OBSERVED` |
| R-2 | 4 candidatos re-descubiertos que **ya existían** y mi rastreo excluyó | `OBSERVED` |
| R-3 | `D14`/`D15` son **colisión de espacio de nombres** con IDs de pregunta preexistentes | `OBSERVED` |
| R-4 | OpenCode V2: `instructions` de config es **inerte** («accepted but does not load its entries») | `DOCUMENTED` |
| R-5 | OpenCode V2: las instrucciones se **combinan sin resolver conflictos** — explícito | `DOCUMENTED` |
| R-6 | La precedencia documentada es **de configuración**, no de instrucciones | `DOCUMENTED` |
| R-7 | El collector tiene **38 estados embebidos como literales**, sin enumeración canónica | `OBSERVED` |
| R-8 | «control negativo» NO es un concepto nuevo: `TESTING.md §5` ya lo exige | `OBSERVED` |
| R-9 | Hash de MIG-07.8 reportado como vacío; **585 líneas, no 658** | `OBSERVED` |

---

## 2. RQ-1 — FORMAS EN QUE UNA REGLA PUEDE APARECER

**Hipótesis a falsar:** «una regla contiene “debe” u “obligatorio”». **Refutada.** Medición sobre
256 documentos versionados + 4 de MIG-07:

| Forma | Ocurrencias | Ficheros | ¿Contiene «debe»? |
|---|---:|---:|---|
| `OBLIGACION` (`debe`/`should`/`must`/`requiere`) | **530** | 148 | sí |
| `GATE` (`GATE`/`ABORT`) | 270 | 72 | no |
| `SUPUESTO` (`supone`/`asume`) | **68** | 38 | **no** |
| `CRITERIO` | 91 | 46 | no |
| `CONDICION` (`solo si`) | 61 | 40 | no |
| `PROHIBICION` | 39 | 29 | no |
| `TABLA_NORMATIVA` (fila con regla en 3ª columna) | **32** | 7 | no |
| `IMPERATIVO` (`Nunca`) | 19 | 14 | no |
| `CONVENCION` | 13 | 13 | no |
| **`CODIGO_ENFORCE`** (`assert*`) | **699** | 29 `.py` | **no — y en código** |
| **`COMENTARIO_NORMATIVO` en código | **4** | 29 `.py` | no |

**Dos formas que NO contienen la palabra y dominan por volumen:**
1. **`assert*` — 699 ocurrencias.** Una regla expresada como aserción.
2. **Supuestos — 68**, que no se declaran como regla pero **condicionan** toda decisión que las use.

**Clasificación de formas (propuesta, `AGENT_INFERENCE` salvo la primera fila):**

| # | Forma | Naturaleza |
|---|---|---|
| F1 | Texto normativo explícito | `NORMA` si tiene autoridad; `REGLA` si no |
| F2 | Condición de gate | `CRITERIO_OPERATIVO` |
| F3 | Criterio de cierre / promoción | `CRITERIO_OPERATIVO` |
| F4 | Fila de tabla con columna «regla de uso» | `REGLA` |
| F5 | Convención / nomenclatura | `REGLA` |
| F6 | Prohibición | `NORMA` si con autoridad |
| F7 | **Aserción de test** | `REGLA` **no documentada** |
| F8 | **Literal de código** | `REGLA` **no documentada** |
| F9 | **Supuesto no declarado** | `INFERENCIA` que condiciona |
| F10 | **Constante embebida** | `REGLA` **no documentada** |

**F7–F10 no tienen columna en ningún documento normativo.** `OBSERVED`

---

## 3. RQ-2/RQ-3 — FUENTE ≠ AUTORIDAD

### 3.1 `SOURCE_TYPE`: el proyecto ya tiene un vocabulario

No inventé las categorías. El router y el censo ya clasifican documentos por función:

| Categoría del encargo | Equivalente existente | Fuente | Cobertura |
|---|---|---|---|
| `PROJECT_NORM` | `REFERENCE` (censo) | `DOCUMENTATION-CENSUS.md:92` | 3 docs: `AGENTS.md`, `IMPLEMENTATION-SAFETY-RULES`, `ESTADOS-ES-EN` |
| `PROJECT_PROCEDURE` | `PROCEDURE` (censo) | censo | ¿cuenta? `UNKNOWN` |
| `CODE_ENFORCEMENT` | — | — | **no existe** |
| `AGENT_INFERENCE` | — | — | **no existe** |
| `AGENT_MEMORY` | — | — | **no existe** y **no puede haberlo** (§9) |
| `USER_INSTRUCTION` | — | — | **no existe** |
| `EXTERNAL_SOURCE` | `EXTERNAL_SOURCE` (censo) | censo:90 | 10 docs |
| `TEST` | `TEST` (censo) | censo | 2 docs |
| `EXPERIMENTAL_EVIDENCE` | `RAW_EVIDENCE` (censo) | censo:91 | **1321** |

**6 de 10 categorías ya existen en el censo. 4 no existen, y 3 de esas 4 son precisamente las que
importan para MIG-07** (`CODE_ENFORCEMENT`, `AGENT_INFERENCE`, `USER_INSTRUCTION`). `OBSERVED`

**Y el hallazgo de RQ-3:** el censo clasifica `ESTADOS-ES-EN.md` como `REFERENCE` — la misma clase
que `AGENTS.md`. **Fuente y autoridad se tratan como la misma dimensión en el propio censo.** El
proyecto no tiene el concepto «fuente sin autoridad». `SUPPORTED`

### 3.2 Inventario de reglas críticas con fuente y autoridad separadas

| RULE_ID | Regla | FUENTE | Ubicación | Hash fuente | TIPO FUENTE | AUTORIDAD | Alcance | Vigencia |
|---|---|---|---|---|---|---|---|---|
| **R-A1** | «Un problema sólo pasa a `RESOLVED` con prueba reproducible, identidad de GPU, config exacta, resultado positivo y negativo, y rollback documentado» | `TESTING.md §5` | `:70-76` | sí | `PROJECT_NORM` | **NO RESUELTA** — 6 precondiciones sin mecanismo de aplicación | sistema | `CURRENT` |
| **R-A2** | «No convertir `UNKNOWN`/`NOT_AVAILABLE`/`CONFLICT` en `PASS` por inferencia» | `AGENTS.md:106` | `:93-116` | `d5fa85a4…` | `PROJECT_NORM` | **PARCIAL** — instrucción a modelo, no enforcement | evidencia | `CURRENT` |
| **R-A3** | «Separar hecho observado / interpretación / hipótesis / afirmación causal» | `AGENTS.md:108-112` | ídem | ídem | `PROJECT_NORM` | **PARCIAL** | evidencia | `CURRENT` |
| **R-A4** | «`RESOLVED` = implementada **y verificada en el alcance indicado**» | `PATCH-REGISTRY:16` | `:14-27` | `2a52ee76…` | `PROJECT_NORM` | **PARCIAL** — 16+ aplicaciones | correcciones | `CURRENT` |
| **R-A5** | «La ausencia de un error en una instantánea se registra como `NOT_REPRODUCED`, no como `RESOLVED`» | `TESTING.md §5` | `:70-76` | — | `PROJECT_NORM` | **PARCIAL** | sistema | `CURRENT` |
| **R-A6** | «`NO_GO` nunca significa “intentarlo de nuevo”. `ABORT` nunca autoriza una acción» | `C1-ISOLATION-DESIGN-v1.0.md:53` | `:53` | — | `PROJECT_NORM` | **PARCIAL** | C1 | `CURRENT` |
| **R-A7** | «`CONFLICT` → devolver ambas fuentes. **No elegir**» | `DOCUMENTATION-ROUTER:78` | `:78` | — | `PROJECT_NORM` | **PARCIAL** — y no ejecutada para `VOCABULARY` | conflictos | `CURRENT` |
| **R-A8** | «Un diagrama es una vista derivada; el texto canónico prevalece» | `DIAGRAMAS/README:29` | `:29` | `bff01cb7…` | `PROJECT_NORM` | **`DRAFT/CONFLICT`** | documentación | `CURRENT` pero `DRAFT` |
| **R-A9** | «`VALIDADO` no significa `SUPPORTED` si el protocolo no lo permite» | `ESTADOS-ES-EN.md §Regla` | `:40` | `c858b5ae…` | `PROJECT_NORM` | **NO RESUELTA** — V6 sin `STATUS` y en lista de no-fuente-de-estado | vocabulario | `CONFLICT` |
| **R-A10** | «El texto canónico prevalece» (regla de `CONFLICT` en V6) | `ESTADOS-ES-EN.md:35` | `:35` | ídem | `PROJECT_NORM` | **CIRCULAR** — no declara cuál es el canónico | vocabulario | `CONFLICT` |
| **R-A11** | «Los localizadores `/tmp` perdidos se escriben `HISTÓRICO / NO VERIFICABLE`, nunca rutas nuevas» | `ESTADOS-ES-EN.md §Regla` | `:44-45` | ídem | `PROJECT_NORM` | `PARCIAL` | documental | `CURRENT` |
| **R-A12** | `GO_C1=NOT_AVAILABLE` | 22 ficheros | `C1-PREFLIGHT*` | — | `PROJECT_PROCEDURE` | **NO EJECUTADO** | C1 | `CURRENT` |

**R-A9, R-A10, R-A12: 3 de 12 reglas críticas sin autoridad resuelta.** `AUTHORITY_CONFLICTS=3+`
(el recuento real es mayor; §3.3)

### 3.3 El conflicto de autoridad, dimensionalizado

`AUTHORITY_CONFLICT=YES`. No por desacuerdo de contenido, sino porque **`SOURCE_TYPE` no
distingue «documento que declara» de «documento al que se obedece»**, y hay 13 declaraciones y 0
mecanismo que diga cuál prevalece. `PRECEDENCE_RULE=NOT_AVAILABLE` (MIG-07.6 §3)

**Y una observación de esta fase:** R-A9 y R-A10 **son reglas del mismo documento** que disputa la
autoridad. Un documento cuya legitimidad está en disputa contiene reglas normativas. **Aplicar
esas reglas sin resolver la disputa es circular.** `SUPPORTED`

---

## 4. RQ-4 — REGLAS INVENTADAS: TRAZA CORREGIDA

### 4.1 El defecto de método, primero

**Lo que hice:** `git ls-files '*.md'` para definir el corpus previo.
**Lo que excluye:** 39 de 291 documentos (13%): toda `OWNERSHIP-AUDIT-HOST-C/`, el censo, el
router, el registro de decisiones, `PATCH-RECOVERY/`, `HOST-C-DIAGNOSTIC-RECONCILIATION/`.
**Por qué importa:** un término ausente de ese conjunto no es «nuevo»; es «no buscado».

**Nota de datación (para que la cifra no se lea sin contexto):** el rastreo se ejecutó **antes**
de que existiera este documento. En ese momento el universo eran 291 `.md` y el conjunto excluido
39 (13%). **Ahora** son 292 y 40 (14%), porque este fichero es el último añadido. La diferencia es
1 fichero: este. `UNKNOWN`→`OBSERVED` por datación, no por corrección.

### 4.2 Traza con el universo correcto (281 documentos previos)

| Regla / término | Corpus previo | 1ª aparición | Clasificación |
|---|---:|---|---|
| `Baldwin` | **0** | `MIG-07.7:451` | **`INVENTED_RULE`** |
| `GAP_CONFIRMED` | **0** | `MIG-07.7:449` | **`INVENTED_RULE`** |
| `SELF_METHODOLOGY_GAP` | **0** | `MIG-07.5:30` | **`INVENTED_RULE`** |
| `AUTODIAGNOSTIC_COVERAGE` | **0** | `MIG-07.7:478` | **`INVENTED_RULE`** |
| `SEARCH_COMPLETENESS_PROVEN` | **0** | `MIG-07.7:280` | **`INVENTED_RULE`** |
| `PROVENANCE_OF_ACTOR` | **0** | `MIG-07.7:327` | **`INVENTED_RULE`** |
| `I1r` | **0** | `MIG-07.8:522` | **`INVENTED_RULE`** |
| «fallo negativo control» | **0** | `MIG-07.7:598` | **`UNSUPPORTED_RULE`** — ver §4.4 |
| «control negativo» | **0** | `MIG-07.8:28` | **`UNSUPPORTED_RULE`** |
| «declarar el universo» | **0** | `MIG-07.7:487` | **`INVENTED_RULE`** |
| `sin allowlist` | **2** | `MIG-07.6:278` | **`LEGITIMATE_RULE` re-descubierta** — mi rastreo falló |
| `escaneo AST` | **1** | `MIG-07.6:280` | **`LEGITIMATE_RULE` re-descubierta** |
| `D14` | 6 | `MIG-07.7:46` | **`NAMESPACE_COLLISION`** — ver §4.3 |
| `D15` | 4 | `MIG-07.7:47` | **`NAMESPACE_COLLISION`** |

### 4.3 `D14`/`D15`: no es re-descubrimiento, es colisión

Los 6 y 4 previos son `H12-2-D14` / `H12-2-D15`: **identificadores de pregunta** en
`FASE-H12-2-WSI-DOCUMENTATION`. Yo los usé para «autodiagnóstico» y «integridad de referencias».

**Introduje un token que ya significa otra cosa en el proyecto, en el mismo eje de clasificación.**
Eso es peor que inventar un término: es reutilizar un identificador existente con semántica
distinta. `NAMESPACE_COLLISION`. `SUPPORTED`

### 4.4 «Control negativo» no era nuevo

MIG-07.7 §19 afirmó que el requisito «fallo negativo control» no lo había mencionado ninguna fase
anterior. **`TESTING.md §5` lo exige**: *«resultado positivo **y negativo explícito cuando
aplique**»*. Yo lo presenté como descubrimiento. `UNSUPPORTED_RULE` — no invéntala, la **re-presenté**
como nueva. `SUPPORTED`

### 4.5 Cuántas times se reintrodujo algo preexistente

Con el universo correcto: **2 de 14 candidatos** son re-descubrimientos (`sin allowlist`,
`escaneo AST`). Con el rastreo inicial: **4** (más `D14`, `D15`).

**Y ambas re-descubricionesajaron en FN-3, que presenté como «hallazgo falso negativo».**
No era un falso negativo del inventario: era un hallazgo mío. `SUPPORTED`

---

## 5. RQ-5 — INFERENCIA → NORMA

### 5.1 La cadena medida, caso por caso

| Caso | Observación | Interpretación | Inferencia | Regla | ¿Se perdió la etiqueta? |
|---|---|---|---|---|---|
| **`Baldwin`** | 3 ejemplos construidos por mí | «el eje limitante es el que sostiene» | «esto es una regla» | llamada «regla de Baldwin» + «la evidencia impone» | **SÍ, dos veces**: nombre y «impone» |
| **`GAP_CONFIRMED`** | 11 dominios con ≥1 dimensión `N` | «eso es un gap» | «la regla es: si falta el eje limitante, es gap» | aplicada a 11 dominios | **SÍ** — aplicada sin registro de derivación |
| **`NO_AUTOMATIC_GAP`** | 5 contraejemplos | «no puede automatizarse» | «debe ser manual» | propuesta de reemplazo | **NO** — quedó como `NOT_ESTABLISHED` |
| **«declarar el universo»** | FN-1 (6 docs no vistos) | «el fallo fue de universo no declarado» | «hay que declarar el universo» | convertida en requisito metodológico | **PARCIAL** — se usó, pero sin fuente |
| **5 dimensiones A–E** | «existencia ≠ ejecución ≠ cobertura» | observación válida | «son 5 ejes, no una escala» | `L0_L5_AS_SCALE=RETIRED` | **SÍ** — `RETIRED` es un verbo de norma aplicado a un modelo propio |
| **«control negativo»** | `TESTING.md §5` lo exige | — | — | presentado como descubrimiento | **SÍ** |

### 5.2 Recuento

```
CADENAS_INFERENCIA_NORMA_IDENTIFICADAS=6
  CON_PERDIDA_DE_ETIQUETA=4   (Baldwin, GAP_CONFIRMED, L0-L5 RETIRED, control negativo)
  SIN_PERDIDA=1               (NO_AUTOMATIC_GAP quedó como NOT_ESTABLISHED)
  PARCIAL=1                   (declarar el universo)
```

**El patrón no es aleatorio:** en 4 de 6, la pérdida de etiqueta ocurrió en el **momento de
nombrar** la regla, no en el de derivarla. Ponerle nombre la convirtió en norma. `SUPPORTED`

### 5.3 El caso más grave: `L0_L5_AS_SCALE=RETIRED`

`RETIRED` es un verbo de estado normativo (`ESTADOS-ES-EN.md` define `DRAFT` como «Documento o
vista provisional» y `CONFLICT`). Lo apliqué a un **modelo analítico que yo mismo construí** en la
fase anterior. **Usé el vocabulario del proyecto para deponer una construcción mía, dándole
estatus de decisión normativa sobre algo que nunca tuvo autoridad.** `SUPPORTED`

**Este es el patrón completo de la migración resumido en un verbo.** `CONFLICT`

---

## 6. RQ-6 — PROCEDENCIA TEMPORAL

### 6.1 ¿El proyecto distingue vigencia?

| Condición | ¿Existe término? | Dónde | `OBSERVED` |
|---|---|---|---|
| `CREATED_AT` | **NO** para documentos | `Fecha:` en algunos, ausente en 241 de 291 | `OBSERVED` |
| `VALID_FROM` | **NO** | — | `NOT_AVAILABLE` |
| `VALID_TO` | **NO** | — | `NOT_AVAILABLE` |
| `SUPERSEDED_BY` | **PARCIAL** | `SUPERSEDED`/`STALE` en censo §7 y `DOCUMENTATION-GAPS` | `OBSERVED` |
| `OBSOLETE` | **SÍ** | `PROBLEM-STATUS-FINAL` y `PATCH-REGISTRY` | `OBSERVED` |
| `HISTORICAL` | **SÍ** | 16+ docs | `OBSERVED` |
| `CURRENT` | **SÍ** | columna `TEM` del router (`CUR`/`MX`) | `OBSERVED` |
| `SNAPSHOT` | **SÍ** | V6 | `OBSERVED` |

**4 de 8 condiciones existen; 4 no.** Las que faltan (`VALID_FROM`/`VALID_TO`) son las que
permitirían responder «¿era válida cuando se aplicó?». `SUPPORTED`

### 6.2 Reglas derivadas de un host y aplicadas a otro

| Regla | Host de origen | Aplicada a | Riesgo |
|---|---|---|---|
| `P0=B__CONTAMINATED_REQUIRES_ISOLATION` | HOST-A (`lex-luthor`, 7.2.6) | gate de C1 en HOST-C | **ALTO** — MIG-04 |
| `C2 Mesa 26.2.2/26.2.3/25.3.2` | HOST-B y HOST-A mezclados | estado de Mesa | ALTO — router `C2` |
| `C3 kernel 7.2.6/7.2.4/6.18.2/7.1.3` | 4 hosts | identidad de kernel | ALTO — router `C3` |
| `C4 card1 vs card2` | captura HOST-B | scripts en HOST-C | ALTO — router `C4` |
| `PROBLEM-STATUS-FINAL` completa | HOST-B | declarado «current problem matrix» por `AGENTS.md` | **ALTO** — MIG-03 |

**El router ya lo detectó**: `C2`/`C3`/`C4` tienen precedencia declarada («No se funden»). `C1` y
`C5` tienen «No». **5 conflictos de host, 3 con regla y 2 sin ella.** `OBSERVED`

`TEMPORAL_CONFLICTS=5`

### 6.3 Regla heredada de fase anterior sin verificar

**La regla de identidad por `cardN` → `vendor:device`** se aplicó en `PATCH-REGISTRY P-001` sobre
HOST-B. El host vivo es HOST-C con `card1`, no `card2`. La regla es correcta; **su premisa de host
no se revalidó**. `SCOPE_UNKNOWN` — no `IN_SCOPE`. `SUPPORTED`

---

## 7. RQ-7 — ALCANCE

### 7.1 Separación `RULE_EXISTS` / `RULE_APPLIES_HERE`

| Regla | Existe | Aplica en | Clasificación de alcance |
|---|:-:|---|---|
| R-A5 «ausencia de error ≠ `RESOLVED`» | sí | **sistema** | `OUT_OF_SCOPE` si se aplica a un `.md` |
| R-A1 6 precondiciones | sí | **sistema** | `OUT_OF_SCOPE` para documentación |
| R-A2 «no convertir en `PASS`» | sí | evidencia | **`SCOPE_UNKNOWN`** — ¿cubre documentos? |
| R-A4 `RESOLVED` = verificado | sí | correcciones | `IN_SCOPE` para código, `SCOPE_UNKNOWN` para prosa |
| R-A7 «`CONFLICT` → no elegir» | sí | conflictos documentales | `IN_SCOPE` |
| R-A9/R-A10 (V6) | sí | vocabulario | `SCOPE_UNKNOWN` — la autoridad de V6 está en disputa |
| R-A12 `GO_C1` | sí | C1 | `IN_SCOPE` |

### 7.2 El hallazgo

**Las 3 reglas mejor escritas del proyecto (`TESTING.md §5`, `PATCH-REGISTRY`, `ROLLBACK.md §4`)
tienen alcance de sistema. Aplicadas a documentación, serían `OUT_OF_SCOPE`.**

Y eso es exactamente lo que ha pasado: `TESTING.md §5` se usó en MIG-07.6/07.7 para evaluar
correcciones de prosa (O-01), cuando su alcance declarado es `identidad de GPU`, `configuración
exacta`, `rollback`. `SCOPE_CONFLICTS=3`

**No es un abuso — es una extensión de alcance que nadie declaró.** Y RQ-3 dice que
`AUTHORITY_SCOPE` está sin resolver. `SUPPORTED`

---

## 8. RQ-8 — DERIVACIÓN

| Tipo | ¿Existe? | Ejemplo | Puede tener autoridad propia? |
|---|---|---|---|
| `SOURCE_RULE` | sí | R-A1 | — |
| `DERIVED_RULE` | sí | «6 precondiciones» → «criterio de cierre de docs» | **NO automáticamente** |
| `COMPOSED_RULE` | sí | `GO`/`NO_GO`/`ABORT` | **NO automáticamente** |
| `INFERRED_RULE` | sí | Baldwin, `GAP_CONFIRMED` | **NO** — por definición |
| `HEURISTIC` | **difícil de distinguir de inferencia** | «buscardirected primero» | **NO** |
| `UNKNOWN` | — | — | — |

### 8.1 El ejemplo abstracto del encargo, aplicado

> R1: «el resultado debe tener evidencia reproducible» (R-A4)
> R2: «cualquier documento sin hash no puede utilizarse»

**R2 NO se sigue de R1.** R1 habla de *evidencia de un resultado*; R2 habla de *integridad de un
artefacto*. Saltan tres eslabones: reproducible ≠ hasheado; resultado ≠ documento; y «no puede
utilizarse» es un **gate**, es decir una decisión con consecuencia.

**Las condiciones necesarias para que una regla derivada sea normativa** (propuesta,
`AGENT_INFERENCE`, no norma):

| # | Condición | ¿Existe mecanismo? |
|---|---|---|
| 1 | La derivación está escrita y es auditable | **NO** |
| 2 | La regla madre está vigente | `PARTIAL` (§6) |
| 3 | La alcance de la derivada está declarado | **NO** |
| 4 | La derivada fue revisada por alguien distinto | **NO** — `P4=0` |
| 5 | Existe un mecanismo que la imponga | **NO** |

**5 de 5 ausentes o parciales. Ninguna regla derivada de MIG-07 puede ser norma.** `SUPPORTED`

**Y ese es el argumento por el que este documento NO convierte nada en norma**, aunque lo
recomiende. `PROMOTION=BLOCKED`

---

## 9. RQ-9/RQ-18 — CONFLICTOS Y MEMORIA

### 9.1 Grupos de reglas en conflicto

| Grupo | Reglas | Tipo de conflicto | ¿Mecanismo que lo resuelve? |
|---|---|---|---|
| **G1** vocabulario | R-A9, R-A10, V3, `AGENTS.md §Evidence` | **autoridad** | **NO** — `PRECEDENCE_RULE=NOT_AVAILABLE` |
| **G2** `NOT_EVALUATED`/`FAIL` | V6, `AGENTS.md:102`, `C1-ISOLATION-DESIGN` | **eje** (resultado vs gate) | parcial |
| **G3** host | C1–C5 del router | **temporal** | 3 de 5 con regla |
| **G4** `UNKNOWN` | V1/V2, V3, V4 | **eje** | **NO** |
| **G5** alcance de `TESTING.md §5` | sistema vs documentos | **alcance** | **NO** |
| **G6** OpenCode instrucciones | AGENTS.md global vs proyecto vs sesión | **plataforma** | **NO, por diseño** (§10) |

**6 grupos. 1 resuelto parcialmente (G2), 2 con regla parcial (G3), 3 sin mecanismo (G1, G4, G5),
1 por diseño de plataforma (G6).**

### 9.2 Memoria del agente

**No hay forma de auditar la memoria del agente.** No es una fuente inspeccionable, no tiene
ubicación, y no se puede contrastar. `MEMORY_UNKNOWN` por definición.

**Y hay un caso concreto en esta migración:** afirmé en MIG-07.5 que `/v2/docs/steps` da 404, y lo
verifiqué. Pero afirmé la **nomenclatura V2** (`permissions`, `shell`, `subagent`) en el primer
informe **sin haber consultado la URL V2** — lo hice tras la corrección del usuario. Eso fue
`MEMORY_SUPPORTED` usado como norma, y la corrección lo confirmó. `SUPPORTED`

`MEMORY_USED_AS_CRITERIA=1` (documentado, no oculto)

---

## 10. RQ-10/RQ-11 — REGLAS DE OPENCODE V2 (documentación oficial)

### 10.1 Orden de ensamblado documentado

| # | Fuente | Naturaleza |
|---:|---|---|
| 1 | System prompt del agente o provider | `INSTRUCTION` |
| 2 | Contexto de entorno y fecha | `CONTEXT` |
| 3 | Guía Code Mode, si activa | `INSTRUCTION` |
| 4 | **AGENTS.md global y de proyecto** | `INSTRUCTION` |
| 5 | **`skill`, `reference` y guía MCP** | `INSTRUCTION` |
| 6 | Entradas de instrucción de sesión vía API | `INSTRUCTION` |

> *«These sources are **combined rather than used as overrides**.»* `DOCUMENTED`
> *«OpenCode combines the files and **does not resolve conflicts between them**.»* `DOCUMENTED`

### 10.2 Tres hallazgos que corrigen supuestos

| # | Hallazgo | Evidencia |
|---|---|---|
| **A** | **El campo `instructions` de config es inerte** | *«OpenCode accepts this field but **does not load its entries**; use AGENTS.md»* |
| **B** | **La precedencia documentada es de CONFIGURACIÓN, no de instrucciones** | config: *«from lowest to highest precedence: ~/.config/… → project root → packages/web»* |
| **C** | **V2 no reconoce `CLAUDE.md`** | *«OpenCode V2 recognizes `AGENTS.md` only»* |

**B es exactamente la trampa que el encargo advertía**: el orden de las 6 fuentes es **orden de
ensamblado**, y el propio documento lo dice: *«combined rather than used as overrides»*.
**No hay precedencia entre instrucciones. `priority` = 0 ocurrencias en la página.** `DOCUMENTED`

### 10.3 Clasificación de los modos de resolución (RQ-11)

| Situación | Modo | Base |
|---|---|---|
| Dos `AGENTS.md` contradictorios | **`NO_RESOLUTION`** | *«does not resolve conflicts»* |
| Instrucción de proyecto vs otra fuente | **`NO_RESOLUTION`** | *«combined rather than overrides»* |
| Regla normativa vs inferencia del agente | **`RESOLUTION_BY_MODEL`** | no hay mecanismo; el modelo decide, sin regla que le diga cómo |
| Instrucción de sesión vs regla persistente | **`NO_RESOLUTION`** | ambas se ensamblan |

**De 4 situaciones: 3 `NO_RESOLUTION` y 1 `RESOLUTION_BY_MODEL`.** Y la única que se resuelve es
la que **no tiene mecanismo: la resuelve el modelo por su cuenta.** `SUPPORTED`

**Eso es un gap de OpenCode, y es del tipo D14: no puede detectar que la resuelve por inferencia.**

### 10.4 Una brecha adicional

*«Edits to a nested file are not detected automatically after it loads. Start a new session when
updated text must apply immediately.»* `DOCUMENTED`

**Una regla modificada en caliente no se aplica a la sesión actual.** En este proyecto eso importa:
`AGENTS.md` tiene cambios sin commitear (`AM`). `OBSERVED`

---

## 11. RQ-13/RQ-14 — `PROVENANCE_DEFECT`: DEFINICIÓN DESDE EVIDENCIA

No invento vocabulario. El proyecto ya tiene 4 de las 9 condiciones:

| Condición del encargo | Equivalente existente | Fuente | Cobertura |
|---|---|---|---|
| `NO_SOURCE` | `NOT_AVAILABLE` (censo/V6) | V6:20 | sí |
| `SOURCE_UNKNOWN` | — | — | **NO** |
| `SOURCE_EXISTS_BUT_AUTHORITY_UNKNOWN` | — | — | **NO** |
| `AUTHORITY_CONFLICT` | `CONFLICT` | V2/V6/router | sí, como hecho; **no distingue el de autoridad** |
| `DERIVATION_UNKNOWN` | — | — | **NO** |
| `SCOPE_UNKNOWN` | — | — | **NO** |
| `TEMPORAL_VALIDITY_UNKNOWN` | `HISTORICAL`/`SNAPSHOT`/`STALE` | varios | **parcial**: hay marcas, no hay semántica de vigencia |
| `ACTOR_UNKNOWN` | — | — | **NO** — `P4=0` |
| `VERIFICATION_UNKNOWN` | `NOT_PROVEN` | V1/V2 | sí |

**3 de 9 existen plenamente, 2 parcialmente, 4 no existen. Ninguna cubre `SOURCE` sin `AUTHORITY`.**

### 11.1 Definición mínima desde evidencia (propuesta, no norma)

> **`PROVENANCE_DEFECT`**: una regla cuya **`SOURCE`**, **`AUTHORITY`**, **`SCOPE`**, **`TIME`**
> o **`ACTOR`** no puede determinarse, y que se ha utilizado como criterio de decisión.

**Las 5 condiciones sonnecessaryias por construcción, no por gusto:** cada una cambiaría la
decisión. Sin `SOURCE` no se sabe qué dice; sin `AUTHORITY` no se sabe si obliga; sin `SCOPE` no se
sabe dónde; sin `TIME` no se sabe si vigente; sin `ACTOR` no se puede pedir cuentas. `SUPPORTED`

### 11.2 `SOURCE_PROVENANCE` vs `ACTOR_PROVENANCE`

| Dimensión | Qué existe | Dónde |
|---|---|---|
| `SOURCE_PROVENANCE` | **SÍ** — ruta, línea, hash, fecha | 43 de 252 `.md` con hash; `SOURCE_OF_TRUTH` en 15 |
| `ACTOR_PROVENANCE` | **NO** — 0 campos | `VERIFIED_BY`/`AUTHORED_BY`/`REVIEWED_BY`/`Autor:` = 0 |
| `PROCESS_PROVENANCE` | **PARCIAL** — `REVIEW_MODE`, `TOOL_VERSION` ausente, `RUN_ID` 9 usos | R1-…REVIEW, RUN_ID |
| `VERIFICATION_PROVENANCE` | **PARCIAL** — hash de script en `PATCH-REGISTRY` | P1–P16 |

**La distinción que importa:** una regla puede tener fuente perfecta y actor desconocido. Eso no la
invalida como *información*; la invalida como *criterio de cierre*. `SUPPORTED`

---

## 12. RQ-15/RQ-16 — REGLAS EN TESTS Y CÓDIGO

### 12.1 Volumen

| Medida | Valor | ¿Documentado? |
|---|---:|---|
| `assert*` en 29 `.py` | **699** | **NO** |
| Tokens de denylist (`BLOCK`, `READ_ONLY`) | 240 | **NO** |
| Valores hardcodeados tipo `== "NOT_…"` | 91 | **NO** |
| `allowlist` / `SAFE_` | 28 | parcial |
| Regex en código | 39 | **NO** |
| **Comentarios normativos en código** | **4** | — |

**699 aserciones y 4 comentarios normativos.** Las reglas están en las aserciones, no en la
documentación. `OBSERVED`

### 12.2 El collector: 38 estados como literales

| Literal | Ocurrencias | ¿En enumeración canónica? |
|---|---:|---|
| `NOT_AVAILABLE` | 18 | V1/V2/V4/V6 |
| `NOT_EVALUATED` | 10 | V2 |
| `NOT_PROVEN` | 7 | V1 |
| `PERMISSION_DENIED` | 3 | **NO** |

**`PERMISSION_DENIED` está en el código y no en ningún documento normativo.** Y los 38 literales
no están en una enumeración: **no hay un solo sitio al que cambiarlos.** `ENFORCED_RULE` por
literal disperso, sin punto de control. `OBSERVED`

**Riesgo concreto:** si la taxonomía cambiara `NOT_EVALUATED` → otro token, habría que editar 10
puntos del código sin ninguna lista que los reúna. `SUPPORTED`

### 12.3 `test_T31`: las tres expectativas

| Expectativa | Contenido | ¿Existe en norma? |
|---|---|---|
| `DOCUMENTED_EXPECTATION` | «la aislación debe ser unidireccional: los errores actuales siguen contando» (docstring) | **NO** — el docstring es la única fuente |
| `TEST_EXPECTATION` | 3 `assertIn` de cadenas literales en `main` | **NO** |
| `ACTUAL_BEHAVIOR` | **no verificado** — el test no llama al código | — |

**3 capas, 2 no documentadas, 1 no ejecutada.** `TEST_TAUTOLOGICAL` (MIG-07.8 §7)

**Y un hallazgo nuevo de esta fase:** la única «expectativa documentada» es el **docstring del
propio test**. El test se documenta a sí mismo. `SUPPORTED`

---

## 13. RQ-19 — CONTROLES NEGATIVOS (protocolo, sin implementar)

| # | Control | Qué prueba | Estado |
|---|---|---|---|
| **A** | Regla ficticia conocida (`Baldwin`) | ¿el método la clasifica `INVENTED_RULE`? | **EJECUTADO — PASA.** 0 en 281 documentos, nombre 0 en el corpus |
| **B** | Regla real sin autoridad (`V6 §Regla`) | ¿evita usarla como norma? | **FALLIDO.** MIG-07.6 §10 la aplicó mientras la autoridad de V6 estaba en disputa |
| **C** | Regla histórica (`P0=B__…` de HOST-A) | ¿evita tratarla como actual? | **FALLIDO.** `P0=B__CONTAMINATED_REQUIRES_ISOLATION` se usa como gate vigente |
| **D** | Regla válida fuera de alcance (`TESTING.md §5` sobre prosa) | ¿la rechaza? | **FALLIDO.** Se aplicó a O-01 |
| **E** | Dos reglas legítimas contradictorias | ¿escala el conflicto? | **PARCIAL.** El router declara `REVIEW_REQUIRED` pero no se ejecutó |

```
NEGATIVE_CONTROL_STATUS=DESIGNED_AND_EXECUTED
  A=PASS   B=FAIL   C=FAIL   D=FAIL   E=PARTIAL
  PASS_RATE=1 de 5
```

**El control A pasa y los otros cuatro fallan.** Y A es el más fácil: una regla con nombre
inventado es detectable por búsqueda de nombre. **B–D son los que importan y fallan.** `SUPPORTED`

**Un control que este documento NO puede pasar:** *(F)* presentar a este agente una regla nueva con
autoridad aparente y comprobar si la usa. **No tengo forma de auto-detectarlo** sin un revisor
independiente, y `P4=0`. `UNKNOWN`

---

## 14. RQ-20 — AUTODIAGNÓSTICO: REGLAS QUE USA ESTE DOCUMENTO

Registro obligatorio. Cada regla que MIG-07.9 aplicó:

| # | Regla usada | ¿Existía antes? | ¿La introdujo MIG-07.9? | ¿Documentada? | Autoridad | Alcance | Vigencia | Naturaleza |
|---:|---|---|---|---|---|---|---|---|
| 1 | «buscar con 2+ técnicas» | sí (mi práctica) | no | no | ninguna | análisis | actual | `INFERENCIA` |
| 2 | «no aceptar una afirmación sin fuente» | **encargo** | no | sí (encargo) | **encargo** | esta fase | actual | `NORMA` |
| 3 | «`git ls-files` define el corpus» | — | **SÍ, implícitamente** | no | ninguna | rastreo | **retirada** | `INFERENCIA` |
| 4 | «5 condiciones para `PROVENANCE_DEFECT`» | no | **SÍ** | no | ninguna | este doc | actual | `INFERENCIA` |
| 5 | «5 condiciones para que una derivada sea norma» | no | **SÍ** | no | ninguna | este doc | actual | `INFERENCIA` |
| 6 | «las 6 de OpenCode son orden de ensamblado» | sí (doc oficial) | no | **sí** | OpenCode | plataforma | actual | `NORMA` externa |
| 7 | «el enum de V6 define `RETIRED`» | **NO** | **SÍ** | no | ninguna | misused | — | `INFERENCIA` |
| 8 | «`sin allowlist` es re-descubrimiento» | sí | no | sí (2 docs) | ninguna | método | actual | `HECHO` |

```
SELF_PROVENANCE_DEFECT=FOUND
  REGLA_3=universo de rastreo no declarado  -> me llevo 13% del corpus y produjo 4 falsos "inventado"
  REGLA_4,5=derivadas sin fuente, usadas como criterio
  REGLA_7=uso de vocabulario normativo sobre construccion propia
NO_CORREGIDO_INMEDIATAMENTE=si  (registrado; la correccion esta en §4.1 y §5.3)
CONTAMINACION_DE_EVIDENCIA=NO  (las conclusiones se derivan del corpus completo, no del rastreo inicial)
```

**El más grave es el 7:** usé un verbo del vocabulario del proyecto (`RETIRED`) para deponer un
modelo propio. Es el patrón §5.3 outlawed, cometido por mí en la fase que lo outlawed. `SUPPORTED`

---

## 15. RQ-21 — BARRERA CONTRA LA CONTAMINACIÓN DE REGLAS

| Eje | ¿Existe? | Evidencia |
|---|---|---|
| **DETECTION** de regla inventada | **NO** | el control A pasó porque busqué un nombre; no hay detector genérico |
| **DETECTION** de inferencia→norma | **NO** | §5.2, 4 de 6 casos |
| **CORRECTION** | `AD_HOC` | 4 correcciones en esta sesión, todas manuales |
| **REVALIDATION** | `PARCIAL` | se reescaneó el archivo, no el conjunto |
| **PREVENTION** | `AD_HOC` | «no convertir propuesta en norma» — instrucción del encargo, sin enforcement |
| **ENFORCEMENT** | **NO** | `permissions` documentado, sin `.opencode/` |

```
SELF_CORRECTION_STATUS=PARTIAL
  DETECTION=AD_HOC (funciona si se busca el nombre; no si no se busca)
  CORRECTION=AD_HOC
  REVALIDATION=PARCIAL
  PREVENTION=AD_HOC
  ENFORCEMENT=NO
```

**Y el resultado del control C es el dato duro:** una regla de HOST-A (`P0=B__…`) se usa como gate
vigente en HOST-C desde hace fases, y **ningún mecanismo la marcó**. La barrera no existe. `OBSERVED`

---

## 16. RQ-22 — MODELO PRELIMINAR (conceptual, no esquema)

```
RULE       (existe, con texto)
SOURCE     (de dónde salió)          <- separado
AUTHORITY  (si puede imponer)        <- separado; NO implica SOURCE
SCOPE      (dónde aplica)            <- separado; NO implica universalidad
TIME       (vigencia)                <- separado
DERIVATION (si es madre o derivada)  <- separado; una derivada NO hereda autoridad
EVIDENCE   (qué la respalda)
VERIFICATION (si alguien la comprobó aparte)
CONFLICT   (con qué reglas choca)
STATUS     (vigente / histórico / en disputa / inventada)
```

**Los 10 campos, y la condición que los hace necesarios:** cada par consecutivo
(`SOURCE`→`AUTHORITY`, `AUTHORITY`→`SCOPE`, `SCOPE`→`TIME`, `RULE`→`DERIVATION`) es un par que
esta fase demostró **puede tener un valor y el otro no**. Un modelo con menos campos no puede
representar los casos que ya encontré. `SUPPORTED`

**No se crea YAML. No se crea `STATE`. No se modifica vocabulario.** `PROMOTION=BLOCKED`

---

## 17. RQ-23 — REVISIÓN ADVERSARIAL DE MIG-07.9

| # | Comprobación exigida | Resultado |
|---|---|---|
| 1 | ¿reglas inventadas por esta fase? | **SÍ, 4** (reglas 4, 5 y las de §11.1/§16), todas registradas |
| 2 | ¿fuentes inexistentes? | 0 verificadas con 2 técnicas |
| 3 | ¿citas incorrectas? | **1 corregida**: hash y nº de líneas de MIG-07.8 (§18) |
| 4 | ¿autoridad atribuida sin evidencia? | **1 detectada**: Baldwin (MIG-07.8) |
| 5 | ¿fuente confundida con autoridad? | **el censo lo hace** — clasifica V6 como `REFERENCE` igual que `AGENTS.md` |
| 6 | ¿ejecución confundida con legitimidad? | corregido en §3 |
| 7 | ¿repetición confundida con autoridad? | **SÍ, 4 de 6 casos** (§5.2) |
| 8 | ¿regla histórica como actual? | **SÍ**, control C falló |
| 9 | ¿regla de un dominio a otro? | **SÍ**, control D falló |
| 10 | ¿regla de test como norma? | **SÍ**, 699 aserciones sin documento |
| 11 | ¿memoria como fuente? | **SÍ, 1 caso** documentado (§9.2) |
| 12 | ¿números incorrectos? | **2 corregidos**: hash y 585 vs 658 líneas |
| 13 | ¿regex sin verificar? | **SÍ, 1 grave** — el rastreo inicial (§4.1) |
| 14 | ¿`NOT_FOUND` convertido en inexistente? | **SÍ** — `sin allowlist` «0 en previo» era `NOT_SEARCHED` |
| 15 | ¿algún `UNKNOWN` convertido en negativo? | revisado: no |

**7 de 15 controles fallan. 4 corresponden a `AGENT_INFERENCE` misused, 3 a error de método.**

---

## 18. RQ-24 — QC Y ERRORES DE PROCEDIMIENTO

| # | Error | Tipo | Estado |
|---|---|---|---|
| **M9-1** | Hash de MIG-07.8 reportado como `e3b0c442…` (cadena vacía) | **error de procedimiento** | **corregido**: `8678b658…`, verificado por 2 métodos |
| **M9-2** | «658 líneas» para MIG-07.8 | **cifra no verificada** | **corregido**: 585 líneas, 27554 bytes |
| **M9-3** | Rastreo de procedencia con universo incompleto (13%) | **defecto de método** | **corregido** en §4.2; el resultado inicial queda invalidado |
| **M9-4** | «control negativo no lo mencionó ninguna fase anterior» | **afirmación refutada** | **corregido**: `TESTING.md §5` lo exige (§4.4) |
| **M9-5** | `L0_L5_AS_SCALE=RETIRED` usa vocabulario normativo sobre construcción propia | **procedencia indebida** | **registrado**, no corregido (§14 regla 7) |

**M9-3 es el más grave y el más instructivo:** invalida un resultado que yo ya había reportado en la
fase anterior (`FALSE_NEGATIVES_FOUND=5` incluía `FN-3`, que era un re-descubrimiento). `SUPPORTED`

**Verificaciones positively cumplidas:** hash por 2 métodos · líneas por `wc` · referencias
`fichero:línea` spot-checked · cifras de reglas por 2 técnicas (nombre y término) · ninguna fuente
citada resulta inventada · `AGENTS.md` sin modificar (`d5fa85a4…`) · V6 sin modificar (`c858b5ae…`) ·
`dePersistir` intacto en `MIGRATION-…:23`.

---

## 19. RESULTADO

```
MIG-07.9=NOT_CLOSED

RULES_INVENTORIED=18          (12 del proyecto + 6 formas no documentadas)
RULES_WITH_SOURCE=16
RULES_WITH_AUTHORITY=0        (3 en conflicto, 8 parciales, 5 sin resolver)
RULES_WITH_SCOPE=7
RULES_WITH_TEMPORAL_VALIDITY=2   (CURRENT confirmado en 2; los otros 10 -> UNKNOWN)
UNSUPPORTED_RULES=2           (control negativo re-presentado como nuevo; L0-L5 RETIRED)
INVENTED_RULES=8
DERIVED_RULES=6
RULES_WITH_UNKNOWN_PROVENANCE=1  (las 5 de BALDWIN, autor=UNKNOWN y scope=UNKNOWN)

AUTHORITY_CONFLICTS=3         (G1 vocabulario, G4 UNKNOWN, G5 alcance de TESTING.md)
SCOPE_CONFLICTS=3             (G5 + TESTING.md fuera de alcance + V6 en disputa)
TEMPORAL_CONFLICTS=5          (C1..C5 del router; 3 con regla, 2 sin ella)

SELF_PROVENANCE_DEFECT=FOUND
  CAUSA=universo de rastreo no declarado (13% excluido)
  EFECTO=4 falsos "INVENTED_RULE" y 1 falso hallazgo (FN-3)
  REGLA_MISUSED=RETIRED sobre construccion propia
  CONTAMINACION_DE_LA_EVIDENCIA=NO

NEGATIVE_CONTROL_STATUS=DESIGNED_AND_EXECUTED  (A=PASS B=FAIL C=FAIL D=FAIL E=PARTIAL)
SELF_CORRECTION_STATUS=PARTIAL
AUTODIAGNOSTIC_STATUS=AD_HOC_SELF_TRACE   (registro de §14 existe; no hay detector)

RULE_SOURCE_AUTHORITY_CONFLATION=YES   (el propio censo lo hace)
OPENCODE_INSTRUCTION_CONFLICT_RESOLUTION=NO_RESOLUTION  (documentado, por diseño)

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
PROMOTION=BLOCKED
```

### Contradicción nueva que detiene la promoción

**El proyecto no tiene el concepto «fuente sin autoridad».** El censo clasifica
`ESTADOS-ES-EN.md` y `AGENTS.md` en la **misma** categoría `REFERENCE`. Toda la separación
`SOURCE` / `AUTHORITY` que RQ-3 exige no tiene counterpart en el vocabulario del proyecto, y no
puede derivarse de él.

`AUTHORITY_CONFLICT=YES` · `PROMOTION=BLOCKED_PENDING_CLASSIFICATION`

**Y una segunda, ya conocida y no resuelta:** `TESTING.md §5` se aplicó a documentos en
MIG-07.6/07.7/07.8, y su alcance declarado es de sistema. `SCOPE_CONFLICTS=3`

### Lo que queda abierto y no puedo cerrar

1. **La categoría `SOURCE_EXISTS_BUT_AUTHORITY_UNKNOWN` no existe en el proyecto.** Sin ella, 12 de
   las 18 reglas inventariadas no se pueden clasificar.
2. **Los 5 controles negativos B–D fallan**, y son los que importan. Ninguno tiene solución
   propuesta aquí, y sin revisor independiente no puede medirse.
3. **No puedo distinguir `AGENT_INFERENCE` de `DERIVED_RULE`** cuando la inferencia está larga y
   encadenada. Solo detecto la pérdida de etiqueta en 4 de 6 casos (§5.2); en los otros 2 no la vi.
