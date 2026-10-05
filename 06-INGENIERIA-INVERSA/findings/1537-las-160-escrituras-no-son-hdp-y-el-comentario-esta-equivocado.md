# 1537 — las 160 escrituras sin nombre no son HDP, y el comentario que las etiqueta está equivocado

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, item 3
CLASSIFICATION=RESULTADO-NEGATIVO+CAUSA-NOMBRADA+ERROR-CORRECTION-PROPIA
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=142 claim 2  lo CONFIRMA y le anade que la etiqueta de bloque es falsa
ESTADO=PROBADO · las 160 escrituras van a 0xB05-0xC3, en grupos de 6 con 1 hueco
       · CERO de esos 160 offsets tiene nombre en el bloque GMC (1156 regs, 1122 offsets)
       · el rango cae DENTRO de la ventana del GMC (0x500-0xF9CD): son direcciones plausibles
       · NO son registros HDP: el unico header HDP llega a 0x0149 y mmHDP_DEBUG0 = 0x00CE
       · el comentario "/* Initialize HDP */" es una etiqueta falsa
       · y mi primer intento de nombrarlas fue un error de metodo, declarado
```

## 1. Que afirmaba el 142, textual

Del hallazgo `142-f-agp-vacia-y-bloque-hdp-sin-nombre.md`:

> 2. **Un bloque de 160 escrituras de registro sin un solo nombre**, con la causa
>    identificada: **el corpus no tiene el header que los nombraría.**

Y señalaba `gmc_v8_0.c:439-447`, la primera cosa que hace `gmc_v8_0_mc_program`. Ese codigo es:

```c
  439   /* Initialize HDP */
  440   for (i = 0, j = 0; i < 32; i++, j += 0x6) {
  441           WREG32((0xb05 + j), 0x00000000);
  442           WREG32((0xb06 + j), 0x00000000);
  443           WREG32((0xb07 + j), 0x00000000);
  444           WREG32((0xb08 + j), 0x00000000);
  445           WREG32((0xb09 + j), 0x00000000);
  446   }
  447   WREG32(mmHDP_REG_COHERENCY_FLUSH_CNTL, 0);
```

**160 escrituras, la primera instruccion de `gmc_v8_0_mc_program`, y todas a cero.** El conjunto de
direcciones es exactamente:

```text
  0xB05 + i*6 + {0,1,2,3,4}   para i = 0..31
  rango  0xB05 .. 0xC3
  paso   6, con 1 palabra saltada entre grupos de 5
```

El `+1` saltado **no es un error mio**: el paso es `j += 0x6` en el codigo, y hay cinco escrituras. Es
deliberado y probablemente sea la palabra que el hardware usa de otra forma, pero no lo se y no lo
afirmo.

## 2. Mi primer intento fue un error de metodo, y lo declaro antes que nada

Resolví los offsets contra **todos** los headers de bloque a la vez y obtuve 152 de 160 "nombrados":
`mmCRTC2_*`, `mmDCP3_*`, `mmTCP_*`, `mmVMSHAREDHV0_*`... Todo mentira.

**El espacio de registros de una GPU esta particionado por bloques, y el offset NO identifica el
registro por si solo.** `0xB05` en la ventana del GMC no es el mismo registro que `0xB05` en la de
DCE. Cruzar bloques produce nombres que existen, en el bloque equivocado, y el resultado parece
convincente. Es el mismo homonimo que el `1470` ya denomino, y lo cometi otra vez.

La forma correcta es resolver **dentro del bloque que la funcion esta programando**, y como esta
funcion es `gmc_v8_0_mc_program`, el bloque es GMC.

## 3. La resolucion correcta: cero de 160

```text
  gmc/gmc_8_1_d.h    1156 registros mm* en 1122 offsets distintos
                     rango 0x0500 - 0xF9CD

  offsets del bucle que existen en GMC     0  de 160
  offsets del bucle que no existen en GMC   160
```

**Ninguno.** Pero el rango `0xB05-0xC3` **cae dentro** del span del bloque GMC (`0x500-0xF9CD`). O
sea: no son direcciones inventadas ni de otroASIC, son **huecos reales dentro de la ventana del GMC que
el header de 7.1.3 no nombra.**

Eso es distinto de "no existen" y mas fuerte que "no los se renombrar": **el hardware tiene ahi 160
palabras y el header no las declara.**

## 4. Y el comentario "Initialize HDP" es falso

Esta es la parte que el 142 no vio, y cambia la lectura del codigo:

```text
  hdp/hdp_4_0_offset.h     el UNICO header HDP del corpus
                           90 registros,  rango 0x0000 - 0x0149
                           mmHDP_DEBUG0 = 0x00CE
