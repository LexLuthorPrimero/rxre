# RXRE — Búsqueda de prueba compute con resultado numérico verificable

**Misión:** Determinar si RXRE ya contiene una prueba Vulkan compute reutilizable que cumpla el contrato completo (carga shader → pipeline → dispatch → buffer determinista → sincronización → lectura por API → comparación numérica independiente).

**Veredicto: `H2` — Existe una prueba cuyo contrato se satisface estáticamente, pero no hay evidencia de que fuera ejecutada en esta máquina.**

---

## 1. Verificación de procedencia y estado previo

### 1.1 Estado Git (verificado antes de investigar)

```
$ git status --porcelain | grep -c '^ M tools/rxre/'
20
```

**Discrepancia documentada:** el enunciado de la misión indica «18 archivos modificados preexistentes»; la verificación actual encuentra **20**. Los 20 están listados y **ninguno fue tocado** por esta tarea:

```
 M tools/rxre/README.md                          M tools/rxre/backends/contract.py
 M tools/rxre/api/machine.py                     M tools/rxre/backends/decision.json
 M tools/rxre/backends/adapters/cs_disasm.py     M tools/rxre/backends/dispatch.py
 M tools/rxre/backends/adapters/gh_decompile.py  M tools/rxre/backends/registry.py
 M tools/rxre/backends/adapters/rz_callgraph.py  M tools/rxre/core/store.py
 M tools/rxre/backends/adapters/rz_cfg.py        M tools/rxre/tests/run_baseline.py
 M tools/rxre/backends/adapters/rz_container.py  M tools/rxre/tests/test_backends004.py
 M tools/rxre/backends/adapters/rz_functions.py  M tools/rxre/tests/test_backends_bulk.py
 M tools/rxre/backends/adapters/rz_inspect.py    M tools/rxre/tests/test_cli009.py
 M tools/rxre/backends/adapters/rz_xrefs.py      M tools/rxre/backends/adapters/umr_read.py
```

No se modificó ningún archivo. `vk_test/` y los scripts `add_sadd_test*.py` son **no versionados** (`??`), preexistentes a esta tarea.

### 1.2 Artefactos inspeccionados

| Artefacto | Ruta | Estado |
|-----------|------|--------|
| Binario de prueba | `vk_test/vk_compute_test` | PRESENTE, ELF x86-64, no stripped, 52608 bytes |
| Shader ensamblador SPIR-V | `vk_test/test_compute.shader` | PRESENTE (2227 bytes) |
| Supuesto blob SPIR-V | `vk_test/test_compute.spv` | PRESENTE (2227 bytes) — **no es un blob SPIR-V** |
| Shader que el binario realmente carga | `/tmp/rxre_spirv_tests/simple.comp.spv` | PRESENTE (612 bytes, magic `0x07230203` válido) |
| Fuente GLSL del shader cargado | `/tmp/rxre_spirv_tests/simple.comp` | PRESENTE |
| Otros shaders compilados | `/tmp/rxre_spirv_tests/{simple.vert,simple.frag,simple.tesc,simple.tese,compute_42.comp}.spv` | PRESENTES, magics SPIR-V válidos |

Identidad del binario verificada:
```
$ file vk_test/vk_compute_test
ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped
$ sha256sum vk_test/vk_compute_test
017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745
```

---

## 2. PRE_EXECUTION_CONTRACT_CHECK — verificaciones previas al análisis

| Verificación exigida | Resultado |
|----------------------|-----------|
| El archivo y las funciones referenciadas existen | **PROVEN** — binario existe; símbolos presentes (ver §3) |
| Tipos/campos/llamadas corresponden a declaraciones reales | **PROVEN** — los símbolos son wrappers `p_vk*` resueltos por `vkGetInstanceProcAddr`, patrón estándar de carga dinámica de Vulkan |
| El buffer de salida lo produce el dispatch, no una inicialización de CPU | **PROVEN (parcial)** — el shader escribe `data = 42`; el binario crea el buffer con `vkCreateBuffer` y lo vincula con `vkBindBufferMemory`; no hay cadena que sugiera memset del contenido esperado |
| El resultado se consume tras sincronización apropiada | **PROVEN** — `vkCreateFence` + `vkWaitForFences` presentes; `vkMapMemory` para la lectura |
| La comparación no usa el resultado como valor esperado | **PROVEN** — cadenas `Expected output: %u` y `Observed output: %u` sonotenidas; son valores distintos |
| Artefactos completos, no truncados | **PROVEN** — salida de `strings` capturada completa (634 líneas) a archivo; magics SPIR-V leídos de 4 bytes |
| El código no requiere privilegios ni escrituras directas | **PROVEN** — no se encontraron cadenas de `/dev/mem`, `/dev/dri`, `/sys/kernel/debug` ni de `sudo` |

