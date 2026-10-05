# 1227 — `QUERY_STATUS`: la prosa declara 7 dwords, hay macros para 2. Las 4 palabras que faltan son **[31:0] enteras**, así que no falta ninguna macro. Y en GFX8 no se emite nunca

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSE-OUT · SEMANTICS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   ítem 9 de la cola:  "atribucion de las 31 macros PACKET3_ de la
                          ventana de QUERY_STATUS"
CORRIGE  la cifra que yo mismo tinha anotado:  no son 31 macros,  son 6
VALIDA   count = payload - 1 en un paquete mas:  12 en total con 12 aciertos
DESRULEO NO FALTAN MACROS PARA 4 DE LOS 6 PAYLOAD:  son palabras [31:0]
         enteras y un entero completo no tiene campo que declarar
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · La ventana, y el error de cifra

```text
  vid.h:436   #define PACKET3_QUERY_STATUS   0xA4
```

Y debajo, **6 macros, no 31**:

```text
  :445   /* CONTROL */
  :446   PACKET3_QUERY_STATUS_CONTEXT_ID(x)       ((x) << 0)
  :447   PACKET3_QUERY_STATUS_INTERRUPT_SEL(x)    ((x) << 28)
  :448   PACKET3_QUERY_STATUS_COMMAND(x)          ((x) << 30)
  :449   /* CONTROL2a */
  :450   PACKET3_QUERY_STATUS_PASID(x)            ((x) << 0)
  :451   /* CONTROL2b */
  :452   PACKET3_QUERY_STATUS_DOORBELL_OFFSET(x)  ((x) << 2)
  :453   PACKET3_QUERY_STATUS_ENG_SEL(x)          ((x) << 25)
```

Las "31" no eran de esta ventana. Eran el recuento de una región más ancha del header. **Anoté
mal la cifra que iba a cerrar**, y lo primero es medirla, no darla por buena.

## 2 · La prosa declara 7 dwords, las macros cubren 2

```c
  vid.h:437-444
      /* 1. header
       * 2. CONTROL
       * 3. CONTROL2
       * 4. ADDR_LO [31:0]
       * 5. ADDR_HI [31:0]
       * 6. DATA_LO [31:0]
       * 7. DATA_HI [31:0]
       */
```

Cruce de los dos inventories:

```text
  dword        nombre        hay macros?   cuantas   ancho derivado
  --------------------------------------------------------------------------
  1            header        --            --        --
  2            CONTROL       si            3         ver §4
  3            CONTROL2      si            3         ver §4
  4            ADDR_LO       no            0         [31:0] entero
  5            ADDR_HI       no            0         [31:0] entero
  6            DATA_LO       no            0         [31:0] entero
  7            DATA_HI       no            0         [31:0] entero
```

**Las 4 sin macro están declaradas como `[31:0]` en la propia prosa.** Un entero completo no
tiene ni máscara ni desplazamiento: no hay nada que declarar. Contarlas como "macros que
faltan" es un error de modelo, no trabajo pendiente.

Es el mismo punto que `1210`/`1225`: la prosa acierta el recuento de dwords, y la ausencia de
macro en una palabra entera es la forma correcta de que falte.

## 3 · `count = 5` cuadra, y es la duodécima comprobación

La emisión, idéntica en los 6 sitios que la tienen:

```c
  gfx_v10_0.c:3800-3811   (identica en v9_0, v9_4_3, v11_0, v12_0, v12_1)
      amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_QUERY_STATUS, 5));
      amdgpu_ring_write(kiq_ring,
                PACKET3_QUERY_STATUS_CONTEXT_ID(0) |
                PACKET3_QUERY_STATUS_INTERRUPT_SEL(0) |
                PACKET3_QUERY_STATUS_COMMAND(2));
      amdgpu_ring_write(kiq_ring, /* Q_sel: 0, vmid: 0, engine: 0, num_Q: 1 */
                PACKET3_QUERY_STATUS_DOORBELL_OFFSET(ring->doorbell_index) |
                PACKET3_QUERY_STATUS_ENG_SEL(eng_sel));
      amdgpu_ring_write(kiq_ring, lower_32_bits(addr));
      amdgpu_ring_write(kiq_ring, upper_32_bits(addr));
      amdgpu_ring_write(kiq_ring, lower_32_bits(seq));
      amdgpu_ring_write(kiq_ring, upper_32_bits(seq));
```

