# RXRE-012 — Auditoría funcional de `reg_resolve.py`

**Proyecto activo:** `/home/lucas/Escritorio/rxre` · rama `audit/register-fields-keying-016r` @ `ca745e9`
**Fecha:** 2026-10-10
**Estado final:** `BUG_CONFIRMED`
**Corpus:** `RESEARCH/working/linux-7.1.3` (y `RESEARCH/kernelbuild/linux-7.1.3` para `test_p003`)
**Alcance:** lectura de Git + Python. Sin escritura sobre Git, sin cambio de rama, sin acceso a hardware. La GPU integrada (`0000:00:02.0` / i915 / fb0) no fue tocada.

---

## 0. Resumen ejecutivo

`reg_resolve.py` (v1.0.0, rama de auditoría) presenta **dos defectos reproducibles** en la resolución de registros, y su consumidor `rxre_register_fields.py` (añadido por `4f05b05`, tocado por `ca745e9`=HEAD) presenta un **tercero** en la selección de cabecera `_sh_mask.h`:

| ID | Fichero | Defecto | Reproducible |
|---|---|---|---|
| **H1a** | `reg_resolve.py` | Declara `CONFLICT` y anula `value` para registros que **la propia generación objetivo** define sin ambigüedad (p.ej. `mmCB_BLEND0_CONTROL`=0xa1e0 en `gca/gfx_8_0_d.h`). | SÍ |
| **H1b** | `reg_resolve.py` | Cuando `value` se anula (conflicto sin regla de selección), `dword_index`/`byte_offset` **siguen emitiéndose** desde un `val` obsoleto: el registro se declara ambiguo y a la vez reporta un byte concreto. | SÍ |
| **H2** | `rxre_register_fields.py` (`ca745e9`) | `derive_sh_mask_header` resuelve caminos relativos contra la **raíz del proyecto rxre**, no contra `amd_root`. El `chosen["rel"]` que el propio `reg_resolve` emite es relativo a `amd_root`, así que la resolución por identidad **falla en silencio** y reactiva el barrido amplio ambiguo (304 campos / 15 cabeceras en vez de 22 / 1). | SÍ |

Se preparó una corrección **en entorno aislado** (`/home/lucas/.rxre012-fix/`, **sin tocar la carpeta activa**) que:
- retiene el valor de la generación objetivo cuando es único (coherente con `reg_resolve` v2.0.0 de `main`, que resuelve `mmCB_BLEND0_CONTROL`→0xa1e0), y
- deriva `dword_index`/`byte_offset` del valor **resuelto** (`out["value"]`), no de `val`, y
- resuelve caminos relativos contra `amd_root`.

**Verificación:** la prueba discriminante pasa de **7 fallos (rc=1)** antes del arreglo a **0 fallos (rc=0)** después; `test_p003` 27/27 verde; `test_p0_2_consumer015` con los **mismos 10 fallos preexistentes** (sin fallos nuevos); ambos `--selftest` rc=0; `trace-register` (que vive en `main`, no en esta rama) no se ve afectado — confirmado por línea base y por análisis estructural.

**El proyecto activo queda sin modificar** (`reg_resolve.py` sigue siendo SHA-256 `ec408d71…`, `rxre_register_fields.py` `f2f7363f…`; `git status` limpio; HEAD sigue siendo `ca745e9`).

---

## 1. Contrato real de resolución

### 1.1 `reg_resolve.py` (v1.0.0, la rama activa)

**Invocación pública** (`tools/reg_resolve.py`):

```text
reg_resolve.py --kernel <raiz-linux> --reg <símbolo> --gfx <gfx> [--json]
reg_resolve.py --kernel <raiz-linux> --resolve <símbolo> --gfx <gfx>
reg_resolve.py --selftest
```

- `--kernel` = raíz del árbol del kernel (p.ej. `…/linux-7.1.3`). Internamente `amd_root = <kernel>/drivers/gpu/drm/amd`.
- `--reg` = símbolo `#define` (p.ej. `mmMC_CG_DATAPORT`, `mmCB_BLEND0_CONTROL`, `mmVM_CONTEXT0_CNTL`).
- `--gfx` = generación objetivo (p.ej. `gfx_8_0`).

