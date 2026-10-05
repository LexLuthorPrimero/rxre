# 1186 — `rxre`: las reglas del proyecto, convertidas de prosa a código ejecutable. Y el vector que encontró que **la frontera dura estaba mal planteada**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL-ENGINE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 ni 0000:00:02.0
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (84 vectores, rc=0)
CLASE=TOOL-FACTORY + VALIDATION · ESTADO=PROBADA_OK
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · Qué hay aquí y qué no

```text
CONSTRUIDO Y PROBADO
  TOOL REGISTRY      27 herramientas, 14 campos, hallazgos INCRUSTADOS en el texto
  CAPABILITY INDEX   20 capacidades, pregunta -> cadena -> pipeline ordenado
  LAS TRES PUERTAS   frontera / ganancia / reversibilidad, con(vector) propia
  PROBE              baja PRESENTE_SIN_PROBAR a VERIFICADA con evidencia real
  REGISTRO ABIERTO   una herramienta nueva entra SIN editar codigo
  VALIDADORES        las 9 reglas del proyecto, EJECUTABLES
  DISCRIMINANTE      el paso mas barato que separa dos modelos vivos
  CACHE CON HASHES   entrada, salida, version y procedencia, o nada

DECLARADO Y NO HECHO
  grafo de relaciones sobre el corpus
  capa de normalizacion por herramienta
  "aprender que herramienta sirve para cada pregunta"
  ejecucion real del pipeline (solo planificacion y sonda)
  adapters que an stdout a un registro comun
```

Lo que **no** esta hecho esta aqui, no en un diagrama. Una caja vacia con
nombre de capa es teatro de herramientas (§99), y un diagrama con diez cajas
vacias es peor que no tener diagrama: promete lo que no hay.

## 1 · LA FRONTERA DUERA ESTABA MAL PLANTEADA, Y LO ENCONTRÓ UN VECTOR

El diseño inicial usaba `solo_lectura` para la puerta de frontera. Es
**incorrecto**, y el vector lo enseño:

```text
puerta("dynamic_debug", ...)  ->  False, frenada_por FRONTERA_INTEL
```

`dynamic_debug` escribe en **tracefs**. Tracefs no es la GPU integrada. La puerta
de frontera, que es **innegociable**, se estaba disparando como si fuera una
politica mas que se puede desactivar con una autorizacion.

Eso hacia dos cosas malas **a la vez**:

1. La frontera dura se parecia como una politica negociable.
2. Una herramienta que **si** tocara la integrada habria pasado por el mismo
   hueco, autorizandola.

Solucion: el campo 14 de la matriz es `toca_integrada`, y las tresPuertas tienen
salidas distintas:

```text
FRONTERA        toca_integrada          -> NO. No hay salida. No hay autorizacion.
GANANCIA        pide_runtime y la       -> NO. Sin riesgo. GANA a la autorizacion:
               estatica ya discrimina      autorizar no compra informacion.
REVERSIBILIDAD  escribe y sin            -> NO. Con autorizacion, SI.
               autorizacion
```

La frontera se prueba con una herramienta **sintetica**, porque en el catalogo no
hay ninguna que toque la integrada. **Ese vacio es el dato**, y por eso la puerta
se prueba igual: para que el dia que aparezca una, no se descubra que el camino
no estaba probado.

Y la matriz gano un campo entero (`toca_integrada`) por eso. El selftest de
`1183`/`1184` lo habria visto: `matriz: toda fila tiene 14 campos`.

## 2 · LA PUERTA DE GANANCIA FRENA INCLUSO LO QUE ES SEGURO

```text
$ rxre find-tool --goal "en vivo: traza cuantas veces se entra en una funcion" \\
      --estatica-suficiente

!! 1. dynamic_debug   FRENADA POR GANANCIA_INFORMACION
!! 2. bpftrace        FRENADA POR GANANCIA_INFORMACION
!! 3. trace-cmd       FRENADA POR GANANCIA_INFORMACION   <-- solo LECTURA
```

`trace-cmd` **no escribe nada** y aun asi queda frenada. Y eso es lo correcto: la
puerta de ganancia trata de **valor**, no de riesgo. Si la evidencia estatica ya
discrimina, una traza no aporta informacion: aporta coste. Autorizar una
herramienta que no va a decir nada nuevo es gasto, y el riesgo es secundario.

## 3 · LOS VALIDADORES: LO MAS CARO DEL PROYECTO, AHORA EJECUTABLE

Las nueve reglas salieron de hallazgos donde la regla equivocada costo trabajo.
Enquanto en prosa son advice; en codigo son una puerta que falla con codigo de
salida distinto de cero.

```text
AUSENCIA_NO_ES_INEXISTENCIA      NOT_FOUND != PROVEN_ABSENT
VERDE_NO_ES_CORRECTO              rc=0 no certifica el resultado
SOFTWARE_NO_ES_HARDWARE          el analisis estatico no es OBSERVED
COMPILAR_NO_ES_EJECUTAR          compilar no dice que se comporte bien
REPRESENTACION_NO_ES_FUENTE      un desensamblado es HIPOTESIS
SIN_PROBAR_NO_ES_DISPONIBLE      estar en el disco no es estar verificado
NULO_NO_ES_CERO                  un valor ausente no se rellena con 0
COINCIDENCIA_UNICA_NO_ES_INDEP.   una coincidencia no corrobora
DECODIFICADO_NO_ES_VERIFICADO    decodificar no es probar
```

Cada una tiene un caso que la hace **FALLAR**, y hay un vector que lo comprueba
para las nueve: una regla que no puede fallar no es una regla.

