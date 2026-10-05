# 1411 — el «wait for the invalidate to complete» del flush de GFX8 espera con `mask = 0`: no espera

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
TARGET=CHIP_POLARIS12

AFECTADO=gfx_v8_0.c:6197-6221      gfx_v8_0_ring_emit_vm_flush
         cikd.h:294-302            semantica de WAIT_REG_MEM_FUNCTION
         gfx_v8_0.c:6053-6061      el flush de HDP, que SI usa el idioma completo
         gfx_v8_0.c:6186-6194      el fence, que espera en memoria de verdad
         gfx_v8_0.c:6932, 6966     la reserva de dwords del anillo

COMPLETA=1401 (la lectura de RESPONSE): las dos vías de invalidación de TLB de
         GFX8, y por qué ninguna de las dos espera de forma observable
ESTADO=PROVEN-ENCODING · el "por que funciona asi" es NOT_DETERMINED
```

## 0 · LO QUE ABRÍ Y LO QUE SALIÓ

Iba a cerrar la cadena causal de la base de tabla de páginas (§14) y, al medir el
tamaño en dwords del flush, encontré que `gfx_v8_0_ring_emit_vm_flush` **no es
solo un envoltorio**: emite un `WAIT_REG_MEM` con el comentario

```c
/* wait for the invalidate to complete */
```

Ese comentario dice una cosa. Lo que escriben los cinco dwords siguientes es
otra. Este hallazgo mide las dos.

## 1 · EL PAQUETE, LOS CINCO DWORDS, LEÍDOS EN ORDEN

`gfx_v8_0.c:6204-6213`, literal:

```c
        /* wait for the invalidate to complete */
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | /* wait */
                                 WAIT_REG_MEM_FUNCTION(0) |  /* always */
                                 WAIT_REG_MEM_ENGINE(0))); /* me */
        amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
        amdgpu_ring_write(ring, 0);
        amdgpu_ring_write(ring, 0); /* mask */
        amdgpu_ring_write(ring, 0x20); /* poll interval */
```

Y la semántica de los campos, de la fuente primaria del PM4 de esta generación,
`cikd.h:294-302` — **`cikd.h` es el header de GFX8**, y los campos están escritos
en el propio header:

```c
#define  WAIT_REG_MEM_FUNCTION(x)   ((x) << 0)
        /* 0 - always
         * 1 - <
         * 2 - <=
         * 3 - ==
         * 4 - !=
         * 5 - >=
         * 6 - >
         */
```

MEDIDO, entonces:

```
  OPERATION  = 0    wait (no write, no write-back)
  FUNCTION   = 0    always
  registro   = mmVM_INVALIDATE_REQUEST   (0x51e, segun 1401)
  ref        = 0
  mask       = 0
  poll       = 0x20
```

## 2 · EL ORDEN DE LOS DWORDS, FIJADO POR DOS USOS DEL MISMO FICHERO

Antes de interpretar `ref` y `mask` hay que saber **en qué orden** llegan. No lo
supongo: lo tomo de los otros dos `WAIT_REG_MEM` de GFX8, que están completos.

**(a) El fence, `gfx_v8_0.c:6186-6194` — espera en memoria, con máscara real:**

```c
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_MEM_SPACE(1) | /* memory */
                                 WAIT_REG_MEM_FUNCTION(3) | /* equal */
                                 WAIT_REG_MEM_ENGINE(usepfp)));
        amdgpu_ring_write(ring, addr & 0xfffffffc);          /* dir lo */
        amdgpu_ring_write(ring, upper_32_bits(addr) & 0xffffffff); /* dir hi */
        amdgpu_ring_write(ring, seq);                        /* ref   */
        amdgpu_ring_write(ring, 0xffffffff);                 /* mask  */
        amdgpu_ring_write(ring, 4); /* poll interval */
