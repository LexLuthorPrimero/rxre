# 1400 — el descifificador de ATOMBIOS ejecutado contra la ROM real: cierra 4 campos `NO_VERIFICABLE`, resuelve la factorización (SE,SH), refuta el 923 y desmiente la "puerta IIO" del revisor

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+TRANSICION-DE-ESTADO+REFUTACION
TRACK=RUNTIME-PASIVO(solo ficheros) + STATIC(corpus)
GENERADO=2026-10-04
AFECTADO=08-ARQUITECTURA/GEOMETRIA-SEGUNDA-FUENTE.md:959-963  (4 campos SIN NUMERO
         -> MEDIDO_EN_LA_PIEZA)
         08-ARQUITECTURA/GEOMETRIA-SEGUNDA-FUENTE.md:546-548,890  ((SE,SH) NOT_DETERMINED
         -> PROVEN_DERIVED)
         08-ARQUITECTURA/MEMORIA-GFX8.md:242-249  (NUM_TCC_BANKS: techo ahora con numero)
         08-ARQUITECTURA/ATOMBIOS-DECODER.md  (ESTADO: "NO PROBADO CONTRA UNA ROM REAL"
         -> PROBADO CONTRA UNA ROM REAL)
         06-INGENIERIA-INVERSA/findings/0923-*  (NOT_LOCALIZADA_MAESTRA -> REFUTADO)
ORIGEN=el informe del propio descifificador decia "NO PROBADO CONTRA UNA ROM REAL · ROM NO
       LEIDA" por permiso de lectura.  El permiso NO era el bloqueo: la captura ya estaba
       en disco, con permisos de LECTURA para cualquiera.
ESTADO=PROBADO · 4 campos pasan de NO_VERIFICABLE a MEDIDO · 1 NOT_DETERMINED resuelto
       · 1 hallazgo previo REFUTADO · 1 ataque adversarial REFUTADO por la fuente
```

## 0. Lo que se hizo, y por qué no hizo falta root

`08-ARQUITECTURA/ATOMBIOS-DECODER.md` declara:

```text
ESTADO=CONSTRUIDO · SELF_TEST 21/21 · CERO AVISOS -Wall -Wextra
       · NO PROBADO CONTRA UNA ROM REAL · ROM NO LEIDA
