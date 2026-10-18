# RXRE — Cierre estático: RADV/GFX8 ACO-LLVM para Polaris 12

**Objetivo:** Investigar la frontera abierta de compilación de shaders en RADV para AMD Radeon RX 550, Polaris 12 (1002:699f), GFX8, determinando qué puede afirmarse sobre la compatibilidad, selección y rutas de compilación ACO/LLVM para GFX8, usando únicamente evidencia estática y artefactos existentes.

**Estado de la frontera:** CERRADA (estática)

---

## 1. Pregunta concreta investigada

¿Cuál es el flujo de selección de backend (ACO vs LLVM) en RADV para GFX8/Polaris12, qué compatibilidad está declarada en el código, y qué aspectos están demostrados por evidencia previa frente a aquellos que requieren ejecución GPU?

---

## 2. Fuentes y versiones consultadas

| Fuente | Ruta | Estado |
|--------|------|--------|
| Código fuente Mesa RADV | `/home/lucas/mesa-26.2.2-build/src/amd/vulkan/` | DISPONIBLE |
| Código fuente Mesa compiler ACO | `/home/lucas/mesa-26.2.2-build/src/amd/compiler/` | DISPONIBLE |
| Código fuente Mesa LLVM | `/home/lucas/mesa-26.2.2-build/src/amd/llvm/` | DISPONIBLE |
| Código fuente Mesa common GPU info | `/home/lucas/mesa-26.2.2-build/src/amd/common/ac_gpu_info.c` | DISPONIBLE |
| Código fuente Mesa common family | `/home/lucas/mesa-26.2.2-build/src/amd/common/amd_family.h` | DISPONIBLE |
| Informe E2 | `/home/lucas/mesa-e2-20260917-175301/E2-report.md` | DISPONIBLE |
| Informe E3 GPU bottleneck | `/home/lucas/mesa-e3-20260917-213646/GPU-BOTTLENECK-report.md` | DISPONIBLE |
| Informe E2 summary | `/home/lucas/mesa-e2-20260917-175301/e2_summary.tsv` | DISPONIBLE |
| Mesa CUSTOM build | `/opt/mesa-26.2.2-rx550-haswell` | NO DISPONIBLE (no verificada) |
| Mesa build local | `/home/lucas/mesa-26.2.2-build` | DISPONIBLE (código fuente, no binario instalado) |

**Nota:** `/opt/mesa-26.2.2-rx550-haswell` no está disponible en el sistema. No se asume que representa la versión actualmente instalada.

---

## 3. Flujo de selección ACO/LLVM reconstruido

### 3.1 Detección del dispositivo y configuración de backend

El flujo comienza en `radv_physical_device_try_create` (`radv_physical_device.c`):

1. **Detección de chip**: `ac_identify_chip` identifica la familia del chip desde el kernel DRM. Para Polaris12 (PCI ID 0x699f), `device_info->family = FAMILY_VI`, y `info->family = CHIP_POLARIS12` (línea `identify_chip(POLARIS12)` en `ac_gpu_info.c`).

2. **Asignación de gfx_level**: Basado en `info->ip[AMD_IP_GFX].ver_major`:
   - `ver_major == 8` → `info->gfx_level = GFX8` (línea 778 de `ac_gpu_info.c`)
   - Polaris12 tiene IP GFX versión 8, por lo que `gfx_level = GFX8`.

3. **Soporte de GPU**: `radv_is_gpu_supported` rechaza solo GFX9 sin gráficos (CDNA) y GFX > GFX12. **GFX8 está soportado** (líneas 2504-2508 de `radv_physical_device.c`).

4. **Selección de backend**: `pdev->use_llvm = instance->debug_flags & RADV_DEBUG_LLVM` (línea 2660 de `radv_physical_device.c`).
   - **Por defecto**: `use_llvm = false` → se usa **ACO** como backend predeterminado.
   - `use_llvm = true` solo si se establece la variable de entorno/flag `RADV_DEBUG_LLVM`.
   - En release builds (`NDEBUG`), si se fuerza LLVM, se muestra error y se revierte a `use_llvm = false` (ACO).
   - Si `AMD_LLVM_AVAILABLE` no está definido en tiempo de compilación y se selecciona LLVM, se hace `abort()`.

