# 1218 — **Sí hay máscara de GFX8**, y no en un header de paquetes: `CP_DMA_ME_COMMAND` es la misma palabra que el `COMMAND` de `DMA_DATA`, y coincide bit a bit. `1215` y `1216` estaban equivocados

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR · METHOD-VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el item "anchuras CP_DMA / DMA_DATA"  que yo mismo deje anotado como
         "sin mirar".  Uno de los dos no era un paquete.
CORRIGE  1215 y 1216:  "no hay mascara de GFX8 en el arbol"  es FALSO
VALIDA   el metodo por desplazamiento con mascaras NATIVAS de GFX8,  que era
         lo que 1216 declaro imposible
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta, y el error de categoría que la cerraba mal

Tenía anotado desde hacía rato:

```text
  "anchuras CP_DMA / DMA_DATA — sin mirar"
```

Lo puse en la misma lista como si las dos fueran paquetes con campos que determinar. **`CP_DMA`
no es un paquete.** Es un bloque de registros del CP, y no lo emite ningún `.c` del driver como
`PACKET3_*`. La pregunta estaba mal formulada, y por eso no se cerraba con una lectura.

```text
  PACKET3_CP_DMA en vid.h        0 apariciones
  PACKET3_CP_DMA en los .c       0 apariciones
  CP_DMA en el arbol del kernel   3802 apariciones,  todas de REGISTRO
```

## 1 · Los 21 campos, con su máscara

`asic_reg/gca/gfx_8_0_sh_mask.h`. Los registros:

```text
  mmCP_DMA_ME_CONTROL       0xc084     mmCP_DMA_PFP_SRC_ADDR      0xc085
  mmCP_DMA_ME_COMMAND       0xc078     mmCP_DMA_PFP_SRC_ADDR_HI   0xc086
  mmCP_DMA_ME_SRC_ADDR      0xc080     mmCP_DMA_PFP_DST_ADDR      0xc087
  mmCP_DMA_ME_SRC_ADDR_HI   0xc081     mmCP_DMA_PFP_DST_ADDR_HI   0xc088
  mmCP_DMA_ME_DST_ADDR      0xc082     mmCP_DMA_PFP_CONTROL       0xc089
  mmCP_DMA_ME_DST_ADDR_HI   0xc083     mmCP_DMA_CNTL              0xc08a
```

Y sus campos, **con la comprobación de coherencia interna del header**:

```text
  CP_DMA_ME_COMMAND
    BYTE_COUNT     0x001fffff  bits [20:0 ] = 21 bits   SHIFT  0   coincide
    DIS_WC         0x00200000  bit  [21:21] =  1 bit    SHIFT 21   coincide
    SRC_SWAP       0x00c00000  bits [23:22] =  2 bits   SHIFT 22   coincide
    DST_SWAP       0x03000000  bits [25:24] =  2 bits   SHIFT 24   coincide
    SAS            0x04000000  bit  [26:26] =  1 bit    SHIFT 26   coincide
    DAS            0x08000000  bit  [27:27] =  1 bit    SHIFT 27   coincide
    SAIC           0x10000000  bit  [28:28] =  1 bit    SHIFT 28   coincide
    DAIC           0x20000000  bit  [29:29] =  1 bit    SHIFT 29   coincide
    RAW_WAIT       0x40000000  bit  [30:30] =  1 bit    SHIFT 30   coincide
    31/32 cubiertos,  hueco: bit [31]

  CP_DMA_ME_CONTROL
    SRC_MTYPE          0x00000c00  bits [11:10] =  2 bits   SHIFT 10   coincide
    SRC_ATC            0x00001000  bit  [12:12] =  1 bit    SHIFT 12   coincide
    SRC_CACHE_POLICY   0x00002000  bit  [13:13] =  1 bit    SHIFT 13   coincide
    DST_SELECT         0x00300000  bits [21:20] =  2 bits   SHIFT 20   coincide
    DST_MTYPE          0x00c00000  bits [23:22] =  2 bits   SHIFT 22   coincide
    DST_ATC            0x01000000  bit  [24:24] =  1 bit    SHIFT 24   coincide
    DST_CACHE_POLICY   0x02000000  bit  [25:25] =  1 bit    SHIFT 25   coincide
    SRC_SELECT         0x60000000  bits [30:29] =  2 bits   SHIFT 29   coincide
    12/32 cubiertos,  huecos [0:9] [14:19] [26:28] [31:31]

  CP_DMA_ME_SRC_ADDR      0xffffffff  [31:0] = 32 bits
  CP_DMA_ME_SRC_ADDR_HI   0x0000ffff  [15:0] = 16 bits
  CP_DMA_ME_DST_ADDR      0xffffffff  [31:0] = 32 bits
  CP_DMA_ME_DST_ADDR_HI   0x0000ffff  [15:0] = 16 bits

  SHIFT == bit mas bajo de la mascara:  21 de 21
```

