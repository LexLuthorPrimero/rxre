# RXRE — Ejecución controlada de `vk_compute_test_fixed` (RX 550 Polaris12)

**Misión:** Determinar si el harness reimplementado `vk_compute_test_fixed` puede inicializar Vulkan, seleccionar la RX 550 Polaris12 y ejecutar el caso compute cuyo resultado esperado es 42.

**Resultado: `INCONCLUSIVE (F)` con causa raíz identificada — `SIGSEGV` por puntero de función nulo en `p_vkCreateDevice`.**

**No se alcanzó ningún dispatch. No hay valor observado. No se declara `CLOSED_EXECUTION`.**

No se afirma equivalencia con el binario original ni se generaliza a GFX8.

Registros primarios: `findings/1616-1625/ejecucion_compute_fixed_20261016/`

---

## 1. Verificaciones previas a la ejecución

| Verificación | Comando | Resultado |
|--------------|---------|-----------|
| Estado Git | `git status --porcelain \| grep -c '^ M tools/rxre/'` | **20** (preservados) |
| Fuente presente | `ls vk_test/vk_compute_test_fixed.c` | PRESENTE, 21789 B |
| Binario presente | `ls vk_test/vk_compute_test_fixed` | PRESENTE, 18800 B |
| `build.log` presente | `ls vk_test/build.log` | PRESENTE, 8545 B |
| Shader presente | `ls /tmp/rxre_spirv_tests/simple.comp.spv` | PRESENTE, 612 B |
| Hash del binario | `sha256sum vk_test/vk_compute_test_fixed` | `a0167d93…2af3d` — **coincide con el auditado** |
| Hash del shader | `sha256sum /tmp/rxre_spirv_tests/simple.comp.spv` | `df08a62b…4a86a` — **coincide con el auditado** |
| Contrato de argv | `grep -n -A2 'shader_path =' …c` | `argc > 1 ? argv[1] : "/tmp/rxre_spirv_tests/simple.comp.spv"` |
| Directorio de registro | `test -e …/ejecucion_compute_fixed_20261016` | NO existía → creado vacío |

**Clasificación: `PROVEN`.** Ningún artefacto faltó ni divergió.

---

## 2. Registro de la ejecución

### 2.1 Identidad

