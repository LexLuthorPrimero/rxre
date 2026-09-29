# Arquitectura del Driver Exclusivo RX 550

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 1
**Estado**: borrador de arquitectura, pendiente de input de IA-1 e IA-2

> **Disciplina de escritura.** Este documento define **interfaces, responsabilidades y
> criterios de éxito**. No afirma ningún offset de registro, tamaño de ring, formato de
> descriptor ni secuencia de inicialización. Eso depende de ingeniería inversa y va marcado
> `[PENDIENTE-IA-1]`. Es la lección de AD-1: un offset escrito de memoria es un cuelgue
> silencioso, y el coste de la lección fue alto.

---

## 1. Objetivo en una frase

Driver mínimo que permita ejecutar compute shaders BC3 en la RX 550 (Polaris 12, GFX8, PCI
`1002:699f`) sin dependencias de `amdgpu.ko` ni RADV en runtime.

**Criterio que demuestra que se ha cumplido**, y que es el mismo de Fase 2:
`make test-gpu` da **0 de 4096 bytes discrepantes** entre el shader ejecutado por
`librx550` y `rx550_decompress_block()`, sin modificar una línea del test.

## 2. Stack a reemplazar

| Capa | Actual | Objetivo |
|---|---|---|
| Kernel | `amdgpu.ko` | `rx550.ko` |
| Userspace | `libdrm_amdgpu` + RADV + Vulkan loader | `librx550` |
| Firmware | PSP/SMU de `amdgpu` | **sin decidir** — ver §7 |

**Lo que NO se reemplaza en el MVP**: PCIe, APM, power state, reset, display. Eso sigue en
`amdgpu`. Ver F4-AD-2.

### 2.1 Tensión no resuelta entre F4-AD-2 y F4-AD-3

`F4-AD-3` decide que `rx550.ko` no dependerá de `amdgpu.ko` en runtime. `F4-AD-2` razona que
limitarse a compute reduce el alcance "10x".

**Estas dos son incompatibles en un punto que aún no está puesto**: inicializar un GCN/RDNA
desde cero exige la secuencia de carga de firmware **PSP/SMU** —blanqueo de stacks, descarga de
firmware, formación de heaps, arranque del scheduler SMU. Sin esa secuencia la GPU no
inicializa y **no hay compute que despachar**. Ese trabajo vive hoy dentro de `amdgpu.ko`.

Consecuencias honestas:

- "Scope 10x menor" **solo es cierto** si se puede reutilizar la inicialización de firmware de
  alguna forma. Sin ella, el alcance real es mayor, no menor.
- La especificación dice a la vez "Firmware: ninguno propio (usar el del kernel si es
  necesario)" y "sin dependencia de `amdgpu.ko` en runtime". **Son incompatibles**: no se
  puede usar el firmware de `amdgpu` sin depender de `amdgpu`.
- **No afirmo** que la secuencia exacta sea recuperable del módulo, ni cómo. Es
  `[PENDIENTE-IA-1]`, y es probablemente **la pregunta más importante de la ronda 2**, por
  encima de los offsets de ring.

## 3. Componentes del driver

### 3.1 Kernel (`rx550.ko`)

| Componente | Responsabilidad | Riesgo |
|---|---|---|
| Dispositivo | nodo de carácter `/dev/rx550` (frente a DRM: §7) | bajo |
| `IOCTL_VERSION` | versionado de ABI; el kernel rechaza si no coincide | **alto** — sin esto, desalineación silenciosa |
| `IOCTL_DEVICE_INFO` | identidad PCI, capabilities, VRAM, heaps | bajo |
| Ring manager | 1 ring de compute en el MVP | medio |
| Command submission | PM4/packets al ring | **crítico** `[PENDIENTE-IA-1]` |
| Shader cache | SPIR-V → ISA (GAR) y Lookup por hash | **crítico** — ver §3.3 |
| BO manager | reserva y mapa de VRAM | medio |
| Fence | sincronización submit→completado | medio |
| Reset | fuera de alcance | — |
| Reclamación del bus PCI | fuera de alcance: se asume exclusividad declarada | **crítico** — ver §5.1 |

**El riesgo crítico no es el ring, es el GAR** (§3.3).

### 3.2 Userspace (`librx550`)

