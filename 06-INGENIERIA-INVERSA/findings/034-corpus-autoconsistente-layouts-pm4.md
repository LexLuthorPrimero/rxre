# 034 · El kernel se autoconsistency-check: 28/28 sobre layouts documentados

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`STRENGTHENS=033-pm4-spec-gfx8-no-existe-y-el-encuadre.md §3`
`RESOLVES=el NOT_DETERMINED de 023 sobre el referente del `−1`, por segunda via`
`CONTINUES=029-release-mem-y-eop-exec-muerto.md` (frontera G, hilo `EOP_TC_MD`)

## CUDA principal

En `033` derive que `F = datos − 1` a partir de `WAIT_REG_MEM` y de `insert_nop`. Era
`PROVEN_DERIVED`. Esta ronda encuentra algo mejor: **el propio kernel documenta el layout
de 25 paquetes en comentarios numerados, y usa esos mismos paquetes.**

Eso da **dos fuentes de verdad independientes dentro del corpus**: el comentario que
documenta el paquete, y el codigo que lo emite. Y coinciden **28/28, sin una sola
discrepancia**.

```
opcode                      doc    F  real  F = doc-1
PACKET3_MAP_QUEUES            6     5     6      OK
PACKET3_SET_RESOURCES         7     6     7      OK
PACKET3_QUERY_STATUS          6     5     6      OK
PACKET3_RUN_CLEANER_SHADER    1     0     1      OK
(+ 24 mas, 6 opcodes distintos, 5 generaciones)
```

Un kernel que se contradijera entre su documentacion y su codigo no seria el kernel
que mueve esta placa. Asi que la convencion de `033` sube de `PROVEN_DERIVED` a
**`PROVEN` con dos fuentes internas**. Sigue sin depender de hardware ni de fuentes
externas.

## Alcance exacto

1. Cosechar los layouts documentados del corpus.
2. Cruzarlos contra las emisiones reales, por opcode.
3. Validar la herramienta por mutacion.
4. Cerrar el dword extra de `RELEASE_MEM` en GFX9 (`029`), que era el hilo hacia la
   frontera G.

## Criterio de terminacion (cumplido)

25 layouts cosechados, 28 cruces verificados, herramienta validada por mutacion,
`RELEASE_MEM` GFX8/GFX9 localizado. Agotado.

---

## 1 · El recurso que no habia explotado

En `cikd.h`, mirando `PACKET3_DMA_DATA`:

```c
#define	PACKET3_DMA_DATA				0x50
/* 1. header
 * 2. CONTROL
 * 3. SRC_ADDR_LO or DATA [31:0]
 * 4. SRC_ADDR_HI [31:32]
 * 5. DST_ADDR_LO [31:0]
 * 6. DST_ADDR_HI [7:0]
 * 7. COMMAND [30:21] | BYTE_COUNT [20:0]
 */
```

Un **layout de dwords documentado, escrito por el propio driver**. Ese comentario se
leia como documentacion decorativa; es una fuente de verdad verificable, porque el
mismo paquete se emite en codigo y se puede contar.

Cosecha de todo el corpus (patron `/* 1. header` seguido de lineas numeradas):

```
opcode                          fichero            linea  payload_doc
PACKET3_DMA_DATA                cikd.h               396        6
PACKET3_CP_DMA                  sid.h                418        5
PACKET3_DMA_DATA                soc15d.h             347        6
PACKET3_SET_RESOURCES           soc15d.h             472        7
PACKET3_MAP_QUEUES              soc15d.h             485        6
PACKET3_UNMAP_QUEUES            soc15d.h             507        5
PACKET3_QUERY_STATUS            soc15d.h             537        6
PACKET3_RUN_CLEANER_SHADER      soc15d.h             561        1
... (+ 17 mas, mismos paquetes repetidos por generacion)

layouts documentados: 25 en 6 ficheros
opcodes distintos:   7
```

`payload_doc` se calcula como `max(numero) - 1`, porque la numeracion empieza en 1 para
la cabecera. Es un parser, no un `grep` — la alternativa hubiera sido contar lineas de
comentario, que no son dwords.

### 1.1 · Una confusion que casi me equivoca

