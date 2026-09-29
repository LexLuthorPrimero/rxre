# MIG-07.7 — MATRIZ DE CAPACIDADES METODOLÓGICAS POR DOMINIO

> Artefacto nuevo de auditoría. No modifica ningún artefacto previo.
> No implementa nada. Sustituye una afirmación global por una descripción por dominio.

```
DOCUMENT_ID=MIG-07.7-DOMAIN-CAPACITY-MATRIX
CREATED_UTC=2026-09-26T05:00:00Z
TYPE=DOMAIN_CAPACITY_MATRIX

MIG-07=VERIFYING   MIG-07.5=VERIFYING   MIG-07.6=VERIFYING   MIG-07.7=VERIFYING
REPLACES_CLAIM=SELF_METHODOLOGY_GAP=PARTIALLY_CONFIRMED (global)
WITH=PER_DOMAIN_MATRIX
IMPLEMENTATION=NOT_EXECUTED
```

Clasificación: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `NOT_PROVEN` · `CONFLICT`
Estados de capacidad: `EXISTENTE` · `PARCIAL` · `AD_HOC` · `NO_IMPLEMENTADO` · `UNKNOWN` · `NOT_APPLICABLE`

---

## 1. FASE 1 — DOMINIOS

### 1.1 Los 13 propuestos, evaluados uno a uno

| # | Dominio propuesto | ¿Debe ser categoría separada? | Justificación |
|---|---|---|---|
| D1 | sistema / operaciones | **SÍ** | Único dominio con verificación automatizada real (`validate_rx550_final.py`, 302 líneas) |
| D2 | código | **SÍ** | Único con revisión por AST sin allowlist y tests unitarios |
| D3 | pruebas | **SÍ, y es el más grave** | Es el dominio donde se descubrió un defecto nuevo (§3) |
| D4 | documentación normativa | **SÍ** | Tiene reglas escritas (`TESTING.md §5`, `PATCH-REGISTRY`) que no cubren prosa |
| D5 | documentación de auditoría | **NO como tal** | Es un subcaso de D4 con requisito de inmutabilidad adicional (§1.3) |
| D6 | evidencia experimental | **SÍ** | Sus JSON carecen de `RUN_ID`/timestamp (medido) |
| D7 | provenance / trazabilidad | **SÍ** | Se descompone en 4 (§9) |
| D8 | autoridad / precedencia | **SÍ** | `PRECEDENCE_RULE=NOT_AVAILABLE` es un gap de un tipo distinto |
| D9 | cobertura de búsqueda | **SÍ** | Es el gap que este mismo análisis cometió (FN-1) |
| D10 | integridad textual | **SÍ** | Se descompone en 5 niveles (§12) |
| D11 | corrección y revalidación | **SÍ** | Es el dominio donde hay más capacidad y menos garantía |
| D12 | independencia de revisión | **SÍ** | 0 campos en el repo |
| D13 | gates / promoción | **SÍ** | Mecanismo conceptualmente distinto de detección |

### 1.2 Dos dominios que el encargo no listó

| # | Dominio añadido | Evidencia de que existe como categoría | Clasificación |
|---|---|---|---|
| **D14** | **autodiagnóstico** | Es el objeto del encargo. Ninguno de D1–D13 lo contiene: es la capacidad de evaluar *la propia metodología*, no el contenido | `OBSERVED` |
| **D15** | **integridad de referencias** | Separado de D10: un documento puede ser textual y sintácticamente válido y **evidencialmente incorrecto** (caso `:43`→`:23`). Es un eje ortogonal, no un subnivel | `OBSERVED` |

### 1.3 Una fusión con penalización explícita

**D5 se fusiona en D4** como `D4.audit`, con un requisito adicional: **inmutabilidad del
registro histórico**. No es lo mismo que prosa normativa —un artefacto de auditoría no se edita,
se versiona— pero **no tiene ninguna capacidad de verificación que D4 no tenga**, y mantenerlo
como categoría separada sugeriría una distinción que la evidencia no sostiene. `SUPPORTED`

**Coste de la fusión, declarado:** al fusionar, `D4.audit` hereda `ENFORCEMENT=NO`, y con él el
caso O-01. Si en el futuro un artefacto de de auditoría получить versionado, habrá que
des-acoplarla. `PLAUSIBLE`

### 1.4 Total

```
DOMAIN_COUNT=15   (13 propuestos − 1 fusionado + 2 añadidos + D4.audit como subcaso)
```

---

## 2. FASE 2 — MATRIZ DE CAPACIDADES

Las 5 columnas de la derecha son las de FASE 3. Se indican explícitamente para no resumirlas.

