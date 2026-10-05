# 1208 — El segundo paquete determinado: `DMA_DATA`. Y una coherencia interna que se **autocomprueba**: la prosa del header y sus macros dicen lo mismo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLAIM-SUPPORT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura y aritmetica)
CONTINUA   1207  con una clase de evidencia nueva:  la enumeracion INLINE de
                   valores legales, que vid.h escribe junto a cada campo
NUEVO      2o dword-group de PM3 determinado.  Y el metodo se autocomprueba.
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

`1207` determinó `MAP_QUEUES` leyendo los comentarios que particionan los macros. La misma
estructura aparece en `DMA_DATA`, y este paquete trae **más** que `MAP_QUEUES`: una cabecera en
prosa que numera los dwords y da los rangos de bits de dos de ellos. La pregunta es si eso
basta para determinarlo entero, y si los macros y la prosa **se contradicen**.

## 1 · La clase de evidencia que ningún hallazgo anterior usó

`vid.h` escribe, junto a cada campo, la enumeración de sus valores legales:

```c
   281  #              define PACKET3_DMA_DATA_ENGINE(x)     ((x) << 0)
   282  		/* 0 - ME
   283  		 * 1 - PFP
   284  		 */
   285  #              define PACKET3_DMA_DATA_SRC_CACHE_POLICY(x) ((x) << 13)
   286  		/* 0 - LRU
   287  		 * 1 - Stream
   288  		 * 2 - Bypass
   289  		 */
```

Esto da una **cota inferior por valor**, independiente de la cota por desplazamiento de `1207`.
Cuando las dos coinciden, el ancho no es una cota: es el ancho. Y la dirección de la atribución
—el enum sigue al macro que documenta— es comprobable **por sentido**, que es lo que hice:

```text
  el enum de vid.h:292-295 dice  0, 1, 3
  se atribuye a                PACKET3_DMA_DATA_DST_SEL
  0 = DST_ADDR using DAS,  1 = GDS,  3 = DST_ADDR using L2
```

Un selector con tres destinos no es un booleano de caché. La atribución es correcta por
significado, no solo por posición.

## 2 · El fallo de mi parser, y por qué casi publica una cifra falsa

Mi primer parser contaba la enumeración que **precede** al macro, y obtenía **55 valores**. El
correcto da **78**. Los dos contaban **23 bloques**: el mismo número de bloques con el contenido
equivocado, porque cada bloque perdía su primer valor cuando abría con `/*` en la misma línea.

La variante de este fallo es la peor de las que he tenido:

```text
  los fallos anteriores   un regex que no encuentra nada devuelve CERO
  este                    un regex que casi encuentra todo devuelve un numero
                          PLAUSIBLE y con la cuenta de bloques CORRECTA
```

Un cero se nota; un 55 con 23 bloques parece sano. **Lo que lo delató fue un guard escrito a
mano dentro del propio script**, que compara su salida contra un positivo leído a mano
(`vid.h:282-284` → `[0, 1]`). La primera vez que lo corrí el guard dijo `SIGUE SIN VERLO`, y por
eso no publicó nada. Causa: `abre.match()` ancla en la posición 0 y la línea empieza con
tabuladores. Sin el guard, esta tabla habría salido con 78 y las atribuciones mal.

## 3 · `CONTROL` de `DMA_DATA`, dword 2 de 7

```text
  PACKET3_DMA_DATA_ENGINE            << 0   -> bits [12:0 ] = 13 bits  enum 0,1     min 1, holgura 12
  PACKET3_DMA_DATA_SRC_CACHE_POLICY  << 13  -> bits [14:13] =  2 bits  enum 0,1,2   EXACTO
  PACKET3_DMA_DATA_SRC_VOLATILE      = 1<<15                       FLAG de 1 bit
  PACKET3_DMA_DATA_DST_SEL           << 20  -> bits [24:20] =  5 bits  enum 0,1,3   min 2, holgura 3
  PACKET3_DMA_DATA_DST_CACHE_POLICY  << 25  -> bits [26:25] =  2 bits  enum 0,1,2   EXACTO
  PACKET3_DMA_DATA_DST_VOLATILE      = 1<<27                       FLAG de 1 bit
  PACKET3_DMA_DATA_SRC_SEL           << 29  -> bits [30:29] =  2 bits  enum 0,1,2,3 EXACTO
  PACKET3_DMA_DATA_CP_SYNC           = 1<<31                       FLAG de 1 bit

  cubiertos 27 de 32      huecos SIN campo:  bits [16:19],  bits [28]
```