### 3.2 Creación del dispositivo y compiler_info

En `radv_device_init_compiler_info` (`radv_device.c` líneas 1134-1300):

- `.use_llvm = pdev->use_llvm` se propaga a `compiler_info.key.use_llvm`.
- `.family = pdev->use_llvm ? pdev->info.family : CHIP_UNKNOWN` (línea 1234) — la familia solo se rellena cuando se usa LLVM; con ACO, `family = CHIP_UNKNOWN` y ACO obtiene la familia desde `compiler_info->debug.family`.
- `.ac = &pdev->info.compiler_info` — contiene `gfx_level` y otras propiedades de hardware.

### 3.3 Selección de backend por etapa de shader

En `radv_shader_nir_to_asm` (`radv_shader.c`):

```
if (compiler_info->key.use_llvm) {
    // LLVM backend: radv_fill_llvm_compiler_options → llvm_compile_shader
} else {
    // ACO backend: radv_aco_fill_compiler_options → aco_compile_shader
}
```

La decisión se toma por etapa de shader individual, basada en el mismo `use_llvm` para todas las etapas. No hay selección diferente por etapa.

En `radv_aco_fill_compiler_options`:
- `aco_info->gfx_level = compiler_info->ac->gfx_level` → GFX8 para Polaris12
- `aco_info->family = compiler_info->debug.family`

En `radv_fill_llvm_compiler_options` (solo si `use_llvm`):
- `options->family = compiler_info->key.family` → CHIP_UNKNOWN con ACO, CHIP_POLARIS12 con LLVM forzado

### 3.4 Target LLVM

No existe referencia explícita a `"gfx804"` en el código fuente de Mesa 26.2.2 consultado. El target LLVM se determina internamente por LLVM a partir de `options->family` (CHIP_POLARIS12) a través de `radv_init_llvm_compiler`. No se puede afirmar estáticamente que el target sea exactamente `"gfx804"` sin inspeccionar la inicialización de LLVM en tiempo de ejecución.

---

## 4. Evidencia previa reutilizada

| Evidencia | Fuente | Clasificación |
|-----------|--------|---------------|
| Dispositivo: RX 550, Polaris 12, 1002:699f | lspci, informes E2/E3 | PROVEN |
| RADV y RadeonSI básicos funcionan | Informes previos | PROVEN |
| vkcube salida exitosa (30 frames) | Informe previo | OBSERVED |
| glxinfo: renderizado directo, OpenGL 4.6 | Informe previo | OBSERVED |
| glxgears: 52.903 FPS | Informe previo | OBSERVED |
| Compilación y validación estática SPIR-V (vertex, fragment, compute, tessellation, geometry) | Informe previo | PROVEN |
| Ejecución real en GPU de compute, geometry y tessellation | Informe previo | OPEN |
| RADV_DEBUG=shaderstats disponible en VK | GPU-BOTTLENECK-report.md §5.4 | OBSERVED |
| RadeonSI (GL) no expone shaderstats | GPU-BOTTLENECK-report.md §5.4 | OBSERVED |
| Compilación de shaders descartada como cuello de rendimiento | GPU-BOTTLENECK-report.md §190 | OBSERVED |
| Scenes ALU/shader no son el cuello (2-3× más rápido que fill) | E2-report.md §92-93 | OBSERVED |

---

## 5. Cobertura por etapa de shader

| Etapa | Compilación SPIR-V demostrada | Validación estática demostrada | Compilación mediante backend específico demostrada | Ejecución real en GPU demostrada | Estado |
|-------|------------------------------|-------------------------------|--------------------------------------------------|----------------------------------|--------|
| Vertex | PROVEN (informe previo) | PROVEN (informe previo) | INFERRED (código RADV maneja todas las etapas por ACO por defecto) | OPEN | PROVEN (estática) / OPEN (dinámica) |
| Fragment | PROVEN (informe previo) | PROVEN (informe previo) | INFERRED (código RADV maneja todas las etapas por ACO por defecto) | OPEN | PROVEN (estática) / OPEN (dinámica) |
| Compute | PROVEN (informe previo) | PROVEN (informe previo) | INFERRED (código RADV maneja todas las etapas por ACO por defecto) | OPEN | PROVEN (estática) / OPEN (dinámica) |
| Tessellation | PROVEN (informe previo) | PROVEN (informe previo) | INFERRED (código RADV maneja todas las etapas por ACO por defecto) | OPEN | PROVEN (estática) / OPEN (dinámica) |
| Geometry | PROVEN (informe previo) | PROVEN (informe previo) | INFERRED (código RADV maneja todas las etapas por ACO por defecto) | OPEN | PROVEN (estática) / OPEN (dinámica) |

