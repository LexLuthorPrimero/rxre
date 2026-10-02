# 155 · El Display Core de esta máquina es DCE 11.2, y eso refuta dos conclusiones de `147`

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC+RUNTIME-OBSERVE
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=READ_ONLY · GPU INTACTA
```

## Qué resuelve

**La corrección más consecuente de la tanda, y sale del log.**

**Esta GPU no usa la tabla de recursos de DCE 10.0.** `147` construyó su modelo
sobre `dce100_resource.c`, y `147` no era el fichero. **El Display Core que se
instancia en esta máquina es DCE 11.2**, y usa `dce112_resource.c`.

**Consecuencia directa: `HDMI_CLOCK_CHANNEL_RATE` existe en esta máquina**, y
`147`/`148` afirmaron lo contrario en dos notas.

## 1 · La observación, y su comprobación cruzada

```
LOG:    amdgpu 0000:01:00.0: [drm] Display Core v3.2.378 initialized on DCE 11.2
HEADER: display/dc/dc.h:66   #define DC_VER "3.2.378"
```

**El log dice `v3.2.378` y la constante del header dice `"3.2.378"`. El mismo
número, por dos vías, y la versión de la abstracción del DC queda `OBSERVED`.**
`PROVEN`, con comprobación cruzada.

**Es la tercera vez que el método de `140` funciona —leer lo que el driver
imprime— y la primera que produce una refutación en lugar de una confirmación.**

## 2 · Y el error de raíz: dos ejes distintos

**El error fue inferir la versión del código del DC a partir de la familia del ASIC.**

| eje | valor en esta máquina | de dónde |
|---|---|---|
| **registros** | **DCE 10.0** | `gmc_v8_0.c` incluye `dce/dce_10_0_d.h` |
| **código del DC** | **DCE 11.2** | el log, y `dce112_*` |

**Son dos ejes distintos y amdgpu los mapea por separado: registros de DCE 10.0 con
código de DCE 11.2.** `PROVEN_DERIVED`, y es la clase de hecho que no se deduce de
ningún nombre de fichero.

*Porque `dce_10_0_d.h` es el header de registros y `dce112_resource.c` es el de
código, y en un driver real esos dos ejes no tienen por qué coincidir.* **En un
dispositivo invented por una placa, `dce_10_0` describe el hardware y `dce112`
describe el camino de código que amdgpu eligió para él.**

**Y esto invalida el razonamiento que usé en `147` sin que lo notara:** *"el chip es
Polaris12, luego el DC es DCE 10.0"*. El primer paso es correcto y el segundo no.

## 3 · Lo que hay en `dce112/` — y está todo

```
dc/resource/dce112/   dce112_resource.c   dce112_resource.h
dc/dce112/            dce112_compressor.c  dce112_compressor.h
dc/hwss/dce112/       dce112_hwseq.c       dce112_hwseq.h
```

**Y `dce112_resource.c:300-304` usa una macro que `147` no había catalogiado:**

```c
        SE_COMMON_MASK_SH_LIST_DCE112(__SHIFT)
        SE_COMMON_MASK_SH_LIST_DCE112(_MASK)
```

**`147` catalogó dos listas, `DCE80_100` y `DCE110`. Hay una tercera, `DCE112`, y es la
que usa esta máquina.**

## 4 · El recuento corregido, y las dos macros comparadas

Impreso por programa sobre `dce_stream_encoder.h`:

| | campos puestos | en cero |
|---|---|---|
| `DCE80_100` — la tabla de `147`, para DCE 10.0 | 89 de 130 | 41 |
| **`DCE112` — la de ESTA máquina, DCE 11.2** | **91 de 130** | **39** |

**Y las dos listas, campo a campo:**

```
SE_COMMON_MASK_SH_LIST_DCE110   7 campos        SE_COMMON_MASK_SH_LIST_DCE112   6 campos
  AFMT_CNTL.AFMT_AUDIO_CLOCK_EN                   AFMT_CNTL.AFMT_AUDIO_CLOCK_EN
  HDMI_CONTROL.HDMI_CLOCK_CHANNEL_RATE            HDMI_CONTROL.HDMI_CLOCK_CHANNEL_RATE
  HDMI_CONTROL.HDMI_DATA_SCRAMBLE_EN              HDMI_CONTROL.HDMI_DATA_SCRAMBLE_EN
  DIG_FE_CNTL.TMDS_PIXEL_ENCODING                  DIG_FE_CNTL.TMDS_PIXEL_ENCODING
  DIG_FE_CNTL.TMDS_COLOR_FORMAT                    DIG_FE_CNTL.TMDS_COLOR_FORMAT
  DIG_FE_CNTL.DIG_STEREOSYNC_SELECT                DP_VID_TIMING.DP_VID_M_DOUBLE_VALUE_EN
  DIG_FE_CNTL.DIG_STEREOSYNC_GATE_EN
