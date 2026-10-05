# 1545 — la magia del driver es el `ucode_version` del otro firmware, y el índice que faltaba es el 0x9F

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, item 5
CLASSIFICATION=EVIDENCIA-DE-DISCO+CIERRE-DE-DOS-HUECOS-NOMBRADOS
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
CIERRA=los DOS huecos que el 1539 dejo abiertos sobre el sondeo de variante
ESTADO=PROBADO · los dos blobs parsean y sus arrays tetran el fichero EXACTAMENTE
       · polaris12_mc.bin     ucode_version = 0x00B4DC50   (32608 B, ip 8.1)
       · polaris12_32_mc.bin  ucode_version = 0x05B4DC40   (32876 B, ip 8.1)
       · la MAGIA del driver es 0x05B4DC40 = EXACTAMENTE la version del firmware de 32 bits
       · ixMC_IO_DEBUG_UP_159 = indice 0x9F = 159 decimal.  El hueco del 1539, cerrado
       · y la entrada 23 de la tabla io_debug del propio firmware es ese indice, con esa version
       · el bucle queda cerrado: el driver lee la version que el firmware declara sobre si mismo
```

## 1. Que abria el 1539, textual

Ese hallazgo cerraba la contradiccion del ancho de bus y dejo dos cosas sin resolver:

> **Un detalle que no encaja y no voy a forzar:** la magia del driver es `0x05b4dc40` y el valor leido
> fue `0x00b4dc50`. Comparten los bytes `b4dc` y difieren en el byte alto y en el ultimo. Si el
> registro fuera la version del ucode de MC, dos cargas del mismo firmware darian el mismo valor. **No
> se si son el mismo registro, leidos en momentos distintos, o dos registros distintos.**

> **El hueco, y es el mas concreto de la parte:** `ixMC_IO_DEBUG_UP_159` se usa una vez y no esta
> definido en ningun header. **Sin ese numero la sonda no se puede reproducir sin hardware.**

Los dos son resolubles leyendo el blob, que esta en disco. Eso es lo que he hecho.

## 2. El blob parsea, y sus arrays tetrcean el fichero

`common_firmware_header` (`amdgpu_ucode.h:30`) y `mc_firmware_header_v1_0` (`amdgpu_ucode.h:44`).
Todo little-endian. `polaris12_mc.bin`, descomprimido de su `.xz`:

```text
  size_bytes                = 32608
  header_size_bytes         = 40
  header_version            = 1.0
  ip_version                = 8.1          <-- el GMC aplicable es 8.1, no 8.2
  ucode_version             = 0x00B4DC50
  ucode_size_bytes          = 32160
  ucode_array_offset_bytes  = 448
  io_debug_size_bytes       = 192
  io_debug_array_offset     = 256
```

Y la comprobacion que hace fiable el parseo, sin la cual lo demas no valeria nada:

```text
  io_debug  @ 256 + 192  =  448
  ucode     @ 448 + 32160 = 32608
  size_bytes declarado    = 32608 = tamano real del fichero
```

**El fichero queda cubierto entero, sin huecos ni solapes, y el total declarado coincide con el
tamano en disco.** Cualquier error de offset habria roto esa cuenta.

## 3. La magia: cerrada

Comparo los dos blobs que el driver declara:

```text
  polaris12_mc.bin       32608 B   ip 8.1   ucode_version = 0x00B4DC50
  polaris12_32_mc.bin    32876 B   ip 8.1   ucode_version = 0x05B4DC40
```

Y el driver (`gmc_v8_0.c:247`):

```c
  if (RREG32(mmMC_SEQ_IO_DEBUG_DATA) == 0x05b4dc40)
          chip_name = "polaris12_32";
```

> **PROBADO: la constante `0x05b4dc40` del driver es, literalmente, el `ucode_version` del firmware
> `polaris12_32_mc.bin`.**

Con eso se resuelve el detalle que el 1539 dejo abierto: **si y la misma magnitud, la version del
ucode de MC, de dos firmwares distintos.** No es un registro raro ni dos registros. Los bytes `b4dc`
que ambos comparten son una familia de versiones de AMD, no una coincidencia que hubiera que explicar.

Y gana fuerza con la tercera fuente: el `1445` leyo `0x00b4dc50` en el silicio de esta placa, que es
**exactamente** el `ucode_version` de `polaris12_mc.bin`. El valor medido en el hardware y el del
fichero en disco coinciden bit a bit.

## 4. El índice que faltaba: cerrado

La tabla `io_debug` del blob son **192 bytes = 24 registros** (el driver lo calcula como
`io_debug_size_bytes / (4*2)`, `gmc_v7_0.c:192`). Y **la entrada 23 es el índice 0x9F con el valor de
la versión**:

```text
  idx   indice       valor
   ...
   22   0x000098   0x010F0201
   23   0x00009F   0x00B4DC50   <-- la version, el mismo valor de la cabecera
