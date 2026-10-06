# 1583 — Ítem 4 cerrado: las seis copias de SoftRegisters reconciliadas **por offset**, y el linaje sale entero. `smu74 == smu75`, y entre `smu71` y `smu72` se insertan **cuatro bytes** que desplazan el bloque DRAM_LOG

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICA-ESTRUCTURAL
CLASSIFICATION=EVIDENCIA-POR-COMPILACIÓN (los 6 structs,  offsets reales de gcc)
MODIFICATIONS=1564 §la tabla de 30 campos  (sustituida por la reconciliacion por offset)
MODIFICATIONS=1564 §"el corte es posicional y limpio"  (CONFIRMADO,  con el punto exacto)
MODIFICATIONS=1578 §2  (el metodo por offset,  aqui extendido a las 6 copias)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura de codigo;  la herramienta se usa
                               sin modificar)
CIERRA   el cuarto hueco de riesgo cero
```

## 1 · Por qué hacía falta el offset y no el nombre

`1564` comparó por **nombre** y consiguió "24 coinciden, 6 divergen, corte en 76".
Ese número estaba **subcontando**, y por un motivo que ahora está medido:

```text
  smu7_discrete.h = smu75.h  con 5 nombres TRUNCADOS
      PmTimerPeriod      /  PmTimerP
      AverageGraphicsActivity / AverageGraphicsA
      AverageMemoryActivity   / AverageMemoryA
      AverageGioActivity      / AverageGioA
      UlvEnterCount           / UlvEnterC
```

El productor por nombre no los ve como el mismo campo, así que **pregunta 30 de 40** y
no puede ver que `smu74` y `smu7_discrete` son layout-identico (`1578` ya lo probó con
gcc para el par, y aquí queda para las seis). El offset no tiene ese problema: pregunta
por **posición en la memoria**, que es lo que el firmware realmente ve.

## 2 · La reconciliación entera, con gcc, las seis copias

```text
  smu71.h          SMU71_SoftRegisters       40 campos   gcc=OK
  smu72.h          SMU72_SoftRegisters       41 campos   gcc=OK
  smu73.h          SMU73_SoftRegisters       41 campos   gcc=OK
  smu74.h          SMU74_SoftRegisters       43 campos   gcc=OK   <-- POLARIS12
  smu75.h          SMU75_SoftRegisters       43 campos   gcc=OK
  smu7_discrete.h  SMU7_SoftRegisters       40 campos   gcc=OK
```

Comparando `smu74` contra cada una **por offset**:

```text
  vs SMU75_SoftRegisters      0 offsets distintos de 43     IDENTICOS
  vs SMU72_SoftRegisters      3 offsets distintos de 43     112, 116, 117
  vs SMU73_SoftRegisters      3 offsets distintos de 43     112, 116, 117
  vs SMU7_SoftRegisters       9 offsets distintos de 43     (los 3 de arriba + 6)
  vs SMU71_SoftRegisters     17 offsets distintos de 45     el corte, en 76
```

**Y el linaje completo, que es lo que sale de aquí:**

```text
  smu71    NO tiene los 4 bytes de *DpmEnabledLevels de UVD/SAMU/ACP/VCE.
           Ademas tiene 3 campos al final que smu74 no tiene:
             DPMFreezeAndForced (108),  Activity_Weight (109),  Reserved8 (110)

  smu72    + los 4 bytes en 76-79.  Cola de 12 bytes SIN NOMBRAR (Reserved[3])
  smu73    identico a smu72.  Los 3 offsets distintos son los MISMOS,  medido:
             smu72 {112, 116, 117}  ==  smu73 {112, 116, 117}   ->  True

  smu74    identico a smu72,  mas la cola nombrada:
             108 UcodeLoadStatus · 112 AllowMvddSwitch · 116 Activity_Weight
             117 Reserved8[3]
           ESTA ES LA DE POLARIS12

  smu75    identico a smu74.  0 diferencias de offset.
```

`smu72`, `smu73` y `smu7_discrete` son **lo mismo**: `smu74` con los últimos 12 bytes
sin nombrar. Eso es una sola causa, no tres, y `1578` ya había medido la cola.

## 3 · El punto de inserción, exacto

```text
                68          72  73  74  75  |  76         77         78         79  | 80
  SMU71      AverageGio  SClk MClk LClk PCIe | DRAM_LOG_ADDR_H                ...   | (DRAM_LOG_ADDR_L)
  SMU74      AverageGio  SClk MClk LClk PCIe | UVD    SAMU   ACP    VCE          | DRAM_LOG_ADDR_H
```

```text
  SMU71   AverageGioActivity  72:SClk 73:MClk 74:LClk 75:PCIe  76:DRAM_LOG_ADDR_H  80:DRAM_LOG_ADDR_L
  SMU74   AverageGioActivity  72:SClk 73:MClk 74:LClk 75:PCIe  76:UVD 77:SAMU 78:ACP 79:VCE
                                                                        80:DRAM_LOG_ADDR_H  84:DRAM_LOG_ADDR_L
