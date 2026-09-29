# Research Log — CIERRE 2026-09-19

> **Reconciliación terminológica 2026-09-24:** las menciones históricas a `draw` se
> interpretan como `W_SMU` cuando provienen de `power1_input`; no implican vatímetro.
Bitácora consolidada final.

> **Nota de trazabilidad (reorganización 2026-09-23):** las rutas `experiments/...` de
> las entradas históricas conservan el estado PRE-REORGANIZACIÓN. Las entradas actuales
> de este log usan los localizadores canónicos `03-EXPERIMENTOS/`.

## 2026-09-17 — Sesión histórica (origen de datos NO reproducibles)
- E1 `mesa-e1-20260917-170430`, E3 `mesa-e3-20260917-213646` (+E4, E5 dentro). Régimen: power1 plano == cap
  25 W, SCLK 330-390, MCLK ~1250-1500, 74-92 °C, FPS altos (phong 1285, desktop 443@1080). Mesa CUSTOM
  `/opt/mesa-26.2.2-rx550-haswell`. kalm sin eventos ese día. **Este régimen NO se ha reproducido después.**
- Backup: `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`.

## 2026-09-18 — Kalm crash y sweep
- 14:05 `rx550-power-sweep-20260918-140527`: cap 25/35, régimen libre (1071/9-10 W) con kalm real activo.
- 08:17 kalm-gpu.service (systemd) muere (`Errno 16` busy al leer power1_cap_max); el kalm real (kalmd.py/
  kalm-lite.py) sigue vivo. Resultados: cap no liga; results.csv tiene columnas desalineadas (solo raw válido).

## 2026-09-19 — Sesión de reproducción y cierre
- **Fase A** (`fase-a-discriminacion-20260919-114241/`): read-only. 3 GL + 3 VK phong + 3 VK default válidas.
  Invalidadas corriidas 04-09 (cataron iGPU Intel - `INVALIDACION-corridas-04-09.md`). Base: 1071/10.5 W/
  42-48 °C. GL jelly 640p 1169-1237; VK phong 396-400; VK default 403.
- **Fase B** (`fase-b-cap-probe-20260919-122038/`, autorizada writes de cap): 28 runs, curva plana
  (25-35 W → 1071/10.5-11.6 W). **El régimen E1/E3 no reaparece ni con cap 25 W.**
- **EP-08**: E1/E3 muestrearon la RX 550 real (header vram/gtt = amdgpu). Runner E1 ausente en backup.
- **EP-06** (`ep06-soak-cap-20260919-205645/`, autorizada cap writes con condición display): soak 7 min y
  pesado → max 13.6 W/67 °C. Réplica E1 a 70-71 °C cap 25 W → SCLK 1071/10-11.5 W, sin pinzado. kalm
  descartado (journal). Máximo W_SMU: 13.6 W.
- **EP-05** (`ep05-mesa-custom-20260919-212249/`, read-only): A/B CUSTOM vs STOCK a 1080p, N=2, desde frío.
  CUSTOM==STOCK (FPS 73-203; 1071/625/9-12.2 W/48-58 °C). Libs verificadas por /proc maps. CUSTOM no
  reproduce el régimen de E5. VK sin selector → iGPU (registrado).
- **CIERRE**: especificación `RX550_BUILD_SPECIFICATION.txt`, `README.md`, `FINAL-RESEARCH-STATUS.md`
  y este conjunto de 8 archivos. No se ejecutaron más experimentos (instrucción).

## Estado final del sistema tras EP-05/cierre [VERIFICADO]
- power1_cap = 35 000 000; DPM=auto; temp ~45-47 °C; kalm real intacto (no tocado); display en Intel
  (card0, i915); sin writes sysfs pendientes; Mesa del sistema sin cambios.

## 2026-09-20 — M1 (cap sostenido 35/30 W) [COMPLETADO]
- Runner `rx550-torneo m1-schedule` (congelado durante el run). `03-EXPERIMENTOS/M1-cap-35-30/runs/20260919-235939`.
- **10/10 corridas OK**, 5×35 W + 5×30 W; SET/readback y RESTORE/readback final correctos; aux sin cambios;
  sin ERROR/CRITICAL/reset/hang; `workload_rc=0`; temp máx 52 °C (< 90 °C).
- `media(power1_input @35 W)` = **12.27 W** < 27 W → compuerta activada → **NO DISCRIMINATIVO**
  (el cap no liga con `vkmark shading:phong` 1080p). ΔFPS = [0,0,0,0,0]; ΔSCLK = [0,0,0,0,0].
- Anomalía: bloque 5 FPS 74→71 en ambos brazos (simétrico, no diferencial del cap).
- HOME/XDG corregido: `stderr` vacío en las 10 corridas (sin error de Mesa shader cache).
- Resultado detallado y hashes: `03-EXPERIMENTOS/M1-cap-35-30/RESULTADOS-M1.md`.
- "NO DISCRIMINATIVO" ≠ "30 W = 35 W para cualquier workload": este workload no alcanzó demanda
  suficiente para que el cap pudiera ligar. No se ejecutan más experimentos.

## 2026-09-28 — Carril A (RE) + Carril B (camino mínimo) [DOCUMENTADO, NADA EJECUTADO]

- **Objeto**: dos carriles separados. RE (semántica GFX8/Polaris12) y camino mínimo de
  ejecución sin DISPLAY/KMS. Sin ejecutar nada y sin modificar el sistema.
- **Resultado**: 10 hechos nuevos (`OBSERVED`/`FACT_FOR_7.1.3`) en `RESEARCH-LINES.md` §16.1.
  Los tres con más peso:
  1. **A-4** el GART de Polaris12 es una apertura **dentro de VRAM** alcanzada por PCIe, no
     system memory (`gmc_v8_0.c:829` aborta sin `adev->gart.bo`, que es un BO de VRAM).
     Cambia el modelo de RE-05, de RE-02 y de L3.
  2. **A-5** el driver habilita **ocho** canales `*_PROTECTION_FAULT_ENABLE_DEFAULT`, uno de
     ellos `EXECUTE_…`, **distinto** de `READ_…` y `WRITE_…` (`gmc_v8_0.c:926-931`). Acota
     RE-01/RE-04; **no** prueba la arista `PTE_EXEC → command fetch`, que es N2.
  3. **A-2/A-3** `asic_reg/gca/gfx_8_0_enum.h` tiene 1448 enumeraciones semánticas de campos
     de registro, pero **0** de paquetes PM4.
- **Carril B**: por observación, esta RX550 **ya ejecuta trabajo GPU sin CRTC** y sin salida
  conectada (los 3 conectores de `card1` están `disconnected`, el log dice `Cannot find any
  crtc or sizes`, y `renderD129` existe en modo `crw-rw-rw-`). DCE queda `DISPLAY_ONLY`. Lo
  que **no** puede afirmarse es que la inicialización de DCE sea eliminable, porque
  `amdgpu_drm_probe` **no está en ninguno de los dos árboles** (`SOURCE_UNAVAILABLE` con
  alcance nombrado). `CANDIDATE_FOR_REMOVAL`, no `MANDATORY_NOT_NEEDED`.
