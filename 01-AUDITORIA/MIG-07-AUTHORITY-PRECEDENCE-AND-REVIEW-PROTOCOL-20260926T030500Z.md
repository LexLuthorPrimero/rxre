# MIG-07 — AUTORIDAD, PRECEDENCIA Y PROTOCOLO DE REVISIÓN

> Artefacto nuevo de auditoría, dentro de `01-AUDITORIA/`.
>
> **Este documento NO declara autoridad sobre ninguna dimensión y NO pretende ser una capa de
> autoridad.** Es un registro de análisis. No se ha modificado ningún documento que analyse.

```
DOCUMENT_ID=MIG-07-AUTHORITY-PRECEDENCE-AND-REVIEW-PROTOCOL
CREATED_UTC=2026-09-26T03:05:00Z
TYPE=AUTHORITY_PRECEDENCE_AUDIT_AND_PROTOCOL
DECLARES_AUTHORITY=NO
E1_RESULT=AUTHORITY_CONFLICT
PRECEDENCE_RULE=NOT_AVAILABLE
E6_RESULT=DIMENSION_REQUIRED_NOT_IMPLEMENTED
E6_IMPLEMENTED=0
MIG-07_STATE=VERIFYING
AUTHORITY_DOCUMENT_CREATED=0
MIGRATIONS_APPLIED=0  TERMS_ADDED=0  TERMS_RENAMED=0  TERMS_REMOVED=0
IMPLEMENTATION=NOT_EXECUTED
```

Clasificación usada: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `CONFLICT`

---

## 1. RESUMEN

La pregunta no era «qué documento está mejor escrito». Era **qué mecanismo determina la autoridad
y qué evidencia demuestra la precedencia**. Respuesta:

**No existe ese mecanismo para la dimensión de vocabulario.** Existen cinco reglas de precedencia
en el proyecto, **ninguna cubre esta dimensión**, y la única que aplica a un conflicto sin
resolver dice literalmente **«Devolver ambas. No elegir»**. `PRECEDENCE_RULE=NOT_AVAILABLE`.

| # | Hallazgo | Clasificación |
|---|---|---|
| 1 | Existen 5 reglas de precedencia, **todas acotadas a un ámbito**. Ninguna rige la dimensión de vocabulario | `OBSERVED` |
| 2 | La regla aplicable a conflictos sin resolver es «**No elegir**» (`DOCUMENTATION-ROUTER.md:78`) | `OBSERVED` |
| 3 | **El censo lista V6 entre los «Documentos que no deben ser fuente de estado»** (`DOCUMENTATION-GAPS.md` §7), motivo: *taxonomía ampliada «provisional»* | `OBSERVED` |
| 4 | El registro de decisiones D clasificó V6 como **«mantener como taxonomía»**, no como autoridad (`DECISIONES-D1-D10.md:393`) | `OBSERVED` |
| 5 | `AGENTS.md` **define** 8 términos; V6 define 26. La intersección es de **2 términos**, y uno (`CONFLICT`) tiene **dos definiciones incompatibles** | `OBSERVED` |
| 6 | V6 **no es autocontenido**: su §Regla de evidencia depende de `SUPPORTED`, definido solo en `AGENTS.md` | `OBSERVED` |
| 7 | La contradicción de `MASTER-RESEARCH-STATUS.md` **se resuelve al separar dimensiones**: navegación-histórica vs. estado-actual. No es un conflicto real | `SUPPORTED` |
| 8 | **Ningún campo del proyecto registra quién produjo o quién verificó algo.** `VERIFIED_BY`, `REVIEWER`, `REVIEWED_BY`, `AUTHORED_BY`, `ACTOR` = 0 ocurrencias | `OBSERVED` |
| 9 | La contradicción `AGENTS.md` ↔ V6 **sobrevive parcialmente** a la separación por dimensiones, por dos razones concretas | `SUPPORTED` |
| 10 | La plantilla de gobernanza existente (`DIAGRAM_ID`/`STATUS`/`LAST AUDITED`/`SOURCE_OF_TRUTH`/`CONFLICTS`/`NOTE`) **no tiene campo de ownership** | `OBSERVED` |
| 11 | Ni V6 ni MRS tienen historial git: **0 commits las tocan**. No hay provenance por git | `NOT_AVAILABLE` |

**E-1 no se resuelve. No se elige autoridad. No se crea documento de autoridad.**
Se prepara el protocolo para que otro la determine.

---

## 2. GRAFO DE AUTORIDAD

### 2.1 Nodos

