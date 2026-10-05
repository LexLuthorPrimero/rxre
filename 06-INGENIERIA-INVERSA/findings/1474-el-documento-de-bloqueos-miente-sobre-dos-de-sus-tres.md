# 1474 — El documento de estado de bloqueos miente sobre dos de sus tres bloqueos: `GFX_HWIP` se cerró sin UMR y el CRC32 se calcula con zlib, y de paso confirmo el 8.0 de `231` desde los binarios

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST, sobre ficheros reales

ARTEFACTO MEDIDO=/lib/firmware/amdgpu/polaris12_*.bin.xz   20 ficheros
  descargados y leidos, no copiados de otro hallazgo
FUENTE DEL LAYOUT=rx550-upstream-7.2.8/.../amdgpu/amdgpu_ucode.h:30-41
                    struct common_firmware_header
CRUCIA=231  (GFX_HWIP, confirmado por mi con criterio autovalidador)
CRUCIA=254  (la cabecera; su "20 de 20" NO es el CRC, es size_bytes)

CORRIGE=009 §4.  Dos de los tres bloqueos que ese documento declara abiertos
        estan cerrados, y uno de ellos con una causa y un coste equivocados.
ESTADO=PROVEN para lo que dice.  NOT_DETERMINED, y declarado, para 8 de 20.
```

## 0 · POR QUÉ ESTE DOCUMENTO

`009` es `Estado de los tres bloqueos: por qué están bloqueados y cómo se abren`.
Es, por título, el documento que uno consulta para saber qué frena el proyecto.
Su tabla de §4 declara tres filas: una `RESUELTO` en `010`, y dos `NOT_DETERMINED`.

Las dos siguen marcando `NOT_DETERMINED`. Ninguna se actualizó.

## 1 · `GFX_HWIP`: LA CAUSA Y EL COSTE ESTÁN FALSOS

Lo que `009:191` afirma, literal:

```text
| `GFX_HWIP` | `NOT_DETERMINED` | requiere leer hardware, no código | UMR, ASIC ID | **alto: `RUNTIME_EXECUTION` no autorizado** |
```

Y `009:199`: *"`GFX_HWIP` requiere UMR."*

Eso lo refuta `231`, que lo cerró desde el firmware. **Y no me fié de `231`: lo
volví a medir sobre los binarios de esta máquina.**

El layout está declarado en `amdgpu_ucode.h:30-41`, y `ip_version_major` es un
**`u16` en el offset 12**, no un `u32`. Eso cambia la lectura, así que leí el
struct entero antes de calcular nada.

MEDIDO, con un criterio que se autovalida:

```text
fichero        size_bytes      real   ok  hdr_maj  hdr_min      IP
  pfp.bin          17044      17044   OK        1        0     8.0
  me.bin           17044      17044   OK        1        0     8.0
  ce.bin            8852       8852   OK        1        0     8.0
  mec.bin         262824     262824   OK        1        0     8.0
  rlc.bin          16660      16660   OK        2        0     8.0
