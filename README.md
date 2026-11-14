# RXRE — repositorio de investigación y desarrollo

**Estado real (2026-11-14): repositorio público de trabajo.** No es el paquete publicado; no demuestra verificación independiente por terceros; no declara `PASS`.

## Qué es esto

[RXRE](https://github.com/LexLuthorPrimero/rxre-engine) es un **motor de investigación en ingeniería inversa asistida por IA**: reconstrucción semántica con evidencia sellada, hipótesis rivales falsables, pruebas discriminantes, veredictos diferenciados (`PROVEN`/`MISMATCH`/`TESTED_ONLY`/`INCONCLUSIVE`, y sus equivalentes operativos `PASS`/`PARTIAL`/`BLOCKED`) y validación con oráculos cuyo alcance y procedencia están declarados.

Este repositorio es el **espacio de investigación y desarrollo** de RXRE. No es la publicación ni el paquete de instalación.

| Repositorio | Qué es | Estado |
| --- | --- | --- |
| este (`rxre`) | Código del engine + evidencia de reconstrucción + corpus de investigación + estado de la misión multiproyecto | público, en desarrollo |
| `rxre-engine` | Paquete publicado del engine (v1.9.0) | publicado; verificación de terceros NOT_EXECUTED |
| `rxre-cleanroom` | Reconstrucción verificable (corpus sellado) | publicado; terceros NOT_EXECUTED |

## Índice exacto de lo que contiene este repo

Clasificación honesta de cada entrada raíz. **RXRE/Engine** = código del motor. **Evidencia** = artefactos sellados con historia propia. **Investigación** = corpus, notas y código experimental de la RX550/GPU. **Histórico** = material de archivo sin valor normativo. **Herramientas** = scripts/piezas auxiliares del engine. **Misión** = continuidad de esta misión.

| Entrada | Qué es | Clase |
| --- | --- | --- |
| `tools/` | Engine RXRE completo: adapters, backends, `machine.py` CLI, `verifier/`, `analysis/`, tests | **RXRE/Engine** |
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

## Lo que este repositorio NO afirma

- Ningún cambio fue verificado por terceros. **Verificación de terceros: NOT_EXECUTED.**
- Ninguna reconstrucción demuestra autenticidad de origen; el hash demuestra integridad frente a lo esperado, no autenticidad.
- Las PRs abiertas en otros ecosistemas (rizin, angr, capstone, morluto/rea) están **en revisión**; al momento de este documento: 0 fusionadas.
- No se afirma `PASS` ni `PROVEN` sin evidencia en el dominio y alcance declarados.

## Cómo probar

```bash
./run_tests.sh                 # corre tools/rxre/tests/*.py (rc=0 PASS, rc=3 SKIP)
python3 -B tools/rxre/tests/test_semantic_equiv_4972.py   # ejemplo: 7/7 PASS
```

Requisitos: Python 3, angr, z3, capstone, radare2, rizin, Ghidra (opcional según tests), bwrap.

## Licencia

GPL v2. Ver `LICENSE`.

## Referencia honesta del estado técnico

La historia detallada de misiones vive en `RXRE_CHANGELOG.md` y `state/multiproject/log.md`. El paquete publicado y su estado de publicación vive en `rxre-engine`. La evidencia sellada vive en `rxre-r3/`. La misión en curso vive en `state/multiproject/`.
