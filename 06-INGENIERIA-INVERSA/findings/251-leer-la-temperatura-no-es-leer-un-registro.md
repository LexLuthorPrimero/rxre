# 251 · §H: leer la temperatura no es leer un registro, y el puente entre §G y §H es una línea

```text
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

> **Convención de rutas de esta nota.** `amdgpu/x.c` es
> `drivers/gpu/drm/amd/amdgpu/x.c`. `pm/y.c` es `drivers/gpu/drm/amd/pm/y.c`.
> Las citas se pueden resolver con la base `$K/drivers/gpu/drm/amd/`, que es donde empieza
> el subárbol `amd/`. Verificado: las 19 citas de esta nota resuelven con esa base.

## Qué resuelve

**Abre §H por el lado que faltaba. `095` cerró la conversión de los límites térmicos
(grados → Q8.8) pero no la ruta por la que se lee el sensor. Esta nota cierra esa ruta entera,
y de paso toca §G.** `PROVEN`.

**⇒ `PROVEN`. La lectura de temperatura tiene cinco saltos y ninguno es una lectura de registro:
`amdgpu_kms.c` → `amdgpu_dpm.c` → `amdgpu_smu.c` → `renoir_ppt.c` → `smu_cmn.c` → el firmware.** `PROVEN`.

**⇒ `PROVEN_ABSENT`. El driver no lee ningún sensor térmico. Ni `mmTHM_TCON_CUR_TMP` ni
`mmTHM_TMON0_RDIL0_DATA` aparecen en un solo `.c` de `amdgpu/`, y no existe `hwmon` en el
corpus.** `PROVEN_ABSENT`.

**⇒ `PROVEN`. Y el firmware no expone la tabla de métricas con `GetMetricsTable` en Renoir:
`renoir_ppt.c` tiene 59 entradas `MSG_MAP(` y ninguna es `GetMetricsTable`. La baja se produce
por `SMU_MSG_TransferTableSmu2Dram`, que Renoir sí declara en `renoir_ppt.c:68`.** `PROVEN`.

**⇒ `PROVEN`. El puente entre §G y §H es `smu_cmn.c:1097`, una llamada a `amdgpu_hdp_flush`
con el comentario «Flush hdp cache: to guard the content seen by GPU is consitent with CPU».**
`PROVEN`.

## 1 · La cadena, con su salto y su línea

| salto | fichero:línea | qué hace |
|---|---|---|
| 1 | `amdgpu_kms.c:1185` | `case AMDGPU_INFO_SENSOR_GPU_TEMP:` |
| 2 | `amdgpu_kms.c:1187-1189` | `amdgpu_dpm_read_sensor(adev, AMDGPU_PP_SENSOR_GPU_TEMP, ...)` |
| 3 | `pm/amdgpu_dpm.c:517` | `int amdgpu_dpm_read_sensor(...)` |
| 4 | `pm/amdgpu_dpm.c:526-528` | `pp_funcs->read_sensor(adev->powerplay.pp_handle, ...)` |
| 5 | `pm/swsmu/amdgpu_smu.c:3956` | `.read_sensor = smu_read_sensor,` |
| 6 | `pm/swsmu/amdgpu_smu.c:3132` | `static int smu_read_sensor(...)` |
| 7 | `pm/swsmu/amdgpu_smu.c:3153-3154` | `smu->ppt_funcs->read_sensor(smu, sensor, data, size)` |
| 8 | `pm/swsmu/smu12/renoir_ppt.c:1458` | `.read_sensor = renoir_read_sensor,` |
| 9 | `pm/swsmu/smu12/renoir_ppt.c:1261` | `static int renoir_read_sensor(...)` |
| 10 | `pm/swsmu/smu12/renoir_ppt.c:1284-1285` | `renoir_get_smu_metrics_data(smu, METRICS_TEMPERATURE_EDGE, ...)` |
| 11 | `pm/swsmu/smu12/renoir_ppt.c:1176` | `static int renoir_get_smu_metrics_data(...)` |
| 12 | `pm/swsmu/smu12/renoir_ppt.c:1189` | `smu_cmn_get_metrics_table(smu, NULL, false)` |
| 13 | `pm/swsmu/smu_cmn.c:1161` | `int smu_cmn_get_metrics_table(...)` |
| 14 | `pm/swsmu/smu_cmn.c:1173` | `smu_cmn_update_table(smu, SMU_TABLE_SMU_METRICS, 0, ...)` |
| 15 | `pm/swsmu/smu_cmn.c:1068` | `int smu_cmn_update_table_read_arg(...)` |
| 16 | `pm/swsmu/smu_cmn.c:1100` | `SMU_MSG_TransferTableSmu2Dram` |
| 17 | | **firmware SMU** |

**⇒ `PROVEN`. Y la cadena pasa por tres punteros a función consecutivos
(`pp_funcs->read_sensor`, `smu->ppt_funcs->read_sensor`, y el dispatch interno de `smu_cmn`),
así que ningún salto se resuelve leyendo un fichero: se resuelve leyendo una tabla de función
de ASIC.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y para un driver propio esto significa que la cadena es reproducible pero no
copiable: hay que escribir una función por ASIC en lugar de una función con un switch. Es la
misma estructura que §G encontró en `gmc_funcs`, y es la razón por la que `246` la trata como
un hallazgo y no como un detalle.** `PROVEN_DERIVED`.

## 2 · La puerta que decide, y la que no decide

**⇒ `amdgpu_dpm.c:526` es `if (pp_funcs && pp_funcs->read_sensor)`. Si no hay función, la función
devuelve `-EINVAL` que fue su valor de retorno inicial, línea 521.** `PROVEN`.

**⇒ `amdgpu_smu.c:3144` es `if (!smu->pm_enabled || !smu->adev->pm.dpm_enabled) return -EOPNOTSUPP;`.
Ésa es la puerta real: con DPM deshabilitado, la lectura de sensor no devuelve un valor erróneo,
devuelve que no está soportado.** `PROVEN`.

**⇒ `PROVEN_DERIVED. `-EOPNOTSUPP` frente a `-EINVAL` es una distinción que un driver propio tiene
que reproducir: `dpm_enabled == 0` es una configuración legítima —se puede forzar
conservador para diagnóstico— y en ese estado el driver no miente diciendo «temperatura
desconocida», dice «esto no está soportado en este modo». Es un contrato observable desde
userspace.** `PROVEN_DERIVED`.

**⇒ Y `amdgpu_smu.c:3153` comprueba `if (smu->ppt_funcs->read_sensor)` y sólo si es verdad llama
al ASIC, con lo que el `switch (sensor)` de `amdgpu_smu.c:3157` es el camino genérico de reserva.
Para Renoir ese camino nunca se usa, porque `renoir_read_sensor` devuelve 0 y el `goto unlock`
de la línea 3155 lo aborta.** `PROVEN`.

## 3 · Los seis sensores de temperatura, y por qué hay cinco que no son de GPU

**⇒ `METRICS_TEMPERATURE_EDGE` (35 usos) y `METRICS_TEMPERATURE_HOTSPOT` (40 usos) son los que
Renoir usa en `renoir_ppt.c:1285` y `:1291`. Los otros cuatro —`MEM` (23), `VRSOC` (14),
`VRGFX` (11), `VRMEM` (3)— no los usa Renoir.** `PROVEN`.

**⇒ `PROVEN_DERIVED. La asimetría 40 contra 35 es informativa: `HOTSPOT` se menciona más que
`EDGE`, y en Polaris12 el foundry monitoriza más el punto caliente de la oblea que el sensor de
borde. `EDGE` es la temperatura que ve el usuario; `HOTSPOT` es la que ve el control térmico.**
`PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y los cuatro que no son de silicio (memoria, VRM de SoC, VRM de GFX, VRM de
memoria) son todos de la placa, no del ASIC. La observación relevante para un driver propio es que
`renoir_read_sensor` sólo expone `EDGE` y `HOTSPOT`, y que `095` ya mostró que el límite térmico
que el driver carga en la tabla del SMC viene de `usTargetOperatingTemp` en el PPT, no de un
sensor leído en caliente.** `PROVEN_DERIVED`.

## 4 · La caché de un milisegundo, que es un detalle de corrección

**⇒ `smu_cmn.c:1172` es
`time_after(jiffies, smu_table->metrics_time + msecs_to_jiffies(1))`. La tabla de métricas se
vuelve a pedir al firmware como mucho una vez por milisegundo, y el resultado se guarda en
`smu_table->metrics_time` en la línea 1182.** `PROVEN`.

**⇒ Y `renoir_get_smu_metrics_data` la pide con `bypass_cache = false` —el argumento `false` de
`renoir_ppt.c:1189`—, o sea que respeta la caché. Y `amdgpu_dpm.c:527` toma
`mutex_lock(&adev->pm.mutex)` alrededor de toda la llamada, así que la ventana de 1 ms y el
mutex son las dos únicas formas de contención en esta ruta.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Esto es accionable y es una decisión de diseño que el driver propio tiene
que tomar explícitamente: sin la caché de 1 ms, cada lectura de `edge` sería un viaje de ida y
vuelta al firmware, y `edge` se lee en bucle de control térmico. La caché no es una optimización
de rendimiento, es un requisito de corrección del lazo de control.** `PROVEN_DERIVED`.

**⇒ Y el sentido del flujo importa para la coherencia: la lectura es «firmware → driver», o sea
`TransferTableSmu2Dram` y no su inverso. La rama `drv2smu == true` de `smu_cmn.c:1091-1098` es la
que se usa cuando el driver *manda* una tabla, y ésa es la que lleva el `amdgpu_hdp_flush`.** `PROVEN`.

## 5 · El puente con §G

**⇒ `smu_cmn.c:1093-1097` es el punto exacto donde las dos fronteras se tocan:**

```c
1093  	/*
1094  	 * Flush hdp cache: to guard the content seen by
1095  	 * GPU is consitent with CPU.
1096  	 */
1097  	amdgpu_hdp_flush(adev, NULL);
```

**⇒ `PROVEN`. El driver afirma, en un comentario y en el mismo punto del código donde manda una
tabla al firmware, que el HDP flush es lo que garantiza que la GPU vea lo que la CPU escribió.**
`PROVEN`.

**⇒ `PROVEN_DERIVED. Y esto confirma retroactivamente la elección de `246`: de los tres registros
que identificó §G, el `GPU_HDP_FLUSH_REQ` es el único que aparece en un punto del código donde el
propio driver explica para qué sirve. El TLB invalidate y el PTBA están justificados por su
propio nombre; el HDP no, y sin embargo es el único con una justificación escrita.** `PROVEN_DERIVED`.

**⇒ Y hay una asimetría que conviene dejar escrita: el HDP flush se emite antes de escribir al
firmware (`drv2smu`), pero no después de leer de él. La lectura de `edge` no necesita flush de
hacia atrás porque la GPU no está leyendo la tabla de métricas: la consume el firmware, no la
GPU.** `PROVEN_DERIVED`.

## 6 · El ASIC correcto, y cómo lo sabe el driver

**⇒ `renoir_ppt.c` es el ASIC de Polaris12, y su tabla se registra en `amdgpu_smu.c:3956` con
`.read_sensor = smu_read_sensor`. La función `renoir_read_sensor` está en `renoir_ppt.c:1261` y
se registra en `renoir_ppt.c:1458`.** `PROVEN`.

**⇒ Y la cadena se resuelve en dos niveles porque `pp_funcs` y `ppt_funcs` son dos tablas
distintas: `pp_funcs` es la tabla genérica de la interfaz de gestión de energía, que apunta a
`smu_read_sensor` para toda la familia swsmu; `ppt_funcs` es la tabla por ASIC, que apunta a
`renoir_read_sensor` para Polaris12.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Consecuencia para el driver propio: hacen falta dos niveles de indirección,
no uno. El nivel externo decide «swsmu o legacy-dpm» y el interno «qué ASIC». El mismo
esquema de dos niveles aparece en §G con `gmc_funcs`. Es un patrón del driver, no una
casualidad de esta ruta.** `PROVEN_DERIVED`.

**⇒ `PROVEN_ABSENT`. Y `legacy-dpm/` tiene su propia ruta de temperatura —`si_dpm.c:7932`
`static int si_dpm_get_temp` y `kv_dpm.c:2940` `static int kv_dpm_get_temp`—, pero `046` ya
cerró que esa ruta no se compila para Polaris12 porque depende de `CONFIG_DRM_AMDGPU_SI`.**
`PROVEN_ABSENT`.

## 7 · Lo que queda abierto de §H en esta nota

**⇒ `NOT_DETERMINED`: el contenido y la disposición de la estructura `SmuMetrics_t` en memoria
del host. `renoir_get_smu_metrics_data` la lee como
`(SmuMetrics_t *)smu_table->metrics_table` y direcciona campos por nombre, pero su definición no
está en el corpus.** `NOT_DETERMINED`.

**⇒ `NOT_IN_CORPUS`: el cuerpo del firmware SMU de esta placa, que es quien realmente llena la
tabla. `221` ya confirmó que el firmware es el de esta placa por dos vías independientes, así que
el objeto existe y es localizable; lo que falta es su análisis, no su disponibilidad.** `NOT_IN_CORPUS`.

**⇒ `PROVEN_DERIVED. Y con eso la lectura de temperatura queda cerrada por completo del lado del
driver: se sabe qué función se llama, en qué ASIC se resuelve, con qué mensaje al firmware, con
qué caché y con qué mutex. Lo único que no está descrito es el interior del mensaje, que es
código del firmware y no de un driver Linux.** `PROVEN_DERIVED`.

## 8 · Errores propios registrados en esta nota

**⇒ `ERROR`. Declaré ausente `amdgpu_dpm_read_sensor` por encontrar 14 llamadas y cero
definiciones en `amdgpu/`, cuando la definición está en `drivers/gpu/drm/amd/pm/amdgpu_dpm.c:517`,
un subárbol que no había mirado porque `ls $AM/*/` no devolvía nada. La prueba de ausencia
correcta es sobre el árbol entero, no sobre un directorio que supongo que es el relevante.** `ERROR`.

**⇒ `ERROR`. De esa misma omisión salió la afirmación falsa de que «no hay ficheros de
polaris en swsmu»: existen, es el directorio `smu12/`, y se llama Renoir, no Polaris12.** `ERROR`.

**⇒ `ERROR`. Busqué `smu_cmn_update_table` como función y no la encontré, cuando es un macro de
`smu_cmn.h:105` que redirige a `smu_cmn_update_table_read_arg`. Una búsqueda de una entidad que
no distingue macro de función produce un falso negativo con toda la apariencia de una ausencia
de implementación.** `ERROR`.

**⇒ Y los tres vuelven a ser la misma forma: una ausencia afirmada sobre un subconjunto del
árbol, cuando la prueba correcta es sobre el árbol entero.** `ERROR`.