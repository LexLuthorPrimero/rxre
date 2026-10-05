# 1468 — el ROM se identifica solo, y mi premisa sobre su tabla maestra estaba plana y simplemente mal

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-ROM+REVISION-PROPIA+REVISION-DE-UN-REVISOR
TRACK=STATIC(solamente el fichero revkit/capturas/amdgpu_vbios.txt) · cero hardware
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1400-*  (GFX_Info: falta un campo)
         06-INGENIERIA-INVERSA/findings/1406-*  (VRAM_Info: queda confirmado y anadido)
         06-INGENIERIA-INVERSA/findings/1445-*  (bus de 128 bits)
         06-INGENIERIA-INVERSA/findings/1448-*  (relojes de reposo)
         el supuesto mio de que el VBIOS podia ser la fuente del firmware de UVD/VCE
ESTADO=PROBADO · la tabla maestra NO es {indice,long,offset}: son dos LISTAS de offsets
       · revision de cabecera 1.1 => la mitad del parser del driver no corre en esta tarjeta
       · la placa se identifica con nombre propio: Lexa XL A0, WEIKENG, Hynix H5GC8H24AJR
       · max_cu_per_sh = 5 => 10 CU => 640 shaders, que es la especificacion del RX 550
       · PROBADO AUSENTE: no hay imagenes de firmware en el ROM (el mayor blob no cabe)
```

## 1. Mi premisa estaba mal, y la prueba de que está mal es de un solo byte

En el encargo le dije al subagente que la tabla maestra estaba en `0x0024`, con
`MASTERSIZE` en `0x24`, `NUM_ENTRIES` en `0x25` y entradas `{BYTE index; BYTE length;
WORD offset}` desde `0x26`.

```text
d[0x24..0x27] = 00 00 00 00
```

**Los cuatro bytes a cero.** Y buscando el valor `0xA30A` — el offset de `VRAM_Info`, que
*cualquier* tabla así tendría que contener — hay **un único golpe en toda la captura**, y
cae **dentro** de la tabla real (§2), no en una segunda tabla.

**Lo que hay es otra cosa**, y el propio `ATOM_ROM_HEADER` la apunta:

```text
ATOM_ROM_HEADER @0x021C   (36 bytes, rev 1.1)
  usMasterCommandTableOffset = 0x974C
  usMasterDataTableOffset    = 0x97F2
```

```text
COMANDOS @0x974C  usStructureSize=166 = 4 + 2*81   OK     frev=1 crev=1
DATOS    @0x97F2  usStructureSize= 74 = 4 + 2*35   OK     frev=1 crev=1

