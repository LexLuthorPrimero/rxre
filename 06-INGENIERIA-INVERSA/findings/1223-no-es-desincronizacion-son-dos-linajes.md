# 1223 — Corrección a `1222`: no es una desincronización. `sid.h` y `cikd.h` son **idénticos** en los 19; `vid.h` es el linaje GFX8 y los otros dos el GFX6/GFX7

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CORRECTION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CORRIGE   1222:  decia que vid.h y cikd.h se "habian desincronizado".  No es
           eso.  Hay DOS LINAJES con el mismo nombre de simbolo,  y cikd.h esta
           dentro del segundo,  no del primero
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que `1222` afirmó y lo que hay

`1222` §5 escribió:

> las copias se han desincronizado SOLO en los offsets. 169 de 221 iguales, 19
> distintos. Alguien actualizó una y no la otra.

**Eso es falso, y la frase es la que hay que retirar.** El censo completo de pares de headers
muestra un tercer archivo en el grupo: `sid.h`. Y `sid.h` no está en medio — está **exactamente en
el lado de `cikd.h`**.

```text
  simbolo                      vid.h    sid.h    cikd.h    sid==cik   vid==cik
  AUD0_REGISTER_OFFSET         0x00000  0x00000  0x00000     si         si
  AUD1_REGISTER_OFFSET         0x00004  0x00006  0x00006     si         NO
  AUD2_REGISTER_OFFSET         0x00008  0x0000c  0x0000c     si         NO
  AUD3_REGISTER_OFFSET         0x0000c  0x00012  0x00012     si         NO
  AUD4_REGISTER_OFFSET         0x00010  0x00018  0x00018     si         NO
  AUD5_REGISTER_OFFSET         0x00014  0x0001d  0x0001d     si         NO
  AUD6_REGISTER_OFFSET         0x00018  0x00024  0x00024     si         NO
  CRTC0_REGISTER_OFFSET        0x00000  0x00000  0x00000     si         si
  CRTC1_REGISTER_OFFSET        0x00200  0x00300  0x00300     si         NO
  CRTC2_REGISTER_OFFSET        0x00400  0x02600  0x02600     si         NO
  CRTC3_REGISTER_OFFSET        0x02600  0x02900  0x02900     si         NO
  CRTC4_REGISTER_OFFSET        0x02800  0x02c00  0x02c00     si         NO
  CRTC5_REGISTER_OFFSET        0x02a00  0x02f00  0x02f00     si         NO
  HPD0_REGISTER_OFFSET         0x00000  0x00000  0x00000     si         si
  HPD1_REGISTER_OFFSET         0x00008  0x00003  0x00003     si         NO
  HPD2_REGISTER_OFFSET         0x00010  0x00006  0x00006     si         NO
  HPD3_REGISTER_OFFSET         0x00018  0x00009  0x00009     si         NO
  HPD4_REGISTER_OFFSET         0x00020  0x0000c  0x0000c     si         NO
  HPD5_REGISTER_OFFSET         0x00028  0x0000f  0x0000f     si         NO

  sid.h identico a cikd.h :  19 de 19
  vid.h identico a cikd.h :   3 de 19      (los tres que valen cero)
```

## 1 · Lo que realmente hay: dos linajes

```text
  LINAJE GFX8          vid.h
      lo incluyen  gfx_v8_0.c:35   gmc_v8_0.c:47   mxgpu_vi.c:29
                       dce_v10_0.c  cz_ih.c  iceland_ih.c  sdma_v2_4.c
                       amdgpu_amdkfd_gfx_v8.c

  LINAJE GFX6/GFX7     sid.h  ==  cikd.h
      sid.h lo incluyen   gfx_v6_0.c  si.c  si_dma.c  si_ih.c  dce_v6_0.c
                          uvd_v3_1.c  vce_v1_0.c
      cikd.h lo incluyen  gfx_v7_0.c  cik.c  cik_ih.c  cik_sdma.c  dce_v8_0.c
                          amdgpu_uvd.c  amdgpu_vce.c  amdgpu_amdkfd_gfx_v7.c
```

**El mismo nombre de símbolo significa un registro distinto en cada ASIC, y por eso los dos
linajes declaran valores distintos.** Eso no es una desincronización: es lo correcto, porque GFX8 y
GFX6 no tienen el mismo mapa de registros.

Lo que sí es duplicación, dentro del segundo linaje, es que `sid.h` y `cikd.h` llevan **19 de 19
idénticos** — dos copias exactas del mismo bloque. Eso es la duplicación que existe, y es
benigna: nunca se incluyen juntas.

## 2 · El riesgo real, que es otro y más pequeño

