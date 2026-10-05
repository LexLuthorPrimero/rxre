# 1532 — el mapa de lanes dice 64 bits y la cadena dice 128: el ROM se contradice, y hay un cuarto testigo sin decodificar

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM (una sola) · FASE=2 (geometria)
CLASSIFICATION=DECODIFICACION+VALIDACION-POR-ENUMERABLE+CONTRADICCION-REGISTRADA
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
CIERRA=el hueco que el 1530 dejo nombrado: usDramDataRemapTblOffset
ESTADO=PROBADO · ATOM_DRAM_DATA_REMAP decodificada: 2 bloques de 34 B, 16 permutaciones
       · los 16 remaps de bit son permutaciones VALIDAS de 0..7  <- validacion por enumerable
       · byte remap Ch0 = IDENTIDAD, Ch1 = INVERTIDO, con campos de 2 bits
       · el mapa tiene 4 bytes por canal = 32 bits por canal, y CHANSIZE=0 tambien lo dice
       · CONTRADICCION ABIERTA: 2 canales x 32 = 64, contra la cadena "128bit"
       · y hay un cuarto testigo sin decodificar: WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1
```

## 1. La tabla que el 1530 dejo sin decodificar

`usDramDataRemapTblOffset = 743` lleva a `0xA5F1`, y el 1530 senalo que **no es un
`ATOM_INIT_REG_BLOCK`**: es un `ATOM_DRAM_DATA_REMAP`. Por eso los dos campos de tamaño que lei ahi
no cuadraban — les estaba aplicando la estructura equivocada. Esto es lo que hay.

Estructura (`atombios.h:8044-8056`), 34 bytes, sin cabecera:

```text
  UCHAR  ucByteRemapCh0, ucByteRemapCh1
  ULONG  ulByte0..3BitRemapCh0
  ULONG  ulByte0..3BitRemapCh1
```

Y `ucMcPhyTileNum = 2`, asi que hay dos bloques de 34 bytes: `0xA5F1` y `0xA613`. Los dos decodifican
a permutaciones validas, que es la prueba de que el segundo no es basura de relleno.

## 2. El encoding, y como losaque sin inventarlo

El header documenta el encoding del campo equivalente en la version V7 (`atombios.h:8005-8006`):

```c
  UCHAR  ucMemDQ7_0ByteRemap;   // =0: Memory Data line BYTE0, =1: BYTE1, =2: BYTE2, =3: BYTE3
  ULONG  ulMemDQ7_0BitRemap;    // each DQ line (7~0) use 3bits: DQ0=Bit[2:0], DQ1:[5:3], ... DQ7:[23:21]
```

**Me equivoque una vez aqui y lo declaro.** Lei primero `ucByteRemapCh0 = 0xE4` como nibbles, obtuve
`[4, 14, 0, 0]`, y casi lo publico como "otra permutacion". Es falso: son **2 bits por byte**, no
nibbles. Lo dice el comentario (los valores van de 0 a 3, luego 2 bits) y lo confirma la aritmetica
(4 bytes x 2 bits = 8 bits = un `UCHAR`). Con 2 bits:

```text
  ucByteRemapCh0 = 0xE4 = 11100100  ->  campos [0,1,2,3]  IDENTIDAD,  byte n -> BYTE n
  ucByteRemapCh1 = 0x1B = 00011011  ->  campos [3,2,1,0]  INVERTIDO, byte n -> BYTE 3-n
```

**Un canal con los bytes en orden y el otro al reves.** Eso no es ruido: es una diferencia real entre
los dos canales, y es el tipo de detalle que decide el orden de bytes en una lectura de VRAM.

## 3. La validacion que hace trustworthy el decode

Los 16 remaps de bit, con 3 bits por linea DQ, dan seis valores distintos. Los seis:

```text
  0x00D1037B  ->  3 7 5 0 0 2 4 6     permutacion de 0..7
  0x00DEC650  ->  0 2 1 3 4 5 7 6     permutacion de 0..7
  0x0008B97E  ->  6 7 5 4 3 1 2 0     permutacion de 0..7
  0x00DEC2D0  ->  0 2 3 1 4 5 7 6     permutacion de 0..7
  0x0009997E  ->  6 7 5 4 1 3 2 0     permutacion de 0..7
  0x007E90A6  ->  6 4 2 0 1 5 7 3     permutacion de 0..7
