# RXRE — CONTRATO DE IDENTIDAD DE RESULTADOS Y PROCEDENCIA

> **Estado**: contrato propuesto. **No implementado.** Ninguna migración se ha
> ejecutado. Ningún cambio de schema se ha aplicado.
>
> Este documento fija la semántica **deseada** y la separa del comportamiento
> que SQLite impone hoy. Cuando divergen, gana el contrato y se marca la
> divergencia como deuda.

**Ámbito**: `results`, `operations`, `edges`, `execution_events`, `store.registrar`,
`store.explicar_operacion`, y las 9 rutas que llegan a `store.registrar`.

---

## 0. Vocabulario (no son sinónimos)

| Término | Definición en este contrato | Dónde vive |
|---------|---------------------------|------------|
| **Identidad** | Lo que dos cosas comparten para ser *la misma* | `results.result_id` |
| **Contenido** | Lo observado: el valor y sus metadatos | `results.value`, `raw_json` |
| **Observación** | El acto de que una operación ve ese contenido | **NO EXISTE HOY** |
| **Procedencia** | Quién observó, cuándo y desde qué operación | `execution_events` (parcial) |
| **Propiedad** | Quién "posee" el contenido | **SIN CONCEPTO** (ver §3) |
| **Idempotencia** | Repetir no crea contenido nuevo | guarda `COLISION:` |
| **Integridad** | Que lo declarado y lo almacenado coincidan | `operations.n_results` (roto) |

Cuatro de estos siete no tienen representación en el schema actual. Esa es la
deuda que este contrato describe.

---

## 1. Decisiones contractuales

### D1 — `result_id` identifica **contenido**, no observación

**Evidencia directa**:
- `rz_inspect._id_resultado` (líneas 77–94) calcula
  `sha256("RAW_BINARY|artefacto|backend|json.dumps(valor, sort_keys=True)")[:12]`.
  Verificado: dos dicts con distinto orden de claves producen el **mismo** id
  (`d2bca9cdd531` en ambos casos).
- El docstring declara la intención: *"Un identificador que NO colisiona. Regla
  de F6"*, y documenta el bug que corrigió: *"36 usos del mismo texto daban 9
  ids distintos, y con `INSERT OR REPLACE` 36 filas se convertían en 9 sin que
  nada lo notara"*.

**Contrato**: el contenido tiene identidad global e inmutable. Dos operaciones
que observan lo mismo observan **la misma cosa**.

**Descartado**: identidad de observación (modelo B). Obligaría a los productores
a incluir la operación en el hash, destruyendo la deduplicación que la guarda
`COLISION:` busca explícitamente.

---

### D2 — Una observación es una **relación única contenido↔operación**

**Pregunta que este contrato debe responder** (punto 6 de la misión): ¿una
observación es una relación única o cada aparición individual?

**Decisión**: **relación única**. `UNIQUE(result_id, operation_id)`.

**Justificación**: una misma operación no puede observar dos veces lo mismo en la
misma invocación — su `results` es una lista de ids distintos. Registrar la
segunda aparición sería ruido que no aporta información. Además, una relación
única hace `n_results` determinista sin contar.

**Consecuencia**: si el **mismo par** (contenido, operación) llega dos veces, es
idempotencia, no una observación nueva.

---

### D3 — La atribución histórica **no se reasigna**

**Evidencia del problema** (`modelos_identidad_contraste.py`, casos 1, 3, 4):
- El dueño de un `result_id` es **la última** observación (1.1).
- La primera queda con 0 filas declarando `n_results=1` (1.2).
- Una repetición **idéntica** también reasigna (3.1) — la idempotencia actual es
  de *contenido*, pero produce el efecto lateral de *transferir propiedad*.
- `edges` y `execution_events` **no** se reasignan (4.1): quedan citando una
  operación que ya no posee el resultado (4.2).

**Contrato**: la procedencia de una observación es **inmutable**. Reobservar
contenido existente **agrega** una observación; **nunca** transfiere ni borra la
anterior.

**Propiedad**: este contrato **elimina el concepto de propiedad**. No hay dueño:
hay autores de observaciones. El `operation_id` de la fila `results` deja de ser
"dueño" y pasa a ser "primera observación" — un dato histórico, no de control.

---

### D4 — Repetir contenido idéntico es idempotencia

**Contrato**: si `result_id` existe y el contenido canónico coincide, se crea la
observación (si no existía) y **no** se toca la fila de contenido.

**Evidencia de que hoy funciona así**: la guarda `COLISION:` (8 rutas) evita el
`INSERT OR REPLACE` antes de que ocurra (`GUARD2`: devuelve `COLISION:G1` sin
reescribir).

---

### D5 — Mismo `result_id` con contenido incompatible ⇒ **conflicto explícito**