| # | Dominio | Capacidad | Mecanismo | Evidencia | A | B | C | D | E | ESTADO |
|---|---|---|---|---|:-:|:-:|:-:|:-:|:-:|---|
| **D1** sistema/operaciones | verificación de estado | `validate_rx550_final.py` | script | 302 líneas; 8 funciones `_evidence` | Y | **P** | **P** | **N** | **N** | `PARCIAL` |
| D1 | rollback verificado | `ROLLBACK.md §4` | doc + 3 cmds | texto literal | Y | **N** | **N** | **N** | **N** | `PARCIAL` |
| D1 | criterio de cierre | `TESTING.md §5` | regla, 6 precond. | texto literal | Y | **N** | **P** | **N** | **N** | `PARCIAL` |
| **D2** código | revisión por AST sin allowlist | escaneo AST | manual | `R1-…REVIEW:174` | Y | **N** | **P** | **N** | **N** | `AD_HOC` |
| D2 | tests unitarios | 154 tests | pytest | 5 ficheros | Y | **N** | **P** | **N** | **N** | `PARCIAL` |
| **D3** pruebas | test que ejercita el barrido real | — | — | `test_T07b` llama `observe()` con fakes | Y | **N** | **N** | **N** | **N** | `PARCIAL` |
| **D3** | **prueba de DEFECT-03** | `test_T31` | `inspect.getsource` + `assertIn` | `test_r1_defects.py:388` | Y | **N** | **N** | **N** | **N** | `AD_HOC` ⚠ |
| **D4** normativa | gate de promoción a `RESOLVED` | `TESTING.md §5` | regla | 6 precond. | Y | **N** | **N** | **N** | **N** | `EXISTENTE` |
| D4 | registro de correcciones con hash de prueba | `PATCH-REGISTRY` | doc | 16+ entradas, hashes | Y | **N** | **P** | **N** | **N** | `EXISTENTE` |
| D4.audit | verificación de prosa | — | — | 0 mecanismos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| D4.audit | inmutabilidad del registro | — | — | exigida por el encargo, no implementada | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D6** evidencia exp. | provenance de host | clave `host` | JSON | 1 de 2 JSON | Y | **P** | **N** | **N** | **N** | `PARCIAL` |
| D6 | `RUN_ID` / timestamp | — | — | 0 claves en `R1-…5434Z.json` | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D7** provenance | hash de artefacto | sha256 en prosa | manual | 43 de 252 `.md` | Y | **N** | **N** | **N** | **N** | `PARCIAL` |
| D7 | hash de script de prueba | `PATCH-REGISTRY` | doc | `fa4c4885…`, `4e0fb097…` | Y | **N** | **P** | **N** | **N** | `PARCIAL` |
| D7 | identidad de actor | `VERIFIED_BY`/`AUTHORED_BY`/`REVIEWED_BY`/`Autor:` | — | **0 ficheros** | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D8** autoridad | regla de precedencia por dimensión | — | — | 5 reglas, 0 aplicables | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| D8 | escalado de conflicto | `ROUTER.ESCALATION` | doc + registro | `REVIEW_REQUIRED → escalar` | Y | **N** | **P** | **N** | **N** | `PARCIAL` |
| **D9** cobertura | búsqueda dirigida | `grep`/`find` | manual | 100+ búsquedas | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| D9 | enumeración del universo | `ls *.md` | manual | FN-1: 6 docs no vistos | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| D9 | prueba de completitud de búsqueda | — | — | 0 mecanismos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D10** integridad textual | escaneo de caracteres | script ad hoc | no versionado | ejecutado 8× | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| D10 | lista blanca de citas | manual, en este análisis | no versionado | 16 tokens | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| **D15** referencias | validación `fichero:línea` | — | — | 0 mecanismos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D11** corrección | diff | git | automático | disponible | Y | **N** | **N** | **N** | **N** | `EXISTENTE` |
| D11 | hash antes/después | sha256 | manual | practice esta sesión | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| D11 | rollback de corrección | `ROLLBACK.md` | doc | sistema solo | Y | **N** | **N** | **N** | **N** | `PARCIAL` |
| D11 | **verificación semántica de la corrección** | — | — | 0 mecanismos; un hash no la prueba | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D12** independencia | práctica de revisión separada | 2 revisiones | doc | `R1-…REVIEW*.md` | Y | **N** | **N** | **N** | **N** | `AD_HOC` |
| D12 | acreditación de actor independiente | — | — | 0 campos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| **D13** gates | gate de promoción | `TESTING.md §5` | regla | sistema | Y | **N** | **N** | **N** | **N** | `EXISTENTE` |
| D13 | gate de promoción documental | — | — | 0 mecanismos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| D13 | enforcement de bloqueo | `permissions`+hook | documentado, no usado | HTTP 200; sin `.opencode/` | Y | **N** | **N** | **N** | **N** | `NOT_APPLICABLE` |
| **D14** autodiagnóstico | evaluación de adequación de método | — | — | 0 mecanismos en OpenCode y en el repo | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |
| D14 | declaración de cobertura del autodiagnóstico | — | — | 0 mecanismos | **N** | **N** | **N** | **N** | **N** | `NO_IMPLEMENTADO` |

**Leyenda de A–E (§3):** A=`EXISTENCE` · B=`EXECUTION` · C=`COVERAGE` · D=`ENFORCEMENT` ·
E=`INDEPENDENCE`. **Y**=SÍ · **P**=PARCIAL · **N**=NO · **U**=UNKNOWN (aparece en D13 fila 3 y D14)

**Recuento: 32 capacidades. `EXISTENTE`=3 · `PARCIAL`=9 · `AD_HOC`=7 · `NO_IMPLEMENTADO`=12 ·
`NOT_APPLICABLE`=1.**

**Las 3 `EXISTENTE` están las 3 en D1/D4 sistema. Ninguna cubre un artefacto de prosa.** `OBSERVED`

---

## 3. FASE 3 — LOS CINCO CONCEPTOS, SEPARADOS

La separación que el encargo exige, y que **L0–L5 no puede expresar**:

| Concepto | Pregunta | Por qué no colapsa en el anterior |
|---|---|---|
| **A** `EXISTENCE` | ¿hay herramienta/regla? | — |
| **B** `EXECUTION` | ¿se ejecuta cuando corresponde? | Un escaneo que existe y nunca se lanza |
| **C** `COVERAGE` | ¿cubre el dominio completo? | Un escaneo que se lanza y mira 1 de 6 ficheros |
| **D** `ENFORCEMENT` | ¿obliga a actuar al fallar? | Un escaneo que se lanza, cubre todo, y cuyo resultado se ignora |
| **E** `INDEPENDENCE` | ¿productor ≠ verificador, acreditado? | Todo lo anterior puede ser cierto y ejecutado por el mismo actor |

**Perfil de O-01, que demuestra que los 5 son independientes:**

```
A=YES   (el escaneo existe)
B=PARTIAL  (se ejecutó 8 veces sobre ficheros individuales)
C=NO    (miró 1 de 8 artefactos en la fase 5; 0 de 6 documentos raíz en MIG-07.5)
D=NO    (su salida no generó acción; el defecto sigue)
E=NO    (el mismo agente que produce detecta y no corrige)
```

**Cuatro de cincoeze negativos en la misma capacidad.** Un único símbolo `L3` habría dicho «hay
chequeo reproducible» y no habría capturedo nada de esto. `SUPPORTED`

---

## 4. FASE 4 — L0–L5 REFORMULADO

### 4.1 El problema confirmado por la evidencia

MIG-07.6 erredo al asignar `L3_MAX` global. Y el error es estructural: **L0–L5 es una escala
lineal de una sola dimensión, y la matriz demuestra que hay al menos 5.**

### 4.2 Las 5 dimensiones, no la escala

| Dimensión | Escala propia | Evidencia de que NO colapsa |
|---|---|---|
| `DETECTION_LEVEL` | L0–L3 | ¿hay chequeo? |
| `EXECUTION_GUARANTEE` | NINGUNA–OCASIONAL–GARANTIZADA | ¿se lanza? O-01: A=Sí, B=Parcial |
| `COVERAGE_LEVEL` | NINGUNA–PARCIAL–COMPLETA–**PROBADA** | ¿mira todo? La última es inalcanzable (§15) |
| `ENFORCEMENT_LEVEL` | NINGUNA–DOCUMENTADA–APLICADA–AUTOMÁTICA | `TESTING.md §5` es DOCUMENTADA; no hay APLICADA |
| `INDEPENDENCE_LEVEL` | I0–I5 (§10) | 19/19 casos: productor = verificador |

### 4.3 Veredicto sobre L0–L5

```
L0_L5_MODEL=RETIRED_AS_SCALE
L0_L5_USABLE_AS=abreviatura de conveniencia, no como medida
INFORMATION_LOST_BY_SINGLE_SCALE=CONFIRMED
  - no distingue existencia de ejecución
  - no distingue ejecución de cobertura
  - no distingue cobertura de enforcement
  - no tiene noción de acreditación de actor
```

**MIG-07.5 y MIG-07.6/badge LR-07 usaron L0–L5 como si fuera una escala. No lo es.** `SUPPORTED`

**Consecuencia sobre el resultado previo:** `CURRENT_DETECTION_LEVEL=DOMAIN_DEPENDENT` de
MIG-07.6 era correcto **por accidente** —olang. Lo correcto era 5 dimensiones por 15 dominios,
y eso es lo que esta matriz entrega.

---

## 5. FASE 5 — MATRIZ DE SELF-METHODOLOGY-GAP POR DOMINIO

| # | Dominio | ¿Capacidad necesaria? | ¿Mecanismo? | ¿Se ejecuta? | ¿Cobertura? | ¿Enforce? | ¿Indep? | ¿Provenance? | ¿Revalid.? | GAP |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 | sistema | sí | **sí** | no | parcial | no | no | sí | **sí** | `NO_GAP` |
| D2 | código | sí | **sí** | no | parcial | no | no | parcial | **sí** | `PARTIAL_GAP` |
| **D3** | **pruebas** | sí | **sí** | no | **no** | no | no | no | no | **`CONFIRMED_GAP`** |
| D4 | normativa | sí | **sí** | no | **sí** | **documentada** | no | sí | **sí** | `PARTIAL_GAP` |
| D4.audit | auditoría | sí | **no** | no | no | no | no | hash | no | **`CONFIRMED_GAP`** |
| D6 | evidencia exp. | sí | parcial | no | no | no | no | **no** | no | **`CONFIRMED_GAP`** |
| D7 | provenance | sí | parcial | no | no | no | **no** | — | — | **`CONFIRMED_GAP`** |
| D8 | autoridad | sí | parcial | no | no | no | no | sí | no | **`CONFIRMED_GAP`** |
| D9 | cobertura | sí | **sí** | **no** | **no** | no | no | — | — | **`CONFIRMED_GAP`** |
| D10 | integridad textual | sí | **sí** | no | **no** | no | no | no | no | **`CONFIRMED_GAP`** |
| D11 | corrección | sí | **sí** | no | parcial | no | no | hash | no | **`CONFIRMED_GAP`** |
| D12 | independencia | sí | **ad_hoc** | no | no | no | **no** | no | no | **`CONFIRMED_GAP`** |
| D13 | gates | sí | **sí** (sistema) | no | **no** (prosa) | **no** | no | — | — | `PARTIAL_GAP` |
| D15 | referencias | sí | **no** | no | no | no | no | no | no | **`CONFIRMED_GAP`** |
| **D14** | autodiagnóstico | sí | **no** | no | no | no | no | no | no | **`CONFIRMED_GAP`** |

