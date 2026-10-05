# 1542 — la escalera de DRAM es correcta pero sus offsets estaban corridos, y corrige un error mío

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, item 7
CLASSIFICATION=CORROBORACION-INDEPENDIENTE+ERROR-CORRECTION-PROPIA+ERROR-CORRECTION-DE-OTRO-HALLAZGO
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1419 (offsets de los escalones 7-10) y 1533 MIO (un solo ulMemoryID, falso)
ESTADO=PROBADO · la escalera del 1419 se reproduce ENTERA: 11 de 11 valores identicos
       · el paso real es UNIFORME de 52 bytes, y 52 es usRegDataBlkSize, medido
       · los offsets del 1419 estan corridos una ranura desde el escalon 7
       · hay un TERMINADOR CERO en la entrada 11, que el 1419 no anoto y que cierra la tabla
       · y yo escribi en el 1533 que habia un solo ulMemoryID.  HAY ONCE, uno por escalon
```

## 1. Por que me puse a comprobar esto, y no a escribir el item 7

 diecinueve hallazgos previos de reloj. El que sostiene el techo de memoria es el `1419`, que leyo
**once frecuencias de DRAM** de la tabla de parcheo de reloj, y el `1449` construyo el techo de
1500 MHz encima. Ese numero esta en `rx550_asic_geom.h:172-177` y en la constante del driver.

Y mi `1530`, de ayer, habia decodificado esa misma tabla y habia dicho que tiene **un solo
`ulMemoryID`** con 14 escrituras de registro. **Un bloque no tiene once IDs.** O el 1419 se equivoco,
o yo.

Toca comprobarlo antes de escribir nada: es un numero del que depende el techo de reloj del proyecto.

## 2. El 1419 tiene la escalera correcta y los offsets corrida

Leyendo el volcado yo, en cada uno de los once offsets que el 1419 declara:

```text
  idx  offset     leido     el 1419 dice   veredicto
   0   0xA393     40000        40000       OK
   1   0xA3C7     80000        80000       OK
   2   0xA3FB     90000        90000       OK
   3   0xA42F    100000       100000       OK
   4   0xA463    112500       112500       OK
   5   0xA497    125000       125000       OK
   6   0xA4CB    137500       137500       OK
   7   0xA533    162500       150000       *** corrido una ranura ***
   8   0xA567    175000       162500       *** corrido una ranura ***
   9   0xA59B    200000       175000       *** corrido una ranura ***
  10   0xA5CF         0       200000       *** corrido una ranura ***
```

**Los valores del 1419 son los once correctos. Los offsets de los cuatro ultimos estan mal**, y el
error nace de un solo sitio: en su tabla el paso de `[6]` a `[7]` es de **104 bytes en vez de 52**.

Con paso uniforme de 52 desde `0xA393`, que es exactamente el `usRegDataBlkSize = 52` que yo medi en
el 1530:

```text
  idx  offset   ulMemClockRange   MHz (unidad 10 kHz)
   0   0xA393        40000          400
   1   0xA3C7        80000          800
   2   0xA3FB        90000          900
   3   0xA42F       100000         1000
   4   0xA463       112500         1125
   5   0xA497       125000         1250
   6   0xA4CB       137500         1375
   7   0xA4FF       150000         1500     <-- el 1419 ponia 0xA533 aqui
   8   0xA533       162500         1625
   9   0xA567       175000         1750
  10   0xA59B       200000         2000
  11   0xA5CF            0            0     <-- TERMINADOR
