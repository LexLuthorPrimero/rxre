# RXRE — Ejecución compute real y validación numérica en RX 550 Polaris12

**Autorización:** ejecución de `vk_test/vk_compute_test` exclusivamente. Cubre solo esta prueba compute.

**Resultado: `BLOCKED` — Resultado D (error previo al dispatch).** La prueba **no alcanzó ningún dispatch compute**. El fallo es de inicialización Vulkan por un defecto determinista en el patrón de carga de funciones del propio binario. **No es una prueba de cálculo fallida.**

Registros crudos: `findings/1616-1625/ejecucion_compute_20261016/`

---

## 1. Fase 1 — Contrato previo (cumplido)

### 1.1 Identidad de artefactos

| Artefacto | SHA-256 esperado | SHA-256 registrado | Resultado |
|-----------|------------------|--------------------|-----------|
| `vk_test/vk_compute_test` | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` | **COINCIDE** |
| `/tmp/rxre_spirv_tests/simple.comp.spv` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | `df08a62b594cca8480aac4a05f0886b19514f25995ad97b34a6d4ee94be4a86a` | **COINCIDE** |

Ningún artefacto fue sustituido.

### 1.2 Estructura del shader

| Propiedad | Valor esperado | Valor observado | Resultado |
|-----------|-----------------|------------------|-----------|
| Tamaño | 612 bytes | 612 bytes | **COINCIDE** |
| Magic SPIR-V | `0x07230203` | `0x07230203` | **COINCIDE** |
| Versión | SPIR-V 1.0 | `0x00010000` | **COINCIDE** |
| Bound | — | 18 | — |
| mtime | — | 2026-10-15 20:15:52 -0300 | anterior al build del ELF |
| Permisos | — | `-rw-r--r-- lucas lucas` | accesible sin elevación |

### 1.3 Dependencias Vulkan

```
ldconfig -p | grep libvulkan
  libvulkan.so.1        => /lib64/libvulkan.so.1
  libvulkan_radeon.so   => /lib64/libvulkan_radeon.so
```

```
$ ldd vk_test/vk_compute_test | grep vulkan
	libvulkan.so.1 => /lib64/libvulkan.so.1 (0x00007fbfcfe33000)
```

**Sin dependencias faltantes.** El ICD de RADV está presente y la biblioteca del driver existe (19378176 bytes, mtime 2026-09-30 21:00).

### 1.4 Variables de entorno

| Variable | Estado |
|----------|--------|
| `VK_ICD_FILENAMES` | no definida |
| `VK_DRIVER_FILES` | no definida |
| `VK_LAYER_PATH` | no definida |
| `LD_LIBRARY_PATH` | no definida |
| `VK_LOADER_DEBUG` | no definida |
| `DISPLAY` | `:0` |
| `WAYLAND_DISPLAY` | `wayland-0` |
| `XDG_RUNTIME_DIR` | `/run/user/1000` |

**Ninguna variable apunta a `/opt/mesa-26.2.2-rx550-haswell`** (verificado con `env | grep`), y ese prefijo **no existe**. No había configuración obsoleta que invalidara la ejecución.

### 1.5 Ausencia de conflicto

```
$ pgrep -af 'vk_compute_test' | grep -v 'pgrep\|/bin/bash -c'
(sin resultados)
```

El match inicial era el propio shell del `pgrep` auto-detectándose. **Ningún proceso competidor.** La GPU está en uso por el stack gráfico (plasma, Xwayland, firefox, RDD), lo cual es normal y no bloqueante.

---

## 2. Fase 2 — Identidad independiente del dispositivo

### 2.1 Evidencia por sysfs (independiente del binario)

```
$ lspci -nn -s 01:00.0
01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI]
        Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X] [1002:699f] (rev c7)

