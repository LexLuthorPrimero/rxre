# Decisiones de Fase 4 — Driver Exclusivo RX 550

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Iniciado**: 2026-09-29 · **Ronda**: 1 · **Última decisión**: `F4-AD-28` (Ronda 10)

Estados, según `AGENTS.md`: `DECIDIDO` · `PROPUESTO` · `ABIERTO` · `BLOQUEADO`.

---

## F4-AD-1 — Ámbitos disjuntos para 3 IAS

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: IA-1 `06-INGENIERIA-INVERSA/` · IA-2 `07-DRIVER/` · IA-3 `08-ARQUITECTURA/`.
- **Justificación**: elimina conflictos de edición entre IAS concurrentes.

## F4-AD-2 — Solo compute inicialmente, no gráficos

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: el driver inicial solo soporta compute.
- **Justificación**: reduce el alcance y permite un MVP realista.
- **Reserva**: el argumento "reduce 10x" es condicional a `F4-AD-6`. Si no hay inicialización
  de firmware reutilizable, el alcance real es mayor.

## F4-AD-3 — Stack completo propio, sin dependencia de `amdgpu.ko`

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` **con reserva mayor** — ver `F4-AD-6`.
- **Decisión**: `rx550.ko` no depende de `amdgpu.ko` en runtime.
- **Justificación**: si dependiera, no sería un driver "exclusivo".

---

## F4-AD-4 — El riesgo que domina el proyecto es el GAR, no el scheduler

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: la primera petición a IA-1 es si existe un camino de SPIR-V a ISA para GFX8
  **sin** `amdgpu`. Sin eso, el objetivo del proyecto no es alcanzable y hay que redefinir el
  MVP **antes** de escribir código.
- **Evidencia de lo que sí sabemos**: el hardware ejecuta el shader vía RADV con 0/4096 de
  discrepancias (`edd434b`, tag `v1.0-fase2-completa`). Lo que no está establecido es si puede
  hacerse sin RADV.

## F4-AD-5 — El MVP no puede ejecutar en la RX 550 sin autorización de sistema

- **Fecha**: 2026-09-29 · **Estado**: `BLOQUEADO`
- **Defecto**: un driver exclusivo exige que `amdgpu` no reclame `1002:699f`. Eso requiere
  `unbind` por sysfs, prohibido por `AGENTS.md` sin autorización expresa.
- **`OWNERSHIP`**: mientras `amdgpu` esté cargada, `OWNERSHIP != FULL`. `AGENTS.md` exige
  evidencia atribuible completa por identidad PCI, FDs, escritores, PM, governor, IRQ,
  scheduler, storage y Btrfs. Declarar `FULL` sería un error.
- **Delimito lo que invalida**: el criterio de éxito 6 (agreement test vía `librx550`).
- **NO invalida**: criterios 1–5, ring en CPU, validación de ioctl, empaquetado, tests de ABI.
- **Autorización que lo resuelve**: permiso humano explícito para desenlazar `1002:699f` y
  cargar `rx550.ko`, con restore garantizado.
- **Comunicación obligatoria**: sin esa autorización, el estado del proyecto se describe como
  *"el driver funciona pero no ejecuta shaders en la RX 550"*. Sin adornos.

## F4-AD-6 — F4-AD-3 choca con el firmware

- **Fecha**: 2026-09-29 · **Estado**: `BLOQUEADO` — depende de `@IA-1`
- **Conflicto**: la especificación pide a la vez «firmware: usar el del kernel» y «sin
  dependencia de `amdgpu.ko` en runtime». **Son incompatibles**: no se puede usar el firmware
  de `amdgpu` sin depender de `amdgpu`.
- **Lo que probablemente falta**: inicializar un GCN/RDNA desde cero exige PSP/SMU —blanqueo
  de stacks, descarga de firmware, formación de heaps, arranque del scheduler SMU. Ese trabajo
  vive hoy dentro de `amdgpu.ko`. **No afirmo** cómo de recuperable es; es `PENDIENTE-IA-1`.
- **Consecuencia**: el alcance del MVP depende de esto. Si resulta que hay que reimplementar
  PSP/SMU, el proyecto cambia de dimension y conviene saberlo antes de invertir.

## F4-AD-7 — Validar antes de comparar, y control negativo obligatorio

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**, heredada de tres incidentes medidos en esta fase:
  1. Una salida **entera a cero** produjo "0 discrepancias" y un falso `PASS`.
  2. Un test que imprimía `[FAIL]` por `stderr` devolvía **`rc=0`**: un CI reportaba verde.
     **Todo test de Fase 4 devuelve código distinto de cero ante fallo.**
  3. `shader_vs_c` no detectó ninguno de los tres bugs reales porque **modela** la aritmética
     en C en vez de compilar y ejecutar el GLSL. **Un emulador en CPU del GAR no sustituye a la
     ejecución real.**
- **Requisito de calidad**: el agreement test debe correr **sin modificar**. Si hay que tocarlo
  para que funcione con `librx550`, el diseño está mal.

## F4-AD-8 — Ningún offset sin fuente registrada

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: ningún offset de registro, tamaño de ring ni formato de descriptor se escribe
  en código hasta que venga de un fuente registrado: binario analizado, offset, contexto.
- **Origen**: AD-1. El coste de aprenderlo fue alto.
- **Estado actual**: `06-INGENIERIA-INVERSA/register-maps/gfx-v8-compute.md` es una **plantilla
  con todos los offsets vacíos** (`NOT_STARTED`). Ningún dato de ring está establecido.

---

## Peticiones a otras IAS

| # | Destinatario | Asunto | Bloquea | Estado |
|---|---|---|---|---|
| P-1 | `@IA-1` | ¿GAR reutilizable sin `amdgpu`? | viabilidad del MVP | `ABIERTO` |
| P-2 | `@IA-1` | Secuencia PSP/SMU | init del dispositivo | `ABIERTO` |
| P-3 | `@IA-1` | Offsets de ring, doorbell, CQ, IRQ | scheduler | `ABIERTO` |
| P-4 | `@IA-1` | Modo de addressing de VRAM en compute | 2 GiB no caben en 32 bits | `ABIERTO` |
| P-5 | `@IA-2` | Char device vs DRM | modo de acceso, ioctl | `ABIERTO` |
| P-6 | `@IA-2` | Campos de `IOCTL_SUBMIT_COMPUTE` | ABI | `ABIERTO` |
| P-7 | `@IA-2` | BOs propios vs TTM/GEM | GPUAddressing en el MVP | `ABIERTO` |
| P-8 | `@IA-2` | Fence: user/kernel, poll/IRQ | si se puede completar sin IRQ | `ABIERTO` |

P-1 y P-2 son **bloqueantes de arquitectura**. P-3 y P-4 son necesarios antes del scheduler.
P-5..P-8 bloquean la implementación pero no el diseño.

## Nota de procedencia

`AGENTS.md` prohíbe afirmar `OWNERSHIP=FULL` con evidencia parcial. Ninguna afirmación de este
registro se apoya en `lsof`, `fuser` ni en un escaneo parcial de `/proc`.


## F4-AD-9 — La via SPIR-V -> ISA esta BLOQUEADA en esta maquina

- **Fecha**: 2026-09-29 · **Estado**: `BLOQUEADO` — medido, no supuesto
- **Medicion** (esta host, clang 22.1.8, `-target amdgcn -mcpu=gfx803`):

| Via | Resultado |
|---|---|
| `clang -x spirv` | `language not recognized: 'spirv'` → **RECHAZADO** |
| `clang -x hlsl` | `HLSL code generation is unsupported for target 'amdgcn'` → **RECHAZADO** |
| `spirv-cross` (SPIR-V->HLSL) | **AUSENTE** en el host |
| `clang -x cl` (OpenCL C) | **FUNCIONA**: emite `.text` + `.AMDGPU.config` |

- **Consecuencia**: el camino propuesto para "`decompress_bc3.spv` (SPIR-V) -> ISA"
  **no esta disponible**. No es una cuestion de prioridad: ninguna de las tres rutas converge.
- **Implicacion**: el shader de Fase 2 **no es reutilizable tal cual**. Habria que
  **reescribirlo en OpenCL C** para que clang produzca ISA. Coste real, no estaba en el plan.
- **Mitigacion parcial**: la ISA es alcanzable por OpenCL C. Falta el **front-end** que convierta
  nuestro shader. `spirv-cross` es una opcion; **no esta autorizado** (instalar paquetes).
- **Lo que NO afirmo**: no se si `spirv-cross` convertiria este shader sin perdida. Usa SSBOs y
  push constants, y su soporte de push constants en HLSL es limitado. `NOT_DETERMINED`.

## F4-AD-10 — El firmware de Polaris 12 esta identificado por fuente primaria

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (dato) / `ABIERTO` (decision)
- **Dato verificado** en
  `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_cgs.c:325-332`,
  `case CHIP_POLARIS12:`:
  - revision P23 (kicker) -> `amdgpu/polaris12_k_smc.bin`
  - resto -> `amdgpu/polaris12_smc.bin`
- **Consecuencia para F4-AD-6**: el blob **existe y es especifico del chip**. La secuencia de
  carga sigue `PENDIENTE-IA-1`, pero ya sabemos **que** hay que cargar.
- **Decision abierta**: cargar el blob desde userspace (Opcion A) o depender de `amdgpu.ko`
  (Opcion B). **No es solo arquitectura**: la Opcion A evita la dependencia que `F4-AD-3`
  prohibe, y por tanto es la unica compatible con ella. La Opcion B contradice `F4-AD-3` y
  deberia rechazarse por esa razon, no por dificultad.

## F4-AD-11 — Fase 4A se redefine: volcar paquetes, no ejecutar

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decision**: mientras no haya autorizacion de `unbind` (F4-AD-5), el MVP no escribe en la
  GPU. Produce **paquetes en memoria para inspeccion**; el valor verificable es que el paquete
  tiene la estructura correcta.
- **Por que no es degradar el objetivo**: es **reordenar**. El objetivo sigue siendo 0/4096 en
  hardware (Fase 4B). Lo que cambia es que 4A no lo cubre, y hay que decirlo.
- **Limite honesto de 4A**: validar la estructura de un paquete **no** prueba que el hardware
  lo ejecute. Es el patron que hundio las Fases 1 y 2: un validador que confirma la forma sin
  ejecutar. Por eso 4B no es opcional, y el criterio 6 se mantiene vivo.


## F4-AD-12 — Formato definitivo del shader: OpenCL C

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: el shader de Fase 4 se escribe en **OpenCL C** y se compila con
  `clang -target amdgcn -mcpu=gfx803 -x cl`, produciendo un objeto ELF con `.text` y
  `.AMDGPU.config`.
- **Base**: medido en esta host (`F4-AD-9`). Es la **única** vía verificada que llega a ISA sin
  `amdgpu.ko`.
- **Consecuencia asumida y explícita**: `decompress_bc3.spv` **deja de ser el artefacto**. El
  agreement test de la Fase 2 (`test_decompress.c`) **no aplica** al formato nuevo. El criterio
  de éxito 6 queda **sin cobertura** hasta que exista un test equivalente para OpenCL C.
- **Qué se conserva**: el **algoritmo** (la decodificación BC3 verificada, 0/4096 con RADV) y el
  **corpus**. No el artefacto binario ni la interfaz.
- **Riesgo nuevo**: OpenCL C no tiene push constants. `num_blocks` pasa a argumento de kernel.
  Eso **cambia la firma** y obliga a un validador nuevo, escrito desde cero, que no existe.
- **Anti-patrón a evitar**: un validador nuevo escrito rápido y validado solo contra sí mismo es
  exactamente el fallo de `shader_vs_c` (F4-AD-7). Necesita control negativo desde el primer día.

## F4-AD-13 — Firmware: carga desde userspace (Opción A)

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: `librx550` lee el blob `polaris12_smc.bin` (`amdgpu_cgs.c:325-332`) y lo pasa al
  kernel por ioctl. `rx550.ko` **no** llama a `amdgpu.ko` para nada.
- **Por qué**: es la única opción **compatible con `F4-AD-3`**. La Opción B contradice `F4-AD-3`
  por definición, no por dificultad.
- **Pendiente IA-1**: formato del blob, secuencia exacta de carga, y si el estado inicial del
  hardware exige algo más. `PENDIENTE-IA-1`.
- **Nota**: extraer y analizar el blob es **independiente** del shader. No tiene por qué esperar
  a `F4-AD-12`.

## F4-AD-14 — `spirv-cross` no está disponible; no es una opción

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (dato)
- **Medición**: `dnf list --available spirv-cross` → **no hay paquete** en los repos activos.
  El paquete `spirv-tools` sí existe, pero es validación y desensamblado, **no conversión**.
- **Consecuencia**: la alternativa "instalar spirv-cross y no reescribir el shader" queda
  cerrada por indisponibilidad, no por preferencia. Habría que compilarlo desde fuente, lo que
  no está autorizado.
- **Corrección de un dato mío anterior**: en la ronda anterior reporté `spirv-val` como
  **ausente**. **Es falso**: `/usr/bin/spirv-val` (SPIRV-Tools v2026.1) está instalado y valida
  `decompress_bc3.spv` con `rc=0`. La limitación que escribí en `PROYECTO_STATUS.md` ("Esquema
  SPIR-V: NOT_AVAILABLE, falta spirv-val") es incorrecta y debe corregirse.

## F4-AD-15 — Orden de fases: el shader va antes que `unbind`

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: no solicitar autorización de `unbind` hasta que exista un shader en formato
  definitivo y validado.
- **Por qué**: con `F4-AD-9` bloqueado, el criterio 6 es inalcanzable de todos modos. Autorizar
  `unbind` ahora compra **riesgo de sistema** a cambio de un objetivo que sigue fuera de
  alcance.
- **Orden**: 1) formato del shader, 2) validarlo, 3) **entonces** pedir `unbind` para 4B.


## F4-AD-16 — El artefacto ELF no es cargable tal cual: hay relocaciones

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (medido)
- **Medición**: decodificador BC3 completo en OpenCL C, `clang -target amdgcn -mcpu=gfx803
  -x cl`, compila y produce `.text` (0x0aac B), `.rel.text`, `.AMDGPU.config`,
  `.AMDGPU.gpr_maximums`.
- **Hallazgo**: `.rel.text` trae **6 reubicaciones sin resolver**:
  - 2 × `R_AMDGPU_ABS32_LO` → `SCRATCH_RSRC_DWORD0`, `SCRATCH_RSRC_DWORD1`
  - 4 × `R_AMDGPU_REL32_LO`/`HI` → `_Z13get_global_idj`
- **Consecuencia para la 4A**: el paso de objeto ELF a código ejecutable es un **procesador de
  relocaciones**, no una volcadura a memoria. **«Volcar PM4 a memoria» subestimaba el trabajo.**
  `A5` entra en los criterios de la 4A (`002-opencl-c-validator.md` §7).
- **Pendiente IA-1** (`P-6`): si esas seis son las que espera el hardware en compute, si hay más
  obligatorias, y qué parseo exige `.AMDGPU.config`. **Esto bloquea la comprobación V4** del
  validador: sin el conjunto correcto, V4 sería un checksum de la salida de clang, no una
  propiedad del formato.
- **No afirmo** que esas seis sean suficientes. El kernel medido es pequeño; uno con LDS o
  atómicos tendría más. `NOT_DETERMINED` hasta P-6.

## F4-AD-17 — Tres capas de validación, separadas por diseño

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: el validador de Fase 4 se divide en capa 1 (algoritmo en CPU), capa 2 (forma del
  artefacto ELF) y capa 3 (agreement en GPU, **inexistente** hasta 4B).
- **Por qué separarlas**: la capa 1 no necesita driver ni hardware. Si falla, las otras dos son
  irrelevantes. Y la capa 3 se documenta como **inexistente**, no como «pendiente», para que
  nadie la cuente como cobertura.
- **Control negativo desde el primer commit**: N1 (`+3` eliminado), N2 (el bug real de Fase 2,
  `8*(cbyte-2)`), N3 (`.text` truncado). **N2 es el más valioso**: es el defecto que
  `shader_vs_c` no detectó. Si el test lo rechaza, tiene poder de discernimiento sobre el tipo de
  fallo que realmente ocurrió.
- **Riesgo declarado**: el artefacto de Fase 2 se validó **en la RX 550**; el de 4A no se
  validará en hardware hasta 4B. **No son resultados equivalentes** y no deben citarse como
  tales.


## F4-AD-18 — El conjunto de reubicaciones NO es fijo; V4 era incorrecta

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (medido)
- **Medición**: dos kernels, mismo compilador:
  - decodificador BC3 en OpenCL C → **6** reubicaciones
  - kernel con LDS + `barrier` + `atomic_add` + `atomic_or` → **22** reubicaciones
- **Símbolos que aparecen solo en el segundo**: `get_local_id`, `barrier`, `atomic_add`,
  `atomic_or`. `SCRATCH_RSRC_DWORD0/1` y `get_global_id` aparecen en ambos.
- **Consecuencia**: la comprobación V4 del validador **no puede ser «el conjunto es exactamente
  este»**. Debe ser **«todo símbolo reubicado pertenece al conjunto conocido, y cada uno está
  resuelto»**. Es comprobación de pertenencia, no de igualdad.
- **Autocorrección**: la versión de V4 que redacté en Ronda 4 era incorrecta. Queda corregida en
  `002-opencl-c-validator.md`.
- **Qué NO afirmo**: cuál es el conjunto completo que espera el hardware. Medido es el conjunto
  que *emite clang*, que no tiene por qué ser el que el hardware necesita. `PENDIENTE-IA-1`
  (`P-6`, punto 3).

## F4-AD-19 — `clang -target amdgcn` NO acepta `--amdhsa`

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (medido)
- **Medición**: `clang -target amdgcn --amdhsa` → `unknown argument: '--amdhsa'`. Con este
  clang (22.1.8) el flag no existe en el driver AMDGPU de compilación directa.
- **Consecuencia**: la variante que HADCODE líneas de shader para el runtime HSA no es accesible
  por esta vía. El artefacto es un objeto ELF con reubicaciones, tal como ya documenta
  `F4-AD-16`.
- **Comprobado también**: `--help` no lista ninguna bandera equivalente en este target. No lo
  doy por definitivo para otras versiones de clang; solo para la medida.


## F4-AD-20 — Fase 3 se disena ahora; NO requiere unbind (pregunta incorrecta)

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (medido)
- **Premisa que se me dio por cierta**: «la ejecución en hardware real sigue bloqueada por
  F4-AD-15 (requiere `unbind`)». **Es incorrecta**, y lo verifiqué antes de aceptar la tarea.
- **Medición**:
  - `vkcube --gpu_number 1` → `Selected GPU 1: AMD Radeon RX 550 (RADV POLARIS12)`, `rc=0`
  - `DRI_PRIME=1 glxgears` → `GL_RENDERER = AMD Radeon RX 550 (radeonsi, polaris12)`
- **Por qué**: Fase 3 mide el sampler **con el driver que ya está cargado**. `F4-AD-15` aplica al
  **driver propio de Fase 4**, que es otra cosa: reclamar el dispositivo en exclusiva. Son dos
  questions distintas y se confundieron.
- **Consecuencia**: **`AD-12` no está bloqueada.** Es ejecutable hoy con el host como está.
  `003-fase3-pipeline-grafico.md` define el experimento.
- **Lo que sí bloquea Fase 3, y es real, y NO es `unbind`**:
  - `VK_FORMAT_BC3_UNORM_BLOCK` como `SAMPLED_IMAGE`: **sin verificar** (es `F1`)
  - `VkImage` BC3 como attachment de render pass: **sin verificar**
  - GLX desde un programa propio: sin resolver (medido en ronda anterior)
- **Tres decisiones de diseño del experimento**:
  1. El fragment shader **no calcula nada**: solo `texture(sampler, uv)`. Si hiciera aritmética,
     un defecto del shader se confundiría con un defecto del sampler. `texture()` es opaco.
  2. El destino es un **FBO**, no un storage buffer: `imageStore` es escritura del shader, y con
     FBO el único escritor es el rasterizador, que es el sampler.
  3. El **predictor se escribe dos veces, de forma independiente**. Si comparte la fórmula con lo
     que se espera, el test **no puede** distinguir truncamiento de redondeo. Control `N4`.

## F4-AD-21 — Fase 3 es prerrequisito lógico de Fase 4B

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Cadena**: si el sampler **trunca** y mantenemos el redondeo (`F4-AD-12`), entonces el encoder de
  la Fase 1 y el sampler de la Fase 4 **no coinciden en la rampa**, y el agreement test de 4B **no
  puede dar 0/4096 por esa causa**.
- **No es un experimento paralelo**: si Fase 3 responde «truncamiento», `F4-AD-12` hay que
  reabrirla **antes** de escribir el shader OpenCL C.
- **Conexión que existe**: los **mismos bloques BC3** (`corpus_compressed.bin`, 1024 B, 64
  bloques) alimentan ambas fases.
- **Conexión que NO existe**: Fase 3 **no necesita nada de Fase 4** para ejecutarse. La
  dependencia es unidireccional: Fase 4B ← Fase 3.


## F4-AD-22 — REGLA DE OPERACIÓN: medir antes de aceptar la premisa

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Regla**: toda afirmación sobre capacidades del hardware, del toolchain o del estado del
  sistema debe verificarse empíricamente —con un comando o un script— **antes** de aceptarse como
  base del diseño. Las premisas teóricas son **puntos de partida para la medición**, no
  conclusiones.
- **Origen**: tres casos en este proyecto, todos con enunciado razonable y todos con la decisión
  cambiada por la medición:

  | Ronda | Premisa | Medición | Decisión que cambió |
  |---|---|---|---|
  | 2 | «clang mitiga el riesgo del GAR» | `clang -x spirv` y `-x hlsl` **rechazados**, `spirv-cross` ausente | `F4-AD-9`: la vía está **bloqueada** |
  | 4 | «son 6 reubicaciones» | un kernel con LDS y atómicos da **22** | `F4-AD-18`: V4 pasó a ser de **pertenencia**, no de igualdad |
  | 5 | «Fase 3 está bloqueada por `unbind`» | `vkcube --gpu_number 1` y `DRI_PRIME=1 glxgears` funcionan | `F4-AD-20`: `AD-12` **no** está bloqueada |

- **Por qué importa, y no es desconfianza**: en este proyecto las premisas **heredadas** se
  vuelven obsoletas cuando el entorno cambia —se instaló `vulkan-headers`, apareció una segunda IAS
  con un tree distinto—. Un diseño construido sobre una premisa no verificada hereda el error
  aunque la premisa pareciera sólida cuando se escribió.
- **Corolario práctico**: si la medición **no** se puede hacer, el estado correcto es
  `NOT_DETERMINED` **explícito**, no asumir el valor más plausible. Aplicado ya a `V4`
  (`P-6` sin respuesta) y a `PGM_RSRC1`.
- **Corolario para revisión**: cuando un documento afirme una capacidad, la revisión debe exigir
  el comando que la demuestra. Una afirmación sin comando reproducible es una hipótesis.

## F4-AD-23 — El probe de capacidad debe abortar, no continuar con otro dispositivo

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Decisión**: el probe F1 **aborta** si no encuentra `1002:699f`. No continúa con el primer
  dispositivo disponible.
- **Por qué**: esta host expone iGPU, AMD y **llvmpipe**. llvmpipe implementa BC3 en software y
  reportaría `SAMPLED_IMAGE`, produciendo un **falso positivo** que invalidaría la medición de
  `AD-12` sin ningún síntoma visible.
- **Segunda barrera**: `V-A`..`V-D` en `004-fallback-sin-rasterizador.md` §4, incluido un chequeo
  explícito de que el dispositivo **no** es llvmpipe.
- **Precedente**: el agreement test de la Fase 2 ya identifica por PCI identity por el mismo
  motivo, y lo documentó en su salida.


## F4-AD-24 — REGLA DE OPERACIÓN: citar el commit de origen de todo dato cruzado

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO`
- **Contexto**: se cancela el protocolo de cerrojos y se trabaja en paralelo sobre ámbitos
  disjuntos. Eso resuelve los conflictos de **fichero**, que `git merge` detecta. **No** los de
  **contenido**: un documento puede afirmar un dato que otra IA cambió sin que nada lo señale.
