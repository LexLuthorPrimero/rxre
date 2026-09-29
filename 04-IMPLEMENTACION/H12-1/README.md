# H12-1 — Probe Vulkan + Wayland clear/present

**Estado:** H12-4 implementado sobre H12-3 y revisado estáticamente; **no se ha ejecutado un smoke H12-4**. El smoke H12-3 previo está aprobado bajo su alcance. H12-1 no es una campaña H12 ni un benchmark.

## Alcance

Este directorio contiene una aplicación C mínima para investigar posteriormente la ruta:

```text
CPU record → Vulkan submit → GPU clear → swapchain/present → Wayland callback
```

La aplicación queda implementada para una fase posterior autorizada. H12-4 no debe ejecutarse hasta recibir una autorización de smoke separada.

### Garantías de diseño

- Wayland nativo mediante `xdg-shell` y `VK_KHR_wayland_surface`.
- Selección fija y verificable del dispositivo Vulkan `vendorID=deviceID=1002:699f`.
  Si no hay exactamente una coincidencia, la aplicación aborta.
- Una sola queue de una familia graphics.
- Un command buffer recording por frame, reutilizado por un slot de recursos;
  no hay compute queue.
- Render pass clear-only, sin shaders, pipelines, geometría ni escritorio.
- Surface y swapchain Vulkan Wayland.
- Dos timestamps GPU por frame cuando la queue y el dispositivo los soportan.
- `VK_EXT_present_timing` solo se activa si están disponibles la extensión, sus
  features, dependencias, dominios y la capacidad de la surface. Se consulta
  únicamente el stage raw `QUEUE_OPERATIONS_END`; no se solicita ni se interpreta
  first pixel.
- `VK_KHR_present_id2` solo se usa cuando la feature y
  `presentId2Supported` de la surface lo permiten; el swapchain incluye
  `VK_SWAPCHAIN_CREATE_PRESENT_ID_2_BIT_KHR` cuando se adjunta un ID.
- `VK_KHR_present_wait2` se consulta como capability de soporte; no se espera,
  no se solicita scheduling y el swapchain no se crea con su flag.
- `VK_EXT_calibrated_timestamps`/`VK_KHR_calibrated_timestamps` se consultan para
  dominios y se usan únicamente para la calibración H12-4
  `VK_TIME_DOMAIN_DEVICE_KHR` ↔ `VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR`.
  `CLOCK_MONOTONIC_RAW`, `PRESENT_STAGE_LOCAL` y `SWAPCHAIN_LOCAL` no
  participan en el mapping H12-4.
- Los semáforos de present se reutilizan por imagen, indexados por la imagen
  adquirida; no se crea un handle vivo por cada frame.
- Una reconfiguración xdg posterior al primer present se registra y solo se
  continúa automáticamente para el caso estrecho `XDG_TOPLEVEL_STATE_ACTIVATED`
  (=4) con extent raw igual al extent activo. No se recrea el swapchain.
- Los demás configures post-present, los estados desconocidos o geométricamente
  sensibles y las condiciones de sincronización insegura mantienen un safety
  hold controlado: H12-1 no implementa todavía recreación de swapchain.
- `wl_surface.frame` se registra como callback del compositor. No se llama vblank,
  first pixel ni display latency.

## Revisión técnica puntual posterior a la aprobación preliminar

La revisión del source corrigió, sin ejecutar el instrumento:

- La capability de surface y el flag de swapchain obligatorios de
  `VK_KHR_present_id2`; los IDs solo se adjuntan cuando esa capability es
  efectiva.
- La capacidad de los arrays de stages de `vkGetPastPresentationTimingEXT` y
  el tratamiento de `time=0` como no disponible.
- La dependencia `VK_KHR_calibrated_timestamps` para present timing y la
  dependencia de `present_wait2` respecto de Present-ID2.
- La carrera de `xdg_surface.configure` posterior al inicio de presents, el
  backpressure `POLLOUT` de Wayland y las esperas acotadas de acquire/fence.
- La reutilización de semáforos de present por imagen, la revalidación del
  contador de dominios de present timing y el delta GPU modular derivado con
  `timestampPeriod`; no se convierte un timestamp GPU en un timestamp absoluto
  de CPU/display.
- La secuencia de inicialización xdg distingue el primer configure, un
  configure pre-present de mismo extent y un configure post-present. El caso
  documentado `XDG_TOPLEVEL_STATE_ACTIVATED=4`, con extent raw `640×360` igual
  al activo, se registra como `POST_PRESENT_STATE_ONLY_CONFIGURE`; no se infiere
  resize ni se recrea el swapchain.
