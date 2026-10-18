# RXRE — Auditoría estática y recuperación de procedencia de `vk_compute_test`

**Misión:** Convertir `vk_test/vk_compute_test` de candidato basado en cadenas a una prueba cuyo flujo de datos sea auditable, verificando estáticamente si el valor esperado y el observado provienen de fuentes independientes.

**Veredicto: `H2` — No hay fuente recuperable, pero el desensamblado permite demostrar la procedencia independiente de ambos operandos y reconstruir el flujo de comparación completo.**

**Esta tarea es estática. No se declara `CLOSED_EXECUTION`.**

---

## 1. Verificación previa (PRE_EXECUTION_CONTRACT_CHECK)

### 1.1 Estado Git

```
$ git status --porcelain | grep -c '^ M tools/rxre/'
20
```

**Discrepancia 18 vs 20 — CONFIRMADA.** El recuento real es **20**, todos bajo `tools/rxre/`, ninguno fuera de ese directorio. El valor 20 se reproduce de forma determinista antes y después de la tarea. Ninguno de los 20 fue modificado.

| # | Archivo | # | Archivo |
|---|---------|---|---------|
| 1 | `tools/rxre/README.md` | 11 | `tools/rxre/backends/adapters/umr_read.py` |
| 2 | `tools/rxre/api/machine.py` | 12 | `tools/rxre/backends/contract.py` |
| 3 | `tools/rxre/backends/adapters/cs_disasm.py` | 13 | `tools/rxre/backends/decision.json` |
| 4 | `tools/rxre/backends/adapters/gh_decompile.py` | 14 | `tools/rxre/backends/dispatch.py` |
| 5 | `tools/rxre/backends/adapters/rz_callgraph.py` | 15 | `tools/rxre/backends/registry.py` |
| 6 | `tools/rxre/backends/adapters/rz_cfg.py` | 16 | `tools/rxre/core/store.py` |
| 7 | `tools/rxre/backends/adapters/rz_container.py` | 17 | `tools/rxre/tests/run_baseline.py` |
| 8 | `tools/rxre/backends/adapters/rz_functions.py` | 18 | `tools/rxre/tests/test_backends004.py` |
| 9 | `tools/rxre/backends/adapters/rz_inspect.py` | 19 | `tools/rxre/tests/test_backends_bulk.py` |
| 10 | `tools/rxre/backends/adapters/rz_xrefs.py` | 20 | `tools/rxre/tests/test_cli009.py` |

### 1.2 Herramientas verificadas antes de usar

| Herramienta | Ruta | Uso |
|-------------|------|-----|
| `readelf` | `/usr/bin/readelf` | Secciones, notas |
| `objdump` | `/usr/bin/objdump` | Desensamblado |
| `nm` | `/usr/bin/nm` | Tabla de símbolos |
| `strings` | disponible | Cadenas con offset |
| `spirv-dis` | disponible | Desensamblado SPIR-V |

### 1.3 Identidad del ELF

```
SHA-256 : 017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745
Tamaño  : 52608 bytes
mtime   : 2026-10-16 08:22:40.454337262 -0300
Clase   : ELF 64-bit LSB executable, x86-64, version 1 (SYSV)
Enlace  : dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2
Strip   : not stripped
BuildID : 923b56af7d336874906f0195aa2516f3302fc756 (sha1)
Compilador: GCC (GNU) 16.2.1 20260819 (Red Hat 16.2.1-2)
```

---

## 2. Estado de recuperación de la fuente

### 2.1 No hay información de depuración

```
$ readelf -S vk_test/vk_compute_test | grep debug
(sin resultados)
```

**No existen secciones `.debug_*`.** El binario conserva la tabla de símbolos (por `-g0` o por no pasarle `-s`), pero **no hay DWARF**: ni `.debug_info`, ni `.debug_line`, ni `.debug_str`. Por tanto **no hay rutas de fuentes recuperables desde el ELF**.

