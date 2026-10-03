# 275 · Los 9 NO_RESUELTO eran 7 del mismo patron: 6 medidos y TAPADAS por la copia de 1776 B

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> Los 9 `NO_RESUELTO` de `smc_copy_scope` **no son 9 incognitas**. Son **7 del
> mismo patron** (variable local asignada a `base + offsetof`) y **2 que
> ningun analisis estatico puede resolver**, porque la direccion la lee el SMC
> en runtime. Y de los 7 resolubles, **6 quedan medidas**, y las 6 caen dentro
> de la copia de 1776 B de `:2118`.

## La taxonomia, que es el hallazgo de verdad

| patron | lineas | n | ¿resoluble estaticamente? |
|---|---:|---:|---|
| `local = base + offsetof(T, F)` | 142, 149, 157, 166, 1146, 1246 | 6 | **SI** |
| local + `sizeof(T) - 92` | 654 | 1 | parcial: tamano si, base pendiente |
| direccion leida del SMC en runtime | 1872, 1881 | 2 | **NO, por principio** |

### Las 2 irresolubles, y por que

```c
1868  smu7_read_smc_sram_dword(hwmgr,
1869          SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, AvfsMeanNSigma),
1870          &tmp, SMC_RAM_END);
1872  smu7_copy_bytes_to_smc(hwmgr, tmp, &AVFS_meanNsigma, sizeof(...), SMC_RAM_END);
```

El destino es `tmp`, y `tmp` **es lo que el SMC acaba de devolver**. La
direccion de destino la decide el firmware en tiempo de ejecucion. Ninguna
herramienta estatica puede resolverla, y no es un fallo de la herramienta: es
`PROVEN_ABSENT` para el metodo.

**Y la herramienta ya lo distingue**: para esas dos dice *"destino no
reconocido: tmp"*, y para las otras seis *"variable local"*. Es una distincion
correcta que ya hace. Se lo reconozco.

## Las 6 medidas, con gcc

`gcc` sobre `smu74_discrete.h`, `-Wall -Wextra` sin un aviso:

```
offsetof(VRConfig)       = 112
offsetof(GraphicsLevel)  = 236
offsetof(MemoryLevel)    = 708
offsetof(BootMVdd)       = 1592
SMU74_MAX_LEVELS_GRAPHICS = 8      sizeof(GraphicsLevel) = 56  ->  448
SMU74_MAX_LEVELS_MEMORY   = 4      sizeof(MemoryLevel)   = 24  ->   96
sizeof(SMU74_Discrete_PmFuses) = 176   ->  :654 copia 176 - 92 = 84
```

| linea | destino | tamano | rango en la RAM del SMC |
|---|---|---|---|
| `:142` | `VRConfig` @ 112 | `sizeof(uint32_t)` = 4 | **112..115** |
| `:149` | `GraphicsLevel` @ 236, constantes AVFS | 448 | **236..683** |
| `:157` | `MemoryLevel` @ 708, constantes AVFS | 24 | **708..731** |
| `:166` | `BootMVdd` @ 1592 | 24 | **1592..1615** |
| `:1146` | `GraphicsLevel` @ 236, tabla de host | 448 | **236..683** |
| `:1246` | `MemoryLevel` @ 708, tabla de host | 96 | **708..803** |

## Y ahora la cobertura, que es lo que el tool no podia responder

La copia de `:2118` cubre `108..1883` (`offsetof(SystemFlags)=108`, y
`1884 - 3*36 = 1776`). **Las seis caen dentro:**

```
:142   112..115    TAPADA
:149   236..683    TAPADA
:157   708..731    TAPADA
:166  1592..1615   TAPADA
:1146  236..683    TAPADA
:1246  708..803    TAPADA
```

**Eso responde la pregunta que `262` dejo abierta.** No es que la cobertura
fuera cero: es que **seis de las nueve escrituras que no podia resolver estan
tapadas**, y la herramienta no lo veia porque no tenia los offsets.

