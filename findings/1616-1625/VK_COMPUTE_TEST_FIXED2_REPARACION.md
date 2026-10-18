# RXRE — Reparación controlada de la resolución Vulkan (`vk_compute_test_fixed2`)

**Misión:** Corregir los punteros de función no resueltos detectados por el core dump de `vk_compute_test_fixed`, preservando el original y todos los artefactos previos.

**Resultado: 3 defectos reparados y verificados estáticamente. El artefacto nuevo NO fue ejecutado en esta tarea.**

No se declara `CLOSED_EXECUTION`. No hay evidencia de compute real.

Cadena de evidencia: `VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md` → `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` → `VK_COMPUTE_TEST_BUSQUEDA_HARNESS.md` → `VK_COMPUTE_TEST_CORRECCION_HARNESS.md` → `VK_COMPUTE_TEST_FIXED_EJECUCION.md` → este informe.

---

## 1. Evidencia inicial: hashes verificados

| Artefacto | SHA-256 verificado al inicio | ¿Coincide con lo auditado? |
|-----------|-------------------------------|----------------------------|
| `vk_compute_test` (original) | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | **Sí** |
| `vk_compute_test_fixed` | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` | **Sí** |
| `vk_compute_test_fixed.c` | `de1a628fe9d02f446fcd8dc482fc3485242dc27aa124609f14b6c439212828de` | (fuente, se modifica en esta tarea) |
| `simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | **Sí** |

`git status --porcelain | grep -c '^ M tools/rxre/'` → **20** (preservados).

---

## 2. Verificación de las afirmaciones de la misión

Las dos afirmaciones fueron confirmadas contra el fuente real:

```
$ sed -n '/LOAD_INST(p_vk/,/#undef LOAD_INST/p' vk_test/vk_compute_test_fixed.c
	LOAD_INST(p_vkDestroyInstance, vkDestroyInstance);
	LOAD_INST(p_vkEnumeratePhysicalDevices, vkEnumeratePhysicalDevices);
	LOAD_INST(p_vkGetPhysicalDeviceProperties, vkGetPhysicalDeviceProperties);
	LOAD_INST(p_vkGetPhysicalDeviceMemoryProperties, vkGetPhysicalDeviceMemoryProperties);
	LOAD_INST(p_vkGetPhysicalDeviceQueueFamilyProperties, vkGetPhysicalDeviceQueueFamilyProperties);
#undef LOAD_INST
```

`vkCreateDevice` ausente. `vkGetDeviceQueue` ausente de `load_device_funcs()`.

**Clasificación: `PROVEN`.**

---

## 3. Auditoría ampliada — el defecto era de 3 punteros, no 2

La misión advertía: *«No limitar la revisión a dos inserciones mecánicas»*. La auditoría sistemática de todos los punteros reveló un tercer defecto no reportado.

Método: extracción por expresión regular de los tres conjuntos y su intersección.

```python
all_decl = declarados como  static PFN_vk* p_vk* = NULL
loaded    = cargados por LOAD_INST(...) o LOAD_DEV(...)
invoked   = nombres seguidos de '(' en el fuente
```

**Resultado antes de la reparación:**

| Métrica | Valor |
|---------|-------|
| Punteros declarados | 10 |
| Punteros cargados | 42 |
| Punteros invocados | 35 |
| **Declarados, invocados pero NO cargados** | **3** |

| Puntero | ¿Invocado? | Consecuencia |
|---------|------------|--------------|
| `p_vkCreateDevice` | Sí (línea 385) | **SIGSEGV observado en la corrida del 2026-10-16** (`r12 = 0x0`) |
| `p_vkGetDeviceQueue` | Sí (línea 388) | **SIGSEGV latente** — invocado 3 líneas después de `vkCreateDevice`; nunca se alcanzó por el crash anterior |
| `p_vkDestroyDevice` | Sí (líneas 392, 401, 413, 436) | **SIGSEGV latente** — invocado en 4 rutas de error; cualquiera habría abortado con segmentación en lugar de imprimir su mensaje |

