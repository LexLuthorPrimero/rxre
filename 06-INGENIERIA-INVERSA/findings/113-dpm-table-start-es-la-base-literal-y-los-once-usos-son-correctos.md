# 113 · La pregunta que 104 dejo abierta: `dpm_table_start` es la base literal, y los once usos son correctos

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

CORRIGE A `104-once-usos-de-dpm-table-start-y-el-hueco-de-108.md` · CORROBORA Y COMPLETA A
`087-los-tres-pidcontroller-son-del-firmware.md` (fichero de otro agente, **no modificado**)

## Que se corrige, y que no

`104` **no afirmo** sin matices que los once usos estuvieran desviados. Su propio texto lo
dice en `:148-158`: si el error fuera real y tan grave, *Tonga habria arrancado mal*, y
marca la pregunta que lo decide como `CONNECTION_MISSING` y `NOT_DETERMINED`.

**La pregunta queda ahora contestada, y contestada por el otro lado.**

Lo que se retira son cuatro etiquetas `PROVEN_DERIVED` y una recomendacion de codigo de
`104`, no su prosa. Y hay que decirlo con precision: **el error de `104` no fue afirmar de
mas en el texto, fue etiquetar como `PROVEN` unas consecuencias que el propio documento
decia que dependian de un `NOT_DETERMINED`.**

## La pregunta, tal cual la dejo `104`

> `dpm_table_start` es la direccion **literal** del campo `DpmTable` de la cabecera del
> firmware, o la direccion a la que hay que sumar 108 para llegar al primer campo que el
> host escribe?

Eso decide todo lo demas. Y se responde **sin el firmware**, por consistencia interna.

## Los datos, medidos otra vez

Vuelvo a medirlo, sin apoyarme en `087`, para que la comprobacion sea independiente:

```
sizeof(SMU74_Discrete_DpmTable)          = 1884    (gcc)
offsetof(SMU74_Discrete_DpmTable, GraphicsPIDController) = 0
offsetof(SMU74_Discrete_DpmTable, MemoryPIDController)   = 36
offsetof(SMU74_Discrete_DpmTable, LinkPIDController)     = 72
offsetof(SMU74_Discrete_DpmTable, SystemFlags)           = 108
offsetof(SMU74_Discrete_DpmTable, VRConfig)              = 112
```

Y el codigo (`polaris10_smumgr.c:2117-2122`):

```c
result = smu7_copy_bytes_to_smc(hwmgr,
                smu_data->smu7_data.dpm_table_start + offsetof(SMU74_Discrete_DpmTable, SystemFlags),
                (uint8_t *)&(table->SystemFlags),
                sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
                SMC_RAM_END);
```

Cuatro offsets consecutivos a 36 de distancia: `0, 36, 72, 108`. Tres PID y luego
`SystemFlags`. Y **`3 * sizeof(PIDController) = 108 = offsetof(SystemFlags)`**, escrito
simbolicamente en el argumento de tamano.

## Las dos lecturas, y por qué solo una es coherente

**(A) `dpm_table_start` es la base literal de la tabla de 1884 bytes.**

```
[dpm+0   , dpm+108 )  tres PIDController   -> los escribe el FIRMWARE
[dpm+108 , dpm+1884)  el resto             -> lo escribe el HOST, 1776 B
```

El origen y el destino usan **el mismo offset**: `&table->SystemFlags` es el byte 108 de la
struct, y `dpm + offsetof(SystemFlags)` es el byte 108 desde `dpm`. La copia es
simetrica. Los tres PID estan **dentro** de la tabla que describen.

**(B) Hay que sumar 108 para llegar al primer campo que el host escribe.**

```
[dpm-108 , dpm+0   )  donde estarian los tres PID, FUERA de la tabla
[dpm+0   , dpm+1776)  lo que escribe el host, 1776 B
```

Aqui los tres controladores quedarian **108 bytes antes del comienzo de su propia tabla**.

## El discriminante: por que (B) no es una disposicion sino una incoherencia

El argumento mas fuerte no es aritmetico, es de alcance.

`087` demostro, por recuento sobre todo el subarbol `pm/powerplay`, que hay **cero
accesos a campo** de `PIDController` en ficheros `.c`: las seis apariciones son la
expresion del tamano. El host **no puede** escribir los tres PID, en ningun sitio, nunca.

Aplicando eso a (B): si la region del firmware fuera de 1776 bytes, **no existiria
ningun camino por el que los tres PID pudieran recibir un valor del host**. No seria una
decision de particion, porque no habria particion posible: el host tiene
`sizeof(DpmTable)` bytes, le cede 1776, y los 108 restantes **no tendrian destino**.

Y hay mas: en (B), el origen `&table->SystemFlags` (byte 108 de la struct) se empareja
con `dpm + 108` (byte 108 desde `dpm`), mientras que el byte 0 de la struct, que si
existe, queda **sin ningun destino en la SRAM**. Habria un desplazamiento de 108 entre
las dos bases **y un agujero de 108 bytes en el origen**. En (A) no hay ninguno de los
dos.

