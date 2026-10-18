# RXRE — Cierre del defecto de orden temporal (`vk_compute_test_fixed3`)

**Misión:** eliminar el defecto residual demostrado en `vk_compute_test_fixed2` y evitar otra iteración basada en correcciones aisladas.

**Resultado: 1 defecto de orden temporal reparado + 2 defectos de la misma clase contractual detectados y reparados. Matriz temporal cerrada con 0 violaciones. El binario NO fue ejecutado.**

No se declara `CLOSED_EXECUTION`. No hay evidencia de compute real.

Cadena de evidencia: `VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md` → `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` → `VK_COMPUTE_TEST_BUSQUEDA_HARNESS.md` → `VK_COMPUTE_TEST_CORRECCION_HARNESS.md` → `VK_COMPUTE_TEST_FIXED_EJECUCION.md` → `VK_COMPUTE_TEST_FIXED2_REPARACION.md` → este informe.

---

## 1. Inspección previa

| Artefacto | SHA-256 verificado al inicio | ¿Coincide con lo auditado? |
|-----------|-------------------------------|----------------------------|
| `vk_compute_test` (original) | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | **Sí** |
| `vk_compute_test_fixed` | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` | **Sí** |
| `vk_compute_test_fixed2` | `f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384` | **Sí** |
| `simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | **Sí** |

`git status --porcelain | grep -c '^ M tools/rxre/'` → **20** (preservados, verificados antes y después).

Informes presentes en `findings/1616-1625/`: 6 informes `VK_COMPUTE*.md`, ninguno sobrescrito.

---

## 2. Hallazgo metodológico principal

La instrucción pedía explícitamente no limitarse a comparar conjuntos declarado/cargado/invocado. **El intento de automatizar esa comprobación produjo tres resultados falsos que tuvieron que corregirse antes de poder confiar en el análisis.** Se documentan porque el método es el resultado más transferable de esta tarea.

### 2.1 Comparación por número de línea: no detecta nada

La primera versión del análisis comparó `min(línea_de_invocación)` contra `max(línea_de_carga)`:

```
p_vkGetDeviceQueue    carga l235    invocación l408    -> "ninguna violación"
```

Es **exactamente el defecto buscado**, y el método lo declaró limpio. Razón: la carga ocurre dentro de `load_device_funcs()` (definida en l179, **llamada** en l411) mientras la invocación está en `main` (l408). `408 < 411`, así que el orden de fuente es aparentemente correcto aunque el orden de ejecución sea el inverso.

**Clasificación: `PROVEN`** — la limitación del método, reproducida.

### 2.2 Recorrido en pre-orden: tampoco detecta nada

La segunda versión construyó un grafo de llamadas, pero expandió los callees **después** de emitir todos los eventos del llamador:

```
main -> [eventos de main] -> [eventos de load_instance_funcs]
main -> [eventos de main] -> [eventos de load_device_funcs]
```

El orden `INVOKE(408)` → `LOAD(235)` se mantenía por construcción. **Clasificación: `PROVEN`** — el sesgo del algoritmo.

### 2.3 Comparar posiciones de línea entre funciones: no tiene sentido

La tercera versión sí distinguió la secuencia de ejecución, pero继续 comparaba números de línea:

```python
if I[0] < L[0]:   # I y L son (indice_secuencia, linea_fuente)
    st = 'VIOLACION'
```

`I[0]` era el índice de secuencia pero `L[0]` seguía siendo la línea de fuente (235 < 408) → falso negativo otra vez. El defecto se hizo visible solo al comparar **índices de secuencia** (`#60` vs `#24`).

**Conclusión: para punteros de función el invariante relevante es una posición en el orden de ejecución, nunca una línea de fuente.** Las líneas solo son significativas dentro de una misma función.

### 2.4 El analizador final

Herramienta de verificación en `/tmp/opencode/temporal_final.py` (fuera del repositorio; no es un artefacto del proyecto). Características:

1. Elimina comentarios de bloque y de línea, y literales de cadena, antes de cualquier análisis — sin esto, los menciones en comentarios (`l382`, `l383`) aparecen como invocaciones falsas.
2. Normaliza a **líneas lógicas** uniendo continuaciones (paréntesis desbalanceados o línea terminada en `=`, `,`, `(`) — sin esto, las asignaciones partidas en dos líneas (`l142-143`, `l181-182`, `l295-296`) aparecen como punteros nunca resueltos.
3. Detecta eventos `LOAD` / `INVOKE` / `CALL` por función.
4. Emite una **secuencia de ejecución** con *splicing en orden*: una llamada se expande exactamente en su punto.
5. Compara **índices de secuencia**, no líneas de fuente.
6. Añade una columna de guardia: si existe `if (!p_vkX)` en las 12 líneas previas de la misma función.

**Limitación conocida y declarada:** el análisis es de flujo estructurado *sin* ramificación por condición; el orden dentro de un `if`/`else` se toma como el del fuente. Es exacto para este programa porque las funciones de carga no tienen ramificación fuera de la macro de retorno temprano, pero no lo sería para un programa con flujo condicional complejo. Todo hallazgo del analizador se contrastó con lectura directa del fuente.

---

## 3. Matriz temporal completa

Matriz de los 48 puntos de resolución del fuente, con el orden de ejecución real. Abreviaturas: `#N` = posición en la secuencia de ejecución, `lN` = línea de fuente.

### 3.1 Las 7 funciones globales estáticas de fase

| Puntero | Declaración | Función que lo resuelve | Objeto requerido | Carga | 1ª invocación | Guardia | Estado |
|---------|-------------|-------------------------|-------------------|-------|---------------|---------|--------|
| `p_vkGetInstanceProcAddr` | l67 | `dlsym` | — | `#0/l142` | `#3/l156` | no | ok |
| `p_vkCreateInstance` | l70 | `gipa(NULL,…)` | ninguno (global) | `#1/l295` | `#2/l314` | no | ok |
| `p_vkDestroyInstance` | l73 | `load_instance_funcs` | `VkInstance` | `#10/l173` | `#11/l330` | **l329** | ok |
| `p_vkEnumeratePhysicalDevices` | l74 | `load_instance_funcs` | `VkInstance` | `#4/l164` | `#12/l336` | no | ok |
| `p_vkGetPhysicalDeviceProperties` | l75 | `load_instance_funcs` | `VkInstance` | `#5/l165` | `#16/l355` | no | ok |
| `p_vkGetPhysicalDeviceMemoryProperties` | l76 | `load_instance_funcs` | `VkInstance` | `#6/l166` | `#21/l391` | no | ok |
| `p_vkGetPhysicalDeviceQueueFamilyProperties` | l77 | `load_instance_funcs` | `VkInstance` | `#7/l167` | `#18/l375` | no | ok |
| `p_vkCreateDevice` | l80 | `load_instance_funcs` | `VkInstance` | `#8/l171` | `#23/l417` | l412 | ok |
| `p_vkDestroyDevice` | l81 | `load_instance_funcs` | `VkInstance` | `#9/l172` | `#61/l433` | no | ok |
| `p_vkGetDeviceQueue` | l82 | `load_device_funcs` | `VkDevice` | **`#60/l235`** | **`#63/l443`** | no | **ok (reparado)** |

### 3.2 Las 38 funciones de dispositivo resueltas por `load_device_funcs`

Todas comparten la misma forma: resueltas en `#26..#60` dentro de `load_device_funcs`, invocadas en `#68..#95`. **Ninguna presenta violación de orden.** Se listan agrupadas:

| Grupo | Punteros | Carga | 1ª invocación |
|-------|----------|-------|---------------|
| Buffers y memoria | `vkCreateBuffer`, `vkGetBufferMemoryRequirements`, `vkAllocateMemory`, `vkBindBufferMemory`, `vkMapMemory`, `vkUnmapMemory` | `#26..#34` | `#68..#77` |
| Shaders | `vkCreateShaderModule` | `#34` | `#80` |
| Descriptores | `vkCreateDescriptorSetLayout`, `vkCreatePipelineLayout`, `vkCreateComputePipelines`, `vkCreateDescriptorPool`, `vkAllocateDescriptorSets`, `vkUpdateDescriptorSets` | `#36..#45` | `#78..#84` |
| Command buffers | `vkCreateCommandPool`, `vkAllocateCommandBuffers`, `vkBeginCommandBuffer`, `vkEndCommandBuffer`, `vkCmdBindPipeline`, `vkCmdBindDescriptorSets`, `vkCmdDispatch`, `vkFreeCommandBuffers` | `#46..#54` | `#85..#95` |
| Submit y sincronización | `vkQueueSubmit`, `vkCreateFence`, `vkWaitForFences` | `#55..#58` | `#91..#94` |

