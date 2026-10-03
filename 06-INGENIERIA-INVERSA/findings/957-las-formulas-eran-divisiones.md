# 957 · Las fórmulas eran divisiones, y eso invalida tres hallazgos

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Correccion mayor
>
> ```
> CLAIM-931 v2  ro_minimo por nivel = 200,165,137,79,73,66,57,48   REFUTED
> CLAIM-947 v2  acomp por nivel = 1010,1213,...,1886               REFUTED
> CLAIM-956 v2  el clock stretching cubre el 79 % inferior         REFUTED
> CLAIM-957     PROVEN. ro_minimo no existe: la formula no se desborda.
>               volt_offset va de 0 a 17 y DECRECE con la efusiva.
> ```
>
> **Lei `/` como `-`.** Las tres son el mismo error de lectura, y viene del mismo
> sitio.

## 1. La causa exacta, y es la sexta vez

En `929` mostre el codigo asi:

```
polaris10_smumgr.c:1675
    volt_without_cks = (uint32_t)((2753594000U + (sclk_table->entries[i].clk/100) * 136
polaris10_smumgr.c:1676
                        (2424180 - (sclk_table->entries[i].clk/100) * 1132925/1000));
```

**Esa linea esta truncada por `cut -c1-104`, y el corte cae exactamente donde
estan la division y la continuacion `\` de linea.** Lo que hay entre las dos lineas
es `* 136418 - (ro - 70) * 1000000) / \` — **una division por el factor
parentizado**.

**Yo leia `... - (2424180 - ...)` como una resta del factor. Es una division por
el factor.**

**Es la sexta vez hoy que `cut -c<N>` destruye una linea logica**, y las cinco
anteriores me produceran: un bug de precedencia inexistente, un `(ro - 44)`
colocado donde no iba, y ahora **tres hallazgos cuantitativos invalidos**. En
todos los casos el sintoma era el mismo: **un numero plausible, con forma de
medida, y sin forma de comprobarlo porque la fuente estaba cortada justo ahi.**

## 2. La formula real

```c
polaris10_smumgr.c:1680-1683      rama else = mi placa, chip_id != CHIP_POLARIS10

volt_without_cks = (uint32_t)((2416794800U + (clk/100) * 1476925/10
                               - (ro - 50) * 1000000)
                              / (2625416 - (clk/100) * (12586807/10000)));

volt_with_cks    = (uint32_t)((2999656000U - (clk/100) * 392803
                               - (ro - 44) * 1000000)
                              / (3422454 - (clk/100) * (18886376/10000)));

:1686-1688   if (volt_without_cks >= volt_with_cks)
                  volt_offset = (uint8_t)(((volt_without_cks - volt_with_cks
                                            + cks_voffset) * 100 + 624) / 625);
```

**Tres cosas que no estan en lo que yo creia:**

```
1.  el factor de ro es 1000000, no el parentizado
2.  hay una division, y el resultado es un cociente pequeno
3.  (ro - 50) en volt_without y (ro - 44) en volt_with
```

## 3. Y no hay desbordamiento en ninguna parte

```
valor maximo de numerador en toda la formula:  2915596158
limite de uint32:                              4294967295
desbordamiento:                                 NINGUNO
```

**El concepto de `acomp` —«el ro donde volt_with_cks se sale de uint32»— no
existe.** Es un artefacto de mi lectura. `947` lo construyo, `956` lo tradujo a
porcentajes y **ambos estan mal en su totalidad.**

**Toda la aritmetica cabe sobrada en 32 bits sin signo.** Y el resultado es un
cociente: `volt_without_cks` ronda 1000-1200, `volt_with_cks` ronda 1000-1200, y
su diferencia es de **unas unidades**, no de mil millones.

## 4. El resultado correcto

`ro` en 1100..2100 con paso 3.92 MHz, y `volt_offset` con la aritmética real:

```
nivel   MHz    volt_offset sobre efuse 0..255      cks_enable del VBIOS
   0    214    siempre 0                                   0
   1    551    0 .. 4                                      1
   2    734    0 .. 9                                      1
   3    980    2 .. 16                                     1
   4   1000    3 .. 16                                     1
   5   1020    4 .. 16                                     1
   6   1046    5 .. 17                                     1
   7   1071    6 .. 17                                     1