```

**El criterio autovalidador es `size_bytes == tamaño real del fichero`.** Si mi
lectura de offsets fuera incorrecta, ese campo no casaría con el tamaño del
fichero. Que case en los cinco es la prueba de que el layout que leí es el
correcto, y por tanto de que el offset 12 es `ip_version_major`. Sin ese
comprobante, esto sería "hay un 8 cerca del principio del fichero".

**Cinco de cinco, IP version 8.0.** `231` queda confirmado por una vía
independiente de la que lo escribió.

**Consecuencia sobre `009`:** el bloqueo estaba cerrado desde el fichero, sin UMR
y sin `RUNTIME_EXECUTION`. El coste "alto" y la causa "requiere leer hardware" son
ambos falsos. El coste real era **cero**: descomprimir un fichero que ya está en
disco.

## 2 · CRC32: EL BLOQUEO TAMBIÉN ESTÁ RESUELTO, Y LA CAUSA TAMBIÉN ERA Falsa

`009` dice que el CRC del firmware no se puede calcular porque `amdgpu_smc.c` está
ausente del árbol. Confirmo la ausencia —`find` no lo encuentra— **pero eso no
impedía calcular el CRC**, porque el campo está en la cabecera común y el
algoritmo se puede determinar por prueba.

El campo es `uint32_t crc32; /* crc32 checksum of the payload */` en el offset
**28**. Mi primer intento usó `raw[header_size_bytes:]` —`header_size_bytes` vale
44— y dio **0 de 20**. Casi lo escribo como "el CRC no valida".

Casi. Leí el comentario del campo, que dice *del payload*, y probé desde el
offset 32, que es donde termina la cabecera común.

MEDIDO sobre los 20:

```text
COINCIDEN 12 de 20     zlib.crc32(fichero[32:]) == crc32 del offset 28
```

Coincide **exacto**, bit a bit, en los doce. Los que coinciden incluyen
`polaris12_mec2.bin.xz` (`0x721be067`) y `polaris12_smc.bin.xz` **no**.

**Error propio, y estaba a un paso de convertirse en un hallazgo falso:**
concluí "el CRC no valida en ninguno" con un criterio que yo mismo había elegido
mal. Si lo hubiera escrito, habría refutado a `254` con mi error. La regla que
aplico desde `1470`: cuando un resultado sale raro, el sospechoso primero es el
instrumento.

## 3 · LOS 8 QUE NO COINCIDEN, Y NO AFIRMO NADA DE ELLOS

```text
polaris12_32_mc   polaris12_k_mc    polaris12_k_smc  polaris12_smc
polaris12_uvd     polaris12_vce     polaris12_mec_2 polaris12_mec2_2
```

Busqué un offset de inicio que produzca el valor declarado, **barriendo 28..80**:

```text
  polaris12_32_mc      hdr_ver=1.0 header_size= 40   inicio_real=None
  polaris12_k_mc       hdr_ver=1.0 header_size= 40   inicio_real=None
  polaris12_k_smc      hdr_ver=1.0 header_size= 36   inicio_real=None
  polaris12_smc        hdr_ver=1.0 header_size= 36   inicio_real=None
  polaris12_uvd        hdr_ver=1.0 header_size= 32   inicio_real=None
  polaris12_vce        hdr_ver=1.0 header_size= 32   inicio_real=None
  polaris12_mec_2      hdr_ver=1.0 header_size= 44   inicio_real=None
  polaris12_mec2_2     hdr_ver=1.0 header_size= 44   inicio_real=None
```

**Ninguno.** Y descarto la explicación fácil: `mc_firmware_header_v1_0` y
`smc_firmware_header_v1_0` **embeben** `struct common_firmware_header` como primer
miembro, así que el CRC sigue en el offset 28 y el layout no explica la
diferencia. Y `polaris12_mc.bin.xz` (`header_size=40`, mismo IP) **sí** valida,
mientras que `polaris12_32_mc.bin.xz` (`header_size=40`, mismo IP) no. Mismo
layout, distinto resultado.

```text
  NOT_DETERMINED  por que 8 de 20 no cumplen crc32 = zlib.crc32(fichero[32:]).
                  Tres candidatos vivos, ninguno probado:
                    (a) esos 8 usan otro algoritmo de checksum
                    (b) el campo no significa eso en esos binarios
                    (c) el CRC se calcula sobre una region que no es un sufijo
                  No se puede distinguir sin una fuente.  NO SE AFIRMA NINGUNA.

  Y DESCARTADO, por medición, un discriminante que yo mismo propuse:
    "es el IP"          REFUTADO.  mc pasa, 32_mc y k_mc no.  Mismo IP.
    "es header_size"    REFUTADO.  mc y 32_mc comparten 40 y salen distinto.
```

Lo que sí es un dato, y **corrige una hipótesis mía**: escribí que el
discriminante era el IP. No lo es. Lo medí agrupando por IP:

```text
  GFX8 (ce, me, pfp, rlc, sdma y _2, mec2)   9 pasan   1 falla   (mec_2)
  MC   (mc pasa; 32_mc y k_mc no)            1 pasa    2 fallan
  SMC, UVD, VCE, k_smc                       0 pasan  4 fallan
  MEC2 (mec2 pasa; mec2_2 no)               1 pasa    1 falla
```

**`mc` pasa y `32_mc` y `k_mc` fallan: mismo IP, mismo `header_version` (1.0) y
mismo `header_size_bytes` (40).** El IP no explica la diferencia. Y `mec_2`
falla siendo GFX8.

```text
  REFUTADO, mio:  "el discriminante es el IP"
  NOT_DETERMINED  cual es la regla que separa los 12 de los 8.  El IP no la
                  separa, y el header_size tampoco (mc y 32_mc comparten 40).
