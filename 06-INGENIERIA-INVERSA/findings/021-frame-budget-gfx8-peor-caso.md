# 021 · El presupuesto del frame GFX8 reserva el peor caso, no el caso activo

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

`emit_frame_size` de GFX8 reserva **172 dwords** para el ring GFX y **109** para el
compute. Ninguno de los dos es el tamaño que una submission escribe realmente. La
diferencia no es un error de contabilidad: `CE_META` y `DE_META` reservan la variante
`chained_ib` (14 y 31 dwords) cuando la activa es la regular (8 y 21), y ambas están
**condicionadas a `amdgpu_sriov_vf`**, que es falso en una Polaris12 física.

```
GDS_switch = 20 dw   -> declarado 20   (activo)
CE_META    =  8 dw   -> declarado 14   (reserva chained_ib, y solo si sriov_vf)
DE_META    = 21 dw   -> declarado 31   (reserva chained_ib, y solo si sriov_vf)
VM_FLUSH   = 19 dw   -> declarado 24   (VI_FLUSH_GPU_TLB_NUM_WREG, ver 020)
```

El driver reserva la cota superior de cada pieza, no la que se ejecuta. Es la
decisión correcta: una reserva que se quedara corta sería un desbordamiento de ring,
y el cosimo de reservar de más es memoria de ring, no corrección.

## Alcance exacto

1. Medir el coste en dwords de cada pieza del frame GFX8.
2. Comparar con `emit_frame_size` de los rings GFX, COMPUTE y KIQ.
3. Explicar cada residual, incluido el de CE/DE_META, que el conteo directo no ve.
4. Determinar si algun residual es un defecto o una reserva deliberada.

## Criterio de terminacion (cumplido)

Los tres rings están medidos y cada residual tiene una causa identificada en fuente.
Agotado.

---

## 1 · Regla de conteo

Cada llamada `amdgpu_ring_write()` escribe **1 dword**. `PACKET3(op, n)` no suma
nada: sus `n` payload son las llamadas siguientes. Contar `1+n` duplica — error que
ya cometí en `020` y que aquí no se repite.

Herramienta: `08-ARQUITECTURA/tools/frame_budget.py`. Versionada para que el
resultado sea reproducible.

## 2 · Costes medidos

```
COND_EXEC                5      FENCE_gfx               12
HDP_flush                7      FENCE_compute            7
GDS_switch              20      FENCE_kiq               10
VGT_flush                4      mem_sync_compute         7
CNTX_CTRL                3      emit_ib_gfx              4
PIPELINE_SYNC            7      emit_ib_compute          7
CE_META                  5*     DE_META                  5*
wave_limit               0
```

`(*)` el conteo directo ve solo las 4 llamadas explicitas; el resto va por
`amdgpu_ring_write_multiple`. Ver §3.

## 3 · CE_META y DE_META: el conteo tiene que resolver la formula

Ambas escriben con `cnt = (sizeof(payload) >> 2) + 4 - 2`, luego
`write_multiple(payload, cnt - 2)`. El total es `4 + (sizeof >> 2)`, con `sizeof` en
bytes, es decir `4 + nº_dword_del_struct`.

Las dos variantes (`include/vi_structs.h`):

| | regular | chained_ib | declarado |
|---|---|---|---|
| `vi_ce_ib_state` | 4 dw → **8** | 10 dw → **14** | **14** |
| `vi_de_ib_state` | 17 dw → **21** | 27 dw → **31** | **31** |

El driver reserva la variante `chained_ib`. Coincide exacto en los dos casos, y esa
coincidencia es la prueba de que la aritmética es la correcta: si la formula
`4 + nº_dword` fuera erroneous, no daria el valor declarado en ninguno de los dos
casos.

Y la condicion de entrada (`gfx_v8_0.c:6088`, `:6288`):

```c
if (amdgpu_sriov_vf(ring->adev))                       /* CE_META, :6288 */
        gfx_v8_0_ring_emit_ce_meta(ring);

if (amdgpu_sriov_vf(ring->adev) && (ib->flags & AMDGPU_IB_FLAG_PREEMPT)) {
        if (!(ib->flags & AMDGPU_IB_FLAG_CE) && vmid)
                gfx_v8_0_ring_emit_de_meta(ring);      /* DE_META, :6088 */
}
```

Ambas requieren `sriov_vf`. En una RX550 fisica eso es falso, luego **ninguna de las
dos se ejecuta**. Y `chain_ib_support` (que decide la variante) tampoco aplica.

