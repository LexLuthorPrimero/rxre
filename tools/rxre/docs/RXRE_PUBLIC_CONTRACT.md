# RXRE_PUBLIC_CONTRACT.md

Lo que una IA puede pedir y recibe. Nada más.

Este documento describe **el comportamiento medido** el 2026-10-05 contra
`linux-7.1.3`. No describe intención: describe lo que sale.

---

## 0. Cómo se habla con RXRE

Hay **dos interfaces**. Ninguna requiere conocer scripts internos.

### 0.1 JSONL — la que una IA usa

```bash
python3 tools/rxre/api/machine.py < peticiones.jsonl
```

Una petición por línea. Una respuesta (envelope) por línea, en el mismo orden.

Una línea malformada **no** tumba el lote: sale un envelope `error` y el bucle
sigue. Cada línea es independiente.

### 0.2 CLI — para una persona

```bash
tools/rxre/rxre <capacidad> [objetivo]
```

`--help` lista todo. Es la misma lógica por detrás.

---

## 1. Operaciones disponibles

`{"op":"ops"}` las devuelve, con descripción y ejemplo. MEDIDO:

| op | para qué |
|---|---|
| `query` | **la principal**. Responde una pregunta de RE. |
| `capabilities` | qué puede investigar y qué responde de verdad |
| `explain` | de dónde sale un `result_id` |
| `relation` | aristas que una herramienta produjo |
| `case` | paquete de handoff por `target`, por referencias |
| `plan` | **el camino hacia una capacidad, SIN ejecutarlo** |
| `backends` | qué backends hay, qué capacidades declara cada uno y cuáles se pueden pedir |
| `run` | **ejecuta una capacidad de reverse engineering** |
| `record` | **graba una hipótesis, un claim, una nota o la siguiente acción** |
| `checkpoint` | **el paquete de continuidad**: qué se sabe, qué queda abierto, qué sigue |
| `ops` | este catálogo |

### 1.1 `run` — ejecutar una capacidad de RE

```json
{"op":"run","capability":"binary.inspect","artefacto":"ruta/a/un.elf"}
```

`capability` es un **identificador cerrado** (`prefijo.nombre`). Sólo se acepta
si el registry la declara, tiene adapter, y está en estado `AVAILABLE` o
`PARTIAL`. Si no, devuelve `blocked` **con el motivo**: no hay adapter, o no hay
producer verificado, o el identificador no es válido.

El envelope trae dos estados distintos y no se mezclan: `status` (el del
envelope) y `backend_status` (el del producer: `ok`, `empty`, `unsupported`,
`blocked`, `invalid_input`, `error`). Se enumeran porque **colapsarlos
destruye información**: un backend que no sabe decompilar no está vacío, no sabe.

### 1.2 `plan` — el camino, antes de recorrerlo

```json
{"op":"plan","capability":"binary.decompile","question":"qué función escribe este registro"}
```

`execution` vale literalmente `"not_started"`. Cada paso declara tres cosas
**distintas**:

| campo | significa | **no** significa |
|---|---|---|
| `verifiable` | el registry afirma que hay producer | que vaya a funcionar |
| `available` | se puede pedir ahora | — |
| `reason` | por qué no, cuando no | — |

Un paso bloqueado **aparece igual**, con `available:false` y su motivo. Un plan
que sólo listara pasos ejecutables sería más vistoso y menos útil.

### 1.3 `record` — el estado de investigación

```json
{"op":"record","kind":"hypothesis","status":"OPEN","session":"s1",
 "target":"0000:01:00.0","text":"VM_CONTEXT0_CNTL lo escribe el reset, no el resume"}
```

`kind` ∈ `hypothesis` · `claim` · `note` · `next_action` · `frontier`.
`status` ∈ `OPEN` · `SUPPORTED` · `REFUTED` · `PROVEN` · `PARTIAL` ·
`NOT_DETERMINED` · `BLOCKED`.

Dos reglas que **no** sonbzonas de estilo:

- **Una `claim` no se puede grabar `PROVEN` sin `refs`.** Una conclusión que no
  se puede rastrear a evidencia no es `PROVEN`.
- **Una entrada de `record` no es evidencia.** `results` es lo que un *producer*
  emitió; una hipótesis es *interpretación*, y por eso va en su propia tabla.