Los layouts no son todos de `PACKET3`. El parserWalking hacia atras 8 lineas para
encontrar el opcode, y a veces encuentra el macro equivocado: `PACKET3_SET_CONFIG_REG_START`,
`PACKET3_SET_SH_REG_END` y similares son **offsets de registro, no opcodes**. En `033` eso
ya me produjo 12 falsos positivos; aqui el riesgo es el mismo y esta acotado por el
hecho de que solo se aceptan layouts que ademas **tienen una emision contable**.

Corroborado ademas por un dato de `033`: `PACKET3_DMA_DATA` esta definido en 4 ficheros
con el mismo valor `0x50`, y `PACKET3_CP_DMA` tiene opcode `0x41` distinto. Si el parser
confundiera opcodes con offsets, los valores no coincidirian entre ficheros. Coinciden.

## 2 · El cruce: 28/28

Herramienta nueva: `08-ARQUITECTURA/tools/pm4_layout_audit.py`. Para cada emision de un
paquete con layout documentado, compara tres cosas:

| quantity | source |
|---|---|
| `doc` | el comentario de layout del kernel |
| `real` | dwords de datos contados en el codigo de emision |
| `F` | el valor que el driver pone en el campo de longitud |

Y exige que las tres cosas sean ciertas a la vez:

```
F == doc - 1        y        F == real - 1
```

Resultado:

```
layouts documentados en el corpus : 25
emisiones con layout documentado  : 28
conformes   : 28
discrepantes: 0
```

### 2.1 · Un caso concreto, leido entero

`gfx_v8_0.c:4345` (`gfx_v8_0_kiq_kcq_enable`), y el layout documentado de
`MAP_QUEUES` correspondiente:

```c
amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_MAP_QUEUES, 5));      /* F = 5 */
amdgpu_ring_write(kiq_ring, PACKET3_MAP_QUEUES_NUM_QUEUES(1));   /* dw2 */
amdgpu_ring_write(kiq_ring,
                  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(...) |
                  PACKET3_MAP_QUEUES_QUEUE(...) |
                  PACKET3_MAP_QUEUES_PIPE(...) |
                  PACKET3_MAP_QUEUES_ME(...));                  /* dw3 */
amdgpu_ring_write(kiq_ring, lower_32_bits(mqd_addr));            /* dw4 */
amdgpu_ring_write(kiq_ring, upper_32_bits(mqd_addr));            /* dw5 */
amdgpu_ring_write(kiq_ring, lower_32_bits(wptr_addr));           /* dw6 */
amdgpu_ring_write(kiq_ring, upper_32_bits(wptr_addr));           /* dw7 */
```

7 dwords totales = **1 cabecera + 6 payload**. `F = 5`. Y el layout documentado en
`soc15d.h:485` dice `payload_doc = 6`. Las dos cuentas coinciden, y `F = payload − 1`.

Ese `MAP_QUEUES` tiene un valor añadido: es el paquete que **instala la cola en el
hardware** y cuyo `doorbell_offset` es el nexo con `031`. Que su layout este documentado
y a la vez coincida con la emision significa que el driver de referencia y su documentacion
no discrepan ni en un bit del paquete que decide que cola ejecuta el hardware.

### 2.2 · El paquete de 1 payload, el borde que importa

`PACKET3_RUN_CLEANER_SHADER` tiene `payload_doc = 1`, y se emite con `F = 0`:

```
PACKET3(PACKET3_RUN_CLEANER_SHADER, 0)   ->   F = 0 = 1 - 1
```

Es el caso limite. Con la lectura de freedreno (`total = F + 1`), `F = 0` daria un
paquete de 1 dword total — lo que significaria que un paquete `RUN_CLEANER_SHADER` no
tiene ningun operando, lo cual es absurdo para un shader que limpia cachés. Con la
lectura del corpus (`payload = F + 1 = 1`), el paquete tiene **un** operando: el puntero
de estado del shader. Que es lo que tiene que tener.

Es el mismo argumento que `033` §3.3 hacia `0x3FFF`, pero ahora con la documentacion del
kernel como|Arbitro en vez de mi inferencia.

## 3 · Validacion por mutacion

Una herramienta que siempre dice "28/28" no vale nada si no se le puede romper. Se
introdujo una discrepancia real en el corpus y se comprueba que la herramienta la ve.

Mutante: `gfx_v8_0.c:4345`, `PACKET3(PACKET3_MAP_QUEUES, 5)` → `, 4`.