- **Regla**: un dato que provenga del trabajo de otra IA se cita **con su commit de origen**. Si no
  lo mediste o verificaste tú en esta ronda, no lo escribas como hecho absoluto.
- **Tres grados**: `medido por mí` (con el comando que lo demuestra) · `citado` (con commit) ·
  `supuesto` (`NOT_DETERMINED`, con la razón). El tercero es el que se olvida y es el que más
  cuesta.
- **Costo real en este proyecto**:
  - `b8294b1` afirmaba que la ruta de cómputo Vulkan no funcionaba en el host. **Falso**: era un
    bug mío de structs declaradas a mano. Corregido en `AD-14`.
  - `test_alpha_ramp` afirmaba conformidad con bcdec; `AD-11` cambió la regla de la rampa y el test
    quedó obsoleto.
  - En ambos casos el documento se quedó con toda la confianza y **sin ninguna marca de caducidad**.
- **Regla de mantenimiento**: al terminar un turno, `git log` sobre los ficheros citados. Si alguno
  cambió desde que lo escribí, corrijo la cita o la marco obsoleta. Son treinta segundos.
- **Documento**: `designs/005-regla-citacion.md`.
- **Lo que NO es**: no es ceremonia, no impide el paralelismo, no sustituye a medir. Solo cambia una
  línea de cómo se escribe un dato. Es la única defensa posible contra la contradicción silenciosa:
  `git merge` detecta ficheros, `grep` no detecta mentiras.

