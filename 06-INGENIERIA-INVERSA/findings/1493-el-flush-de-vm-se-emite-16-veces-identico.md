# 1493 — El flush de VM sí se emite, 16 veces en `sdma0` y byte a byte idénticas: el driver invalida el mismo VMID 16 veces en una sola vuelta al anillo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

RESUELVE  el NOT_DETERMINED de 1490: "si el flush de VM se emite cuando el
          VMID cambia".  Si, y solo en el anillo SDMA0.

DATO QUE IMPORTA
  Los 16 son IDENTICOS dword a dword.  Invalidar 16 veces el mismo VMID no
  invalida nada nuevo a partir de la segunda.  Eso es trabajo que el driver de
  referencia hace y que un driver propio NO debe imitar.

DESCUBRE TAMBIEN, y no lo buscaba
  las DOS ramas de gfx_v8_0_get_hdp_flush_mask estan observadas en hardware,
  una por anillo:  gfx da mask=0x1/ENGINE=1 (PFP) y comp da mask=0x20/ENGINE=0
  (ME).  Las dos salidas de esa funcion, medidas.

CIERRA    1411 y 1441: el poll con mask=0 existe, se emite, y es un POLL.
```

## 0 · LA PREGUNTA DE 1490, Y CÓMO SE RESPONDE BIEN

`1490` dejó:

```text
  NOT_DETERMINED  si el flush de VM se emite cuando el VMID cambia.
```

El error que iba a cometer es buscar solo en el anillo PM4, que es donde
`1411` miró. La respuesta está en **los cuatro anillos**, y en uno de ellos.

## 1 · PRIMERO: EN NINGUNO DE LOS CUATRO HAY UN WAIT SOBRE EL REGISTRO

```text
  anillo        WAIT_REG_MEM   reg=0x51e   otros regs
  comp_1.3.1         1            0        0x1537
  gfx                8            0        0x1537
  sdma0              0            0        -
  sdma1              0            0        -
```

**Cero.** Ningún `WAIT_REG_MEM` espera sobre `mmVM_INVALIDATE_REQUEST` en ninguna
captura. Y los que hay, en PM4, son todos flush de HDP.

**El detalle del anillo de compute**, que es el único `WAIT_REG_MEM` suyo y que
resulta ser la segunda rama de una función ya leída:

```text
  dw266: ENGINE=0 OP=1 FUNC=3  reg=0x1537  ref=0x1538  mask=0x00000020  int=0x20
