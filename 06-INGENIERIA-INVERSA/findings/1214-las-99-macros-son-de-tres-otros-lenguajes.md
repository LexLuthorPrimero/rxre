# 1214 — Las 99 macros «discrepantes» son de **tres otros lenguajes**. Y la medida de fondo: **51 de 70** opcodes de `vid.h` no declaran ni un campo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   la pregunta que 1213 dejo abierta:  por que vid.h no separa el bloque
         compartido de 99 macros
NUEVO    la medida de fondo del lenguaje:  la mediana de las 70 ventanas de
         opcode es 1 LINEA
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta

`1211` §4 y `1213` §5 dejaron pendiente por qué `vid.h` no separa un bloque de 99 macros cuyo
nombre no lleva el de su paquete. La respuesta no es que el header esté mal escrito: es que
**esos 99 no son campos de paquete PM3.**

## 1 · La causa estructural: una única ventana no cerrada

De las **70** ventanas de opcode que quedan tras el filtro de 8 bits de `1213`, **una** no está
cerrada por un opcode siguiente: la del **último** opcode del fichero.

```text
  PACKET3_QUERY_STATUS   vid.h:436   ventana [436:517] = 81 lineas
```

Y las ventanas más anchas, con la mediana al lado:

```text
      PACKET3_QUERY_STATUS   [ 436: 517]   81 lineas
      PACKET3_DMA_DATA       [ 271: 334]   63 lineas
      PACKET3_UNMAP_QUEUES   [ 406: 436]   30 lineas
      PACKET3_EVENT_WRITE_EOP[ 237: 266]   29 lineas
      PACKET3_SURFACE_SYNC   [ 201: 225]   24 lineas
      PACKET3_WAIT_REG_MEM    [ 168: 190]   22 lineas
      ...
      mediana de las 70:        1 linea
```

Todo lo que `vid.h` declara después de `vid.h:436` cae dentro de la ventana de `QUERY_STATUS` por
encuadre, y lo que hay ahí, por prefijo:

```text
      SE   12      VCE  11      HEVC   8      RB    8
      PACKET3  6   PKR   6      SC     6
```

**Ni un prefijo es `QUERY_STATUS`.** Eso es la prueba directa de que la ventana no describe un
paquete: describe el final del fichero.

## 2 · Las 99, partidas por familia, con quién las usa

```text
  CON prefijo PACKET3_                        31
      PACKET3_DEST_BASE_0..3_ENA, CB0..CB7_DEST_BASE_ENA, DB_DEST_BASE_ENA,
      PACKET3_TC_VOL_ACTION_ENA, TCL1_ACTION_ENA, SH_KCACHE_ACTION_ENA,
      PACKET3_SEM_SEL_WAIT, PACKET3_BASE_INDEX, ...
      -> plausibles campos de un paquete vecino.  No: el prefijo PACKET3_ vale
         como prefijo de por si,  asi que NO se puede separar mas aqui.

  SIN prefijo PACKET3_                         68,  en siete familias
      SE      12   SE_MAP, SE_MAP_MASK, SE_PAIR_MAP, SE_PAIR_XSEL, ...
      VCE     11   VCE_CMD_NO_OP, VCE_CMD_IB, VCE_CMD_FENCE, VCE_CMD_UPDATE_PTB
      EOP      8   EOP_EXEC, EOP_CACHE_POLICY, EOP_TC_VOL_ACTION_EN, ...
      HEVC     8   HEVC_ENC_CMD_NO_OP, HEVC_ENC_CMD_FENCE, ...
      RB       8   RB_MAP_PKR0, RB_MAP_PKR0_MASK, RB_XSEL2, ...
      PKR      6   PKR_MAP, PKR_MAP_MASK, PKR_XSEL, PKR_YSEL, ...
      SC       6   SC_MAP, SC_MAP_MASK, SC_XSEL, SC_YSEL, ...
      WR / EVENT / DATA / INT / DST / FRAME / CE   9
```

Y quién las usa, medido:

```text
  VCE_CMD_NO_OP         vce_v1_0.c  vce_v3_0.c  vce_v4_0.c     -> comandos de VCE
  HEVC_ENC_CMD_NO_OP    uvd_v6_0.c  uvd_v7_0.c                -> comandos de HEVC
  PKR_MAP               gfx_v8_0.c  (3 usos)
  EOP_TC_VOL_ACTION_EN  0 ficheros .c
```

`PKR_MAP` sí la usa `gfx_v8_0.c`, y el contexto es el que decide:

```c
   3439   RB_XSEL2(1) | PKR_MAP(2) |
   3526   raster_config_se &= ~PKR_MAP_MASK;
   3529   raster_config_se |= PKR_MAP(RASTER_CONFIG_PKR_MAP_3);
```

Están componiendo **`raster_config`**, que es el valor de `PA_SC_RASTER_CONFIG`. Son **campos de un
registro MMIO**, no campos de un paquete. `SC_MAP`, `SE_MAP`, `RB_MAP_*`, `SE_PAIR_*` son del
mismo bloque y del mismo uso.

