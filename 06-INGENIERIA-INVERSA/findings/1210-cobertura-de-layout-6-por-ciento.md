# 1210 — Solo el **6%** de los paquetes que el driver GFX8 emite tiene layout conocido, y **2%** por sitios de emisión. Dos de los cuatro ya determinados ni se emiten en GFX8

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=GAP-QUANTIFICATION · SCOPING
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
ESCALA      1207, 1208, 1209
CONVIERTE   "vid.h define 78 paquetes"  en una lista priorizada y medible
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

Un layout determinado de un paquete que el driver nunca emite no sirve para nada, y un paquete
que el driver emite cuyo layout no se conoce es un agujero en cualquier decodificador. La
pregunta es una sola:

```text
¿DE LOS PAQUETES QUE EL DRIVER GFX8 EMITE, CUANTOS TIENEN LAYOUT CONOCIDO?
```

## 1 · Los cuatro, medidos

```text
  paquetes PACKET3 definidos en vid.h            78
  de ellos, con layout declarado por grupos        4      <- solo 4 de 78
  emitidos por gfx_v8_0.c                         30
  emitidos Y con layout                            2      <- MAP_QUEUES, UNMAP_QUEUES

  cobertura por paquete        2 de 30  =   6%
  cobertura por sitio de emision  2 de 67 =   2%
```

Los cuatro con layout, y su atribución exacta por opcode — **no** por prefijo adivinado:

```text
  PACKET3_DMA_DATA      7 grupos   vid.h:280, 309
  PACKET3_MAP_QUEUES    2 grupos   vid.h:393, 400
  PACKET3_UNMAP_QUEUES  7 grupos   vid.h:414, 424, 426, 428, 430, 432, 434
  PACKET3_QUERY_STATUS  3 grupos   vid.h:445, 449, 451

  y ningun grupo contiene macros de otro paquete:  comprobado los 19
```

## 2 · Y el dato incómodo: dos de los cuatro no se emiten en GFX8

```text
  PACKET3_DMA_DATA      lo emite solo  gfx_v9_0.c
  PACKET3_QUERY_STATUS  lo emiten      gfx_v9_0.c  gfx_v10_0.c  gfx_v11_0.c
                                       gfx_v12_0.c  gfx_v12_1.c  gfx_v9_4_3.c
  PACKET3_MAP_QUEUES    lo emite  gfx_v8_0.c    1 uso
  PACKET3_UNMAP_QUEUES  lo emite  gfx_v8_0.c    1 uso
```

**GFX8 no emite ni `DMA_DATA` ni `QUERY_STATUS`.** De los dos paquetes que `1208` determinó por
completo, uno no existe en esta generación. `1208` no está equivocado —el
layout es correcto y el header es coherente consigo mismo—, pero **uno de sus dos objetos está
fuera del alcance de esta placa**, y eso no se dijo entonces.

> Que `1208` y `1209` determinan y cierran el layout. Lo que no cierran, y se cierra aquí, es
> para qué sirve:  un paquete correcto y bien trazado, de un ASIC que no es el nuestro.

## 3 · Los 28 huecos, por uso real

Ordenados por número de emisiones en `gfx_v8_0.c`, que es el orden en que un decodificador los
encontraría:

```text
   10  PACKET3_WRITE_DATA              <- el caballo de batalla de la ruta de graficos
    6  PACKET3_SET_SH_REG
    6  PACKET3_SET_SH_REG_START
    5  PACKET3_EVENT_WRITE
    3  PACKET3_NOP
    3  PACKET3_DISPATCH_DIRECT
    3  PACKET3_WAIT_REG_MEM
    3  PACKET3_SET_CONTEXT_REG
    3  PACKET3_SET_CONTEXT_REG_START
    2  PACKET3_CONTEXT_CONTROL
    2  PACKET3_INDIRECT_BUFFER
    2  PACKET3_EVENT_WRITE_EOP
    2  PACKET3_PREAMBLE_CNTL
    1  PACKET3_SET_BASE          PACKET3_CLEAR_STATE        PACKET3_COND_EXEC
    1  PACKET3_INDIRECT_BUFFER_CONST   PACKET3_COPY_DATA     PACKET3_PFP_SYNC_ME
    1  PACKET3_SURFACE_SYNC     PACKET3_RELEASE_MEM       PACKET3_ACQUIRE_MEM
    1  PACKET3_SET_CONFIG_REG   PACKET3_SET_CONFIG_REG_START
    1  PACKET3_SET_UCONFIG_REG  PACKET3_SET_UCONFIG_REG_START
    1  PACKET3_SWITCH_BUFFER    PACKET3_SET_RESOURCES
```