## F4-AD-25 — Aplicación de `F4-AD-24` a mi propio trabajo, con dos autocorrecciones

- **Fecha**: 2026-09-29 · **Estado**: `DECIDIDO` (medido)
- **Por qué esta decisión existe**: `F4-AD-24` dice «cita lo que no mediste». La primera aplicación
  honesta de esa regla es aplicársela a uno mismo. Al revisar `004` y `003` con la regla activa
  aparecieron **tres** afirmaciones propias que no estaban sustentadas como escritas.
- **Autocorrección 1 — el orden de enumeración de dispositivos estaba invertido**. `004` §3.1
  listaba `[0]` = RX 550, `[1]` = Intel, `[2]` = llvmpipe. Medido (`vulkaninfo --summary`):
  el orden real es **iGPU(0) → RX 550(1) → llvmpipe(2)**. El documento acertaba al exigir filtro
  por PCI y se equivocaba en el ejemplo, y el ejemplo es lo que se copia. Un probe escrito
  copiando el ejemplo habría medido la Intel. Corregido en `004` §2.1.
- **Autocorrección 2 — `004` §5.1 trataba `STORAGE_IMAGE` como riesgo, no como ausencia**.
  `VK_FORMAT_FEATURE_STORAGE_IMAGE_BIT` **no está** en `VK_FORMAT_BC3_UNORM_BLOCK` para
  `1002:699f` (medido). El fallback por compute `imageLoad` no es una vía arriesgada: es
  `NOT_AVAILABLE`. Reclasificado.
