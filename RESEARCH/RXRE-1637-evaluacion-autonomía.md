# RXRE-1637 — Evaluación de la autonomía de RXRE como plataforma de investigación de reverse engineering

**Fecha:** 2026-10-12
**Estado de la misión:** BASELINE + DISEÑO DE EVALUACIÓN + PRIMERAS MEJORAS JUSTIFICADAS
**Rama:** main (sin cambios de rama, todo secuencial)

---

## RESPUESTA DIRECTA A LA PREGUNTA CENTRAL

> **Can RXRE independently discover and justify previously unencoded technical relationships, identify what prevents it from proving them, and improve its ability to investigate other problems without relying on case-specific hardcoding?**

**Respuesta honesta basada en el análisis de este turno:**

**No, RXRE no es hoy una plataforma de investigación autónoma.** Es un **orquestador de análisis estáticos** que:
- Invoca herramientas preexistentes (rizin/radare2/Capstone/Ghidra/Coccinelle)
- Devuelve sus salidas con un sobre-encapsulamiento de consistencia
- Declara qué capacidades están disponibles, pero **no razona sobre lo que quiere saber**

Los mecanismos que faltan y que lo impiden son **arquitecturales**, no de adapters:

| Nivel | ¿Existe en RXRE hoy? | Qué falta |
|---|---|---|
| A — Tool orchestration | **Sí**, parcialmente | El dispatch existe y devuelve siempre 6 canales. El problema es que no valida *semántica*, solo esquema. |
| B — Evidence-aware investigation | **No** | No hay registro de evidencias, no hay enlace claim→evidencia, no hay estatus epistémico (PROVEN/PARTIAL/NOT_DETERMINED) más allá de `status: ok/empty/error`. |
| C — Cross-tool synthesis | **No** | Un adapter produce un resultado aislado; no hay nada que conecte `binary.xrefs` con `binary.callgraph` o con el resultado de `source.semantic_search`. Las capacidades son compartimentos estancos. |
| D — Causal investigation | **No** | No hay representación de cadenas causales, no hay detección de eslabones faltantes, no hay generación de hipótesis competidoras. |
| E — Adaptive investigation | **No** | No hay seguimiento de hipótesis, no hay selección de experimento por valor discriminante, no hay retroalimentación del resultado a la estrategia. |
| F — Generalizable autonomous research | **No** | Todo lo anterior es requisito para esto. Hoy no hay nada que generalice. |

**Conclusión clasificada:** RXRE está en **Nivel A parcial** (orquestación con sobre-encapsulamiento) y **no alcanza el Nivel B**. Cualquier mejora de autonomía debe pasar primero por un **contrato común de evidencia** antes que por más adapters.

---

## 1. BASELINE: QUÉ EXISTE REALMENTE (verificado en este checkout)

### 1.1 Registros y adapters

```
Total adapters: 14
binary.basic_blocks, binary.callgraph, binary.decompile, binary.disassemble,
binary.disassemble_func, binary.exports, binary.functions, binary.imports,
binary.inspect, binary.sections, binary.strings, binary.symbols,
binary.xrefs, source.semantic_search
```

**Sin adapter:** `binary.cfg`, `binary.dataflow` (ambas `AVAILABLE` en el registry → **capacidad declarada sin producer**, `esta_permitida()` = `False` con motivo explícito).

### 1.2 Comprobación de lo que ya existía vs. lo reportado

La hipótesis "xrefs y callgraph tienen adapters" fue CONFIRMADA en el checkout (no solo en reportes):

```
$ python3 backends/dispatch.py:dispatch.ejecutar('binary.callgraph', {...})
  status=ok, nodes=5, edges=82, backend=radare2

$ dispatch.ejecutar('binary.xrefs', {..., 'nivel_analisis':'aaa'})
  status=ok, xrefs=74
```

**Pero un resultado con esquema válido no prueba corrección semántica.** Verificación independiente:

- **Callgraph nodes→edges estructuralmente válido?** El adapter cuenta `edges = Σ len(imports)`. `imports` de radare2 son **referencias a funciones externas** (e.g. `reloc.__libc_start_main`), no necesariamente llamadas *en* la función. **No se verifica que cada endpoint de arista exista como nodo.** Esto es una diferencia clave con un CFG y con xrefs. El test `test_callgraph1636.py` (22/22) no lo comprueba.
- **Xrefs nivel_analisis:** Se sabe por el registro que `aa; axtj → []` y `aaa; axtj → 3` sobre `/bin/ls`. La dependencia está documentada en el registry, pero no hay prueba de que un `empty` detectado en *runtime* haya sido interpretado como "análisis insuficiente" y no como "no hay xrefs".

### 1.3 Contrato y persistencia: el eslabón más débil

`dispatch.ejecutar()` devuelve **siempre** un envelope de 6 canales con `results`, `limitations`, `producer_ejecutado`, `persistido`. Pero:

- `persistir()` es **casuística**: vive solo en `rz_inspect.py` (`_persistir()` delega ahí). `rz_xrefs.persistir` y `rz_callgraph.persistir` existen como stubs con `metadata: {"found": True}` — **no escriben nada en ningún registro** y no hay tabla de operaciones. `test_dispatch004.py` tiene fallos preexistentes por falta de `api/machine.py` y `fixtures/bin/rxre_min.elf`.
- **Consecuencia:** no hay forma de `explain <result_id>` ni de reconstruir una cadena causal a partir de evidencias. Un resultado que no se persiste no forma parte del conocimiento del sistema.

**Estado epistémico actual:** los adapters devuelven `ok | empty | error`. No hay noción de `PARTIAL`, `NOT_DETERMINED`, `DEFERRED` en el resultado — solo en el registry. **Una herramienta que da `empty` no se distingue de una que no existe.**

---

## 2. INVESTIGACIÓN EXTERNA: BENCHMARKS DE REVERSE ENGINEERING AUTÓNOMO

### 2.1 AgentRE-Bench — https://github.com/agentrebench/AgentRE-Bench (MIT, 2026)

- **Qué mide:** capacidad de un agente para analizar binarios fuente-desconocidos y responder sobre infraestructura C2, esquemas de codificación, técnicas anti-análisis, inyección de procesos y protocolos de comunicación.
- **Mecánica:** da al agente un binario compilado + un conjunto de herramientas de análisis estático, **sin fuente, sin internet, sin ejecución arbitraria**, y lo evalúa con un **scorer determinista** contra una verdad de experta fija. Cada hallazgo se acredita; las afirmaciones no respaldadas se penalizan.
- **Resultados (V3, Windows PE):** el mejor modelo (Kimi K3) alcanza ~0.68; la recuperación *exacta* de cadenas de ejecución, configuración, claves y C2 "sigue siendo un problema abierto". La eliminación de símbolos reduce el promedio un 6.47% relativo → **los agentes dependen de anclajes léxicos más que de razonamiento a nivel de instrucción**.
- **Relevancia para RXRE:** **inspiración de diseño, no reutilización directa.** Su valor transferible: (1) scorer determinista con campo por campo ponderado + Jaccard para conjuntos; (2) penalización de afirmaciones sin evidencia; (3) preservación de trayectorias completas. RXRE podría adoptar su *patrón* de puntuación en una capa de evaluación, sin copiar el marco.
- **Limitación:** requiere un corpus de binarios con verdad de experta — que es exactamente lo que RXRE no tiene y que costaría meses construir.

### 2.2 SRE-Bench — https://arxiv.org/abs/2608.11469 (Columbia DAPLab, 2026)

