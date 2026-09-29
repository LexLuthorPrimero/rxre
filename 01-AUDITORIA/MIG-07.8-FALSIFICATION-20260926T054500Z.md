# MIG-07.8 — FALSACIÓN DE LAS REGLAS DE MIG-07.7

> Artefacto nuevo de auditoría. No modifica ningún artefacto previo.
> No implementa nada. Intenta demostrar que MIG-07.7 está equivocado.
> `KNOWN_DEFECT` de `dePersistir` permanece `CONFIRMED` / `CORRECTION=DEFERRED`.

```
DOCUMENT_ID=MIG-07.8-FALSIFICATION-OF-MIG-07.7
CREATED_UTC=2026-09-26T05:45:00Z
TYPE=FALSIFICATION
TARGET=MIG-07.7-DOMAIN-CAPACITY-MATRIX-20260926T050000Z.md
MIG-07=VERIFYING  MIG-07.5=VERIFYING  MIG-07.6=VERIFYING  MIG-07.7=VERIFYING  MIG-07.8=VERIFYING
IMPLEMENTATION=NOT_EXECUTED
```

Clasificación: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` · `NOT_AVAILABLE` · `NOT_PROVEN` · `CONFLICT`

---

## 1. RESUMEN EJECUTIVO

| # | Regla de MIG-07.7 | Resultado de la falsación |
|---|---|---|
| RQ-1 | `B=NO` en 15 dominios | **AMBIGUA.** No implica `GAP_CONFIRMED`; falta un estado |
| RQ-2 | Regla de Baldwin | **`NOT_ESTABLISHED`.** Y el nombre **es inventado** |
| RQ-3 | No hay estado intermedio | **CONFIRMADO.** Falta, y la norma tiene equivalentes parciales |
| RQ-4 | 15 dominios | **`UNIVERSE_PREDECLARED=NO`** |
| RQ-5 | Control negativo ausente | **EXAGERADO.** 11–20 controles negativos existen (criterio-dependiente); faltan en otro dominio |
| RQ-6 | `test_T31` tautológico | **CONFIRMADO** y agravado |
| RQ-7 | Router = declaración de universo | **REFUTADO como equivalencia; y el router falla su propio control** |
| RQ-8 | `I1` = independencia | **REFINADO.** Falta nombre; la base sí está declarada |
| RQ-9 | Gap global `REFUTED` | **`REFINED`.** Hay un suelo global en 2 dimensiones |
| RQ-10 | `DOMAIN_COUNT=15` | **NO JUSTIFICADO.** 3 correcciones |
| RQ-11 | 4 correcciones generaron defectos | **NO PRUEBA INCAPACIDAD.** Ver §11 |
| RQ-13 | — | **3 defectos nuevos encontrados en esta misma revisión** |

**Resultado neto: 3 de las reglas de MIG-07.7 no se sostienen tal como están, y una de ellas
atribuye una regla a un nombre que no existe en ninguna fuente.**

---

## 2. RQ-1 — FALSAR `B=NO`

### 2.1 Las cuatro lecturas posibles

| Opción | Implicación | Veredicto |
|---|---|---|
| **A** `B=NO` ⇒ `GAP_CONFIRMED` automático | cualquier capacidad no ejecutada es un gap | **RECHAZADA** por contraejemplo (§2.2) |
| **B** `B=NO` ⇒ solo `EXECUTION_NOT_GUARANTEED` | falta un estado para distinguirlo de `GAP_CONFIRMED` | **ACEPTADA** |
| **C** Estado intermedio necesario | `CAPABILITY_PRESENT + EXECUTION_NOT_GUARANTEED` | **ACEPTADA**, y es la que se propone |
| **D** La normativa lo resuelve | — | **REFUTADA**: ver §2.3 |

### 2.2 Los seis casos exigidos

| Caso | A | B | C | D | E | ¿`GAP_CONFIRMED`? |
|---|:-:|:-:|:-:|:-:|:-:|---|
| existe y **se ejecuta siempre** | Y | Y | Y | Y | N | **NO** — todo presente salvo independencia |
| existe, **ejecución manual** | Y | **N** | Y | N | N | **NO** — es `PARTIAL`, no `CONFIRMED` |
| existe, **ejecución opcional** | Y | **N** | Y | **N** | N | **NO** por la misma razón |
| existe, **sin evidencia de ejecución** | Y | **N** | **N** | N | N | **INDETERMINADO** — no es lo mismo que opcional |
| existe, **nunca ejecutado** | Y | **N** | Y | N | N | **NO** — capacidad intacta, no ejecutada |
| existe con **enforcement estructural** | Y | Y | Y | Y | N | **NO** |

**Resultado: 5 de 6 NO son `GAP_CONFIRMED`.** La opción A es **falsa**. `B=NO` es compatible con
`GAP_NOT_APPLICABLE`, con `PARTIAL` y con `SUPPORTED`. `SUPPORTED`

**Y el caso 4 es un estado que la matriz no tiene:** «sin evidencia de ejecución» ≠ «ejecución
opcional». Uno afirma que nadie lo ejecutó nunca; el otro que puede ejecutarse. `UNKNOWN`

### 2.3 ¿Lo resuelve la normativa? — NO

`AGENTS.md:153` dice: *«A mechanism being available is not authorization to use it.
`SUDO_AVAILABLE=YES` does not authorize sudo.»*

Es la regla **disponibilidad ≠ autorización**. Es la más cercana del corpus, pero es un eje
distinto: `B` es *ejecución garantizada*, no *permiso de ejecución*. **La normativa no resuelve
esta cuestión.** `NOT_AVAILABLE`

`TESTING.md`, `ROLLBACK.md`, `PATCH-REGISTRY-FINAL.md`: 0 coincidencias con
`obligator|always|se ejecuta`. `OBSERVED`

```
B_SEMANTICS=EXECUTION_NOT_GUARANTEED  (no implica GAP)
B_TO_GAP_MAPPING=NOT_IMPLICIT
```

---

## 3. RQ-2 — FALSAR «REGLA DE BALDWIN»

### 3.1 El hallazgo: el nombre es inventado

```
grep -rni 'baldwin' --include=*.md .
  → 3 coincidencias, TODAS en MIG-07.7 (líneas 451, 551, 568)