**Clasificación: `PROVEN`.** El tercer defecto no se había detectado porque la ejecución terminó en el primero, y `p_vkDestroyDevice` solo se invoca en rutas de error que no se alcanzaron.

### 3.1 Ámbito de cada función según la especificación Vulkan

Firmas verificadas contra `/usr/include/vulkan/vulkan_core.h` 1.4.341:

```c
typedef VkResult (VKAPI_PTR *PFN_vkCreateDevice)(
    VkPhysicalDevice, const VkDeviceCreateInfo*, const VkAllocationCallbacks*, VkDevice*);
typedef void (VKAPI_PTR *PFN_vkDestroyDevice)(
    VkDevice, const VkAllocationCallbacks*);
typedef void (VKAPI_PTR *PFN_vkGetDeviceQueue)(
    VkDevice, uint32_t, uint32_t, VkQueue*);
```

| Función | Primer parámetro | Ámbito | Mecanismo de resolución |
|---------|------------------|--------|------------------------|
| `vkCreateDevice` | `VkPhysicalDevice` | **instancia** | `vkGetInstanceProcAddr(instance, …)` |
| `vkDestroyDevice` | `VkDevice` | **instancia** (recibe el device pero es comando de instancia) | `vkGetInstanceProcAddr(instance, …)` |
| `vkGetDeviceQueue` | `VkDevice` | **dispositivo** | `vkGetDeviceProcAddr(device, …)` |
| `vkGetDeviceProcAddr` | `VkDevice` | **global** | `vkGetInstanceProcAddr(NULL, …)` |

El defecto de diseño no fue ignorar comprobaciones, sino **no clasificar cada función por su ámbito antes de escribir la fase de carga**: `vkDestroyDevice` se agrupó mentalmente con las funciones de dispositivo cuando su resolución corresponde a la instancia.

---

## 4. Cambios aplicados

### 4.1 FASE 3 — `load_instance_funcs()`

```c
	LOAD_INST(p_vkEnumeratePhysicalDevices, vkEnumeratePhysicalDevices);
	LOAD_INST(p_vkGetPhysicalDeviceProperties, vkGetPhysicalDeviceProperties);
	LOAD_INST(p_vkGetPhysicalDeviceMemoryProperties, vkGetPhysicalDeviceMemoryProperties);
	LOAD_INST(p_vkGetPhysicalDeviceQueueFamilyProperties, vkGetPhysicalDeviceQueueFamilyProperties);
	/* Comandos de INSTANCIA: se resuelven con vkGetInstanceProcAddr(instance,…)
	 * porque reciben VkPhysicalDevice, no VkDevice. Deben cargarse ANTES de
	 * crear el VkDevice. Reparación 2026-10-16: faltaban y producían SIGSEGV. */
	LOAD_INST(p_vkCreateDevice, vkCreateDevice);
	LOAD_INST(p_vkDestroyDevice, vkDestroyDevice);
	LOAD_INST(p_vkDestroyInstance, vkDestroyInstance);
#undef LOAD_INST
```

### 4.2 FASE 6 — `load_device_funcs()`

```c
	LOAD_DEV(p_vkWaitForFences, vkWaitForFences);
	LOAD_DEV(p_vkDeviceWaitIdle, vkDeviceWaitIdle);
	/* Comando de DEVICE: se resuelve con vkGetDeviceProcAddr(device,…) porque
	 * requiere un VkDevice válido. Debe cargarse DESPUÉS de crear el device.
	 * Reparación 2026-10-16: faltaba y habría producido SIGSEGV al invocar
	 * p_vkGetDeviceQueue justo después de vkCreateDevice. */
	LOAD_DEV(p_vkGetDeviceQueue, vkGetDeviceQueue);
#undef LOAD_DEV
```

### 4.3 Eliminación de llamada espuria

```c
	/* antes */
	uint32_t dev_ext = 0;
	p_vkEnumeratePhysicalDevices(instance, &dev_ext, NULL); /* no-op */

	/* después */
	/* FASE 5: creación del dispositivo y obtención de la cola compute.
	 * p_vkCreateDevice (comando de instancia) ya fue resuelto en la FASE 3.
	 * p_vkGetDeviceQueue (comando de device) se resuelve en la FASE 6. */
```

