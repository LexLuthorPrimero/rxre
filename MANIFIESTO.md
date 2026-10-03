# Manifiesto de compactación documental — 2026-10-03
# Generado por global-coordinator-01 (AGENT-01 COORDINACION).
# Nada se borra: todo lo movido está aquí y en git. Destino del estado: ESTADO.md
# Formato: sha256  bytes  ruta_de_origen  ->  ruta_nueva

2a8e59d17243302a177a0e85c8ce47f5a2aa21713b332d563a6694d5e3b5cec8    1605  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/02-ARQUITECTURA⁄DECISIONS.md
9f838c74dec6f751022e7acae652fb9c5b5719f63895a17bec449e12de01ad48     523  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/03-EXPERIMENTOS⁄EXP-[NÚMERO]-[NOMBRE-CORTO].md
1d7bcf36f9e7bffd1d65fe6c5d14c03df91c5e4ed3b898466c28942a18c1dde3   28242  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/29⁄9⁄26.md
da4ad1b418377abd68eee05b5bd265b9feaeb0612735a8bf5e34097cedf6b247   12457  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/30⁄9⁄26.md
c2c468a40d29c7d6e42150562d420f4dc54e010b2976d64d9f998121897c1935    4046  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/AGENTS-BORRADOR-48.md
1f339533c00798ee95a08d6d4234b03607cf25156fd4f068ee7a6d7d94dde70e    4230  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/CIERRE_PROYECTO.md
f29bc17e93a848f038c7b5413f4b053cf88356e8998b33176ce3fc674d246c80    2106  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/comportamiento.md
a46bde65b60c56c93ca00e60d254eea9964f3e0968c99a970199f2f328ed3bec    6503  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/FINAL-RELEASE-REPORT.md
c1fc5e8301b3acf9b9818f08826b87703e9d9eff1dfa38602dbbd767ef9834ea    4582  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/FINAL-RESEARCH-STATUS.md
1d1d31abd1dbbb70b993be88b6d016e8b1eae741384ba2033a84ee6c22bd1655    9815  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/ideas2.md
f0fb276f42088d332ecfeb95af997a8be9f3c5abb488428509f966d0f2e0716e   17909  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/ideas3.md
d3ac0ebd531625b8a53ce85b6e418af867aed2f70c6b4b6128dd89165ed30dd3     342  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/PATCH-REGISTRY.md
b078b080af9805efb8c13cd0a7519e329eea814c9280228b24155891439593e7     384  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/PROBLEM-STATUS.md
1c55b6372611a532d15643250d7fd15a2c561912263de04aebc948311d2903cf   10611  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/PROYECTO_STATUS.md
188d67916b144e6bb755c6c8ed6d4a8b5ef9a4df46b43a16ae613f2fdcff6420    3286  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/RELEASE-CANDIDATE.md
357d74c1850d2276fc21afbc310ed220fabc04137c233459cc11baa599af78ce    2015  (raiz o 00-INDICE)  ->  archive/documentacion-compactada-20261003/RELEASE-EXCLUSIONS.md

## Por que se movieron

- PROYECTO_STATUS / CIERRE_PROYECTO / RELEASE-CANDIDATE / FINAL-RELEASE-REPORT /
  RELEASE-EXCLUSIONS / FINAL-RESEARCH-STATUS: seis documentos que se declaraban
  'estado final' y competian entre si. Son tres cierres sucesivos (2026-09-19,
  09-25, 09-29). Sus cifras, limitaciones y estados estan en ESTADO.md sin resumir.
- PATCH-REGISTRY.md: cabecera de tabla con 2 filas que afirman 'LZ4 adaptativo
  Implementado'. No hay LZ4 en el codigo del compresor y DECISIONS.md no lo
  registra; AD-8 confirmo BC3 estandar. Afirmacion falsa en documento que competia
  por autoridad. El registro real es PATCH-REGISTRY-FINAL.md (24 filas).
- PROBLEM-STATUS.md: plantilla sin rellenar (384 B). El canonico es
  PROBLEM-STATUS-FINAL.md, citado por 27 documentos, con 8 estados tipados.
- ideas2.md / ideas3.md: brainstorm superado por ideas.md.
- AGENTS-BORRADOR-48.md: se declara SUBORDINADO y NO EJECUTAR en su propia cabecera.
- 29/9/26.md, 30/9/26.md: bitacoras sueltas por fecha en la raiz.
- comportamiento.md: 'regla operativa' no incorporada a COORDINACION.md.
- 02-ARQUITECTURA-DECISIONS.md y 03-EXPERIMENTOS-EXP-plantilla.md: nombre con
  U+2044 (FRACTION SLASH) en lugar de '/', colgados en la raiz. El primero es un
  fragmento de 18 lineas cuya unica decision (formato RGB565 propio) fue
  retractada por su propia AD-6; el segundo es una plantilla sin rellenar.
  El DECISIONS.md canonico esta en 02-ARQUITECTURA/DECISIONS.md, 1322 lineas.

## Lo que NO se toco

- 504 findings en 06-INGENIERIA-INVERSA/findings/: evidencia primaria.
- 9 vistas generadas por tools/artifacts.py: se regeneran solas.
- PATCH-REGISTRY-FINAL.md y PROBLEM-STATUS-FINAL.md: referenciados por 23 y 27
  documentos respectivamente; son canonicos, no duplicados.
- Los 15 mounts de AGENTS.md: requieren root. AGENTS.md esta a 0 B por un bind
  mount vacío; lo径 del y otro agente esta en 08-ARQUITECTURA/AGENTS.RECTOR-*.bak
  y en el blob a40e21cb del object store. Fuera del alcance documental.
