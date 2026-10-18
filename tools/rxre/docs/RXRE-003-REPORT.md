# RXRE-003 — Informe

Estabilización de RXRE para que una IA pueda hacer RE sin conocer los scripts.

Medido el 2026-10-05/06 contra `linux-7.1.3`. Nada de esto es por diseño: es por
ejecución.

---

## 1. Baseline (§3)

Ejecutado **antes** de tocar nada.

```
rxre --help                                        rc=0
rxre capabilities                                  rc=0
machine query "quien escribe VM_CONTEXT0_CNTL"     rc=0
test_rxre.py        (14 grupos)                     rc=0
test_rxre002.py     (13 grupos)                     rc=0
test_fixtures.py    (29 comprobaciones)             rc=0
```

Baseline en verde. Se permitió agregar funcionalidad.

---

## 2. Contrato público congelado (§4, §5)

`tools/rxre/docs/RXRE_PUBLIC_CONTRACT.md`

Responde las nueve preguntas de §4. Cada campo con tipo, obligatoriedad,
productor, valores permitidos, condición de ausencia y de error.

**Superficie pública real**, medida:

| interfaz | para qué |
|---|---|
| `api/machine.py` (JSONL) | la que usa una IA |
| `rxre` (CLI) | la que usa una persona |

---

## 3. Prueba de usabilidad por IA (§6, §23)

`tools/rxre/tests/ai_usability_test.py`

La IA recibe **solo**: la interfaz pública, el objetivo de investigación, y el
catálogo que ella pide. **No** recibe nombres de scripts, ni de capacidades, ni
indicación de cuál usar.

Y no usa `capabilities.resolver()` para elegir — elegir **es** lo que se prueba.
Si usara la función interna, la prueba mediría que la función funciona contra sí
misma.

**Pregunta**: *«¿Quién escribe VM_CONTEXT0_CNTL y qué evidencia respalda cada
candidato?»*

**Log completo**: `/tmp/opencode/rxre_ai_test.jsonl` (10 pasos).

### Métricas (§22)

| métrica | antes | después |
|---|---|---|
| T1 pasos hasta primera operación válida | 3 | 3 |
| T2 pasos hasta primer resultado útil | 5 | 5 |
| T3 % operaciones interpretadas bien | 100 | 100 |
| **T4 % `next_actions` ejecutables** | **50** | **100** |
| T5 % provenance reconstruible | 100 | 100 |
| T6 operaciones repetidas | 0 | 0 |
| T7 errores de interpretación | 0 | 0 |
| **T8 pérdida de contexto tras handoff** | **100** | **0** |
| T9 % tareas sin conocer scripts | 100 | 100 |

**Antes** de T4/T8: la IA no conseguía elegir capacidad (recibía el catálogo
vacío) y la mitad de sus siguientes pasos eran callejones.

---

## 4. Fallos observados y clasificación (§7)

| # | fallo | clase | evidencia |
|---|---|---|---|
| F1 | 7 de 10 `next_actions` no eran invocables | **C** | `{"op":"provenance"}` → `error: operacion desconocida` |
| F2 | catálogo de intenciones solo en `ops`; `capabilities` devolvía `[]` | **B** | la IA no tenía nada que elegir |
| F3 | `target_permitido` era lista **negra** | **I** | `i915`, `0000:03:00.0`, `unknown` pasaban |
| F4 | `chain` de `explain` son nombres, no valores | **E** | `['result','operation','tool',...]` |
| F5 | sin `plan`, sin `session`, sin `handoff` | **C** | T8 = 100 |
| F6 | `result_id` **colisionaba**: 36 resultados → 9 ids | **E** | muchos usos comparten texto |
| F7 | catálogo decía `resolved_by` pero no **cómo invocarlo** | **B** | `{"op":"register"}` no existe |
| F8 | normalizador leía `_raw_json`; mutar el handler no cambiaba nada | **D** | el camino probado ≠ el usado |

Clave (§7): **F8 esrxre-002 otra vez**, en otra guise. Ya se detectó y se reparó
para `provenance`; el mismo fallo quedaba en `search`.

---

## 5. Reparaciones (§7 PASO 7)

Solo los bloqueos reales, uno por iteración.