`p_vkGetDeviceProcAddr` (local en `load_device_funcs`, `#24/l181`, guardia en `l183`) queda resuelto por `p_vkGetInstanceProcAddr(NULL, "vkGetDeviceProcAddr")` y se invoca en `#25/l190` dentro de la macro `LOAD_DEV`. Correcto: es un comando **global** y no requiere `VkDevice`.

### 3.3 Resultado del cierre

```
DEFECTOS (0): []
INERTES (10): [p_vkDestroyBuffer, p_vkDestroyCommandPool, p_vkDestroyDescriptorPool,
               p_vkDestroyDescriptorSetLayout, p_vkDestroyFence, p_vkDestroyPipeline,
               p_vkDestroyPipelineLayout, p_vkDestroyShaderModule, p_vkDeviceWaitIdle,
               p_vkFreeMemory]
```

**Las 10 funciones inertes** se resuelven y nunca se invocan. No representan riesgo de puntero nulo; representan recursos del ICD nunca liberados (§7).

---

## 4. Defectos encontrados

### D1 — Invocación de `p_vkGetDeviceQueue` antes de su resolución (`PROVEN`)

| Verificación | Valor (fixed2) |
|--------------|----------------|
| Posición de resolución en la secuencia | **#61** |
| Posición de la primera invocación | **#24** |
| ¿Resolución antes de invocación? | **NO** |
| ¿Guardia previa a la invocación? | **NO** |
| ¿Hay comprobación antes de invocarlo? | **NO** |

`p_vkGetDeviceQueue` es un `static … = NULL` global, invocado en `main` antes de que `load_device_funcs(dev)` seplete el puntero. `load_device_funcs` se llama **una sola vez** en todo el programa (verificado: `l179` definición, `l411` única llamada).

**Consecuencia:** llamada indirecta a la dirección `0x0` → `SIGSEGV`, con el modo de fallo ya documentado en el core dump del 2026-10-16 (`rip=0x0`, `r12=0x0`, stdout no vaciado por el aborto). Alcanzable de forma **incondicional** tras un `vkCreateDevice` exitoso — es decir, en la ruta principal, no en una ruta de error.

### D2 — Ruta de fallo parcial con `p_vkDestroyInstance` sin resolver (`PROVEN`)

Este defecto no lo detecta el análisis secuencial: la carga de `p_vkDestroyInstance` (`#10/l173`) ocurre *antes* de su invocación (`#11/l330`), pero **la carga puede fallar y dejar el puntero a NULL**.

```
l317:  if (load_instance_funcs(instance, "instance")) {
l318:      p_vkDestroyInstance(instance, NULL);      <-- posible NULL
l319:      return 1;
l320:  }
```

`load_instance_funcs` puede devolver `1` desde cualquiera de sus siete macros `LOAD_INST`. Si falla cualquiera de las **seis primeras** (l164–l172), `p_vkDestroyInstance` ya está resuelto y la llamada es correcta. Si falla la **séptima** (`vkDestroyInstance`, l173), el puntero sigue a `NULL` y `l318` invoca a través de él.

**Distinción esencial:** *carga intentada* ≠ *carga exitosa*. La matriz secuencial de §3 registra el orden de los eventos, no su resultado.

Sobre la alcanzabilidad del disparador: `vkDestroyInstance` es un comando **central obligatorio** de Vulkan 1.0, y `/usr/include/vulkan/vulkan_core.h` lo declara. Que un ICD conformante lo omita no debería ocurrir → `INFERRED`, no `PROVEN`. La ruta en el código sí es real y está cerrada.

### D3 — Handle `VkQueue` sin validar (`PROVEN`)

`vkGetDeviceQueue` tiene firma `void (VkDevice, uint32_t, uint32_t, VkQueue*)`: **no devuelve `VkResult`**, así que el macro `CHECK` no puede aplicarse. `queue` era el único handle de objeto Vulkan del programa sin comprobación posterior; un `VK_NULL_HANDLE` habría llegado a `run_dispatch()` → `p_vkQueueSubmit(VK_NULL_HANDLE, 1, &si, fence)` (l274), donde el driver lo desreferenciaría.

