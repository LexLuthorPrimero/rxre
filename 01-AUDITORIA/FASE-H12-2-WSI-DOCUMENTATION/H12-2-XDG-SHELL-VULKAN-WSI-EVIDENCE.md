# H12-2 — Evidencia documental del ciclo Wayland/xdg-shell/Vulkan WSI

**Fecha de corte:** 2026-09-24
**Alcance:** únicamente H12-2 y la reconciliación de sus artefactos r1/r2/r3.
**Tipo de trabajo:** documental/read-only. No se ejecutó una nueva corrida, no se programaron contadores, no se modificó configuración del sistema y no se realizaron cambios de Vulkan/KMS/PM.

## 1. Resultado ejecutivo

1. El XML local utilizado por el build es
   `wayland-protocols` **1.49**, archivo estable `stable/xdg-shell/xdg-shell.xml`,
   cuyo contenido coincide byte a byte con el tag oficial `1.49`. El archivo
   declara interfaces xdg-shell **v7** y el binding generado contiene
   `XDG_TOPLEVEL_STATE_ACTIVATED = 4`.
2. H12-1 hace bind deliberado de `xdg_wm_base` con **versión 1** en el source
   revisado. La versión global anunciada por el compositor no quedó en el
   metadata de H12-2; por tanto, no se afirma que el compositor haya negotiado
   v7. Las reglas usadas por H12-2 (`configure`, `ack_configure`, commit inicial
   y `activated=4`) existen en v1.
3. En r3, `xdg_toplevel.configure` mostró `width=640`, `height=360`,
   `states=[4]`. Contra la versión exacta, `4` significa
   **`xdg_toplevel.state.activated`**. No significa fullscreen, maximizado,
   `resizing`, teclado focused, puntero focused ni error del compositor.
4. El segundo `xdg_surface.configure` (serial 12837) fue observado por el
   cliente después de que `vkQueuePresentKHR` ya había regresado, pero la
   secuencia no contiene un timestamp del compositor ni un evento que identifique
   la causa. Por eso:
   - la regla absoluta «configure posterior al primer present = conflicto» queda
     **REFUTED** como regla de protocolo;
   - la intención exacta del compositor y la causa del evento quedan `UNKNOWN`;
   - el evento no se declara benigno, resize, fullscreen, maximización ni error.
5. `states=[4]` más el extent igual a `640×360` no prueba un resize. La
   compatibilidad de un swapchain no cambia por un estado `activated` por sí
   sola; sin embargo, H12-2 abortó antes de demostrar una continuación posterior
   al evento. La recreación y la compatibilidad runtime post-configure siguen
   sin cerrarse.
6. La especificación Vulkan para Wayland establece que la implementación WSI
   emite `wl_surface.attach`, `damage` y `commit` durante
   `vkQueuePresentKHR`, y que la aplicación que quiera sincronizar cambios de
   ventana con un frame debe enviar sus requests antes de esa llamada. El
   commit xdg inicial es anterior y separado; después de que la presentación WSI
   comenzó, el cliente no debe duplicar el attach/damage/commit del buffer
   presentable.
7. H12-2 cierra una parte de la **auditoría de capacidad y semántica de WSI**,
   no la hipótesis causal H12. `VK_KHR_present_id2`, present timing y
   `VK_KHR_present_wait2` no están disponibles en r3; first pixel, vblank y
   display latency siguen `NOT_AVAILABLE`. La pregunta «¿M1 estaba limitado por
   GPU completion o por presentación/VSync?» sigue causalmente `UNKNOWN`.

## 2. Fuentes primarias y referencias

### 2.1 xdg-shell local y oficial

- **Archivo local exacto:**
  `/usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml`
- **Paquete:** `wayland-protocols-devel-1.49-1.fc44.noarch`
- **SHA-256 local:**
  `7ba7f9c8473deee674cb1f154a18abd0bb0cc072604fc055b0c15e459fc4c7df`
- **Tag oficial:**
  `https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/1.49/stable/xdg-shell/xdg-shell.xml`
- **Copia raw/mirror usada para comparación:**
  `https://raw.githubusercontent.com/wayland-mirror/wayland-protocols/1.49/stable/xdg-shell/xdg-shell.xml`
- La comparación local/tag fue byte a byte idéntica.
- **Versión de protocolo:** `xdg_wm_base`, `xdg_surface` y `xdg_toplevel`
  declaran `version="7"`.
- **Líneas relevantes del XML local:** `xdg_surface` 409–618;
  `ack_configure` 560–593; `xdg_surface.configure` 598–618; `state` 830–948;
  `xdg_toplevel.configure` 1144–1172; `set_maximized` 1030–1051.

### 2.2 Wayland core local

- **Archivo local:** `/usr/share/wayland/wayland.xml`
- **Paquete:** `wayland-devel-1.25.0-1.fc44.x86_64`
- **SHA-256 local:**
  `08fb558d96742b41eab330c386f7b0c17d82169e69edad612ea89c17d6b1d53e`
- **Tag oficial:**
  `https://gitlab.freedesktop.org/wayland/wayland/-/blob/1.25.0/protocol/wayland.xml`