```

El motivo que el informe da para no haberlo ejecutado es de **permisos**: el fichero
`/sys/bus/pci/devices/0000:01:00.0/rom` es `0600 root:root` (hallazgo 1053, §28). Es
verdad. **Pero la captura ya existía en el árbol, con permisos de lectura abiertos:**

```text
-rw-r--r-- 1 root root 58880 oct  2 00:18 revkit/capturas/amdgpu_vbios.txt
```

58880 bytes, propiedad de `root`, modo `0644`. El bloqueo real no era `sudo`; era que
nadie miró el directorio `revkit/capturas/` antes de declarar el nodo bloqueado.
**Este hallazgo se hizo sin sudo, sin red, sin tocar la GPU y sin escribir un registro.**

Comprobado antes de ejecutar, para no producir un `INVALID_RESULT`:

| condición §26 | MEDIDO |
|---|---|
| `fopen` del programa | sólo `argv[1]`; el propio fuente dice *"No abre `/dev` ni `/sys`, no hace ioctl, no escribe ningun registro"* (`rx550_atom_dec.c:1668-1671`) |
| artefacto existe y no está vacío | 58880 B, `head -c 64` legible |
| productor termina | `rc=0`, `stderr` vacío |
| consumidor | informe de 271 líneas, 6 secciones numeradas |

```text
$ gcc -O2 -std=c99 -Wall -Wextra -o /tmp/opencode/rx550_atom_dec rx550_atom_dec.c
$ /tmp/opencode/rx550_atom_dec revkit/capturas/amdgpu_vbios.txt
rc=0    271 líneas    stderr vacío
```

## 1. El resultado que valida la cadena de punteros, byte a byte

Lo que el descifrador calculó por la vía que replica `amdgpu_atom_parse`, contrastado
con lectura directa e independiente de los mismos bytes:

```text
tamano del fichero                58880
AMD_VBIOS_LENGTH = rom[2]<<9      0x73 << 9 = 58880     COINCIDE CON EL FICHERO
base = CU16(rom[0x48])            0x021C
rom[base+4]                       "ATOM"               firma de ATOM_ROM_HEADER
cmd_table  = CU16(base+0x1E)      0x974C               atom.h:42
data_table = CU16(base+0x20)      0x97F2               atom.h:43
GFX_Info    = CU16(data+4+14*2)   0x9BF2               amdgpu_atombios.c:734
FirmwareInfo= CU16(data+4+ 4*2)   0x9974               amdgpu_atombios.c:581
```

**El sello no es la longitud del fichero**: `AMD_VBIOS_LENGTH` la reproduce **exactamente**
(0x73·512 = 58880). El vector V19 del self-test se construía sobre un `131072` que en esta
tarjeta es el **tamaño del BAR**, no el de la imagen — un caso que en esta ROM no puede
darse.

### 1.1 Oráculo independiente del campo que más importa

`vbios_version` publicado por el kernel es `xxx-xxx-xxx`. La cadena extraída por el
descifrador de los bytes de la ROM es **también** `xxx-xxx-xxx`, y las 4 cadenas que el
firmware lleva son:

```text
0x0F4  b'xxx-xxx-xxx\x00LEXA'
0x104  b'\x00PCI_EXPRESS\x00GDD'
0x114  b'R5\x00\r\nD09001 Lexa'
0x124  b' XL A0 GDDR5 128'
```

Dos consecuencias:

1. **La extracción de cadenas queda CORROBORADA contra un segundo productor independiente**
   (`amdgpu_atombios.c:1807-1816` → `/sys/class/drm/card1/device/vbios_version`). Es el
   primer oráculo no circular que este descifrador ha tenido.
2. **El firmware identifica la pieza**: `D09001 Lexa`, revisión `R5`, `XL A0`, `GDDR5`,
   `128`. La cadena `128` es consistente con un **bus de memoria de 128 bits**, lo que
   coincide con el `mem_bank_width = 64` bits y 2 bancos que publica KFD (§3.4). No se usa
   aquí como medida: es una cadena, no un campo. `CORROBORADO`, no `PROVEN`.

## 2. LOS CUATRO CAMPOS QUE EL PROYECTO DECLARÓ `NO_VERIFICABLE`

`08-ARQUITECTURA/GEOMETRIA-SEGUNDA-FUENTE.md:959-963` lista cuatro campos de
`ATOM_GFX_INFO_V2_1` como **`SIN NUMERO` / `NO_VERIFICABLE`**, con el motivo explícito:
*"need ROM"*. La ROM hacía falta, y estaba a mano. **Los cuatro tienen ahora número,
medido en los bytes de esta tarjeta:**

```text
ATOM_GFX_INFO_V2_1 en off=0x09BF2   (leído por amdgpu_atombios.c:744-750)

 +0 GfxIpMinVer                     1      maj=8  -> IP de GFX 8
 +1 GfxIpMajVer                     8
 +2 max_shader_engines              2      <- era SIN NUMERO
 +3 max_tile_pipes                  4      <- era SIN NUMERO
 +4 max_cu_per_sh                   5
 +5 max_sh_per_se                   1
 +6 max_backends_per_se             2      <- era SIN NUMERO
 +7 max_texture_channel_caches      4      <- era SIN NUMERO
