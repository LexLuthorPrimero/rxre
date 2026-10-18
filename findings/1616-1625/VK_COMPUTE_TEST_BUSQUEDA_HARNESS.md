# RXRE — Búsqueda de harness Vulkan reutilizable sin modificar el binario

**Misión:** Encontrar una vía ya existente en RXRE para ejecutar una prueba compute Vulkan verificable sin modificar `vk_test/vk_compute_test`, sin escribir código nuevo y sin iniciar otra prueba de GPU.

**Veredicto: `H3` — No hay una vía reutilizable dentro del alcance autorizado.**

**Esta tarea es de inspección estática. No se ejecutó ningún harness ni se envió ningún dispatch. No se declara `CLOSED_EXECUTION`.**

Informe de ejecución (actualizado con la corrección de causa raíz): `findings/1616-1625/VK_COMPUTE_TEST_PREPARACION_EJECUCION.md`

---

## 1. Verificación de procedencia y estado previo

### 1.1 Estado Git

```
$ git status --porcelain | grep -c '^ M tools/rxre/'
20
```

**Los 20 archivos modificados preexistentes siguen intactos.** Ninguno fue tocado en esta tarea. Verificación reproducida antes y después.

### 1.2 Corrección de causa raíz aplicada al informe de ejecución

La tarea anterior atribuyó el fallo a que el binario resolviera `vkCreateInstance` con `g_instance == NULL`. **Esa atribución era errónea** y quedó corregida en `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` §5.3-bis.

Resumen de la corrección:

| | Atribución errónea (retirada) | Atribución correcta (vigente) |
|---|---|---|
| `vkCreateInstance` con `g_instance == NULL` | Causa del fallo | **Comportamiento correcto** (comando global); se resolvió con éxito |
| Función que realmente falló | — | `vkEnumeratePhysicalDevices`, comando de instancia |
| Defecto real | — | `load_all_functions` agrupa comandos globales y de instancia en un único lote previo a crear la instancia |

---

## 2. TIERRA — Verificación revisada de la causa raíz

### 2.1 ¿La resolución de `vkCreateInstance` con instancia nula es un defecto?

**No.** Verificación por desensamblado:

```asm
400626: call 400526 <load_func>      ; load_func("vkCreateInstance")
40062b: mov  %rax,0x4ab6(%rip)       ; p_vkCreateInstance ← RETORNÓ NO-NULL
400637: call 400526 <load_func>      ; load_func("vkEnumeratePhysicalDevices")
```

El hecho de que `p_vkCreateInstance` se asigne en `0x40062b` **y** de que el flujo continúe hasta `0x400637` es prueba directa de que la primera resolución devolvió un puntero válido. Si `vkCreateInstance` hubiera fallado, `load_func` (`0x400550`–`0x400579`) habría ejecutado `exit(1)` sin alcanzar la segunda llamada.

**Clasificación: `REFUTED`** — el uso de `vkGetInstanceProcAddr(NULL, "vkCreateInstance")` es el mecanismo Vulkan especificado para comandos globales y funcionó.

### 2.2 Valor de retorno del resolver

`load_func` (`0x400526`–`0x400583`) implementa exactamente este contrato:

```asm
40054a: call *%rcx                    ; vkGetInstanceProcAddr(g_instance, name)
40054c: mov  %rax,-0x8(%rbp)
400550: cmpq $0x0,-0x8(%rbp)          ; ¿NULL?
400555: jne 40057e                    ; no → retorna puntero
400562: mov  $0x402f68,%esi           ; "Failed to load Vulkan function: %s"
40056f: call *<fprintf@plt>           ; escribe nombre de la función
400574: mov  $0x1,%edi
400579: call *<exit@plt>              ; exit(1)
```

**No hay tolerancia a `NULL`**: cualquier función no resuelta aborta el proceso. **Clasificación: `PROVEN`.**

### 2.3 Asignación efectiva de `p_vkCreateInstance`

| Dirección | Contenido |
|-----------|-----------|
| `0x40062b` | `mov %rax,0x4ab6(%rip)` → `0x4050e8 <p_vkCreateInstance>` |

El puntero quedó asignado. **Clasificación: `PROVEN`.**

### 2.4 Función cuya resolución falla realmente

Orden real de las 7 llamadas, resuelto contra `strings -t x`:

| # | Nombre | Tipo de comando Vulkan | `g_instance` | Resultado |
|---|--------|------------------------|--------------|-----------|
| 1 | `vkCreateInstance` | **global** | `NULL` | **RESUELTO** |
| 2 | `vkEnumeratePhysicalDevices` | **de instancia** | `NULL` | **FALLA → `exit(1)`** |
| 3 | `vkGetPhysicalDeviceProperties` | de instancia | — | no alcanzado |
| 4 | `vkGetPhysicalDeviceQueueFamilyProperties` | de instancia | — | no alcanzado |
| 5 | `vkGetPhysicalDeviceMemoryProperties` | de instancia | — | no alcanzado |
| 6 | `vkGetPhysicalDeviceFeatures` | de instancia | — | no alcanzado |
| 7 | `vkDestroyInstance` | de instancia | — | no alcanzado |

**Clasificación: `PROVEN`** — el orden se lee directamente del desensamblado (`0x400626`–`0x40068c`) y los nombres se resuelven contra la tabla de cadenas en `.rodata`.

### 2.5 Condición exacta que conduce a `exit(1)`

`cmpq $0x0,-0x8(%rbp)` en `0x400550` → si el puntero devuelto es `NULL` → mensaje a stderr → `exit(1)` en `0x400579`. El mensaje capturado fue `Failed to load Vulkan function: vkEnumeratePhysicalDevices`.

**Clasificación: `PROVEN`** — coincide exactamente con la salida registrada en `ejecucion_compute_20261016/stderr.txt`.

### 2.6 Refutación de la atribución anterior

| Afirmación anterior | Estado |
|---------------------|--------|
| «El fallo se debe a resolver `vkCreateInstance` con instancia nula» | **`REFUTED`** por el desensamblado (`0x40062b`–`0x400637`) y por el comportamiento especificado de Vulkan |
| «La resolución de `vkCreateInstance` con una instancia nula es el mecanismo Vulkan esperado para un comando global. No atribuir el fallo a ese argumento sin demostrar un defecto concreto» | **CUMPLIDA** — verificado que se resuelve correctamente y que el defecto está en otro lugar |

---

## 3. CUERPO — Candidatos inspeccionados

### 3.1 Adaptadores registrados en RXRE

Fuente de verdad: `tools/rxre/backends/registry.py`.

```
$ grep -oE '"[a-z_]+\.[a-z_]+"' tools/rxre/backends/registry.py | sort -u
binary.basic_blocks          binary.functions           rxre.create_finding
binary.callgraph             binary.imports             rxre.create_finding_relation
binary.cfg                   binary.inspect             rxre.evaluate_applicability
binary.dataflow              binary.sections            rxre.get_finding
binary.decompile             binary.strings             rxre.list_finding_relations
binary.disassemble           binary.symbols             rxre.list_findings
binary.disassemble_func       binary.xrefs               rxre.plan_investigation
binary.exports               decision.json              rxre.search_findings
gpu.register_read            rea.inspect_firmware       source.ast_parse
gpu.register_read            source.semantic_search
```

**Único adaptador con acceso a hardware: `gpu.register_read`.**

### 3.2 Contratos de `gpu.register_read`

Fichero: `tools/rxre/backends/adapters/umr_read.py`. Documentado en `dispatch.py:362`.

| Contrato | ¿Lo satisface? | Evidencia |
|----------|----------------|-----------|
| Inicializa Vulkan | **NO** | Invoca el binario externo `umr -r <regname>`; no contiene `vkCreateInstance` |
| Resuelve `vkGetInstanceProcAddr` | **NO** | Sin coincidencia en `api/`, `backends/adapters/`, `core/`, `storage/`, `knowledge_ingestion/`, `tests/` |
| Crea un compute pipeline | **NO** | Alcance exclusivo: lectura de registros MMIO |
| Emite un dispatch | **NO** | Idem |
| Lee y compara un resultado | **NO** | Verifica formato hex de stdout, no aritmética |
| Selección de dispositivo por PCI | **SÍ** | Allow-list `0000:01:00.0`, validación de `asic.ip.regname` |
| Requisito de privilegios | root | `geteuid()==0`, escaladaDeclarada, no automatizada |

**Conclusión del candidato: no es reutilizable para compute.** Es un adaptador de lectura de registros, no un harness de ejecución.

### 3.3 Búsqueda de inicialización Vulkan en `tools/rxre/`

```
$ for d in api backends/adapters core storage knowledge_ingestion tests; do
    grep -rlE 'vkCreateInstance|VkInstanceCreateInfo|vkGetInstanceProcAddr' "tools/rxre/$d"
  done
  api:                     (sin coincidencias)
  backends/adapters:       (sin coincidencias)
  core:                    (sin coincidencias)
  storage:                 (sin coincidencias)
  knowledge_ingestion:     (sin coincidencias)
  tests:                   (sin coincidencias)
```

**Ningún componente propio de RXRE inicializa Vulkan.** El subárbol `tools/rxre/github/` se excluyó por ser código de terceros.

