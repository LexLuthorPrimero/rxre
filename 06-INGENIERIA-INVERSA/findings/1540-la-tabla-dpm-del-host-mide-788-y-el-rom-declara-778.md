# 1540 — la tabla DPM del host mide 788 y el ROM declara 778, y los últimos 20 bytes son memoria

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, item 6
CLASSIFICATION=EVIDENCIA-POR-COMPILACION+CONTRADICCION-NUEVA+HOMONIMO
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=item 6 (contrato host<->SMC).  NO toca el 1091 ni el 081: comparan OTROS structs
ESTADO=PROBADO · sizeof(SMU7_Fusion_DpmTable) = 788, por gcc, con pack(1)
       · el ROM declara usStructureSize = 778 para la misma tabla.  Diferencia de 10 bytes
       · smc_layout da 4 huecos, 27 bytes, que el host direcciona pero no escribe
       · los ultimos 20 bytes del struct son CINCO campos DRAM_LOG_* de memoria
       · el limite del ROM cae 2 bytes DENTRO de DRAM_LOG_PHY_ADDR_H
       · y los mismos cinco campos existen tambien en SMU7_SoftRegisters, y el driver los
         alcanza por offsetof(SMU74_SoftRegisters, ...): el struct de SMU74, no el de SMU7
```

## 1. Por que item 6 no es "leer el host", y la herramienta que si lo es

Hay 33 hallazgos previos sobre SMC/SMU/DPM, la zona mas densa del arbol. Antes de escribir, los
relei y mire que comparaban. Los dos que tocan **tamano de tabla** son:

```text
  1091   pp_table (ROM) = 778   contra   PPTable_t (host) = 1240     -> truncada al 62,7 %
  081    SMU74_Discrete_DpmTable = 1884, no 1120                      -> correccion
```

**Ninguno de los dos compara `SMU7_Fusion_DpmTable`.** Uno usa `PPTable_t` y el otro el struct de
SMU74, que es de otra generacion. La comparacion que importa para Polaris12 —el struct que el host
escribe contra el tamaño que el ROM declara para la misma tabla— **no estaba medida.**

La herramienta que si la mide es `tools/smc_layout.py`, y primero le pase `--selftest`.

## 2. La herramienta queda validada contra el compilador

`smc_layout.py --type SMU7_Fusion_DpmTable` reporta `TAMANO=788 CONFIANZA=COMPLETA usos=26`, y sus
offsets. Los contrasto con gcc sobre la cabecera real con `pack(1)`:

```text
  campo                          smc_layout    gcc offsetof     coinciden
  ---------------------------------------------------------------------------
  sizeof(SMU7_Fusion_DpmTable)       788              788          SI
  GraphicsDpmLevelCount               76               76          SI
  GraphicsLevel                       84               84          SI
  FpsLowT                             758              758          SI
  LowSclkInterruptT                   764              764          SI
```

**5 de 5.** Un dato derivado de regex sobre codigo no compilado, contra `offsetof` de gcc. Es la
validacion cruzada que §22 pide, y aqui pasa.

El gcc necesita dos macros que el build define y **ningun header declara**:
`SMU__NUM_SCLK_DPM_STATE` y `SMU__NUM_LCLK_DPM_LEVELS`. Los puse a 8, que es lo que hacen
`smu71`–`smu75`. Es un supuesto y lo declaro: si el build de esta placa usara otros numeros, el
`sizeof` cambiaria. **Pero no puede cambiar en 10 bytes**, porque esos macros solo multiplican los
arrays de niveles, y el struct tiene `GraphicsLevel[224]` ya resuelto.

## 3. La diferencia: 788 contra 778

```text
  ROM, PowerPlayInfo @ 0x9C0A
       usStructureSize   = 778
       ucTableFormatRev  = 7
       ucTableContentRev = 1
       fin de la tabla   = 0x9F14      <-- que es exactamente donde empieza Object_Header,
                                             la siguiente entrada de la master data table

  HOST, sizeof(SMU7_Fusion_DpmTable) = 788
       diferencia                      =  10 bytes