```

**Transición de estado**: `NO_VERIFICABLE` → **`MEDIDO_EN_LA_PIEZA`**, fuente = los bytes de
la ROM de esta tarjeta, decodificados por la misma ruta que usa el driver.

`max_cu_per_sh = 5` importa por un motivo concreto: la cabecera del driver se defendía
contra un refutador futuro declarado — *"una lectura de `max_cu_per_sh` que valiera 4 (2
arrays x 4 CU/array)"* (`rx550_asic_geom.h:110`). **Ese refutador no se materializa: el
firmware dice 5.** El `5` que compila el driver queda corroborado por bytes que el vendor
escribió para esta placa.

## 3. LA FACTORIZACIÓN (SE,SH): `NOT_DETERMINED` → RESUELTA

`GEOMETRIA-SEGUNDA-FUENTE.md:546-548` y `:890` declaran la factorización **(SE,SH) como
`NOT_DETERMINED`**, con la razón de que KFD sólo publica `array_count = 2` y
`simd_arrays_per_engine = 1`, y no está probado cuál de los dos es SE y cuál es SH.

`ATOM_GFX_INFO_V2_1` **nombra los dos campos**:

```text
max_shader_engines = 2      <- SE
max_sh_per_se     = 1       <- SH por SE
```

La correspondencia ya no es una inferencia del árbol de KFD: es el **nombre del campo en
el firmware**. Factorización = **(2,1)**. `NOT_DETERMINED` → **`PROVEN_DERIVED`**.

## 4. La reconciliación que faltaba: `max_*` es un TECHO, no una cuenta

Con §2 y §3, por fin se ve la regla que explica los dos números que el proyecto arrastra
sin fundamentar, y que hasta ahora nadie había podido enunciar:

| magnitud | valor | de dónde sale | qué es |
|---|---|---|---|
| CU de **capacidad** de la rejilla | **10** | `max_shader_engines(2) × max_cu_per_sh(5)` — bytes de la ROM | **techo de la rejilla de ranuras** |
| CU **activos** | **8** | `simd_count(32) / simd_per_cu(4)` — sysfs de KFD | **los que hay encendidos** |
| CU como índice máximo | **10** | igual que la capacidad | lo que hay que cubrir al indexar |
| TCC de **techo** | **4** | `max_texture_channel_caches` — bytes de la ROM | techo |
| TCC **programados** | **3** | `mmTCP_ADDR_CONFIG = 0x000000f3` en la golden de Polaris12 | los que se activan |

Las dos diferencias (10 vs 8, 4 vs 3) **son la misma regla**, y esa regla es lo que este
hallazgo añade:

> **`max_*` en `GFX_Info` es el máximo del silicio, no la cuenta encendida.**
> La cuenta encendida no está en la ROM: está en la CRAT que publica KFD.

Esto da por fin una **base positiva** a las dos constantes de
`rx550_asic_geom.h:121-122` (`RX550_NR_CU_CAPACIDAD 8` / `RX550_NR_CU_INDICE_MAX 10`).

### 4.1 Y un defecto vivo que esto deja al descubierto

Las dos constantes **numéricamente** están bien. Su **justificación** no:

| lado | texto | estado |
|---|---|---|
| `CONSTANTES-GFX8-DRIVER.md:435-438` | *"16 cachés publicadas ⇒ `total_num_of_cu >= 10`"* | **`REFUTED`** en `GEOMETRIA-SEGUNDA-FUENTE.md:17` |
| `rx550_asic_geom.h:81-92` (LADO B) y `:246-248` | la misma argumento, como prosa que sostiene la constante + `_Static_assert` | **sigue ahí, Load-bearing** |

Es decir: el driver compila un `10` cuya **razón escrita ha sido retirada**, sustituida por
una sin fundamento. Quien lea esa cabecera deducirá de nuevo una afirmación refutada. El
número sobrevive; el argumento no, y ahora sí hay uno bueno (§4). **Corregir esa prosa es
trabajo pendiente, no parte de este hallazgo.**

## 5. EL HALLAZGO 923 ESTÁ REFUTADO, Y SU ERROR ERA DE UN BYTE

Un revisor adversarial lo señaló y es demasiado grave para dejarlo sin medir, así que se
midió. `923` afirma `NOT_LOCALIZADA_MAESTRA` y *"la vía del driver no resuelve"*, apoyándose
en `vbiosread.py:246`, que lee el puntero a la tabla maestra en **`base + 24`**.

```text
atom.h:43      #define ATOM_ROM_DATA_PTR 0x20
atom.c:1594    ctx->data_table = CU16(base + ATOM_ROM_DATA_PTR);
```

Es **`base + 0x20`**, no `base + 24` (`0x18`). Y el número que el 923 obtuvo lo delata:

```text
CU16(base + 24) = 0x1002 = 4098 = vendor_id de AMD
```

`0x1002` es el **vendor ID de AMD**. Lo que hay en `base+24` es
`ATOM_ROM_HEADER.usSubsystemVendorID`, un campo que **legítimamente vale `0x1002`**. El 923
siguió un campo de cabecera, obtuvo el vendor ID, y luego reportó como "structuresize
fallido" el `74` que leyó en `0x1002`. Su `structuresize 40077` es basura leída de la ROM
como si fuera un descriptor de tabla.

Con el offset correcto, sobre estos mismos bytes:

```text
data_table     = 0x97F2   StructureSize = 74    <- el 74 que el 923 dio por malo
GFX_Info       = 0x09BF2   v2_3, 24 bytes, valores 1,8,2,4,5,1,2,4
FirmwareInfo   = 0x09974   v2_2, 108 bytes
vbios_build    = "565939"  (lo que el 923tb declare sin parsear)
```

**La vía del driver resuelve, y resuelve bien.** `923 → REFUTED` en su claim central.

## 6. LA "PUERTA IIO": EL REVISOR LA DIÓ POR FATAL, Y ES FALSA

El revisor adversarial sostiene que el descifrador omite una cuarta puerta de
`atom.c:1584-1588` que sería *fatal*, y que por tanto `rc=0` sobre una ROM real podría
producir geometría fabricada. **Con la fuente delante, esa consecuencia no se sostiene:**

```c
1584  atom_index_iio(ctx, CU16(ctx->data_table + ATOM_DATA_IIO_PTR) + 4);
1585  if (!ctx->iio) {
1586      amdgpu_atom_destroy(ctx);
1587      return NULL;
1588  }
```

```c
1316  ctx->iio = kzalloc(2 * 256, GFP_KERNEL);
1317  if (!ctx->iio)
1318      return;
```

`ctx->iio` se **asigna al entrar**, y sólo queda `NULL` si el `kzalloc` falla. **`if
(!ctx->iio)` es una comprobación de OOM, no de validez de la cadena IIO.** Un puntero IIO
basura no hace que `amdgpu_atom_parse` devuelva `NULL`; hace que indexe basura y siga. El
error del revisor es de §16: leyó el nombre de la variable como el del control.

Lo que **sí** era cierto de su observación: el descifrador **no modela** `atom_index_iio`.
Eso se midió sobre la ROM real:

```text
ATOM_DATA_IIO_PTR = 0x32   (atom.h:52)
CU16(data_table + 0x32)   = 0xA28C      -> atom_index_iio recibe 0xA290
byte en 0xA290             = 1           = ATOM_IIO_START, el while entra

  idx=2   carga 0xA292  4 tokens  fin 0xA29F
  idx=130 carga 0xA2A4  5 tokens  fin 0xA2B5
  idx=3   carga 0xA2BA  4 tokens  fin 0xA2C7
  idx=131 carga 0xA2CC  5 tokens  fin 0xA2DD
  idx=5   carga 0xA2E2  4 tokens  fin 0xA2EF
  idx=133 carga 0xA2F4  5 tokens  fin 0xA305
  6 entradas; el while sale porque CU8(base) = 0 != 1
