# 1217 — Sí hay anchuras nativas de GFX8: **21**, en la prosa de `vid.h`. Y la prosa acierta el recuento de dwords en los **5** paquetes, contra **28** puntos de emisión

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el "falta una mascara de GFX8"  de 1216 §5.  No hay mascaras,  pero si
         hay anchuras:  en la prosa,  que es la otra forma de declararlas
VALIDA   la prosa de vid.h como autorizativa para el recuento de dwords
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Qué se cierra

`1216` §5 decía, con nombre:

> `FALTA una mascara de GFX8. vid.h tiene 0.`

Eso sigue siendo cierto y no lo muevo. Pero la pregunta que estaba detrás —*¿hay alguna anchura
de campo de GFX8 en el árbol?*— tiene una respuesta que no había buscado: **`vid.h` declara
anchuras en prosa**, con la misma forma `[hi:lo]` que usan las máscaras de `soc15d.h`, y esas sí son
del ASIC de esta placa.

## 1 · La prosa, y el recuento de dwords que declara

Cinco paquetes tienen cabecera en prosa. Literal, `vid.h:371-380` y `:406-413`:

```c
   371  #define  PACKET3_SET_RESOURCES        0xA0
   372  /* 1. header
   373   * 2. CONTROL
   374   * 3. QUEUE_MASK_LO [31:0]
   375   * 4. QUEUE_MASK_HI [31:0]
   376   * 5. GWS_MASK_LO [31:0]
   377   * 6. GWS_MASK_HI [31:0]
   378   * 7. OAC_MASK [15:0]
   379   * 8. GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]
   380   */

   406  #define  PACKET3_UNMAP_QUEUES         0xA3
   407  /* 1. header
   408   * 2. CONTROL
   409   * 3. CONTROL2
   410   * 4. CONTROL3
   411   * 5. CONTROL4
   412   * 6. CONTROL5
   413   */
```

Eso declara el **número de dwords de payload**. Y el driver dice cuántos escribe. Con
`count = payload − 1`, corroborado en `1199` por tres puntos de emisión más `.emit_ib_size = 7`:

```text
  paquete          prosa     payload    driver count   payload   coincide
  DMA_DATA          6 dwords      6      5 (1 ASIC)        6        SI
  SET_RESOURCES     7 dwords      7      6 (7 ASIC)       7        SI
  MAP_QUEUES        6 dwords      6      5 (7 ASIC)       6        SI
  UNMAP_QUEUES      5 dwords      5      4 (7 ASIC)       5        SI
  QUERY_STATUS      6 dwords      6      5 (6 ASIC)       6        SI
```

**Cinco de cinco, sin una sola discrepancia, en 28 puntos de emisión repartidos por 8
implementaciones GFX** (`gfx_v8_0`, `v9_0`, `v9_4_3`, `v10_0`, `v11_0`, `v12_0`, `v12_1`, y
`amdkfd_gfx_v9/v10/v11/v10_3`).

Eso convierte la prosa en **fuente autorizada para el número de dwords**, y es lo que faltaba para
`1216`: las fronteras de dword de GFX8 existen, declaradas como prosa, y validadas contra el
driver.

> Y explica la aparente contradicción de `1213`: `UNMAP_QUEUES` tiene **siete** comentarios de
> grupo (`CONTROL`, `CONTROL2a`, `CONTROL2b`, `CONTROL3a`, `CONTROL3b`, `CONTROL4`, `CONTROL5`) y
> **cinco** dwords de payload según la prosa. No es contradicción: `CONTROL2a`+`CONTROL2b` son el
> dword 3 partido en dos, y `CONTROL3a`+`CONTROL3b` el dword 4. La numeración `a`/`b` de `vid.h`
> es una subdivisión, no un dword nuevo.

## 2 · Las 21 anchuras nativas, y las 6 que importan

```text
  DMA_DATA       dword 3  DATA              [31:0 ] = 32 bits
  DMA_DATA       dword 4  SRC_ADDR_HI       [31:0 ] = 32 bits
  DMA_DATA       dword 5  DST_ADDR_LO       [31:0 ] = 32 bits
  DMA_DATA       dword 6  DST_ADDR_HI       [ 7:0 ] =  8 bits
  DMA_DATA       dword 7  COMMAND           [30:21] = 10 bits
  DMA_DATA       dword 7  BYTE_COUNT        [20:0 ] = 21 bits
  SET_RESOURCES  dword 3  QUEUE_MASK_LO     [31:0 ] = 32 bits
  SET_RESOURCES  dword 4  QUEUE_MASK_HI     [31:0 ] = 32 bits
  SET_RESOURCES  dword 5  GWS_MASK_LO       [31:0 ] = 32 bits
  SET_RESOURCES  dword 6  GWS_MASK_HI       [31:0 ] = 32 bits
  SET_RESOURCES  dword 7  OAC_MASK          [15:0 ] = 16 bits
  SET_RESOURCES  dword 8  GDS_HEAP_SIZE     [16:11] =  6 bits
  SET_RESOURCES  dword 8  GDS_HEAP_BASE     [ 5:0 ] =  6 bits
  MAP_QUEUES     dword 4..7  MQD/WPTR ADDR  [31:0 ] = 32 bits  x4
  QUERY_STATUS   dword 4..7  ADDR/DATA       [31:0 ] = 32 bits  x4
```

