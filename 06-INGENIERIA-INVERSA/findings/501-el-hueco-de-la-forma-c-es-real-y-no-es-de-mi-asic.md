# 501 · El hueco de la forma C es real, y no es de mi ASIC

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> La pregunta que `600` dejó abierta tiene respuesta, y es **las dos cosas a la
> vez**: el hueco **existe** —4 sitios reales en el corpus— y **no me afecta**.
> Mi fichero tiene **13 escrituras, 13 resueltas, cero en esa forma**.
>
> ```
> 14 ficheros smumgr en pm/powerplay/smumgr/
>   12 LIMPIOS
>    2 con la forma sin punto:  ci_smumgr.c (3),  iceland_smumgr.c (1)
> ```
>
> Y el hueco produce el motivo **equivocado**, que es lo que lo hacía peligroso:
> `destino no reconocido` acusa al fichero de una expresión que **sí** está
> escrita.

## Los cuatro sitios, con su ASIC

Ámbito contado antes de buscar: `pm/` **85** ficheros `.c`, `amdgpu/` **304**,
**389 examinados**, **63 llamadas de copia** clasificadas una a una.

| destino | fichero:línea | ASIC |
|---|---|---|
| `smu_data->arb_table_start` | `ci_smumgr.c:1681` | Cedar Island |
| `smu_data->mc_reg_table_start` | `ci_smumgr.c:1858` | Cedar Island |
| `ci_data->fan_table_start` | `ci_smumgr.c:2203` | Cedar Island |
| `smu7_data->fan_table_start` | `iceland_smumgr.c:2157` | Iceland |

Reparto de las 63 llamadas de copia del ámbito:

```
A_offsetof             13
C_miembro_con_punto    11
C_miembro_SIN_PUNTO     4    <-- las que la herramienta no reconoce
otra (variable local)   35
ilegible                0
```

## Mi ruta, los 13 destinos uno a uno

```
:142    variable local            vr_config_address
:149    variable local            graphics_level_address
:157    variable local            graphics_level_address
:166    variable local            graphics_level_address
:654    variable local            pm_fuse_table_offset
:1146   variable local            array
:1246   variable local            array
:1511   con punto                 smu_data->smu7_data.arb_table_start
:1872   variable local            tmp
:1881   variable local            tmp
:2118   offsetof                  smu_data->smu7_data.dpm_table_start + offsetof
:2254   con punto                 smu_data->smu7_data.fan_table_start
:2398   offsetof                  smu_data->smu7_data.dpm_table_start + offsetof
```

**Cero en la forma sin punto.** Los dos «con punto» llevan siempre la estructura
intermedia `smu_data->smu7_data.`, que es lo que contiene el punto que la forma C
exige.

**Consecuencia directa**: ninguna conclusión de esta rama depende de este hueco.
El estado `VALIDATED` de `smc_copy_scope` **no se ve afectado para esta placa**, y
por eso el arreglo no es urgente. Es la respuesta que la pregunta pedía y no la
que temía.

## El observable: el motivo es falso

Ejecutada la herramienta sobre los dos ficheros afectados:

```
ci_smumgr.c:1681     smu_data->arb_table_start       (destino: destino no reconocido: ...)
ci_smumgr.c:1858     smu_data->mc_reg_table_start    (destino: destino no reconocido: ...)
ci_smumgr.c:2203     ci_data->fan_table_start         (destino: destino no reconocido: ...)
iceland_smumgr.c:2157  smu7_data->fan_table_start     (destino: destino no reconocido: ...)
```

Y el contraste, sobre mi ASIC, con el mismo patrón de llamada: **13 escrituras,
13 resueltas**.

`destino no reconocido` es una afirmación sobre el **fichero**, y es falsa: la
expresión está escrita, es sintaxis válida de C, y la herramienta simplemente no
tiene la regla. Un motivo falso es peor que una ausencia honesta, porque **dirige
la búsqueda al sitio equivocado**: quien lo lea irá al fuente a buscar una
expresión mal escrita que no está mal escrita.

## Por qué arreglarlo NO es quitar una condición

Esta es la parte que no había visto cuando anoté el hueco, y es la razón de que
no sea un cambio de una línea.

Hoy la forma C devuelve la base así:

```python
return 0, "miembro del contexto", "miembro:" + e
```

Es decir, **la base es el texto entero de la expresión**. Si se quita el
`"." in e` para aceptar `smu_data->arb_table_start`, pasa lo siguiente:

- `smu_data->arb_table_start` daría base `miembro:smu_data->arb_table_start`
- `smu_data->smu7_data.arb_table_start` daría base
  `miembro:smu_data->smu7_data.arb_table_start`

**Dos escrituras a la misma tabla quedarían con bases distintas y no se compararían
entre sí.** La herramienta no daría un número falso: daría `SIN_ORDEN` donde
antes decía `TAPADA`. Un acierto que se convierte en «no lo sé», sin que nadie
haya tocado el hardware.

Y el error simétrico es peor: canonicalizar por el **último miembro** —el camino
obvio— metería `arb_table_start` de `smu_data` y `arb_table_start` de `smu_data->
smu7_data` en la misma base **aunque fueran tablas distintas** en ASICs distintos.
Eso sí sería un número falso.

