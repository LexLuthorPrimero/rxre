# 036 · El vocabulario PM4 que Polaris12 ejecuta de verdad: 21 paquetes, no 74

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA=08-ARQUITECTURA/tools/pm4_reachable.py` (nueva, validada por mutacion)
`CONTINUES=034` (framing), `033` (framing), `022` (`COND_EXEC` inerte)

## CUDA principal

`sid.h` define **74 opcodes PACKET3** para GFX8. Un `grep PACKET3` da esa impresion y es
falsa: el ASIC **ejecuta 22**, de los cuales **1 no hace nada** y **3 mas son codigo muerto**.
El numero real de paquetes que un driver propio tendria que emitir para este chip es **21**.

La distincion importa porque las tres categorias requieren trabajo distinto:

```
A · se emite y hace algo ............ 21   <- el trabajo real
B · se emite y es no-op .............  1   <- COND_EXEC
C · emitido, nunca alcanzado ........  3   <- solo en amdgpu_gfx.c
D · otro ASIC ...................... 208 emisiones, no son codigo muerto
```

Un inventario construido con `grep` no distingue A de B. **Un paquete puede estar en cada
submit y ser un no-op**, y contarlo como necesario es trabajo desperdiciado: no porque el
paquete sobre, sino porque su predicado nunca se escribe.

## Alcance exacto

1. Alcanzabilidad estatica desde las semillas reales de submit, init y teardown.
2. Separar emitido-de-hecho de emitido-inerte.
3. Excluir las otras generaciones, que es una falsa afirmacion fácil de construir.
4. Validar la herramienta por mutacion.

## Criterio de terminacion (cumplido)

Herramienta construida, mutacion validada, corpus restaurado e intacto, y las cuatro
categorias medidas. Agotado.

---

## 1 · El metodo: alcanzabilidad, no busqueda

ElIndices de funciones cubre `8374` funciones en `amdgpu/*.c` y `145` opcodes definidos
entre todas las cabeceras. Las semillas son **unicamente punteros de tablas**, en tres
familias:

| familia | punteros | para que |
|---|---|---|
| `ring_funcs` de GFX8 | 46 (3 tablas: gfx, compute, kiq) | el camino de envio |
| `amd_ip_funcs` de GFX8 | 17 | init, suspend, resume, hw_fini |
| genericas del submit | 5 | `amdgpu_ring_commit`, `amdgpu_ib_*`, `amdgpu_fence_*` |

BFS sobre las llamadas. Resultado: **262 funciones alcanzables**.

### 1.1 · Por que las semillas son punteros y no nombres

`gfx_v8_0_early_init`, `gfx_v8_0_resume` y `gfx_v8_0_hw_fini` **no los llama nadie por
nombre**. Verificado: `grep` fuera de `gfx_v8_0.c` no encuentra ninguna llamada. Se invocan
a traves de `struct amd_ip_funcs gfx_v8_0_ip_funcs` (`gfx_v8_0.c:6849-6868`).

Consecuencia que no es academica: **las tres fases del ciclo de vida —arranque, envio y
apagado— no tienen ni una arista de llamada directa entre ellas.** Un indexador que solo
buscase llamadas las perderia las tres enteras, y con ellas los paquetes de arranque y de
apagado: `SET_RESOURCES`, `MAP_QUEUES` y `UNMAP_QUEUES`.

## 2 · Categoria A — lo que el chip ejecuta de verdad

21 opcodes, con valor resuelto desde la cabecera correcta:

```
0x11 SET_BASE            x1    gfx_v8_0.c:4184      ┐
0x12 CLEAR_STATE         x1    gfx_v8_0.c:4180      │ inicio de cola
0x28 CONTEXT_CONTROL     x2    gfx_v8_0.c:6311      ┘
0x37 WRITE_DATA          x9    gfx_v8_0.c:5123     Registers
0x3C WAIT_REG_MEM        x3    gfx_v8_0.c:6180      ┐
0x3F INDIRECT_BUFFER     x1    gfx_v8_0.c:6125      │
0x40 COPY_DATA           x1    gfx_v8_0.c:6337      │ envio
0x42 PFP_SYNC_ME         x1    gfx_v8_0.c:6212      │
0x43 SURFACE_SYNC        x1    gfx_v8_0.c:6763      │
0x46 EVENT_WRITE         x2    gfx_v8_0.c:6060      │
0x47 EVENT_WRITE_EOP     x2    gfx_v8_0.c:6145      │
0x49 RELEASE_MEM         x1    gfx_v8_0.c:6239      ┘
0x4A PREAMBLE_CNTL       x2    gfx_v8_0.c:4151      inicio
0x58 ACQUIRE_MEM         x1    gfx_v8_0.c:6763      envio
0x68 SET_CONFIG_REG      x1    gfx_v8_0.c:6120      ┐
0x69 SET_CONTEXT_REG     x1    gfx_v8_0.c:4172      │
0x79 SET_UCONFIG_REG     x1    gfx_v8_0.c:850       │
0x8B SWITCH_BUFFER       x1    gfx_v8_0.c:6279      ┘
0xA0 SET_RESOURCES       x1    gfx_v8_0.c:4331      ┐
0xA2 MAP_QUEUES          x1    gfx_v8_0.c:4345      │ KIQ
0xA3 UNMAP_QUEUES        x1    gfx_v8_0.c:4773      ┘ apagado
```

`SET_UCONFIG_REG` esta en `gfx_v8_0.c:850`, muy al principio del fichero, en la funcion que
escribe la configuracion de numero de anillos. Es el unico opcode efectivo cuya unica
emision esta fuera de la zona de "emit_*" de la tabla de anillos.

### 2.1 · Los tres que vienen del KIQ, y por que son la parte no obvia

`SET_RESOURCES`, `MAP_QUEUES` y `UNMAP_QUEUES` son el **protocolo de instalacion de
colas**, y viven en el KIQ, no en los rings de usuario:

- `SET_RESOURCES` + `MAP_QUEUES` → `gfx_v8_0_kiq_kcq_enable` → arranque/resume
- `UNMAP_QUEUES` → `gfx_v8_0_kcq_disable` → `gfx_v8_0_hw_fini` → **apagado**

Es la conclusion de mayor valor para el driver propio: **sin estos tres el hardware no tiene
una cola que ejecutar**, y `UNMAP_QUEUES` pertenece a una fase del ciclo de vida distinta de
las otras dos. Un diseno que solo implemente "emitir trabajo" no los tiene.

## 3 · Categoria B — emitido e inerte

```
0x22 COND_EXEC   x1   gfx_v8_0.c:6321   en gfx_v8_0_ring_emit_init_cond_exec
```

La funcion esta cableada (`.init_cond_exec`, `gfx_v8_0.c:6910`) y se llama en cada submit
desde `amdgpu_ib.c:246-247` y `amdgpu_vm.c:839-840`. Se emite, en serio:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_COND_EXEC, 3));
amdgpu_ring_write(ring, lower_32_bits(addr));
amdgpu_ring_write(ring, upper_32_bits(addr));
/* discard following DWs if *cond_exec_gpu_addr==0 */
amdgpu_ring_write(ring, 0);
```

`F = 3` con 4 dwords de datos: coherente con la convencion de `034`.

Y sin embargo **no hace nada**, por `022`: el predicado que lee el hardware vive en
`cond_exe_gpu_addr`, y el unico que escribe ese valor es `set_preempt_cond_exec`, cuyos
consumidores son:

```
gfx_v9_0.c  gfx_v10_0.c  gfx_v11_0.c  gfx_v12_0.c
sdma_v5_0.c  sdma_v5_2.c  sdma_v6_0.c  sdma_v7_0.c  sdma_v7_1.c
amdgpu_vpe.c
```

**cero en el path GFX8** (`gfx_v8_0.c`, `amdgpu_gfx.c`, `gmc_v8_0.c`, `cikd.c`: 0). Verificado
de nuevo en esta ronda.

### 3.1 · La distincion que este hallazgo establish

> **"Esta en el vocabulario vivo" y "hace algo" son dos preguntas distintas.**

Mi herramienta y `022` no se contradicen: miden cosas diferentes. La herramienta mide si un
paquete **llega al hardware**; `022` mide si **tiene efecto**. Un paquete puede estar en cada
submit y ser un no-op.

`022` usa la palabra "inerte", no "ausente", y es la palabra correcta. Este documento confirma
que es distinto de ausente.

## 4 · Categoria C — codigo muerto en este ASIC

```
0x12 CLEAR_STATE       x1   amdgpu_gfx.c:2544
0x28 CONTEXT_CONTROL   x1   amdgpu_gfx.c:2495
0x4A PREAMBLE_CNTL     x2   amdgpu_gfx.c:2492
```

Los tres en `amdgpu_gfx.c`, en el emisor generico de preamble. Coherente con `022`: el
preamble IB es parte del protocolo de preemption, y GFX8 no preempte.

**Ojo con el detalle:** `CLEAR_STATE`, `CONTEXT_CONTROL` y `PREAMBLE_CNTL` aparecen **a la
vez** en A y en C. Son el mismo opcode con dos sitios de emision: uno en `gfx_v8_0.c`
alcanzable, otro en `amdgpu_gfx.c` inalcanzable. La herramienta clasifica por
`(opcode, fichero)`, no por opcode. Es correcto y hay que leerlo asi: **el opcode se usa,
pero la variante generica no se ejecuta en este ASIC.**

## 5 · Las cuatro correcciones que la herramienta me hizo

Las cuatro son defectos reales mios, y las cuatro salieron de construir la herramienta — no
de leerla con mas cuidado.

### 5.1 · La lista de "muertos" contaminada por otras generaciones

Primera version: "NO ALCANZABLE" listaba 31 opcodes, casi todos de `gfx_v10_0.c` y
`gfx_v11_0.c`. Esos son **otros ASICs**: son inalcanzables desde semillas GFX8 *por
definicion*, no por estar muertos. Meterlos en una lista llamada "no alcanzable" presenta una
falsa afirmacion de la clase que mas dano hace: invita a concluir que un paquete no se usa
cuando en realidad lo usa otra generacion. Corregido: 31 → 3, con 208 emisiones de otras
generaciones apartadas y etiquetadas.

### 5.2 · `MAP_QUEUES` reportado como muerto, siendo el paquete mas importante

Con solo `ring_funcs_gfx` y `ring_funcs_compute` sembradas, la herramienta reporto
`MAP_QUEUES` y `UNMAP_QUEUES` como codigo muerto. Es absurdo —`MAP_QUEUES` es lo que instala
la cola en el hardware— y por eso fue util.

Causa: el KIQ tiene su propia tabla, `gfx_v8_0_ring_funcs_kiq` (`:6951`), que no sembre.
Anadida.

### 5.3 · La ruta de instalacion de colas no pasa por ningun `ring_funcs`

Anadido el KIQ, `MAP_QUEUES` seguia muerto. Causa de fondo, que no es un bug sino una
propiedad del diseno:

```
gfx_v8_0_kcq_resume  ->  gfx_v8_0_kiq_kcq_enable  ->  MAP_QUEUES
```

Es un camino de **init/resume**, no de submit. Un inventario de PM4 que solo mire el envio
informa mal **por construccion**: omite la palabra que enciende el motor. Por eso las
semillas tienen tres familias.

### 5.4 · La herramienta era insensible justo a lo que debe medir

Con las hojas sembradas directamente (`kiq_kcq_enable`, `kcq_init_queue`, `ring_init`),
rompi la arista `kcq_resume -> kiq_kcq_enable` y **el resultado no cambio**: la hoja estaba
sembrada y se alcanzaba igual. La prueba de mutacion no detectaba nada porque la herramienta
no distinguia esos casos.

Corregido: las semillas son solo punteros de nivel superior. Con el mutante la respuesta pasa
de 21 a 19 efectivos y `MAP_QUEUES` y `SET_RESOURCES` caen a la lista de muertos.

### 5.5 · Y lo que la correccion revelo: mi lista de muertos era un artefacto

Al sembrar bien, las funciones alcanzables suben de 152 a **262**, y de la lista de muertos
salen `SET_BASE` y `CLEAR_STATE` de `gfx_v8_0.c` —que pasan acategory A. Esos dos no estaban
muertos; mi siembra no los alcanzaba. **Lo que yo iba a publicar como codigo muerto era un
artefacto de mi propia herramienta.**

## 6 · Validacion por mutacion

Mutante: `gfx_v8_0.c`, la llamada `return gfx_v8_0_kiq_kcq_enable(adev);` deja de resolver.

```
                sin mutante   con mutante
