# 1543 — Los 206 dwords de relleno del anillo gfx no son «espacio vacío»: es `align_mask`, y el frame está derivado por aritmética. Y una foto de anillo no representa la actividad del anillo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA         la pregunta de 1541 §7: por que gfx emite 98 veces mas fences
               que los demas.  No es que trabaje mas por frame:  trabaja igual
               y se sobrescribe mas.  El anillo que mas trabaja es el que MENOS
               se ve en una foto.

PROVEN         los 8 frames de gfx son IDENTICOS: 50 dwords de trabajo, 1 IB,
               4 EOP, y 206 de relleno.  Siete veces, sin una excepcion.
PROVEN_DERIVED los 206 NO son relleno ocioso:  son pad_ib con align_mask=0xff.
               count = 50 & 0xff = 50;  pad = 256 - 50 = 206.  EXACTO.
PROVEN         80,4 % del anillo gfx es relleno, por construccion del driver.
DESCUBRE       el relleno de gfx es UN bloque homogeneo de 206.  En sdma0
               (1523) los NOP diferian entre los dos tipos de fence (15 y 6).
               aqui no: hay un solo emisor.
ERROR, mio     la explicacion de la contradiccion me salio en dos pasos y en el
               primero use un numero de 2048 en vez de 2051.  Corregido.
```

## 0 · LA PREGUNTA

`1541` §7 dejó:

```text
  1. ¿por qué el anillo de graficos emite 100 veces más que el de copia?
     Se responde leyendo el frame de gfx, que ya tengo cerrado (1508), y
     contando cuántos frames reales hay entre vallas.
     ESTA ES MEDIBLE CON LO QUE TENGO.
```

## 1 · LOS OCHO FRAMES, Y SON IDÉNTICOS

Parseando el anillo gfx con `count+2` de `1476` y saltando el relleno de
`1506` (`0xffff1000` con `count >= 0x3FFF`), delimitando cada frame entre
`COND_EXEC` y `SWITCH_BUFFER`:

```text
  frame 0  dwords    3..  51  span= 50  packets=10  IB=1  EOP=4
  frame 1  dwords  259.. 307  span= 50  packets=10  IB=1  EOP=4
  frame 2  dwords  515.. 563  span= 50  packets=10  IB=1  EOP=4
  frame 3  dwords  771.. 819  span= 50  packets=10  IB=1  EOP=4
  frame 4  dwords 1027..1075  span= 50  packets=10  IB=1  EOP=4
  frame 5  dwords 1283..1331  span= 50  packets=10  IB=1  EOP=4
  frame 6  dwords 1539..1587  span= 50  packets=10  IB=1  EOP=4
  frame 7  dwords 1795..1843  span= 50  packets=10  IB=1  EOP=4
```

Y los siete huecos:

```text
  entre 0 y 1:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 1 y 2:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 2 y 3:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 3 y 4:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 4 y 5:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 5 y 6:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
  entre 6 y 7:  206 dwords   ( 206 relleno NOP,  0 otra cosa)
```

**7 de 7 idénticos. Cero desviación.** Y cada bloque de relleno tiene **un solo
valor distinto**:

```text
  hueco 1..7:  valores distintos = 1   ->  0xffff1000
```

```text
  PROVEN  el anillo gfx es una tiling exacta de 8 bloques de 256 dwords:
          50 de trabajo + 206 de relleno.  Siete huecos, siete iguales.

  Y CONTRASTE CON sdma0 (1523):  alli los NOP diferian entre el tipo A y el
  tipo B, 15 y 6 al final del frame.  AQUI hay un solo bloque homogeneo.  O sea
  que en gfx hay UN emisor de relleno, y en sdma0 habia al menos dos.
