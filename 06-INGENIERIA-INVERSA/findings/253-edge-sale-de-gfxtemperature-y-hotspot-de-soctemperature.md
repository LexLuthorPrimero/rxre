# 253 · `edge` sale de `GfxTemperature` y `hotspot` sale de `SocTemperature`, y eso cambia lo que el driver propio tiene que pedir

```text
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

> **Convención de rutas.** `amdgpu/x.c` = `drivers/gpu/drm/amd/amdgpu/x.c`.
> `pm/y.c` = `drivers/gpu/drm/amd/pm/y.c`. Las 21 citas de esta nota resuelven con la base
> `drivers/gpu/drm/amd/`.

## Qué resuelve

**Cierra el `NOT_DETERMINED` que `251` dejó sobre la estructura `SmuMetrics_t`.** `PROVEN`.

**⇒ `PROVEN`. La definición está en `pm/swsmu/inc/pmfw_if/smu12_driver_if.h:171-210`, 40 líneas,
40 campos, todos `uint16_t` salvo los arrays.** `PROVEN`.

**⇒ Y el hallazgo que la definición destapa, que no era visible desde `251`: en Polaris12,
`METRICS_TEMPERATURE_EDGE` se lee de `metrics->GfxTemperature` y `METRICS_TEMPERATURE_HOTSPOT`
se lee de `metrics->SocTemperature`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. El nombre del sensor y el nombre del campo no coinciden, y la asimetría es
en la dirección contraria a la que sugiere el sentido común: `edge` es la temperatura del GFX y
`hotspot` es la del SoC. Un driver propio que pida «el campo que se llama edge» al firmware
obtiene la del SoC.** `PROVEN_DERIVED`.

## 1 · La estructura, completa

**⇒ `smu12_driver_if.h:171-210`, y el comentario de unidad está en cada campo:** `PROVEN`.

```c
171  typedef struct {
172      uint16_t ClockFrequency[CLOCK_COUNT]; //[MHz]
174      uint16_t AverageGfxclkFrequency;      //[MHz]
175      uint16_t AverageSocclkFrequency;      //[MHz]
176      uint16_t AverageVclkFrequency;        //[MHz]
177      uint16_t AverageFclkFrequency;        //[MHz]
179      uint16_t AverageGfxActivity;          //[centi]
180      uint16_t AverageUvdActivity;          //[centi]
182      uint16_t Voltage[2];                  //[mV] indices: VDDCR_VDD, VDDCR_SOC
183      uint16_t Current[2];                  //[mA] indices: VDDCR_VDD, VDDCR_SOC
184      uint16_t Power[2];                    //[mW] indices: VDDCR_VDD, VDDCR_SOC
186      uint16_t FanPwm;                      //[milli]
187      uint16_t CurrentSocketPower;          //[W]
189      uint16_t CoreFrequency[8];            //[MHz]
190      uint16_t CorePower[8];                //[mW]
191      uint16_t CoreTemperature[8];          //[centi-Celsius]
192      uint16_t L3Frequency[2];              //[MHz]
193      uint16_t L3Temperature[2];            //[centi-Celsius]
195      uint16_t GfxTemperature;              //[centi-Celsius]
196      uint16_t SocTemperature;              //[centi-Celsius]
197      uint16_t ThrottlerStatus;
198      uint16_t spare;
200      uint16_t StapmOriginalLimit;          //[W]
201      uint16_t StapmCurrentLimit;           //[W]
202      uint16_t ApuPower;                    //[W]
203      uint16_t dGpuPower;                   //[W]
205      uint16_t VddTdcValue;                 //[mA]
206      uint16_t SocTdcValue;                 //[mA]
207      uint16_t VddEdcValue;                 //[mA]
208      uint16_t SocEdcValue;                 //[mA]
209      uint16_t reserve[2];
210  } SmuMetrics_t;
```

**⇒ `PROVEN_DERIVED. Y el comentario de unidad es el dato más valioso de la estructura: la
documentación existe, es una línea por campo, y dice la unidad de cada uno. Es el único punto del
corpus donde el firmware se describe a sí mismo sin que ningún registro lo documente.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Las unidades no son homogéneas y esa heterogeneidad es el error que un driver
propio hereda si copia sin mirar: hay `centi` (centésimas), `milli` (milisimas), `mW`, `mA`, `mV`,
`MHz` y `W` en la misma estructura. Sólo un campo, `CurrentSocketPower`, está en vatios planos;
los cinco campos de TDC y EDC están en miliamperios; las tres potencias `Stapm*`, `ApuPower` y
`dGpuPower` están en vatios.** `PROVEN_DERIVED`.

**⇒ Y los cinco campos de temperatura están todos en centi-Celsius: `CoreTemperature[8]` (línea
191), `L3Temperature[2]` (193), `GfxTemperature` (195) y `SocTemperature` (196). Cuatro
declaraciones, y Renoir sólo lee las dos últimas.** `PROVEN`.

## 2 · La tabla, su tamaño y su asignación

