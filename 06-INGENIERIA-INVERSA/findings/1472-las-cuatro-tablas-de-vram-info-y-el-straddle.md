# 1472 — las cuatro tablas de `VRAM_Info`: el arranque del controlador de memoria, y el straddle queda localizado

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-ROM+CONFIRMACION-DE-HALLAZGO-PROPIO
TRACK=STATIC(revkit/capturas/amdgpu_vbios.txt) · cero hardware · cero escrituras
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1419-*  CONFIRMADO, con la marca de fin explicada
         06-INGENIERIA-INVERSA/findings/1449-*  CONFIRMADO: 11 perfiles, ni uno mas ni menos
         06-INGENIERIA-INVERSA/findings/1406-*  CONFIRMADO y ampliado
ESTADO=PROBADO · usRegIndex ES el offset MMIO del MC en gfx8, sin tabla de indireccion
       · la tabla de MC PHY init programa 4 registros de STRADDLE con offsets PRESET
         y TODOS los bits de calibracion a cero: no ejecuta la busqueda, la deja puesta
       · los dos tiles de MC reciben valores DISTINTES: 0x00000000 y 0x00008200
       · la tabla de mem-adjust esta bien formada y semanticamente VACIA: cero escrituras
       · usDramDataRemapTblOffset NO es un ATOM_INIT_REG_BLOCK: son 68 bytes que encajan exactos
       · y el ACCESS_PLACEHOLDER confirma los 11 perfiles del 1449 en vez de contradecirlos
```

## 1. La convención, y una corrección que es mía

`atombios.h:7472-7483`, textual:

```c
typedef struct _ATOM_INIT_REG_INDEX_FORMAT{
    USHORT usRegIndex;            // MC register index
    UCHAR  ucPreRegDataLength;    // offset in ATOM_INIT_REG_DATA_BLOCK.saRegDataBuf
}ATOM_INIT_REG_INDEX_FORMAT;

typedef struct _ATOM_INIT_REG_BLOCK{
   USHORT                           usRegIndexTblSize;   //size of asRegIndexBuf
   USHORT                           usRegDataBlkSize;    //size of ATOM_MEMORY_SETTING_DATA_BLOCK
   ATOM_INIT_REG_INDEX_FORMAT       asRegIndexBuf[1];
   ATOM_MEMORY_SETTING_DATA_BLOCK   asRegDataBuf[1];
}ATOM_INIT_REG_BLOCK;
```

**No lleva cabecera común.** Los tamaños están en **+0** y **+2**, y la tabla de índices en +4.

> **Yo leí `usRegIndexTblSize` en `+2` durante la verificación** y me salió `52`, con un
> `usRegDataBlkSize` de 2607. Es la cuarta vez esta sesión que cuento bytes a partir de una
> suposición de layout en vez de del struct. Lo anoté porque el número que obtuve
> (`num_entries = 16`) era plausible y sin embargo estaba mal.

**El resto lo fija el propio driver** (`amdgpu/amdgpu_atombios.c:1477-1502`):

```c
reg_data = (ATOM_MEMORY_SETTING_DATA_BLOCK *)
        ((u8 *)reg_block + (2 * sizeof(u16)) + le16_to_cpu(reg_block->usRegIndexTblSize));
num_entries = (u8)(le16_to_cpu(reg_block->usRegIndexTblSize) /
                   sizeof(ATOM_INIT_REG_INDEX_FORMAT)) - 1;
while (i < num_entries) {
        if (format->ucPreRegDataLength & ACCESS_PLACEHOLDER)   /* 0x80 */
                break;
        ...
        i++;
}
reg_table->last = i;
```

O sea: `usRegIndexTblSize` es un **tamaño en bytes** que incluye la entrada de fin, el stride es
**3** (`#pragma pack(1)` en `atombios.h:191`), y el driver para en `ACCESS_PLACEHOLDER`.

