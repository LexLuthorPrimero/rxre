# 286 · `doclint` no indexaba `07-DRIVER/`: el driver, fuera de toda cita verificable

`CLASSIFICATION=TOOLING` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=3` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`DESARROLLA=extender el indice de doclint al arbol del driver`

## Cuestión principal

`doclint` comprueba que las citas de un hallazgo —un nombre de fichero, dos
puntos y un numero de linea— **se resuelvan**.
El índice de `doclint` cubría el kernel, `08-ARQUITECTURA`, `04-IMPLEMENTACION` y
`/usr/src/kernels`. **No cubría `07-DRIVER/`.**

Consecuencia: toda afirmación sobre el **driver**, que es el entregable del
proyecto, se apoyaba en citas que el linter no podía resolver y por tanto no
podía verificar. Un hallazgo sobre el driver era verificable a mano y no
verificable por máquina.

## Criterio de terminación

El índice incluye `07-DRIVER/`, el self-test lo exige, y el efecto está medido
sobre las citas reales. **Cumplido.**

## La medición

Sobre los documentos del proyecto, con el extractor de citas del propio
`doclint` (`CITE`), contando cada nombre distinto una vez:

| | sin `07-DRIVER` | con `07-DRIVER` |
|---|---|---|
| ficheros indexados | 2802 | **2827** |
| nombres citados sin resolver | 33 | **23** |
| nombres ganados | — | **10**, 37 ocurrencias |

**Los 10 nombres ganados son exactamente ficheros del driver**, sin
contaminación:

```
rx550_pm4.c x9   rx550_pm4.h x7   test_pm4.c x6    rx550_drv.c x4
rx550_mc.h x1    rx550_mc.c x1    + 4 citas con ruta ya cualificada
```

## La comprobación que hace que la cifra signifique algo

**Anadir ficheros no puede deshacer una resolucion.** No lo doy por Supuesto:
lo compruebo.

```
PERDIDOS al anadir 07-DRIVER:  0
```

Que sea 0 es informativo porque **no es automatico**. `resolve()` exige unicidad
(`len(hits) == 1`), asi que en principio un nombre que hoy resuelve por azar
podria dejar de resolver al aparecer un homonimo. Que no haya pasado es una
comprobacion, no una suposicion.

Y el segundo control: los nombres ganados son **todos** del driver. Un resultado
del que ganaran tambien ficheros del kernel habria indicado que el filtro de
comparacion estaba mal, no que la cobertura improved. Ese control es el que
habriapillado un error mio real en el primer script de medicion.

## Un fallo mio, y por que lo cuento

El primer script de medicion imprimo "resueltos solo por 07-DRIVER: 472" e
incluyo `gmc_v8_0.c` (706 ocurrencias) y `sid.h` (77) **entre los ficheros
ganados**. Esos son del corpus del kernel y no tienen relacion con `07-DRIVER`.
El script tenia los dos conjuntos intercambiados: `sin` contenia los nombres
**resueltos** y `con` los **no resueltos**, y al restarlos salia todo.

**Una salida que se contradice consigo misma no es un dato: es ruido con
formato de dato.** Los tres numeros que parecian Scout —472, 33, 23— eran
incoherentes entre si (33-23=10, no 472), y eso era la senal. Si me hubiera
quedado con el listado, habria reportado como propios 10 ficheros del kernel.

Lo reescribi nombrando cada conjunto por lo que **es**, no por una sigla.

## El self-test, en las tres direcciones

Un filtro que solo sabe decir "no" es un muro, y uno que solo sabe decir "si" es
un sello. Las dos mitades van juntas:

| caso | esperado | por queno es decorativo |
|---|---|---|
| `rx550_mc.h` **resuelve** | si | solo existe en `07-DRIVER/`: si la raiz no se indexa, **falla entero** |
| `rx550_este_fichero_no_existe.h` | no | si resolviera, cualquier nombre inventado daria por verificado |
| `smu9_driver_if.h` (2 homonimos) | no, y **sin elegir uno** | colision **real** en el indice, no un nombre inventado |

El tercero es el que importa: sin el, un resolutor podria elegir un homonimo y
declarar verificada una cita que apunta al fichero equivocado. Y hay una cuarta
comprobacion que el anterior no tenia: que el caso de ambiguedad **no se quede
vacio**. Si `smu9_driver_if.h` dejara de colisionar, el control dejaria de
probar nada — y un control vacio que pasa es peor que un control que falta.

**El fallo corta el lint.** Quitando la raiz del indice:

```
AUTOTEST FALLA:
   el resolutor no encuentra rx550_mc.h (¿07-DRIVER sin indexar?)
