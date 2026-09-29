# 001 — Arquitectura del driver exclusivo RX 550 (Fase 4)

**Ámbito**: `08-ARQUITECTURA/` (IA-3 Arquitecto)
**Fecha**: 2026-09-29
**Estado**: borrador inicial, pendiente de input de IA-1 e IA-2

> **Regla de escritura de este documento.** No se afirma ningún offset de registro, formato de
> SDMA ni layout de ring sin fuente. Todo lo que depende de ingeniería inversa va marcado
> `[PENDIENTE-IA-1]` y no se da por conocido. Este documento define **interfaces y
> responsabilidades**, que es lo que un arquitecto puede fijar antes de que exista el análisis.

---

## 1. Objetivo

Sustituir `amdgpu` + RADV para la carga de **compute** en la RX 550, de modo que
`decompress_bc3.comp` se ejecute en un driver propio, conservando el resultado verificado en
Fase 2: **0 de 4096 bytes discrepantes** frente al decodificador de referencia (tag
`v1.0-fase2-completa`, commit `edd434b`).

La prueba de que el objetivo se ha cumplido no es "el driver arranca", sino que el mismo
agreement test da 0/4096 **contra el driver propio**.

## 2. Arquitectura de alto nivel

```
┌──────────────────────────────────────────────────────────────┐
│ userspace:  rx550_rt  (runtime, ICD o API privada)            │
│   · carga/descarga SPIR-V            · dispatch               │
│   · buffers SSBO                     · lectura de resultados  │
└───────────────┬──────────────────────────────────────────────┘
                │  ioctl (ABI estable, versionado)
┌───────────────▼──────────────────────────────────────────────┐
│ kernel:  rx550.ko                                             │
│   · gestión de contexto y memoria          ·GAR: shader→host  │
│   · ICD de cola y scheduler               · Residency         │
│   · doorbell / SQEs                       · fault handling    │
└───────────────┬──────────────────────────────────────────────┘
                │  MMIO (BAR0..BAR5) + SDMA rings
┌───────────────▼──────────────────────────────────────────────┐
│ hardware:  Polaris 12 (GFX8)                                 │
│   · CUs, LDS, TCS                        · texture units      │
│   · SDMA engines + doorbells             · VRAM 2 GiB         │
└──────────────────────────────────────────────────────────────┘
```

Componentes y responsabilidades:

| Componente | Responsabilidad | Depende de |
|---|---|---|
| `rx550.ko` | MMIO, rings, reset, IRQ, memoria | BSD, PIC, PM |
| Scheduler | Filas de trabajo, preemptión, contexto | formato de SQ: `[PENDIENTE-IA-1]` |
| GAR (GPU Assembly/Register) | Shader → ISA hardware | **`[PENDIENTE-IA-1]`, es el riesgo mayor** |
| `rx550_rt` userspace | API, ICD, caché de shaders | ABI de ioctl (este doc) |

## 3. Interfaz kernel ↔ userspace

Transport: **ioctl**, no `mmap` de ring por el cliente en el MVP. Motivo: `mmap` de un ring
exige un modelo de sincronización que todavía no está diseñado, y un ioctl con copia
intermedia es suficiente para compute por lotes. `mmap` se difiere a la Fase 4.2 si el
rendimiento lo exige.

```
struct rx550_ioctl_desc {
    __u32 abi_version;      // el kernel rechaza si no coincide
    __u32 cmd;              // RX550_IOC_*
    __u64 arg;              // puntero a struct del comando
    __u64 arg_size;         // longitud, validada contra max del comando
    __u64 out_off, out_len; // copia a userspace
    __u64 in_off,  in_len;  // copia desde userspace
    __u64 status;           // salida: 0 = OK, >0 = código de error
};
```

Comandos del MVP:

| Cmd | Uso |
|---|---|
| `CREATE_CTX` | crea contexto de compute |
| `LOAD_SHADER` | registra SPIR-V; devuelve id + log de compilación |
| `ALLOC_MEM` | reserva VRAM (USERPTR o no) |
| `MAP_MEM` | fija direcciones de VRAM en el espacio del shader |
| `BIND_SSBO` | liga binding ↔ buffer + offset + rango |
| `SET_PUSH_CONST` | escribe el push constant block |
| `DISPATCH` | x,y,z workgroups |
| `WAIT` | fence con timeout |
| `READBACK` | copia VRAM → userspace |

Decisiones de ABI, con su porqué:

- **`abi_version` obligatorio y comparado al entrar.** Un driver de kernel y una librería
  userspace desalineados no deben producir corrupción silenciosa.
- **Validación de `arg_size` por comando**, contra un máximo conocido, antes de copiar.
- **`READBACK` como comando y no como `mmap`**: es el camino que necesita el agreement test, y
  así el MVP no depende todavía de un modelo de coherencia de caché compartido.

**Interfaz de GPUAddressing.** No se usa BISM/HST por defecto. Alternativa: precisión 48 bits
requiere el modo de addressing por rangos, cuyo formato de tabla es `[PENDIENTE-IA-1]`. Para el
MVP, planar 32/40 bits si el hardware lo soporta en el modo de compute elegido
`[PENDIENTE-IA-1]`. Este es un bloqueante real para 2 GiB de VRAM y hay que decidirlo pronto.

## 4. Path de submit: de userspace a la ring de compute

