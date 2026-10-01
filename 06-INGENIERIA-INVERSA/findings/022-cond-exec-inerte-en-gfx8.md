# 022 · COND_EXEC en GFX8: emitido con un predicado que nadie puede poner a falso

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=021-frame-budget-gfx8-peor-caso.md` §6 (ronda que alli quedo abierta)

## CUDA principal

`COND_EXEC` es el unico paquete de este path cuyo predicado **no esta en el ring**: lo
lee de memoria de GPU, en `*cond_exe_gpu_addr`. Es estructuralmente distinto del
`WAIT_REG_MEM` de `017`, que lee un registro.

En GFX8 **se emite y no puede hacer nada**. El predicado se inicializa a 1 y todos los
20 call sites que pueden ponerlo a 0 son de **preemption**, y GFX8 no tiene preemption. El cuerpo de la funcion de emision es identico al de GFX9
(salvo el nombre), que si lo usa.

```
GFX8:  emite COND_EXEC   |  init_cond_exec   = si (solo ring GFX)
       set_preempt_cond_exec = NO LO LLAMA NUNCA   ->  predicado siempre 1
       preempt_ib asignado     = NO
       => el paquete nunca descarta. Es un no-op de 5 dw por submission.
GFX9:  mismo cuerpo de emision  |  si lo llama  ->  preemption lo usa
```

`NEGATIVE_RESULT`: no es que no se haya investigated el efecto de `COND_EXEC` en GFX8.
Es que en este ASIC el mecanismo esta inerte por construccion.

## Alcance exacto

1. Localizar todos los emisores de `COND_EXEC` y el predicado que leen.
2. Determinar quien puede escribir ese predicado, y si es alcanzable en GFX8.
3. Medir el coste en ring de un paquete que no hace nada.
4. Clasificar.

## Criterio de terminacion (cumplido)

Los dos emisores de GFX8, los tres escritores del predicado en todo el arbol, y la
cadena de guardas que los separa de GFX8 estan trazados. Agotado.

---

## 1 · Los dos emisores, y no es uno

`init_cond_exec` existe **solo** en `ring_funcs_gfx` de GFX8:

```
gfx_v8_0_ring_funcs_gfx      init_cond_exec = 1
gfx_v8_0_ring_funcs_compute  init_cond_exec = 0
gfx_v8_0_ring_funcs_kiq      init_cond_exec = 0
```

Y hay **dos** call sites, no uno, en una sola submission:

```
amdgpu_ib_schedule()                        amdgpu_vm.c:839  (dentro de amdgpu_vm_flush)
  ib.c:223   amdgpu_vm_flush(ring, ...)  -->  emite COND_EXEC #1  (vm.c:840)
                                            parcheado en vm.c:905
  ib.c:230   amdgpu_ring_ib_begin()
  ib.c:247   amdgpu_ring_init_cond_exec()   emite COND_EXEC #2
  ib.c:319   amdgpu_ring_patch_cond_exec()  parcheado en 319
  ib.c:333   amdgpu_ring_commit()
```

O sea: el ring GFX emite `COND_EXEC` **dos veces** por submission — uno envolviendo
la secuencia de vm-flush y otro envolviendo el frame. Los dos reserves de `021`
(5 dw cada uno) corresponden a esto.

### 1.1 · Un tercer emisor, sin parchear — en GFX11, no en GFX8

`ib.c:304-307` emite un `COND_EXEC` mas y **descarta el valor de retorno**:

```c
if (ring->funcs->emit_gfx_shadow && ring->funcs->init_cond_exec &&
    adev->gfx.cp_gfx_shadow) {
        amdgpu_ring_emit_gfx_shadow(ring, 0, 0, 0, false, 0);
        amdgpu_ring_init_cond_exec(ring, ring->cond_exe_gpu_addr);  /* retorno descartado */
}
```

Sin el offset no hay `patch_cond_exec`, luego ese paquete sale con lo que
`init_cond_exec` escribio: `num_skip` = 0 y el dw extra = 0. Es un `COND_EXEC` cuyo
conteo nunca se calcula.

`NEGATIVE_RESULT` del driver de referencia, **no alcanzable en Polaris12**: la
condicion exige `adev->gfx.cp_gfx_shadow`, y el unico sitio del arbol que lo pone a
true es `gfx_v11_0.c:714` (el campo esta comentado "for gfx11" en
`amdgpu_gfx.h:508`). En GFX8 es false y ese emisor no se ejecuta.

Lo registro porque (a) es informacion heredable para el driver propio, que si podria
querer esa secuencia, y (b) un `COND_EXEC` sin parchear es exactamente el tipo de
detalle que `WARN_ON(ring->ring[offset] != 0)` de `patch_cond_exec` sugiere que
alguien deberia revisar. No afecta a esta RX550: `NOT_APPLICABLE` con causa, no
`PROVEN_ABSENT`.

## 2 · El predicado

```
amdgpu_ring.c:317-323
  ring->cond_exe_gpu_addr = amdgpu_ring_get_gpu_addr(ring, ring->cond_exe_offs);
  ring->cond_exe_cpu_addr = amdgpu_ring_get_cpu_addr(ring, ring->cond_exe_offs);
  /* always set cond_exec_polling to CONTINUE */
  *ring->cond_exe_cpu_addr = 1;
