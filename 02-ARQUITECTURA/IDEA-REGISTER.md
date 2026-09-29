# IDEA-REGISTER — Registro de ideas originales del usuario

**ORIGIN=IDEA_ORIGINAL_USUARIO** · **AUTOR=usuario humano** · **NO_MODELO · NO_OPENCODE · NO_EXTERNO**

> Estas ideas **no son hechos, ni conclusiones, ni mejoras demostradas, ni
> hipótesis**, salvo donde una fila diga explícitamente lo contrario. Son
> propuestas de investigación. La regla del propio autor
> (`~/Escritorio/ideas.txt:171-172`):
> `IDEA → pregunta → hipótesis → experimento → optimización`, y
> **«No meter directo en registro de hipótesis»**.

| | |
|---|---|
`SOURCE_FILE` | `~/Escritorio/ideas.txt` · 21 569 B · `SHA256 d8c174f1cb2c59435b71223e…` (prefijo 24 hex) |
`COPIAS_PRESERVADAS_EN_EL_PROYECTO` | 8, **byte-idénticas** al origen, todas untracked y **0 menciones en el router**: `ideas.txt`, `00-INDICE/ideas.txt`, `01-AUDITORIA/ideas.txt`, `02-ARQUITECTURA/ideas.txt`, `03-EXPERIMENTOS/ideas.txt`, `04-IMPLEMENTACION/ideas.txt`, `05-FUENTES-EXTERNAS/ideas.txt`, `tools/ideas.txt` |
`FECHA_DE_INTEGRACION` | 2026-09-26 |
`TOTAL_IDEAS_NOMINALES` | **184** = 107 `R-NEW-*` + 15 `METH-NEW-*` + 62 `N-INT-*` |
`REVISION_ADVERSARIAL` | **Del propio autor** (`ideas.txt:180-376`). Se conserva íntegra; este registro **no la sustituye ni la reevalúa** |
`CREADO_POR` | integración documental. No añade ideas |

## Por qué este documento existe

Ninguna estructura vigente del proyecto tiene esta función:

| Documento | Función | Por qué no sirve |
|---|---|---|
`00-INDICE/HYPOTHESIS-REGISTER.md` (213 L, `8bfa7e4c`) | hipótesis H1–H12 | el autor lo prohíbe explícitamente (`ideas.txt:172`) |
`…/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md` (347 L, `efa3273c`) | candidatos de experimento | exige checklist de 8 preguntas con `Confirmación`/`Refutación`/`Riesgos`. Es un **experimento validable**, no una idea. L4: «NO ejecutar. Solo documentar» |
`02-ARQUITECTURA/open_questions.md` (25 L, `7165832a`) | preguntas abiertas | `CIERRE 2026-09-19`; contiene 5 preguntas `O-*` ya clasificadas |
`02-ARQUITECTURA/rejected_ideas.md` (26 L, `82ff4857`) | ideas refutadas | contiene `R-01..R-09`, todas con evidencia de refutación |
`02-ARQUITECTURA/hypotheses.md` (33 L, `92b6b2c6`) | hipótesis CIERRE | mismo corte temporal |
`AGENTS.md` | autoridad metodológica | `AGENTS.md:381-382` prohíbe usarlo como base de datos |

## Estructura de 5 niveles (definida por el autor, `ideas.txt:347-371`)

```
N1  MECANISMO DE IDEACIÓN      METH-NEW-01..15
N2  PREGUNTA / PROBLEMA        H1..H12 · O-* · N-INT-52..55
N3  IDEA                       R-NEW-* · N-INT-*
N4  EXPERIMENTO / MÉTRICA      R-NEW-21/56/99 · EXPERIMENT-CANDIDATES · Q1..Q7
N5  OPTIMIZACIÓN POSSIBLE      ninguna idea de este registro llega a N5
```

```
ORIGEN            CORPUS EXISTENTE              ESTE REGISTRO
─────────────────────────────────────────────────────────────────────
ideas.txt ──►  H1..H12    hipótesis        ──►  EQUIVALENT_OF  (no se mueven)
              G/M/F/S/A/P  candidatos      ──►  VARIANT_OF
              Q1..Q7      experimentos     ──►  PARENT_OF (árbol de experimentos)
              I-01..I-02  instrumentación  ──►  DERIVES_FROM
              O-*         preguntas        ──►  EQUIVALENT_OF
              W-01/P-*    Mesa/ICD         ──►  EQUIVALENT_OF
              R-01..R-09  refutadas        ──►  CONTRADICTS (si aplica)

REGLA DEL AUTOR (ideas.txt:368):
  «no crear nueva IDEA cuando solo cambia parámetro experimental,
   salvo que introduzca mecanismo causal distinto»
```

## Convenciones de relación

`EQUIVALENT_OF` misma idea · `VARIANT_OF` misma línea + dimensión/observado/discriminante
distinto · `PARENT_ID`+`CHILD_ID`+`RELATION=SUBIDEA` descomposición · `CONTRADICTS`
conflicto real · `CONTRADICTS_SCOPE_DISTINTO` ≠ refutación · `NOT_DETERMINED`
insuficiente para decidir.

---

# 1. RENDIMIENTO

| ID | Formulación original | N | Mecanismo | Corpus | Relación | Estado autor | Falta | Discriminante |
|---|---|:--:|---|---|---|---|---|---|
| `R-NEW-01` | separar throughput/geometría/fragmentos (matriz VS/FS) | N3 | descomponer | `G-01`,`G-08` | `VARIANT_OF` | `REFORMULAR` | workloads ortogonales por etapa | VS-only vs FS-only vs ambos |
| `R-NEW-02` | layers vs fragmentos | N3 | variar | `G-05`,`G-07` | `VARIANT_OF` | `REFORMULAR`→coste raster/memoria | capas no son variable causal universal | capas con tipo de layer fijo |
| `R-NEW-03` | resolución vs trabajo efectivo vs WSI/present | N3 | descomponer | `H12` | `PARENT` → 3 hijos | `DIVIDIR EN 3` | tres fenómenos distintos | render-only vs present-only |
| `R-NEW-04` | resolución vs render scale | N3 | variar | `H11` | `VARIANT_OF` | **CONSERVAR** | — | escalado de resolución con cap fijo |
| `R-NEW-05` | oversubscription de recursos shader | N3 | variar | `S-01` | `VARIANT_OF` | `CONSERVAR` si se define recurso | «oversubscription» ambiguo | recurso shader excede capacidad |
| `R-NEW-06` | barrido de intensidad aritmética | N3 | variar | — | `NUEVA` | **VERDE FUERTE** | roofline memoria-vs-cómputo | barrido ALU/FLOP |
| `R-NEW-07` | barrido de patrón de acceso a memoria | N3 | variar | — | `NUEVA` (padre) | `VERDE` | familia; 08/09/10 son subcasos | patrón secuencial vs aleatorio |
| `R-NEW-08` | reutilización de texturas | N3 | descomponer | `R-NEW-07` | `SUBIDEA(07)` | `SUBIDEA` | — | reutilización intra-frame |
| `R-NEW-09` | umbral de tamaño de textura | N3 | variar | `H6`,`M-01` | `DUPLICATE` | `REDUNDANTE` | parameter-sweep | — |
| `R-NEW-10` | umbral de cantidad de texturas | N3 | variar | `H6`,`M-01` | `DUPLICATE` | `SUBIDEA` | — | — |
| `R-NEW-11` | barrido de presión VBO/IBO | N3 | variar | `G-03` | `VARIANT_OF` | **CONSERVAR** | — | tamaño VBO/IBO |
| `R-NEW-12` | instancing vs geometría duplicada | N3 | analogía | `G-04` | `VARIANT_OF` | **CONSERVAR** como experimento, no optimización universal | — | mismo resultado lógico, distinta representación |
| `R-NEW-13` | barrido de densidad de draw calls | N3 | variar | `G-01` | `VARIANT_OF` (padre de 14/15/16/18) | **VERDE FUERTE** | — | nº draws por frame |
| `R-NEW-14` | barrido de tamaño de batch | N3 | fusionar→`13` | `R-NEW-13` | `DUPLICATE_OF(13)` | `CASI REDUNDANTE` | — | — |
| `R-NEW-15` | saturación de envío CPU | N4 | — | `R-NEW-13/14/16` | `DUPLICATE` | **NO ES IDEA. CRITERIO DE RESULTADO** | — | — |

