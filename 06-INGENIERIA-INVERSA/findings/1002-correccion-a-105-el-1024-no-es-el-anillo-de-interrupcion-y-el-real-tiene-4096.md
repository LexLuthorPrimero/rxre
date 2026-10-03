# 1002 · Corrección a `105`: el `1024` de `gfx_v8_0.c:1875` no es un anillo de interrupción, y el anillo de IH real tiene 4096 entradas

```
CLASSIFICATION=CORRECTION+DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
WRITE_EXECUTION=NONE · MODIFICATIONS=0 (el corpus no se toca)
RUNTIME=NOT_RUN · GPU INTACTA · SIN MMIO · SIN ESCRITURA A REGISTROS
CORRECTS=105-se-ih-y-el-camino-real-de-los-faults.md
CONTINUES=051-interrupt-vector-iv-gfx8-y-teardown-lifo.md
CONTINUES=096-se-mecanismo-de-fence-completo.md
AUTORIA=AGENTE-19 (AGENT-19, interrupts / IH / fences)
```

## Qué corrige

`105` afirmo, y lo marco **`PROVEN`** en su tabla de cierre:

> «EOP tiene un anillo dedicado de 1024 entradas» — `PROVEN` (`gfx_v8_0.c:1875`)
> «**1024 entradas, no una IRQ simple.** Es un anillo de interrupciones.»

**Es falso, y por dos motivos independientes.** El `1024` no es el tamaño de nada
relacionado con interrupciones, y el anillo de interrupción que sí existe en esta
GPU tiene **4096 entradas**, no 1024.

Además, en el mismo bloque de código `105` cita dos nombres de `SRCID` que no
existen y cuenta mal las fuentes registradas: **cinco, no tres**.

Lo que **no** se cae es lo demás de `105`, que es lo valioso: que
`gfx_v8_0_eop_irq` es quien llama a `amdgpu_fence_process`, que la IRQ selecciona el
anillo por `ring_id`, y que los faults van a `drm_sched_fault`. Eso queda intacto y
esta corroborado aqui.

## 1 · Qué es el `1024` de `gfx_v8_0.c:1875`

La firma del receptor dice qué es el tercer argumento:

```
amdgpu_ring.c:217   * @max_dw: maximum number of dw for ring alloc
amdgpu_ring.c:226   int amdgpu_ring_init(struct amdgpu_device *adev, struct amdgpu_ring *ring,
amdgpu_ring.c:227   		     unsigned int max_dw, struct amdgpu_irq_src *irq_src,
```

Y qué hace con él:

```
amdgpu_ring.c:339   	ring->ring_size = roundup_pow_of_two(max_dw * 4 * sched_hw_submission);
amdgpu_ring.c:341   	ring->ring_size = roundup_pow_of_two(max_dw * 4);
amdgpu_ring.c:375   	ring->max_dw = max_dw;
```

`1024` son **dwords del buffer de comandos del ring**. `ring_size` sale de
`1024 * 4 = 4096` bytes. **No tiene nada que ver con interrupciones.**

Y la llamada vive dentro de la inicialización del ring de **compute**:

```
gfx_v8_0.c:1846   static int gfx_v8_0_compute_ring_init(struct amdgpu_device *adev, int ring_id,
gfx_v8_0.c:1866   	sprintf(ring->name, "comp_%d.%d.%d", ring->me, ring->pipe, ring->queue);
gfx_v8_0.c:1875   	r = amdgpu_ring_init(adev, ring, 1024, &adev->gfx.eop_irq, irq_type,
```

## 2 · La prueba que lo cierra: el cuarto argumento

El cuarto argumento es `struct amdgpu_irq_src *irq_src`, y `&adev->gfx.eop_irq` es
un `struct amdgpu_irq_src` **a secas**:

```
amdgpu_gfx.h:464   	struct amdgpu_irq_src		eop_irq;
```

Y ese tipo **no tiene ningún campo de anillo**:

```
amdgpu_irq.h:62   struct amdgpu_irq_src {
amdgpu_irq.h:63   	unsigned				num_types;
amdgpu_irq.h:64   	atomic_t				*enabled_types;
amdgpu_irq.h:65   	const struct amdgpu_irq_src_funcs	*funcs;
amdgpu_irq.h:66   };
```

Tres campos: un entero, un puntero y un puntero a función. **No hay `ring`, no hay
`ring_size`, no hay `ptr_mask`.** La afirmación de `105` es *estructuralmente
imposible*: no cabe un anillo de 1024 entradas en un struct de dos punteros.

Y hay un contraargumento mejor que además cierra la intención: **la misma llamada,
con el mismo `1024` y el mismo `eop_irq`, inicializa el ring GFX.**