- **Copia raw/mirror usada para comparación:**
  `https://raw.githubusercontent.com/wayland-mirror/wayland/1.25.0/protocol/wayland.xml`
- La comparación local/tag fue byte a byte idéntica.
- **`wl_surface.commit`:** líneas 1709–1724 del XML local. El commit crea una
  actualización de contenido desde el estado pending; no convierte un callback
  de frame en vblank.

### 2.3 Vulkan WSI

- **Especificación fijada al header local:** Vulkan `v1.4.341`
  (`/usr/include/vulkan/vulkan_core.h`, `VK_HEADER_VERSION 341`).
- **Capítulo WSI versionado:**
  `https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.341/chapters/VK_KHR_surface/wsi.adoc`
- **SHA-256 del `.adoc` versionado descargado:**
  `0774c8044cf42663f9bac2abe7c62d019184edc64b2bb3ddf20a2a7083fa1224`
- **URL navegable oficial:**
  `https://docs.vulkan.org/spec/latest/chapters/VK_KHR_surface/wsi.html#platformCreateSurface_wayland`
- **Extensión de swapchain y resultados:**
  `https://registry.khronos.org/vulkan/specs/latest/man/html/VK_KHR_swapchain.html`,
  `https://registry.khronos.org/vulkan/specs/latest/man/html/VkSwapchainCreateInfoKHR.html`
- **Secciones versionadas usadas:** Wayland `currentExtent` y
  `wl_surface.commit` (líneas 226–261 del `.adoc`); resultados
  `VK_SUBOPTIMAL_KHR`/`VK_ERROR_OUT_OF_DATE_KHR` (6961–6999 y 7150–7181).
- **Extensión local:** `VK_KHR_wayland_surface` header version 6
  (`/usr/include/vulkan/vulkan_wayland.h`). El metadata de H12-2 no registra la
  revisión de la extensión negociada por el ICD.

### 2.4 Mesa upstream/local como corroboración source-level

- **Checkout local:** commit
  `c5e413533f461cffb98150c9d91908ea1911c589`
  (`26.1-branchpoint-1415-gc5e413533f4`).
- **Archivo:** `src/vulkan/wsi/wsi_common_wayland.c`
- **URL upstream:**
  `https://github.com/mesa3d/mesa/blob/c5e413533f461cffb98150c9d91908ea1911c589/src/vulkan/wsi/wsi_common_wayland.c`
- En `wsi_wl_swapchain_queue_present` se observan `wl_surface_attach`, damage y
  `wl_surface_commit` dentro de la ruta de present (aprox. líneas 3180–3417 del
  checkout local). Esto corrobora la regla oficial de Vulkan, pero no sustituye
  a la especificación ni prueba por sí solo el ICD exacto que ejecutó H12-2.

### 2.5 Build y artefactos H12-2

- CMake: `04-IMPLEMENTACION/H12-1/CMakeLists.txt`, líneas 18–45; resuelve
  `pkgdatadir` y usa `stable/xdg-shell/xdg-shell.xml`.
- Build revisado: `/tmp/opencode/h12-1-build-review/`.
- La regla de build contiene literalmente
  `/usr/bin/wayland-scanner client-header //usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml`.
- `wayland-scanner`: `1.25.0`.
- **Artefactos generados del build:** header SHA-256
  `23778840e17096e2b83138aadc171d626b6f3b8e05bf29ba5ccdd65cb92fbb5a` y
  protocol.c SHA-256
  `6acb725de29bab4d19a0ef629f1e97ed4fe05e8028f147daa4685f388077aaf3`.
- **Binario de r3 disponible:** SHA-256
  `0f6a0dc84ee2c31a72cc834e6c73e55255607b1bb1a1b931c76e446fcb244760`.
- Artefactos r1/r2/r3:
  - r1: `/tmp/opencode/h12-2-smoke-20260924-rx550.jsonl`,
    SHA-256 `81f4f085b9a13fe39018240a7c3922cf5fd0a14121a0a70a19fb98cca643b0e7`.
  - r2: `/tmp/opencode/h12-2-smoke-20260924-rx550-r2.jsonl`,
    SHA-256 `77b482a356331ad16df469e4e2d7b39ecfe66d37788a8afe9df8ff2a4e7c1ffc`.
  - r3: `/tmp/opencode/h12-2-smoke-20260924-rx550-r3.jsonl`,
    SHA-256 `f54c81d097ebc25e391d24f693ccd2522ba7f3a36ca750062ef6e3bbf6f9a4bb`.
- **stderr complementario:** los tres archivos `.stderr.txt` tienen SHA-256
  `e89d4626e7596e6ce2101383a8e879d0d56743fe460c40d9d73f12b7c3b7e0b9`,
  `5866ecab9ec8a0a37d27bac17ec8d87ef659a08b807d30ffde6bd5cae1dd5f2c` y
  `f7e3a4171f4a69ea2468936d4102f9fa7890763499a3de5223abf25600e724fa`,
  respectivamente; sus textos se citan en §3.5. Las rutas `/tmp` son
  efímeras; los hashes y los extractos de este informe son el registro durable
  de esta reconciliación.