**El header es internamente coherente en los 21 campos.** En AMD la máscara viene **ya
desplazada**, así que `MASK` y `SHIFT` son el mismo dato escrito dos veces; que coincidan en 21 de
21 significa que el bloque está bien generado.

## 2 · El cruce: `CP_DMA_ME_COMMAND` ES el `COMMAND` de `DMA_DATA`

Tres declaraciones independientes de la misma palabra de 32 bits:

```text
  A.  la PROSA de vid.h:278,  sin mascaras
        7. COMMAND [30:21] | BYTE_COUNT [20:0]

  B.  los MACROS de paquete de vid.h:309-334,  sin mascaras  (de 1209)
        DIS_WC = 1<<21   SRC_SWAP <<22   DST_SWAP <<24
        SAS = 1<<26     DAS = 1<<27     SAIC = 1<<28
        DAIC = 1<<29    RAW_WAIT = 1<<30

  C.  las MASCARAS de gfx_8_0_sh_mask.h,  con posicion y anchura
        BYTE_COUNT [20:0]=21   DIS_WC [21]   SRC_SWAP [23:22]=2
        DST_SWAP [25:24]=2     SAS [26]     DAS [27]       SAIC [28]
        DAIC [29]              RAW_WAIT [30]   hueco [31]
```

**Coinciden las tres en los 32 bits, campo por campo, incluido `RAW_WAIT` en el bit 30** — que en
mi grep anterior había quedado cortado y por eso `1209` no lo mencionó. Y el hueco del registro,
bit `[31]`, es exactamente lo que implica la prosa: si `COMMAND` es `[30:21]` y `BYTE_COUNT` es
`[20:0]`, el bit 31 no pertenece a nadie.

Eso identifica `CP_DMA_ME_COMMAND` con el dword 7 de `DMA_DATA` como
**PROVEN-dentro-del-alcance-medido**, no como hipótesis: nueve campos, nueve coincidencias de
posición y de ancho, más el hueco.

## 3 · Y el `CONTROL`: cuatro campos compartidos, cuatro posiciones idénticas

```text
  campo                    vid.h (desplazamiento)   registro (mascara)   ancho
  ---------------------------------------------------------------------------
  SRC_CACHE_POLICY         << 13                    bits [13]           2 vs 1
  DST_SEL / DST_SELECT     << 20                    bits [21:20]         5 vs 2
  DST_CACHE_POLICY         << 25                    bits [25]           5 vs 1
  SRC_SEL  / SRC_SELECT    << 29                    bits [30:29]         2 vs 2  EXACTO
```

**Las cuatro posiciones de inicio coinciden exactamente.** Y el registro nombra dos campos que el
header de paquete no declara: `SRC_MTYPE [11:10]` y `DST_MTYPE [23:22]`, ambos de 2 bits, más
`SRC_ATC` y `DST_ATC` de 1 bit.

## 4 · La validación del método, por fin sobre GFX8

