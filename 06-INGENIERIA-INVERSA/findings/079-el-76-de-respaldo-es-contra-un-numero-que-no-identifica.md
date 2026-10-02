# 079 · El 76% de respaldo textual es contra un número que no identifica un finding

```
ID:           079
RETRACTADO_PARCIALMENTE_POR=091   (solo la clausula del bloqueo; el resto del hallazgo sigue vigente)
CLAUSULA_RETRACTADA=INSECURE_SIG_CLAIM
TIPO:        CORRECCION DE 078 + HALLAZGO
ALCANCE:     tools/relations.py, KNOWLEDGE-GRAPH.md
TOOL:        tools/relations.py v1.0.0, selftest 27/27 PASS
GPU:         INTACTA
CORRIGE_A:   078
```

## RESUMEN

`078` cerró con este veredicto:

> de las 89 aristas, 85 tienen respaldo textual en el cuerpo de su origen, y 4
> son retracciones donde el silencio es lo correcto. **CERO afirmaciones que
> dependan solo de una cabecera.**

El primer `NEXT ACTION` de `078` era precisamente el que podía tumbarlo:

> *Si sale que las 68 son en su mayoría AMBIGUAS, entonces el veredicto se
> corrige.*

**Salen.** Y no «en su mayoría»: **58 de 68**.

> **Nota sobre el denominador, y es importante**: estas cifras se midieron con
> 89 aristas. Al escribir `078` y este mismo hallazgo, el grafo pasó a **91** y
> el corte volvió a dar 13/58/20. Las 58 y las 20 no se mueven; las totales sí,
> porque **el grafo crece con cada hallazgo que escribo**. Cualquier cifra de
> este hallazgo es válida para el corpus en el momento de medirla, y hay que
> volver a medirla después de escribir. Un recuento que no lleva su fecha es un
> número sin sujeto.

## 1 · EL CORTE

La herramienta tenía las dos mitades calculadas y no las cruzaba: `!` (destino
ambiguo, de `073`) y el nivel de respaldo (de `078`). El cruce:

| respaldo | destino **único** | destino **AMBIGUO** | total |
|---|---|---|---|
| `NOMBRE` (cita el fichero) | 0 | **1** | 1 |
| `NUMERO` (menciona `023`) | **12** | **58** | 68 |
| `NINGUNA` (solo cabecera) | 4 | 16 | 20 |
| | **16** | **75** | 89 |

## 2 · POR QUÉ EL VEREDICTO DE 078 ERA DEMASIADO FUERTE

Un respaldo textual dice que **el origen menciona al destino**. Con 36 números
duplicados, mencionar `023` no dice **cuál** de estos dos:

```
023-pte-productor-sdma-gfx8.md
023-pm4-count-convencion-medida.md
```

`078` majeures **`023 AMENDA 022`** y **`035 CORRECTS 023`**, y el cuerpo de `035`
menciona `023` — pero `035-correccion-ptepde-is-polaris12.md` rectifica la
**producción de PTE**, que es el primer fichero. La mención acierta. Y
`023-pm4-count-convencion-medida.md` menciona `023` quizá por otra razón.

**No es un error de medición: es un acierto con suerte.** El respaldo prueba que
el origen menciona *un* finding con ese número, no *el* finding al que apunta la
arista. Y cuando hay dos, el texto no siempre puede decidirlo.

### Las tres cifras, y cuál es la buena

```
16 de 89 (18%)   respaldo textual Y destino inequívoco   <- lo que se sostiene
58 de 89 (65%)   mención por número, pero el número es ambiguo
 1 de 89  (1%)   cita por nombre, con destino ambiguo
20 de 89 (22%)   sin mención en el cuerpo (16 verbo vacío + 4 retracción)
```

**El 18%, no el 76%.** Las 12 de destino único son de las más fuertes del
proyecto: se cita un número que existe una sola vez, en un cuerpo que lo
menciona. La de nombre es igualmente válida aunque el número sea ambiguo —**el
nombre no es ambiguo aunque su número lo sea**—, y por eso la cuenta correcta es
**13**, no 12.

| | aristas |
|---|---|
| respaldo inequívoco (nombre, o número único) | **13** |
| mención por número, con dos findings del mismo número | 58 |
| sin mención en el cuerpo | 18 |

## 3 · LA AVERGÜENZA, DICHA SIN MAQUILLAJE

El `NEXT ACTION` de `078` decía que ese corte era «el resultado que quiero,
porque es el que puede cambiar la conclusión». Lo fue.

