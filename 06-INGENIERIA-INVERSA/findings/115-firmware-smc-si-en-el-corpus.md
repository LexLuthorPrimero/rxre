# 115 · El firmware del SMC SI está en el corpus, y su tamaño resuelve el límite de la SRAM que `100` dejó abierto

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

RESUELVE UNA PARTE DE `100` · ACOTA `108`/`218` · CORRIGE UNA AUSENCIA FALSA MIA ·
NEGATIVE_RESULT sobre desensamblado GCN

## 1. La ausencia que yo mismo declaré era falsa

Mi memoria de sesión decía, sin ambigüedad:

> "Disposición del firmware de SMU 7.4: `NOT_IN_CORPUS`. **Firmware ausente del árbol**
> (`find` de `*.bin`/`*.hex`/`*.rom`/`*.fw` con `smu`: cero resultados)."

**Es falso, y el motivo del error está en la propia búsqueda**: el filtro exigía la
cadena `smu` en el nombre. El fichero se llama `polaris12_smc.bin`. **`smc` no es `smu`.**

Es exactamente la clase de error que vengo registrando: un filtro bien construido que
produce un cero, y un cero leído como ausencia. Un filtro de búsqueda que no encuentra
**no demuestra que no exista**: solo demuestra que el patrón no casa.

Y no es un fichero suelto: está versionado.

```
06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin
  130388 B   SHA256 4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77
  commit bee9f4b  "F4-R3: IA-1 entrega formato PM4 de GFX8, blob SMC y respuesta a IA-2"
  .gitignore con excepción acotada y razón escrita
  procedencia documentada en findings/008-firmware-blob.md:
    origen /usr/lib/firmware/amdgpu/polaris12_smc.bin.xz  (xz -dc)
```

Verifiqué el SHA256 yo mismo y coincide con el declarado. **Es el firmware real que
instala el sistema para esta placa.**

## 2. Su cabecera es aritméticamente autosuficiente

Con `struct common_firmware_header` (`amdgpu/amdgpu_ucode.h:30-41`):

| campo | valor | nota |
|---|---:|---|
| `size_bytes` | 130388 | **exactamente el tamaño del fichero** |
| `header_size_bytes` | 36 | |
| `header_version_major/minor` | 1 / 0 | |
| `ip_version_major/minor` | 7 / 2 | |
| `ucode_version` | 0x00221700 | |
| `ucode_size_bytes` | 130132 | 0x0001FC54 |
| `ucode_array_offset_bytes` | 256 | 0x00000100 |
| `crc32` | 0xAE2B3B78 | |
| `ucode_start_addr` | **0x00020000** | |

Dos comprobaciones que se sostienen solas:

```
ucode_array_offset_bytes + ucode_size_bytes = 256 + 130132 = 130388 = tamaño del fichero
ucode_start_addr = 0x00020000 = SMU7_FIRMWARE_HEADER_LOCATION
```

La segunda es la importante: **el propio firmware declara dónde se carga, y es
exactamente la constante que el driver usa para leer su cabecera** (`smu74.h:594`, y lo
mismo en `smu71`/`smu72`/`smu73`/`smu75`). Verificado por nombre exacto en las cinco
cabeceras: **las seis familias de SMU7 usan 0x20000**.

## 3. Y hay 220 bytes reservados donde el firmware escribe su tabla de punteros

Medida sobre el blob, la única región de ceros larga al principio es:

```
0x00023 .. 0x00100   221 B    (SMC 0x20023 .. 0x20100)
```

El payload arranca en `0x100`, que es **exactamente** `ucode_array_offset_bytes`. El hueco
reservado es `0x24 .. 0x100` = **220 bytes**.

Y aquí viene lo que importa: **todos los campos de estado de ejecución que el driver lee
caen dentro de ese hueco.** Con `struct SMU74_Firmware_Header` leída en SMC `0x20000`:

| campo | offset en el blob | valor en la imagen |
|---|---:|---:|
| `SoftRegisters` | 48 (0x30) | **0** |
| `DpmTable` | 52 (0x34) | **0** |
| `FanTable` | 56 (0x38) | **0** |
| `CacConfigTable` | 60 (0x3C) | **0** |
| `CacStatusTable` | 64 (0x40) | **0** |
| `mcRegisterTable` | 68 (0x44) | **0** |
| `mcArbDramTimingTable` | 72 (0x48) | **0** |
| `PmFuseTable` | 76 (0x4C) | **0** |

**Consecuencia, y es una clasificación mejor que `NOT_IN_CORPUS`:**