### 3.4 Búsqueda de harnesses compute en el repositorio

```
$ for d in vk_test revkit tools benchmark results artifacts 04-IMPLEMENTACION 06-INGENIERIA-INVERSA; do
    find "$d" -maxdepth 3 \( -name '*.c' -o -name '*.cpp' -o -name '*.py' \) | xargs grep -lE 'vkCreateInstance|vkCmdDispatch|vkQueueSubmit'
  done
  vk_test:              (ninguno)
  revkit:               (ninguno)
  tools:                (ninguno)
  benchmark:            (ninguno)
  results:              (ninguno)
  artifacts:            (ninguno)
  04-IMPLEMENTACION:    (ninguno)
  06-INGENIERIA-INVERSA:(ninguno)
```

**Ningún harness compute en el repositorio**, salvo el binario `vk_compute_test` ya auditado (cuyo código fuente no está presente).

### 3.5 Candidato VK-GL-CTS

| Verificación | Resultado |
|--------------|-----------|
| ¿Presente en el repositorio? | **SÍ** — `tools/rxre/github/VK-GL-CTS/` |
| ¿Compilado? | **NO** — sin ejecutables `vk*` |
| ¿`vkcompute` instalado en el sistema? | **NO** — `command -v vkcompute` sin resultado |
| ¿Módulos compute en la fuente? | No localizados a profundidad ≤3 |
| ¿Reutilizable sin recompilar? | **NO** |

**Conclusión del candidato: requiere compilación, prohibida en esta tarea.**

### 3.6 Resumen de candidatos

