# 1213 — **«78 paquetes» eran 70.** Ocho de ellos no pueden ser opcodes, y contaminaban las ventanas de `1211`. La cobertura real es **42%**, no 20%

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR · INSTRUMENT-FIX · CORRECTION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/pm4_grupos.py  (filtro de opcodes de 8 bits)
CORRIGE   1210 (78 paquetes, 30 emitidos, 20% de cobertura)
           1211 (19 sin lista plana — la lista de §6 no cuadra)
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · El error, en una frase

Conté como opcode cualquier línea de la forma `#define PACKET3_X <hex>`. **Esa forma la
cumplen tanto un opcode como las constantes de reubicación `*_START` y `*_END`, y ocho de ellas
tienen un valor que no cabe en el campo de opcode.** Mi propio árbol de ventanas las daba por
paquetes, y partían en sitios donde no hay paquete.

## 1 · El filtro que faltaba, y que ya estaba escrito en el árbol

`vid.h:105-107`:

```c
#define PACKET3(op, n)	((PACKET_TYPE3 << 30) |				\
			 (((op) & 0xFF) << 8) |				\
			 ((n) & 0x3FFF) << 16)
```

El opcode se enmascara a **8 bits**. Un valor mayor que `0xFF` no puede viajar como opcode: la
expresión lo tritura. No es una regla que yo imponga; es la que el header escribe.

## 2 · El censo, con y sin el filtro

```text
  lineas con la forma '#define PACKET3_X <hex>'      78
  con valor <= 0xFF   pueden ser opcode               70
  con valor >  0xFF   NO PUEDEN ser opcode              8
```

Las ocho, y son las cuatro familias de reubicación completas:

```text
  vid.h:341   PACKET3_SET_CONFIG_REG_START     0x00002000
  vid.h:342   PACKET3_SET_CONFIG_REG_END       0x00002c00
  vid.h:344   PACKET3_SET_CONTEXT_REG_START    0x0000a000
  vid.h:345   PACKET3_SET_CONTEXT_REG_END      0x0000a400
  vid.h:348   PACKET3_SET_SH_REG_START         0x00002c00
  vid.h:349   PACKET3_SET_SH_REG_END           0x00003000
  vid.h:353   PACKET3_SET_UCONFIG_REG_START    0x0000c000
  vid.h:354   PACKET3_SET_UCONFIG_REG_END      0x0000c400
```

Las cuatro ventanas, y son de la misma magnitud:

```text
  SET_SH_REG       0x02c00 -> 0x03000   = 0x400 bytes = 256 dwords
  SET_CONTEXT_REG  0x0a000 -> 0x0a400   = 0x400 bytes = 256 dwords
  SET_UCONFIG_REG  0x0c000 -> 0x0c400   = 0x400 bytes = 256 dwords
  SET_CONFIG_REG   0x02000 -> 0x02c00   = 0xc00 bytes = 768 dwords   <- la que se sale
```

Tres de cuatro son exactamente `0x400`. La cuarta no, y queda anotada abajo sin explicar.

## 3 · Lo que estaba contaminado, y cómo se ve

`1212` demostró que `_START`/`_END` son bases de reubicación por el argumento del `& 0xFF`. Lo
que **no** hice entonces fue aplicarlo al instrumento. `ventanas()` y `plano()` seguían
tratándolas como paquetes.

La prueba de que contaminaban, y el efecto del arreglo en la misma cifra:

```text
  ANTES    PACKET3_SET_SH_REG       ventana (347, 348)
  AHORA    PACKET3_SET_SH_REG       ventana (347, 350)
```

Antes, `vid.h:348` y `:349` —las dos constantes— cerraban el paquete y quedaban fuera. Ahora no lo
cierran, y **la ventana se abre para incluirlas, que es lo correcto: le pertenecen.** El arreglo
no ajusta un número, cambia la atribución en la dirección buena.

## 4 · Las cifras corregidas, y las tres que hay que rehacer

```text
                          1210 / 1211        1213
                          publicaron         medido
  opcodes PACKET3 en vid.h     78                 70
  emitidos por gfx_v8_0.c      30                 26
  con layout, por paquete    6 de 30 = 20%    11 de 26 = 42%
  con layout, por sitio      18 de 67 = 26%    29 de 56 = 51%
  sin lista plana              24                 15
```

**26 y no 30** porque cuatro de los que contaba como paquetes emitidos son las constantes
`SET_SH_REG_START`, `SET_CONTEXT_REG_START`, `SET_CONFIG_REG_START` y
`SET_UCONFIG_REG_START`, que el driver **usa**, y por eso salían como "paquetes emitidos por
`gfx_v8_0.c`". No son paquetes: son las bases que se le restan a un offset.

Y **15 y no 24** porque cinco de los que `1211` §6 listó como sin macros sí las tienen, y mi filtro
las descartaba otra vez:

```text
  EVENT_WRITE        2 macros    EVENT_WRITE_EOP   11 macros
  PREAMBLE_CNTL      2 macros    SET_BASE           1 macro
  SURFACE_SYNC      23 macros
```

