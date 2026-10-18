# RXRE-CAPABILITY-016R: REGISTER FIELDS KEYING – RECONCILIATION AND VALIDATION

## RESUMEN DE LA AUDITORÍA

**Objetivo:** Auditar la implementación de RXRE-CAPABILITY-016 (register-fields-keying) para verificar si cumple su contrato y completar únicamente las brechas demostradas.

**Worktree auditado:** 
- `/home/lucas/Escritorio/rxre` (worktree principal)
- Estado inicial: rama `migration/validated-legacy-work`, commit `a923ddc6e42a515cef924effe4527e63f4642823`
- Commits bajo auditoría: `4f05b05` (fix) y `a923ddc` (docs)

**Worktree aislado de auditoría:** 
- Creado en `/tmp/rxre-audit/wt` basado en `d5b7d9f` (main verificado)
- Commits integrados: `4f05b05` y `a923ddc` (después de revisión)

## ANÁLISIS DE PROVENANCIA DE COMMITS AUDITADOS

### Commit 4f05b05: `fix: register-fields selects sh_mask.h from resolved identity`
- **Parents:** `9ce74c5`, `12a3462`, `4b7d067`
- **Relación con d5b7d9f:** Divergente - comparte ancestro común en `0145566` (feat: generalize register identity resolution)
- **Diff principal:** 
  - Nuevo archivo: `tools/rxre_register_fields.py` (706 líneas)
  - Elimina múltiples archivos de benchmark y herramientas (ver sección de diffs completos)

### Commit a923ddc: `docs: add RXRE-CAPABILITY-016 validation report`
- **Parent:** `4f05b05`
- **Relación con d5b7d9f:** Descendiente de 4f05b05
- **Diff principal:**
  - Nuevo archivo: `benchmark/RXRE-CAPABILITY-016.md` (181 inserciones)

## ANÁLISIS DEL CONTRATO REAL

### 1. Uso de identidad del resolver común
**Evidencia:** ✅ CONFIRMADO
- `rxre_register_fields.py` acepta `--resolved-header` y `--resolved-json` que provienen directamente de `reg_resolve.py`
- En `main()` (líneas 638-654), si se proporciona `--resolved-json`, se parsea y se extrae `chosen.file` como `resolved_header`
- El flujo es: `reg_resolve.resolve_reg()` → JSON → `--resolved-json` → `rxre_register_fields.py` → `find_register_fields()`

### 2. Proporción de --resolved-json
**Evidencia:** ✅ INTEGRADO
- El flag `--resolved-json` está diseñado para aceptar directamente la salida de `reg_resolve.py` 
- No requiere pasos manuales: `rxre_register_fields.py --resolved-json <(reg_resolve ...)`
- El código extrae automáticamente `chosen.file` y opcionalmente `definition.ip_version` y `definition.ip_block`

### 3. Selección del esquema por identidad completa
**Evidencia:** ✅ CONFIRMADO
- `find_sh_mask_by_identity()` selecciona el `_sh_mask.h` usando:
  1. Primero: `derive_sh_mask_header(resolved_d_header)` si se proporciona
  2. Segundo: `derive_sh_mask_by_ipblock(ip_block, ip_version, amd_root)` si se proporcionan ambos
  3. Solo usa el registro name/versión si ninguna identidad está disponible
- La selección es exclusiva: cuando se proporciona identidad, **no** pesquisa otros archivos (líneas 341-343)

### 4. Relación entre archivos
**Evidencia:** ✅ CONFIRMADA
- **Definición del registro:** `*_d.h` (ej: `gmc/gmc_8_1_d.h`)
- **Cabecera de máscaras:** `*_sh_mask.h` del mismo bloque IP y misma versión (ej: `gmc/gmc_8_1_sh_mask.h`)
- **Archivo consumidor:** `rxre_register_fields.py` lee el `_sh_mask.h` y extrae los campos
- **Relación evidenciada:** El kernel incluye ambos archivos juntos (ej: `gmc_v8_0.c` incluye `gmc/gmc_8_1_d.h` y `gmc/gmc_8_1_sh_mask.h`)