## 2. `usRegIndex` ES el offset MMIO — y hay una pruebaNegative que lo fija

La prueba es que los índices **salen con nombres coherentes sin ninguna tabla de indirección**:

```text
índice 0x0A28 -> mmMC_SEQ_RAS_TIMING      = 0xa28   (gmc_8_1_d.h:740)
índice 0x0A2C -> mmMC_SEQ_CAS_TIMING      = 0xa2c
índice 0x0A2F -> mmMC_SEQ_WR_CTL_D2       = 0xa2f
índice 0x0AD5 -> mmMC_SEQ_MISC_TIMING2    = 0xad5
```

Los 13 índices de la tabla ya cerrada resuelven a un **conjunto coherente de timings DRAM**
(`MC_SEQ_WR_CTL_D0/D1/D2`, `PMG_TIMING`, `RAS_TIMING`, `CAS_TIMING`, `MISC_TIMING`,
`MISC_TIMING2`, `MISC1/3/8`, `ARB_DRAM_TIMING/2`). Un stride equivocado no produce eso.

**Y un negativo con el mismo peso:**.parseados 1122 defines `mm` de `gmc_8_1_d.h`, el rango es
`0x0500..0xF9CD` — **no hay ninguno por debajo de `0x500`**. Por tanto los índices
`0x0000-0x000F` **no son offsets MMIO** y pertenecen a otro espacio de nombres. Eso es un
`PROBADO` por ausencia con alcance explícito, no un `NOT_FOUND`.

## 3. `ACCESS_PLACEHOLDER`: CONFIRMA el hallazgo 1449

El subagente chloroplasto esto tocó un hallazgo ya cerrado y lo marcó. Lo verifiqué con el
parseo exacto del driver:

```text
bloque @ 0xA365   usRegIndexTblSize=42 (=14 slots de 3)   usRegDataBlkSize=52
num_entries = 42/3 - 1 = 13

  e  offset    usRegIndex  len    ACCESS_PLACEHOLDER(0x80)
  0  0xA369    0x0A2F     0x04   no
  1  0xA36C    0x0A30     0x00   no     (len&0xF == 0 => VALUE_SAME_AS_ABOVE)
  2  0xA36F    0x0AD5     0x04   no
  ...                                      (entradas 2..10 iguales)
 11  0xA38A    0x09DD     0x84   SI   <-- el driver para aqui
 12  0xA38D    0x09DE     0x84   SI

  => reg_table->last = 11,  11 registros almacenados (entradas 0..10)
```

Y los **11 grupos** de datos, con paso `usRegDataBlkSize = 52`:

```text
 grupo  cabecera@   memID  clockRange (10 kHz)   MHz
    0   0xA393        0           40000          400
    1   0xA3C7        0           80000          800
    2   0xA3FB        0           90000          900
    3   0xA42F        0          100000         1000
    4   0xA463        0          112500         1125
    5   0xA497        0          125000         1250
    6   0xA4CB        0          137500         1375
    7   0xA4FF        0          150000         1500
    8   0xA533        0          162500         1625
    9   0xA567        0          175000         1750
   10   0xA59B        0          200000         2000
   siguiente dword: 0x00000000  = END_OF_REG_DATA_BLOCK
```

> **Once registros y once grupos, uno por registro.** La lista del hallazgo 1419 y el `techo =
> 1500` del 1449 quedan **CONFIRMADOS con la marca de fin del driver**, no contradichos.
>
> Y queda un detalle limpio: `usRegDataBlkSize = 52 = 4 + 4×12`, o sea que el BIOS reserva
> **12** huecos de valor, y el driver sólo lee 11. **El duodécimo existe y nunca se lee.**

## 4. `MC PHY init` @ 0xA635 — los cuatro registros de STRADDLE

