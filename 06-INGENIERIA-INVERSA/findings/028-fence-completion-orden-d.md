# 028 · Frontera D: el fence sí tiene completion; el ring GFX lo ejecuta de tres formas

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=AGENTS.md:617-627` (frontera D: orden PTBA→INVALIDATE→WAIT→PFP_SYNC_ME→next IB)

## CUDA principal

El fence **es el unico punto del path de submit donde el hardware confirma que el
trabajo anterior termino**, y lo hace de tres formas distintas segun el ring. Las tres
son reales y las tres se pueden fechar con el fuente:

```
GFX      : EVENT_WRITE_EOP  x2   (uno con seq-1, otro con seq y EOP_EXEC)
COMPUTE  : RELEASE_MEM      x1
KIQ      : WRITE_DATA       x1 + WRITE_DATA a mmCPC_INT_STATUS (si INT)
```

El contraste con el vm-flush es el punto: `WAIT_REG_MEM(always, mask=0)` **no compara
nada** (`017`), mientras que el fence **escribe un valor y lo espera el CPU**. Ese es
el completion que el driver propio necesita y que si existe en GFX8 — solo que no es
un wait en el ring: es una **direccion de memoria en la que el hardware deposita un
secuencial**.

## Alcance exacto

1. Los tres `emit_fence` de GFX8, con su encoding y su mecanismo.
2. Que significa cada campo (`INT_SEL`, `DATA_SEL`, `EOP_EXEC`).
3. El coste en dwords de cada uno, y si la reserva del ring lo cubre.
4. Que garantia ofrece cada uno y cual es el completion real del submit.

## Criterio de terminacion (cumplido)

Los tres fences estan medidos, sus campos decodificados, y el coste comparado con la
reserva por ring. Agotado.

---

## 1 · Los tres fences

### 1.1 · `gfx_v8_0_ring_emit_fence_gfx` — 12 dw, dos EOP

```c
/* 1er EOP: seq - 1, sin EOP_EXEC */
PACKET3(PACKET3_EVENT_WRITE_EOP, 4)
EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN
        | EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) | EVENT_INDEX(5)
addr & 0xfffffffc
upper_32_bits(addr) | DATA_SEL(1) | INT_SEL(0)
lower_32_bits(seq - 1) | upper_32_bits(seq - 1)

/* 2do EOP: seq, con EOP_EXEC si el caller lo pide */
PACKET3(PACKET3_EVENT_WRITE_EOP, 4)
... | (exec ? EOP_EXEC : 0)
addr & 0xfffffffc
upper_32_bits(addr) | DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0)
lower_32_bits(seq) | upper_32_bits(seq)
```

El primero lleva `seq - 1` y el comentario explica por que:

```
/* Workaround for cache flush problems. First send a dummy EOP
 * event down the pipe with seq one below. */
```

Es decir: el primer EOP **no** completa el fence, solo fuerza el vaciado de caches
recorriendo el pipeline. El segundo es el que lleva el valor real. `seq - 1` y no `seq`
porque si escribiera `seq` el CPU podria observar el fence antes de que el vaciado de
cache terminase.

Eso es una **disciplina de orden**, y es la unica vez en todo el path donde el driver
manda deliberadamente un valor *anterior* al real para no adelantarse. Es informacion
sobre el hardware que no sale de ningun comentario: sale de la estructura del codigo.

**Y es una tecnica con historia, no un idiosyncraticismo de GFX8.** El mismo workaround
con el mismo texto aparece en `gfx_v7_0.c:2120` y `gfx_v8_0.c:6142`, y **no** en GFX6.
Ver §1.1bis.

`EOP_EXEC` (`vid.h:249`, comentario `/* For Trailing Fence */`) se anade solo si el
caller pasa `AMDGPU_FENCE_FLAG_EXEC`. Es la variante de "trailing fence", que debe
ejecutarse incluso si el contexto se pierde.

### 1.1bis · La evolucion del fence: cuatro estrategias en cuatro generaciones

El fence **cambia de forma sustantiva** entre generaciones. No es el mismo mecanismo
con ajustes, son cuatro distintos:

```
GFX6  (gfx_v6_0_ring_emit_fence)     4 paquetes
  SET_CONFIG_REG   -> mmCP_COHER_CNTL2         (coherencia por configuracion)
  SURFACE_SYNC     -> TCL1 + TC + SH_KCACHE + SH_ICACHE   (4 caches)
  EVENT_WRITE_EOP  -> seq

