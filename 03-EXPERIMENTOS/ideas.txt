```text
IDEAS ORIGINALES DEL USUARIO
(no son hechos ni mejoras demostradas; son ideas mías, el usuario, no del modelo)
Base: tabla consolidada. Evaluación posterior.
Mecanismos: combinar, variar, invertir, transferir, reformular, descomponer, eliminar, extrapolar, analogía, cambio de contexto.
Estructura: CORPUS → MECANISMO → IDEA → {evidencia, faltante, discriminante}

1 RENDIMIENTO
R-NEW-01 separar throughput/geometría/fragmentos (matriz VS/FS)
R-NEW-02 layers vs fragmentos
R-NEW-03 resolución vs trabajo efectivo vs WSI/present
R-NEW-04 resolución vs render scale
R-NEW-05 oversubscription de recursos shader
R-NEW-06 barrido de intensidad aritmética
R-NEW-07 barrido de patrón de acceso a memoria
R-NEW-08 reutilización de texturas
R-NEW-09 umbral de tamaño de textura
R-NEW-10 umbral de cantidad de texturas
R-NEW-11 barrido de presión VBO/IBO
R-NEW-12 instancing vs geometría duplicada
R-NEW-13 barrido de densidad de draw calls
R-NEW-14 barrido de tamaño de batch
R-NEW-15 saturación de envío CPU

2 CPU↔GPU↔ENVÍO
R-NEW-16 mismo trabajo GPU, distinta tasa de envío CPU
R-NEW-17 ritmo artificial de CPU
R-NEW-18 envío por lotes vs incremental
R-NEW-19 sensibilidad a afinidad de CPU
R-NEW-20 sensibilidad a frecuencia de CPU
R-NEW-21 mapa de divergencia GPU busy/FPS

3 H8 STARVATION
R-NEW-22 distribución de duración de busy
R-NEW-23 correlación de fase busy/FPS
R-NEW-24 latencia de finalización de fence
R-NEW-25 latencia submit-to-fence
R-NEW-26 espera WSI vs finalización GPU

4 H12 PRESENTACIÓN
R-NEW-27 workload sin present
R-NEW-28 mismo render, distinto modo de presentación
R-NEW-29 barrido de frecuencia de present
R-NEW-30 barrido de profundidad de cola de frames
R-NEW-31 triple vs doble buffering
R-NEW-32 primer frame vs estado estable

5 RUNTIME PM
R-NEW-33 atribución de despertar PM en primer frame
R-NEW-34 duración idle vs latencia de despertar
R-NEW-35 experimento de ráfagas repetidas
R-NEW-36 caracterización de histéresis de runtime PM

6 ASPM/PCIe
R-NEW-37 estado de enlace PCIe vs latencia de ráfaga
R-NEW-38 umbral de duración de ráfaga
R-NEW-39 umbral de tamaño de transferencia
R-NEW-40 escalera de throughput PCIe

7 VRAM/GTT/SPILLING
R-NEW-41 escalera de working set
R-NEW-42 histéresis de presión VRAM
R-NEW-43 churn de residencia
R-NEW-44 experimento de tiempo de vida de recursos
R-NEW-45 comparación VRAM/GTT a misma capacidad
R-NEW-46 acantilado de rendimiento por spill a PCIe

8 MCLK/DPM
R-NEW-47 observador de transiciones MCLK
R-NEW-48 latencia de transición MCLK
R-NEW-49 modelo de histéresis MCLK
R-NEW-50 clasificador de workload para MCLK
R-NEW-51 mapa de independencia SCLK/MCLK
R-NEW-52 coste de transición de clock

9 POWER CAP
R-NEW-53 curva de sensibilidad al cap
R-NEW-54 experimento de distancia al cap
R-NEW-55 detección de umbral de cap
R-NEW-56 curva de eficiencia (FPS/W, work/joule)
R-NEW-57 equilibrio térmico dependiente del cap

10 TEMPERATURA
R-NEW-58 constante de tiempo térmica
R-NEW-59 retardo temperatura-rendimiento
R-NEW-60 deuda térmica sin calentamiento artificial
R-NEW-61 misma temperatura, distinta historia
R-NEW-62 experimento de recuperación térmica

11 SHADER/ACO
R-NEW-63 barrido de ILP
R-NEW-64 matriz occupancy vs ILP
R-NEW-65 umbral de unroll
R-NEW-66 barrido de ancho de precisión
R-NEW-67 barrido de dependencia cross-lane
R-NEW-68 complejidad shader vs presión de registros
R-NEW-69 tradeoff compile-time vs runtime de shader

12 MSAA/RASTER/ROP
R-NEW-70 curva de escalado MSAA
R-NEW-71 sample shading vs MSAA
R-NEW-72 experimento de control DCC
R-NEW-73 barrido de complejidad de blend
R-NEW-74 barrido de formato de attachment

13 GRÁFICOS+CÓMPUTO
R-NEW-75 solapamiento gráficos/cómputo
R-NEW-76 sensibilidad al número de colas
R-NEW-77 barrido de coste de barreras
R-NEW-78 barrido de profundidad de dependencias
R-NEW-79 frontera de utilidad de async compute

14 SDMA/COPY
R-NEW-80 utilización del copy engine
R-NEW-81 solapamiento copy/gráficos
R-NEW-82 umbral de tamaño de copy

15 MESA/RADV/RADEONSI
R-NEW-83 comparación Mesa por workload
R-NEW-84 comparación Mesa cold-start vs steady-state
R-NEW-85 comparación de driver emparejada por API
R-NEW-86 mismo workload / distinta versión Mesa
R-NEW-87 matriz de interacción de variables de entorno
R-NEW-88 auditoría de aplicabilidad de workarounds

16 VULKAN
R-NEW-89 matriz de capacidades de colas Vulkan
R-NEW-90 experimento de coste de sincronización
R-NEW-91 granularidad de command buffers
R-NEW-92 presión de descriptor/resource-binding
R-NEW-93 variación de pipeline-state

17 INSTRUMENTACIÓN
R-NEW-94 acuerdo entre múltiples observadores
R-NEW-95 caracterización de latencia de medición
R-NEW-96 sensibilidad a frecuencia de muestreo
R-NEW-97 experimento de overhead del observador
R-NEW-98 alineación de timestamps
R-NEW-99 mapa semántico de métricas

18 CONTADORES GFX8
R-NEW-100 mapeo contador→hipótesis
R-NEW-101 análisis de redundancia de contadores
R-NEW-102 conjunto de falsación por contadores
R-NEW-103 cadena de validación física

19 POWER PROFILES
R-NEW-104 matriz de comportamiento de perfiles
R-NEW-105 latencia de transición de perfil
R-NEW-106 interacción perfil × workload
R-NEW-107 frontera de eficiencia de perfiles

20 METODOLÓGICAS
METH-NEW-01 matriz de ideas
METH-NEW-02 ideación guiada por contradicciones
METH-NEW-03 inversión de resultados negativos
METH-NEW-04 caza de fronteras
METH-NEW-05 inversión de confounders
METH-NEW-06 búsqueda de variables ocultas
METH-NEW-07 ideación por vacío de medición
METH-NEW-08 sustitución de modelos
METH-NEW-09 búsqueda de analogías entre dominios
METH-NEW-10 motor de recombinación
METH-NEW-11 inversión de parámetros
METH-NEW-12 descomposición temporal
METH-NEW-13 descomposición espacial
METH-NEW-14 descomposición de escala
METH-NEW-15 perturbación sin optimización

ESTRUCTURA
IDEA → pregunta → hipótesis → experimento → optimización.
No meter directo en registro de hipótesis.
Generación divergente vs evaluación convergente.
Siguiente paso: generador formal de ideas para OpenCode.
Bucle: DOC → EVIDENCIA → MECANISMOS → IDEAS → DUP/CONTR → HIPÓTESIS → EXPERIMENTOS → EVIDENCIA → NUEVA IDEACIÓN.

Estas ideas son mías, del usuario. No son del asistente.
```