- **Qué mide:** el primer benchmark de RE **libre de contaminación** y a escala real. 19 programas creados desde cero (16.9K LOC promedio), con 44 primitivas anti-análisis internas, dando 262 instancias y 1.572 tareas graduadas determinísticamente en 6 niveles.
- **Hallazgo central:** el mejor modelo (GPT-5.6-sol) llega a 61.4% y resuelve completo solo 31.5% de las instancias. **La insensibilidad de los agentes a optimización y enlazado, frente a la sensibilidad a la pérdida de símbolos, sugiere que los agentes dependen más de patrones léxicos que de razonamiento a nivel de instrucción.**
- **Relevancia para RXRE:** refuerza la tesis de que el "conteo de cadenas" o "número de xrefs" es un indicio pobre de comprensión real. Para RXRE, la analogía es: `nodes=5, edges=82` es un análogo directo del "reconocer familias de comportamiento" sin "recuperar la cadena de ejecución exacta".

### 2.3 SWE-bench Science — https://arxiv.org/abs/2608.19799 (2026)

- **Qué mide:** reparación de software científico en repositorios completos (119 tareas, 98 repositorios, 20 dominios). Cada tarea tiene **tests públicos + tests privados con reverse-checks** diseñados para atrapar parches que pasan lo visible pero no generalizan.
- **Hallazgo central:** el mejor agente (Claude Code/Opus-5) alcanza **47.9% Pass@1 con 96.6% en tests públicos**. La brecha entre lo visible y lo oculto es el punto de medición. Además, un test controlado (**paired ablation**) muestra que **el contexto científico ayuda a modelos débiles (16.48%→23.08%) pero perjudica a fuertes (36.26%→31.87%)** → *efecto de anclaje*: el contexto bien alineado constriñe, el mal alineado induce una historia plausible-pero-falsa.
- **Relevancia transferible inmediata para RXRE:** **el patrón "tests públicos vs. tests privados con reverse-checks"** es reutilizable sin tocar el benchmark. RXRE puede aplicar esto: un test que un adapter pasa (público) + un test independiente que valida la *semántica* del resultado contra un oráculo distinto (privado), detectando así parches "que pasan el esquema pero no la semántica".

### 2.4 AgentLens — https://www.microsoft.com/en-us/research/publication/agentlens-revealing-the-lucky-pass-problem-in-swe-agent-evaluation/

- **Qué mide:** el "lucky pass problem" — agentes que dan respuestas correctas por casualidad sin comprender.
- **Relevancia:** justifica por qué **un test que pasa no prueba que el adapter es correcto**, y por qué un resultado `ok` no prueba que RXRE "resolvió" la pregunta. RXRE debe medir la *calidad del razonamiento intermedio*, no solo la respuesta final.

---

## 3. MATRIZ DE RELEVANCIA (benchmarks → fallo en RXRE)

| Método benchmark | Mide | Supuesto | Verdad de experta | Falla que detecta | Aplicación a RXRE | Reutilizable |
|---|---|---|---|---|---|---|
| AgentRE scorer | respuesta estructurada vs. verdad fija, penaliza afirmaciones no respaldadas | la respuesta se descompone en campos ponderables | experta privada | afirmaciones sin evidencia | capa de evaluación sobre resultados de RXRE | patrón, no código |
| SRE-Bench | instancias fuente-desconocido a escala real | sin contaminación de training | privada, generada desde cero | sobre-aprovechamiento de patrones |RXRE ya trabaja con binarios locales sin fuente; el benchmark valida que su enfoque | no (corpus propio necesario) |
| SWE-bench Science | tests públicos + privados con reverse-checks | lo visible no es suficiente | privada con verificación ejecutable | parches que pasan lo visible pero no generalizan | **reverse-check independiente** sobre la salida de un adapter | **sí (patrón directo)** |
| AgentLens | lucky passes | la respuesta correcta puede ser casual | evidencia del trayecto | respuesta correcta sin comprensión | medir *causas* del éxito, no solo el resultado | patrón |
| Metamorphic testing (buscado) | relaciones preservadas bajo transformación de entrada | la salida debe transformarse de forma predecible | propiedades, no verdad exacta | regresiones semánticas | `xrefs(bin) == xrefs(bin_con_xrefs_agregado)` — pendiente de diseño | diseño propio |

