# RXRE — Validación causal de ejecución de shaders RADV/GFX8 (Polaris 12)

**Misión:** Determinar qué etapas de shaders están demostradas en ejecución real en la RX 550 (1002:699f, GFX8) bajo RADV, y cuáles permanecen abiertas.

**Resultado: `PARTIAL`** — Vertex y Fragment闭合 por evidencia de ejecución (ruta integrada). Compute, Tessellation y Geometry quedan `OPEN` por ausencia de herramientas discriminantes en el sistema.

---

## 1. Inventario de evidencia previa (reutilizada, no regenerada)

| Fuente | Contenido reutilizado |
|--------|-----------------------|
| `findings/1616-1625/CONTINUACION_MAPA_POLARIS12.md` §11.1, §13 | vkcube exit 0, 30 frames; matriz de cobertura SPIR-V por etapa; vkcube = rutas `mh-A-vkd-*`, `mh-A-vke-*` |
| `findings/1616-1625/GLOBAL_WORK_SCAN_REPORT.md` §6 | Fila «UMR SDMA0_STATUS» y fila `vkcube` en tabla de pruebas ejecutadas |
| `findings/1616-1625/RADV_GFX8_ACO_LLVM_CLOSURE.md` §7 | «Ejecución real de shaders en GPU por etapa → OPEN» |
| `/home/lucas/mesa-e3-20260917-213646/GPU-BOTTLENECK-report.md` §5.4 | `RADV_DEBUG=shaderstats` produjo SGPR/VGPR/VALU/instrucciones vía **vkmark 640x480** (VK) — evidencia de compilación ACO instrumentada |

**Evidencia previa clave reutilizada (no repetida):**

| Prueba | Versión | Resultado previo | Eslabón que demuestra |
|--------|---------|------------------|----------------------|
| `timeout 10 vkcube --c 30 --gpu_number 0` | Mesa 26.2.4 | exit 0, 30 frames, `RADV POLARIS12` | Compilación + envío GPU + finalización de ruta gráfica VS+FS |
| `glxinfo` | Mesa 26.2.4 | `radeonsi, polaris12, ACO`, GL 4.6, direct rendering | Ruta OpenGL/ACO (noRADV) |
| `glxgears` | Mesa 26.2.4 | 52.903 FPS | Ruta gráfica OpenGL sostenida |
| `glslc` + `spirv-val` × 7 shaders | SPIR-V 1.6 | vertex/fragment/compute/tesc/tese/geom + int_ops/fp_ops comp compilados y validados | **Solo** compilación GLSL→SPIR-V + validación estática; **no** compilación a ISA GFX8 ni envío GPU |

---

## 2. Verificación de herramientas discriminantes (inspección, no ejecución)

Comando: `command -v` sobre el conjunto de herramientas de conformance, ejecutado sin sudo.

| Herramienta | Estado verificado | Consecuencia |
|-------------|-------------------|--------------|
| `vkcube` | PRESENTE `/usr/bin/vkcube` | Única prueba Vulkan ejecutable |
| `vkcubepp` | PRESENTE `/usr/bin/vkcubepp` | Wrapper de vkcube, misma cobertura |
| `vulkaninfo` | PRESENTE `/usr/bin/vulkaninfo` | Solo enumera capacidades declaradas |
| `spirv-val`, `glslc` | PRESENTES | Solo validación estática de SPIR-V |
| **`piglit`** | **AUSENTE** | Sin conformance OpenGL |
| **`deqp` / Vulkan CTS** | **AUSENTE** | Sin conformance Vulkan |
| **`vkmark`** | **AUSENTE** | La evidencia previa de §5.4 del informe E3 usó vkmark; la herramienta ya no está instalada |

Verificación adicional sobre el binario `vkcube` (solo lectura, `strings`):

```
$ strings /usr/bin/vkcube | grep -E '\.(vert|frag|comp|geom|tesc|tese)|\.spv'
cube.frag
cube.vert
```

**`vkcube` contiene exclusivamente `cube.vert` y `cube.frag`.** No contiene shaders de compute, geometry, tessellation control ni tessellation evaluation.