# 2. CPU↔GPU↔ENVÍO

| ID | Original | N | Mec. | Corpus | Relación | Estado autor | Falta |
|---|---|:--:|---|---|---|---|---|
| `R-NEW-16` | mismo trabajo GPU, distinta tasa de envío CPU | N3 | variar | `R-NEW-13` | `DUPLICATE(13)` | `REDUNDANTE` | — |
| `R-NEW-17` | ritmo artificial de CPU | N3 | variar | `R-NEW-13` | `VARIANT_OF(13)` | `EXPERIMENTO AUXILIAR` | control de envío |
| `R-NEW-18` | envío por lotes vs incremental | N3 | variar | `R-NEW-13/14` | `DUPLICATE(13)` | `REDUNDANTE` | — |
| `R-NEW-19` | sensibilidad a afinidad de CPU | N3 | variar | `H4`,`H5` | `CONTRADICTS_SCOPE_DISTINTO` | `DÉBIL PARA RX550. CARACTERIZACIÓN DE ENTORNO` | no es propiedad de la GPU |
| `R-NEW-20` | sensibilidad a frecuencia de CPU | N4 | — | `H4` | `VARIANT_OF` | `AUXILIAR` | control |
| `R-NEW-21` | mapa de divergencia GPU busy/FPS | N4 | — | `H8`,`Q6` | `DERIVES_FROM` | **NO ES IDEA. MÉTRICA/CLASIFICADOR** | busy alto + FPS bajo **no** demuestra starvation |

# 3. H8 STARVATION

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-22` | distribución de duración de busy | N3 | variar | `H8` | `VARIANT_OF` | **BUENA** |
| `R-NEW-23` | correlación de fase busy/FPS | N3 | variar | `H8` | `VARIANT_OF` | **BUENA** — requiere sincronía precisa |
| `R-NEW-24` | latencia de finalización de fence | N4 | — | `H8` | `PARENT` | **BUENA** |
| `R-NEW-25` | latencia submit-to-fence | N4 | — | `H8` | `VARIANT_OF(24)` | **BUENA** — medición temporal |
| `R-NEW-26` | espera WSI vs finalización GPU | N3 | descomponer | `H8`,`H12` | `VARIANT_OF` | **MUY BUENA** — «GPU DONE ≠ PRESENT READY ≠ FRAME DISPLAYED» |

# 4. H12 PRESENTACIÓN

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-27` | workload sin present | N3 | eliminar | `H12` | `VARIANT_OF` | **MUY BUENA** |
| `R-NEW-28` | mismo render, distinto modo de presentación | N3 | variar | `H12` | `VARIANT_OF` | **BUENA** — depende del stack |
| `R-NEW-29` | barrido de frecuencia de present | N3 | variar | `H12` | `VARIANT_OF` | `AMARILLA` — acoplada a compositor/WSI |
| `R-NEW-30` | barrido de profundidad de cola de frames | N3 | variar | `H12` | `VARIANT_OF` | **BUENA** — modifica throughput y latency |
| `R-NEW-31` | triple vs doble buffering | N3 | variar | `R-NEW-30` | `VARIANT_OF(30)` | `DÉBIL/DEPENDIENTE DEL STACK` |
| `R-NEW-32` | primer frame vs estado estable | N3 | descomponer | `H4` | `PARENT` de 33 | **MUY BUENA** |

# 5. RUNTIME PM

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-33` | atribución de despertar PM en primer frame | N3 | descomponer | `H4`,`R-NEW-32` | `SUBIDEA(32)` | **BUENA** pero causalmente ambiciosa: primer frame no demuestra PM |
| `R-NEW-34` | duración idle vs latencia de despertar | N3 | invertir | `H4` | `VARIANT_OF` | **BUENA** — «mejor forma de atacar H4» |
| `R-NEW-35` | experimento de ráfagas repetidas | N3 | variar | `R-NEW-34` | `DUPLICATE(34)` | `REDUNDANTE` |
| `R-NEW-36` | caracterización de histéresis de runtime PM | N3 | variar | `H4` | `VARIANT_OF` | `SOSPECHOSA` → reformular a transición/retención de estado, no asumir histéresis |

# 6. ASPM/PCIe

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-37` | estado de enlace PCIe vs latencia de ráfaga | N3 | variar | `H5` | `PARENT` | **BUENA** — depende de observabilidad |
| `R-NEW-38` | umbral de duración de ráfaga | N3 | variar | `R-NEW-37` | `SUBIDEA(37)` | — |
| `R-NEW-39` | umbral de tamaño de transferencia | N3 | variar | `R-NEW-40` | `SUBIDEA(40)` | — |
| `R-NEW-40` | escalera de throughput PCIe | N3 | extrapolar | `H5` | `PARENT` | **BUENA** — familia PCIe burst/transfer |

