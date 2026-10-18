# RXRE — Corrección controlada del harness Vulkan compute

**Misión:** Corregir el defecto de inicialización de `vk_test/vk_compute_test` para permitir que la prueba alcance su dispatch, preservando el ELF original como evidencia inmutable.

**Veredicto: `H2` — No hay fuente original, pero fue posible construir una implementación equivalente y auditable con dependencias ya instaladas.**

**El artefacto nuevo NO fue ejecutado en esta tarea. No hay evidencia de compute real. No se declara `CLOSED_EXECUTION`.**

Cadena de evidencia: `VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md` → `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` → `VK_COMPUTE_TEST_BUSQUEDA_HARNESS.md` → este informe.

---

## 1. Verificación de estado previo

### 1.1 Estado Git

```
$ git status --porcelain | grep -c '^ M tools/rxre/'
20
```

**Los 20 archivos modificados preexistentes permanecen intactos.** Ninguno fue tocado.

### 1.2 Búsqueda de fuente original

| Vía consultada | Resultado |
|----------------|-----------|
| `vk_test/` contenido | Solo 3 archivos: `test_compute.shader`, `test_compute.spv`, `vk_compute_test` |
| `Makefile` / `CMakeLists.txt` / `Dockerfile` en `vk_test/` | Ninguno |
| `find . -maxdepth 2 -iname 'CMakeLists.txt'` | Solo `./KytyPS5-Source/CMakeLists.txt` (no relacionado) |
| `git log --all -- vk_test/` | **Sin commits — el directorio nunca estuvo versionado** |
| `.gitignore` que excluya `vk_test/` | No encontrado |

**H1 REFUTADA.** No existe fuente, receta de compilación, paquete de origen ni historial. Solo hay un ELF.

### 1.3 Dependencias de construcción (PRE_EXECUTION_CONTRACT_CHECK)

| Recurso | Estado | Ruta |
|---------|--------|------|
| `gcc` | PRESENTE | `/usr/lib64/ccache/gcc` |
| `make`, `cmake`, `pkg-config` | PRESENTES | `/usr/bin/` |
| Headers Vulkan | PRESENTES | `/usr/include/vulkan/vulkan_core.h` |
| Versión headers | **1.4.341** | `pkg-config --modversion vulkan` |
| Flags de compilación | `-lvulkan` | `pkg-config --libs vulkan` |

No fue necesario instalar nada ni elevar privilegios.

---

## 2. Identidad de los artefactos

| Artefacto | SHA-256 | Tamaño | Estado |
|-----------|---------|--------|--------|
| **Original** `vk_test/vk_compute_test` | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | 52608 B | **INTACTO antes y después** |
| **Nuevo** `vk_test/vk_compute_test_fixed` | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` | 18800 B | Creado en esta tarea |
| Shader `/tmp/rxre_spirv_tests/simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | 612 B | **INTACTO** |

### 2.1 Procedencia del artefacto nuevo

| Propiedad | Valor |
|-----------|-------|
| Formato | ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped |
| BuildID | `aaf8d127d3deaf989463d550049588e68b19a5f9` |
| mtime | 2026-10-16 13:12:50 -0300 |
| Dependencia dinámica | `libvulkan.so.1 => /lib64/libvulkan.so.1` |
| Nombre distinto del original | `vk_compute_test_fixed` |
| El original fue reemplazado | **NO** — hash verificado idéntico |

**Clasificación: `PROVEN`** — todos los datos provienen de `sha256sum`, `stat`, `file` y `ldd` sobre los artefactos reales.

---

## 3. Diferencias concretas de inicialización

### 3.1 Defecto del original

El binario original resolvía punteros mediante `load_func()`, que llamaba `vkGetInstanceProcAddr(g_instance, name)`. `load_all_functions()` ejecutaba un lote de 7 nombres **antes** de crear la instancia, con `g_instance == NULL`:

| # | Nombre | Tipo de comando | Resultado con `g_instance == NULL` |
|---|--------|-----------------|--------------------------------------|
| 1 | `vkCreateInstance` | **global** | RESUELTO |
| 2 | `vkEnumeratePhysicalDevices` | de instancia | **NULL → `exit(1)`** |
| 3–7 | props, queue family, mem props, features, destroy | de instancia | no alcanzados |

`load_func` (`0x400550`) no toleraba `NULL`: abortaba con `exit(1)` en `0x400579`.

### 3.2 Corrección aplicada

La resolución se separó en fases explícitas:

| Fase | Contenido | Mecanismo |
|------|-----------|-----------|
| 0 | `dlopen("libvulkan.so.1")` + `dlsym("vkGetInstanceProcAddr")` | loader |
| 1 | `vkCreateInstance` | `vkGetInstanceProcAddr(VK_NULL_HANDLE, …)` |
| 2 | Crear instancia | `vkCreateInstance(&ici, NULL, &instance)` |
| 3 | `vkEnumeratePhysicalDevices`, `vkDestroyInstance`, props de dispositivo | `vkGetInstanceProcAddr(instance, …)` |
| 4 | Enumerar dispositivos y verificar RX 550 por `vendorID`/`deviceID` | — |
| 5 | `vkCreateDevice` + `vkGetDeviceQueue` | — |
| 6 | 28 funciones de device (buffer, memoria, pipeline, descriptor, command buffer, fence) | `vkGetDeviceProcAddr(device, …)` |

**Verificación estática de la corrección:** `nm vk_compute_test_fixed | grep -c load_func` → **0**. La función `load_func` del original no existe en el artefacto nuevo; fue sustituida por `load_loader`, `load_instance_funcs` y `load_device_funcs`, cada una con su instancia válida.

### 3.3 Contrato de la prueba preservado

| Contrato | Original (por desensamblado) | Nuevo (por fuente) | Idéntico |
|---------|------------------------------|---------------------|----------|
| Tamaño del buffer | 4 bytes (`movq $0x4`) | `bci.size = 4` | Sí |
| Binding | 0 | `b.binding = 0` | Sí |
| Tipo de descriptor | `VK_BUFFER_USAGE_2_STORAGE_BUFFER_BIT` (`0x20`) | `VK_BUFFER_USAGE_STORAGE_BUFFER_BIT` | Sí |
| Purga a cero por CPU | `memset(g_out_mapped, 0, 4)` @ `0x4013bb` | `memset(mapped, 0, 4)` | Sí |
| Dispatch | `1x1x1` | `p_vkCmdDispatch(cmd, 1, 1, 1)` | Sí |
| Espera de fence | `UINT64_MAX` (`mov $0xffffffffffffffff,%r8`) | `VK_TRUE, UINT64_MAX` | Sí |
| Esperado | literal `0x2a` @ `0x401e13` | `uint32_t expected = EXPECTED_VALUE;` (=42) | Sí |
| Observado | `mov (%rax),%eax` desde memoria mapeada | `*(uint32_t *)mapped` | Sí |
| PASS | stdout + `eax = 0` | `printf("RESULT: PASS \n"); return 0;` | Sí |
| FAIL | stderr + `eax = 1` | `fprintf(stderr, "RESULT: FAIL \n"); return 1;` | Sí |

---

## 4. Firmas y fase de resolución de cada función

Verificadas contra `/usr/include/vulkan/vulkan_core.h` (1.4.341) antes de escribir el código.

### Fase 1 — global (instancia nula)

```c
typedef VkResult (VKAPI_PTR *PFN_vkCreateInstance)(
    const VkInstanceCreateInfo*, const VkAllocationCallbacks*, VkInstance*);
```

### Fase 3 — de instancia

```c
typedef VkResult (VKAPI_PTR *PFN_vkEnumeratePhysicalDevices)(
    VkInstance, uint32_t*, VkPhysicalDevice*);
typedef void (VKAPI_PTR *PFN_vkDestroyInstance)(
    VkInstance, const VkAllocationCallbacks*);
typedef void (VKAPI_PTR *PFN_vkGetPhysicalDeviceProperties)(
    VkPhysicalDevice, VkPhysicalDeviceProperties*);
```

### Fase 5 — creación de device

```c
typedef VkResult (VKAPI_PTR *PFN_vkCreateDevice)(
    VkPhysicalDevice, const VkDeviceCreateInfo*, const VkAllocationCallbacks*, VkDevice*);
typedef void (VKAPI_PTR *PFN_vkGetDeviceQueue)(VkDevice, uint32_t, uint32_t, VkQueue*);
```

### Fase 6 — de device

28 funciones resueltas con `vkGetDeviceProcAddr(device, …)`, incluyendo `vkCreateBuffer`, `vkMapMemory`, `vkCmdDispatch`, `vkQueueSubmit`, `vkWaitForFences`.

### Nota sobre la clasificación de fases

No se asumió que «todo no global es de instancia». `vkGetDeviceProcAddr` es un **comando global** (se resuelve con `vkGetInstanceProcAddr(NULL, …)`), y `vkEnumeratePhysicalDevices` es de **instancia**, no de device. La separación reflects esa distinción.