**Salida (`--json`):** envelope con `results[0]` que contiene:

| Campo | Tipo | Semántica |
|---|---|---|
| `symbol` | str | el símbolo pedido |
| `verdict` | str | `DEFINIDO_EN_GENERACION_OBJETIVO` / `DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO` / `PROVEN_ABSENT_EN_ASIC_REG` |
| `value` | str\|None | hex del offset resuelto, o `None` si es ambiguo/ausente |
| `chosen` | dict\|None | `{file:abs, rel:amd_root-relativo, value:int}` — la definición elegida |
| `defined_in` | list[str] | todas las `rel` donde aparece el símbolo |
| `conflict` | bool | `True` si hay >1 valor distinto **entre todas las apariciones** |
| `candidates` | list[str] | valores únicos ordenados (cuando hay conflicto) |
| `selection_rule` / `selection_evidence` | str\|dict | presentes solo cuando una regla resolvió el conflicto |
| `dword_index` / `byte_offset` | str\|None | para registros `mm*` (`dword_index_de_mm`): el índice y `índice*4` |
| `unit` / `unit_evidence` | str | unidad declarada (no deducida) |

**Lógica de resolución (`resolve_reg`):**
1. `order = [gca/{gfx}_d.h, gc/{gfx}_offset.h]`; para `gfx_8_0` **presta** además el `gmc/gmc_8_X_d.h` que `amdgpu/gmc_v8_0.c` incluye (leído del fuente C).
2. `hits` = todas las definiciones del símbolo en `asic_reg` (todas las generaciones).
3. `in_target` = `hits` cuyo `file` está en `order`; `chosen = in_target[0]` (o `None`).
4. Si `unique_values` (sobre **todos** los `hits`) > 1 → `conflict=True`, `candidates`. Reglas de selección:
   - (única, en v1.0.0) si `chosen` es un header `gmc/` y `gfx==gfx_8_0`: busca el `#include "gmc/<h>"` en `gmc_v8_0.c`; si aparece → `selection_evidence`, retiene `value`.
   - si no hay regla → `chosen=None`, `value=None`.
5. Para `mm*`: `dword_index = hex(val)`, `byte_offset = hex(val*4)` donde `val = chosen["value"] if chosen else hits[0]["value"]`.

**Contrato de `rxre_register_fields.py` (el consumidor, `4f05b05`):**
```text
rxre_register_fields.py --kernel <amd_root> --reg <REG> --gfx <gfx> [--resolved-header <d.h>] [--resolved-json <reg_resolve.json>] [--selftest]
```
- `find_register_fields(amd_root, reg, gfx, resolved_header, ip_block, ip_version)` → lista de campos.
- `derive_sh_mask_header(resolved_d_header)` → el `_sh_mask.h` homólogo (`<prefijo>_<vers>_d.h` → `<prefijo>_<vers>_sh_mask.h`, misma carpeta), o `None`.
- `find_sh_mask_by_identity(amd_root, resolved_d_header, ip_block, ip_version)` → la cabecera única compatible.
- `--resolved-json` lee `results[0].chosen.file` (**absoluto**) de la salida de `reg_resolve`.

### 1.2 Qué produce reg_resolve para el caso testigo (corpus real, medido)

`mmVM_CONTEXT0_CNTL` está definido en **11 headers con 4 valores distintos**:
- `gmc/{6_0,7_0,7_1,8_1,8_2}_d.h` → **0x504** (linaje GMC / GFX8 = el target)
- `mmhub/{1_0,9_1,9_3_0}_offset.h` → **0x06c0** (linaje MMHUB, otras generaciones)
- `gc/{9_0,9_1,9_2_1}_offset.h` → **0x0880** (linaje GC, otras generaciones)

