# 1477 — el sobre de voltaje de la placa, y un bug del driver que se ejecuta en esta tarjeta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-ROM+EVIDENCIA-DE-SILICIO+BUG-DE-DRIVER+REVISION-DE-UN-REVISOR
TRACK=STATIC(revkit/capturas/amdgpu_vbios.txt) + MEDIDO(1448) · cero escrituras
GENERADO=2026-10-05
AFECTADO=09-POWER-CLOCKS/                              (el sobre de voltaje, cerrado)
         06-INGENIERIA-INVERSA/findings/1448-*         (VDDGFX 700 mV: era el MINIMO declarado)
         06-INGENIERIA-INVERSA/findings/1468-*         (se cierra: el ROM declara su tamano)
         06-INGENIERIA-INVERSA/findings/1416/1418      (nada)
ESTADO=PROBADO · VDDGFX/VDDC: 700 -> 1075 mV, con DOS campos independientes que coinciden
       · el 700 mV MEDIDO es exactamente ulMinVddc: la tarjeta esta en su suelo declarado
       · techo = 1075 mV => 53.6 % de margen sobre el punto en reposo, no 0 %
       · MVDDC (raíl de la GDDR5): 1350 -> 1500 mV, en mV planos, sin el Q2
       · y un BUG VIVO: confusion de tipos en atomctrl_get_leakage_vddc_base_on_leakage,
         con un llamante real en smu7_hwmgr.c:2905, que es el camino que usa esta tarjeta
```

## 1. EL SOBRE DE VOLTAJE, y es el dato de rendimiento que faltaba

De `ASIC_ProfilingInfo` @ `0xA6E4`, rev **3/6**, `usStructureSize = 268` — y el tamaño declarado
por el struct en el árbol es exactamente 268.

```text
ulMaxVddc             @0xA6E8 = 0x0001A3EC   /100 =  1075 mV
ulMinVddc             @0xA6EC = 0x00011170   /100 =   700 mV
usMaxVoltage_0_25mv   @0xA7E6 = 4300  x0.25  =  1075 mV
```

> **Dos campos independientes, calculados por dos caminos distintos, dan 1075 mV.** Eso cross-valida
> la unidad **y** los offsets del struct a la vez. No es un número del que me fié: es una
> coincidencia que no podía fabricarse.

Y contra el silicio:

```text
MEDIDO en la placa (hallazgo 1448, 30 muestras, desv 0.0):   VDDGFX = 700 mV
DECLARADO en el ROM:                                         ulMinVddc/100 = 700 mV
```

> **El 700 mV que medí es exactamente el suelo declarado.** No es "un voltaje bajo": es **el
> mínimo que el propio BIOS dice que esta tarjeta necesita**, y la tarjeta está sitting on it.

**Consecuencia para §77.** El punto de partida del trabajo de rendimiento no es un dato arbitrario
sino el suelo del sobre declarado. Y el techo es **1075 mV**: **53.6 % de margen** sobre el punto
en reposo, no 0 %. Eso cambia qué se puede esperar de un barrido de voltaje, y es la primera vez
que el proyecto tiene un número de margen en vez de una impresión.

### 1.1 La trampa del Q2, y por qué aquí NO aplica

Hay un `÷4` (Q2, mV con 2 bits fraccionarios) en `ppatomctrl.c:1194-1195`, pero está **guardado
por `CHIP_TONGA`/`CHIP_FIJI`** y lee `ATOM_ASIC_PROFILING_INFO_V3_3`. **Polaris nunca toma esa
rama**: `ppatomctrl.c:1200-1201` divide por **100**.

**Aplicar ÷4 daría 268.75 mV, equivocado por ~2.6×.** Y el comentario `0.01mv` del header existe
sólo en `V3_5` (`atombios.h:5511-5512`); `V3_6` (`atombios.h:5555-5556`) no lo lleva.

### 1.2 El raíl de la memoria: 1350 → 1500 mV

De `VoltageObjectInfo` @ `0xA7F0`, rev 3/1, `usStructureSize = 52`, cadena de
`ATOM_VOLTAGE_OBJECT_HEADER_V3 {UCHAR type; UCHAR mode; USHORT size}` que **cierra exactamente en
los 52 bytes**:

```text
obj0 @0xA7F4  type=1 VDDC   mode=7 SVID2  size=12
obj1 @0xA800  type=4 VDDCI  mode=7 SVID2  size=12
obj2 @0xA80C  type=2 MVDDC  mode=0 GPIO_LUT  size=24   -> cierra en 0xA824 = fin del bloque
```

`usVoltageValue` está documentado **"in mV"** (`atombios.h:5128`) y el driver **no divide**:
`amdgpu_atombios.c:1408` es un `le16_to_cpu` pelado. **No hay `/4` en todo el camino de voltaje.**

```text
LUT0 @0xA818  ulVoltageId=0x00000000  usVoltageValue = 1350 mV
LUT1 @0xA81E  ulVoltageId=0x40000000  usVoltageValue = 1500 mV
```

Dos códigos CG-VID que sólo difieren en el bit 30 de la máscara. Coherente con GDDR5.

> **Y un `PROVEN_ABSENT` con consequence:** `VoltageObjectInfo` **no declara ningún objeto
> VDDGFX** (tipos presentes: 1, 4, 2; falta el 5 = `VOLTAGE_TYPE_VDDGFX`). Esta tabla no
> restringe el VDDGFX en absoluto. El único que lo restringe es `ASIC_ProfilingInfo`.

## 2. UN BUG VIVO DEL DRIVER, en esta tarjeta

Y aquí tengo que corregir al revisor antes que nada.

### 2.1 El revisor inventó un símbolo

El informe llama a la función **`atomctrl_get_evd_voltage_limit`**. Ese símbolo **no existe en
ninguna parte**:

```text
$ grep -rn 'get_evd_voltage_limit' pm/ include/ amdgpu/
  (nada)