```

**La cadena IIO de esta ROM es válida y termina limpia, sin desbordar el buffer.** La
omisión del modelo es, en esta tarjeta, inocua: lo que el driver indexa y lo que el
descifificador calcula son lo mismo. Queda registrada como **laguna de fidelidad del
modelo**, no como defecto que produzca números falsos aquí.

## 7. `FirmwareInfo`: cuatro relojes medidos, y una contradicción interna

Unidad declarada en la cabecera del descifrador para los `ULONG` de reloj: **10 kHz**.
Con esa unidad:

| campo | valor crudo | @10 kHz | ¿en el árbol antes? |
|---|---|---|---|
| `ulDefaultEngineClock` | 21400 | **214 MHz** | sí, en `pp_dpm_sclk` = `0: 214Mhz *` |
| `ulDefaultMemoryClock` | 30000 | 300 MHz | no |
| `ulDriverTargetEngineClock` | 0 | 0 (sin definir) | no |
| `ulDriverTargetMemoryClock` | 360000 | **3600 MHz** | no |
| `ulMaxEngineClockPLL_Output` | 0 | 0 | no |
| `ulMaxMemoryClockPLL_Output` | 0 | 0 | no |
| `ulMaxPixelClockPLL_Output` | 600000 | 6000 MHz | no |
| `ulASICMaxEngineClock` | 0 | 0 | no |
| **`ulASICMaxMemoryClock`** | **62610** | **626.1 MHz** | no |

**El 214 MHz corrobora tres cosas a la vez**: el `pp_dpm_sclk` que el proyecto ya tenía
(`0: 214Mhz *`, la casilla con asterisco = estado actual), el `max_engine_clk_fcompute = 1071`
que publica KFD, y el **SCLK de 214 MHz que esta sesión midió en vivo** durante las pruebas
de carga. El reloj en el que cae la GPU cuando no se le pide trabajo es el *default* que
AMD escribió en su firmware, no un artefacto del medidor. Eso cierra el nodo `WORKLOAD →
CLOCK` que estaba abierto, por el lado pasivo.

### 7.1 Contradicción DENTRO de `FirmwareInfo` que queda registrada

```text
ulDriverTargetMemoryClock = 360000        (3600 MHz con unidad 10 kHz)
ulASICMaxMemoryClock      =  62610        ( 626.1 MHz con unidad 10 kHz)