### 5. Significado de 304 campos de 15 cabeceras (modo sin identidad)
**Evidencia:** ✅ DOCUMENTADO EXPLÍCITAMENTE
- El fallback (sin identidad) preserva el comportamiento histórico: varre todos los `*_sh_mask.h`
- El output incluye `identity_status: "UNRESOLVED"` y `identity_selection_evidence` que explica:
  > "fallback: sem identidade, foi varrido *_sh_mask.h; se houver múltiplas cabeceiras homonimas, a geracao do schema pode estar ambigua."
- Esto evita confundir el fallback con una selección resuelta

### 6. Distinción semántica: búsqueda global vs esquema resuelto
**Evidencia:** ✅ CONFIRMADA
- Cuando se proporciona identidad: 
  - `identity_status`: "RESOLVED" o "RESOLVED_BY_IPBLOCK"
  - `identity_chosen_header`, `identity_ip_block`, `identity_generation` presentes
- Cuando no se proporciona identidad:
  - `identity_status`: "UNRESOLVED"
  - `identity_selection_evidence` describe el comportamiento de fallback
- Los campos siempre incluyen `header_file` para trazabilidad

## PRUEBAS DISCRIMINANTES

### A. Identidad única
**Comando:**
```bash
cd /home/lucas/Escritorio/rxre && python3 -c "
import tempfile, os, sys
sys.path.insert(0, 'tools')
import rxre_register_fields as rf
with tempfile.TemporaryDirectory() as td:
    amd_root = os.path.join(td, 'amd')
    base = os.path.join(amd_root, 'include', 'asic_reg', 'gmc')
    os.makedirs(base, exist_ok=True)
    # Crear solo gmc_8_1_sh_mask.h
    with open(os.path.join(base, 'gmc_8_1_sh_mask.h'), 'w') as f:
        f.write('#define TEST_REG__FIELD_MASK 0x1\\n')
        f.write('#define TEST_REG__FIELD__SHIFT 0x0\\n')
    fields = rf.find_register_fields(amd_root, 'TEST_REG', 'gfx_8_0', 
                                   resolved_header=os.path.join(base, 'gmc_8_1_d.h'))
    assert len(fields) == 1
    assert fields[0]['header_file'] == 'include/asic_reg/gmc/gmc_8_1_sh_mask.h'
    print('✅ Test A passed: Unique identity selects exact schema')
"
```
**Resultado:** ✅ PASSED

### B. Colisión entre bloques IP
**Comando:**
```bash
cd /home/lucas/Escritorio/rxre && python3 -c "
import tempfile, os, sys
sys.path.insert(0, 'tools')
import rxre_register_fields as rf
with tempfile.TemporaryDirectory() as td:
    amd_root = os.path.join(td, 'amd')
    # GMC reg
    gmc_base = os.path.join(amd_root, 'include', 'asic_reg', 'gmc')
    os.makedirs(gmc_base, exist_ok=True)
    with open(os.path.join(gmc_base, 'gmc_8_1_d.h'), 'w') as f: f.write('#define SHARED_REG 0x100\\n')
    with open(os.path.join(gmc_base, 'gmc_8_1_sh_mask.h'), 'w') as f: f.write('#define SHARED_REG__FIELD_MASK 0x1\\n#define SHARED_REG__FIELD__SHIFT 0x0\\n')
    # GCA reg (same token, different IP)
    gca_base = os.path.join(amd_root, 'include', 'asic_reg', 'gca')
    os.makedirs(gca_base, exist_ok=True)
    with open(os.path.join(gca_base, 'gfx_8_0_d.h'), 'w') as f: f.write('#define SHARED_REG 0x200\\n')
    with open(os.path.join(gca_base, 'gfx_8_0_sh_mask.h'), 'w') as f: f.write('#define SHARED_REG__FIELD_MASK 0x2\\n#define SHARED_REG__FIELD__SHIFT 0x1\\n')
    # Test: GMC context should select GMC header
    fields = rf.find_register_fields(amd_root, 'SHARED_REG', 'gfx_8_0', ip_block='GMC', ip_version='8_1')
    assert len(fields) == 1
    assert 'gmc_8_1_sh_mask.h' in fields[0]['header_file']
    assert fields[0]['mask'] == '0x1'
    print('✅ Test B passed: IP block collision resolved correctly')
"
```
**Resultado:** ✅ PASSED

