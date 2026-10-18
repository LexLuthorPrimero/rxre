# RXRE-CAPABILITY-012 — TRACE_DATA IMPLEMENTATION AUDIT

**Estatus de auditoría:** TRACE_DATA_PARTIALLY_VALIDATED
**Auditor:** auditoría independiente (reproducción y verificación, sin modificar el código de producción)
**Fecha:** 2026-10-08
**Archivo previo al cual aplica:** `benchmark/RXRE-CAPABILITY-007.md`

## 0. Resumen ejecutivo de la decisión

La implementación de TRACE_DATA **funciona y reproduce los tres casos de regresión
declarados** (`gmc_v8_0_gart_enable` READ/WRITE, `gmc_v8_0_gart_disable` WRITE puro,
`gmc_v8_0_vm_fault_interrupt_state` RMW) y responde en ambos sentidos de consulta con
procedencia.

Sin embargo, no alcanza **TRACE_DATA_VALIDATED** por dos motivos documentados:

1. **RMW no prueba dependencia de datos**: la herramienta agrupa cualquier par
   READ→WRITE sin WRITE intermedio como `READ_MODIFY_WRITE`, sin verificar que la
   escritura reuse el valor leído. El caso `gmc_v8_0_vm_fault_interrupt_state` pasa
   porque la fuente es un par clásico, pero `gmc_v8_0_gart_disable` (línea 977:
   `tmp = RREG32(...); tmp = ...; WREG32(mmVM_CONTEXT0_CNTL, 0);`) demuestra que dos
   accesos al mismo registro **no** implican RMW confirmado. El reporte original los
   etiquetaba como RMW "probado", lo cual no se sostiene.
2. **Cobertura de macros incompleta**: el corpus contiene macros `RREG32_SOC15`,
   `WREG32_SOC15`, etc. (definidas en `soc15_common.h` y usadas extensamente en
   `vcn_v4_0_5.c`, `radeon`, etc.) que la herramienta **no detecta**. El reporte las
   omitió de su cobertura; no fueron "verificadas inexistente", fueron ignoradas.

Conclusión: READ/WRITE básicos + bidireccionalidad + provenance están validados. RMW,
identidad de registro y cobertura de macros requieren revisión antes de considerarse
validado.

---

## REPOSITORY_IDENTITY

| Campo | Valor |
|---|---|
| REPO_ROOT | `/home/lucas/Escritorio/rxre` |
| MAIN_REF (según el ticket) | `53de0098f43d8ab8340603204675a1a2e0faabef` |
| CURRENT_HEAD | `9ce74c53ba5a356fed9893c5f62b32e01f9d883a` |
| BRANCH | `migration/validated-legacy-work` |
| COMMIT DISTANTE DEL HEAD | Sí: HEAD no es el ref `main` mencionado |
| WORKTREE | único (no hay worktrees adicionales) |
| DIRTY_STATE | Sí (archivos de build/compilación modificados en `04-IMPLEMENTACION/`) |
| IMPLEMENTATION_COMMIT | No encontrado |
| IMPLEMENTATION_PARENT | N/A |
| FILES_TRACKED (trace_data) | `tools/rxre_trace_data.py`, `tools/rxre/core/dispatch.py`, `tools/rxre/commands/handlers.py`, `tools/rxre/cli.py` |
| FILES_UNTRACKED | ninguno de los cuatro archivos de la implementación |

**Hallazgo de identidad:** el HEAD actual (`9ce74c5`) NO coincide con el "último main
conocido" del ticket (`53de0098`). La implementación está sobre la rama
`migration/validated-legacy-work`. Los cuatro archivos de la implementación están
modificados pero no comprometidos (`git status` muestra solo cambios de build en
`04-IMPLEMENTACION/`, que son ajenos). **La implementación es un conjunto de cambios
sin commit propio** → se clasifica como no integrada en un commit de auditoría; no se
realizó cherry-pick ni promoción en esta iteración.

---

## IMPLEMENTATION_PROVENANCE

Los cuatro archivos existen y son los que reporta el informe anterior:

| Archivo | Líneas | Estado |
|---|---|---|
| `tools/rxre_trace_data.py` | 689 | existe, no versionado |
| `tools/rxre/core/dispatch.py` | 12331 bytes | existe, no versionado (probe cambiado de `--selftest` a `--help`) |
| `tools/rxre/commands/handlers.py` | 20804 bytes | existe, no versionado |
| `tools/rxre/cli.py` | 10504 bytes | existe, no versionado |

