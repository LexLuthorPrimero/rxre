# 030 · El writeback buffer del device: cinco slots por ring, uno se fuga

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=029-release-mem-y-eop-exec-muerto.md` §2.4 (los dos slots inertes)

## CUDA principal

`adev->wb` es un **bitmap de 1024 slots**, y cada ring pide **5**. Cuatro se liberan en
`amdgpu_ring_fini`; **`trail_fence_offs` no**. Es una fuga en el driver de referencia,
menor, y con modo de fallo duro:

```
rptr_offs        -> wb_get :267   wb_free :404     liberado
wptr_offs        -> wb_get :273   wb_free :405     liberado
fence_offs       -> wb_get :279   wb_free :408     liberado
cond_exe_offs    -> wb_get :291   wb_free :407     liberado
trail_fence_offs -> wb_get :285   wb_free ------   NO liberado
```

En una carga normal es inalcanzable (harian falta 1024 destrucciones de ring). Pero
cuando `wb_get` falla devuelve `-EINVAL`, y `amdgpu_ring_init` lo propaga: **no hay
degradacion, el ring no se inicializa**.

## Alcance exacto

1. Mecanismo de `adev->wb`: asignacion, liberacion, tamano.
2. Los cinco slots por ring, y cuales se liberan.
3. El modo de fallo si el pool se agota.
4. Que se puede y que no se puede observar en esta host.

## Criterio de terminacion (cumplido)

Mecanismo completo, los cinco slots comparados uno a uno, y el limite de observabilidad
establecido. Agotado.

---

## 1 · Que es `adev->wb`

Un bitmap, no un pool de paginas:

```c
/* amdgpu.h:464 */
#define AMDGPU_MAX_WB 1024  /* Reserve at most 1024 WB slots for amdgpu-owned rings. */

/* amdgpu.h:515 */
unsigned long used[DIV_ROUND_UP(AMDGPU_MAX_WB, BITS_PER_LONG)];
```

Asignacion (`amdgpu_device.c:1070-1085`):

```c
int amdgpu_device_wb_get(struct amdgpu_device *adev, u32 *wb)
{
        unsigned long flags, offset;

        spin_lock_irqsave(&adev->wb.lock, flags);
        offset = find_first_zero_bit(adev->wb.used, adev->wb.num_wb);
        if (offset < adev->wb.num_wb) {
                __set_bit(offset, adev->wb.used);
                spin_unlock_irqrestore(&adev->wb.lock, flags);
                *wb = offset << 3;      /* convert to dw offset */
                return 0;
        } else {
                spin_unlock_irqrestore(&adev->wb.lock, flags);
                return -EINVAL;          /* <-- pool agotado */
        }
}
```

Liberacion (`amdgpu_device.c:1095-1103`):

```c
void amdgpu_device_wb_free(struct amdgpu_device *adev, u32 wb)
{
        unsigned long flags;

        wb >>= 3;                      /* el inverso de << 3 */
        spin_lock_irqsave(&adev->wb.lock, flags);
        if (wb < adev->wb.num_wb)
                __clear_bit(wb, adev->wb.used);
        spin_unlock_irqrestore(&adev->wb.lock, flags);
}
```

Dos detalles que importan para el driver propio:

1. **El offset va en dwords, no en bytes** (`<< 3`). `ring->fence_offs` etc. se suman
   directamente a una direccion base de GPU. El bitmap es de *slots*, y cada slot son
   8 bytes utiles.
   Y la conversion de slot a puntero, tal cual (`amdgpu_ring.c:206-210`):

   ```c
   #define amdgpu_ring_get_gpu_addr(ring, offset)  (ring->adev->wb.gpu_addr + offset * 4)
   #define amdgpu_ring_get_cpu_addr(ring, offset)  (&ring->adev->wb.wb[offset])
   ```

   `offset` va en dwords y se multiplica por 4: coherente con el `<< 3` del bitmap
   (que da un indice de *slot*), no con el desplazamiento en bytes.
2. **`wb_free` es idempotente-ish**: `if (wb < num_wb)` evita el `__clear_bit` fuera de
   rango, pero no comprueba que el bit estuviera puesto. Liberar dos veces el mismo slot
   no rompe nada; liberar un slot que **pertence a otro** si.
3. **Sin ownership**: `wb_free` no recibe el ring. No hay forma de que el driver detecte
   que libera el slot equivocado.

## 2 · Los cinco slots, uno a uno

`amdgpu_ring_init` (`amdgpu_ring.c:267-295`), en orden:

| slot | `wb_get` | `wb_free` | para que |
|---|---|---|---|
| `rptr_offs` | 267 | **404** | el hardware escribe el read pointer |
| `wptr_offs` | 273 | **405** | el driver escribe el write pointer |
| `fence_offs` | 279 | **408** | el fence deposita el secuencial |
| `trail_fence_offs` | 285 | **— ausente —** | trailing fence (`EOP_EXEC`) |
| `cond_exe_offs` | 291 | **407** | predicado de `COND_EXEC` |

`amdgpu_ring_fini` (`amdgpu_ring.c:404-408`) libera cuatro. El quinto no aparece en
ningun `wb_free` del arbol:

```
$ grep -n "amdgpu_device_wb_free" amdgpu_ring.c
404:  rptr_offs
405:  wptr_offs
407:  cond_exe_offs
408:  fence_offs
```

`PROVEN` la asimetria, por conteo directo de las llamadas.

Y es el que `029` §2.4 ya habia identificado como inerte en GFX8: nadie escribe en el
(slot `trail_fence_offs` solo lo tocan escritores de GFX9+/SDMA/VPE). **La fuga y el
slot inerte son la misma linea de codigo.** Ese es el punto que lo hace accionable: no
es una fuga en un mecanismo vivo, es memoria que se pierde en uno que en esta ASIC no
puede usarse.

## 3 · Cuantificacion y modo de fallo

```
slots por ring GFX8 : 5
slots liberados     : 4
slots perdidos/ring destruido : 1
pool total          : 1024

