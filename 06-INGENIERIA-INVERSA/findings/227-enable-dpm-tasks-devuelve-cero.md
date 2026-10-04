# 227  smu7_enable_dpm_tasks tiene 23 asserts, no 15: los 7 primeros fallos se propagan, los 15 siguientes se tragan, y devuelve 0

> **H1 CORREGIDO EL 2026-10-04.** El titulo anterior decia «`smu7_enable_dpm_tasks` ejecuta ~15 pasos que pueden fallar, registra cada fallo y devuelve 0». Ese
> enunciado ya no describe el estado del arbol. El veredicto vigente esta en este
> mismo fichero:
> - `:19` — el conteo real: «tiene 23 asserts: 22 `REGISTRA_Y_SIGUE` y 1»
> - `:32` — la propagacion: «los 7 fallos anteriores SI se propagan»
> - `:39` — los 15 tragados: «Los 15 ultimos fallos se»
>
> Este parche toca **solo el H1** y esta marca. El cuerpo no se reescribe: la
> correccion del titulo tiene que quedar rastreable, o el titulo parece haber
> sido asi siempre.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## CORREGIDO POR `228` (antes `228`) — dos errores en este hallazgo
>
> **1. El conteo.** Este fichero dice "quince pasos" y "los pasos de `:1619` a `:1688`".
> **La funcion `smu7_enable_dpm_tasks` (`:1566`) tiene 23 asserts: 22 `REGISTRA_Y_SIGUE` y 1
> `ABORTA`.** Me faltaban los 7 primeros porque mi lectura empezo en `:1616` en vez de en el
> inicio de la funcion. `PARTIAL_READ_AS_COMPLETE` aplicado a mi propia lectura.
>
> **2. El mecanismo.** Este fichero afirma que "cada fallo se registra y la ejecucion
> continua". **Es cierto desde `:1623`, pero no desde el principio:**
>
> ```
> :1569   int result = 0;
> :1573   result = tmp_result   }  7 escrituras ANTES
> ...                           }
> :1613   result = tmp_result   }
> :1619   PP_ASSERT(0 == result, ..., return result)   <-- LEE result: ABORTA
>          ==> los 7 fallos anteriores SI se propagan
> :1623   result = tmp_result   }  15 escrituras DESPUES
> ...                           }  y ya no las lee nadie
> :1687   result = tmp_result   }
> :1692   return 0;
> ```
>
> **22 escrituras, 1 lectura, y 15 escrituras despues del lector.** Los 15 ultimos fallos se
> tragan; los 7 primeros no.
>
> **Lo que sobrevive y se reinforce:** `:1087 return 0` hace que el `return result` de `:1619`
> sea inerte salvo por esos 7 pasos, y `:1692 return 0` descarta lo acumulado. Y la conclusion
> sobre el indice negativo se **refuerza**: la cadena exige que
> `smu7_setup_default_dpm_tables` deje `count == 0` y aun asi devuelva exito, que es
> exactamente lo que hace (`:1068` descarta el retorno interno, `:1087` devuelve 0).
>
> **Y una segunda correccion, mia y de busqueda:** este fichero dice que
> `smu7_enable_dpm_tasks` "no tiene llamadores". **Falso**: esta cableada en
> `.dynamic_state_management_enable` (`smu7_hwmgr.c:5861`) y se invoca de forma indirecta.
> Un `static` sin llamadas DIRECTAS puede estar en una tabla de funciones.

**ENCADENA `099` con una lectura con indice negativo, y SEPARA lo que se sostiene de lo que
no.** Incluye una autocorreccion mia por busqueda mal planteada.

## El hallazgo que se sostiene

`smu7_enable_dpm_tasks` (`smu7_hwmgr.c:1566`) es la secuencia que arranca el DPM. Cada uno de
sus quince pasos tiene esta forma:

```c
tmp_result = smu7_algo(hwmgr);
PP_ASSERT_WITH_CODE((0 == tmp_result), "Failed to algo!", result = tmp_result);
```

Y el macro **no altera el flujo de control**:

```c
/* pp_debug.h:37-43 */
#define PP_ASSERT_WITH_CODE(cond, msg, code)       \
        do {                                       \
                if (!(cond)) {                     \
                        pr_warn_ratelimited("%s\n", msg);  \
                        code;             \
                }                                  \
        } while (0)
```

`code` se ejecuta en linea. **`result = tmp_result` es una asignacion, no un `return`.** O sea:
**cada fallo se registra en `result` y la ejecucion continua.**

Y el final de la funcion es:

```c
        1690|   smu7_populate_umdpstate_clocks(hwmgr);
        1692|   return 0;                    <-- literal, no return result
```

**`return 0`, no `return result`.** Los quince fallos acumulados se descartan en la ultima
linea.

Y el consumidor **si** propaga, lo cual hace el hallazgo mas triste y no menos cierto:

```c
/* hardwaremanager.c:91-94 */
if (NULL != hwmgr->hwmgr_func->dynamic_state_management_enable)
        ret = hwmgr->hwmgr_func->dynamic_state_management_enable(hwmgr);
return ret;
```

