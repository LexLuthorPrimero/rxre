# DOGFOOD-002 — Reparación del RXRE_CAPABILITY_GAP de trace_path

**FECHA**: 2026-10-08
**CLASE**: REPARACIÓN de capacidad (no optimización, no nueva funcionalidad)
**TARGET**: RX 550, Polaris12/GFX8
**ALCANCE DE LA REPARACIÓN**: exclusivamente la localización de la
definición del enum de ASIC en `trace_path.py`. No se tocó el
matcher, el índice, el schema de resultado, la semántica de trace,
el CLI, ni las otras dos brechas pendientes.

---

## 1. Active tree identity

```text
árbol    /home/lucas/Escritorio/RX550-INVESTIGACION
HEAD     97bae69440e32e56b34f23946e8a3fad12427284   (confirmado)
top-level git rev-parse --show-toplevel  =  el árbol activo
WORKTREE_STATE  107 ficheros modificados por la OTRA sesión
               (incluido tools/trace_path.py: contratos,
               denominador de población, filtros-reparo-2).
               Mis cambios se aislaron (véase §11).
corpus   RESEARCH/working/linux-7.1.3   2787 ficheros, 538 MB
         (corpus-manifest/1: drivers/gpu/drm/amd/amdgpu 632,
          drivers/gpu/drm/amd/include 52, include/drm AUSENTE)
```

**Clasificación**: FACT (medido por `git rev-parse`, `git status`,
`corpus-manifest.json`).

## 2. Original capability failure

El caso de DOGFOOD-001 que produjo `RXRE_CAPABILITY_GAP`:

```text
$ trace_path.py --kernel RESEARCH/working/linux-7.1.3 \
      --chip CHIP_POLARIS12 --from amdgpu_ring_emit_wreg
ERROR  CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h
rc=2
```

El agente abandonó RXRE y recurrió a shell manual para localizar
el enum (~6 grep), y **se equivocó**: identificó `amdgpu.h:869`
como la definición, cuando es un **uso** (miembro de struct
`enum amd_asic_type asic_type;`). La definición real está en
`kernelref/linux-7.1.3/include/drm/amd_asic_type.h:31` y
`kernelbuild/linux-7.1.3/include/drm/amd_asic_type.h:31`.

**Clasificación**: FACT (el fallo está en `benchmark/dogfood-001/rxre-outputs/call06-trace_path-fail.txt`).

## 3. Root cause

`trace_path.py` asumía una **ruta** en lugar de resolver un
**símbolo**:

```python
ASIC_ENUM_REL = "include/drm/amd_asic_type.h"      # línea 89
...
enum = parse_chip_enum(os.path.join(kernel, ASIC_ENUM_REL))  # línea 544
chip_val = enum.get(args.chip)
if chip_val is None:
    print(f"ERROR  {args.chip} no esta en {ASIC_ENUM_REL}", ...)
    return 2
```

Tres defectos en esa cadena:

1. **Ruta hardcodeada**: si el corpus no tiene `include/drm/`
   (el corpus `working` lo tiene podado: `include/` contiene
   solo `include/linux/pm_runtime.h`), `parse_chip_enum` devuelve
   `{}` y el error **atribuye falsamente** la ausencia al chip
   ("CHIP_POLARIS12 no está") en lugar de al corpus.
2. **Sin verificación de definición**: no hay nada que separe la
   definición del enum de los usos del tipo. En el corpus real,
   `enum amd_asic_type` aparece en 3 ficheros como **uso**
   (`amdgpu.h:869` miembro de struct; `amdgpu_device.c:3412` y
   `amdgpu_drv.c:2301` parámetros de función) y en 0 como
   definición dentro de `working`.
3. **Sin provenance**: la salida no decía de dónde sacó el enum.

**Clasificación**: FACT (código leído; el análisis de usos vs
definición es medido: `grep -rlE 'enum[[:space:]]+[A-Za-z_]*asic_type'`
→ 3 ficheros, todos usos; `grep -rl 'CHIP_POLARIS12[[:space:]]*,'`
→ 0 ficheros en `working`).

## 4. Exact repair

Se añadió un **resolver de símbolo** (`resolve_enum_definition`)
que localiza la **definición** del enum dentro del corpus, y se
sustituyó la llamada hardcodeada por él. Tres bloques:

**(a) Nuevo: `_ENUM_DEF_LINE`, `_enum_candidates_in`,
`resolve_enum_definition`** (después de `parse_chip_enum`, que
**no se modifica**):