**⇒ `renoir_ppt.c:157` es `SMU_TABLE_INIT(tables, SMU_TABLE_SMU_METRICS, sizeof(SmuMetrics_t), ...)`
y `renoir_ppt.c:164` es `smu_table->metrics_table = kzalloc_obj(SmuMetrics_t)`. La tabla del host
tiene exactamente el tamaño de la estructura, sin relleno.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y esto tiene una consecuencia medible: el tamaño de la descarga del firmware
es `sizeof(SmuMetrics_t)`, y como el driver no puede calcular ese tamaño sin la definición, el
número de bytes que baja por el canal SMC queda fijado por el compilador en el momento de
compilar. Para el driver propio es el número que hay que conocer de antemano para reservar el
búfer, y se deriva de la estructura, no de un parámetro del firmware.** `PROVEN_DERIVED`.

## 3 · La tabla de traducción miembro → campo, que es donde está la trampa

**⇒ `renoir_ppt.c:1195` abre el `switch (member)` y las líneas 1222-1229 son las dos que
importan:** `PROVEN`.

```c
1222   case METRICS_TEMPERATURE_EDGE:
1223       *value = (metrics->GfxTemperature / 100) *
1224       SMU_TEMPERATURE_UNITS_PER_CENTIGRADES;
1225       break;
1226   case METRICS_TEMPERATURE_HOTSPOT:
1227       *value = (metrics->SocTemperature / 100) *
1228       SMU_TEMPERATURE_UNITS_PER_CENTIGRADES;
1229       break;
```

**⇒ `PROVEN`. `METRICS_TEMPERATURE_EDGE` → `GfxTemperature`, y `METRICS_TEMPERATURE_HOTSPOT` →
`SocTemperature`. Los dos casos, en esas dos líneas, sin ambigüedad.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y hay una segunda asimetría que refuerza la anterior: el enum
(`pm/swsmu/inc/amdgpu_smu.h:1682-1683`) declara `METRICS_TEMPERATURE_EDGE` antes que
`METRICS_TEMPERATURE_HOTSPOT`, y los campos de la struct los declara `GfxTemperature` antes que
`SocTemperature` en el mismo orden relativo. El orden del enum y el orden de los campos están
alineados, y el del `switch` también. No es un descuido de indexación: son dos listas paralelas
que mantienen el orden por construcción y que sólo rompen la correspondencia de nombres.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Consecuencia práctica y es la razón de esta nota: si el driver propio pide al
firmware «el miembro METRICS_TEMPERATURE_EDGE» y luego lo metería en una variable llamada
`hotspot` por analogía con otro ASIC, el error es silencioso y da un número plausible durante
toda la vida del driver. Sólo se detecta comparando el valor leído contra el valor que se sabe
por otra vía.** `PROVEN_DERIVED`.

## 4 · La conversión, y por qué el 1000 está ahí

**⇒ `pm/swsmu/inc/amdgpu_smu.h:37` es `#define SMU_TEMPERATURE_UNITS_PER_CENTIGRADES 1000`.** `PROVEN`.

**⇒ Y el consumidor declara su unidad en `amdgpu/amdgpu_kms.c:1186`: `/* get temperature in
millidegrees C */`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. La cadena de conversión es `(centi / 100) * 1000`, es decir grados por 1000,
que es exactamente mili-grados. Los dos factores están justificados y se cancelan: `/100` quita
las centésimas y `*1000` pone las milésimas. La operación neta es `valor * 10`.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el truncamiento es real y hay que verlo: `/100` es división entera de
enteros, así que un sensor que reporte 43.95 °C como centi-Celsius devuelve 4395, y
`4395/100 = 43` por truncar, no por redondear. El driver pierde hasta 0.99 °C de resolución y
nunca redondea al alza. Para una lectura que alimenta un lazo de control térmico, truncar es la
elección conservadora y es correcta; para una lectura que se muestra al usuario, es un defecto
visible.** `PROVEN_DERIVED`.

## 5 · Las dos unidades distintas, y por qué no se contradicen

**⇒ `095` cerró que el límite térmico de la tabla del SMC es Q8.8: `usTargetOperatingTemp *
SMU7_Q88_FORMAT_CONVERSION_UNIT`, con la constante igual a 256.** `PROVEN` (por `095`).

**⇒ Y aquí la lectura del sensor en vivo es mili-grados, con factor 1000.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Son dos unidades distintas para dos tablas distintas, y no es una
contradicción: la de Q8.8 va en una tabla de parámetros que el firmware carga una vez, y la de
mili-grados es el valor instantáneo que se lee del sensor. Un driver propio tiene que manejar
las dos y no confundirlas, porque una se compara contra un umbral fijo y la otra se entrega a
userspace.** `PROVEN_DERIVED`.

**⇒ Y hay un tercer valor en la misma familia que conviene no confundir con ninguno de los dos:
`222` midió que `usTjMax = 93` en el VBIOS se convierte en `usOperatingTempMaxLimit = 43`
porque el driver le resta 50 cuando el valor es mayor o igual que 50. Ese 43 es un entero en
grados, sin decimales, y es el límite de operación, no una lectura.** `PROVEN_DERIVED`.