**Comportamiento actual** (demostrado, caso 2 del contraste): el contenido
anterior **se sobrescribe sin aviso**. Nada lo detecta.

**Contrato**: debe producir un **conflicto declarado**, nunca sobrescritura
silenciosa. El envelope debe reportar el conflicto con el `result_id` afectado y
**no** escribir.

**Justificación**: el propio código ya documenta por qué esto importa — *"36
filas se convertían en 9 sin que nada lo notara"* (`rz_inspect.py`). Ese fue un
bug de identidad; el conflicto de contenido es el mismo fallo en otra forma.

---

### D6 — La igualdad de contenido se define por una representación **canónica concreta**

**Hallazgo verificado** — `store.py:874`:
```python
str(r.get("value", ""))[:4000],   # value
```
Esto **no es canónico** y **está truncado**:

| Comprobación | Resultado |
|--------------|-----------|
| `str({'a':1,'b':2})` vs `str({'b':2,'a':1})` | **Distintos** — depende del orden de inserción |
| Valor de 5000 caracteres | `value` queda en **4000**, `raw_json` en 5045 |
| Dos contenidos largos **distintos** | Producen el **mismo** `value` truncado |

**Contrato**: la igualdad de contenido se evalúa sobre
`json.dumps(resultado, sort_keys=True, default=str)` — que **sí** es canónico
para estructuras JSON (verificado: `a` y `b` dan el mismo texto).

**Se rechaza usar `value`** como criterio de igualdad: no es canónico y trunca.
**Se rechaza usar `raw_json` textual** sin normalizar: `raw_json` serializa el
dict *completo* del resultado, no solo el contenido, y `default=str` puede
introducir `repr()` con direcciones de memoria no deterministas.

**Pregunta abierta**: qué hacer cuando `default=str` produce texto no
determinista. No resuelto.

---

### D7 — Definición exacta de `n_results`

La misión pide distinguir tres números. **Solo uno puede vivir en
`operations.n_results`**; los otros dos no tienen columna.

| Magnitud | Definición | ¿Existe? |
|----------|-----------|----------|
| **Elementos emitidos** | `len(env["results"])` — lo que el productor entregó | ✅ `n_results` hoy |
| **Contenidos distintos** | `COUNT(DISTINCT result_id)` de las observaciones de la operación | ❌ no existe |
| **Observaciones** | filas de `result_observations` de la operación | ❌ no existe |

**Contrato** — con D2 (relación única) las tres magnitudes **coinciden siempre**.
Por tanto:

> **`operations.n_results` = número de observaciones de la operación = número
> de contenidos distintos observados.** Se invariante.

**Consecuencia**: la declaración de discrepancia de `explicar_operacion`
(`store.py:913-940`, añadida en F1/F4-C2) pasa a ser **innecesaria** — no por
que la contradicción sea rara, sino porque el sistema la vuelve **imposible**.

**Nota sobre el histórico**: los 46 registros actuales tienen
`n_results == len(response_json.results)` (verificado: 45/45 antes de las
inserciones de F1/F4; 46/46 después). Bajo el contrato nuevo, el valor histórico
se lee como "contenidos distintos", lo cual es una **reinterpretación** de un
campo existente, no una migración de datos.

---

### D8 — Consultas, procedencia y observaciones repetidas

| Consulta | Contrato |
|----------|----------|
| Resultados de una operación | `JOIN results r ON r.result_id = o.result_id FROM result_observations o WHERE o.operation_id = ?` |
| Contenido global por id | `SELECT * FROM results WHERE result_id = ?` — estable, nunca reasignado |
| Procedencia de un contenido | `SELECT * FROM result_observations WHERE result_id = ?` — **N filas**, una por operación que lo observó |
| Observaciones repetidas | Colapsadas por D2: `(result_id, operation_id)` es único |

**El caso "misma operación, dos veces"** (D2) aparece como **una** observación.
Si el consumidor necesita distinguir dos invocaciones, el `operation_id` ya las
distingue (es distinto por invocación, porque incluye `time.time()` en
`store.py:852`).

---

### D9 — Integridad referencial y atomicidad

**Invariantes**:

| # | Invariante | Mecanismo |
|---|-----------|-----------|
| I1 | Todo `result_id` de una observación existe en `results` | FK `result_observations.result_id → results.result_id` |
| I2 | Toda operación de una observación existe | FK `→ operations.operation_id` |
| I3 | Una observación por par | PK compuesta `(result_id, operation_id)` |
| I4 | `n_results` == número de observaciones | Invariante de aplicación, verificada por test |
| I5 | El contenido de un `result_id` no cambia tras su primer INSERT | Sin `OR REPLACE`; verificación por hash canónico |

