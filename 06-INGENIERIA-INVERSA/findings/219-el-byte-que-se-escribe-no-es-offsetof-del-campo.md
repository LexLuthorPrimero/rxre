# 219  El byte que se escribe no es `offsetof(campo)`: los dos parches eligen byte por convención, y no se Guestrean entre si

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CORRIGE A `103-el-parche-de-uvd-reescribe-bootvddc.md` · `107-el-parche-de-uvd-escribe-sobre-smio-5.md` ·
`108-el-determinante-del-desfase-y-lo-que-no-se-puede-cerrar.md` · CORROBORA A `218`

## Por que se abre

`218` retiro el hueco de 108 bytes. Con ello caen las invasiones de `210` y `107`, que
estaban construidas **enteras** sobre ese hueco. Pero al re-leer el codigo real para
etiquetarlas aparecio una pregunta que ni `210` ni `107` se hacian, y que es distinta:

> Las dos mascaras escriben **un byte**. ¿De que byte del DWORD se trata?

## El codigo, literalmente

`polaris10_smumgr.c:2292-2301`, parche de UVD:

```c
mm_boot_level_offset = smu_data->smu7_data.dpm_table_start
                                + offsetof(SMU74_Discrete_DpmTable, UvdBootLevel);
mm_boot_level_offset /= 4;
mm_boot_level_offset *= 4;
mm_boot_level_value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset);
mm_boot_level_value &= 0x00FFFFFF;
mm_boot_level_value |= smu_data->smc_state_table.UvdBootLevel << 24;
cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset, mm_boot_level_value);
```

`polaris10_smumgr.c:2328-2337`, parche de VCE:

```c
mm_boot_level_offset = smu_data->smu7_data.dpm_table_start
                                + offsetof(SMU74_Discrete_DpmTable, VceBootLevel);
mm_boot_level_offset /= 4;
mm_boot_level_offset *= 4;
mm_boot_level_value = cgs_read_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset);
mm_boot_level_value &= 0xFF00FFFF;
mm_boot_level_value |= smu_data->smc_state_table.VceBootLevel << 16;
cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC, mm_boot_level_offset, mm_boot_level_value);
```

## Los offsets, medidos

```
offsetof(SMU74_Discrete_DpmTable, UvdBootLevel)  = 1576
offsetof(SMU74_Discrete_DpmTable, VceBootLevel)  = 1577
offsetof(SMU74_Discrete_DpmTable, AcpBootLevel)  = 1578
offsetof(SMU74_Discrete_DpmTable, SamuBootLevel) = 1579
offsetof(SMU74_Discrete_DpmTable, GraphicsBootLevel) = 1580
```

Los cuatro primeros son `uint8_t` consecutivos (`smu74_discrete.h:298-301`), y
`1576 = 4 x 394`: **los cuatro estan en el mismo DWORD**, el palabra 394.

```
palabra 394 = [1576, 1580)
   byte 0 = 1576  UvdBootLevel    <-- el parche de UVD se ancla aqui
   byte 1 = 1577  VceBootLevel    <-- el parche de VCE se ancla aqui
   byte 2 = 1578  AcpBootLevel
   byte 3 = 1579  SamuBootLevel
```

## Que byte escribe cada parche

| parche | mascara | desplazamiento | byte del DWORD | offset en la struct | campo de la struct |
|---|---|---|---|---:|---|
| UVD | `0x00FFFFFF` | `<< 24` | 3 | **1579** | `SamuBootLevel` |
| VCE | `0xFF00FFFF` | `<< 16` | 1 | **1577** | `VceBootLevel` |

**Y aqui esta el hallazgo: los dos no concuerdan consigo mismos.**

- El parche de **VCE** escribe el byte 1, que es exactamente donde esta `VceBootLevel`.
  **Coincide con su nombre.**
- El parche de **UVD** escribe el byte 3, que es **tres bytes mas alla** de donde esta
  `UvdBootLevel`. El byte 3 lo ocupa `SamuBootLevel`.

O sea: **`offsetof(campo)` no es el byte que el parche escribe.** El `offsetof` se usa
como **ancla de la palabra** — de ahi el `/4*4` — y el byte dentro de la palabra lo elige
la convencion mascara/desplazamiento.

