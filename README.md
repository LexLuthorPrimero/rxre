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

## Qué contiene

| Directorio | Contenido |
| --- | --- |
| `tools/rxre/` | El engine: backends, adapters, API (`machine.py`), verificador independiente (`verifier/`), análisis acotados (`ssa`, `ir`, `diff_harness`, `decompiler/fidelity`), tests |
| `rxre` | Launcher del CLI |
| `rxre-r3/` | Evidencia sellada de reconstrucciones (wc, filenvercmp…) |
| `vk_test/` | Pruebas Vulkan/SPIR-V |
| `rx550-upstream-7.2.8/` | Integración RX550 |
| `state/multiproject/` | Estado persistente de la misión multiproyecto (log, backlog, capacidad, evidencia) |
| `RESEARCH/` | Informes históricos de misiones (RXRE-1637…1644, PS5) |
| `findings/`, `06-INGENIERIA-INVERSA/` | Diarios de hallazgos de la investigación |
| `revkit/`, `04-IMPLEMENTACION/`, `07-DRIVER/`, `03-EXPERIMENTOS/`, `08-ARQUITECTURA/` | Trabajo de la RX550/driver/análisis experimental |
| `audit/`, `docs/`, `archive/` | Auditorías, documentación e historial |
| `.gitignore`, `run_tests.sh` | Reglas de versionado e runner de tests |

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
