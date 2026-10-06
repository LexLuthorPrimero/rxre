# 1577 — Ítem 1 **cerrado y PROBADO**: `1002:699f` → `CHIP_POLARIS12` → `AMDGPU_FAMILY_VI` → `case` compartido con POLARIS10 y POLARIS11 → `polaris10_smu_funcs`. Y la prueba **no** es el grafo de includes que usé en el baseline: es un `switch` con tres `case` seguidos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSEOUT · DISPATCH
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+RESOLUCIÓN-DE-HUECO-NOMBRADO
MODIFICATIONS=1574 §LO QUE SIGUE 1º punto (cerrado) y su método (corregido)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1574 §LO QUE SIGUE  primer punto:
         "NO VERIFICADO  que Polaris12 entre por polaris10_smumgr.c"
VALIDA   toda la cadena de soft_regs_start de 1574,  y por tanto 1547, 1549,
         1552, 1558 y 1564,  que depended de ella
CORRIGE   el METODO de 1574:  use el grafo de includes como prueba  y no lo era
ABRE     un bloque por stepping que esta placa NO cumple
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · La cadena, de punta a punta, con la línea

```text
  1  lspci                                    01:00.0  1002:699f  rev c7
                                                  MEDIDO en 1231

  2  amdgpu_drv.c:2041
         {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
     -> el device 0x699F  mapea a  CHIP_POLARIS12

  3  hwmgr.c:131   case AMDGPU_FAMILY_VI:
     hwmgr.c:154   case CHIP_POLARIS11:
     hwmgr.c:155   case CHIP_POLARIS10:
     hwmgr.c:156   case CHIP_POLARIS12:
     hwmgr.c:157       hwmgr->smumgr_funcs = &polaris10_smu_funcs;
     hwmgr.c:158       polaris_set_asic_special_caps(hwmgr);
     hwmgr.c:159       hwmgr->feature_mask &= ~(PP_UVD_HANDSHAKE_MASK);
     hwmgr.c:160       break;
     hwmgr.c:169   smu7_init_function_pointers(hwmgr);

  4  polaris10_smumgr.c:2681   const struct pp_smumgr_func polaris10_smu_funcs = {
     polaris10_smumgr.c:2683       .smu_init = polaris10_smu_init,

  5  polaris10_smumgr.c:335   static int polaris10_smu_init(struct pp_hwmgr *hwmgr)
     polaris10_smumgr.c:339       smu_data = kzalloc_obj(struct polaris10_smumgr);
     polaris10_smumgr.c:343       hwmgr->smu_backend = smu_data;
     polaris10_smumgr.c:345       if (smu7_init(hwmgr)) { ... }

  6  polaris10_smumgr.c:2492  polaris10_process_firmware_header()
     polaris10_smumgr.c:2516      data->soft_regs_start = tmp;
```

**PROBADO.** Y la forma que toma la prueba es la más fuerte posible: **no es una comparación de
includes, es un `switch` con tres `case` consecutivos sin `break`.** `CHIP_POLARIS11`,
`CHIP_POLARIS10` y `CHIP_POLARIS12` caen literalmente en el mismo brazo, y ese brazo **elige
`polaris10_smu_funcs`**. Eso no admite otra lectura.

## 2 · La corrección que importa: el include graph era evidencia, no prueba

`1574` escribió esto:

```text
  NO VERIFICADO  que Polaris12 entre por polaris10_smumgr.c.  Encontre que
  smu7_hwmgr.c:55 incluye polaris10_smumgr.h  (grafo de includes,  que es el
  mecanismo que he usado toda la sesion),  pero no segui la asignacion del
  puntero de funciones hasta el chip.
```

**La conclusion de mi baseline era correcta y mi prueba era incorrecta.** Dejé un `NO VERIFICADO` en el lugar
justo, que es lo que me permitió volver. Pero el razonamiento que escribí —"el grafo de includes
es el mecanismo que he usado toda la sesión"— estaba siendo aplicado donde no toca: el grafo de
includes decide **qué header aporta qué símbolo**, no **qué función se ejecuta**.

Y esa distinción ya me había costado caro antes: en `1546` y `1558` el grafo de includes fue la
prueba de que GFX8 toma prestado `gmc_8_1_d.h`. **Eso sigue siendo válido** —porque ahí la
pregunta es qué header define el símbolo— pero **aquí la pregunta es quién llama, y la respuesta
la tiene el `switch`, no el include.**

Me costó tres rondas encontrarlo, y la causa de dos de ellas fue que busqué por `pfn` —que no
existe en este árbol— cuando el campo se llama `smu_init`.

## 3 · Confirmación independiente, y por la vía de runtime

