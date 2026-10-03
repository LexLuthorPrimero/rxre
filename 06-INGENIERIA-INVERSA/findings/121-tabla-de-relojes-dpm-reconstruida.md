# 121 · La tabla de relojes DPM de esta placa, reconstruida del VBIOS y validada contra tres valores en caliente

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CIERRA el `NOT_DETERMINED` de `224` (antes `120`) (stride del registro MCLK) · da sentido a los "8 y 4"
de `099` · segunda parte del hilo de VBIOS que empezo en `116`

## La tabla completa

Con los strides ya medidos con gcc y **validados por la disposicion del ROM**, las dos
tablas de dependencia de esta placa dan esto:

```
ATOM_Polaris_SCLK_Dependency_Table @ 0x9D15   sizeof(Record) = 15   ucNumEntries = 8
ATOM_Tonga_MCLK_Dependency_Table    @ 0x9D8F   sizeof(Record) = 13   ucNumEntries = 3
```

Las **unidades son 10 kHz**, y eso **no lo supuse: lo demostraron tres valores a la vez**
contra la lectura en vivo del driver:

| nivel | `ulSclk` | MHz | `ulMclk` | MHz | observado en caliente |
|---:|---:|---:|---:|---:|---|
| 0 | 21400 | **214** | 30000 | **300** | `PSTATE_SCLK: 214 MHz` · `MCLK: 300 MHz` |
| 1 | 55100 | 551 | 62500 | **625** | `PSTATE_MCLK: 625 MHz` |
| 2 | 73400 | 734 | 150000 | 1500 | |
| 3 | 98000 | 980 | — | | |
| 4 | 100000 | 1000 | — | | |
| 5 | 102000 | 1020 | — | | |
| 6 | 104600 | 1046 | — | | |
| 7 | 107100 | 1071 | — | | |

**Tres de tres.** Si las unidades fueran kHz, 30000 kHz serian 30 MHz y la placa no
funcionaria; si fueran MHz, 30000 MHz no existe. **La unidad queda fijada por el dato, no por
la suposicion.**

Y el resto de la captura (`SCLK: 997 MHz`) encaja: es la frecuencia de trabajo, y cae entre
los niveles 3 y 4. **No tiene que coincidir con un estado.**

## La validacion del stride, por partida doble

Esto es lo que hace el dato fiable, y no lo hace ningun guessed valor:

```
tabla SCLK en 0x9D15, 8 entradas de 15 B  ->  fin en 0x9D15 + 122 = 0x9D8F
tabla MCLK declarada en 0x9D8F                                    COINCIDE

tabla MCLK en 0x9D8F, 3 entradas de 13 B  ->  fin en 0x9D8F +  41 = 0x9DB8
tabla MM dep declarada en 0x9DB8                                   COINCIDE
```

**Cada tabla termina exactamente donde empieza la siguiente.** Un error de un byte en
cualquiera de los dos strides lo romperia. **El ROM se autovalidan dos veces, y con dos
structs distintas.**

Ese fue el error que dejo `NOT_DETERMINED` en `224` (antes `120`): lei la tabla MCLK con el stride del
registro **SCLK** (15 en vez de 13) y salieron valores absurdos (65536000, 4096001000). La
causa es que **son dos registros distintos**:

```c
ATOM_Polaris_SCLK_Dependency_Record   15 B    UCHAR; USHORT; ULONG; USHORT; UCHAR; UCHAR; ULONG
ATOM_Tonga_MCLK_Dependency_Record     13 B    UCHAR; USHORT; USHORT; USHORT; ULONG; USHORT
```

Y **no existe** `ATOM_Polaris_MCLK_Dependency_Record`: Polaris usa el de Tonga. Lo busque por
nombre exacto antes de concluir que no existia, porque un nombre mal buscado produce `0` que
no es ausencia.

## Y esto explica los "8 y 4" de `099`

`099` documenta que tras un fallo de `smu7_setup_dpm_tables_v1` los contadores quedan en
**8 y 4 con valores a cero**. Y las cotas del firmware son:

```
SMU__NUM_SCLK_DPM_STATE   = 8     smu74.h:32
SMU__NUM_MCLK_DPM_LEVELS  = 4     smu74.h:33
MAX_REGULAR_DPM_NUMBER    = 8     smu7_hwmgr.h:95
```

Ahora se ve lo que significan:

| | capacidad del SMC | lo que declara este VBIOS |
|---|---:|---:|
| graficos | **8** | **8** |
| memoria | **4** | **3** |

**El VBIOS declara exactamente 8 estados de graficos, que es exactamente la capacidad de la
tabla del SMC.** No es casualidad ni sobra: es el diseno. **Los "8" de `099` son la capacidad
del SMC, y este VBIOS los llena todos.**

Y en memoria hay **3 de 4**: **una ranura queda sin usar**. No es un fallo — `mclk_table`
tiene 4 elementos y solo se escriben 3 — pero significa que **el nivel de memoria mas alto
no lo define el PPT**: lo define el firmware. Y eso encaja con lo que dice `99` del lado del
SMC.

**Esto NO resuelve `099`** (su afirmacion es sobre el codigo, y sigue igual), pero **si le da
el significado numerico que le faltaba**: 8 y 4 son las capacidades, no conteos leidos.