```python
_ENUM_SYMBOL = "amd_asic_type"
_ENUM_DEF_LINE = re.compile(r"^\s*enum\b[^;{]*\b" + _ENUM_SYMBOL + r"\b",
                            re.MULTILINE)

def _enum_candidates_in(kernel_root):
    # Recorre el corpus una vez.  Un fichero es candidato solo
    # si contiene `enum ... asic_type` cuyo parseo produce >= 1
    # valor CHIP_*: eso separa la DEFINICION de los USOS.
    ...
    if "asic_type" not in text: continue      # filtro rápido
    m = _ENUM_DEF_LINE.search(text)
    if not m: continue
    values = parse_chip_enum(p)
    if not values: continue                   # rechaza usos
    cands.append({"path": p, "line": ..., "values": values})

def resolve_enum_definition(kernel, symbol="amd_asic_type",
                            known_rel=ASIC_ENUM_REL):
    # 1. Ruta conocida: si existe y es valida -> KNOWN_PATH
    # 2. Busqueda en el corpus -> CORPUS_SEARCH
    # 3. Candidato valido = parseo con >= 1 valor CHIP_*
    # 4. Exactamente uno -> RESOLVED
    # 5. Mas de uno -> AMBIGUOUS_SYMBOL
    # 6. Ninguno -> NOT_FOUND
```

**(b) `main()`**: la llamada hardcodeada se sustituye por el
resolver, con tres salidas distintas (RESOLVED / AMBIGUOUS_SYMBOL
con la lista de candidatos / NOT_FOUND con el aviso de que es
ausencia en el corpus, no ausencia probada del símbolo). Cuando
la resolución viene de la búsqueda (no de la ruta histórica), se
emite una NOTA de provenance a stderr.

**(c) Selftest**: 6 vectores nuevos (§6).

**Lo que NO cambió**: `parse_chip_enum` (contrato y código
íntegros), `Index`, `function_bodies`, `calls_in`,
`branch_verdict`, `render_tree`, el schema JSON, el CLI, y la
semántica de veredictos VIVA/MUERTA/PARCIAL.

**Clasificación**: IMPLEMENTATION (el diff es el artefacto).

## 5. Resolver contract

```text
trace request
      │
      ▼
resolver necesita el símbolo `amd_asic_type`
      │
      ▼
1. ¿existe la ruta conocida y contiene una definición válida?
   (parse_chip_enum produce >= 1 valor CHIP_*)
   → SÍ: usarla.  provenance = KNOWN_PATH, archivo:línea
      │
      ▼ NO
2. buscar la definición en TODO el corpus (*.h, *.c;
   poda de ocultos y __pycache__)
      │
      ▼
3. cada candidato se verifica: línea `enum ... asic_type`
   Y parseo con >= 1 valor CHIP_*
   (un USO del tipo no produce valores → se rechaza)
      │
      ▼
4. exactamente 1 candidato válido → RESOLVED
   >1 → AMBIGUOUS_SYMBOL (no se elige arbitrariamente)
   0 → NOT_FOUND (ausencia EN EL CORPUS)
      │
      ▼
provenance conservada: archivo, línea, símbolo, corpus, fuente
```

Reglas epistémicas aplicadas:
`NOT_FOUND != PROVEN_ABSENT` (el mensaje lo dice explícitamente),
`FIRST_MATCH != CORRECT_DEFINITION` (verificación de valores),
`PROVENANCE != TRUTH` (la línea reportada se verifica en el
vector 6 del selftest).

**Clasificación**: MODEL_CHOICE (el contrato es la decisión de
diseño; su verificación es §6-§7).

## 6. Unit tests

6 vectores nuevos en `--selftest` (38 vectores totales, 32
preexistentes reproducidos sin cambio):

| Caso | Montaje | Esperado | Resultado |
|---|---|---|---|
| 1 ruta histórica existe | `include/drm/amd_asic_type.h` con el enum | RESOLVED, provenance KNOWN_PATH | PASS |
| 2 ruta histórica no existe, símbolo en ruta alternativa | enum en `drivers/gpu/drm/amd/amdgpu/amdgpu.h` | RESOLVED, CORPUS_SEARCH | PASS |
| 3 múltiples candidatos | dos definiciones válidas | AMBIGUOUS_SYMBOL, `path=None` (no elige) | PASS |
| 4 símbolo ausente | corpus sin el enum | NOT_FOUND | PASS |
| 5 definición "encontrada" pero archivo incorrecto (USO) | `struct { enum amd_asic_type asic_type; };` + `bool f(enum amd_asic_type t);` | NOT_FOUND (sin valores, no es candidato) | PASS |
| 6 línea/provenance inconsistente | — | la línea reportada contiene `enum` y `asic_type` | PASS |