```
rx550_open() / rx550_close()
rx550_load_spirv(const void *spv, size_t len, rx550_shader_t *out)
rx550_submit_compute(rx550_shader_t, const rx550_submit_desc_t *desc)
rx550_wait_fence(rx550_fence_t, uint64_t timeout_ns)
rx550_readback(rx550_bo_t, void *dst, size_t len, size_t offset)
```

Responsabilidades: validación del SPIR-V en userspace antes de subirlo, caché de shaders,
traducción de un nivel superior a los ioctls. **El kernel no interpreta SPIR-V.**

El SPIR-V es el de Fase 2, ya compilado y verificado:
`04-IMPLEMENTACION/decompressor/decompress_bc3.spv`. No se reescribe.

### 3.3 Shader integration — el riesgo que domina el proyecto

GFX8 no tiene compilador de shaders público. Tres caminos posibles:

| Camino | Coste | Riesgo |
|---|---|---|
| **(A) Reutilizar el GAR de `amdgpu.ko`** | bajo | contradice F4-AD-3 |
| **(B) Reutilizar LLVM/RADV** | medio |dejaría de ser "driver exclusivo" |
| **(C) Escribir el backend ISA** | muy alto | **puede ser mayor que el driver** |

**Lo que sí está establecido por evidencia propia** (commit `edd434b`, tag
`v1.0-fase2-completa`): el hardware **ejecuta** `decompress_bc3.comp` en la RX 550 vía RADV y
produce 0/4096 de discrepancias. Lo que **no** está establecido es si puede hacerse sin RADV.

**Por eso P-1 a IA-1 es la primera pregunta de la ronda.** Si la respuesta es "no hay camino
viable sin reutilizar el GAR de `amdgpu`, el MVP debe redefinirse antes de escribir código", y
eso es mejor saberlo en la ronda 2 que en la semana 6.

## 4. Path de submit de comandos

```
 1. userspace  rx550_submit_compute(shader, desc)
 2. ioctl      RX550_IOCTL_SUBMIT_COMPUTE
 3. kernel     valida abi_version, cmd, arg_size contra el máximo del comando
 4. kernel     localiza el shader en caché (hash del SPIR-V)
 5. kernel     escribe el paquete de trabajo en el ring de compute   [PENDIENTE-IA-1]
 6. kernel     publica el WPTR y hace doorbell                      [PENDIENTE-IA-1]
 7. hardware   SDMA drena el ring y ejecuta el dispatch
 8. hardware   actualiza el WDDM o genera la interrupción de cola    [PENDIENTE-IA-1]
 9. kernel     marca el fence y despierta al waiter
10. userspace  rx550_wait_fence() → rx550_readback()
```

Puntos abiertos, todos `[PENDIENTE-IA-1]`:

- Estructura del header de paquete y del descriptor de dispatch.
- Offsets MMIO de `CP_RB_BASE`, `CP_RB_WPTR`, `CP_RB_CNTL`, `CP_START`.
- Semántica de doorbell y si el ring envuelve correctamente.
- Mecanismo de interrupción: qué registro de CQ hay que limpiar y cómo se limpia.

**Regla dura heredada de Fases 1 y 2**: ningún offset se escribe en código hasta que venga de
un fuente registrado, con el binario analizado, el offset y el contexto. Igual que en AD-1.

## 5. MVP — criterios de éxito

| # | Criterio | Cómo se verifica | Ejecutable sin autorización de sistema |
|---|---|---|---|
| 1 | `rx550.ko` carga y crea `/dev/rx550` | `dmesg`, `ls -l /dev/rx550` | sí |
| 2 | `IOCTL_VERSION` responde correctamente | test de ioctl, incluido ABI mismatch | sí |
| 3 | Se puede submitir un compute shader simple | fence completa sin timeout | sí |
| 4 | El shader escribe en memoria legible desde CPU | lectura y verificación del valor | sí |
| 5 | Fence retorna al completarse | test de `wait` con timeout | sí |
| 6 | `decompress_bc3.comp` da **0/4096** vía `librx550` | `make test-gpu` sin modificar | **NO** — ver §5.1 |

### 5.1 Por qué el criterio 6 no es ejecutable en el MVP

Escribir en el ring de la RX 550 requiere ser dueño del dispositivo. Con `amdgpu` cargada, no lo
somos: el módulo reclama `1002:699f` y su nodo DRM.

