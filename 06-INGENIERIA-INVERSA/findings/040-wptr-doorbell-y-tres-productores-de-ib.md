# 040 · `wptr` y doorbell reconstruidos — y hay **tres** productores de referencia-a-IB, no uno

`CLASSIFICATION=IMPLEMENTATION+CORRECTION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`CIERRA=el bloque E de la frontera` · `CORRIGE=una lectura incompleta de 039`

## CUDA principal

Dos cosas. La primera es un **descubrimiento**: GFX8 no tiene un productor de "referenciar un
IB" sino **tres**, uno por tipo de ring, con **formatos distintos**. Mi `039` implementó el de
sDMA y no dijo que existían los otros dos, lo cual convertía "el productor" en "un productor"
sin decirlo.

La segunda es la geometría del ring, que era lo que faltaba para que la secuencia dejar de ser
un formato correcto y pase a ser un envío.

## 1 · Tres productores, tres formatos

| ring | productor | formato | paquete | dwords |
|---|---|---|---|---|
| GFX | `gfx_v8_0_ring_emit_ib_gfx` (`:6075`) | **PACKET3** | `INDIRECT_BUFFER` 0x3F, count 2 | 4 |
| compute | `gfx_v8_0_ring_emit_ib_compute` (`:6107`) | **PACKET3** | `INDIRECT_BUFFER` 0x3F, count 2 | 4 |
| KIQ | — el mismo `emit_ib` que compute (`:6969`) | **PACKET3** | 0x3F, count 2 | 4 |
| sDMA/page | `sdma_v4_0_ring_emit_ib` (`sdma_v4_0.c:816`) | **sDMA** | `SDMA_OP_INDIRECT` = 4 | 6 |

El de GFX y el de compute comparten opcode y cuentan igual, y se diferencian en **un bit**:

```c
/* gfx_v8_0_ring_emit_ib_gfx */
header = PACKET3(PACKET3_INDIRECT_BUFFER, 2);
control |= ib->length_dw | (vmid << 24);

/* gfx_v8_0_ring_emit_ib_compute */
u32 control = INDIRECT_BUFFER_VALID | ib->length_dw | (vmid << 24);
```

`INDIRECT_BUFFER_VALID` es `1 << 23` (`cikd.h:317`). El ring de **compute** pone el bit de
válido; el de **gráficos no**. Es el mismo paquete con un bit distinto y **no sé por qué**
— `NOT_DETERMINED`, y no lo supongo.

Dos consecuencias que no había visto:

**La máscara de dirección es distinta y más fuerte.** `gfx_v8_0` usa
`ib->gpu_addr & 0xFFFFFFFC` — 4 bytes, no 32. `sdma_v4_0` usa `& 0xffffffe0` — 32 bytes. El
comentario de `sdma_v4_0` dice *"base must be 32 byte aligned"*; el de GFX no dice nada. Dos
rings del mismo ASIC con alineaciones exigidas distintas, y `039` implementó la del sDMA sin
mencionar la otra.

**`vmid` va en bits 31:24**, no en 19:16. `control |= (vmid << 24)`. Otro sitio para el mismo
campo en otro productor, y otro lugar donde un mismo nombre significa dos cosas.

**Y `039` se equivocó al generalizar.** Escribí allí, en el punto 1 de "cinco puntos", que el
paquete de referencia "es un paquete sDMA con el VMID en bits 3:0, no un PACKET3". Eso es
cierto del productor sDMA que implementé, y **falso como afirmación sobre GFX8**: los anillos
de gráficos y de compute usan `PACKET3_INDIRECT_BUFFER`. Lo que 039 debería haber dicho es "el
productor que implementé es sDMA, y no comprobé si hay más". No lo comprobé. El `SDMA_OP_INDIRECT`
de 039 es real y está bien codificado; lo que no es único es el papel.

## 2 · La geometría del ring, completa y verificada

`amdgpu_ring_init()`, `amdgpu_ring.c:111-126`:

```c
max_ibs_dw = ring->funcs->emit_frame_size +
             amdgpu_ring_max_ibs(ring->funcs->type) * ring->funcs->emit_ib_size;
max_ibs_dw = (max_ibs_dw + ring->funcs->align_mask) & ~ring->funcs->align_mask;
if (WARN_ON(max_ibs_dw > max_dw))
        max_dw = max_ibs_dw;