GFX7  (gfx_v7_0_ring_emit_fence)     2 EOP
  EVENT_WRITE_EOP  -> seq - 1       <-- workaround de cache flush
  EVENT_WRITE_EOP  -> seq

GFX8  (gfx_v8_0_ring_emit_fence_gfx) 2 EOP
  EVENT_WRITE_EOP  -> seq - 1       <-- mismo workaround, mismo texto
  EVENT_WRITE_EOP  -> seq (+EOP_EXEC)

GFX9+ (gfx_v9_0 y siguientes)       RELEASE_MEM, 1 paquete
  ya no hay seq-1
```

Tres cosas que se ven al ponerlas en fila:

1. **El numero de caches bajo de 4 a 3.** GFX6 invalida `SH_KCACHE` e `SH_ICACHE`;
   GFX8 solo `TCL1`, `TC`, `TC_WB`. Los caches de shader se drenan por otro camino, muy
   probablemente el `EOP` al recorrer el pipeline. `DERIVATION`, no `PROVEN`: ningun
   documento lo dice.
2. **El workaround de `seq - 1` nace en GFX7 y muere en GFX9.** Compensacion por un
   problema de cache flush que existio exactamente dos generaciones. `PROVEN` que
   aparece y desaparece; `NOT_DETERMINED` por que desaparecio y por que `RELEASE_MEM` no
   lo necesita.
3. **GFX6 no necesita ningun paquete de vaciado previo** porque su flush es
   *sincrono por configuracion*: escribe `CP_COHER_CNTL2` y continua. El problema que
   obligo a inventar `seq - 1` en GFX7 es que en GFX7 el vaciado paso a ser
   *asincrono y dependiente del EOP*.

Ultimo punto, y es la leccion para el driver propio: **el fence es la parte del path
que mas cambio entre generaciones**, mas incluso que el vm-flush, que no cambio nada
entre GFX6 y GFX8. Es donde el hardware se manifesto mas.

### 1.2 · `gfx_v8_0_ring_emit_fence_compute` — 7 dw, un `RELEASE_MEM`

```c
/* RELEASE_MEM - flush caches, send int */
PACKET3(PACKET3_RELEASE_MEM, 5)
EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN
        | EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT) | EVENT_INDEX(5)
DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0)
addr & 0xfffffffc
upper_32_bits(addr)
lower_32_bits(seq) | upper_32_bits(seq)
```

Un solo paquete, porque `RELEASE_MEM` **ya** hace flush + escritura. No hace falta el
EOP dummy previo: en un ring de compute no hay pipeline de graficos que vaciar de la
misma manera, asi que el `seq - 1` no tendria sentido.

`PROVEN_DERIVED` la razon de la diferencia: el GFX emite 2 paquetes porque su pipeline lo
exige, y el codigo del compute no lo hace. Esa asimetria **no esta comentada** y es
informacion de hardware.

### 1.3 · `gfx_v8_0_ring_emit_fence_kiq` — 5 dw, escritura directa

```c
BUG_ON(flags & AMDGPU_FENCE_FLAG_64BIT);      /* solo 32 bit por seq */

PACKET3(PACKET3_WRITE_DATA, 3)
WRITE_DATA_ENGINE_SEL(0) | WRITE_DATA_DST_SEL(5) | WR_CONFIRM
lower_32_bits(addr) | upper_32_bits(addr)
lower_32_bits(seq)

