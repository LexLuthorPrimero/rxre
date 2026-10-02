# 086 · `usec_timeout` del handshake SMC: 1000000 iteraciones, constante, y tres timeouts distintos en el arbol

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

Cierra el pendiente `usec_timeout`: donde se inicializa y que promise exactamente.

## El valor

`hwmgr->usec_timeout` se inicializa en **un** sitio:

`pm/powerplay/hwmgr/hwmgr.c:85`

```c
hwmgr->usec_timeout = AMD_MAX_USEC_TIMEOUT;
```

`AMD_MAX_USEC_TIMEOUT` esta en `drivers/gpu/drm/amd/include/amd_shared.h:30`:

```c
#define AMD_MAX_USEC_TIMEOUT        1000000  /* 1000 ms */
```

**No se sobreescribe nunca.** Unico sitio de asignacion en todo el subarbol `pm/powerplay`: el de la
linea 85. No hay variante por ASIC, no hay ajuste por reloj, no hay ruta que lo cambie
para Polaris12 ni para nada. Es 1 segundo para todos los ASIC que pasan por powerplay.

La primera busqueda lo dio por ausente porque el grep limitaba `*.h` al subarbol
`pm/powerplay` y `amd_shared.h` vive en `drivers/gpu/drm/amd/include/`, fuera. Un nombre
no encontrado por donde se ha buscado no es un nombre ausente.

## Que promete el bucle

`phm_wait_on_register`, `pm/powerplay/hwmgr/smu_helper.c:110-132`:

```c
for (i = 0; i < hwmgr->usec_timeout; i++) {
        cur_value = cgs_read_register(hwmgr->device, index);
        if ((cur_value & mask) == (value & mask))
                break;
        udelay(1);
}
/* timeout means wrong logic*/
if (i == hwmgr->usec_timeout)
        return -1;
```

Cuenta **iteraciones**, no tiempo transcurrido. Cada vuelta es una lectura de registro
mas un `udelay(1)`, luego el tiempo real de pared es

```
1000000 x (coste de cgs_read_register + 1 microsegundo)  >=  1 segundo
```

El limite es un cota inferior, no un techo. Un driver propio que copie esto hereda un
timeout que en hardware lento puede ser bastante mas de un segundo. Si lo que se quiere
es un timeout de reloj, hay que medirlo con el reloj, no contar vueltas.

## La cadena del handshake SMC

`smu7_smumgr.c:135-155`, que es el protocolo ya descrito en el scope de SMC:

```c
PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);   /* espera a Resp==0 */
cgs_write_register(hwmgr->device, mmSMC_RESP_0, 0);
cgs_write_register(hwmgr->device, mmSMC_MESSAGE_0, msg);
PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, SMC_RESP, 0);   /* espera a Resp!=0 */
ret = PHM_READ_FIELD(hwmgr->device, SMC_RESP_0, SMC_RESP);
```

Las dos esperas van por `phm_wait_for_register_unequal` (`smu_helper.c:155`). La cadena
de macros, de arriba abajo:

```c
PHM_WAIT_FIELD_UNEQUAL(hwmgr, reg, field, fieldval)
  -> PHM_WAIT_REGISTER_UNEQUAL(hwmgr, reg, value, mask)
     -> PHM_WAIT_REGISTER_UNEQUAL_GIVEN_INDEX(hwmgr, mm##reg, value, mask)
        -> phm_wait_for_register_unequal(hwmgr, index, value, mask)
```

`smu_helper.h:234`, `:230`, `:225`. La macro mete el `mm` delante del nombre, asi que
`PHM_WAIT_FIELD_UNEQUAL(hwmgr, SMC_RESP_0, ...)` acaba leyendo `mmSMC_RESP_0`.

Hay ademas una forma indirecta, `smu_helper.c:179`:

```c
int phm_wait_for_indirect_register_unequal(struct pp_hwmgr *hwmgr,
                                            uint32_t indirect_port,
                                            uint32_t index, uint32_t value, uint32_t mask)
{
        ...
        cgs_write_register(hwmgr->device, indirect_port, index);
        return phm_wait_for_register_unequal(hwmgr, indirect_port + 1, value, mask);
}
```

Esta **escribe** `index` en `indirect_port` y despues espera en `indirect_port + 1`. Por
la convencion de los registros indirectos, `indirect_port` es el registro de INDICE y
`indirect_port + 1` el de DATOS. Escribiendo el indice y esperando a que el dato cambie,
la espera es por transicion: el host no comprueba un valor, comprueba que el hardware
haya reaccionado.

Que `+1` sea el registro de DATOS **esta verificado en este corpus, con nombres**,
no supuesto. El gemelo de escritura, `smu7_smumgr.c:38`:

```c
static int smu7_set_smc_sram_address(struct pp_hwmgr *hwmgr, uint32_t smc_addr, uint32_t limit)
{
        PP_ASSERT_WITH_CODE((0 == (3 & smc_addr)), "SMC address must be 4 byte aligned.", return -EINVAL);
        PP_ASSERT_WITH_CODE((limit > (smc_addr + 3)), "SMC addr is beyond the SMC RAM area.", return -EINVAL);

        cgs_write_register(hwmgr->device, mmSMC_IND_INDEX_11, smc_addr);
        PHM_WRITE_FIELD(hwmgr->device, SMC_IND_ACCESS_CNTL, AUTO_INCREMENT_IND_11, 0);
        return 0;
}
```

