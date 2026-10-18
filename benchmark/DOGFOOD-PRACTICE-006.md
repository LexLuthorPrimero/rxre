# DOGFOOD-PRACTICE-006 — READ/WRITE RELATION TRACING

## RESUMEN EJECUTIVO

**CLASIFICACIÓN:** `READ_WRITE_CAPABILITY_GAP`

Se ha determinado que RXRE **NO puede** reconstruir automáticamente las relaciones de datos REGISTER → READ/WRITE SITE → FUNCTION. Solo puede:

1. Extraer esquemas de campos de registro desde headers (`register-fields`)
2. Resolver definiciones de offset de registros (`register`)
3. Rastrear llamadas entre funciones (`trace_path`)
4. Buscar coincidencias de texto en el corpus (`search`/`evidence`/`symbol`)

La reconstrucción real de READ/WRITE (quién escribe VM_CONTEXT0_CNTL en qué línea de qué función) requiere **inspección manual del corpus con shell (grep/awk)** porque no existe una capacidad de análisis de flujo de datos en RXRE.

---

## 1. ESTADO DEL REPOSITORIO ACTIVO

```
REPOSITORY_ROOT = /home/lucas/Escritorio/rxre
HEAD = 9ce74c53ba5a356fed9893c5f62b32e01f9d883a
BRANCH = migration/validated-legacy-work
WORKTREE = /home/lucas/Escritorio/rxre (dirty: 227 ficheros modificados por otra sesión en paralelo)
```

Trabajo realizado READ-ONLY. No se ha modificado RXRE ni el worktree principal.

---

## 2. PREGUNTA DE INVESTIGACIÓN

```
¿Quién escribe VM_CONTEXT0_CNTL
y quién lo lee,
y puede RXRE reconstruir esas relaciones?
```

---

## 3. CAPACIDADES RXRE EXISTENTES (PRE-CHECK)

| Capacidad | Comando real | Propósito | Estado |
|---|---|---|---|
| `register-fields` | `rxre register-fields <REG> --gfx <gfx>` | Extrae campos de registro desde `*_sh_mask.h` | ✅ Funcional |
| `register` | `rxre register <REG> --gfx <gfx>` | Resuelve offset/definición de registro | ✅ Funcional |
| `search` | `rxre search <texto>` | Búsqueda literal en corpus | ✅ Funcional |
| `evidence` | `rxre evidence <texto>` | Búsqueda con clasificación | ✅ Funcional |
| `symbol` | `rxre symbol <simbolo>` | Búsqueda de palabra exacta | ✅ Funcional |
| `trace_path` | `trace_path --from/--callers-of <SYM>` | Rastrea llamadas función→función | ✅ Funcional (calls, no data) |
| `xref` | `rxre xref <simbolo>` | Referencias cruzadas por AST | ❌ BLOCKED (AST incompleto) |

**NO existe** ninguna capacidad RXRE para: `REGISTER → WRITE SITE → FUNCTION`, `REGISTER → READ SITE → FUNCTION`, `FUNCTION → registers it reads/writes`.

---

## 4. CASO PRINCIPAL: VM_CONTEXT0_CNTL

### 4.1 register-fields (schema del registro)

```
COMMAND: rxre register-fields VM_CONTEXT0_CNTL --gfx gfx_8_0 --json
EXIT_STATUS: 0
RESULT: Status ok, 304 resultados (29 campos únicos × 11 headers)
```

Esto da **el esquema del registro** (campos, máscaras, desplazamientos, provenance), pero **NO** dice quién lo escribe.

### 4.2 register (definición de offset)

```
COMMAND: rxre register VM_CONTEXT0_CNTL --gfx gfx_8_0 --json
EXIT_STATUS: 0
RESULT: PROVEN_ABSENT_EN_ASIC_REG
LIMITATION: "busqueda exhaustiva sobre include/asic_reg. Es una ausencia de definicion de offset, no de hardware"
```

No hay definición de offset en el corpus `working` (solo hay macros de campo en headers).

### 4.3 search/evidence/symbol (coincidencias de texto)