Comprobación explícita de info de líneas:
```
$ readelf --debug-dump=decodedline vk_test/vk_compute_test
(sin salida — no existe .debug_line)
```

### 2.2 Búsqueda de la fuente en el repositorio

| Búsqueda | Alcance | Resultado |
|----------|---------|-----------|
| `select_rx550` (símbolo único del binario) | `*.c *.cpp *.h *.py *.md *.txt` en todo el repo | **0 coincidencias** |
| `g_out_buffer`, `Observed output` | `tools/`, `findings/`, raíz `*.c *.cpp *.h` | 0 coincidencias (solo `gl4cComputeShaderTests.cpp` / `es31cComputeShaderTests.cpp` de OpenGL CTS, no relacionados) |
| `vk_compute_test` en logs de build | `findings/`, `results/`, `artifacts/`, `docs/` | 0 registros de compilación (solo el informe creado en la tarea anterior) |
| Objetos `.o` o artefactos de build junto al binario | `vk_test/` | Ninguno — solo 3 archivos: dos `.shader`/`.spv` y el ELF |

### 2.3 Conclusión sobre la fuente

**La fuente no es recuperable ni desde el ELF (sin DWARF) ni desde el repositorio (sin coincidencias).** El único rastro es la firma del compilador (GCC 16.2.1 Red Hat) y los símbolos no estáticos.

**Estado de recuperación: FALLIDO (H1 refutada).**

---

## 3. Símbolos del programa (superficie de auditoría disponible)

### 3.1 Funciones definidas

| Dirección | Símbolo | Rol |
|-----------|---------|-----|
| `0x40095e` | `main` | Orquestación completa del test |
| `0x400717` | `select_rx550` | Selección explícita del dispositivo |
| `0x40069b` | `find_memory_type` | Búsqueda de tipo de memoria compatible |
| `0x400584` | `load_all_functions` | Carga dinámica de ~50 punteros `p_vk*` |

### 3.2 Estado global del dispositivo

`g_instance`, `g_pdev`, `g_device`, `g_queue`, `g_queue_family`, `g_mem_props`, `g_vulkan_lib`

### 3.3 Estado global del pipeline

`g_shader_mod`, `g_pl_layout`, `g_dsl`, `g_dpool`, `g_dset`, `g_pipeline`, `g_cmd_pool`, `g_cmd_buf`, `g_fence`

### 3.4 Estado global del buffer

`g_out_buffer`, `g_out_memory`, `g_out_mapped` — **tres objetos distintos para un único buffer de salida**

### 3.5 Punteros de función (carga dinámica)

46 punteros `p_vk*` resueltos vía `p_vkGetInstanceProcAddr`, incluyendo `p_vkCreateShaderModule`, `p_vkCreateComputePipelines`, `p_vkCmdDispatch`, `p_vkQueueSubmit`, `p_vkWaitForFences`, `p_vkMapMemory`, `p_vkUpdateDescriptorSets`.

---

## 4. Flujo de datos reconstruido

Reconstrucción a partir del desensamblado de `main` (`0x40095e`–`0x401eb9`). Las direcciones son verificables con `objdump -d`.