> **Escribí un veredicto positivo en `078` y en la línea siguiente escribí cómo
> comprobar si era falso. Ejecuté el cruce y el veredicto se cae de 85 a 13.**
>
> El error no fue medir mal: la medición de `078` era correcta —1 por nombre, 68
> por número, 20 sin mención— y el número era 68, no 13. El error fue **elegir
> el agregado que favours la conclusión** sin mirar el cruce que la podía
> tumbar, cuando ese cruce estaba a una línea de código y ya estaba calculado.
>
> No es la primera vez que en este proyecto sale un número plausible que
> favorece lo que uno quiere. La diferencia es que aquí lo busqué yo, y aquí lo
> encontré yo. Eso es lo que hace que buscarlo valga la pena.

## 4 · ERRORES PROPIOS

Ninguno en esta iteración: el cruce es un `grep` sobre dos salidas que ya
existían. Lo que sí hay es el error de razonamiento de `078`, arriba, y queda
registrado como tal.

## 5 · ESTADO

```
grafo            89 filas · 78 pares · 14 familias · 73 con destino AMBIGUO
respaldo         13 inequívocas (18%)   <- la cifra buena
                 58 por número, destino ambiguo (65%)
                 18 sin mención en el cuerpo (16 verbo vacío + 4 retracción)
declaración      123 findings · 78 números distintos · 36 duplicados
                 73 con relación · 46 sin ella · 10 omisiones (17 CLARA + 8 MUTUA)
vocabulario      19 verbos, 9 sin contenido semántico
frontera         259 huecos abiertos, 7 vías
citaciones       291 resueltas, 0 fallos
selftests        relations 27/27 · frontier 12/12 · claims 20/20 · artifacts 14/14
                 rx550pm4val PASS · rx550ref PASS
GPU              01:00.0 Lexa PRO rev c7, INTACTA
```

## 6 · LO QUE SIGUE ABIERTO, ORDENADO POR CUÁNTO VALE

**1 · La ambigüedad de 36 números.** Es el bloque de más valor y **sigue sin
herramienta**, y ahora se sabe por qué: 58 de las 89 aristas son
irrecuperables sin desambiguar, y desambiguar exige decidir a cuál de los dos
iba cada mención del cuerpo. La herramienta puede *proponer* por parecido de
título, y proponer es inventar.

La excepción es la que `077` ya encontró: las citas **por nombre** no son
ambiguas. Y hay hallazgos que citan por nombre.

**2 · Un verbo de dependencia.** 9 de 19 verbos no dicen de qué depende un
finding. Sin uno, la mitad del grafo no afirma nada. Es convención, no
herramienta, y exige decidir el nombre y la semántica antes de aplicarlo a 122
hallazgos.

**3 · Las 25 aristas clara/mutua de `077`.** 17 CLARA escribibles sin leer, 8
MUTUA que exigen lectura.

**4 · 20 findings sin ninguna etiqueta de cabecera.** Mecánico y auditable:
tras hacerlo, el recuento debe ser 0.

**5 · Sin atajo técnico:** `FUNCTION=always` (`NOT_PUBLISHED`, discriminante en
`056 §7`, requiere inyección PM4/IB) y cargar un módulo propio
(`CONFIG_MODULE_SIG_ALL=y` + `CONFIG_SECURITY_LOCKDOWN_LSM=y`).
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  el cruce de 078: respaldo textual x ambiguedad de destino

Medido:
  89 aristas
    13 con respaldo INEQUIVOCO  (nombre, o numero que existe una vez)
    58 con mencion por numero pero destino AMBIGUO
    18 sin mencion en el cuerpo (16 verbo vacio + 4 retraccion)

Retractado por este hallazgo:
  078: "de las 89 aristas, 85 tienen respaldo textual ... CERO afirmaciones
       que dependan solo de una cabecera"
  El aggregation era correcto y la conclusion incorrecta: el 85 no cruzaba con
  la ambiguedad. La cifra buena es 13.

NEXT ACTION:
  Poner el CRUCE en la herramienta y no solo en el hallazgo. La seccion
  CUANTAS ARISTAS SOSTIENEN ALGO tiene que imprimir la tabla de 2x2 --respaldo
  x ambiguedad-- y no solo el total por nivel de respaldo, porque el total
  agregado es exactamente lo que produjo un veredicto falso dos hallazgos
  seguidos.

  Regla que sale de aqui, y que es general: CUANDO UN RECUENTO SE DESCOMPONE,
  IMPRIMIR LA DESCOMPOSICION. Un total agregado invita a ser ledo; una tabla
  cruzada obliga a mirar la interseccion, que es donde estaba el problema.

  Y luego, con la herramientaya debiendo imprimirlo, el unico trabajo que queda
  con valor real es el que ninguna herramienta puede hacer: DECIDIR, para 58
  aristas con destino ambiguo, a cual de los dos findings apunta cada una.
  Eso es lectura, y son 58.
```