- **E1/E2**: no tocados. `B-09` y `B-02-bis` siguen `BLOCKED`; no se sorteó ninguno.
- **Correcciones propias registradas** (§16.5 y §15.10):
  - §15.2 decía «la semántica no está en el material». Demasiado amplio: es falso para
    `asic_reg/gca`. Corregido.
  - La fila `B-08` de §8 conservaba la causa «D3hot» que §6 ya había refutado. §6 y §8
    contradecían. Alineadas.
  - `INTERPRETATION_ERROR` (defecto #13): encadené `grep … | head -4` y leí el truncamiento
    como ausencia. `PCIE GART` **sí** está en `gmc_v8_0.c:942`. Es la **misma clase** que el
    defecto #8 (token literal `INDIRECT_BUFFER`), luego es `PATTERN`, no error aislado. Regla
    reforzada: nunca acortar la salida de un `grep` antes de contar sus coincidencias.
- **`KNOWN-LIMITATIONS.md` y `DEVELOPMENT-LOG.md` no existen** y nunca existieron: 0 en
  `git log --all`, 0 en `git ls-files`, 0 en el censo documental, 0 en el router. Lo que
  existe es el campo `KNOWN_LIMITATIONS` por registro en
  `01-AUDITORIA/R1-TECHNICAL-SEMANTIC-MODEL-V2-20260926.md`, y esta entrada vive aquí.
  **No se creó ningún fichero nuevo** (§16.0).

## 2026-09-28 — Ronda de firmware GFX/Polaris12 [DOCUMENTADO, NADA EJECUTADO]

- **Objeto único**: firmware GFX en el host, correlacionado con RE-06, RE-10 y N2.
  Lectura y forense. Sin `sudo`, sin sysfs, sin módulos, sin E1/E2, sin `B-09`, sin
  `B-02-bis`.
- **Método**: layout del header demostrado **primero desde fuente**
  (`amdgpu_ucode.h:30-41` y `:181-186`), verificado **byte a byte idéntico** entre el
  baseline 7.1.3 y el árbol 7.2.8, y **después** aplicado al binario con autovalidación.
  Herramienta en C (`AGENTS.md` §13.8), read-only, con control negativo ejecutado.
- **Resultado principal**: `/lib/firmware/amdgpu/` tiene 677 ficheros, **todos `.xz`**; 20
  con prefijo `polaris12`. Los 11 GFX están declarados en `MODULE_FIRMWARE` de
  `gfx_v8_0.c` y coinciden uno a uno con el inventario. `chip_name = "polaris12"` para
  `CHIP_POLARIS12` (`gfx_v8_0.c:973-974`).
- **`ucode_feature_version` de esta pieza**: PFP `46` (base) / `49` (`_2`); CE `46` / `49`;
  ME `46` / `49`; MEC y MEC2 `46` / `49`. **`>= 46` se cumple con las dos variantes**, así
  que la elección `_2` frente a base **no es discriminante**. El kernel actual imprimió
  `Chained IB support enabled!`, línea que sólo existe dentro del
  `if (ce_fv >= 46 && pfp_fv >= 46)`.
- **Lo que NO se escribe**: «el firmware usado es X». `REQUESTED` queda `DERIVATION` y
  `USED` queda `UNKNOWN`; el log no nombra los ficheros GFX cargados.
- **RE-06** → `PARTIALLY_RESOLVED` (se cierra la mitad del driver; la del hardware no).
- **RE-10** → `PARTIALLY_RESOLVED`: demostrada la cadena firmware→driver→característica
  (capas 1–2–3). **La capa 4, «el hardware implementa la característica», sigue
  `UNKNOWN`** y no se avanza.
- **N2**: `UNKNOWN_FROM_TREE`, sin cambio. El firmware no aporta ningún discriminante. El
  valor 49 es un número de ucode, no una afirmación sobre permisos de lectura de memoria.
- **RE-05**: intacto. El GART sigue siendo apertura de VRAM por PCIe; el firmware no lo
  toca.
- **Defectos propios** (§17.10): (a) afirmé que los ficheros de 20-22 B eran placeholders
  vacíos — **falso**, descomprimen a 262-375 KB; (b) **bug en la herramienta de offsets**:
  leí `ucode_version` con 16 bits siendo el campo de 32, y en estos ficheros el valor
  cabía, así que el error era invisible; corregido antes de emitir resultados.
- **Descubrimiento adversarial que más pesa**: `polaris10`, `polaris11` y `polaris12`
  declaran **el mismo** `ip=8.0`, `ucode_version=254` y `feature=49`, y difieren **sólo en
  `crc32``. **El header no identifica el ASIC**; el único vínculo fichero→ASIC es el nombre
  vía `chip_name`. Por tanto `feature=49` es un valor de la familia GFX 8.0, no un dato
  de este silicio.

## 2026-09-28 — Cierre de REQUESTED + CPU_MODEL_CLASS_ATTRIBUTION [DOCUMENTADO, NADA EJECUTADO]

- **REQUESTED → `DERIVATION_ONLY`** (no `PROVEN`, no `NOT_AVAILABLE_BY_PERMISSION`).
  Se encontró evidencia **negativa discriminante**: `amdgpu_ucode_request`
  (`amdgpu_ucode.c:1521-1522`) imprime el nombre del firmware **sólo si la petición
  opcional falla**. Las 5 peticiones `OPTIONAL` son exactamente las 5 variantes `_2`
  (parseo exhaustivo: 16 peticiones, 5 OPTIONAL, 11 REQUIRED). El log del boot actual
  **empieza en la primera línea del kernel**, tiene 1144 líneas, **0** apariciones de
  `Optional firmware` y **0** descartes de printk. Luego el fallback no se tomó y la
  variante resuelta fue la `_2` para las cinco familias.
  **Lo que no es**: un registro positivo del nombre. El estado no sube a `PROVEN` porque la
  única interfaz que lo daría, `amdgpu_firmware_info`, es debugfs `NOT_AVAILABLE_BY_PERMISSION`
  y no se hizo bypass. `PRESENT = REQUESTED` no se usó como prueba, y
  `feature_version` tampoco.
- **RE-06** sigue `PARTIALLY_RESOLVED` (la conclusión `>= 46` es inmune a la ambigüedad:
  base 46 y `_2` 49, ambos cumplen). **RE-10** sin cambio: capas 1-3 `PROVEN`, capa 4
  `UNKNOWN`. **N2** `UNKNOWN_FROM_TREE`, sin cambio.
- **CPU_MODEL_CLASS_ATTRIBUTION**: `CPUID(1).EAX = 0x000306C3` (family 6, model 0x3C,
  stepping 3) verificado directamente y contrastado con `/proc/cpuinfo`. 4 núcleos / 8
  hilos. microcode `0x28`. **`CPUID(0xD,0).EAX = 0x7` = soporte x87+SSE+AVX;
  `XGETBV(0) = 0x7` = estado real idéntico; sin AVX-512.** Sin hypervisor, por dos
  fuentes independientes: `CPUID(0x40000000).eax = 0x7` (leaf ausente) y ausencia del flag
  `hypervisor` en `/proc/cpuinfo`.
- **Tres correcciones a premisas de la ronda**: `-march=haswell`, `-mtune=haswell`, el
  rechazo de `native`, `x86-64-v4` y `SIGILL` tienen **0 ocurrencias** en el corpus del
  proyecto. Se reetiquetan como `NOT_FOUND` y se conserva la decisión de target como
  `MODEL_CHOICE` razonada, no como hecho heredado. La incompatibilidad de `x86-64-v4` se
  sostiene como `DERIVATION` de la matriz ISA (v4 exige AVX-512, esta CPU no lo tiene), y
  **no** como `SIGILL` observado, porque no se observó ninguno.
- **Error de alcance propio que casi fue una regresión**: 166 líneas con `-march=`/
  `-mtune=` en todo el repo son los Makefiles **del propio kernel**
  (`RESEARCH/kernelbuild/.../arch/x86/Makefile`), no decisiones del proyecto; con alcance
  de proyecto son **0**. Casi registré «el proyecto usa `-march=native`».
- **Tercer bug de instrumento en dos rondas**: el lector de CPUID decodificaba los bits de
  XCR0 desde `EBX` en vez de `EAX`, e imprimió `eax=0x7` junto a `x87=0 SSE=0 AVX=0` —
  contradicción visible. Corregido antes de usar ningún valor. Los tres bugs previos fueron
  `rd16` sobre un campo `uint32`, `grep | head` leído como ausencia, y éste.

## 2026-09-28 — Discriminante DMI [DOCUMENTADO, NADA EJECUTADO]

- **Alcance**: sólo lectura de `/sys/class/dmi/id/`, `/sys/firmware/dmi/tables/` y
  `/sys/firmware/dmi/entries/`. Sin `sudo`, sin MSR, sin experimento, sin tocar sistema,
  código, firmware ni configuración. RX550, firmware, RE-06, RE-10 y N2 no reabiertos.
- **Corrección de partida, la más importante**: **`IDENTIFICACION.md` no existe**, y
  `MEASUREMENT_ENTITY`, `OBSERVED_PLACEMENT`, `HARDWARE_INSTANCE`, `PORT_BOUND` y
  `CPU_MODEL_CLASS_ATTRIBUTION` **no están definidos por el proyecto**: sus únicas
  apariciones en las 401 fichas `.md` están en mi §18 de la ronda anterior.
  `INSTANCE_ANCHORED` aparece **1 vez en todo el corpus** y es una etiqueta que propuse yo.
  Conforme a la instrucción, **no se modifica ningún estado formal** y no se inventa el
  destino: se registra la capacidad de la evidencia.
- **DMI completo y real**: `sys_vendor` ECS · `product_name` H81H3-M4 · `board_name`
  H81H3-M4 · `board_vendor` ECS · `bios_vendor` American Megatrends Inc. · `bios_version`
  4.6.5 · `bios_date` 05/21/2015 · `chassis_type` 3. Sin marcadores de relleno en los 8
  campos pedidos.
- **Lo que cierra la instancia, no**: `product_serial`, `board_serial`, `chassis_serial` y
  `product_uuid` son **`EACCES` en `-r-------- root:root`**. La vista SMBIOS cruda
  (`tables/DMI` 2970 B, `smbios_entry_point` 31 B y los 6 atributos de las **77** entradas
  de `entries/`) está **también** cerrada por permisos. No se hizo bypass.
- **Resultado**: `HARDWARE_INSTANCE` **sigue `PARTIAL`**. DMI ancla a una **plataforma**
  (fabricante, modelo de producto y placa, BIOS y fecha), que es un *modelo de placa*, no
  una *unidad*. El identificador de instancia es exactamente el campo que sysfs restringe.
  `SILICON_INSTANCE_ATTRIBUTION` sigue `NOT_READY`: DMI no declara CPU alguna.
- **Anclaje CPU→plataforma**: `CPUID(1).EAX = 0x000306C3` (family 6, model 0x3C, stepping 3)
  + 1 physical id / 4 core id / 8 lógicos / microcode 0x28 → plataforma ECS H81H3-M4 con
  BIOS AMI 4.6.5 de 2015. **Coherente** con Haswell, pero sólo `CONSISTENT`: DMI no declara
  la CPU, así que no corrobora la atribución.
- **Provenance**: los valores DMI son `PLATFORM_DECLARED`, no `MEASURED`. Que sysfs los
  exponga no añade independencia: es un eco de lo que declara la propia placa.
- **Defecto propio**: el control adversarial 3 (marcadores de relleno) lo pasé primero
  **sólo sobre los 8 campos pedidos** y devolvió 0. Al ensanchar al conjunto completo
  aparecieron **2**: `product_sku` y `chassis_asset_tag`, ambos `To be filled by O.E.M.`.
  Ámbito de control demasiado estrecho; corregido en §19.7.

## 2026-09-28 — RE-01 (RX550): corrección de falso negativo y apertura del camino de probe

- **Corrección de una afirmación propia previa**: §16.3 declaraba que `amdgpu_probe` /
  `amdgpu_drm_probe` no estaban en ningún árbol y que por eso las etapas «DRM device» y
  «amdgpu probe» **no eran trazables desde fuente**. **Era un falso negativo mío.** En esta
  versión el punto de entrada es **`amdgpu_pci_probe`**, definido en `amdgpu_drv.c:2364` y
  registrado en `:3138` como `.probe` del `pci_driver`. `amdgpu_main.c` no existe, y da igual.
  La causa fue buscar por los nombres de función que yo esperaba en vez de seguir el puntero
  que el código declara. Segunda vez en esta sesión que un `NOT_FOUND` mío es fallo de
  método y no de dato. El `LIMITATION` de §16.3 queda revocado.
- **Secuencia real trazada**: `amdgpu_pci_probe` → `amdgpu_driver_load_kms`
  (`amdgpu_kms.c:135`) → `amdgpu_device_init` (`amdgpu_device.c:3679`, 467 líneas) →
  `drm_dev_register` (`amdgpu_drv.c:2435`). **Derivación**: el nodo DRM **no existe** mientras
  se inicializa VRAM/GEM/TTM/GPUVM/rings/firmware.
- **Cruce con B-08-bis**: `amdgpu_set_init_level(adev, AMDGPU_INIT_LEVEL_DEFAULT)` está en
  `amdgpu_device.c:3859`, antes de `drm_dev_register`. Eso sitúa el punto de setting del
  `!full_init` que §6 dejó abierto, aunque **no** lo excluye: la función también puede
  bajarlo después, en rutas no trazadas. El `UNKNOWN` se mantiene con motivo más preciso.
- **No hecho, y dicho**: no se trazó el interior de `amdgpu_device_ip_early_init`, que es
  donde ocurre el grueso (discovery, firmware, VRAM, GEM/TTM, GPUVM, rings, PM4, scheduler).
  La ronda cierra el `LIMITATION`, no el mapa completo.
- **Defecto ajeno visible**: §20 (línea paralela, CPU/Haswell) tiene 2 caracteres CJK
  corruptos y 38 filas de tabla sin estructura. **No se ha tocado**: es contenido de otra
  línea y la misión prohíbe modificarlo. Se reporta.

## 2026-09-28 — RE-02 (RX550): trazado de amdgpu_device_ip_early_init()

- **Localización**: `amdgpu_device.c:1926-2115`, `static`, 190 líneas, **un solo caller**
  (`:3861`, dentro de `amdgpu_device_init`).
- **Clasificación §13 = C (combinación)**: construye la lista **y** ejecuta los callbacks.
  `vi_set_ip_blocks` construye; `->early_init(ip_block)` en `:2044` ejecuta, dentro del
  bucle `:2036-2058`, asignando `status.valid`.
- **Polaris12**: `switch (asic_type)` `:1946` → `case CHIP_POLARIS12:` `:1980` →
  `family = AMDGPU_FAMILY_VI` `:1986` → `vi_set_ip_blocks` `:1989` → `vi.c:2109` → 9
  `amdgpu_device_ip_block_add()`.
- **Cruce con el host, y es el resultado de fuerza de la ronda**: la lista **estática**
  (`vi.c:2110-2123`) coincide bloque a bloque, en orden y con las mismas versiones, con los
  9 bloques que el log del kernel reporta. Queda confirmado que `dm_ip_block` **sí** se
  añadió en este host.
- **Control 2 ejecutado, y no fue gratis**: `gmc_v8_0_early_init` **no** inicializa
  VRAM. Su cuerpo contiene `amdgpu_irq_get`, `VGA_CONTROL`, `AMDGPU_VM_FAULT_STOP_ALWAYS`,
  `REG_GET_FIELD`/`RREG`; no contiene `amdgpu_bo_init` ni `amdgpu_vm_manager_init`.
  VRAM/GEM/TTM (`gmc_v8_0.c:1154`) y GPUVM (`gmc_v8_0.c:1169`) están en **`sw_init`**
  (`gmc_v8_0_sw_init:1094`), no en `early_init`.
- **Orden de fases** dentro de `device_init`: `:3861` early_init → **`:4017`
  `drm_mode_config_init`** → `:4019` `amdgpu_device_ip_init` (sw_init) → `:4058` late_init.
- **Resultado honesto**: la función trazada es la **cabeza** del camino, no su cuerpo. 6 de
  13 etapas quedan `UNKNOWN` o `PARTIALLY_TRACED` (ucodes GFX, rings, PM4, fence, scheduler,
  workload).
- **Dos autocorrecciones**: (a) dije «no inicializa, sólo construye» — falso, `->early_init`
  está en `:2044`, dentro de su rango; detectado al localizar la función contenedora de la
  llamada. (b) atribuí `amdgpu_bo_init`/`amdgpu_vm_manager_init` a `gmc_v8_0_sw_init` con una
  ventana de 30 líneas insuficiente; la función contenedora real confirma la atribución.
  Segunda ocurrencia del método «conclusión provisional desde una ventana de lectura
  insuficiente» (§21 fue la primera).
- **No contestado**: si el bloque de display es eliminable; cuánta generalidad del `case`
  compartido con POLARIS10/11/VEGAM es necesaria para este RX550.

## 2026-09-28 — RE-02 (RX550): amdgpu_device_ip_init -> GMC -> GFX -> rings -> scheduler

- **Estructura de `amdgpu_device_ip_init` (`amdgpu_device.c:2299-2477`)**: un solo bucle
  (`:2308-2383`) con **dos** ramas que ejecutan `hw_init` dentro de el, para `COMMON`
  (`:2329`) y `GMC` (`:2349`). Tras el bucle: `ib_pool_init` `:2388`,
  `ucode_create_bo` `:2395`, `hw_init_phase1` `:2399`, `fw_loading` `:2403`,
  `hw_init_phase2` `:2407`, `ras_recovery_init` `:2427`, `init_schedulers` `:2459`.
- **Cadena pedida, completa**: `gmc_v8_0_sw_init` `:1094-1187` contiene, en orden,
  `gmc_v8_0_init_microcode` `:1143` -> `gmc_v8_0_mc_init` `:1149` ->
  **`amdgpu_bo_init` `:1154`** -> **`gmc_v8_0_gart_init` `:1158`** ->
  `first_kfd_vmid = 8` `:1168` -> **`amdgpu_vm_manager_init` `:1169`**.
  **`FACT`: `gmc_v8_0_sw_init` no escribe ni un registro.**
- **`amdgpu_bo_init` (`amdgpu_object.c:1058-1082`)**: MTRR/PAT (`:1063`, `:1072`), dos
  `drm_info` (`:1076`, `:1079`) y `return amdgpu_ttm_init(adev)` (`:1081`). **No**
  demuestra GEM, **no** crea BOs, **no** reserva VRAM. `amdgpu_ttm_init`
  (`amdgpu_ttm.c:2066-2227`) es donde están los heaps: VRAM `:2096`, GTT `:2155`, pools
  on-chip, doorbells, `ioremap_wc` `:2116`. Todo software.
- **GART (regla 7)**: `gmc_v8_0_gart_init:948-963` son 16 líneas, 0 WREG. Crea
  `gart.bo` + `gart.ptr` como **BO en `AMDGPU_GEM_DOMAIN_VRAM`** (`amdgpu_gart.c:271`) y
  hace `memset_io` de todo el tamaño con `AMDGPU_PTE_EXECUTABLE` (`gmc_v8_0.c:961`).
- **RE-05 cerrado con linea exacta**: `gmc_v8_0_gart_enable:942-944` es el origen del log
  del host `"PCIE GART of %uM enabled"`, con `table_addr = amdgpu_bo_gpu_offset(
  adev->gart.bo)` en `:840`; y el `256M` viene de `gmc_v8_0.c:592-595`
  (`case CHIP_POLARIS12: gart_size = 256ULL << 20`). `gmc_v8_0_gart_enable` tiene
  **21 WREG / 7 RREG**.
- **GPUVM (regla 8)**: `amdgpu_vm_manager_init` (`amdgpu_vm.c:2868-2902`) es 100 % software.
  VMID: `amdgpu_ids.c:574-603`, con `num_ids = first_kfd_vmid = 8` para GC < 10.0.0 y bucle
  `j = 1..7` -> **VMID 1 a 7**, coherente con el comentario `gmc_v8_0.c:1163-1167`.
- **GMC sw/hw/fw (regla 9)**: `gmc_v8_0_hw_init` (`:1203-1236`) = `init_golden_registers`
  `:1208` (sw) + `mc_program` `:1210` (hw) + `gmc_v8_0_polaris_mc_load_microcode` `:1221`
  (**fw a hw**, y `:1220` es exactamente `CHIP_POLARIS12`) + `gart_enable` `:1228` (hw).
  **El paso software->hardware ocurre en la MISMA vuelta del bucle**, no en una fase global.
- **Firmware: dos ramas**. La de §17 (GFX) queda confirmada por el lado del codigo que
  produce su silencio: `gfx_v8_0.c:983-1150`, `_2` en `OPTIONAL` y fallback `REQUIRED` en
  `-ENODEV`. **Aparece una rama que §17 no cubrio: el firmware MC**, `gmc_v8_0.c:217-269`,
  `AMDGPU_UCODE_REQUIRED`, cargado al hardware en `gmc_v8_0.c:388-398` via
  `WREG32(mmMC_SEQ_SUP_PGM, ...)`. **Los estados de §17 NO cambian.**
- **Hecho nuevo que matiza §17**: el nombre del firmware MC **no** lo fija solo
  `asic_type`. `gmc_v8_0.c:241-251` escribe `mmMC_SEQ_IO_DEBUG_INDEX`, lee
  `mmMC_SEQ_IO_DEBUG_DATA` y si vale `0x05b4dc40` elige `polaris12_32`, si no `polaris12`.
  El nombre es funcion del ASIC **y** de un registro leido en runtime.
- **`amdgpu_device_fw_loading` no cubre a Polaris12**: `:2178-2212` esta gateado por
  `asic_type >= CHIP_VEGA10` y solo recorre PSP; POLARIS12 precede a VEGA10 en el enum.
  Queda `amdgpu_pm_load_smu_firmware` (`:2215`). El recorrido de PSP es generalidad de
  amdgpu, no requisito de este RX550.
- **GFX entra en `gfx_v8_0_sw_init` (`:1886-2032`)**: `num_mec = 2` `:1901`, 5 IRQ
  `:1914-1942`, **firmware `:1948`**, BOs RLC `:1954` y MEC `:1960`, **ring GFX
  `:1977-1979`**, compute rings `:1994`, KIQ `:2005`/`:2011`, MQD `:2016`,
  `gpu_early_init` `:2022`.
- **Control 2 ejecutado y con resultado negativo**: `gfx_v8_0_gpu_early_init`
  (`:1638-1844`, 207 lineas) tiene **0 WREG y 3 RREG**; solo llama 2x
  `amdgpu_atombios_get_gfx_info`. Pese al nombre, **no programa hardware**.
  `gfx_v8_0_cp_resume` (`:4710-4736`) tiene **0 WREG y 0 RREG**: es dispatcher a
  `cp_gfx_resume`, `kcq_resume`, `kiq_resume`, `enable_gui_idle_interrupt`.
- **Rings (control especial)**: `amdgpu_ring_init` (`amdgpu_ring.c:226-386`, 161 lineas)
  tiene **0 WREG**. Cubre caller, objeto en `adev->rings[]` `:259-260`, fences `:262`/`:326`,
  5 writebacks `:267-295`, sizing de IB `:332-334`, `ring_size` `:339`, **buffer en
  `AMDGPU_GEM_DOMAIN_GTT`** `:361-366` e inscripcion en `gpu_sched` `:378-382`. Hardware
  programming, enable y submission: `NOT_IN_THIS_FUNCTION`.
- **Scheduler**: `drm_sched_init(&ring->sched, &args)` en `amdgpu_device.c:2258`, uno por
  ring, y **solo para rings que ya existen** en `adev->rings[]` (`:2232`). La dependencia
  ring object -> scheduler es innegable por orden de codigo (rings en `:2312`, scheduler
  en `:2459`).
- **Correcciones a §22**: (a) el firmware GFX no estaba en fase desconocida; la fase es
  `sw_init` `:1948` y el load a hw es `gfx_v8_0_hw_init:4752`/`:4756` desde `phase2:2159`.
  (b) la funcion contenedora de `gfx_v8_0.c:1875` es `gfx_v8_0_compute_ring_init:1846`, y
  el ring GFX se crea en `gfx_v8_0_sw_init:1977`. (c) `amdgpu_gfx_init` **no existe** en
  7.1.3; solo `amdgpu_gfx_init_spm_golden`.
- **Cinco errores de instrumento en esta ronda** (todos registrados en §23.13): dos firmas
  demasiado especificas dejaron `awk` leyendo el fichero entero desde la linea 1;
  `amdgpu_vmid_mgr_init` se busco en `amdgpu_vm.c` y esta en `amdgpu_ids.c:574`; y un
  `heredoc` de ~380 lineas se corrompio y escribio contenido ajeno (diagramas y CJK) en
  `RESEARCH-LINES.md`. Detectado por conteo de secciones, revertido desde
  `/tmp/opencode/RLD2.bak` (3340 lineas, §22 presente) y reescrito con la herramienta de
  escritura. **Tercera y cuarta ocurrencia** de los dos metodos ya registrados, y la quinta
  sobre el instrumento de escritura.
- **Verificacion de los 2 CJK del documento (fuera de §23)**: ambos en **§20**
  (`RE-CPU-01`, linea paralela), lineas 2785 y 2873. Ya reportados en ronda previa;
  **no tocados** por ser contenido ajeno. `CROSS-LINE_CANDIDATE` re-verificado.
- **Lo que queda abierto**: la programacion de hardware efectiva de GFX (un nivel mas abajo
  que `gfx_v8_0_cp_resume`), la construccion y envio de PM4, y si el scheduler se crea
  para los rings de UVD y VCE. Todo `NOT_TRACED` por decision de alcance.

## 2026-09-28 — RE-02 (RX550): gfx_v8_0_cp_resume y la cadena de ring (OBJECT/PROGRAMMED/ENABLED/TESTED)

- **Las cinco funciones pedidas**, todas `static` en `gfx_v8_0.c`, con extension y
  conteo explicito de WREG/RREG sobre el rango completo:
  `gfx_v8_0_cp_resume` `:4710-4736` (27, 0/0) · `gfx_v8_0_kiq_resume` `:4663-4667` (5, 0/0) ·
  `gfx_v8_0_kcq_resume` `:4669-4684` (16, 0/0) ·
  `gfx_v8_0_cp_test_all_rings` `:4686-4708` (23, 0/0) ·
  `gfx_v8_0_cp_gfx_resume` `:4227-4278` (52, **12 WREG**).
- **Estructura de corchete en `cp_resume`**: `:4715` deshabilita las interrupciones de idle
  y `:4733` las rehabilita. Orden: kiq -> cp_gfx -> kcq -> test_all_rings.
- **Segundo caller de la cadena, NO en el camino de arranque**: `gfx_v8_0_post_soft_reset`
  (`gfx_v8_0.c:5055`, callback `.post_soft_reset` en `:6864`) invoca las cuatro en
  `:5081-5089`, y lo hace via `amdgpu_device_ip_post_soft_reset`
  (`amdgpu_device.c:4822-4831`) desde `:5137`. Es un camino de **recuperacion**, no de
  probe. Clasificado `NOT_IN_BOOT_PATH`.
- **A. KIQ**: `gfx_v8_0_kiq_resume` tiene 5 lineas y un callee. En la rama de arranque
  (`:4603-4618`) `gfx_v8_0_kiq_init_queue` hace `gfx_v8_0_kiq_setting` `:4588` (1 WREG:
  `mmRLC_CP_SCHEDULERS` con `me/pipe/queue` y bit `0x80`), `vi_srbm_select` `:4610`,
  `gfx_v8_0_mqd_init` `:4611` (**0 WREG, 23 RREG**), y **`gfx_v8_0_mqd_commit` `:4612`
  (7 WREG)**. KIQ **PROGRAMMED** = `:4612`. KIQ **ENABLED** = dos actos fuera de
  `kiq_resume`: `WREG32(mmCP_MEC_CNTL, 0)` en `:4283` (des-halta MEC1/MEC2) y el
  `amdgpu_ring_commit(kiq_ring)` en `:4360` que suena el doorbell.
- **`gfx_v8_0_mqd_commit` `:4546-4581` descompuesto**: `CP_PQ_WPTR_POLL_CNTL.EN=0` `:4556`;
  bucle `mmCP_HQD_VMID`..`mmCP_HQD_EOP_CONTROL` `:4559-4560`; **bajo
  `if (asic_type != CHIP_TONGA)` — CIERTO para POLARIS12** — escribe `mmCP_HQD_EOP_RPTR`,
  `mmCP_HQD_EOP_WPTR`, `mmCP_HQD_EOP_WPTR_MEM` `:4567-4571`; bucle
  `mmCP_HQD_EOP_EVENTS`..`mmCP_HQD_ERROR` `:4573-4574`; bucle `mmCP_MQD_BASE_ADDR`..
  `mmCP_HQD_ACTIVE` `:4577-4578` ("activate the HQD").
- **`vi_srbm_select` (`vi.c:578-587`)**: 1 WREG a `mmSRBM_GFX_CNTL` con
  `PIPEID`/`MEID`/`VMID`/`QUEUEID`. Es lo que direcciona los `WREG32(mqd_reg, ...)` de
  `mqd_commit` a la cola correcta.
- **B. GFX ring**: `gfx_v8_0_cp_gfx_resume` afecta a **un solo** ring (`gfx_ring[0]`,
  `:4241`) y **NO usa MQD**: escribe `CP_RB0_*` directamente. Base
  `mmCP_RB0_BASE(_HI) = ring->gpu_addr >> 8` `:4269-4270`; tamano
  `rb_bufsz = order_base_2(ring->ring_size / 8)` `:4242` -> `RB_BUFSZ`/`RB_BLDSZ` `:4243-4244`;
  `mmCP_RB0_WPTR = 0` `:4255`; `CP_RB0_RPTR_ADDR(_HI)` `:4259-4260`;
  `CP_RB_WPTR_POLL_ADDR_LO/HI` `:4263-4264`; `mmCP_RB_VMID = 0` `:4238` (el ring GFX usa
  VMID 0, el de sistema). **Enable explicito**: `gfx_v8_0_cp_gfx_start` `:4275` ->
  `gfx_v8_0_cp_gfx_enable(true)` `:4142` -> `mmCP_ME_CNTL` sin `ME_HALT`/`PFP_HALT`/`CE_HALT`
  `:4089-4097`. Doorbell de GFX: `gfx_v8_0_set_cpg_door_bell` `:4272` (3 WREG).
- **C. KCQ, las cuatro por separado**:
  `gfx_v8_0_cp_compute_enable(adev, true)` `:4673` -> `WREG32(mmCP_MEC_CNTL, 0)`, des-halta
  MEC; en la rama de disable **si** pone `sched.ready = false` `:4286`, en la de enable no.
  `gfx_v8_0_kcq_init_queue` `:4676` -> 0 WREG, y **NO llama a `gfx_v8_0_mqd_commit`**
  (asimetria con KIQ `:4612`). `gfx_v8_0_set_mec_doorbell_range` `:4681` (3 WREG).
  `gfx_v8_0_kiq_kcq_enable` `:4683` -> 0 WREG, emite PM4 y commitea.
- **Asimetria central de la ronda**: el MQD de un **compute queue no lo programa el
  driver**. No hay ningun `WREG` de HQD para un KCQ. El MQD viaja a la GPU dentro de
  `PACKET3_MAP_QUEUES` (`gfx_v8_0.c:4345-4357`) con
  `mqd_addr = amdgpu_bo_gpu_offset(ring->mqd_obj)` `:4341` y
  `wptr_addr = ring->wptr_gpu_addr` `:4342`. Por eso el estado `PROGRAMMED` de un KCQ queda
  **UNKNOWN** y no se inventa un estado inventado.
- **D. Doorbell MEC** (`gfx_v8_0.c:4653-4661`, 9 lineas): bajo
  `if (asic_type > CHIP_TONGA)` — **CIERTO** para POLARIS12 — escribe
  `mmCP_MEC_DOORBELL_RANGE_LOWER = doorbell_index.kiq << 2` y `_UPPER =
  doorbell_index.mec_ring7 << 2`; y **fuera** de esa condicion,
  `WREG32_FIELD(CP_PQ_STATUS, DOORBELL_ENABLE, 1)` `:4660`. El propio comentario `:4659`
  separa la linea de habilitacion de las dos de rango. Orden: se habilita **antes** del
  commit del KIQ en `:4360`.
- **El doorbell ES el mecanismo de commit**. `amdgpu_ring_commit`
  (`amdgpu_ring.c:169-189`, 0 WREG) hace `mb()` y llama a `amdgpu_ring_set_wptr`, que es
  **macro** de dispatch (`amdgpu_ring.h:436`).
  `gfx_v8_0_ring_set_wptr_gfx` `:6022-6034` -> `*wptr_cpu_addr = wptr` +
  `WDOORBELL32(...)` si `use_doorbell`; `gfx_v8_0_ring_set_wptr_compute` `:6222-6229` ->
  **incondicional**. `WDOORBELL32` es `writel(v, adev->doorbell.cpu_addr + index)`
  (`amdgpu_doorbell_mgr.c:65`). **La tabla KIQ usa la implementacion de compute**
  (`.set_wptr` en `:6958`). `DERIVATION`: un doorbell no es un `WREG32` de registro de IP,
  asi que contar `WREG` **no basta** para detectar programacion de hardware; este caso lo
  demuestra con `gfx_v8_0_ring_set_wptr_compute` que tiene 0 WREG y aun asi es la
  operacion que hace visible el trabajo al hardware.
- **`use_doorbell = true` en los tres tipos** para Polaris12: GFX `:1972-1973` (bajo
  `asic_type != CHIP_TOPAZ`), compute `:1862`, KIQ `amdgpu_gfx.c:317`.
- **E. Ring test**: `amdgpu_ring_test_helper` (`amdgpu_ring.c:751-767`) llama a
  `amdgpu_ring_test_ring`, que **no es una funcion sino una macro**
  (`#define amdgpu_ring_test_ring(r) (r)->funcs->test_ring((r))`, `amdgpu_ring.h:432`).
  Las tres tablas de gfx_v8_0 apuntan a la **misma** `gfx_v8_0_ring_test_ring` (`:838`).
  Su cuerpo: `WREG32(mmSCRATCH_REG0, 0xCAFEDEAD)` `:845`; `amdgpu_ring_alloc(ring, 3)` `:846`;
  emite `PACKET3_SET_UCONFIG_REG` (`= 0x79`, `cikd.h:476`) con destino `mmSCRATCH_REG0` y
  valor `0xDEADBEEF` `:850-852`; `amdgpu_ring_commit` `:853`; y **sondea** con
  `RREG32(mmSCRATCH_REG0)` hasta `usec_timeout` veces `:855-860`. PASS si
  `tmp == 0xDEADBEEF` antes de agotar el timeout; FAIL = `-ETIMEDOUT` `:862-863`.
  **No interviene ningun fence**: es sondeo de registro.
  **PRIMERA EJECUCION REAL DE GPU DEMOSTRABLE** en todo el camino minimo: el valor cambia
  solo si la GPU leyo el paquete del ring y ejecuto la escritura. `ring->sched.ready =
  !r` en `amdgpu_ring.c:764`, o sea `ready = true` **solo** si el test paso.
- **Asimetria en `cp_test_all_rings`**: el test de `gfx_ring[0]` `:4693` y el de
  `kiq[0].ring` `:4698` **abortar** el arranque si fallan (`if (r) return r;`); el de los
  compute rings `:4704` **ignora el retorno**. Un KCQ con test fallido queda
  `sched.ready = false` sin hacer fallar el init.
- **PM4: tres emisores, los tres de inicializacion.**
  (1) `gfx_v8_0_cp_gfx_start` `:4151-4187` sobre el ring GFX: `PREAMBLE_BEGIN_CLEAR_STATE`,
  `CONTEXT_CONTROL`, `SET_CONTEXT_REG` en bucle sobre `vi_cs_data`, `SET_CONTEXT_REG` para
  `mmPA_SC_RASTER_CONFIG`, `PREAMBLE_END_CLEAR_STATE`, `CLEAR_STATE`, `SET_BASE` para
  `CE_PARTITION_BASE`. (2) `gfx_v8_0_kiq_kcq_enable` `:4331-4357` sobre el KIQ:
  `PACKET3_SET_RESOURCES` +6 y `PACKET3_MAP_QUEUES` +5 por cola.
  (3) `gfx_v8_0_ring_test_ring` `:850-852`. **Ninguna llamada a `emit_ib`, `emit_fence` ni
  `emit_vm_flush` en toda la cadena.**
- **Frontera de submission fijada**: el test de ring invoca `amdgpu_ring_write`
  directamente, **sin** `amdgpu_cs_ioctl`, **sin** `amdgpu_cs_parser`, **sin**
  `amdgpu_ib`, **sin** `amdgpu_cs_patch_jobs` y **sin** fence de usuario. Es
  `INITIALIZATION TEST`, no `USER WORKLOAD SUBMISSION`. La frontera queda entre
  `sched.ready = true` (`amdgpu_ring.c:764`) y `amdgpu_cs_ioctl` (`amdgpu_cs.c:1438`,
  ronda previa).
- **Correccion de §23.12**: `PM4` pasa de `NOT_TRACED` a `PROVEN_CALLEE` con tres emisores
  y su soporte. `submission` **sigue** `NOT_TRACED`, pero por un motivo nuevo y mas
  preciso: los tres emisores son de inicializacion.
- **CONTROL 3, resultado de la ronda**: **no existe ni una linea de codigo especifica de
  `CHIP_POLARIS12`** en esta cadena. El chip se selecciona solo por comparaciones
  **negativas o de rango** contra `CHIP_TONGA` y `CHIP_TOPAZ` (`:4714`, `:4197`, `:4215`,
  `:4567`, `:4655`, `:1972`). Todas son inclusivas: comportamiento GFX8/VI general con dos
  excepciones antiguas. Desglose: especifico de Polaris12 = nada; compartido GFX8/VI = toda
  la cadena; generico amdgpu = `amdgpu_ring_init`/`_commit`/`_test_helper`,
  `amdgpu_mm_wdoorbell`, `drm_sched_init`; heredado de DRM scheduler = `ring->sched.ready`.
- **COLISION DE NUMERACION CON LA LINEA PARALELA, registrada sin tocar lo ajeno**: al
  anexar, `RESEARCH-LINES.md` ya tenia un `## 24. REMOVABILITY-01 (RX550) — SDMA NO ES UN
  MOTOR DE COPIA...` de 328 lineas (3859-4185) que **no existia** al cierre de la ronda
  anterior (el documento tenia 3855 lineas). Renumeré **mi** seccion de `## 24.` a
  `## 25.` y sus 19 subsecciones. **No** edite una sola linea del contenido ajeno ni de
  `IDEA-REGISTER.md`, `experiments_proposed.md` ni `R2-GLOBAL-DOCUMENTATION-MAP.md`, que
  tambien tienen modificaciones recientes. Unico control que hice sobre lo ajeno: el
  conjunto de IDs sigue siendo **184 en ambos ficheros e identico**, y `REMOVABILITY-01`
  **no introduce ningun ID nuevo**. `NOT_INCORPORATED`: no leí ni usé su contenido.
- **Cuatro errores de instrumento**, todos detectados antes de escribir nada:
  `amdgpu_ring_test(` y `amdgpu_ring_set_wptr` **no son funciones sino macros**
  (`amdgpu_ring.h:432` y `:436`); `amdgpu_ring_clear_ring` es `static inline` en
  `amdgpu_ring.h:488`, no una funcion de `.c`; y un patron de firma con 4 grupos no
  matcheo. **Sexta** y **septima** ocurrencia de los dos metodos ya registrados
  ("macro o puntero de funcion donde se busca una funcion", "forma esperada en vez de
  definicion").
- **Corrupcion de escritura detectada y reparada**: el fichero temporal de §25 salio con 4
  fragmentos corruptos (2 CJK, 1 cirilico, 1 fragmento en ingles) y 2 celdas de tabla con
  pipes escapados. Los 6 se corrigieron y verificaron antes de anexar.

---

## 2026-09-28 — REMOVABILITY-02 (RX550): separacion hardware/driver de la ruta CPU de VM

**SOURCE UNICA:** `RESEARCH/kernelbuild/linux-7.1.3` (upstream 7.1.3 = kernel runtime). No se
consulto master ni otra version como evidencia. **HOST_SCOPE:** el host vivo, solo para
`OBSERVATION` de log de boot y de parametros de modulo en lectura.

- **Pregunta:** la imposibilidad de actualizar PTEs desde CPU con BAR < VRAM, ¿es (A)
  hardware, (B) mecanismo CPU de amdgpu, (C) rendimiento, (D) combinacion, (E) `UNKNOWN`?
- **Documentado en:** `02-ARQUITECTURA/RESEARCH-LINES.md` §26. No se creo ningun fichero.
- **Resultado:** **(D)**, con las cuatro partes en niveles distintos y **ninguna en A**.
  La restriccion real esta en `amdgpu_object.c:137` (`lpfn = visible_pfn`), una decision de
  colocacion de allocator, mas `amdgpu_ttm.c:2116` (`ioremap_wc` de exactamente
  `visible_vram_size`). El `WARN_ONCE` de `amdgpu_vm.c:2631-2633` dice "recommended", no
  bloquea, y el flujo continua por la ruta CPU igual.
- **Hallazgo que cierra el discriminante:** el PTE contiene una **direccion fisica de 40
  bits** (`gmc_v8_0.c:1134`, `pte_addr_mask = 0x000000FFFFFFF000`). El BAR es la apertura
  de la **CPU**, no la de la GPU. Por tanto la ventana del BAR no es un contrato del
  silicio para la GPU, y `NOT_DETERMINED` se conserva para la pregunta del silicio.
- **Hallazgo nuevo de capacidad (DERIVATION, no FACT):** con la geometria observada
  (`vm size is 64 GB, 2 levels, block size is 10-bit`) las tablas de pagina ocupan
  **128 MiB**, contra una ventana observada de **256 MiB**. **Caben, con margen de 2x.**
  En *este* host la ruta CPU no esta bloqueada por falta de BAR. Con RAM mayor
  (`vm_size = phys_ram_gb * 3`, `amdgpu_vm.c:2415-2418`) podria no caber.
- **Corte CPU/GPU de la ruta SDMA, exigido por la consigna y verificado:** hasta
  `amdgpu_vm_sdma_update` todo es construccion de paquete en memoria de host
  (`ib->ptr[ib->length_dw++]`). La primera instruccion que toca la GPU es
  `amdgpu_job_submit` (`amdgpu_vm_sdma.c:123`). `amdgpu_ring_pad_ib` **no** implica
  ejecucion. Ademas el opcode es `SDMA_OP_GEN_PTEPDE`, **no PM4 de GFX**: es otra ruta y no
  se confunde con la de §25.
- **Asimetria no supuesta, verificada:** la CPU no necesita ver el *dato*, solo la
  *tabla*. `amdgpu_gmc_get_pde_for_bo` (`amdgpu_gmc.c:112-127`) resuelve VRAM a
  `amdgpu_bo_gpu_offset` y GTT a `dma_address[0]`, sin mirar `visible_vram_size`.
- **Sin fallback (FACT):** `use_cpu_for_update` se asigna dos veces en todo el arbol
  (`amdgpu_vm.c:2626` y `:2735`) y no vuelve a cambiar. Si la ruta elegida falla, no hay
  reintento por la otra.
- **Error de instrumento de esta ronda, 1:** `grep -rn "amdgpu_gmc_map_gart"` devolvio 0 y
  lo lei como "esa funcion no existe". **Falso:** es `amdgpu_vm_map_gart`
  (`amdgpu_vm.c:957`). Es la **cuarta** vez del token literal (defecto #8 de §15.10) y la
  **quinta** del truncamiento (§15.10 #13). `INTERPRETATION_ERROR`, detectado al no poder
  explicar `pages_addr ? … : addr` siguiendo el termino que ya tenia en la cabeza. **PATTERN
  confirmada por sexta vez: buscar por el nombre que uno espera en vez de seguir el
  simbolo que el codigo declara.**
- **Citas corregidas antes de escribir:** 9 referencias `file:line` estaban desplazadas
  (`amdgpu_vm_cpu.c:88`->`:87`, `:90`->`:91`, `:112`->`:110`, `:122`->`:123`;
  `amdgpu_gmc.c:172`->`:175`; `amdgpu_vm_sdma.c:112`->`:113`; `amdgpu_object.c:203-229`->`:818-844`;
  `amdgpu_vm_pt.c:52-64`->`:50-64`, `:101-112`->`:103-112`, y cuatro de la tabla de §26.6).
  Verificadas una a una contra el arbol tras la correccion.
- **Residuos de escritura propios, corregidos:** 4 palabras pegadas y 2 fugas CJK
  introducidas en §26, detectadas por el escaner y por un grep de tokens composed, y
  corregidas antes de cerrar.
- **`NOT_AVAILABLE`:** `include/drm/drm_sched.h` no esta en la extraccion de 7.1.3 del
  proyecto. `NOT_FOUND` con ruta nombrada. No consultada en otra version. No bloquea:
  `drm_sched_entity_init` y `drm_sched_job_init` estan en
  `drivers/gpu/drm/scheduler/`, que si esta, y se leyeron directamente.
- **Lo que NO se hizo:** no se ejecuto el experimento de §24; `vm_update_mode` se leyó y no
  se escribio; no se toco `ip_block_mask`, configuracion, firmware, kernel ni sistema; no
  se modifico amdgpu, Mesa ni `/lib/firmware`; no se cargo ningun modulo; no se uso sudo;
  no se toco la linea CPU/Haswell; no se evaluo SDMA removal mediante modificacion.
- **Estado del discriminante de §24:** `INVESTIGATION_REQUIRED`. La separacion
  hardware/driver se **consiguio** estaticamente para B y para el default; **no** se
  produjo evidencia que separe C de una capacidad real del silicio, y eso se conserva como
  `NOT_DETERMINED` en vez de elegir.

## 2026-09-28 — RE-02 (RX550): queue_bitmap → numero real de compute rings en Polaris12

- **CASO B en su forma fuerte**: el numero real no es 64 ni `UNKNOWN`, es una **funcion
  cerrada de un unico parametro de modulo**, con valor numerico demostrado bajo los
  valores por defecto documentados.
  `CANDIDATE_QUEUE_SPACE = 64` (PROVEN_FROM_SOURCE) ·
  `ENABLED_QUEUE_BITS = min(clamp(amdgpu_num_kcq), 32)` ·
  `COMPUTE_RINGS_CREATED = ENABLED_QUEUE_BITS` (1:1 con los bits) · **= 8 con los
  valores por defecto**. El 8 es **invariante** respecto a `amdgpu_compute_multipipe`:
  las dos politicas producen 8 bits. Depende **solo** de `amdgpu_num_kcq`.
- **Mapeo (mec,pipe,queue) → bit, aritmetico y no tabla**: `amdgpu_gfx_mec_queue_to_bit`
  (`amdgpu_gfx.c:48-59`) = `mec*32 + pipe*8 + queue` para Polaris12, con
  `num_mec=2` (`gfx_v8_0.c:1901`), `num_pipe_per_mec=4` (`:1910`),
  `num_queue_per_pipe=8` (`:1911`). Existe la **inversa**
  `amdgpu_queue_mask_bit_to_mec_queue` (`amdgpu_gfx.c:61-70`), luego el mapeo es
  **biyectivo** sobre el espacio candidato: 64 ternas, bits 0..63, sin huecos ni
  colisiones.
- **A. `amdgpu_gfx_is_mec_queue_enabled`** (`amdgpu_gfx.c:72-77`, 6 lineas): un
  `test_bit` sobre `adev->gfx.mec_bitmap[xcc_id].queue_bitmap`. En Polaris12 se invoca
  **siempre con `xcc_id = 0`** (`gfx_v8_0.c:1990`). `mec` **no** es un indice de ME: se
  traduce a `ring->me = mec + 1` (`gfx_v8_0.c:1857`).
- **DECOY descartado por el cuerpo, no por el nombre**: `amdgpu_gfx_me_queue_to_bit`
  (`amdgpu_gfx.c:79`) es casi homonimo pero opera sobre `adev->gfx.me.queue_bitmap`
  (`:97`), que es el bitmap de colas de **graficos** con `AMDGPU_MAX_GFX_QUEUES`. No
  participa en esta cadena.
- **C. Escritores de `queue_bitmap`, conjunto EXHAUSTIVO** (busqueda de `set_bit`,
  `bitmap_or`, `bitmap_set`, `bitmap_zero` sobre `mec_bitmap` en los 304 `.c`):
  (1) `bitmap_zero(adev->gfx.mec_bitmap[0].queue_bitmap, 128)` en `gfx_v8_0.c:1293`,
  dentro de `gfx_v8_0_mec_init` (`:1287-1318`, 0 WREG); (2) `set_bit` en
  `amdgpu_gfx.c:224` (rama multipipe) y `:232` (rama no-multipipe), ambos dentro de
  `amdgpu_gfx_compute_queue_acquire` (`:206-240`), llamado desde `gfx_v8_0.c:1296`.
  **No hay ningun otro escritor**: ni `bitmap_or`, ni asignacion directa, ni copia, ni
  escritura indirecta por referencia. Los `bitmap_zero` de v7_0, v9_0, v9_4_3, v10_0,
  v11_0, v12_0 y v12_1 son de otros ASIC.
- **HALLAZGO ESTRUCTURAL**: **ninguna de las dos ramas del escritor suma un termino `mec`
  al indice de bit**. Multipipe: `set_bit(pipe * num_queue_per_pipe + queue, ...)`.
  No-multipipe: `set_bit(i, ...)`. En ambas los bits quedan por debajo de
  `num_pipe_per_mec * num_queue_per_pipe = 32`.
- **D. `mec_bitmap`**: `struct amdgpu_mec_bitmap { DECLARE_BITMAP(queue_bitmap,
  AMDGPU_MAX_COMPUTE_QUEUES); }` (`amdgpu_gfx.h:121-124`).
  `AMDGPU_MAX_COMPUTE_QUEUES = AMDGPU_MAX_QUEUES = 128` (`amdgpu_gfx.h:50`, `:47`).
  `mec_bitmap[AMDGPU_MAX_GC_INSTANCES] = mec_bitmap[8]` (`:423`, `:46`).
  **El bitmap es de 128 bits pero el espacio candidato de Polaris12 es de 64**: los bits
  64..127 nunca se consultan, porque `mec < num_mec = 2` implica `bit <= 63`. Ancho de
  estructura y espacio de valores son magnitudes distintas.
  `NUM_XCC(x) = hweight16(x)` (`amdgpu_gfx.h:79`) y `xcc_mask = 1`
  (`gfx_v8_0_early_init:5263`) → `num_xcc = 1` → **solo se escribe `mec_bitmap[0]`**.
- **`OBSERVATION` (latencia, no fallo activo)**: `gfx_v8_0_mec_init:1293` hace
  `bitmap_zero` **solo de `mec_bitmap[0]`**, a diferencia de `gfx_v12_1.c:596` y
  `gfx_v9_4_3.c:629` que recorren todos los indices. `mec_bitmap[1..7]` quedan sin
  inicializar en el camino GFX8. No es fallo porque `num_xcc = 1` y el consumidor usa
  `xcc_id = 0`, pero cualquier lectura futura de `mec_bitmap[j>0]` en GFX8 leeria
  memoria no inicializada. Registrado, no reparado.
- **Orden demostrado, y era el riesgo principal**: `num_compute_rings` se fija en
  `gfx_v8_0_early_init:5265` (el callback `.early_init`, `gfx_v8_0.c:6851`), que corre en
  `amdgpu_device_ip_early_init` — una fase **anterior** a `sw_init`. Y dentro de
  `gfx_v8_0_sw_init`, `num_mec`/`num_pipe_per_mec`/`num_queue_per_pipe` se fijan en
  `:1901-1911`, **antes** de `gfx_v8_0_mec_init:1960` y del bucle de creacion `:1987`.
  No hay lectura de valor sin inicializar.
- **`num_compute_rings`**: unico punto de escritura para gfx_v8_0,
  `gfx_v8_0_early_init:5265` = `min(amdgpu_gfx_get_num_kcq(adev),
  AMDGPU_MAX_COMPUTE_RINGS)`. `amdgpu_gfx_get_num_kcq` (`amdgpu_gfx.c:1357-1366`):
  `amdgpu_num_kcq == -1` → 8; `> 8` o `< 0` → `dev_warn` + 8; si no, el valor.
  `int amdgpu_num_kcq = -1;` (`amdgpu_drv.c:233`),
  `module_param_named(num_kcq, amdgpu_num_kcq, int, 0444)` (`amdgpu_drv.c:958`).
- **Politica de reparto**: `amdgpu_gfx_is_compute_multipipe_capable`
  (`amdgpu_gfx.c:152-168`): GC de Polaris12 es 8.0.0 → `:160` falsa; no es POLARIS11 →
  `:165` falsa; `:168` `return num_mec > 1` → **true** con los parametros por defecto.
  `int amdgpu_compute_multipipe = -1;` (`amdgpu_drv.c:205`),
  `module_param_named(compute_multipipe, ..., 0444)` (`amdgpu_drv.c:574`).
  Ambos parametros son **0444**: escribibles solo en la carga del modulo.
- **La aritmetica, con los valores por defecto**: `clamp(-1) = 8` →
  `num_compute_rings = min(8, 8) = 8` → `max_queues_per_mec = min(32, 8) = 8`.
  Multipipe, `j = 0`, `i = 0..7` → `pipe = i%4`, `queue = (i/4)%8` → bits
  **`{0, 1, 8, 9, 16, 17, 24, 25}`**. No-multipipe → bits **`{0..7}`**.
  **Ambos casos: 8 bits, todos `< 32`, o sea todos de `mec = 0`.**
- **E. Correspondencia 1:1** entre bit habilitado y compute ring creado. El bucle
  (`gfx_v8_0.c:1986-2003`) recorre el espacio candidato completo y sin solapamientos
  (el mapeo terna→bit es biyectivo), llama a `is_mec_queue_enabled(adev, 0, i, k, j)` y
  por cada bit activo hace **una** `gfx_v8_0_compute_ring_init` y **un** `ring_id++`.
  Coherencia interna verificada: `num_compute_rings = 8` es el mismo valor que recorren
  `gfx_v8_0_mec_init:1298`, `gfx_v8_0_kcq_resume:4675`,
  `gfx_v8_0_kiq_kcq_enable:4339` y `gfx_v8_0_cp_test_all_rings:4702`.
- **DERIVACION RELEVANTE**: **MEC2 no se usa para computo en este camino**. Aunque
  `num_mec = 2` declara dos unidades, ninguna funcion del arranque habilita una cola de
  `mec = 1`, porque el escritor no suma termino `mec` y
  `max_queues_per_mec = 8 < 32`. Los 8 anillos tienen `ring->me = 1`
  (`gfx_v8_0.c:1857`). Hecho sobre el codigo, **no** afirmacion sobre la capacidad de
  silicio de MEC2.
- **F. KIQ SEPARATION**: el KIQ **no** es un compute ring y no participa en `mec_bitmap`.
  Vive en `gfx.kiq[AMDGPU_MAX_GC_INSTANCES]` (`amdgpu_gfx.h:424`), no en
  `gfx.compute_ring[64]` (`:462`); su tipo es `AMDGPU_RING_TYPE_KIQ` y su tabla
  `gfx_v8_0_ring_funcs_kiq` (`:6951`); no cuenta en `num_compute_rings`; se inicializa
  por `amdgpu_gfx_kiq_init_ring` (`amdgpu_gfx.c:306`, invocado desde
  `gfx_v8_0_sw_init:2011`), que no toca el bitmap MEC. Su MQD se distingue **por tipo de
  ring**: `gfx_v8_0_mqd_init:4540-4541`. Total de rings del bloque GFX con los valores por
  defecto: **1 GFX + 1 KIQ + 8 compute**.
- **H. `CONTROL 3`**: **no hay ninguna linea de codigo cuyo contenido sea exclusivo de
  Polaris12**. Lo unico especifico es la *inclusion* en un `case` del `switch` de
  `gfx_v8_0_sw_init:1893`, cuya rama comparte valores con TONGA, FIJI, POLARIS10,
  POLARIS11 y VEGAM (`:1894-1902`); TOPAZ y STONEY reciben `num_mec = 1`, lo que prueba
  que el valor **depende del ASIC**. Compartir 2/4/8 **no** demuestra que las 64 colas
  esten habilitadas, y esta ronda lo quantify: **ocho**.
- **I. REMOVABILITY_STATUS = NOT_DECIDED**. Recursos por anillo: ranura en
  `compute_ring[]`, BO del MQD, ranura en `mqd_backup[]` (`amdgpu_gfx.h:118`, 64
  entradas), un doorbell (`gfx_v8_0.c:1863`), `eop_gpu_addr`, y el registro en
  `adev->rings[]` + scheduler (`amdgpu_device.c:2258`). **Compartido, no duplicado**:
  `hpd_eop_obj` es un solo BO de `num_compute_rings * GFX8_MEC_HPD_SIZE` = 8*4096 =
  32768 bytes (`gfx_v8_0.c:1298-1305`). Generalidad presente pero no ejercitada:
  `mec_bitmap[8]` (se usa 1), bitmap de 128 bits (se usan <=64),
  `compute_ring[64]` (se usan 8), `mqd_backup[64]` (se usan 8), `num_mec = 2` (1 efectiva
  para computo), dos ramas de politica (se usa una). **De `queue_bitmap` depende solo el
  numero de anillos**, no las estructuras ni los recursos por anillo.
  `UNKNOWN` y no evaluado: si un numero menor alteraria la correccion del reparto
  multipipe, la geometria del HPD, o el rango de doorbells
  (`gfx_v8_0_set_mec_doorbell_range:4657` usa `doorbell_index.mec_ring7`, o sea asume 8).
- **`NOT_AVAILABLE`**: `/sys/module/amdgpu/parameters/num_kcq` y `.../compute_multipipe`
  — por restriccion de alcance, no por permiso. No hay `dev_info` ni `drm_info` en
  `gfx_v8_0_compute_ring_init` ni en el bucle de creacion que imprima el conteo, y el
  `dev_dbg` de `amdgpu_gfx.c:237` (`"mec queue bitmap weight=%d"`) requiere dynamic
  debug. Por eso el valor real de esta maquina queda como funcion del parametro, no como
  numero.
- **`METHODOLOGICAL_ERRORS = NONE` en esta ronda**. Dos búsquedas que podrian haber dado
  falso `NOT_FOUND` se resolvieron por metodo: (a) `amdgpu_gfx_mec_queue_to_bit` se
  confirmo en su rango completo `:48-59` en vez de asumirlo desde el `case` de
  `sw_init`; (b) el homonimo `amdgpu_gfx_me_queue_to_bit` (`:79`) se descarto **por el
  cuerpo** — opera sobre `gfx.me.queue_bitmap` (`:97`) — y no por el nombre. Es el mismo
  control que en §25 detecto que `amdgpu_ring_test_ring` era una macro.
- **Renumeracion**: la linea paralela anadio `## 26. REMOVABILITY-02` (`PTES`) entre
  §25 y esta ronda. Mi seccion es `## 27.`, sin colision. Las secciones ajenas `## 24.` y
  `## 26.` no se han tocado.
- **Validacion de escritura**: el temporal salio con 8 fragmentos corruptos (2 CJK,
  `se_ha`, `heterozygocyclo`, `searched`, `se.border`, `Clark`, `XxCC` y dos ideogramas CJK) mas 2
  caracteres U+FFFD que introduje al corregir. Los 10 se repararon y verificaron antes de
  anexar: 0 CJK, 0 cirilico, 0 U+FFFD, 12 bloques de tabla, 0 desajustes, 26 vallas.

## 2026-09-28 — RE-02 (RX550): auditoria MEC1 falsada, cierre CGPG/queue0, cierre de observabilidad de PT

- **Alcance**: los tres bloques proceden de auditorias estaticas de
  `RESEARCH/kernelbuild/linux-7.1.3` (upstream 7.1.3). Sin sudo, sysfs, debugfs, modulos,
  parametros, runtime, workloads, compilacion, parches ni fuentes web. Registrado en
  `RESEARCH-LINES.md` como `## 28.`; seccion `## 24.`, `## 26.` y `## 27.` intactas.
- **BLOQUE 1 — `MEC1_ONLY` global = INVALIDATED.**
  - `CLAIM-1` **PROVEN**: `amdgpu_gfx_compute_queue_acquire()` solo escribe bits en
    `[0,32)` — los dos unicos escritores (`amdgpu_gfx.c:224`, `:232`) no suman termino
    `mec`, y `max_queues_per_mec <= AMDGPU_MAX_COMPUTE_RINGS = 8 < 32`.
  - `CLAIM-2` **PROVEN**: el bucle `gfx_v8_0.c:1987-2003` con
    `is_mec_queue_enabled(adev,0,i,k,j)` y `ring->me = mec+1` (`:1857`) ⇒ `me = 1` en todo
    compute ring creado.
  - **Falsacion**: `amdgpu/amdkfd/amdgpu_amdkfd_gfx_v8.c` implementa un mecanismo
    **independiente**, sin leer ni escribir `mec_bitmap`:
    `lock_srbm` `:42-49` escribe `WREG32(mmSRBM_GFX_CNTL, PIPEID or MEID or VMID or
    QUEUEID)`; `acquire_queue` `:57-64` calcula `mec = (pipe_id/num_pipe_per_mec)+1`;
    `kgd_init_interrupts` `:112-129` programa `mmCPC_INT_CNTL`; `:172-180` escribe
    `mmRLC_CP_SCHEDULERS.scheduler1 = ((mec<<5) or (pipe<<3) or queue_id or 0x80)`;
    `:186-187` programa el HQD; `:408` limpia `scheduler1`.
    Con `num_pipe_per_mec = 4`: `pipe_id 0..3 → mec=1`, `pipe_id 4..7 → mec=2`.
    Clasificado `DRIVER_PATH_CAPABLE_OF_MEC2`, **no** `HARDWARE_CAPABILITY`.
  - **Corroboracion**: el codificado de `amdkfd_gfx_v8.c:179` es identico al de
    `gfx_v8_0_kiq_setting` (`gfx_v8_0.c:4300-4301`): dos implementaciones independientes
    del mismo contrato. Y `kgd_init_interrupts` programa el `mmCPC_INT_CNTL` de MEC2 que
    amdgpu se niega a hacer en `gfx_v8_0.c:6422-6424`, corroborando la particion de
    ownership de IRQ.
  - `MEC2_CAPABILITY` = **UNKNOWN**, conservado. Si `pipe_id >= 4` es alcanzable desde
    userspace/KFD queda **UNKNOWN** y como cuestion separada; no se convierte en
    afirmacion ni en implicacion de inalcanzabilidad.
  - **Correccion metodologica**: `MEC2_NOT_USED_BY_AMDGPU_7_1_3 = INVALIDATED`. Las
    formulaciones validas son `MEC2_NOT_USED_FOR_AMDGPU_USER_COMPUTE_QUEUES` y
    `MEC2_SELECTED_BY_KGD_LEGACY_GFX8_PATH` y `MEC2_SELECTED_BY_KIQ`, las tres `FACT`.
    Causa del error: en §25/§27 registre que el KIQ no es un compute ring y no extendi
    esa separacion a donde se situa el KIQ ni a la existencia de la capa KGD con modelo
    de direccionamiento propio. Leccion: `X no es Y` no implica `X irrelevante`.
- **BLOQUE 2 — cierre CGPG / queue 0.**
  `CGPG_JUSTIFICATION_IN_TREE = NOT_VERIFIABLE` · `QUEUE0_CAUSAL_ORIGIN = UNKNOWN` ·
  `QUEUE0_RESTRICTION = DRIVER_POLICY` · `POLICY_CAUSE = UNKNOWN`.
  `CGPG_SAVE`/`LOAD`/`RUN` = 0 ocurrencias en el arbol; `CGPG_IDLE` = 1, el propio
  comentario (`amdgpu_gfx.c:289`). No existe `PACKET3_CTXCTL_*`;
  `gfx_v8_ring_emit_cntxcntl` (`gfx_v8_0.c:6283-6314`) usa hex literales con nombres de
  context switch. `GDS_OA_CGPG_RESTORE__QUEUEID_MASK 0xf0000`
  (`gfx_8_1_sh_mask.h:17939`) demuestra que **existe** una codificacion CGPG con
  `QUEUEID`, pero `mmGDS_OA_CGPG_RESTORE` tiene **0** usos en `.c` de
  `drivers/gpu/drm/amd` y no conecta con el KIQ ni con `queue == 0` ⇒ `NOT_SUFFICIENT`.
  `RLC_PG_DELAY_3__CGCG_ACTIVE_BEFORE_CGPG` (histéresis, `gfx_v9_0.c:2981-2984`,
  `gfx_v10_0.c:8386`, `gfx_v11_0.c:5719`) y `PPSMC_MSG_SetGfxCGPG` existen sin operandos
  de cola ⇒ `NOT_SUFFICIENT`. `CAUSAL_LINK_PROVEN = NO`. Limite: resultado sobre
  **observabilidad causal en linux-7.1.3**, no afirmacion sobre hardware, RLC, PM4 ni
  especificacion del silicio; la ausencia de simbolos no se convierte en afirmacion sobre
  el hardware. El arbol no contiene `.git` ni especificacion.
- **BLOQUE 3 — cierre de observabilidad de page tables.**
  `OBSERVABILITY_STATUS = REQUIRES_NEW_INSTRUMENTATION` · `EXISTING_CHAIN = NONE` ·
  `MISSING_LINK = PDE -> leaf PT` · `ROOT_REQUIRED = YES` · `UAPI_SUFFICIENT = NO` ·
  `NEW_KERNEL_CODE_REQUIRED = NO` · `NEW_DEBUG_INSTRUMENTATION_REQUIRED = YES` ·
  `FINAL_EXPERIMENT_STATUS = BLOCKED_BY_MISSING_INSTRUMENTATION` ·
  `POLARIS12_CAPABILITY = NOT_DETERMINED` · `METHODOLOGY_STATUS = METHODOLOGY_REQUIRED`.
  `pd_address` identifica el root PD; `amdgpu_vram` permite leer un offset conocido pero
  no localizar la leaf PT; `amdgpu_bo_gpu_offset()` (`amdgpu_object.c:1474`,
  declarado en `amdgpu_object.h:308`) es capacidad interna, no interfaz UAPI. Verificado
  que no existe interfaz de lectura de hoja: `grep` de `leaf pt` / `pde.*leaf` en
  `amdgpu/*.c` y `*.h` da **0**. Desbloquear root/permisos/reboot no resuelve: falta el
  instrumento. Este bloqueo de observabilidad **no** se convierte en conclusion sobre
  capacidad de Polaris12.
  **Distincion con §26 (REMOVABILITY-02, linea paralela)**: §26 establece **como** se
  actualizan PDE/PTE (ruta SDMA `SDMA_OP_GEN_PTEPDE` frente a ruta CPU); este bloque
  establece si se puede **leer** una hoja. No se solapan ni se duplican.
- **Verificacion de la afirmacion de la capa KGD antes de registrarla**: la afirmacion
  sobre `amdgpu_amdkfd_gfx_v8.c` no provenia de mis rondas, por lo que se verifico antes
  de escribirla como `FACT` (fichero existente; formula en `:60`, `:118`, `:172`;
  `mmSRBM_GFX_CNTL` en `:48`/`:53`; `mmRLC_CP_SCHEDULERS.scheduler1` en `:177-180`/`:408`).
  Registrar sin verificar habria violado la separacion FACT/DERIVATION/UNKNOWN del
  proyecto.
- **Integridad de escritura**: temporal validado antes de anexar (0 CJK, 0 cirilico, 0
  U+FFFD, vallas pares). Tres celdas de tabla con pipes escapados `\|` se reescribieron
  sin pipes; 0 desajustes de columna en los 5 bloques. Una alerta de `filas_huerfanas`
  resulta ser **falso positivo**: es prosa de §28.1.2 con una expresion `|` dentro de
  código inline, no una fila de tabla; no se modificó.

## 2026-09-28 — RE-02 (RX550): pipe_id >= 4 — el HIQ de KFD lleva una cola interna al MEC2

- **Alcance**: segunda ronda de la auditoria de politica MEC1. Cierra el `UNKNOWN` que §28
  dejo abierto para `pipe_id >= 4`. Estatico sobre `RESEARCH/kernelbuild/linux-7.1.3` mas el
  subarbol KFD. Sin sudo, sysfs, debugfs, modulos, parametros, runtime, workloads,
  compilacion, parches ni fuentes web. Registrado en `RESEARCH-LINES.md` como `## 29.`;
  seccion `## 24.`, `## 26.` y `## 27.` intactas. **No reabre `CLAIM-1` ni `CLAIM-2`.**
- **Pregunta falsable**: para GFX8/Polaris12, puede el `pipe_id` que llega a
  `amdgpu_amdkfd_gfx_v8.c::kgd_hqd_load()` ser `>= 4`? Respuesta **B** (existe ruta). La
  opcion A es cierta solo para compute queues de usuario, y falsa como global.
- **Doble ruta, distinto comportamiento**:
  - compute queues de USUARIO: escritor `allocate_hqd()`
    (`kfd_device_queue_manager.c:764`), acotado por el bucle `i < get_pipes_per_mec` con
    `% get_pipes_per_mec` (`:755-756`) => `pipe` en `[0,3]` => `mec = 1`.
  - **HIQ** (cola interna del kernel): escritor `kfd_kernel_queue.c:144`, **constante**,
    que **evita** `allocate_hqd()` => `pipe = 4` => `mec = 2`.
- **Procedencia del extracto KFD**: el subarbol **NO** esta en
  `kernelbuild/linux-7.1.3` (`find -type d -name "kfd*"` -> vacio; tampoco
  `drivers/gpu/drm/amd/amdkfd/`). Si esta en
  `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/` (984 `.c`). Mismo arbol 7.1.3:
  4 ficheros presentes en ambos extracts son **byte-identicos** (SHA-256) `amdgpu_gfx.c`
  `36fd95baee2d02ac`, `amdgpu_amdkfd_gfx_v8.c` `77cbbb8bf7ab66c3`, `gfx_v8_0.c`
  `2427f5b5fcb44778`, `amdgpu_mes.c` `0d33fce14050c0b0`. **La premisa de §28 ("requiere
  instrumentacion de runtime") era mas restrictiva de lo necesario**: la cota no estaba en
  runtime, estaba en `allocate_hqd()`.
- **Cadena de evidencia primaria (HIQ)**: `kfd_device.c:1112` `kgd2kfd_resume_process` ->
  `:1128` `kfd_resume` -> `:1132` `node->dqm->ops.start` ->
  `kfd_device_queue_manager.c:2969` `dqm->ops.start = start_cpsch` -> `:1829`/`:1837`
  `pm_init` -> `kfd_packet_manager.c:279`/`:311`
  `kernel_queue_init(dev, KFD_QUEUE_TYPE_HIQ)` -> **`kfd_priv.h:89`
  `#define KFD_CIK_HIQ_PIPE 4`** -> **`kfd_kernel_queue.c:144`
  `kq->queue->pipe = KFD_CIK_HIQ_PIPE`** -> `:146` `load_mqd(..., pipe=4, ...)` ->
  `kfd_mqd_manager_vi.c:165` `kfd2kgd->hqd_load(adev, mqd, pipe_id=4, ...)` ->
  `amdgpu_amdkfd_gfx_v8.c:596` `.hqd_load = kgd_hqd_load` -> `:154`/`:166`
  `acquire_queue(adev, 4, queue_id)` -> **`:60` `mec = (4/4)+1 = 2`** -> `:45`
  `mmSRBM_GFX_CNTL = PIPEID or MEID(2) or VMID or QUEUEID` (`vid.h:71`, `MEID(x)=(x)<<2`) ->
  `:172-179` `mmRLC_CP_SCHEDULERS.scheduler1 = (2<<5) or (0<<3) or q or 0x80`.
  `num_pipe_per_mec = 4` (`gfx_v8_0.c:1910`) => la aritmetica no admite ambiguedad.
- **CORROBORACION (testigo interno del driver)**: `kfd_device_queue_manager.c:3703-3708`
  imprime `KFD_CIK_HIQ_PIPE / get_pipes_per_mec(dqm) + 1` bajo el rotulo
  `"   Inst %d, HIQ on MEC %d Pipe %d Queue %d\n"`. Para Polaris12 = `4/4+1 = 2`. El driver
  afirma en su propia salida que el HIQ vive en el MEC 2.
- **Limites clasificados por origen**:
  - **UAPI**: `include/uapi/linux/kfd_ioctl.h` tiene **0** ocurrencias de `pipe` y **0** de
    `KFD_QUEUE_TYPE_HIQ` => userspace no selecciona `pipe_id` y no puede pedir un HIQ.
  - **KFD**: cota del bucle `:755-756`; `get_pipes_per_mec()` `:108-111` = 4, desde
    `amdgpu_amdkfd.c:183` <- `gfx_v8_0.c:1910`; `next_pipe_to_allocate` = 0 (`:1516`) y
    mantido en `[0,3]` por `% 4` (`:776`); `is_pipe_enabled` invocado con `mec` fijo en 0
    (`:758`, `:86`).
  - **KFD + safety**: `allocated_queues = kcalloc(get_pipes_per_mec(), ...)` = 4 entradas
    (`:1509-1510`), indexado en `:761` => con `pipe >= 4` seria lectura fuera de limites.
    **La cota es safety-critical, no solo politica.**
  - **ASIC/GFX8**: `amdgpu_amdkfd.c:203-207` `last_valid_bit = 1*4*8 = 32` y limpia los bits
    `>= 32` de `cp_queue_bitmap` => 2o candado independiente para la ruta de usuario.
  - **AUSENCIA DE LIMITE**: el HIQ. `kfd_kernel_queue.c:144` es asignacion constante, sin
    validacion de rango.
- **Lo que el usuario puede y no puede hacer**: `MEC2_SELECTABLE_BY_USERSPACE =
  NOT_PROVEN` y **no por una limitacion, sino por diseno del UAPI**: no existe campo
  `pipe`. `MEC2_REACHABLE_FROM_USERSPACE = PARTIALLY_PROVEN`: userspace no selecciona pero
  si dispara, por `kgd2kfd_resume_process` con un proceso KFD adjunto.
  `SELECTABLE_BY_USER` y `REACHABLE_BY_TRIGGER` no se colapsan. **Formulacion admitida, y la
  unica**: existe una ruta KFD iniciada por el ciclo de ejecucion del dispositivo que lleva
  una **cola interna del kernel** al MEC2. **No** es "userspace selecciona MEC2". El HIQ no
  es un compute ring de usuario.
- **ESTADO CONSOLIDADO** (protocolo de auditoria | equivalente §2.3 del proyecto):
  `CLAIM-1` = `SURVIVES` | `PROVEN` · `CLAIM-2` = `SURVIVES` | `PROVEN` ·
  `CLAIM-3` = **`INVALIDATED`** · `MEC2_NOT_USED_BY_AMDGPU_7_1_3` = **`INVALIDATED`** ·
  `MEC2_SELECTABLE_BY_DRIVER` = `PROVEN` · `MEC2_REACHED_BY_KFD_KERNEL_PATH` = `PROVEN` ·
  `MEC2_SELECTABLE_BY_USERSPACE` = `NOT_PROVEN` ·
  `MEC2_REACHABLE_FROM_USERSPACE` = `PARTIALLY_PROVEN` | `PARTIALLY_SUPPORTED` ·
  `MEC2_CAPABLE_HARDWARE` = **`UNKNOWN`**. `SURVIVES` pertenece al protocolo de auditoria y
  `PROVEN` al vocabulario del proyecto: **no son sinonimos**, se registran ambos.
  `MEC2_REACHED_BY_KFD_KERNEL_PATH` es propiedad del **camino de software demostrado**;
  `MEC2_CAPABLE_HARDWARE` **no** se infiere de ella.
- **Correccion de alcance sobre `amdgpu_mes.c:151`**: el comentario ("only MEC1 is used for
  both kernel and user compute queue") **no** es evidencia de politica global. El `break`
  de `:156` gobierna solo el bucle MES; el HIQ es un kernel queue, no pasa por ahi, y opera
  en MEC2. `DOCUMENTAL`, alcance restringido a lo que gobierna.
- **`R-1 = EXHAUSTIVENESS_NOT_PROVEN`**, degradado a limitacion de completitud de inventario
  y **NO** a incertidumbre sobre el veredicto: `working/` es un subarbol parcial, sin
  `MANIFEST` y sin `kfd_queue.h`, y el subarbol amdkfd falta en `kernelbuild/`. La busqueda
  de escritores de `q->pipe` (`(->|\.)pipe\s*=[^=]`) devolvio 2. **Un tercer escritor no
  invalidaria el testigo**: `:144` es una asignacion constante, no un valor derivado, y no
  depende de la completitud del barrido.
- **LIMIT no verificado**: la rama del HIQ depende de `!shared_resources.enable_mes`
  (`amdgpu_amdkfd.c:190`); `start_nocpsch` solo llama `pm_init` para `CHIP_HAWAII`
  (`:1549-1556`). La condicion de `adev->enable_mes` para Polaris12 **no se inspecciono**:
  `NOT_VERIFIED_IN_THIS_PASS`.
- **CONSISTENT_WITH (no es prueba)**: el comentario de `amdgpu_gfx.c:288` ("Using pipes 2/3
  from MEC 2 seems cause problems") prohibe MEC2 pipes 2 y 3 y **permite** 0 y 1. Pipe 0 de
  MEC2 es donde se situa el HIQ. Coherente con cohabitacion deliberada.
- **Lo que §29 NO hace**: no investiga capacidad de silicio de MEC2; no reabre `CLAIM-1` ni
  `CLAIM-2`; no reaudita `mec_bitmap`, KIQ, MES ni `amdgpu_amdkfd_gfx_v8.c` como mecanismo
  (solo trazo la procedencia de `pipe_id` hasta el); no investiga por que AMD coloca el HIQ
  en el pipe 4; no convierte ningun `UNKNOWN` en `FACT`.
- **Hallazgo lateral, reportado y NO reparado** (fuera de alcance, sin efecto sobre esta
  evidencia): 3 contaminaciones CJK/cyrillicas preexistentes en `RESEARCH-LINES.md` —
  linea 1921 (alfabeto cirilico incrustado donde deberia ir "se ve"), linea 2785 (ideograma
  antes de `per-CPU`), linea 2873 (ideograma en "la frecuencia efectiva"); las tres
  cadenas se reproducen textualmente en `RESEARCH-LINES.md` y **no** se copian aqui para no
  reintroducir contaminacion en este log. Misma clase de fallo que el control de escritura
  de §27. No se tocan (§12.4: reportar, no reparar).
- **Concurrencia de escritura detectada en esta ronda** (relevante para el registro, no para
  la evidencia): `research_log.md` cambio de hash entre dos lecturas de esta misma sesion
  (`86f44ae3...` -> `81652fa2...`, mtime 08:58:30) porque la linea paralela anadio la
  entrada de §28. Se verifico estabilidad por hash antes de anexar y se confirmo que §28
  **no** se duplica. `RESEARCH-LINES.md` estaba estable (`533a51e6...`) y no fue tocado por
  la linea paralela.
- **Integridad de escritura**: en `RESEARCH-LINES.md`, 3 inserciones puras y 1 modificacion
  (marcador de estado que **conserva** el valor historico `UNKNOWN` en la fila de §28.4);
  6 tablas con conteo de columnas consistente; 0 vallas; 0 CJK/cirilico/U+FFFD introducidos.
  Se detecto y reparo 1 contaminacion CJK introducida en el propio borrador antes de anexar.