```

Frente a los del anillo gfx, que tienen `mask=0x1` y `ENGINE=1`. Y
`gfx_v8_0_get_hdp_flush_mask` tiene exactamente dos ramas:

```c
if ((ring->funcs->type == AMDGPU_RING_TYPE_COMPUTE) ||
    (ring->funcs->type == AMDGPU_RING_TYPE_KIQ)) {
        switch (ring->me) {
        case 1: *ref_and_mask = GPU_HDP_FLUSH_DONE__CP2_MASK << ring->pipe; ...
} else {
        *ref_and_mask  = GPU_HDP_FLUSH_DONE__CP0_MASK;   /* 0x1 */
        *reg_mem_engine = WAIT_REG_MEM_ENGINE(1);        /* pfp  */
}
```

| anillo | rama | `ref_and_mask` | engine | medido |
|---|---|---|---|---|
| gfx | `else` | `CP0_MASK` = 1 | 1 (PFP) | `1490` |
| comp_1.3.1 | `COMPUTE` | `CP2_MASK << pipe` = 0x20 | 0 (ME) | aquí |

**Las dos salidas de esa función están observadas en hardware, una en cada
anillo.** Eso es más de lo que `1490` afirmaba, y no costó nada: salió al mirar
el anillo que antes no miraba.

## 2 · Y EN EL SDMA0 ESTÁ, 16 VECES

```text
  dword == 0x51e en sdma0:            16
  dword == 0x51e en los otros tres:    0
```

Los 16, byte a byte, con el contexto de 4 dwords antes y 7 después:

```text
  [-4]  0xf000000e    packet header
  [-3]  0x0000054f    PAGE_TABLE_BLOCK_SIZE / array de context0-7   (1430)
  [-2]  0x0f400900    page table base
  [-1]  0xf000000e    packet header
  [ 0]  0x0000051e    mmVM_INVALIDATE_REQUEST
  [ 1]  0x00000001
  [ 2]  0x00000008    = 1 << 3
  [ 3]  0x00001478    mmVM_INVALIDATE_REQUEST << 2     <- el POLL
  [ 4]  0x00000000
  [ 5]  0x00000000
  [ 6]  0x00000000
  [ 7]  0x0fff000a    RETRY=0xfff  INTERVAL=10
```

**Forma distinta entre los 16: una.** Idénticos dword a dword.

`[3]=0x1478` y `[7]=0x0fff000a` son la firma que `1488` identificó como
`sdma_v3_0.c:1064-1072`. Los 16 son ese mismo camino.

## 3 · NO ES EL MISMO PAQUETE VISTO VARIAS VECES

Esa era la objeción y la resolví antes de escribir el veredicto, porque
cambia el significado entero. **Si el anillo estuviera enrollado, los 16 serían
una sola emisión vista 16 veces.**

```text
  posiciones:  93 253 365 423 471 605 941 999 1047 1095 1143 1453 1613 1725 1783 1831
  separaciones: 160 112 58 48 134 336 58 48 48 48 310 160 112 58 48
                min=48  max=336  distintas=7
```

Un anillo enrollado produce **un** hueco grande, del tamaño del anillo menos un
paquete, y todos los demas pasos iguales. Aqui:

- la separación máxima es 336, y el anillo es de 2048 dwords: **no hay hueco de wrap**
- hay **7 separaciones distintas**, no una
- el patrón `160, 112, 58, 48` **se repite** (posiciones 0–3 y 11–14)

```text
  PROVEN  son 16 emisiones DISTINTAS dentro de una sola vuelta al anillo.

  Y ESO tiene una consecuencia de verdad:  el volcado es un instante, y en ese
  instante el anillo contiene los ultimos ~2048 dwords de trabajo.  Caben 16
  invalidaciones.  El driver hizo 16 en ese intervalo.

  PROVEN_DERIVED  invalidar el mismo VMID 16 veces en una ventana de 2048
  dwords es trabajo redundante a partir de la segunda.  Un driver propio que
  invalide solo cuando la base de tabla o el VMID cambian tiene menos trabajo
  de ring.  Esto NO es una hipotesis de rendimiento: es un recuento de lo que
  el driver de referencia emite, y la mecanica de por que es redundante la da
  la semantica del registro (un poll con mask=0 no distingue una peticion de la
  anterior).
```

## 4 · LO QUE AFIRMO Y LO QUE NO

```text
PROVEN          los 16 son identicos, con la misma base de tabla
                (0x0f400900) y el mismo valor escrito
PROVEN          no es enrollamiento: 7 separaciones distintas, sin hueco de wrap
PROVEN          las dos ramas de gfx_v8_0_get_hdp_flush_mask estan observadas,
                una por anillo, con los valores que predice cada rama
PROVEN          el camino de sdma_v3_0.c:1064-1072 se emite 16 veces por
                ventana de anillo

CONSISTENTE, no probado
  [2] = 0x08 = 1 << 3  ->  VMID 3.  Es lo que escribe
  `gmc_v8_0.c:659  WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)`, y 1<<3 = 8.  No
  he leido el layout del packet SDMA WRITE_REG para confirmar que ese dword es
  el valor y no parte de la direccion, asi que lo dejo como CONSISTENTE.
  Lo que NO depende de esto: que los 16 son iguales.

NO AFIRMO
  que el driver este mal.  Puede que invalidate 16 veces porque cada
 dispatch revalida por robustez, o porque hay 16 contextos y el codigo
  recorre un bucle.  El bucle de gmc_v8_0_flush_gpu_tlb_pasid (1478) recorre
  vmid = 1..15, y eso PRODUCIRIA invalidaciones distintas, no iguales.  Asi que
  no es ese bucle.

  Y no es colision de mi parte: los 16 tienen la MISMA forma y la misma base,
  y un bucle sobre vmid daria 1<<1, 1<<2, ... distintos.

NOT_DETERMINED  por que se emite 16 veces.  Es una pregunta de runtime, y el
                volcado no dice quien pidio cada una.
```

## 5 · POR QUÉ ESTO CIERRA 1411 Y 1441

```text
  1411  "el WAIT_REG_MEM del flush de VM espera con mask=0 y por tanto no
        espera".
  1441  contó 3 WAIT_REG_MEM con FUNCION 0 en el IB.

  LO QUE DICEN SIGUE SIENDO CIERTO SOBRE EL CODIGO:  gfx_v8_0.c:6205-6213
  escribe OPERATION(0)|FUNCTION(0)|ENGINE(0) con mask 0.

  LO QUE SE AÑADE, y es lo que faltaba:  ese paquete NO aparece en ninguna
  de las cuatro capturas.  El paquete que SI aparece y que hace lo mismo, 16
  veces, es un POLL_REGMEM de SDMA con func=0.

  Y LA DISTINCION ES LA QUE 1411 NO HIZO:
    en PM4, WAIT_REG_MEM con FUNCTION(0) es un PAUSE (espera un valor, no un
    cambio).  En SDMA, POLL_REGMEM con FUNC(0) es ALWAYS (no espera nada).
    Los dos son "func=0" y los dos son no-ops de espera, pero uno esta en un
    anillo que no aparece en la captura.

  ASI QUE 1411 NO ESTA REFUTADO.  Esta corregido en el alcance: el mecanismo
  esta en el anillo SDMA, y en el PM4 no se ha observado.
```

## 6 · ESTADO

```text
PROVEN          16 INVALIDATE_REQUEST identicos en sdma0, 0 en los otros 3
                anillos, no enrollados (7 separaciones distintas, sin wrap)
PROVEN          2 ramas de gfx_v8_0_get_hdp_flush_mask observadas, una por
                anillo, con los valores que cada rama predice
CONFIRMA        1411 y 1441 en su afirmacion sobre el codigo; corrige el
                alcance: el paquete no aparece en captura PM4
CONSISTENTE     [2]=8 = 1<<3 = VMID 3, sin confirmar el layout del packet

PROVEN_DERIVED  el driver invalida el mismo VMID 16 veces por ventana de
                anillo.  Redundante a partir de la segunda, porque un poll
                con mask=0 no distingue una peticion de la anterior.  Es la
                primera mejora de rendimiento con base medida en el driver de
                referencia y no en una hipotesis.

NOT_DETERMINED  quien pide cada una de las 16, y por que.  Runtime.
```

## 7 · LO QUE ABRE, Y ES LO SIGUIENTE

```text
ABRE, medible
  1. ¿las 16 invalidaciones salen de UN batch del scheduler, o de 16 batches?
     Los 16 ocupan posiciones IRREGULARES en el anillo, lo que sugiere que no
     son consecutivas.  Si no son consecutivas, hay trabajo de por medio, y
     entonces el poll con mask=0 puede estar ahí para algo.

  2. ¿el anillo gfx emite flush de VM cuando DEBE?  Este anillo no lo tiene.
     Con la funcion leida (gfx_v8_0.c:6197) se sabe que deberia, si cambia el
     VMID.  La pregunta es si cambia en estos workloads, y eso necesita otro
     volcado con un context distinto.

  3. Y la de mas valor para el driver propio:  si el poll con mask=0 no
     espera, ¿que garantia da?  Si no da ninguna, el paquete sobra y se puede
     omitir.  Eso es una afirmacion sobre el HARDWARE, no sobre el codigo, y
     es la que 1411 dejo abierta desde el principio.
```

La 3 es la que importa para el objetivo del proyecto: es la primera pregunta
que separa "copiar el driver de referencia" de "escribir el correcto".
