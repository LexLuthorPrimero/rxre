# RXRE — RX550 Reverse Engineering Engine

Punto de entrada único para que una IA investigue la AMD Radeon RX 550
(Polaris12 / GFX8) sin saber qué script existe ni qué flags tiene cada uno.

**Entrada/salida:** `tools/rxre/api/machine.py` lee un request JSONL por `stdin`
y devuelve un envelope JSONL por `stdout`. Las órdenes (`op`) son:
`backends, experiment, explain, lessons, ops, plan, reflect, research, run, saturate`.

Ejemplos (entrada única por línea):

```bash
# listar backends/capacidades y su estado en vivo
echo '{"op":"backends"}' | python3 tools/rxre/api/machine.py

# leer un registro de la GPU (requiere root: MMIO de amdgpu es root-only)
echo '{"op":"run","capability":"gpu.register_read","pci_address":"0000:01:00.0","register_name":"mmGRBM_STATUS"}' | sudo -E RXRE_DB=/tmp/rxre_demo.sqlite PYTHONPATH=tools:tools/rxre python3 tools/rxre/api/machine.py

# reconstruir evidencia por result_id (clave estable entre tablas)
echo '{"op":"explain","result_id":"<result_id>"}' | python3 tools/rxre/api/machine.py
```

> **Estado actual (`main` @ `53173f2`, RXRE-CORE-CAUSAL-002):** 26 suites verdes;
> evento durable (`execution_events`); `trace_id` operativo. La superficie y el
> estado de las capacidades dependen del *registry*: consúltalos en vivo con
> `op=backends` y en `RXRE-CORE-CAUSAL-002_REPORT.md`. Lo que no cambia es el
> contrato (envelope de cuatro estados).

## Qué es y qué no es

**Es** una capa de despacho y normalización. **No** reescribe ninguna de las
~220 herramientas de `tools/`: las invoca, comprueba que responden y traduce su
salida a un formato único. El registro de herramientas es `tools/toolreg.py`,
que ya existía y sigue siendo la fuente única. RXRE no añade un segundo catálogo.

## Capacidades

RXRE declara **24 adapters** en `tools/rxre/backends/dispatch.py::ADAPTERS`. Cada
adapter enlaza una capacidad a un *producer* y una lista de parámetros
obligatorios; nada que no esté allí se ejecuta (§21: la allow-list vive en el
*registry*, no en el dispatch). Familias:

- **binario** (rizin / radare2 / capstone): `binary.inspect`, `binary.functions`,
  `binary.sections`, `binary.imports`, `binary.exports`, `binary.strings`,
  `binary.symbols`, `binary.basic_blocks`, `binary.disassemble`,
  `binary.disassemble_func`, `binary.xrefs`, `binary.callgraph`, `binary.cfg`,
  `binary.dataflow`, `binary.decompile`.
- **fuente** (coccinelle): `source.semantic_search`.
- **conocimiento** (sqlite, `core/store.py`): `rxre.create_finding`,
  `rxre.get_finding`, `rxre.list_finding_relations`,
  `rxre.create_finding_relation`, `rxre.list_findings`,
  `rxre.search_findings`, `rxre.evaluate_applicability`,
  `rxre.plan_investigation`.
- **GPU** (umr): `gpu.register_read`.

El estado en vivo (AVAILABLE / PARTIAL / NOT_DETERMINED) de cada backend, con su
motivo de bloqueo, se obtiene con `echo '{"op":"backends"}' | python3
tools/rxre/api/machine.py`. `angr` y `rz-ghidra` están declarados como
`NOT_DETERMINED` (test_dispatch004).

Verificación individual documentada con evidencia ejecutable (verificado sobre
este mismo árbol): `binary.decompile` ejecuta Ghidra 12.1.4 de verdad sobre
`/bin/ls` (test_decomp003, **23/23**, pseudocódigo de 1680 líneas con la firma
`uVar*`/`iVar*` de Ghidra); `gpu.register_read` lee MMIO con `umr -r` sobre la
RX550 de este host (test_umr_hardware002, **11/11**, `mmGRBM_STATUS=0x3028` y
`mmMC_VM_FB_LOCATION=0xf47ff400`, reconstruibles con `explain`); `trace_id` y el
cruzado `result_id`/`operation_id` son reconstruibles (test_r001_trace_id,
**27/27**; test_opencode_trace007, **18/18**). El lote rápido de regresión
(run_baseline.py, 13 suites) es **13/13 verde**. El conjunto: **26 suites
verdes** sobre `main@53173f2`.

