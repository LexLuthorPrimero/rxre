# 100 · El límite de la SRAM del SMC es el doble de la SRAM que el propio driver declara

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> **RESUELTO POR `115-firmware-smc-si-en-el-corpus.md`.**
>
> Este documento decia (`:172`): *"Las dos lecturas son `NOT_DETERMINED` sin el hardware
> **o el firmware**"*. El firmware estaba en el corpus y aporta el testigo:
>
> ```
> firmware real:  base 0x20000 + 130388 B  ->  termina en 0x3FD54
> SMC_RAM_END                           = 0x40000     margen 684 B
> ```
>
> **Si la SMC fueran 128 KiB, el firmware que el host carga en 0x20000 no cabria.**
> La SMC es de **256 KiB**. Se **CONFIRMA** `SMC_SIZE_CONSTANTS_CONFLICT = PROVEN`, y se
> **cierran** los dos `NOT_DETERMINED`:
>
> - `SMC_IS_256_KIB = PROVEN_DERIVED`. `SMC_RAM_END = 0x40000` es el valor **correcto**;
>   `POLARIS10_SMC_SIZE = 0x20000` se queda corto y no protege nada.
> - Reparto: `0x00000..0x1FFFF` = 128 KiB de tablas del host; `0x20000..0x3FD54` = el
>   firmware. Con la tabla DPM de 1884 B, quedan **129188 B** de holgura abajo.
>
> **Y se corrige el tono del hallazgo**: la direccion 0 que "atraviesa los dos checks" no
> es memoria no mapeada ni un hueco, es **SRAM real de la mitad baja reservada a tablas**.
> Que el check no la rechace no es un fallo del check: la direccion es valida.

## El hallazgo en una frase

El driver declara que la SRAM del SMC de Polaris12 mide **128 KiB**
(`POLARIS10_SMC_SIZE 0x20000`, `polaris10_smumgr.c:55`) y despues **pasa `limit =
0x40000`, 256 KiB**, en todas las copias. La comprobacion de rango acepta, por tanto,
el doble de lo que existe.

Y no es una incoherencia menor: **la cabecera del firmware vive exactamente en
`0x20000`**, la frontera de la SMC real. O sea que las direcciones que salen de la
cabecera estan, por construccion, en la zona que el limite declara valida y que el
tamano declarado dice que no existe.

## Los dos numeros, verificados

```
polaris10_smumgr.c:55   #define POLARIS10_SMC_SIZE 0x20000   <- 128 KiB
smu7_smumgr.c:36        #define SMU7_SMC_SIZE        0x20000   <- 128 KiB, lo mismo
smu74.h:594             #define SMU7_FIRMWARE_HEADER_LOCATION 0x20000
polaris10_smumgr.h:33   #define SMC_RAM_END         0x40000   <- 256 KiB, lo que se PASA
smu7_smumgr.h:30        #define SMC_RAM_END         0x40000   <- idem
```

Que ambos ficheros del driver declaren 0x20000 como el tamano de la SMC, y que todas las
llamadas pasen 0x40000 como limite, significa que la incoherencia esta dentro del propio
driver: **no es un parametro que venga de fuera mal puesto, es una constante que el
fichero de sizes y la de limites contradicen.**

`SMC_RAM_END` vale 0x40000 en los cinco ficheros que lo definen: `ci_smumgr.c:63`,
`vegam_smumgr.h:32`, `smu7_smumgr.h:30`, `polaris10_smumgr.h:33`, `smu10_hwmgr.c:46`.
Es un valor heredado de una generacion con SRAM mayor, copiado sin revisar.

## La comprobacion es real, pero no protege lo que dice proteger

`smu7_smumgr.c:58-59`, en `smu7_copy_bytes_to_smc`:

```c
PP_ASSERT_WITH_CODE((0 == (3 & smc_start_address)),
        "SMC address must be 4 byte aligned.", return -EINVAL);

PP_ASSERT_WITH_CODE((limit > (smc_start_address + byte_count)),
        "SMC address is beyond the SMC RAM area.", return -EINVAL);
```

Tres cosas, todas verificadas:

**1. La comprobacion no es decorativa.** `PP_ASSERT_WITH_CODE` (`pp_debug.h:37-43`) es
`do { if (!(cond)) { pr_warn_ratelimited(...); code; } } while (0)`, **sin ninguna guarda
de compilacion**. No se desactiva en release. Devuelve `-EINVAL` de verdad.

**2. `limit` es un parametro libre, no un tope del hardware.** No hay ninguna constante
interna que lo imponga. La prueba de que el autor lo trata como un valor arbitrario es
`smu7_program_jump_on_start` (`:115-122`), que pasa `sizeof(data)+1`, o sea **5**, como
limite. Cada llamada elige el suyo.

