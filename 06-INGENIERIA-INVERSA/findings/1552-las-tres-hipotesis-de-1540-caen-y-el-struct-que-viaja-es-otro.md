# 1552 — Las **tres** hipótesis de `1540` caen. La tabla que se envía es `SMU74_Discrete_DpmTable` con longitud recortada a propósito, y **`SMU7_Fusion_DpmTable` no se transmite nunca**: es un buffer de relleno del host

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=RESOLUCION-DE-CONTRADICCION
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CODIGO+RESOLUCION-DE-TRES-HIPOTESIS
MODIFICATIONS=1540 §3 (cerrado entero) · 1547 §5a (cerrado) · 1549 (apoyado)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1540 §3  entero:  las TRES explicaciones que 1540 enumero y no eligio
         quedan REFUTADAS,  cada una por un motivo distinto
CIERRA   1547 §5a  el discriminante que 1547 nombro y postergo
RESOLUCION   el 788 contra el 778  NO es un fallo,  NO es una contradiccion,  y
         NO es un descuido del host.  Es una comparacion entre dos structs que
         nunca estan en la misma transaccion
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · Lo que `1540` dejó abierto, textual

> **NO AFIRMO que eso sea un fallo.** La comparación es la natural —el firmware tiene que
> interpretar el layout que el host escribe— pero **no tengo fuente que declare que
> `usStructureSize` sea directamente comparable a `sizeof` de la struct del host.** Tres
> motivos posibles, y no elijo: `usStructureSize` podría excluir algo; el struct del host podría
> llevar campos de una revisión de SMU7 posterior; o el host podría estar escribiendo 10 bytes
> de más. Sin un consumidor que corte en 788, no se separa.

Las tres se caen, y cada una por su propio motivo. El tercero es el que importa y es el que
no era obvio.

## 2 · Hipótesis 1: "`usStructureSize` podría excluir algo" — REFUTADA

Ya cerrada en `1547`, y la prueba es el uso del propio driver: en cinco sitios resta
`sizeof(ATOM_COMMON_TABLE_HEADER)` de `usStructureSize` y divide por otro `sizeof`
(`amdgpu_atombios.c:99, 130, 161, 197`), y en un sexto compara `offsetof()` contra
`usStructureSize` en un `<` (`amdgpu_atombios.c:1290`).

Si `usStructureSize` excluyera algo, esas seis operaciones no significaría nada.

## 3 · Hipótesis 2: "el struct del host lleva campos de una revisión de SMU7 posterior" — REFUTADA

El mecanismo **existe** y está escrito en `atombios.h:212-213`, sobre
`ucTableContentRevision` — *"Change it only when the table needs to change but the firmware Image
can't be updated, while Driver needs to carry the new table!"*. Pero no aplica:

```text
  ROM   ucTableFormatRev = 7    ucTableContentRev = 1
  HOST  el struct se llama  SMU7_Fusion_DpmTable
```

**El 7 y el 1 concuerdan con el nombre.** ROM y host están en la misma revisión, así que la
divergencia de tamaño no la explica el mecanismo documentado.

## 4 · Hipótesis 3: "el host escribe 10 bytes de más" — REFUTADA, y aquí está

Esta es la que `1547 §5a` nombró y postergó, y la respuesta es que **el host nunca transmite
ese struct**.

### 4.1 · `SMU7_Fusion_DpmTable` no se envía

```text
  smu7_hwmgr.c:743     memset(&(data->dpm_table), 0x00, sizeof(data->dpm_table));
      ->  la UNICA aparicion de  sizeof(data->dpm_table)  en el fichero.  Y es un
          memset en el host,  no un envio.

  smu7_setup_dpm_tables_v0()  :781-867   rellena  data->dpm_table  campo a campo.
                                          NO llama a cgs_write_ind_register,
                                          ni a smu7_copy_bytes_to_smc,  ni pasa
                                          ninguna longitud.  No envia nada.
  smu7_setup_dpm_tables_v1()  :869       lo mismo por su cuenta.
  smu7_populate_and_upload_sclk_mclk_dpm_levels()  :4340-4386
                                          solo manipula el struct en memoria  y
                                          llama a smum_populate_all_{graphic,memory}_levels.

  cgs_write_ind_register  en smu7_hwmgr.c            32 llamadas
  de las cuales tocan data->dpm_table                 0
```

**Cero Transfers de `data->dpm_table`.** Es un buffer de relleno del host: se pone a cero, se
rellena campo a campo, y no sale por ahí.

### 4.2 · Lo que sí se envía es **otro** struct, con longitud recortada a propósito

```c
  pm/powerplay/smumgr/polaris10_smumgr.c:2117-2123
      /* Upload all dpm data to SMC memory.(dpm level, dpm level count etc) */
      result = smu7_copy_bytes_to_smc(hwmgr,
                      smu_data->smu7_data.dpm_table_start +
                      offsetof(SMU74_Discrete_DpmTable, SystemFlags),
                      (uint8_t *)&(table->SystemFlags),
                      sizeof(SMU74_Discrete_DpmTable) - 3 * sizeof(SMU74_PIDController),
                      SMC_RAM_END);
```

Tres cosas, y las tres decisivas:

```text
  a)  EL STRUCT QUE VIAJA ES  SMU74_Discrete_DpmTable.
      No es SMU7_Fusion_DpmTable.  Son dos structs distintos,  como ya se se vio con
      los DRAM_LOG_*,  que estan en ambos  (1549).

  b)  LA LONGITUD NO ES  sizeof.  Es  sizeof(...)  MENOS  3 * sizeof(SMU74_PIDController).
      Es una longitud recortada a proposito,  escrita a mano.  El host decide hasta
      donde llega,  y decide no llegar hasta el final.

  c)  EMPIEZA EN  offsetof(..., SystemFlags),  no en el principio del struct.
```

Y `1540` ya sabia que `SMU74_Discrete_DpmTable` mide otra cosa: su §1 lista el hallazgo `081`
como *"SMU74_Discrete_DpmTable = 1884, no 1120 — corrección"*. **O sea que el struct que sí
transmite ya tenía su tamaño medido y corregido por otro hallazgo, y no es el de esta
discusión.**

### 4.3 · Y la cola `DRAM_LOG_*`, por si acaso

Ya cerrado en `1549`: los cinco valores llegan con **cinco escrituras sueltas** a
`data->soft_regs_start + offsetof(SMU_SoftRegisters, ...)`, no dentro de ninguna tabla.

## 5 · La resolución, en una frase

```text
  1540 comparo:   el usStructureSize = 778  que declara el ROM  para PowerPlayInfo
              con  el sizeof = 788  de  SMU7_Fusion_DpmTable,  en el host.

  La realidad:    SMU7_Fusion_DpmTable  no se transmite.  Es un buffer de relleno.
                  Lo que se transmite es  SMU74_Discrete_DpmTable,  y con una
                  longitud recortada a mano:  sizeof - 3 * sizeof(PIDController).
                  Y la cola DRAM_LOG_*  va por soft_regs_start,  campo a campo.

  =>  los dos numeros comparados  no participan en la misma transaccion.
      La comparacion era natural  y era correcta como comparacion,  pero no
      describe ningun flujo de datos.  NO ES UN FALLO.
```

**El `778` del ROM y el `788` del host siguen siendo los dos que son.** Lo que cambia es que
`1540` losropatchéo a un contrato de host↔SMC y ese contrato no los contiene.

Y una observación que vale más que la resolución: **`1540` tenía razón en que la comparación es
la natural**, porque `usStructureSize` contra `sizeof` es exactamente el contrato de AtomBIOS
—`1547` lo probó— y en general sí lo es. **Lo que no se dio por hecho es que en este caso
concreto los dos `sizeof` en cuestión no son el del struct que viaja.** Ahí está la lección:
el contrato es correcto y la pareja concreta no lo cumplo, y por eso la discrepancia no es un
fallo sino una medida mal elegida.

## 6 · Procedimiento

```text
PREGUNTA   ¿el host escribe 10 bytes de mas?  (hipotesis 3 de 1540)
FUENTES    pm/powerplay/hwmgr/smu7_hwmgr.c:743, 781-867, 869, 4340-4386
           conteo de las 32 llamadas a cgs_write_ind_register  del fichero
           pm/powerplay/smumgr/polaris10_smumgr.c:2117-2123
           pm/powerplay/hwmgr/smu7_hwmgr.c:5489-5528  (1549)
MEDIDO     sizeof(data->dpm_table) aparece  UNA VEZ  y es un memset en el host
     las 32 escrituras indirectas del hwmgr  tocan dpm_table  CERO veces
     smu7_setup_dpm_tables_v0/v1  no envian nada
     lo que se envia  = SMU74_Discrete_DpmTable  con longitud
       sizeof(SMU74_Discrete_DpmTable) - 3*sizeof(SMU74_PIDController)
       empezando en offsetof(..., SystemFlags)
     la cola DRAM_LOG_*  va por soft_regs_start  campo a campo  (1549)
ALCANCE DE LA AUSENCIA (§16)  para decir que el struct no se transmite  mire:
     todo smu7_hwmgr.c          (304 .c revisados  solo los de esta familia)
     smu7_setup_dpm_tables_v0 y _v1  y  populate_and_upload  las tres funciones
     que tocarían el envio
     las 32 llamadas a escritura indirecta  del hwmgr,  una a una
     polaris10_smumgr.c,  que es donde si esta la copia en bloque
     y el unico sizeof(data->dpm_table)  del arbol
   Con eso  PROVEN_ABSENT  para el camino del hwmgr de smu7.  No lo declaro para
   otros smumgr de la familia  que no he revisado uno a uno.
CIERRA   1540 §3 completo,  1547 §5a
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto,  no se escribio nada
RUNTIME      NOT_RUN
LO QUE SIGUE
  - el frente SMU/DPM  queda con una asimetria que conviene escribir aparte:
    el host tiene DOS structs para la misma tabla  (SMU7_Fusion_DpmTable  para
    rellenar,  SMU74_Discrete_DpmTable  para enviar),  y solo el segundo importa
    como formato detransporte.  Por eso el 788  no describe nada del SMC
  - 1540 §5  ya noto que DRAM_LOG_* esta en los dos structs.  Ahora sabemos que solo
    en SMU7_SoftRegisters se usa.  Eso es una tercera copia del mismo nombre en tres
    structs distintos,  y es un mapa pequeno y cerrado que se puede cerrar entero
```