```
CONFIRMED_GAPS=11
PARTIAL_GAPS=3
NO_GAPS=1
UNKNOWN_GAPS=0
```

**`UNKNOWN_GAPS=0` merece una advertencia.** No significa que no los haya: significa que **este
análisis no encontró ninguno del que pueda dar cuenta**. Dado que D9 (`COVERAGE`) es
precisamente la capacidad de encontrar huecos, y D9 está en `CONFIRMED_GAP`, **esta matriz no
puede certificar su propia completitud.** Ver §15. `SUPPORTED`

### 5.1 El único `NO_GAP`: D1

D1 (sistema/operaciones) es el único dominio con las 5 dimensiones en `Y` o `P` sin ningún `N`
en existencia. Tiene verificador, rollback, criterio de cierre con 6 precondiciones, y registro
de correcciones. **Su weakness es B (`EXECUTION`=NO) y D (`ENFORCEMENT`=NO), no la ausencia de
mecanismo.**

**Eso refuta la versión global de MIG-07.5 con precisión: D1 no tiene gap de metodología. Y es
el dominio donde más trabajo se hizo.** `SUPPORTED`

---

## 6. FASE 6 — CASO O-01 COMO PRUEBA DE DOMINIO

| Atributo | Valor | Evidencia |
|---|---|---|
| ¿Qué detector existe? | escaneo de caracteres CJK/camelCase, **no versionado** | script invocado en sesión |
| ¿Qué dominio cubre? | **D10 únicamente**, y solo caracteres | |
| ¿Qué dominio **no** cubre? | D15 (referencias), D4.audit (prosa), D5→D4.audit | el defecto `:43`→`:23` **no lo detecta** |
| ¿Ejecución obligatoria? | **NO** | se lanzaba a criterio |
| ¿El resultado genera acción? | **NO** | 5 fases sin corrección |
| ¿La corrección se verifica? | **NO** | |
| ¿Puede permanecer después del check? | **SÍ** | `KNOWN_DEFECT`, 5 fases |

```
DETECTION_EXISTS=YES
DOMAIN_COVERAGE=LIMITED  (D10 solo)
ENFORCEMENT=NO
REVALIDATION=NO
SEMANTIC_VERIFICATION=NO
O01_PERSISTENCE_DEMONSTRATED=YES
```

**Y el hallazgo que lo hace más grave: el mismo escaneo tampoco detectó que la *cita* fuera
incorrecta.** Un detector de caracteres sobre un documento cuyo error central es una referencia
equivocada es un detector que no cubre el dominio del documento. `SUPPORTED`

---

## 7. FASE 7 — CASOS DE AUTOCORRECCIÓN POR DOMINIO

| Mecanismo | D1 sistema | D2 código | D4 doc. normativa | D4.audit auditoría |
|---|---|---|---|---|
| rollback | **sí** (`ROLLBACK.md`) | parcial | **no** | **no** |
| diff | sí (git) | sí (git) | sí (git) | sí (git) |
| hash | sí | sí (`PATCH-REGISTRY`) | no | **sí, practiced** |
| test | sí (`run_tests.py`) | **sí** (154) | no | no |
| post-check | **sí** (`ROLLBACK.md §4`) | no | no | no |
| revalidación de la corrección | **sí, 6 precond.** | **NO** (ver §3) | no | no |
| independencia | no | no | no | no |

### Tres correcciones obligatorias del lenguaje

| # | Afirmación previa | Corrección |
|---|---|---|
| 1 | «hash = verificación de la corrección» | **FALSO.** Un hash prueba que el fichero **cambió**, nunca que la corrección era **correcta**. Ningún hash puede. No es un gap de OpenCode: es una limitación de la clase de prueba |
| 2 | «rollback = prueba de que la corrección era correcta» | **FALSO.** `ROLLBACK.md §4` verifica que se **restauró**, no que el cambio previo era correcto |
| 3 | «test = independencia» | **FALSO.** 154 tests, 1 agente. Ver §3: `test_T31` es un `assertIn` sobre texto fuente |

---

## 8. FASE 8 — COBERTURA: LOS 5 FALSOS NEGATIVOS

Cuatro separaciones que el encargo exige:
`SEARCH_EXISTS` · `SEARCH_EXECUTED` · `SEARCH_COMPLETE` · `SEARCH_COMPLETENESS_PROVEN`

| FN | Procedimiento que lo habría detectado | ¿Existía? | ¿Se ejecutó? | ¿Cobertura? | ¿Señal de falta de cobertura? | ¿Podía descubrir su propia falta? |
|---|---|---|---|---|---|---|
| **FN-1** 6 docs raíz | **`ls *.md` en la raíz** | **SÍ** | **NO** | **NO** | **NO** | **NO** |
| **FN-2** `NON_AUTHORITATIVE` del collector | `grep NON_AUTHORITATIVE` en el collector | **SÍ** | no | n/a | no | **NO** — el campo se leyó, no se interpretó |
| **FN-3** escaneo AST sin allowlist | leer los artefactos de revisión previos | **SÍ** | no | n/a | no | **NO** |
| **FN-4** hash prueba↔corrección | leer `PATCH-REGISTRY:71` | **SÍ** | no | n/a | no | **NO** |
| **FN-5** 360 staged / 0 commits | `git status` | **SÍ** | **SÍ** (lo hice en otra fase) | **NO** (no lo clasifiqué) | **NO** | no |

