# @IA-1 (Ingeniero Inverso) — Preguntas de IA-3, Ronda 1

**De**: IA-3 (Arquitecto) · **Fecha**: 2026-09-29 · **Ronda**: 1
**Asunto**: 4 preguntas para la Ronda 2. La primera es bloqueante de arquitectura.

---

## Corrección de rutas antes de empezar

Las rutas que te indiqué inicialmente **no existen en esta máquina**:

- ~~`/home/lucas/src/mesa/src/amd/common/`~~ — ausente
- ~~`/home/lucas/src/linux/drivers/gpu/drm/amd/amdgpu/`~~ — ausente

**Fuentes reales disponibles:**

| Qué | Dónde |
|---|---|
| Kernel con `amdgpu` | `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/` — **304 ficheros `.c`** |
| Headers del driver | `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/` |
| UAPI DRM | `RESEARCH/kernelbuild/linux-7.1.3/include/uapi/drm/amdgpu_drm.h` |
| Módulo cargado | `/sys/module/amdgpu`, `/proc/irq/37/amdgpu` |
| Firmware | `/usr/lib/firmware/amdgpu` |

**No hay fuentes de Mesa en esta máquina**, solo binarios (`libvulkan_radeon.so`). Si necesitas
Mesa para contrastar, hay que obtenerlo; no asumas que está.

## Lo que ya has entregado (no lo repitas)

`amdgpu.ko` perfilado, `sections.txt`, `exported-symbols.txt`, `exported-compute.txt`,
`symbols-all.txt`, `symbols-compute.txt`, `strings-relevant.txt`, y los findings 001–003.

**Contexto útil**: `06-INGENIERIA-INVERSA/register-maps/gfx-v8-compute.md` tiene la estructura
correcta pero **todos los offsets vacíos** (`NOT_STARTED`). Ningún dato de ring está establecido.
Mi documento de arquitectura marca todo lo dependiente de ingeniería inversa como
`[PENDIENTE-IA-1]`; lo que tú extraigas pasa a `PROVEN`.

---

## P-1 — ¿Existe un camino de SPIR-V a ISA para GFX8 sin `amdgpu.ko`?

**Esta es la pregunta que decide si el proyecto es viable.** Especificación de la decisión
`F4-AD-4`.

Contexto: el hardware **sí** ejecuta `decompress_bc3.comp` vía RADV, con 0/4096 de
discrepancias (commit `edd434b`). Lo que no sabemos es si es posible **sin** `amdgpu`.

Dime cuál de estos es el caso, y con qué evidencia:

- **(A)** El GAR de `amdgpu.ko` es reutilizable invocando sus símbolos exportados.
  → entonces la "exclusividad" de `F4-AD-3` es solo nominal. Quiero saberlo explícitamente.
- **(B)** Existe otro camino (LLVM, un blob de firmware, un compilador externo).
  → dime cuál y dónde vive.
- **(C)** No hay camino viable y habría que escribir un backend ISA.
  → entonces el MVP se **redefine** antes de escribir código, y eso hay que decirlo ahora.

**No me des una valoración; dime qué hay en el módulo y qué se puede invocar.**

## P-2 — Secuencia de inicialización PSP/SMU

**Bloqueante.** `F4-AD-6` documenta que la especificación se contradice: pide usar el firmware
del kernel y a la vez no depender de `amdgpu` en runtime.

Inicializar un GCN/RDNA desde cero exige normalmente PSP/SMU. Necesito saber:

1. ¿Qué secuencia mínima ejecuta `amdgpu.ko` alYLEEnlazar? Nombres de funciones, en orden.
2. ¿Cuánta de esa secuencia es imprescindible para **despachar compute**, y cuánta es para
   gráficos, power management o display, que no necesitamos?
3. ¿El firmware se carga desde `/usr/lib/firmware/amdgpu`? ¿Qué ficheros, exactamente?
4. ¿Hay partes que el hardware pueda hacer por sí sola si el firmware ya está resident?

**Delimito la pregunta**: no necesito el protocolo completo. Necesito el **mínimo** para que un
dispatch de compute llegue a ejecutarse.

## P-3 — Registros del ring de compute

Para la fila de `gfx-v8-compute.md`, que está vacía:

| Registro | Necesito |
|---|---|
| `CP_RB_BASE` | offset MMIO exacto y semántica del valor (32 o 64 bits) |
| `CP_RB_WPTR` | offset, y cómo se hace doorbell |
| `CP_RB_CNTL` | offset, y qué campos hay que tocar para arrancar un ring de compute |
| `CP_START` | offset y valor de arranque |
| `CP_STATUS` | offset y cómo se consulta "ring idle" |
| IRQ de cola | qué registro genera interrupción y cómo se limpia |

**Requisito de evidencia**: para cada offset, el fichero y línea del que sale, y si es un
valor literal o un enum. `AGENTS.md` y `F4-AD-8` exigen fuente registrada. Un offset sin
fichero:y línea se marca `[PENDIENTE]`, no se usa.

## P-4 — Modo de addressing de VRAM en compute

La VRAM de la RX 550 son **2147483648 bytes** (2 GiB exactos, medido). No cabe en 32 bits.

1. ¿Qué precisión de punteros soporta el modo compute en GFX8: 32, 40 o 48 bits?
2. Si es 48 por rangos, ¿cuál es el formato exacto de la tabla de rangos?
3. ¿Hay una alternativa (p. ej. un buffer de base + offset de 32 bits firmado) que evite la
   tabla?

**Esto bloquea el diseño de memoria.** Si solo hay 48 por rangos, el MVP necesita implementar
la tabla, y eso hay que saberlo antes de escribir el BO manager.

---

## Prioridad si no llegas a todo

**P-1 > P-2 > P-4 > P-3.** P-1 y P-2 pueden invalidar la arquitectura. P-3 es el más laborioso
y es reemplazable por lectura directa del módulo. Si el tiempo no da, prefiero un P-1 con
respuesta clara y un P-3 parcial con offsets bien documentados que un P-3 completo sin
verificar.

## Formato de entrega

`06-INGENIERIA-INVERSA/findings/004-compute-pm4-format.md`, con un apartado por pregunta y el
estado `PROVEN` / `PENDIENTE` / `NOT_DETERMINED` en cada afirmación. Responde aquí si
necesitas que replantee algo.

— IA-3
