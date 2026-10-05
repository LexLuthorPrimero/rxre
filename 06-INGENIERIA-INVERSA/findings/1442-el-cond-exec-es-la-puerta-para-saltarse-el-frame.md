# 1442 — el `COND_EXEC` es la puerta que permite saltarse el frame entero, y su campo de cuenta en el IB vale **exactamente** lo que el patcher del driver calcula

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ARTEFACTO=revkit/capturas/amdgpu_ring_gfx.txt   dwords 3..7
CORPUS=rx550-upstream-7.2.8 (solo lectura)

AFECTADO=gfx_v8_0.c:6319-6334      gfx_v8_0_ring_emit_init_cond_exec
         amdgpu_ring.h:544-554     amdgpu_ring_patch_cond_exec
         amdgpu_ring.c:291-321     cond_exe_offs, writeback buffer
         amdgpu_vm.c:833-834       una emision del COND_EXEC
         amdgpu_ib.c:247, 319      la otra, y el unico parcheo

COMPLETA=1412 §1 y 1441: el ultimo tipo de paquete del artefacto queda decodificado
ESTADO=OBSERVADO con confirmacion aritmetica exacta
```

## 0 · EL ÚLTIMO PAQUETE SIN DECODIFICAR

Del artefacto quedan ocho tipos. `1412` identificó el `WAIT_REG_MEM` de HDP,
`1420` el `INDIRECT_BUFFER`, `1440` las cuatro `EVENT_WRITE_EOP`, `1441` el
relleno `.nop` y el `SWITCH_BUFFER`. Quedaban dos: `0x22 COND_EXEC` y el `0x8b`
que ya casó con `gfx_v8_ring_emit_sb` en dos dwords exactos.

El `COND_EXEC` es el que importa, porque **es el mecanismo que permite saltarse
el frame entero**, y eso es una decisión de rendimiento, no de corrección.

## 1 · LA FUENTE, LEÍDA ENTERA, Y EL PATCHER

`gfx_v8_0_ring_emit_init_cond_exec` (`gfx_v8_0.c:6319-6334`), completo:

```c
static unsigned gfx_v8_0_ring_emit_init_cond_exec(struct amdgpu_ring *ring,
                                                  uint64_t addr)
{
        unsigned ret;

        amdgpu_ring_write(ring, PACKET3(PACKET3_COND_EXEC, 3));
        amdgpu_ring_write(ring, lower_32_bits(addr));
        amdgpu_ring_write(ring, upper_32_bits(addr));
        /* discard following DWs if *cond_exec_gpu_addr==0 */
        amdgpu_ring_write(ring, 0);
        ret = ring->wptr & ring->buf_mask;
        /* patch dummy value later */
        amdgpu_ring_write(ring, 0);
        return ret;
}
```

Y `amdgpu_ring_patch_cond_exec` (`amdgpu_ring.h:544-554`):

```c
        WARN_ON(offset > ring->buf_mask);
        WARN_ON(ring->ring[offset] != 0);

        ring->ring[offset] = amdgpu_ring_get_dw_distance(ring, offset, ring->wptr - 1);
```

**El `ret` es la dirección del dummy, no un valor de cuenta.** `amdgpu_ring_write`
escribe en `ring->wptr` e incrementa, así que:

```
  wptr = W al entrar
  W    header
  W+1  addr_lo
  W+2  addr_hi
  W+3  0                       <- la condicion, literal
  ret = (W+4) & buf_mask       <- el puntero al dummy que se acaba de escribir
  W+4  0                       <- el dummy, y AQUI parchea el patcher
  wptr = W+5
```

## 2 · EL ARTEFACTO, Y LA COMPROBACIÓN ARITMÉTICA

```
  dword   3  0xc0032200   PACKET3_COND_EXEC, count 3
  dword   4  0x00001080   lower_32_bits(addr)
  dword   5  0x000000ff   upper_32_bits(addr)
  dword   6  0x00000000   condicion, literal 0 del driver
  dword   7  0x0000002b   el dummy YA PARCHEADO
```

**El patcher dice que el valor es `get_dw_distance(7, wptr - 1)`.**

Y `wptr` al parchear es el final del frame. En este bloque, el último dword de
trabajo real es el **50** (último operando de la valla B):

```
  distancia  50 - 7  =  43  =  0x2b
