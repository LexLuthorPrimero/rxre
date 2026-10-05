# 1230 — Frente PM4 declarado **SATURATED**, con el inventario completo y el motivo nombrado de cada cosa que queda

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SATURATION · FRONTIER-CLOSE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   ítem 11 de la cola:  "declarar SATURATED el frente PM4 con el motivo
                         escrito"
ESTADO   FRONTIER PM4 / vid.h  ->  SATURATED
MOTIVO   CLAIM CLOSED en lo que el header declara  +  DEPENDENCY EXTERNAL en lo
         que no declara.  Los ocho pendientes que quedan tienen el motivo
         nombrado uno a uno  (§100),  no son "no se me ocurre nada mas"
REABRE   con las 5 condiciones de §56 escritas en §5
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · El inventario completo, medido

```text
  seccion de paquetes PACKET3 en vid.h          lineas 112..455
  en 456 empieza VCE_CMD_NO_OP,  otra lengua de comandos

  defines PACKET3_ con valor                     78
    de los cuales > 0xFF  y por tanto no opcodes    8     (bases de reubicacion, 1212)
  ---------------------------------------------------------
  opcodes validos                                 70
    con al menos un campo declarado               15
    con la ventana vacia                          55     y los 55 explicados  (1229 §2)
```

Los 55 vacíos se dividen en **51** cuya ventana contiene una sola línea (el opcode siguiente) y
**4** (`SET_CONFIG_REG`, `SET_CONTEXT_REG`, `SET_SH_REG`, `SET_UCONFIG_REG`) cuyo único contenido son
las bases `*_START`/`*_END`. **Ninguno pendiente.**

## 2 · Los 15 que sí declaran estructura, y hasta dónde llega cada uno

```text
  prosa Y comentario de grupo de dword    4    DMA_DATA        16 campos
                                                 MAP_QUEUES      11
                                                 QUERY_STATUS     6
                                                 UNMAP_QUEUES    10
  prosa, sin comentario de grupo           1    SET_RESOURCES    3
  ninguna de las dos                       10    SURFACE_SYNC    23
                                                 EVENT_WRITE_EOP 11
                                                 MEM_SEMAPHORE    5
                                                 WRITE_DATA       5
                                                 INDIRECT_BUFFER  4
                                                 WAIT_REG_MEM     4
                                                 EVENT_WRITE      2
                                                 PREAMBLE_CNTL    2
                                                 FRAME_CONTROL    1
                                                 SET_BASE         1
```

Y qué emite `gfx_v8_0.c` de esos 10:

```text
  paquete            campos  emisiones  count en gfx_v8_0.c
  WRITE_DATA             5        10    3, cnt_ce, cnt_de      <- dos son RUNTIME
  EVENT_WRITE            2         5    0
  WAIT_REG_MEM           4         3    5
  EVENT_WRITE_EOP       11         2    4
  INDIRECT_BUFFER        4         2    2
  PREAMBLE_CNTL          2         2    0
  SET_BASE               1         1    2
  SURFACE_SYNC          23         1    3
  FRAME_CONTROL          1         0    --    NUNCA lo emite GFX8
  MEM_SEMAPHORE          5         0    --    NUNCA lo emite GFX8
  ------------------------------------------------------------------------
  total                          26 emisiones
```

**26 emisiones sobre 10 paquetes.** De los dos con cero emisiones, `MEM_SEMAPHORE` no lo emite
**ningún** `gfx_v*_0.c` y `FRAME_CONTROL` tampoco: no son de GFX8, son de la familia GFX9 en
adelante. Se declaran en `vid.h` porque el header es compartido, no porque se usen aquí.

**Invariante acumulado:** `count = payload − 1`, comprobado en **12 paquetes, 12 aciertos, 0
fallos** (`1199` tres puntos, `1225` ocho paquetes, `1227` uno). Es el único invariante del frente
que se sostiene sin excepciones.

## 3 · Los ocho pendientes, cada uno con su motivo nombrado