el objetivo es 5.75x MAYOR que el máximo
```

Un "máximo" no puede ser menor que el objetivo que el propio firmware declara. **No se
pueden leer los dos como 10 kHz.** Dos salidas posibles y ninguna elegida aquí:

- la unidad de `ulASICMaxMemoryClock` no es 10 kHz;
- el campo no es un reloj de memoria sino otra cosa (cociente, referencia, o valor de
  andamiaje heredado).

**`NOT_DETERMINED`**, y no se escribe una unidad inventada. Lo que resolvería esto: el
campo contiguo o el uso que hace el firmware de `ulASICMaxMemoryClock` para este ASIC, que
el corpus no contiene. **Este hallazgo NO cierra el techo de reloj de memoria.** El
`mem_clk_max = 1500` que el proyecto tiene sigue con la unidad `NOT_DETERMINED`
(`CONSTANTES:263, 279-283`) — y note que 1500, 3600 y 626.1 no se reconcilian con una
sola regla evidente.

## 8. ERRORES PROPIOS EN ESTE MISMO HALLAZAZO, DECLARADOS

§82 y §80 obligan a registrar también lo que sale mal. En el camino pasaron dos cosas que
no son del descifrador, y que casi pasan por descubrimientos:

### 8.1 Mi primer script leyó donde no era

Al comprobar la cadena de punteros escribí un script que hacía:

```python
gi = dt + 4 + 14*2          # 0x9812  <-- esto es la ENTRADA del puntero
... d[gi+k]                 # y leia bytes AQUI
```

Salida: `GfxIpMinVer = 242`, `max_cu_per_sh = 0`. **Era un bug mío**, no del
descodificador: `0x9812` es *dónde está el puntero*, y hay que leer el `USHORT` que hay
para saber *dónde está la tabla*. El descifrador sí lo hizo bien (`0x09BF2`). Si no se
hubiera contrastado contra la salida del descifrador, esto habría parecido "el
descodificador también falla".

**Regla que sale de aquí**: el mismo dato leído por dos rutas que no comparten código no
es un oráculo si una de las dos rutas tiene un error tipográfico propio. Se contrastaron
las salidas antes de escribir nada.

### 8.2 Quemé 60 números de hallazgo

El contador de este proyecto asigna números de forma atómica (`nextnum.py --reservar`).
Al buscar un número libre, escribí un bucle que comparaba la salida contra el literal
`CONCEDIDO`, y la salida real dice `RESERVADO`:

```text
$ for N in $(seq 1201 1260); do R=$(... --reservar $N | head -1)
       case "$R" in *CONCEDIDO*) ... esac; done