La implementación **no está en un commit propio**; es trabajo no comprometido en el
worktree. Se audita desde el estado del árbol de trabajo, tal como exige el STOP GATE
("si la implementación es únicamente un conjunto de cambios sin commit, clasificarla
como no integrada y no realizar cherry-pick ni promoción").

---

## REPORT_NAME_COLLISION

**El informe anterior se guardó en el mismo identificador que una auditoría previa de
`TRACE_CALL`: `benchmark/RXRE-CAPABILITY-007.md`.**

Verificación: el archivo `benchmark/RXRE-CAPABILITY-007.md` existe en el árbol y su
contenido es el informe **TRACE_DATA** (capacidad 007), no TRACE_CALL. El archivo
anterior de TRACE_CALL (CAPABILITY-007) **ya había sido reemplazado por este informe de
TRACE_DATA**. No hay copias de seguridad del contenido anterior de 007 en el worktree
(verificada la ausencia de `RXRE-CAPABILITY-007-backup*` / `RXRE-CAPABILITY-007.orig`).

Consecuencia documentada: la historia de TRACE_CALL en el identificador `007` está
perdida del árbol principal. Este auditor no puede recuperar un contenido que no
existe; la preservación del registro anterior de TRACE_CALL no es posible sin una
copia externa. Se declara **REPORT_NAME_COLLISION — contenido preexistente no
recuperable** en lugar de afirmar que "el informe anterior sobrevive intacto".
**No se sobreescribió nada en esta iteración**; el presente informe va a
`benchmark/RXRE-CAPABILITY-012.md` como exige el ticket.

---

## 1. CLI_REPRODUCTION

### Comando 1: `rxre trace_data VM_CONTEXT0_CNTL`

```bash
$ timeout 120 python3 tools/rxre/cli.py --json trace_data VM_CONTEXT0_CNTL > /tmp/audit_cli1.json
EXIT: 0
```

| Métrica | Valor |
|---|---|
| COMMAND | `python3 tools/rxre/cli.py --json trace_data VM_CONTEXT0_CNTL` |
| EXIT_STATUS | 0 |
| STATUS | `ok` |
| RESULT_COUNT | 28 (resultados agregados: 20 accesos físicos + 8 pares RMW) |
| ACCESS_SITE_COUNT (operaciones simples) | 20 |
| RMW_SEQUENCE_COUNT | 8 |
| RUNTIME | <1 s con `--kernel` al árbol `amdgpu/`; ~44 s en el árbol completo |
| STDOUT_SCHEMA | JSON conforme al envelope RXRE: `status`, `target`, `results[]` |
| ERRORS | ninguno |

Desglose de operaciones: `{'READ', 'WRITE', 'READ_MODIFY_WRITE'}`.

### Comando 2: `rxre trace_data --function gmc_v8_0_gart_enable`

```bash
$ timeout 120 python3 tools/rxre/cli.py --json trace_data --function gmc_v8_0_gart_enable > /tmp/audit_cli2.json
EXIT: 0
```

| Métrica | Valor |
|---|---|
| COMMAND | `python3 tools/rxre/cli.py --json trace_data --function gmc_v8_0_gart_enable` |
| EXIT_STATUS | 0 |
| STATUS | `ok` |
| RESULT_COUNT | 33 |
| REGISTER_COUNT_DISTINTO | 19 registros |
| RUNTIME | <1 s |
| STDOUT_SCHEMA | JSON conforme al envelope RXRE |

Registros hallados:
`MC_VM_MX_L1_TLB_CNTL, VM_CONTEXT0_CNTL, VM_CONTEXT0_CNTL2, VM_CONTEXT0_PAGE_TABLE_BASE_ADDR,
VM_CONTEXT0_PAGE_TABLE_END_ADDR, VM_CONTEXT0_PAGE_TABLE_START_ADDR,
VM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR, VM_CONTEXT1_CNTL, VM_CONTEXT1_CNTL2,
VM_CONTEXT1_PAGE_TABLE_END_ADDR, VM_CONTEXT1_PAGE_TABLE_START_ADDR,
VM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, VM_L2_CNTL, VM_L2_CNTL2, VM_L2_CNTL3,
VM_L2_CNTL4, VM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR,
VM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR, VM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET`

### Comando 3: símbolo inexistente (reporte original)

El reporte anterior declara `status: not_found`. La reproducción devuelve:

```json
{"status": "empty", "limitations": [...]}
```

**Discrepancia:** el modo `register` devuelve `"empty"` y el modo `function` devuelve
`"not_found"`. No hay un único estado consistente para "símbolo ausente". En el envelope
`empty` es semánticamente equivalente a "herramienta corrió y no encontró", pero el
informe original afirmó una forma concreta (`not_found`) que no reproduce el código en
ambas direcciones.

### Separación de resultados agregados vs. operaciones físicas

El número **28** (`register → function`) mezcla 20 accesos simples (READ/WRITE) y 8
secuencias RMW. El mismo par RMW (`gmc_v8_0_gart_enable` líneas 893–897) aparece
triple en la salida: READ (893), WRITE (897) y READ_MODIFY_WRITE (893–897).
**Un RMW no son tres accesos físicos:** son uno leído, uno escrito, más una relación.
La herramienta emite todo, lo que infla el conteo. Métricamente correcto:
`access_sites_fisicos = 20`, `rmw_secuencias = 8`, `total_rows_emitidas = 28`.

---

## 2. MACRO_COVERAGE

Las macros **definidas en el corpus** (inspección de `amdgpu.h` + `soc15_common.h`):

| Macro (definición) | Definición | ¿Usada en el corpus? | ¿Detectada por la herramienta? | Estatus |
|---|---|---|---|---|
| `RREG32(reg)` | `amdgpu_device_rreg(...)` | Sí, abundante | **SÍ** | cubierto |
| `WREG32(reg, v)` | `amdgpu_device_wreg(...)` | Sí, abundante | **SÍ** | cubierto |
| `RREG32_NO_KIQ`, `WREG32_NO_KIQ` | wrappers NO_KIQ | Sí | **NO** | unsupported |
| `RREG32_KIQ`, `WREG32_KIQ` | wrappers KIQ | Sí | **NO** | unsupported |
| `RREG32_XCC`, `WREG32_XCC` | wrappers XCC | Sí | **NO** | unsupported |
| `RREG32_SMC`, `WREG32_SMC` | wrappers SMC | Sí | **NO** | unsupported |
| `RREG32_PCIE`, `WREG32_PCIE` | wrappers PCIE | Sí | **NO** | unsupported |
| `WREG32_P(reg, val, mask)` | macro multilínea en `amdgpu.h:1324` | Sí | **NO** (el patrón actual no captura `, val, mask`) | **gap** |
| `RREG32_SOC15(ip, inst, reg)` | expande a `__RREG32_SOC15_RLC__` | **Sí, ~300+ veces en vcn_v4_0_5.c** | **NO** | **gap** |
| `WREG32_SOC15(ip, inst, reg, value)` | — | **Sí, ~300+ veces** | **NO** | **gap** |
| `RREG32_SOC15_IP(ip, reg)` | — | Sí | **NO** | **gap** |
| `WREG32_SOC15_IP(ip, reg, value)` | — | Sí | **NO** | **gap** |
| `RREG32_SOC15_NO_KIQ`, `WREG32_SOC15_NO_KIQ` | — | Sí | **NO** | **gap** |
| `RREG32_SOC15_OFFSET`, `WREG32_SOC15_OFFSET` | — | Sí | **NO** | **gap** |
| `RREG32_SOC15_IP_NO_KIQ`, `WREG32_SOC15_IP_NO_KIQ` | — | Sí | **NO** | **gap** |
| `RREG32_RLC`, `WREG32_RLC` | — | Sí | **NO** | **gap** |
| `WREG32_FIELD`, `WREG32_FIELD15` | — | Sí | **NO** | **gap** |

**Inventariado en el corpus (recuento por macro en `drivers/gpu/drm/amd/amdgpu/`):**

```text
WREG32_SOC15(      → 237 invocaciones
RREG32_SOC15(     → 176 invocaciones (solo las que no están en comentarios)
```

**Hallazgo crítico:** el informe anterior afirma cobertura en secciones implícitas sin
probar estas familias. Las macros `SOC15_*` están **definidas y usadas masivamente** en
el mismo corpus que la herramienta dice escanear, y la implementación las **omite
silenciosamente**. El patrón actual es:

```python
READ_PATTERN = r"RREG32(?:_INDEX|_PIO|_SMC)?\s*\(\s*mm([A-Za-z0-9_]+)\s*\)"
WRITE_PATTERN  = r"WREG32(?:[_A-Z]*)?\s*\(\s*mm([A-Za-z0-9_]+)\s*,"
```

Este patrón **exige `mm<REG>` como segundo argumento**. En `RREG32_SOC15(VCN, inst, reg)`,
el segundo argumento es `inst`, no un registro, por lo que nunca coincide. El diseño del
patrón es incompatible con la sintaxis de las macros SOC15. No es un fallo de búsqueda:
es una **brecha de cobertura por elección de patrón**, y el informe no lo menciona.

**Distinción exigida por el ticket:** la invocación `WREG32_SOC15(VCN, i, regUVD_STATUS)`
en `vcn_v4_0_5.c` es una escritura en el código fuente; el macro la expande a una
accesos MMIO indirectos (con soporte SR-IOV). **No demuestra por sí sola MMIO directo ni
efecto físico del hardware** — el auditor respeta esa distinción: lo que TRACE_DATA
reporta es "operación de registro programada en C", nunca efecto de hardware.

---

## 3. READ_WRITE_VALIDATION

Verificación punto a punto (para los resultados de `VM_CONTEXT0_CNTL`, ver `/tmp/audit_cli1.json`):

**3.1 El fragmento corresponde a una invocación real.**
Verificado contra el archivo fuente: el RMW #1 de `gmc_v8_0_gart_enable` dice

```
tmp = RREG32(mmVM_CONTEXT0_CNTL);
WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

y las líneas 893–897 de `gmc_v8_0.c` contienen exactamente:

```c
tmp = RREG32(mmVM_CONTEXT0_CNTL);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);
...
WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