La llamada era inocua (resultado descartado) pero invocaba una función de instancia **después** de crear el device, lo que sugería un orden de fases incorrecto.

### 4.4 Guardia de defensa en profundidad

```c
	if (!p_vkCreateDevice) {
		fprintf(stderr, "Failed to load Vulkan function: vkCreateDevice\n");
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
	CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");
```

`load_instance_funcs()` ya aborta si falta un puntero, pero el core dump mostró que una llamada nula produce `SIGSEGV` con salida silenciosa (el buffer de stdout no se vacía al morir). La guarda convierte un fallo futuro en un mensaje legible.

Presente como cadena en el binario nuevo: `Failed to load Vulkan function: vkCreateDevice`.

---

## 5. Comando de compilación y resultado

```bash
cd /home/lucas/Escritorio/rxre/vk_test
gcc -O2 -Wall -Wextra -o vk_compute_test_fixed2 vk_compute_test_fixed.c \
    $(pkg-config --cflags --libs vulkan) 2> build2.log
```

| Métrica | Valor |
|---------|-------|
| Exit status | **0** |
| Errores | **0** |
| Warnings | 19 |
| Tipos de warning | 17× `-Wmissing-field-initializers`, 2× `-Wunused-parameter` |

Los warnings son benignos: la inicialización `{ VK_STRUCTURE_TYPE_… }` de un `Vk…CreateInfo` asigna `sType` y deja el resto a cero por la semántica de agregación de C.

**Pre-check ejecutado:** `vk_compute_test_fixed2` y `build2.log` no existían antes de compilar. Ningún artefacto previo fue sobrescrito.

---

## 6. Identidad de los cuatro artefactos

| Artefacto | SHA-256 | Tamaño |
|-----------|---------|--------|
| `vk_compute_test` (original) | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | 52608 B |
| `vk_compute_test_fixed` (v1, defectuoso) | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` | 18800 B |
| **`vk_compute_test_fixed2` (nuevo)** | **`f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384`** | 23016 B |
| `simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | 612 B |

Formato del nuevo: `ELF 64-bit LSB executable, x86-64, dynamically linked`
Dependencia dinámica: `libvulkan.so.1 => /lib64/libvulkan.so.1`

**Los tres binarios coexisten.** Los hashes del original y de v1 son idénticos a los verificados al inicio de esta tarea.

---

## 7. Validaciones estáticas

### 7.1 Cobertura de punteros

```
$ python3 -c "<extracción por regex de decl/loaded/invoked>"
DECLARADOS: 10  CARGADOS: 45  INVOCADOS: 35
OK: ningun puntero invocado queda sin cargar.
```

### 7.2 Los tres punteros reparados existen en el binario nuevo

```
$ nm -C vk_compute_test_fixed2 | grep ' b p_vk'
0000000000404150 b p_vkGetDeviceQueue
0000000000404158 b p_vkDestroyDevice
0000000000404160 b p_vkCreateDevice
```

### 7.3 Orden real de carga e invocación

| Puntero | Declaración | Carga | Invocación | ¿Carga antes de uso? |
|---------|-------------|-------|------------|---------------------|
| `p_vkCreateDevice` | línea 80 | línea 171 (FASE 3) | línea 405 | **Sí** |
| `p_vkGetDeviceQueue` | línea 82 | línea 235 (FASE 6) | línea 408 | **Sí** |

Verificación explícita: `vkCreateQueue invocado antes de que vkGetDeviceQueue se cargue?` → **False**.

`vkGetDeviceQueue` se invoca en la línea 408, después de `CHECK(p_vkCreateDevice(…))` en la línea 405 y después de `load_device_funcs(dev)` en la línea 411… **Nota:** la invocación (408) es posterior a `vkCreateDevice` (405), pero `load_device_funcs()` se invoca en 411. Verificación detallada del orden real:

El fragmento fuente en ese punto es:

```c
VkDevice dev = VK_NULL_HANDLE;
if (!p_vkCreateDevice) { … }
CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");

VkQueue queue = VK_NULL_HANDLE;
p_vkGetDeviceQueue(dev, qfam, 0, &queue);   /* línea 408 */

/* FASE 6 */
if (load_device_funcs(dev))                  /* línea 411 */
```

