# Inventario de capacidades de RXRE

**Corte del catálogo:** 2026-11-18. Este inventario se obtuvo del registro y del dispatch del checkout local. Es una clasificación de implementación y superficie; no es una nueva validación de todas las herramientas ni una afirmación de revisión externa.

## Respuesta corta

El registro anuncia **30 capabilities**. Con una definición estricta de “propia” —el productor principal es código o estado interno de RXRE—, **10 son nativas de RXRE**, **1 es híbrida** y **19 delegan el análisis en herramientas externas**.

| Clase de implementación | Cantidad | Qué significa |
| --- | ---: | --- |
| Nativa de RXRE | 10 | Nueve capacidades de conocimiento sobre el backend `knowledge` y el lifting propio `rxre-lifter` |
| Híbrida | 1 | `gpu.mmr_read`: adapter RXRE sobre la interfaz ioctl del kernel/hardware |
| Delegada | 19 | El productor principal es Rizin, radare2, Capstone, Ghidra, Coccinelle, Tree-sitter, UMR o REA |
| **Total registrado** | **30** | 10 + 1 + 19 |

Por tanto, “RXRE tiene 30 capacidades propias” sería impreciso. Tiene 30 entradas en su registro de capabilities; 10 son nativas bajo la definición de arriba. Aparte existen operaciones API y módulos internos IER que no son entradas de ese registro.

## Las 30 capabilities registradas

El estado es el que devuelve el catálogo al corte indicado. `AVAILABLE` o `PARTIAL` describe el estado declarado para el alcance medido; no garantiza que la herramienta esté instalada en otro host ni que el resultado pruebe una propiedad general.

### Nativas de RXRE: 10

| Capability | Estado | Productor | Función |
| --- | --- | --- | --- |
| `rxre.create_finding` | `AVAILABLE` | `knowledge` | Crea un hallazgo persistente |
| `rxre.create_finding_relation` | `AVAILABLE` | `knowledge` | Crea una relación entre hallazgos |
| `rxre.evaluate_applicability` | `AVAILABLE` | `knowledge` | Evalúa aplicabilidad de evidencia/hallazgos |
| `rxre.get_finding` | `AVAILABLE` | `knowledge` | Recupera un hallazgo |
| `rxre.list_finding_relations` | `AVAILABLE` | `knowledge` | Lista relaciones de hallazgos |
| `rxre.list_findings` | `AVAILABLE` | `knowledge` | Lista hallazgos |
| `rxre.observation_engine` | `AVAILABLE` | `knowledge` | Integra observaciones registradas |
| `rxre.plan_investigation` | `AVAILABLE` | `knowledge` | Propone un plan de investigación |
| `rxre.search_findings` | `AVAILABLE` | `knowledge` | Busca en hallazgos registrados |
| `binary.lift` | `PARTIAL` | `rxre-lifter` | Levanta instrucciones a una representación interna; conserva las limitaciones de cobertura/contrato |

Las nueve capacidades `rxre.*` pertenecen al modelo de conocimiento de RXRE y usan la persistencia de `core/store.py`; pueden escribir en la base configurada. No son nueve herramientas externas.

### Híbrida: 1

| Capability | Estado | Productor | Límite |
| --- | --- | --- | --- |
| `gpu.mmr_read` | `AVAILABLE` | `mmr_ioctl` | RXRE aporta el adapter; la lectura depende de la interfaz del kernel y del hardware. Sigue la puerta `require_gpu()` y las restricciones de autorización. |

### Delegadas a herramientas externas: 19

| Capability | Estado | Productor(es) declarados |
| --- | --- | --- |
| `binary.basic_blocks` | `AVAILABLE` | radare2, Rizin |
| `binary.callgraph` | `AVAILABLE` | radare2, Rizin |
| `binary.cfg` | `AVAILABLE` | radare2, Rizin |
| `binary.dataflow` | `AVAILABLE` | radare2, Rizin |
| `binary.decompile` | `PARTIAL` | Ghidra, radare2, Rizin |
| `binary.disassemble` | `AVAILABLE` | Capstone, radare2, Rizin |
| `binary.disassemble_func` | `AVAILABLE` | Capstone, Rizin |
| `binary.exports` | `AVAILABLE` | Rizin |
| `binary.functions` | `AVAILABLE` | radare2, Rizin |
| `binary.imports` | `AVAILABLE` | Rizin |
| `binary.inspect` | `AVAILABLE` | radare2, Rizin |
| `binary.sections` | `AVAILABLE` | Rizin |
| `binary.strings` | `AVAILABLE` | Rizin |
| `binary.symbols` | `AVAILABLE` | Rizin |
| `binary.xrefs` | `AVAILABLE` | radare2, Rizin |
| `gpu.register_read` | `AVAILABLE` | UMR |
| `rea.inspect_firmware` | `AVAILABLE` | REA |
| `source.ast_parse` | `AVAILABLE` | Tree-sitter |
| `source.semantic_search` | `AVAILABLE` | Coccinelle (`spatch`) |