Y como `SamuBootLevel` solo se escribe una vez en todo el fichero,
`polaris10_smumgr.c:1429`:

```c
table->SamuBootLevel = 0;
```

...y no hay ninguna otra escritura al campo, **su valor 0 lo copia la carga completa a la
direccion 1579 y acto seguido el parche de UVD sobrescribe ese mismo byte** con el nivel
de arranque de UVD. El valor de `SamuBootLevel` **no llega nunca al firmware** por esa via.

## Por que esto NO es un bug, y como lo se

Porque el codigo es **identico en Tonga**, un ASIC de 2012 que salio al mercado:

```c
/* tonga_smumgr.c:2688-2697, literalmente las mismas dos lineas */
mm_boot_level_value &= 0x00FFFFFF;
mm_boot_level_value |= smu_data->smc_state_table.UvdBootLevel << 24;
```

Y la geometria es la misma: `offsetof(SMU72_Discrete_DpmTable, UvdBootLevel) = 1788`, que
tambien es multiplo de 4, con `VceBootLevel` en 1789, byte 1 de la misma palabra.

Un desplazamiento de byte incorrecto **reproducido verbatim en un chip que arranco durante
años no es un desplazamiento incorrecto**: es que el firmware lee ese byte. Lo que es
imposible es que el host lea ese byte por error y el firmware por acierto durante doce años.

- Que el firmware lea el byte 3 como nivel de arranque de UVD: **`NOT_IN_CORPUS`**.
- Que el host y el firmware coincidan en ese byte: **`PROVEN_DERIVED`**, por la replicas
  en dos generaciones y porque el otro funciona.

Lo que **si** es `PROVEN` y es el objeto de este documento:

1. Los dos parches apuntan a **el mismo DWORD** (`1577 / 4 * 4 = 1576`). Se confirma dos
   veces, aqui con `210` y aqui.
2. **Cada mascara preserva el byte de la otra.** UVD escribe el byte 3 y VCE el byte 1, y
   `0x00FFFFFF` no toca el byte 1 ni `0xFF00FFFF` no toca el byte 3. **No colisionan**, y
   el orden entre ellas es irrelevante.
3. **`offsetof(campo)` no identifica el byte SMC** en esta region.

## Lo que esto retira, y lo que sobrevive

| etiqueta | documento | estado |
|---|---|---|
| `SMC_UVD_PATCH_WRONG_OFFSET` | `210` | **REFUTED** (reposaba en `offsetof - 108`) |
| `SMC_UVD_PATCH_HITS_BOOT_VDDC` | `210` | **REFUTED** (`1576 + 108 = 1684`, con el hueco anulado) |
| `SMC_UVD_PATCH_DESTROYS_BOOT_VOLTAGE` | `210` | **REFUTED** |
| `SMC_PATCH_OFFSET_MIXES_REFERENCE_FRAMES` | `210` | **REFUTED** |
| `SMC_RAW_WRITE_HITS_SMIO5` | `107` | **REFUTED** (`1468 = 1576 - 108`, con el hueco anulado) |
| `SMC_RAW_WRITE_WRITES_INDEX_AS_BOOT_LEVEL` | `107` | **REFUTED** (no cae en `Smio`) |
| todo el discriminante `--hueco 108` | `108` | **REFUTED**: el hueco no existe |
| `SMC_VCE_PATCH_SAME_WORD` | `210` | **se sostiene**, rederivado |
| `SMIO_IS_AN_INDEX_NOT_A_VOLTAGE` | `107` | **se sostiene**, independiente |
| `SMIO5_IS_NEVER_WRITTEN_BY_ANY_PRODUCER` | `107` | **se sostiene**, pero queda sin consecuencia |
| `SMC_RAW_WRITE_HITS_NOT_BOOT_VDDC` | `107` | **imprecisa**: el ancla es 1576, el byte es 1579 |

Sobre `107` hay que ser justo: su parte original —*que el parche no cae en `BootVddc`*— la
confirmo, y con razon, refuteando a `210`. La que estaba mal era la localizacion
alternativa (`Smio[5]`), que venia del hueco.

## Y el alcance de la convencion, medido

`0x00FFFFFF` en cada familia:

| familia | apariciones |
|---|---|
| Tonga | 2 |
| Fiji | 2 |
| Polaris12 | 1 |
| VegaM | 1 |
| Iceland | 0 |
| CI | 0 |

