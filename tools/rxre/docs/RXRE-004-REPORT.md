# RXRE-004 — INFORME DE CIERRE

> Backends de reverse engineering / decompilación.
> Fecha de medición: **2026-10-06**. Todo lo de aquí procede de un producer
> ejecutado o de un fichero cuyo hash se ha comparado. Nada se infiere de un
> nombre de fichero.

---

## 0. Resumen ejecutivo

RXRE-004 cierra **B0 → B8**. La propiedad central de §26 está **demostrada**:

```
IA → RXRE contract → capability → plan → backend adapter → artifact
   → provenance → explain → next action
```

sin que la IA tenga que nombrar `rizin`, `radare2`, `angr` ni `rz-ghidra`. Se
comprueba como **black-box por JSONL**, no importando el dispatcher.

**`AUTONOMOUS_USE` sigue en `PARTIAL`.** No se ha ejecutado todavía el test con
un LLM real (§21); lo medido aquí es la *superficie*, no el *uso*.

---

## 1. Estado por etapa

| etapa | criterio de aceptación | resultado |
|---|---|---|
| **B0** | 21/21 detectadas, 0 sobreviven, 0 inválidas | **CERRADO** — 31/31 tras B2/B3/B4/B7 |
| **B1** | fixture pequeño, reproducible, con hash | **CERRADO** — 4728 B, `a183f60d…`, byte-idéntico al reconstruir |
| **B2** | arquitectura no soportada ≠ `empty`; `PROVENANCE_INCOMPLETE`; colisión | **CERRADO** |
| **B3** | `target` real, `explain` con 13 eslabones | **CERRADO** |
| **B4** | `binary.inspect` alcanzable por una IA | **CERRADO** — 120 vectores |
| **B5** | clasificación de dataflow respaldada por producer | **CERRADO** — etiqueta igual, razón corregida |
| **B6** | plan sin ejecución | **CERRADO** — 6 pasos, 6 verificables, 1 ejecutable |
| **B7** | contrato congelado + decisión machine-readable | **CERRADO** — `decision.json`, mutado y restaurado |
| **B8** | findings registrados + informe | **CERRADO** — `1568`–`1573` |

### Suites

```
test_rxre           rc=0   14 grupos      (RXRE-001)
test_rxre002        rc=0   13 grupos      (RXRE-002)
test_fixtures       rc=0   29 checks
test_rxre003        rc=0   111 checks     (RXRE-003)
test_backends004    rc=0   138 checks     (nuevo)
test_fixture004     rc=0   33 checks      (nuevo, B1)
test_dispatch004    rc=0   120 checks     (nuevo, B4–B7)
test_mutations003   rc=0   31/31 DETECTED, 0 SOBREVIVE, 0 INVALID
```

---

## 2. Lo que cambió de estado

### 2.1 `binary.inspect` — `NOT_DETERMINED` → **PROVEN**

Ejecutable de punta a punta por la superficie pública, con provenance de 13
eslabones reconstruible por `explain`. El único ciclo completo del proyecto en
reverse engineering.

### 2.2 `binary.dataflow` — etiqueta igual, **razón corregida**

La etiqueta `PARTIAL` en rizin resultó correcta, pero **por otro motivo**:

| | antes | después (medido) |
|---|---|---|
| razón | «`pdj` es desensamblado, no dataflow» | «el producer es `afvxj` y su JSON está mal formado» |

La razón anterior era **falsa**: `pdj` nunca se usó como data-flow; atribuirle un
límite de formato inventaba un defecto en un producer que no era el. Y en
radare2 la capacidad pasó de `NOT_DETERMINED` a `AVAILABLE` (su `afvxj` emite
JSON válido).

> una razón correcta importa tanto como una etiqueta correcta: son cosas
> distintas y se pueden equivocar por separado

### 2.3 Los estados del backend: 4 → **6**

`unsupported` (rc=4) e `invalid_input` (rc=5) son necesarios y no decorativos.
Ver `1571`.

---

## 3. PROVEN

