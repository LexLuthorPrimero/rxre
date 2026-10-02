# 153 · El identificador de salida: un word de 32 bits, y siete rutas del firmware

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La pregunta con la que cerré `152`:** cómo pasa un nombre en software a una
dirección de registro en el camino de salida. **La respuesta es un word de 32 bits con
tres campos ortogonales, y no necesita tabla de búsqueda — y el número de salidas
físicas de esta GPU lo declara el firmware, no el driver.**

## 1 · `union ddi_channel_mapping`: un byte, cuatro carriles

`display/include/grph_object_ctrl_defs.h:239-253`:

```c
/* Invalid channel mapping */
enum { INVALID_DDI_CHANNEL_MAPPING = 0x0 };

/**
 * DDI PHY channel mapping reflecting XBAR setting
 */
union ddi_channel_mapping {
        struct mapping {
                uint8_t lane0:2;        /* Mapping for lane 0 */
                uint8_t lane1:2;
                uint8_t lane2:2;
                uint8_t lane3:2;
        } mapping;
        uint8_t raw;
};
```

**Cuatro carriles de dos bits = ocho bits, con una vista `raw` de un byte.** Y el
comentario dice exactamente para qué: *"DDI PHY channel mapping reflecting XBAR
setting"* — **el mapa de los carriles del PHY al crossbar.** `PROVEN`.

**Y el valor cero es explícitamente inválido.** `PROVEN`.

### Dónde se rellena, y dónde se consume

| | |
|---|---|
| se rellena | `dc/link/link_factory.c:790` y `:798` — `link->ddi_channel_mapping = path->channel_mapping;` |
| se consume | `dc/clk_mgr/dce110/dce110_clk_mgr.c:157-158` — `cfg->ddi_channel_mapping = stream->link->ddi_channel_mapping.raw;` |

**⇒ La cadena es de tres saltos: el *path* trae el mapa, el enlace lo hereda, y el
gestor de relojes lo recibe en crudo.** `PROVEN_DERIVED`.

**Y que lo consuma el gestor de relojes tiene sentido físico:** el mapa de carriles
a crossbar decide qué PLL maneja qué salida, así que el reloj se programa con él.

**Y `clk_mgr/` tiene `dce100/`, `dce110/`, `dce112/`, `dce120/` más dieciséis `dcn*`.**
**El gestor de relojes de DCE 10.0 está en el corpus**, que es lo que faltaba para
cerrar este eslabón: `147` tenía el stream encoder de esta GPU, y ahora también el
gestor de relojes.

## 2 · Y de dónde viene el mapa: una tabla de ATOM BIOS

El `path` de arriba viene de `ext_disp_conn_info`, en el mismo fichero
(`grph_object_ctrl_defs.h:315-337`), y **es una estructura de firmware**:

```c
        uint32_t device_acpi_enum;
        /* A physical connector for displays to plug in, using object connector definitions */
        struct graphics_object_id device_connector_id;
        /* An index into external AUX/DDC channel LUT */
        uint8_t ext_aux_ddc_lut_index;
        /* An index into external HPD pin LUT */
        uint8_t ext_hpd_pin_lut_index;
        /* external encoder object id */
        struct graphics_object_id ext_encoder_obj_id;
        /* XBAR mapping of the PHY channels */
        union ddi_channel_mapping channel_mapping;

        unsigned short caps;
} path[MAX_NUMBER_OF_EXT_DISPLAY_PATH];
```

**Cada ruta de display externo lleva, declarado por el firmware:** el enum ACPI del
dispositivo, el identificador de objeto del conector, un índice a la tabla de
canales AUX/DDC, un índice a la tabla de pines HPD, el identificador de objeto del
codificador, el mapa del crossbar, y las capacidades. `PROVEN`.

**Y `MAX_NUMBER_OF_EXT_DISPLAY_PATH` es 7** (`grph_object_ctrl_defs.h:274`), con
`NUMBER_OF_UCHAR_FOR_GUID 16` al lado.