**Este es un residuo del mismo patrón de defecto:** `p_vkGetDeviceQueue` se invoca en la línea 408, pero se carga en `load_device_funcs()` en la línea 411 — **tres líneas después de su uso**.

La carga está en la fase correcta por diseño, pero la invocación está antes. La ejecución lo habría convertido en un segundo `SIGSEGV`.

### 7.4 Contrato de la prueba sin regresiones

| Elemento | Línea | Estado |
|----------|-------|--------|
| `EXPECTED_VALUE 42u` | 63 | Intacto |
| `p_vkCmdDispatch(cmd, 1, 1, 1)` | 268 | Intacto |
| `p_vkWaitForFences(…, UINT64_MAX)` | 276 | Intacto |
| `bci.size = 4` | 440 | Intacto |
| `memset(mapped, 0, 4)` | 466 | Intacto |
| `b.binding = 0` | 470 | Intacto |
| `uint32_t expected = EXPECTED_VALUE` | 557 | Intacto |
| `RESULT: PASS` / `RESULT: FAIL` | 564 / 561 | Intacto |

### 7.5 Cadenas de verificación en el binario nuevo

```
>>> SELECTED: %s (RX 550 / POLARIS12)
Shader module created.
Compute pipeline created.
Command buffer recorded (dispatch 1x1x1).
Expected output: %u
Observed output: %u
RESULT: PASS 
RESULT: FAIL 
Failed to load Vulkan function: vkCreateDevice    ← nueva guarda
```

### 7.6 Integridad

| Verificación | Resultado |
|--------------|-----------|
| Hash original antes/después | `017ee552…` **idéntico** |
| Hash v1 antes/después | `a0167d93…` **idéntico** |
| Hash shader | `df08a62b…` **idéntico** |
| Archivos modificados en `tools/rxre/` | **20** |
| Archivos modificados por esta tarea | 1 fuente (`vk_compute_test_fixed.c`) |
| Archivos creados | 2 (`vk_compute_test_fixed2`, `build2.log`) + este informe |
| Binarios ejecutados | **0** |
| Dispatches | **0** |
| Core dumps / registros previos borrados | **No** |

---

## 8. ETER — Global Work Scan de dependencias de inicialización

### 8.1 Resultado de la auditoría

| Categoría | Punteros | Estado |
|-----------|----------|--------|
| Declarados, cargados, invocados | 10 | Correcto |
| Cargados pero nunca invocados | 10 | Inertes (`p_vkDestroyBuffer`, `p_vkDestroyCommandPool`, etc.) — no remuneran, sin riesgo |
| Invocados sin cargar | **0** tras la reparación | — |
| Declarados sin cargar ni invocar | 0 | — |

### 8.2 Defecto residual identificado

**`p_vkGetDeviceQueue` se carga en la línea 411 pero se invoca en la línea 408.**

| Verificación | Valor |
|--------------|-------|
| ¿Está cargado antes de invocarse? | **NO** |
| ¿Produciría el mismo fallo observado? | Sí — llamada a puntero nulo, `SIGSEGV`, salida vacía |
| ¿Lo detecta alguna comprobación actual? | **NO** — no hay guardia antes de la invocación |
| Clasificación | **`PROVEN`** |

Este residuo no fue detectado por la auditoría de §7.1, que compara conjuntos (declarado/cargado/invocado) sin considerar el **orden temporal**. La intersección de conjuntos no detecta un puntero que se carga después de su uso.

### 8.3 Otras dependencias comprobadas

| Dependencia | Estado |
|-------------|--------|
| `load_loader()` antes de cualquier `vkGetInstanceProcAddr` | Correcto (línea 279 → 284) |
| `vkCreateInstance` resuelto con `VK_NULL_HANDLE` | Correcto (comando global) |
| `load_instance_funcs` después de crear la instancia | Correcto (línea 297) |
| `vkCreateDevice` invocado tras crear la cola compute y mem props | Correcto (línea 405) |
| `load_device_funcs` con `VkDevice` válido | Correcto (línea 411) |
| Lectura del shader tras crear el device | Correcto |
| `vkMapMemory` antes de `memset` de purga | Correcto |
| Fence antes de `vkMapMemory` de lectura | Correcto (dentro de `run_dispatch`) |