# 7. VRAM/GTT/SPILLING

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-41` | escalera de working set | N3 | extrapolar | `H6`,`G-03` | `VARIANT_OF(H6)` | **MUY BUENA** — ya implícita en H6 |
| `R-NEW-42` | histéresis de presión VRAM | N3 | variar | `H6` | `VARIANT_OF` | `ESPECULATIVA` — no asumir histéresis |
| `R-NEW-43` | churn de residencia | N3 | variar | `M-03` | `VARIANT_OF` | **BUENA** — requiere observar residency |
| `R-NEW-44` | experimento de tiempo de vida de recursos | N3 | variar | `M-01` | `VARIANT_OF` | **NO ES VRAM PRESSURE. Resource-management overhead. Separar** |
| `R-NEW-45` | comparación VRAM/GTT a misma capacidad | N3 | variar | `H6`,`M-02` | `VARIANT_OF` | **MUY BUENA** |
| `R-NEW-46` | acantilado de rendimiento por spill a PCIe | N3 | invertir | `H6` | `VARIANT_OF` | **BUENA** — «cliff» es predicción fuerte; reformular a discontinuidades por spilling |

# 8. MCLK/DPM

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-47` | observador de transiciones MCLK | N3 | cambio de contexto | `H7`,`H3` | `VARIANT_OF(H7)` | **MUY BUENA** — «forma menos peligrosa de H7» (no requiere forcing) |
| `R-NEW-48` | latencia de transición MCLK | N4 | — | `H7` | `VARIANT_OF` | **BUENA** — necesita sampling suficiente |
| `R-NEW-49` | modelo de histéresis MCLK | N3 | extrapolar | `H7` | `VARIANT_OF` | `DEMASIADO PRONTO` — primero demostrar transiciones |
| `R-NEW-50` | clasificador de workload para MCLK | N3 | descomponer | `H7` | `VARIANT_OF` | **BUENA** |
| `R-NEW-51` | mapa de independencia SCLK/MCLK | N3 | variar | `H7` | `VARIANT_OF` | **BUENA** |
| `R-NEW-52` | coste de transición de clock | N3 | variar | `H3`,`H7` | `VARIANT_OF` | `DEMASIADO FUERTE` → reformular a efectos temporales |

# 9. POWER CAP

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-53` | curva de sensibilidad al cap | N3 | extrapolar | `H1` | `PARENT` de 54/55 | `FUSIONAR 53/54/55` |
| `R-NEW-54` | experimento de distancia al cap | N3 | variar | `R-NEW-53` | `SUBIDEA(53)` | — |
| `R-NEW-55` | detección de umbral de cap | N3 | invertir | `R-NEW-53` | `SUBIDEA(53)` | — |
| `R-NEW-56` | curva de eficiencia (FPS/W, work/joule) | N4 | — | `H1` | `DERIVES_FROM` | **NO ES HIPÓTESIS DE HARDWARE. MÉTRICA** — FPS/W oculta utilidad/calidad/latencia/estabilidad |
| `R-NEW-57` | equilibrio térmico dependiente del cap | N3 | variar | `R-NEW-53`,`H2` | `SUBIDEA(53)` | **BUENA** — consecuencia de 53, no independiente |

# 10. TEMPERATURA

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-58` | constante de tiempo térmica | N3 | extrapolar | `H2` | `VARIANT_OF` | **BUENA** |
| `R-NEW-59` | retardo temperatura-rendimiento | N3 | variar | `R-NEW-58` | `DERIVED_FROM(58)` | **BUENA** pero derivada |
| `R-NEW-60` | deuda térmica sin calentamiento artificial | N3 | eliminar | `H2`,`P-03` | `VARIANT_OF` | **MUY BUENA** — evita el heating `CONGELADO` |
| `R-NEW-61` | misma temperatura, distinta historia | N3 | invertir | `H2` | `NUEVA` (independiente) | **MUY INTERESANTE** — prueba path dependence |
| `R-NEW-62` | experimento de recuperación térmica | N3 | variar | `R-NEW-60/61` | `DUPLICATE` | `REDUNDANTE` |

# 11. SHADER/ACO

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-63` | barrido de ILP | N3 | variar | `S-01` | `VARIANT_OF` | **BUENA** |
| `R-NEW-64` | matriz occupancy vs ILP | N3 | variar | `S-01` | `VARIANT_OF` | **MUY BUENA** |
| `R-NEW-65` | umbral de unroll | N3 | variar | `S-02` | `SUBIDEA(63/64)` | — |
| `R-NEW-66` | barrido de ancho de precisión | N3 | variar | `S-03` | `VARIANT_OF` | **BUENA, peligrosa semánticamente** |
| `R-NEW-67` | barrido de dependencia cross-lane | N3 | variar | `S-04` | `VARIANT_OF` | **BUENA** si la operación está soportada |
| `R-NEW-68` | complejidad shader vs presión de registros | N3 | variar | `S-01` | `VARIANT_OF` | **MUY BUENA** |
| `R-NEW-69` | tradeoff compile-time vs runtime de shader | N3 | variar | `S-01` | `VARIANT_OF` | **BUENA** — lifecycle/performance engineering |

# 12. MSAA/RASTER/ROP

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-70` | curva de escalado MSAA | N3 | extrapolar | `F-02` | `VARIANT_OF` | **BUENA** |
| `R-NEW-71` | sample shading vs MSAA | N3 | descomponer | `F-01` | `VARIANT_OF` — distinta de 70 | **BUENA** |
| `R-NEW-72` | experimento de control DCC | N3 | invertir | `F-02` | `DUPLICATE` | ya implícita en F-02 |
| `R-NEW-73` | barrido de complejidad de blend | N3 | variar | `F-03` | `VARIANT_OF` | **BUENA** |
| `R-NEW-74` | barrido de formato de attachment | N3 | variar | `F-04` | `VARIANT_OF` | **BUENA** |

# 13. GRÁFICOS+CÓMPUTO

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-75` | solapamiento gráficos/cómputo | N3 | combinar | `A-01`,`H9` | `DUPLICATE_OF(A-01)` | **BUENA** — ya existe A-01 |
| `R-NEW-76` | sensibilidad al número de colas | N2 | — | `H9` | `SUBIDEA(H9)` | **PRECONDICIÓN, NO IDEA** |
| `R-NEW-77` | barrido de coste de barreras | N3 | variar | `A-01` | `VARIANT_OF` | **BUENA** |
| `R-NEW-78` | barrido de profundidad de dependencias | N3 | variar | `R-NEW-77` | `VARIANT_OF(77)` | **BUENA** — muy relacionada |
| `R-NEW-79` | frontera de utilidad de async compute | N4 | — | `A-01` | `DERIVES_FROM` | **NO INDEPENDIENTE. Criterio emergente de A-01** |

# 14. SDMA/COPY

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-80` | utilización del copy engine | N3 | variar | `M-04` | `VARIANT_OF` | **BUENA** |
| `R-NEW-81` | solapamiento copy/gráficos | N3 | combinar | `M-04`,`A-02` | `VARIANT_OF` | **BUENA** |
| `R-NEW-82` | umbral de tamaño de copy | N3 | variar | `R-NEW-80/81` | `SUBIDEA(80)` | — |

