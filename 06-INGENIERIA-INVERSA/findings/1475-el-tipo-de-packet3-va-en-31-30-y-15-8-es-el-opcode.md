# 1475 — El layout PACKET3, corregido: el **tipo** va en `[31:30]` y `[15:8]` es el **opcode**. Un oráculo independiente dentro del propio corpus lo declara, y yo llevaba días diciendo lo contrario

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

ARTEFACTO=rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/
  amdgpu/cikd.h:214-233          el driver: macros de construccion y lectura
  amdkfd/kfd_pm4_headers.h:30-40 el MISMO layout, con bitfields, otro fichero

CORRIGE=1412 y mi resumen de 1459.  Los dos decian "tipo en [15:8], cuenta en
        [29:16]".  La cuenta es correcta.  EL TIPO NO: esta en [31:30].
ESTADO=PROVEN.  Dos definiciones independientes en el corpus coinciden.
NOVEDAD=un oráculo de la MISMA ASIC que no es el driver, para el PM4.  Es el
        segundo caso de la familia que 1459 abrió (1459: umr; 1475: kfd).
```

## 0 · EL ERROR, DICHO PRIMERO

Mi resumen, repetido en `1412` y en `1459`:

```text
  "PACKET3: tipo en bits [15:8], cuenta en [29:16]"
```

La segunda mitad es correcta. La primera es un error, y viene de una lectura
rápida: `CP_PACKET3_GET_OPCODE(h) = ((h) >> 8) & 0xFF` me hizo leer "el byte de
[15:8] es el tipo del paquete". **No: es el opcode**, y el *tipo* es otro campo,
en `[31:30]`, con el valor 3.

La distinción no es cosmética. `PACKET3_NOP` vale `0x10` y `PACKET3_SET_BASE`
vale `0x11`: son **opcodes**, no tipos. Hay un solo tipo 3. Si alguien hubiera
usado mi frase para construir un decodificador, habría tratado 256 "tipos" como
si fueran el campo que decide la longitud del paquete.

## 1 · LAS DOS FUENTES, LEÍDAS ENTERAS

**Fuente A — el driver, `amdgpu/cikd.h:214-233`:**

```c
#define  PACKET_TYPE3      3
#define  CP_PACKET_GET_TYPE(h)  (((h) >> 30) & 3)
#define  CP_PACKET_GET_COUNT(h) (((h) >> 16) & 0x3FFF)
#define  CP_PACKET3_GET_OPCODE(h) (((h) >> 8) & 0xFF)

#define  PACKET3(op, n)   ((PACKET_TYPE3 << 30) |      /*  3 en [31:30]  */
                          (((op) & 0xFF) << 8) |       /* op en [15:8]   */
                          ((n) & 0x3FFF) << 16)        /*  n en [29:16]  */

#define  PACKET3_COMPUTE(op, n) (PACKET3(op, n) | 1 << 1)   /* bit 1 */
```

**Fuente B — otro fichero, mismos bits, con bitfields.**
`amdkfd/kfd_pm4_headers.h:30-40`:

```c
union PM4_MES_TYPE_3_HEADER {
        struct {
                uint32_t reserved1:8;
                uint32_t opcode:8;    /* IT opcode */
                uint32_t count:14;    /* number of DWORDs - 1 in the information body */
                uint32_t type:2;      /* packet identifier. It should be 3 for type 3 */
        };
        uint32_t u32all;
};
```

Los bitfields del C se asignan de least a most significant bit, así que:

```text
  reserved1    [7:0]
  opcode       [15:8]     <-- lo que yo llamaba "tipo"
  count        [29:16]
  type         [31:30]
```

**Coinciden los cuatro campos, el ancho y el signo.** Dos ficheros distintos,
misma información, y uno de los dos no es el driver que produce el IB.

## 2 · EL LAYOUT, Y UNA RESERVA SOBRE EL `count`

```text
  bit  31 30 | 29            16 | 15       8 | 7      1 | 0
      type   |     count (14)    |   opcode    |  reservado | COMPUTE

  type    = 3        (PACKET_TYPE3 << 30)
  count   = n        (14 bits, mascara 0x3FFF)
  opcode = op       (8 bits)
  bit 0            = reservado
  bit 1            = 1 si es un paquete de COMPUTE
```

**La reserva, porque es el sitio donde un decodificador propio se equivoca:**
las dos fuentes dicen cosas distintas sobre qué cuenta `count`, y no lo reconcile.

```text
  cikd.h                 PACKET3(op, n) escribe ((n) & 0x3FFF) << 16
                         -> n es el numero de dwords tal cual se pasa

  kfd_pm4_headers.h      "number of DWORDs - 1 in the information body"
                         -> el campo es n_menos_1

  y el nombre del macro lo respalda:  CP_PACKET_GET_COUNT, no CP_PACKET_GET_N