```
gfx_v8_0.c:1977   		r = amdgpu_ring_init(adev, ring, 1024, &adev->gfx.eop_irq,
gfx_v8_0.c:1978   				     AMDGPU_CP_IRQ_GFX_ME0_PIPE0_EOP,
```

Un solo `struct amdgpu_irq_src eop_irq` está compartido por el ring GFX **y** por
todos los rings de compute. Si `1024` fuera un anillo de interrupción dedicado al
EOP, el ring GFX y los de compute no podrían apuntar al mismo objeto con el mismo
número. **`eop_irq` es el destino del enrutado de IRQ de esos rings, no un anillo.**

Las dos llamadas:

| linea | ring | `max_dw` | `irq_src` | `irq_type` |
|---|---|---|---|---|
| 1875 | `comp_%d.%d.%d` (compute) | 1024 | `&adev->gfx.eop_irq` | `AMDGPU_CP_IRQ_COMPUTE_MEC1_PIPE0_EOP + …` |
| 1977 | `gfx` | 1024 | `&adev->gfx.eop_irq` | `AMDGPU_CP_IRQ_GFX_ME0_PIPE0_EOP` |

## 3 · El anillo de interrupción que sí existe: 64 KiB, 4096 entradas

El anillo de IH de esta GPU lo inicializa `tonga_ih.c` — que `051` ya identifico
como el bloque real pese a que el log diga `<ih_v3_0_0>`:

```
tonga_ih.c:311   	r = amdgpu_ih_ring_init(adev, &adev->irq.ih, 64 * 1024, true);
```

Aritmética, con el codigo que la hace:

```
amdgpu_ih.c:49    	rb_bufsz = order_base_2(ring_size / 4);
amdgpu_ih.c:50    	ring_size = (1 << rb_bufsz) * 4;
amdgpu_ih.c:51    	ih->ring_size = ring_size;
amdgpu_ih.c:52    	ih->ptr_mask = ih->ring_size - 1;
```

```
tonga_ih.c:125   	rb_bufsz = order_base_2(adev->irq.ih.ring_size / 4);
tonga_ih.c:127   	ih_rb_cntl = REG_SET_FIELD(ih_rb_cntl, IH_RB_CNTL, RB_SIZE, rb_bufsz);
```

| magnitud | valor |
|---|---|
| `ring_size` | `64 * 1024` = **65536 bytes** |
| `RB_SIZE` (campo de `IH_RB_CNTL`) | `order_base_2(16384)` = **14** |
| `ptr_mask` | `0xffff` |
| **entradas IV de 16 B** | **4096** |
| reserva real (`dma_alloc_coherent`) | 65544 B = anillo + 8 de sombras |

**4096 entradas, no 1024.** Con la reserva de 8 bytes:

```
amdgpu_ih.c:65    	ih->ring = dma_alloc_coherent(adev->dev, ih->ring_size + 8,
amdgpu_ih.c:71    	ih->wptr_addr = dma_addr + ih->ring_size;
amdgpu_ih.c:73    	ih->rptr_addr = dma_addr + ih->ring_size + 4;
```

Contraste con las otras IH del árbol, que usan una constante mayor — `64 KiB` es
**específico de Tonga**, no un valor común:

```
amdgpu_ih.h:30   	#define IH_RING_SIZE	(256 * 1024)      <- ih_v6_0/6_1/7_0, vega, navi
tonga_ih.c:311   	amdgpu_ih_ring_init(adev, &adev->irq.ih, 64 * 1024, true)   <- ESTA GPU
cik_ih.c:313 / cz_ih.c:302 / iceland_ih.c:301   	64 * 1024, false
```

**Para un driver propio, la cifra que importa es 4096 y su consecuencias:** un
anillo de 4096 entradas de 16 B aguanta 4096 vectores sin que el host los recoja.
A la tasa de fences medida en `098` (138/s) eso son ~30 s de producto grande sin
recoger antes de que el hardware marque `RB_OVERFLOW` — que `051` §4 ya describio:
descarta vectores y el driver lo asume con un "Hopefully" textual. **El margen
depende de un número que `105` conto mal por un factor de 4.**

### Y el mapa de tipos de interrupción: cinco, no tres

`105` dice «los IDs de fuente que se registran son tres». Los cinco `amdgpu_irq_add_id`
de la `sw_init` de GFX8 son:

```
gfx_v8_0.c:1914   VISLANDS30_IV_SRCID_CP_END_OF_PIPE       -> &adev->gfx.eop_irq
gfx_v8_0.c:1919   VISLANDS30_IV_SRCID_CP_PRIV_REG_FAULT    -> &adev->gfx.priv_reg_irq
gfx_v8_0.c:1925   VISLANDS30_IV_SRCID_CP_PRIV_INSTR_FAULT  -> &adev->gfx.priv_inst_irq
gfx_v8_0.c:1931   VISLANDS30_IV_SRCID_CP_ECC_ERROR         -> &adev->gfx.cp_ecc_error_irq
gfx_v8_0.c:1937   VISLANDS30_IV_SRCID_SQ_INTERRUPT_MSG     -> &adev->gfx.sq_irq
```