§100 admite `SATURATED` por `CLAIM CLOSED`, `NO DISCRIMINANT REMAINS`, `NO OBSERVABLE AVAILABLE`,
`REMAINING UNCERTAINTY NON-CRITICAL`, `COST/RISK UNJUSTIFIED` o `DEPENDENCY EXTERNAL`. Estos ocho
se reparten entre las tres últimas, y ninguno es "no se me ocurre nada más".

```text
  1  ANCHURAS POR EXTRACCION EN GFX8
     no hay en el arbol ni una linea de codigo que extraiga campos de paquete.
     La unica via son los headers de registro, y de ahi salen cotas y mascaras
     nativas,  no la disposicion en dwords.
     ESTADO  NO_OBSERVABLE_AVAILABLE

  2  LA ESPECIFICACION DE AMD
     033 ya declaro que AMD no publica el bloque de gestion de memoria de GFX8.
     La especificacion del formato de paquetes tampoco esta en el arbol,  en
     ninguna generacion.  Todo lo anterior sale de lectura de codigo,  nunca de
     la fuente primaria.
     ESTADO  DEPENDENCY_EXTERNAL

  3  MAP_QUEUES.CONTROL2  y  el maximo de DOORBELL_OFFSET
     DOORBELL_OFFSET no es un registro:  es un puntero a un MQD en VRAM.  No se
     puede validar con mascaras de registro.  Su maximo depende de
     num_compute_rings,  que es runtime.
     ESTADO  DEPENDENCY_RUNTIME

  4  PASID con dos bits
     PASID(x) = (x) << 0  con DOORBELL_OFFSET en <<2  deja PASID en [1:0].  La
     convencion a/b  (vid.h:449,451)  es sistematica  (1229 §5),  asi que la
     prosa dice bien y el campo esta mal nombrado.  Reproducido en los 4 headers
     del paquete  (vid.h, soc15d.h, nvd.h, gfx_v12_1_pkt.h).  Y 0 emisiones en
     todo el driver:  no hay ni una escritura con la que contrastarlo.
     ESTADO  NO_DISCRIMINANT_REMAINS

  5  LA PERMUTACION DE sid.h EN LOAD_SH_REG / LOAD_CONFIG_REG / LOAD_CONTEXT_REG
     sid.h da  0x61 / 0x5F / 0x60  y los otros cinco headers dan
     0x5F / 0x60 / 0x61.  0 emisiones de los tres en todo el arbol.  Sin uso no
     hay discriminante,  y los dos lados estan escritos.
     ESTADO  NO_DISCRIMINANT_REMAINS

  6  ibref.py  110 de 116
     7 vectores de round-trip,  una sola causa:  el literal de cabecera del
     fixture no esta en el .pyc  y rellenarlo seria inventar el fixture.
     ESTADO  DEPENDENCY_EXTERNAL

  7  CP_WAIT_REG_MEM
     el registro existe  y declara CERO campos.  No es un hueco de busqueda:  es
     que el header no lo describe  y nadie mas lo hace en el arbol.
     ESTADO  CLAIM_NOT_APPLICABLE

  8  RUNTIME
     no se ha leido ni un registro de 0000:01:00.0.  dmesg da "Operacion no
     permitida" sin escalar;  /sys/kernel/debug/dri/ da "Permiso denegado".
     Cerraria el ENG_SEL de 25 bits de esta RX550  (1228)  y el PTE de 074,
     que ya no tienen mas soporte estatico.
     ESTADO  DEPENDENCY_EXTERNAL
```

De los ocho, **seis no son trabajo pendiente**: son dependencias externas o de runtime, y dos son
`NOT_APPLICABLE` por propiedades del propio header, no por falta de esfuerzo.

## 4 · Lo que el frente dejó cerrado, que es la parte que importa

Lo que sí se determinó y no estaba antes:

```text
  count = payload - 1                      12/12 paquetes,  0 fallos
  la posicion del dword de CONTROL no es uniforme:
      COPY_DATA lo lleva primero,  DISPATCH_DIRECT, COND_EXEC e
      INDIRECT_BUFFER_CONST lo llevan al final                            (1225)
  8 de los 9 paquetes sin clase, clasificados por el count contra las
  escrituras reales;  NOP no es un paquete en un flujo sino el valor con el
  que memset32 rellena el anillo entero                                     (1225, 1226)
  0x3FFF del NOP es el saturado del campo de 14 bits,  no un tamaño de anillo:
  cubre 1/16 del KIQ de GFX8                                              (1226)
  QUERY_STATUS:  la prosa declara 7 dwords,  hay macros para 2,  y las 4 que
  faltan son [31:0] enteras;  en GFX8 no se emite nunca                    (1227)
  ENG_SEL en <<25 en GFX8, GFX9 y GFX10;  <<28 solo en GFX12.1.  Y
  DOORBELL_OFFSET = [ENG_SEL-1 : 2],  asi que 23 bits en GFX8 y 26 en GFX12.1,
  que es lo que explica el cambio como deliberado y no como errata       (1228)
  las 4 anomalias de opcode del conjunto de headers estan todas en sid.h,
  ni una en vid.h                                                          (1224)
  la seccion de paquetes PACKET3 acaba en la linea 455,  y la atribucion por
  posicion se salia 32 macros de copia de registro                        (1229)
  55 de 70 opcodes sin estructura declarada,  y los 55 explicados          (1229)
```

## 5 · Condiciones de reapertura (§56)

El frente **no está muerto**, está acotado. Se reabre, sin destruir lo anterior, con cualquiera de:

```text
  a)  APARECION DE UN CAMPO.  Si una cabecera de paquete del arbol gana prosa que
      nombre sus dwords,  uno de los 10 sin estructura pasa a cerrarse con el
      mismo metodo que cerro los 5.  Es lo unico que amplia el frente.
  b)  UNA EMISION NUEVA.  Si el driver emite uno de los dos que hoy no emite
      (FRAME_CONTROL, MEM_SEMAPHORE),  aparece un segundo punto de emision y
      count = payload - 1 deja de ser un unico punto por paquete.
  c)  LA ESPECIFICACION DE AMD.  Resuelve de una vez los pendientes 2, 4 y 5,
      que hoy son tres NOT_DETERMINED por falta de la fuente primaria.
  d)  ACCESO DE RUNTIME.  Una lectura controlada sobre 0000:01:00.0  cierra el
      ENG_SEL de 25 bits y el PTE de 074.
  e)  UN HEADER NUEVO EN EL ARBOL.  Si entra una generacion mas,  ENG_SEL y
      DOORBELL_OFFSET se vuelven a comparar  y la divergencia de 1228 vuelve a
      tener posibilidad de cerrarse.
```

## 6 · Procedimiento

```text
PREGUNTA   ¿el frente PM4 esta saturado?  ¿que queda  y por que no se puede?
FUENTES    pm4_grupos.py  --selftest (68 vectores),  --plano,  --clase
           el censo de emisiones sobre gfx_v8_0.c,  cuenta de OCURRENCIAS
MEDIDO     seccion 112..455  ·  78 defines con valor  ·  8 > 0xFF  ·  70 opcodes
           15 con estructura (4 prosa+y-grupo, 1 prosa, 10 ninguna)
           55 sin estructura,  explicados (51 ventana de una linea, 4 bases)
           26 emisiones de GFX8 sobre 10 paquetes
           2 de los 10 con cero emisiones:  FRAME_CONTROL y MEM_SEMAPHORE
           count = payload - 1 en 12/12
PENDIENTES 8,  cada uno con estado asignado de entre los seis motivos de §100
REABRE     5 condiciones,  escritas
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  el frente PM4 ya no es donde trabajar.  El siguiente frente con
  discriminante real es el de RUNTIME:  una lectura controlada sobre
  0000:01:00.0.  Todo lo demas que queda abierto depende de runtime o de una
  especificacion que AMD no publica,  y ninguna de las dos depende de mi.
```