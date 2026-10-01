# 031 · `rptr` y `wptr`: tres dominios de memoria, y ningún `mb()` entre ellos

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=030-writeback-buffer-wb-slots.md`, `028-fence-completion-orden-d.md`

## CUDA principal

El estado de control de un ring GFX8 vive en **tres dominios de memoria distintos**, y
la secuencia de commit los recorre sin un unico `mb()` explicito en el path del ring:

```
1. ring->ring            BO en GTT          el CPU escribe con ring->ring[wptr++]
2. wptr_cpu_addr         BO en GTT          *addr = wptr        (memoria normal)
3. doorbell.cpu_addr     BO en DOORBELL     writel()            (MMIO de dispositivo)
```

`gfx_v8_0_ring_set_wptr_compute` son **dos escrituras a dos dominios distintos**, y la
segunda es la que hace sonar el timbre. El hardware recibe el doorbell, y para poder
interpretarlo necesita ver el valor de `wptr` — que esta en **otra pagina, en otra
BO, en otro dominio**.

Que eso funcione en esta placa es `OBSERVED` (el equipo funciona). Por que funciona es
`NOT_DETERMINED`, y la razon probable —`writel` a la apertura de doorbells actua como
barrera de escritura del bus del PCIe, no como una simple escritura— es `HYPOTHESIS`
con respaldo en la plataforma pero **no** en el codigo de amdgpu.

## Alcance exacto

1. Los tres dominios y de que BO/domain salen.
2. La secuencia exacta de `set_wptr` y `get_rptr`.
3. Que mecanismo de orden existe, si existe alguno en el driver.
4. Que es `PROVEN` y que no.

## Criterio de terminacion (cumplido)

Los tres dominados estan localizados con su BO y su `mem_type`, y la secuencia de
escritura esta medida. Agotado.

---

## 1 · Los tres dominios

### 1.1 · El ring mismo

```c
/* amdgpu_ring.c:361-366 */
amdgpu_bo_create_kernel(adev, ring->ring_size + ring->funcs->extra_bytes,
                        PAGE_SIZE,
                        AMDGPU_GEM_DOMAIN_GTT,        <-- GTT
                        &ring->ring_obj, &ring->gpu_addr,
                        (void **)&ring->ring);
```

El driver escribe con `amdgpu_ring_write` (`amdgpu_ring.h`):

```c
static inline void amdgpu_ring_write(struct amdgpu_ring *ring, uint32_t v)
{
        ring->ring[ring->wptr++ & ring->buf_mask] = v;   <-- memoria NORMAL
        ring->wptr &= ring->ptr_mask;
        ring->count_dw--;
}
```

**Escritura a memoria normal, no a MMIO.** Sin `writel`, sin volatile, sin nada. El
driver escribe el IB como si fuera RAM, y el hardware lo lee desde alli. Eso funciona
porque la pagina esta pinned y mapeada de forma coherente — `coherent` por el pinning, no
por el codigo.

### 1.2 · Los slots del writeback

```c
/* amdgpu_device.c:1041-1046 */
r = amdgpu_bo_create_kernel(adev, AMDGPU_MAX_WB * sizeof(uint32_t) * 8,
                            PAGE_SIZE,
                            AMDGPU_GEM_DOMAIN_GTT,        <-- GTT, el mismo dominio
                            &adev->wb.wb_obj, &adev->wb.gpu_addr,
                            (void **)&adev->wb.wb);
```

Mismo dominio que el ring. `wptr_cpu_addr = &wb.wb[wptr_offs]` — **memoria normal**.

### 1.3 · El doorbell — aqui cambia

```c
/* amdgpu_doorbell_mgr.c:165-171 */
r = amdgpu_bo_create_kernel(adev, size, PAGE_SIZE,
                            AMDGPU_GEM_DOMAIN_DOORBELL,   <-- OTRO dominio
                            &adev->doorbell.kernel_doorbells, NULL,
                            (void **)&adev->doorbell.cpu_addr);