El indice va a `mmSMC_IND_INDEX_11` y el dato a `mmSMC_IND_DATA_11`
(`smu7_smumgr.c:235` y `:249`). Los nombres existen en el corpus.

## AUTO_INCREMENT esta apagado a proposito

`PHM_WRITE_FIELD(..., SMC_IND_ACCESS_CNTL, AUTO_INCREMENT_IND_11, 0)` desactiva el
auto-incremento antes de cada acceso. Por eso el bucle de copia **reescribe el registro
de indice cada 4 bytes**, con `addr += 4` a mano, en lugar de escribir el indice una vez
y dejar que el hardware avance:

```c
while (byte_count >= 4) {
        data = src[0] * 0x1000000 + src[1] * 0x10000 + src[2] * 0x100 + src[3];
        result = smu7_set_smc_sram_address(hwmgr, addr, limit);   /* por cada dword */
        cgs_write_register(hwmgr->device, mmSMC_IND_DATA_11, data);
        src += 4;  byte_count -= 4;  addr += 4;
}
```

Consecuencia para un driver propio: una escritura de 1776 bytes hace **444** escrituras
al registro de indice, no una. Es correcto y es lento. Activando el auto-incremento se
podria escribir el indice una vez, pero eso cambia el protocolo y no esta medido que el
firmware lo soporte. No es una optimizacion que se pueda hacer sin medir.

La misma funcion es la que usan las lecturas (`smu7_read_smc_sram_dword`, `:229`) y las
escrituras sueltas (`smu7_write_smc_sram_dword`, `:240`), luego el patron es comun a todo
el acceso a la SRAM del SMC, no solo a la copia.

## Dos codigos de error distintos para la misma familia de esperas

| funcion | condicion | error |
|---|---|---|
| `phm_wait_on_register` (`smu_helper.c:110`) | el registro llega al valor | `-1` |
| `phm_wait_for_register_unequal` (`smu_helper.c:155`) | el registro deja de ser el valor | `-ETIME` |

`-1` es un codigo generico, no `ETIME`. Un caller que compare contra `-ETIME` para
saber "ha expirado" no capturara un `phm_wait_on_register` agotado. Es un detalle
pequeno y es exactamente el tipo de cosa que se equivoca al reimplementar.

## Tres timeouts distintos en el mismo arbol

No confundir. Son tres mecanismos separados con valores distintos:

| simbolo | valor | quien lo usa |
|---|---:|---|
| `AMD_MAX_USEC_TIMEOUT` | 1000000 (1 s) | `hwmgr->usec_timeout`, las esperas de powerplay y del handshake SMC |
| `AMDGPU_MAX_USEC_TIMEOUT` | 100000 (100 ms) | `adev->usec_timeout`, el core de amdgpu (`amdgpu_device.c:3696`) |
| `usec_timeout` local | 50000 (50 ms) | variables locales en `gfx_v10_0.c`, `gfx_v11_0.c`, `gfx_v12_0.c`, `gfx_v12_1.c` |

Las de 50 ms son locales a cada funcion de lectura de registros MMIO y **no** son el
timeout del SMC. Confundirlas daria un factor 20 de diferencia en el timeout del
handshake.

Ademas `pm/legacy-dpm/si_smc.c:184-187` tiene sus propios valores (1 s y 200 ms), pero
es legacy-dpm: ruta de generacion de Tonga, no la activa de Polaris12.

## Lo que un driver propio hereda y lo que tiene que decidir

Heredar, tal cual:

- `usec_timeout = 1000000` iteraciones
- la semantica "cuenta vueltas, no reloj"
- el codigo `-1` en `phm_wait_on_register`

Decidir, no copiar:

- si el timeout tiene que ser de reloj y no de iteraciones. Con un reloj el
  comportamiento deja de depender de lo lento que sea el bus de registros, que es
  justamente lo que hace el valor actual impredecible entre placas.
- el codigo de error. Devolver `-ETIME` en los dos casos hace que el caller pueda
  distinguir "expiro" de "fallo" sin conocer la funcion.

## Clasificacion

- `USEC_TIMEOUT_INIT = PROVEN`: `hwmgr.c:85`, unico sitio, `AMD_MAX_USEC_TIMEOUT`.
- `USEC_TIMEOUT_VALUE = PROVEN`: 1000000 iteraciones, equivalente a 1 s minimo.
- `USEC_TIMEOUT_ASIC_SPECIFIC = REFUTED`: no hay variante por ASIC.
- `USEC_TIMEOUT_IS_WALL_CLOCK = REFUTED`: cuenta iteraciones.
- `USEC_TIMEOUT_HANDOFF = PROVEN`: dos esperas por transicion sobre `SMC_RESP_0`.
- `USEC_TIMEOUT_ERROR_CODES = PROVEN`: `-1` y `-ETIME` en funciones gemelas.

## Lo que esto NO dice

No dice cuanto tarda de verdad un handshake en esta placa. Eso es medirlo, y medirlo
requiere hardware.

No dice si 1 segundo es suficiente para Polaris12. Es el valor que el driver upstream
usa para todos los ASIC, lo cual no es lo mismo que que sea el correcto para este.

No hay lectura de hardware aqui. Todo es estatico.