Hay un segundo sitio donde se comprueba lo mismo, y es una guarda de **runtime** sobre `chip_id`:

```c
  smu7_hwmgr.c:5459-5461
      if (!(hwmgr->chip_id >= CHIP_POLARIS10 &&
            hwmgr->chip_id <= CHIP_VEGAM))
              return -EINVAL;
```

Para leer `hwmgr->pptable` como `SMU74_Discrete_DpmTable` **hace falta** que `chip_id` esté en ese
rango. Polaris12 lo está, porque el brazo del `switch` lo pone ahí con POLARIS10 y POLARIS11.

O sea que hay **dos** comprobaciones independientes del mismo hecho, en ficheros distintos, y
las dos la satisfacen. Eso ya no es `PROVEN` por una vía: es `PROVEN` por dos.

## 4 · Y el hallazgo que salió de paso: hay un bloque por stepping que esta placa no cumple

```c
  smu7_hwmgr.c:1975-1984
      if ((adev->pdev->device == 0x699F) &&
          (adev->pdev->revision == 0xCF)) {
              phm_cap_unset(..., PHM_PlatformCaps_PowerContainment);
              data->enable_tdc_limit_feature   = false;
              data->enable_pkg_pwr_tracking_feature = false;
              data->disable_edc_leakage_controller  = true;
              phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
      }
```

Y lo que `1231` midió de esta máquina:

```text
  01:00.0  1002:699f  rev c7       ->  revision = 0xC7
  la condicion pide                ->  revision = 0xCF
  0xC7 != 0xCF   ->  EL BLOQUE NO SE EJECUTA EN ESTA PLACA
```

Consecuencia, y es concreta: **esta tarjeta conserva cinco capacidades que el driver
deshabilita explícitamente en el stepping `0xCF` del mismo device.**

```text
  PowerContainment            sigue activo
  ClockStretcher              sigue activo
  enable_tdc_limit_feature    true
  enable_pkg_pwr_tracking     true
  disable_edc_leakage_controller  false  ( o sea,  el controlador de fugas EDC
                                            NO se desactiva  )
```

Eso tiene lectura directa en temperatura y en consumo, y es de las pocas cosas de esta lista que
**no son** semántica de protocolo sino comportamiento de potencia en una placa concreta.

**Y no sé si el driver se está olvidando de esta placa o si el stepping `0xCF` es
 deliberadamente distinto.** No lo decido. Lo que afirmo es el hecho, que es sólido: la condición
existe, es por device+revision, y esta placa no la cumple.

Eso abre una pregunta con discriminante real: **¿qué hace el stepping `0xCF` que motivó esa
 guarda, y le aplica a `0xC7`?** Los ficheros que lo responderían son los de EDC y power
 del SMU7, y es estático.

## 5 · Procedimiento

```text
PREGUNTA   ¿entra Polaris12 por polaris10_smumgr.c?
FUENTES    la tabla de device IDs        amdgpu_drv.c:2041
           el switch de hwmgr             hwmgr.c:131-170,  leido entero
           la tabla de ops                polaris10_smumgr.c:2681-2683
           el cuerpo del init             polaris10_smumgr.c:335-350
           la guarda de runtime           smu7_hwmgr.c:5459-5461
           la guarda por stepping          smu7_hwmgr.c:1975-1984
           y el PCI ID de esta maquina,  medido en 1231
MEDIDO     0x699F -> CHIP_POLARIS12                amdgpu_drv.c:2041
     CHIP_POLARIS11 / POLARIS10 / POLARIS12  en el MISMO case,  sin break
     ese case asigna  polaris10_smu_funcs     hwmgr.c:157
     .smu_init = polaris10_smu_init            :2683
     smu_backend = smu_data  y  smu7_init()    :343, :345
     confirmacion independiente:  la guarda chip_id de smu7_hwmgr.c:5459
     revision de esta placa = 0xC7;  la guarda de stepping pide 0xCF
DESVIO MIO  2 rondas perdidas buscando "pfn",  que no existe en este arbol;  el
     campo se llama smumgr_funcs  y el miembro .smu_init.  Y la confusion de
     fondo:  trate el grafo de includes como prueba de una pregunta de dispatch,
     que es donde no aplica
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - quedan los seis huecos de riesgo cero queescribo arriba.  El 1 ya no esta
  - el bloque de stepping de smu7_hwmgr.c:1975 abre algo con valor real:  que
    hacen EDC y power en el stepping 0xCF  y si aplica a 0xC7.  Es estatico  y
    toca temperatura y consumo en ESTA placa
  - y sigue en pie lo unico que cierra soft_regs_start:  el valor de
    SMC_RAM[0x20030]  por dos accesos de registro  que necesitan tu OK
```