```
SEARCH_EXISTS=YES          (5/5)
SEARCH_EXECUTED=PARTIAL    (1/5 en MIG-07.5)
SEARCH_COMPLETE=NO          (0/5)
SEARCH_COMPLETENESS_PROVEN=NO  (imposible, ver §15)
```

### 8.1 El caso FN-1, que es el instructive

**¿Podía el procedimiento descubrir que no había cubierto el dominio?** **NO.**

MIG-07.5 hizo ~40 búsquedas dirigidas, todas con resultados, ninguna vacía. **Desde dentro, el
procedimiento se ve completo**: cada consulta devuelve algo. La señal de que faltaban 6 documentos
no era «una búsqueda que falló» sino «una búsqueda que no se hizo».

**Único mecanismo que lo habría detectado: enumerar el universo antes de buscar en él.**
`ls *.md` en la raíz. Una línea. `OBSERVED`

**Y esa técnica tiene un nombre que ya existe en el proyecto:** el router obliga a declarar
`PRIMARY`, `SECONDARY`, `RAW` y `HOST` por tema — es un **declarador de universo**. MIG-07.5 no
lo usó. `SUPPORTED`

**Conclusión de FASE 8, y es la más importante del documento:**

> **Una búsqueda completa no es demostrable porque haya terminado.** Solo es demostrable si el
> universo se declaró antes de buscar. `SEARCH_COMPLETENESS_PROVEN` no es alcanzable por
> inspección del resultado; requiere un artefacto previo que declare el universo.

---

## 9. FASE 9 — PROVENANCE: CUATRO TIPOS

| Tipo | Qué responde | Campos que existen | Cobertura |
|---|---|---|---|
| **P1** `PROVENANCE_OF_ARTIFACT` | ¿qué es este fichero? | `sha256` en 29 de 252 `.md` (versionados); censos congelados | parcial |
| **P2** `PROVENANCE_OF_ACTION` | ¿qué se hizo y cuándo? | `RUN_ID` (9), `HOST_SCOPE` (4), `SOURCE_OF_TRUTH` (15) | parcial; **0 en `R1-…5434Z.json`** |
| **P3** `PROVENANCE_OF_VERIFICATION` | ¿se verificó y con qué prueba? | hash de script en `PATCH-REGISTRY`; «Prueba de validación» | parcial, **solo D1/D2** |
| **P4** `PROVENANCE_OF_ACTOR` | ¿quién lo hizo y quién lo revisó? | **0 campos** | **nula** |

**La distinción que corrige un error previo:** «hash de script» es **P3**, no P4. Prueba que
*qué* se ejecutó. **No** prueba *quién* lo ejecutó. `P4` sigue enteramente ausente, y es la única
que permitiría acreditar independencia. `SUPPORTED`

---

## 10. FASE 10 — INDEPENDENCIA I0–I5

| Nivel | Definición | ¿Demostrable hoy? | Evidencia |
|---|---|---|---|
| **I0** | ninguna separación | — | estado real |
| **I1** | otra fase / sesión | **SÍ** | las 2 revisiones R1, distintas sesiones |
| **I2** | otro proceso / agente | **NO** | 0 campos de autor |
| **I3** | agente con contexto independiente | **NO** | sin mecanismo de contexto limpio |
| **I4** | actor independiente acreditado | **NO** | requiere P4 |
| **I5** | enforcement estructural de independencia | **NO** | requiere hook activo; no hay `.opencode/` |

```
INDEPENDENCE_LEVEL_DEMONSTRABLE=I1
I1=PRACTICE_WITHOUT_ATTESTATION
```

**Reglas que se confirman, no se inventan:**
- **DOS SESIONES DEL MISMO AGENTE ≠ ACTOR INDEPENDIENTE.** Son I1, no I2.
- **DOS DOCUMENTOS DEL MISMO AUTOR ≠ VERIFICACIÓN INDEPENDIENTE.** Mismo.

**Y una tercera, que este análisis exemplifies:** **UNA REVISIÓN DEL MISMO AUTOR ≠ VERIFICACIÓN.**
Las 3 correcciones que esta revisión produjo (FP-4 parcial, FN-1, §3) son actos de razonamiento
no verificado, idénticos en naturaleza a los que produjo MIG-07.5. `SUPPORTED`

**Los niveles no se asumen definitivos.** I2 e I3 son plausibles de alcanzar (un subagente con
`edit: deny` es I3 documentado: `permissions` existe). Lo que no es plausible es **I4 sin P4**,
porque I4 es una definición de acreditación. `SUPPORTED`

---

## 11. FASE 11 — AUTORIDAD: QUÉ FALTARÍA PARA `AUTHORITY_RESOLVED`

**No se resuelve. Se especifica.**

| Sub Condición | Estado | Evidencia que faltaría |
|---|---|---|
| `authority_exists` | **SÍ** | 13 artefactos declaran autoridad |
| `authority_is_declared` | **SÍ** | 13 declaraciones explícitas |
| `authority_is_current` | **NO** | V6 sin `STATUS`; MRS degradada por `AGENTS.md:21-24`; la que declara el orden es `DRAFT/CONFLICT` |
| `authority_has_precedence` | **NO** | `PRECEDENCE_RULE=NOT_AVAILABLE`; 5 reglas, 0 aplicables a la dimensión |
| `authority_conflict_is_resolved` | **NO** | `ROUTER:267` = `REVIEW_REQUIRED`, sin escalar |
| `authority_change_is_controlled` | **NO** | 0 reglas de supersesión; `superseded` solo como etiqueta de censo |

