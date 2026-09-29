# KNOWLEDGE-POLICY

Normas del sistema de investigación, conocimiento, provenance, aprendizaje y
anti-repetición de `RX550-INVESTIGACION`.

**Estado:** `DESIGN_FROZEN`. Este documento **transcribe** el diseño congelado
(secciones B.2–B.8, B.12, B.13, D.1–D.3, J, K, L). No crea política nueva, no
altera la taxonomía, ni los estados epistémicos, ni las reglas de provenance.
`AGENTS.md` sigue siendo la autoridad superior: donde este documento y
`AGENTS.md` parezcan discrepar, `AGENTS.md` prevalece y la discrepancia se
registra como `CONTRADICTION`.

**Alcance de este documento:** reglas. No contiene datos. Los datos viven en
los cuatro artefactos TSV de este directorio.

---

## 1. Artefactos

| Artefacto | Fichero | Columnas | Contenido en Fase 1 |
|---|---|---:|---|
`SRC` | `SOURCE-REGISTRY.tsv` | 17 | cabecera, **0 filas** |
`KB` | `KNOWLEDGE-BASE.tsv` | 36 | cabecera, **0 filas** |
`NEG` | `NEGATIVE-KNOWLEDGE.tsv` | 14 | cabecera, **0 filas** |
`CTR` | `CONTRADICTIONS.tsv` | 14 | cabecera, **0 filas** |

Código de infraestructura: `knowledge_schema.py` (esquema, vocabularios,
validación de cabecera, E/S TSV), `src_registry.py` (generador `SRC`).
Pruebas: `test_knowledge_infrastructure.py`.

`router = proyección`. `DOCUMENTATION-ROUTER/` **no** es una fuente de verdad
sobre el conocimiento: consume estos artefactos. Su
`DOCUMENTATION-INVENTORY-ROUTING.tsv` es hoy un censo independiente; su
conversión en proyección pertenece a la **Fase 3** y no se ha hecho.

## 2. Ubicación

`MODEL_CHOICE` (no `HUMAN_POLICY`: `AGENTS.md:177` — una taxonomía o un nombre
no es una decisión humana). Los cuatro TSV residen en
`01-AUDITORIA/DOCUMENTATION-ROUTER/knowledge/`, junto al router que los
proyectará. La decisión formal `HD-01` sigue **abierta** y no bloquea: la
evidencia de que hace falta un artefacto nuevo ya está establecida
(`02-ARQUITECTURA/knowledge.md` se declara base de cierre; `AGENTS.md:379-382`
prohíbe reutilizar histórico).

## 3. Recuento de columnas — `ERROR_KIND=DOCUMENTARY` · `HD-09` RESUELTA

Las listas de columnas nombradas del diseño dan **SRC=17, KB=36, NEG=14,
CTR=14**. La sección `D.3` del mismo diseño declaraba **20/33/15/14**.

**`D.3 = 20/33/15/14` es un error documental de conteo. NO es una especificación
de columnas.** No existe columna alguna que lo respalde: `D.3` enuncia un
recuento y nunca una lista, de modo que la diferencia no es reconstruible desde
el diseño. Usar `D.3` como esquema obligaría a inventar 3 columnas de `SRC` y
1 de `NEG` sin nombre, y a retirar 3 de `KB` sin justificación.

| | |
|---|---|
`DECISION_ID` | `HD-09` |
`DECISION` | Las listas nombradas de `B.5`–`B.8` son el esquema autoritativo: `SRC=17`, `KB=36`, `NEG=14`, `CTR=14` |
`AGENT` | `HUMAN` |
`FECHA` | 2026-09-26 |
`ALCANCE` | `SRC` y `NEG`: la lista nombrada está **por debajo** de `D.3` (faltarían 3 y 1). `KB`: la lista nombrada está **3 por encima** de `D.3`. `CTR` (14) coincide en ambas y no requiere decisión |
`PROHIBICIONES` | No añadir `PUBLICATION_DATE`, ni `GIT_STATE`, ni ninguna otra columna. No eliminar columnas de `KB` |
`AUTORIDAD` | Este documento y las cabeceras de los cuatro TSV. El informe de diseño `DESIGN_FROZEN` **no está persistido en ningún fichero del repositorio** (verificado: 0 ficheros contienen `DESIGN_FROZEN`, `ENTITY_CLASS`, `SOURCE-REGISTRY`, `EPISTEMIC_STATE` o `REFERENT_DRIFT` fuera de este directorio), de modo que **este documento es la única referencia normativa en disco para los esquemas** |

