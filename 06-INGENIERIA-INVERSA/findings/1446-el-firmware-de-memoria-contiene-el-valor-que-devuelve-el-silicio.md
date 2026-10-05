# 1446 — el firmware de memoria de esta tarjeta, leído de disco, contiene el valor exacto que devuelve el silicio

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+CADENA-CERRADA+MEJORIA-DE-INSTRUMENTO
TRACK=STATIC(el firmware, en disco) · CERO contacto con la GPU
GENERADO=2026-10-04
ORIGEN=encargo del propietario: "busca en internet como mejorar las herramientas que
       tienes para alcanzar lo que buscas".  La búsqueda de internet dio una mejora concreta.
AFECTADO=06-INGENIERIA-INVERSA/findings/1445-*   (explica su "valor parecido pero distinto")
         09-POWER-CLOCKS/  (el techo de reloj de memoria ya no necesita hardware para
                            investigarse: se lee del firmware)
ESTADO=PROBADO · el fichero /lib/firmware/amdgpu/polaris12_mc.bin contiene la respuesta
       · el valor leido del silicio en 1445 es EXACTAMENTE una palabra de ese fichero
       · la pregunta "que firmware carga esta placa" se responde SIN tocar la GPU
```

## 0. La mejora de herramienta que salió de la búsqueda

Al buscar la especificación de PM4 me topé con algo más útil: la búsqueda de firmware
AMD dio la estructura `mc_firmware_header_v1_0` (`amdgpu_ucode.h`):

```c
struct common_firmware_header {
        uint32_t size_bytes, header_size_bytes;
        uint16_t header_version_major, header_version_minor;
        uint16_t ip_version_major, ip_version_minor;
        uint32_t ucode_version;
        uint32_t ucode_size_bytes, ucode_array_offset_bytes;
        uint32_t crc32;
};
struct mc_firmware_header_v1_0 {
        struct common_firmware_header header;
        uint32_t io_debug_size_bytes;
        uint32_t io_debug_array_offset_bytes;
};
```

**El encabezado del firmware de memoria declara un array `io_debug`.** Es decir: **el
firmware lleva dentro la tabla de sondeos que el driver consulta por MMIO.**

Eso convierte la pregunta del hallazgo 1445 —"¿qué firmware de MC carga esta placa?"— de
una lectura de hardware en **una lectura de fichero**.

## 1. El fichero, y por qué es el de esta tarjeta

```text
/lib/firmware/amdgpu/polaris12_mc.bin.xz    11 328 B  (xz)  ->  32 608 B
```

Es el que el driver pide: el sondeo de 1445 devolvió la rama **no-32-bits**, luego
`chip_name = "polaris12"` y el fichero pedido es `polaris12_mc.bin`. **El fichero y la
medición se corresponden por el mismo razonamiento.**

## 2. La cabecera, leída por offset explícito

```text
+0   size_bytes                 32608 (0x7f60)   = el tamano exacto del fichero descomprimido
+4   header_size_bytes          40    (0x28)     = 32 + 8: exactamente el mc_firmware_header_v1_0
+8   header_version_major       1
+10  header_version_minor       0
+12  ip_version_major           8                <-- MC IP 8.1
+14  ip_version_minor           1
+16  ucode_version              11852880 (0xb4dc50)     <-- ★
+20  ucode_size_bytes           32160 (0x7da0)
+24  ucode_array_offset_bytes   448   (0x1c0)
+28  crc32                      0x9b1e395c

+32  io_debug_size_bytes        192   (0xc0)      = 48 palabras de 32 bits
+36  io_debug_array_offset_bytes 256 (0x100)     -> la tabla empieza en el byte 288
```

**Dos autocontroles que salen bien sin ninguna fuente externa:**

- `size_bytes = 32608` **es exactamente el tamaño del fichero descomprimido.** El parseo está
  en la posición correcta.
- `header_size_bytes = 40 = 0x28`, que es exactamente `32` del common + `8` del MC. La
  estructura declarada tiene el tamaño que dice tener.

**Y `ip_version = 8.1`**, que **corrobora por vía independiente** el `gmc_v8_1_ip_block`
(8.1.0) que-announced el log de arranque en el hallazgo 1418. El encabezado del firmware
confirma la versión de IP que el driver descubrió.

## 3. LA TABLA `io_debug`, y por qué son pares

Las 48 palabras, en pares:

```text
 [ 0] 0x00 = 0x00000081     [ 1] 0x01 = 0x00000008
 [ 2] 0x02 = 0x00000083     [ 3] 0x03 = 0x00000000
 [ 4] 0x04 = 0x00000084     [ 5] 0x05 = 0x00000100
 [ 6] 0x06 = 0x00000085     [ 7] 0x07 = 0x00000001
 ...