```text
REVISIÓN ADVERSARIAL DE MIS IDEAS
(ideas originales del usuario, no del modelo)
Criterio: demostrar redundancia, mala formulación, no discriminancia, no causalidad, inejecutabilidad, debilidad o mezcla caracterización/optimización.
No descartar por falta de evidencia. Literatura respalda generación divergente + evaluación convergente, pero eso no convierte idea en hipótesis científica.

RESULTADO GLOBAL
107 ideas nominales → no mismo estatus.
~30-40 independientes o potencialmente independientes.
~35-45 variantes de otras (no conservar ID propio).
~10-20 experimentos/mediciones, no ideas.
~10-15 sin hipótesis falsable.
METH-NEW: reglas metodológicas, no ideas sobre RX550.
Marcar: REDUNDANT, REFORMULATE, SUBIDEA, METHOD_RULE.

1 RENDIMIENTO
R-NEW-01 VERDE/AMARILLO. Matriz VS/FS pobre; cambiar ambos confunde ocupación/bandwidth/raster/registros. Idea fuerte: workloads ortogonales por etapa. Parcialmente redundante con 05/06/68. CONSERVAR REFORMULAR.
R-NEW-02 AMARILLO. layers no es variable causal universal; depende de tipo de layer. REFORMULAR: layers→coste raster/memoria.
R-NEW-03 VERDE pero demasiado grande. Tres fenómenos: rendering, trabajo efectivo, presentación. DIVIDIR EN 3.
R-NEW-04 VERDE. Conservar.
R-NEW-05 VERDE. "Oversubscription" ambiguo. Conservar si se define recurso.
R-NEW-06 VERDE FUERTE. Roofline memory-vs-compute. Conservar.
R-NEW-07 VERDE. Familia. 08/09/parte 10 son subcasos.
R-NEW-08 SUBIDEA de 07.
R-NEW-09 REDUNDANTE/PARAMETER-SWEEP (H6/M-01).
R-NEW-10 SUBIDEA H6/M-01.
R-NEW-11 VERDE. Conservar.
R-NEW-12 VERDE. Conservar como experimento, no optimización universal.
R-NEW-13 VERDE FUERTE. Conservar.
R-NEW-14 CASI REDUNDANTE con 13. Fusionar: submission granularity sweep.
R-NEW-15 REDUNDANTE con 13/14/16. CRITERIO DE RESULTADO.

2 CPU↔GPU
R-NEW-16 REDUNDANTE con 13. Fusionar.
R-NEW-17 AMARILLO. EXPERIMENTO AUXILIAR.
R-NEW-18 REDUNDANTE con 13/14. Fusionar.
R-NEW-19 DÉBIL PARA RX550. CARACTERIZACIÓN DE ENTORNO.
R-NEW-20 AUXILIAR.
R-NEW-21 NO ES IDEA. MÉTRICA/CLASIFICADOR. gpu_busy alto+FPS bajo no demuestra starvation.

3 H8
R-NEW-22 BUENA. Conservar.
R-NEW-23 BUENA. Conservar como experimento temporal; necesita sincronía precisa.
R-NEW-24 BUENA. Conservar.
R-NEW-25 BUENA. Conservar como medición temporal.
R-NEW-26 MUY BUENA. Conservar. GPU DONE ≠ PRESENT READY ≠ FRAME DISPLAYED.

4 H12
R-NEW-27 MUY BUENA.
R-NEW-28 BUENA, depende del stack.
R-NEW-29 AMARILLA. Acoplada a compositor/WSI.
R-NEW-30 BUENA. Puede modificar throughput y latency.
R-NEW-31 DÉBIL/DEPENDIENTE DEL STACK.
R-NEW-32 MUY BUENA. Fusionar con 33.

5 RUNTIME PM
R-NEW-33 BUENA pero causalmente ambiciosa. Primer frame no demuestra PM.
R-NEW-34 BUENA. Mejor forma de atacar H4.
R-NEW-35 REDUNDANTE con 34.
R-NEW-36 SOSPECHOSA. REFORMULAR → transición/retención de estado PM, no asumir histéresis.

6 PCIe
R-NEW-37 BUENA, dependiente de observabilidad.
R-NEW-38 SUBIDEA de 37.
R-NEW-39 SUBIDEA de 40.
R-NEW-40 BUENA. Familia: PCIe burst/transfer characterization.

7 VRAM/GTT
R-NEW-41 MUY BUENA. Ya implícita en H6.
R-NEW-42 ESPECULATIVA. No asumir hysteresis.
R-NEW-43 BUENA. Requiere observar residency.
R-NEW-44 NO ES VRAM PRESSURE. Resource-management overhead. Separar.
R-NEW-45 MUY BUENA.
R-NEW-46 BUENA. "Cliff" predicción fuerte. Reformular: discontinuidades por spilling.

8 MCLK/DPM
R-NEW-47 MUY BUENA. Forma menos peligrosa de H7.
R-NEW-48 BUENA. Necesita sampling suficiente.
R-NEW-49 DEMASIADO PRONTO. Primero demostrar transiciones.
R-NEW-50 BUENA.
R-NEW-51 BUENA.
R-NEW-52 DEMASIADO FUERTE. Reformular: efectos temporales de transiciones.

9 POWER CAP
R-NEW-53/54/55 esencialmente CAP→respuesta en 3 formas. FUSIONAR.
R-NEW-56 BUENA pero no hipótesis de hardware. MÉTRICA. FPS/W oculta utilidad/calidad/latencia/estabilidad.
R-NEW-57 BUENA. Consecuencia de 53, no independiente.

10 TEMPERATURA
R-NEW-58 BUENA.
R-NEW-59 BUENA pero derivada de 58.
R-NEW-60 MUY BUENA. Evita heating artificial.
R-NEW-61 MUY INTERESANTE. Independiente: prueba path dependence.
R-NEW-62 REDUNDANTE con 60/61.

11 SHADER/ACO
R-NEW-63 BUENA.
R-NEW-64 MUY BUENA.
R-NEW-65 SUBIDEA de 63/64.
R-NEW-66 BUENA, peligrosa semánticamente.
R-NEW-67 BUENA si operación soportada/relevante.
R-NEW-68 MUY BUENA.
R-NEW-69 BUENA. Más lifecycle/performance engineering.

12 MSAA/RASTER
R-NEW-70/71/72/73/74 BUENAS. Sobreviven bien. 71 diferente de 70. 72 ya implícita en F-02.

13 GRAPHICS+COMPUTE
R-NEW-75 BUENA. Ya existe A-01.
R-NEW-76 PRECONDICIÓN, NO IDEA.
R-NEW-77 BUENA.
R-NEW-78 BUENA, muy relacionada con 77.
R-NEW-79 NO INDEPENDIENTE. Criterio emergente de A-01.

14 SDMA
R-NEW-80 BUENA.
R-NEW-81 BUENA.
R-NEW-82 SUBIDEA de 80/81.

15 MESA
R-NEW-83 BUENA.
R-NEW-84 BUENA.
R-NEW-85 MUY BUENA. Evita Vulkan CUSTOM vs OpenGL STOCK.
R-NEW-86 BUENA, puede ser benchmarking de versiones.
R-NEW-87 PELIGROSA. Explosión combinatoria A×B×C×D×E. Seleccionar solo con hipótesis de mecanismo.
R-NEW-88 BUENA pero auditoría documental.

16 VULKAN
R-NEW-89 MUY BUENA como capability audit. No mejora.
R-NEW-90 BUENA.
R-NEW-91 BUENA, relacionada con 13/14.
R-NEW-92 BUENA, potencialmente enorme.
R-NEW-93 BUENA, puede ser combinatoria explosiva.

17 INSTRUMENTACIÓN
R-NEW-94/95/96/97/98 MUY BUENAS.
R-NEW-99 NO ES EXPERIMENTO. Infraestructura epistemológica. Requisito/documentación.

18 CONTADORES GFX8
R-NEW-100 MUY BUENA.
R-NEW-101 BUENA.
R-NEW-102 EXCELENTE METODOLÓGICAMENTE. Pregunta: ¿qué observación distinguiría H de ¬H?
R-NEW-103 MUY BUENA. Validación de instrumentación.

19 POWER PROFILES
R-NEW-104 BUENA.
R-NEW-105 SUBIDEA de 104.
R-NEW-106 SUBIDEA de 104.
R-NEW-107 MÉTRICA/CRITERIO.

20 METODOLOGÍA
METH-NEW-01 NO ES MECANISMO COMPLETO. REPRESENTACIÓN.
METH-NEW-02 MUY BUENA. Contradicción→validar fuentes→determinar si real→idear.
METH-NEW-03 BUENA. Estrategia generativa, no inferencia.
METH-NEW-04 MUY BUENA. Una de las mejores.
METH-NEW-05 MUY BUENA. Mejor: aislar variables confundentes.
METH-NEW-06 BUENA. Exigir: variable+mecanismo plausible+observabilidad.
METH-NEW-07 EXCELENTE.
METH-NEW-08 MUY BUENA. Solo con modelos alternativos plausibles.
METH-NEW-09 VÁLIDA PELIGROSA. Exigir: mecanismo fuente→isomorfismo funcional→mecanismo candidato→predicción.
METH-NEW-10 MUY BUENA. Necesita poda por mecanismo.
METH-NEW-11 BUENA. Parámetro debe tener significado causal.
METH-NEW-12 MUY BUENA.
METH-NEW-13 BUENA. No todo observable con esa granularidad.
METH-NEW-14 MUY BUENA.
METH-NEW-15 EXCELENTE. Debería ser regla central del generador.

PROBLEMA ESTRUCTURAL: 5 NIVELES
N1 MECANISMO DE IDEACIÓN (METH-NEW-02/03/04...)
N2 PREGUNTA CIENTÍFICA (H8, H12, H6...)
N3 EXPERIMENTO (R-NEW-24/40/70...)
N4 MÉTRICA/INSTRUMENTO (R-NEW-21/56/99...)
N5 POSIBLE OPTIMIZACIÓN
No debería haber un único registro plano de "ideas".

REFUTACIONES MÁS FUERTES (cuestionables como ideas independientes)
R-NEW-15, 21, 29, 35, 36, 38, 39, 42, 49, 52, 55, 56, 59, 62, 65, 76, 79, 82, 87, 99, 105, 106, 107, METH-NEW-01.

SOBREVIVEN MEJOR COMO LÍNEAS DE INVESTIGACIÓN
R-NEW-04, 06, 07, 11, 12, 13, 22, 24, 25, 26, 32, 34, 40, 41, 43, 45, 47, 50, 51, 60, 61, 63, 64, 68, 70, 71, 72, 73, 74, 75, 77, 80, 81, 85, 86, 90, 91, 94, 95, 96, 97, 98, 100, 101, 102, 103.
Metodológicamente: METH-NEW-02, 03, 04, 06, 07, 08, 10, 12, 14, 15.

CONCLUSIÓN CLAVE
Problema mayor: generador produce variaciones de experimentos y las etiqueta como ideas.
Ejemplo memoria: 8 "ideas" podrían ser 1 idea raíz (caracterizar transición de régimen de memoria) con árbol de experimentos.
Ejemplo submission: 1 idea raíz (coste submission CPU→GPU) con ramas.
Ejemplo clocks: 1 idea raíz (mecanismo transición DPM) con ramas.
REFACTORIZAR, no descartar. Conservar trazabilidad. Elevar a ~30-50 ideas raíz con árbol de experimentos debajo.
Regla: no crear nueva IDEA cuando solo cambia parámetro experimental, salvo que introduzca mecanismo causal distinto.

ESTRUCTURA RECOMENDADA
DOMINIO → PREGUNTA/PROBLEMA → IDEA → {mecanismo, predicción, variables, observables, falsador} → EXPERIMENTOS (E1, E2, E3).

Literatura: separar generación amplia de evaluación/refinamiento, alternar iterativamente. Analogía = generador, no evidencia.

Estas ideas y la revisión adversarial son mías, del usuario. No del asistente.
```