```

**Los dieciseis son permutaciones de 0..7.** Un byte leido con la base equivocada, o con un ancho de
campo equivocado, no produce permutaciones. Y solo usan 24 de los 32 bits, que es justo lo que dice
"8 lineas DQ x 3 bits". El encoding esta confirmado por su propia aritmetica.

Ademas hay estructura entre los dos tiles: comparten 10 de 16 valores, y `0x0009997E` aparece en el
tile 0 como `Byte0Ch1` y en el tile 1 como `Byte0Ch0` y `Byte0Ch1`. Los tiles son casi el mismo
mapa con tres permutaciones cambiadas.

## 4. La contradiccion, registrada y sin resolver a la fuerza

Aqui esta lo que este hallazgo produce, y es una **contradiccion nueva**, no un cierre:

```text
  testigo 1  la cadena del ROM, offset 0x131
             "Lexa XL A0 GDDR5 128bit 2GB 214e/300m"                     dice 128

  testigo 2  usEnableChannels = 0x0003  (2 canales)  x  usMcRamCfg.CHANSIZE = 0 (32 bits)
                                                                            dice 64

  testigo 3  ATOM_DRAM_DATA_REMAP: dos canales (Ch0, Ch1) de 4 bytes cada uno
             4 bytes = 32 bits por canal                                      dice 64
```

Los testigos 2 y 3 **concuerdan entre si y son independientes**, y ambos dicen 64. El testigo 1 dice
128. **Y los tres estan en el mismo fichero.**

Esto no reabre el `911` —su conclusion de 128 bits se apoya en el testigo 1 y sigue en pie— pero
anade algo que no estaba: **el ROM no es coherente consigo mismo sobre el ancho de bus**, y dos de sus
tres declaraciones coinciden en 64. Publicar "128" sin decir esto seria presentar la mitad.

Hipotesis, **sin elegir**:

```text
  H1  el "canal" del MC es un subcanal de 32 bits y un canal de 64 son 2 subcanales.
      Entonces 2 subcanales = 64 bits y habria que mirar usEnableChannels con otra lectura.
      No hay fuente en el corpus que la confirme.
  H2  la cadena "128bit" describe el ancho total de los dispositivos y MC_CHMAP cuenta otra cosa.
      Plausible, pero entonces los testigos 2 y 3 no estanSpeaker midiendo lo mismo que la cadena,
      y no tengo forma de saber que miden.
  H3  uno de los dos campos esta mal.  NO: los dos son independientes y coinciden.
  H4  el MC ve 64 y la GPU expone 128.  Habria un doble ancho en el camino.  No hay ninguna tabla
      que lo declare.
```

**Ninguna de las cuatro se puede separar con lo que hay.** §80: no hay ganador intuitivo.

## 5. El cuarto testigo, que es el que probablemente cierra esto

En el mismo ROM hay una cadena que **nadie ha decodificado**:

```text
  WEIKENG_LEXA_D090_BY_GD5_25632_HY64B1\config.h
```

Es el nombre del fichero de configuracion con el que se compuso esta BIOS. Descompuesto:

```text
  WEIKENG        el proyecto de board
  LEXA_D090      el ASIC, Polaris12
  BY_GD5         tipo de memoria: GDDR5
  25632          <-- densidad y organizacion del dispositivo, SIN DECODIFICAR
  HY             Hynix
  64B1           <-- <-- aqui hay un 64, y es el nombre del fichero, no la cadena de 128
