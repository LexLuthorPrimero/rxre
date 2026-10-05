# 1435 — el alcance del hallazgo 1402 se estrecha: la ruta de potencia de esta tarjeta es smu7, y su escala es correcta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=CORRECCION-DE-ALCANCE+REFUTACION-DE-PRODUCTOR
TRACK=STATIC(7.1.3, el kernel que corre) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1402-*   ->  CONSECUENCIA ENMENDADA
         09-POWER-CLOCKS/  (el motivo real, que es mejor que el que se le puso)
ORIGEN=el hallazgo 1418 marco 1402 como POR_REVISAR porque su premisa de alcance —que
       arcturus_ppt.c esta en el camino de esta maquina— resulto falsa.  Aqui se arbitra.
ESTADO=PROBADO · arcturus_ppt.c:661 es INALCANZABLE en esta tarjeta, por tabla y no por
       ausencia de fichero · la ruta que sirve la potencia es smu7 y escala bien
       · NO hay ambiguedad de unidad en 7.1.3 para esta tarjeta
       · el motivo por el que esa cifra no es medicion es OTRO, y si se puede medir
```

## 1. Lo que 1402 afirmaba, y qué parte cae

1402 escribió:

> *`arcturus_ppt.c:661` escala `AverageSocketPower` por `<< 8` (=256) en 7.1.3 y por
> `* MILLIWATT_PER_WATT` (=1000UL) en 7.2.8. Razón 3.90625.*
> **CONSECUENCIA:** *09-POWER-CLOCKS: no usar cifras de potencia de
> `AMDGPU_PP_SENSOR_GPU_AVG_POWER` como medición hasta cerrar la escala.*

**La divergencia es real y se mantiene.** `arcturus_ppt.c:661` sigue siendo `<< 8` en
7.1.3 y `* MILLIWATT_PER_WATT` en 7.2.8, y la corrección de 1402 §2 —que el `<< 8` es de la
familia smu11 completa, no de Arcturus— sigue en pie.

**Lo que cae es el alcance.** La consecuencia se apoyaba en que ese `case` se ejecuta en
esta máquina. No se ejecuta.

## 2. Por qué `arcturus_ppt.c` no se ejecuta aquí

No por "`CHIP_POLARIS12` no aparece en el fichero". Eso sería `NOT_FOUND`. Es
`PROVEN` inalcanzable, por tres legs:

1. **`arcturus_set_ppt_funcs()` —el único registrador de `arcturus_ppt_funcs`— se llama desde
   un único sitio**, `pm/swsmu/amdgpu_smu.c:770`, protegido por
   `case IP_VERSION(11, 0, 2):` de `amdgpu_ip_version(adev, MP1_HWIP, 0)`.
2. **`is_support_sw_smu()` es false aquí.** Su condición es
   `amdgpu_ip_version(adev, MP1_HWIP, 0) >= IP_VERSION(11, 0, 0)`. Esta tarjeta **no tiene
   bloque MP1** —medido en el log del hallazgo 1418, nueve bloques y ninguno es MP1— así que
   la versión es 0 y la comparación falla.
3. **`adev->powerplay.pp_funcs` sólo lo asignan cuatro ficheros en todo el árbol amd**, y
   esta tarjeta coge el primero:

   | asignador | fichero | ¿alcanzable aquí? |
   |---|---|---|
   | `&pp_dpm_funcs` | `pm/powerplay/amd_powerplay.c:62` | **sí** — `pp_smu_ip_block`, `vi.c:2114` |
   | `&swsmu_pm_funcs` | `pm/swsmu/amdgpu_smu.c:837` | no: exige MP1 ≥ 11.0.0 |
   | `&si_dpm_funcs` | `pm/legacy-dpm/si_dpm.c:8001` | no: nunca se añade el bloque SI |
   | `&kv_dpm_funcs` | `pm/legacy-dpm/kv_dpm.c:2962` | no: nunca se añade el bloque KV |

> `arcturus_get_smu_metrics_data()` no se entra, y la línea 660-661 no se evalúa. No es
> "probablemente no se use": está **fuera del grafo de despacho** de esta ASIC.

## 3. La ruta que sí sirve la potencia, y su escala

Medida en **7.1.3**, el kernel que corre.

```c
/* amdgpu/amdgpu_kms.c:1201-1214 */
case AMDGPU_INFO_SENSOR_GPU_AVG_POWER:
        if (amdgpu_dpm_read_sensor(adev, AMDGPU_PP_SENSOR_GPU_AVG_POWER, ...)) {
                /* fall back to input power for backwards compat */
                if (amdgpu_dpm_read_sensor(adev, AMDGPU_PP_SENSOR_GPU_INPUT_POWER, ...))
                        return -EINVAL;
        }
        ui32 >>= 8;
