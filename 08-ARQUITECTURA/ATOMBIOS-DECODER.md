# ATOMBIOS-DECODER — descifrador de la ROM de la RX 550, construido y validado sin la ROM

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SUB-NODIGO
NODE_ID=ATOMBIOS-DECODER · GENERADO=2026-10-04
TARGET=AMD Radeon RX 550 · Polaris12 / GFX8 · PCI 1002:699F rev 0xc7
ENTREGABLES=03-EXPERIMENTOS/ATOMBIOS-DECODER/{rx550_atom_dec.c,rx550_atom_dec.h}
          08-ARQUITECTURA/ATOMBIOS-DECODER.md   (este fichero)
ESTADO=CONSTRUIDO · SELF_TEST 21/21 · CERO AVISOS -Wall -Wextra
       · NO PROBADO CONTRA UNA ROM REAL · ROM NO LEIDA
VEREDICTO=PASA los criterios de paso definidos en la seccion 5
```

## 0. Que resuelve esto y que no

El hallazgo 1053 ha establecido que la geometria esta en
`/sys/bus/pci/devices/0000:01:00.0/rom`, que pide root para leerse. Ese nodo, cuando
se ejecute, tendra que dar **toda** la informacion de golpe, no 128 KiB por descifrar
a mano.

Este nodo construye y valida ese descifrador. **No lo ejecuta contra la ROM real**,
porque no puede leerla: uid 1000 recibe `PermissionError` sobre un fichero modo
`0600` de root (medido en el hallazgo 1053, y reverificado aqui solo con `os.stat`,
sin abrir). Todo lo que sigue procede de dos fuentes, y de ninguna otra:

| fuente | que aporta | medido |
|---|---|---|
| `RESEARCH/baseline/linux-7.1.3/...` | los **offsets** | leer el codigo del driver |
| vectores **sinteticos** | que los offsets se aplican como se cree | 21 vectores, 21 pasan |

Lo que **no** hay es una ROM real que confirme un solo offset. Eso esta en la
seccion 8, y es la parte mas importante de este informe.

---

## 1. La ruta que este descifrador replica, y por que esa y no otra

El encargo exigia offsets exactos derivados del fuente. Eso obliga primero a fijar
**que ruta ejecuta el driver para ESTE ASIC**, porque hay dos y no son la misma.

### 1.1 La geometria de Polaris12 sale del ATOMBIOS: PROBADO

```
gfx_v8_0.c:1676-1681
	case CHIP_POLARIS11:
	case CHIP_POLARIS12:
		ret = amdgpu_atombios_get_gfx_info(adev);
		if (ret)
			return ret;
```

Ese es el punto de lectura de la geometria para este ASIC. Y funciona, es decir la
ROM tiene que ser un ATOMBIOS leido por la ruta clasica.

### 1.2 La ruta de descubrimiento IP NO aplica a Polaris12: PROBADO

Es un descarte importante, porque `amdgpu_discovery.c:1767-1786` —la linea que el
hallazgo 1053 cita para los tamanos de cache L1/L2— parece que fuera la fuente, y no
lo es:

```
amdgpu_device.c:1978-1994
	case CHIP_POLARIS10:
	case CHIP_POLARIS11:
	case CHIP_POLARIS12:
	case CHIP_VEGAM:
		...
		r = vi_set_ip_blocks(adev);             <-- Polaris12 entra aqui
		break;
	default:
		r = amdgpu_discovery_set_ip_blocks(adev);   <-- y NO entra aqui