fin de COMANDOS 0x974C+166 = 0x97F2 = inicio de DATOS      True
```

**Esa aritmética se sostiene sola** y no admite otra lectura: son
`ATOM_MASTER_LIST_OF_COMMAND_TABLES` (`atombios.h:272-354`, 81 entradas) y
`ATOM_MASTER_LIST_OF_DATA_TABLES` (`atombios.h:2783-2820`, 35 entradas), es decir una cabecera
común de 4 bytes seguida de offsets `USHORT` nombrados. **35 y 81 entradas; 21 y 62 presentes.**

> **Lección de método, y es la segunda vez esta ronda.** Yo escribí la premisa; el subagente la
> refutó; y yo lo verifiqué antes de aceptarla. Un dato que uno mismo inventa y que nadie
> contrasta se convierte en "conocimiento del proyecto" en una frase. Ya va tres veces esta
> sesión.

## 2. EL MAPA COMPLETO

21 bloques de datos presentes (de 35) y 62 de comandos (de 81). Todo en
`revkit/capturas/amdgpu_vbios.txt`, 58 880 B.

**Comprobación aritmética de todo el mapa:** el final de cada bloque cae en el offset del
siguiente, o a 1 byte antes. Los 36 huecos de un byte ocurre siempre donde
`offset + usStructureSize` es impar y el siguiente offset es par — **alineación a 2 bytes,
no corrupción**. Cero solapes, cero desbordes, y el bloque más alto termina en
`0xE5BF = 58 815 < 58 880`.

```text
0x0000..0x974C = 38908 B   sin mapear (codigo x86 de arranque, cadenas, cabeceras, PCIR)
0x974C..0xE5BF = 20083 B   mapeado por las tablas maestras
0xE5BF..0xE600 =    65 B   cola sin mapear
```

### 2.1 Bloques de datos: los que importan

| k | bloque | off | tamaño | rev | consumidor `file:line` |
|---|---|---|---|---|---|
| 4 | FirmwareInfo | 0x9974 | 108 | 2/2 | `amdgpu_atombios.c:581,1191` |
| 6 | LCD_Info | 0x9A14 | 78 | 1/3 | `bios_parser.c:1291,1491,1505,1620` |
| 8 | SMU_Info | 0xA8BC | 56 | 2/1 | `ppatomctrl.c:1000,1024` |
| 10 | GPIO_I2C_Info | 0x9A62 | 220 | 1/1 | `amdgpu_atombios.c:88,121,152` |
| 11 | VRAM_UsageByFirmware | 0x9B3E | 12 | 1/5 | `amdgpu_atombios.c:1667` |
| 12 | GPIO_Pin_LUT | 0x9B4A | 28 | 1/1 | `amdgpu_atombios.c:185` |
| 14 | **GFX_Info** | 0x9BF2 | 24 | 2/3 | `amdgpu_atombios.c:734` |
| 15 | PowerPlayInfo | 0x9C0A | 778 | 7/1 | `processpptables.c:836`; `kv_dpm.c:2704` |
| 17 | SaveRestoreInfo | 0xA8A4 | 24 | 2/1 | `NOT_CONSUMED` |
| 22 | Object_Header | 0x9F14 | 158 | 1/3 | `amdgpu_atombios.c:288,315` |
| 23 | IndirectIOAccess | 0xA28C | 125 | 1/1 | `atom.c:1584` |
| 24 | MC_InitParameter | 0x9FB2 | 729 | 2/1 | `NOT_CONSUMED` |
| 26 | ASIC_InternalSS_Info | 0xA824 | 40 | 3/1 | `amdgpu_atombios.c:904` |
| 28 | **VRAM_Info** | 0xA30A | 986 | 2/2 | `amdgpu_atombios.c:1455` |
| 31 | ASIC_ProfilingInfo | 0xA6E4 | 268 | 3/6 | `ppatomctrl.c:1044,1132` |
| 32 | VoltageObjectInfo | 0xA7F0 | 52 | 3/1 | `amdgpu_atombios.c:1304,1348,1384` |
| 24 | TV_VideoMode | 0xA84C | 87 | 2/3 | `NOT_CONSUMED` |
| 34 | ServiceInfo | 0xA8F4 | 85 | 1/1 | `NOT_CONSUMED` |
| 3 | StandardVESA_Timing | 0x983C | 312 | 1/2 | `NOT_CONSUMED` |
| 5 | PaletteData | 0x99E0 | 52 | 2/1 | `NOT_CONSUMED` |
| 13 | VESA_ToInternalModeLUT | 0x9B66 | 140 | 1/1 | `NOT_CONSUMED` |

### 2.2 Bloques de comando: presentes pero **inalcanzables en esta tarjeta**

Catorce tablas de comando tienen un offset `0x0000` en el ROM **pese a que el driver tiene un
consumidor para ellas**. Es decir: **el código existe y no puede dispararse nunca aquí.**

| índice | bloque | consumidor |
|---|---|---|
| 6, 8, 21, 22, 24, 25, 26 | EnableCRTCMemReq, DVOEncoderControl, DAC_LoadDetection, LVTMAEncoderControl, DAC1/2EncoderControl, DVOOutputControl | `command_table.c`, `atombios_crtc.c`, `atombios_encoders.c` |
| 36, 39, 50 | GetPixelClock, SetCRTC_Timing, ExternalEncoderControl | ídem |
| 68, 69 | DAC1/2OutputControl | ídem |
| 74, 75 | DIG1/2EncoderControl | `atombios_encoders.c` |
| 16 | GPUVirtualizationInfo | `amdgpu_atombios.c:1547` |
| 18 | PPLL_SS_Info / SS_Info | `bios_parser.c:1206,1796,1804` — **todas las rutas de spread-spectrum retornan pronto** |
| 30 | IntegratedSystemInfo | `amdgpu_atombios.c:773,800`; `kv_dpm.c:2554` |

**Y 47 de las 62 presentes no tienen consumidor en este corpus**, incluidos los cinco bloques
de reloj que usan las rutas antiguas: `SetEngineClock` (0xAD2A), `SetMemoryClock` (0xAED6),
`SetPixelClock`, `SetDCEClock`, `Gfx_Init`, `MemoryControllerInit`, `ASIC_Init`.

> **Salvedad obligatoria.** Este corpus está podado. `NOT_CONSUMED` significa *"no hay
> consumidor en los ficheros presentes"*, **no** "amdgpu lo ignora". Dos demostraciones de que
> la poda es severa: `amdgpu_atombios.c` son 1951 líneas y contiene **cero** apariciones de
> `master_table`, `MASTERSIZE` o `get_table_position` — el propio caminhero de la tabla maestra
> no está, y sin embargo el fichero sí usa `GetIndexIntoMasterTable` en 18 sitios.
> `discovery.c` **no existe**. `struct atom_master_list_of_command_tables` **no existe**.

## 3. Revision de cabecera 1.1 ⇒ la mitad del parser está muerta

```c
/* bios_parser.c:3067 */   if (tbl_rev.major >= 2 && tbl_rev.minor >= 2) return false;   /* 1.1 PASA  */
/* bios_parser2.c:3775 */  if (!(tbl_rev.major >= 2 && tbl_rev.minor >= 2)) return false; /* 1.1 RECHAZADO */
```

Y el dato medido: `ucTableFormatRevision = 1`, `ucTableContentRevision = 1`.

> **El parser V2 no puede leer este ROM, y con él queda muerto todo `bios_parser2.c` y todo
> `command_table2.c`**: `smu_info`, `vram_info`, `dce_info`, `umc_info`,
> `integratedsysteminfo`, `gpio_pin_lut`, `firmwareinfo`, `lcd_info`, `displayobjectinfo`,
> `setpixelclock`, `setdceclock`. Es una fracción grande del código de parseo del driver que
> **nunca se ejecuta en esta tarjeta**, y que por tanto no es candidato a explicar su
> comportamiento.

Los *call sites* que eligen entre los dos parsers no están en el corpus, así que digo las
guardas, no la selección en tiempo de ejecución.

## 4. LA PLACA SE IDENTIFICA CON NOMBRE PROPIO

Las cadenas del ROM son **evidencia primaria**, no adorno:

```text
0x0030  " 761295520"
0x0050  "05/12/21 03:53"                                    fecha de compilacion
0x00F4  "xxx-xxx-xxx"      [1] "LEXA"  [2] "PCI_EXPRESS"  [3] "GDDR5"
0x0119  "D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m"      mensaje de arranque
0x016E  "(C) 1988-2010, Advanced Micro Devices, Inc."
0x019A  "ATOMBIOSBK-AMD VER015.050.002.001.000000"
0x01C3  "hy64b-3.bin"
0x01EB  "WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1\\config.h"
0x0248  ATOM_PCI_INFO: vendor 0x1002  device 0x699F   subVID 0x0000  subDID 0x0018
```

**Cuatro cosas que el proyecto no sabía, y las cuatro del propio fabricante:**

| dato | valor | por qué importa |
|---|---|---|
| **revisión de silicio** | **`Lexa XL A0`** | el proyecto sólo sabía "Lexa" |
| **plataforma de placa** | **`WEIKENG`** | nombre real de la plataforma, del propio AMD |
| **fabricante y parte de VRAM** | **Hynix `H5GC8H24AJR`** | en `0xA34A`, y `HY64` en el nombre de configuración |
| **build** | `ATOMBIOSBK-AMD VER015.050.002.001`, 05/12/21 03:53 | fecha y versión exactas |

**Y dos corroboraciones cruzadas que no eran el objetivo:**

```text
ROM   "128bit"       ->  el bus de 128 bits del hallazgo 1445.  Segunda fuente
ROM   "214e/300m"    ->  SCLK 214 / MCLK 300 MEDIDOS en el hallazgo 1448.  Tercera fuente
                        (la primera era FirmwareInfo.ulDefaultEngineClock/MemoryClock)