`gap_kind` ∈ `HUECO_DE_EVIDENCIA` · `HUECO_DE_CONEXION` — y sólo para
`hypothesis` y `claim`. Distinguirlos importa: fusionarlos hace perseguir
mediciones que no van a responder nada.

### 1.4 `checkpoint` — continuar sin que nadie te lo explique

```json
{"op":"checkpoint","session":"s1","target":"0000:01:00.0"}
```

Devuelve hipótesis abiertas, hipótesis refutadas, claims, fronteras, la
siguiente acción, y **cuánta evidencia hay en la base** (operations, results,
edges). Es una vista: las entradas **apuntan** a sus `refs`, la evidencia se
cuenta y no se copia.

Es la operación que permite que una sesión continúe después de perder todo el
contexto conversacional, sin depender de que nadie recuerde el proyecto.

---

## 2. REQUEST

```json
{"op":"query","target":"0000:01:00.0","question":"quien escribe VM_CONTEXT0_CNTL"}
```

| campo | tipo | obl. | significado |
|---|---|---|---|
| `op` | str | sí | `"query"`, `"explain"`, `"relation"`, `"capabilities"`, `"ops"` |
| `target` | str | no | PCI. Defecto `0000:01:00.0`. **`0000:00:02.0` → `blocked`.** |
| `question` | str | sí* | pregunta en prosa. *o `capability` |
| `capability` | str | no | atajo para saltar el descubrimiento |
| `inputs.target` | str | no | objetivo explícito (registro, símbolo, fichero) |
| `inputs.max_hits` | int | no | tope de resultados por etapa. Defecto y máximo: **200** |
| `inputs.field` | str | no | campo de registro |
| `inputs.dir` | str | no | directorio para `provenance.keys` |
| `scope` | str | no | def. `linux-7.1.3` |
| `result_id` | str | solo `explain` | |
| `clase` | str | solo `relation` | `writers` · `readers` · `references` · `path` |
| `nodo` | str | solo `relation` | `"fichero.c:123"` |

### 2.1 `question` o `capability`, no los dos

Con `capability` y sin `question`, RXRE **sustituye** la question por
`"capacidad explicita: <cap>"`. Es un Synthetic para que el contrato de
validación la acepte; no aparece en la respuesta.

### 2.2 Lo que NO se acepta

- Campos desconocidos: se ignoran. No hay error.
- `op` inexistente → `error` con la lista de ops válidas.
- Línea no-JSON → envelope `error`, el lote continúa.
- `question` sin verbo ni término del dominio → `empty` pidiendo el objetivo.

---

## 3. RESPONSE

```json
{
  "schema_version": "1.0",
  "contract_version": "1.0",
  "engine_version": "0.2.0",
  "status": "ok",
  "operation": "register.writers",
  "target": "0000:01:00.0",
  "results": [],
  "evidence": [],
  "provenance": [],
  "limitations": [],
  "tools_used": [],
  "request": {},
  "next_actions": [],
  "stages": [],
  "operation_id": "op_...",
  "capability_resolution": {},
  "aristas": [],
  "relations_summary": {},
  "duration_s": 0.0
}
```

### 3.1 `status` — cuatro, y solo cuatro

| status | rc | significa |
|---|---|---|
| `ok` | 0 | produjo resultados |
| `empty` | 0 | **corrió y no encontró** |
| `blocked` | 2 | **no se ejecutó**, y se dice por qué |
| `error` | 1 | la herramienta falló |

`empty` y `blocked` comparten rc=0 a propósito. El detalle está en `status`, y es
ahí donde hay que mirar.

### 3.2 `results[]` — normalizados

Las 15 claves existen **siempre** en cada elemento:

`result_id` · `type` · `value` · `source` · `location` · `scope` · `tool` ·
`tool_version` · `input` · `timestamp` · `artifact` · `artifact_hash` · `status`
· `limitations` · `raw`

`raw` conserva el original sin reinterpretar. **`type` es lo que hace
interpretables resultados de nueve herramientas distintas.**

`type` medidos: `register` · `source_occurrence` · `trace_node` · `pm4_census` ·
`provenance_key` · `capabilities_item`.

### 3.3 `capability_resolution` — por qué se eligió

```json
{"resolved":"register.writers","confidence":"pista_explicita",
 "matched":{"capability":"register.writers","pistas":[3],"peso_total":3},
 "candidates":["symbol.locate"],
 "reason":"pista(s) de intencion que casaron en el enunciado",
 "detail":{"matched_patterns":["\\b(escribe|escritor|...)\\b"]},
 "options":[ ... 12 capacidades ... ]}
```