| Nodo | Función | Dimensión que reclama | Declaración explícita | Fecha decl. | Provenance | Hash | Estado | ¿Modifica o describe? | Reclamada por |
|---|---|---|---|---|---|---|---|---|---|
| **N1** `AGENTS.md` | instrucción de agente | metodología, vocabulario (A), seguridad, estado | `Canonical navigation and state` + `## Evidence vocabulary` | — (texto *recorded on 2026-09-25*) | **0 commits** | `d5fa85a4…` | vigente | **modifica** (regla) | nadie lo nombra `SOURCE_OF_TRUTH`; 15 rutas lo citan |
| **N2** `00-INDICE/ESTADOS-ES-EN.md` | tabla ES/EN de estados | ciclo de vida documental (I), elegibilidad (M), validez temporal (O) | ninguna propia; `REPARATION-PLAN` N8 la llama «Vocabulario canónico» (propuesto) | `2026-09-24` | **0 commits** | `c858b5ae…` | **sin `STATUS`** | describe | N5, N6 (ambos DRAFT), N7, N11 |
| **N3** `DIAGRAMAS/09-ESTADOS-CIENTIFICOS.md` | máquina de estados | ciclo científico | `SOURCE_OF_TRUTH: N2, N4, N7, N8, N9` | `LAST AUDITED 2026-09-24` | 0 commits | `0893e61e…` | **`DRAFT/CONFLICT`** | describe | nadie |
| **N4** `DIAGRAMAS/10-NAVEGACION-DOCUMENTAL.md` | navegación | navegación | `SOURCE_OF_TRUTH: README.md, 00-INDICE/README.md, MASTER-RESEARCH-STATUS, MASTER-PLAN, R2-MAP, PROJECT-DOC-STATUS, ROADMAP, SAFETY-RULES` | `2026-09-24` | 0 commits | — | `DRAFT/CONFLICT` | describe | nadie |
| **N5** `DIAGRAMAS/13-REGLA-FUNDAMENTAL.md` | regla de representación | ciclo de vida | `SOURCE_OF_TRUTH: N10, N2, N8, N12, N4` | `2026-09-24` | 0 commits | — | **`DRAFT`** | describe | nadie |
| **N6** `DOCUMENTATION-ROUTER.md` | enrutado documental | navegación, resolución de consultas | `VOCABULARY → PRIMARY: N1 §Evidence vocabulary; SECONDARY: N2; ESCALATION: REVIEW_REQUIRED` | — | **UNTRACKED** | — | vigente | describe | N1 lo designa «START HERE for any documentation question» |
| **N7** `DOCUMENTATION-CENSUS.md` | censo documental | taxonomía de documentos | clasifica N1, `IMPLEMENTATION-SAFETY-RULES` y **N2** como `REFERENCE` | `2026-09-25` | **UNTRACKED** | — | vigente, congelado | describe | nadie |
| **N8** `00-INDICE/MASTER-RESEARCH-STATUS.md` | índice maestro | navegación + addendas | ninguna propia | — | 0 commits | — | vigente (addenda D6) | describe | 8 diagramas (`SOURCE_OF_TRUTH`), incl. N1 lo degrada |
| **N9** `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | reconciliación | taxonomía `SOURCE_OF_TRUTH_CURRENT/_HISTORICAL/_DERIVED` | esa taxonomía de 3 valores | `2026-09-25` | UNTRACKED | — | vigente | describe | N6 lo cita como `CONFLICT_SOURCE` |
| **N10** `DIAGRAMAS/README.md` | índice de diagramas | **orden de autoridad documental** | «La autoridad documental es, en este orden» (6 niveles) + «Un diagrama es una vista derivada» | `LAST AUDITED 2026-09-25` | 0 commits | `bff01cb7…` | **`DRAFT/CONFLICT`** | describe | N5 lo nombra `SOURCE_OF_TRUTH` |
| **N11** `DECISIONES-D1-D10.md` | registro de decisiones | estado canónico de 10 matters | «la fila de estado superior es la precedencia vigente» | — | 0 commits | — | vigente (`✅ ADOPTADA`) | **modifica** | nadie |
| **N12** `R1-6-EVIDENCE-STATE-MODEL.md` (en repo) | modelo de evidencia | evidencia (A), reproducibilidad (H) | 10 términos ES | — | UNTRACKED | — | vigente | describe | N3, N5 |
| **N13** `PROBLEM-STATUS-FINAL.md` (V4) | matriz de problemas | resultado de problema (F) | `Fuente de observación: FINAL-VALIDATION-20260925T135831Z.json` | `2026-09-25` | 0 commits | `2a52ee76…` | vigente | describe | N1 lo nombra «current problem matrix» |
| **N14** `DOCUMENTATION-GAPS.md` | registro de huecos | **registro de supresión de estado** | §7 «Documentos que no deben ser fuente de estado» — **incluye N2** | `2026-09-25` | UNTRACKED | — | vigente, congelado | describe | N7 |
| **N15** `REPARATION-PLAN.md` | plan de reparación | propuesta | N8: «Vocabulario canónico» para tabla ES/EN ** conditioned on autorización explícita** | — | UNTRACKED | — | histórico (§7 de N14) | describe | nadie |

### 2.2 Aristas

Cada arista tiene evidencia textual. **Ninguna inventada.**

| # | Origen → Destino | Tipo | Evidencia textual | Ubicación | ¿Explícita? |
|---|---|---|---|---|---|
| **E1** | N3 → N2 | `SOURCE_OF_TRUTH` | `SOURCE_OF_TRUTH:` / `- 00-INDICE/ESTADOS-ES-EN.md` | `09:5-10` | explícita |
| **E2** | N5 → N2 | `SOURCE_OF_TRUTH` | `- 00-INDICE/ESTADOS-ES-EN.md` | `13:8` | explícita |
| **E3** | N5 → N10 | `SOURCE_OF_TRUTH` | `- 00-INDICE/DIAGRAMAS/README.md` | `13:7` | explícita |
| **E4** | N5 → N4 | `SOURCE_OF_TRUTH` | `- 01-AUDITORIA/FASE-R1-…/R1-6-…md` | `13:11` | explícita |
| **E5** | N8 → (nodos) | `SOURCE_OF_TRUTH` ×8 | 8 diagramas lo nombran `MASTER-RESEARCH-STATUS.md` | 8 cabeceras | explícita |
| **E6** | N10 → N8 | **autoridad #1 de un orden de 6** | «1. `00-INDICE/MASTER-RESEARCH-STATUS.md` y sus addendas vigentes» | `README:24` | explícita |
| **E7** | N10 → todos | *regla de prevalencia* | «Un diagrama es una **vista derivada**… el texto canónico prevalece y el diagrama queda `CONFLICT`» | `README:29` | explícita |
| **E8** | N1 → N6 | *designación de punto de entrada* | «`DOCUMENTATION-ROUTER.md` — **START HERE for any documentation question**» | `AGENTS:11` | explícita |
| **E9** | N6 → N1,N2 | `PRIMARY`/`SECONDARY` + escalado | `` `VOCABULARY` … `AGENTS.md` §Evidence vocabulary \| CUR \| … \| `ESTADOS-ES-EN.md` \| — \| `REVIEW_REQUIRED` (dos vocabularios) `` | `ROUTER:267` | explícita |
| **E10** | N7 → N1,N2 | *clasificación de rol* | `` `REFERENCE` \| 3 \| `AGENTS.md`, `IMPLEMENTATION-SAFETY-RULES.md`, `ESTADOS-ES-EN.md` `` | `CENSUS:92` | explícita |
| **E11** | **N14 → N2** | **supresión de estado** | «`00-INDICE/ESTADOS-ES-EN.md` \| taxonomía ampliada "provisional" \| `DIAGRAMAS/10` §CONFLICT» | `GAPS §7` | explícita |
| **E12** | **N11 → N2** | *clasificación de acción* | «vocabulario ampliado y normalizado \| **mantener como taxonomía** \| **No**» | `DECISIONES:393` | explícita |
| **E13** | N15 → N2 | *propuesta condicionada* | «N8 … Vocabulario canónico … **Los 8 requieren autorización explícita de creación**» | `REPARATION-PLAN:183,185` | explícita |
| **E14** | N2 → N1 | **dependencia de definición** | «`VALIDADO` no significa `SUPPORTED` si el protocolo no lo permite» — `SUPPORTED` no está en la tabla de N2 | `V6:40` | explícita |
| **E15** | N1 → N8 | *degradación* | «`MASTER-RESEARCH-STATUS.md` … **does not hold the current state** … Do not enter through it» | `AGENTS:21-24` | explícita |
| **E16** | N1 → N13 | *designación* | «`PROBLEM-STATUS-FINAL.md` — current problem matrix» | `AGENTS:13` | explícita |
| **E17** | N9 → N8 | `SOURCE_OF_TRUTH_CURRENT` | `SOURCE_OF_TRUTH_CURRENT=C1-SIDE + current file bytes` | `RECONCILIATION:192` | explícita |
| **E18** | N3 → N2 | *caracterización contradictoria* | «La taxonomía se amplió en `ESTADOS-ES-EN.md`, pero **sigue siendo provisional**» | `09:14` | explícita |
| **E19** | N2 → (nadie) | *ausencia de `STATUS`* | 0 ocurrencias de `STATUS:`/`DIAGRAM_ID:`/`SHA256` | `V6` completo | explícita (por ausencia) |
| **E20** | N3 → N5 | `SOURCE_OF_TRUTH` | N5 nombra a N3 vía `R1-6`; N3 no nombra a N5 | `13:11` | explícita |

**Observación estructural: N2 (V6) tiene 5 aristas entrantes (E1, E2, E11, E12, E13) y 1 saliente
(E14).** De las 5 entrantes: **3 lo clasifican como no-autoridad** (E11 supresión de estado, E12
«mantener como taxonomía», E13 propuesta no autorizada) y **2 son diagramas `DRAFT`/`DRAFT/CONFLICT`**
(E1, E2). **Cero aristas entrantes desde documentos vigentes no-DRAFT.** `OBSERVED`.

---

## 3. REGLAS DE PRECEDENCIA

Búsqueda de 24 términos (ES+EN). Resultado: 5 reglas con formulación normativa.

| # | Regla | Texto literal | Ámbito | ¿Cubre vocabulario? |
|---|---|---|---|---|
| **P1** | Fila de estado superior | «la fila de estado superior es la precedencia vigente» | `DECISIONES-D1-D10:43` — el propio registro D | **no** |
| **P2** | Resultados canónicos sobre mapas | «D2: `R2-GLOBAL-DOCUMENTATION-MAP.md` es una vista `DRAFT/CONFLICT`; los resultados y estados canónicos tienen precedencia» | `DECISIONES:46-47` — matter D2 | **no** |
| **P3** | Diagrama es vista derivada | «Un diagrama es una **vista derivada**. Si el diagrama contradice al texto canónico, el texto canónico prevalece» | `DIAGRAMAS/README:29` — orden documental | **parcial**: degrada a N1–N4, no a N2 |
| **P4** | `CONFLICT` → texto canónico | «`CONFLICT` … Fuentes incompatibles sin precedencia resuelta \| **El texto canónico prevalece**» | `V6:35` — la propia tabla de N2 | **circular**: N2 se cita a sí misma |
| **P5** | **No elegir** | «`CONFLICT` \| Fuentes incompatibles \| **Devolver ambas. No elegir**» y «`REVIEW_REQUIRED` \| … \| **Escalar a revisión editorial**» | `ROUTER:78,80` — manejo de conflictos | **SÍ — es la que aplica** |

### Resultado

```
PRECEDENCE_RULE=NOT_AVAILABLE
```

**Precisión necesaria:** no es que no exista ninguna regla. Existen 5. **Ninguna determina qué
documento tiene autoridad sobre el vocabulario de estados.** Y la única que gobierna un conflicto
sin resolver sobre ese tema (P5) **ordena no elegir** y escalar a revisión editorial — una
escalación que **nadie ejecutó**. `SUPPORTED`.

**Corolario operativo:** cualquier intento de cerrar E-1 eligiendo autoridad violaría P5, que es
la única regla explícitamente aplicable. `SUPPORTED`.

---

## 4. RECONSTRUCCIÓN HISTÓRICA

| Nodo | Fecha declarada | mtime | Creación | ¿Derivación? | ¿Reparación? | ¿Provisional declarada? | ¿Referida como autoridad? | ¿Actualización? | ¿Provenance? |
|---|---|---|---|---|---|---|---|---|---|
| N2 (V6) | `2026-09-24` | 09-25 11:16 | como N8 de un plan | **sí**, de un plan de reparación | **reparación** (normalización de mezcla ES/EN) | por N3 (`sigue siendo provisional`); por N14 (`"provisional"`) | 2 diagramas DRAFT | **sin evidencia** | **0 commits** |
| N3 | `LAST AUDITED 2026-09-24` | 09-25 11:16 | como diagrama del set | vista | — | sí (`provisional`, DRAFT) | — | no | 0 commits |
| N10 | `LAST AUDITED 2026-09-25` | 09-25 11:16 | índice de diagramas | — | — | `DRAFT/CONFLICT` | — | no | 0 commits |
| N1 | `recorded on 2026-09-25` | **09-25 20:03** | el más reciente | no | — | no | — | **sí, es el mecanismo vivo** | **0 commits** |
| N8 | — | 09-25 | — | — | — | no | **8 diagramas** | addenda D6 vigentes | 0 commits |
| N6 | — | 09-25 | — | — | — | no | por N1 («START HERE») | — | **UNTRACKED** |
| N7 | `2026-09-25` | 09-25 | — | — | — | no | — | congelado | **UNTRACKED** |
| N11 | — | 09-25 | — | no | registro de reparación | no | — | vigente | 0 commits |
| N13 | `2026-09-25` | 09-25 | derivado de una captura | **sí** | — | no | por N1 | — | 0 commits |
| N15 | — | 09-25 | plan | — | **reparación** | no (`DRAFT/CONFLICT` per N14) | no | no | UNTRACKED |

### Lecturas obligatorias

1. **Antigüedad ≠ autoridad.** N2 es de `2026-09-24`; N1 es de `2026-09-25` y es más reciente.
   La más antigua es tratada como taxonomía, la más reciente como mecanismo vivo. `OBSERVED`
2. **Cantidad de referencias ≠ autoridad.** N8 tiene 8 `SOURCE_OF_TRUTH` y N1 lo degrada. N2 tiene
   5 entrantes y 3 de ellas lo descalifican. `OBSERVED`
3. **Calidad editorial ≠ autoridad.** N2 es el mejor redactado (único con «Regla de uso») y está
   en la lista de «no debe ser fuente de estado». `OBSERVED`
4. **`SOURCE_OF_TRUTH` autodeclarado ≠ autoridad.** N3 es `DRAFT/CONFLICT` y usa `SOURCE_OF_TRUTH`
   para sugerir N2 como autoridad, en un documento cuyo conflicto #1 declara a N2 provisional. `OBSERVED`
5. **El orden de creación documentado es: plan de reparación (N15) → N2 → decision register (N11)
   clasifica N2 como «mantener como taxonomía» → censo (N7) la clasifica `REFERENCE` → registro de
   huecos (N14) la pone en «no fuente de estado».** Es decir: **N2 fue creada y nunca promovida.**
   `SUPPORTED`
6. **No hay provenance por git para ningún nodo de autoridad.** 0 de los 8 commits tocan
   `AGENTS.md`, `ESTADOS-ES-EN.md`, `DIAGRAMAS/README.md` ni `PROBLEM-STATUS-FINAL.md`. Los
   commits son *bulk group-adds*. `NOT_AVAILABLE`
7. **Dos de los nodos que registran el conflicto (N6, N7) están `UNTRACKED`.** El conflicto
  authority está documentado fuera del control de versiones. `OBSERVED`

---

## 5. ANÁLISIS DE `AGENTS.md`

| Pregunta | Respuesta | Evidencia | Clasificación |
|---|---|---|---|
| **A.** ¿Define vocabulario? | **SÍ** | `## Evidence vocabulary` → «**Use these labels consistently**» + 8 definiciones | `OBSERVED` |
| **B.** ¿Solamente referencia? | **No** | define; y su lista canónica (`:11-19`) es de navegación/estado, no de vocabulario | `OBSERVED` |
| **C.** ¿Reglas metodológicas con precedencia sobre N2? | **Parcialmente** | Define reglas que N2 no puede contradecir: «Never convert `UNKNOWN`, `NOT_AVAILABLE`, or `CONFLICT` into `PASS` by inference»; «Always separate: 1. observed fact 2. interpretation 3. hypothesis 4. causal claim»; «Do not silently normalize historical claims into current claims». **Pero no declara precedencia sobre N2** — N2 no aparece en N1 (0 menciones) | `SUPPORTED` |
| **D.** ¿Operan en dimensiones distintas? | **MAYORMENTE SÍ** | N1: 6 términos de evidencia (A) + `FAIL` (E) + `DEFERRED` (D). N2: ciclo de vida (I) + elegibilidad (M) + validez temporal (O). **Intersección: 2 de 8 y 2 de 26** — `CONFLICT` y `DESCONOCIDO`/`UNKNOWN` | `OBSERVED` |
| **E.** ¿Puede desaparecer la contradicción separando dimensiones? | **PARCIALMENTE** | La separación es ya el modelo del router (E9: `PRIMARY`=N1, `SECONDARY`=N2). Pero el router marca `REVIEW_REQUIRED` **precisamente porque la separación no es limpia** | `SUPPORTED` |
| **F.** ¿La contradicción sigue existiendo después? | **SÍ, por dos razones concretas** | ver abajo | `SUPPORTED` |