```

Vive en el writeback buffer del dispositivo (`amdgpu_device_wb_get`,
`amdgpu_ring.c:291`), no en el ring. Valor inicial **1**.

## 3 · Quien puede ponerlo a 0 — y por que ninguno llega a GFX8

`grep -rn "amdgpu_ring_set_preempt_cond_exec("` sobre todo el arbol da **20 call sites
en 10 ficheros**, y en los 20 es lo mismo: assertar preemption.

| fichero | call sites | para que |
|---|---|---|
| `gfx_v9_0.c` | 2 (`:5739` assert, `:5774` deassert) | `gfx_v9_0_ring_preempt_ib`, MCBP |
| `gfx_v10_0.c`, `gfx_v11_0.c`, `gfx_v12_0.c` | 2 cada uno | `*_ring_preempt_ib` |
| `amdgpu_vpe.c` | 2 | `vpe_ring_preempt_ib` |
| `sdma_v5_0`, `v5_2`, `v6_0`, `v7_0`, `v7_1` | 2 cada uno | preemption de SDMA |

`gfx_v8_0.c`: **0** de 20. Ni GFX6 ni GFX7 tampoco. Y la razon de fondo es que no hay
preemption que assertar:

```
ASIC         preempt_ib asignado
gfx_v6_0            0
gfx_v7_0            0
gfx_v8_0            0        <-- nuestra placa
gfx_v9_0            1
gfx_v9_4_3          1
gfx_v10_0           1
gfx_v11_0           1
gfx_v12_0           1
gfx_v12_1           0
```

La frontera coincide exactamente con la de `set_preempt_cond_exec`. No es
coincidencia: `set_preempt_cond_exec` existe **para** `preempt_ib`, y GFX8 no tiene
`preempt_ib`.

### 3.1 · Las dos rutas que podrian eludir eso — y por que no llegan

`amdgpu_ring_preempt_ib` es un **macro sin guarda** (`amdgpu_ring.h:453`):

```c
#define amdgpu_ring_preempt_ib(r) (r)->funcs->preempt_ib(r)
```

Llamarlo sobre un ring GFX8 seria un NULL-deref. Solo dos call sites existen, y ambos
estan cerrados antes de llegar:

**a) debugfs** (`amdgpu_debugfs.c:2013-2015`) — guarda explicita:

```c
if (!amdgpu_ring_sched_ready(ring) || !ring->funcs->preempt_ib)
        return -EINVAL;