`mmCB_BLEND0_CONTROL` está definido en **10 headers con 2 valores distintos**:
- `gca/{gfx_8_0,gfx_8_1,gfx_7_0,gfx_7_2,gfx_6_0}_d.h` → **0xa1e0** (linaje GFX, incluye el target `gca/gfx_8_0_d.h`)
- `gc/{gc_9_0,gc_9_1,gc_9_2_1,gc_10_1_0,gc_10_3_0}_offset.h` → **0x01e0** (linaje GC, otras generaciones)

`mmMC_CG_DATAPORT` está definido en **5 headers con 2 valores distintos**:
- `gmc/{6_0,7_1,8_1}_d.h` → **0xa21**; `gmc/{7_0,8_2}_d.h` → **0xa32**.

---

## 2. Rutas de código y pruebas

### 2.1 Consumidores de `reg_resolve.py` en la rama activa
- `tools/rxre/core/dispatch.py:227` — registra la capacidad `register` con `cmd=["reg_resolve.py"]` (invocado por subproceso vía `os.path.join(TOOLS, …)`).
- `tools/rxre/core/normalize.py` — `de_registro()` parsea la salida `--json`; pasa el resultado crudo (`raw=r`) **sin** indexar `dword_index`/`byte_offset`, por lo que anularlos no rompe `normalize`.
- Tests que ejercen `reg_resolve.py` por CLI: `test_p003.py` (T0301/T0302), `test_p0_2_consumer015.py`, tests de cobertura (`mutate_*`).

### 2.2 Consumidores de `rxre_register_fields.py`
- **Ninguno** en el core de `rxre` de esta rama: solo su propio `--selftest` y su CLI. (Verificado por grep: ningún `import rxre_register_fields` fuera del propio fichero.)

### 2.3 `trace-register` — **no está en esta rama**
- `grep -rln 'trace.register|trace_register|trace_data' tools/rxre` → **sin resultados** en `/home/lucas/Escritorio/rxre`.
- `find … -name test_trace_register.py` → **no existe** en el proyecto activo.
- `trace-register` vive en **`main`** (`/home/lucas/.rxre-wt/promotion-002` @ `04e1c02`), donde `tools/rxre/cli.py:146-154` lo declara como composición interna `trace_data → reg_resolve → rxre_register_fields` (`tools/rxre/commands/trace_register.py`, que **importa** los tres como módulos y llama a `find_register_fields(..., resolved_header=abs_d, ...)` con **camino absoluto** `identity["chosen_header_abs"]`).

### 2.4 Pruebas existentes y su cobertura
| Prueba | Cubre | Estado base (sin arreglo) |
|---|---|---|
| `test_p003.py::test_0301` | `mmCB_BLEND0_CONTROL`/`mmCB_BLEND1_CONTROL` @ gfx_8_0: espera `dword_index`=0xa1e0/0xa1e1 y `byte_offset`=0x28780/0x28784 | **PASA — pero solo por el defecto H1b** (el `value` está a `None` y el `dword_index` lo filtra `val` obsoleto) |
| `test_p003.py::test_0302` | `mmMC_CG_DATAPORT` @ gfx_8_0: exige `conflict=true`, `chosen` no nulo, `value` no nulo (resuelto por el `#include` de `gmc_v8_0.c`) | PASA (no se altera con el arreglo) |
| `test_p0_2_consumer015.py` | detección de ambigüedad intra-TU (FIXTURE/CLASIFICADOR) | **10/48 FALLAN** — preexistente, ajeno a `reg_resolve` (feature no implementada) |
| `reg_resolve.py --selftest` | vectores internos | rc=0 |
| `rxre_register_fields.py --selftest` | vectores A–D (usa `resolved_header` **absoluto**) | rc=0 |

**Casos no cubiertos por las pruebas existentes** (y que el audit añade):
- registro `mm*` **fuera de la generación objetivo** con conflicto trans-generacional (`mmMC_CG_DATAPORT @ gfx_9_4_0`): el `dword_index`/`byte_offset` filtrado.
- registro de la generación objetivo con valor único pero conflicto trans-linaje (`mmCB_BLEND0_CONTROL @ gfx_8_0`): el `value` anulado indebidamente.
- `resolved_header` **relativo** (la forma `chosen["rel"]` que `reg_resolve` emite): la base de resolución incorrecta (H2).