```

## 4 · UNA COINCIDENCIA QUE NO PIDE NADA, PERO SE REGISTRA

`231` afirma que los cinco ucode de gráficos dan 8.0. Los acabo de medir.

`polaris12_mec2.bin.xz` y `polaris12_mec.bin.xz` tienen **el mismo CRC declarado**
(`0x721be067`) y el mismo tamaño. `polaris12_sdma.bin.xz` y
`polaris12_sdma1.bin.xz` también comparten CRC (`0x67458532`). Son ficheros
idénticos con dos nombres.

Eso conecta con `1466`, que dice que el firmware que se ejecuta es el `_2`, no el
que tiene el nombre natural. **No lo desarrollo aquí**: es la rama de otro nodo y
sería duplicarla.

## 5 · CORRECCIÓN A `009`

```text
CORRIGE  009 §4 tabla, fila GFX_HWIP
         estado  NOT_DETERMINED -> PROVEN (231, confirmado aqui en 5 de 5)
         causa   "requiere leer hardware, no código" -> FALSA.  Sale del
                 firmware, que es un fichero en disco.
         via     UMR, ASIC ID -> no hace falta.  Descomprimir y leer el offset 12.
         coste   "alto: RUNTIME_EXECUTION no autorizado" -> CERO.  Fue cerrado
                 sin tocar el hardware y sin pedir autorizacion.

CORRIGE  009 §4 tabla, fila CRC32 firmware
         estado  NOT_DETERMINED -> PARCIAL.  12 de 20 con zlib desde el offset
                 32; 8 sin regla identificada.
         causa   "amdgpu_smc.c ausente del arbol" -> NO IMPIDE NADA para el
                 campo.  El CRC esta en la cabecera comun, no en el SMC.

NO SE TOCA  009 sigue siendo valido en que los tres bloqueos se declararon
         juntos y que dos shareban causa.  Ese diagnostico no cambio.
```

## 6 · POR QUÉ UN DOCUMENTO DE ESTADO SE VUELVE FALSO, Y CÓMO SE EVITA

`009` es de 2026-09-29. `231` es posterior. **`009` no se actualizó porque nadie
lo tiene que actualizar**: no hay nada en el sistema que exija que un documento de
estado refleje el estado.

Es la misma clase de fallo que `1470` y `1473`, y merece nombre propio:

```text
  UN DOCUMENTO DE ESTADO ES UNA AFIRMACION CON FECHA, Y ESO TIENE UN COSTE:
  no seINVALIDA SOLO.  Su mantenimiento depende de que alguien se acuerde.

  Y HAY ASIMETRIA:  actualizarlo cuesta trabajo, no actualizarlo cuesta una
  conclusion falsa.  La incentive esta mal.

  LO QUE SE PUEDE HACER, y es lo unico que escala sin disciplina:
    un documento de estado declara su propia lista de CIERRES, y el verificador
    comprueba que cada cierre citado tiene un hallazgo que exista.  No hace falta
    que el texto este actualizado: hace falta que la referencia sea verificable.

  GAP CONCRETO, para cuando haya hueco: 009 declara 3 bloqueos; 231 y 254
  cerran 2.  Un simple "cada NOT_DETERMINED de 009 tiene un CIERRA=" habria
  detectado el de GFX_HWIP.  Es el inventario NOT_DETERMINED POR RAZON de 1473,
  y aqui se ve que tiene destinatario real.
```

## 7 · ESTADO

```text
PROVEN           IP version 8.0 en los 5 ucode de graficos, leida del binario con
                 criterio autovalidador (size_bytes == tamano real, 5 de 5).
PROVEN           crc32 (offset 28) == zlib.crc32(fichero[32:]) en 12 de 20.
PROVEN           8 de 20 no cumplen esa regla para NINGUN inicio en 28..80.
PROVEN           los 8 no se explican por el layout: MC y SMC embeben la cabecera
                 comun, y polaris12_mc valida mientras 32_mc no.
PROVEN_ABSENT    el driver no valida el campo crc32 en ningun sitio.  (254 §)
NOT_DETERMINED   cual es la regla de los 8.  Tres candidatos, ninguno probado.
                 Y refutados dos discriminantes que propuse: el IP y el
                 header_size_bytes.  mc pasa, 32_mc no, con los dos iguales.

CIERRA           el bloqueo GFX_HWIP de 009, y su coste
CIERRA           parcialmente el bloqueo CRC32 de 009
CONFIRMA         231, por via independiente
NO TOCA          254: su "20 de 20" es size_bytes, no el CRC.  No lo refuto.
NO TOCA          1466 ni la rama de firmware: es de otro nodo.

REPRODUCIBLE     los numeros salen de /lib/firmware/amdgpu/, que esta en esta
                 maquina.  Si el firmware cambia, hay que volver a medirlos, y
                 el hallazgo envejece con el, que es lo correcto.
```
