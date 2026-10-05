# 1207 — El layout de `MAP_QUEUES` sale completo del propio `vid.h`: el header **nombra los dos dwords** en un comentario, y eso faltaba desde `1201`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLAIM-SUPPORT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura y aritmetica)
CORROBORA  1203, 1205 y 1206 por una CUARTA via,  esta del primario
CORRIGE    el alcance de 1201 ("38 campos con << y 0 con mascara": cierto,  y
            aun asi insufficiente,  porque faltaba leer los COMENTARIOS)
NUEVO      el primer dword PM4 del proyecto cuyo layout queda DETERMINADO
            desde fuente primaria
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

`1205`/`1206` dejaron cerrado el ancho de `PIPE` (2 bits) y de `ME` (1 bit) por tres y cuatro
vías. Quedaban abiertos, entre otros, `DOORBELL_OFFSET` y el `CONTROL2` que el propio driver
menciona en el mapa de la cola. La pregunta es una sola:

```text
¿CUAL ES EL LAYOUT DE LOS DOS DWORD DE MAP_QUEUES EN GFX8?
```

## 1 · La pieza que faltaba desde `1201`: los comentarios del header

`1201` contó en `vid.h` 38 campos de PM3 con `<<` y **0** con máscara, y metering correctly que
eso no determina un layout. Es cierto, y aun así era una lectura incompleta. El header
**particiona los campos por dword en comentarios**, y eso no se vio porque el recuento era de
macros, no de estructura:

```c
   392   */
   393  /* CONTROL */
   394  #              define PACKET3_MAP_QUEUES_QUEUE_SEL(x)       ((x) << 4)
   395  #              define PACKET3_MAP_QUEUES_VMID(x)            ((x) << 8)
   396  #              define PACKET3_MAP_QUEUES_QUEUE_TYPE(x)      ((x) << 21)
   397  #              define PACKET3_MAP_QUEUES_ALLOC_FORMAT(x)    ((x) << 24)
   398  #              define PACKET3_MAP_QUEUES_ENGINE_SEL(x)      ((x) << 26)
   399  #              define PACKET3_MAP_QUEUES_NUM_QUEUES(x)      ((x) << 29)
   400  /* CONTROL2 */
   401  #              define PACKET3_MAP_QUEUES_CHECK_DISABLE(x)   ((x) << 1)
   402  #              define PACKET3_MAP_QUEUES_DOORBELL_OFFSET(x) ((x) << 2)
   403  #              define PACKET3_MAP_QUEUES_QUEUE(x)           ((x) << 26)
   404  #              define PACKET3_MAP_QUEUES_PIPE(x)            ((x) << 29)
   405  #              define PACKET3_MAP_QUEUES_ME(x)              ((x) << 31)
```

`vid.h:393` dice `CONTROL` y `vid.h:400` dice `CONTROL2`. **La partición es código fuente, no
inferencia mía.** Eso era lo que `1201` no miró, y explica por qué el mismo bloque de macros
que en `1201` «no determinaba un layout» sí lo determina: la información estaba, en la misma
pantalla, en los comentarios.

## 2 · El método: el desplazamiento del campo siguiente acota el ancho por arriba

No hay anchos declarados, pero cada campo empieza en un bit conocido y el siguiente empieza en
otro. El intervalo entre ambos es el ancho, y no hay forma de escribir un valor en el campo de
arriba que no invada el de abajo. Es el mismo fundamento que `ancho_pm4.py` pero **por
desplazamiento en vez de por valor**, y por eso cubre campos que la otra vía no cubre.

```text
  CONTROL    (vid.h:394-399)
      QUEUE_SEL         << 4    ->  bits [ 7:4]  =  4 bits
      VMID              << 8    ->  bits [20:8]  = 13 bits
      QUEUE_TYPE        << 21   ->  bits [23:21] =  3 bits
      ALLOC_FORMAT      << 24   ->  bits [25:24] =  2 bits
      ENGINE_SEL        << 26   ->  bits [28:26] =  3 bits
      NUM_QUEUES        << 29   ->  bits [31:29] =  3 bits
      cubiertos 28/32      hueco:  bits [3:0]

  CONTROL2   (vid.h:401-405)
      CHECK_DISABLE     << 1    ->  bits [ 1:1]  =  1 bit
      DOORBELL_OFFSET   << 2    ->  bits [25:2]  = 24 bits
      QUEUE             << 26   ->  bits [28:26] =  3 bits
      PIPE              << 29   ->  bits [30:29] =  2 bits
      ME                << 31   ->  bits [31:31] =  1 bit
      cubiertos 31/32      hueco:  bits [0:0]
```

Ninguno de los dos huecos está explicado por ningún macro. `CONTROL[3:0]` son 4 bits enteros
sin campo, lo que **impide** afirmar que esta lista esté completa para ese dword.

## 3 · Lo fuerte: tres campos caen EXACTOS, sin holgura

Esto es más fuerte que una cota inferior. Cruzando cada ancho con la tabla que el driver mismo
declara:

```text
  campo      bits        ancho  valor maximo que el driver puede pasar   ajuste
  ------------------------------------------------------------------------------
  ME         [31:31]      1     num_mec          = 2  = 2^1             EXACTO
  PIPE       [30:29]      2     num_pipe_per_mec = 4  = 2^2             EXACTO
  QUEUE      [28:26]      3     num_queue_per_pipe = 8 = 2^3            EXACTO

  DOORBELL_OFFSET [25:2]  24     sin cota calculable   -> con holgura
  VMID            [20:8]  13     sin cota calculable   -> con holgura
```