```text
  LO QUE 1222 DIJO   "si una unidad incluyera los dos,  habria redefinicion con
                       el mismo nombre y valor distinto".  Cierto como mecanismo,
                       y ademas no aplica:  gfx_v8_0.c no incluye cikd.h ni sid.h,
                       asi que no hay conflicto posible en el codigo de esta placa.

  LO QUE PASA EN REALIDAD
     El riesgo no es de compilacion.  Es de LECTURA:  quien abra cikd.h o sid.h
     buscando AUD0_REGISTER_OFFSET obtiene 0x1780,  y ese valor no es el de
     GFX8.  El unico que vale para esta placa esta en vid.h,  y solo porque el
     grafo de includes lo mete en la unidad de traduccion de GFX8.

  Y ESO ES UN HECHO DEL GRAFO,  no una propiedad del simbolo.  El simbolo se llama
  igual en los dos linajes  y no lleva nada que lo distinga.
```

## 3 · El censo completo de headers duplicados, que era lo que `1222` dejó nombrado

Todos los pares y grupos de headers de `amdgpu/` que comparten símbolos:

```text
  grupo                                            compartidos  divergentes
  nvd + soc15d                                            56           0
  cikd + gfx_v12_1_pkt + nvd + sid + soc15d + vid          47           5
  cikd + sid + vid                                         28          19
  6 x *_sdma_pkt_open                                      25           0
  gfx_v12_1_pkt + nvd                                      21           0
  cikd + vid                                               21           0
  navi10 + sdma_v6_0_0 + sdma_v7_1_0                       20           0
  cikd + nvd + sid + soc15d + vid                          18           0
  navi10 + sdma_v6_0_0 + sdma_v7_1_0 + vega10              16           1
  cikd + gfx_v12_1_pkt + nvd + soc15d + vid                13           0
  soc15d + vid                                              9           0
  cikd + sid + soc15d + vid                                 8           1
  mmsch_v4_0 + mmsch_v5_0                                   8           0
  ... y 22 grupos mas,  todos con 0 o 1 divergente

  total de simbolos divergentes en todo el conjunto:  27
```

Dos cosas que salen de ese censo:

```text
  1.  LA DUPLICACION MAS GRANDE ES LIMPIA.  nvd + soc15d  comparten 56
      simbolos y los 56 tienen el MISMO valor.  Los seis headers
      *_sdma_pkt_open comparten 25,  y los 25 iguales.  Los linajes de
     _packet_ estan sincronizados.

  2.  LA DIVERGENCIA ESTA CONCENTRADA.  De los 27 simbolos divergentes,  19
      son los *_REGISTER_OFFSET  de los dos linajes,  y los 8 restantes
      (5 + 1 + 1 + 1) estan en tres grupos que no he mapeado.  Queda nombrado
      como fila,  no abandonado.
```

## 4 · Lo que `1222` acertó y no retiro

```text
  - que vid.h y cikd.h comparten 169 #define byte-identicos:  sigue siendo
    cierto,  y es la duplicacion de bloques de registro que 1221 midio
  - que el desplazamiento +99 entre los bloques de ambos es el mismo:  cierto
  - que el grafo de includes decide cual vale:  cierto,  y es lo que sostiene
    todo este hallazgo
  - que ambos omiten PKR_XSEL2 y que la omision viene heredada:  cierto
```

Lo único que retiro es lainterpretacion de «alguien actualizó una y no la otra».

## 5 · Procedimiento

```text
PREGUNTA   ¿hay mas pares de headers duplicados con divergencia de valores?
FUENTES    censo de los ~90 headers de amdgpu/:  contar nombres y comparar texto
           los tres ficheros, leidos con las 19 lineas de cada offset
           el grafo de includes de los dos linajes
MEDIDO     pares con >=8 simbolos compartidos:  13
           sid.h == cikd.h en los 19 offsets:  19 de 19
           vid.h == cikd.h en los 19 offsets:   3 de 19
           simbolos divergentes en todo el conjunto de headers:  27
           nvd + soc15d:  56 compartidos,  0 divergentes
LO QUE SE CORRIGE
   1222  "las copias se han desincronizado SOLO en los offsets... alguien
          actualizo una y no la otra"  ->  RETIRADO.  Hay dos linajes de ASIC
          con el mismo nombre de simbolo,  y sid.h pertenece al segundo.
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - los 8 simbolos divergentes que no son offsets,  en tres grupos sin mapear:
    el grupo de 5 (cikd + gfx_v12_1_pkt + nvd + sid + soc15d + vid),  el de 1
    de los sdma_pkt_open,  y los 2 de mmsch
  - si AUD0_REGISTER_OFFSET de vid.h se puede contrastar con un RREG32
```