# 060 · `src_data[0]` sí es el payload: el decodificador de display está en `dce_v8_0.c`, no en el GMC

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORRECTS=059 (que lo descartó) y 058 §3 (las 2 candidatas restantes)`

## CUDA principal

`059` descartó `src_data[0]` como(payload del evento: en la única generación
donde se consume, es un puntero de ring. **Eso era cierto pero no era la
pregunta correcta**, porque el decodificador no estaba en el bloque de interrupts
— estaba en el de **display**, y para esta misma GPU.

`dce_v8_0.c:3083-3115`, `dce_v8_0_crtc_irq`:

```c
unsigned crtc = entry->src_id - 1;
uint32_t disp_int = RREG32(interrupt_status_offsets[crtc].reg);

switch (entry->src_data[0]) {
case 0: /* vblank */
        WREG32(mmLB_VBLANK_STATUS + crtc_offsets[crtc],
               LB_VBLANK_STATUS__VBLANK_ACK_MASK);
        if (amdgpu_irq_enabled(adev, source, irq_type))
                drm_handle_vblank(adev_to_drm(adev), crtc);
        break;
case 1: /* vline */
        WREG32(mmLB_VLINE_STATUS + crtc_offsets[crtc],
               LB_VLINE_STATUS__VLINE_ACK_MASK);
        break;
default:
        DRM_DEBUG("Unhandled interrupt: %d %d\n", entry->src_id, entry->src_data[0]);
```

**`src_data[0]` es un discriminante de subtipo de evento.** Y con esto, la
granularidad que `058 §3` daba por perdida queda recuperada.

## 1 · Por qué los SRCID de display parecen alias y no lo son

`058` encontró que `0x13`–`0x17` tienen seis alias cada uno:
`VERTICAL_INTERRUPT{0,1,2}`, `EXT_TIMING_SYNC_LOSS`, `EXT_TIMING_SYNC`,
`EXT_TIMING_SIGNAL`. Lo interpretó como «el hardware no puede distinguirlos».

Es un artefacto de **dónde se registra cada SRCID**:

```c
/* dce_v8_0.c:2696 */
amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY, i + 1, &adev->crtc_irq);
/* dce_v8_0.c:2702 */
amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY, i, &adev->pageflip_irq);
/* dce_v8_0.c:2708 */
amdgpu_irq_add_id(adev, AMDGPU_IRQ_CLIENTID_LEGACY, 42, &adev->hpd_irq);
```

El display registra **SRCID = crtc + 1**, y `dce_v8_0_crtc_irq` lo deshace con
`crtc = src_id - 1`. Los alias del enum `ivsrcid` (`D1_VERTICAL_INTERRUPT*`,
`D1_EXT_TIMING_*`) son **nombres de la especificación**, no registros distintos
del driver: el driver registra el SRCID una vez y desambigua por `src_data[0]`.

**Los alias de `ivsrcid` no son aliases de hardware.** Son una nomenclatura de
generación donde varios eventos comparten número, y el hardware separa el resto
por el segundo dword del vector.

Eso **retira** la conclusión de `058` de que el IV tiene granularidad limitada. La
tiene, pero no donde se busca.

## 2 · Lo que el IV decodifica por completo, para esta GPU

Con `051 §2` (layout), `193` (SRCID de fault), `058` (tabla) y este documento:

| campo | bits | lo consume | qué significa |
|---|---|---|---|
| `dw0[7:0]` | 8 | todos los bloques | SRCID: 1..N = CRTC+1, 42 = HPD, 0x92/0x93 = fault de VM, 0x2a = HPD |
| `dw1[27:0]` | 28 | `dce_v8_0_crtc_irq` | subtipo: 0 = vblank, 1 = vline, otro = sin manejar |
| `dw2[7:0]` | 8 | `tonga_ih_decode_iv` | ring_id |
| `dw2[15:8]` | 8 | GMC | vmid |
| `dw2[31:16]` | 16 | GMC | pasid |

**El IV de GFX8 queda decodificado por vía estática**, sin runtime y sin
documentación externa.

## 3 · Los dos patrones de sincronización que ofrece la GPU

Recogiendo `051 §4`, `059` y este documento, hay dos formas de que el hardware
comunique un puntero, y el coste es distinto:

| patrón | dónde viaja | lectura CPU | posición en `AM_LB_VBLANK_STATUS` |
|---|---|---|---|
| registro + re-lectura | `mmIH_RB_WPTR` | 2 MMIO reads | event-driven, sin polling |
| auto-`IRQ` con puntero | `src_data[0]` del IV | 0 lecturas | el vector **es** la notificación |

El segundo es el barato y **el driver de GFX8 no lo usa** (`tonga_ih.c` no tiene
`self_irq`; el mecanismo existe en `ih_v7_0.c:552` pero para otro ASIC).

Para un driver propio: `LB_VBLANK_STATUS` es un **ack**, y escribirlo es la
forma de liberar el evento. Con `IE` de display se hace por MMIO del LB. Con
registro de IRQ, `amdgpu_irq_get(adev, source, irq_type)`.

## 4 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| `src_data[0]` es subtipo de evento de display | FACT | **PROVEN** (`dce_v8_0.c:3092`) |
| SRCID 1..N = crtc+1 en DCE_v8_0 | FACT | **PROVEN** (`dce_v8_0.c:2696`) |
| los alias de `ivsrcid` no son aliases de hardware | DERIVATION | **PROVEN_DERIVED** |
| el IV queda decodificado por completo sin runtime | DERIVATION | **PROVEN_DERIVED** |
| `tonga_ih.c` no implementa `self_irq` | NEGATIVE_RESULT | **PROVEN_ABSENT** |
| qué subtipos existen para `src_data[0] > 1` | — | **NOT_DETERMINED**: el `default` los descarta |

## Correcciones

- **`058 §3`**: las dos candidatas restantes (registro aparte, estado de scanout)
  quedan **descartadas por este hallazgo**. La información estaba en `src_data[0]`.
- **`059`**: `src_data[0]` **no** es el payload en el único uso de la generación
  IH (`ih_v7_0.c`), y **sí** lo es en el bloque de display. `059` la omitió, pero
  responder la pregunta equivocada: buscó en el bloque que decodifica el IV, no
  en el que lo interpreta el evento.

## Nota de proceso

Dos correcciones encadenadas en esta iteración, y las dos por el mismo error de
búsqueda: **buscar el consumidor de un campo dentro del bloque que produce ese
campo.** `src_data` lo produce el IH (copia de `dw[1]`) y lo consume el DCE. Busqué
en el primero, encontré un consumidor legítimo en otra generación, y concluí que
el campo no tenía payload. Dos pasos de más.

Lo que lo habría resuelto: antes de concluir que un campo no tiene consumidor,
`grep -rl` sobre **todo** `*.c`, no sobre el subárbol temático. Es la diferencia
entre "no lo consume este bloque" y "no lo consume nadie".