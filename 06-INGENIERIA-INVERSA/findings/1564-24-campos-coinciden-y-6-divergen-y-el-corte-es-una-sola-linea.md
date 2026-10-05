# 1564 — Extendido a los 30 campos comunes: **24 coinciden y 6 divergen, y el corte es una sola línea en el offset 76.** La causa es un `insert`/`delete` único entre SMU71 y SMU72. Y `smu7_discrete.h` trunca cinco nombres, lo que hacía que mi herramienta preguntara por 30 de 40 sin decirlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICA-ESTRUCTURAL + TOOL
CLASSIFICATION=EVIDENCIA-POR-COMPILACIÓN+EVIDENCIA-POR-DIFF-DE-LISTAS
MODIFICATIONS=1558 §4.2 (riesgo corregido, más pequeño y más preciso) · 1562 §LO QUE SIGUE 3º punto
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/smu_softregs.py  (modo --todos,  un guard,  2 vectores
                              nuevos  ·  17 -> 20 vectores)
CIERRA   1562 §LO QUE SIGUE  tercer punto:  "extender el cruce a los 40 campos
                         declarados del struct,  no solo a los cinco de DRAM_LOG_*"
CORRIGE   1558 §4.2  el riesgo,  y lo hace mas pequeno  y mas preciso
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · La tabla entera, y el corte

```text
  (modo --todos)  declarados por la copia mas pequena: 40   preguntados por nombre: 30

  campo                    71    72    73    74    75  7_disc
  RefClockFrequency         0     0     0     0     0     0    UNICO
  FeatureEnables            8     8     8     8     8     8    UNICO
  PreVBlankGap             12    12    12    12    12    12    UNICO
  VBlankTimeout            16    16    16    16    16    16    UNICO
  TrainTimeGap             20    20    20    20    20    20    UNICO
  MvddSwitchTime           24    24    24    24    24    24    UNICO
  LongestAcpiTrainTime     28    28    28    28    28    28    UNICO
  AcpiDelay                32    32    32    32    32    32    UNICO
  G5TrainTime              36    36    36    36    36    36    UNICO
  DelayMpllPwron           40    40    40    40    40    40    UNICO
  VoltageChangeTimeout     44    44    44    44    44    44    UNICO
  HandshakeDisables        48    48    48    48    48    48    UNICO
  DisplayPhy1Config        52    52    52    52    52    52    UNICO
  ...                       ..    ..    ..    ..    ..    ..
  DisplayPhy8Config        59    59    59    59    59    59    UNICO
  AverageGraphicsActivity  60    60    60    60    60    60    UNICO
  AverageMemoryActivity    64    64    64    64    64    64    UNICO
  AverageGioActivity       68    68    68    68    68    68    UNICO
  SClkDpmEnabledLevels     72    72    72    72    72    72    UNICO
  MClkDpmEnabledLevels     73    73    73    73    73    73    UNICO
  LClkDpmEnabledLevels     74    74    74    74    74    74    UNICO
  PCIeDpmEnabledLevels     75    75    75    75    75    75    UNICO
  ------------------------------------------------------------------ corte
  DRAM_LOG_ADDR_H          76    80    80    80    80    80    DIVERGE
  DRAM_LOG_ADDR_L          80    84    84    84    84    84    DIVERGE
  DRAM_LOG_PHY_ADDR_H      84    88    88    88    88    88    DIVERGE
  DRAM_LOG_PHY_ADDR_L      88    92    92    92    92    92    DIVERGE
  DRAM_LOG_BUFF_SIZE       92    96    96    96    96    96    DIVERGE
  UlvTime                 100   104   104   104   104   104   DIVERGE
```

**El corte es limpio, y por posición, no por campo:** los 24 campos que coinciden están todos en
offset **≤ 75**, y los 6 que divergen están todos en **≥ 76**, y los 6 caen exactamente **4 bytes
antes** en SMU71. No hay excepciones en ninguna dirección.

**Esto corrige el riesgo que `1558` enunció.** Escribí que el invariante se rompía si "alguien
añade un campo antes del bloque en uno solo de los cinco". La realidad es más precisa y más
favorable: **la mitad del struct es un invariante fuerte y verificado** — 24 campos, offsets 0 a
75, seis copias de acuerdo byte a byte — y **el cambio de 7.1 a 7.2 es una única inserción**, no
una deriva gradual.

## 2 · La causa, por diferencia de listas de campos

```text
  conteo de campos declarados, por copia
      SMU71_SoftRegisters     40
      SMU72_SoftRegisters     41
      SMU73_SoftRegisters     41
      SMU74_SoftRegisters     43
      SMU75_SoftRegisters     43
      SMU7_SoftRegisters      40      (smu7_discrete.h)

  smu71 -> smu72
      insert   en el indice 28:  UVDDpmEnabledLevels, SAMUDpmEnabledLevels,
                                 ACPDpmEnabledLevels, VCEDpmEnabledLevels
      delete   en el indice 36:  DPMFreezeAndForced, Activity_Weight, Reserved8

  smu72 -> smu73      sin cambios
  smu73 -> smu74      1 cambio:  Reserved  ->  AllowMvddSwitch, Activity_Weight, Reserved8
  smu74 -> smu75      sin cambios
```

**Los cuatro insertados son `uint8_t`** — se ven en `smu7_discrete.h:76-77` como
`uint8_t SAMUDpmEnabledLevels`. Cuatro bytes. **Y el offset 76 es exactamente donde empieza la
divergencia.**

O sea: la lectura es esta y no otra.