# 15. MESA/RADV/RADEONSI

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-83` | comparación Mesa por workload | N3 | variar | `H10`,`O-Mesa` | `VARIANT_OF` | **BUENA** |
| `R-NEW-84` | comparación Mesa cold-start vs steady-state | N3 | descomponer | `H10` | `VARIANT_OF` — cubre el hueco de EP-05 | **BUENA** |
| `R-NEW-85` | comparación de driver emparejada por API | N3 | invertir | `H10`,`P-011` | `VARIANT_OF` | **MUY BUENA** — evita Vulkan CUSTOM vs OpenGL STOCK |
| `R-NEW-86` | mismo workload / distinta versión Mesa | N3 | variar | `H10` | `VARIANT_OF` | **BUENA** — benchmarking de versiones |
| `R-NEW-87` | matriz de interacción de variables de entorno | N3 | combinar | `F-02` | `VARIANT_OF` | **PELIGROSA** — explosión A×B×C×D×E; seleccionar sólo con hipótesis de mecanismo |
| `R-NEW-88` | auditoría de aplicabilidad de workarounds | N4 | — | `W-01`,`P-006`,`R0-3` | `DERIVES_FROM` | **BUENA** — auditoría documental |

# 16. VULKAN

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-89` | matriz de capacidades de colas Vulkan | N2 | — | `H9`,`P-011` | `VARIANT_OF` | **MUY BUENA como capability audit. No mejora** |
| `R-NEW-90` | experimento de coste de sincronización | N3 | variar | `A-01` | `VARIANT_OF` | **BUENA** |
| `R-NEW-91` | granularidad de command buffers | N3 | variar | `R-NEW-13` | `VARIANT_OF(13)` | **BUENA** |
| `R-NEW-92` | presión de descriptor/resource-binding | N3 | variar | — | `NUEVA` | **BUENA, potencialmente enorme** |
| `R-NEW-93` | variación de pipeline-state | N3 | variar | — | `NUEVA` | **BUENA** — puede ser combinatoria explosiva |

# 17. INSTRUMENTACIÓN

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-94` | acuerdo entre múltiples observadores | N4 | — | `I-01` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-95` | caracterización de latencia de medición | N4 | — | `I-01` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-96` | sensibilidad a frecuencia de muestreo | N3 | variar | `I-01`,`H3` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-97` | experimento de overhead del observador | N3 | variar | `I-01` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-98` | alineación de timestamps | N4 | — | `I-01`,`R-NEW-23` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-99` | mapa semántico de métricas | N4 | — | `I-01`,`…ADDENDUM:33-46` | `DERIVES_FROM` | **NO ES EXPERIMENTO. Infraestructura epistemológica. Requisito/documentación** |

# 18. CONTADORES GFX8

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-100` | mapeo contador→hipótesis | N4 | — | `Q1..Q7`,`I-01` | `DERIVES_FROM` | **MUY BUENA** |
| `R-NEW-101` | análisis de redundancia de contadores | N4 | eliminar | `Q1..Q7` | `DERIVES_FROM` | **BUENA** |
| `R-NEW-102` | conjunto de falsación por contadores | N4 | invertir | `Q1..Q7` | `DERIVES_FROM` | **EXCELENTE METODOLÓGICAMENTE** — «¿qué observación distinguiría H de ¬H?» |
| `R-NEW-103` | cadena de validación física | N4 | descomponer | `I-01` | `DERIVES_FROM` | **MUY BUENA** — las 5 capas de `…ADDENDUM:85-89` |

# 19. POWER PROFILES

| ID | Original | N | Mec. | Corpus | Relación | Estado autor |
|---|---|:--:|---|---|---|---|
| `R-NEW-104` | matriz de comportamiento de perfiles | N3 | variar | `P-01` | `PARENT` | **BUENA** |
| `R-NEW-105` | latencia de transición de perfil | N3 | variar | `R-NEW-104` | `SUBIDEA(104)` | — |
| `R-NEW-106` | interacción perfil × workload | N3 | combinar | `R-NEW-104` | `SUBIDEA(104)` | — |
| `R-NEW-107` | frontera de eficiencia de perfiles | N4 | — | `P-01` | `DERIVES_FROM` | **MÉTRICA/CRITERIO** |

# 20. METH-NEW — REGLAS METODOLÓGICAS

**No son ideas sobre la RX 550.** Son reglas de ideación/evaluación (N1). No se convierten en hipótesis de hardware.

| ID | Original | Mecanismo | Estado autor | Nota de integración |
|---|---|---|---|---|
| `METH-NEW-01` | matriz de ideas | representación | `NO ES MECANISMO COMPLETO. REPRESENTACIÓN` | satisfecha por este documento |
| `METH-NEW-02` | ideación guiada por contradicciones | contradicción→idear | **MUY BUENA** | applicable a `CTR-001..007` |
| `METH-NEW-03` | inversión de resultados negativos | invertir | **BUENA** | estrategia generativa, no inferencia |
| `METH-NEW-04` | caza de fronteras | invertir | **MUY BUENA** | «una de las mejores» |
| `METH-NEW-05` | inversión de confounders | invertir | **MUY BUENA** | — |
| `METH-NEW-06` | búsqueda de variables ocultas | descomponer | **BUENA** | exigir variable+mecanismo+observabilidad |
| `METH-NEW-07` | ideación por vacío de medición | descomponer | **EXCELENTE** | aplicable a los 5 `NOT_AVAILABLE` de `…ADDENDUM` |
| `METH-NEW-08` | sustitución de modelos | analogía | **MUY BUENA** | sólo con modelos alternativos plausibles |
| `METH-NEW-09` | búsqueda de analogías entre dominios | analogía | **VÁLIDA PELIGROSA** | exigir: mecanismo fuente→isomorfismo→mecanismo candidato→predicción. **Analogía = generador, no evidencia** |
| `METH-NEW-10` | motor de recombinación | combinar | **MUY BUENA** | necesita poda por mecanismo |
| `METH-NEW-11` | inversión de parámetros | invertir | **BUENA** | el parámetro debe tener significado causal |
| `METH-NEW-12` | descomposición temporal | descomponer | **MUY BUENA** | aplicable a `R-NEW-32`, `N-INT-39` |
| `METH-NEW-13` | descomposición espacial | descomponer | **BUENA** | no todo observable con esa granularidad |
| `METH-NEW-14` | descomposición de escala | descomponer | **MUY BUENA** | aplicable a `G-03`, `R-NEW-40/41` |
| `METH-NEW-15` | perturbación sin optimización | invertir | **EXCELENTE** | «debería ser regla central del generador» |

---

# 21. N-INT — IDEAS INTERNACIONALES DEL USUARIO

`ORIGIN=IDEA_ORIGINAL_USUARIO`. Búsqueda en AMD/LLVM/Khronos/literatura GPU
(`ideas.txt:381`). Las fuentes externas son `CONTEXT`, **nunca autora**. Ninguna
de estas familias tiene equivalente en el corpus del proyecto.

## A. Microarquitectura / shader

| ID | Original | Corpus | Relación | Estado autor |
|---|---|---|---|---|
| `N-INT-01` | separar latencia oculta de throughput bruto (latency-hiding efficiency) | `S-01` | `NUEVA` | mecánica nueva |
| `N-INT-02` | distancia load→use (latency hiding intra-wave) | `S-01` | `NUEVA` | mecánica nueva |
| `N-INT-03` | dependencia artificial vs natural | `S-02` | `NUEVA` | mecánica nueva |
| `N-INT-04` | lifetime de VGPR como variable independiente (register count ≠ register lifetime) | `S-01` | `VARIANT_OF` | «register count ≠ register lifetime» |
| `N-INT-05` | trade-off ILP↔occupancy con frontera de compensación explícita | `S-01` | `VARIANT_OF` | — |
| `N-INT-06` | scheduler-sensitive shader (mismo algoritmo, distinto orden) | `S-04` | `NUEVA` | — |
| `N-INT-07` | instruction-mix sensitivity (igual FLOP, distinta mezcla) | `S-01` | `NUEVA` | — |
| `N-INT-08` | scalar/vector separation (SGPR-heavy vs VGPR-heavy) | `S-01` | `NUEVA` | — |

## B. Memoria

| ID | Original | Corpus | Relación | Estado |
|---|---|---|---|---|
| `N-INT-09` | localidad temporal vs espacial (separar R-NEW-07) | `R-NEW-07` | `REFORMULA(07)` | refactoriza |
| `N-INT-10` | divergencia de accesos dentro de wave | `R-NEW-07` | `NUEVA` | — |
| `N-INT-11` | working-set × localidad | `R-NEW-41` | `VARIANT_OF` | — |
| `N-INT-12` | working-set × wave occupancy | `R-NEW-41` | `VARIANT_OF` | — |
| `N-INT-13` | reutilización inter-wave | `R-NEW-08` | `VARIANT_OF` | — |
| `N-INT-14` | memory-level parallelism sweep | `R-NEW-06` | `VARIANT_OF` | — |
| `N-INT-15` | latencia vs bandwidth (roofline omite latency) | `R-NEW-06` | `VARIANT_OF` | — |

## C. Cachés y compresión

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-16` | cache-capacity sweep (cache-resident→pressure→memory) | `M-01` | `VARIANT_OF` |
| `N-INT-17` | cache-thrashing controlado | `M-01` | `NUEVA` |
| `N-INT-18` | cache reuse distance | `M-01` | `NUEVA` |
| `N-INT-19` | compresión vs bandwidth (DCC como reducción de tráfico, no ON/OFF) | `F-02` | `REFORMULA(F-02)` |
| `N-INT-20` | compresión × render target format | `F-04` | `VARIANT_OF` |