24 entradas (la 24 es `usRegIndex = 0xFFFF`, `END_OF_REG_INDEX_BLOCK`). Un grupo, cabecera
`0x00FFFFFF` ⇒ `memID=0`, `clockRange = CLOCK_RANGE_HIGHEST` ⇒ **aplicar sin restricción**.
Diez índices resuelven a MMIO:

| e | índice | registro (`gmc_8_1_d.h`) | valor |
|---|---|---|---|
| 0 | `0x0A80` | `mmMC_SEQ_MISC0` :881 | `0x50402172` |
| 1 | `0x0A8C` | `mmMC_SEQ_MISC4` :899 | `0xe000c228` |
| 2 | `0x0A95` | `mmMC_SEQ_MISC5` :900 | `0xa26abc58` |
| 3 | `0x0A96` | `mmMC_SEQ_MISC6` :901 | `0x308ca00d` |
| 4 | `0x0A99` | `mmMC_SEQ_MISC7` :902 | `0x7005e000` |
| 5 | `0x0A82` | `mmMC_SEQ_RESERVE_M` :885 | `0x6103405b` |
| 6 | `0x0A74` | `mmMC_IO_PAD_CNTL_D0` :834 | `0x00000000` |
| 7 | `0x0A75` | `mmMC_IO_PAD_CNTL_D1` :835 | `0x001b0000` |
| 20 | `0x0A4E` | **`mmMC_IO_DPHY_STR_CNTL_D0`** :789 | `0x00934934` |
| 21 | `0x0A54` | **`mmMC_IO_DPHY_STR_CNTL_D1`** :798 | `=prev` |
| 22 | `0x0A97` | **`mmMC_IO_APHY_STR_CNTL_D0`** :790 | `0x0002f75d` |
| 23 | `0x0A98` | **`mmMC_IO_APHY_STR_CNTL_D1`** :799 | `=prev` |

Las entradas 8–19 llevan índices `0x00,0x01,…,0x0F` con `len = 0x44`: espacio de nombres bajo,
`NOT_RESOLVED` (y por §2, **definitivamente no MMIO**).

### 4.1 Los offsets de straddle, y por qué esto responde a la pregunta del techo de reloj

```text
mmMC_IO_DPHY_STR_CNTL_D0 = 0x00934934
  PSTR_OFF_D = 52    NSTR_OFF_D = 36
  PSTR_OFF_S = 52    NSTR_OFF_S = 36
  USE_D_CAL = USE_S_CAL = CAL_SEL = LOAD_D_STR = LOAD_S_STR = AUTO_LD_STR = 0

mmMC_IO_APHY_STR_CNTL_D0 = 0x0002f75d
  PSTR_OFF_A = 29    NSTR_OFF_A = 29
  PSTR_OFF_D_RD = 47   NSTR_OFF_D_RD = 0
  USE_A_CAL = USE_D_RD_CAL = CAL_SEL = LOAD_A_STR = LOAD_D_RD_STR = 0
```

> **Los offsets de straddle están puestos, y todos los bits que lanzarían la calibración están
> a cero.** `USE_*_CAL = 0`, `CAL_SEL = 0`, `AUTO_LD_STR = 0`.
>
> Eso responde a la pregunta que el proyecto tenía abierta —"¿qué registros determinan el reloj
> de memoria alcanzable?"— con una respuesta que **no es la que se esperaba**: el BIOS **no
> ejecuta la búsqueda**. Presetea cuatro offsets y deja la búsqueda para otro agente.
>
> **`NOT_DETERMINED`:** quién la ejecuta. Casi con seguridad el firmware de SMU o PSP, dado
> que `polaris12` no tiene MP1 y `smu8_hwmgr.c` **no menciona** `VRAM_Info`, `mc_reg_table` ni
> `retrain` en ninguna línea. No lo afirmo: lo nombro como la única vía que queda.

