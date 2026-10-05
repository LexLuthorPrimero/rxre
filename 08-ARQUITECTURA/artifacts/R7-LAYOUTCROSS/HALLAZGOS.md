# R7 — LAYOUTCROSS: contraste cruzado de layouts PM4 declarados vs oráculos del corpus

Instrumento: `tools/layoutcross.py`
Fecha: 2026-10-04
Alcance: `08-ARQUITECTURA/tools/pm4_codec.py::DOC_LAYOUTS` (única herramienta
del proyecto que declara layouts por opcode), contrastado contra dos oráculos
**dentro del corpus**: los comentarios numerados `/* 1. header ... N. ... */` de
las cabeceras del kernel, y las emisiones `PACKET3(OPCODE, F)` de los `.c`.

Salida archivada: `salida.txt` (27 líneas, rc=1).

---

## 1. El hueco medido que justifica el instrumento

`pm4_codec.check_layouts()` recorre sus 7 layouts declarados y busca una
emisión `PACKET3(op, F)` **en `gfx_v8_0.c`**. Medido:

```
VERIFICADO   PACKET3_SET_RESOURCES     7 payload, F=6   coincide
VERIFICADO   PACKET3_MAP_QUEUES        6 payload, F=5   coincide
VERIFICADO   PACKET3_UNMAP_QUEUES      5 payload, F=4   coincide
SIN ORACULO  PACKET3_CP_DMA            6 payload, declarados
SIN ORACULO  PACKET3_DMA_DATA          6 payload, declarados
SIN ORACULO  PACKET3_QUERY_STATUS      6 payload, declarados
SIN ORACULO  PACKET3_RUN_CLEANER_SHADER 1 payload, declarados
```

**Verifica 3 de 7.** Los otros 4 tienen **0 apariciones** en `gfx_v8_0.c`, y la
comprobación hace `continue` sin emitir nada.

Eso es `NOT_FOUND → PROVEN_ABSENT`: **un layout nunca contrastado produce el
mismo silencio que un layout verificado correcto.** El lector no puede
distinguirlos.

`pm4_layout_audit.py` ya tenía el oráculo complementario (los comentarios
numerados) pero solo lo contrasta **kernel contra kernel**. Ninguna
herramienta contrastaba el lado de las herramientas.

Cobertura medida de este instrumento: **7 de 7 contra cabeceras, 4 de 7
contra emisión.** Sin el oráculo de cabeceras, 3 de 7 seguirían mudos.

---

## 2. Defecto encontrado: `PACKET3_CP_DMA` displaced en un dword

`pm4_codec.DOC_LAYOUTS["PACKET3_CP_DMA"]` declara **6** entradas. El kernel
documenta **5 de payload**.

Fuente primaria, `sid.h:417-423`:

```c
#define	PACKET3_CP_DMA					0x41
/* 1. header
 * 2. SRC_ADDR_LO or DATA [31:0]
 * 3. CP_SYNC [31] | SRC_SEL [30:29] | ENGINE [27] | DST_SEL [21:20] |
 *    SRC_ADDR_HI [7:0]
 * 4. DST_ADDR_LO [31:0]
 * 5. DST_ADDR_HI [7:0]
 * 6. COMMAND [30:21] | BYTE_COUNT [20:0]
 */
```

= cabecera + 5 payload.

Lo declarado por la herramienta:

```
1. CONTROL                                                  <-- LA CABECERA
2. SRC_ADDR_LO | DATA
3. CP_SYNC[31] | SRC_SEL[30:29] | ENGINE[27] | DST_SEL[21:20] | SRC_ADDR_HI[7:0]
4. DST_ADDR_LO[31:0]
5. DST_ADDR_HI[7:0]
6. COMMAND[30:21] | BYTE_COUNT[20:0]
```

**Es el único layout de los 7 que cuenta la cabecera.** Los otros seis no la
cuentan. Consecuencia: al decodificar, `DW0` se etiqueta `CONTROL` cuando en
realidad es `SRC_ADDR_LO`, y **todos los nombres siguientes quedan desplazados
una posición**.

