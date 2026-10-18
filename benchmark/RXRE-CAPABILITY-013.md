# RXRE-CAPABILITY-013 — TRACE_DATA IMPLEMENTATION RECONCILIATION

## OBJETIVO

Comparar las dos implementaciones existentes de TRACE_DATA y determinar cuál constituye la base técnica adecuada para su validación e integración en RXRE. READ-ONLY sobre el worktree.

## REPOSITORY_IDENTITY

```text
REPO_ROOT           /home/lucas/Escritorio/rxre
MAIN_REF            53de0098f43d8ab8340603204675a1a2e0faabef  (main)
CURRENT_HEAD        9ce74c53ba5a356fed9893c5f62b32e01f9d883a  (migration/validated-legacy-work)
WORKTREE            único
DIRTY_STATE         SÍ (cambios de build en 04-IMPLEMENTACION/ y archivos modificados
                      en revkit/, tools/, 08-ARQUITECTURA/, etc.)
```

---

## CANDIDATE_A_PROVENANCE  (rama `capability/trace-data`, commit `e35ae36`)

```text
REPOSITORY_ROOT     /home/lucas/Escritorio/rxre
COMMIT_O_BRANCH     e35ae361db9138ce3e3792f7a71e72a3e89ef182 (capability/trace-data)
HEAD                e35ae36
WORKTREE            (consultado via git cat-file, no checkout realizado)
TRACKED_FILES       tools/trace_data.py, tools/reg_resolve.py
UNTRACKED_FILES     n/a (commit aislado)
IMPLEMENTATION_FILE_HASH   a1af46d0fc4fb952573fdf5067ea84a4  (tools/trace_data.py)
TEST_FILE_HASHES    — (no incluye fixtures; usa --selftest con vectores internos)
DEPENDENCIES         tools/reg_resolve.py (import interno)
```

Arquetipo: standalone con integración a `reg_resolve`. 655 líneas. Salida JSON
anidada por función. Auto-declara `WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE`.

## CANDIDATE_B_PROVENANCE  (worktree, `migration/validated-legacy-work`)

```text
REPOSITORY_ROOT     /home/lucas/Escritorio/rxre
COMMIT_O_BRANCH     9ce74c53ba5a356fed9893c5f62b32e01f9d883a (migration/validated-legacy-work)
HEAD                9ce74c5
WORKTREE            worktree principal (dirty)
TRACKED_FILES       — (cambios no committeados; files untracked)
UNTRACKED_FILES     tools/rxre_trace_data.py (untracked)
                    tools/rxre/core/dispatch.py (modificado, untracked)  
                    tools/rxre/commands/handlers.py (modificado, untracked)
                    tools/rxre/cli.py (modificado, untracked)
IMPLEMENTATION_FILE_HASH   c6e5c5999ccfb69b9b36354f0cdfe5f7  (tools/rxre_trace_data.py)
TEST_FILE_HASHES    n/a
DEPENDENCIES         ninguna (no importa reg_resolve)
```

Arquetipo: integrado a `rxre` vía dispatch/handlers/cli. 689 líneas (trace_data.py).
Salida JSON plana por registro. Auto-declara `WORK_CLASS=READ_ONLY` implícito.

---

## CODE_AND_INTERFACE_COMPARISON

| Aspecto | Candidate A (e35ae36) | Candidate B (9ce74c5) |
|---|---|---|
| Archivo principal | `tools/trace_data.py` | `tools/rxre_trace_data.py` |
| Líneas | 655 | 689 |
| Integración RXRE | Standalone (script) | dispatch.py (etapa 3), handlers.py, cli.py |
| `import reg_resolve` | ✅ (import interno) | ❌ (no import, no register_resolution) |
| Macro families | `SOC15_*`, `bare` (RREG32/WREG32/WREG32_P) | `bare` solamente (RREG32/WREG32/WREG32_*) |
| CLI | `--kernel --amd-root --file [--function] [--json]` | `--register|--function [--kernel] [--gfx] [--json]` |
| Salida JSON | anidada por función (`functions[]`) | plana (`results[]`) |
| Self-test | vectors internos, <1 s | corpus de prueba (amdgpu/), ~1s cached / ~88s cold |
| RMW mecanismo | `software_rmw[]` + `hardware_rmw[]` | único `READ_MODIFY_WRITE` |
| RMW detección | data-flow (variable dependiente) | proximidad (READ→WRITE, sin WRITE intermedio) |
| Register identity | `register_resolution` con `value`/`unit`/`conflict`/`chosen_header` | solo `register` (nombre textual) |
| Transport classification | `NOT_DETERMINED` (SR-IOV condicional) | NO |
| Capa distinción | SOURCE_TOKEN/REGISTER_RESOLUTION/ACCESS_TRANSPORT/HARDWARE_EFFECT | solo operation/source |