## El contrato: un envelope, cuatro estados

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "operation": "search",
  "target": "VM_CONTEXT0_CNTL",
  "results": [],
  "evidence": [],
  "provenance": [],
  "limitations": [],
  "tools_used": []
}
```

Las nueve claves base existen **siempre**, incluso cuando `results` está vacío.
Además, los adapters añaden `capability`, `ejecutada`, `producer_ejecutado`,
`rc`, `operation_id`, `persistido`, `nota_persistencia` y `limitations` según el
contrato de `backends/contract.py` y `backends/dispatch.py::ejecutar`.

| `status` | significa | rc |
|---|---|---|
| `ok` | produjo resultados | 0 |
| `empty` | se ejecutó y no encontró | 0 |
| `blocked` | **no se pudo ejecutar**, y se dice por qué | 2 |
| `error` | la herramienta falló | 1 |

### La regla que impone el envelope

**`empty` nunca se convierte en ausencia.** Es la clase de defecto que este
proyecto cuenta siete veces, y el envelope la cierra por construcción: un `empty`
sale siempre con `limitations` explicando que la herramienta corrió y no
encontró, y que eso **no** es que no exista.

`blocked` existe porque `empty` no alcanza. Y `blocked` **no** es
`NOT_DETERMINED`: `blocked` significa "se comprobó la precondición y no se
cumple" (p.ej. falta de root para MMIO de amdgpu); `NOT_DETERMINED` significa
"no se pudo verificar".

Un `results` que contiene `verdict: NO_ENCONTRADO` **tampoco** cuenta como
resultado: `trace` lo sube a `limitations` y devuelve `empty`.

## Códigos de salida

```
0   ok o empty     (vacío NO es fallo: mira `status`)
1   error
2   blocked        (la precondición no se cumple; NO se ejecutó)
```

## Pruebas

```bash
python3 tools/rxre/tests/run_baseline.py                                  # 13 suites rápidas (sin HW ni Ghidra)
python3 tools/rxre/tests/test_decomp003.py                                # Ghidra real /bin/ls: 23/23 (~20s)
python3 tools/rxre/tests/test_umr_hardware002.py                          # GPU umr RX550: 11/11 (root)
python3 tools/rxre/tests/test_r001_trace_id.py                            # trace_id: 27/27
python3 tools/rxre/tests/test_opencode_trace007.py                        # traza + cruce OpenCode<->RXRE: 18/18
```

La suite son **32 archivos `test_*.py`** en `tools/rxre/tests/`. Estado
**medido** el 2026-10-15 sobre el árbol de trabajo:

```text
=== BASELINE 31 passed / 1 failed / 0 errored (of 32) ===
```

El único fallo es `test_container1632.py`, **preexistente y ajeno a este
trabajo**: se cuelga descomprimiendo `amdgpu.ko.zst` sin `zstd` disponible.
No se ha investigado. Antes de esta sesión eran 29 ficheros / 26 verdes según
el mensaje de commit de `main@53173f2`; ese número es **evidencia histórica**
(§86) y no una observación vigente.

`tools/rxre/tests/test_cli009.py` añade **71 checks** de integración del CLI
(71/71 verdes), incluidos tests de regresión **probados por mutación**: al
reintroducir cada bug, la suite baja a 66/67, 60/61 o 66/67 con el mensaje
exacto del defecto.

Los vectores ejecutan
el producer de verdad donde corresponde (Ghidra sobre `/bin/ls`, `umr -r` sobre
la RX550, rizin/radare2 sobre binarios); `binary.decompile` incluye además un
modo `fixture_json` que simula al *producer* solo para probar la clasificación
(ET_REL vs EMPTY) sin arrancar la JVM, pero su nivel C ejecuta Ghidra real
(test_decomp003). `run_baseline.py` vive committeado en `tools/rxre/tests/` (runner reproducible:
descubre `test_*.py` + ejecuta con RXRE_DB aislada). Las suites que tocan la
RX550 (umr) requieren root (`sudo -S`, pw vía stdin al prompt; no se persiste secret en disco).

## CLI unificado (`./rxre`)

El entry point `./rxre` (en la raíz del repositorio) es un router operativo
que expone todas las capacidades de RXRE como subcomandos. No importa nada:
reenvía a `tools/rxre/api/machine.py` por JSONL, o invoca herramientas
auxiliares por subprocess.

### Modos de salida

| Flag | Salida |
|---|---|
| (por defecto) | legible para humanos |
| `--json` | JSON estructurado (stdout) |
| `--human` | texto legible (explícito) |

Los diagnósticos siempre van a stderr. Stdout se mantiene limpio para JSON/JSONL.

### Códigos de salida

```
0  ok o empty   (vacío NO es fallo: mira `status` en el JSON)
1  error
2  blocked     (la precondición no se cumple; NO se ejecutó)
```

### Subcomandos del motor (reenvían a machine.py)

Estos subcomandos construyen una petición JSONL y la envían a `machine.py`.
Los argumentos `--key value` se convierten en campos del request JSON.

```bash
./rxre ops                              # lista las 10 operaciones del engine
./rxre capabilities                     # lista las 25 capabilities con estado
./rxre backends                         # alias de capabilities
./rxre run binary.inspect --artefacto /bin/ls
./rxre run binary.inspect --artefacto /bin/ls --json
./rxre plan binary.decompile --question "qué función escribe este registro"
./rxre explain res_abc123               # reconstruye la cadena de evidencia
./rxre experiment --capability binary.inspect --question "..." --prediction 0x0800
./rxre reflect --feedback "r2 -v falló" --outcome failure
./rxre research --kind frontier --text "..." --status OPEN --target binary.cfg
./rxre saturate --target binary.cfg
./rxre lessons --ejecutar true
```

### Subcomandos de integración (invocan scripts existentes)

Estos subcomandos ejecutan herramientas auxiliares con contrato verificado.

```bash
./rxre selftest     # ejecuta tools/rxre/tests/run_baseline.py
./rxre inventory    # ejecuta RXRE/tools/rxre_boot.py (19 vectores, READONLY)
./rxre verify       # ejecuta las 5 herramientas FASE 0 (boot, frontier,
                    #   contracts, deleg, touch) — todas READONLY