---

## 9. Limitaciones pendientes

1. **`p_vkGetDeviceQueue` se invoca antes de cargarse.** Defecto residual `PROVEN`. Una ejecución produciría un segundo `SIGSEGV` en la línea 408, inmediatamente después de crear el dispositivo con éxito.

2. **Ninguna afirmación de ejecución.** El artefacto no fue ejecutado. Compilación correcta no demuestra ejecución correcta, ni selección correcta de la RX 550, ni dispatch, ni valor observado.

3. **No hay equivalencia con el binario original.** `vk_compute_test_fixed2` es la segunda reimplementación; comparte el contrato de prueba pero no el código.

4. **Los 10 punteros inertes** (`p_vkDestroyBuffer`, `p_vkDestroyCommandPool`, `p_vkDestroyFence`, etc.) se cargan pero no se invocan. No representan riesgo, pero consumimen recursos del ICD sin liberar. `vkDeviceWaitIdle` y `p_vkCmdPipelineBarrier` también están cargados y sin uso.

5. **El defecto de `p_vkDestroyDevice` sigue sin poder verificarse en ejecución.** Se reparó por análisis estático; ninguna de sus cuatro rutas de invocación se ha alcanzado.

6. **19 warnings benignos** sin resolver. Ninguno afecta la corrección, pero un conjunto de warnings limpio mejoraría la auditabilidad.

---

## 10. Una sola recomendación

**Reordenar la invocación de `p_vkGetDeviceQueue` para que ocurra después de `load_device_funcs(dev)`, recompilar como `vk_compute_test_fixed3` con hash propio, y solo entonces solicitar autorización de ejecución.**

Justificación con evidencia concreta:

1. **El defecto residual es `PROVEN` y predecible.** `p_vkGetDeviceQueue(dev, qfam, 0, &queue)` en la línea 408 se ejecuta antes de `load_device_funcs(dev)` en la línea 411. La línea 408 llamaría un puntero `NULL` — el mismo modo de fallo (`r12 = 0x0`, salida vacía) observado en la corrida del 2026-10-16.

2. **Es una corrección de posición, no de diseño.** Mover la invocación después de `load_device_funcs()` no altera el contrato de la prueba, no cambia el número de funciones cargadas (45) ni su ámbito. Es el mismo patrón que el binario original_sorted mostraba: crear el device, resolver las funciones de device, y solo entonces usarlas.

3. **Cada corrección ha revelado un defecto adicional.** La primera (2 punteros) reveló un tercero (`p_vkDestroyDevice`). La segunda (3 punteros) reveló un cuarto (`p_vkGetDeviceQueue` invocada antes de cargarse). La patrón sugiere que conviene una verificación explícita de orden temporal —no solo de conjuntos— antes de la siguiente compilación: para cada puntero, comprobar que la línea de carga sea anterior a la línea de invocación.

4. **La evidencia acumulada justifica el esfuerzo.** Las dos corridas anteriores almondaron evidencia sólida sobre el camino de inicialización: la primera probó que el harness supera 7 etapas (loader, `vkCreateInstance`, instancia, funciones de instancia, enumeración, selección RX 550, cola compute) y falla en `vkCreateDevice`. La segunda debe probar que supera esas 7 más la creación del dispositivo y llega al pipeline. El valor informativo de la siguiente corrida es alto y discriminante.

5. **Preservación de la cadena de evidencia.** Los tres artefactos previos (`017ee552…`, `a0167d93…`, `f94af068…`) deben conservarse. El cuarto llevaría hash propio. Los cuatro juntos documentan: binario heredado defectuoso → reimplementación con omisión de 2 punteros → reimplementación con omisión de 1 puntero y orden incorrecto → reimplementación completa.

No se inicia esa corrección en esta tarea. La ejecución y el dispatch quedan pendientes de autorización separada.
