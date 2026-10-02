# 109 · §D: un anillo GFX, dos motores, y tres esperas con tres registros distintos

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN (el volcado de 097 es la fuente de la parte observada)
GPU INTACTA
```

## Qué resuelve

La premisa de `108`: *si PFP y ME son dos motores, ¿el anillo GFX tiene un fetch
o dos?* **Respuesta: un solo anillo, y los dos ejecutan paquetes de él.**

Y de ahí sale algo mejor: **las tres esperas del driver no son la misma espera.**

## Un anillo, dos motores

```
gfx_v8_0.c:60      #define GFX8_NUM_GFX_RINGS     1
gfx_v8_0.c:5264    adev->gfx.num_gfx_rings = GFX8_NUM_GFX_RINGS;
```

**Un anillo GFX.** Más `num_compute_rings` (L5265, `min(get_num_kcq,
AMDGPU_MAX_COMPUTE_RINGS)`) y el KIQ. **El host ya observó 8 compute rings**
(`098`: `ring 1 (comp_1.0.0)` … `ring 8 (comp_1.3.1)`), así que
`get_num_kcq` devolvió 8 en esta GPU.

**Y el anillo GFX lo consumen los dos motores.** No es una deducción mía: lo
dice la elección explícita de motor en el propio driver, y difiere según el tipo
de anillo:

```
gfx_v8_0.c:5243   *reg_mem_engine = 0;                          <- compute/KIQ → ME
gfx_v8_0.c:5245   *ref_and_mask = GPU_HDP_FLUSH_DONE__CP0_MASK;  <- CP0 = PFP
gfx_v8_0.c:5246   *reg_mem_engine = WAIT_REG_MEM_ENGINE(1);     <- ring GFX → PFP
```

**El mismo anillo GFX tiene esperas dirigidas a PFP, y `ring_emit_vm_flush` tiene
una dirigida a ME.** Dos motores ejecutando del mismo anillo.

**Esto matiza `108`.** Ahí escribí *"un motor consume sus paquetes en orden de
cola, y PTBA está antes en la cola"*. **Eso es cierto por motor, pero no basta
como argumento global:** con dos consumidores del mismo anillo, el orden entre
ellos no lo garantiza la cola sino el `PFP_SYNC_ME`.

## Las tres esperas, y son tres cosas distintas

| emisor | línea | `MEM_SPACE` | `FUNCTION` | `ENGINE` |(ref, mask) | poll |
|---|---|---|---|---|---|---|
| `ring_emit_hdp_flush` | `gfx_v8_0.c:6047` | (0) | **3** `==` | pfp | **iguales** | `0x20` |
| `ring_emit_pipeline_sync` | `gfx_v8_0.c:6180` | **1** memoria | **3** `==` | pfp/me | `seq` / `0xffffffff` | 4 |
| `ring_emit_vm_flush` | `gfx_v8_0.c:6199` | (0) registro | **0** `always` | me | **`0` / `0`** | `0x20` |

**Sólo una de las tres tiene la condición de valor vacía.** Las otras dos son
comparaciones reales contra la dirección que nombra el propio driver.

**Y eso es lo que `017` no vio: la condicion vacia es real, pero no es la misma espera en
los tres sitios.** `017`/eplanteó sobre la de `vm_flush` y generalizó; las otras
dos demuestran que el driver **sabe escribir una espera real cuando la quiere.**

## Y aquí está el cierre de `097`/`098`

```
gfx_v8_0.c:6177   uint32_t seq  = ring->fence_drv.sync_seq;
gfx_v8_0.c:6178   uint64_t addr = ring->fence_drv.gpu_addr;
gfx_v8_0.c:6181       WAIT_REG_MEM_MEM_SPACE(1) |   /* memory */
gfx_v8_0.c:6182       WAIT_REG_MEM_FUNCTION(3) |   /* equal */
gfx_v8_0.c:6184   amdgpu_ring_write(ring, addr & 0xfffffffc);
gfx_v8_0.c:6186   amdgpu_ring_write(ring, seq);
gfx_v8_0.c:6187   amdgpu_ring_write(ring, 0xffffffff);   /* mask: 32 bits */
```

**El GPU espera a que la página de fence contenga `sync_seq`.**

Y `096` estableció que el host lee **la misma página** por
`amdgpu_fence_read` (`amdgpu_fence.c:84-85`), y que su valor se compara con
`amdgpu_fence_process` contra `sync_seq` (`amdgpu_fence.c:220`).

**La página de fence es el punto de encuentro entre hardware y host.** El GPU la
espera; el host la lee. No hay dos mecanismos: hay uno, con dos lectores.

**Eso es `§G` cerrándose sin hardware:** la coherencia del fence no depende de la
TLB, no depende de la BAR, y no necesita ninguna page table. Es una celda de
memoria del sistema (`096`: `AMDGPU_GEM_DOMAIN_GTT`, 32 KiB de writeback) que
ambos lados leen.

**Y explica por qué `098` vio un retraso máximo de 4 con 758.647 muestras:** el
`poll interval` de esta espera es **4** (`gfx_v8_0.c:6188`). No es una
coincidencia que pueda probarse, pero el número es el mismo y la magnitud del
retraso es la que cabría esperando un paquete que sondea cada 4 unidades.

## Lo que no consigo atribuir, y lo digo

Los 8 paquetes `WAIT_REG_MEM` del ring vivo de `097`/`107` tienen:

```
FUNCTION=3  OPERATION=1  ENGINE=pfp  REF=0x00001537  MASK=0x00001538  ADDR1=1  ADDR2=1
```

**El dword de flags coincide exactamente con `gfx_v8_0.c:6048-6050`**
(`OPERATION(1) | FUNCTION(3) | reg_mem_engine` con `reg_mem_engine = ENGINE(1)`).

**Pero `ref` y `mask` no coinciden con el código.** `gfx_v8_0.c:6053` y `:6054`
escriben **la misma variable `ref_and_mask` en los dos**, así que deberían ser
iguales. Observados difieren en 1 (`0x1537` vs `0x1538`).

**Y las otras dos tampoco encajan**: `pipeline_sync` pondría `MEM_SPACE=1` y
`OPERATION=0`; `vm_flush` pondría `FUNCTION=0`.

**Así que no atribuyo los 8 paquetes a ningún emisor de `gfx_v8_0.c`.** O mi
layout de los 5 dwords de payload es incorrecto, o el emisor está en otro
fichero. `soc15d.h:205-212` declara siete campos para cinco dwords, así que
**varios campos comparten dword** y no he establecido el reparto.

**Esto corrige `107`, que los atribuí a `gfx_v8_0.c:6047`.** El *flags* dword
encaja; el resto no. `107` debe quedar como `CORROBORATED` en la atribución, no
`PROVEN_DERIVED`. **No lo edito — `107` es mío, así que sí, y lo corrijo al
final.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| 1 anillo GFX | `PROVEN` (`gfx_v8_0.c:60`, `:5264`) |
| 8 anillos de compute | `OBSERVED` (`098`) |
| PFP y ME ejecutan del mismo anillo | `PROVEN` (`L5243` vs `L5246`) |
| Las tres esperas difieren en `FUNCTION` | `PROVEN` |
| Sólo `vm_flush` tiene condición vacía | `PROVEN` (`L6199-6206`) |
| El driver sabe escribir una espera real | `PROVEN` (`L6180-6187`) |
| `pipeline_sync` espera la página de fence == `sync_seq` | `PROVEN` |
| La página de fence une GPU y host | `PROVEN_DERIVED` |
| El reparto de los 5 dwords de payload | `NOT_DETERMINED` |
| A qué emisor pertenecen los 8 observados | **`NOT_DETERMINED`** |
| Cuánto dura un `poll interval` en unidades reales | `NOT_DETERMINED` |

**Las dos últimas son las que cierran el resto de §D.** Con el layout de payload
resuelto, `107` recuperaría la atribución y `094` podría confirmar que los 17
términos de su presupuesto corresponden a paquetes reales.

## Procedencia

- `STATIC` — `gfx_v8_0.c:60`, `gfx_v8_0.c:5228-5247`, `gfx_v8_0.c:6036-6056`,
  `gfx_v8_0.c:6174-6189`, `gfx_v8_0.c:6191-6215`, `gfx_v8_0.c:5259-5274`,
  `amdgpu_fence.c:84-85`, `amdgpu_fence.c:220`, `soc15d.h:199-225`.
- `OBSERVED` — el volcado de `097`, que es de sólo lectura.
- Sin MMIO write, sin TLB, sin módulos.
- **Corrige `108`** (la premisa del orden) y **degrada la atribución de `107`**.
  Ambos son míos.
- Encadenada con `107`/`108` (las funciones y la visibilidad), `095` (PFP/ME),
  `096`/`097`/`098` (la página de fence), `094` (el presupuesto del frame).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, y es sobre algo que hice mal y no detecté a tiempo.**

En `108` afirmé que el orden de la cola basta porque las dos escrituras son del
mismo motor. **Es un argumento válido por motor, pero presented como garantía
global, y con dos motores leyendo el mismo anillo no lo es.** Lo escribí antes
de comprobar cuántos anillos hay y cuántos motores los leen, que es justo lo que
`AGENTS.md` §D L417 pide resolver.

**Y en `107` atribuí los 8 paquetes a un emisor sin comprobar los cinco dwords de
payload, sólo el primero.** El primer dword encajaba, y eso me bastó para
llamarlo `PROVEN_DERIVED`. **Un dword que coincide no es un paquete que
coincide:** los otros cuatro son la mitad de la prueba.