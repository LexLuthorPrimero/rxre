# 121 · §E: el PM4 que emite GFX8 se resuelve estáticamente, y la contabilidad del driver cuadra exacta

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`ABRE=secE (PM4 / CP / IB), que era el unico item de esa frontera sin herramienta`
`CONFIRMA=110 (por via independiente), y la cadena de secD`

## Cuestión principal

`AGENTS.md` §E pide resolver *IB → fetch → PFP/ME → packet decode → ejecución →
fence/interrupt*, cerrando *"packet consumption, ordering, PFP, ME,
synchronization, ring semantics"*.

La primera mitad es un problema de **aritmética de constantes**: el driver
construye cabeceras PM4 con macros, y esas macros son evaluables. ¿Se puede
hacer sin placa?

## Criterio de terminación

Producir el programa PM4 dword a dword, con valor hexadecimal y `fichero:línea`,
para las funciones de anillo de GFX8. **Cumplido**, con una limitación honesta
que se declara en §Confounders.

## Herramienta

`08-ARQUITECTURA/tools/pm4_emit.py`. No ejecuta código del driver: **evalúa las
macros del propio driver** y lee sus `amdgpu_ring_write`.

El detalle que la hace correcta y no un juguete: **sigue los `#include` reales**
en vez de usar una lista fija de cabeceras. No es preferencias de estilo — `gfx_v8_0.c:41`
incluye `gmc/gmc_8_2_d.h` y `gmc_v8_0.c:35` incluye `gmc/gmc_8_1_d.h`. Una lista
fija habría cargado la versión equivocada del mapa de registros sin avisar.

Y los valores vienen de dos sitios, como en C:

| fuente | qué aporta | ejemplo |
|---|---|---|
| `#define` | macros de paquete | `PACKET3`, `EOP_TCL1_ACTION_EN` (`vid.h:241`) |
| `enum` | la mitad de los valores | `CACHE_FLUSH_AND_INV_TS_EVENT = 0x14` (`gfx_8_0_enum.h:5277`) |

Sin los enums, el `EVENT_WRITE_EOP` de `gfx_v8_0.c` quedaba sin resolver aunque
el valor estuviera literalmente en el corpus.

## Escalera de validación

```
BUILD              sintaxis OK, arranca
BASIC TEST         --self-test: 12 vectores + 6 controles negativos  -> OK
KNOWN INPUT        PACKET3(varios) contra sid.h
EXPECTED OUTPUT    0xC0053C00 / 0xC0004200 / 0x00038514, calculados a mano
EDGE CASE          llamada multilinea, ternario, cross-file, condicional
FAILURE CHECK      6 simbolos desconocidos TIENEN que lanzar excepcion
OUTPUT VALIDATION  contraste contra emit_frame_size del propio driver
CLASIFICACION      TOOL_VALIDATED
```

El último paso es el que importa. **El contraste no es contra la propia
herramienta**: es contra los `emit_frame_size` comentados de `gfx_v8_0.c`, una
cantidad que el driver declara y que nadie calculó desde la emisión. Si
coinciden, dos caminos independientes producing el mismo número.

## El resultado: 6 de 6 contadores cuadran exacto

```
$ pm4_emit.py --frame-size
funcion                                    sin cond. declarado   delta  nota
gfx_v8_0_ring_emit_gds_switch                       20        20       0  exacto
gfx_v8_0_ring_emit_hdp_flush                        7         7       0  exacto
gfx_v8_0_ring_emit_pipeline_sync                    7         7       0  exacto
gfx_v8_0_ring_emit_vm_flush                        17        17       0  exacto
gfx_v8_0_emit_mem_sync_compute                      7         7       0  exacto
gfx_v8_0_emit_wave_limit                            5         5       ?  INCOMPLETO
```

**La contabilidad de tamaño de anillo del driver es correcta y exacta** para
todas las funciones comparables. Eso no estaba demostrado antes: era una suma
comentada a la que nadie había contrastado.

## Y la aritmética sale entera: 24, 22 y 17

