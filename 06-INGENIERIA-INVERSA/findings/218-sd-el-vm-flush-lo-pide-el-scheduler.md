# 218  §D: el vm_flush lo pide el scheduler, y eso reconcilia 094 con 111

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN (la parte observada viene del volcado de 111)
GPU INTACTA
```

## Qué resuelve

La contradicción que `216` dejó abierta: `094` cuenta un `PFP_SYNC_ME` en el
presupuesto del frame, y `216` midió **uno** en twenty segundos frente a 34 fences
y 8 jobs.

**No hay contradicción. El vm_flush no es por frame: lo decide el scheduler, y
en un escritorio en régimen permanente casi nunca se pide.**

## El call site, y es único

`gfx_v8_0_ring_emit_vm_flush` se asigna como puntero:

```
gfx_v8_0.c:6901   .emit_vm_flush = gfx_v8_0_ring_emit_vm_flush,   (ring GFX)
gfx_v8_0.c:6938   .emit_vm_flush = gfx_v8_0_ring_emit_vm_flush,   (compute)
```

Y en todo el driver hay **un solo sitio** que lo invoca por la tabla:

```
amdgpu_vm.c:813   vm_flush_needed &= !!ring->funcs->emit_vm_flush  &&
amdgpu_vm.c:814              job->vm_pd_addr != AMDGPU_BO_INVALID_OFFSET;
```

## Y de dónde sale `vm_flush_needed`

```
amdgpu_vm.c:793   bool vm_flush_needed = job->vm_needs_flush;
amdgpu_vm.c:799   if (amdgpu_vmid_had_gpu_reset(adev, id)) {
amdgpu_vm.c:801       vm_flush_needed = true;
amdgpu_vm.c:823   if (!vm_flush_needed && !gds_switch_needed && !need_pipe_sync &&
amdgpu_vm.c:824       !cleaner_shader_needed)
amdgpu_vm.c:825       return;
```

**Sólo dos fuentes, y ninguna de las dos es "estoy enviando un frame":**

| fuente | qué significa |
|---|---|
| `job->vm_needs_flush` | **el scheduler decidió** que este job cambia page tables |
| `amdgpu_vmid_had_gpu_reset(adev, id)` | **hubo un reset** de GPU que afecta a este VMID |

**Y si no hace falta, la función vuelve en L825 sin escribir un solo dword.**

**Un compositor que no cambia de buffers no pide vm_flush.** Reutiliza los
mapeos existentes, así que no toca page tables, así que no hay nada que
invalidar. **Y eso es exactamente lo que midió `216`**: 34 fences, 8 jobs, **1
vm_flush** en veinte segundos.

**Los fences son de job. El vm_flush es de actualización de page table.** No son
la misma frecuencia, y por eso `094` y `216` no discrepaban.

## Y `094` está bien: presupuesta el peor caso

```
gfx_v8_0.c:6929   VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7 + /* gfx_v8_0_ring_emit_vm_flush */
gfx_v8_0.c:6964   17 + /* gfx_v8_0_ring_emit_vm_flush */
```

`emit_frame_size` es un **máximo**, no un promedio, y `094` ya lo dijo así
(*"maximum 215dw"*). Presupuesta un frame que sí hace flush, que es el peor caso.
`216` midió una ventana que no lo hace.

**Los dos eran correctos. Medían cosas distintas sin decirlo.**

## Y esto matiza `194`, que dice "siempre"

`194` establecio que en GFX8 `needs_flush` **siempre es verdadero** al actualizar
page tables:

```
amdgpu_vm.c:1157   flush_tlb |= amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 0, 0);
```

Eso sigue siendo `PROVEN`. **Lo que cambia es la frecuencia, no la regla**: la
regla es "si actualizas page tables en GFX8, el invalidate es obligatorio"; y
`218` establece **que las actualizaciones son raras**, porque las decide el
scheduler y un compositor en régimen no las hace.

**Para un driver propio la distinción es operativa y no cosmética**: si no
puedes invalidar, **no puedes actualizar page tables en absoluto** en esta GPU.
No es "se Permite omitir el flush": es "sin flush, ese cambio no es visible".

## Y de paso: por qué el `COND_EXEC` no se cierra

El mismo bloque explica el `SWITCH_BUFFER` doble de `072`:

```
amdgpu_vm.c:829   /* There is no matching insert_end for this on purpose for the vm flush.
amdgpu_vm.c:830    * The IB portion of the submission has both.  Having multiple
amdgpu_vm.c:831    * insert_start sequences is ok, but you can only have one insert_end
amdgpu_vm.c:832    * per submission based on the way VCN FW works.  For JPEG
amdgpu_vm.c:833    * you can as many insert_start and insert_end sequences as you like as
amdgpu_vm.c:834    * long as the rest of the packets come between start and end sequences.
amdgpu_vm.c:835    */
amdgpu_vm.c:836   if (ring->funcs->insert_start)
amdgpu_vm.c:837       ring->funcs->insert_start(ring);
amdgpu_vm.c:839   if (ring->funcs->init_cond_exec)
amdgpu_vm.c:840       patch = amdgpu_ring_init_cond_exec(ring, ring->cond_exe_gpu_addr);
```

**El kernel dice por qué el vm_flush abre un `insert_start` y deliberadamente no
lo cierra, y lo dice blaming al firmware de VCN**: *un solo `insert_end` por
envío*.

**Eso es el condicionamiento de `072` y `094`:** el bloque de vm_flush va
*entre* el `insert_start` y el `insert_end` del IB. Y `094` ya había copiado el
comentario del driver sobre el `COND_EXEC` que salta por encima del
`SWITCH_BUFFER` doble (`gfx_v8_0.c:6884-6886`).

**Tres hallazgos que parecían independientes y salen del mismo párrafo:** el
framing asimétrico de `072`, el `4 + /* double SWITCH_BUFFER */` de `094`, y la
regla de "un insert_end por envío".

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Un solo call site de `emit_vm_flush` | `PROVEN` (`amdgpu_vm.c:813`) |
| Sólo lo pide el scheduler o un reset | `PROVEN` (`L793`, `L799-804`) |
| Si no hace falta, no se escribe nada | `PROVEN` (`L823-825`) |
| `094` presupuesta el peor caso | `PROVEN_DERIVED` |
| `216` es coherente con `094` | `PROVEN_DERIVED` |
| Un compositor en régimen no pide vm_flush | `CORROBORATED` — no observado directamente |
| El vm_flush abre un `insert_start` sin cerrarlo | `PROVEN` (`L829-837`) |
| "Un insert_end por envío, por el firmware de VCN" | `PROVEN` (`L831-832`, afirmación del driver) |
| Qué pone `job->vm_needs_flush` | **`NOT_DETERMINED`** |
| Si la regla de VCN aplica igual a GFX8 | **`NOT_DETERMINED`** |

**La penúltima es la que queda, y es el eslabón real.** `job->vm_needs_flush` lo
pone el scheduler, y no he seguido el scheduler. **Sin eso no se sabe cuándo hay
un invalidate**, que es justo lo que `AGENTS.md` §D y §C quieren cerrado.

**Y la última tiene un matiz que hay que decir:** el comentario blamea a
**"the way VCN FW works"**, y VCN es un motor de vídeo. Este anillo es el GFX.
**No sé si la restricción del `insert_end` es del scheduling en general o
específica de VCN, y el texto mezcla ambos** ("per submission" en general,
"VCN FW" como causa). **Lo marco `NOT_DETERMINED` en vez de extenderlo a GFX8 por
analogía**, que es exactamente lo que `AGENTS.md` L431 prohíbe.

## Procedencia

- `STATIC` — `amdgpu_vm.c:793-825` y `:829-845`, `gfx_v8_0.c:6901` y `:6929` y
  `:6964` y `:6884-6886`.
- `OBSERVED` — el volcado de `216`, de sólo lectura.
- Sin MMIO write, sin TLB, sin módulos, sin cambiar parámetros.
- **Reconcilia `094` y `216`**, y matiza `194` y `072`.
- Encadenada con `194` (el invalidate obligatorio), `094` (el presupuesto),
  `216` (next IB), `072` (el COND_EXEC), `108`/`214` (los motores).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, sobre cómo se me pasó una contradicción obvia.**

En `216` vi `PFP_SYNC_ME = 1` contra 34 fences y lo anoté como contradicción
**sin comprobar quién llama a `ring_emit_vm_flush`.** Era un `grep` y era la
pregunta entera. **Anoté una contradicción entre dos hallazgos míos en vez de
resolverla, y la nota decía "no lo resuelvo" como si eso fuera honestidad cuando
en realidad era trabajo pendiente disfrazado de rigor.**

Es la diferencia entre `NOT_DETERMINED` y `no lo he buscado`. La primera es una
frontera legítima; la segunda es una tarea que no hice.

**Y hay una segunda, más fea: en el borrador de esta nota escribí "hasta
encontró"**, que era una lengthwise de CJK colada en medio del texto. La detecté
al comprobar el artefacto, como otras seis veces. **La comprobación posterior del
artefacto me ha salvado siete veces hoy de publicar basura.**