**Consecuencia:** No existe en el sistema ninguna prueba capaz de ejercitar compute, tessellation o geometry en la GPU. No es una limitación de permisos (no requeriría root); es ausencia de la herramienta.

---

## 3. Definición aplicada: ejecución demostrada

Para cerrar una etapa se exigen cinco eslabones: (1) shader identificado y etapa confirmada; (2) compilación y creación de objetos; (3) envío efectivo a GPU; (4) finalización sin error relevante; (5) resultado observable y validado contra condición esperada independiente del exit status.

| Etapa | (1) Identificado | (2) Compilado | (3) Enviado a GPU | (4) Finalizado | (5) Resultado validado | Estado |
|-------|------------------|----------------|-------------------|----------------|----------------------|--------|
| **Vertex** | Sí (`cube.vert` en binario) | Sí (RADV, ACO) | Sí (vkcube dibuja) | Sí (30 frames, exit 0) | **Parcial** — frame presentado; sin comprobación numérica del contenido | **CLOSED_EXECUTION (ruta integrada)** |
| **Fragment** | Sí (`cube.frag` en binario) | Sí (RADV, ACO) | Sí (vkcube sombrea) | Sí (30 frames, exit 0) | **Parcial** —同上; sin comprobación numérica del contenido | **CLOSED_EXECUTION (ruta integrada)** |
| **Compute** | Sí (SPIR-V compilado, §13.2) | **No demostrado a ISA GFX8** | **No** | **No** | **No** | **OPEN** |
| **Tess. control** | Sí (SPIR-V compilado) | **No demostrado a ISA GFX8** | **No** | **No** | **No** | **OPEN** |
| **Tess. eval** | Sí (SPIR-V compilado) | **No demostrado a ISA GFX8** | **No** | **No** | **No** | **OPEN** |
| **Geometry** | Sí (SPIR-V compilado) | **No demostrado a ISA GFX8** | **No** | **No** | **No** | **OPEN** |

**Nota de granularidad:** vkcube ejercita vertex y fragment **de forma integrada y no aislada**. El mismo programa y la misma llamada de dibujo dependen de ambas etapas. No existe mecanismo de aislamiento en la evidencia disponible, por lo que no se atribuye causalidad individual a una etapa; se registra una ruta gráfica integrada VS+FS.

---

## 4. Pruebas reutilizadas y pruebas nuevas

| Categoría | Detalle |
|-----------|---------|
| Pruebas nuevas ejecutadas | **Ninguna.** No se justificó ninguna: las disponibles no son discriminantes para las etapas abiertas |
| Pruebas reutilizadas (evidencia previa) | vkcube (30 frames, exit 0), glxinfo, glxgears, glslc+spirv-val × 7, vkmark shaderstats (E3 §5.4) |
| Pruebas repetidas | **Ninguna.** Repetir vkcube no aportaría información nueva: el binario se verificó estáticamente y solo contiene VS+FS |
| Pruebas descartadas por no discriminantes | `vulkaninfo` (solo enumera capacidades declaradas; no envía trabajo) |

---

## 5. Clasificación epistemológica de conclusiones

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| `vkcube` contiene únicamente `cube.vert` y `cube.frag` | **PROVEN** | `strings /usr/bin/vkcube` ejecutado; resultado reproducible |
| `piglit`, `deqp`, `vkmark` no están instalados | **PROVEN** | `command -v` ejecutado; sin sudo |
| Vertex se ejecutó en GPU bajo RADV | **OBSERVED** | vkcube 30 frames, exit 0 (evidencia previa, `CONTINUACION_MAPA_POLARIS12.md` §11.1) |
| Fragment se ejecutó en GPU bajo RADV | **OBSERVED** | Misma prueba integrada |
| La ruta VS+FS produjo salida observable sin error | **OBSERVED** | Frames renderizados y presentados |
| El contenido del frame es numéricamente correcto | **OPEN** | No hay condición esperada independiente verificada |
| Compute se ejecutó en GPU | **OPEN** | Sin prueba disponible; SPIR-V compilado no implica envío |
| Tessellation (control/eval) se ejecutó en GPU | **OPEN** | Ídem |
| Geometry se ejecutó en GPU | **OPEN** | Ídem |
| La compilación SPIR-V demuestra soporte de etapa en GFX8 | **REFUTED** | `spirv-val` valida consistencia del binario SPIR-V, no traducción a ISA GFX8 ni ejecución |
| El shader no se envía a la GPU | **REFUTED** | vkcube renderiza y presenta; el trabajo se envía |
| El trabajo se envía pero falla la ejecución | **REFUTED** (para VS+FS) | 30 frames sin error visible |
| El fallo está en ACO | **REFUTED** (como hipótesis actual) | No se observó ningún fallo; ACO es el backend usado y la ruta funciona |
| El resultado calculado es incorrecto | **OPEN** | Sin comprobación numérica disponible |