### Las dos razones por las que la separación no cierra la contradicción

**R-1 — `CONFLICT` tiene dos definiciones incompatibles.**

| Fuente | Definición | Eje |
|---|---|---|
| N1 `:98` | «`CONFLICT`: sources disagree» | evidencia (A) — dos fuentes dicen cosas distintas |
| N2 `:35` | «Fuentes incompatibles sin precedencia resuelta \| **El texto canónico prevalece**» | reconciliación (K) — dos fuentes incompatibles y **una regla de resolución** |

Una es un hecho; la otra es un hecho **más** un imperative de resolución. No son la misma
clasificación. `CONFLICT`.

**R-2 — N2 depende de N1 y no lo declara.** N2 `§Regla de evidencia`: «`VALIDADO` no significa
`SUPPORTED` si el protocolo no lo permite». `SUPPORTED` **no está en la tabla de N2** (E14). N2 usa
una categoría de N1 **sin citarla ni importarla**. Si N1 cambiara `SUPPORTED`, N2 cambiaría de
significado sin que nadie lo decidiera. `CONFLICT`.

**Tercer punto, weaker:** N2 declara en su propia tabla la regla P4 («el texto canónico
prevalece») sin declarar cuál es el texto canónico. Es una regla **circular**: se invoca a sí
misma. `CONFLICT`.