```

**Coincide exactamente.** Y no es una aproximación: es la aritmética del patcher,
con el `offset` y el `wptr` que salen del propio bloque.

> **Esto es el tipo de confirmación que `§46 ORACLE ENGINE` busca y que este
> proyecto no tenía:** no un oráculo externo, sino **una predicción numérica del
> driver que el artefacto cumple al dword**. Si el valor fuera 42 o 44, el patcher
> estaría mal. Es 43.

**Y de ahí sale el span, que es lo que el mecanismo controla:**

```
  el COND_EXEC governs dwords 8 .. 50
     HDP flush, context control, IB, WRITE_DATA, las DOS vallas
  y NO gobierna
     dword 51  SWITCH_BUFFER
     dwords 52..255  relleno .nop
```

## 3 · DÓNDE VIVE LA VARIABLE DE CONDICIÓN, Y POR QUÉ SU DIRECCIÓN ES ALTA

`amdgpu_ring.c:291`, al reservar el anillo:

```c
        r = amdgpu_device_wb_get(adev, &ring->cond_exe_offs);
        if (r) {
                dev_err(adev->dev, "(%d) ring cond_exec_polling wb alloc failed\n", r);
```

**Es un writeback buffer, o sea memoria de sistema, no VRAM.** Y la dirección
del artefacto es `0x000000ff_00001080`.

**Eso no cabe en la VRAM de esta placa.** MEDIDO: la tarjeta tiene ~2 GiB, y
`gmc_v8_0.c:1165-1173` deja `vram_base_offset = 0` en la rama discreta. Con una
dirección de 68 GB, **la variable de condición está en el espacio GTT**, mapped
desde RAM del sistema, que es donde mete `amdgpu_device_wb_get`.

> **Y aquí está el detalle que un driver propio necesita:** la condición de la
> que depende **omitir medio frame de trabajo** está en **RAM del sistema**,
> escribible por la CPU sin tocar la cola de la GPU. Eso es lo que hace posible el
> skip: el CPU decide en el momento del submit y solo tiene que cambiar un
> dword. **Si la variable estuviera en VRAM, el skip exigiera un writeback y el
> mecanismo no valdría la pena.**

## 4 · EL `COND_EXEC` SE EMITE **DOS** VECES POR FRAME, Y SOLO SE PARCHEA UNO

MEDIDO sobre el árbol:

```
  amdgpu_vm.c:833-834     if (ring->funcs->init_cond_exec)
                             patch = amdgpu_ring_init_cond_exec(ring,
                                          ring->cond_exe_gpu_addr);

  amdgpu_ib.c:247-248     if (ring->funcs->init_cond_exec)
                             cond_exec = amdgpu_ring_init_cond_exec(ring,
                                          ring->cond_exe_gpu_addr);

  amdgpu_ib.c:319         amdgpu_ring_patch_cond_exec(ring, cond_exec);
```

> ### ⚠ CORRECCION — ver 1443.  Aqui afirmo que solo se parchea uno.  Falso
>
> ```
>   amdgpu_vm.c:833   patch       = init_cond_exec(...)
>   amdgpu_vm.c:896   patch_cond_exec(ring, patch)         <- SI se parchea
>   amdgpu_ib.c:247   cond_exec   = init_cond_exec(...)
>   amdgpu_ib.c:319   patch_cond_exec(ring, cond_exec)     <- y este tambien
> ```
>
> **Dos emisiones, dos parcheos.** Escribi «no se parchea» y anoti «hay que
> buscar quien lo usa»: exactamente el `NOT_DETERMINED` sin abrir el fichero que
> `1430` §7 prohibe. **Habia leido la funcion entera, habia visto `unsigned int
> patch = 0;` en su linea 789, y no subi a mirar el final.**
>
> La conclusion de `1442` no cambia. **La explicacion si: `1443` muestra que este
> camino es el de `amdgpu_ib_schedule`, y por eso hay un solo `COND_EXEC` y un
> solo switch buffer en el artefacto.**

Y el artefacto tiene **un solo `COND_EXEC` por bloque, en el dword 3**, seguido
inmediatamente por el flush de HDP en el 8. Eso casa con el orden de
`amdgpu_ib.c`: `init_cond_exec` y justo después `amdgpu_device_flush_hdp`.

> **Lo que se puede afirmar:** en esta captura el `COND_EXEC` presente es el de
> `amdgpu_ib.c:247`, por posición respecto al HDP flush. **Lo que no:** por qué
> no está el de `amdgpu_vm.c:833`. Y esa es una pregunta de runtime —si el camino
> de vm_entity se ejecutó en este anillo— no de lectura de código.

## 5 · LO QUE LE PASA A UN DRIVER PROPIO

```
  EL MECANISMO, en tres piezas y con su coste
     1. un writeback buffer por anillo, en RAM del sistema   (amdgpu_ring.c:291)
     2. un COND_EXEC de 5 dwords al principio del frame      (gfx_v8_0.c:6324)
     3. un parche en el submit que pone la cuenta real       (amdgpu_ring.h:552)
     en total: 5 dwords fijos + 1 escritura de CPU por frame

  LA CONDICION, medida
     "discard following DWs if *cond_exec_gpu_addr == 0"
     -> si la variable es 0, la GPU se salta lo que viene
     y el codigo la pone a CONTINUE siempre (amdgpu_ring.c:322)

  LO QUE UN DRIVER PROPIO NO PUEDE HACER
     omitir el writeback buffer        -> pierde el skip entero
     omitir el parche del submit       -> la cuenta queda en 0 y no salta nunca
     parchar antes de terminar el frame -> cuenta incorrecta, salta de mas o de menos
     la ultima es la peligrosa: saltarse de mas es corrupcion de contexto,
     y no hay assert en el camino
```

**Y el número que da la medida del mecanismo:** el `COND_EXEC` governs **43 de 256
dwords** del bloque, o sea el **17 %** del frame. Ese es el techo del skip.

> **Y ese techo es un dato de rendimiento, no de corrección.** Un frame de 43
> dwords saltado es un frame cuyo flush de TLB, cambio de contexto, IB y vallas
> no se emiten **porque la GPU decide que no hacen falta**. `1441` mostró que en
> esta captura ese trabajo **sí** se emitió, es decir **el skip no se activó** —
> el contador de secuencia estaba en 0x9bae y avanzó en los 8 bloques, lo que
> significa que **los frames se ejecutaron todos, uno por bloque**.

Eso es una medición del artefacto, no una hipótesis: **8 vallas, 8 COND_EXEC, 8
workloads, 8 ejecuciones.** La carga no se benefició del skip.

## 6 · LO QUE NO SE AFIRMA

- **No se dice que el skip esté roto.** Al contrario: el parche está escrito, y
  en esta carga no se activó porque el trabajo se hacía. Que se pueda armar es
  `PROVEN` por el código; que se haya armado alguna vez en esta GPU es
  `NOT_OBSERVED`.
- **No se dice por qué el `COND_EXEC` de `amdgpu_vm.c` no está.** `NOT_DETERMINED`,
  y es runtime.
- **No se nombra la dirección `0x000000ff_00001080` más allá de «está en el
  espacio GTT».** Que el prefijo `0x000000ff` sea el inicio de la ventana GTT de
  esta ASIC es `NOT_PUBLISHED` en este corpus.
- **No se toca el corpus ni el artefacto.**

```
ESTADO
  COND_EXEC, decodificado
     5 dwords: header, addr_lo, addr_hi, condicion(0), cuenta(parcheada)
     en el artefacto, en los 8 bloques, en el dword 3           OBSERVADO
     la cuenta vale 0x2b = 43                                    OBSERVADO
     y 50 - 7 = 43, con el 50 siendo el fin del trabajo real
     -> la aritmetica del patcher se cumple AL DWORD             PROVEN

  la condicion
     "discard following DWs if *cond_exec_gpu_addr == 0"
     vive en un writeback buffer en RAM del sistema, no en VRAM   PROVEN
     el codigo la pone a CONTINUE siempre
     el skip gobierna 43 de 256 dwords = 17 % del frame          PROVEN

  emisiones   (CORREGIDO en 1443: dos parcheos, no uno)
     dos por frame: amdgpu_vm.c:833 y amdgpu_ib.c:247
     parcheados: amdgpu_vm.c:896 y amdgpu_ib.c:319
     el del artefacto es el de amdgpu_ib.c, por posicion          PROVEN
     por que falta el otro                                      NOT_DETERMINED

  en ESTA carga el skip no se activo
     8 COND_EXEC, 8 pares de vallas, 8 frames                   OBSERVADO

  SWITCH_BUFFER
     2 dwords, casa con gfx_v8_ring_emit_sb                     OBSERVADO

  ultimo tipo de paquete del artefacto sin decodificar:  ninguno

  GPU     INTACTA
  sudo    NO usado
  corpus  solo lectura
  artefacto  solo lectura
```