- Los abortos estructurados ahora incluyen fase, frame, código, estado, motivo,
  cleanup, estado final y summary antes de salir con código no cero.
- Cada `xdg_surface.configure` emite un evento diagnóstico con serial, el
  último `xdg_toplevel.configure` observado (width/height/states), estado de
  ack, swapchain, frame y posición respecto del primer present.
- La revisión H12-3 original pasó el schema de `v1` a `v2` para hacer explícitos
  los campos nuevos y la semántica modular; H12-4 actualiza ahora el contrato de
  frame a `v4` según la sección de esquema.

Los resultados parciales de present timing quedan `UNKNOWN`; un resultado completo
con stage `QUEUE_OPERATIONS_END` no disponible también queda `UNKNOWN`. Solo un
stage no cero se marca disponible. El límite de 256 callbacks
`wl_surface.frame` pendientes evita acumulación ilimitada de proxies; al
superarlo se emite `CONFLICT` y se aborta. No se añadieron mediciones de first
pixel, vblank, display latency, ownership efectivo, async overlap ni PCIe.

## Archivos

```text
04-IMPLEMENTACION/H12-1/
├── CMakeLists.txt
├── DEPENDENCIAS.md
├── README.md
├── include/
│   └── h12_probe.h
└── src/
    └── h12_probe.c
```

`CMakeLists.txt` genera el binding xdg-shell en el directorio de build. No se
genera ni modifica código de Mesa, kernel, firmware o servicios.

## Dependencias y build

Las dependencias y su comprobación están detalladas en `DEPENDENCIAS.md`.
No se instala nada automáticamente.

Build fuera del árbol, para no contaminar el repositorio:

```sh
cmake -S 04-IMPLEMENTACION/H12-1 \
      -B /tmp/opencode/h12-1-build
cmake --build /tmp/opencode/h12-1-build --parallel 2
```

El segundo comando solo compila y enlaza. No ejecuta `h12_probe`, no lanza una
campaña, no lee/escribe sysfs y no cambia configuración del sistema. H12-4 no
agrega librerías, headers, paquetes ni servicios; reutiliza Vulkan/Wayland ya
requeridos y las estructuras de propiedades core ya disponibles.

## Ejecución futura (requiere autorización de smoke H12-4)

No ejecutar hasta que H12-2 defina el protocolo, precondiciones, rollback de
logs y autorización explícita. La interfaz prevista es:

```sh
h12_probe --frames N --width W --height H \
          --present-mode fifo --output RUTA_NUEVA.jsonl
```

- `--frames` es finito (default 120; máximo de seguridad del parser:
  1,000,000). H12-2 debe fijar el valor explícitamente en el protocolo.
- El present mode solicitado debe estar soportado; no se cambia silenciosamente.
- `--output` usa creación exclusiva (`wx`): una ruta existente no se sobrescribe.
- El salida por defecto es stdout.
- El binario no se debe lanzar desde esta fase.

## Flujo de ejecución por frame

1. Se adquiere una imagen del swapchain con `vkAcquireNextImageKHR`, en una
   ventana acotada y sirviendo eventos Wayland durante la espera.
2. Se registra `cpu_timestamp_before_recording_ns` inmediatamente antes de
   `vkBeginCommandBuffer`.
3. Se graba un render pass clear-only y, si está disponible, se escriben los
   queries GPU begin/end.
4. Se completa una barrera Wayland pre-present: se despachan configures
   pendientes sin commit-after-present; un extent pre-present diferente se
   aborta.
5. Se solicita `wl_surface.frame` después de esa barrera y antes de
   `vkQueueSubmit`/`vkQueuePresentKHR`.
6. Se captura `calibration_sample` `before_frame` con la función de calibrated
   timestamps disponible y únicamente para DEVICE + CLOCK_MONOTONIC, justo
   antes de solicitar el callback y entrar al tramo submit/present.
7. Se registra `cpu_timestamp_before_submit_ns` justo antes de `vkQueueSubmit`.
8. Se registra `cpu_timestamp_after_submit_ns` justo después de `vkQueueSubmit`.
9. Se registra `present_call_timestamp_ns` justo antes de la llamada y se
   llama a `vkQueuePresentKHR`.
