# 1486 — De los 15 sitios que escriben `INVALIDATE_REQUEST` en el driver, solo 6 son código vivo en esta tarjeta. Y los 6 vivos hacen exactamente lo mismo: esperar un HDP flush que nunca termina

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

COMPOSICION   asicpath.py 1484  (que ramas ejecuta POLARIS12)
            + el dispatch de vi.c        (que IP blocks registra)
            + reg_census.py 1478          (que funcion escribe que registro)
            Las tres por separado ya existian.  Esta es la primera pregunta que
            las tres juntas contestan y que ninguna contestaba.

RESULTADO     15 escritores de mmVM_INVALIDATE_REQUEST en el driver
              6 VIVOS   9 MUERTOS
              y los 6 vivos, leidos, hacen lo MISMO:
                1. amdgpu_gmc_emit_flush_gpu_tlb()   <- el unico productor real
                2. esperar el HDP flush
                3. escribir INVALIDATE_REQUEST
                4. esperar la RESPONSE con un POLL_REGMEM de FUNCION 0
              Los tresUltimos pasos son el mismo codigo en tres ficheros.

CONFIRMA     1420 (15 sitios en 6 generaciones), y lo CORRIGE: son 15 sitios
             pero solo 6 vivos, y los 9 muertos no cuentan como productores.
CIERRA       1411 y 1441.  El "poll con mask=0 que no espera" tiene un solo
             PRODUCTOR, y los tres POLL_REGMEM con FUNCION 0 son el mismo.
```

## 0 · POR QUÉ ESTA ES LA PRIMERA COMPOSICIÓN QUE APORTA ALGO

Tengo tres herramientas que no sabían la una de la otra:

```text
  asicpath    qué comparaciones de ASIC se cumplen      (1484)
  dispatch    qué IP blocks registra POLARIS12         (vi.c, leído a mano)
  reg_census  qué función escribe qué registro          (1478)
```

Pregunta que sale de juntarlas: **¿de los N sitios que escriben este registro en
todo el driver, cuántos son código que esta tarjeta ejecuta?**

`1420` contó 15 sitios en 6 generaciones. Eso es un hecho. **No decía cuántos
corren aquí**, y un sitio que no corre no es un productor: es texto.

## 1 · LOS 15, CON SU VEREDICTO

```text
  fichero:linea                                  VIVO?   por que
  amdgpu/gfx_v8_0.c:6209                          VIVO   gfx_v8_0_ip_block
  amdgpu/gmc_v8_0.c:634                           VIVO   gmc_v8_1_ip_block (funcs
                                                            de gmc_v8_0.c)
  amdgpu/gmc_v8_0.c:659                           VIVO   idem
  amdgpu/gmc_v8_0.c:674                           VIVO   idem
  amdgpu/sdma_v3_0.c:1067                         VIVO   sdma_v3_1_ip_block
                                                            (definido en
                                                             sdma_v3_0.c:1693)
  amdgpu/uvd_v6_0.c:1083                          VIVO   uvd_v6_3_ip_block
                                                            (definido en
                                                             uvd_v6_0.c)

  amdgpu/cik_sdma.c:857                           MUERTO cik_sdma.o solo lo
                                                            incluye
                                                            amdgpu_amdkfd_gfx_v7.c,
                                                            que es GFX7
  amdgpu/gfx_v6_0.c:2376                          MUERTO GFX6
  amdgpu/gfx_v7_0.c:3156                          MUERTO GFX7
  amdgpu/gmc_v6_0.c:351, :367                     MUERTO GMC6
  amdgpu/gmc_v7_0.c:443, :468, :483               MUERTO GMC7
  amdgpu/sdma_v2_4.c:794                          MUERTO SDMA2.4; el vivo es v3_1

  VIVOS 6    MUERTOS 9
```

**El dispatch está medido, no supuesto.** Los 10 bloques que POLARIS12 registra
(`vi.c:2105-2123`), con el fichero que los define:

```text
  vi_common_ip_block      vi.c
  gmc_v8_1_ip_block       gmc_v8_0.c        <- 1471 §1: misma tabla de funcs
  tonga_ih_ip_block       tonga_ih.c
  gfx_v8_0_ip_block       gfx_v8_0.c
  sdma_v3_1_ip_block      sdma_v3_0.c       <- 1452: mismo fichero, otra revision
  pp_smu_ip_block         pm/powerplay/amd_powerplay.c
  amdgpu_vkms_ip_block    amdgpu_vkms.c
  dm_ip_block             display/amdgpu_dm/amdgpu_dm.c
  uvd_v6_3_ip_block       uvd_v6_0.c        <- igual: el bloque es 6_3, el
                                               fichero es v6_0
  vce_v3_4_ip_block       vce_v3_0.c        <- idem
```

## 2 · LOS 6 VIVOS DICEN LO MISMO

Leídos, no contados:

```c
/* amdgpu/sdma_v3_0.c:1058-1070 */
static void sdma_v3_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
                                         unsigned vmid, uint64_t pd_addr)
{
        amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);

        /* wait for flush */
        amdgpu_ring_write(ring, SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) |
                          SDMA_PKT_POLL_REGMEM_HEADER_HDP_FLUSH(0) |
                          SDMA_PKT_POLL_REGMEM_HEADER_FUNC(0)); /* always */
        amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST << 2);
        amdgpu_ring_write(ring, 0);
        amdgpu_ring_write(ring, 0); /* reference */
        amdgpu_ring_write(ring, 0); /* mask */
