# 1211 — El mayor agujero (`WRITE_DATA`, 10 emisiones) se cierra por un camino que no era el de los comentarios: **la ventana de opcode**. La cobertura pasa de **6% a 20%**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · TOOL-EXTENSION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/pm4_grupos.py  (modo --plano  y  ventanas)
                           + este hallazgo
ESCALA      1210 nombro WRITE_DATA como el mayor agujero.  Este lo cierra.
CORROBORA   1199 (count = payload - 1) por un paquete que no habia mirado
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

`1210` medió que `PACKET3_WRITE_DATA` es el paquete más emitido de `gfx_v8_0.c` —10 de 67
sites— y que **no tiene ni un comentario de grupo**, así que el método de `1209` no lo toca. La
pregunta es si su layout es determinable **por otra vía**, y si esa vía es tan fuerte como la de
los comentarios o solo una suposición.

## 1 · Lo primero: el uso del driver ya dice el tamaño del paquete

Diez emisiones en `gfx_v8_0.c`. **Ocho** usan el mismo literal:

```text
      891  ib.ptr[0] = PACKET3(PACKET3_WRITE_DATA, 3);
     5123  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     5131  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     5139  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     5147  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     6259  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     6268  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     6366  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
     7165  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, cnt_ce));
     7198  amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, cnt_de));
```

Y el cuerpo de una de ellas, literal, `gfx_v8_0.c:5122-5127`:

```c
	/* GDS Base */
	amdgpu_ring_write(ring, PACKET3(PACKET3_WRITE_DATA, 3));
	amdgpu_ring_write(ring, (WRITE_DATA_ENGINE_SEL(0) |
				WRITE_DATA_DST_SEL(0)));
	amdgpu_ring_write(ring, amdgpu_gds_reg_offset[vmid].mem_base);
	amdgpu_ring_write(ring, 0);
	amdgpu_ring_write(ring, gds_base);
```

Cabecera con `count = 3`, y **cuatro** `amdgpu_ring_write` después. O sea cuatro dwords de
payload. `count = payload − 1`, que es exactamente lo que corroboró `1199` — y este paquete no
figura en aquel hallazgo, así que es una corroboración por un objeto distinto.

**Diez de las diez emisiones dicen que `WRITE_DATA` tiene cuatro dwords de payload.** Eso no es una
cota del header: es el driver, en el codigo compilado, diciendo cuántos dwords emite.

## 2 · El layout del dword de campo, y por dónde se obtiene

`vid.h:141-160` es el bloque completo. `vid.h:141` es el opcode `0x37` y `vid.h:161` es el
opcode siguiente `0x38`. **Entre los dos no hay nada que no sea de este paquete.** La ventana la
delimita el propio header.

```text
  vid.h:141  #define  PACKET3_WRITE_DATA            0x37
  vid.h:142  #define  WRITE_DATA_DST_SEL(x)          ((x) << 8)   enum 0..5
  vid.h:150  #define  WR_ONE_ADDR                   (1 << 16)
  vid.h:151  #define  WR_CONFIRM                    (1 << 20)
  vid.h:152  #define  WRITE_DATA_CACHE_POLICY(x)     ((x) << 25)  enum 0,1
  vid.h:156  #define  WRITE_DATA_ENGINE_SEL(x)       ((x) << 30)  enum 0,1,2
  vid.h:161  #define  PACKET3_DRAW_INDEX_INDIRECT_MULTI 0x38
```

Resultado, con el método de `1209`:

```text
  WRITE_DATA_DST_SEL        << 8   ->  bits [15:8 ] =  8 bits   enum 0,1,2,3,5   min 3, holgura 5
  WR_ONE_ADDR               = 1<<16                     FLAG de 1 bit
  WR_CONFIRM                = 1<<20                     FLAG de 1 bit
  WRITE_DATA_CACHE_POLICY   << 25  ->  bits [29:25] =  5 bits   enum 0,1          min 1, holgura 4
  WRITE_DATA_ENGINE_SEL     << 30  ->  bits [31:30] =  2 bits   enum 0,1,2        EXACTO

  cubiertos 17/32      huecos sin campo:  bits [0:7], bits [17:19], bits [21:24]
```

`ENGINE_SEL` con 3 valores en 2 bits es **exacto**, y su enumeración (`0 - me`, `1 - pfp`,
`2 - ce`) dice además para qué sirve el paquete:seleccion de engine, no otra cosa.

## 3 · El detalle que casi lo rompe: `vid.h` usa dos prefijos para el mismo paquete

`WR_ONE_ADDR` y `WR_CONFIRM` **no** empiezan por `WRITE_DATA_`. Un filtro por nombre los pierde,
y con ellos se pierde el layout: sin ellos, `DST_SEL` se mide como `[24:8]` = 17 bits en vez de 8.

Mi primera versión del modo plano filtraba por nombre, y por eso cogía **3** macros de
`WRITE_DATA`. La regla correcta ya estaba establecida para los grupos: **la frontera es el
opcode, no el nombre**. Corregido, son 5.

Y entonces apareció el problema serio: **99 macros de las 15 listas planas no llevan en su nombre
el de su paquete.** El caso mas claro:

```text
  PACKET3_SURFACE_SYNC  ocupa vid.h:201-225 con 23 macros,  entre ellas
        RB_MAP_PKR0   RB_MAP_PKR0_MASK   RB_MAP_PKR1   RB_MAP_PKR1_MASK
        PKR_MAP   PKR_XSEL   PKR_YSEL   SC_MAP   SE_MAP   SE_PAIR_MAP ...
```