- **Implicación de `OWNERSHIP`**: `AGENTS.md` establece que `OWNERSHIP=FULL` exige evidencia
  atribuible completa. Mientras `amdgpu` esté presente, **`OWNERSHIP != FULL`**. Declarar lo
  contrario es un error, no una convención.
- **El desbloqueo** es `unbind` de `1002:699f` de `amdgpu` más carga de `rx550.ko`. Eso es
  escritura en sysfs y cambio de estado del sistema: **prohibido por `AGENTS.md`** sin
  autorización expresa del humano, con restore garantizado.

**Delimitación**, para no propagar el bloqueo más de lo necesario:

- **Invalida**: el criterio 6, y con él el objetivo declarado del proyecto.
- **NO invalida**: criterios 1–5 y todo el trabajo estructural — ring en CPU, validación de
  ioctl, empaquetado de shaders, tests de ABI.

Mientras tanto, el estado honesto del proyecto es: *"el driver funciona pero no ejecuta
shaders en la RX 550 real"*. Eso debe decirse así, sin adornos.

### 5.2 Dos requisitos de calidad heredados

**Validar antes de comparar.** Tres incidentes de esta fase lo motivate:

1. Una salida **entera a cero** produjo "0 discrepancias" y un falso `PASS`. Sin validación
   previa del buffer, el test se autolimita a confirmar que dos caminos erred identically.
2. Un test que imprimía `[FAIL]` por `stderr` y devolvía **`rc=0`** hacía que un CI reportara
   verde sobre un fallo. **Todo test de Fase 4 devuelve código distinto de cero ante fallo.**
3. `shader_vs_c` —el validador que "confirmaba" el shader— **no detectó ninguno** de los tres
   bugs reales, porque **modela** la aritmética en C en vez de compilar y ejecutar el GLSL. Un
   emulador en CPU del GAR **no** sustituye a la ejecución real.

**Reutilizar el test sin tocarlo.** El criterio 6 usa `04-IMPLEMENTACION/decompressor/
test_decompress.c` tal cual. Si hay que modificarlo para que funcione con `librx550`, la
interpretación es que el driver se ha adaptado al test en vez de al revés.

## 6. NO objetivos

Gráficos, display y modesetting · multi-GPU · power management · suspend/resume ·
eviction de VRAM · reset de GPU · virtualización · rendimiento · vGPU · GFX8 counters.

## 7. Decisiones pendientes

### Para IA-2 (Driver)

| # | Decisión | Por qué bloquea |
|---|---|---|
| D-1 | Char device vs subsistema DRM | fija el modo de acceso y el modelo de ioctl |
| D-2 | `IOCTL_SUBMIT_COMPUTE`: campos exactos | ABI; cambiarla después rompe a userspace |
| D-3 | BOs propios vs reusar TTM/GEM | decide si hace falta GPUAddressing en el MVP |
| D-4 | Fence: user o kernel, poll o IRQ | decide si el MVP puede completarse sin IRQ |

### Para IA-1 (Ingeniero Inverso)

| # | Decisión | Por qué bloquea |
|---|---|---|
| R-1 | **¿Hay GAR reutilizable sin `amdgpu`?** | **define si el MVP es viable** |
| R-2 | Secuencia de carga de firmware PSP/SMU | sin ella no hay inicialización |
| R-3 | Offsets de ring, doorbell, CQ, IRQ | necesario antes del scheduler |
| R-4 | Modo de addressing de VRAM soportado en compute | 2 GiB de VRAM no caben en 32 bits |

### Mías, pendientes de lo anterior

- D-5: ICD de Vulkan frente a API privada. Se decide al final del MVP, no antes.
- D-6: reutilización de firmware (contradice F4-AD-3; §2.1).

## 8. Referencias

- `02-ARQUITECTURA/DECISIONS.md` — AD-1..AD-15. AD-1 sobre no reescribir structs internas de
  `amdgpu` se mantiene vigente como advertencia.
- `06-INGENIERIA-INVERSA/register-maps/gfx-v8-compute.md` — **plantilla, offsets vacíos
  (`NOT_STARTED`)**. Ningún dato de este documento debe considerarse establecido.
- `04-IMPLEMENTACION/decompressor/` — shader y agreement test, cierre v1.0.
- Fuente disponible en disco: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu`
  (304 ficheros `.c`) e `include/uapi/drm/amdgpu_drm.h`. **No hay fuentes de Mesa en esta
  máquina**, solo binarios.