**Nota:** El código de RADV (`radv_shader_nir_to_asm`) no diferencia entre etapas para la selección de backend. Todas las etapas pasan por el mismo flujo: ACO por defecto, LLVM solo si se fuerza con `RADV_DEBUG_LLVM`. No hay restricción de GFX8 para ninguna etapa específica en el código inspectado.

---

## 6. Características específicas de GFX8 en RADV

El código de RADV contiene condiciones explícitas para GFX8:

| Característica | Condición | Estado para GFX8 |
|--------------|-----------|------------------|
| `KHR_copy_memory_indirect` | `gfx_level >= GFX8` | ✅ Soportado |
| `KHR_index_type_uint8` | `gfx_level >= GFX8` | ✅ Soportado |
| `EXT_device_generated_commands` | `gfx_level >= GFX8` | ✅ Soportado |
| `EXT_index_type_uint8` | `gfx_level >= GFX8` | ✅ Soportado |
| `shaderDeviceClock` | `gfx_level >= GFX8` | ✅ Soportado |
| `shaderSharedFloat32AtomicAdd` | `gfx_level >= GFX8` | ✅ Soportado |
| `indirectMemoryCopy` | `gfx_level >= GFX8` | ✅ Soportado |
| `indirectMemoryToImageCopy` | `gfx_level >= GFX8` | ✅ Soportado |
| `apiVersion` | `gfx_level >= GFX8 ? RADV_API_VERSION : 1.3` | ✅ API completa |
| `D16` (LLVM) | `gfx_level >= GFX8` | ✅ Soportado con LLVM |
| `shader_buffer_float_minmax` | `gfx_level <= GFX7` o `GFX10+` | ❌ NO para GFX8 |
| `pops` (LLVM) | `gfx_level >= GFX9 && !use_llvm` | ❌ NO para GFX8 |
| `EXT_shader_image_float32_atomic_add` | `gfx_level >= GFX12 && !use_llvm` | ❌ NO para GFX8 |

**Conclusión:** GFX8 tiene soporte declarado y parcial en RADV. Algunas características avanzadas requieren GFX9+ o GFX12+, pero no hay restricción que impida que GFX8 funcione con ACO.

---

## 7. Clasificaciones epistemológicas

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| Polaris12 (CHIP_POLARIS12) pertenece a FAMILY_VI | PROVEN | `ac_gpu_info.c` switch FAMILY_VI incluye POLARIS12 |
| gfx_level = GFX8 para Polaris12 | PROVEN | `ac_gpu_info.c` línea 778: `ip[AMD_IP_GFX].ver_major == 8` → GFX8 |
| GFX8 está soportado por radv_is_gpu_supported | PROVEN | Solo rechaza GFX9 sin gráficos y GFX > GFX12 |
| Backend predeterminado para GFX8 es ACO | PROVEN | `use_llvm = false` por defecto; `RADV_DEBUG_LLVM` requiere activación explícita |
| LLVM solo disponible si AMD_LLVM_AVAILABLE y no es release build | PROVEN | `radv_physical_device.c` líneas 2660-2675 |
| Todas las etapas de shader usan el mismo backend (ACO por defecto) | PROVEN | `radv_shader_nir_to_asm` no diferencia por etapa |
| Target LLVM "gfx804" para Polaris12 | OPEN | No hay referencia explícita en el código fuente consultado |
| Ejecución real de shaders en GPU por etapa | OPEN | Requiere ejecución GPU; no demostrada estáticamente |
| Compilación de shaders es cuello de rendimiento | REFUTED | GPU-BOTTLENECK-report.md §190, E2-report.md §92-93 |
| RADV/GFX8 no funciona en absoluto | REFUTED | vkcube, glxinfo, glxgears funcionaron; GFX8 soportado en código |