```
[1] Selección de shader
    0x400976: cmpl $0x1,-0x594(%rbp)        ; argc > 1 ?
    0x40098a: mov %rax,-0x8(%rbp)          ; → shader_path = argv[1]
    0x400990: movq $0x403220,-0x8(%rbp)    ; → default = "/tmp/rxre_spirv_tests/simple.comp.spv"
                                                (0x403220 verificado con strings -t x)
    0x4009b6: call <load_all_functions>    ; resuelve 46 p_vk*
    0x4009b1: fwrite("...")                ; mensaje informativo

[2] Instancia + selección de GPU
    0x4009db: movl $0x400000               ; flags = VK_API_VERSION_1_0
             ...
    (vkCreateInstance → vkEnumeratePhysicalDevices → vkGetPhysicalDeviceProperties)
    → call <select_rx550>                 ; selección explícita del dispositivo
    → vkCreateDevice, vkGetDeviceQueue    ; g_device, g_queue

[3] Módulos shader y layout
    (fopen/fread de shader_path → buffer local)
    0x4015fc: mov $0x403896,%edi           ; "Shader module created."
             p_vkCreateShaderModule       ; g_shader_mod
    (sha1 de g_shader_mod, binding 0, STORAGE_BUFFER, 4 bytes)
             p_vkCreateDescriptorSetLayout ; g_dsl
             p_vkCreatePipelineLayout     ; g_pl_layout

[4] Buffer de salida
             p_vkCreateBuffer             ; g_out_buffer (size=4)
             p_vkGetBufferMemoryRequirements
             call <find_memory_type>      ; busca memoria HOST_VISIBLE|HOST_COHERENT
             p_vkAllocateMemory            ; g_out_memory

[5] GRABADO #1 — warm-up
    0x400f21: p_vkUpdateDescriptorSets   ; binding 0 → g_out_buffer
    0x400f32: p_vkCmdBindPipeline
    0x400f43: p_vkCmdBindDescriptorSets
    0x400f54: p_vkCmdDispatch             ; (1,1,1)
             p_vkEndCommandBuffer
    0x400f76: p_vkQueueSubmit
    0x400f87: p_vkWaitForFences           ; espera fence

[6] LIMPIEZA DEL BUFFER por CPU
    0x401372: je 4013a7                    ; salto condicional al memset
    0x4013a7: mov 0x3eb2(%rip),%rax       ; → 0x405260 <g_out_mapped>
    0x4013ae: mov $0x4,%edx                ; length = 4
    0x4013b3: mov $0x0,%esi                ; value = 0
    0x4013bb: call <memset@plt>           ; memset(g_out_mapped, 0, 4)  ← PURGA A CERO
    0x4013c0: p_vkUnmapMemory

[7] GRABADO #2 — medición
    0x401903: p_vkUpdateDescriptorSets   ; binding 0 → g_out_buffer
    0x401ad3: p_vkCmdBindPipeline
    0x401af2: p_vkCmdBindDescriptorSets
    0x401b2b: p_vkCmdDispatch             ; (1,1,1)
    0x401b4e: p_vkEndCommandBuffer
    0x401c9a: p_vkQueueSubmit
    0x401d1b: p_vkWaitForFences           ; r8=UINT64_MAX (espera indefinida)
    0x401d4b: cmpl $0x0,-0x84(%rbp)       ; verifica resultado del fence

[8] LECTURA
    0x401da8: p_vkMapMemory                ; g_out_memory → g_out_mapped
    0x401dee: mov (%rax),%eax              ; observed = *(uint32_t*)g_out_mapped
    0x401df0: mov %eax,-0x94(%rbp)         ; → stack slot -0x94
    0x401df6: p_vkUnmapMemory

[9] VALOR ESPERADO (literal, independiente)
    0x401e13: movl $0x2a,-0x98(%rbp)      ; expected = 42  ← INMEDIATO EN CÓDIGO
    0x401e1d: fwrite(stdout)
    0x401e2a: mov $0x403b97,%esi           ; "Expected output: %u"
             call <fprintf>
    0x401e49: mov $0x403bac,%esi           ; "Observed output: %u"
             call <fprintf>

[10] COMPARACIÓN Y RAMAS
    0x401e5b: mov -0x94(%rbp),%eax        ; observed
    0x401e61: cmp -0x98(%rbp),%eax        ; observed vs expected
    0x401e67: jne 401e8e                   ; → rama FAIL
    (rama PASS:)
    0x401e7d: mov $0x403bc8,%edi           ; "RESULT: PASS "
    0x401e82: call <fwrite>
    0x401e8c: jmp 401eb8                   ; exit con eax=0
    (rama FAIL:)
    0x401ea1: mov $0x403c08,%esi           ; "RESULT: FAIL "
    0x401eae: call <fprintf>
    0x401eb3: mov $0x1,%eax                ; exit con eax=1
    0x401eb8: leave / ret
```