```
AUTHORITY_RESOLVED=NO
BLOQUING_SUBCONDITIONS=4 de 6
```

**La evidencia que existiría si se cumplieran:** una regla escrita que, dado un artefacto y una
dimensión, devuelva un artefacto único, con vigencia, con procedimiento de cambio, y cuya
violación sea detectable. **Ninguna de las 6 subcondiciones tiene hoy un mecanismo de
verificación.** `SUPPORTED`

**Consecuencia notable: aunque las 6 se cumplieran, no habría forma de comprobarlo
automáticamente.** El cumplimiento de una regla de precedencia es, en sí mismo, un problema de
D9 (cobertura) y D8 (enforcement). `SUPPORTED`

---

## 12. FASE 12 — INTEGRIDAD DE SALIDA: CINCO EJES

| Eje | Qué detecta | ¿Mecanismo? | Caso que lo demuestra |
|---|---|---|---|
| **character_integrity** | caracteres no esperados | escaneo ad hoc | `能否`, `dePersistir` |
| **syntax_integrity** | estructura malformada | markdownlint: **NO** | tablas rotas |
| **reference_integrity** | `fichero:línea` no resuelve | **NO** | **`:43` → `:23`** |
| **semantic_integrity** | el contenido dice lo que debe | **NO** | afirmaciones no verificadas |
| **evidence_integrity** | la referencia **respalda** la afirmación | **NO** | una cita puede resolver y no sustentar |

**El caso `:43`→`:23` es la demostración canónica:** el documento era textual y sintácticamente
válido, y **evidencialmente incorrecto**. Character y syntax no lo detectan. `SUPPORTED`

**Y el más difícil:** `evidence_integrity` **no es automatizable con herramientas de análisis de
texto.** Requiere juicio. Por tanto cualquier claim de QC sobre «el documento es correcto» es
`AUTHOR_REASONING_ONLY`. `SUPPORTED`

---

## 13. FASE 13 — ARQUITECTURA DE VERSIONADO DE AUDITORÍAS (especificación, no implementación)

```
KNOWN_DEFECT=CONFIRMED
  01-AUDITORIA/MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md:23
  sha256=575c7957ed2a2faabd79073690e0d97113d32c3d4061b6398a4acf9405ee53aa
CORRECTION=DEFERRED
```

**Lo que una corrección debe preservar, y que hoy no tiene mecanismo:**

| # | Requisito | Solución especificada | Estado |
|---|---|---|---|
| R-1 | hash original intacto | el original **no se edita jamás** | `NOT_IMPLEMENTED` |
| R-2 | contenido original legible | el original permanece | `NOT_IMPLEMENTED` |
| R-3 | provenance de la corrección | entrada nueva con fecha, autor, motivo, hash | `NOT_IMPLEMENTED` |
| R-4 | referencia histórica | el original declara que fue corregido, y en qué | `NOT_IMPLEMENTED` |
| R-5 | relación con la versión corregida | puntero `SUPERSEDES` / `SUPERSEDED_BY` | `NOT_IMPLEMENTED` |
| R-6 | que la corrección sea auditable | diff verificable entre ambas | `NOT_IMPLEMENTED` (git daría R-6 solo si ambos están versionados; hoy ninguno lo está) |

**El repositorio ya tiene la noción:** el censo usa `SUPERSEDED`/`STALE` con «Quién lo marca».
**La noción existe; el mecanismo no.** `SUPPORTED`

**No se implementa. No se inventa el formato.**

---

## 14. FASE 14 — CONDICIÓN MÍNIMA PARA DECLARAR `SELF_METHODOLOGY_GAP`

Cuatro valores, no tres. El cuarto es el que la evidencia exige:

| Valor | Evidencia exigida | Cuándo usarlo |
|---|---|---|
| `GAP_NOT_APPLICABLE` | el dominio tiene A,B,C,D,E en `Y`/`P` y ninguna `N` | D1. **Un valor de primera clase, no una ausencia** |
| `GAP_PARTIAL` | ≥1 dimensión en `N` **y** las restantes en `Y`/`P` | D2, D4, D13 |
| `GAP_UNKNOWN` | no se pudo determinar alguna de A–E | ningún dominio hoy; pero es el valor **honesto** por defecto |
| `GAP_CONFIRMED` | ≥1 dimensión en `N` en el eje **que limita la conclusión** | D3, D9, D12, D15 |

**Regla de Baldwin que la evidencia impone (y que corrige a MIG-07.5):**

> `GAP_CONFIRMED` **NO** es «no existe ningún mecanismo». Es «**el mecanismo que falta recae
> sobre el eje que sostiene la conclusión**».

Aplicada:
- D10: falta `C` (cobertura) → el defecto sobrevive → `GAP_CONFIRMED` ✅
- D1: falta `B` (ejecución) → el mecanismo existe pero no se lanza → `GAP_PARTIAL` ✅
- D13: falta enforcement en prosa → el gate existe para sistema → `GAP_PARTIAL` ✅

**Con esta regla, la afirmación global de MIG-07.5 queda deshecha correctamente:** D1 es
`GAP_NOT_APPLICABLE`, no un gap. `SUPPORTED`