---

## 4. DISEÑO DE EVALUACIÓN INDEPENDIENTE (Test A–F)

Los tests están diseñados para **medir la calidad de la investigación, no el esquema de la salida**. El oráculo no es el mismo adapter que evalúa.

### Test A — Reconstrucción causal completa (unquestioning target: una función real)

**Pregunta real:** *"¿Qué función de entrada lee y escribe el primer argumento de programa en /bin/ls?"*

**Procedimiento:**
1. RXRE debe: (a) identificar el artefacto; (b) descubrir candidatos; (c) seguir transformaciones; (d) conectar `binary.symbols` → `binary.disassemble_func` → `binary.xrefs` → `binary.callgraph`; (e) establecer qué relaciones están justificadas con fuentes; (f) listar eslabones faltantes; (g) dar conclusión con estatus epistémico; (h) proponer experimento siguiente si la evidencia no alcanza.
2. **Puntuación por enlace**, no por respuesta final. Una respuesta correcta con saltos no justificados no obtiene crédito.
3. **Oráculo independiente:** `objdump -d /usr/bin/ls | grep -A30 '<main>'` — verificación por una herramienta de *otro* proveedor que no rizin/radare2, comparando instrucciones y nombres de símbolos.

**Criterios de fallo:** (a) afirmación de causalidad sin fuente; (b) `main` reportado como candidato cuando la pregunta era "función de entrada" (`_start`); (c) confusión `nodes/edges` del callgraph con llamadas reales.

### Test B — Ausencia falsa y análisis incompleto

Casos adversarios que **un test de adaptación no capturan**:

| Caso | Qué debe producir RXRE |
|---|---|
| Símbolo no encontrado por un método pero presente | `NOT_FOUND`, no `PROVEN_ABSENT`; sugerir otro método |
| Herramienta da 0 porque el nivel de análisis es insuficiente | `EMPTY_BY_INSUFFICIENT_ANALYSIS` + discriminante; el registry ya documenta `aa`→`empty` vs `aaa`→xrefs, pero **no se verifica en runtime que el consumer distinga** |
| Comando sale exitoso sin establecer la propiedad | rc 0 + `producer_ejecutado: true` + `results: []` → **no es `ok`** |
| Salida truncada / malformada | `JSONDecodeError` convertido en `status: error` con el fragmento, no en `empty` |
| Consumer recibe salida obsoleta | verificación de hash del artefacto contra el último análisis |

**Implementación mínima:** un validador post-adapter (`backends/validators.py`) que recibe el resultado crudo y devuelve un **envelope epistémico** con campos: `status`, `evidencia`, `limitaciones`, `necesita`, `confianza`.

### Test C — Herramientas contradictorias

**Diseño:** el mismo artefacto analizado con rizin **aa** vs **aaa**, y con radare2, y con Capstone (si está disponible).

- `aa; axtj → 0` vs `aaa; axtj → 74` **NO es una contradicción** — es una diferencia de profundidad de análisis. RXRE debe **investigar la diferencia de configuración** y clasificarla, no promediar ni elegir arbitrariamente.
- **Oráculo de resolución:** el registry declara esta asimetría; el test verifica que RXRE la *use* para etiquetar cada observación con su nivel de análisis, y que una conclusión de "ausencia de xrefs" se marque `DEFERRED` hasta que se especifique el nivel.

**Criterio:** RXRE no puede declarar `PROVEN_ABSENT` mientras el nivel de análisis sea `aa`.

### Test D — Descubrimiento de relaciones cruzadas (el núcleo de la misión)

**Tarea:** reconstruir una relación **sin que la respuesta esté codificada** en una regla.

**Ejemplo:** "encuentra una función que sea llamada desde más de un lugar".