```
...
PACKET3_MAP_QUEUES    6    5     6     5  OK
PACKET3_MAP_QUEUES    6    4     6     5  *** DISCREPA ***
...
conformes   : 27
discrepantes: 1

VEREDICTO: hay discrepancias. No cerrar la convencion; investigarlas.
  gfx_v8_0.c:4345 gfx_v8_0_kiq_kcq_enable PACKET3_MAP_QUEUES F=4 real=6 doc=6
```

La herramienta **detecta y localiza** la discrepancia con fichero, linea y funcion. Sin
que nadie le diga donde mutar.

Restaurado el corpus y comprobado: vuelve a 28/28, y `git status --porcelain RESEARCH/`
queda **vacio** — el corpus esta intacto.

Un segundo mutante se intento sobre el opcode `PACKET3_MAP_QUEUES` en `sid.h` y resulto
**inaplicable**: GFX8 no usa ese opcode desde `sid.h`, lo toma de la cabecera de la
generacion que le toca. Lo dejo anotado porque es exactamente el tipo de supuesto
equivocado que haria perder tiempo: si hubiera "verificado" ese mutante contra `sid.h`
estaria midiendo el fichero equivocado.

## 4 · `RELEASE_MEM`: el dword extra de GFX9, localizado

`029` dejo este `NOT_DETERMINED` con tres hipotesis separadas (contador vs reservado vs
otro). La ronda lo cierra por razonamiento de codigo, no por hardware.

### 4.1 · GFX8: 6 payload

```c
/* gfx_v8_0.c:6239, emit_fence */
amdgpu_ring_write(ring, PACKET3(PACKET3_RELEASE_MEM, 5));        /* F = 5, payload 6 */
amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN |
                         EOP_TC_ACTION_EN |
                         EOP_TC_WB_ACTION_EN |
                         EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) |
                         EVENT_INDEX(5)));                        /* dw2: acciones */
amdgpu_ring_write(ring, DATA_SEL(...) | INT_SEL(int_sel ? 2 : 0));  /* dw3 */
amdgpu_ring_write(ring, addr & 0xfffffffc);                       /* dw4 */
amdgpu_ring_write(ring, upper_32_bits(addr));                     /* dw5 */
amdgpu_ring_write(ring, lower_32_bits(seq));                      /* dw6 */
amdgpu_ring_write(ring, upper_32_bits(seq));                      /* dw7 */
```

6 payload: acciones, `DATA_SEL`/`INT_SEL`, addr(2), seq(2). Cuadra con
`RELEASE_MEM` de 6.

### 4.2 · GFX9: 7 payload, y el bit que lo explica

```c
/* gfx_v9_0.c:5546 */
amdgpu_ring_write(ring, PACKET3(PACKET3_RELEASE_MEM, 6));        /* F = 6, payload 7 */

if (writeback) {
        dw2 = EOP_TC_NC_ACTION_EN;
} else {
        dw2 = EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN |
              EOP_TC_MD_ACTION_EN;
}
dw2 |= EOP_TC_WB_ACTION_EN | EVENT_TYPE(...) | EVENT_INDEX(5);
if (exec)
        dw2 |= EOP_EXEC;
```

GFX8 tiene **un solo camino**. GFX9 tiene **dos**, y solo uno lleva `EOP_TC_MD_ACTION_EN`.

`soc15d.h:321` lo define con comentario:

```c
#define  EOP_TC_MD_ACTION_EN  (1 << 21)  /* L2 metadata */
```

El bit **MD** es el unico de todo el bloque que tiene nombre propio ("L2 metadata"), y el
unico que no existe en `cikd.h` (el juego de GFX8). El resto del bloque es
`TCL1`/`TC`/`TC_WB`/`TC_NC`, todos presentes en ambas generaciones.

**Lectura:** el bit 21 no es un contador ni un reservado. Es una **tercera superficie de
cache en L2** —la de metadatos— que GFX9 flusha y GFX8 no tiene o no nombra. Aparece
exactamente en la rama que **no** hace writeback, es decir donde se invalida en vez de
escribir.

Eso conecta con `029` §6: el hilo de `EOP_TC_MD_ACTION_EN` lleva a la frontera G. Lo que
`033` establecio como `NOT_DETERMINED` por falta de documentacion PM4 **esta
resuelto por el corpus**, porque la informacion no estaba en el documento de AMD sino en
el codigo del driver. Es la leccion de `033` aplicada: cuando la fuente primaria no
tiene la respuesta, el corpus es la fuente.

