# KNOWLEDGE-GRAPH

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Aristas entre findings, leidas de las cabeceras y con el
vocabulario **MEDIDO** por `tools/relations.py`, no con una lista
de verbos escrita a mano. Tabla y no grafo dibujado: un .dot hay
que renderizarlo para leerlo, y no se audita con grep.

Se miden 37 etiquetas de relacion, 172 filas de arista y 155 pares
`(desde,hacia)` distintos. La diferencia entre filas y pares es
FLEXION: la misma relacion escrita con dos verbos.

La lista cerrada que este archivo usaba antes conocia 9 de las
37 etiquetas, y por eso Cherry 8 aristas de 155.

| desde | verbo | verbo normalizado | hacia | nota |
|---|---|---|---|---|
| 018 | `CONTINUES` | `CONTINUA` | 017 |  |
| 018 | `HALLAZGO` | `HALLAZGO` | 018 | SELF |
| 019 | `CONTINUES` | `CONTINUA` | 017 |  |
| 019 | `CORRECTED_BY` | `CORRIGIDO_POR!` | 030 |  |
| 022 | `CONTINUES` | `CONTINUA!` | 021 |  |
| 023 | `AMENDA` | `CORRIGE` | 022 |  |
| 023 | `CONTINUES` | `CONTINUA` | 017 |  |
| 023 | `CORRECTED_BY` | `CORRIGIDO_POR!` | 035 |  |
| 023 | `MEDIDO_EN_MI_ASIC_POR` | `MEDIDO_EN_MI_ASIC_POR!` | 045 |  |
| 025 | `CONTINUES` | `CONTINUA!` | 024 |  |
| 026 | `COMPLEMENTS` | `COMPLETA!` | 024 |  |
| 026 | `CONTINUES` | `CONTINUA!` | 024 |  |
| 027 | `COMPLEMENTS` | `COMPLETA!` | 024 |  |
| 027 | `CONTINUES` | `CONTINUA!` | 026 |  |
| 028 | `CONTINUES` | `CONTINUA!` | 024 |  |
| 029 | `CONTINUES` | `CONTINUA` | 017 |  |
| 029 | `CONTINUES` | `CONTINUA!` | 028 |  |
| 030 | `CONTINUES` | `CONTINUA` | 017 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA` | 018 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA` | 019 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA` | 020 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 021 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA` | 022 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 023 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 024 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 025 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 026 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 027 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 028 | `017–029` 1/1 |
| 030 | `CONTINUES` | `CONTINUA!` | 029 |  |
| 030 | `CONTINUES` | `CONTINUA!` | 029 | `017–029` 1/1 |
| 030 | `CORRECTS` | `CORRIGE` | 019 |  |
| 031 | `CONTINUES` | `CONTINUA!` | 030 |  |
| 032 | `CIERRA` | `CIERRA!` | 030 |  |
| 032 | `COMPLEMENTS` | `COMPLETA!` | 031 |  |
| 033 | `COMPLEMENTS` | `COMPLETA!` | 031 |  |
| 033 | `CONTINUES` | `CONTINUA!` | 023 |  |
| 034 | `CONTINUES` | `CONTINUA!` | 029 |  |
| 034 | `STRENGTHENS` | `REFUERZA!` | 033 |  |
| 035 | `CORRECTS` | `CORRIGE!` | 023 |  |
| 035 | `RECTIFIES` | `CORRIGE!` | 024 |  |
| 035 | `RETRACTED_BY` | `RETRACTADO_POR!` | 043 |  |
| 036 | `CLAUSULA_RETRACTADA_POR` | `CLAUSULA_RETRACTADA_POR` | 091 |  |
| 036 | `CONTINUES` | `CONTINUA` | 034 |  |
| 036 | `IMPLEMENTS` | `IMPLEMENTA!` | 035 |  |
| 036 | `RETRACTED_PARTLY_BY` | `RETRACTADO_PARCIALMENTE_POR!` | 043 |  |
| 037 | `CONTINUES` | `CONTINUA!` | 036 |  |
| 038 | `CONTINUES` | `CONTINUA!` | 036 |  |
| 039 | `CONTINUES` | `CONTINUA!` | 038 |  |
| 040 | `CONTINUES` | `CONTINUA!` | 039 |  |
| 041 | `COMPLEMENTS` | `COMPLETA!` | 040 |  |
| 041 | `CONTINUES` | `CONTINUA!` | 040 |  |
| 042 | `COMPLEMENTS` | `COMPLETA!` | 041 |  |
| 042 | `CONTINUES` | `CONTINUA!` | 041 |  |
| 043 | `CERRADO_POR` | `CIERRA!` | 046 |  |
| 043 | `COMPLEMENTS` | `COMPLETA!` | 042 |  |
| 043 | `CONTINUES` | `CONTINUA!` | 042 |  |
| 043 | `RETRACTS` | `RETRACTA!` | 035 |  |
| 044 | `COMPLEMENTS` | `COMPLETA!` | 043 |  |
| 044 | `CONTINUES` | `CONTINUA!` | 043 |  |
| 044 | `IMPLEMENTS` | `IMPLEMENTA!` | 043 |  |
| 045 | `COMPLEMENTS` | `COMPLETA!` | 040 | `040-smu-canal-mensajes-gfx8.md,041-curva-at-histeresis-dvfs-gfx8.md,` 1/1 |
| 045 | `COMPLEMENTS` | `COMPLETA!` | 041 | `040-smu-canal-mensajes-gfx8.md,041-curva-at-histeresis-dvfs-gfx8.md,` 1/1 |
| 045 | `COMPLETA` | `COMPLETA!` | 023 |  |
| 045 | `CONTINUES` | `CONTINUA!` | 043 |  |
| 046 | `CLAUSULA_RETRACTADA_POR` | `CLAUSULA_RETRACTADA_POR` | 091 |  |
| 046 | `CONTINUES` | `CONTINUA!` | 045 |  |
| 046 | `CORRECTS` | `CORRIGE!` | 040 | `040,041,042,043,044,045` 6/6 |
| 046 | `CORRECTS` | `CORRIGE!` | 041 | `040,041,042,043,044,045` 6/6 |
| 046 | `CORRECTS` | `CORRIGE!` | 042 | `040,041,042,043,044,045` 6/6 |
| 046 | `CORRECTS` | `CORRIGE!` | 043 | `040,041,042,043,044,045` 6/6 |
| 046 | `CORRECTS` | `CORRIGE!` | 044 | `040,041,042,043,044,045` 6/6 |
| 046 | `CORRECTS` | `CORRIGE!` | 045 | `040,041,042,043,044,045` 6/6 |
| 046 | `GENERALIZADO_POR` | `GENERALIZADO_POR!` | 047 |  |
| 047 | `CLAUSULA_RETRACTADA_POR` | `CLAUSULA_RETRACTADA_POR` | 091 |  |
| 047 | `CONTINUES` | `CONTINUA!` | 046 |  |
| 047 | `CORRECTS_RUTA` | `CORRIGE!` | 046 |  |
| 047 | `CORRIGE` | `CORRIGE!` | 051 |  |
| 047 | `GENERALIZA` | `GENERALIZA!` | 046 |  |
| 048 | `CONTINUES` | `CONTINUA!` | 033 |  |
| 048 | `CONTINUES` | `CONTINUA!` | 047 |  |
| 048 | `CORRECTS` | `CORRIGE!` | 040 |  |
| 049 | `COMPLEMENTS` | `COMPLETA!` | 047 | `047,048` 2/2 |
| 049 | `COMPLEMENTS` | `COMPLETA!` | 048 | `047,048` 2/2 |
| 049 | `COMPLETA` | `COMPLETA!` | 048 |  |
| 050 | `COMPLEMENTS` | `COMPLETA!` | 049 |  |
| 050 | `CONTINUES` | `CONTINUA!` | 049 |  |
| 051 | `CLAUSULA_RETRACTADA_POR` | `CLAUSULA_RETRACTADA_POR` | 091 |  |
| 051 | `CONTINUES` | `CONTINUA!` | 050 |  |
| 051 | `CORRIGE_LA_POLITICA_DE` | `CORRIGE_LA_POLITICA!` | 046 |  |
| 052 | `CONTINUES` | `CONTINUA!` | 051 |  |
| 053 | `COMPLEMENTS` | `COMPLETA!` | 046 | `046,050` 2/2 |
| 053 | `COMPLEMENTS` | `COMPLETA!` | 050 | `046,050` 2/2 |
| 055 | `COMPLEMENTS` | `COMPLETA` | 053 |  |
| 058 | `CONTINUES` | `CONTINUA!` | 051 |  |
| 059 | `CONTINUES` | `CONTINUA!` | 051 |  |
| 059 | `CORRECTS` | `CORRIGE` | 058 |  |
| 060 | `CORRECTS` | `CORRIGE` | 059 |  |
| 061 | `CIERRA` | `CIERRA` | 060 |  |
| 061 | `CONTINUES` | `CONTINUA!` | 051 |  |
| 074 | `RETRACTADO_PARCIALMENTE_POR` | `RETRACTADO_PARCIALMENTE_POR` | 091 |  |
| 079 | `RETRACTADO_PARCIALMENTE_POR` | `RETRACTADO_PARCIALMENTE_POR` | 091 |  |
| 096 | `HALLAZGO` | `HALLAZGO!` | 096 | SELF |
| 106 | `CONTINUES` | `CONTINUA` | 104 |  |
| 107 | `CONTINUES` | `CONTINUA` | 106 |  |
| 110 | `CONFIRMA` | `CONFIRMA` | 017 |  |
| 110 | `CORRIGE` | `CORRIGE` | 106 |  |
| 114 | `CONTINUES` | `CONTINUA` | 113 |  |
| 119 | `CERRADO_POR` | `CIERRA!` | 043 | `043,046` 2/2 |
| 119 | `CERRADO_POR` | `CIERRA!` | 046 | `043,046` 2/2 |
| 119 | `CONTINUES` | `CONTINUA` | 114 |  |
| 119 | `REFINA` | `REFINA!` | 043 |  |
| 120 | `AUDITA` | `AUDITA!` | 071 |  |
| 120 | `CONTINUES` | `CONTINUA` | 119 |  |
| 121 | `CONFIRMA` | `CONFIRMA` | 110 |  |
| 121 | `CONTINUES` | `CONTINUA` | 120 |  |
| 121 | `RETRACTA_LA_PROMESA_DE` | `RETRACTA_LA_PROMESA_DE` | 120 |  |
| 122 | `CONTINUES` | `CONTINUA!` | 121 |  |
| 122 | `MISMA_CLASE_QUE` | `MISMA_CLASE_QUE` | 034 |  |
| 125 | `CONTINUES` | `CONTINUA!` | 122 |  |
| 125 | `GENERALIZA` | `GENERALIZA!` | 122 |  |
| 125 | `HALLAZGO` | `HALLAZGO` | 125 | SELF |
| 127 | `CONTINUES` | `CONTINUA` | 126 |  |
| 127 | `RESUELVE` | `RESUELVE` | 123 |  |
| 130 | `CONFIRMA` | `CONFIRMA` | 110 |  |
| 134 | `CONTINUES` | `CONTINUA!` | 127 |  |
| 135 | `CERRADO_POR` | `CIERRA` | 191 |  |
| 182 | `CORRIGE` | `CORRIGE` | 144 |  |
| 182 | `MEDIDO_POR` | `MEDIDO_POR` | 244 |  |
| 193 | `CONTINUES` | `CONTINUA!` | 051 |  |
| 231 | `CONFIRMADO_POR` | `CONFIRMADO_POR` | 190 |  |
| 231 | `CORRIGIDO_POR` | `CORRIGIDO_POR` | 182 |  |
| 239 | `CORRIGIDO_POR` | `CORRIGIDO_POR` | 190 |  |
| 242 | `RETRACTADO_POR` | `RETRACTADO_POR` | 203 |  |
| 246 | `CORREGIDO_POR` | `CORREGIDO_POR` | 247 |  |
| 974 | `CONTINUES` | `CONTINUA!` | 099 |  |
| 974 | `CORRECTS` | `CORRIGE!` | 131 |  |
| 976 | `CONTINUES` | `CONTINUA!` | 131 |  |
| 976 | `CORRECTS` | `CORRIGE!` | 101 |  |
| 976 | `CORRECTS` | `CORRIGE` | 974 |  |
| 978 | `CORRECTS` | `CORRIGE!` | 101 |  |
| 978 | `CORRECTS` | `CORRIGE` | 976 |  |
| 978 | `CORROBORADO_POR` | `CORROBORADO_POR` | 183 |  |
| 979 | `CONTINUES` | `CONTINUA` | 974 |  |
| 979 | `CONTINUES` | `CONTINUA` | 976 |  |
| 979 | `CONTINUES` | `CONTINUA` | 978 |  |
| 979 | `CORROBORADO_POR` | `CORROBORADO_POR!` | 023 |  |
| 979 | `CORROBORADO_POR` | `CORROBORADO_POR!` | 087 |  |
| 979 | `CORROBORADO_POR` | `CORROBORADO_POR` | 183 |  |
| 979 | `CORROBORADO_POR` | `CORROBORADO_POR` | 292 |  |
| 980 | `CORRIGE_A` | `CORRIGE_A` | 977 |  |
| 981 | `CONTINUES` | `CONTINUA!` | 101 |  |
| 981 | `CORRECTS` | `CORRIGE` | 979 |  |
| 982 | `CONTINUES` | `CONTINUA` | 973 |  |
| 983 | `CONTINUES` | `CONTINUA` | 982 |  |
| 985 | `CONTINUES` | `CONTINUA` | 982 |  |
| 986 | `CONTINUES` | `CONTINUA!` | 033 |  |
| 986 | `CORRECTS` | `CORRIGE` | 979 |  |
| 986 | `CORRECTS` | `CORRIGE` | 981 |  |
| 987 | `CONTINUES` | `CONTINUA` | 967 |  |
| 987 | `CONTINUES` | `CONTINUA` | 981 |  |
| 987 | `CORRECTS` | `CORRIGE` | 979 |  |
| 988 | `CONTINUES` | `CONTINUA` | 984 |  |
| 991 | `CONTINUES` | `CONTINUA!` | 033 |  |
| 991 | `CONTINUES` | `CONTINUA` | 986 |  |
| 991 | `CONTINUES` | `CONTINUA` | 987 |  |
| 992 | `CONTINUES` | `CONTINUA` | 188 |  |
| 992 | `CONTINUES` | `CONTINUA` | 991 |  |
| 993 | `CONTINUES` | `CONTINUA` | 980 |  |
| 993 | `NUMERO` | `NUMERO` | 993 | SELF |
| 994 | `CONTINUES` | `CONTINUA` | 988 |  |
| 994 | `CONTINUES` | `CONTINUA` | 988 |  |

**Total**: 172 filas de arista (155 pares distintos, 28
familias de verbo, 99 con destino AMBIGUO: el numero no
identifica un finding y el `!` lo dice) en 76 findings con
aristas salientes.
428 findings sin ninguna relacion declarada.

De las que, 27 salen de etiquetas con VARIOS destinos (multivalor,
rango o lista de ficheros) que antes no se contaban. En la
columna `nota` se ve la etiqueta original y cuantos de sus
destinos resolvieron.