---

## 3. Comparación del arreglo existente (`4f05b05`, `ca745e9`)

**`4f05b05` — "fix: register-fields selects sh_mask.h from resolved identity"** (ancestro de HEAD):
- Añade `tools/rxre_register_fields.py` (706 inserciones). **No toca `reg_resolve.py`.**
- Introduce la selección de `_sh_mask.h` **por identidad resuelta** (en vez del primer `_sh_mask.h` que contenga el registro). Es la base correcta; su autotest (veces A–D) pasa.

**`ca745e9` (HEAD) — "fix: resolve relative paths in derive_sh_mask_header for CLI identity resolution"**:
- Modifica `rxre_register_fields.py` (+8/−1): acepta caminos relativos en `derive_sh_mask_header`.
- **Pero la base elegida es la raíz del proyecto rxre** (`project_root = abspath(join(dirname(__file__), pardir))` = `/home/lucas/Escritorio/rxre`), **no `amd_root`**. Como los headers del kernel viven bajo `amd_root` y **no** bajo la raíz del proyecto, un camino relativo (la forma `chosen["rel"]` de `reg_resolve`) se resuelve a una ruta inexistente → `derive_sh_mask_header` devuelve `None` → `find_register_fields` reactiva el barrido amplio ambiguo. **El propósito declarado del commit no se cumple para caminos relativos del árbol del kernel**: es el defecto H2.

**`main` (v2.0.0, `04e1c02`, en `promotion-002`) — referencia:**
- `reg_resolve.py` es **v2.0.0** (664 líneas de diff vs v1.0.0): añade el subsistema `REGISTER_IDENTITY` (RXRE-CAPABILITY-011) donde la identidad es `(token, ip_block, offset, generation)` y cada discriminante deja `selection_evidence`.
- En v2.0.0, `dword_index`/`byte_offset` se derivan de `v = out.get("value")` (el valor **post-conflicto**): cuando el conflicto anula `value`, `dword_index`/`byte_offset` también son `None`. **v2.0.0 no tiene H1b.**
- v2.0.0 **resuelve** `mmCB_BLEND0_CONTROL @ gfx_8_0` a `value=0xa1e0, conflict=False, selection_evidence=True, status=RESOLVED`. **v2.0.0 no tiene H1a.**
- La `rxre_register_fields.py` de `main` **sí tiene H2** (misma base `project_root`), pero es latente: `trace-register` le pasa un camino **absoluto**, por lo que nunca entra en la rama relativa.

**Conclusión de la comparación:** los defectos H1a/H1b existen **solo en v1.0.0** (rama de auditoría); `main` ya los corrigió con el subsistema REGISTER_IDENTITY. H2 existe **en ambas ramas** (latente en `main`). El arreglo que se prepara aquí es un *backport mínimo* del comportamiento correcto de v2.0.0 a v1.0.0, **sin** reimplementar todo el subsistema REGISTER_IDENTITY.

---

## 4. Casos probados y resultados

Prueba discriminante: `/home/lucas/.rxre012-scratch/probe_reg_resolve.py` (8 aserciones). Corpus real `RESEARCH/working/linux-7.1.3`.

### 4.1 Antes del arreglo (`probe_reg_resolve.py` → **rc=1, 7 fallos**)

**H1 — `mmMC_CG_DATAPORT @ gfx_9_4_0` (y `gfx_10_3_0`, `gfx_11_0_0`; no está en la generación objetivo):**
```text
verdict      = DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO
value        = None          # correcto: no está en el target
conflict     = True
candidates   = ['0xa21', '0xa32']
dword_index  = 0xa21         # ← FILTRADO de val (=hits[0]=gmc_6_0, 1º alfabético)
byte_offset  = 0x2884        # ← 0xa21*4, calculado sobre un valor NO resuelto
```
→ El registro se declara **ambiguo** (`value=None`) y a la vez se reporta un **byte offset concreto** (0x2884). Contradictorio: un consumidor que lea `byte_offset` obtiene 0x2884 aunque el registro se declaró irresoluble.