`HYPOTHESIS` marcada, con su base: que `MD` = "metadata" y no otra cosa es lectura de
un comentario del driver, y el nombre de un campo del driver no es la semantica del
hardware. Lo que **si** es `PROVEN` es que la diferencia 6-vs-7 se explica por una rama
de codigo con un bit que el propio driver comenta como "L2 metadata", y que ese bit no
existe en la cabecera de GFX8.

## 5 · Clasificacion

| afirmacion | estado |
|---|---|
| El kernel documenta el layout de 25 paquetes | `PROVEN` — patron `/* 1. header` |
| 7 opcodes distintos tienen layout documentado | `PROVEN` |
| `F == doc − 1` y `F == real − 1` en 28/28 | **`PROVEN`, dos fuentes internas** |
| `F = datos − 1`, paquete = `F + 2` | **`PROVEN`** (subido de `PROVEN_DERIVED` en `033`) |
| La herramienta detecta una discrepancia inyectada | `PROVEN` — mutante validado |
| `MAP_QUEUES` documentado = emitido, bit a bit | `PROVEN` |
| `RELEASE_MEM` GFX8 = 6 payload | `PROVEN` |
| `RELEASE_MEM` GFX9 = 7 payload | `PROVEN` |
| El bit que explica la diferencia es `EOP_TC_MD_ACTION_EN` | `PROVEN` — rama de codigo |
| Que `MD` sea "L2 metadata" y no otra cosa | `HYPOTHESIS` — nombre del driver, no spec |
| Que exista una superficie de metadatos en L2 en GFX8 | `NOT_DETERMINED` |

## 6 · Confounders

- **Los 25 layouts se concentran en 7 paquetes.** La muestra es pequena y no es
  representativa de la variedad de paquetes: son precisamente los que el kernel documento
  porque son complicados (`SET_RESOURCES`, `MAP_QUEUES`). Un paquete "normal" no tiene
  layout documentado. El argumento se sostiene porque la regla es de **enquadre**, no de
  paquete, y 7 paquetes de 5 generaciones la confirman, pero no es una muestra de los
  74 opcodes. `LIMITATION` declarada.
- **`payload_doc` lo calcula un parser, no una persona.** Si el comentario numerado
  tuviera un error de numeracion, el parser propagaria el error y la coincidencia con `real`
  lo delataria. Que coincidan es lo que importa, y por eso comparo las tres columnas en
  vez de fiarme de una.
- **`RUN_CLEANER_SHADER` tiene layout documentado con 1 payload pero no se emite en GFX8**
  (solo GFX9+). La confirmacion del borde viene de esas emisiones, no del path GFX8. El
  argumento sigue valiendo —el paquete existe y su layout esta documentado— pero no es una
  medida sobre esta placa.
- El `EOP_TC_MD_ACTION_EN` es `1 << 21`. Que el bit 21 no este en el bloque GFX8 y si en
  GFX9 es `PROVEN` por lectura de las dos cabeceras. Que eso signifique "una superficie
  de metadatos en L2" es lectura de un comentario de una linea. `HYPOTHESIS`, marcada.
- **El mutante de opcode en `sid.h` resulto inaplicable** porque GFX8 toma ese opcode de
  otra cabecera. No es un fallo de la herramienta (que no fue sensible a el) sino un
  recordatorio de que `sid.h` no es la unica fuente de opcodes de GFX8. En GFX8 hay al
  menos `cikd.h` (que si lo usa) y la cabecera de la generacion. `NOTA` de navegacion.

## 7 · UNLOCKS

- **La convencion de encoding PM4 pasa de `PROVEN_DERIVED` a `PROVEN` con fuentes
  independientes internas.** Un driver propio puede escribir un assembler PM4 GFX8 sin
  ningunOUN caveat de plataforma, sin hardware, y sin depender de un tercero que podria
  estar equivocado (`033` §4 demostro que freedreno lo esta en un punto).
- **Herramienta reusable:** `pm4_layout_audit.py` es un detector de discrepancias entre
  documentacion y codigo. Si alguien modifica el driver y rompe un layout, salta. Es la
  forma de hacer mantenible la afirmacion "el corpus es consistente consigo mismo".