`candidates` son las **perdedoras**. Sin ellas, una respuesta y una coincidencia
única se verían igual.

Si no casa ninguna: `resolved: null` + `options` con el catálogo entero. RXRE
**no adivina**.

### 3.4 `next_actions[]` — CUIDADO

```json
{"action":"explain","why":"...","produces":"..."}
```

Tres acciones distintas según estado:

| estado | acciones |
|---|---|
| `ok` | `explain`, `provenance` |
| `empty` | `cross_check`, `widen_scope` |
| `blocked` | `read_blocked_reason` |
| `error` | `capabilities` |

> **HUECO MEDIDO.** `provenance` **no es una `op`**. La respuesta lo propone y
> `{"op":"provenance"}` devuelve `error: operacion desconocida`. `explain` sí
> existe. Ver `RXRE-003-HUECO-01`.
>
> `cross_check` y `widen_scope` tampoco son ops ejecutables hoy.

### 3.5 `stages[]` — el pipeline

```json
[{"step":"definition","op":"register","status":"ok",
  "resultados":1,"raw_resultados":1,"limitations":[...]}]
```

`op` es la **capacidad** (`register`, `search`), no el script. El script real
está en `capabilities` y en `tools_used`.

### 3.6 `limitations[]` — obligatorio en `empty`

`empty` sale **siempre** con `limitations` no vacío, y nunca propone concluir que
no existe.

### 3.7 `aristas[]` y `relations_summary`

```json
{"src":"drivers/gpu/drm/amd/amdgpu/gfxhub_v1_0.c:223","tipo":"WRITES",
 "dst":"VM_CONTEXT0_CNTL","status":"observed","tool":"evidence_search.py",
 "evidence":{"patron":"escritura","text":"tmp = REG_SET_FIELD(...)"},
 "limitations":["candidato, no escritor demostrado"]}
```

Derivan del **patrón de texto** del uso. `status` es `observed`, nunca `proven`.
Si el texto no casa con ningún constructor conocido → `REFERENCES`, **no**
`READS`.

### 3.8 `operation_id` y `result_id`

- `operation_id` = `op_` + hash. Persiste el envelope entero en SQLite.
- `result_id` = `res_<tipo>_` + hash del **contenido**.

Un `result_id` es **determinista**: la misma consulta dos veces da los mismos
ids. Un id **no persistido** no existe: eso es `empty`, no `error`.

### 3.9 `explain`

```bash
{"op":"explain","result_id":"res_register_124ada0de01e"}
```

Trae `result`, `operation` y la cadena conceptual
`result → operation → tool → input → artifact → source`.

Un `result_id` inexistente → `empty` con: *«no hay ninguna fila con ese
result_id en esta base. Eso NO es que el resultado no exista: es que no se ha
registrado aquí»*.

> **HUECO MEDIDO.** La cadena `chain` es una lista de **nombres**, no de
> valores. Los datos vienen en `result` y en `operation`, pero no hay un
> eslabón por paso. Ver `RXRE-003-HUECO-02`.

---

## 4. `capabilities` — descubribilidad

```json
{"capability":"register.writers",
 "question":"¿Quién escribe este registro?",
 "requires":["register_name"],
 "resolved_by":["register","search"],
 "max_hits":200,
 "example":{"operation":"search","inputs":{"target":"VM_CONTEXT0_CNTL"}},
 "limitations":["los escritores se derivan del PATRON de texto del uso: ..."]}
```

12 capacidades. Cada una lleva `limitations` con lo que **no** puede afirmar.

`resolved_by` son verbos, no scripts. **Una IA puede elegir sin saber que existe
`evidence_search.py`.**

---

## 5. Límites declarados, no descubiertos

| límite | dónde se declara |
|---|---|
| `xref` sale `blocked` (AST a medias) | `status` + `limitations` |
| autores = candidatos, no escritores | cada `arista.limitations` |
| `pct` es porcentaje, no recuento | cada `provenance_key.limitations` |
| `pm4` es texto, no JSON | `limitations` del `pm4_census` |
| writers no son únicos | `register.writers.limitations` |

---

## 6. Ausencias reales

**Documentadas aquí porque son huecos, no features pendientes.** Cada fila dice
cómo se comprobó que sigue faltando; ninguna se heredó sin volver a mirar.