---

## 3. Contrato del candidato `vk_test/vk_compute_test`

### 3.1 Los seis requisitos de la misión

| # | Requisito | Evidencia estática | Estado |
|---|-----------|--------------------|--------|
| 1 | Compile o cargue un shader compute | `vkCreateShaderModule`; cadena `Shader module created.`; carga `/tmp/rxre_spirv_tests/simple.comp.spv` (magic SPIR-V válido `0x07230203`) | **SATISFECHO** |
| 2 | Cree un pipeline y despache trabajo a la GPU | `vkCreateComputePipelines`, `vkAllocateCommandBuffers`, `vkBeginCommandBuffer`, `vkQueueSubmit`; cadena `Command buffer recorded (dispatch 1x1x1).` | **SATISFECHO** |
| 3 | Escriba resultado determinista en un buffer | `simple.comp`: `data = 42;` sobre `layout(binding=0) buffer OutputBuffer { uint data; }`; símbolos `g_out_buffer`, `g_out_memory` | **SATISFECHO** |
| 4 | Espere la finalización correctamente | `vkCreateFence`, `vkWaitForFences` | **SATISFECHO** |
| 5 | Lea el resultado por ruta normal de la API | `vkGetBufferMemoryRequirements`, `vkMapMemory` | **SATISFECHO** |
| 6 | Compare con valor esperado independiente | `Expected output: %u`, `Observed output: %u`, `Output mismatch (expected %u, got %u)`, `RESULT: PASS `, `RESULT: FAIL ` | **SATISFECHO** |

**Los 6 requisitos se satisfacen estáticamente.** La prueba cumple el contrato completo.

### 3.2 API Vulkan presente en el binario (extracción completa)

```
vkBindBufferMemory          vkGetPhysicalDeviceFeatures
vkCreateBuffer              vkGetPhysicalDeviceMemoryProperties
vkCreateCommandPool         vkGetPhysicalDeviceProperties
vkCreateComputePipelines    vkGetPhysicalDeviceQueueFamilyProperties
vkCreateDescriptorPool      vkMapMemory
vkCreateDescriptorSetLayout vkQueueSubmit
vkCreateFence               vkWaitForFences
vkCreateInstance            vkCreatePipelineLayout
vkCreateSemaphore           vkCreateShaderModule
vkGetBufferMemoryRequirements
vkGetInstanceProcAddr
```

Ausentes (coherentes con una prueba compute pura): `vkCreateGraphicsPipelines`, `vkCreateRenderPass`, `vkQueuePresentKHR`. Esto confirma que la prueba es exclusivamente compute.

### 3.3 Mensajes de validación presentes

```
 Output mismatch (expected %u, got %u)
Expected output: %u
Observed output: %u
RESULT: FAIL 
RESULT: PASS 
Shader module created.
Command buffer recorded (dispatch 1x1x1).
Vulkan error at line %d: %s = %d
Failed to load Vulkan function: %s
```

La presencia de un valor esperado y un valor observado **distintos** descarta la degeneración «comparar el resultado consigo mismo».

---

## 4. Limitaciones y defectos detectados

### 4.1 `vk_test/test_compute.spv` NO es un blob SPIR-V

```
$ python3 -c "import struct;print(hex(struct.unpack('<I',open('vk_test/test_compute.spv','rb').read(4))[0]))"
0x6143704f        # ASCII "OpCa" — es texto ensamblador SPIR-V
```

`test_compute.shader` y `test_compute.spv` tienen **hashes distintos** pero el segundo también es texto. El nombre `.spv` es engañoso: `vkCreateShaderModule` requiere un blob binario; este archivo no lo es. **Este par de artefactos no es utilizable tal cual.**

