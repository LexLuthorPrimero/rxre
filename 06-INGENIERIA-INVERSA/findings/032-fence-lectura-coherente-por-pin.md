# 032 · La lectura del fence es una lectura de CPU normal — y por qué funciona

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`COMPLEMENTS=031-rptr-wptr-tres-dominios.md` (§4 era `NOT_DETERMINED` sin causa
nombrada), `025-gart-invalidate-con-orden-cpu.md` §2

## CUDA principal

El completion del fence que `028` establecio como el mecanismo real **no usa ninguna
barrera en el camino de lectura**. El CPU hace, literalmente:

```c
while ((int32_t)(wait_seq - amdgpu_fence_read(ring)) > 0 && timeout > 0) {
        udelay(2);
        timeout -= 2;
}

static u32 amdgpu_fence_read(struct amdgpu_ring *ring)
{
        ...
        if (drv->cpu_addr)
                seq = le32_to_cpu(*drv->cpu_addr);     <-- LECTURA NORMAL
        ...
}
```

Sin `mb()`, sin `readl`, sin volatile. La garantia **no esta en el codigo del fence**:
esta en que la pagina que se lee es **coherente por construccion**, y eso lo resuelve el
`pin` del BO mas abajo en la cadena.

## Alcance exacto

1. Los dos caminos de lectura del fence (polling e interrupcion) y que tienen en comun.
2. La cadena de creacion del BO del writeback hasta el `pin`.
3. Por que una lectura normal de una pagina escrita por la GPU es valida aqui.
4. Que queda `NOT_DETERMINED` y por que.

## Criterio de terminacion (cumplido)

Los dos caminos de lectura transcritos, y la cadena `bo_create_kernel` →
`bo_create_reserved` → `bo_pin` → `bo_kmap` cerrada. Agotado.

---

## 1 · Los dos caminos, y por que es el mismo problema

### 1.1 · Polling

```c
/* amdgpu_fence.c:310-320 */
signed long amdgpu_fence_wait_polling(struct amdgpu_ring *ring,
                                      uint32_t wait_seq, signed long timeout)
{
        while ((int32_t)(wait_seq - amdgpu_fence_read(ring)) > 0 && timeout > 0) {
                udelay(2);
                timeout -= 2;
        }
        return timeout > 0 ? timeout : 0;
}
```

### 1.2 · Interrupcion

```c
/* amdgpu_fence.c:207-219 */
bool amdgpu_fence_process(struct amdgpu_ring *ring)
{
        ...
        do {
                last_seq = atomic_read(&ring->fence_drv.last_seq);
                seq = amdgpu_fence_read(ring);        <-- LA MISMA lectura
        } while (atomic_cmpxchg(&drv->last_seq, last_seq, seq) != last_seq);
        ...
}
```

### 1.3 · La lectura

```c
/* amdgpu_fence.c:79-89 */
static u32 amdgpu_fence_read(struct amdgpu_ring *ring)
{
        struct amdgpu_fence_driver *drv = &ring->fence_drv;
        u32 seq = 0;

        if (drv->cpu_addr)
                seq = le32_to_cpu(*drv->cpu_addr);
        else
                seq = atomic_read(&drv->last_seq);
        return seq;
}
```

Y la escritura, del lado del CPU (`amdgpu_fence_write`, `:63-69`):

```c
static void amdgpu_fence_write(struct amdgpu_ring *ring, u32 seq)
{
        if (drv->cpu_addr)
                *drv->cpu_addr = cpu_to_le32(seq);     <-- ESCRITURA NORMAL
}
```

`PROVEN`: **ambos lados, la escritura del CPU y la lectura del CPU, son asignaciones
normales de memoria.** No hay `writeq`, ni `readq`, ni `writel`, ni volatile, ni barrera
en ninguna de las dos.

Y `drv->cpu_addr` viene de `ring->fence_cpu_addr` (`amdgpu_fence.c:415-416`), que sale
de `amdgpu_ring_get_cpu_addr(ring, ring->fence_offs)` = `&adev->wb.wb[fence_offs]`
(`amdgpu_ring.c:299-300`, `:208-210`).

**Es decir: la pagina es la misma que la del `wptr` y la del `rptr` de `031`**, la del
BO del writeback. Una sola pagina, tres usos, todos con acceso normal.

## 2 · Donde esta la garantia: el pin

La garantia no esta en el codigo del fence. Esta en la creacion del BO
(`amdgpu_device.c:1041-1046`):

```c
r = amdgpu_bo_create_kernel(adev, AMDGPU_MAX_WB * sizeof(uint32_t) * 8,
                            PAGE_SIZE, AMDGPU_GEM_DOMAIN_GTT,
                            &adev->wb.wb_obj, &adev->wb.gpu_addr,
                            (void **)&adev->wb.wb);
```

`amdgpu_bo_create_kernel` delega en `amdgpu_bo_create_reserved`
(`amdgpu_object.c:337-346`), y **ahi** esta la garantia:

```c
int amdgpu_bo_create_reserved(...)
{
        ...
        bp.flags = cpu_addr ? AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED
                : AMDGPU_GEM_CREATE_NO_CPU_ACCESS;
        ...
        r = amdgpu_bo_create(adev, &bp, bo_ptr);
        r = amdgpu_bo_reserve(*bo_ptr, false);
        r = amdgpu_bo_pin(*bo_ptr, domain);        <-- ttm_bo_pin: pagina COHERENTE
        r = amdgpu_ttm_alloc_gart(&(*bo_ptr)->tbo); <-- bind en el GART
        *gpu_addr = amdgpu_bo_gpu_offset(*bo_ptr);
        if (cpu_addr)
                r = amdgpu_bo_kmap(*bo_ptr, cpu_addr);   <-- ttm_bo_kmap
        ...
}
```

**CORRECCION PROPIA**: mi primera lectura de este documento decia que
`amdgpu_bo_create_kernel` "nunca pinnea". Falso, y lo dije porque mire el nombre de la
funcion y no su cuerpo. `bo_create_kernel` es un envoltorio de tres lineas sobre
`bo_create_reserved`, y el `pin` esta ahi (`amdgpu_object.c:279`). Lo mismo me paso con
`031` al buscar `get_cpu_addr` en la cabecera equivocada: existe en `amdgpu_ring.c`, no
en `amdgpu_ring.h`.

El pin es lo que convierte el mapeo en coherente. `amdgpu_bo_pin` termina en
`ttm_bo_pin(&bo->tbo)`, y `ttm_bo_pin` es el punto donde TTM garantiza que las paginas
no se mueven mientras el BO esta pinneado. Con la pagina fija y mapeada, una escritura
del dispositivo es visible para el CPU sin ninguna operacion de cache.

`PROVEN_DERIVED`, y con una dependencia que nombro: el codigo de amdgpu **delega** esa
propiedad en TTM/DRM. Que `ttm_bo_pin` produzca un mapeo coherente es una propiedad del
subsistema de memoria de Linux, no de amdgpu. Es la misma clase de dependencia que
`031` §4 tiene con `writel`.

## 3 · La cadena completa

```
amdgpu_device_wb_init()                        [amdgpu_device.c:1037]
  amdgpu_bo_create_kernel(32768, GTT)
    -> amdgpu_bo_create_reserved()
         bp.flags |= AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED
         amdgpu_bo_create()                    crea el objeto
         amdgpu_bo_pin()                       ttm_bo_pin  -> PAGINA FIJA
         amdgpu_ttm_alloc_gart()               lo liga al GART, direccion GPU
         amdgpu_bo_kmap()                      ttm_bo_kmap -> MAPA PARA CPU
  memset(wb, 0, 32768)                        lo pone a 0

amdgpu_ring_init()                             [amdgpu_ring.c:297-300]
  ring->fence_cpu_addr = &wb.wb[fence_offs]   puntero de CPU

amdgpu_fence_driver_start_ring()              [amdgpu_fence.c:415]
  ring->fence_drv.cpu_addr = ring->fence_cpu_addr

el hardware escribe            -> la pagina del fence, via la direccion GPU
el CPU lee                     -> *drv->cpu_addr, lectura normal
```

Todo el que `031` llamo `writel` a doorbell es para el **wptr**, no para el
**fence**. Son dos mecanismos distintos y no deben confundirse:

| | para que | dominio | acceso del CPU |
|---|---|---|---|
| `fence_cpu_addr` | secuencia de completitud | GTT (mapeado coherente) | lectura normal |
| `doorbell.cpu_addr` | hacer sonar el timbre al CP | `AMDGPU_PL_DOORBELL` | `writel` |

El fence **no necesita `writel`** porque no es una puerta: es un buzon. El hardware
deposita un valor y el CPU lo lee cuando quiere. El `wptr` si necesita `writel` porque
si es una puerta: sin ella el CP no sabe que hay trabajo.

## 4 · Que queda `NOT_DETERMINED`

La garantia queda **acotada**, no cerrada:

| afirmacion | estado |
|---|---|
| Ambos lados del fence usan acceso normal de memoria | `PROVEN` |
| La pagina del fence es la del BO del writeback | `PROVEN` |
| Ese BO se pinnea en `bo_create_reserved` | `PROVEN` |
| Con la pagina pinneada, una escritura del dispositivo es visible para el CPU | `DERIVATION` — propiedad de TTM/DRM |
| Que en esta placa el Hardware escriba realmente en esa pagina | `NOT_DETERMINED` |
| Que no haya una segunda copia en cache de CPU que tape la lectura | `NOT_DETERMINED` — coherente por pin, pero no medido |

Las dos ultimas filas son lo que impide decir `PROVEN`. Un pin garantiza que la pagina
no se mueve; no garantiza por si solo que el camino de escritura del dispositivo a esa
pagina sea coherente en esta plataforma concreta. Eso es coherencia CPU↔GPU sobre GART,
y es el mismo limite que `025` §2 y `031` §4 ya nombraron para sus mecanismos.

**Consolidado**: hay **tres** mecanismos de sincronizacion en este ASIC, con garantias
de distinto grado:

```
fence    : buzon en pagina pinneada.   garantia: TTM.        NOT_DETERMINED el hardware
wptr     : puerta en apertura MMIO.     garantia: plataforma. NOT_DETERMINED
invalidate: no hay.                     garantia: ninguna.    NOT_IMPLEMENTABLE
```

Los tres tienen su limite nombrado y **los tres estan bloqueados por la misma causa
faltante**: la semantica de hardware de esta placa, que no esta en el corpus. Es un
`BLOCKED` unico con tres manifestationes, no tres bloqueos distintos.

## 5 · Clasificacion

| afirmacion | estado |
|---|---|
| `amdgpu_fence_read` es una lectura de CPU normal | `PROVEN` |
| `amdgpu_fence_write` es una escritura de CPU normal | `PROVEN` |
| Polling e interrupcion usan la misma lectura | `PROVEN` |
| La pagina del fence es la del BO del writeback | `PROVEN` |
| El BO se pinnea en `bo_create_reserved` | `PROVEN` — corrige mi error de este doc |
| Que pin implica coherencia CPU↔GPU | `DERIVATION` — delegacion en TTM/DRM |
| Que el fence necesite `writel` | `REFUTED` — es un buzon, no una puerta |
| Que el fence y el doorbell compartan mecanismo | `REFUTED` — dominios y roles distintos |
| Que el hardware escriba correctamente en esa pagina | `NOT_DETERMINED` |

## 6 · Confounders

- La propiedad de coherencia viene de `ttm_bo_pin`, que esta **fuera del corpus**: el
  arbol `drivers/gpu/drm/amd` de esta copia no incluye `ttm/`. Verificado: no existe
  `ttm_amdgpu.c` en `RESEARCH/working/linux-7.1.3/`. Es una `LIMITATION` del corpus, y
  la conclusion sobre `pin` es por tanto `DERIVATION` y no `PROVEN`.
- El resto del subsistema de memoria de Linux (mm, DRMM) tampoco esta. La cadena se
  cierra en el borde del corpus, que es donde termina `amdgpu_bo_pin`.
- Que el fence se lea sin volatile no es un problema en x86: una lectura de memoria
  normal no es reordenable respecto a otras. En una arquitectura debilaria haria falta
  `READ_ONCE` o equivalente. `HYPOTHESIS` sobre el motivo, `PROVEN` sobre el codigo.

## 7 · UNLOCKS

- El driver propio puede implementar el fence **exactamente igual**: una pagina pinneada,
  el hardware deposita un secuencial, el CPU lee un entero normal en bucle. Es el
  mecanismo mas simple y el que ya funciona.
- Los tres mecanismos de sincronizacion quedan **clasificados por grado de garantia** en
  una tabla, que es lo que el driver propio necesita para decidir donde apoyarse.
- El `BLOCKED` unico queda nombrado con precision: **falta la semantica de hardware de
  esta placa**, y afecta a fence, wptr e invalidate por igual. Eso convierte tres
  preguntas abiertas en una sola, con un solo discriminante que las resolveria: medir
  una vez con instrumentacion, y las tres caen.
- `031` §4 puede ahora decir donde acaba su `NOT_DETERMINED`: no en el codigo de
  amdgpu, sino en `ttm_bo_pin` y en la semantica de la apertura de doorbell.

## 8 · Criterio de falsificacion

Se refutaria si: (a) `ttm_bo_pin` no produjera un mapeo coherente — eso dejaria el fence
sin garantia y seria un fallo grave del subsistema de memoria, refutable leyendo
`drivers/gpu/drm/ttm/ttm_bo.c`, que **no esta en este corpus**; (b) el hardware
escribiera el fence por un camino que no pase por la pagina mapeada (por ejemplo, un
canal de MMIO que copie a otro sitio) — refutable solo con instrumentacion; (c) existiera
una lectura del fence con barrera en alguna ruta que no haya seguido — el barrido de
`amdgpu_fence_read` dio 5 usos, todos en `amdgpu_fence.c`, y todos pasan por la misma
funcion. (a) y (b) son `NOT_DETERMINED` por limite del corpus y por hardware
respectivamente.

## 9 · Evidencia

```
amdgpu_fence.c:   63-69 (fence_write: asignacion normal),
                  79-89 (fence_read: lectura normal),
                  207-219 (fence_process: usa fence_read),
                  310-320 (wait_polling: bucle con fence_read),
                  415-416 (fence_drv.cpu_addr = ring->fence_cpu_addr)
amdgpu_ring.c:    208-210 (get_cpu_addr = &wb.wb[offset]),
                  297-300 (fence_cpu_addr = get_cpu_addr(fence_offs))
amdgpu_device.c:  1037-1057 (wb_init: bo_create_kernel + memset)
amdgpu_object.c:  337-346 (bo_create_kernel -> bo_create_reserved),
                  279 (bo_pin DENTRO de bo_create_reserved)  <-- la garantia,
                  396-... (bo_kmap)
LIMITACION:       ttm/ no esta en el corpus -> la coherencia de pin es DERIVATION
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.