## D. Rasterización

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-21` | overdraw depth (1×,2×,4×,8×,16×) | `G-05` | `VARIANT_OF` |
| `N-INT-22` | Early-Z effectiveness (front-to-back vs back-to-front) | `G-05` | `NUEVA` |
| `N-INT-23` | depth complexity × shader cost | `G-07` | `VARIANT_OF` |
| `N-INT-24` | primitive discard efficiency (hipótesis a validar, no asumir) | `G-02` | `VARIANT_OF` — no asumir |
| `N-INT-25` | small primitive amplification (triángulos grandes vs muchos pequeños) | `G-02` | `VARIANT_OF` |

## E. Sincronización

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-26` | barrier scope minimization (global vs resource-specific) | `A-01` | `VARIANT_OF` |
| `N-INT-27` | stage-mask precision (ALL_COMMANDS→ALL_GRAPHICS→specific) | `A-01` | `NUEVA` |
| `N-INT-28` | access-mask precision (stage scope vs access scope) | `A-01` | `NUEVA` |
| `N-INT-29` | barrier batching (10 separadas vs 1 DependencyInfo con 10) | `R-NEW-77` | `VARIANT_OF` |
| `N-INT-30` | barrier placement distance (producer→barrier→consumer) | `R-NEW-78` | `VARIANT_OF` |
| `N-INT-31` | dependency direction (vertex→fragment, fragment→vertex, compute→graphics, graphics→compute) | `A-01` | `NUEVA` |
| `N-INT-32` | barrier necessity audit (qué dependencia protege cada barrier) | `R-NEW-77` | `VARIANT_OF` |

## F. CPU/API

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-33` | descriptor-update pressure | `R-NEW-92` | `VARIANT_OF` |
| `N-INT-34` | descriptor reuse (nuevo cada frame vs reutilizado) | `R-NEW-92` | `VARIANT_OF` |
| `N-INT-35` | descriptor update × draw-call density | `R-NEW-92`+`13` | `VARIANT_OF` — cruza dos familias |
| `N-INT-36` | pipeline-state change density | `R-NEW-93` | `VARIANT_OF` |
| `N-INT-37` | pipeline cache cold/warm | `R-NEW-69` | `VARIANT_OF` |
| `N-INT-38` | shader cache cold/warm (separar pipeline/shader/fs/runtime) | `R-NEW-69` | `VARIANT_OF` |
| `N-INT-39` | first-frame causal decomposition (PM wake, shader comp, pipeline creation, descriptor alloc, resource upload, WSI) — MUY FUERTE | `R-NEW-32/33` | `REFORMULA` — **MUY FUERTE** |

## G. Frame pacing

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-40` | mismo FPS medio, distinta distribución (16,16,16 vs 8,8,8,40) | `H3` | `VARIANT_OF` |
| `N-INT-41` | p50/p90/p95/p99/max decomposition | `H3`,`Q6` | `VARIANT_OF` |
| `N-INT-42` | frame-time autocorrelation (independientes, periódicos, burst-like, correlacionados) | `H3` | `NUEVA` |
| `N-INT-43` | stutter recurrence interval | `H3` | `NUEVA` |
| `N-INT-44` | frame pacing vs GPU utilization (mismo gpu_busy promedio, distinta distribución) | `H8`,`R-NEW-21` | `VARIANT_OF` |

## H. Async compute

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-45` | async-compute complementarity (qué carga gráfica deja recursos utilizables) | `A-01` | `VARIANT_OF` |
| `N-INT-46` | async compute interference curve (10%,25%,50%,75%,100%) | `A-01` | `VARIANT_OF` |
| `N-INT-47` | complementarity map (beneficial, neutral, interfering) | `A-01` | `DERIVES_FROM` |

## I. Descriptor/pipeline/resource

| ID | Original | Corpus | Relación |
|---|---|---|---|
| `N-INT-48` | resource allocation churn (GPU execution vs allocation/free) | `R-NEW-44` | `REFORMULA(44)` |
| `N-INT-49` | buffer packing (mismo payload, distintas estrategias) | `M-03` | `VARIANT_OF` |
| `N-INT-50` | per-object update vs batched update | `R-NEW-18` | `VARIANT_OF` |
| `N-INT-51` | state-change locality (random vs state-grouped) | `R-NEW-93` | `VARIANT_OF` |

## J. Performance ceilings

| ID | Original | Corpus | Relación | Estado |
|---|---|---|---|---|
| `N-INT-52` | ceiling decomposition (matemático→memoria→occupancy→submission→sync→WSI) | `R-NEW-06/41` | `NUEVA` | — |
| `N-INT-53` | distance-to-ceiling (achieved/theoretical) | `R-NEW-56` | `VARIANT_OF` | — |
| `N-INT-54` | ceiling migration (memory-bound→compute-bound→sync-bound→WSI-bound) — MUY FUERTE | — | `NUEVA` | **MUY FUERTE** |
| `N-INT-55` | multi-ceiling Pareto map (performance, power, thermal, latency, stability) | `R-NEW-56` | `VARIANT_OF` | — |

## K. DVFS

| ID | Original | Corpus | Relación | Estado |
|---|---|---|---|---|
| `N-INT-56` | frequency response curve (frequency→performance,power,energy,temp) | `H1`,`H3` | `VARIANT_OF` | — |
| `N-INT-57` | frequency sensitivity by workload class (compute/memory/latency/WSI-bound) | `H1` | `VARIANT_OF` | — |
| `N-INT-58` | energy-per-frame (no FPS/W) | `R-NEW-56` | `REFORMULA(56)` | métrica mejor |
| `N-INT-59` | energy-delay product (EDP=Energy×Delay) | `R-NEW-56` | `NUEVA` | — |
| `N-INT-60` | power-transition hysteresis vs workload transition | `H7`,`H3` | `VARIANT_OF` | — |

## L. Raíces nuevas

| ID | Original | Corpus | Relación | Estado autor |
|---|---|---|---|---|
| `N-INT-61` | **MIGRACIÓN DE CUELLO DE BOTELLA** | — | `NUEVA` (raíz) | **LA MÁS POTENTE**. Bucle: medir→identificar ceiling→perturbar solo ese mecanismo→medir→¿desapareció?→NO: refutar/reformular; SÍ: nuevo ceiling→nueva hipótesis |
| `N-INT-62` | **IGUAL TRABAJO, DISTINTA REPRESENTACIÓN** | `R-NEW-12` | `NUEVA` (raíz) | «¿qué coste depende de representación y no del trabajo lógico?» |

## Árbol sugerido por el autor

```
RX550
 ├─ COMPUTE    latency hiding · ILP · registers · SGPR/VGPR      N-INT-01..08
 ├─ MEMORY     locality · cache · MLP · residency               N-INT-09..20
 ├─ PIPELINE   barriers · submission · descriptors · state       N-INT-26..38, 49..51
 ├─ GPU EXECUTION
 ├─ DVFS/THERMAL/WSI                                           N-INT-40..47, 56..60
 ├─ OBSERVABILITY  counters · timeline · métricas               R-NEW-94..103
 └─ BOTTLENECK MIGRATION                                        N-INT-61
