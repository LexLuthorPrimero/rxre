# 604 · Una contradicción que no puedo cerrar, y una premisa de toda la rama sin verificar

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## ENMENDADO por `605` — leer este hallazgo con la corrección puesta
>
> Este texto **se conserva íntegro** como registro de lo que se pensaba entonces
> (§68: no destruir historia), pero dos de sus conclusiones quedan **sustituidas**:
>
> | afirmación de `604` | estado real |
> |---|---|
> | «No he probado que `polaris10_smumgr.c` se ejecute en mi placa» | **`REFUTED` por `605`**: sí se ejecuta, cerrado por agotamiento sobre el `switch` de `amdgpu_discovery.c:2293` |
> | «si la respuesta es swsmu, la rama entera describe código muerto» | **`REFUTED`**: swsmu no tiene generación smu7, luego no puede atender mi ASIC |
> | «caen los hallazgos `403`…`603` en lo que respecta a si describen mi hardware» | **sin cambio**: `605` los **resucita**, la premisa pasa a `PROVEN` |
> | la contradicción del PowerTune (`0x9EAA` vs `0x9EAB`) | **`NOT_DETERMINED`**, sigue abierta, con un discriminante nuevo en `605` |
>
> La lección de este hallazgo sí se sostiene, y `605` la confirma por tercera vez:
> el error fue un artefacto mío convertido en afirmación sobre el hardware.

> ## Resultado
>
> Al medir el PowerTune encontré **una contradicción real** entre dos mediciones
> que ambas se sostienen, y al rastrearla apareció algo más grave: **que toda la
> rama depende de una premisa que no he verificado**.
>
> ```
> PowerTune en 0x9EAB (lo que dice usPowerTuneTableOffset = 673)
>     layout ALINEADO, el que usa el kernel:  TDP=0  TDC=8960  TjMax=0   -> basura
>     layout EMPAQUETADO:                     TDP=35 TDC=36   TjMax=93  -> coherente
>
> PowerTune en 0x9EAA (un byte antes), layout alineado:
>     TDP=35 TDC=36 TjMax=93 Shutdown=97 stretch=2   -> LOS CINCO
> ```
>
> **No sé por qué.** Y la premisa sin verificar es más importante que la
> contradicción.

## La contradicción

Tres campos del header PowerPlayInfo apuntan a direcciones que **verifiqué con
anclas independientes**:

| offset | campo | valor | destino | ancla |
|---|---|---|---|---|
| 45 | `usSclkDependencyTableOffset` | 267 | `0x9D15` | **confirmada** por `267` |
| 57 | `usPowerTuneTableOffset` | 673 | `0x9EAB` | sin ancla externa |
| 61 | `usPCIETableOffset` | 752 | `0x9EFA` | **coherente**: rev 1, 3 entradas |

La de `0x9D15` coincide con lo que `267` midió de forma independiente. La de `0x9EFA`
da una tabla PCIe que **decodifica coherente** (3 entradas, 8 carriles, 26100 kHz). Y
la de `0x9EAB` da basura bajo el layout que usa el kernel.

Probé **doce bases candidatas** con el layout alineado, de `0x9EA6` a `0x9EB1`, y
**solo `0x9EAA` da los cinco valores de golpe**. Ninguna otra.

Y `0x9EAA` es exactamente `0x9EAB − 1`, o sea `673 − 672`.

**Las dos cosas no pueden ser verdad**, y no voy a elegir la que me conviene:

- Si `usPowerTuneTableOffset` es 673, la tabla está desplazada 1 byte y el kernel
  lee basura.
- Si la tabla está donde los datos son coherentes, entonces el offset está mal, y
  el recorrido del header que hice está desplazado 1 byte — **pero entonces `:45` y
  `:61` también lo estarían**, y `:45` coincide con un ancla y `:61` decodifica
  bien.