**Conclusión de FASE 4:** la contradicción **no es de competencia total**, sino de **solapamiento
parcial no resuelto** en `CONFLICT` y en la dependencia `SUPPORTED`. Eso es un `CONFLICT` más
acotado y más accionable que el formulado en la fase anterior. `SUPPORTED`.

---

## 6. ANÁLISIS DE `MASTER-RESEARCH-STATUS.md`

| Pregunta | Determinación | Evidencia | Clasificación |
|---|---|---|---|
| ¿Hablan de dimensiones distintas? | **SÍ** | N1 niega que N8 tenga el **estado actual**; N10 le da autoridad para el **orden documental** («y sus addendas vigentes») | `SUPPORTED` |
| ¿Uno es histórico? | **Parcialmente** | N1: «historical navigation»; su overlay `2026-09-25` **delega** en los documentos raíz. N11: «Addenda D6 vigente; snapshot pre-D6 conservado como histórico» | `SUPPORTED` |
| ¿Uno está obsoleto? | **No constatado** | N14 §7 **no lista N8** entre los que no deben ser fuente de estado. Su addenda D6 está `vigente` | `OBSERVED` |
| ¿Existe regla superior? | **No** | Ninguna de P1–P5 cubre N1 vs N10 | `NOT_AVAILABLE` |
| ¿Es realmente un conflicto? | **NO, tras separar dimensiones** | Las dos afirmaciones son simultáneamente verdaderas: N8 es autoridad *documental* (índice + addendas) y **no** es fuente del *estado actual* (delega). Lo que N10 omite es el calificador «y sus addendas vigentes» frente al estado actual | `SUPPORTED` |

**Matiz que impide cerrarlo del todo:** N10 coloca a N8 en el puesto #1 de un orden que se titula
«autoridad documental» **sin** excluir explícitamente el estado actual. Y N10 es `DRAFT/CONFLICT`.
Así que la separación de dimensiones es **una reconstrucción mía**, no una declaración del
proyecto. `PLAUSIBLE`.

**Por tanto: la contradicción nº10 que la fase anterior registrou como `CONFLICT` se degrada a
`PLAUSIBLE` y se re-clasifica: no es un conflicto de autoridad, es una omisión de calificador en
un documento `DRAFT`.** Corrección registrada. `SUPPORTED`.

**Consecuencia no intencional:** esto **deja a N8 como la autoridad documental más referenciada
del proyecto** (8 `SOURCE_OF_TRUTH`) y **la única cuyo estado no está suprimido por el censo**.
No se propone convertirla en autoridad de vocabulario: no tiene vocabulario. `OBSERVED`.

---

## 7. REQUISITOS DE AUTORIDAD PARA V6