```

**Los cuatro `*DpmEnabledLevels` de UVD, SAMU, ACP y VCE se insertaron en el offset 76
entre la generación SMU71 y la SMU72.** Todo lo que está en 76 o después se desplaza
+4. Eso **confirma** el corte que `1564`олееportó, y ahora lo localiza con el nombre
del campo que ocupa el hueco.

Y es un hecho sobre el **firmware**, no sobre el driver: el bloque de registros blandos
del SMU ganó cuatro bytes en esa generación. Es de la misma clase que el crecimiento de
la tabla DPM, no de la clase de un descuido de C.

## 4 · Por qué esto importa para esta placa, y no es solo historia de familias

```text
  DIRECCION DE DRAM_LOG_ADDR_H,  DENTRO del bloque de registros blandos
      en SMU71  (Carrizo, ~2015)         offset  76
      en Polaris12 (RX550, nuestra)      offset  80
```

`1574` ya decía: `soft_regs_start` es la **dirección** del bloque, y
`polaris10_get_offsetof(SMU_SoftRegisters, DRAM_LOG_ADDR_H)` devuelve **80** para esta
placa. O sea que la dirección real del registro de dirección del log de DRAM en esta
GPU es:

```text
  soft_regs_start + 80
```

**Y el número 76, que es el que tiene cualquier código copiado de una generación
SMU71, leería 4 bytes antes.** Con un bloque cuyo campo en 76 es
`UVDDpmEnabledLevels`, un byte de un contador de niveles de UVD — o sea, algo que
cambia por actividad de decodificación de vídeo, no por la dirección que se Seek.

Es exactamente el caso que §5 y §71 señalan: **una specialization que se apoya en un
número de otra generación es un error silencioso**, y aquí el número está a cuatro
bytes de un campo que se mueve solo. Para el driver propio, la regla que sale es
concreta:

```text
  REGLA  todo offset dentro de un bloque de firmware se resuelve con offsetof
         contra la struct DE ESA GENERACION,  nunca con un literal copiado.
         Y el literal se guarda junto al nombre del campo,  no suelto
```

## 5 · Una limitación medida, y por qué no la persigo

El `sizeof` de las seis structs **no se puede medir en una sola translation unit**:

```text
  smu72.h:92:3: error: conflicting types for 'data_64_t';  have 'struct <anonimo>'
```

Es el conflicto de cabeceras que `1564` ya había encontrado con `gmc_8_1_d.h` contra
`gmc_8_2_d.h`: **dos cabeceras de la misma familia se definen el mismo símbolo con
tipos distintos, y no se pueden incluir juntas.** Por eso `smu_softregs.py` compila
**una unidad por struct** en vez de una para todas.

Lo que eso deja sin medir es el `sizeof` de cada copia, y **no lo persigo** por dos
motivos: los offsets ya dan toda la información que hace falta para el linaje, y el
tamaño se puede derivar del último offset más el ancho del último campo sin ambigüedad.
Anotado como `NOT_DETERMINED` en el tamaño, no como ausencia.

## 6 · Procedimiento y alcance

```text
PREGUNTA   cual es el linaje real de las 6 copias de SoftRegisters,  y donde estan
           los limites de layout entre ellas
FUENTES    tools/smu_softregs.py,  REUTILIZADO sin modificar:
             campos_por_parseo()  ->  la lista de campos que DECLARA cada struct
             campos_comunes()     ->  nombres comunes  (la via que usa 1564)
             offsets_por_compilacion()  ->  gcc contra la cabecera real
           la tabla completa offset -> nombre  de las 6,  hecha a mano
MEDIDO     40/41/41/43/43/40 campos declarados,  las seis compilan con gcc
     smu74 vs smu75   ->  0 offsets distintos
     smu74 vs smu72   ->  3   (112, 116, 117)
     smu74 vs smu73   ->  3   (los mismos 3,  verificado como conjunto igual)
     smu74 vs discrete->  9   (los 3 + 6 de truncatura ya medidos en 1578)
     smu74 vs smu71   ->  17,  con el corte en 76
     la insercion son 4 bytes de *DpmEnabledLevels (UVD/SAMU/ACP/VCE) en 76
     smu71 tiene de mas  DPMFreezeAndForced(108)  Activity_Weight(109)
                                    Reserved8(110)
     sizeof conjunto:  NO MEDIBLE,  por conflicto de tipos entre cabeceras
DESVIO MIO  uno,  de los de siempre
     itere un dict esperando pares y me dio  "too many values to unpack".
     Los offsets de smu_softregs.py  son  {nombre: offset}  y yo los trataba
     como  [(nombre, offset)]  porque campos_por_parseo()  si devuelve pares.
     Dos productores con la misma forma nominal  y distinto tipo:  la clase de
     fallo que me ha costado 10 veces hoy,  y la unica forma de verla es leer la
     linea de origen cuando la conclusion depende del dato
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 7 · Lo que sigue

```text
  huecos de riesgo cero de mi lista de siete:  SOLO EL 7
    item 7:  cobertura de descubrimiento de RXRE con un denominador que no sea
    el mio.  El 15/15 que di en 1575  era real pero trivial:  quince 'case'
    contiguos en un solo fichero,  con nombres que aparecen literales.  La regla
    justa tiene que esparcirse por el corpus

  y con esto quedan cerradas las tres piezas de la cadena de soft_regs_start:
    1577  la ruta de dispatch,  probada con un switch
    1578  que struct es la de esta placa,  y que la colision era irrelevante
    1583  que offset tiene cada campo dentro del bloque  ->  DRAM_LOG_ADDR_H = 80
  de modo que la unica incógnita que queda es el VALOR de soft_regs_start:
    SMC_RAM[0x20030].  Con la receta del driver (1579),  las dos direcciones
    confirmadas en los tres linajes,  y pendiente de tu OK
```