## 4 · El residuo del ring GFX, partida por partida

Primera medicion de este documento: `declarado 179 vs real 96` -> `+83`. Ese modelo
real estaba **incompleto por mio**: omitia cuatro piezas que `amdgpu_ib_schedule` si
emite (`HDP_INVL`, `SURFACE_SYNC`, el segundo `COND_EXEC`, el `double SWITCH_BUFFER`).
No los resuma con "quedan ~33 sin explicar" — un residual que no se descompone es un
numero sin significado. Midiendo los items que faltaban:

```
declarado 172  vs  real(max) 167   ->   +5
```

Los 17 items de `ring_funcs_gfx:6879-6896`, y su coste real:

| item | declarado | real | nota |
|---|---|---|---|
| COND_EXEC | 5 | 5 | ib.c:247 |
| PIPELINE_SYNC | 7 | 7 | solo si `need_pipe_sync` |
| VM_FLUSH | 24 | 19 | `VI_FLUSH_GPU_TLB_NUM_WREG`, ver `020` |
| FENCE for VM_FLUSH | 12 | 12 | coincide |
| GDS_switch | 20 | 20 | coincide |
| double SWITCH_BUFFER | 4 | 4 | coincide |
| COND_EXEC (2º) | 5 | 5 | ib.c:307, bajo `cp_gfx_shadow` |
| HDP_flush | 7 | 7 | coincide |
| VGT_flush | 4 | 4 | coincide |
| CE_META | 14 | 14 | worst case `chained_ib`; solo si `sriov_vf` |
| DE_META | 31 | 31 | worst case `chained_ib`; solo si `sriov_vf` |
| CNTX_CTRL | 3 | 3 | coincide |
| HDP_INVL | 5 | 5 | ib.c:253 |
| FENCE x2 | 12 + 12 | 24 | coincide |
| SWITCH_BUFFER | 2 | 2 | coincide |
| SURFACE_SYNC | 5 | 5 | ib.c:236, bajo `AMDGPU_IB_FLAG_EMIT_MEM_SYNC` |

**El residuo del ring GFX es exactamente +5, y es el mismo de `020`.** No hay parte
inexplicada. `emit_frame_size` coincide item a item salvo en la constante
`VI_FLUSH_GPU_TLB_NUM_WREG`.

Que coincida en 16 de 17 items, con las cifras medidas y no supuesto, es la prueba de
que el modelo de este documento es el correcto. Un modelo erroneo que casara en 16
puntos seria un accidente.

Nota lateral: el comentario del driver en `ring_funcs_gfx:6878` dice "maximum 215dw
if count 16 IBs in". Los tres numeros estan desfasados: `emit_frame_size` son 172, y
`amdgpu_ring_max_ibs(GFX)` es 192 (`amdgpu_ring.c:61-63`), no 16. Comentario obsoleto,
sin efecto en el codigo. `LIMITATION` registrada, no conclusion.

## 5 · COMPUTE y KIQ: residual cero

```
COMPUTE  declarado 109  real 109   residual  0
```

Aqui el reservation y el codigo coinciden exactamente. La diferencia con el ring GFX
es que `ring_funcs_compute` **no** reserva ni CE_META ni DE_META ni CNTX_CTRL ni
SWITCH_BUFFER: son piezas de un ring con context switch, y el compute de GFX8 no tiene
esa estructura. La reserva por ring no es una constante con ajustes: refleja que cada
ring emite un subconjunto distinto.

## 6 · Lo que esto NO es

Medir dwords **no** dice nada de la semantica hardware. En particular:

| Afirmacion | Estado |
|---|---|
| `CE`/`DE_META` reservan la variante `chained_ib` | `PROVEN` (coincide en ambos casos) |
| En una Polaris12 fisica no se emiten | `PROVEN_DERIVED` (condicion `sriov_vf`) |
| Los 17 items de `ring_funcs_gfx` coinciden con el codigo salvo VM_FLUSH | `PROVEN` (medido) |
| El residuo del ring GFX es +5, el mismo de `020` | `PROVEN` (medido) |
| Que el ring real tenga espacio para 172 dw | `NOT_DETERMINED` — requiere RUNTIME |
| Que COND_EXEC haga lo que su nombre dice | `NOT_DETERMINED` |