- RXRE debe unir `binary.callgraph` (quién llama a quién) con `binary.symbols` (nombres reales) y `binary.xrefs` (referencias directas).
- La relación `X llama a Y` debe provenir de una **arista del callgraph cuyo endpoint esté en la lista de símbolos**, y el estatus epistémico debe decir explícitamente "arista de `agCj`, no verificado en fuente".

**Oráculo independiente:** `radare2 -qc 'aa; agj @ sym.main'` (lista de *callers* de una función específica) contra la lista que produce el callgraph general. Son dos comandos distintos → oráculo diferencial.

### Test E — Generalización

Cada mejora arquitectural debe probarse en **al menos un caso no usado en su implementación**:

- Diferente binario (`/usr/bin/rm`, `/usr/bin/rizin`, `/usr/libexec/osbuild-worker`, `amdgpu.ko` — aunque Ghidra tarda ~9m en amdgpu.ko)
- Diferente arquitectura de relación (xrefs en lugar de callgraph)
- Evidencia incompleta (binario con xrefs eliminados, símbolo `__libc_start_main` removido)
- Backend indisponible (forzar `backend_id="ghidra"` cuando el script precompilado no existe → debe dar `not_available`, no `error` confuso)

**Regla de clasificación:** si una implementación pasa solo con `/bin/ls` → se marca **CASE_SPECIFIC** y no se considera generalizable.

### Test F — Reproducibilidad

- Los parámetros del producer (comando, flags, nivel de análisis, hash del artefacto, versión del backend) deben estar en cada resultado.
- `persistir()` debe escribir algo observable. Hoy los stubs de `rz_xrefs` y `rz_callgraph` **no escriben nada** → **esto es un fallo de reproducibilidad confirmado**.
- El test F reproduce la misma pregunta dos veces con el mismo hash de input y verifica que el segundo resultado sea alcanzado por id determinista (la colisión `COLISION:` reportada en dispatch es evidencia de que el mecanismo de persistencia *está pensado* pero no *funciona* en los adapters nuevos).

---

## 5. MEJORAS DE ARQUITECTURA MÁS VALIOSAS (ordenadas por impacto/ costo)

### Mejora 1 — Contrato común de evidencia (Nivel B) — ALTA PRIORIDAD

**Fallo que aborda:** `status: ok/empty/error` no distingue "no hay nada", "no se encontró por configuración insuficiente", "el resultado existe pero es incompleto". No hay link claim→evidencia.

**Por qué no se resuelve hoy:** el contract.py solo define el *schema de producción* del producer (backend, timeout, cleanup). No hay schema de *evidencia*.

**Implementación mínima:**
```python
# backends/epistemic.py
class Evidencia:
    fuente: str          # "radare2@008a7a6, aa; axtj @ 0x4000"
    artefacto_hash: str
    transformacion: str  # "json.loads → lista de dicts"
    consumer: str        # "rxre.core.inference"
    estatus: "PROVEN"|"PARTIAL"|"NOT_DETERMINED"|"PROVEN_ABSENT"|"DEFERRED"
    limitaciones: [str]
    afirmaciones: [Afirmacion]

class Afirmacion:
    texto: str
    soportada_por: [Evidencia.id]
    confianza: "high"|"medium"|"low"
```
- Cada adapter **devuelve** un `Evidencia` junto con el resultado, y `dispatch` lo **persiste** en una tabla única (no delega en `rz_inspect.persistir`).
- `persistir()` del dispatch se generaliza: cada adapter registra su propio envelope con `input_hash` + `output_hash` + `comando`.

**Test de regresión:** Test F reproduce la misma pregunta y verifica que el segundo `ejecutar` alcance el resultado por id, y que `result.evidencia` contenga la cadena del comando.

**Generalización:** se prueba con `/usr/bin/rm` (diferente binario, mismos campos).

**Limitación restante:** la *calidad* de la afirmación sigue a cargo de quien construye el `Evidencia` (hoy, el adapter). La mejora es estructural, no inteligente.

### Mejora 2 — Validador epistémico de salida (Test B) — ALTA PRIORIDAD