**H2 — `VM_CONTEXT0_CNTL` @ gfx_8_0, `resolved_header` relativo (`chosen["rel"]` de reg_resolve):**
```text
chosen.rel (amd_root-relativo) = include/asic_reg/gmc/gmc_8_1_d.h
derive_sh_mask_header(rel)       = None          # ← resuelve contra raíz del proyecto → no existe → None
A) resolved_header ABSOLUTO      → 22 campos,  cabecera = gmc_8_1_sh_mask.h
B) resolved_header RELATIVO      → 304 campos, 15 cabeceras (gc_9_0, gc_9_1, …, gmc_6_0, gmc_8_1, gmc_8_2, mmhub_*, …)
C) rel unido a amd_root (correcto) → 22 campos,  cabecera = gmc_8_1_sh_mask.h   (= A)
```
→ Pasar la forma relativa que **el propio reg_resolve emite** cae en el barrido amplio: **13.8× más campos**, con esquemas de **otras generaciones** mezclados. El commit `ca745e9` no logra su propósito.

### 4.2 Después del arreglo (`probe_fixed.py` → **rc=0, 0 fallos**)

**H1 corregido:**
```text
mmMC_CG_DATAPORT @ gfx_9_4_0: value=None conflict=True candidates=['0xa21','0xa32']
                                 dword_index=None byte_offset=None   # ← coherente con value=None
```

**H2 corregido:**
```text
derive_sh_mask_header(rel, amd_root) = …/asic_reg/gmc/gmc_8_1_sh_mask.h
B) resolved_header RELATIVO → 22 campos, gmc_8_1_sh_mask.h   # ← ahora = A = C
```

### 4.3 El caso `test_0301` (el que un arreglo ingenuo rompía)

El arreglo **solo** de coherencia (anular `dword_index` cuando `value` es `None`) rompía `test_p003::test_0301`, porque `mmCB_BLEND0_CONTROL @ gfx_8_0` tiene **el target definido sin ambigüedad** (0xa1e0 en `gca/gfx_8_0_d.h`) pero v1.0.0 lo declaraba conflicto y anulaba `value`; `test_0301` solo pasaba **por el filtrado** de `val`. Por eso el arreglo correcto tiene **dos partes** (ver §5):

**`mmCB_BLEND0_CONTROL @ gfx_8_0` después del arreglo completo:**
```text
FIXED v1.0.0: value=0xa1e0  conflict=True  dword_index=0xa1e0  byte_offset=0x28780
              chosen=include/asic_reg/gca/gfx_8_0_d.h  selection_evidence=True (TARGET_GENERATION_HEADER)
MAIN  v2.0.0: value=0xa1e0  conflict=False dword_index=0xa1e0  byte_offset=0x28780
              selection_evidence=True
```
→ `value`/`dword_index`/`byte_offset`/`selection_evidence` **coinciden con main v2.0.0**. Solo difiere `conflict` (True en v1.0.0 = declara la diferencia trans-linaje y la resuelve con regla; False en v2.0.0 = no la declara). Esa diferencia es semántica preexistente de v1.0.0 y es **requerida** por `test_0302` (que exige `conflict=true`).

### 4.4 Regresiones (entorno aislado `/home/lucas/.rxre012-regtree/`, corpus por symlink solo-lectura)

| Prueba | Antes (activo, sin arreglo) | Después (arreglo aislado) | Veredicto |
|---|---|---|---|
| `test_p003.py` | 27/27 rc=0 | **27/27 rc=0** | ✅ sin regresión; `test_0301` ahora pasa **correctamente** (valor retenido, no filtrado) |
| `test_p0_2_consumer015.py` | 10/48 rc=1 | **10/48 rc=1 — `diff` de líneas de fallo: IDENTICAL_FAILURES** | ✅ mismos 10 fallos preexistentes, **cero nuevos** |
| `reg_resolve.py --selftest` | rc=0 | **rc=0** | ✅ |
| `rxre_register_fields.py --selftest` | rc=0 | **rc=0** | ✅ |
| `python3 -m py_compile` (ambos) | — | **COMPILE_OK** | ✅ |