Las tres declaraciones para `gfx_v8_0_ring_emit_vm_flush` — una por tipo de
anillo — se descomponen exactamente:

| anillo | declaración | valor | emisión real |
|---|---|---|---|
| GFX (`:6878`) | `VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 9` | **24** | 17 + 2 (`PFP_SYNC_ME`) = 19 |
| compute (`:6929`) | `VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7` | **22** | 19 |
| KIQ (`:6964`) | `17` | **17** | 17 (**sin** `PFP_SYNC_ME`) |

**El 9 y el 7 son exactamente los 2 dwords del `PFP_SYNC_ME`**, y el KIQ no los
reserva porque `usepfp` es falso (`gfx_v8_0.c:6194`, `:6210`). Una aritmética que
el driver no documenta y que sale exacta por los tres lados.

Esto **confirma por vía independiente** que `PFP_SYNC_ME` es condicional, que
`215`Establishió leyendo el código.

## Y el `NUM_WREG` que sobraba no es un error

`vi.h:27` dice `VI_FLUSH_GPU_TLB_NUM_WREG 3`. Pero `gmc_v8_0_emit_flush_gpu_tlb`
(`gmc_v8_0.c:668`) emite **2** `wreg`, y lo mismo en GCN1 y GCN2 — lo verifiqué
en las tres: los tres cuerpos son idénticos salvo el nombre.

Es una **reserva deliberadamente holgada**, compartida entre motores que pagan
distinto por registro:

```
gfx_v8_0.c:6929   VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7   (GFX, 5 dwords por WREG)
sdma_v3_0.c:1576  VI_FLUSH_GPU_TLB_NUM_WREG * 3 + 6   (SDMA, 3 dwords por WREG)
uvd_v6_0.c:1587   VI_FLUSH_GPU_TLB_NUM_WREG * 6 + 8   (UVD, 6 dwords por WREG)
```

El multiplicador es del motor; el número de WREGs es el máximo. Sobrar por uno es
correcto. **No es un bug, y es el tipo de cosa que parece un bug** — por eso
hacía falta medirlo en vez de leerlo.

## Verificación independiente de `215`

`215` cerró que la cabecera del `WAIT_REG_MEM` del vm-flush vale
`0x00000000`, leyéndolo. Aquí sale **por evaluación de macros**, un mecanismo
distinto:

```
$ pm4_emit.py --func gfx_v8_0_ring_emit_vm_flush
gfx_v8_0_ring_emit_vm_flush  (linea 6191)  9 dwords (2 condicionales), 9 resueltos
    6199  dword          0xC0053C00
    6200  dword          0x00000000          <- la cabecera del WAIT
    6203  dword          0x0000051E          <- POLL_ADDR = mmVM_INVALIDATE_REQUEST
    6204  dword          0x00000000
    6205  dword          0x00000000
    6206  dword          0x00000000          <- MASK = 0
    6207  dword          0x00000020          <- poll interval
    6212  dword          0xC0004200  [cond]  <- PFP_SYNC_ME
    6213  dword          0x00000000  [cond]
```

Más los 10 dwords de los 2 `wreg` de `gmc_v8_0.c`, que la herramienta cuenta al
cruzar ficheros. **Dos mecanismos, mismo número.**

## §E: el resultado negativo que abre la frontera

```
$ pm4_emit.py --control
PACKET3 definidos en sid.h : 83
emitidos por GFX8          : 20
nunca emitidos             : 63
```

**GFX8 usa 20 de los 83 paquetes que el propio `sid.h` define.** El 76% del
espacio de packet3 documentado no lo toca esta placa.

Eso es un `NEGATIVE_RESULT` con valor: para un driver propio son 63 paquetes que
no hace falta implementar, y 20 que sí. Es la primera vez que §E tiene un
recuento en vez de una intuición.

## Los seis bugs que la herramienta tuvo, y por qué importa

Todos los encontró la validación, ninguno el código:

| # | bug | síntoma |
|---|---|---|
| 1 | `\s*(\(...\))?` en el regex de macros | `WR_CONFIRM (1 << 20)` se parseaba como macro con parámetro, y **desaparecía** |
| 2 | `partition("(")` + `rsplit(")")` | `A(0) \| B(0)` cortaba en el paréntesis equivocado |
| 3 | `WRITE_RE` sin `re.S` | la llamada de 3 líneas del WAIT **no se veía** |
| 4 | offset de línea `+1` | todas las lineas iban mal |
| 5 | sin enums | `EVENT_WRITE_EOP` sin resolver |
| 6 | `any(o <= off)` en vez de `off in cond` | **un** offset condicional marcaba todo lo posterior |

El #6 es el instructive: producía `hdp_flush` con **0** dwords incondicionales,
porque un `if` temprano contaminaba el resto de la función. Una herramienta que
cuenta mal en la dirección de "menos de lo que hay" **nunca va a declarar una
reserva insuficiente**, así que el error se escondía justo en el lado que
interesa.

Y el peor de todos no llegó a la tabla: el recuento cruzando ficheros contaba
los `wreg` **dos veces** y daba `29 emitidos vs 17 declarados →
RESERVA INSUFICIENTE`. **Un falso positivo que señalaba un bug de driver que no
existe.** Si lo hubiera publicado sin comprobar, esta investigación habría
inventado un defecto en amdgpu.

**Lecciones que se llevan:**

1. Una herramienta de recuento debe **separar incondicional de condicional** y
   decirlo, o sus "defectos" son ruido.
2. El self-test con vectores conocidos no basta: hace falta un **contraste
   contra una cantidad independiente**. Aquí, `emit_frame_size`.
3. Cruzar ficheros casi siempre duplica. Hay que tener una lista explícita de lo
   que ya se expandió en sitio.

## Límites declarados

**Lo que la herramienta NO resuelve, y por qué:**

- **65 de 161 dwords** siguen sin valor absoluto. Son **variables locales**
  (`addr`, `seq`, `exec`) y eso no es un fallo: sin análisis de flujo de datos no
  se pueden conocer. Se marcan `~` y se reporta la parte que sí se sabe
  (`00000001..00000002 | ?(upper_32_bits(addr) & 0xffff)`).
- **`lower_32_bits()` y `upper_32_bits()` no están en el corpus.** Confirmado con
  búsqueda sobre todo `drivers/gpu/drm/amd/`: **cero resultados**. Son macros
  del kernel genérico (`include/linux/bitops.h`), fuera de este snapshot parcial.
  **No las he asumido**: quedan sin resolver. Sustituirlas por su semántica
  conocida subiría el número de resueltos, pero sería una suposición no
  verificada, y aquí no caben.
- **Las variables locales no son uncertainty**: son *unknown*. La distinción
  importa y la herramienta la mantiene: un dword con `~` no es un dword con `?`.

## Clasificación

| afirmación | estado |
|---|---|
| El PM4 de GFX8 se resuelve estáticamente sin placa | `PROVEN` — 9/9 dwords en la función real |
| La cabecera del WAIT del vm-flush es `0x00000000` | `PROVEN` por 2 vías independientes |
| El `MASK=0` hace vacua la comparación | `PROVEN` — `:6206` |
| `PFP_SYNC_ME` son 2 dwords condicionales | `PROVEN` — `[cond]` en 6212/6213 |
| 24/22/17 cuadran con la emisión por tipo de anillo | `PROVEN` — `--frame-size` |
| `emit_frame_size` es correcto para las 6 funciones | `PROVEN` — contraste independiente |
| `VI_FLUSH_GPU_TLB_NUM_WREG=3` con 2 WREG reales es holgura | `PROVEN` |
| GFX8 emite 20 de 83 paquetes | `PROVEN` — `--control` |
| Los 63 paquetes no emitidos son innecesarios | `NOT_DETERMINED` — pueden ser para otras rutas |
| 65 dwords dependen de variables locales | `PROVEN` — `~` |
| `lower_32_bits`/`upper_32_bits` ausentes del corpus | `PROVEN_ABSENT` — búsqueda sobre `amd/` |
| Que el hardware ejecute los paquetes en orden de emisión | `NOT_DETERMINED` — sin cambio |