```

Y `AMDGPU_GEM_DOMAIN_DOORBELL` mapea a un `mem_type` propio:

```c
/* amdgpu_object.c:1569 */
case AMDGPU_GEM_DOMAIN_DOORBELL:  return AMDGPU_PL_DOORBELL;
```

Con su propio sitio en la tabla de colocaciones (`amdgpu_object.c:148-154`,
`fpfn = 0, lpfn = 0, mem_type = AMDGPU_PL_DOORBELL`). Es una region del mapa de
memoria del dispositivo, no RAM asignada por el SO.

El acceso lo hace `amdgpu_mm_wdoorbell` (`amdgpu_doorbell_mgr.c:59-70`):

```c
void amdgpu_mm_wdoorbell(struct amdgpu_device *adev, u32 index, u32 v)
{
        if (amdgpu_device_skip_hw_access(adev)) return;
        if (index < adev->doorbell.num_kernel_doorbells)
                writel(v, adev->doorbell.cpu_addr + index);    <-- writel, no asignacion
        else
                dev_err(...);
}
```

`writel` — una **escritura de dispositivo**, con las barreras que implica en la
plataforma x86.

## 2 · La secuencia

Hay **dos** versiones de `set_wptr` en GFX8, y la diferencia importa mas que la
simetria anterior.

### 2.0 · La cuarta via: `mmCP_RB0_WPTR`

`gfx_v8_0_ring_set_wptr_gfx` (`gfx_v8_0.c`) tiene dos ramas:

```c
static void gfx_v8_0_ring_set_wptr_gfx(struct amdgpu_ring *ring)
{
        struct amdgpu_device *adev = ring->adev;

        if (ring->use_doorbell) {
                *ring->wptr_cpu_addr = lower_32_bits(ring->wptr);
                WDOORBELL32(ring->doorbell_index, lower_32_bits(ring->wptr));
        } else {
                WREG32(mmCP_RB0_WPTR, lower_32_bits(ring->wptr));
                (void)RREG32(mmCP_RB0_WPTR);        <-- LECTURA DE CONFIRMACION
        }
}
```

La rama `else` **no toca el writeback en absoluto**: escribe el `wptr` directamente en
el registro del hardware y **vuelve a leerlo**. Esa lectura no es un descuido: es un
`write-read barrier` clasico —el patron de "escribe, lee lo mismo, y el hecho de que
vuelva a salir garantiza que la escritura paso".

Es la **unica garantia de orden explicita del driver en todo el path del ring**, y esta
en la rama que **no se usa en GFX8**. `PROVEN` por lectura.

**Comprobado: `use_doorbell` es TRUE en GFX8, en los dos rings.** Y no hay duda:

```c
/* gfx_v8_0.c:1862, en gfx_v8_0_compute_ring_init */
ring->use_doorbell = true;
ring->doorbell_index = adev->doorbell_index.mec_ring0 + ring_id;