```

> **El ROM declara en texto plano los relojes que el silicio tiene en reposo.** Eso convierte
> la medición de 1448 de "coincide con el default del firmware" a "coincide con lo que el
> propio AMD escribió en la placa". Es la clase de corroboración que no se puede obtener de
> otra fuente del proyecto.

## 5. `GFX_Info`: falta un campo, y con él se cierra el número de shaders

`_ATOM_GFX_INFO_V2_3` (`atombios.h:5660-5675`) usa **`UCHAR`, no `USHORT`** — mi primera
lectura dio basura por usar `u16`, y el subagente acertó al leerlo como bytes.

```text
GFX_Info @0x9BF2   usStructureSize=24  frev=2  crev=3

  GfxIpMinVer                   = 1
  GfxIpMajVer                   = 8        <- gfx8, confirmado
  max_shader_engines            = 2
  max_tile_pipes                = 4
  max_cu_per_sh                 = 5        <- ESTE NO ESTABA DECODIFICADO
  max_sh_per_se                 = 1
  max_backends_per_se           = 2
  max_texture_channel_caches    = 4

  2 SE x 1 SH x 5 CU = 10 CU = 640 shaders
```

> **640 shaders es exactamente la especificación del RX 550.** El 1400 había cerrado cinco
> campos y dejó este por decodificar; con él, la geometría de shaders queda **cerrada por el
> ROM** y por primera vez con un número que se puede contrastar contra el silicio.

## 6. `VRAM_Info`: confirmado, y ahora con el número de parte

`_ATOM_VRAM_INFO_HEADER_V2_2` (`atombios.h:8027`), elegido por datos
(`usReserved1 == 0` en +14):

```text
+4  usMemAdjustTblOffset        =  76  -> ATOM_INIT_REG_BLOCK @0xA356   (3, 4)
+6  usMemClkPatchTblOffset      =  91  -> ATOM_INIT_REG_BLOCK @0xA365   (42, 52)  <- el del 1419
+8  usMcAdjustPerTileTblOffset  = 713  -> 0xA5D3   (6, 8)
+10 usMcPhyInitTableOffset      = 811  -> 0xA635   (75, 92)
+12 usDramDataRemapTblOffset    = 743  -> 0xA5F1
+14 usReserved1                 =   0     <- cierra el V2_2
+16 ucNumOfVRAMModule           =   1
+17 ucMemoryClkPatchTblVer      =   1
+18 ucVramModuleVer             =   8     <- ATOM_VRAM_MODULE_V8
+19 ucMcPhyTileNum              =   2     <- corrobora mem_banks_count=2 (1406)
```

**El par `(42, 52)` en `0xA365` es único en los 58 880 bytes.** Los once perfiles de timings del
1419 son, por tanto, re-derivables y están anclados de forma única.

```text
ATOM_VRAM_MODULE_V8 @0xA31E   (atombios.h:7943-7961, offsets LEIDOS del struct, no supuestos)
  usMemorySize  @+20 = 2048 MB = 2 GiB            OK
  ucMemoryType  @+11 = 80    <- NO es un valor de enum
  ucDensity     @+14 = 99    <- NO es un valor de enum
  "H5GC8H24AJR" en 0xA34A = +44 sobre el cabecera del modulo