```

## Diagrama — flujo de una idea

```
IDEA (R-NEW-47 / N-INT-39 / …)
   │  ORIGIN=IDEA_ORIGINAL_USUARIO
   ▼
PREGUNTA  ── ¿qué observers separan H de ¬H? ──  (METH-NEW-02, METH-NEW-04)
   ▼
HIPÓTESIS ── sólo tras esa pregunta; NO antes
   │         destino: 00-INDICE/HYPOTHESIS-REGISTER.md  (NO este documento)
   ▼
EXPERIMENTO ─ checklist de 8 preguntas
   │         destino: 02-ARQUITECTURA/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md
   ▼
OBSERVACIÓN ── sólo tras ejecución autorizada
   │            destino: 01-AUDITORIA/ (artefactos de ejecución)
   ▼
CONCLUSIÓN  ── causalidad o correlación, declarada como tal
   ▼
OPTIMIZACIÓN ── ninguna idea de este registro ha llegado aquí
```

---

# CONTRADICCIONES

Registradas, **no resueltas** (regla del prompt: no inventar síntesis).

| ID | Afirmación A | Afirmación B | Scope | Tipo | Evidencia para resolver |
|---|---|---|---|---|---|
`CTD-01` | `R-NEW-19` «sensibilidad a afinidad de CPU» es una idea de la RX 550 | el autor lo marca `DÉBIL PARA RX550. CARACTERIZACIÓN DE ENTORNO` | propiedad del host, no de la GPU | `DIFFERENT_SCOPE` | — |
`CTD-02` | `H8` `gpu_busy=100%`+starvation = `REQUIRES EXPERIMENT` | master la resume como «gating descartado» | registro H1–H12 vs `MASTER-RESEARCH-STATUS` | `CONTRADICTION` abierta | `02-HIPOTESIS-H1-H12.md` CONFLICTS lo preserva |
`CTD-03` | `H1`/`H2` locales de fases | `H1`/`H2` de proyecto | alcance de ID | `DIFFERENT_SCOPE` | `HYPOTHESIS-REGISTER.md:20-22` prohíbe fusionarlos |
`CTD-04` | `R-NEW-53/54/55` = 3 ideas | el autor: `FUSIONAR` = 1 | granularidad | `REFACTOR` (no pérdida) | — |
`CTD-05` | `R-NEW-09/10` ideas propias | `H6`/`M-01` ya cubren el barrido | Corpus vs usuario | `DUPLICATE` | — |
`CTD-06` | `R-NEW-36` histéresis de runtime PM | `R-NEW-42` histéresis VRAM | el autor marca ambas `ESPECULATIVA`/`SOSPECHOSA`: no asumir histéresis | `NOT_DETERMINED` | observación de transiciones |
`CTD-07` | `R-NEW-15` = idea | `R-NEW-15` = criterio de resultado | nivel N3 vs N4 | `REFACTOR` | — |
`CTD-08` | `R-NEW-56` FPS/W como métrica | `N-INT-58` energy-per-frame, `N-INT-59` EDP | métrica de eficiencia | `REFORMULA` | — |

# NOT_DETERMINED

| ID | Cuestión | Falta |
|---|---|---|
`ND-01` | ¿cuál de las 184 ideas es `NUEVA` vs `VARIANT_OF` en casos de mecanismo compartido? | análisis por mecanismo de `S-01`, `A-01`, `M-04`: los `.md` del corpus no documentan el mecanismo interno, sólo el objetivo |
`ND-02` | prioridad relativa entre `R-NEW-*` y `N-INT-*` | ninguna fuente la define; el autor da prioridad **dentro** de cada bloque, no entre bloques |
`ND-03` | si `N-INT-*` requiere autorización privilegiada por caso | depende de cada experimento; no evaluado |
`ND-04` | equivalencia exacta `N-INT-52` (ceiling decomposition) ↔ `FASE-D` `Q1..Q7` | `FASE-D-ETAPA-3-PLAN.md:51-68` no usa el término «ceiling» |

# CONTROL DE COMPLETITUD

```
ideas.txt → 184 IDs nominales
          → 184 filas con destino en este documento   184/184
          → los 107 R-NEW conservan formulación original  107/107
          → los 15 METH-NEW conservan formulación         15/15
          → los 62 N-INT conservan formulación            62/62
          → todas marcadas ORIGIN=IDEA_ORIGINAL_USUARIO
          → 0 convertidas en hipótesis, hechos ni mejoras
          → 8 contradicciones registradas, 0 resueltas
          → 4 NOT_DETERMINED con evidencia faltante nombrada
          → 0 borradas, 0 fusionadas sin trazar DUPLICATE_OF/PARENT_ID
          → la revisión adversarial del autor se conserva íntegra
          → 0 ideas nuevas generadas por esta integración