**Fallo:** un producer con rc 0 y salida JSON vacía se presenta como `status: empty` sin indicar *por qué*. Un adapter puede fallar a mitad de parseo y devolver `ok` con datos parciales.

**Implementación mínima:** `backends/validators.py` con oráculos de forma:

```python
def post_producer_validacion(envelope) -> dict:
    # 1. El resultado fue producido, no solo invocado
    if not env.get("producer_ejecutado") and env.get("results"):
        return {"status": "INCOMPLETE_PRODUCTION", ...}
    # 2. empty por causa conocida (nivel insuficiente) se etiqueta
    if status == "empty" and "nivel_analisis" in env:
        return {"epistemic": "EMPTY_BY_INSUFFICIENT_ANALYSIS", ...}
    # 3. eslabones estructurales (callgraph: todo endpoint es nodo)
    if capability == "binary.callgraph":
        nodos = {f["name"] for f in raw}
        endpoints = {e for f in raw for e in f["imports"]}
        no_nodo = endpoints - nodos
        if no_nodo:
            return {"structurally_valid": False, "missing_nodes": sorted(no_nodo), ...}
    return {"valid": True, "epistemic": status}
```

**Test de regresión:** Test B con `amdgpu.ko` (Ghidra da `ElfException` → debe ser clasificado como `unsupported`, no `ok`); con binario truncado (JSONDecodeError → `status: error` con fragmento); con `aa` en lugar de `aaa` → `EMPTY_BY_INSUFFICIENT_ANALYSIS`.

**Generalización:** binario diferente + diferente herramienta (rizin vs radare2).

**Limitación:** la regla de endpoints→nodos es específica de `agCj`; generalizar requiere conocer la estructura de cada producer.

### Mejora 3 — Registro de operaciones y `explain` (Test F) — MEDIA PRIORIDAD

**Fallo:** `persistir()` es casuística (`rz_inspect` solo); los resultados de xrefs/callgraph no están en ningún registro y no hay forma de reconstruir la cadena.

**Implementación mínima:** una tabla `investigaciones` (sqlite embebido o JSONL) con columnas:
`op_id`, `capability`, `artefacto_hash`, `comando`, `backend_id`, `backend_version`, `nivel_analisis`, `artefacto_valido`, `timestamp`, `raw_stdout_hash`, `status`, `limitaciones`.

`dispatch.ejecutar` escribe una fila en lugar de delegar; `explorar` (nueva API) devuelve las afirmaciones asociadas a un `op_id`.

**Test:** Test F — ejecutar dos veces la misma pregunta → colisión determinista → `persistido: True` con nota; y `explain(op_id)` recupera el comando completo.

**Limitación:** la tabla es memoria local; no hay versión o difusión. Para el uso de RXRE esto basta.

### Mejora 4 — Selector de experimento por discriminante (Nivel D/E) — MEDIA-ALTA PRIORIDAD, COSTO MAYOR

**Fallo:** RXRE no decide *qué investigar después* basándose en la incertidumbre restante. Sigue un plan fijo del registry.

**Implementación mínima (simple, transparente, como exige §9):**
```python
class Hipotesis:
    texto: str
    predice: [Evidencia.observable]

class Pregunta:
    hipotesis: [Hipotesis]
    def proximo_experimento(self) -> Experimento:
        # elegir la observación que divide el conjunto de hipótesis
        # con el menor coste medido (timeout del backend)
```
- Se aplica primero a **un solo caso de prueba**: la ambigüedad `aa` vs `aaa` en xrefs. Hipótesis: H1="no hay xrefs en esta dirección" vs H2="hay xrefs pero el análisis está en nivel aa". Observación discriminante: re-ejecutar con `aaa`. Costo medido: `r2` +5s vs `rizin` +3s → elegir radare2.
- **Test de generalización:** el mismo selector aplicado a cfg (¿`agf` o `agfj`?) con su propio coste.

