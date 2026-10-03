# 215  AllowMvddSwitch se escribe a soft_regs_start + 112, y soft_regs_start no tiene guarda de cero

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

## El hallazgo

Hay dos escrituras a un registro de control del firmware cuyo destino se calcula sumando
un desplazamiento a `soft_regs_start`, y **`soft_regs_start` no se comprueba en ninguna de
las dos**. Es el mismo patron de direccion sin validar que `100` documento para la SRAM, y
aparece aqui por el otro camino: **no es una copia, es una escritura registro a registro**.

`polaris10_populate_vr_config`, `polaris10_smumgr.c:1745-1762`:

```c
if (SMU7_VOLTAGE_CONTROL_BY_SVID2 == data->mvdd_control) {
        if (config != VR_SVI2_PLANE_2) {
                config = VR_SVI2_PLANE_2;
                table->VRConfig |= (config << VRCONF_MVDD_SHIFT);
                cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
                        smu_data->smu7_data.soft_regs_start
                                + offsetof(SMU74_SoftRegisters, AllowMvddSwitch), 0x1);
        } else { ... }
} else if (SMU7_VOLTAGE_CONTROL_BY_GPIO == data->mvdd_control) {
        config = VR_SMIO_PATTERN_2;
        table->VRConfig |= (config << VRCONF_MVDD_SHIFT);
        cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
                smu_data->smu7_data.soft_regs_start
                        + offsetof(SMU74_SoftRegisters, AllowMvddSwitch), 0x1);
}
```

Dos ramas, dos escrituras, **el mismo destino y el mismo valor `0x1`**. Y el patron es
claro: cuando el control de MVDD es por SVI2 o por GPIO, el driver **concede permiso** de
cambio de voltaje escribiendo `AllowMvddSwitch = 1`.

`offsetof(SMU74_SoftRegisters, AllowMvddSwitch) = 112`, medido con gcc. Y
`sizeof(SMU74_SoftRegisters) = 120`.

## De donde sale `soft_regs_start`, y por que puede valer 0

Cuatro usos en el fichero, y **ninguno comprueba que no sea cero**:

| linea | que hace | acumula error |
|---:|---|---|
| 316 | lee el registro del firmware como **fallback** | **no** |
| 1749 | escribe `+112` | no aplica |
| 1758 | escribe `+112` | no aplica |
| 2517 | lo lee en `process_firmware_header` | si |

El de `:316` es el interesante, y el comentario lo explica:

```c
/* Setup SoftRegsStart here for register lookup in case DummyBackEnd is used and ProcessFirmwareHeader is not executed */
smu7_read_smc_sram_dword(hwmgr,
                SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, SoftRegisters),
                &(smu_data->smu7_data.soft_regs_start), 0x40000);
```

O sea: el propio driver reconoce que **hay un caso en el que la cabecera del firmware no
se procesa**, y por eso lee el registro aqui como red de seguridad. Es exactamente el
escenario de un backend de pruebas.

Y ese es justo el caso en el que `soft_regs_start` **se queda en el valor que tenia**, que
tras `kzalloc_obj` (`:339`) es **0**.

## Que pasa con el destino en cero

Con `soft_regs_start == 0`, las dos escrituras van a la direccion:

```
0 + offsetof(SMU74_SoftRegisters, AllowMvddSwitch) = 112
```

Y aqui hay que ser precisos, porque **dos cosas distintas** se pueden decir de esa
direccion, y confundirlas seria el error de base de coordenadas por sexta vez:

**1. Pasa todos los checks.** La comprobacion de `smu7_set_smc_sram_address`
(`smu7_smumgr.c:40-41`) es alineacion a 4 y rango contra `limit`. Con `217`:
`3 & 112 == 0` (alineado) y `0x40000 > 112` (en rango). **Pasa.** Y `217` es la direccion
del vector de arranque mas `217`, asi que **no** es la direccion 0 peligrosa de `100`; es
un offset pequeno pero no nulo.

**2. Cae dentro del rango que escribe la tabla DPM.** La copia de `:2118` escribe de
`108` a `1883`. Y `112 >= 108`: **la direccion 112 esta dentro**.

Ahora el orden, que es lo que decide si hay consecuencia:

```
:2034   polaris10_populate_vr_config   -> escribe en 112
:2118   smu7_copy_bytes_to_smc         -> escribe de 108 a 1883
```

**La escritura va ANTES que la copia completa.** Y la copia completa la sobreescribe. O
sea: **el efecto de la escritura anulada por la tabla se pierde**, y en la SRAM queda el
valor que puso la copia, no el `0x1`.

Eso **degrada el hallazgo**: no es un corrupcion de memoria, es un **permiso que no se
concede**.

## Y eso es el hallazgo de verdad

`AllowMvddSwitch = 1` es lo que **permite** al firmware cambiar el voltaje de MVDD. Las
dos ramas que lo escriben son las que dicen "el control de MVDD es por SVI2" o "por
GPIO", es decir, "hay un regulador con control electronico, hay que permitirle cambiar de
voltaje".

Si `soft_regs_start` vale 0 y la escritura se pierde:

- el firmware **nunca ve `AllowMvddSwitch = 1`**;
- y no cambia el voltaje de MVDD, o lo cambia por un camino que el host no ha autorizado.

Que el firmware lo necesite para funcionar, o que tenga otro camino, es `NOT_IN_CORPUS`:
el firmware no esta en el corpus y no puedo ver que hace con ese bit.