**Tres campos exactos** de ocho. Los `FLAG` no tienen ancho por desplazamiento —`(1 << 15)` es un
valor constante, no un campo— y su ancho es de 1 bit por construcción, no por deducción.

Los huecos importan y no se pueden tapar: **`vid.h` no da cuenta de 5 de los 32 bits de
`CONTROL`.** No se puede afirmar que esta lista esté completa.

## 4 · `COMMAND`, dword 7 de 7, y aquí está la coherencia interna

```text
  PACKET3_DMA_DATA_DIS_WC        = 1<<21   FLAG
  PACKET3_DMA_DATA_CMD_SRC_SWAP  << 22  -> bits [23:22] = 2 bits  enum 0,1,2,3  EXACTO
  PACKET3_DMA_DATA_CMD_DST_SWAP  << 24  -> bits [25:24] = 2 bits  enum 0,1,2,3  EXACTO
  PACKET3_DMA_DATA_CMD_SAS       = 1<<26   FLAG
  PACKET3_DMA_DATA_CMD_DAS       = 1<<27   FLAG
  PACKET3_DMA_DATA_CMD_SAIC      = 1<<28   FLAG
  PACKET3_DMA_DATA_CMD_DAIC      = 1<<29   FLAG
  PACKET3_DMA_DATA_CMD_RAW_WAIT  = 1<<30   FLAG

  cubiertos por macros: bits [21:30]
```

Y la prosa del propio header, `vid.h:272-279`, literal:

```c
   272  /* 1. header
   273   * 2. CONTROL
   274   * 3. SRC_ADDR_LO or DATA [31:0]
   275   * 4. SRC_ADDR_HI [31:0]
   276   * 5. DST_ADDR_LO [31:0]
   277   * 6. DST_ADDR_HI [7:0]
   278   * 7. COMMAND [30:21] | BYTE_COUNT [20:0]
   279   */
```

```text
  la prosa dice   COMMAND [30:21]  |  BYTE_COUNT [20:0]
  los macros dan  COMMAND ocupa bits [21:30]
  BYTE_COUNT      no tiene macro:  ningun PACKET3_DMA_DATA_BYTE_COUNT existe
  JUNTOS, COMMAND y BYTE_COUNT cubren [30:0] = los 31 bits bajos

  LO QUE QUEDA:  el bit 31.  La prosa no lo nombra y ningun macro lo ocupa.
                 NOT_FOUND
```

**Esto es lo importante del hallazgo.** La prosa y los macros son dos afirmaciones
independientes dentro de la misma fuente primaria, y **coinciden**. No es que el código fuente
sea autoridad: es que el código fuente se **autocomprueba**, y cuando dos partes sueltas de un
mismo documento dicen lo mismo sobre el mismo hecho, el error tiene que estar en ambas a la vez
para pasar inadvertido.

> `PIPE` de `MAP_QUEUES` quedó corroborado por cuatro vías, y ahora se cierra con una quinta y
> distinta: `vid.h` es internamente coherente respecto a los rangos que declara, en dos paquetes
> independientes. Es coherencia de documento, no de hardware. `CORROBORATED`, no `PROVEN`.

## 5 · Lo que este hallazgo NO abre

```text
  NO dice que los campos EXACTOS no puedan ser mas anchos.  "EXACTO" quiere
  decir que el ancho calculado coincide con el minimo que exige la
  enumeracion.  Que el hardware lo interprete asi es OTRO claim,  y no medido.

  NO dice que los huecos [16:19] y [28] de CONTROL no pertenezcan a ningun
  campo.  Dice que ningun macro los nombra.  NOT_FOUND,  no PROVEN_ABSENT.

  NO ha leido ni un registro de la RX550.  RUNTIME=NOT_RUN.

  NO cierra el resto de vid.h.  Los otros paquetes siguen sin determinar,  y
  el metodo exige para cada uno:  comentario de particion + enumeraciones +
  prosa de cabecera.  No todos tendran las tres cosas.
```