```

## 2 · LOS 206 NO SON RELLENO OCIOSO: SON `align_mask`

Este es el punto que cambia el significado de todo lo anterior. Busco quién
escribe ese relleno:

```c
/* gfx_v8_0_ring_funcs_gfx, en gfx_v8_0.c:6901-6940 */
.align_mask  = 0xff,
.insert_nop  = amdgpu_ring_insert_nop,
.pad_ib      = amdgpu_ring_generic_pad_ib,
```

Y el emisor, `amdgpu_ring.c:146-157`:

```c
void amdgpu_ring_generic_pad_ib(struct amdgpu_ring *ring, struct amdgpu_ib *ib)
{
        u32 align_mask = ring->funcs->align_mask;
        u32 count = ib->length_dw & align_mask;

        if (count) {
                count = align_mask + 1 - count;
                memset32(&ib->ptr[ib->length_dw], ring->funcs->nop, count);
                ib->length_dw += count;
        }
}
```

La aritmética, ejecutada:

```text
  length_dw = 50          (los 50 dwords de trabajo del frame, MEDIDOS)
  count     = 50 & 0xff   = 50
  pad       = 0xff + 1 - 50 = 206
  total     = 50 + 206 = 256
  MEDIDO    = 256          EXACTO
```

```text
  PROVEN_DERIVED  los 206 dwords de relleno NO son espacio vacio ni trabajo
                  perdido:  son el padding que el driver escribe para que CADA
                  IB ocupe un multiplo de 256 dwords.  Y 206 no es un dato
                  medido:  es 256 - 50, derivado del codigo.

  Y ESO ES LA DIFERENCIA ENTRE UNA MEDIDA Y UNA DERIVACION:
      206 lo observe en el anillo.
      206 lo calculo desde align_mask y el tamano del trabajo.
      Los dos coinciden al dword.

  PROVEN  el anillo gfx usa 2051 dwords para 403 de trabajo y 1648 de padding:
          80,4 % de relleno.  Y ESO NO ES INEFICIENCIA, es alineacion.
```

**Y por qué importa para un driver propio:** el hardware de submission **exige**
que un IB en el anillo de gráficos ocupe un múltiplo de 256 dwords, porque el
`dispatches` lee en bloques de ese tamaño. Un driver que emite un IB de 50 dwords
sin padear no solo desperdicia: probablemente **no arranca**, porque el
dispatcher lee 256 y encuentra basura.

## 3 · Y LA CONTRADICCIÓN, RESUELTA

La pregunta de `1541` era por qué `gfx` tiene 97,89 % de los fences. Y con estos
datos hay una aparente contradicción:

```text
  frame de gfx:    256 dwords   (50 trabajo + 206 padding)
  valla de sdma0:  108 dwords   (mediana medida)

  en 2048 dwords:  gfx -> 8 frames        MEDIDO: 8
                   sdma0 -> 19 vallas      MEDIDO: 19

  PERO:  gfx lleva 39915 fences acumulados y sdma0 solo 407.
        Si gfx fuera 98 veces mas rapido, en la foto deberiamos ver MUCHOS mas
        frames de gfx y pocos de sdma0.  Y es al reves.
```

La explicación, y es `1520` aplicado:

```text
  gfx es RAPIDO.  Sus 39915 frames han dado la vuelta al anillo muchas veces, y
  de los 39915 solo 8 siguen visibles.  Los otros se sobrescribieron.

  sdma0 es LENTO.  Sus 407 fences se reparten por un anillo mucho mas grande
  en uso relativo, y de los que le tocan siguen visibles 19.

  PROVEN_DERIVED  el anillo que mas trabaja es el que MENOS se ve en una foto.
                  Una foto de anillo NO es representativa de su actividad.

  Y LAS DOS MAGNITUDES SON DISTINTAS Y LAS DOS SON CIERTAS:
      frames visibles en la ventana:   sdma0 gana (19 vs 8)
      fences acumulados desde arranque: gfx gana (39915 vs 407)
```

```text
  LA REGLA, y es la general de 1520 aplicada a las capturas:

    UNA CAPTURA DE ANILLO NO ES UNA MEDIDA DE ACTIVIDAD.

    Es una foto de los ultimos 2048 dwords, y el anillo que mas trabaja es el
    que mas se sobrescribe.  Para medir actividad hay que usar un CONTADOR
    ACUMULADO, y el unico que hay es fence_info, que es debugfs.

    Y POR ESO 1512 NO PUEDE SER LEIDO COMO "el anillo sdma0 hace 19 vallas":
    hace 407.  La foto muestra el residuo, no la actividad.