- **Autocorrección 3 — `004` §3 no fijaba el tiling de la imagen**, y `linearTilingFeatures` de
  BC3 **no** incluye `SAMPLED_IMAGE` (solo `COPY_IMAGE_INDIRECT_DST_BIT_KHR`). Sin el requisito
  `VK_IMAGE_TILING_OPTIMAL`, el camino principal de `003` §3 fallaría de forma no obvia.
  Requisito añadido (`004` §5.6, comprobación `V-E`).
- **Consecuencia de fondo**: la regla no es un ritual de formato. Aplicada a documentos ya
  escritos, encontramos tres errores **reales**, dos de ellos en un documento que iba a ser la
  especificación que IA-2 implementaría. La regla capturó lo que la revisión normal no capturó.
- **Cumplimiento** (medido): `DOCUMENTATION-ROUTER.md` §3bis (commit `ad4d08b`, **fuera de mi
  ámbito**) afirma que Vulkan/RADV en `HOST-C` es `NOT_AVAILABLE` porque `mesa-vulkan-drivers` no
  está instalado. Es **falso**: `rpm -qf /usr/lib64/libvulkan_radeon.so` →
  `mesa-vulkan-drivers-freeworld-26.2.3-1.fc44.x86_64`, y RADV enumera `1002:699f` y responde
  consultas de formato. Tercer caso del patrón «se comprueba un vecino, no el objeto» que
  `AGENTS.md` §Falsificación ya documenta dos veces. **Reportado, no reparado**: `01-AUDITORIA/`
  no es mi ámbito. La decisión que sí tomo es no citar §3bis como autoridad sobre el estado de
  Vulkan en este host.