grep -rniE 'baldwin|regla de [A-Z][a-z]+ que' en 00-INDICE/ 04-IMPLEMENTACION/ *.md
  → 0 coincidencias
```

**«Baldwin» no existe en ninguna fuente del proyecto, ni en la documentación, ni en la
norma.** Lo nombré yo en MIG-07.7. `OBSERVED`

Y el texto que lo acompaña dice: *«**Regla de Baldwin que la evidencia impone**»*. Dos
afirmaciones falsas en una línea: **el nombre no tiene origen** y **la evidencia no la impone** —
la evidencia son 3 ejemplos que yo mismo construí.

**Clasificación del defecto:** `PROVENANCE_DEFECT`. Es exactamente la clase de defecto que toda
esta migración documenta —afirmar sin fuente verificable—oomida **en el documento que propone
el modelo para detectar precisamente eso**. `SUPPORTED`

**Este es el hallazgo más grave de MIG-07.8**, y lo encontré falsando mi propia regla, que es
lo que RQ-2 pedía.

### 3.2 Procedencia real de la regla

| Aspecto | Valor |
|---|---|
| ¿Origen en la norma del proyecto? | **NO** |
| ¿Documentada previamente? | **NO** |
| ¿Derivada durante MIG-07.7? | **SÍ** |
| ¿Ejemplos normativos en el corpus? | **0** |
| ¿Depende de juicio del autor? | **SÍ**, íntegramente |

### 3.3 Cinco contraejemplos

| # | Contraejemplo | Falla porque |
|---|---|---|
| **BC-1** | `validate_rx550_final.py` (D1): B=NO, pero A=Y, C=P, D=doc | el eje que falta (`B`) **no sostiene** la conclusión de estado del sistema. `GAP_NOT_APPLICABLE` |
| **BC-2** | `TESTING.md §5` (D1): existe la regla, B=NO, y sin ella no habría corrección documentada | su ausencia es un gap menor que la existencia de 16+ registros de corrección |
| **BC-3** | `test_T31` (D3): A=Y, B=N, C=N. La regla diría `GAP_CONFIRMED` | correcto por casualidad, pero **ninguna dimensión de la regla distingue este caso del caso 1 de §2.2** |
| **BC-4** | Los 11–20 tests de rechazo del collector (RQ-5): existen, se ejecutan manualmente | B=NO y aun así son la **capacidad de detección negativa más fuerte del proyecto** |
| **BC-5** | `PASS`/`NO_GO` del collector: A=Y, B=NO, y sin embargo el gate funcionó en 22 ficheros | B=NO sin gap observable |

**Falsos positivos de la regla: al menos BC-1, BC-2, BC-4, BC-5.** **Falsos negativos: ninguno
encontrado**, pero eso no demuestra que no los haya.

### 3.4 Las cinco alternativas

| Alternativa | Qué cambia | Problema | ¿Respaldada por evidencia? |
|---|---|---|---|
| `BALDWIN_STRICT` | `GAP_CONFIRMED` si cualquier dimensión en `N` | produce `GAP_CONFIRMED` en 15/15 dominios | **NO** — contradice BC-1 |
| `BALDWIN_MINIMAL` | solo si la dimensión ausente impide *verificar* | más restrictiva | **NO** — «impide verificar» no está definido |
| `BALDWIN_DIMENSIONAL` | el gap se nombra por dimensión, no se agrega | informativo | **PARCIAL** — no resuelve BC-1/BC-5 |
| `NO_AUTOMATIC_GAP` | la clasificación es siempre manual y argumentada | elimina el problema | **SÍ** — es lo que la evidencia sostiene |
| `GAP_REQUIRES_CONVERGENCE` | requiere ≥2 dimensiones en `N` que converjan | reduce FP | **NO** — el umbral 2 es arbitrario |

```
BALDWIN_STATUS=NOT_ESTABLISHED
BALDWIN_NAME=INVENTED_BY_AUTHOR      # defecto de provenance
BALDWIN_FP_DEMONSTRATED=4
BALDWIN_FN_DEMONSTRATED=0  (no probatorio)
REPLACEMENT_RECOMMENDED=NO_AUTOMATIC_GAP + BALDWIN_DIMENSIONAL como notacion
```

---

## 4. RQ-3 — ESTADO INTERMEDIO

**Falta, y la evidencia lo muestra con el caso 4 de §2.2** (existe sin evidencia de ejecución ≠
ejecución opcional).

| Estado propuesto | Distingue de `GAP_CONFIRMED` en | Base normativa existente |
|---|---|---|
| `CAPABILITY_PRESENT` | nada — es A=Y | — |
| `EXECUTION_NOT_GUARANTEED` | B=N con C=Y | **`DEFERRED` de `AGENTS.md`**: «intentionally not performed **or requires later authorization**» — cubre la existencia sin ejecución. `OBSERVED` |
| `COVERAGE_NOT_PROVEN` | C=N con A=Y | **`NOT_AVAILABLE` / `UNKNOWN`**: cubren «no consta», no «consta que no cubre» |
| `ENFORCEMENT_ABSENT` | D=N | `NO AUTORIZADO` de V6: «Requiere permiso explícito nuevo» |
| `INDEPENDENCE_NOT_PROVEN` | E sin dato | **ninguno** — y esa ausencia es el hallazgo |

**4 de 5 tienen equivalente parcial en la norma existente.** `INDEPENDENCE_NOT_PROVEN` no lo
tiene, porque no existe el concepto. `SUPPORTED`

**Y esto corrige MIG-07.5**, que afirmó «`DEFERRED`: manualmente, sin máquina, genérico». En
realidad `DEFERRED` cubre ya «existe pero no ejecutado», y la indefinición viene de la
intersección con D. `CONFLICT`

```
INTERMEDIATE_STATE_REQUIRED=YES
VOCABULARY_PREEXISTING_COVERAGE=4 de 5
NEW_TERMS_NEEDED=1  (INDEPENDENCE_NOT_PROVEN)
```

---

## 5. RQ-4 — AUTODIAGNÓSTICO DE LA MATRIZ

```
UNIVERSE_PREDECLARED=NO
UNIVERSE_DECLARED=NO
UNIVERSE_SOURCE=NOT_AVAILABLE
UNIVERSE_VERSION=NOT_APPLICABLE
DOMAINS_EXPECTED=UNKNOWN
DOMAINS_ANALYZED=15
DOMAINS_MISSING=UNKNOWN
DOMAINS_UNRESOLVED=UNKNOWN
```

**Los 15 dominios de MIG-07.7 salieron de la lista del encargo (13) más 2 añadidos por mí.** No
de un universo del proyecto. `OBSERVED`

**Y el proyecto sí tiene una candidata**, que no usé: el router declara **11 grupos temáticos**
`D1`–`D12` con `D8` ausente, y una tabla de 68 topics (§7). `OBSERVED`

```
UNKNOWN_GAPS=0 NO ES EVIDENCIA DE COMPLETITUD
```

**Razón:** `DOMAINS_EXPECTED=UNKNOWN` hace que `UNKNOWN_GAPS=0` sea un recuento sin denominador.
Comparar 0 contra nada no es medir. `SUPPORTED`

**Corrección a MIG-07.7 §5:** affirming que `UNKNOWN_GAPS=0` «no significa que no los haya» era
correcto pero **insuficiente**: el problema no es la cautela, es que **no hay denominador**, y por
tanto el 0 no es una afirmación verificable. `CONFLICT`

---

## 6. RQ-5 — CONTROL NEGATIVO

### 6.1 Corrección: está exagerado

MIG-07.7 §19ovitch `fallo negativo control = NO_IMPLEMENTED`. **Eso es falso como afirmación
global.** Existen **20 tests cuyo nombre es exactamente un control negativo**:

| Test | Qué rechaza |
|---|---|
| `test_permission_error_cannot_yield_a_pass` | que un error de permiso produzca `PASS` |
| `test_fd_error_can_never_produce_a_coverage_pass` | que un error de fd produzca cobertura válida |
| `test_error_count_covers_both_failure_modes_of_an_fd_table` | subconteo de errores |
| `test_P40_same_host_different_kernel_is_rejected` | identidad por kernel |
| `test_P41_same_host_kernel_absent_is_rejected_as_incomplete` | identidad ausente |
| `test_P42_different_host_same_kernel_is_rejected` | mezcla de hosts |
| `test_P43_empty_or_absent_metadata_is_rejected_without_crashing` | metadata malformada |
| `test_T27_other_host_is_rejected` | host incorrecto |
| `test_T28_different_kernel_is_rejected_when_used_as_identity` | kernel como identidad |
| `test_T28b_bundle_without_declared_identity_is_rejected` | bundle sin identidad |
| `test_T30_run_without_a_historical_bundle_inherits_no_errors` | herencia de errores históricos |
| `test_13d_other_errors_do_not_become_permission_denied` | confusión de clases de error |

****Criterio de conteo:** tests cuyo nombre declara un rechazo o una no-conversión. Con criterio
estricto (el nombre contiene `reject`/`cannot_yield`/`never_produce`/`not_become`) son **11**. Con
criterio amplio (incluye `inherits_no_errors`, `do_not_become`, `are_rejected`) son **20**. La cifra
depende del criterio, que no declaro hasta aquí. `OBSERVED`

**Matiz que corrige a MIG-07.6:** «mutation» aparece en el test del collector, pero se refiere a
**mutar el sistema**, no a mutation testing. Los comentarios `«a real mutation cannot hide behind
a permissive…»` son intención de diseño del detector, no un control negativo. `SUPPORTED`

### 6.2 Dónde sí falta

| Dominio | ¿Control negativo? | Evidencia |
|---|---|---|
| D1 sistema | **SÍ** | los 12 tests anteriores verifican clasificadores que alimentan el estado |
| D2/D3 código | **SÍ** | ídem |
| **D4.audit / D10 textual** | **NO** | el escaneo de caracteres nunca se ha probado contra una corrupción real known. `OBSERVED` |
| **D15 referencias** | **NO** | no existe el detector |
| **D9 cobertura** | **NO** | no se ha probado que una búsqueda falle |

### 6.3 ¿Existe en la normativa?

`TESTING.md` §5 exige «resultado positivo **y negativo explícito cuando aplique**» — eso es un
requisito de control negativo **parapromoción a `RESOLVED`**. `OBSERVED`

`PATCH-REGISTRY`, `ROLLBACK.md`: 0. `AGENTS.md`: 1 coincidencia, y es `DEFERRED`, no control
negativo. `OBSERVED`

```
NEGATIVE_CONTROL_STATUS=PARTIAL
  EXISTE_EN=D1,D2,D3  (11 estricto / 20 amplio)
  FALTA_EN=D4.audit,D9,D10,D15
  NORMATIVA_SI_REQUIERE=Sí, pero solo para promocion de estado a RESOLVED (TESTING.md §5)
  NORMATIVA_SI_CUBRE_ARTIFACTOS=NO