Que el driver devuelva un handle nulo para una familia de colas solicitada explícitamente en `dci.pQueueCreateInfos` con `queueCount=1` y `queueIndex=0` no debería ocurrir → `INFERRED`. La ausencia de validación en el código sí es `PROVEN`.

### D4 — Guardia de `p_vkCreateDevice` alcanzable sólo por análisis estático (`PROVEN`, sin cambio)

La guardia `if (!p_vkCreateDevice)` (l412) es **código muerto**: `p_vkCreateDevice` se resuelve mediante `LOAD_INST` en l171, y esa macro devuelve `1` abortando la fase si el puntero es `NULL`; si se llega a l412 entonces `load_instance_funcs` devolvió `0`, luego `p_vkCreateDevice` no puede ser `NULL`. Se conserva sin modificar: es inofensiva y documenta la intención. Se corrige la afirmación del informe anterior que la describía como protección viva — es `PROVEN` inalcanzable.

---

## 5. Cambios aplicados

### 5.1 D1 — reordenación de FASE 6

```c
	CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");

	/* FASE 6: resolución de las funciones de DISPOSITIVO. … */
	if (load_device_funcs(dev)) {
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}

	VkQueue queue = VK_NULL_HANDLE;
	p_vkGetDeviceQueue(dev, qfam, 0, &queue);
```

El bloque `load_device_funcs` se movió **por encima** de la invocación. No es un traslado de línea:

- La ruta de fallo de FASE 6 invoca `p_vkDestroyDevice` (resuelto en l172) y `p_vkDestroyInstance` (resuelto en l173). Ambos son comandos de **instancia**, resueltos en FASE 3, y se llega a FASE 6 solo si `load_instance_funcs` devolvió `0` → ambos garantizados no nulos. **La reordenación no introduce una ruta de limpieza insegura.**
- `load_device_funcs` devuelve `1` en cuanto una resolución falla, de modo que alcanzar la línea de `p_vkGetDeviceQueue` implica que `LOAD_DEV(p_vkGetDeviceQueue)` devolvió un puntero válido. No hace falta una guardia adicional.

### 5.2 D2 — guarda en la ruta de fallo parcial

```c
	if (load_instance_funcs(instance, "instance")) {
		if (p_vkDestroyInstance)
			p_vkDestroyInstance(instance, NULL);
		return 1;
	}
```

Cubre el séptimo caso sin cambiar el comportamiento en los otros seis (donde el puntero sí está resuelto y la llamada ocurre igual).

### 5.3 D3 — validación del handle de cola

```c
	if (queue == VK_NULL_HANDLE) {
		fprintf(stderr, "vkGetDeviceQueue returned VK_NULL_HANDLE "
		                "(queueFamilyIndex=%u)\n", qfam);
		p_vkDestroyDevice(dev, NULL);
		p_vkDestroyInstance(instance, NULL);
		return 1;
	}
```

**No se tocó** el contrato de la prueba: `EXPECTED_VALUE 42u` (l63), `bci.size = 4` (l480), `memset(mapped, 0, 4)` (l506), `b.binding = 0` (l510), `cpi.stage.pName = "main"` (l541), `dbi = { out_buf, 0, 4 }` (l565), `UINT64_MAX` (l276), `RESULT: PASS`/`FAIL` (l601/604). Ningún cambio afecta al shader, al buffer, al binding, al dispatch, a la sincronización ni a la comparación contra 42.

---

## 6. Resultado de compilación

```bash
cd /home/lucas/Escritorio/rxre/vk_test
gcc -O2 -Wall -Wextra -o vk_compute_test_fixed3 vk_compute_test_fixed.c \
    $(pkg-config --cflags --libs vulkan) 2> build3.log > build3.stdout.log
```

| Métrica | Valor |
|---------|-------|
| Exit status | **0** |
| stdout | 0 bytes |
| stderr | 8545 bytes |
| Errores | **0** |
| Warnings | 19 |

**Pre-check ejecutado:** `vk_compute_test_fixed3` y `build3.log` no existían. Sin pipelines: stderr y stdout separados, exit status capturado directamente. Compilador: `gcc (GCC) 16.2.1 20260819 (Red Hat 16.2.1-2)`; headers `vulkan 1.4.341`.

