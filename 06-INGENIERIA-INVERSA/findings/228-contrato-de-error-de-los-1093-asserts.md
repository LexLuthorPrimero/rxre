# 228  El contrato de error de los 1093 asserts, y una RETRACCIONmia sobre `122`

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Barrido sistematico del patron de `227` (antes `227`), con una herramienta nueva. Cierra con una
RETRACCION: `122` tenia razon y la correccion que yo iba a publicar era el error.**

## La herramienta

`tools/assert_contract.py` v1.0.0. **51 pruebas, 0 fallos, `TOOL_VALIDATED`.**

`PP_ASSERT_WITH_CODE(cond, msg, code)` se expande (`pp_debug.h:37-43`) a:

```c
do { if (!(cond)) { pr_warn_ratelimited("%s\n", msg); code; } } while (0)
```

**El tercer argumento decide el contrato y no altera el flujo por si solo.** Hay cinco
formas, y solo una detiene:

| categoria | significado | n | % |
|---|---|---|---|
| `ABORTA` | `return X` | **928** | **84,9 %** |
| `REGISTRA_Y_SIGUE` | `x = y` | 86 | 7,9 % |
| `PR_WARN_PURO` | vacio | 33 | 3,0 % |
| `SALTA` | `goto L` | 25 | 2,3 % |
| `OTRO` | `continue`, asignaciones multiples | 21 | 1,9 % |

**1093 ocurrencias en el arbol de powerplay.**

### El dato que reencuadra `227` (antes `227`)

**El arbol ABORTA en el 84,9 % de los casos.** `227` (antes `227`) dokumenento una secuencia que acumula
fallos y devuelve 0; mediendolo, eso es **la excepcion, no la norma**.

De las 16 funciones que contienen `REGISTRA_Y_SIGUE`, **solo 4 terminan en `return 0`
literal**. Y **3 de esas 4 estan en `vega10_hwmgr.c`, que no es mi familia.**

- `FUNCIONES_CON_REGISTRA = 16`; `DE_ELLAS_CON_RETURN_0 = 4` (25 %).
- `TRES_DE_LAS_CUATRO_ESTAN_EN_VEGA10 = PROVEN`: `vega10_set_power_state_tasks`,
  `vega10_get_evv_voltages`, `vega10_apply_state_adjust_rules`.
- `LA_UNICA_EN_MI_ARBOL = PROVEN`: `smu7_enable_dpm_tasks` (`smu7_hwmgr.c:1566`).

## Correccion a `227` (antes `227`): 22 escritores, 1 lector, 15 escrituras despues del lector

`227` (antes `227`) dijo "quince pasos" y "cada fallo se registra y la ejecucion continua". **Las dos
cosas eran incorrectas, y el error fue mio por leer un trozo.**

Mi `awk` empezaba en `:1616` en vez de en el inicio de la funcion, asi que **no vi los 7
asserts anteriores**. `PARTIAL_READ_AS_COMPLETE` aplicado a mi propia lectura.

El cuadro real, con `int result = 0;` en `:1569`:

```
:1569   int result = 0;                              <-- inicializado a cero
:1573   result = tmp_result      REGISTRA  }  los 7 primeros fallos
...
:1613   result = tmp_result      REGISTRA  }
:1619   PP_ASSERT(0 == result, ..., return result)   <-- LEE result, UNA VEZ
        ==> si fallo cualquiera de los 7, aqui ABORTA y propaga
:1623   result = tmp_result      REGISTRA  }  15 fallos mas
...
:1687   result = tmp_result      REGISTRA  }  y ya no lo lee NADIE
:1692   return 0;                                   <-- literal
```

**22 escrituras, 1 lectura, y 15 escrituras ocurren DESPUES de la lectura.**

- `ASSERTS_EN_LA_FUNCION = 23`: 22 `REGISTRA_Y_SIGUE` + 1 `ABORTA`.
- `PRIMEROS_7_FALLOS_SI_SE_PROPAGAN = PROVEN`: `:1619` lee el `result` que ellos escriben.
- `ULTIMOS_15_FALLOS_SE_TRAGAN = PROVEN`: occurren despues de `:1619`; `:1692` no devuelve
  `result`. **El consumidor (`hardwaremanager.c:92`, `:94`) propaga un cero.**
- `MI_LECTURA_EMPEZO_EN_1616_Y_PERDIO_LOS_7 = CORRECTED`: `PARTIAL_READ_AS_COMPLETE`.

Y el aborte de `:1619` **es inerte en su otra mitad**: `:1618` llama a
`smu7_setup_default_dpm_tables`, que **devuelve 0 incondicionalmente** en `:1087`. O sea
que `:1619` solo puede dispararse por los 7 pasos anteriores.