**Conclusion: (A).** `dpm_table_start` es la base literal de la tabla, la struct del host
modela exactamente la imagen en memoria del firmware, y **no hay que sumar ni restar 108**.

## Lo que esto retira

| etiqueta de `104` | estado ahora |
|---|---|
| `SMC_GRAPHICS_LEVEL_OVERRUNS_ACPI_AND_MEMORY = PROVEN_DERIVED` | **REFUTED** |
| `SMC_MEMORY_LEVEL_OVERRUNS_LINK_LEVEL = PROVEN_DERIVED` | **REFUTED** |
| `SMC_VR_CONFIG_HITS_VR_HOT_LEVEL = PROVEN_DERIVED` | **REFUTED** |
| `SMC_BOOT_MVDD_HITS_CLOCK_STRETCHER = PROVEN_DERIVED` | **REFUTED** |
| `SMC_DPM_OFFSET_MIXES_REFERENCE_FRAMES = PROVEN` | **REFUTED** |
| `SMC_DPM_OFFSET_HOLE_NOT_COMPENSATED = PROVEN` | la descripcion es cierta, la implicacion no se sigue |
| `SMC_WHETHER_FIRMWARE_COMPENSATES_108 = NOT_DETERMINED` | **cerrada: (A)** |
| `SMC_ALL_ROUTES_COPY_FROM_SYSTEM_FLAGS = PROVEN` | **se sostiene**, y ahora por el motivo correcto |

Los cuatro `REFUTED` caen por la misma razon: cada uno computa `offsetof(campo) + 108` y
consulta que hay ahi. Ese `+ 108` es **la CONCLUSION que se estaba comprobando**, usada
como premisa. Sumar 108 a un offset y mirar que hay, **no puede fallar**: si la lectura
es correcta, dara lo que la lectura predice. **Es la forma circular de `104`**, y es la
septima vez que aparece el mismo error de base, esta vez en mi propio trabajo reciente.

### La prueba numerica que cierra el caso, y es la mas simple

No hace falta el argumento de la region inalcanzable. **Los arrays empotran exacto en la
struct**, medido:

```
offsetof(SMU74_Discrete_DpmTable, GraphicsLevel)    = 236    8 x 56 = 448 B  -> [236, 684)
offsetof(SMU74_Discrete_DpmTable, MemoryACPILevel)  = 684
offsetof(SMU74_Discrete_DpmTable, MemoryLevel)      = 708    4 x 24 =  96 B  -> [708, 804)
offsetof(SMU74_Discrete_DpmTable, LinkLevel)        = 804
```

```
236 + 448 = 684 = offsetof(MemoryACPILevel)      EXACTO
708 +  96 = 804 = offsetof(LinkLevel)            EXACTO
```

**Los dos campos que `104` declara invadidos empiezan exactamente donde termina el array
anterior.** Byte a byte, sin sobrante.

Eso es lo que hace la refutacion incontestable, y explica por que `104` no podia
encontrarlo: para ver que un array se sale hay que mirar **donde empieza el campo
siguiente**, y en este caso coincide con el final **redondeando al multiploplo de 4 de la
propia struct**. Un desplazamiento de 108 no dejaria esa coincidencia; la habria roto.

Lo que `104` reporto fue, literalmente, que el array "invade `MemoryACPILevel` (24 B)".
Y `MemoryACPILevel` esta en 684, que es donde el array **termina**. Los 24 B empiezan en
684, no en 236.

Igual con `MemoryLevel`: la invasion de 108 B sobre `LinkLevel` (que empieza en 804)
exigiria que el array llegase a 912. Llega a 804.

## Y el punto mas urgente: hay una recomendacion de codigo que se retira

`104` recomienda, para un driver propio, una funcion que **resta** 108:

```c
static inline uint32_t smc_addr(const struct polaris10_smumgr *s,
                                size_t offsetof_campo)
{
        return s->smu7_data.dpm_table_start
                        + offsetof_campo
                        - offsetof(struct SMU74_Discrete_DpmTable, SystemFlags);
}
```

**Se retira por completo.** Con la lectura (A), ese `- 108` **introduce** un
desplazamiento real: cada campo caeria 108 bytes antes de su sitio, que es exactamente el
fallo que `104` creia estar corrigiendo. Un driver propio que siguiera esa receta
escribiria la tabla DPM desplazada.

Lo que sobrevive de `104` no es la aritmetica, es la **disciplina**:

- **Una sola funcion** para convertir un campo en direccion. Correcto, y ahora con la
  operacion simple:

```c
static inline uint32_t smc_addr(const struct polaris10_smumgr *s,
                                size_t offsetof_campo)
{
        return s->smu7_data.dpm_table_start + offsetof_campo;
}
```

- **Que el compilador fuerce a pasar por ahi.** Sigue siendo la unica defensa real, porque
  el error de coordenadas es silencioso por naturaleza.
- **Que la funcion este probada contra el layout real.** Sigue siendo la leccion de `104`:
  comparar nombres de campos no detecta un error de base. Eso no cambia con esta
  correccion; cambia **que base hay que comprobar**.

## Y una comprobacion de correspondencia que si se sostiene

