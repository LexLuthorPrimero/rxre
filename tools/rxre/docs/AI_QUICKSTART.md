# AI_QUICKSTART

Todo lo que necesitas para usar RXRE. Nada de esto requiere saber qué hay
dentro.

```bash
RXRE=tools/rxre/api/machine.py
```

Se habla por **JSONL**: una petición JSON por línea, una respuesta por línea.

---

## 1. ¿Qué puedes hacer?

```bash
echo '{"op":"ops"}' | python3 $RXRE
```

Trae `capabilities[]`: 11 intenciones con `question`, `requires`,
`limitations`, `max_hits` e **`invocable`** — el request literal para llamarla.

`results[]` en esa misma respuesta son **scripts**; `capabilities[]` son
**intenciones**. No son el mismo catálogo.

---

## 2. Haz una pregunta

```bash
echo '{"op":"query","target":"0000:01:00.0",
       "question":"quien escribe VM_CONTEXT0_CNTL"}' | python3 $RXRE
```

`question` va en prosa. El objetivo se extrae solo, o se pasa explícito:

```json
{"op":"query","target":"0000:01:00.0","capability":"register.writers",
 "inputs":{"target":"VM_CONTEXT0_CNTL"}}
```

---

## 3. Lee el estado. Es lo que decide todo

| `status` | rc | qué pasó | qué **no** significa |
|---|---|---|---|
| `ok` | 0 | produjo resultados | que un resultado sea un hecho |
| `empty` | 0 | **corrió y no encontró** | **que no exista** |
| `blocked` | 2 | **no se ejecutó** | que no haya nada |
| `error` | 1 | la herramienta falló | — |

`empty` y `blocked` comparten rc=0. **`status` es la verdad, no el código.**

- `empty` sale **siempre** con `limitations` diciendo por qué, y **nunca** propone
  concluir que no existe.
- `blocked` significa que no se ejecutó. Sobre el hardware no se concluye nada.

---

## 4. Sigue `next_actions`

Cada acción lleva `op` y `args` **reales**. Se ejecutan tal cual:

```json
"next_actions": [
  {"action":"explain","available":true,"op":"explain",
   "args":{"result_id":"res_register_124ada0de01e"}}
]
```

```bash
echo '{"op":"explain","result_id":"res_register_124ada0de01e"}' | python3 $RXRE
```

Si `available` es `false`, hay un motivo. **No hay pasos a ciegas.**

Cada acción trae `success` y `stop`: cuándo funcionó y cuándo la vía está agotada.

---

## 5. De dónde salió

```bash
echo '{"op":"explain","result_id":"..."}'     | python3 $RXRE   # un resultado
echo '{"op":"explain","operation_id":"op_..."}' | python3 $RXRE   # toda la operación
```

Por `operation_id` salen **todas** las etapas del pipeline y todos sus
resultados. Sin esto, una operación de dos etapas no se puede explicar entera.

Un `result_id` que no está en la base → `empty` diciendo que **no está
registrado**, no que no exista.

---

## 6. Relaciones

```bash
echo '{"op":"relation","clase":"writers","nodo":"drivers/.../gfxhub_v1_0.c:223"}' \
  | python3 $RXRE
```

`writers` · `readers` · `references` · `path`.

Las aristas de escritura nacen **`observed`**, con su limitación escrita:

> un uso que casa con `REG_SET_FIELD` es un **candidato** a escritor;
> demostrar que escribe exige ejecutar la función

No hay herramienta que clasifique lectura/escritura. La derivación es por
**patrón de texto**, y se dice.

---

## 7. Handoff

```bash
echo '{"op":"case","target":"0000:01:00.0"}' | python3 $RXRE
```

Devuelve todo lo registrado para ese target: operaciones, resultados y aristas
**por referencia** (`operation_id`, `result_id`), no copias.

Cierra el contexto, entrega el `case_id`, y otra IA sigue con `explain` sin
volver a ejecutar.

---

## 8. Alcance

`target` es lista **blanca**: `0000:01:00.0`, `01:00.0` y `rx550`.

Cualquier otra cosa —incluida la Intel `0000:00:02.0`, `i915`, `unknown` o
vacío— devuelve **`blocked`** antes de ejecutar. Un target que no se reconoce no
se asume que sea la RX550.

---

## 9. Lo que no existe

| falta | qué hacer en su lugar |
|---|---|
| `op: plan` | inspecciona `capability_resolution` de la respuesta |
| `--field` en composición | usa la CLI: `tools/rxre/rxre register X --field F` |
| `dwarf`, `binary` | no hay adaptador |
| lectura/escritura de registros | `relation` da candidatos, no hechos |

---

## 10. Errores que verás

| mensaje | qué hacer |
|---|---|
| `no se pudo extraer el objetivo` | pasa `inputs.target` |
| `ninguna intencion casa con el enunciado` | mira `capability_resolution.options` y elige `capability` |
| `objetivo fuera del alcance` | el target no es la RX550 |
| `no hay ninguna fila con ese result_id` | no está **registrado**, no inexistente |

Ninguno de esos es un fallo de la herramienta: son respuestas.