- **Causa:** el recuento se escribió en `D.3` sin contrastarlo con las listas
  nombradas de `B.5`–`B.8`; el error se propagó a la especificación de Fase 1.
- **Corrección:** primero la lista nombrada por agente; ahora **confirmada
  por decisión humana** (`HD-09`). No se añadieron 3 columnas para alcanzar
  "20": hacerlo habría sido inventar campos, y el diseño lo prohíbe.
- **Prevención:** `test_frozen_column_counts_are_the_named_lists` fija los
  cuatro números, y `write_tsv` se niega a escribir si la cabecera no es
  exactamente la congelada, de modo que la deriva no puede llegar al disco.
- **Estado:** `RESOLVED` (decisión humana). `RULE_WORTHY=NO` — la regla "una
  lista de campos y su recuento deben derivarse del mismo origen" ya queda
  impuesta por código.

## 4. Sentinels para datos no disponibles

Un valor nunca está vacío. Se escribe un sentinel explícito.

| Sentinel | Significado |
|---|---|
`NOT_AVAILABLE` | la fuente/objeto no existe o no es accesible |
`NOT_DETERMINED` | hubo observación; no cierra la propiedad |
`NOT_DECLARED` | la fuente **no declara** versión |
`UNKNOWN` | sin host declarado; `AGENTS.md:38-41` prohíbe asignar uno en silencio |
`NOT_APPLICABLE` | la pregunta no tiene significado válido en ese contexto |

`VERSION_BASIS` y `RETRIEVAL_BASIS` son obligatorios y no vacíos: un sentinel
se justifica siempre.

## 5. Reglas duras del registro `SRC`

1. **`SHA256` es la identidad del contenido** y se calcula siempre del objeto
   real. Un hash declarado por un tercero se *verifica*, no se confía: una
   discrepancia se rechaza (`SHA256_REJECTED`).
2. **`VERSION` nunca se inventa.** Sin versión declarada: `NOT_DECLARED` +
   `VERSION_BASIS` no vacío.
3. **`COMMIT` nunca se inventa.** Es el último commit que tocó *ese* fichero;
   `NOT_AVAILABLE` si el fichero no está versionado por git. El `HEAD` del
   repositorio nunca sustituye al commit por fichero.
4. **`RETRIEVAL_DATE` es la fecha de adquisición/verificación, nunca de
   publicación.** `RETRIEVAL_BASIS` declara cómo se obtuvo (`mtime` no es una
   fecha de adquisición humana). Una fecha de publicación no tiene columna: se
   escribe en `NOTES` como `PUBLICATION_DATE=` y rechazarla si coincide con
   `RETRIEVAL_DATE`.
5. **`TEMPORALITY` ≠ `OBSOLESCENCE`.** `TEMPORALITY` responde *"¿cuándo era
   válido este contenido?"*; `OBSOLESCENCE` responde *"¿cuál es el ciclo de vida
   de este registro?"*. El generador no determina ninguno: `UNKNOWN` y
   `UNKNOWN_VALIDITY`. La existencia de un fichero no prueba que su contenido
   sea actual.
6. **`ENTITY_CLASS`**: `NOT_A_SOURCE` exige `SOURCE_TYPE=NOT_APPLICABLE`, y un
   rol real exige `ENTITY_CLASS ≠ NOT_A_SOURCE`. Registro no es promoción: el
   generador emite `NOT_A_SOURCE` por defecto.
7. **`REFERENT_DRIFT`** es un valor válido de `OBSOLESCENCE`: el `SHA256` del
   referente registrado ya no coincide. No se borra el registro; se degrada.
8. **`HOST_SCOPE` por defecto `UNKNOWN`.** El router tiene `HOST_SCOPE=UNKNOWN`
   en 1406 de 1576 filas; no se hereda ese valor ni se adivina ninguno.
9. **`ACCESS` es medido**: `GRANTED`, `DENIED` (existe, no se puede leer) o
   `SOURCE_ABSENT` (no existe). Un error de lectura nunca se convierte en
   ausencia.

## 6. Relación con git, y por qué no hay columna `GIT_STATE`

El diseño congelado fija 17 columnas y prohíbe añadir ninguna. La relación
`SOURCE_ID → objeto → SHA256 → COMMIT → estado git` se hace explícita con un
token fijo y legible por máquina dentro de `NOTES`:

```
GIT_STATE=TRACKED_CLEAN | TRACKED_DIRTY | UNTRACKED | NOT_A_GIT_REPO
```

