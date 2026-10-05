# 1220 — `ENGINE_SEL` no es un campo: el hardware selecciona motor **eligiendo registro**. Y los dos `COMMAND` del CP DMA son idénticos 9 de 9

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el unico campo de MAP_QUEUES/WRITE_DATA que 1215 dejo como cota sin
         confirmar:  ENGINE_SEL.  No se confirma porque NO PUEDE:  no es un campo
CORROBORA  DMA_DATA por cuarta via:  dos registros de GFX8,  9 de 9 y 8 de 8
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · De dónde venía la duda

`1215` y `1218` dejaron escrito, sin suavizar, que `WRITE_DATA.ENGINE_SEL` es **cota por arriba de
2 bits** y que sin una máscara no se puede confirmar. `ENGINE_SEL` está en `vid.h:156` como

```c
  #define WRITE_DATA_ENGINE_SEL(x)  ((x) << 30)   /* 0 - me / 1 - pfp / 2 - ce */
```

La pregunta es si hay una máscara que lo confirme. Y el resultado es que **no la hay, y no puede
haberla.**

## 1 · Cero ocurrencias, y dos motores

```text
  ENGINE_SEL como campo de registro en gfx_8_0_sh_mask.h      0 ocurrencias

  y los 14 registros del bloque:
    mmCP_DMA_ME_CONTROL   0xc078      mmCP_DMA_PFP_CONTROL      0xc077
    mmCP_DMA_ME_COMMAND   0xc084      mmCP_DMA_PFP_COMMAND      0xc089
    mmCP_DMA_ME_SRC_ADDR  0xc080      mmCP_DMA_PFP_SRC_ADDR     0xc085
    mmCP_DMA_ME_SRC_ADDR_HI 0xc081    mmCP_DMA_PFP_SRC_ADDR_HI  0xc086
    mmCP_DMA_ME_DST_ADDR  0xc082      mmCP_DMA_PFP_DST_ADDR     0xc087
    mmCP_DMA_ME_DST_ADDR_HI 0xc083    mmCP_DMA_PFP_DST_ADDR_HI  0xc088
    mmCP_DMA_CNTL         0xc08a      mmCP_DMA_READ_TAGS         0xc08b
```

**Hay dos motores, `ME` y `PFP`, y no hay ninguno para `CE`.** El hardware implementa la
selección de motor **eligiendo registro**, no escribiendo un campo. El campo `ENGINE_SEL` del
paquete es la forma en que el paquete codifica una elección que el hardware resuelve en la
dirección del registro.

Eso explica la ausencia, y es mejor que una cota sin confirmar:

```text
  ANTES    ENGINE_SEL = 2 bits,  cota por arriba,  sin mascara que lo confirme
  AHORA    ENGINE_SEL no es un campo del hardware.  La seleccion ocurre en la
           direccion del registro.  No hay mascara porque no hay campo.

  Y EL DATO QUE NO SE PUDO DESCARTAR:  el enum de vid.h declara TRES opciones
  (me, pfp, ce)  y solo hay DOS motores implementados.  Que el tercer valor no
  tenga destino en GFX8 es NOT_DETERMINED.  Puede que la DMA del CE este en otro
  bloque,  o que el valor 2 no sea alcanzable desde esta placa.
```

## 2 · Y los dos `COMMAND` son idénticos 9 de 9

`CP_DMA_ME_COMMAND` y `CP_DMA_PFP_COMMAND`, campo a campo:

```text
  campo          ME mask        PFP mask       identicos
  BYTE_COUNT     0x001fffff    0x001fffff       si
  DIS_WC         0x00200000    0x00200000       si
  SRC_SWAP       0x00c00000    0x00c00000       si
  DST_SWAP       0x03000000    0x03000000       si
  SAS            0x04000000    0x04000000       si
  DAS            0x08000000    0x08000000       si
  SAIC           0x10000000    0x10000000       si
  DAIC           0x20000000    0x20000000       si
  RAW_WAIT       0x40000000    0x40000000       si

  identicos: 9 de 9
```

Y los dos `CONTROL`:

```text
  campos en ME   8      campos en PFP   8
  comunes: 8     con mascara identica: 8
  solo en ME: []        solo en PFP: []
```

## 3 · Cuarta corroboracion de `DMA_DATA`

El dword 7 de `DMA_DATA` tiene ahora **cuatro** declaraciones independientes que coinciden:

```text
  A.  PROSA  vid.h:278        COMMAND [30:21] | BYTE_COUNT [20:0]
  B.  MACROS vid.h:309-334    sin mascara, Positions identicas a la mascara
  C.  MASCARA  CP_DMA_ME_COMMAND     9 campos,  cobertura [0:30],  hueco [31]
  D.  MASCARA  CP_DMA_PFP_COMMAND    9 campos,  identica a C en los 9
```

Y el dword 2, `CONTROL`, tiene **tres**: la prosa lo nombra, los macros de `vid.h` dan 4 campos con
4 posiciones de inicio idénticas a `CP_DMA_ME_CONTROL`, y ahora hay **dos** copias de esa máscara
iguales entre sí.

> Dos registros físicamente distintos, con direcciones distintas y con el mismo layout byte a
> byte, son la misma tabla generada dos veces. Es la corroboracion interna más fuerte posible sin
> hardware, y no la habia buscado porque `1215` ya habia concluido que no habia nada que
> buscar.

## 4 · Procedimiento

```text
PREGUNTA   ¿hay una mascara que confirme ENGINE_SEL,  y hay mas mascaras
            nativas para los otros paquetes?
FUENTES    asic_reg/gca/gfx_8_0_sh_mask.h   (ENGINE_SEL: 0 ocurrencias;  los dos
           juegos de campos de CP_DMA_ME_* y CP_DMA_PFP_*)
           asic_reg/gca/gfx_8_0_d.h         (los 14 registros del bloque)
           vid.h:156                        (el enum me / pfp / ce)
MEDIDO     ENGINE_SEL como campo de registro:  0
           registros del bloque:  14,  dos motores,  ninguno para CE
           COMMAND ME vs PFP:  9 campos,  9 mascaras identicas
           CONTROL ME vs PFP:  8 campos,  8 mascaras identicas,  ninguno exclusivo
LO QUE SE CIERRA
   1215 / 1218  "ENGINE_SEL = 2 bits,  cota,  sin mascara"  ->  no es un campo:
                la seleccion es por registro.  Ausencia explicada.
LO QUE NO SE CIERRA
  - el tercer valor del enum (ce):  no hay registro.  NOT_DETERMINED.
  - si la DMA del CE existe en otro bloque de GFX8.
  - MAP_QUEUES.CONTROL2 sigue sin validar:  MAP_QUEUES escribe un puntero a MQD
    en VRAM,  no un registro  (esto es de 1219 §4).
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
```