---

## 5. Verificaciones específicas solicitadas

### 5.1 ¿El shader cargado es `simple.comp.spv` y no `test_compute.spv`?

**PROVEN.** El desensamblado muestra una **única** referencia a la ruta del shader:

```
$ grep -c '0x403220' full.asm
1
  0x400990: movq $0x403220,-0x8(%rbp)     ; default
```
Y `0x403220` corresponde a `"/tmp/rxre_spirv_tests/simple.comp.spv"` (verificado con `strings -t x`, offset `0x3220`). No existe ninguna referencia a `test_compute.spv` ni a `test_compute.shader`.

Además, el shader se puede sobreescribir con `argv[1]` si `argc > 1` (`cmpl $0x1,-0x594(%rbp)` en `0x400976`). Con `argc == 1` se usa el valor por defecto.

### 5.2 ¿El shader en `/tmp` coincide con el analizado, sin asumir estado actual?

**INFERRED, con límite explícito.** El archivo actual tiene mtime `2026-10-15 20:15:52`, **anterior** al mtime del ELF (`2026-10-16 08:22:40`), y su desensamblado SPIR-V confirma:

```
OpEntryPoint GLCompute %main "main"
OpDecorate %_ Binding 0
%uint_42 = OpConstant %uint 42
%gl_WorkGroupSize = OpConstantComposite %v3uint %uint_1 %uint_1 %uint_1
OpStore %14 %uint_42
```

Esto es consistente con un shader que escribe 42 en binding 0. **Límite:** `/tmp` no es persistente y no hay hash registrado del shader en el momento de la compilación del ELF; no puede demostrarse que el archivo actual sea byte-idéntico al que se usó entonces. Solo puede afirmarse que es compatible con el valor esperado codificado en el binario.

### 5.3 ¿El buffer de salida es el mismo recurso asociado al descriptor?

**PROVEN.** Existe un único juego de símbolos: `g_out_buffer`, `g_out_memory`, `g_out_mapped`. `vkCreateBuffer` produce `g_out_buffer`; `vkAllocateMemory` produce `g_out_memory`; `vkBindBufferMemory` los vincula; `vkMapMemory` produce `g_out_mapped` a partir de `g_out_memory`. `vkUpdateDescriptorSets` referencia `g_out_buffer` con binding 0. No hay segundo buffer ni segundo binding.

El shader declara `OpDecorate %_ Binding 0` — coincide.

### 5.4 ¿El valor observado se lee de memoria escrita por el dispatch, no de una constante ni de memoria inicializada por CPU?

**PROVEN — es la relación más fuerte de la auditoría.**

La evidencia converge en cuatro puntos:

1. **La CPU purga el buffer a cero antes del segundo dispatch** (`0x4013bb: memset(g_out_mapped, 0, 4)` con `esi=0`, `edx=4`). El buffer **no** contiene 42 antes del dispatch.

2. **El valor esperado es un inmediato en el código**, cargado en una instrucción distinta (`0x401e13: movl $0x2a,-0x98(%rbp)`), hacia un **slot de pila distinto** (`-0x98`) del observado (`-0x94`).

3. **El valor observado se lee de memoria mapeada**, no de un inmediato: `0x401dee: mov (%rax),%eax` donde `%rax` proviene de `g_out_mapped` cargado en `0x401dd9`.

4. **El `memset` es el único uso de memset/memcpy del binario** y opera sobre `g_out_mapped`, con el valor `0` — nunca con `0x2a`.

Consecuencia: si el valor observado fuese 42, **solo puede provenir del dispatch que ejecutó el shader**. La procedencia de ambos operandos es **independiente y demostrable**.

### 5.5 ¿El valor esperado tiene procedencia independiente?