```

**El offset DECRECE con la efusiva.** De 17 en el silicio mas lento a 6 en el mas
rapido, en el nivel mas alto. **Y eso es lo fisicamente esperable**: un oscilador
de anillo mas rapido es silicio mas rapido, y el silicon rapido necesita menos
margen. **El sentido de la dependencia es correcto, y eso es una corroboracion
contra mi propia lectura anterior, que predecia lo contrario sin motivo.**

**Y hay un detalle de implementacion que importa:** `volt_offset` se declara en
`:1659`, **fuera del bucle**, inicializado a 0 y sin resetear. **Si la condicion
no se cumple en un nivel, ese nivel hereda el valor del nivel anterior.** Para mi
tarjeta eso no cambia los niveles altos —siempre se asignan— pero para el nivel 1
y el 2 si, y es el motivo de que sus rangos lleguen a 0.

## 5. La corroboracion con el VBIOS aguanta, y por un motivo mejor

`947` dijo que el VBIOS desactiva el clock stretching en el nivel 0 porque ahi la
aritmetica del driver no puede sostenerse. **El motivo era inventado. El
resultado es el mismo, y la razon correcta es mas simple:**

```
nivel 0 (214 MHz)   volt_offset = 0 para TODA efusiva, sin excepcion
VBIOS               cks_enable = 0 en ese nivel
```

**El driver calcula cero ahi por su cuenta, con toda la efusiva posible.** El
VBIOS desactiva el clock stretching en el unico nivel donde no tendria efecto.
**Las dos fuentes coinciden, y ahora por una razon que se puede enunciar en una
frase y comprobar con la formula, en vez de con un umbral inventado.**

**Ese es el unico resultado de los tres que sobrevive, y sobrevive mejor.**

## 6. Lo que queda en pie de los tres hallazgos corregidos

```
DE 931   la unidad de clk = 10 kHz, del propio kernel              SIGUE
DE 931   los 8 niveles: 214..1071 MHz                              SIGUE
DE 931   clock stretching activo en 7 de 8                         SIGUE
DE 947   asic_type = CHIP_POLARIS12, ro_range = 1100..2100         SIGUE
DE 947   la rama de smu7_hwmgr.c:2573 se ejecuta                   SIGUE
DE 956   ro usa 8 bits de la efusiva, indice 268, shift 24         SIGUE
DE 956   el /255 es el dominio de 8 bits                           SIGUE
DE 956   nivel 0 nunca aplica offset                               SIGUE
DE 931   ro_minimo por nivel                                        CAE
DE 947   acomp por nivel                                           CAE
DE 947   la aritmetica se desborda                                 CAE
DE 956   el 79 % inferior                                          CAE
```

**Ocho afirmaciones sobreviven y cuatro caen.** Las cuatro que caen son las
cuatro que exigian leer la formula, y las ocho que sobreviven son las que se
midieron con una herramienta o con el VBIOS.

## 7. Errores de esta iteracion

**1.** Le `/` como `-` porque la linea venia cortada. **Un corte de linea no es un
corte de linea logica cuando hay continuacion `\`**, y no mire el caracter de
continuacion porque el corte se comio el final de la primera parte.

**2.** Construi sobre la lectura erronea **dos hallazgos completos** —`947` con su
tabla de umbrales, `956` con su porcentaje— **sin volver a la fuente.** Cada uno
partio de un numero plausible: 200, 1010, 79 %. **Ninguno tenia un control que
pudiera fallar**, y por eso los tres pasaron la revision de dominio.

**3.** El dominio dio un veredicto que acepté: «65282 mV es absurdo, es un
bitmask» — eso era cierto de los datos de la tabla VDDGFX, y **lo use como
evidencia de que estaba leyendo bien el resto**. **Un acierto de lectura en un
sitio no valida la lectura en otro**, y yo lo use como si la validara.

**4. La leccion, y es la que mas me cuesta:** **una lectura hecha sobre una linea
truncada no es una lectura con una limitacion, es una lectura sin validar.** Y
cuando la limitacion cae en el operador, no en un parametro, el resultado no es
un valor dudoso: **es una aritmetica distinta**, con numeros que parecen
razonables y no lo son.

## 8. Que hago para que no vuelva a pasar

**La accion obvia es no usar `cut -c` sobre codigo.** Es una regla que llevo
incumpliendo seis veces hoy y que ahora tiene un coste de tres hallazgos.

**Y la regla de fondo:** un numero que sale de una expresion aritmetica no se
acepta hasta que se ha reescrito la expresion **entera** en algun sitio, con los
parentesis, y se ha ejecutado. Es lo que acabo de hacer en Python, y por eso esta
finding tiene un resultado correcto donde las tres anteriores tenian uno falso.

**Es el mismo principio que aplico a los offsets de struct, pero extendido a las
formulas: BTF para layouts, compilacion para offsets, y ejecucion para
aritmetica.**

## 9. Frontier siguiente

```
1.  las formulas son divisiones; yo las lei como restas           PROVEN
2.  no hay desbordamiento de uint32 en ninguna parte              PROVEN
3.  el concepto de acomp de 947 y 956 no existe                   REFUTED
4.  volt_offset va de 0 a 17 y DECRECE con la efusiva             PROVEN
5.  el nivel 0 da 0 para toda efusiva                             PROVEN
6.  volt_offset se hereda entre niveles si no se asigna           PROVEN
7.  el sentido de la dependencia es el fisicamente esperado        CORROBORATED
8.  ro_minimo, acomp y el 79 %                                   REFUTED
9.  efuse concreta                                               RUNTIME_MISSING
```

**La linea tiene ahora su aritmetica verificada y sus tres hallazgos erroneos
marcados. Falta lo unico que no puedo tener: el valor de `efuse`.**

**Pero la tabla que acabo de calcular es el resultado aunque `efuse` no llegue:
es el rango completo de lo que el driver puede escribir, en los ocho niveles, para
toda silicio posible de mi placa.** Y ese rango —0 a 17, decreciente con la
efusiva, cero en el nivel de reposo— **es la especificacion completa de lo que el
clock stretching hace en mi placa.**

El frente util es **traducir ese rango a milivoltios**, que es la unidad en la que
el VBIOS presenta las tensiones y en la que `950` midio los 812 mV reales. Con la
escala `*100/625` del propio fuente y la escalera de 700..1100 mV de la placa,
cada valor de `volt_offset` se puede situar. **Eso convierte «el clock stretching
aplica un offset de 0 a 17» en «aplica entre X e Y milivoltios», que es la unidad
en la que la pregunta «cuanto margen compra» tiene sentido.**

Criterio de cierre: el rango de milivoltios correspondiente al rango de
`volt_offset`, por nivel, con la escala derivada de la propia formula y la escalera
de tension del VBIOS, y **explicitamente que parte de la afirmacion depende de
`efuse` y cual no**. Si la conversion depende de la unidad —que es
`SEMANTIC_MISSING` desde `927`— decirlo, y no suponerla.