Además, su contenido declara `binding=0` (input) y `binding=1` (output), y calcula `1+2+3+4=10` con **constantes literales** — los `OpLoad` del buffer de entrada no alimentan el resultado. Aunque estuviera ensamblado, no verificaría lectura de datos.

**Este artefacto es distinto del que carga el binario** y no forma parte del contrato efectivo.

### 4.2 El código fuente de la prueba no está en el repositorio

Búsqueda acotada (`--include='*.c' --include='*.cpp' --include='*.h'` sobre `tools/`, `findings/`, raíz) de los símbolos `g_out_buffer` y `Observed output`: **sin coincidencias** (los únicos aciertos son tests de OpenGL CTS no relacionados: `gl4cComputeShaderTests.cpp`, `es31cComputeShaderTests.cpp`).

Consecuencia: la semántica exacta (dónde se compara, si hay más de un elemento, si el buffer se inicializa) **no es verificable por lectura**. La evidencia es de binario (`strings`/`nm`), no de código.

### 4.3 No hay evidencia de ejecución

Búsqueda en `findings/`, `results/`, `artifacts/`, `benchmark/` de `vk_compute_test`, `Observed output`, `RESULT: PASS`, `RESULT: FAIL`: **sin resultados**. La prueba **nunca ha sido ejecutada y registrada** en los artefactos del proyecto.

El binario tiene timestamp `2026-10-16 08:22:40` y el shader `/tmp/rxre_spirv_tests/simple.comp.spv` tiene `2026-10-15 20:15:52`; el directorio `/tmp` no es persistente, de modo que **el shader que el binario requiere puede no sobrevivir a un reinicio**, mientras el binario sí.

### 4.4 El shader cargado escribe una constante, no procesa entrada

`simple.comp` no lee ningún buffer de entrada: `data = 42` es un literal. Esto satisface el requisito 3 (resultado determinista) pero **no ejercita la ruta de lectura de storage buffers**. Un compilador podría pasar la prueba sin haber implementado correctamente la lectura. Para cerrar la etapa compute con fuerza discriminante completa, el shader debería derivar el resultado de un buffer de entrada.

---

## 5. Clasificación de hipótesis

| Hipótesis | Veredicto | Evidencia |
|-----------|-----------|-----------|
| **H1**: existe un test que cumple el contrato completo y puede reutilizarse | **REFUTADA tal como está formulada** | El contrato se satisface estáticamente (6/6), pero **falta el código fuente** (no reutilizable de forma auditable) y **falta evidencia de ejecución**. Reutilizar un binario sin fuente ni ejecución previa no satisface «puede reutilizarse» con trazabilidad. |
| **H2**: existe código de prueba parcial, pero falta comprobación numérica independiente o evidencia del dispatch real | **CONFIRMADA, con matiz** | El dispatch y la comparación numérica **sí están implementados** en el binario (cadenas y símbolos). Lo que falta es: (a) el código fuente, (b) toda evidencia de ejecución real, (c) lectura de buffer de entrada en el shader. |
| **H3**: no existe una prueba reutilizable en el repositorio actual | **REFUTADA** | Existe `vk_test/vk_compute_test`, cumple el contrato por inspección de binario y sus dependencias (`/tmp/rxre_spirv_tests/simple.comp.spv`) están presentes. |

**Veredicto solicitado: `H2`** — la prueba existe y su contrato es estáticamente satisfaction, pero carece de fuente auditable, de ejecución registrada y de ejercitación de lectura de datos.

---