1. La matriz de backends, con producer ejecutado por capacidad (`1568`).
2. `import angr` **no importa angr** dentro del árbol (`1573`).
3. `unsupported` como estado propio: `rc=0` + contenido + sin arquitectura (`1571`).
4. Determinismo ≠ unicidad (`1570`).
5. `exit 0` con el ejecutable equivocado produce el banner de rizin (`1569`).
6. El data-flow **no puede cerrar la frontera WRITES** (`1572`).
7. `binary.inspect` alcanzable por una IA sin nombrar el backend.
8. La allow-list se demuestra por **lo que rechaza**: 6 rechazos, 6 motivos.
9. El fixture es reproducible byte a byte.
10. La decisión `PRIMARY=rizin` es consumida, no decorativa (mutación detectada).

---

## 4. PARTIAL

- **`AUTONOMOUS_USE = PARTIAL`.** La superficie está medida; el uso por un LLM
  real no (§21). **No se sube a `PROVEN`.**
- **5 de 6 pasos del plan hacia `binary.decompile` son verificables pero no
  ejecutables.** La capacidad existe en el registry (`AVAILABLE`) pero no tiene
  adapter. Verificable ≠ ejecutable, y el plan dice las dos cosas.
- **`binary.cfg` y `binary.callgraph` en rizin** son `PARTIAL`: existen como
  producer y emiten ASCII. Radare2 los da en JSON; por eso es `SECONDARY`.

---

## 5. NOT_DETERMINED

- **`angr`**: `import angr` funciona dentro del árbol (namespace package,
  `__file__ is None`); fuera, `ModuleNotFoundError`. **No se comprobó que angr
  no sirva: se comprobó que no se puede verificar aquí.**
- **`rz-ghidra`**: requiere Ghidra + CMake + toolchain Java. No se instaló.
- **`binary.decompile`**: `UNAVAILABLE` en los dos backends medidos, `ND` en los
  no verificables. **No se declara ninguna capacidad de decompilación.**

---

## 6. BLOCKED / DEFERRED

| | estado | motivo |
|---|---|---|
| `binary.functions`, `disassemble`, `cfg`, `dataflow` como adaptador | DEFERRED | medidos y disponibles; falta adapter. No bloqueados |
| compilar rizin 0.10-dev | **DEFERRED** | ninguna pregunta concreta lo exige (§20) |
| `target:0000:00:02.0` | BLOCKED | la iGPU no aparece en el bus PCI; requiere leer la BIOS, que requiere reinicio y autorización del propietario |

---

## 7. Contradicciones que se han resuelto

1. **«rizin no calcula xrefs»** — FALSO. Era `aa` en vez de `aaa`.
2. **`binary.dataflow` en rizin** — etiqueta correcta, razón falsa. Corregida.
3. **Los recuentos de la prosa (11 / 7)** — viejos frente al registro real
   (14 / 8). Los detectó el vector que compara `primary` contra el recuento.
4. **`COLISION` como fallo** — no lo es: `result_id` es determinista, así que
   la evidencia ya existe y `explain` la alcanza.

---

## 8. Lo que NO se pudo hacer

- **No se ejecutó el test con un LLM real** (§21). Es lo único que separa
  `PARTIAL` de `PROVEN` para `AUTONOMOUS_USE`, y requiere un agente externo.
- **No se verificó angr ni rz-ghidra.** Sin instalación global (§20). Por eso
  `binary.decompile` sigue sin declararse.
- **No se compiló rizin 0.10-dev.** El repo es `v0.10.0-dev`; el binario que
  corre es 0.7.4. Es una discrepancia declarada, no oculta
  (`tool_version` ≠ `repository_commit`).
- **No se cerró la frontera WRITES.** El hallazgo `1572` explica por qué el
  data-flow no sirve para eso.

---

## 9. Mutaciones: 31 y por qué importan

Cada mutación es un mecanismo al que se le rompe a propósito y se mide si un
vector lo detecta. Las que importan:

| mutación | por qué importa |
|---|---|
| `el adapter usa el ejecutable equivocado` | `exit 0` ≠ resultado válido |
| `unsupported se colapsa a empty` | la conversión `empty → absent` |
| `el result_id se deriva solo del valor` | F6: un id que colisiona no identifica |
| `la version se declara sin verificar` | apariencia de éxito sin contenido |
| `persistir firma la operacion con un target PCI` | evidencia de hardware que no ocurrió |
| `explain deja de devolver la cadena del backend` | la cadena se rompe en el último eslabón |
| `la allow-list acepta cualquier capability` | una allow-list que acepta todo no es una allow-list |
| `la allow-list deja de preguntar al registry` | copiar en vez de preguntar |
| `PRIMARY pasa de rizin a radare2` | §15: la decisión se consume |
| `una arquitectura sin identificar se declara soportada` | `null` no es «no tiene» |

### 9.1 El fallo de arnés que produjo 3 «supervividas» falsas

Las mutaciones de la allow-list **sí se aplicaban**, pero el arnés les
asignaba la suite equivocada (`test_backends004` en vez de
`test_dispatch004`). Sobrevivieron por eso.

> una mutación contra la suite equivocada no es una supervivencia: es una
> medición que no se hizo

La lista pasó de 3-tuplas a 4-tuplas, con la suite por mutación.

---

## 10. La clase de defecto que se repite

Cuatro iteraciones, un mismo patrón: **un mecanismo calculado y nunca
comparado.**

- RXRE-001: un criterio que no podía pasar.
- RXRE-002: un normalizador que leía `raw_json` e ignoraba al producer.
- RXRE-003: `target_permitido` implementado como lista negra.
- RXRE-004: `exit 0` con el banner; vectores que pasaban por la razón
  equivocada; mutaciones contra la suite equivocada.

Ninguno se encontró leyendo el código. Todos los encontró una **mutación** o
un **productor real**.

```
mecanismo implementado  ≠  mecanismo verificado
test verde             ≠  correctness
backend correcto       ≠  semántica correcta
```

---

## 11. Deliverables

```text
tools/rxre/docs/RXRE-004-BACKEND-MATRIX.md     la matriz medida
tools/rxre/docs/RXRE-004-BACKEND-CONTRACT.md  el contrato congelado (§14, §17)
tools/rxre/docs/RXRE-004-REPORT.md            este informe
tools/rxre/backends/contract.py                los 6 estados + 11 peldaños
tools/rxre/backends/registry.py                capacidades medidas + notas
tools/rxre/backends/decision.json              la decisión §18, machine-readable
tools/rxre/backends/dispatch.py                la allow-list + el plan
tools/rxre/backends/adapters/rz_inspect.py     la vertical binary.inspect
tools/rxre/fixtures/bin/{rxre_min.c,.ld,.elf,MANIFEST.json,README.md}
tools/rxre/tests/test_backends004.py           138 vectores
tools/rxre/tests/test_fixture004.py             33 vectores
tools/rxre/tests/test_dispatch004.py           120 vectores
```

Findings: **`1568` `1569` `1570` `1571` `1572` `1573`**, todos con fichero
detrás de su reserva (verificado con `nextnum.py --auditar`).

---

## 12. El siguiente paso

**Un test de usabilidad con un LLM real** (§21), recibiendo **sólo**
`RXRE_PUBLIC_CONTRACT.md` y una pregunta. Sin nombres de scripts, sin nombres de
backends, sin arquitectura interna.

Mide:

```
discover → choose → plan → execute → interpret → explain → next action
```

y es lo único que puede mover `AUTONOMOUS_USE` de `PARTIAL` a `PROVEN`.

Dos candidatas naturales después, por lo que desbloquean:

1. **`binary.functions` como adaptador.** Es la segunda vertical natural: el
   fixture ya tiene 4 funciones con ground truth conocido, y `aflj` las
   encuentra. Discrimina: el backend acierta el número de funciones que el
   fuente declara?
2. **El data-flow de las 24 aristas WRITES.** `1572` dice que el data-flow
   **no** sirve. La vía es la que el proyecto ya tiene: clasificar
   REG_SET_FIELD / REG_RMW / WREG con un productor que diga *qué* escribe, no
   *qué parece una escritura*.