```

**Una consistencia que si importa y sale gratis:** el final declarado de la tabla DPM, `0x9F14`, es
exactamente el offset de `Object_Header`, indice 22 de la master data table. **El tamaño declarado por
el ROM no es arbitrario: termina donde empieza la siguiente tabla.** Eso da confianza en el 778, y por
tanto en que los 788 son 10 de mas.

> **PROBADO por compilacion y por lectura del ROM:** la vista que el host tiene de la tabla DPM
> mide 10 bytes mas que la que el ROM declara para la misma tabla.
>
> **NO AFIRMO que eso sea un fallo.** La comparacion es la natural —el firmware tiene que interpretar
> el layout que el host escribe— pero **no tengo fuente que declare que `usStructureSize` sea
> directamente comparable a `sizeof` de la struct del host.** Tres motivos posibles, y no elijo:
> `usStructureSize` podria excluir algo; el struct del host podria llevar campos de una revision de
> SMU7 posterior; o el host podria estar escribiendo 10 bytes de mas. Sin un consumidor que corte en
> 788, no se separa.

## 4. Los 27 bytes que el host no escribe

`smc_layout --unwritten` da la otra mitad del contrato: **huecos entre campos que el host direcciona
pero no escribe. El firmware los lee sin inicializar.**

```text
  offset  77    1 byte   entre GraphicsDpmLevelCount y UvdLevelCount
  offset 308   20 bytes   entre GraphicsLevel y UvdLevel
  offset 756    2 bytes   entre GraphicsVoltageChangeEnable y FpsLowT
  offset 760    4 bytes   entre FpsLowT y LowSclkInterruptThreshold
                ---
               27 bytes
```

Eso es **el contrato host<->SMC, medido**: 27 bytes cuyo valor decide el firmware y no el host. Los
dos huecos de 760 y 756 estan pegados a la cola, que es donde empieza lo de la seccion siguiente.

## 5. Y la cola es memoria: cinco campos DRAM_LOG

Los ultimos cinco campos del struct, textuales (`smu7_fusion.h:252-256`):

```c
      uint32_t   DRAM_LOG_ADDR_H;
      uint32_t   DRAM_LOG_ADDR_L;
      uint32_t   DRAM_LOG_PHY_ADDR_H;
      uint32_t   DRAM_LOG_PHY_ADDR_L;
      uint32_t   DRAM_LOG_BUFF_SIZE;
```

Con offsets de gcc:

```text
  768..772  DRAM_LOG_ADDR_H          DENTRO del tamaño declarado del ROM (778)
  772..776  DRAM_LOG_ADDR_L          DENTRO
  776..780  DRAM_LOG_PHY_ADDR_H      <-- EL LIMITE DEL ROM CAE AQUI, a mitad del campo
  780..784  DRAM_LOG_PHY_ADDR_L      FUERA
  784..788  DRAM_LOG_BUFF_SIZE       FUERA
```

> **PROBADO: el limite declarado del ROM, 778 bytes, cae dos bytes dentro de `DRAM_LOG_PHY_ADDR_H`,
> y los dos ultimos campos quedan fuera de la tabla que el ROM declara.**

Los bytes que hay ahi en el ROM no son cero:

```text
  offset 768   0x08020000
  offset 772   0x65F40000
  offset 776   0x009E0000
  offset 780   0x00880301      (ya fuera de la tabla)
```

**No los interpreto.** `DRAM_LOG` es un buffer de registro de DRAM; los valores parecen direcciones o
tamanos, pero no hay fuente en el corpus que declare la unidad, y ya me paso cinco veces hoy
asumiendo una.

## 6. Y los mismos cinco campos estan en otro struct, con otro nombre de generacion

```text
  smu7_fusion.h:39    struct SMU7_SoftRegisters     contiene DRAM_LOG_* en las lineas 69-73
  smu7_fusion.h:209   struct SMU7_Fusion_DpmTable   contiene DRAM_LOG_* en las lineas 252-256
```

Los mismos cinco nombres, dos structs. Y el driver los alcanza por el tercero:

```c
  polaris10_smumgr.c:2437    case DRAM_LOG_ADDR_H:
  polaris10_smumgr.c:2438            return offsetof(SMU74_SoftRegisters, DRAM_LOG_ADDR_H);
  polaris10_smumgr.c:2441    case DRAM_LOG_PHY_ADDR_H:
  polaris10_smumgr.c:2442            return offsetof(SMU74_SoftRegisters, DRAM_LOG_PHY_ADDR_H);