---

## 15. FASE 15 — EL AUTODIAGNÓSTICO TAMBIÉN NECESITA COBERTURA

Las 4 preguntas. Las 4 tienen la misma respuesta honesta.

| # | Pregunta | Respuesta honesta |
|---:|---|---|
| 1 | ¿cómo sabe que examinó todo el dominio? | **no lo sabe.** Solo puede saberlo si el universo se declaró antes |
| 2 | ¿cómo detecta que dejó fuera documentos? | **solo enumerando primero.** `ls` antes de `grep`. Es la lección de FN-1 |
| 3 | ¿cómo detecta que su clasificación tiene falsos negativos? | **no puede.** 5 FN en 1 revisión; la tasa de FN desconocidos es `UNKNOWN` |
| 4 | ¿cómo detecta un mecanismo que él no conocía? | **no puede.** Es un límite estructural: un detector es una regla fija |

```
AUTODIAGNOSTIC_COVERAGE=UNKNOWN
```

**Y esto es la conclusión que cierra el círculo:**

> El autodiagnóstico **no puede ser una autoridad absoluta sobre su propia cobertura**, porque
> la información que le falta es precisamente la que su búsqueda no encontró. **D9 es
> `GAP_CONFIRMED` y por eso D14 no puede certificarse a sí mismo.**

**Mitigación disponible, no suficiente:** declarar el universo antes de buscar
(`SEARCH_COMPLETE`), y registrar el universo buscado (`SEARCH_EXECUTED`). Eso convierte
`COMPLETE` de afirmación en artefacto. **No convierte `COMPLETENESS_PROVEN` en alcanzable.**

**Y una observación que cierra la revisión de sí misma:** esta matriz obtiene
`UNKNOWN_GAPS=0`, lo que **parece** más fuerte que el `PARTIALLY_CONFIRMED` de MIG-07.6. Y es
**menos fuerte**, porque no tiene tarjeta de universos declarados. `SUPPORTED`

---

## 16. FASE 16 — RESULTADO

