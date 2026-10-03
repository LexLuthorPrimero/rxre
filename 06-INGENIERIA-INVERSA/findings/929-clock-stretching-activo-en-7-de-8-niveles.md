# 929 · El clock stretching está activo en 7 de los 8 niveles de SCLK

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **La tabla de dependencia SCLK de mi placa, decodificada entera, con los ocho
> niveles y el estado de clock stretching de cada uno.**
>
> **7 de 8 niveles tienen clock stretching activo**, y el desactivado es el más
> bajo. `cks_voffset` vale 0 en todos: el VBIOS no añade offset estático.
>
> El margen de tensión en voltios **no es calculable estáticamente**, y el motivo
> está localizado con precisión: los dos extremos de la fórmula son runtime.

## 1. La base, recalculada y no memorizada

Empecé usando la dirección que tenía anotada de hallazgos anteriores, **`0x9D14`**,
y salió `ucNumEntries = 1` con `ulSclk = 5478400`. Obvio que estaba mal.
**La recalculé por la cadena del driver**, sin usar ninguna dirección recordada:

```
base       = CU16(0x48)        = 0x021C     [ATOM en base+4]
data_table = CU16(base+0x20)   = 0x97F2
mdt[15]    PowerPlayInfo       = 0x9C0A
usSclkDependencyTableOffset @base+45 = 267 -> tabla en 0x9D15
```

Y los tres valores, **45, 57 y 61**, son los que da el BTF para los tres campos.
Base correcta, tabla en **`0x9D15`**, un byte más de lo que tenía.

## 2. El paso del registro: lo decide el dominio, no el BTF

El BTF dice que `_ATOM_Polaris_SCLK_Dependency_Record` mide **15 bytes**, empaquetado.
Lo comprobé contra el dominio antes de fiarme:

```
stride 16 (alineado):  VddcOff=38912  ulSclk=83  SclkOff=33554432  -> basura
                        y luego 3690987520, 98304000, 2684354566
stride 15 (empaquetado): vddInd 0,2,2,5,6,7,8,9   SclkOff 0,3000,3000,3000,1500x4
```

**El empaquetado gana por dominio**, no porque el BTF lo diga: la versión alineada
no tiene **ni un solo** valor plausible, y la empaquetada tiene una secuencia de
`vddInd` monótona y `SclkOff` en valores redondos.

Es la segunda vez hoy que el BTF y el dominio coinciden, y usar los dos juntos es
lo que convierte un resultado en una medida.

## 3. Los ocho niveles, convertidos como hace el driver

```
rec       clk   vddInd   Edc   ucCKSVOffsetandDisable  cks_enable  cks_voffset
  0     21400        0     0                       128           0           0
  1     55100        2     0                         0           1           0
  2     73400        2     0                         0           1           0
  3     98000        5     0                         0           1           0
  4    100000        6     0                         0           1           0
  5    102000        7     0                         0           1           0
  6    104600        8     0                         0           1           0
  7    107100        9     0                         0           1           0

Sclk_CKS_masterEn0_7 = 0xFE = 11111110
```

La regla es de **un solo bit**, y es activa a la inversa:

```c
process_pptables_v1_0.c:464
    cks_enable  = (((ucCKSVOffsetandDisable & 0x80) >> 7) == 0) ? 1 : 0;
    cks_voffset =  (ucCKSVOffsetandDisable & 0x7F);
```

El bit 7 es un **deshabilitador activo a bajo**, y los siete bits bajos son el
offset.

**Resultado: clock stretching activo en los niveles 1 a 7, desactivado solo en el
nivel 0**, que es el más bajo de la tabla. Y `cks_voffset = 0` en los ocho: el
VBIOS no pone offset estático, todo el ajuste lo calcula el driver.

Y el bucle `:1671` corre `i` de 0 a `count-1` con `count = 8`, y
`Sclk_voltageOffset` es `int8[8]`: **encaja exactamente, no hay desbordamiento.**

## 4. Lo que no es calculable, y por qué

La función `:1650-1709` calcula el margen de voltaje así:

```c
ro = ((efuse * (ro_range_maximum - ro_range_minimum)) / 255) + ro_range_minimum;

volt_without_cks = 2416794800U + (clk/100)*1476925/10
                 - (2625416 - (clk/100)*(12586807/10000));        NO depende de ro
volt_with_cks    = 2999656000U - (clk/100)*392803
                 - (ro - 44) * (3422454 - (clk/100)*(18886376/10000));   SI depende
```

(es la rama `else`, la de mi placa: `chip_id == CHIP_POLARIS10` es falso)

**`ro` sale de la efusiva del ASIC** vía `atomctrl_read_efuse`, y **`ro_range_maximum`
y `ro_range_minimum` también**, calculados en `smu7_calculate_ro_range` a partir de
la misma efusiva.

Así que los dos extremos de la fórmula son runtime, y **`volt_with_cks` es
`RUNTIME_MISSING`**. Es el mismo límite que `927` cerró para los coeficientes
AVFS, y por la misma causa: **la semántica está en el firmware del SMC y en la
efusiva, no en el código.**

## 5. Lo que esto significa para el objetivo

**La regulación de tensión de mi placa no es una curva media/sigma, sino clock
stretching aplicado a 7 de los 8 niveles de reloj**, con el driver calculando el
offset en función de la efusiva de silicio.

Eso tiene una consecuencia práctica y medible para un driver propio: **el margen
que aporta el clock stretching depende del silicio concreto**, porque `ro` se lee
de la efusiva. **Dos placas del mismo modelo pueden tener márgenes distintos**, y
un valor fijo sería una aproximación, no una medida.

Y hay un punto que ya está medido y que pertenece a la línea del ventilador: el
`Sclk_voltageOffset` que el driver calcula **sí llega al SMC** —es un campo del
`smc_state_table`— mientras que los 96 bytes de parámetros de ventilador **no**
(`907`). Es decir: **la ruta de tensión está completa y la de ventilador está rota.**

## 6. Errores de esta iteración

**1. Usé una dirección absoluta que tenía anotada** en vez de recalcularla por la
cadena del driver, y obtuve `ucNumEntries = 1` con `ulSclk = 5478400`. Lo detecté
porque los valores eran absurdos, no porque hubiera comprobado.

Es el mismo error de `908` con las bases: **una dirección anotada es una
conclusión de hace tres hallazgos, no un dato.** Y esta vez costó una lectura
entera.

**2.** Casi me fío del BTF para el paso del registro sin mirar el dominio. Esta vez
coincidieron, y aun así lo comprobé. La lección de `908` §6 era que **una
coherencia entre dos métodos es más fuerte que uno**, y aquí verifiqué que el
segundo método no era un eco del primero.

Ninguno de los dos habría detectado un corpus con el layout alineado, y por eso
los dos importan.

## 7. Frontier siguiente

**Salir de la línea SCLK. Con ella queda cerrado todo lo estáticamente medible
sobre la regulación de tensión de mi placa.**

Lo que queda, y es un resultado útil para el driver propio:

```
1.  8 niveles de SCLK, de 21400 a 107100, en la unidad que todavia no se.
2.  clock stretching activo en 7 de 8; desactivado solo en el mas bajo.
3.  cks_voffset = 0 en todos: el offset lo calcula el driver, no el VBIOS.
4.  el margen depende de la efusiva de silicio: ro es RUNTIME_MISSING, y con
    el los dos extremos de la formula. Es el mismo limite que 927 cerro para
    los coeficientes AVFS.
5.  la tension esta bien governada; el ventilador no (907).
```

El frente siguiente útil es **el límite térmico**, porque es la variable que
decide el rendimiento sostenido y ahora sé que el driver no la gobierna: los
parámetros de ventilador no llegan al SMC, y el margen de clock stretching depende
de la efusiva.

Y hay una pregunta que sí es estática y que conecta las dos líneas: **qué
frecuencia de SCLK fija el nivel 0**, el único sin clock stretching. Si ese nivel
es el de reposo, entonces la placa baja de reloj antes de subir tensión, y eso
es justo el mecanismo por el que el defecto del ventilador se paga en rendimiento.