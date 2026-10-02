# 096 · §E: el mecanismo de fence completo, y el host lee memoria del sistema, no MMIO

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

Dominios 19 (`fences`) y 22 (`synchronization / ordering`) del universo de
`AGENTS.md`. Ninguno tenía iteración propia. `094` había visto tres `FENCE` de 12
dwords en el frame GFX y no sabía qué eran; `095` había visto que los motores se
paran en bloque y no sabía cómo se sincronizan.

**Es todo software behaviour, y se reconstruye entero por estática.** Es la
capa que un driver propio necesita para no perder trabajo.

## La emisión: dos EOP, y el segundo es un dummy

```
gfx_v8_0.c:6135   static void gfx_v8_0_ring_emit_fence_gfx(struct amdgpu_ring *ring, u64 addr, u64 seq, unsigned flags)
gfx_v8_0.c:6142       /* Workaround for cache flush problems. First send a dummy EOP
gfx_v8_0.c:6143        * event down the pipe with seq one below.
gfx_v8_0.c:6144        */
gfx_v8_0.c:6145       amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
gfx_v8_0.c:6154       amdgpu_ring_write(ring, lower_32_bits(seq - 1));
gfx_v8_0.c:6159       amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
gfx_v8_0.c:6170       amdgpu_ring_write(ring, upper_32_bits(seq));
```

**Dos `PACKET3_EVENT_WRITE_EOP` de 5 dwords cada uno: primero `seq - 1`, después
`seq`.** El primero es un dummy explícito, y el motivo está escrito: *cache
flush problems*.

Esto es un hecho de hardware filtrado por el driver, no un capricho. La
hipótesis más fuerte que el corpus permite es: **la escritura del valor de fence
tiene que llegar después de que el flush de caché haya ocurrido, y el hardware
compara el valor leído contra el esperado.** Por eso se escribe un valor
distinto primero.

**Y no lo sé con certeza.** Que el kernel lo llame "workaround" significa que
AMD encontró un síntoma, no que publicara la causa. `NOT_DETERMINED`, y
marcado como tal abajo.

Los dos EOP llevan la misma acción, y son tres:

```
gfx_v8_0.c:6146       EOP_TCL1_ACTION_EN | EOP_TC_ACTION_EN | EOP_TC_WB_ACTION_EN
gfx_v8_0.c:6149       EVENT_TYPE(CACHE_FLUSH_AND_INV_TS_EVENT)
gfx_v8_0.c:6150       EVENT_INDEX(5)
```

**`CACHE_FLUSH_AND_INV_TS_EVENT`** — el fence no sólo señala, **vacía caché e
invalida el timestamp**. Eso es la respuesta a por qué hace falta el dummy: el
propio evento muta el estado de caché, y el orden importa.

## Las cuatro banderas, y el fence tiene tres ejes

```
amdgpu_ring.h:62   #define AMDGPU_FENCE_FLAG_64BIT      (1 << 0)
amdgpu_ring.h:63   #define AMDGPU_FENCE_FLAG_INT        (1 << 1)
amdgpu_ring.h:64   #define AMDGPU_FENCE_FLAG_TC_WB_ONLY (1 << 2)
amdgpu_ring.h:67   #define AMDGPU_FENCE_FLAG_EXEC       (1 << 3)  /* preemption or reset */
```

Y cómo se traducen al packet:

```
gfx_v8_0.c:6152   (upper_32_bits(addr) & 0xffff) | DATA_SEL(1) | INT_SEL(0)
gfx_v8_0.c:6168   (upper_32_bits(addr) & 0xffff) | DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0)
gfx_v8_0.c:6165   (exec ? EOP_EXEC : 0)
```

| bandera | campo del packet | efecto |
|---|---|---|
| `64BIT` | `DATA_SEL` 1 → 2 | escribe el seq en 64 bits en vez de 32 |
| `INT` | `INT_SEL` 0 → 2 | genera interrupción, no sólo escritura |
| `EXEC` | `EOP_EXEC` | fuerza ejecución ante preemption o reset |
| `TC_WB_ONLY` | — | **no lo lee `gfx_v8_0_ring_emit_fence_gfx`** |

