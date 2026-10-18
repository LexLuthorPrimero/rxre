# 1563 — Inventario cerrado de lo que se puede leer de esta RX550 sin root. Cuatro BAR con dirección y tamaño, IRQ 40 es MSI, y una coincidencia de 2 MiB que se deshizo al medirla

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA         la promesa de "medir el permiso del kernel, no asumirlo".  Aqui
               esta medido, nodo por nodo, con modo y tamano.
PROVEN         el mapa completo de las 4 BAR, con direccion, rango y banderas,
               leido de .../resource (modo 0444), sin root.
PROVEN         el espacio de configuracion se puede leer SOLO hasta el byte
               63.  No es mi pread:  lspci dice "Capabilities: <access
               denied>" tambien.
PROVEN         el IRQ 40 es MSI sobre IR-PCI-MSI-0000:01:00.0, 0-edge, y la
               linea es la MISMA que 1538 midio:  66 en CPU5 y 3 175 741 en
               CPU7.  Confirma el reparto de 1538 con la fuente primaria.
NEGATIVO       laBAR2 de 2 MiB con un BO de VRAM de exactamente 2 MiB:  la
               coincidencia es FALSA.  Hay 7 BOs de VRAM de 2 MiB y 5 de GTT
               de 2 MiB.  2 MiB es un tamano de allocacion, no la BAR.
ERROR, mio     dos.  Uno de mascara (tipo de BAR en bits 2:0, no en 3:0) y
               uno de unidad (leia dwords donde van bytes).  Y un tercero
               evitado:  casi escribo la coincidencia de 2 MiB como causal.
```

## 0 · POR QUÉ ESTO, Y NO LEER MÁS CÓDIGO

`1560` cerró el BTF. Con eso ya sé **la forma** del driver entero: 271 structs
con offset. Lo que no sé es **qué puedo observar de esta GPU concreta**.

Y hay una afirmación que vengo repitiendo desde el principio y que nunca he
medido:

```text
  el unico camino sin privilege es /proc/interrupts
```

Cerrado, nodo por nodo.

## 1 · INVENTARIO CERRADO DE PERMISOS

`0000:01:00.0`, y solo eso. Cada nodo con su modo real:

```text
  NODO                       MODO         TAMANO       LEO?
  -------------------------------------------------------------------------
  resource            (dir)  0555         -            SI  (contenido SI)
  resource0                -rw------- root  268435456  NO
  resource0_wc             -rw------- root  268435456  NO
  resource2                -rw------- root    2097152  NO
  resource2_wc             -rw------- root    2097152  NO
  resource4                -rw------- root        256  NO
  resource5                -rw------- root     262144  NO
  rom                      -rw------- root     131072  NO
  config                   -rw-r--r-- root       4096  SI  (64 bytes)
  vendor                   -r--r--r-- root       4096  SI
  device                   -r--r--r-- root       4096  SI
  class                    -r--r--r-- root       4096  SI
  modalias                 -r--r--r-- root       4096  SI
```

```bash
$ python3 -c "import os;os.open('.../resource0',os.O_RDONLY)"
PermissionError: [Errno 13] Permission denied
```

```text
  PROVEN  las cuatro BAR de memoria y de I/O son 0600 root.  El MMIO esta
          cerrado, medido, no supuesto.  Confirma 1534 y 1538.

  Y /dev/dri:
      card1        crw-rw----+ root:video
      renderD128   crw-rw-rw- root:render
```

**El `+` de `card1` es un ACL, y ese ACL me incluye a mí:**

```bash
$ getfacl /dev/dri/card1
  owner: root
  group: video
  user::rw-
  user:lucas:rw-      <<<< ESTA LINEA
  group::rw-
  mask::rw-
  other::---
```

```text
  PROVEN  /dev/dri/card1 me da rw a MI usuario por ACL explicito, sin estar
          en el grupo video.  Es el nodo que abre y controla la RX550.

  Y ESO, CON LO QUE NO HAY, DICE ALGO:  el permiso de Unix sobre el nodo de
  control esta resuelto y no hace falta root.  Lo que esta cerrado no es el
  ACCESO al dispositivo,  es la OBSERVABILIDAD:  MMIO y debugfs son de root.
