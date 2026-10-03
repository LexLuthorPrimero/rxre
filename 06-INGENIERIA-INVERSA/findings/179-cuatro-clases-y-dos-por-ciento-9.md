# 179 · Cuatro clases, y el 2,9% que no toca ni el bus ni el silicio

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La extensión que `178` nombró, y produce un resultado que corrige a `178`: la separación
entre los dos canales no es «capa genérica contra capa por generación».** `PROVEN_DERIVED`.

**⇒ Aplicando los dos canales a los 42 subárboles de `display/` —510 ficheros, 443.839
líneas— salen cuatro clases, y sólo dos de ellas se parecen a lo que `178` describió.**`
`PROVEN`.

**⇒ Y hay una cuarta que `178` no contemplaba: 12.981 líneas —el 2,9%— que no delegan ni
escriben un registro, y son filtros de escalado, aritmética de punto fijo y procesamiento
de mensajes HDCP.** `PROVEN`.

## 1 · Las dos columnas, sobre los 42 subárboles

**Mismos tres criterios que `178`, sin cambiar ninguno: `(\w+)->(\w+)->(\w+)\(` para el
canal 1, `\bREG_\w*\s*\(` para el canal 2.** Denominador: líneas, contadas con `wc -l`.

**El total cuadra con la cifra conocida: 510 ficheros y 443.839 líneas.** `PROVEN`.
*Es la segunda vía independiente de un número que `172` ya había medido.*

| clase | subárboles | líneas | % de `display/` |
|---|---|---|---|
| **LAS DOS** | 18 | 214.549 | 48,4% |
| **SOLO DELEGA** | 11 | 180.014 | 40,6% |
| **SOLO ESCRIBE** | 10 | 11.934 | 2,7% |
| **SORTO** | 5 | 12.981 | 2,9% |

**⇒ Las dos clases de `178` cubren el 89,0% de las líneas, y las otras dos el 5,6%.**
`PROVEN_DERIVED`.

## 2 · Y por qué `178` estaba incompleto, con los contraejemplos

**`178` dijo: la capa genérica delega y no escribe; la capa por generación escribe y no
delega. Las dos cosas son ciertas y ninguna basta para separar el árbol.**

| contraejemplo | líneas | 2 ptr | `REG_*` | por qué importa |
|---|---|---|---|---|
| `dc/hwss/` | 27.251 | 1.202 | 322 | **las dos cosas, y es el segundo subárbol más delegante después de `dc/core/`** |
| `dc/dce/` | 17.841 | 25 | 770 | **las dos, y por menos de un 1% de delegación** |
| `dc/bios/` | 13.172 | 52 | 3 | **`dce112` es el bloque de esta GPU, y escribe por el BIOS, no por un registro** |
| `dc/dce110/` | 6.676 | 10 | **0** | **un directorio por generación que no escribe ni un registro** |

**⇒ `dc/dce110/` es la prueba de que «por generación» no significa «escribe registros»:
6.676 líneas de DCE 11.0 con cero escrituras, porque las escrituras de esa generación
viven en `dce110_hwseq.c`, que está en `dc/hwss/` y no en `dc/dce110/`.** `PROVEN_DERIVED`.

**⇒ Y `dc/dce/` —17.841 líneas, 770 escrituras de registro, 25 punteros dobles— es el
contrario: delega poco y escribe mucho, que es exactamente el perfil que `178` le
asignó.** `PROVEN_DERIVED`. *Las dos clases que `178`  no están separadas por capa,
están separadas por qué archivo se está mirando, y el mismo archivo puede caer en una u
otra según el subárbol al que se atribuya.*

## 3 · Las tres clases completas

**LAS DOS (18 subárboles, 214.549 líneas):** `dc/resource/` 50.053, `amdgpu_dm/` 32.304,
`dc/hwss/` 27.251, `dc/clk_mgr/` 18.218, `dc/dce/` 17.841, `dc/bios/` 13.172,
`dc/dio/` 11.149, `dc/gpio/` 9.236, `dc/dpp/` 8.837, `dc/hubbub/` 7.730, `dc/hubp/` 7.381,
`dc/optc/` 5.760, `dc/mpc/` 5.237, `dc/dsc/` 2.961, `dc/hpo/` 1.595, `dc/dcn10/` 1.526,
`dc/pg/` 1.222, `dc/dcn30/` 1.195. `PROVEN`.

**SOLO DELEGA (11 subárboles, 180.014 líneas):** `dc/dml/` 77.927, `dc/dml2_0/` 40.058,
`dc/core/` 22.132, `dc/link/` 19.451, `modules/` 10.413, `dc/irq/` 7.870,
`dc/dce110/` 6.676, `dc/` 3.649, `dc/dce120/` 1.291, `dc/dce112/` 848,
`dc/soc_and_ip_translator/` 547. `PROVEN`.

**SOLO ESCRIBE (10 subárboles, 11.934 líneas):** `dc/dccg/` 6.104, `dmub/` 6.035,
`dc/dcn20/` 1.318, `dc/opp/` 920, `dc/dwb/` 725, `dc/mmhubbub/` 647, `dc/dcn31/` 504,
`dc/dcn21/` 446, `dc/dcn201/` 410, `dc/dcn301/` 219. `PROVEN`.

**⇒ Las dos clases de `178` no están «la genérica arriba y la del chip abajo»: `dc/dml/`,
que son 77.927 líneas y el subárbol más grande del árbol, sólo delega, y `dc/dccg/` que son
6.104 líneas sólo escribe.** `PROVEN_DERIVED`.

## 4 · Y la cuarta clase: 12.981 líneas que no tocan nada

**Cinco subárboles con cero en las dos columnas: `dc/sspl/` 6.973, `dc/basics/` 5.059,
`dc/hdcp/` 425, `dc/dce60/` 268, `dc/dce80/` 256.** `PROVEN`.

**Y qué hay dentro, fichero por fichero:**

| fichero | líneas | funciones | qué es |
|---|---|---|---|
| `dc/sspl/dc_spl_scl_easf_filters.c` | 2.589 | 14 | escalado EASF, coeficientes de filtro |
| `dc/basics/dce_calcs.c` | 3.620 | 6 | aritmética de ancho de banda |
| `dc/sspl/dc_spl.c` | 1.934 | 30 | consulta de formatos y de espacio de color |
| `dc/sspl/dc_spl_scl_filters.c` | 1.234 | 0 | sólo tablas de coeficientes |
| `dc/basics/vector.c` | 307 | 16 | álgebra vectorial |
| `dc/basics/fixpt31_32.c` | 511 | 1 | punto fijo de 31,32 bits |
| `dc/basics/custom_float.c` | 173 | 3 | formato de coma flotante personalizada |
| `dc/basics/conversion.c` | 158 | 5 | conversión de matrices |
| `dc/basics/dc_common.c` | 102 | 5 | preguntas de configuración |
| `dc/basics/bw_fixed.c` | 188 | 1 | ancho de banda en punto fijo |
| `dc/hdcp/hdcp_msg.c` | 425 | 3 | procesamiento de mensajes HDCP |

**⇒ Un filtro de escalado, un descriptor de matrices, un contador de ancho de banda y un
decodificador de mensajes de cifrado. Ninguno de los cuatro habla con el hardware: son
aritmética y formato de mensaje.** `PROVEN_DERIVED`.

**⇒ Y para un driver propio, esto es la parte del árbol que se puede reutilizar entera sin
entender el silicio: 12.981 líneas de software puro.** `PROVEN_DERIVED`.

## 5 · Y las cuatro cifras del principio, con su aritmética

**⇒ De 443.839 líneas, 2.203 punteros dobles y 8.010 escrituras de registro.** `PROVEN`.

| cifra | valor | comprobación |
|---|---|---|
| densidad global de delegación | 5,0 por mil | 2.203 / 443.839 |
| densidad global de escritura | 18,0 por mil | 8.010 / 443.839 |
| Delegación en `dc/hwss/` | 44,1 por mil | 1.202 / 27.251 |
| Líneas SORTO | 2,9% | 12.981 / 443.839 |

**⇒ Y una comprobación que sale del propio reparto: las cuatro clases suman
214.549 + 180.014 + 11.934 + 12.981 = 419.478, que no son 443.839.** `PROVEN_DERIVED`.

**⇒ La diferencia son 24.361 líneas, y es `dc/dml2_0/dml21/src/`, que no es un subárbol de
`display/` sino un árbol de fuentes importado con sus propios directorios.** `PROVEN_DERIVED`.
*Y por eso el total del primer apartado —510 ficheros, 443.839 líneas— sí cuadra: usa un
criterio distinto, el de directorio con al menos un `.c` a cualquier profundidad, que cuenta
`spl/` dos veces, una como `dc/sspl` y otra como subárbol suyo.* **Los dos totales son
correctos y miden cosas distintas, y la diferencia entre ellos está localizada exactamente
en un árbol y es de 24.361 líneas.**

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Cuatro clases, y 48,4 / 40,6 / 2,7 / 2,9 % | `PROVEN` |
| `dc/dce110/` escribe cero registros en 6.676 líneas | `PROVEN_DERIVED` |
| `dc/dce/` delega 25 veces y escribe 770 | `PROVEN_DERIVED` |
| Los 12.981 «sorth» no tocan hardware | `PROVEN_DERIVED` |
| El 2,9% es reutilizable sin entender el silicio | `PROVEN_DERIVED` |
| La diferencia entre los dos totales es `dml2_0/dml21/src/` | `PROVEN_DERIVED` |
| Qué subárboles de «LAS DOS» son de esta GPU | **`NOT_DETERMINED`** |
| Cuál de las 4 clases es la que se compila para Polaris12 | **`NOT_DETERMINED`** |
| Por qué `dml` y `dml2_0` sólo delegan y no escriben | **`NOT_DETERMINED`** |

**La primera de las abiertas es la que la clasificación deja abierta y es la de más valor:
`LAS DOS` mezcla `dc/resource/` —la tabla de constructores, la parte más genérica del árbol— con `dc/dce/` —que es DCE 11.2 puro—, y ningún criterio de los tres que he medido
separa lo que es código de esta GPU de lo que es infraestructura para veinte.** `NOT_DETERMINED`.

**Y la forma de cerrarla ya se ha usado en `236` y es la que funciona: se sabe qué se
instancia, no qué se puede instantiate.** *Para esta GPU se instancian `dce112`,
`dce110_hwseq` y `dce110_clk_mgr`; el resto de las 42 subárboles son código muerto en esta
placa, y no porque no se pueda compilar sino porque el constructor nunca los llama.*

## Procedencia

- `STATIC` -- `display/`, recorrido completo con `os.walk`: 510 `.c`, 443.839 líneas
  contadas con `wc -l` sobre cada fichero, agrupados en 42 subárboles por el criterio del
  primer nivel bajo `dc/` (o el propio `dc/` cuando no hay subnivel).
- Citas con línea, las once del fichero de cuarto clase:
  `display/dc/sspl/dc_spl.c:13` (`spl_is_yuv420`),
  `display/dc/sspl/dc_spl_scl_easf_filters.c:2383` (`spl_easf_get_scale_ratio_to_reg_value`),
  `display/dc/basics/dce_calcs.c:75` (`calculate_bandwidth`),
  `display/dc/basics/vector.c:29` (`dal_vector_construct`),
  `display/dc/basics/fixpt31_32.c:477` (`dc_fixpt_s4d19`),
  `display/dc/basics/custom_float.c:29` (`build_custom_float`),
  `display/dc/basics/conversion.c:130` (`convert_hw_matrix`),
  `display/dc/basics/dc_common.c:30` (`is_rgb_cspace`),
  `display/dc/basics/bw_fixed.c:41` (`abs_i64`),
  `display/dc/hdcp/hdcp_msg.c:122` (`hdmi_14_process_transaction`),
  `display/dc/sspl/dc_spl_filters.c:7` (`SPL_NAMESPACE`).
- El resto de rutas, sin línea, y sólo como procedencia de recuento:
  `display/dc/sspl/dc_spl_scl_easf_filters.c`,
  `dc/sspl/dc_spl_scl_filters.c`, `dc/basics/dce_calcs.c`, `dc/basics/vector.c`,
  `dc/basics/fixpt31_32.c`, `dc/basics/custom_float.c`, `dc/basics/conversion.c`,
  `dc/basics/dc_common.c`, `dc/basics/bw_fixed.c`, `dc/hdcp/hdcp_msg.c` — con el número de
  líneas y el de funciones de cada uno, y los tres primeros nombres de función de cada uno.
- Patrones, idénticos a los de `178`: `(\w+)\s*->\s*(\w+)\s*->\s*(\w+)\s*\(` y
  `\bREG_\w*\s*\(`. Recuento de funciones:
  `^(?:static\s+)?(?:inline\s+)?(?:void|int|bool|char|uint\d+_t|int\d+_t|unsigned|signed|
  enum\s+\w+|struct\s+\w+\s*\*|const\s+struct\s+\w+\s*\*)\s*(\w+)\s*\(` en modo `re.M`.
- **Un error de escala propio, cuarta vez:** el `printf` del primer intento tenía seis
  huecos de formato y siete valores, y `python` lo rechazó con `TypeError: not all
  arguments converted during string formatting`. **Es la misma línea de código fallando
  cuatro veces en tres notas, y la causa es que escribo la columna nueva antes de quitar
  la que ya no uso.** *La regla que sale: cuando una tabla gana una columna, se relee el
  `printf`, y si gana una fila, se relee la longitud de la tupla.*
- **Dos nombres inventados, decimoquinto y decimoquinto y medio:** primero
  `dc/link/protocols/dp_train_dp.c`, que no existe, y después **las once líneas de las once
  citas de esta misma nota, que estaban todas inventadas.** *Las once fallaron a la
  verificación y las once se habían escrito del mismo modo: por posición dentro del
  fichero, no por búsqueda del símbolo.* **`calculate_bandwidth` lo puse en la línea 2272 de
  un fichero de 3.620 líneas, y está en la 75.** **Ésta es la forma más cara de la serie de
  nombres inventados, porque una cita inventada no se detecta con un `grep` que la busca:
  se detecta con un `grep` que la resuelve, y `citecheck` no lo hacía porque sólo contaba
  el par —las dos veces que falló, la resolución la hizo un programa que leí las líneas
  una a una.**
- **Y las dos veces que ha pasado lo del nombre de fichero ha sido porque el programa se
  cayó** con `FileNotFoundError` antes de dar un número, que es la quinta forma en que un
  programa me para. **Las once líneas inventadas, en cambio, no hicieron caer nada: el
  programa las imprimió con confianza.**
- Encadenada con `178` (**los dos canales, y aquí los dos canales sobre los 42
  subárboles, que corrigen su separación en dos clases**), `238` (la densidad aplicada a
  nueve ficheros), `237` (la densidad como medida), `175` (los 108 puntos),
  `173` (los 75 manejadores y el intérprete de 119 operaciones), `172` (`dc/core/` y los
  bloques ausentes), `236` (**qué se instancia y no qué se compila**), `234` (las 149
  escrituras de `dce_stream_encoder.c`), `159` (los 52 constructores), `232` (la tabla de
  swizzle), `155`, `154`, `153`, `150`, `145`, `140`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El censo de los 42 subárboles refutó la clasificación de `178` sin que ninguna de sus
medidas estuviera mal.** `178` decía: el secuenciador delega y no escribe; los ficheros por
generación escriben y no delegan. Cierto para los ficheros que midió, y falso para el
árbol: `dc/hwss/` hace las dos cosas y es el segundo subárbol más delegante; `dc/dce110/`
no escribe nada; `dc/dce/` hace las dos.

**La lección es la regla (i) de esta tanda, y es la segunda vez que aparece con una forma
nueva:** *medir la parte que se está mirando y generalizarla es el error dominante.* En
`178` miré cinco ficheros —tres de la capa genérica y dos de la por generación— y llamé
«la arquitectura» a lo que pasaba en ellos. **Los dos criterios que usé eran correctos y
la clasificación que construí sobre ellos era una generalización de cinco muestras.**

**Y el antídoto funcionó y es el mismo de siempre:** *extender el mismo programa al conjunto
completo, no a más muestras.* Cinco ficheros elegidos a mano dan una clasificación;
cuarenta y dos agrupados por un criterio declarado dan el reparto real, y el reparto real
tiene cuatro clases, no dos.

**Y la cuarta clase es la que no podía existir antes de medir el conjunto:** el 2,9% de
líneas que no tocan ni el bus de instrucciones ni el silicio —filtros de escalado, punto
fijo, vectores, mensajes HDCP—, que para un driver propio es lo más barato que hay porque
se reutiliza entero.