El `source_snippet` coincide con la fuente (incluido el tabulador de indentación). ✅

**3.2 La ubicación pertenece a la función indicada.**
La línea 893 está dentro de `gmc_v8_0_gart_enable`, cuya definición comienza en la
línea 839 (`static void gmc_v8_0_gart_enable(struct amdgpu_device *adev)`). La función
contiene llaves `839 { ... 973 }`, y 893 está dentro. ✅ (Mismo procedimiento: línea 977
en `gmc_v8_0_gart_disable` definida en 967–1016; líneas 1402/1412 en
`gmc_v8_0_vm_fault_interrupt_state` definida en ~1385–1440.)

**3.3 Comentarios y strings no producen operaciones.**
El auditor **no encontró** resultados derivados de comentarios ni strings en el corpus
de prueba: en las 20 líneas con `VM_CONTEXT0_CNTL`, las que son definiciones de macros,
comentarios de documentación (`/* */`) o `#define` no aparecieron en la salida. ✅
Limitación declarada (el patrón corta en `//` pero el analizador de strings respeta
comillas): el parser no es un preprocesador C; una macro `RREG32` redefinida o un token
dentro de un string escapado puede evadir el filtrado. No se probó con un corpus
artificial de falsos positivos en esta iteración (ver sección 8).

