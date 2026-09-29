# DECISIONS-F4 — Registro de decisiones, Fase 4

**Ámbito**: `08-ARQUITECTURA/` (IA-3 Arquitecto)
**Iniciado**: 2026-09-29
**Estado**: vivo

Convención de estados, tomada de `AGENTS.md`:

| Estado | Significado |
|---|---|
| `DECIDIDO` | cerrado, con la evidencia que lo sostiene |
| `ABIERTO` | requiere información que aún no existe |
| `BLOQUEADO` | no avanzable hasta resolver una dependencia |
| `PROPUESTO` |-emittingido por mí, pendiente de las otras IAS |

---

## F4-001 — El MVP es solo compute

- **Fecha**: 2026-09-29
- **Estado**: `DECIDIDO`
- **Decisión**: el driver propio cubre exclusivamente carga de compute. No toca gráficos,
  vídeo, display, PM ni reset.
- **Por qué**: el objetivo verificable del proyecto es el agreement test de Fase 2, que es
  compute. Ampliar al stack gráfico multiplica la superficie sin producir un criterio de éxito
  adicional.
- **Consecuencia**: amdgpu sigue presente para PCIe, APM, power state y display. Ver F4-002.

## F4-002 — El MVP no puede ejecutar en la GPU real sin autorización de sistema

- **Fecha**: 2026-09-29
- **Estado**: `BLOQUEADO`
- **Defecto**: un driver exclusivo necesita que amdgpu no reclame `1002:699f`. Eso exige
  bind/unbind, que es un cambio de estado del sistema.
- **Delimito**: invalida el **criterio de éxito 5** (agreement test contra el driver propio)
  durante el MVP. **No** invalida los criterios 1–4 y 6: cargar el módulo, la validación de
  ABI, el ring en CPU y el fuzz siguen siendo ejecutables.
- **Autorización que lo resuelve**: permiso explícito del humano para `echo 0000:03:00.0 >
  /sys/bus/pci/drivers/amdgpu/unbind` y carga de `rx550.ko`, con restore garantizado.
  `AGENTS.md` prohíbe(sysfs y acciones privilegiadas sin autorización expresa.
- **Nota**: sin esta autorización el MVP entrega "el driver funciona pero no ejecuta shaders
  en la RX 550", lo cual **no** satisface el objetivo declarado. Debe declararse así, no
  maquillarse.

## F4-003 — Transporte kernel↔userspace: ioctl, no mmap de ring

- **Fecha**: 2026-09-29
- **Estado**: `PROPUESTO`
- **Decisión**: ioctl con copia intermedia en el MVP. `mmap` del ring se difiere.
- **Por qué**: `mmap` exige un modelo de coherencia de caché y sincronización que no está
  diseñado; ioctl basta para compute por lotes.
- **Contraargumento que acepto**: la copia añade latencia y puede ser inaceptable si el
  objetivo incluye rendimiento. Se revisa al final del MVP, no antes.

## F4-004 — GPUAddressing: no se usa BISM/HST en el MVP

- **Fecha**: 2026-09-29
- **Estado**: `ABIERTO` — depende de `@IA-1`
- **Decisión provisional**: precisión 32/40 bits si el modo de compute lo soporta. El modo por
  rangos de 48 bits, que es lo que VRAM de 2 GiB normalmente requiere, tiene un formato de
  tabla que aún no está verificado.
- **Por qué importa**: 2 GiB de VRAM y punteros de buffer de proceso no caben en 32 bits.
  Si el hardware solo ofrece 48 bits por rangos, esto **bloquea** el MVP.

## F4-005 — El riesgo principal es el GAR, no el driver

- **Fecha**: 2026-09-29
- **Estado**: `DECIDIDO`
- **Decisión**: la primera petición a `@IA-1` es si existe un camino utilizable de shader a
  ISA para GFX8. Sin eso, el proyecto no es viable y hay que saberlo antes de escribir código.
- **Evidencia disponible**: el hardware **sí** ejecuta el shader, vía RADV, con 0/4096 de
  discrepancias (`edd434b`). Lo que no está establecido es si puede hacerse **sin** RADV.

## F4-006 — `OWNERSHIP` del dispositivo es requisito, no descripción

- **Fecha**: 2026-09-29
- **Estado**: `DECIDIDO`
- **Decisión**: ningún entregable de IA-1 o IA-2 puede declarar `OWNERSHIP=FULL` del nodo.
  Según `AGENTS.md`, `FULL` exige evidencia atribuible completa por identidad PCI, más
  namespaces, FDs de DRM, escritores, PM, governor, IRQ, scheduler, storage y BtrF.
- **Consecuencia práctica**: mientras amdgpu esté cargada, la propiedad del nodo **no es
  nuestra**. Declararlo es un error, no una convencionalidad.

## F4-007 — Heredado de Fases 1 y 2: validar antes de comparar

- **Fecha**: 2026-09-29
- **Estado**: `DECIDIDO`
- **Decisión**: el test debe validar sus propios datos antes de comparar, y el control
  negativo es obligatorio. Learned de esta fase:
  1. Sin validación previa, una salida **entera a cero** produjo "0 discrepancias" y un
     falso `PASS`.
  2. Un test que imprime `[FAIL]` y devuelve `rc=0` hace que un CI reporte verde sobre un
     fallo. **Todo test de Fase 4 debe devolver código de salida no cero ante fallo.**
  3. Un validador que **modela** el código en lugar de ejecutarlo (`shader_vs_c`) no detectó
     ninguno de los tres bugs reales. Para GFX8, un emulador en CPU del GAR **no** sustituye a
     la ejecución real.
- **Consecuencia**: el mismo `make test-gpu` debe correr sin modificarse y dar 0/4096 contra
  `rx550_rt`. Si hay que tocarlo para que funcione, el diseño está mal.

---

## Registro de peticiones a otras IAS

| # | Destinatario | Asunto | Fecha | Estado |
|---|---|---|---|---|
| P-1 | `@IA-1` | ¿Existe camino de shader a ISA para GFX8 sin RADV? | 2026-09-29 | `ABIERTO` |
| P-2 | `@IA-1` | Formato del descriptor de work y del ring de SDMA | 2026-09-29 | `ABIERTO` |
| P-3 | `@IA-1` | Offsets de doorbell, WDDM/RDDM, CQ e IRQ | 2026-09-29 | `ABIERTO` |
| P-4 | `@IA-1` | Modo de addressing de VRAM soportado en compute | 2026-09-29 | `ABIERTO` |
| P-5 | `@IA-2` | Scheduler: round-robin por contexto o contexto único | 2026-09-29 | `ABIERTO` |
| P-6 | `@IA-2` | Aislamiento de memoria por contexto en el MVP | 2026-09-29 | `ABIERTO` |

P-1 y P-4 son bloqueantes. P-2 y P-3 son necesarios antes de escribir el scheduler.