alcanzables        262           261
efectivos (A)       21            19
muertos en GFX8      3             5     <- +SET_RESOURCES +MAP_QUEUES
```

La herramienta **saca** del inventario lo que deja de ser alcanzable, con el recuento
correcto. Restaurado el corpus y comprobado: 21/1/3, y `git status --porcelain RESEARCH/`
vacio. **`GPU INTACTA`, `MODIFICATIONS 0` sobre el corpus.**

Segunda comprobacion: `pm4_layout_audit.py --only=gfx_v8_0` confirma que el unico paquete con
layout documentado **en el path GFX8** es `MAP_QUEUES`, y que es conforme. Los demas de los
7 opcodes documentados son de v9+.

## 7 · Clasificacion

| afirmacion | estado |
|---|---|
| 74 opcodes PACKET3 en `sid.h` (80 defines − 6 offsets) | `PROVEN` — contabilidad §10 |
| 22 alcanzables desde las semillas de este ASIC | `PROVEN` — alcanzabilidad estatica |
| 21 de esos hacen algo | `PROVEN_DERIVED` — por exclusion de la categoria B |
| `COND_EXEC` se emite pero es no-op | `PROVEN` — `022`, reverificado |
| 3 emisiones muertas en este ASIC, todas en `amdgpu_gfx.c` | `PROVEN` |
| Las tres fases del ciclo de vida no tienen aristas directas entre si | `PROVEN` — solo punteros |
| 208 emisiones de otras generaciones, no son codigo muerto | `PROVEN` |
| Que el inventario este **completo** | `NOT_DETERMINED` — ver §8 |
| Que `SET_UCONFIG_REG` solo se emita una vez en todo el ASIC | `OBSERVATION` de la herramienta |

## 8 · Confounders

- **El corpus es parcial y eso es una falsa negativa garantizada.** No hay `display/`, `dc/`,
  `amdkfd/`, `ttm/`, `vcn/`, `jpeg/`. `296` nombres llamados no resuelven; los mas citados
  son `amdgpu_ring_write` (desde 23 funciones) y `lower_32_bits` (desde 15), que son helpers
  sin clave. **Un paquete alcanzable solo desde una ruta de display apareceria como
  "muerto", y eso es un falso negativo.** El estado correcto del inventario es
  `PROVEN` para el subgrafo del kernel, y `NOT_DETERMINED` como inventario del ASIC.
- **La alcanzabilidad es sobreaproximada en un punto concreto:** una funcion alcanzable no
  significa que su rama se ejecute. Un `if` cuya condicion es falsa en esta placa marca la
  funcion como alcanzable. El unico filtro semantico del que dispongo es la categoria B
  (inertes afirmadas a mano), y solo lo he poblado con `COND_EXEC`. **Puede haber mas
  inertes que no conozco.** Ese es el limite honesto de este documento.
- **`KNOWN_INERT` esta afirmado, no calculado.** No hay forma automatica de deducir que un
  paquete es un no-op: requiere saber que su predicado nunca se escribe. Poblado a mano con
  `022` como fuente.
- Los 21 son **sitios de emision en el kernel**, no 21 secuencias distintas. `WRITE_DATA`
  aparece 9 veces porque lo emite `emit_wreg` con argumentos distintos; el driver propio
  necesita **una** forma de emitirlo, no nueve. El numero 21 mide **vocabulario**, no
  trabajo de implementacion.
- La lista C clasifica por `(opcode, fichero)`. Que `CONTEXT_CONTROL` salga en A y en C no es
  una contradiccion: son dos sitios de emision distintos del mismo opcode.

## 9 · UNLOCKS

- **El conjunto de trabajo del driver propio queda acotado en 21 paquetes**, con su valor y
  su funcion de origen. Es la entrada de `DESIGN_FREEDOM` mas concreta de la serie:
  `008-c-scheduler-ring` y `016-gfx8-submission-contract` dejan de tener que deducirlo.
- **Se separa la palabra que enciende el motor del trabajo que se le envia.**
  `SET_RESOURCES` + `MAP_QUEUES` son arranque, `UNMAP_QUEUES` es apagado, y el resto es envio.
  Un diseno que solo implemente envio no arranca.
- **`COND_EXEC` se puede descartar con justificacion medida** en lugar de supuesta: se
  emite y no hace nada porque su unico escritor no existe en GFX8. Eso **elimina un paquete
  del conjunto de trabajo y dos slots del writeback** (`cond_exe_offs`), cerrando el
  `UNLOCKS` de `022` con el mecanismo exacto.
- **La categoria de "inerte" queda establecida como categoria de primera clase** en la
  contabilidad de paquetes. Es la que un `grep` no puede ver y la que mas trabajo
  desperdiciado genera.
- **Herramienta reutilizable para cualquier ASIC del arbol:** cambiando las tres familias de
  punteros semilla, el mismo analysis da el vocabulario de GFX9, GFX10, NV10. Y con el
  mutante de `034` hay ya dos herramientas con validacion negativa.
- **La leccion de metodo de esta ronda, y es la misma de siempre con dos
  variantes:** ninguno de los cuatro defectos salio leyendo mas. Salieron porque un numero
  era absurdo (`MAP_QUEUES` muerto), porque un mutante no cambio nada, o porque una lista
  tenia duplicados que no podia tener. **La comprobacion que falla es la que informa.**

## 10 · Criterio de falsificacion

Se refutaria si: (a) un paquete emitible solo desde `display/` o `dc/` no apareciera en las
categorias A/B/C — refutable con el corpus completo, o con los modulos listados en
`/proc/modules` y sus simbolos; (b) `gfx_v8_0_kiq_kcq_enable` fuera alcanzable por una ruta
distinta de `kcq_resume` que la herramienta no viera — refutable con un punto de corte en
`/sys/kernel/debug/tracing`, que ya sabemos que no es legible en esta maquina, luego
`NOT_DETERMINED` en esta host; (c) quedara algun otro paquete inerte sin detectar — refutable
solo leyendo la semantica de cada uno de los 21, que es trabajo de hardware y `033` ya
establecio que no hay documento que lo cubra; (d) el conteo de 74 no fuera el numero de opcodes de
GFX8. **COMPROBADO, con la contabilidad exacta:**

```
defines PACKET3_* con valor literal en sid.h ....... 80
  de ellos, offsets de registro _START/_END ........  6   (lineas 524-533)
  opcodes .......................................... 74
  rango de valores ................................. 0x10 .. 0x8B
  Extension: contiguos, lineas 343-550, con los 6
  offsets intercalados dentro
