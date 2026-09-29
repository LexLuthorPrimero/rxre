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
