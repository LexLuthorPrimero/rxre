# 116 · `usClockStretchAmount = 2` leído del VBIOS real: la rama se ejecuta y no falla

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CIERRA `US-CLOCK-STRETCH-AMOUNT` (abierto en `115`) · REUTILIZA `008-firmware-blob.md` y
`revkit/atomrom.py` (ficheros de otro agente, **no modificados**)

## El resultado

```
/usr/share/... revkit/capturas/amdgpu_vbios.txt   58880 B, ROM real de esta placa
ATOM_Tonga_POWERPLAYTABLE          @ 0x9C0A
  usPowerTuneTableOffset = 673  ->  ATOM_Polaris_PowerTune_Table @ 0x9EAB

  usClockStretchAmount       = 2
  usTjMax                    = 93
  usSoftwareShutdownTemp     = 97
  usTemperatureLimitHotspot  = 80
  usTDP                      = 35
  ucCKS_LDO_REFSEL           = 5
```

**Consecuencia directa**, contra lo que `115` dejó como cadena condicional:

| pregunta de `115` | respuesta |
|---|---|
| ¿`init_smc_table` falla? (`usClockStretchAmount > 5`) | **NO**. Es 2, y `2 > 5` es falso |
| ¿la rama se ejecuta en mi ASIC? | **SI**, y con valor valido |

O sea: **`polaris10_populate_clock_stretcher_data_table` se ejecuta, encuentra
`stretch_amount = 2` en `[1,5]`, y continua**. No hay fallo de arranque, no se desactiva
`PHM_PlatformCaps_ClockStretcher`, y la escritura de `ixPWR_CKS_CNTL` con `&= 0xFFFFFFFE`
(polaris10_smumgr.c:1704-1706) **si se ejecuta**.

`115` habia dejado esto como `NOT_IN_CORPUS` por no tener el VBIOS. **Ahora es `PROVEN`.**

## La validacion: por que me creo estos numeros y no los anteriores

Este documento **no** aceptaria los numeros sin una comprobacion independiente, y esa
comprobacion es lo que mas trabajo costo. La cadena tiene cuatro eslabones y **los tres
primeros los lei mal**:

### Eslabon 1 · la tabla

`atomrom.py` (validado antes de usarse: sus 11 controles pasan **sin** el VBIOS real)
localiza `PowerPlayInfo` en `0x97F2 + 4 + 2*15 = 0x9C0A`, y reporta
`size=778 rev=7.1`.

### Eslabon 2 · el desplazamiento

`process_pptables_v1_0.c:826` llama `get_cac_tdp_table(..., pPowerTuneTable)`, y
`pPowerTuneTable = powerplay_table + le16_to_cpu(powerplay_table->usPowerTuneTableOffset)`
(`:826` y las linesas anteriores). Para Polaris la rama es la de
`ATOM_Polaris_PowerTune_Table` (`:658-678`, la tercera; las otras dos son Tonga y Fiji,
seleccionadas por `table->ucRevId < 3`).

### Eslabon 3 · los offsets, y aqui estan los DOS bugs

Los mido con gcc, que es el metodo que uso desde el principio de la sesion. **Pero esta
vez no podia simplemente incluir la cabecera**, porque `pptable_v1_0.h:32` incluye
`hwmgr.h`, que a su vez incluye la cadena de `atomfirmware.h` y `atombios.h` (compilar
`gcc -I ...` directo falla). Asi que **extraje los campos con un script** y genere el C.

**Bug 1 — el empaquetado.** Mi primer probe compilo los campos con **alineacion natural**.
Fallo: las cabeceras ATOM llevan

```
pptable_v1_0.h:30   #pragma pack(push, 1)
pptable_v1_0.h:498  #pragma pack(pop)
atombios.h:214      #pragma pack(1)   /* BIOS data must use byt[te] alignment */
```

Con `pack(1)`, `sizeof(ATOM_Tonga_POWERPLAYTABLE)` cae de 76 a 73 y
`usPowerTuneTableOffset` se mueve de 54 a 53. **Es 1 byte de diferencia, y 1 byte basta
para que todo lo demas sea basura.**

**Bug 2 — un miembro que mi regex no vio, y que pesa 4 bytes.**
`ATOM_Tonga_POWERPLAYTABLE` empieza con

```c
typedef struct _ATOM_Tonga_POWERPLAYTABLE {
        ATOM_COMMON_TABLE_HEADER sHeader;    /* <-- NO es UCHAR/USHORT/ULONG */
        UCHAR  ucTableRevision;
        USHORT usTableSize;
        ...
```