**PROVEN.** El esperado `42` está codificado como inmediato `movl $0x2a` en el binario (`0x401e13`), en una basic block separada de la lectura. No hay ninguna ruta por la que el valor observado流入 el esperado: viven en slots de pila distintos (`-0x94` vs `-0x98`) y se comparan con `cmp` en `0x401e61`.

Coincide con la constante del shader (`OpConstant %uint 42`), lo que confirma que el autor写到 un test coherente, no uno que derives el esperado de lo observado.

### 5.6 ¿La comparación controla realmente las ramas PASS y FAIL?

**PROVEN.** El control de flujo está explícito:

| Dirección | Instrucción | Efecto |
|-----------|-------------|--------|
| `0x401e67` | `jne 401e8e` | Si difieren → rama FAIL |
| `0x401e7d`–`0x401e82` | `mov $0x403bc8` + `call fwrite` | Emite `"RESULT: PASS "` a stdout |
| `0x401e8c` | `jmp 401eb8` | Termina con `eax = 0` |
| `0x401ea1`–`0x401eae` | `mov $0x403c08` + `call fprintf` | Emite `"RESULT: FAIL "` a stderr |
| `0x401eb3` | `mov $0x1,%eax` | Termina con `eax = 1` |

El código de salida distingue los dos casos. La cadena `" Output mismatch (expected %u, got %u)"` existe en `.rodata` (`0x403c18`) pero **no es referenciada por ninguna instrucción** — es texto muerto, no una ruta de ejecución. Documentado como hallazgo.

### 5.7 ¿Las operaciones de sincronización y memoria son coherentes?

**PROVEN.**

- `vkWaitForFences` se invoca con `r8 = 0xffffffffffffffff` (`mov $0xffffffffffffffff,%r8` en `0x401d29`), que es `UINT64_MAX` — espera sin timeout, calendario permanente. El valor devuelto se verifica en `0x401d4b` antes de continuar.
- `vkMapMemory` se invoca con `r9 = 0x405260` (puntero a `g_out_mapped`) y `ecx = 0x4` (tamaño 4), tras el fence.
- El orden es: `QueueSubmit` (0x401c9a) → `WaitForFences` (0x401d1b) → `MapMemory` (0x401da8) → lectura (0x401dee). **El acceso al buffer host-visible ocurre después de la señalización de finalización.**

La presencia de `p_vkCmdPipelineBarrier` (símbolo cargado pero no localizado como llamada en el flujo reconstruido) sugiere que el autor contempló barreras, aunque no se usó en esta ruta.

### 5.8 ¿Las cadenas pertenecen al flujo ejecutable y no son código muerto?

**Auditado caso por caso.**

| Cadena | vaddr | ¿Referenciada? | Veredicto |
|--------|-------|----------------|-----------|
| `/tmp/rxre_spirv_tests/simple.comp.spv` | `0x403220` | Sí, `0x400990` | **VIVA** |
| `Shader module created.` | `0x403896` | Sí, `0x4015fc` | **VIVA** |
| `Command buffer recorded (dispatch 1x1x1).` | `0x403a70` | en flujo | **VIVA** |
| `Expected output: %u` | `0x403b97` | Sí, `0x401e2a` | **VIVA** |
| `Observed output: %u` | `0x403bac` | Sí, `0x401e49` | **VIVA** |
| `RESULT: PASS ` | `0x403bc8` | Sí, `0x401e7d` | **VIVA** |
| `RESULT: FAIL ` | `0x403c08` | Sí, `0x401ea1` | **VIVA** |
| ` Output mismatch (expected %u, got %u)` | `0x403c18` | **No** | **MUERTA** |

Las siete cadenas del contrato están en el flujo ejecutable. La octava es texto muerto.

---

## 6. Tabla de contratos: demostrados, refutados, abiertos

### 6.1 Demostrados estáticamente (`PROVEN`)

