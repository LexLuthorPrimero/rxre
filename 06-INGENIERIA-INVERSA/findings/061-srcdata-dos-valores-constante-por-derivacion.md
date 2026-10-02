# 061 · `src_data[0]` tiene exactamente dos valores válidos, y es constante por derivación

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CIERRA=060 §4, última fila` · `CONTINUES=051, 052, 058, 059, 060`

## CUDA principal

`060` dejó abierto: *qué subtipos existen para `src_data[0] > 1`*, respondiendo
que el `default` los descarta.

Se cierra, y no con una búsqueda: **es constante en todo el dominio legal de
generaciones presentes.** GFX6, GFX8 y GFX10 enumeran los **mismos dos** casos,
con los **mismos comentarios**, carácter a carácter.

Eso es `DERIVATION_BEFORE_OBSERVATION` (AGENTS.md:310): si el resultado es
constante en el dominio, la observación no aporta. Aquí no hay ni una sola
observación que hacer — el campo tiene dos valores por contrato, y `default` existe
para robustez, no para cubrir una tercera posibilidad.

## 1 · El resultado

```
dce_v6_0    2 subtipos    case 0: /* vblank */   case 1: /* vline */
dce_v8_0    2 subtipos    idénticos, comentarios idénticos
dce_v10_0   2 subtipos    idénticos, comentarios idénticos
```

Tres generaciones separadas por cuatro años de producto, con el switch
byte a byte el mismo:

```c
switch (entry->src_data[0]) {
case 0: /* vblank */
        ...
        DRM_DEBUG("IH: IH event w/o asserted irq bit?\n");
        DRM_DEBUG("IH: D%d vblank\n", crtc + 1);
case 1: /* vline */
        ...
        DRM_DEBUG("IH: IH event w/o asserted irq bit?\n");
        DRM_DEBUG("IH: D%d vline\n", crtc + 1);
default:
        DRM_DEBUG("Unhandled interrupt: %d %d\n", entry->src_id, entry->src_data[0"]);
```

## 2 · Lo que significa

- **`src_data[0]` ∈ {0, 1}** para eventos de display. `PROVEN_DERIVED` por
  constancia en el dominio legal.
- El `default` no cubre un tercer subtipo que ocurra en hardware: cubre
  **robustez**, porque el valor viene del hardware y el driver no lo controla.
- **GFX8 no recortó nada.** No es que esta generación tenga menos subtipos que las
  vecinas: es que el campo nunca tuvo más.
- El `DRM_DEBUG("Unhandled interrupt")` es un `dev_dbg`, no un `dev_warn` — es
  decir, el driver considera que ver ese `default` **no es un error**. Consistente
  con que el campo tenga dos valores.

Corolario para un driver propio: **no hay un tercer valor que descubrir**. Si se
implementa el camino de display, son vblank y vline, y el `default` es por si acaso.

## 3 · Dónde queda el IV de GFX8, por completo

Con este documento, el canal de interrupts de la GPU queda leído de punta a punta
**sin runtime y sin documentación externa**:

| campo | bits | significado | fuente |
|---|---|---|---|
| `dw0[7:0]` | 8 | SRCID | 051 §2 |
| | | `1..N` = CRTC+1 | 060 §1 |
| | | `42` = HPD | 060 §1 |
| | | `0x92`, `0x93` = fault de VM | 052 §1 |
| `dw1[27:0]` | 28 | subtipo: `0` vblank, `1` vline | 060 §2, este |
| `dw2[7:0]` | 8 | ring_id | 051 §2 |
| `dw2[15:8]` | 8 | vmid | 051 §2 |
| `dw2[31:16]` | 16 | pasid | 051 §2 |
| — | — | `client_id` constante = LEGACY | 051 §2 |

Es el único camino por el que el hardware avisa a la CPU sin que la CPU lea un
registro, y está cerrado. Cuando llegue el runtime, lo que haya que observar ya
está nombrado.

## 4 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| `src_data[0]` ∈ {0, 1}, constante en GFX6/8/10 | DERIVATION | **PROVEN_DERIVED** |
| los comentarios son idénticos entre generaciones | FACT | **PROVEN** |
| `default` es robustez, no tercer subtipo | DERIVATION | **PROVEN_DERIVED** |
| GFX8 no recortó subtipos | DERIVATION | **PROVEN_DERIVED** |
| `dev_dbg` en el `default`, no `dev_warn` | FACT | **PROVEN** |

## 5 · Lo que queda abierto, y es deliberado

Cerrado el IV, la frontera que impide cerrar más es **el orden de ejecución del
invalidate respecto al siguiente IB** (`F1`), y no depende de decodificar el IV:
depende de saber si el `WAIT_REG_MEM` con `FUNCTION=always` espera algo. Eso está
en `056` como `NOT_DETERMINED` con la fuente primaria descartada con causa, y su
discriminante está escrito en `017 §5`.

Es `BLOCKED_BY_AUTHORIZATION`: requiere escribir en la GPU. Y `057 §5` demostró que
**toda** observación de GPUVM en esta máquina pasa por escribir, así que no hay una
ruta lateral que la esquive.

## Nota de proceso

Este es el hallazgo más corto de la tanda y el que menos trabajo costó, y llega
después del más largo. La razón: la pregunta *"¿existe un tercer valor?"* se
responde mirando tres generaciones, no leyendo una. Las dos iteraciones previas
(`059`, `060`) gastaron esfuerzo en **buscar** en lugar de en **preguntar si el
resultado podía ser constante**.

Es el mismo punto de `DERIVATION_BEFORE_OBSERVATION` que el
`INFORMATION_GAIN_GATE` del proyecto pide aplicar antes de escolher tarea: si puedo derivar
la respuesta, no debo medirla. Lo hice al revés dos veces y luego bien una vez.