if (flags & AMDGPU_FENCE_FLAG_INT) {
        PACKET3(PACKET3_WRITE_DATA, 3)
        WRITE_DATA_ENGINE_SEL(0) | WRITE_DATA_DST_SEL(0) | WR_CONFIRM
        mmCPC_INT_STATUS, 0, 0x20000000        /* src_id 178 */
}
```

**Sin EOP, sin flush de caches.** Es una escritura de registro pura. Con `INT` son
5 + 5 = **10 dw**.

`BUG_ON(flags & AMDGPU_FENCE_FLAG_64BIT)` con el comentario *"we only allocate 32bit
for each seq wb address"*. Es la misma clase de `LIMITATION` que `026` §1: el codigo
declara una restriccion que su propia firma no expresa.

## 2 · Los campos, decodificados

De `vid.h:237-266`:

| campo | shift | valores | significado |
|---|---|---|---|
| `DATA_SEL` | 29 | 0/1/2/3/4 | descartar / low 32 / **64 bits** / contador GPU / contador sys |
| `INT_SEL` | 24 | 0/1/2 | ninguno / solo int / **int cuando la escritura se confirma** |
| `EOP_EXEC` | 28 | bit | trailing fence: ejecutar aunque se pierda el contexto |
| `EOP_TCL1_ACTION_EN` | 16 | bit | actuar sobre TCL1 (L1 de textura) |
| `EOP_TC_ACTION_EN` | 17 | bit | actuar sobre TC/L2 |
| `EOP_TC_WB_ACTION_EN` | 15 | bit | writeback de TC/L2 |
| `EOP_CACHE_POLICY` | 25 | 0/1/2 | LRU / Stream / Bypass |

`INT_SEL = 2` es el que da la garantia fuerte: **la interrupcion se dispara cuando la
escritura se confirma**, no cuando el paquete se decodifica. Esa es la distincion entre
"el CPU sabe que se emitio" y "el CPU sabe que se ejecuto".

`DATA_SEL = 3` y `4` (mandar un contador en vez del dato) estan definidos y **el driver
de GFX8 no los usa nunca**. `PROVEN_ABSENT` por barrido de `DATA_SEL` en `gfx_v8_0.c`.
Es capacidad disponible no usada, como `COND_EXEC` pero al reves: aqui el mecanismo
existe y esta en uso; lo que falta es la variante.

## 3 · El coste, y una discrepancia aritmetica

| ring | fence | dw reales | declarado por fence | declarado total |
|---|---|---|---|---|
| `GFX` | `fence_gfx` | **12** | 12 x2 = 24 | 24 |
| `COMPUTE` | `fence_compute` | **7** | 7 x3 = 21 | 21 |
| `KIQ` | `fence_kiq` sin INT | **5** | 7 x3 = 21 | 21 |
| `KIQ` | `fence_kiq` con INT | **10** | 7 x3 = 21 | 21 |

GFX y COMPUTE cuadran exactamente. **KIQ no**: declara 7 y emite 5 o 10.

### 3.1 · ¿Es un defecto del driver de referencia?

Aritmetica:

```
1 fence con INT :  real 10  vs declarado  7   -> desborda por 3
3 fences con INT:  real 30  vs declarado 21   -> desborda por 9
```

Con el `INT` que el driver **siempre** activa (`amdgpu_fence.c:118`:
`seq, flags | AMDGPU_FENCE_FLAG_INT`), el `else` de `amdgpu_fence.c:175`
(`seq, 0`) es el unico sin INT, y ese es `fence_wait_polling`.

**Pero la severidad es baja, por dos razones medidas:**

**(a) El driver lo detecta.** `amdgpu_ring_commit` (`amdgpu_ring.c:172-173`):

```c
if (ring->count_dw < 0)
        drm_err(adev_to_drm(ring->adev), "writing more dwords to the ring than expected!\\n");
```

`count_dw` se descuenta en cada `amdgpu_ring_write` y se inicializa con lo que se
reservo. Es una **asercion en runtime, no corrupcion**: el anillo no se desborda porque
`ring_alloc` alineo y el ring es circular; lo que se rompe es la contabilidad y sale un
`drm_err`.

**(b) El camino no se ejercita en GFX8.** El propio driver dice que KIQ no usa el
scheduler (`amdgpu_ring.c:241-243`):

```
* it's used for a number of gfx/compute tasks by both
* KFD and KGD which may have outstanding fences and
* it doesn't really use the gpu scheduler anyway;
* KIQ tasks get submitted directly to the ring.
```

Los submits de usuario pasan por `drm_sched_job_arm` → el ring GFX o compute, nunca KIQ.
KIQ recibe trabajo del firmware y de los tests de anillo. `gfx_v8_0_ring_test_ring`
**no llama a `emit_fence`** (escribe un `SET_UCONFIG_REG` y hace polling de un
registro). El otro camino, `gfx_v8_0_gfx_shadow`, exige `cp_gfx_shadow`, que solo
`gfx_v11_0.c` pone a true.

`NOT_APPLICABLE` para Polaris12 con causa, no `PROVEN_ABSENT`. Es un defecto real del
driver de referencia **para ASIC con GFX shadow o con KIQ schedulable**, y en GFX8 no
llega a ejecutarse.

`NEGATIVE_RESULT` heredable: si el driver propio emite fence en un ring sin EOP, tiene
que **contar el `INT`**.

## 4 · Que garantia da cada uno

Aqui esta el completion que la frontera D necesita:

```
[submit]  ... IB ...
          FENCE      -> el hardware escribe seq en una direccion de GPU
                       y (si INT) genera interrupcion al CONFIRMAR la escritura