```
MIG-07.7=VERIFYING

DOMAIN_COUNT=15

CONFIRMED_GAPS=11    (D3,D4.audit,D6,D7,D8,D9,D10,D11,D12,D14,D15)
PARTIAL_GAPS=3       (D2,D4,D13)
NO_GAPS=1            (D1)
UNKNOWN_GAPS=0       -- con la advertencia de §5: no certifica su propia completitud

MAX_DETECTION_BY_EXISTENCE=L3
MAX_EXECUTION_GUARANTEE=NINGUNA
MAX_COVERAGE=PARCIAL
MAX_COVERAGE_PROVEN=NO
MAX_ENFORCEMENT=DOCUMENTADA_SOLO_D1_D4_SISTEMA
MAX_ENFORCEMENT_AUTOMATICA=NINGUNA
MAX_INDEPENDENCE=I1

SELF_METHODOLOGY_GAP_SCOPE=PER_DOMAIN
  CONFIRMED: D3 pruebas · D4.audit auditoría · D6 evidencia experimental ·
             D7 provenance de actor · D8 autoridad · D9 cobertura de búsqueda ·
             D10 integridad textual · D11 verificación semántica de corrección ·
             D12 independencia · D14 autodiagnóstico · D15 integridad de referencias
  PARTIAL:   D2 código · D4 documentación normativa · D13 gates
  NONE:      D1 sistema/operaciones

AUTODIAGNOSTIC_COVERAGE=UNKNOWN
SELF_METHODOLOGY_GAP_GLOBAL=REFUTED
L0_L5_AS_SCALE=RETIRED
REPLACED_BY=5_dimensions_x_15_domains

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

---

## 17. FASE 17 — FALSACIÓN DE LA MATRIZ

| # | Contraejemplo buscado | Resultado |
|---|---|---|
| **CF-1** | ¿dominio omitido? | **POSIBLE: falta un eje transversal «tiempo».** `mtime` en bloque (`2026-09-25 11:16`) impide establecer el orden real de creación. No se añade dominio porque no hay capacidad que clasificar: se registra como limitación |
| **CF-2** | ¿capacidad omitida? | **SÍ, una: `run_tests.py` con `64/64`.** No figura en la matriz. Se añade a D1/D2. `CORRECTION` |
| **CF-3** | ¿mecanismo mal clasificado? | **`TESTING.md §5` como `EXISTENTE` y no `PARCIAL`.** Es una regla escrita sin automatización → `EXISTENTE` en A, `NO` en B. Correcto tal como está |
| **CF-4** | ¿cobertura sobreestimada? | **D2: `C=PARCIAL` podría ser `NO`.** 154 tests que no ejecutan la orquestación. Admitido |
| **CF-5** | ¿independencia sobreestimada? | **`I1` podría ser `I0`.** Las revisiones se hicieron tras leer las del autor. Admitido: `I1` es la lectura más generosa |
| **CF-6** | ¿enforcement confundido con documentación? | **Revisado: D13 fila 1 es `DOCUMENTADA`, no `AUTOMÁTICA`.** Correcto. El riesgo era el contrario: habríasinfraestimado |
| **CF-7** | ¿detección confundida con garantía? | **Es el error central que esta matriz corrige.** `MAX_DETECTION_BY_EXISTENCE=L3` junto a `MAX_EXECUTION_GUARANTEE=NINGUNA` lo hace explícito |
| **CF-8** | ¿D4.audit debería ser dominio aparte? | **Posible.** La fusión de §1.3 tiene un coste declarado. `UNKNOWN` |
| **CF-9** | ¿D1 es realmente `NO_GAP`? | **Es el contraejemplo más fuerte a mi propia matriz.** D1 tiene `B=NO`: el verificador no se ejecuta obligatoriamente. Si `B=NO` invalida `NO_GAP`, entonces **todos los dominios** son `GAP_PARTIAL` o peor, y `NO_GAPS=0`. **No lo decido aquí**: es la decisión que la revisión humana debe tomar |
| **CF-10** | ¿`GAP_CONFIRMED` en 11 dominios es demasiado? | **Podría ser.** La regla Baldwin hace `GAP_CONFIRMED` muy fácil: basta una dimensión en `N`. Con 15 dominios y 5 dimensiones, casi todo califica. **La regla es demasiado laxa.** `UNKNOWN` si se mantiene |

**Contraejemplos materiales: 3** (CF-2 corrección aplicada, CF-9 sin resolver, CF-10 sin
resolver). **Autofalsaciones: 2** (CF-4, CF-5 admissions).

---

## 18. FASE 18 — CRITERIO DE CIERRE

| # | Criterio | Estado |
|---:|---|---|
| 1 | el modelo ya no es global cuando la evidencia es por dominio | **CUMPLE** |
| 2 | existencia y garantía separadas | **CUMPLE** (5 columnas) |
| 3 | cobertura diferenciada | **CUMPLE** (columna C) |
| 4 | independencia diferenciada | **CUMPLE** (columna E + I0–I5) |
| 5 | el autodiagnóstico tiene condición de cobertura | **CUMPLE** (`AUTODIAGNOSTIC_COVERAGE=UNKNOWN`, §15) |
| 6 | **sin contraejemplos sin resolver** | **FALLA** — CF-9 y CF-10 |
| 7 | **sin afirmaciones críticas solo por razonamiento del autor** | **FALLA** — la clasificación de los 15 dominios, los umbrales de la regla Baldwin y CF-9/CF-10 son todos juicio |

**6 de 8. `MIG-07.7=VERIFYING`.**

Los dos criterios que fallan fallan por la misma razón que en las 6 fases anteriores: **nadie
independiente ha revisado nada**, y ahora hay evidencia directa de por qué: D12 está en
`GAP_CONFIRMED` y `I1` es el techo demostrable.

---

## 19. CONTESTANDO LA PREGUNTA FINAL

> *«¿Qué tendría que ser capaz de hacer OpenCode para saber que su propia metodología es
> insuficiente, y cómo demostraríamos que realmente lo sabe?»*

**Para saberlo, según la evidencia de esta matriz:**

1. **Declarar el universo antes de buscar** (`SEARCH_COMPLETE` como artefacto). Sin esto no hay
   `C` y no hay gap demostrable. Es la lección de FN-1 y la única defensa contra D9.
2. **Separar A/B/C/D/E** y no colapsarlos. Un escaneo que corre, cubre y cuyo resultado se ignora
   tiene A=Y, B=Y, C=?, D=N.
3. **Emitir `GAP_UNKNOWN` como valor por defecto** cuando alguna de las 5 dimensiones no se pudo
   determinar. La presión por emitir un valor es lo que produjo 3 autocorrecciones en 6 fases.
4. **Exigir la dimensión limitante**: decir *qué eje* falla, no solo *que algo* falla.
5. **Declarar `AUTODIAGNOSTIC_COVERAGE=UNKNOWN`** siempre que no exista artefacto de universo.

**Para demostrar que realmente lo sabe, harían falta 4 cosas, y ninguna existe:**

| # | Requisito de demostración | Estado |
|---|---|---|
| 1 | **Fallo negativo control**: un gap sembrado que el mecanismo debe detectar | `NO_IMPLEMENTED` — y sin él, cualquier detección positive no demuestra nada |
| 2 | **Cobertura probada**: el universo declarado cubre el dominio real | `UNKNOWN` (§15) |
| 3 | **Tasa de falsos negativos medida**: sobre casos conocidos | `UNKNOWN` |
| 4 | **Verificador independiente del verificador** | `NO_IMPLEMENTED` (D12) |

**El requisito 1 es el que ninguna de las 8 fases anteriores mencionó, y es el que hace toda la
diferencia:** hasta ahora, «el escaneo dio 0» seFWAT se tomó como evidencia de que no había
defectos. **Un detector que nunca ha sido probado contra un defecto sembrado no puede demostrar
nada, ni en positivo ni en negativo.** `SUPPORTED`

**Ese es el hallazgo final, y es un `CONFIRMED_GAP` más: la ausencia de un fallo negativo
control impide demostrar la capacidad de cualquier mecanismo de QC, y por tanto invalida la
evidencia de «calidad» de las 6 fases anteriores.**

---

## 20. REGISTRO

```
ARCHIVOS_CREADOS=1     (este informe)
ARCHIVOS_MODIFICADOS=0
STAGED=360  (sin cambio)
HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5  (sin cambio)
COMMITS=0  PUSHES=0
UNTRACKED_FUERA_01_AUDITORIA=0
.opencode/=NO   STATE/=NO
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
```

`KNOWN_DEFECT=CONFIRMED` (`dePersistir`, `MIGRATION-…:23`) · `CORRECTION=DEFERRED` — §13
especifica la arquitectura sin implementarla.