**Esto REFUERZA la conclusion de `227` (antes `227`) sobre el indice negativo.** La cadena exigia que
`smu7_setup_default_dpm_tables` dejara `count == 0` y aun asi devolviera exito: exactamente
lo que hace, porque `:1068` descarta el retorno interno y `:1087` devuelve 0.

## Un assert que se dispara siempre: `PP_ASSERT_WITH_CODE(false, ...)`

`polaris10_smumgr.c:1728-1732`, **en la ruta viva de mi ASIC**:

```c
        } else {
                PP_ASSERT_WITH_CODE(false,
                        "VDDC should be on SVI2 control in merged mode!",
                        );
        }
```

Con `cond = false`, `!(false)` es cierto, asi que **el aviso se emite cada vez que se entra
en esa rama**, y el tercer argumento vacio lo convierte en un `pr_warn` **sin ninguna
accion**.

La rama se alcanza cuando `data->voltage_control` **no es** `SMU7_VOLTAGE_CONTROL_BY_SVID2`
**ni** `SMU7_VOLTAGE_CONTROL_BY_GPIO` (`:1722`, `:1725`) — o sea cuando vale `NONE`.

- `ASSERT_CON_LITERAL_FALSE = PROVEN`: `:1729`.
- `NO_ACTUA = PROVEN`: tercer argumento vacio.
- `SE_DISPARA_CUANDO_VOLTAGE_CONTROL_ES_NONE = PROVEN_DERIVED`: es la unica forma de entrar.

Es la manera **sintacticamente valida pero semanticamente vacia** de escribir «esto no deberia
pasar»: un `return -EINVAL`Convertido en un aviso. Y `pr_warn_ratelimited` lo limita.

## Los 5 `PR_WARN_PURO` de `polaris10_smumgr.c`, y que pasa despues de cada uno

`7 vegam`, `6 fiji`, `6 smu7_hwmgr`, **`5 polaris10_smumgr` (mi ruta viva)**, `2 tonga`.

| linea | aviso | que pasa despues |
|---|---|---|
| `:445` | `usTargetOperatingTemp <= 255` | inerte, y `222` demostro que no dispara (`93 <= 255`) |
| `:1297` | `Cannot find ACPI VDDC voltage value` | **`:1302` sobrescribe `result` sin comprobarlo** |
| `:1332` | `Cannot find ACPI VDDCI voltage value` | igual que `:1297` |
| `:1729` | `VDDC should be on SVI2 control` | nada, ver arriba |
| `:2411` | `Failed to program memory timing parameters!` | **`:2415 return result`** — propaga, **sin deshacer** |

**`:1297` es el caso con consecuencia.** El fallo de la busqueda ACPI se avisa, y **una linea
despues `result` se reasigna con otra llamada sin comprobar el valor intermedio**:

```c
 1293|  result = polaris10_get_dependency_volt_by_clk(hwmgr, ..., &table->ACPILevel.MinVoltage, &mvdd);
 1297|  PP_ASSERT_WITH_CODE((0 == result), "Cannot find ACPI VDDC voltage value ...", );
 1302|  result = polaris10_calculate_sclk_params(hwmgr, sclk_frequency, &(table->ACPILevel.SclkSet...));
```

**Y mi hipótesis de «basura al SMC» queda REFUTADA, con la evidencia a favor:**

```c
/* polaris10_smumgr.c:361, dentro de polaris10_get_dependency_volt_by_clk */
*voltage = *mvdd = 0;
```

La funcion **se autoinicializa a cero**. Asi que el fallo produce **`MinVoltage = 0`, un
valor bien definido**, no un valor indeterminado. Y ese cero se convierte y entra en la tabla
del SMC en `:1310`.

- `EL_FALLO_PRODUCE_UN_CERO_BIEN_DEFINIDO = PROVEN`: `:361`.
- `EL_CERO_LLEGA_A_LA_TABLA_DEL_SMC = PROVEN`: `:1310` lo convierte.
- `EL_ERROR_SE_DESCARTA_EN_1302 = PROVEN`: `result` se sobrescribe sin comprobar.

`:2411` es el caso honesto: **propaga** el fallo por `:2415`, pero **sin deshacer** lo que
`polaris10_program_mem_timing_parameters` ya habia escrito a medias.

## Mi error en la herramienta, y por que lo cuento

La primera version clasificaba **86** `REGISTRA_Y_SIGUE`. **30 de ellos eran `goto`.**

```c
PP_ASSERT_WITH_CODE(cond, "msg", r = -EINVAL; goto failed);
```

Mi clasificador miraba **la primera sentencia** del argumento, veia una asignacion, y
concluia «registra y sigue». **El `goto` va detras y ABORTA.** Es
`PARTIAL_READ_AS_COMPLETE` aplicado a un argumento multi-sentencia, y fue el mismo error que
me hizo perder los 7 asserts de `227` (antes `227`).