## 3. Datos locales de H12-2

### 3.1 Metadata de r3

El primer registro de r3 (`schema=h12-1.metadata.v2`) confirma:

| Campo | Valor |
|---|---|
| target | `1002:699f` |
| PCI seleccionado | `0000:01:00.0` |
| nombre | `AMD Radeon RX 550 / 550 Series (RADV POLARIS12)` |
| vendor/device | `0x1002` / `0x699f` |
| superficie/swapchain | `640×360`, 3 imágenes |
| queue | family 0, count 1 |
| present mode | solicitado y seleccionado `FIFO` |
| timestamp query | `PRESENT`, 64 bits válidos, período 40 ns |
| calibrated timestamps | `PRESENT`, 4 dominios |
| Present-ID2 | `NOT_AVAILABLE` |
| present timing | `NOT_AVAILABLE` |
| Present-Wait2 | `NOT_AVAILABLE` |
| first pixel/vblank/display latency | `NOT_AVAILABLE` |
| PCIe payload | `NOT_AVAILABLE` |

El metadata se escribe durante la inicialización; por eso su
`xdg_surface_configure_count=1` no contradice el summary final con count 2.

### 3.2 Secuencia inicial observada

Registro `h12-1.diagnostic.v1`, `configure_index=1`:

```json
{"phase":"initialization","serial":12832,
 "toplevel_configure_seen_before_surface_configure":true,
 "toplevel_width":0,"toplevel_height":0,
 "toplevel_states":[],
 "initial_configure_completed":false,
 "ack_configure_requested":true,
 "swapchain_created":false}
```

Interpretación limitada: el compositor envió una configuración inicial con
width/height en cero y sin estados. El cero no es un tamaño de buffer cero: la
especificación dice que el cliente decide esa dimensión. El primer commit de
superficie sin buffer, el ack y la configuración quedaron completados antes de
crear el swapchain; esto sí coincide con la secuencia inicial documentada por
xdg-shell.

### 3.3 Segundo configure observado

Registro `h12-1.diagnostic.v1`, `configure_index=2`:

```json
{"phase":"post_present","frame_id":1,"serial":12837,
 "toplevel_configure_seen_before_surface_configure":true,
 "toplevel_width":640,"toplevel_height":360,
 "toplevel_states":[4],"toplevel_states_truncated":false,
 "surface_configured":true,"surface_width":640,"surface_height":360,
 "swapchain_created":true,"swapchain_image_count":3,
 "initial_configure_completed":true,"presentation_started":true,
 "first_present_completed":true,"present_call_in_progress":false,
 "submitted_frames":2,"ack_configure_requested":true,
 "surface_reconfigure_pending":false}
```

El `surface_reconfigure_pending=false` es el estado dentro del callback antes de
que la aplicación aplique su safety hold. El error posterior registra el hold como
`surface_reconfigure_pending=true`. `submitted_frames=2` y
`first_present_completed=true` prueban que el cliente había regresado de
`vkQueuePresentKHR` para el primer frame; no prueban que un pixel haya sido
visible.

### 3.4 r1, r2 y r3

| Corrida | Evidencia | Resultado observado |
|---|---|---|
| r1 | JSON de 2 líneas; solo metadata y `SURFACE_RECONFIGURE_AFTER_PRESENT_START`; sin summary ni campos de cleanup | El evento se observó después de iniciar la presentación y el proceso terminó por la vía fatal. El artefacto no permite certificar cleanup. |
| r2 | Error estructurado en `drain`, `cleanup_performed=false`, `cleanup_status=NOT_STARTED`, summary con `frames_submitted=2`, `frames_emitted=0`, `pending_frame_callbacks_final=1` | El safety hold y el summary eran visibles, pero el cleanup no había comenzado. |
| r3 | Dos diagnostics completos, error `POST_PRESENT_CONFIGURE_UNCLASSIFIED`, `cleanup_performed=true`, `cleanup_status=COMPLETED`, summary `pending_frame_callbacks_final=0` | La seguridad pudo terminar y registrar el estado; el segundo configure siguió clasificado por la instrumentación de r3 como no decidido. |

Las etiquetas `CONFLICT` de r1–r3 son estados de la política de safety hold de
H12-1, no una afirmación de que el compositor emitiera un error xdg-shell.

### 3.5 stderr complementario

Los stderr asociados con los tres artefactos registran la evolución de la
instrumentación, no una clasificación causal nueva:

- r1: `xdg_surface.configure arrived after Vulkan presentation started; H12-1 does not recreate the swapchain`.
- r2: `xdg_surface.configure arrived after the first completed present`.
- r3: `xdg_surface.configure arrived after the first present; raw toplevel state and dimensions were recorded, but the event is not classified as resize, benign, or compositor error`.

La frase «not classified» de r3 es explícita: la propia corrida no se
clasificó el evento como resize, benigno o error.

## 4. Hallazgos documentales

### H12-2-D01 — ¿Cuál es la versión exacta del `xdg-shell.xml` local?

