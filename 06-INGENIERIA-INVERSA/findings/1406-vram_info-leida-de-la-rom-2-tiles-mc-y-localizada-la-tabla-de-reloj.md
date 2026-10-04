# 1406 — `VRAM_Info` leída de la ROM: 2 tiles MC, 1 módulo VRAM, y localizada la tabla de parcheo de reloj de memoria

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+CERRADURA-DE-HUECO
TRACK=RUNTIME-PASIVO(fichero) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=08-ARQUITECTURA/MEMORIA-GFX8.md  (barrera de VRAM_Info: "no la tiene el decodificador")
         09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-*  (el techo de reloj de memoria, que el
         hallazgo 1400 dejo NOT_DETERMINED, tiene ahora su tabla localizada)
ORIGEN=revision adversarial del decifrador de ATOMBIOS: de 35 indices de la tabla maestra,
       el descifrador resuelve 2 (GFX_Info=14, FirmwareInfo=4).  senalo que VRAM_Info (28)
       era el caro.  aqui se resuelve.
ESTADO=PROBADO · la tabla existe, esta presente y se lee · 3 numeros con control interno
       · corrobora el 2 de los bancos de memoria por una via independiente
```

## 0. Por qué esta tabla era el hueco caro

`VRAM_Info` es el **indice 28** de la tabla maestra de datos. Contiene el numero de modulos
de VRAM y la geometria del subsistema de memoria. Un revisor la senalo como el hueco
principal del descifificador y cerro ademas el techo de reloj de memoria: el hallazgo 1400
midio que `ulASICMaxMemoryClock` y `ulDriverTargetMemoryClock` se contradicen bajo la misma
unidad, asi que ese techo no se puede fechar sin mirar la memoria por la via que usa el
firmware.

Localizada en la ROM real por la misma via que el resto (`master[28]`):

```text
tabla maestra  en 0x97F2   StructureSize 74
master[28]     off 0x982E  -> 0xA30A        (no vacio)
en 0xA30A:     usStructureSize = 986
               ucTableFormatRevision = 2      (frev)
               ucTableContentRevision = 2      (crev)
```

`986` es el tamano declarado. Ese numero se usa como control mas adelante.

## 1. Dos cabeceras candidatas, y los datos eligen — no la suposicion

El corpus tiene dos estructuras para esta version y **el numero de version no las
distingue** (`frev=2` sirve para las dos):

| | `_ATOM_VRAM_INFO_HEADER_V2_1` (atombios.h:8013) | `_ATOM_VRAM_INFO_HEADER_V2_2` (atombios.h:8027) |
|---|---|---|
| tras `usPerBytePresetOffset`/`usMcAdjustPerTileTblOffset` | `usDramDataRemapTblOffset` + `usReserved[3]` | `usMcPhyInitTableOffset`, `usDramDataRemapTblOffset`, `usReserved1` |
| ultimo byte antes del array | `ucReserved` | **`ucMcPhyTileNum`** |

Elegir a ojo seria inventar (§16). **Los propios bytes eligen**, porque un campo llamado
*reserved* tiene que valer cero:

```text
                     +4     +6     +8     +10    +12    +14
V2_1  ->  0x004C 0x005B 0x02C9 [0x032B] [0x02E7] [0x0000]     campo +14 = usReserved[0]
                                            ^^^^^  NO CERO -> V2_1 NO cierra

V2_2  ->  0x004C 0x005B 0x02C9 0x032B 0x02E7 0x0000
                                    ^^^^^^  usReserved1 = 0   -> V2_2 CIERRA
```

**El layout V2_2 es el correcto, y queda demostrado por un campo reservado que vale cero.**
No por preferencia, no por que "parezca mas nuevo".

## 2. Los números, con su control

```text
ATOM_VRAM_INFO_HEADER_V2_2 en 0xA30A  (frev=2, crev=2, size=986)

 +4  usMemAdjustTblOffset        =    76
 +6  usMemClkPatchTblOffset      =    91
 +8  usMcAdjustPerTileTblOffset  =   713
 +10 usMcPhyInitTableOffset      =   811
 +12 usDramDataRemapTblOffset    =   743
 +14 usReserved1                 =     0     <- CONTROL
 +16 ucNumOfVRAMModule           =     1
 +17 ucMemoryClkPatchTblVer      =     1
 +18 ucVramModuleVer             =     8
 +19 ucMcPhyTileNum              =     2