---

## 8. Contradicciones y limitaciones

**No se encontraron contradicciones** en la evidencia disponible:

1. El código declara soporte para GFX8 y las pruebas previas (vkcube, glxinfo, glxgears) confirmaron funcionamiento básico.
2. No hay restricción de GFX8 para ACO en el código de RADV.
3. La compilación de shaders fue descartada como cuello de rendimiento, no como imposibilidad.

**Limitaciones:**

1. El target LLVM exacto ("gfx804" vs otro) no puede afirmarse estáticamente sin inspección en tiempo de ejecución.
2. La ejecución real de shaders por etapa en GPU no ha sido demostrada (solo compilación estática y validación SPIR-V).
3. Algunos características avanzadas (shader_buffer_float_minmax, pops, etc.) no están disponibles para GFX8, pero esto no impide el funcionamiento básico.

---

## 9. Cambios realizados

**No se modificó ningún archivo.** Esta tarea es de investigación estática y documentación. No se escribió ningún script, no se repitieron pruebas, no se modificaron componentes del sistema, Mesa, RADV, RadeonSI, LLVM, ACO, WSI, firmware ni configuraciones.

No hay informe existente que mantenga específicamente la frontera RADV/GFX8 en `findings/1616-1625/`. La información RADV/GFX8 estaba dispersa en los informes E2 y E3. Se crea este informe como documentación de cierre estático.

---

## 10. Decisión final de la frontera

**Estado: CERRADA (estática)**

La frontera estática puede cerrarse porque se ha determinado:

1. **Cómo se selecciona el backend:** Por defecto ACO (`use_llvm = false`). LLVM solo si se establece `RADV_DEBUG_LLVM` y está disponible en tiempo de compilación, y no es un release build.
2. **Compatibilidad declarada con GFX8:** GFX8 está soportado por `radv_is_gpu_supported`. Hay características específicas de GFX8 habilitadas en el código. Algunas características avanzadas requieren GFX9+ o GFX12+.
3. **Aspectos demostrados por evidencia previa:** Compilación SPIR-V estática para todas las etapas, validación de shaders, funcionamiento básico (vkcube, glxinfo, glxgears).
4. **Aspectos que requieren ejecución GPU y permanecen abiertos:** Ejecución real de shaders por etapa, target LLVM exacto ("gfx804" no verificado estáticamente).

**Cerrar la investigación estática no equivale a certificar el funcionamiento completo de ACO, LLVM o todas las etapas de shaders en Polaris 12.**

---

## 11. Una sola siguiente acción prioritaria

**Ninguna acción inmediata requerida.** La frontera RADV/GFX8 ACO-LLVM está cerrada estáticamente. Si en una fase futura con autorización de ejecución GPU se desea verificar la ejecución real de shaders por etapa, esa sería la siguiente acción, pero queda fuera del alcance actual.

---

## 12. GLOBAL_WORK_SCAN

Revisión del mapa global RXRE:

| Frontera | Estado | ¿Afectada por este cierre? |
|----------|--------|---------------------------|
| GMC VM_CONTEXT | REJECTED (gap no existe) | No |
| RadeonSI error recovery | CLOSED | No |
| SDMA v3.1 / UMR | CLOSED_STATIC | No |
| MC firmware 32 vs 64-bit | PROVEN / runtime OPEN | No |
| Alias POLARIS11/POLARIS12 | PROVEN / funcional OPEN | No |
| RADV/GFX8 ACO-LLVM | **CLOSED_STATIC** (este informe) | N/A |
| SPIR-V/GFX8 GPU execution | OPEN | No — requiere ejecución GPU, fuera de alcance estático |

No se identificó una nueva frontera prioritaria que pueda abordarse estáticamente sin ampliar el alcance. Las fronteras restantes requieren ejecución GPU o autorización que no está disponible.

**No se abre nueva línea de trabajo.** El mapa global refleja los hallazgos sin duplicaciones.