```

`amdgpu_discovery_get_gfx_info()` (el que contiene las lineas 1767-1786 con
`gc_l1_data_cache_size_per_sqc`, `gc_tcc_size` y compania) se llama solo desde
`amdgpu_discovery_set_ip_blocks()`, que **Polaris12 no ejecuta**. Para este ASIC la
fuente de la geometria es `amdgpu_atombios_get_gfx_info()`.

**Consecuencia directa:** el hallazgo 1053 afirma que los tamanos de cache L1 y L2
estan en la ROM, y su tabla dice que los cierra `amdgpu_discovery.c:1767-1786`. Esa
linea no corre para Polaris12, y `ATOM_GFX_INFO_V2_1` **no tiene ningun campo de
tamano de cache**. Los tamanos de cache de este ASIC salen de otro sitio, y se
detalla en la seccion 7.

### 1.3 Cadena completa replicada

```
amdgpu_bios.c:161     pci_map_rom(adev->pdev, &size)      -> el buffer es la ROM
amdgpu_bios.c:171     memcpy_fromio(adev->bios, bios,size)    byte a byte
amdgpu_bios.c:174     check_atom_bios(adev, size)
amdgpu_atombios.c:1914  amdgpu_atom_parse(card, adev->bios)
atom.c:1560-1571        0xAA55 y cadena magica ATI
atom.c:1573-1580        base y firma "ATOM"
atom.c:1582-1583        cmd_table, data_table
amdgpu_atombios.c:739   amdgpu_atom_parse_data_header(ctx, 14, ...)
atom.c:1642-1661        resolucion de la entrada 14
amdgpu_atombios.c:744-750  copia de los seis campos de geometria
```

**El offset del buffer es el offset del fichero.** `adev->bios[0]` es el byte 0 del
fichero ROM, porque `pci_map_rom` entrega la BAR entera y se copia tal cual. Eso es lo
que hace que un descifrador de fichero sea legitimo y no una aproximacion.

---

## 2. Los campos y sus offsets, cada uno con su cita

Tipo de todos: `ATOM_GFX_INFO_V2_1` (`atombios.h:5647-5658`), 12 bytes, con
`#pragma pack(1)` en `atombios.h:191`. Todos los campos son `UCHAR`, 1 byte,
little-endian.

`base` de la tabla = `data_table + 4 + 14*2` (`atom.c:1646-1647`). El indice 14 sale de
`atombios.h:2799`, contado sobre los miembros de `ATOM_MASTER_LIST_OF_DATA_TABLES`, y
lo corroboran dos cosas independientes: `GetIndexIntoMasterTable(DATA, GFX_Info)` en
`amdgpu_atombios.c:734` se define como `offsetof(...)/sizeof(USHORT)` en
`atombios.h:7151`, y el indice `gfx_info` ocupa la misma posicion 14 en
`atom_master_list_of_data_tables_v2_1` de `atomfirmware.h:405`.

| offset en GFX_Info | ancho | tipo | valor en RX 550 | cita del driver que lo consume |
|---|---|---|---|---|
| +0 | 2 | `usStructureSize` | sin dato | `atom.c:1654` |
| +2 | 1 | `ucTableFormatRevision` | sin dato | `atom.c:1656` |
| +3 | 1 | `ucTableContentRevision` | sin dato | `atom.c:1658` |
| +4 | 1 | `GfxIpMinVer` | sin dato | `atombios.h:5650` |
| +5 | 1 | `GfxIpMajVer` | sin dato | `atombios.h:5651` |
| **+6** | 1 | `max_shader_engines` | **SE** | **`amdgpu_atombios.c:744`** |
| **+7** | 1 | `max_tile_pipes` / `reserved` | ver 2.1 | **`amdgpu_atombios.c:745`** |
| **+8** | 1 | `max_cu_per_sh` | **CU por SH** | **`amdgpu_atombios.c:746`** |
| **+9** | 1 | `max_sh_per_se` | **SH por SE** | **`amdgpu_atombios.c:747`** |
| +10 | 1 | `max_backends_per_se` | sin dato | `amdgpu_atombios.c:748` |
| **+11** | 1 | `max_texture_channel_caches` | **NUM_TCC_BANKS** | **`amdgpu_atombios.c:749-750`** |

`NUM_TCC_BANKS` esta en la ROM por esta via, y la cadena hasta el consumidor esta
cerrada: `amdgpu_kms.c:1023` hace
`dev_info->num_tcc_blocks = adev->gfx.config.max_texture_channel_caches;`.

**CU totales es una DERIVACION, no un campo.** No existe en la ROM ni lo calcula el
driver. El descifrador lo imprime como derivacion explicita
`max_shader_engines * max_sh_per_se * max_cu_per_sh` y dice que es suyo.

### 2.1 El byte +7 tiene dos semanticas segun la version, y el driver no lo mira

`amdgpu_atombios.c:745` lee `max_tile_pipes` del offset +7 **sin mirar `frev` ni
`crev`**. Pero las dos cabeceras del arbol no coinciden:

| version | +7 | cita |
|---|---|---|
| v2_1, v2_2, v2_3, v3_0 | `max_tile_pipes` | `atombios.h:5653`, `atomfirmware.h:1799,1819,1920` |
| v2_4, v2_7 | `reserved` | `atomfirmware.h:1844` |

