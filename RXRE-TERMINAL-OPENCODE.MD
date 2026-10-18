# Investigacion: OpenCode + RXRE + terminal como sistema integrado

La busqueda apunta a una conclusion importante: no necesitamos convertir OpenCode, RXRE y la terminal en tres agentes separados. Necesitamos que funcionen como un unico ciclo de percepcion, razonamiento, accion, evidencia, aprendizaje y descubrimiento.

Hay soluciones conocidas que cubren partes del problema y enfoques menos ortodoxos que pueden servir para conectar las partes. No hay evidencia todavia de que una sola solucion implemente los ocho principios completos; conviene combinar mecanismos comprobables, no copiar una arquitectura entera.

## 1. Repositorios con mecanismos aprovechables

[OpenCode | The open source AI coding agent](https://images.openai.com/static-rsc-4/fZaKMwY08tU_NsPC5Z90BrdvnAdHmQQdJ3pq27R0oomkAdJRBJdLBZvtamSXzQ5cNC1jyI08aUf-dXYgAx7Nt3VM6zAFVR_9bTr1ZKRZ8CNqfbbMzaoM-XO7Y4nJN3wZubryGDdAZS4C_Brvjq9Q5Z9lni1tb-0rXk4LikzS3LI?purpose=inline)

1\. OpenCode Observability

Repositorio: danilofalcao/opencode-observability

Registra ejecuciones de herramientas, ciclo de vida de sesiones, mensajes, permisos y datos de entrada/salida, y los almacena para su inspeccion. Es relevante para que RXRE analice lo que OpenCode hizo realmente, no solo lo que afirma haber hecho.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



[Abrir repositorio](https://github.com/danilofalcao/opencode-observability)

Aprovechar: eventos observables, registro persistente y trazabilidad de ejecuciones.

Investigar antes de integrar: cobertura real de eventos, integridad de los datos y compatibilidad con la version instalada.

[GitHub - rohitg00/agentmemory: #1 Persistent memory for AI coding agents based on real-world benchmarks · GitHub](https://images.openai.com/static-rsc-4/aprdDCDnarPj-7AUDvCJUd6xJ4u0aSwt911Ygt3stoDRiJNrMusgThuRf8gdxEHV0sr2L9JW9BJt-NHvSqjWuMgypyxHjx2NCqW_2ofP_SWyEQCF-Rou3m4ZqZBguSjCUoen1r4P_dvIKgCAgHOs72s-6Hk_xgdWQ94wRdqGblw?purpose=inline)

2\. AgentMemory para OpenCode

Repositorio: rohitg00/agentmemory

Integra memoria persistente mediante hooks y herramientas de OpenCode. Su documentacion distingue las API de OpenCode 1.x y 2.x, describe diferencias reales entre eventos y advierte que cargar un plugin no demuestra que sus hooks funcionen correctamente.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



[Abrir integracion](https://github.com/rohitg00/agentmemory/tree/main/plugin/opencode)

Aprovechar: captura de eventos, recuperacion de memoria y contexto antes de las siguientes decisiones.

Riesgo: duplicar memoria o registrar observaciones sin conseguir que cambien el comportamiento posterior.

[Stateful AI Agents: A Deep Dive into Letta (MemGPT) Memory Models | by piyush jhamb | Feb, 2026 | Medium](https://images.openai.com/static-rsc-4/eS6RmKuCfJ_vtp_WnPXD8S5YpGTmrbhPulnz94S_khZAPX_SNHx_VmQ5YtlF_rX674BPtvWQSPcFZiRQfXXMrdOyyZQ8q0H36UDFi2Ba83vxL7yccp_H6HNHT6QVlWyYgLDsXFugRCxnsezWRzMa04y83rUbh_OcoMu6ie68KPg?purpose=inline)

3\. Letta Code / MemFS

Repositorio: letta-ai/letta-code

Ofrece agentes con estado persistente y un sistema de memoria basado en archivos versionados con Git. Separa las instrucciones siempre presentes de los conocimientos que se recuperan bajo demanda.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



[Abrir Letta Code](https://github.com/letta-ai/letta-code)

Aprovechar: memoria versionada, historial de cambios, consolidacion y recuperacion selectiva.

No copiar automaticamente: introducir otro runtime de agentes podria duplicar responsabilidades que RXRE ya posee.

[【論文瞬読】記憶から学ぶAIエージェント：MEMRLが実現する「経験を糧にした自己進化」｜AI Nest](https://images.openai.com/static-rsc-4/urarm3rCpWePsBF4v1DUPsPjSUqBAQCfXKWfwwAQ3l2QG1OrRhnxf9TCbrteQcyioJP47o9NmZ98UXrsU7yVvVvr1DYyRVmfHFmiecSjZWVm_D7u54BDefi0Ez-MsUZuBKsfzplx6Ym7YoPpN3aZO8o3xP8dQrwrwMwpkkFUEBk?purpose=inline)

4\. MemRL

Repositorio: MemTensor/MemRL

Investiga el aprendizaje en tiempo de ejecucion mediante experiencias almacenadas y retroalimentacion del entorno, reforzando memorias asociadas con mejores resultados sin necesitar modificar los pesos del modelo base.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



[Abrir repositorio](https://github.com/MemTensor/MemRL)

Aprovechar: que las experiencias influyan en la seleccion de estrategias futuras.

Adaptacion para RXRE: evaluar resultados posteriores y consecuencias, no premiar simplemente que una operacion termine sin errores.

[The Ultimate Autoresearch Guide - by Aakash Gupta](https://images.openai.com/static-rsc-4/H3RIJjnyrDWJ0cRpEXWCTrST4-FucA05ozL1Y6DxcFxfqyChlEIAnI-OEkLcI6hhsP1YEbUYWGAe7VMTYh2T4a5--Nu2eN_RhryO13katnDJir1093i-UDBqxhmPM9YTvV2WfTzHDqhHJPeihYtio0zgR1_23_8fygLmMLc2ZpQ?purpose=inline)

5\. autoresearch

Repositorio: karpathy/autoresearch

Permite que un agente itere sobre un programa de investigacion, ejecute experimentos con una metrica y conserve o descarte cambios segun los resultados.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



[Abrir repositorio](https://github.com/karpathy/autoresearch)

Aprovechar: experimentos comparables, criterios objetivos, ciclos repetidos y decisiones basadas en resultados.

Limite: el proyecto original se centra en investigacion y entrenamiento de modelos; su mecanismo experimental es mas transferible que su codigo especifico.

## 2. Enfoques poco ortodoxos

Estos son especialmente interesantes porque cambian la forma en que los componentes se coordinan, en lugar de limitarse a agregar mas instrucciones al modelo.

## A. Stigmergia: que el entorno coordine el trabajo

Repositorios: [AdviceNXT/sbp](https://github.com/AdviceNXT/sbp) y [Production-Grade/stigmergy](https://github.com/Production-Grade/stigmergy)

En vez de depender de un planificador central que decide cada paso, los componentes dejan señales en un entorno compartido. Una observacion nueva puede aumentar la prioridad de una investigacion; un fallo puede generar una tarea de diagnostico; una evidencia que queda obsoleta puede reducir su prioridad.

SBP propone senales temporales que decaen y rastros duraderos cuando hay informacion que conservar. Stigmergy utiliza acumulacion de presion para activar trabajo cuando se supera un umbral.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Aplicacion a RXRE: convertir las fronteras abiertas, fallos recurrentes, contradicciones y oportunidades de experimentacion en senales cuantificables que compitan por prioridad.

Riesgo: bucles de reintento, senales que se refuerzan mutuamente y consumo infinito de recursos. Hacen falta limites, caducidad, deduplicacion y criterios de finalizacion.

## B. Blackboard: conocimiento compartido en vez de agentes aislados

Repositorio: [arvarik/bmas](https://github.com/arvarik/bmas)

Una pizarra compartida contiene hechos, propuestas, resultados y tareas. Diferentes procesos pueden contribuir sin tener que intercambiar cadenas de mensajes fragiles directamente. bMAS documenta runtimes con un registro persistente de eventos, contratos de ejecucion y puntos de recuperacion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Aplicacion a RXRE: OpenCode, los comandos de terminal y los mecanismos de RXRE deberian consumir y producir evidencia bajo un contrato comun, con identificadores, procedencia y estado de validacion.

Riesgo: convertir la pizarra en otra base de datos desconectada. Debe existir una unica fuente de verdad o un contrato explicito de sincronizacion con los artefactos actuales de RXRE.

## C. Memoria que cambia las decisiones, no solo el contexto

Combinar memoria persistente (AgentMemory/Letta) con seleccion de experiencias segun su utilidad (MemRL).

Una leccion no deberia considerarse eficaz porque se guardo, porque existe un test o porque un agente la puede recuperar. Deberia demostrarse que, ante una situacion equivalente, la leccion cambia una decision y mejora el resultado.

Aplicacion a RXRE: registrar la situacion, la decision anterior, la leccion recuperada, la nueva decision, el resultado observado y si la mejora se mantiene en casos posteriores.

Riesgo: confundir correlacion con causalidad o reforzar una estrategia que tuvo exito por casualidad.

## D. Autoinvestigacion con experimentos competitivos

Inspirarse en autoresearch, pero ampliar la unidad experimental: no solo modificar codigo, sino probar hipotesis sobre el propio flujo de trabajo.

Ejemplo: si OpenCode afirma haber escrito un archivo, pero RXRE no encuentra el resultado esperado, plantear hipotesis distintas:

- El comando no se ejecuto.
- El proceso fallo o quedo incompleto.
- La salida se perdio o se interpreto mal.
- El archivo se escribio en otra ubicacion.
- RXRE consulto otra base de datos o un estado obsoleto.

Cada hipotesis debe generar una prueba discriminante. Se conserva la explicacion que sobrevive a la evidencia, no la que parece mas convincente.

Aplicacion a RXRE: transformar cada fallo en una oportunidad de descubrir un defecto causal del sistema, sin asumir que todo fallo requiere una nueva funcionalidad.

## 3. Como conectaria los ocho principios

Los ocho principios no deberian ser ocho modulos independientes. Cada uno debe funcionar a traves de OpenCode, RXRE y la terminal.

| Principio | Mecanismo operativo                                                    | Prueba de que funciona                                       |
| --------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| CUERPO    | Observacion del entorno, procesos, herramientas, recursos y artefactos | Detecta el estado real y no uno supuesto                     |
| MENTE     | Hipotesis alternativas y experimentos discriminantes                   | Distingue causas que predicen resultados diferentes          |
| ALMA      | Objetivos persistentes, funcion de valor y prioridades                 | Elige acciones que mejoran objetivos definidos               |
| TIERRA    | Evidencia con procedencia, versiones y condiciones de validez          | Otro proceso puede reproducir o refutar la afirmacion        |
| FUEGO     | Intervenciones y experimentos con predicciones falsables               | Mide si la accion produjo el cambio previsto                 |
| AIRE      | Integridad de datos entre productor, transformacion y consumidor       | Detecta truncamiento, perdida, desajuste y salida incompleta |
| AGUA      | Memoria causal, consecuencias y actualizacion de estrategias           | Una leccion modifica decisiones futuras de manera medible    |
| ETER      | Integracion global, conexiones nuevas y alternativas                   | Al agotarse una via, propone otra via comprobable            |

El punto decisivo es AIRE: una IA puede razonar correctamente y aun asi fracasar si la terminal pierde datos, OpenCode interpreta mal una herramienta o RXRE lee un estado distinto del que se modifico. Sin integridad de extremo a extremo, los otros principios pueden aparentar funcionar mientras toman decisiones sobre evidencia falsa.

## 4. La arquitectura que merece probarse

\#chatgpt-mermaid-\_r_337\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_337\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_337\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_337\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_337\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_337\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_337\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_337\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_337\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_337\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_337\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_337\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_337\_ p{margin:0;}#chatgpt-mermaid-\_r_337\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_337\_ .label text,#chatgpt-mermaid-\_r_337\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .node rect,#chatgpt-mermaid-\_r_337\_ .node circle,#chatgpt-mermaid-\_r_337\_ .node ellipse,#chatgpt-mermaid-\_r_337\_ .node polygon,#chatgpt-mermaid-\_r_337\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .rough-node .label text,#chatgpt-mermaid-\_r_337\_ .node .label text,#chatgpt-mermaid-\_r_337\_ .image-shape .label,#chatgpt-mermaid-\_r_337\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_337\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .rough-node .label,#chatgpt-mermaid-\_r_337\_ .node .label,#chatgpt-mermaid-\_r_337\_ .image-shape .label,#chatgpt-mermaid-\_r_337\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_337\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_337\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_337\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_337\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_337\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_337\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_337\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_337\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_337\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_337\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_337\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_337\_ .icon-shape,#chatgpt-mermaid-\_r_337\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_337\_ .icon-shape p,#chatgpt-mermaid-\_r_337\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_337\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_337\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_337\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_337\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_337\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_337\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_337\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_337\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_337\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_337\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_337\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_337\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_337\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_337\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_337\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_337\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_337\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .node rect,#chatgpt-mermaid-\_r_337\_ .node circle,#chatgpt-mermaid-\_r_337\_ .node ellipse,#chatgpt-mermaid-\_r_337\_ .node polygon,#chatgpt-mermaid-\_r_337\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_337\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_337\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_337\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_337\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_337\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}OpenCode: decisiones yherramientasTerminal: ejecucion yobservacionRXRE: evidencia y analisiscausalMemoria: experiencias yconsecuenciasFuncion de valor: objetivos yprioridadesFrontera de investigacionExperimento discriminanteVerificacion independientecomando y prediccionresultado, codigo, stdout,stderrhechos y procedencialecciones evaluadascausas candidatasprioridadresultado verificadoevidencia util para la siguientedecision

Este diseno es una hipotesis arquitectonica, no una descripcion de capacidades ya implementadas. Debe adaptarse a las interfaces reales del repositorio y de la version instalada de OpenCode.

## 5. Orden de investigacion y ejecucion

No integraria todos estos repositorios ni agregaria otra capa de agentes todavia. Primero investigaria y validaria los mecanismos con mayor impacto:

1. Observabilidad real de OpenCode y la terminal. Comprobar que se capturan las llamadas a herramientas, argumentos, resultados, errores, codigos de salida y cambios reales en los artefactos.
2. Contrato de evidencia OpenCode -> terminal -> RXRE. Seguir una operacion real desde su ejecucion hasta su persistencia, consulta y uso en una decision posterior. Detectar donde se pierde o distorsiona informacion.
3. Ciclo causal cerrado. Seleccionar un fallo real, proponer hipotesis, ejecutar una prueba discriminante, verificar el resultado y actualizar la conclusion.
4. Memoria con efecto comprobable. Medir si una leccion cambia decisiones posteriores y evita repetir un fallo; comparar con un caso de control cuando sea posible.
5. Prioridad y descubrimiento. Despues de establecer la integridad del ciclo, experimentar con una funcion de valor para ALMA y senales de frontera para ETER. Medir si encuentran trabajo util que de otro modo quedaria sin atender.

La busqueda de repositorios es una fuente de mecanismos, no una razon para instalarlos. En particular, el codigo externo debe evaluarse por compatibilidad, licencia, dependencias, comportamiento observado y coste de mantenimiento.

Restriccion inmediata: como la ultima informacion disponible indica que `RXRE-CAUSAL-EVOLUTION-001` estaba en curso, no lanzaria otra implementacion en paralelo. Usaria esta investigacion como material para reconciliar con su informe y con el estado real de RXRE antes de decidir que cambiar.

El criterio final no es que la IA tenga ocho nombres nuevos en sus instrucciones. Es que pueda observar, razonar, perseguir objetivos, actuar, preservar evidencia, aprender de consecuencias y descubrir nuevas vias dentro de un ciclo integrado, y que cada capacidad tenga pruebas reproducibles.