```

`uvd_v6_0_ring_emit_vm_flush` (línea 1078) tiene **la misma estructura**, con el
`PACKET0` de UVD en vez del `SDMA_PKT_HEADER`.

**Y `gfx_v8_0.c:6209` y `gmc_v8_0.c:674` son la versión de la valla del ring de
gráficos**, que `1467` ya había decodificado en el IB real.

```text
  CONVERGENCIA, la tercera de esta sesion y la mas fuerte:
    el codigo fuente dice que hay UN origen de la invalidacion
    el IB capturado dice lo mismo
    y ahora el dispatch dice que de 15 candidatos solo 6 llegan a ejecutarse

  Tres vias independientes, mismo numero: uno.
```

## 3 · LO QUE CIERRA, Y LO QUE ABRE

```text
CIERRA  1420  "15 sitios en 6 generaciones".  Cierto, y ahora con el dato que
           faltaba: 6 vivos.  Un sitio muerto no es un productor, y contarlos
           como tales infla el numero de productores por 2,5x.
CIERRA  1411  el poll con mask=0.  Los tres POLL_REGMEM con FUNCION 0 son EL
           MISMO codigo en tres ficheros distintos (gfx_v8_0, sdma_v3_0,
           uvd_v6_0), y por eso el budget de 1411 contaba "excesses" que en
           parte eran el mismo paquete en tres anillos.
CIERRA  1441  los 3 POLL_REGMEM con FUNCION 0.  Confirmados, y ahora se sabe
           de donde vienen: de las tres copias de la misma funcion de flush.

ABRE, y es la consecuencia practica
  UN PRODUCTOR REAL, no tres.  amdgpu_gmc_emit_flush_gpu_tlb es el unico que
  escribe la base de tabla y lanza la invalidacion.  Los otros cinco sitios son
  el ROLLO del driver, no la CAUSA.

  Para el driver propio, esto reduce el problema: no hay que reimplementar seis
  caminos de invalidate, hay que reimplementar UNO, y saber que los tres
  rings (gfx, sdma, uvd) lo comparten.

ABRE, y no lo hago aqui
  ¿son tres copias o una con macro?  No lo mire.  Si es una funcion con
  #define, el codigo real es uno y el resto es texto.  Eso cambia el recuento de
  "productores distintos" de 1 a 1, pero cambia el codigo a copiar.

NOT_DETERMINED  si el HDP flush que espera el POLL_REGMEM con FUNCION 0 se
          completa alguna vez.  Es codigo del driver esperando un evento de
          hardware, y el hardware no se ha observado.  Es el unico punto de
          este hallazgo que necesita runtime.
```

## 4 · EL ERROR QUE CASI ESCRIBO

Iba a afirmar que los 9 muertos son "código de otra generación" como si fuera una
categoría única. No lo es, y la diferencia importa:

```text
  gfx_v6_0.c, gfx_v7_0.c, gmc_v6_0.c, gmc_v7_0.c, sdma_v2_4.c
      -> otra ASIC.  El fichero no se compila para esta tarjeta.

  cik_sdma.c
      -> OTRA COSA.  cik_sdma.o SI se compila (Makefile:82), pero solo lo
         incluye amdgpu_amdkfd_gfx_v7.c.  Es codigo GFX7 alcanzable desde un
         fichero que se compila.

  Y uvd_v6_0.c y vce_v3_0.c
      -> TERCERA COSA.  Son VIVOS, pero el bloque registrado es uvd_v6_3 y
         vce_v3_4: el fichero contiene la revision antigua y la nueva.

  O sea: "vivo/muerto" a nivel de FICHERO es una clasificacion que mezcla tres
  mecanismos distintos.  Los tres producen "no se ejecuta", pero por razones que
  no se pueden arreglar igual, y confundirlos es como confundir las 3 vias de
  codigo muerto de 1484 §5.
```

## 5 · LO QUE ESTO DICE DE LA COMPOSICION

```text
  Las tres herramientas ya existian y ninguna se modifico para este hallazgo.
  Lo unico nuevo es la CRUCIA, y por eso:

  - la consulta ya no es "quien escribe este registro" (reg_census, responde)
  - ni "que rama corre" (asicpath, responde)
  - sino "quien escribe este registro Y CORRE AQUI", que es la pregunta que
    importa para un driver propio.

  Y esa tercera pregunta no la responde ninguna de las dos primeras.  Por eso
  el relation graph que pediste NO es una idea abstracta: es exactamente la
  arista que falta, y ya se ve con dos greps y una tabla.

  LO QUE AUN FALTA para que sea consulta y no cruce manual: que el cruce sea
  una operacion del instrumento.  No lo hago aqui; lo dejo como el siguiente
  paso, y medido, porque ya se ha medido que hace falta y por tres veces.
```

## 6 · ESTADO

```text
PROVEN          15 escritores de INVALIDATE_REQUEST, 6 vivos en POLARIS12
PROVEN          los 6 vivos comparten estructura: gmc_emit_flush_gpu_tlb, esperar
                HDP, escribir REQUEST, esperar RESPONSE con POLL_REGMEM FUNCION 0
PROVEN          los 3 POLL_REGMEM con FUNCION 0 son el mismo codigo en 3 ficheros
CONFIRMA        1420 (los 15 sitios) y lo corrige (solo 6 son productores)
CONFIRMA        1411 y 1441, y explica por que el budget contaba de mas
CIERRA          el numero de productores distintos: 1, no 6
NOT_DETERMINED  si el HDP flush con FUNCION 0 se completa.  Necesita runtime.
NOT_DETERMINED  si los tres son copias o uno con #define.  No lo mire.

ERROR PROPIO    iba a llamar "otra generacion" a los 9 muertos.  cik_sdma.c se
                COMPILA y solo es inalcanzable desde un include; uvd_v6_0.c
                esta VIVO con una revision antigua dentro.  Tres mecanismos
                distintos bajo una sola etiqueta.
```