## F4-AD-26 — La Regla de Citación, formalizada

- **Fecha**: 2026-09-29 · **Ronda**: 8 · **Estado**: `DECIDIDO`
- **Origen de la petición**: la regla fue propuesta por IA-1 en
  `reviews/2026-09-29-amendment-citation-rule.md` (commit `35c2a45`) y registrada por mí como
  `F4-AD-24` (commit `939155b`). Esta decisión la **formaliza** y le añade la parte que faltaba.
- **Texto de la regla**:

  > **Todo dato proveniente de otra IA debe citarse con su commit/fuente. Si no lo mediste vos,
  > no lo escribas como hecho absoluto.**

- **Los tres grados**, y la obligación de declarar cuál:

  | Grado | Qué es | Cómo se escribe | Obligación |
  |---|---|---|---|
  | **Medido por mí** | lo verifiqué yo, en esta ronda | afirmación directa + **el comando que lo demuestra** | el comando es lo que la hace auditable |
  | **Citado** | viene del trabajo de otra IA | «Según IA-N (commit `abc123`), X» | el hash es la marca de caducidad |
  | **Supuesto** | nadie lo ha medido | `NOT_DETERMINED` + la razón | es el que se olvida y el que más cuesta |

- **Lo que esta decisión añade sobre `F4-AD-24`**: `F4-AD-24` decía «cita el commit». No decía
  **qué hacer con los datos que no son de otra IA y que tampoco he medido**, que es el caso
  habitual. Por eso el tercer grado no es opcional: un dato propio no verificado es exactamente
  el que `F4-AD-22` prohíbe presentar como capacidad del host.