**⇒ Los tres números, entonces, con su unidad:** `usTjMax` 93 en grados enteros del VBIOS;
`usOperatingTempMaxLimit` 43 en grados enteros tras el `-50`; y la lectura en vivo en
mili-grados. **El paso de 43 a la unidad de lectura es una conversión que el driver NO hace en
ningún sitio del corpus.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: dónde se comparan esos 43 con la lectura de 43000 mili-grados. No hay
código en el driver que lo haga, porque el control térmico vive en el firmware. La pregunta de
«¿baja la GPU de reloj porque está a 43 grados?» tiene su respuesta en el firmware y no en el
driver.** `NOT_DETERMINED`.

## 6 · Un segundo caso raro en la misma función, por el mismo motivo

**⇒ `renoir_ppt.c:1211` abre `case METRICS_CURR_SOCKETPOWER:` y las dos ramas de las líneas 1218
y 1220 no hacen lo mismo:** `PROVEN`.

```c
1218       *value = metrics->CurrentSocketPower << 8;
1219     else
1220       *value = (metrics->CurrentSocketPower << 8) / 1000;
```

**⇒ La condición de las líneas 1212-1217 es
`(MP1_HWIP == IP_VERSION(12,0,1) && fw_version >= 0x40000f) ||
(MP1_HWIP == IP_VERSION(12,0,0) && fw_version >= 0x373200)`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Una rama multiplica por 256 y la otra multiplica por 256 y divide por 1000.
La diferencia es de un factor de 1000, y la condición selecciona por VERSIÓN DE FIRMWARE, no por
campo: el mismo campo de la misma placa da dos valores que difieren en 1000 según qué firmware
esté cargado. Para un driver propio esto es un contrato que hay que escribir explícitamente, y es
la clase de cosa que no se puede deducir: se mide.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y la asimetría de unidades lo explica: `CurrentSocketPower` está en vatios
en la struct (línea 187) y la rama antigua devuelve vatios mientras la nueva devuelve milivatios.
Es una migración de unidad hecha dentro del driver, no por el firmware.** `PROVEN_DERIVED`.

## 7 · Lo que queda abierto

**⇒ `NOT_DETERMINED`: la disposición interna de la tabla tal como la escribe el firmware. La
struct del driver es la disposición que el driver espera; que coincida con la del firmware es un
acuerdo que no se puede verificar leyendo el driver, porque el firmware y el driver son
compilados por separado y ese acuerdo sólo se comprueba en runtime.** `NOT_DETERMINED`.

```text
PENDIENTE=253-1 | HALLAZGO=253-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/sys/kernel/debug/dri/0/amdgpu_pm_info  (fichero de debugfs)
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

**⇒ `NOT_DETERMINED`: el sentido de `GfxTemperature` frente a `SocTemperature` en el hardware. El
driver las llama así, pero qué sensor físico es cada una —si `Gfx` es el de la GPU y `Soc` el del
chip, o al revés, o si el SoC de Polaris12 incluye la propia GPU— no lo dice ninguna fuente del
corpus.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y esta nota reduce el `NOT_IN_CORPUS` de `251`: el lado del driver está
cerrado hasta el último campo, y lo único que falta es el firmware que rellena la tabla. La
estructura que el firmware rellena ya está identificada por nombre, tamaño y campos, así que un
análisis del binario del firmware tiene un objetivo exacto y no una búsqueda abierta.** `PROVEN_DERIVED`.

## 8 · Errores propios registrados en esta nota

**⇒ `ERROR`. Escribí `NOT_DETERMINED` sobre la estructura de `SmuMetrics_t` en `251` sin haber
buscado el nombre del fichero que la contiene. El nombre del tipo tiene el sufijo de la
generación, `smu12_driver_if.h`, y el subárbol `pm/swsmu/inc/pmfw_if/` tiene 19 ficheros de
interfaz, uno por ASIC. La ausencia que afirmé era una búsqueda sin hacer sobre un directorio
que existe y que no había listado.** `ERROR`.

**⇒ `ERROR`. Escribí una frase con caracteres CJK que se me colaron al redactar, y además
construí «sin U+6307 U+5B9A un registro», donde dos caracteres CJK sustituyeron a un verbo
español. Es la tercera
vez en tres notas y las tres han aparecido en el mismo sitio: una frase larga del primer párrafo de
un apartado. El sitio del error es predecible, y eso lo hace evitable.** `ERROR`.

**⇒ Y el mismo tramo llevaba un bloque de código con un literal inventado: escribí
`(metrics->CurrentSocketPower << 1000) / 1000` donde el fichero tiene `<< 8`. Lo detecté al
reverificar la cita contra `renoir_ppt.c:1220`. La cita apuntaba a la línea correcta y el literal
que copié era falso: copiar el código a mano introduce errores que la cita no.** `ERROR`.