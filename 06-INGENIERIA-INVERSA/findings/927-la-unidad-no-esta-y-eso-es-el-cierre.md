# 927 · La unidad de los coeficientes no está en el corpus, y eso es el cierre

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> El frente queda **cerrado como `SEMANTIC_MISSING`**, no abierto.
>
> Busqué la unidad de los coeficientes de droop en los cuatro sitios donde podía
> estar, y **no está en ninguno**. Y hay una razón más fuerte que la ausencia:
> **el driver nunca los lee**, solo los escribe. La evaluación ocurre en el
> firmware del SMC, que no está en este corpus.
>
> Eso no es un hueco que se cierre mirando más. Es un límite con nombre.

## 1. Los cuatro sitios, y lo que tiene cada uno

| sitio | qué tiene |
|---|---|
| `inc/smu74.h:803-809` | `struct GB_VDROOP_TABLE_t` con cuatro `int32`, **sin un solo comentario** |
| `inc/smu73_discrete.h:565-572` | `struct SMU_QuadraticCoeffs` con cinco campos, **sin comentarios ni unidad** |
| `pm/powerplay/smumgr/vegam_smumgr.c:1582-1600` | el mismo copiado campo a campo, **sin comentarios** |
| `include/atombios.h:5601-5615` | la declaración del ATOM, **sin comentarios** |

Y la búsqueda de la unidad por otros medios: `grep -i` de `vdroop|droop` junto a
`unit|mv|mivolt|escala|shift` sobre las cabeceras devuelve **solo registros de GC**
(`GC_DIDT_DROOP_CTRL__DIDT_DROOP_LEVEL_EN__SHIFT` y compañía), que son el droop de
la tabla de dispatched idle, **otra cosa distinta**.

## 2. La razón de fondo: son de escritura única

`GB_VDROOP_TABLE` tiene **80 apariciones** en `amd/`, y al clasificarlas:

```
declaraciones de struct y de campo    ~12
el copiado en polaris10_smumgr.c      20   (:1838-1853)
el copiado en vegam_smumgr.c          20   (:1584-1599)
lecturas del valor de los coeficientes   0
```

**El kernel los copia al SMC y no vuelve a mirarlos.** Lo único que se lee de ese
bloque son los dos `enable`, en `:1887-1888`, que se empaquetan en
`avfs_vdroop_override_setting`.

Eso significa que **el significado de `a0`, `m1`, `b`, `m1_shift` y `m2_shift`
está entero en el firmware del SMC**, y no hay ninguna ruta de código en este
corpus que lo revele. `SEMANTIC_MISSING` es la clasificación correcta, y por
definición no se resuelve con más búsqueda estática.

## 3. Lo que sí queda cerrado, y es bastante

```
VBIOS 0xA6E4  =  ATOM_ASIC_PROFILING_INFO_V3_6
                 usStructureSize 268 = el tamaño del BTF
                 revisiones 3 / 6   = el nombre del struct

del VBIOS, CKSON      a0=-112,329,504  a1=200,456  a2=1,625
del VBIOS, CKSOFF     a0=-156,228,387  a1=196,702  a2=100,959
de :1820-1822, CKSOFF a0=-156,228,387  a1=196,702  a2=100,959   IDENTICOS

AVFSGB  CKSON    m1=958   m2=65,164   b=56   shifts 24/12
AVFSGB  CKSOFF   m1=789   m2=65,233   b=59   shifts 24/12
```

Con los coeficientes ya demostrados como tales por el nombre del campo destino
(`925`), y la coherencia entre las dos curvas:

```
m2: 65,164 vs 65,233   ->  0.1 %
a1: 200,456 vs 196,702 ->  2   %
a0: negativo en las dos
```

**Y con los valores, medibles y enteros, de la curva que gobierna el voltaje de mi
plata**, más `Platform_mean = 500 mV` y `MaxVoltage = 1075 mV`, que sí tienen
unidad porque el nombre del campo la declara: `usMaxVoltage_0_25mv`.

## 4. La diferencia de nombres que casi me hace fallar

```
smu74_discrete.h:370   SMU_QuadraticCoeffs   AVFSGB_VDROOP_TABLE   <- el mio
smu75_discrete.h:376   SMU_QuadraticCoeffs   AVFSGB_FUSE_TABLE     <- el mismo campo
```