```

**24 registros, y el `1447` midio 24 pares.** Coinciden exactamente.

Y el nombre del símbolo lo descifra solo: `ixMC_IO_DEBUG_UP_159`. **`UP` es el microprocesador, y 159
decimal es 0x9F.** El driver escribe el índice **0x9F** (`gmc_v8_0.c:245`) y lee por `DATA` el valor
que el propio firmware pone ahi.

> **PROBADO: `ixMC_IO_DEBUG_UP_159` = 0x9F.** No hace falta hardware para obtenerlo: la tabla del
> firmware lo nombra por posicion.

## 5. Y el bucle queda cerrado sobre si mismo

Esta es la forma, y merece decirse con todas las piezas:

```text
  el firmware declara su propia version      -> en su cabecera, offset 16
  el firmware la publica tambien             -> en su tabla io_debug, entrada 23, indice 0x9F
  el driver escribe el indice 0x9F           -> gmc_v8_0.c:245
  el driver lee el valor                     -> gmc_v8_0.c:247
  el driver lo compara con la version del
    firmware de la OTRA variante             -> 0x05b4dc40, el ucode_version de polaris12_32_mc.bin
```

**El driver decide que variante de chip tiene leyendo lo que el firmware dice de si mismo, por un
indice que el propio firmware usa para publicar su version.** Es un circuito cerrado, y no requiere
ninguna tabla de configuracion, ningun registro de configuracion y ningun campo del ROM.

Eso explica tambien por que el 1445 no tenia otra via: la sonda **es** la lectura del firmware, y sin
el firmware cargado no hay nada que leer.

## 6. Una trampa que aqui si evite, y que el 1537 ya me habia enseñado

Los 24 indices van de `0x00007C` a `0x00009F`. **Ninguno tiene nombre en el header del bloque GMC**, y
podria parecer el mismo caso que las 160 escrituras sin nombre del 1537.

No lo es, y la diferencia es de espacio de nombres:

- las 160 escrituras del 1537 escriben a **direcciones MMIO** de la ventana del GMC, y ahi buscar un
  nombre en `gmc_8_1_d.h` es lo correcto
- estos 24 indices son **indices del fichero de registros interno del MC**, que es lo que acepta
  `mmMC_SEQ_IO_DEBUG_INDEX`. El driver escribe indice y lee `DATA`. **No son direcciones y no se
  resuelven contra un header de offsets; no hay nombre que buscar.**

Lo dejo escrito porque el error es facil y yo lo cometi ayer con los bloques cruzados: un
`0x00007C` sin nombre **no es un registro sin documentar, es un indice de otro espacio de nombres**.

## 7. Donde queda el item 5

```text
  el blob de MC parsea y es coherente de extremo a extremo      PROBADO
  su cabecera, ip 8.1, ucode_version 0x00B4DC50                 PROBADO
  la tabla io_debug tiene 24 entradas, con la version al final  PROBADO
  ixMC_IO_DEBUG_UP_159 = 0x9F                                   PROBADO, sin hardware
  la magia del driver = ucode_version del firmware de 32 bits  PROBADO, bit a bit
  el 1445 leyo en el silicio el valor del fichero de disco      CORROBORADO
  los 24 indices de io_debug                                   SIN RESOLVER, y no resolubles:
                                                              son otro espacio de nombres
  que hacen los otros 23                                        NOT_IN_CORPUS
RIESGO         ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE         lectura de un fichero de /lib/firmware.  El fichero es del paquete del
               distribucion, versionado por el sistema, y su hash es reproducible.
```

**El item 5 pasa de PARCIAL a medido en su parte estructural.** Lo que queda —que hacen los otros 23
indices y que hace el ucode— es codigo de microcontrolador, y no esta en ningun sitio del proyecto.

## 8. Decision log (§103)

```text
DECISION    cerrar los dos huecos del 1539 y declarar el item 5 medido en su estructura
WHY         los dos eran NOT_DETERMINED con el productor nombrado, y el productor estaba en disco.
            §95 pide decir que falta, quien lo produce y con que observable: aqui la respuesta
            era "el fichero .xz del propio paquete del firmware", y no se habia mirado.
ALTERNATIVA  no tocarlo, porque el 1539 ya declaraba 128 bits y el ancho no dependia de esto.
            Descartada: el 1539 dejo dos huecos explicitos, y dejarlos porque el claim principal
            ya estaba es exactamente el patron que tu senalaste.
DISCriminante  ninguno.  El valor de la magia del driver y el del ucode_version del otro blob
            son el mismo numero de 32 bits.  No hay hipotesis que separar.
CONSECUENCIA  el 1539 queda sin huecos, y el item 5 con su estructura medida.  Ademas queda
            documentado que la sonda de variante no necesita hardware para reproducirse: se
            puede simular con el fichero.
REVERSIBLE  no.  La igualdad de dos valores de 32 bits no admite interpretation.
```
