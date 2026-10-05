# 1489 — el ROM declara las mismas escaleras que la placa ejecuta, y se contradice a sí mismo en 25 mV

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-ROM+CROSS-CHECK+CONTRADICCION+REVISION-PROPIA
TRACK=STATIC(revkit/capturas/amdgpu_vbios.txt) vs MEDIDO(1485) · cero hardware · cero escrituras
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1449-*  el techo de 1500, por TERCERA via
         06-INGENIERIA-INVERSA/findings/1477-*  el sobre de voltaje, con una contradiccion dentro
         06-INGENIERIA-INVERSA/findings/1485-*  y una correccion a mi propio marco
         06-INGENIERIA-INVERSA/findings/0273-*  reproducido y ampliado
ESTADO=PROBADO · la escalera de GRAFICOS del ROM coincide 8/8 BIT-EXACTOS con la medida
       · la escalera de MEMORIA coincide 3/3 bit-exactos, incluido el techo de 1500
       · y el ROM se contradice a si mismo: una tabla declara 1100 mV y otra 1075 mV
       · NO hay tabla PCIe en el ROM, lo que corrige mi propio marco sobre el x4/x16
```

## 1. El bloque, y su tamaño no encaja con ningún struct de upstream

`PowerPlayInfo` es el **índice 15** de datos. Localizado por la **propia tabla maestra del ROM**,
no por mi memoria:

```text
ATOM_ROM_HEADER @0x021C, rev 1.1  ->  tabla maestra de datos @0x97F2  (74 B, 34 u16)
índice  4 -> 0x97FE -> 0x9974  firmwareinfo          (coincide con lo ya medido)
índice 15 -> 0x9814 -> 0x9C0A  powerplayinfo
índice 31 -> 0x9834 -> 0xA6E4  asic_profiling_info
índice 32 -> 0x9836 -> 0xA7F0  voltageobject_info
índice  2 -> 0x97FA -> 0x0000  smc_dpm_info           AUSENTE
```

```text
0x9C0A:  usStructureSize = 778   frev = 7   crev = 1
0x9C0A + 778 = 0x9F14  =  exactamente donde empieza displayobjectinfo (indice 22)
```

**Y el tamaño no encaja con nada que exista upstream.** Medido compilando los structs con gcc
bajo `#pragma pack(1)`, no suponiendo:

```text
ATOM_PPLIB_POWERPLAYTABLE      = 37 B
ATOM_PPLIB_POWERPLAYTABLE2/3/4 = 40 / 46 / 66
ATOM_PPLIB_POWERPLAYTABLE5     = 88 B      <-- el ultimo de la familia
ATOM_POWERPLAY_INFO             = 178 B
ATOM_POWERPLAY_INFO_V3          = 186 B
                                       778  !=  ninguna
```

`atombios.h` no tiene `ATOM_POWERPLAY_INFO_V4..V7`; sólo V2 y V3. `pptable.h` para en 5.
**Y la selección del driver es por TAMAÑO, nunca por revisión** (`legacy_dpm.c:211-212`, `:242`,
`:327-328`); `ucTableFormatRevision` no se lee en ningún sitio del parseo.

> **La revisión 7/1 de este ROM no tiene struct.** Eso no invalida el contenido —los bloques
> Los localizo por unicidad — pero significa que **el layout de la cabecera rev 7 es
> `NOT_DETERMINED`**, y que quien lo consuma lo hace como un caso no previsto.

## 2. LA ESCALERA DE GRÁFICOS: coincide 8/8, bit a bit

Tres arrays dentro del bloque, cada uno **con una única solución en los 58 880 bytes del ROM**
(búsqueda de N-tuplas ordenadas a todos los strides 2..64 sobre la imagen entera).

**8 registros × 15 B @ `0x9D1A`, `u32` en record+0, unidad 10 kHz:**

