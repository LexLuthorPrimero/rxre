# 278 · El recuento de cobertura de polaris10: 6 de 7 escrituras DPM las pisa la copia de 1776 B

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> El `TAPADA 0` de `smc_copy_scope` no era verdad. Con las medidas de gcc y el
> orden de ejecucion probado en `263`, **las 6 escrituras a la tabla DPM caen
> dentro de la copia de 1776 B, y las 6 se sobrescriben**. Y alimentar mejor la
> herramienta produjo **un numero falso**, que es peor que un sin resolver.

## Lo que cambio al darle las entradas completas

```
antes    5 offsets ·  5 tamanos                      ->  4 VIVA,  9 NO_RESUELTO
interm.  9 offsets ·  7 tamanos                      ->  6 VIVA,  7 NO_RESUELTO
ahora    9 offsets ·  9 tamanos + 3 contadores       ->  9 VIVA,  4 NO_RESUELTO
```

Tres huecos eran **entradas**, no codigo:

| hueco | como se resuelve |
|---|---|
| alias de `#define` | `--contador SMU74_MAX_LEVELS_GRAPHICS=8 SMU74_MAX_LEVELS_MEMORY=4` |
| `sizeof(<variable>)` | `--sizeof avfs_graphics_level_polaris10=448 avfs_memory_level_polaris10=24` |
| `X = sizeof(T)` a secas | `--contador graphics_level_size=448` |

El cuarto, **multi-asignacion**, no se resuelve por entrada. Y es el que falla.

## El numero falso, que es el hallazgo de verdad

```
:157  graphics_level_address  tam=1592..1615  24B
```

Eso **no existe**. Es una combinacion de dos cosas distintas:

- la base **1592** viene de la **tercera** asignacion de `graphics_level_address`
  (`BootMVdd`, en `:164`);
- el tamano **24** viene del argumento de la **segunda** llamada
  (`sizeof(avfs_memory_level_polaris10)`, en `:158`).

El valor correcto es `MemoryLevel = 708`: **708..731**.

**El defecto de multi-asignacion no produce «sin resolver»: produce un rango
plausible, de la magnitud correcta y completamente falso.** Eso es peor que un
`NO_RESUELTO`, porque quien lo lea no tiene motivo para dudar.

El mapa `ctx[nombre] = (off, base)` sobrescribe en cada asignacion y solo
conserva la ultima. El punto de uso se descarta.

Repasando los nueve:

| linea | tool | correcto | veredicto |
|---|---|---|---|
| `:142` | 112..115 | 112..115 | OK |
| `:149` | sin resolver | 236..683 | falta `graphics_level_size` |
| `:157` | **1592..1615** | **708..731** | **FALSO** |
| `:166` | 1592..1593 | 1592..1593 | OK, **y por suerte** |
| `:1146` | 236..683 | 236..683 | OK |
| `:1246` | 708..803 | 708..803 | OK |

Cinco correctos, uno falso, tres sin resolver. **Un falso de nueve.**

`:166` merece nota: acierta **por casualidad**. Es la tercera asignacion, que es
justo la que sobrevive en el mapa, y el tamano lo infiere del tipo de la variable
de destino. Con otro orden de asignaciones fallaria tambien.

## El recuento de cobertura, hecho a mano

`smc_copy_scope` dice `TAPADA 0` porque **compara en orden textual**, y lo
admite en su propio pie. El orden de ejecucion es otro, y lo tengo probado:

| linea | destino | rango | la cubre `:2118` | cuando ejecuta |
|---|---|---|---|---|
| `:142` | `VRConfig` | 112..115 | **SI** | fw_loading, 2403 |
| `:149` | `GraphicsLevel` AVFS | 236..683 | **SI** | fw_loading, 2403 |
| `:157` | `MemoryLevel` AVFS | 708..731 | **SI** | fw_loading, 2403 |
| `:166` | `BootMVdd` | 1592..1593 | **SI** | fw_loading, 2403 |
| `:1146` | `GraphicsLevel` host | 236..683 | **SI** | `init_smc_table`, antes de `:2118` |
| `:1246` | `MemoryLevel` host | 708..803 | **SI** | `init_smc_table`, antes de `:2118` |

Y dentro de la misma funcion el orden es textual **y** de ejecucion:

```
:1956  polaris10_populate_all_graphic_levels    -> escribe :1146
:1960  polaris10_populate_all_memory_levels     -> escribe :1246
:2118  smu7_copy_bytes_to_smc, 1776 B          -> cubre 108..1883
```

**Las seis caen dentro de `108..1883`, y las seis se sobrescriben.**