ring->ring_size = roundup_pow_of_two(max_dw * 4 * sched_hw_submission);
...
ring->buf_mask = (ring->ring_size / 4) - 1;
```

Para el ring GFX de la RX550 (`gfx_v8_0.c:6873-6900`):

| entrada | valor | fuente |
|---|---|---|
| `align_mask` | `0xff` | `:6875` |
| `emit_frame_size` | 172 | `:6881`, descompuesto en 18 términos |
| `emit_ib_size` | 4 | `:6900` |
| `amdgpu_ring_max_ibs(GFX)` | **192** | `amdgpu_ring.c` — *"Need to keep at least 192 on GFX7+ for old radv"* |
| `max_dw` (pedido) | 1024 | `:1875` |
| `sched_hw_submission` | 8 | valor por defecto de `amdgpu_sched_hw_submission` |

```
max_ibs_dw = 172 + 192*4 = 940
alineado a 0x100        = 1024        (940 & ~0xff = 768, +0xff & ~0xff = 1024)
max_dw = max(1024, 1024) = 1024        (el WARN_ON no dispara)
ring_size = roundup_pow_of_two(1024*4*8) = 32768
buf_mask  = 32768/4 - 1 = 8191
```

**`0192` y no 15.** Es el número que hace que la reserva sea suficiente, y el comentario dice
exactamente por qué: compatibilidad con radv. Es un número heredado de un driver de espacio de
usuario, no una propiedad del hardware. `MODEL_CHOICE`, no `HARDWARE`.

`028` cerró la fórmula pero no estos valores, y `0192` es el mayor de todos ellos.

## 3 · `wptr` y el doorbell

`gfx_v8_0_ring_set_wptr_gfx()`, `gfx_v8_0.c:6028-6040`:

```c
if (ring->use_doorbell) {
        *ring->wptr_cpu_addr = lower_32_bits(ring->wptr);
        WDOORBELL32(ring->doorbell_index, lower_32_bits(ring->wptr));
} else {
        WREG32(mmCP_RB0_WPTR, lower_32_bits(ring->wptr));
        (void)RREG32(mmCP_RB0_WPTR);
}
```

`use_doorbell` es `true` en todos los rings de GFX8 que he leído (`:1862` compute,
`:1973` gfx). El `else` escribe `mmCP_RB0_WPTR` y **vuelve a leerlo** — un readback como
semántica de escritura, que es un patrón que no aparece en ningún otro sitio del camino y que
`039`/`037` no habían tocado.

Y el doorbell es la **única escritura del camino que no es un paquete**:

```c
/* amdgpu_doorbell_mgr.c:59-69 */
void amdgpu_mm_wdoorbell(struct amdgpu_device *adev, u32 index, u32 v)
{
        if (index < adev->doorbell.num_kernel_doorbells)
                writel(v, adev->doorbell.cpu_addr + index);
        else
                dev_err(..., "writing beyond doorbell aperture: 0x%08x!\n", index);
}
```

`adev->doorbell.cpu_addr + index` — `index` en **dwords**, así que el desplazamiento real es
`index * 4`. `adev->doorbell.base = pci_resource_start(adev->pdev, 2)`
(`amdgpu_doorbell_mgr.c:210`): **el doorbell es una escritura a BAR2**, no un registro MMIO
con nombre. Es el único punto del camino de envío donde el driver escribe fuera de un paquete.

**Verificado en este host**, y aquí sí es una lectura, no una escritura:

```
01:00.0  Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X] (rev c7)
BAR0 (0x10): e000000c    64-bit, prefetchable
BAR2 (0x18): f000000c    64-bit, prefetchable   <- la aperture de doorbells
BAR4 (0x20): 0000e001
BAR5 (0x24): f7d00000
```

BAR2 en `0x00000000f0000000`. Los índices legacy de GCN (`amdgpu_doorbell.h:100-119`, vía
`vi.c:1441` → `legacy_doorbell_index_init`):

```
KIQ        0x000      MEC_RING0   0x010    GFX_RING0   0x020
sDMA_ENG0  0x1E0      IH          0x1E8    MAX         0x3FF
```

Un ring compute usa `mec_ring0 + ring_id` (`gfx_v8_0.c:1863`), o sea 0x010 para el primero. Su
doorbell estaría en `0xF0000000 + 0x10*4 = 0xF0000040`. **`NOT_RUN`: no he escrito ahí, y no
se escribe sin autorización explícita.** El cálculo es aritmética sobre constantes verificadas;
la escritura es `RUNTIME` bloqueado por política, no por duda.

## 4 · La reserva de IB, en bytes

`amdgpu_ib_get(adev, NULL, size, ...)` — `size` es **bytes**, no dwords. Verificado con
`gfx_v8_0.c:887`, que pide `20` y escribe `ib.length_dw = 5`: 5 dwords son 20 bytes exactos.
Los demás usos encajan: 256 → 64 dwords, 16 → 4, `AMDGPU_GEM_DOMAIN_GTT` para todos.

Lo que no había conectado: el IB es RAM de sistema, el ring también (`AMDGPU_GEM_DOMAIN_GTT` en
`amdgpu_ring.c` para el `ring_obj`), y el doorbell es VRAM-vía-BAR2. **Tres espacios de
memoria distintos** en una sola entrega, y por eso `rx550_ring_submit()` recibe dos `ib`
distintos en vez de uno.

## UNLOCKS

- La geometría del ring está cerrada y verificada: 32768 bytes, `buf_mask` 8191, alineación
  0x100, 192 IBs de reserva. Una implementación propia puede calcular su `wptr` y decidir
  cuándo hay sitio sin copiar de amdgpu.
- El doorbell es una escritura a BAR2 con `index * 4`, y el índice de cada ring se conoce.
  La aritmética está; la escritura está bloqueada por política y así queda escrito.
- El `readback` de `mmCP_RB0_WPTR` es la única semántica de escritura no-paquete del camino, y
  sólo en el `else` que GFX8 no toma.

## Lo que queda abierto, y por qué no se resuelve aquí

| afirmación | estado | por qué |
|---|---|---|
| por qué compute pone `INDIRECT_BUFFER_VALID` y gfx no | `NOT_DETERMINED` | ni comentario ni test lo explica |
| qué necesita el `readback` de `WPTR` | `NOT_DETERMINED` | rama que GFX8 no toma |
| si el NOP de alineación es necesario o cosmético | `NOT_DETERMINED` | requiere `wptr` real, y `wptr` real requiere ring real |
| alineación mínima de un IB por tipo de ring | `PARTIAL`: 4 B en gfx/compute, 32 B en sDMA | los dos comentarios dicen cosas distintas |
| qué hace el hardware con un `wptr` mayor que el buffer | `NOT_DETERMINED` | `buf_mask` existe pero su aplicación no está en el camino que he leído |

Ninguno se resuelve con el corpus. Los dos primeros necesitan la especificación, que `033`
ya declaró no publicada. Los otros dos son `RUNTIME` y `RUNTIME=NOT_RUN` por política.

## Falsación

- La geometría se refuta si `amdgpu_ring_max_ibs(AMDGPU_RING_TYPE_GFX)` no devuelve 192, o si
  `emit_frame_size` no suma 172. Ambas están en el código con su línea.
- Los tres productores se refutan si un cuarto emisor de IB existe para otro tipo de ring de
  GFX8. `grep -rn "\.emit_ib *=" *.c` da siete y los tres de GFX8 son los que cito.
- El doorbell en BAR2 se refuta si `adev->doorbell.base` no es `pci_resource_start(pdev, 2)`.
  La línea existe, y el host confirma que BAR2 es una BAR de 64 bits con espacio de memoria.

## Evidencia

```
amdgpu_ring.c:          111-126 (geometría), amdgpu_ring_max_ibs (192, con su comentario)
gfx_v8_0.c:             6028-6040 (set_wptr), 1875/1977 (max_dw 1024),
                        6075-6105 (emit_ib_gfx), 6107-6140 (emit_ib_compute),
                        6873-6900 (ring_funcs_gfx: align_mask, frame_size, ib_size),
                        6954-6975 (ring_funcs_kiq: usa el emit_ib de compute), 1862-1863
amdgpu_doorbell_mgr.c:  59-69 (wdoorbell), 205-215 (base = BAR2), 130-139 (índice GPU)
amdgpu_doorbell.h:      100-119 (índices legacy), cikd.h:317 (INDIRECT_BUFFER_VALID 1<<23)
vi.c:                   1441 (legacy_doorbell_index_init para GFX8)
amdgpu_ttm.c:           670-676 (DOORBELL: uncached, iomem)
host (LECTURA):         lspci/setpci de 01:00.0, BAR2 = 0xF0000000
corpus:                 MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro escrito. `insmod` no ejecutado. `GPU INTACTA`.