**Mismo tipo, mismo offset, nombre distinto entre generaciones de ASIC.** Es el
caso de siempre: si busco `AVFSGB_VDROOP_TABLE` en la ruta de Vega M no encuentro
nada y concluyo que el campo no existe.

Lo anoto porque es la razón por la que varias búsquedas de hoy
tuvieron que repetirse: **el nombre del campo no es el mismo en todas las
generaciones**, y `NAME_MATCH != SEMANTIC_MATCH` aqui se manifestaba justo al
revés, `SEMANTIC_MATCH` con dos nombres distintos.

## 5. Por qué no ajusto la escala hasta que cuadre

Podría tomar `b = 56` y `b = 59`, suponer una forma de la curva y buscar el factor
que devuelve milivoltios. Saldría **un** número, y un número único y bonito es
justo lo que el proyecto llama inventar.

Se que `b` es el término independiente de la curva porque así se comporta en las
dos ramas. **La escala require saber cómo divide el firmware**, y esa es
precisamente la parte que no está.

Un dato que sí apunta en la dirección correcta, y que dejo como hipótesis con
valor de discriminante y no como conclusión: **56 y 59 son enteros pequeños y muy
próximos**, y `Platform_mean` es 500 mV. Si `b` estuviera en alguna unidad de
tensión, esperaría ver `b` cerca de la tensión de referencia con una escala de
decenas. **Pero «esperaría ver» no es medir**, y la diferencia entre las dos
hipótesis que da igual.

## 6. Errores de esta iteración

Ninguno de medición. Tres de alcance, y los tres son honestos:

**1.** Propuse esta acción como cierre del frente, y **la respuesta correcta era
que no se puede cerrar con los datos disponibles**. Eso es un resultado, no un
fracaso, y lo registro como tal en vez de buscar un número para cerrar la caja.

**2.** Busqué la unidad en cuatro sitios y **cualquiera de los cuatro podía haber
dado el número**. Debí hacer los cuatro antes de concluir, y los hice.

**3.** Lo de `AVFSGB_VDROOP_TABLE` frente a `AVFSGB_FUSE_TABLE` lo vi al buscar,
después de haber escrito dos hallazgos sobre ese campo con el nombre que en mi
generación es el correcto. **No me costó nada esta vez**, porque ya venía de
`904` con la lección de las herramientas. Esa es la diferencia entre una lección
escrita y una aplicada.

## 7. Frontier siguiente

**Salir de la línea AVFS. La cadena de regulación de tensión queda cerrada hasta
donde este corpus puede llegar, y su último límite está nombrado.**

Lo que queda cerrado, y que es el resultado útil para un driver propio:

```
1.  La tension de mi placa la gobierna la curva VDROOP con clock stretching,
    no la media/sigma: Platform_sigma = 0 lo deja inactivo.
2.  Los coeficientes se suben en el rango 108..1883, que :2118 copia entero.
3.  Los valores exactos estan medidos, con dos fuentes independientes que
    concuerdan al 0.1 % en el termino cuadratico.
4.  El driver sobrescribe CKSOFF con los mismos valores que el VBIOS, asi que
    en mi placa la sobrescritura es un no-op.
5.  El limite: la SEMANTICA de los coeficientes (unidad y formula) esta en el
    firmware del SMC, no en el codigo. SEMANTIC_MISSING, no NOT_FOUND.

Y hay un defecto REAL ya medido que no pertenece a esta linea y que si pertenece
al objetivo: el ventilador no se sube al SMC. :2254 copia 8 bytes de un puntero
donde el firmware espera 96 de parametros (907). El control de ventilador
efectivo lo decide el firmware, no el driver.

El siguiente frente util no es mas AVFS: es el limite termico que ese defecto
deja sin governar, que es justo la variable que decide el rendimiento sostenido
de una placa de 35 W.
```

Criterio de cierre de la linea: **ninguno pendiente**. Los coeficientes estan
medidos, la forma esta probada, y el limite del corpus esta nombrado con su
causa. Lo unico que queda es la semantica del firmware del SMC, y eso es la linea
B.