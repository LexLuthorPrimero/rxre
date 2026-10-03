# 166 · La tabla del BIOS declara dos conectores: uno DVI y uno HDMI

```
CLASSIFICATION=DOCUMENTATION · TRACK=OBSERVED
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=SYSFS_READ_ONLY · GPU INTACTA
```

## Qué resuelve

**El bloque más grande que quedaba abierto desde `151`: cuáles son las salidas físicas
de esta placa.** Y se resuelve leyendo `/sys/class/drm`, sin placa, sin root y sin MMIO.

**⇒ El BIOS de esta tarjeta declara dos conectores, y son un DVI-D y un HDMI-A. No hay
DisplayPort, no hay VGA, no hay LVDS.** `PROVEN`, observado.

**Y con eso queda documentada de una vez, de principio a fin, la cadena de salida que
las quince notas anteriores han recorrido por partes.**

## 1 · Lo observado

```
/sys/class/drm/card0/device:uevent   DRIVER=i915      <- la iGPU Intel, la de la sesión
/sys/class/drm/card1/device:uevent   DRIVER=amdgpu    <- esta GPU
```

| conector | tarjeta | estado | modos | EDID |
|---|---|---|---|---|
| **`card1-DVI-D-1`** | amdgpu | `disconnected` | **0** | 0 bytes |
| **`card1-HDMI-A-2`** | amdgpu | `disconnected` | **0** | 0 bytes |
| `card0-HDMI-A-1` | i915 | **`connected`** | **39** | — |
| `card0-VGA-1` | i915 | `disconnected` | 0 | — |

**⇒ Dos conectores en la AMD, ambos desconectados, con cero modos y EDID de cero bytes.
Ninguno de los dos es DisplayPort ni VGA.** `PROVEN`, observado.

**⇒ Y el `VGA-1` es de la iGPU, no de la AMD.** `PROVEN`.

**⇒ Y la numeración de conectores es global: `HDMI-A-2` es el segundo HDMI del sistema
porque `HDMI-A-1` lo ocupa la iGPU.** `PROVEN_DERIVED`. **Esa numeración la hace el
núcleo de drm, no el driver de amdgpu, y es la prueba de que los conectores de las dos
tarjetas están en un mismo registro.**

**Y con esto queda cerrada `233` de otra manera que con «cero CRTC»:** no es sólo que no
haya nada conectado, es que **la lista de salidas de esta GPU es de longitud dos y
conocida.**

## 2 · Y el tipo de conector es dato de firmware, y la cadena entera

El `switch` de `154` que decide `connector_signal` funciona sobre `link->link_id.id`, y
ese `link_id` sale de la tabla de conectores del ROM:

```c
link_factory.c:518    link->link_id =
link_factory.c:519            bios->funcs->get_connector_id(bios, init_params->connector_index);
link_factory.c:523    DC_LOG_DC("BIOS object table - link_id: %d", link->link_id.id);
```

**Y `get_connector_id` lee una tabla del propio ROM, en un offset que el ROM se indica a
sí mismo:**

```c
bios_parser.c:167   uint32_t connector_table_offset = bp->object_info_tbl_offset
bios_parser.c:168           + le16_to_cpu(bp->object_info_tbl.v1_1->usConnectorObjectTableOffset);
bios_parser.c:170   ATOM_OBJECT_TABLE *tbl = ((ATOM_OBJECT_TABLE *) bios_get_image(&bp->base,
bios_parser.c:171                   connector_table_offset, struct_size(tbl, asObjects, 1)));
bios_parser.c:175           dm_error("Can't get connector table from atom bios.\n");
```

**Y el bucle que la recorre, con su presupuesto:**

```c
dc.c:237   for (i = 0; dc->link_count < connectors_num && i < MAX_LINKS; i++) {
dc.c:238           struct graphics_object_id connector_id = bios->funcs->get_connector_id(bios, i);
dc.c:242           if (connector_id.id == CONNECTOR_ID_UNKNOWN)
dc.c:243                   continue;
```

**⇒ La cadena completa, y no hay ningún salto sin documentar:**