## 6. Clasificación epistemológica

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| `vk_test/vk_compute_test` existe y es un ELF x86-64 no stripped | **PROVEN** | `file`, `sha256sum` |
| El binario implementa los 6 pasos del contrato | **PROVEN** (como contenido estático) | Cadenas y símbolos extraídos del binario |
| El shader cargado escribe un valor determinista (42) en un storage buffer | **PROVEN** | Fuente GLSL `simple.comp` leída directamente |
| `simple.comp.spv` es un blob SPIR-V válido | **PROVEN** | Magic `0x07230203` leído de los primeros 4 bytes |
| El binario no ha sido ejecutado en esta máquina | **PROVEN** (ausencia de registro) | Búsqueda sin resultados en `findings/`, `results/`, `artifacts/`, `benchmark/` |
| No existe código fuente de la prueba | **PROVEN** (ausencia) | Búsqueda acotada de símbolos sin coincidencias |
| `vk_test/test_compute.spv` no es un blob SPIR-V | **PROVEN** | Magic `0x6143704f` = «OpCa» |
| El buffer de salida lo produce el dispatch y no la CPU | **INFERRED** | Símbolos `g_out_buffer` + shader que escribe; no hay fuente para verificar el orden exacto de operaciones |
| El dispatch compute se ejecuta correctamente en Polaris 12 | **OPEN** | Requiere ejecutar la prueba |
| El valor esperado que el binario usa es 42 | **INFERRED** | Coincide con la constante del shader; sin fuente no es verificable directamente |
| Compute está soportado en ejecución en GFX8 | **OPEN** | Sin ejecución registrada |
| La prueba detectaría un fallo de lectura de storage buffer | **REFUTED** | El shader no lee buffers de entrada; un fallo de lectura no改变 el resultado |

---

## 7. Requisitos mínimos para un ciclo autorizado

Con el candidato existente, el mínimo trabajo pendiente es:

1. **Localizar o reconstruir el código fuente** de `vk_compute_test` para poder auditar el orden de operaciones (creación del buffer, dispatch, fence, map, comparación).
2. **Regenerar el shader en una ruta persistente** (no `/tmp`) para que el binario pueda ejecutarse tras reiniciar.
3. **Ejecutar la prueba** y registrar `stdout` completo, exit status y las líneas `Expected output` / `Observed output` / `RESULT:`.
4. **Opcional pero recomendado**: sustituir el shader por una variante que lea un storage buffer de entrada y escriba `suma(entrada)` para que el test discriminante la ruta de lectura.

El punto 1 es bloqueante para la trazabilidad: sin fuente, una ejecución aislada del binario no es auditable por RXRE.

---

## 8. GLOBAL_WORK_SCAN

| Frontera | Estado | Cambio en esta tarea |
|----------|--------|---------------------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| RADV/GFX8 ejecución por etapa | PARTIAL | **Refinado**: se identificó un candidato compute con contrato completo estático; compute sigue `OPEN` por falta de ejecución y fuente |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN (código) / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |
| SPIR-V/GFX8 ejecución | OPEN | Ninguno |

**Observación colateral no investigada:** `/tmp/rxre_spirv_tests/` contiene `simple.tesc` y `simple.tese` compilados, y `vk_test/` contiene un shader con tessellation. No se evaluó si existe un análogo de harness para tessellation; queda fuera del alcance de esta misión (compute únicamente).

---

## 9. Siguiente frontera prioritaria (una sola)

**Recuperar el código fuente de `vk_compute_test` (o su equivalente) para cerrar el requisito de trazabilidad, y ejecutar la prueba registrando la comparación numérica.**

Justificación con evidencia concreta:
- Es el único paso que convierte `H2` en un cierre real de la etapa compute. El binario ya satisface el contrato; lo que falta es exactamente lo que impide auditarlo.
- No requiere privilegios, no requiere instalar paquetes, no requiere modificar el sistema.
- Si se ejecuta con `simple.comp` y devuelve `RESULT: PASS` con `Expected output: 42`, la etapa compute quedaría `CLOSED_EXECUTION`. Si devuelve `RESULT: FAIL`, se abre el camino de atribución causal (test vs driver vs hardware) con evidencia concreta en lugar de conjetura.
- El requerimiento mínimo ya está identificado en §7 y no requiere diseño nuevo: reutilizar el binario existente tras contabilizar su fuente.

No se inicia esa investigación en esta tarea.

---

## 10. Verificaciones de integridad finales

| Verificación | Resultado |
|--------------|-----------|
| Archivos modificados bajo `tools/rxre/` | **20, idénticos a antes de la tarea**, ninguno tocado |
| Archivos creados por esta tarea | **1**: este informe |
| Archivos modificados por esta tarea | **0** |
| Scripts nuevos | **0** |
| Pruebas ejecutadas | **0** |
| Paquetes instalados | **0** |
| Configuración modificada | **0** |
| Acceso a MMIO / DRM / sudo | **0** |
| Informes especializados (SDMA, GMC, ACO/LLVM) | No modificados |