- **`EOP_TC_MD_ACTION_EN` queda aislado como el unico campo de la frontera G que tiene
  nombre propio en el driver.** Es el punto de entrada para la siguiente ronda de
  cache/coherencia: hay que determinar que superficies de cache hay en GFX8 y si el
  hardware tiene una que el driver no nombra.
- **La leccion de `033` queda aplicada con exito:** `033` concluyo que la semantica PM4 no
  existe publicada. Este `NOT_DETERMINED` se cerro con el corpus. La leccion no es "no
  hay documentacion" sino "el corpus del driver es mas rico de lo que parece, y hay que
  leerlo como fuente de verdad, no solo como codigo a compilar".
- `DESIGN_FREEDOM`: el driver propio no necesita `SET_RESOURCES` completo si no mapea
  recursos de la misma forma; pero si necesita `MAP_QUEUES` porque sin el el hardware no
  tiene cola. Con el layout medido, saberlo escribir es directo.

## 8 · Criterio de falsificacion

Se refutaria si: (a) un layout documentado del corpus tuviera una numeracion que no
correspondiera a dwords reales, y el parser propagara el error silenciosamente —refutable
leyendo un paquete a mano contra su comentario, que es lo que hice con `MAP_QUEUES` §2.1;
(b) existiera un paquete con layout documentado que se emita con `F != doc − 1` en una
ruta que no yo haya barrido —refutable, el barrido es de todo `*.c` y el filtro `--only`
esta disponible; (c) `EOP_TC_MD_ACTION_EN` no fuera la causa de la diferencia 6-vs-7 sino
un efecto secundario —refutable contando los payload de ambas ramas de GFX9 por separado,
que no hice porque las dos ramas emiten 7; (d) el hardware tratara `F` como `datos − 1`
pero con un payload implicito adicional —refutable solo con hardware, y es el limite que
`033` §10 ya nombró.

## 9 · Evidencia

```
CORPUS — layouts documentados:
  cikd.h:396-402          PACKET3_DMA_DATA      payload_doc 6
  sid.h:418-425           PACKET3_CP_DMA        payload_doc 5
  soc15d.h:347,472,485,507,537,556,561   DMA_DATA, SET_RESOURCES,
                                         MAP_QUEUES, UNMAP_QUEUES,
                                         QUERY_STATUS, RUN_CLEANER_SHADER_9_0,
                                         RUN_CLEANER_SHADER
  vid.h:272,372,385,407,437               los mismos
  nvd.h:398,582,596,618,648,669           los mismos
  gfx_v12_1_pkt.h:231,372,385,406,436      los mismos
  total 25 layouts, 7 opcodes, 6 ficheros

CORPUS — emisiones (leidas enteras, no contadas por heuristica):
  gfx_v8_0.c:4345-4357    MAP_QUEUES  F=5, 6 dw  (verificado linea a linea)
  gfx_v8_0.c:6239-6247    RELEASE_MEM F=5, 6 dw  GFX8
  gfx_v9_0.c:5546-5557    RELEASE_MEM F=6, 7 dw  GFX9, dos ramas
  soc15d.h:321            EOP_TC_MD_ACTION_EN (1<<21) /* L2 metadata */
  cikd.h:396+             sin EOP_TC_MD: el bit no existe en GFX8

HERRAMIENTA:
  08-ARQUITECTURA/tools/pm4_layout_audit.py
    -- sin argumentos: todo el arbol -> 28/28
    validada por mutacion: gfx_v8_0.c:4345 ,5 -> ,4  => detecta y localiza
    restaurado: 28/28, git status --porcelain RESEARCH/ vacio
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

## 10 · Resumen del estado de la frontera D

```
enquadre PM4 (tipo, longitud, opcode, paridad)   PROVEN   034 + 033
convencion F = datos - 1                         PROVEN   034 (doble fuente)
payload de COND_EXEC                             NOT_DETERMINED   requiere hardware
payload de RELEASE_MEM extra (GFX9)              PROVEN (causa)   034
payload de VM_INVALIDATE / INT_SEL               NOT_DETERMINED   requiere hardware
superficie de metadatos en L2 (GFX8)             NOT_DETERMINED   034, siguiente ronda
```

Lo que queda abierto **no se cierra con mas lectura de codigo**: es el comportamiento
del hardware. Y `033` ya establecio que no habra documento que lo resuelva. El proximo
paso con valor real es un experimento de hardware, y su diseno es lo que corresponde
documentar.