# 1222 — `vid.h` y `cikd.h` son casi el mismo archivo, y **discrepan en los 19 offsets de registro**, hasta 8704 bytes. El que vale para GFX8 lo decide el grafo de includes, no la preferencia

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR · HEADER-DUPLICATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el item que 1221 dejo nombrado:  cotejar los 2 bloques de cikd.h
NUEVO    duplicacion de archivo con CONSECUENCIA:  dos copies del mismo bloque
         declaran los mismos nombres con valores distintos
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · El cotejo que `1221` dejó pendiente

`1221` halló 4 bloques `/* mmX mask */` en el árbol: 2 en `vid.h` y 2 en `cikd.h`. Cotejados:

```text
  PA_SC_RASTER_CONFIG     vid.h:480  32 macros    cikd.h:579  32 macros   IDENTICAS
  PA_SC_RASTER_CONFIG_1   vid.h:507   6 macros    cikd.h:606   6 macros   IDENTICAS
  y el desplazamiento entre los dos bloques es  +99 lineas en AMBOS
```

**Byte a byte idénticos, con el mismo desplazamiento.** O sea que la región se copió como una
unidad. Y los dos **omiten `PKR_XSEL2`** igual, porque la omisión viene heredada, no es una
omisión independiente en cada archivo.

## 1 · La duplicación, medida

```text
                          vid.h          cikd.h
  lineas                   516            615
  #define                  219            221

  #define con el MISMO nombre en ambos          188
    de los cuales,  texto byte-identico        169
    de los cuales,  texto DISTINTO              19

  desplazamiento mas frecuente:   +124 lineas,  106 #define
  segundo mas frecuente:           +99 lineas,   32 #define
```

**169 de los 221 `#define` de `cikd.h` son idénticos a los de `vid.h`.** Y hay una región de 106
definiciones con desplazamiento fijo. `cikd.h` es, en esa zona, el mismo documento que `vid.h`.

## 2 · Y los 19 que difieren, divergen de verdad

Los 19 son de la forma `(X - X)`, o sea **offsets relativos** dentro de un bloque. Ninguno coincide:

```text
  AUD0_REGISTER_OFFSET        vid.h 0x0000    cikd.h 0x0000        +0
  AUD1_REGISTER_OFFSET        vid.h 0x0004    cikd.h 0x0006        -2
  AUD2_REGISTER_OFFSET        vid.h 0x0008    cikd.h 0x000c        -4
  AUD3_REGISTER_OFFSET        vid.h 0x000c    cikd.h 0x0012        -6
  AUD4_REGISTER_OFFSET        vid.h 0x0010    cikd.h 0x0018        -8
  AUD5_REGISTER_OFFSET        vid.h 0x0014    cikd.h 0x001d        -9
  AUD6_REGISTER_OFFSET        vid.h 0x0018    cikd.h 0x0024       -12
  CRTC0_REGISTER_OFFSET       vid.h 0x0000    cikd.h 0x0000        +0
  CRTC1_REGISTER_OFFSET       vid.h 0x0200    cikd.h 0x0300      -256
  CRTC2_REGISTER_OFFSET       vid.h 0x0400    cikd.h 0x2600     -8704
  CRTC3_REGISTER_OFFSET       vid.h 0x2600    cikd.h 0x2900      -768
  CRTC4_REGISTER_OFFSET       vid.h 0x2800    cikd.h 0x2c00     -1024
  CRTC5_REGISTER_OFFSET       vid.h 0x2a00    cikd.h 0x2f00     -1280
  HPD0..HPD5                 0x0000..0x0028   0x0000..0x000f    +0..+25

  con el mismo valor:  0 de 19
  separacion maxima:  8704 bytes (0x2200)
```

Y el patrón delata cuál es coherente. Los offsets de `vid.h` tienen **paso uniforme de 4 bytes**,
que es lo que tiene un array de registros:

```text
  vid.h    AUD0..AUD6:  0x0000  0x0004  0x0008  0x000c  0x0010  0x0014  0x0018
           paso constante de 4

  cikd.h  AUD0..AUD6:  0x0000  0x0006  0x000c  0x0012  0x0018  0x001d  0x0024
           paso irregular:  6, 6, 6, 6, 5, 7
```

Y `CRTC2` no está ni cerca: `0x0400` contra `0x2600`. Eso no es deriva, es otro mapa de registros.

## 3 · Cuál vale, y por qué no es opinión

El grafo de includes lo decide:

```text
  gfx_v8_0.c   incluye  vid.h                  (linea 35)
               incluye  gca/gfx_8_0_sh_mask.h (linea 51)
               NO incluye cikd.h

  cikd.h  lo incluyen   gfx_v7_0.c   dce_v8_0.c   cik.c   cik_ih.c
                         cik_sdma.c  amdgpu_uvd.c  amdgpu_vce.c
                         amdgpu_amdkfd_gfx_v7.c

  vid.h   lo incluyen   gfx_v8_0.c   gmc_v8_0.c   mxgpu_vi.c   dce_v10_0.c
                         cz_ih.c  iceland_ih.c  sdma_v2_4.c  amdgpu_amdkfd_gfx_v8.c
```

**Para GFX8 el que vale es `vid.h`**, y no porque lo prefiera sino porque es el que entra en la
unidad de traducción que compila este ASIC. `cikd.h` es el header de GFX7 y de los bloques
CIK/UVD/VCE.

## 4 · Por qué esto importa aunque no se toque nada

```text
  UN RIESGO REAL, NO ESTETICO
  Si una unidad de traduccion incluyera los dos,  habria redefinicion de macro con el
  MISMO nombre y VALOR DISTINTO:  el compilador avisa,  y con -Werror no
  compila.  Hoy no compila porque gfx_v8_0.c no incluye cikd.h,  pero eso es
  casualidad de includes,  no una proteccion.

  Y ALGO MAS INTERESANTE:  vid.h y cikd.h estan casi duplicados,  y las copias
  se han desincronizado SOLO en los offsets.  169 de 221 iguales,  19 distintos.
  Eso quiere decir que alguien actualizo una y no la otra,  en algun momento,
  y no hay nada en el arbol que lo advierta.

  LO QUE NO AFIRMO:  que vid.h tenga los offsets CORRECTOS para el hardware.
  Que es el que se incluye es un hecho del grafo.  Que sus valores sean los
  buenos para el silicio es NOT_DETERMINED sin RREG32.
```

## 5 · Procedimiento

```text
PREGUNTA   ¿los bloques de cikd.h son iguales a los de vid.h,  y que
            consecuencias tiene la duplicacion?
FUENTES    vid.h:479-513      cikd.h:578-612     (los dos bloques de cada uno)
           vid.h completo     cikd.h completo    (censo de #define)
           gfx_v8_0.c:24-58   (el grafo de includes)
MEDIDO     bloques identicos byte a byte:  2 de 2
             desplazamiento entre bloques:  +99 lineas en los dos
  vid.h  516 lineas / 219 define     cikd.h  615 lineas / 221 define
  nombres compartidos: 188    texto identico: 169    texto distinto: 19
  offsets de registro con el mismo valor:  0 de 19
  separacion maxima:  8704 bytes
  paso de AUD en vid.h:  4 bytes constante     en cikd.h:  6,6,6,6,5,7
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - si hay OTROS pares de headers duplicados con divergencia de valores:  el
    metodo es contar nombres y luego comparar texto,  que es como se
    encontro antes el de radeontop, spatch y los vectores de ibref
  - si alguno de los 19 offsets se puede contrastar con un registro real
```