`binary.decompile` figura `PARTIAL`: no implica soporte universal para todos los formatos (por ejemplo, el caso medido de módulos ELF `ET_REL` tiene límites). `binary.dataflow` agregado `AVAILABLE` tampoco significa cobertura completa de escrituras; respeta las limitaciones que devuelve el backend elegido.

## Backends y tecnologías

El registro contiene **11 identificadores de backend**:

- **8 herramientas externas:** Capstone, Coccinelle, Ghidra, radare2, REA, Rizin, Tree-sitter y UMR.
- **3 productores internos o interfaces de RXRE:** `knowledge`, `rxre-lifter` y `mmr_ioctl`.

`angr` y `rz-ghidra` aparecen como candidatos no verificables (`NOT_DETERMINED`); no son parte de las 30 capabilities registradas ni se cuentan entre las 11 entradas de backend.

## Capabilities, operaciones y módulos IER no son lo mismo

| Superficie | Conteo del checkout | Fuente de verdad | Nota |
| --- | ---: | --- | --- |
| Capabilities registradas | 30 | `backends/registry.py`, consultado por `backends/dispatch.py` | Productores de evidencia accesibles mediante `op:run` si pasan el allow-list |
| Operaciones de API únicas | 33 | `HANDLERS` en `api/machine.py` | Incluye operaciones del motor, utilidades, y handlers sujetos a límites distintos |
| Operaciones anunciadas por `op:ops` | 20 | `_handle_ops()` en `api/machine.py` | Catálogo curado; **no es exhaustivo** |
| Subcomandos de motor del launcher `./rxre` | 11 | `ENGINE_OPS` en el launcher raíz `rxre` | No incluye todas las operaciones directas de la API |

Entre las 13 operaciones API no enumeradas por `op:ops` están `defect`, `territory`, `query`, `relation`, `investigate`, `hypothesize`, `select_experiment`, `select_experiment_predictive`, `bench`, `eter`, `execution`, `ingest` y `claim`. `defect` reconstruye un defecto sin repararlo; `territory` identifica el entorno de un artefacto. Ambas se envían por JSONL a `api/machine.py`, no son subcomandos de `./rxre`. Que un nombre esté en `HANDLERS` no significa que sea inocuo, autorizado o adecuado para exploración: inspecciona el handler y las instrucciones antes de invocarlo. En particular, `claim` tiene restricciones explícitas.

Los módulos de `ier/` —por ejemplo `evidence_contract`, `transformer_witness`, `independent_verifier`, `lifetime_contract`, `region_analyzer`, `call_summary_admission` y `expression_metadata_witness`— son componentes internos del motor. No se suman al registro de 30 hasta que exista una capability registrada que los exponga. `expression_metadata_witness` compara metadatos de expresiones IR antes/después de una reescritura; el [expediente IER-EMW-001](IER_EXPRESSION_METADATA_WITNESS_001.md) registra su reproducción reducida del issue angr #7013, límites y uso.

## Cómo refrescar este inventario

1. Ejecuta `./rxre capabilities --json` o consulta `dispatch.listar()` y cuenta `capacidades`.
2. Usa `registry.py` para el productor/estado declarado y `ADAPTERS` en `dispatch.py` para confirmar qué capabilities tienen adapter.
3. Cuenta las claves únicas de `HANDLERS` para la API; no uses la cantidad de `op:ops` como total.
4. Consulta `ENGINE_OPS` en `rxre` para el subconjunto con subcomando propio.
5. Actualiza esta página cuando cambie el registro o la clasificación. Anota el corte y conserva separados los estados operativos, la evidencia y la validación de terceros.

La identidad y las reglas de trabajo están en [`AGENTS.md`](../AGENTS.md); el [inicio rápido para agentes](AI_QUICKSTART.md) explica cómo empezar con seguridad.