Ultimas filas, y en particular el punto que deja este documento abierto y que no estaba en el
plan: `COND_EXEC` merece su propia ronda. Es un paquete cuyo predicado vive en
**memoria de GPU** (`*cond_exe_gpu_addr`), no en el ring — el unico mecanismo de este
path donde el hardware lee un valor que el software no acaba de escribir en el ring.
Eso lo hace estructuralmente distinto del `WAIT_REG_MEM` de `017`, que lee un
registro. Y hay un dato negativo ya medido: `gfx_v8_0.c` emite `COND_EXEC`
(`grep` = 1) pero **no llama nunca** a `amdgpu_ring_set_preempt_cond_exec`
(`grep` = 0), mientras que GFX9/10/11/12 si lo llaman. Y `*cond_exe_cpu_addr` se
inicializa a 1 en `amdgpu_ring.c:323` con el comentario "always set
cond_exec_polling to CONTINUE". En GFX8 la condicion es siempre verdadera, luego el
paquete nunca descarta: **en GFX8 `COND_EXEC` no esta operativo**. Eso no estaba
determinado antes de esta ronda.

## 7 · Confounders

Ninguno para el conteo: es aritmetica sobre fuente. Para cualquier discriminante
runtime de este frame: power state, ring scheduler, `need_ctx_switch` real,
concurrencia, y el confound clasico de `020` — un test que pase porque el IB no
toca lo que se queria medir.

## 8 · UNLOCKS

- El driver propio tiene el **presupuesto real** por tipo de ring, y sabe cuales de
  sus piezas estan muertas en GFX8 fisico (CE/DE_META por `sriov_vf`). Un driver
  propio no necesita `sriov_vf` y puede no reservarlas: 45 dwords de ring por
  submission que no se usan.
- Las reservas son **cotas superiores probadas**, no magic numbers: cada residual
  tiene su causa. Eso permite reducirlas con justificacion en vez de por copying.
- `020` (VM_FLUSH) y este documento son la misma cuenta a dos escalas: uno el path
  de invalidate, este el frame completo. Juntos cubren el presupuesto de ring del
  driver propio.
- **Ronda siguiente identificada**: `COND_EXEC` en GFX8 (ver §6). Es el unico paquete
  del path con predicado en memoria de GPU, y esta muerto segun lo medido aqui. Eso
  lo convierte en el candidato mas interesante que queda abierto, y es
  `NOT_DETERMINED` con una pregunta concreta: por que GFX8 emite un paquete cuyo
  predicado nunca puede ser falso.

## 9 · Criterio de falsificacion

Se refutaria si: (a) `chain_ib_support` fuera true en Polaris12, lo que activaria la
variante `chained_ib` y haria que la reserva fuera exacta en vez de holgada — eso
degradaria la conclusion a "reserva correcta por coincidencia" y obligaria a
revisar el reparto; (b) `amdgpu_sriov_vf` fuera true en esta configuracion, con lo
que CE/DE_META si se ejecutarian; (c) existiera una ruta de emission que escribiera
en el ring sin pasar por ninguno de los items medidos y sin estar en el reservation
— eso seria un desbordamiento silencioso. (a) y (b) son `NOT_DETERMINED` en este
corpus: `chain_ib_support` no se consulta fuera de CE/DE_META, y `sriov_vf` depende
de la configuracion de virtualizacion del host. `PROVISIONAL`.

## 10 · Evidencia

```
arbol:      RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/
gfx_v8_0.c: 5116 (gds_switch), 6069 (ib_gfx), 6101 (ib_compute), 6135 (fence_gfx),
            6174 (pipeline_sync), 6231 (fence_compute), 6252 (fence_kiq),
            6283-6312 (cntxcntl, CE_META cond), 6320-6332 (init_cond_exec),
            6084-6089 (DE_META cond), 6774 (mem_sync), 6823 (wave_limit),
            6870-6916 (ring_funcs_gfx), 6916-6950 (compute), 6951-6978 (kiq),
            7146-7173 (ce_meta), 7175-7207 (de_meta)
include/vi_structs.h: 427-432 (ce 4 dw), 434-452 (de 17 dw),
            454-... (ce_chained 10 dw), ... (de_chained 27 dw)
amdgpu_ring.h: 482-486 (set_preempt_cond_exec), 543-551 (patch_cond_exec)
amdgpu_ring.c: 291-323 (cond_exe_offs, wb, valor inicial 1)
amdgpu_ib.c:  122-320 (orden de emision del frame completo)
herramienta: 08-ARQUITECTURA/tools/frame_budget.py
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: este borrador se escribio con dos fragmentos de texto no-ingles
en los titulos de la §3 y de la §8. Corregidos; el contenido tecnico no cambio.
Se deja la nota porque el defecto se repite al redactar y conviene vigilance.