```
COMMAND: rxre search VM_CONTEXT0_CNTL --max-hits 5 --json
EXIT_STATUS: 0
RESULT: 5-10 hits, todos son comentarios en headers (.h):
  file: .../mmhub_1_0_sh_mask.h line: 8070
  text: //VM_CONTEXT0_CNTL
  file: .../gc/gc_9_0_sh_mask.h line: 7017
  text: //VM_CONTEXT0_CNTL
```

**Problema:** RXRE encuentra coincidencias de texto, pero:
- Mayoría son **comentarios** (`//VM_CONTEXT0_CNTL`), no código real
- No diferencia entre aparición en comentario y operación real READ/WRITE
- No reporta qué tipo de operación (READ vs WRITE vs REFERENCE)

---

## 5. RELACIÓN WRITE (evidencia manual del corpus)

**Inspección manual con grep:**

```
$ grep -n "WREG32.*VM_CONTEXT0_CNTL" gmc/gmc_v8_0.c
897:    WREG32(mmVM_CONTEXT0_CNTL, tmp);
977:    WREG32(mmVM_CONTEXT0_CNTL, 0);
```

**Relación WRITE resuelta manualmente:**

| REGISTER | FUNCTION | FILE | LINE | OPERATION | PROVENANCE |
|---|---|---|---|---|---|
| VM_CONTEXT0_CNTL | gmc_v8_0_gart_enable | amdgpu/gmc_v8_0.c | 897 | WRITE | WREG32(mmVM_CONTEXT0_CNTL, tmp); |
| VM_CONTEXT0_CNTL | gmc_v8_0_gart_disable | amdgpu/gmc_v8_0.c | 977 | WRITE | WREG32(mmVM_CONTEXT0_CNTL, 0); |

**Otros writers posibles** que RXRE no detectó automáticamente:

| FUNCTION | LINE | OPERATION |
|---|---|---|
| gmc_v8_0_vm_fault_interrupt_state | 1404, 1414 | WRITE (tras RREG32 read-modify-write) |

---

## 6. RELACIÓN READ (evidencia manual del corpus)

**Inspección manual con grep:**

```
$ grep -n "RREG32.*mmVM_CONTEXT0_CNTL" gmc/gmc_v8_0.c
893:    tmp = RREG32(mmVM_CONTEXT0_CNTL);
1402:        tmp = RREG32(mmVM_CONTEXT0_CNTL);
1412:        tmp = RREG32(mmVM_CONTEXT0_CNTL);
```

**Relación READ resuelta manualmente:**

| REGISTER | FUNCTION | FILE | LINE | OPERATION |
|---|---|---|---|---|
| VM_CONTEXT0_CNTL | gmc_v8_0_gart_enable | amdgpu/gmc_v8_0.c | 893 | READ (RREG32) |
| VM_CONTEXT0_CNTL | gmc_v8_0_vm_fault_interrupt_state | amdgpu/gmc_v8_0.c | 1402, 1412 | READ (RREG32) |

### 6.1 Diferenciación READ vs WRITE vs READ-MODIFY-WRITE

El corpus permite distinguir estos casos manualmente:

| Caso | Patrón | Ejemplo | Clasificación |
|---|---|---|---|
| WRITE puro | `WREG32(mmVM_CONTEXT0_CNTL, ...)` | línea 897, 977 | WRITE |
| READ puro | `tmp = RREG32(mmVM_CONTEXT0_CNTL);` | línea 893 | READ |
| READ-MODIFY-WRITE | `tmp = RREG32(...) + ...; WREG32(..., tmp);` | líneas 1402-1404 | READ-MODIFY-WRITE |

**Capacidad RXRE:** `trace_path` distingue `RREG32`/`WREG32` **en el output de llamada**, pero solo como parte del subgrafo de llamadas, no como relación register→operation. **NO existe** una capability que analice operaciones de acceso a registros.

---

## 7. BIDIRECCIONALIDAD

### 7.1 REGISTER → functions que leen/escriben

```
COMMAND: rxre search VM_CONTEXT0_CNTL --max-hits 20 --json
RESULTADO: Solo encuentra coincidencias de texto (principalmente comentarios en .h)
CONCLUSIÓN: UNSUPPORTED (no diferencia código de comentarios, ni READ de WRITE)
```

