# 104 · Once usos de dpm_table_start, y el hueco de 108 bytes no existe: dpm_table_start es la base literal y el -108 se retira

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «Once usos de dpm_table_start, y el hueco de 108 bytes no se compensa en ninguno». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:17` — el hueco no existe: «la base literal**. En consecuencia **quedan `REFUTED`**»
> - `:23` — la funcion con -offsetof se retira: «SE RETIRA**: introduciria un desplazamiento real de 108 B»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

> **CORREGIDO POR `113-dpm-table-start-es-la-base-literal-y-los-once-usos-son-correctos.md`**
>
> La pregunta que este documento dejo abierta y marcada `NOT_DETERMINED` en `:148-158`
> ("¿`dpm_table_start` es la base literal o hay que sumarle 108?") esta **contestada: es
> la base literal**. En consecuencia **quedan `REFUTED`**:
> `SMC_GRAPHICS_LEVEL_OVERRUNS_ACPI_AND_MEMORY`, `SMC_MEMORY_LEVEL_OVERRUNS_LINK_LEVEL`,
> `SMC_VR_CONFIG_HITS_VR_HOT_LEVEL`, `SMC_BOOT_MVDD_HITS_CLOCK_STRETCHER` y
> `SMC_DPM_OFFSET_MIXES_REFERENCE_FRAMES`.
>
> **La funcion `smc_addr()` que se recomienda mas abajo, con el `- offsetof(SystemFlags)`,
> SE RETIRA**: introduciria un desplazamiento real de 108 B. Lo que se conserva es la
> disciplina (una sola funcion, forzada por el compilador, probada contra el layout real),
> no la aritmetica.
>
> El error de este documento no fue afirmar de mas en la prosa: fue **etiquetar como
> `PROVEN_DERIVED` unas consecuencias que el propio documento declaraba dependientes de un
> `NOT_DETERMINED`**, y comprobar "+108" contra la misma lectura que estaba en prova.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El hallazgo, y por que `210` era solo el primer caso

`210` mostraba un parche que calcula la direccion de un campo como
`dpm_table_start + offsetof(SMU74_Discrete_DpmTable, campo)` y que por eso queda **108
bytes** tarde, porque la copia inicial de la tabla no empieza en el offset 0.

La pregunta obvia es si ese error es de uno o de todos. Inventario completo de los usos de
`dpm_table_start` en `polaris10_smumgr.c`: **once direcciones calculadas con `offsetof`,
mas la copia inicial, mas la lectura de la cabecera**. Y **ninguna compensa el hueco.**

## La causa, enunciada una vez

La copia de `:2118-2123` no empieza en el offset 0 de la struct:

```c
smu_data->smu7_data.dpm_table_start + offsetof(SMU74_Discrete_DpmTable, SystemFlags),
(uint8_t *)&(table->SystemFlags),
sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
```

`offsetof(SystemFlags) = 108` (gcc). Los tres `SMU74_PIDController` de la cabeza los
escribe el firmware, no el host. `195` documento ese hueco: el host escribe `[108, 1884)`.

De ahi sale la regla que el codigo incumple en once sitios:

```
posicion_smc(campo) = dpm_table_start + offsetof(Campo) - 108
```

El codigo usa `dpm_table_start + offsetof(Campo)`. **Falta restar 108.**

`dpm_table_start` es la base **segun el firmware**, que coloca los campos en su offset real.
`offsetof` es un offset en la struct **del host**, que tiene 108 bytes de cabeza que el
firmware no tiene. Sumarlos mezcla dos sistemas de referencia y produce una direccion
**valida, alineada y dentro del rango que el check acepta**: el peor tipo de error, el que
no dispara ningun assert.

## Los once usos, con lo que hay realmente en cada direccion

Offset de `SystemFlags` = 108. Para cada uso, la direccion que el codigo calcula
corresponde en la struct al offset `offsetof(campo) + 108`:

| linea | campo que el codigo cree | offset | que hay realmente ahi | |
|---:|---|---:|---|---|
| 140 | `VRConfig` | 112 | `VRHotLevel` (220) | desviado |
| 147 | `GraphicsLevel` | 236 | `GraphicsLevel`, elemento 1 | desviado |
| 155 | `MemoryLevel` | 708 | `MemoryLevel` entero, desplazado | desviado |
| 164 | `BootMVdd` | 1592 | `ClockStretcherAmount` | desviado |
| 1046 | `GraphicsLevel` | 236 | `GraphicsLevel`, elemento 1 | desviado |
| 1215 | `MemoryLevel` | 708 | `MemoryLevel` entero, desplazado | desviado |
| 2292 | `UvdBootLevel` | 1576 | `BootVddc` byte 0 | desviado |
| 2328 | `VceBootLevel` | 1577 | `BootVddc` byte 1 | desviado |
| 2400 | `LowSclkInterruptThreshold` | 1692 | `SclkFcwRangeTable` | desviado |
| 2594 | `GraphicsLevel` | 236 | `GraphicsLevel`, elemento 1 | desviado |
| 2597 | `MemoryLevel` | 708 | `MemoryLevel` entero, desplazado | desviado |

**Once de once.**

## Y el caso grave: los dos array writes se salen del array

Para los escalares, el efecto es "escribe en el campo de al lado". Para los **arrays** es
peor, porque el `array_size` que usa el codigo es el **tamano completo del array**, y al
desplazar el punto de partida, la escritura se come lo que hay detras.

### `GraphicsLevel` en `:1046`, `:2594` y `:147`

```
el array real, tras la copia:   +128 .. +575   (448 B = 8 x 56)
la escritura del codigo:        +236 .. +683   (448 B, el tamano completo)
exceso:                                      108 B
```

La invasion cae sobre, en orden:

| campo | offset host | bytes invadidos |
|---|---:|---:|
| `MemoryACPILevel` | 684 | **24 de 24**, entero |
| `MemoryLevel` | 708 | **84 de 96** |

O sea: la escritura de `GraphicsLevel` **consume `MemoryACPILevel` completo y 84 de los
96 bytes de `MemoryLevel`**.

Y en `:147` es peor por el orden: `polaris10_setup_graphics_level_structure` copia
`avfs_graphics_level_polaris10` a `GraphicsLevel` **antes** de que exista la tabla real,
como valor por defecto. Con el desfase, ese valor por defecto aterriza sobre
`MemoryACPILevel` y `MemoryLevel`.

### `MemoryLevel` en `:1215`, `:155` y `:2597`

```
el array real, tras la copia:   +600 .. +695   (96 B = 4 x 24)
la escritura del codigo:        +708 .. +803   (96 B)
exceso:                                       108 B
```

| campo | offset host | bytes invadidos |
|---|---:|---:|
| `LinkLevel` | 804 | **108 de 128** |

## El detalle que hace que esto no lo detecte nadie

**Para los arrays, el desfase no cambia de campo: cambia de elemento.** Por eso un barrido
que compara nombres de campos dice "OK": `+236 + 108 = 344` cae **dentro** de
`GraphicsLevel`, en el elemento 1.

Mi primer script commetio exactamente ese error y salio "0 bytes fuera del array",
porque comparaba el final de la escritura contra el final del array **en la base del
host**. Comparado contra la base de la copia, que es donde estan de verdad, sobran 108.

Es el mismo error de referencia que da el fallo real: **comparar contra el sistema de
coordenadas equivocado produce un "no hay problema" que es falso.** Por eso la
verificacion de este documento esta en tabla, no en nombre de campo.

## Y el mismo error existe en TODAS las rutas, no solo en Polaris12

Esto es lo que la verificacion **corrigio**. Una version anterior de este documento
afirmaba que las rutas antiguas copiaban desde el offset 0 y por eso su calculo era
correcto. **Es falso**, y lo fui a comprobar linea por linea:

| fichero | linea | campo de inicio de la copia | `offsetof` |
|---|---:|---|---:|
| `tonga_smumgr.c` | 2437 | `SystemFlags` | **108** |
| `iceland_smumgr.c` | 2057-2058 | `SystemFlags` | **108** |
| `fiji_smumgr.c` | 2105 | `SystemFlags` | **108** |
| `polaris10_smumgr.c` | 2118-2120 | `SystemFlags` | **108** |
| `vegam_smumgr.c` | 2134 | `SystemFlags` | **108** |

`offsetof(SystemFlags) = 108` en las cinco cabeceras, medido: `smu71`, `smu72`, `smu73`,
`smu74` y `smu75`.

**Tonga, Iceland y Fiji tienen exactamente el mismo patron de calculo, y el mismo hueco
de 108 bytes.** Por tanto **no es una regresion de SMU 7.4**: la formula
`dpm_table_start + offsetof(campo)` esta equivocada en toda la familia, en todas las
generaciones.

Eso cambia el alcance de forma importante y en dos direcciones:

- **Para mi placa no cambia nada**: el fallo de Polaris12 sigue siendo real y verificado.
- **Pero `210` y `104` no son un hallazgo de Polaris12**, son de la familia SMU7 entera. Y
  eso es un dato mas fuerte para un driver propio: no es una caracteristica exotica de la
  ruta de Polaris12 que hay que vigilar especialmente, es una convencion de codigo que
  hay que rehacer, en cualquier ruta.

Y explica una paradoja: si el error fuera real y tan grave en Tonga, Tonga habria
arrancado mal. Opciones: (a) el firmware de esas generaciones colocaba los campos en el
offset del host y el de SMU 7.4 no, o (b) hay compensacion en otro sitio. **No lo he
determinado**, y es `CONNECTION_MISSING`: no he buscado si `dpm_table_start` que devuelve
la lectura de la cabecera esta ya desplazado por el firmware, en lugar de ser la base
literal.

Y esa es **la pregunta que decide todo el hallazgo**, y la dejo abierta:

> `dpm_table_start` es la direccion **literal** del campo `DpmTable` de la cabecera del
> firmware, o la direccion a la que hay que sumar 108 para llegar al primer campo que
> escribe el host?

Si es la literal, los once usos estan desviados 108 bytes. Si el firmware define
`DpmTable` de modo que `dpm_table_start + 108` sea el inicio de la parte gestionable por el
host, entonces el codigo **deberia** sumar 108 y no lo hace, y el error es al reves.

No lo puedo decidir sin el firmware. Lo que si es `PROVEN` es que **el codigo y el layout
de la struct usan dos bases distintas sin que nada lo reconcilie**, y que la consecuencia
es que los once usos apuntan a direcciones 108 bytes distintas de las que el layout dice.
Que el firmware lo compense o no es `NOT_IN_CORPUS`.

## Que queda abierto

`polaris10_get_mac_definition` (`:2400`) usa `LowSclkInterruptThreshold` y el
`update_sclk_threshold` de VegaM tiene una funcion equivalente con la misma forma. En
VegaM la copia empieza en 0, asi que ahi el calculo acierta: el mismo codigo, el mismo
error teorico, resultado distinto por generacion. Eso es lo que hace que esto no sea "un
bug de Polaris10" sino "una formula correcta para SMU <= 7.3 aplicada sin revisar a
SMU >= 7.4".

## Lo que NO dice

No dice que los valores que hay ahora en la SRAM sean erroneous. La tabla la escribe el
firmware al arrancar segun su propio layout, y el host la sobrescribe con datos
descolocados. Que el host haya escrito en `MemoryACPILevel` lo que el firmware puso en
`GraphicsLevel[0]` es un hecho; cual de los dos valores queda depende del orden real de
escritura en marcha: `RUNTIME_MISSING`.

No se si el firmware lee `GraphicsLevel[0]` o `GraphicsLevel[1]`. `SEMANTIC_MISSING`.

No hay lectura de hardware, no hay escritura, no hay `/sys`, no hay modulos.

## Clasificacion

- `SMC_DPM_OFFSET_HOLE_NOT_COMPENSATED = PROVEN`: once usos de
  `dpm_table_start + offsetof(...)`, ninguno resta `offsetof(SystemFlags) = 108`.
- `SMC_DPM_OFFSET_MIXES_REFERENCE_FRAMES = PROVEN`: `dpm_table_start` es la base del
  firmware; `offsetof` es un offset en la struct del host. Distintas bases.
- `SMC_GRAPHICS_LEVEL_OVERRUNS_ACPI_AND_MEMORY = PROVEN_DERIVED`: 448 B escritos en
  `+236`; el array real esta en `+128..+575`. Invade `MemoryACPILevel` (24 B) y 84 de los
  96 de `MemoryLevel`.
- `SMC_MEMORY_LEVEL_OVERRUNS_LINK_LEVEL = PROVEN_DERIVED`: 96 B en `+708`; el array real
  esta en `+600..+695`. Invade 108 de los 128 de `LinkLevel`.
- `SMC_VR_CONFIG_HITS_VR_HOT_LEVEL = PROVEN_DERIVED`: `:140`, offset 112 + 108 = 220.
- `SMC_BOOT_MVDD_HITS_CLOCK_STRETCHER = PROVEN_DERIVED`: `:164`, offset 1592 + 108 = 1700.
- `SMC_ALL_ROUTES_COPY_FROM_SYSTEM_FLAGS = PROVEN`: las cinco (`tonga:2437`,
  `iceland:2057`, `fiji:2105`, `polaris10:2118`, `vegam:2134`) copian desde
  `offsetof(SystemFlags) = 108`. **Una version anterior de este documento decia que las
  rutas antiguas copiaban desde offset 0. Es falso.**
- `SMC_WHETHER_FIRMWARE_COMPENSATES_108 = NOT_DETERMINED`: si `dpm_table_start` apunta al
  inicio real de la struct o al inicio de la parte gestionable por el host decide si los
  once usos estan desviados o si el host deberia sumar 108. `CONNECTION_MISSING` y
  `NOT_IN_CORPUS`: requiere el firmware.
- `SMC_ERROR_IS_SILENT = PROVEN`: las direcciones resultantes estan alineadas y dentro del
  rango que `SMC_RAM_END` acepta, luego ningun assert se dispara. `100` explica por que el
  rango es amplio.
- `SMC_DETECTION_NEEDS_COORDINATE_BASE_CHECK = PROVEN` el metodo: comparar nombres de
  campo dice "OK" para los arrays. Hay que comparar rangos en la base de la copia.

## Lo que esto obliga a hacer en un driver propio

**Una sola funcion para convertir un campo en direccion**, y que esa funcion este probada
contra el layout real:

```c
static inline uint32_t smc_addr(const struct polaris10_smumgr *s,
                                size_t offsetof_campo)
{
        return s->smu7_data.dpm_table_start
                + offsetof_campo
                - offsetof(struct SMU74_Discrete_DpmTable, SystemFlags);
}
```

Que el compilador fuerce a pasar por ahi: **ningun sitio deberia poder sumar
`dpm_table_start` y `offsetof` sin pasar por esa funcion.** Es la unica defensa real
contra este error, porque el resultado es silencioso por naturaleza.

Y el test que lo caza sin hardware: al terminar la inicializacion, leer de la SRAM los
`n` bytes de cada array que el driver creo haber escrito, y compararlos con lo que tiene
en memoria. Si el desplazamiento es de 108, la comparacion falla en el primer array. No
hace falta placa: hace falta poder leer la SRAM del SMC, que es lo unico que `100` ya
demuestra que no hay forma de verificar.

> **ACTUALIZACION.** Esta pregunta ya no esta abierta: `212` la resuelve con evidencia
> indirecta pero solida. La lectura de `PmFuses` en `:529` extrae cuatro bytes
> consecutivos con los shifts que el layout exige, lo que prueba que el layout del host y
> el del firmware coinciden byte a byte. De ahi se sigue la **lectura (A)**: los once
> usos estan **desviados 108 bytes**. Estado `PROVEN_DERIVED`.

## CORRECCION GRAVE de este documento, hecha en la misma sesion

**El orden de las llamadas reduce esto de hallazgo vivo a defecto latente.** Una version
anterior de este documento daba a las copias parciales un impacto grave. Es falso, y la
razon es el orden real dentro de `polaris10_init_smc_table`.

### El orden, verificado

```
1952  populate_smc_link_level        escribe en table, no copia
1956  populate_all_graphic_levels    escribe en table y COPIA 448 B a +236
1960  populate_all_memory_levels     escribe en table y COPIA  96 B a +708
1964  populate_smc_acpi_level        escribe en table          <-- SI existe
1968  populate_smc_vce_level
1972  populate_smc_samu_level
1980  program_memory_timing_parameters
1984  populate_smc_uvd_level
1988  populate_smc_boot_level
1992  populate_smc_initailial_state
1996  populate_bapm_parameters_in_dpm_table
2010  populate_avfs_parameters
2034  populate_vr_config             COPIA   4 B a +112
2118  smu7_copy_bytes_to_smc         COPIA 1776 B a +108   <-- LA COMPLETA, LA ULTIMA
2127  populate_pm_fuses              COPIA  84 B a pm_fuse_table_offset
```

### La aritmetica que lo deja latente

La copia completa cubre `[108, 1884)` en base host, y va **la ultima**. Las seis copias
parciales escriben en:

| linea | campo | escribe en base host | dentro de `[108, 1884)`? |
|---:|---|---|---|
| 147 | `GraphicsLevel` | [236..683] | si |
| 155 | `MemoryLevel` | [708..803] | si |
| 140 | `VRConfig` | [112..115] | si |
| 164 | `BootMVdd` | [1592..1593] | si |
| 2594 | `GraphicsLevel` | [236..683] | si |
| 2597 | `MemoryLevel` | [708..803] | si |

**Las seis caen dentro del rango de la copia completa**, y la copia completa va despues y
va a la direccion **correcta**. O sea: las seis escrituras desviadas **se sobrescriben**.

Por eso la invasion de 108 bytes de `GraphicsLevel` sobre `MemoryACPILevel` y `MemoryLevel`
**no llega a la SRAM**: la copia completa pone esos dos campos en su sitio despues.

Estado corregido:

- `SMC_PARTIAL_COPIES_ARE_OVERWRITTEN = PROVEN_DERIVED`: las seis caen en `[108, 1884)` y
  la copia completa de `:2118` va ultima. **El error de las parciales es latente.**
- `SMC_PARTIAL_COPIES_ERROR_IS_REAL = PROVEN`: la aritmetica del desfase sigue siendo
  correcta; lo que cambia es que **queda tapado**, no que no exista.

### Lo que NO queda tapado, y es donde sigue el hallazgo

**`210` sigue vivo y no se corrige con esto.** El parche de UVD/VCE (`:2292`, `:2328`)
ocurre en `polaris10_update_uvd_smc_table` y `..._vce_smc_table`, que se llaman **fuera**
de `init_smc_table`, en el camino de transicion DPM. No hay ninguna copia completa
detras que los tape. El byte de `BootVddc` que pisan se queda pisado.

Ese es el unico sitio de la lista donde el error de 108 bytes **llega a la SRAM**.

### Y una correccion de metodo, la tercera del mismo tipo

Mi tabla original de "que hay realmente ahi" decia, para `:140`, que `VRConfig + 108 = 220`
caia en `VRHotLevel`. **Es una cuenta que no significa nada**, porque la copia completa no
coloca los campos en `offsetof + 108` sino en `offsetof - 108`. Lo que hay que comparar
es el **rango completo** de cada escritura contra el rango de la copia que la puede
sobreescribir.

La misma clase de error que ya me corrigio dos veces: **comparar contra el sistema de
coordenadas equivocado produce un "no hay problema" o un "hay problema" que no es cierto.**
Tres veces en tres documentos consecutivos, por el mismo motivo.


## CORRECCION 2026-10-02: la invasion de MemoryLevel NO EXISTE

`214` encontro un bug de ambito en `smc_copy_scope` que resolvia las variables locales
una sola vez para el fichero entero. Con ese bug, la herramienta atribuia a `MemoryLevel`
el rango de `GraphicsLevel`. Corregido, da lo correcto:

```
:1143  236..683  448 B   polaris10_populate_all_graphic_levels   (GraphicsLevel)
:1243  708..803   96 B   polaris10_populate_all_memory_levels    (MemoryLevel)
```

Y con el rango correcto, la invasion que este documento atribuia a `MemoryLevel`
**desaparece**:

```
MemoryLevel: offset 708, 96 B  -> ocupa 708..803
LinkLevel:   offset 804
la escritura acaba en 803, LinkLevel empieza en 804  ->  NO invade
```

**La copia parcial de `:1243` escribe 96 bytes en `708..803`, y `LinkLevel` empieza en
804.** No hay invasion. Este documento la afirmaba porque comparaba el rango **sin
compensar** (`708..803`) contra el array **compensado** (`600..695`), que son dos bases
distintas.

Es la **quinta vez** el mismo error: sumar 108 donde habia que restar, o comparar una
posicion de tabla contra un offset de struct. En `209`, en `104` dos veces, en `210`, y
aqui.

### Y la de GraphicsLevel, esa si se sostiene

La invasion de `GraphicsLevel` **si** es real, y por un motivo distinto: la copia es de
**448 bytes**, el array completo, y va en `236..683`. Con el array real en `128..575`, la
escritura se sale por `576..683`, que cae sobre:

| campo | offset | bytes invadidos |
|---|---:|---:|
| `MemoryACPILevel` | 684 | 0, porque 683 < 684 |
| `MemoryLevel` | 708 | 0, porque 683 < 708 |

Espera: `683 < 684`, asi que **tampoco invade**. Reviso las dos con la aritmetica:

```
GraphicsLevel declarado: offset 236, 448 B  ->  236..683
array real tras la copia (base - 108):        ->  128..575
la escritura acaba en 683; el array acaba en 575 ->  se sale en 576..683
que hay en 576..683 de la struct?
```

### La invasion de GraphicsLevel, medida byte a byte

Los 108 bytes que la escritura se sale del array (`576..683` en base struct) caen
**dentro del propio `GraphicsLevel`**, no en otros campos:

```
byte 576 -> GraphicsLevel (offset 236, 448 B), byte interno 340
...
byte 683 -> GraphicsLevel (offset 236, 448 B), byte interno 447
```

`GraphicsLevel` esta declarado en 236 y mide 448 B, o sea que **ocupa `236..683`**. La
escritura va de `236` a `683`: **exactamente el array completo**, sin invadir nada.

O sea: **la invasion tampoco existe.** Mi cuenta decia que la escritura se salia del
array en `576..683` y que eso caia sobre `MemoryACPILevel` y `MemoryLevel`, pero esos
campos estan en 684 y 708, y `683 < 684`. **No los alcanza.**

Lo que la invasion de mi documento era, en realidad, la **diferencia entre donde la
copia coloca el array** (`128..575`, compensada) **y donde escribe la copia parcial**
(`236..683`, sin compensar). Son las dos posiciones del mismo array, y la diferencia son
108 bytes. Es el desfase de 108 otra vez, no una invasion.

### Y que queda de este documento, entonces

**El desfase de 108 bytes es `PROVEN`** y sigue siendo el contenido de este documento:
once usos de `dpm_table_start + offsetof(...)` que no compensan el hueco. Lo que **no**
existe es ninguna invasion de memoria por esa causa:

| afirmacion de una version anterior | estado |
|---|---|
| `GraphicsLevel` invade `MemoryACPILevel` (24 B) y `MemoryLevel` (84 B) | **REFUTED**: `GraphicsLevel` acaba en 683, `MemoryACPILevel` empieza en 684 |
| `MemoryLevel` invade `LinkLevel` (108 B) | **REFUTED**: `MemoryLevel` acaba en 803, `LinkLevel` empieza en 804 |
| las copias parciales son sobreescritas por la completa de `:2118` | `PROVEN`, y sigue siendo cierto |

Las tres invasiones eran el **mismo numero, 108**, en tres sitios distintos, lo cual es
justo lo que hace sospechar de un error de calculo antes que de tres defectos
coincidentes. Y el error de calculo era mio: comparar el rango sin compensar contra el
array compensado, o contra el array declarado.

La quinta vez. `209`, `104` dos veces, `210`, y aqui.

Y eso tiene una consecuencia util: **el unico sitio donde el desfase de 108 llega a la
SRAM sin que nada lo tape sigue siendo el parche registro a registro de `210`/`107`**, que
no es una copia sino un leer-modificar-escribir, y por eso la copia de `:2118` no lo
cubre. Ese hallazgo no dependia de ninguna invasion y **no cae**.