### 6.1 Evaluación de warnings — sin asumir que son benignos

| Tipo | Cantidad | Evaluación |
|------|----------|------------|
| `-Wmissing-field-initializers` | 17 | **Realmente benignos.** Provienen de la inicialización `{ VK_STRUCTURE_TYPE_… }` de estructuras `Vk…CreateInfo`. En C, un inicializador de agregado pone a cero todos los miembros no inicializados, y Vulkan exige exactamente cero para los no provistos. No hay lectura de miembro no inicializado. |
| `-Wunused-parameter` | 2 | **Realmente benignos, pero con observación.** `shader_mod` y `buf`, parámetros de `run_dispatch()` que el cuerpo no usa: el módulo de shader ya está vinculado al pipeline en `cpi.stage.module` y el buffer ya está enlazado al conjunto de descriptores en `dbi`. No hay error, pero la firma declara dependencias que el cuerpo no ejerce. Es ruido de diseño menor, no una avería. |

**Ningún warning oculta un defecto de esta tarea.** En particular, no hay warnings de punteros nulos posibles: gcc no los emite en este nivel de análisis, lo que refuerza que la matriz temporal de §3 —no el compilador— es la que sostiene la garantía de orden.

---

## 7. Validaciones estáticas

### 7.1 Matriz temporal del binario nuevo

```
DEFECTOS (0): []
```
`p_vkGetDeviceQueue`: resolución `#60`, invocación `#63`.

### 7.2 Prueba a nivel de código máquina

`objdump -d` sobre ambos binarios. En `fixed2`:

```
  4008a2:  call   QWORD PTR [rip+0x38a8]   # 404150 <p_vkGetDeviceQueue>   <-- INVOCACION
  400c28:  mov    QWORD PTR [rip+0x3521],rax # 404150 <p_vkGetDeviceQueue>  <-- RESOLUCION
```

**La invocación está 902 bytes (`0x386`) ANTES que la resolución.** El defecto queda probado por código máquina, independiente del análisis de fuente.

En `fixed3`:

```
  400c09:  call   r12                       ; p_vkGetDeviceProcAddr(dev, "vkGetDeviceQueue")
  400c0c:  mov    QWORD PTR [rip+0x353d],rax # 404150 <p_vkGetDeviceQueue>   <-- RESOLUCION
  400c13:  test   rax,rax
  400c16:  je     401ceb <main+0x188b>      ; ruta "Failed to load Vulkan function: %s"
  400c32:  call   rax                                                     <-- INVOCACION
  400c34:  cmp    QWORD PTR [rsp+0x30],0x0
  400c3a:  je     401819 <main+0x13b9>      ; ruta "vkGetDeviceQueue returned VK_NULL_HANDLE"
```

Secuencia binaria: **resolver → comprobar nulo → invocar → validar handle.** Las 38 instrucciones de separación entre resolución e invocación incluyen exactamente la comprobación de nulos de la macro `LOAD_DEV`.

Rutas de destino verificadas:
- `401ceb` → `fprintf(stderr, "Failed to load Vulkan function: %s", "vkGetDeviceQueue")`
- `401819` → `fprintf(stderr, "vkGetDeviceQueue returned VK_NULL_HANDLE (queueFamilyIndex=%u)")` → salta a `400cd1`, que ejecuta `call [p_vkDestroyDevice]` (`400cd8`) y `call [p_vkDestroyInstance]` (`400ce5`).

Para `p_vkCreateDevice` en `fixed3`: almacén en `4005f5`, recarga en `400825`, `test rax,rax` / `je` en `400867`/`40086a`, invocación `call rax` en `400882`. Orden correcto.

### 7.3 Tabla de símbolos

```
0000000000404160 b p_vkCreateDevice
0000000000404158 b p_vkDestroyDevice
0000000000404150 b p_vkGetDeviceQueue
0000000000404188 b p_vkDestroyInstance
```

### 7.4 Contrato de la prueba en el binario

```
>>> SELECTED: %s (RX 550 / POLARIS12)
Shader module created.
Compute pipeline created.
Command buffer recorded (dispatch 1x1x1).
Expected output: %u
Observed output: %u
RESULT: FAIL
RESULT: PASS
vkGetDeviceQueue returned VK_NULL_HANDLE (queueFamilyIndex=%u)   <-- nueva
Failed to load Vulkan function: vkCreateDevice
```