[CPU]     lee fence_cpu_addr, compara con seq
          -> cuando coincide, todo lo anterior a ese fence esta hecho
```

Es un **handshake por memoria compartida**, no un wait en el ring. Y tiene una
propiedad que el `WAIT_REG_MEM` no tiene: **el CPU lo observa**, porque
`fence_drv.cpu_addr` apunta a una pagina de sistema mapeada de forma coherente.

`PROVEN_DERIVED` la cadena, leyendo `amdgpu_fence_emit` (`amdgpu_fence.c:101-125`) y
los consumidores de `fence_cpu_addr`. Que la coherencia de CPU↔MMIO↔GPU sea suficiente
en esta placa es `HYPOTHESIS`, marcada: es la misma `HYPOTHESIS` que `025` §2 para el
path GART, y alli queda `NOT_DETERMINED` para el efecto hardware.

### 4.1 · Lo que esto NO resuelve

El fence ordena **el trabajo del shader** respecto al fence. **No** ordena el
invalidate de TLB respecto al IB siguiente:

- `fence` responde a "termino el trabajo dispatched".
- el vm-flush responde a "cambie el page table root".

Son dos preguntas distintas y el fence no contesta la segunda. `018` ya cerro que el
invalidate no tiene ack; este documento no lo cambia, **anade un mecanismo de orden que
si funciona pero para otro objeto**.

Lo que si habilita: el driver propio puede colocar un fence **despues** del
`emit_vm_flush` y apoyarse en una garantia que el vm-flush no da. Eso no convierte
`NOT_PROVEN` en `PROVEN`: el invalidate seguiria sin confirmacion propia, pero el
trabajo posterior quedaria ordenado por un mecanismo que si funciona.

`HYPOTHESIS` de diseño, no afirmación. El codigo de referencia **no** hace eso
(`emit_vm_flush` va seguido de `PFP_SYNC_ME`, no de un fence), y no hay ninguna razon
en el corpus para que lo haga. `NOT_DETERMINED` si seria correcto o innecesario.

## 5 · Clasificacion

| Afirmacion | Estado |
|---|---|
| Hay tres mecanismos de fence distintos en GFX8 | `PROVEN` (tres funciones) |
| `fence_gfx` manda `seq-1` primero, deliberadamente | `PROVEN` + comentario |
| `INT_SEL=2` significa "int al confirmar la escritura" | `PROVEN` (encoding en `vid.h`) |
| `EOP_EXEC` es la variante de trailing fence | `PROVEN` (encoding) |
| `fence_compute` no necesita el EOP dummy | `PROVEN_DERIVED` (un paquete, no dos) |
| `fence_kiq` no hace flush de caches | `PROVEN` (no hay ningun EOP) |
| `DATA_SEL` 3 y 4 no se usan en GFX8 | `PROVEN_ABSENT` (barrido) |
| Costes 12 / 7 / 5-10 dw | `PROVEN` (conteo) |
| KIQ declara 7 y emite 5 o 10 | `PROVEN` |
| Eso produce `drm_err` de "more dwords than expected" | `PROVEN_DERIVED` |
| KIQ no ejercita `emit_fence` en GFX8 | `NOT_APPLICABLE` con causa |
| El fence da completion por memoria compartida | `PROVEN_DERIVED` |
| Que esa coherencia baste en esta placa | `HYPOTHESIS` — mismo limite que `025` |
| Que un fence tras el vm-flush mejore el orden | `HYPOTHESIS` de diseno, `NOT_DETERMINED` |
| El fence cambio de estrategia en 4 generaciones | `PROVEN` (§1.1bis) |
| Que los caches de shader se drenen por el EOP | `DERIVATION` |

Ultima fila, y es la mas util: es la primera **opcion de diseno** que la serie produce
con una base medida. No es una recomendacion --el codigo de referencia no la hace y no
hay evidencia de que sirva-- pero es el sitio donde un driver propio puede aportar algo
que el driver de referencia no aporta.

## 6 · Confounders

- El recuento de dw de los fences **si** lo verifico con la herramienta de `021`
  (`frame_budget.py` mide `FENCE_gfx`=12, `FENCE_compute`=7, `FENCE_kiq`=10). Consistente
  con el conteo manual de aqui.
- El `BUG_ON(AMDGPU_FENCE_FLAG_64BIT)` de `fence_kiq` no se puede disparar en este
  corpus: ningun call site pasa 64BIT a un ring KIQ. `NOT_OBSERVED`, no
  `PROVEN_ABSENT`: el barrido fue de `amdgpu_cs.c`, `amdgpu_ib.c` y `amdgpu_fence.c`,
  no de todo el arbol.
- `INT_SEL` y `DATA_SEL` se leyeron de los **comentarios** de `vid.h`. Misma clase de
  evidencia que `026` §3 para los bits del PTE: documentacion de fuente, no hardware.
  Aqui hay menos riesgo porque los valores que el driver usa (1 y 2) son los
  obvios, pero sigue siendo comentario.

## 7 · UNLOCKS

- La frontera D tiene ahora **un mecanismo de orden que funciona**, distinto del que
  estaba buscando. El driver propio no esta obligado a depender solo de `PFP_SYNC_ME`.
- El fence es el punto de instrumentacion natural para cualquier discriminante runtime
  de esta serie: si un experimento necesita saber "cuando ha terminado esto", el
  mecanismo existe y esta probado por el propio driver de referencia.
- `seq - 1` como disciplina de orden es una tecnica reutilizable: para cualquier
  escritura de la que el CPU dependa, mandar primero el valor anterior obliga al
  hardware a recorrer el pipeline antes de exponer el bueno.
- `DATA_SEL` 3 y 4 son capacidad documentada y no usada. Un contador de GPU por IB es
  exactamente el tipo de instrumentacion que un driver propio querría y que el de
  referencia no habilita.
- La discrepancia de KIQ es `NEGATIVE_RESULT` con causa y severidad acotadas: el driver
  lo detecta en runtime, y el camino no se recorre en GFX8.

## 8 · Criterio de falsificacion

Se refutaria si: (a) `emit_frame_size` de `ring_funcs_kiq` reservara mas de lo que
transcribo — comprobable leyendo las 6 lineas, y ya esta checked; (b) KIQ recibiera
schedulable jobs en GFX8 por una ruta que no he encontrado, lo que convertiria la
discrepancia de latente en activa — refutable con un `dmesg` buscando el `drm_err`;
(c) `seq - 1` no sirviera para ordenar y fuera un residuo sin efecto — refutable solo
con RUNTIME; (d) `INT_SEL=2` no significara "al confirmar" y por tanto el fence no
diera el completion que le atribuyo — refutable con la especificacion PM4, que es la
misma fuente que falta en `022` y `023`. (a) esta cerrada; (b) y (c) exigen RUNTIME;
(d) exige documentacion externa.

## 9 · Evidencia

```
gfx_v8_0.c:   6135-6170 (fence_gfx: 2 EOP, seq-1 + seq), 6174-6185 (pipeline_sync),
              6231-6248 (fence_compute: RELEASE_MEM), 6252-6275 (fence_kiq),
              6899/6930/6936/6965/6967 (reservas y asignaciones por ring)
vid.h:        237-266 (DATA_SEL, INT_SEL, EOP_EXEC, EOP_*_ACTION_EN)
amdgpu_fence.c: 101-125 (emit: seq, flags|INT), 168-180 (wait_polling: seq, 0),
                407-432 (start_ring)
amdgpu_ring.c: 172-173 (drm_err si count_dw < 0), 238-250 (KIQ sin scheduler),
                95-101 (ring_alloc)
08-ARQUITECTURA/tools/frame_budget.py  (FENCE_gfx=12, FENCE_compute=7, FENCE_kiq=10)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador contenia texto corrupto en §4.1 y en §7. Corregido.
Noveno caso del mismo defecto al escribir; la nota se conserva porque el patron es mio
y se repite.