- **Un dato que no es mío y que tampoco he medido se escribe `NOT_DETERMINED`, no «según el
  sentido común»**. La historia de esta regla en el proyecto demuestra el coste: el orden de
  dispositivos invertido (`F4-AD-25`) llevaba dos rondas sin que nadie lo notara, porque se
  escribía como hecho y se leía como hecho.
- **Alcance**: aplica a **todo** dato de todo documento de `08-ARQUITECTURA/`, incluidos los
  valores «de fuente primaria» (un número de `vulkan_core.h` sin número de línea y sin versión
  del paquete es un dato no verificable).
- **Mantenimiento**: al terminar un turno, `git log` sobre los ficheros citados. Si alguno cambió
  desde que lo escribí, corrijo la cita o la marco obsoleta. Registrado en `005` §6.
- **Documento de aplicación**: `designs/005-regla-citacion.md` (patrones y ejemplos) y
  `designs/004-fallback-sin-rasterizador.md` §9 (tabla de procedencia completa, aplicada).

## F4-AD-27 — `P-9` resuelto: la hipótesis rival estaba mal formulada

- **Fecha**: 2026-09-29 · **Ronda**: 9 · **Estado**: `DECIDIDO` (medido, con salvedad)
- **La pregunta que `004` §6 hacía**: «¿cómo se **verifica** que la decodificación la hizo el
  hardware?». Es la formulación equivocada, y por eso parecía irresoluble: `AGENTS.md` §
  Falsificación no pide *demostrar*, pide **nombrar la observación que refutaría la hipótesis
  rival**. Sin rival nombrado no hay criterio de éxito, y «no veo señales de software» no es
  una medida.
- **La hipótesis rival real**: no es «el driver puede decodificar BC3 en software». Es
  «**el contexto creado no es el que creemos**».
- **Medición** (`grep`, 2026-09-29):
  ```
  $ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/gallium/drivers/radeonsi/  → 0
  $ grep -rn "dxt5_rgba\|dxt5_srgba\|u_format_s3tc" src/amd/vulkan/               → 0
  ```
  Mesa 26.2: `radeonsi` y `RADV` **no contienen descompresor BC3 en CPU**. El único
  decodificador por software está en el camino de `llvmpipe`
  (`src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c`), que es **otro driver**, no una ruta
  alternativa dentro de radeonsi. Un contexto radeonsi no tiene a dónde caer.