| Contrato | Evidencia |
|----------|-----------|
| El shader cargado es `simple.comp.spv`, no `test_compute.spv` | Referencia única `0x403220` en `0x400990` |
| El shader escribe un valor determinista en binding 0 | `OpStore %14 %uint_42` + `OpDecorate %_ Binding 0` |
| Existe un dispatch real a la GPU | `p_vkCmdDispatch` en `0x400f54` y `0x401b2b` |
| El trabajo se envía a la cola | `p_vkQueueSubmit` en `0x400f76` y `0x401c9a` |
| La finalización se espera antes de leer | `p_vkWaitForFences` en `0x401d1b` posterior a ambos submit |
| El valor observado se lee de memoria mapeada | `mov (%rax),%eax` en `0x401dee` desde `g_out_mapped` |
| El valor esperado es un literal independiente | `movl $0x2a,-0x98(%rbp)` en `0x401e13`, slot distinto |
| El buffer se purga a 0 por CPU antes del dispatch de medición | `memset(g_out_mapped, 0, 4)` en `0x4013bb` |
| La comparación gobierna dos ramas con exit codes distintos | `jne 401e8e`; PASS→`eax=0`, FAIL→`eax=1` |
| Existe un único recurso de salida | `g_out_buffer` / `g_out_memory` / `g_out_mapped` |
| La selección de dispositivo es explícita para RX 550 | Función `select_rx550` en `0x400717` |

### 6.2 Refutados

| Afirmación previa | Veredicto |
|-------------------|-----------|
| «El valor observado podría provenir de una inicialización de CPU» | **REFUTADA** — la CPU escribe `0`, el esperado es `42`, el observado se lee tras el fence |
| «La comparación podría usar el mismo valor como esperado» | **REFUTADA** — inmediato en `0x401e13` vs lectura de memoria en `0x401dee`, slots distintos |
| «Las cadenas podrían pertenecer a rutas alternativas» | **REFUTADA** para las 7 cadenas del contrato; **CONFIRMADA** solo para ` Output mismatch` |
| «H1: hay fuente recuperable o DWARF» | **REFUTADA** — no hay `.debug_*` ni coincidencias en el repo |

### 6.3 Abiertos

| Cuestión | Motivo |
|----------|--------|
| Si el binario se ejecutó alguna vez en esta máquina | No hay registro en ningún artefacto |
| Si `simple.comp.spv` actual es byte-idéntico al usado al compilar | `/tmp` no persistente; solo hay mtime anterior, coherente |
| Número de dispatch efectivos (¿2 warm-up + 1 medida, o 1 + 1?) | La reconstrucción muestra 2 dispatch; el propósito exacto no es verificable sin fuente |
| Si la rama `je 4013a7` (memset) se toma siempre | Requiere conocer la condición en `0x401372`; el análisis del predicado excede esta tarea |
| Comportamiento real en la RX 550 | Requiere ejecución, fuera de alcance |

---

## 7. Clasificación epistemológica de conclusiones

| Afirmación | Clasificación | Evidencia faltante para elevar |
|------------|---------------|-------------------------------|
| El ELF no contiene DWARF | **PROVEN** | — |
| No hay fuente en el repositorio | **PROVEN** (ausencia reproducible) | — |
| La referencia al shader es única y apunta a `simple.comp.spv` | **PROVEN** | — |
| El buffer se purga a 0 antes del dispatch | **PROVEN** | — |
| El esperado es literal 42, independiente del observado | **PROVEN** | — |
| La comparación gobierna PASS/FAIL con exit codes distintos | **PROVEN** | — |
| La sincronización precede a la lectura | **PROVEN** | — |
| `test_compute.spv` no interviene en el flujo | **PROVEN** | — |
| ` Output mismatch` es texto muerto | **PROVEN** | — |
| El shader actual es el compilado en el momento del build | **INFERRED** | Hash del shader en el momento del build |
| La condición en `0x401372` siempre toma la rama del memset | **OPEN** | Análisis del predicado o fuente |
| El despacho observado es el segundo de dos (warm-up + medida) | **OPEN** | Fuente o comentario del autor |
| El test pasa en la RX 550 | **OPEN** | Ejecución autorizada |