## Y cierra el borde de `224` (antes `120`)

`224` (antes `120`) dejo esto: la tabla SCLK del VBIOS declara 8, la cota es 8, y **el margen es cero**.

Con la tabla completa se ve **por que el borde existe y por que es justo**:

- El SMC tiene **8** ranuras para graficos. El VBIOS declara **8** estados.
- Si el VBIOS declarara uno mas, `dpm_levels[8]` se saldria. Y el check es `count >= 1`.

O sea: **el formato y el host estan exactamente emparejados, sin holgura, por construccion.**
Un check `>= 1` sobre dos cantidades que estanizadas a proposito es un check que **solo
puede fallar si el VBIOS se sale del rango que el propio diseno fija**.

**Eso convierte el borde de `224` (antes `120`) de "riesgo teorico" en "riesgo de cambio de formato":** si
alguien anade un noveno estado de graficos al PPT (que es una mejora razonable), **el driver
existente se sale del array sin avisar.**

## Clasificacion

- `SCLK_RECORD_SIZE_IS_15 = PROVEN_DERIVED`: gcc con `pack(1)`, y la tabla MCLK empieza en
  `0x9D15 + 2 + 8*15` exactamente.
- `MCLK_RECORD_SIZE_IS_13 = PROVEN_DERIVED`: gcc con `pack(1)`, y la tabla MM dependency
  empieza en `0x9D8F + 2 + 3*13` exactamente. **CIERRA** el `NOT_DETERMINED` de `224` (antes `120`).
- `NO_POLARIS_SPECIFIC_MCLK_RECORD_EXISTS = PROVEN_ABSENT`: solo hay
  `ATOM_Tonga_MCLK_Dependency_Record`. Buscado por nombre exacto.
- `DPM_CLOCK_UNITS_ARE_10_KHZ = PROVEN_DERIVED`: **tres** valores coinciden con la lectura
  viva (214, 300, 625 MHz). kHz y MHz quedan descartados por magnitud.
- `THIS_GPU_HAS_8_SCLK_STATES_214_TO_1071_MHZ = PROVEN`: tabla completa, arriba.
- `THIS_GPU_HAS_3_MCLK_STATES_300_625_1500_MHZ = PROVEN`: tabla completa.
- `VBIOS_SCLK_STATES_EXACTLY_FILL_SMC_CAPACITY = PROVEN_DERIVED`: 8 del VBIOS = 8 de
  `SMU__NUM_SCLK_DPM_STATE` = 8 de `MAX_REGULAR_DPM_NUMBER`. **Sin holgura, por diseno.**
- `VBIOS_MCLK_STATES_LEAVE_ONE_SLOT_FREE = PROVEN_DERIVED`: 3 de 4. El nivel de memoria mas
  alto lo define el firmware, no el PPT.
- `FINDING_099_S_EIGHT_AND_FOUR_ARE_CAPACITIES = PROVEN_DERIVED`: el significado numerico
  que le faltaba. **No resuelve `099`**, que sigue siendo lo que es sobre el codigo.
- `DPM_CLOCK_BOUNDARY_IS_A_FORMAT_CHANGE_RISK = PROVEN_DERIVED`: anadir un noveno estado al
  PPT desbordaria `dpm_levels[8]` sin que ningun check lo note.
- `RECORD_SIZE_ERROR_MODE = PROVEN_DERIVED`: leer una tabla con el stride del otro registro
  da valores absurdos pero **no un fallo visible**. Es la causa de los tres errores de `116`
  y de este.

## Lo que esto obliga a hacer en un driver propio

1. **Mi driver tiene que declarar su tabla de niveles, no heredarla.** Los 8 estados y los
   3 de memoria **son numeros del VBIOS de esta placa**, no constantes universales. Un
   driver que fije 8 y 4 en codigo y acepte cualquier PPT esta suponiendo lo que este VBIOS
   deja vacia una ranura en memoria.
2. **Validar `count` contra la capacidad del destino, siempre.** Es la unica defensa que
   funciona cuando el formato y el host estan emparejados sin holgura. Y aqui se emparejan
   **a proposito**, luego el caso "un nivel mas" **es un cambio legitimo del PPT** que
   rompe el driver. **Mi driver tiene que rechazarlo con un mensaje claro, no salirse del
   array en silencio.**
3. **Una tabla tiene un registro, y cada registro tiene su stride.** No hay "el stride de
   las tablas de dependencia": hay dos, de 15 y de 13 B. Un driver propio que share el
   parseo entre ellas **tiene que validar el stride de cada una**, y la validacion mas
   barato es la que uso aqui: **que la tabla termine exactamente donde empieza la
   siguiente.**
4. Y la regla de unidades, que es la mas subestimada de esta tanda: **no se deducen, se
   verifican contra una lectura viva.** `10 kHz` no estaba en ningun header. Sale de que
   30000, 62500 y 21400 coincidan con 300, 625 y 214 MHz. **Un driver propio tiene que
   documentar la unidad de cada campo de frecuencia y comprobarla**, porque un factor 10 mal
   puesto no da error: da frecuencias que no existen.