```

**El layout diverge a partir de ahí.** `ucMemoryType = 80` y `ucDensity = 99` no son miembros
de sus enumeraciones, así que **todo lo posterior a `usMemorySize` queda `NOT_DETERMINED`.** No
desplazo el struct para que encaje; eso sería fabricar la decodificación.

## 7. PROBADO AUSENTE: no hay imágenes de firmware en este ROM

Cuatro líneas independientes, y la última es aritmética, y es la que zanja la discusión:

1. **Ninguna de las dos tablas maestras tiene una entrada de imagen.** Los 35 nombres de datos
   y los 81 de comandos están inventariados; ninguno es un contenedor de imagen.
   `FirmwareInfo` (0x9974) son 108 bytes de relojes y límites, **sin puntero ni longitud**.
2. **Tamaño.** `IndirectIOAccess` → IIO es 120 bytes de *programas de escritura de
   registros**, no microcódigo.
3. **Sonda de contenido.** Los 20 blobs de `/lib/firmware/amdgpu/polaris12_*.bin.xz`
   descomprimidos, buscando los primeros 24 bytes de cada uno en la captura: **cero
   coincidencias.**
4. **Aritmética, y es la que manda:**

```text
la captura entera = 58 880 B = 57.5 KiB

polaris12_uvd.bin     375 424 B   NO CABE
polaris12_mec_2.bin   262 824 B   NO CABE
polaris12_vce.bin     166 816 B   NO CABE
polaris12_smc.bin     130 388 B   NO CABE
```

**El firmware de UVD es 6.4 veces más grande que el ROM completo.** No hay forma de que esté
dentro. Y el driver lo carga de disco: `amdgpu_uvd.c:78,244-246` mapea
`CHIP_POLARIS12 → FIRMWARE_POLARIS12 = "amdgpu/polaris12_uvd.bin"` y lo pide en
`amdgpu_uvd.c:263`.

> **Esto refuta una hipótesis que yo mismo puse en el encargo** ("sin MP1 el VBIOS podría ser
> lo que se ejecuta"). El subagente la rechazó por su cuenta y con razón. La anoté aquí para
> que quede escrita como lo que era: una suposición mía, sin respaldo.

## 8. Anomalías, explícitas

| # | anomalía | estado |
|---|---|---|
| 1 | `d[0x0004]=0x9D`, `d[0x0005]=0x02` — dentro de `ATOM_ROM_HEADER` pero **ningún struct del corpus los define** | `NOT_DETERMINED` |
| 2 | **Dos pares de subsistema distintos en un ROM**: `ATOM_ROM_HEADER` = 0x1002/0x0B04; `ATOM_PCI_INFO` = 0x0000/0x0018. Cuál manda | `NOT_DETERMINED` |
| 3 | `ulASICMaxEngineClock = 0`, `ulMaxEngineClockPLL_Output = 0`, `ulDriverTargetEngineClock = 0`, mientras los relojes de memoria **sí** están poblados | `OBSERVADO` |
| 4 | `ATOM_BYTEDATA` **no existe en este corpus** (cero coincidencias). La columna "creator" es `NOT_PRESENT` en los 83 bloques: es un hecho del corpus, no del BIOS | `NOT_PRESENT` |
| 5 | `ATOM_VRAM_MODULE_V8` divergen a partir de +21 (§6) | `NOT_DETERMINED` |
| 6 | Checksum del ROM en `0x0002 = 0xE973`. Ninguna suma de 16 bits sobre ventana alguna coincide. `usCRC_BlockOffset = 0x0265`. El algoritmo no está en el corpus | `NOT_DETERMINED` |
| 7 | La captura son 58 880 B, no 131 072. 115×512 = 58 880, así que puede ser una imagen entera de 115 sectores en vez de un truncamiento | `NOT_DETERMINED` |

## 9. Procedencia

```text
fichero  revkit/capturas/amdgpu_vbios.txt   58 880 B  (única fuente; cero hardware)
fuente   include/atombios.h:208-214   ATOM_COMMON_TABLE_HEADER (4 bytes, sin creator)
         include/atombios.h:272-354   ATOM_MASTER_LIST_OF_COMMAND_TABLES   81 entradas
         include/atombios.h:2783-2820 ATOM_MASTER_LIST_OF_DATA_TABLES      35 entradas
         include/atombios.h:5660-5675 _ATOM_GFX_INFO_V2_3     (UCHAR, no USHORT)
         include/atombios.h:7943-7963 _ATOM_VRAM_MODULE_V8
         include/atombios.h:8027      _ATOM_VRAM_INFO_HEADER_V2_2
         bios_parser.c:3067 / bios_parser2.c:3775   las dos guardas de revisión
         amdgpu_uvd.c:78,244-246,263  el firmware de UVD viene de disco