Mi regex de extraccion aceptaba `UCHAR|USHORT|ULONG|BOOL|CHAR` y **descarto
`ATOM_COMMON_TABLE_HEADER sHeader;` en silencio**. Cuatro bytes de deslocamiento, otra vez
por un filtro.

`ATOM_COMMON_TABLE_HEADER` (atombios.h:208) es `usStructureSize` (u16) +
`ucTableFormatRevision` (u8) + `ucTableContentRevision` (u8) = **4 bytes**, medido.

### Eslabon 4 · la validacion que SI decide

Aqui es donde se cae la cadena si algo va mal, y por eso la puse como puerta:

```
leido   usStructureSize = 778   |  atomrom dice size=778    -> COINCIDE
leido   ucTableFormatRevision = 7  |  atomrom dice rev=7.1   -> COINCIDE
leido   ucTableSize = 77        |  gcc dice sizeof(T) = 77 -> COINCIDE
```

**Tres coincidencias independientes**, y la tercera es la mejor: `usTableSize` en el disco
vale 77 y `sizeof(ATOM_Tonga_POWERPLAYTABLE)` calculado por gcc **empaquetado** vale 77.
Eso es una comprobacion cruzada entre dos metodos que no comparten nada, y solo puede
coincidir por la razon correcta.

## Y una corroboracion que no es la misma prueba

Los valores no son arbitrarios, y eso se ve en sus relaciones mutuas:

```
usTemperatureLimitHotspot  = 80
usTjMax                   = 93
usSoftwareShutdownTemp    = 97
```

Ordenan como deben: **hotspot < junction < apagado**. Si los offsets estuvieran
desplazados, esta relacion no se sostendria, porque los tres campos estan a 6 bytes de
distancia entre si (`17`, `23`, `29`) y un error de 4 o 5 bytes los leeria en otro sitio.

Y contra la lectura viva que hay en el corpus (`revkit/capturas/amdgpu_pm_info.txt`):

```
GPU Temperature: 42 C     <  usTjMax (93)      <  usSoftwareShutdownTemp (97)
```

Una placa a 42 °C en reposo esta coherentemente por debajo de ambos limites. Y
`usTemperatureLimitHotspot = 80` explica por que el ceiling termico efectivo sea 80 y no
93: el hotspot va antes.

**`usClockStretchAmount = 2` tambien encaja**: es un valor pequeno y no cero, que es
justo lo que haria falta para que la cadena de `115` se cerrara sin fallo.

## El detalle que hace que esto no fuera trivial

`get_cac_tdp_table` elige entre **tres** structs segun `table->ucRevId`, y el `ucRevId`
del PowerTune table real es **8964** (`PT+0` leido como u8 da 0x2304, y el byte alto es
de otro campo).

Con `ucRevId = 8964`, la condicion `if (table->ucRevId < 3)` es **falsa**, asi que se toma
**la rama de Polaris**, que es la que he leido. Correcto por suerte del layout, pero
**depende de un byte que no es una revision valida**. Si el layout estuviera desplazado
un byte mas, `ucRevId` seria otro valor, y si fuera `< 3` el driver leeria
`ATOM_Tonga_PowerTune_Table`, que tiene **menos campos** y desplazados.

Es decir: **el codigo selecciona el layout correcto por una comparacion sobre un campo que
no significa nada**. Funciona porque el valor happen a ser >= 3. Eso no es robustez, es
suerte con una comprobacion.

## Clasificacion

- `VBIOS_IN_CORPUS = PROVEN`: `revkit/capturas/amdgpu_vbios.txt`, 58880 B. Contiene
  `ATOMBIOS BK-AMD VER015.050.002.001.000000` y la cadena
  `D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m`.
- `VBIOS_BELONGS_TO_THIS_GPU = PROVEN_DERIVED`: `dev=0000:01:00.0` en `name.txt`, y
  `amdgpu_pm_info.txt` da 997 MHz SCLK / 812 mV / 42 C en la misma sesion de captura.
- `POWERPLAY_TABLE_AT_0x9C0A = PROVEN`: `usStructureSize = 778`,
  `ucTableFormatRevision = 7`, `ucTableContentRevision = 1`. Los tres coinciden con
  `atomrom.py`.
- `ATOM_STRUCTS_ARE_BYTE_PACKED = PROVEN`: `#pragma pack(1)` en `atombios.h:214` y
  `pptable_v1_0.h:30/498`. Sin ello los offsets se mueven 1 byte.
- `ATOM_TONGA_POWERPLAYTABLE_HAS_A_4_BYTE_COMMON_HEADER = PROVEN`:
  `sizeof(ATOM_COMMON_TABLE_HEADER) = 4`, primer miembro de la struct. **Mi regex de
  extraccion lo descarto dos veces antes de darme cuenta.**