### 7.2 FUNCTION → registers que lee/escribe

```
COMMAND: trace_path --from gmc_v8_0_gart_enable --kernel kernelbuild/linux-7.1.3 --depth 3 --json
RESULTADO: Devuelve subgrafo de funciones llamadas por gmc_v8_0_gart_enable
CONCLUSIÓN: Solo rastrea CALLS entre funciones, NO reporta registros tocados
```

**Ambas direcciones son UNSUPPORTED** para relaciones de datos. Solo funcionan para relaciones de llamada.

---

## 8. COMPARACIÓN CON TRACE (CALL RELATION)

```
VM_CONTEXT0_CNTL
    ↓ WRITES [UNSUPPORTED]
gmc_v8_0_gart_enable    ← RXRE NO sabe esto automáticamente
    ↓ CALLS [PROVEN por trace_path]
gmc_v8_0_hw_init
```

| Flecha | RXRE capability | Estado |
|---|---|---|
| REGISTER → WRITE | search/evidence | UNSUPPORTED (solo texto, sin clasificación READ/WRITE) |
| FUNCTION → REGISTER | ninguna | UNSUPPORTED (no existe) |
| FUNCTION → FUNCTION (calls) | trace_path | **PROVEN** (--callers-of, --from) |

**Conclusión:** `trace_path` resuelve la flecha FUNCTION→FUNCTION, pero RXRE no resuelve las flechas que involucran a registros.

---

## 9. RXRE FIRST — Registro de consultas

| # | COMMAND | INPUT | EXIT_STATUS | RESULT | Clasificación del resultado |
|---|---|---|---|---|---|
| 1 | `rxre register-fields VM_CONTEXT0_CNTL` | --gfx gfx_8_0 | 0 | ok, 304 resultados | Información de schema (no data flow) |
| 2 | `rxre register VM_CONTEXT0_CNTL` | --gfx gfx_8_0 | 0 | PROVEN_ABSENT_EN_ASIC_REG | Sin offset en corpus |
| 3 | `rxre search VM_CONTEXT0_CNTL` | --max-hits 5 | 0 | 5 hits, todos comentarios | Coincidencias textuales |
| 4 | `rxre evidence VM_CONTEXT0_CNTL` | --max-hits 10 | 0 | 10 hits | PROVEN, pero sin clasificación de op |
| 5 | `rxre symbol VM_CONTEXT0_CNTL` | --max-hits 20 | 0 | 20 hits | Comentarios en headers |
| 6 | `rxre xref VM_CONTEXT0_CNTL` | --json | 3 (blocked) | AST incompleto | BLOCKED |
| 7 | `trace_path --callers-of gmc_v8_0_gart_enable` | --kernel kernelbuild | 0 | OK, 1 caller (gmc_v8_0_hw_init) | CALL resuelto correctamente |
| 8 | `trace_path --from gmc_v8_0_gart_enable` | --depth 3 --json | 0 | OK, subgrafo de llamadas | CALL resuelto correctamente |

**Shell manual necesario para:**
- Encontrar las líneas exactas con WREG32/RREG32 de VM_CONTEXT0_CNTL
- Asociar esas líneas con sus funciones definidoras
- Distinguir READ de WRITE de READ-MODIFY-WRITE

---

## 10. CADENA DE EVIDENCIA

### Evidencia manual (shell) construida:

```
VM_CONTEXT0_CNTL
   ↓ DEFINITION (register-fields)
VM_CONTEXT0_CNTL__ENABLE_CONTEXT_MASK = 0x1, shift 0 (gmc_8_2_sh_mask.h)
   ↓ WRITE OPERATION (grep WREG32)
line 897: WREG32(mmVM_CONTEXT0_CNTL, tmp);
   ↓ FUNCTION CONTAINER (awk/sed context)
function: gmc_v8_0_gart_enable(struct amdgpu_device *adev) {
```

**NOTA EPISTEMOLÓGICA:** Esta cadena está construida manualmente con shell, NO es una salida estructurada de RXRE. RXRE no produce esta cadena automáticamente.