Corregido: `clasifica` parte el argumento en sentencias (respetando los `;` de un `for`) y
**gana la que mas flujo cambia** — `SALTA` sobre `REGISTRA`, `ABORTA` sobre todo. El cambio
se ve en los numeros: **`SALTA` 15 -> 25** y **`REGISTRA` 96 -> 86**, los mismos diez casos.

- `CLASIFICADOR_MIRABA_SOLO_LA_PRIMERA_SENTENCIA = CORRECTED`: 30 de 96 mal.
- `AHORA_GANA_LA_SENTENCIA_DE_MAYOR_EFECTO = PROVEN`: `partir_sentencias` + orden de pruebas.

Y las regex me fallaron **dos veces seguidas** en el mismo fichero, por_styles distintos de
 parentesis: `:1619` es `PP_ASSERT_WITH_CODE(0 == result,` (sin parentesis) y `:1623` es
`PP_ASSERT_WITH_CODE((0 == tmp_result),` (con parentesis). Una regex que fija el numero de
parentesis mide el **estilo**, no el contenido. Ahora es `\(+ ... \)*`.

## RETRACCION: `122` tenia razon y mi correccion era el error

**Casi publico una correccion falsa.** `122`tenia escrito que
`ulPlatformCaps = 0x068000` son «bit 15 VDDCI_CONTROL, bit 17 BACO, bit 18 sin nombre».
Me parecio **incorrecto** y lo «corregi», porque:

```
PHM_PlatformCaps_AtomBiosPpV1 = 0,        (hardwaremanager.h:55)
PHM_PlatformCaps_ControlVDDCI,            (hardwaremanager.h:110)  -> indice 55, NO bit 15
PHM_PlatformCaps_ControlVDDGFX,           (hardwaremanager.h:205)  -> indice 150
196 miembros en total, indices 0..195
```

**`0x068000` no tiene el bit 55 encendido.** Conclui que mi decodificacion original estaba
mal. **Estaba bien.**

La verdad es que **estoy usando dos enums distintos con nombres parecidos**:

- `ATOM_TONGA_PP_PLATFORM_CAP_*` (`pptable_v1_0.h:53-72`): mascaras del **VBIOS**.
  `VDDCI_CONTROL = 0x8000`, `BACO = 0x20000`, `VDDGFX_CONTROL = 0x1`.
- `PHM_PlatformCaps_*` (`hardwaremanager.h:55+`): el enum **de runtime**, 196 miembros.

**Los dos viven en sistemas de coordenadas distintos, y `set_platform_caps`
(`process_pptables_v1_0.c:55-125`) es el puente.** Es una tabla explicita de mascaras con
nombre, no una copia de indices.

Con las mascaras correctas, `0x068000` = `0x8000 | 0x20000 | 0x40000`:

```
bit 15  0x08000  ATOM_TONGA_PP_PLATFORM_CAP_VDDCI_CONTROL    SET
bit 17  0x20000  ATOM_TONGA_PP_PLATFORM_CAP_BACO             SET
bit 18  0x40000  SIN MASCARA DEFINIDA
```

**`122` dice exactamente eso.** Mi correccion era falsa y queda retractada.

> **Un enum cuyo nombre empieza igual que otro no es el mismo enum.** Aqui `PHM_PlatformCaps_`
> y `ATOM_TONGA_PP_PLATFORM_CAP_` coexisten, significan cosas distintas, y el segundo **no
> esta en el corpus** (0 miembros en este arbol): solo existe el comentario que lo referencia
> y las mascaras numericas. `122` uso las mascaras — la fuente de verdad. Yo use el enum.

- `LA_DECODIFICACION_DE_122_ES_CORRECTA = CONFIRMADO`: mascaras ATOM, bits 15 y 17.
- `MI_CORRECCION_DE_122_ERA_UN_FALSO_POSITIVO = RETRACTADO`.
- `LOS_DOS_ENUMS_ESTAN_EN_COORDENADAS_DISTINTAS = PROVEN`: el puente es `set_platform_caps`
  (`:55-125`).

**Y esto tiene una consecuencia seria, que es lo que importa:** como `ControlVDDCI` **si**
esta activo (`set_platform_caps:94-96`), `data->vddci_control != NONE` en mi placa. Eso
**descarta** una via por la que yo creia bloqueado un bug de desplazamiento, y abre
`127`.

## Un `continue` dentro de `do { } while (0)` no salta de la funcion

`set_platform_caps` tiene cinco asserts con `continue` como tercer argumento:

```c
/* process_pptables_v1_0.c:57-67 */
PP_ASSERT_WITH_CODE((~powerplay_caps & ____RETIRE16____),
        "ATOM_PP_PLATFORM_CAP_ASPM_L1 is not supported!", continue);
```

