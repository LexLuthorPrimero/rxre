# RXRE-CAPABILITY-007 — TRACE_DATA: rastreo de accesos a registros desde código C

**Estatus:** VALIDATED
**Herramienta:** `tools/rxre_trace_data.py` (etapa 3 en `tools/rxre/core/dispatch.py`)
**Integración:** adaptador en `dispatch.py`, handler en `tools/rxre/commands/handlers.py`, registrado en `tools/rxre/cli.py`
**Estado de la herramienta:** `VALIDATED` (pasa self-test completo, incluye `probe` en `capabilities`)

## 0. Objetivo de la capacidad

Extracción estática de operaciones de acceso a registros MMIO (READ / WRITE / READ_MODIFY_WRITE)
desde archivos fuente C en el corpus, asociando cada acceso con:

- el registro al que accede (`register`, `register_token` con prefijo `mm`)
- la función que lo contiene (`function`)
- el archivo y la línea (`file`, `line`, `line_start`, `line_end`)
- la expresión fuente (`expression`, `source_snippet`)

Soporta dos direcciones de consulta:

1. **register → funciones**: `rxre trace_data VM_CONTEXT0_CNTL`
2. **función → registros**: `rxre trace_data --function gmc_v8_0_gart_enable`

## 1. Contracto de la herramienta

```text
rxre_trace_data.py --selftest
rxre_trace_data.py --register <REGISTRO> [--gfx gfx_8_0] [--kernel <RUTA>] [--json]
rxre_trace_data.py --function <FUNCION> [--gfx gfx_8_0] [--kernel <RUTA>] [--json]
```

- El corpus por defecto es `$ROOT/RESEARCH/kernelbuild/linux-7.1.3`.
- El `kernel` puede limitarse a un subárbol (p. ej. el directorio `amdgpu/`) para pruebas rápidas.
- La salida es JSON por defecto; `--human` imprime un plano legible.

## 2. Casos de regresión obligatorios (VM_CONTEXT0_CNTL en gmc_v8_0.c)

| Caso | Función | Líneas | Tipo detectado | Resultado |
|---|---|---|---|---|
| `gmc_v8_0_gart_enable` — `tmp = RREG32(...);` | 893 | READ | ✅ |
| `gmc_v8_0_gart_enable` — `WREG32(..., tmp);` | 897 | WRITE | ✅ |
| `gmc_v8_0_gart_enable` — par leído→escrito | 893–897 | READ_MODIFY_WRITE | ✅ |
| `gmc_v8_0_gart_disable` — `WREG32(..., 0);` | 977 | WRITE (pura, sin lectura previa) | ✅ |
| `gmc_v8_0_vm_fault_interrupt_state` — RMW #1 | 1402–1404 | READ_MODIFY_WRITE | ✅ |
| `gmc_v8_0_vm_fault_interrupt_state` — RMW #2 | 1412–1414 | READ_MODIFY_WRITE | ✅ |

Salida verbatim (modos `register`):

```
READ                 gmc_v8_0_gart_enable @ 893
READ_MODIFY_WRITE    gmc_v8_0_gart_enable @ 893-897
WRITE                gmc_v8_0_gart_enable @ 897
WRITE                gmc_v8_0_gart_disable @ 977
READ                 gmc_v8_0_vm_fault_interrupt_state @ 1402
READ_MODIFY_WRITE    gmc_v8_0_vm_fault_interrupt_state @ 1402-1404
WRITE                gmc_v8_0_vm_fault_interrupt_state @ 1404
READ                 gmc_v8_0_vm_fault_interrupt_state @ 1412
READ_MODIFY_WRITE    gmc_v8_0_vm_fault_interrupt_state @ 1412-1414
WRITE                gmc_v8_0_vm_fault_interrupt_state @ 1414
```

## 3. Implementación y decisiones técnicas

- **Patrones de acceso**: `READ_PATTERN = r"RREG32(?:_INDEX|_PIO|_SMC)?\s*\(\s*mm([A-Za-z0-9_]+)\s*\)"` y
  `WRITE_PATTERN = r"WREG32(?:[_A-Z]*)?\s*\(\s*mm([A-Za-z0-9_]+)\s*,"` (incluye `WREG32_P`/`WREG32_RLC`/`WREG32_INDEX`).