```

**Son el mismo conjunto salvo en dos campos:** DCE 11.0 añade stereosync, DCE 11.2
añade `DP_VID_M_DOUBLE_VALUE_EN`. **Y las cinco primeras entradas son idénticas en
ambas**, y **las cinco existen en las dos.**

## 5 · Las dos refutaciones

### `147` — «esta GPU no tiene `HDMI_CLOCK_CHANNEL_RATE`»

**`REFUTED`.** Está en la lista `DCE112`, que es la de esta máquina, en
`HDMI_CONTROL`. `PROVEN`.

**Y por tanto las dos entradas que `147` contabilizó como "cero por no existir en
generación" —`HDMI_CLOCK_CHANNEL_RATE` y `AFMT_AUDIO_CLOCK_EN`— no son ceros por
ausencia: son ceros porque `147` miró la tabla equivocada.** `PROVEN_DERIVED`.

### `148` — «el umbral de 340 MHz no es programable en esta GPU»

**`REFUTED` para esta máquina.** La cadena que `148` construyó queda así:

| fichero | qué tiene | ¿programable aquí? |
|---|---|---|
| `dce_stream_encoder.c:43` | `HDMI_CLOCK_CHANNEL_RATE_MORE_340M 340000` | el umbral existe |
| `dc_hw_types.h:826-828` | flag `LTE_340MCSC_SCRAMBLE` | la decisión se declara |
| `dce_stream_encoder.h` | `HDMI_CONTROL.HDMI_CLOCK_CHANNEL_RATE` | **el campo EXISTE y tiene máscara distinta de cero** |

**⇒ Los tres eslabones existen, y en esta máquina el reloj de canal HDMI es
programable.** `PROVEN_DERIVED`.

## 6 · Y las dos correcciones de `148` que sí se sostienen

**La división importa, y hay que hacerla explícita.**

**Corrección 1 de `148` — «el código es de DCE 11.0, no de esta GPU». SE SOSTIENE.**
`dce112_hwseq.c` tiene **cero** apariciones de `dce110_stream_encoder` — medido por
programa. **DCE 11.2 no usa el tipo `dce110_stream_encoder`.** `PROVEN_ABSENT`.

**Corrección 2 de `148` — «`TMDS_PIXEL_ENCODING = 1` es YCbCr 4:2:2, no un tipo de
salida». SE SOSTIENE**, sin cambios: la enumeración de `dc_hw_types.h:773-780` no
depende de la versión del DC.

**Lo que se cae es la conclusión que las rodeaba**, que era "el campo no existe en
esta GPU". El campo existe; lo que no existe es el camino de código de DCE 11.0 que
lo escribía. **Son dos hechos distintos y yo los fundí.**

## 7 · Y lo que sí sobrevive de `147`, `151`, `152`, `153`, `154`

| nota | afirmación | ¿afectada? |
|---|---|---|
| `147` | los dos `struct` tienen los mismos 130 nombres | **no** — es la definición, no la tabla |
| `147` | una macro genera las dos tablas (`SE_SF`) | **no** |
| `147` | los bits 7-11 son el fragmento | **no** |
| `147` | el patrón del fragmento (137, 133, 130) | **no** |
| `147` | 89 de 130 | **sí** → 91 de 130 |
| `147` | el reloj de canal ausente | **sí** → `REFUTED` |
| `148` | el sink es genérico | **no** |
| `148` | 3 campos de registro definidos a mano | **no** |
| `149` | la frontera DM→DC, 4 enums + 16 bits | **no** |
| `149` | `enum_id` va de 1 a 7 | **no** — confirmado por `154` |
| `151` | **DCE 11.2 usa DML1** | **no, y reforzada** — `dce112` tampoco pone `using_dml2` |
| `151` | `kzalloc_obj` explica el `false` inicial | **no**, y ahora con `link_create:929` |
| `152` | los dos campos de `dc_link` | **no** |
| `153` | el identificador de 32 bits, dos verificaciones cruzadas | **no** |
| `154` | el `switch` sobre `link_id.id` | **no** |

**Once de quince afirmaciones sobreviven intactas, y las cuatro afectadas son
exactamente las que dependían de qué tabla de recursos se está leyendo.** `PROVEN`.

**Y `151` sale reforzada por una vía que no había buscado:** `dce112` está en la lista
de los seis ficheros de recursos que **no** ponen `using_dml2` — y ahora sé que el
fichero que cuenta es el correcto, porque el log dice que el DC es DCE 11.2.

## 8 · Y el `NEGATIVE_RESULT` sobre mi propio observable propuesto

`154` terminó diciendo que la línea `LINK_INFO` de `link_factory.c:722` era un punto
de observación sin placa. **`LINK_INFO` es `DC_LOG_HW_HOTPLUG`** (`link_factory.c:53-55`):

```c
#define LINK_INFO(...) \
        DC_LOG_HW_HOTPLUG(  \
                __VA_ARGS__)