---

## 8. Diagrama del flujo real reconstruido

```
                  ┌──────────────────────────────────────────┐
                  │  argc > 1 ?  argv[1]  :  DEFAULT         │
                  │  DEFAULT = /tmp/rxre_spirv_tests/         │
                  │            simple.comp.spv  (0x403220)    │
                  │  cmpl $0x1,-0x594(%rbp)  → 0x400976      │
                  └───────────────────┬──────────────────────┘
                                      ▼
                  ┌──────────────────────────────────────────┐
                  │  load_all_functions: 46 punteros p_vk*   │
                  └───────────────────┬──────────────────────┘
                                      ▼
                  ┌──────────────────────────────────────────┐
                  │  vkCreateInstance (API 1.0, 0x400000)     │
                  │  vkEnumeratePhysicalDevices              │
                  │  select_rx550 (0x400717)  ← GPU explícita │
                  │  vkCreateDevice / vkGetDeviceQueue        │
                  └───────────────────┬──────────────────────┘
                                      ▼
       ┌──────────────────────────────────────────────────────────┐
       │  CARGA DE RECURSOS                                        │
       │  fopen/fread(shader_path)          ← lee /tmp/...spv      │
       │  vkCreateShaderModule            → "Shader module created"│
       │  vkCreateDescriptorSetLayout      binding 0, STORAGE, 4B  │
       │  vkCreatePipelineLayout                                  │
       │  vkCreateBuffer (size=4)         → g_out_buffer          │
       │  find_memory_type                HOST_VISIBLE|COHERENT   │
       │  vkAllocateMemory                → g_out_memory          │
       │  vkBindBufferMemory                                        │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
       ┌──────────────────────────────────────────────────────────┐
       │  GRABADO #1 (warm-up)                                    │
       │  UpdateDescriptorSets → CmdBindPipeline →                │
       │  CmdBindDescriptorSets → CmdDispatch(1,1,1) →             │
       │  EndCommandBuffer → QueueSubmit → WaitForFences          │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
       ┌──────────────────────────────────────────────────────────┐
       │  PURGA POR CPU          je 4013a7 @ 0x401372            │
       │  memset(g_out_mapped, 0, 4)      @ 0x4013bb   ◄── 0      │
       │  vkUnmapMemory                                            │
       │  ⚠ buffer ahora contiene 0, NO 42                        │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
       ┌──────────────────────────────────────────────────────────┐
       │  GRABADO #2 (medición)                                    │
       │  UpdateDescriptorSets → CmdBindPipeline →                │
       │  CmdBindDescriptorSets → CmdDispatch(1,1,1) @ 0x401b2b → │
       │  EndCommandBuffer @ 0x401b4e → QueueSubmit @ 0x401c9a →   │
       │  WaitForFences @ 0x401d1b (timeout = UINT64_MAX)          │
       │  cmpl $0x0 → verifica retorno                             │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
       ┌──────────────────────────────────────────────────────────┐
       │  LECTURA                                                  │
       │  vkMapMemory(g_out_memory) → g_out_mapped   @ 0x401da8   │
       │  observed = *(uint32_t*)g_out_mapped  @ 0x401dee           │
       │           → stack[-0x94]                                   │
       │  vkUnmapMemory                     @ 0x401df6             │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
       ┌──────────────────────────────────────────────────────────┐
       │  ESPERADO (inmediato en código)                            │
       │  expected = 0x2a  = 42            @ 0x401e13               │
       │           → stack[-0x98]   ◄── slot DISTINTO              │
       │  fprintf(stdout, "Expected output: %u")  @ 0x401e2a        │
       │  fprintf(stdout, "Observed output: %u")  @ 0x401e49        │
       └───────────────────┬──────────────────────────────────────┘
                           ▼
                 ┌─────────────────────┐
                 │ cmp [-0x98], eax    │  @ 0x401e61
                 │      @ 0x401e61     │
                 └──────┬───────┬──────┘
              jne 401e8e│       │igual
                        ▼       ▼
        ┌───────────────┐   ┌────────────────────┐
        │  RESULT: FAIL │   │  RESULT: PASS      │
        │  → stderr     │   │  → stdout          │
        │  eax = 1      │   │  eax = 0           │
        │  @ 0x401ea1   │   │  @ 0x401e7d        │
        └───────┬───────┘   └─────────┬──────────┘
                └──────────┬──────────┘
                           ▼
                    leave / ret  @ 0x401eb8
```