> `DpmTable` **no es una constante de la imagen**. Es **estado de ejecución** que el
> firmware escribe en esa región reservada cuando arranca.

Eso explica de una vez dos cosas:

1. Por qué el driver los lee **después** de arrancar el firmware y no antes
   (`smu7_request_smu_load_fw` en `:317`, y `process_firmware_header` más tarde).
2. Por qué **`108`/`218` no se pueden cerrar leyendo la imagen**: el valor que hace falta
   no está en el binario, porque **no existe como constante**. Es `NOT_AVAILABLE` con
   motivo, que es más preciso que `NOT_IN_CORPUS`.

Y explica también el `Digest[5]` de la cabecera: no es un digest, son los cinco primeros
dwords de la cabecera común. **La vista `SMU74_Firmware_Header` y la vista
`common_firmware_header` se solapan**, y eso es intencionado, no una confusión mía.

## 4. Y aquí queda resuelto el límite de la SRAM que `100` dejó abierto

`100` documentó una contradicción y no la pudo cerrar:

| constante | valor |
|---|---:|
| `SMC_RAM_END` (el límite que usa el driver) | 0x40000 = 262144 B |
| `POLARIS10_SMC_SIZE` (la SMC declarada) | 0x20000 = 131072 B |

Es decir, el driver comprobaba contra **el doble** de la SMC declarada. Mi conclusión
fue que el límite era demasiado amplio y que por eso la dirección 0 pasaba los checks.

**El firmware lo resuelve por testigo:**

```
firmware: base 0x20000 + 130388 B  ->  termina en 0x3FD54
SMC_RAM_END                          = 0x40000
margen                               = 684 B
```

**Si la SMC fueran 128 KiB, un firmware de 130388 B cargado en 0x20000 se saldría en
130388 B. No cabe.** La SMC es de 256 KiB, y `SMC_RAM_END = 0x40000` es el valor
**correcto**, no un límite demasiado amplio.

Además, el reparto queda limpio:

```
0x00000 .. 0x1FFFF   128 KiB   SRAM baja: las tablas que escribe el host
0x20000 .. 0x3FD54   130 KiB   firmware del SMC
```

Con la tabla DPM de 1884 B dentro de los 128 KiB bajos, quedan **129188 B** de holgura.

**Y esto corrige el tono de `100`:** la dirección 0 que "atraviesa los dos checks" no es
memoria no mapeada ni un hueco: es **SRAM real de la mitad baja, reservada a tablas**.
Que el check no la rechace no es un fallo del check; es que la dirección es válida.

## 5. La cadena del clock stretcher, cerrada en sus tres eslabones

De paso queda resuelto un hilo que empezó mirando los parches con máscara.

**El camino se ejecuta en mi ASIC.** Las tres condiciones de `smu7_hwmgr.c:1938-1940`:

```c
if ((hwmgr->pp_table_version != PP_TABLE_V0)
    && (hwmgr->feature_mask & PP_CLOCK_STRETCH_MASK)
    && (table_info->cac_dtp_table->usClockStretchAmount != 0))
        phm_cap_set(..., PHM_PlatformCaps_ClockStretcher);
```

1. `pp_table_version`: en `hwmgr_early_init` se pone `PP_TABLE_V1` por defecto
   (`hwmgr.c:86`). En `AMDGPU_FAMILY_VI`, `case CHIP_POLARIS12` **no** lo sobrescribe
   (`hwmgr.c:154-157`). Topaz y `AMDGPU_FAMILY_CI` sí pasan a `PP_TABLE_V0` (`hwmgr.c:63`
   y `:105`), y ahí el `&&` cortocircuita antes de desreferenciar.
   **Para Polaris12 queda `PP_TABLE_V1`.**
2. `feature_mask` viene de `adev->pm.pp_feature = amdgpu_pp_feature_mask`
   (`amd_powerplay.c:59`), cuyo valor por defecto es `0xfff7bfff` (`amdgpu_drv.c:202`).
   Decodificado: **`PP_CLOCK_STRETCH_MASK = 0x400` está activo**. Los tres `&= ~` de
   `amdgpu_device.c:2021-2027` solo aplican a SR-IOV VF, a SIENNA VF, o al PCIe dinámico:
   ninguno aplica a una dGPU de pantalla completa.
3. Luego **sí** se evalúa la tercera condición.

**Y mi hipótesis de desreferencia nula queda refutada.** `table_info` es
`(struct phm_ppt_v1_information *)hwmgr->pptable`, y `smu7_init_dpm_defaults` **no tiene
guarda de NULL** — mientras que otras funciones del mismo fichero **sí** la tienen
(`:879`, `:946`). Era el candidato a fallo. Pero la cadena de llamadas lo impide:

```c
/* hwmgr.c:249-256 */
ret = hwmgr->pptable_func->pptable_init(hwmgr);
if (ret)
        goto err;                                  /* aborta ANTES */
...
ret = hwmgr->hwmgr_func->backend_init(hwmgr);     /* = smu7_hwmgr_backend_init */
```

Y `smu7_init_dpm_defaults` se llama desde `smu7_hwmgr_backend_init` (`:3037`,
`.backend_init = &smu7_hwmgr_backend_init` en `:5858`). Además `pptable_init` solo
devuelve éxito tras `kzalloc_obj` + `PP_ASSERT_WITH_CODE((NULL != hwmgr->pptable), ...,
return -ENOMEM)`. **Si `backend_init` corre, `pptable` no es NULL.**

Un resultado negativo, y por eso lo escribo: la cadena entera se puede seguir de punta a
punta sin placa.

**Y el resto de la rama, que sí es una afirmación útil:** si la capacidad se activa,
`init_smc_table` falla **si y solo si** `usClockStretchAmount > 5`
(`polaris10_smumgr.c:1696` falla con `== 0 || > 5`, y la condición de activación ya
garantiza `!= 0`). El valor sale del PPT, que se lee del **VBIOS**, no de un fichero:
`/etc/powerplay/` **no existe en este sistema**, y `process_pptables_v1_0.c:1308` lo
toma con `get_powerplay_table(hwmgr)`.

## 6. NEGATIVE_RESULT: en esta máquina no hay desensamblador GCN que funcione

Estuve a punto de leer el firmware. **No se puede**, y conviene que conste por qué, para
que nadie vuelva a intentarlo:

| herramienta | resultado medido |
|---|---|
| `llvm-objdump --triple=amdgcn` | registra el target `amdgcn`, pero al desensamblar: **`LLVM ERROR: disassembly not yet supported for subtarget`** |
| `llvm-objcopy -I binary -O elf64-...` | crea el ELF bien, pero `llvm-objdump` no lo desensambla |
| `radare2` / `rizin` | **ninguna** arquitectura GCN/MISA en su lista |
| `strings` | 67 cadenas, **todas basura**: el firmware no tiene tabla de cadenas |
| `llvm-mc --disassemble --hex` | desensambla, pero **no es fiable** |

**`llvm-mc --disassemble --hex` produce basura con apariencia de respuesta.** Medido:

- no expone límites de instrucción: alimentado con 11 palabras devuelve 9 líneas, con 2
  palabras devuelve 1, con 1 palabra devuelve 1. Palabra a palabra da `v_cndmask` donde
  el ensamblador dice `v_mov_b32_e32`, y para otras entradas responde literalmente
  **`PLEASE submit a bug report to https://github.com/llv...`**

Escribí una herramienta alrededor, la validé con un round-trip real (9 instrucciones
ensambladas -> 9 desensambladas, equivalentes y en orden, que **sí** pasó), y al
aplicarla al blob **el modo exacto falló en 11 de 22 pruebas** porque el desensamblador no
respeta los límites. **La he eliminado en vez de dejarla**: una herramienta que
desensambla con seguridad y sin avisar es peor que no tener ninguna.

Un decodificador GCN correcto es trabajo de proyecto, no de iteración, y sin verdad de
terreno no se puede validar. **La vía barata que queda es la de la estructura del blob**,
que es la de las secciones 2 a 4, y ya ha producido más que el desensamblado habría
producido.

## Clasificación

- `FIRMWARE_BLOB_IN_CORPUS = PROVEN`: `06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin`,
  130388 B, SHA256 `4b8eb326...`, commit `bee9f4b`, procedencia
  `/usr/lib/firmware/amdgpu/polaris12_smc.bin.xz`. **REFUTA** mi "firmware ausente".
- `MY_SEARCH_FILTER_CAUSED_A_FALSE_ABSENCE = PROVEN`: el filtro exigía `smu`; el fichero
  se llama `smc`. Un filtro que no encuentra no demuestra que no exista.
- `FIRMWARE_HEADER_IS_SELF_CONSISTENT = PROVEN`: 256 + 130132 = 130388 = tamaño; y
  `ucode_start_addr = 0x20000 = SMU7_FIRMWARE_HEADER_LOCATION`, coincidente en las seis
  cabeceras de SMU7.
- `FIRMWARE_RESERVED_GAP_IS_220_BYTES = PROVEN`: región cero `0x24..0x100`, que termina
  exactamente en `ucode_array_offset_bytes`.