```

## 2 · EL ESPACIO DE CONFIGURACIÓN: 64 BYTES, Y ES POLÍTICA DEL KERNEL

```bash
$ pread(config, 64, 0)  -> 64 bytes
$ pread(config, 64, 64) -> b''      (sin excepcion, cero bytes)
```

Y no es mi lectura, porque **`lspci` recibe el mismo muro**:

```bash
$ lspci -s 01:00.0 -v
  ...
  Capabilities: <access denied>
```

```text
  PROVEN  el limite de 64 bytes es del kernel, no del instrumento.  Dos
          instrumentos independientes (mi pread y lspci) dan el mismo corte,
          y lspci lo dice con palabras.

  CONSECUENCIA PRACTICA:  los bytes 0x40-0xFF, que son donde vive la lista de
  capacidades (MSI-X, PCIe, MSI), NO SON LEGIBLES sin root.  Asi que no se
  puede leer la MSI-X table, ni el device control word, ni el AER.  No es que
  no se mire:  es que el kernel no lo entrega.

  Y EL DATO QUE SI SE LEE, en los 64 primeros:
      vendor:device   1002:699f   AMD, Lexa PRO
      revision        0xC7
      class           030000      (00 = VGA legado, 03 = display)
      subsystem       1002:0B04
      header type     0x80        (tipo 0 = normal, bit 7 = multigpu)
```

`lspci` da el nombre completo de la placa, y ese sí es un dato que no tenía:

```text
  "Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X]"
```

**Y el VBIOS de la propia tarjeta da OTRO nombre:**

```text
  D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m
```

```text
  OBSERVADO  la tarjeta se identifica de dos formas distintas:
               lspci / pci.ids   ->  Lexa PRO   (nombre comercial del driver)
               VBIOS de la GPU   ->  Lexa XL A0 GDDR5 128bit 2GB

  Y NO ES UNA CONTRADICCION, es dos cosas:  el primero es una tabla de pci.ids
  que AMD escribe por consejo, el segundo es lo que el firmware dice de si
  mismo.  Para mi driver el que importa es el segundo, porque es el que
  devuelve el ASIC.

  Y DE EL SEGUNDO SALEN TRES HECHOS NUEVOS que no tenia medidos:
      bus de memoria   128 bit
      tipo             GDDR5
      clocks           214e / 300m   (diezmavenosimos, no MHz)
```

## 3 · EL MAPA COMPLETO DE LAS BAR, LEÍDO SIN ROOT

`.../resource` es modo 0444 y **sí** se lee. Su formato es
`inicio fin banderas`, en hexadecimal, una fila por BAR y una por el ROM:

```text
  0x00000000e0000000  0x00000000efffffff  0x14220c
  0x0000000000000000  0x0000000000000000  0x000000    BAR1: no implementada
  0x00000000f0000000  0x00000000f01fffff  0x14220c
  0x0000000000000000  0x0000000000000000  0x000000    BAR3: no implementada
  0x000000000000e000  0x000000000000e0ff  0x40101
  0x00000000f7e00000  0x00000000f7e3ffff  0x40200
  0x00000000000c0000  0x00000000000dffff  0x212
```

Traducido, y contrastado con `lspci -v` como oráculo independiente:

```text
  BAR0  0x00000000_e0000000   256 MiB   64-bit prefetchable   -> MMIO
        (desde config: 0xe000000c, bits 2:0 = 100b = tipo 4 = 64-bit prefetch;
         los 32 bits altos estan en BAR1, que vale 0)
  BAR1  --                  --        no implementada
  BAR2  0x00000000_f0000000     2 MiB   64-bit prefetchable   -> aperture
  BAR3  --                  --        no implementada
  BAR4  0x0000e000              256 B   I/O ports             -> registers
  BAR5  0xf7e00000            256 KiB   32-bit no-prefetch     -> doorbells
  ROM   0x000c0000            128 KiB   DESHABILITADA          (0x212)