`COMMIT` lleva el valor; `NOTES` lleva el estado. `GIT_STATE_TOKEN_RE` lo
valida. Alternativa rechazada: una columna `GIT_STATE`18ª, que rompería el
esquema congelado. `git status` **no** es fuente de verdad sobre el contenido:
un fichero `TRACKED_DIRTY` tiene como identidad el hash de sus bytes de árbol
de trabajo, no el del commit.

## 7. Límite de alcance de Fase 1

El generador **no** enumera el corpus. Enumerar es Fase 2 (migración). El CLI
exige `--path` explícito; sin él crea el registro vacío. Ninguna prueba lee,
escribe o enumera el proyecto. `U1`=1880 ficheros, `U1b`=304 sin catalogar,
`U2` y `U3b` quedan intactos y sin tocar.

## 8. Estados epistémicos (8, una sola casa)

Viven en `EPISTEMIC_STATE` (`KB` para `OPEN_QUESTION`/`HYPOTHESIS`/
`LIMITATION`; `NEG` para los 8). **Nunca** en `CLASS`. `AGENTS.md:20-23` es el
dueño del lado positivo (`OBSERVED`/`SUPPORTED`); esta lista es su complemento.

`UNKNOWN` · `NOT_INVESTIGATED` · `NOT_FOUND` · `NOT_OBSERVED` ·
`NOT_AVAILABLE` · `NOT_DETERMINED` · `NOT_APPLICABLE` · `PROVEN_ABSENT`

Eje discriminante: `NOT_FOUND` presupone búsqueda **dirigida al objeto**;
`NOT_OBSERVED` presupone un **barrido** que no alcanzó el elemento.
`NOT_INVESTIGATED` afirma **por qué** no se estableció; `UNKNOWN` afirma que no
se ha clasificado la causa.

**`PROVEN_ABSENT` es irrepresentable** salvo que se poblen seis campos:
`SCOPE` (universo) · `SEARCH_METHOD=SWEEP` · `SOURCES_SEARCHED` con al menos una
entrada · `VERSION_SCOPE` fijado · `LIMITATION` **vacía** · `REUSE_CONDITION` no
vacía. Ninguna ausencia por simple `grep`, clave, lista, fila o resultado
vacío qualify. Por eso 0 de los 7 casos reales del proyecto lo satisfacen.

## 9. Provenance (8 saltos)

`SOURCE` —Extraction→ `EXTRACTED_FACT` —Derivation→ `DERIVATION` —Derivation→
`CONCLUSION` —Analysis→ `MODEL` —Implementation→ `CODE_REF` —
Implementation→ `TEST_REF` —TestExecution→ `OBSERVATION`.

* `LOCATION` = `(CODE_ID, CODE_SHA256, LOC_ANCHOR)`. `fichero.py:1656` como
  provenance **se rechaza**: se rompe al mover una línea. `LOC_ANCHOR` es un
  símbolo, no un número de línea.
* Un hash **no** sustituye provenance semántica: identifica *qué*; el ancla y
  `SRC_FILE:LINE` localizan *dónde*; ninguno dice *por qué*.
* `FACT` o `CONCLUSION` sin cadena resoluble hasta `SOURCE_ID` o
  `HUMAN_DECISION_REF` se rechazan al escribir: huérfanos.
* `OBSERVATION`/`MEASUREMENT` exigen `ARTIFACT_SHA256` + `HOST_SCOPE` +
  `TEMPORALITY`.

## 10. Reglas de obsolescencia, contradicción y repetición

* `SUPERSEDED` exige `SUPERSEDED_BY` no vacío apuntando a un `KB_ID`/`CTR_ID`
  existente.
* `TEMPORALITY=HISTORICAL ⇒ OBSOLESCENCE=HISTORICAL`; nada `HISTORICAL` entra
  como `CURRENT`. Nada se borra jamás.
* `CTR` es append-only. `RESOLVED` exige `RESOLUTION_BASIS` no vacío. Un `CTR`
  `OPEN` es un estado legítimo y recuperable, con `FALSIFIER` obligatorio. Una
  `CONCLUSION` que toca un `CTR` `OPEN` debe enlazarlo.
* `NEG` exige `LIMITATION` no vacía (salvo `PROVEN_ABSENT`), que nombra por qué
  el resultado **no** prueba ausencia.
* Clave anti-repetición: `CONCEPT + SYMBOL + CLAIM + SCOPE + HOST + VERSION +
  QUESTION_TYPE`. `QUESTION_TYPE` es indispensable: *«¿qué significa
  `drm-client-id`?»* (`SEMANTICS`) y *«¿`drm-client-id` demuestra asociación
  proceso→GPU?»* (`RELATION_ATTRIBUTES`) comparten `CONCEPT` y `SYMBOL`, y sin
  esa columna la segunda heredaría `ALREADY_ESTABLISHED` de la primera.
  Respuestas: `ALREADY_ESTABLISHED` · `PARTIALLY_ESTABLISHED` · `CONTRADICTED`
  · `OBSOLETE` · `NOT_INVESTIGATED` · `REQUIRES_NEW_EVIDENCE`.

