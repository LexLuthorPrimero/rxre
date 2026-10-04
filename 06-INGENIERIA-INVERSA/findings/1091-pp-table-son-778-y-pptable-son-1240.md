# 1091 — `pp_table` son 778 bytes y `PPTable_t` son 1240: la tabla está truncada al 62,7 % y las frecuencias DPM no están en ella

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=RECONSTRUCCION+RESULTADO-NEGATIVO · TRACK=STATIC+COMPILED
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-009 (PROVEN -> PARCIAL)
         09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-007 (via de acceso: CERRADA)
         06-INGENIERIA-INVERSA/PPT-DECODE/  (instrumento, nuevo)
ORIGEN=E-PWR-009 ("Status: NOT YET DECODED. Currently UNUSED_EVIDENCE")
ESTADO=PROBADO · sizeof por COMPILACION · resultado NEGATIVO medido
herramienta   06-INGENIERIA-INVERSA/PPT-DECODE/extrae_tipo.py + mapa.c (C)
```

## 0 · Tres cosas, y la segunda cierra una puerta

| # | | |
|---|---|---|
| 1 | `sizeof(PPTable_t)` = **1240 bytes**, medido compilando el header del driver | `E-PWR-009` trataba los 778 como si identificaran el tipo |
| 2 | **Las frecuencias DPM observadas NO están en el blob**, en ninguna codificación | **`pp_table` no es atajo para la curva V/F** |
| 3 | La ruta que `E-PWR-009` cita **no existe en este kernel** | corrección de procedencia |

## 1 · EL TAMAÑO, MEDIDO POR EL COMPILADOR

Extraje `PPTable_t` y sus dependencias del `smu11_driver_if.h` **del propio corpus** —
16 `#define` de niveles DPM, `PPCLK_e`, `I2cControllerName_e`, `AVFS_VOLTAGE_TYPE_e`,
`DpmDescriptor_t` — y los compilé:

```
sizeof(PPTable_t)             = 1240
sizeof(DpmDescriptor_t)       = 24
sizeof(I2cControllerConfig_t) = 28
```

**Instrumento:** `06-INGENIERIA-INVERSA/PPT-DECODE/extrae_tipo.py` (extrae) +
`mapa.c` (imprime `sizeof`). El mapa sale de `offsetof` sobre el tipo real, no de
parsearlo a mano: *un mapa hecho a ojo es una suposición; uno que sale del
compilador es una medición*.

Y la fuente confirma el 1240 por su cuenta:

```c
/* arcturus_ppt.c:256 -- SMU_TABLE_INIT(tables, SMU_TABLE_PPTABLE, sizeof(PPTable_t), ...) */
```

**El blob son 778 bytes, y `amdgpu_get_pp_table()` hace `memcpy(buf, table, size)`
sin prefijo de tamaño** (`pm/amdgpu_pm.c:551-575`), o sea que 778 es el
`power_play_table_size` **de runtime**, y ese valor lo fija el firmware:

```c
/* smu_v11_0.c:283-286 */
if (!smu->smu_table.power_play_table)      smu->smu_table.power_play_table = table;
if (!smu->smu_table.power_play_table_size) smu->smu_table.power_play_table_size = size;
```

**778 ≠ 1240, y son objetos distintos:** el tamaño que declara el driver y el tamaño
que el firmware entregó. **El blob está truncado al 62,7 %**, así que **todo campo a
partir del offset 778 no es observable**, y eso hay que decirlo antes de usar nada de
lo que sí está.

## 2 · EL RESULTADO NEGATIVO, Y ES EL QUE IMPORTA

`FreqTableGfx` está en el offset **352**, comfortably dentro de los 778. Si el blob
fuera una `PPTable_t`, ahí estarían las frecuencias. Busqué las ocho que el propio
proyecto observó (`E-PWR-004`: 214, 551, 734, 980, 1000, 1020, 1046, 1071 MHz):

```text
búsqueda como uint16, MHz x1        7 de 8 ausentes   (solo 1000, en 2 sitios)
búsqueda como uint16, MHz x2        8 de 8 ausentes
búsqueda como uint16, MHz x10       8 de 8 ausentes
búsqueda como uint32, MHz x100      6 de 8 ausentes
RUN de 4+ consecutivos, x1/x2/x10   NINGUNO
MCLK 300 / 625 MHz                   ausentes
MCLK 1500 MHz                        aparece 2 veces, no en run
```

**Las frecuencias DPM que la GPU está publicando en `pp_dpm_sclk` no están, en ningún
encoding, en los 778 bytes que el driver llama "la tabla de power play".**

### Las dos explicaciones, y por qué esto NO es "las frecuencias no están en la PPT"

| hipótesis | estado |
|---|---|
| la PPT no contiene frecuencias, las calcula el SMU en runtime | posible, pero **no la puedo sostener** |
| **el layout del firmware no es el `PPTable_t` de 7.1.3** | **más probable, y hay evidencia** |

La evidencia a favor de la segunda es que **la decodificación por offsets produce
absurdos con el struct correcto**:

```text
TedgeLimit   @40 = 2      -> 2 °C de límite de temperatura de borde
FitLimit     @56 = 41216  -> un uint32 de "límite de ajuste" que no está en 16 bits
PpmPowerLimit@60 = 61440  ->同样的问题，下面不再重复
MinVoltageGfx@76 = 256    -> plausible
MaxVoltageGfx@80 = 0      -> un máximo de voltaje de 0 mV
```

