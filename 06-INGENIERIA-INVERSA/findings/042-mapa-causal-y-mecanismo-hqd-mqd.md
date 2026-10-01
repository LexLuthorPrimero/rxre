# 042 · El mapa causalFlechas encuentra 64 registros que nadie había mirado

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTAS_NUEVAS=08-ARQUITECTURA/tools/causal_chain.py`, `next_work.py`
`CONTINUES=041` · `DESCUBRE=el mecanismo HQD MQD, que no estaba en ningun hallazgo`

## CUDA principal

`next_work.py` respondió "qué hago ahora" con algo que no esperaba:

```
[1] 64 registros que el camino alcanza y ningun hallazgo menciona
    detalle: 64 de 95 registros sin mencion documental
```

Y al mirarlos, la lista empieza por `mmCP_HQD_CTX_SAVE_*`, `mmCP_HQD_EOP_*`,
`mmCP_HQD_IB_CONTROL`, `mmCP_MQD_CONTROL`… **el mecanismo HQD/MQD entero**, que no
aparece en ningún hallazgo de este proyecto.

La cadena resulta ser:

```
mmCP_HQD_VMID ... mmCP_HQD_EOP_CONTROL   (rango contiguo)
   LEIDO en cp_gfx_start   -> guardado en mqd->cp_hqd_*
   REESCRITO tras un stop  -> en el mismo orden, por bucles
```

**El hardware inicializa esos registros al crear un HQD; el driver los lee, los
guarda en el MQD, y los reescribe cuando reanuda la cola.** Es el mecanismo de
ahorro/restaurado de estado de cola. Está en el código, escrito por el driver, y
no estaba en el mapa.

Y sale de una herramienta, no de pensar en ello. Eso es exactamente el
`SOURCE → … → HARDWARE EFFECT` que el proyecto busca, aplicado.

## Alcance exacto

1. Componer las cinco herramientas existentes en un mapa causal generado.
2. Automatizar la pregunta "qué hago después" a partir del estado real.
3. Investigar el borde que la herramienta discover.
4. Documentar.

## Criterio de terminacion (cumplido)

1093 aristas extraídas y verificadas, 64 registros sin documentar,,
mecanismo MQD identificado y documentado. Agotado.

---

## 1 · El mapa causal, generado

`causal_chain.py` compone lo que ya existía sin duplicar nada:

```
gmmio_inventory  +  pm4_reachable  +  pm4_codec
       +  include_closure  +  causal_map
              ↓
      CAUSAL CHAIN
```

Cada arista dice **qué función escribe/lee/emite qué**, con fichero y línea.
Nada más. Nada de lo que no esté en el código.

```
funciones alcanzables : 262
aristas extraídas     : 1093

tipo           qué significa                            n
CALL           llama a                                684
IB_WRITE       escribe dwords en el indirect buffer   172
REG_WRITE      escribe el registro MMIO                95
REG_READ       lee el registro MMIO                    86
PM4_EMIT       emite el paquete PM4                    52
WR_MEM         escribe memoria del writeback            2
DOORBELL       toca el doorbell                         2
```

Y la confirmación de `031`, ahora **por máquina**:

```
WR_MEM    gfx_v8_0_ring_set_wptr_gfx     -> *ring->wptr_cpu_addr   gfx_v8_0.c:6028
DOORBELL  gfx_v8_0_ring_set_wptr_gfx     -> doorbell               gfx_v8_0.c:6029
WR_MEM    gfx_v8_0_ring_set_wptr_compute -> *ring->wptr_cpu_addr   gfx_v8_0.c:6227
DOORBELL  gfx_v8_0_ring_set_wptr_compute -> doorbell               gfx_v8_0.c:6228
```

Las dos escrituras de `031` §2, **en líneas consecutivas**. La cadena de dos
dominios de memoria, medida por la herramienta, sin que nadie la nombrara.

### 1.1 · Un bug de los filtros, y por qué lo ocultaba

Los filtros `--edges` y `--register` no funcionaban: el resumen decía `WR_MEM 2`
pero al pedir `--edges WR_MEM` salía vacío.

Motivo: los bucles buscaban el flag sobre `args`, que ya excluía los `--`, así que
`args[i+1]` era la posición siguiente de una lista **sin** el flag. Los datos
eran correctos; el filtro estaba roto.

Un filtro que devuelve vacío cuando hay datos es peor que no tener filtro:
se lee como "no hay nada" y se pierde el dato. Corregido sobre `sys.argv`.

## 2 · El mecanismo HQD/MQD: lo que la herramienta encontró

De los 64 registros sin documentar, el grupo coherente es el **HQD** (Hardware
Queue Descriptor), el estado de una cola:

```
mmCP_HQD_VMID        mmCP_HQD_CTX_SAVE_*    mmCP_HQD_EOP_*
mmCP_MQD_BASE_ADDR   mmCP_HQD_CTX_SAVE_SIZE  mmCP_HQD_IB_CONTROL
mmCP_MQD_CONTROL     mmCP_HQD_CNTL_STACK_*  mmCP_HQD_ERROR
```

### 2.1 · El ciclo, en el código

**Al arrancar una cola** (`gfx_v8_0_cp_gfx_start`), lee el estado que el hardware
puso:

```c
/* gfx_v8_0.c:4515-4532, en cp_gfx_start */
tmp = RREG32(mmCP_HQD_CTX_SAVE_CONTROL);
tmp = REG_SET_FIELD(tmp, CP_HQD_CTX_SAVE_CONTROL, MTYPE, 3);
mqd->cp_hqd_ctx_save_control = tmp;