Igual que `____RETIRE64____`, `____RETIRE512____`, `____RETIRE1024____`, `____RETIRE2048____`
(todas mascaras retire en `pptable_v1_0.h:57-64`).

El `continue` cae dentro del `do { ... } while (0)` del macro, asi que **continua ese lazo
vacio**, que equivale a terminar la sentencia. **No salta de la funcion.** El aviso sale y
no pasa nada: exactamente `PR_WARN_PURO` en el efecto.

- `CONTINUE_DENTRO_DE_DO_WHILE_0_NO_ES_SALTO = PROVEN`: es el `while (0)` de `pp_debug.h:38`.
- `LOS_5_ASSERTS_RETIRE_NO_HACEN_NADA_UTIL = PROVEN_DERIVED`: su `code` no cambia el flujo.
- `LOS_NOMBRES_RETIRE_ESTAN_EN_UN_CANTO_VACIO = PROVEN`: `____RETIRE16____` y compañía.

## Clasificacion

- `CONTRATO_DE_ERROR_BARRIDO = PROVEN`: 1093 ocurrencias, 5 categorias.
- `EL_ARBOL_ABORTA_EN_EL_84_9 = PROVEN`: 928 de 1093.
- `EL_125_ES_LA_EXCEPCION = PROVEN`: 4 funciones de 16; 3 en vega10.
- `ENABLE_DPM_TASKS_TIENE_23_ASSERTS_NO_15 = CORRECTED`: 22 registran + 1 aborta.
- `22_ESCRITURAS_1_LECTURA_15_DESPUES = PROVEN`: `:1569`, `:1619`, `:1692`.
- `LOS_7_PRIMEROS_FALLOS_SI_SE_PROPAGAN = PROVEN`: `:1619` los lee.
- `EL_ABORTE_DE_1619_ES_INERTE_PARA_1087 = PROVEN`: `smu7_setup_default_dpm_tables`
  devuelve 0 siempre.
- `ASSERT_CON_LITERAL_FALSE = PROVEN`: `:1729`, sin accion.
- `LOS_5_PR_WARN_PURO_EN_MI_RUTA_VIVA = PROVEN`: `polaris10_smumgr.c`.
- `EL_FALLO_ACPI_PRODUCE_UN_CERO_NO_UN_DETERMINADO = PROVEN`: `:361` autoinicializa.
- `EL_ERROR_SE_DESCARTA_EN_1302 = PROVEN`: `result` se sobrescribe sin comprobar.
- `CLASIFICADOR_30_DE_96_MAL = CORRECTED`: `PARTIAL_READ_AS_COMPLETE`.
- `REGEX_FRAGILES_AL_ESTILO_DE_PARENTESIS = CORRECTED`: dos fallos seguidos, mismo fichero.
- `LA_DECODIFICACION_DE_122_ERA_CORRECTA = CONFIRMADO`: mascaras ATOM.
- `MI_CORRECCION_DE_122_ERA_UN_FALSO_POSITIVO = RETRACTADO`.
- `CONTINUE_EN_DO_WHILE_0_NO_ES_UN_SALTO = PROVEN`: los 5 asserts RETIRE.

## Lo que esto obliga a hacer en un driver propio

1. **Un `assert` que no actua es peor que no tener assert**: paga el coste de la rama y no
   protege nada. Si no va a abortar, que no exista.
2. **Y un assert con condicion literal `false` es peor**: se dispara siempre, no hace nada, y
   con `pr_warn_ratelimited` el ruido se vuelve silencio. Es codigo que parece vigilar y no
   vigila.
3. **Un error acumulado necesita UN lector, y el lector tiene que ir al FINAL.** Acumular 22
   escrituras y leer una en el medio pierde 15 silenciosamente. Si se acumula, se lee al
   salir.
4. **Sobrescribir `result` sin comprobar el anterior rompe el contrato entero.** Es el
   `215` de nuevo: dos propietarios de la misma variable en el mismo bloque.
5. **Los avisos de arranque no se limitan por frecuencia.** Si hay que diagnosticar un
   fallo de arranque, `pr_warn_ratelimited` es lo contrario de lo que se quiere.
6. **Y una transicion de estado que puede fallar debe deshacer lo que ya hizo.** `:2411`
   propaga el error pero deja el timing de memoria a medias.
7. **Regla de comprobacion de alcance, nueva y util: al decodificar un campo crudo,
   encontrar el codigo que lo traduce y usarlo, no el enum de nombre parecido.**
   `set_platform_caps` era la autoridad y yo ni lo mire antes de «corregir» a `122`.

## Retirada de la afirmacion que este hallazgo deja en pie

`127` recoge el defecto de las dos rutas de `polaris10_get_dependency_volt_by_clk`, y su
alcance depende de `ControlVDDCI` — que este hallazgo **confirma activo** en mi placa.