10. Se despachan eventos Wayland, se consultan fences y se recuperan los
    timestamps GPU; al observar el fence y leer las queries se captura
    `calibration_sample` `after_frame`.
11. Se escribe un registro JSONL por frame cuando el GPU y los callbacks/timing
    están listos; al finalizar, un drenado acotado de callbacks/timing convierte
   lo ausente en `NOT_AVAILABLE` o `UNKNOWN` según haya una observación parcial.
   Antes de destruir recursos, cada fence tiene una espera de seguridad acotada
   de 5 s; una expiración es un error y aborta.

El frame interval es exactamente la diferencia entre timestamps de llamada a
`vkQueuePresentKHR` de frames consecutivos. El primer frame no tiene intervalo
y se escribe `null` (`NOT_AVAILABLE`); el campo lleva su fuente explícita.

## Esquema de salida

El archivo es JSON Lines. La primera línea es metadata; después se intercalan
eventos `event=calibration_sample`, `event=frame` y
`event=xdg_surface_configure`. H12-4 extiende el contrato de frame a
`h12-1.frame.v4` y usa `h12-4.metadata.v1`, `h12-4.calibration.v1` y
`h12-4.summary.v1`. El schema de error conserva `h12-1.error.v2` y el
diagnóstico conserva `h12-1.diagnostic.v1` porque no cambia su semántica.
Los timestamps GPU query permanecen raw y la conversión modular de H12-3 no se
convierte en un timestamp CPU/display exacto. El summary incluye el estado final
del mapping, conteos de samples y de candidatos brackets, max deviation raw y
los conteos de polls/callbacks. Los abortos de timing, dominio,
reconfiguración, backlog de callbacks y timeouts de seguridad se escriben como
`event=error` con schema separado. Cada error incluye fase, frame_id cuando
existe, código, estado, motivo, cleanup, estado final y la referencia de summary;
el summary se escribe antes de terminar con código no cero.

### Metadata

- `run_id`, `target_pci`, `selected_pci`, `device_name`, `vendor_id`, `device_id`,
  `device_uuid`, `driver_uuid`, `driver_name`, `driver_info` y `driver_version`.
- `queue_family_index` y `queue_count=1`; `logical_device_scope` y `logical_device_created` registran que la
  corrida usa un único `VkDevice` lógico, sin serializar el handle numérico.
- Extensión/present mode/extent/imágenes del swapchain. Metadata registra
  `initial_xdg_configure_completed` y `xdg_surface_configure_count`; el summary
  registra `swapchain_suboptimal_observed`. Un `VK_SUBOPTIMAL_KHR` se conserva
  como resultado real y no se reinterpreta.
- Capabilities de timestamp queries, present timing, present wait2 y calibrated
  timestamps; se incluyen `calibrated_timestamp_variant`,
  `calibrated_function_available`, `calibrated_domain_query_valid`, dominios
  raw/named, `timestamp_period_ns`, `timestamp_valid_bits`,
  `calibration_same_run_status` y los dominios objetivo
  DEVICE + CLOCK_MONOTONIC.
- `gpu_cpu_clock_correlation=UNKNOWN` en metadata antes de observar samples;
  el estado por frame y el summary se calculan sólo con brackets válidos. La
  calibración H12-4 no es una medición de display, vblank, scanout, first pixel
  ni compositor completion.
- `present_id2_capability`, `present_id2_surface_supported`,
  `present_timing_time_domain_kind`, `present_timing_time_domains_counter` y
  `present_timing_time_domains_counter_final`; este último permite verificar
  si el dominio seleccionado siguió disponible. `present_wait2_swapchain_enabled`
  es `false` porque H12-1 no usa `vkWaitForPresent2KHR`.
- `first_pixel=NOT_AVAILABLE`, `vblank=NOT_AVAILABLE`,
  `display_latency=NOT_AVAILABLE`.
- `queue_ownership_exclusive=UNKNOWN`, `async_overlap=UNKNOWN`.
- `pcie_bandwidth=NOT_AVAILABLE`.

### Evento `h12-4.calibration.v1`

Cada frame intenta dos muestras, `phase=before_frame` y `phase=after_frame`, con
un único `sample_id` por muestra. El evento conserva el resultado raw de
`vkGetCalibratedTimestampsKHR` o `vkGetCalibratedTimestampsEXT`:

- `run_id`, `sample_id`, `phase`, `frame_id`, `device_time_domain`,
  `host_time_domain` y sus IDs numéricos.