Los cinco tienen sus macros, y sus ventanas están acotadas. Los perdí por volver a filtrar por
nombre —`EVENT_WRITE` escribe `EVENT_TYPE`, `EVENT_INDEX`, `DST_SEL`, `DATA_SEL`, `INT_SEL`, y
ninguno empieza por `EVENT_WRITE`— que es **exactamente** el error que `1211` ya había corregido
y que reintroduje en el script de clasificación. Segunda vez en la misma sesión, con el patrón
literal idéntico.

## 5 · Lo que queda sin lista plana, y su clase

Los 15, con la ventana que les corresponde:

```text
   6  PACKET3_SET_SH_REG         (347, 350)    SIN ESTRUCTURA,  probado en 1212
   3  PACKET3_NOP                (112, 113)
   3  PACKET3_DISPATCH_DIRECT    (118, 119)
   3  PACKET3_SET_CONTEXT_REG    (343, 346)    SIN ESTRUCTURA,  mismo patron que 1212
   2  PACKET3_CONTEXT_CONTROL    (131, 132)
   1  PACKET3_CLEAR_STATE        (116, 117)
   1  PACKET3_COND_EXEC          (125, 126)
   1  PACKET3_INDIRECT_BUFFER_CONST (137, 138)
   1  PACKET3_COPY_DATA          (199, 200)
   1  PACKET3_PFP_SYNC_ME        (200, 201)
   1  PACKET3_RELEASE_MEM        (267, 268)    POR DETERMINAR,  ver abajo
   1  PACKET3_ACQUIRE_MEM        (334, 335)    POR DETERMINAR,  ver abajo
   1  PACKET3_SET_CONFIG_REG     (340, 343)    SIN ESTRUCTURA,  mismo patron que 1212
   1  PACKET3_SET_UCONFIG_REG    (352, 355)    SIN ESTRUCTURA,  mismo patron que 1212
   1  PACKET3_SWITCH_BUFFER      (364, 365)
```

Cuatro son de la familia de reubicación que `1212` ya probó: el driver escribe
`mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START` y
`mmSCRATCH_REG0 - PACKET3_SET_UCONFIG_REG_START`, o sea un índice opaco. **SIN ESTRUCTURA.**

Dos —`RELEASE_MEM` y `ACQUIRE_MEM`— son un caso aparte que **no clasifico**: el driver sí compone
su payload con macros de campo,

```text
  gfx_v8_0.c  ACQUIRE_MEM   amdgpu_ring_write(ring, PACKET3_TCL1_ACTION_ENA | ...)
  gfx_v8_0.c  RELEASE_MEM   amdgpu_ring_write(ring, (EOP_TCL1_ACTION_EN | ...)
```

pero esas macros (`PACKET3_TCL1_ACTION_ENA`, `EOP_TC_VOL_ACTION_EN`, `PKR_MAP`, `SE_PAIR_YSEL_MASK`,
y 99 más) están declaradas **fuera** de la ventana de su paquete, en un bloque compartido que
`vid.h` no separa. Son las 99 macros discrepantes de `1211`. Determinables, pero no por la vía de
la ventana, y no tengo una via mejor probada todavia.

```text
  SIN ESTRUCTURA,  con el patron de 1212 probado   4
  POR DETERMINAR,  bloque compartido sin aislar      2
  clase NO DETERMINADA por este metodo               9
```

Nueve —los de 1 a 3 usos— no los clasifico porque no tengo un discriminante para separarlos, y
un `SIN ESTRUCTURA` sin probar sería repetir el error de `1210`.

## 6 · Procedimiento

```text
PREGUNTA   ¿de qué clase es cada paquete emitido sin lista de campos, y el
            censo de opcodes de 1210 es correcto?
FUENTES    vid.h:105-107 (la mascara),  vid.h:341-354 (las ocho)
           asic_reg/gca/gfx_8_0_d.h  (bases de bloque)
           gfx_v8_0.c  (los puntos de emision)
MEDIDO     78 formas / 70 opcodes / 8 imposibles
           ventanas despues del arreglo: SET_SH_REG (347, 350)
           cobertura 11 de 26 paquetes = 42%,  29 de 56 sitios = 51%
MUTACION   verificada, no afirmada.  Quitando el filtro de 8 bits:
             FALLA las ventanas ya no tienen entradas de mas   78
             FALLA SET_SH_REG ... se abre a [347:350]  (347, 348)
             FALLA PACKET3_SET_SH_REG_START ya NO es una ventana  esta
             SELFTEST: 50 de 53
           restaurado: SELFTEST OK: 53 vectores
AUTOCORR.  dos errores mios,  ambos de la clase "filtrar por nombre en vez
           de por posicion":  uno en 1211 §6 (5 paquetes perdidos)  y otro en
           el script de clasificacion de este hallazgo (los mismos 5).  La
           segunda vez con patron literal identico en la misma sesion.
LO QUE NO SE RESUELVE
           por que SET_CONFIG_REG tiene ventana 0xc00 y las otras tres 0x400
           por que vid.h no separa el bloque compartido de 99 macros
           si NOP y CLEAR_STATE tienen estructura o no:  no hay discriminante
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```