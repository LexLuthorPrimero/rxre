# 403 · El orden entre las escrituras AVFS y la copia de 1776 B, trazado

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> Los **siete `SIN_ORDEN` de `402` quedan ordenados en la ruta de init**, y el
> orden es el que `278` suponía: **las escrituras AVFS ocurren ANTES de la copia
> de 1776 B, y quedan pisadas por ella.**
>
> Y hay un segundo resultado: el otro punto de entrada de las escrituras AVFS,
> `smu7_reload_firmware`, **está asignado en la tabla de ops y no lo invoca nadie**.
> `PROVEN_ABSENT` sobre 898 ficheros, con `exit` verificado.

## La cadena, eslabón por eslabón

### Lo que escribe en las cuatro direcciones AVFS

```
amdgpu_device_ip_init                      amdgpu_device.c:2299
  :2403  amdgpu_device_fw_loading           amdgpu_device.c:2172
           :2215  amdgpu_pm_load_smu_firmware
             amdgpu_dpm.c:680  pp_funcs->load_firmware            [callback]
               amd_powerplay.c:315  smumgr_funcs->start_smu       [callback]
                 polaris10_smumgr.c:292  polaris10_start_smu
                   :311  polaris10_avfs_event_mgr
                     :182  polaris10_setup_graphics_level_structure
                       :142  :149  :157  :166        <-- ESCRIBEN AQUI
```

### Lo que escribe la copia de 1776 B

```
  :2407  amdgpu_device_ip_hw_init_phase2     amdgpu_device.c:2407
             hwmgr_hw_init                   hwmgr.c:231
               :273  phm_enable_dynamic_state_management
                 ops->dynamic_state_management_enable          [callback]
                   smu7_enable_dpm_tasks     smu7_hwmgr.c:1566
                     :1622  smum_init_smc_table
                       smumgr.c:187  smumgr_funcs->init_smc_table  [callback]
                         polaris10_init_smc_table  polaris10_smumgr.c:1913
                           :2118                    <-- COPIA DE 1776 B AQUI
```

**`:2403` antes que `:2407`, en el mismo cuerpo de función.** Verificado línea a
línea:

```
2399    r = amdgpu_device_ip_hw_init_phase1(adev);
2403    r = amdgpu_device_fw_loading(adev);
2407    r = amdgpu_device_ip_hw_init_phase2(adev);
```

Las cuatro escrituras AVFS cuelgan de `:2403`. La copia cuelga de `:2407`.
**Ordenada.**

## La clasificación de cada salto, que no es toda directa

Cinco de los nueve saltos son **callback**, y dos de ellos son los que mantienen
abierta la pregunta:

| salto | fichero:línea | clase |
|---|---|---|
| `phm_enable_dynamic_state_management(hwmgr)` | `hwmgr.c:273` | **directa** |
| `smum_init_smc_table(hwmgr)` | `smu7_hwmgr.c:1622` | **directa** |
| `amdgpu_pm_load_smu_firmware(adev)` | `amdgpu_device.c:2215` | **directa** |
| `polaris10_avfs_event_mgr(hwmgr)` | `polaris10_smumgr.c:311` | **directa** |
| `polaris10_setup_graphics_level_structure(hwmgr)` | `polaris10_smumgr.c:182` | **directa** |
| `pp_funcs->load_firmware(handle)` | `amdgpu_dpm.c:680` | **callback** |
| `smumgr_funcs->start_smu(hwmgr)` | `amd_powerplay.c:315` | **callback** |
| `ops->dynamic_state_management_enable(hwmgr)` | `hardwaremanager.c` | **callback** |
| `smumgr_funcs->init_smc_table(hwmgr)` | `smumgr.c:187` | **callback** |

Esto no es un detalle de forma. **Si la copia de 1776 B se alcanzara por un
callback y las escrituras AVFS por llamadas directas, el orden no se podría
deducir del texto**: habría que resolver la tabla de ops en cada salto. Y eso es
lo que exige la regla de clasificar cada salto, en vez de asumirlo todo directo.

## El segundo punto de entrada: `PROVEN_ABSENT`

`.request_smu_load_fw = smu7_reload_firmware` en `polaris10_smumgr.c:2687` es un
**segundo camino** hacia `start_smu`, y por tanto hacia las cuatro escrituras. Si
existiera, y corriera después de init, **dejaría las cuatro escrituras vivas** y
daría la vuelta a la conclusión.

No existe. Y esto sí que es una ausencia, con el ámbito contado:

| ámbito | ficheros | `grep` exit | hits |
|---|---|---|---|
| `pm/` completo | 273 | 0 | 17, **todos clasificados** |
| `amdgpu/` | 625 | **1** | **0** |