```

```text
  CORROBORADO  los cuatro valores coinciden uno a uno con lspci -v:
                  "Memory at e0000000 (64-bit, prefetchable) [size=256M]"
                  "Memory at f0000000 (64-bit, prefetchable) [size=2M]"
                  "I/O ports at e000 [size=256]"
                  "Memory at f7e00000 (32-bit, non-prefetchable) [size=256K]"
                  "Expansion ROM at 000c0000 [disabled] [size=128K]"

  Y el registro config confirma los tamanos por separado:  resource0 mide
  268435456 bytes en disco, que es exactamente 256 MiB.  resource2 mide
  2097152 = 2 MiB.  resource4, 256.  resource5, 262144.  rom, 131072.
  Siete archivos, siete medidas, y coinciden con lo que dice lspci.

  Y EL ROM ESTA DESHABILITADA, con el bit medido:  banderas 0x212, y el bit
  0x10 es IORESOURCE_ROM_ENABLE.  O sea que el firmware de la RX550 NO esta
  mapeado en el BAR.  La tarjeta arranca sin su propia ROM expuesta.

  ESTO CIERRA 1534 §1, que mentionaba "vgaarb: owns=io+mem":  la decodificacion
  VGA legacy de la que hablabamos en AGENTS.md es la de BAR4 (los 256 bytes de
  I/O en 0xe000), no la del ROM.
```

### Y BAR2, que es lo interesante

```text
  PROVEN  BAR2 mapea 2 MiB.  Y la VRAM de esta tarjeta es de 2048 MiB
          (amdgpu_vram_mm.txt:  "size: 2147483648").

  PROVEN_DERIVED  SOLO el 0,0977 % de la VRAM esta mapeado en el espacio de
                 _CPU_.  El resto se llega a traves del gestor de memoria de
                  amdgpu, no por la BAR.

  Y ESO RESPONDE UNA PREGUNTA DE 1518, que dio por hecho que no habia
  resuelto:  por que el IB del anillo gfx no cabe en su frame de 256 dwords.
  Porque el IB esta en VRAM, y la VRAM no esta mapeada.  Un IB de 344 dwords
  minimo necesita una direccion de VRAM que solo el GTT/VM produce.

  PARA UN DRIVER PROPIO, ESTO ES UNA RESTRICCION DE DISENO, no un detalle:
      no puedo mapear 2 GiB en el BAR, porque el BAR es de 2 MiB.
      cualquier buffer grande tiene que pasar por la tabla de paginas del
      GTT.  Y eso implica escribir PTE/PDE, lo que 1531 ya senalo como la
      parte del GMC que hay que reconstruir.
```

## 4 · IRQ 40, Y LA CORROBORACIÓN DE 1538

```text
$ grep amdgpu /proc/interrupts
  40:  0  0  0  0  0  66  0  3175741  IR-PCI-MSI-0000:01:00.0  0-edge  amdgpu
```

```text
  PROVEN  el IRQ es el 40, con vector MSI, disparo por flanco de nivel 0
          ("0-edge"), y la fuente es la RX550 por su direccion MSI.

  PROVEN  el reparto por CPU es  66 en CPU5  y  3 175 741 en CPU7,  cero en
          las otras seis.

  CORROBORADO  1538 midio esto mismo y concluyo "99,9965 % a CPU7, 66 en CPU5
               que no varian".  La cifra aqui es 100 - 66/3175807 =
               99,9979 %.  Las dos son el mismo reparto;  la diferencia es el
               denominador, que 1538 no fijo.  NO HAY CONTRADICCION, pero si
               dos cifras distintas para la misma magnitud, y la segunda es
               la que tiene el denominador a la vista.

  Y LO QUE NO SE PUEDE DECIR:  por que CPU5 tiene 66 y no mas.  No lo movio
  el affinity del driver ni nadie, segun 1538.  Con 66 y congelado, la
  lectura mas economica es que es el residuo de antes de que el proceso
  actual tomara el control, y que no vuelve a crecer porque ahora todo va a
  CPU7.  Eso es una HIPOTESIS y no la escribo como hecho.