En el fichero de Polaris12 **solo hay dos** read-modify-write con mascara sobre la tabla
(`:2298` y `:2334`), y **ninguno mas**. Iceland y CI no la usan, coherente con que no
tienen UVD/VCE comparable.

## Clasificacion

- `PATCH_ANCHORS_WORD_NOT_BYTE = PROVEN`: `offsetof(campo)` mas `/4*4` localizan la
  palabra; el byte lo elige la mascara con el desplazamiento.
- `PATCH_UVD_WRITES_BYTE_3 = PROVEN_DERIVED`: `0x00FFFFFF` con `<< 24` escribe el byte 3,
  offset 1579.
- `PATCH_VCE_WRITES_BYTE_1 = PROVEN_DERIVED`: `0xFF00FFFF` con `<< 16` escribe el byte 1,
  offset 1577, que **si** es donde esta `VceBootLevel`.
- `PATCH_UVD_BYTE_IS_SAMU_BOOT_LEVEL_BYTE = PROVEN_DERIVED`: 1579 =
  `offsetof(SamuBootLevel)`. El ancla y el byte **no coinciden**, y solo en UVD.
- `SAMU_BOOT_LEVEL_NEVER_REACHES_FIRMWARE_VIA_THIS_PATH = PROVEN_DERIVED`: se asigna 0 en
  `:1429`, es la unica escritura al campo, la copia completa lo lleva a 1579 y el parche
  de UVD sobrescribe ese byte. Que el firmware lea ahi otra cosa: `NOT_IN_CORPUS`.
- `PATCHES_SAME_WORD = PROVEN`: palabra 394, los dos. Rederivado desde `218`/`219`.
- `PATCH_MASKS_PRESERVE_EACH_OTHER = PROVEN`: bytes 3 y 1, mascaras disjuntas en esos bits.
  **El orden entre ellos es irrelevante.**
- `PATCH_CONVENTION_REPLICATED_IN_TONGA = PROVEN`: mismas dos lineas en
  `tonga_smumgr.c:2692-2693`, misma geometria (`1788`, multiplo de 4; `1789` byte 1). Por
  eso no es un bug.
- `FW_UVD_BOOT_LEVEL_IS_BYTE_3 = NOT_IN_CORPUS`: lo que el firmware lee ahi.
- `PATCH_SCOPE_IS_TWO_WRITES = PROVEN`: `:2298` y `:2334` son las unicas dos.

## Lo que esto obliga a hacer en un driver propio

Es la leccion practica de toda la secuencia `211` → `218` → `219`, y es la mas transferible:

1. **`offsetof(campo)` no es la direccion SMC del campo.** En esta region es el **ancla de
   la palabra**. Si mi driver escribe `smc[base + offsetof(X)] = valor` y el firmware
   espera el byte 3, escribo en el sitio equivocado.
2. **No "simplificar" el `/4*4` mas mascara a una escritura de byte directa.** El codigo
   parece redundante —alinear, leer, enmascarar, escribir— y sin embargo es lo que
   preserva los bytes vecinos. Un(driver propio que lo "limpie" introduce un fallo que
   existe en el arbol de Linux y no en el mio, que es el riesgo real al reimplementar.
3. **Un read-modify-write con mascara es un contrato de ocupacion de bits**, y hay que
   escribirlo como tal: que byte ocupa, que bytes preserva, y quien mas los ocupa. El
   `210` lo encontro a medias y por eso leyo una colision donde no la hay.
4. Y la generalizacion, que es la que mas casos cubre: **si un campo tiene dos escritores,
   las mascaras tienen que ser disjuntas en los bits que cada uno escribe**, y eso se
   comprueba leyendo las dos mascaras, no comparando nombres de campos. Aqui se cumple:
   byte 3 contra byte 1.

Y un punto sobre el proceso: `211`, `210` y `107` compartian **el mismo error de base**,
derivado uno del otro, y los tres parecian confirmarse mutuamente. **Una cadena de
hallazgos que se apoyan en el mismo supuesto no es una confirmacion multiple: es un
supuesto con tres ramificaciones.** La refutacion vino de medir una cosa que ninguno midio:
que `GraphicsLevel + 448` cae **exactamente** en `MemoryACPILevel`.