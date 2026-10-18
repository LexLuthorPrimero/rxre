# RXRE: investigar mecanismos para construir cuerpo, mente, alma y los cinco elementos

La búsqueda debe ir más allá de los prompts de agentes convencionales. Para RXRE, interesa encontrar mecanismos que permitan a una IA percibir su entorno técnico, construir modelos causales, actuar sobre sistemas reales, conservar experiencia útil, adaptarse y descubrir trabajo que todavía no sabe que necesita hacer.

La hipótesis de trabajo es que los ocho principios podrían materializarse mediante una combinación de mecanismos de distintas disciplinas: sistemas autónomos, memoria evolutiva, control por retroalimentación, causalidad, teoría de la información, recuperación después de fallos, grafos de conocimiento y experimentación automática.

No conviene implementar todo eso de golpe. Primero hay que identificar proyectos existentes, estudiar sus mecanismos concretos y determinar cuáles encajan con RXRE sin duplicar capacidades ni crear complejidad innecesaria.

## 1. Repositorios que vale la pena estudiar

Estos proyectos aportan mecanismos concretos. No todos sirven para integrarlos directamente en RXRE; algunos son referencias de diseño y otros podrían aportar componentes reutilizables.

[Karpathy Let an Agent Tune His Code. It Found 20 Things He Missed.](https://images.openai.com/static-rsc-4/yjAmWAsQLnFKX9TZIzmFJgByCJJomU7MOix2jXfhmsujiegI9LHOqNw83R3p-TJG7OGnRBxkVhy4PkieYMtB1ymYrYLm4guBTuStTaOC9czIjwalsBP1PaJaMHvTuySxeVO2wcmwdfU-cY83pSDtCDvAe9nMGIzaEbosst8nhNk?purpose=inline)

1\. AutoResearch — experimentación autónoma

Prioridad alta

Repositorio: [karpathy/autoresearch](https://github.com/karpathy/autoresearch)

La IA modifica una parte del sistema, ejecuta un experimento acotado, mide el resultado y conserva o descarta el cambio según la evidencia. Su idea más interesante es tratar el programa de investigación como algo que puede evolucionar mediante ciclos experimentales.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Aplicación a RXRE: que cada mejora propuesta tenga una hipótesis, un experimento, una comparación contra el estado inicial y un criterio explícito de aceptación.

[Voyager, Embodied Agent with LLM 톺아보기](https://images.openai.com/static-rsc-4/Uq_peQogbtJDy5xjyVI0JU8Gzbmcrv7NQ-Mh5NhVMNDWuienjo6Ia-K4mokS-Ei8BzQ4LIYTwogxkV7fgbC26DFPeBLEuzGUc_pYyHxnDagkp3YKmub3iCE69JAphefEOq7LigdhAxWwsOLB7RyzwI7zTRWE2CPikFaYObAXVs0?purpose=inline)

2\. Voyager — aprendizaje acumulativo de habilidades

Repositorio: [MineDojo/Voyager](https://github.com/MineDojo/Voyager)

Combina exploración, objetivos progresivos, una biblioteca de habilidades ejecutables y retroalimentación del entorno. Las habilidades adquiridas pueden reutilizarse y combinarse en tareas posteriores.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Aplicación a RXRE: transformar procedimientos técnicos exitosos en habilidades reutilizables, con precondiciones, entradas, salidas, pruebas y condiciones de fallo. No volver a descubrir la misma solución en cada tarea.

[Memory in Language Model-Enabled Agents](https://images.openai.com/static-rsc-4/Y-jzq4bFRW_ahosRBapJKXDM1ntb4-WhGX6rU041W-wRzDUZNabdBdrDklLY0Qopg3WkyOogR1nE4nMt1czoSbDOebI0WmanPB6oz8DSTr_LonOWqKEm2Nz9dyw2eH9EalkJsmjzy421WqtebrSTTGV7_ML4tp2mCjFG_W0bAIQ?purpose=inline)

3\. Reflexion — aprendizaje a partir del fracaso

Repositorio: [noahshinn/reflexion](https://github.com/noahshinn/reflexion)

Emplea retroalimentación sobre los resultados y reflexiones verbales que ayudan a orientar intentos posteriores.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Aplicación a RXRE: no registrar solamente que una operación falló, sino qué hipótesis resultó incorrecta, qué condición causó el fallo y qué debería cambiar en el siguiente intento.

[Stateful AI Agents: A Deep Dive into Letta (MemGPT) Memory Models | by piyush jhamb | Feb, 2026 | Medium](https://images.openai.com/static-rsc-4/eS6RmKuCfJ_vtp_WnPXD8S5YpGTmrbhPulnz94S_khZAPX_SNHx_VmQ5YtlF_rX674BPtvWQSPcFZiRQfXXMrdOyyZQ8q0H36UDFi2Ba83vxL7yccp_H6HNHT6QVlWyYgLDsXFugRCxnsezWRzMa04y83rUbh_OcoMu6ie68KPg?purpose=inline)

4\. Letta / MemGPT — memoria persistente del agente

Repositorio: [letta-ai/letta](https://github.com/letta-ai/letta)

Su enfoque separa la memoria de trabajo de la memoria duradera y permite construir agentes con estado persistente.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Aplicación a RXRE: mantener una identidad operativa coherente entre sesiones, con objetivos, decisiones previas, conocimientos verificados, errores conocidos y asuntos pendientes, sin mezclar hechos con hipótesis.

[LangGraph 入门：用图结构构建你的第一个多智能体工作流_数据库_DYuW5gBmH-2048 AI社区](https://images.openai.com/static-rsc-4/rt5K06q5jqyK1adHGULz_QyAjljGIuOgW5ruDjAswD4QZ-bDrVKte_dBKA7VoFA-t3CiEqyEMd5Tg-QoS_GbsCjpHICB0Ap4gp_4XEX95owkkGeL-s0UdF5JN-GhPAFZxGRdJsfkKvfRgxiVB1b1_hbWoXtZrKmUYcqXeC-lASA?purpose=inline)

5\. LangGraph — continuidad y recuperación

Repositorio: [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)

Proporciona persistencia de estados, checkpoints, ejecución durable y pausas con intervención humana.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



Aplicación a RXRE: recuperar el trabajo después de una interrupción sin repetir efectos secundarios, perder hallazgos o confundir una operación iniciada con una completada.

[How to stop your autoresearch loop from cheating](https://images.openai.com/static-rsc-4/dQLbWmr0Y_8FzN2s1Qk5g_PejQg72v_T-KOUyiG9WbnxEKYFa7rvI_fQ_uZV39RBFeMFwnO62q3yVd2RYkTmdZLOH9ufSG6jKlP4_gdx4DHqSrTQlSLdZZmyRlvxHH08Dlh7EsRzZ1H6jUyIYviTif_yFEgZY4fykN09c0HyePc?purpose=inline)

6\. AutoResearch-AI — infraestructura para investigar

Repositorio: [vukrosic/autoresearch-ai](https://github.com/vukrosic/autoresearch-ai)

Organiza objetivos, líneas de base, hipótesis, propuestas de experimentos, métricas, registros y continuidad del trabajo. También distingue la generación de propuestas de su evaluación.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

vukrosic/autoresearch-ai · GitHub



Aplicación a RXRE: investigar sistemáticamente las limitaciones del propio proyecto sin depender de que la IA recuerde espontáneamente todo lo que queda por hacer.

### Qué tienen en común

Estos proyectos apuntan a una conclusión importante: un agente más capaz no se obtiene simplemente haciéndolo reflexionar más. Se obtiene construyendo un circuito entre estado, observación, hipótesis, acción, resultado, memoria y nueva decisión.

RXRE podría aprovechar esa idea sin adoptar ninguno de estos frameworks íntegramente.

## 2. Métodos menos convencionales que podrían cambiar RXRE

Aquí es donde investigaría más allá de los frameworks habituales.

A. Homeostasis computacional: el cuerpo

En biología, un organismo regula su estado interno. Una analogía técnica sería que RXRE mantenga variables de control para saber si su proceso de investigación está funcionando.

Por ejemplo:

- Integridad de los artefactos.
- Porcentaje de afirmaciones importantes respaldadas por evidencia.
- Cantidad de hipótesis abiertas sin experimentos discriminantes.
- Tiempo consumido sin obtener información nueva.
- Errores recurrentes y pérdida de contexto.
- Riesgo de interferencia con trabajo activo.

Mecanismo propuesto: un monitor calcula indicadores a partir de eventos reales y activa respuestas concretas cuando detecta desviaciones. Si la evidencia es insuficiente, prioriza inspección; si se repite un fallo, revisa la causa; si no hay información nueva, cambia de estrategia.

No se trata de fingir sensaciones, sino de implementar autorregulación basada en mediciones.

B. Memoria por consecuencias: la mente

En vez de guardar conversaciones enteras, RXRE podría mantener un registro estructurado de experiencias técnicas:

- Situación inicial.
- Predicción.
- Acción ejecutada.
- Resultado observado.
- Causa identificada.
- Condiciones en las que la solución funciona.
- Condiciones en las que deja de funcionar.
- Evidencia que permitiría refutar la conclusión.

Mecanismo propuesto: recuperar experiencias por semejanza causal y condiciones de aplicación, no solamente por similitud textual.

Esto permitiría distinguir dos problemas que parecen iguales en una descripción, pero tienen causas diferentes.

C. Función de valor global: el alma

Un agente puede terminar muchas tareas sin contribuir al objetivo general. Para evitarlo, RXRE podría evaluar cada acción según:

- Relevancia para los objetivos establecidos.
- Solidez de la evidencia.
- Impacto técnico esperado.
- Coste de investigación.
- Riesgo de regresión.
- Dependencias que desbloquea.
- Reducción de incertidumbre.

Mecanismo propuesto: priorizar el trabajo por utilidad global y evidencia, no por facilidad, novedad superficial o cantidad de archivos modificados.

La función de valor debe derivarse de los objetivos reales del proyecto, no inventarse de forma autónoma.

D. Grafo de procedencia: la tierra

Cada afirmación técnica importante podría conectarse con sus pruebas, archivos, comandos, resultados y dependencias.

```
CLAIM
  -> OBSERVATION
  -> ARTIFACT
  -> PRODUCER
  -> TRANSFORMATION
  -> CONSUMER
  -> VALIDATION
  -> CONCLUSION
```

Mecanismo propuesto: ninguna conclusión crítica queda aislada de su procedencia. Si cambia un artefacto, RXRE identifica qué conclusiones dependen de él y cuáles necesitan volver a verificarse.

E. Mutación controlada: el fuego

En lugar de permitir que la IA modifique indiscriminadamente su propia arquitectura, permitirle proponer cambios pequeños y comprobables en procedimientos, políticas o componentes autorizados.

Mecanismo propuesto:

1. Formular una hipótesis de mejora.
2. Registrar el comportamiento de referencia.
3. Ejecutar una prueba acotada.
4. Comparar contra la referencia.
5. Conservar el cambio solo si supera criterios predefinidos.
6. Mantener una vía de reversión.

Una mejora del propio sistema necesita pruebas independientes de las que utilizó para proponerla.

F. Estigmergia: el aire

La estigmergia es una forma de coordinación en la que los agentes se coordinan indirectamente mediante cambios persistentes en un entorno compartido.

En RXRE, el equivalente podría ser un registro de eventos y hallazgos que cualquier etapa del flujo pueda consultar:

- Hallazgo nuevo.
- Dependencia desbloqueada.
- Contradicción detectada.
- Artefacto invalidado.
- Experimento fallido.
- Hipótesis refutada.
- Tarea que puede retomarse.

Mecanismo propuesto: en lugar de depender de que un agente recuerde comunicar cada descubrimiento, las etapas posteriores reaccionan a eventos verificables.

El objetivo no es multiplicar agentes, sino reducir las pérdidas de información entre etapas.

G. Memoria adaptativa y recuperación: el agua

No toda la información debería conservarse para siempre con el mismo peso.

Mecanismo propuesto: diferenciar hechos estables, observaciones temporales, hipótesis, procedimientos reutilizables y conocimientos invalidados.

Cuando aparece evidencia contradictoria, RXRE actualiza el estado de las conclusiones afectadas, conserva su historial y evita reutilizar automáticamente procedimientos que dejaron de ser válidos.

La memoria no solo acumula información: también identifica cuándo debe revisarse.

H. Búsqueda de novedad causal: el éter

Los sistemas de investigación suelen perseguir objetivos explícitos. Pero una parte importante de los descubrimientos surge de encontrar conexiones inesperadas entre problemas aparentemente separados.

Mecanismo propuesto: mantener un grafo de cuestiones abiertas, componentes, afirmaciones y dependencias; buscar rutas de investigación que conecten anomalías conocidas con áreas poco exploradas.

RXRE podría priorizar conexiones por:

- Capacidad para explicar varias anomalías a la vez.
- Posibilidad de distinguir hipótesis competidoras.
- Número de dependencias que desbloquea.
- Coste de comprobación.
- Potencial de revelar una limitación estructural.

La novedad por sí sola no demuestra valor: cada conexión relevante debe convertirse en una pregunta verificable.

Estos ocho mecanismos son propuestas de diseño inspiradas en conceptos conocidos. Su combinación específica para RXRE todavía requeriría investigación, implementación y evaluación.

## 3. Cuatro proyectos menos convencionales que merecen una investigación profunda

Estos son especialmente relevantes porque se acercan a la idea de un sistema que aprende a utilizarse mejor a sí mismo.

7\. Recuris — evolución selectiva de la memoria

[Gen-Verse/Recuris](https://github.com/Gen-Verse/Recuris)

Su propuesta consiste en mejorar la memoria de un agente de larga duración, en lugar de modificar directamente los pesos del modelo o reescribir todo su prompt. Analiza trazas estructuradas, identifica qué componente de la memoria contribuyó a un fallo y somete las modificaciones a una validación independiente.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Qué investigaría para RXRE: un sistema que aprenda a corregir sus propios procedimientos de memoria, planificación y recuperación, pero que no acepte una modificación solo porque el propio agente la considera buena.

8\. MemSkill — aprender a recordar

[ViktorAxelsen/MemSkill](https://github.com/ViktorAxelsen/MemSkill)

En vez de tratar la memoria como un depósito estático, estudia cómo evolucionar las estrategias que determinan qué recordar, cómo extraerlo y dónde concentrar la atención.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Qué investigaría para RXRE: que el agente aprenda, a partir de casos difíciles, qué tipo de información necesita conservar para resolver mejor las siguientes tareas.

9\. MemRL — memoria con utilidad comprobada

[MemTensor/MemRL](https://github.com/MemTensor/MemRL)

Explora el aprendizaje sobre memoria episódica a partir de la retroalimentación del entorno, separando el razonamiento relativamente estable de las estrategias almacenadas que pueden actualizarse.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Qué investigaría para RXRE: cómo determinar qué experiencias anteriores realmente mejoran el éxito de una tarea y cuáles son irrelevantes o perjudiciales.

10\. Agentes coordinados mediante estigmergia

[KeepALifeUS/autonomous-agents](https://github.com/KeepALifeUS/autonomous-agents)

Este proyecto explora la coordinación mediante un entorno compartido, en lugar de depender exclusivamente del intercambio directo de mensajes entre agentes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Qué investigaría para RXRE: que los descubrimientos, las contradicciones y las dependencias pendientes queden registrados en un espacio compartido que permita continuar el trabajo sin reconstruirlo desde cero.

No implica crear más agentes: el mecanismo puede servir también para coordinar distintas etapas de un único agente.

## 4. La arquitectura que investigaría para RXRE

Mi propuesta es estudiar una arquitectura integrada, pero mantener separados los mecanismos que observan, deciden, actúan y validan.

ÉTER — Campo global de conocimiento

Objetivos, relaciones, preguntas abiertas y oportunidades de investigación

### CUERPO

Sensores, herramientas, estado real y observaciones

### MENTE

Hipótesis, causalidad, planificación y predicciones

### TIERRA

Artefactos, procedencia, contratos y estado recuperable

### AIRE

Eventos, flujos de datos y dependencias

### FUEGO

Experimentos, acciones y cambios controlados

### AGUA

Memoria adaptativa, recuperación y continuidad

ALMA — Coherencia del propósito

Evalúa si el trabajo contribuye a los objetivos reales de RXRE y respeta sus restricciones permanentes.

Ciclo de retroalimentación

Observar -> formular hipótesis -> actuar -> validar -> aprender -> descubrir el siguiente problema

El diagrama representa una arquitectura conceptual. No afirma que RXRE ya tenga esos componentes.

La parte importante es que todos los principios intercambien información a través de un estado verificable. El cuerpo produce observaciones; la mente construye explicaciones; la tierra conserva fundamentos y procedencia; el aire conecta los datos; el fuego ejecuta transformaciones; el agua actualiza la experiencia; el éter detecta relaciones globales; y el alma mantiene la orientación del conjunto.

## 5. Qué haría primero, sin introducir complejidad innecesaria

| Prioridad | Mecanismo                            | Resultado que debe demostrarse                                          |
| --------- | ------------------------------------ | ----------------------------------------------------------------------- |
| 1         | Memoria de experiencias y fallos     | Menos errores repetidos y recuperación de soluciones válidas            |
| 2         | Registro de eventos y procedencia    | Reconstrucción verificable de lo que ocurrió                            |
| 3         | Ciclo experimental con referencia    | Mejoras medidas, no solo propuestas                                     |
| 4         | Memoria adaptativa                   | Recuperación de información útil sin acumular ruido                     |
| 5         | Grafo causal y búsqueda de fronteras | Descubrimiento de dependencias y problemas todavía abiertos             |
| 6         | Autorregulación del proceso          | Detección de estancamiento, pérdida de información y fallos recurrentes |

El orden definitivo debe depender de lo que RXRE ya implemente. Si alguno de estos mecanismos existe, corresponde evaluarlo y mejorarlo, no duplicarlo.

## 6. Instrucción para el agente que ya está trabajando con RXRE

No inicies otro agente ni otra ejecución paralela. Puedes entregarle al agente actual esta ampliación de investigación para que contraste los proyectos anteriores con la arquitectura real.

RXRE - INVESTIGACION DE MECANISMOS NO CONVENCIONALES

Continua desde tu estado de trabajo actual. No reinicies la tarea, no crees ramas ni worktrees adicionales y no interfieras con operaciones activas.

OBJETIVO

Investigar mecanismos existentes en repositorios publicos que puedan ayudar a que RXRE proporcione al agente un comportamiento operativo integrado de:

BODY, MIND, SOUL, EARTH, FIRE, AIR, WATER y AETHER.

INVESTIGACION PRIORITARIA

Examina los mecanismos y, cuando sea posible, el codigo de:

1. [https://github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)
2. [https://github.com/MineDojo/Voyager](https://github.com/MineDojo/Voyager)
3. [https://github.com/noahshinn/reflexion](https://github.com/noahshinn/reflexion)
4. [https://github.com/letta-ai/letta](https://github.com/letta-ai/letta)
5. [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
6. [https://github.com/vukrosic/autoresearch-ai](https://github.com/vukrosic/autoresearch-ai)
7. [https://github.com/Gen-Verse/Recuris](https://github.com/Gen-Verse/Recuris)
8. [https://github.com/ViktorAxelsen/MemSkill](https://github.com/ViktorAxelsen/MemSkill)
9. [https://github.com/MemTensor/MemRL](https://github.com/MemTensor/MemRL)
10. [https://github.com/KeepALifeUS/autonomous-agents](https://github.com/KeepALifeUS/autonomous-agents)

No presupongas que las descripciones publicas demuestran que un mecanismo funciona en RXRE. Contrasta documentacion, codigo, pruebas, limitaciones, requisitos y licencias cuando sea pertinente.

PREGUNTAS TECNICAS

A. Como puede RXRE conservar experiencias verificadas y convertirlas en procedimientos reutilizables?

B. Como puede aprender que informacion recordar, recuperar, revisar o descartar?

C. Como puede modificar sus procedimientos de investigacion mediante cambios pequenos, reversibles y evaluados independientemente?

D. Como puede representar la procedencia completa de una afirmacion y sus dependencias causales?

E. Como puede detectar estancamiento, incertidumbre, errores recurrentes y perdida de informacion?

F. Como puede descubrir conexiones nuevas entre hallazgos sin generar trabajo especulativo ni duplicar tareas?

G. Que mecanismos pueden implementarse con la arquitectura existente, sin introducir dependencias innecesarias?

H. Que evidencia permitiria demostrar que cada mecanismo mejora realmente el comportamiento del agente?

METODO

1. Inspecciona el estado actual de RXRE y sus capacidades demostradas.
2. Reconstruye el punto de entrada y el flujo de ejecucion relevante.
3. Contrasta los mecanismos externos con los componentes existentes.
4. Identifica mecanismos ausentes, redundantes o insuficientes.
5. Selecciona el mecanismo de mayor valor respaldado por la evidencia.
6. Si la tarea actual permite implementarlo sin conflictos, realiza una modificacion acotada y reversible.
7. Valida el resultado contra una referencia y registra las pruebas.
8. Realiza un GLOBAL WORK SCAN y continua por las vias legitimas de progreso.

No integres un framework completo solo porque resulte interesante. Extrae y adapta mecanismos concretos unicamente cuando exista una justificacion tecnica.

ENTREGABLE

Presenta una matriz que relacione:

- Principio de RXRE.
- Repositorio y mecanismo estudiado.
- Evidencia inspeccionada.
- Capacidad actual de RXRE.
- Brecha demostrada.
- Mecanismo propuesto.
- Coste, riesgo y dependencias.
- Metodo de validacion.
- Resultado observado.
- Siguiente accion.

Distingue claramente entre mecanismos investigados, propuestas, cambios implementados y resultados comprobados.

Continua trabajando desde el estado existente. La investigacion no debe terminar al completar la matriz si queda una mejora pertinente, viable y respaldada por evidencia.

## Conclusión

La dirección más prometedora no es hacer que RXRE tenga ocho personalidades separadas. Es investigar cómo dotarlo de observación del estado, razonamiento causal, propósito persistente, memoria de experiencias, transformación controlada, circulación íntegra de información, adaptación y descubrimiento global.

Los proyectos más interesantes para profundizar primero son Recuris, MemSkill, AutoResearch y Voyager: juntos ofrecen líneas de investigación sobre evolución de la memoria, aprendizaje de estrategias de memoria, experimentación con evaluación y acumulación de habilidades ejecutables. Sus mecanismos todavía deben contrastarse con RXRE antes de decidir qué adoptar.
