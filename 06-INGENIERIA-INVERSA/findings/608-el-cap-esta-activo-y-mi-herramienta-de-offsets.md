# 608 · El cap está activo, y mi herramienta de offsets tiene un error de 1 byte

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## ANULADO POR `906` — este hallazgo se construyó sobre un método defectuoso
>
> Texto íntegro conservado (§68), pero **su premisa central era falsa y la medí
> mal**.
>
> | afirmación de este fichero | estado real |
> |---|---|
> | «el VBIOS va empaquetado y el struct no» | **`REFUTED`**: los dos van empaquetados (`pptable_v1_0.h:30` tiene `#pragma pack(push,1)` y el struct está dentro) |
> | «este árbol lee direcciones imposibles» | **`REFUTED`**: leía el struct mal, no el árbol |
> | «este árbol no conduce mi placa» | **`REFUTED`**: la versión coincide (`7.1.3-200.nobara.fc44.x86_64`) y el árbol es correcto |
> | «la captura está truncada» | **`REFUTED`**: el option header declara 115×512 = 58880 y el fichero tiene eso |
> | «`base = 0x9C0A`» | **`PROVEN`**, y el BTF del módulo confirma los tres offsets que leí |
>
> **Causa**: mi generador de probes extraía el *cuerpo* del struct y lo compilaba
> fuera del `#pragma pack` que lo rodea. Un solo defecto produjo los cuatro
> síntomas: `usTableSize`@6, los offsets en 46/58/62, y `usClockStretchAmount`@26.
>
> El BTF del `amdgpu.ko` en marcha da `usTableSize`@**5**, offsets **45/57/61** y
> `usClockStretchAmount`@**25**. Los cinco valores que leí a mano del VBIOS
> coinciden con el módulo y **ninguno** con mi probe.
>
> Lo que sí sobrevive de este fichero: la cadena de `base = 0x9C0A` con sus cinco
> validaciones, y la medición del option header.


> ## CONSECUENCIA DE `906` — el `NOT_DETERMINED` de §3 sí se resuelve
>
> `usClockStretchAmount` = **2**, confirmado por el BTF del módulo en marcha
> (offset empaquetado **25**). Está en dominio (1..5), así que:
>
> ```
> :1696  if (stretch == 0 || stretch > 5)  ->  FALSO, no aborta
> :2005  init_smc_table CONTINUA
> :2118  LA COPIA DE 1776 B SE EJECUTA
> ```
>
> - El cap **sí** está activo (`§1` de este fichero, sigue siendo `PROVEN`).
> - El populate ClockStretcher **sí** tiene éxito.
> - **`502` vuelve a ser válido**: los 6 `TAPADA` tapan de verdad y las
>   escrituras AVFS de `:142/:149/:157/:166` **no sobreviven**.
> - **`505` queda `CORROBORATED`**, que era su conclusión original.
> - `601` **sigue `REFUTED`**, y ahora el BTF lo confirma.
>
> Y queda intacto lo mejor de este fichero: **la causa estaba identificada y
> escrita en su §6, y no la apliqué al probe siguiente.**

> ## Resultado
>
> La pregunta era si la puerta de clock stretcher de `:2004` dispara. **Sí
> dispara**, y la cadena entera está medida. Pero al medirla encontré que **mi
> propia herramienta de `offsetof` discrepa del VBIOS en 1 byte en los tres
> campos de golpe**, lo que deja en duda su propio resultado.
>
> Y en el camino queda **refutada** la afirmación central de `601`.

## 1. La puerta: sí dispara, con la cadena completa medida

El interruptor es `smu7_hwmgr.c:1939-1942`:

```c
if ((hwmgr->pp_table_version != PP_TABLE_V0) &&
    (hwmgr->feature_mask & PP_CLOCK_STRETCH_MASK) &&
    (table_info->cac_dtp_table->usClockStretchAmount != 0))
        phm_cap_set(..., PHM_PlatformCaps_ClockStretcher);
```

Las tres condiciones, medidas:

| condición | valor | fuente |
|---|---|---|
| `pp_table_version != PP_TABLE_V0` | V1 | VBIOS |
| `PP_CLOCK_STRETCH_MASK = 0x400` (`include/amd_shared.h:226`) | — | medido |
| `amdgpu_pp_feature_mask = 0xfff7bfff` (`amdgpu_drv.c:202`, **parámetro de módulo**) | `0xfff7bfff & 0x400 = 0x400` | medido |
| `adev->pm.pp_feature = amdgpu_pp_feature_mask` | `amdgpu_device.c:2021` | medido |
| `hwmgr->feature_mask = adev->pm.pp_feature` | `amd_powerplay.c:59` | medido |
| `usClockStretchAmount != 0` | **26880** | medido sobre mi VBIOS |

Y hay una **tercera** condición que la anula, y no aplica:

```c
smu7_hwmgr.c:1975
if ((adev->pdev->device == 0x699F) && (adev->pdev->revision == 0xCF))
        phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
```

Mi revisión es **`0xC7`**, no `0xCF`. Corrijo el alcance de `604`, que la tenía
como portador sin verificar: `revkit/obs.py:141` lee
`/sys/bus/pci/devices/*/revision`, que es **fuente primaria**, y `:36` cita la
línea de arranque del kernel
`(POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7)`, donde ese `0xC7` lo lee el driver
del espacio de configuración PCI. **No es secundario, y no es `0xCF`.**

Con eso, la cadena:

```
cap ACTIVO
  -> :2002  phm_cap_enabled = TRUE
  -> :2004  polaris10_populate_clock_stretcher_data_table
  -> :1661  stretch_amount = (uint8_t)26880 = 0
  -> :1696  if (stretch_amount == 0 || stretch_amount > 5)   ->  CIERTO
  -> :1697  phm_cap_unset(ClockStretcher)
  -> :1701  return -EINVAL
  -> :2007  PP_ASSERT_WITH_CODE(0 == result, ..., return result)  -> ABORTA
  -> :2118  LA COPIA DE 1776 B NO SE EJECUTA
```

Leído completo, `:1650-1709` y `:1996-2016`. Y confirmado que
`PP_ASSERT_WITH_CODE(cond, msg, code)` **ejecuta `code` cuando `cond` es falsa**
(`pp_debug.h:37`).

**Consecuencia sobre `502`:** los **6 `TAPADA` no tapan nada**, porque `:2118` no
corre. Y las cuatro escrituras AVFS de `:142/:149/:157/:166` **sobreviven**.

Un detalle que no había visto: `:1696` está **después** del bucle `:1671-1691`,
así que `Sclk_CKS_masterEn0_7`, `Sclk_voltageOffset[]` y `LdoRefSel` **sí quedan
escritos** aunque la función falle. Y en `:1674` hay una rama
`chip_id == CHIP_POLARIS10` que mi `CHIP_POLARIS12` no toma.

## 2. `601` queda refutada: la tabla PCIe no tiene ningún relleno

`601` afirmaba que el VBIOS ponía las entradas en `entries@2` y el kernel las leía
en `entries@4`, un desfase de 2 bytes. Medido con gcc sobre el struct real:

```
ATOM_Polaris10_PCIE_Record:  sizeof alineado 8 / empaquetado 8     SIN RELLENO
                             ulPCIE_Sclk   @+4  en ambos
ATOM_Polaris10_PCIE_Table:   ucRevId @0, ucNumEntries @1, entries @2  en ambos
```

Y `process_pptables_v1_0.c:550-552` avanza con
`GET_FLEXIBLE_ARRAY_MEMBER_ADDR`, que es `sizeof(type) * n` = **8**
(`pp_debug.h:58-59`). Paso 8, alineado, sin ambigüedad.

**No hay desfase de 2 bytes. `601` era `PROVEN` y es `REFUTED`.**

Su origen está claro: en esta sesión hice un probe con el cuerpo del struct
sacado a mano, y el resultado de `601` salió de un layout supuesto. Lo mismo que
me pasó ahora con un probe de la tabla PCIe, que me dio carriles 0/0/252 hasta
que usé el struct real.

Y el dato bueno: la tabla PCIe decodifica coherente en `0x9EFA`.

```
0x9EFA:  rev=1  numEntries=3
  lanes  8 / 8 / 8
  sclk   2812 / 26100 / 26100 kHz
```

## 3. El problema real: mi herramienta de offsets discrepa 1 byte

Midiendo `ATOM_Tonga_POWERPLAYTABLE` con gcc, los tres campos quedan así:

| campo | kernel dice | yo leí en el VBIOS | el VBIOS con el offset del kernel da |
|---|---|---|---|
| `usSclkDependencyTableOffset` | **46** | 45 | 30465 |
| `usPowerTuneTableOffset` | **58** | 57 | **2** |
| `usPCIETableOffset` | **62** | 61 | **2** |

Un desfase de **1 byte en los tres**, y los valores del kernel son absurdos: un
offset de 30465 sale del ROM de 58880 bytes, y un offset de 2 apunta dentro de la
propia cabecera.

Además, 45, 57 y 61 son **impares**, y con campos `USHORT`/`ULONG` eso es
**imposible** en cualquier struct naturalmente alineado. El VBIOS los tiene en
impares, y solo una de estas dos cosas puede ser cierta:

```
H1  el VBIOS esta empaquetado 1 byte  ->  el driver lee TODOS los campos
                                            de la cabecera corridos
H2  la base que yo calculo esta 1 byte
    tarde  ->  el driver lee bien y mi
               base 0x9C0A es la que falla
```

