# 1549 — Los cinco `DRAM_LOG_*` llegan al SMC con **cinco escrituras sueltas a `soft_regs_start`**, no con la tabla DPM. Eso **desvanece la alarma de `1547 §4`**, y de paso corrige **dos errores míos**: busqué en `amdgpu/`, donde el SMU7 de Polaris12 **no está**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CORRECCION + RESOLUCION-DE-HUECO-NOMBRADO
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CODIGO+AUTOCORRECCION-DOS-VECES
MODIFICATIONS=1547 §4 y §5c (corregidos) · confirma 1540 en la atribución de struct
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CORRIGE  1547 §4  su consecuencia,  que era alarmista y estaba mal
CORRIGE  1547 §5c  descartada:  no es un error de eleccion de struct
DESRULEO LOS DIEZ BYTES DE MAS NO SON "CAMPOS DRAM_LOG_ QUE NO LLEGAN":
         el driver no los escribe dentro de la tabla,  los escribe aparte
CONFIRMA 1540  en su atribucion de struct  (que yo habia puesto en duda dos
         mensajes antes  y era mi error)
CIERRA   el discriminante (b) de 1547 §5:  ya esta medido
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Lo que hace el driver con los cinco campos

`smu7_notify_cac_buffer_info()`, `pm/powerplay/hwmgr/smu7_hwmgr.c:5489-5528`:

```c
  5496  struct smu7_hwmgr *data = (struct smu7_hwmgr *)(hwmgr->backend);
  5498  cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
  5499                  data->soft_regs_start +
  5500                  smum_get_offsetof(hwmgr,
  5501                                  SMU_SoftRegisters, DRAM_LOG_ADDR_H),
  5502                  mc_addr_hi);
  ...  (cinco escrituras identicas en forma,  5498-5526)
  5522  cgs_write_ind_register(hwmgr->device, CGS_IND_REG__SMC,
  5523                  data->soft_regs_start +
  5524                  smum_get_offsetof(hwmgr,
  5525                                  SMU_SoftRegisters, DRAM_LOG_BUFF_SIZE),
  5526                  size);
```

**Tres cosas, y las tres importan:**

```text
  a)  SON CINCO ESCRITURAS INDIVIDUALES,  no una copia de la tabla.
  b)  EL DESTINO ES  data->soft_regs_start  +  offsetof(SMU_SoftRegisters, ...)
      O sea  la region de SoftRegisters del SMC,  que NO es la tabla DPM.
  c)  EL offsetof se toma de  SMU_SoftRegisters,  no de  SMU7_Fusion_DpmTable.
```

**El punto (c) es el que importa.** El driver **no usa** la posición que esos cinco campos
tienen en `SMU7_Fusion_DpmTable`. Usa la que tienen en `SMU7_SoftRegisters`. Son dos structs
distintos con los mismos cinco nombres, y el código elige explícitamente el segundo.

## 2 · Por qué esto desvanece la alarma de `1547 §4`

`1547 §4` escribió, textual:

> Los diez bytes que el host escribe de más son los tres últimos campos `DRAM_LOG_*`, y los
> tres son de memoria. Si el firmware honra la declaración del ROM, **los diez bytes de más
> nunca llegan al firmware**, incluido `DRAM_LOG_BUFF_SIZE`.

**Eso es falso, y la razón es (a) y (b) de §1.** Los valores de `DRAM_LOG_*` llegan al SMC por
`soft_regs_start`, que es un destino distinto del que la tabla DPM acota. Que la tabla se
declare de 778 no limita nada de lo que va por `soft_regs_start`.

Es decir: **el truncamiento de 778 a 788, si existe, no puede cortar los `DRAM_LOG_*`.**

Y la observación de `1540` —de que en el ROM esos bytes no están en cero, `0x009E0000` y
`0x00880301` en 776 y 780— sigue siendo un hecho, pero **pierde su lectura dramática**: esos
bytes son la cola de una struct que nadie escribe ahí por ese campo.

**Esto es lo que `1547 §5` había predicho y named mal.** Escribí que el discriminante (c) era
"si la cola se escribe usando `offsetof` de otro struct, los 10 bytes son un error de elección
de struct". **La realidad es la tercera cosa**: el driver no escribe la cola por la tabla en
absoluto, así que no hay error de elección de struct ni de tamaño **en ese camino**.

## 3 · Error mío, primero: busqué en el subárbol equivocado

Medí esto y sale:

```text
  $ grep -rn "SMU7_Fusion_DpmTable" amdgpu/     ->  NINGUNA REFERENCIA
  $ grep -rn "DRAM_LOG_"        amdgpu/*.c     ->  NINGUNA ESCRITURA
```

Y estaba a punto de escribir que **`amdgpu/` no usa `SMU7_Fusion_DpmTable` para nada**, lo que
hubiera sido una refutación de `1540` publicada y falsa.

Lo que pasa es que **`amdgpu_smu.c` no existe en este árbol**, ni `smu_v7_0.c`:

```text
  amdgpu/  tiene 304 .c   pero sus ficheros de SMU son  smuio_v9_0, smuio_v11_0 ... smu_v13_0_10
                          o sea  SOLO generacion nueva.  No hay smu_v7_0.c,  ni amdgpu_smu.c
```

**Y el SMU7 de Polaris12 vive en otro sitio:**

```text
  pm/powerplay/inc/smu7_fusion.h            la struct
  pm/powerplay/hwmgr/smu7_hwmgr.c           el codigo que la usa
  pm/powerplay/smumgr/polaris10_smumgr.c    el smumgr de la familia
  pm/Makefile:42   PM_LIBS = swsmu powerplay legacy-dpm   ->  SI se compila
```