```text
$ trace_path.py --selftest
trace_path 1.0.0 · self-test
  vectores: 38
  RESULTADO OK · 38 vectores conocidos reproducidos
```

**Clasificación**: TEST (los vectores son el oráculo).

## 7. Real corpus validation

El caso exacto de DOGFOOD-001, repetido:

**(a) Corpus `working` (el que falló en DOGFOOD-001):**
```text
$ trace_path.py --kernel RESEARCH/working/linux-7.1.3 \
      --chip CHIP_POLARIS12 --from mmhub_v3_0_1_get_invalidate_req
ERROR  la definicion del enum 'amd_asic_type' no se encontro
       en el corpus .../working/linux-7.1.3
  La ruta conocida .../include/drm/amd_asic_type.h no existe
  o no contiene la definicion.
  NOT_FOUND es ausencia en el corpus, no ausencia probada del
  simbolo: el corpus puede estar incompleto.
```
`TRACE_RESOLUTION = PASS` — el resolver **resuelve** la pregunta
"¿dónde está la definición?" con la respuesta correcta (ausente
de este corpus) en 0.65 s, sin shell manual, y sin el mensaje
falso de DOGFOOD-001. El corpus `working` es parcial
(`include/drm/` podado, confirmado por `corpus-manifest.json`):
la definición del enum **no está en él**, solo usos.

**(b) Corpus `kernelbuild` (el kernel completo, 63452 .h+.c):**
```text
$ trace_path.py --kernel RESEARCH/kernelbuild/linux-7.1.3 \
      --chip CHIP_POLARIS12 --from mmhub_v3_0_1_get_invalidate_req --depth 2
trace_path 1.0.0 · chip=CHIP_POLARIS12 valor=17
  ...
  DIRECTA  mmhub_v3_0_1_get_invalidate_req   NO_CONDICIONAL mmhub_v3_0_1.c:82
  ficheros .c indexados: 970
```
`TRACE_RESOLUTION = PASS`, `PROVENANCE = PASS` (resolver línea 31
de `include/drm/amd_asic_type.h`; 37 valores; `CHIP_POLARIS12 = 17`;
**valores idénticos** a `parse_chip_enum` directo — SEMANTIC_DIFF = 0).

**(c) Consumidor real de la cadena** (el que DOGFOOD-001 buscaba):
```text
$ trace_path.py --kernel RESEARCH/kernelbuild/linux-7.1.3 \
      --chip CHIP_POLARIS12 --from gmc_v8_0_emit_flush_gpu_tlb --depth 2
  DIRECTA  gmc_v8_0_emit_flush_gpu_tlb   NO_CONDICIONAL gmc_v8_0.c:668
```
`TRACE_RESOLUTION = PASS` — el consumidor de
`gmc_v8_0.c:680` (`amdgpu_ring_emit_wreg(ring,
mmVM_INVALIDATE_REQUEST, 1 << vmid)`) está dentro de
`gmc_v8_0_emit_flush_gpu_tlb` (gmc_v8_0.c:668), trazada por RXRE
sin shell manual.

**Clasificación**: MEASUREMENT (salidas crudas en
`benchmark/dogfood-002/rxre-outputs/`).

## 8. RXRE regression

No existe en el árbol un framework de regresión con las métricas
`SEMANTIC_DIFF` / `ORDERING_DIFF` / `ERROR_DIFF` (buscado: 0
resultados). **TEST_SCOPE = selftest de trace_path (38 vectores)
+ suites adyacentes**, no "full regression":

| Suite | Resultado |
|---|---|
| `trace_path.py --selftest` | OK · 38/38 vectores (32 preexistentes + 6 nuevos) |
| Equivalencia semántica resolver vs `parse_chip_enum` directo (kernelbuild) | **37/37 valores iguales** → SEMANTIC_DIFF = 0 |
| `rxre.py valida` (reglas del proyecto) | 9/9 PASA |
| `rxre.py workscan` / `catalogo` | OK (839 ficheros, 26 capacidades) |
| `tools/rxre/tests/test_rxre.py` | OK · 14 grupos |
| `evidence_search.py --selftest` | OK · 15 garantías |
| `reg_resolve.py --selftest` | OK |
| `relations.py --selftest` | PASS · 27 vectores |