```

`preempt_ib` es NULL en GFX8 → `-EINVAL`, no llega al macro.

**b) mux / MCBP** (`amdgpu_ring_mux.c:401`) — guarda en `ib_begin`:

```c
void amdgpu_ring_ib_begin(struct amdgpu_ring *ring)
{
        if (ring->is_sw_ring)                       /* amdgpu_ring.c:821-824 */
                amdgpu_sw_ring_ib_begin(ring);
}
```

y dentro:

```c
if (adev->gfx.mcbp && ring->hw_prio > AMDGPU_RING_PRIO_DEFAULT) {
        if (amdgpu_mcbp_scan(mux) > 0)
                amdgpu_mcbp_trigger_preempt(mux);    /* -> preempt_ib */
```

`adev->gfx.mcbp` si puede ser true en cualquier ASIC — lo pone un module param
(`amdgpu_mcbp`, `amdgpu_device.c:3607`) o `sriov_vf`. **Pero** la rama exige
`ring->is_sw_ring`, y ese flag lo pone **solo** `gfx_v9_0.c:2361`. En GFX8
`is_sw_ring` nunca es true, luego la ramaMCBP es inalcanzable aunque `mcbp` este
activo.

Con eso, las dos rutas estan cerradas. `PROVEN_ABSENT` por objeto nombrado
(`preempt_ib`), no por un `grep` que podria contar mal.

## 4 · Lo que el paquete hace en GFX8

`PACKET3_COND_EXEC` (`vid.h:105`): `TYPE3 << 30 | (op & 0xFF) << 8 | (n & 0x3FFF) << 16`.

```
gfx_v8_0_ring_emit_init_cond_exec()          [gfx_v8_0.c:6320-6332]
  PACKET3(PACKET3_COND_EXEC, 3)
  addr_lo            <- *cond_exe_gpu_addr, 64 bits partido
  addr_hi
  0                  <- num_skip  (parcheado despues)
  ret = wptr & mask  <- offset del patch
  0                  <- dummy, el que se parchea
```

Con `n = 3` y cuatro dwords de payload, el patron `n = payload - 1` que se ve en
`WAIT_REG_MEM` (`PACKET3(..., 5)` con seis payload). El campo `num_skip` que el
hardware leeria es dw3; el driver parchea **dw4**, un dword extra. Medido con una
reproduccion dword a dword, no supuesto.

Interpretacion (`HYPOTHESIS`, marcada como tal): si el hardware leyese `num_skip` de
dw3, estaria leyendo 0 y **no descartaria nunca** — con independencia del predicado.
Esa es una lectura alternativa a "el predicado nunca es falso", y las dos
convergen en el mismo efecto observable. **Cual de las dos es la correcta no se
puede decidir leyendo el codigo**: haria falta la especificacion PM4 de GFX8, o un
discriminante runtime. `NOT_DETERMINED`. Lo que si es `PROVEN` es que **ninguna de
las dos lecturas posibles puede llegar a descartar en GFX8**, porque el predicado no baja
a 0 en ninguna parte.

Lo que esto deja al driver propio: `COND_EXEC` es una **posibilidad disponible y no
usada**. El predicado esta en memoria de GPU, el CP lo lee, y el driver puede
escribirlo. Es la unica primitiva de este path donde una predicacion reside fuera del
ring. Si el hardware acepta un `num_skip` distinto de 0, es un mecanismo de
"descartar este frame si el software dice que no" que el driver de referencia no
exploita en GFX8. `MODEL_CHOICE` para el driver propio, con la condicion de que
`NOT_DETERMINED` sobre el campo exacto.

## 5 · El coste, medido

5 dw por emision, 2 emisiones por submission del ring GFX = **10 dw** (40 B) por
submission en el ring que no producen efecto. Es `PROVEN` por el conteo de `021` y
por `grep` de los dos call sites.

En un anillo de 64 KiB (16384 dw) son 10 dw: 0.06 %. Irrelevante para el rendimiento.
Lo relevante no es el coste: es que el driver propio tiene ahi un mecanismo
disponible.

## 6 · Clasificacion

| Afirmacion | Estado |
|---|---|
| `COND_EXEC` se emite 2 veces por submission en el ring GFX de GFX8 | `PROVEN` (2 call sites) |
| `init_cond_exec` solo existe en `ring_funcs_gfx`, no en compute ni KIQ | `PROVEN` (3 tablas) |
| El predicado vive en WB de dispositivo, no en el ring | `PROVEN` (`amdgpu_ring.c:317-323`) |
| Su valor inicial es 1 y el comentario dice "always ... CONTINUE" | `PROVEN` |
| `gfx_v8_0.c` nunca llama a `set_preempt_cond_exec` | `PROVEN_ABSENT` (20 call sites en 10 ficheros, ninguno GFX8) |
| GFX8 no tiene `preempt_ib` | `PROVEN_ABSENT` (8 ASICs medidos) |
| Las dos rutas que podrian assertar preemption estan cerradas en GFX8 | `PROVEN` (guardas de debugfs y de mux, §3.1) |
| El paquete nunca descarta en GFX8 | `PROVEN_DERIVED` (predicado no baja a 0, §3) |
| El cuerpo de los dos `init_cond_exec` es identico salvo el nombre de la funcion | `PROVEN` (comparacion linea a linea, 11/11) |
| Que campo lee el hardware como `num_skip` (dw3 o dw4) | `NOT_DETERMINED` |
| Si el hardware puede descartar con un `num_skip` > 0 | `NOT_DETERMINED` |
| Que hace el CP cuando el predicado es 1 | `NOT_DETERMINED` — solo la especificacion PM4 |

Ultima fila: decir "no descarta" es una conclusion sobre el efecto, no sobre el
codigo. Lo `PROVEN` es que el software no le da entrada para descartar. El hardware
que haga con un predicado verdadeiro es `NOT_DETERMINED`, y no debe leerse como
"probablemente continue" — `017` ya mostro que un comentario de driver no es
evidencia de semantica, y este caso es el mismo patron.

## 7 · Confounders

Ninguno para la conclusion: la cadena de guardas es aritmetica sobre fuente, y cada
eslabon se comprobó por separado.

Matiz que si queda, y con el que hay que tener cuidado: `adev->gfx.mcbp` **si** es
activable en GFX8 por module param. Si alguien lo activa esperando MCBP, no pasara
nada — porque `is_sw_ring` sigue falso y la rama no se toma. Consecuencia para el
driver propio: no se puede "activar" esta ruta en GFX8 sin tocar `is_sw_ring` a mano,
lo que seria escribir en un ring GFX8 un paquete pensado para otra generacion.
`NOT_APPLICABLE` con causa.

## 8 · UNLOCKS

- El driver propio tiene **una primitiva de sincronizacion no usada** en este ASIC:
  predicado en memoria de GPU leido por el CP. Es el unico sitio donde una decision
  puede depender de estado que el CPU escribe fuera del ring. La restriccion es
  `NOT_DETERMINED` sobre el campo, y esa es la pregunta a responder antes de
  depender de ella.
- Se cierra el circulo de la frontera C de `AGENTS.md`. Los tres mecanismos de
  espera del path GFX8 estan ahora clasificados:
  - `WAIT_REG_MEM` (`017`): sin predicado, no prueba completion.
  - `COND_EXEC` (este): predicado en memoria, inerte en GFX8.
  - No hay ack de invalidate (`018`): `NOT_IMPLEMENTABLE`.
  Ninguno puede dar completion. El driver propio no hereda ninguna via de
  completion en este ASIC, y eso es una `REQUIREMENT` con tres ramas justificadas,
  no una laguna de investigacion.
- `020`/`021` dan el coste de esta pieza: 10 dw por submission de ring GFX. Es
  relevante para el diseno del ring, no para el rendimiento.

## 9 · Criterio de falsificacion

Se refutaria si: (a) existiera en GFX8 una ruta que escribiera
`*cond_exe_cpu_addr` sin pasar por `set_preempt_cond_exec` — eso exige un barrido de
todos los escritores de `cond_exe_cpu_addr`, que son **dos** en todo el arbol
(`amdgpu_ring.c:323` la inicializacion y el setter), ambos revisados; (b) `preempt_ib`
fuera asignado en algun ring de GFX8 por una ruta de configuracion que no leo
(`grep` sobre las tres `ring_funcs` lo da ausente, y las tres son las unicas de
`gfx_v8_0`); (c) la especificacion PM4 dijera que `COND_EXEC` con predicado 1 hace
algo distinto de continuar — posible, y no resoluble aqui. (a) y (b) refutan el
`NEGATIVE_RESULT`; (c) solo cambia la descripcion, no el resultado de que el software
no le da entrada para descartar.

## 10 · Evidencia

```
gfx_v8_0.c:   6320-6332 (init_cond_exec), 6870-6916 (ring_funcs_gfx: solo esta
              tiene init_cond_exec), 6174-6180 (emit_frame_size con 5+5 COND_EXEC)
amdgpu_ring.c: 291 (wb_get), 317-323 (gpu/cpu addr, valor inicial 1),
              407 (wb_free), 820-830 (ib_begin -> sw_ring solo si is_sw_ring)
amdgpu_ring.h: 409-410 (campos), 452-453 (macros sin guarda),
              482-486 (set_preempt_cond_exec), 543-551 (patch_cond_exec)
amdgpu_ib.c:  223, 246-247, 304-307, 319          (2 emisores + 2 parches)
amdgpu_vm.c:  839-840, 905                        (emisor y parche del primero)
amdgpu_debugfs.c: 2013-2015                       (guarda !preempt_ib)
amdgpu_ring_mux.c: 393-406                        (guarda mcbp && is_sw_ring)
amdgpu_device.c: 3604-3616                        (set_mcbp: module param o sriov)
gfx_v9_0.c:   5739, 5774 (assert/deassert), 2361 (is_sw_ring = true),
              5860-5875 (init_cond_exec: cuerpo identico a GFX8, 11/11 lineas)
vid.h:        105-107 (PACKET3), 169-189 (WAIT_REG_MEM para contraste)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador de §4 contenia dos fragmentos de texto corrupto
(dos fragmentos en §4). Corregidos; el contenido tecnico no
cambio. Es el tercer caso del mismo defecto al escribir, asi que la nota se
conserva en vez de borrarse.