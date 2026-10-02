# 052 · Los dos SRCID de fault de GFX8 decodificados, y 112 vectores que nadie ha catalogado

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=SCOPED(findings)` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CONTINUES=051 §2 (layout del IV)` · `CORRIGE_por=047 §Tabla (la fila de 0x92 vs 0x93 pasa a REFUTED)`

## CUDA principal

El IV de GFX8 trae `src_id` de 8 bits y el driver registra **dos** para fallos de
traducción. Sus números son **0x92 y 0x93**, contiguos, y ambos apuntan al mismo
handler. Con esto el IV queda **completamente decodificado** por vía estática:
`src_id` dice qué pasó, `vmid` y `pasid` dicen quién, `src_data[0]` dice dónde.

Y de paso: la tabla tiene **112 vectores** y **ninguno** está catalogado en el
proyecto.

Control de duplicación **antes** de derivar: `VISLANDS30_IV_SRCID` → 0 ficheros
en `findings/` y `docs/`.

## 1 · Los dos SRCID de fault

`gmc_v8_0.c:1115` y `:1119`, con valores de
`include/ivsrcid/ivsrcid_vislands30.h:222-223`:

```c
#define VISLANDS30_IV_SRCID_GFX_PAGE_INV_FAULT   0x00000092  /* 146 */
#define VISLANDS30_IV_SRCID_GFX_MEM_PROT_FAULT   0x00000093  /* 147 */
```

| src_id | nombre | nº decimal |
|---|---|---|
| `0x92` | `GFX_PAGE_INV_FAULT` | 146 |
| `0x93` | `GFX_MEM_PROT_FAULT` | 147 |

Contiguos y del rango alto (de 112 vectores declarados), lo que es coherente con
que sean eventos raros.

## 2 · Los dos van al MISMO handler, y se distinguen por src_id

Las dos registraciones pasan **`&adev->gmc.vm_fault`** — el mismo puntero:

```
L1115  ... GFX_PAGE_INV_FAULT, &adev->gmc.vm_fault);
L1119  ... GFX_MEM_PROT_FAULT, &adev->gmc.vm_fault);
```

Es decir: **el driver no despacha dos handlers distintos.** Uno solo procesa ambos
y los separa por el `src_id` del IV, que lee explícitamente en dos sitios:

- `gmc_v8_0.c:1435` — `dev_err(..., entry->src_id, entry->src_data[0])`
- `gmc_v8_0.c:1465` — ídem, en el log de fault

Cadena completa, verificada:

```
HARDWARE   escribe 16 B en el ring de IH, dw0[7:0] = 0x92 o 0x93
CORPUS     tonga_ih.c:262      entry->src_id = dw[0] & 0xff
DISPATCH   amdgpu_irq.c:513    src->funcs->process(adev, src, &entry)
HANDLER    gmc_v8_0.c:1427     gmc_v8_0_process_interrupt
REGISTRO   gmc_v8_0.c:1756     vm_fault.num_types = 1   ← un solo tipo
```

`num_types = 1` (`gmc_v8_0.c:1756`) confirma lo mismo desde el otro lado: para
GFX8 hay **un** tipo de vm_fault, no dos.

## 3 · El IV queda decodificado, y eso es lo que permite correlacionar

Con 051 §2 (layout) y este hallazgo (valores de src_id), un IV de fault se lee
así sin ninguna fuente adicional:

| offset | ancho | lectura |
|---|---|---|
| `dw0[7:0]` | 8 | `0x92` = fallo de invalidación de página · `0x93` = protección de memoria |
| `dw1[27:0]` | 28 | site ID y status del fault |
| `dw2[15:8]` | 8 | el VMID que faults |
| `dw2[31:16]` | 16 | el PASID |

Y como el invalidate se emite **por VMID** (`gmc_v8_0.c:680`,
`1 << vmid`), un fault trae dentro el VMID al que se pidió la invalidación. Es
la primera vez que, por vía puramente estática, existe un camino para correlacionar
un fault con la invalidación que lo precedió.