```

**Segundo control, independiente del anterior.** Los cinco offsets son *relativos al
inicio de la tabla* (no absolutos en la ROM: 76, 91, 713, 811, 743 son todos menores que
986). Si fueran absolutos caerían todos en la cabecera de la ROM, lo que es absurdo para
cinco punteros a tablas distintas. Que los cinco caigan dentro del tamaño declarado es lo
que fija la interpretación. **Es el mismo argumento que el de `AMD_VBIOS_LENGTH`, y aquí sí
cierra.**

## 3. Corroboración con la observación en vivo, por una vía que no existía

`ucMcPhyTileNum = 2` es el **tercer** número `2` de la geometría de memoria, y ninguno de
los dos anteriores venía del firmware:

| fuente | qué dice | cómo se obtuvo |
|---|---|---|
| sysfs KFD | `mem_banks_count = 2` | `nodes/1/properties`, en vivo |
| sysfs KFD, banco 0 | `width = 64` bits, `size_in_bytes = 2147483648`, `heap_type 2`, `mem_clk_max 1500` | `nodes/1/mem_banks/*/properties` |
| **bytes de la ROM (este hallazgo)** | **`ucMcPhyTileNum = 2`** | `VRAM_Info` +19 |
| bytes de la ROM | cadena `GDDR5 128` | cadena de identificación, off 0x124 |

**64 bits × 2 tiles = bus de 128 bits**, que es exactamente lo que dice la cadena del
firmware. Tres fuentes, dos de ellas de lectura distinta, **ninguna previa a este hallazgo
venía del firmware**: el `2` de los bancos se había obtenido siempre del kernel en
ejecución. Ahora el firmware lo declara.

Estado: `CORROBORADO` en tres vias. **No** se afirma aquí el ancho de bus como campo
medido — la cadena `GDDR5 128` es una cadena, no un campo, y el árbol no contiene ningun
`ucMemBusWidth` que el driver lea (§16: `NOT_FOUND`, no ausente).

## 4. Lo que esto deja situado para cerrar el techo de memoria

El hallazgo 1400 cerró esto como `NOT_DETERMINED`:

```text
ulDriverTargetMemoryClock = 360000   (3600 MHz con unidad 10 kHz)
ulASICMaxMemoryClock      =  62610   ( 626.1 MHz con la misma unidad)
el objetivo es 5.75x mayor que el "maximo": no pueden ser ambos 10 kHz
```

**Ahora hay dos punteros localizados** a las tablas donde ese reloj se programa:

```text
usMemClkPatchTblOffset  =  91   -> ATOM_INIT_REG_BLOCK con los ajustes de MC por reloj
usMcPhyInitTableOffset  = 811   -> ATOM_INIT_REG_BLOCK con la inicializacion PHY de MC
```

`usMemClkPatchTblOffset` con su `ucMemoryClkPatchTblVer = 1` es, por nombre y por
posición, **la lista de registros AC de memoria dependiente del reloj**. Es el sitio donde
un techo de reloj de memoria se podría leer en lugar de inferirse de un campo que se
contradice a sí mismo.

**Esto NO cierra el techo.** Registra dónde está la tabla. Para leerla hace falta decodificar
`ATOM_INIT_REG_BLOCK` en 0xA30A+91 y saber qué campo es la frecuencia — y el corpus no
declara esa unidad. El estado sigue siendo `NOT_DETERMINED`, pero **deja de ser
"no sabemos dónde mirar"**.

## 5. Lo que este hallazgo NO hace

- **No fija la unidad de `mem_clk_max`.** El valor `1500` de sysfs sigue sin unidad
  declarada; el hallazgo 1400 lo dejó así y nada aquí lo cambia.
- **No cierra `ulASICMaxMemoryClock`.** Localiza dónde mirar, no qué mirar.
- **No amplía el descifrador.** Esto es una lectura hecha a mano sobre la captura real para
  **medir una cosa concreta**, no una extensión del instrumento. El instrumento no ha
  cambiado: sigue resolviendo 2 de 35 índices, y su `ESTADO` sigue diciendo
  `NO PROBADO CONTRA UNA ROM REAL` porque el fichero que lo sostiene no se ha tocado.
  Actualizarlo es trabajo pendiente y explícito.
- **No toca la GPU.** Cero escrituras, cero privileged access.

## 6. Procedencia

```text
captura     revkit/capturas/amdgpu_vbios.txt   58880 B  modo 0644
estructuras RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/include/atombios.h:7977-8041
            (_ATOM_VRAM_INFO_V2, _V3, _V4, _HEADER_V2_1, _HEADER_V2_2)
consumidor  amdgpu_atombios.c:1455  (GetIndexIntoMasterTable(DATA, VRAM_Info);
                                     lee usMemAdjustTblOffset via amdgpu_atom_parse_data_header)
runtime     /sys/class/kfd/kfd/topology/nodes/1/properties          (mem_banks_count)
            /sys/class/kfd/kfd/topology/nodes/1/mem_banks/*/properties
metodo      lectura directa de la captura, sin sudo, sin ejecucion de nada
```

```text
ESTADO=PROBADO · VRAM_Info (indice 28) localizada y leida de la ROM real
       · layout V2_2 elegido por DATO (campo reservado = 0), no por suposicion
       · segundo control: los 5 offsets caen dentro del tamano declarado 986
       · ucMcPhyTileNum = 2 corrobora mem_banks_count = 2 por via INDEPENDIENTE
       · techo de reloj de memoria: sigue NOT_DETERMINED, pero con la tabla localizada
CONSECUENCIA  el "2" de los bancos de memoria ya no depende solo del kernel en ejecucion
LIMITACION   el ancho de bus sigue siendo cadena ("GDDR5 128"), no campo leido
Siguiente    1) decodificar ATOM_INIT_REG_BLOCK en 0xA30A+91 (usMemClkPatchTblOffset) y
               0xA30A+811 (usMcPhyInitTableOffset): ahi esta el reloj de memoria
            2) con eso, cerrar por fin E-PWR-* del techo de memoria y el 1400 §7.1
            3) el descifrador sigue en 2/35 indices: decidir si se amplia o se abandona
```