Lo único que se me ocurre para resolverlo es que el VBIOS tenga una rareza propia
en esa tabla, y **no tengo forma de comprobarlo con este corpus**.

## Lo que significaría si la primera lectura es la buena, y por qué no lo doy por bueno

`ATOM_Polaris_PowerTune_Table` (`pptable_v1_0.h:422`) empieza:

```c
UCHAR  ucRevId;      /* @0 */
USHORT usTDP;        /* @2  <-- 1 byte de relleno en @1 */
```

Medido: `sizeof` alineado 56, empaquetado 53, y `usClockStretchAmount` en **26**
alineado / **25** empaquetado. **Los tres** structs PowerTune (Tonga, Fiji, Polaris)
tienen el mismo `UCHAR` + `USHORT`, así que no es un *typo* de uno.

Y `PP_ASSERT_WITH_CODE(cond, msg, code)` **ejecuta `code` cuando la condición es
falsa** — no está compilado fuera (`pp_debug.h:37`).

La cadena, si el kernel leyera 26880:

```
usClockStretchAmount  = 26880
:1661  stretch_amount = (uint8_t)26880 = 0
:1696  if (stretch == 0 || stretch > 5)   ->  CIERTO
:1699  PP_ASSERT_WITH_CODE(false, ..., return -EINVAL)
:2005  PP_ASSERT_WITH_CODE(0 == result, ..., return result)
       -> init_smc_table ABORTA en :2007
       -> :2118 LA COPIA DE 1776 B NO SE EJECUTA
```

Eso **revertiría `505`** y **dejaría sin objeto el `TAPADA 6` de `502`**.

**No lo afirmo**, porque un resultado que predice que la tarjeta no inicializa su
tabla DPM es un resultado que predice un fallo muy visible, y eso me dice que en
algún eslabón estoy equivocado. Prefiero un `NOT_DETERMINED` honesto a una
conclusión que no puede ser cierta.

## La premisa que no había verificado, y que es más grave

**No he probado que `polaris10_smumgr.c` se ejecute en mi placa.**

Todo lo que he construido desde `403` —el orden traced, `TAPADA 6`, las 16 puertas,
el cap de clock stretcher, la tabla PCIe, los 95 campos— asume que el **powerplay
legacy** es la ruta viva. Lo único que sé es que mi `device` es `0x699F` y que
`amdgpu_drv.c:2041` lo mapea a `CHIP_POLARIS12`, que es un concepto del powerplay
legacy.

Y **`chip_id` viene de `revkit/obs.py:37`, un portador secundario.**

Lo que sí he encontrado ahora, al rastroar el productor de la contradicción:

```
adev->powerplay.pp_handle  lo asigna quien inicializa:
   amd_powerplay.c:61      = hwmgr     <- powerplay LEGACY  (mi ruta)
   amdgpu_smu.c:836        = smu       <- swsmu              (la otra)
   kv_dpm.c / si_dpm.c     = adev      <- legacy DPM

amdgpu_dpm.c:39   amdgpu_dpm_is_legacy_dpm(adev)  ==  (pp_handle == adev)
amdgpu_dpm.c:126  struct smu_context *smu = adev->powerplay.pp_handle;   <- TIPO swsmu
```

Ese `:126` es la señal: **`amdgpu_dpm.c` trata `pp_handle` como `smu_context`**, que es
el tipo de **swsmu**. En el powerplay legacy ese mismo campo contiene un
`struct pp_hwmgr *`.

No he encontrado la función que decide, y **no sé cuál de los dos-subsistemas se
registra para `CHIP_POLARIS12`**. Ese es un `NOT_FOUND` real: busqué
`amdgpu_dpm_init` en `pm/amdgpu_dpm.c` y **no existe**, así que la inicialización
está en otro sitio y no lo he encontrado.

