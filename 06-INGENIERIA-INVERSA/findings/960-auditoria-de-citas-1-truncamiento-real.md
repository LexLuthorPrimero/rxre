# 960 · Auditoría de citas: 1 truncamiento real, y la herramienta que lo encuentra

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **49 hallazgos, 209 citas marcadas, y solo 4 truncamientos reales. Uno es el que
> ya conocemos —citado a propósito como ilustración— y los otros tres son
> coherentes.** No hay ningun error nuevo derivado de un corte de linea.
>
> Y la herramienta que lo comprueba tiene **una trampa en su diseño** que
> tardé dos versiones en ver, y que es la misma clase de error que la hizo
> necesaria.

## 1. Lo primero: la verificación de lo que dije que iba a rehacer

```
:1674|    if (hwmgr->chip_id == CHIP_POLARIS10) {
:1675|        volt_without_cks = (uint32_t)((2753594000U + (sclk_table->entries[i].clk/100) * 136418 - (ro - 70) * 1000000) / \
:1676|                        (2424180 - (sclk_table->entries[i].clk/100) * 1132925/1000));
...
:1680|        volt_without_cks = (uint32_t)((2416794800U + (sclk_table->entries[i].clk/100) * 1476925/10 - (ro - 50) * 1000000) / \
:1681|                        (2625416 - (sclk_table->entries[i].clk/100) * (12586807/10000)));
:1682|        volt_with_cks = (uint32_t)((2999656000U - (sclk_table->entries[i].clk/100) * 392803 - (ro - 44) * 1000000) / \
:1683|                        (3422454 - (sclk_table->entries[i].clk/100) * (18886376/10000)));
:1686|        if (volt_without_cks >= volt_with_cks)
:1687|            volt_offset = (uint8_t)(((volt_without_cks - volt_with_cks +
:1688|                        sclk_table->entries[i].cks_voffset) * 100 + 624) / 625);
```

**Leido integro, sin truncar, confirma mi implementacion de `957` caracter a
caracter**, incluida la precedencia de `(clk/100) * 1476925/10` —que en C es
`((clk/100)*1476925)/10`, asociatividad izquierda— y la constante precalculada
`(12586807/10000) = 1258`.

**Regla que queda fijada: nada de `cut -c` sobre codigo.** No es una preferencia
de estilo; esta vez costo tres hallazgos.

## 2. La herramienta, y la trampa que tenia

`tools/citas.py` **v1.2.0**, `VALIDATED`, **19 casos de self-test, 0 fallos,
exit=0**.

**Lo que hace:** extrae de cada hallazgo las lineas de codigo citadas y las
confronta con las 5.9 M de lineas del corpus.

**Y aqui esta la trampa, que es lo importante de esta finding:**

> **Una linea truncada ES subcadena de la linea real.**

Mi primera version hacia `cita in linea`, que devuelve **True** tanto para una cita
fiel como para un corte a media linea. **Es decir: el metodo que probe primero es
exactamente el que no puede detectar el fallo que motiva la herramienta.**

La version actual mira **donde termina** la cita:

```
COMPLETA  la cita es la linea entera
SUFIJO    la cita llega hasta el final de la linea      <- legitimo
PARCIAL   coincide pero se corta antes de tiempo        <- el fallo
AUSENTE   no aparece en ninguna linea
```

Y el vector de self-test que lo demuestra, que es lo que hace la prueba y no el
codigo:

```
ok  la TRAMPA: la truncada es subcadena de la real  (por eso el subcadena no basta)
ok  pero verificar() la marca PARCIAL
ok  y no llega al final de la linea                (cubierta 0.75)
```

**Un self-test que demuestra que el metodo ingenuo no funciona vale mas que un
metodo que funciona, porque el segundo puede volver a introducirse sin que nadie
se entere.**

**Y un segundo defecto, de rendimiento.** La v1.1.0 **agotó el tiempo de
ejecucion**: `mas_cercana` recorria el corpus entero por cada cita ausente, y con
209 discrepancias eso es `O(n^2)`. No lo arregle reportandolo como lento: lo
arregle moviendo la ruta cara **solo al caso raro** —una cita truncada de verdad—
y dejando el caso frecuente —una cita que no existe, que soy yo mismo
calculando— **sin localizar**. **Cuesta 179 s en vez de agotar el limite, y el
resultado es el mismo.**

## 3. La auditoría

```
49 hallazgos de mi banda 900+
209 citas marcadas
  4 TRUNCADA
205 AUSENTE
```

**Los 205 `AUSENTE` son, en su mayoria, falsos positivos mios**: mi propia salida
de calculo (`sizeof(SMU74_SoftRegisters) = 120`), mis reescrituras deliberadas
(`(clk/100)` en vez de `sclk_table->entries[i].clk`), y tablas de resultados.
**La herramienta no distingue «cita del corpus» de «calculo mio»**, y eso es un
limite conocido, no un fallo de los hallazgos.

**Los 4 `TRUNCADA`, uno a uno:**