| falta | efecto en una IA | cómo se comprobó (2026-10-06) |
|---|---|---|
| `binary.decompile` | no se puede descompilar | `UNAVAILABLE` en los dos backends medidos; `angr` y `rz-ghidra` siguen `NOT_DETERMINED` |
| `relation path` A→B | devuelve aristas que tocan un nodo, no un camino | `op:relation` no acepta origen y destino |
| `dwarf`, `binary` (el resto de capacidades de RE) | declaradas pero sin adapter | `op:backends` las lista en `no_ejecutables` con el motivo |
| `angr`, `rz-ghidra` | backends analíticos sin verificar | `NOT_DETERMINED`: no instalados, no compilados |
| `binary.cfg`/`callgraph` en rizin | ASCII, no JSON | `PARTIAL` con la limitación en las notas del backend |

### 6.1 Lo que YA NO está ausente

Estas afirmaciones se corrigieron el 2026-10-06 porque eran **falsas**: la
interfaz las tenía, el contrato no lo sabía.

| se decía | realidad medida |
|---|---|
| «**No hay `plan`**» | `op:plan` responde `ok`, `execution:"not_started"`, 6 pasos |
| «`op: plan` — no puede inspeccionar el camino antes de ejecutarlo» | corregido arriba (§1.2) |
| «`op: session`/`handoff` — no puede recuperar una investigación» | `op:checkpoint` + `op:record` (§1.3, §1.4) |
| «`op: provenance` — `next_actions` lo propone y no existe» | la provenance viaja en el envelope y `explain` la reconstruye |
| «`next_actions` ejecutables: 3 de 4 no son invocables» | **4 de 4 invocables** (medido) |
| «`dwarf`, `binary` — no hay adaptador» | sigue faltando, pero ahora con `binary.inspect` funcionando y el resto declarado |

> un contrato que afirma una ausencia inexistente es peor que un contrato
> callado: la IA no busca lo que dice que no existe

---

## 7. Errores de uso

| caso | status | dice |
|---|---|---|
| `op` inexistente | `error` | la lista de ops válidas |
| línea no-JSON | `error` | el error de parseo; el lote sigue |
| sin `op` | `error` | falta `op` |
| `target: 0000:00:02.0` | **`blocked`** | la Intel queda fuera de toda operación |
| `question` sin objetivo extraíble | `empty` | pide `inputs.target` |

`0000:00:02.0` → `blocked` y no `error`: *«no lo hago por política»* no es *«lo
intenté y falló»*.

---

## 8. Reproducir una operación

```bash
# misma pregunta dos veces -> mismos result_id
echo '{"op":"query","question":"donde esta VM_CONTEXT0_CNTL"}' | python3 tools/rxre/api/machine.py | python3 -c "import sys,json; print([r['result_id'] for r in json.load(sys.stdin)['results']])"
echo '{"op":"query","question":"donde esta VM_CONTEXT0_CNTL"}' | python3 tools/rxre/api/machine.py | python3 -c "import sys,json; print([r['result_id'] for r in json.load(sys.stdin)['results']])"
```

Base: `tools/rxre/storage/rxre.sqlite3` (WAL). Variable `RXRE_DB` para otra ruta.

---

## 9. Persistencia

```sql
operations(operation_id, request_id, contract_ver, operacion, capability,
           question, target, scope, status, n_results, request_json,
           response_json, timestamp, duracion_s)
results(result_id, operation_id, type, value, source, file, line, scope,
        tool, tool_version, status, raw_json, timestamp)
edges(src, tipo, dst, status, scope, tool, evidence_json, operation_id,
      result_id, timestamp)
relations(src_operation, src_result, dst_operation, relation, payload_json)
```

`edges` = relaciones del **dominio RE** (WRITES, READS...).
`relations` = aristas de **composición** entre llamadas.
Son grafos distintos y no se mezclan.

`operations.operation_id` y `results.operation_id` son FK. `edges.operation_id`
admite `NULL`: una arista **sin** provenance es guardable, y poder distinguir
"no tiene provenance" de "tiene provenance" es lo que hace útil la columna.

---

## 10. Alcance

`0000:01:00.0` permitido. `0000:00:02.0` bloqueado antes de ejecutar.

RXRE-003 no lee hardware, no completa el build, no escribe en el árbol de
fuentes. El ioctl que se ejecuta (`AMDGPU_INFO_DEV_INFO`) es de lectura, y en la
tanda actual ni siquiera se llama.