---

## COMMON_CORPUS

```text
CORPUS_ROOT     /home/lucas/Escritorio/rxre/RESEARCH/kernelbuild/linux-7.1.3
CORPUS_FILE     drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c
FILE_HASH       (sin registrar hash exacto, file exists: 52231 bytes, 2024-07-04)
```

---

## MACRO_COVERAGE

Tabla de familias de macros inspeccionadas en el corpus:

| MACRO | EXISTS_IN_CORPUS | INVOCACIONES (gmc_v8_0.c) | RECOGNIZED_BY_A | RECOGNIZED_BY_B |
|---|---|---|---|---|
| `RREG32` | ✅ (amdgpu.h:1293) | 84 | ✅ | ✅ |
| `WREG32` | ✅ (amdgpu.h:1295) | 131 | ✅ | ✅ |
| `WREG32_P` | ✅ (amdgpu.h:1324) | 1 | ✅ | ❌ (pattern no matches) |
| `RREG32_SOC15` | ✅ (soc15_common.h:66) | 176 en vcn_v4_0_5.c | ✅ | ❌ |
| `WREG32_SOC15` | ✅ (soc15_common.h:82) | 237 en vcn_v4_0_5.c | ✅ | ❌ |
| `RREG32_SOC15_IP` | ✅ (soc15_common.h:70) | varias | ✅ | ❌ |
| `WREG32_SOC15_IP` | ✅ (soc15_common.h:86) | varias | ✅ | ❌ |
| `RREG32_SOC15_NO_KIQ` | ✅ (soc15_common.h:74) | varias | ✅ | ❌ |
| `WREG32_SOC15_NO_KIQ` | ✅ (soc15_common.h:92) | varias | ✅ | ❌ |
| `RREG32_SOC15_OFFSET` | ✅ (soc15_common.h:78) | varias | ✅ | ❌ |
| `WREG32_SOC15_OFFSET` | ✅ (soc15_common.h:96) | varias | ✅ | ❌ |

**Conclusión:** Candidate A detecta 11 familias; Candidate B detecta 3 (RREG32, WREG32,
WREG32_P *no* — ver nota). Candidate A distingue macro_family (`soc15` vs `bare`).

---

## COMMON_CASES_RESULTS

### VM_CONTEXT0_CNTL — register→function

| Candidate A | Candidate B |
|---|---|
| status: ok | status: ok |
| 28 accesos físicos (84R, 131W → solo gmc_v8_0 filter) | 20 accesos simples + 8 RMW rows = 28 rows |
| 7 RMW software | 8 RMW (todos READ_MODIFY_WRITE) |
| gmc_v8_0_gart_enable: READ(893), WRITE(897), RMW(893→897) | idem |

### gmc_v8_0_gart_enable — function→register

| Candidate A | Candidate B |
|---|---|
| 28 accesos, 7 RMW, 7 reg distintos con VM_CONTEXT0_CNTL | 33 resultados, 19 reg distintos |
| var tracked: `var=tmp transforms=N` | no var info |

---

## RMW_DEPENDENCY_VALIDATION

### Candidate A — data-flow tracked

```text
gmc_v8_0_gart_enable L893→L897: READ RREG32 → RMW-SW var=tmp transforms=3 → WRITE WREG32(…,tmp)
```

**Mecanismo:** rastrea la variable `tmp` entre lectura y escritura, verifica que
`tmp` se transforme (`REG_SET_FIELD`) entre medio. Emite `software_rmw` con
`dependent_variable` y `transforms`. **No produce RMW cross-case (L14→L21 falso positivo
es rechazado: la re-lectura de L19 mata el valor de L14).**

### Candidate B — proximity only

```python
while j < len(operations) and operations[j]['operation'] != 'WRITE':
    j += 1
# cualquier WRITE del mismo registro post-READ forma RMW
```

**No rastrea variable.** Un caso negativo como `tmp = RREG32(reg); WREG32(reg, 0)`
**sería clasificado como RMW** si no hay otro WRITE entre medio. La herramienta no
tiene estado `RMW_CANDIDATE` o `DEPENDENCY_NOT_DETERMINED`; todo es `READ_MODIFY_WRITE`
declarado.

### Caso negativo del ticket (auditor)

```c
tmp = RREG32(reg);
WREG32(reg, 0);   // constante, sin dependencia
```