**Esto no contradice a 018.** `018` objeta que `INVALIDATE_RESPONSE` no
correlaciona con `INVALIDATE_REQUEST` porque `REQUEST` es un mapa de 16 bits sin
token. Correcto, y sigue siendo correcto. Lo que hay **además** es el IV, que es
un evento con identidad, no un estado. Son dos mecanismos distintos y `018` trata
sólo el primero.

## 4 · Un comentario obsoleto que el driver arrastra

`gmc_v8_0.c:1123-1127`, inmediatamente antes de
`amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)`:

```c
/* Adjust VM size here.
 * Currently set to 4GB ((1 << 20) 4k pages).
 * Max GPUVM size for cayman and SI is 40 bits.
 */
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
```

El comentario dice **4 GB**; la llamada produce **64 GB** en esta máquina
(`clamp(12×3, 64, 1024) = 64`, verificado contra la línea del log de arranque
`vm size is 64 GB`). Y menciona "cayman and SI", generaciones anteriores a GFX8.

Es un comentario heredado que ya no describe lo que la línea hace. **No lo he
corregido**: `gmc_v8_0.c` es el árbol de referencia, no código del proyecto, y
AGENTS.md §DOCUMENTACIÓN EXTERNA trata el corpus como fuente de evidencia, no como
material editable. Se registra.

## 5 · El rango completo de vectores, y su ausencia en el proyecto

`ivsrcid_vislands30.h` declara **112** `VISLANDS30_IV_SRCID`, con valores hasta
`0x2a` en el bloque D1 y **`0x92`–`0x93`** para los faults de protección.

`AMDGPU_MAX_IRQ_SRC_ID = 0x100` (`amdgpu_irq.h:32`), o sea 256: la tabla de esta
GPU ocupa 112 de 256 posiciones y `0x92`/`0x93` caen dentro.

Con `src_id` validado contra `AMDGPU_MAX_IRQ_SRC_ID` en `amdgpu_irq.c:500`, la
tabla completa del enum es lo que un driver propio necesita para decodificar
cualquier IV que reciba. **No está en ningún hallazgo ni documento del proyecto.**
No la transcribo aquí: son 112 líneas y pertenece al árbol, no a un hallazgo. Lo
que este documento establece es que **existe, dónde, y que nadie la ha catalogado.**

## 6 · Clasificación

| afirmación | clase | estado |
|---|---|---|
| `GFX_PAGE_INV_FAULT = 0x92` | FACT | **PROVEN** |
| `GFX_MEM_PROT_FAULT = 0x93` | FACT | **PROVEN** |
| ambos se registran contra el mismo handler | FACT | **PROVEN** (mismo puntero) |
| `num_types = 1` para GFX8 | FACT | **PROVEN** |
| el IV se puede correlacionar con el invalidate por VMID | DERIVATION | **PROVEN_DERIVED** |
| el comentario de L1123 dice 4 GB y la llamada da 64 GB | FACT | **PROVEN** (comentario vs log de arranque) |
| la tabla tiene 112 vectores | FACT | **PROVEN** |
| contenido de `src_data[0]` en cada caso | — | **NOT_DETERMINED**, exige RUNTIME |
| diferencia de comportamiento entre 0x92 y 0x93 | — | `REFUTED` en `047`: comparten handler y el mismo cuerpo, y leen los mismos tres `PROTECTION_FAULT_*`. La diferencia está en `src_id`, no en `src_data[0]` |or src_id en el código |

## Lo que este hallazgo NO cierra

No cierra F1, ni 018, ni F2b. No he ejecutado nada. Lo que hace es **cerrar la
decodificación del IV por vía estática**, que hasta ahora requería RUNTIME, y eso
convierte el canal de interrupts en una fuente utilizable para cualquier
discriminante futuro que necesite identificar quién faults y por qué.

## Nota de proceso

Dos búsquedas con regex sobre un fichero de defines devolvieron vacío porque el
formato usa separadores variables; la cita se jonó con `grep -n` literal tras un
`cat -A`. El valor `0x92` estaba en la línea 222 todo el rato. Segundo caso de la
misma clase que el `ih_v3_0.c` de la iteración anterior: **el patrón no es el
fichero**. `READ_SCOPE_GATE` antes de concluir, siempre.