| # | reparación | qué cierra |
|---|---|---|
| R1 | `next_actions` con `op` + `args` reales, o `available:false` con motivo | F1 · T4 50→100 |
| R2 | `capabilities` expone el catálogo de intenciones | F2 · la IA elige capacidad |
| R3 | `target_permitido` → lista **blanca** | F3 |
| R4 | `explain` acepta `operation_id`; `store.explicar_operacion` | F4, R1 |
| R5 | `op: case` — RE_CASE por referencias, sin tabla nueva | F5 · T8 100→0 |
| R6 | `result_id` incluye la ubicación | F6 · 36 ids, 36 distintos |
| R7 | campo `invocable` en el catálogo | F7 |
| R8 | el handler aplica su decisión al canal que lee el normalizador | F8 |

**R1 tuvo que repetirse.** La primera reparación proponía
`explain_operation` pasando `operation_id` a un `explain` que solo aceptaba
`result_id`. **La acción propuesta era ella misma un callejón.** Se detectó al
*ejecutar* las acciones, no al mirarlas — y por eso el vector de RXRE-003 las
ejecuta.

---

## 6. Mutaciones contractuales (§20)

`tools/rxre/tests/test_mutations003.py`

**12 mutaciones, 12 detectadas.** Ninguna sobrevive.

| mutación | detectada por |
|---|---|
| `blocked`→`empty` en el gate del target | test_rxre002 |
| quitar la `limitation` obligatoria de `empty` | test_rxre |
| dejar `next_actions` vacío | test_rxre003 |
| proponer una acción sin `op` | test_rxre003 |
| alterar el `result_id` | test_rxre003 |
| dejar `provenance` vacía | test_rxre003 |
| resolver a una capacidad inexistente | test_rxre002 |
| borrar las aristas | test_rxre003 |
| dejar `chain` vacía en `explain` | test_rxre003 |
| el normalizador deja de mirar al productor | test_rxre003 |
| **el handler deja de devolver resultados** | test_fixtures |
| `target_permitido` → lista negra | test_rxre003 |

### Lo que las mutaciones encontraron

**Seis sobrevivieron en la primera pasada**, y cada una era de un tipo distinto:

- **Tres eran mutadores rotos**, no fallos del runtime. Uno usaba `[] or f()`,
  que devuelve `f()`. Otro apuntaba a un texto que ya no existía. Un tercero
  declaraba la suite equivocada —daría «SOBREVIVE» sin medir nada.

  > un mutador que no aplica no es un mutador que sobrevive

- **Tres eran huecos de cobertura reales.** Y uno de ellos dejó un bug:
  escribir la comprobación *«los `result_id` son únicos»* falló con
  **36 resultados y 9 ids distintos**. `result_id` se derivaba de
  (tipo, valor, herramienta), y muchos usos de un registro comparten el mismo
  texto. Con `INSERT OR REPLACE`, 36 filas se convertían en 9 **sin que nada lo
  notara**.

> un identificador que colisiona no identifica

Y la última, la que más costó: **el fixture no notaba que el handler devolviera
cero resultados**. Es F8 otra vez. El normalizador leía `_raw_json` mientras el
handler recortaba `hits`; mutar el recorte no cambiaba la salida. Arreglar la
cobertura Consistió en **arreglar el código**, que es el orden correcto.

---

## 7. Seguridad (§17)

Lista **blanca**, no negra. Comprobado:

| target | resultado |
|---|---|
| `0000:01:00.0` | permitido |
| `01:00.0`, `rx550` | permitido |
| `0000:00:02.0` | **blocked** |
| `i915` | **blocked** |
| `0000:03:00.0` | **blocked** |
| `unknown` | **blocked** |
| vacío | **blocked** |

103 comprobaciones en `test_rxre003.py`, incluidas las cuatro clases de target
de §17.

**No se tocó hardware.** Ni lectura, ni escritura. Ninguna operación de esta
iteración abre `/dev/dri` ni escribe MMIO.

---

## 8. Persistencia y handoff (§9, §10, §12)

Base tras la sesión: **819 operaciones, 93 resultados, 65 aristas, 0 ids
duplicados.**

`op: case` es una **vista sobre `operations`**, con `case_id` derivado de
(target, question). No hay tabla nueva ni copia de evidencia (§10).