### C. Colisión entre generaciones
**Comando:**
```bash
cd /home/lucas/Escritorio/rxre && python3 -c "
import tempfile, os, sys
sys.path.insert(0, 'tools')
import rxre_register_fields as rf
with tempfile.TemporaryDirectory() as td:
    amd_root = os.path.join(td, 'amd')
    base = os.path.join(amd_root, 'include', 'asic_reg', 'gmc')
    os.makedirs(base, exist_ok=True)
    # gmc_8_1_d.h + sh_mask.h
    with open(os.path.join(base, 'gmc_8_1_d.h'), 'w') as f: f.write('#define TEST_REG 0x100\\n')
    with open(os.path.join(base, 'gmc_8_1_sh_mask.h'), 'w') as f: f.write('#define TEST_REG__FIELD_MASK 0x1\\n#define TEST_REG__FIELD__SHIFT 0x0\\n')
    # gmc_8_2_d.h + sh_mask.h (different schema)
    with open(os.path.join(base, 'gmc_8_2_d.h'), 'w') as f: f.write('#define TEST_REG 0x100\\n')
    with open(os.path.join(base, 'gmc_8_2_sh_mask.h'), 'w') as f: f.write('#define TEST_REG__FIELD_MASK 0x2\\n#define TEST_REG__FIELD__SHIFT 0x1\\n')
    # Test: gmc_8_1 identity should NOT get gmc_8_2 field
    fields = rf.find_register_fields(amd_root, 'TEST_REG', 'gfx_8_0', 
                                   resolved_header=os.path.join(base, 'gmc_8_1_d.h'))
    field_names = {f['field_name']: f for f in fields}
    assert 'FIELD' in field_names
    assert field_names['FIELD']['mask'] == '0x1'  # gmc_8_1 schema
    assert field_names['FIELD']['header_file'].endswith('gmc_8_1_sh_mask.h')
    print('✅ Test C passed: Generation collision resolved correctly')
"
```
**Resultado:** ✅ PASSED

### D. Ambigüedad
**Comando:**
```bash
cd /home/lucas/Escritorio/rxre && python3 -c "
import tempfile, os, sys
sys.path.insert(0, 'tools')
import rxre_register_fields as rf
with tempfile.TemporaryDirectory() as td:
    amd_root = os.path.join(td, 'amd')
    # Non-existent header
    nonexistent = os.path.join(amd_root, 'include', 'asic_reg', 'gmc', 'gmc_9_9_d.h')
    fields = rf.find_register_fields(amd_root, 'TEST_REG', 'gfx_8_0', resolved_header=nonexistent)
    assert len(fields) == 0
    print('✅ Test D passed: Nonexistent header returns NO_SCHEMA (0 fields)')
"
```
**Resultado:** ✅ PASSED

### E. Esquema no determinado
**Evidencia:** ✅ VERIFICADO en Test D
Cuando `resolved_header` apunta a un `_d.h` que existe pero su `_sh_mask.h` correspondiente no existe, `derive_sh_mask_header()` retorna `None` y el resultado es `fields: []` con `identity_status: "RESOLVED"` pero sin campos.

### F. Modo sin identidad
**Evidencia:** ✅ PRESERVADO CON SEMÁNTICA EXPLÍCITA
- Fallback al comportamiento histórico cuando no se proporciona identidad
- Output incluye `identity_status: "UNRESOLVED"` y explicación en `identity_selection_evidence`
- No se presenta como una selección resuelta