**Cinco registros, cinco `irq_funcs`, uno por fuente.** `105` conto cinco `irq_funcs`
y despues conto tres `add_id` de los cinco que estan a la vista: incoherente con su
propia lista.

Y dos nombres que `105` cita **no existen** en el arbol:

| `105` cita | real |
|---|---|
| `VISLANDS30_IV_SRCID_CP_PRIV_REG` | `…_CP_PRIV_REG_FAULT` |
| `VISLANDS30_IV_SRCID_CP_PRIV_INST` | `…_CP_PRIV_INSTR_FAULT` |

## 4 · El `ack` del anillo: doorbell, no `mmIH_RB_RPTR`

Esto `105` no lo cubre y es la pieza de «acknowledgement» de mi encargo.

```
tonga_ih.c:319   	adev->irq.ih.use_doorbell = true;
tonga_ih.c:320   	adev->irq.ih.doorbell_index = adev->doorbell_index.ih;
```

```
tonga_ih.c:283   	if (ih->use_doorbell) {
tonga_ih.c:285   		*ih->rptr_cpu = ih->rptr;
tonga_ih.c:286   		WDOORBELL32(ih->doorbell_index, ih->rptr);
tonga_ih.c:287   	} else {
tonga_ih.c:288   		WREG32(mmIH_RB_RPTR, ih->rptr);
tonga_ih.c:289   	}
```

**En esta GPU el `rptr` se acusa con una escritura a doorbell MMIO, no escribiendo
`mmIH_RB_RPTR`.** Y la rama `else` está **muerta**, comprobado y no supuesto: en todo
el árbol, `adev->irq.ih.use_doorbell` recibe un valor **once por fichero de IH, siempre
`true`, y nunca `false` en ninguna parte**:

```
ih_v6_0.c:595   	adev->irq.ih.use_doorbell = true;
ih_v6_1.c:570   	adev->irq.ih.use_doorbell = true;
ih_v7_0.c:608   	adev->irq.ih.use_doorbell = true;
tonga_ih.c:319  	adev->irq.ih.use_doorbell = true;      <- ESTA GPU
navi10_ih.c:577 	adev->irq.ih.use_doorbell = true;
vega10_ih.c:497 	adev->irq.ih.use_doorbell = true;
vega20_ih.c:588 	adev->irq.ih.use_doorbell = true;
```

`grep` de toda forma `use_doorbell *=` sobre `*.c` no devuelve **ninguna**
asignación a `false`, y `amdgpu_irq_init` no toca el campo. Para Polaris12 el `ack`
es **inequívocamente** la puerta.

El `WREG32(mmIH_RB_RPTR, 0)` que `051` §4 localizó en `tonga_ih.c:142` es un *reset*
de arranque, no un *ack*: está en `tonga_ih_irq_init`, antes de que haya nada que
reconocer.

Esto importa para el diseño: **el ack es una escritura volatile a MMIO**, con el
coste y la semántica de orden que implica. Un driver propio que acuse escribiendo
el `rptr` a un buffer de RAM en vez de a la puerta MMIO produce un consumidor
que no avanza: el hardware no lo veria.

Corolario de §5 de `051`: el `wptr` que el host lee es una **sombra en RAM**
(`*ih->wptr_cpu`, `tonga_ih.c:205`), escrita por el hardware vía
`WPTR_WRITEBACK_ENABLE` (`tonga_ih.c:129`). **Asimetría de primer plano: `wptr` por
writeback a RAM, `rptr` por doorbell MMIO.** Los dos lados del anillo se comunican
por mecanismos distintos.

## 5 · Lo que NO se cae de `105`

Re-verificado en esta sesión, contra el mismo corpus:

| afirmación de `105` | estado tras esta sesión |
|---|---|
| 5 fuentes de IRQ, cada una con `.set` y `.process` | `PROVEN` — **corregido el conteo de `add_id`: 5, no 3** |
| `gfx_v8_0_eop_irq` llama a `amdgpu_fence_process` | `PROVEN` — intacto |
| la IRQ selecciona el anillo por `ring_id` (`me`/`pipe`/`queue`) | `PROVEN` — intacto |
| los faults van a `drm_sched_fault` | `PROVEN` — intacto |
| el status de fault se lee en un handler **GMC** | `PROVEN` — intacto |
| `printk_ratelimit` limita a un mensaje | `PROVEN` — intacto |
| el status de `vm_fault_stop` en esta maquina | `OBSERVED` — intacto |
| **«EOP tiene un anillo de 1024 entradas»** | **`REFUTED`** — no existe tal anillo |
| **«los IDs registrados son tres»** | **`REFUTED`** — son cinco |