```text
                         1216 (GFX9/GFX10)     1218 (GFX8 nativo)
  comparables                     4                       6
  subestima                       0                       0
  exactas                         1                       3
  sobrestima                      3                       3
  origen de las mascaras        ajenas (GFX9/GFX10)   nativas de GFX8
```

**Cero subestimaciones, sobre la mascara del propio ASIC.** La invariante de `1216` queda
confirmada en el ASIC que nos importa, y con el doble de comparables.

Y el reparto 3/6 exacto es el dato honesto: **la mitad de las veces el desplazamiento acierta el
ancho y la otra mitad lo sobrestima por el hueco hasta el siguiente campo.** Eso es lo que mide, y
`ENGINE_SEL` de `WRITE_DATA` —2 bits por desplazamiento, sin máscara que lo confirme— sigue siendo
cota, como dije en `1215`.

## 5 · Lo que se corrige, sin suavizar

```text
  1215  "no hay lado de extraccion en el arbol"          ->  hay 9196 campos con
        mascara en gfx_8_0_sh_mask.h,  y los del paquete
        estan ahi.  Lo que es cierto:  vid.h tiene 0.

  1216  "falta una mascara de GFX8"                     ->  no falta.  Esta aqui:
                                                        CP_DMA_ME_COMMAND y
                                                        CP_DMA_ME_CONTROL

  1216  "no se puede validar el metodo con una mascara
         de GFX8"                                       ->  se puede,  y esta hecho:
                                                        §4
```

**El error de fondo fue dónde busqué.** Busqué máscaras en las cabeceras de **paquetes**, porque el
contexto era el layout de paquetes, y no pensé que el mismo hardware declara esos campos otra
vez en el header de **registros**, que es donde AMD los pone con anchura. La conclusión «no hay
que buscar más» salió de un alcance que yo mismo había elegido, y no lo declaré como tal.

## 6 · Procedimiento

```text
PREGUNTA   ¿anchuras de CP_DMA / DMA_DATA?
HALLAZGO   CP_DMA no es un paquete.  Es un bloque de registros:  3802 apariciones
           en el arbol  y 0 como PACKET3_*  y 0 emisiones en .c
MEDIDO     21 campos con mascara en CP_DMA_ME_*  (9 COMMAND + 8 CONTROL + 4 addr)
           SHIFT == bit mas bajo de la mascara:  21 de 21
           COMMAND de DMA_DATA:  prosa == macros == mascaras,  los 32 bits
           CONTROL de DMA_DATA:  4 de 4 posiciones de inicio identicas
           validacion del desplazamiento:  6 comparables, 0 subestima, 3 exactas,
           3 sobrestima
LO QUE NO SE CIERRA
  - los registros de DIRECCION no cuadran con la prosa:  la prosa dice
    6. DST_ADDR_HI [7:0] = 8 bits  y  el registro dice 16 bits  [15:0].
    NO lo trato como contradiccion:  el registro sostiene una direccion
    absoluta y el packet un offset relativo,  y eso son dos objetos.  Que sea
    asi es NOT_DETERMINED,  no medido.
  - SRC_MTYPE / DST_MTYPE / SRC_ATC / DST_ATC:  el registro los declara y el
    header de paquete no.  No se sabe si el hardware los acepta por el packet.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
AUTOCORR.  cuatro fallos de script en esta medicion,  todos mios y todos de
   parseo:  (a) SHIFT con regex codicioso que se comia el nombre del campo;
           (b) anadir el SHIFT a una mascara que ya viene desplazada,  y por eso
               salian campos de 22 bits donde caben 1;  (c) el parser de MASK
               nunca disparo porque la linea no termina en "_MASK" sino en el
               valor hex,  y el guard dio "coincide: True"  SOBRE CERO CAMPOS;
           (d) falta quitar "_MASK" en una rama y no en la otra.
   El (c) es el importante:  un guard que pasa porque no compro nada.  Es la
   misma clase de 1210/1209,  y la razon por la que el guard de 1209 obliga a
   contrastar el recuento de vectores ejecutados contra un declarado.
```