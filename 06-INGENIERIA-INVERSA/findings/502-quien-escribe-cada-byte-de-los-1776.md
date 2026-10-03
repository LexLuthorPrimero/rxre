# 502 · Quién escribe cada byte de los 1776, y por qué la copia es condicional

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> La tabla de 95 campos que la copia de 1776 B sube al SMC, campo a campo, con
> su **último escritor**. De ellos, **73 los escribe `polaris10_init_smc_table`** y
> **22 no los escribe nadie**: 21 se subirán **en cero, siempre**.
>
> Y la copia **no es incondicional**: hay **16 puertas de retorno temprano** entre
> `:1913` y `:2118`, y si cualquiera salta, los 1776 bytes no se suben.

## La fuente, y una deducción que no era obvia

```c
2118 result = smu7_copy_bytes_to_smc(hwmgr,
2119 smu_data->smu7_data.dpm_table_start +
2120 offsetof(SMU74_Discrete_DpmTable, SystemFlags),
2121 (uint8_t *)&(table->SystemFlags),
2122 sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
2123 SMC_RAM_END);
```

Medido por gcc: `sizeof` = **1884**, `offsetof(SystemFlags)` = **108**,
`sizeof(SMU74_PIDController)` = **36**. Así que `1884 − 3×36` = **1776**.

**El `− 3*sizeof(PIDController)` no excluye nada del final**: es una forma
indirecta de calcular `offsetof(SystemFlags)`, que ya es exactamente `3×36`. La
copia va **de `SystemFlags` al final del struct**, `108..1883`. Confirmado:
`108 + 1776 = 1884`.

**98 campos** declarados en `SMU74_Discrete_DpmTable` (`smu74_discrete.h:236`),
de los cuales **95 caen en el rango copiado**.

## Que se suba en cero no es basura: es `kzalloc_obj`

Antes de preguntarse qué campos quedan sin escribir, la pregunta es qué tienen si
nadie los escribe. La tabla vive en

```c
polaris10_smumgr.h:57: SMU74_Discrete_DpmTable smc_state_table;
```

dentro de `struct polaris10_smumgr`, y se asigna en

```c
polaris10_smumgr.c:339: smu_data = kzalloc_obj(struct polaris10_smumgr);
```

**`kzalloc`**, no `kmalloc`. La tabla empieza **en cero**. No hay ningún `memset`
de ella en el fichero —el único `memset` es `:2574`, de `mc_reg_table`.

Así que un campo sin escritor se sube como **cero, de forma determinista**, no como
basura. Eso convierte la pregunta «qué campos quedan sin escribir» en «qué campos
son cero por construcción», que es una pregunta con respuesta.

## El reparto

```
Alcance transitivo desde polaris10_init_smc_table: 20 funciones
campos en el rango copiado: 95
con >=1 escritura: 73
SIN escritura: 22
```

**18 de los 22 tienen CERO apariciones en todo el fichero** — no solo no los escribe
`init_smc_table`: no los escribe nadie, en ningún sitio.

| campo | offset | tamaño | por qué está en cero |
|---|---|---|---|
| `AcpLevel` `AcpLevelCount` `AcpBootLevel` | 1204, 214, 1578 | 12, 1, 1 | ACP es motor de display: **Polaris10 no lo tiene** |
| `DTEInterval` `DTEMode` | 1602, 1603 | 1, 1 | DTE: no activado en esta ruta |
| `SVI2Enable` | 1604 | 1 | esquema SVI2, no usado aquí |
| `PPM_PkgPwrLimit` `PPM_TemperatureLimit` | 1608, 1610 | 2, 2 | seguimiento de potencia de paquete |
| `FpsHighThreshold` `FpsLowThreshold` | 1616, 1618 | 2, 2 | umbral de respuesta del ventilador |
| `ClockStretcherAmount` `ClockStretcherDataTable` `CKS_LOOKUPTable` | 1700, 1712, 1728 | 1, 16, 32 | ver más abajo |
| `Sclk_CKS_masterEn8_15` | 1702 | 1 | ver más abajo |
| `MasterDeepSleepControl` `BootPhases` `VddGfxReChkWait` `DPMFreezeAndForced` | 211, 219, 1696, 1703 | 1 | no activados en esta ruta |
| `Reserved1` `Reserved2` `Reserved` | 223, 230, 232 | 1, 2, 4 | **relleno**: que estén en cero es lo correcto |

El patrón es coherente: los 22 son campos de motores que Polaris10 no tiene
(ACP), de funciones que esta ruta no activa (DTE, SVI2, PPM, FPS), o **relleno de
estructura**. No hay ni uno solo que sea un campo de reloj o de voltaje activo que
se esté quedando sin inicializar por error.

## Los tres casos que merecen explicación