```

```c
/* pm/powerplay/hwmgr/smu7_hwmgr.c:4151-4158 */
case AMDGPU_PP_SENSOR_GPU_AVG_POWER:
        if ((adev->asic_type != CHIP_HAWAII) &&
            (adev->asic_type != CHIP_BONAIRE) &&
            (adev->asic_type != CHIP_FIJI) &&
            (adev->asic_type != CHIP_TONGA))
                return -EOPNOTSUPP;
        else
                return smu7_get_gpu_power(hwmgr, (uint32_t *)value);
```

**`CHIP_POLARIS12` no está en la lista.** Comportamiento real en esta tarjeta:

```text
AMDGPU_PP_SENSOR_GPU_AVG_POWER  ->  -EOPNOTSUPP
     -> cae al fallback de compatibilidad:  GPU_INPUT_POWER
          -> misma lista, Polaris12 tampoco está:  smu7_get_gpu_power()
               ->  PPSMC_MSG_GetCurrPkgPwr,  SIN NINGUNA ESCALA   smu7_hwmgr.c:4064-4065
     ->  ui32 >>= 8                                              amdgpu_kms.c:1213
```

**El SMC entrega vatios en Q24.8 y el consumidor hace `>> 8`. Producto y consumidor
concuerdan.** En 7.2.8 el productor pasa por `PP_PWR_Q24_8_TO_MW` y el consumidor divide por
1000: **misma unidad física, mismo resultado**, sólo cambia el redondeo.

> **Para esta tarjeta no hay ambigüedad de unidad que resolver, y no hay error de 3.9×.**
> `grep -rn MILLIWATT .../linux-7.1.3/drivers/gpu/drm/amd/` → **0 apariciones**, que es
> coherente: en 7.1.3 esa ruta no la necesita.

## 4. El motivo real, que es mejor que el que se le puso a 1402

La cifra de potencia de esta tarjeta **sigue sin ser una medición**, pero por razones
medibles y no por una ambigüedad de escala:

```c
/* smu7_hwmgr.c:4060-4086, inlined en smu7_get_gpu_power() */
smum_send_msg_to_smc_with_parameter(hwmgr, PPSMC_MSG_GetCurrPkgPwr, 0, &tmp);
*query = tmp;                      /* sin escala */
if (tmp != 0) return 0;            /* caso normal: una sola lectura, y sale */