- `SMU74_RUNTIME_FIELDS_LIVE_IN_RESERVED_GAP = PROVEN`: `SoftRegisters`@48 a
  `PmFuseTable`@76 caen todos en `0x24..0x100`, y están a cero en la imagen.
- `DPM_TABLE_IS_RUNTIME_STATE_NOT_AN_IMAGE_CONSTANT = PROVEN_DERIVED`: por lo anterior.
  **Clasifica mejor que `NOT_IN_CORPUS`**: el valor no existe como constante.
- `SMC_IS_256_KIB_NOT_128 = PROVEN_DERIVED`: el firmware de 130388 B cargado en 0x20000
  termina en 0x3FD54 y **no cabe** en 128 KiB. **`SMC_RAM_END = 0x40000` es correcto** y
  `POLARIS10_SMC_SIZE = 0x20000` se queda corto. **Cierra la pregunta abierta de `100`.**
- `ADDRESS_ZERO_IS_LOW_SMC_TABLE_RAM = PROVEN_DERIVED`: los 128 KiB bajos son SRAM de
  tablas; la dirección 0 es una dirección válida, no un hueco. **Corrige el tono de `100`.**
- `CLOCK_STRETCH_PATH_EXECUTES_ON_POLARIS12 = PROVEN`: `PP_TABLE_V1` +
  `PP_CLOCK_STRETCH_MASK` activo en `0xfff7bfff`, y ninguno de los tres `&= ~` aplica.
- `CLOCK_STRETCH_NULL_DEREF_HYPOTHESIS = REFUTED`: `pptable_init` debe tener éxito antes
  de `backend_init`, y exige `pptable != NULL`.
- `CLOCK_STRETCH_INIT_FAILS_IFF_STRETCH_GT_5 = PROVEN_DERIVED`: la activación ya
  garantiza `!= 0`, y la función falla con `== 0 || > 5`.
- `PPT_COMES_FROM_VBIOS_NOT_A_FILE = PROVEN`: `/etc/powerplay/` no existe;
  `process_pptables_v1_0.c:1308` usa `get_powerplay_table(hwmgr)`.
- `GCN_DISASSEMBLER_AVAILABLE = PROVEN_ABSENT`: medido en cuatro herramientas.
- `LLVM_MC_HEX_MODE_IS_NOT_A_DECODER = TOOL_BROKEN`: round-trip correcto pero modo exacto
  falla 11 de 22 sobre el blob.

## Discriminantes que quedan abiertos

```
PENDIENTE=DPM-BASE-EN-SMC | HALLAZGO=113-dpm-table-start-es-la-base-literal-y-los-once-usos-son-correctos.md
             | ESTADO=NOT_AVAILABLE
             | NECESITA=el VALOR de SMU74_Firmware_Header.DpmTable en ejecucion
             | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

`NOT_AVAILABLE` y no `NOT_DETERMINED`: el valor no es una constante del firmware que falte
leer, **es estado de ejecución que hay que observar**. No hay lectura estática que lo dé.
Solo dos vías: instrumentar el driver para leerlo tras `smu7_request_smu_load_fw`
(NIVEL 1, parche propio, sin tocar el kernel en ejecución), o instrumentar la SRAM
(NIVEL 3).

Y añade una segunda, más barata, que es la que de verdad importa:

```
PENDIENTE=US-CLOCK-STRETCH-AMOUNT | HALLAZGO=115-firmware-smc-si-en-el-corpus.md
             | ESTADO=NOT_IN_CORPUS
             | NECESITA=el campo usClockStretchAmount de la tabla CAC_DTP del VBIOS
             | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

## Lo que esto obliga a hacer en un driver propio

1. **No copies `POLARIS10_SMC_SIZE`.** Es la mitad del límite real. Si mi driver valida
   contra 128 KiB, **rechaza su propio firmware**, porque el firmware que el host carga
   en 0x20000 no cabe. El límite correcto es 0x40000 y sale del **tamaño real de la
   imagen**, no de un `#define`.
2. **La región reservada del firmware es un contrato.** Son 220 bytes en
   `SMC 0x20024..0x20100`, y ahí es donde el firmware deja su tabla de punteros. Un
   driver propio tiene que respetarla: escribir en ella es escribir sobre el estado de
   ejecución del firmware.
3. Y la regla general de este hallazgo, que es la que más me costó: **una búsqueda con
   filtro que devuelve cero es un resultado sobre el filtro, no sobre el objeto.**
   Debí escribir `find -iname '*smc*' -o -iname '*smu*'` desde el principio.