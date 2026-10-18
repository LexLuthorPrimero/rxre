Corregí los dos diagramas sin cambiar el modelo conceptual ni el estado operativo. El Mermaid queda limpio y el ASCII muestra explícitamente que los planos emiten eventos hacia ÉTER, mientras AIRE y TIERRA atraviesan las operaciones.

## 1. Mermaid limpio

\#chatgpt-mermaid-\_r_10d3\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_10d3\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_10d3\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_10d3\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_10d3\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_10d3\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_10d3\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_10d3\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_10d3\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_10d3\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_10d3\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_10d3\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_10d3\_ p{margin:0;}#chatgpt-mermaid-\_r_10d3\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_10d3\_ .label text,#chatgpt-mermaid-\_r_10d3\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .node rect,#chatgpt-mermaid-\_r_10d3\_ .node circle,#chatgpt-mermaid-\_r_10d3\_ .node ellipse,#chatgpt-mermaid-\_r_10d3\_ .node polygon,#chatgpt-mermaid-\_r_10d3\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .rough-node .label text,#chatgpt-mermaid-\_r_10d3\_ .node .label text,#chatgpt-mermaid-\_r_10d3\_ .image-shape .label,#chatgpt-mermaid-\_r_10d3\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_10d3\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .rough-node .label,#chatgpt-mermaid-\_r_10d3\_ .node .label,#chatgpt-mermaid-\_r_10d3\_ .image-shape .label,#chatgpt-mermaid-\_r_10d3\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_10d3\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_10d3\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_10d3\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_10d3\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_10d3\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_10d3\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_10d3\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_10d3\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_10d3\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_10d3\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_10d3\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_10d3\_ .icon-shape,#chatgpt-mermaid-\_r_10d3\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_10d3\_ .icon-shape p,#chatgpt-mermaid-\_r_10d3\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_10d3\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_10d3\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_10d3\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_10d3\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_10d3\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_10d3\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_10d3\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_10d3\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_10d3\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_10d3\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_10d3\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_10d3\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_10d3\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_10d3\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_10d3\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_10d3\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .node rect,#chatgpt-mermaid-\_r_10d3\_ .node circle,#chatgpt-mermaid-\_r_10d3\_ .node ellipse,#chatgpt-mermaid-\_r_10d3\_ .node polygon,#chatgpt-mermaid-\_r_10d3\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_10d3\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_10d3\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_10d3\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_10d3\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_10d3\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}ALMAproposito y criterio de cierreETERhub asincronono media llamadas directasMENTEcausalidadCUERPOobservacion realFUEGOtransformacionAGUAaprendizajeAIREtraza transversalTIERRAevidencia transversaldefine criteriosync directosync directosync directosync directoevento asyncevento asyncevento asyncevento asyncnotificanotificaobservaobservaobservaobservaregistraregistraregistraregistra

## 2. ASCII corregido

```
                    +------------------------------+
                    |             ALMA             |
                    | proposito / criterio de cierre|
                    +---------------+--------------+
                                    |
                                    | define
                                    v
                    +------------------------------+
                    |             ETER             |
                    | recibe eventos asincronos    |
                    | coordina; no media llamadas  |
                    +---------------+--------------+
                                    ^
                                    |
                         eventos async entrantes
                                    |
       +----------------------------+----------------------------+
       |                            |                            |
       |                            |                            |
+------+-------+          +---------+------+          +----------+-----+
|    MENTE     |<== sync =>|    CUERPO      |<== sync =>|     FUEGO      |
| hipotesis    |           | observacion    |           | transformacion |
| causalidad   |           | real           |           | rollback       |
+------+-------+           +--------+-------+           +--------+------+
       ^                            |                            |
       |                            |                            |
       +========== sync ============+============ sync ==========+
                                    |
                              +-----+-----+
                              |   AGUA    |
                              | aprendizaje|
                              +-----------+

     +----------------------------------------------------------------+
     |                    CAPAS TRANSVERSALES                         |
     |                                                                |
     |  AIRE: traza decisiones, llamadas, herramientas y resultados    |
     |  TIERRA: evidencia, hashes, procedencia e incertidumbre         |
     |                                                                |
     |  Ambas observan las transiciones de TODOS los planos.          |
     |  ETER puede notificarles, pero no es su unica fuente posible.   |
     +----------------------------------------------------------------+

     +----------------------------------------------------------------+
     |                  DISCIPLINA EPISTEMICA                         |
     |                                                                |
     | EVIDENCE -> SEMANTICS -> SCHEMA -> DISCRIMINATING TEST          |
     |          -> IMPLEMENTATION -> VALIDATION -> nueva evidencia     |
     +----------------------------------------------------------------+

     +----------------------------------------------------------------+
     |                      PUERTA GLOBAL                             |
     |                                                                |
     | AUDIT A-F -> DELIVERED -> CHALLENGED                            |
     |                         <-> CONTESTED                            |
     |                                  |                             |
     |                                  v                             |
     |                               ACCEPTED                          |
     |                                  |                             |
     |                                  v                             |
     |                               ETAPA 1                           |
     |                                                                |
     | Sin ACCEPTED, ETAPA 1 permanece BLOQUEADA.                      |
     +----------------------------------------------------------------+
```

Límite del dibujo: las conexiones transversales representan la responsabilidad conceptual de AIRE y TIERRA; no afirman que la instrumentación actual ya capture todas las transiciones. Del mismo modo, la flecha de ALMA a ÉTER representa la hipótesis del modelo, no un contrato confirmado del repositorio.

## Estado operativo

```
AUDIT A-F:       esperando artefactos
INICIO:          no confirmado
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
```

No cambia el alcance de la auditoría ni se autoriza ninguna modificación de RXRE.