- `device_timestamp_ticks`, `host_timestamp_ns`, `max_deviation_ns`,
  `timestamp_period_ns` y `timestamp_valid_bits`; los valores raw son `null`
  únicamente cuando la API no devolvió una muestra válida. El sample no
  enmascara ni desenrolla el valor raw; el mapping aplica `timestampValidBits`
  sólo para comparar y rechaza wrap/no-monotonicidad.
- `calibration_status`, `same_run_validation_status`, `vk_result` y `reason`.
- `device_uuid`, `driver_uuid`, `vendor_id`, `device_id`, `selected_pci`,
  `driver_name`, `driver_info`, `driver_version`, `queue_family_index`,
  `calibrated_timestamp_variant` y `calibrated_function_available`.

El evento separa conceptualmente:

- **RAW:** timestamps y `maxDeviation_ns` tal como fueron devueltos.
- **CALIBRATION:** dominios, bracket phase, sample/frame IDs y fórmula de
  referencia.
- **STATUS:** `PRESENT`, `UNKNOWN` o `NOT_AVAILABLE`.
- **UNCERTAINTY:** `maxDeviation_ns`, `reason`, estado same-run y los deltas de
  drift; no se convierten en una garantía de error futuro.

Un `calibration_status=PRESENT` con `same_run_validation_status=UNKNOWN` sólo
significa que la llamada individual devolvió una muestra raw coherente; no
habilita mapping ni candidato. El candidato requiere ambos contexts en
`PRESENT`.

La lista de dominios tiene un límite de almacenamiento de 16 entradas; si la
API informa más o una respuesta queda truncada, se marca
`calibrated_domains_truncated=true` y el mapping queda `UNKNOWN`, no se acepta
como threshold ni se completa artificialmente.

`CLOCK_MONOTONIC_RAW`, `PRESENT_STAGE_LOCAL` y `SWAPCHAIN_LOCAL` sólo pueden
aparecer como nombres de la lista de dominios auditada por la API; nunca se
solicitan para el mapping H12-4. `maxDeviation_ns` siempre se registra raw cuando
la llamada es exitosa, incluso si vale cero; cero fuerza
`calibration_status=UNKNOWN`. No se compara con `timestampPeriod` y no
representa display latency, vblank, scanout, first pixel, compositor completion
ni precisión futura.

### Mapping y drift por frame

El frame referencia sus samples con `calibration_before_sample_id` y
`calibration_after_sample_id`. Sólo una muestra `PRESENT` en cada extremo,
validada same-run y con timestamps GPU dentro del bracket, habilita:

```text
host_sample_ns + (gpu_timestamp_ticks - device_sample_ticks)
                  * timestamp_period_ns
```

El resultado se guarda como `gpu_timestamp_begin_cpu_candidate_ns` y
`gpu_timestamp_end_cpu_candidate_ns`, explícitamente **candidate estimate**.
La conversión a nanosegundos enteros exige que el producto sea representable
sin redondeo silencioso; si no lo es, se conserva `null` y `UNKNOWN`.
Se selecciona el sample endpoint más cercano (`NEAREST_BRACKETED`) sin
interpolación silenciosa. `gpu_clock_mapping_spread_ns` es el mayor spread
entre las dos candidatas; `gpu_clock_mapping_source_sample_id` es `null` si
begin y end requirieron samples distintos. `gpu_clock_mapping_max_deviation_ns`
es el máximo raw de los dos samples y se conserva aunque el bracket o la
aritmética haga fallar el mapping. Si falta bracket, hay overflow, no
monotonicidad no explicada, coerencia aritmética imposible o cualquier
validación same-run incompleta, ambos candidates son `null` y
`gpu_clock_correlation_status=UNKNOWN` (o `NOT_AVAILABLE` si la capability
no existe). `PRESENT` aquí sólo describe que se produjeron candidates
bracketados; no certifica precisión ni causalidad.

Entre muestras consecutivas se registran `calibration_device_delta_ticks`,
`calibration_device_delta_ns`, `calibration_host_delta_ns` y
`calibration_residual_ns`. El residual es un diagnóstico de drift con aritmética
segura, no una métrica de precisión y no tiene threshold de aceptación.

### Diagnóstico xdg-shell