```
ROM (ATOM_OBJECT_TABLE)
  -> bios_parser.c:167-172   usConnectorObjectTableOffset, bios_get_image
  -> bios_parser.c:158       bios_parser_get_connector_id
  -> dc.c:238                bucle sobre las entradas, saltando UNKNOWN
  -> link_factory.c:518      link->link_id
  -> link_factory.c:626-671  el switch de 154: decide connector_signal
  -> dce110_str_enc_funcs    uno de los cuatro setters de 157
  -> dce_stream_encoder.c    los registros, con la máscara de 147/156
```

**Quince notas recorrieron este camino por partes y aquí está entero, con la línea.** `PROVEN_DERIVED`.

**Y el número de conectores que el driver construye es el número de entradas no-`UNKNOWN`
de la tabla del ROM, acotado por `connectors_num` y por `MAX_LINKS`.** `PROVEN_DERIVED`.

## 3 · Y el driver avisa de que la tabla puede mentir

El comentario que precede al bucle, en `dc.c:232-236`, es de primera clase:

> *"VBIOS may report a higher amount of valid indices than there are actual. Some VBIOS
> have valid configurations for more connectors than there act on the card. This may be
> because the manufacturer used the same VBIOS for variants of the same card."*

**⇒ El propio driver advierte que la tabla del BIOS puede declarar más salidas de las
que la tarjeta tiene cableadas, porque el fabricante comparte el VBIOS entre variantes
del mismo chip.** `PROVEN`.

**⇒ Por tanto lo que queda probado es «el BIOS de esta tarjeta declara dos conectores, un
DVI-D y un HDMI-A», y NO «la placa tiene exactamente dos conectores físicos».** La
diferencia importa, y el propio código la declara. `PROVEN_DERIVED`.

**Es la misma clase de precisión que `164` aplicó entre la dirección base y el tamaño de
la VRAM: el valor observado es real, y lo que no afirma es todo lo que uno le pone
encima por costumbre.**

## 4 · Y lo que esto dice de las cifras de la banda

| afirmación | fuente | estado |
|---|---|---|
| 7 registros `DP_VID_TIMING` | `232` | el driver los declara |
| 4 carriles, HBR3, 32,40 Gbps | `160` | el driver lo declara |
| 7 rutas en `ext_disp_conn_info` | `153` | el driver las declara |
| `MAX_NUMBER_OF_EXT_DISPLAY_PATH 7` | `153` | constante del driver |
| **2 conectores en la tabla del BIOS: DVI-D y HDMI-A** | **sysfs, observado** | **la placa** |

**⇒ Esta GPU declara capacidad DisplayPort completa —siete salidas, cuatro carriles,
HBR3— y el BIOS de la tarjeta no expone ni un solo DisplayPort.** `PROVEN_DERIVED`.

**Y no es una anomalía: es la razón por la que existe el comentario de `dc.c:232`, y es lo
que `158` ya había aislado por el otro lado** —el codificador analógico no se construye
porque este DC no lo tiene, pese a que la placa arranque por VGA de BIOS.

**⇒ Las siete salidas DP y las siete rutas del firmware son el techo del driver; los dos
conectores DVI y HDMI son el suelo de la placa. Entre los dos hay 25,92 Gbps que esta
tarjeta puede mover y no tiene por dónde.** `PROVEN_DERIVED`.

**Y el más lento de los dos declarados manda sobre el más rápido:** el DVI-D es
`DVI_SINGLE_LINK` o `DVI_DUAL_LINK` en el enums de `150`, y el HDMI es
`SIGNAL_TYPE_HDMI_TYPE_A`, que es el `hdmi_set_stream_attribute` de la tabla. **Ninguno de
los dos toca los 4 carriles ni HBR3, porque ninguno es un enlace DisplayPort.** `PROVEN_DERIVED`.

## 5 · Y la receta para observar la tabla sin MMIO

```c
link_factory.c:523   DC_LOG_DC("BIOS object table - link_id: %d", link->link_id.id);
```

**⇒ La tabla de conectores del BIOS se anuncia en el log, a nivel `DC_LOG_DC`.** `PROVEN`.