Los cinco primeros concentran 30 de las 67 emisiones. **`WRITE_DATA` solo son 10**, y no tiene
ningún grupo de macros en `vid.h`. Es el primero que habría que determinar para que un
decodificador de la ruta de gráficos valiera algo, y es el mayor agujero de todos.

## 4 · El fallo mío, y por qué esta tabla casi no existe

La primera versión de este cruce dio **cero paquetes emitidos y `agrupación` sobre un nombre
inventado**. Dos defectos, ambos de la clase que ya había grabado seis veces:

```text
  a)  OPC = r"...\s*$"  compilado SIN re.M
      -> $  ancla al FIN DEL CADENA,  no al fin de la linea
      -> 0 opcodes donde hay 78

  b)  la pertenencia de un grupo la saqué de un prefijo adivinado:
        re.sub(r"_[A-Z0-9]+$", "", "PACKET3_SET_SH_REG_START") = "PACKET3_SET_SH_REG"
      eso fusiona SET_SH_REG con SET_SH_REG_START y deforma el recuento entero
```

(a) es la **tercera** vez que me falta `re.M`. Las dos anteriores ya estaban en mi lista de
errores, con otros dos regex. El patrón es siempre el mismo: **una bandera de una línea que se
escribe una vez y se olvida**.

> Lo de (a) es más traicionero de lo que parece. `\s*` antes de `$` se come el resto del
> fichero, así que el regex no falla con error: devuelve una lista **más corta**. Sin `re.M` da
> 0; pero con cualquier variante que funcione en un fichero de una línea y falle en otro, el
> resultado es un número verosímil.

(b) es peor: no es un fallo de regex, es un **supuesto de nomenclatura**. Que un macro se llame
`X_START` no significa que pertenezca a otro paquete. La atribución correcta es el **opcode más
reciente**, que es lo que hace ahora `pm4_grupos.py`, y hay un vector que exige que ningún
grupo contenga macros de otro paquete.

## 5 · Qué es y qué no es esta cifra

```text
  ESTADO  OBSERVATION sobre el ARBOL,  no sobre el hardware.
          Que gfx_v8_0.c escriba PACKET3_WRITE_DATA 10 veces es un hecho de
          fuente.  Que la RX550 lo ejecute 10 veces es de runtime,  y no se
          ha medido.  RUNTIME=NOT_RUN.

  "CON layout"  significa lo que 1209 define:  los intervalos salen de los
                desplazamientos del primario y,  si hay enumeracion,  el
                ancho coincide con el minimo.  No hay extraccion en ningun
                sitio del arbol.

  LA LISTA NO ES TRABAJO PENDIENTE TODAVIA.  Es el hueco medido.  Que un
  paquete se pueda determinar depende de si vid.h declara sus dwords por
  comentario:  COPY_DATA  tiene enumeraciones en vid.h  y no tiene grupo,  y
  eso es una cosa distinta a no saber nada de el.
```

## 6 · Procedimiento

```text
PREGUNTA   ¿de los paquetes que emite el driver GFX8,  cuantos tienen layout?
HERRAMIENTA  tools/pm4_grupos.py  (ya existente)  +  el cruce de arriba
FUENTES    vid.h            78 opcodes,  14 comentarios de dword
           gfx_v8_0.c       los puntos de emision
           gfx_v9_0.c, gfx_v10_0.c, gfx_v11_0.c, gfx_v12_0.c, gfx_v12_1.c,
           gfx_v9_4_3.c     quien emite DMA_DATA y QUERY_STATUS
MEDIDO     78 definidos / 4 con layout / 30 emitidos / 2 ambos
           6% por paquete,  2% por sitio de emision
AUTOCORR.  dos fallos mios:  falta de re.M en el regex de opcodes  (0 donde
           habia 78),  y pertenencia de grupo por prefijo adivinado en vez de
           por opcode.  Los doscorregieron corregidos antes de escribir.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```