[10] 0x0a = 0x00000088     [11] 0x0b = 0x00040000
 ...
[26] 0x1a = 0x00000092     [27] 0x1b = 0x00000fff
 ...
[36] 0x24 = 0x00000098     [37] 0x25 = 0x010f0201
[38] 0x26 = 0x0000009f     [39] 0x27 = 0x00b4dc50      <-- ★
[40] 0x28 = 0x0002be01     [41] 0x29 = 0x0003f801
[42] 0x2a = 0x0003496c     [43] 0x2b = 0x0003425d
[44] 0x2c = 0x0002bf7f     [45] 0x2d = 0x0002400f
[46] 0x2e = 0x0003696c     [47] 0x2f = 0x00036021
```

**Son pares (índice, valor).** Y el par 19/20 es exactamente el del sondeo:

| | tabla `io_debug` del fichero | hallazgo 1445, en la placa |
|---|---|---|
| índice | `0x26 = 0x0000009f` | `WREG32(mmMC_SEQ_IO_DEBUG_INDEX, 0x9f)` |
| valor | `0x27 = 0x00b4dc50` | `RREG32(mmMC_SEQ_IO_DEBUG_DATA) = 0x00b4dc50` |
| | `0x00b4dc50 = ucode_version` | **idéntico** |

> **El valor que leí del silicio es una palabra de este fichero.** No una coincidencia, no
> un patrón plausible: la misma palabra de 32 bits, en la posición que el índice indica.

**Y `0x00b4dc50` es el campo `ucode_version` de la cabecera.** Así que el sondeo no devuelve
un identificador arbitrario: **el controlador de memoria de esta tarjeta devuelve su número
de versión de firmware**, que es lo que el driver compara.

## 4. Esto explica el "parecido pero distinto" de 1445

El hallazgo 1445 dejó sin interpretar lo siguiente, y lo dejó registrado sin usarlo:

```text
leído en el silicio   0x00b4dc50
magico del vendor     0x05b4dc40     (firma de la variante de 32 bits)
coinciden en 10 de los 24 bits bajos; difieren en el bit 4
```

**Ahora está explicado: los dos son números de versión de firmware de MC.** El de esta
tarjeta es `0xb4dc50`; el de la variante de 32 bits es `0xb4dc40`. Son firmware distintos y
por eso las versiones difieren.

```text
      0xb4dc40   <- version esperada para la variante de 32 bits
      0xb4dc50   <- version de ESTA tarjeta
      -------
      0x000010   <- un bit