**Y esto explica por qué `154` no encontró esas líneas y por qué la vía de `143`
(`LINK_INFO` = `DC_LOG_HW_HOTPLUG`) no las ve:** **son dos niveles de log distintos.** El
nivel para ver la tabla del BIOS es el de DC, no el de hotplug, y eso se activa con la
máscara de depuración del DC, no con una bandera de HPD. `PROVEN_DERIVED`.

**⇒ La receta para el siguiente intento en campo es exacta y no requiere placa:**
`amdgpu.dc=0x...` con el bit de `DC_LOG_DC` puesto, más un arranque con la AMD
conectada a un monitor, y leer las líneas `BIOS object table - link_id:`. Con eso se
obtiene el `id` bruto de cada entrada de la tabla, que es el dato que el `switch` de `154`
recibe. `PROVEN_DERIVED`.

**Y es lo que separa `NOT_DETERMINED` de observado en la última frontera de firmware que
queda: la tabla de conectores no está ausente del corpus, está ausente del log porque el
nivel de log no estaba puesto.** Es el mismo hallazgo que `155` —`LINK_INFO` sin máscara no
produce nada— con un nivel distinto.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| La AMD declara 2 conectores: `DVI-D-1` y `HDMI-A-2` | `PROVEN`, observado |
| Ambos desconectados, 0 modos, EDID de 0 bytes | `PROVEN`, observado |
| El `VGA-1` es de la iGPU, no de la AMD | `PROVEN`, observado |
| La numeración de conectores es global entre tarjetas | `PROVEN_DERIVED` |
| La cadena ROM → `link_id` → señal → registros, entera | `PROVEN_DERIVED` |
| El nº de enlaces = entradas no-`UNKNOWN` de la tabla del BIOS | `PROVEN_DERIVED` |
| La tabla puede declarar más salidas de las cableadas | `PROVEN` — dice el propio driver |
| La placa tiene exactamente 2 conectores físicos | **`NOT_DETERMINED`** |
| La cadena no declara ningún DisplayPort, con 32,40 Gbps de techo | `PROVEN_DERIVED` |
| Ni el DVI ni el HDMI tocan 4 carriles ni HBR3 | `PROVEN_DERIVED` |
| La tabla se anuncia a nivel `DC_LOG_DC` | `PROVEN` |
| El `id` bruto de cada entrada, con la máscara puesta | **`NOT_DETERMINED`** — nivel 2 |
| Si un monitor en la HDMI daría 4K60 | **`NOT_DETERMINED`** |
| La polaridad de HPD, que `155` dejó como tabla de firmware | **`NOT_DETERMINED`** |

**La primera de las abiertas es la única que puede ser falsa, y es falsa a favor de la
prueba: la tabla declara dos, y la placa puede tener una entrada más que no esté
cableada.** *El driver lo dice explícitamente, y es un recordatorio de que un `PROVEN` de
una tabla de firmware es un `PROVEN` sobre lo que el firmware afirma, no sobre lo que el
hierro tiene.*

**La segunda se cierra con una bandera y un monitor, y es la siguiente jugada de campo:
`amdgpu.dc=<máscara de DC_LOG_DC>`, y leer `BIOS object table - link_id:`.**

## Procedencia

- `OBSERVED` -- `/sys/class/drm/card0/device/uevent` y `card1/device/uevent` (qué driver
  lleva cada tarjeta), y para cada uno de los cuatro conectores los ficheros `status`,
  `enabled`, `modes`, `dpms` y `edid`, con `wc -l` sobre `modes` y `wc -c` sobre `edid`.
  Sin root, sin MMIO, sin escribir nada.
- `STATIC` -- `display/dc/link/link_factory.c:513-523` (la asignación de `link_id` y el
  `DC_LOG_DC`), `:626-671` (el `switch` de `154`),
  `display/dc/bios/bios_parser.c:158-178` (`bios_parser_get_connector_id`, el offset
  `usConnectorObjectTableOffset` y `bios_get_image`),
  `display/dc/bios/bios_parser.c:2969` (la asignación a `.get_connector_id`),
  `display/dc/core/dc.c:232-250` (el comentario de la tabla que puede mentir, y el bucle
  con `connectors_num`, `MAX_LINKS` y el salto de `CONNECTOR_ID_UNKNOWN`),
  `display/dc/bios/command_table2.c:332` (el `MAX_LINKS` de la otra tabla de comandos).