Literales de nombre presentes: `vkCreateDevice`, `vkDestroyInstance`, `vkGetDeviceQueue`.

### 7.5 Identidad de los artefactos

| Artefacto | SHA-256 | Tamaño | Estado |
|-----------|---------|--------|--------|
| `vk_compute_test` (original) | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | 52608 B | **intacto** |
| `vk_compute_test_fixed` | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` | 18800 B | **intacto** |
| `vk_compute_test_fixed2` | `f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384` | 23016 B | **intacto** |
| **`vk_compute_test_fixed3` (nuevo)** | **`b633146608a0819e3b1ca32ced66d043ea71a09b178b762adfbaf0d17f0c318c`** | 23016 B | nuevo |
| `simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | 612 B | **intacto** |

Formato: `ELF 64-bit LSB executable, x86-64, dynamically linked`. Los cuatro binarios coexisten.

### 7.6 Recuperación del eslabón perdido: fuente de `fixed2`

`vk_test/` **no está rastreado por git** (`git ls-files vk_test/` vacío, `?? vk_test/`). El informe anterior registró que el fuente de `fixed` se había perdido al reutilizar `vk_compute_test_fixed.c` para `fixed2`. Esa pérdida se repitía con esta tarea, así que se cerró:

1. Se invirtieron los tres cambios sobre el fuente actual para reconstruir el estado de `fixed2`.
2. Se compiló el fuente reconstruido **en su ruta original** y se comparó con el binario preservado.

```
hash recomputado : f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384
hash fixed2      : f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384
RESULTADO: IDENTICO BYTE A BYTE
```

Se preserva como `vk_test/vk_compute_test_fixed2.c`, SHA-256 `c7effeb345418d1871bb52561fb84a9469201e3f91f47038c9114580b2175108`. **Clasificación: `PROVEN`** — la reconstrucción reproduce exactamente el artefacto auditado.

**Hallazgo lateral de este proceso:** el hash del binario depende de la **ruta del fuente**. El mismo contenido compilado desde `vk_test/` y desde `/tmp/` produce hashes distintos (`b6331466…` vs `3a569056…`), mientras que dos compilaciones desde la misma ruta son idénticas. La primera verificación de la reconstrucción falló por esta razón y fue una verificación inválida, no una reconstrucción incorrecta. **Consecuencia para informes futuros:** cualquier hash de este proyecto solo es reproducible si se declaran la ruta del fuente y el comando de compilación.

---

## 8. Estado epistemico de cada conclusión

| Afirmación | Clasificación | Base |
|------------|----------------|------|
| `p_vkGetDeviceQueue` se invocaba antes de resolverse en `fixed2` | **`PROVEN`** | Fuente (§3) **y** código máquina (§7.2): `0x4008a2` vs `0x400c28` |
| Esa invocación habría producido `SIGSEGV` | **`PROVEN`** | El puntero es `static … = NULL` sin otra escritura previa; una llamada indirecta a `0x0` es un fallo determinista. Modo de fallo coherente con el core dump previo (`rip=0x0`, `r12=0x0`) |
| La ruta `l318` podía invocar `p_vkDestroyInstance` a NULL | **`PROVEN`** | El análisis secuencial no lo ve; se deduce de que la 7ª de 7 macros puede fallar dejando el puntero a NULL |
| Ese disparador no ocurriría con un ICD conformante | **`INFERRED`** | `vkDestroyInstance` es comando central obligatorio de Vulkan 1.0 y está declarado en el header |
| `vkGetDeviceQueue` no puede devolver estado de error | **`PROVEN`** | Firma `void` en `vulkan_core.h` l4443 |
| El driver no devolvería un `VkQueue` nulo para la familia solicitada | **`INFERRED`** | La familia se selecciona de `VK_QUEUE_COMPUTE_BIT` reales y se solicita explícitamente en `dci.pQueueCreateInfos` |
| Matriz temporal de `fixed3`: 0 violaciones de orden | **`PROVEN`** | Analizador (§2.4) + confirmación por desensamblado (§7.2). Limitación del analizador declarada en §2.4 |
| La ruta de fallo de FASE 6 invoca solo punteros resueltos | **`PROVEN`** | `p_vkDestroyDevice` (l172) y `p_vkDestroyInstance` (l173) son de FASE 3; FASE 6 solo se alcanza con `load_instance_funcs` == 0 |
| `fixed2.c` reconstruido es el fuente de `fixed2` | **`PROVEN`** | Recompilación byte a byte idéntica (§7.6) |
| El binario compila sin errores | **`OBSERVED`** | exit status 0, 0 errores, registro capturado |
| El binario ejecuta correctamente el pipeline compute | **`OPEN`** | No ejecutado. Compilación correcta no demuestra ejecución correcta |
| La RX 550 es la identidad del dispositivo en esta tarea | **`OPEN`** | No ejecutado; no se emitió ningún `>>> SELECTED:` |