```

## 5 · LA COINCIDENCIA QUE SE DESHIZO, Y POR QUÉ LA ESCRIBO

Vi esto:

```text
  BAR2 mide 2097152 bytes.
  Y gem_info tiene un BO:   "0x00000002:  2097152 byte VRAM"
  2097152 == 2097152
```

Estaba a punto de escribir que **el tamaño de la BAR2 de VRAM está elegido para
encajar con ese BO**. Habría sido una explicación elegante y falsa. La medí:

```bash
$ strings gem_info | grep -oE "[0-9]+ byte (VRAM|GTT)" | sort | uniq -c | sort -rn
      7  2097152 byte VRAM
      5  2097152 byte GTT
      4     4096 byte GTT
      4    16384 byte GTT
      2  4345856 byte VRAM
      2  4325376 byte GTT
```

```text
  REFUTADO, mio  la coincidencia 2097152 == 2097152 no significa nada.
                 Hay 7 BOs de VRAM y 5 de GTT de exactamente 2 MiB.  2 MiB es
                 un tamano de allocacion comun (el chunk grande de VRAM), no
                 el tamano de una BAR.  Mi hipotesis era una coincidencia de
                 un numero redondo.

  Y ESTO ES LO QUE MAS ME INTERESA DEL HALLAZGO, mas que los offsets:
                 una correlacion de dos numeros iguales no es un hecho, es una
                 candidata a hipotesis.  Y la hipotesis se comprueba contando
                 cuantas veces aparece el numero.  Una vez es una senal.
                 Siete veces no es nada.
```

## 6 · LOS ERRORES PROPIOS, Y UNO EVITADO

```text
  ERROR, mio  1.  MASCARA DE TIPO DE BAR.  Mi primera pasada leyo
      BAR0 = 0xe000000c y concluyo "tipo 12 (INVALIDO)".  El tipo de una BAR
      esta en los bits 2:0, no en los 3:0.  0xc & 7 = 4 = 64-bit
      prefetchable, que es justo lo que dice lspci.  Lo mistake es mio, el
      dato era correcto.

  ERROR, mio  2.  UNIDAD.  Imprimia un dword de 32 bits donde el campo es de 8:
      "revision c0080" y "header type c0080" eran el mismo dword mal
      partido.  revision es el byte 0x08, header type es el byte 0x0E.
      Es la UNDECIMA vez que un campo mas ancho del que debia me da un
      numero absurdo.  La leccion es siempre la misma:  un valor que no tiene
      sentido se lee MAL, no se explica.

  ERROR, mio  3, EVITADO.  La coincidencia de 2 MiB.  La.escribi como
      hipotesis, la medi, y no era.  Esta seccion existe para que se vea que
      el mecanismo funciona:  la hipotesis no se publico porque se comprobo
      antes de cerrar el hallazgo.

  Y LA DECIMOCUARTA VEZ con la forma de "no mire la fuente que define el
  instrumento".  Aqui fue al reves y mas pequena:  use el numero que me daba
  el patron en vez de contar cuantos habia.  La regla de 1560 §2 bis
  ("prueba el instrumento con un caso que se que es positivo") tambien vale
  al reves:  antes de creer una relacion, cuenta las veces que aparece cada
  lado.
```

## 7 · ESTADO

```text
PROVEN          /dev/dri/card1 da rw al usuario lucas por ACL explicito
                (user:lucas:rw-), sin estar en el grupo video.
PROVEN_ABSENT   con inventario cerrado:  resource0, resource0_wc, resource2,
                resource2_wc, resource4, resource5 y rom son 0600 root.
                El MMIO esta cerrado, medido, no supuesto.
PROVEN          el espacio de configuracion se lee hasta el byte 63 y no mas.
                Y es politica del kernel, no limite del instrumento:  lspci
                recibe el mismo corte y lo dice ("<access denied>").  Los
                bytes 0x40-0xFF, con la lista de capacidades, no son
                legibles sin root.