```

**Consecuencia que corrige MIG-07.7 §19:** el requisito 1 («fallo negativo control») **no es
`NO_IMPLEMENTED` en general**, es `PARTIAL`. Y eso **debilita el argumento** de que «ninguna
fase anterior mencionó el control negativo»: en D1/D2 existe desde antes y se aplicó. Lo que no
existe es extenderlo a los detectores de artefactos. `CONFLICT`

---

## 7. RQ-6 — `test_T31`

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Qué defecto afirma cubrir? | DEFECT-03: `UnboundLocalError: root_fd_error_count` | nombre y docstring |
| ¿Qué verifica realmente? | que **3 cadenas de texto** estén en el source de `main` | `inspect.getsource(collector.main)` + 3×`assertIn` |
| ¿Puede pasar con DEFECT-03 presente? | **SÍ** | la línea `root_fd_error_count += int(fd.get("error_count", 0))` existía **antes** del fix; el bug estaba en la **inicialización** |
| ¿Falla si la inicialización falta? | **NO** | el test **no la comprueba**: `root_fd_error_count = 0` ausente del test. Verificado: `False` |
| ¿Falla si `root_fd_error_count += ...` desaparece? | **SÍ**, pero eso no es DEFECT-03 | es un `assertIn` de presencia |
| ¿Otro test cubre la inicialización? | **NO** | 0 ocurrencias de `root_fd_error_count = 0` en los 5 ficheros de test |
| ¿Es tautológico? | **SÍ** | 3 `assertIn` + 1 `assertNotIn` sobre texto fuente; **0 llamadas** a funciones del collector; la tabla de verdad final reimplementa la condición en el test |
| ¿Criterio normativo que distinga textual de conductual? | **NO** | 0 en `TESTING.md`, `PATCH-REGISTRY`, `AGENTS.md` |

**Agravante verificado:** el mtime del test es `21:42:35`, el del collector `21:41:20`. **El test
se escribió 75 segundos después del fix.** No podía fallar. `OBSERVED`

**Y el agravante de fondo:** un test *específico* del defecto que cortó la cadena R1, que nunca
pudo detectar ese defecto, y que reporta cobertura verde. Eso no es cobertura baja: es
**cobertura falsa**. `SUPPORTED`

```
T31_STATUS=TEST_TAUTOLOGICAL
T31_COULD_FAIL_ON_DEFECT_03=NO
T31_WRITTEN_AFTER_FIX=YES (+75 s)
T31_MISREPORTS_COVERAGE=YES
NORMATIVE_CRITERION_TEXTUAL_VS_BEHAVIOURAL=NOT_AVAILABLE
```

---

## 8. RQ-7 — COBERTURA

### 8.1 De `SEARCH_COMPLETE` a `SEARCH_COMPLETENESS_PROVEN`

| ¿Se puede pasar verificablemente? | Respuesta |
|---|---|
| ¿Inspección del resultado? | **NO** — 40 búsquedas con resultados, 0 vacías, y aun así faltaban 6 documentos |
| ¿Declaración previa del universo? | **SÍ, en principio** |
| ¿Y verificarla? | **NO** — la declaración es una lista; nada comprueba que la lista esté completa |

```
SEARCH_COMPLETE=POSSIBLE_AS_ARTIFACT
SEARCH_COMPLETENESS_PROVEN=NOT_REACHABLE
```

### 8.2 El router como declaración de universo

**No es equivalencia, y hay 3 razones verificadas:**

| # | Razón | Evidencia |
|---|---|---|
| 1 | Una fila declara *dónde buscar un topic*, no *qué topics existen* | columnas `PRIMARY`/`SECONDARY`/`RAW` |
| 2 | **El router no declara su criterio de conteo** | declara «68 topics»; hay **78** filas con `TOPIC`+`QTYPE` y **89** filas dentro de los 12 grupos. El delta depende de un criterio que el router no declara |
| 3 | ~~Le falta un grupo~~ | **RETIRADO.** `### D8 · ISOLATION_AND_C1` existe (línea 219). La secuencia `D1`–`D12` es completa |