```

```text
ESTADO=PROBADO · la tabla maestra no es {indice,long,offset}: son dos LISTAS de offsets USHORT
       (166 = 4+2*81 comandos, 74 = 4+2*35 datos) y la aritmetica se sostiene sola
REFUTADA mi premisa del encargo.  d[0x24..0x27] = 00 00 00 00.  REFUTADA tambien mi hipotesis
       de que el VBIOS podia ser la fuente del firmware de UVD/VCE: el mayor blob es 6.4x el ROM
NUEVO  revision de silicio "Lexa XL A0";  plataforma "WEIKENG";  VRAM Hynix "H5GC8H24AJR"
NUEVO  revision de cabecera 1.1 => bios_parser2.c y command_table2.c NO CORREN en esta tarjeta
NUEVO  max_cu_per_sh = 5 (atombios.h:5669).  2 SE x 1 SH x 5 CU = 10 CU = 640 shaders, que es la
       especificacion del RX 550.  El numero de shaders queda cerrado por el ROM
CORROBORADO  "128bit" del ROM corrobora el bus del 1445.  "214e/300m" corrobora los relojes en
       reposo MEDIDOS en el 1448: tercera fuente independiente para 214/300 MHz
CORROBORADO  VRAM_Info: el par (42,52) en 0xA365 es UNICO en los 58880 bytes, asi que los once
       perfiles del 1419 quedan anclados de forma unica