`104` afirmo que el offset minimo alcanzado por una escritura del host es 108 y que
ninguna baja de ahi. **Lo he vuelto a medir por via distinta**, con `smc_copy_scope` y los
offsets de gcc, y se sostiene:

| escritura | destino | offset |
|---|---|---:|
| `:2118` (la herramienta decia `:2115`; corregido al anclar la llamada) | `dpm_table_start + offsetof(SystemFlags)` | 108 |
| `:140` | `dpm_table_start + offsetof(VRConfig)` | 112 |
| `:147`/`:1046`/`:2594` | `dpm_table_start + offsetof(GraphicsLevel)` | 236 |
| `:155`/`:1215`/`:2597` | `dpm_table_start + offsetof(MemoryLevel)` | 708 |
| `:164` | `dpm_table_start + offsetof(BootMVdd)` | 1592 |
| `:2398` (la herramienta decia `:2396`; corregido al anclar la llamada) | `dpm_table_start + offsetof(LowSclkInterruptThreshold)` | 1692 |

**Minimo 108. Ninguno por debajo.** Y esa propiedad **solo es esperable bajo (A)**: en (B),
los 108 bytes iniciales de la struct serian precisamente la region que el firmware
gestionaria, y que el host dejara sin tocar por coherencia, asi que tampoco lo distingue.
Lo que si hace es que **ninguna escritura del host depende de lo que haya en `[0, 108)`**,
que es justo lo que `087` afirma.

## Lo que sigue sin determinarse

Esto **no** cierra el contenido de la region. Sigue `NOT_IN_CORPUS`:

- Que valores tiene el firmware en `[dpm+0, dpm+108)`.
- Si los tres PID estan activos, o solo el de graficos.
- Si el firmware lee los tres o solo uno: **que haya tres no implica que los tres se
  usen**.
- `FW_SMU_INTERPRETATION` sigue abierto.

Eso es coherente con `087`, que tampoco lo cierra, y con `111`: **no hay ni una sola
lectura de verificacion en toda la ruta**, asi que el contenido de esa region no es
observable desde el host ni siquiera con placa, sin instrumentacion nueva.

## Clasificacion

- `DPM_BASE_IS_LITERAL_TABLE_BASE = PROVEN_DERIVED`: la lectura (A). Se sostiene porque en
  (B) los 108 bytes de la struct no tendrian destino en la SRAM, y el host no tiene
  ningun acceso a campo PID con el que escribirlos.
- `DPM_STRUCT_MODELS_FIRMWARE_IMAGE_EXACTLY = PROVEN_DERIVED`: origen y destino comparten
  el offset 108; no hay desplazamiento ni agujero entre las dos bases.
- `DPM_OFFSET_MINIMUM_TOUCHED_IS_108 = PROVEN_DERIVED`: 6 destinos, minimo 108, ninguno
  por debajo. Medido con `smc_copy_scope` mas offsets de gcc.
- `DPM_SUBTRACTION_NAMES_ITS_OWN_REASON = PROVEN`: `sizeof(DpmTable) - 3*sizeof(PID)`
  aparece **identico en las seis generaciones** (Tonga, Iceland, Fiji, CI, VegaM,
  Polaris12), con la misma estructura de destino `dpm + offsetof(SystemFlags)` y origen
  `&table->SystemFlags`.
- `DPM_FOUR_RUNNINGS_REFUTED = REFUTED`: los cuatro `PROVEN_DERIVED` de `104`.
- `DPM_REFERENCE_FRAMES_DO_NOT_MIX = REFUTED`: `SMC_DPM_OFFSET_MIXES_REFERENCE_FRAMES`.
- `DPM_104_SMC_ADDR_SUBTRACTION_WITHDRAWN = REFUTED`: la funcion recomendada restaria 108
  e introduciria el desplazamiento que pretendia evitar.
- `FW_SMU_INTERPRETATION = NOT_IN_CORPUS`: sin cambios. El contenido de `[0, 108)` sigue
  sin determinarse.

## Lo que esto obliga a hacer en un driver propio

1. **Modelo la region del firmware como una region, con su propietario.** Los 108 bytes
   de cabeza no son "un hueco" ni "algo que hay que compensar": son la zona de los tres
   controladores PID, **propiedad del firmware**, y por tanto **reservada**. `087` lo
   formula bien: *se ignoran como contenido y se respetan como espacio*.
2. **La unica operacion de coordenadas es `base + offsetof(campo)`, sin correccion.** Si
   aparece un `+ 108` o un `- 108` explicito, es que alguien esta mezclando dos bases, y
   hay que averiguar cuales.
3. **Antes de afirmar un desplazamiento, comprobar que las dos bases no estan ya
   alineadas.** Este documento es el argumento: si el origen es `&campo` y el destino es
   `base + offsetof(campo)`, las dos bases estan alineadas **por construccion**, y buscar
   que hay en `offsetof + 108` no puede fallar.

La tercera es la generalizacion. Un desplazamiento solo es real si **el codigo lo
introduce**. Aqui el codigo no lo introduce: usa `offsetof`, que ya es la posicion
correcta dentro del tipo. `104` busco un `+ 108` en un sitio donde la struct **ya era** el
desplazamiento.