Y encaja con `263` y `265` sin contradecirlos, que es la comprobacion que mas me
importa aqui:

- `263` demostro que la copia de `:2118` corre **despues** de
  `setup_graphics_level_structure`, que escribe las constantes AVFS en 236 y
  708.
- `265` demostro que lo que sobrevive es la tabla **derivada del VBIOS**.
- Esto anade que **las dos fuentes escriben los mismos 236..683 y 708..803**, y
  el orden decide. El VBIOS gana.

**Los tres hallazgos se cierran en una sola cadena, y ahora con numeros medidos
en vez de una deduccion.**

## El caso que el tool ya sabia manejar

`graphics_level_address` toma **tres valores distintos en la misma funcion**:

```c
147  graphics_level_address = dpm_table_start + offsetof(..., GraphicsLevel);
155  graphics_level_address = dpm_table_start + offsetof(..., MemoryLevel);
164  graphics_level_address = dpm_table_start + offsetof(..., BootMVdd);
```

Un resolvedor por ambito de *funcion* se come las tres. Resolverlo exige
seguir el punto de uso, no el nombre. Es la limitacion concreta que impide que
la herramienta cierre estas seis, y **esta escrita en su propio codigo**
(`:689-700` documenta el caso equivalente para `array`).

## CORRECCION: el hueco del tool NO era la indireccion de variable local

Escribi que a `smc_copy_scope` le faltaba resolver `local = base + offsetof`. **Es falso, y lo he comprobado antes de dejarlo escrito.**

`RE_LOCAL_ADDR` (`:170`) **casa perfectamente** con las tres formas reales:

```
declarado simple      -> CASA  nombre='vr_config_address'
asignacion simple     -> CASA  nombre='graphics_level_address'
declarado multilinea  -> CASA  nombre='array'
```

La causa real era **mi fichero de offsets incompleto**: le pase 5 y no incluia
`VRConfig`, `GraphicsLevel`, `MemoryLevel` ni `BootMVdd`. El mensaje «variable
local» era el `offsetof` sin valor, no una falta de capacidad. **Es el mismo
fallo que cometi al principio de esta rama: dar por hecho el input.**

Al darle los 9 offsets y los 7 tamanos, todo medido por gcc:

```
antes   13 escrituras ·  5 offsets ·  5 tamanos ->  4 VIVA,  9 NO_RESUELTO
ahora   13 escrituras ·  9 offsets ·  7 tamanos ->  6 VIVA,  7 NO_RESUELTO
```

Dos escrituras mas resueltas **sin tocar la herramienta**. Un error mio.

## Los cuatro huecos que quedan, ahora si nombrados

**1. Cadenas de alias en `#define`.** El multiplicador no es literal:

```
inc/smu74.h:134   #define SMU74_MAX_LEVELS_GRAPHICS  SMU__NUM_SCLK_DPM_STATE
inc/smu74.h:32    #define SMU__NUM_SCLK_DPM_STATE    8
```

`--lectura-defines` lee literales y no sigue el alias. Resueltos a mano,
`array_size` de `:1146` y `:1246` serian `56*8=448` y `24*4=96`.

**2. `sizeof(<variable>)` en vez de `sizeof(<tipo>)`.**

```
:93   static const SMU74_Discrete_MemoryLevel avfs_memory_level_polaris10 = {
:157  ... sizeof(avfs_memory_level_polaris10) ...
```

El nombre es una variable, no un tipo. Falta mapear nombre -> tipo desde la
declaracion.

**3. Multi-asignacion: la ultima pisa a las anteriores.** Confirmado y
**visible en la salida**:

```
:166  graphics_level_address  tam=1592..1593   <- BootMVdd, la TERCERA asignacion
```

Y se aplica tambien a `:149` y `:157`, donde no corresponde. Con tres
asignaciones en `:147`, `:155` y `:164`, el mapa por nombre solo guarda la
ultima. Resolverlo exige seguir el **punto de uso**, no el nombre.