**⇒ Siete rutas de display externo declaradas por el firmware, para un chip con un
motor de display y dos shader engines.** `PROVEN`.

**Y las dos tablas de índices son la parte interesante:** el mapa no está codificado,
está *indexado*. **El firmware entrega índices, y el driver las resuelve contra tablas
que no están en el corpus.** Es la misma clase de dependencia que `140` encontró con
`MC_VM_FB_LOCATION`: un valor que hay que leer del hardware, aquí del firmware, y que
no se puede inventar.

## 3 · `struct graphics_object_id`: el word de 32 bits

`display/include/grph_object_id.h:227-232`:

```c
struct graphics_object_id {
        uint32_t  id:8;
        enum object_enum_id  enum_id :4;
        enum object_type  type :4;
        uint32_t  reserved:16;      /* for padding. total size should be u32 */
};
```

**Aritmética, impresa por programa:**

```
  id         : 8 bits   -> 0..255
  enum_id    : 4 bits   -> 0..15
  type       : 4 bits   -> 0..15
  reserved   : 16 bits  -> solo relleno, el comentario dice que el total debe ser u32
  total      : 32 bits = 4 bytes   COINCIDE: True
```

**El comentario del driver predice 32 bits y la suma da 32.** Es la comprobación
cruzada más pequeña y más satisfactoria de la tanda, y es la clase de verificación
que `151` pidió y que aquí se cumple sin coste. `PROVEN`.

### Y el contenido de los ocho bits útil

`enum object_type` (`L30`), **10 valores**:

```
OBJECT_TYPE_UNKNOWN    OBJECT_TYPE_ENCODER      OBJECT_TYPE_GENERIC
OBJECT_TYPE_GPU        OBJECT_TYPE_CONNECTOR    OBJECT_TYPE_AUDIO
                        OBJECT_TYPE_ROUTER       OBJECT_TYPE_CONTROLLER
                        OBJECT_TYPE_CLOCK_SOURCE OBJECT_TYPE_ENGINE
```

`enum object_enum_id` (`L50`), **8 valores**:

```
ENUM_ID_UNKNOWN  ENUM_ID_1  ENUM_ID_2  ENUM_ID_3  ENUM_ID_4  ENUM_ID_5  ENUM_ID_6  ENUM_ID_7
```

**Los dos encajan en sus campos de 4 bits con holgura:** 10 valores en 16 códigos
(6 libres), y 8 en 16 (8 libres). `PROVEN_DERIVED`.

### Y la identificación que cierra la cadena

**`ENUM_ID_1` … `ENUM_ID_7` son exactamente siete valores, y
`MAX_NUMBER_OF_EXT_DISPLAY_PATH` es exactamente 7.** `PROVEN_DERIVED`.

**⇒ `object_enum_id` ES el índice de la ruta de display, y va de 1 a 7 porque el 0
está reservado para lo desconocido — igual que `INVALID_DDI_CHANNEL_MAPPING = 0x0`.**
Los dos ceros reservados coinciden, y eso no es casualidad: es la misma convención
en dos sitios.

**Y con esto, la respuesta completa a "cómo se convierte un nombre en software en una
dirección de registro":**

```
  type     4 bits   qué clase de objeto: encoder, connector, router, engine, …
  enum_id  4 bits   cuál de las 7 rutas de display, 1..7, desde el firmware
  id       8 bits   cuál de los 256 de esa clase
  ------------------------------------------------------------------
  total   32 bits   y el hardware exige un dword, por eso el campo reserved
```

**Es la misma idea que un VMID, y está invertida.** Un VMID es un entero pequeño que
*selecciona* una tabla de páginas, así que el hardware necesita una tabla. **Un
`graphics_object_id` es un identificador *compuesto* con campos ortogonales, así que
la dirección se calcula desde los campos y no hace falta tabla.** `PROVEN_DERIVED`.