| est | ROM | raw | MHz | **medido** | Δ |
|--:|---|--:|--:|--:|--:|
| 0 | `0x9D1A` | 21400 | 214 | 214 | **0** |
| 1 | `0x9D29` | 55100 | 551 | 551 | **0** |
| 2 | `0x9D38` | 73400 | 734 | 734 | **0** |
| 3 | `0x9D47` | 98000 | 980 | 980 | **0** |
| 4 | `0x9D56` | 100000 | 1000 | 1000 | **0** |
| 5 | `0x9D65` | 102000 | 1020 | 1020 | **0** |
| 6 | `0x9D74` | 104600 | 1046 | 1046 | **0** |
| 7 | `0x9D83` | 107100 | **1071** | **1071** | **0** |

**Ocho de ocho, sin promediar nada.** Incluye el 551, que es el valor más raro de la lista y el
que más delata un error de lectura. La unidad de 10 kHz **no está supuesta**: es la misma
codificación de 3 bytes (`usEngineClockLow` u16 + `ucEngineClockHigh` u8, `pptable.h:430-431`)
que lee `si_dpm.c:7255-7256`, y produce los ocho enteros exactos.

## 3. LA ESCALERA DE MEMORIA: coincide 3/3, techo incluido

**3 registros × 13 B @ `0x9D98`, `u32` en record+0:**

| niv | ROM | raw | MHz | **medido** | Δ |
|--:|---|--:|--:|--:|--:|
| 0 | `0x9D98` | 30000 | 300 | 300 | **0** |
| 1 | `0x9DA5` | 62500 | 625 | 625 | **0** |
| 2 | `0x9DB2` | 150000 | **1500** | **1500** | **0** |

> **El techo de memoria de 1500 MHz queda corroborado por TERCERA vía independiente**: la tabla
> DPM que puebla el driver desde la SMU (`pp_dpm_mclk`), la medición en la placa bajo carga
> (hallazgo 1485, 57/57 muestras), y ahora **el propio ROM**. Tres fuentes, un número.

Y el `FirmwareInfo.ulDriverTargetMemoryClock = 360000` y `ulASICMaxMemoryClock = 62610` siguen
discrepando de 1500 MHz. **Son otros dos campos, no la escalera** — la escalera existe y es
inequívoca, y esos dos números siguen `NOT_DETERMINED` sin tocar la escalera.

## 4. UNA CONTRADICCIÓN DENTRO DEL PROPIO ROM

Y aquí hay algo que no buscaba y que es un hallazgo limpio.

**10 registros × 8 B @ `0x9C83`, `u16` en record+0:**

```text
700, 750, 800, 850, 875, 900, 950, 1000, 1050, 1100   mV
```

fronteira comprobada: la entrada anterior (`0x9C7B`) vale 0 y la siguiente (`0x9CD3`) vale 2048, así
que son exactamente 10.

Y en la **misma imagen**, `ASIC_ProfilingInfo` @ `0xA6E4` dice:

```text
ulMinVddc / 100 =  700 mV     <-- COINCIDE EXACTAMENTE con el minimo de la escalera
ulMaxVddc / 100 = 1075 mV     <-- DISCREPA en +25 mV del maximo de la escalera
```

> **Dos tablas del mismo ROM discrepan 25 mV en el techo de voltaje.** El mínimo coincide al
> milivoltio, lo que dice que las dos tablas hablan de la misma magnitud; y el máximo no.
>
> **No lo resuelvo y no elijo cuál tiene razón.** Las dos son fuente primaria del fabricante
> sobre el mismo componente, y una de las dos se equivoca —o las dos usan un criterio
> distinto del que les estoy suponiendo—. Lo que sí es `PROBADO` es que la contradicción existe
> y vale 25 mV.

**Y un dato sobre el punto de trabajo medido:** el hallazgo 1485abe midió **881 mV** con carga
completa. **881 no es ningún escalón** de esta escalera —los vecinos son 875 y 900—. O sea que
**la SMU interpola** y no se limita a los escalones declarados. Eso es una observación, no una
interpretación: 881 está entre 875 y 900 y no es ninguno de los dos.