```

`FUNCTION(3) == equal`, `mask = 0xffffffff`, `ref = seq`. **Espera a que la
dirección de memoria contenga `seq`.**

**(b) El flush de HDP, `gfx_v8_0.c:6053-6061` — el idioma canónico:**

```c
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */
                                 WAIT_REG_MEM_FUNCTION(3) |  /* == */
                                 reg_mem_engine));
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_REQ);
        amdgpu_ring_write(ring, mmGPU_HDP_FLUSH_DONE);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, ref_and_mask);
        amdgpu_ring_write(ring, 0x20); /* poll interval */
```

**`ref == mask == ref_and_mask`.** Eso es el idioma de GCN para *esperar a que
todos los bits de la máscara estén puestos*: `HDP_FLUSH_DONE` tiene que valer lo
mismo que `HDP_FLUSH_REQ`.

> **Los dos casos ajenos fijan el orden: `dir_lo`, `dir_hi`, `ref`, `mask`, `poll`.
> Y fijan el idioma: la comparación es contra `ref`, enmascarada con `mask`.**

## 3 · LO QUE HACE EL PAQUETE DEL FLUSH DE VM, A PARTIR DE ESO

Con el orden y el idioma ya medidos por el propio árbol:

```
  funcion  = always        (0)
  ref      = 0
  mask     = 0

  -> la condicion evaluada es   (valor & 0)  ==  0
  -> eso es  0 == 0,  cierto siempre, para cualquier valor del registro
```

**El paquete se cumple en el instante en que la GPU lo ejecuta.** No es una espera:
es un `PACKET3` válido, bien codificado, y sin efecto de bloqueo.

MEDIDO también: `mmVM_INVALIDATE_REQUEST` es `0x51e` (`1401`), y en el caso (b)
el driver **sí** sabe escribir un `WAIT_REG_MEM` que espera de verdad, con la
misma forma de paquete, en el mismo fichero, a treinta líneas de distancia.

> **El comentario y la codificación dicen cosas distintas, y ambas están
> medidas.** El comentario afirma una espera de completitud; los cinco dwords
> codifican un `mask` que hace la condición trivialmente cierta.

Y hay un detalle que refuerza la lectura y que no es mío: **`WAIT_REG_MEM_OPERATION(0)`
es `wait` a secas**, mientras que en HDP es `1`, *write, wait, write*. O sea que
en el flush de VM el driver eligió explícitamente **no** reescribir el registro
—que es lo correcto, porque es auto-borrable— y eligió explícitamente `always`
en vez de `==`. **Las dos elecciones parecen deliberadas. Una de ellas
probablemente no lo es.**

## 4 · LA RESERVA DE DWORDS DEL ANILLO LO DELATA

`gfx_v8_0.c:6932` (ring de compute) y `gfx_v8_0.c:6966` (KIQ):

```c
        VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7 + /* gfx_v8_0_ring_emit_vm_flush */
```

```c
        17 + /* gfx_v8_0_ring_emit_vm_flush */
```

MEDIDO, contando con `gfx_v8_0_ring_emit_wreg` = **5 dwords** por escritura
(`gfx_v8_0.c:6369-6373`: header `PACKET3` en 6369, y `cmd`, `reg`, `0`, `val` en 6370-6373):

```
  gfx_v8_0_ring_emit_vm_flush emite
     amdgpu_gmc_emit_flush_gpu_tlb
        2 x emit_wreg  x 5 dwords                            = 10
     PACKET3_WAIT_REG_MEM
        header + cmd + reg + ref + mask + poll               =  6
     PACKET3_PFP_SYNC_ME, solo en el ring de GFX             =  2
                                                        total
        ring KIQ      10 + 6 + 0                            = 16
        ring de GFX   10 + 6 + 2                            = 18

  reserva
        ring KIQ                    17                       -> 1 de sobra
        ring de compute  3*5 + 7  = 22                       -> 4 de sobra

  ### ⚠ CORRECCION — ver 1441.  Aqui hay dos errores, y uno de ellos es mio