$ cat /sys/class/drm/card1/device/{vendor,device,revision}
0x1002
0x699f
0xc7
```

| Atributo | Valor | Requisito | Resultado |
|----------|-------|-----------|-----------|
| `vendor` | `0x1002` (AMD) | `1002` | **COINCIDE** |
| `device` | `0x699f` | `699f` | **COINCIDE** |
| `revision` | `0xc7` | `c7` | **COINCIDE** |
| PCI address | `0000:01:00.0` | `0000:01:00.0` | **COINCIDE** |
| Nombre marketing | Lexa PRO / RX 550 | RX 550 | **COINCIDE** |

### 2.2 Desambiguación respecto a la Intel HD 4600

```
$ ls -la /dev/dri/by-path/
pci-0000:01:00.0-card                        -> ../card1
pci-0000:01:00.0-platform-simple-framebuffer.0-card -> ../card0
pci-0000:01:00.0-render                       -> ../renderD128
```

**El nodo de render (`renderD128`) pertenece a `0000:01:00.0` = RX 550.** El Intel HD 4600 es `card0` vía `simple-framebuffer` y **no tiene nodo de render**. No hay posibilidad de confusión: la prueba, de haber llegado a abrir el dispositivo, habría usado el RX 550.

El dispositivo Intel que controla la pantalla **no fue modificado ni interrumpido**.

### 2.3 Driver Vulkan

| Componente | Valor |
|-----------|-------|
| ICD | `/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` |
| Biblioteca del driver | `/usr/lib64/libvulkan_radeon.so` (19378176 bytes) |
| API declarada por el ICD | `1.4.354` |
| Loader | `/lib64/libvulkan.so.1` |

---

## 3. Fase 3 — Ejecución autorizada

### 3.1 Registro temporal

| Marca | Valor ISO 8601 |
|-------|----------------|
| T0 (inicio) | `2026-10-16T13:03:54-03:00` |
| T1 (fin) | `2026-10-16T13:03:58-03:00` |
| Duración | 4 segundos |

### 3.2 Comando ejecutado (una sola vez, sin pipelines)

```
./vk_test/vk_compute_test > stdout.txt 2> stderr.txt
RC=$?
```

Sin argumentos: el binario usó su ruta embebida `/tmp/rxre_spirv_tests/simple.comp.spv` (referencia única en `0x403220`). Sin recompilación, sin regeneración de shader, sin variables Vulkan forzadas.

### 3.3 stdout completo (51 bytes, íntegro)

```
=== Vulkan Compute Test — RX 550 / POLARIS12 ===
```

### 3.4 stderr completo (59 bytes, íntegro)

```
Failed to load Vulkan function: vkEnumeratePhysicalDevices
```

### 3.5 Exit status real

```
1
```

Verificado inmediatamente después de la redirección, antes de cualquier otro comando. **No se repitió la ejecución.**

---

## 4. Fase 4 — Integridad posterior

| Verificación | Resultado |
|--------------|-----------|
| SHA-256 ELF post | `017ee552…071745` — **idéntico** |
| SHA-256 shader post | `df08a62b…4a86a` — **idéntico** |
| `diff hashes_pre.txt hashes_post.txt` | sin diferencias |
| Archivos de registro | 7 archivos, ninguno vacío salvo los esperables |
| Archivos modificados en `/tmp` | ninguno |
| Archivos modificados bajo `tools/rxre/` | **20** (idéntico al previo) |
| Archivos modificados en total por esta tarea | 0 (solo 1 informe nuevo + 7 registros) |

### Archivos de registro creados

```
findings/1616-1625/ejecucion_compute_20261016/
  timestamp_inicio.txt   26 bytes
  hashes_pre.txt        194 bytes
  stdout.txt             51 bytes
  stderr.txt             59 bytes
  exit_status.txt         2 bytes
  timestamp_fin.txt      26 bytes
  hashes_post.txt       194 bytes
