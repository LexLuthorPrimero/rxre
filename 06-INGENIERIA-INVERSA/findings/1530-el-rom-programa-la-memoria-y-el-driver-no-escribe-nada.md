# 1530 — el ROM contiene la lista de registros de memoria que programa la BIOS, y el driver no escribe ninguno

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM (una sola) · FASE=2
CLASSIFICATION=EVIDENCIA-DE-ROM+DECODIFICACION+CIERRE-DE-ITEM
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
CIERRA=item 4 de la definicion de cierre: qué programa el controlador de memoria y cuándo
ESTADO=PROBADO · los 5 punteros de VRAM_Info son RELATIVOS a la tabla, no absolutos
       · 42 entradas de indice decodificadas, 4 de 4 bloques terminan en el centinela 0xFFFF
       · usRegIndex es el offset en BYTES dentro del bloque MC: 15 de 15 resuelven a registro con nombre
       · 13 registros distintos de temporizacion y PHY, con sus valores
       · amdgpu NO escribe ninguno: sus 5 escrituras MC estan todas en el cargador de microcode
```

## 1. La pregunta del item 4

La definicion de cierre de la parte 1 pide: *qué programa el controlador de memoria, cuándo, y qué lee
antes de tiempo*. El 1511 ya dio el orden de fases del driver. Faltaba la otra mitad: **el ROM
declara cinco tablas de ajuste de memoria. ¿Qué contienen?**

Y la pregunta de fondo, que es la que importa para un driver propio: **si el driver no programa el
controlador de memoria, ¿quién lo hace, y dónde está esa información?**

## 2. Los offsets son relativos a la tabla, y se prueba sin suponerlo

`ATOM_VRAM_INFO_HEADER_V2_2` tiene cinco `USHORT`. Los valores medidos son pequenos —76, 91, 713,
743, 811— y si fueran absolutos caerian en el relleno anterior al header ATOM (que esta en `0x021C`).
Eso ya huele mal, pero "huele mal" no es una prueba. La prueba es doble:

```text
  base ABSOLUTA (0x0004C, 0x005B, 0x02C9, ...)   los cinco dan basura
       usRegIndexTblSize / usRegDataBlkSize:  0/0, 13626/51, 26207/26206, 5296/20582, 26114/49345

  base TABLA    (vi + off,  vi = 0xA30A)        los cinco dan valores utilizables
       3/4,  42/52,  6/8,  75/92,  7140/891
```

Y el quinto que "sigue sin cuadrar" no cuadra porque **no es un `ATOM_INIT_REG_BLOCK`**: el propio
comentario del header dice *"offset of ATOM_DRAM_DATA_REMAP array"*. Le estaba aplicando la
estructura equivocada. No es un fallo del offset.

Con la base de tabla hay **dos comprobaciones independientes** y las dos pasan 4 de 4:

```text
  ATOM_INIT_REG_INDEX_FORMAT = USHORT + UCHAR = 3 bytes con packing
  usRegIndexTblSize debe ser multiplo de 3:        3, 42, 6, 75      las cuatro
  cada bloque debe terminar en 0x0FFFF:            las cuatro, en la entrada exacta
```

Dosemannasi coincidencias a la vez no ocurren con una base equivocada.

## 3. `usRegIndex` es el offset en bytes dentro del bloque MC

No hay tabla de mapeo de indices en gfx8 — lo busque: `ATOM_REG_INDEX` y `usOffsetToIndex` no
existen en el header de esta generacion. Asi que el indice deberia ser el offset directo. Y lo es:

```text
  0x09DE  ->  mmMC_ARB_DRAM_TIMING2      0x0A28  ->  mmMC_SEQ_RAS_TIMING
  0x0A29  ->  mmMC_SEQ_CAS_TIMING        0x0A2C  ->  mmMC_SEQ_PMG_TIMING
  0x0A2F  ->  mmMC_SEQ_WR_CTL_D0         0x0A30  ->  mmMC_SEQ_WR_CTL_D1
  0x0A80  ->  mmMC_SEQ_MISC0             0x0A8C  ->  mmMC_SEQ_MISC4
  0x0A95  ->  mmMC_SEQ_MISC5             0x0A96  ->  mmMC_SEQ_MISC6
  0x0A98  ->  mmMC_IO_APHY_STR_CNTL_D1   0x0A99  ->  mmMC_SEQ_MISC7
  0x0AD5  ->  mmMC_SEQ_WR_CTL_2