### 4.5 `trace-register` (en `main`, `promotion-002` @ `04e1c02`)

Línea base con los ficheros originales de `main` (`python3 tools/rxre/cli.py trace-register --target VM_CONTEXT0_CNTL --kernel … --file drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c --function gmc_v8_0_gart_enable --gfx gfx_8_0 --json`):
```text
TRACE_REGISTER_BASELINE_RC = 0
stdout = 48911 bytes, sha256 = 6a1ad89cf742a8feb1708c5586c21e750b81d191728bbe1050c99a3b960125e3
envelope.status      = ok
identity.status      = RESOLVED
identity.chosen_header = include/asic_reg/gmc/gmc_8_1_d.h
identity.value       = 0x504   identity.dword_index = 0x504   identity.byte_offset = 0x1410
identity.conflict    = False
schema.status        = RESOLVED   (sh_mask_provenance.header_files = 1 fichero: gmc_8_1_sh_mask.h)
fields               = list[22]   field_count = 22
relations.software_rmw_count = 1
```

**¿Por qué el arreglo no puede romper `trace-register`?**
1. `trace-register` **no está en la rama activa** (`ca745e9`); vive en `main` (`04e1c02`). El arreglo está aislado en `/home/lucas/.rxre012-fix/` y **no toca los ficheros de `main`**.
2. `trace-register` corre con **`reg_resolve.py` v2.0.0 de `main`**, que **ya** deriva `dword_index`/`byte_offset` de `out.get("value")` (sin H1b) y **ya** resuelve el target por REGISTER_IDENTITY (sin H1a). H1 es un *no-op* sobre v2.0.0.
3. `trace-register` llama a `find_register_fields(..., resolved_header=<absoluto>, ...)`. H2 (base de caminos relativos) **nunca se activa** con un camino absoluto.
4. El arreglo v1.0.0 resuelve el **mismo target** de `trace-register` (`mmVM_CONTEXT0_CNTL @ gfx_8_0`) a **`value=0x504, dword_index=0x504, byte_offset=0x1410`** — **idéntico** a main v2.0.0 (medido en §4.6).

### 4.6 Cierre del bucle: el target de `trace-register` resuelto por la rama arreglada

```text
FIXED v1.0.0 (mmVM_CONTEXT0_CNTL @ gfx_8_0): value=0x504  conflict=True  dword_index=0x504  byte_offset=0x1410  chosen=gmc_8_1_d.h  (vía #include de gmc_v8_0.c)
MAIN  v2.0.0 (mmVM_CONTEXT0_CNTL @ gfx_8_0): value=0x504  conflict=False dword_index=0x504  byte_offset=0x1410  (vía REGISTER_IDENTITY)
→ value / dword_index / byte_offset IDÉNTICOS.
```

---

## 5. Defecto reproducible y corrección preparada

### 5.1 Defectos confirmados (reproducibles, corpus real)

- **H1a** — anulación indebida de `value` para registros de la generación objetivo con valor único. Reproducible: `reg_resolve.py --kernel <corpus> --reg mmCB_BLEND0_CONTROL --gfx gfx_8_0 --json` → `value=None, conflict=True, candidates=['0x1e0','0xa1e0']` aunque `gca/gfx_8_0_d.h` lo define sin ambigüedad como 0xa1e0.
- **H1b** — filtrado de `dword_index`/`byte_offset` desde `val` obsoleto. Reproducible: `… --reg mmMC_CG_DATAPORT --gfx gfx_9_4_0 --json` → `value=None` pero `dword_index='0xa21'`, `byte_offset='0x2884'`.
- **H2** — base incorrecta para caminos relativos en `derive_sh_mask_header`. Reproducible: `find_register_fields(amd_root, "VM_CONTEXT0_CNTL", "gfx_8_0", resolved_header="include/asic_reg/gmc/gmc_8_1_d.h")` → 304 campos / 15 cabeceras en vez de 22 / `gmc_8_1_sh_mask.h`.