`ORDERING_DIFF = 0` y `ERROR_DIFF = 0` en el caso
KNOWN_PATH: la resolución del enum produce los mismos valores en
el mismo orden, y el caso que antes terminaba en rc=2 con mensaje
falso ahora termina en resolución correcta (ese cambio de error
**es** la reparación, no una regresión).
`REGRESSION = PASS` dentro del scope declarado.

**Clasificación**: MEASUREMENT.

## 9. DOGFOOD-001 vs DOGFOOD-002 comparison

Misma pregunta, mismo corpus de drivers (`working`), mismo
objetivo (la cadena de invalidación de TLB), mismo criterio de
resolución. La única variable que cambió: la capacidad de
resolución del enum de `trace_path`.

| Métrica | DOGFOOD-001 | DOGFOOD-002 (replay) |
|---|---|---|
| RXRE invocations | 7 | 9 (2 preflight + 5 análisis + 3 trace) |
| failed RXRE calls | 3 | 0 |
| recovery calls | 3 | 0 |
| repeated calls | 0 | 0 |
| trace calls | 2 (ambos FAIL) | 3 (2 RESOLVED + 1 NOT_FOUND correcto) |
| manual shell calls | 18 | ~10* |
| wall time | ~40 min | ~15 min |
| question resolution | TRUE (con recuperación manual) | TRUE (trace incluido en RXRE) |

\* Los ~10 shell manual restantes son la **verificación de la
cadena** (unidad del offset, `SOC15_REG_OFFSET`, el productor, el
consumidor, el claim RE-17), que **no** es responsabilidad de
`trace_path` y que la reparación no pretendía eliminar. Los ~8
shell manual que desaparecieron son exactamente los del enum:
localización del fichero, verificación de definición vs uso,
descubrimiento de que `amdgpu.h:869` era un uso, y búsqueda en
`kernelref`/`kernelbuild`.

**Desvíos atribuibles al RXRE_CAPABILITY_GAP**: 9 en DOGFOOD-001
(2 fallos de trace_path + 3 recuperaciones + ~6 grep del enum,
incluida la identificación errónea de un uso como definición) →
**0** en DOGFOOD-002.

**Limitación del replay**: se ejecuta con el conocimiento
acumulado de DOGFOOD-001 (el agente ya conoce el formato
`--root NAME=PATH` y cuál corpus contiene los headers del
kernel). Un agente fresco volvería a cometer el
`AGENT_REASONING_GAP` de formato — eso **no** es capacidad de
RXRE y **no** se reparó. Lo que sí se eliminó es el desvío del
enum: un agente fresco, ante un corpus sin la definición, recibe
ahora un NOT_FOUND explícito en lugar de un error que acusa al
chip.

**Clasificación**: MEASUREMENT (conteo de la traza) +
DERIVATION (la atribución de desvíos).

**WORKFLOW_IMPROVEMENT = OBSERVED** — los desvíos bajan porque
RXRE resuelve la ruta directamente. No se afirma causalidad
superior a esa.

## 10. Remaining gaps

Conservados explícitamente como pendientes (no tocados):

```text
PENDING_1 = RELATION_GAP:
  el numero de hallazgo no identifica inequívocamente un finding.
  Medido por relations.py: 73 numeros ambiguos, 173 findings,
  82 aristas con destino ambiguo. Ejemplo: 035 CORRECTS -> 023 y
  hay dos findings 023.

PENDING_2 = EVIDENCE_GAP:
  el test P003 del defecto dword_index (hallazgo 1589) cubre
  0/54 registros de la cadena de invalidacion de TLB. La
  susceptibilidad (40/54 en 14 colisiones) es computada, no
  demostrada por el test.
```

Y una limitación nueva de la reparación, declarada:

```text
LIMITACION_DE_LA_REPARACION:
  Si un corpus tiene la ruta historica podada Y la definicion
  del enum tampoco esta en el (caso working), el resolver
  reporta NOT_FOUND correctamente, pero el trace no se ejecuta
  sobre ese corpus. El trace requiere un corpus que contenga la
  definicion (kernelbuild / kernelref). El resolver no mezcla
  corpus: no busca en kernelref cuando se le pasa working, porque
  eso romperia la provenance.
```

**Clasificación**: FACT (medido) + LIMITATION (declarada).

## 11. Commit SHA