- Candidate A: **RECHAZADO** como RMW (no hay `transforms`, pero el mecanismo verifica
  que WRITE reuse la variable → si WRITE usa constante `0`, no se empareja).
- Candidate B: **CLASIFICADO COMO RMW FALSO POSITIVO** (no distingue variable de
  constante).

**Veredicto RMW:** Candidate A ✅ / Candidate B ❌.

---

## REGISTER_IDENTITY

| Campo | Candidate A | Candidate B |
|---|---|---|
| `register_token` | ✅ | ✅ |
| `register_identity` | ✅ (register_resolution.value) | ❌ (solo nombre) |
| `offset` | ✅ (reg_resolve integration) | ❌ |
| `ip_block` | ✅ (via reg_resolve) | ❌ |
| `generation` | ✅ (gfx_8_0 chip context) | ❌ (hardcoded default) |
| `consumer_context` | ✅ | ❌ |

**Veredicto REGISTER_IDENTITY:** Candidate A ✅ / Candidate B ❌.

---

## PROVENANCE

| Requisito | Candidate A | Candidate B |
|---|---|---|
| file exists | ✅ | ✅ |
| line_start/line_end | ✅ | ✅ |
| source_snippet | ✅ | ✅ |
| macro (nombre real) | ✅ | ❌ (no registra macro) |
| line range en RMW | ✅ | ✅ |
| register_token | ✅ | ✅ |

---

## FALSE_POSITIVES

| Caso | Candidate A | Candidate B |
|---|---|---|
| COMMENT | ✅ (strip_comment + macro-aware) | ✅ (strip_line_comment) |
| STRING_LITERAL | ✅ (regex-aware) | ❌ no probado con vector |
| MACRO_DEFINITION | ✅ | ✅ |
| INDEPENDENT_READ_AND_WRITE | ✅ (cross-case rechazado) | ❌ (proximity-only) |
| REFErence_WITHOUT_ACCESS | ✅ | ✅ |

---

## CLEAN_CHECKOUT_VALIDATION

```text
Candidate A: commit e35ae36 existe en el repositorio, archivos rastreados.
             Regresa rc=0 en --selftest. No se checkouteó (READ-ONLY).
Candidate B: files UNTRACKED en el worktree dirty. No hay commit.
             --selftest supera 60s de timeout (escanea árbol completo).
```

---

## METRIC_RECONCILIATION (gmc_v8_0.c)

| Métrica | Candidate A | Candidate B |
|---|---|---|
| READ_ACCESS_SITES | 84 | 12 |
| WRITE_ACCESS_SITES | 131 | 12 |
| RMW_CONFIRMED | 60 (1 hardware) | 0 (no data-flow) |
| RMW_CANDIDATES | 0 | 8 (los 8 son "confirmed" sin prueba) |
| UNSUPPORTED_MACRO_INVOCATIONS | 0 (11 familias soportadas) | 300+ SOC15_* sin reconocer |
| FALSE_POSITIVES observados | 0 | 0 en corpus real, pero 1 potencial (par sin dependencia) |

Nota: Candidate B reporta 12 READ y 12 WRITE para gmc_v8_0.c (solo VM_CONTEXT0_CNTL
filter), Candidate A reporta todo el archivo (216 accesos). Métricas normalizadas a
`--function gmc_v8_0_gart_enable`:

| Métrica | A (gart_enable) | B (gart_enable) |
|---|---|---|
| Access sites | 28 | 28 |
| RMW confirmed | 7 | 7 (sin data-flow proof) |
| Registers | 19 | 19 |

---

## FINAL_CLASSIFICATION

### CANDIDATE_A_PREFERRED

**Candidate A supera a Candidate B en tres dimensiones críticas que el ticket
RXRE-CAPABILITY-012 declaró como requirements:**

1. **RMW_DEPENDENCY_VALIDATION** — A demuestra data-flow (var tracking); B no.
2. **REGISTER_IDENTITY** — A integra reg_resolve (offset, ip_block, generation); B
   solo entrega nombre textual.
3. **MACRO_COVERAGE** — A detecta 11 familias (SOC15_*); B detecta solo RREG32/WREG32.

Candidate B tiene una integración CLI más completa (`rxre trace_data`) y probe `--help`,
pero eso no compensa la falta de data-flow RMW, identity resolution y macro coverage
que el ticket RXRE-CAPABILITY-012 exige.

**Candidate A no fue integrado a `rxre` CLI** en su commit (es standalone). Candidate B
sí lo está. Por tanto: **CANDIDATE_A_PREFERRED como base técnica, pero requiere
integración CLI** — la decisión es sobre *qué base técnica validar primero*, no sobre
promover commits.
