# 1574 — BASELINE, sin RXRE: la cadena completa de `soft_regs_start`, hasta el registro y el offset. **Y la hoja es una dirección, o sea que el DRAM log va a `SMC_RAM[soft_regs_start + 80]`**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=BASELINE-PRE-REGISTRATION
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+EVIDENCIA-POR-COMPILACIÓN+PRE-REGISTRACIÓN
MODIFICATIONS=ninguno.  Este hallazgo ES el baseline, y se congela aquí
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno.  El binario de gcc se compilo en
                              /tmp/opencode/,  fuera del arbol
PARTE     BASELINE del experimento de RXRE.  Registrado ANTES de usar RXRE,
          y no se toca despues.  Si RXRE coincide,  el valor probado es la
          velocidad y la trazabilidad.  Si no coincide,  el desacuerdo es el
          hallazgo
PREGUNTA   ¿de donde sale soft_regs_start  y cual es la cadena
           producer → artifact → consumer → representation → evidence?
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · La cadena, completa

```text
  CONSUMIDOR     smu7_hwmgr.c:5498-5526   cgs_write_ind_register(..., CGS_IND_REG__SMC,
                       data->soft_regs_start + offsetof(SMU74_SoftRegisters, DRAM_LOG_*),  valor)
                 5 escrituras,  offsets 80 / 84 / 88 / 92 / 96      <- de 1564,  por gcc
                 ademas :1170  :1186  HandshakeDisables   :1280  :4119  :4705  :4710

  PRODUCTOR      polaris10_process_firmware_header()      polaris10_smumgr.c:2492
                     :2510  smu7_read_smc_sram_dword(hwmgr,
                              SMU7_FIRMWARE_HEADER_LOCATION
                                + offsetof(SMU74_Firmware_Header, SoftRegisters),
                              &tmp, SMC_RAM_END)
                     :2516  data->soft_regs_start = tmp
                     :2517  smu_data->smu7_data.soft_regs_start = tmp

  PRIMITIVA      smu7_read_smc_sram_dword()                smu7_smumgr.c:229
                     :233  smu7_set_smc_sram_address(hwmgr, smc_addr, limit)
                     :235  *value = cgs_read_register(hwmgr->device, mmSMC_IND_DATA_11)
                     smu7_set_smc_sram_address()          smu7_smumgr.c:38
                     :43   cgs_write_register(hwmgr->device, mmSMC_IND_INDEX_11, smc_addr)
                     :44   PHM_WRITE_FIELD(SMC_IND_ACCESS_CNTL, AUTO_INCREMENT_IND_11, 0)

  REPRESENTACION SMU74_Firmware_Header                     smu74.h:559-591
                     Digest[5] · Version · HeaderSize · Flags · EntryPoint · CodeSize
                     ImageSize · Rtos · SoftRegisters · DpmTable · FanTable · ...
                     offsetof(SoftRegisters) = 48      POR GCC
                     sizeof(SMU74_Firmware_Header) = 180  POR GCC

  ARTEFACTO      la dword en SMC_RAM[ 0x20000 + 48 ]  =  SMC_RAM[ 0x20030 ]

  EVIDENCIA      lo que falta es EL VALOR de esa dword,  y solo el valor.
                 Dos accesos a registro  y ya esta:
                     escribir  mmSMC_IND_INDEX_11 = 0x1AC   con 0x20030
                     leer     mmSMC_IND_DATA_11  = 0x1AD
```

**`SMU7_FIRMWARE_HEADER_LOCATION = 0x20000` es idéntico en los cuatro headers** — `smu7.h:166`,
`smu73.h:520`, `smu74.h:594`, `smu75.h:488`. No hay ambigüedad por generación.

## 2 · Lo que cambia el cuadro: `soft_regs_start` es una DIRECCIÓN

No es un desplazamiento dentro de un buffer del host. **Es el valor que el firmware escribió en su
propio header**, y dice dónde está la región de soft-registros dentro de la SRAM del SMC.

```text
  nivel 1   SMC_RAM[ 0x20030 ]        = soft_regs_start     (lo escribe el firmware)
  nivel 2   SMC_RAM[ soft_regs_start + 80 ]  = DRAM_LOG_ADDR_H
```

O sea que el DRAM log **no está en una dirección calculable**: está en una dirección que el
firmware decide. Y el header del firmware **es lo que dice dónde está cada cosa** — también
`DpmTable` (offset 52), `mcRegisterTable` (68), y cinco tablas más.

Eso conecta con `1552`: `dpm_table_start` sale del mismo sitio (`polaris10_smumgr.c:2506`), y es
la base que se le suma a `offsetof(SMU74_Discrete_DpmTable, ...)`. **El host no calcula ninguna de
esas bases: las lee del firmware.** Es un patrón, no un caso.

## 3 · La segunda asimetría de GFX8, y es del mismo tipo que `1546`