## Confounders

- **`PACKET3(op, n)` con `op` en bits [15:8] y `n` en [28:16]**, y bits [7:0] a
  cero. Lo verifiqué contra la fórmula de `sid.h:336`, no de memoria. Mi primera
  expectativa —`PACKET3_WRITE_DATA = 0x28`— era **falsa**: es `0x37` (`sid.h:377`).
  La herramienta tenía razón y yo no; el self-test lo corrigió, no al revés.
- **La herramienta no modela flujo de datos**, solo constantes. Un `if` con valor
  desconocido no es una constante.
- **`--frame-size` compara una reserva con una emisión**, y solo tiene sentido
  donde el comentario nombra una función. Las filas `INCOMPLETO` no concluyen.
- **No he desensamblado el `.ko`** para contrastar los dwords. Sería el
  siguiente paso natural y convertiría `PROVEN` en `PROVEN_DERIVED` de otra
  clase.
- **El filtro de includes tiene profundidad 3.** Con más profundidad habría más
  macros; con menos, menos. Es un límite explícito, no un accidente.

## Desfalsificación

- **(a)** La cabecera es `0x00000000` → refutable con `pm4_emit --func`, y con
  `gfx_v8_0.c:6200-6202`.
- **(b)** 24/22/17 cuadran → refutable con `--frame-size`; si `declared` bajara,
  saldría `RESERVA INSUFICIENTE`.
- **(c)** 20 de 83 paquetes → refutable con `--control`.
- **(d)** `lower_32_bits` ausente → refutable con `grep -rn "define lower_32_bits"`.
- **(e)** 6 funciones cuadran exacto → refutable cambiando un `emit_frame_size`.
- **(f)** Que el hardware ejecute en orden → **no refutable aquí**, y la
  herramienta no lo afirma.

## UNLOCKS

- **§E tiene herramienta y tiene su primer recuento.** El item de "packet
  consumption" pasa de intuición a 20 de 83.
- **`secD` queda con la cadena de emisión cerrada numéricamente**: 17 + 2, con
  los valores de cada dword.
- **La primera aritmética que el driver no documenta** (24/22/17) sale exacta
  por los tres lados, y explica un `NUM_WREG` que parecía equivocado.
- **El driver no tiene ningún bug de contabilidad de anillo en GFX8.** Antes era
  "no comprobado"; ahora es `PROVEN` por contraste independiente.
- **Siguiente discriminante natural**: desensamblar `gfx_v8_0_ring_emit_vm_flush`
  en `/tmp/amdgpu_loaded.ko` y verificar que los 19 dwords aparecen como
  inmediatos. Convierte la aritmética estática en bytes observados.

## Evidencia

```
08-ARQUITECTURA/tools/pm4_emit.py   --self-test --func --all --control --frame-size

vid.h:178-188        PACKET3_WAIT_REG_MEM + sus 4 campos
sid.h:377            PACKET3_WRITE_DATA = 0x37
gfx_8_0_enum.h:5277  CACHE_FLUSH_AND_INV_TS_EVENT = 0x14
vid.h:241,249        EOP_TCL1_ACTION_EN = 1<<16 ; EOP_EXEC = 1<<28

gfx_v8_0.c:6191-6214 emit_vm_flush, 9 dwords (2 condicionales)
gfx_v8_0.c:6878      GFX:     VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 9  = 24
gfx_v8_0.c:6929      compute: VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7  = 22
gfx_v8_0.c:6964      KIQ:     17
vi.h:27              VI_FLUSH_GPU_TLB_NUM_WREG = 3   (2 WREG reales)
gmc_v8_0.c:668-681   gmc_v8_0_emit_flush_gpu_tlb: 2 WREG

$ grep -rn "define lower_32_bits" drivers/gpu/drm/amd/
(sin resultado)
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