```
userspace:  rx550_rt_dispatch(ctx, x, y, z)
   ↓ rellena un paquete de trabajo en memoria de usuario
ioctl DISPATCH
   ↓
kernel:     scheduler añade el TW a una fila
   ↓ escribe el descriptor en el ring de SDMA
doorbell:   MMIO write → despierta el motor
   ↓
hardware:   SDMA drena el ring → rellena WDDM/RDDM → CQ/interrupt
   ↓ IRQ
kernel:     marca el fence, despierta el waiter
   ↓
userspace:  rx550_rt_wait(fence) → READBACK
```

Puntos donde el diseño **está abierto** y requieren IA-1:

| Punto | Por qué importa | Estado |
|---|---|---|
| Estructura del descriptor de work | Si está mal, el hardware cuelga o ejecuta basura | `[PENDIENTE-IA-1]` |
| Ring sizing y wraparound | Si el ring no envuelve correctamente, trabajo perdido | `[PENDIENTE-IA-1]` |
| Doorbell register y su offset | Un offset inventado es un cuelgue silencioso | `[PENDIENTE-IA-1]` |
| Inkremento de WDDM | Señal de error si el hardware no avanza | `[PENDIENTE-IA-1]` |
| Interrupción CQ | Si no se dispara, `WAIT` cuelga | `[PENDIENTE-IA-1]` |

**Regla dura que se hereda de Fases 1 y 2**: ningún offset se escribe en código hasta que
venga de un fuente registrado. La cadena de evidencia debe incluir el binario analysed, el
offset y el contexto, como se hizo con el parser de AD-1.

## 5. Stack mínimo a reemplazar

**Solo compute.** El driver propio **no** toca gráficos, vídeo, display ni capacidad de compute
avanzado en el MVP.

Se mantiene amdgpu para: gestión de PCIe, APM, power state, reset, display. **Implicación
crítica**: para que el driver propio tome la GPU, hay que hacer que amdgpu **no** reclame el
dispositivo — bind/unbind de `1002:699f`. Eso requiere privilegios y es un cambio de estado
del sistema: **no está autorizado** sin aprobación explícita del humano, y el MVP **no lo
incluye**.

### Consecuencia que hay que aceptar de entrada

Con dos drivers compitiendo por el mismo dispositivo, **el MVP no puede ejecutar el
shader en la GPU real desde el driver propio**. Las dos opciones:

- **(A) Bind sobre `vfio-pci` / `bind` de driver**: fuera de la GPU para amdgpu, piloto en
  modo no-exclusivo. Requiere autorización de sistema.
- **(B) GPU secundaria o entorno de pruebas**: un segundo `[1002:699f]` no está disponible.

**Conclusión: el agreement test del MVP solo es ejecutable si se autoriza (A).** Hasta
entonces, el trabajo se limita a compilar, a tests de estructura de paquetes en CPU, y a
revisión del análisis de IA-1. Esto es una limitación de planificación, no de diseño, y hay
que decía antes de empezar, no después.

## 6. Criterios de éxito del MVP

| # | Criterio | Verificación |
|---|---|---|
| 1 | `rx550.ko` carga sin panic en una máquina de prueba | log de dmesg |
| 2 | ioctl round-trip con validación de ABI | fuzz de `arg_size` |
| 3 | `LOAD_SHADER` acepta el SPIR-V de `decompress_bc3.comp` y devuelve handle | log de GAR |
| 4 | `DISPATCH` completa sin WDDM stuck | fence con timeout |
| 5 | **`make test-gpu` da 0/4096 con `rx550_rt`** | el agreement test existente, sin modificar |
| 6 | Sin `oops`, sin VRAM leak en 10 000 dispatches | dmesg + RSS |

**El criterio 5 es el único que demuestra el objetivo.** Los otros son necesarios.

El criterio 5 reutiliza `04-IMPLEMENTACION/decompressor/test_decompress.c` sin modificar una
línea. Si el test necesita cambios para funcionar con el driver propio, es señal de que el
driver se ha adaptado al test en vez de al revés.

## 7. Decisiones pendientes que requieren input

### De IA-1 (Ingeniero Inverso) — bloqueantes

1. **GAR: ¿existe un compilador de shader utilizable?** GFX8 no tiene un compilador público.
   Esto decide si el MVP es viable: usar un compilador existente (LLVM/AMDGPU) o escribir el
   backend, que es un proyecto mayor que el driver.
2. Formato del descriptor de work de compute en el ring de SDMA.
3. Offsets de doorbell, WDDM/RDDM, CQ, y el mecanismo de IRQ.
4. Modo de addressing de VRAM soportado en compute (32/40/48 bits).

### De IA-2 (Driver)

1. ¿El scheduler del MVP es round-robin por contexto, o un único contexto activo? Afecta al
   diseño de `CREATE_CTX` y al aislamiento.
2. ¿Aislamiento de memoria por contexto en el MVP, o memoria plana compartida? Afecta a si
   hace falta GPUAddressing en 2.1.

### Mías, pendientes de los anteriores

- `DECISIONS-F4-002`: si se puede ejecutar en GPU real durante el MVP (depende de la autorización A).
- `DECISIONS-F4-003`:ICD de Vulkan frente a API privada (solo decide al final del MVP).

## 8. Riesgo principal

**El riesgo no es el driver. Es el GAR.** Si no hay un camino de shader a ISA para GFX8, el
MVP se convierte en "el driver funciona pero no ejecuta shaders", que es un resultado que no
sustenta el objetivo del proyecto. **Por eso la pregunta 1 a IA-1 es la primera petición, antes
de escribir una línea de código.**

Lo que sí sabemos por evidencia propia: el hardware **ejecuta** el shader en la RX 550, vía
RADV, con 0/4096 de discrepancias. Lo que no sabemos es si podemos hacerlo sin RADV.
