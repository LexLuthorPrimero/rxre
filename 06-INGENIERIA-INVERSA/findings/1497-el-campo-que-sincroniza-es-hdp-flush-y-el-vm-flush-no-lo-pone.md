# 1497 — Los tres `POLL_REGMEM` del anillo SDMA de esta ASIC: dos esperan de verdad, y el del flush de VM es el único con `func=0` **y** `mask=0`. El campo que sincroniza es `HDP_FLUSH`, y ese no lo pone

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA        la mitad estatica de la pregunta de 1495 §7.3: "si el poll con
              mask=0 no espera, ¿que garantia da?"  La garantia no la da func,
              la da HDP_FLUSH.  El vm_flush no lo pone.

DESCUBRE      HDP_FLUSH(1) es el campo que engancha la sincronizacion del HDP,
              y aparece en 6 sitios del driver, ninguno de ellos el vm_flush.
              Los dos poll que ESPERAN lo ponen.  El que no espera, no.

DATO         func=0 aparece 2 veces en todo el driver y func=3 aparece 22.
             El vm_flush es uno de los dos.  Y sus dos hermanos en el MISMO
             fichero usan func=3 con mask real.

NO AFIRMO    que quitar el poll mejore el rendimiento.  Ver §5.
```

## 0 · LA PREGUNTA EXACTA

`1495` §6 dejó:

```text
  YA SABIDO   no espera (mask=0 con func=0)
  YA SABIDO   ocupa 6 de 12 dwords
  FALTA       si el hardware lo trata como no-op o si aun asi sincroniza algo
```

Y `1411` lo había planteado desde el principio, con otra palabra: **¿qué
garantía da?**

Se responde mirando los otros dos `POLL_REGMEM` del mismo fichero, que son sus
comparadores directos.

## 1 · LOS TRES, DE UN MISMO FICHERO VIVO

`sdma_v3_0.c` tiene exactamente tres. Leídos enteros:

| emisor | línea | `func` | `HDP_FLUSH` | máscara | referencia | intervalo |
|---|---|---|---|---|---|---|
| `ring_emit_pipeline_sync` | 1036 | **3** | 0 | `0xffffffff` | `seq` real | 4 |
| `ring_emit_hdp_flush` | 459 | **3** | **1** | `ref_and_mask` | `GPU_HDP_FLUSH_DONE` | 10 |
| `ring_emit_vm_flush` | 1064 | **0** | 0 | `0` | **ninguna** | 10 |

```c
/* 1036, pipeline_sync — ESPERA */
SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) |
SDMA_PKT_POLL_REGMEM_HEADER_HDP_FLUSH(0) |
SDMA_PKT_POLL_REGMEM_HEADER_FUNC(3) |          /* equal */
SDMA_PKT_POLL_REGMEM_HEADER_MEM_POLL(1)
        -> addr, seq, 0xffffffff        <- mask real, compara contra seq

/* 459, hdp_flush — ESPERA */
SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) |
SDMA_PKT_POLL_REGMEM_HEADER_HDP_FLUSH(1) |     <<<< ESTE
SDMA_PKT_POLL_REGMEM_HEADER_FUNC(3)             /* == */
        -> mmGPU_HDP_FLUSH_DONE, ref_and_mask   <- mask real

/* 1064, vm_flush — NO ESPERA */
SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) |
SDMA_PKT_POLL_REGMEM_HEADER_HDP_FLUSH(0) |     <<<< y NO ESTE
SDMA_PKT_POLL_REGMEM_HEADER_FUNC(0)             /* always */
        -> 0x1478, 0, 0                         <- mask CERO
```

## 2 · EL ARGUMENTO QUE FALTAVA: `HDP_FLUSH` NO ES DECORATIVO

Medido en todo el driver:

```text
  POLL_REGMEM_HEADER_FUNC(0)     2 sitios
  POLL_REGMEM_HEADER_FUNC(3)    22 sitios
  POLL_REGMEM_HEADER_HDP_FLUSH(1) 6 sitios
```

**`func=0` es la excepción, dos veces de 24.** Y las dos están en ficheros de
distintas generaciones: `sdma_v3_0.c:1064` (vivo en esta tarjeta) y otra. No es
un idiom; es un caso particular.

Más fuerte que eso: **los dos polls que esperan sincronizan, y para eso ponen
`HDP_FLUSH(1)` o `MEM_POLL(1)`.** El de `vm_flush` no pone ninguno de los dos.

```text
  PROVEN_DERIVED  los tres campos que hacen que un POLL_REGMEM ESPERE son
                  FUNC != 0, y HDP_FLUSH o MEM_POLL.  Los dos que esperan
                  cumplen eso.  El vm_flush no cumple ninguno.

  Y POR LO TANTO:  la garantia que 1411 buscaba no esta en func, ni en la
  mascara.  Esta en HDP_FLUSH, que es un bit aparte y que el vm_flush deja
  a 0.

  LO QUE NO AFIRMO:  que con los tres a 0 el packet no sincronice NADA.
  Puede que la sincronizacion este en el SRBM_WRITE que lo precede, que es
  una escritura real.  Eso es hardware y no lo tengo.
