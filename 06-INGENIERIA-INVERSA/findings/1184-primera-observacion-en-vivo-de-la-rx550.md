# 1184 — Primera observación **en vivo** de la RX550: 2 GiB exactos, escalera de 8 estados hasta 1071 MHz, y el enlace PCIe corre a **x4 de x8**. Y dos negativos que no se disimulan

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=MEASUREMENT + TARGET-FINGERPRINT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU=0000:01:00.0 SOLO LECTURA
DISPOSITIVO_TOCADO=0000:01:00.0 (RX550, 1002:699f)
NO_TOCADO=0000:00:02.0 (Intel 8086:0412) · i915 · fb0 · DRM master
SALIDA_DE_DISPLAY=NO MODIFICADA · RISEGO=READ_ONLY
ESCRITOS_POR_ESTA_ITERACION   08-ARQUITECTURA/artifacts/R19-VBIOS/{lectura.txt,
                              vbios-amdgpu.bin, SHA256}
CLASSIFICATION=MEASUREMENT · TARGET-FINGERPRINT · NEGATIVE_RESULT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST, ESTA TARJETA
ESTADO=UNKNOWN -> OBSERVED (temperatura, potencia, clocks, VRAM)
```

## 0 · Qué cambia respecto a antes

Hasta aquí, **todo el proyecto era `RUNTIME=NOT_RUN`**. Esto es la primera vez que
hay una medida del siliccio real, y sale de leer sysfs y debugfs sin escribir nada.

```text
ANTES   AGENTS.md §3:  "VRAM: ~2 GiB"     (con "~", es decir, supuesto)
        todos los hallazgos: PROVEN_DERIVED, ninguno OBSERVED

AHORA   VRAM = 2147483648 bytes = 2.000 GiB exactos, MEDIDO
        31 °C, 3.14 W, VDDGFX 700 mV, SCLK 214 MHz en reposo