- **Pregunta:** identificar el XML, tag, versión de interfaz y binding usados
  localmente.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** paquete local, CMake, regla de build y tag oficial.
- **URL/referencia:** `CMakeLists.txt:18–45`; tag oficial
  `https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/1.49/stable/xdg-shell/xdg-shell.xml`.
- **Evidencia exacta:** `pkg-config --modversion wayland-protocols` devuelve
  `1.49`; el RPM es `wayland-protocols-devel-1.49-1.fc44.noarch`; el hash local
  coincide con el raw del tag; el XML declara `version="7"`; el build usa
  `/usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml` con
  `wayland-scanner 1.25.0`.
- **Interpretación:** el binding generado puede contener la API v7, pero eso no
  significa que H12-1 haya negotiated v7 con el compositor.
- **Demuestra:** la versión del XML local y la procedencia del build.
- **No demuestra:** la versión global del compositor, la revisión del ICD
  Vulkan, ni el comportamiento de un compositor distinto.
- **Limitaciones:** el metadata de H12-2 no contiene un hash del XML ni la
  versión de `xdg_wm_base` negociada.
- **Estado final:** `CONFIRMED`.

### H12-2-D02 — ¿La versión de runtime fue v7 o v1?

- **Pregunta:** separar capacidad del XML generado de la versión realmente
  negociada por H12.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** source H12 `src/h12_probe.c`; CMake build rule.
- **URL/referencia:** source local, función `registry_global`; el source
  revisado contiene `bind_version = version < 1u ? version : 1u`.
- **Evidencia exacta:** el source limita intencionadamente el bind de
  `xdg_wm_base` a versión 1; el header generado conserva constantes v7;
  `xdg_toplevel.configure`, `xdg_surface.configure` y `ack_configure` no tienen
  `since` que los limite a una versión posterior.
- **Interpretación:** la semántica mínima necesaria para H12-2 es v1; el
  número de versión del bind no cambia los valores del enum `state` (por
  ejemplo, `activated=4`). No se debe afirmar que el compositor ofreció o
  aceptó v7.
- **Demuestra:** intención de bind source-level y disponibilidad de las
  operaciones usadas.
- **No demuestra:** el valor de `wl_registry.global.version` observado en la
  sesión, ni que el compositor implementara extensiones v2–v7.
- **Limitaciones:** el binario/log no serializa la versión del registry.
- **Estado final:** `PARTIALLY CONFIRMED`.

### H12-2-D03 — ¿Qué significa exactamente `state=4`?

- **Pregunta:** decodificar el array raw `[4]` contra la versión exacta.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** `xdg_toplevel.state` en el XML local v7 y header generado.
- **URL/referencia:** `stable/xdg-shell/xdg-shell.xml:830–871`; tag oficial
  `1.49` indicado en D01.
- **Evidencia exacta:** `<entry name="activated" value="4" ...>`; la descripción
  dice que las decorations deberían pintarse como una window active y que no se
  debe asumir keyboard o pointer focus. `states` es un array de valores enum de
  32 bits, no un bitmask: `[4]` es el valor enum 4, no “bit 2”. El header
  generado contiene `XDG_TOPLEVEL_STATE_ACTIVATED = 4`.
- **Interpretación:** el segundo configure codifica el estado
  `activated`; no codifica por sí solo el motivo por el que el compositor lo
  envió.
- **Demuestra:** el valor enum y su semántica de decoración activada.
- **No demuestra:** que el usuario activó la ventana, que tenía focus de
  teclado o puntero, ni que hubiera un error, resize, maximización o
  fullscreen.
- **Limitaciones:** el estado es una hint de configuración; no es un evento de
  input focus.
- **Estado final:** `CONFIRMED`.

### H12-2-D04 — ¿Qué_semántica tiene `xdg_toplevel.configure`?

- **Pregunta:** qué solicita el evento, qué campos contiene y cuándo se aplica.
  A diferencia de `xdg_surface.configure`, `xdg_toplevel.configure` no tiene
  serial propio.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** XML xdg-shell local v7,Tag 1.49.
- **URL/referencia:** `xdg-shell.xml:1144–1172`; tag oficial D01.
- **Evidencia exacta:** el evento «asks the client to resize its toplevel
  surface or to change its state»; el estado no se aplica inmediatamente;
  width/height son hints; cero significa que el cliente decide la dimensión;
  los estados indican cómo interpretar width/height y, posiblemente, cómo
  dibujar.
- **Interpretación:** `640×360/[4]` es una configuración solicitada, no una
  medición de display ni una orden de resize obligatoria.
- **Demuestra:** el significado normativo de los campos del evento.
- **No demuestra:** que la superficie ya haya cambiado de tamaño, que el
  compositor haya dibujado un pixel, ni que H12 haya procesado un commit
  posterior.
- **Limitaciones:** el evento no incluye un timestamp ni un causal id del
  compositor.
- **Estado final:** `CONFIRMED`.

### H12-2-D05 — ¿Qué_semántica tiene `xdg_surface.configure`?