Plantilla de gobernanza existente (`DIAGRAMAS/13` y los 14 diagramas):
`DIAGRAM_ID` · `STATUS` · `LAST AUDITED` · `SOURCE_OF_TRUTH` · `CONFLICTS` · `NOTE`.

### 7.1 NECESARIO PARA SER AUTORIDAD

| # | Requisito | Estado actual | Evidencia | Clasificación |
|---|---|---|---|---|
| **R1** | **Autocontención semántica**: definir todo término que use | **FALLA** | usa `SUPPORTED` (no definido) y `W_SMU` (no definido) en su §Regla de evidencia | `OBSERVED` |
| **R2** | **Integridad del término**: la forma normada coincide con la usada | **FALLA** | `DIAGNOSTIC ONLY` = 0 usos; el corpus usa `DIAGNOSTIC` (21), que N2 no define | `OBSERVED` |
| **R3** | **Cobertura de los términos en uso del proyecto** | **FALLA** | 3 términos en uso no definidos: `DOCUMENTED`, `SUPPORTED`, `INCONCLUSIVE` (usados junto a 6 de sus términos en `DIAGRAMAS/00`) | `OBSERVED` |
| **R4** | **Ciclo de vida declarado** (`STATUS`) | **FALLA** | 0 ocurrencias. No puede ser `DRAFT` ni `LIVE`; no tiene estado | `OBSERVED` |
| **R5** | **Integridad de contenido** (hash) | **FALLA** | 0 ocurrencias de `SHA256` en un documento propuesto como autoridad | `OBSERVED` |
| **R6** | **Procedencia de creación autorizada** | **NO DEMOSTRADA** | `REPARATION-PLAN:185` exige autorización explícita para N8; no hay registro | `NOT_AVAILABLE` |
| **R7** | **Ausencia de supresión vigente** | **FALLA** | `DOCUMENTATION-GAPS §7` la lista entre los que **no deben ser fuente de estado** | `OBSERVED` |
| **R8** | **Regla de precedencia declarada** | **FALLA** | su P4 es circular; no declara qué texto es canónico | `CONFLICT` |
| **R9** | **Ausencia de contradicción con la autoridad operativa** | **FALLA** | router `REVIEW_REQUIRED`; censo `REFERENCE` | `CONFLICT` |

### 7.2 CONVENIENTE PERO NO NECESARIO

| # | Requisito | Por qué no es necesario |
|---|---|---|
| C1 | `DIAGRAM_ID` | V6 no es un diagrama; el ID es del sistema de diagramas |
| C2 | `LAST AUDITED` | útil, no habilitante: R4 y R5 son los que importan |
| C3 | `NOTE: no autoriza acciones` | todas las fuentes lo incluyen; es convención, no condición |
| C4 | `CONFLICTS:` block | con R4 y R8 resueltas no hay conflicto que declarar |
| C5 | **Ownership** | la plantilla del proyecto **tampoco tiene campo de owner**. No es, ni lo que impide; es un hueco compartido | 
| C6 | Versionado semántico | ningún documento del proyecto lo tiene |
| C7 | Reglas de actualización | ninguna fuente del proyecto las tiene; sería una capa nueva |

**Nota sobre C5 y C7:** son recomendables, pero el proyecto entero carece de ellas. Implementarlas
sólo en V6 crearía **una capa de autoridad nueva**, que es exactamente lo que la regla fundamental
de esta fase prohíbe. `SUPPORTED`.

**Balance: 9 requisitos, 9 fallan o no se demuestran.** V6 necesitaría 9 correcciones para ser
gobernable; 2 de ellas (R1, R2) son semánticas y afectarían al significado de otras dimensiones.

---

## 8. ANÁLISIS MÍNIMO DE E-6

### 8.1 El dato irreducible

El encargo propone seis candidatos: `verificador`, `productor`, `relación de independencia`,
`evidencia de revisión`, `fecha`, `alcance`. **No todos son necesarios.**

| Candidato | ¿Necesario? | Razón | Clasificación |
|---|---|---|---|
| `verificador` | **SÍ** | sin identidad del verificador no hay nada que independizar | `SUPPORTED` |
| `productor` | **SÍ** | la independencia es una **relación**; sin dos partes no hay relación | `SUPPORTED` |
| `relación de independencia` | **NO como campo** | es la **comparación** de los dos anteriores, no un tercer dato. Se deriva | `SUPPORTED` |
| `evidencia de revisión` | **DEPENDE** | sin ella, `verificador` es una declaración sin respaldo. Mínimo: identificador de artefacto | `SUPPORTED` |
| `fecha` | **NO para el hecho** | la fecha es provenance, no independencia. Se puede tener revisión sin fecha y no cambia el hecho | `SUPPORTED` |
| `alcance` | **SÍ** | sin alcance, «revisado» no distingue «revisé la afirmación» de «revisé el documento entero» | `PLAUSIBLE` |

**Mínimo irreducible: 3 campos — `verificador`, `productor`, `alcance`.**
`relación` se deriva comparando los dos primeros. `evidencia` es un identificador, no un texto.
`fecha` es provenance y no participa del hecho. `SUPPORTED`.

### 8.2 Hallazgo que condiciona toda decisión

```
VERIFIED_BY  = 0    REVIEWER   = 0    REVIEWED_BY = 0
AUTHORED_BY  = 0    ACTOR      = 0    CROSS_CHECK = 0
TIMESTAMP    = 0    TOOL_VERSION = 0
```

Campos que **sí** existen: `SHA256` (74), `AUDITED` (21), `SOURCE_OF_TRUTH` (15), `RUN_ID` (9),
`PROVENANCE` (6), `HOST_SCOPE` (4), `INDEPENDENT` (2, en prosa).

**El proyecto tiene provenance sobre *qué* y nunca sobre *quién*.** `OBSERVED`.

**Consecuencia para E-6:** cualquier representación de J requiere **crear provenance de identidad
que nunca ha existido en el proyecto**. No es «un campo más»: es una clase de provenance nueva.
Eso **desaconseja** cualquier opción que parezca barata (un atributo del finding, un campo más en
provenance) y **favorece** Forzaría las que la hacen explícita. `SUPPORTED`.

### 8.3 Mecanismos que ya partly cumplen la función