Y un detalle con explicación propia: los pares `D0`/`D1` se fuerzan **idénticos** porque la
entrada `D1` tiene `len & 0xF == 0`, que es `VALUE_SAME_AS_ABOVE`. **El BIOS trata las dos
instancias de memoria como simétricas para straddle.** Eso es una afirmación sobre la topología
física, y sale del dato.

## 5. Los dos tiles de MC reciben valores DISTINTES

`@0xA5D3`, 2 entradas (la segunda es el end mark), **dos grupos** de 8 bytes:

| grupo | cabecera@ | `memID` | `clockRange` | valor |
|---|---|---|---|---|
| 0 | `0xA5DD` | 0 | `0xFFFFFF` | `0x00000000` |
| 1 | `0xA5E5` | **1** | `0xFFFFFF` | **`0x00008200`** |

**El campo `memID` se está usando como número de tile del PHY de MC.** Eso es exactamente lo que
dice el comentario de `ucMcPhyTileNum` en `atombios.h:8039`, y es la primera vez que se ve
funcionar en los datos.

- Índice único: `0x000E`, `len = 0x44` — espacio bajo, `NOT_RESOLVED`.
- Ese índice **no aparece** en la tabla de PHY (que lleva `0,1,2,3,4,5,9,A,B,C,D,F`), así que
  esta tabla es **la única fuente** de un valor para el hueco 14.
- Tile 0 explícitamente `0x00000000`, tile 1 `0x00008200` = bits 9 y 15.
- **Significado de `0x00008200`: `NOT_DETERMINED`.** No hay definición de campo para el índice
  `0x000E` en ningún sitio del árbol.

> **Y una hipótesis que marco como tal:** el espacio de índices `0x00-0x0F` son 16 huecos, que
> casan con los 16 carriles de byte de una interfaz de 128 bits, y `atombios.h:8032` llama a la
> tabla hermana *"Per Byte Offset Preset Settings"*. Que el bit 15 esté activo en el valor del
> tile 1 encajaría con un mapa carril-14 → bit-15. **Nada en este corpus lo establece.**

## 6. `usDramDataRemapTblOffset` NO es un `ATOM_INIT_REG_BLOCK`

Leída como tal da `usRegIndexTblSize = 0x1BE4` y `usRegDataBlkSize = 0x037B`. La hipótesis
falla en su propia cabecera.

Es un array **`ATOM_DRAM_DATA_REMAP[ucMcPhyTileNum]`** (`atombios.h:8044-8056`): 2×`UCHAR` +
**8**×`ULONG` empaquetado = **34 bytes**, × `ucMcPhyTileNum = 2` = **68 bytes**, de `0xA5F1` a
`0xA634`. **Cero holgura, cero solape**, y termina justo donde empieza la siguiente tabla.

```text
tile 0 @0xA5F1   ChRemap (0xE4, 0x1B)
   ch0 masks B0..B3: 0x00D1037B  0x00DEC650  0x0008B97E  0x00DEC2D0
   ch1 masks B0..B3: 0x0009997E  0x00DEC650  0x0008B97E  0x00DEC2D0
tile 1 @0xA613   ChRemap (0xE4, 0x1B)
   ch0 masks B0..B3: 0x0009997E  0x00DEC650  0x0008B97E  0x00DEC2D0
   ch1 masks B0..B3: 0x0009997E  0x00DEC650  0x0009997E  0x007E90A6
```

**Granularidad: por canal.** Cada tile recibe un código de remapeo de bytes por canal y cuatro
máscaras de 32 bits por canal — 128 bits de máscara por canal, dos canales por tile. Los
`ucByteRemapCh0/1` son idénticos en los dos tiles; **las máscaras no**: difieren en `ch0 B0` y en
`ch1 B2/B3`.

**`NOT_DETERMINED`:** qué bit de máscara va a qué línea DQ física. Y hay una tensión aritmética
que no sé resolver: 2 canales × 128 bits = 256 posiciones de máscara para un bus de 128 bits, así
que **no son un mapa DQ 1:1**.