### `LowSclkInterruptThreshold@1692`: confirma `:2398` por otra vía

Es el **único** de los 22 que aparece en el fichero, y sus 3 apariciones son
`:2402` (la copia de overdrive) y `:2455-2456` (una tabla de offsets).

**Se sube en CERO tras init, y solo lo escribe el camino de overdrive.** Eso
corrobora `:2398` **desde un ángulo independiente**: no por el orden de las
llamadas que tracé en `403`, sino por el contenido del campo. Si `:2398`
sobreviviera a la copia, el campo quedaría con el valor del host; si la copia lo
pisara, quedaría en cero.

Y `:2398` no está en los 20 funciones alcanzables desde `init_smc_table`, luego no
puede escribir antes de `:2118`.

### El clock stretcher: dos campos con nombre parecido, y **NO** son el mismo

`267` midió `usClockStretchAmount = 2` en la tabla **PowerTune** de mi VBIOS, con
layout Fiji, offset 25. Acabo de volver a medirlo en mi VBIOS:

```
PowerTune @0x9EAB rev = 4 -> layout Fiji
usClockStretchAmount (offset 25) = 2
```

**Coincide.** Pero ese es un campo de la **tabla VBIOS**, y el campo de la tabla
DPM se llama `ClockStretcherAmount` y **está en `@1700` y nadie lo escribe en
`polaris10_smumgr.c`**.

Dos campos, tablas distintas, nombres parecidos: `NAME_MATCH ≠ SEMANTIC_MATCH`.
El `2` de mi VBIOS **no** es el valor que se sube a `@1700`. Ese se sube en cero.

### El comentario que miente sobre el CKS

`:1695` dice:

```c
/* Populate CKS Lookup Table */
if (stretch_amount == 0 || stretch_amount > 5) {... return -EINVAL; }
value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, ixPWR_CKS_CNTL);
```

El comentario anuncia rellenar la tabla de lookup. **El código no la rellena**:
comprueba el valor, sale si no vale, y limpia el bit 0 de un registro. `CKS_LOOKUPTable@1728`
son 32 bytes de cero con un comentario que promete lo contrario.

**Defecto de upstream, no de mi VBIOS.** Y encaja con `Sclk_CKS_masterEn0_7@1701`
—que sí se escribe— frente a `Sclk_CKS_masterEn8_15@1702`—que no. El par es
coherente: hay 8 niveles SCLK (VBIOS), así que los niveles 8-15 no existen y su
máscara es cero.

## La copia es condicional: 16 puertas

Enumeradas todas las salidas entre `:1913` y `:2118`:

```
:1946 populate_ulv_state:1953 populate_smc_link_level
:1957 populate_all_graphic_levels:1961 populate_all_memory_levels
:1965 populate_smc_acpi_level:1969 populate_smc_vce_level
:1973 populate_smc_samu_level:1981 program_memory_timing_parameters
:1985 populate_smc_uvd_level:1989 populate_smc_boot_level
:1993 populate_smc_initailial_state:1997 populate_bapm_parameters
:2005 populate_clock_stretcher_data_table
:2011 populate_avfs_parameters:2035 populate_vr_config
:2095 atomctrl_get_dfs_pll_dividers_vi -> "Can not find DFS divide id for Sclk"
```

Todas con `PP_ASSERT_WITH_CODE(..., return result)`. **Cualquiera que falle impide
que se suban los 1776 bytes.** La última, `:2095`, depende de encontrar un
divisor DFS para SCLK en la tabla BIF, y **esa tabla no está en mi corpus**.

## La puerta del clock stretcher, medida en mi placa

`:2002` solo entra si `PHM_PlatformCaps_ClockStretcher` está activo. Ese cap se
pone en `smu7_hwmgr.c:1941`:

```c
if ((hwmgr->pp_table_version != PP_TABLE_V0) && (hwmgr->feature_mask & PP_CLOCK_STRETCHER)
 && (table_info->cac_dtp_table->usClockStretchAmount != 0))
 phm_cap_set(hwmgr->platform_descriptor.platformCaps, PHM_PlatformCaps_ClockStretcher);
```

y se **quita** en `:1975`:

```c
if ((adev->pdev->device == 0x699F) && (adev->pdev->revision == 0xCF)) {
...
 phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
}
```

**Mi `device` es `0x699F` y mi `rev` es `0xC7`. La condición pide `0xCF`. No se
cumple**, así que este bloque **no me aplica** y el cap no se quita aquí.

Con lo medido:

| condición | estado |
|---|---|
| `usClockStretchAmount != 0` | **PROVEN**: 2 en mi VBIOS |
| `revision == 0xCF` | **REFUTED** para mi placa: es `0xC7` |
| `pp_table_version != PP_TABLE_V0` | **NOT_DETERMINED** |
| `feature_mask & PP_CLOCK_STRETCHER` | **NOT_DETERMINED** |
| `stretch_amount` en `(0,5]` | **PROVEN**: 2 cumple |

