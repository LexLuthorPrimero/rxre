# 256 · ASIC_InternalSS_Info: mi VBIOS declara spread spectrum de memoria y motor, y el camino que lo activa SI se ejecuta en mi ASIC

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Cierre de una lectura pendiente
>
> Mi anotacion anterior decia "ASIC_InternalSS_Info declarado presente, solo
> cabecera de 4 bytes leida". Era incompleta y **subestimaba la relevancia**:
> la tabla tiene un consumidor vivo dentro de `smu7_hwmgr`, y de ahi sale una
> escritura al SMC. Este hallazgo lee la tabla entera y reconstruye la cadena.

## Que pregunte y por que ahora

Mi VBIOS declara `ASIC_InternalSS_Info` en `0xa824` y yo solo habia leido sus
cuatro primeros bytes. Era el ultimo bloque de **corpus primario sin leer**, y
la via estatica tiene discriminante fuerte a coste cero: es un fichero de
58 880 bytes que ya tengo, y ningun hardware se toca.

## La tabla, medida

Fuente: `revkit/capturas/amdgpu_vbios.txt`, 58 880 B. Offset `0xa824` = 43 044,
dentro de rango. Extraccion con `od -A x -t x1z -j 43044 -N 64`.

```
0xa824   28 00 03 01                          <- cabecera
0xa828   ff ff ff 00 | 7d 00 | b8 0b | 01 | 00 | 00 00
0xa834   ff ff ff 00 | 32 00 | 4e 0c | 02 | 00 | 00 00
0xa840   ff ff ff 00 | 7c 01 | 4e 0c | 07 | 12 | 00 00
0xa84c   57 00 02 03  ...                     <- cabecera de la tabla SIGUIENTE
```

`ATOM_COMMON_TABLE_HEADER` son 4 bytes: `usStructureSize = 0x0028 = 40`,
`ucFormatRevision = 3`, `ucContentRevision = 1`. Luego **V3**, no V1 ni V2, y por
eso toca `ATOM_ASIC_SS_ASSIGNMENT_V3` (`atombios.h:6701`), de 12 bytes:
`ulTargetClockRange`(4) + `usSpreadSpectrumPercentage`(2) +
`usSpreadRateIn10Hz`(2) + `ucClockIndication`(1) + `ucSpreadSpectrumMode`(1) +
`ucReserved[2]`(2).

**Verificacion cruzada del limite, no una suposicion:** `4 + 3*12 = 40` coincide
con `usStructureSize`, y `0xa824 + 40 = 0xa84c`, donde empieza `57 00 02 03`, que
es una cabecera valida de la tabla siguiente. El tamaño declarado cae exacto en
la frontera real.

## Los tres registros