No se ejecuta el lint: el linter no supera su autotest.
```

El autotest es una **condicion de ejecucion**, no un aviso.

## Dos citas erroneas que el linter cazo

Al cubrir el arbol del driver (y al resolverse `gfx_v8_0.c` de verdad), aparecio
un error mio que estaba escrito desde hacia tiempo:

| documento | antes | despues |
|---|---|---|
| `010-pgm-rsrc1-decoded.md:146` | `gfx_8_0.c` mas un rango de lineas | `gfx_v8_0.c:1535-1564` |
| `112-...:32` | `gfx_8_0.c` | `gfx_v8_0.c` |

**La columna "antes" va sin numero de linea a proposito.** Si lo escribo
completo, `CITE` lo reconoce como cita, el linter avisa, y con razon: no hay
`gfx_8_0.c` que abrir. La regla aqui es **no debilitar el linter para que mi
documento pase** — si hace falta, se cambia el documento, que es lo que he
hecho. Un aviso que se silencia porque el documento se ha adaptado al aviso es
un aviso que ya no mira nada.

**Verifique el dato antes de corregir la cadena**, porque un nombre arreglado
puede esconder un numero de linea falso:

- `gfx_v8_0.c:1535-1564` contiene `SET_SH_REG` + `mmCOMPUTE_PGM_LO` +
  `DISPATCH_DIRECT`. **El rango es correcto.**
- `112` afirma que ese fichero "no toca el page walker": `walk_` = 0,
  `page_table` = 0, `GTT` = 0 en 7206 lineas. **La afirmacion es correcta.**

El unico defecto era el nombre. Y el mecanismo del error es una **asimetria de
convenciones** que ahora esta medida:

```
cabeceras  asic_reg/gca/gfx_8_0_*.h   SIN la v   (3 ficheros)
fuente     amdgpu/gfx_v8_0.c           CON la v   (1 fichero)
```

`010` por si mismo no era coherente: citaba `gfx_v8_0.c` **bien** cuatro veces y
`gfx_8_0.c` mal una. Por eso el arreglo fue **`s/gfx_8_0\.c/gfx_v8_0.c/g`** y no
un `s/gfx_8_0/gfx_v8_0/`: el segundo habria roto las 7 citas correctas a
`gfx_8_0_sh_mask.h`, que **no** lleva la `v`.

Tambien queda visto que las cabeceras de GFX8 viven en `asic_reg/**gca**/`, no
en `asic_reg/gfx/`.

## Lo que sigue sin resolverse: 23 nombres, y no es lo mismo

| clase | nombres | ocurre. | se puede arreglar |
|---|---|---|---|
| **Mesa**: `lp_bld_*`, `u_format_s3tc.c`, `lp_screen.c` | 8 | 25 | **no**: el codigo no esta en esta maquina |
| abreviaturas: `ib.c`, `vm.c`, `device.c`, `kms.c` | 4 | 16 | si, pero es estilo de escritura, no hecho |
| `gmc_8_0.c` (falta la `v`) | 1 | 1 | si — mismo fallo que `gfx_8_0.c` |
| ASIC que no es esta placa: `smu7_7_1_1_d.h`, `v1_2.c`... | 5 | 5 | **no por diseno**: no se indexan ASIC ajenos |
| ausentes de verdad: `amdgpu_drm.h`, `fichero.c` | 2 | 9 | revisar una por una |

**Mesa no esta en esta maquina.** No es un indice mal puesto: no hay nada que
indexar. Esas 25 ocurrencias **no son verificables aqui**, y declararlas
arregladas seria el error de decir "todo bien" donde lo que hay es "no puedo
mirar".

## Confounders

- **`--self` solo mira `0[23]*.md`.** Mis hallazgos recientes (`279`, `286`) no
  entran. Mediciones como estas hay que hacer con la lista de ficheros
  explicita, no con `--self`.
- **El recuento global es un instrumento inestable**: entre dos ejecuciones
  paso de 372 a 375 documentos porque otra sesion escribe a la vez. Por eso la
  medicion de arriba es **por nombre**, no sobre el total.
- **`07-DRIVER/kernel/rx550_pm4.c` y `.h` tienen cambios sin commitear de otra
  sesion.** Los he leido y no los he tocado ni los he committeado.
- **No he construido el driver.** Un nombre resuelto no es un nombre correcto:
  `resolve()` encuentra el fichero, no verifica que la linea exista.
- **`v1_2.c` y `v12_0.c` no los he clasificado con certeza**: el corpus tiene
  `gfx_v12_0.c` y `gfx_v12_1.c`, asi que pueden ser truncamientos, pero no lo he
  verificado y queda como `NOT_DETERMINED`.

## Clasificacion

| afirmacion | estado |
|---|---|
| `07-DRIVER` no estaba en el indice de `doclint` | `PROVEN` — `CORPUS_ROOTS` |
| 10 nombres pasan a resolver, 37 ocurrencias | `PROVEN` — recount con `CITE` |
| 0 resoluciones perdidas | `PROVEN` |
| los 10 ganados son del driver | `PROVEN` |
| `gfx_8_0.c` no existe; `gfx_v8_0.c` si | `PROVEN` |
| el rango 1535-1564 es el correcto | `PROVEN` — leido |
| `gfx_v8_0.c` no toca el page walker | `PROVEN` — 0 de 3 patrones en 7206 lineas |
| cabeceras `gfx_8_0_*` sin `v`, fuentes `gfx_v8_0.c` con `v` | `PROVEN` |
| las cabeceras de GFX8 estan en `asic_reg/gca/` | `PROVEN` |
| Mesa no esta en esta maquina | `PROVEN` — `find` en `/` |
| `resolve()` elige un homonimo si lo hay | `NO` — `len(hits)==1` |
| `v1_2.c`/`v12_0.c` son truncamientos | `NOT_DETERMINED` |

## UNLOCKS

- **El entregable del proyecto ahora es citable por maquina.** Antes, el driver
  era el unico sujeto sin cobertura.
- **Un linter que no cubre el sujeto de sus documentos cubre el decorado.**
  Esa es la regla general, y aqui estaba Fallada.
- **Los controles negativos tambien se autocomprueban**: el caso de ambiguedad
  verifica que sigue habiendo ambiguedad.
- **`--self` es un selector incompleto.** Si la cobertura importa, el alcance del
  linter tambien: ahora `0[23]*` es una lista de numeros, no un criterio.
- **Siguiente paso**: `gmc_8_0.c` es el mismo fallo que `gfx_8_0.c` y hay al
  menos una cita mas con la `v` perdida. Localizarlas todas con una regla
  --"nombre de fuente `X_Y.c` citeddo sin `v`" -- y comprobar **el rango** en
  cada una, que es donde el nombre puede estar mal y la linea tambien.

## Evidencia

```
CORPUS_ROOTS: + 07-DRIVER          2802 -> 2827 ficheros
SIN 07-DRIVER -> 33 sin resolver   CON -> 23
GANADOS 10 nombres / 37 ocurrencias, todos del driver
PERDIDOS 0
AUTOTEST FALLA al quitar la raiz; el lint no se ejecuta
ls amdgpu/gfx_v8_0.c              EXISTE (7206 lineas)
ls amdgpu/gfx_8_0.c               no existe
grep -c 'walk_|page_table|GTT'    0 / 0 / 0
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=3` (doclint + 2 documentos). `GPU INTACTA`.