**Los tres ejes son independientes: interrupt sí o no, 32 o 64 bits, y ejecución
forzada.** Y hay un cuarto owner:

```
amdgpu_ring.h:58   #define AMDGPU_FENCE_OWNER_UNDEFINED  ((void *)0ul)
amdgpu_ring.h:59   #define AMDGPU_FENCE_OWNER_VM         ((void *)1ul)
amdgpu_ring.h:60   #define AMDGPU_FENCE_OWNER_KFD        ((void *)2ul)
```

**`TC_WB_ONLY` existe y GFX8 no lo usa.** Está definido en el cabecero común y
lo consumen otras generaciones. Para esta GPU hay tres flavors de fence, no
cuatro.

## El estado: un ring buffer, no un contador

```
amdgpu_ring.h:118   struct amdgpu_fence_driver {
amdgpu_ring.h:119       uint64_t              gpu_addr;
amdgpu_ring.h:120       uint32_t             *cpu_addr;
amdgpu_ring.h:122       uint32_t              sync_seq;
amdgpu_ring.h:123       atomic_t              last_seq;
amdgpu_ring.h:127       struct timer_list     fallback_timer;
amdgpu_ring.h:128       unsigned              num_fences_mask;
amdgpu_ring.h:130       struct dma_fence     **fences;
```

Y el procesamiento:

```
amdgpu_fence.c:213       do {
amdgpu_fence.c:214           last_seq = atomic_read(&drv->last_seq);
amdgpu_fence.c:215           seq      = amdgpu_fence_read(ring);
amdgpu_fence.c:217       } while (atomic_cmpxchg(&drv->last_seq, last_seq, seq) != last_seq);
amdgpu_fence.c:226       last_seq &= drv->num_fences_mask;
amdgpu_fence.c:232           ++last_seq;
amdgpu_fence.c:233           last_seq &= drv->num_fences_mask;
amdgpu_fence.c:234           ptr = &drv->fences[last_seq];
amdgpu_fence.c:246       } while (last_seq != seq);
```

**Es un ring buffer de fences, y el host lo recorre desde `last_seq` hasta
`seq`.** El número de ranuras:

```
amdgpu_fence.c:461   ring->fence_drv.num_fences_mask = ring->num_hw_submission * 2 - 1;
amdgpu_fence.c:463   ring->fence_drv.fences = kcalloc(ring->num_hw_submission * 2, sizeof(void *), GFP_KERNEL);
amdgpu_fence.c:450   if (!is_power_of_2(ring->num_hw_submission))
amdgpu_fence.c:451       return -EINVAL;
```

**`2 × num_hw_submission` ranuras, y `num_hw_submission` tiene que ser potencia
de dos** o el ring no arranca.

**Consecuencia real, y no es trivia:** si la GPU avanza más de
`2 × num_hw_submission` secuencia sin que el host recoja, el contador da la vuelta
y `last_seq == seq` con el host atrás. `amdgpu_fence.c:223-224` lo detecta —
`if (unlikely(seq == last_seq)) return false;` — y devuelve "sin progreso". **El
host no se cuelga: se queda esperando.** Eso es un límite de diseño del driver,
y un driver propio tiene que elegir el mismo `num_hw_submission` o uno mayor.

## La lectura: memoria normal, no MMIO

```
amdgpu_fence.c:79   static u32 amdgpu_fence_read(struct amdgpu_ring *ring)
amdgpu_fence.c:84       if (drv->cpu_addr)
amdgpu_fence.c:85           seq = le32_to_cpu(*drv->cpu_addr);
amdgpu_fence.c:86       else
amdgpu_fence.c:87           seq = atomic_read(&drv->last_seq);
```

**Una lectura de CPU ordinary sobre memoria que la GPU escribe por DMA.** Sin
MMIO, sin registro, sin `ioreload`.