/* gfx_v8_0.c:1973, en el init del gfx ring */
if (adev->asic_type != CHIP_TOPAZ) {          /* solo Island lo excluye */
        ring->use_doorbell = true;
        ring->doorbell_index = adev->doorbell_index.gfx_ring0;
}
```

`PROVEN`. La rama `else` con `WREG32` + `RREG32` **no se ejecuta en Polaris12**: es
codigo muerto en esta ASIC.

Eso **refuerza** el punto y lo hace mas incomodo para el driver de referencia de lo que
parecia a primera vista: el patron de garantia explicita mas fuerte que el driver
conoce —escribir el registro y releerlo— esta disponible, esta escrito, a treinta lineas
de distancia, y no se usa. El driver prefiere depender de la semantica de `writel`.

Lo que deja la conclusion de §4 intacta y ahora con el caso concreto: **la rama viva es
la que depende de una propiedad de la plataforma, no la que la exige.**

### 2.1 · La version de compute

`gfx_v8_0_ring_set_wptr_compute` (`gfx_v8_0.c`), la que usa el ring de compute:

```c
static void gfx_v8_0_ring_set_wptr_compute(struct amdgpu_ring *ring)
{
        struct amdgpu_device *adev = ring->adev;

        /* XXX check if swapping is necessary on BE */
        *ring->wptr_cpu_addr = lower_32_bits(ring->wptr);        <- (a) GTT
        WDOORBELL32(ring->doorbell_index, lower_32_bits(ring->wptr));  <- (b) DOORBELL
}
```

Dos escrituras:

| paso | destino | dominio | tipo de acceso |
|---|---|---|---|
| (a) | `wptr_cpu_addr` | `GTT` | asignacion normal |
| (b) | `doorbell.cpu_addr + index` | `DOORBELL` | `writel` |

Y `WDOORBELL32` es `amdgpu_mm_wdoorbell(adev, index, v)` (`amdgpu_doorbell.h:398`).

**Entre (a) y (b) no hay `mb()`, ni `wmb()`, ni nada.** `PROVEN` por lectura.

### 2.2 · Y donde si hay `mb()`

El `mb()` esta **un nivel mas arriba**, en `amdgpu_ring_commit`:

```c
void amdgpu_ring_commit(struct amdgpu_ring *ring)
{
        ...
        if (count != 0)
                ring->funcs->insert_nop(ring, count);   /* padding a fetch size */

        mb();
        amdgpu_ring_set_wptr(ring);
        ...
}
```

O sea: el `mb()` esta **antes** de llamar a `set_wptr`, es decir antes de (a). No esta
entre (a) y (b). Ese matiz es el punto: el driver ordena "todo lo que escribi en el
ring, antes de tocar el wptr", y **no** ordena "el wptr, antes del doorbell" — porque
esas dos son la misma operacion logica y el driver asume que la escritura MMIO de (b)
es barrier suficiente.

El comentario `/* We pad to match fetch size */` explica el `insert_nop`: el ring se
rellena hasta el tamano de fetch del hardware para que el CP no lea a mitad.

## 3 · `get_rptr`: la otra mitad de la asimetria

```c
/* gfx_v8_0.c:6006 */
static u64 gfx_v8_0_ring_get_rptr(struct amdgpu_ring *ring)
{
        return *ring->rptr_cpu_addr;
}
```

Una lectura y nada mas. **No hay `update_rptr`** — el campo no existe en las
`ring_funcs` de GFX8 ni en ninguna otra generacion de este corpus (`grep` sobre
`*.c`: 0). El hardware escribe el `rptr` por su cuenta en esa pagina del writeback, y
el driver lo lee.

Asimetria completa:

```
rptr  :  push=false   el HARDWARE escribe, el CPU lee
wptr  :  push=true    el CPU escribe (GTT) + MMIO (DOORBELL)
```

**`rptr` no necesita puerta porque el hardware lo anuncia.** El `wptr` si la necesita
porque el hardware no puede leer la variable de CPU por otra via. Esa es la razon de
que exista el doorbell, y no es una conjetura: se deduce de que `get_rptr` sea una
lectura simple y `set_wptr` sean dos escrituras.

`DERIVATION`, marcada como tal. El codigo no dice "por eso hay doorbell"; la
estructura del codigo lo implica y es la unica explicacion que encaja sin hypotheses
adicionales.

## 4 · Que garantia existe, y cual no

| afirmacion | estado |
|---|---|
| El ring se escribe como memoria normal, sin `writel` | `PROVEN` |
| El estado del `wptr` esta en un BO en GTT | `PROVEN` |
| El doorbell esta en un BO con `AMDGPU_PL_DOORBELL`, otro dominio | `PROVEN` |
| `set_wptr` son dos escrituras a dos dominios | `PROVEN` |
| Entre ellas no hay `mb()` explicito | `PROVEN` |
| Existe una rama con `WREG32`+`RREG32` de confirmacion | `PROVEN` — y no se usa en GFX8 |
| Que `use_doorbell` sea true en GFX8 (gfx y compute) | `PROVEN` (`gfx_v8_0.c:1862, 1973`) |
| Que la rama `WREG32`+`RREG32` este muerta en Polaris12 | `PROVEN_DERIVED` |
| El `mb()` de `ring_commit` esta antes de `set_wptr`, no entre sus dos escrituras | `PROVEN` |
| El `rptr` lo escribe el hardware; no hay `update_rptr` | `PROVEN` |
| `writel` a la apertura de doorbell actua como barrera de escritura | `HYPOTHESIS` — propiedad de la plataforma, no del codigo |
| Que el hardware ve el `wptr` antes de procesar el doorbell | `NOT_DETERMINED` |
| Que `writel` a este dominio implica vaciado de posted-writes en x86 | `NOT_DETERMINED` — depende del tipo de memoria |

Ultimas dos filas, que son las que importan. El driver **no tiene ningun mecanismo
propio** de orden entre (a) y (b). Depende de que `writel` a una apertura de dispositivo
sea barrier suficiente. Eso es verdad en x86 para el camino habitual —una escritura a
MMIO posted se vacia antes de que el dispositivo pueda observar una escritura previa de
memoria normal por el mismo camino— pero es una propiedad de la plataforma, no una
garantia del driver, y **no esta verificada para el dominio `AMDGPU_PL_DOORBELL` de esta
placa en particular**.

`NOT_DETERMINED` con el discriminante identificado: cambiar (a) por una escritura
`writel` equivalente, o insertar `wmb()` explicito, y ver si el comportamiento cambia. Es
un experimento de compilacion y runtime, fuera del alcance estatico de esta ronda.

## 5 · Clasificacion

| afirmacion | estado |
|---|---|
| Tres dominios de memoria para el estado de un ring | `PROVEN` |
| El ring y el wb comparten dominio (`GTT`) | `PROVEN` |
| El doorbell tiene dominio propio (`AMDGPU_PL_DOORBELL`) | `PROVEN` |
| `set_wptr` = escritura GTT + `writel` DOORBELL | `PROVEN` |
| `mb()` en `ring_commit` esta antes de `set_wptr` | `PROVEN` |
| `rptr` es push del hardware; `wptr` es push del CPU | `PROVEN` |
| Que el driver ordene (a) antes de (b) explicitamente | `REFUTED` — no existe tal codigo |
| Que `writel` a doorbell baste como barrera | `HYPOTHESIS` de plataforma |
| Que el hardware respete el orden en esta placa | `NOT_DETERMINED` |

## 6 · Confounders

- La afirmacion de que `writel` es barrier suficiente viene de la arquitectura x86 y del
  diseno de las aperturas de dispositivo, **no de amdgpu**. Un driver que [_escriba en
  otro orden, o que corra en ARM, tendria que tratarlo distinto. `025` §2 tiene la misma
  dependencia para `mb()` + `flush_hdp`.
- `AMDGPU_PL_DOORBELL` con `fpfn = 0, lpfn = 0` sugiere que la colocacion la resuelve la
  BIOS o el firmware, no el driver. El codigo no dice donde acaba esa pagina, asi que la
  **atribucion concreta de la pagina fisica es `NOT_DETERMINED`**. No afecta a la
  conclusion —da igual donde este, es un dominio distinto al GTT— pero si importa para
  cualquier razon sobre su tamano o alineacion.
- El `mb()` de `ring_commit` podria ser redundante en x86 y existir por portabilidad a
  architectures debiles. El driver no lo dice. `HYPOTHESIS`.

## 7 · UNLOCKS

- El driver propio tiene el **contrato de orden completo** del submit: escribir el IB en
  memoria normal, escribir el `wptr` en GTT, y tocar el doorbell con `writel`. Tres
  pasos, tres dominios, y el unico punto donde se toca el dispositivo es el ultimo.
- **`rptr` no necesita puerta** es la conclusion util: es push del hardware. Un driver
  propio no debe buscar un `update_rptr` que no existe, ni escribir en `rptr_cpu_addr`.
- La pregunta que queda abierta —*que garantiza el orden entre la escritura del `wptr`
  y el `writel` del doorbell*— es **la** pregunta de sincronizacion de esta serie, y
  tiene un discriminante concreto y pequeno: insertar `wmb()` explicito entre (a) y (b)
  y comparar. No requiere hardware nuevo, solo recompilar.
- `DESIGN_FREEDOM` con base medida: el driver propio puede **fusionar (a) y (b)** si
  escribe el `wptr` en la propia pagina de doorbells, eliminando la dependencia de la
  barrera de plataforma. Es una opcion que el driver de referencia no considera porque
  no le hace falta a el.

## 8 · Criterio de falsificacion

Se refutaria si: (a) `writel` a `AMDGPU_PL_DOORBELL` no fuera barrier suficiente y
hubiera fallos de visibilidad en la practica — eso seria un bug del driver de referencia
y un `CONTRADICTION` con el hecho de que el equipo funciona; (b) el `wptr` no se usara en
la practica y el hardware leyera otra cosa de la pagina — refutable leyendo el
`COMPUTE_DISPATCH` o el `GRBM`, no el codigo; (c) existiera un `wmb()` o equivalente
oculto en la macro `WDOORBELL32` o en `amdgpu_mm_wdoorbell` que yo no haya leido — el
cuerpo de las dos esta transcrito completo en §1.3 y §2, no hay mas; (d) el firmware
consultara el `wptr` en la pagina del writeback en vez de leerlo del doorbell, lo que
cambiaria la pregunta — `NOT_DETERMINED`, exige hardware.

## 9 · Evidencia

```
gfx_v8_0.c:        6006-6009 (get_rptr = lectura simple),
                   6162-6178 (set_wptr_gfx: doorbell O WREG32+RREG32 de confirmacion),
                   6231-6248 (set_wptr_compute),
                   1862 (compute_ring_init: use_doorbell = true),
                   1973 (gfx ring init: use_doorbell = true, solo excluye CHIP_TOPAZ)