| Mecanismo | Dónde | Qué aporta | Qué no aporta | Clasificación |
|---|---|---|---|---|
| `VERIFICADO` | `R1-6` | cross-check como condición de clase de evidencia | **quién**; la definición la satisface el auto-contraste | `OBSERVED` |
| `NON_AUTHORITATIVE_REASON` | `DOCUMENTARY-RECONCILIATION` (6 valores) | marca de no-autoridad por motivo | ningún valor menciona identidad de verificador | `OBSERVED` |
| `AUTHORITY` / `AUTHORITATIVE` | `collector.py:1527,2687` | declara la **fuente** del criterio (`AGENTS_MD_OWNERSHIP_CRITERION`) | no registra quién verificó | `OBSERVED` |
| `REVIEW_REQUIRED` | `ROUTER:80` | mechanism de escalado a revisión editorial | no registra el resultado | `OBSERVED` |
| `LIMITATIONS=[… no independent validation]` | `DOCUMENTARY-RECONCILIATION` | única aparición del concepto, en negativo | no es campo consultable | `OBSERVED` |

---

## 9. ALTERNATIVAS DE REPRESENTACIÓN

**No se elige.**

| # | Alternativa | Información preservada | Información perdida | Ambigüedad | Complejidad | Compat. con N2 | Auditabilidad |
|---|---|---|---|---|---|---|---|
| **ALT-1** | **Dimensión propia (J)** | los 3 campos + la relación derivada | ninguna de los 3 | **baja** (1 eje ortogonal) | **alta**: 17ª dimensión | **baja**: 4 de sus términos no están en N2; el eje I de N2 no cubre J | **alta** (valor único y consultable) |
| **ALT-2** | **Provenance** (`verificador`, `productor`) | los 2 de identidad | **alcance**; y la relación se derivaría fuera del modelo | **media**: no se distingue revisor de productor sin convención nueva | **media**: 2 campos en un esquema existente | **alta**: N2 §Regla ya gobierna provenance semántico | media: campos sueltos, no consultables como estado |
| **ALT-3** | **Metadata de revisión** (bloque por documento) | los 3 por documento | **granularidad**: no por afirmación. Un documento con 50 afirmaciones queda con 1 valor | **alta**: mezcla revisión de documento con revisión de afirmación | baja | media | **baja**: sin índice |
| **ALT-4** | **Atributo del finding** | los 3 por hallazgo | **nada**, si el finding es la unidad | **media**: se confunde con `FINDING_STATE` (B), que ya existe y significa otra cosa | **baja** | media | alta |
| **ALT-5** | **Estado de gate** (`GO`/`NO_GO` sobre revisión) | que la revisión fue condición de avance | **quién revisó**; y el gate nunca se ejecutó (`GO_C1=NOT_AVAILABLE` en 20+ ficheros) | **baja** (reutiliza E) | **baja** | media | media: `NO_GO` no distingue «no revisado» de «revisado y rechazado» |
| **ALT-6** | **Composición de campos** (`X_BY_INDEPENDENT`) | los 3 por composición | **nada formalmente** | **alta**: el operador `/` tiene 513 patrones y **5 funciones**, ninguna declarada | media | baja | **baja**: no es indexable |

### Lectura transversal

- **Ningún `CONFLICT` abierto entre dimensiones**: las 6 son representables.
- **Sólo ALT-1 preserva los 3 campos con baja ambigüedad.** Las otras 5 pierden al menos un campo
  o la granularidad.
- **Sólo ALT-1 tiene conflicto de compatibilidad con N2** — y ese conflicto es informativo: si J se
  crea, **N2 queda formalmente incompleta**, lo que es una razón más (y no una objeción) para que
  N2 se reformule como parte del mismo cambio.
- **ALT-4 es la más barata y la más ambigua**: se solapa con `FINDING_STATE`.
- **ALT-6 es la peor**: se apoyaría en un operador que ya se demonstró no declarado y multifunción.

`SUPPORTED`. **Ninguna alternativa se elige aquí.**

---

## 10. PROTOCOLO DE REVISIÓN INDEPENDIENTE

> **Este protocolo NO es una revisión.** Es su definición. Quien lo ejecute no debe haber escrito
> los análisis previos. Si lo ha escrito, su revisión **no cuenta** (RC-4).

### 10.1 Precondiciones para el revisor

| # | Precondición | Verificable |
|---|---|---|
| P1 | No haber redactado `MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md` | por autoría |
| P2 | No haber redactado `MIG-07-VOCABULARY-MAPPING-20260926T011531Z.md` | por autoría |
| P3 | No haber redactado `MIG-07-INDEPENDENT-REVIEW-20260926T011531Z.md` | por autoría |
| P4 | No haber redactado `MIG-07-SEMANTIC-MODEL-20260926T015000Z.md` | por autoría |
| P5 | No haber redactado `MIG-07-AUTHORITY-AND-INDEPENDENT-VERIFICATION-20260926T022000Z.md` | por autoría |
| P6 | No haber redactado este documento | por autoría |
| P7 | Tener acceso de lectura al repo | — |
| P8 | Poder afirmar «no encontré» sobre un término | requiere búsqueda exhaustiva |

### 10.2 Método obligatorio: **muestreo de usos reales**, no sólo grep

| Regla | Detalle |
|---|---|
| **M1** | Para cada ítem de la muestra (§11), leer **el contexto completo** del uso, no la línea |
| **M2** | Mínimo **3 usos distintos** por término, de **≥3 ficheros distintos**, salvo que el término tenga <3 usos (entonces se documenta) |
| **M3** | Incluir obligatoriamente ≥1 uso **negativo o contradictorio** si existe |
| **M4** | Registrar la **clasificación revisada** de cada uso,REE separadamente de la del autor |
| **M5** | Prohibido concluir desde grep: cada afirmación debe citar `fichero:línea` |
| **M6** | Si un término no aparece, registrar `NOT_AVAILABLE` — **no inferir** su semántica |

### 10.3 Ítems de la muestra (14, según encargo)