Y el caso `else` es el que hay que mirar de verdad: **si no hay `cpu_addr`, el
host lee su propio `last_seq` y siempre ve el mismo valor.** Nunca detecta
progreso. La traducción es Silenciosa.

## Y hay un temporizador de respaldo, porque no confía en la IRQ

```
amdgpu_fence.c:188   * Start a timer as fallback to our interrupts.
amdgpu_fence.c:192   mod_timer(&ring->fence_drv.fallback_timer, jiffies + AMDGPU_FENCE_JIFFIES_TIMEOUT);
amdgpu.h:277          #define AMDGPU_FENCE_JIFFIES_TIMEOUT  (HZ / 2)
amdgpu_fence.c:264       dev_warn(ring->adev->dev, "Fence fallback timer expired on ring %s\n", ring->name);
```

**500 ms.** Si la interrupción no llega en medio segundo, el timer sondea
`amdgpu_fence_process` y avisa.

**Es un dato de diseño, no un detalle:** el driver **no confía en su propia IRQ**.
Un driver propio que sólo implemente la IRQ hereda un modo de fallo que
amdgpu decidió cubrir; uno que implemente el timer tiene el modo de fallo
opuesto, un timeout de medio segundo por job cuando el polling falla.

## Dónde vive la página: RAM del sistema, en GTT

Esto es lo que cierra la cadena, y es la respuesta a `§G`.

```
amdgpu_ring.c:297   ring->fence_gpu_addr = amdgpu_ring_get_gpu_addr(ring, ring->fence_offs);
amdgpu_ring.c:299   ring->fence_cpu_addr = amdgpu_ring_get_cpu_addr(ring, ring->fence_offs);
amdgpu_ring.c:302   ring->rptr_gpu_addr  = ...
amdgpu_ring.c:307   ring->wptr_gpu_addr  = ...
amdgpu_ring.c:312   ring->trail_fence_gpu_addr = ...
amdgpu_ring.c:317   ring->cond_exe_gpu_addr = ...
```

**Cinco palabras de control, y las cinco son offsets dentro del propio ring
buffer.** Eso significa que **el ring es bidireccional**: la GPU escribe `wptr`
dentro del ring, y el host lo lee de ahí.

Y el operando de `COND_EXEC` no está en el ring sino en una región aparte:

```
amdgpu_device.c:1042   r = amdgpu_bo_create_kernel(adev, AMDGPU_MAX_WB * sizeof(uint32_t) * 8,
amdgpu_device.c:1043                                       PAGE_SIZE, AMDGPU_GEM_DOMAIN_GTT,
amdgpu_device.c:1044                                       &adev->wb.wb_obj, &adev->wb.gpu_addr,
amdgpu_device.c:1045                                       (void **)&adev->wb.wb);
```

**`AMDGPU_GEM_DOMAIN_GTT` — RAM del sistema.** Y `amdgpu_bo_create_kernel`
devuelve un puntero de kernel, o sea que está mapeada en el espacio virtual del
núcleo.

Tamaño: `AMDGPU_MAX_WB = 1024` (`amdgpu.h:464`), y el comentario de
`amdgpu_device.c:1041` explica el `* 8`: *"AMDGPU_MAX_WB 256bit slots"*.
`4 bytes × 8 = 32 bytes = 256 bits`. **1024 slots × 32 bytes = 32 KiB.**