```

**`SMU74_SoftRegisters`, no `SMU7`.** La funcion es una tabla de mapeo compartida con el camino
SMU74 y en la rama de polaris10 sigue usando el struct de SMU74. Es el mismo patron que el
`num_banks` del `1528` y el `prt` del `139`: **dos campos con el mismo nombre, structs de
generaciones distintas, y el codigo que enlaza con el equivocado sin querer.**

Me corrijo tambien de una cosa que escribi mal antes de este hallazgo: puse entre parentesis
que el host no escribe ninguno de los cinco. **Es falso**, hay referencias. Lo que no vi al principio
es que van por el struct de SMU74, y eso es lo que hace la trampa.

## 7. Donde queda el item 6

```text
  el host direcciona la tabla campo a campo con offsetof        PROBADO  (smc_layout, 5/5 vs gcc)
  sizeof de la tabla que escribe el host                       PROBADO  788 por gcc
  tamaño que declara el ROM para la misma tabla                 PROBADO  778, y termina donde toca
  bytes que el host NO escribe y el firmware si lee             PROBADO  27, en 4 huecos
  el limite del ROM cae dentro de un campo de memoria           PROBADO  a mitad de DRAM_LOG_PHY_ADDR_H
  por que difieren 788 y 778                                    NOT_DETERMINED, tres hipotesis
  que significan los valores ROM de DRAM_LOG                    NOT_DETERMINED, sin unidad declarada
  que hace el firmware con los 27 bytes                         NOT_IN_CORPUS, y no hay forma de saberlo
```

**El item 6 no se cierra, y por el motivo honesto: el contrato esta medido en el lado del host, y la
semantica del lado del firmware no es alcanzable desde el corpus.** Eso es lo que dice el propio
`smc_layout.py` en su primera linea de salida: *"mide el contrato de memoria. NO dice que hace el
firmware"*. La herramienta avisa de su propio limite antes de que uno se lo pregunte.

Lo que si queda, y es util para un driver propio: **los 788 bytes con su layout exacto campo a campo,
los 27 que el host no toca, y los cinco campos de DRAM de la cola.** Para escribir un driver propio
eso es el 100 % de lo que el host le dice al SMC, y esta medido byte a byte.

## 8. Decision log (§103)

```text
DECISION    publicar la diferencia 788/778 como MEDIDA, sin declararla bug
WHY         las dos cifras estan medidas por vias independientes (gcc y el ROM), y la
            comparacion es la natural pero no esta JUSTIFICADA por ninguna fuente.  Declarar
            el bug seria el atajo que el 1532 critico en el caso opuesto.
ALTERNATIVA  ignorar los 10 bytes porque "el header siempre va por delante".  Descartada: eso
            es una pauta, no una fuente, y no me sirve para cerrar un numero.
DISCriminante  un consumidor que corte la copia en 788, o el codigo de la BIOS.  El
            `099` ya dijo que el retorno de setup de tablas DPM se ignora; si el firmware
            aceptara 788 y truncara, habria que encontrar donde.
CONSECUENCIA  item 6 con 5 de 7 medidos.  Los 2 que faltan son uno de firmware y otro de
            unidad: los dos NOT_IN_CORPUS con la dependencia nombrada.
REVERSIBLE  si resulta que usStructureSize excluye 10 bytes por definicion, la "diferencia" es
            cero y este hallazgo se reduce al hallazgo de los 27 bytes, que sigue valiendo.
```

## 9. El cruce entre items, que es lo que hace util esto

Este hallazgo toca **item 6 (contrato SMC) y item 2 (geometria de memoria) en el mismo byte.** La cola
de la tabla DPM es memoria, y es donde el host y el firmware se separan: el host direcciona hasta el
byte 788, el ROM declara 778, y entre 768 y 788 hay cinco campos de log de DRAM de los que el
proyecto no sabe la unidad.

**Para un driver propio, esa frontera es exactamente lo que hay que escribir a mano**, porque no hay
otro sitio de donde sacarlo: no esta en el driver, no esta en el ROM de forma utilizable, y no esta
en el firmware porque el firmware no esta.