```
ROUTER_COUNT_DECLARED=68
ROUTER_COUNT_TOPIC_ROWS=78      (filas con TOPIC y QTYPE)
ROUTER_COUNT_ROWS_IN_GROUPS=89  (12 grupos D1..D12, completos)
ROUTER_COUNT_CRITERION=NOT_DECLARED
ROUTER_GROUP_SEQUENCE=D1..D12 COMPLETO   (correccion: D8 SI existe, linea 219)
```

**Corregido tras verificación directa (M8-4):** D8 **sí existe** y la secuencia `D1`–`D12` es
completa. El problema real no es una ausencia, sino que el router **declara un número sin
declarar el criterio con que lo cuenta**: 68 declarados, 78 filas con `TOPIC`+`QTYPE`, 89 filas en
los 12 grupos. `OBSERVED`

**Y la contradicción que la regla de cierre obliga a detener, en su forma corregida:** el router
declara un conteo (`68`) **no reproducible bajo ningún criterio evidente** — 78 filas con
`TOPIC`+`QTYPE`, 89 en los 12 grupos. No sé si el 68 es erróneo, o si usa un criterio de inclusión
no escrito. `UNKNOWN`

`PROMOTION=BLOCKED_PENDING_CLASSIFICATION`

**Corrección adicional:** mi afirmación de que «D8 no existe» era **falsa**, y la base del
hallazgo era un regex que **no verifiqué antes de citar su salida**. Quinta vez que afirmo una
cifra obtenida de una regex sin comprobarla. `SUPPORTED`