> Ahí está el error de encuadre que venía arrastrando desde `1201`: **`vid.h` no es solo un header
> de paquetes PM3.** Es el header de paquetes del ASIC, y además trae comandos de VCE/UVD/HEVC y
> definiciones de campos de registro. Contarlo entero como "campos de PM3" mezcla tres lenguajes.

## 3 · La descomposición exacta de las 99

```text
  99  macros cuyo nombre no lleva el de su paquete

     59   de OTROS LENGUAJES,  y no de paquete ninguno
            19  comandos VCE/UVD/HEVC          (vce_v*.c, uvd_v*.c)
            32  campos de registro MMIO        (RB_/PKR_/SC_/SE_*/SE_PAIR_*)
             8  constantes EOP sin uso         (0 ficheros .c)

     31   con prefijo PACKET3_,  plausibles campos de un paquete vecino
      9   sin prefijo pero SI campos de paquete de una ventana vecina
            WR_ONE_ADDR, WR_CONFIRM          -> WRITE_DATA,  probado en 1211
            EVENT_TYPE, EVENT_INDEX          -> EVENT_WRITE / _EOP
            DATA_SEL, INT_SEL, DST_SEL       -> EVENT_WRITE
            FRAME_CMD                        -> FRAME_CONTROL
            CE_PARTITION_BASE                -> SET_BASE
```

**Ninguna de las 99 es evidencia de una frontera rota.** Y dos de ellas —`WR_ONE_ADDR` y
`WR_CONFIRM`— estaban en la lista de discrepantes y su atribución por posición es **correcta**, que
es justo lo que `1211` demostró. "El nombre no lleva el del paquete" y "la atribución es errónea"
son dos cosas distintas, y las confundí al contar.

## 4 · La medida de fondo: el lenguaje que `vid.h` describe

Distribución de las 70 ventanas por anchura:

```text
        1 lineas : 51 paquetes   <- MODA
        3 lineas :  6
        6 lineas :  2
        9 lineas :  1
       11 lineas :  1
       13 lineas :  1
       20 lineas :  1
       22 lineas :  2
       24 lineas :  1
       29 lineas :  1
       30 lineas :  1
       63 lineas :  1
       81 lineas :  1
```

**51 de 70 — el 73%— son una sola línea: un `#define PACKET3_X 0xNN` y nada más.** `vid.h` declara
campos para una minoría de los paquetes que nombra, y los que sí los declara son los de la ruta de
cola y de contexto, no los de la ruta de dibujo.

Eso responde una pregunta que llevaba abierta desde `1200` y `1201`: **no es que el layout no sea
determinable por falta de información en el header. Es que el header no contiene información de
layout para tres cuartas partes de los paquetes.** Son dos limitaciones distintas y se deben
tratar distinto:

```text
  SIN DATOS EN EL HEADER    51 de 70 paquetes.  Determinarlos exige otra fuente
                            (AMDGPU, uvd, uvd_v6_0.c, vce_v*.c, y sobre todo
                            ASUREMENTOS) o escribir el decodificador y validarlo
                            contra el ASIC.
  DECLARADO                 19 de 70.  Es lo que pm4_grupos.py determina.

  NOTA  "otra fuente" no es un cholet:  en el arbol esta cikd.h,  que declara
        PACKET3_SET_SH_REG_END con el MISMO valor que vid.h.  1212 mostro que
        esos valores no los usa nadie.  Un valor coincidente en dos cabeceras
        corrobora el numero,  no el significado.
```

## 5 · Procedimiento

```text
PREGUNTA   ¿por que vid.h no separa un bloque de 99 macros,  y que parte del
            lenguaje de paquetes describe ese header?
FUENTES    vid.h completo (515 lineas)
           vce_v1_0.c  vce_v3_0.c  vce_v4_0.c  uvd_v6_0.c  uvd_v7_0.c
           gfx_v8_0.c:3439, 3526-3531   (el uso de PKR_MAP)
           sid.h  soc15d.h  cikd.h  nvd.h  (las otras copias)
MEDIDO     70 ventanas,  mediana 1 linea,  51 de una sola linea
           1 ventana sin cierre (QUERY_STATUS, 81 lineas)
           99 discrepantes = 59 otros lenguajes + 31 PACKET3_ + 9 sin prefijo
AUTOCORR.  en el recuento anterior llame "discrepantes" a 99 macros y deje
           entender que las 99 eran un problema de atribucion.  No lo son:  40
           de ellas estan correctamente o plausiblemente atribuidas,  y 59 son
           de otros lenguajes.  "El nombre no lleva el del paquete"  y  "la
           atribucion es erronea"  no son lo mismo,  y los conte como si lo
           fueran.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE NO SE RESUELVE
  - por que SET_CONFIG_REG tiene ventana 0xc00 y las otras tres 0x400 (1213)
  - cual de los 31 macros PACKET3_ pertenece a que paquete vecino:  el prefijo
    PACKET3_ no lo dice,  y habria que usar el uso en el driver para separarlos
  - si NOP y CLEAR_STATE tienen estructura:  no hay discriminante
  - que porcentaje de los 51 paquetes desnudos es determinable desde AMDGPU,
    uvd_v6_0.c o vce_v*.c.  ESA es la siguiente fila de trabajo,  y es medible.
```