## 11. Aprendizaje

`ERROR_KIND ∈ {TOOLING, METHODOLOGICAL, FACTUAL, DOCUMENTARY, INTERPRETATION,
IMPLEMENTATION}`.

`ERROR → CAUSE → CORRECTION → PREVENTION` es la cadena mínima;
`RULE`, `TEST` y `KB` son condicionales. `CAUSE`, `CORRECTION` y `PREVENTION`
son obligatorios y no vacíos.

`RULE_WORTHY` (basta uno): destruye evidencia · daño irreversible · rompe
reproducibilidad · defecto sistémico · viola un requisito explícito de
`AGENTS.md` · riesgo grave y previsible. El umbral *"≥2 ocurrencias"* queda
derogado: excluiría un error único que destruyó evidencia.

`RULE_NOT_WORTHY`: error aislado sin daño a evidencia ni reproducibilidad, con
la corrección capturada en `KB` o `TEST`. **Ninguna regla nueva se escribe en
`AGENTS.md` sin autorización humana** (`MIG-07.9`: *«ninguna regla descubierta
se convierte en norma»*, `PROMOTION=BLOCKED`).

## 12. Preservación de evidencia

`AGENTS.md:371-377`. Sustituir un fichero de trabajo exige: copia byte-for-byte
a una ruta de recuperación → `SHA256` registrado y comparado → candidato
comparado antes de aplicarse. `write_registry` **rechaza** sobrescribir un
registro existente sin `recovery_dir`. Un fichero nuevo no tiene versión previa
que destruir, y por eso `HD-05` no bloquea la Fase 1.

Prohibido `git checkout --`, `git restore`, `git reset`, `git clean` sobre
ficheros de trabajo. Una reversión es una eliminación de evidencia.

## 13. Búsqueda: declarar el universo

Toda búsqueda debe declarar su universo antes de ejecutarse
(`MIG-07.9`, patrón `FN-1`, cuarta repetición). *«No apareció en lo que busqué»*
no es una afirmación sobre el universo. `U1`, `U2`, `U3` están declarados en el
diseño; `U2` y `U3b` permanecen `RECALL=NOT_DETERMINED`.

## 13b. Anclaje de un `NEGATIVE_RESULT` a su objeto físico — `MODEL_CHOICE`

`NEG` no tiene ninguna columna que cite un objeto físico (0 de 14). El ancla
vive en `KB.OBSERVED_IN`, que el diseño no normó: de 36 columnas de `KB`, sólo
9 tienen vocabulario cerrado o patrón; `OBSERVED_IN`, `ARTIFACT_SHA256` y
`RELATED_NEGATIVE` son texto libre con la única norma de "no vacío".

**Convención adoptada (`MODEL_CHOICE`, no vocabulario del schema):**

```
PATH_OR_URL=<ruta exacta del repositorio>;SHA256=<sha256 completo en minúsculas>
```

Se aplica en `KB.OBSERVED_IN` cuando el objeto no tiene fila `SRC`. El mismo
`SHA256` se repite en `KB.ARTIFACT_SHA256`, y `KB.RELATED_NEGATIVE` referencia
el `NEG_ID`.

**Límite declarado:** la convención no la valida ningún validador del schema.
Un `SRC` con `SOURCE_ID` sigue siendo el ancla preferida; esta convención
existe para el caso en que el objeto **no** debe promoverse a `SOURCE`
(descarga fallida, fragmento, binario sin rol de fuente). `NOT_APPLICABLE` en
`KB.SOURCE_ID` marca que no hay fila `SRC`.

**No es un `SOURCE_ID` nuevo** y no introduce columnas.

## 14. Qué NO cubre este sistema

Dos reglas de `AGENTS.md` no son verificables mecánicamente porque gobiernan
prosa fuera del registro: `RULE_WORTHY` (`PROSE-1`) y *«`PASS` requiere
evidencia»* (`VERDICT-1`). Se declaran `LIMITATION`. **No** se crea un artefacto
de veredictos para cubrirlas: la carga que producirían es la señal de que la regla
no es automatizable.

## 15. Decisiones humanas