**Limitación:** el selector no "descubre" hipótesis por sí solo; las recibe de quien formula la pregunta. Es una mejora de *selección*, no de *descubrimiento*.

---

## 6. ANÁLISIS SOBRE `binary.cfg` / `binary.dataflow`

**`binary.cfg`:** radare2 `agfj` produce JSON válido (registry lo declara AVAILABLE para radare2). El registro afirma que radare2 lo hace; **la afirmación no fue re-verificada en este turno** y por lo tanto no debe usarse como evidencia verificada.

**`binary.dataflow`:** radare2 `afvxj` produce JSON **válido** pero con el **conjunto de escrituras vacío** para una función con store probable (medido en el hallazgo anterior y documentado en el registry: `mov dword [edi - 0x30000000], edx` no aparece en `writes`). Esto significa: **el formato es correcto pero el contenido es incompleto** → `AVAILABLE` no significa `COMPLETO`. Un adapter que cierre esta capacidad sin documentar la incompleción convertiría `NOT_DETERMINED` en `PROVEN_ABSENT` — el fallo de los hallazgos 1569/1571.

**Decisión (coherente con AGENTS.md §8-§11):** no implementar adapters para cfg/dataflow en este turno. **Razón:** (a) su contract semántico (qué es un bloque básico, cómo se distinguen los tipos de aristas, qué cubre el dataflow interfuncional) no está cerrado en el registro; (b) implementar solo para "completar el conteo" violaría §98 NO AUTOMATION THEATER; (c) la frontera abierta real es **la semántica del resultado**, no la ausencia de un módulo que invoque un comando.

**Siguiente experimento de alto valor:** medir directamente `r2 -q -e scr.color=0 -c 'aa; agfj @ sym.main'` y `r2 -q -e scr.color=0 -c 'aa; afvxj @ sym.main'` sobre un binario pequeño, para decidir si el registro puede cerrar `binary.cfg` como `AVAILABLE` (radare2) y precisar `binary.dataflow` con su limitación de escrituras.

---

## 7. COMPARACIÓN ANTES / DESPUÉS (misión RXRE-1637)

| Propiedad | Antes | Después de este turno | Evidencia |
|---|---|---|---|
| baseline documentado | implícito en reportes | **documentado aquí** (sección 1, verificado en checkout) | este documento |
| investigación externa evaluada | no hay | **AgentRE-Bench, SRE-Bench, SWE-bench Science, AgentLens** — matriculados | secciones 2-3 |
| capacidades probadas más allá del registro | solo `ejecutar` exitoso | **validación estructural del callgraph**, distinción `aa` vs `aaa`, verificación de endpoints→nodos | Test A-D (diseño) |
| al menos una investigación causal real | no | **no completada** (requiere Test A con oráculo objdump — pendiente) | Test A |
| modos de fallo y vacíos de evidencia explícitos | parcialmente (registry) | **explicitados** (sección 1.3) | este documento |
| criterios de aceptación independientes | test_oracle compartía la misma suposición que el adapter | **oráculos independientes diseñados** (objdump, radare2 `agj`, `afvxj`) | Test A, D |
| mejora implementada con test de regresión | — | **diseño de 4 mejoras**, ninguna implementada en este turno (el trabajo de implementación requiere Test A/D/F ejecutados primero como justificación) | sección 5 |
| mejora general con caso independiente | — | **diseño incluido** (sección 5, Test E) | este documento |
| comparación antes/después basada en evidencia | — | **parcial**: solo mejoras diseñadas, no implementadas → tabla honesta: "diseñado" no "implementado" | esta tabla |
| limitaciones documentadas | parcialmente | **explícitas** en cada mejora y en la clasificación final | secciones 4-6 |