```text
IDEAS INTERNACIONALES DEL USUARIO (N-INT)
(ideas mías, del usuario, no del modelo)
Búsqueda en AMD/LLVM/Khronos/literatura GPU para encontrar mecanismos NO representados en las 107 previas.
Criterio: no expandir mismas familias draw calls→VRAM→MCLK→WSI.

A. MICROARQUITECTURA/SHADER
N-INT-01 separar latencia oculta de throughput bruto (latency-hiding efficiency)
N-INT-02 distancia load→use (latency hiding intra-wave)
N-INT-03 dependencia artificial vs natural
N-INT-04 lifetime de VGPR como variable independiente (register count ≠ register lifetime)
N-INT-05 trade-off ILP↔occupancy con frontera de compensación explícita
N-INT-06 scheduler-sensitive shader (mismo algoritmo, distinto orden)
N-INT-07 instruction-mix sensitivity (igual FLOP, distinta mezcla)
N-INT-08 scalar/vector separation (SGPR-heavy vs VGPR-heavy)

B. MEMORIA
N-INT-09 localidad temporal vs espacial (separar R-NEW-07)
N-INT-10 divergencia de accesos dentro de wave
N-INT-11 working-set × localidad
N-INT-12 working-set × wave occupancy
N-INT-13 reutilización inter-wave
N-INT-14 memory-level parallelism sweep
N-INT-15 latencia vs bandwidth (roofline omite latency)

C. CACHÉS Y COMPRESIÓN
N-INT-16 cache-capacity sweep (cache-resident→pressure→memory)
N-INT-17 cache-thrashing controlado
N-INT-18 cache reuse distance
N-INT-19 compresión vs bandwidth (DCC como reducción de tráfico, no ON/OFF)
N-INT-20 compresión × render target format

D. RASTERIZACIÓN
N-INT-21 overdraw depth (1×,2×,4×,8×,16×)
N-INT-22 Early-Z effectiveness (front-to-back vs back-to-front)
N-INT-23 depth complexity × shader cost
N-INT-24 primitive discard efficiency (hipótesis a validar, no asumir)
N-INT-25 small primitive amplification (triángulos grandes vs muchos pequeños)

E. SINCRONIZACIÓN
N-INT-26 barrier scope minimization (global vs resource-specific)
N-INT-27 stage-mask precision (ALL_COMMANDS→ALL_GRAPHICS→specific)
N-INT-28 access-mask precision (stage scope vs access scope)
N-INT-29 barrier batching (10 separadas vs 1 DependencyInfo con 10)
N-INT-30 barrier placement distance (producer→barrier→consumer)
N-INT-31 dependency direction (vertex→fragment, fragment→vertex, compute→graphics, graphics→compute)
N-INT-32 barrier necessity audit (qué dependencia protege cada barrier)

F. CPU/API
N-INT-33 descriptor-update pressure
N-INT-34 descriptor reuse (nuevo cada frame vs reutilizado)
N-INT-35 descriptor update × draw-call density
N-INT-36 pipeline-state change density
N-INT-37 pipeline cache cold/warm
N-INT-38 shader cache cold/warm (separar pipeline/shader/fs/runtime)
N-INT-39 first-frame causal decomposition (PM wake, shader comp, pipeline creation, descriptor alloc, resource upload, WSI) — MUY FUERTE

G. FRAME PACING
N-INT-40 mismo FPS medio, distinta distribución (16,16,16 vs 8,8,8,40)
N-INT-41 p50/p90/p95/p99/max decomposition
N-INT-42 frame-time autocorrelation (independientes, periódicos, burst-like, correlacionados)
N-INT-43 stutter recurrence interval
N-INT-44 frame pacing vs GPU utilization (mismo gpu_busy promedio, distinta distribución)

H. ASYNC COMPUTE
N-INT-45 async-compute complementarity (qué carga gráfica deja recursos utilizables)
N-INT-46 async compute interference curve (10%,25%,50%,75%,100%)
N-INT-47 complementarity map (beneficial, neutral, interfering)

I. DESCRIPTOR/PIPELINE/RESOURCE
N-INT-48 resource allocation churn (GPU execution vs allocation/free)
N-INT-49 buffer packing (mismo payload, distintas estrategias)
N-INT-50 per-object update vs batched update
N-INT-51 state-change locality (random vs state-grouped)

J. PERFORMANCE CEILINGS
N-INT-52 ceiling decomposition (matemático→memoria→occupancy→submission→sync→WSI)
N-INT-53 distance-to-ceiling (achieved/theoretical)
N-INT-54 ceiling migration (memory-bound→compute-bound→sync-bound→WSI-bound) — MUY FUERTE
N-INT-55 multi-ceiling Pareto map (performance, power, thermal, latency, stability)

K. DVFS
N-INT-56 frequency response curve (frequency→performance,power,energy,temp)
N-INT-57 frequency sensitivity by workload class (compute/memory/latency/WSI-bound)
N-INT-58 energy-per-frame (no FPS/W)
N-INT-59 energy-delay product (EDP=Energy×Delay)
N-INT-60 power-transition hysteresis vs workload transition

L. IDEAS MÁS NUEVAS PARA EL PROYECTO
N-INT-01 latency hiding, 02 load→use, 03 dependencia, 04 register lifetime, 06 scheduler-sensitive, 07 instruction-mix, 08 SGPR/VGPR, 09 temporal vs spatial, 10 memory divergence, 12 working-set×occupancy, 14 MLP, 15 latency vs bandwidth, 16 cache-capacity, 17 thrashing, 18 reuse distance, 19 compression×bandwidth, 21 overdraw, 22 Early-Z, 23 depth×shader, 24 discard, 25 primitive-size, 26 barrier scope, 27 stage-mask, 28 access-mask, 29 barrier batching, 30 barrier placement, 31 dependency direction, 33 descriptor-update, 36 pipeline-state density, 37 pipeline-cache cold/warm, 38 shader-cache cold/warm, 39 first-frame decomposition, 40 same-FPS different distributions, 42 autocorrelation, 43 stutter recurrence, 45 async complementarity, 46 interference curve, 48 allocation churn, 49 buffer packing, 51 state-change locality, 52 ceiling decomposition, 54 ceiling migration, 55 multi-ceiling Pareto, 57 DVFS by workload class, 58 energy-per-frame, 60 workload-transition×DVFS.

N-INT-61 MIGRACIÓN DE CUELLO DE BOTELLA (la más potente)
medir estado→identificar ceiling→perturbar solo ese mecanismo→medir→¿desapareció?→NO: refutar/reformular; SÍ: identificar nuevo ceiling→nueva hipótesis→repetir.
Bucle: DOC→EVIDENCIA→MODELO DE CEILINGS→BOTTLENECK→IDEACIÓN→EXPERIMENTO→PERTURBACIÓN→NUEVO BOTTLENECK→NUEVA IDEACIÓN.

N-INT-62 IGUAL TRABAJO, DISTINTA REPRESENTACIÓN (nueva línea raíz)
mismo resultado lógico, representaciones A/B distintas (muchos/pocos draws, duplicada/instancing, muchos/reutilizados descriptors, barriers amplias/precisas, command buffers pequeños/grandes, shader dependiente/scheduler-friendly, memoria localidad/no).
Pregunta: ¿qué coste depende de representación y no del trabajo lógico?

ÁRBOL SUGERIDO
RX550 → COMPUTE (latency hiding, ILP, registers, SGPR/VGPR) / MEMORY (locality, cache, MLP, residency) / PIPELINE (barriers, submission, descriptors, state changes) → GPU EXECUTION → DVFS/THERMAL/WSI → OBSERVABILITY (counters, timeline, metrics) → BOTTLENECK MIGRATION.

CONCLUSIÓN
Novedades más fuertes: latency hiding intra-wave, register lifetime, MLP, cache/reuse distance, memory divergence, barrier scope/stage/access, barrier batching, pipeline/shader-cache cold paths, first-frame causal decomposition, frame-time structure, async-compute complementarity, ceiling decomposition, bottleneck migration.
~50 líneas nuevas, no todas IDs independientes; varias forman árboles.
Muchas requieren capability audit, instrumentación o autorización.

Estas ideas son mías, del usuario. No del asistente.
```