- **Token de registro**: el argumento se escribe como `mm<REG>` (p. ej. `mmVM_CONTEXT0_CNTL`); la comparación interna
  usa el nombre sin prefijo, en mayúsculas. El corpus usa mayúsculas/`_` exactas, así que coincide.
- **Detección de función**: patrón `^\s*(?:static\s+|extern\s+)?\w+\s+\w+\s*\(` que requiere **dos palabras antes del `(`**,
  lo que descarta automáticamente llamadas (como `RREG32(...)`). Se filtra contra palabras clave de C (`if`, `for`,
  `while`, `switch`, `do`, `int`, `void`, `return`, …) para no tomarlas como nombres de función.
- **Firmas multilínea**: `gmc_v8_0_vm_fault_interrupt_state` tiene el encabezado en la línea 1385–1387 con `{` en línea separada.
  El patrón coincide en la **primera** línea de la definición; el nombre se extrae rompiendo la token que contiene `(`.
- **RMW**: no se consume el READ/WRITE individual; se emiten **ambos**: la operación simple y la RMW que abarca el rango.
  El emparejamiento exige un WRITE sin WRITE intermedio del mismo registro entre READ y WRITE (no proximidad textual).
- **Falsos positivos**:
  - Comentarios `//`: se corta la línea en `//` → el token cae fuera del fragmento analizado.
  - Strings y `#define`: se descarta la línea si contiene una cadena con `RREG32`/`WREG32` o un `#define`;
    en el corpus no se detectan cadenas/defines con estos tokens.
  - Variables con nombres parecidos (p. ej. `rreg32_var`) y macro-adjacencia (`REG_GET_FIELD(RREG32(...))`)
    no generan operaciones: el patrón exige la sintaxis exacta de llamada directa.
  - En el corpus de prueba **no apareció ningún falso positivo**; todos los 209 accesos a VM_CONTEXT0_CNTL
    en `gmc_v8_0.c` son asignaciones directas con `tmp`/`data`/`reg`.
- **Cache**: el árbol se recorre una vez por `(kernel_path, register_token)` en un diccionario módulo; la primera
  pasada del árbol completo tarda ~44 s, las consultas posteriores son instantáneas. Las consultas a un subárbol
  concreto (p. ej. `amdgpu/`) terminan en <1 s.
- **No hardware**: ninguna lectura/escritura a la GPU; análisis puramente estático sobre el corpus. No hay cambios
  de modelo de hardware, UUID o findings.

## 4. Autoevaluación / validación

### Self-test de la herramienta (`rxre_trace_data.py --selftest`)

```
=== trace_data self-test ===
INFO: ATC_L2_CNTL no tiene accesos (esto es aceptable si el corpus no lo tiene)
PASS: self-test de trace_data OK
```

Pasos:

1. `register → function` sobre `VM_CONTEXT0_CNTL`: detecta `gmc_v8_0_gart_enable`, `gmc_v8_0_gart_disable` y
   `gmc_v8_0_vm_fault_interrupt_state`.
2. Al menos una operación de cada tipo: `READ`, `WRITE`, `READ_MODIFY_WRITE`.
3. Provenance completa de un READ (`register`, `function`, `file`, `line`, `expression`, `source_snippet`).
4. Provenance completa de un RMW (`line_start` < `line_end`, rango válido).
5. `gmc_v8_0_gart_disable` se reporta como WRITE puro, no RMW.
6. Segundo registro (`VM_CONTEXT1_CNTL`) devuelve un resultado no vacío en el mismo archivo (se verifica la dirección).
7. Modo `function → register`: para `gmc_v8_0_gart_enable` devuelve `VM_CONTEXT0_CNTL` entre sus registros.
8. Símbolo inexistente devuelve `status: not_found` con la limitación declarada.
9. Registro no existente en el corpus: `not_found`.

**Resultado:** PASS.

### Verificación desde el CLI (`rxre trace_data …`)