**Un falso negativo por buscar en el sitio equivocado.** Y es el error con más consecuencias
potenciales de los que he hecho: habría desmentido un hallazgo ajeno, correcto, por un `grep` que
volvía vacío.

La lección es la de siempre y ya la he pagado demasiadas veces, pero en una versión nueva: **un
cero de `grep` no es evidencia de ausencia hasta que has comprobado que el fichero que
contendría la referencia existe.** Aquí ni siquiera había fichero. Y hay un refuerzo concreto: la
ausencia tiene que ser **localizada**, y esta era global, pero el `grep` no lo sabía.

## 4 · Error mío, segundo: `1540` tenía razón sobre el struct

Al recorrer `smu7_fusion.h` hacia atrás para localizar a qué struct pertenecen las líneas
252-256, mi escaneo buscando el literal `"typedef struct"`paró en la línea 207 y atribuyó el
bloque a `SMU7_Fusion_StateInfo`:

```text
  207  typedef struct SMU7_Fusion_StateInfo SMU7_Fusion_StateInfo;   <- lo que mi escaneo dio
  209  struct SMU7_Fusion_DpmTable {                                 <- NO lleva "typedef"
  284  typedef struct SMU7_Fusion_DpmTable SMU7_Fusion_DpmTable;     <- el typedef esta aqui
  258  };                                                            <- cierra en 258
```

**La clave de mi escaneo estaba mal**: la línea 209 abre el struct **sin** la palabra `typedef`
—el `typedef` está en 284, al final—, así que la búsqueda saltó al struct anterior.

La realidad, que confirma `1540` exactamente:

```text
  smu7_fusion.h:209   struct SMU7_Fusion_DpmTable {
  smu7_fusion.h:252-256   los cinco DRAM_LOG_*
  smu7_fusion.h:258   };
  smu7_fusion.h:284   typedef struct SMU7_Fusion_DpmTable SMU7_Fusion_DpmTable;
```

**Los offsets 768..788 de `1540` son de `SMU7_Fusion_DpmTable`, como decía.** No tenía duda.

## 5 · Lo que queda abierto, y es menos de lo que parecía

```text
  ABIEN RESUELTO   comparabilidad de usStructureSize con sizeof          (1547)
  ABIEN RESUELTO   los DRAM_LOG_* no viajan por la tabla DPM             (aqui)
  ABIEN RESUELTO   no es un error de eleccion de struct                   (aqui, 1547 §5c cae)
  ABIEN RESUELTO   la atribucion de struct de 1540                        (aqui, §4)

  SIGUE ABIERTO    la tabla DPM  de 788 bytes  SI se envia,  y CUANTOS bytes
                   se envian de verdad
```

Y la siguiente medición está identificada y es estática:

```text
  smu7_copy_bytes_to_smc()  se llama  UNA SOLA VEZ  en smu7_hwmgr.c,  y en :5483,
  escribiendo  DisplayWatermark  con  offsetof(SMU74_Discrete_DpmTable, DisplayWatermark)
  y una longitud explicita.   O sea  un campo suelto,  no la tabla.

  dpm_table_start  se usa  UNA SOLA VEZ  tambien,  en la misma linea 5483.

  =>  la tabla DPM de 788 bytes  NO se copia en bloque por ahi.  El envio real
      esta en  smu7_setup_dpm_tables_v0()  (781)  y  _v1()  (869).
      La pregunta es que longitud escriben.
```

Eso es lo que queda, y es una medición de un solo fichero, sin hardware.

## 6 · Procedimiento

```text
PREGUNTA   (discriminante b de 1547 §5)  ¿quien escribe la cola DRAM_LOG_* y
           hasta donde?
FUENTES    pm/powerplay/hwmgr/smu7_hwmgr.c:5489-5528  (la funcion completa)
           grep de DRAM_LOG_ en todo el arbol,  con los subarboles separados
           pm/powerplay/inc/smu7_fusion.h:207,209,258,284
           pm/Makefile:42      ls amdgpu/ | grep smu
MEDIDO     la cola se escribe con 5 cgs_write_ind_register  sueltas
     destino = data->soft_regs_start + offsetof(SMU_SoftRegisters, ...)
     el offsetof es de SMU_SoftRegisters,  NO de SMU7_Fusion_DpmTable
     smu7_copy_bytes_to_smc:  1 llamada,  campo suelto
     dpm_table_start:          1 uso,  la misma linea
     amdgpu/ NO tiene amdgpu_smu.c ni smu_v7_0.c  ->  el SMU7 no esta ahi
     smu7_fusion.h:209 abre el struct SIN "typedef";  el typedef esta en 284
AUTOCORR.  dos,  y las dos haberian publicado cosas falsas:
  (a)  "amdgpu/ no usa SMU7_Fusion_DpmTable"  era un falso negativo por buscar en el
       subarbol equivocado.  El fichero que contendria la referencia ni existe alli.
  (b)  "las lineas 252-256 son de SMU7_Fusion_StateInfo"  era mi escaneo con una clave
       equivocada.  1540 tenia razon.
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE
  - ESTATICO,  un solo fichero:  smu7_setup_dpm_tables_v0() (:781)  y _v1() (:869).
    Que longitud escriben,  y si esa longitud es sizeof(SMU7_Fusion_DpmTable)  = 788.
    Si lo es,  los 10 bytes SI salen  y la pregunta (3) de 1540 queda confirmada.
    Si es menor,  la pregunta se cierra en negativo y el 788 del host  es un struct
    con cola que nadie envia
  - y queda por ahi el heredado de 1540 §5:  que el mismo campo este en
    SMU7_Fusion_DpmTable  y en SMU7_SoftRegisters,  y solo en el segundo se use
```