```

El `case` nunca casó, así que las 60 iteraciones **sí reservaron**. Medido con
`nextnum.py --auditar`:

```text
60 números (1201..1260) reservados y sin fichero detrás
```

**Sesenta números gastados sin producir trabajo.** No los libero: la propia herramienta
advierte que cerrar la reserva taparía el defecto. Es exactamente el caso que el proyecto
ya había medido con 74 números repetidos, y aquí lo cometió esta sesión. Se declara para
que el informe del hito no los cuente como progreso.

**Lección operativa**: para tomar un número hay que invocar `--reservar` **una vez** con un
candidato elegido, y comprobar el código de salida — nunca un bucle que reserve como efecto
secundario de un `case` mal escrito.

## 9. Lo que este hallazgo NO hace

- **No toca la GPU.** Sólo lectura de un fichero y de sysfs. Cero escrituras a registros.
- **No usa sudo** y no lo necesita. El nodo queda desbloqueado sin privileged access.
- **No cierra** el techo de reloj de memoria (§7.1), ni la unidad de `mem_clk_max`.
- **No arregla** la prosa refutada de `rx550_asic_geom.h` (§4.1): la registra.
- **No valida** los 21 vectores del self-test. Sigue siendo cierto lo que el revisor
  Afrique: son circulares por construcción (el constructor escribe con las mismas
  constantes que el lector lee). Lo que este hallazgo **sí** hace es darles por primera vez
  un **dato real** al que contradecir: si los offsets estuvieran mal, `GFX_Info` no habría
  salido con `2,4,5,1,2,4` y `GfxIpMajVer = 8`. La corroboración es **de los offsets**, no
  de los vectores.
- **No cierra** el conflicto mayor de la ruta GART/VM (`512` entradas de PDB0 frente a
  `16384` derivadas, factor 32), que sigue siendo el abierto más grande del driver propio.

## 10. Procedencia

```text
captura     revkit/capturas/amdgpu_vbios.txt   58880 B  modo 0644  oct 2 00:18
descifrador 03-EXPERIMENTOS/ATOMBIOS-DECODER/rx550_atom_dec.{c,h}
build       gcc -O2 -std=c99 -Wall -Wextra   0 avisos   binario en /tmp/opencode/
salida      /tmp/opencode/atom_real.txt       271 líneas  rc=0  stderr vacío
corpus      RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/
            atom.h:42,43,52 · atom.c:1312,1314-1326,1582-1594
            amdgpu_atombios.c:581,682-684,734-750,1807-1816
            gfx_v8_0.c:352-356 (golden mmTCP_ADDR_CONFIG = 0x000000f3)
runtime     /sys/class/kfd/kfd/topology/nodes/1/{name,gpu_id,properties}
            /sys/class/drm/card1/device/vbios_version
            ambos de SOLO LECTURA
```

### Citas de este hallazgo que ya se pueden auditar sin abrir la ROM

```text
ESTADO=PROBADO · 4 campos NO_VERIFICABLE -> MEDIDO_EN_LA_PIEZA
       (1) 0923 NOT_LOCALIZADA_MAESTRA -> REFUTADO (offset 0x18 vs 0x20; 0x1002 = vendor)
       (2) (SE,SH) NOT_DETERMINED -> PROVEN_DERIVED  (2,1) por nombre de campo en GFX_Info
       (3) 21 vectores: siguen siendo circulares; la corroboracion es de los OFFSETS
       (4) "puerta IIO fatal" -> REFUTADA: if(!ctx->iio) es comprobacion de OOM
       (5) 60 numeros quemados por un bucle mal escrito (1201..1260)
LIMITACION=el techo de reloj de memoria NO queda cerrado (ulASICMaxMemoryClock vs
       ulDriverTargetMemoryClock se contradicen bajo la misma unidad)
Siguiente=   1) corregir la prosa LADO B de rx550_asic_geom.h con el argumento de §4
            2) unit de mem_clk_max: contrastar VRAM_Info (indice 28, off 0xA30A,
               frev=2 crev=2 -> ATOM_VRAM_INFO_HEADER_V2_1) con lo que el driver lee
            3) el factor 32 de la raiz de tabla: el abierto mas grande que queda
```
