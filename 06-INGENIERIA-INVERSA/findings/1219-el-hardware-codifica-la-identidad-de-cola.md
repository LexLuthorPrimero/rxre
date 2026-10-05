# 1219 — El hardware codifica la identidad de cola en un registro, con **máscaras de GFX8**: `CP_ECC_FIRSTOCCURRENCE`. `PIPE` = 2 bits y `QUEUE` = 3 bits, quinta y segunda corroboracion

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · CORROBORATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CONTINUA   1218:  el header de REGISTROS de GFX8 tiene mascaras nativas,  y es
             donde hay que mirar para validar campos de paquete
CIERRA     una de las dos diferencias que 1218 dejo abiertas
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · El método, y por qué este registro

`1218` cerró el método: los campos de paquete están declarados otra vez, **con máscara**, en
`asic_reg/gca/gfx_8_0_sh_mask.h`. La pregunta siguiente es qué registro del CP corresponde a cada
palabra de paquete.

Y aparece uno que no es un caso cualquiera: **`CP_ECC_FIRSTOCCURRENCE` no implementa un paquete,
sino que codifica la identidad de la cola que el hardware está atendiendo.** Es el hardware
diciendo, con su propia codificación, qué `ME`, `PIPE`, `QUEUE` y `VMID` está usando. Los mismos
cuatro campos que `MAP_QUEUES` empaqueta, con la diferencia de que **este viene con máscara**.

```text
  gfx_8_0_d.h:290   mmCP_ECC_FIRSTOCCURRENCE   0x307a
```

## 1 · Los seis campos, con su máscara y su hueco

```text
  campo        mascara     bits        ancho   hueco antes
  INTERFACE    0x00003    [ 1:0 ]      2 bits
  CLIENT       0x000f0    [ 7:4 ]      4 bits     2 bits sin campo  [3:2]
  ME           0x00300    [ 9:8 ]      2 bits
  PIPE         0x00c00    [11:10]      2 bits
  QUEUE        0x07000    [14:12]      3 bits
  VMID         0xf0000    [19:16]      4 bits     1 bit sin campo   [15]
```

## 2 · El cruce con `MAP_QUEUES`

Lo que `vid.h` empaqueta y lo que el hardware registra, campo a campo:

```text
  campo    en el PAQUETE (vid.h)     ancho por      ancho en el
                                       desplazamiento  REGISTRO     veredicto
  ------------------------------------------------------------------------------
  ME       bit [31]                       1             2        DIFERENTE
  PIPE     bits [30:29]                   2             2        EXACTO
  QUEUE    bits [28:26]                   3             3        EXACTO
  VMID     bits [20:8]                   13             4        el registro es menor
```

**Dos exactos.** `PIPE` = 2 bits por quinta vía, y esta es la primera que sale de un **registro de
GFX8 con máscara declarada**, no de un desplazamiento ni de un censo de nombres. `QUEUE` = 3 bits
por segunda vía, después del ajuste exacto con `num_queue_per_pipe = 8`.

## 3 · `ME`: 1 bit en el paquete, 2 en el registro. No lo declaro contradiction

Es la diferencia que `1218` no pudo cerrar, y hay que tratarla con cuidado porque **no son la misma
magnitud**:

```text
  EL PAQUETE     MAP_QUEUES.ME  ocupa el bit [31].  El driver escribe
                 ring->me == 1 ? 0 : 1   (gfx_v8_0.c:4353),  o sea un valor de
                 DOS opciones.  1 bit es el minimo exacto para eso.

  EL REGISTRO    CP_ECC_FIRSTOCCURRENCE.ME  son 2 bits,  o sea hasta cuatro.

  Y 1206   demostro que en GFX8 ring->me = mec + 1  y  que en Polaris12
           num_mec = 2,  de modo que me solo toma los valores 1 y 2  y
           MAP_QUEUES los codifica como 0 y 1.

  ASI QUE    el paquete codifica un MENÚ de dos opciones —cual de los dos
             MEs usar— y el registro REPORTA un índice fisico de hasta
             cuatro.  Que el hardware tenga cuatro MEs posibles en esta
             familia es coherente con que el mismo header nombre
             CP_CONTEXT_CNTL__ME0PIPE0  y  CP_CPC_BUSY_STAT__MEC1_*  y MEC2_*.

  ESTADO       que el paquete usa 1 bit y el registro 2 es OBSERVADO.
               que eso es porque son magnitudes distintas es la
               INTERPRETACION,  y es NOT_DETERMINED.  No lo subo a
               conclusion sin leer el registro.
```

`VMID` es el caso limpio del patrón de `1218`: desplazamiento da 13, el registro da 4. Cuatro bits
son exactamente dieciséis VMID, que es el número que tiene un GFX8. El 13 era cota por arriba, y
encaja con el «sobrestima la mitad de las veces» de `1218`.

## 4 · Dos resultados negativos, que también son resultado

```text
  CP_WAIT_REG_MEM    existe el registro  (mmCP_WAIT_REG_MEM)  y DECLARA CERO
                     campos en gfx_8_0_sh_mask.h.  El layout de
                     WAIT_REG_MEM por esta via no se puede validar.  NEGATIVE_RESULT
                     con causa nombrada.

  CP_MQD             existen 3 registros.  MAP_QUEUES no tiene un registro que lo
                     implemente,  porque MAP_QUEUES no escribe un registro:
                     escribe un PUNTERO  (MQD_ADDR)  a un MQD que esta en
                     VRAM.  No es un layout que se pueda validar con mascaras de
                     registro:  es una escritura a memoria.
                     Es la razon por la que CONTROL2 se queda sin validar.
```

El segundo es más interesante que un resultado negativo: **explica por qué `MAP_QUEUES.CONTROL2`
—incluido `DOORBELL_OFFSET`, el único `NOT_DETERMINED` grande que me queda de `1217`— no se puede
cerrar por esta vía.** No es que falte información: es que el objeto es memoria, y las máscaras de
registro no lo cubren.

## 5 · Procedimiento

```text
PREGUNTA   ¿que registro del CP corresponde a cada palabra de paquete, y hay
            mascaras nativas para PIPE, ME, QUEUE y VMID?
FUENTES    asic_reg/gca/gfx_8_0_d.h:290   (mmCP_ECC_FIRSTOCCURRENCE 0x307a)
           asic_reg/gca/gfx_8_0_sh_mask.h (los 6 campos con mascara)
           vid.h:400-405                   (los mismos campos en el paquete)
           gfx_v8_0.c:4353                (que valores pasa el driver)
MEDIDO     6 campos en el registro,  2 huecos  ([3:2] de 2 bits, [15] de 1)
           PIPE    2 vs 2   EXACTO
           QUEUE   3 vs 3   EXACTO
           ME      1 vs 2   OBSERVADO,  interpretacion NOT_DETERMINED
           VMID   13 vs 4   cota por arriba,  y 4 bits = 16 VMID
NEGATIVOS  CP_WAIT_REG_MEM declara 0 campos
           MAP_QUEUES escribe un puntero a MQD en VRAM,  no un registro:
           su CONTROL2 no es validable con mascaras de registro
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE ABIERTO
  - leer CP_ECC_FIRSTOCCURRENCE y ver si ME trae 2 o 4:  eso separa las dos
    lecturas de §3.  Es RUNTIME,  y es una lectura sola.
  - el valor real de ME que el hardware escribe cuando se mapea una cola en
    esta placa:  con num_mec=2 solo hay dos MEs,  asi que el bit alto deberia
    ser 0.  Si no lo es,  el modelo de 1206 esta incompleto.
  - DOORBELL_OFFSET sigue sin cota superior,  y §4 dice por que.
```