```text
  count = 5   ->   payload = 6   ->   + cabecera = 7 dwords
  prosa dice 7 dwords                                        CUADRA
  escrituras de payloadcontadas = 6                           CUADRA

  1199   3 puntos          1225   8 paquetes mas        1227   este
  total 12 comprobaciones, 12 aciertos, 0 fallos
```

**Y las 4 escrituras "que faltan" son exactamente las 4 palabras enteras.** `lower_32_bits(addr)`,
`upper_32_bits(addr)`, `lower_32_bits(seq)`, `upper_32_bits(seq)`: direcciones y datos de 32 bits
completos, escritos sin tocar bits. La prosa y el driver coinciden dword a dword, 7 de 7.

## 4 · Lo que sí se deriva: dos anchuras

Dentro de un mismo dword declarado, el inicio del campo siguiente acota al anterior — el
método de `1207`, que aquí sí aplica porque el grupo está declarado:

```text
  CONTROL    CONTEXT_ID      << 0     INTERRUPT_SEL  << 28   COMMAND  << 30
             => CONTEXT_ID ocupa [27:0]  = 28 bits
             => INTERRUPT_SEL ocupa [29:28] = 2 bits
             => COMMAND ocupa [31:30] = 2 bits
             28 + 2 + 2 = 32,  sin hueco

  CONTROL2   PASID           << 0     DOORBELL_OFFSET << 2   ENG_SEL << 25
             => PASID ocupa [1:0]  = 2 bits     <-- ver §5
             => DOORBELL_OFFSET ocupa [24:2] = 23 bits,  o mas
             => ENG_SEL ocupa [31:25] = 7 bits
```

El `CONTROL` sale **perfecto: 28+2+2 = 32, sin un solo bit perdido.** Es la misma clase de
acierto que `1207` (PIPE=2, ME=1, QUEUE=3 exactos contra `num_pipe_per_mec`).

`DOORBELL_OFFSET` da ≥23 bits, lo cual **coincide con `1205`**: allí quedó escrito que el máximo
de `DOORBELL_OFFSET` depende de `num_compute_rings`, que es runtime. 23 bits es el suelo que da
el header, y el techo está en otra parte.

## 5 · La asimetría real: dos campos con macro que nadie usa, dos campos usados que no tienen macro

El comentario de `gfx_v10_0.c:3805` nombra **cuatro** campos de `CONTROL2`:

```text
  /* Q_sel: 0, vmid: 0, engine: 0, num_Q: 1 */
```

Y de esos cuatro:

```text
  campo        hay macro?   se usa en la emision?   desplazamiento
  --------------------------------------------------------------------
  Q_sel        NO           NO                     el comentario dice 0
  vmid         NO           NO                     el comentario dice 0
  engine       NO           NO                     el comentario dice 0
  num_Q        NO           NO                     el comentario dice 1
  --------------------------------------------------------------------
  DOORBELL_OFFSET  SI       SI                     << 2
  ENG_SEL           SI       SI                     << 25
  PASID             SI       NO  <<< nunca se usa   << 0
```

**`PASID` es el reverso exacto**: tiene macro, desplazamiento declarado, y **cero usos en los 6
sitios de emisión**. Los seis escriben `DOORBELL_OFFSET | ENG_SEL` y nunca `PASID`.

Mientras tanto `Q_sel`, `vmid`, `engine` y `num_Q` están **nombrados en un comentario de
emisión** — o sea, el driver afirma conocerlos — y no tienen macro.