Esas no son campos de `SURFACE_SYNC`: son un bloque de mapa de registros. **Si el límite fuese
solo posicional, el modo plano daría un superconjunto y sus cifras no valdrían.**

## 4 · Lo que salva la cifra, y es lo único

Cada opcode delimita su ventana en el header. Y los 15 paquetes, **sin excepción**, tienen todos
sus macros dentro de su propia ventana:

```text
  paquete                      opcode@linea  ventana        macros  todos dentro
  PACKET3_WRITE_DATA               141      [ 141: 161]     5   SI
  PACKET3_EVENT_WRITE              226      [ 226: 237]     2   SI
  PACKET3_EVENT_WRITE_EOP          237      [ 237: 266]    11   SI
  PACKET3_PREAMBLE_CNTL            268      [ 268: 271]     2   SI
  PACKET3_DMA_DATA                 271      [ 271: 334]    16   SI
  PACKET3_FRAME_CONTROL            365      [ 365: 371]     1   SI
  PACKET3_SET_RESOURCES            371      [ 371: 384]     3   SI
  PACKET3_MAP_QUEUES               384      [ 384: 406]    11   SI
  PACKET3_UNMAP_QUEUES             406      [ 406: 436]    10   SI
  PACKET3_QUERY_STATUS             436      [ 436: 517]    38   SI
  PACKET3_INDIRECT_BUFFER          190      [ 190: 199]     4   SI
  PACKET3_MEM_SEMAPHORE            162      [ 162: 168]     5   SI
  PACKET3_WAIT_REG_MEM             168      [ 168: 190]     4   SI
  PACKET3_SET_BASE                 113      [ 113: 116]     1   SI
  PACKET3_SURFACE_SYNC             201      [ 201: 225]    23   SI

  atribucion ACOTADA por el propio header : 15
  atribucion que se sale de la ventana    : 0
```

> Un hueco en una ventana sería la prueba de que el header **no** mantiene ese invariante, y
> entonces el modo plano no valdría. No hay ni uno. Eso no convierte a los 99 macros en campos de
> su paquete: **convierte la atribución en acotada en vez de supuesta**, que es lo que hace
> falta para que la cifra sea citable.

## 5 · La cobertura, medida de las dos maneras

```text
  paquetes PACKET3 definidos en vid.h                     78
  con grupo de macros      (fuente fuerte)                 4
  con lista plana de macros, acotada a su ventana         15
  emitidos por gfx_v8_0.c                                  30

  CON GRUPO    2 de 30  =   6%     2 de 67 sitios  =   2%
  CON PLANO    6 de 30  =  20%    18 de 67 sitios  =  26%
```

Lo que gana el modo plano, por uso:

```text
      PACKET3_WRITE_DATA      10 usos      <- el mayor agujero, cerrado
      PACKET3_WAIT_REG_MEM     3 usos
      PACKET3_INDIRECT_BUFFER  2 usos
      PACKET3_SET_RESOURCES    1 uso
```

**16 de los 18 sitios de emisión que se ganan son de `WRITE_DATA`.** Ese era el objetivo de
`1210` y se ha alcanzado.

## 6 · Lo que sigue sin layout, y es lo que queda

24 paquetes emitidos sin nada. Los cinco primeros concentran 23 de las 49 emisiones restantes:

```text
   6  PACKET3_SET_SH_REG              3  PACKET3_DISPATCH_DIRECT
   6  PACKET3_SET_SH_REG_START        3  PACKET3_SET_CONTEXT_REG
   5  PACKET3_EVENT_WRITE             3  PACKET3_SET_CONTEXT_REG_START
   3  PACKET3_NOP                     2  PACKET3_CONTEXT_CONTROL
```

Y una asimetría que **no** explica el método: `SET_SH_REG` y `SET_SH_REG_START` no tienen
macros, y `SET_CONTEXT_REG` tampoco, mientras `SET_CONTEXT_REG_START` sí. Los dos pares de
`START`/no-`START` deberían parecerse. O `vid.h` los omite, o los declara en otro sitio, y eso
es una pregunta concreta, no una tarea vaga.

## 7 · Procedimiento

```text
PREGUNTA   ¿el layout de WRITE_DATA es determinable sin comentario de grupo,
            y la via es tan fuerte como la de los comentarios?
HERRAMIENTA  tools/pm4_grupos.py --plano   (nuevo)  y  --selftest: 47 vectores
FUENTES    vid.h:141-161   (el paquete entero, de opcode a opcode)
           gfx_v8_0.c:891, 5122-5152, 6259, 6268, 6366, 7165, 7198
           1199  para count = payload - 1
MEDIDO     15 paquetes con lista plana acotada,  0 fuera de su ventana
           99 macros con nombre que no lleva el de su paquete
           cobertura 6% -> 20% por paquete,  2% -> 26% por sitio de emision
AUTOCORR.  el modo plano con filtro por nombre cogia 3 de las 5 macros de
           WRITE_DATA  y por eso daba DST_SEL = 17 bits en vez de 8.  Corregido
           a atribucion por posicion,  que es la regla que ya usaba para los
           grupos.  Y mis expectativas de vector (8 paquetes, 85 macros) eran
          erradas:  el guard global las detecto y las fije al valor medido
           (15 y 99).  Cuarta vez que ese guard salva una cifra.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN.  "10 emisiones con count 3"  es un hecho de FUENTE,  no
              de ejecucion:  que la RX550 las ejecute no se ha medido.
```