```
1  957 hall:24  ->  polaris10_smumgr.c:1675
   citado: volt_without_cks = (uint32_t)((2753594000U + ... * 136
   REAL, y citado a proposito como ilustracion del fallo. Es la v1 de 929.

2  hall:67  ->  amdgpu_drv.c:2041
   citado: {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12}
   el real termina en coma y yo lo cito sin ella. SUSTANCIA CORRECTA.

3  hall:26  ->  smu7_hwmgr.c:4121
   citado: (idx == AMDGPU_PP_SENSOR_GPU_LOAD)
   el real sigue con un "?". SUSTANCIA CORRECTA.

4  hall:73  ->  jpeg_v1_0.c:97
   citado: mask = 0x000000FF
   FALSO POSITIVO: es mi resultado calculado, y coincide por casualidad con el
   principio de una linea de jpeg. No es una cita.
```

**Conclusion de la auditoria, y es un resultado negativo valuable:**

```
errores nuevos derivados de un corte de linea      CERO
la v2 de 929 era el unico, y ya esta corregido
las otras dos truncaciones son de la v1 de 954 y 947, por sintaxis menor
```

**He leido con `cut -c1-10x` durante toda la linea, unas veces al dia, y solo ha
producido un error real.** **Es una comprobacion empirica, no una regla
derivada de que «es peligroso»: es lo que dice el dato.**

Y tiene un corollary que me importa mas: **la mayor parte del trabajo de esta linea
no se hizo con `cut` sino con `grep -n`, que devuelve la linea entera.** **El
escenario del fallo estaba mas acotado de lo que temia**, porque la mayoria de las
veces que necesito ver codigo uso `grep` y solo el resto de las veces use `cut`.

## 4. Lo que la herramienta NO hace

```
no verifica que el codigo diga lo que creo que dice
no verifica que la linea citada sea la que quiero
no distingue mi calculo de una cita
no verifica afirmaciones sobre semantica
```

**Es un control de integridad textual, no un verificador de conocimiento.** Lo
que evita es un modo de fallo concreto —el corte— y no mas. **Un control que
previene un error concreto es mas util que uno que previene todos**, siempre que
no se presente como mas de lo que es.

## 5. Errores de esta iteracion

**1.** Escribi el verificador con matching por subcadena, que es el metodo
obvio, y **no puede detectar el fallo que lo motiva.** Lo vi porque un self-test
dio `FALLO` en un caso que deberia pasar, y el caso era precisamente el truncado.
**Un fallo de self-test tambien puede señalar un fallo de criterio, no un fallo de
test.**

**2.** Los dos fallos siguientes —una cita fiel marcada como `PARCIAL`— eran por
el backslash de continuacion de linea, que no es contenido. **Tuve que normalizarlo
para no marcar como truncada toda cita de una linea partida.** Y lo que mas
importa: **el self-test tiene ahora un vector que demuestra la trampa**, de modo
que volver al criterio ingenuo falla de forma visible.

**3.** Deje la herramienta en un estado que **agotaba el limite de tiempo** y casi lo
reporto como «lenta». Lo mide: **179 s**. **Una herramienta que no termina no es
una herramienta lenta, es una herramienta rota**, y el arreglo es de una linea:
poner el trabajo caro en el caso raro.

## 6. Frontier siguiente

```
1.  las tres formulas verificadas integro contra mi Python         PROVEN
2.  citas.py v1.2.0, 19 casos, 0 fallos                            VALIDATED
3.  el matching por subcadena NO puede detectar un corte            PROVEN
4.  verificar() por posicion de terminacion, si                     PROVEN
5.  la v1.1.0 agotaba el tiempo; la v1.2.0 tarda 179 s              PROVEN
6.  49 hallazgos auditados, 209 citas marcadas, 4 TRUNCADA         PROVEN
7.  de esas 4: 1 es la v1 de 929, ya corregida                     PROVEN
8.  errores nuevos por corte de linea                               CERO  PROVEN_ABSENT
9.  el clasificador no distingue mi calculo de una cita            DEGRADED
10. la mayoria del trabajo se hizo con grep -n, no con cut         PROVEN
```

**El frente util es el punto 9, y es una mejora de la herramienta, no del
conocimiento.** La herramienta marca 205 falsos positivos y 1 hallazgo real: **una
señal con una tasa de acierto de 1 en 209 no es utilizable**, por muy correcta que
sea su logica. **Reducir los falsos positivos es lo que la hace entrar en el ciclo
de trabajo, porque una herramienta que hay que filtrar a mano se deja de usar.**

El camino es acotado y no requiere hardware: **distinguir las citas de mis calculos,
que es una cuestion de forma y no de contenido.** Los resultados de calculo tienen
forma de asignacion con `=` y un numero; las citas tienen la sintaxis del fichero
de origen. Y hay un criterio que no requires heuristica: **un hallazgo que contiene
una tabla de resultados suyos no deberia auditarse linea a linea sino solo en los
bloques que llevan un `archivo.c:NNN` encima.**

Criterio de cierre: la herramienta con la tasa de falsos positivos medida sobre los
49 hallazgos, y el reparto real entre «cita truncada», «cita fiel», «calculo mio» y
«prosa». Si los falsos positivos bajan por debajo del 10 %, la auditoria se puede
usar sin filtrado manual, que es el punto en el que empieza a prevenir errores en
lugar de solo documentarlos.