**Atomicidad**: `results` y `result_observations` deben escribirse en **una sola
transacción**. El comportamiento actual ya lo cumple — un solo `c.commit()`
(`store.py:879`) tras ambas escrituras, y verificado: una violación `NOT NULL`
a mitad del bucle deja la BD sin ninguna de las dos filas (`ATOM1`).

**Consecuencia de D5**: si hay conflicto de contenido, el `INSERT` en
`result_observations` **no** debe ocurrir. O todo, o nada.

**Deuda a corregir**: `edges.result_id` y `execution_events.result_id` son texto
**sin `REFERENCES`** (verificado: solo 8 FKs en el schema, ninguna sobre
`results`). Bajo el contrato pasarían a tener FK válida, lo que **expondría**
referencias colgantes hoy invisibles (las 76 de `execution_events` con
`operation_id = "COLISION:..."` y los 7 huérfanos — §10).

---

### D10 — Los 7 huérfanos y los 76 marcadores `COLISION:`

**Verificado con consultas de solo lectura. NO reparados en esta misión.**

| Grupo | Diagnóstico | Tratamiento propuesto |
|-------|-------------|------------------------|
| **7 `results` huérfanos** (`res_parity_*`, `rxre_ps5_013_*`) | `operation_id` **sin prefijo `op_`** y `timestamp` en epoch (`1791912403`), no ISO. `store.registrar` escribe `%Y-%m-%dT%H:%M:%S%z`. **No los escribió `store.registrar`**: inserción por script el 2026-10-13 | Declararlos en `limitations` del backfill. **No inventar** una operación padre |
| **76 `execution_events` con `operation_id = "COLISION:res_..."`** | La guarda devuelve ese marcador y `dispatch` lo asigna a `env["operation_id"]` (`store.py:108-110`). **0 filas** en `operations` con ese id | Bajo D3, el marcador **se elimina**: una colisión deja de ser un "retorno" y pasa a ser una **observación creada**. El `operation_id` vuelve a ser un id real |

**Nota**: el novena productor (`rz_findings._persistir`) **no escribe `results`**
— verificado: `rxre.create_finding` valida que `evidence_ids` ya existan y
escribe solo en `findings`. Tras un `create_finding` exitoso, `results` conserva
la misma única fila y `operations` no recibe fila nueva. **No hay hueco de
cobertura que cerrar.**

---

### D11 — Límites del backfill

**Lo que un backfill PUEDE hacer**:
- Por cada fila actual de `results`, crear **una** observación con su
  `operation_id` actual. Total: 272 observaciones reconstruidas.

**Lo que NO puede**:
- **No recupera historia perdida.** No existe evidencia de cuántas operaciones
  observaron cada contenido antes de la última.
- **No recupera contenido sobrescrito.** Los casos 2 y 5 del contraste lo
  demuestran: el valor anterior desapareció sin rastro.
- **No es historia original.** Cada observación reconstruida es una
  *afirmación* de que esa operación observó ese contenido; es cierta, pero es
  la **última** observación conocida, no todas.

**Declaración obligatoria en la migración**: el backfill produce
`observaciones reconstruidas desde el estado actual`. No debe presentarse como
procedencia histórica completa.

**Testimonio parcial**: `execution_events` conserva `result_id` de observaciones
anteriores — 163 eventos, con `operation_id` a veces real y a veces `COLISION:`.
Es el **único** rastro de observaciones previas que sobrevive, y cubre solo
`results[0]` de cada ejecución (verificado: con 5 resultados, se registra 1).

---

### D12 — Inventario de lo que una migración debe revisar

| Elemento | Ubicación | Riesgo |
|----------|-----------|--------|
| 9 productores de `result_id` | `dispatch.py:470`, 7 adapters, `rz_findings.py:131` | **Bajo**: el contrato no cambia lo que producen |
| 8 guardas `COLISION:` | `dispatch.py:468`, `rz_inspect:488`, `ts_ast:609`, `umr_read:679`, `rz_callgraph:665`, `rz_xrefs:601`, `gh_decompile:722`, `rz_cfg:374` | **Alto**: la semántica de la guarda **cambia** — deja de ser "no escribir" y pasa a ser "no escribir contenido, sí escribir observación" |
| `store.registrar` | `store.py:842-886` | **Alto**: el `OR REPLACE` se elimina; `value[:4000]` deja de ser criterio |
| `store.explicar_operacion` | `store.py:889-940` | **Medio**: la JOIN cambia; la declaración de discrepancia se vuelve obsoleta |
| `operations.n_results` | `store.py:855,862` | **Medio**: reinterpretación, no recálculo |
| `edges.result_id` | `store.py:124` (sin FK) | **Alto**: añadir FK expone colgantes |
| `execution_events.result_id` | `store.py:471` (sin FK) | **Alto**: ídem; 76 filas con id inexistente bloquearían la FK |
| `re_case` | `store.py:1131` | **Ninguno**: sin consumidores (verificado) |
| `_sintetizar` | `machine.py:919` | **Ninguno**: recalcula del envelope vivo, no de la columna |
| Tests | 15+ ficheros mencionan `n_results`/`result_id`/`explicar_operacion` | **Alto**: las expectativas de `n_results` cambian |