Quince son la palabra entera, que no aporta nada. **Las seis que sí son campo de bits:**

```text
  SET_RESOURCES  OAC_MASK        [15:0 ] = 16 bits    <- el driver lo emite
  SET_RESOURCES  GDS_HEAP_SIZE   [16:11] =  6 bits    <- el driver lo emite
  SET_RESOURCES  GDS_HEAP_BASE   [ 5:0 ] =  6 bits    <- el driver lo emite
  DMA_DATA       DST_ADDR_HI     [ 7:0 ] =  8 bits    <- GFX8 no lo emite
  DMA_DATA       COMMAND         [30:21] = 10 bits    <- GFX8 no lo emite
  DMA_DATA       BYTE_COUNT      [20:0 ] = 21 bits    <- GFX8 no lo emite
```

Y `SET_RESOURCES` **lo emite `gfx_v8_0.c:4331`**. Eso son tres anchuras de campo de GFX8,
verificadas por prosa, en un paquete que esta placa usa de verdad.

La corroboración es independiente y ya existe: `1208` §4 comprobó que la prosa de `DMA_DATA`
—`7. COMMAND [30:21] | BYTE_COUNT [20:0]`— coincide exactamente con el grupo de macros, que da
`COMMAND` en `[21:30]`. **Prosa y macros dicen lo mismo de la misma palabra.** Eso es lo que
convierte la prosa en fuente y no en comentario.

## 3 · Y el driver escribe ese dword, literal

`gfx_v8_0.c:4325-4331`, el bloque `SET_RESOURCES` que emite:

```c
	amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_SET_RESOURCES, 6));
	amdgpu_ring_write(kiq_ring, 0);	/* vmid_mask:0 queue_type:0 (KIQ) */
	amdgpu_ring_write(kiq_ring, lower_32_bits(queue_mask));	/* queue mask lo */
	amdgpu_ring_write(kiq_ring, upper_32_bits(queue_mask));	/* queue mask hi */
	amdgpu_ring_write(kiq_ring, 0);	/* gws mask lo */
	amdgpu_ring_write(kiq_ring, 0);	/* gws mask hi */
	amdgpu_ring_write(kiq_ring, 0);	/* oac mask */
	amdgpu_ring_write(kiq_ring, 0);	/* gds heap base:0 gds heap size:0 */
```

Siete dwords después de la cabecera, `count = 6`, y la prosa dice siete. **Coincide**, y coincide
también el **comentario del driver**, que nombra en el orden exacto los campos que nombra la
prosa: `queue mask lo/hi`, `gws mask lo/hi`, `oac mask`, `gds heap base`/`gds heap size`.

Ese es el cuarto ejemplo de que la prosa es fuente utilizable. En este caso el dword 8 lo escribe
un `0` con comentario, así que **no se observa qué pasa con `GDS_HEAP_BASE [5:0]` y
`GDS_HEAP_SIZE [16:11]` cuando no son cero**. En esta ruta el driver nunca pone un heap de GDS, y
por tanto esta máquina no puede enseñar esos dos campos funcionando.

## 4 · Estado, y lo que sigue sin poder

```text
  RECUENTO DE DWORD DE GFX8      PROVEN-dentro-del-alcance-medido
                                 5 paquetes, 28 puntos de emision, 8 ASIC, 0 fallos
  ANCHURAS NATIVAS DE GFX8      21 en prosa,  6 de campo de bits,  3 en un
                                 paquete que la placa usa
  PROSA = AUTORIDAD             CORROBORATED  por dos vias independientes:
                                   1208  prosa == macros en DMA_DATA
                                   1217  prosa == count del driver en 5/5

  LO QUE SIGUE SIN PODER
  - validar el metodo por desplazamiento con una mascara de GFX8:  no hay
    ninguna,  y las de GFX9/GFX10 no se transfieren
  - el comportamiento de GDS_HEAP_BASE y GDS_HEAP_SIZE con valores distintos de
    cero:  el driver de esta ruta escribe 0,  y eso es RUNTIME o nada
  - los 51 paquetes sin macros siguen sin determinarse por esta via:  solo 5
    tienen prosa
```

## 5 · Procedimiento

```text
PREGUNTA   ¿hay anchuras de campo de GFX8 en el arbol,  y la prosa de vid.h es
            fiable?
FUENTES    vid.h:271-279, 371-380, 384-391, 406-413, 436-443  (los 5 bloques)
           gfx_v8_0.c:4325-4331  (el bloque SET_RESOURCES)
           los 13 ficheros gfx_v*.c y amdkfd_gfx_v*.c  del arbol,  para el
           recuento de emisiones  (leido del arbol,  no de memoria)
MEDIDO     prosa == driver en 5 de 5 paquetes,  28 puntos de emision
           21 anchuras en prosa,  6 no triviales,  3 en SET_RESOURCES
           21 campos con mascara en soc15d/nvd siguen sin transferir
AUTOCORR.  ninguno en este hallazgo.  El de 1216 quedo escrito ahi.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```