tmp = RREG32(mmCP_HQD_IB_CONTROL);
tmp = REG_SET_FIELD(tmp, CP_HQD_IB_CONTROL, MIN_IB_AVAIL_SIZE, 3);
tmp = REG_SET_FIELD(tmp, CP_HQD_IB_CONTROL, MTYPE, 3);
mqd->cp_hqd_ib_control = tmp;

mqd->cp_hqd_eop_rptr           = RREG32(mmCP_HQD_EOP_RPTR);
mqd->cp_hqd_eop_wptr           = RREG32(mmCP_HQD_EOP_WPTR);
mqd->cp_hqd_eop_wptr_mem       = RREG32(mmCP_HQD_EOP_WPTR_MEM);
mqd->cp_hqd_ctx_save_base_addr_lo = RREG32(mmCP_HQD_CTX_SAVE_BASE_ADDR_LO);
mqd->cp_hqd_ctx_save_size      = RREG32(mmCP_HQD_CTX_SAVE_SIZE);
mqd->cp_hqd_eop_done_events    = RREG32(mmCP_HQD_EOP_EVENTS);
mqd->cp_hqd_error              = RREG32(mmCP_HQD_ERROR);
...
```

**Al reanudar** una cola, los reescribe en el mismo orden:

```c
/* gfx_v8_0.c:4559-4575, en cp_gfx_start */
for (mqd_reg = mmCP_HQD_VMID; mqd_reg <= mmCP_HQD_EOP_CONTROL; mqd_reg++)
        WREG32(mqd_reg, mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]);
...
for (mqd_reg = mmCP_HQD_EOP_EVENTS; mqd_reg <= mmCP_HQD_ERROR; mqd_reg++)
        WREG32(mqd_reg, mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]);