**4. `X = sizeof(T)` sin el `* CONST`.**

```
:128  graphics_level_size = sizeof(avfs_graphics_level_polaris10);
```

La herramienta tiene el patron para `sizeof(T) * CONST` (`:723`), no para
`sizeof(T)` a secas.

Los cuatro son pequenos, localizados, y ninguno exige redisenar la herramienta.

## Lo que faltaba, y aqui SI queda resuelto

**La base de `:654`.** La he rastreado:

```
611  smu7_read_smc_sram_dword(hwmgr,
612      SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, PmFuseTable),
613      &pm_fuse_table_offset, SMC_RAM_END)
```

**Tercera direccion leida del SMC en runtime**, igual que `tmp` en `:1872` y
`:1881`. Es `PROVEN_ABSENT` estaticamente, no un hueco del tool. Y tiene una
segunda puerta: `:609` exige `PHM_PlatformCaps_PowerContainment`, que en `269`
vi que solo se desactiva para `0x699F/0xCF`; mi revision es `0xC7`, luego **el
bloque si corre en mi placa**.

**La taxonomia final de las nueve:**

| patron | lineas | estado |
|---|---:|---|
| `local = base + offsetof` | 142, 149, 157, 166, 1146, 1246 | **resoluble** |
| direccion leida del SMC | 654, 1872, 1881 | **`PROVEN_ABSENT` estatico** |

Tres de nueve son irresolubles por el metodo, no por la herramienta.

## Lo que NO afirmo

- **NO** afirmo que la copia de `:2118` llegue a ejecutarse en mi placa. Es el
  camino de init, y `B_RUNTIME = NOT_EXECUTED`.
- **NO** afirmo el **orden de ejecucion entre** `:1146` y `:2118`. Se que
  `:2118` va despues de `:149` (`:263`); no he trazado si `:1146` esta antes o
  despues dentro de la misma funcion. **Eso es `NOT_DETERMINED`** y cambia cual
  de las dos fuentes gana en 236..683.
- **NO** he modificado `smc_copy_scope`. Es herramienta mia y el arreglo existe,
  pero esta iteracion es read-only.
- No he medido hardware.

## El estado de la herramienta, corregido

`smc_copy_scope` **no** tiene el hueco que yo dije en la primera version de este
documento. La version corregida:

- El patron `local = base + offsetof` **ya lo resuelve**. `RE_LOCAL_ADDR` casa y
  `resuelve_destino` aplica el `offsetof`. Lo que faltaba eran los **valores**.
- Las tres direcciones leidas del SMC (`pm_fuse_table_offset`, y los dos `tmp`)
  son `PROVEN_ABSENT` estaticamente, y el tool ya las separa con otro mensaje.
- Los cuatro huecos reales son los cuatro nombrados arriba: cadenas de alias,
  `sizeof` de variable, multi-asignacion, y `sizeof(T)` sin multiplicador.

Estado: `VALIDATED` para lo que cubre. Los cuatro huecos son **adicionales y
pequenos**; ninguno es la falta de capacidad que le atribuí.

Y una leccion que vale mas que el hallazgo: **dos veces en esta rama di por
supuesto el input de la herramienta** — la primera con un fichero de offsets
incompleto, la segunda con el patron mal compilado en mi propio test. Las dos
veces la herramienta tenia razon y yo la culpe. Un `NO_RESUELTO` describe lo
que la herramienta recibio, no lo que el codigo dice.

## Frontier siguiente

Rastrear `pm_fuse_table_offset` para cerrar la octava de las nueve, y despues
extender `smc_copy_scope` para el patron `local = base + offsetof` con las
mediciones de gcc como entrada. Con eso el recuento de cobertura de
`polaris10_smumgr.c` pasa de «4 VIVA, 9 sin resolver» a un numero completo, y
`262` queda con su `TAPADA` real.

`B_RUNTIME = NOT_EXECUTED`. Sigue haciendo falta `Autorizo WRITE_EXECUTION para
B_EXPERIMENT`.