**3. El valor 0 atraviesa los dos checks.** Con `smc_start_address = 0`:
`3 & 0 == 0` (pasa el de alineacion) y `0x40000 > 0 + 1776` (pasa el de rango). Y se
ejecuta la copia.

Que la direccion 0 sea el vector de arranque del SMC lo dice el propio driver:
`smu7_program_jump_on_start` (`:115-122`) escribe ahi los 4 bytes `E0 00 80 40` en modo
no protegido. **Un destino a cero no da un error: da una escritura sobre el punto de
entrada del firmware del SMC.**

## Y hay un agujero mas: desbordamiento de entero

`smc_start_address + byte_count` es aritmetica `uint32_t` sin proteccion. Con
`addr = 0xFFFFF000` y `byte_count = 0x2000`:

```
addr + byte_count = 0xFFFFF000 + 0x2000 = 0x1000     (desborda)
0x40000 > 0x1000  ->  PASA
```

El check de rango se salva solo. Y el check por DWORD de `smu7_set_smc_sram_address`
(`:41`, `limit > (smc_addr + 3)`) tiene **el mismo** problema, con solo 3 bytes de suma.

Que un valor asi sea alcanzable depende de lo que devuelva la cabecera del firmware:
`RUNTIME_MISSING`. Que la comprobacion falle exactamente por donde deberia
detenerlo: `PROVEN`.

## La cadena que convierte esto en alcanzable: un fallo de lectura no detiene nada

Esta es la parte que verifiqué de punta a punta, porque sin ella lo anterior seria un
defecto teorico.

**Paso 1.** `smu7_read_smc_sram_dword` (`:235`):

```c
*value = result ? 0 : cgs_read_register(hwmgr->device, mmSMC_IND_DATA_11);
```

Si la lectura falla, **el valor de salida es 0**, no el contenido de la variable anterior.

**Paso 2.** La lectura de `dpm_table_start` (`polaris10_smumgr.c:2500-2507`):

```c
result = smu7_read_smc_sram_dword(hwmgr,
                SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, DpmTable),
                &tmp, SMC_RAM_END);

if (0 == result)
        smu_data->smu7_data.dpm_table_start = tmp;      /* solo si la lectura fue bien */

error |= (0 != result);
```

Asi que si la lectura falla, `dpm_table_start` **conserva su valor anterior**, que tras
`kzalloc_obj` (`:339`) es **0**. Y el error **se acumula** en `error`.

**Paso 3.** Ese error, al volver, **no detiene la inicializacion**
(`smu7_hwmgr.c:1607-1609`):

```c
tmp_result = smum_process_firmware_header(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result),
        "Failed to process firmware header!", result = tmp_result);
```

El tercer argumento del macro es `result = tmp_result`: **anota el error en una variable y
sigue**. No es `return`. Y cinco lineas mas abajo:

```c
result = smu7_setup_default_dpm_tables(hwmgr);          /* :1618 */
...
tmp_result = smum_init_smc_table(hwmgr);                /* :1622 */
```

`smum_init_smc_table` es `polaris10_init_smc_table`, que en `:2118-2123` copia **1776
bytes** a `dpm_table_start`.

**Resultado: con la cabecera del firmware ilegible, el driver anota el error, sigue
adelante, y escribe 1776 bytes en la direccion 0 de la SRAM del SMC.** Los dos checks de
`:58-59` pasan. Y la direccion 0 es el punto de entrada del firmware.

Ese es el recorrido completo: lectura fallida -> 0 -> error anotado -> flujo continua ->
1776 bytes en la direccion 0 -> los checks pasan.

## El patron de fondo: los limites se validan mal y en un solo sitio

De las cuatro direcciones que salen de la cabecera del firmware, **solo una tiene guarda
de cero**:

| destino | lee de la cabecera | guarda `== 0` |
|---|---|---|
| `dpm_table_start` | `:2500-2507` | **no** |
| `arb_table_start` | `:2511-2516` | **no** |
| `pm_fuse_table_offset` | `:611-614` | **no** |
| `fan_table_start` | `:2530-2536` | **si**, `:2184` |

Verificado por busqueda de `_start == 0` y `pm_fuse_table_offset == 0` en
`polaris10_smumgr.c`: un unico resultado, la linea 2184.

Y hay una incoherencia interna mas, en la misma familia: la lectura de `mcRegisterTable`
(`:2522-2528`) **no acumula el error**, a diferencia de las otras cinco, que si lo hacen
(`:2508`, `:2520`, `:2538`, `:2548`, `:2558`). Un fallo de ahi es invisible. Hoy es
inerte porque esa tabla no se copia nunca, lo cual es en si mismo otro hallazgo
(`CONNECTION_MISSING`): Tonga si la sube (`tonga_smumgr.c:2154-2202`) y Polaris12 no.