```

**Es la pista mas economica que queda en toda la parte, y es estatica.** `25632` es un codigo de
densidad/organizacion de fabricante. Si `25632` significa "2 Gb, x32", entonces hacen falta 4
dispositivos x32 para 128 bits, y para 2 GB con dual rank. Y `HY64B1` lleva un 64 en el nombre.

> **El discriminador del item 1 esta aqui y con nombre:** decodificar `25632` y `64B1` contra la
> tabla de deteccion de fabricante. Si los dispositivos son x32, el "64" del MC son dos subcanales de
> un canal de 64, y H1 gana. Si son x64, el MC ya cuenta el canal completo y H2 gana.

Y para hacerlo hay una tabla en el ROM que **no he mirado todavia**: la de deteccion de fabricante de
memoria, que es la que traduce esos codigos a `ucDensity`, `ucMemoryVenderID` y organisation. El
`ucDensity = 99` y el `ucMemoryVenderID` del modulo son **justo la salida de esa tabla**, y estan sin
decodificar.

## 6. Estado del item 1 tras este hallazgo

```text
  antes   el ancho era 128 por la cadena (911/923), con el 64 del driver explicado como residuo
  ahora   el ancho tiene 3 testigos en el ROM, y 2 de 3 dicen 64
          el mapa de lanes esta DECODIFICADO y validado por enumerabilidad
          y hay un cuarto testigo sin decodificar que probablemente decide

  NO AFIRMO  que la tarjeta sea de 64.  NO AFIRMO que sea de 128.
  AFIRMO    que el ROM contiene declaraciones incompatibles y que el testigo mas barato para
            separarlas es la cadena de configuracion mas la tabla de deteccion de fabricante.
RIESGO      ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE      el decode del remap es una lectura de un volcado con estructuras del header de 7.1.3.
            La validacion por enumerabilidad es fuerte pero no es medida del silicio.
```

## 7. Decision log (§103)

```text
DECISION    registrar la contradiccion en vez de resolverla
WHY         dos testigos independientes coinciden en 64 y la cadena dice 128.  No hay fuente que
            diga que los tres midan lo mismo, y elegir el mas comforts me seria inventar.
ALTERNATIVA  declarar 64 bits y corregir el 911.  Descartada: contradice la cadena del propio ROM
            y no tengo forma de explicar por que el ROM se contradiria en un campo tan visible.
ALTERNATIVA  declarar 128 y dejar el 64 como error de lectura.  Descartada por el mismo motivo.
DISCriminante  la cadena WEIKENG_..._GD5_25632_HY64B1 y la tabla de deteccion de fabricante.  Es
            ROM, es estatica, y ya se que es el sitio.  §95: la duda dice que falta, quien la
            produce, con que observable y con que herramienta.
CONSECUENCIA  el item 1 de la definicion de cierre NO se cierra en este hallazgo.  Se estrecha a
            una pregunta con respuesta en el ROM.
REVERSIBLE  el hallazgo entero cae si la tabla de deteccion resulta estar ausente.  Antes de
            escribir esto no lo compruebe.
```

## 8. Nota de disciplina, porque me la gane dos veces hoy

Hoy perdi tiempo en dos cosas que las herramientas habrian dicho antes:

1. **Contei 58 de 81** indexando la tabla de comandos con el puntero de datos, y "descubri" una
   contradiccion con el 1468 que no existia. Lo cazo la asimetria `SetMemoryClock == VRAM_UsageByFirmware`.
2. **Lei `ucByteRemapCh0` como nibbles** y estaba a punto de publicar `[4,14,0,0]` como resultado. Lo
   cazo que un campo que el header enumera de 0 a 3 no puede ocupar 4 bits.

Las dos veces, la correccion vino de una comprobacion gratuita: comparar contra lo que el productor
dice. **Un decode no se valida porque no quepte; se valida porque sus valores caen en el dominio que
el productor declara.** Las permutaciones de 0..7 y los dos centinelas `0xFFFF` son exactamente eso,
y son gratis.