```

El nombre real es **`atomctrl_get_leakage_vddc_base_on_leakage`** (`ppatomctrl.c:1119`). Y mi
primera verificación falló por el mismo motivo que él: **empecé a leer el bloque en la línea
1128, en mitad de la función, así que no vi el nombre y creí el suyo.** Los dos cometieron el mismo
error por motivos distintos. Lo declaro porque es la segunda vez hoy que un nombre inventado
casi entra como cita.

### 2.2 El bug, verificado en el código

La función castea el bloque a un struct **V2_1** y lo indexa con offsets de V2_1
(`ppatomctrl.c:1132-1158`):

```c
profile = (ATOM_ASIC_PROFILING_INFO_V2_1 *)smu_atom_get_data_table(hwmgr->adev, ix, ...);
if ((profile->asHeader.ucTableFormatRevision >= 2) &&
    (profile->asHeader.ucTableContentRevision >= 1) &&
    (profile->asHeader.usStructureSize >= sizeof(ATOM_ASIC_PROFILING_INFO_V2_1))) {
        leakage_bin  = (u16 *)((char *)profile + profile->usLeakageBinArrayOffset);
        vddc_id_buf  = (u16 *)((char *)profile + profile->usElbVDDC_IdArrayOffset);
        vddc_buf     = (u16 *)((char *)profile + profile->usElbVDDC_LevelArrayOffset);
        if (profile->ucElbVDDC_Num > 0) {
                for (i = 0; i < profile->ucElbVDDC_Num; i++) {
                        if (vddc_id_buf[i] == virtual_voltage_id) {
                                for (j = 0; j < profile->ucLeakageBinNum; j++) {
                                        if (efuse_voltage_id <= leakage_bin[j]) {
                                                *vddc = vddc_buf[j * profile->ucElbVDDC_Num + i];
```

**La guarda es un límite inferior de tamaño, y una tabla V3_6 de 268 bytes lo satisface:**

```text
la guarda                     3>=2  6>=1  268 >= sizeof(V2_1)   ->  PASA
el bloque de esta tarjeta     rev 3/6, usStructureSize = 268

offset 8  de V2_1  ucElbVDDC_Num          -> en V3_6 cae dentro de ulMinVddc
                                          -> lee 0x70 = 112,  que es > 0  -> ENTRA
offset 9  de V2_1  usElbVDDC_IdArrayOffset-> resto de ulMinVddc, leido como UCHAR/UCHAR
                                          -> puntero DENTRO del bloque, leido como u16[112]
```

Y el índice final es `j * profile->ucElbVDDC_Num + i`, con `ucElbVDDC_Num = 112`: **con `j`
creciendo, la lectura sale del bloque de 268 bytes.** Es una lectura fuera de límites sobre un
buffer derivado del ROM.

### 2.3 Y es CÓDIGO VIVO en esta tarjeta

Esto es lo que decide la gravedad, y lo comprobé:

```text
smu7_hwmgr.c:2896  static int smu7_get_elb_voltages(struct pp_hwmgr *hwmgr)
smu7_hwmgr.c:2901          if (atomctrl_get_leakage_id_from_efuse(hwmgr, &efuse_voltage_id) == 0) {
smu7_hwmgr.c:2905                  atomctrl_get_leakage_vddc_base_on_leakage(hwmgr, &vddc, &vddci, ...
```

**Existe el llamante, y esta tarjeta va por el camino smu7** — el log de arranque del proyecto lo
dice: `smu_v1_0_0(powerplay)`. **No es código muerto: se ejecuta en el arranque de esta GPU.**

El resultado es que `vddc` recibe un `u16` basura (o 0), el llamante lo guarda en
`data->vddc_leakage.actual_voltage[count]`, y el conteo se incrementa.

> **`NOT_DETERMINED` y lo digo:** si eso produce un daño visible. La lectura fuera de límites
> está `PROBADA` leyendo el código; las consecuencias observables, no. No he ejecutado nada ni
> he mirado un `oops`, y no voy a afirmar un fallo que no he visto. Lo que sí afirmo es que
> **la aritmética de punteros y índices está mal**, y que es alcanzable en esta tarjeta.

**Aviso de alcance, y es el mismo de siempre:** este corpus está podado, así que *no hay
llamantes* significaría "no hay llamantes en los ficheros presentes". Aquí sí hay, y está en el
mismo fichero, a 300 líneas. Eso **no** es un caso de podado: es un caso real.

## 3. `MC_InitParameter` NO es una tabla de timings

`@0x9FB2`, rev 2/1, 729 bytes. El struct es `ATOM_MC_INIT_PARAM_TABLE_V2_1`
(`atombios.h:7520-7528`), y es sólo **cabecera**: sus dos últimos campos son punteros, y los 709
bytes restantes son lo que apuntan.

```text
+0x04  ulMCUcodeVersion        = 0x00B4DE20
+0x08  ulMCUcodeRomStartAddr   = 0x00037000
+0x0C  ulMCUcodeLength         = 0x00001F8E   (8078 B)
+0x10  usMcRegInitTableOffset  = 25  -> 0x9FCB   (primer registro, verificado por aritmetica)
+0x12  usReserved              = 20  -> 0x9FC6   = la cadena ASCII "D090"
```

**`"D090"`** — que casa con `D09001 Lexa XL A0` (0x0119) y con `WEIKENG_LEXA_D090_…` (0x01F8).
El comentario del header dice que ahí va un `ATOM_INIT_REG_BLOCK`; **para este ROM no es cierto**,
es una cadena.

Y luego **115 de 115 registros resuelven** contra `gmc_8_1_sh_mask.h`, en una array de
`ATOM_REG_INIT_SETTING {USHORT usRegIndex; ULONG ulRegValue}` de 6 bytes. El índice es el offset
crudo del registro, confirmado por `0x0994 → mmMC_CITF_MISC_VM_CG`.

**Y el resultado que cambia el nombre del bloque: cero registros de timing DRAM.**

```text
18 registros con "TIMING" en el nombre en gmc_8_1_d.h:
  mmMC_SEQ_RAS_TIMING 0x0A28   mmMC_SEQ_CAS_TIMING 0x0A29   mmMC_ARB_DRAM_TIMING 0x09DD
  mmMC_PHY_TIMING_D0/D1/D2 0x0ACC-0x0ACE   mmMC_SEQ_TRAIN_TIMING 0x0A40   + variantes _LP
NINGUNO aparece en la array.   PROVEN_ABSENT.
```

Es una **tabla de arbitraje y créditos del memory-hub**: `mmMC_HUB` ×68, `mmMC_ARB` ×22,
`mmMC_CITF` ×8, y los clientes de lectura/escritura. Los **8 MCD** (`MCDS..MCDV`, `MCDW..MCDZ`)
de `mmMC_HUB_RDREQ_CNTL = 0x70003E1C` son **colas write-data del hub, no canales DRAM** — no los
confundas.

**Ancho de datos: `NOT_DETERMINED`.** Nada en los 115 registros codifica 128 bits. Los únicos
números por carril son créditos (`mmMC_HUB_WDP_CREDITS = 0x72722828` → VM0=40, VM1=40,
STOR0=114, STOR1=114), que son recuentos de crédito, no anchura.

**Y una anomalía que no se forceja:** 12 bytes en `0x9FDD` parseados como dos registros dan
índices `0x0B00` y `0x0BD3`, y ambos caen en un **hueco sin asignar** de `gmc_8_1_d.h`
(`0x0B00..0x0C7F` no lo cubre ninguna definición). Los vecinos documentados más cercanos son
`0x0AFF` y `0x0C80`. Los únicos candidatos en todo el árbol son de Navi/Vega, otra generación.
**`NOT_DETERMINED`.** No desplacé la array para absorberlos.

## 4. El spread-spectrum está muerto por dos razones, y la segunda es la real

`ASIC_InternalSS_Info` @ `0xA824`, rev 3/1, 40 bytes → `ATOM_ASIC_SS_ASSIGNMENT_V3` de 12 bytes,
**3 entradas exactas**:

```text
#  @       ulTargetClockRange  Spread%  Rate(10Hz)  ClockIndication
0  0xA828  0x00FFFFFF         125      3000       1 = ASIC_INTERNAL_MEMORY_SS
1  0xA834  0x00FFFFFF          50      3150       2 = ASIC_INTERNAL_ENGINE_SS
2  0xA840  0x00FFFFFF         380      3150       7  (sin #define en este arbol)
```

Los tres `ulTargetClockRange = 0x00FFFFFF` = **`CLOCK_RANGE_HIGHEST`**, el centinela que significa
"cualquier reloj". Eso, más el stride limpio de 12, confirma el layout V3. Si el driver lo mirara:
**1.25 % de down-spread a 30 kHz en reloj de memoria**, 0.50 % a 31 kHz en el de gráficos.

**Razón 1** (la que ya sabía): `PPLL_SS_Info` es el índice 18 y el ROM tiene `0x0000` ahí.
**Razón 2, y es la que muerde:** `amdgpu_atombios.c:911-918` hace puerta por
`mode_info.firmware_flags`, y ese valor **es 0 en esta tarjeta**:

```text
firmwareinfo (índice 4) @0x9974 es rev 2/2
amdgpu_atomfirmware.c:63 exige frev==3 && crev>=1 || frev>3   ->  FALLA, devuelve 0
```

> **El dato del spread-spectrum está presente, bien formado, y apagado por una comprobación de
> revisión de OTRA tabla.** Y la palabra de capacidad en `0x99C4` (`0x401F`) **sí** tiene
> `ATOM_BIOS_INFO_MEMORY_CLOCK_SS_SUPPORT` y `…ENGINE_CLOCK_SS_SUPPORT` puestas. O sea: **el ROM
> declara que lo soporta y el driver no lo lee, por una razón que no tiene que ver con él.**

## 5. Cierre del tamaño de la imagen: el ROM declara dónde acaba

`ServiceInfo` @ `0xA8F4` describe 17 huecos. **El hueco 16 es `(offset=0xE5BE, length=66)`, y lo
he encontrado en el fichero en `0xA941`:**

```text
0xE5BE + 0x42 = 0xE600 = 58 880 B
longitud de la captura      = 0xE600 = 58 880 B     COINCIDE
```

> **El ROM describe su propia imagen ATOM y dice que acaba exactamente donde acaba la captura.**
> Esto cierra la pregunta que el hallazgo 1468 dejó como `NOT_DETERMINED` ("¿son 58 880 bytes la
> imagen entera o un truncamiento?"): **la parte ATOM de la imagen es exactamente 58 880 bytes.**
>
> Con una distinción que hay que hacer: eso **no** dice que el dispositivo ROM sea de 58 880
> bytes. Un ROM de 128 KiB puede tener la imagen ATOM ocupando sólo los primeros 58 880. Lo que
> queda `NOT_DETERMINED` es el **dispositivo**; lo que queda **cerrado** es la **imagen**.

Y en esa luz, `ulMCUcodeRomStartAddr = 0x00037000` **queda fuera de la imagen ATOM**. No lo
resuelvo: puede ser una dirección de memoria y no un offset de fichero.

## 6. `VRAM_UsageByFirmware`: 32 KB y 32 KB

`@0x9B3E`, rev 1/5, `ATOM_FIRMWARE_VRAM_RESERVE_INFO_V1_5`, 12 bytes exactos:

```text
ulStartAddrUsedByFirmware = 0x001FFFE0
usFirmwareUseInKb         = 32 KB
usFBUsedByDrvInKb         = 32 KB
```

`0x001FFFE0 & ATOM_VRAM_OPERATION_FLAGS_MASK (0xC0000000) = 0`, así que
`amdgpu_atombios.c:1686-1691` toma la ruta simple: **`usage_bytes = 32768`**, y como es distinto
de cero, el valor por defecto de `20*1024` de la línea 1694 **no** aplica.

> **La reserva de framebuffer del driver en esta tarjeta es de 32 KB, no los 20 KB que el driver
> usaría por defecto.** Es un número que importa para el dimensionado de buffers, y sale de un
> campo que nadie había leído.

## 7. Procedencia

```text
fichero  revkit/capturas/amdgpu_vbios.txt  58 880 B
structs  include/atombios.h:5255-5268   ATOM_ASIC_PROFILING_INFO_V2_1  (el struct del bug)
         include/atombios.h:5552-5621   ATOM_ASIC_PROFILING_INFO_V3_6  (el de verdad, 268 B)
         include/atombios.h:5110-5114   ATOM_VOLTAGE_OBJECT_HEADER_V3
         include/atombios.h:5128        usVoltageValue "in mV"
         include/atombios.h:4347-4352   ATOM_FIRMWARE_VRAM_RESERVE_INFO_V1_5
         include/atombios.h:7514-7528   ATOM_REG_INIT_SETTING, ATOM_MC_INIT_PARAM_TABLE_V2_1
         include/atombios.h:6685-6694   ATOM_ASIC_SS_ASSIGNMENT_V3
driver   pm/powerplay/hwmgr/ppatomctrl.c:1119-1158   la función y la guarda
         pm/powerplay/hwmgr/smu7_hwmgr.c:2896-2918   EL LLAMANTE
         pm/powerplay/smumgr/polaris10_smumgr.c:1807-1812  seis constantes hardcodeadas
         amdgpu/amdgpu_atomfirmware.c:63  la puerta de firmware_flags
         amdgpu/amdgpu_atombios.c:1408    le16_to_cpu pelado, sin /4
medido   VDDGFX = 700 mV, 30 muestras, desv 0.0  (hallazgo 1448)
```

```text
ESTADO=PROBADO · sobre de VDDGFX/VDDC 700 -> 1075 mV.  DOS campos independientes dan 1075
       (ulMaxVddc/100 y usMaxVoltage_0_25mv x 0.25), lo que cross-valida unidad y offsets
CORROBORADO  el 700 mV MEDIDO es exactamente ulMinVddc/100.  No es un voltaje bajo: es el suelo
       declarado, y el techo son 1075 mV => 53.6 % de margen en vez de 0 %
NUEVO  MVDDC (rail GDDR5) 1350 -> 1500 mV, en mV planos: el Q2 no aplica aqui y ÷4 daria
       268.75 mV, ~2.6x equivocado.  El Q2 solo es Tonga/Fiji (ppatomctrl.c:1194-1195)
PROVEN_ABSENT  VoltageObjectInfo no declara ningun objeto VDDGFX (tipos 1,4,2; falta el 5)
BUG DE DRIVER, VIVO  atomctrl_get_leakage_vddc_base_on_leakage (ppatomctrl.c:1119) castea el
       bloque a V2_1 con una guarda que es un limite inferior de tamano; un bloque V3_6 de 268 B
       la satisface, ucElbVDDC_Num lee 112 dentro de ulMinVddc, entra al bucle, e indexa
       vddc_buf[j*112+i] sobre un buffer de 268 B.  LLAMANTE REAL en smu7_hwmgr.c:2905, y esta
       tarjeta va por smu7.  NO es codigo muerto.  Las consecuencias observables: NOT_DETERMINED
REVISION  el revisor se invento el simbolo "atomctrl_get_evd_voltage_limit"; no existe.  El
       nombre real es atomctrl_get_leakage_vddc_base_on_leakage.  Mi primera verificacion fallo
       igual: lei desde la linea 1128, en mitad de la funcion
NUEVO  MC_InitParameter es una tabla de ARBITRAJE Y CREDITOS del memory-hub, no de timings:
       PROVEN_ABSENT sobre los 18 registros con TIMING en el nombre.  Los 8 MCD son colas
       write-data del hub, NO canales DRAM
NUEVO  el spread-spectrum esta muerto por una puerta de REVISION de otra tabla:
       firmware_flags == 0 porque firmwareinfo es rev 2/2 y amdgpu_atomfirmware.c:63 exige 3.1+.
       Y la palabra de capacidad del ROM (0x401F) SI dice que lo soporta
NUEVO  VRAM_UsageByFirmware = 32 KB de firmware, 32 KB de framebuffer del driver (no los 20 KB
       por defecto).  0x001FFFE0 & 0xC0000000 == 0, luego no es SRIOV y aplica la ruta simple
CIERRA  1468 §9.9 "si la captura es el ROM entero": ServiceInfo describe 17 huecos y el 16 es
       (0xE5BE, 66), que acaba en 0xE600 = 58 880 = la longitud exacta de la captura.  La
       IMAGEN ATOM es exactamente 58 880 B.  El DISPOSITIVO ROM sigue NOT_DETERMINED
NOT_DETERMINED  si el bug de voltaje produce un dano visible; los 12 bytes de 0x9FDD; el ancho de
       datos, que no esta codificado en MC_InitParameter; el sentido de ulMCUcodeRomStartAddr
LIMITE  nada de esto se ha ejercido.  CERO escrituras, CEROmodule load, la GPU no se toco
RIESGO  ninguno en esta operacion
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active
Siguiente  1) el bug de voltaje es el hallazgo mas accionable del lote.  Decidir si merece una
           prueba controlada (que implicaria cargar modulo) o queda documentado
         2) el techo de voltaje 1075 mV es un objetivo de benchmark: el margen es real y medible,
           y es el camino natural del §77 para el reloj de graficos
         3) el sobre de MVDDC 1350-1500 mV y su LUT de 2 entradas: solo dos puntos, y el reloj
           de memoria llega a 1500 MHz.  Si el rail tiene dos puntos, tiene DOS estados
```

## 8. Lo que esto cambia para el objetivo

Dos cosas, y las dos son de rendimiento:

**Una.** El trabajo de rendimiento parte ahora de un número, no de una impresión: **700 mV es el
suelo y 1075 mV es el techo**, y la tarjeta está en el suelo. El margen es **53.6 %**. El barrido
de voltaje deja de ser "probemos a ver hasta dónde da" y pasa a ser un plan con dos puntos
verificados por el propio BIOS.

**Dos.** Hay un **bug de lectura fuera de límites que se ejecuta en el arranque de esta tarjeta**,
en el camino de voltaje, porque una guarda de tamaño satisfecha por un layout que ya no es el
mismo. Eso no es un hallazgo de reverse engineering: es un hallazgo sobre el driver que corre, y
por tanto es información que el objetivo del proyecto necesita aunque no sea del ASIC.

**Ninguna de las dos requiere tocar la GPU.** Ambas salieron de 52 bytes y 729 bytes de un
fichero que estaba en el árbol desde el principio.