Es decir: **si la ROM trae GFX_Info 2.4 o 2.7, el driver lee como `max_tile_pipes` un
byte que el propio firmware llama `reserved`.** El driver funciona igual porque ese
campo no lo usa nadie en GFX8, pero el descifrador tiene que decirlo en vez de elegir
en silencio, y eso hace: imprime el valor y una linea `SEMANTICA=max_tile_pipes` o
`SEMANTICA=reserved` segun la version. El vector V03 lo comprueba.

### 2.2 CONTRADICCION entre dos cabeceras: GFX_Info 2.3

Esta es la parte que mas caro sale equivocada, y no es culpa de este trabajo:

| cabecera | desde +12 | tamano total |
|---|---|---|
| `atombios.h:5660-5675` (`ATOM_GFX_INFO_V2_3`) | 3 `USHORT`: umbral de fuga + 2 offsets de tabla + 3 reservadas | 24 B |
| `atomfirmware.h:1814-1836` (`atom_gfx_info_v2_3`) | 8 `ULONG` de direcciones de registro, y despues mas campos | 52 B |

Los dos layouts son **incompatibles**. El arbol no dice cual usa el firmware. El
descifrador **no imprime ningun valor de +12 en adelante cuando `crev==3`**: imprime
`DISPUTADO` con las dos citas enfrentadas. Elegir una seria inventar.

### 2.3 Campos del ROM header y de FirmwareInfo

Del `ATOM_ROM_HEADER` (`atombios.h:219-239`, 36 B, base+0) se decodifican los 16
campos con su offset individual, incluido `usMasterDataTableOffset` en +0x20
(`atombios.h:236`), que es la bisagra de todo: `atom.c:1591-1593` lo usa para encontrar
la tabla maestra.

De `ATOM_FIRMWARE_INFO` (`atombios.h:2948-2980`, indice 4 de `amdgpu_atombios.c:581`)
se decodifica el prefijo hasta +44 inclusive, que es todo lo que tiene cita individual
usable: `ulFirmwareRevision` en +4 (que es `ctx->version`, `atom.c:1597`), los relojes
por defecto y maximos, y `ucASICMaxTemperature` en +44.

**`NO_DERIVADO_POR_ALCANCE` a partir de +45.** Ahi empiezan
`usFirmwareCapability` y `usReferenceClock`, que el driver si lee
(`amdgpu_atombios.c:597` y `:716`), pero cuyo offset depende del tamano de la union
`ATOM_FIRMWARE_CAPABILITY_ACCESS`, que cambia segun `CONFIG` (`atombios.h:2933-2946`).
No los declaro porque no puedo derivar su offset de forma inequivoca, y un offset
dudoso es exactamente el fallo que este descifrador existe para evitar.

### 2.4 La cadena `vbios_version`, que es el otro extremo del hallazgo 1053

`/sys/class/drm/card1/device/vbios_version = b'xxx-xxx-xxx\n'` viene de aqui:

```
atom.c:1437         str_num = rom[0x2F]                (atomfirmware.h:221)
atom.c:1438-1440    off = u16 en 0x6E                  (atomfirmware.h:222)  lectura DESALINEADA
atom.c:1443         si str_num == 0, off = 0x80        (atomfirmware.h:223)
atom.c:1456-1461    copiar mientras el byte este entre 0x20 y 0x7A, hasta 43 bytes
amdgpu_atombios.c:1807-1816  sysfs imprime ctx->vbios_pn
```

El descifrador reproduce esa logica y muestra **donde** esta la cadena y por que via.
Una desviacion consciente: `atom.c:1439` lee un `USHORT` desalineado en 0x6E; el
descifrador lo lee byte a byte en little-endian. Mismo resultado en x86-64, sin
comportamiento indefinido. Documentado, no accidental.

---

## 3. Que NO hay: no hay verificacion de CRC, y por que eso importa

Existe el campo `ATOM_ROM_HEADER.usCRC_BlockOffset` (`atombios.h:227`). **Pero no hay
ninguna verificacion de CRC en la ruta que este descifrador replica**: no la hay en
`atom.c`, ni en `amdgpu_atombios.c`, ni en `amdgpu_bios.c` (medido con grep sobre los
tres ficheros completos).

Eso tiene una consecuencia dura: un descifrador que anadiese una puerta de CRC
aceptaria ROMs que el driver rechaza, o rechazaria ROMs que el driver acepta. El
descifrador **no comprueba CRC**, y el vector **V15** lo demuestra en los dos
sentidos: primero que su propio CRC-16/ARC **si** discrimina (cambia al cambiar un
byte, `0xCBD1` a `0xA7D5`, y vuelve a `0xCBD1` al restaurarlo), y segundo que aun con
el CRC corrupto la ROM **se acepta igual**.