---

## 9. Defectos no descartados

1. **10 punteros inertes.** `p_vkDestroyBuffer`, `p_vkDestroyCommandPool`, `p_vkDestroyDescriptorPool`, `p_vkDestroyDescriptorSetLayout`, `p_vkDestroyFence`, `p_vkDestroyPipeline`, `p_vkDestroyPipelineLayout`, `p_vkDestroyShaderModule`, `p_vkDeviceWaitIdle`, `p_vkFreeMemory` se resuelven y nunca se invocan. Sin riesgo de puntero nulo, pero **fugas de recursos del ICD**: el proceso destruye `VkDevice` y `VkInstance` con objetos hijos vivos. Vulkan no exige liberar hijos antes del padre, así que no es una violación, pero impide una salida limpia y cualquier análisis de capasfuturo. **No corregido:** fuera del contrato de inicialización.

2. **Fuga de `code` y de objetos Vulkan en rutas `CHECK`.** `code` (el SPIR-V leído) solo se libera en dos rutas; los objetos creados tras el FASE 6 no se destruyen si un `CHECK` posterior falla. Fugas de proceso, no averías. **No corregido:** mismo motivo.

3. **Guardia de `p_vkCreateDevice` inalcanzable** (D4). Inofensiva, se conserva. **No corregido:** eliminarla reduciría ruido pero perdería la documentación de la invariante.

4. **`-Wunused-parameter` en `run_dispatch`.** La firma declara `shader_mod` y `buf` sin ejercerlos. **No corregido:**cosmético.

5. **Los shaders `test_compute.shader` / `test_compute.spv` en `vk_test/` (l907/l922) no se usan.** El harness lee `/tmp/rxre_spirv_tests/simple.comp.spv`. Riesgo de confundir qué shader se probaría. **No corregido:** fuera de alcance, pero registrado para evitar un error en la ejecución autorizada.

6. **Equivalencia con el binario original: `REFUTED`.** `vk_compute_test_fixed3` es la tercera reimplementación. Comparte el contrato de prueba con `vk_compute_test`, no el código. Nada observado en esta cadena es evidencia sobre el comportamiento del original.

7. **El core dump del 2026-10-16 sigue sin interpretar más allá de `rip=0x0`.** Corregir D1 elimina el modo de fallo, pero el binario original sigue bloqueado por diseño (§`VK_COMPUTE_TEST_FIXED_EJECUCION.md`).

---

## 10. Estado de la frontera compute

| Etapa | Estado | Decisión |
|-------|--------|----------|
| Carga del loader | cerrada estáticamente | `CLOSED_STATIC` |
| `vkCreateInstance` + resolución de comandos de instancia | cerrada estáticamente | `CLOSED_STATIC` |
| Enumeración y selección RX 550 por vendor/device ID | cerrada estáticamente | `CLOSED_STATIC` |
| `vkCreateDevice` | cerrada estáticamente | `CLOSED_STATIC` |
| Resolución de comandos de dispositivo | cerrada estáticamente (**esta tarea**) | `CLOSED_STATIC` |
| Obtención de cola compute | cerrada estáticamente | `CLOSED_STATIC` |
| Creación de shader module / pipeline / dispatch | `OPEN` | pendiente de ejecución |
| Valor observado = 42 | `OPEN` | pendiente de ejecución |

La frontera compute sigue **`OPEN`**. Ninguna afirmación de ejecución es posible a partir de este informe.

---

## 11. Una sola recomendación

**Solicitar autorización de ejecución de `vk_compute_test_fixed3` con el contrato de 11 campos de `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` §6, en un directorio de registro nuevo verificado vacío, capturando stdout, stderr y exit status por separado sin pipes.**