```

Directorio verificado como vacío antes de escribir: no se sobrescribió ningún registro previo.

---

## 5. Interpretación causal — Resultado D

### 5.1 Clasificación

**Resultado D: fallo de inicialización Vulkan, previo al dispatch.**

No es un resultado B (FAIL con observado cero) ni C (FAIL con otro valor). No hubo valor observado: **el shader nunca se cargó en la GPU y ningún dispatch se emitió**.

### 5.2 Punto exacto del fallo

Traza reconstruida con el desensamblado (mismo artefacto auditado en `VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md`):

| Dirección | Acción | Estado |
|-----------|--------|--------|
| `0x4009ac` | `fwrite` del banner a stdout | **COMPLETADO** (stdout tiene la línea) |
| `0x4009b6` | `call load_all_functions` | INICIADO |
| `0x400592` | `dlopen("libvulkan.so.1")` | **OK** (no hay mensaje "Cannot open") |
| `0x4005e1` | `dlsym("vkGetInstanceProcAddr")` | **OK** (no hay mensaje "Cannot load") |
| `0x400626` | `load_func("vkCreateInstance")` | **FALLA SILENCIOSAMENTE** |
| `0x400637` | `load_func("vkEnumeratePhysicalDevices")` | **FALLA → mensaje + `exit(1)`** |

El mensaje de error corresponde a `load_func` en `0x400557`–`0x400579`:
```asm
40054a: call *%rcx                    ; vkGetInstanceProcAddr(g_instance, name)
400550: cmpq $0x0,-0x8(%rbp)          ; ¿devolvió NULL?
400555: jne 40057e                    ; si no, retorna el puntero
400562: mov  $0x402f68,%esi           ; "Failed to load Vulkan function: %s"
40056f: call *<fprintf@plt>
400579: call *<exit@plt>              ; exit(1)
```

### 5.3 Causa raíz — `PROVEN` por análisis estático

**El binario resuelve `vkCreateInstance` usando `vkGetInstanceProcAddr` con `g_instance == NULL`.**

Evidencia:

1. `load_func` lee el primer argumento de `vkGetInstanceProcAddr` desde el símbolo global `g_instance` (`0x4050c0`):
   ```asm
   400539: mov 0x4b80(%rip),%rax   # 4050c0 <g_instance>
   40054a: call *%rcx              ; rdi = g_instance
   ```

2. `g_instance` está en `.bss` (`nm`: `00000000004050c0 b g_instance`) → **valor inicial 0**.

3. `load_func("vkCreateInstance")` es la **primera** llamada de la tabla (`0x400626`), es decir, antes de que exista ninguna instancia.

4. El puntero `p_vkCreateInstance` (`0x4050e8`) se asigna en `0x40062b`, inmediatamente tras el retorno de `load_func`.

**Por qué falla siempre:** la especificación de Vulkan establece que `vkGetInstanceProcAddr(instance, pName)` devuelve un puntero válido cuando `instance` es `NULL` únicamente para los comandos globales (`vkEnumerateInstanceExtensionProperties`, `vkEnumerateInstanceLayerProperties`, `vkCreateInstance`). Para cualquier otro comando **debe** devolver `NULL`.

Por tanto el fallo no es una limitación del driver ni del entorno: es un defecto determinista del patrón de carga del binario.

### 5.3-bis CORRECCIÓN DE LA ATRIBUCIÓN (2026-10-16)

Una versión anterior de este informe Bradbury horny apuntaba que el fallo radicaba en resolver `vkCreateInstance` con `g_instance == NULL`. **Esa atribución era incorrecta y queda corregida.**

**La resolución de `vkCreateInstance` con instancia nula es el mecanismo correcto y esperado de Vulkan para un comando global, y así se comportó.**

Orden real de las 7 llamadas a `load_func` dentro de `load_all_functions` (`0x400626`–`0x40068c`), resuelto contra la tabla de cadenas en `.rodata`:

| # | Dirección del nombre | Nombre cargado | `g_instance` | Resultado |
|---|----------------------|----------------|--------------|-----------|
| 1 | `0x402ff3` | `vkCreateInstance` | `NULL` | **RESUELTO** (comando global) |
| 2 | `0x403004` | `vkEnumeratePhysicalDevices` | `NULL` | **FALLA → mensaje + `exit(1)`** |
| 3 | `0x40301f` | `vkGetPhysicalDeviceProperties` | — | no alcanzado |
| 4 | `0x403040` | `vkGetPhysicalDeviceQueueFamilyProperties` | — | no alcanzado |
| 5 | `0x403070` | `vkGetPhysicalDeviceMemoryProperties` | — | no alcanzado |
| 6 | `0x403094` | `vkGetPhysicalDeviceFeatures` | — | no alcanzado |
| 7 | `0x4030b0` | `vkDestroyInstance` | — | no alcanzado |

Evidencia directa de que la carga 1 funcionó:

```asm
400626: call 400526 <load_func>      ; load_func("vkCreateInstance")
40062b: mov  %rax,0x4ab6(%rip)       ; 4050e8 <p_vkCreateInstance>  ← RETORNÓ NO-NULL
400637: call 400526 <load_func>      ; load_func("vkEnumeratePhysicalDevices")
```

El hecho de que `p_vkCreateInstance` se asigne en `0x40062b` **y** de que la ejecución continúe hasta `0x400637` prueba que la primera resolución devolvió un puntero válido. Si hubiera fallado, `load_func` habría ejecutado `exit(1)` en `0x400579` sin alcanzar la segunda llamada.

**Defecto real, reformulado:** `load_all_functions` carga en un único lote, **antes** de crear la instancia, tanto comandos globales como comandos que requieren una instancia válida. `vkEnumeratePhysicalDevices` es un comando de instancia y, por tanto, devuelve correctamente `NULL` cuando se le pasa `g_instance == NULL`. El binario no distingue entre ambos tipos de comando.

**Clasificación: `PROVEN`.** El orden de las llamadas se lee del desensamblado; la tabla de nombres se resuelve contra `strings -t x`; el comportamiento de `vkGetInstanceProcAddr` con instancia nula es un hecho documentado de la especificación Vulkan, no una inferencia sobre el código.

### 5.4 Hipótesis descartadas

| Hipótesis | Veredicto | Evidencia |
|-----------|-----------|-----------|
| El shader no se compiló | **DESCARTADA** | El fallo ocurrió en `0x400637`, dentro de `load_all_functions`, muy anterior a cualquier lectura del shader (`fopen` del `.spv` ocurre en `0x401099`, después de crear la instancia) |
| El dispatch no se envió | **DESCARTADA** | `vkCreateInstance` se resolvió pero nunca se invocó (`p_vkCreateInstance` está en `0x4050e8`; no hay llamada a `*%rcx` con ese puntero antes del fallo). No existió instancia, ni device, ni cola, ni buffer |
| El driver RADV no soporta la función | **DESCARTADA** | El ICD declara API 1.4.354 y `libvulkan_radeon.so` está presente. `vkEnumeratePhysicalDevices` es una función Vulkan 1.0 obligatoria. El retorno `NULL` es el comportamiento **correcto** de `vkGetInstanceProcAddr` con instancia nula, no una ausencia en el driver |
| El ICD no fue encontrado por el loader | **DESCARTADA** | `dlopen("libvulkan.so.1")` y `dlsym("vkGetInstanceProcAddr")` funcionaron; `vkCreateInstance` se resolvió correctamente, lo que demuestra que el puntero base es válido |
| Variables de entorno obsoletas | **DESCARTADA** | Ninguna variable Vulkan definida; `/opt/mesa-26.2.2-rx550-haswell` no aparece ni existe |
| Permisos insuficientes | **DESCARTADA** | El fallo es aritmético del flujo de control, no de permisos: `dlopen`/`dlsym` funcionaron y el proceso alcanzó `exit(1)` por su propia lógica |
| Fallo del shader o del binding | **NO APLICABLE** | No se alcanzó esa fase |

---

## 6. Estado epistemico y alcance

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| La ejecución se produjo y se registró completamente | **PROVEN** | 7 archivos de registro, stdout/stderr íntegros, exit status capturado |
| La GPU objetivo es RX 550 Polaris12 (`1002:699f` rev `c7`) en `0000:01:00.0` | **PROVEN** | sysfs `vendor`/`device`/`revision`, `lspci`, symlink `by-path` |
| El nodo de render pertenece al RX 550, no al Intel | **PROVEN** | `pci-0000:01:00.0-render → renderD128`; el Intel es `simple-framebuffer` sin render node |
| La prueba alcanzó un dispatch compute | **REFUTED** | El flujo abortó en `load_all_functions`, antes de `vkCreateInstance` |
| La prueba produjo un valor observado | **REFUTED** | No existe línea `Expected output:` ni `Observed output:` en stdout |
| El fallo es del patrón de carga del binario | **PROVEN** | `g_instance == NULL` en `.bss`, `load_func` lo usa como primer argumento, `vkCreateInstance` es el primer nombre de la tabla |
| Compute funciona o falla en Polaris12 | **OPEN** | Esta ejecución no aporta evidencia sobre el comportamiento de compute |
| El shader en `/tmp` es el del build original | **OPEN** | Sin cambio respecto a la auditoría estática |

---

## 7. Frontera: `BLOCKED`

**Justificación:** el objetivo de esta tarea era obtener evidencia de ejecución del compute en Polaris12. La ejecución se realizó pero **no produjo evidencia utilizable**: el binario no puede superar su propia fase de inicialización con ninguna configuración de entorno. Reintentar sin modificar el binario produciría el mismo resultado de forma determinista.

No se clasifica como `OPEN` porque existe una causa identificada y verificable, no una incertidumbre.
No se clasifica como `CLOSED_EXECUTION` porque no hubo dispatch ni valor observado.

**La frontera de ejecución compute en Polaris12 permanece sin demostrar.**

---

## 8. GLOBAL_WORK_SCAN

| Frontera | Estado | Efecto |
|----------|--------|--------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| **RADV/GFX8 ejecución compute** | **`BLOCKED`** — binario con defecto de inicialización determinista | Reemplaza `OPEN` con causa identificada |
| RADV/GFX8 ejecución tess/geom | OPEN | Ninguno |
| RADV/GFX8 ejecución vertex/fragment | OBSERVED (vkcube, ruta integrada) | Ninguno |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |

**No se reabrió ninguna frontera cerrada.** No se corrieron pruebas adicionales ni se modificó el entorno.

---

## 9. Verificaciones de integridad finales

| Verificación | Resultado |
|--------------|-----------|
| `git status --porcelain \| grep -c '^ M tools/rxre/'` | **20** (idéntico) |
| SHA-256 ELF pre/post | idénticos |
| SHA-256 shader pre/post | idénticos |
| Archivos modificados por la ejecución | **0** |
| Archivos creados | **8** (1 informe + 7 registros en directorio nuevo) |
| Registros previos sobrescritos | **0** (directorio verificado vacío) |
| Binario modificado | No |
| Shader modificado | No |
| `/dev/dri` / MMIO / VRAM | No |
| sudo / root | No |
| Paquetes instalados | No |
| Configuración modificada | No |
| Dispositivo Intel interrumpido | No |
| Pruebas Vulkan adicionales | No |
| Despatches fuera del binario | No |

---

## 10. Siguiente frontera prioritaria (una sola)

**Determinar mediante análisis estático si existe una variante del harness que resuelva `vkCreateInstance` por el camino correcto (`vkGetInstanceProcAddr(NULL, "vkCreateInstance")` o `dlopen` + `dlsym` directo), sin modificar el binario existente ni escribir código nuevo en esta tarea.**

Justificación con evidencia concreta:
- La causa raíz es una única instrucción: `load_func` pasa `g_instance` (NULL en ese punto) como primer argumento de `vkGetInstanceProcAddr` para un comando que requiere ese valor nulo. La corrección sería llamar `load_func` con el puntero global cuando `g_instance` sea NULL.
- El repositorio contiene `tools/rxre/` con adaptadores de backend y un framework de dispatch. Existe la posibilidad de que ya haya una vía de ejecución programática que evite el defecto del binario, o de que el mismo patrón de carga esté presente en herramientas propias.
- Si esa vía existe y puede auditarse, permitiría obtener la evidencia de ejecución compute sin tocar el artefacto original, que debe preservarse por su valor de evidencia histórica.
- Si no existe, la alternativa sería solicitar autorización específica para corregir `load_func` en el binario, lo que produciría un artefacto distinto que debería registrarse con hash propio para no confundirlo con el original.

No se inicia esa investigación en esta tarea.

---

## 11. Nota sobre el alcance de esta conclusión

Esta tarea **no demuestra** que compute funcione ni falle en Polaris12. Demuestra únicamente que el binario `vk_compute_test` en su forma actual no puede inicializar Vulkan, independientemente del dispositivo, del driver y del entorno. La evidencia sobre el comportamiento real de compute en GFX8 sigue ausente y requiere una vía de ejecución distinta.