`ucClockIndication` lo resuelve el propio header, que lo documenta de forma
explicita (`atombios.h:6642-6652`, "SW uses the IDs below to search if the SS is
required/enabled on a clock branch"):

| # | off | `ulTargetClockRange` | `usSpreadSpectrumPercentage` | `usSpreadRateIn10Hz` | `ucClockIndication` | `ucSpreadSpectrumMode` |
|---|-----|----------------------|------------------------------|----------------------|--------------------|------------------------|
| 0 | `0xa828` | `0x00FFFFFF` | 125 -> **1.25 %** | 3000 -> **30 kHz** | 1 = `ASIC_INTERNAL_MEMORY_SS` | `0x00` |
| 1 | `0xa834` | `0x00FFFFFF` | 50 -> **0.50 %** | 3150 -> **31.5 kHz** | 2 = `ASIC_INTERNAL_ENGINE_SS` | `0x00` |
| 2 | `0xa840` | `0x00FFFFFF` | 380 -> **0.38 %** | 3150 -> **31.5 kHz** | 7 = `ASIC_INTERNAL_SS_ON_DP` | `0x12` |

`ulTargetClockRange = 0x00FFFFFF` es centinela: ningun limite superior.

Las unidades salen del comentario del **campo**, no del nombre:
`usSpreadSpectrumPercentage` esta "in unit of 0.01%", y `ucSpreadSpectrumMode`
bit4 (`SS_MODE_V3_PERCENTAGE_DIV_BY_1000_MASK = 0x10`) lo cambia a 0.001%. Los
registros 0 y 1 tienen modo `0x00`, luego van en centesimas; el registro 2 tiene
`0x12 = 0b10010`, luego bit1 = `SS_MODE_V3_EXTERNAL_SS_MASK` y bit4 activos:
**SS externo** y porcentaje en milesimas.

Estado de esta tabla: **`PROVEN` (medido)** para contenido y tamano.
`PROVEN` para el significado de `ucClockIndication` (esta en el header de este
mismo arbol, no en un comentario de terceros).

## La cadena, y si se ejecuta en mi ASIC

Este es el punto que obliga a preguntarse "¿este camino corre en mi placa?" antes
de publicar nada. La cadena entera:

```
polaris_set_asic_special_caps()          hwmgr.c:483
   :492-495   phm_cap_set  Memory... + Engine...        <- INCONDICIONAL
        |
        v
smu7_init_dpm_defaults()                smu7_hwmgr.c:1803
   :1968      if (!atomctrl_is_asic_internal_ss_supported) unset ambos
              -> ppatomctrl.c:829   return table != NULL
              -> mi VBIOS TIENE la tabla, luego los caps QUEDAN ACTIVOS
        |
        v
smu7_enable_dpm_tasks()                 smu7_hwmgr.c:1566
   :1584-1587 cap Engine... => SMC GENERAL_PWRMGT.DYN_SPREAD_SPECTRUM_EN = 1
        |
        v
smu7_disable_dpm_tasks()                smu7_hwmgr.c:1738
   :1759-1762 INCONDICIONAL: CG_SPLL_SPREAD_SPECTRUM.SSEN = 0
                                 GENERAL_PWRMGT.DYN_SPREAD_SPECTRUM_EN = 0
```

`atomctrl_is_asic_internal_ss_supported()` lo he leido entero (`ppatomctrl.c:824-833`)
y es `table != NULL`, sin mirar contenido. Los caps los pone `polaris_set_asic_special_caps`,
que es el handler de **POLARIS12**, y smu7 solo los borra si falta la tabla. Como
la tabla existe, **la escritura al SMC ocurre**. Estado: **`PROVEN`**.

`polaris_set_asic_special_caps` esta leida **completa**, de `:483` a `:514`: 32
lineas, dos menciones de `SpreadSpectrum` y **ningun `unset`**. La primera lectura
me habia dejado en `:500`, o sea a mitad, y eso no basta para afirmar
"incondicional". Como segunda comprobacion, el bloque `:500-501` de esa misma
funcion discrimina `hwmgr->chip_id == CHIP_POLARIS12` de forma explicita: mi ASIC
esta nombrado alli, lo que confirma la ruta otra vez por una via independiente.

**La asimetria es el contenido de diseño real:** el *disable* es incondicional y
el *enable* esta condicionado por capacidad. Un driver especializado que limpie
`DYN_SPREAD_SPECTRUM_EN` debe volver a programarlo en su camino de enable, o el
spread spectrum se queda apagado el resto de la sesion y la placa se comporta de
otra manera respecto a la referencia. Que eso rendia mas o menos es
`NOT_DETERMINED`; que la asimetria existe, no.

## Un defecto de granularidad, con el matiz que le toca

El test de soporte es **binario sobre la existencia de la tabla**, nunca sobre su
contenido: `asic_internal_ss_get_ss_asignment()` (`ppatomctrl.c:838`) es quien
busca por `ucClockIndication`, y **`smu7_init_dpm_defaults` no la llama**. Un
VBIOS con una sola entrada DP pondria los dos caps sin declarar ni memoria ni
motor.

En mi placa el test grueso acierta **por suerte del contenido, no por diseno**:
las entradas 1 (MEMORY_SS) y 2 (ENGINE_SS) existen. Asi que el defecto es
`PROVEN` como propiedad del codigo y **`NOT_OBSERVED` en este ASIC**.

## Los datos que amdgpu nunca lee en mi ASIC

`atomctrl_get_engine_clock_spread_spectrum` la llaman `ci_smumgr.c:345`,
`fiji_smumgr.c:903`, `tonga_smumgr.c:586`, `iceland_smumgr.c:843`.
`atomctrl_get_memory_clock_spread_spectrum` la llaman `ci_smumgr.c:1085`,
`tonga_smumgr.c:879`, `iceland_smumgr.c:1127`.

**Ninguna de las dos la llama `polaris10_smumgr.c`** (mi ruta viva, `chip_id = 17`),
y `grep -niE "spread|spectrum" polaris10_smumgr.c` no devuelve nada. `smu7_hwmgr.c`
solo usa el bit de capacidad, jamas los valores.

Consecuencia: el hardware recibe "spread spectrum dinamico activado" y **amdgpu
nunca le entrega la magnitud ni la frecuencia** que mi VBIOS declara. De donde
salen los parametros reales es `NOT_DETERMINED`: o el SMC lee la tabla por su
cuenta, o hay valores por defecto de hardware. No lo he determinado.

## El discriminante que casi me hace publicar una contradiccion

Inmediatamente despues del test de SS, `smu7_hwmgr.c:1975-1984`:

```c
if ((adev->pdev->device == 0x699F) && (adev->pdev->revision == 0xCF))
        phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
```

`file(1)` sobre mi ROM declara `PCI AMD/ATI device=0x699f`. Si mi placa cumpliera
ademas `revision == 0xCF`, el ClockStretcher quedaria desactivado por aqui y el
hallazgo `132` (ClockStretcher medido VIVO) se caeria.

**El discriminante es la revision, y `0xC7` no es `0xCF`: difieren en un bit.**
La unica fuente que tengo de la revision es `revkit/obs.py:37`, que transcribe
una linea de dmesg: `POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7`.

Grado de esa evidencia, sin subirla de nivel: el **device ID** esta `PROVEN` por
dos soportes independientes (`file(1)` sobre el ROM, y ese mismo script). La
**revision** es `PROVEN_DERIVED` por portador secundario: **ninguna captura
primaria del proyecto la contiene** (`state.txt`, `amdgpu_pm_info.txt`,
`amdgpu_gem_info.txt`, `amdgpu_firmware_info.txt` no llevan device ni revision).
No lo presento como medido.

Resultado: la condicion es falsa en mi placa, el ClockStretcher **no** se
desactiva por ese path, y `132` sigue en pie. Sin ese discriminante, un fallo de
un bit en la transcripcion habria publicado una contradiccion falsa.

## UNIT_MISMATCH queevi por mirar antes de publicar

El campo de 2 bytes tiene **dos unidades distintas** segun la version del struct:

- V1 `ATOM_ASIC_SS_ASSIGNMENT`: `usSpreadRateInKhz`, en kHz.
- V3 `ATOM_ASIC_SS_ASSIGNMENT_V3`: `usSpreadRateIn10Hz`, en unidades de 10 Hz.

Mismo offset, mismos 2 bytes, factor 100 de diferencia. Haber leido solo el
comentario de V1 me habria hecho escribir "3150 kHz = 3,15 MHz de modulacion",
que es absurdo; el comentario de V3 da 31,5 kHz, que es sensato.

El recorrido de `asic_internal_ss_get_ss_asignment` tipa el puntero como V1
**siempre**, sin pedir `crev`, pero ambos structs miden 12 bytes, asi que el
avance es seguro en memoria. Y el driver **si** corrige la unidad
(`ppatomctrl.c:873-877`): `speed_spectrum_rate /= 100` cuando major es 3, o
cuando major 2 con minor >= 2. Para mi V3.1 eso da 3150 -> 31 kHz.

Residuo real, y **no es un fallo funcional**: el campo vale 3150 en unidades de
10 Hz, que son 31,5 kHz exactos, y la division entera entrega **31**. Se pierden
0,5 kHz, un 1,6 % relativo. El registro 0 (3000) cae exacto en 30. Lo dejo como
`PROVEN` de perdida de precision, no como bug.

## Lo que NO afirmo

- **NO** afirmo que el spread spectrum este programado en mi silicio en este
  momento. La tabla dice que el VBIOS lo *especifica*; que se programe y con que
  valores es `NOT_DETERMINED`.
- **NO** afirmo que los 300/625 MHz de MCLK medidos esten afectados.
- **NO** afirmo un defecto observable en esta placa. El defecto de granularidad
  es `NOT_OBSERVED` aqui.
- **NO** he ejecutado runtime. `B_RUNTIME = NOT_EXECUTED`. No hay medicion, y todo
  lo de este documento es lectura de corpus mas derivacion.
- `ixCG_SPLL_SPREAD_SPECTRUM` sigue **sin declararse** en las cabeceras de mi
  corpus, igual que `ixPWR_CKS_CNTL`. El registro se escribe por
  `PHM_WRITE_INDIRECT_FIELD`, asi que el valor numerico no lo puedo resolver
  aqui: `SEMANTIC_MISSING`.

## Tool y reproducibilidad

Sin herramienta nueva. Extraccion con `od`, busquedas con `grep` acotadas, y
cruce de struct contra la cabecera del **mismo** arbol. Reproducible con los
mismos comandos sobre el mismo fichero.

## Frontera siguiente

La procedencia de los parametros reales de modulacion: si el SMC lee la tabla
`ASIC_InternalSS_Info` por su cuenta, debe existir un lector en el firmware, que
no tengo. Discriminante barato: buscar el offset `0xa824` o la firma de la tabla
en el firmware SMC del corpus. Es `RUNTIME_MISSING` con lo que hay, no ausente.