## 5-bis · Corrección posterior, de MÉTODO y no de cifras

`tools/pm4_grupos.py` (`1209`) reproduce **exactamente** las cifras de §3 y §4: `CONTROL` con
27/32 y huecos `[16:19]` y `[28]`, `COMMAND` con los 8 macros en `[21:30]` y dos `EXACTO`.

Pero encontró **tres defectos en el método de este hallazgo**. Ninguno altera las cifras
publicadas, porque aquí filtré por nombre de macro; los tres alterarían cualquier otro cálculo:

```text
  1.  El límite de un grupo NO es el comentario siguiente:  es el siguiente opcode.
      vid.h:309  /* COMMAND */  arrastraba PACKET3_SET_RESOURCES_VMID_MASK,
      PACKET3_SET_RESOURCES_UNMAP_LATENTY y PACKET3_SET_RESOURCES_QUEUE_TYPE,
      que son de otro paquete.  Desplazamientos 0, 16 y 29,  y el ultimo CHOCABA
      con PACKET3_DMA_DATA_CMD_DAIC = 1<<29.

  2.  P_GRUPO = (CONTROL\d?|COMMAND)  aceptaba 9 de los 14 comentarios de dword.
      Los 5 que no aceptaba  --  CONTROL2a, CONTROL2b, CONTROL3a, CONTROL3b  y el
      CONTROL2a de QUERY_STATUS  --  se absorbian en el grupo anterior:  sus
      desplazamientos se sumaban y salian "bits [-1:0] = 0 bits"  y
      "holgura -2",  que son veredictos IMPOSIBLES publicados como si fueran datos.

  3.  La prosa de cabecera indexada por número de dword COLISIONABA entre paquetes:
      p[7] devolvia la prosa de otro paquete,  no la de DMA_DATA.
```

El segundo es **el mismo fallo de clase que ya tenía grabado como error propio**: una clase de
carácter que se queda corta y deja pasar cosas sin fallar. Volvió porque la lección no se
generalizó a la herramienta nueva. Quinta vez que aparece esa clase, y la segunda en este árbol
con un patrón literal igual.

> Un regex que no encuentra nada devuelve cero y se nota. Uno que encuentra casi todo devuelve
> un número plausible y **no se nota**. Lo único que los separa es contrastar el recuento del
> filtro contra el recuento sin filtro, y eso es un vector, no una nota.

## 6 · Procedimiento

```text
PREGUNTA   ¿el header basta para determinar DMA_DATA,  y se contradicen sus
            macros con su prosa?
FUENTES    vid.h:272-334,  leido con numero de linea
           gfx_v8_0.c  para el uso real de DMA_DATA
METODO     interseccion de TRES clases de evidencia del mismo primario:
             1. desplazamiento del macro        -> cota por arriba
             2. enumeracion inline de valores   -> cota por abajo
             3. prosa de cabecera del paquete   -> contraste independiente
AUTOVALIDACION  guard dentro del propio script contra un positivo leido a
             mano (vid.h:282-284).  La PRIMERA ejecucion del guard fallo y no
             publico ninguna cifra.  Sin el guard habria publicado 78 con las
             atribuciones cruzadas en un bloque.
DISCREPANCIA REAL  ninguna.  La unica que reporto como "DIFIERE" era mi propia
             notacion:  la prosa escribe [alto:bit] y mi tabla [bit:alto].
             El conjunto de bits es identico.  Corregido antes de escribir.
AUTOCORR.  dos fallos de script mio:  (a) al abrir bloque inicializaba
             cur_line pero no cur_vals -> AttributeError;  (b) comparaba un
             DESPLAZAMIENTO contra un ANCHO,  que no significa nada.  Los
             dos los encontre al ver la tabla,  no antes.
DISPOSITIVO  NINGUNO
RUNTIME      NOT_RUN
```