Probado: IA B recibe **93 `result_id`** y explica uno **sin reejecutar la
consulta**. El caso **no lleva copias** — solo ids y localizaciones, verificado
por vector.

---

## 9. Artefactos (§27)

| artefacto | dónde |
|---|---|
| Contrato público | `docs/RXRE_PUBLIC_CONTRACT.md` |
| Quickstart para IA | `docs/AI_QUICKSTART.md` |
| RE_CASE de ejemplo | `docs/EJEMPLO_RE_CASE.json` |
| Transcripción de la IA | `/tmp/opencode/rxre_ai_test.jsonl` |
| Prueba de usabilidad | `tests/ai_usability_test.py` |
| Vectores de estabilidad | `tests/test_rxre003.py` (103) |
| Mutaciones | `tests/test_mutations003.py` (12) |

---

## 10. Estado final

```
test_rxre.py        14 grupos      OK
test_rxre002.py     13 grupos      OK
test_fixtures.py    29 checks      OK
test_rxre003.py     103 checks     OK
test_mutations003   12/12          OK
```

---

## 11. Veredicto (§21, §28)

```text
AUTONOMOUS_USE = PARTIAL
```

**Lo que queda `PROVEN`:**

- Una IA descubre, elige, ejecuta, interpreta, explica y continúa **sin conocer
  ningún script interno**. T9 = 100, y la prueba prohíbe explícitamente los nombres.
- `empty` / `blocked` / `error` permanecen distinguibles, y **no** se confunde el uno
  con el otro. Con 12 mutaciones que lo rompen, 12 detectadas.
- La provenance es reconstruible por las dos vías: `result_id` y
  `operation_id`.
- El Intel sigue bloqueado, y ahora un target **desconocido** también.
- Toda operación ejecutada es reproducible: mismo input → mismo `result_id`.

**Lo que NO alcanza `PROVEN`:**

- **No es `PROVEN` porque la prueba la ejecuta un agente con una regla de
  elección mínima (conteo de palabras)**, no un modelo de lenguaje real. Eso
  demuestra que el contrato es *suficiente*, no que sea *óptimo* para cualquier
  IA.
- **T2 = 5 pasos.** Una IA que no hace la extracción de objetivo necesita pasar
  `inputs.target` a mano.
- **El `_id` de un resultado es determinista pero no un contenido hash
  verificable.** No hay `result_id` → artefacto reproducible fuera de la base.
- **La arista WRITES sigue siendo candidata por patrón.** 24 candidatos, 0
  escrituras demostradas. Eso está escrito, pero es la limitación más
  grande que queda y **no se ha cerrado**.

---

## 12. La siguiente frontera

**No es agregar capacidades.** Es la que la prueba dejó abierta:

1. **`autonomous_use` con un LLM real**, no con un agente de conteo de
   palabras. La regla de elegir capacidad es el punto donde una IA real
   fallaría distinto, y no está medido.
2. **`plan` sin ejecución** (§15). hoy la IA ve `capability_resolution` *después*
   de ejecutar; el encargo pide ver el camino *antes*.
3. **Cerrar WRITES.** 24 candidatos por patrón. Ninguna herramienta en `tools/`
   clasifica lectura/escritura. Es una **capacidad ausente medida**, y §26 dice:
   solo se agrega si la prueba demuestra que bloquea la investigación.
4. **`result_id` verificable fuera de la base** — el hash del artefacto, no del
   contenido interpretado.

La 1 es la que decide si `AUTONOMOUS_USE` pasa de `PARTIAL` a `PROVEN`. Y no se
puede responder sin ejecutarla.

---

## 13. Una nota

Las tres iteraciones consecutivas de RXRE comparten la misma forma:

```text
escribir un mecanismo correcto  →  mutarlo  →  descubrir que no lo era
```

RXRE-001: un criterio que no podía pasar.
RXRE-002: un normalizador que ignoraba al productor.
RXRE-003: un verificador de target que era una lista negra.

En los tres, el defecto **no** lo encontró leyendo el código. Lo encontró una
mutación deliberada, y en dos casos el defecto estaba en el **mismo sitio** que
el trabajo anterior.

> un mecanismo que no ha sido mutado no está verificado;
> está probado

Eso no es una crítica del método. Es el método.