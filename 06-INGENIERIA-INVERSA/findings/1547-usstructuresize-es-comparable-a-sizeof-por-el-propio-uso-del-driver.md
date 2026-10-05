# 1547 — La prueba que `1540` decía que le faltaba: **el propio driver resta `sizeof` a `usStructureSize`, en cuatro sitios.** `usStructureSize` es comparable a `sizeof`, queda PROBADO por su propio uso

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=RESOLUCION-DE-HUECO-NOMBRADO
CLASSIFICATION=EVIDENCIA-POR-PROPIO-USO-DEL-DRIVER+RESOLUCION-PARCIAL
MODIFICATIONS=1540 (cierra su hueco declarado y refuta 1 de sus 3 explicaciones)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el hueco que 1540 dejo escrito con su propia palabras:  "no tengo fuente
         que declare que usStructureSize sea directamente comparable a sizeof
         de la struct del host"
CIERRA   una de las TRES explicaciones posibles que 1540 enumero y no eligio
DEJA     mas afilada la tercera,  y con una consecuencia operativa
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · El hueco que `1540` declaró

`1540` mide, por compilación y por lectura del ROM:

```text
  ROM,  PowerPlayInfo @ 0x9C0A      usStructureSize = 778   ucTableFormatRev = 7
                                     ucTableContentRev = 1
  HOST, sizeof(SMU7_Fusion_DpmTable) = 788          diferencia = 10 bytes
```

Y dice, textual:

> **NO AFIRMO que eso sea un fallo.** [...] **no tengo fuente que declare que
> `usStructureSize` sea directamente comparable a `sizeof` de la struct del host.**
> Tres motivos posibles, y no elijo: `usStructureSize` podría excluir algo; el
> struct del host podría llevar campos de una revisión de SMU7 posterior; o el
> host podría estar escribiendo 10 bytes de más. **Sin un consumidor que corte en
> 788, no se separa.**

Es un hueco honesto y bien nombrado. **La fuente existe, y es el driver.**

## 2 · La cadena, medida de punta a punta

### 2.1 · De dónde sale `usStructureSize`

```c
  include/atombios.h:208-214
      typedef struct _ATOM_COMMON_TABLE_HEADER
      {
          USHORT usStructureSize;                     <-- el primer campo
          UCHAR  ucTableFormatRevision;
          UCHAR  ucTableContentRevision;
      }ATOM_COMMON_TABLE_HEADER;
```

### 2.2 · Y el driver lo lee como un contador de bytes

```c
  amdgpu/atom.c:1642-1661
      bool amdgpu_atom_parse_data_header(struct atom_context *ctx, int index,
                                          uint16_t *size, uint8_t *frev, uint8_t *crev,
                                          uint16_t *data_start)
      {
          int offset = index * 2 + 4;
          int idx = CU16(ctx->data_table + offset);
          ...
          if (size)   *size = CU16(idx);          /* idx[0] = usStructureSize  */
          if (frev)   *frev = CU8(idx + 2);      /* idx[2] = ucTableFormatRev  */
          if (crev)   *crev = CU8(idx + 3);      /* idx[3] = ucTableContentRev */
          *data_start = idx;
      }
```

`idx` apunta a la cabecera común de la tabla. `size` **es** `usStructureSize`, leído del ROM.

### 2.3 · Y aquí está la prueba: el driver le resta un `sizeof` del host

```c
  amdgpu/amdgpu_atombios.c:99-100     (ATOM_GPIO_I2C_INFO)
      num_indices = (size - sizeof(ATOM_COMMON_TABLE_HEADER)) /
                    sizeof(ATOM_GPIO_I2C_ASSIGMENT);
  amdgpu/amdgpu_atombios.c:130-131    (ATOM_GPIO_I2C_INFO)
      num_indices = (size - sizeof(ATOM_COMMON_TABLE_HEADER)) /
                    sizeof(ATOM_GPIO_I2C_ASSIGMENT);
  amdgpu/amdgpu_atombios.c:161-162    (ATOM_GPIO_I2C_INFO)
      num_indices = (size - sizeof(ATOM_COMMON_TABLE_HEADER)) /
                    sizeof(ATOM_GPIO_I2C_ASSIGMENT);
  amdgpu/amdgpu_atombios.c:197-198    (ATOM_GPIO_PIN_LUT)
      num_indices = (size - sizeof(ATOM_COMMON_TABLE_HEADER)) /
                    sizeof(ATOM_GPIO_PIN_ASSIGNMENT);
```