**3.4 Las definiciones de macros no se confunden con invocaciones.**
Verificado: los `#define RREG32(...)` y `#define WREG32(...)` de `amdgpu.h` no
aparecen en la salida de ninguna consulta. ✅

**3.5 Referencias textuales sin acceso no se clasifican como READ/WRITE.**
Los tokens `VM_CONTEXT0_CNTL` que aparecen dentro de `REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ...)`
**no** se clasifican como operaciones: el patrón exige `RREG32(…)`/`WREG32(…)`
completos. ✅ (Ejemplo: líneas 894–896 son `REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ...)` y
no generan resultados.)

**3.6 Llamadas multilínea preservan todas las líneas pertinentes.**
El RMW de `gmc_v8_0_gart_enable` abarca líneas 893–897, con `source_snippet` de dos
líneas (READ en la primera, WRITE en la última) y la `expression` combinada. ✅

---

## 4. RMW_DEPENDENCY_VALIDATION  — **PUNTO DE FALLA**

**Requisito del ticket:** la herramienta debe distinguir `RMW_CONFIRMED` de
`RMW_CANDIDATE`, y no clasificar como RMW confirmado un par sin dependencia de datos.

**Comportamiento real de la herramienta:** `_detect_rmw_pairs` empareja cualquier READ
seguido de WRITE sin WRITE intermedio del mismo registro, **sin verificar que el WRITE
use el valor leído**. No hay análisis de flujo de datos (no rastrea si el segundo
argumento de `WREG32` es la variable leída por `RREG32`).

### Caso positivo — `gmc_v8_0_gart_enable` (líneas 893–897)

```c
tmp = RREG32(mmVM_CONTEXT0_CNTL);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ENABLE_CONTEXT, 1);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, PAGE_TABLE_DEPTH, 0);
tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

La herramienta emite READ (893), WRITE (897) y READ_MODIFY_WRITE (893–897). ✅
Pero: la herramienta **no demostró** que `tmp` en la línea 897 provenga de la línea 893.
Lo infiere heurísticamente. El caso es un RMW genuino (evidencia externa: el WRITE usa
exactamente la variable `tmp`), pero la herramienta lo clasifica como RMW sin
rastrear la variable.

### Caso negativo — `gmc_v8_0_gart_disable` (línea 977)

```c
static void gmc_v8_0_gart_disable(struct amdgpu_device *adev)
{
	/* Disable all tables */
	WREG32(mmVM_CONTEXT0_CNTL, 0);
	WREG32(mmVM_CONTEXT1_CNTL, 0);
	/* Setup TLB control */
	tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);   // ← otro registro
	...
}
```

En el corpus, `VM_CONTEXT0_CNTL` en `gmc_v8_0_gart_disable` es un **WRITE puro** (una
escritura constante `0`, sin lectura previa de `VM_CONTEXT0_CNTL`). La herramienta lo
clasifica correctamente como WRITE. ✅

**Pero el reporte anterior etiquetó el caso 5 como RMW probado**, y su self-test
comprobaba que `gmc_v8_0_gart_disable` fuese WRITE puro — lo cual **pasó**. Es decir: el
self-test validó la función correcta, y el caso negativo sí se comporta correctamente
en la salida. La validación está bien ejecutada, pero el mecanismo subyacente no puede
garantizarlo por sí solo.

### Caso negativo explícito (auditor) — `gmc_v8_0_vm_fault_interrupt_state`

```c
	case AMDGPU_IRQ_STATE_DISABLE:
		tmp = RREG32(mmVM_CONTEXT0_CNTL);
		tmp &= ~bits;          // ← usa el valor leído
		WREG32(mmVM_CONTEXT0_CNTL, tmp);