| Candidato | Ruta | ¿Inicializa Vulkan? | ¿Compute con validación? | ¿Reutilizable sin compilar? |
|-----------|------|---------------------|--------------------------|------------------------------|
| `gpu.register_read` | `tools/rxre/backends/adapters/umr_read.py` | No (delega en UMR) | No | No aplicable |
| `rea.inspect_firmware` | `tools/rxre/backends/adapters/rea_inspect.py` | No | No | No aplicable |
| `vk_compute_test` | `vk_test/vk_compute_test` | **Sí, defectuosa** | Sí, si superara el fallo | **Sí, pero bloqueada** |
| VK-GL-CTS | `tools/rxre/github/VK-GL-CTS/` | Sí (fuente) | Sí (fuente) | No (requiere compilar) |
||vkcube` | `/usr/bin/vkcube` | Sí | No (solo VS+FS) | Sí, pero fuera de alcance |

---

## 4. Veredicto sobre las hipótesis

| Hipótesis | Veredicto | Evidencia |
|-----------|-----------|-----------|
| **H1**: existe un harness reutilizable que inicializa Vulkan correctamente y puede validar compute sin modificar el ELF original | **REFUTADA** | Ningún componente de `tools/rxre/` contiene inicialización Vulkan (§3.3). Ningún harness compute en el repositorio (§3.4). `gpu.register_read` no emite dispatch ni lee resultados aritméticos (§3.2). VK-GL-CTS requiere compilación (§3.5). El único binario con el flujo completo es el bloqueado |
| **H2**: existen componentes reutilizables, pero falta una vía completa | **CONFIRMADA** | Existen piezas: `gpu.register_read` aporta selección de dispositivo por PCI y captura de stdout/stderr/exit status; `/tmp/rxre_spirv_tests/simple.comp.spv` es un SPIR-V compute válido; el flujo de `vk_compute_test` está completamente auditado. Falta el nexo: inicialización Vulkan + pipeline + dispatch + lectura aritmética |
| **H3**: no hay una vía reutilizable dentro del alcance autorizado | **CONFIRMADA** | Combinado de H1 refutada y H2: las piezas existen dispersas pero ninguna satisface el contrato completo sin escribir código |

**Veredicto solicitado: `H3`.**

---

## 5. AGUA — Registro reutilizable

### 5.1 Lección sobre resolución de funciones Vulkan

`vkGetInstanceProcAddr(NULL, name)` devuelve puntero válido **solo** para tres comandos globales: `vkEnumerateInstanceExtensionProperties`, `vkEnumerateInstanceLayerProperties`, `vkCreateInstance`. Cualquier otro comando devuelve `NULL` por diseño. Un harness que agrupe la carga de comandos globales y de instancia en un único lote previo a crear la instancia fallará de forma determinista en la primera función de instancia.

### 5.2 Lección sobre atribución causal

Atribuir un fallo a un argumento aparentemente sospechoso sin verificar el orden real de llamadas lleva a conclusiones erróneas. La evidencia decisiva fue localizar la asignación del puntero entre dos invocaciones consecutivas de `load_func`: eso probó que la primera había tenido éxito y местó el fallo en la segunda.

### 5.3 Componentes reutilizables identificados

| Componente | Ruta | Qué aporta |
|------------|------|-----------|
| Selección de dispositivo por PCI | `tools/rxre/backends/adapters/umr_read.py` | Allow-list `0000:01:00.0`, validación de formato |
| Captura de resultado | `umr_read.py` | stdout/stderr/exit status separados, verificación de formato |
| SPIR-V compute válido | `/tmp/rxre_spirv_tests/simple.comp.spv` | Escribe `42` en binding 0, magic `0x07230203` |
| Flujo de pipeline auditado | `VK_COMPUTE_TEST_AUDITORIA_ESTATICA.md` | Secuencia completa verificada por desensamblado |
| Contrato de registro | `VK_COMPUTE_TEST_PREPARACION_EJECUCION.md` §6 | 11 campos obligatorios por ejecución |

---

## 6. GLOBAL_WORK_SCAN

| Frontera | Estado | Efecto de esta tarea |
|----------|--------|----------------------|
| SDMA v3.1 / UMR | CLOSED_STATIC | Ninguno |
| GMC VM_CONTEXT (gap) | REJECTED | Ninguno |
| RADV/GFX8 ACO-LLVM (backend) | CLOSED_STATIC | Ninguno |
| **RADV/GFX8 ejecución compute** | **`BLOCKED`** — causa raíz corregida y precisa | La atribución errónea fue corregida; el bloqueo permanece |
| RADV/GFX8 ejecución tess/geom | OPEN | Ninguno |
| RADV/GFX8 ejecución vertex/fragment | OBSERVED (vkcube, ruta integrada) | Ninguno |
| RadeonSI error recovery | CLOSED | Ninguno |
| MC firmware 32/64 | PROVEN / OPEN (runtime) | Ninguno |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | Ninguno |

**No se reabrió ninguna frontera cerrada.** No se ejecutó ningún harness ni se enviaron dispatches.

---

## 7. Verificaciones de integridad finales

| Verificación | Resultado |
|--------------|-----------|
| `git status --porcelain \| grep -c '^ M tools/rxre/'` | **20** (idéntico) |
| Archivos modificados por esta tarea | **1** (`VK_COMPUTE_TEST_PREPARACION_EJECUCION.md`, corrección de causa raíz) |
| Archivos creados por esta tarea | **1** (este informe) |
| Scripts creados | **0** |
| Harness ejecutados | **0** |
| Dispatches enviados | **0** |
| `/dev/dri`, MMIO, VRAM | **No** |
| sudo / root | **No** |
| Paquetes instalados / herramientas | **No** |
| Configuración modificada | **No** |
| Informes previos sobrescritos | **No** |
| Binario `vk_compute_test` modificado | **No** |
| Shaders modificados | **No** |

---

## 8. Recomendación única

**Proponer como frontera posterior la corrección autorizada de `load_all_functions` en `vk_compute_test`, produciendo un artefacto separado con hash independiente y preservando el original intacto.**

Justificación con evidencia concreta:

1. **La causa raíz está identificada con precisión y es una corrección acotada.** El defecto es que las 7 funciones del lote inicial se resuelven con `g_instance == NULL`, pero solo `vkCreateInstance` es un comando global. Las otras 6 requieren una instancia. La corrección consiste en mover el segundo lote (y el resto) a después de `vkCreateInstance`, o en usar `vkGetProcAddr` — no es un rediseño.

2. **No hay ninguna vía reutilizable dentro del alcance actual.** H1 está refutada por §3.3, §3.4 y §3.5. Los componentes existentes (`gpu.register_read`, el SPIR-V, el flujo auditado) no se pueden componer sin escribir código, lo cual está prohibido.

3. **El artefacto original debe preservarse.** `vk_compute_test` con SHA-256 `017ee552f079434a7b3d7bc64f1334ef467e2651b8c8610cc2a7df07de071745` tiene valor probatorio: documenta un fallo real de un harness. Una versión corregida debe registrarse con hash propio y nombre distinto, para no confundir la evidencia.

4. **El resultado sería discriminante.** Con la corrección, un `observed = 42` + `RESULT: PASS` + exit `0` cerraría la etapa compute en Polaris12. Un `observed = 0` + `RESULT: FAIL` + exit `1` aportaría la primera evidencia real de fallo de dispatch en GFX8, atribuible con el flujo ya auditado.

**Requisitos previos a cualquier autorización de corrección:**
- Autorización explícita para producir un binario modificado.
- Nombre distinto (por ejemplo `vk_compute_test_fixed`) y hash independiente registrado.
- Preservación del original con su hash actual.
- No modificar shaders ni configuración del sistema.

No se inicia esa investigación en esta tarea.