amdgpu_ring.c:     206-210 (get_gpu_addr/get_cpu_addr: offset*4, &wb.wb[offset]),
                   361-372 (ring_obj en GTT), 375 (max_dw)
amdgpu_ring.h:     amdgpu_ring_write = asignacion normal a ring->ring[wptr++]
amdgpu_device.c:   1040-1046 (wb_obj en GTT, 32 KiB, 1024 slots de 256 bit)
amdgpu_doorbell_mgr.c: 59-70 (amdgpu_mm_wdoorbell = writel),
                   150-177 (kernel_doorbells en AMDGPU_GEM_DOMAIN_DOORBELL)
amdgpu_doorbell.h: 398 (WDOORBELL32 = amdgpu_mm_wdoorbell)
amdgpu_object.c:   148-154 (AMDGPU_PL_DOORBELL en la tabla de colocaciones),
                   1569 (DOMAIN_DOORBELL -> PL_DOORBELL)
amdgpu_ring.c:     172-186 (ring_commit: mb() antes de set_wptr)
barrido:           grep -rn "update_rptr" *.c -> 0 resultados
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

---

## ENMENDADO POR `037` — §3 cierra: el doorbell lo gobierna `CP_RB_DOORBELL_CONTROL`

`031` §3 dejo abierto que garantia une la escritura del `wptr` con el `writel` del doorbell, y §7
lo dejo como el `DESIGN_FREEDOM` de fusionarlas. Faltaba el paso intermedio: **que
registro hardware le dice al CP que apertura vigilar**. `037` lo midio.