## 7. La tabla de mem-adjust está vacía — y eso es un dato

`@0xA356`, `3, 4`: la tabla de índices son 3 bytes, es decir **una entrada, y es
`usRegIndex = 0xFFFF`** ⇒ `num_entries = 0`. El área de datos es un `0x00FFFFFF` y luego el
`0x00000000` de fin.

> **`usMemAdjustTblOffset` es "memory vendor specific MC adjust setting"** (`atombios.h:8030`).
> Esta tarjeta **no declara ningún ajuste de MC específico de su fabricante de memoria.**
> Coherente con `ucNumOfVRAMModule = 1`, y coherente con que la parte sea Hynix sin
> parametrización propia.

## 8. Qué consume el driver, y el aviso obligatorio

| campo | consumidor en los ficheros presentes |
|---|---|
| `usMemClkPatchTblOffset` | **SÍ** — `amdgpu_atombios.c:1477`; `ppatomctrl.c:161,202` |
| `usMcPhyInitTableOffset` | **NINGUNO** |
| `usMcAdjustPerTileTblOffset` | **NINGUNO** (sólo comentarios de cabecera) |
| `usDramDataRemapTblOffset` | **NINGUNO** |
| `usMemAdjustTblOffset` | **NINGUNO** |
| `ucMcPhyTileNum` | **NINGUNO** |

Ruta de llamada: `polaris10_smumgr.c:2568 polaris10_initialize_mc_reg_table` → registrado como
`.initialize_mc_reg_table` en `polaris10_smumgr.c:2704`; `polaris10_smumgr.o` **se compila**
(`smumgr/Makefile:27`); la tabla de ops entra por `hwmgr/smu7_hwmgr.c:55`.
Y `atomctrl_initialize_mc_reg_table_v2_2` (`ppatomctrl.c:173`) declara
`ATOM_VRAM_INFO_HEADER_V2_2` — **exactamente la versión de esta tarjeta** — y lee **sólo**
`usMemClkPatchTblOffset` (`ppatomctrl.c:202`).

**Aviso obligatorio: este corpus está podado.** `PP_HWMGR_POLARIS10` no aparece en ningún sitio
y no hay tabla de despacho por versión de smumgr. Por tanto *"ningún consumidor aquí"* significa
*"ningún consumidor en los ficheros presentes"*, **no** "upstream ignora estas tablas". Y si
`699f` llega o no a la tabla de ops de `polaris10` es `PARTIAL` desde estos ficheros.

Un detalle que refuerza la lectura: `atomfirmware.h:3255` y `:3382` etiquetan ese mismo campo como
**`// reserved for now`** en las cabeceras v2.x antiguas. **El propio upstream lo marca
reservado.**

## 9. Procedencia

```text
fichero  revkit/capturas/amdgpu_vbios.txt   58 880 B
structs  include/atombios.h:7472-7483   ATOM_INIT_REG_INDEX_FORMAT (3 B, pack(1)), ATOM_INIT_REG_BLOCK
         include/atombios.h:7485-7488   END_OF_REG_INDEX_BLOCK 0x0ffff, END_OF_REG_DATA_BLOCK 0,
                                        ATOM_INIT_REG_MASK_FLAG 0x80, CLOCK_RANGE_HIGHEST 0x00ffffff
         include/atombios.h:7498        ACCESS_PLACEHOLDER 0x80
         include/atombios.h:8044-8056   ATOM_DRAM_DATA_REMAP  (2*UCHAR + 8*ULONG = 34 B)
         include/asic_reg/gmc/gmc_8_1_d.h:740-915  nombres de registro
driver   amdgpu/amdgpu_atombios.c:1477-1502   el bucle que manda
         pm/powerplay/hwmgr/ppatomctrl.c:46-91,110,116,161,173-205
         pm/powerplay/smumgr/polaris10_smumgr.c:2568,2704
```