```

# RELACIÓN CON EL CORPUS

| Corpus | Dónde vive | Ideas del usuario que lo tocan |
|---|---|---|
`H1..H12` | `00-INDICE/HYPOTHESIS-REGISTER.md`, `00-INDICE/DIAGRAMAS/02-HIPOTESIS-H1-H12.md` | `R-NEW-01..107`, `N-INT-01..62` |
`G-01..08` | `…/POLARIS12-MAP/EXPERIMENT-CANDIDATES.md:26-119` | `R-NEW-01/02/11/12/13`, `N-INT-21..25` |
`M-01..04` | `…:120-164` | `R-NEW-41..46`, `N-INT-16..20,49` |
`F-01..04` | `…:165-204` | `R-NEW-70..74`, `N-INT-19,20` |
`S-01..04` | `…:205-244` | `R-NEW-63..69`, `N-INT-01..08` |
`A-01..02` | `…:245-264` | `R-NEW-75..79`, `N-INT-26..32,45..47` |
`P-01..03` | `…:265-291` (`P-02/03` `CONGELADO`) | `R-NEW-104..107` |
`Q1..Q7` | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PLAN.md:51-68` | `R-NEW-100..103` |
`I-01..I-02` | `02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md` | `R-NEW-94..103` |
`O-PHY/O-MCLK/O-BOT/O-Mesa/O-FPS/O-ROOT` | `02-ARQUITECTURA/open_questions.md` | `R-NEW-45`, `R-NEW-47`, `R-NEW-83` |
`W-01`, `P-006`, `P-011` | `05-FUENTES-EXTERNAS/…/R0-3-…`, `PATCH-REGISTRY-FINAL.md:38,43` | `R-NEW-88` |
`R-01..R-09` | `02-ARQUITECTURA/rejected_ideas.md:6-26` | ninguna: `R-NEW-*` no contradice ninguna refutación |
`METH-NEW-*` | **este documento** | — |

# PROBLEMAS DOCUMENTALES DETECTADOS

| # | Problema | Evidencia | Estado |
|---|---|---|---|
`PD-01` | el fichero fuente está **duplicado 8×** dentro del proyecto, byte-idéntico | 8 × `d8c174f1cb2c59435b71223e` 21569 B | preservado, **no eliminado** |
`PD-02` | las 8 copias son `.txt` y **ninguna** está en el router | `grep` router = 0 para las 8 | este documento las referencia |
`PD-03` | `tools/ideas.txt` está en un directorio de herramientas: ubicación semánticamente incorrecta | — | reportado, no movido |
`PD-04` | el fichero no tiene metadatos (sin `ORIGIN`, fecha, ni relación con el corpus) | — | resuelto por este documento |
`PD-05` | `~/Escritorio/ideas` no existe; sólo `ideas.txt` | — | reportado |

# DERIVACIÓN A LÍNEAS DE INVESTIGACIÓN

**Añadido 2026-09-28.** Sección de navegación. **No mueve, reordena, reescribe ni
elimina ninguna de las 184 filas anteriores.** Su único propósito es declarar dónde
vive la jerarquía y cómo se recorre en ambos sentidos.

## Contrato entre los dos documentos

| Documento | Rol | Fuente de verdad de |
|---|---|---|
`02-ARQUITECTURA/IDEA-REGISTER.md` (**este**) | **inventario plano y completo** | los **184 IDs**, su formulación original y su estado declarado por el autor |
`02-ARQUITECTURA/RESEARCH-LINES.md` | **router jerárquico** | las **13 líneas raíz**, su mecanismo candidato, predicción, falsador, experimentos, estado y bloqueo |

Recorrido en ambos sentidos:

```
IDEA-ID → clasificación → línea raíz/sublínea → mecanismo → predicción → experimento
        → observable → falsador → estado → bloqueo/dependencia → evidencia documental
```
y, inversamente, desde cualquier línea raíz hasta cada ID que la compone.

## Garantías de la derivación

- **184/184 IDs presentes** en este documento y en `RESEARCH-LINES.md`. Verificado
  por comparación de conjuntos: idénticos, 0 huérfanos, 0 duplicados.
- La derivación **no elimina ideas**. Reordena el corpus; no descarta nada.
- La derivación **no convierte ningún ID en hipótesis**. Una idea clasificada como
  `ROOT_LINE` sigue siendo exactamente lo que era: una pregunta sin responder. El
  orden `IDEA → PREGUNTA → HIPÓTESIS → EXPERIMENTO` de este documento
  (ver *Diagrama — flujo de una idea*) sigue vigente, y la hipótesis se crea sólo
  cuando un experimento produzca evidencia que la justifique.
- La derivación **no cambia el nivel de evidencia** de ningún ID. Clasificar un ID
  como `METRIC`, `INSTRUMENT` o `ALREADY_CLOSED_REFUTED` es una decisión
  documental, no un resultado experimental.
- Ninguna línea de `RESEARCH-LINES.md` ha alcanzado `OBSERVATION`.

## Tabla de derivación (compacta)

El detalle fila por fila de los 184 IDs —clasificación, línea, sublinea,
experimento, estado, justificación y procedencia— está en
`02-ARQUITECTURA/RESEARCH-LINES.md` §4, y **no se duplica aquí**.