### 5.2 Corrección (en `/home/lucas/.rxre012-fix/`, **no aplicada** al proyecto activo)

**`reg_resolve.py`** — dos cambios:
1. **Regla de selección de la generación objetivo** (nueva rama `elif` en el bloque de conflicto): se calcula `target_values` sobre `in_target` (solo los headers de la generación objetivo). Si `chosen` es `gca/{gfx}_d.h` o `gc/{gfx}_offset.h` **y** `len(target_values)==1`, se retiene el valor con `selection_evidence` de tipo `TARGET_GENERATION_HEADER`. (Los demás candidatos pertenecen a **otras** generaciones, no al target.) Esto alinea el `value` de v1.0.0 con v2.0.0 y hace que `test_0301` pase **correctamente**.
2. **Coherencia `dword_index`/`byte_offset`**: se derivan de `v = out.get("value")` (post-conflicto), no de `val`. Cuando el conflicto anula `value`, ambos son `None`. Idéntico al enfoque de v2.0.0.

**`rxre_register_fields.py`** — un cambio:
- `derive_sh_mask_header(resolved_d_header, amd_root=None)`: si el camino es relativo y hay `amd_root`, lo resuelve contra `amd_root` (la base correcta para `chosen["rel"]`); si no hay `amd_root`, conserva la base anterior (raíz del proyecto) por compatibilidad. `find_sh_mask_by_identity` le pasa `amd_root`, que `find_register_fields` ya tenía.

**Hash de los ficheros arreglados:**
```text
e0ce27063c2b9c57580b9088013c577161a5ef1f5460b2eeb39dae0e5a484959  /home/lucas/.rxre012-fix/reg_resolve.py
277f2bab392f4ee92b86a81ce167617db67a8f6c43ba6386e2573aa1d0767c46  /home/lucas/.rxre012-fix/rxre_register_fields.py
```
**El proyecto activo queda intacto:**
```text
ec408d712f17673d27296e91fb819da0d427333a519e280d08c573a389819870  /home/lucas/Escritorio/rxre/tools/reg_resolve.py   (sin cambios)
f2f7363fa11b9266e033b1aa2461f429c81343a20629dad6182ef4746c1467c9  /home/lucas/Escritorio/rxre/tools/rxre_register_fields.py (sin cambios)
git status --porcelain → (vacío) ; git rev-parse HEAD → ca745e9130e9e993f8310eba98e9c9afbf879b34
```

### 5.3 Limitaciones del arreglo (registradas, no ocultas)
- El arreglo conserva la semántica v1.0.0 de **declarar** `conflict=True` ante diferencias trans-linaje y resolverla con regla (no la suprime como hace v2.0.0). Es intencional: `test_0302` exige `conflict=true`. Quien quiera la semántica v2.0.0 (`conflict=False`) debe backportear el subsistema REGISTER_IDENTITY completo, no este parche mínimo.
- Caso límite no cubierto: un registro definido en **dos** headers de la **misma** generación objetivo con valores distintos (p.ej. `gca/gfx_8_0_d.h`=X y el `gmc_8_1_d.h` prestado=Y, X≠Y). En ese caso `len(target_values)==2`, la regla nueva no se activa y `value` se anula (comportamiento conservador: conflicto genuino intra-target). No se ha encontrado tal caso en el corpus; se deja como limitación explícita.
- H2 también está presente en la `rxre_register_fields.py` de `main` (latente, porque `trace-register` usa caminos absolutos). El arreglo de aquí corrige la rama de auditoría; `main` necesitaría el mismo cambio si algún día se le pasa un `resolved_header` relativo.

---

## 6. Recomendación técnica