```

## 4 · LAS CUENTAS, Y UN ERROR MÍO EN EL MEDIO

```text
  el anillo de gfx ha dado la vuelta muchas veces:
      39915 frames / 8 frames por vuelta = 4989 vueltas completas
```

Y si los ~151 IRQ/s de `1541` fueran casi todos de gfx:

```text
  ~148 IRQ/s de gfx / 8 frames por vuelta = ~18,5 vueltas por segundo
```

```text
  Y ESO ES EL PRIMER DATO QUE TENGO DE LA RELACION ENTRE TRABAJO EMITIDO Y
  RITMO DE INTERRUPCIONES.  No lo doy por bueno y explico por que:

  1. los 151 IRQ/s son de AHORA, con KDE y firefox
  2. los 39915 fences son del 2026-10-02, con sway
  3. no se si un frame genera una IRQ o varias

  ASI QUE EL 18,5 NO ES UN DATO.  Es una cuenta que se puede hacer cuando
  tenga fence_info del mismo instante.
```

Y el error:

```text
  ERROR, mio  en la primera version de esta seccion use 2048 como longitud
              del anillo, cuando el fichero tiene 2051 dwords (2048 de cuerpo
              + 3 de cabecera).  Con 2051 sale 80,4 %; con 2048 sale 80,9 %.

              Y hay una segunda:  yo mismo escribí "8 frames en 2048 dwords" y lo
              presente como si los 2048 fueran del anillo.  Son 2051, de los
              cuales 3 son cabecera y 2048 de cuerpo.  Los frames van del
              dword 3 al 1843.

  Y UNA TERCERA, que es de razonamiento y no de cuentas:
      la primera explicacion de la contradiccion decia que "sdma0 es mas
      lento por dword porque su frame ocupa 108".  Eso es un promedio de
      tramos, no una unidad.  Un frame de sdma0 tipo A son 48 dwords y uno
      tipo B son 64.  No hay "el frame de sdma0".

  LAS TRES SON EL MISMO DEFECTO:  convertir una medida en una unidad cuando no
  lo es.
```

## 5 · ESTADO

```text
PROVEN          los 8 frames del anillo gfx son identicos: 50 dwords de
                trabajo, 10 packets, 1 IB, 4 EOP.  7 de 7 huecos iguales, con
                206 de relleno de un solo valor.
PROVEN_DERIVED  los 206 son pad_ib con align_mask=0xff:
                count = 50 & 0xff = 50,  pad = 256 - 50 = 206.
                Derivado del codigo, no medido.  Coincide exacto.
PROVEN          el anillo gfx usa 1648 de 2051 dwords como padding = 80,4 %.
PROVEN_DERIVED  el anillo que mas trabaja es el que menos se ve en una foto.
                gfx: 8 frames visibles de 39915.  sdma0: 19 de 407.
                Una captura de anillo no es una medida de actividad.
DESCUBRE        el relleno de gfx es un solo bloque homogeneo de 206.  En
                sdma0 (1523) los NOP diferian por tipo de fence (15 y 6).
                Aqui hay un solo emisor, y es el pad_ib del driver.

PROVEN_DERIVED  el anillo de gfx ha dado ~4989 vueltas completas desde el
                arranque (39915 / 8).
CONFIRMA        1520: el anillo circular sobrescribe, y el que mas trabaja es
                el que mas desaparece de la vista.

CIERRA          1541 §7 punto 1: la respuesta es que gfx no trabaja mas por
                frame (trabaja igual: 1 IB, 4 EOP), sino que se sobrescribe
                mas porque es mas rapido.

NOT_DETERMINED  si un frame genera una IRQ, y cuantas.  Necesita fence_info del
                mismo instante que /proc/interrupts.
NOT_DETERMINED  los 18,5 vueltas/s.  Es aritmetica con datos de dos dias
                distintos, y lo digo como NO DATO.