- **Y cuatro errores de ruta y de orden de tubería propios, en dos calls consecutivos.**
  (1) Encadené `cut` antes de `sed` por tercera vez en la tanda, lo que truncó las rutas
  al ancho de corte y produjo cuatro líneas de ruta desnuda sin contenido. (2) Busqué
  `dc_link.c` en `display/dc/core/` y no existe: la asignación de `link_id` está en
  `link_factory.c`. (3) Un `grep` de `link_id\s*=` en `dc_link.c` volvió vacío por el
  fichero inexistente, y lo leí como «no se asigna». (4) El patrón `get_connector_id` con
  `--include='*.c'` sobre `dc/bios/` devolvió siete líneas de ruta vacía por el mismo
  problema del punto 1. **Los tres primeros habrían producido un `PROVEN_ABSENT` falso
  sobre toda la cadena de firmware, y la cuarta vez que eso casi me ocurre en esta
  tanda.**
- Encadenada con `165` (las 325.854 líneas que no se ejecutan, y aquí **cuáles** no se
  ejecutan:
  las dos salidas de una lista de dos), `233` (cero CRTC, y aquí la lista que está detrás
  de ese cero), `160` (4 carriles y HBR3, y aquí que no hay DisplayPort que los use),
  `158` (VGA sin codificador analógico, y aquí que el VGA es de la iGPU),
  `157` (los cuatro setters, y aquí cuál se usaría en cada uno de los dos conectores),
  `155` (**los puntos de firmware, y el noveno: el `id` de cada entrada de la tabla del
  BIOS, que ahora se sabe anunciar a nivel `DC_LOG_DC` y no a nivel de hotplug**),
  `154` (el `switch` que recibe el `link_id`), `153` (las siete rutas del driver frente a
  las dos del BIOS), `151` (los `ENCODER_ID_*` bloqueados por firmware, y ahora la
  cadena que los produce).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El bloque más grande que quedaba abierto llevaba diecinueve notas esperando y se ha
cerrado
en un `ls` de `/sys/class/drm`. Y eso no es suerte: es que la respuesta estaba siempre
en el objeto que el driver registra, y nadie se había preguntado qué registra cuando no
tiene nada conectado.**

*Quince notas midterm mi subsystem —enlace, reloj, IRQ, codificador, tablas de swizzle,
calibrador— y todas respondían a «qué hace el driver», no a «qué tiene la tarjeta».* **Y
la pregunta que faltaba, la que la tabla del BIOS responde, es la más simple de todas:
¿cuántas salidas tiene y de qué tipo? Y eso está en el nombre del conector, que es un
fichero de texto en `/sys`, y que la placa escribe al arrancar.**

**Y la observación de método que sale es más útil que el hallazgo: `card1-DVI-D-1` y
`card1-HDMI-A-2` son, literalmente, la respuesta a dos `NOT_DETERMINED` de `151` y de
`153`, y la forma de la respuesta no se parecía en nada a las preguntas.** *Cinco notas
buscando `get_connector_id` en el árbol, contando los `CONNECTOR_ID_*`, midiendo los
`ENCODER_ID_*` que el BIOS sustituye — y la respuesta era un nombre de fichero con un
número al final, y el número al final no es el del BIOS sino el de drm.*

**Y hay un segundo resultado, que es de método y no de contenido: el driver avisa en su
propio comentario que la tabla del BIOS puede declarar más salidas de las que la placa
tiene cableadas.** *Y eso obliga a acotar la afirmación: lo probado es lo que afirma el
firmware, no lo que hay soldado.* **Es la tercera vez en dos notas que un dato del
firmware necesita una frase que separe «lo que el BIOS dice» de «lo que el hardware
tiene» — la primera fue `164` con la dirección base de la VRAM, la segunda el hueco de
42 GiB— y las tres son la misma disciplina: un valor leído de una tabla de firmware es un
dato sobre el firmware.**