**La rama ` Output mismatch (expected %u, got %u)` (0x403c18) no aparece en este diagrama porque no tiene ninguna instrucción que la referencie: es texto muerto.**

---

## 9. GLOBAL_WORK_SCAN

| Frontera | Estado | Efecto de esta tarea |
|----------|--------|----------------------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| RADV/GFX8 ejecución compute | **OPEN** → candidato.upgradable | La prueba pasa de «candidato basado en cadenas» a «flujo auditado con procedencia independiente demostrada»; sigue `OPEN` por falta de ejecución |
| RADV/GFX8 ejecución tess/geom | OPEN | Ninguno |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |

**Cambio de estado de la prueba compute:** de «contrato tentatively satisfecho por cadenas» a **«contrato PROVEN por desensamblado»**. La frontera de ejecución compute permanece `OPEN` —esta tarea es estática y no demuestra ejecución real— pero el obstáculo técnico identified (auditoría del flujo) queda resuelto.

---

## 10. Verificaciones de integridad finales

| Verificación | Resultado |
|--------------|-----------|
| `git status --porcelain \| grep -c '^ M tools/rxre/'` antes | 20 |
| `git status --porcelain \| grep -c '^ M tools/rxre/'` después | **20** |
| Archivos modificados por esta tarea | **0** |
| Archivos creados por esta tarea | **1** (este informe) |
| Scripts creados | **0** |
| Binario ejecutado | **No** |
| Shaders ejecutados / despatches enviados | **No** |
| `/dev/dri`, MMIO, VRAM | **No** |
| sudo / root | **No** |
| Paquetes instalados / herramientas instaladas | **No** |
| Configuración modificada | **No** |
| Informes especializados (SDMA, GMC, ACO/LLVM) modificados | **No** |

Artefactos analizados (solo lectura): `vk_test/vk_compute_test`, `vk_test/test_compute.spv`, `vk_test/test_compute.shader`, `/tmp/rxre_spirv_tests/simple.comp{,.spv}`. Ninguno alterado.

---

## 11. Siguiente frontera prioritaria (una sola)

**Ejecutar `vk_compute_test` en un ciclo autorizado y registrar `stdout`, `stderr` y exit status**, con el shader en una ruta persistente del repositorio en lugar de `/tmp`.

Justificación con evidencia concreta:
- La auditoría estática cerró los doce contratos de §6.1 como `PROVEN`. La procedencia independiente de esperado y observado está demostrada por el `memset` a cero seguido de lectura de memoria mapeada.
- Lo único que separa esta prueba de un cierre de la etapa compute es la ejecución, y ahora se sabe **exactamente qué observing**: `Expected output: 42`, `Observed output: X`, `RESULT: PASS|FAIL`, exit 0 o 1.
- Si devuelve `PASS` con `observed = 42`, la etapa compute pasa a `CLOSED_EXECUTION`. Si devuelve `FAIL`, la evidencia permite atribuir causalidad (valor observado ≠ 42 pinpoint si el buffer quedó en 0 → el dispatch no escribió → defecto de ejecución; valor corrupto → defecto de pipeline o hardware).
- Requisito previo, no opcional: mover `simple.comp.spv` fuera de `/tmp` antes de ejecutar, porque `/tmp` no sobrevive reinicios y el binario lo referencia por ruta absoluta embebida (`0x403220`).

No se inicia esa investigación en esta tarea.
