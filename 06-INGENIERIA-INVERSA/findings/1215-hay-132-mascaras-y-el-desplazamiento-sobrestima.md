# 1215 — `1201` estaba equivocado: hay **132 máscaras de campo** en el árbol. Y al cruzar los métodos, el desplazamiento **sobrestima siempre**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR · METHOD-VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CORRIGE   1201:  "0 anchuras de campo PM4 declaradas en todo el arbol"  es FALSO
           1207 / 1209 / 1211:  el desplazamiento es una COTA POR ARRIBA,  y
           hay pruebas de que sobrestima  —  no es el ancho
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que se rompe

`1201` barrió **69 091 ficheros** y concluded que no existe en el árbol ni una anchura de campo
PM4 declarada, con un patrón que se autovalidaba contra un positivo. Lo que `1209` dio por establecido fue: no hay lado
de extracción en el árbol, no hay código que extraiga estos campos.

**Es falso.** Hay **132**.

## 1 · Dónde están y por qué el barrido no las vio

```text
  nvd.h        69 campos con mascara explicita
  soc15d.h     63 campos con mascara explicita
  vid.h         0
```

La forma es esta, y el detalle está en la **doble raya baja**:

```c
   soc15d.h:247  #define PACKET3_COPY_DATA__SRC_SEL(x) ((((unsigned)(x)) & 0xF) << 0)
   soc15d.h:248  #define PACKET3_COPY_DATA__DST_SEL(x) ((((unsigned)(x)) & 0xF) << 8)
   soc15d.h:249  #define PACKET3_COPY_DATA__SRC_CACHE_POLICY(x) ((((unsigned)(x)) & 0x3) << 13)
   soc15d.h:250  #define PACKET3_COPY_DATA__COUNT_SEL(x) ((((unsigned)(x)) & 0x1) << 16)
   soc15d.h:251  #define PACKET3_COPY_DATA__WR_CONFIRM(x) ((((unsigned)(x)) & 0x1) << 20)
```

Contra lo que escribe `vid.h`, que es solo desplazamiento:

```c
   vid.h:142     #define WRITE_DATA_DST_SEL(x)          ((x) << 8)
```

Dos diferencias, y las dos importan: **doble raya baja** (`__`) en lugar de una, y una **máscara
explícita** `& 0xF` en lugar de nada. Un barrido que buscaba una cosa y no la otra no podía
encontrarlas, y su patrón se validaba contra un positivo **de la forma que buscaba**, que es
precisamente el fallo que `1210` cerró para otros casos: validar el guard contra el mismo criterio
que produce la cifra no demuestra nada.

> La lección repetida, y aquí con consecuencias: un guard que compara la salida contra un positivo
> **de la misma forma que el patrón** no valida el patrón. Hay que validarlo contra un positivo de
> **otra** forma, o la cifra solo se confirma a sí misma.

## 2 · El cruce, y lo que dice de mis métodos

Alineando por **sufijo** —`vid.h` escribe `WRITE_DATA_DST_SEL` y `soc15d.h` escribe `DST_SEL`—,
porque son el mismo campo:

```text
  campo                       bit   vid.h        mascara soc15d.h    mascara nvd.h
  WRITE_DATA_DST_SEL            8   8 bits      4 bits  <8>        4 bits  <8>
  WR_ONE_ADDR                  16   4 bits      (no)               (no)
  WR_CONFIRM                   20   5 bits      1 bit   <20>       1 bit   <20>
  WRITE_DATA_CACHE_POLICY      25   5 bits      2 bits  <28>       2 bits  <28>
  WRITE_DATA_ENGINE_SEL        30   2 bits      (no)               (no)
```

Tres cosas, y las tres importan:

```text
  1.  El desplazamiento NUNCA subestima.  0 de 3.  Como la teoria predice:
      el hueco hasta el siguiente campo es una cota por arriba  y el campo
      real cabe dentro  forzosamente.

  2.  El desplazamiento SOBRESTIMA SIEMPRE en estos tres.  3 de 3, y nunca
      igual.  No es el ancho:  es el hueco.

  3.  soc15d.h y nvd.h COINCIDEN EXACTAMENTE en los tres campos donde ambos
      existen  (4, 1, 2 bits).  Dos generaciones distintas de ASIC declarando
      la misma anchura:  es la corroboracion mas fuerte sin hardware.
```

**Y para `DST_SEL` hay tres números distintos, y los tres son ciertos:**

| fuente | número | qué mide |
|---|---|---|
| enumeración inline de `vid.h` (`0,1,2,3,5`) | 3 bits | mínimo para representar los valores documentados |
| máscara de `soc15d.h` (`& 0xF`) | 4 bits | **ancho real del campo** |
| desplazamiento en `vid.h` (`<< 8`, siguiente en 16) | 8 bits | cota por arriba |

## 3 · Qué hay que corregir en lo que escribí antes

`1209` fiercely define `EXACTO` así:

> el ancho calculado por desplazamiento coincide con el mínimo que exige la enumeración

Eso sigue siendo cierto, y no es lo que hay que corregir. Lo que hay que corregir es **la fuerza
de la conclusión**, y hay que decirlo sin suavizar:

```text
  LO QUE AFIRME                     LO QUE REALMENTE SABIA
  ------------------------------------------------------------------
  "PIPE = 2 bits"  CORROBORATED    PIPE cabe en 2 bits  [2 bits] y el
                                   hardware genera 3, asi que 2 es exacto.
                                   ESTO SIGUE VALIENDO  y  no lo mueve nada.

  "ME = 1 bit"  CORROBORATED       lo mismo  [1 bit],  2 MEs  [2 bits]

  "QUEUE = 3 bits"  EXACTO         8 colas  = 2^3  [3 bits].  ESTO SIGUE
                                   VALIENDO por el ajuste con
                                   num_queue_per_pipe = 8.

  "campos EXACTOS de DMA_DATA"     aqui el desplazamiento dio 2 bits para un
                                   campo cuyo minimo por enumeracion era 2.
                                   Con mascara real no lo se.  El metodo no
                                   lo distingue de un acierto.
```

Y el punto duro: **`ENGINE_SEL` de `WRITE_DATA` da 2 bits por desplazamiento y no hay máscara que
lo confirme.** Sigue siendo cota. `1211` lo escribió como `EXACTO` con la definición correcta, pero
este cruce muestra que `EXACTO` **no** significa «el hardware lo tiene así de ancho».

## 4 · Lo que NO se puede hacer con las 132, y por qué

Las 132 son de **`soc15d.h` (GFX9) y `nvd.h` (GFX10/GFX11)**. `vid.h`, el header de GFX8, tiene
**cero**. Por §69 —*no transferir automáticamente conocimiento de otra generación*— usarlas como
hecho de GFX8 sería exactamente lo que el proyecto prohíbe.

Y no son directamente transferibles, por una razón medida. Intenté el test de solape, que solo
necesita la máscara y el desplazamiento, sin conocer los dwords:

```text
  campos con mascara en las dos cabeceras   132   en 19 paquetes
  pares de campos con rangos solapados       300
```

**300 solapes, y todos son entre dwords distintos.** `SRC_SEL [0:3]` es el dword de control y
`SRC_32B_ADDR_LO [2:31]` es un dword de dirección: jamás se escriben en el mismo sitio. El test
solo sería válido si supiera qué campos comparten dword, y **`soc15d.h` y `nvd.h` no declaran esa
frontera con comentarios**, que es lo que `vid.h` sí hace (`/* CONTROL */`, `/* CONTROL2 */`) y lo
que `1207` explotó.

```text
  EL BLOQUEO,  con nombre:  para validar el metodo por desplazamiento hacen
  falta los limites de dword de las cabeceras nuevas.  vid.h los tiene
  declarados.  soc15d.h y nvd.h no los declaran.  Sin ellos toda comparacion
  que no agrupe por dword produce falsos solapes.
```

Lo que **sí** es legítimo, y es lo que hice: comparar un paquete donde `vid.h` **sí** declara el
dword de control por comentario. `WRITE_DATA` es el caso bueno —de ahí la tabla de §2—, y los tres
campos que se pudieron alinear dan desplazamiento ≥ máscara, con cero excepciones.

## 5 · Procedimiento

```text
PREGUNTA   ¿existe lado de extraccion en el arbol?  y  ¿que dice el cruce de
            tres metodos sobre los mismos campos?
FUENTES    soc15d.h:246-253   nvd.h:252-260   (las mascaras)
           vid.h:141-161       (el desplazamiento de los mismos campos)
           las seis cabeceras de paquete del arbol, para el censo
MEDIDO     132 mascaras explicitas: nvd.h 69, soc15d.h 63, vid.h 0
           3 campos comparables de WRITE_DATA:
             desplazamiento >= mascara en 3 de 3,  igual en 0 de 3
             soc15d.h == nvd.h en 3 de 3
           300 solapes aparentes al no agrupar por dword, todos entre dwords
           distintos
LO QUE SE CORRIGE
   1201  "0 anchuras de campo en todo el arbol"  ->  hay 132,  en soc15d/nvd.
         Lo que si es cierto:  vid.h tiene 0.
   1209  "EXACTO" no significa "el ancho real".  Significa "coincide con el
         minimo por enumeracion".  Sigue siendo correcto lo que afirmaba,
         y ahora se sabe que el desplazamiento sobrestima donde hay mascara.
   1207 / 1211  sus tablas de anchura son COTAS POR ARRIBA.  No habia
         ninguna prueba de que fueran el ancho;  ahora hay prueba de que
         cuando hay mascara,  no lo son.
AUTOCORR.  dos fallos mios en este hallazgo:
   (a) conte mascaras con un patron que usaba [^\\n]* dentro de grep,  que es
       una clase de caracteres y no un salto de linea:  daba 0.  Rehecho con
       .*,  y salio 132.
   (b) alinee por nombre entero y no por sufijo,  y los nombres no coinciden
       entre cabeceras  (WRITE_DATA_DST_SEL frente a DST_SEL):  daba 0
       comparaciones  y parecia que no habia dato.  Era un fallo de
       alineacion,  no una ausencia.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE QUEDA ABIERTO
  - los limites de dword de soc15d.h y nvd.h  (el bloqueo de §4)
  - si ENGINE_SEL de WRITE_DATA son 2 bits de verdad:  hace falta mascara
  - si las 132 mascaras de GFX9/GFX10 describen GFX8:  §69 dice que no se
    transfieren,  y no se transfieren.  Son HIPOTESIS ESTRUCTURADAS,  que es
    mejor que nada  y peor que una medicion.
```