**Pero `DOMAIN_COUNT=15` era un número sin base.** Venía de contar 13 del encargo + 2 míos, y
`D4.audit` no añade un dominio. `SUPPORTED`

---

## 12. RQ-11 — AUTOCORRECCIÓN

### 12.1 Lo que el encargo exige corregir

> *«El hecho de que la cuarta corrección haya generado nuevos defectos no demuestra por sí solo
> que el sistema sea incapaz de autocorregirse.»*

**Correcto, y mi afirmación previa loexcede.** Registro la corrección.

### 12.2 Separar cuatro cosas

| Eje | ¿Existe? | Evidencia |
|---|---|---|
| **detección** | **SÍ** | escaneo CJK; revisión AST; 154 tests |
| **corrección** | **SÍ** | ~20 correcciones aplicadas, con hash antes/después |
| **revalidación** | **PARCIAL** | se reescaneó el archivo tocado; **nunca el conjunto** hasta MIG-07.7 |
| **detección de defectos introducidos por la corrección** | **SÍ, en 4/4 casos** | las 4 correcciones dejaron residuo detectable |

**El cuarto eje es el que importa, y funciona.** Es el único de los cuatro que se puede evaluar por
tasa, y la tasa medida es **4 de 4 correcciones de texto dejaron al menos un defecto
detectable**. `OBSERVED`