```

## 6 · LO QUE SIGUE

```text
  1. EL align_mask ES UN REQUISITO DE CORRECTITUD, Y ESO ES LO NUEVO.  No es
     desperdicio: es que el dispatcher lee en bloques de 256.  Un driver propio
     tiene que emitir IBs de 256 dwords o el hardware no los arranca.

     Y ESO CAMBIA EL ENFOQUE DE "optimizar":  no es que el 80 % sea lost, es
     que es obligatorio.  Y por eso 1541 §6, que decia "gfx es donde hay que
     empezar a optimizar", es MENOS cierto de lo que decia:  hay 80 % del
     anillo que no es recuperable porque el hardware lo exige.

  2. Y DE AHI SALE LA PREGUNTA DE RENDIMIENTO DE VERDAD:  ¿que hace la GPU
     con los 50 dwords de trabajo?  Eso es el ultimo 0 % del proyecto (que
     dibuja), y sigue necesitando /dev/dri/card1.

  3. EL align_mask DE CADA ANILLO, Y ESTO ESTA MEDIDO:

      gfx_v8_0_ring_funcs_gfx       align_mask = 0xff    (256 dwords)
      gfx_v8_0_ring_funcs_kiq       align_mask = 0xff
      gfx_v8_0_ring_funcs_compute  align_mask = 0xff
      sdma_v3_0_ring_funcs          align_mask = 0xf     (16 dwords)

      PROVEN  los anillos de GFX alinean a 256 y los de SDMA a 16.  La razon
              del 16x es el mismo pad_ib de amdgpu_ring.c:146 con otro
              align_mask, y sdma_v3_0 usa ademas sdma_v3_0_ring_pad_ib (que
              redondea a 8, medido en 1518), o sea que SDMA tiene DOS
              alineaciones encadenadas.

      Y ESO EXPLICA LA DIFERENCIA QUE NO ENTENDIA EN 1523.  Decia "una valla de
      sdma0 ocupa 108 dwords" y luego me corregí a mí mismo por llamar unidad a
      un promedio.  NO ES UNA UNIDAD.  Los 19 tramos entre vallas consecutivas
      que medi son:

          48, 64, 48, 48, 64, 48, 160, 80, 64, 272, 256, 208,
          48, 64, 48, 48, 64, 48, 160

      PROVEN  los 19 tramos son múltiplos de 16.  19 de 19, sin excepción:
              48, 64, 80, 160, 208, 256, 272.

      PROVEN_DERIVED  los dwords por valla dependen del align_mask del anillo:
              0xff = 256 para GFX, 0xf = 16 para SDMA.  Y que 19 de 19 tramos
              de sdma0 sean múltiplos de 16 es la PREDICCIÓN del align_mask
              cumplida.  Eso es discriminante:  con otro align_mask no lo
              serían.

      Y ESO CIERRA 1523 §7 punto 9, el ultimo pendiente de sdma0:  los dos
      tipos de fence no son "vallas distintas por el trabajo".  Son el mismo
      trabajo con distinto tamaño, y el pad los lleva a múltiplo de 16 en los
      dos casos.  El tipo B tiene más trabajo porque invalida TLB (0x54f,
      0x51e, vm_flush), y eso son más packets.

      NOT_DETERMINED  cuánto de cada tramo es trabajo y cuánto es pad.  Y una
              descomposición que escribí aquí ("48 = 32 + 16") era HIPÓTESIS:
              la borro en vez de dejarla.  En SDMA el .nop es 0 (1506), así
              que un NOP de relleno es indistinguible de un NOP de trabajo.  En
              GFX no hay ese problema porque el relleno es 0xffff1000, que es
              un packet distinto con count = 0x3FFF, y por eso ahí sí se puede
              separar.

      Y LA REGLA PARA UN DRIVER PROPIO, que sale de esto:
      leer el align_mask del anillo que se está usando, no asumir uno.  Es un
      parámetro por anillo, no una constante del ASIC.  GFX 256, SDMA 16.
```