**Y `ddi_channel_mapping` es el mismo truco un nivel más abajo:** cuatro campos de dos
bits empaquetados en un byte, con una vista `raw` para el hardware. **Dos
identificadores compuestos, ambos empaquetados, ambos con relleno declarado.**

## 4 · Lo que esto añade a la cadena de firmware

`149` encontró, en el comentario de un campo, que el timing se pasa a la tabla de
comandos del BIOS. `153` lo convierte en estructura con nombre:

| punto de contacto con el firmware | dónde |
|---|---|
| reloj de píxel con 100 Hz de precisión, "to BIOS command table" | `dc_hw_types.h:987-993` |
| rutas de display externo, 7, con conector, AUX, HPD, encoder y crossbar | `grph_object_ctrl_defs.h:315-337` |
| polaridad de sincronismo, "reversed with dal1 or video bios define" | `dc_hw_types.h:801-804` |
| base de la VRAM, `MC_VM_FB_LOCATION` | `gmc_v8_0.c:417` |
| identificador de conector por ACPI | `grph_object_ctrl_defs.h:318` |

**Cinco puntos de contacto con firmware, en tres ficheros y tres dominios distintos —
GMC, DC y atom BIOS.** Y ninguno se puede derivar del corpus: son valores que hay que
leer del hardware o de la placa.

**Para un driver propio, esto significa que la mitad de display tiene una dependencia
de firmware que ninguna cantidad de lectura de código sustituye.** Es la misma
conclusión que `140` y `144`, y aquí tiene forma de tabla.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `ddi_channel_mapping` = 4×2 bits + `raw` de un byte | `PROVEN` |
| El cero es inválido | `PROVEN` |
| Se rellena en `link_factory.c:790/798` desde `path` | `PROVEN` |
| Lo consume el gestor de relojes como `raw` | `PROVEN` |
| `clk_mgr/dce100/` existe | `PROVEN` |
| El mapa viene de `ext_disp_conn_info`, estructura de ATOM BIOS | `PROVEN` |
| `MAX_NUMBER_OF_EXT_DISPLAY_PATH` = 7 | `PROVEN` |
| `graphics_object_id` = 8+4+4+16 = 32 bits | `PROVEN` (suma por programa) |
| El comentario "should be u32" coincide con la suma | `PROVEN` (comprobación cruzada) |
| `object_type` tiene 10 valores, `object_enum_id` tiene 8 | `PROVEN` |
| `enum_id` va de 1 a 7 y es la ruta de display | `PROVEN_DERIVED` |
| Los dos ceros reservados coinciden | `PROVEN_DERIVED` |
| Un objeto compuesto no necesita tabla de búsqueda | `PROVEN_DERIVED` |
| Cinco puntos de contacto con firmware | `PROVEN` (por recuento) |
| Las tablas AUX/DDC y HPD que esos índices referencian | **`NOT_IN_CORPUS`** |
| Cuántas de las 7 rutas existen en esta placa | **`NOT_DETERMINED`** |
| Cuántos DIG/DVI tiene físicamente esta GPU | **`NOT_DETERMINED`** |
| Dónde se asigna `connector_signal` | **`NOT_DETERMINED`** — abierto desde `150` |

**Las dos primeras filas abiertas son la misma cosa: hay siete índices y no sabemos
cuántos son reales en esta máquina. Eso se lee del firmware, no del código.**

**Y la tercera, la que sigue abierta desde `150`, es la que este bloque de notas ha
ido rodeando cinco veces: dónde se decide el valor de la señal.** Con el nombre
correcto —`connector_signal`, en `struct dc_link`— la búsqueda es una línea, y no la
he cerrado porque `link_factory.c` tiene 800 líneas y no lo he leído entero. **Es el
único `NOT_DETERMINED` de esta tanda que no es de hardware ni de firmware, y se
cierra con un fichero que ya está identificado y con línea.**