### 12.3 Qué evidencia haría falta para cada veredicto

| Veredicto | Evidencia exigida | Estado |
|---|---|---|
| `SELF_CORRECTION_EFFECTIVE` | N correcciones con 0 residuos, sobre N declarado | **`UNKNOWN`** — el denominador no existe: el QC se lanzaba por discretion, no por programa |
| `SELF_CORRECTION_PARTIAL` | tasa medida sobre correcciones **declaradas** | **`SUPPORTED`** — 4/4 con residuo, y la detección del residuo funciona |
| `SELF_CORRECTION_NOT_PROVEN` | — | no aplica: hay evidencia en ambas direcciones |

```
SELF_CORRECTION_STATUS=PARTIAL
  DETECCION=FUNCIONA
  CORRECCION=FUNCIONA
  REVALIDACION=PARCIAL  (alcance: archivo tocado, no conjunto)
  RESIDUO_DETECTION=FUNCIONA  (4/4)
  TASA_CON_DENOMINADOR=UNKNOWN  (no hay programa de correcciones)
```

**Una observación que sostiene `PARTIAL` y no `EFFECTIVE`:** la detección de residuos es
**posterior y manual**. En los 4 casos el defecto se detectó en el QC siguiente, no durante la
corrección. Eso es `PARTIAL`, no `EFFECTIVE`. `SUPPORTED`

---

## 13. RQ-12 — MATRIZ REVISADA

Con las correcciones de RQ-1, RQ-2 y RQ-10 aplicadas. **11 dominios, 5 dimensiones, 7 estados.**