1. **Aplicar el arreglo aislado** (`/home/lucas/.rxre012-fix/reg_resolve.py` y `rxre_register_fields.py`) al proyecto activo **bajo autorización**, o — preferible — **backportear `reg_resolve.py` v2.0.0 de `main`** (el subsistema REGISTER_IDENTITY), que es la corrección completa y la que ya usa `trace-register`. El parche mínimo de aquí es un *backport* válido y de bajo riesgo; el backport de v2.0.0 es la solución de fondo.
2. **No tratar `test_p003::test_0301` como prueba verde del estado actual**: pasa **por el defecto** H1b. Tras el arreglo pasa **correctamente** (valor retenido por regla de generación objetivo). Cualquier futura auditoría de `reg_resolve` debe usar el discriminante `value=None ⇒ dword_index=None` (§4.1) y `mmCB_BLEND0_CONTROL @ gfx_8_0 ⇒ value=0xa1e0` (§4.3) como vectores.
3. **Corregir H2 en `main` también** (misma base `amd_root` en `derive_sh_mask_header`), aunque sea latente: es un defecto de consistencia de contrato que puede activarse con cualquier `resolved_header` relativo.
4. **`test_p0_2_consumer015.py` (10/48)** queda fuera de este incidente: sus fallos son de FIXTURE/CLASIFICADOR (ambigüedad intra-TU), una feature no implementada, **no** de `reg_resolve`. No debe bloquear la aplicación del arreglo.

---

## 7. Siguiente tarea concreta

**Autorizar y aplicar** uno de los dos caminos (§6.1) en un worktree aislado, y luego:
1. Copiar `reg_resolve.py` y `rxre_register_fields.py` arreglados a `tools/` del worktree (o backportear v2.0.0).
2. Re-ejecutar, en ese worktree: `test_p003.py` (esperado 27/27), `test_p0_2_consumer015.py` (esperado: los mismos 10 fallos preexistentes, sin nuevos), `reg_resolve.py --selftest` y `rxre_register_fields.py --selftest` (esperado rc=0), y `probe_reg_resolve.py` (esperado rc=0, 0 fallos).
3. En `promotion-002` (`main`), re-ejecutar la suite A–J de `test_trace_register.py` (esperado 10/10) para confirmar que `trace-register` sigue verde con la corrección H2 si se aplica también a `main`.
4. Registrar el hallazgo y la transición de estado en el grafo de `findings/` (de `OPEN` a `RESOLVED` para H1a/H1b/H2), con los hashes de los artefactos de este informe.

---

## 8. Estado final

```text
ESTADO_FINAL = BUG_CONFIRMED
```

**Justificación:** tres defectos reproducibles con evidencia de corpus real (H1a, H1b en `reg_resolve.py` v1.0.0; H2 en `rxre_register_fields.py` desde `ca745e9`), demostrados con una prueba discriminante que **falla antes** (7 fallos, rc=1) y **pasa después** (0 fallos, rc=0) de una corrección preparada y validada en entorno aislado, sin modificar la carpeta activa, sin romper `test_p003` (27/27), sin introducir fallos nuevos en `test_p0_2_consumer015` (mismos 10 preexistentes), y sin afectar a `trace-register` (que vive en `main` y corre sobre v2.0.0 con caminos absolutos). El arreglo queda listo en `/home/lucas/.rxre012-fix/` pendiente de autorización para aplicarse.

**Lo que se demostró vs. lo que queda indeterminado:**
- **Demostrado:** los tres defectos y su reproducción; la corrección mínima y su validación; la equivalencia del `value`/`dword_index`/`byte_offset` arreglado con `main` v2.0.0 para `mmCB_BLEND0_CONTROL` y `mmVM_CONTEXT0_CNTL`; la no-regresión.
- **Indeterminado:** si existe en el corpus un registro con conflicto genuino **intra-target** (dos headers de la misma generación objetivo con valores distintos) — se barrió por la regla conservadora (§5.3) y no se encontró, pero no se agotó el espacio de todos los `(ip_block, generación)`.
- **No hecho (por restricción):** aplicar el arreglo al proyecto activo, backportear v2.0.0 completo, y correr la suite A–J de `trace-register` con la corrección H2 sobre `main` — quedan como siguiente tarea (§7), pendientes de autorización.