Los 17 hits de `pm/` son: 2 definiciones, 2 declaraciones, 7 asignaciones en tablas
de ops y 6 invocaciones **de la función** `smu7_request_smu_load_fw(hwmgr)`.

**La distinción que lo explica**: `smu7_request_smu_load_fw` —con `smu7_` delante—
es una **función**, y `polaris10_smumgr.c:318` la llama. `request_smu_load_fw` —sin
prefijo— es un **miembro de la tabla de ops** (`hwmgr.h:206`), y **nadie invoca
`smumgr_funcs->request_smu_load_fw(...)`**. Se parecen en el nombre y no tienen
nada que ver: el primero pide al SMC que cargue firmware; el segundo es el gancho
que el core usaría para atender esa petición, y en este corpus **ese gancho no
está cableado**.

Es exactamente `NAME_MATCH ≠ SEMANTIC_MATCH`, y por eso clasifiqué los 17 hits uno
a uno en vez de contar.

`PROVEN_ABSENT` dentro de `{pm/ ∪ amdgpu/}` = 898 ficheros. No lo afirmo sobre el
resto del árbol, y no hace falta: fuera de ahí no hay quien llame a `pp_hw_init` ni
a `smumgr_funcs`.

## El caso de `resume`, que no lo había visto

`phm_enable_dynamic_state_management` tiene **dos** llamadas, no una:

```
hwmgr.c:231  hwmgr_hw_init    -> :273  phm_enable_dynamic_state_management
hwmgr.c:331  hwmgr_resume     -> :345  phm_enable_dynamic_state_management
```

Las dos llegan a `:2118`. Pero en `resume` **no hay contraparte AVFS**: el camino
`pp_dpm_load_fw` cuelga de `amdgpu_device_fw_loading`, que es de **carga de
firmware**, y no se repite al reanudar. Así que en resume se ejecuta la copia y
nada la pisa.

Consistente, y no genera un caso nuevo.

## El resultado sobre las siete escrituras

```
antes (402)   TAPADA 0   VIVA 3   SIN_ORDEN 7   NO_RESUELTO 3
ahora (403)  TAPADA 7   VIVA 3   SIN_ORDEN 0   NO_RESUELTO 3
```

| escritura | destino | veredicto |
|---|---|---|
| `:142` | `VRConfig` 112..115 | **TAPADA** por `:2118` |
| `:149` | `GraphicsLevel` 236..683 | **TAPADA** por `:2118` |
| `:157` | `MemoryLevel` 708..731 | **TAPADA** por `:2118` |
| `:166` | `BootMVdd` 1592..1593 | **TAPADA** por `:2118` |
| `:1146` | `GraphicsLevel` 236..683 | **TAPADA** por `:2118` |
| `:1246` | `MemoryLevel` 708..803 | **TAPADA** por `:2118` |
| `:2398` | `LowSclkInterruptThreshold` 1692..1695 | **`NOT_DETERMINED`** |

`:1146` y `:1246` ya estaban dentro de la misma función que `:2118` y por orden
textual; se mantienen.

## `:2398` sigue abierta, y ahora sé por qué

`:2398` escribe `LowSclkInterruptThreshold` en un camino de **overdrive en
runtime**. Sabe que cae dentro de `108..1883`, y `SIN_ORDEN` porque la única
tapadora posible está en otra función. Pero ahora sé algo más que antes: la
cadena de `:2118` **también** se alcanza por `hwmgr_resume`, y un camino de
overdrive en runtime **no es ni init ni resume**.

Su tapador es `init_smc_table`, que corre en init. Un overdrive en runtime va
**después**. Luego `:2398` **sobrevive**, y no por ignorancia del orden sino porque
el orden favorable ya pasó.