smum_send_msg_to_smc(hwmgr, PPSMC_MSG_PmStatusLogStart, NULL);
cgs_write_ind_register(..., ixSMU_PM_STATUS_95, 0);
for (i = 0; i < 10; i++) {
        msleep(500);
        smum_send_msg_to_smc(hwmgr, PPSMC_MSG_PmStatusLogSample, NULL);
        tmp = cgs_read_ind_register(..., ixSMU_PM_STATUS_95);
        if (tmp != 0) break;
}
```

| defecto | evidencia | por qué invalida la medición |
|---|---|---|
| **es una muestra instantánea**, no un promedio | el mensaje es `GetCurrPkgPwr` — "corriente", no "media"; y la etiqueta `GPU_AVG_POWER` es un nombre de ioctl, no una ventana de integración | una lectura puntual no es un promedio de nada |
| **si el SMC devuelve 0, la lectura bloquea hasta ~5 s** dentro del mutex de DPM | el bucle de 10 × `msleep(500)`, llamado bajo `mutex_lock(&adev->pm.mutex)` en `pm/amdgpu_dpm.c:527` | una lectura de un sensor puede retrasar transiciones de DPM ~5 s |
| **la unidad de `ixSMU_PM_STATUS_95` no está declarada en la fuente** | el símbolo viene de una cabecera soc15 ausente del corpus; `PPSMC_MSG_GetCurrPkgPwr` sí está, `smu7_ppsmc.h:393` = `((uint16_t)0x282)` | la rama de respaldo es la única cuyo valor no se puede auditar |

**El primero es el importante.** Antes atribuí "no es medición" a una escala mal
entendida; **es una muestra puntual con etiqueta de promedio**, y eso no se arregla
entendiendo la escala: hay que muestrear N veces y promediar, con su desviación.

## 5. Cómo queda 1402

| | |
|---|---|
| **la divergencia `<< 8` vs `* 1000UL`** | se mantiene. `PROBADO` como lectura de fuente |
| **es de la familia smu11 completa, no de Arcturus** | se mantiene (1402 §2) |
| **`arcturus_ppt.c:661` se ejecuta en esta tarjeta** | **`REFUTADO`** |
| **las cifras de potencia de esta host no son medición** | **se mantiene, pero por otro motivo** (§4) |
| **«hasta cerrar la escala»** | **caduca**: no hay escala que cerrar en esta ruta |

## 6. Una trampa que este hallazgo explica, y que casi me costó el mismo error que 1418

**El log no dice qué pila de power management está viva.** Esta tarjeta imprime

```text
detected ip block number 5 <smu_v1_0_0> (powerplay)
```

y ese mismo `pp_smu_ip_block` lo registran **dos mundos distintos**: `vi.c:2114` para el
legacy, y `amdgpu_discovery.c:2301` para ASIC soc15 con MP1. **El banner es idéntico en los
dos casos.** Quien lea el log **no puede saber** cuál de los dos está activo.

La prueba es que el bloque 5 apareció: por la rama `default:` de `amdgpu_discovery.c` este
ASIC habría recibido `-EINVAL` ("Failed to add smu ip block"), porque MP1 es 0.

> Y las tres decisiones que deciden IP blocks, familia y pila de PM viven en **tres ficheros
> distintos, con tres claves distintas**: `amdgpu_device.c:1975-1996` decide bloques por
> `asic_type`; la familia por un efecto secundario de una comprobación de APU
> (`amdgpu_device.c:1984`); y la pila de PM en `hwmgr.c:78`, que conmuta **primero por
> familia** y **después por chip** (`hwmgr.c:131`, `:156`).
>
> **Ésta es la razón estructural por la que el hallazgo 1418 se equivocó de ASIC.** No fue
> descuido de lectura: el árbol tiene tres Mapas y sólo uno es visible desde el arranque.

## 7. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/     (el kernel que corre)
  amdgpu/amdgpu_kms.c:1201-1214        el fallback y el >> 8
  amdgpu/amdgpu_discovery.c:2301       pp_smu_ip_block tambien se registra aqui
  amdgpu/amdgpu_device.c:1975-1996     los bloques por asic_type ; familia en :1984
  amdgpu/vi.c:2114                     y aqui, para esta tarjeta
  pm/amdgpu_dpm.c:527-530              el mutex que rodea la lectura
  pm/powerplay/amd_powerplay.c:62,278-301   pp_dpm_funcs ; pp_smu_ip_block 1.0.0
  pm/powerplay/hwmgr/hwmgr.c:78,131,156      hwmgr_early_init: familia, luego chip
  pm/powerplay/hwmgr/smu7_hwmgr.c:4060-4086  smu7_get_gpu_power, el bucle de 5 s
  pm/powerplay/hwmgr/smu7_hwmgr.c:4151-4158  la lista de ASIC que excluye a POLARIS12
  pm/powerplay/inc/smu7_ppsmc.h:393          PPSMC_MSG_GetCurrPkgPwr = 0x282
  pm/swsmu/amdgpu_smu.c:594,768-773,837      is_support_sw_smu ; arcturus ; swsmu_pm_funcs
  pm/legacy-dpm/si_dpm.c:8001, kv_dpm.c:2962 los otros dos asignadores, inalcanzables
grep  MILLIWATT en linux-7.1.3/drivers/gpu/drm/amd/  ->  0
metodo   lectura estatica de 7.1.3.  Ninguna ejecucion, ningun acceso root.
```

```text
ESTADO=PROBADO · arcturus_ppt.c:661 PROVEN inalcanzable en esta tarjeta (3 legs, no por
       ausencia de fichero): sin MP1 -> is_support_sw_smu() false -> nunca se instala
       swsmu_pm_funcs -> nunca se llama arcturus_set_ppt_funcs()
       · la ruta real es smu7 y su escala es CONSISTENTE en 7.1.3: SMC da Q24.8 W, el
         consumidor hace >>8.  No hay ambiguedad de unidad y no hay error de 3.9x aqui
       · 7.2.8 produce la MISMA unidad fisica con otro redondeo, no una escala distinta
ENMIENDA  1402: "hasta cerrar la escala" CADUCA para esta tarjeta.  "no es medicion" se
       mantiene, pero por motivos distintos y MEDIBLES
MOTIVO_REAL  (a) es una muestra instantanea (PPSMC_MSG_GetCurrPkgPwr), no un promedio
       (b) si el SMC devuelve 0, la lectura bloquea hasta ~5 s dentro de mutex de DPM
       (c) la unidad de la rama de respaldo ixSMU_PM_STATUS_95 no esta declarada
NUEVO    el banner <smu_v1_0_0> (powerplay) NO identifica la pila de PM: lo imprime el
       mismo pp_smu_ip_block desde dos mundos.  Y bloques/familia/PM se deciden en tres
       ficheros con tres claves.  Esa asimetria es la causa estructural de 1418
LIMITACION ixSMU_PM_STATUS_95 no esta en el corpus; su unidad queda NOT_DETERMINED
Siguiente  1) promediar N muestras de GetCurrPkgPwr con su desviacion: eso es lo que
           convierte el numero en medicion, y no requiere ninguna escritura al hardware
         2) amdgpu_ioctl.c y amdgpu_hwmon.c NO estan en el corpus, asi que el salto ioctl->case
           y el EBUSY de hwmon siguen sin cierre por fuente.  La via fdinfo de DRM queda
           como la unica lectura pasiva posible para el oraculo de fence
```