---

## 2. Alternativas descartadas

| Alternativa | Por qué se descarta |
|-------------|---------------------|
| **A — identidad global, 1 fila** (comportamiento actual) | Impuesta por el storage, no por un contrato. Contradice la procedencia que `execution_events` ya guarda (casos 4.1/4.3) |
| **B — PK compuesta `(result_id, operation_id)`** | Obliga a los productores a incluir la operación en el hash; destruye la deduplicación que `COLISION:` busca |
| **Calcular `n_results` como `COUNT(*)`** | No resuelve duplicados: 2 elementos con igual `result_id` dan conteo 2, filas 1 |
| **Comparar `value` para detectar conflicto** | No es canónico y trunca a 4000 chars (§D6, verificado) |
| **Añadir la guarda de colisión a `rz_findings`** | El productor no escribe `results`; la guarda sería código muerto |

---

## 3. Preguntas abiertas

| # | Pregunta | Por qué sigue abierta |
|---|----------|----------------------|
| P1 | ¿Qué hacer si `json.dumps(default=str)` produce texto no determinista (direcciones de memoria)? | No medido. Afecta a la detección de conflicto (D5) |
| P2 | ¿Una observación registra el **contenido en ese momento** o solo la referencia? | Si el contenido es inmutable (D1), la referencia basta. No verificado que el productor no mute el dict tras emitirlo |
| P3 | ¿Debe `n_results` histórica reinterpretarse o versionarse? | 46 registros con el valor antiguo |
| P4 | ¿Qué hacer con las 76 filas de `execution_events` con `operation_id` inexistente al añadir la FK? | Requiere decisión: reparar, o declarar la FK como `DEFERRABLE`/parcial |
| P5 | ¿El backfill crea observación para los 7 huérfanos? | No hay operación padre que vincular |

---

## 4. Conflictos con el comportamiento actual

| Contrato | Comportamiento actual | Divergencia |
|----------|----------------------|-------------|
| D3 — procedencia inmutable | El dueño es la última observación | **Contradicción** |
| D5 — conflicto explícito | Sobrescritura silenciosa | **Contradicción** |
| D6 — igualdad canónica | `value` = `str(...)[:4000]` | **Contradicción** |
| D7 — `n_results` invariante | Se desincroniza; se declara la discrepancia | **Contradicción** |
| D1 — identidad de contenido | Ya es así | Cumple |
| D2 — relación única | Implícita (una fila por id) | Cumple |
| D4 — idempotencia | La guarda `COLISION:` ya lo hace | Cumple |

**Cuatro contradicciones de siete decisiones.** Este contrato no describe el
sistema actual: describe el sistema que la evidencia sostiene.

---

## 5. Tests discriminantes que el contrato habilita

Derivables del contrato, sin implementarlo:

| Test | Discrimina | Falla hoy |
|------|-----------|-----------|
| T1: reobservar contenido existente crea 2 observaciones | D2, D3 | ✅ falla: hay 1 fila, dueño cambiado |
| T2: `n_results` == observaciones, siempre | D7 | ✅ falla tras reobservar |
| T3: mismo `result_id` con contenido distinto ⇒ conflicto, no escritura | D5 | ✅ falla: sobrescribe |
| T4: orden de claves distinto ⇒ mismo contenido, no conflicto | D6 | ✅ falla: `value` difiere |
| T5: valor >4000 chars ⇒ detección de conflicto correcta | D6 | ✅ falla: truncado |
| T6: `explicar_operacion` no declara discrepancia | D7 | ✅ falla hoy: declara |
| T7: excepción a mitad ⇒ ni contenido ni observación | D9 | ✅ **pasa hoy** (atomicidad ya existe) |

---

## 6. Evidencia de la base de desarrollo (solo lectura)

```
sha256: 396e68380ad8878d479a8893ef9ae403   (sin cambios)
operaciones con n_results>0 y 0 filas ....... 0
reasignaciones reales entre operaciones ..... 0
operaciones con n_results != filas reales .... 0
edges colgantes ............................. 0
results huerfanos ........................... 7
execution_events con operation_id COLISION: . 76
```

**Daño histórico por colisión: CERO.** El modelo C no repara historia perdida;
previene la siguiente.

---

## 7. Nota sobre alcance

Este documento **no** autoriza implementación. La siguiente misión debería:
1. Validar P1–P5.
2. Redactar la migración.
3. Revisar las 8 guardas `COLISION:` (D4 cambia su semántica).

Implementar sin resolver P1 y P4 deja el sistema con una FK que no se puede
crear.