| ID | Asunto | Estado |
|---|---|---|
`HD-01` | ubicación canónica de los TSV | **abierta**, no bloquea (`MODEL_CHOICE` aplicado) |
`HD-05` | versionar los TSV en git | **`NOT_BLOCKING_FOR_PHASE_1`**; bloquea el **commit** |
`HD-06` | regla de clasificación de los 304 ficheros no catalogados | **abierta**, **bloquea Fase 2** |
`HD-09` | esquema autoritativo de columnas | **`RESOLVED` 2026-09-26** — `SRC=17`, `KB=36`, `NEG=14`, `CTR=14` (listas nombradas). `D.3=20/33/15/14` es error documental de conteo, no especificación. Ver §3 |
`HD-06a` | `GravityMark_1.89.run` (193 327 384 B, `de090c7b9e40…`) | **`ARTIFACT`**, `SOURCE_TYPE=NOT_DETERMINED`. No hay 7º `SOURCE_TYPE`: un binario propietario de tercero no encaja en los 6 roles, y la razón queda en `NOT_DETERMINED` |
`HD-06a-2` | `SOURCE_TYPE` del binario externo | **`RESOLVED` 2026-09-26** — se mantiene `NOT_DETERMINED`; no se inventa rol |
`HD-06b` | `Unigine_Superposition-1.1.run.partial` (34 365 440 B, `5fdca56b5440…`) | **`NEGATIVE_RESULT`** — descarga parcial/cancelada, preservada (no borrada). Fila `NEG` escrita; fila `KB` **diferida**, ver `HD-06b-3` |
`HD-06b-2` | formato del vínculo `NEG`→objeto físico | **`RESOLVED` 2026-09-26** — convención `PATH_OR_URL=…;SHA256=…` en `KB.OBSERVED_IN`, `MODEL_CHOICE`, ver §13b |
`HD-06c` | `v23.done` (44 B) | **`NOT_A_SOURCE`** — flag sin productor/consumidor demostrado |
`HD-06d` | 139 regenerables (72+16+49+2) | **`CORPUS_ADMISSION=EXCLUDED_REGENERABLE_OR_RUNTIME_NOISE`** — fuera del corpus, **no** borrados, **no** `PROVEN_ABSENT` |
`HD-06b-3` | `KB.ERROR_KIND` no admite centinela y `CLASS=NEGATIVE_RESULT` no es un `ERROR` | **`REQUIRES_HUMAN_DECISION`** — ver abajo |
`HD-06e` | regla de admisión de los 301 restantes | **`NOT_RESOLVED`** |

`HD-05` en concreto: la política de historia del repositorio es humana
(`AGENTS.md:300` prohíbe `commit` sin autorización). La Fase 1 no requiere
`commit`: los ficheros son nuevos, no hay versión previa que sobrescribir, y
`git checkout` no puede afectar a un path ausente del índice. La decisión sigue
pendiente para el momento en que se quiera commitear.

## 16. `HD-06b-3` — límite de esquema no resuelto

Al escribir la fila `KB` que ancla el `NEGATIVE_RESULT` al objeto físico surge
un conflicto que **esta ronda no resuelve**:

`KB.ERROR_KIND` tiene vocabulario **cerrado** de 6 valores
(`TOOLING`, `METHODOLOGICAL`, `FACTUAL`, `DOCUMENTARY`, `INTERPRETATION`,
`IMPLEMENTATION`) y **no admite centinela**. Una fila
`CLASS=NEGATIVE_RESULT` no es un error, luego no hay valor honesto que escribir
en esa celda:

| Opción | Consecuencia |
|---|---|
`NOT_APPLICABLE` en `ERROR_KIND` | ✅ correcto, ❌ **amplía el dominio del schema** — prohibido en esta ronda |
uno de los 6 valores | ❌ afirmaría falsamente un `ERROR_KIND` |
dejar la celda vacía | ❌ `validate_value` rechaza vacío |
**no escribir la fila `KB`** | ✅ elegida. La fila `NEG` (14/14) **sí** se escribió; la fila `KB` queda sin escribir y **sin referencia colgante** |

**Falsificador de este límite:** una fila `KB` de clase distinta de `ERROR`
que se valide contra el esquema actual. No existe: `ERROR_KIND` es el único
campo de `KB` cuyo dominio no incluye ningún centinela y todas las clases no
`ERROR` deben rellenarlo.

**Estado:** `REQUIRES_HUMAN_DECISION`. Requiere o bien ampliar el dominio de
`ERROR_KIND` con un centinela (cambio de schema, `HD-09` no lo autorizó), o
bien una regla que diga qué valor llevar `ERROR_KIND` en filas que no son
`ERROR`.