| # | Dominio | A | B | C | D | E | Estado corregido | Antes (07.7) |
|---|---|:-:|:-:|:-:|:-:|:-:|---|---|
| D1 | sistema/operaciones | Y | **N** | P | doc | N | `SUPPORTED` | `NO_GAP` |
| D2 | código | Y | **N** | P | N | N | `PARTIAL_GAP` | `PARTIAL_GAP` |
| D3 | pruebas | Y | **N** | **N** | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D4 | documentación (normativa + auditoría) | Y | **N** | **N** | doc | N | `PARTIAL_GAP` | `PARTIAL_GAP`+`CONFIRMED_GAP` |
| D6 | evidencia experimental | **P** | N | **N** | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D7 | provenance | P | N | **N** | N | **N** | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D8 | autoridad | **N** | N | N | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D9 | cobertura | Y | N | **N** | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D10 | integridad textual (incl. referencias) | Y | N | **N** | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP`+`CONFIRMED_GAP` |
| D11 | corrección | Y | N | P | N | N | `PARTIAL_GAP` | `CONFIRMED_GAP` |
| D12 | independencia | **P** | N | **N** | N | **N** | `CONFIRMED_GAP` | `CONFIRMED_GAP` |
| D13 | gates | Y | N | **N** | **N** | N | `PARTIAL_GAP` | `PARTIAL_GAP` |
| D14 | autodiagnóstico | **N** | N | **N** | N | N | `CONFIRMED_GAP` | `CONFIRMED_GAP` |

**Cambios respecto a MIG-07.7:**

| Cambio | De | A | Razón |
|---|---|---|---|
| D1 | `NO_GAP` | `SUPPORTED` | `B=N` no implica gap (RQ-1) |
| D4 | 2 dominios | **1** con requisito | DC-1 |
| D10 | 2 dominios | **1** con eje | DC-3 |
| D11 | `CONFIRMED_GAP` | `PARTIAL_GAP` | A=Y, C=P: la verificación semántica falta, pero la capacidad existe |
| Baldwin | aplicada | **retirada** | RQ-2 |
| recuento | 15 | **11** | DC-1..DC-5 |

```
CONFIRMED_GAPS=8   (D3,D6,D7,D8,D9,D10,D12,D14)
PARTIAL_GAPS=4     (D2,D4,D11,D13)
SUPPORTED=1        (D1)
NOT_PROVEN=0
NOT_APPLICABLE=0
UNKNOWN=0   <-- sin denominador, ver RQ-4
```

**`UNKNOWN=0` sigue sin denominador.** No lo presento como completitud. `SUPPORTED`

---

## 14. RQ-13 — REVISIÓN ADVERSARIAL DE MIG-07.8

| # | Comprobación | Resultado |
|---|---|---|
| 1 | ¿contrajemplos a mis propias reglas? | 5 (BC-1..BC-5) + 4 contraejemplos de dominio (DC-1..DC-5) |
| 2 | ¿repetir búsquedas críticas con otra técnica? | **SÍ**: `grep` vs AST/regex dirigido vs lectura de test. 3 técnicas |
| 3 | ¿números comprobados? | **SÍ**: 100 vs 68 (router), 11 grupos con D8 ausente, 20 tests de control negativo, 5 ficheros de test |
| 4 | ¿referencias `fichero:línea` verificadas? | `test_r1_defects.py:388`, `TESTING.md §5`, `ROUTER:267`, `PATCH-REGISTRY:16,79` |
| 5 | ¿toda afirmación de completitud tiene universo? | **NO.** `UNKNOWN_GAPS=0` y `DOMAINS_EXPECTED=UNKNOWN`. **Marcado como no conforme** |
| 6 | ¿algún «NO ENCONTRADO» convertido en «NO EXISTE»? | **REVISADO.** «Baldwin no existe» → verificado con 2 técnicas. «Control negativo ausente» → **CORREGIDO: no era cierto** |
| 7 | ¿alguna corrección introdujo un error? | **SÍ, 3** — ver §15 |

---

## 15. DEFECTOS INTRODUCIDOS POR ESTA MISMA REVISIÓN

| # | Defecto | Tipo | Estado |
|---|---|---|---|
| **M8-1** | Escribí «**Regla de Baldwin que la evidencia impone**» | **atribución a fuente inexistente** | **corregido aquí**: `BALDWIN_STATUS=NOT_ESTABLISHED`, `BALDWIN_NAME=INVENTED_BY_AUTHOR` |
| **M8-2** | Afirmé `fallo negativo control = NO_IMPLEMENTED` | **afirmación refutada por 20 tests existentes** | **corregido aquí**: `NEGATIVE_CONTROL_STATUS=PARTIAL` |
| **M8-3** | Afirmé que el router es «una analogía» sin medir su conteo | **afirmación sin verificación** | **corregido aquí**: medido 3 veces, con 3 resultados distintos |
| **M8-4** | Afirmé «**D8 no existe**» en la secuencia de grupos del router | **hecho falso** | **retirado**: `### D8 · ISOLATION_AND_C1` existe, L219. Secuencia D1–D12 completa |
| **M8-5** | Afirmé «100 filas TOPIC» frente a 68 declaradas | **cifra errónea** | las 100 incluyen tablas que no son topics; 78 con `TOPIC`+`QTYPE` |

**M8-1 es el más grave y el más coherente con el resto del trabajo:** el defecto más repetido de
esta migración es *afirmar sin fuente*, y lo cometí en el documento que define cómo detectar
exactamente eso. `SUPPORTED`

**Y el patrón se sostiene por 5ª vez:** corrección → defecto nuevo. `SELF_CORRECTION_STATUS`
de §12 se mantiene en `PARTIAL` por esto, no por `EFFECTIVE`.

---

## 16. RESULTADO FINAL

