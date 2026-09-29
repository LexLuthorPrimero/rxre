# Decisiones de Fase 4 — Driver Exclusivo RX 550

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Iniciado**: 2026-09-29 · **Ronda**: 1

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