**Y queda una confusion de fondo que esta sesión cierra.** `105` dio por hecho que el
`1024` era del EOP. No es del EOP **ni de ningun anillo de interrupcion**: es del
buffer de comandos. La conclusión operativa para un driver
propio es que el presupuesto de 1024 dwords del ring GFX y el anillo de IH de 4096
vectores son **dos cosas independientes** que `105` fusionó en una.

## 6 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| el `1024` de `gfx_v8_0.c:1875` es `max_dw` del buffer de comandos | FACT | **PROVEN** (`amdgpu_ring.c:217/339/375`) |
| `ring_size` del ring GFX = `roundup_pow_of_two(1024*4)` = 4096 B | DERIVATION | **PROVEN_DERIVED** |
| `struct amdgpu_irq_src` no tiene campo de anillo | FACT | **PROVEN** (`amdgpu_irq.h:62-66`) |
| `eop_irq` lo comparten el ring GFX y los de compute | FACT | **PROVEN** (`:1875` y `:1977`) |
| el anillo de IH de esta GPU es 64 KiB | FACT | **PROVEN** (`tonga_ih.c:311`) |
| 4096 entradas IV de 16 B, `RB_SIZE`=14, `ptr_mask`=0xffff | DERIVATION | **PROVEN_DERIVED** |
| `64 KiB` es propio de Tonga, no la constante común | DERIVATION | **PROVEN_DERIVED** (`IH_RING_SIZE`=256 KiB) |
| 5 `add_id` registrados, no 3 | CORRECTION | **PROVEN** (`gfx_v8_0.c:1914-1937`) |
| los dos nombres `SRCID` de `105` no existen | CORRECTION | **PROVEN** |
| el `ack` del `rptr` es doorbell MMIO, no `mmIH_RB_RPTR` | FACT | **PROVEN** (`tonga_ih.c:283-289`) |
| `wptr` llega por writeback a RAM, `rptr` sale por doorbell | DERIVATION | **PROVEN_DERIVED** |
| `use_doorbell` es `true` y no lo revierte nadie | FACT | **PROVEN** (7 ficheros, 0 asignaciones a `false`) |
| cuantos overflow reales ocurren en esta maquina | — | **`NOT_DETERMINED`**, y ahora cuantificable |

## Procedencia

- `STATIC` — `gfx_v8_0.c:1846-1879` y `:1966-1983` y `:1905-1940`,
  `amdgpu_ring.c:217-227` y `:336-376`, `amdgpu_ih.c:42-97`,
  `tonga_ih.c:102-150` y `:248-292` y `:306-325`, `amdgpu_irq.h:62-66`,
  `amdgpu_gfx.h:464-469`, `amdgpu_ih.h:30-31`, `amdgpu_drv.c:2041`.
- **Sin RUNTIME.** Sin lectura de la GPU. Sin escrituras. GPU intacta.
- `TARGET_MATCH` re-verificado por la vía estática: `amdgpu_drv.c:2041` mapea
  `0x1002:0x699F` — el ID exacto del `HARDWARE-FINGERPRINT.md` §3 — a
  `CHIP_POLARIS12`. No es un ASIC vecino.
- Encadenada con `051` (layout del IV, overflow), `096` (el fence y su timer de
  respaldo), `098` (tasa de fences medida), `105` (corregida por esta).

## Nota de método

**El fallo de `105` es un fallo de aridad, no de lectura.** Leyó la firma de
`amdgpu_ring_init` — o no la leyó — y vio un `1024` junto a un `eop_irq` en una línea
que habla de IRQ, y concluyo que el `1024` era del anillo de IRQ.

Tres cosas lo habrían parado, y las tres eran estáticas y gratuitas:

1. **el nombre del tercer parámetro** (`max_dw`) y su uso (`ring_size` en bytes);
2. **la cuarta línea de contexto**, que dice `comp_%d.%d.%d` — un ring de compute;
3. **el `sizeof` del tipo**: `struct amdgpu_irq_src` no tiene dónde vivir un anillo.

Las tres son la definición de lo que este proyecto llama `READ_SCOPE_GATE`, y `051`
la aplicó en su §9 precisamente contra cuatro nombres de fichero inventados. **El
mismo gate, aplicado a un parámetro en vez de a un fichero, habria atrapado la
misma clase de error dos findings más tarde.**

Corolario más general: **`105` mezcló el objeto `eop_irq` con el buffer `ring`.**
Son dos cosas distintas que en la misma línea de llamada aparecen uno al lado del
otro, y la línea parece hablar de IRQ porque el otro objeto sí es de IRQ. La
confusión no fue de valores sino de **a qué valor pertenecía cuál.**