```

`1441`/`1442` trataron el count como aritmética directa del patcher, y `1462` ya
dice que la longitud de un paquete es *count + 2*. **Con lo de aquí, "count + 2"
solo es correcto si `count` es el valor crudo del campo, no el decrementado.**
Lo dejo declarado como `PARTIAL`, no como error de nadie, y lo escribo porque un
decodificador propio tiene que elegir una de las dos lecturas y **no puede
cambiarlas según convenga**.

## 3 · POR QUÉ ESTE ORACLE NO LO HABIA VISTO, Y POR QUÉ IMPORTA

`1421` §6 mide que las cabeceras de macros PM4 del corpus están vaciadas a 2
defines, y que `si.h`/`vi.h` son stubs. Es cierto. **Pero la afirmación
generalizada —"el corpus no tiene el layout"— era más fuerte que el alcance de
la medición**, y por eso lo di por cerrado.

La lección es la de siempre y ya la he escrito seis veces: **medí lo que
busqué, no busqué lo que hay.** Busqué "definición de PACKET3" y encontré la del
driver. No busqué "otra declaración del layout".

Lo que esto abre, y es lo importante:

```text
  HAY UN SEGUNDO ORACLE DE PM4 EN EL CORPUS, y no es el driver.
  Es amdkfd, que es otro consumidor de la misma ASIC.

  Y ESO es una clase general, no un caso:
      1459  oraculo de REGISTROS fuera del corpus  -> /usr/share/umr/
      1475  oraculo de PM4 DENTRO del corpus      -> amdkfd/kfd_pm4_headers.h

  El segundo es mejor que el primero para una razon concreta:
  el primero hay que confiar en que su numeracion coincide con la del driver,
  y por eso 1471 tuvo que comprobarlo.  El segundo comparte struct, offset y
  compilador con el codigo que escribe, asi que la coincidencia de bits no
  necesita suposicion: es la MISMA declaracion en otro consumidor.
```

Lo que **no** hago, y es deliberado: no trato `kfd_pm4_headers.h` como
autoridad. `amdkfd` es un driver distinto, con sus propios fines, y su struct
`pm4_map_process` es la vista de KFD, no la del ring de gfx. Sirve para
**contrastar el layout del encabezado**, que es lo que he hecho. Para la
semántica de un opcode, sigue mandando `cikd.h` más lo que haya observado en el
IB real.

## 4 · ESTADO DE ESTA FRONTERA

```text
PROVEN           layout PACKET3: type[31:30]=3, count[29:16], opcode[15:8],
                 bit1=COMPUTE.  Dos definiciones independientes coinciden.
REFUTADO         mi frase "tipo en [15:8]" de 1412 y 1459.  Era el opcode.
PARTIAL          el significado de count: cikd.h lo escribe crudo, kfd lo
                 documenta como n-1.  No reconciliado.  Afecta a la longitud
                 total del paquete y por tanto a mi decodificador de IB.
CIERRA           la mitad de la ambiguedad de 1462 sobre la longitud.
ABRE             la otra mitad: cual de las dos lecturas produce los 2051
                 dwords de revkit/capturas/amdgpu_ring_gfx.txt.  Eso SI es
                 decidible con el IB que ya tengo, y es el siguiente paso.
```

## 5 · LA NORMA QUE ESTE HALLAZGO ESTABLECE

```text
  AL AFIRMAR UN LAYOUT DE BIT EN ESTE PROYECTO

    1. busca una segunda declaracion en el corpus, no solo la del driver
       que lo escribe.  amdkfd declara el mismo PACKET3.
    2. si las dos difieren en ALGO, no promedies: declara PARTIAL y di cual
       es la que tu codigo asume y por que.
    3. distingue TIPO de OPCODE.  En PACKET3 el tipo es un campo de 2 bits y
       vale siempre 3.  Hay 256 opcodes y un tipo.  Confundirlos produce un
       decodificador que parece funcionar y cuenta mal.
```

## 6 · LO QUE SIGUE, Y ES LO QUE MANDO

`PARTIAL` de §2 es decidible **con el IB real que ya capturé**, sin hardware ni
permisos. `1462` dice "la longitud es count + 2". Si al trocear los 8 bloques de
256 dwords con `count + 2` las longitudes cuadran y con `count + 1` no, la
ambiguedad esta resuelta y `kfd_pm4_headers.h` queda como la fuente equivocada
para este campo. Si las dos cuadran, entonces el campo es ambiguo de verdad y
hay que decirlo.

Eso es `§48 DISCRIMINANT FIRST` aplicado a un `PARTIAL` que yo mismo produje, con
un discriminante que ya tengo en disco.
