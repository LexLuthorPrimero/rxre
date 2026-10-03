# CONTRADICTIONS

<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la siguiente ejecucion lo sobrescribe. -->

Aristas que corrigen, rectifican o retractan, con el verbo
**MEDIDO** por `tools/relations.py` y el **sentido** calculado.

El sentido se calcula, no se lee del nombre de la etiqueta: una
arista mal leida marca como caducado al finding que corrige, que es
peor que no detectar la retraccion.

El sentido se calcula solo para `_BY`, la unica terminacion
inequivoca. Para `CERRADO_POR`, `MEDIDO_EN_MI_ASIC_POR`,
`GENERALIZADO_POR` y `CORRIGE_LA_POLITICA_DE` se imprime el verbo
tal cual con la marca de que su sentido NO esta calculado: cuatro
verbos que acaban igual pero significan cuatro cosas, y

  `043 | CERRADO_POR | 046`  ->  "046 RECIBE de 043"   **FALSO**
  lo correcto es que 043 queda cerrado POR 046.

Que verbos cuentan como de contradiccion es una lista POSITIVA de
12, no una negation. Los demas se declaran abajo, porque un verbo
nuevo que no entre en la lista tiene que verse, no desaparecer.

| desde | verbo | normalizado | hacia | sentido |
|---|---|---|---|---|
| 019 | `CORRECTED_BY` | `CORRIGIDO_POR!` | 030 | 019 RECIBE de 030 |
| 023 | `AMENDA` | `CORRIGE` | 022 | 023 AMENDA a 022 |
| 023 | `CORRECTED_BY` | `CORRIGIDO_POR!` | 035 | 023 RECIBE de 035 |
| 030 | `CORRECTS` | `CORRIGE` | 019 | 030 CORRECTS a 019 |
| 035 | `CORRECTS` | `CORRIGE!` | 023 | 035 CORRECTS a 023 |
| 035 | `RECTIFIES` | `CORRIGE!` | 024 | 035 RECTIFIES a 024 |
| 035 | `RETRACTED_BY` | `RETRACTADO_POR!` | 043 | 035 RECIBE de 043 |
| 036 | `RETRACTED_PARTLY_BY` | `RETRACTADO_PARCIALMENTE_POR!` | 043 | 036 RECIBE de 043 |
| 043 | `CERRADO_POR` | `CIERRA!` | 046 | 043 --CERRADO_POR-> 046  (sentido NO calculado) |
| 043 | `RETRACTS` | `RETRACTA!` | 035 | 043 RETRACTS a 035 |
| 047 | `CORRECTS_RUTA` | `CORRIGE!` | 046 | 047 CORRECTS_RUTA a 046 |
| 047 | `CORRIGE` | `CORRIGE!` | 051 | 047 CORRIGE a 051 |
| 048 | `CORRECTS` | `CORRIGE!` | 040 | 048 CORRECTS a 040 |
| 051 | `CORRIGE_LA_POLITICA_DE` | `CORRIGE_LA_POLITICA!` | 046 | 051 --CORRIGE_LA_POLITICA_DE-> 046  (sentido NO calculado) |
| 059 | `CORRECTS` | `CORRIGE` | 058 | 059 CORRECTS a 058 |
| 060 | `CORRECTS` | `CORRIGE` | 059 | 060 CORRECTS a 059 |
| 110 | `CORRIGE` | `CORRIGE` | 106 | 110 CORRIGE a 106 |
| 135 | `CERRADO_POR` | `CIERRA` | 191 | 135 --CERRADO_POR-> 191  (sentido NO calculado) |
| 182 | `CORRIGE` | `CORRIGE` | 144 | 182 CORRIGE a 144 |
| 974 | `CORRECTS` | `CORRIGE!` | 131 | 974 CORRECTS a 131 |
| 976 | `CORRECTS` | `CORRIGE` | 974 | 976 CORRECTS a 974 |
| 976 | `CORRECTS` | `CORRIGE!` | 101 | 976 CORRECTS a 101 |
| 978 | `CORRECTS` | `CORRIGE` | 976 | 978 CORRECTS a 976 |
| 978 | `CORRECTS` | `CORRIGE!` | 101 | 978 CORRECTS a 101 |
| 981 | `CORRECTS` | `CORRIGE` | 979 | 981 CORRECTS a 979 |
| 986 | `CORRECTS` | `CORRIGE` | 979 | 986 CORRECTS a 979 |
| 986 | `CORRECTS` | `CORRIGE` | 981 | 986 CORRECTS a 981 |
| 987 | `CORRECTS` | `CORRIGE` | 979 | 987 CORRECTS a 979 |

**Total**: 28 aristas de contradiccion, 11 verbos.

## Verbos de relacion que NO son de contradiccion

No son un error: son relaciones de otro tipo que el grafo de
contradicciones excluye a proposito. Se listan para que la
exclusion sea visible.

| verbo | usos |
|---|---|
| `CONTINUES` | 66 |
| `COMPLEMENTS` | 10 |
| `CORROBORADO_POR` | 5 |
| `CLAUSULA_RETRACTADA_POR` | 4 |
| `CONFIRMA` | 3 |
| `HALLAZGO` | 3 |
| `CIERRA` | 2 |
| `COMPLETA` | 2 |
| `CORRIGIDO_POR` | 2 |
| `GENERALIZA` | 2 |
| `IMPLEMENTS` | 2 |
| `RETRACTADO_PARCIALMENTE_POR` | 2 |
| `AUDITA` | 1 |
| `CONFIRMADO_POR` | 1 |
| `CORREGIDO_POR` | 1 |
| `CORRIGE_A` | 1 |
| `GENERALIZADO_POR` | 1 |
| `MEDIDO_EN_MI_ASIC_POR` | 1 |
| `MEDIDO_POR` | 1 |
| `MISMA_CLASE_QUE` | 1 |
| `NUMERO` | 1 |
| `REFINA` | 1 |
| `RESUELVE` | 1 |
| `RETRACTADO_POR` | 1 |
| `RETRACTA_LA_PROMESA_DE` | 1 |
| `STRENGTHENS` | 1 |

26 verbos excluidos, 117 aristas.
Si aparece uno nuevo aqui, es que no se ha decidido que clase es -- que es distinto de que no lo sea.