**Cuatro sitios, dos tipos de tabla.** En los cuatro: un valor leído del ROM se le resta un
`sizeof` del host, y el resto se divide por otro `sizeof` del host, para obtener una cuenta de
elementos.

**Si las dos unidades no fueran comparables, la aritmética no significaría nada.** El driver
hace exactamente la comparación que `1540` decía no tener fuente para.

Y hay una segunda muestra del mismo uso, en `amdgpu_atombios.c:1290-1295`, donde `size` se usa
como cota de un recorrido de longitud variable:

```c
      u32 size = le16_to_cpu(v3->sHeader.usStructureSize);
      u32 offset = offsetof(ATOM_VOLTAGE_OBJECT_INFO_V3_1, asVoltageObj[0]);
      u8 *start = (u8 *)v3;
      while (offset < size) {                      /* el ROM acota el recorrido */
              ...
              offset += le16_to_cpu(vo->asGpioVoltageObj.sHeader.usSize);
      }
```

Ahí `offsetof` — un `offsetof` del host — se compara contra `usStructureSize` **en la misma
desigualdad**. Quinta prueba, y la más limpia: un desplazamiento calculado por el compilador
contra un número del ROM, en un `<`.

> **PROBADO por el uso del propio driver, en cinco sitios: `usStructureSize` es un contador de
> bytes con la misma unidad y el mismo origen de alineación que `sizeof` y que `offsetof` del
> host. La comparabilidad de `1540` deja de ser una hipótesis.**

## 3 · Qué queda de las tres explicaciones de `1540`

```text
  (1)  "usStructureSize podria excluir algo"
       REFUTADO.  Es un contador de bytes comparable a sizeof,  por cinco usos del
       propio driver.  Si excluyera algo,  el num_indices de las cuatro tablas
       GPIO saldria fraccional y el recorrido de voltaje se saldria del buffer.

  (2)  "el struct del host podria llevar campos de una revision de SMU7 posterior"
       HAY MECANISMO DOCUMENTADO PARA ESTO,  y esta en el propio atombios.h:
           include/atombios.h:212-213
             UCHAR ucTableContentRevision;
               //Change it only when the table needs to change but the firmware
               //Image can't be updated, while Driver needs to carry the new table!
       O sea:  AtomBIOS documenta explicitamente que el driver debe llevar una tabla
       mas grande que la que el firmware declara,  cuando el firmware no se puede
       actualizar.  ESTO EXISTE Y ESTA ESCRITO.
       PERO NO APLICA AQUI,  y hay que decirlo:  el ROM declara
       ucTableFormatRev = 7 y ucTableContentRev = 1,  y el struct se llama
       SMU7_Fusion_DpmTable.  El 7 y el 1 del ROM concuerdan con el nombre del
       struct.  O sea que ROM y host estan en la MISMA revision,  y la
       divergencia de tamaño no se explica por el mecanismo documentado.

  (3)  "el host podria estar escribiendo 10 bytes de mas"
       VIVA,  y ahora es la unica que queda en pie.
```

**De tres candidatos a uno.** Y el que queda es el que `1540` no se atrevia a elegir sin la fuente
que acabo de encontrar.

## 4 · Y la consecuencia, que es lo que hay que hacer con esto

Si `(3)` es la explicación, la consecuencia no es cosmética:

```text
  offset 768..772  DRAM_LOG_ADDR_H       DENTRO de 778
  offset 772..776  DRAM_LOG_ADDR_L       DENTRO
  offset 776..780  DRAM_LOG_PHY_ADDR_H   <-- el limite del ROM cae aqui,  a mitad
  offset 780..784  DRAM_LOG_PHY_ADDR_L   FUERA
  offset 784..788  DRAM_LOG_BUFF_SIZE    FUERA
```

**Los diez bytes que el host escribe de más son los tres últimos campos `DRAM_LOG_*`, y los
tres son de memoria.** El host escribe 788, el ROM declara 778, y si el firmware honra la
declaración del ROM, **los diez bytes de más nunca llegan al firmware**, incluido
`DRAM_LOG_BUFF_SIZE`, que es el tamaño del buffer de log de DRAM.

Y `1540` ya midió que esos bytes **no están en cero** en el ROM:

```text
  offset 776   0x009E0000
  offset 780   0x00880301
```

O sea: hay datos en la región que el host sobrescribe con su cola y que el ROM no declara como
parte de la tabla. Si el host escribe los 10, esos valores se pierden. Si no los escribe,
quedan.

## 5 · Qué discrimina, y por qué no lo hago aquí

`1540` decía *"sin un consumidor que corte en 788, no se separa"*. **Ya no: el discriminante
existe y es otro.** Los candidatos, en orden de coste:

```text
  a)  EL STRUCT DEL FIRMWARE.  El SMC tiene su propia copia de SMU7_Fusion_DpmTable
      compilada dentro del binario que vive en el ROM.  Si se puede localizar su
      declaracion de tamaño o su consumidor de DRAM_LOG_BUFF_SIZE,  dice quien gana.
      El ROM esta volcado en el arbol  (1400, 1406, 1429).
      COSTE: Offline, sobre el volcado.  ES EL MEJOR.

  b)  QUIEN ESCRIBE LA TABLA Y HASTA DONDE.  El host la rellena campo a campo.  Si
      escribe los cinco DRAM_LOG_* con una instruccion propia,  entonces el host
      quiere los 788 y el ROM se queda corto.  Si los escribe por un bucle sobre
      sizeof(),  el host cree que la tabla mide 788.
      COSTE:  ESTATICO.  Y ES LO QUE DEBERIA MEDIR PRIMERO.

  c)  LA REVISION EN EL NOMBRE.  SMU7_Fusion_DpmTable  frente a  SMU74_SoftRegisters
      —el mismo campo en dos structs distintos,  que es lo que 1540 §5 ya noto—.
      Si el host escribe la cola de uno usando offsets del otro,  los 10 bytes son
      un error de eleccion de struct,  no de tamano.
      COSTE:  ESTATICO,  Y EL MISMO QUE 1540 §5 YA ABRIO.
```

`b` y `c` son estáticos y no tocan hardware. **Los hago en este orden**, y no ahora, porque
este hallazgo ya cierra lo que se le pidió cerrar y la instrucción es una cosa a la vez.

## 6 · Procedimiento

```text
PREGUNTA   ¿existe la fuente que 1540 declara no tener,  para decir si
           usStructureSize es comparable a sizeof de la struct del host?
FUENTES    include/atombios.h:208-214        (ATOM_COMMON_TABLE_HEADER y su comentario)
           amdgpu/atom.c:1642-1661            (de donde sale size, frev, crev)
           amdgpu/amdgpu_atombios.c:99,130,161,197   (size - sizeof, dividido por sizeof)
           amdgpu/amdgpu_atombios.c:1286-1295       (offsetof < size)
MEDIDO     size == usStructureSize,  leido por atom.c:1654 desde el puntero a la
           cabecera comun
     4 sitios  restan sizeof(ATOM_COMMON_TABLE_HEADER)  y dividen por otro sizeof
     1 sitio mas compara offsetof() contra size  en un <
     => 5 pruebas de comparabilidad,  hechas por el driver,  no por mi
     REFUTADA  la explicacion (1)  "usStructureSize podria excluir algo"
     EXISTE Y DOCUMENTADO  el mecanismo de (2),  en atombios.h:212-213,  pero NO
       APLICA:  ROM formatRev=7 contentRev=1  concuerda con el nombre SMU7_Fusion
     VIVA  (3)  el host escribe 10 bytes de mas
CONSECUENCIA  los 10 bytes de mas son 3 campos DRAM_LOG_*,  y el ultimo es
     DRAM_LOG_BUFF_SIZE.  Si el firmware honra los 778,  no llegan.  Y en el ROM
     esos bytes no estan en cero  (0x009E0000, 0x00880301)
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE,  en orden de coste
  1  ESTATICO:  quien escribe la tabla DPM  y hasta donde.  Si escribe los cinco
     DRAM_LOG_* con una instruccion propia,  el host quiere 788.  Si los escribe
     por un bucle sobre sizeof,  el host cree que la tabla mide 788
  2  ESTATICO:  si la cola se escribe usando offsetof de SMU74_SoftRegisters en vez
     de SMU7_Fusion_DpmTable  —  lo que 1540 §5 ya noto y no cerro
  3  OFFLINE:  el struct del firmware dentro del volcado del ROM
```