>
> **Error 1, el numero.** El exceso del anillo de compute **no es 4, es 6**, y el
> del anillo de gfx **tampoco**: hay **tres** formulas, no dos, porque el anillo
> de gfx usa `+ 9` y el de compute `+ 7`. Recuento correcto, con el `PFP_SYNC_ME`
> que solo emite el anillo de gfx:
>
> ```
>   anillo GFX      reserva 3*5+9 = 24   emision 18   exceso 6
>   anillo COMPUTE  reserva 3*5+7 = 22   emision 16   exceso 6
>   anillo KIQ      reserva 17           emision 16   exceso 1
> ```
>
> Aqui puse 18 como emision del anillo de compute, y el compute **no** emite el
> `PFP_SYNC_ME`. De ahi el 6 en vez del 4.
>
> **Error 2, la atribucion.** Este §4 nombro «ring de compute» sin decir que hay
> tres, y el artefacto (`1441`) es un anillo **de gfx**, cuya formula es la de
> `+ 9`. **La reserva que aplica a la evidencia que tengo es la de gfx, no la de
> compute.** Correcto en `1441-el-budget-nombra-tres-vallas-y-el-ib-tiene-dos.md`.
>
> Lo que **no** cambia: el `mask = 0`, que es el hallazgo, y que el KIQ estaba
> bien (17 contra 16, exceso 1).

Y `vi.h:27`:

```c
#define VI_FLUSH_GPU_TLB_NUM_WREG   3
```

**El 3 no corresponde a nada que emita.** MEDIDO: `gmc_v8_0_emit_flush_gpu_tlb`
emite 2 escrituras, y el gemelo de GCN6, `gmc_v6_0_emit_flush_gpu_tlb`, emite
**las mismas dos** — con el mismo `if (vmid < 8)` partido y todo. **La constante
`VI_FLUSH_GPU_TLB_NUM_WREG = 3` no corresponde ni a GFX8 ni a GCN6.**

> Sobre-reservar dwords en `emit_frame_size` **no es un fallo**: es una cota, y una
> cota holgada es segura. Lo que sí es un dato es que **la fórmula que supuestamente
> dimensiona el flush de VM cuenta una emisión que no existe en ninguna generación
> de este árbol**, y que el `+ 7` está dimensionado para el `WAIT_REG_MEM` más lo
> que falta, no para un flush sin esperar.

## 5 · LO QUE CIERRA DE `1401`, Y LO QUE NO

`1401` había medido que `gmc_v8_0_flush_gpu_tlb_pasid` (vía MMIO) acaba con un
`RREG32(mmVM_INVALIDATE_RESPONSE)` cuyo resultado se descarta, y había dejado su
propósito como `NOT_DETERMINED`.

Con esto, las dos vías de invalidación de TLB de GFX8 quedan así:

| | vía | cómo sincroniza | espera de verdad |
|---|---|---|---|
| MMIO, por VMID | `gmc_v8_0_flush_gpu_tlb` | ninguna | **no** |
| MMIO, por PASID | `gmc_v8_0_flush_gpu_tlb_pasid` | lee `RESPONSE`, sin usar el valor | **no** |
| PM4, por VMID | `gfx_v8_0_ring_emit_vm_flush` | `WAIT_REG_MEM` con `mask = 0` | **no** |

**Ninguna de las tres espera a que la invalidación termine**, y eso es `PROVEN`
sobre el código por la vía del `mask`, no por opinión.

Lo que **queda abierto**, y es `NOT_DETERMINED` con motivo:

- **Si el hardware de GFX8 necesita esa espera.** Que el driver no la haga y la
  GPU funcione es un hecho empírico, no una prueba: el paquete está ahí, lo que
  significa que **alguien muchas veces creyó que hacía falta**. La hipótesis más
  fuerte es que en GFX8 la invalidación se ordena antes de la siguiente operación
  y el `fence` normal del trabajo ya cubre el caso, con lo que el paquete sería
  **vestigial**. Eso es `HIPOTESIS`, y laowo separo del `PROVEN` de arriba.

- **Qué hace la lectura de `RESPONSE` en la vía MMIO.** Sigo sin saberlo. Lo que
  este hallazgo **sí** hace es quitarle una explicación que parecía buena: no es
  «esperar de completion» disfrazado, porque la vía PM4 que **sí lleva un
  comentario de espera** es la que no espera. Si el autor hubiera querido
  esperar, la vía PM4 lo habría hecho con `mask` real, y la tiene a treinta
  líneas.