**Unidad de la escalera de voltaje: `PARTIAL`.** Ningún struct la documenta. mV es la única
lectura bajo la cual los números son físicamente sensatos y están a 25 mV de una tabla vecina,
pero es una inferencia mía, no una declaración de la fuente.

## 5. NO hay tabla PCIe, y eso corrige MI marco

Busqué una tabla de estados PCIe en el bloque y en todo el ROM: **cero hallazgos creíbles**.
Barrido de ≥2 registros con forma (generación∈{1..5}, carriles∈{1,2,4,8,16}) a strides 2..32, y
búsqueda de conteos de carriles 8/16/32 en `u16` en todo el bloque. Y la tabla que históricamente
llevaba los estados DPM del SMC, el **índice 2 `smc_dpm_info`, es `0x0000`: ausente.**

> **Consecuencia, y es una corrección a lo que dije en mi mensaje anterior.** Yo señalé el
> "x4 a 5 GT/s frente al x16 que declara `pp_dpm_pcie`" como la siguiente discrepancia a
> medir. **Es un marco equivocado**: el ROM **no declara nada** del ancho de este enlace. No hay
> contradicción ROM↔hardware que medir; `2.5GT/s x8` y `5.0GT/s x16` son una afirmación **del
> firmware de la SMU**, como lo son las escaleras de reloj, y **para los relojes la afirmación de
> la SMU coincide con el ROM y para el enlace no hay con qué compararla.**
>
> La asimetría es real y es lo destacable: los relojes tienen declaración en el ROM, el enlace
> no. Por qué, `NOT_DETERMINED`.

## 6. Una lectura fuera de límites latente

Por la selección por tamaño, el gate lee `usTableSize` (offset de struct 19 → ROM `0x9C1D`), que
vale **32768**. Como `32768 >= 88` (PPLIB5), **la rama PPLIB5 se toma**. Entonces lee
`usFanTableOffset` = **34048** y calcula `bios + 0x9C0A + 34048 = 0x1210A` = **74 042**, que está
**pasado el final del buffer de 58 880 bytes.**

Eso es una lectura fuera de límites en código de PowerPlay legacy. **Pero no la atribuyo a esta
tarjeta**: en Polaris10 las `pp_funcs` vienen de `polaris10_smumgr.c`, no de la tabla legacy, y no
existe ningún símbolo `platform_caps` bajo `pm/powerplay/smumgr/`. Es coherente con que las tablas
DPM vengan de la SMU.

**Estado honesto:** *"la lectura mala es alcanzable en esta tarjeta"* = `NOT_DETERMINED`, porque no
he trazado el grafo de llamadas completo. *"El desajuste de tamaño existe en upstream"* =
**`PROVEN`**.

## 7. Procedencia

```text
fichero  revkit/capturas/amdgpu_vbios.txt   58 880 B, lectura binaria
localiz  ATOM_ROM_HEADER @0x021C -> tabla maestra de datos @0x97F2 -> indice 15 = 0x9C0A
structs  include/atombios.h:9054-9088      ATOM_POWERPLAY_INFO y V2/V3   (no hay V4..V7)
         include/pptable.h:174-246          ATOM_PPLIB_POWERPLAYTABLE..5  (la familia acaba en 5)
         include/pptable.h:430-431         usEngineClockLow / ucEngineClockHigh
         include/atomfirmware.h:243-262    atom_rom_header_v2_2
         include/atomfirmware.h:429-433    atom_master_data_table_v2_1
driver   pm/legacy-dpm/legacy_dpm.c:211-212,242,327-328   seleccion POR TAMANO
         pm/legacy-dpm/si_dpm.c:7255-7256  la lectura de 3 bytes del reloj de graficos
medido   pp_dpm_sclk y pp_dpm_mclk (hallazgos 1449 y 1485)
```