```text
$ rxre valida --regla AUSENCIA_NO_ES_INEXISTENCIA \\
      --caso '{"busqueda":"rg","resultado":"NOT_FOUND","veredicto":"PROVEN_ABSENT"}'
AUSENCIA_NO_ES_INEXISTENCIA   FALLA   se declara PROVEN_ABSENT tras NO FIND
```

Y el tri-estado, que es lo que hace que esto sirva:

```text
PASA           la regla se respeta
FALLA          se incumple, y esto es un HALLAZGO
NO_APLICA      falta el dato; NO se aprueba por omision
```

**`NO_APLICA` nunca es `PASA`.** Esa confusion es exactamente lo que las reglas
existen para evitar, asi que el validador no la cometia.

La ultima regla se aplica al propio `1185`: un decodificado sin reensamblado es
un decodificado, no una prueba. Por eso `1185` reensambla.

## 4 · EL DISCRIMINANTE, Y POR QUE ES LA PIEZA QUE MAS COSTA EVITAR

```text
$ rxre discriminante --modelos "H1 por el anillo" "H2 directo" --pruebas '[
    {"nombre":"grep",       "h1":"R","h2":"R","coste":1},
    {"nombre":"round-trip", "h1":"A","h2":"B","coste":2},
    {"nombre":"MMIO",       "h1":"X","h2":"Y","coste":3,"necesita_runtime":true}]'

{"estado":"OK","prueba":"round-trip","coste":2}
```

`grep` esta mas barato y **no separa**: da lo mismo bajo los dos modelos. Ese es
el filtro, y por eso `separa` se calcula antes que `coste`. Sin el, el motor
propondria el grep, veria que no separa, y volveria a proponer el grep.

Y el MMIO se pondera ×3 por ser runtime: el orden es lo que importa, y el runtime
tiene reversibilidad y riesgo. Cuando **ninguna** prueba separa:

```text
{"estado":"SIN_DISCRIMINANTE",
 "motivo":"ninguna prueba separa los modelos: hay que INSTRUMENTAR, no ejecutar"}
```

Que es la distincion que mas caro sale olvidar: se llega a instrumentar cuando lo
que hacia falta era **medir**.

## 5 · EL REGISTRO ABIERTO, Y POR QUE NO SE REESCRIBE

```text
$ rxre register-tool --name clrxdisasm --cap ISA_DECODE \\
      --limitaciones "AUSENTE en esta maquina (1185)"
REGISTRADA: registrada como PRESENTE_SIN_PROBAR: hay que probarla
```

El requisito era "si manana aparece una herramienta nueva, no hay que modificar el
comportamiento de todas las IAs". Se cumple con un fichero aparte
(`RXRE-REGISTRY.json`) que se lee al arrancar. **No** se reescribe `CAP` a mano: si
las herramientas vivieran en el codigo, cada alta seria un cambio de codigo y
habria que revalidar el nucleo entero.

Y al registrarse nace **`PRESENTE_SIN_PROBAR`**, no `DISPONIBLE`. Registro no es
verificacion, y el propio validador `SIN_PROBAR_NO_ES_DISPONIBLE` lo haria fallar
si el registro lo declarara disponible.

## 6 · TRES ERRORES PROPIOS, Y LOS TRES SALIERON DE LOS VECTORES

| error | sintoma | por que no se vio leyendo |
|---|---|---|
| frontera confundida con "escribe en el sistema" | `dynamic_debug` frenado como si tocara la i915 | el codigo se leia bien; lo que estaba mal era el **modelo** |
| expectativa de probe contra la salida real | `pahole` FALLO con `rc=0` y evidencia `v1.30` | la expectativa era "pahole" y la herramienta imprime su version |
| vectores que reentran en el dispatch | `rxre --selftest` colgaba | dos vectores llamaban a `main()` **desde dentro** de `selftest` |

El tercero es el mas caro y el mas instructive: se manifiesta como **desbordamiento
de pila**, no como fallo de test. Un test que cuelga el harness no dice que esta
mal; dice que la maquina esta mal.

> **Un vector que ejecuta el codigo que prueba puede colgarse.** El cableado se
> comprueba leyendo, no reentrando.

## 7 · LA INCONSISTENCIA QUE EL PROPIO PROYECTO SE BUSCO

```text
toolreg.py --selftest   ->  22 vectores
rxre.py     --selftest   ->  no hacia nada, rc=2   (usa subcomandos)
```

Dos instrumentos del proyecto con la misma palabra significando cosas distintas.
Un agente que aprende `--selftest` de uno lo aplica al otro y no obtiene nada: es
la dependencia de memoria que este proyecto viene a quitar, **metida dentro de la
herramienta que la quita**. Ahora ambas formas funcionan y ambas dan 84 y 22.

## 8 · Procedimiento

```text
construido   tools/rxre.py, 84 vectores, rc=0
             las tres Puertas, con vector propio y sin salida en la frontera
             9 validadores ejecutables, cada uno con un caso que lo hace fallar
             motor de discriminantes: separa antes que coste, pondera runtime
             registro extensible por fichero, nace SIN PROBAR
             cache con hash de clave, valor, version y procedencia

medido       toolreg 22 · layoutcross 79 · mmio 48 · oraculo 116 vectores
             ibref 77 de 116 (1183, sin cerrar)
             verif DERIVA en 11 de 51: dos instrumentos nuevos cambian el
             recuento que varias medidas dan por bueno, y no se re-fija la base

no hecho     grafo de relaciones, normalizacion por herramienta, ejecucion real
             del pipeline. Declarado arriba, no dibujado.

escrituras   0 ficheros de otros agentes; nada commiteado
runtime      RUNTIME=NOT_RUN. Ni la RX550 ni la Intel.
```