Igual con `AMD_VBIOS_LENGTH` (`amdgpu_bios.c:45`): el campo existe, pero solo se usa en
`amdgpu_bios.c:202`, que es otra funcion (`amdgpu_read_bios_from_rom`), no en
`amdgpu_read_bios` (`amdgpu_bios.c:154-180`), que es la que usa `pci_map_rom`. El
descifrador lo imprime y lo marca como no usado en esta ruta. Vector **V19**.

### 3.1 LIMITACION: toda la cadena de offsets del ATOMBIOS es de 16 bits

Medido sobre el fuente, y no supuesto:

```
atombios.h:2785   cada entrada de ATOM_MASTER_LIST_OF_DATA_TABLES es USHORT
atom.c:1647       idx = CU16(ctx->data_table + offset)     assigned a uint16_t
atom.h:35         ATOM_ROM_TABLE_PTR, leido con CU16 en atom.c:1573
atom.h:43         ATOM_ROM_DATA_PTR, leido con CU16 en atom.c:1583
```

Consecuencia: **toda la estructura del ATOMBIOS cabe en 64 KiB.** Una ROM de 128 KiB
truncada a 65536 **no es detectable** desde la estructura del ATOMBIOS, porque toda la
estructura sigue dentro de los primeros 64 KiB. Eso es un `NEGATIVE_RESULT`
registrado como vector **V04b**, y es la razon por la que el vector de trunca a la
mitad usa una ROM de 3072 B en lugar de la de 128 KiB: con 128 KiB la mitad no corta
nada, y un vector que no discrimina no vale como vector.

---

## 4. El self-test: 21 vectores, ejecutados al correr

Los 21 se ejecutan en **cada** invocacion, antes de decodificar nada. Si alguno falla,
el programa no sigue: sale con `rc=1` y no emite informe.

```sh
gcc -std=c99 -Wall -Wextra -O2 -o rx550_atom_dec rx550_atom_dec.c
./rx550_atom_dec
```

Salida medida:

```text
[self-test] todos los vectores son SINTETICOS.
[self-test] no se ha leido ninguna ROM real en este programa.
  [PASA] V01   ROM sintetica bien formada, layout V2_1: SE=2 CU/SH=8 SH/SE=4 TP=4 BKNDS=2 TCC=8 CU_total=64
  [PASA] V02   byte en off=0x00508 (GFX_Info+8) cambiado 8->9, detectado y localizado en off=0x00508
  [PASA] V03   layout atom_gfx_info_v2_4 (crev=4): +7 marcada RESERVED, gc_lds_size=64 gc_max_scratch_slots_per_cu=32 en off=0x0053F
  [PASA] V04   truncada a la mitad: rc=5 y dice DONDE, off=0x600 con fichero de 0x600 (corte dentro de FirmwareInfo, que empieza en 0x0600)
  [PASA] V04b  NEGATIVO: ROM de 0x20000 truncada a 0x10000 se ACEPTA con rc=0. Motivo medido: toda la cadena de offsets del ATOMBIOS es de 16 bits ...
  [PASA] V05   truncada dentro de GFX_Info: rc=5, primer byte ausente off=0x50B, que es max_texture_channel_caches
  [PASA] V06   truncada dentro de FirmwareInfo: rc=5, primer byte ausente off=0x610, dentro de ulDefaultMemoryClock
  [PASA] V07   firma "ATOM" invalida ("ATOX"): rc=4 rechazado
  [PASA] V08   firma de VBIOS invertida (AA 55): rc=4 rechazado
  [PASA] V09   cadena magica ATI invalida en 0x30: rc=4 rechazado
  [PASA] V10   ATOM_ROM_TABLE_PTR = 0: rc=4 rechazado
  [PASA] V11   base 0xFFF0 mas alla del fichero: rc=4 rechazado
  [PASA] V12   fichero vacio (0 bytes): rc=4 rechazado
  [PASA] V13   fichero de 1 byte (< 0x49): rc=4 rechazado
  [PASA] V14   GFX_Info ausente: rc=6 y dice AUSENTE, no imprime ceros como si fueran un valor
  [PASA] V15   el CRC SI discrimina (0xCBD1 -> 0xA7D5 al cambiar un byte, y vuelve a 0xCBD1 al restaurarlo), y aun asi la ROM con el CRC a 0x342E se ACEPTA con rc=0: la ruta del driver no verifica CRC
  [PASA] V16   ROM sin ATOMBIOS ("ATXM"): rc=4 rechazado; que no la haya leido no significa que no la contenga
  [PASA] V17   ruta inexistente: open() falla y el programa debe salir con rc=3
  [PASA] V18   directorio como entrada: fread devuelve 0 bytes, hay que rechazarlo
  [PASA] V19   AMD_VBIOS_LENGTH = 0xFF<<9 = 130560, que no coincide con el tamano real 131072, y aun asi rc=0: el campo no gobierna la aceptacion
  [PASA] V20   marcadores L1=16 KiB y L2=2048 KiB plantados en off=0x00900: ningun campo decodificado los reproduce, porque no existe offset derivado para un tamano de cache
[self-test] vectores ejecutados = 21, fallos = 0
```