```text
ESTADO=PROBADO · escalera de GRAFICOS del ROM = escalera medida, 8/8 BIT-EXACTOS
       · escalera de MEMORIA del ROM = escalera medida, 3/3 bit-exactos, techo 1500 incluido
       · usStructureSize = 778 no encaja con NINGUN struct de upstream {37,40,46,66,88,178,186}
       · y la seleccion del driver es por tamano, nunca por revision
NUEVO CONTRADICCION  dentro del propio ROM: PowerPlayInfo declara una escalera de VDDC de
       700..1100 mV (10 pasos, @0x9C83) y ASIC_ProfilingInfo declara 700..1075 mV.  El minimo
       coincide al milivoltio; el maximo discrepa en +25 mV.  No se resuelve cual tiene razon
NUEVO  el punto de trabajo medido (881 mV, hallazgo 1485) NO es ningun escalon de la escalera
       declarada: los vecinos son 875 y 900.  La SMU interpola
CORRECCION PROPIA  yo defini el "x4 real frente a x16 declarado por pp_dpm_pcie" como la
       siguiente discrepancia a medir.  Es un marco equivocado: el ROM NO declara nada del
       ancho de enlace, y smc_dpm_info esta AUSENTE.  No hay contradiccion ROM<->hardware que
       medir; pp_dpm_pcie es una afirmacion solo de la SMU
PROBADO NEGATIVO  no hay struct de PowerPlayInfo rev 6/7 upstream.  Y no hay en el ROM ningun
       identificador SocketAngle/SOCKET_ANGLE (0 coincidencias en include/), asi que no hay
       struct al que decodificar contra
NOT_DETERMINED  el layout de la cabecera rev 7 mas alla del byte 3; la semantica de las colas
       de los registros de 15 B (+4,+8,+12,+14) y de 13 B (+4..+12); la columna u32@+8 =
       {0,3000,3000,3000,1500,1500,1500,1500}, que NO decodifica a {300,625,1500} bajo ninguna
       unidad que sepa justificar; la unidad de la escalera de voltaje (mV es la unica lectura
       sensata, pero es inferida); y si la rama PPLIB5 llega a ejecutarse en esta tarjeta
LIMITE  tres de los arrays del bloque tienen contenido sin nombre.  Los localizo por unicidad y
       describo su contenido, pero no los nombro
RIESGO  ninguno.  CERO escrituras, cero hardware, cero acceso a la GPU
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active
Siguiente  1) las colas de los registros de 15 y 13 bytes: son el unico contenido del bloque que
           no tiene semantica, y son 8 y 3 registros respectivamente
         2) la contradiccion de 25 mV: cual de las dos tablas manda.  El discriminante barato es
           si la SMU llega a pedir un voltaje de la escalera por encima de 1075, y eso se ve
           forzando el reloj con carga y leyendo amdgpu_pm_info.  Es medible con lo que ya hay
         3) el enlace: sin declaracion en el ROM, la pregunta del x4/x16 es del firmware de la
           SMU y solo se responde con instrumentacion del enlace, no con el ROM
```

## 8. Por qué esto importa más de lo que parece

La tabla DPM que el driver expone **no** viene del ROM: la puebla el firmware de la SMU y la
sube a SM RAM. Eso lo Sabía el hallazgo 1449. Lo que **no** sabía nadie es si la SMU se inventa
los valores o si los copia de un sitio.

> **Copia.** Las dos escaleras coinciden **bit a bit** con lo que el ROM declara, en once valores
> y sin una sola excepción. La probabilidad de que eso sea casualidad es despreciable, y la
> coincidencia incluye el 551 —el valor más raro de la lista—, que es exactamente donde un error
> de decodificación se delataría.

**Eso convierte la escalera de la SMU en hardware documentado**, no en un artefacto opaco. Y para
el objetivo del proyecto eso es exactamente lo que hace falta: un driver especializado necesita
saber qué estados existen y qué significan, y ahora se sabe que los estados que el silicio
recorre están escritos por el fabricante en la propia placa, con su número exacto, en un offset
conocido.