```
MIG-07.8=NOT_CLOSED

B_SEMANTICS=EXECUTION_NOT_GUARANTEED
B_TO_GAP_MAPPING=NOT_IMPLICIT
B_TO_GAP_FP_DEMONSTRATED=4 de 6 casos

BALDWIN_STATUS=NOT_ESTABLISHED
BALDWIN_NAME=INVENTED_BY_AUTHOR
BALDWIN_DEFECT=PROVENANCE_DEFECT
BALDWIN_REPLACEMENT=NO_AUTOMATIC_GAP + BALDWIN_DIMENSIONAL(com_notacion)

DOMAIN_UNIVERSE_STATUS=UNIVERSE_PREDECLARED=NO
  UNIVERSE_SOURCE=NOT_AVAILABLE
  DOMAINS_EXPECTED=UNKNOWN
  DOMAINS_ANALYZED=15 (recontados: 11)
  UNKNOWN_GAPS_DENOMINATOR=NONE

NEGATIVE_CONTROL_STATUS=PARTIAL
  EXISTE_EN=D1,D2,D3 (11 estricto / 20 amplio; TESTING.md §5 lo exige para RESOLVED)
  FALTA_EN=D4.audit,D9,D10,D15

T31_STATUS=TEST_TAUTOLOGICAL
  COULD_FAIL_ON_DEFECT_03=NO
  CHECKS_INITIALIZATION=NO
  WRITTEN_AFTER_FIX=+75s
  MISREPORTS_COVERAGE=YES

COVERAGE_STATUS=SEARCH_COMPLETE_DECLARABLE / SEARCH_COMPLETENESS_PROVEN_NOT_REACHABLE
  ROUTER_UNIVERSE=ANALOGY_ONLY
  NEW_CONTRADICTION=ROUTER_COUNT_68_vs_100_Y_D8_AUSENTE
  PROMOTION=BLOCKED_PENDING_CLASSIFICATION

INDEPENDENCE_STATUS=I1r
  ACTOR=NO_ACREDITADO
  OBJECT=ACREDITADO  (COLLECTOR_REVIEWED=0985ad03…)
  MODE=ACREDITADO    (READ_ONLY_NO_EXECUTION_NO_SUDO)
  CRITERION=ACREDITADO (hallazgos por severidad)
  DATE=ACREDITADO
  CONTEXT=PARCIAL    (HOST_SCOPE, HEAD)

SELF_CORRECTION_STATUS=PARTIAL
  DETECCION=FUNCIONA
  CORRECCION=FUNCIONA
  REVALIDACION=PARCIAL (archivo tocado, no conjunto)
  RESIDUO_DETECTION=FUNCIONA (4/4)
  TASA_CON_DENOMINADOR=UNKNOWN

GLOBAL_GAP_STATUS=REFINED
  POR_MECANISMO=REFUTED
  POR_SUELO=CONFIRMED  (P4=0 y C=NO en los 11)

DOMAIN_COUNT=11   (MIG-07.7 decía 15)
CONFIRMED_GAPS=8
PARTIAL_GAPS=4
NO_GAPS=0         (D1 pasa a SUPPORTED)
UNKNOWN_GAPS=0    (sin denominador)
NOT_PROVEN_COUNT=0

SELF_DEFECTS_INTRODUCED=5   (M8-1..M8-5)
PROMOTION=BLOCKED
  RAZON_1=contradicción ROUTER-68-vs-100 sin clasificar
  RAZON_2=Baldwin sin fundamento
  RAZON_3=universo no declarado
  RAZON_4=control negativo sin extender a artefactos

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

```
KNOWN_DEFECT=CONFIRMED
  01-AUDITORIA/MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md:23
CORRECTION=DEFERRED
```

---

## 17. CONTRADICCIÓN NUEVA — PROMOCIÓN DETENIDA

El encargo ordena: *«Si aparece una contradicción nueva, detener la promoción y documentarla.»*

**`ROUTER-68-vs-100` + `D8 ausente`.** El `DOCUMENTATION-ROUTER` declara «Tabla de routing — 68
topics», contiene 100 filas `TOPIC`, y su secuencia de grupos salta de `D7` a `D9`.

**No la corrijo. No la clasifico unilateralmente.** Y tiene consecuencia directa: **el router
era la mejor candidata a declaración de universo del proyecto, y falla su propia verificación
en dos formas.** Eso degrada el mecanismo que RQ-7 necesitaría.

`PROMOTION=BLOCKED_PENDING_CLASSIFICATION`

**Y la contradicción tiene una segunda lectura posible que no puedo descartar:** si el router
declara 68 topics y tiene 100 filas, o el conteo es erróneo, o la tabla contiene filas que no son
topics. Ninguna de las dos se puede decidir sin el criterio de inclusión, que el router no
declara. `UNKNOWN`