```text
  mmSMC_IND_INDEX_11 = 0x1AC    en smu_7_1_1_d.h:179  smu_7_1_2_d.h:91  smu_7_1_3_d.h:94
  mmSMC_IND_DATA_11  = 0x1AD    en smu_7_1_1_d.h:180  smu_7_1_2_d.h:92  smu_7_1_3_d.h:95
```

**No hay un `smc_8_0_d.h`.** Los registros del SMC salen de los headers **SMU7.1**, igual que los
del controlador de memoria salían de `gmc_8_1_d.h` en `1546`.

```text
  GFX8 es PRESTADO en:   GMC   -> gmc_8_1_d.h       (1546, 1548)
                         SMC   -> smu_7_1_*_d.h      (este hallazgo)
  GFX8 es NATIVO en:     GCA   -> gfx_8_0_d.h  y  gfx_8_0_sh_mask.h
```

**El tercer bloquenative/prestado, y el mismo patrón.** Eso convierte la asimetría de `1546` de
"un caso" en una regla, y esa regla es utilizable: para GFX8, un registro que no esté en
`gfx_8_0_*` hay que buscarlo en la cabecera prestada del bloque correspondiente, y el grafo de
includes decide cuál.

## 4 · Contabilidad de esfuerzo, sin adornar

```text
  RONDAS DE MEDICION      8
  COMPILACIONES          2  (una fallida por un fallo mio de shell)
  GREPS DIRIGIDOS        14
  RESPUESTAS EN RED       3  (por que no hay pfn,  por que no hay smc_8_0_d.h,
                              y una linea 793 que resulto ser una red herring)
  ERRORES MIOS           2
    (a)  un pipeline  gcc ... | grep | sed  con  ||  al final:  el || nunca se
         dispara porque sed devuelve 0,  y el binario no corrio.  Me dio la
         sensacion de "no compila" cuando si compilaba
    (b)  busque el despacho de smumgr por "pfn"  y no existe en este arbol;  perdi
         dos rondas en una ruta que no era la
  MINUTOS DE TRABAJO EFECTIVO   ~12
```

Y lo que **no** encontré, que es parte del baseline honesto:

```text
  NO VERIFICADO   que Polaris12 entre por polaris10_smumgr.c.  Encontre que
                  smu7_hwmgr.c:55 incluye polaris10_smumgr.h  (grafo de includes,
                  lo cual es el mecanismo que he usado toda la sesion),  pero no
                  segui la asignacion del puntero de funciones hasta el chip.
  NO VERIFICADO   la definicion del producer  smu7_set_smc_sram_address  con
                  respecto al limite:  la asercion dice  limit > smc_addr+3,  y
                  SMC_RAM_END  no lo medi
  NO VERIFICADO   que el valor de  SMC_RAM[0x20030]  sea coherente con el rango
                  que el propio codigo valida
```

## 5 · Procedimiento

```text
PREGUNTA   ¿de donde sale soft_regs_start?
FUENTES    grep de la ASIGNACION  (  no del uso  )  ->  6 sitios,  uno por smumgr
           de familia;  el de Polaris12 es polaris10_smumgr.c
           la funcion que contiene la linea 2510  ->  polaris10_process_firmware_header,  :2492
           smu7_read_smc_sram_dword  ->  smu7_smumgr.c:229  y  su helper  :38
           smu74.h:559-591  para el struct del firmware header
           gcc con offsetof,  para los offsets  ->  no a ojo
           grep de SMU7_FIRMWARE_HEADER_LOCATION  en los cuatro headers
           grep de mmSMC_IND_{INDEX,DATA}_11  ->  y descubri que viven en smu_7_1_*
MEDIDO     offsetof(SMU74_Firmware_Header, SoftRegisters)  = 48      POR GCC
           sizeof(SMU74_Firmware_Header)                     = 180    POR GCC
           SMU7_FIRMWARE_HEADER_LOCATION = 0x20000  en los 4 headers,  identico
           SMC_RAM[0x20000 + 48] = SMC_RAM[0x20030]
           mmSMC_IND_INDEX_11 = 0x1AC   mmSMC_IND_DATA_11 = 0x1AD
           el productor  ES  MMIO:  cgs_read_register  y  cgs_write_register
           los registros NO estan en gfx_8_0_*:  estan en smu_7_1_{1,2,3}_d.h
NO SE USO  RXRE.  Ninguna linea de tools/rxre/.  Este es el punto de partida
           contra el cual se mide.
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - el experimento:  repetir ESTA pregunta por la interfaz publica de RXRE,  y
    medir si llega al mismo producer con menos trabajo  y si el explain() aguanta
  - lo que queda abierto de este baseline  y hay que decir  no lo cierra RXRE:
    la asignacion del pfn por chip,  y el valor de SMC_RAM_END
```