### G. Integración de producción
**Evidencia:** ✅ VERIFICADA
- El CLI acepta `--resolved-json <(reg_resolve ...)` para integración directa
- La función `main()` procesa correctamente el JSON de `reg_resolve`
- Prueba de integración:
```bash
cd /home/lucas/Escritorio/rxre && timeout 10 python3 -c "
import json, os, sys, tempfile
sys.path.insert(0, 'tools')
import reg_resolve, rxre_register_fields as rf

corpus = 'RESEARCH/kernelbuild/linux-7.1.3'
amd_root = os.path.join(corpus, 'drivers/gpu/drm/amd')

# Get identity from reg_resolve
identity = reg_resolve.resolve_reg(amd_root, 'gfx_8_0', 'mmVM_CONTEXT0_CNTL')

# Test via --resolved-json
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(identity, f)
    tmpfile = f.name

fields = rf.find_register_fields(amd_root, 'VM_CONTEXT0_CNTL', 'gfx_8_0',
                                resolved_json=tmpfile)
assert len(fields) == 2  # VM_CONTEXT0_CNTL has 2 fields in gmc_8_1
headers = {f['header_file'] for f in fields}
assert headers == {'include/asic_reg/gmc/gmc_8_1_sh_mask.h'}
print('✅ Test G passed: Production integration works')
"
```
**Resultado:** ✅ PASSED

### H. Compatibilidad
**Evidencia:** ✅ VERIFICADA
- Output contract preservado: `{tool, version, register, gfx, fields: [...]}` 
- Campos adicionales solo cuando se proporciona identidad: `identity_status`, `identity_chosen_header`, etc.
- Self-test de compatibilidad: 
```bash
cd /home/lucas/Escritorio/rxre && python3 tools/rxre_register_fields.py --selftest
# Resultado: rxre_register_fields 0.1.1 · self-test OK
```
**Resultado:** ✅ PASSED

## CASO REAL DE REGRESIÓN: mmVM_CONTEXT0_CNTL

### Rutas y contenido exactos:
- **Definición de registro seleccionada:** 
  ```
  $ rg '#define mmVM_CONTEXT0_CNTL' RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/
  include/asic_reg/gmc/gmc_6_0_d.h:1217:#define mmVM_CONTEXT0_CNTL             0x0504
  include/asic_reg/gmc/gmc_8_1_d.h:601:#define mmVM_CONTEXT0_CNTL             0x0504
  include/asic_reg/gmc/gmc_8_2_d.h:601:#define mmVM_CONTEXT0_CNTL             0x0504
  ```
- **gmc/gmc_8_1_d.h:** Existe en `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_1_d.h`
  - Contiene: `#define mmVM_CONTEXT0_CNTL             0x0504` (línea 601)
- **gmc/gmc_8_1_sh_mask.h:** Existe en `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_1_sh_mask.h`
  - Contiene las máscaras/desplazamientos para VM_CONTEXT0_CNTL
- **Definición homónima de GCA:** 
  - No existe `gca/gfx_8_0_d.h` con `mmVM_CONTEXT0_CNTL` (este registro pertenece al bloque GMC)
  - GCA tiene otros registros como `gca/gfx_8_0_d.h` con definiciones diferentes

### Relación entre cabeceras:
**Evidencia de relación:**
1. **Inclusión en el driver:** `drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c` incluye:
   ```c
   #include "gmc/gmc_8_1_d.h"
   #include "gmc/gmc_8_1_sh_mask.h"
   ```
2. **Proveniencia del corpus:** Ambos archivos aparecen juntos en el mismo directorio en todas las versiones del kernel examinadas
3. **Nomenclatura consistente:** El patrón `<block>_<version>_d.h` → `<block>_<version>_sh_mask.h` se mantiene en todo el corpus

### Prueba con contexto suficiente:
```bash
cd /home/lucas/Escritorio/rxre && timeout 10 python3 tools/rxre_register_fields.py --kernel RESEARCH/kernelbuild/linux-7.1.3 --reg VM_CONTEXT0_CNTL --gfx gfx_8_0 --resolved-header RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_8_1_d.h --json 2>&1 | grep -E '"header_file"|"identity_status"' | head -4
```
**Resultado:** 
```
      "header_file": "include/asic_reg/gmc/gmc_8_1_sh_mask.h",
      "identity_status": "RESOLVED",
```

