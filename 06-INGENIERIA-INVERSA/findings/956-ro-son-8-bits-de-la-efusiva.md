# 956 · `ro` son 8 bits de la efusiva, y el clock stretching cubre el 79 % inferior

> ## CORRECCION — este hallazgo contiene numeros INVALIDADOS. Ver `957`.
>
> La lectura de las formulas de `polaris10_smumgr.c:1680-1683` fue **erronea**:
> los grupos parentizados son **divisiones**, no restas. La linea esta cortada por
> `cut -c1-104` justo donde esta el `/` y la continuacion `\`.
>
> Lo que **NO** se sostiene: el "79 % inferior" y la tabla de `efuse_max` por nivel.
>
> Lo que **si** se sostiene y no depende de esa lectura: que `ro` usa 8 bits de la efusiva, indice 268, shift 24, mask 0xFF; que el `/255` de la formula es el dominio de 8 bits del origen; que el nivel 0 nunca aplica offset.
>
> **El texto de abajo se conserva integro**, a proposito: es la v1, y el
> mecanismo del error es evidencia.


WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **La efusiva no se lee de un registro: la lee el VBIOS ejecutando un comando
> ATOM.** Por eso `ro` es el único `RUNTIME_MISSING` de mi línea sin dirección, y
> por eso no la tendrá nunca.
>
> Y al medir sus parámetros sale lo que hace la línea casi completa:
>
> **`ro` son 8 bits exactos de la efusiva. Con eso, el `/255` de la fórmula deja de
> ser una constante arbitraria, y los umbrales de `947` se vuelven un porcentaje
> del silicio posible de mi placa.**

## 1. El mecanismo, que no es el que yo suponia

```
ppatomctrl.c:922-947   atomctrl_read_efuse(hwmgr, start_index, end_index, efuse)
    efuse_param.sEfuse.usEfuseIndex = cpu_to_le16((start_index / 32) * 4);
    efuse_param.sEfuse.ucBitShift   = (start_index - ((start_index / 32) * 32));
    efuse_param.sEfuse.ucBitLength  = (end_index - start_index + 1);

    result = amdgpu_atom_execute_table(adev->mode_info.atom_context,
                    GetIndexIntoMasterTable(COMMAND, ReadEfuseValue),
                    (uint32_t *)&efuse_param, sizeof(efuse_param));

    *efuse = result ? 0 : le32_to_cpu(efuse_param.ulEfuseValue) & mask;
```

**Es una ejecucion de comando ATOM del VBIOS**, no una lectura de registro. El host
solo pasa un bloque de parametros y recibe el valor de vuelta.

**Consecuencia directa sobre mi clasificacion:** `ro` **no tiene direccion**, y no
es que yo no la haya encontrado. **No existe una direccion**, porque la lectura no
es un acceso de memoria: es el VBIOS leyendo la efusiva del ASIC con su propio
microcodigo. **Es el unico `RUNTIME_MISSING` de la linea con un motivo
irreducible, y el motivo es de naturaleza distinta al de los otros siete.**

## 2. Los parametros exactos, y por que no estaban donde los busque

Los straps **no estan en ninguna cabecera**:

```
grep -r STRAP_ASIC_RO_LSB en todo drivers/gpu/drm/amd/   ->  2 coincidencias, ambas en .c
polaris10_smumgr.c:1647   #define STRAP_ASIC_RO_LSB    2168
polaris10_smumgr.c:1648   #define STRAP_ASIC_RO_MSB    2175
vegam_smumgr.c:57         #define STRAP_ASIC_RO_LSB    2168
```

**Son `#define` locales dentro del propio `.c`**, diez lineas antes de la funcion
que los usa. Los perdi buscandolos en `pm/powerplay/inc/`, que es donde estan
**todos** los demas.

Con los valores:

```
mask          = 0x000000FF
usEfuseIndex  = (2168 / 32) * 4   = 67 * 4  = 268
ucBitShift    = 2168 - 2144       = 24
ucBitLength   = 2175 - 2168 + 1   = 8
```

**Y encaja exacto: 24 + 8 = 32, un byte alineado de una palabra.** No es
aproximado, es un byte limpio de la palabra de efusiva 268.

**`ro` se construye con 8 bits de la efusiva del ASIC. Punto.**

## 3. El `/255 deja de ser una constante

```
ro = ((efuse * (ro_range_max - ro_range_min)) / 255) + ro_range_min
```

Con `ro_range = 1100..2100` (`947`, rama else de `chip_id == CHIP_POLARIS12`):

```
ro = ((efuse * 1000) / 255) + 1100
```

**El 255 es el dominio de 8 bits de `efuse`.** No es un factor de escala
elegido: es el numero de valores distintos que puede tomar el origen. **Y eso fija
la resolucion de `ro` en `1000/255 = 3.92 MHz` por unidad de efusiva.**

**Un numero de la formula de `931` queda explicado por la anchura del dato que
alimenta la formula**, que es un tipo de corroboracion que no habia usado: no dos
fuentes dicen lo mismo, es que **una constante de la forma coincide con una
propiedad de su entrada**.

## 4. Y los umbrales de `947`, en unidades de efusiva

`947` dio el `acomp` por fila, que es donde `volt_with_cks` se sale de `uint32` y la
comparacion se invierte. Traducido al dominio real de mi silicio:

```
nivel  MHz   acomp   efuse_max   % del dominio   el offset se aplica
   0    214    1010           -              -   NUNCA (acomp < ro_min)
   1    551    1213          28             11%   si efuse <= 28
   2    734    1376          70             28%   si efuse <= 70
   3    980    1708         155             61%   si efuse <= 155
   4   1000    1743         163             64%   si efuse <= 163
   5   1020    1781         173             68%   si efuse <= 173
   6   1046    1833         186             73%   si efuse <= 186
   7   1071    1886         200             79%   si efuse <= 200
```

**Dos afirmaciones, y las dos salen de numeros medidos:**

**1. El clock stretching se aplica en el nivel mas alto mientras mi silicio**
```
este por debajo del 79 % inferior de su propio rango de efusiva. Por encima, el
uint32 del voltaje se desborda y el driver no aplica offset.
```

**2. En el nivel mas bajo no se aplica nunca**, porque su `acomp` (1010) esta por
debajo del `ro_min` de mi placa (1100). **Y el VBIOS pone `cks_enable = 0` ahi.**

**Eso convierte la corroboracion de `947` en cuantitativa.** No es «las dos
fuentes coinciden»: es que **el VBIOS desactiva el clock stretching exactamente en
el unico nivel donde la aritmetica del driver no puede sostenerlo para ninguna
efusiva posible de mi placa.** La cifra 79 % es la fraccion de silicio en la que el
mecanismo funciona al nivel mas alto.

## 5. Lo que esto NO es, y es importante decirlo

```
NO es que el 79 % sea la probabilidad de que mi placa lo tenga
NO es que yo sepa en que punto esta mi silicio
NO es que el clock stretching sea bueno o malo para mi placa
```

**`efuse` sigue siendo `RUNTIME_MISSING`.** Lo que he hecho es **acotar donde puede
estar**: en 0..255, con paso 3.92 MHz en `ro`. **Un dato con dominio conocido es
mucho mas util que un dato sin dominio, pero sigue siendo un dato que no tengo.**

Y la consecuencia practica es la que mas me importa: **si mi efusiva esta por
encima de 200, el driver no aplica ningun offset de clock stretching en el nivel
mas alto, y mi placa sube de reloj sin margen electrico.** Esa es una hipotesis
**verificable con una sola lectura**, y es de las que un driver propio tendria que
decidir de forma consciente.

## 6. Errores de esta iteracion

**1. Busque los straps en el directorio de includes durante tres llamadas.**
Estan en el `.c`, diez lineas antes de usarlos. **El `0` de tres searches seguidos
era el mismo error, no tres evidencias**, y debio dispararme el mismo control que
me disparo en `941` y `954`: **cuando N intentos fallan igual, la pista esta en lo
que tienen en comun.**

**2. Conclui «no hay direccion porque no la encuentro»** antes de leer
`atomctrl_read_efuse`. La funcion estaba a un grep de distancia y su cuerpo dice
exactamente lo que no hay. **Mi clasificacion de `ro` como `RUNTIME_MISSING` sin
direccion era correcta por accidente**, y por el motivo equivocado: no era que no
la hubiera buscado, es que **no existe direccion**.

**3.** Escribi «bits en total» a media frase. Cuarta vez hoy, y el verificador la
encontro otra vez. **Es un tic, y la defensa es el verificador, no mi cuidado.**

## 7. Frontier siguiente

```
1.  la efusiva se lee ejecutando un comando ATOM del VBIOS        PROVEN
2.  no hay direccion: no es un acceso de memoria                  PROVEN
3.  ro usa 8 bits, efuse index 268, shift 24, mask 0xFF           PROVEN
4.  los straps son #define locales en el .c, no de una cabecera   PROVEN
5.  ro = ((efuse * 1000)/255) + 1100, paso 3.92 MHz               PROVEN
6.  el /255 es el dominio de 8 bits del origen                     PROVEN_DERIVED
7.  acomp por fila en unidades de efusiva, y cobertura            PROVEN
8.  nivel 7: se aplica con efuse <= 200 de 255, el 79 % inferior   PROVEN_DERIVED
9.  nivel 0: nunca, y el VBIOS lo desactiva                       CORROBORATED
10. efuse concreta                                           RUNTIME_MISSING
11. los otros 6 RUNTIME_MISSING, en 6 direcciones conocidas       RUNTIME_MISSING
```

**La linea de clocks, tension y ventilacion de esta placa queda con su coste
runtime enumerado y cerrado por categorias:**

```
6 valores, en direcciones conocidas (955)    una palabra de 4 bytes cada uno
1 valor, sin direccion posible (esta)        efusiva: lo ejecuta el VBIOS
1 ventana de promediado, sin semantica        SEMANTIC_MISSING
1 techo termico, sin medir                    RUNTIME_MISSING
```

**Y queda una sola pregunta con peso de decision, y es de silicio:** si mi efusiva
esta por encima de 200, el driver no aplica offset de clock stretching en el nivel
mas alto. **Toda la maquina de clock stretching de mi placa depende de ocho bits
que no he leido.**

El frente que me toca, y que no requiere hardware, es **cuantificar que pasaria en
cada caso**, es decir: dado `efuse` en 0..255, que `volt_offset` resulta en cada uno
de los ocho niveles con la aritmetica real de `uint32`, y que tension implicaria
frente a la curva del VBIOS. **Eso convierte la pregunta de «que pasa» en una
tabla, y la tabla es un resultado aunque el dato no venga.**

Criterio de cierre: los ocho `volt_offset` en funcion de `efuse`, con la
aritmetica sin signo de 32 bits del fuente, y el punto de la curva del VBIOS donde
caeria cada uno. Y explicitamente, que parte de esa tabla depende del dato que no
tengo y que parte no.