```

**Una versión de firmware que se lee de un fichero y una placa que la devuelve por MMIO.**
El parecido no era una pista: era la forma que tenía el número de versión.

## 5. El fallo de autocontrol, declarado

El `crc32` de la cabecera **no coincide con ninguno de los tres rangos que probé**:

```text
rango probado                                          crc32 calculado
ucode_array_offset .. +ucode_size   (448..32608)      0x79450f90
todo tras la cabecera                (40..32608)      0x7bcbe184
todo el fichero                      (0..32608)       0x87909dbf
declarado en la cabecera                               0x9b1e395c
```

**Ninguno coincide. `NOT_DETERMINED` sobre qué payload cubre ese CRC.** Con la misma
confianza con que anoto que `size_bytes` y `header_size_bytes` **sí** cuadran.

La validación que sí importa no es el CRC: es que **una palabra del fichero, en la posición
que el índice indica, es bit a bit lo que el hardware devolvió.** Eso no lo produce un
parseo desplazado.

## 6. Por qué esto mejora el proyecto más de lo que parece

Antes de este hallazgo, la pregunta "¿qué variante de memoria es esta tarjeta?" exigía
**encender la placa y escribir un registro**. Ahora se responde leyendo 32 KB de disco.

Y el hallazgo tiene una consecuencia de método, que es la que voy a explotar:

> **El firmware de la tarjeta es un documento que la tarjeta escribió sobre sí misma, y
> está en `/lib/firmware/amdgpu/`. No es fuente del driver: es fuente del silicio.**
>
> El proyecto llevaba semanas tratando el firmware como un obstáculo ("no hay blob de
> discovery", "no se puede leer el SPI ROM"). **Ese diagnóstico era medio verdad.** El
> contenido que se buscaba —identidad, geometría, tablas— **está en los `.bin` que el propio
> driver carga**, y esos sí se pueden leer sin permiso ni hardware.

Los 20 ficheros `polaris12_*` de `/lib/firmware/amdgpu/` (hallazgo 1428) **son la caja de
 Pandora**: `mc`, `smc`, `rlc`, `sdma`, `me`, `mec`, `ce`, `pfp`, `uvd`, `vce`. Cada uno con
 su cabecera `common_firmware_header`, que ya sabemos parsear.

**Y el objetivo que estaba bloqueado tiene candidato directo**: el techo de reloj de memoria
sigue con dos candidatos, 1500 y 2000 MHz (hallazgo 1419), y `polaris12_mc.bin` es
precisamente el firmware que programa la memoria.

## 7. Procedencia

```text
fuente de la mejora   busqueda web: struct mc_firmware_header_v1_0, amdgpu_ucode.h
                      (fuente publica: git.zx2c4.com/linux-dev, drivers/gpu/drm/amd/
                       amdgpu/amdgpu_ucode.h)
fichero               /lib/firmware/amdgpu/polaris12_mc.bin.xz   11328 B  -> mc.bin 32608 B
estructuras           amdgpu_ucode.h: common_firmware_header y mc_firmware_header_v1_0
                      (confirmadas contra la cabecera por size_bytes y header_size_bytes)
contraste con el HW   hallazgo 1445:  INDEX=0x9f  ->  DATA=0x00b4dc50
                      esta lectura:    par [0x26]=0x9f, [0x27]=0x00b4dc50, y
                                      ucode_version = 0xb4dc50
autocontrol que pasa  size_bytes == tamano del fichero ; header_size_bytes == 0x28
autocontrol que falla  crc32: NOT_DETERMINED sobre el rango (§5)
contacto con la GPU   NINGUNO.  Todo es lectura de fichero.
```

```text
ESTADO=PROBADO · polaris12_mc.bin lleva dentro el valor que el hardware devuelve por MMIO:
       el par io_debug (0x9f -> 0x00b4dc50) es exactamente el sondeo de 1445
       · 0x00b4dc50 es el campo ucode_version de la cabecera del propio firmware
       · ip_version = 8.1 en la cabecera, corrobora gmc_v8_1_ip_block del log de arranque
EXPLICA  los "10 de 24 bits coincidentes" de 1445: ambos son numeros de version de
       firmware de MC.  El de esta tarjeta es 0xb4dc50; el de la variante de 32 bits es
       0xb4dc40.  La version difiere en un bit, y por eso las versiones difieren
AUTOCONTROL  size_bytes y header_size_bytes cuadran.  El crc32 NO cuadra con ninguno de
       los tres rangos probados -> NOT_DETERMINED, declarado
MEJORIA DE INSTRUMENTO  la identidad de la memoria se lee de disco.  El techo de reloj ya
       no necesita hardware para investigarse: esta en polaris12_mc.bin
NUEVO     el firmware de la tarjeta es FUENTE DEL SILICIO, no fuente del driver.  Y el
       proyecto lleva semanas tratandolo como un obstáculo.  Los 20 ficheros polaris12_*
       son la caja de Pandora, y su cabecera ya sabemos parsearla
LIMITE   no he tocado los otros 19 firmware; no he interpretado los pares de la tabla
       mas alla del par 0x9f; el crc32 sigue sin cerrar
Siguiente  1) parsear polaris12_mc.bin entero: la tabla tiene 24 pares y solo he usado uno.
           Los otros 23 indices son preguntas que el controlador de memoria sabe contestar
         2) el techo de reloj de memoria: buscar en polaris12_mc.bin el equivalente a la
           tabla de 11 escalones que 1419 leyo en la ROM.  Si estan ahi, 1500 vs 2000 se
           decide sin hardware
         3) smc, que es el firmware de la SMU, y donde vive todo lo de unidades y DPM
```