./rxre workscan     # cuenta hallazgos, repeticiones, authorship en findings/
./rxre mutate       # mutation testing (mutate_reg_resolve, mutate_relations,
                    #   mutate_target)
```

**Contratos verificados antes de integrar:**

| Herramienta | READONLY | WRITES_GPU | TOUCHES_INTEGRATED |
|---|---|---|---|
| `rxre_boot.py` | yes | no | no |
| `rxre_frontier.py` | yes | no | no |
| `rxre_contracts.py` | yes | no | no |
| `rxre_deleg.py` | yes | no | no |
| `rxre_touch.py` | no* | no | no |
| `mutate_reg_resolve.py` | sí (scratch /tmp) | no | no |
| `mutate_relations.py` | sí (scratch /tmp) | no | no |
| `mutate_target.py` | no** | no | no |

\* `rxre_touch.py` declara `WRITES_FILES=indeterminado`: puede escribir archivos
de salida con `--out`. No toca la GPU ni la iGPU.
\** `mutate_target.py` hace backup/restore de `target.py` in place. Pre-check de
`git status` advierte si hay cambios no staged. `RAIZ` se deriva de `__file__`
(corregido de hardcodeado).

### `mutate` — estado medido (2026-10-15)

```text
mutate_reg_resolve  4/4 con comportamiento esperado
mutate_relations    4/4 con comportamiento esperado
mutate_target       4/4 con comportamiento esperado
./rxre mutate       rc=0
```

`target.py` verificado **intacto** tras el run: `git status` vacío, hash
`1eaf88ceae0a9a5c2687907c80b8359f9fa04f3f7d92b934bf42bb9d661b0739`.

Dos reparaciones documento los hallazgos 1628 y 1629:

- El catálogo de `mutate_target.py` estaba escrito contra una versión anterior
  de `target.py`: el mapa se llama `_MAPA_PCI` (no `MAPPING`) y el formato de
  provenance cambió de f-string a `%`. **2 de 4 mutantes no se aplicaban.**
- El mutante **M3 sobrevive, y está correctamente clasificado como mutante
  EQUIVALENTE** en hosts de un solo target, no como agujero del oráculo. Medido:
  con M3 aplicado, el triple `(bdf, vendor, device)` sigue siendo reconstruible
  desde las entradas [1] y [2] de la provenance.

**Riesgo residual conocido:** `mutate_target.py` escribe `target.py` in-place
y el backup/restore **no es atómico**. Si el proceso muere entre la escritura
del mutante y el restore, el fichero queda mutado. Recuperación: el backup
sobrevive en `/tmp/opencode/mutate-target-scratch/target.py.bak`, y
`git checkout` es la vía de referencia mientras el fichero esté versionado.
Un `try/finally` en el propio script no se ha implementado.

### `workscan` — estado medido (2026-10-15)

```text
=== WORKSCAN (2 directorios) ===
  06-INGENIERIA-INVERSA/findings     md=39   numerados=39   max=1632
  findings                           md=23   numerados=12   max=1615

  ficheros .md (union):    62
  hallazgos numerados:      51
  numeros distintos:        48
  repeticiones:             3
  ficheros de mas:          6
  MAXIMO ESCRITO:           1632
  MAXIMO RESERVADO:         1626  (trabajo gastado, 867 reservas)
  por autor:
    AGENTE-INSTR: 6
    SISTEMA AUTÓNOMO RXRE: 14
  sin autor:               31