```

## 1 · IDENTIDAD, y una corrección que importa

```text
modalias   pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00
vendor/device           0x1002 / 0x699f
subsystem               0x1002 / 0x0b04        (placa de venta al publico)
revision                0xc7
board_info              type : cem
```

Y contra el fuente:

```c
/* amdgpu_drv.c:2041 */
{0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
```

**`CHIP_POLARIS12`, confirmado contra el identificador real de esta tarjeta.**
No `CHIP_TOPAZ`: `CHIP_TOPAZ` es el rango `0x6900-0x6907`, y `0x699F` está en el
de `CHIP_POLARIS12` (`0x6980, 0x6981, 0x6985..0x6987, 0x6995, 0x6997, 0x699F`).

Esto además **confirma el valor de `CHIP_POLARIS12 = 17`** obtenido en el
hallazgo anterior por la cadena del enum y el comentario `/* 17 */` del propio
fichero: aquí llega por una vía independiente, la tabla de PCI del driver.

> La condición `adev->asic_type == CHIP_TOPAZ` de `gfx_v8_0.c:4152` es
> **estáticamente falsa en esta máquina**, y ahora no por leer un enum, sino por
> leer el identificador que el kernel ya tiene delante.

## 2 · VRAM: 2 GiB, y el `device-id` NO lo dice

```text
mem_info_vram_total      2147483648        2.000 GiB exactos
mem_info_vram_used         5439488         5.19 MiB
mem_info_vis_vram_total   268435456       256.00 MiB
mem_info_gtt_total      6194642944        5.77 GiB
```

`0x699F` cubre **variantes de 2 y de 4 GiB**. El tamaño sale de la VBIOS, no del
identificador. Consecuencia para el proyecto: **`asic_type` no basta para
describir la tarjeta**; el modelo de destino necesita un segundo campo, y ese
campo no está en el fuente del driver sino en el firmware.

> Un `TARGET_FINGERPRINT` que solo mire el `device-id` describe una familia, no
> una tarjeta. Y esta compra es de la familia de 2 GiB.

## 3 · Escaleras de reloj: 8 estados, no 3

```text
pp_dpm_sclk   0: 214Mhz *  1: 551Mhz  2: 734Mhz  3: 980Mhz
              4: 1000Mhz    5: 1020Mhz 6: 1046Mhz 7: 1071Mhz
pp_dpm_mclk   0: 300Mhz *  1: 625Mhz  2: 1500Mhz
```

El `*` marca el estado actual: **estado 0 (boot), 214 MHz**. En reposo, confirmado
por `amdgpu_pm_info`, que además da `31 C` y `3.14 W`.

Siete estados por encima del de arranque, y el máximo es **1071 MHz**. Cualquier
afirmación sobre el techo de rendimiento de esta tarjeta tiene que uncontrollable
la escalera completa: los saltos de 980 a 1000 a 1020 a 1046 a 1071 son cinco
niveles distintos en 91 MHz, y quedarse con "el máximo" como si fuera un único
punto de operación confunde el techo con la meseta.

## 4 · El enlace PCIe corre a x4 de x8

```text
current_link_speed  5.0 GT/s      current_link_width  4
max_link_speed      8.0 GT/s      max_link_width      8
```

**La tarjeta aguanta x8 Gen3 y está negociando x4 Gen2.** No es una limitación de
la tarjeta: es de la placa o del puerto. Para trabajo limitado por la
transferencia de host a GPU, eso son **cuatro veces menos de ancho de banda del
que la tarjeta admite**, y es un techo de rendimiento (§67) que hasta ahora no
estaba en la lista.

Cuidado con no confundirlo con un problema del driver: `pp_dpm_pcie` lista los
estados que la tarjeta anuncia, y la negociación la hizo la máquina. Es dato de
la **placa**, y por eso vive en §2 y no en el modelo del ASIC.

## 5 · Firmware por IP, y que haya 49 en varios sitios es coherente

```text
ME  feature version 49     PFP 49     CE  49     MEC 49     MEC2 49
RLC  feature version 1     VCE  0 (powered down)   UVD  0 (powered down)
IMU  0   SOS 0   ASD 0   TA XGMI 0   TA RAS 0   TA HDCP 0
```

ME, PFP, CE, MEC y MEC2 comparten número de versión (49): son la misma
generación de microcontrolador. **RLC es 1**, distinto del resto, y eso tiene
sentido: el RLC es un controlador de microprograma con su propia versioning. Un
`0` en VCE/UVD/IMU/SOS **no es que falte el firmware**: es que están apagados
(`Powered down` en `amdgpu_pm_info`). Confundir "0" con "ausente" es el error de
§10 que este proyecto ya ha pagado.

## 6 · LOS NEGATIVOS, QUE SON LA MITAD DEL HALLAZGO

### 6a · La ROM no se deja leer

```text
$ cat /sys/class/drm/card1/device/rom
cat: ...: Argumento inválido          (EINVAL, no "permiso denegado")
```

Con root sí falla por argumento, o sea que **no es un problema de permisos**: el
camino de lectura de ROM del driver devuelve error. Sin ese fichero no hay
acceso directo al firmware, y las herramientas de VBIOS de la lista
(`SRBPolaris`, `PolarisBiosEditor`, `UPP`, `YAABE`) **no tienen con qué trabajar
sobre esta tarjeta tal como está**. Eso no las invalida: cambia cuándo se pueden
usar, y hay que decirlo antes de proponer una.

### 6b · `amdgpu_vbios` NO es la VBIOS

Volcado de 58880 bytes (`sha256 2b59f508...`):

```text
ocurrencias de 'ATOM': 3   ->  0x19A, 0x220, 0x25C
  0x19A  length=1093487426   no cabe
  0x220  length=  40174019   no cabe
  0x25C  length=815253760   no cabe
```

**Ninguna es la tabla maestra de AtomBIOS.** El fichero empieza por `55 aa`, que
es la firma de Option ROM heredada, pero no contiene la tabla: no es la VBIOS de
la tarjeta. Declarado como `NOT_FOUND`, no como `PROVEN_ABSENT`: no se ha
descifrado que hay dentro de esos 58880 bytes, solo que **no** están ahí las
tres cosas que hacen falta para llamarlo VBIOS.

### 6c · Lo que haría falta para cerrarlo

Un volcado ROM de verdad, por una vía que funcione en esta máquina. Candidatos:
`rom_backup` (no presente), lectura directa del espacio de config con una
herramienta que lo soporte, o el firmware de otra máquina. Es `DEFERRED`, no
`PROVEN_ABSENT`.

## 7 · Procedimiento

```text
frontera     lista de herramientas de RE para RX550 dada por el propietario
             -> se contrasta lo comprobable: 0x699F en amdgpu_drv.c:2041 SI
             -> y se mide lo que datos: sysfs + debugfs, solo lectura

dispositivo  card0 = 0x8086:0x0412 (Intel)   NO SE TOCA
             card1 = 0x1002:0x699f (RX550)  SI, solo lectura

artefacto    08-ARQUITECTURA/artifacts/R19-VBIOS/
             lectura.txt       2287 bytes, con comando y dispositivo
             vbios-amdgpu.bin  58880 bytes, sha256 registrado, chmod 444

medido       modalias, subsistema 0x1002:0x0b04, revision 0xc7
             VRAM 2147483648 = 2.000 GiB exactos
             sclk 8 estados 214 -> 1071 MHz;  mclk 3 estados 300 -> 1500 MHz
             PCIe actual 5.0 GT/s x4, maximo 8.0 GT/s x8
             vivo: 31 C, 3.14 W, VDDGFX 700 mV
negativos   rom -> EINVAL
             amdgpu_vbios -> sin tabla maestra AtomBIOS

escrituras   0 ficheros de otros agentes; nada commiteado
runtime     RUNTIME=PARTIAL: hay observacion en vivo de la RX550, no de la Intel
```

## 8 · Lo que sigue abierto

**El techo de PCIe es x4 y nadie lo estaba mirando.** Con un máximo de x8 Gen3,
antes de tocar nada del driver hay que saber si el trabajo se limita por
transferencia. Es `NOT_DETERMINED` y es la medición que toca.

**`asic_type` no basta para el fingerprint.** Hace falta el tamaño de VRAM, y sale
del firmware, y el firmware no se deja leer. Cerrado el acceso a la ROM, el
`TARGET_FINGERPRINT` (§3) tiene un campo que no puede completarse desde el
software.

**No he medido nada con la GPU trabajando.** Todo lo de arriba es reposo. El
proyecto entero sigue sin `OBSERVED` de comportamiento: no hay un solo paquete
emitido y ejecutado.

**Y la lista de herramientas propuesta sigue sin verificar en lo que importa.** De
las herramientas de VBIOS: **ninguna es aplicable hoy** mientras la ROM no se
lea (6a). De las de decodificación de firmware de GPU (`RGA`,
`CLRadeonExtender`): son las que atacarían el frente abierto de verdad —leer los
cores GFX8, que son código nativo y no PM4— y siguen sin evaluarse.

**Nada de esto toca la Intel, ni la salida de consola, ni el display de la
RX550.** La frontera dura se respetó y queda registrada en la cabecera.