Las cuatro primeras por el orden de `263`: `fw_loading` en 2403 **antes** de
`phase2` en 2407. Las dos ultimas por orden textual dentro de la misma funcion.

## Las que no entran en la cuenta, y por que

| linea | destino | por que queda fuera |
|---|---|---|
| `:1511` | `arb_table_start` 0..383 | **otra base**: no es `dpm_table_start` |
| `:2254` | `fan_table_start` 0..35 | **otra base** |
| `:654` | `pm_fuse_table_offset` | direccion que lee el SMC: `PROVEN_ABSENT` |
| `:1872` | `tmp` | idem, `AvfsMeanNSigma` |
| `:1881` | `tmp` | idem, `AvfsSclkOffsetTable` |

`:1511` y `:2254` estan en tablas distintas, y la herramienta lo trata bien: su
`base_nombre` impide comparar dos regiones como si fueran la misma. Es lo que
`214` pidio, y esta hecho.

## Lo que queda sin determinar

**`:2398`** escribe `dpm_table_start + 1692`, 4 bytes, que **esta dentro** de
`108..1883`. Pero escribe en el camino de **overdrive en runtime**, que corre
despues de init. Si es asi, `:2118` la pisa en init, pero no al reves, y `:2398`
**sobrevive**.

Estado: **`NOT_DETERMINED`**, y no lo fuerzo. Es el unico caso donde el orden de
ejecucion decide y no lo he trazado.

## El cierre de la cadena

```
7 escrituras a la tabla DPM de polaris10_smumgr.c
6 de ellas caen dentro de la copia de 1776 B (108..1883)  -> se sobrescriben
1 (:2398) depende de un orden de ejecucion que no he trazado -> NOT_DETERMINED
3 (:654, :1872, :1881) son direcciones que decide el firmware -> PROVEN_ABSENT
2 (:1511, :2254) estan en otras tablas y no compiten
```

`262` decia que `TAPADA 0` no era un resultado sino la ausencia de comparacion.
**Tenia razon, y ahora se cual es el numero.**

## Y el hallazgo transversal de la rama entera

**Cuanto mas se le alimenta a la herramienta, mas oportunidad tiene de devolver un
numero falso en vez de ninguno.**

La secuencia de esta sesion: `NO_RESUELTO 9` → `VIVA 4` → `VIVA 6` → `VIVA 9`, y en
ese ultimo paso aparecio `1592..1615`, que no es un rango real. Un `NO_RESUELTO`
es honesto. Un rango de la magnitud correcta **no lo es**.

La leccion operativa: **antes de quitarle un `NO_RESUELTO` a una herramienta,
comprobar que lo que devuelve en su lugar esta verificado por otro camino.** Yo
tenia gcc para comprobarlo. Una herramienta sin esa segunda fuente no tiene
como distinguir un acierto de una coincidencia.

## Lo que NO afirmo

- **NO** afirmo que `:2118` se ejecute en mi placa. Es el camino de init, y
  `B_RUNTIME = NOT_EXECUTED`.
- **NO** afirmo el orden entre `:2398` y `:2118`. Es `NOT_DETERMINED`.
- **NO** he modificado `smc_copy_scope` en esta iteracion. Los cuatro huecos
  estan nombrados; ninguno era de codigo, salvo el de multi-asignacion.
- No he medido hardware.

## Estado de la herramienta

`smc_copy_scope` sigue **`VALIDATED`**. Con las entradas completas produce nueve
rangos de los que **cinco son correctos, uno es falso y tres se declaran
sin resolver**.

Es decir: **el defecto de multi-asignacion ha pasado de ser un hueco a ser un
riesgo**, porque antes se manifestaba como `NO_RESUELTO` y ahora se manifiesta
como un numero. Un riesgo que antes era visible y que ha dejado de serlo **es un
empeoramiento, aunque el recuento de `VIVA` mejore**. Lo digo asi porque el
numero de `VIVA` mejoraria en cualquier tableau de control.

## Frontier siguiente

Arreglar la multi-asignacion: que `ctx` guarde **todas** las asignaciones de un
nombre, con su posicion, y que `resuelve_destino` elija la vigente en el punto
de uso en vez de la ultima. Es un cambio pequeno y tiene criterio de cierre
limpio: `graphics_level_address` en `:149`, `:157` y `:166` debe dar **236**,
**708** y **1592**, en ese orden.

Es la unica accion pendiente de esta rama. Y es la que evita que la herramienta
siga devolviendo un valor erroneo que parece razonable: es peor que seguir
siendo honesto.

`B_RUNTIME = NOT_EXECUTED`. Sigue haciendo falta `Autorizo WRITE_EXECUTION para
B_EXPERIMENT`.