- **Pregunta:** entender la secuencia role-state → surface configure → commit.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** XML xdg-shell local v7, Tag 1.49.
- **URL/referencia:** `xdg-shell.xml:598–618`; tag oficial D01.
- **Evidencia exacta:** el evento marca el final de una secuencia de uno o más
  eventos; los eventos de role se latchean y el `xdg_surface.configure` final
  representa el conjunto atómico; el cliente debe adaptar la superficie, hacer
  ack y luego commitear.
- **Interpretación:** el serial 12837 identifica el final de la secuencia de
  configuración; no es por sí mismo una llamada a `wl_surface.commit`. El
  evento base no contiene width/height ni states; esos datos proceden del
  `xdg_toplevel.configure` latched inmediatamente antes.
- **Demuestra:** la atomicidad de la configuración pendiente y las obligaciones
  del cliente.
- **No demuestra:** que H12-2 haya sobrevivido o completado un commit WSI
  posterior con ese estado.
- **Limitaciones:** la aplicación guarda el estado raw y el ack, pero r3 corta
  antes de una nueva presentación que permita observar la aplicación posterior.
- **Estado final:** `CONFIRMED`.

### H12-2-D06 — ¿Cuáles son las reglas de `ack_configure`?

- **Pregunta:** ack inmediato,último serial, múltiples acks y commit.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** XML xdg-shell local v7, Tag 1.49.
- **URL/referencia:** `xdg-shell.xml:560–593`; tag oficial D01.
- **Evidencia exacta:** si el cliente commitea en respuesta, debe hacer ack
  antes del commit; si recibe varios configure antes de responder, puede ack
  solo el último; puede ack varias veces antes del próximo commit; el último
  ack antes del commit identifica la respuesta; ack old/duplicate genera
  `invalid_serial`.
- **Interpretación:** el `ack_configure_requested=true` de r3 prueba que H12
  generó el request para el serial recibido; no prueba por sí solo que el
  compositor recibiera el request o que un commit posterior completara el
  estado. En r3 el primer serial observado es 12832 y el segundo 12837, cada
  uno con su propio diagnóstico; no aparece un serial intermedio. El ack es un
  request xdg de configuración, no un "present acknowledgment" de Vulkan y no
  confirma que una imagen haya sido visible.
- **Demuestra:** la obligación de ack y la corrección formal de la secuencia.
- **No demuestra:** entrega, ack de peer o aplicación efectiva del estado.
- **Limitaciones:** no hay round-trip Wayland ni registro de compositor para
  el ack.
- **Estado final:** `CONFIRMED`.

### H12-2-D07 — ¿Puede haber varios configures?

- **Pregunta:** distinguir secuencia de configuración de evento único.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** XML xdg-shell local v7, Tag 1.49.
- **URL/referencia:** `xdg-shell.xml:598–616`, `1030–1051`; tag oficial D01.
- **Evidencia exacta:** «a set of one or more events»; el cliente puede
  descartar todos menos el último antes de responder; `set_maximized` dice que
  el compositor todavía emite configure si la superficie ya estaba maximizada;
  `xdg_toplevel.resize` documenta configures durante el resize y otro configure
  al finalizar, sin estado `resizing`.
- **Interpretación:** una secuencia puede contener más de un
  `xdg_surface.configure`; el segundo evento de r3 no es inválido por ser el
  segundo.
- **Demuestra:** que el protocolo no define “un configure y nunca más”.
- **No demuestra:** que r3 haya recibido varios configure sin responder, ni la
  causa del segundo.
- **Limitaciones:** la fuente de `set_maximized` es una operación de
  maximización; no convierte el estado observado en maximización.
- **Estado final:** `CONFIRMED`.

### H12-2-D08 — ¿Es un error/conflicto cualquier configure posterior al primer present?

- **Pregunta:** evaluar la regla anterior que abortaba todo configure
  post-present.
- **Estado anterior:** `CONFLICT` como regla de seguridad H12-1.
- **Fuente:** xdg-shell configure sequence y Vulkan Wayland WSI.
- **URL/referencia:** `xdg-shell.xml:598–618`, `1144–1172`;
  `Vulkan-Docs v1.4.341/chapters/VK_KHR_surface/wsi.adoc:226–261`.
- **Evidencia exacta:** el protocolo describe configures como secuencias de
  estado y no los limita al intervalo anterior al primer commit/present; la
  capa Vulkan puede recibir cambios de ventana y debe relacionarlos con presents
  futuros. No existe una regla xdg-shell que diga que todo configure recibido
  después de `vkQueuePresentKHR` sea un error. El serial 12837 tampoco es un
  frame number, timestamp ni prueba de que el compositor lo emitiera por el
  present.
- **Interpretación:** la regla absoluta era demasiado fuerte. Un configure
  post-present puede ser una configuración de estado válida; puede requerir
  reconfiguración si la evidencia muestra una geometría nueva, o puede ser otro
  evento de shell, pero la etiqueta `CONFLICT` de H12 era una safety policy.
- **Demuestra:** la ausencia de una prohibición normativa y la necesidad de
  clasificar por contenido, no solo por tiempo.