Si el cap está activo, `:1696` no salta (2 está en el rango), la función devuelve 0
en `:1708`, y la copia ocurre. **Lo que no puedo afirmar es que el cap esté activo**:
depende de dos condiciones que no he verificado.

**Y aunque el cap no estuviera activo, la copia ocurriría igual**: sin `:2004`, no
hay puerta. La revisión `0xCF` no cambia si se suben los 1776 bytes; cambia si los
campos CKS se rellenan.

## Sobre la revisión, con honestidad

El `0xC7` viene de `revkit/obs.py:37`, un **portador secundario**: ninguna captura
primaria lleva la revisión. Aquí es **discriminante**, porque decide si el cap de
clock stretcher se quita. Un dato de fuente secundaria está decidiendo una
 bifurcación de la cadena de init. **Es la primera vez que eso ocurre en esta rama,
y conviene que quede dicho.**

## Dos errores míos, y el primero casi destruía el resultado

**1. Leí la captura VBIOS como texto hexadecimal.** La captura es **binario crudo**
(58880 bytes leídos como texto), no un volcado hex. Mi regex recuperó **223 bytes
de 58880** y produjo un index error. Si no hubiera comprobado el número de bytes
recuperados, habría reportado el valor de un byte de otra parte del fichero.

Lo detecté por una condición que ya es costumbre: **contar antes de interpretar**.
Es la segunda vez que esa regla salva un resultado, después del `grep` de `287`.

**2. Mi primer modelo de grafo de llamadas tenía un solo nivel.** Solo registraba 
funciones que `init_smc_table` llama **directamente**, así que todo lo que escribieran
sus callees salía como «nadie lo escribe». Daba **31** campos sin escritor.

Al pasar a **grafo transitivo** (20 funciones alcanzables) el número bajó a **22**:
**9 eran falsos positivos míos**. Uno de ellos era `SclkFcwRangeTable`, que se
escribe desde la **VBIOS** (`:857-868`) y, si esa lectura falla, desde una tabla
**hardcodeada** (`:873-886`).

Un modelo de grafo de llamadas con un nivel no es un modelo: es un **`NOT_FOUND`
disfrazado de ausencia**, que es exactamente el error contra el que este proyecto
avisa desde el principio.

## Lo que NO afirmo

- **NO** afirmo que la copia ocurra en mi placa. Está tras **16 puertas**; he
 medido la del clock stretcher en dos de sus cinco condiciones.
- **NO** afirmo nada de `:2095`: depende de `bif_sclk_table`, **fuera de mi corpus**
 (`EVIDENCE_MISSING`).
- **NO** afirmo la revisión `0xC7` como hecho primario. Viene de un portador
 secundario y aquí es discriminante.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`; hace falta
 `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** he tocado `smc_copy_scope.py` ni el árbol de kernel. `MODIFICATIONS 0`.

## Artefacto

La tabla completa de los 95 campos con offset, tamaño y último escritor está en
`/tmp/opencode/tabla_1776.txt`, generada con:

- `gcc` para el layout (98 campos, extraídos de `smu74_discrete.h:236`, no escritos
 a mano);
- grafo de llamadas transitivo sobre `polaris10_smumgr.c`;
- clave de orden `(nivel_de_llamada, línea_del_sitio, línea_en_callee)`.

**No está en el repositorio** porque es reproducible y regenerable, y porque un
fichero generado a mano en el árbol de hallazgos se convierte pronto en una
afirmación sin fuente. La regla es la de siempre: lo que se puede volver a calcular,
se vuelve a calcular.

## Frontier siguiente

**Cerrar las dos condiciones del cap de clock stretcher**: `pp_table_version !=
PP_TABLE_V0` y `feature_mask & PP_CLOCK_STRETCHER`.

No salen de `polaris10_smumgr.c` ni de la VBIOS: salen de cómo se rellena
`hwmgr->platform_descriptor.platformCaps`, que se construye en
`smumgr_init_smc_data` / `polaris10_smu_init` a partir de la **tabla de
características de plataforma** del VBIOS (`pptable_info->platform_table`). Esa
tabla **sí está en mi captura**, y `phm_cap_set` deja los caps en un mapa que se
puede volcar campo a campo igual que he hecho con los 95.

Es el mismo método, aplicado a un origen distinto: **extraer la tabla del VBIOS,
medirla con gcc, y listar qué caps se activan y cuáles no.**

Criterio de cierre: la lista de los 32 caps de `platformCaps` con su estado final en
mi placa, y con ello `PHM_PlatformCaps_ClockStretcher` pasa de `NOT_DETERMINED` a
`PROVEN` o `REFUTED`.