### 4.1 Que cubre cada requisito duro, con su vector

| requisito del encargo | vector | resultado medido |
|---|---|---|
| ROM sintetica bien formada, valores distinguibles, checksum coherente | V01 | SE=2, CU/SH=8, SH/SE=4, TP=4, BKNDS=2, TCC=8; CRC-16/ARC almacenado y coherente |
| la MISMA ROM con un byte cambiado, **ver el cambio y su donde** | V02 | byte en `off=0x00508` (`GFX_Info`+8) cambiado 8 a 9, detectado **y localizado en ese mismo offset** |
| truncada a la mitad, `rc != 0` y decir DONDE | V04 | `rc=5`, primer byte ausente `off=0x600` |
| firma invalida, rechazarla | V07, V16 | `rc=4` para `ATOX` y para `ATXM` |
| vacia (0 bytes), rechazarla | V12 | `rc=4` |
| **negativos que NO debe aceptar** | V08,V09,V10,V11,V13,V14,V17,V18 | los 8 rechazados con su codigo propio |

Sobre los valores que pedia el encargo para el vector sintetico: **SE=2, SH/SE=4,
CU/SH=8** estan en la tabla y el descifrador los lee (V01). **L1=16 KiB** y
**L2=2048 KiB** estan plantados en `off=0x0900` pero **no se decodifican**, y eso es lo
correcto: no existe ningun offset derivado en `GFX_Info` para un tamano de cache. El
vector **V20** existe justo para comprobar que no se inventan: recorre los 32 valores
decodificados y verifica que ninguno reproduce los marcadores. `bytes_por_slot=64`
**tampoco** viene de la ROM para este ASIC (ver seccion 7), aunque si aparece en la
tabla si la version es 2.4 (V03).

### 4.2 V04b: un resultado negativo que tambien es una regla

V04b registra que una ROM de 128 KiB truncada a 65536 **se acepta**. No es un fallo
del descifrador: es la consecuencia directa de la cadena de offsets de 16 bits
documentada en 3.1. Se incluye porque un self-test que solo sabe decir «pasa» no sirve
para distinguir «funciona» de «no se ha probado».

---

## 5. Criterios de paso, medidos

| criterio | como se midio | resultado |
|---|---|---|
| compila con `-Wall -Wextra`, **0 avisos** | `gcc -std=c99 -Wall -Wextra -O2` | **PASA**, salida vacia |
| self-test pasa todos sus vectores | `./rx550_atom_dec` | **21/21**, `fallos = 0` |
| salida identica byte a byte desde la raiz y desde el directorio propio | `diff` de stdout **y** stderr | **PASA**, `sha256` identicos en las 4 capturas |
| cada campo impreso lleva offset, ancho, endianness y cita | inspeccion de la salida del informe | **PASA**, las 4 lineas por campo |
| un truncamiento produce `rc != 0` | V04, V05, V06 y `head -c` sobre ficheros reales | **PASA**, `rc=5` en los tres |

Detalle del criterio de directorio de trabajo, que el encargo justifica con el hallazgo
1051: el mensaje de uso **no imprime `argv[0]`**, precisamente para que la salida no
dependa de como se invoque. Y la ruta de entrada se imprime tal como la da el usuario,
no reconstruida. Medido:

```text
sha256  c80bb5ff...402f150  out_desde_raiz
sha256  c80bb5ff...402f150  out_desde_dir_propio
sha256  655dac17...7e91800  err_desde_raiz
sha256  655dac17...7e91800  err_desde_dir_propio
```

### 5.1 Codigos de salida

