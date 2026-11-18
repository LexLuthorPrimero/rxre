# RXRE — repositorio de investigación y desarrollo

**Estado real (2026-11-18): repositorio público de trabajo.** No es el paquete publicado ni cuenta con verificación independiente por terceros. Los resultados de pruebas locales no equivalen a validación externa ni prueban una capacidad general.

## Qué es esto

[RXRE](https://github.com/LexLuthorPrimero/rxre-engine) es un **motor de investigación en ingeniería inversa asistida por IA**: reconstrucción semántica con evidencia sellada, hipótesis rivales falsables, pruebas discriminantes, veredictos diferenciados (`PROVEN`/`MISMATCH`/`TESTED_ONLY`/`INCONCLUSIVE`, y sus equivalentes operativos `PASS`/`PARTIAL`/`BLOCKED`) y validación con oráculos cuyo alcance y procedencia están declarados.

Este repositorio es el **espacio de investigación y desarrollo** de RXRE. No es la publicación ni el paquete de instalación.

## Si eres una IA que acaba de entrar

1. Lee [`AGENTS.md`](AGENTS.md) antes de actuar: fija los límites, la autorización y los estados de evidencia.
2. Inspecciona `git status --short --branch` y conserva todos los cambios existentes.
3. Para el motor, lee [`tools/rxre/AGENTS.md`](tools/rxre/AGENTS.md), [`tools/rxre/README.md`](tools/rxre/README.md), la [guía de inicio](tools/rxre/docs/AI_QUICKSTART.md) y el [inventario de capabilities y operaciones](tools/rxre/docs/CAPABILITIES.md).
4. Consulta `./rxre ops` y `./rxre capabilities` para ver los catálogos anunciados. `op:ops` no enumera necesariamente todos los handlers: comprueba `HANDLERS` en `tools/rxre/api/machine.py` y `ENGINE_OPS` en `rxre` antes de concluir que una ruta no existe.
5. Antes de probar, inspecciona los efectos del test y usa una `RXRE_DB` temporal. No ejecutes una prueba de hardware ni accedas a la GPU sin autorización y sin pasar por `require_gpu()`.

`AGENTS_ESTADO_GENERADO.md` es una instantánea fechada, no estado en vivo; no la edites a mano. Verifica su fecha y vuelve a ejecutar el verificador indicado antes de usarla como evidencia actual.

Los archivos bajo `tools/rxre/docs/archive/` son referencias históricas. No son instrucciones vigentes.

| Repositorio | Qué es | Estado |
| --- | --- | --- |
| este (`rxre`) | Código del engine + evidencia de reconstrucción + corpus de investigación + estado de la misión multiproyecto | público, en desarrollo |
| `rxre-engine` | Paquete publicado del engine (v1.9.0) | publicado; verificación de terceros NOT_EXECUTED |
| `rxre-cleanroom` | Reconstrucción verificable (corpus sellado) | publicado; terceros NOT_EXECUTED |

## Índice exacto de lo que contiene este repo

Clasificación honesta de cada entrada raíz. **RXRE/Engine** = código del motor. **Evidencia** = artefactos sellados con historia propia. **Investigación** = corpus, notas y código experimental de la RX550/GPU. **Histórico** = material de archivo sin valor normativo. **Herramientas** = scripts/piezas auxiliares del engine. **Misión** = continuidad de esta misión.

| Entrada | Qué es | Clase |
| --- | --- | --- |
| `tools/` | Engine RXRE completo: adapters, backends, `machine.py` CLI, `verifier/`, `analysis/`, tests y guías específicas para agentes | **RXRE/Engine** |
| `rxre` | Launcher del CLI (`python3`) | **Engine** |
| `rxre-r3/` | Evidencia sellada de reconstrucciones (wc, filenvercmp…) | **Evidencia** |
| `vk_test/` | Pruebas Vulkan/SPIR-V (shaders, binarios) | **Investigación/GPU** |
| `rx550-upstream-7.2.8/` | Snapshot upstream del kernel para la RX550 | **Investigación/GPU** |
| `state/multiproject/` | Estado de esta misión (log, backlog, capacidad, evidencia) | **Misión** |
| `run_tests.sh` | Runner de tests (`tools/rxre/tests/*.py`) | **Engine** |
| `LICENSE` | GPL v2 | Metadato |
| `README.md` / `AGENTS.md` / `AGENTS_ESTADO_GENERADO.md` | Alcance real + política agentes + estado generado | Metadato |
| `RXRE_CHANGELOG.md` | Historial de misiones | Metadato/Histórico |
| `VERIFY.md` / `VERIFIED_HASHES.md` | Instrucciones y hashes de verificación | Metadato |
| `RELEASE-NOTES.md` | Notas de publicación | Metadato |
| `03-EXPERIMENTOS/` | ATOMBIOS-DECODER (prueba de decodificación ATOMBIOS/GPU) | **Investigación** |
| `04-IMPLEMENTACION/` | Driver experimental RX550 (`rx550-driver/`) | **Investigación** |
| `06-INGENIERIA-INVERSA/` | Notas de ingeniería inversa (hallazgos temáticos) | **Histórico** |
| `07-DRIVER/` | Benchmarks del driver (`bench/`) | **Investigación** |
| `08-ARQUITECTURA/` | Notas de arquitectura (TOOLCAT, REPARO-2, grafo) | **Histórico** |
| `RESEARCH/` | Informes de misiones (1637–1644, PS5-001/002, baseline) | **Histórico** |
| `RXRE/` | Bootstrap del motor (`rxre_boot.py`, contratos propios) | **Engine** |
| `revkit/` | Herramientas de captura/análisis RX550 (parseo, MMRs) | **Investigación** |
| `findings/` | Diarios de hallazgos `.md` numerados | **Histórico** |
| `audit/` | Auditorías, claims, revisión (docs internos) | **Histórico** |
| `archive/` | Archivo (`rxre-esqueleto-2026-10-18/`) | **Histórico** |
| `artifacts/` | Dumps sueltos (gfx8 cobertura) | **Histórico** |
| `results/` | Resultados de sesión (p.ej. DOGFOOD-1621) | **Histórico** |
| `patches/` | Parche Coccinelle puntual | **Herramientas** |
| `scripts/` | `f2_producer_safe.py` | **Herramientas** |
| `docs/` | Informes/contratos internos (SPE, publicación, decisiones) | **Histórico** |
| `.rxre/` | Snapshots GPU RX550 (fixtures internos) | **Investigación** |
| `.gitignore` | Reglas (rxre.sqlite3, .rxre/, paquete SPE…) | Metadato |

Ninguna entrada de esta tabla tiene valor normativo por sí sola; la verdad son el código, los tests y los expedientes enlazados.

## Capacidades IER incorporadas

El código de `tools/rxre/ier/` incluye ahora capacidades acotadas para evaluar transformaciones con evidencia y para analizar vidas temporales de regiones:

Para el recuento de capabilities propias, híbridas y delegadas, y la diferencia frente a operaciones API y módulos internos, consulta el [inventario completo](tools/rxre/docs/CAPABILITIES.md). No sumes esas superficies como si fueran una sola categoría.

- `evidence_contract.py` vincula la fuente sellada, el caso, la transformación propuesta y las observaciones que deben preservarse. Un manifiesto íntegro por sí solo no basta para admitir una transformación.
- `transformer_witness.py` evalúa seis condiciones (`B`, `W`, `O`, `L`, `C`, `D`) sobre un modelo explícito de la transformación. `SAFE_TO_TRANSFORM` requiere que todas estén demostradas; una condición desconocida produce abstención. El módulo no prueba por sí solo el comportamiento del binario ni del driver.
- `independent_verifier.py` reconstruye y verifica esas propiedades por un camino separado del testigo. Su resultado sigue acotado al caso y a la evidencia consumida; no declara `PROVEN` sin un oráculo independiente que cubra el dominio.
- `lifetime_contract.py` comprueba identidad del artefacto, integridad, CFG y solapamiento de vidas. `IRRELEVANT` significa que una referencia no observa la vida candidata en ese punto; nunca autoriza por sí solo una transformación.
- `angr_guard_bridge.py` y `rxre_angr_adapter.py` enlazan decisiones del análisis con el binario, la función, el callsite y los resúmenes declarados. Ante evidencia ausente o contradictoria, bloquean o se abstienen.
- `machine.py` expone las operaciones `defect` (reconstrucción causal, sin reparar) y `territory` (identificación del entorno tecnológico). `store.py` clasifica el esquema M281 y bloquea escrituras cuando una base protegida está incompleta o es incompatible; la migración automática queda limitada a rutas no protegidas.

Las pruebas adversariales correspondientes están en `tools/rxre/tests/`: `test_evidence_contract.py`, `test_transformer_witness.py`, `test_independent_verifier.py`, `test_lifecycle_integration_adversarial.py`, `test_lifetime_irrelevant_adversarial.py`, `test_second_fixture_lifetime.py`, `test_angr_guard_bridge_adversarial.py` y `test_rxre_angr_adapter.py`. También siguen las pruebas de `region_analyzer` y `call_summary_admission` para la cadena #7294.

Las pruebas que usan evidencia sellada M10/M11 esperan esos artefactos locales bajo `~/rxre-angr-7294-m10` y `~/rxre-angr-7294-m11`; se pueden cambiar las rutas con `RXRE_7294_SEALED_DIR`, `RXRE_7294_M11S_DIR` y `RXRE_7294_M11_DIR`. `test_angr_7294.py` necesita además `RXRE_ANGR_7294_SOURCE`; si falta ese checkout, informa `SKIP`.

## Lo que este repositorio NO afirma

- Ningún cambio fue verificado por terceros. **Verificación de terceros: NOT_EXECUTED.**
- Ninguna reconstrucción demuestra autenticidad de origen; el hash demuestra integridad frente a lo esperado, no autenticidad.
- Las PRs abiertas en otros ecosistemas (rizin, angr, capstone, morluto/rea) están **en revisión**; al momento de este documento: 0 fusionadas.
- No se afirma `PASS` ni `PROVEN` sin evidencia en el dominio y alcance declarados.

## Cómo probar

```bash
./run_tests.sh                 # runner amplio; inspecciona primero sus dependencias y efectos
RXRE_DB=/tmp/rxre-ier-focused-tests.sqlite3 python3 -B tools/rxre/tests/test_evidence_contract.py
```

El runner amplio puede encontrar pruebas que requieren herramientas externas, corpus local o hardware; no lo uses como primer paso de una tarea. Ejecuta primero una prueba específica, con `RXRE_DB` temporal cuando pueda haber persistencia. Requisitos de herramientas: Python 3; angr, z3, capstone, radare2, rizin, Ghidra y bwrap solo según la prueba o capability elegida.

## Licencia

GPL v2. Ver `LICENSE`.

## Referencia honesta del estado técnico

La historia detallada de misiones vive en `RXRE_CHANGELOG.md` y `state/multiproject/log.md`. El paquete publicado y su estado de publicación vive en `rxre-engine`. La evidencia sellada vive en `rxre-r3/`. La misión en curso vive en `state/multiproject/`.