---

## 6. Diferencia entre compilación estática y ejecución real

| Nivel | Qué demuestra | Qué NO demuestra | Etapas cubiertas |
|-------|---------------|------------------|------------------|
| `glslc` | GLSL → SPIR-V válido | Traducción a ISA GFX8, envio a GPU, resultado | Todas (7 shaders) |
| `spirv-val` | Consistencia del módulo SPIR-V | Semántica GFX8, capacidad de hardware | Todas (7 shaders) |
| `RADV_DEBUG=shaderstats` (E3) | Registro de ACO: SGPR/VGPR/VALU/instrucciones por shader | Que el shader se ejecutara con datos de entrada reales | Compute/vertex/fragment (indirecto, vía vkmark) |
| `vkcube` | Envío a GPU + finalización + presentación | Aislamiento por etapa; corrección numérica | VS+FS (integrados) |

**Distinción crítica:** el nivel `RADV_DEBUG=shaderstats` documentado en el informe E3 demuestra que ACO **compiló** shaders hasta instrucciones GFX8 con conteos de recursos (SGPR/VGPR). Eso es evidencia de compilación real a ISA, superior a `spirv-val`, pero sigue sin demostrar que el shader se **ejecutara** con resultados validados.

---

## 7. Requisito mínimo para resolver las etapas abiertas

Sin crear pruebas nuevas en esta fase, el requisito para un ciclo autorizado posterior es:

| Etapa | Requisito mínimo |
|-------|------------------|
| Compute | Programa Vulkan que: cree storage buffer de salida, despache compute shader con resultado aritmético conocido, lea el buffer y compare contra valor esperado. Alternativa: `vkmark` (ya usado antes en E3) o Vulkan CTS `vulkancompute` |
| Tess. control/eval | Programa o test que use `VK_PIPELINE_BIND_POINT_ALL_GRAPHICS` con etapas TCS/TES activas y verifique geometría resultante |
| Geometry | Programa o test con `geometryShader` activo y validación del primitivo de salida |
| Todas | Alternativa institucional: instalar `piglit` (GL) o Vulkan CTS (VK) desde paquetes del sistema — **requiere autorización de instalación, fuera del alcance actual** |

No se recomiendo escribir un programa Vulkan nuevo en esta fase: la instrucción prohíbe scripts nuevos y la utilidad sería de un solo uso frente a la disponibilidad de suites estándar.

---

## 8. Archivos actualizados y diff

**Creado (nuevo, no sobrescribe nada):**
- `findings/1616-1625/RADV_GFX8_SHADER_EJECUCION_VALIDACION.md` (este archivo)

**No modificados:**
- `RADV_GFX8_ACO_LLVM_CLOSURE.md`, `GLOBAL_WORK_SCAN_REPORT.md`, `GMC_VM_CONTEXT_GPUVM_REGDB_GAP.md`, informes SDMA, informes E2/E3.

Justificación de no editar el mapa global canónico: el GLOBAL_WORK_SCAN de la tarea previa (consolidación) ya السؤال está registrado como «RADV/GFX8 shaders → OPEN / requiere ejecución». Este informe refina ese estado a `PARTIAL` con detalle por etapa, pero el cambio de una línea en el mapa global no aporta información adicional y aumentaría el riesgo de colisión con el diff previo pendiente de revisar.

---