**Mientras eso no esté resuelto, la premisa de toda la rama es `NOT_PROVEN`**, y con
ella caen los hallazgos `403`, `502`, `505`, `506`, `507`, `601` y `603` en lo que
respecta a **si describen mi hardware**. Sus mediciones del código siguen siendo
válidas como Measurement del código; lo que no está probado es que ese código
corra.

## Lo que sí queda en pie, con el alcance correcto

| afirmación | alcance |
|---|---|
| `SMU74_Discrete_DpmTable` no tiene relleno | **`PROVEN` sobre el código** |
| `ATOM_Polaris10_PCIE_Table` tiene 2 bytes de relleno y el VBIOS no | **`PROVEN` sobre el código y mi VBIOS** |
| Los 7 `SIN_ORDEN` se ordenan por el trazado de `403` | **`PROVEN` sobre el código**, sujeto a la premisa |
| Los 95 campos con su último escritor | **`PROVEN` sobre el código**, sujeto a la premisa |
| Todo eso **describe mi placa** | **`NOT_PROVEN`** |

Es una distinción que he hecho mal hasta ahora: **medir el código** y **medir el
hardware** no son lo mismo, y he estado confundiendo el segundo con el primero.

## Errores de esta iteración, que han sido varios y del mismo tipo

**1. Miré en la cabecera equivocada y concluí que los structs no existían.** Busqué
`ATOM_Polaris_PowerTune_Table` en `amd/include/pptable.h`, no encontré nada, y dije
«no existe en este kernel». Están en `pm/powerplay/hwmgr/pptable_v1_0.h`. Con el
ámbito acotado y el `exit` verificado en `amd/` completo, aparecieron en dos golpes.

Es la **séptima vez** que un búsqueda acotada mal hecha me da una ausencia, y la
primera en la que además **actué sobre ella** en vez de repetir la búsqueda.

**2. Cuatro intentos seguidos de fallo en el generador de probes**, todos de la misma
familia: `%s` de C dentro de un `%` de Python, `%%zu` doble-escapado, una llave de
`main` cerrada de más, y una línea `return` suelta. Dos fueron **silenciosos**: el
fichero se escribía mal y el error aparecía en gcc, lejos de la causa.

**3. Calculé «1280 bytes de relleno» en `603` con una aritmética que no podía
funcionar**, comparando el tamaño de un elemento de array contra el span del array.
Un número plausible y falso, del tamaño exacto del hallazgo que buscaba.

Los tres son: **un artefacto mío, plausible, y falso**. Y los tres se habrían
evitado con la misma regla que ya funciona — contar y mirar la unidad antes de
interpretar.

## Frontier siguiente

**Resolver cuál de los dos subsistemas de power play se registra para `CHIP_POLARIS12`,
antes de nada más.**

Es la premisa de toda la rama y está sin verificar desde el principio. Todo lo demás
—la contradicción del PowerTune, el defecto de la tabla PCIe, las 16 puertas— son
mediciones **sobre el código**, y son válidas, pero **no describen mi hardware hasta
que se sepa que ese código corre**.

La pregunta es concreta y acotada: **`adev->powerplay.pp_handle` acaba siendo un
`struct pp_hwmgr *` (legacy) o un `struct smu_context *` (swsmu) para el ASIC
`CHIP_POLARIS12`**, y quién lo asigna en el camino de mi placa.

Y si la respuesta es **swsmu**, entonces la rama entera está describiendo código
muerto y hay que **empezar de otro lado**: los relojes y el DPM de mi placa estarían
en `swsmu/smu7/arcturus_ppt.c` o similar, no en `polaris10_smumgr.c`. Sería un
descubrimiento desagradable pero **decisivo**, y habría evitado seis hallazgos sobre una
ruta que quizá no se ejecuta.

Criterio de cierre: el punto del arranque donde se decide, el tipo efectivo de
`pp_handle` para `CHIP_POLARIS12`, y con ello la premisa de la rama pasa de
`NOT_PROVEN` a `PROVEN` o a `REFUTED`.