Los tres campos que se pueden cruzar con una constante del driver **no tienen ni un bit de
sobra**. No es que el campo sea «lo bastante ancho para»: es exactamente el número de bits que
hace falta para indexar `adev->gfx.mec`.

> `PIPE` = 2 bits queda corroborado por cuarta vía, y esta es la **primaria**: el propio header
> del kernel, no el código que lo llama, ni el censo de nombres de `1205`.

## 4 · Cruce con la herramienta ya validada: complementaria, no contradictoria

`ancho_pm4.py` (`1203`) sobre los mismos macros:

```text
  MAP_QUEUES_PIPE         necesita 2 bits    PIPE(pipe)          con pipe = pipe
  MAP_QUEUES_ME           ancho NO deducible  ME(x)
  MAP_QUEUES_QUEUE        ancho NO deducible  QUEUE(queue_id)
  MAP_QUEUES_VMID         ancho NO deducible  VMID(m->cp_hqd_vmid)
  MAP_QUEUES_DOORBELL_OFFSET  ancho NO deducible  DOORBELL_OFFSET(doorbell_off)
```

`NO deducible` **no significa «no se sabe»**: significa «el argumento es una variable, así que
no hay literal del que sacar una cota por valor». Las dos vías miden cosas distintas:

```text
  via por VALOR      (ancho_pm4.py)   cota inferior,  desde el literal que el
                                      driver pasa:  PIPE necesita 2
  via por DESPLAZAMIENTO  (este)      cota por arriba,  desde el inicio del
                                      campo siguiente:  PIPE es 2
```

Sobre `PIPE` **coinciden exactamente**. Sobre `ME`, `QUEUE`, `VMID` y `DOORBELL_OFFSET` solo
hay la segunda, y por eso este hallazgo **extiende** lo que `1203` podía decir, en vez de
corregirlo.

## 5 · `DOORBELL_OFFSET`: lo que se cierra y lo que no

```text
  CERRADO   el campo son 24 bits,  bits [25:2],  y el <<2 significa que la unidad
            es un dword.  Eso responde "de que ancho" y NO responde "de que valor".

  ABIERTO   el VALOR maximo que el driver puede pasar:
                ring->doorbell_index = adev->doorbell_index.mec_ring0 + ring_id
            y  ring_id va hasta num_compute_rings-1,  que el driver calcula como
                min(amdgpu_gfx_get_num_kcq(adev), ...)   (gfx_v8_0.c:5265)
            que es de runtime.

    NO CONCLUIR  que 24 bits sean necesarios.  Con los numeros de esta placa el
    valor cabe en unos 13 bits:  la holgura es de hecho,  y esta reconstruccion
    no la puede cuantificar sin el numero de KCQ.

    NOT_DETERMINED   el ancho REAL de arriba (la cota es por desplazamiento,  no
                      por extraccion:  no hay codigo en el arbol que extraiga
                      DOORBELL_OFFSET)
```

`GFX8_MEC_HPD_SIZE = 4096` (`gfx_v8_0.c:61`) va a `hpd_eop_gpu_addr`, **no** a
`doorbell_index`. No son el mismo campo y no se deben sumar.

## 6 · Clasificación epistémica

```text
  layout de CONTROL y CONTROL2   CORROBORATED   fuente primaria,  y el propio
                                 header nombra los dos dwords
  PIPE = 2 bits                  CORROBORATED   4 vias,  la 4a primaria
  ME   = 1 bit                   CORROBORATED   3 vias
  QUEUE= 3 bits                  CORROBORATED   ajuste exacto con
                                                 num_queue_per_pipe = 8
  DOORBELL_OFFSET ancho          CORROBORATED   24 bits por desplazamiento
  DOORBELL_OFFSET valor maximo   NOT_DETERMINED   depende de runtime
  bits [3:0] de CONTROL          NOT_FOUND      ningun macro los nombra
  anchuras por EXTRACCION        NOT_FOUND      ningun codigo del arbol
                                                extrae estos campos
  reloj / ASIC leido             NOT_OBSERVED   RUNTIME=NOT_RUN
```

La diferencia con `1200`/`1201` es el punto: aquellos hallazgos, que no determinaban un layout a partir de
desplazamientos sueltos. Aquí hay **una declaración de agrupación en la fuente**, que es lo que
convierte once desplazamientos en dos tablas.

## 7 · Procedimiento

```text
PREGUNTA   ¿cual es el layout de los dos dword de MAP_QUEUES en GFX8?
HERRAMIENTA  ninguna nueva.  Aritmetica de intervalos sobre los desplazamientos
            leidos, y contraste con la herramienta validada en 1203.
FUENTE     vid.h:386-408,  con los numeros de linea
           gfx_v8_0.c:4345-4356  (los dos dwords que el driver escribe)
           gfx_v8_0.c:1862-1865  (calculo de doorbell_index)
           gfx_v8_0.c:5265       (num_compute_rings, de runtime)
AUTOCORR.  mi primer calculo de huecos uso "inicio+1" como final del campo,  y
           produjo huecos que se solapaban con los campos.  Rehago con el
           intervalo real.  El error era mio,  no del dato.
CLASE      ESTA_ES_LA_PRIMERA_VEZ  que un dword PM4 queda determinado desde
           fuente primaria.  Los 37 campos PM3 restantes de vid.h siguen sin
           particion declarada,  y son una fila de trabajo concreta.
DISPOSITIVO  NINGUNO
RUNTIME      NOT_RUN
```