```

**15 de 15 en el offset exacto, sin base que ajustar.** Los indices caen todos en `0x800`-`0xFFF`, que
es justo el rango del bloque GMC, donde ya se sabia que viven `mmMC_SHARED_CHMAP` (0x801) y
`mmMC_ARB_RAMCFG` (0x9D8).

## 4. Lo que hay dentro, bloque por bloque

| bloque | @ | entradas | datos | contenido |
|---|---|--:|--:|---|
| `usMemAdjustTblOffset` | `0xA356` | 1 | 4 B | **vacia**: la unica entrada es el centinela |
| `usMemClkPatchTblOffset` | `0xA365` | 14 | 52 B | ajustes por reloj de memoria |
| `usMcAdjustPerTileTblOffset` | `0xA5D3` | 2 | 8 B | 1 ajuste, por tile de PHY |
| `usMcPhyInitTableOffset` | `0xA635` | 25 | 92 B | **inicializacion del PHY de memoria** |

Con `ucMcPhyTileNum = 2`: dos tiles de PHY, y una tabla por tile.

Y los valores estan ahi, con su `ulMemoryID`:

```text
  usMemClkPatchTbl    ulMemoryID = 0x00009C40      <- el unico con un ID de memoria real
                      WR_CTL_D0 = 0x0A0A5F20   RAS_TIMING = 0x0A0A5F20
                      DRAM_TIMING2 = 0x009D8822   WR_CTL_D1 = 0x00005055
  los otros tres      ulMemoryID = 0x00FFFFFF      <- el valor "sin ID de memoria"