El framing no se rompe: el paquete se consume bien. Por eso nada más lo
delata. Es exactamente el modo de fallo que el propio `pm4_codec` describe en
su docstring, y el paquete afectado es precisamente aquel sobre el que
`tools/pm4decode.c` ya tiene un defecto de nomenclatura registrado (`0x41`
nombrado `PREAMBLE_*` cuando vale `CP_DMA`).

**No se ha modificado `pm4_codec.py`.** Se reporta.

---

## 3. Falsos positivos que el instrumento mate (3 de 7)

Primera ejecución: `QUERY_STATUS`, `UNMAP_QUEUES` y `RUN_CLEANER_SHADER`
salieron `DISCREPA` con "coincidencia 0%". **Eran falsos positivos míos.**

| paquete | kernel documenta | herramienta declara | cuentas |
|---|---|---|---|
| `QUERY_STATUS` | `CONTROL \| CONTROL2 \| ADDR_LO \| ADDR_HI \| DATA_LO \| DATA_HI` | `cadence \| CONTEXT_STATUS \| VMID \| REGISTER_INDEX \| STATUS_VALUE \| dword[4] \| dword[5]` | 6 = 6 |
| `UNMAP_QUEUES` | `CONTROL \| CONTROL2 \| CONTROL3 \| CONTROL4 \| CONTROL5` | `ACTION \| QUEUE_SEL \| ENGINE_SEL \| NUM_QUEUES \| DOORBELL_OFFSET0 \| dword[2..4]` | 5 = 5 |
| `RUN_CLEANER_SHADER` | `RESERVED [31:0]` | `CLEANER_MODE / type` | 1 = 1 |

Las cuentas coinciden en las tres. Lo que difiere es **granularidad del
nombre**: el kernel nombra ranuras genéricas o directamente `RESERVED`, y la
herramienta nombra la interpretación semántica del mismo dword.

Ausencia de nombre comparable **no** es evidencia de defecto. Es el mismo
error que `NOT_FOUND → PROVEN_ABSENT`, en otra forma: aquí
`sin_nombre → DISCREPA`.

Corrección aplicada: un cuarto veredicto, `NOMBRES_NO_COMPARABLES`, que se
separa de `DISCREPA` y de `OK`. Con él, el recuento real es:

```
OK 3   DISCREPA 1   SIN_ORACULO 0   NOMBRES_NO_COMPARABLES 3
```

Vector de regresión en el selftest: `PACKET3_GEN` con kernel
`CONTROL|CONTROL2|CONTROL3` frente a una herramienta que desglosa los bits
debe dar `NOMBRES_NO_COMPARABLES`, nunca `DISCREPA`.

---

## 4. La clase de bug que más me costó: unidades

Cuatro veces en esta sesión comparé **payload contra total** y obtuve un
falso positivo cada vez. La aritmética era correcta; el nombre de las dos
cantidades era el mismo ("dwords") y nadie decía cuál era cuál.

El project's own tools reproducen la ambigüedad:

- `pm4_codec.py:93-95` — *"el de soc15d.h (GFX9+) tiene 7 dwords y este
  tiene 6"*. **Falso**: `vid.h:385-392` y `soc15d.h:485-492` documentan
  layouts **idénticos de 7 entradas**. El autor cuenta *payload* para `vid.h`
  y *total con cabecera* para `soc15d.h`, dentro de la misma frase. La
  conclusión (6 payload) acierta; la justificación está mal, y por eso el
  número nunca delató el error.
- `pm4_codec.py:254-255` — repite la misma premisa en `check_layouts()`.
- `pm4_layout_audit.documented_layouts()` **devuelve payload** (`max(nums) - 1`)
  pero su docstring habla de *"el último número es el total de dwords"*. Un
  lector razonable lee mal, y yo leí mal.

**El código de `pm4_codec.check_layouts()` sí es correcto**: usa
`esperado = F + 1` y no cuenta `ring_write`, es decir, razona en payload.

Por eso `layoutcross.py` no hereda la ambigüedad: **ninguna cuenta sale sin
unidad.** El bloque `UNIDADES:` de la salida declara que `herr`, `cab` y `emi`
son `SOLO_PAYLOAD` y que `total` es `TOTAL(cabecera+payload)` con
`total = cab + 1`.

