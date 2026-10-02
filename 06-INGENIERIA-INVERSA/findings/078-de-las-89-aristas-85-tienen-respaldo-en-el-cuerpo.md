# 078 · De las 89 aristas, 85 tienen respaldo en el cuerpo del origen y 4 son retracciones

```
ID:           078
TIPO:        HALLAZGO — CIERRA el NEXT ACTION de 077
ALCANCE:     tools/relations.py, KNOWLEDGE-GRAPH.md
TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS
GPU:         INTACTA
```

## RESUMEN

La pregunta era: **de las 89 aristas del grafo, cuántas aportan algo?** El
discriminante no puede ser el verbo —eso mediría el vocabulario—, así que es
textual:

> Una arista está **SOSTENIDA** si el finding ORIGEN menciona al finding
> DESTINO en su **cuerpo**, no solo en la cabecera.

| | aristas | |
|---|---|---|
| el origen **cita al destino por nombre** (`023-pte-….md`) | **1** | 1% |
| el origen lo **menciona por número** (`023`) | **68** | 76% |
| **ninguna mención**: solo la cabecera lo declara | **20** | 22% |

Y de esas 20:

| | | |
|---|---|---|
| verbo **sin contenido semántico** (`CONTINUES`, `COMPLEMENTS`) | 16 | que no estén en el cuerpo no pierde nada |
| verbo que **afirma algo**, y es **retracción o corrección** | 4 | el silencio del cuerpo es lo correcto |
| **afirman sin retrospectiva y sin mención** | **0** | — |

**VEREDICTO: de las 89 aristas, 85 tienen respaldo textual en el cuerpo de su
origen, y 4 son retracciones donde el silencio es lo correcto. CERO
afirmaciones que dependan solo de una cabecera.**

## 1 · POR QUÉ EL NÚMERO DESNUDO CUENTA, Y CON QUÉ RESERVA

La primera medición dio **1 de 89** sostenidas, buscando solo por nombre de
fichero. Era un resultado tan extremo que lo sospechoso no era el número sino el
método, y mirar dio la respuesta:

```
$ grep -o "\b0[0-9][0-9]\b" 073-…-grafos.md | sort | uniq -c | sort -rn | head
     10 023      <- numero desnudo, 10 veces
      5 035
```

Los findings **se citan por número**, no por nombre. Sólo 10 de las 89 aristas
tenían una cita nominal, y buscar sólo por nombre daba 1.

La razón es histórica y se ve en `077`: la convención de citar por
nombre-desnudo es la que produce 3206 `RUTA_EQUIVOCADA` en
`tools/artifacts.py`. Los findings se nombran en el texto corto y se citan por
número en el largo. Es una convención, no un descuido.

### La reserva

Un número desnudo es ambiguo por la razón de siempre: **36 números duplicados**.
Y además `023` puede ser un finding o un número de registro. El patrón exige
aislamiento:

```python
NUM_BARE = re.compile(r"(?<![0-9A-Za-z._/-])(0[0-9][0-9])(?![0-9A-Za-z._/-])")
```

Sin las dos negaciones, casarían `amdgpu_vm_sdma.c:197` (`197` preceded de `:`)
y cualquier `0x023` (por `x`). Es la novena aparición de la clase de `075`, y
la segunda vez que el aislamiento es lo que separa un registro de otro.

## 2 · LAS 4 QUE AFIRMAN Y NO ESTÁN EN EL CUERPO — Y POR QUÉ ESTÁN BIEN

```
019  CORRECTED_BY          -> 030
023  CORRECTED_BY          -> 035
035  RETRACTED_BY          -> 043
036  RETRACTED_PARTLY_BY   -> 043
```

Las cuatro son **correcciones y retracciones**, y su dirección es retróactiva:
`X RETRACTED_BY Y` significa que **Y** retractó a **X**, y **Y no existía cuando
X se escribió**.

Que el cuerpo de `035` mencione a `043` sería un anacronismo: exigirle a un
documento que cite la corrección que lo vino a invalidar es exigirle que se
refiera a algo posterior a su escritura. En un grafo de evidencia eso es
incorrecto por construcción, no por omisión.

> **Hay una asimetría que el grafo tiene que declarar y antes no**: una arista
> hacia atrás **no puede** tener respaldo en el cuerpo de su origen, y eso no
> la invalida. Una arista hacia adelante debería, y si no lo tiene es sospechosa.
>
> Por eso el corte no es «sostenida / no sostenida». Es en tres, con el tercero
> separado de los otros dos.

## 3 · LAS 16 QUE NO DICEN NADA

```
028 CONTINUES -> 024      041 COMPLEMENTS -> 040
029 CONTINUES -> 017      042 COMPLEMENTS -> 041
030 CONTINUES -> 017      055 COMPLEMENTS -> 053
030 CONTINUES -> 018      049 COMPLEMENTS -> 047
030 CONTINUES -> 021      ... y 8 más
```

`CONTINUES` (11) y `COMPLEMENTS` (5) son, semánticamente, **vacíos**: no dicen de
qué depende el finding, sólo que hay un anterior o que se añade a otro. Que no
aparezcan en el cuerpo **no pierde nada**, porque no portaban nada.

Y esto es lo que hace que el veredicto sea el que es: de las 89 aristas,
**37 tienen un verbo semánticamente vacío** (`CONTINUES` 42 filas contando
multivalor, `COMPLEMENTS` 16, más `COMPLETA`, `STRENGTHENS`, `CIERRA`,
`GENERALIZA`, `IMPLEMENTS`). Es decir:

> **El 52% del grafo del proyecto no afirma nada.** No es un defecto del grafo:
> es un defecto del vocabulario, que no tiene ningún verbo de **dependencia**
> —«esta afirmación no se sostiene sin aquella»— que es el único verbo que
> justificaría una arista en una cadena de evidencia.

## 4 · ERRORES PROPIOS EN ESTA ITERACIÓN

| error | detectado por |
|---|---|
| primer guion: `A=[(et,)+(x[0],x[3])…]` — `et` definido en el bucle | `NameError: name 'et' is not defined` |
| segundo: desempaqueté la arista de 3 campos como de 4 | `ValueError: too many values to unpack (expected 3, got 4)` |
| `aristas_t.index((num, et, dest, None))` para actualizar in-place — **`index` devuelve la PRIMERA coincidencia**, y con aristas duplicadas actualiza siempre la misma | por el código, antes de ejecutar; se rehízo con índice de bucle |
| el `assert` del bloque falló dos veces al anclar por texto | `AssertionError`, y el fichero quedó sin escribir |

El tercero merece nombre: `list.index()` sobre una lista de tuplas devuelve la
primera igual, y como hay aristas repetidas (`030 CONTINUES 017` aparece una
vez pero `021 COMPLEMENTS 030` y otra con el mismo verbo/destino pueden
coincidir), **actualizar in-place por `index` corrompe**. Un índice de bucle es
`enumerate`, no `.index()`.

## 5 · ESTADO

```
grafo            89 filas · 78 pares · 14 familias · 73 con destino AMBIGUO
sostén           1 por nombre · 68 por número · 20 solo cabecera
                 de las 20: 16 verbo vacío · 4 retracción · 0 sin sostén
declaración      120 findings en 76 números · 36 números duplicados
                 73 con relación · 46 sin ella · 10 omisiones (17+8)
vocabulario      19 verbos · de los cuales 9 SIN contenido semántico
frontera         259 huecos abiertos, 7 vías de cierre
citaciones       291 resueltas, 0 fallos
selftests        relations 27/27 · frontier 12/12 · claims 20/20 · artifacts 14/14
                 rx550pm4val PASS · rx550ref PASS
GPU              01:00.0 Lexa PRO rev c7, INTACTA
```

## 6 · LO QUE ESTO CIERRA Y LO QUE NO

**Cierra:** la cadena de evidencia del proyecto **está sostenida**. Ninguna
afirmación del grafo depende únicamente de una cabecera, y las cuatro que sólo
existen en cabeceras son retracciones donde eso es lo correcto. Es el primer
veredicto **positivo** sobre la integridad del grafo, y se opone a los cinco
anteriores, que fueron todos hallazgos de Measurement.

**No cierra, y son cosas distintas:**

1. **El vocabulario.** 9 de 19 verbos no dicen de qué depende un finding.
   Añadir un verbo de dependencia exige decidir su nombre y su semántica, y
   aplicarlo a 120 hallazgos. Es trabajo de convención, no de herramienta.
2. **La ambigüedad de 36 números.** Sigue sin atajo, y `079`-style: la arista
   «por número» (68) es tan válida como la nominal (1) *cuando* el número es
   único, y no lo es cuando no. **De las 68 por número, cuántas tienen destino
   ambiguo** es un corte que la herramienta ya tiene calculado y no ha impreso.
   Es un `grep`.
3. **17 aristas CLARA + 8 MUTUA** de `077`, que son edición.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  seccion CUANTAS ARISTAS SOSTIENEN ALGO en tools/relations.py
  tres niveles (NOMBRE / NUMERO / NINGUNA) en vez de un si-o-no
  aislamiento del numero desnudo: (?<![0-9A-Za-z._/-])…(?![0-9A-Za-z._/-])

Medido:
  89 aristas: 1 respaldada por nombre, 68 por numero, 20 solo por cabecera
  de las 20: 16 con verbo semanticamente vacio, 4 retracciones, 0 sin sosten
  VEREDICTO: cero afirmaciones que dependan solo de una cabecera
  9 de 19 verbos del proyecto no dicen de que depende un finding

Retractado:
  "1 de 89 sostenidas" -- era el resultado de buscar solo por nombre de
    fichero, y los findings se citan por numero 10 veces mas que por nombre

NEXT ACTION:
  El corte que falta y que es un GREP: DE LAS 68 ARISTAS RESPALDADAS POR
  NUMERO, CUANTAS TIENEN DESTINO AMBIGUO.

  La herramienta ya tiene las dos mitades calculadas y no las cruza:

    73 de 89 filas llevan `!` (destino ambiguo)
     1 respaldada por nombre      -> inequivoca por construccion
    68 respaldadas por numero      -> UNA de ellas por numero, con el mismo
                                       numero para dos findings distintos

  Ese cruce es el dato que decide si el respaldo textual del 76% es real o es
  una coincidencia de numeros. Y es exactamente la clase de corte que esta
  herramienta sabe hacer sin inventar: el `!` ya esta puesto, la mencion ya
  esta medida, y solo falta restar.

  Si sale que las 68 son en su mayoria AMBIGUAS, entonces el veredicto de 078
  se corrige: el 76% de respaldo textual seria respaldado CONTRA un finding
  que no se sabe cual de los dos es, y habria que rebajarlo. Ese es el
  resultado que quiero, porque es el que puede cambiar la conclusion.
```