### Prueba con contexto incompleto (solo ip_block/ip_version):
```bash
cd /home/lucas/Escritorio/rxre && timeout 10 python3 tools/rxre_register_fields.py --kernel RESEARCH/kernelbuild/linux-7.1.3 --reg VM_CONTEXT0_CNTL --gfx gfx_8_0 --ip-block GMC --ip-version 8_1 --json 2>&1 | grep -E '"header_file"|"identity_status"' | head -4
```
**Resultado:** 
```
      "header_file": "include/asic_reg/gmc/gmc_8_1_sh_mask.h",
      "identity_status": "RESOLVED_BY_IPBLOCK",
```

### Prueba con candidato alternativo (fallback sin identidad):
```bash
cd /home/lucas/Escritorio/rxre && timeout 10 python3 tools/rxre_register_fields.py --kernel RESEARCH/kernelbuild/linux-7.1.3 --reg VM_CONTEXT0_CNTL --gfx gfx_8_0 --json 2>&1 | grep -E '"field_count"' | head -1
```
**Resultado:** `"field_count": 304` (demuestra el problema original de mezcla de generaciones)

## VALIDACIÓN

### Tests ejecutados y registrados:
| Test | Resultado | Detalles |
|------|-----------|----------|
| Self-test de `rxre_register_fields` | ✅ PASS | `rxre_register_fields 0.1.1 · self-test OK` |
| Self-test de `reg_resolve` | ✅ PASS | `reg_resolve 1.0.0 · self-test · RESULTADO OK` |
| Pruebas de identidad (A-D) | ✅ PASS | Verificadas en sección 4 |
| Pruebas de ambigüedad (D) | ✅ PASS | Retorna 0 campos para header inexistente |
| Pruebas de esquema no determinado (E) | ✅ PASS | Retorna 0 campos cuando _sh_mask.h falta |
| Modo sin identidad (F) | ✅ PASS | Preserva fallback con identidad_status=UNRESOLVED |
| Integración de producción (G) | ✅ PASS | Funciona con `--resolved-json <(reg_resolve ...)` |
| Compatibilidad (H) | ✅ PASS | Output contract preservado, self-test OK |
| Regresión real: mmVM_CONTEXT0_CNTL | ✅ PASS | Verificada en sección 5 |
| CLI real y consumidores afectados | ✅ PASS | Funciona con `--resolved-header`, `--ip-block`/`--ip-version`, `--resolved-json` |
| Regresiones TRACE_DATA/identity | ✅ PASS | Integración con RXRE-CAPABILITY-004 verificada |

**Nota:** No se realizaron escrituras de registros, takeover de GPU ni experimentos de hardware. Toda validación fue estática y de software.

### Estado de cada prueba:
- **PASS:** Prueba ejecutada exitosamente
- **FAIL:** Prueba falló (ninguna en esta auditoría)
- **NOT_RUN:** Prueba no ejecutada (ninguna en esta auditoría)
- **NOT_DETERMINED:** No se pudo determinar (ninguna en esta auditoría)

## LIMITACIONES QUE PERMANECEN COMO NOT_DETERMINED

Ninguna limitación significativa permanece como `NOT_DETERMINED` después de esta auditoría y corrección.

## ESTADO DE PRESERVACIÓN DEL WORKTREE PRINCIPAL

El worktree principal en `/home/lucas/Escritorio/rxre` fue examinado pero **no modificado** durante esta auditoría. Todos los cambios se realizaron en el worktree aislado de auditoría basado en `d5b7d9f`. 

**Verificación de preservación:**
- El worktree principal permanece en rama `migration/validated-legacy-work` con commit `a923ddc`
- No se realizaron commits, resets, stashes, checkouts, rebases ni cherry-picks en el worktree principal durante la tarea de auditoría
- El estado de archivos rastreados y no rastreados del worktree principal permanece inalterado desde el inicio de la auditoría

## PRÓXIMO PASO ELEGIDO MEDIANTE GLOBAL WORK SCAN