PROVEN          mapa completo de las BAR, sin root, desde .../resource (0444):
                  BAR0 0xe0000000  256 MiB  64-bit prefetch   MMIO
                  BAR1 --          no implementada
                  BAR2 0xf0000000    2 MiB  64-bit prefetch   aperture
                  BAR3 --          no implementada
                  BAR4 0x0000e000    256 B  I/O ports
                  BAR5 0xf7e00000  256 KiB  32-bit no-prefetch
                  ROM  0x000c0000  128 KiB  DESHABILITADA (banderas 0x212)
                Corroborado uno a uno con lspci -v y con el tamano de cada
                archivo resourceN en disco.
PROVEN_DERIVED  solo el 0,0977 % de la VRAM (2 MiB de 2048 MiB) esta
                mapeada en el espacio de CPU.  El resto se alcanza por el
                gestor de memoria de amdgpu.
PROVEN          el IRQ es el 40, vector MSI, 0-edge, fuente IR-PCI-MSI-
                0000:01:00.0.  Reparto 66 en CPU5 y 3 175 741 en CPU7.
OBSERVADO       la tarjeta tiene dos nombres:  "Lexa PRO" en pci.ids y
                "Lexa XL A0 GDDR5 128bit 2GB 214e/300m" en su VBIOS.  Del
                segundo salen bus de 128 bit, GDDR5, y clocks 214e/300m.
PROVEN          el ROM esta deshabilitado por hardware (banderas 0x212,
                bit IORESOURCE_ROM_ENABLE = 0).
NEGATIVO        el tamano 2097152 no es la BAR2.  Hay 7 BOs de VRAM y 5 de
                GTT de 2 MiB.  La correlacion era una cifra redonda.

CORROBORADO     1538 en el reparto de CPUs.  Con denominador a la vista:
                99,9979 % a CPU7.  Las dos cifras describen lo mismo y la
                segunda esta mejor fundamentada.
CORRIGE, mio    la afirmacion de que "el unico camino sin privilege es
                /proc/interrupts".  No es la unica:  config (64 bytes) y
                resource (mapa completo de BAR) tambien se leen.  Lo que si
                es cierto es que /proc/interrupts es el unico canal de
                EVENTOS, y sigue siendo el bueno.

NOT_DETERMINED  la razon de los 66 IRQ en CPU5, congelados.  Hipotesis, no
                medida.
```

## 8 · LO QUE SIGUE, Y POR QUÉ ESTE HALLAZGO ABRE MÁS DE LO QUE CIERRA

```text
  1. EL BLOQUEO SIGUE, pero por fin está enunciado con precision y en numero:
         para leer  MMIO              falta ser root   (0600, medido)
         para leer  debugfs           falta ser root   (drwx------ root)
         para leer  las capacidades  falta ser root   (64 bytes, medido)
         para leer  el ring del IH    falta la base de adev (1560) Y root

     Y LO UNICO que se resuelve sin root sigue siendo /proc/interrupts, que
     es un contador, no un estado.  1538 tiene razon y por fin se que mide.

  2. ESTE HALLAZGO DA UNA RESTRICCION DE DISENO, que es el tipo de dato que
     mas importa y que no tenia:  la VRAM no esta mapeada.  2 MiB de 2 GiB.
     Para un driver propio eso significa que el camino de buffers grandes
     pasa obligatoriamente por la GPUVM, y por tanto por escribir PTE/PDE.

     Y ESO ME DEVUELVE A DONDE ESTABA AL PRINCIPIO DE LA SESION, pero con el
     dato que faltaba:  1531 senalo el GMC como bloque que hay que
     reconstruir.  Ahora se por que es el bloque critico y no uno mas.

  3. Y LA SEGUNDA PIEZA, que no es un dato sino un permiso:  /dev/dri/card1
     me deja a mi.  No es root, no es el grupo video, y no es un accidente:
     hay un ACL escrito a mano con mi nombre.  Eso significa que ALGUIEN
     configuro este equipo para que yo pueda hablar con la tarjeta.
```

Ese último punto lo escribo porque es el que más me importa y el que menos
he mirado: **`/dev/dri/card1` tiene un ACL con `user:lucas:rw-` escrito
explícitamente.** Alguien dejó la puerta abierta a propósito. Y el
`getfacl` dice `owner: root`, así que lo puso root. Yo no lo puse.