| # | Ítem | Dónde muestrear | Pregunta al revisor |
|---|---|---|---|
| **S1** | `VERIFIED` | ≥6 usos, incluyendo ≥1 de `PRIOR-ART.md` (familia VF-7) y ≥1 de `00-MAESTRO-PROYECTO.md` (leyenda VF-6) | ¿Las 8 familias son distinguibles? ¿Falta alguna? |
| **S2** | `REPRODUCIBLE` | `RX550_BUILD_SPECIFICATION.txt`, `R1-6`, `MASTER-PLAN` | ¿`VERIFICADO` y `REPRODUCIBLE` son distinguibles en uso real, o son sinónimos? |
| **S3** | `DOCUMENTED` | `03-ARBOL` (regla), `MASTER-PLAN` (escalera), `FASE-G` | ¿Pertenece al eje I o al eje A, o a ambos? |
| **S4** | `PASS` | ≥6 usos: ≥1 de cada rol PF-1..PF-6, incluido ≥1 arista de diagrama | ¿El rol de arista es un estado? |
| **S5** | `UNKNOWN` | ≥4 usos, ≥1 en columna `Estado` de V4 | ¿Es un eje o una etiqueta transversal? |
| **S6** | `SUPPORTED` | ≥4 usos, ≥1 dentro de V6 y ≥1 en la escalera de `00-MAESTRO` | ¿Definirlo resolvería R1 de V6, o crearía un conflicto nuevo? |
| **S7** | `PARTIALLY VERIFIED` | ≥3 usos, ≥1 con grafía `PARTIALLY_VERIFIED` | ¿Las dos grafías son el mismo término? |
| **S8** | `GO`/`NO_GO`/`ABORT` | `C1-ISOLATION-DESIGN-v1.0.md`, ≥1 preflight | ¿`NO_GO_PRE` es una variante o un estado distinto? |
| **S9** | Operador `/` | ≥10 pares, ≥1 de cada función (1–5) | ¿Las funciones 4–5 deben entrar en el modelo? |
| **S10** | `SOURCE_OF_TRUTH` | las 14 cabeceras de diagrama + `DOCUMENTARY-RECONCILIATION` | ¿Es una declaración de autoridad o un índice de fuentes? |
| **S11** | Documentos `DRAFT/CONFLICT` | ≥4, incl. `09-`, `10-`, `13-`, `00-MAESTRO` | ¿La autodeclaración `DRAFT/CONFLICT` invalida su `SOURCE_OF_TRUTH`? |
| **S12** | `AGENTS.md` | §Evidence vocabulary, §Documentation and provenance, §Current project state | ¿Define, referencia o ambas? |
| **S13** | V6 completo | las 27 filas + §Regla de evidencia | ¿Es autocontenido? ¿Qué términos le faltan? |
| **S14** | V4 | las 4 primeras filas de la matriz + §Regla de lectura | ¿Es derivado? ¿Su `Estado` contradice a V6? |

### 10.4 Preguntas de falsación obligatorias

| # | Pregunta | Refuta si la respuesta es afirmativa |
|---|---|---|
| **F1** | ¿Existe una regla de precedencia que determine la autoridad del vocabulario y que este análisis no encontró? | `PRECEDENCE_RULE=NOT_AVAILABLE` |
| **F2** | ¿`DOCUMENTATION-GAPS §7` es una lista de **supresión de estado** o un simple inventario? Si es inventario, E11 no es una arista de autoridad | §2.2 E11 |
| **F3** | ¿`DECISIONES-D1-D10:393` («mantener como taxonomía») clasificó V6 o sólo propuso no tocarlo? | §2.2 E12 |
| **F4** | ¿`AGENTS.md` es una capa más de autoridad, o el mecanismo operativo que el router elige? | §5 F |
| **F5** | ¿V6 y N2 son el mismo documento? (confusión documental posible) | todo §5 |
| **F6** | ¿El «No elegir» del router se refiere a fuentes de contenido, no a documentos normativos? | §3 P5 |
| **F7** | ¿Existe un documento no inspeccionado que declare `AUTHORITY` sobre vocabulario? | §2 |
| **F8** | ¿Las 5 reglas de precedencia son en realidad una sola, dispersa? | §3 |
| **F9** | ¿`DIAGNOSTIC ONLY` tiene 0 usos porque el término se escribe de otra forma, o porque no se usa? | §7 R2 |
| **F10** | ¿La separación de dimensiones de §5/§6 elimina el conflicto, o sólo lo hace más pequeño? | §5, §6 |
| **F11** | ¿El mínimo irreducible de E-6 son realmente 3 campos, y no 2? | §8.1 |
| **F12** | ¿`NON_AUTHORITATIVE_REASON` ya implementa J? | §8.3 |

### 10.5 Restricciones del revisor

- **NO** modificar ningún archivo del repositorio. Entregar el informe como texto.
- **NO** crear documento de autoridad.
- **NO** elegir autoridad entre N1 y N2 (P5 lo prohíbe).
- **NO** usar `VERIFIED` ni `PASS` como categoría de clasificación.
- Registrar explícitamente **qué ítems de la muestra no pudo revisar** y por qué.

---

## 11. MUESTRA PROPUESTA

Mínimo **60 usos** distribuidos:

| Estrato | Ítems | Usos mínimos | Ficheros mínimos |
|---|---|---|---|
| **Colisionados** | S1, S2, S3, S4, S5, S6, S7 | 24 | 12 |
| **Gobernanza** | S8, S10, S11, S12, S13, S14 | 18 | 8 |
| **Composición** | S9 | 10 | 5 |
| **Positivos** (uso conforme a la definición declarada) | cualquiera | 8 | 5 |
| **Negativos** (uso que viola la definición declarada) | cualquiera | 8 | 5 |

**Distribución mínima por fichero: 1 uso máximo por fichero y por sección**, para evitar que un
documento muy citado domine la muestra. `OBSERVED` — método propuesto, no aplicado.

---

## 12. CRITERIOS DE ACEPTACIÓN / RECHAZO

### Aceptación (todas las 8 necesarias)

| # | Criterio |
|---|---|
| **A1** | Todas las precondiciones P1–P8 cumplidas y declaradas |
| **A2** | ≥60 usos revisados con `fichero:línea` en cada conclusión |
| **A3** | Los 14 ítems de muestra cubiertos, o los no cubiertos declarados con motivo |
| **A4** | Las 12 preguntas F1–F12 respondidas explícitamente |
| **A5** | Al menos **3 refutaciones** del análisis previo, o justificación de por qué no hay ninguna |
| **A6** | Método de muestreo (§10.2) aplicado y declarado |
| **A7** | Clasificaciones usando sólo el vocabulario permitido |
| **A8** | Informe que **no** elige autoridad entre N1 y N2 |

### Rechazo (cualquiera)

| # | Criterio de rechazo |
|---|---|
| **R1** | El revisor redactó alguno de los 6 documentos de la fase MIG-07 |
| **R2** | Conclusiones sin `fichero:línea` |
| **R3** | Usa `VERIFIED` o `PASS` como categoría de clasificación |
| **R4** | Elige autoridad entre N1 y N2 sin resolver F1 y F6 |
| **R5** | Crea o modifica un archivo del repositorio |
| **R6** | No responde F1–F12 |
| **R7** | Muestra < 60 usos o concentrada en < 15 ficheros |
| **R8** | Declara MIG-07 `CLOSED` |

---

## 13. CONTRADICCIONES PENDIENTES