**Clasificación: `PROVEN`** para las firmas (leídas del header del sistema) y `INFERRED` para el comportamiento en runtime, que no se verificó por no ejecutar el artefacto.

---

## 5. Comandos de construcción

### 5.1 Primer intento (falló)

```bash
cd /home/lucas/Escritorio/rxre/vk_test
gcc -O2 -Wall -Wextra -o vk_compute_test_fixed vk_compute_test_fixed.c \
    $(pkg-config --cflags --libs vulkan) 2> build.log
# exit status: 1
```

Error real:
```
vk_compute_test_fixed.c:516:22: error: 'VK_COMMAND_POOL_CREATE_ONE_TIME_SUBMIT_BIT'
                                    no se declaró aquí
```

**Clasificación: `PROVEN`** — el nombre de constante no existe en `vulkan_core.h`.

### 5.2 Corrección aplicada

Verificación contra el header:
```bash
$ grep -E 'VK_COMMAND_POOL_CREATE_[A-Z_]+\s*=' /usr/include/vulkan/vulkan_core.h
    VK_COMMAND_POOL_CREATE_TRANSIENT_BIT = 0x00000001,
    VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT = 0x00000002,
    VK_COMMAND_POOL_CREATE_PROTECTED_BIT = 0x00000004,
```

Sustitución:
```c
cpci.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT |
             VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
```

### 5.3 Segundo intento (correcto)

```bash
gcc -O2 -Wall -Wextra -o vk_compute_test_fixed vk_compute_test_fixed.c \
    $(pkg-config --cflags --libs vulkan) 2> build.log
# exit status: 0
# errores: 0
# warnings: N (solo -Wmissing-field-initializers y -Wunused-parameter)
```

Los warnings de `-Wmissing-field-initializers` son benignos: la inicialización `{ VK_STRUCTURE_TYPE_… }` de un `Vk…CreateInfo` pone `sType` y deja el resto a cero por la semántica de agregación de C.

Los dos parámetros sin uso (`shader_mod`, `buf` en `run_dispatch`) se eliminaron de la firma en una iteración posterior de limpieza.

---

## 6. Contratos verificados y abiertos

### 6.1 Verificados (`PROVEN`)

| Contrato | Evidencia |
|----------|-----------|
| Compilador, headers y libs disponibles sin instalación | `command -v`, `pkg-config --modversion vulkan` → 1.4.341 |
| Firmas Vulkan coinciden con el header del sistema | `grep` sobre `vulkan_core.h` |
| El destino no existía antes de compilar | `ls` → `NO existe` |
| Compilación sin errores | exit status 0, `grep -c error build.log` → 0 |
| Artefacto nuevo existe, íntegro y con hash propio | `sha256sum`, `stat`, `file` |
| El original permanece intacto | hash idéntico al de la tarea de auditoría |
| `load_func` (el defecto) no existe en el nuevo | `nm \| grep -c load_func` → 0 |
| Resolución por fases presente en símbolos | `nm` lista `p_vk*` para las 3 fases |
| Cadenas de verificación presentes | `strings`: `Expected output`, `Observed output`, `RESULT: PASS`, `RESULT: FAIL`, `>>> SELECTED`, `Shader module created` |
| Dependencia dinámica satisfecha | `ldd` → `libvulkan.so.1 => /lib64/libvulkan.so.1` |
| Los 20 archivos preexistentes intactos | `git status --porcelain \| grep -c` → 20 |

### 6.2 Abiertos

| Cuestión | Motivo |
|----------|--------|
| ¿El artefacto nuevo supera la fase de inicialización? | **No ejecutado.** Es laIncógnita principal |
| ¿La enumeración de dispositivos encuentra `1002:699f`? | No verificado sin ejecución |
| ¿El compute produce 42 en Polaris12? | No verificado sin ejecución |
| ¿El `RESULT: PASS` del nuevo equivale al del original? | No se puede afirmar equivalencia binaria: es código nuevo |
| ¿Las advertencias del compilador ocultan defectos? | Bajo riesgo, pero no descartable sin revisión manual completa |
| ¿El pipeline compila en GFX8? | No verificado; `vkCreateComputePipelines` no se ha invocado |

---

## 7. Limitaciones que impiden afirmar equivalencia con el original