**No elijo.** Y no puedo elegir con lo que tengo, porque mi barrido de bases fue
**degenerado**: `0x9C09 + 46` es **la misma dirección** que `0x9C0A + 45`. Al
mover base y offsets a la vez llegué al mismo byte y leí eso como «la única base
que funciona». No era una base distinta: era la misma lectura descrita de dos
formas.

**Eso es lo grave.** La medición de la tabla PCIe y la del PowerTune salieron
del **mismo fichero y del mismo método de extracción**, así que **no puedo
assertar que `usClockStretchAmount` valga 26880** sin heredar un método que ya
se ha demonstrado desplazado 1 byte en el fichero vecino.

## 4. Lo que sí y lo que no

| afirmación | estado |
|---|---|
| el cap de ClockStretcher se activa en mi placa | **`PROVEN`**, cadena completa |
| `rev = 0xC7`, luego el escape `:1975` no aplica | **`PROVEN`**, fuente primaria |
| `ATOM_Polaris10_PCIE_Table` no tiene relleno | **`PROVEN`**, gcc |
| la tabla PCIe vive en `0x9EFA` con 3 entradas | **`PROVEN`** |
| «desfase de 2 bytes en la tabla PCIe» (`601`) | **`REFUTED`** |
| `usClockStretchAmount = 26880` -> `:2118` no corre | **`NOT_DETERMINED`**: depende de H1/H2 |
| la contradicción `0x9EAA` / `0x9EAB` | **`NOT_DETERMINED`**, y ahora con menos ruido |

Lo que **no** he hecho, y es un límite que declaro: he medido offsets de struct
sacando el cuerpo con una expresión regular y montando un probe aparte, y eso ha
fallado dos veces hoy en dos structs vecinos. Es una fuente de error conocida y
debo cambiarla antes de volver a usarla.

## 5. Los errores de esta iteración

**1. Barrido degenerado, leído como resultado.** Moví base y offset a la vez y
llegué al mismo byte. Parecía haber encontrado una base alternativa y no había
ninguna. Lo vi al calcular `0x9C09+46 == 0x9C0A+45` al escribir el resultado, y
no antes de actuar.

**2. Un probe sobre layout supuesto.** Antes de usar el struct real de la tabla
PCIe leí unos bytes con un layout que me inventé, y obtuve carriles 0/0/252. Si
no llego a usar el struct real, habría «confirmado» que el desfase existía.

**3. El `%` de C dentro del `%` de Python, décima vez**, y la cuarta en dos días.
Cuatro fallos seguidos de la misma clase al generar un probe, dos de ellos
silenciosos.

**4. `ATOM_COMMON_TABLE_HEADER`:** asumí que eran 2 bytes. Son **4**
(`USHORT usStructureSize` + 2 `UCHAR`). Lo supe porque el resultado no cuadraba, y
debí verificarlo antes.

Los cuatro son **supuestos no verificados que actué como mediciones**, y los dos
últimos ya los había pagado antes en esta sesión.

## 6. Regla que me llevo, y que es la que faltaba

Durante toda esta serie he estado midiendo struct con gcc y comparando contra
el VBIOS, y **tratando el resultado de gcc como verdad sin medir el sesgo del
método**. No lo había hecho porque `603`, `505` y `601` salían coherentes, y esa
coherencia era **mi** criterio de éxito, no uno independiente.

El criterio que falta es **una referencia que no dependa del método**: para cada
struct, un byte del VBIOS cuyo valor solo pueda ser ese. La tabla PCIe casi lo
era, y por casi la di por buena sin comprobar que `601` estaba mal.

Corregido: **antes de comparar struct contra VBIOS, buscar un valor que discrimine
y comprobar que el método lo reproduce.** Sin eso, comparar dos veces es
confirmarse a uno mismo.

## Frontier siguiente

**Resolver H1 frente a H2: la base real de `PowerPlayInfo`.**

Es un solo punto de arranque: `get_powerplay_table` (`process_pptables_v1_0.c:244`)
devuelve la base, y esa base viene de la cadena `usMasterDataTableOffset` +
`usTableOffset` del ROM. Si esa cadena da `0x9C0A` con el struct natural, entonces
**H1** y el VBIOS está empaquetado y el driver lee corrido toda la cabecera. Si da
`0x9C09`, entonces **H2** y mi base era la equivocada, el driver lee bien, y el
PowerTune se lee correctamente.

Es exactamente la medición que debí hacer antes de comparar nada, y su resultado
decide si `:2118` corre. Criterio de cierre: la dirección base que produce el
driver, y con ella `:2118` queda `PROVEN` o `REFUTED`.

Y una consecuencia que ya no puede esperar: si **H1**, el desfase es de 1 byte por
campo y afecta a **toda** la cabecera `PowerPlayInfo`, no solo al PowerTune. Eso
sería un hallazgo mayor que `601`, `505` y `602` juntos.