| rc | significado |
|---|---|
| 0 | self-test OK y (sin fichero, o decodificacion OK) |
| 1 | fallo el self-test; no se decodifica nada |
| 2 | falta el argumento |
| 3 | no se pudo leer la entrada (no existe, es un directorio, lectura corta, sin memoria) |
| 4 | rechazada: no es ATOMBIOS segun la ruta del driver |
| 5 | truncada: una referencia cae fuera del fichero; el mensaje da el offset |
| 6 | `GFX_Info` ausente: se dice AUSENTE, **no** se imprimen ceros |

Medido sobre ficheros reales, no solo vectores:

```text
sin argumentos              rc=2   uso: rx550_atom_dec <fichero-rom>
ruta inexistente            rc=3   no se pudo abrir la entrada
directorio                  rc=3   no es un fichero regular legible
fichero vacio               rc=4   mide 0 bytes
100 bytes de ceros          rc=4   firma de VBIOS invalida
mitad de 128 KiB            rc=0   <-- NEGATIVO V04b, correcto por 3.1
1296 B                      rc=5   TRUNCADA, la cabecera comun de GFX_Info
1552 B                      rc=5   TRUNCADA, el prefijo de ATOM_FIRMWARE_INFO
```

### 5.2 Garantias de lector puro

- El unico `fopen` del programa es el de `argv[1]`.
- No hay `open`, `ioctl`, `/dev`, `/sys` ni `RREG`/`WREG` en ninguna forma.
- No he abierto `/dev/dri/renderD129` ni ningun nodo de device. No he leido ni escrito
  la ROM: solo `os.stat`, que es una llamada al `stat(2)` del pathname.
- **Medido antes y despues de mi turno, la GPU sigue dormida:**

```text
ANTES     runtime_status = suspended   runtime_active_time = 278853
DESPUES   runtime_status = suspended   runtime_active_time = 278853
```

`runtime_active_time` es **identico**. Solo avanzo `runtime_suspended_time`, que es lo
que tiene que avanzar si la GPU sigue suspendida mas tiempo. La ROM conserva sus
`131072` bytes y su modo `0600`.

---

## 6. Decisiones tomadas sin permiso, y por que

El encargo dice decidir y documentar. Estas son las cinco.

1. **Replicar la ruta ATOMBIOS, no la de ATOMFW.** `atom.h:35` y `atombios.h` frente a
   `atomfirmware.h`. Motivo: seccion 1.1, `gfx_v8_0.c:1676-1681` fija el lector de este
   ASIC. Consecuencia: la rama `#ifdef __KERNEL__` del `.c` deja el formateo de errores
   como prototipo sin implementar, porque no hay un camino de kernel verificado que
   inventar.
2. **Sin puerta de CRC ni de `AMD_VBIOS_LENGTH`.** Motivo: seccion 3, el driver no las
   tiene. Un descifrador que acepta mas o menos que el driver es peor que uno que no
   acepta.
3. **Imprimir `+7` como `reserved` cuando la version lo dice**, aunque el driver lo lea
   como `max_tile_pipes`. Motivo: seccion 2.1. Imprimir el nombre del driver y callar
   la contradiccion seria esconder el dato.
4. **No imprimir nada de `+12` cuando `crev==3`.** Motivo: seccion 2.2, dos layouts
   incompatibles y ningun arbitro en el arbol. Imprimir el de `atombios.h` o el de
   `atomfirmware.h` seria inventar.
5. **Marcar `NO_DERIVADO_POR_ALCANCE` en `FirmwareInfo +45`.** Motivo: seccion 2.3, el
   offset depende de `CONFIG` y no es derivable de forma inequivoca. Dejarlo fuera con
   la razon escrita es mejor que un offset plausible y equivocado.

---

## 7. Que NO se puede saber sin la ROM

La parte que mas valor tiene, porque delimita lo que la peticion de root va a cerrar y
lo que no va a cerrar.

### 7.1 Lo que la ROM SI cierra (si es un ATOMBIOS)

| campo | offset | por que se cierra |
|---|---|---|
| `max_shader_engines` (SE) | `GFX_Info`+6 | `amdgpu_atombios.c:744` |
| `max_cu_per_sh` | `GFX_Info`+8 | `amdgpu_atombios.c:746` — **la contradiccion 5-contra-8 en su origen** |
| `max_sh_per_se` | `GFX_Info`+9 | `amdgpu_atombios.c:747` |
| `max_backends_per_se` | `GFX_Info`+10 | `amdgpu_atombios.c:748` |
| `max_texture_channel_caches` (NUM_TCC_BANKS) | `GFX_Info`+11 | `amdgpu_atombios.c:749-750` y `amdgpu_kms.c:1023` |
| CU totales | derivado de +6,+9,+8 | derivacion explicita, no un campo |
| version del IP de graficos | `GFX_Info`+4,+5 | `atombios.h:5650-5651` |
| `vbios_version` | cadena en la ROM | `atom.c:1437-1461` y `amdgpu_atombios.c:1815` |
| clocks por defecto y maximos | `FirmwareInfo`+4..+44 | `amdgpu_atombios.c:603,641-643,668-670,682-684` |