```text
ESTADO=PROBADO · usRegIndex ES el offset MMIO del MC en gfx8.  Sin tabla de indireccion: indice
       0x0A28 resuelve a mmMC_SEQ_RAS_TIMING=0xa28 y los 13 de la tabla cerrada a un conjunto
       coherente de timings DRAM.  Y gmc_8_1_d.h no tiene ningun mm por debajo de 0x500, asi que
       los indices 0x0000-0x000F NO son MMIO
CONFIRMADO  1419 y 1449.  ACCESS_PLACEHOLDER en las entradas 11 y 12 => reg_table->last = 11 =>
       11 registros; y hay exactamente 11 grupos con clockRange 400..2000.  El BIOS reserva 12
       huecos de valor (52 = 4+4*12) y el driver lee 11
NUEVO  la tabla de MC PHY init programa 4 registros de STRADDLE con offsets PRESET y TODOS los
       USE_*_CAL / CAL_SEL / AUTO_LD_STR a cero: el BIOS NO ejecuta la busqueda de straddle
NUEVO  mmMC_IO_PAD_CNTL_D1 = 0x001b0000: CK_AUTO_EN=1, VREFI_SEL=22, VREFI_EN=0.  Sin ningun
       registro DLL en la tabla (gmc_8_1_d.h no tiene ninguno con ese nombre)
NUEVO  los dos tiles de MC reciben valores DISTINTES: 0x00000000 y 0x00008200, y el campo memID
       se usa como numero de tile, tal como documenta atombios.h:8039
NUEVO  usDramDataRemapTblOffset NO es ATOM_INIT_REG_BLOCK: son ATOM_DRAM_DATA_REMAP[2],
       34 B x 2 = 68 B, de 0xA5F1 a 0xA634, con cero holgura
NUEVO  usMemAdjustTblOffset esta bien formada y SEMANTICAMENTE VACIA: cero escrituras de
       registro.  Esta tarjeta no declara ajuste de MC especifico de su fabricante de memoria
NOT_DETERMINED  quien ejecuta la busqueda de straddle (casi con seguridad SMU/PSP, pero no se
       afirma).  El significado de los indices 0x0000-0x000F y del valor 0x00008200.  Que bit de
       mascara del remap va a que linea DQ, con la tension de 256 posiciones para 128 bits
LIMITE  tres de las cuatro tablas no las consume el driver de este kernel.  Si el BIOS las pone
       ahi, es porque ALGUIEN mas las lee; lo mas probable es el firmware de MC/SMU
RIESGO  ninguno.  CERO escrituras, cero hardware
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active
Siguiente  1) la busqueda de straddle: es el unico sitio donde "reloj de memoria alcanzable"
           podria decidirse, y el BIOS solo pone los presets.  Las tres tablas que el driver no
           lee son la pista de quien lo hace
         2) MC_InitParameter y ASIC_ProfilingInfo: el otro subagente esta sobre ellas, y son
           bloques que el driver de este kernel ignora, o sea que el ROM es la unica fuente
         3) 0x0000-0x000F es un espacio de nombres de 16 entradas que parece ser "por carril de
           byte" (atombios.h:8032 lo dice).  Si se nombra, cae el significado de 0x00008200
```

## 10. Lo que esto añade al objetivo

El objetivo es un driver para esta tarjeta. Este trabajo acaba de decir **dónde el hardware deja
de medir por sí solo**: el BIOS pone cuatro offsets de straddle y no busca. El reloj de memoria
alcanzable —el techo de 1500 MHz del hallazgo 1449— **no lo decide esta tabla**, y quien lo
decide no es el driver.

Eso separa dos cosas que el proyecto tenía mezcladas: *qué es alcanzable* lo decide el
firmware de la memoria, y *qué registers hay que tocar* lo decide el driver. **Es un buen
resultado, aunque sea un resultado negativo sobre dónde mirar.**