### Regla numérica fijada, con tres anclas independientes en el corpus

| paquete | F | payload emitido | dwords totales |
|---|---|---|---|
| `EVENT_WRITE` | 0 | 1 | 2 |
| `EVENT_WRITE_EOP` | 4 | 5 | 6 |
| `RELEASE_MEM` | 5 | 6 | 7 |
| `MAP_QUEUES` | 5 | 6 | 7 |

**payload = F + 1**, y es idéntico en `gfx_v8_0.c`, `gfx_v9_0.c`,
`gfx_v9_4_3.c`, `gfx_v10_0.c`, `gfx_v11_0.c` y `gfx_v12_1.c`.

---

## 5. Resultados negativos con número

- **`max_depth=3` de `pm4_emit.resolve_includes` no es un problema**: cuesta
  **1 solo fichero** (108 vs 109). Sus 3 rutas de búsqueda fijas pierden 32
  ficheros, todos del Display Manager y el DAL (`amdgpu_dpm.h`, `dc_types.h`,
  `dal_types.h`), y **ningún header de opcodes**. Resolución adecuada para su
  propósito. Frontera cerrada.
- **Los 7 layouts son invariantes entre generaciones**: `F` es idéntico en las
  6 generaciones que los emiten. La afirmación de alcance GFX9+ de
  `pm4_codec` se sostiene para 6 de 7; `CP_DMA` no se emite en el corpus.
- `PACKET3_RUN_CLEANER_SHADER_9_0` está documentado por el kernel y
  `pm4_codec` no lo declara: hueco de cobertura en sentido inverso, sin
  oráculo de emisión (0 apariciones).

---

## 6. Errores propios corregidos en esta construcción

1. `_tokens` exigía mayúsculas; el kernel escribe `WPTR_ADDR_HI` y
   `pm4_codec` escribe `doorbell_offset` para el mismo campo. Habría
   declarado discrepante lo que es el mismo nombre. Ahora se ignoran mayúsculas.
2. El filtro de líneas de continuación rechazaba las que empiezan por `*`,
   que es **exactamente** como el kernel las escribe. La entrada 3 perdía
   `SRC_ADDR_HI`.
3. `range(i-1, max(0, i-10), -1)` queda **vacío** si el comentario está en las
   primeras líneas: el `#define` de la línea anterior nunca se miraba y el
   opcode salía `None`, perdiendo el header entero en silencio. Corregido a
   `max(-1, ...)`. **La misma expresión con `-8` existe en
   `pm4_layout_audit.py`**; en el corpus no muerde porque ningún
   `/* 1. header` está entre las líneas 0 y 7, pero es la misma clase latente.
4. Alineaba por contenido y **aceptaba** el resultado como OK, lo que habría
   normalizado el defecto de `CP_DMA` en lugar de marcarlo. El veredicto
   compara longitudes crudas; la alineación solo dice *dónde* sobran.
5. El diagnóstico restaba el índice de alineación dos veces y llegaba a decir
   `"sobran 0"` **justo en el caso que motiva el instrumento**.
6. `contrastar` esperaba tablas planas y el selftest pasaba dicts anidados
   (`TypeError`). Además, sin `break`, la última tabla pisaba a la primera.
7. Fixture con `\t` literal en vez de tabulador: el `\s+` de la regex no lo
   veía y el oráculo de cabecera devolvía vacío.

---

## 7. Puerta de deriva: `verif` ampliado de 18 a 23 medidas

Cinco medidas nuevas, porque un hallazgo que no tiene puerta puede evaporarse
sin que nadie lo note:

| medida | clase | qué mide |
|---|---|---|
| `layout.declarantes` | `ESTABLE` | quién declara layouts (se descubre, no se codifica) |
| `layout.declaraciones` | `ESTABLE` | cuántos layouts se declaran en total |
| `layout.discrepancias` | `CONOCIDA` | cuentas de payload que no cuadran |
| `layout.nombres_no_comparables` | `CONOCIDA` | cuenta correcta sin nombre contrastable |
| `layout.sin_oraculo` | `VACIA` | declaraciones sin ningún oráculo (debe ser 0) |