- **No demuestra:** que el evento concreto sea benigno, que el compositor no
  tenga un bug, ni que el swapchain siga siendo compatible después.
- **Limitaciones:** una implementación puede devolver `OUT_OF_DATE` o un error
  de Wayland en una llamada posterior; H12-2 no ejecutó la continuación.
- **Estado final:** `REFUTED`.

### H12-2-D09 — ¿Por qué apareció el segundo configure?

- **Pregunta:** identificar la causa del compositor, no sólo el enum recibido.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** r3 JSON, stderr y XML xdg-shell.
- **URL/referencia:** `h12-2-smoke-20260924-rx550-r3.jsonl`; XML D01–D07.
- **Evidencia exacta:** `toplevel_configure_seen_before_surface_configure=true`,
  `states=[4]`, mismo extent, `first_present_completed=true`; no hay
  compositor ID, causa, timestamp, `wl_display.error`, `xdg_toplevel.close`,
  cambio de output ni un request de maximización/fullscreen registrado.
- **Interpretación:** el estado observado es compatible con una actualización de
  activation, pero también con una respuesta de shell a otro cambio de estado
  que no se capturó. No se puede elegir una causa.
- **Demuestra:** únicamente el estado raw y el orden observado por el cliente.
- **No demuestra:** intención del compositor, error, resize real ni
  beneficiario para M1.
- **Limitaciones:** no se capturó el evento compositor que originó la secuencia,
  ni una traza de `wl_display` con tiempo de envío/recepción. Para r3 sí queda
  cerrada la existencia de un configure inicial previo: serial 12832,
  `initial_xdg_configure_completed=true` y swapchain posterior; lo que queda
  desconocido es la causa del segundo configure, no la ausencia del primero.
- **Estado final:** `UNKNOWN`.

### H12-2-D10 — ¿El segundo configure implicó un cambio de tamaño?

- **Pregunta:** separar hint de resize, estado de shell y resize del compositor.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** `xdg_toplevel.configure` y Wayland/Vulkan WSI.
- **URL/referencia:** `xdg-shell.xml:1144–1161`;
  `Vulkan-Docs v1.4.341/wsi.adoc:226–230, 6961–6999`.
- **Evidencia exacta:** r3 pasa de `surface_width=640,height=360` a
  `toplevel_width=640,height=360`; no hay un extent distinto. En Wayland,
  `currentExtent` es el valor especial y el `imageExtent` del swapchain
  determina el tamaño de ventana después del primer present.
- **Interpretación:** el evento no solicita un nuevo extent numérico. La
  ausencia de un extent distinto no prueba que ninguna operación interna del
  compositor haya cambiado la superficie; además, width/height de xdg están en
  coordenadas de window geometry y `imageExtent` está en píxeles, por lo que
  scale, transform y geometría efectiva pueden intervenir. Para cerrar esa
  diferencia haría falta evidencia de presentación/capabilities posterior.
- **Demuestra:** no hay evidencia de un cambio de tamaño codificado en el
  segundo configure.
- **No demuestra:** que no haya existido resize interno, scaling, output change
  o posterior out-of-date.
- **Limitaciones:** el probe abortó antes de una nueva consulta de capabilities
  y antes de un nuevo present.
- **Estado final:** `PARTIALLY CONFIRMED`.

### H12-2-D11 — ¿El estado 4 prueba focus, fullscreen, maximización o resize?

- **Pregunta:** evitar la equivalencia indebida entre el enum y sinónimos de UI.
- **Estado anterior:** `UNKNOWN`/`CONFLICT` por clasificación demasiado fuerte.
- **Fuente:** `xdg_toplevel.state` y `xdg_toplevel.configure`.
- **URL/referencia:** `xdg-shell.xml:839–871, 1144–1172`; tag oficial D01.
- **Evidencia exacta:** `maximized=1`, `fullscreen=2`, `resizing=3`,
  `activated=4`; el array r3 contiene únicamente `[4]`; la descripción de
  `activated` prohíbe asumir keyboard/pointer focus.
- **Interpretación:** r3 no codifica fullscreen, maximización ni `resizing`;
  codifica `activated`. La proposición “state=4 prueba cualquiera de los otros”
  es falsa.
- **Demuestra:** el valor y sus límites de interpretación.
- **No demuestra:** que no exista fullscreen/maximización en una capa externa,
  ni que la ventana no haya sido redibujada visualmente.
- **Limitaciones:** el array de estados no registra compositor policy,
  decorations, focus de seat ni visible pixels.
- **Estado final:** `REFUTED`.

### H12-2-D12 — ¿Quién hace `wl_surface.commit` en Vulkan Wayland?

- **Pregunta:** separar requests de la aplicación de la operación WSI.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** Vulkan WSI versionado y Mesa source-level.
- **URL/referencia:** `Vulkan-Docs v1.4.341/wsi.adoc:237–261`;
  `Mesa c5e4135.../src/vulkan/wsi/wsi_common_wayland.c:3180–3417`.