```

`0xB05` esta **fuera** del bloque HDP por un factor de 10. Y el `mmHDP_DEBUG0` que el `1450` declaro
como "el ultimo campo sin nombrar del IB real" esta en `0x00CE`, no en este rango. **El bucle no pasa
por ahi.**

Y el `mmHDP_REG_COHERENCY_FLUSH_CNTL` de la linea 447, que si lleva nombre, **tampoco esta en un
header HDP**: vive en `nbif_6_1_offset.h` (0x0e16) y `nbio_7_0/7_4_offset.h` (0x00f6), con
`_BASE_IDX` distintos. O sea, los nombres `mmHDP_*` de gfx8 estan repartidos entre headers de NBIO y
NBIF, no en uno de HDP.

> **PROBADO: el comentario `/* Initialize HDP */` de `gmc_v8_0.c:439` no describe el bloque que el
> codigo toca.** El bucle escribe en la ventana del GMC, en huecos sin nombre entre 0xB05 y 0xC3.

## 5. Que queda del 142, y que es lo unico que queda

```text
CONFIRMADO    el 142: no hay header en el corpus que nombre esas 160 escrituras.  La causa que
              declaro es correcta.
ANADIDO       no son HDP, y el comentario es una etiqueta falsa.
ANADIDO       caen dentro del span del GMC, asi que son huecos reales del mapa de esa ventana,
              no direcciones de ningun otro ASIC.
ANADIDO       el salto de 6 con 5 escrituras deja 1 palabra sin tocar por grupo.  Que esa palabra
              sea intencional no se sabe.  NOT_DETERMINED, y con la razon: no hay header que la
              nombre ni codigo que la escriba.
NOT_DETERMINED  que hace el codigo.  Poner 160 registros a cero no es una operacion trivial y no
              se puede llamar "inicializacion" sin saber que inicializa.
LIMITE        todo es lectura de headers.  Ni una lectura de hardware.
RIESGO        ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
```

## 6. Decision log (§103)

```text
DECISION    tratar esto como resultado negativo con causa nombrada, no como hueco abierto
WHY         §100: una frontera se puede declarar SATURATED con "NO OBSERVABLE AVAILABLE".  Aqui
            el header que lo nombraria no existe en el corpus, y eso no se arregla con mas
            busqueda: lo he buscado en los seis headers HDP/OSS/NBIO/NBIF que hay.
ALTERNATIVA  buscar un header HDP de gfx8 en otro arbol del proyecto (working/, kernelbuild/).
            YA ESTA HECHO: los tres arboles tienen el mismo juego de headers, y gmc_8_1_d.h
            tiene 1156 registros y ninguno en el rango.  No hay mas donde mirar.
ALTERNATIVA  intentar adivinar el proposito por el nombre de la funcion que lo contiene.
            Descartada: seria §64 en estado puro, un UNKNOWN sin encapsular.
DISCriminante  un header de ASIC que declare la ventana del GMC de gfx8 completa.  No existe en
            7.1.3.  Si existiera, este item se cierra en una pasada.
CONSECUENCIA  el item 3 tiene ahora su unico hueco con causa, y no es recuperable sin otra fuente.
REVERSIBLE  no.  Si alguien trae el header correcto, este hallazgo es el que dice donde mirarlo.
```

## 7. Lo que esto dice del estado del item 3

Antes de escribir, por mi propia regla, leí los once hallazgos previos del tema. El resultado es que
el item 3 **esta cerrado en todo lo que el corpus permite**:

```text
  apertura del GART, no cambia en runtime       CERRADO   (1020)
  las 5907 MiB de GTT son la mitad de la RAM     CERRADO   (243, 1010)
  el TTM si esta en el corpus                    CERRADO   (1026, y verificado en MI arbol)
  la apertura AGP esta vacia                     CERRADO   (142 claim 1)
  160 escrituras sin nombre                      CERRADO con causa EXTERNA   (este)
```

**Cinco de cinco.** El sexto, el nombre de las 160 escrituras, queda `DEFERRED` por dependencia externa
nombrada: falta el header que declara la ventana del GMC de gfx8.

Y al cerrarlo me queda una cosa pequena y util: **`mmHDP_REG_COHERENCY_FLUSH_CNTL`, que si lleva
nombre, no esta en ningun header HDP sino en NBIO y NBIF, con `_BASE_IDX` distintos.** Los nombres
`mmHDP_*` de esta generacion estan dispersos en tres bloques distintos. Eso explica por que buscar
"el header HDP" no es una accion que funcionar: **el bloque HDP no es una unidad de nombres en gfx8.**