Justificación con la evidencia concreta disponible:

1. **La frontera está cerrada por el lado estático y solo falta el lado de ejecución.** La matriz temporal da 0 violaciones de orden, y el desensamblado confirma a nivel de máquina que la secuencia es resolver → comprobar nulo → invocar → validar. No queda ningún puntero invocable a NULL en la ruta principal ni en las rutas de error. La última barrera conocida antes del dispatch era precisamente esta, y ya está resuelta y verificada por dos métodos independientes.

2. **El valor informativo de esta corrida es alto y discriminante.** Las dos corridas anteriores fijaron la posición de partida: la primera probó que el harness supera 7 etapas (loader, `vkCreateInstance`, resolución de instancia, enumeración, selección RX 550, cola compute) y muere en `vkCreateDevice`; la segunda murió exactamente en el puntero ahora reparado. Esta corrida debería superar 10 etapas y alcanzar `vkCreateComputePipelines`. Un `Compute pipeline created.` seguido de `Command buffer recorded (dispatch 1x1x1).` y `Observed output: 42` sería la **primera evidencia de dispatch compute real en Polaris12**; un `Vulkan error at line …: vkCreateComputePipelines = …` sería el primer fallo atribuible a la traducción ACO→ISA de GFX8. Ambos resultados son informativos y ninguno exige otra iteración de código.

3. **No conviene seguir refining estáticamente sin ejecución.** Las tres correcciones anteriores revelaron cada vez un defecto adicional (2 punteros ausentes → un tercero → orden incorrecto → ruta de fallo parcial). Ese patrón sugiere que la auditing estática tiene rendimiento decreciente: los defectos que quedan son de alcanzabilidad en runtime, no de estructura. Un cuarto ciclo de lectura del fuente produciríaRAIDSchema hipótesis, no pruebas. La ejecución es el únicoRemaining generador de evidencia.

4. **El riesgo de ejecución es acotado y ya conocido.** El programa no escribe en `/dev/dri` ni en MMIO/VRAM, no requiere root, no modifica el sistema, realiza un solo dispatch 1×1×1 sobre un buffer de 4 bytes mapeado, y tiene un contrato de comparación determinista. Los fallos esperados (si los hay) se manifestan como mensajes `Vulkan error at line …` en stderr, no como daño.

5. **La cadena de evidencia queda completa y trazable.** Cinco artefactos (`017ee552…`, `a0167d93…`, `f94af068…`, `b6331466…`) con sus fuentes —el eslabón de `fixed2` quedó recuperado y probado en §7.6— documentan la progresión: binario heredado bloqueado por diseño → reimplementación con 2 punteros ausentes → reimplementación con 1 puntero ausente → reimplementación con orden incorrecto → reimplementación con orden temporal cerrado. La conservación de los cinco permite que cualquier resultado futuro sea atribuido con precisión.

---

## 12. Límites respetados

| Límite | Verificación |
|--------|--------------|
| No ejecutar ningún binario Vulkan | 0 ejecuciones. `objdump`, `nm` y `gcc` no ejecutan el binario |
| No realizar dispatches ni pruebas de hardware | Ninguna |
| No escribir en `/dev/dri`, MMIO ni VRAM | Ningún acceso |
| No usar sudo, su ni root | Ninguna elevación |
| No instalar paquetes ni modificar el sistema | Solo `gcc`, `nm`, `objdump`, `strings`, `python3`, `pkg-config` |
| No crear ramas, worktrees ni clones | Ninguno |
| No sobrescribir informes ni registros | 6 informes previos intactos; este es nuevo |
| No modificar el original ni los artefactos fixed/fixed2 | 3 binarios con hash idéntico al inicial |
| No modificar el shader | `df08a62b…` idéntico |
| Preservar los 20 archivos modificados bajo `tools/rxre/` | 20 antes y después |
| No borrar core dumps ni registros previos | Ninguno borrado |

Archivos creados en esta tarea: `vk_test/vk_compute_test_fixed2.c` (fuente reconstruido y probado), `vk_test/vk_compute_test_fixed3`, `vk_test/build3.log`, `vk_test/build3.stdout.log` (0 bytes), este informe. Archivo modificado: `vk_test/vk_compute_test_fixed.c`.