- **Evidencia exacta:** la especificación dice que `vkQueuePresentKHR` hace que
  Vulkan envíe `wl_surface.commit`; `attach`, `damage` y `commit` deben ser
  emitidos por la implementación durante `vkQueuePresentKHR` y no fuera de
  ella. También dice que los requests de cambios de ventana que deban
  sincronizarse con un frame se envían antes de `vkQueuePresentKHR`.
- **Interpretación:** H12-1 puede enviar `xdg_surface_ack_configure`,
  `xdg_surface.set_window_geometry` y `wl_surface.frame`, pero el
  attach/damage/commit del buffer presentable pertenece al WSI. El commit xdg
  inicial es un commit de aplicación previo y separado; una vez que la
  presentación WSI comenzó, el cliente no debe duplicar el commit del buffer.
  El modo FIFO puede retrasar la actualización visual, pero no convierte el
  commit de protocolo WSI en un commit que la aplicación deba emitir fuera de
  `vkQueuePresentKHR`. El `wl_surface.frame` sigue siendo sólo un callback de
  compositor.
- **Demuestra:** ownership y orden normativo de la presentación.
- **No demuestra:** que el callback de frame sea vblank, first pixel o que el
  pixel se haya mostrado.
- **Limitaciones:** la regla es spec/API; la implementación Mesa local sólo es
  corroboración source-level y no prueba el ICD runtime exacto.
- **Estado final:** `CONFIRMED`.

### H12-2-D13 — ¿Cuándo se necesita recrear el swapchain?

- **Pregunta:** distinguir cambio de estado, cambio de extent y error WSI.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** Vulkan WSI versionado.
- **URL/referencia:** `Vulkan-Docs v1.4.341/wsi.adoc:6961–6999, 7150–7181`;
  `VkSurfaceCapabilitiesKHR` y `VK_KHR_swapchain` oficiales enlazados desde esa
  especificación.
- **Evidencia exacta:** `VK_SUBOPTIMAL_KHR` significa que el swapchain ya no
  coincide exactamente pero todavía puede presentar; la especificación base
  permite decidir si se continúa o se recrea, mientras que la resolución del
  issue 9 de `VK_KHR_swapchain` recomienda consultar y recrear en la próxima
  oportunidad conveniente. `VK_ERROR_OUT_OF_DATE_KHR` significa que la surface
  ya no es compatible y la aplicación debe consultar propiedades nuevas y
  recrear si desea continuar. El resultado puede venir de acquire o present;
  en Wayland `currentExtent` es especial.
- **Interpretación:** un `activated=4` con extent 640×360 no exige por sí solo
  recrear. Un extent/configuración incompatible, `OUT_OF_DATE`, o una decisión
  de adaptación tras `SUBOPTIMAL` sí puede exigir o justificar recreación. En
  Wayland, `currentExtent` es un valor especial y no debe interpretarse como
  `640×360`. `oldSwapchain` no es una sustitución atómica: el swapchain viejo
  se retira incluso si la creación del nuevo falla. r3 terminó antes de probar
  el siguiente present.
- **Demuestra:** la regla de manejo de resultados y la distinción entre
  suboptimal y out-of-date.
- **No demuestra:** que el swapchain de r3 hubiera permanecido óptimo, ni que
  el compositor no hubiera enviado otro configure.
- **Limitaciones:** H12-2 no consultó capabilities después del segundo
  configure; `swapchain_suboptimal_observed=false` sólo describe los returns
  observados hasta el abort.
- **Estado final:** `PARTIALLY CONFIRMED`.

### H12-2-D14 — ¿Qué cambiaron r1, r2 y r3?

- **Pregunta:** preservar la evolución de la instrumentación y del cleanup.
- **Estado anterior:** evidencia dispersa y cleanup no documentado.
- **Fuente:** los tres JSONL y stderr bajo `/tmp/opencode/`.
- **URL/referencia:** hashes y rutas listados en §2.5.
- **Evidencia exacta:** r1 carece de summary/cleanup; r2 añade error estructurado
  y summary pero `NOT_STARTED`; r3 añade raw toplevel state/dimensions, serial,
  `ack_configure_requested` y cleanup `COMPLETED`.
- **Interpretación:** r3 mejora la evidencia de seguridad, pero conserva la
  clasificación histórica `POST_PRESENT_CONFIGURE_UNCLASSIFIED`; no se
  reescribe r1/r2 ni se convierte r3 en una clasificación causal.
- **Demuestra:** el progreso de logging y la	finalización de cleanup de r3.
- **No demuestra:** que r1 haya dejado procesos o recursos activos; sólo que
  su artefacto no lo certifica.
- **Limitaciones:** no hay manifest de invocación que asocie cada log a un hash
  de binario; la temporally build/source se documenta como consistencia, no como
  prueba criptográfica de provenance.
- **Estado final:** `PARTIALLY CONFIRMED`.

### H12-2-D15 — ¿H12-2 cerró la hipótesis causal H12?

- **Pregunta:** separar la auditoría de capacidad del bottleneck causal.
- **Estado anterior:** `UNKNOWN`.
- **Fuente:** metadata r3, H12-1 README y Vulkan WSI.
- **URL/referencia:** r3 JSONL; `HYPOTHESIS-REGISTER.md` H12;
  Vulkan WSI D12–D13.