- **Trampa que casi produce un diagnóstico falso**: `radeonsi` tiene funciones llamadas
  `gfx6_decompress_textures` y `si_decompress_color_texture` que **no** son de BC3 — son
  *fast-clear* (CMask/FMASK/DCC). La guarda en `si_blit.c:568-571` lo dice, y el
  `assert(sctx->gfx_level < GFX11)` en `:567` lo confirma. Un grep de `decompress` en radeonsi
  genera una advertencia falsa.
- **Hallazgo que da valor al experimento**: la aritmética de `llvmpipe`
  (`lp_build_lerpdxta`, `lp_bld_format_s3tc.c:817-877`) no es ni truncamiento ni redondeo.
  Reproducida y comparada sobre los **136 686** pares donde spec y trunc difieren:
  | llvmpipe coincide con… | Pares | % |
  |---|---|---|
  | spec `+3`/`+2` | 42 170 | 30.8 |
  | truncamiento (bcdec) | 93 867 | 68.6 |
  | **ninguna de las dos** | **649** | **0.47** |
  Ese tercer conjunto es un **discriminante conocido y calculable sin GPU**. Convierte la idea
  débil de `004` §6 («si coincide con llvmpipe, es sospechoso») en un control con poder de
  discernimiento: requiere `V-H`.
- **Consecuencia**: `P-9` **no bloquea** el camino principal (Vulkan selecciona por PCI identity
  en el propio programa, sin depender de `DRI_PRIME`) ni la Opción C (cubre `GL_RENDERER` con
  `V-A` más el predictor llvmpipe con `V-H`). Ninguna vía queda bloqueada por `P-9`.
- **Vías descartadas y por qué**: `vkGetBufferDeviceAddress` responde a «¿la dirección es de
  dispositivo?», no a «¿quién decodificó?». Los timeline semaphores miden orden de submits, no
  el origen aritmético de un texel. **Latencia**: no concluyente por sí sola, y medirla exige
  benchmark — prohibido por `AGENTS.md` §Safety sin autorización.
- **Salvedad que impide llamarlo `OBSERVED` para este host**: el árbol leído es
  `/home/lucas/mesa` = `26.1-branchpoint-1415-gc5e413533f4` (`VERSION 26.2.0-devel`); el driver
  instalado es `mesa-dri-drivers-26.2.3-1.fc44`. Misma serie menor, **commit no verificado
  igual**. La conclusión es `PLAUSIBLE` para el binario en ejecución. Petición `Q-3` en `006`
  §10: `nm -D`/`strings` sobre `radeon_dri.so` y `libvulkan_radeon.so`.
- **No resuelve `AD-12`**: `P-9` era sobre la interpretabilidad del experimento; la medición de
  la rampa sigue siendo Fase 3.
- **Documento**: `designs/006-p9-hardware-vs-software.md`.

## F4-AD-28 — Cierre formal de Fase 3: qué queda cerrado y qué no

- **Fecha**: 2026-09-29 · **Ronda**: 10 · **Estado**: `DECIDIDO` (cierre de diseño, no de
  medición)
- **Qué significa este cierre**: la **infraestructura de diseño** de Fase 3 está cerrada y
  verificada. La **medición de `AD-12` no está hecha**. Estas dos cosas se han viene confundiendo
  en los intercambios, y la confusión produce un estado que parece más avanzado de lo que es.

### 1. Cerrado y verificado

| # | Elemento | Evidencia | Commit |
|---|---|---|---|
| 1 | `VK_FORMAT_BC3_UNORM_BLOCK` soporta `SAMPLED_IMAGE` en `1002:699f`; `optimalTilingFeatures = 0xd401` | `vulkaninfo --show-formats`, sha256 `5ff5762b…fffd` | `9277e3c` |
| 2 | La `VkImage` BC3 debe ser **`VK_IMAGE_TILING_OPTIMAL`** — `linearTilingFeatures` no tiene `SAMPLED_IMAGE` | misma medición | `9277e3c` |
| 3 | Orden real de dispositivos: iGPU(0) → RX550(1) → llvmpipe(2). Los **tres** reportan `SAMPLED_IMAGE` | `vulkaninfo --summary` | `9277e3c` |
| 4 | `F4-AD-23` justificado empíricamente: elegir por índice acertaría **por accidente** | ídem | `9277e3c` |
| 5 | `radeonsi` y `RADV` **no** tienen descompresor BC3 en CPU → la hipótesis rival no es la de `P-9` | `grep`, 2 búsquedas, 0 resultados | `1e28733` |
| 6 | `gfx6_decompress_textures` / `si_decompress_color_texture` son **fast-clear**, no BC3 | `si_blit.c:568-571`, `assert(:567)` | `1e28733` |
| 7 | La aritmética de llvmpipe difiere de spec **y** de trunc en **649** triplas `(a0,a1,i)`, con los tres valores esperados | Python con los tipos del fuente, incl. wrap i16 | `5c02833` |
| 8 | Los 649 bloques BC3 están codificados y verificados (posición del índice, color negro, UV) | 0 fallos de 649 | `5c02833` |
| 9 | `P-9` no bloquea ninguna vía: la hipótesis rival es «contexto equivocado» y la cubren `V-A`/`V-B`/`V-H` | `006` §1, §4 | `1e28733` |

### 2. Criterio de pase — cuatro ramas, `rc` distinto de cero en todas salvo el acierto

**El test mide `AD-12`; no lo presupone.** Un criterio que presupusiera la respuesta declararía
fallo un hardware que funciona bien. En las 649 triplas, por construcción,
`spec ≠ trunc ≠ llvmpipe`, luego las tres ramas son excluyentes:

| Resultado en las 649 | Interpretación | `rc` |
|---|---|---|
| uniforme en `spec`, **cero** en `llvmpipe` | hardware, redondeo `+3`/`+2` — `AD-11` confirmado en hardware | `0` |
| uniforme en `trunc`, **cero** en `llvmpipe` | hardware, truncamiento — `AD-11` **refutado** en hardware | `1` |
| reparto mixto `spec`/`trunc`, o ninguno de los tres | regla distinta; `NOT_DETERMINED`, se reporta sin forzar | `2` |
| **cualquier** caso en `llvmpipe` | `CONTAMINATED_LLVMPIPE` — fallo del entorno, **no** propiedad del hardware | `3` |

**Regla que decide el paso**: uniforme en `spec` **o** uniforme en `trunc`, y **cero** en
`llvmpipe`. `AD-12` es la consecuencia del test, no su premisa.

**`rc` distinto de cero ante cualquier fallo** es obligatorio, no una recomendación: en este
proyecto un test que imprimía `[FAIL]` por `stderr` devolvía `rc=0` y un CI reportaba verde
(`F4-AD-7` §2). Comprobación `V-G`.

### 3. `VK_FILTER_NEAREST` — requisito obligatorio, no preferencia

**Cambio respecto a `003` §3, que especificaba `LINEAR` sin justificarlo.**

Con `LINEAR`, el sampler **además** de decodificar el bloque interpola espacialmente entre texels
vecinos. Esa aritmética adicional:

- destruye el aislamiento del índice `i` en la posición `p` — el valor leído ya no depende solo
  del bloque y del código de índice;
- es exactamente la aritmética que `AD-12` **no** quiere medir.

`SAMPLED_IMAGE_FILTER_LINEAR_BIT` **está presente** en `0xd401`, luego `LINEAR` es perfectamente
legal — y por eso el fallo sería **silencioso**: el test correría, devolvería números, y serían
incorrectos sin ninguna señal. `NEAREST` aísla la decodificación del bloque.

### 4. Dependencias externas — `AD-12` sigue `NOT_DETERMINED` hasta que se resuelvan

| # | Dependencia | Responsable | Qué bloquea |
|---|---|---|---|
| `Q-5` | Validar `expect_llvmpipe` contra el decodificador **real** de llvmpipe, no contra mi modelo Python | `@IA-1` | la validez de los 649. Mi transcripción de `lp_build_lerpdxta` es una **reimplementación**, no una ejecución |
| `Q-3` | `nm -D`/`strings` sobre `radeon_dri.so` y `libvulkan_radeon.so` | `@IA-1` | convierte `PLAUSIBLE` en `OBSERVED` para el binario instalado (el árbol leído es `26.1-branchpoint-1415-gc5e413533f4`; el driver es `26.2.3-1.fc44`) |
| commit de fuentes de `04-IMPLEMENTACION/` | — | `@IA-2` | reproducibilidad del corpus |
| autorización de carga de GPU | humano | — | ejecutar la medición en la RX 550. `AGENTS.md` §Safety |

**`Q-5` es la dependencia dura.** Si mi transcripción tiene un error, los 649 casos son los
equivocados y el test no discrimina nada — con apariencia de funcionar. El test de `Q-5` tiene
poder de fallar: si un `expect_llvmpipe` estuviera mal, la comparación lo dice.

### 5. Hallazgo de esta ronda — el error de IA-1 es real pero inocuo

`06-INGENIERIA-INVERSA/findings/015-llvmpipe-discriminating-pairs.md` (sin commitear al momento
de escribir esto) calcula `weight7 = 255*64/7 = 2330`. El valor entero es **2331**
(`16320/7 = 2331 r3`). **IA-1 se equivocó.**

Lo comprobé porque el número importa: es el peso de la rampa de 8 valores.

**Verificación del impacto**, sobre las 195 840 triplas de la rama `a0 > a1` (las únicas donde
`weight7` se usa):

```
triplas donde w7=2330 vs w7=2331 cambia el resultado: 0
  i=2: w(2331)=36  w(2330)=36  IGUALES
  i=5: w(2331)=145 w(2330)=145 IGUALES
  i=7: w(2331)=218 w(2330)=218 IGUALES
```

`2330·(i−1) >> 6` y `2331·(i−1) >> 6` coinciden para todo `i` de 2 a 7. **Los 649 casos del
commit `5c02833` no cambian**, y el clasificador de IA-1 tampoco, siempre que use el mismo
`>> 6`.

**Lo que sí hay que corregir** es la transcripción en el documento, no el corpus: publicar
`2330` como el valor de la constante es un dato falso en la documentación, del mismo tipo que los
ya registrados en `AGENTS.md` §Falsificación. La clasificación correcta del defecto es
`NON_BLOCKER` para el corpus y **defecto documental** para `015`.

**No he corregido `015`**: es ámbito de `06-INGENIERIA-INVERSA/`. Lo reporto.

### 6. Lo que este cierre NO declara

- **No** declara `AD-12` resuelto. Sigue `NOT_DETERMINED`.
- **No** declara que la GPU ejecuta el shader de Fase 3. Nadie lo ha ejecutado.
- **No** declara `OWNERSHIP != FULL` en ningún sentido; `F4-AD-5` sigue vigente y `unbind` no
  está autorizado.
- **No** repara el `CONFLICT` del router sobre el estado de Vulkan en `HOST-C`, reportado en
  `9277e3c` §6 y pendiente de quien mantenga `01-AUDITORIA/`.
- **No** cierra `P-1`…`P-8` (peticiones a otras IAS en `F4-AD-6` y §«Peticiones»).
- **No** toca el cerrojo ajeno ni `COORDINACION.md`.