**El consumidor hace su trabajo. El valor que propaga es un cero constante.**

Y el aviso de cada fallo es `pr_warn_ratelimited`, luego **esta limitado por frecuencia**: tras
varias ocurrencias **hay silencio**. Es decir: el unico sintoma de estos quince fallos se
atenua a proposito.

- `SMU7_ENABLE_DPM_TASKS_ALWAYS_RETURNS_0 = PROVEN`: `:1692` es `return 0` literal. Ningun
  camino devuelve `result`.
- `EVERY_STEP_RECORDS_AND_CONTINUES = PROVEN`: el `code` del macro es `result = tmp_result`, y
  `PP_ASSERT_WITH_CODE` no hace `return` ni `goto` (`pp_debug.h:37-43`). Quince ocurrencias
  de `:1619` a `:1688`.
- `CONSUMER_PROPAGATES_FAITHFULLY = PROVEN`: `hardwaremanager.c:92` y `:94`. **El defecto no
  esta en el consumidor.**
- `FAILURE_WARNINGS_ARE_RATE_LIMITED = PROVEN`: `pr_warn_ratelimited`. Tras varias, silencio.

Esto es el patron de `215` ("dos propietarios") llevado a una escala nueva: **quince escritores
sobre un mismo `result`, y un solo lector que nunca ve nada.**

## La cadena con `099`, y donde se rompe

`099` documento que `smu7_setup_dpm_tables_v1` se llama **descartando su retorno** (`:1068`).
Encadenando:

```
:1065  smu7_reset_dpm_tables(hwmgr)              -> todos los count a 0
:1068  smu7_setup_dpm_tables_v1(hwmgr)            -> retorno DESCARTADO
:1075  memcpy(&golden_dpm_table, &dpm_table, ...) -> golden hereda los count

:1618  smu7_setup_default_dpm_tables(hwmgr)      -> retorna 0 aunque el interior fallara
:1619  result = tmp_result                        -> y aun asi NO hay return
:1690  smu7_populate_umdpstate_clocks(hwmgr)      -> se ejecuta igual
:1515  ...dpm_levels[sclk_table.count - 1]...      <- si count==0, indice -1
:1517  ...dpm_levels[mclk_table.count - 2]...      <- si count==0, indice -2
:1692  return 0
```

**Y `smu7_populate_umdpstate_clocks` (`:1505`) no tiene NINGUN guardia antes de ese `if`:**

```c
 1505| static void smu7_populate_umdpstate_clocks(struct pp_hwmgr *hwmgr)
 ...
 1511| if (golden_dpm_table->mclk_table.count == 1) {
 1512|         percentage = 70;
 1513|         hwmgr->pstate_mclk = golden_dpm_table->mclk_table.dpm_levels[0].value;
 1514| } else {
 1515|         percentage = 100 * ...sclk_table.dpm_levels[sclk_table.count - 1]... /
 1516|                     ...mclk_table.dpm_levels[mclk_table.count - 1]...;
 1517|         hwmgr->pstate_mclk = ...mclk_table.dpm_levels[mclk_table.count - 2]...;
 1518| }
```

Con `count == 0` la rama `else` se toma y salen **`dpm_levels[-1]` y `dpm_levels[-2]`**.

La misma forma esta en `smu7_get_profiling_clk` (`:3259`), y ese **si** tiene guardia:

```c
 3269| if (golden_dpm_table->mclk_table.count < 1)  return -EINVAL;
 ...
 3272| percentage = 100 * ...sclk_table.dpm_levels[sclk_table.count - 1]... /
 3273|                 ...mclk_table.dpm_levels[mclk_table.count - 1]...;
```

**Pero el guardia cubre `mclk_table`, y `:3272` lee tambien `sclk_table`, que no se comprueba
en ninguna parte de esa funcion.** Una de las dos esta guardada y la otra no.

## Y aqui se rompe: en esta placa, `count == 0` no es alcanzable

**Lo comprobe antes de afirmarlo, porque dos hallazgos de esta sesion lo evitaron asi.**

`smu7_setup_dpm_tables_v1` solo puede fallar por cinco asserts (`:885`, `:888`, `:892`,
`:895`), y `table_info == NULL` esta descartado antes (`:879`). Las dos tablas que exige son
`table_info->vdd_dep_on_sclk` y `->vdd_dep_on_mclk`, y **sus getters del PPT ya validan que no
esten vacias**:

```c
/* process_pptables_v1_0.c:443 y equivalente */
PP_ASSERT_WITH_CODE((0 != polaris_table->ucNumEntries), "SCLK dependency table count is 0.", return 1);
```

Y `hwmgr.c:249-252` hace `goto err` si `pptable_init` falla, de modo que `backend_init` — que es
donde vive todo esto — **no llega a ejecutarse**.

En esta placa ademas el VBIOS declara **8 entradas SCLK y 3 MCLK** (`121`).

**Conclucion honesta:**

- `NEGATIVE_INDEX_IS_SHOWN_IN_THE_CODE = PROVEN`: las dos lineas existen y no tienen guardia
  que las cubra.