La clave correcta es el **nombre del último miembro**, que es lo que identifica la
tabla,independientemente de la ruta por la que se llegue:

```
smu_data->arb_table_start              ->  base = arb_table_start
smu_data->smu7_data.arb_table_start    ->  base = arb_table_start   (misma)
smu_data->fan_table_start              ->  base = fan_table_start   (distinta)
```

Eso es lo que ya hace `214` con `dpm_table_start` / `fan_table_start` /`
arb_table_start`, y por lo que `:1511` y `:2254` no se comparan entre sí.

**Pero hay un riesgo nuevo que hay que mirar antes de hacerlo**: si dos structs
distintos tuvieran un miembro con el **mismo nombre** y fueran tablas distintas,
el último miembro las fundiría. En `smumgr.c` hay varios ficheros con
`fan_table_start` en distintos ASIC, pero cada uno define **su propia** tabla, así
que fundirlas es correcto. Ese caso hay que verificarlo, no suponerlo: es
exactamente el `NAME_MATCH ≠ SEMANTIC_MATCH` que ya me costó una iteración
entera.

## Lo que NO he hecho, y la razón

**No he arreglado la forma C.** Dos razones, y las dos son de método:

1. El arreglo no es de una línea: necesita una clave de base correcta, y esa clave
   tiene un caso ambiguo que no he verificado.
2. **No afecta a mi ASIC.** Ninguna conclusión mía depende de ello, y el
   protocolo es explícito sobre no gastar esfuerzo enLo que no cambia una
   decisión. Gastarlo aquí sería el error opuesto al de las cuatro últimas
   iteraciones, donde gasté demasiado en mi propia infraestructura.

Lo dejo **anotado con su sitio exacto, sus cuatro sitios y su manifestació́n
observable**, que es lo que lo hace encontrable. Eso es `NOT_APPLICABLE` para mi
placa y `NOT_PROVEN` para el resto del corpus, y son dos estados distintos.

## Errores que no cometí esta vez, y por qué importa

Los errores que he pagado en esta serie han sido casi todos de **ausencia antes de
tiempo**. Esta vez:

- **Conté el ámbito antes de buscar**: 85 + 304 ficheros, 389 examinados.
- **Clasifiqué las 63 llamadas una a una**, no busqué un patrón y conté.
- **`exit` verificado** en cada `grep`.
- **Leí la función completa** cuando hizo falta, no una ventana.

El resultado es que la respuesta es «sí, 4, ninguno mío», que es una afirmación
que se puede comprobar. Si hubiera hecho el `grep` de la forma que falló en `287`
—con `timeout` sobre el árbol entero— habría gotten otro cero, y esta vez el cero
habría sido **una respuesta en lugar de un error**.

La diferencia no fue de cuidado: fue que el corrector de esta vez exigía el
recuento del ámbito antes de dejar que su palabra valiera. Eso no es unCheckout
disciplina, es una propiedad del script.

## Lo que NO afirmo

- **NO** afirmo que la forma C esté correcta para los ASIC de `ci_smumgr.c` e
  `iceland_smumgr.c`. He medido **qué** reconoce la herramienta y **qué** no, y
  nada más. Que el destino valga `0` es una **convención** de la herramienta
  (`offset 0` dentro de la tabla), no un hecho sobre esas tablas.
- **NO** afirmo que la clave «último miembro» sea correcta sin comprobar el caso
  de dos miembros homónimos en structs distintos.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`; sigue haciendo falta
  `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** he tocado `smc_copy_scope.py` en esta iteración. `MODIFICATIONS 0`.
- **NO** he tocado `artifacts.py`, `atomrom.py`, `AGENTS.md` ni el árbol de kernel.

## Estado

`smc_copy_scope` 1.7.0 — **`VALIDATED`**, 34 vectores, y **el hueco de la forma C
queda acotado**: 4 sitios, en 2 ficheros, de 2 ASIC que no son el mío. Para esta
placa es `NOT_APPLICABLE`.

`:2398` sigue `SIN_ORDEN`, con motivo.

## Frontier siguiente

**Volver al hardware**, y dejar el directorio de infraestructura.

Esta iteración cerró la última frontera que quedaba en `smc_copy_scope`, y las
cuatro anteriores fueron sobre herramientas e índices. La rama de SMU/DPM está
cerrada y medida:

```
10 escrituras con rango verificado por gcc
6 TAPADA nombrando a :2118,  1 SIN_ORDEN con motivo,  3 PROVEN_ABSENT
0 rangos falsos
```

La frontera con discriminante técnico real que queda, y que **no** he tocado, es
**qué escribe realmente el host en cada byte de la copia de 1776 B**. La copia
mueve `108..1883` entero desde la tabla del host; `:142`, `:149`, `:157`, `:166`
escriben **antes** y quedan pisadas. Eso significa que **el contenido final de
esa región lo decide `hwmgr_init_dpm_defaults` y la tabla VBIOS**, no el código
AVFS. Es la pregunta que conecta la tabla DPM con el reloj de 1071 MHz que
`267` decodificó, y es el eslabón que falta entre «qué escribe el host» y «qué
lee el SMC».

Criterio de cierre: una lista, campo a campo, de los 1776 bytes, con para cada uno
**quién lo escribe por última vez** y **de dónde sale el valor**.