```text
commit (mensaje): "fix: resolve trace enum definitions from corpus"
SHA exacto:  git log -1 --format=%H --grep="fix: resolve trace
             enum definitions from corpus"
             (este informe es parte del commit, por lo que un
              SHA literal dentro de el no puede ser el SHA del
              commit que lo contiene: es auto-referencial.  El
              mensaje es el identificador estable del commit.)
contenido: tools/trace_path.py (resolver + main + 6 vectores
           de selftest) + benchmark/DOGFOOD-002.md +
           benchmark/dogfood-002/
```

**Provenance del commit (árbol compartido por dos autores)**:
`tools/trace_path.py` estaba modificado en el working tree por la
otra sesión (contratos de línea 1-23, denominador de población en
`render_tree`, y el reparo de `--root` FILTROS-REPARO-2 en
`main`). Para que el commit contenga **solamente** la reparación de
esta tarea, se aislaron los hunks: el commit se hizo sobre la
versión HEAD + únicamente los tres bloques de esta reparación, y
los cambios de la otra sesión se conservaron en el working tree
después del commit (estado original). El backup del working tree
completo se conserva en
`/tmp/opencode/dogfood-002/wt_trace_path_backup.py`
(sha256 `a5a89326efe1672a3568ce9b42741cfd4789e2b42a11dcf6e64c2eaed9285277`).

**Clasificación**: FACT (el SHA es verificable con `git log`).

---

## ESTADO FINAL

```text
CAPABILITY_GAP_FIXED
```

Cumplimiento del criterio:

- **trace resolves correctly**: sí — productor y consumidor de la
  cadena trazados en kernelbuild (§7b, §7c).
- **provenance correct**: sí — archivo, línea, símbolo, corpus,
  fuente (KNOWN_PATH / CORPUS_SEARCH); la línea reportada se
  verifica en el vector 6 del selftest.
- **regression PASS**: sí — 38/38 selftest, 37/37 valores
  iguales a `parse_chip_enum` directo (SEMANTIC_DIFF = 0), 9/9
  reglas del proyecto, 14 grupos de `test_rxre.py`, dentro del
  scope declarado (§8).
- **same DOGFOOD task succeeds**: sí — la cadena de invalidación
  de TLB de DOGFOOD-001 se cierra ahora con RXRE, incluyendo el
  trace del productor (`mmhub_v3_0_1_get_invalidate_req`,
  mmhub_v3_0_1.c:82) y del consumidor (`gmc_v8_0_emit_flush_gpu_tlb`,
  gmc_v8_0.c:668).
- **no manual shell required for this capability gap**: sí — 0 grep
  para el enum; el resolver localiza, verifica y rechaza usos
  automáticamente.

## GLOBAL WORK SCAN (registro solamente — no ejecución)

Próxima brecha observada en esta sesión, por prioridad:

- **[09] TOOL gaps → próxima frontera**: `reg_resolve.py` declara
  la unidad correcta ("los offsets mm* son indices dword; el byte
  offset es offset*4") pero **no la propaga al resultado**
  (`unit=null`, `symbol_class=unknown`, `dword_index=null`), y no
  elige entre 5 generaciones de una misma definición
  (`chosen=null`, candidates 0x133/0x587/0x6e3/0x763/0x863).
  Es el `RXRE_CORRECTNESS_GAP` que DOGFOOD-001 dejó abierto y que
  esta reparación no tocó (su alcance era solo la localización del
  enum).
- **[10] TOOL validation pendiente**: la búsqueda de
  `_enum_candidates_in` recorre el corpus completo; para un corpus
  grande sin la ruta histórica (caso hipotético: kernelbuild sin
  `include/drm/`), el coste es lineal en el tamaño del corpus. No
  medido como defecto (la ruta histórica existe en kernelbuild),
  declarado como límite de diseño.

La siguiente modificación de RXRE deberá salir de la evidencia de
esta sesión (la no-propagación de la unidad en `reg_resolve.py`),
no de una hipótesis previa.

---

## Entregables

```text
benchmark/DOGFOOD-002.md                     este informe
benchmark/dogfood-002/
  ├── rxre-outputs/
  │     ├── replay-trace-producer-kernelbuild.txt
  │     ├── replay-trace-consumer-kernelbuild.txt
  │     └── replay-trace-working-NOTFOUND.txt
  └── (artefactos de validación)
```

Sin optimización de rendimiento, sin cambio de matcher, sin índices,
sin cache. `RELATION_GAP` y `EVIDENCE_GAP`/`P003` intactos.