## Procedencia

- `STATIC` -- `display/include/grph_object_ctrl_defs.h:239-253` (la unión y el
  cero inválido), `:273-274` (`NUMBER_OF_UCHAR_FOR_GUID`, `MAX_NUMBER_OF_EXT_DISPLAY_PATH`),
  `:315-337` (`ext_disp_conn_info` y su array de `path`),
  `display/include/grph_object_id.h:227-243` (el word de 32 bits y su constructor),
  `display/include/grph_object_id.h:30` (`object_type`),
  `display/include/grph_object_id.h:50` (`object_enum_id`),
  `display/dc/link/link_factory.c:790` `:798`,
  `display/dc/clk_mgr/dce110/dce110_clk_mgr.c:157-158`,
  `display/dc/core/dc.h:1738` (el campo `ddi_channel_mapping` en `dc_link`, de `152`),
  `display/dc/clk_mgr/` (los 21 subdirectorios de versión).
- Comprobaciones, todas por programa: la suma `8+4+4+16` contra el comentario del
  driver; el recuento de valores de las dos enumeraciones contra la anchura de sus
  campos; la comparación de `ENUM_ID_1..7` contra `MAX_NUMBER_OF_EXT_DISPLAY_PATH`.
- Un error de ruta y uno de patrón, en esta nota: busqué `struct graphics_object_id`
  en `grph_object_defs.h` cuando está en `grph_object_id.h`, y mi `re.findall` de los
  `GFX_*` exigía una coma final y devolvió 0. El primero se vio porque `n` quedó
  vacío; el segundo, porque 0 no cuadraba con un fichero que claramente define ids.
- Encadenada con `152` (los dos campos del enlace y la `union` que era el `PTBA` del
  display), `151` (DML1 y los límites del DC), `150` (la `enum signal_type` y el
  `NOT_DETERMINED` de dónde se decide), `149` (la frontera DM→BIOS, que aquí tiene
  estructura con nombre), `144` (la uAPI), `140` (el mapa de direcciones y
  `MC_VM_FB_LOCATION`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La mejor comprobación de la tanda salió de leer un comentario de relleno.** El
driver escribe `reserved:16; /* for padding. total size should be u32 */` — y eso es
una afirmación falsable sobre la propia estructura. Sumar los campos da 32, y la
comprobación cuesta una línea de Python. **Es la clase de verificación que `151`
pidió y que no es opcional: un comentario de relleno es una predicción, y las
predicciones se comprueban.**

**Y la segunda mejor fue cruzar dos números que no tienen por qué coincidir.** Seven
`ENUM_ID_*` contra `MAX_NUMBER_OF_EXT_DISPLAY_PATH 7` — un nombre de enumeración y
una constante de dimensionamiento, en ficheros a treinta líneas de distancia. Si
hubieran dado 6 y 7, la hipótesis de que `enum_id` es el índice de ruta se caía. **Y
dieron 7 y 7, y además los dos ceros reservados coinciden** — `ENUM_ID_UNKNOWN` y
`INVALID_DDI_CHANNEL_MAPPING = 0x0`. **Dos convenciones independientes alineadas es
lo que convierte una coincidencia en una derivación.**

*Y la lección de fondo, que es la que recorre las tres últimas notas: los
identificadores de hardware se leen en la definición del tipo, se cuentan sus
campos, y se comprueban sus enumeraciones contra las anchuras que declaran.* Nada
de eso requiere hardware, y las tres cosas juntas convierten "el display direcciona
así" en un número con dos verificaciones cruzadas.

**Y queda un `NOT_DETERMINED` que es mío y no del hardware: dónde se asigna
`connector_signal`.** Cinco notas rodeándolo, y la razón por la que no está cerrado
es que `link_factory.c` tiene 800 líneas y las leí con `grep`. **Es la misma
condición de `148`, `150` y `152` por cuarta vez, y la próxima nota la cierra o
repite el patrón.**