### 7.2 Lo que la ROM NO cierra, aunque el hallazgo 1053 la liste

| lo que 1053 dice que cierra la ROM | realidad medida | donde esta de verdad |
|---|---|---|
| **tamano de cache L1** | `ATOM_GFX_INFO_V2_1` no tiene ningun campo de cache. Y `amdgpu_discovery.c:1767-1786` **no corre para Polaris12** (seccion 1.2) | fijo en el kernel: `kfd_crat.c:94` (TCP L1 = 16 KiB por CU), `:103` (SQC instruccion = 32 KiB), `:113` (SQC datos = 16 KiB) |
| **tamano de cache L2** | no esta en ninguna version de `GFX_Info` | **no esta en ninguna parte de este kernel**: `kfd_crat.c:122` dice literalmente `TODO: Add L2 Cache information` |
| **bytes por slot de scratch** | para GFX8 lo fija el codigo | `gfx_v8_0.c:7125` da `lds_size = 64`; `gfx_v8_0.c:7123` da `max_scratch_slots_per_cu = 32` |

Esto **no es una refutacion de que la geometria este en la ROM**: es una refutacion de
tres filas concretas de su tabla. Las filas de CU, SE y NUM_TCC_BANKS se mantienen, y son
las que cierran la contradiccion 5-contra-8 de `CONSTANTES-GFX8-DRIVER`.

Consecuencia operativa: la peticion de root **no desbloquea L1, L2 ni los bytes por slot
de scratch**, porque esos tres no salen de ahi en este kernel. Lo que desbloquea es la
geometria de CU, `max_cu_per_sh`, y la cadena de diagnostico.

### 7.3 Tampoco cierra, y conviene saberlo antes de prometerlo

`max_gprs`, `max_gs_threads` y `max_hw_contexts` estan fijos en `gfx_v8_0.c:1682-1684`
para `CHIP_POLARIS12`. `wave_front_size`, `max_waves_per_simd`, `lds_size` y
`max_scratch_slots_per_cu` estan fijos en `gfx_v8_0.c:7122-7126`. `gb_addr_config` es una
constante, `gfx_v8_0.c:65`. Ninguno de esos viene de la ROM.

### 7.4 Si la version de `GFX_Info` resultara ser 2.4 o 2.7

Ahi la ROM **si** contendria `gc_num_gprs`, `gc_wave_size`, `gc_lds_size`,
`gc_max_scratch_slots_per_cu`, `active_cu_per_sh` y compania (offsets +0x30 a +0x3F, y
+0x48 a +0x4C), y el descifrador los imprime. **Pero no los consume este ASIC**: los lee
`amdgpu_atomfirmware.c:942-961`, que es la ruta de ATOMFW, mientras que Polaris12 usa
`amdgpu_atombios_get_gfx_info` y solo lee el prefijo de 12 bytes
(`amdgpu_atombios.c:744-750`). Serian un dato disponible, no un dato en uso. El
descifrador lo dice en la salida de esa rama en vez de presentarlo como geometria viva.

---

## 8. Lo que NO se afirma

Esta seccion existe porque un descifrador sin ella es propaganda.

- **El descifrador NO ha sido probado contra una ROM real.** Ni una. Su entrada real es
  `PermissionError` con el modo `0600` de root. Todo lo que ha visto es el mismo.
- **Sus offsets pueden no coincidir con el layout real.** Vienen de leer el codigo del
  driver, y el codigo dice como el driver **leeria** la ROM, no necesariamente como el
  firmware la **escribio**. Si el firmware tiene una version distinta de la que el driver
  espera, los offsets que el driver usa seran los que el use, esten o no bien.
- **Puede que no haya ATOMBIOS en la ROM.** 128 KiB es el tamano de una ROM PCI, no una
  garantia de que lleve un ATOMBIOS. El vector V16 comprueba que el programa rechaza una
  ROM sin el, y el programa dira `RECHAZO` con el motivo exacto si la real no lo trae.