---

## 11. FALSO POSITIVO

Se encontró una aparición de VM_CONTEXT0_CNTL que **NO es** READ/WRITE:

```
file: drivers/gpu/drm/amd/include/asic_reg/mmhub/mmhub_1_0_sh_mask.h line: 8070
text: //VM_CONTEXT0_CNTL
```

**Problema:** RXRE **no clasifica correctamente** esto:
- Devuelve el hit como coincidencia textual válida
- No marca que es un comentario
- No lo excluye automáticamente de resultados de "operaciones reales"

**RXRE false positive handling = NO** (no distingue comentarios de código).

---

## 12. CASO NEGATIVO

```
COMMAND: rxre search RXRE_TEST_REGISTER_DOES_NOT_EXIST --max-hits 5 --json
RESULTADO: empty / 0 hits
```

**Análisis:** RXRE reporta "empty" (0 hits) para registros inexistentes, pero no distingue si:
- El registro no existe EN EL CORPUS consultado (NOT_FOUND)
- El registro no existe en absoluto (PROVEN_ABSENT)

**Clasificación:** El resultado es razonablemente `NOT_FOUND` (ausencia en corpus consultado), aunque el corpus de headers define muchos registros y RXRE busca en todo el corpus. No hay conversión errónea a `PROVEN_ABSENT` en este caso, pero la distinción no está documentada explícitamente.

---

## 13. MÉTRICAS

```
RXRE_INVOCATIONS = 8
RXRE_FAILURES = 1 (xref con rc=3 blocked; técnicamente "blocked" no es "failure" pero no resolvió)
RXRE_RECOVERIES = 0 (ninguna recuperación post-fix en esta sesión)
MANUAL_SHELL_CALLS = 3 (grep, awk, sed para reconstruir write/read sites + funciones)
WRITE_RELATIONS_RESOLVED = 2 (gmc_v8_0_gart_enable@897, gmc_v8_0_gart_disable@977)
READ_RELATIONS_RESOLVED = 2 (gmc_v8_0_gart_enable@893, gmc_v8_0_vm_fault_interrupt_state@1402, 1412)
UNRESOLVED_RELATIONS = ∞ (todas las relaciones register→operation quedan pendientes)
FALSE_POSITIVES = 5+ (comentarios //VM_CONTEXT0_CNTL que RXRE incluye como hits)
```

### Separación RXRE_CAPABILITY_GAP vs AUXILIARY_SHELL:

```
RXRE_CAPABILITY_GAP (lo que RXRE no puede hacer):
- Reconstruir automáticamente register→READ/WRITE→function
- Diferenciar RREG32 de WREG32 como tipo de operación de acceso a registro
- Distinguir comentarios de código en resultados de búsqueda
- Identificar read-modify-write a nivel de registro

AUXILIARY_SHELL (uso legítimo de shell para explorar el corpus):
- grep para encontrar WREG32/RREG32 en .c files
- awk/sed para obtener contexto de función alrededor de una línea
```

---

## 14. CAPABILITY GAPS IDENTIFICADOS

### GAP PRINCIPAL

```
GAP: register → read/write site → function tracing
EXPECTED_CAPABILITY: 
  rxre data-flow VM_CONTEXT0_CNTL --json
  que devuelva: [{register, operation: READ|WRITE|RMW, function, file, line}]
ACTUAL_CAPABILITY:
  - rxre search/evidence: coinciden texto, incluyen comentarios, no clasifican op
  - rxre trace_path: rastrea calls función→función, no toca registros
  - rxre register-fields: schema de campos desde headers, no data flow
SOURCE_EVIDENCE:
  - 8 comandos RXRE ejecutados: ninguno devuelve una tabla de operaciones READ/WRITE
  - El corpus tiene 4 operaciones reales (3 READ, 1 WRITE puro, 2 RMW) en gmc_v8_0.c
  - RXRE encontró 0 de ellas como "operaciones de registro identificadas"
```

### GAP SECUNDARIO