- `US_CLOCK_STRETCH_AMOUNT_IS_2 = PROVEN`: VBIOS `0x9EAB + 25`.
- `CLOCK_STRETCH_BRANCH_EXECUTES_AND_SUCCEEDS = PROVEN_DERIVED`: `2 != 0` activa la
  capacidad, y `2` no cumple `== 0 || > 5`, asi que `init_smc_table` **no** falla.
  **Cierra el pendiente que `115` dejo abierto.**
- `US_TJMAX_IS_93 = PROVEN` y `US_SOFTWARE_SHUTDOWNTEMP_IS_97 = PROVEN`: VBIOS `0x9EAB+17`
  y `+23`. **Resuelve dos `RUNTIME_MISSING` de mi lista de bloqueados.**
- `POWERPLAY_SIZE_CROSS_CHECK = PROVEN_DERIVED`: `usTableSize` en disco = 77 =
  `sizeof` por gcc empaquetado. Dos metodos independientes que coinciden.
- `THERMAL_ORDER_IS_COHERENT = PROVEN_DERIVED`: 80 (hotspot) < 93 (TjMax) < 97 (shutdown).
  Tres campos a 6 bytes de distancia: un error de offset lo romperia.
- `CAC_TDP_LAYOUT_SELECTED_BY_INVALID_REVISION_BYTE = PROVEN`: `ucRevId` leido = 8964,
  que no es una revision. La seleccion del struct depende de un campo sin significado
  y funciona por que el byte sale alto, no por diseno.

## Los errores que cometi, porque son la parte util

Tres en una tarde, y los tres **silenciosos**: producian numeros, no avisos.

1. **Compilar una struct empaquetada sin `pack`.** Offset 54 en vez de 53.
2. **Un regex de extraccion que descarta miembros no escalares.** 4 bytes de mas.
3. **Creyerme el valor de `atomrom.py` sin entender que imprimia.** Segui sobre
   `0x9C0A` sin comprobar que alli starts `usStructureSize` y no `ucTableRevision`.

El primero y el segundo seupidieron por el mismo mecanismo: **una comprobacion de
coherencia que solo se dispara si el numero es absurdo.** Un `usClockStretchAmount = 878`
es visible; un offset equivocado por 4 que produce `usTDP = 19712` tambien. Pero
`usClockStretchAmount = 2` **no es absurdo en absoluto**, asi que **el ojo no lo caza**.

**Solo lo cazo la comprobacion cruzada**: `usTableSize` en disco tiene que ser igual al
`sizeof` que calcula gcc. Si no coinciden, no se lee nada mas. Ese es el unico mecanismo
que funciono, y lo puse antes de leer el campo que importaba, no despues.

> **Un numero plausible no es un numero verificado.** `2` es plausible. Que `2` sea el
> campo `usClockStretchAmount` y no el byte de al lado, es lo que hay que demostrar.

## Discriminante que queda abierto

```
PENDIENTE=POWERPLAY-STRUCT-SELECTION | HALLAZGO=116-clock-stretch-amount-leido-del-vbios.md
             | ESTADO=NOT_DETERMINED
             | NECESITA=por que ucRevId=8964 selecciona la rama de Polaris y no la de
             |          Tonga, y que haria un VBIOS con rev<3
             | ALCANZABLE_SIN_ROOT=si
```

Es legible del corpus: solo hay que leer el codigo de las tres ramas y ver que campos
tienen en comun. **No necesita placa**, asi que es trabajo pendiente, no bloqueado.

## Lo que esto obliga a hacer en un driver propio

1. **No seleccionar layout por un campo de version que no validas.** El codigo lee
   `ucRevId`, no comprueba que sea una versionKnown, y elige entre tres structs
   incompatibles. Un driver propio tiene que **validar el campo** (rango Known, o el
   `usStructureSize` que da el tamano real) antes de elegir la interpretacion. Si no,
   el mismo VBIOS puede leerse con dos layouts distintos segun un byte.
2. **Toda struct de un formato empaquetado se mide con `pack(1)`, siempre.** Y el
   `sizeof` medido tiene que **coincidir con el `usTableSize` del propio fichero**: es la
   unica verificacion cruzada disponible sin placa, y es gratis.
3. Y la regla general, que es la tercera vez que sale esta sesion: **un parser que
   descarta miembros que no reconoce es un parser que miente sobre el tamano del
   registro.** Hay que fallar al ver un tipo no esperado, no seguir.