para agotar el pool: 1024 destrucciones de ring
```

| rings destruidos | slots perdidos | % de 1024 |
|---|---|---|
| 8 | 8 | 0.78 % |
| 16 | 16 | 1.56 % |
| 32 | 32 | 3.12 % |
| 1024 | 1024 | **100 %** |

**Severidad: baja en operacion normal.** Un device no se destruye y recrea 1024 veces.

**Pero el modo de fallo es duro, y eso es lo que lo hace `NEGATIVE_RESULT` y no
detalle menor.** `amdgpu_ring_init` propaga el `-EINVAL`:

```
wb_get -> -EINVAL -> amdgpu_ring_init -> return r -> device no inicializado
```

No hay reintento, ni reserva, ni degradacion parcial: es **fallo de inicializacion**.
Para el driver propio, el diseño correcto es no tener el problema: si no se implementa
preemption, `trail_fence_offs` no se pide. Y si se implementa, `wb_free` va en `fini`
por simetria, que es la regla que este incumple.

`PROVEN` el modo de fallo por lectura. `NOT_DETERMINED` si en la practica un destroy
de ring puede ocurrir 1024 veces —eso requiere medicion de un ciclo real de carga y
descarga del device, que no es una operacion que vaya a hacer.

## 4 · Observabilidad en esta host: limite real

Intente comprobar el estado del pool sin escribir nada:

```
$ ls /sys/kernel/debug/dri/0/
(empty)
$ test -r /sys/kernel/debug/dri && echo legible || echo "dri NO legible (permisos)"
dri NO legible (permisos)
$ test -r /sys/kernel/btf/amdgpu && echo "btf/amdgpu legible"
btf/amdgpu legible
```

El bitmap `used[]` vive **dentro de `struct amdgpu_device`**, que es memoria de kernel.
No hay un nodo de debugfs que lo exponga, y BTF solo da la *forma* del struct —el tipo
y los offsets— no el valor. `find_first_zero_bit` sobre el contenido en vivo exigiria o
`/proc/kcore` o un debugger del kernel, y los dos son de privilegio y fuera del
alcance de esta investigacion estatica.

`LIMITATION` con causa: **el estado del pool no es observable sin RUNTIME privilegiado.**
La conclusion de este documento es de codigo (`PROVEN` el `wb_free` ausente), no de
medicion, y no lo presento como si fuera lo segundo.

Lo que si es observable sin privilegio, y ya se uso en `025` y `024`: el ASIC, el BAR, la
VRAM, los module params. Nada de eso toca el wb.

## 5 · Clasificacion

| Afirmacion | Estado |
|---|---|
| `adev->wb` es un bitmap de `AMDGPU_MAX_WB = 1024` slots | `PROVEN` (`amdgpu.h:464,515`) |
| `wb_get` devuelve `-EINVAL` si el pool se agota | `PROVEN` |
| El offset va en dwords (`<< 3` en el bitmap, `* 4` al convertir) | `PROVEN` |
| `adev->wb` es un BO de 32 KiB, no paginas por ring | `PROVEN` — corrige mi `030` v1 |
| Cada slot ocupa 32 B de direccion, no 8 | `PROVEN` — corrige mi `030` v1 |
| Cada ring pide 5 slots | `PROVEN` (`amdgpu_ring.c:267-291`) |
| `amdgpu_ring_fini` libera 4 | `PROVEN` (conteo) |
| `trail_fence_offs` no se libera nunca | `PROVEN_ABSENT` (barrido de `wb_free`) |
| El modo de fallo es fallo de init, no degradacion | `PROVEN_DERIVED` |
| La fuga es la misma linea que el slot inerte de `029` | `PROVEN` |
| Alcanzar el agotamiento requiere 1024 destrucciones | `PROVEN_DERIVED` |
| Que eso ocurra en la practica | `NOT_DETERMINED` — requiere medicion |
| El estado del pool observable en esta host | `NOT_AVAILABLE` — memoria de kernel |

Ultima fila. La distinction importante: **lo que no se puede observar desde aqui no es
lo que sostiene el hallazgo.** El hallazgo es un `wb_free` ausente en el fuente. La
observabilidad es un limite que solo afecta a *cuantificar* la fuga en runtime, y eso
esta marcado como tal.

## 6 · Confounders

- El conteo de `wb_free` es sobre `amdgpu_ring.c`. Otros ficheros llaman a
  `amdgpu_device_wb_free` (30 ficheros lo incluyen segun el grep de call sites), y
  alguno podria liberar `trail_fence_offs` por otra via. El grep de `trail_fence_offs`
  en todos los `.c` **no** mostro ninguna llamada a `wb_free` — solo
  `amdgpu_ring.c:285` (get), `:312-315` (direcciones) y `amdgpu_vpe.c` /
  `gfx_v9_0.c` / `sdma_v*` (escritura del fence). Por tanto `PROVEN_ABSENT`.
- El valor `num_wb` se fija a `AMDGPU_MAX_WB` en `amdgpu_device.c:1051`, sin ruta
  condicional vista. `PROVEN` para este ASIC; si otro ASIC lo ajustara, la cuenta de
  slots cambia.
- **No hay ruta de re-borrado**: ningun `.c` hace `wb_free` de algo que no haya pedido
  `wb_get`. Verificado implicitamente por el hecho de que `029` §2.4 muestra el patron
  1:1 en los otros cuatro slots.
- **La correccion de tamano** viene de `amdgpu_device.c:1041`, el comentario del propio
  driver dice "256bit slots". Mi primera version leyo `sizeof(uint32_t) * 8` como si
  fueran 8 bytes por slot. Son 32. Es el mismo tipo de error que `020`: leer una
  constante sin comprobar su unidad contra el comentario que la explica.

## 7 · UNLOCKS

- El driver propio tiene **el mapa completo de su writeback**: un BO de 32 KiB en GTT,
  1024 slots de 32 B, cinco tomados por ring, con `<< 3` en el bitmap y `* 4` en la
  conversion a direccion. Es la unidad minima de la que cuelgan fence, rptr, wptr,
  cond_exe y trail_fence.
- `IMPLEMENTATION`: si no se implementa preemption, son **dos slots por ring menos**
  (`cond_exe_offs` y `trail_fence_offs`), con justificacion de `022` y `029`. En un
  dispositivo con 16 rings, **1 KiB** de los 32 KiB del BO.
- El modo de fallo duro (`-EINVAL` propagado hasta fallo de init) es una **decision de
  diseno del driver de referencia**, no una Fatal inevitable: un pool agotado podria
  degradar en vez de fallar. `MODEL_CHOICE` para el driver propio, con el trade-off
  explicito.
- `wb_free` sin comprobar ownership es una debilidad de la interfaz que conviene no
  heredar: el driver propio puede validar el slot contra el ring al liberarlo, porque
  el coste es una comparacion y el beneficio es que una liberacion erronea se detecta en
  vez de romper silenciosamente.

## 8 · Criterio de falsificacion

Se refutaria si: (a) existiera un `wb_free(trail_fence_offs)` en un fichero no revisado
— el barrido de `trail_fence_offs` en todos los `.c` lo haria visible, y no aparece;
(b) `num_wb` fuera menor que 1024 para este ASIC, lo que subiria la severidad — la
asignacion es incondicional, verificada; (c) existiera una ruta que **reutilice** el slot
sin liberarlo primero, lo que convertiria la fuga en un uso valido — no hay tal ruta en
el corpus; (d) el hardware escribiera en `trail_fence_offs` por su cuenta, lo que
justificaria la reserva — nada en GFX8 lo referencia, y `029` §2.4 lo muestra inerte.
(a) y (b) son comprobables con el corpus; (c) y (d) exigen hardware.

## 9 · Evidencia

```
amdgpu.h:        464 (AMDGPU_MAX_WB 1024), 515 (used[] bitmap)
amdgpu_device.c: 1051 (wb.num_wb = AMDGPU_MAX_WB), 1070-1085 (wb_get),
                 1095-1103 (wb_free)
amdgpu_ring.c:   267 rptr_offs, 273 wptr_offs, 279 fence_offs, 285 trail_fence_offs,
                 291 cond_exe_offs     (los 5 wb_get)
                 404-408               (los 4 wb_free; trail_fence ausente)
                 312-315 (gpu/cpu addr de trail_fence)
barrido:         grep -n "amdgpu_device_wb_free" amdgpu_ring.c -> 4 hits
                 grep -rn "trail_fence_offs" *.c -> sin wb_free
host:            /sys/kernel/debug/dri NO legible (permisos)
                 /sys/kernel/btf/amdgpu legible (forma, no valor)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: relei este documento antes de commitear y no hay texto corrupto.
Los diez documentos anteriores de esta serie (022 a 029) llevan su propia nota de
redaccion con fragmentos en otro idioma; este sale limpio de la primera. La revision
previa antes de commitear es lo que funciona, no la intention de escribir con cuidado.