- **Evidencia exacta:** se confirmaron target, queue family 0, FIFO, 3 images,
  640×360, timestamp query y calibrated timestamps; no están disponibles
  Present-ID2, present timing o Present-Wait2, y first pixel/vblank/display
  latency no fueron entregados.
- **Interpretación:** la capa de capacidad WSI está parcialmente auditada y la
  semántica xdg del segundo configure está documentada. No se separó GPU
  completion de presentation/VSync para M1; `wl_surface.frame` no llena ese
  hueco.
- **Demuestra:** qué capacidades y telemetrías están disponibles.
- **No demuestra:** que M1 sea VSync-limited, GPU-limited o WSI-limited.
- **Limitaciones:** el contexto operativo del proyecto registra que el output
  RX550 estaba desconectado; no se reconstruyó una campaña ni se midió first
  pixel.
- **Estado final:** `PARTIALLY CONFIRMED`.

## 5. Corrección documental que puede aplicarse después

La evidencia permite una corrección de protocolo **para una futura revisión de
código**, pero no se autoriza aquí a cambiar código ni ejecutar H12:

1. No abortar automáticamente sólo porque un `xdg_surface.configure` fue
   observado después del primer `vkQueuePresentKHR`.
2. Decodificar `states` contra el XML exacto; no tratar `4` como resize,
   fullscreen, maximización, focus o error.
3. Si el estado raw es exactamente `[ACTIVATED=4]`, el extent raw coincide con
   el extent activo, el configure del role precede inmediatamente al configure
   de la surface y no hay una operación WSI crítica en curso, se puede
   considerar un camino state-only para revisión estática. Esto no demuestra que
   el compositor haya permanecido en activated ni que el próximo present sea
   seguro.
4. Mantener safety hold para extent incompatible, estado desconocido/truncado,
   combinaciones de estados, configure durante una operación WSI, o cuando no
   se pueda probar la continuación. La safety hold debe describirse como
   política de la aplicación, no como error del compositor.
5. ACK cada configure según las reglas de serial; no inventar un
   `wl_surface.attach`/`damage`/`commit` de aplicación para el WSI. La
   aplicación debe hacer ack y mantener los requests de sincronización antes de
   la llamada present en la que el WSI emite su commit.
6. Recreate del swapchain sólo por evidencia de extent/capabilities/present
   result que lo requiera; no por el hecho temporal de un configure state-only.
7. Antes de cualquier nueva ejecución, registrar versión de `xdg_wm_base`,
   hash del XML, hash del binario, negotiated `wl_compositor` version, raw
   `xdg_toplevel` state/dimensions, resultado de `vkQueuePresentKHR` y una
   nueva consulta de capabilities después del evento.

El source working tree contiene un borrador no ejecutado de la clasificación
`POST_PRESENT_STATE_ONLY_CONFIGURE`; su mtime es posterior al binario/log de r3.
Este informe no lo trata como evidencia runtime. La fuente canónica del
comportamiento observado continúa siendo el JSONL r3 con
`POST_PRESENT_CONFIGURE_UNCLASSIFIED`.

## 6. Restricciones y límites finales

- En esta actualización documental no se editó deliberadamente código, Mesa,
  kernel, firmware, VBIOS, DPM, power cap, PM, ASPM ni servicios. El source
  working tree ya contiene/continúa conteniendo un borrador no ejecutado; no se
  presenta como cambio autorizado por este informe.
- No se ejecutó H12, H12-1, un benchmark o una campaña posterior.
- No se usaron `power1_input`, `mem_busy_percent`, `wl_surface.frame` o un
  callback como sustitutos de wattmeter, bandwidth, vblank o first pixel.
- `state=4` sólo pasó de `UNKNOWN` a `CONFIRMED` como valor enum
  `activated`; no se promovió a causalidad.
- La incompatibilidad runtime del swapchain después del segundo configure es
  `UNKNOWN` hasta que exista una continuación autorizada y evidencia de
  acquire/present/capabilities.

## 7. Referencias primarias consolidadas

1. xdg-shell 1.49 local y tag:
   `https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/1.49/stable/xdg-shell/xdg-shell.xml`
2. Wayland core 1.25.0 local y tag:
   `https://gitlab.freedesktop.org/wayland/wayland/-/blob/1.25.0/protocol/wayland.xml`
3. Vulkan WSI, tag 1.4.341:
   `https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.341/chapters/VK_KHR_surface/wsi.adoc`
4. Vulkan Wayland WSI navigable:
   `https://docs.vulkan.org/spec/latest/chapters/VK_KHR_surface/wsi.html#platformCreateSurface_wayland`
5. Mesa source-level Wayland WSI:
   `https://github.com/mesa3d/mesa/blob/c5e413533f461cffb98150c9d91908ea1911c589/src/vulkan/wsi/wsi_common_wayland.c`
6. H12-2 artefactos locales y hashes: §2.5 de este documento.
