# RXRE-002 — la capa que una IA usa sin conocer los scripts

RXRE-001 es una CLI que agrupa herramientas. RXRE-002 es la capa que responde a
**una pregunta**.

```bash
echo '{"op":"query","target":"0000:01:00.0","question":"quien escribe VM_CONTEXT0_CNTL"}' \
  | python3 tools/rxre/api/machine.py
```

La IA no necesita saber que existe `evidence_search.py` ni que
`reg_resolve.py` no ve nada en `asic_reg` para ese símbolo.

## Qué hay

| fichero | fase | qué hace |
|---|---|---|
| `api/request.py` | A | contrato request/response, `next_actions`, target permitido |
| `api/machine.py` | A | JSONL sobre stdin; una línea rota no tumba el lote |
| `core/capabilities.py` | B | catálogo de 11 **intenciones** → herramientas, con límites declarados |
| `core/engine.py` | C/F | despacho y pipelines deterministas con estado por etapa |
| `core/normalize.py` | D | resultado normalizado con las 15 claves + `raw` siempre |
| `core/store.py` | E | SQLite (WAL): `operations`, `results`, `relations`, `edges` |
| `commands/query.py` | B–G | `query`, `explain`, `relation` |

## El contrato

**Request**: `operation`, `question`, `capability`, `target`, `inputs`, `scope`,
`constraints`, `requested_evidence`.

**Response**: las 11 claves del envelope de RXRE-001, más `request`,
`next_actions`, `stages`, `operation_id`, `aristas`, `capability_resolution`.

Estados: `ok` · `empty` · `blocked` · `error`. rc: 0 · 0 · 2 · 1.

### Las tres reglas que el contrato hace imposibles de violar por accidente

**1. `empty` no es ausencia.** Un `empty` sale siempre con `limitations` diciendo
que la herramienta corrió y no encontró, y **nunca** propone concluir que no
existe: ofrece `cross_check` o `widen_scope`.

**2. `blocked` no es `empty`.** `xref.py` sale con rc=3 porque el AST del árbol
está a medias. Traducirlo a `empty` haría que una IA concluyera que
`amdgpu_vm` no tiene referencias. Sale `blocked`, rc=2, y no ejecuta.

**3. Un `PROVEN_ABSENT_*` acotado no es un hallazgo.** `reg_resolve.py` responde
`ok` con `PROVEN_ABSENT_EN_ASIC_REG` para un símbolo inexistente, porque *no hay
definición de offset en `asic_reg`* sí es una respuesta correcta. El pipeline lo
detecta y lava el estado a `empty`.

## Composición determinista

```
register.writers  =  register  →  search
register.uses     =  register  →  search
symbol.callers    =  search    →  trace
pm4.opcodes       =  pm4
```

Determinista, no planificado. Dos preguntas iguales dan los mismos `result_id`,
porque los ids se derivan del contenido y no del reloj.

Un `empty` en una etapa **no** para la composición (la siguiente es otra
pregunta). Un `blocked` **sí** se propaga (la siguiente depende de esta).

## Relaciones

`WRITES` / `READS` se **derivan** del patrón de texto del uso
(`REG_SET_FIELD`, `REG_RMW`, `WREG`, `RREG`, `READ_DWORD`), y cada arista nace
`observed` con su limitación escrita:

> un uso que casa con un constructor de escritura es un **candidato** a escritor;
> demostrar que escribe exige ejecutar la función

Si el texto no casa con ningún constructor conocido, la arista es `REFERENCES`,
**no** `READS`.

MEDIDO: no existe en `tools/` ninguna herramienta que clasifique lectura/escritura
de un registro. La derivación es explícita y esa es su limitación.

## Alcance

`0000:01:00.0` es el único target. `0000:00:02.0` (Intel HD 4600) devuelve
`blocked` antes de ejecutar nada, y lo dice:

```
blocked · la GPU integrada del procesador queda fuera de TODA operación (§32)
```

RXRE-002 no lee hardware. No completa el build. No escribe en el árbol de fuentes.

## Pruebas

```bash
python3 tools/rxre/tests/test_rxre.py       # RXRE-001, 14 grupos
python3 tools/rxre/tests/test_rxre002.py    # contrato, 13 grupos
python3 tools/rxre/tests/test_fixtures.py   # regresión, 29 comprobaciones
```

Las tres en verde. El fixture usa **entradas reales** del corpus `linux-7.1.3` y
ata valores medidos, no solo forma: `D1=85.7`, `D2=85.7`, `D3=28.6`.

`D3` en 28.6 es una deficiencia real de la que el fixture se entera si alguien
la empeora.

## Mutaciones probadas

Nueve. Las que importan:

| mutación | resultado |
|---|---|
| `blocked` → `empty` (Intel) | detectada |
| `candidates` de la resolución → `[]` | detectada, tras 2 intentos |
| quitar el techo `min(pedido, 200)` | detectada, tras 2 intentos |
| objetivo sin extensión (`gfxhub_v1_0`) | detectada |
| fallback de `resolver()` elige la primera | detectada, tras 4 intentos |
| `provenance` pierde `D3` | detectada |
| `pct` a 0.0 en todo | detectada, tras 3 intentos |

La de `pct` merece nota: el normalizador leía `_raw_json` (el dato crudo) en
vez de la salida del handler, así que **mutar el handler no cambiaba nada**. Eso
hace que el camino probado y el camino usado sean distintos.

> un normalizador que relee el dato crudo ignora al que lo produce

## Estado

RXRE-002, Fases A–H completas. I (test de usabilidad por IA) es el siguiente.

### Ausentes, y medidos

- **Sin capability catalogue para scripts.** Se puede leer el registro de
  herramientas, pero no el de capacidades.
- **`relation path`** devuelve las aristas que tocan un nodo, no un camino A→B.
- **Sin `dwarf` ni `binary`.** El encargo los pide en la tanda 2; no hay
  adaptador.
- **Sin `--field`** en el pipeline de registro (el handler de RXRE-001 lo acepta;
  la composición no lo encamina).
- **`pm4` devuelve texto**, porque `pm4ops.py` imprime una tabla. Marcado como tal,
  no fingido.
- **Sin hypotheses, sin experiments, sin fixtures de runtime.** Fuera de alcance
  de esta fase por diseño: RXRE-002 no ejecuta nada destructivo.

### Nota sobre `tools_used`

En un pipeline, `tools_used` va vacío: se rellena por capacidad, no por etapa.
El script real de cada etapa está en `stages[].op` y en `provenance`.