- `NEGATIVE_INDEX_UNREACHABLE_ON_THIS_BOARD = PROVEN_DERIVED`: el `count == 0` exige un fallo
  que los getters del PPT ya impiden. **No ocurre en mi placa.**
- Y la forma de disparo seria **`table_info == NULL`**, que `:879` devuelve antes de tocar los
  contadores, dejando los de `golden_dpm_table` en lo que `smu7_reset_dpm_tables` (**`:1065`**)
  puso: **cero**. Ese es el unico hueco real que veo, y **no se como llegar a el**.

## Y mi error de esta tanda, que casi publica codigo muerto

Escribi, al medir: *«`smu7_enable_dpm_tasks` no tiene llamadores»*, y lo diagnostique como
"static sin referencias = codigo muerto".

**Es falso, y lo encontre porque la afirmacion era fuerte y la comprobe por mas de un camino:**

```
smu7_hwmgr.c:5861:  .dynamic_state_management_enable = &smu7_enable_dpm_tasks,
```

**Se llama por puntero a funcion.** Un `grep` del nombre en llamadas directas no lo encuentra,
porque la llamada es `hwmgr->hwmgr_func->dynamic_state_management_enable(hwmgr)`.

> **Un `static` sin llamadas DIRECTAS no es codigo muerto: puede estar cableado en una tabla
> de funciones.** Es la misma clase de error que el filtro `smu`/`smc` de `115`, y la segunda
> vez que la cometo en dos dias.

Y por el camino vi que que la forma `enable_dpm_tasks` **existe en las seis familias**
(`smu7`, `smu8`, `smu10`, `vega10`, `vega12`, `vega20`), todas cableadas igual. **Es un
convenio de arquitectura, no un descuido de una familia.**

## Clasificacion

- `SMU7_ENABLE_DPM_TASKS_ALWAYS_RETURNS_0 = PROVEN`: `:1692` es `return 0` literal.
- `FIFTEEN_STEPS_RECORD_AND_CONTINUE = PROVEN`: `:1619` a `:1688`, con el `code` del macro
  siendo `result = tmp_result`. `PP_ASSERT_WITH_CODE` (`pp_debug.h:37-43`) no altera el flujo.
- `CONSUMER_IS_FAITHFUL = PROVEN`: `hardwaremanager.c:92` y `:94`. **El defecto no es de quien
  llama.**
- `WARNINGS_ARE_RATE_LIMITED = PROVEN`: `pr_warn_ratelimited`.
- `NEGATIVE_INDEX_LINES_HAVE_NO_GUARD = PROVEN`: `:1515` y `:1517` en
  `smu7_populate_umdpstate_clocks` (`:1505`), sin guardia previo.
- `PROFILING_CLK_GUARDS_MCLK_BUT_NOT_SCLK = PROVEN`: `:3269` comprueba `mclk_table.count`;
  `:3272` lee tambien `sclk_table.count - 1`, sin comprobarlo.
- `COUNT_ZERO_IS_UNREACHABLE_ON_THIS_BOARD = PROVEN_DERIVED`: los getters del PPT validan
  `!= 0`, y `hwmgr.c:249-252` aborta antes de `backend_init`. El VBIOS declara 8 y 3.
- `MY_STATIC_WITHOUT_CALLERS_CLAIM_WAS_A_FALSE_NEGATIVE = CORRECTED`: la funcion esta
  cableada en `.dynamic_state_management_enable` (`smu7_hwmgr.c:5861`) y se invoca de forma
  indirecta. **No es codigo muerto.**
- `ENABLE_DPM_TASKS_IS_A_CROSS_FAMILY_CONVENTION = PROVEN_DERIVED`: la misma forma existe en
  `smu7`, `smu8`, `smu10`, `vega10`, `vega12` y `vega20`, todas cableadas igual.

## Lo que esto obliga a hacer en un driver propio

1. **Una secuencia de arranque tiene que devolver el peor fallo, no cero.** Acumular quince
   errores y devolver `return 0` es peor que no acumularlos: **consume la señal y la tira**.
   Mi driver tiene que devolver el **primer** fallo, o el **mas severo**, y no seguir
   despues de un fallo que deja el estado a medias.
2. **Y si se decide seguir, tiene que ser explicito**: un `continue` documentado y un resumen
   al final. Aqui no hay ninguna de las dos cosas.
3. **Un aviso limitado por frecuencia no es un aviso**: tras el primer arranque se calla. Para
   fallos de arranque, la limitacion **impide** el diagnostico que se necesita.
4. **Toda lectura `dpm_levels[count - 1]` exige comprobar `count >= 1`**, y si se leen dos
   tablas, comprobar **las dos**. Aqui una de las dos lecturas tiene guardia y la otra no, en
   lineas contiguas.
5. **Y la generalizacion de `215`:** un campo con dos propietarios es un error de diseno.
   **Un `result` con quince escritores y ningun lector es el mismo error, y peor**, porque no
   hay ni siquiera un propietario que se entere.