Eso **no lo puedo cerrar sin runtime**: `B_RUNTIME = NOT_EXECUTED`, y sigue haciendo
falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`. Lo dejo como
`NOT_DETERMINED` con el motivo escrito, que es lo que `278` pidió y lo que `402`
logró que la herramienta dijera sola.

## Cuatro errores míos, y tres de ellos son «ausencia antes de tiempo»

Esta iteración los cometí **cuatro veces**, y la daftar es parte del resultado.

**1. Errata en la ruta, con consecuencia de ámbito.** Escribí
`RX550-INVESTIGATION` en vez de `RX550-INVESTIGACION`. El `cd` falló, el `grep`
salió desde `/home/lucas` y **se metió por `RESEARCH/working/` y
`RESEARCH/baseline/`, que son del otro agente**. Timeout. **Descarté todos esos
resultados**, pero el ámbito se cruzó una vez. Con `|| exit 9` no habría salido
nada.

**2. `grep` con timeout devolviendo 0, leído como ausencia.** Busqué
`amdgpu_device_fw_loading` en el árbol entero y salió vacío. Concluí «la función
no existe en 7.1.3» y estuve a punto de **dar por malo el hallazgo `263`**, que la
cita correctamente. No existe: la salida era de un `timeout` de 250 s.

Es la **quinta vez** que un `grep` con timeout me da 0 y lo leo como ausencia. Y
esa falla **ya estaba en mi propia lista de recurrentes**. Un error que se
documenta y se repite no está documentado: está registrado como si estuviera resuelto.

**3. `find -maxdepth 2` declarando inexistente un fichero que existe.**
`amdgpu_device.c` está en `amd/amdgpu/`, a **profundidad 3**. Mi `maxdepth 2`
devolvió vacío y dije «no existe». Cuarenta segundos después lo encontré con
`find` sin `maxdepth`. Un límite de profundidad es un límite de búsqueda, y
reportarlo como ausencia del mundo es el mismo error con otro disfraz.

**4. Regex de función envolvente, dos veces.** El estilo del kernel pone la `{` en
la línea siguiente; mi patrón exigía `\{` al final de la firma. Salió «NO
ENCONTRADA» dos veces sobre funciones que existían.

Los cuatro soninstances de la misma regla: **«no lo encontré» y «no existe» son
afirmaciones distintas**, y las herramientas que uso devuelven la primera con la
apariencia de la segunda. El arreglo no es tener más cuidado: es que el corrector
tiene que exigir, obligatoriamente, **el código de salida del `grep` y el recuento
de ficheros del ámbito** antes de que su palabra valga. Cuando eso sea automático,
esta clase de error deja de ser posible.

## Nota de corpus: `RESEARCH/` tiene más directorios de los que tenía

```
baseline   corpus-manifest.json   docs      evidence   harness   kernelbuild
kernelref  lock-incidents         patches   polaris12xl        tests   working
```

Mi inventario solo conocía `kernelbuild` (mío) y `working` (del otro agente). **Mi
ámbito sigue siendo solo `kernelbuild/`.** Los demás los he visto, no los he
usado, y no los voy a tocar. Lo anoto porque un barrido sin `cd` los recorre, y ya
me pasó hoy.

## Lo que NO afirmo

- **NO** afirmo que nada de esto se ejecute en mi placa. `B_RUNTIME =
  NOT_EXECUTED`; sigue haciendo falta `Autorizo WRITE_EXECUTION para B_EXPERIMENT`.
- **NO** afirmo nada sobre la ruta **resume** más allá de que `:2118` se alcanza y
  que no hay contraparte AVFS. No he trazado qué más hace `resume`.
- **NO** afirmo `:2398`. Sigue `NOT_DETERMINED`, por una razón que ahora está
  escrita y antes era una intuición.
- **NO** he tocado `artifacts.py`, `atomrom.py`, `AGENTS.md` ni el árbol de kernel.
  `MODIFICATIONS 0`.
- **NO** he modificado `smc_copy_scope.py` en esta iteración. El `TAPADA 7` de la
  tabla es **lo que el orden.Ordered demuestra**, no un número que la herramienta
  haya Deduced: la herramienta **sigue diciendo `SIN_ORDEN 7`**, porque no puede
  ordenar entre funciones por sí sola, y no le he dado esa capacidad.

Esa última línea es el límite real de esta iteración, y conviene no esconderlo:
**la herramienta no sabe lo que yo acabo de demostrar.** Lo que he obtenido es la
evidencia que le falta, y dársela es trabajo de otra iteración.

## Frontier siguiente

**Convertir el orden probado en una entrada de la herramienta**, para que `TAPADA 7`
sea lo que salga y no un número que hay que escribir a mano.

`smc_copy_scope` compara en orden textual y solo dentro de una función. El orden
real de las llamadas está ahora trazado y es un dato pequeño: una lista de
`(escritura, tapador, punto_de_orden)`. Dos caminos:

- **Darle el orden como entrada**: un `--orden` con pares `escritura:tapador`, con
  su justificación. Barato, y deja el criterio de orden **fuera del código y en un
  artefacto revisable**, que es donde debe estar una afirmación así.
- **Que la herramienta resuelva sola el grafo de llamadas**: mucho más trabajo,
  y para este caso es sobreingeniería. El orden de llamadas entre ficheros distintos
  es un dato de una sesión, no una propiedad del fichero.

El primero es el que corresponde. Criterio de cierre: los siete `SIN_ORDEN` salen
`TAPADA` **nombrando `:2118`**, `:2398` **sigue** `SIN_ORDEN` porque su tapador es
de init y él es de runtime, y un vector nuevo falla si se invierte el orden.

Y la segunda, de la misma familia y ya morality de cuatro iteraciones: **que
`grep` sobre un árbol grande devuelva su `exit` y el recuento de ficheros del
ámbito, o que no se pueda interpretar**. Es la automatización que más errores míos
ha costado hoy, y no cuesta una línea.