```
gfx_v8_0.c:4200   CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET = ring->doorbell_index
                  CP_RB_DOORBELL_CONTROL.DOORBELL_EN      = 1
                  offset 0x003059
```

Y con eso queda **cerrado** lo que este documento dio por supuesto:

```
init:    CP_RB_DOORBELL_CONTROL.DOORBELL_OFFSET = doorbell_index
         -> el HW sabe que apertura vigilar

submit:  *wptr_cpu_addr = wptr                     GTT, pagina del writeback
         writel(doorbell[doorbell_index], wptr)    apertura de dispositivo
```

El doorbell **solo lleva el indice**. El valor del `wptr` solo existe en la pagina del
writeback. Por eso el HW tiene que verla antes de procesar el timbre — y por eso el
`mb()` de `ring_commit` tiene que estar antes de las dos escrituras, y no entre ellas.

### Correccion de una hipotesis mia de `037`

`037` afirmo que el puntero que gobierna la puerta es `CP_HQD_PQ_WPTR` (`0x3255`) y no
`CP_RB0_WPTR` (`0x3045`). **Falso.** Los sitios de escritura lo desmienten:

```
CP_HQD_PQ_WPTR   se escribe UNA vez, con el literal 0    (:4381)  -> init
CP_RB0_WPTR      :6031-6032  solo en la rama ELSE de set_wptr_gfx  -> MUERTA en GFX8
                 :6019       solo en la rama ELSE de get_wptr      -> MUERTA en GFX8
                 :4255       init
```

`CP_RB0_WPTR` sirve para **dos** cosas: el valor inicial al arrancar el ring, y el
mecanismo alternativo sin doorbell que `031` §2.0 demostro que no se usa en esta ASIC.
Las ramas `else` son exactamente la via del `WREG32`+`RREG32` de confirmacion que este
documento describio como codigo muerto. Ahora se ve que **el registro que esa rama
escribia es `CP_RB0_WPTR`**, lo que cierra el circulo.

### Lo que queda abierto, y es lo de §4

Sigue sin resolverse **por que es suficiente** que `writel` a la apertura actue como
barrera. `037` anadio que hay **tres** espacios de direccionamiento —`RREG32` directo,
`RREG32_SMC` con prefijo `ix`, y `AMDGCN_REG_OFFSET` por bloque— y el segundo es el de la
apertura del doorbell? No: el doorbell es `writel` sobre `adev->doorbell.cpu_addr`, que
viene de un BO en `AMDGPU_GEM_DOMAIN_DOORBELL` (`031` §1.3). Los tres espacios de `037` son
otra cosa y no se solapan con este.

`NOT_DETERMINED` §4 sin cambio, con su discriminante sin cambio: insertar `wmb()` entre
las dos escrituras y comparar. Requiere hardware.