## Lo que NO dice

No dice que esto ocurra en esta placa. Necesito saber si la lectura de la cabecera
tiene exito, que es lo normal. Que el driver **no compruebe** es `PROVEN`; que se dispare
es `RUNTIME_MISSING`.

No digo que la SMC real mida 128 KiB. Digo que **el propio driver lo declara asi** en dos
ficheros. Si la SMC real fuera de 256 KiB, entonces el `0x20000` de
`POLARIS10_SMC_SIZE` es el que estaria mal, y el hallazgo se convierte en "la constante
del tamano no se usa para nada". **Las dos lecturas son `NOT_DETERMINED` sin el hardware
o el firmware.** Lo que si es `PROVEN` es que las dos constantes **no coinciden** y que
solo una de las dos protege algo.

No hay lectura de hardware aqui, no hay escritura, no hay `/sys`, no hay modulos.

## Clasificacion

- `SMC_SIZE_CONSTANTS_CONFLICT = PROVEN`: `0x20000` declarado en dos ficheros frente a
  `0x40000` pasado en todos. No es un parametro externo: son dos constantes del driver.
- `SMC_LIMIT_DOUBLES_DECLARED_SIZE = PROVEN_DERIVED`: el rango `0x20000..0x3FFFF` pasa el
  check y queda fuera de la SMC que el driver declara.
- `SMC_HEADER_LIVES_AT_SIZE_BOUNDARY = PROVEN`: `SMU7_FIRMWARE_HEADER_LOCATION = 0x20000`
  coincide exactamente con `POLARIS10_SMC_SIZE`. Las direcciones de la cabecera estan en la
  zona que el limite valida y el tamano niega.
- `SMC_COPY_CHECKS_ARE_REAL = PROVEN`: `pp_debug.h:37-43` sin guarda de compilacion, con
  `return -EINVAL`.
- `SMC_LIMIT_IS_A_FREE_PARAMETER = PROVEN`: `smu7_program_jump_on_start` (`:119`) pasa 5
  como limite. No hay tope interno.
- `SMC_ADDRESS_ZERO_PASSES_BOTH_CHECKS = PROVEN_DERIVED`: `3 & 0 == 0` y
  `0x40000 > 0 + byte_count`.
- `SMC_ADDRESS_ZERO_IS_FIRMWARE_ENTRY = PROVEN`: `smu7_program_jump_on_start` (`:115-122`)
  escribe el vector de arranque ahi.
- `SMC_RANGE_CHECK_OVERFLOWS = PROVEN_DERIVED`: `0xFFFFF000 + 0x2000 = 0x1000`, y
  `0x40000 > 0x1000` pasa. El check por DWORD de `:41` tiene el mismo fallo.
- `SMC_READ_FAILURE_YIELDS_ZERO = PROVEN`: `smu7_smumgr.c:235`.
- `SMC_DPM_START_UNGUARDED = PROVEN_ABSENT`: sin guarda de cero; `fan_table_start` si la
  tiene (`:2184`), y es la unica.
- `SMC_FW_HEADER_ERROR_DOES_NOT_STOP_INIT = PROVEN`: `smu7_hwmgr.c:1609` es
  `result = tmp_result`, no `return`; seguido de `:1618` y `:1622`.
- `SMC_FULL_CHAIN_REACHABLE = PROVEN_DERIVED` la cadena, `RUNTIME_MISSING` si la lectura
  de la cabecera falla en esta placa.
- `SMC_MC_REG_TABLE_READ_ERROR_DROPPED = PROVEN`: `:2522-2528` sin `error |=`, frente a
  las otras cinco que si.
- `SMC_MC_REG_TABLE_NEVER_UPLOADED = PROVEN` el hecho, `CONNECTION_MISSING` si es decision
  o olvido. Tonga si lo hace (`tonga_smumgr.c:2154-2202`).

## Lo que esto obliga a hacer en un driver propio

Cuatro cosas, todas de una linea cada una:

1. **Usar un unico limite, derivado del tamano real de la SRAM, no una constante
   heredada.** Si el limite no coincide con el tamano, uno de los dos miente, y el que
   miente es el que protege.
2. **Rechazar el destino 0 de forma explicita** en toda copia a la SRAM. El 0 es una
   direccion valida para el check de rango y es el vector de arranque: no puede pasar.
3. **Comprobar la suma sin desbordar**: `byte_count > limit - addr` en vez de
   `addr + byte_count > limit`, que es la forma que desborda.
4. **Propagar el fallo de lectura de la cabecera antes de usar el destino**, no anotarlo y
   seguir. La cadena de `:1609` a `:1622` es exactamente el patron a no copiar.