- **Que no la haya leido no significa que no lo contenga.** Los tres casos de la seccion
  7.2 son «esta ruta no lo lee», no «no esta».
- **La geometria que imprima sera la que el driver lee, no necesariamente la del
  silicio.** `max_cu_per_sh` por `GFX_Info`+8 es lo que `amdgpu_atombios.c:746` copia.
  Que el ASIC tenga 8 CU por SH en vez de 5 no se deduce de ahi; se mide en el hardware.
- **La contradiccion 5-contra-8 no queda resuelta por este trabajo.** Este trabajo
  encuentra **donde** esta el numero que la origina (`GFX_Info`+8). Cual de los dos
  valores consume es otro nodo, con hardware.
- **`is_atom_fw` no se ha verificado.** `amdgpu_bios.c:541` lo define como
  `asic_type >= CHIP_VEGA10`, y el enum de chips **no esta en este arbol**: `soc15.h`
  son 4018 bytes y no lo contiene. No heredo esa comparacion. Lo que si basta, y es lo
  que uso, es `gfx_v8_0.c:1676-1681`.
- **Ningun CRC.** No hay verificacion de CRC en la ruta replicada (seccion 3). Si la ROM
  estuviera corrupta en un byte inocuo, el descifrador no lo detectaria y el driver
  tampoco.

---

## 9. Ficheros creados

```text
03-EXPERIMENTOS/ATOMBIOS-DECODER/rx550_atom_dec.h    303 lineas
03-EXPERIMENTOS/ATOMBIOS-DECODER/rx550_atom_dec.c   ~1700 lineas
08-ARQUITECTURA/ATOMBIOS-DECODER.md                  este fichero
```

No he tocado `04-IMPLEMENTACION/rx550-driver/`, `tools/`, `revkit/` ni `docs/`. **No
he hecho commit**; eso lo deja el nodo principal.

Para compilar y probar:

```sh
gcc -std=c99 -Wall -Wextra -O2 -o rx550_atom_dec rx550_atom_dec.c
./rx550_atom_dec                      # solo self-test
./rx550_atom_dec <ruta-a-la-rom>      # self-test + informe
```

Cuando llegue el momento de la lectura con root:

```sh
sudo cp /sys/bus/pci/devices/0000:01:00.0/rom /tmp/rom.bin
sudo chown 1000:1000 /tmp/rom.bin
./rx550_atom_dec /tmp/rom.bin > informe-1053.txt 2>&1
```

Un `cp` y nada mas: abrir `/dev/dri/renderD129` no hace falta para nada de esto, y sigue
sin estar decidido.

---

## 10. Procedencia

Fuentes leidas, con su hash, para que las citas de este informe sean auditables:

```text
sha256  da1ac6e2c7e34aa894eb9b8ae40e4bed6f14d3dddc015cd3c300eaf0160151ba
        drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c            60399 B, 1951 lineas
sha256  0247ad297df56603ece4e6a15a4687beb8ba694bdb0e6a04128b6f5109676163
        drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.h
sha256  2f543d5518d0a2bfd3a20c0220faac6edf1f1023279c952d503edffc02667dc0
        drivers/gpu/drm/amd/include/atombios.h                  9309 lineas
sha256  b389f8aed3dc383b9a3273bb7ea2c46234c48febe1e00d35405821ae2d6fee97
        drivers/gpu/drm/amd/include/atomfirmware.h              4642 lineas
sha256  8fd0f4888d995db48516e2e70fdf248310e7cf38d95d30bfb008c207658e8bb9
        drivers/gpu/drm/amd/amdgpu/amdgpu_atomfirmware.c        1119 lineas
sha256  6157ba431d5fd2ce19fa40508becd293665ad4ada529b3f76179d509c2b9e3e6
        drivers/gpu/drm/amd/amdgpu/atom.h                       172 lineas
```

`amdgpu_bios.c`, `atom.c`, `gfx_v8_0.c`, `amdgpu_kms.c`, `amdgpu_device.c`,
`kfd_crat.c` y `kfd_device.c` se leyeron enteros o por rango acotado para obtener las
citas, sin hash de registro porque son citas de linea puntual.

Comprobacion de prosa: los tres ficheros se recorrieron con `unicodedata.name()`
buscando nombres que contengan `CJK`, `HIRAGANA`, `KATAKANA`, `HANGUL` o `IDEOGRAPHIC`.
**Resultado: 0 en los tres.** Los unicos caracteres no ASCII son `a` e `i` con tilde,
mas raya y punto medio, todos de nombre latino o de puntuacion.