**Consecuencia que conecta con `086`:** la coherencia del fence **no depende de
la BAR**. `086` dice que la BAR son 256 MiB de 2 GiB de VRAM. El fence no está
en VRAM, está en RAM del sistema, y el host la lee directamente. **Por eso el
mecanismo de fence funciona en esta GPU aunque la VRAM no sea visible.** Es la
primera pieza de §G que se cierra sin depender de la TLB.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| El fence se emite como dos EOP, `seq-1` y `seq` | `PROVEN` (`gfx_v8_0.c:6145-6170`) |
| El EOP lleva flush de caché e invalidate de TS | `PROVEN` (`CACHE_FLUSH_AND_INV_TS_EVENT`) |
| Tres ejes: `DATA_SEL`, `INT_SEL`, `EOP_EXEC` | `PROVEN` (`gfx_v8_0.c:6152-6168`) |
| `TC_WB_ONLY` no se usa en GFX8 | `PROVEN` (no leído por el emisor) |
| El host recorre un ring de `2 × num_hw_submission` | `PROVEN` (`amdgpu_fence.c:461-463`) |
| `num_hw_submission` debe ser potencia de dos | `PROVEN` (`amdgpu_fence.c:450-451`) |
| El host lee memoria ordinary, no MMIO | `PROVEN` (`amdgpu_fence.c:84-85`) |
| Sin `cpu_addr` el host nunca detecta progreso | `PROVEN` (`amdgpu_fence.c:86-87`) |
| Hay timer de respaldo de 500 ms | `PROVEN` (`amdgpu_fence.c:192`, `HZ/2`) |
| El writeback buffer está en RAM del sistema, 32 KiB | `PROVEN` (`amdgpu_device.c:1042-1043`) |
| El ring es bidireccional | `PROVEN_DERIVED` (5 controles dentro del ring) |
| **Por qué hace falta el dummy `seq-1`** | **`NOT_DETERMINED`** |
| Cuánta API cache queda sin vaciar en el momento del fence | `NOT_DETERMINED` |
| Qué garantiza el orden EOP frente al trabajo previo | `NOT_DETERMINED` |
| Si el hardware reintenta un fence perdido | `NOT_DETERMINED` |
| Qué pasa con `num_hw_submission` en esta máquina | `NOT_DETERMINED` — no medido |

**Las dos primeras filas de `NOT_DETERMINED` son el corazón del asunto.** El
driver escribe un valor que no es el que quiere antes de escribir el que quiere,
y lo justifica con "cache flush problems" sin explicar el mecanismo. Para un
driver propio, **copiar el workaround sin entenderlo es un riesgo**: si la causa
fuera otra, la copia no funcionaría igual.

Pero también es **la vía más barata que queda para cerrar `hardware execution
ordering`**: la página de fence está en RAM del sistema y es legible sin tocar
la TLB, sin MMIO y sin riesgo para la sesión gráfica. Provocar un job, leer el
valor que escribió la GPU, y ver si llegó `seq` o `seq-1`, es un discriminante
directo sobre si el dummy importa. **No requiere F1.**

## Procedencia

- `STATIC` — `gfx_v8_0.c:6135-6172`, `amdgpu_fence.c:79-90` y `:190-267` y
  `:395-470`, `amdgpu_ring.h:58-72` y `:116-131`, `amdgpu_ring.c:288-320`,
  `amdgpu_device.c:1028-1085`, `amdgpu.h:277` y `:464`.
- Sin `RUNTIME`. Sin lectura de la GPU. Sin escrituras.
- Encadenada con `094` (los tres `FENCE` del frame), `095` (los tres motores),
  `086` (BAR = 256 MiB), `072` (COND_EXEC, cuya cuenta está en el writeback),
  `090` (§G, el grano del L2).
- Cierra los dominios 19 y 22 en su parte de software.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Nota de método.** Escribí en un borrador que el buffer writeback lo asignaba
`amdgpu_device_wb_get`, y no es cierto: esa función sólo reparte **índices** con
un bitmap (`find_first_zero_bit` sobre `adev->wb.used`, y devuelve
`offset << 3`). La memoria la reserva `amdgpu_device_wb_init`, tres funciones
más arriba. **Leí el allocator y confundí "repartir ranuras" con "reservar
memoria".**

Es la novena vez que el nombre de una función no dice lo que hace, y la segunda
que caigo en la misma sesión después de `gmc_v8_0_vram_gtt_location` en `086`.
La diferencia es que esta la pillé siguiendo la cadena de llamadas en vez de
quedarme en el primer sitio donde aparecía `wb`.