| ID range | → CLASSIFICATION | → RESEARCH-LINE | → DESTINATION |
|---|---|---|---|
`R-NEW-01..07` | EXPERIMENT | L6, L4, L1 | `RESEARCH-LINES.md` §4 filas 01–07; E14, E12, E1 |
`R-NEW-08..10` | REDUNDANT | L3 | fusionados en E7/E8 |
`R-NEW-11` | EXPERIMENT | L3 | E8 |
`R-NEW-12..13` | EXPERIMENT | L1 | E1 |
`R-NEW-14` | REDUNDANT | — | `FUSIONAR_EN_E1` |
`R-NEW-15` | METRIC | — | §3; el autor ya lo declaraba «NO ES IDEA» |
`R-NEW-16` | REDUNDANT | — | `FUSIONAR_EN_E2` |
`R-NEW-17` | EXPERIMENT_AUXILIARY_CONTROL | L2 | control de E5 |
`R-NEW-18` | REDUNDANT | — | `FUSIONAR_EN_E2` |
`R-NEW-19..20` | EXPERIMENT_AUXILIARY_CONTROL | — / L2 | caracterización de entorno; control de E5 |
`R-NEW-21` | METRIC | — | §3; «NO ES IDEA. MÉTRICA/CLASIFICADOR» |
`R-NEW-22..25` | EXPERIMENT | L2 | E5 |
`R-NEW-26` | EXPERIMENT | L9 | E21, `BLOCKED` por B-02 |
`R-NEW-27..31` | EXPERIMENT | L9 | E21, `BLOCKED` por B-02 |
`R-NEW-32` | EXPERIMENT | L11 | E24 |
`R-NEW-33..34` | EXPERIMENT | L11 | E25 |
`R-NEW-35` | REDUNDANT | — | `FUSIONAR_EN_E34` |
`R-NEW-36` | EXPERIMENT | L11 | E25; `CTD-06` no asumir histéresis |
`R-NEW-37..40` | EXPERIMENT | L3b (subline de L3) | E11 |
`R-NEW-41..46` | EXPERIMENT | L3 | E8; E9 `BLOCKED` por B-04; E10 |
`R-NEW-47..52` | EXPERIMENT | L8 | E20; `INVESTIGATION_REQUIRED` |
`R-NEW-53..55`, `R-NEW-57` | ALREADY_CLOSED_REFUTED | L8 | §7; refutado por M1 y EP-06 |
`R-NEW-56` | METRIC | — | sustituida por `N-INT-58`/`N-INT-59` |
`R-NEW-58..61` | EXPERIMENT | L8 | E20 |
`R-NEW-62` | REDUNDANT | — | `FUSIONAR_EN_E60_E61` |
`R-NEW-63..65` | EXPERIMENT / REDUNDANT | L4 | E12, `BLOCKED` por B-01 |
`R-NEW-66..68` | EXPERIMENT | L5 | E13, `BLOCKED` por B-01 |
`R-NEW-69` | EXPERIMENT | L11 | E24 |
`R-NEW-70..71`, `R-NEW-73..74` | EXPERIMENT | L6 | E15 |
`R-NEW-72` | REDUNDANT | — | `FUSIONAR_EN_E15` |
`R-NEW-75` | REDUNDANT | L10 | `FUSIONAR_EN_E22` |
`R-NEW-76` | PRECONDITION | — | §3; «PRECONDICIÓN, NO IDEA» |
`R-NEW-77..78` | EXPERIMENT | L7 | E17, E18 |
`R-NEW-79` | METRIC | — | §3; criterio emergente de A-01 |
`R-NEW-80..81` | EXPERIMENT | L10 | E23 |
`R-NEW-82` | REDUNDANT | L10 | `FUSIONAR_EN_E23` |
`R-NEW-83` | EXPERIMENT | L9 | E21 |
`R-NEW-84` | EXPERIMENT | L11 | E24 |
`R-NEW-85..86` | EXPERIMENT | L1 | E1 |
`R-NEW-87` | REDUNDANT | — | barrido combinatorio; «PELIGROSA» |
`R-NEW-88` | INSTRUMENT | — | auditoría documental |
`R-NEW-89` | PRECONDITION | — | capability audit |
`R-NEW-90` | EXPERIMENT | L7 | E17 |
`R-NEW-91` | EXPERIMENT | L1 | E2; `SHARED_EXPERIMENT` con L2 |
`R-NEW-92..93` | EXPERIMENT | L1 | E4 |
`R-NEW-94..98` | INSTRUMENT | — | §3 |
`R-NEW-99` | INSTRUMENT | — | «NO ES EXPERIMENTO» |
`R-NEW-100..101`, `R-NEW-103` | INSTRUMENT | — | dependen de B-01 |
`R-NEW-102` | METHOD_RULE | — | falsación por contadores |
`R-NEW-104..106` | EXPERIMENT | L8 | E20 |
`R-NEW-107` | METRIC | — | §3 |
`N-INT-01..03`, `N-INT-05`, `N-INT-14..15` | EXPERIMENT | L4 | E12, `BLOCKED` por B-01 |
`N-INT-04`, `N-INT-06..08` | EXPERIMENT | L5 | E13, `BLOCKED` por B-01 |
`N-INT-09..13`, `N-INT-16..18`, `N-INT-48` | EXPERIMENT | L3 | E8, E10 |
`N-INT-19..20` | EXPERIMENT | L6 | E15 |
`N-INT-21..25` | EXPERIMENT | L6 | E14, E16 |
`N-INT-26..32` | EXPERIMENT | L7 | E17, E18 |
`N-INT-33..36` | EXPERIMENT | L1 | E4 |
`N-INT-37..39` | EXPERIMENT | L11 | E24 |
`N-INT-40..43` | EXPERIMENT | L9 | E21, `BLOCKED` por B-02 |
`N-INT-44` | EXPERIMENT | L2 | E5 |
`N-INT-45..47` | EXPERIMENT | L10 | E22 |
`N-INT-49..51` | EXPERIMENT | L1 | E3, E4 |
`N-INT-52`, `N-INT-54`, `N-INT-61` | METHOD_RULE | L12 | E26; `METHOD` |
`N-INT-53`, `N-INT-55`, `N-INT-58`, `N-INT-59` | METRIC | — | §3 |
`N-INT-56..57` | EXPERIMENT | L8 | E19, `BLOCKED` por B-03 y B-08 |
`N-INT-60` | EXPERIMENT | L8 | E20 |
`N-INT-62` | EXPERIMENT | L1 | E1; raíz declarada por el autor |
`METH-NEW-01..15` | METHOD_RULE | — | §3; no son ideas sobre la RX 550 |

## Recuento por clase

Verificado mecánicamente sobre las 184 filas de `RESEARCH-LINES.md` §4, contando
la columna `NEW_CLASSIFICATION`. Suma exacta: **184**.

| `NEW_CLASSIFICATION` | IDs | Nota |
|---|---:|---|
`EXPERIMENT` | 123 | pregunta científica con experimento asignado |
`METHOD_RULE` | 19 | 15 `METH-NEW` + `R-NEW-102` + `N-INT-52`/`N-INT-54`/`N-INT-61` |
`REDUNDANT` | 13 | fusionables, con destino declarado |
`INSTRUMENT` | 10 | no son preguntas científicas |
`METRIC` | 9 | el autor ya lo declaraba así en 6 de ellas |
`ALREADY_CLOSED_REFUTED` | 5 | `R-NEW-53..55`, `R-NEW-57`, `R-NEW-60` |
`EXPERIMENT_AUXILIARY_CONTROL` | 3 | `R-NEW-17`, `R-NEW-19`, `R-NEW-20` |
`PRECONDITION` | 2 | `R-NEW-76`, `R-NEW-89` |
**Total** | **184** | |

De los 184: **147** tienen `ROOT_LINE` no vacío (pertenecen a una de las 13 líneas
raíz) y **37** no tienen línea, con la razón declarada fila a fila en
`RESEARCH-LINES.md` §4. De los 13 `REDUNDANT`, 6 conservan línea de destino
(`R-NEW-08`, `R-NEW-09`, `R-NEW-10`, `R-NEW-65`, `R-NEW-75`, `R-NEW-82`) y 7 se
fusionan sin línea propia.

`LIMITATION`: `NEW_CLASSIFICATION` y `ROOT_LINE` son ejes **ortogonales**: un ID
puede ser `EXPERIMENT` de una línea y simultáneamente funcionar como `FALSIFIER` de
otra, sin que la tabla lo refleje. La fuente única y no ambigua es la fila
completa de `RESEARCH-LINES.md` §4.

## Estado de las contradicciones tras la derivación

Ninguna contradicción se resuelve. `CTD-04`, `CTD-05`, `CTD-07` y `CTD-08` cambian
de estado a `RESOLVED_BY_RECLASSIFICATION`, que es estrictamente menor que
`RESOLVED`: reordenar el corpus no aporta evidencia. `CTD-01`, `CTD-02`, `CTD-03` y
`CTD-06` permanecen abiertas, y `CON-01`, `CON-02`, `CON-03` y `GAP-09` permanecen
abiertas. Detalle en `RESEARCH-LINES.md` §7.

# LÍMITES

- `PD-01` no se corrige: eliminar 7 copias es borrar evidencia sin autorización.
- Este documento **no prioriza** ideas: el autorcompetition de prioridad es suyo.
- `ND-01..ND-04` quedan abiertos: no se resolvieron por inferencia.
- Ninguna idea fue elevada a hipótesis, experimento, evidencia ni mejora.
- `AGENTS.md` **no modificado**.