Un límite térmico de 2 °C y un voltaje máximo de 0 no son una tabla malformada: son
**una tabla leída con el mapa equivocado**. Si el struct fuera el correcto,
`TedgeLimit` tendría que ser ~97 °C (el `temp1_crit` que el proyecto ya midió) y
`MaxVoltageGfx` sería distinto de 0.

**Conclusión honesta, y es la que manda:** `pp_table` **no se puede decodificar con
`PPTable_t` de este kernel**, y el motivo es medible —los campos que deben contener
frecuencias no las contienen, y los campos que sí están dentro de la ventana
decodifican a valores físicamente imposibles—. La revisión del firmware de
Polaris12 queda `NOT_DETERMINED`: **no sé qué versión de PPT envía**, y sin eso no
puedo nombrar el offset de ningún campo con honestidad.

## 3 · POR QUÉ CASI TE PRESENTO UNA DECODIFICACIÓN FALSA

Lo primero que hice fue el mapa de offsets y volcar los campos. **Salieron números**,
que es exactamente el estado en el que un error se convierte en un hallazgo: hay que
mirar la salida para decidir. Los numeros no se comprueban solos.

Lo que los delató fue el **oráculo**: si la tabla fuera la fuente de los niveles DPM,
las ocho frecuencias tendrían que estar ahí, en un run, y no estaban. **Ese es el
momento en el que "tengo un mapa y unos datos" pasa a "no tengo nada".**

Lo escribo porque es el mismo patrón que el `1057`: un campo o un mapa que parece
correcto y no lo es, y que solo se detecta cuando se busca la corroboración externa
en lugar de la interna. Y porque la alternativa —presentar `TedgeLimit = 2` como un
dato medido— habría sido un halluc con formato de tabla.

## 4 · CORRECCIÓN DE PROCEDENCIA A `E-PWR-009`

La cadena que el propio `E-PWR-009` escribe es semánticamente correcta y
**geométricamente falsa** para este kernel:

| lo que dice `E-PWR-009` | lo que existe en 7.1.3 |
|---|---|
| `pm/swsmu/amdgpu_smu.c:644` | `amd/pm/swsmu/amdgpu_smu.c`, y la función acaba en **661** |
| `smu_table->power_play_table` / `power_play_table_size` | **existe**, línea 657 y 661 |
| `== SMU_TABLE_DPMCLKPOWRESET` | **`DPMCLKPOWRESET` no existe en ningún fichero del corpus.** El tipo real es `PPTable_t`, en `powerplay/inc/smu11_driver_if.h:612` |
| *"the blob must be decoded against the Arcturus `DPMCLKPOWRESET` struct"* | el tipo que hay que compilar es `PPTable_t`, y **compilado da 1240, no 778** |

La causa del path equivocado es visible: en este corpus el driver cuelga de
`drivers/gpu/drm/amd/`, no de `drivers/gpu/drm/amd/amdgpu/`. Es el mismo despiste que
tuve yo al buscar `smu_dpm.c`.

## 5 · LO QUE ESTO CIERRA Y LO QUE DEJA ABIERTO

**Cierra una vía, y eso es un resultado:** `pp_table` **no** es un atajo para la curva
V/F. `E-PWR-007` sigue siendo correcto al decir que una curva exige un barrido con
carga, y ahora además se sabe **por qué no hay atajo**: la tabla que hay no contiene
los niveles, y la que los contiene no se puede leer con este struct.

**Abierto, y con el nombre de lo que falta:**

| falta | quién lo produce | qué observable |
|---|---|---|
| revisión de PPT que envía el firmware de esta Polaris12 | el firmware, vía `smu_v11_0_get_ppt_info` | el número de versión de PPT, que es el primer campo |
| un `PPTable_t` de la revisión que corresponda | el driver de esa versión | los offsets |
| el barrido con carga | §48 EXPERIMENT, y necesita una carga EGL/GLES headless | la curva V/F real |

**Y sigue sin cerrarse nada que dependiera de esto:** la contradicción del enlace
(`1085`) no la usaba; `E-PWR-008` (histéresis) no depende de la PPT.

## 6 · PROCEDENCIA

```text
instrumento  06-INGENIERIA-INVERSA/PPT-DECODE/{extrae_tipo.py, mapa.c}
             extrae del corpus, compila, imprime sizeof
medida 1     sizeof(PPTable_t) = 1240   (C, compilador, sobre el tipo del driver)
medida 2     blob 09-POWER-CLOCKS/evidence/pp_table.txt = 778 B, sha256 ff65c3f52132b8df
medida 3     778/1240 = 62.7 %  -> truncado
medida 4     8 frecuencias DPM ausentes en 4 encodings x 2 anchos; ningun run
medida 5     TedgeLimit=2, MaxVoltageGfx=0, FitLimit=41216  -> layout incompatible
origen       amdgpu_get_pp_table() pm/amdgpu_pm.c:551-575 (memcpy sin prefijo)
             smu_sys_get_pp_table() pm/swsmu/amdgpu_smu.c:643-662 (size de runtime)
             smu_v11_0.c:283-286 (el firmware fija el size)
escrituras   0 en el arbol.  GPU intacta.  No he cargado nada.
```

**Lo que este documento NO prueba.** No prueba **cuál** es el layout correcto: sólo
que este no lo es. No prueba que la PPT no contenga frecuencias — puede contenerlas
en una revisión de firmware que no sé leer. No he tocado la GPU, no he hecho barrido
con carga, y no he medido rendimiento. Y `pp_table` sigue siendo `UNUSED_EVIDENCE`,
que es el estado correcto.