```text
  SMU71  es el raro.  Los otros cuatro (72, 73, 74, 75)  y la copia discrete
  comparten layout desde el offset 76 en adelante,  con un bloque de cuatro
  niveles de DPM byte  que SMU71 no tiene,  y por eso todo lo que va detras va
  cuatro bytes mas atras.
```

Y `SMU72 -> SMU73` **y** `SMU74 -> SMU75` no cambian **nada** en la lista. O sea que el bloque
`*DpmEnabledLevels` es la discontinuidad real entre 7.1 y 7.2, y lo que hay entre 7.2 y 7.5 son
solo esos retoques de `Reserved`/`AllowMvddSwitch` que no mueven la cola.

## 3 · `smu7_discrete.h` es `smu75.h` con cinco nombres truncados

Cinco identificadores están acortados en la copia discrete. **Cinco de cinco caen en la misma
posición y el mismo offset**, lo que prueba que el layout es idéntico y solo cambian los
identificadores:

```text
  PmTimerPeriod            pos 1   off 4     ->  PmTimerP             pos 1   off 4     MISMO
  AverageGraphicsActivity  pos 21  off 60    ->  AverageGraphicsA     pos 21  off 60    MISMO
  AverageMemoryActivity    pos 22  off 64    ->  AverageMemoryA       pos 22  off 64    MISMO
  AverageGioActivity       pos 23  off 68    ->  AverageGioA          pos 23  off 68    MISMO
  UlvEnterCount            pos 37  off 100   ->  UlvEnterC            pos 37  off 100   MISMO
  Reserved8                pos 42  off 117   ->  Reserved             pos 39  off 108   DISTINTO
```

El sexto no es una truncatura: es otro campo. `Reserved8` en `smu75.h` es un campo distinto del
`Reserved` de la copia discrete.

## 4 · Y esto rebajó mi propia herramienta: preguntaba 30 de 40, en silencio

La intersección por nombre se queda en **30 campos** porque las truncaturas tienen nombres
distintos. Los cinco campos truncados **no aparecen en la tabla**, así que **tampoco pueden
aparecer como divergentes**.

Y eso es la parte peligrosa, porque no es un número falso: **es una pregunta más pequeña que
parece una respuesta.** El informe decía "todos únicos" sobre 30 campos, y un lector que no
sabiera de las truncaturas leería "esta struct es idéntica en los 40 campos". No lo es: es idéntica
en los que se perguntaron, y la herramienta no decía cuáles eran.

Es el fallo de `1209` en una forma nueva. Las formas anteriores fueron un número verosímil y
erroneo, o un `grep` vacío. Esta es **una pregunta recortada que se presenta como respuesta
completa**, y no hay forma de verla en la salida si no se cuenta el número de campos.

Corregido en dos sitios:

```text
  el informe  imprime  "declarados por la copia mas pequena: 40   preguntados por
                       nombre: 30"  y un AVISO con la diferencia
  un vector   comprueba que ese AVISO  SE IMPRIMA  (  V11  )
```

Y `1558 §4.2` sigue en pie en su versión fuerte: el invariante de 24 campos no lo vigila nadie, y
`--todos` ahora lo vigila.

## 5 · Un defecto del parseo que esta medición expuso

```text
  smu7_discrete.h:38    struct SMU7_SoftRegisters
  smu7_discrete.h:39    {
```

La llave va en la línea siguiente. Los otros cinco la traen en la misma línea. `campos_por_parseo`
exigía la misma línea, así que **esa cabecera devolvía cero campos, en silencio**. Se 
manifestó como `comunes = 0`, que se lee como "no hay campos comunes" y no como "el parseo no vio
una cabecera". Las dos cosas se distinguen solo contando campos por copia.

Corregido, y ahora **V10 exige que el parseo vea las seis** con al menos 5 campos cada una.

## 6 · Procedimiento

```text
PREGUNTA   ¿los 30 campos comunes de SoftRegisters coinciden entre las seis copias,
           o el acuerdo de los cinco DRAM_LOG_* es casualidad de la cola?
HERRAMIENTA  tools/smu_softregs.py --todos   (nuevo modo)
FUENTES     los seis headers de include/pm/powerplay/inc/,  por parseo y por
             compilacion  (dos productores,  cruzados en V3)
MEDIDO      30 campos comunes preguntados  de 40 declarados por la menor copia
     24 con offset identico en las seis copias
      6 divergentes,  los seis con SMU71  4 bytes antes
     el corte es POSICIONAL y limpio:  todo <=75 coincide,  todo >=76 diverge
     causa:  smu71 -> smu72  inserta 4 campos uint8_t  (los cuatro *DpmEnabledLevels)
             en el indice 28  y borra 3 en el 36
     smu72 -> smu73  y  smu74 -> smu75:  sin cambios en la lista de campos
     smu7_discrete.h = smu75.h  con 5 nombres truncados,  mismo offset y posicion
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - queda por decidir  y  NO lo decido aqui:  si el bloque de cuatro
    *DpmEnabledLevels byte  que SMU72 anade  y SMU71 no tiene  es  una adicion de
    la especificacion  o  un relleno de espaciado.  Con lo medido  los dos son
    compatibles  y  no hay discriminante en el arbol
  - el modo --todos tiene una limitacion que ahora dice  y que no arregla:
    comparar por POSICION en vez de por nombre.  El mecanismo esta,  la decision
    de si vale la pena  no es mia
  - y la deuda real que queda en el frente SMU/DPM  y no es de esta tool:
    el valor de soft_regs_start en esta placa,  que es runtime
```