```

**Once frecuencias, las mismas once, en el mismo orden, con los mismos valores.** El 1419 no se
equivoco en el dato; se equivoco en la direccion, y la direccion es lo que permite reproducirlo.

## 3. Y hay un terminador que nadie habia anotado

La entrada 11 vale **cero**. No es una frecuencia, es el fin de la tabla.

Eso importa por una razon concreta: `usMemClockRange` es un campo de **24 bits**, y `0x00FFFFFF`
—el valor que el 1533 encontro en las otras tres tablas— es **todos los unos**, el comodin. Aqui el
terminador es **todo cero**, que es un centinela distinto y no puede confundirse con el comodin.

**Y da un cierre limpio de la tabla, que antes no existia:** 11 entradas y un cero. La tabla es
autolimitada, asi que no hace falta saber el numero de escalones por otra via.

## 4. Correccion mia, y esta si me afecta a lo que escribi ayer

El `1533` afirmo, textual:

> los cuatro con `ucMemBlkId = 0` [...] el unico con un ID de memoria real

 referring a `usMemClkPatchTbl = 0x00009C40`. **Eso es falso.** No hay un ID: hay **once**, uno por
escalon de reloj, y van desde `0x00009C40` hasta `0x00030D40`. Yo leí el primero y generalicé.

Lo que si se sostiene del 1533, porque no depende de esto:

- `ucMemBlkId` esta en `[31:24]` y `ulMemClockRange` en `[23:0]` (el endianness no cambia las posiciones)
- `0x00FFFFFF` en las otras tres tablas es el comodin de "cualquier reloj"
- el driver no decodifica `ulMemClockRange` en ninguna parte del arbol

Lo que cae es la frase "es el unico con un ID de memoria real", que era una generalizacion mia desde
un solo ejemplo. **Once ejemplos la refutan.**

Y hay una consecuencia que no habia visto: si la tabla tiene once IDs de reloj y `ucMemBlkId` es `0`
en todos, entonces **el SMC selecciona el escalon por `ulMemClockRange` y el `ucMemBlkId` no
participa.** Eso es una lectura del diseno del selector, y es coherente con que los otros tres bloques
usen el comodin.

## 5. Lo que esto NO cambia

```text
  NO SE TOCA   el techo de 1500 MHz.  El 1500 es el escalon [7] de la tabla, y eso no se debate:
               es un escalon real del firmware, no un techo.  El techo real lo discute el 1449.
  NO SE TOCA   la lista de 11 frecuencias.  11 de 11 reproducidas.
  NO SE TOCA   la unidad de 10 kHz, que el 1419 declaro y que la estructura de 24 bits sostiene.
  NO SE TOCA   los 13 registros MC que se programan por escalon.  No los he vuelto a medir.
RIESGO         ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE         reproduccion sobre el volcado con el lector validado de atom_chain.py
               (--self-test: 79 casos, 0 fallos).
```

## 6. Item 7, donde queda

```text
  la escalera de DRAM                       11 de 11, REPRODUCIDA        este
  el paso entre escalones                   52 bytes = usRegDataBlkSize   este
  el terminador de la tabla                 entrada 11 = 0                 este
  los offsets del 1419 en 7-10              CORREGIDOS                    este
  el techo de reloj de memoria              1500 MHz, PROBADO             1449, no se toca
  la unidad de mem_clk_max                  MHz, CORROBORADA             1419
  la unidad de SCLK_DOWN_HYST               NO declarada en la fuente    1110, sigue abierto
  el voltage                               bastante avanzado             1477, 208, 266
```

**El item 7 tiene sus numeros de reloj verificados dos veces por vias independientes, y con el
terminador.** Lo que queda abierto en el es la unidad de un campo de histeresis y la semantica de los
voltajes, y ninguno de los dos se cierra sin el firmware.

## 7. Decision log (§103)

```text
DECISION    publicar la correccion de offsets como correccion, y la escalera como corroborada
WHY         §80 no admite ganador intuitivo, y aqui no hay conflicto: el 1419 y yo medimos lo
            mismo con metodos distintos y coincide 11 de 11.  La correccion es de direccion, no
            de valor, y sin ella la tabla no se puede reproducir.
ALTERNATIVA  no publicar nada, porque los valores son los mismos.  Descartada: los offsets son
            lo que hace falta para volver a medir, y estan mal en un hallazgo PROBADO que cuatro
            hallazgos posteriores citan como fuente.
ALTERNATIVA  dudar del 1419 entero por el hueco de 104 bytes.  Descartada: con paso uniforme los once
            valores salen exactos.  El hueco es un error de calculo del paso, no una tabla rota.
DISCriminante  ninguno necesario: los once valores son un conjunto cerrado y el terminador los
            confirma.  Eso es mas fuerte que cualquier discriminante.
CONSECUENCIA  el 1533 queda corregido en una frase, y el 1419 en cuatro offsets.  La escalera que
            sostiene el techo de reloj del proyecto queda con dos reproducciones independientes.
REVERSIBLE  si el paso no fuera uniforme y hubiera una entrada de 104 bytes que contenga dos
            frecuencias, mis once valores serian los mismos pero la estructura seria otra.  La
            hipotesis del terminador cero hace muy improbable eso.
```

## 8. Una nota sobre como se produjo esto

No he PUBLICADO una errata del 1419 porque me cine la escalera. Me puse a comprobar porque **mi propio
hallazgo de ayer decía que esa tabla tenia un solo ID**, y eso no encaja con once frecuencias. Si no
hubiera leido mi 1533, habria publicado el item 7 apoyada en una tabla que yo mismo habia descrito mal.

**El valor de terminar las cosas no es solo cerrar mas huecos: es que los hallazgos anteriores se van
volviendo comprobables.** Cada uno de mis diez dio un alternativa real, y cuatro corrigieron a los
anteriores. Ese es el mecanismo que tu consejo estaba describiendo, y ya se nota en los numeros.