`discrepancias` y `nombres_no_comparables` son `CONOCIDA`, no `DRIFTABLE`: son
defectos registrados y Mouth-closing sobre ellos cada ejecución sería ruido que
enseña a ignorar la puerta. La clase `CONOCIDA` hace que solo seaNotable si
**crece** o **se corrige**.

### Verificación previa a congelar

No se congeló a ciegas. Primero se ejecutó `verif` con las 5 medidas nuevas sin
congelar: **las 18 medidas existentes dieron cero deriva**. Solo las 5 nuevas
aparecieron como `SIN_BASE`. Congelar en ese estado no oculta nada.

### Puerta probada, no solo escrita

Se perturbó la línea base y se comprobó que las 4 medidas con contenido
disparan con su clasificación:

```
layout.sin_oraculo        VACIA     antes: 2  ahora: 0
layout.discrepancias      CONOCIDA  APARECEN (1): PACKET3_CP_DMA
layout.declarantes        ESTABLE   DESAPARECEN (1): pm4_extra.py
layout.declaraciones      ESTABLE   antes: 9  ahora: 7
```

`CONOCIDA` muestra **apariciones y desapariciones**, así que si alguien
corrige `CP_DMA` la puerta lo registra como corrección, no como ruido.

### Detalle de contrato que hubo que respetar

`layoutcross.py --json` sale con **rc=0 aunque haya discrepancias**. El rc=1 de
su modo legible significa "hay discrepancia", y una discrepancia registrada no
es un fallo del instrumento. Si `--json` devolviera 1, `verif.ejecutar()` lo
leería como error de ejecución y la medida passaría a `NO_SE_MIDE`: **una puerta
que se apaga sola cuando el sensor dice algo incómodo**.

## 8. Reproducción

```
python3 tools/layoutcross.py --selftest   # 20 vectores, rc=0, hermético
python3 tools/layoutcross.py               # rc=1 (hay DISCREPA)
python3 tools/layoutcross.py --json        # rc=0, datos estructurados
python3 tools/verif.py --selftest          # rc=0, 23 medidas
python3 tools/verif.py                     # rc=0, sin deriva
```

Hermeticidad verificada: copia aislada de los instrumentos en
`/tmp/opencode/herm6`, ejecución desde ese directorio sin acceso al corpus,
20 vectores verdes.

Códigos de salida de `layoutcross` en modo legible: `0` toda declaración con
oráculo y coincidente · `1` hay `DISCREPA` · `2` ninguna tiene oráculo.

No se ha modificado ningún fichero de otro agente. `pm4_codec.py` y
`pm4_layout_audit.py` quedan intactos; el defecto de `CP_DMA` se reporta.

---

# 9 · Ampliación posterior: TRES oráculos, no uno

El instrumento tenía una tabla. Ahora tiene **tres**, y cada una responde a una
pregunta que las otras dos no pueden responder. La razón de que sean tres no es
estética: es que **contar, situar y cubrir fallan de forma independiente**.

| tabla | pregunta | qué NO puede ver |
|---|---|---|
| CONTEO | ¿cuántos dwords? | qué dword es cuál, qué falta |
| ASIGNACIÓN | ¿qué bits ocupa lo que se declara? | lo que **no** se declara |
| COBERTURA | ¿qué escribe el kernel que no se declara? | campos escritos solo bajo condición |

Hallazgos que produjo cada una, sobre el mismo fichero:

```
CONTEO      1061  CP_DMA declara 6, el kernel documenta 5
ASIGNACIÓN  1073  SET_RESOURCES: queue_type[15:14] vs <<29; RESOURCE_SIZE no existe
            1077  UNMAP_QUEUES: 4 contradicciones que NO se pueden resolver
COBERTURA   1082  MAP_QUEUES CONTROL2: queue, pipe y me escritos y no rotulados
```

## 10 · La clase de defecto que ninguna de las dos primeras puede ver

`1082` es el hallazgo que justifica la tercera tabla, y la lección es general:

> **Las tablas de conteo y de asignación solo hablan de lo que la herramienta
> afirma. Un campo que falta no produce una fila en ninguna de las dos, porque no
> hay nada que comparar.**

Cinco verificadores pasan un layout al que le faltan tres campos:

```
pm4_codec.check_layouts()   len == F+1              -> 6 == 6   no ve nada
pm4_layout_audit.py         F vs payload documentado -> 5 == 5   no ve nada
layoutcross CONTEO          entradas vs payload      -> 6 == 6   no ve nada
layoutcross ASIGNACION      posicion de lo declarado -> bien     no ve nada
layoutcross COBERTURA       que escribe y falta      -> 3 campos
```

`map_queues.CONTROL2` tiene **cinco** campos documentados en `vid.h` y la
herramienta declara **uno**.

## 11 · Alcance de la tabla de COBERTURA, y por qué está acotado

Sin filtro, la tabla producía **17 filas y ninguna defendible**: acusaba a
`MAP_QUEUES` de omitir `VMID` y `ALLOC_FORMAT` usando emisiones de GFX10 y GFX11.
Comparar la emisión de una generación con el layout declarado de otra es un
**error de categoría**, no un defecto.

Por defecto solo juzga `gfx_v8_0.c`, y **los ficheros excluidos se cuentan y se
nombran**:

```
ALCANCE: solo emisiones de gfx_v8_0.c
Emisiones de otras generaciones EXCLUIDAS y no juzgadas: 10
  amdgpu_amdkfd_gfx_v10.c, amdgpu_amdkfd_gfx_v10_3.c, amdgpu_amdkfd_gfx_v11.c,
  amdgpu_amdkfd_gfx_v9.c, gfx_v10_0.c, gfx_v11_0.c, gfx_v12_0.c,
  gfx_v12_1.c, gfx_v9_0.c, gfx_v9_4_3.c
```

Excluir en silencio sería el mismo fallo que deny-default que este instrumento
existe para cazar.

## 12 · Errores propios que esta ampliación costó

1. **Fusionó generaciones** en un mapa por ordinal, sin fichero. Todas las
   emisiones de un opcode se sumaban.
2. **El filtro de generación se escribía con un `None`.** Con `--generacion`
   sin valor, `args.generacion is None` tomaba la rama de "generación
   personalizada" y filtraba por `[None]`, que no casa con ningún fichero: la
   tabla salía **vacía** y decía *"ningún campo escrito por el kernel queda sin
   declarar"*. **Un filtro mal escrito se disfraza de resultado limpio**, que es
   la forma más peligrosa de fallo en un instrumento de ausencias. Se detectó
   porque **contra_decía lo verificado a mano**; sin esa verificación manual se
   habría publicado un instrumento que dice que no pasa nada.
3. **Confundió `_tokens` con `_nombres`.** `ACTION` y `ME` no tienen guion bajo y
   salían como no declarados cuando sí lo estaban.
4. **`condicional` declarado como `set` y usado como `dict`**, y sin usar. Se
   sustituyó por una limitación de alcance escrita: no se modela el flujo de
   control, así que la tabla **notifica de más**, que es el sentido seguro.

La clase 2 es la que más me importa: **es el mismo `NOT_FOUND → PROVEN_ABSENT`
del proyecto, cometido por el instrumento que existe para detectarlo.**

## 13 · Estado verificado

```
selftest     48 vectores, rc=0
hermeticidad /tmp/opencode/herm6, sin corpus, 48 vectores, rc=0
corpus       96 líneas de salida, rc=1
             CONTEO:       OK 3   DISCREPA 1   SIN_ORACULO 0
                          NOMBRES_NO_COMPARABLES 3
             ASIGNACION:   OK 27  CONTRADICCION 6  CAMPO_INVENTADO 1
                          NOMBRES_NO_COMPARABLES 8  SIN_ORACULO_BITS 1   (de 43)
             COBERTURA:    3 campos escritos y no declarados
puerta       tools/verif.py, 29 medidas, SIN DERIVA, rc=0
             antes de congelar cada bloque, las medidas previas dieron cero deriva
             puerta probada por perturbacion tres veces (18->23->27->29)
```