## 6 · LO QUE LE PASA A UN DRIVER PROPIO

```
  SI EMPIEZAS POR COPIAR gmx_v8_0_ring_emit_vm_flush
     copias un PAQUETE que no hace nada               -> 16-18 dwords de ring
                                                       ocupados por un no-op
     y copias la RESERVA (3*5+7 = 22)                 -> coherente con arriba,
                                                       pero por el motivo equivocado

  LO QUE HAY QUE DECIDIR, y es una decision real
     ¿GFX8 necesita esperar a DOMAIN_INVALIDATED_n?   -> 1 lectura MMIO
        si RESPONSE es distinto de REQUEST tras un ciclo   -> si, y hay que
                                                               esperar de verdad
        si REQUEST es auto-borrable                        -> esperar a REQUEST==0,
                                                               que es lo que el
                                                               paquete INTENTABA
                                                               hacer con mask=0
```

**Y esa es la conexión con `1401`:** si `mmVM_INVALIDATE_REQUEST` es
auto-borrable —y el `WAIT_REG_MEM_OPERATION(0)`, sin reescritura, sugiere que el
autor lo creía—, entonces la espera correcta es `mask = 0xFFFF, ref = 0` con
`FUNCTION(3) == equal`, y **el paquete actual tiene `mask` y `ref` a cero cuando
querría tener `mask` a `0xFFFF`.**

Es **una línea de código** de diferencia. Y es exactamente el tipo de línea que un
driver propio tiene que decidir, no heredar.

## 7 · LO QUE NO SE AFIRMA

- **No se dice que GFX8 tenga un fallo de TLB.** El driver es de producción y la
  GPU funciona. Lo que se afirma es que **la sincronización explícita de la
  invalidación no está en el código**, y que la que parece estar, no lo está.
- **No se dice que `mask = 0` haga trampas en el hardware.** La lectura de
  «condición trivialmente cierta» viene del idioma del propio driver (caso b:
  `ref == mask`), no de la guía de hardware. Es `PROVEN` sobre el uso, y
  `NOT_PUBLISHED` el hardware del opcode.
- **No se toca ningún fichero del corpus.** Todo es lectura.

```
ESTADO
  gfx_v8_0_ring_emit_vm_flush, GFX8
     orden de los 5 dwords        dir_lo, dir_hi, ref, mask, poll   PROVEN
     idioma de la comparacion    (valor & mask) == ref              PROVEN
        fijado por los 2 otros WAIT_REG_MEM del mismo fichero
     OPERATION 0    wait, sin reescribir                            PROVEN
     FUNCTION  0    always        (cikd.h:294-302)                  PROVEN
     ref       = 0
     mask      = 0     ->  (valor & 0) == 0, cierto siempre         PROVEN
     -> EL PAQUETE NO ESPERA                                      PROVEN
     el comentario dice "wait for the invalidate to complete"        PROVEN
     el comentario y el codigo discrepan                           PROVEN

  tamano real del flush   (CORREGIDO en 1441, ver la nota de mas arriba)
     ring KIQ       16 dwords     reserva 17     -> 1 de sobra     PROVEN
     ring COMPUTE   16 dwords     reserva 22     -> 6 de sobra     PROVEN
     ring GFX       18 dwords     reserva 24     -> 6 de sobra     PROVEN
     emit_wreg      5 dwords      (gfx_v8_0.c:6369-6373)           PROVEN
     VI_FLUSH_GPU_TLB_NUM_WREG = 3, emite 2, y GCN6 tambien 2     PROVEN

  las 3 vias de invalidacion de TLB de GFX8 esperan?                 NO    PROVEN
  GFX8 necesita esa espera?            NOT_DETERMINED -> 1 lectura MMIO
  para que sirve el RREG32 de RESPONSE NOT_DETERMINED, y este hallazgo le
                                       QUITA la explicacion de "espera"
  si REQUEST es auto-borrable         HIPOTESIS, apoyada en OPERATION(0)

  completa 1401 con la parte sincronizacion
  corpus  solo lectura
  GPU     INTACTA
  sudo    NO usado
```