```

## 3 · Y EL ORDEN IMPORTA, Y LO DICE EL DRIVER

En los dos que esperan, la secuencia es **escribir, esperar, escribir**:

```c
/* pipeline_sync */
addr, seq, 0xffffffff        <- espera a que seq aparezca
```

```c
/* hdp_flush */
amdgpu_gmc_emit_flush_gpu_tlb(...)
POLL con HDP_FLUSH(1) sobre mmGPU_HDP_FLUSH_DONE
```

Y en `vm_flush`, lo que hay antes del poll es:

```c
amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);   /* 8 dwords utiles */
POLL con func=0, mask=0                                  /* 6 dwords */
```

`gmc_v8_0_emit_flush_gpu_tlb` ya lanza la invalidación —escribe
`mmVM_CONTEXT0_CNTL`, el array de contexto y `mmVM_INVALIDATE_REQUEST`— y el poll
viene detrás. **El trabajo real ya está hecho antes del poll.**

## 4 · LO QUE ESTO LE DICE AL DRIVER PROPIO

```text
  LO QUE HAY QUE COPIAR, y es lo unico con garantia:
    los 8 dwords de gmc_v8_0_emit_flush_gpu_tlb
      SRBM_WRITE(PAGE_TABLE_BLOCK_BASE, pd_addr >> 12)
      SRBM_WRITE(mmVM_INVALIDATE_REQUEST, 1 << vmid)
    mas la escritura de CONTEXT0_CNTL que hace el MMU

  LO QUE HAY QUE RESPONDER ANTES DE OMITIR:
    ¿el poll con func=0 y los tres campos a 0 sincroniza algo?
      - si NO:  son 6 dwords por invalidacion, 4,7 % del buffer (1495), y
               se pueden quitar.
      - si SI:  hay que saber QUE sincroniza, porque entonces el paquete es
               una barrera y quitarlo rompe.

  Y HAY UNA TERCERA POSIBILIDAD que no habia considerado:  que el poll sirva
  como una espera de TIEMPO, porque lleva DW5 = RETRY_COUNT|INTERVAL.  Con
  interval=10 y retry=0xfff, si WAIT_ALWAYS espera interval*retry, el coste
  seria de hasta ~40 microsegundos por paquete, que es MUCHO mas que 6
  dwords.

  ESO cambia por completo la cuenta, y es la medible siguiente.
```

## 5 · LO QUE NO AFIRMO, Y POR QUÉ

```text
NO AFIRMO  que quitar el poll mejore el rendimiento.

  Tres razones, y las tres son serias:
    1. §74 exige benchmark con baseline y modificado.  No hay ninguno.
    2. Puede ser robustez.  Si el SRBM_WRITE y el INVALIDATE_REQUEST se
       solapan en la pipeline, el poll podria dar un orden que el hardware no
       garantiza solo.  "No espera" no es "no hace nada".
    3. Si WAIT_ALWAYS tiene coste de tiempo, quitarlo cambia la sincronizacion
       y no solo el rendimiento.

NO AFIRMO  que los 16 INVALIDATE_REQUEST identicos sean un error.  1493 §4 ya
           lo dejo abierto: puede ser que el scheduler revalida por robustez.

NO AFIRMO  nada sobre si func=0 con mask distinto tendria sentido.  El corpus
           tiene los dos casos juntos, y no se puede separar cual de los dos
           campos es el que anula la espera.
```

## 6 · ESTADO

```text
PROVEN          los 3 POLL_REGMEM de sdma_v3_0.c usan (func, HDP_FLUSH, mask):
                  pipeline_sync  (3, 0, 0xffffffff)   ESPERA
                  hdp_flush      (3, 1, ref_and_mask)  ESPERA
                  vm_flush       (0, 0, 0)             NO ESPERA
PROVEN          func=0 aparece 2 veces en el driver; func=3, 22 veces
PROVEN          HDP_FLUSH(1) aparece 6 veces, ninguna en el vm_flush
PROVEN          los 8 dwords utiles preceden al poll: la invalidacion ya esta
                lanzada por gmc_v8_0_emit_flush_gpu_tlb antes del poll
CONFIRMA        1411: el poll no espera.  Y AFIRMA POR QUE: no pone ninguno de
                los dos campos que enganchan la espera (HDP_FLUSH, MEM_POLL)

CIERRA          la mitad ESTATICA de la pregunta de 1495 §7.3

NOT_DETERMINED  si con los tres campos a 0 el packet sincroniza algo.  Es
                HARDWARE, y sigue bloqueado por credenciales.
NOT_DETERMINED  si WAIT_ALWAYS tiene coste de tiempo (interval * retry).  Con
                interval=10 y retry=0xfff, el techo teorico son ~40 us por
                paquete.  Si es cierto, dominates el 4,7 % de dwords por
                VARIAS ORDENES DE MAGNITUD, y esa es la cuenta que importa.

ABRE            la siguiente medicion es el coste de tiempo, no el de dwords.
                Y hay una forma de medirlo SIN runtime: comparar el anillo
                de una carga que invalida mucho con el de una que invalida
                poco.  Si el tiempo por frame escala con el numero de
                invalidaciones, el poll cuesta tiempo.  Es comparativo, y las
                capturas que hay no son de dos cargas distintas.
```

## 7 · LA LECCION DE ESTE HALLAZGO

`1411` hizo la pregunta correcta —*¿espera o no espera?*— y llevo la respuesta
equivocada: *"no espera porque `mask=0`"*. La respuesta correcta era:

```text
  no espera porque no pone HDP_FLUSH ni MEM_POLL, y porque func=0.
  Y hay OTRO camino para esperar en ese mismo fichero, con los otros dos
  puestos, y el driver lo usa 22 veces.
```

**Un no-op se identifica por comparación con sus hermanos, no por sus propios
campos.** Los tres campos a cero parecían la explicación, y eran la consequencia:
el driver no pone los campos porque en ese sitio no quiere sincronizar, y esa
es una decisión, no un descuido.