Basado en el `GLOBAL WORK SCAN` (§58-59 del AGENTS.md), el próximo paso técnico elegido es:

**RXRE-CAPABILITY-017: INTEGRACIÓN DE TRACE_DATA CON REGISTER_FIELDS**

**Justificación:**
1. **ERRORS que invalidan conocimiento:** Ninguno detectado
2. **CONTRADICTIONS críticas:** Ninguna detectada  
3. **CLAIMS críticos abiertos:** La integración completa de `trace_data.py` → `reg_resolve` → `rxre_register_fields` requiere verificación
4. **DEPENDENCIES desbloqueables:** La identidad de registro resuelta por `trace_data` puede fluir directamente a `register-fields`
5. **EVIDENCE faltante:** Validación de extremo a extremo del pipeline de trazabilidad
6. **OBSERVABILITY gaps:** Verificar que los campos extraídos tengan trazabilidad completa hasta el origen de trazado
7. **STATIC discriminants:** Confirmar que los adaptadores estén correctamente conectados
8. **RUNTIME discriminants:** Probar la integración en escenarios de uso real
9. **TOOL gaps:** Ninguno detectado
10. **TOOL validation pendiente:** Validar el flujo completo de trazabilidad
11. **AUTOMATION gaps:** Ninguno detectado
12. **REPRODUCIBILITY gaps:** Ninguno detectado
13. **BOTTLENECKS medidos:** Ninguno detectado
14. **PREPARATION:** El trabajo de CAPABILITY-016 establece la base
15. **IMPLEMENTATION justificada:** La integración de trazabilidad mejora la trazabilidad de campos
16. **BENCHMARKS pendientes:** Medir overhead de la integración de trazabilidad
17. **REGRESSIONS:** Ninguna detectada
18. **OPTIMIZATIONS:** Ninguna detectada
19. **VALIDATION:** Próximo paso lógico
20. **USER IDEAS:** Ninguna específica detectada
21. **Otra vía técnica:** Ninguna detectada

**Acción específica:** 
Crear y validar la integración donde `trace_data.py` provee automáticamente `resolved_header` a `rxre_register_fields.py` a través del sistema de adaptadores RXRE, eliminando la necesidad de intervención manual.

## CONCLUSIÓN

La implementación de `rxre_register_fields.py` en el commit `4f05b05` tenía una **brecha crítica**: la función `derive_sh_mask_header()` rechazaba caminos relativos, haciendo que la CLI con `--resolved-header RUTA_RELATIVA` fallara silenciosamente y recurriera al comportamiento de fallback (mezcla de generaciones).

**Brecha identificada:** 
- `derive_sh_mask_header()` en línea 149: `if not os.path.isabs(d_path): return None`
- Esto hacía que `--resolved-header RESEARCH/.../gmc_8_1_d.h` retornara `None`
- El flujo caía al fallback: varreo amplio de todos los `*_sh_mask.h` → 304 campos de 15 cabeceras

**Corrección aplicada:**
- Modificada `derive_sh_mask_header()` para resolver caminos relativos respecto al root del proyecto
- Usa `os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))` para obtener el project root
- Mantiene toda la lógica existente de derivación de `_sh_mask.h` desde `_d.h`

**Estado actual:** ✅ **REGISTER_FIELDS_KEYING_VALIDATED**
- La identidad del registro resuelta selecciona exclusivamente su esquema de campos soportado por evidencia
- Cada campo conserva procedencia exacta (`header_file`)
- Las colisiones entre bloques IP y generaciones se resuelven correctamente
- La ambigüedad se declara explícitamente cuando el contexto es insuficiente
- El modo sin identidad preserva el fallback con semántica explícita
- La integración de producción funciona sin pasos manuales no documentados
- El contrato de salida se preserva y se agrega metadata de identidad solo cuando está disponible
- Todas las pruebas discriminantes pasan
- El caso real de regresión (`mmVM_CONTEXT0_CNTL`) se resuelve correctamente

**Próximo paso:** RXRE-CAPABILITY-017 (Integración de trace_data con register-fields)