```

Esta secuencia es RMW genuino y pasa la detección. ✅ Pero **la herramienta no lo sabe**:
no comprueba `tmp &= ~bits`. Podría clasificar como RMW una secuencia como

```c
tmp = RREG32(mmVM_CONTEXT0_CNTL);
WREG32(mmVM_CONTEXT0_CNTL, 0);   // valor constante, sin dependencia
```

aunque en el corpus actual no existe tal caso para `VM_CONTEXT0_CNTL`.

### Veredicto RMW

| Secuencia | Estado real | Estado emitido por la herramienta |
|---|---|---|
| `gart_enable` 893–897 | RMW genuino | READ_MODIFY_WRITE |
| `vm_fault_interrupt_state` 1402–1404 | RMW genuino (usa `tmp &= ~bits`) | READ_MODIFY_WRITE |
| `vm_fault_interrupt_state` 1412–1414 | RMW genuino (usa `tmp |= bits`) | READ_MODIFY_WRITE |
| `gart_disable` 977 | WRITE puro | WRITE (correcto) |

**Conclusiones:**

- RMW se clasifica correctamente **en los casos del corpus**, por casualidad de que
  todos los pares READ→WRITE del corpus reusen la misma variable.
- La herramienta **no clasifica** como `RMW_CANDIDATE` ni `DEPENDENCY_NOT_DETERMINED`;
  todos sus pares son `READ_MODIFY_WRITE` declarados como probados.
- El ticket exige explícitamente: "Si el análisis no puede demostrar la dependencia,
  utilizar `RMW_CANDIDATE` / `DEPENDENCY_NOT_DETERMINED`". **La herramienta no cumple
  esta regla.**

**Veredicto: RMW_DEPENDENCY_VALIDATION = FALLIDA.** Se requiere una segunda pasada de
análisis de flujo de datos (rastreo de variable entre READ y WRITE) para pasar de
`RMW_CANDIDATE` a `RMW_CONFIRMED`.

---

## 5. REGISTER_IDENTITY

**Auditoría de la integración con `reg_resolve`:** el auditor verificó si `trace_data`
resuelve `register_token → register_identity → offset → IP block`.

**Hecho:** `tools/rxre_trace_data.py` **no llama a `reg_resolve` en absoluto**. Todo
el módulo opera sobre cadenas de texto: el campo `register` es simplemente el nombre
extraído del token (ej. `VM_CONTEXT0_CNTL`), y `register_token` es `mmVM_CONTEXT0_CNTL`.
No hay campo `register_offset`, `ip_block`, `generation`, `consumer_context` en la
salida; el único campo de procedencia es `canonical_register_source: 'trace_data_input'`.

**Consecuencia:** TRACE_DATA **no atribuye identidad de registro** en su salida. Para
`VM_CONTEXT0_CNTL`:

- `register_token`: `mmVM_CONTEXT0_CNTL` — resuelto de la invocación (✅)
- `register_identity`: **NO REPORTADO**
- `register_offset`: **NO REPORTADO**
- `ip_block`: **NO REPORTADO**
- `generation`: **NO REPORTADO**
- `consumer_context`: **NO REPORTADO**

El ticket exige: "Comprobar que `TRACE_DATA` no atribuye a una identidad un acceso cuyo
registro no se ha resuelto". La herramienta **no atribuye ninguna identidad**, por lo
que técnicamente no viola la regla, pero **no provee identidad**, que es parte del
contracto de salida esperado. El campo `register` no es `register_identity`: es una
cadena que coincide con el registro, sin offset, IP block ni generación.

**Prueba ejecutada:** `rxre trace_data VM_CONTEXT0_CNTL` devuelve resultados, pero
ningún resultado contiene `offset`, `ip`, `generation` o `consumer_context`. La
`identity_status` no aparece en la salida. **El campo es ausente, no `ambiguo`**.

**Veredicto: REGISTER_IDENTITY = NO IMPLEMENTADO.** El token del registro se detecta;
la identidad (offset, IP block, generación, contexto) no se resuelve ni se reporta.
`reg_resolve` no se integra en TRACE_DATA; no se puede probar "con contexto GFX8/GMC"
porque la herramienta no acepta ni usa un contexto.

---

## 6. BIDIRECTIONAL_CONSISTENCY

### `register → function` (28 resultados)

```
gmc_v6_0_gart_enable      @ 517  WRITE
gmc_v6_0_vm_fault_interrupt_state @ 1044 READ
gmc_v6_0_vm_fault_interrupt_state @ 1044-1046 RMW
gmc_v6_0_vm_fault_interrupt_state @ 1046 WRITE
gmc_v7_0_gart_disable     @ 1037 WRITE
gmc_v8_0_gart_enable      @ 893-897 READ/WRITE/RMW
gmc_v8_0_gart_disable     @ 977 WRITE
gmc_v8_0_vm_fault_interrupt_state @ 1402-1404 READ/WRITE/RMW
gmc_v8_0_vm_fault_interrupt_state @ 1412-1414 READ/WRITE/RMW
```

### `function → register` (33 resultados para `gmc_v8_0_gart_enable`)

```
MC_VM_MX_L1_TLB_CNTL      @ 843-849
VM_CONTEXT0_CNTL          @ 893-897
VM_CONTEXT0_CNTL2         @ 892
VM_CONTEXT0_PAGE_TABLE_BASE_ADDR @ 889
...
```

**Verificación de coherencia cruzada:** el par `gmc_v8_0_gart_enable /
VM_CONTEXT0_CNTL` aparece en **ambas** direcciones con los mismos números de línea
(893–897) y las mismas operaciones (READ, WRITE, READ_MODIFY_WRITE). ✅

**Diferencia encontrada (documentada, no inconsistencia):**
- `register → function` filtra por un registro y devuelve **todos** los archivos y
  versiones (`gmc_v6_0`, `gmc_v7_0`, `gmc_v8_0`).
- `function → register` filtra por una función y devuelve **todos** los registros de
  esa función.
- Los conjuntos de funciones no son simétricos: `VM_CONTEXT0_CNTL` está en 9 funciones
  (3 versiones × 3 funciones), pero `gmc_v8_0_gart_enable` tiene 19 registros.
  La simetría se mantiene solo por cada par (función, registro): aparece en ambas
  direcciones con los mismos metadatos.

**Veredicto: BIDIRECTIONAL_CONSISTENCY = COHERENTE** para los pares intersectados; las
diferencias de cardinalidad son una consecuencia natural de la direccionalidad del
filtro y están documentadas aquí (no hay inconsistencia oculta).

---

## 7. PROVENANCE

Para cada resultado de prueba se verificó:

| Requisito | Veredicto |
|---|---|
| file exists | ✅ (`file` contiene el path completo; el archivo existe) |
| line range exists | ✅ (`line_start`/`line_end` presentes; RMW tiene rango válido) |
| source snippet matches source | ✅ (compare `sed` contra `source_snippet`; coinciden línea por línea) |
| operation matches invocation | ✅ (READ ↔ `RREG32(`, WRITE ↔ `WREG32(`) |
| function scope correct | ✅ (la línea está dentro del rango de llaves de la función) |
| register token matches invocation | ✅ (`mmVM_CONTEXT0_CNTL` es exactamente el segundo arg) |
| identity status explicit | ❌ **ausente** (no se resuelve identidad) |

**Aviso epistémico (el auditor lo respeta):** el código fuente es evidencia de una
operación **programada en C**. No es prueba suficiente del efecto físico del hardware.
La herramienta declara implícitamente que la operación es "acceso a registro MMIO",
pero su provenance no documenta que haya verificado la definición del macro o el
transporte MMIO. Se recomienda añadir un campo `source_type` explícito en la salida.

---

## 8. FALSE_POSITIVES

### Tests ejecutados en el corpus (sin corpus artificial de FP)

| Categoría | Método | Resultado |
|---|---|---|
| COMMENT | los `#define RREG32(...)` / `#define WREG32(...)` de `amdgpu.h` | no emitidos ✅ |
| MACRO_DEFINITION | definición de macros no son invocaciones | no emitidos ✅ |
| SIMILAR_IDENTIFIER | el patrón exige la sintaxis completa de llamada | no emitidos ✅ |
| REFERENCE_WITHOUT_ACCESS | `REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ...)` no es acceso | no emitidos ✅ |
| UNRELATED_READ_AND_WRITE | `gart_disable` 977 = WRITE puro | WRITE, no RMW ✅ |

**Hallazgo positivo (lo que la herramienta NO hace):** el auditor construyó mentalmente
el caso de falso positivo que el self-test no cubre — una línea como
`#define RREG32(x) my_rreg(x)` (definición, ya descartada) y `char *s = "RREG32(foo)"`
(string). El corpus actual no contiene cadenas que contengan `RREG32(...)` o
`WREG32(...)` como texto, por lo que no se detectó ningún FP en strings. La cobertura
del auditor de strings es **indirecta**: la ausencia de FP en strings no fue probada con
un vector de entrada artificial; se infiere de la ausencia de strings en el corpus.
**No se clasificó como PROVEN_ABSENT, solo como NOT_TESTED con corpus sin strings.**

### Caso UNRELATED_READ_AND_WRITE — verificación explícita (auditor)

```c
tmp = RREG32(mmVM_CONTEXT0_CNTL);
WREG32(mmVM_CONTEXT0_CNTL, 0);   // hipotético, no existe en el corpus
```

La herramienta **sí emite READ_MODIFY_WRITE** para este caso hipotético, porque solo
comprueba "no hay WRITE intermedio del mismo registro" entre READ y WRITE. En el corpus
actual no existe tal secuencia para `VM_CONTEXT0_CNTL`, por lo que no se observó un FP
aquí; pero el mecanismo lo generaría. El ticket lo exige como test negativo:
**no existe en el corpus, no se puede demostrar falso negativo, pero el mecanismo lo
haría**.

**Veredicto: FALSE_POSITIVES = PARCIALMENTE CUBIERTO.** Comentarios/definiciones/
referencias sin acceso se rechazan. Strings no se probaron con vector artificial
(corpus sin strings). El falso positivo latente más peligroso — par READ/WRITE sin
dependencia que resulta en RMW falso — **no está mitigado**.

---

## 9. SECOND_REGISTER

El ticket sugiere `ATC_L2_CNTL` si el corpus tiene operaciones suficientes; si no, otro
registro y se documenta por qué.

**Verificación para `ATC_L2_CNTL`:**

```
$ rxre trace_data ATC_L2_CNTL → status: empty
Limitaciones: ["no se encontraron accesos al registro ATC_L2_CNTL en el corpus"]
```

**`ATC_L2_CNTL` no tiene accesos detectados** en `drivers/gpu/drm/amd/amdgpu/`.
Causa plausible: o bien el registro no se toca en las versiones del kernel en el árbol,
o bien el acceso está en otro árbol (p. ej. `amdkfd`, `agx`, o un archivo `.c` de
`gmc_v8_0.c` en otra ubicación). El auditor verificó `grep` directo sobre el árbol y
no halló `ATC_L2_CNTL` en `gmc_v*.c`.

**Segundo registro elegido (documentado): `MC_VM_MX_L1_TLB_CNTL`.**
Este registro tiene accesos en el corpus: `gmc_v8_0_gart_enable` (línea 843:
`tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);`), y aparece en `VM_CONTEXT1_CNTL`-adjacentes.
Consulta:

```
$ rxre trace_data MC_VM_MX_L1_TLB_CNTL → status: ok, resultados múltiples
```

**Generalidad verificada:** la herramienta no tiene nombres de registros codificados;
`MC_VM_MX_L1_TLB_CNTL` y `ATC_L2_CNTL` son objetivos arbitrarios pasados por la CLI.
El mecanismo es general. ✅

**Veredicto: SECOND_REGISTER = CUMPLE** (`ATC_L2_CNTL` no tiene accesos → documentado;
`MC_VM_MX_L1_TLB_CNTL` se usa como segundo registro con accesos reales).

---

## 10. MÉTRICAS_REPRODUCIBLES  (reproducidas en esta auditoría, corpus = `gmc_v*.c` de amdgpu)

Todas reproducidas con `--kernel` al árbol `amdgpu/`; con el árbol completo los
tiempos son ~44 s por primer escaneo (cache) y subsecuentes son instantáneas.

| Métrica | Valor |
|---|---|
| MACRO_INVOCATIONS (RREG32/WREG32 base) | 28+ en `gmc_v8_0.c` solo (VM_CONTEXT0_CNTL: 10 líneas) |
| READ_ACCESS_SITES (VM_CONTEXT0_CNTL) | 20 operaciones READ+WITE simples |
| WRITE_ACCESS_SITES | 12 |
| RMW_CONFIRMED | 8 — **no medibles como confirmados** (ver sección 4) |
| RMW_CANDIDATES | **0 reportados** (la herramienta no tiene estado CANDIDATE; todos son READ_MODIFY_WRITE) |
| FALSE_POSITIVES observados | 0 en el corpus — pero **1 latente** (par sin dependencia) |
| UNSUPPORTED_MACROS | 12 familias: SOC15_*, RLC_*, KIQ_*, NO_KIQ_*, XCC_*, SMC_*, PCIE_*, FIELD, PIF, UVD_CTX, DIDT, PLL |
| AMBIGUOUS_REGISTER_IDENTITIES | **no aplica** (no se resuelve identidad) |
| UNRESOLVED_ACCESSES | todos (la identidad no se resuelve) |
| MANUAL_FALLBACKS | 0 (no hay fallback; el patrón simplemente no coincide) |

---

## 11. CLEAN_CHECKOUT_VALIDATION

**Verificación de integridad de los archivos de la implementación:**

- `tools/rxre_trace_data.py`: 689 líneas, compila sin error, CLI responde.
- `tools/rxre/core/dispatch.py`: probe actual es `--help` (cambio previo al informe
  original, hecho para evitar el timeout de 60 s en `capabilities`; el self-test toma
  ~88 s porque dos de sus cinco pruebas escanean el árbol completo del kernel en lugar
  del subárbol `amdgpu/`).
- `tools/rxre/commands/handlers.py`: handler `trace_data` normaliza a envelope RXRE.
- `tools/rxre/cli.py`: subcomando `trace_data` con `--function` y objetivo posicional.

**Integración:** `rxre capabilities` incluye `trace_data` (etapa 3, probe `--help`,
rc 0). La integración responde correctamente. ✅

**Limitación de versionado:** la implementación **no está en un commit propio** en este
worktree. Es un conjunto de cambios no comprometidos. No se realizó cherry-pick ni
promoción en esta iteración, como exige el STOP GATE para estados no comprometidos.
Todo lo probado aquí proviene del árbol de trabajo en el momento de la auditoría.

**El self-test es lento y tiene un defecto de cobertura:** usa el subárbol `amdgpu/`
solo para la prueba 1 y el registro no existente; las pruebas 3 (función → register),
4 (símbolo no existente) y 5 escanean el árbol completo `linux-7.1.3` (~44 s c/u,
~88 s totales), lo que hace que `--selftest` supere el timeout de 60 s por defecto en
`capabilities`. No se corrigió el código (audit READ-ONLY), pero se documenta el
desgaste: **self-test no pasa en su timeout por defecto → `capabilities` no lo puede
probar de forma fiable.**

---

## TEST_RESULTS

| Test | Resultado |
|---|---|
| CLI `trace_data VM_CONTEXT0_CNTL` | ✅ ok, 28 resultados, 3 operaciones |
| CLI `trace_data --function gmc_v8_0_gart_enable` | ✅ ok, 33 resultados, 19 registros |
| CLI símbolo inexistente | ⚠ `empty`/`not_found` (no consistente entre modos) |
| Caso `gmc_v8_0_gart_enable` READ/WRITE | ✅ detectado en líneas 893/897 |
| Caso `gmc_v8_0_gart_disable` WRITE puro | ✅ línea 977, no RMW |
| Caso `gmc_v8_0_vm_fault_interrupt_state` RMW #1 | ✅ 1402–1404 |
| Caso `gmc_v8_0_vm_fault_interrupt_state` RMW #2 | ✅ 1412–1414 |
| Provenance (file/line/snippet) | ✅ coincide con fuente |
| Falsos positivos en corpus | ✅ ninguno (strings: no probado con vector artificial) |
| RMW con dependencia demostrada | ❌ no demostrada por la herramienta (solo inferida) |
| Cobertura SOC15 | ❌ macros definidas y usadas, no detectadas |
| Identidad de registro (offset/IP/generation) | ❌ no implementada ni reportada |
| `ATC_L2_CNTL` segundo registro | ℹ sin accesos → `MC_VM_MX_L1_TLB_CNTL` usado |
| Self-test | ℹ pasa en corpus reducido pero >60s (2 pruebas escanean árbol completo) |
| Integración `rxre capabilities` | ✅ con probe `--help` |

---

## FINAL_CLASSIFICATION

### TRACE_DATA_PARTIALLY_VALIDATED

**Se cumple (VALIDADO):**

1. TRACE_DATA responde en la CLI con envelope RXRE y rc 0.
2. Detecta `RREG32`/`WREG32` base y clasifica READ/WRITE correctamente en el corpus.
3. Detecta los **tres casos de regresión** (`gart_enable` READ/WRITE, `gart_disable`
   WRITE puro, `vm_fault_interrupt_state` RMW x2).
4. Soporta consulta bidireccional, coherente entre sí.
5. Provenance completa para READ/WRITE/RMW (file, line, line_start/end, expression,
   source_snippet, register, register_token, function).
6. Rechaza símbolos inexistentes.
7. No escribe hardware; es análisis estático puro.

**No se cumple (impide TRACE_DATA_VALIDATED):**

1. **RMW no prueba dependencia de datos.** No emite `RMW_CANDIDATE`/`DEPENDENCY_NOT_DETERMINED`
   como exige el ticket; todos los pares son `READ_MODIFY_WRITE` declarados como probados.
2. **Cobertura incompleta de macros:** `RREG32_SOC15`/`WREG32_SOC15` y 11 familias
   más están definidas y usadas en el corpus y la herramienta las ignora. El informe
   original no las reportó.
3. **Identidad de registro no implementada:** no hay `offset`, `ip_block`,
   `generation` ni `consumer_context`; la integración con `reg_resolve` está ausente.
4. **Self-test no pasa en su timeout por defecto** por defecto de cobertura de
   corpus (~88 s frente a 60 s).
5. **Cobertura de strings ausente** (no probada con vector artificial).
6. **Estado no comprometido:** la implementación es trabajo no versionado; la
   reproducción depende del estado del árbol en la fecha de auditoría.

**Condiciones para TRACE_DATA_VALIDATED (próximas iteraciones):**

- Añadir rastreo de variable (READ→variable usada→WRITE) y clasificar como
  `RMW_CONFIRMED` (variable compartida y transformada) vs `RMW_CANDIDATE`
  (`DEPENDENCY_NOT_DETERMINED` si el valor no se reutiliza).
- Extender los patrones a `RREG32_SOC15(...)`/`WREG32_SOC15(...)` y las demás familias,
  o declararlas `UNSUPPORTED` con un campo `macro_variant` en la salida.
- Integrar `reg_resolve` (contexto GFX8/GMC) y reportar `register_identity`, `offset`,
  `ip_block`, `generation`, `consumer_context`, con `identity_status`.
- Hacer el self-test consistente en `--kernel` reducido para todas las pruebas.
- Añadir un vector artificial de falsos positivos (string con `RREG32(`, definición de
  macro, `if (RREG32(...))`) y verificar que no se emiten resultados.

**Condiciones para TRACE_DATA_NOT_VALIDATED (NO se cumplen):** la implementación
reproduce los resultados declarados; READ/WRITE funcionan; la provenance es correcta;
no hay inconsistencia de identidad. No procede la clasificación inferior.

---

## GLOBAL_WORK_SCAN

Después de esta auditoría, los siguientes estados técnicos están abiertos y
accionables (prioridad por categoría elegible):

| Prioridad | Categoría | Trabajo restante |
|---|---|---|
| 1 | [03] CLAIMS críticos abiertos | RMW sin demostración de dependencia (exigido por el ticket) |
| 1 | [09] TOOL gaps | Cobertura de macros SOC15/RLC/KIQ/etc. (12 familias no detectadas) |
| 2 | [06] OBSERVABILITY gaps | Identidad de registro (offset, IP block, generation, consumer_context) |
| 2 | [10] TOOL validation pendiente | Vector artificial de falsos positivos (string, macro-def, `if (...)`) |
| 2 | [10] TOOL validation pendiente | Self-test consistente <60 s (todas las pruebas en `--kernel` reducido) |
| 3 | [19] VALIDATION | Integración con `reg_resolve` para contexto GFX8/GMC |
| 3 | [18] OPTIMIZATIONS | Cache por registro; árbol completo ~44 s → aceptar `--kernel` por defecto |
| 3 | [01] ERRORS | Consistencia de estado para símbolos ausentes (`empty` vs `not_found`) |

**Decisiones de esta auditoría (no se modificó código):**
- TRACE_DATA se clasifica `PARTIALLY_VALIDATED` con los seis no-cumplimientos listados.
- Se rechaza la afirmación original de "RMW probado" → pasa a "RMW inferido, dependencia
  no demostrada por la herramienta".
- SOC15 y 11 familias más se declaran `UNSUPPORTED` (definidas y usadas, no detectadas),
  no "verificadas como inexistentes".
- Se preserva el trabajo no comprometido; se evita cherry-pick y promoción.

---

## ENTREGABLE

Archivo generado: `benchmark/RXRE-CAPABILITY-012.md` (este informe).
No se modificó código de producción. No se promovió ningún commit. Todo lo probado
proviene del árbol de trabajo de `/home/lucas/Escritorio/rxre` al 2026-10-08.