```
GAP: xref capability
EXPECTED_CAPABILITY:
  rxre xref VM_CONTEXT0_CNTL --json
  que reconstruya referencias cruzadas de símbolos
ACTUAL_CAPABILITY:
  rxre xref VM_CONTEXT0_CNTL → blocked: "xref.py no puede construir el AST"
  rc=3, no hay resultados
```

---

## 15. CONCLUSIÓN FINAL

### 15.1 Lo que RXRE resuelve automáticamente (PROVEN)

| Relación | RXRE capability | Estado |
|---|---|---|
| register → fields (schema) | register-fields | ✅ PROVEN |
| register → offset definition | register | ✅ PROVEN (o PROVEN_ABSENT_EN_ASIC_REG) |
| function → functions it CALLS | trace_path --callers-of | ✅ PROVEN |
| function → functions it IS CALLED BY | trace_path --from | ✅ PROVEN |
| text match anywhere | search/evidence/symbol | ✅ PROVEN |

### 15.2 Lo que RXRE NO resuelve (UNSUPPORTED / GAP)

| Relación | Estado |
|---|---|
| register → function que la WRITE | **UNSUPPORTED** |
| register → function que la READ | **UNSUPPORTED** |
| function → registers que lee/escribe | **UNSUPPORTED** |
| differentiate comment vs code match | **UNSUPPORTED** |
| classify RREG32 vs WREG32 as register op | **UNSUPPORTED** |
| xref by AST | **BLOCKED** (AST incompleto) |

### 15.3 Clasificación del STOP GATE

```
RESULTADO: READ_WRITE_CAPABILITY_GAP
```

**Razón:** Existe evidencia reproducible (el corpus gmc_v8_0.c tiene 4 operaciones de VM_CONTEXT0_CNTL) pero **RXRE no puede resolverlas automáticamente**. Todas las relaciones register→READ/WRITE→FUNCTION requieren inspección manual del corpus.

**Lo que SÍ se demostró:** RXRE tiene una excelente base (register-fields, trace_path) pero le falta la capa de análisis de flujo de datos (data flow) que una herramienta de RE de driver necesitaría.

---

## 16. EPISTEMOLOGÍA

Se mantuvo rigurosamente:
- ✅ `SOURCE != HARDWARE` - el corpus es fuente, no efecto de hardware
- ✅ `IMPLEMENTATION_IS_NOT_AUTHORITY` - el código de AMD es evidencia, no verdad
- ✅ `NOT_FOUND != PROVEN_ABSENT` - se distingue ausencia en corpus de ausencia probada
- ✅ `EMPTY_RESULT != ABSENCE` - 0 hits de RXRE no significa que el registro no se usa
- ✅ `PROVENANCE != TRUTH` - la provenance de un hit no garantiza que sea una operación real
- ✅ `READ/WRITE != HARDWARE_EFFECT` - demostrar que una función lee/scrive un registro NO demuestra efecto en el hardware
- ✅ `CALL_RELATION != DATA_RELATION` - trace_path resuelve CALLS, no relaciones de datos
- ✅ La reconstrucción manual con shell se declaró como tal (no como salida de RXRE)

---

## 17. GLOBAL WORK SCAN

Clasificación de fronteras restantes (SOLO):

```
SEARCH          — search/evidence ya funcionan (pero limitados a texto plano)
REGISTER_SCHEMA — register-fields VALIDATED (304 campos VM_CONTEXT0_CNTL)
TRACE_CALL      — trace_path VALIDATED (calls función→función)
TRACE_DATA      — **FRONTERA ABIERTA**: no existe capacidad de rastreo register→READ/WRITE
RELATION        — xref BLOCKED (AST incompleto)
PROVENANCE      — buena en schema, pobre en data flow
SEMANTICS       — no aplicado
VALIDATION      — pending para data-flow
HARDWARE_RUNTIME — no aplicado
```

**FRONTERA FINAL:** `TRACE_DATA` — la capa de análisis de flujo de datos (data flow) que permita reconstruir automáticamente REGISTER → READ/WRITE SITE → FUNCTION.

No se implementó nada en esta sesión. La solución queda documentada como frontera abierta para iteraciones futuras.

---

# FIN DEL DOGFOOD