Eso tiene una lectura mecánica y una preferencia:

- `PASID` sin uso: no es un campo de este camino, o quedó de una versión anterior.
- `PASID(x) = (x) << 0` con `DOORBELL_OFFSET` en `<< 2` obliga a que `PASID` ocupe `[1:0]`, dos
  bits. **Un PASID de 2 bits no puede ser un PASID.** O el comentario `CONTROL2a` /
  `CONTROL2b` de `vid.h:449,451` designa **dos dwords distintos**, no dos mitades del mismo, o
  la macro `PASID` está mal.

La prosa (`:439`) nombra **`CONTROL2` en singular**, un solo dword. Si fuera verdad, `PASID`
ocupa `[1:0]` y es absurdo. Si `PASID` está bien, la prosa omite un dword. **Los dos no pueden
ser ciertos a la vez**, y es una contradicción real del header, no una duda mía.

## 6 · Alcance para GFX8

```text
  gfx_v9_0.c      QUERY_STATUS con count=5
  gfx_v9_4_3.c    QUERY_STATUS con count=5
  gfx_v10_0.c     QUERY_STATUS con count=5
  gfx_v11_0.c     QUERY_STATUS con count=5
  gfx_v12_0.c     QUERY_STATUS con count=5
  gfx_v12_1.c     QUERY_STATUS con count=5
  gfx_v8_0.c      APARICIONES: 0        <-- GFX8 no lo emite
```

**GFX8 declara el paquete con prosa completa y 6 macros, y no lo emite ni una vez.** De los 6
sitios, ninguno es de esta generación: el primero es GFX9.

Consecuencia para el alcance: el layout de `QUERY_STATUS` está **PROVEN para GFX9..GFX12**
(7 de 7 dwords contra la prosa) y es **NOT_OBSERVED en GFX8**. No es que sea distinto, es que
este driver no lo usa en esta generación, así que no hay emisión contra la cual contrastarlo.

## 7 · Procedimiento

```text
PREGUNTA   atribuir las macros de la ventana de QUERY_STATUS
FUENTES    vid.h:436-453 (opcode, prosa, 6 macros)
           los 6 puntos de emision en gfx_v9_0 / v9_4_3 / v10_0 / v11_0 /
           v12_0 / v12_1,  leidos con linea
           conteo de apariciones en gfx_v8_0.c
MEDIDO     6 macros,  no 31:  la cifra que yo había anotado estaba mal
           prosa 7 dwords contra 6 payload escritos:  CUADRA
           count=5 -> payload=6:  invariante de 1225 se sostiene por duodecima vez
           CONTROL:  CONTEXT_ID[27:0]=28  INTERRUPT_SEL[29:28]=2  COMMAND[31:30]=2
                     28+2+2=32 sin hueco
           CONTROL2: PASID[1:0]=2 bits,  que no puede ser un PASID
           PASID tiene macro y 0 usos;  Q_sel/vmid/engine/num_Q se nombran en un
           comentario de emision y no tienen macro
           gfx_v8_0.c: 0 apariciones
CONTRADICCION  registrada,  sin resolver
           vid.h:439 dice "CONTROL2" en singular (un dword)  y  :450 pone
           PASID en <<0 con DOORBELL_OFFSET en <<2  ->  PASID queda en 2 bits.
           Los dos no pueden ser ciertos.  Queda NOT_DETERMINED:  no se puede
           decidir sin la especificacion,  que 033 ya declaro que no publica,  y
           sin lectura del hardware.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - la contradiccion de PASID se puede acotar mas sin hardware:  ver si otro
    header del linaje (soc15d.h, que es GFX9) mantiene el <<0,  o si lo cambia
  - CONTROL es el segundo caso de cierre exacto de la prosa contra la
    derivacion por desplazamiento,  tras PIPE/ME/QUEUE de 1207
```