```

Los 6 offsets son `SET_CONFIG_REG_START/END`, `SET_CONTEXT_REG_START/END` y
`SET_SH_REG_START/END`: **no son opcodes**, son offsets de registro, y sus valores
(`0x2000`, `0xa000`, `0x2c00`) estan en el rango de offsets, no en el de opcodes. Es el
mismo error que casi me invalida la prediccion de freedreno en `033` §4.1.

`(d)` queda por tanto `PROVEN`. Lo que **no** es `PROVEN` es que ese sea el conjunto
completo de opcodes que GFX8 puede decodificar: `sid.h` es la cabecera del bloque
CIK/VI y GFX8 toma de ella lo que necesita, pero un opcode decodificable por el hardware y
sin definir aqui seria invisible para esta herramienta. Eso no tiene respuesta en el
corpus.

## 11 · Evidencia

```
HERRAMIENTA:
  08-ARQUITECTURA/tools/pm4_reachable.py
    funciones indexadas en amdgpu/*.c : 8374
    opcodes PACKET3 definidos (todas cabeceras) : 145
    semillas : 46 ring_funcs + 17 ip_funcs + 5 genericas = 68
    alcanzables : 262
    resultado : A=21  B=1  C=3  D=208

VALIDACION NEGATIVA:
  mutante gfx_v8_0.c: return gfx_v8_0_kiq_kcq_enable -> _MUTADO
    21 -> 19 efectivos, +MAP_QUEUES +SET_RESOURCES a muertos
  restaurado -> 21/1/3, git status --porcelain RESEARCH/ vacio

CORROBORACION:
  pm4_layout_audit.py --only=gfx_v8_0
    unico opcode con layout documentado en el path GFX8 = MAP_QUEUES, conforme

CODIGO:
  gfx_v8_0.c:6849-6868   amd_ip_funcs: 17 punteros de ciclo de vida
  gfx_v8_0.c:6870,6916,6951  ring_funcs_gfx / _compute / _kiq
  gfx_v8_0.c:6910       .init_cond_exec = gfx_v8_0_ring_emit_init_cond_exec
  gfx_v8_0.c:6315-6329  emision de COND_EXEC (F=3, 4 datos)
  gfx_v8_0.c:4331,4345,4773  SET_RESOURCES / MAP_QUEUES / UNMAP_QUEUES
  amdgpu_ib.c:246-247    llamada a init_cond_exec en el submit
  amdgpu_vm.c:839-840    llamada a init_cond_exec en el vm flush
  set_preempt_cond_exec: 10 ficheros, 0 en el path GFX8
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU. `GPU INTACTA`.