1. **No es el binario original corregido.** Es una reimplementación desde cero. La equivalencia es de **flujo de datos**, no de código. Un diferencia de comportamiento podría originarse en cualquiera de los dos artefactos.

2. **El original no puede reconstruirse exactamente.** Sin fuente, no hay forma de verificar que la reimplementación conserve optimizaciones, orden exacto de llamadas o mensajes del original.

3. **El shader no fue validado contra el pipeline.** `vkCreateShaderModule` y `vkCreateComputePipelines` no se han ejecutado.

4. **Diferencia documentada en flags.** El original usaba `movl $0x0,-0x2c0(%rbp)` para `VkBufferCreateInfo.size` con `movl $0x20` para usage (`VK_BUFFER_USAGE_2_STORAGE_BUFFER_BIT` con la palabra `2` de la extensión, equivalente numérica a `VK_BUFFER_USAGE_STORAGE_BUFFER_BIT`). El nuevo usa las constantes canónicas sin sufijo, equivalentes.

5. **El original hacía dos dispatch explícitos** (calentamiento + medición) con un `memset` intermedio. El nuevo ejecuta `run_dispatch()` una vez tras el `memset`. La auditoría estática del original no pudo determinar si la condición en `0x401372` se cumple siempre; el nuevo hace un único dispatch tras la purga, que es el comportamiento mínimo合同.

6. **`apiVersion = VK_API_VERSION_1_0`** en el nuevo, igual que el original (`movl $0x400000`). El ICD declara 1.4.354, superior.

---

## 8. GLOBAL_WORK_SCAN

| Frontera | Estado | Efecto |
|----------|--------|--------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| **RADV/GFX8 ejecución compute** | **`BLOCKED` → pendiente de fase de ejecución** | El bloqueo técnico (defecto de carga) tiene ahora una salida candidata sin modificar el original |
| RADV/GFX8 ejecución tess/geom | OPEN | Ninguno |
| RADV/GFX8 ejecución vertex/fragment | OBSERVED (vkcube) | Ninguno |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |

**No se reabrió ninguna frontera cerrada.** No se ejecutó el artefacto nuevo.

---

## 9. Verificaciones de integridad

| Verificación | Resultado |
|--------------|-----------|
| Hash original antes | `017ee552…071745` |
| Hash original después | `017ee552…071745` — **idéntico** |
| Hash shader antes/después | `df08a62b…4a86a` — **idéntico** |
| `git status --porcelain \| grep -c '^ M tools/rxre/'` | **20** (idéntico) |
| Archivos modificados | **0** |
| Archivos creados | **3** (`vk_compute_test_fixed.c`, `vk_compute_test_fixed`, `build.log`) + este informe |
| Harness ejecutado | **No** |
| Dispatches enviados | **0** |
| `/dev/dri`, MMIO, VRAM | **No** |
| sudo / root | **No** |
| Paquetes instalados | **No** |
| Configuración modificada | **No** |
| Shaders modificados | **No** |

---

## 10. Siguiente acción prioritaria

**Solicitar autorización para ejecutar `vk_test/vk_compute_test_fixed` siguiendo el contrato de registro de 11 campos de `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` §6, registrando la evidencia en un directorio nuevo.**

Justificación con evidencia concreta:

1. **La corrección es verificable por análisis estático y ya lo fue.** `load_func` desapareció; las tres funciones de carga usan instancias válidas; las 28 funciones de device se resuelven tras crear el device; las firmas coinciden con `vulkan_core.h` 1.4.341; compila sin errores.

2. **El original queda preservado como evidencia inmutable.** Con hash `017ee552…071745` y nombre `vk_compute_test`, documenta un fallo real de harness que no debe perderse.

3. **El resultado sería discriminante en tres niveles:**
   - Si aborta en `vkEnumeratePhysicalDevices` → el defecto no era solo el orden de cargas.
   - Si supera inicialización pero no encuentra `1002:699f` → problema de enumeración o de permisos sobre el nodo de render.
   - Si imprime `>>> SELECTED` y `RESULT: PASS` con exit `0` → **cierra la etapa compute en Polaris12** con evidencia de ejecución real.
   - Si imprime `RESULT: FAIL` con `Observed output: 0` → **primera evidencia real de fallo de dispatch en GFX8**, atribuible con el flujo ya auditado.

4. **Requisitos previos a la autorización:** directorio de registro nuevo verificado vacío; captura de stdout/stderr/exit status sin pipelines; hash del artefacto nuevo registrado junto al resultado; hash del shader verificado antes y después.

No se inicia esa ejecución en esta tarea.