```

**Y `journalctl -k -b | grep -c 'Connector\['` devuelve 0.** **La línea no se imprime
en esta máquina.** `PROVEN`, por ausencia con el productor identificado — el mismo
argumento que cerró `142` para la apertura AGP.

**Así que el `NOT_DETERMINED` de `154` sobre qué conector tiene esta placa sigue
abierto, y esta nota además de que la vía que yo proponía no funciona sin cambiar
una máscara de log.** `NEGATIVE_RESULT`, sobre mi propia propuesta.

**Y hay un dato colateral del log que importa para el proyecto y que no estaba en mi
cabecera:**

```
i915 0000:00:02.0: [drm] Found haswell (device ID 0412) integrated display
```

**Esta máquina tiene una iGPU Intel Haswell además de la RX550.** El compositor
 corre sobre la Intel, no sobre la AMD. **Eso no cambia ningún `NOT_DETERMINED` de
esta nota, pero sí tiene consecuencia sobre el bloqueo F1** —"requiere cerrar la
sesión gráfica"— y no la he investigated porque no es de mi incumbencia en esta nota.
Lo dejo anotado, con el número y la fuente, para quien lo necesite.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El DC de esta máquina es DCE 11.2 | `OBSERVED` + `PROVEN` |
| `DC_VER "3.2.378"` coincide con el log | `PROVEN` (comprobación cruzada) |
| Registros DCE 10.0 con código DCE 11.2 | `PROVEN_DERIVED` |
| La tabla es `dce112_resource.c`, no `dce100` | `PROVEN` |
| Existe una tercera macro, `SE_COMMON_MASK_SH_LIST_DCE112` | `PROVEN` |
| 91 de 130 campos, 39 en cero | `PROVEN` (por programa) |
| `HDMI_CLOCK_CHANNEL_RATE` existe en esta máquina | `PROVEN` |
| `AFMT_AUDIO_CLOCK_EN` existe en esta máquina | `PROVEN` |
| `147`: el reloj de canal ausente | **`REFUTED`** |
| `148`: el umbral de 340 MHz no programable | **`REFUTED`** |
| `148`: el código es de DCE 11.0, no de esta GPU | se sostiene (`dce112_hwseq.c`, 0 apariciones) |
| `148`: `TMDS_PIXEL_ENCODING` es YCbCr 4:2:2 | se sostiene |
| 11 de 15 afirmaciones de las cinco notas | intactas |
| DCE 11.2 usa DML1 | `PROVEN_DERIVED`, reforzada |
| `LINK_INFO` no se imprime aquí | `PROVEN` (ausencia, productor identificado) |
| Cuál es el `connector_index` de esta placa | **`NOT_DETERMINED`** |
| Cuántos DIG/DVI tiene físicamente esta GPU | **`NOT_DETERMINED`** |
| Si esta placa tiene DP, HDMI, VGA o LVDS | **`NOT_DETERMINED`** |
| `DP_VID_M_DOUBLE_VALUE_EN`, qué es | **`NOT_DETERMINED`** |
| La iGPU Intel y su efecto sobre F1 | **`NOT_INVESTIGATED`** |

**Las tres primeras siguen siendo firmware, y la quinta es un campo nuevo que aparece
en la lista de esta máquina y que nadie ha mirado: `DP_VID_TIMING.
DP_VID_M_DOUBLE_VALUE_EN`.**

## Procedencia

- `OBSERVED` -- `journalctl -k -b`, dos líneas: la del Display Core y la de la iGPU
  Intel. **NIVEL 2**, sin MMIO.
- `STATIC` -- `display/dc/dc.h:66` (`DC_VER`),
  `display/dc/resource/dce112/dce112_resource.c:300-304` (la macro de DCE 11.2),
  `display/dc/dce/dce112/`, `display/dc/hwss/dce112/`,
  `display/dc/dce/dce_stream_encoder.h` (las tres listas de campos),
  `display/dc/link/link_factory.c:53-55` (`LINK_INFO` = `DC_LOG_HW_HOTPLUG`),
  `display/dc/link/link_factory.c:917-925` (de `154`),
  `display/dc/resource/dce100/dce100_resource.c:250-254` (la tabla de `147`),
  `display/dc/clk_mgr/dce100/` (de `153`).
- Recuento por programa: campos puestos y en cero para las dos macros; comparación
  campo a campo de `DCE110` contra `DCE112`; presencia de los dos campos refutados;
  el recuento de `dce110_stream_encoder` en `dce112_hwseq.c`.
- Encadenada con `154` (la decisión de la señal, y el `NOT_DETERMINED` que queda),
  `153` (el identificador de 32 bits), `152` (`struct dc_link`),
  `151` (DML1 y los límites del DC — **reforzada**), `150` (la enumeración de señal),
  `149` (la frontera DM→DC), `148` (**dos de sus tres conclusiones refutadas**),
  `147` (**su tabla y dos conclusiones refutadas**), `140` (el método de leer el log).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La ruta que funcionó tres veces dio una refutación, y eso es exactamente para lo que
sirve.** `140` confirmó el mapa de direcciones, `142` cerró la apertura AGP por
ausencia, y `155` acaba de refutar dos conclusiones mías. **Las tres vinieron de leer
una línea que el driver ya escribía en el log al arrancar, sin placa, sin root, sin
MMIO.**

*Y el error de raíz tiene una forma que ya se había visto en el mismo bloque y que
**Y hay una regla transferible que sale de aquí, y es la generalización de todas las
demás de la tanda:** *antes de decidir qué variante de código se está leyendo,
comprobar qué variante se instancia.* No por el nombre del ASIC, no por el nombre
del header, no por suposición razonable — **por lo que el driver dice que
instanció.** Cuesta un `grep` en el log y sustituye a cinco notas de trabajo
equivocado.
**Y hay una regla transferible que sale de aquí, y es la generalización de todas las
demás de la tanda:** *antes de decidir qué variante de código se está leyendo,
comprobar qué variante se instancia.* No por el nombre del ASIC, no por el nombre
del header, no por suposición razonable — **por lo que el driver dice que
instanció.** Cuesta un `grep` en el log y sustituye a cinco notas de trabajo
equivocado.

**Y una observación sobre el coste de no hacerlo, que es la parte incómoda:** cuatro
notas —`147`, `148`, `149`, `150`— se construyeron sobre una tabla equivocada, y
`147` llegó a una conclusión sobre el hardware de esta GPU que era falsa y que
`155` desmiente con una línea de log. **Ninguna de las cuatro era incorrecta como
afirmación sobre DCE 10.0; las cuatro son incorrectas como afirmación sobre esta
máquina.** Y la diferencia entre las dos cosas es un identificador que el kernel
escribe en el log y que yo no miré hasta que una pregunta de display me llevó a
mirar el log por otro motivo.