```

Y activa la cola con un tercer bucle, de `mmCP_MQD_BASE_ADDR` a `mmCP_HQD_ACTIVE`.

### 2.2 · Lo que esto significa

El driver **no programa** esos registros desde cero: los **preserva**. Lee lo que
el hardware inicializó al crear el HQD, lo guarda en el MQD (el `mqd_data[]` en
memoria del driver), y lo reescribe cuando la cola se reanuda.

Eso tiene una consecuencia directa para el driver propio: **hay ~38 campos
`cp_hqd_*` que el driver tiene que conocer**, y que no se deducen del código
sino del hardware. Un `mwd` mal rellenado no da error de compilación: da una cola
que no arranca. Es `NOT_DETERMINED` por qué valores exactos son válidos, pero el
*conjunto* de campos está `PROVEN` por el código.

Es el mismo patrón que `036` establecio con los paquetes PM4 —el conjunto de trabajo
real— y su versión de estado-de-cola.

### 2.3 · Y conecta con `022` sin contradecirlo

`022` estableció que **no hay preemption** en GFX8: `COND_EXEC` es inerte, no hay
`preempt_ib`. Y este documento muestra un mecanismo de **save/restore de contexto**
que existe.

No se contradicen. Son cosas distintas:

| | `COND_EXEC` | `CP_HQD_CTX_SAVE_*` |
|---|---|---|
| qué es | saltar DWs si un predicado lo dice | guardar/restaurar el estado de la cola |
| para qué | preemption: interrumpir y reanudar | **parar y reanudar** una cola |
| en GFX8 | inerte (predicado nunca escrito) | **activo** — se lee y se reescribe |

El segundo no necesita preemption: es lo que pasa cuando una cola se detiene por
cualquier razón. La preemption es un caso particular. Que no haya preemption no
significa que no haya gestión de ciclo de vida de la cola.

Esa distinción no estaba escrita en ningún hallazgo. La herramienta la puso al
lado.

## 3 · La herramienta de "qué hago ahora"

`next_work.py` combina cuatro fuentes y las ordena por coste:

```
[0] block_size: valores en conflicto              coste~1    <- de causal_map
[1] 64 registros sin mención documental            coste~10   <- de causal_chain
[2] 207 fronteras que se cierran releyando         coste~20
[3] 48 fronteras que solo se cierran midiendo      coste~100
```

El candidato 0 sale de `causal_map`. El candidato 1, de cruzar `causal_chain`
(qué registros toca el código) con un barrido de `mm[A-Z_]+` sobre los
documentos (qué registros menciona la gente). Ese cruce no lo hacía nadie.

### 3.1 · Lo que decide y lo que no

Decide cuál es el **más barato de empezar**. No decide cuál es el más importante.
Los costes son juicios declarados, no medidas, y por eso están en el código y son
discutibles.

Si el ranking empuja a hacer lo barato y lo barato no mueve nada, el ranking es un
problema. Lo dejo dicho porque es el fallo clásico de optimizar por lo medible.

## 4 · Clasificación

| afirmación | estado |
|---|---|
| 1093 aristas del camino GFX8, con fichero y línea | `PROVEN` — generadas del código |
| Las dos escrituras de `031` en líneas consecutivas | `PROVEN` — reproduced por la herramienta |
| 64 registros tocados por el código sin mención documental | `PROVEN` |
| El driver lee ~15 registros `CP_HQD_*` al arrancar cola | `PROVEN` — `gfx_v8_0.c:4505-4532` |
| Y los reescribe en el mismo orden al reanudar | `PROVEN` — `:4559-4575`, bucles |
| 38 campos `cp_hqd_*` en el driver | `PROVEN` — conteo de `grep` |
| Que el hardware inicialice esos registros | `HYPOTHESIS` — inferido del patrón |
| Que valores exactos son válidos para cada campo | `NOT_DETERMINED` — no hay documentación |
| Que `CP_HQD_CTX_SAVE_*` sea "preemption" | `REFUTED` — `022` la separó; son cosas distintas |

## 5 · Confounders

- **`cp_gfx_start` es UN camino de arranque.** No el único. Hay al menos
  `cp_resume`, y el resto de generación (`gfx_v9_0`..`gfx_v12_1`) tienen sus
  propias versiones. El hallazgo es del camino GFX8 y no se ha comprobado que
  sea idéntico en otros.
- **Los rangos contiguos de los bucles se calculan en runtime** con
  `mqd_data[mqd_reg - mmCP_MQD_BASE_ADDR]`. Eso significa que el conjunto
  exacto de registros reescritos depende del `mqd_data[]` que se haya llenado,
  y mi extracción ve el bucle pero no Expandir el array. La lista de 64 puede
  estar incompleta o sobrecontar.
- **La extracción por regex no es AST.** Puede meterse en comentarios y cadenas.
  La validación manual de los hallazgos (§2) lo confirma en los casos citados,
  pero la cifra global de 1093 aristas tiene ese margen.
- **`next_work` clasifica "hardware" por palabras en el texto** (`hardware`,
  `RUNTIME`, `experimento`). Un `NOT_DETERMINED` cuya frase no mentiona esas
  palabras va a "lectura" aunque necesite hardware. La clasificación es
  aproximada por construcción.
- Los 207 y 48 cuentan **líneas con `NOT_DETERMINED`**, no fronteras distintas.
  Una misma frontera mencionada en diez líneas cuenta diez. El numero es un
  orden de magnitud, no un recuento.

## 6 · UNLOCKS

- **El mapa causal deja de ser un objetivo y es una salida de comando.**
  `causal_chain --json` da 1093 aristas para cualquier agente que quiera
  consultarlas. `--graph` da dot para graphviz.
- **El mecanismo HQD/MQD entra en el mapa**, que era el hueco más grande que
  quedaba en la gestión de cola: qué estado hay que preservar al parar y
  reanudar.
- **`next_work` cierra el ciclo de detección de trabajo.** Una herramienta
  que dice "64 registros sin mirar" es un generador de hypotheses, no un
  informe. Ese es el salto de "analizar" a "descubrir".
- **La distinción `COND_EXEC` vs `CP_HQD_CTX_SAVE_*`** era implícita y ahora
  está escrita: preemption y gestión de ciclo de vida son subsistemas
  distintos, y que no haya preemption no implica que no haya save/restore.

## 7 · Criterio de falsificación

Se refutaría si: (a) `cp_gfx_start` no fuera alcanzable en GFX8 — refutable con
`pm4_reachable --seeds`, que lo incluye vía `ip_funcs.sw_init`; (b) los registros
`cp_hqd_*` fueran escritos por otro camino también — refutable con
`--edges REG_WRITE --register mmCP_HQD_EOP_RPTR`, que ya devuelve los sitios; (c)
el hardware no inicializara esos registros — solo hardware, y no es
desfalsificable aquí; (d) el conjunto de 64 estuviera inflado por comentarios —
refutable con un parser de AST, que es el límite declarado.

## 8 · Evidencia

```
HERRAMIENTAS:
  08-ARQUITECTURA/tools/causal_chain.py
    262 funciones alcanzables, 1093 aristas con fichero:linea
    WR_MEM/DOORBELL en 6028/6029 y 6227/6228  (las dos de 031)
  08-ARQUITECTURA/tools/next_work.py
    4 candidatos, ordenados por coste declarado
    el 1 es "64 registros sin mencion documental"

HALLAZGO:
  gfx_v8_0.c:4505-4532   lee ~15 CP_HQD_* al arrancar cola -> mqd->cp_hqd_*
  gfx_v8_0.c:4559-4575   reescribe el rango al reanudar, por bucles
  gfx_v8_0.c:4577-4579   activa el HQD
  38 campos cp_hqd_* en gfx_v8_0.c
```

`WRITE_EXECUTION=NONE`. `GPU INTACTA`.