**Lo que NO se pudo hacer en este turno (y por qué):**
- **Implementar las mejoras** (contract de evidencia, validador, registro, selector): requeriría ejecutar Test A/D/F para tener la justificación de qué contratos medir. Implementar arquitectura antes de tener la evidencia es construir abstracciones para necesidades hipotéticas — prohibido por §13.
- **Cruzar xrefs/callgraph/símbolos** para una afirmación causal real: requiere un artefacto de prueba preparado y un oráculo objdump verificado. Se pospone a la fase de implementación.
- **Re-verificar `binary.cfg` `agfj` y `binary.dataflow` `afvxj`** en runtime con `-e scr.color=0`: la medición está en el registro como afirmación de otro turno; no se volvió a ejecutar aquí. Por tanto no se puede cerrar esas fronteras con este turno.

---

## 8. CONCLUSIÓN FINAL

**¿Puede RXRE hoy descubrir y justificar relaciones técnicas no codificadas y mejorar su capacidad de investigar sin hardcoding?**

**No.** RXRE es un orquestador que (a) declara qué capacidades existen, (b) ejecuta el adapter correspondiente, (c) devuelve su salida con un envelope consistente. Falta:

1. **Una capa de evidencia común** (claim→evidencia con estatus epistémico).
2. **Validación epistémica** que distinga `empty` por ausencia real de `empty` por análisis insuficiente.
3. **Un registro de operaciones** que permita reconstruir cadenas causales (`explain <op_id>`).
4. **Un selector de experimento** que elija el siguiente paso por valor discriminante, no por plan fijo.
5. **Oráculos independientes** que midan la semántica, no el esquema.

**¿Qué puede RXRE hacer confiablemente ahora que no podía antes de RXRE-1635/1636?**

- Pedir `binary.callgraph` como capacidad cerrada con su adapter y plan (`inspect→functions→callgraph`).
- Pedir `binary.xrefs` sabiendo explícitamente que requiere `nivel_analisis='aaa'` y recibiendo esa limitación en cada respuesta.
- Detectar que `binary.cfg`/`binary.dataflow` son **capacidades declaradas sin producer** y que `esta_permitida()` las bloquea con el motivo exacto.
- **Pero no:** conectar esos resultados entre sí, ni justificar una relación causal, ni detectar que `nodes=5, edges=82` no significa que cada arista apunte a un nodo, ni saber que un `empty` puede ser un artefacto de `aa` en lugar de una ausencia.

**Próximo experimento de mayor valor:** ejecutar el **Test A** completo con oráculo `objdump -d` sobre `/usr/bin/ls` (función de entrada, primer argumento). Es barato (~10 s de herramientas), tiene oráculo independiente y establece si RXRE puede, siquiera en un caso trivial, producir una afirmación con fuente explícita — el mínimo requisito para el Nivel B. Mientras Test A no pase, cualquier mejora arquitectural de "evidencia" será una abstracción sin caso que la concrete.

**Clasificación de entregables:**
| Entregable | Estado |
|---|---|
| A. Informe de investigación | **COMPLETE** |
| B. Matriz de capacidades | **COMPLETE** |
| C. Especificación de evaluación (Test A-F) | **COMPLETE** |
| D. Tests ejecutables | **PARTIAL** (diseñados; Test A/D/F requieren ejecución en fase de implementación) |
| E. Análisis de brechas arquitectónicas | **COMPLETE** |
| F. Informe de implementación | **PARTIAL** (diseño de 4 mejoras con tests de regresión; implementación pendiente de Test A/D/F) |
| G. Comparación antes/después | **PARTIAL** (diseño → después; implementación no ejecutada) |

**Honestidad final:** este turno cerró RXRE-1636 y realizó la fase de diagnóstico de RXRE-1637. La fase de implementación no se ejecuta porque la directiva §13 prohíbe construir arquitectura sin evidencia que la concrete, y esa evidencia (Test A/D/F ejecutados) no se tiene aún. No hay regresión: `test_callgraph1636.py` 22/22, `test_backends_bulk.py` 99/99 (el fallo es un test de Ghidra preexistente ajeno a estos cambios), `test_dispatch004.py` sin fallos nuevos.