| Campo | Valor |
|-------|-------|
| Ruta absoluta del ejecutable | `/home/lucas/Escritorio/rxre/vk_test/vk_compute_test_fixed` |
| SHA-256 del ejecutable | `a0167d931e9ae9e33b4a6e645c4ceaf6ea5b08f4c33d75328fa8c9c39ac2af3d` |
| SHA-256 del shader | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` |
| Directorio de trabajo | `/home/lucas/Escritorio/rxre` |
| T0 (inicio) | `2026-10-16T13:25:59-03:00` |
| T1 (fin) | `2026-10-16T13:26:03-03:00` |
| Duración | 4 s |

### 2.2 Comando exacto

```bash
./vk_test/vk_compute_test_fixed > $D/stdout.txt 2> $D/stderr.txt
RC=$?
```

Sin argumentos: el binario usó su ruta por defecto embebida. Sin pipelines. Sin elevación. **Ejecutado una sola vez**, no repetido.

### 2.3 Salida completa

**stdout: 0 bytes (vacío)**
```
[contenido vacío]
```

**stderr: 0 bytes (vacío)**
```
[contenido vacío]
```

**Exit status: `139`**
```
139
```

Mensaje del shell (fuera de los flujos capturados):
```
Violación de segmento  (`core' generado) ./vk_test/vk_compute_test_fixed
```

`139 = 128 + 11` → **SIGSEGV**.

### 2.4 Integridad posterior

| Artefacto | Hash pre | Hash post | Resultado |
|-----------|----------|-----------|-----------|
| `vk_compute_test_fixed` | `a0167d93…` | `a0167d93…` | **IDÉNTICO** |
| `simple.comp.spv` | `df08a62b…` | `df08a62b…` | **IDÉNTICO** |
| `vk_compute_test` (original) | `017ee552…` | `017ee552…` | **IDÉNTICO** |
| Archivos modificados en `tools/rxre/` | 20 | 20 | **INTACTOS** |

---

## 3. Análisis del crash (evidencia primaria)

### 3.1 Captura del core

`systemd-coredump` capturó el dump (PID `1883682`, coincide con el de nuestra ejecución):

```
/var/lib/systemd/coredump/core.vk_compute_test.1000.f3f071906ebf44988b70fe60fbb6553e.1883682.1792167962000000.zst
```

Extraído con `zstd -dc` a `/tmp/opencode/core_fixed.core` (23183360 bytes). **No se re-ejecutó el binario.**

### 3.2 Backtrace

```
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0000000000000000 in ?? ()
#1  0x0000000000400860 in main ()
```

Registros en el momento del fallo:

| Registro | Valor | Interpretación |
|----------|-------|----------------|
| `rip` | `0x0` | **se intentó ejecutar código en la dirección nula** |
| `r12` | `0x0` | puntero de función called-era nulo |
| `rdi` | `0x3e4755b0` | = `r14`; dirección en el espacio del driver, no del binario |
| `rdx` | `0x0` | `pAllocator = NULL` |
| `rbx` | `0x0` | |

Instrucción del crash (`0x40085d` → `0x400860`):

```asm
400830: mov    %rcx,%r12          ; r12 = puntero de función
...
400847: mov    %r14,%rdi          ; rdi = pdev (VkPhysicalDevice)
40084a: movl   $0x1,0x3c4(%rsp)   ; dci.queueCreateInfoCount = 1
400855: mov    %rax,0x3c8(%rsp)   ; dci.pQueueCreateInfos = &qci
40085d: call   *%r12              ; LLAMADA CON r12 == NULL
400860: test   %eax,%eax          ; (no se alcanza)
```

### 3.3 Mapeo al fuente

Los valores inicialesizados antes de la llamada corresponden a `VkDeviceCreateInfo` y `VkDeviceQueueCreateInfo`:

| Offset en pila | Valor | Campo |
|----------------|-------|-------|
| `0x1d0(%rsp)` | `2` | `qci.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO` (=2) |
| `0x1e4(%rsp)` | `%ebx` | `qci.queueFamilyIndex` |
| `0x1e8(%rsp)` | `1` | `qci.queueCount = 1` |
| `0x3b0(%rsp)` | `3` | `dci.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO` (=3) |
| `0x3c4(%rsp)` | `1` | `dci.queueCreateInfoCount = 1` |
| `0x3c8(%rsp)` | `%rax` | `dci.pQueueCreateInfos = &qci` |

La llamada es exactamente:

```c
CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");
```

(fuente línea 385)

### 3.4 Causa raíz — bug en la reimplementación

**`p_vkCreateDevice` se usa pero nunca se resuelve.**

```c
/* línea 80: declaración */
static PFN_vkCreateDevice   p_vkCreateDevice   = NULL;

/* línea 385: uso */
CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");
```

`load_instance_funcs()` carga cinco funciones:

```c
LOAD_INST(p_vkDestroyInstance, vkDestroyInstance);
LOAD_INST(p_vkEnumeratePhysicalDevices, vkEnumeratePhysicalDevices);
LOAD_INST(p_vkGetPhysicalDeviceProperties, vkGetPhysicalDeviceProperties);
LOAD_INST(p_vkGetPhysicalDeviceMemoryProperties, vkGetPhysicalDeviceMemoryProperties);
LOAD_INST(p_vkGetPhysicalDeviceQueueFamilyProperties, vkGetPhysicalDeviceQueueFamilyProperties);
```

**`vkCreateDevice` y `vkGetDeviceQueue` no están en esa lista.** `vkCreateDevice` es un comando de **instancia** y debía cargarse en esa fase; `vkGetDeviceQueue` es de **device** y debía cargarse en `load_device_funcs()`.

Verificación:

```bash
$ grep -n 'p_vkCreateDevice\|p_vkGetDeviceQueue' vk_test/vk_compute_test_fixed.c
80:static PFN_vkCreateDevice   p_vkCreateDevice   = NULL;
82:static PFN_vkGetDeviceQueue p_vkGetDeviceQueue = NULL;
385:	CHECK(p_vkCreateDevice(pdev, &dci, NULL, &dev), "vkCreateDevice");
388:	p_vkGetDeviceQueue(dev, qfam, 0, &queue);
```

Solo la declaración y el uso. **Ninguna asignación.**

**Clasificación: `PROVEN`.** La ausencia de asignación es verificable por inspección del fuente; la llamada nula es verificable por el backtrace y `r12 = 0x0`.

### 3.5 El defecto es del artefacto nuevo, no del original

| Artefacto | ¿Tiene este defecto? | Evidencia |
|-----------|----------------------|-----------|
| `vk_compute_test` (original) | **NO** | Su tabla de 7 nombres incluye `vkCreateInstance` y 6 de instancia; resuelve `vkCreateDevice` en la fase correcta (después del device, en `0x400e0c`+). Su fallo era distinto: abortar antes de crear la instancia |
| `vk_compute_test_fixed` (nuevo) | **SÍ** | `p_vkCreateDevice` nunca se asigna |

El bug fue introducido por la reimplementación y no es una propiedad heredada del original.

---

## 4. Clasificación discriminante del resultado

**Resultado F: programa termina sin demostrar si alcanzó el dispatch — pero con causa raíz identificada.**

La taxonomía de la misión sería «C. Dispositivo correcto, fallo antes del dispatch» **si** pudiéramos confirmar que el dispositivo fue seleccionado. No podemos confirmarlo por stdout (vacío), pero sí podemos acotarlo:

### 4.1 Qué se sabe

| Etapa | Estado | Evidencia |
|-------|--------|-----------|
| Carga del loader (`dlopen`/`dlsym`) | **Superada** | Habría emitido `Cannot open libvulkan.so.1` o `Cannot load vkGetInstanceProcAddr` a stderr; stderr está vacío |
| Resolución de `vkCreateInstance` | **Superada** | Ídem: habría emitido `Failed to load Vulkan function: vkCreateInstance` |
| Creación de instancia | **Superada** | Ídem: `vk_error()` escribe a stderr sin buffer |
| Carga de las 5 funciones de instancia | **Superada** | Ídem |
| **Enumeración de dispositivos** | **Superada** | Habría emitido `No Vulkan physical devices` o `Out of memory` |
| **Búsqueda y selección de RX 550** | **Superada** | Habría emitido `RX 550 (vendor=0x1002 device=0x699f) NOT found` |
| **Búsqueda de cola compute** | **Superada** | Habría emitido `No compute memory type` / `No compute queue family` |
| `vkCreateDevice` | **FALLÓ** | `SIGSEGV` por puntero nulo |
| Dispatch | **NO ALCANZADO** | — |
| Lectura del buffer | **NO ALCANZADA** | — |
| Comparación | **NO ALCANZADA** | — |

**Todas las rutas de error anteriores escriben con `fprintf(stderr, …)`, que es no-buferizado.** Un fallo en cualquiera de ellas habría dejado texto en `stderr.txt`. El archivo tiene **0 bytes**.

**Clasificación: `CORROBORATED`** — la inferencia de que las etapas 1–7 se superaron se apoya en que stderr está vacío y en que `stderr` no se bufferiza. No es una prueba directa de que la enumeración tuviera éxito, pero es evidencia fuerte y suposición cero.

### 4.2 Lo que no puede afirmarse

| Afirmación | Estado |
|------------|--------|
| El dispositivo Vulkan seleccionado fue la RX 550 | **`INFERRED`** — el banner `>>> SELECTED:` y la línea `GPU%u: …` estaban en el buffer de stdout, perdido por SIGSEGV. No hay evidencia directa del `vendorID`/`deviceID` del dispositivo que esta corrida seleccionó |
| Hubo acceso al driver RADV | **`PROVEN`** para el proceso: el core tiene mapeados `/usr/lib64/libvulkan_radeon.so` y `/usr/lib64/libvulkan_dzn.so` (bibliotecas de drivers ICD). **No se puede afirmar** cuál se usó para la enumeración |
| Compute funciona o falla en Polaris12 | **`OPEN`** — no se alcanzó el pipeline |

### 4.3 Acceso al dispositivo

La tarea advierte: *«No afirmar que no hubo acceso al dispositivo solo porque el harness no escriba directamente en `/dev/dri`»*.

**Hubo acceso al dispositivo.** Evidencia:
- El core contiene `libvulkan_radeon.so` mapeada en `0x7fba3aa00000–0x7fba3bc62000`.
- `vkCreateInstance` se ejecutó (superó esa fase) y el loader negocia los ICDs durante esa llamada.
- `vkEnumeratePhysicalDevices` se ejecutó, lo que requiere acceso al driver.

No se sitúa ninguna escritura en MMIO o VRAM por el harness: solo usa la API Vulkan estándar. No se ejecutó `gpu_recover`, no se usaron escrituras a `/dev/dri`, no hubo `sudo`.

---

## 5. Clasificación epistemológica

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| La ejecución se produjo con hash de binario y shader coincidentes | **PROVEN** | Registros `hashes_pre.txt` / `hashes_post.txt` |
| El proceso terminó con SIGSEGV (exit 139) | **PROVEN** | `exit_status.txt` = 139; backtrace del core |
| `rip = 0x0` y `r12 = 0x0` en el momento del fallo | **PROVEN** | `info registers` sobre el core |
| La llamada fallida es `p_vkCreateDevice(pdev, &dci, NULL, &dev)` | **PROVEN** | Estructuras inicializadas en pila coinciden con `VkDeviceCreateInfo`; `rdx = 0` = `pAllocator` |
| `p_vkCreateDevice` nunca se resuelve en el fuente | **PROVEN** | `grep` sobre el fuente: solo declaración y uso |
| El defecto pertenece al artefacto nuevo, no al original | **PROVEN** | El original resuelve `vkCreateDevice` en la fase correcta (`0x400e0c`) |
| Las fases anteriores a `vkCreateDevice` se superaron | **CORROBORATED** | stderr vacío (0 bytes) y `fprintf(stderr)` no bufferizado en todas las rutas de error previas |
| El dispositivo seleccionado fue la RX 550 | **INFERRED** | El banner se habría impreso en stdout, perdido por SIGSEGV; no hay evidencia directa |
| El proceso accedió a los drivers ICD | **PROVEN** | `libvulkan_radeon.so` y `libvulkan_dzn.so` mapeadas en el core |
| El harness alcanzó el dispatch | **REFUTED** | El crash es anterior a `vkCreateDevice`; el pipeline no se creó |
| Compute produce 42 en Polaris12 | **OPEN** | No se evaluó |
| Equivalencia con el binario original | **OPEN** y no afirmable | Artefactos distintos; solo comparte el contrato de prueba |

---

## 6. Lo que esta corrida NO demuestra

- **No demuestra** que compute funcione ni falle en Polaris12.
- **No demuestra** equivalencia con `vk_compute_test`.
- **No demuestra** nada sobre GFX8 en general.
- **No invalida** el análisis estático previo del original: la cadena `polaris12 → oss300 → oss_3_0_0.reg → mmSDMA0_CHICKEN_BITS → 0x3405` no se ve afectada.
- **No aporta evidencia de ejecución de shaders**, ni compute, ni vertex/fragment.

---

## 7. GLOBAL_WORK_SCAN

| Frontera | Estado | Efecto de esta corrida |
|----------|--------|------------------------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| **RADV/GFX8 ejecución compute** | **`OPEN`** — el bloqueo anterior (binario original defectuoso) sigue vigente, y el artefacto nuevo tiene un defecto propio que impide obtener evidencia | La frontera no avanzó: se desplazó el defecto de un artefacto a otro |
| RADV/GFX8 ejecución tess/geom | OPEN | Ninguno |
| RADV/GFX8 ejecución vertex/fragment | OBSERVED (vkcube) | Ninguno |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |

**No se reabrió ninguna frontera cerrada.** No se ejecutó ninguna prueba adicional.

### Hipótesis discriminadas

| Hipótesis | Estado tras la corrida |
|-----------|------------------------|
| «El defecto del binario original es el único obstáculo para obtener evidencia de compute» | **REFUTADA** — el artefacto nuevo tiene un defecto independiente |
| «La resolución por fases es unkai corregir el problema del original» | **CONFIRMADA PARCIALMENTE** — el harness superó 7 fases que el original no alcanzaba; el fallo actual está en una fase no implementada |

---

## 8. Verificaciones de integridad

| Verificación | Resultado |
|--------------|-----------|
| `git status --porcelain \| grep -c '^ M tools/rxre/'` | **20** antes y después |
| Hash `vk_compute_test` (original) | `017ee552…071745` — **idéntico** |
| Hash `vk_compute_test_fixed` | `a0167d93…2af3d` — **idéntico** pre/post |
| Hash `simple.comp.spv` | `df08a62b…4a86a` — **idéntico** pre/post |
| Archivos modificados por esta tarea | **0** |
| Archivos creados | **1** informe + **7** registros en directorio nuevo |
| Correcciones de código | **0** — el bug se documenta, no se corrige en esta tarea |
| Re-ejecuciones | **0** — el binario se ejecutó una sola vez |
| Core dump analizado | Sin re-ejecución: `gdb` sobre el dump capturado |
| sudo / root | No |
| Escrituras MMIO / VRAM / `/dev/dri` | No |
| `gpu_recover` | No |
| Instalación de paquetes | No |
| Cambio de drivers, firmware, permisos, configuración | No |
| Otras pruebas o benchmarks | No |

---

## 9. Una sola siguiente acción prioritaria

**Corregir la carga de `vkCreateDevice` y `vkGetDeviceQueue` en `vk_test/vk_compute_test_fixed.c` y volver a compilar con un artefacto de hash nuevo, preservando tanto el original como la versión actual defectuosa.**

Justificación con evidencia concreta:

1. **El defecto está localizado con precisión y es de una línea.** `p_vkCreateDevice` falta en `load_instance_funcs()` y `p_vkGetDeviceQueue` falta en `load_device_funcs()`. Añadir dos llamadas `LOAD_INST` / `LOAD_DEV` corrige el flujo. No es un rediseño.

2. **La evidencia acumulada demuestra que el resto del camino funciona.** El harness superó siete etapas que el binario original no alcanzaba: carga del loader, resolución de `vkCreateInstance`, creación de instancia, carga de funciones de instancia, enumeración de dispositivos, búsqueda de la RX 550 por `vendorID`/`deviceID`, y búsqueda de cola compute. Ninguna emitió error.

3. **El registro de esta corrida tiene valor diagnóstico propio.** Un core dump con `r12 = 0x0` en la llamada a `p_vkCreateDevice` es evidencia directa y reutilizable del tipo de defecto que hay que evitar: usar un puntero de función sin verificar que fue resuelto.

4. **La corrección no invalida nada previo.** El original (`017ee552…`) y esta versión (`a0167d93…`) deben preservarse; la nueva llevaría un tercer hash. Los tres artefactos juntos documentan la progresión: binario heredado defectuoso → reimplementación con omisión → reimplementación completa.

5. **Resultado esperado de la siguiente ejecución:** si el harness supera `vkCreateDevice`, `vkGetDeviceQueue`, la carga de 28 funciones de device y `vkCreateComputePipelines`, imprimiría `Compute pipeline created.` y `Command buffer recorded (dispatch 1x1x1).`, lo que constituye la **primera evidencia de dispatch compute real en Polaris12**. Si `vkCreateComputePipelines` falla, el mensaje `Vulkan error at line …: vkCreateComputePipelines = …` permitiría atribuir el fallo a la traducción de ACO a ISA GFX8.

No se inicia esa corrección en esta tarea.