## 9. Verificaciones de integridad ejecutadas

| Verificación | Resultado |
|--------------|-----------|
| Estado Git del repositorio | 18 archivos modificados preexistentes bajo `tools/rxre/` (README, api/machine.py, 12 adapters, backends, tests) — **no tocados por esta tarea** |
| Existencia de los 7 informes de `findings/1616-1625/` | Verificados |
| `strings /usr/bin/vkcube`grep de etapas | Ejecutado, salida completa capturada (2 shaders) |
| `command -v` sobre 9 herramientas | Ejecutado, salida completa capturada |
| Modificaciones a Mesa, RADV, ACO, kernel, firmware | **Ninguna** |
| Acceso MMIO / DRM / sudo | **Ninguno** |

---

## 10. Estado final de la frontera

**`PARTIAL`**

- **Cerrado por ejecución:** Vertex y Fragment, como ruta integrada VS+FS bajo RADV/ACO (`OBSERVED`, con resultado validado solo de forma cualitativa).
- **Abierto:** Compute, Tessellation control, Tessellation evaluation, Geometry — no por fallo observado, sino por ausencia de prueba discriminante en el sistema (`OPEN`).

**No se declara que RADV/GFX8 funcione ni falle en las etapas abiertas.** No hay evidencia que sugiera defecto: la compilación de los shaders correspondientes es correcta a nivel SPIR-V y ACO registra recursos GFX8 válidos, pero la cadena de ejecución no ha sido ejercitada.

---

## 11. GLOBAL_WORK_SCAN y siguiente frontera prioritaria

**Fronteras del mapa global tras esta tarea:**

| Frontera | Estado | ¿Reabierta? |
|----------|--------|--------------|
| SDMA v3.1 / UMR | CLOSED_STATIC | No |
| GMC VM_CONTEXT gap | REJECTED | No |
| RADV/GFX8 ACO-LLVM (selección de backend) | CLOSED_STATIC | No |
| **RADV/GFX8 ejecución por etapa** | **PARTIAL (VS+FS execution; CS/TCS/TES/GS OPEN)** | Parcialmente |
| RadeonSI error recovery | CLOSED | No |
| MC firmware 32/64 | PROVEN (código) / OPEN (runtime) | No |
| Alias POLARIS11/POLARIS12 | PROVEN / impacto OPEN | No |

**Siguiente frontera prioritaria única:**

**Cerrar las etapas compute / tessellation / geometry de RADV/GFX8 mediante una prueba discriminante que valide el resultado calculado, no solo la finalización.**

Justificación basada en evidencia concreta:
- Es la única frontera material abierta que **no requiere privilegios**, no requiere modificar el sistema y no está bloqueada por una frontera ya cerrada.
- Las alternativas son: (a) instalar `piglit` o Vulkan CTS — requiere autorización de instalación, no disponible; (b) escribir un programa Vulkan nuevo — prohibido en esta fase por la regla de no crear scripts; (c) usar `vkmark`, que Cubo ya no está instalado pero se usó con éxito en el ciclo E3 (`shaderstats` activo), lo que indica que existió en el sistema y podría restituirse.
- Incertidumbre que resolvería: si el backend ACO genera código GFX8 correcto y ejecutable para las etapas que requieren unidades de hardware distintas del pipeline gráfico (compute: CU/LDS; tessellation: TCS/TES y el hardware de invocación; geometry: hardware de primitivas), o si existe una limitación real en GFX8/ACO para alguna de ellas.

**Siguiente paso discriminante (para un ciclo autorizado):** verificar disponibilidad de `vkmark` en el repositorio de paquetes o restaurar el entorno E3 (`/opt/mesa-26.2.2-rx550-haswell` no está disponible actualmente). Con esa herramienta, `RADV_DEBUG=shaderstats` distinguishing da evidencia de compilación GFX8 por etapa, y el exit statusSuccessful de la escena compute da un resultado observable. Si `vkmark` no es recuperable, el mínimo restante es autorización para instalar `piglit`/Vulkan-CTS o para escribir un test compute de un solo uso.

No se inicia esa investigación en esta tarea.