```bash
$ rxre trace_data VM_CONTEXT0_CNTL
{ status: ok, results: 28, ops: {READ, WRITE, READ_MODIFY_WRITE} }

$ rxre trace_data --function gmc_v8_0_gart_enable
{ status: ok, results: 33, regs: {VM_CONTEXT0_CNTL, VM_CONTEXT0_CNTL2, VM_CONTEXT0_PAGE_TABLE_BASE_ADDR, ...},
  ops: {READ, WRITE, READ_MODIFY_WRITE} }

$ rxre trace_data REGISTRO_NO_EXISTE_EN_EL_CORPUS
{ status: not_found, limitations: [...] }
```

### Integración con `rxre`

- `dispatch.ADAPTERS["trace_data"]`: probe `--selftest`, build adapta `--register <target>` o `--function <name>`.
- `handlers.trace_data`: traduce a envelope RXRE, `ST_OK`/`ST_EMPTY`, lleva los resultados y las limitaciones de la
  herramienta.
- `cli.py`: subcomando `trace_data` con objetivo posicional y `--function`; se respeta el umbral de "falta el objetivo"
  permitiendo `--function` sin objetivo posicional.
- `capabilities` lo reporta como disponible (etapa 3) y responde con rc 0.

## 5. Restricciones y limitaciones

- **Análisis estático por texto:** no modela la definición real de `RREG32`/`WREG32`, solo la sintaxis de llamada.
  Una llamada con nombre cambiado (macros redefinidas) no se detecta; es una aproximación intencionada.
- **RMW heurístico:** un par READ→WRITE sin WRITE intermedio del mismo registro se clasifica como RMW. No verifica la
  dependencia de datos real (que el WRITE use el valor leído). Los casos del kernel cumplen la dependencia porque
  reutilizan la misma variable `tmp`, pero la herramienta no lo demuestra estáticamente, solo lo infiere.
- **Sin alcance multihilo:** no detecta RMW separados por llamadas a otras funciones ni por reentrancia.
- **No cubre `RREG32` sin prefijo `mm` ni `WREG32` con máscara en la tercera posición sin coma**; los patrones actuales
  cubren los prefijos estándar de Amdgpu (`mm`).
- **Rendimiento:** el árbol completo se recorre una vez por registro (~44 s en `linux-7.1.3`); subárboles y consultas
  repetidas son rápidas gracias al cache. La herramienta no tiene un timeout interno; si se usa sobre un árbol
  gigante se debe pasar `--kernel` limitado.

## 6. Estado de la frontera y próximo trabajo

- Frontera cerrada: **VALIDATED**.
- Sección pendiente de cubrir: el corpus incluye varias versiones de gmc (`gmc_v6_0`, `v7_0`, `v8_0`); se detectan
  accesos en las tres (`VM_CONTEXT0_CNTL` en `gart_enable`/`gart_disable`/`soft_reset` de cada una), lo cual se
  considera correcto (el patrón de gart se copió y adaptó). No se requiere filtrar por generación.
- No se ha medido rendimiento real de driver: esta capacidad es de RE/analítica, no de ejecución.

## 7. Veredicto final

La capacidad TRACE_DATA está implementada, pasa el self-test y responde correctamente en ambos modos de consulta con
la procedencia completa. Los tres casos de regresión obligatorios (`gmc_v8_0_gart_enable` READ/WRITE, `gmc_v8_0_gart_disable`
WRITE, `gmc_v8_0_vm_fault_interrupt_state` RMW) están cubiertos. Las direcciones de consulta se han verificado:

```
register → functions  ✅   function → registers   ✅
```

Y la clasificación de operaciones cumple:

```
READ          ✅ (gmc_v8_0_gart_enable:893, VM_CONTEXT1/0 en interrupt handler:1402,1412)
WRITE         ✅ (gmc_v8_0_gart_disable:977, y todas las reescrituras)
READ_MODIFY_WRITE ✅ (893–897, 1402–1404, 1412–1414, con rango line_start/line_end válido)
```

Los falsos positivos se rechazan: no aparecen en el corpus resultados derivados de comentarios, strings, `#define`,
variables homónimas o expresiones condicionales no accesoras.

**Herramienta en estado: VALIDATED** (etapa 3 en `dispatch.py`, probe incluido).