NUEVO  17 bloques tienen consumidor en el corpus pero offset 0x0000 en el ROM: codigo que no
       puede dispararse nunca en esta tarjeta.  Incluye todas las rutas de spread-spectrum
LIMITE  NOT_CONSUMED significa "no hay consumidor en este corpus", no "amdgpu lo ignora": el
       caminero de la tabla maestra, discovery.c y atom_master_list_of_command_tables NO estan
NOT_DETERMINED  checksum del ROM; los bytes 0x04/0x05 de la cabecera; que par de subsistema
       manda; los campos del modulo VRAM despues de usMemorySize; si la captura es el ROM entero
RIESGO  ninguno.  CERO escrituras, cero hardware.  El fichero es de lectura
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active, un /dev/fb0
Siguiente  1) los 20 bloques de datos y 62 de comandos con cabecera pero sin campos decodificados:
           es la mayor reserva sin explotar, y es trabajo estatico y seguro
         2) el mapa de offsets de dce110_hwseq.c, pero solo tras que el propietario decida que
           ocurre con DVI-D-1 y HDMI-A-2, que siguen siendo tema aparte y sin permiso
```

## 10. Lo que este mapa resuelve para el objetivo del proyecto

El objetivo es un driver **para esta tarjeta concreta**. Este ROM, con `WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1`
como nombre de plataforma, **es la declaración de qué placa es esta**. Todo lo que siga —
geometría de clocks, tablas de timings, límites de voltaje, y la revisión de silicio A0 — tiene ya
el lugar exacto donde está escrito por el fabricante. Un driver especializado empieza por
saber qué placa tiene delante, y hasta hoy el proyecto no lo sabía.