Cada evento `xdg_surface.configure` registra evidencia observable y la
clasificación derivada de ella: serial, `configure_index`, si hubo un
`xdg_toplevel.configure` inmediatamente antes, width/height/states raw del
toplevel, `ack_configure_requested`,
`surface_configured`, extent activo (`surface_width`/`surface_height`), estado de
surface/swapchain, frame actual, `submitted_frames` y
`first_present_completed`. `toplevel_states` es el array raw de estados; el
registro agrega `classification` y `state_only` para dejar explícita la
decisión. El caso `POST_PRESENT_STATE_ONLY_CONFIGURE` sólo se permite para un
único estado raw `XDG_TOPLEVEL_STATE_ACTIVATED=4`, con extent raw igual al
activo, configure role inmediatamente anterior, swapchain válido y ninguna
operación WSI crítica en curso. No se interpreta activation como keyboard/pointer
focus. La revisión conserva `h12-1.diagnostic.v1`; `classification` y
`state_only` son campos aditivos para las ejecuciones futuras.

### Evidencia documental de xdg-shell y Vulkan WSI

> **Nota H12-2:** la reconciliación primaria, los hashes de r1/r2/r3 y la
> matriz completa de hallazgos están en
> `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`.
> H12-2 r4 validó `POST_PRESENT_STATE_ONLY_CONFIGURE` con `ACTIVATED=4` y
> extent `640×360`; el resultado histórico de r3 permanece
> `POST_PRESENT_CONFIGURE_UNCLASSIFIED` y no se modifica.

La clasificación se basa en evidencia documental y de la evidencia runtime ya
registrada; las fuentes externas no sustituyen una observación del compositor:

- El build local consume
  `/usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml` desde
  `wayland-protocols 1.49`. El XML define `activated=4`; la fuente canónica es
  [wayland-protocols/xdg-shell](https://gitlab.freedesktop.org/wayland/wayland-protocols).
- El header generado confirma
  `XDG_TOPLEVEL_STATE_ACTIVATED=4`. H12-1 hace bind de `xdg_wm_base` con
  versión 1, donde `xdg_toplevel.configure`, `xdg_surface.configure` y
  `xdg_surface.ack_configure` ya existen.
- xdg-shell define la secuencia role configure → `xdg_surface.configure(serial)`
  → `ack_configure`; el ack puede preceder al commit y no obliga a hacer un
  commit inmediato. La implementación conserva el ack del serial recibido.
- La especificación Vulkan WSI para Wayland establece que la implementación de
  `vkQueuePresentKHR` emite `wl_surface.attach`, `damage` y `commit` para la
  imagen presentable. El commit xdg inicial es previo y separado; después de
  que WSI/presentation comenzó, la aplicación no debe duplicar el commit del
  buffer presentable. Fuente: [Vulkan WSI Wayland v1.4.341](https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.341/chapters/VK_KHR_surface/wsi.adoc) y [navegable actual](https://docs.vulkan.org/spec/latest/chapters/VK_KHR_surface/wsi.html#platformCreateSurface_wayland).
- La evidencia runtime de r3 es
  `/tmp/opencode/h12-2-smoke-20260924-rx550-r3.jsonl`; su línea histórica
  `POST_PRESENT_CONFIGURE_UNCLASSIFIED` no se modifica. La nueva clasificación
  sólo se aplica a futuras ejecuciones y no modifica r1/r2/r3.

La documentación no demuestra first pixel, vblank, display latency, ownership
exclusivo, async overlap ni PCIe bandwidth. También permanece `UNKNOWN` la
causa concreta que hizo que el compositor enviara el segundo configure, la
combinación de estados que podría aparecer en otra corrida y cualquier cambio
de extent/output posterior.

### Registro por frame

| Campo JSONL | Significado |
|---|---|
| `run_id`, `device_uuid`, `driver_uuid`, `selected_pci`, `driver_name`, `driver_version` | Contexto repetido en cada frame para validar que el sample y el frame pertenecen a la misma corrida y al mismo `VkDevice` lógico; no se usa el handle numérico. |
| `frame_id` | Índice 0-based de la corrida. |
| `cpu_timestamp_before_recording_ns` | `CLOCK_MONOTONIC` antes de `vkBeginCommandBuffer`. |
| `cpu_timestamp_before_submit_ns` | `CLOCK_MONOTONIC` inmediatamente antes de `vkQueueSubmit`. |
| `cpu_timestamp_after_submit_ns` | `CLOCK_MONOTONIC` inmediatamente después de `vkQueueSubmit`. |
| `frame_callback_requested_cpu_ns` | `CLOCK_MONOTONIC` justo antes de emitir `wl_surface.frame`; `null` si no se obtuvo. |
| `frame_callback_received_cpu_ns` | `CLOCK_MONOTONIC` al entrar al callback `wl_callback.done`; `null` si no se obtuvo. |
| `cpu_callback_request_to_receive_ns` | Diferencia CPU host-side entre request y recepción, sólo si ambos timestamps son válidos y el orden es coherente; no es display latency. |
| `gpu_timestamp_status` | `PRESENT`, `UNKNOWN`, `CONFLICT` o `NOT_AVAILABLE`. |
| `gpu_query_result` | Resultado Vulkan real de la lectura de queries; `null` si no se solicitó. |
| `gpu_timestamp_begin_ticks`, `gpu_timestamp_end_ticks` | Valores raw de timestamp query, si existen. |
| `gpu_elapsed_ticks_modulo` | Diferencia modular de ticks después de aplicar `timestampValidBits`; no unwraps absolutos. |
| `gpu_elapsed_ns_from_period_modulo` | Conversión del delta modular usando `timestampPeriod`; puede ser `null` si excede el rango. |
| `gpu_elapsed_conversion_status` | `PRESENT` solo si la conversión modular fue representable; no es timestamp de display. |
| `calibration_before_sample_id`, `calibration_after_sample_id` | Samples H12-4 que forman el bracket del frame; `null` si no se capturaron. |
| `calibration_before_status`, `calibration_after_status` | Status individual de cada sample; no se promotionalmente convierte en mapping válido. |
| `calibration_same_run_status` | Validación de identidad/contexto de la corrida; no es una afirmación de display. |
| `gpu_clock_correlation_status` | Estado conservador del mapping DEVICE→CLOCK_MONOTONIC; no claims de presentación física. |
| `gpu_timestamp_begin_cpu_candidate_ns`, `gpu_timestamp_end_cpu_candidate_ns` | Estimaciones CPU candidatas, sólo con bracket; no son timestamps CPU exactos. |
| `gpu_clock_mapping_method` | `NEAREST_BRACKETED` cuando hay candidate; no hay interpolación. |
| `gpu_clock_mapping_source_sample_id` | Sample endpoint común usado por begin/end; `null` si son distintos. |
| `gpu_clock_mapping_spread_ns` | Mayor separación entre candidatas bracketing; diagnóstico, no garantía. |
| `gpu_clock_mapping_max_deviation_ns` | Máximo `maxDeviation` raw de los samples del bracket. |
| `calibration_drift_status` y `calibration_*_delta_*`, `calibration_residual_ns` | Drift diagnóstico entre before/after; residual no es precisión ni acceptance threshold. |
| `gpu_fence_observed_cpu_ns` | `CLOCK_MONOTONIC` en el instante en que el host observó el fence como completado; no es finalización GPU, present completion, vblank ni first pixel. |
| `gpu_fence_observation_source` | `vkGetFenceStatus` o `vkWaitForFences`, según la ruta existente que observó el fence; `null` si no hubo timestamp válido. |
| `present_call_timestamp_ns` | `CLOCK_MONOTONIC` inmediatamente antes de `vkQueuePresentKHR`. |
| `present_id_requested`, `present_id_assigned` | ID efectivamente adjunto al present y su valor; `null` si no se solicitó. |
| `present_timing_status` | `PRESENT`, `UNKNOWN`, `CONFLICT` o `NOT_AVAILABLE`. |
| `present_timing_report_complete` | `reportComplete` raw; un stage con tiempo cero no se marca disponible. |
| `present_timing_present_id` | ID raw devuelto por present timing; se correlaciona con el ID enviado por `VK_KHR_present_id2`. |
| `present_timing_target_requested` | `false` en H12-1: no se solicita target time. |
| `present_timing_target_time_ns` | Valor raw de la API (`targetTime=0`); no se interpreta como vblank. |
| `present_timing_stage_count`, `present_timing_stage_mask` | Datos raw del stage solicitado. No se nombra ni se convierte first pixel. |
| `present_timing_queue_operations_end_time` | Tiempo raw del stage `QUEUE_OPERATIONS_END`, si la API lo entrega; no es vblank. |
| `present_timing_time_domain`, `present_timing_time_domain_id` | Dominio raw de la API, sin asumir equivalencia con CPU. |
| `wl_surface_frame_callback_status` | `PRESENT`, `UNKNOWN` o `NOT_AVAILABLE`; es un callback de compositor. |
| `wl_surface_frame_callback_time_ms` | Tiempo entregado por Wayland al callback, no vblank. |
| `frame_interval_ns` | Diferencia entre llamadas a present; `null` en el primer frame. |
| `frame_interval_source` | `present_call_cpu_monotonic`; no es intervalo GPU/display. |
| `image_index` | Índice de imagen del swapchain adquirido. |
| `acquire_result`, `submit_result`, `present_result`, `present_per_image_result` | Results Vulkan realmente obtenidos. |

Los valores no disponibles se escriben como `null` y acompañan un status
explícito. No se rellenan con estimadores.

### Núcleo de observabilidad H12-3

El núcleo H12-3 agrega únicamente observaciones host-side del mismo lifecycle:

- `frame_callback_requested_cpu_ns` se captura inmediatamente antes de
  `wl_surface_frame`.
- `frame_callback_received_cpu_ns` se captura al procesar `wl_callback.done`.
- `cpu_callback_request_to_receive_ns` sólo se calcula si ambos valores existen
  y la recepción es posterior a la solicitud.
- `gpu_fence_observed_cpu_ns` se captura en el punto existente donde
  `vkGetFenceStatus` o `vkWaitForFences` devuelve `VK_SUCCESS`.
- `gpu_fence_observation_source` identifica esa ruta existente.

No se agrega ninguna espera para obtener los timestamps. Los nuevos campos no
modifican la espera de acquire, la espera de fence, el polling, el número de
frames ni el callback de `wl_surface.frame`. Son `null` si `CLOCK_MONOTONIC` no
puede obtenerse. Un fence observado por el host no representa el instante exacto
de finalización GPU, present completion, vblank, first pixel o display latency.
El `wl_surface_frame_callback_time_ms` existente permanece raw, con base de
tiempo indefinida; no se convierte a CPU/GPU ni se correlaciona.

Los timestamps CPU y GPU permanecen en dominios separados. H12-3 no agrega
sysfs/hwmon, DRM fdinfo, métricas por frame, swapchain recreation, nuevos
estados xdg, Present-ID2, present timing, present wait ni benchmark. H12-4
agrega únicamente una calibración same-run DEVICE↔CLOCK_MONOTONIC; no agrega
una correlación con compositor/display.

## Límites y riesgos

- No hay prueba de correlación end-to-end entre reloj GPU, `CLOCK_MONOTONIC` y
  compositor. H12-4 sólo captura y valida una calibración same-run
  DEVICE↔CLOCK_MONOTONIC; cualquier mapping hacia compositor/display permanece
  `UNKNOWN`/`NOT_AVAILABLE`.
- `maxDeviation_ns` se conserva raw y no se compara con `timestampPeriod`, no
  define un threshold y no garantiza error futuro, frecuencia, latencia ni
  precisión del candidate estimate.
- El bracket exige before/after del mismo run, mismo `VkDevice` lógico, UUIDs,
  dominio, período y bits válidos. No se desenrolla wrap ni se convierte una
  disminución no explicada en drift válido; la aritmética no representable
  deja el candidate en `null` y el mapping en `UNKNOWN`.
- `wl_surface.frame` no prueba que el frame sea visible ni que exista un pixel
  mostrado.
- `VK_EXT_present_timing` puede entregar resultados parciales, cambiantes o
  correlacionados por dominio. El probe no rellena faltantes. Si cambia el
  `timeDomainsCounter`, revalida la lista; si el dominio seleccionado ya no está
  disponible se registra `CONFLICT` y se aborta. Un resultado parcial o un
  stage con tiempo cero permanece `UNKNOWN`; si la cola de timing devuelve
  `VK_ERROR_PRESENT_TIMING_QUEUE_FULL_EXT`, se registra `CONFLICT` y la
  corrida aborta sin reintentar el semáforo consumido.
- El tamaño final de la surface se registra después de la configuración xdg;
  no se asume que coincida con el argumento si el compositor impone otro valor.
- La espera de acquire se acota a 1 s por frame y la espera de seguridad de
  fence a 5 s; durante ellas se siguen despachando eventos Wayland. H12-2 debe
  fijar la política de abort y el registro de un timeout.
- La llamada final `vkDeviceWaitIdle` no tiene un timeout portable en Vulkan;
  H12-2 debe envolver la corrida con un watchdog externo y abortar el proceso
  si el ICD no completa el cleanup. Un `fatal()` con log inicializado intenta
  cleanup seguro; si el propio cleanup no puede completarse, summary conserva
  `cleanup_status=STARTED` y el proceso termina con código no cero.
- Un configure xdg inicial o pre-present de mismo extent se completa antes de
  solicitar `wl_surface.frame`. Un extent pre-present diferente mantiene el
  safety hold `SURFACE_PRE_PRESENT_EXTENT_CHANGE`.
- Un configure post-present con un único estado raw
  `XDG_TOPLEVEL_STATE_ACTIVATED=4`, extent raw igual al activo, configure role
  inmediatamente anterior y swapchain válido se clasifica como
  `POST_PRESENT_STATE_ONLY_CONFIGURE`: no se genera `CONFLICT`, no se recrea el
  swapchain y no se emite un commit de aplicación; WSI conserva la propiedad de
  `attach`/`damage`/`commit` durante present.
- Mantienen safety hold y `CONFLICT`: extent incompatible o no disponible,
  estado distinto de `ACTIVATED`, estado desconocido o truncado, ausencia del
  configure role inmediatamente anterior, swapchain no válido, configure durante
  una operación WSI crítica, o cualquier condición de sincronización no segura.
  `POST_PRESENT_CONFIGURE_UNCLASSIFIED` permanece para evidencia que no permite
  aplicar la vía state-only; no es un error del compositor.
- Un resultado `VK_SUBOPTIMAL_KHR` se conserva y se marca en el summary, pero
  no se reinterpreta como resize confirmado. No se implementa recreación de
  swapchain, rotación, resize dynamic, `present_wait2` bloqueante ni scheduling
  de target times en H12-1.
- El límite de 1,000,000 frames es solo una guarda del parser; una corrida
  científica debe usar un número mucho menor y ser definida por H12-2. El
  límite de 256 callbacks `wl_surface.frame` pendientes es una guarda de
  lifetime; no se debe aumentar sin un protocolo de backpressure/cleanup.
- No se mide ownership efectivo de queues/clientes, async overlap, ACE/CU,
  first pixel, vblank, display latency, PCIe payload ni bandwidth.
- La aplicación no es un benchmark: no calcula FPS, throughput, score ni
  clasificación de bottleneck.

## H12-3 — historial y preservación

H12-2 r4 quedó aprobado bajo su alcance: el segundo configure runtime fue
`POST_PRESENT_STATE_ONLY_CONFIGURE`, no activó safety hold y emitió dos frames.
El smoke H12-3 posterior validó los campos host-side y quedó aprobado bajo su
alcance. H12-4 conserva esos invariantes y no modifica la evidencia histórica.

## H12-4 — implementación estática; smoke pendiente

H12-4 está implementado como extensión conservadora de H12-3. La compilación y
el análisis estático no autorizan ni sustituyen un smoke runtime.

La implementación:

- carga la función KHR/EXT realmente disponible y consulta dominios, pero sólo
  solicita `DEVICE` + `CLOCK_MONOTONIC` en cada muestra;
- captura `before_frame` justo antes de la secuencia callback/submit y
  `after_frame` después de observar el fence y leer las queries, sin espera
  artificial, flush explícito por sample ni cambio de acquire/submit/present/
  polling/cleanup;
- emite `h12-4.calibration.v1` con raw, status, same-run y uncertainty;
- calcula brackets y nearest-endpoint candidates sólo con aritmética segura;
- registra drift residual sin threshold y trata wrap, overflow o
  no-monotonicidad no explicada como `UNKNOWN`;
- conserva todos los claims negativos de H12-3: no first pixel, vblank, scanout,
  display latency, visible frame, compositor completion, ownership, async
  overlap ni PCIe.

No se implementó `PRESENT_WITH_HIGH_DEVIATION`; no existe threshold numérico
para `maxDeviation`. `gpu_timestamp_begin_cpu_candidate_ns` y
`gpu_timestamp_end_cpu_candidate_ns` son estimates candidatos, no timestamps
CPU exactos.

### Smoke H12-4

**No autorizado.** No ejecutar `h12_probe`, smoke, benchmark, campaña,
experimento, cambio de servicio, governor, DPM, power cap, runtime PM, IRQ,
scheduler, red, sudo, `/sys` o commit/push/merge sin una autorización separada.
La verificación realizada para H12-4 se limita a build, análisis estático,
revisión de diff/invariantes y dependencias.