```

Reporta **dos magnitudes distintas** a propósito: lo **escrito** (ficheros que
existen) y lo **reservado** (trabajo gastado según `RESERVAS.ledger`).
Presentarlas como una sola sobrestimaría el progreso.

La versión anterior escaneaba **un solo** directorio y por eso reportaba
`max=1615` cuando el máximo real de la unión era `1623`: subreportaba en 8.
Ver hallazgo 1627.

### Modo JSONL passthrough (compatible)

Si no se pasa un subcomando conocido y stdin tiene datos, el CLI reenvía
todo a `machine.py` sin procesar — idéntico al comportamiento anterior:

```bash
echo '{"op":"ops"}' | ./rxre
echo '{"op":"run","capability":"binary.inspect","artefacto":"/bin/ls"}' | ./rxre
printf '{"op":"ops"}\n{"op":"ops"}\n' | ./rxre
```

La detección no depende de `stdin.isatty()` únicamente: lee stdin realmente;
si está vacío y hay un arg posicional desconocido, devuelve error rc=2.

### Riesgos y limitaciones

- **`selftest` incluye tests que requieren root** para acceso GPU (umr). Sin
  root, `run_baseline.py` usa `timeout=300s` por test y los marca FAIL/TIMEOUT.
- **`toolkit_cross.py`** tiene un `ROOT` hardcodeado a `~/Escritorio/RX550-INVESTIGACION/`.
  **No está integrado** en el CLI: las herramientas FASE 0 solo lo *leen* como
  texto (no lo importan, no lo ejecutan). Ver `rxre_contracts.py` para el
  análisis estático.
- **`mutate_target.py`** modifica `tools/rxre/core/target.py` in-place
  (backup/restore). Se verifica con `git status` antes de ejecutar.



`RESEARCH/working/linux-7.1.3` está **incompleto**: su `include/` solo contiene
`linux/`, no `drm/`. Por eso `trace` y `xref` apuntan a
`RESEARCH/kernelbuild/linux-7.1.3`, que sí tiene `include/drm/`. Medido, no
supuesto: con `working`, `trace_path.py` falla con
`CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h`. (Nota: `RESEARCH/` y
las herramientas legacy —`trace_path.py`, `xref.py`, `pm4ops.py`…— están fuera
del árbol comiteado de `main`; el motor RXRE actual se describe en §3.)

## Limitaciones conocidas

- **`xref` está bloqueada** en este árbol (`status: blocked`, rc=2). El AST está
  incompleto y `xref.py` no completa el build porque eso es una escritura. Es
  correcto que lo diga, y no se intenta esquivarlo. **Nota distinta: `binary.xrefs`**
  (el adapter rizin/r2 `axtj`) **sí está operativo** vía CLI desde 2026-10-16.
- **`binary.xrefs` y `binary.callgraph` estaban rotas por CLI** hasta 2026-10-16.
  El defecto (`artefacto.encode()` trataba el path string como contenido) se
  confirmó via CLI: `binary.xrefs` sobre `/bin/ls` devolvía `empty` y ahora
  devuelve `ok` con 74 xrefs. El patrón correcto es el de `rz_cfg.py`: validar
  `os.path.isfile(artefacto)`, hashear con `sha256_de`, pasar el path directo
  a `argv`. Ver finding `1616-rxre-bms-ext-002`.
- **`pm4` devuelve texto, no JSON**, porque `pm4ops.py` imprime una tabla. Se
  devuelve como un resultado de `kind: "texto"` y se dice que no es JSON, en vez
  de fingir que sí.
- **`gpu.register_read` requiere root.** El acceso a MMIO de amdgpu vía `umr -r`
  exige `geteuid()==0` (CAP_SYS_ADMIN). El adapter devuelve `blocked` sin root;
  no hay forma de leer registros de la GPU sin él (test_umr_hardware002 valida
  el camino root + RX550, y la hard boundary de la Intel `0000:00:02.0`).
- **`binary.decompile` no decompila módulos kernel (`ET_REL`).** Ghidra 12
  importa el ELF pero su loader produce 0 funciones para `ET_REL`
  (`amdgpu.ko` → `REPORT: Import succeeded` + 0 funciones). El adapter clasifica
  eso como `unsupported` (no `empty`): para `.ko` se usan `binary.functions` /
  `binary.inspect` (rizin/radare2 sí leen `ET_REL`) o el BTF de
  `/sys/kernel/btf/amdgpu`.
- **RXRE no revalida las herramientas de fondo.** Cada una trae su propio
  self-test. Revalidar 220 aquí sería duplicar `toolreg.py` y mentir sobre quién
  es responsable de qué.
- **No hay estado entre llamadas.** Sin sockets, sin demonios. El envelope lleva
  lo necesario para el siguiente paso.
- **Repositorio multi-worktree activo.** `main` es el baseline publicable
  (`53173f2`). Las ramas `capability/*`, `repair/*`, `migration/*` viven en
  worktrees separados y comparten la base de evidencia viva
  (`tools/rxre/storage/rxre.sqlite3`); no forman parte de `main`.

## Los ocho principios (RXRE-ECO-001) — estado auditado 2026-10-16

Los ocho principios (`body/mind/soul/earth/fire/air/water/aether` en
`backends/adapters/ocho_principios.py`) son un **auditoría post-hoc**, no un
gate automático en dispatch. `op: audit` verifica que una operación REAL cumpla
el contrato epistemico antes de marcarla cerrada.

### Mejora 2026-10-16 (RXRE-BMS-EXT-002-F)

**Problema:** `binary.xrefs` y `binary.callgraph` devolvían `empty` vía CLI
(`artefacto.encode()` trataba el path como contenido). El audit reportaba:
CUERPO violation (sin precheck), TIERRA violation (provenance como string),
ALMA violation (sin pregunta patron), ETER not_proven (dato aislado).

**Fix aplicado a 4 archivos:**

| Archivo | Cambio | Principios arreglados |
|---|---|---|
| `adapters/rz_xrefs.py` | path/bytes, precheck, provenance dict, raw fields | 8/8 |
| `adapters/rz_callgraph.py` | misma corrección (mismo defecto sistémico) | 8/8 |
| `adapters/umr_read.py` | backend_existe verified antes de early-returns | CUERPO |
| `api/machine.py` | BODY→MIND loop: reflect en early return; invalid_input vs blocked | CUERPO, MIND |

### Resultados de audit (2026-10-16)

`binary.xrefs` via CLI sobre `/bin/ls`:
```
operacion_cerrada: True
estado: ok
cumplen: [CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER]
violacion: []
```

`binary.callgraph` via CLI sobre `/bin/ls`:
```
operacion_cerrada: True
estado: ok
cumplen: [CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER]
violacion: []
```

## Estado

RXRE-CORE-CAUSAL-002 (`main` @ `53173f2`). 26 adapters declarados, 26+ suites de
prueba (31/32 baseline verdes; test_container1632 requiere zstd). El audit de
los 8 principios (RXRE-ECO-001) aprobado para `binary.xrefs` y `binary.callgraph`
vía CLI. La frontera de ingreso hardware verificada es `gpu.register_read` sobre Polaris12
por `umr -r` (root): el camino de lectura real de registros de la GPU RX 550.