| # | Contradicción | Tipo | Dimensión | Estado | Quién puede resolverla |
|---|---|---|---|---|---|
| **X1** | Router `VOCABULARY` = `REVIEW_REQUIRED` sin escalar | proceso | gobernanza | `OPEN` | revisión editorial (**P5**) |
| **X2** | `CONFLICT` definido como hecho (N1) vs hecho+regla (N2) | **semántica** | A vs K | `OPEN` | decisión editorial |
| **X3** | N2 usa `SUPPORTED` sin definirlo (dependencia no declarada de N1) | **semántica** | A | `OPEN` | decisión editorial |
| **X4** | P4 de N2 es circular: «el texto canónico prevalece» sin declarar cuál | lógica | I | `OPEN` | decisión editorial |
| **X5** | N2 en la lista de «no fuente de estado» vs 2 diagramas que la nombran `SOURCE_OF_TRUTH` | gobernanza | I | `OPEN` | revisión editorial |
| **X6** | V6 `DIAGNOSTIC ONLY` (0 usos) vs corpus `DIAGNOSTIC` (21) | **semántica** | M | `OPEN` | decisión editorial |
| **X7** | `PASS` con 6 roles y sin definición | **semántica** | F/D/E/P | `OPEN` | decisión editorial |
| **X8** | `VERIFIED` con polaridad invertida (VF-1 vs VF-7) | **semántica** | A | `OPEN` | decisión editorial |
| **X9** | `VERIFICADO` y `REPRODUCIBLE` solapados | **semántica** | A vs H | `OPEN` | decisión editorial |
| **X10** | Operador `/`: 513 patrones, 5 funciones, 0 declaraciones | **semántica** | P | `OPEN` | decisión editorial |
| **X11** | 2 dimensiones del encargo inexistentes: C, J | modelo | — | J propuesta; C sin resolver | decisión editorial |
| **X12** | N10 coloca N8 #1 sin excluir estado actual | **redundada** (§6) | gobernanza | `PLAUSIBLE` | — |

**Corregidas en esta fase:** la contradicción `MASTER-RESEARCH-STATUS.md` (antes X-candidata,
reportada como nº10 en la fase anterior) **se degrada a `PLAUSIBLE` y se re-clasifica** como
omisión de calificador en documento `DRAFT`. Se registra la corrección. `SUPPORTED`.

**Ninguna contradicción se resuelve aquí.** `OBSERVED`.

---

## 14. ESTADO MIG-07

```
MIG-07=VERIFYING

E1_RESULT=AUTHORITY_CONFLICT
PRECEDENCE_RULE=NOT_AVAILABLE
E6_RESULT=DIMENSION_REQUIRED_NOT_IMPLEMENTED
E6_IMPLEMENTED=0

AUTHORITY_DOCUMENT_CREATED=0
ARBITRARY_AUTHORITY_CHOSEN=0
V6_MODIFIED=NO   AGENTS_MODIFIED=NO
MIGRATIONS_APPLIED=0  TERMS_ADDED=0  TERMS_RENAMED=0  TERMS_REMOVED=0
IDENTITY_PROVENANCE_EXISTING=0   (VERIFIED_BY/REVIEWER/AUTHORED_BY/ACTOR = 0)
E6_MINIMUM_IRREDUCIBLE=3 campos (verificador, productor, alcance)
E6_ALTERNATIVES_EVALUATED=6   E6_ALTERNATIVE_CHOSEN=0

RULES_OF_PRECEDENCE_FOUND=5   COVERING_VOCABULARY=1 (y ordena NO elegir)
CONTRADICTIONS_OPEN=11   CONTRADICTIONS_CORRECTED=1
REVIEW_PROTOCOL_READY=YES   REVIEW_PROTOCOL_EXECUTED=0
CLOSURE_CRITERIA_MET=4/13

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

### Criterio de cierre (§FASE 9)

| # | Requisito | Estado |
|---:|---|---|
| 1 | Autoridad resuelta **o formalmente declarada inexistente** | **PARCIAL**: `AUTHORITY_CONFLICT` + `PRECEDENCE_RULE=NOT_AVAILABLE`. Falta resolver X1–X5 |
| 2 | Modelo semántico estable | **NO**: 11 contradicciones abiertas |
| 3 | E-6 representado de forma decidida | **NO**: 6 alternativas evaluadas, ninguna elegida |
| 4 | **Revisión independiente real** | **NO**: protocolo listo, no ejecutado |
| 5 | Contradicciones críticas resueltas | **NO** |
| 6 | Provenance suficiente | **NO**: 0 identidad; 4 nodos de autoridad sin hash; 2 untracked |
| 7 | Vocabulario sin pérdida semántica | **NO**: 15 pérdidas confirmadas |
| 8 | Gate de migración preparado | **NO** |
| 9 | Ningún cambio operativo pendiente | **SÍ** |
| 10 | Documentación consistente | **NO** |

**1 de 10. MIG-07 no puede cerrarse.**

---

## 15. LIMITACIONES

1. **Este documento no declara autoridad** y por tanto no resuelve E-1 por sí mismo. Tampoco
   podría: hacerlo violaría la regla fundamental de esta fase y P5. `OBSERVED`
2. **`PRECEDENCE_RULE=NOT_AVAILABLE` es un resultado de búsqueda negativa.** Con 24 términos y
   3 métodos, un término ausente del patrón («jerarquía», «manda», `binding`) podría escaparse. La fase
   anterior falló dos veces por cobertura. `UNKNOWN`
3. **La clasificación de V6 como `REFERENCE` (E10) y supresión de estado (E11) provienen de
   documentos `UNTRACKED` y congelados.** No son normativa; son evidencia de clasificación.
   `PLAUSIBLE`
4. **La regla de separación de dimensiones de §5/§6 es una reconstrucción mía**, no una
   declaración del proyecto. `PLAUSIBLE`
5. **mtime no es evidencia de creación.** Los ficheros tienen mtime `2026-09-25` en bloque
   (escritura por lote). Sólo se usaron fechas declaradas. `NOT_AVAILABLE`
6. **Los conteos de `AGENTS.md` incluyen 15 secciones**; no se auditó si alguna redefine
   vocabulario más allá de §Evidence vocabulary. `UNKNOWN`
7. **E-6 no se implementó ni se probó.** El mínimo de 3 campos no tiene instancia que lo valide. `UNKNOWN`
8. **No se leyeron las 1321 filas `RAW_EVIDENCE`**: sólo documentos normativos y muestreo. `UNKNOWN`
9. **Autoría: la misma que produjo las 8 refutaciones previas (K-1..K-8).** Sesgo conocido, no
   mitigado. Es exactamente lo que exige el protocolo de §10. `SUPPORTED`
10. **La muestra propuesta no se ejecutó.** §11 es un diseño, no un resultado. `OBSERVED`