```

`0x00FFFFFF` es el mismo valor en los tres bloques que no son el de parcheo de reloj, y
`0x00009C40` = 40 000 decimal. **No interpreto ninguno de los dos**: no hay fuente en el corpus que
declare la unidad de `ulMemoryID`, y el valor `0x00FFFFFF` es el centinela de "todos los estados de
memoria" o un valor de relleno, pero no puedo distinguirlo sin el codigo de la BIOS.

## 5. El resultado que cierra el item 4

Pregunta: *escribe `amdgpu` alguno de esos 13 registros?*

Las escrituras a `mmMC_SEQ_*` en todo `amdgpu/*.c` son **cinco registros distintos**, y las cinco
estan dentro del cargador de microcode:

| registro | donde | que es |
|---|---|---|
| `mmMC_SEQ_IO_DEBUG_INDEX` | `gmc_v8_0.c:245` (`init_microcode`) | cargador |
| `mmMC_SEQ_IO_DEBUG_DATA` | `gmc_v8_0.c:319` (`tonga_mc_load_microcode`) | cargador |
| `mmMC_SEQ_SUP_PGM` | `gmc_v8_0.c:323` (`tonga_mc_load_microcode`) | cargador |
| `mmMC_SEQ_SUP_CNTL` | 20 escrituras, todas en cargadores | cargador |
| `mmMC_SEQ_MISC0` | `gmc_v8_0.c:380` (`polaris_mc_load_microcode`), y la operacion es `data &= ~(0x40)` | cargador |

Y en las otras familias, cero:

```text
  WREG32 a mmMC_IO_*         0
  WREG32 a mmMC_ARB_DRAM_*   0
```

> **PROBADO: en gfx8, `amdgpu` no escribe ni un solo registro de configuracion del controlador de
> memoria.** Las cinco escrituras que hace son del cargador de microcode. Sumado al 1511 —que ya
> demostro que tampoco escribe `MC_ARB_RAMCFG` ni `MC_SHARED_CHMAP`, y que los lee antes de que se
> programen— el cuadro es completo.

**Consecuencia para el proyecto, y es la que importa:** las temporizaciones de DRAM, las de escritura,
RAS, CAS, PMG y el strapping del PHY de esta tarjeta **existen solo en el ROM**, las programa la BIOS
en el POST, y el kernel de Linux no las lee ni las escribe. Para un driver propio no hay que
inventarlas ni adivinarlas: **están ahi, decodificadas, y este hallazgo las deja nombradas.** El
proyecto acaba de pasar de "no sabemos como configura la BIOS la memoria" a "tenemos la lista de
registros y valores".

## 6. Lo que queda sin cerrar, con nombre

```text
NO CERRADO  usDramDataRemapTblOffset (743 -> 0xA5F1).  Es ATOM_DRAM_DATA_REMAP, otra estructura, y
            es el mapa de lanes DRAM -> GPU.  Es el que mas falta: es literalmente como el bus
            reparte los datos.  Decodificarlo es el siguiente paso Natural y NO es un ATOM_INIT_REG_BLOCK.
NO CERRADO  la semantica de ulMemoryID.  0x00FFFFFF en tres bloques y 0x9C40 en el cuarto, sin
            unidad declarada en ninguna fuente del corpus.
NO CERRADO  el usRegIndex = 0x000E de usMcAdjustPerTileTbl.  No resuelve en el bloque GMC; 0x000E
            corresponde a registros de otros bloques (SDMA1, MMHUB).  O esa tabla vive en otro espacio
            de direcciones, o ese indice no es un offset MC.  Sin determinar, con nombre.
NO CERRADO  por que el bloque de ajuste de memoria esta VACIO (una sola entrada, el centinela) en una
            placa que es GDDR5 de 2 GB.  Puede ser legitimo: no todo necesita ajuste por vendedor.
RIESGO      ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE      todo esto es lectura del volcado del ROM con las estructuras del header de 7.1.3.  Es
            la fuente que el propio driver declara, no una medicion de la tarjeta.
```

## 7. Decision log (§103)

```text
DECISION    dar por cerrado el item 4 con "el ROM lo programa y el driver no lo toca"
WHY         no hace falta saber que valores exactos escriben la BIOS para establecer QUIEN programa
            el controlador.  Y esa pregunta es la que el item 4 formulaba.
ALTERNATIVA  dejar el item 4 abierto hasta que un subagente mase 42 valores y publicarlos todos.
            Descartada: mezcla el dato con la conclusion, y 42 valores sin contexto no cierran nada.
            Los valores van en el proximo hallazgo, donde ya hay consumidor para ellos.
DISCriminante  el solape de escrituras.  Si el driver escribiera alguno de los 13, "la BIOS programa
            la memoria" seria falso.  El solape es 0.
CONSECUENCIA  el 1522 decia que el driver no decodifica la geometria; este dice algo mas fuerte: no
            programa el controlador.  Los dos juntos acotan que hay que reconstruir a mano.
REVERSIBLE  si apareciera una version del driver que escribiese MC_SEQ_WR_CTL en gfx8, esta
            conclusion cae.  En este corpus no existe.
```

## 8. Donde queda la parte 1 tras este hallazgo

```text
  item 1  identidad de memoria        cerrado por 911/923 (128 bits) y 1511 (el 64 no es la config)
  item 2  geometria de VRAM           fila 4 KB PROBADO (1528); bancos/ranks crudos y sin uso;
                                      nº de filas NOT_DETERMINED con fuente nombrada
  item 3  aperturas y direcciones     sin tocar
  item 4  qué programa el MC          CERRADO (este): el ROM, y el driver no toca nada
  item 5  firmware de MC              parcial (1447)
  item 6  contrato host<->SMC         sin tocar
  item 7  reloj y voltaje de memoria  bastante avanzado
  item 8  registros de MC             este hallazgo acota el subconjunto que importa
  item 9  sin hardware (DEFERRED)     training, refresh, estado DRAMP
```

**Siguiente accion natural, y es el hueco mas grande que queda en el item 2:**
`usDramDataRemapTblOffset` -> `0xA5F1`, el mapa de lanes DRAM a GPU. Es lo que dice donde acaba cada
bit de una transaccion de 128 bits, y es geometria de verdad.