Lo que **si** es `PROVEN`: **el permiso se concede a una direccion que puede no ser la
correcta, y si no lo es, la escritura se pierde en silencio**, porque la copia completa de
la tabla va despues y la pisa. No hay error, no hay assert, no hay aviso.

## Y el orden importa en los dos sentidos

Es importante decir que la conclusion depende **enteramente** del orden, y que ese orden
lo he verificado:

- Si `populate_vr_config` corriera **despues** de la copia de `:2118`, la escritura
  sobreviviria y dejaria un `1` en la direccion 112, que es el primer byte despues de
  `SystemFlags` (`108..111`). Eso si seria una corrupcion de la tabla.
- Como corre **antes**, la escritura se pierde y lo que queda es el permiso no concedido.

Las dos consecuencias son distintas y opuestas en su gravedad. Y **el orden es una
sentencia en una funcion, no una invariante**: si alguien mueve
`polaris10_populate_vr_config` despues de la copia, el fallo pasa de "permiso no
concedido" a "corrupcion de la tabla".

Eso es lo mismo que observe en `094` con los flags de `GraphicsVoltageChangeEnable`, y es
la misma debilidad estructural: **el resultado depende del orden de unas sentencias**.

## Lo que esto tiene de patron, y por que lo registro aparte

Tres hallazgos distintos, tres contextos distintos, **la misma debilidad**:

| documento | dos escrituras al mismo destino | que lo salva |
|---|---|---|
| `094` | `phm_find_boot_level` y `populate_smc_initailial_state` sobre `GraphicsBootLevel` | el segundo **sobrescribe** al primero con otro indice |
| `210`/`107` | `update_uvd_smc_table` y `update_vce_smc_table` sobre el mismo DWORD | cada mascara **preserva** el byte de la otra |
| `215` | las dos ramas de `populate_vr_config` sobre `AllowMvddSwitch` | **nada**: escriben lo mismo, y la copia de la tabla lo pisa |

El tercero es el caso donde **no hay red**: las dos escrituras son identicas y ambas se
pierden.

En los dos primeros, el conflicto se resuelve por construccion porque los dos escritores
hacen cosas distintas. En el tercero, hacen lo mismo, asi que el conflicto no se resuelve:
o aciertan las dos, o fallan las dos.

Y el denominador comun de los tres es **un campo o registro con dos propietarios y ninguna
comprobacion de que el destino sea valido**.

## Clasificacion

- `SOFTREGS_ALLOW_MVDD_SWITCH_WRITE = PROVEN`: `polaris10_smumgr.c:1749-1750` y
  `:1758-1759`, dos ramas, mismo destino, mismo valor `0x1`.
- `SOFTREGS_OFFSET_IS_112 = PROVEN_DERIVED`: `offsetof(SMU74_SoftRegisters,
  AllowMvddSwitch) = 112`, `sizeof = 120`, medidos con gcc.
- `SOFTREGS_START_HAS_NO_ZERO_GUARD = PROVEN_ABSENT`: cuatro usos (`:316`, `:1749`,
  `:1758`, `:2517`), ninguno comprueba que no sea 0. Busqueda por nombre exacto.
- `SOFTREGS_FALLBACK_EXISTS_BECAUSE_HEADER_MAY_NOT_RUN = PROVEN`: el comentario de
  `:314` lo dice: *"in case DummyBackEnd is used and ProcessFirmwareHeader is not
  executed"*.
- `SOFTREGS_FALLBACK_READ_DOES_NOT_ACCUMULATE_ERROR = PROVEN`: `:316` no acumula error,
  a diferencia de `:2517`. Dos lecturas del mismo campo con comportamientos distintos.
- `SOFTREGS_WRITE_AT_ZERO_LANDS_INSIDE_DPM_COPY = PROVEN_DERIVED`: `217` esta en
  `[108, 1884)`, la zona que escribe la copia de `:2118`.
- `SOFTREGS_WRITE_IS_OVERWRITTEN_BY_DPM_COPY = PROVEN` el orden: `:2034` antes de
  `:2118`. **La escritura se pierde.**
- `SOFTREGS_PERMISSION_MAY_NOT_BE_GRANTED = PROVEN_DERIVED` la consecuencia,
  `NOT_IN_CORPUS` el efecto: el firmware nunca ve `AllowMvddSwitch = 1`.
- `SOFTREGS_ORDER_DEPENDENCY_IS_FRAGILE = PROVEN`: el resultado depende de que
  `populate_vr_config` se llame antes de la copia. Mover una sentencia cambia el fallo de
  "permiso no concedido" a "corrupcion de la tabla".

## Lo que esto obliga a hacer en un driver propio

Un registro de la SRAM del firmware al que se concede un permiso tiene que tener
**propietario unico**, y tres reglas:

1. **Comprobar el destino antes de escribir**, no solo que la copia pase el check de
   rango. `217` pasa el check y no por eso es la direccion correcta.
2. **Escribir despues de todo lo demas**, o en un punto del arranque donde se sepa que no
   hay ninguna copia posterior. `AllowMvddSwitch` debe ser **la ultima** escritura.
3. Y **leerlo de vuelta** para confirmar. Es una escritura de un DWORD a un registro de
   permiso: releerlo y comprobar que vale 1 es un ciclo de lectura de la SRAM, que es lo
   que el driver **no hace nunca** (`100` documento que no hay ninguna verificacion).

La tercera es la que convierte el fallo en detectable, y es la de `210` tambien: un
leer-modificar-escribir sin lectura de confirmacion no puede saber si ha surtido efecto.
